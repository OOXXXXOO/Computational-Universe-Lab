"""Task 11/12 current-Parent authority contracts and attack tests."""

from __future__ import annotations

import inspect
from dataclasses import replace
from types import SimpleNamespace
import unittest

import numpy as np


SHA0 = "0" * 64
SHA1 = "1" * 64
SHA2 = "2" * 64
SHA3 = "3" * 64


def _selection():
    from rulespace_v3.calibration_authority import (
        SelectedControlEvidenceRef,
        WindowThresholdSelection,
        window_threshold_selection_payload,
    )
    from rulespace_v3.evidence import canonical_sha

    refs = tuple(
        SelectedControlEvidenceRef(
            control_id=control_id,
            control_registry_entry_sha=SHA1,
            expected_rank_declaration_sha=SHA1,
            run_spec_sha=SHA1,
            paired_response_sha=SHA1,
            shell_manifest_sha=SHA1,
            comparison_2t_run_spec_sha=SHA1,
            comparison_2t_response_sha=SHA1,
            comparison_2t_shell_manifest_sha=SHA1,
        )
        for control_id in ("full", "zero", "direct_sum")
    )
    provisional = WindowThresholdSelection(
        selected_fejer_order=256,
        h_scale_ref=1.0,
        h_noise_ref=1e-14,
        h_signal_min=0.5,
        h_tau_sig=1e-3,
        curv_scale_ref=1.0,
        curv_noise_ref=1e-14,
        curv_signal_min=0.5,
        curv_tau_sig=1e-3,
        selected_evidence_refs=refs,
        selection_sha=SHA0,
    )
    return replace(
        provisional,
        selection_sha=canonical_sha(
            window_threshold_selection_payload(provisional)
        ),
    )


def _calibration(parent_sha: str = SHA1):
    from rulespace_v3.application_authority_v2 import (
        WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION,
        WindowThresholdCalibrationV2,
        window_threshold_calibration_v2_payload,
    )
    from rulespace_v3.evidence import canonical_sha

    provisional = WindowThresholdCalibrationV2(
        calibration_schema_version=WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION,
        authority_state="CURRENT_PARENT_V2_BOUND_CALIBRATION",
        parent_freeze_v2_sha=parent_sha,
        current_control_registry_sha=SHA2,
        current_window_protocol_sha=SHA3,
        current_calibration_outcome_sha="4" * 64,
        selection=_selection(),
        replay_contract_id=(
            "replay-window-threshold-calibration-under-current-parent-v2"
        ),
        calibration_v2_sha=SHA0,
    )
    return replace(
        provisional,
        calibration_v2_sha=canonical_sha(
            window_threshold_calibration_v2_payload(provisional)
        ),
    )


