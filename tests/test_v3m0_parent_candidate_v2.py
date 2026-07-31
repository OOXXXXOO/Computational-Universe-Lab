"""Contract tests for the inert post-preflight Parent candidate v2."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ParentCandidateV2SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v3.parent_candidate_v2 import (
            build_v3m0_parent_freeze_candidate_v2,
        )

        cls.candidate = build_v3m0_parent_freeze_candidate_v2()

    def test_minimal_manifest_is_independent_inert_and_self_hashed(self) -> None:
        from rulespace_v3.parent_candidate_v2 import (
            PARENT_CANDIDATE_V2_SCHEMA_VERSION,
            parent_candidate_v2_manifest_payload,
            verify_parent_freeze_candidate_v2,
        )
        from rulespace_v3.evidence import canonical_sha

        candidate = self.candidate

        self.assertEqual(
            candidate.candidate_schema_version,
            PARENT_CANDIDATE_V2_SCHEMA_VERSION,
        )
        self.assertEqual(candidate.authority_state, "PROVISIONAL_NOT_ISSUED")
        self.assertEqual(
            candidate.based_on_issued_parent_freeze_sha,
            "f57079846203b2cbcf86da7ebfb06c8d6bc55c5a2c16e2548e009d2a6ce607d9",
        )
        self.assertEqual(
            candidate.based_on_candidate_v1_sha,
            "b7fb771dc15ad3da8056ce2d9a5837cc6cc85288cce1a442fea7a4231ce9f96a",
        )
        self.assertEqual(
            candidate.candidate_sha,
            canonical_sha(parent_candidate_v2_manifest_payload(candidate)),
        )
        self.assertIs(verify_parent_freeze_candidate_v2(candidate), candidate)

        from rulespace_v3.parent_freeze import (
            build_v3m0_parent_freeze_candidate,
            verify_parent_freeze_candidate,
        )

        candidate_v1 = build_v3m0_parent_freeze_candidate()
        self.assertEqual(candidate_v1.candidate_sha, candidate.based_on_candidate_v1_sha)
        self.assertIs(verify_parent_freeze_candidate(candidate_v1), candidate_v1)

    def test_five_bindings_are_live_preflight_source_and_commit_bound(self) -> None:
        from rulespace_v3.parent_freeze import (
            build_v3m0_parent_freeze_candidate,
        )

        candidate = self.candidate
        candidate_v1 = build_v3m0_parent_freeze_candidate()
        scenario_by_id = {
            scenario.scenario_execution_spec.scenario_id: scenario
            for application in candidate_v1.application_candidates
            for scenario in application.scenario_candidates
        }
        expected = {
            "v3m0.synthetic-control.c07.v1.scenario.constructive.v1": (
                "c87e94f12f5705cce025d7bd8ee6c25ebd919c73",
                "880434e85ee9cbde10cf968adaad5ea8d868db653535a257c461acf5199cb4bf",
            ),
            "v3m0.synthetic-control.c07.v1.scenario.destructive.v1": (
                "c87e94f12f5705cce025d7bd8ee6c25ebd919c73",
                "601ec8e7e33dddb2355d8fcf25ea1dd814c835243c6fabdb1a5ee56b20609f60",
            ),
            "v3m0.synthetic-control.c08.v1.scenario.rank-missing.v1": (
                "c87e94f12f5705cce025d7bd8ee6c25ebd919c73",
                "691625e4eb95c6cc58b30e5641c80b50d049cd6ab462a947b9e9b0376c783465",
            ),
            "v3m0.synthetic-control.c10.v1.scenario.extra-mode.v1": (
                "c87e94f12f5705cce025d7bd8ee6c25ebd919c73",
                "78730d39f991f9e951c2594274fddf2a1d5249f57f9c38d3aa5979fe138a8c58",
            ),
            "v3m0.synthetic-control.c12.v1.scenario.ir-normalization.v1": (
                "b9b221d362a1d9a76ae14f26f9a90644b5be79ce",
                "a3546be452486fe8fa2dd0dff840e5cae41f74b88c5dcf40e53b700e0f8da693",
            ),
        }
        self.assertEqual(len(candidate.preflight_bindings), 5)
        self.assertEqual(
            tuple(item.scenario_id for item in candidate.preflight_bindings),
            tuple(expected),
        )
        for binding in candidate.preflight_bindings:
            self.assertEqual(
                (binding.source_commit_sha, binding.preflight_artifact_sha),
                expected[binding.scenario_id],
            )
            self.assertEqual(
                hashlib.sha256((ROOT / binding.source_path).read_bytes()).hexdigest(),
                binding.source_sha,
            )
            self.assertEqual(binding.candidate_v1_sha, candidate.based_on_candidate_v1_sha)
            source_scenario = scenario_by_id[binding.scenario_id]
            self.assertEqual(
                binding.candidate_scenario_sha,
                source_scenario.candidate_scenario_sha,
            )
            self.assertEqual(
                binding.scenario_execution_spec_sha,
                source_scenario.scenario_execution_spec.scenario_sha,
            )

    def test_binding_splice_and_resign_are_rejected_by_live_replay(self) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_candidate_v2 import (
            candidate_construction_preflight_binding_payload,
            parent_candidate_v2_manifest_payload,
            verify_parent_freeze_candidate_v2,
        )

        original = self.candidate.preflight_bindings[0]
        changed = replace(
            original,
            preflight_artifact_sha="0" * 64,
            binding_sha="0" * 64,
        )
        changed = replace(
            changed,
            binding_sha=canonical_sha(
                candidate_construction_preflight_binding_payload(changed)
            ),
        )
        attacked = replace(
            self.candidate,
            preflight_bindings=(changed, *self.candidate.preflight_bindings[1:]),
            candidate_sha="0" * 64,
        )
        attacked = replace(
            attacked,
            candidate_sha=canonical_sha(parent_candidate_v2_manifest_payload(attacked)),
        )
        with self.assertRaises(ValueError):
            verify_parent_freeze_candidate_v2(attacked)

    def test_unknown_missing_and_current_authority_issuers_fail_closed(self) -> None:
        import copy

        from rulespace_v3.calibration_authority import (
            issue_v3m0_calibration_application_permit,
        )
        from rulespace_v3.parent_candidate_v2 import (
            verify_parent_freeze_candidate_v2,
        )
        from rulespace_v3.parent_freeze import (
            issue_v3m0_parent_freeze,
            verify_parent_freeze,
        )

        unknown = copy.deepcopy(self.candidate)
        object.__setattr__(unknown, "forged_authority", True)
        with self.assertRaises(ValueError):
            verify_parent_freeze_candidate_v2(unknown)

        missing = copy.deepcopy(self.candidate)
        object.__delattr__(missing, "issuance_disposition")
        with self.assertRaises(ValueError):
            verify_parent_freeze_candidate_v2(missing)

        issued_root_before = issue_v3m0_parent_freeze().manifest.parent_freeze_sha
        with self.assertRaises(TypeError):
            verify_parent_freeze(self.candidate)
        with self.assertRaises(TypeError):
            issue_v3m0_calibration_application_permit(
                self.candidate,
                object(),
                "candidate-v2-must-not-enter-permit-issuer",
            )
        self.assertEqual(
            issue_v3m0_parent_freeze().manifest.parent_freeze_sha,
            issued_root_before,
        )

    def test_prediction_constructor_rejects_measured_exact_semantics(self) -> None:
        from rulespace_v3.parent_candidate_v2 import (
            CandidateV2PredictionQuantity,
            PARENT_CANDIDATE_V2_PREDICTION_QUANTITY_SCHEMA_VERSION,
        )

        with self.assertRaisesRegex(ValueError, "measured"):
            CandidateV2PredictionQuantity(
                quantity_schema_version=(
                    PARENT_CANDIDATE_V2_PREDICTION_QUANTITY_SCHEMA_VERSION
                ),
                quantity_id="forbidden-finite-T-value",
                branch_scope="actual",
                semantics="MEASURED_EXACT",
                formula_id=None,
                analytic_side_labels=(),
                qualitative_requirements=(),
                parameter_refs=(),
                quantity_sha="0" * 64,
            )

    def test_all_five_prediction_profiles_are_analytic_only(self) -> None:
        from rulespace_v3.c12_incidence_preflight import C12_SCENARIO_ID
        from rulespace_v3.interference_mode_preflight import (
            INTERFERENCE_MODE_SCENARIO_IDS,
        )
        from rulespace_v3.parent_candidate_v2 import (
            build_candidate_v2_prediction_profile,
            candidate_v2_prediction_profile_payload,
            verify_candidate_v2_prediction_profile,
        )

        allowed = {
            "FORMULA_DERIVED",
            "ANALYTIC_SIDE",
            "QUALITATIVE_REQUIRED",
        }
        for scenario_id in (*INTERFERENCE_MODE_SCENARIO_IDS, C12_SCENARIO_ID):
            with self.subTest(scenario_id=scenario_id):
                profile = build_candidate_v2_prediction_profile(scenario_id)
                self.assertIs(
                    verify_candidate_v2_prediction_profile(profile),
                    profile,
                )
                self.assertTrue(profile.quantities)
                self.assertTrue(
                    all(item.semantics in allowed for item in profile.quantities)
                )
                body = repr(candidate_v2_prediction_profile_payload(profile)).lower()
                for forbidden in (
                    "measured_exact",
                    "selected_fejer",
                    "singular_values",
                    "bridge_noise",
                    "margin",
                ):
                    self.assertNotIn(forbidden, body)

    def test_all_five_refreezes_compose_binding_dag_selector_and_profiles(
        self,
    ) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            extract_candidate_scenario_contract,
        )
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_candidate_v2 import (
            candidate_v2_scenario_refreeze_payload,
        )

        self.assertEqual(len(self.candidate.scenario_refreezes), 5)
        self.assertEqual(
            tuple(item.scenario_id for item in self.candidate.scenario_refreezes),
            tuple(item.scenario_id for item in self.candidate.preflight_bindings),
        )
        for refreeze, binding in zip(
            self.candidate.scenario_refreezes,
            self.candidate.preflight_bindings,
        ):
            with self.subTest(scenario_id=refreeze.scenario_id):
                self.assertEqual(refreeze.scenario_id, binding.scenario_id)
                self.assertEqual(
                    refreeze.preflight_binding_sha,
                    binding.binding_sha,
                )
                self.assertEqual(len(refreeze.operation_dag.operations), 3)
                compiled = extract_candidate_scenario_contract(
                    refreeze.operation_dag
                )
                self.assertEqual(
                    refreeze.proposed_selector_spec.source_selector.tensor_sha,
                    compiled.proposed_source_selection.tensor_sha,
                )
                self.assertEqual(
                    refreeze.proposed_selector_spec.readout_selector.tensor_sha,
                    compiled.proposed_readout_selection.tensor_sha,
                )
                self.assertEqual(
                    refreeze.response_template.selector_sha,
                    refreeze.proposed_selector_spec.selector_sha,
                )
                self.assertEqual(
                    refreeze.response_template.expected_actual_shell_rank,
                    compiled.expected_actual_shell_rank,
                )
                self.assertEqual(
                    refreeze.response_template.expected_matched_shell_rank,
                    compiled.expected_matched_shell_rank,
                )
                self.assertEqual(
                    refreeze.response_template.dag_sha,
                    refreeze.operation_dag.dag_sha,
                )
                self.assertEqual(
                    refreeze.response_template.compiled_contract_sha,
                    compiled.contract_sha,
                )
                self.assertEqual(
                    refreeze.response_template.actual_program_sha,
                    compiled.actual_program_sha,
                )
                self.assertEqual(
                    refreeze.response_template.matched_ablated_program_sha,
                    compiled.matched_ablated_program_sha,
                )
                self.assertTrue(refreeze.response_template.construction_rule_id)
                self.assertRegex(
                    refreeze.response_template.preflight_actual_effect_digest,
                    r"^[0-9a-f]{64}$",
                )
                self.assertRegex(
                    refreeze.response_template.preflight_matched_effect_digest,
                    r"^[0-9a-f]{64}$",
                )
                self.assertEqual(
                    refreeze.prediction_profile.scenario_id,
                    refreeze.scenario_id,
                )
                self.assertEqual(
                    refreeze.scenario_refreeze_sha,
                    canonical_sha(
                        candidate_v2_scenario_refreeze_payload(refreeze)
                    ),
                )

    def test_nested_selector_tensor_unknown_field_fails_closed(self) -> None:
        import copy

        from rulespace_v3.parent_candidate_v2 import (
            verify_parent_freeze_candidate_v2,
        )

        attacked = copy.deepcopy(self.candidate)
        tensor = attacked.scenario_refreezes[0].proposed_selector_spec.source_selector
        object.__setattr__(tensor, "unhashed_selector_override", True)
        with self.assertRaises(ValueError):
            verify_parent_freeze_candidate_v2(attacked)

    def test_selector_and_dag_splices_fail_after_full_resign(self) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_candidate_v2 import (
            candidate_v2_scenario_refreeze_payload,
            parent_candidate_v2_manifest_payload,
            verify_parent_freeze_candidate_v2,
        )

        first, foreign = self.candidate.scenario_refreezes[:2]
        for field, value in (
            ("proposed_selector_spec", foreign.proposed_selector_spec),
            ("operation_dag", foreign.operation_dag),
        ):
            with self.subTest(field=field):
                changed = replace(
                    first,
                    **{field: value, "scenario_refreeze_sha": "0" * 64},
                )
                changed = replace(
                    changed,
                    scenario_refreeze_sha=canonical_sha(
                        candidate_v2_scenario_refreeze_payload(changed)
                    ),
                )
                attacked = replace(
                    self.candidate,
                    scenario_refreezes=(
                        changed,
                        *self.candidate.scenario_refreezes[1:],
                    ),
                    candidate_sha="0" * 64,
                )
                attacked = replace(
                    attacked,
                    candidate_sha=canonical_sha(
                        parent_candidate_v2_manifest_payload(attacked)
                    ),
                )
                with self.assertRaises(ValueError):
                    verify_parent_freeze_candidate_v2(attacked)

    def test_candidate_and_execution_sha_swaps_fail_after_full_resign(self) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_candidate_v2 import (
            candidate_construction_preflight_binding_payload,
            candidate_v2_scenario_refreeze_payload,
            parent_candidate_v2_manifest_payload,
            verify_parent_freeze_candidate_v2,
        )

        original_binding = self.candidate.preflight_bindings[0]
        original_refreeze = self.candidate.scenario_refreezes[0]
        attacks = (
            ("candidate_scenario_sha", original_binding.scenario_execution_spec_sha),
            ("scenario_execution_spec_sha", original_binding.candidate_scenario_sha),
        )
        for field, value in attacks:
            with self.subTest(field=field):
                changed_binding = replace(
                    original_binding,
                    **{field: value, "binding_sha": "0" * 64},
                )
                changed_binding = replace(
                    changed_binding,
                    binding_sha=canonical_sha(
                        candidate_construction_preflight_binding_payload(
                            changed_binding
                        )
                    ),
                )
                changed_refreeze = replace(
                    original_refreeze,
                    preflight_binding_sha=changed_binding.binding_sha,
                    scenario_refreeze_sha="0" * 64,
                )
                changed_refreeze = replace(
                    changed_refreeze,
                    scenario_refreeze_sha=canonical_sha(
                        candidate_v2_scenario_refreeze_payload(changed_refreeze)
                    ),
                )
                attacked = replace(
                    self.candidate,
                    preflight_bindings=(
                        changed_binding,
                        *self.candidate.preflight_bindings[1:],
                    ),
                    scenario_refreezes=(
                        changed_refreeze,
                        *self.candidate.scenario_refreezes[1:],
                    ),
                    candidate_sha="0" * 64,
                )
                attacked = replace(
                    attacked,
                    candidate_sha=canonical_sha(
                        parent_candidate_v2_manifest_payload(attacked)
                    ),
                )
                with self.assertRaises(ValueError):
                    verify_parent_freeze_candidate_v2(attacked)

    def test_response_template_attacks_fail_after_full_resign(self) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_candidate_v2 import (
            candidate_v2_response_template_payload,
            candidate_v2_scenario_refreeze_payload,
            parent_candidate_v2_manifest_payload,
            verify_parent_freeze_candidate_v2,
        )

        index = 2
        original_refreeze = self.candidate.scenario_refreezes[index]
        original_template = original_refreeze.response_template
        attacks = (
            ("compiled_contract_sha", "f" * 64),
            ("expected_matched_shell_rank", 2),
            ("preflight_actual_effect_digest", "f" * 64),
            (
                "construction_rule_id",
                f"{original_template.construction_rule_id}.forged",
            ),
        )
        for field, value in attacks:
            with self.subTest(field=field):
                changed_template = replace(
                    original_template,
                    **{field: value, "template_sha": "0" * 64},
                )
                changed_template = replace(
                    changed_template,
                    template_sha=canonical_sha(
                        candidate_v2_response_template_payload(changed_template)
                    ),
                )
                changed_refreeze = replace(
                    original_refreeze,
                    response_template=changed_template,
                    scenario_refreeze_sha="0" * 64,
                )
                changed_refreeze = replace(
                    changed_refreeze,
                    scenario_refreeze_sha=canonical_sha(
                        candidate_v2_scenario_refreeze_payload(changed_refreeze)
                    ),
                )
                refreezes = list(self.candidate.scenario_refreezes)
                refreezes[index] = changed_refreeze
                attacked = replace(
                    self.candidate,
                    scenario_refreezes=tuple(refreezes),
                    candidate_sha="0" * 64,
                )
                attacked = replace(
                    attacked,
                    candidate_sha=canonical_sha(
                        parent_candidate_v2_manifest_payload(attacked)
                    ),
                )
                with self.assertRaises(ValueError):
                    verify_parent_freeze_candidate_v2(attacked)


if __name__ == "__main__":
    unittest.main()
