from __future__ import annotations

import ast
import base64
import inspect
import math
import struct
import unittest
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace
from unittest import mock

import numpy as np

import rulespace_v3.fp64 as fp64_module
import rulespace_v3.spectral as spectral
from rulespace_v3.calibration_authority import (
    build_c04_canonical_angle_recipe,
)
from rulespace_v3.dynamics import (
    MeasuredTransition,
    VerifiedTransition,
    measured_transition_payload,
    transition_support_payload,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor
from rulespace_v3.fp64_protocol import (
    build_fp64_enclosure_protocol,
    verify_fp64_enclosure_protocol,
)
from rulespace_v3.grids import (
    build_dynamics_grid_manifest,
    verify_dynamics_grid_manifest,
)
from rulespace_v3.metric import (
    METRIC_NORMALIZATION_ID,
    METRIC_ORIGIN_SCHEMA_VERSION,
    STABILITY_METRIC_SCHEMA_VERSION,
    MetricOriginManifest,
    StabilityMetricWitness,
    metric_origin_payload,
    metric_support_payload,
    stability_metric_witness_payload,
)


def _c04_laurent_coefficients() -> tuple[np.ndarray, tuple[tuple[int, ...], ...]]:
    """Compile the analytic C04 local shears without any live Parent."""

    recipe = build_c04_canonical_angle_recipe()
    channel_index = {
        channel: index for index, channel in enumerate(recipe.channel_order)
    }
    state_count = len(recipe.channel_order)
    coefficients = {
        0: np.eye(state_count, dtype=np.complex128),
    }
    for step in recipe.steps:
        generator = np.zeros(
            (state_count, state_count),
            dtype=np.complex128,
        )
        generator[
            channel_index[step.destination_channel],
            channel_index[step.source_channel],
        ] = step.coefficient
        updated = {exponent: matrix.copy() for exponent, matrix in coefficients.items()}
        for exponent, matrix in coefficients.items():
            shifted = exponent + step.offset[0]
            updated.setdefault(
                shifted,
                np.zeros(
                    (state_count, state_count),
                    dtype=np.complex128,
                ),
            )
            updated[shifted] += generator @ matrix
        coefficients = updated

    for exponent, matrix in coefficients.items():
        if exponent < -2 or exponent > 2:
            np.testing.assert_array_equal(matrix, np.zeros_like(matrix))
    support = tuple((offset,) for offset in range(-2, 3))
    # The recipe uses exp(+ik o), while the Laurent witness uses exp(-ik d).
    values = np.stack(
        tuple(coefficients[-offset] for (offset,) in support),
        axis=0,
    )
    return values, support


def _c04_raw_spectral_fixture():
    coefficients, support = _c04_laurent_coefficients()
    recipe = build_c04_canonical_angle_recipe()
    state_count = len(recipe.channel_order)
    spatial_shape = (5,)
    kernel = np.zeros(
        (state_count, state_count) + spatial_shape,
        dtype=np.complex128,
    )
    for coefficient, (offset,) in zip(coefficients, support):
        kernel[:, :, offset % spatial_shape[0]] = coefficient
    support_sha = canonical_sha(
        transition_support_payload(
            support,
            spatial_shape,
            recipe.channel_order,
            "channel-identity-v1",
        )
    )
    transition = MeasuredTransition(
        transition_schema_version="v3m0.measured-transition.v1",
        parent_freeze_sha="a" * 64,
        prestructure_authority_sha="b" * 64,
        factory_sha="c" * 64,
        factory_role="actual",
        state_schema_id="state.c04.spectral-golden.v1",
        channel_order=recipe.channel_order,
        spatial_shape=spatial_shape,
        dt=1.0,
        boundary_manifest_id="periodic-v1",
        state_basis_convention_id="channel-identity-v1",
        kernel=freeze_complex_tensor(kernel),
        support_offsets=support,
        support_sha=support_sha,
        macro_steps=1,
        transition_sha="0" * 64,
    )
    transition = replace(
        transition,
        transition_sha=canonical_sha(measured_transition_payload(transition)),
    )

    metric_support = ((0,),)
    metric_kernel = freeze_complex_tensor(
        np.eye(state_count, dtype=np.complex128)[None, :, :]
    )
    metric_support_sha = canonical_sha(metric_support_payload(metric_support))
    structure_sha = "d" * 64
    origin = MetricOriginManifest(
        origin_schema_version=METRIC_ORIGIN_SCHEMA_VERSION,
        origin_kind="synthetic-identity-v1",
        parent_freeze_sha="a" * 64,
        prestructure_authority_sha="b" * 64,
        factory_sha="c" * 64,
        structure_manifest_sha=structure_sha,
        evidence_lane="synthetic-classical",
        derivation_or_preregistration_sha="e" * 64,
        metric_kernel_sha=metric_kernel.tensor_sha,
        metric_support_sha=metric_support_sha,
        origin_sha="0" * 64,
    )
    origin = replace(
        origin,
        origin_sha=canonical_sha(metric_origin_payload(origin)),
    )
    metric = StabilityMetricWitness(
        witness_schema_version=STABILITY_METRIC_SCHEMA_VERSION,
        structure_manifest_sha=structure_sha,
        metric_kind="constant-state-v1",
        metric_kernel=metric_kernel,
        metric_support_offsets=metric_support,
        metric_support_sha=metric_support_sha,
        normalization_id=METRIC_NORMALIZATION_ID,
        positive_eigenvalue_floor=1.0,
        condition_number_max=1.0,
        metric_origin=origin,
        witness_sha="0" * 64,
    )
    metric = replace(
        metric,
        witness_sha=canonical_sha(stability_metric_witness_payload(metric)),
    )
    protocol = build_fp64_enclosure_protocol()
    grid = build_dynamics_grid_manifest(support, metric_support)
    return transition, metric, protocol, grid


class NonzeroSpectralScalarCandidateTests(unittest.TestCase):
    def test_legacy_public_export_surface_is_exactly_preserved(self) -> None:
        self.assertEqual(
            tuple(spectral.__all__),
            (
                "CANDIDATE_ALGORITHM_ID",
                "COLUMN_DATA_SCHEMA_VERSION",
                "COLUMN_ENCODING_ID",
                "DISTANCE_CONVENTION_ID",
                "DIVISION_METHOD_ID",
                "HARD_COLUMN_NAMES",
                "NORMALIZED_AUDIT_SCHEMA_VERSION",
                "NORMALIZED_METRIC_RESIDUAL_GATE",
                "POWER_DRIFT_AUDIT_SCHEMA_VERSION",
                "RAW_COLUMN_NAMES",
                "ROUNDING_METHOD_ID",
                "SPECTRAL_AVAILABLE_COLUMN_COUNT",
                "SPECTRAL_COVERAGE_SCHEMA_VERSION",
                "SPECTRAL_HARD_COLUMN_COUNT",
                "SPECTRAL_SIDECAR_SCHEMA_VERSION",
                "TORUS_DOMAIN_ID",
                "NormalizedMetricResidualAudit",
                "PowerDriftAudit",
                "SpectralMarginCoverage",
                "SpectralPointEnclosureColumnarSidecar",
                "VerifiedNormalizedMetricResidualAudit",
                "build_exact_zero_spectral_margin_coverage",
                "build_spectral_margin_coverage",
                "build_power_drift_audit",
                "certify_normalized_metric_residual_audit",
                "normalized_metric_residual_audit_payload",
                "power_drift_audit_payload",
                "spectral_margin_coverage_payload",
                "spectral_point_sidecar_payload",
                "verify_normalized_metric_residual_audit",
                "verify_power_drift_audit",
                "verify_spectral_margin_coverage",
            ),
        )

    def test_full64_raw_and_legacy_adapter_bodies_have_exact_goldens(
        self,
    ) -> None:
        transition, metric, protocol, grid = _c04_raw_spectral_fixture()
        raw_core = spectral._build_spectral_margin_coverage_from_raw
        raw_calls = 0

        def counted_raw_core(
            raw_transition,
            raw_metric,
            raw_protocol,
            *,
            dynamics_grid,
        ):
            nonlocal raw_calls
            raw_calls += 1
            return raw_core(
                raw_transition,
                raw_metric,
                raw_protocol,
                dynamics_grid=dynamics_grid,
            )

        transition_owner = object()
        metric_owner = object()
        factory = object()
        authority = object()
        structure = object()
        transition_view = SimpleNamespace(
            factory=factory,
            prestructure=authority,
            transition=transition,
        )

        def transition_reverifier(value):
            self.assertIs(value, transition_owner)
            return transition_view

        def structure_builder(owner_factory, owner_authority):
            self.assertEqual(
                (owner_factory, owner_authority),
                (factory, authority),
            )
            return structure

        def metric_verifier(
            value,
            owner_factory,
            owner_authority,
            owner_structure,
        ):
            self.assertEqual(
                (
                    value,
                    owner_factory,
                    owner_authority,
                    owner_structure,
                ),
                (metric_owner, factory, authority, structure),
            )
            return metric

        legacy_builder = spectral._make_legacy_spectral_margin_coverage_builder(
            counted_raw_core,
            required_profile="cartesian-full-64-v1",
            transition_reverifier=transition_reverifier,
            structure_builder=structure_builder,
            metric_verifier=metric_verifier,
            protocol_verifier=verify_fp64_enclosure_protocol,
            grid_builder=build_dynamics_grid_manifest,
            grid_verifier=verify_dynamics_grid_manifest,
        )
        with mock.patch(
            "numpy.linalg.svd",
            side_effect=ValueError("optional diagnostic unavailable"),
        ):
            raw = raw_core(
                transition,
                metric,
                protocol,
                dynamics_grid=grid,
            )
            legacy = legacy_builder(
                transition_owner,
                metric_owner,
                protocol,
            )

        self.assertEqual(raw_calls, 1)
        self.assertEqual(legacy, raw)
        self.assertEqual(
            spectral.spectral_margin_coverage_payload(legacy),
            spectral.spectral_margin_coverage_payload(raw),
        )
        self.assertEqual(
            spectral.spectral_point_sidecar_payload(legacy.point_enclosures),
            spectral.spectral_point_sidecar_payload(raw.point_enclosures),
        )
        self.assertEqual(
            raw.coverage_sha,
            "db6e515ab1cef62859cdfeec09dc02435f38a763435e14bfdff71f5ca013a250",
        )
        self.assertEqual(
            raw.point_enclosures.sidecar_sha,
            "fbb99846436f57e3b50cd3fb5c01756488286132b1780b795ff93b89deb6e10b",
        )

    def test_owner_neutral_raw_api_contract_is_private_and_exact(self) -> None:
        expected = {
            "_build_spectral_margin_coverage_from_raw": (
                "transition",
                "stability_metric",
                "fp64_protocol",
                "dynamics_grid",
            ),
            "_build_normalized_metric_residual_audit_from_raw": (
                "metric_residual",
                "spectral_margins",
            ),
            "_build_power_drift_audit_from_raw": ("normalized",),
        }
        for name, parameter_names in expected.items():
            self.assertTrue(hasattr(spectral, name), name)
            function = getattr(spectral, name)
            signature = inspect.signature(function)
            self.assertEqual(tuple(signature.parameters), parameter_names)
            self.assertNotIn(name, spectral.__all__)
        expected_annotations = {
            "_build_spectral_margin_coverage_from_raw": (
                (
                    "MeasuredTransition",
                    "StabilityMetricWitness",
                    "Fp64EnclosureProtocol",
                    "DynamicsKGridManifest",
                ),
                "SpectralMarginCoverage",
            ),
            "_build_normalized_metric_residual_audit_from_raw": (
                (
                    "LaurentResidualCertificate",
                    "SpectralMarginCoverage",
                ),
                "NormalizedMetricResidualAudit",
            ),
            "_build_power_drift_audit_from_raw": (
                ("NormalizedMetricResidualAudit",),
                "PowerDriftAudit",
            ),
        }
        for name, (
            parameter_annotations,
            return_annotation,
        ) in expected_annotations.items():
            signature = inspect.signature(getattr(spectral, name))
            self.assertEqual(
                tuple(
                    parameter.annotation for parameter in signature.parameters.values()
                ),
                parameter_annotations,
            )
            self.assertEqual(signature.return_annotation, return_annotation)
        coverage_signature = inspect.signature(
            spectral._build_spectral_margin_coverage_from_raw
        )
        self.assertIs(
            coverage_signature.parameters["dynamics_grid"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )

    def test_spectral_owner_neutral_core_has_no_parent_v3_import_edge(
        self,
    ) -> None:
        tree = ast.parse(inspect.getsource(spectral))
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        self.assertTrue(
            imported_modules.isdisjoint(
                {
                    "application_materialization_v3",
                    "certificate_v3",
                    "metric_support_authority_v1",
                    "parent_v3_application_prestructure",
                    "runtime_grids_v3",
                    "transition_authority_v3",
                }
            )
        )
        for lane in (
            spectral._build_exact_zero_spectral_margin_coverage_from_raw_lane,
            spectral._build_full64_spectral_margin_coverage_from_raw_lane,
        ):
            source = inspect.getsource(lane)
            self.assertNotIn("VerifiedTransition", source)
            self.assertNotIn("_reverify_verified_transition", source)

    def test_body_cap_checker_accepts_an_injected_low_cap(self) -> None:
        calls: list[int] = []

        def exact_size(payload, *, maximum_bytes):
            self.assertEqual(payload, {"body": "value"})
            calls.append(maximum_bytes)
            raise ValueError("canonical JSON resource cap exceeded")

        checker = spectral._make_coverage_body_cap_checker(
            maximum_bytes=64,
            exact_size=exact_size,
            payload_builder=lambda coverage: {"body": coverage},
        )
        with self.assertRaisesRegex(
            ValueError,
            "spectral canonical body exceeds",
        ):
            checker("value")
        self.assertEqual(calls, [64])

    def test_raw_dispatcher_selects_both_profiles_from_the_provided_grid(
        self,
    ) -> None:
        events: list[tuple[str, object]] = []
        transition = object()
        metric = object()
        protocol = object()

        def verify_methods():
            events.append(("methods", None))

        def validate_inputs(raw_transition, raw_metric, raw_protocol, grid):
            self.assertIs(raw_transition, transition)
            self.assertIs(raw_metric, metric)
            self.assertIs(raw_protocol, protocol)
            events.append(("validate", grid))
            return grid

        def exact_zero_lane(
            raw_transition,
            raw_metric,
            raw_protocol,
            *,
            dynamics_grid,
        ):
            self.assertEqual(
                (raw_transition, raw_metric, raw_protocol),
                (transition, metric, protocol),
            )
            events.append(("exact-zero", dynamics_grid))
            return "exact-result"

        def full64_lane(
            raw_transition,
            raw_metric,
            raw_protocol,
            *,
            dynamics_grid,
        ):
            self.assertEqual(
                (raw_transition, raw_metric, raw_protocol),
                (transition, metric, protocol),
            )
            events.append(("full64", dynamics_grid))
            return "full64-result"

        dispatcher = spectral._make_spectral_margin_coverage_from_raw_dispatcher(
            validate_inputs=validate_inputs,
            exact_zero_lane=exact_zero_lane,
            full64_lane=full64_lane,
            method_closure_verifier=verify_methods,
        )
        exact_grid = SimpleNamespace(qualification_profile="exact-offset-zero-v1")
        full64_grid = SimpleNamespace(qualification_profile="cartesian-full-64-v1")
        self.assertEqual(
            dispatcher(
                transition,
                metric,
                protocol,
                dynamics_grid=exact_grid,
            ),
            "exact-result",
        )
        self.assertEqual(
            dispatcher(
                transition,
                metric,
                protocol,
                dynamics_grid=full64_grid,
            ),
            "full64-result",
        )
        self.assertEqual(
            events,
            [
                ("methods", None),
                ("validate", exact_grid),
                ("exact-zero", exact_grid),
                ("methods", None),
                ("validate", full64_grid),
                ("full64", full64_grid),
            ],
        )

    def test_legacy_coverage_builder_joins_before_one_raw_call(self) -> None:
        events: list[str] = []
        transition = object()
        metric = object()
        protocol = object()
        raw_transition = SimpleNamespace(
            support_offsets=((-1,), (0,), (1,)),
        )
        verified_metric = SimpleNamespace(metric_support_offsets=((0,),))
        verified_protocol = object()
        grid = SimpleNamespace(qualification_profile="cartesian-full-64-v1")
        view = SimpleNamespace(
            factory="factory",
            prestructure="prestructure",
            transition=raw_transition,
        )

        def transition_reverifier(value):
            self.assertIs(value, transition)
            events.append("transition")
            return view

        def structure_builder(factory, authority):
            self.assertEqual((factory, authority), ("factory", "prestructure"))
            events.append("structure")
            return "structure-body"

        def metric_verifier(value, factory, authority, structure):
            self.assertEqual(
                (value, factory, authority, structure),
                (metric, "factory", "prestructure", "structure-body"),
            )
            events.append("metric")
            return verified_metric

        def protocol_verifier(value):
            self.assertIs(value, protocol)
            events.append("protocol")
            return verified_protocol

        def grid_builder(transition_support, metric_support):
            self.assertEqual(
                (transition_support, metric_support),
                (raw_transition.support_offsets, ((0,),)),
            )
            events.append("grid-build")
            return grid

        def grid_verifier(value, transition_support, metric_support):
            self.assertIs(value, grid)
            self.assertEqual(
                (transition_support, metric_support),
                (raw_transition.support_offsets, ((0,),)),
            )
            events.append("grid-verify")
            return value

        def raw_builder(
            raw,
            raw_metric,
            raw_protocol,
            *,
            dynamics_grid,
        ):
            self.assertEqual(
                (raw, raw_metric, raw_protocol, dynamics_grid),
                (raw_transition, verified_metric, verified_protocol, grid),
            )
            events.append("raw")
            return "coverage"

        builder = spectral._make_legacy_spectral_margin_coverage_builder(
            raw_builder,
            required_profile="cartesian-full-64-v1",
            transition_reverifier=transition_reverifier,
            structure_builder=structure_builder,
            metric_verifier=metric_verifier,
            protocol_verifier=protocol_verifier,
            grid_builder=grid_builder,
            grid_verifier=grid_verifier,
        )
        self.assertEqual(builder(transition, metric, protocol), "coverage")
        self.assertEqual(
            events,
            [
                "transition",
                "structure",
                "metric",
                "protocol",
                "grid-build",
                "grid-verify",
                "raw",
            ],
        )

    def test_legacy_normalized_and_power_builders_delegate_once(self) -> None:
        normalized_events: list[str] = []
        transition = object()
        metric = object()
        metric_residual = object()
        margins = object()
        view = SimpleNamespace(factory="factory", prestructure="prestructure")
        coverage = SimpleNamespace(fp64_enclosure_protocol="protocol")

        def transition_reverifier(value):
            self.assertIs(value, transition)
            normalized_events.append("transition")
            return view

        def structure_builder(factory, authority):
            self.assertEqual((factory, authority), ("factory", "prestructure"))
            normalized_events.append("structure")
            return "structure"

        def metric_verifier(value, factory, authority, structure):
            self.assertEqual(
                (value, factory, authority, structure),
                (metric, "factory", "prestructure", "structure"),
            )
            normalized_events.append("metric")
            return "verified-metric"

        def coverage_verifier(value, owner, verified_metric):
            self.assertEqual(
                (value, owner, verified_metric),
                (margins, transition, "verified-metric"),
            )
            normalized_events.append("coverage")
            return coverage

        def residual_verifier(
            value,
            owner,
            structure,
            verified_metric,
            fp64_protocol,
        ):
            self.assertEqual(
                (value, owner, structure, verified_metric, fp64_protocol),
                (
                    metric_residual,
                    transition,
                    "structure",
                    "verified-metric",
                    "protocol",
                ),
            )
            normalized_events.append("residual")
            return "verified-residual"

        def normalized_raw(value, spectral_margins):
            self.assertEqual(
                (value, spectral_margins),
                ("verified-residual", coverage),
            )
            normalized_events.append("raw")
            return "normalized"

        normalized_builder = spectral._make_legacy_normalized_audit_builder(
            normalized_raw,
            transition_reverifier=transition_reverifier,
            structure_builder=structure_builder,
            metric_verifier=metric_verifier,
            coverage_verifier=coverage_verifier,
            residual_verifier=residual_verifier,
        )
        self.assertEqual(
            normalized_builder(metric_residual, margins, transition, metric),
            "normalized",
        )
        self.assertEqual(
            normalized_events,
            [
                "transition",
                "structure",
                "metric",
                "coverage",
                "residual",
                "raw",
            ],
        )

        power_events: list[str] = []
        normalized = object()

        def normalized_reverifier(value):
            self.assertIs(value, normalized)
            power_events.append("normalized")
            return SimpleNamespace(audit="normalized-body")

        def power_raw(value):
            self.assertEqual(value, "normalized-body")
            power_events.append("raw")
            return "power"

        power_builder = spectral._make_legacy_power_drift_audit_builder(
            power_raw,
            normalized_reverifier=normalized_reverifier,
        )
        self.assertEqual(power_builder(normalized), "power")
        self.assertEqual(power_events, ["normalized", "raw"])

    def test_production_legacy_wrappers_capture_canonical_raw_callable(
        self,
    ) -> None:
        expected_bindings = (
            (
                spectral._expected_exact_zero_coverage,
                spectral._build_spectral_margin_coverage_from_raw,
            ),
            (
                spectral._expected_nonzero_coverage,
                spectral._build_spectral_margin_coverage_from_raw,
            ),
            (
                spectral._expected_normalized_audit,
                spectral._build_normalized_metric_residual_audit_from_raw,
            ),
            (
                spectral._expected_power_drift_audit,
                spectral._build_power_drift_audit_from_raw,
            ),
        )
        for wrapper, raw_core in expected_bindings:
            with self.subTest(wrapper=wrapper.__name__):
                captured = tuple(
                    cell.cell_contents for cell in (wrapper.__closure__ or ())
                )
                self.assertIn(raw_core, captured)

    def test_saved_power_raw_core_ignores_post_freeze_global_redirect(
        self,
    ) -> None:
        normalized = spectral.NormalizedMetricResidualAudit(
            audit_schema_version=spectral.NORMALIZED_AUDIT_SCHEMA_VERSION,
            metric_residual_sha="1" * 64,
            spectral_margin_coverage_sha="2" * 64,
            raw_metric_residual_upper=+0.0,
            covered_g_lambda_min_lower=1.0,
            division_method_id=spectral.DIVISION_METHOD_ID,
            normalized_metric_residual_upper=+0.0,
            audit_sha="3" * 64,
        )
        saved = spectral._build_power_drift_audit_from_raw
        expected = saved(normalized)
        for target_name in (
            "compute_power_drift_bounds",
            "canonical_sha",
            "replace",
            "type",
        ):
            with self.subTest(target_name=target_name):
                redirected = mock.Mock(
                    side_effect=AssertionError("redirected power helper")
                )
                with mock.patch.object(
                    spectral,
                    target_name,
                    redirected,
                    create=True,
                ):
                    observed = saved(normalized)
                self.assertEqual(observed, expected)
                redirected.assert_not_called()
        post_init_redirect = mock.Mock(
            side_effect=AssertionError("redirected PowerDriftAudit post-init")
        )
        with mock.patch.object(
            spectral.PowerDriftAudit,
            "__post_init__",
            post_init_redirect,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "dataclass dependency drifted",
            ):
                saved(normalized)
        post_init_redirect.assert_not_called()

    def test_saved_power_raw_core_ignores_private_power_builder_redirect(
        self,
    ) -> None:
        normalized = spectral.NormalizedMetricResidualAudit(
            audit_schema_version=spectral.NORMALIZED_AUDIT_SCHEMA_VERSION,
            metric_residual_sha="1" * 64,
            spectral_margin_coverage_sha="2" * 64,
            raw_metric_residual_upper=1.0e-16,
            covered_g_lambda_min_lower=1.0,
            division_method_id=spectral.DIVISION_METHOD_ID,
            normalized_metric_residual_upper=1.0e-16,
            audit_sha="3" * 64,
        )
        saved = spectral._build_power_drift_audit_from_raw
        expected = saved(normalized)
        redirected = mock.Mock(
            side_effect=AssertionError("redirected private power builder")
        )
        range_redirect = mock.Mock(
            side_effect=AssertionError("redirected private range")
        )
        max_redirect = mock.Mock(side_effect=AssertionError("redirected private max"))
        with (
            mock.patch.object(
                fp64_module,
                "_build_power_values",
                redirected,
            ),
            mock.patch.object(
                fp64_module,
                "range",
                range_redirect,
                create=True,
            ),
            mock.patch.object(
                fp64_module,
                "max",
                max_redirect,
                create=True,
            ),
        ):
            observed = saved(normalized)
        self.assertEqual(observed, expected)
        redirected.assert_not_called()
        range_redirect.assert_not_called()
        max_redirect.assert_not_called()

    def test_saved_power_raw_core_fails_closed_before_foreign_init_redirect(
        self,
    ) -> None:
        normalized = spectral.NormalizedMetricResidualAudit(
            audit_schema_version=spectral.NORMALIZED_AUDIT_SCHEMA_VERSION,
            metric_residual_sha="1" * 64,
            spectral_margin_coverage_sha="2" * 64,
            raw_metric_residual_upper=1.0e-16,
            covered_g_lambda_min_lower=1.0,
            division_method_id=spectral.DIVISION_METHOD_ID,
            normalized_metric_residual_upper=1.0e-16,
            audit_sha="3" * 64,
        )
        saved = spectral._build_power_drift_audit_from_raw
        saved(normalized)
        redirected = mock.Mock(
            side_effect=AssertionError("redirected foreign constructor")
        )
        with mock.patch.object(
            fp64_module.PowerDriftBounds,
            "__init__",
            redirected,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "fp64 owner dependency drifted",
            ):
                saved(normalized)
        redirected.assert_not_called()

    def test_power_guard_rejects_chameleon_init_descriptor_statically(
        self,
    ) -> None:
        normalized = spectral.NormalizedMetricResidualAudit(
            audit_schema_version=spectral.NORMALIZED_AUDIT_SCHEMA_VERSION,
            metric_residual_sha="1" * 64,
            spectral_margin_coverage_sha="2" * 64,
            raw_metric_residual_upper=1.0e-16,
            covered_g_lambda_min_lower=1.0,
            division_method_id=spectral.DIVISION_METHOD_ID,
            normalized_metric_residual_upper=1.0e-16,
            audit_sha="3" * 64,
        )
        saved = spectral._build_power_drift_audit_from_raw
        original_init = inspect.getattr_static(
            fp64_module.PowerDriftBounds,
            "__init__",
        )
        redirected = mock.Mock(
            side_effect=AssertionError("chameleon constructor executed")
        )

        class ChameleonInit:
            def __get__(self, instance, owner):
                if instance is None:
                    return original_init

                def hostile_bound(*args, **kwargs):
                    return redirected(instance, *args, **kwargs)

                return hostile_bound

        with mock.patch.object(
            fp64_module.PowerDriftBounds,
            "__init__",
            ChameleonInit(),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "fp64 owner dependency drifted",
            ):
                saved(normalized)
        redirected.assert_not_called()

    def test_power_guard_authority_cannot_be_cleared_before_init_attack(
        self,
    ) -> None:
        normalized = spectral.NormalizedMetricResidualAudit(
            audit_schema_version=spectral.NORMALIZED_AUDIT_SCHEMA_VERSION,
            metric_residual_sha="1" * 64,
            spectral_margin_coverage_sha="2" * 64,
            raw_metric_residual_upper=1.0e-16,
            covered_g_lambda_min_lower=1.0,
            division_method_id=spectral.DIVISION_METHOD_ID,
            normalized_metric_residual_upper=1.0e-16,
            audit_sha="3" * 64,
        )
        saved = spectral._build_power_drift_audit_from_raw
        holder = spectral._FP64_POWER_BOUNDS_METHOD_CLOSURE
        dependencies = getattr(holder, "_dependencies", None)
        resolutions = getattr(holder, "_resolutions", None)
        authority_cleared = False
        try:
            try:
                object.__setattr__(holder, "_dependencies", ())
                object.__setattr__(holder, "_resolutions", ())
                authority_cleared = True
            except (AttributeError, TypeError):
                pass
            redirected = mock.Mock(
                side_effect=AssertionError("unguarded constructor executed")
            )
            with mock.patch.object(
                fp64_module.PowerDriftBounds,
                "__init__",
                redirected,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "fp64 owner dependency drifted",
                ):
                    saved(normalized)
            redirected.assert_not_called()
        finally:
            if authority_cleared:
                object.__setattr__(holder, "_dependencies", dependencies)
                object.__setattr__(holder, "_resolutions", resolutions)

    def test_saved_legacy_builders_ignore_post_freeze_global_redirect(
        self,
    ) -> None:
        cases = (
            (
                spectral.build_exact_zero_spectral_margin_coverage,
                "_expected_exact_zero_coverage",
                (object(), object(), object()),
            ),
            (
                spectral.build_spectral_margin_coverage,
                "_expected_spectral_margin_coverage",
                (object(), object(), object()),
            ),
            (
                spectral.build_power_drift_audit,
                "_expected_power_drift_audit",
                (object(),),
            ),
        )
        for saved, target_name, args in cases:
            with self.subTest(target_name=target_name):
                redirected = mock.Mock(return_value=object())
                with mock.patch.object(spectral, target_name, redirected):
                    with self.assertRaises((TypeError, ValueError)):
                        saved(*args)
                redirected.assert_not_called()

        expected_redirect = mock.Mock(return_value=object())
        issue_redirect = mock.Mock(return_value=object())
        saved_certifier = spectral.certify_normalized_metric_residual_audit
        with (
            mock.patch.object(
                spectral,
                "_expected_normalized_audit",
                expected_redirect,
            ),
            mock.patch.object(
                spectral,
                "_issue_verified_normalized_audit",
                issue_redirect,
            ),
        ):
            with self.assertRaises((TypeError, ValueError)):
                saved_certifier(object(), object(), object(), object())
        expected_redirect.assert_not_called()
        issue_redirect.assert_not_called()

    def test_public_builder_rejects_dead_opaque_before_redirected_lanes(
        self,
    ) -> None:
        transition = object.__new__(VerifiedTransition)
        object.__setattr__(
            transition,
            "_VerifiedTransition__transition",
            SimpleNamespace(support_offsets=((-1,), (0,), (1,))),
        )
        metric = object.__new__(StabilityMetricWitness)
        object.__setattr__(metric, "metric_support_offsets", ((0,),))
        protocol = object()
        with (
            mock.patch.object(
                spectral,
                "_expected_nonzero_coverage",
                return_value=object(),
            ) as nonzero,
            mock.patch.object(
                spectral,
                "_expected_exact_zero_coverage",
                return_value=object(),
            ) as exact_zero,
        ):
            with self.assertRaises((TypeError, ValueError)):
                spectral.build_spectral_margin_coverage(
                    transition,
                    metric,
                    protocol,
                )
        nonzero.assert_not_called()
        exact_zero.assert_not_called()

    def test_scalar_gauss_jordan_supports_general_complex_matrices(self) -> None:
        matrix = np.asarray(
            (
                (1.0 + 0.0j, 0.0 + 0.25j),
                (0.0 - 0.25j, 1.0 + 0.0j),
            ),
            dtype=np.complex128,
        )
        inverse = spectral._scalar_gauss_jordan_inverse(matrix)
        self.assertLessEqual(
            float(np.linalg.norm(inverse @ matrix - np.eye(2), ord="fro")),
            2.0e-15,
        )

    def test_scalar_cholesky_supports_general_hermitian_positive_metric(
        self,
    ) -> None:
        metric = np.asarray(
            (
                (1.0 + 0.0j, 0.0 + 0.25j),
                (0.0 - 0.25j, 1.0 + 0.0j),
            ),
            dtype=np.complex128,
        )
        factor = spectral._scalar_hermitian_cholesky(metric)
        inverse = spectral._scalar_lower_triangular_inverse(factor)
        self.assertLessEqual(
            float(np.linalg.norm(factor @ factor.conj().T - metric, ord="fro")),
            2.0e-15,
        )
        self.assertLessEqual(
            float(np.linalg.norm(inverse @ factor - np.eye(2), ord="fro")),
            2.0e-15,
        )

    def test_root64_symbol_witness_uses_table_center_without_runtime_trig(
        self,
    ) -> None:
        protocol = build_fp64_enclosure_protocol()
        # M(k)=Σ_d K_d exp(-ikd), so d=+1 at n=8 uses root -8 mod 64.
        entry = protocol.root_interval_table.entries[56]
        expected = complex(
            struct.unpack(">d", struct.pack(">Q", entry.real_center_f64_bits))[0],
            struct.unpack(">d", struct.pack(">Q", entry.imag_center_f64_bits))[0],
        )
        identity = np.eye(2, dtype=np.complex128)[None, :, :]
        with (
            mock.patch("math.sin", side_effect=AssertionError("runtime sin")),
            mock.patch("math.cos", side_effect=AssertionError("runtime cos")),
            mock.patch("math.exp", side_effect=AssertionError("runtime exp")),
        ):
            center, error = spectral._laurent_symbol_center_and_error(
                identity,
                ((1,),),
                (8,),
                protocol,
            )
        np.testing.assert_array_equal(center, expected * np.eye(2))
        self.assertGreater(error, 0.0)

    def test_nonzero_hard_point_uses_no_lapack_and_has_positive_margins(
        self,
    ) -> None:
        protocol = build_fp64_enclosure_protocol()
        identity = np.eye(2, dtype=np.complex128)[None, :, :]
        with (
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
            point, _, _ = spectral._hard_spectral_point(
                identity,
                ((1,),),
                identity,
                ((0,),),
                (8,),
                protocol,
            )
        self.assertEqual(set(point), set(spectral.HARD_COLUMN_NAMES))
        self.assertTrue(all(math.isfinite(value) for value in point.values()))
        self.assertGreater(point["transition_symbol_error_upper_b64"], 0.0)
        self.assertGreater(point["metric_symbol_error_upper_b64"], 0.0)
        self.assertGreater(point["m_sigma_min_lower_b64"], 0.0)
        self.assertGreater(point["g_lambda_min_lower_b64"], 0.0)

    def test_nonzero_builder_does_not_retain_point_candidate_matrices(
        self,
    ) -> None:
        source = inspect.getsource(
            spectral._build_full64_spectral_margin_coverage_from_raw_lane
        )
        self.assertNotIn("transition_centers", source)
        self.assertNotIn("metric_centers", source)
        self.assertNotIn("list[np.ndarray]", source)
        self.assertIn("for reciprocal_index in grid.reciprocal_indices", source)

    def test_unavailable_optional_diagnostics_emit_exactly_fourteen_columns(
        self,
    ) -> None:
        identity = np.eye(2, dtype=np.complex128)
        with mock.patch(
            "numpy.linalg.svd",
            side_effect=ValueError("diagnostic unavailable"),
        ):
            self.assertIsNone(
                spectral._optional_raw_point_diagnostic(identity, identity)
            )
        grid = build_dynamics_grid_manifest(((1,),), ((0,),))
        sidecar = spectral._build_columnar_sidecar(
            grid=grid,
            n_state=2,
            hard_columns={name: (1.0,) * 64 for name in spectral.HARD_COLUMN_NAMES},
            raw_columns=None,
            unavailable_reason="lapack-diagnostics-unavailable-v1",
        )
        self.assertEqual(sidecar.raw_diagnostic_status, "unavailable-v1")
        self.assertEqual(
            sidecar.raw_byte_count,
            64 * 8 * spectral.SPECTRAL_HARD_COLUMN_COUNT,
        )

    def test_parent_independent_c04_full64_hard_margins_and_columns(
        self,
    ) -> None:
        coefficients, support = _c04_laurent_coefficients()
        metric_coefficients = np.eye(4, dtype=np.complex128)[None, :, :]
        metric_support = ((0,),)
        protocol = build_fp64_enclosure_protocol()
        grid = build_dynamics_grid_manifest(support, metric_support)
        self.assertEqual(grid.qualification_profile, "cartesian-full-64-v1")
        self.assertEqual(grid.torus_denominators, (64,))
        self.assertEqual(
            grid.reciprocal_indices,
            tuple((index,) for index in range(64)),
        )

        points = []
        with (
            mock.patch("math.sin", side_effect=AssertionError("runtime sin")),
            mock.patch("math.cos", side_effect=AssertionError("runtime cos")),
            mock.patch("math.exp", side_effect=AssertionError("runtime exp")),
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
                "numpy.linalg.eigvalsh",
                side_effect=AssertionError("LAPACK eigvalsh"),
            ),
            mock.patch(
                "numpy.linalg.eigvals",
                side_effect=AssertionError("LAPACK eigvals"),
            ),
        ):
            for reciprocal_index in grid.reciprocal_indices:
                point, _, _ = spectral._hard_spectral_point(
                    coefficients,
                    support,
                    metric_coefficients,
                    metric_support,
                    reciprocal_index,
                    protocol,
                )
                points.append(point)
        self.assertEqual(len(points), 64)
        self.assertTrue(
            all(set(point) == set(spectral.HARD_COLUMN_NAMES) for point in points)
        )

        hard_columns = {
            name: tuple(point[name] for point in points)
            for name in spectral.HARD_COLUMN_NAMES
        }
        m_derivative = spectral._axis_derivative_bounds(
            coefficients,
            support,
        )
        g_derivative = spectral._axis_derivative_bounds(
            metric_coefficients,
            metric_support,
        )
        table = protocol.root_interval_table
        fill = spectral._fraction_upper_float(
            Fraction(
                table.pi_upper_numerator,
                (1 << table.dyadic_exponent) * 64,
            ),
            "test fill",
        )
        m_increment = spectral._coverage_increment(fill, m_derivative)
        g_increment = spectral._coverage_increment(fill, g_derivative)
        covered_m_min = spectral.directed_sub_lower(
            min(hard_columns["m_sigma_min_lower_b64"]),
            m_increment,
        )
        covered_m_max = spectral.directed_add_upper(
            max(hard_columns["m_sigma_max_upper_b64"]),
            m_increment,
        )
        covered_g_min = spectral.directed_sub_lower(
            min(hard_columns["g_lambda_min_lower_b64"]),
            g_increment,
        )
        covered_g_max = spectral.directed_add_upper(
            max(hard_columns["g_lambda_max_upper_b64"]),
            g_increment,
        )
        m_condition = spectral.directed_div_upper(
            covered_m_max,
            covered_m_min,
        )
        g_condition = spectral.directed_div_upper(
            covered_g_max,
            covered_g_min,
        )
        self.assertAlmostEqual(
            min(hard_columns["m_sigma_min_lower_b64"]),
            0.5,
            delta=2.0e-14,
        )
        self.assertAlmostEqual(m_derivative[0], 3.322007801916572, places=14)
        self.assertAlmostEqual(m_increment, 0.16306867665107944, places=14)
        self.assertAlmostEqual(covered_m_min, 0.3369313233489113, places=14)
        self.assertAlmostEqual(m_condition, 6.419909716767732, places=13)
        self.assertEqual(g_derivative, (+0.0,))
        self.assertEqual(g_increment, +0.0)
        self.assertAlmostEqual(covered_g_min, 0.25, delta=8.0e-15)
        self.assertAlmostEqual(g_condition, 8.0, delta=2.0e-13)
        self.assertGreaterEqual(
            covered_m_min,
            spectral.SPECTRAL_M_SIGMA_MIN_GATE,
        )
        self.assertLessEqual(m_condition, spectral.SPECTRAL_CONDITION_MAX)
        self.assertGreaterEqual(
            covered_g_min,
            spectral.SPECTRAL_G_LAMBDA_MIN_GATE,
        )
        self.assertLessEqual(g_condition, spectral.SPECTRAL_CONDITION_MAX)

        unavailable = spectral._build_columnar_sidecar(
            grid=grid,
            n_state=4,
            hard_columns=hard_columns,
            raw_columns=None,
            unavailable_reason="lapack-diagnostics-unavailable-v1",
        )
        self.assertEqual(
            unavailable.raw_byte_count,
            64 * 8 * spectral.SPECTRAL_HARD_COLUMN_COUNT,
        )
        for name in spectral.HARD_COLUMN_NAMES:
            column = getattr(unavailable, name)
            self.assertEqual(len(base64.b64decode(column, validate=True)), 64 * 8)

        available = spectral._build_columnar_sidecar(
            grid=grid,
            n_state=4,
            hard_columns=hard_columns,
            raw_columns={name: (+1.0,) * 64 for name in spectral.RAW_COLUMN_NAMES},
            unavailable_reason=None,
        )
        self.assertEqual(
            available.raw_byte_count,
            64 * 8 * spectral.SPECTRAL_AVAILABLE_COLUMN_COUNT,
        )


if __name__ == "__main__":
    unittest.main()
