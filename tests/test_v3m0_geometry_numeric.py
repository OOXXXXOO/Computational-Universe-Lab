from __future__ import annotations

import dataclasses
import json
import math
import unittest
from unittest import mock

import numpy as np

from rulespace_v3.geometry import (
    DEGENERATE_ROTATION_SEEDS,
    GeometryNumericalThresholds,
    audit_degenerate_rotations,
    compute_geometry_spectrum,
)


THRESHOLDS = GeometryNumericalThresholds(
    signal_threshold=1e-12,
    geometry_threshold=0.05,
    geometry_ambiguity_half_width=0.01,
    coverage_threshold=0.5,
    coverage_ambiguity_half_width=0.1,
)


class V3M0GeometryNumericalKernelTests(unittest.TestCase):
    def setUp(self):
        self.kernel = np.asarray(
            [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]],
            dtype=np.complex128,
        )
        self.quotient = np.asarray(
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            dtype=np.complex128,
        )
        self.metric = np.eye(2, dtype=np.complex128)
        self.targets = np.asarray(
            [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]],
            dtype=np.complex128,
        )

    def measure(self, response):
        return compute_geometry_spectrum(
            response,
            self.kernel,
            self.quotient,
            self.metric,
            self.targets,
            thresholds=THRESHOLDS,
        )

    def test_tt_row_full_and_low_rank_spectra_keep_explicit_zero_extension(self):
        tt = self.measure(self.targets)
        tt_row = self.measure(
            np.asarray(
                [[1.0, 0.0], [0.0, 0.0], [0.0, 1.0]],
                dtype=np.complex128,
            )
        )
        full_h = self.measure(np.eye(3, dtype=np.complex128))
        low_rank = self.measure(self.targets[:, :1])

        np.testing.assert_allclose(tt.g_spectrum, (0.0, 0.0), atol=1e-12)
        np.testing.assert_allclose(tt.c_spectrum, (1.0, 1.0), atol=1e-12)
        np.testing.assert_allclose(tt_row.g_spectrum, (1.0, 0.0), atol=1e-12)
        np.testing.assert_allclose(tt_row.c_spectrum, (0.0, 1.0), atol=1e-12)
        self.assertEqual(len(full_h.g_spectrum), 3)
        np.testing.assert_allclose(full_h.g_spectrum, (1.0, 0.0, 0.0), atol=1e-12)
        np.testing.assert_allclose(full_h.c_spectrum, (1.0, 1.0), atol=1e-12)
        np.testing.assert_allclose(low_rank.g_spectrum, (0.0,), atol=1e-12)
        np.testing.assert_allclose(low_rank.c_spectrum, (0.0, 1.0), atol=1e-12)
        self.assertEqual(low_rank.coverage_phys, 0.5)
        self.assertEqual(low_rank.rank_deficit, 1)
        self.assertIsNone(low_rank.n_response)
        self.assertEqual(low_rank.n_curv, 1)

    def test_quotient_gauge_dressing_does_not_change_coverage(self):
        response = self.targets
        dressed_targets = self.targets + np.asarray(
            [[0.0, 0.0], [0.0, 0.0], [3.0, -2.0]],
            dtype=np.complex128,
        )

        plain = self.measure(response)
        dressed = compute_geometry_spectrum(
            response,
            self.kernel,
            self.quotient,
            self.metric,
            dressed_targets,
            thresholds=THRESHOLDS,
        )

        np.testing.assert_allclose(plain.c_spectrum, dressed.c_spectrum, atol=1e-12)
        self.assertEqual(plain.coverage_phys, dressed.coverage_phys)

    def test_internal_degenerate_rotation_preserves_both_spectra(self):
        response = self.targets
        rotation = np.asarray(
            [[0.0, 1.0j], [1.0j, 0.0]],
            dtype=np.complex128,
        )

        baseline = self.measure(response)
        rotated = self.measure(response @ rotation)

        np.testing.assert_allclose(
            baseline.g_spectrum,
            rotated.g_spectrum,
            rtol=0.0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            baseline.c_spectrum,
            rotated.c_spectrum,
            rtol=0.0,
            atol=1e-12,
        )
        self.assertEqual(baseline.delta_geom_dof, rotated.delta_geom_dof)
        self.assertEqual(baseline.coverage_phys, rotated.coverage_phys)

    def test_roundoff_at_unit_interval_endpoints_is_canonicalized(self):
        rng = np.random.default_rng(88_031)

        def qr_columns(rows, columns):
            raw = (
                rng.normal(size=(rows, columns))
                + 1.0j * rng.normal(size=(rows, columns))
            ).astype(np.complex128)
            return np.linalg.qr(raw)[0][:, :columns]

        response = qr_columns(5, 3)
        kernel = qr_columns(5, 2)
        quotient = (rng.normal(size=(4, 5)) + 1.0j * rng.normal(size=(4, 5))).astype(
            np.complex128
        )
        raw_metric = (rng.normal(size=(4, 4)) + 1.0j * rng.normal(size=(4, 4))).astype(
            np.complex128
        )
        metric = (raw_metric.conj().T @ raw_metric + np.eye(4)).astype(np.complex128)
        targets = qr_columns(5, 2)

        result = compute_geometry_spectrum(
            response,
            kernel,
            quotient,
            metric,
            targets,
            thresholds=THRESHOLDS,
        )

        self.assertEqual(result.c_spectrum[-1], 1.0)
        for value in (*result.g_spectrum, *result.c_spectrum):
            self.assertTrue(math.isfinite(value))
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_three_frozen_rotation_audit_reports_hard_drift_bound(self):
        audit = audit_degenerate_rotations(
            self.targets,
            self.kernel,
            self.quotient,
            self.metric,
            self.targets,
            thresholds=THRESHOLDS,
        )

        self.assertEqual(
            tuple(row.seed for row in audit.rows),
            DEGENERATE_ROTATION_SEEDS,
        )
        self.assertLessEqual(audit.degenerate_rotation_drift_max, 1e-12)
        self.assertTrue(audit.passed)

    def test_rotation_audit_representation_mismatch_is_json_safe_undefined(self):
        response = np.asarray(
            [
                [math.sqrt(0.4), 0.0],
                [math.sqrt(0.6), 0.0],
                [0.0, 1.0],
            ],
            dtype=np.complex128,
        )
        audit = audit_degenerate_rotations(
            response,
            np.asarray([[0.0], [0.0], [1.0]], dtype=np.complex128),
            np.eye(3, dtype=np.complex128),
            np.eye(3, dtype=np.complex128),
            np.asarray([[1.0], [0.0], [0.0]], dtype=np.complex128),
            thresholds=THRESHOLDS,
        )

        self.assertFalse(audit.passed)
        self.assertIsNone(audit.degenerate_rotation_drift_max)
        self.assertTrue(any(row.row_drift_max is None for row in audit.rows))
        json.dumps(dataclasses.asdict(audit), allow_nan=False)

    def test_geometry_and_coverage_grey_bands_null_only_discrete_verdicts(self):
        angle = np.arcsin(0.05)
        response = np.asarray(
            [[np.cos(angle)], [0.0], [np.sin(angle)]],
            dtype=np.complex128,
        )
        geometry_grey = self.measure(response)

        self.assertTrue(geometry_grey.geometry_ambiguous)
        self.assertIsNone(geometry_grey.delta_geom_dof)
        self.assertGreater(geometry_grey.delta_geom_energy, 0.0)

        coverage_response = np.asarray(
            [[2.0**-0.5], [2.0**-0.5], [0.0]],
            dtype=np.complex128,
        )
        one_target = self.targets[:, :1]
        coverage_grey = compute_geometry_spectrum(
            coverage_response,
            self.kernel,
            self.quotient,
            self.metric,
            one_target,
            thresholds=THRESHOLDS,
        )

        self.assertTrue(coverage_grey.coverage_ambiguous)
        self.assertIsNone(coverage_grey.coverage_phys)
        self.assertIsNone(coverage_grey.rank_deficit)
        self.assertAlmostEqual(coverage_grey.c_spectrum[0], 0.5)

    def test_metric_validation_precedes_svd_and_never_clips(self):
        bad_metric = np.asarray(
            [[1.0, 0.5], [0.0, 1.0]],
            dtype=np.complex128,
        )
        with mock.patch(
            "numpy.linalg.svd",
            side_effect=AssertionError("SVD ran before metric validation"),
        ) as svd:
            with self.assertRaisesRegex(ValueError, "Hermitian"):
                compute_geometry_spectrum(
                    self.targets,
                    self.kernel,
                    self.quotient,
                    bad_metric,
                    self.targets,
                    thresholds=THRESHOLDS,
                )
        svd.assert_not_called()

    def test_arithmetic_work_cap_precedes_any_decomposition(self):
        scalar = np.zeros(1, dtype=np.complex128)
        response = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_500, 1_500),
            strides=(0, 0),
        )
        kernel = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_500, 1),
            strides=(0, 0),
        )
        quotient = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1, 1_500),
            strides=(0, 0),
        )
        targets = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_500, 1),
            strides=(0, 0),
        )
        with mock.patch(
            "numpy.linalg.eigh",
            side_effect=AssertionError("eigh ran before geometry work cap"),
        ) as eigh:
            with mock.patch(
                "numpy.linalg.svd",
                side_effect=AssertionError("SVD ran before geometry work cap"),
            ) as svd:
                with self.assertRaisesRegex(ValueError, "work cap"):
                    compute_geometry_spectrum(
                        response,
                        kernel,
                        quotient,
                        np.ones((1, 1), dtype=np.complex128),
                        targets,
                        thresholds=THRESHOLDS,
                    )
        eigh.assert_not_called()
        svd.assert_not_called()

    def test_rotation_audit_aggregate_work_cap_precedes_any_decomposition(self):
        scalar = np.zeros(1, dtype=np.complex128)
        response = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_000, 600),
            strides=(0, 0),
        )
        kernel = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_000, 1),
            strides=(0, 0),
        )
        quotient = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1, 1_000),
            strides=(0, 0),
        )
        targets = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_000, 1),
            strides=(0, 0),
        )
        with mock.patch(
            "numpy.linalg.eigh",
            side_effect=AssertionError("eigh ran before audit aggregate work cap"),
        ) as eigh:
            with mock.patch(
                "numpy.linalg.svd",
                side_effect=AssertionError("SVD ran before audit aggregate work cap"),
            ) as svd:
                with self.assertRaisesRegex(ValueError, "aggregate.*work cap"):
                    audit_degenerate_rotations(
                        response,
                        kernel,
                        quotient,
                        np.ones((1, 1), dtype=np.complex128),
                        targets,
                        thresholds=THRESHOLDS,
                    )
        eigh.assert_not_called()
        svd.assert_not_called()

    def test_work_cap_precedes_finite_scan_and_allocation(self):
        scalar = np.zeros(1, dtype=np.complex128)
        response = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_500, 1_500),
            strides=(0, 0),
        )
        kernel = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_500, 1),
            strides=(0, 0),
        )
        quotient = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1, 1_500),
            strides=(0, 0),
        )
        targets = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_500, 1),
            strides=(0, 0),
        )
        with mock.patch(
            "rulespace_v3.geometry.np.array",
            side_effect=AssertionError("allocation ran before work preflight"),
        ) as array:
            with mock.patch(
                "rulespace_v3.geometry.np.all",
                side_effect=AssertionError("finite scan ran before work preflight"),
            ) as all_values:
                with self.assertRaisesRegex(ValueError, "work cap"):
                    compute_geometry_spectrum(
                        response,
                        kernel,
                        quotient,
                        np.ones((1, 1), dtype=np.complex128),
                        targets,
                        thresholds=THRESHOLDS,
                    )
        array.assert_not_called()
        all_values.assert_not_called()

        response = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(16_000, 1),
            strides=(0, 0),
        )
        kernel = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(16_000, 1),
            strides=(0, 0),
        )
        quotient = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_000, 16_000),
            strides=(0, 0),
        )
        metric = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(1_000, 1_000),
            strides=(0, 0),
        )
        targets = np.lib.stride_tricks.as_strided(
            scalar,
            shape=(16_000, 1),
            strides=(0, 0),
        )
        with mock.patch(
            "rulespace_v3.geometry._materialize_matrix",
            side_effect=AssertionError(
                "geometry materialized before complete work preflight"
            ),
        ) as materialize:
            with self.assertRaisesRegex(ValueError, "work cap"):
                compute_geometry_spectrum(
                    response,
                    kernel,
                    quotient,
                    metric,
                    targets,
                    thresholds=THRESHOLDS,
                )
        materialize.assert_not_called()

    def test_unresolved_above_line_quotient_mode_is_never_silently_deleted(self):
        response = np.eye(2, dtype=np.complex128)
        kernel = np.eye(2, dtype=np.complex128)
        quotient = np.diag([1.0e8, 1.0e-6]).astype(np.complex128)
        targets = np.asarray([[0.0], [1.0]], dtype=np.complex128)

        with self.assertRaisesRegex(ValueError, "numerical rank"):
            compute_geometry_spectrum(
                response,
                kernel,
                quotient,
                np.eye(2, dtype=np.complex128),
                targets,
                thresholds=THRESHOLDS,
            )

    def test_geometry_and_coverage_lines_are_consumed_not_hardcoded(self):
        angle = np.arcsin(0.2)
        response = np.asarray(
            [[np.cos(angle)], [0.0], [np.sin(angle)]],
            dtype=np.complex128,
        )
        shifted = GeometryNumericalThresholds(
            signal_threshold=1e-12,
            geometry_threshold=0.3,
            geometry_ambiguity_half_width=0.01,
            coverage_threshold=0.8,
            coverage_ambiguity_half_width=0.01,
        )

        baseline = self.measure(response)
        changed = compute_geometry_spectrum(
            response,
            self.kernel,
            self.quotient,
            self.metric,
            self.targets,
            thresholds=shifted,
        )

        self.assertEqual(baseline.delta_geom_dof, 1.0)
        self.assertEqual(changed.delta_geom_dof, 0.0)


if __name__ == "__main__":
    unittest.main()