def _application_authority(
    control_case_id: str = "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
    application_instance_id: str = "v3m0.synthetic-control.c07.v1",
    scenario_id: str = (
        "v3m0.synthetic-control.c07.v1.scenario.constructive.v1"
    ),
):
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.factory import freeze_complex_tensor
    from rulespace_v3.parent_freeze import (
        APPLICATION_SCENARIO_SCHEMA_VERSION,
        SCENARIO_BASIS_SELECTOR_SCHEMA_VERSION,
        ApplicationScenarioExecutionSpec,
        ScenarioBasisSelectorSpec,
        application_scenario_execution_spec_payload,
        scenario_basis_selector_spec_payload,
    )
    from rulespace_v3.parent_v2_contracts import (
        CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION,
        CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION,
        CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION,
        CurrentApplicationAuthorityV2,
        CurrentScenarioAuthorityV2,
        CurrentScenarioResponseContractV2,
        current_application_authority_v2_payload,
        current_scenario_authority_v2_payload,
        current_scenario_response_contract_v2_payload,
    )

    execution0 = ApplicationScenarioExecutionSpec(
        scenario_schema_version=APPLICATION_SCENARIO_SCHEMA_VERSION,
        scenario_id=scenario_id,
        operation_output_ids=("output.00",),
        execution_lane="BLOCK_SUCCESS",
        execution_recipe_id="test-local-shear-recipe-v1",
        recipe_parameter_wires=(),
        recipe_derivation_source_id="test-reviewed-dag-v1",
        expected_terminal_stage="success",
        expected_undefined_reason=None,
        expected_artifact_type="VerifiedResponseBlock",
        scenario_sha=SHA0,
    )
    execution = replace(
        execution0,
        scenario_sha=canonical_sha(
            application_scenario_execution_spec_payload(execution0)
        ),
    )
    source_injection = freeze_complex_tensor(
        np.asarray(((1.0,), (0.0,)), dtype=np.complex128)
    )
    readout_coisometry = freeze_complex_tensor(
        np.asarray(((1.0, 0.0),), dtype=np.complex128)
    )
    selector0 = ScenarioBasisSelectorSpec(
        selector_schema_version=SCENARIO_BASIS_SELECTOR_SCHEMA_VERSION,
        scenario_id=scenario_id,
        public_source_basis_manifest_id=SHA1,
        public_readout_basis_manifest_id=SHA2,
        source_selector_derivation_id="test-source-selector-v1",
        readout_selector_derivation_id="test-readout-selector-v1",
        source_selector=source_injection,
        readout_selector=readout_coisometry,
        source_injection=source_injection,
        readout_coisometry=readout_coisometry,
        selector_sha=SHA0,
    )
    selector = replace(
        selector0,
        selector_sha=canonical_sha(
            scenario_basis_selector_spec_payload(selector0)
        ),
    )
    response0 = CurrentScenarioResponseContractV2(
        response_contract_schema_version=(
            CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION
        ),
        contract_state="CURRENT_REVIEWED_RESPONSE_CONTRACT",
        scenario_id=scenario_id,
        selector_sha=selector.selector_sha,
        selector_spec=selector,
        source_trial_vectors=freeze_complex_tensor(
            np.eye(1, dtype=np.complex128)
        ),
        response_torus_denominators=(8, 8),
        response_reciprocal_indices=((1, 0),),
        source_readout_bridge_reciprocal_indices=((1, 0),),
        source_readout_bridge_steps=(4,),
        reference_reciprocal_index=(1, 0),
        preregistered_phase_bands=((0.2, 0.4),),
        operation_dag_sha=SHA1,
        compiled_contract_sha=SHA1,
        construction_rule_id="test-target-slot-deletion-v1",
        construction_family_id="test-local-shear-v1",
        expected_actual_shell_rank=1,
        expected_matched_shell_rank=1,
        actual_step_count=1,
        matched_ablated_step_count=1,
        actual_program_sha=SHA1,
        matched_ablated_program_sha=SHA2,
        preflight_derivation_or_recipe_sha=SHA3,
        actual_effect_digest=SHA1,
        matched_ablated_effect_digest=SHA2,
        response_template_sha=SHA1,
        prediction_profile_sha=SHA1,
        uses_global_fft_projection=False,
        uses_per_k_time_step_projector=False,
        response_contract_sha=SHA0,
    )
    response = replace(
        response0,
        response_contract_sha=canonical_sha(
            current_scenario_response_contract_v2_payload(response0)
        ),
    )
    scenario0 = CurrentScenarioAuthorityV2(
        scenario_authority_schema_version=(
            CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION
        ),
        authority_state="CURRENT_REVIEWED_SCENARIO",
        control_case_id=control_case_id,
        application_instance_id=application_instance_id,
        based_on_application_spec_sha=SHA1,
        scenario_id=scenario_id,
        scenario_execution_spec=execution,
        source_disposition="CANDIDATE_V2_REVIEWED_MODIFIED",
        source_candidate_v1_scenario_sha=SHA1,
        source_candidate_v2_refreeze_sha=SHA2,
        response_contract=response,
        scenario_authority_sha=SHA0,
    )
    scenario = replace(
        scenario0,
        scenario_authority_sha=canonical_sha(
            current_scenario_authority_v2_payload(scenario0)
        ),
    )
    application0 = CurrentApplicationAuthorityV2(
        application_authority_schema_version=(
            CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION
        ),
        authority_state="CURRENT_REVIEWED_APPLICATION",
        control_case_id=control_case_id,
        application_instance_id=application_instance_id,
        based_on_application_spec_sha=SHA1,
        source_candidate_v1_application_sha=SHA1,
        complete_scenario_execution_specs=(execution,),
        scenario_authorities=(scenario,),
        application_authority_sha=SHA0,
    )
    return replace(
        application0,
        application_authority_sha=canonical_sha(
            current_application_authority_v2_payload(application0)
        ),
    )


