from __future__ import annotations

import math
import unittest

import numpy as np

from rulespace_v3.sigma import (
    dm26_controls,
    fit_constant,
    fit_high_order,
    fit_power,
    fit_sigma,
    leave_one_out_power,
    run_dm26,
)


class V3M0PureSigmaFitTests(unittest.TestCase):
    def test_r37_axial_fixture_is_reproduced_without_importing_runner(self):
        x = np.asarray(
            (
                0.2617993877991494,
                0.39269908169872414,
                0.5235987755982988,
                0.5890486225480862,
                0.6544984694978736,
                0.7853981633974483,
            ),
            dtype=np.float64,
        )
        y = np.asarray(
            (
                0.08527863993099939,
                0.09920145403478804,
                0.12421118741495234,
                0.18264646934117562,
                0.23853315927237403,
                0.1775137049625285,
            ),
            dtype=np.float64,
        )

        constant = fit_constant(x, y)
        power = fit_power(x, y)

        self.assertAlmostEqual(constant.A, 0.15123076915946965, places=15)
        self.assertAlmostEqual(constant.sigma_A, 0.0238650630500747, places=15)
        self.assertAlmostEqual(constant.rss, 0.017086237031521217, places=15)
        self.assertAlmostEqual(constant.aic, -33.167448764359804, places=13)
        self.assertAlmostEqual(power.A, -0.19134650736650763, places=14)
        self.assertAlmostEqual(power.B, 0.4377735289965842, places=14)
        self.assertAlmostEqual(power.alpha, 0.37000000000000005, places=15)
        self.assertAlmostEqual(power.sigma_A, 2.131816018607365, places=13)
        self.assertAlmostEqual(
            constant.aic - power.aic,
            2.6951090036189598,
            places=13,
        )
        self.assertEqual(len(leave_one_out_power(x, y)), len(x))

    def test_dm26_clean_zero_and_true_floor_controls_have_teeth(self):
        controls = dm26_controls()
        self.assertEqual(
            tuple(row.control_id for row in controls[:4]),
            (
                "A1",
                "A2",
                "A3",
                "A4",
            ),
        )
        self.assertEqual(
            tuple(row.control_id for row in controls[4:]),
            (
                "B1",
                "B2",
                "B3",
                "B4",
            ),
        )
        self.assertTrue(all(row.matches_expected for row in controls))
        self.assertTrue(all(row.decision.both_pollution for row in controls[:4]))
        self.assertTrue(all(not row.decision.both_pollution for row in controls[4:]))
        self.assertAlmostEqual(
            controls[0].decision.power_full.A,
            -0.00019077085462718135,
            places=15,
        )
        self.assertAlmostEqual(
            controls[4].decision.high_order.A,
            -0.00011800089765528002,
            places=15,
        )

    def test_dm26_reproduces_frozen_round_two_decision(self):
        x = np.asarray(
            [2.0 * math.pi / size for size in (16, 24, 32, 48)],
            dtype=np.float64,
        )
        y = np.asarray(
            (
                0.03768751594167317,
                0.01696358473225302,
                0.0095841172506926,
                0.004272980201108287,
            ),
            dtype=np.float64,
        )

        decision = run_dm26(x, y)

        self.assertTrue(decision.both_pollution)
        self.assertAlmostEqual(
            decision.power_full.A,
            -0.00012265669635452142,
            places=15,
        )
        self.assertAlmostEqual(decision.power_full.alpha, 1.9600000000000004)
        self.assertAlmostEqual(
            decision.high_order.A,
            7.85048555294876e-08,
            places=16,
        )
        self.assertAlmostEqual(
            decision.delta_aic_power_minus_high,
            49.44934303010231,
            places=11,
        )
        self.assertAlmostEqual(
            decision.A_half,
            -3.513917995894423e-05,
            places=15,
        )

    def test_fit_inputs_are_strict_finite_positive_and_sized(self):
        good_x = np.asarray((0.1, 0.2, 0.3, 0.4), dtype=np.float64)
        good_y = np.asarray((0.01, 0.04, 0.09, 0.16), dtype=np.float64)
        for bad_x, bad_y in (
            (good_x.astype(np.float32), good_y),
            (good_x, good_y[:-1]),
            (np.asarray((0.0, 0.2, 0.3, 0.4)), good_y),
            (good_x, np.asarray((0.01, np.nan, 0.09, 0.16))),
            (good_x[:3], good_y[:3]),
        ):
            with self.subTest(bad_x=bad_x, bad_y=bad_y):
                with self.assertRaises((TypeError, ValueError)):
                    fit_power(bad_x, bad_y)

    def test_high_order_is_not_silently_used_as_primary_power_fit(self):
        x = np.asarray((0.1, 0.2, 0.3, 0.4), dtype=np.float64)
        y = 0.2 * x**2 - 0.05 * x**4

        power = fit_power(x, y)
        high = fit_high_order(x, y)

        self.assertEqual(power.parameter_count, 3)
        self.assertEqual(high.parameter_count, 4)
        self.assertGreaterEqual(
            power.aic - high.aic,
            2.0,
        )

    def test_fit_sigma_keeps_constant_result_defined_with_null_alpha(self):
        x = np.asarray((0.1, 0.2, 0.3, 0.4), dtype=np.float64)
        y = np.full(4, 0.2, dtype=np.float64)

        result = fit_sigma(
            x,
            y,
            "geometry-manifest-constant-v1",
            deterministic=False,
        )

        self.assertEqual(result.geometry_manifest_id, "geometry-manifest-constant-v1")
        self.assertEqual(result.model_winner, "constant")
        self.assertIsNone(result.alpha)
        self.assertFalse(result.alpha_identifiable)
        self.assertFalse(result.zero_consistent)
        self.assertTrue(math.isfinite(result.A))
        self.assertEqual(result.fit_window, tuple(float(value) for value in x))
        self.assertEqual(result.expanded_window, result.fit_window)

    def test_fit_sigma_deterministic_double_test_separates_zero_and_floor(self):
        x = np.asarray(
            [2.0 * math.pi / size for size in (16, 24, 32, 48)],
            dtype=np.float64,
        )
        clean_zero = (0.236 * x**2 - 0.05 * x**4 + 0.01 * x**6).astype(np.float64)
        true_floor = (1.2e-4 + 0.236 * x**2 - 0.05 * x**4 + 0.01 * x**6).astype(
            np.float64
        )

        zero = fit_sigma(
            x,
            clean_zero,
            "geometry-manifest-clean-zero-v1",
            deterministic=True,
        )
        floor = fit_sigma(
            x,
            true_floor,
            "geometry-manifest-true-floor-v1",
            deterministic=True,
        )

        self.assertTrue(zero.zero_consistent)
        self.assertFalse(floor.zero_consistent)
        self.assertEqual(zero.zero_test, "dm26-double-test")
        self.assertTrue(all(control.matches_expected for control in zero.dm26_controls))
        self.assertIsNotNone(zero.dm26_decision)
        self.assertIsNotNone(floor.dm26_decision)

    def test_fit_sigma_rejects_unbound_or_nonphysical_fit_payloads(self):
        x = np.asarray((0.1, 0.2, 0.3, 0.4), dtype=np.float64)
        y = np.asarray((0.01, 0.04, 0.09, 0.16), dtype=np.float64)

        for manifest in ("", "bad manifest", "x" * 257):
            with self.subTest(manifest=manifest):
                with self.assertRaises((TypeError, ValueError)):
                    fit_sigma(x, y, manifest, deterministic=True)

        for bad_x, bad_y in (
            (np.asarray((0.1, 0.2, 0.3, 6.0)), y),
            (x, np.asarray((0.01, 0.04, 0.09, 1.1))),
        ):
            with self.assertRaises(ValueError):
                fit_sigma(
                    bad_x,
                    bad_y,
                    "geometry-manifest-bounds-v1",
                    deterministic=True,
                )


if __name__ == "__main__":
    unittest.main()
