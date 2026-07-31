from __future__ import annotations

import dataclasses
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from rulespace_v3.blocks import ResponseBlock, VerifiedResponseBlock
from rulespace_v3.causal import (
    CausalResult,
    SurvivalThresholdCalibration,
    SurvivalThresholdControlEvidence,
    SurvivalThresholdInstanceAudit,
    VerifiedSurvivalThresholdCalibration,
    calibrate_survival_threshold,
    compute_causal_survival,
    survival_threshold_calibration_payload,
    survival_threshold_control_evidence_payload,
    survival_threshold_instance_audit_payload,
    verify_survival_threshold_calibration,
)
from rulespace_v3.factory import freeze_complex_tensor


class V3M0CausalAuthorityContractTests(unittest.TestCase):
    def test_frozen_wire_shapes_match_the_taskbook(self) -> None:
        self.assertEqual(
            tuple(SurvivalThresholdInstanceAudit.__dataclass_fields__),
            (
                "audit_schema_version",
                "application_spec",
                "permit",
                "actual_block",
                "ablated_block",
                "survival_spectrum",
                "measured_side_labels",
                "expected_side_labels",
                "signed_threshold_margins",
                "minimum_absolute_margin",
                "audit_sha",
            ),
        )
        self.assertEqual(
            tuple(SurvivalThresholdControlEvidence.__dataclass_fields__),
            (
                "evidence_schema_version",
                "parent_freeze",
                "instance_audits",
                "evidence_sha",
            ),
        )
        self.assertEqual(
            tuple(SurvivalThresholdCalibration.__dataclass_fields__),
            (
                "calibration_schema_version",
                "tau_surv",
                "ambiguity_half_width",
                "control_evidence",
                "calibration_sha",
            ),
        )
        self.assertEqual(
            tuple(CausalResult.__dataclass_fields__),
            (
                "survival_spectrum",
                "epsilon_dof",
                "epsilon_cont",
                "chi_extra",
                "kappa_map",
                "d_proc_sq",
                "gain_ratio",
                "phase_shift",
                "ambiguous",
            ),
        )
        for record_type in (
            SurvivalThresholdInstanceAudit,
            SurvivalThresholdControlEvidence,
            SurvivalThresholdCalibration,
            CausalResult,
        ):
            self.assertTrue(
                record_type.__dataclass_params__.frozen,
                record_type.__name__,
            )

    def test_opaque_threshold_is_module_issued_only(self) -> None:
        with self.assertRaises(TypeError):
            VerifiedSurvivalThresholdCalibration(
                object(),
                object.__new__(SurvivalThresholdCalibration),
                "0" * 64,
            )
        fake = object.__new__(VerifiedSurvivalThresholdCalibration)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            fake.calibration

    def test_calibration_requires_nonempty_aligned_live_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            calibrate_survival_threshold((), ())
        with self.assertRaisesRegex(ValueError, "same length"):
            calibrate_survival_threshold(((object(), object()),), ())
        with self.assertRaises((TypeError, ValueError)):
            calibrate_survival_threshold(
                ((object(), object()),),
                (object(),),
            )

    def test_evaluator_rejects_raw_and_forged_response_blocks(self) -> None:
        raw = object.__new__(ResponseBlock)
        fake_threshold = object.__new__(VerifiedSurvivalThresholdCalibration)
        with self.assertRaisesRegex(TypeError, "VerifiedResponseBlock"):
            compute_causal_survival(raw, raw, fake_threshold)

        forged = object.__new__(VerifiedResponseBlock)
        with self.assertRaises((TypeError, ValueError)):
            compute_causal_survival(forged, forged, fake_threshold)

    def test_hydration_rejects_raw_or_incomplete_evidence_before_hashing(self) -> None:
        raw = object.__new__(SurvivalThresholdCalibration)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            verify_survival_threshold_calibration(raw, (), ())
        for payload_builder, record_type in (
            (
                survival_threshold_instance_audit_payload,
                SurvivalThresholdInstanceAudit,
            ),
            (
                survival_threshold_control_evidence_payload,
                SurvivalThresholdControlEvidence,
            ),
            (
                survival_threshold_calibration_payload,
                SurvivalThresholdCalibration,
            ),
        ):
            with self.subTest(payload=payload_builder.__name__):
                with self.assertRaises((TypeError, ValueError, AttributeError)):
                    payload_builder(object.__new__(record_type))

    def test_opaque_wrapper_is_not_a_serializable_dataclass(self) -> None:
        self.assertFalse(dataclasses.is_dataclass(VerifiedSurvivalThresholdCalibration))


