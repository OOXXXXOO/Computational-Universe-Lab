"""Exact-contract and fail-closed tests for the current Parent-v2 authority.

The signed erratum and reviewed final candidate root are deliberately absent.
The only legal behavior in that state is to replay all 23 ``BLOCK_SUCCESS``
scenario authorities and refuse issuance before a capability exists.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
from dataclasses import fields, replace
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ParentPreparationCommitAnchorTests(unittest.TestCase):
    def test_stale_preparation_commit_is_not_accepted_by_shape_alone(self) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            PARENT_V2_PREPARATION_COMMIT_SHA,
            _preparation_commit_blocking_reasons,
        )

        self.assertIsNotNone(PARENT_V2_PREPARATION_COMMIT_SHA)
        reasons = _preparation_commit_blocking_reasons(
            PARENT_V2_PREPARATION_COMMIT_SHA
        )
        self.assertTrue(reasons)
        self.assertTrue(
            any(
                "required preparation path" in reason
                or "reviewed source closure" in reason
                for reason in reasons
            ),
            reasons,
        )


class ParentFreezeV2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            _build_reviewed_modified_scenario_authorities,
            _build_reviewed_unchanged_scenario_authorities,
            _ordered_current_scenario_authorities,
        )

        cls.modified = _build_reviewed_modified_scenario_authorities()
        cls.unchanged = _build_reviewed_unchanged_scenario_authorities()
        cls.all_current = _ordered_current_scenario_authorities(
            cls.modified,
            cls.unchanged,
        )

    def test_exact_wire_schemas_are_separate_from_v1_and_candidates(self) -> None:
        from rulespace_v3.parent_v2_contracts import (
            CurrentApplicationAuthorityV2,
            CurrentScenarioAuthorityV2,
            CurrentScenarioResponseContractV2,
            ParentFreezeV2Manifest,
            SignedSourceRefV1,
        )

        self.assertEqual(
            tuple(item.name for item in fields(SignedSourceRefV1)),
            (
                "source_ref_schema_version",
                "source_role",
                "relative_path",
                "raw_sha256",
                "preparation_commit_sha",
                "source_ref_sha",
            ),
        )
        self.assertIn(
            "expected_matched_shell_rank",
            CurrentScenarioResponseContractV2.__dataclass_fields__,
        )
        self.assertIn(
            "matched_ablated_program_sha",
            CurrentScenarioResponseContractV2.__dataclass_fields__,
        )
        self.assertIn(
            "matched_ablated_effect_digest",
            CurrentScenarioResponseContractV2.__dataclass_fields__,
        )
        self.assertIn(
            "construction_rule_id",
            CurrentScenarioResponseContractV2.__dataclass_fields__,
        )
        for field in (
            "selector_spec",
            "source_trial_vectors",
            "response_torus_denominators",
            "response_reciprocal_indices",
            "source_readout_bridge_reciprocal_indices",
            "source_readout_bridge_steps",
            "reference_reciprocal_index",
            "preregistered_phase_bands",
            "actual_step_count",
            "matched_ablated_step_count",
        ):
            self.assertIn(
                field,
                CurrentScenarioResponseContractV2.__dataclass_fields__,
            )
        self.assertIn(
            "source_disposition",
            CurrentScenarioAuthorityV2.__dataclass_fields__,
        )
        self.assertIn(
            "scenario_authorities",
            CurrentApplicationAuthorityV2.__dataclass_fields__,
        )
        self.assertIn(
            "reviewed_candidate_v2",
            ParentFreezeV2Manifest.__dataclass_fields__,
        )

    def test_readiness_enumerates_all_success_scenarios_with_no_contract_gap(
        self,
    ) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            audit_v3m0_parent_v2_readiness,
            expected_block_success_scenario_ids,
        )

        audit = audit_v3m0_parent_v2_readiness()
        expected = expected_block_success_scenario_ids()

        self.assertEqual(len(expected), 23)
        self.assertEqual(audit.expected_block_success_scenario_ids, expected)
        self.assertEqual(
            audit.promoted_modified_scenario_ids,
            tuple(item.scenario_id for item in self.modified),
        )
        self.assertGreaterEqual(len(audit.promoted_modified_scenario_ids), 5)
        self.assertEqual(audit.unresolved_unchanged_scenario_ids, ())
        self.assertEqual(
            set(audit.promoted_modified_scenario_ids)
            | {item.scenario_id for item in self.unchanged},
            set(expected),
        )
        self.assertFalse(audit.can_issue)
        self.assertEqual(audit.finalization_inputs_state, "NOT_INJECTED")

    def test_five_modified_authorities_are_exact_live_candidate_v2_promotions(
        self,
    ) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            verify_reviewed_modified_scenario_authority,
        )
        from rulespace_v3.parent_v2_contracts import CurrentScenarioAuthorityV2

        self.assertGreaterEqual(len(self.modified), 5)
        for authority in self.modified:
            with self.subTest(scenario_id=authority.scenario_id):
                self.assertIs(type(authority), CurrentScenarioAuthorityV2)
                self.assertEqual(
                    authority.source_disposition,
                    "CANDIDATE_V2_REVIEWED_MODIFIED",
                )
                self.assertRegex(
                    authority.source_candidate_v1_scenario_sha, r"^[0-9a-f]{64}$"
                )
                self.assertRegex(
                    authority.source_candidate_v2_refreeze_sha, r"^[0-9a-f]{64}$"
                )
                response = authority.response_contract
                self.assertGreater(response.expected_actual_shell_rank, 0)
                self.assertGreater(response.expected_matched_shell_rank, 0)
                self.assertGreater(response.actual_step_count, 0)
                self.assertGreater(response.matched_ablated_step_count, 0)
                self.assertTrue(response.construction_rule_id)
                self.assertTrue(response.construction_family_id)
                self.assertRegex(response.actual_program_sha, r"^[0-9a-f]{64}$")
                self.assertRegex(
                    response.matched_ablated_program_sha,
                    r"^[0-9a-f]{64}$",
                )
                self.assertRegex(response.actual_effect_digest, r"^[0-9a-f]{64}$")
                self.assertRegex(
                    response.matched_ablated_effect_digest,
                    r"^[0-9a-f]{64}$",
                )
                self.assertIs(
                    verify_reviewed_modified_scenario_authority(authority),
                    authority,
                )

    def test_fully_resigned_modified_contract_splices_fail_live_replay(self) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_freeze_v2 import (
            verify_reviewed_modified_scenario_authority,
        )
        from rulespace_v3.parent_v2_contracts import (
            current_scenario_authority_v2_payload,
            current_scenario_response_contract_v2_payload,
        )

        original = self.modified[0]
        attacks = (
            (
                "expected_matched_shell_rank",
                original.response_contract.expected_matched_shell_rank + 1,
            ),
            ("matched_ablated_program_sha", "a" * 64),
            ("matched_ablated_effect_digest", "b" * 64),
            ("construction_rule_id", "hostile-re-signed-rule"),
        )
        for field, value in attacks:
            with self.subTest(field=field):
                changed_response = replace(
                    original.response_contract,
                    **{field: value, "response_contract_sha": "0" * 64},
                )
                changed_response = replace(
                    changed_response,
                    response_contract_sha=canonical_sha(
                        current_scenario_response_contract_v2_payload(changed_response)
                    ),
                )
                changed = replace(
                    original,
                    response_contract=changed_response,
                    scenario_authority_sha="0" * 64,
                )
                changed = replace(
                    changed,
                    scenario_authority_sha=canonical_sha(
                        current_scenario_authority_v2_payload(changed)
                    ),
                )
                with self.assertRaises(ValueError):
                    verify_reviewed_modified_scenario_authority(changed)

    def test_c01_c04_are_exact_selected_lane_and_c04_recipe_authorities(self) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            verify_reviewed_unchanged_scenario_authority,
        )

        self.assertEqual(
            tuple(item.control_case_id for item in self.unchanged),
            (
                "C01_BLIND_HOLDOUT_FULL",
                "C02_CONDITIONED_ZERO",
                "C03_EQUAL_RANK_DIRECT_SUM",
                "C04_CANONICAL_ANGLE_025_075",
            ),
        )
        self.assertEqual(
            tuple(
                (
                    item.response_contract.expected_actual_shell_rank,
                    item.response_contract.expected_matched_shell_rank,
                )
                for item in self.unchanged
            ),
            ((1, 1), (1, 0), (2, 1), (1, 1)),
        )
        self.assertEqual(
            tuple(item.source_disposition for item in self.unchanged),
            (
                "PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE",
                "PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE",
                "PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE",
                "PARENT_V1_C04_CLOSED_RECIPE",
            ),
        )
        expected_shapes = (
            ((2, 1), (1, 2), (1, 1)),
            ((2, 1), (1, 2), (1, 1)),
            ((4, 2), (2, 4), (2, 2)),
            ((4, 2), (2, 4), (2, 2)),
        )
        for authority, shapes in zip(self.unchanged, expected_shapes):
            with self.subTest(control_case_id=authority.control_case_id):
                response = authority.response_contract
                self.assertEqual(
                    response.selector_spec.source_injection.shape,
                    shapes[0],
                )
                self.assertEqual(
                    response.selector_spec.readout_coisometry.shape,
                    shapes[1],
                )
                self.assertEqual(response.source_trial_vectors.shape, shapes[2])
                self.assertEqual(response.response_torus_denominators, (8,))
                self.assertEqual(response.response_reciprocal_indices, ((1,), (2,)))
                self.assertIs(
                    verify_reviewed_unchanged_scenario_authority(authority),
                    authority,
                )

        c01, c02, c03, c04 = self.unchanged
        self.assertEqual(
            (
                c01.response_contract.actual_step_count,
                c01.response_contract.matched_ablated_step_count,
                c02.response_contract.actual_step_count,
                c02.response_contract.matched_ablated_step_count,
                c03.response_contract.actual_step_count,
                c03.response_contract.matched_ablated_step_count,
                c04.response_contract.actual_step_count,
                c04.response_contract.matched_ablated_step_count,
            ),
            (3, 3, 3, 0, 6, 3, 57, 45),
        )
        self.assertEqual(
            c04.response_contract.preflight_derivation_or_recipe_sha,
            "04e5f901cf7848eb66d89ee8138b4ba6c128640af7467f584c684b6a80753aa9",
        )
        self.assertEqual(
            c04.response_contract.actual_effect_digest,
            "160801cefb8ac4f0533b0759e542449114dd7e10fcf3d3a89ecd8f540cee104f",
        )
        self.assertEqual(
            c04.response_contract.matched_ablated_effect_digest,
            "4d054aa8b469461be249600ad74b95ef11f682e5e08106c5ff190501eeb7ab1a",
        )

    def test_unchanged_authority_full_resign_cross_case_and_zero_rank_attacks_fail(
        self,
    ) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_freeze_v2 import (
            verify_reviewed_unchanged_scenario_authority,
        )
        from rulespace_v3.parent_v2_contracts import (
            current_scenario_authority_v2_payload,
            current_scenario_response_contract_v2_payload,
        )

        original = self.unchanged[0]
        attacks = (
            ("expected_matched_shell_rank", 0),
            ("matched_ablated_program_sha", "c" * 64),
            ("matched_ablated_effect_digest", "d" * 64),
            ("construction_family_id", "hostile-cross-case-family"),
            (
                "response_reciprocal_indices",
                tuple(reversed(original.response_contract.response_reciprocal_indices)),
            ),
        )
        for field, value in attacks:
            with self.subTest(field=field):
                response = replace(
                    original.response_contract,
                    **{field: value, "response_contract_sha": "0" * 64},
                )
                response = replace(
                    response,
                    response_contract_sha=canonical_sha(
                        current_scenario_response_contract_v2_payload(response)
                    ),
                )
                attacked = replace(
                    original,
                    response_contract=response,
                    scenario_authority_sha="0" * 64,
                )
                attacked = replace(
                    attacked,
                    scenario_authority_sha=canonical_sha(
                        current_scenario_authority_v2_payload(attacked)
                    ),
                )
                with self.assertRaises(ValueError):
                    verify_reviewed_unchanged_scenario_authority(attacked)

        cross_case = replace(
            original,
            control_case_id="C02_CONDITIONED_ZERO",
            scenario_authority_sha="0" * 64,
        )
        cross_case = replace(
            cross_case,
            scenario_authority_sha=canonical_sha(
                current_scenario_authority_v2_payload(cross_case)
            ),
        )
        with self.assertRaises(ValueError):
            verify_reviewed_unchanged_scenario_authority(cross_case)

        with self.assertRaises((TypeError, ValueError)):
            replace(
                original.response_contract,
                expected_actual_shell_rank=0,
            )

    def test_all_twenty_three_authorities_are_in_parent_v1_canonical_order(
        self,
    ) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            _require_complete_block_success_registry,
            expected_block_success_scenario_ids,
        )

        self.assertEqual(len(self.modified), 19)
        self.assertEqual(len(self.unchanged), 4)
        self.assertEqual(
            tuple(item.scenario_id for item in self.all_current),
            expected_block_success_scenario_ids(),
        )
        self.assertIs(
            _require_complete_block_success_registry(self.all_current),
            self.all_current,
        )

    def test_complete_registry_gate_rejects_missing_duplicate_and_extra(self) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            _require_complete_block_success_registry,
        )

        with self.assertRaisesRegex(ValueError, "missing"):
            _require_complete_block_success_registry(self.modified)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            _require_complete_block_success_registry((*self.modified, self.modified[0]))
        extra = copy.deepcopy(self.modified[0])
        object.__setattr__(
            extra,
            "scenario_id",
            "v3m0.synthetic-control.c99.v1.scenario.hostile.v1",
        )
        with self.assertRaisesRegex(ValueError, "outside"):
            _require_complete_block_success_registry((*self.modified, extra))

    def test_root_bearing_builder_and_issuer_are_outside_source_closure(self) -> None:
        from rulespace_v3.parent_freeze_v2 import _build_source_closure

        closure = _build_source_closure()
        paths = {item[0] for item in closure}
        self.assertNotIn("rulespace_v3/parent_freeze_v2.py", paths)
        self.assertNotIn("rulespace_v3/parent_authority.py", paths)

    def test_source_closure_covers_recipe_derivations_and_live_raw_bytes(self) -> None:
        from rulespace_v3.parent_freeze_v2 import _build_source_closure

        closure = _build_source_closure()
        by_path = dict(closure)
        required = {
            "rulespace_v3/ablation.py",
            "rulespace_v3/application_recipes.py",
            "rulespace_v3/c05_projector_recipe.py",
            "rulespace_v3/calibration_authority.py",
            "rulespace_v3/controls.py",
            "rulespace_v3/geometry_application_recipes.py",
            "rulespace_v3/evidence.py",
            "rulespace_v3/factory.py",
            "rulespace_v3/geometry.py",
            "rulespace_v3/response.py",
            "rulespace_v3/registry.py",
            "rulespace_v3/thresholds.py",
            "rulespace_v3/trace.py",
        }
        self.assertTrue(required.issubset(by_path))
        self.assertEqual(tuple(by_path), tuple(sorted(by_path)))
        for relative_path, source_sha in closure:
            self.assertEqual(
                source_sha,
                hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest(),
            )

    def test_draft_and_uninjected_finalization_inputs_make_issuance_impossible(
        self,
    ) -> None:
        from rulespace_v3.parent_authority import issue_v3m0_parent_freeze_v2
        from rulespace_v3.parent_freeze_v2 import (
            PARENT_V2_PREPARATION_COMMIT_SHA,
            PARENT_V2_REVIEWED_CANDIDATE_V2_SHA256,
            PARENT_V2_SIGNED_ERRATUM_RAW_SHA256,
            ParentV2IssuanceBlocked,
        )

        self.assertEqual(
            PARENT_V2_PREPARATION_COMMIT_SHA,
            "93cc836d8dfeac49f8f5d60b41c5f5bdfe9d077d",
        )
        self.assertIsNone(PARENT_V2_REVIEWED_CANDIDATE_V2_SHA256)
        self.assertIsNone(PARENT_V2_SIGNED_ERRATUM_RAW_SHA256)
        self.assertIn(
            "状态：DRAFT",
            (ROOT / "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md").read_text(),
        )
        self.assertEqual(
            len(inspect.signature(issue_v3m0_parent_freeze_v2).parameters), 0
        )
        with self.assertRaises(ParentV2IssuanceBlocked) as caught:
            issue_v3m0_parent_freeze_v2()
        joined = " | ".join(caught.exception.reasons)
        self.assertIn("SIGNED", joined)
        self.assertNotIn("BLOCK_SUCCESS scenarios lack", joined)

    def test_current_facade_rejects_v1_candidate_forgery_and_subclass(self) -> None:
        from rulespace_v3.parent_authority import (
            VerifiedParentFreezeV2,
            require_current_parent,
        )
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
        from rulespace_v3.parent_freeze_v2 import _live_candidate_v2

        for foreign in (
            issue_v3m0_parent_freeze(),
            _live_candidate_v2(),
        ):
            with self.subTest(foreign_type=type(foreign).__name__):
                with self.assertRaises(TypeError):
                    require_current_parent(foreign)

        forged = object.__new__(VerifiedParentFreezeV2)
        with self.assertRaises(ValueError):
            require_current_parent(forged)

        class HostileVerifiedParentFreezeV2(VerifiedParentFreezeV2):
            pass

        hostile = object.__new__(HostileVerifiedParentFreezeV2)
        with self.assertRaises(TypeError):
            require_current_parent(hostile)

    def test_live_candidate_cache_retains_only_immutable_bytes(self) -> None:
        from rulespace_v3.parent_freeze_v2 import _live_candidate_v2

        exposed = _live_candidate_v2()
        expected_root = exposed.candidate_sha
        expected_rank = exposed.scenario_refreezes[
            0
        ].response_template.expected_matched_shell_rank
        object.__setattr__(exposed, "candidate_sha", "f" * 64)
        object.__setattr__(
            exposed.scenario_refreezes[0].response_template,
            "expected_matched_shell_rank",
            expected_rank + 1,
        )
        replayed = _live_candidate_v2()
        self.assertIsNot(replayed, exposed)
        self.assertEqual(replayed.candidate_sha, expected_root)
        self.assertEqual(
            replayed.scenario_refreezes[
                0
            ].response_template.expected_matched_shell_rank,
            expected_rank,
        )

    def test_reviewed_authority_caches_retain_only_immutable_bytes(self) -> None:
        import rulespace_v3.parent_freeze_v2 as freeze

        for forbidden in (
            "_REVIEWED_MODIFIED_SCENARIO_AUTHORITY_SNAPSHOT",
            "_REVIEWED_UNCHANGED_SCENARIO_AUTHORITY_SNAPSHOT",
        ):
            self.assertFalse(hasattr(freeze, forbidden))
        for accessor in (
            freeze._reviewed_modified_scenario_authority_bytes,
            freeze._reviewed_unchanged_scenario_authority_bytes,
        ):
            self.assertIs(type(accessor()), bytes)

        first = freeze._build_reviewed_unchanged_scenario_authorities()
        expected_rank = first[0].response_contract.expected_matched_shell_rank
        object.__setattr__(
            first[0].response_contract,
            "expected_matched_shell_rank",
            0,
        )
        second = freeze._build_reviewed_unchanged_scenario_authorities()
        self.assertIsNot(first, second)
        self.assertEqual(
            second[0].response_contract.expected_matched_shell_rank,
            expected_rank,
        )

    def test_unknown_fields_and_public_promotion_or_hydration_are_closed(self) -> None:
        import rulespace_v3.parent_authority as authority
        import rulespace_v3.parent_freeze_v2 as freeze
        from rulespace_v3.parent_freeze_v2 import (
            verify_reviewed_modified_scenario_authority,
        )

        attacked = copy.deepcopy(self.modified[0])
        object.__setattr__(attacked, "unhashed_override", True)
        with self.assertRaises(ValueError):
            verify_reviewed_modified_scenario_authority(attacked)

        for module in (authority, freeze):
            for forbidden in (
                "promote_parent_v2",
                "promote_current_scenario",
                "verify_parent_freeze_v2_manifest",
                "hydrate_parent_freeze_v2",
            ):
                self.assertFalse(hasattr(module, forbidden))


if __name__ == "__main__":
    unittest.main()
