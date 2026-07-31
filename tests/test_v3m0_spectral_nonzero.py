from __future__ import annotations

import base64
import inspect
import math
import struct
import unittest
from fractions import Fraction
from types import SimpleNamespace
from unittest import mock

import numpy as np

import rulespace_v3.spectral as spectral
from rulespace_v3.calibration_authority import (
    build_c04_canonical_angle_recipe,
)
from rulespace_v3.dynamics import VerifiedTransition
from rulespace_v3.fp64_protocol import build_fp64_enclosure_protocol
from rulespace_v3.grids import build_dynamics_grid_manifest
from rulespace_v3.metric import StabilityMetricWitness


def _c04_laurent_coefficients(
) -> tuple[np.ndarray, tuple[tuple[int, ...], ...]]:
    """Compile the analytic C04 local shears without any live Parent."""

    recipe = build_c04_canonical_angle_recipe()
    channel_index = {
        channel: index for index, channel in enumerate(recipe.channel_order)
    }
    state_count = len(recipe.channel_order)
    coefficients = {
        0: np.eye(state_count, dtype=np.complex128),
    }
    for step in recipe.steps:
        generator = np.zeros(
            (state_count, state_count),
            dtype=np.complex128,
        )
        generator[
            channel_index[step.destination_channel],
            channel_index[step.source_channel],
        ] = step.coefficient
        updated = {
            exponent: matrix.copy()
            for exponent, matrix in coefficients.items()
        }
        for exponent, matrix in coefficients.items():
            shifted = exponent + step.offset[0]
            updated.setdefault(
                shifted,
                np.zeros(
                    (state_count, state_count),
                    dtype=np.complex128,
                ),
            )
            updated[shifted] += generator @ matrix
        coefficients = updated

    for exponent, matrix in coefficients.items():
        if exponent < -2 or exponent > 2:
            np.testing.assert_array_equal(matrix, np.zeros_like(matrix))
    support = tuple((offset,) for offset in range(-2, 3))
    # The recipe uses exp(+ik o), while the Laurent witness uses exp(-ik d).
    values = np.stack(
        tuple(coefficients[-offset] for (offset,) in support),
        axis=0,
    )
    return values, support


