from __future__ import annotations

import dataclasses
import unittest
from unittest import mock

import numpy as np

from rulespace_v3.factory import (
    freeze_complex_tensor,
    frozen_tensor_array,
)
from rulespace_v3.registry import ControlReadoutCalibrationSpec

from rulespace_v3.blocks import (
    ResponseBlock,
    VerifiedResponseBlock,
    _derive_response_block_matrices,
    _freeze_block_matrix,
    response_block_payload,
    verify_selected_control_response_block,
)


def _readout_spec(
    *,
    source: np.ndarray | None = None,
    readout: np.ndarray | None = None,
    incidence: np.ndarray | None = None,
    curvature: np.ndarray | None = None,
) -> ControlReadoutCalibrationSpec:
    source_values = np.eye(2, dtype=np.complex128) if source is None else source
    readout_values = np.eye(2, dtype=np.complex128) if readout is None else readout
    incidence_values = (
        np.eye(2, dtype=np.complex128) if incidence is None else incidence
    )
    curvature_values = (
        np.eye(2, dtype=np.complex128) if curvature is None else curvature
    )
    provisional = ControlReadoutCalibrationSpec(
        spec_schema_version="v3m0.control-readout-calibration-spec.v1",
        source_metric_whitener=freeze_complex_tensor(source_values),
        h_metric_whitener=freeze_complex_tensor(readout_values),
        curvature_incidence_operator=freeze_complex_tensor(incidence_values),
        curvature_metric_whitener=freeze_complex_tensor(curvature_values),
        curvature_normalizer_id="synthetic-identity-v1",
        spec_sha="0" * 64,
    )
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.registry import readout_calibration_spec_payload

    return dataclasses.replace(
        provisional,
        spec_sha=canonical_sha(readout_calibration_spec_payload(provisional)),
    )


