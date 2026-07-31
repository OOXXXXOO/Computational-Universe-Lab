from __future__ import annotations

import math
import unittest
from unittest import mock

import numpy as np

from rulespace_v3.causal import (
    CausalNumericalThresholds,
    compute_causal_spectrum,
)


THRESHOLDS = CausalNumericalThresholds(
    absolute_signal_threshold=1e-12,
    raw_noise_floor=0.0,
    relative_gap_min=1e3,
    survival_threshold=0.5,
    survival_ambiguity_half_width=0.1,
)


class V3M0CausalNumericalKernelTests(unittest.TestCase):
    def measure(self, actual, ablated, ablated_all, *, thresholds=THRESHOLDS):
        return compute_causal_spectrum(
            actual,
            ablated,
            ablated_all,
            thresholds=thresholds,
        )

    def test_full_zero_and_rank_one_survival(self):
        actual = np.eye(2, dtype=np.complex128)
        zero = np.zeros((2, 2), dtype=np.complex128)
        rank_one = np.diag([1.0, 0.0]).astype(np.complex128)

        full_result = self.measure(actual, actual, actual)
        zero_result = self.measure(actual, zero, zero)
        half_result = self.measure(actual, rank_one, rank_one)

        np.testing.assert_allclose(full_result.survival_spectrum, (1.0, 1.0))
        self.assertEqual(full_result.epsilon_dof, 1.0)
        self.assertEqual(full_result.epsilon_cont, 1.0)
        np.testing.assert_allclose(zero_result.survival_spectrum, (0.0, 0.0))
        self.assertEqual(zero_result.epsilon_dof, 0.0)
        self.assertEqual(zero_result.epsilon_cont, 0.0)
        np.testing.assert_allclose(half_result.survival_spectrum, (0.0, 1.0))
        self.assertEqual(half_result.epsilon_dof, 0.5)
        self.assertEqual(half_result.epsilon_cont, 0.5)

    def test_phase_and_scalar_gain_preserve_survival_but_change_auxiliary_report(self):
        actual = np.eye(2, dtype=np.complex128)
        ablated = -2.0j * actual

        result = self.measure(actual, ablated, ablated)

        np.testing.assert_allclose(result.survival_spectrum, (1.0, 1.0))
        self.assertEqual(result.epsilon_dof, 1.0)
        self.assertAlmostEqual(result.kappa_map, 1.0)
        self.assertAlmostEqual(result.d_proc_sq, 0.0)
        self.assertAlmostEqual(result.gain_ratio, 2.0)
        self.assertAlmostEqual(result.phase_shift, math.pi / 2.0)

    def test_full_source_extra_mode_is_not_hidden_by_actual_sector(self):
        actual = np.asarray([[1.0], [0.0]], dtype=np.complex128)
        ablated_on_actual = np.asarray([[1.0], [0.0]], dtype=np.complex128)
        ablated_all = np.eye(2, dtype=np.complex128)

        result = self.measure(
            actual,
            ablated_on_actual,
            ablated_all,
        )

        self.assertEqual(result.epsilon_dof, 1.0)
        self.assertAlmostEqual(result.chi_extra, 0.5)

    def test_grey_survival_keeps_continuous_coordinate_but_nulls_dof_verdict(self):
        actual = np.asarray([[1.0], [0.0]], dtype=np.complex128)
        # A one-dimensional ablated subspace at 45 degrees gives s=1/2.
        ablated = np.asarray([[1.0], [1.0]], dtype=np.complex128)

        result = self.measure(actual, ablated, ablated)

        self.assertTrue(result.ambiguous)
        self.assertIsNone(result.epsilon_dof)
        self.assertAlmostEqual(result.epsilon_cont, 0.5)

    def test_zero_ablated_map_has_null_procrustes_fields(self):
        actual = np.eye(2, dtype=np.complex128)
        zero = np.zeros((2, 2), dtype=np.complex128)

        result = self.measure(actual, zero, zero)

        self.assertIsNone(result.kappa_map)
        self.assertIsNone(result.d_proc_sq)
        self.assertIsNone(result.gain_ratio)
        self.assertIsNone(result.phase_shift)

    def test_nonzero_orthogonal_maps_have_undefined_phase(self):
        actual = np.diag([1.0, -1.0]).astype(np.complex128)
        ablated = np.eye(2, dtype=np.complex128)

        result = self.measure(actual, ablated, ablated)

        self.assertEqual(result.kappa_map, 0.0)
        self.assertEqual(result.d_proc_sq, 1.0)
        self.assertIsNotNone(result.gain_ratio)
        self.assertIsNone(result.phase_shift)

    def test_roundoff_at_unit_interval_endpoints_is_canonicalized(self):
        rng = np.random.default_rng(7_312_026)
        raw = (rng.normal(size=(5, 3)) + 1.0j * rng.normal(size=(5, 3))).astype(
            np.complex128
        )
        actual = np.linalg.qr(raw)[0][:, :3]
        phase = np.exp(1.0j * rng.uniform(-math.pi, math.pi))
        scale = 10.0 ** rng.uniform(-150.0, 150.0)
        ablated = (scale * phase * actual).astype(np.complex128)

        result = self.measure(actual, ablated, ablated)

        self.assertEqual(result.survival_spectrum[-1], 1.0)
        self.assertEqual(result.kappa_map, 1.0)
        self.assertEqual(result.d_proc_sq, 0.0)
        for value in result.survival_spectrum:
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_calibrated_survival_line_is_consumed_not_hardcoded(self):
        actual = np.asarray([[1.0], [0.0]], dtype=np.complex128)
        ablated = np.asarray(
            [[math.sqrt(0.75)], [0.5]],
            dtype=np.complex128,
        )
        high_line = CausalNumericalThresholds(
            absolute_signal_threshold=1e-12,
            raw_noise_floor=0.0,
            relative_gap_min=1e3,
            survival_threshold=0.8,
            survival_ambiguity_half_width=0.01,
        )

        default = self.measure(actual, ablated, ablated)
        shifted = self.measure(
            actual,
            ablated,
            ablated,
            thresholds=high_line,
        )

        self.assertEqual(default.epsilon_dof, 1.0)
        self.assertEqual(shifted.epsilon_dof, 0.0)

    def test_scaled_rank_deficiency_and_extreme_gain_fail_closed_or_stay_finite(self):
        rank_one = np.full((2, 2), 1.0e8 + 0.0j, dtype=np.complex128)
        with self.assertRaisesRegex(ValueError, "numerical rank|actual response lost"):
            self.measure(rank_one, rank_one, rank_one)

        unresolved = np.diag([1.0e8, 1.0e-6]).astype(np.complex128)
        with self.assertRaisesRegex(ValueError, "numerical rank"):
            self.measure(unresolved, unresolved, unresolved)

        huge = (1.0e155 * np.eye(2)).astype(np.complex128)
        huge_result = self.measure(huge, huge, huge)
        for value in (
            huge_result.kappa_map,
            huge_result.d_proc_sq,
            huge_result.gain_ratio,
            huge_result.phase_shift,
        ):
            self.assertIsNotNone(value)
            self.assertTrue(math.isfinite(value))

    def test_resource_cap_precedes_full_finite_scan(self):
        oversized = np.lib.stride_tricks.as_strided(
            np.zeros(1, dtype=np.complex128),
            shape=(4_097, 4_097),
            strides=(0, 0),
        )
        with mock.patch(
            "rulespace_v3.causal.np.all",
            side_effect=AssertionError("finite scan ran before resource cap"),
        ) as all_values:
            with self.assertRaisesRegex(ValueError, "resource cap"):
                self.measure(oversized, oversized, oversized)
        all_values.assert_not_called()

    def test_aggregate_work_cap_precedes_first_decomposition(self):
        individually_admissible = np.zeros((448, 448), dtype=np.complex128)
        with mock.patch(
            "rulespace_v3.causal.np.linalg.svd",
            side_effect=AssertionError("SVD ran before aggregate work cap"),
        ) as svd:
            with self.assertRaisesRegex(ValueError, "aggregate.*work cap"):
                self.measure(
                    individually_admissible,
                    individually_admissible,
                    individually_admissible,
                )
        svd.assert_not_called()

    def test_work_cap_precedes_finite_scan_and_allocation(self):
        scalar = np.zeros(1, dtype=np.complex128)
        too_costly = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_500, 1_500),
            strides=(0, 0),
        )
        with mock.patch(
            "rulespace_v3.causal.np.array",
            side_effect=AssertionError("allocation ran before work preflight"),
        ) as array:
            with mock.patch(
                "rulespace_v3.causal.np.all",
                side_effect=AssertionError("finite scan ran before work preflight"),
            ) as all_values:
                with self.assertRaisesRegex(ValueError, "work cap"):
                    self.measure(too_costly, too_costly, too_costly)
        array.assert_not_called()
        all_values.assert_not_called()

    def test_all_grey_ablated_spectrum_is_undefined_not_silent_null(self):
        actual = np.eye(2, dtype=np.complex128)
        grey = (1.0e-4 * np.eye(2)).astype(np.complex128)
        calibrated = CausalNumericalThresholds(
            absolute_signal_threshold=1e-3,
            raw_noise_floor=1e-6,
            relative_gap_min=1e3,
            survival_threshold=0.5,
            survival_ambiguity_half_width=0.1,
        )

        with self.assertRaisesRegex(ValueError, "grey"):
            self.measure(
                actual,
                grey,
                grey,
                thresholds=calibrated,
            )


if __name__ == "__main__":
    unittest.main()
