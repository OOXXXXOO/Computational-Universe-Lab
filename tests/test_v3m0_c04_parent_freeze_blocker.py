from __future__ import annotations

import math
import unittest

import numpy as np

from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.response import _extract_projector_candidates
from rulespace_v3.spectral import _require_signed_permutation


class C04ParentFreezeSatisfiabilityAudit(unittest.TestCase):
    """Regression audit that the former two-state C04 contradiction is closed."""

    def test_four_state_positive_band_supplies_c04_rank_one_reference(self) -> None:
        parent = issue_v3m0_parent_freeze().manifest
        application = parent.synthetic_control_application_specs[3]
        grid = application.grid_protocol

        self.assertEqual(
            application.control_case_id,
            "C04_CANONICAL_ANGLE_025_075",
        )
        self.assertEqual(
            application.basis_protocol.source_basis.channel_order,
            ("q0", "p0", "q1", "p1"),
        )
        self.assertEqual(
            grid.preregistered_phase_bands,
            ((math.pi / 2.0 - 1.0 / 8.0, math.pi / 2.0 + 1.0 / 8.0),),
        )
        self.assertEqual(grid.expected_shell_rank, 1)

        identity = np.eye(4, dtype=np.complex128)
        symplectic_form = np.asarray(
            (
                (0.0, 1.0, 0.0, 0.0),
                (-1.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
                (0.0, 0.0, -1.0, 0.0),
            ),
            dtype=np.complex128,
        )
        reference = np.asarray(
            (
                (0.0, -1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, -1.0, 0.0),
                (0.0, 0.0, 0.0, -1.0),
            ),
            dtype=np.complex128,
        )
        _require_signed_permutation(reference)
        np.testing.assert_array_equal(
            reference.T @ symplectic_form @ reference,
            symplectic_form,
        )
        np.testing.assert_array_equal(reference.conj().T @ reference, identity)
        candidates = _extract_projector_candidates(
            reference,
            identity,
            grid.preregistered_phase_bands,
            256,
            identity,
            identity,
        )
        self.assertEqual(
            sum(item.rank for item in candidates),
            grid.expected_shell_rank,
        )


if __name__ == "__main__":
    unittest.main()
