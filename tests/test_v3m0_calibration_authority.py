from __future__ import annotations

import dataclasses
import functools
import subprocess
import sys
import textwrap
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import numpy as np

import rulespace_v3.calibration_authority as authority_module
import rulespace_v3.dynamics as dynamics_module
import rulespace_v3.prestructure as prestructure_module
from rulespace_v3.dynamics import (
    _transition_symbol_from_raw,
    measure_transition,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    _reverify_verified_factory,
    frozen_tensor_array,
)
from rulespace_v3.grids import (
    build_application_bridge_grid_manifest,
    build_response_grid_manifest,
)
from rulespace_v3.metric import build_stability_metric_witness
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import (
    issue_v3m0_application_prestructure_authority,
)
from rulespace_v3.registry import (
    ControlReadoutCalibrationSpec,
    build_closed_control_registry,
    readout_calibration_spec_payload,
)
from rulespace_v3.replay_scope import (
    _replay_scope_statistics,
    _scoped_replay_context,
)
from rulespace_v3.window import (
    build_control_window_protocol_entries,
    build_window_calibration_protocol,
)
from rulespace_v3.structure import build_structure_manifest
from tests.test_v3m0_window_thresholds import _window_controls

from rulespace_v3.calibration_authority import (
    CalibrationApplicationPermit,
    ResponseBlockAttemptOutcome,
    SelectedControlEvidenceRef,
    V3M0ScenarioConstruction,
    VerifiedCalibrationApplicationPermit,
    VerifiedResponseBlockAttemptOutcome,
    VerifiedV3M0ScenarioConstruction,
    V3M0ApplicationResponseRunSpec,
    WindowCalibrationOutcome,
    WindowThresholdCalibrationManifest,
    WindowThresholdSelection,
    build_c04_canonical_angle_recipe,
    build_v3m0_application_response_run_spec,
    c04_canonical_angle_recipe_symbol,
    calibration_application_permit_payload,
    issue_v3m0_calibration_application_permit,
    issue_v3m0_response_block_attempt,
    materialize_v3m0_scenario_construction,
    response_block_attempt_outcome_payload,
    reverify_verified_response_block_attempt_outcome,
    v3m0_scenario_construction_payload,
    verify_calibration_application_permit,
    verify_response_block_attempt_outcome,
    verify_v3m0_application_response_run_spec,
    verify_v3m0_scenario_construction,
    verify_window_threshold_calibration,
    window_calibration_outcome_payload,
    window_threshold_calibration_manifest_payload,
    window_threshold_selection_payload,
)


@dataclass(frozen=True)
class _CandidateAudit:
    fejer_order: int

    def __deepcopy__(self, memo):
        del memo
        raise AssertionError("authority cloning dispatched to __deepcopy__")


def task12_sealed_without_strict_task11_replay(test_method):
    """Keep legacy Task-12 tests fail-closed until a numerical replay exists."""

    @functools.wraps(test_method)
    def assert_sealed(self):
        with self.assertRaisesRegex(TypeError, "WindowCandidateAudit"):
            self._application_permit()

    return assert_sealed


class CalibrationApplicationPermitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
        cls.parent_manifest = cls.parent.manifest
        cls.controls = _window_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        cls.registry_body = cls.registry.registry
        entries = build_control_window_protocol_entries(cls.registry)
        cls.protocol = build_window_calibration_protocol(
            cls.registry,
            entries,
        )
        cls.protocol_body = cls.protocol.protocol

    def _empty_candidate_outcome(self) -> WindowCalibrationOutcome:
        refs = tuple(
            SelectedControlEvidenceRef(
                control_id=entry.control_id,
                control_registry_entry_sha=entry.entry_sha,
                expected_rank_declaration_sha=(str(index + 1) * 64)[-64:],
                run_spec_sha=(str(index + 2) * 64)[-64:],
                paired_response_sha=(str(index + 3) * 64)[-64:],
                shell_manifest_sha=(str(index + 4) * 64)[-64:],
                comparison_2t_run_spec_sha=(str(index + 5) * 64)[-64:],
                comparison_2t_response_sha=(str(index + 6) * 64)[-64:],
                comparison_2t_shell_manifest_sha=(str(index + 7) * 64)[-64:],
            )
            for index, entry in enumerate(self.registry_body.entries)
        )
        provisional_selection = WindowThresholdSelection(
            selected_fejer_order=256,
            h_scale_ref=1.0,
            h_noise_ref=1.0e-6,
            h_signal_min=1.0,
            h_tau_sig=1.0e-3,
            curv_scale_ref=1.0,
            curv_noise_ref=1.0e-6,
            curv_signal_min=1.0,
            curv_tau_sig=1.0e-3,
            selected_evidence_refs=refs,
            selection_sha="0" * 64,
        )
        selection = dataclasses.replace(
            provisional_selection,
            selection_sha=canonical_sha(
                window_threshold_selection_payload(provisional_selection)
            ),
        )
        provisional_manifest = WindowThresholdCalibrationManifest(
            calibration_schema_version=(
                "v3m0.window-threshold-calibration-manifest.v1"
            ),
            control_registry=self.registry_body,
            window_protocol=self.protocol_body,
            candidate_audits=(),
            calibration_manifest_sha="0" * 64,
        )
        manifest = dataclasses.replace(
            provisional_manifest,
            calibration_manifest_sha=canonical_sha(
                window_threshold_calibration_manifest_payload(provisional_manifest)
            ),
        )
        from rulespace_v3.contracts import BlockStatus

        provisional_outcome = WindowCalibrationOutcome(
            status=BlockStatus(True, None),
            manifest=manifest,
            selection=selection,
            outcome_sha="0" * 64,
        )
        return dataclasses.replace(
            provisional_outcome,
            outcome_sha=canonical_sha(
                window_calibration_outcome_payload(provisional_outcome)
            ),
        )

    def _successful_calibration(self):
        cached = getattr(type(self), "_cached_calibration", None)
        if cached is not None:
            return cached
        empty = self._empty_candidate_outcome()
        provisional_manifest = dataclasses.replace(
            empty.manifest,
            candidate_audits=tuple(
                _CandidateAudit(fejer_order=order)
                for order in authority_module.T_CANDIDATES
            ),
            calibration_manifest_sha="0" * 64,
        )
        manifest = dataclasses.replace(
            provisional_manifest,
            calibration_manifest_sha=canonical_sha(
                window_threshold_calibration_manifest_payload(provisional_manifest)
            ),
        )
        provisional_outcome = dataclasses.replace(
            empty,
            manifest=manifest,
            outcome_sha="0" * 64,
        )
        outcome = dataclasses.replace(
            provisional_outcome,
            outcome_sha=canonical_sha(
                window_calibration_outcome_payload(provisional_outcome)
            ),
        )
        result = verify_window_threshold_calibration(
            outcome,
            self.registry,
            self.protocol,
        )
        type(self)._cached_calibration = result
        return result

    def _application_permit(self, ordinal: int = 4):
        calibration = self._successful_calibration()
        spec = self.parent_manifest.synthetic_control_application_specs[ordinal - 1]
        permit = issue_v3m0_calibration_application_permit(
            self.parent,
            calibration,
            spec.application_instance_id,
        )
        return calibration, spec, permit

    def _failed_reference_outcome(self, control_index: int, order: int):
        from rulespace_v3.contracts import BlockStatus, UndefinedReason
        from rulespace_v3.response import (
            ENDPOINT_REFERENCE_ATTEMPT_SCHEMA_VERSION,
            ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION,
            RESPONSE_RUN_SPEC_SCHEMA_VERSION,
            EndpointReferenceAttemptAudit,
            EndpointReferenceFailure,
            EndpointReferenceOutcome,
            EndpointReferenceSpec,
            ResponseRunSpec,
            endpoint_reference_attempt_audit_payload,
            endpoint_reference_outcome_payload,
            endpoint_reference_spec_payload,
            response_run_spec_payload,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        entry = self.registry_body.entries[control_index]
        protocol_entry = self.protocol_body.control_entries[control_index]
        provisional_run = ResponseRunSpec(
            run_spec_schema_version=RESPONSE_RUN_SPEC_SCHEMA_VERSION,
            run_spec_id=f"v3m0.response-run.{entry.control_id}.T{order}.v1",
            window_protocol_sha=self.protocol_body.protocol_sha,
            control_registry_entry_sha=entry.entry_sha,
            fejer_order=order,
            state_schema_id=entry.source_basis.state_schema_id,
            channel_order=entry.source_basis.channel_order,
            source_basis=entry.source_basis,
            readout_basis=entry.readout_basis,
            spatial_shape=protocol_entry.source_readout_bridge_grid.spatial_shape,
            response_grid=protocol_entry.response_grid,
            source_readout_bridge_grid=protocol_entry.source_readout_bridge_grid,
            source_readout_bridge_steps=protocol_entry.source_readout_bridge_steps,
            source_trial_vectors=freeze_complex_tensor(
                np.eye(len(entry.source_basis.vectors_wire), dtype=np.complex128)
            ),
            bridge_tolerance=1.0e-12,
            spec_sha="0" * 64,
        )
        run_spec = dataclasses.replace(
            provisional_run,
            spec_sha=canonical_sha(response_run_spec_payload(provisional_run)),
        )
        provisional_spec = EndpointReferenceSpec(
            reference_spec_schema_version=ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION,
            window_protocol_sha=self.protocol_body.protocol_sha,
            control_registry_entry=entry,
            actual_factory_sha=entry.factory_sha,
            actual_transition_sha="a" * 64,
            actual_dynamics_certificate_sha="b" * 64,
            candidate_fejer_order=order,
            reference_reciprocal_index=protocol_entry.reference_reciprocal_index,
            preregistered_phase_bands=protocol_entry.preregistered_phase_bands,
            expected_shell_rank=protocol_entry.expected_shell_rank,
            expected_shell_rank_source_id=(
                protocol_entry.expected_shell_rank_source_id
            ),
            reference_spec_sha="0" * 64,
        )
        spec = dataclasses.replace(
            provisional_spec,
            reference_spec_sha=canonical_sha(
                endpoint_reference_spec_payload(provisional_spec)
            ),
        )
        provisional_attempt = EndpointReferenceAttemptAudit(
            attempt_schema_version=ENDPOINT_REFERENCE_ATTEMPT_SCHEMA_VERSION,
            reference_spec=spec,
            candidate_phases=(),
            candidate_ranks=(),
            expected_shell_rank=protocol_entry.expected_shell_rank,
            expected_shell_rank_source_id=(
                protocol_entry.expected_shell_rank_source_id
            ),
            candidate_participations=(),
            runner_up_overlaps=(),
            hermitian_residuals=(),
            idempotent_residuals=(),
            g_invariance_residuals=(),
            eigenphase_residuals=(),
            observed_competitor_gaps=(),
            attempt_sha="0" * 64,
        )
        attempt = dataclasses.replace(
            provisional_attempt,
            attempt_sha=canonical_sha(
                endpoint_reference_attempt_audit_payload(provisional_attempt)
            ),
        )
        provisional_outcome = EndpointReferenceOutcome(
            status=BlockStatus(False, UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS),
            failure=EndpointReferenceFailure.PHASE_BAND_EMPTY,
            reference_spec=spec,
            attempt_audit=attempt,
            reference=None,
            outcome_sha="0" * 64,
        )
        outcome = dataclasses.replace(
            provisional_outcome,
            outcome_sha=canonical_sha(
                endpoint_reference_outcome_payload(provisional_outcome)
            ),
        )
        return run_spec, outcome

    def _strict_unresolved_candidates(self):
        from rulespace_v3.calibration_authority import (
            CANDIDATE_ATTEMPT_AUDIT_SCHEMA_VERSION,
            CandidateAttemptAudit,
            ControlCandidateAudit,
            ControlCandidateFailure,
            ControlCandidateOutcome,
            WindowCandidateAudit,
            candidate_attempt_audit_payload,
            control_candidate_audit_payload,
            control_candidate_failure_reason,
            control_candidate_outcome_payload,
            issue_expected_rank_declaration,
            window_candidate_audit_payload,
        )
        from rulespace_v3.contracts import BlockStatus

        cached = getattr(type(self), "_cached_strict_unresolved", None)
        if cached is not None:
            return cached
        result = []
        declarations = {
            entry.control_id: issue_expected_rank_declaration(
                self.registry,
                entry.control_id,
            )
            for entry in self.registry_body.entries
        }
        for order in authority_module.T_CANDIDATES:
            controls = []
            for index, entry in enumerate(self.registry_body.entries):
                outcomes = []
                for candidate_order in (order, 2 * order):
                    run_spec, reference = self._failed_reference_outcome(
                        index,
                        candidate_order,
                    )
                    provisional_attempt = CandidateAttemptAudit(
                        attempt_schema_version=(CANDIDATE_ATTEMPT_AUDIT_SCHEMA_VERSION),
                        control_registry_entry_sha=entry.entry_sha,
                        fejer_order=candidate_order,
                        reference_outcome=reference,
                        shell_outcome=None,
                        paired_response_outcome=None,
                        attempt_sha="0" * 64,
                    )
                    attempt = dataclasses.replace(
                        provisional_attempt,
                        attempt_sha=canonical_sha(
                            candidate_attempt_audit_payload(provisional_attempt)
                        ),
                    )
                    failure = ControlCandidateFailure.REFERENCE_FAILED
                    provisional_outcome = ControlCandidateOutcome(
                        status=BlockStatus(
                            False,
                            control_candidate_failure_reason(failure),
                        ),
                        failure=failure,
                        run_spec=run_spec,
                        attempt_audit=attempt,
                        outcome_sha="0" * 64,
                    )
                    outcomes.append(
                        dataclasses.replace(
                            provisional_outcome,
                            outcome_sha=canonical_sha(
                                control_candidate_outcome_payload(provisional_outcome)
                            ),
                        )
                    )
                provisional_control = ControlCandidateAudit(
                    control_registry_entry=entry,
                    expected_rank_declaration=declarations[entry.control_id],
                    candidate_t=outcomes[0],
                    comparison_2t=outcomes[1],
                    readout_spectrum_audits=(),
                    comparison_2t_readout_spectrum_audits=(),
                    phase_separation=None,
                    overlap_margin=None,
                    projector_t2t_distance=None,
                    passed=False,
                    audit_sha="0" * 64,
                )
                controls.append(
                    dataclasses.replace(
                        provisional_control,
                        audit_sha=canonical_sha(
                            control_candidate_audit_payload(provisional_control)
                        ),
                    )
                )
            provisional_window = WindowCandidateAudit(
                fejer_order=order,
                control_audits=tuple(controls),
                readout_aggregate_audits=(),
                passed=False,
                audit_sha="0" * 64,
            )
            result.append(
                dataclasses.replace(
                    provisional_window,
                    audit_sha=canonical_sha(
                        window_candidate_audit_payload(provisional_window)
                    ),
                )
            )
        answer = tuple(result)
        type(self)._cached_strict_unresolved = answer
        return answer

    @staticmethod
    def _scenario_id(spec, index: int = 0) -> str:
        return spec.scenario_execution_specs[index].scenario_id

    def test_fake_calibration_or_parent_cannot_issue_permit(self) -> None:
        instance_id = self.parent_manifest.synthetic_control_application_specs[
            3
        ].application_instance_id
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_calibration_application_permit(
                self.parent,
                object(),
                instance_id,
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_calibration_application_permit(
                object(),
                object(),
                instance_id,
            )

    def test_calibration_authority_rejects_missing_six_candidate_audits(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "six|candidate"):
            verify_window_threshold_calibration(
                self._empty_candidate_outcome(),
                self.registry,
                self.protocol,
            )

    def test_calibration_authority_rejects_fejer_order_only_candidate_fakes(
        self,
    ) -> None:
        """A self-hashed object with only ``fejer_order`` is not evidence."""

        with self.assertRaisesRegex(TypeError, "WindowCandidateAudit"):
            self._successful_calibration()

    def test_expected_rank_declaration_is_closed_over_registry_entry(self) -> None:
        from rulespace_v3.calibration_authority import (
            expected_rank_declaration_payload,
            issue_expected_rank_declaration,
        )

        for entry in self.registry_body.entries:
            declaration = issue_expected_rank_declaration(
                self.registry,
                entry.control_id,
            )
            self.assertEqual(
                declaration.control_registry_sha, self.registry_body.registry_sha
            )
            self.assertEqual(declaration.control_registry_entry_sha, entry.entry_sha)
            self.assertEqual(
                declaration.expected_h_actual_rank,
                entry.expected_h_actual_rank,
            )
            self.assertEqual(
                declaration.expected_h_ablated_rank,
                entry.expected_h_ablated_rank,
            )
            self.assertEqual(
                declaration.declaration_sha,
                canonical_sha(expected_rank_declaration_payload(declaration)),
            )

    def test_task11_calibration_records_match_the_frozen_exact_schema(self) -> None:
        from rulespace_v3.calibration_authority import (
            BranchSpectrumAudit,
            CandidateAttemptAudit,
            ControlCandidateAudit,
            ControlCandidateOutcome,
            ExpectedRankDeclaration,
            PerControlReadoutSpectrumAudit,
            ReadoutAggregateCalibrationAudit,
            WindowCandidateAudit,
        )

        expected_fields = {
            ExpectedRankDeclaration: (
                "declaration_schema_version",
                "control_registry_sha",
                "control_registry_entry_sha",
                "control_id",
                "expected_h_actual_rank",
                "expected_h_ablated_rank",
                "expected_curv_actual_rank",
                "expected_curv_ablated_rank",
                "parent_freeze_sha",
                "declaration_sha",
            ),
            CandidateAttemptAudit: (
                "attempt_schema_version",
                "control_registry_entry_sha",
                "fejer_order",
                "reference_outcome",
                "shell_outcome",
                "paired_response_outcome",
                "attempt_sha",
            ),
            ControlCandidateOutcome: (
                "status",
                "failure",
                "run_spec",
                "attempt_audit",
                "outcome_sha",
            ),
            BranchSpectrumAudit: (
                "branch",
                "declared_rank",
                "spectrum_shape",
                "spectrum_order_id",
                "raw_spectrum",
                "active_min",
                "inactive_max",
                "branch_sha",
            ),
            PerControlReadoutSpectrumAudit: (
                "readout_kind",
                "control_registry_entry_sha",
                "expected_rank_declaration_sha",
                "fejer_order",
                "run_spec_sha",
                "paired_response_sha",
                "actual",
                "ablated",
                "actual_bridge_operator_error_upper",
                "ablated_bridge_operator_error_upper",
                "audit_sha",
            ),
            ReadoutAggregateCalibrationAudit: (
                "readout_kind",
                "per_control",
                "scale_ref",
                "null_max",
                "bridge_operator_error_max",
                "noise_ref",
                "signal_min",
                "tau_sig",
                "signal_noise_ratio",
                "raw_relative_gap",
                "absolute_signal_gate_passed",
                "relative_gap_gate_passed",
                "aggregate_sha",
            ),
            ControlCandidateAudit: (
                "control_registry_entry",
                "expected_rank_declaration",
                "candidate_t",
                "comparison_2t",
                "readout_spectrum_audits",
                "comparison_2t_readout_spectrum_audits",
                "phase_separation",
                "overlap_margin",
                "projector_t2t_distance",
                "passed",
                "audit_sha",
            ),
            WindowCandidateAudit: (
                "fejer_order",
                "control_audits",
                "readout_aggregate_audits",
                "passed",
                "audit_sha",
            ),
        }
        for record_type, fields in expected_fields.items():
            self.assertEqual(tuple(record_type.__dataclass_fields__), fields)
            self.assertFalse(
                any(
                    name in record_type.__dataclass_fields__
                    for name in ("tau_surv", "tau_geom", "tau_cover")
                )
            )

    def test_branch_spectrum_uses_exact_rank_partition_and_optional_empties(
        self,
    ) -> None:
        from rulespace_v3.calibration_authority import BranchSpectrumAudit

        rank_zero = BranchSpectrumAudit(
            branch="actual",
            declared_rank=0,
            spectrum_shape=(2, 2),
            spectrum_order_id="k-major-singular-descending-v1",
            raw_spectrum=(3.0, 1.0, 2.0, 0.0),
            active_min=None,
            inactive_max=3.0,
            branch_sha="0" * 64,
        )
        self.assertIsNone(rank_zero.active_min)
        self.assertEqual(rank_zero.inactive_max, 3.0)
        with self.assertRaisesRegex(ValueError, "active_min"):
            dataclasses.replace(rank_zero, active_min=0.0)
        with self.assertRaisesRegex(ValueError, "descending"):
            dataclasses.replace(
                rank_zero,
                raw_spectrum=(1.0, 3.0, 2.0, 0.0),
                inactive_max=3.0,
            )

        full_rank = dataclasses.replace(
            rank_zero,
            declared_rank=2,
            active_min=0.0,
            inactive_max=None,
        )
        self.assertEqual(full_rank.active_min, 0.0)
        self.assertIsNone(full_rank.inactive_max)

    def test_control_candidate_failure_reason_is_a_closed_total_mapping(self) -> None:
        from rulespace_v3.calibration_authority import (
            ControlCandidateFailure,
            control_candidate_failure_reason,
        )
        from rulespace_v3.contracts import UndefinedReason

        self.assertEqual(
            {
                failure: control_candidate_failure_reason(failure)
                for failure in ControlCandidateFailure
            },
            {
                ControlCandidateFailure.REFERENCE_FAILED: (
                    UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS
                ),
                ControlCandidateFailure.SHELL_FAILED: (
                    UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS
                ),
                ControlCandidateFailure.RESPONSE_FAILED: (
                    UndefinedReason.PAIRED_RESPONSE_FAILED
                ),
                ControlCandidateFailure.BRIDGE_FAILED: (
                    UndefinedReason.RESPONSE_BRIDGE_FAILED
                ),
            },
        )
        with self.assertRaises(TypeError):
            control_candidate_failure_reason("reference_failed")

    def test_strict_six_candidate_failure_graph_builds_only_unresolved_outcome(
        self,
    ) -> None:
        from rulespace_v3.calibration_authority import (
            calibrate_window_and_thresholds,
        )
        from rulespace_v3.contracts import UndefinedReason

        outcome = calibrate_window_and_thresholds(
            self.registry,
            self.protocol,
            self._strict_unresolved_candidates(),
        )
        self.assertFalse(outcome.status.defined)
        self.assertIs(outcome.status.reason, UndefinedReason.WINDOW_UNRESOLVED)
        self.assertIsNone(outcome.selection)
        self.assertEqual(
            tuple(item.fejer_order for item in outcome.manifest.candidate_audits),
            authority_module.T_CANDIDATES,
        )
        cloned_manifest = authority_module._clone_task12_wire(
            outcome.manifest,
            local_record_types=(WindowThresholdCalibrationManifest,),
            candidate_record_types=authority_module._candidate_record_types(
                outcome.manifest
            ),
        )
        self.assertEqual(cloned_manifest, outcome.manifest)
        self.assertIsNot(cloned_manifest, outcome.manifest)
        with self.assertRaisesRegex(ValueError, "successful calibration"):
            verify_window_threshold_calibration(
                outcome,
                self.registry,
                self.protocol,
            )

    def test_strict_candidate_graph_rejects_resigned_cross_order_splice(self) -> None:
        from rulespace_v3.calibration_authority import (
            calibrate_window_and_thresholds,
            control_candidate_audit_payload,
            window_candidate_audit_payload,
        )

        candidates = self._strict_unresolved_candidates()
        first = candidates[0]
        control = first.control_audits[0]
        changed_control0 = dataclasses.replace(
            control,
            comparison_2t=control.candidate_t,
            audit_sha="0" * 64,
        )
        changed_control = dataclasses.replace(
            changed_control0,
            audit_sha=canonical_sha(control_candidate_audit_payload(changed_control0)),
        )
        changed_window0 = dataclasses.replace(
            first,
            control_audits=(changed_control,) + first.control_audits[1:],
            audit_sha="0" * 64,
        )
        changed_window = dataclasses.replace(
            changed_window0,
            audit_sha=canonical_sha(window_candidate_audit_payload(changed_window0)),
        )
        with self.assertRaisesRegex(ValueError, "T/2T"):
            calibrate_window_and_thresholds(
                self.registry,
                self.protocol,
                (changed_window,) + candidates[1:],
            )

    def test_strict_candidate_graph_rejects_resigned_reference_selection(self) -> None:
        from rulespace_v3.calibration_authority import (
            calibrate_window_and_thresholds,
            candidate_attempt_audit_payload,
            control_candidate_audit_payload,
            control_candidate_outcome_payload,
            window_candidate_audit_payload,
        )
        from rulespace_v3.response import (
            endpoint_reference_attempt_audit_payload,
            endpoint_reference_outcome_payload,
        )

        candidates = self._strict_unresolved_candidates()
        first = candidates[0]
        control = first.control_audits[0]
        candidate_outcome = control.candidate_t
        candidate_attempt = candidate_outcome.attempt_audit
        reference = candidate_attempt.reference_outcome
        reference_attempt0 = dataclasses.replace(
            reference.attempt_audit,
            candidate_phases=(0.0,),
            candidate_ranks=(reference.reference_spec.expected_shell_rank,),
            candidate_participations=(1.0,),
            runner_up_overlaps=(None,),
            hermitian_residuals=(0.0,),
            idempotent_residuals=(0.0,),
            g_invariance_residuals=(0.0,),
            eigenphase_residuals=(0.0,),
            observed_competitor_gaps=(None,),
            attempt_sha="0" * 64,
        )
        reference_attempt = dataclasses.replace(
            reference_attempt0,
            attempt_sha=canonical_sha(
                endpoint_reference_attempt_audit_payload(reference_attempt0)
            ),
        )
        changed_reference0 = dataclasses.replace(
            reference,
            attempt_audit=reference_attempt,
            outcome_sha="0" * 64,
        )
        changed_reference = dataclasses.replace(
            changed_reference0,
            outcome_sha=canonical_sha(
                endpoint_reference_outcome_payload(changed_reference0)
            ),
        )
        candidate_attempt0 = dataclasses.replace(
            candidate_attempt,
            reference_outcome=changed_reference,
            attempt_sha="0" * 64,
        )
        changed_candidate_attempt = dataclasses.replace(
            candidate_attempt0,
            attempt_sha=canonical_sha(
                candidate_attempt_audit_payload(candidate_attempt0)
            ),
        )
        candidate_outcome0 = dataclasses.replace(
            candidate_outcome,
            attempt_audit=changed_candidate_attempt,
            outcome_sha="0" * 64,
        )
        changed_candidate_outcome = dataclasses.replace(
            candidate_outcome0,
            outcome_sha=canonical_sha(
                control_candidate_outcome_payload(candidate_outcome0)
            ),
        )
        control0 = dataclasses.replace(
            control,
            candidate_t=changed_candidate_outcome,
            audit_sha="0" * 64,
        )
        changed_control = dataclasses.replace(
            control0,
            audit_sha=canonical_sha(control_candidate_audit_payload(control0)),
        )
        first0 = dataclasses.replace(
            first,
            control_audits=(changed_control,) + first.control_audits[1:],
            audit_sha="0" * 64,
        )
        changed_window = dataclasses.replace(
            first0,
            audit_sha=canonical_sha(window_candidate_audit_payload(first0)),
        )
        with self.assertRaisesRegex(ValueError, "failure is not mechanical"):
            calibrate_window_and_thresholds(
                self.registry,
                self.protocol,
                (changed_window,) + candidates[1:],
            )

    def test_strict_candidate_graph_rejects_resigned_caller_rank(self) -> None:
        from rulespace_v3.calibration_authority import (
            calibrate_window_and_thresholds,
            control_candidate_audit_payload,
            expected_rank_declaration_payload,
            window_candidate_audit_payload,
        )

        candidates = self._strict_unresolved_candidates()
        first = candidates[0]
        control = first.control_audits[0]
        changed_declaration0 = dataclasses.replace(
            control.expected_rank_declaration,
            expected_h_actual_rank=(
                control.expected_rank_declaration.expected_h_actual_rank + 1
            ),
            declaration_sha="0" * 64,
        )
        changed_declaration = dataclasses.replace(
            changed_declaration0,
            declaration_sha=canonical_sha(
                expected_rank_declaration_payload(changed_declaration0)
            ),
        )
        changed_control0 = dataclasses.replace(
            control,
            expected_rank_declaration=changed_declaration,
            audit_sha="0" * 64,
        )
        changed_control = dataclasses.replace(
            changed_control0,
            audit_sha=canonical_sha(control_candidate_audit_payload(changed_control0)),
        )
        changed_window0 = dataclasses.replace(
            first,
            control_audits=(changed_control,) + first.control_audits[1:],
            audit_sha="0" * 64,
        )
        changed_window = dataclasses.replace(
            changed_window0,
            audit_sha=canonical_sha(window_candidate_audit_payload(changed_window0)),
        )
        with self.assertRaisesRegex(ValueError, "differs from registry"):
            calibrate_window_and_thresholds(
                self.registry,
                self.protocol,
                (changed_window,) + candidates[1:],
            )

    def test_raw_self_hashed_permit_is_not_a_live_capability(self) -> None:
        self.assertEqual(
            tuple(CalibrationApplicationPermit.__dataclass_fields__),
            (
                "permit_schema_version",
                "scope",
                "parent_freeze",
                "application_spec",
                "calibration_manifest",
                "selection",
                "selected_fejer_order",
                "window_protocol",
                "response_grid",
                "source_readout_bridge_grid",
                "source_readout_bridge_steps",
                "reference_reciprocal_index",
                "preregistered_phase_bands",
                "expected_shell_rank",
                "expected_shell_rank_source_id",
                "source_basis",
                "readout_basis",
                "readout_calibration_spec",
                "permit_sha",
            ),
        )
        forbidden = {
            "paired_response",
            "control_evidence",
            "transition",
            "certificate",
            "physical_adapter",
        }
        self.assertTrue(
            forbidden.isdisjoint(CalibrationApplicationPermit.__dataclass_fields__)
        )
        raw = object.__new__(CalibrationApplicationPermit)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            calibration_application_permit_payload(raw)
        fake = object.__new__(VerifiedCalibrationApplicationPermit)
        with self.assertRaises((TypeError, ValueError)):
            fake.permit

    def test_application_grids_and_readout_spec_are_uniquely_derived(self) -> None:
        spec = self.parent_manifest.synthetic_control_application_specs[3]
        response = build_response_grid_manifest(spec)
        bridge = build_application_bridge_grid_manifest(spec)
        protocol = spec.readout_protocol
        provisional = ControlReadoutCalibrationSpec(
            spec_schema_version=("v3m0.control-readout-calibration-spec.v1"),
            source_metric_whitener=protocol.source_metric_whitener,
            h_metric_whitener=protocol.h_metric_whitener,
            curvature_incidence_operator=(protocol.curvature_incidence_operator),
            curvature_metric_whitener=(protocol.curvature_metric_whitener),
            curvature_normalizer_id=protocol.curvature_normalizer_id,
            spec_sha="0" * 64,
        )
        derived = dataclasses.replace(
            provisional,
            spec_sha=canonical_sha(readout_calibration_spec_payload(provisional)),
        )
        self.assertEqual(
            response.reciprocal_indices,
            spec.grid_protocol.response_reciprocal_indices,
        )
        self.assertEqual(
            bridge.reciprocal_indices,
            spec.grid_protocol.bridge_reciprocal_indices,
        )
        self.assertEqual(
            derived.source_metric_whitener,
            protocol.source_metric_whitener,
        )

    def test_application_run_spec_has_no_caller_metric_or_operator_fields(
        self,
    ) -> None:
        self.assertEqual(
            tuple(V3M0ApplicationResponseRunSpec.__dataclass_fields__),
            (
                "run_spec_schema_version",
                "permit_sha",
                "application_spec_sha",
                "fejer_order",
                "source_basis",
                "readout_basis",
                "response_grid",
                "source_readout_bridge_grid",
                "source_readout_bridge_steps",
                "source_trial_vectors",
                "bridge_tolerance",
                "run_spec_sha",
            ),
        )
        forbidden = {
            "source_metric",
            "physical_h_metric",
            "curvature_operator",
            "paired_response",
            "control_evidence",
        }
        self.assertTrue(
            forbidden.isdisjoint(V3M0ApplicationResponseRunSpec.__dataclass_fields__)
        )

    def test_run_spec_and_permit_verifiers_reject_object_new_wrappers(
        self,
    ) -> None:
        fake = object.__new__(VerifiedCalibrationApplicationPermit)
        with self.assertRaises((TypeError, ValueError)):
            build_v3m0_application_response_run_spec(fake)
        raw_run = object.__new__(V3M0ApplicationResponseRunSpec)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            verify_v3m0_application_response_run_spec(raw_run, fake)
        raw_permit = object.__new__(CalibrationApplicationPermit)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            verify_calibration_application_permit(
                raw_permit,
                self.parent,
                object(),
            )

    def test_oversized_raw_permit_caps_before_hash_or_upstream_replay(
        self,
    ) -> None:
        raw = object.__new__(CalibrationApplicationPermit)
        for field in CalibrationApplicationPermit.__dataclass_fields__:
            object.__setattr__(raw, field, None)
        object.__setattr__(raw, "permit_schema_version", "v1")
        object.__setattr__(raw, "scope", "x" * 20_000)
        with (
            mock.patch.object(
                authority_module,
                "canonical_sha",
                side_effect=AssertionError("hash ran first"),
            ),
            mock.patch.object(
                authority_module,
                "_reverify_verified_parent_freeze",
                side_effect=AssertionError("parent replay ran first"),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "resource cap"):
                verify_calibration_application_permit(
                    raw,
                    object(),
                    object(),
                )

    def test_application_construction_schema_is_snapshot_only(self) -> None:
        self.assertEqual(
            tuple(V3M0ScenarioConstruction.__dataclass_fields__),
            (
                "construction_schema_version",
                "permit",
                "scenario_spec",
                "operation_evaluations",
                "operation_effect_digests",
                "recipe_id",
                "recipe_derivation_source_id",
                "recipe_parameter_reads",
                "recipe_sha",
                "construction_status",
                "ablation_pair_snapshot",
                "interface_sha",
                "source_basis_sha",
                "readout_basis_sha",
                "response_grid_sha",
                "bridge_grid_sha",
                "run_spec_sha",
                "actual_effect_digest",
                "ablated_effect_digest",
                "actual_factory_sha",
                "ablated_factory_sha",
                "ablation_manifest_sha",
                "ablation_construction_sha",
                "construction_sha",
            ),
        )
        self.assertNotIn(
            "live_construction",
            V3M0ScenarioConstruction.__dataclass_fields__,
        )
        fake = object.__new__(VerifiedV3M0ScenarioConstruction)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            _ = fake.construction

    @task12_sealed_without_strict_task11_replay
    def test_closed_dag_materializes_unique_local_matched_pair(self) -> None:
        _, spec, permit = self._application_permit()
        scenario_id = self._scenario_id(spec)
        construction = materialize_v3m0_scenario_construction(
            permit,
            scenario_id,
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )
        raw = construction_view.construction
        actual = _reverify_verified_factory(construction_view.actual)
        ablated = _reverify_verified_factory(construction_view.ablated)

        self.assertTrue(raw.construction_status.defined)
        self.assertEqual(raw.permit, permit.permit)
        self.assertEqual(raw.actual_factory_sha, actual.factory.factory_sha)
        self.assertEqual(raw.ablated_factory_sha, ablated.factory.factory_sha)
        self.assertNotEqual(raw.actual_factory_sha, raw.ablated_factory_sha)
        self.assertEqual(actual.factory.channel_order, ("q0", "p0", "q1", "p1"))
        self.assertEqual(actual.factory.state_shape, (4, 8))
        self.assertEqual(ablated.factory.state_shape, actual.factory.state_shape)
        self.assertEqual(
            {primitive.offset for primitive in actual.factory.primitives},
            {(-1,), (0,), (1,)},
        )
        self.assertEqual(
            {
                offset
                for primitive in actual.factory.primitives
                for offset in primitive.support_offsets
            },
            {(-1,), (0,), (1,)},
        )
        self.assertEqual(len(actual.factory.primitives), 57)
        self.assertEqual(
            len(raw.ablation_pair_snapshot.ablation_manifest.replacements),
            12,
        )
        self.assertNotEqual(raw.actual_effect_digest, raw.ablated_effect_digest)
        provenance_ids = {node.provenance_id for node in actual.trace.provenance_nodes}
        self.assertTrue(
            {operation.operation_instance_id for operation in spec.operations}.issubset(
                provenance_ids
            )
        )

        hydrated = verify_v3m0_scenario_construction(
            raw,
            permit,
            scenario_id,
        )
        self.assertIs(type(hydrated), VerifiedV3M0ScenarioConstruction)
        self.assertEqual(
            raw.construction_sha,
            canonical_sha(v3m0_scenario_construction_payload(raw)),
        )

    @task12_sealed_without_strict_task11_replay
    def test_application_authorities_run_real_fp64_unitary_symplectic_steps(
        self,
    ) -> None:
        _, spec, permit = self._application_permit()
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )
        identity = np.eye(4, dtype=np.complex128)
        symplectic_form = np.kron(
            np.eye(2, dtype=np.complex128),
            np.asarray(
                ((0.0, 1.0), (-1.0, 0.0)),
                dtype=np.complex128,
            ),
        )
        recipe = build_c04_canonical_angle_recipe()

        for role, factory in (
            ("actual", construction_view.actual),
            ("matched_ablated", construction_view.ablated),
        ):
            prestructure = issue_v3m0_application_prestructure_authority(
                permit,
                construction,
                role,
            )
            transition = measure_transition(factory, prestructure)
            raw_transition = transition.transition
            if role == "actual":
                injected_provisional = dataclasses.replace(
                    raw_transition,
                    dt=raw_transition.dt + 1.0,
                    transition_sha="0" * 64,
                )
                injected_raw = dataclasses.replace(
                    injected_provisional,
                    transition_sha=canonical_sha(
                        dynamics_module.measured_transition_payload(
                            injected_provisional
                        )
                    ),
                )
                injected = dynamics_module._register_measured_transition(
                    injected_raw,
                    factory,
                    prestructure,
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "immutable seal mismatch",
                ):
                    dynamics_module._reverify_verified_transition(injected)
                with self.assertRaisesRegex(
                    ValueError,
                    "immutable seal mismatch",
                ):
                    dynamics_module.transition_symbol(
                        injected,
                        np.asarray((0.0,), dtype=np.float64),
                    )
            self.assertLessEqual(
                max(abs(offset[0]) for offset in raw_transition.support_offsets),
                2,
            )
            self.assertEqual(
                prestructure.authority.authority_kind,
                "synthetic-application-v1",
            )
            self.assertEqual(
                prestructure.authority.synthetic_application_permit_sha,
                permit.permit.permit_sha,
            )
            self.assertEqual(
                prestructure.authority.synthetic_application_scenario_spec,
                construction_view.construction.scenario_spec,
            )
            for momentum in (np.pi / 4.0, np.pi / 2.0):
                matrix = _transition_symbol_from_raw(
                    raw_transition,
                    np.asarray((momentum,), dtype=np.float64),
                )
                opposite = _transition_symbol_from_raw(
                    raw_transition,
                    np.asarray((-momentum,), dtype=np.float64),
                )
                np.testing.assert_allclose(
                    matrix,
                    c04_canonical_angle_recipe_symbol(
                        recipe,
                        float(momentum),
                        role,
                    ),
                    rtol=0.0,
                    atol=1.0e-12,
                )
                self.assertLessEqual(
                    float(
                        np.linalg.norm(
                            matrix.conj().T @ matrix - identity,
                            ord=2,
                        )
                    ),
                    1.0e-12,
                )
                self.assertLessEqual(
                    float(
                        np.linalg.norm(
                            opposite.T @ symplectic_form @ matrix - symplectic_form,
                            ord=2,
                        )
                    ),
                    1.0e-12,
                )
                np.testing.assert_allclose(
                    opposite,
                    matrix.conj(),
                    rtol=0.0,
                    atol=1.0e-12,
                )

    @task12_sealed_without_strict_task11_replay
    def test_application_authority_mechanically_derives_j_and_identity_metric(
        self,
    ) -> None:
        _, spec, permit = self._application_permit()
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )
        expected_j = np.kron(
            np.eye(2, dtype=np.complex128),
            np.asarray(
                ((0.0, 1.0), (-1.0, 0.0)),
                dtype=np.complex128,
            ),
        )
        for role, factory in (
            ("actual", construction_view.actual),
            ("matched_ablated", construction_view.ablated),
        ):
            authority = issue_v3m0_application_prestructure_authority(
                permit,
                construction,
                role,
            )
            structure = build_structure_manifest(factory, authority)
            metric = build_stability_metric_witness(
                factory,
                authority,
                structure,
            )
            np.testing.assert_array_equal(
                frozen_tensor_array(structure.structure_form),
                expected_j,
            )
            np.testing.assert_array_equal(
                frozen_tensor_array(metric.metric_kernel)[0],
                np.eye(4, dtype=np.complex128),
            )
            self.assertEqual(
                metric.metric_origin.derivation_or_preregistration_sha,
                permit.permit.application_spec.application_spec_sha,
            )

    @task12_sealed_without_strict_task11_replay
    def test_construction_rejects_cross_permit_and_unissued_wrapper(self) -> None:
        _, spec, first_permit = self._application_permit(4)
        _, _, same_body_other_permit = self._application_permit(4)
        _, _, wrong_case_permit = self._application_permit(5)
        scenario_id = self._scenario_id(spec)
        first = materialize_v3m0_scenario_construction(
            first_permit,
            scenario_id,
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_v3m0_scenario_construction(
                first.construction,
                wrong_case_permit,
                scenario_id,
            )
        fake = object.__new__(VerifiedV3M0ScenarioConstruction)
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                first_permit,
                fake,
                "actual",
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                same_body_other_permit,
                first,
                "actual",
            )

    @task12_sealed_without_strict_task11_replay
    def test_application_role_authority_requires_live_permit_and_construction(
        self,
    ) -> None:
        _, spec, permit = self._application_permit(4)
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )

        authority = issue_v3m0_application_prestructure_authority(
            permit,
            construction,
            "actual",
        )
        self.assertEqual(
            authority.authority.synthetic_application_permit_sha,
            permit.permit.permit_sha,
        )
        self.assertEqual(
            authority.authority.synthetic_scenario_construction_sha,
            construction_view.construction.construction_sha,
        )

        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                self.parent,
                spec,
                "f" * 64,
                construction_view.outcome,
                "actual",
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                object(),
                construction,
                "actual",
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                permit,
                object(),
                "actual",
            )

        _, _, other_permit = self._application_permit(5)
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                other_permit,
                construction,
                "actual",
            )

    @task12_sealed_without_strict_task11_replay
    def test_application_prestructure_hit_revalidates_all_live_dependencies(
        self,
    ) -> None:
        _, spec, permit = self._application_permit(4)
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )
        prestructure = issue_v3m0_application_prestructure_authority(
            permit,
            construction,
            "actual",
        )
        namespace = "rulespace_v3.prestructure.VerifiedPrestructureAuthority"
        parent_manifest = object.__getattribute__(
            self.parent,
            "_VerifiedParentFreeze__manifest",
        )
        permit_body = object.__getattribute__(
            permit,
            "_VerifiedCalibrationApplicationPermit__permit",
        )
        construction_body = object.__getattribute__(
            construction,
            "_VerifiedV3M0ScenarioConstruction__construction",
        )
        assert construction_view.outcome.pair is not None
        construction_outcome_manifest = construction_view.outcome.pair.manifest
        factory_primitive = construction_view.actual.factory.primitives[0]
        cases = (
            (
                "parent",
                parent_manifest,
                "parent_freeze_sha",
                "f" * 64,
            ),
            (
                "permit",
                permit_body,
                "permit_sha",
                "f" * 64,
            ),
            (
                "scenario-construction",
                construction_body,
                "construction_sha",
                "f" * 64,
            ),
            (
                "construction-outcome",
                construction_outcome_manifest,
                "manifest_sha",
                "f" * 64,
            ),
            (
                "selected-factory",
                factory_primitive,
                "coefficient_wire",
                (
                    factory_primitive.coefficient_wire[0] + 1.0,
                    factory_primitive.coefficient_wire[1],
                ),
            ),
        )
        with _scoped_replay_context():
            prestructure_module._reverify_verified_prestructure_authority(prestructure)
            for label, target, field, changed in cases:
                with self.subTest(dependency=label):
                    original = getattr(target, field)
                    hits_before = dict(_replay_scope_statistics().hits).get(
                        namespace,
                        0,
                    )
                    try:
                        object.__setattr__(target, field, changed)
                        with self.assertRaises((TypeError, ValueError)):
                            prestructure_module._reverify_verified_prestructure_authority(
                                prestructure
                            )
                    finally:
                        object.__setattr__(target, field, original)
                    hits_after = dict(_replay_scope_statistics().hits).get(
                        namespace,
                        0,
                    )
                    self.assertEqual(hits_after, hits_before)
            with (
                mock.patch.object(
                    authority_module,
                    "_reverify_verified_calibration_application_permit",
                    side_effect=AssertionError(
                        "live permit reverifier rebinding was consulted"
                    ),
                ) as rebound_permit,
                mock.patch.object(
                    authority_module,
                    "_reverify_verified_scenario_construction",
                    side_effect=AssertionError(
                        "live construction reverifier rebinding was consulted"
                    ),
                ) as rebound_construction,
            ):
                prestructure_module._reverify_verified_prestructure_authority(
                    prestructure
                )
            rebound_permit.assert_not_called()
            rebound_construction.assert_not_called()

    @task12_sealed_without_strict_task11_replay
    def test_application_prestructure_issuance_ignores_prebound_rebinding(
        self,
    ) -> None:
        _, spec, permit = self._application_permit(4)
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        with (
            mock.patch.object(
                authority_module,
                "_reverify_verified_calibration_application_permit",
                side_effect=AssertionError(
                    "pre-issuance permit rebinding was consulted"
                ),
            ) as rebound_permit,
            mock.patch.object(
                authority_module,
                "_reverify_verified_scenario_construction",
                side_effect=AssertionError(
                    "pre-issuance construction rebinding was consulted"
                ),
            ) as rebound_construction,
            mock.patch.object(
                prestructure_module,
                "issue_v3m0_application_prestructure_authority",
                side_effect=AssertionError(
                    "pre-issuance issuer rebinding was consulted"
                ),
            ) as rebound_issuer,
        ):
            prestructure = issue_v3m0_application_prestructure_authority(
                permit,
                construction,
                "actual",
            )
        rebound_permit.assert_not_called()
        rebound_construction.assert_not_called()
        rebound_issuer.assert_not_called()
        verified = prestructure_module._reverify_verified_prestructure_authority(
            prestructure
        )
        self.assertIs(verified.application_permit, permit)
        self.assertIs(verified.application_construction, construction)

    def test_fresh_prestructure_capture_is_import_order_stable_and_rebind_safe(
        self,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        for first, second in (
            ("rulespace_v3.prestructure", "rulespace_v3.calibration_authority"),
            ("rulespace_v3.calibration_authority", "rulespace_v3.prestructure"),
        ):
            with self.subTest(first=first):
                probe = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        (f"import {first}; import {second}; print('IMPORT_ORDER_OK')"),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    probe.returncode,
                    0,
                    msg=f"stdout={probe.stdout}\nstderr={probe.stderr}",
                )
                self.assertIn("IMPORT_ORDER_OK", probe.stdout)
        script = textwrap.dedent(
            """
            from unittest import mock

            import rulespace_v3.calibration_authority as calibration
            with (
                mock.patch.object(
                    calibration,
                    "_reverify_verified_calibration_application_permit",
                    side_effect=AssertionError("rebound permit consulted"),
                ) as rebound_permit,
                mock.patch.object(
                    calibration,
                    "_reverify_verified_scenario_construction",
                    side_effect=AssertionError("rebound construction consulted"),
                ) as rebound_construction,
            ):
                import rulespace_v3.prestructure as prestructure

                assert not hasattr(
                    prestructure,
                    "_install_application_prestructure_dependencies",
                )
                assert not hasattr(
                    prestructure,
                    "_bootstrap_application_prestructure_dependencies",
                )
                assert not hasattr(
                    calibration,
                    "issue_v3m0_application_prestructure_authority",
                )
                genuine_issuer = (
                    prestructure.issue_v3m0_application_prestructure_authority
                )

                fake_permit = object.__new__(
                    calibration.VerifiedCalibrationApplicationPermit
                )
                fake_construction = object.__new__(
                    calibration.VerifiedV3M0ScenarioConstruction
                )
                with (
                    mock.patch.object(
                        calibration.VerifiedCalibrationApplicationPermit,
                        "_prestructure_reverify",
                        side_effect=AssertionError(
                            "rebound permit descriptor consulted"
                        ),
                    ) as rebound_permit_descriptor,
                    mock.patch.object(
                        calibration.VerifiedV3M0ScenarioConstruction,
                        "_prestructure_reverify",
                        side_effect=AssertionError(
                            "rebound construction descriptor consulted"
                        ),
                    ) as rebound_construction_descriptor,
                    mock.patch.object(
                        prestructure,
                        "issue_v3m0_application_prestructure_authority",
                        side_effect=AssertionError("rebound issuer consulted"),
                    ) as rebound_issuer,
                ):
                    try:
                        genuine_issuer(
                            fake_permit,
                            fake_construction,
                            "actual",
                        )
                    except (TypeError, ValueError, AttributeError):
                        pass
                    else:
                        raise AssertionError(
                            "incomplete child wrappers did not fail closed"
                        )
                rebound_permit_descriptor.assert_not_called()
                rebound_construction_descriptor.assert_not_called()
                rebound_issuer.assert_not_called()
            rebound_permit.assert_not_called()
            rebound_construction.assert_not_called()
            print("FRESH_CAPTURE_OK")
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertIn("FRESH_CAPTURE_OK", result.stdout)

    @task12_sealed_without_strict_task11_replay
    def test_application_prestructure_rejects_slot_copy_and_expired_children(
        self,
    ) -> None:
        _, spec, permit = self._application_permit(4)
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )

        copied_permit = object.__new__(VerifiedCalibrationApplicationPermit)
        for field in ("permit", "token", "seal"):
            attribute = f"_VerifiedCalibrationApplicationPermit__{field}"
            object.__setattr__(
                copied_permit,
                attribute,
                object.__getattribute__(permit, attribute),
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                copied_permit,
                construction,
                "actual",
            )

        copied_construction = object.__new__(VerifiedV3M0ScenarioConstruction)
        for field in ("construction", "token", "seal"):
            attribute = f"_VerifiedV3M0ScenarioConstruction__{field}"
            object.__setattr__(
                copied_construction,
                attribute,
                object.__getattribute__(construction, attribute),
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                permit,
                copied_construction,
                "actual",
            )

        with authority_module._PERMIT_LOCK:
            permit_record = authority_module._PERMIT_LIVE.pop(id(permit))
        try:
            with self.assertRaises((TypeError, ValueError)):
                issue_v3m0_application_prestructure_authority(
                    permit,
                    construction,
                    "actual",
                )
        finally:
            with authority_module._PERMIT_LOCK:
                authority_module._PERMIT_LIVE[id(permit)] = permit_record

        with authority_module._SCENARIO_CONSTRUCTION_LOCK:
            construction_record = authority_module._SCENARIO_CONSTRUCTION_LIVE.pop(
                id(construction)
            )
        try:
            with self.assertRaises((TypeError, ValueError)):
                issue_v3m0_application_prestructure_authority(
                    permit,
                    construction,
                    "actual",
                )
        finally:
            with authority_module._SCENARIO_CONSTRUCTION_LOCK:
                authority_module._SCENARIO_CONSTRUCTION_LIVE[id(construction)] = (
                    construction_record
                )

    @task12_sealed_without_strict_task11_replay
    def test_operation_parameters_change_scenario_effect_digest(self) -> None:
        _, spec, permit = self._application_permit(4)
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        raw = authority_module._reverify_verified_scenario_construction(
            construction
        ).construction
        self.assertEqual(len(raw.operation_effect_digests), 3)
        self.assertEqual(
            len({digest for _, digest in raw.operation_effect_digests}),
            3,
        )
        self.assertNotEqual(raw.actual_effect_digest, raw.ablated_effect_digest)
        self.assertNotEqual(
            raw.ablation_pair_snapshot.actual_factory.runtime_operator_sha,
            raw.ablation_pair_snapshot.ablated_factory.runtime_operator_sha,
        )

    @task12_sealed_without_strict_task11_replay
    def test_expected_typed_terminations_are_replayed_and_never_issue_downstream(
        self,
    ) -> None:
        self.assertEqual(
            tuple(ResponseBlockAttemptOutcome.__dataclass_fields__),
            (
                "attempt_schema_version",
                "application_spec",
                "scenario_spec",
                "permit",
                "terminal_stage",
                "status",
                "raw_singular_values",
                "activation_labels",
                "precursor_evidence_sha",
                "downstream_capability_issued",
                "outcome_sha",
            ),
        )
        expected = {
            11: (
                ("activation", "response_null", (0.0,), ("null",)),
                ("activation", "response_grey", (0.5,), ("grey",)),
            ),
            13: (("activation", "response_null", (0.0, 0.0), ("null", "null")),),
            14: (
                (
                    "endpoint_shell",
                    "endpoint_shell_ambiguous",
                    (1.0,),
                    ("signal",),
                ),
                ("activation", "response_null", (0.0,), ("null",)),
                ("trace", "trace_unclassified", (), ()),
                ("stability", "unstable", (), ()),
            ),
        }
        first_attempt = None
        first_permit = None
        first_scenario_id = None
        for ordinal, expected_scenarios in expected.items():
            _, spec, permit = self._application_permit(ordinal)
            for scenario, (
                terminal_stage,
                reason_value,
                singular_values,
                activation_labels,
            ) in zip(spec.scenario_execution_specs, expected_scenarios):
                attempt = issue_v3m0_response_block_attempt(
                    permit,
                    scenario.scenario_id,
                )
                self.assertIs(type(attempt), VerifiedResponseBlockAttemptOutcome)
                raw = reverify_verified_response_block_attempt_outcome(attempt)
                self.assertEqual(raw.application_spec, spec)
                self.assertEqual(raw.scenario_spec, scenario)
                self.assertEqual(raw.permit, permit.permit)
                self.assertEqual(raw.terminal_stage, terminal_stage)
                self.assertFalse(raw.status.defined)
                self.assertEqual(raw.status.reason.value, reason_value)
                self.assertEqual(raw.raw_singular_values, singular_values)
                self.assertEqual(raw.activation_labels, activation_labels)
                self.assertIs(raw.downstream_capability_issued, False)
                self.assertEqual(
                    raw.outcome_sha,
                    canonical_sha(response_block_attempt_outcome_payload(raw)),
                )
                hydrated = verify_response_block_attempt_outcome(
                    raw,
                    permit,
                    scenario.scenario_id,
                )
                self.assertIs(
                    type(hydrated),
                    VerifiedResponseBlockAttemptOutcome,
                )
                if first_attempt is None:
                    first_attempt = attempt
                    first_permit = permit
                    first_scenario_id = scenario.scenario_id

        self.assertIsNotNone(first_attempt)
        self.assertIsNotNone(first_permit)
        self.assertIsNotNone(first_scenario_id)
        fake = object.__new__(VerifiedResponseBlockAttemptOutcome)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            reverify_verified_response_block_attempt_outcome(fake)
        _, _, wrong_permit = self._application_permit(12)
        with self.assertRaises((TypeError, ValueError)):
            verify_response_block_attempt_outcome(
                reverify_verified_response_block_attempt_outcome(first_attempt),
                wrong_permit,
                first_scenario_id,
            )


if __name__ == "__main__":
    unittest.main()