class NonzeroSpectralScalarCandidateTests(unittest.TestCase):
    def test_public_builder_dispatches_nonzero_support_to_full64_lane(
        self,
    ) -> None:
        transition = object.__new__(VerifiedTransition)
        object.__setattr__(
            transition,
            "_VerifiedTransition__transition",
            SimpleNamespace(support_offsets=((-1,), (0,), (1,))),
        )
        metric = object.__new__(StabilityMetricWitness)
        object.__setattr__(metric, "metric_support_offsets", ((0,),))
        protocol = object()
        expected = object()
        with (
            mock.patch.object(
                spectral,
                "_expected_nonzero_coverage",
                return_value=expected,
            ) as nonzero,
            mock.patch.object(
                spectral,
                "_expected_exact_zero_coverage",
                side_effect=AssertionError("exact-zero lane selected"),
            ),
        ):
            observed = spectral.build_spectral_margin_coverage(
                transition,
                metric,
                protocol,
            )
        self.assertIs(observed, expected)
        nonzero.assert_called_once_with(transition, metric, protocol)

    def test_scalar_gauss_jordan_supports_general_complex_matrices(self) -> None:
        matrix = np.asarray(
            (
                (1.0 + 0.0j, 0.0 + 0.25j),
                (0.0 - 0.25j, 1.0 + 0.0j),
            ),
            dtype=np.complex128,
        )
        inverse = spectral._scalar_gauss_jordan_inverse(matrix)
        self.assertLessEqual(
            float(np.linalg.norm(inverse @ matrix - np.eye(2), ord="fro")),
            2.0e-15,
        )

    def test_scalar_cholesky_supports_general_hermitian_positive_metric(
        self,
    ) -> None:
        metric = np.asarray(
            (
                (1.0 + 0.0j, 0.0 + 0.25j),
                (0.0 - 0.25j, 1.0 + 0.0j),
            ),
            dtype=np.complex128,
        )
        factor = spectral._scalar_hermitian_cholesky(metric)
        inverse = spectral._scalar_lower_triangular_inverse(factor)
        self.assertLessEqual(
            float(np.linalg.norm(factor @ factor.conj().T - metric, ord="fro")),
            2.0e-15,
        )
        self.assertLessEqual(
            float(np.linalg.norm(inverse @ factor - np.eye(2), ord="fro")),
            2.0e-15,
        )

    def test_root64_symbol_witness_uses_table_center_without_runtime_trig(
        self,
    ) -> None:
        protocol = build_fp64_enclosure_protocol()
        # M(k)=Σ_d K_d exp(-ikd), so d=+1 at n=8 uses root -8 mod 64.
        entry = protocol.root_interval_table.entries[56]
        expected = complex(
            struct.unpack(">d", struct.pack(">Q", entry.real_center_f64_bits))[0],
            struct.unpack(">d", struct.pack(">Q", entry.imag_center_f64_bits))[0],
        )
        identity = np.eye(2, dtype=np.complex128)[None, :, :]
        with (
            mock.patch("math.sin", side_effect=AssertionError("runtime sin")),
            mock.patch("math.cos", side_effect=AssertionError("runtime cos")),
            mock.patch("math.exp", side_effect=AssertionError("runtime exp")),
        ):
            center, error = spectral._laurent_symbol_center_and_error(
                identity,
                ((1,),),
                (8,),
                protocol,
            )
        np.testing.assert_array_equal(center, expected * np.eye(2))
        self.assertGreater(error, 0.0)

    def test_nonzero_hard_point_uses_no_lapack_and_has_positive_margins(
        self,
    ) -> None:
        protocol = build_fp64_enclosure_protocol()
        identity = np.eye(2, dtype=np.complex128)[None, :, :]
        with (
            mock.patch(
                "numpy.linalg.inv",
                side_effect=AssertionError("LAPACK inverse"),
            ),
            mock.patch(
                "numpy.linalg.cholesky",
                side_effect=AssertionError("LAPACK Cholesky"),
            ),
            mock.patch(
                "numpy.linalg.svd",
                side_effect=AssertionError("LAPACK SVD"),
            ),
            mock.patch(
                "numpy.linalg.eigh",
                side_effect=AssertionError("LAPACK eigh"),
            ),
        ):
            point, _, _ = spectral._hard_spectral_point(
                identity,
                ((1,),),
                identity,
                ((0,),),
                (8,),
                protocol,
            )
        self.assertEqual(set(point), set(spectral.HARD_COLUMN_NAMES))
        self.assertTrue(all(math.isfinite(value) for value in point.values()))
        self.assertGreater(point["transition_symbol_error_upper_b64"], 0.0)
        self.assertGreater(point["metric_symbol_error_upper_b64"], 0.0)
        self.assertGreater(point["m_sigma_min_lower_b64"], 0.0)
        self.assertGreater(point["g_lambda_min_lower_b64"], 0.0)

    def test_nonzero_builder_does_not_retain_point_candidate_matrices(
        self,
    ) -> None:
        source = inspect.getsource(spectral._expected_nonzero_coverage)
        self.assertNotIn("transition_centers", source)
        self.assertNotIn("metric_centers", source)
        self.assertNotIn("list[np.ndarray]", source)
        self.assertIn("for reciprocal_index in grid.reciprocal_indices", source)

    def test_unavailable_optional_diagnostics_emit_exactly_fourteen_columns(
        self,
    ) -> None:
        identity = np.eye(2, dtype=np.complex128)
        with mock.patch(
            "numpy.linalg.svd",
            side_effect=ValueError("diagnostic unavailable"),
        ):
            self.assertIsNone(
                spectral._optional_raw_point_diagnostic(identity, identity)
            )
        grid = build_dynamics_grid_manifest(((1,),), ((0,),))
        sidecar = spectral._build_columnar_sidecar(
            grid=grid,
            n_state=2,
            hard_columns={
                name: (1.0,) * 64 for name in spectral.HARD_COLUMN_NAMES
            },
            raw_columns=None,
            unavailable_reason="lapack-diagnostics-unavailable-v1",
        )
        self.assertEqual(sidecar.raw_diagnostic_status, "unavailable-v1")
        self.assertEqual(
            sidecar.raw_byte_count,
            64 * 8 * spectral.SPECTRAL_HARD_COLUMN_COUNT,
        )

    def test_parent_independent_c04_full64_hard_margins_and_columns(
        self,
    ) -> None:
        coefficients, support = _c04_laurent_coefficients()
        metric_coefficients = np.eye(4, dtype=np.complex128)[None, :, :]
        metric_support = ((0,),)
        protocol = build_fp64_enclosure_protocol()
        grid = build_dynamics_grid_manifest(support, metric_support)
        self.assertEqual(grid.qualification_profile, "cartesian-full-64-v1")
        self.assertEqual(grid.torus_denominators, (64,))
        self.assertEqual(
            grid.reciprocal_indices,
            tuple((index,) for index in range(64)),
        )

        points = []
        with (
            mock.patch("math.sin", side_effect=AssertionError("runtime sin")),
            mock.patch("math.cos", side_effect=AssertionError("runtime cos")),
            mock.patch("math.exp", side_effect=AssertionError("runtime exp")),
            mock.patch(
                "numpy.linalg.inv",
                side_effect=AssertionError("LAPACK inverse"),
            ),
            mock.patch(
                "numpy.linalg.cholesky",
                side_effect=AssertionError("LAPACK Cholesky"),
            ),
            mock.patch(
                "numpy.linalg.svd",
                side_effect=AssertionError("LAPACK SVD"),
            ),
            mock.patch(
                "numpy.linalg.eigvalsh",
                side_effect=AssertionError("LAPACK eigvalsh"),
            ),
            mock.patch(
                "numpy.linalg.eigvals",
                side_effect=AssertionError("LAPACK eigvals"),
            ),
        ):
            for reciprocal_index in grid.reciprocal_indices:
                point, _, _ = spectral._hard_spectral_point(
                    coefficients,
                    support,
                    metric_coefficients,
                    metric_support,
                    reciprocal_index,
                    protocol,
                )
                points.append(point)
        self.assertEqual(len(points), 64)
        self.assertTrue(
            all(set(point) == set(spectral.HARD_COLUMN_NAMES) for point in points)
        )

        hard_columns = {
            name: tuple(point[name] for point in points)
            for name in spectral.HARD_COLUMN_NAMES
        }
        m_derivative = spectral._axis_derivative_bounds(
            coefficients,
            support,
        )
        g_derivative = spectral._axis_derivative_bounds(
            metric_coefficients,
            metric_support,
        )
        table = protocol.root_interval_table
        fill = spectral._fraction_upper_float(
            Fraction(
                table.pi_upper_numerator,
                (1 << table.dyadic_exponent) * 64,
            ),
            "test fill",
        )
        m_increment = spectral._coverage_increment(fill, m_derivative)
        g_increment = spectral._coverage_increment(fill, g_derivative)
        covered_m_min = spectral.directed_sub_lower(
            min(hard_columns["m_sigma_min_lower_b64"]),
            m_increment,
        )
        covered_m_max = spectral.directed_add_upper(
            max(hard_columns["m_sigma_max_upper_b64"]),
            m_increment,
        )
        covered_g_min = spectral.directed_sub_lower(
            min(hard_columns["g_lambda_min_lower_b64"]),
            g_increment,
        )
        covered_g_max = spectral.directed_add_upper(
            max(hard_columns["g_lambda_max_upper_b64"]),
            g_increment,
        )
        m_condition = spectral.directed_div_upper(
            covered_m_max,
            covered_m_min,
        )
        g_condition = spectral.directed_div_upper(
            covered_g_max,
            covered_g_min,
        )
        self.assertAlmostEqual(
            min(hard_columns["m_sigma_min_lower_b64"]),
            0.5,
            delta=2.0e-14,
        )
        self.assertAlmostEqual(m_derivative[0], 3.322007801916572, places=14)
        self.assertAlmostEqual(m_increment, 0.16306867665107944, places=14)
        self.assertAlmostEqual(covered_m_min, 0.3369313233489113, places=14)
        self.assertAlmostEqual(m_condition, 6.419909716767732, places=13)
        self.assertEqual(g_derivative, (+0.0,))
        self.assertEqual(g_increment, +0.0)
        self.assertAlmostEqual(covered_g_min, 0.25, delta=8.0e-15)
        self.assertAlmostEqual(g_condition, 8.0, delta=2.0e-13)
        self.assertGreaterEqual(
            covered_m_min,
            spectral.SPECTRAL_M_SIGMA_MIN_GATE,
        )
        self.assertLessEqual(m_condition, spectral.SPECTRAL_CONDITION_MAX)
        self.assertGreaterEqual(
            covered_g_min,
            spectral.SPECTRAL_G_LAMBDA_MIN_GATE,
        )
        self.assertLessEqual(g_condition, spectral.SPECTRAL_CONDITION_MAX)

        unavailable = spectral._build_columnar_sidecar(
            grid=grid,
            n_state=4,
            hard_columns=hard_columns,
            raw_columns=None,
            unavailable_reason="lapack-diagnostics-unavailable-v1",
        )
        self.assertEqual(
            unavailable.raw_byte_count,
            64 * 8 * spectral.SPECTRAL_HARD_COLUMN_COUNT,
        )
        for name in spectral.HARD_COLUMN_NAMES:
            column = getattr(unavailable, name)
            self.assertEqual(len(base64.b64decode(column, validate=True)), 64 * 8)

        available = spectral._build_columnar_sidecar(
            grid=grid,
            n_state=4,
            hard_columns=hard_columns,
            raw_columns={
                name: (+1.0,) * 64 for name in spectral.RAW_COLUMN_NAMES
            },
            unavailable_reason=None,
        )
        self.assertEqual(
            available.raw_byte_count,
            64 * 8 * spectral.SPECTRAL_AVAILABLE_COLUMN_COUNT,
        )


if __name__ == "__main__":
    unittest.main()
