from __future__ import annotations

import dataclasses
import unittest

import numpy as np

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.dynamics import (
    measure_transition,
    measured_transition_payload,
    transition_kernel_array,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor
from rulespace_v3.instability import (
    _build_instability_growth_counter_witness_from_raw,
    certify_instability_growth_counter_witness,
    instability_growth_counter_witness_payload,
    verify_instability_growth_counter_witness,
    verify_instability_growth_counter_witness_arithmetic,
)
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.registry import build_closed_control_registry
from tests.test_v3m0_dynamics import _quarter_turn_controls


class InstabilityGrowthCounterWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(cls.controls, cls.parent)
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

    def _resigned_jordan_raw(self):
        raw = self.transition.transition
        kernel = np.zeros_like(transition_kernel_array(self.transition))
        kernel[:, :, 0] = np.asarray(
            [[1.0, 1.0], [0.0, 1.0]],
            dtype=np.complex128,
        )
        changed = dataclasses.replace(
            raw,
            kernel=freeze_complex_tensor(kernel),
            transition_sha="0" * 64,
        )
        return dataclasses.replace(
            changed,
            transition_sha=canonical_sha(measured_transition_payload(changed)),
        )

    def test_exact_jordan_profile_has_complete_integer_growth_witness(self):
        witness = _build_instability_growth_counter_witness_from_raw(
            self._resigned_jordan_raw()
        )
        self.assertIsNotNone(witness)
        assert witness is not None
        self.assertEqual(witness.macro_step, 16_384)
        self.assertEqual(witness.initial_norm_squared, 1)
        self.assertEqual(witness.final_norm_squared, 268_435_457)
        self.assertEqual(
            witness.required_growth_squared_strict_upper,
            100_000_001,
        )
        self.assertGreater(
            witness.final_norm_squared,
            witness.required_growth_squared_strict_upper,
        )
        self.assertEqual(
            verify_instability_growth_counter_witness_arithmetic(witness),
            witness,
        )

    def test_ordinary_quarter_turn_does_not_emit_jordan_witness(self):
        self.assertIsNone(
            certify_instability_growth_counter_witness(self.transition)
        )

    def test_resigned_norm_and_non_live_transition_are_rejected(self):
        witness = _build_instability_growth_counter_witness_from_raw(
            self._resigned_jordan_raw()
        )
        assert witness is not None
        changed = dataclasses.replace(
            witness,
            final_norm_squared=268_435_456,
            witness_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            witness_sha=canonical_sha(
                instability_growth_counter_witness_payload(changed)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_instability_growth_counter_witness_arithmetic(changed)
        with self.assertRaises((TypeError, ValueError)):
            verify_instability_growth_counter_witness(
                witness,
                self.factory,
                self.authority,
            )

    def test_nested_support_and_tensor_hashes_are_reconstructed(self):
        raw = self._resigned_jordan_raw()
        changed_raw = dataclasses.replace(
            raw,
            support_sha="1" * 64,
            transition_sha="0" * 64,
        )
        changed_raw = dataclasses.replace(
            changed_raw,
            transition_sha=canonical_sha(
                measured_transition_payload(changed_raw)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            _build_instability_growth_counter_witness_from_raw(changed_raw)

        witness = _build_instability_growth_counter_witness_from_raw(raw)
        assert witness is not None
        changed_matrix = dataclasses.replace(
            witness.transition_matrix,
            tensor_sha="2" * 64,
        )
        changed_witness = dataclasses.replace(
            witness,
            transition_matrix=changed_matrix,
            witness_sha="0" * 64,
        )
        changed_witness = dataclasses.replace(
            changed_witness,
            witness_sha=canonical_sha(
                instability_growth_counter_witness_payload(changed_witness)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_instability_growth_counter_witness_arithmetic(
                changed_witness
            )


if __name__ == "__main__":
    unittest.main()