def _parent_manifest(*application_stages):
    applications = tuple(item[0] for item in application_stages)
    specifications = tuple(
        SimpleNamespace(
            control_case_id=application.control_case_id,
            application_instance_id=application.application_instance_id,
            application_spec_sha=application.based_on_application_spec_sha,
            required_pipeline_stages=(pipeline_stage,),
        )
        for application, pipeline_stage in application_stages
    )
    candidates = tuple(
        SimpleNamespace(
            control_case_id=application.control_case_id,
            application_instance_id=application.application_instance_id,
            based_on_application_spec_sha=(
                application.based_on_application_spec_sha
            ),
            candidate_application_sha=(
                application.source_candidate_v1_application_sha
            ),
            scenario_candidates=tuple(
                SimpleNamespace(scenario_execution_spec=execution)
                for execution in application.complete_scenario_execution_specs
            ),
        )
        for application in applications
    )
    return SimpleNamespace(
        parent_freeze_v2_sha=SHA1,
        current_application_authorities=applications,
        historical_parent_v1=SimpleNamespace(
            synthetic_control_application_specs=specifications,
        ),
        reviewed_candidate_v1=SimpleNamespace(
            application_candidates=candidates,
        ),
    )


class ApplicationAuthorityV2PublicSurfaceTests(unittest.TestCase):
    def test_public_issuers_accept_no_threshold_or_scenario_template_inputs(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            issue_v3m0_calibration_application_permit_v2,
            issue_v3m0_window_threshold_calibration_v2,
        )

        self.assertEqual(
            tuple(
                inspect.signature(
                    issue_v3m0_window_threshold_calibration_v2
                ).parameters
            ),
            ("parent",),
        )
        self.assertEqual(
            tuple(
                inspect.signature(
                    issue_v3m0_calibration_application_permit_v2
                ).parameters
            ),
            ("parent", "calibration", "application_instance_id"),
        )

    def test_calibration_issuer_rejects_v1_candidate_and_untyped_parents(
        self,
    ) -> None:
        from rulespace_v3.application_authority_v2 import (
            issue_v3m0_window_threshold_calibration_v2,
        )
        from rulespace_v3.parent_candidate_v2 import (
            ParentFreezeCandidateV2Manifest,
        )
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze

        for value in (
            issue_v3m0_parent_freeze(),
            object.__new__(ParentFreezeCandidateV2Manifest),
            object(),
        ):
            with self.subTest(parent_type=type(value).__name__):
                with self.assertRaises(TypeError):
                    issue_v3m0_window_threshold_calibration_v2(value)

    def test_permit_issuer_rejects_v1_raw_forged_and_subclass_calibrations(
        self,
    ) -> None:
        from rulespace_v3.application_authority_v2 import (
            VerifiedWindowThresholdCalibrationV2,
            WindowThresholdCalibrationV2,
            issue_v3m0_calibration_application_permit_v2,
        )
        from rulespace_v3.calibration_authority import (
            VerifiedWindowThresholdCalibration,
        )

        class HostileCalibration(VerifiedWindowThresholdCalibrationV2):
            pass

        for value in (
            object.__new__(VerifiedWindowThresholdCalibration),
            object.__new__(WindowThresholdCalibrationV2),
            object.__new__(HostileCalibration),
            object(),
        ):
            with self.subTest(calibration_type=type(value).__name__):
                with self.assertRaises(TypeError):
                    issue_v3m0_calibration_application_permit_v2(
                        object(),
                        value,
                        "v3m0.synthetic-control.c07.v1",
                    )

    def test_parent_seam_still_fails_closed_without_v2_task11_replay(self) -> None:
        from types import SimpleNamespace

        from rulespace_v3 import application_authority_v2 as authority

        with self.assertRaisesRegex(
            authority.ApplicationAuthorityV2UpstreamUnavailable,
            "cannot be rebound",
        ):
            authority._replay_current_window_threshold_calibration_v2(
                object(),
                SimpleNamespace(parent_freeze_v2_sha=SHA1),
            )

    def test_public_issuer_is_detached_from_module_rebinding(self) -> None:
        from types import SimpleNamespace
        from unittest.mock import patch

        from rulespace_v3 import application_authority_v2 as authority

        with patch.object(
            authority,
            "_require_exact_current_parent",
            return_value=SimpleNamespace(parent_freeze_v2_sha=SHA1),
        ), patch.object(
            authority,
            "_replay_current_window_threshold_calibration_v2",
            return_value=_calibration(),
        ):
            with self.assertRaises(TypeError):
                authority.issue_v3m0_window_threshold_calibration_v2(object())

    def test_private_raw_issuers_are_not_reachable_module_attributes(self) -> None:
        from rulespace_v3 import application_authority_v2 as authority

        for name in (
            "_issue_replayed_window_threshold_calibration_v2",
            "_issue_calibration_application_permit_v2",
            "_make_public_issuers",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(authority, name))


