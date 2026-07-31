from __future__ import annotations

import unittest
from unittest import mock

import numpy as np

from rulespace_v3.linalg import (
    canonical_orthonormal_columns,
    hermitian_positive_whitener,
    whiten_quotient_columns,
)


class V3M0LinearAlgebraTests(unittest.TestCase):
    def test_positive_hermitian_metric_has_audited_sqrt_and_inverse(self):
        metric = np.array(
            [
                [2.0 + 0.0j, 0.0 + 0.25j],
                [0.0 - 0.25j, 1.5 + 0.0j],
            ],
            dtype=np.complex128,
        )

        whitening = hermitian_positive_whitener(metric)

        np.testing.assert_allclose(
            whitening.sqrt_metric.conj().T @ whitening.sqrt_metric,
            metric,
            rtol=0.0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            whitening.inverse_sqrt_metric @ whitening.sqrt_metric,
            np.eye(2, dtype=np.complex128),
            rtol=0.0,
            atol=1e-12,
        )
        self.assertGreater(whitening.minimum_eigenvalue, 0.0)
        self.assertLessEqual(whitening.hermitian_residual, 1e-12)
        self.assertLessEqual(whitening.reconstruction_residual, 1e-12)
        self.assertLessEqual(whitening.inverse_residual, 1e-12)

        whitening.sqrt_metric[0, 0] = 99.0
        fresh = hermitian_positive_whitener(metric)
        self.assertNotEqual(fresh.sqrt_metric[0, 0], 99.0)

    def test_nonhermitian_or_nonpositive_metric_is_rejected_without_clipping(self):
        nonhermitian = np.array(
            [[1.0, 0.5], [0.0, 1.0]],
            dtype=np.complex128,
        )
        singular = np.diag([1.0, 0.0]).astype(np.complex128)
        indefinite = np.diag([1.0, -0.1]).astype(np.complex128)

        with self.assertRaisesRegex(ValueError, "Hermitian"):
            hermitian_positive_whitener(nonhermitian)
        with self.assertRaisesRegex(ValueError, "positive"):
            hermitian_positive_whitener(singular)
        with self.assertRaisesRegex(ValueError, "positive"):
            hermitian_positive_whitener(indefinite)

    def test_resource_shape_preflight_precedes_eigendecomposition(self):
        oversized = np.lib.stride_tricks.as_strided(
            np.zeros(1, dtype=np.complex128),
            shape=(4_097, 4_097),
            strides=(0, 0),
        )
        with mock.patch(
            "numpy.linalg.eigh",
            side_effect=AssertionError("eigh ran before the resource cap"),
        ) as eigh:
            with self.assertRaisesRegex(ValueError, "resource cap"):
                hermitian_positive_whitener(oversized)
        eigh.assert_not_called()

        cubic_work = np.lib.stride_tricks.as_strided(
            np.zeros(1, dtype=np.complex128),
            shape=(1_500, 1_500),
            strides=(0, 0),
        )
        with mock.patch(
            "numpy.linalg.eigh",
            side_effect=AssertionError("eigh ran before the work cap"),
        ) as eigh:
            with self.assertRaisesRegex(ValueError, "work cap"):
                hermitian_positive_whitener(cubic_work)
        eigh.assert_not_called()

    def test_canonical_column_basis_is_input_basis_invariant(self):
        columns = np.array(
            [
                [1.0, 1.0j],
                [1.0j, 1.0],
                [0.5, -0.25j],
            ],
            dtype=np.complex128,
        )
        internal_unitary = np.array(
            [[0.0, 1.0j], [1.0j, 0.0]],
            dtype=np.complex128,
        )

        first = canonical_orthonormal_columns(columns, absolute_threshold=1e-12)
        second = canonical_orthonormal_columns(
            columns @ internal_unitary,
            absolute_threshold=1e-12,
        )

        np.testing.assert_allclose(first, second, rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(
            first.conj().T @ first,
            np.eye(first.shape[1], dtype=np.complex128),
            rtol=0.0,
            atol=1e-12,
        )
        with self.assertRaisesRegex(ValueError, "strictly positive"):
            canonical_orthonormal_columns(
                columns,
                absolute_threshold=0.0,
            )

    def test_canonical_basis_does_not_apply_singular_cutoff_to_projected_axes(self):
        diffuse = np.full((400, 1), 0.05 + 0.0j, dtype=np.complex128)

        basis = canonical_orthonormal_columns(
            diffuse,
            absolute_threshold=0.5,
            expected_rank=1,
        )

        self.assertEqual(basis.shape, (400, 1))
        np.testing.assert_allclose(
            basis.conj().T @ basis,
            np.ones((1, 1), dtype=np.complex128),
            rtol=0.0,
            atol=1e-12,
        )

    def test_metric_null_direction_is_removed_only_by_frozen_quotient(self):
        full_columns = np.eye(2, dtype=np.complex128)
        quotient_map = np.array([[1.0, 0.0]], dtype=np.complex128)
        quotient_metric = np.array([[2.0]], dtype=np.complex128)

        result = whiten_quotient_columns(
            full_columns,
            quotient_map,
            quotient_metric,
            absolute_threshold=1e-12,
        )

        self.assertEqual(result.quotient_rank, 1)
        self.assertEqual(result.whitened_basis.shape, (1, 1))
        np.testing.assert_allclose(
            result.whitened_basis.conj().T @ result.whitened_basis,
            np.ones((1, 1), dtype=np.complex128),
            rtol=0.0,
            atol=1e-12,
        )
        self.assertLessEqual(result.orthogonality_residual, 1e-12)

        with mock.patch(
            "numpy.linalg.svd",
            side_effect=AssertionError("SVD ran before metric validation"),
        ) as svd:
            with self.assertRaisesRegex(ValueError, "positive"):
                whiten_quotient_columns(
                    full_columns,
                    np.eye(2, dtype=np.complex128),
                    np.diag([2.0, 0.0]).astype(np.complex128),
                    absolute_threshold=1e-12,
                )
        svd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
