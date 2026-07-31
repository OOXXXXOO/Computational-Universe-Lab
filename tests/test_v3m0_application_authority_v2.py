"""Task 11/12 current-Parent authority contracts and attack tests."""

from __future__ import annotations

import inspect
from dataclasses import replace
import unittest


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
    from rulespace_v3.parent_freeze import (
        APPLICATION_SCENARIO_SCHEMA_VERSION,
        ApplicationScenarioExecutionSpec,
        application_scenario_execution_spec_payload,
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
    response0 = CurrentScenarioResponseContractV2(
        response_contract_schema_version=(
            CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION
        ),
        contract_state="CURRENT_REVIEWED_RESPONSE_CONTRACT",
        scenario_id=scenario_id,
        selector_sha=SHA1,
        operation_dag_sha=SHA1,
        compiled_contract_sha=SHA1,
        construction_rule_id="test-target-slot-deletion-v1",
        construction_family_id="test-local-shear-v1",
        expected_actual_shell_rank=1,
        expected_matched_shell_rank=1,
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
        scenario_authorities=(scenario,),
        application_authority_sha=SHA0,
    )
    return replace(
        application0,
        application_authority_sha=canonical_sha(
            current_application_authority_v2_payload(application0)
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
            ("parent", "calibration", "control_case_id"),
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
                        "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
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
    def test_expected_permit_selects_all_scenarios_by_control_case_only(self) -> None:
        from types import SimpleNamespace

        from rulespace_v3.application_authority_v2 import (
            _expected_calibration_application_permit_v2,
        )

        application = _application_authority()
        parent = SimpleNamespace(
            parent_freeze_v2_sha=SHA1,
            current_application_authorities=(application,),
        )

        permit = _expected_calibration_application_permit_v2(
            parent,
            _calibration(),
            application.control_case_id,
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
                "C99_CALLER_INVENTED_CASE",
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