class ResponseBlockNumericalTests(unittest.TestCase):
    def test_identity_metrics_freeze_branch_specific_five_matrix_chain(
        self,
    ) -> None:
        values = np.asarray(
            (
                ((2.0 + 0.0j, 0.0 + 0.0j), (0.0 + 0.0j, 0.0 + 0.0j)),
                ((1.0 + 0.0j, 0.0 + 0.0j), (0.0 + 0.0j, 0.0 + 0.0j)),
            ),
            dtype=np.complex128,
        )
        matrices = _derive_response_block_matrices(
            values,
            _readout_spec(),
            h_signal_threshold=0.5,
            curvature_signal_threshold=0.5,
        )

        self.assertEqual(matrices.q_all.shape, (2, 2))
        self.assertEqual(matrices.q_active.shape, (2, 1))
        self.assertEqual(matrices.v_curv.shape, (1, 1))
        self.assertEqual(matrices.q_curv.shape, (2, 1))
        self.assertEqual(matrices.s_curv.shape, (4, 1))
        self.assertLessEqual(matrices.q_all_orth_residual, 1.0e-12)
        self.assertLessEqual(matrices.q_active_orth_residual, 1.0e-12)
        self.assertLessEqual(matrices.q_curv_orth_residual, 1.0e-12)
        self.assertLessEqual(matrices.s_curv_hermitian_residual, 1.0e-12)
        self.assertEqual(matrices.active_rank, 1)
        self.assertEqual(matrices.curvature_rank, 1)

    def test_metric_whitening_and_curvature_operator_are_mechanical(
        self,
    ) -> None:
        values = np.asarray(
            (((1.0 + 0.0j, 0.0 + 0.0j), (0.0 + 0.0j, 0.25 + 0.0j)),),
            dtype=np.complex128,
        )
        spec = _readout_spec(
            source=np.diag((2.0, 1.0)).astype(np.complex128),
            readout=np.diag((1.0, 2.0)).astype(np.complex128),
            incidence=np.diag((1.0, 0.0)).astype(np.complex128),
            curvature=np.eye(2, dtype=np.complex128),
        )
        matrices = _derive_response_block_matrices(
            values,
            spec,
            h_signal_threshold=0.1,
            curvature_signal_threshold=0.1,
        )

        self.assertEqual(matrices.active_rank, 2)
        self.assertEqual(matrices.curvature_rank, 1)
        self.assertLessEqual(matrices.q_all_orth_residual, 1.0e-12)

    def test_nonpositive_or_numerically_unresolved_metric_fails_closed(
        self,
    ) -> None:
        values = np.eye(2, dtype=np.complex128)[None, :, :]
        bad_specs = (
            _readout_spec(source=np.diag((1.0, 0.0)).astype(np.complex128)),
            _readout_spec(readout=np.diag((1.0, -1.0)).astype(np.complex128)),
        )
        for spec in bad_specs:
            with self.subTest(spec=spec.spec_sha):
                with self.assertRaisesRegex(
                    ValueError,
                    "positive|invertible",
                ):
                    _derive_response_block_matrices(
                        values,
                        spec,
                        h_signal_threshold=1.0e-12,
                        curvature_signal_threshold=1.0e-12,
                    )

    def test_metric_null_direction_requires_an_explicit_quotient(
        self,
    ) -> None:
        values = np.eye(2, dtype=np.complex128)[None, :, :]
        singular = _readout_spec(curvature=np.diag((1.0, 0.0)).astype(np.complex128))
        with self.assertRaisesRegex(
            ValueError,
            "positive|quotient|invertible",
        ):
            _derive_response_block_matrices(
                values,
                singular,
                h_signal_threshold=0.1,
                curvature_signal_threshold=0.1,
            )

    def test_exact_null_response_has_explicit_zero_ranks(self) -> None:
        values = np.zeros((2, 2, 2), dtype=np.complex128)
        matrices = _derive_response_block_matrices(
            values,
            _readout_spec(),
            h_signal_threshold=0.1,
            curvature_signal_threshold=0.1,
        )
        self.assertEqual(matrices.active_rank, 0)
        self.assertEqual(matrices.curvature_rank, 0)
        self.assertEqual(matrices.q_active.shape, (2, 0))
        self.assertEqual(matrices.v_curv.shape, (0, 0))
        self.assertEqual(matrices.q_curv.shape, (2, 0))
        self.assertEqual(matrices.s_curv.shape, (4, 0))
        for raw in (
            matrices.q_active,
            matrices.v_curv,
            matrices.q_curv,
            matrices.s_curv,
        ):
            frozen = _freeze_block_matrix(raw)
            self.assertTrue(all(size > 0 for size in frozen.shape))
            self.assertTrue(
                np.array_equal(
                    frozen_tensor_array(frozen),
                    np.zeros(frozen.shape, dtype=np.complex128),
                )
            )

    def test_frozen_matrix_views_are_fresh_and_cannot_mutate_evidence(
        self,
    ) -> None:
        values = np.eye(2, dtype=np.complex128)[None, :, :]
        matrices = _derive_response_block_matrices(
            values,
            _readout_spec(),
            h_signal_threshold=0.1,
            curvature_signal_threshold=0.1,
        )
        frozen = freeze_complex_tensor(matrices.q_all)
        first = frozen_tensor_array(frozen)
        first[0, 0] = 99.0
        second = frozen_tensor_array(frozen)
        self.assertEqual(second[0, 0], 1.0 + 0.0j)

    def test_aggregate_work_cap_precedes_metric_or_column_decomposition(
        self,
    ) -> None:
        dimension = 407
        identity = np.eye(dimension, dtype=np.complex128)
        values = identity[None, :, :].copy()
        spec = _readout_spec(
            source=identity,
            readout=identity,
            incidence=identity,
            curvature=identity,
        )
        with (
            mock.patch.object(
                np.linalg,
                "eigh",
                side_effect=AssertionError("metric decomposition ran first"),
            ) as eigh,
            mock.patch.object(
                np.linalg,
                "svd",
                side_effect=AssertionError("SVD ran first"),
            ) as svd,
        ):
            with self.assertRaisesRegex(ValueError, "work cap"):
                _derive_response_block_matrices(
                    values,
                    spec,
                    h_signal_threshold=0.1,
                    curvature_signal_threshold=0.1,
                )
        eigh.assert_not_called()
        svd.assert_not_called()


class ResponseBlockAuthorityTests(unittest.TestCase):
    def test_raw_or_object_new_block_is_not_a_runtime_authority(self) -> None:
        fake_response = object()
        fake_calibration = object()
        raw = object.__new__(ResponseBlock)
        with self.assertRaises((TypeError, ValueError)):
            verify_selected_control_response_block(
                raw,
                fake_response,
                fake_calibration,
                "actual",
            )
        fake = object.__new__(VerifiedResponseBlock)
        with self.assertRaises((TypeError, ValueError)):
            fake.block

    def test_block_wire_registry_includes_full_response_and_five_matrices(
        self,
    ) -> None:
        self.assertEqual(
            tuple(ResponseBlock.__dataclass_fields__),
            (
                "block_schema_version",
                "branch",
                "source_readout_response",
                "response_sha",
                "pair_sha",
                "operator_spec",
                "q_all",
                "q_active",
                "v_curv",
                "q_curv",
                "s_curv",
                "audit",
                "paired_response_sha",
                "calibration_manifest_sha",
                "selected_fejer_order",
                "application_authority_sha",
                "block_sha",
            ),
        )
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            response_block_payload(object.__new__(ResponseBlock))


if __name__ == "__main__":
    unittest.main()