class WindowThresholdCalibrationV2WireTests(unittest.TestCase):
    def test_exact_wire_recursively_binds_current_parent_and_selection(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION,
            WindowThresholdCalibrationV2,
            verify_window_threshold_calibration_v2_wire,
            window_threshold_calibration_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = WindowThresholdCalibrationV2(
            calibration_schema_version=(
                WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION
            ),
            authority_state="CURRENT_PARENT_V2_BOUND_CALIBRATION",
            parent_freeze_v2_sha=SHA1,
            current_control_registry_sha=SHA2,
            current_window_protocol_sha=SHA3,
            current_calibration_outcome_sha="4" * 64,
            selection=_selection(),
            replay_contract_id=(
                "replay-window-threshold-calibration-under-current-parent-v2"
            ),
            calibration_v2_sha=SHA0,
        )
        calibration = replace(
            provisional,
            calibration_v2_sha=canonical_sha(
                window_threshold_calibration_v2_payload(provisional)
            ),
        )

        verified = verify_window_threshold_calibration_v2_wire(calibration)
        self.assertEqual(verified, calibration)
        self.assertIsNot(verified, calibration)
        self.assertEqual(
            verified.calibration_v2_sha,
            canonical_sha(window_threshold_calibration_v2_payload(verified)),
        )

    def test_unknown_nested_field_is_rejected_even_when_outer_hash_is_resigned(
        self,
    ) -> None:
        import copy

        from rulespace_v3.application_authority_v2 import (
            WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION,
            WindowThresholdCalibrationV2,
            verify_window_threshold_calibration_v2_wire,
            window_threshold_calibration_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = WindowThresholdCalibrationV2(
            calibration_schema_version=(
                WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION
            ),
            authority_state="CURRENT_PARENT_V2_BOUND_CALIBRATION",
            parent_freeze_v2_sha=SHA1,
            current_control_registry_sha=SHA2,
            current_window_protocol_sha=SHA3,
            current_calibration_outcome_sha="4" * 64,
            selection=_selection(),
            replay_contract_id=(
                "replay-window-threshold-calibration-under-current-parent-v2"
            ),
            calibration_v2_sha=SHA0,
        )
        clean = replace(
            provisional,
            calibration_v2_sha=canonical_sha(
                window_threshold_calibration_v2_payload(provisional)
            ),
        )
        attacked = copy.deepcopy(clean)
        object.__setattr__(
            attacked.selection,
            "caller_threshold_override",
            0.0,
        )

        with self.assertRaises(ValueError):
            verify_window_threshold_calibration_v2_wire(attacked)


class WindowThresholdCalibrationV2CapabilityTests(unittest.TestCase):
    def test_wrapper_is_internal_exact_live_and_immutable(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            VerifiedWindowThresholdCalibrationV2,
            WindowThresholdCalibrationV2,
            require_window_threshold_calibration_v2,
        )

        raw = object.__new__(WindowThresholdCalibrationV2)
        with self.assertRaises(TypeError):
            VerifiedWindowThresholdCalibrationV2(object(), raw, SHA0)

        forged = object.__new__(VerifiedWindowThresholdCalibrationV2)
        with self.assertRaises(ValueError):
            require_window_threshold_calibration_v2(forged)
        with self.assertRaises(AttributeError):
            forged.caller_threshold_override = 0.0

        class HostileCalibration(VerifiedWindowThresholdCalibrationV2):
            pass

        with self.assertRaises(TypeError):
            require_window_threshold_calibration_v2(
                object.__new__(HostileCalibration)
            )
        with self.assertRaises(TypeError):
            require_window_threshold_calibration_v2(raw)


class CalibrationApplicationPermitV2WireTests(unittest.TestCase):
    def test_expected_permit_selects_all_scenarios_by_application_instance(
        self,
    ) -> None:
        from rulespace_v3.application_authority_v2 import (
            _expected_calibration_application_permit_v2,
        )

        application = _application_authority()
        parent = _parent_manifest(
            (application, "control-application-evidence"),
        )

        permit = _expected_calibration_application_permit_v2(
            parent,
            _calibration(),
            application.application_instance_id,
        )
        self.assertEqual(permit.application_authority, application)
        self.assertEqual(
            permit.scenario_authority_shas,
            tuple(
                item.scenario_authority_sha
                for item in application.scenario_authorities
            ),
        )
        with self.assertRaises(ValueError):
            _expected_calibration_application_permit_v2(
                parent,
                _calibration(),
                "v3m0.synthetic-control.c99.caller-invented.v1",
            )

    def test_selected_calibration_case_and_instance_ids_never_get_permits(
        self,
    ) -> None:
        from rulespace_v3.application_authority_v2 import (
            _expected_calibration_application_permit_v2,
        )

        selected = (
            (
                "C01_BLIND_HOLDOUT_FULL",
                "v3m0.synthetic-control.c01.v1",
                "holdout-span",
            ),
            (
                "C02_CONDITIONED_ZERO",
                "v3m0.synthetic-control.c02.v1",
                "conditioned-zero",
            ),
            (
                "C03_EQUAL_RANK_DIRECT_SUM",
                "v3m0.synthetic-control.c03.v1",
                "equal-rank-direct-sum",
            ),
        )
        for control_case_id, application_instance_id, scenario_slug in selected:
            application = _application_authority(
                control_case_id=control_case_id,
                application_instance_id=application_instance_id,
                scenario_id=(
                    f"{application_instance_id}.scenario.{scenario_slug}.v1"
                ),
            )
            parent = _parent_manifest((application, "window-calibration"))
            for caller_identifier in (
                control_case_id,
                application_instance_id,
            ):
                with self.subTest(
                    control_case_id=control_case_id,
                    caller_identifier=caller_identifier,
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "application instance|selected calibration",
                    ):
                        _expected_calibration_application_permit_v2(
                            parent,
                            _calibration(),
                            caller_identifier,
                        )

    def test_c20_analysis_application_is_not_removed_by_case_filter(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            _expected_calibration_application_permit_v2,
        )

        application = _application_authority(
            control_case_id="C20_DM26_CLEAN_ZERO_TRUE_FLOOR",
            application_instance_id="v3m0.synthetic-control.c20.v1",
            scenario_id=(
                "v3m0.synthetic-control.c20.v1.scenario.clean-zero.v1"
            ),
        )
        parent = _parent_manifest(
            (application, "control-application-evidence"),
        )

        permit = _expected_calibration_application_permit_v2(
            parent,
            _calibration(),
            application.application_instance_id,
        )
        self.assertEqual(permit.control_case_id, application.control_case_id)
        self.assertEqual(
            permit.application_authority.application_instance_id,
            application.application_instance_id,
        )

    def test_exact_permit_binds_parent_calibration_application_and_scenarios(
        self,
    ) -> None:
        from rulespace_v3.application_authority_v2 import (
            CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION,
            CalibrationApplicationPermitV2,
            calibration_application_permit_v2_payload,
            verify_calibration_application_permit_v2_wire,
        )
        from rulespace_v3.evidence import canonical_sha

        application = _application_authority()
        scenario_shas = tuple(
            item.scenario_authority_sha
            for item in application.scenario_authorities
        )
        provisional = CalibrationApplicationPermitV2(
            permit_schema_version=(
                CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION
            ),
            scope="v3m0-current-synthetic-control-application-v2",
            parent_freeze_v2_sha=SHA1,
            calibration=_calibration(),
            control_case_id=application.control_case_id,
            application_authority=application,
            scenario_authority_shas=scenario_shas,
            selected_fejer_order=256,
            permit_sha=SHA0,
        )
        permit = replace(
            provisional,
            permit_sha=canonical_sha(
                calibration_application_permit_v2_payload(provisional)
            ),
        )

        verified = verify_calibration_application_permit_v2_wire(permit)
        self.assertEqual(verified, permit)
        self.assertIsNot(verified, permit)
        self.assertEqual(
            verified.scenario_authority_shas,
            scenario_shas,
        )

    def test_control_case_and_scenario_splices_fail_after_outer_resign(self) -> None:
        import copy

        from rulespace_v3.application_authority_v2 import (
            CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION,
            CalibrationApplicationPermitV2,
            calibration_application_permit_v2_payload,
            verify_calibration_application_permit_v2_wire,
        )
        from rulespace_v3.evidence import canonical_sha

        application = _application_authority()
        provisional = CalibrationApplicationPermitV2(
            permit_schema_version=(
                CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION
            ),
            scope="v3m0-current-synthetic-control-application-v2",
            parent_freeze_v2_sha=SHA1,
            calibration=_calibration(),
            control_case_id=application.control_case_id,
            application_authority=application,
            scenario_authority_shas=tuple(
                item.scenario_authority_sha
                for item in application.scenario_authorities
            ),
            selected_fejer_order=256,
            permit_sha=SHA0,
        )
        clean = replace(
            provisional,
            permit_sha=canonical_sha(
                calibration_application_permit_v2_payload(provisional)
            ),
        )
        for field, value in (
            ("control_case_id", "C08_RANK_R_MISSING_MODES"),
            ("scenario_authority_shas", (SHA3,)),
            ("parent_freeze_v2_sha", SHA2),
        ):
            with self.subTest(field=field):
                attacked = copy.deepcopy(clean)
                object.__setattr__(attacked, field, value)
                object.__setattr__(attacked, "permit_sha", SHA0)
                object.__setattr__(
                    attacked,
                    "permit_sha",
                    canonical_sha(
                        calibration_application_permit_v2_payload(attacked)
                    ),
                )
                with self.assertRaises(ValueError):
                    verify_calibration_application_permit_v2_wire(attacked)


class CalibrationApplicationPermitV2CanonicalParentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
        from rulespace_v3.parent_freeze_v2 import (
            _build_reviewed_modified_scenario_authorities,
            _build_reviewed_unchanged_scenario_authorities,
            _group_application_authorities,
            _live_candidate_v1,
            _ordered_current_scenario_authorities,
        )

        candidate = _live_candidate_v1()
        current = _ordered_current_scenario_authorities(
            _build_reviewed_modified_scenario_authorities(),
            _build_reviewed_unchanged_scenario_authorities(),
        )
        cls.candidate = candidate
        cls.parent = SimpleNamespace(
            parent_freeze_v2_sha=SHA1,
            current_application_authorities=(
                _group_application_authorities(current, candidate)
            ),
            historical_parent_v1=issue_v3m0_parent_freeze().manifest,
            reviewed_candidate_v1=candidate,
        )

    def test_c13_c14_c20_permits_keep_complete_typed_analysis_lineage(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            _expected_calibration_application_permit_v2,
        )

        candidate_by_case = {
            item.control_case_id: item
            for item in self.candidate.application_candidates
        }
        expected_lanes = {
            "C13_BOTH_ZERO_UNDEFINED": ("EXPECTED_TYPED_TERMINATION",),
            "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL": (
                "EXPECTED_TYPED_TERMINATION",
                "EXPECTED_TYPED_TERMINATION",
                "EXPECTED_TYPED_TERMINATION",
                "EXPECTED_TYPED_TERMINATION",
            ),
            "C20_DM26_CLEAN_ZERO_TRUE_FLOOR": (
                "ANALYSIS_CONTROL",
                "ANALYSIS_CONTROL",
            ),
        }
        for control_case_id, lanes in expected_lanes.items():
            with self.subTest(control_case_id=control_case_id):
                source = candidate_by_case[control_case_id]
                permit = _expected_calibration_application_permit_v2(
                    self.parent,
                    _calibration(),
                    source.application_instance_id,
                )
                self.assertEqual(permit.scenario_authority_shas, ())
                self.assertEqual(
                    permit.application_authority.complete_scenario_execution_specs,
                    tuple(
                        item.scenario_execution_spec
                        for item in source.scenario_candidates
                    ),
                )
                self.assertEqual(
                    tuple(
                        item.execution_lane
                        for item in (
                            permit.application_authority.complete_scenario_execution_specs
                        )
                    ),
                    lanes,
                )

    def test_c07_permit_keeps_constructive_destructive_reviewed_split(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            _expected_calibration_application_permit_v2,
        )

        source = next(
            item
            for item in self.candidate.application_candidates
            if item.control_case_id
            == "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE"
        )
        permit = _expected_calibration_application_permit_v2(
            self.parent,
            _calibration(),
            source.application_instance_id,
        )
        expected_ids = tuple(
            item.scenario_execution_spec.scenario_id
            for item in source.scenario_candidates
        )
        self.assertEqual(
            tuple(
                item.scenario_id
                for item in (
                    permit.application_authority.complete_scenario_execution_specs
                )
            ),
            expected_ids,
        )
        self.assertEqual(
            tuple(
                item.scenario_id
                for item in permit.application_authority.scenario_authorities
            ),
            expected_ids,
        )

    def test_resigned_current_application_cannot_reorder_reviewed_tuple(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            _expected_calibration_application_permit_v2,
        )
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_v2_contracts import (
            current_application_authority_v2_payload,
        )

        source = next(
            item
            for item in self.parent.current_application_authorities
            if item.control_case_id
            == "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL"
        )
        provisional = replace(
            source,
            complete_scenario_execution_specs=tuple(
                reversed(source.complete_scenario_execution_specs)
            ),
            application_authority_sha=SHA0,
        )
        attacked = replace(
            provisional,
            application_authority_sha=canonical_sha(
                current_application_authority_v2_payload(provisional)
            ),
        )
        parent = SimpleNamespace(
            **{
                **vars(self.parent),
                "current_application_authorities": tuple(
                    attacked if item is source else item
                    for item in self.parent.current_application_authorities
                ),
            }
        )

        with self.assertRaisesRegex(ValueError, "reviewed candidate|spliced"):
            _expected_calibration_application_permit_v2(
                parent,
                _calibration(),
                attacked.application_instance_id,
            )

    def test_real_c01_c03_selected_lanes_still_cannot_receive_permits(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            _expected_calibration_application_permit_v2,
        )

        for source in self.candidate.application_candidates[:3]:
            with self.subTest(control_case_id=source.control_case_id):
                with self.assertRaisesRegex(ValueError, "selected calibration"):
                    _expected_calibration_application_permit_v2(
                        self.parent,
                        _calibration(),
                        source.application_instance_id,
                    )


class CalibrationApplicationPermitV2CapabilityTests(unittest.TestCase):
    def test_wrapper_is_internal_exact_live_and_immutable(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            CalibrationApplicationPermitV2,
            VerifiedCalibrationApplicationPermitV2,
            require_calibration_application_permit_v2,
        )

        raw = object.__new__(CalibrationApplicationPermitV2)
        with self.assertRaises(TypeError):
            VerifiedCalibrationApplicationPermitV2(object(), raw, SHA0)

        forged = object.__new__(VerifiedCalibrationApplicationPermitV2)
        with self.assertRaises(ValueError):
            require_calibration_application_permit_v2(forged)
        with self.assertRaises(AttributeError):
            forged.scenario_template_override = object()

        class HostilePermit(VerifiedCalibrationApplicationPermitV2):
            pass

        with self.assertRaises(TypeError):
            require_calibration_application_permit_v2(
                object.__new__(HostilePermit)
            )
        with self.assertRaises(TypeError):
            require_calibration_application_permit_v2(raw)


if __name__ == "__main__":
    unittest.main()
