from __future__ import annotations

import dataclasses
import unittest
from unittest import mock

import mpmath as mp
import numpy as np

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.bridge import (
    _preflight,
    audit_full_state_bridge,
    bridge_audit_payload,
    build_full_state_bridge_spec,
    full_state_bridge_spec_payload,
    generate_bridge_trial_vectors,
    verify_full_state_bridge_audit,
    verify_full_state_bridge_spec,
)
from rulespace_v3.dynamics import measure_transition
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.registry import build_closed_control_registry
from tests.test_v3m0_dynamics import _quarter_turn_controls


class FullStateBridgeTests(unittest.TestCase):
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

    def test_spec_is_mechanical_and_has_no_observer_or_fejer_fields(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        self.assertEqual(spec.macro_steps, (1, 2, 4))
        self.assertEqual(spec.bridge_grid.reciprocal_indices, ((0,),))
        np.testing.assert_array_equal(
            frozen_tensor_array(spec.state_trial_vectors),
            np.eye(2),
        )
        self.assertEqual(spec.trial_gram_frobenius_upper, 0.0)
        fields = {field.name for field in dataclasses.fields(spec)}
        self.assertNotIn("source_basis", fields)
        self.assertNotIn("readout_basis", fields)
        self.assertNotIn("fejer_order", fields)
        self.assertEqual(
            verify_full_state_bridge_spec(
                spec,
                self.factory,
                self.authority,
            ),
            spec,
        )

    def test_bridge_replays_full_periodic_executor_for_every_case(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        audit = audit_full_state_bridge(
            self.transition,
            self.factory,
            self.authority,
            spec,
        )
        self.assertEqual(len(audit.cases), 1 * 3 * 2)
        self.assertEqual(
            tuple(
                (case.reciprocal_index, case.macro_steps, case.trial_index)
                for case in audit.cases
            ),
            tuple(
                ((0,), steps, trial)
                for steps in (1, 2, 4)
                for trial in range(2)
            ),
        )
        self.assertLessEqual(audit.normalized_max, 1e-12)
        self.assertEqual(
            verify_full_state_bridge_audit(
                audit,
                self.transition,
                self.factory,
                self.authority,
                spec,
            ),
            audit,
        )

    def test_resigned_trial_or_audit_tamper_is_rejected(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        changed_trials = frozen_tensor_array(spec.state_trial_vectors)
        changed_trials[0, 0] = 0.5
        changed_spec = dataclasses.replace(
            spec,
            state_trial_vectors=freeze_complex_tensor(changed_trials),
            bridge_spec_sha="0" * 64,
        )
        changed_spec = dataclasses.replace(
            changed_spec,
            bridge_spec_sha=canonical_sha(
                full_state_bridge_spec_payload(changed_spec)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_spec(
                changed_spec,
                self.factory,
                self.authority,
            )

        audit = audit_full_state_bridge(
            self.transition,
            self.factory,
            self.authority,
            spec,
        )
        first = dataclasses.replace(
            audit.cases[0],
            raw_abs_residual=0.5,
            normalized_residual=0.5,
        )
        changed_audit = dataclasses.replace(
            audit,
            cases=(first,) + audit.cases[1:],
            raw_abs_max=0.5,
            normalized_max=0.5,
            bridge_sha="0" * 64,
        )
        changed_audit = dataclasses.replace(
            changed_audit,
            bridge_sha=canonical_sha(
                bridge_audit_payload(changed_audit)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_audit(
                changed_audit,
                self.transition,
                self.factory,
                self.authority,
                spec,
            )
        missing = dataclasses.replace(
            audit,
            cases=audit.cases[:-1],
            bridge_sha="0" * 64,
        )
        missing = dataclasses.replace(
            missing,
            bridge_sha=canonical_sha(bridge_audit_payload(missing)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_audit(
                missing,
                self.transition,
                self.factory,
                self.authority,
                spec,
            )
        duplicate = dataclasses.replace(
            audit,
            cases=audit.cases + (audit.cases[-1],),
            bridge_sha="0" * 64,
        )
        duplicate = dataclasses.replace(
            duplicate,
            bridge_sha=canonical_sha(bridge_audit_payload(duplicate)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_audit(
                duplicate,
                self.transition,
                self.factory,
                self.authority,
                spec,
            )

        reordered = dataclasses.replace(
            audit,
            cases=tuple(reversed(audit.cases)),
            bridge_sha="0" * 64,
        )
        reordered = dataclasses.replace(
            reordered,
            bridge_sha=canonical_sha(bridge_audit_payload(reordered)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_audit(
                reordered,
                self.transition,
                self.factory,
                self.authority,
                spec,
            )

    def test_executor_resource_cap_is_checked_by_integer_preflight(self):
        with self.assertRaises((TypeError, ValueError)):
            _preflight(
                k_count=1,
                trial_count=1,
                state_count=1,
                spatial_shape=(600_000_000,),
                primitive_count=1,
            )


class DenseBridgeTrialTests(unittest.TestCase):
    def test_sha256_dense_trials_use_scalar_householder_and_are_orthonormal(self):
        with mock.patch(
            "numpy.linalg.qr",
            side_effect=AssertionError("LAPACK QR is forbidden"),
        ), mock.patch(
            "numpy.linalg.svd",
            side_effect=AssertionError("LAPACK SVD is forbidden"),
        ), mock.patch(
            "numpy.linalg.eigh",
            side_effect=AssertionError("LAPACK eigh is forbidden"),
        ):
            tensor, upper = generate_bridge_trial_vectors(
                36,
                "a" * 64,
            )
        values = frozen_tensor_array(tensor)
        self.assertEqual(values.shape, (32, 36))
        with mp.workdps(100):
            total = mp.mpf("0")
            for first in range(32):
                for second in range(32):
                    entry = mp.mpc("0")
                    for state in range(36):
                        left = mp.mpc(
                            float(values[first, state].real),
                            float(values[first, state].imag),
                        )
                        right = mp.mpc(
                            float(values[second, state].real),
                            float(values[second, state].imag),
                        )
                        entry += left * mp.conj(right)
                    if first == second:
                        entry -= 1
                    total += abs(entry) ** 2
            independent = float(mp.sqrt(total))
        self.assertLessEqual(independent, upper)
        self.assertLessEqual(upper, 1e-12)
        again, again_upper = generate_bridge_trial_vectors(36, "a" * 64)
        self.assertEqual(again, tensor)
        self.assertEqual(again_upper, upper)
        q_columns = values.conj()
        for column in q_columns:
            nonzero = np.flatnonzero(column != 0.0)
            self.assertGreater(len(nonzero), 0)
            first = column[nonzero[0]]
            self.assertGreater(first.real, 0.0)
            self.assertEqual(first.imag, 0.0)

    def test_small_state_trials_are_bit_exact_identity(self):
        tensor, upper = generate_bridge_trial_vectors(4, "b" * 64)
        np.testing.assert_array_equal(
            frozen_tensor_array(tensor),
            np.eye(4),
        )
        self.assertEqual(upper, 0.0)


if __name__ == "__main__":
    unittest.main()
