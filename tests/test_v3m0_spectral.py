from __future__ import annotations

import base64
import dataclasses
import inspect
import math
import struct
import unittest
from unittest import mock

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.dynamics import VerifiedTransition, measure_transition
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.fp64 import is_positive_zero
from rulespace_v3.fp64_protocol import build_fp64_enclosure_protocol
from rulespace_v3.grids import DynamicsKGridManifest
from rulespace_v3.laurent import (
    certify_laurent_residuals,
    laurent_residual_payload,
)
from rulespace_v3.metric import build_stability_metric_witness
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.registry import build_closed_control_registry
from rulespace_v3.spectral import (
    HARD_COLUMN_NAMES,
    PowerDriftAudit,
    VerifiedNormalizedMetricResidualAudit,
    _preflight_spectral_resources,
    _scalar_gauss_jordan_inverse,
    _scalar_hermitian_cholesky,
    _scalar_lower_triangular_inverse,
    _spectral_ordered_complex_dot_values,
    build_exact_zero_spectral_margin_coverage,
    build_power_drift_audit,
    normalized_metric_residual_audit_payload,
    power_drift_audit_payload,
    spectral_margin_coverage_payload,
    spectral_point_sidecar_payload,
    certify_normalized_metric_residual_audit,
    verify_normalized_metric_residual_audit,
    verify_power_drift_audit,
    verify_spectral_margin_coverage,
)
from rulespace_v3.structure import build_structure_manifest
from tests.test_v3m0_dynamics import _quarter_turn_controls


def _decode_column(value: str) -> tuple[float, ...]:
    raw = base64.b64decode(value, validate=True)
    return tuple(
        item[0] for item in struct.iter_unpack(">d", raw)
    )


class ExactZeroSpectralAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        cls.construction = matched_ablation(cls.controls[0].factory)
        assert cls.construction.pair is not None
        cls.factory = cls.construction.pair.actual
        cls.authority = issue_synthetic_prestructure_authority(
            cls.parent,
            cls.registry,
            "full",
            cls.construction,
            "actual",
        )
        cls.transition = measure_transition(cls.factory, cls.authority)
        cls.structure = build_structure_manifest(
            cls.factory,
            cls.authority,
        )
        cls.metric = build_stability_metric_witness(
            cls.factory,
            cls.authority,
            cls.structure,
        )
        cls.protocol = build_fp64_enclosure_protocol()
        (
            cls.structure_residual,
            cls.metric_residual,
        ) = certify_laurent_residuals(
            cls.transition,
            cls.structure,
            cls.metric,
            cls.protocol,
        )

    def _coverage(self):
        return build_exact_zero_spectral_margin_coverage(
            self.transition,
            self.metric,
            self.protocol,
        )

    def _normalized(self):
        coverage = self._coverage()
        verified = certify_normalized_metric_residual_audit(
            self.metric_residual,
            coverage,
            self.transition,
            self.metric,
        )
        return coverage, verified

    def test_exact_zero_coverage_has_root64_fill_and_fourteen_hard_columns(self):
        coverage = self._coverage()
        self.assertEqual(
            coverage.qualification_grid.qualification_profile,
            "exact-offset-zero-v1",
        )
        self.assertEqual(
            coverage.qualification_grid.reciprocal_indices,
            ((0,),),
        )
        self.assertEqual(
            coverage.spectral_diagnostic_grid,
            coverage.qualification_grid,
        )
        pi_hi = (
            self.protocol.root_interval_table.pi_upper_numerator
            / float(1 << self.protocol.root_interval_table.dyadic_exponent)
        )
        self.assertGreaterEqual(coverage.fill_distance, pi_hi)
        self.assertGreater(coverage.fill_distance, 3.14)
        self.assertFalse(is_positive_zero(coverage.fill_distance))

        sidecar = coverage.point_enclosures
        self.assertEqual(sidecar.point_count, 1)
        self.assertEqual(
            sidecar.raw_diagnostic_status,
            "unavailable-v1",
        )
        self.assertEqual(sidecar.raw_byte_count, 14 * 8)
        self.assertEqual(len(HARD_COLUMN_NAMES), 14)
        for field in HARD_COLUMN_NAMES:
            with self.subTest(field=field):
                values = _decode_column(getattr(sidecar, field))
                self.assertEqual(len(values), 1)
                self.assertTrue(math.isfinite(values[0]))
        self.assertTrue(
            is_positive_zero(
                _decode_column(
                    sidecar.transition_symbol_error_upper_b64
                )[0]
            )
        )
        self.assertTrue(
            is_positive_zero(
                _decode_column(sidecar.metric_symbol_error_upper_b64)[0]
            )
        )
        for values in (
            coverage.m_sigma_min_axis_derivative_bounds,
            coverage.m_sigma_max_axis_derivative_bounds,
            coverage.g_lambda_min_axis_derivative_bounds,
            coverage.g_lambda_max_axis_derivative_bounds,
        ):
            self.assertEqual(len(values), 1)
            self.assertTrue(is_positive_zero(values[0]))
        for value in (
            coverage.m_sigma_min_coverage_increment,
            coverage.m_sigma_max_coverage_increment,
            coverage.g_lambda_min_coverage_increment,
            coverage.g_lambda_max_coverage_increment,
        ):
            self.assertTrue(is_positive_zero(value))
        self.assertGreaterEqual(coverage.covered_m_sigma_min_lower, 1e-8)
        self.assertLessEqual(
            coverage.covered_m_condition_number_upper,
            1e8,
        )
        self.assertGreaterEqual(coverage.covered_g_lambda_min_lower, 1e-12)
        self.assertLessEqual(
            coverage.covered_g_condition_number_upper,
            1e8,
        )
        self.assertEqual(
            verify_spectral_margin_coverage(
                coverage,
                self.transition,
                self.metric,
            ),
            coverage,
        )

    def test_coverage_has_no_laurent_input_or_reverse_dependency(self):
        self.assertEqual(
            tuple(
                inspect.signature(
                    build_exact_zero_spectral_margin_coverage
                ).parameters
            ),
            ("transition", "stability_metric", "fp64_protocol"),
        )
        with mock.patch(
            "rulespace_v3.spectral.verify_laurent_residual_certificate",
            side_effect=AssertionError("coverage touched Laurent residual"),
        ):
            self._coverage()

    def test_exact_origin_uses_the_frozen_scalar_candidate_path(self):
        with (
            mock.patch(
                "rulespace_v3.spectral._scalar_gauss_jordan_inverse",
                wraps=_scalar_gauss_jordan_inverse,
            ) as inverse,
            mock.patch(
                "rulespace_v3.spectral._scalar_hermitian_cholesky",
                wraps=_scalar_hermitian_cholesky,
            ) as cholesky,
            mock.patch(
                "rulespace_v3.spectral._scalar_lower_triangular_inverse",
                wraps=_scalar_lower_triangular_inverse,
            ) as triangular_inverse,
            mock.patch(
                "numpy.linalg.inv",
                side_effect=AssertionError("LAPACK inverse"),
            ),
            mock.patch(
                "numpy.linalg.cholesky",
                side_effect=AssertionError("LAPACK Cholesky"),
            ),
            mock.patch(
                "numpy.linalg.svd",
                side_effect=AssertionError("LAPACK SVD"),
            ),
            mock.patch(
                "numpy.linalg.eigh",
                side_effect=AssertionError("LAPACK eigh"),
            ),
        ):
            coverage = self._coverage()
        inverse.assert_called_once()
        cholesky.assert_called_once()
        triangular_inverse.assert_called_once()
        self.assertGreater(
            _decode_column(
                coverage.point_enclosures
                .inverse_residual_frobenius_upper_b64
            )[0],
            0.0,
        )
        self.assertGreater(
            _decode_column(
                coverage.point_enclosures
                .cholesky_factorization_residual_frobenius_upper_b64
            )[0],
            0.0,
        )

    def test_spectral_dot_uses_q_four_n_minus_one_and_directed_abs_sums(self):
        left = (1.0 + 2.0j, 3.0 + 4.0j)
        right = (5.0 + 6.0j, 7.0 + 8.0j)
        with (
            mock.patch(
                "rulespace_v3.spectral._spectral_ordered_complex_multiply",
                wraps=(
                    __import__(
                        "rulespace_v3.spectral",
                        fromlist=["_spectral_ordered_complex_multiply"],
                    )._spectral_ordered_complex_multiply
                ),
            ) as multiply,
            mock.patch(
                "rulespace_v3.spectral._spectral_ordered_complex_add",
                wraps=(
                    __import__(
                        "rulespace_v3.spectral",
                        fromlist=["_spectral_ordered_complex_add"],
                    )._spectral_ordered_complex_add
                ),
            ) as accumulate,
            mock.patch(
                "rulespace_v3.spectral.directed_mul_upper",
                wraps=(
                    __import__(
                        "rulespace_v3.spectral",
                        fromlist=["directed_mul_upper"],
                    ).directed_mul_upper
                ),
            ) as directed_multiply,
            mock.patch(
                "rulespace_v3.spectral.directed_add_upper",
                wraps=(
                    __import__(
                        "rulespace_v3.spectral",
                        fromlist=["directed_add_upper"],
                    ).directed_add_upper
                ),
            ) as directed_accumulate,
        ):
            _spectral_ordered_complex_dot_values(left, right)
        self.assertEqual(multiply.call_count, 2)
        self.assertEqual(accumulate.call_count, 1)
        self.assertEqual(directed_multiply.call_count, 8)
        self.assertEqual(directed_accumulate.call_count, 8)

    def test_cholesky_inverse_lower_requires_residual_strictly_below_one(self):
        with mock.patch(
            "rulespace_v3.spectral._matrix_product_subtraction_roundoff_upper",
            side_effect=(+0.0, +0.0, 2.0),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Cholesky inverse residual must be below one",
            ):
                self._coverage()

    def test_resigned_fill_sidecar_or_semantic_negative_zero_is_rejected(self):
        coverage = self._coverage()
        changed_fill = dataclasses.replace(
            coverage,
            fill_distance=+0.0,
            coverage_sha="0" * 64,
        )
        changed_fill = dataclasses.replace(
            changed_fill,
            coverage_sha=canonical_sha(
                spectral_margin_coverage_payload(changed_fill)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_spectral_margin_coverage(
                changed_fill,
                self.transition,
                self.metric,
            )

        sidecar = coverage.point_enclosures
        bad_column = base64.b64encode(struct.pack(">d", 2.0)).decode("ascii")
        changed_sidecar = dataclasses.replace(
            sidecar,
            m_sigma_min_lower_b64=bad_column,
            column_data_sha="0" * 64,
            sidecar_sha="0" * 64,
        )
        changed_sidecar = dataclasses.replace(
            changed_sidecar,
            column_data_sha=canonical_sha(
                {
                    "column_data_schema_version": (
                        "v3m0.spectral-column-data.v1"
                    ),
                    "ordered_columns": [
                        [name, getattr(changed_sidecar, name)]
                        for name in HARD_COLUMN_NAMES
                    ],
                }
            ),
        )
        changed_sidecar = dataclasses.replace(
            changed_sidecar,
            sidecar_sha=canonical_sha(
                spectral_point_sidecar_payload(changed_sidecar)
            ),
        )
        changed_coverage = dataclasses.replace(
            coverage,
            point_enclosures=changed_sidecar,
            coverage_sha="0" * 64,
        )
        changed_coverage = dataclasses.replace(
            changed_coverage,
            coverage_sha=canonical_sha(
                spectral_margin_coverage_payload(changed_coverage)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_spectral_margin_coverage(
                changed_coverage,
                self.transition,
                self.metric,
            )

        with self.assertRaises((TypeError, ValueError)):
            dataclasses.replace(
                coverage,
                m_sigma_min_coverage_increment=-0.0,
            )

    def test_raw_coverage_rejects_nested_grid_subclasses_and_wire_lists(self):
        coverage = self._coverage()

        @dataclasses.dataclass(frozen=True)
        class UnknownGrid(DynamicsKGridManifest):
            extra_unknown_field: str = "must-not-be-accepted"

        for field in (
            "qualification_grid",
            "spectral_diagnostic_grid",
        ):
            with self.subTest(field=field):
                forged_grid = UnknownGrid(
                    **{
                        item.name: getattr(
                            coverage.qualification_grid,
                            item.name,
                        )
                        for item in dataclasses.fields(
                            DynamicsKGridManifest
                        )
                    }
                )
                changed = dataclasses.replace(
                    coverage,
                    **{field: forged_grid},
                )
                self.assertEqual(changed.coverage_sha, coverage.coverage_sha)
                with self.assertRaises((TypeError, ValueError)):
                    verify_spectral_margin_coverage(
                        changed,
                        self.transition,
                        self.metric,
                    )

        for field in (
            "grid_m_sigma_min_lower",
            "m_sigma_min_axis_derivative_bounds",
        ):
            with self.subTest(field=field):
                forged = object.__new__(type(coverage))
                for item in dataclasses.fields(coverage):
                    object.__setattr__(
                        forged,
                        item.name,
                        getattr(coverage, item.name),
                    )
                object.__setattr__(
                    forged,
                    field,
                    list(getattr(coverage, field)),
                )
                self.assertEqual(
                    canonical_sha(spectral_margin_coverage_payload(forged)),
                    coverage.coverage_sha,
                )
                with self.assertRaises((TypeError, ValueError)):
                    verify_spectral_margin_coverage(
                        forged,
                        self.transition,
                        self.metric,
                    )

    def test_coverage_preflight_rejects_transition_subclass_before_property(self):
        class UnknownTransition(VerifiedTransition):
            @property
            def transition(self):
                raise AssertionError("subclass property executed")

        forged = object.__new__(UnknownTransition)
        with self.assertRaises(TypeError):
            verify_spectral_margin_coverage(
                self._coverage(),
                forged,
                self.metric,
            )

    def test_coverage_preflight_bounds_root64_and_schema_before_payload(self):
        coverage = self._coverage()
        protocol = coverage.fp64_enclosure_protocol
        table = protocol.root_interval_table

        changed_table = object.__new__(type(table))
        for item in dataclasses.fields(table):
            object.__setattr__(
                changed_table,
                item.name,
                getattr(table, item.name),
            )
        object.__setattr__(
            changed_table,
            "entries",
            table.entries + (table.entries[0],),
        )
        changed_protocol = object.__new__(type(protocol))
        for item in dataclasses.fields(protocol):
            object.__setattr__(
                changed_protocol,
                item.name,
                getattr(protocol, item.name),
            )
        object.__setattr__(
            changed_protocol,
            "root_interval_table",
            changed_table,
        )
        changed_coverage = dataclasses.replace(
            coverage,
            fp64_enclosure_protocol=changed_protocol,
        )

        forged_schema = object.__new__(type(coverage))
        for item in dataclasses.fields(coverage):
            object.__setattr__(
                forged_schema,
                item.name,
                getattr(coverage, item.name),
            )
        object.__setattr__(
            forged_schema,
            "coverage_schema_version",
            "x" * 65,
        )
        for forged in (changed_coverage, forged_schema):
            with self.subTest(forged=type(forged).__name__):
                with mock.patch(
                    "rulespace_v3.spectral.spectral_margin_coverage_payload",
                    side_effect=AssertionError("payload before preflight"),
                ) as payload:
                    with self.assertRaises((TypeError, ValueError)):
                        verify_spectral_margin_coverage(
                            forged,
                            self.transition,
                            self.metric,
                        )
                payload.assert_not_called()

    def test_verifiers_reject_unknown_in_memory_record_fields(self):
        coverage = self._coverage()
        object.__setattr__(
            coverage,
            "caller_toolchain",
            {"label": "forged"},
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_spectral_margin_coverage(
                coverage,
                self.transition,
                self.metric,
            )

        coverage = self._coverage()
        object.__setattr__(
            coverage.point_enclosures,
            "caller_toolchain",
            {"label": "forged"},
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_spectral_margin_coverage(
                coverage,
                self.transition,
                self.metric,
            )

        _, verified = self._normalized()
        object.__setattr__(
            verified.audit,
            "caller_toolchain",
            {"label": "forged"},
        )
        with self.assertRaises((TypeError, ValueError)):
            build_power_drift_audit(verified)

        _, verified = self._normalized()
        power = build_power_drift_audit(verified)
        object.__setattr__(
            power,
            "caller_toolchain",
            {"label": "forged"},
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_power_drift_audit(power, verified)

    def test_audit_wire_validation_precedes_canonical_hash(self):
        coverage, verified = self._normalized()
        normalized_raw = verified.audit
        object.__setattr__(normalized_raw, "audit_sha", "not-a-sha")
        with mock.patch(
            "rulespace_v3.spectral.canonical_sha",
            side_effect=AssertionError("hash before normalized wire gate"),
        ) as canonical:
            with self.assertRaises((TypeError, ValueError)):
                verify_normalized_metric_residual_audit(
                    normalized_raw,
                    self.metric_residual,
                    coverage,
                    self.transition,
                    self.metric,
                )
        canonical.assert_not_called()

        _, verified = self._normalized()
        power = build_power_drift_audit(verified)
        object.__setattr__(power, "audit_sha", "not-a-sha")
        with mock.patch(
            "rulespace_v3.spectral.canonical_sha",
            side_effect=AssertionError("hash before power wire gate"),
        ) as canonical:
            with self.assertRaises((TypeError, ValueError)):
                verify_power_drift_audit(power, verified)
        canonical.assert_not_called()

    def test_strict_base64_and_resource_preflight_fail_closed(self):
        coverage = self._coverage()
        with self.assertRaises((TypeError, ValueError)):
            dataclasses.replace(
                coverage.point_enclosures,
                m_sigma_min_lower_b64="not-base64!",
            )
        with mock.patch(
            "rulespace_v3.spectral.np.empty",
            side_effect=AssertionError("allocation must not occur"),
        ) as allocator:
            with self.assertRaises((TypeError, ValueError)):
                _preflight_spectral_resources(
                    point_count=262_145,
                    n_state=2,
                    encoded_column_count=14,
                )
            with self.assertRaises((TypeError, ValueError)):
                _preflight_spectral_resources(
                    point_count=1,
                    n_state=10_000,
                    encoded_column_count=14,
                )
        allocator.assert_not_called()

        forged = object.__new__(type(coverage))
        for item in dataclasses.fields(coverage):
            object.__setattr__(
                forged,
                item.name,
                getattr(coverage, item.name),
            )
        object.__setattr__(
            forged,
            "raw_diagnostic_unavailable_reason",
            "x" * 65,
        )
        with (
            mock.patch(
                "rulespace_v3.spectral.SPECTRAL_MAX_CANONICAL_BODY_BYTES",
                64,
            ),
            mock.patch(
                "rulespace_v3.spectral.canonical_sha",
                side_effect=AssertionError("hash before body preflight"),
            ) as canonical,
        ):
            with self.assertRaises(ValueError):
                verify_spectral_margin_coverage(
                    forged,
                    self.transition,
                    self.metric,
                )
        canonical.assert_not_called()

    def test_normalized_audit_rebuilds_complete_residual_and_coverage(self):
        coverage, verified = self._normalized()
        self.assertIsInstance(
            verified,
            VerifiedNormalizedMetricResidualAudit,
        )
        audit = verified.audit
        self.assertEqual(
            audit.metric_residual_sha,
            self.metric_residual.residual_sha,
        )
        self.assertEqual(
            audit.spectral_margin_coverage_sha,
            coverage.coverage_sha,
        )
        self.assertEqual(
            audit.raw_metric_residual_upper,
            self.metric_residual.raw_global_momentum_supremum_bound,
        )
        self.assertEqual(
            audit.covered_g_lambda_min_lower,
            coverage.covered_g_lambda_min_lower,
        )
        self.assertLessEqual(
            audit.normalized_metric_residual_upper,
            1e-12,
        )
        hydrated = verify_normalized_metric_residual_audit(
            audit,
            self.metric_residual,
            coverage,
            self.transition,
            self.metric,
        )
        self.assertEqual(hydrated.audit, audit)

        changed = dataclasses.replace(
            audit,
            normalized_metric_residual_upper=math.nextafter(
                audit.normalized_metric_residual_upper,
                math.inf,
            ),
            audit_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            audit_sha=canonical_sha(
                normalized_metric_residual_audit_payload(changed)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_normalized_metric_residual_audit(
                changed,
                self.metric_residual,
                coverage,
                self.transition,
                self.metric,
            )

        changed_residual = dataclasses.replace(
            self.metric_residual,
            raw_global_momentum_supremum_bound=(
                self.metric_residual.raw_global_momentum_supremum_bound
                * 0.5
            ),
            residual_sha="0" * 64,
        )
        changed_residual = dataclasses.replace(
            changed_residual,
            residual_sha=canonical_sha(
                laurent_residual_payload(changed_residual)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            certify_normalized_metric_residual_audit(
                changed_residual,
                coverage,
                self.transition,
                self.metric,
            )

    def test_power_audit_requires_live_verified_normalized_authority(self):
        _, verified = self._normalized()
        with (
            mock.patch("builtins.pow", side_effect=AssertionError("pow")),
            mock.patch("math.exp", side_effect=AssertionError("exp")),
        ):
            audit = build_power_drift_audit(verified)
        self.assertIsInstance(audit, PowerDriftAudit)
        self.assertEqual(
            audit.normalized_metric_residual_audit_sha,
            verified.audit.audit_sha,
        )
        self.assertEqual(audit.macro_step, 16384)
        self.assertEqual(audit.nonzero_delta_squaring_count, 14)
        self.assertEqual(audit.executed_squaring_count, 14)
        self.assertLessEqual(audit.drift_upper, 1e-8)
        self.assertEqual(
            verify_power_drift_audit(audit, verified),
            audit,
        )

        with self.assertRaises((TypeError, ValueError)):
            build_power_drift_audit(verified.audit)
        forged = object.__new__(VerifiedNormalizedMetricResidualAudit)
        with self.assertRaises((TypeError, ValueError)):
            build_power_drift_audit(forged)

        with self.assertRaises((TypeError, ValueError)):
            dataclasses.replace(
                audit,
                executed_squaring_count=13,
            )
        changed = dataclasses.replace(
            audit,
            growth_upper=math.nextafter(audit.growth_upper, math.inf),
            audit_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            audit_sha=canonical_sha(power_drift_audit_payload(changed)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_power_drift_audit(changed, verified)

    def test_power_audit_rejects_slot_mutation_of_exposed_normalized_raw(self):
        _, verified = self._normalized()
        self.assertGreater(
            verified.audit.normalized_metric_residual_upper,
            0.0,
        )
        object.__setattr__(
            verified.audit,
            "normalized_metric_residual_upper",
            +0.0,
        )
        with self.assertRaises((TypeError, ValueError)):
            build_power_drift_audit(verified)


if __name__ == "__main__":
    unittest.main()
