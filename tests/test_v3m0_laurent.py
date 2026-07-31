from __future__ import annotations

import dataclasses
import unittest
from fractions import Fraction
from unittest import mock

import numpy as np

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
                structure_residual.coefficient_roundoff_frobenius_uppers[0]
                * 2.0,
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
        right = {
            (0,): np.zeros((2, 2), dtype=np.complex128)
        }
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
        with mock.patch(
            "rulespace_v3.laurent.LAURENT_MAX_EVIDENCE_BODY_BYTES",
            1,
        ):
            with mock.patch(
                "rulespace_v3.laurent.freeze_complex_tensor",
                wraps=freeze_complex_tensor,
            ) as allocation:
                with self.assertRaisesRegex(
                    ValueError,
                    "canonical evidence body cap exceeded",
                ):
                    certify_laurent_residuals(
                        self.transition,
                        self.structure,
                        self.metric,
                        self.protocol,
                    )
                allocation.assert_not_called()

    def test_verifier_body_cap_precedes_payload_materialization_and_hash(self):
        residual, _ = certify_laurent_residuals(
            self.transition,
            self.structure,
            self.metric,
            self.protocol,
        )
        with mock.patch(
            "rulespace_v3.laurent.LAURENT_MAX_EVIDENCE_BODY_BYTES",
            1,
        ):
            with mock.patch(
                "rulespace_v3.laurent.laurent_residual_payload",
            ) as payload:
                with mock.patch(
                    "rulespace_v3.laurent.canonical_sha",
                ) as hashing:
                    with self.assertRaisesRegex(
                        ValueError,
                        "canonical evidence body cap exceeded",
                    ):
                        verify_laurent_residual_certificate(
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
            {
                "convolution_pair_counts": (
                    residual.convolution_pair_counts + (1,)
                )
            },
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
