from __future__ import annotations

import builtins
import dataclasses
import inspect
import unittest
from fractions import Fraction
from unittest import mock

import numpy as np

import rulespace_v3.laurent as laurent_module
import rulespace_v3.fp64 as fp64_module
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.dynamics import measure_transition
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array
from rulespace_v3.fp64_protocol import build_fp64_enclosure_protocol
from rulespace_v3.laurent import (
    _coefficient_frobenius_upper_sum,
    _ordered_complex_add,
    _ordered_complex_dot_values,
    _ordered_complex_multiply,
    _preflight_convolution,
    _preflight_convolution_chain,
    _scalar_convolve,
    _zero_errors,
    certify_laurent_residuals,
    laurent_residual_payload,
    verify_laurent_residual_certificate,
)
from rulespace_v3.metric import build_stability_metric_witness
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.registry import build_closed_control_registry
from rulespace_v3.structure import build_structure_manifest
from tests.test_v3m0_dynamics import _quarter_turn_controls


_LEGACY_LAURENT_ALL = (
    "FOURIER_CONVENTION_ID",
    "LAURENT_MAX_ARITHMETIC_WORK",
    "LAURENT_MAX_COEFFICIENT_ENTRIES",
    "LAURENT_MAX_PAIR_PRODUCT",
    "LAURENT_MAX_SUPPORT",
    "LAURENT_RESIDUAL_SCHEMA_VERSION",
    "MATRIX_NORM_ID",
    "MOMENTUM_SUPREMUM_METHOD_ID",
    "LaurentResidualCertificate",
    "certify_laurent_residuals",
    "laurent_residual_payload",
    "verify_laurent_residual_certificate",
)


class LaurentPrimitiveClosureTests(unittest.TestCase):
    def test_owner_neutral_cores_have_private_builtins(self):
        for core in (
            laurent_module._preflight_laurent_resources_from_raw,
            laurent_module._build_laurent_residual_from_raw,
        ):
            with self.subTest(core=core.__name__):
                self.assertIsNot(
                    core.__globals__["__builtins__"],
                    builtins.__dict__,
                )


