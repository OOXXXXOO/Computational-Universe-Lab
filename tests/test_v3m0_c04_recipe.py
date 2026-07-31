from __future__ import annotations

import math
import unittest

import numpy as np

from rulespace_v3.calibration_authority import (
    C04_CANONICAL_ANGLE_RECIPE_ID,
    build_c04_canonical_angle_recipe,
    c04_canonical_angle_recipe_symbol,
    c04_reciprocal_swap_symbol,
)
from rulespace_v3.factory import frozen_tensor_array


def _phase_band_projector(
    matrix: np.ndarray,
    phase_band: tuple[float, float],
) -> np.ndarray:
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    phases = np.angle(eigenvalues)
    selected = np.flatnonzero((phases >= phase_band[0]) & (phases <= phase_band[1]))
    if len(selected) != 1:
        raise AssertionError("C04 reference band must select exactly one mode")
    columns = eigenvectors[:, selected]
    gram = columns.conj().T @ columns
    return columns @ np.linalg.inv(gram) @ columns.conj().T


def _orthonormal_columns(matrix: np.ndarray, rank: int) -> np.ndarray:
    left, singular_values, _ = np.linalg.svd(matrix, full_matrices=False)
    if len(singular_values) < rank or singular_values[rank - 1] <= 1.0e-12:
        raise AssertionError("C04 stacked response lost its frozen rank")
    return left[:, :rank]


class C04CanonicalAngleRecipeTests(unittest.TestCase):
    def test_reciprocal_swap_has_the_frozen_executor_symbol(self) -> None:
        for momentum in (0.0, math.pi / 4.0, math.pi / 2.0, math.pi):
            expected = np.asarray(
                (
                    (0.0, -np.exp(-1.0j * momentum)),
                    (np.exp(1.0j * momentum), 0.0),
                ),
                dtype=np.complex128,
            )
            np.testing.assert_allclose(
                c04_reciprocal_swap_symbol(momentum),
                expected,
                rtol=0.0,
                atol=1.0e-15,
            )

    def test_local_recipe_is_unitary_symplectic_and_hits_025_075(self) -> None:
        recipe = build_c04_canonical_angle_recipe()
        self.assertEqual(recipe.recipe_id, C04_CANONICAL_ANGLE_RECIPE_ID)
        self.assertEqual(recipe.channel_order, ("q0", "p0", "q1", "p1"))
        self.assertEqual(recipe.primitive_support_radius, 1)
        self.assertEqual(recipe.expected_shell_rank, 1)
        self.assertEqual(
            recipe.reference_phase_band,
            (math.pi / 2.0 - 1.0 / 8.0, math.pi / 2.0 + 1.0 / 8.0),
        )
        self.assertNotEqual(
            recipe.actual_effect_digest,
            recipe.ablated_effect_digest,
        )
        self.assertTrue(recipe.steps)
        self.assertTrue(any(step.target_conditioned for step in recipe.steps))
        self.assertTrue(
            all(
                len(step.offset) == 1 and abs(step.offset[0]) <= 1
                for step in recipe.steps
            )
        )

        identity = np.eye(4, dtype=np.complex128)
        symplectic_form = frozen_tensor_array(recipe.canonical_structure)
        source = frozen_tensor_array(recipe.source_injection)
        readout = frozen_tensor_array(recipe.readout)
        actual_responses: list[np.ndarray] = []
        ablated_responses: list[np.ndarray] = []

        for momentum in recipe.response_momenta:
            for branch, responses in (
                ("actual", actual_responses),
                ("matched_ablated", ablated_responses),
            ):
                matrix = c04_canonical_angle_recipe_symbol(
                    recipe,
                    momentum,
                    branch,
                )
                opposite = c04_canonical_angle_recipe_symbol(
                    recipe,
                    -momentum,
                    branch,
                )
                self.assertLessEqual(
                    float(np.linalg.norm(matrix.conj().T @ matrix - identity, 2)),
                    1.0e-12,
                )
                self.assertLessEqual(
                    float(
                        np.linalg.norm(
                            opposite.T @ symplectic_form @ matrix - symplectic_form,
                            2,
                        )
                    ),
                    1.0e-12,
                )
                self.assertLessEqual(
                    float(np.linalg.norm(opposite - matrix.conj(), 2)),
                    1.0e-12,
                )
                projector = _phase_band_projector(
                    matrix,
                    recipe.reference_phase_band,
                )
                responses.append(readout @ projector @ source)

        actual = np.concatenate(tuple(actual_responses), axis=0)
        ablated = np.concatenate(tuple(ablated_responses), axis=0)
        actual_basis = _orthonormal_columns(actual, rank=2)
        ablated_basis = _orthonormal_columns(ablated, rank=2)
        survival = np.linalg.svd(
            ablated_basis.conj().T @ actual_basis,
            compute_uv=False,
        )
        np.testing.assert_allclose(
            np.sort(survival**2),
            np.asarray((0.25, 0.75), dtype=np.float64),
            rtol=0.0,
            atol=2.0e-14,
        )


if __name__ == "__main__":
    unittest.main()