class V3M0CausalBlockConsumptionTests(unittest.TestCase):
    @staticmethod
    def _raw_pair():
        identity = freeze_complex_tensor(np.eye(3, dtype=np.complex128))
        q_all = freeze_complex_tensor(np.eye(2, dtype=np.complex128))
        actual_q_curv = freeze_complex_tensor(
            np.asarray(((1.0 + 0.0j,), (0.0 + 0.0j,)), dtype=np.complex128)
        )
        ablated_q_curv = freeze_complex_tensor(
            np.asarray(((0.0 + 0.0j,), (1.0 + 0.0j,)), dtype=np.complex128)
        )
        actual_values = freeze_complex_tensor(
            np.asarray(
                (
                    (
                        (1.0 + 0.0j, 0.0 + 0.0j),
                        (0.0 + 0.0j, 1.0 + 0.0j),
                        (0.0 + 0.0j, 0.0 + 0.0j),
                    ),
                ),
                dtype=np.complex128,
            )
        )
        ablated_values = freeze_complex_tensor(
            np.asarray(
                (
                    (
                        (0.5 + 0.0j, 0.0 + 0.0j),
                        (np.sqrt(0.75) + 0.0j, 0.0 + 0.0j),
                        (0.0 + 0.0j, 1.0 + 0.0j),
                    ),
                ),
                dtype=np.complex128,
            )
        )
        operator = SimpleNamespace(
            curvature_incidence_operator=identity,
            curvature_metric_whitener=identity,
        )
        source_basis = object()
        readout_basis = object()

        def response(branch, values):
            return SimpleNamespace(
                branch=branch,
                values=values,
                source_basis=source_basis,
                readout_basis=readout_basis,
                run_spec_sha="1" * 64,
            )

        common = dict(
            pair_sha="2" * 64,
            paired_response_sha="3" * 64,
            calibration_manifest_sha="4" * 64,
            selected_fejer_order=256,
            application_authority_sha="5" * 64,
            operator_spec=operator,
            q_all=q_all,
        )
        actual = SimpleNamespace(
            **common,
            branch="actual",
            source_readout_response=response("actual", actual_values),
            q_curv=actual_q_curv,
            audit=SimpleNamespace(curvature_rank=1),
        )
        ablated = SimpleNamespace(
            **common,
            branch="matched_ablated",
            source_readout_response=response(
                "matched_ablated",
                ablated_values,
            ),
            q_curv=ablated_q_curv,
            audit=SimpleNamespace(curvature_rank=1),
        )
        return actual, ablated

    def test_actual_sector_is_applied_to_ablated_response_and_full_source(self) -> None:
        actual_raw, ablated_raw = self._raw_pair()
        actual = object.__new__(VerifiedResponseBlock)
        ablated = object.__new__(VerifiedResponseBlock)
        threshold = object.__new__(VerifiedSurvivalThresholdCalibration)
        selection = SimpleNamespace(
            curv_tau_sig=1.0e-12,
            curv_noise_ref=0.0,
        )
        permit = SimpleNamespace(
            selection=selection,
            calibration_manifest=SimpleNamespace(
                calibration_manifest_sha="4" * 64
            ),
        )
        calibration = SimpleNamespace(
            control_evidence=SimpleNamespace(
                instance_audits=(SimpleNamespace(permit=permit),)
            )
        )
        block_views = (
            SimpleNamespace(block=actual_raw),
            SimpleNamespace(block=ablated_raw),
        )
        with (
            mock.patch(
                "rulespace_v3.causal._reverify_verified_response_block",
                side_effect=block_views,
            ),
            mock.patch(
                "rulespace_v3.causal."
                "_reverify_verified_survival_threshold_calibration",
                return_value=calibration,
            ),
        ):
            result = compute_causal_survival(actual, ablated, threshold)

        self.assertAlmostEqual(result.survival_spectrum[0], 0.25)
        self.assertEqual(result.epsilon_dof, 0.0)
        self.assertAlmostEqual(result.epsilon_cont, 0.25)
        self.assertAlmostEqual(result.chi_extra, 0.875)

    def test_block_resource_cap_precedes_tensor_materialization(self) -> None:
        actual_raw, ablated_raw = self._raw_pair()
        oversized = SimpleNamespace(shape=(4_097, 4_097, 2))
        actual_raw.source_readout_response.values = oversized
        ablated_raw.source_readout_response.values = oversized
        actual = object.__new__(VerifiedResponseBlock)
        ablated = object.__new__(VerifiedResponseBlock)
        threshold = object.__new__(VerifiedSurvivalThresholdCalibration)
        selection = SimpleNamespace(
            curv_tau_sig=1.0e-12,
            curv_noise_ref=0.0,
        )
        permit = SimpleNamespace(
            selection=selection,
            calibration_manifest=SimpleNamespace(
                calibration_manifest_sha="4" * 64
            ),
        )
        calibration = SimpleNamespace(
            control_evidence=SimpleNamespace(
                instance_audits=(SimpleNamespace(permit=permit),)
            )
        )
        with (
            mock.patch(
                "rulespace_v3.causal._reverify_verified_response_block",
                side_effect=(
                    SimpleNamespace(block=actual_raw),
                    SimpleNamespace(block=ablated_raw),
                ),
            ),
            mock.patch(
                "rulespace_v3.causal."
                "_reverify_verified_survival_threshold_calibration",
                return_value=calibration,
            ),
            mock.patch(
                "rulespace_v3.causal.frozen_tensor_array",
                side_effect=AssertionError("tensor materialized before cap"),
            ) as materialize,
        ):
            with self.assertRaisesRegex(ValueError, "resource cap"):
                compute_causal_survival(actual, ablated, threshold)
        materialize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