class LaurentResidualTests(unittest.TestCase):
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
        cls.authority = issue_synthetic_prestructure_authority(
            cls.parent,
            cls.registry,
            "full",
            cls.construction,
            "actual",
        )
        cls.factory = cls.construction.pair.actual
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

    def test_two_raw_laurent_residuals_are_mechanical_and_small(self):
        structure_residual, metric_residual = certify_laurent_residuals(
            self.transition,
            self.structure,
            self.metric,
            self.protocol,
        )
        self.assertEqual(structure_residual.residual_kind, "canonical-structure")
        self.assertEqual(metric_residual.residual_kind, "stability-metric")
        self.assertEqual(
            structure_residual.operand_shas,
            (
                self.transition.transition.transition_sha,
                self.structure.structure_manifest_sha,
                self.structure.structure_form.tensor_sha,
            ),
        )
        self.assertEqual(
            metric_residual.operand_shas,
            (
                self.transition.transition.transition_sha,
                self.metric.witness_sha,
                self.metric.metric_kernel.tensor_sha,
            ),
        )
        for residual in (structure_residual, metric_residual):
            self.assertEqual(residual.support_offsets, ((0,),))
            coefficients = frozen_tensor_array(residual.coefficients)
            np.testing.assert_array_equal(coefficients, 0.0)
            self.assertEqual(residual.convolution_pair_counts, (1, 1))
            self.assertLessEqual(
                residual.raw_global_momentum_supremum_bound,
                1e-12,
            )
            self.assertEqual(
                residual.fp64_enclosure_protocol_sha,
                self.protocol.protocol_sha,
            )
            self.assertEqual(
                verify_laurent_residual_certificate(
                    residual,
                    self.transition,
                    self.structure,
                    self.metric,
                    self.protocol,
                ),
                residual,
            )

    def test_owner_neutral_raw_cores_match_legacy_and_are_private(self):
        raw_transition = self.transition.transition
        self.assertIsNone(
            laurent_module._preflight_laurent_resources_from_raw(
                raw_transition,
                self.metric,
            )
        )
        expected = certify_laurent_residuals(
            self.transition,
            self.structure,
            self.metric,
            self.protocol,
        )
        observed = tuple(
            laurent_module._build_laurent_residual_from_raw(
                raw_transition,
                self.structure,
                self.metric,
                protocol=self.protocol,
                kind=kind,
            )
            for kind in ("canonical-structure", "stability-metric")
        )
        self.assertEqual(observed, expected)
        self.assertEqual(
            tuple(residual.residual_sha for residual in expected),
            (
                "9d81a1fb8c7d9fed3b660738f211e4eed575ebcd2394c14ee59cc101d8860ae1",
                "f62f237b5d1b70c4a80f2cf510bdc7dd21b7d998968c81576a05420dd631048e",
            ),
        )
        preflight_signature = inspect.signature(
            laurent_module._preflight_laurent_resources_from_raw
        )
        self.assertEqual(
            tuple(preflight_signature.parameters),
            ("transition", "stability_metric"),
        )
        self.assertTrue(
            all(
                parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
                for parameter in preflight_signature.parameters.values()
            )
        )
        self.assertEqual(str(preflight_signature.return_annotation), "None")
        builder_signature = inspect.signature(
            laurent_module._build_laurent_residual_from_raw
        )
        self.assertEqual(
            tuple(builder_signature.parameters),
            ("transition", "structure", "metric", "protocol", "kind"),
        )
        self.assertTrue(
            all(
                builder_signature.parameters[name].kind
                is inspect.Parameter.POSITIONAL_OR_KEYWORD
                for name in ("transition", "structure", "metric", "protocol")
            )
        )
        self.assertIs(
            builder_signature.parameters["kind"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )
        self.assertEqual(
            str(builder_signature.return_annotation),
            "LaurentResidualCertificate",
        )
        self.assertEqual(tuple(laurent_module.__all__), _LEGACY_LAURENT_ALL)
        self.assertNotIn(
            "_preflight_laurent_resources_from_raw",
            laurent_module.__all__,
        )
        self.assertNotIn(
            "_build_laurent_residual_from_raw",
            laurent_module.__all__,
        )
        self.assertIn(
            laurent_module._build_laurent_residual_from_raw,
            tuple(
                cell.cell_contents
                for cell in (laurent_module._build_residual.__closure__ or ())
            ),
        )
        raw_preflight = laurent_module._preflight_laurent_resources_from_raw
        raw_builder = laurent_module._build_laurent_residual_from_raw
        with mock.patch.object(
            laurent_module,
            "_preflight_convolution_chain",
            side_effect=AssertionError("redirected preflight helper ran"),
        ):
            self.assertIsNone(raw_preflight(raw_transition, self.metric))
        with mock.patch.object(
            laurent_module,
            "_transition_map_from_raw",
            side_effect=AssertionError("redirected transition-map helper ran"),
        ):
            self.assertEqual(
                raw_builder(
                    raw_transition,
                    self.structure,
                    self.metric,
                    self.protocol,
                    kind="canonical-structure",
                ),
                expected[0],
            )

    def test_legacy_laurent_joins_precede_exactly_one_raw_core_call(self):
        events = []

        def transition_join(value):
            events.append("transition-join")
            return laurent_module._reverify_verified_transition(value)

        def structure_join(*args):
            events.append("structure-join")
            return laurent_module.verify_structure_manifest(*args)

        def metric_join(*args):
            events.append("metric-join")
            return laurent_module.verify_stability_metric_witness(*args)

        def protocol_join(value):
            events.append("protocol-join")
            return laurent_module.verify_fp64_enclosure_protocol(value)

        raw_core = mock.Mock(
            side_effect=lambda *args, **kwargs: (
                events.append("raw-core"),
                laurent_module._build_laurent_residual_from_raw(*args, **kwargs),
            )[1]
        )
        legacy = laurent_module._make_legacy_residual_builder(
            raw_core,
            transition_reverifier=transition_join,
            structure_verifier=structure_join,
            metric_verifier=metric_join,
            protocol_verifier=protocol_join,
        )
        observed = legacy(
            kind="canonical-structure",
            transition=self.transition,
            structure=self.structure,
            metric=self.metric,
            protocol=self.protocol,
        )
        expected = laurent_module._build_laurent_residual_from_raw(
            self.transition.transition,
            self.structure,
            self.metric,
            self.protocol,
            kind="canonical-structure",
        )
        self.assertEqual(observed, expected)
        self.assertEqual(
            events,
            [
                "transition-join",
                "structure-join",
                "metric-join",
                "protocol-join",
                "raw-core",
            ],
        )
        raw_core.assert_called_once()

    def test_saved_laurent_core_ignores_cross_owner_fp64_redirect(self):
        raw_transition = self.transition.transition
        raw_builder = laurent_module._build_laurent_residual_from_raw
        expected = raw_builder(
            raw_transition,
            self.structure,
            self.metric,
            self.protocol,
            kind="canonical-structure",
        )
        with mock.patch.object(
            fp64_module,
            "_directed_binary",
            side_effect=AssertionError("cross-owner fp64 redirect reached"),
        ) as redirected:
            observed = raw_builder(
                raw_transition,
                self.structure,
                self.metric,
                self.protocol,
                kind="canonical-structure",
            )
        redirected.assert_not_called()
        self.assertEqual(observed, expected)

    def test_saved_public_laurent_entry_ignores_post_freeze_dispatch_redirect(self):
        saved_certify = laurent_module.certify_laurent_residuals
        with mock.patch.object(
            laurent_module,
            "_build_residual",
            return_value="LAURENT_PERMISSION_BYPASS",
        ) as redirected:
            with self.assertRaises((TypeError, ValueError)):
                saved_certify(object(), object(), object(), object())
        redirected.assert_not_called()

    def test_saved_laurent_cores_ignore_post_freeze_builtin_shadows(self):
        raw_transition = self.transition.transition
        raw_preflight = laurent_module._preflight_laurent_resources_from_raw
        raw_builder = laurent_module._build_laurent_residual_from_raw
        expected = raw_builder(
            raw_transition,
            self.structure,
            self.metric,
            self.protocol,
            kind="canonical-structure",
        )
        redirects = []
        patches = []
        for name in ("type", "len", "sorted", "tuple"):
            redirected = mock.Mock(
                side_effect=AssertionError(f"laurent.{name} was consulted")
            )
            redirects.append(redirected)
            patches.append(
                mock.patch.object(
                    laurent_module,
                    name,
                    redirected,
                    create=True,
                )
            )
        with patches[0], patches[1], patches[2], patches[3]:
            self.assertIsNone(raw_preflight(raw_transition, self.metric))
            observed = raw_builder(
                raw_transition,
                self.structure,
                self.metric,
                self.protocol,
                kind="canonical-structure",
            )
        self.assertEqual(observed, expected)
        for redirected in redirects:
            redirected.assert_not_called()

    def test_saved_laurent_core_ignores_owner_numeric_module_redirects(self):
        raw_transition = self.transition.transition
        raw_builder = laurent_module._build_laurent_residual_from_raw
        expected = raw_builder(
            raw_transition,
            self.structure,
            self.metric,
            self.protocol,
            kind="canonical-structure",
        )
        redirected_stack = mock.Mock(
            side_effect=AssertionError("redirected Laurent numpy was consulted")
        )
        redirected_isfinite = mock.Mock(
            side_effect=AssertionError("redirected Laurent math was consulted")
        )
        redirected_np = mock.Mock(stack=redirected_stack)
        redirected_math = mock.Mock(isfinite=redirected_isfinite)
        with (
            mock.patch.object(laurent_module, "np", redirected_np),
            mock.patch.object(laurent_module, "math", redirected_math),
        ):
            observed = raw_builder(
                raw_transition,
                self.structure,
                self.metric,
                self.protocol,
                kind="canonical-structure",
            )
        redirected_stack.assert_not_called()
        redirected_isfinite.assert_not_called()
        self.assertEqual(observed, expected)

    def test_global_bound_includes_nonzero_coefficient_center_norm(self):
        roundoff = 2.0**-50
        bound = _coefficient_frobenius_upper_sum(
            ((0,),),
            {
                (0,): np.asarray(
                    [[3.0 + 4.0j, 0.0], [0.0, 0.0]],
                    dtype=np.complex128,
                )
            },
            (roundoff,),
        )
        self.assertGreater(bound, 5.0)
        self.assertGreaterEqual(
            Fraction.from_float(bound),
            Fraction(5) + Fraction.from_float(roundoff),
        )

    def test_resigned_roundoff_bound_or_coefficient_is_rejected(self):
        structure_residual, _ = certify_laurent_residuals(
            self.transition,
            self.structure,
            self.metric,
            self.protocol,
        )
        changed = dataclasses.replace(
            structure_residual,
            coefficient_roundoff_frobenius_uppers=(
                structure_residual.coefficient_roundoff_frobenius_uppers[0] * 2.0,
            ),
            residual_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            residual_sha=canonical_sha(laurent_residual_payload(changed)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_laurent_residual_certificate(
                changed,
                self.transition,
                self.structure,
                self.metric,
                self.protocol,
            )

    def test_convolution_resource_caps_precede_candidate_allocation(self):
        with self.assertRaises((TypeError, ValueError)):
            _preflight_convolution(
                left_count=1_001,
                right_count=1_000,
                n_state=2,
            )
        with self.assertRaises((TypeError, ValueError)):
            _preflight_convolution(
                left_count=100_000,
                right_count=1,
                n_state=100,
            )

        transition_support = tuple((index - 500,) for index in range(1_001))
        with mock.patch("rulespace_v3.laurent.np.zeros") as allocation:
            with self.assertRaisesRegex(
                ValueError,
                "second Laurent convolution pair-product cap exceeded",
            ):
                _preflight_convolution_chain(
                    transition_support,
                    ((0,),),
                    transition_support,
                    2,
                )
            allocation.assert_not_called()

    def test_nonzero_subnormal_is_rejected_before_exact_zero_masks_it(self):
        subnormal = np.nextafter(0.0, 1.0)
        left = {
            (0,): np.asarray(
                [[subnormal + 0.0j, 0.0], [0.0, 0.0]],
                dtype=np.complex128,
            )
        }
        right = {(0,): np.zeros((2, 2), dtype=np.complex128)}
        with self.assertRaisesRegex(ValueError, "subnormal"):
            _scalar_convolve(
                left,
                _zero_errors(left, 2),
                right,
                _zero_errors(right, 2),
                2,
            )

    def test_dot_dag_uses_q_four_n_minus_one_operation_shape(self):
        left = (1.0 + 2.0j, 3.0 + 4.0j)
        right = (5.0 + 6.0j, 7.0 + 8.0j)
        with mock.patch(
            "rulespace_v3.laurent._ordered_complex_multiply",
            wraps=_ordered_complex_multiply,
        ) as multiply:
            with mock.patch(
                "rulespace_v3.laurent._ordered_complex_add",
                wraps=_ordered_complex_add,
            ) as accumulate:
                _ordered_complex_dot_values(left, right)
                self.assertEqual(multiply.call_count, 2)
                self.assertEqual(accumulate.call_count, 1)
                multiply.reset_mock()
                accumulate.reset_mock()
                _ordered_complex_dot_values(left[:1], right[:1])
                self.assertEqual(multiply.call_count, 1)
                self.assertEqual(accumulate.call_count, 0)

    def test_evidence_body_cap_precedes_coefficient_tensor_freeze(self):
        allocation = mock.Mock(wraps=freeze_complex_tensor)
        test_core = laurent_module._freeze_laurent_neutral_core(
            laurent_module._build_laurent_residual_from_raw,
            global_overrides={
                "LAURENT_MAX_EVIDENCE_BODY_BYTES": 1,
                "freeze_complex_tensor": allocation,
            },
        )
        with self.assertRaisesRegex(
            ValueError,
            "canonical evidence body cap exceeded",
        ):
            test_core(
                self.transition.transition,
                self.structure,
                self.metric,
                self.protocol,
                kind="canonical-structure",
            )
        allocation.assert_not_called()

    def test_verifier_body_cap_precedes_payload_materialization_and_hash(self):
        residual, _ = certify_laurent_residuals(
            self.transition,
            self.structure,
            self.metric,
            self.protocol,
        )
        payload = mock.Mock()
        hashing = mock.Mock()
        test_verifier = laurent_module._freeze_laurent_neutral_core(
            laurent_module.verify_laurent_residual_certificate,
            global_overrides={
                "LAURENT_MAX_EVIDENCE_BODY_BYTES": 1,
                "laurent_residual_payload": payload,
                "canonical_sha": hashing,
            },
        )
        with self.assertRaisesRegex(
            ValueError,
            "canonical evidence body cap exceeded",
        ):
            test_verifier(
                residual,
                self.transition,
                self.structure,
                self.metric,
                self.protocol,
            )
        payload.assert_not_called()
        hashing.assert_not_called()

    def test_raw_cardinality_schema_rejects_before_json_materialization(self):
        residual, _ = certify_laurent_residuals(
            self.transition,
            self.structure,
            self.metric,
            self.protocol,
        )
        oversized_support = tuple((index,) for index in range(100_001))
        attacks = (
            {"support_offsets": oversized_support},
            {"operand_shas": residual.operand_shas + ("f" * 64,)},
            {"convolution_pair_counts": (residual.convolution_pair_counts + (1,))},
        )
        for attack in attacks:
            with self.subTest(field=next(iter(attack))):
                with mock.patch(
                    "rulespace_v3.laurent.json.dumps",
                ) as serialization:
                    with self.assertRaises((TypeError, ValueError)):
                        dataclasses.replace(residual, **attack)
                    serialization.assert_not_called()


if __name__ == "__main__":
    unittest.main()
