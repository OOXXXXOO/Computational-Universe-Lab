"""Exact-contract and fail-closed tests for the current Parent-v2 authority.

The signed erratum and its preparation commit are deliberately absent while
this test is introduced.  The only legal behavior in that state is to replay
the reviewed five-scenario candidate, enumerate every BLOCK_SUCCESS scenario,
and refuse issuance with an explicit gap inventory.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
from dataclasses import fields, replace
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ParentFreezeV2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            _build_reviewed_modified_scenario_authorities,
        )

        cls.modified = _build_reviewed_modified_scenario_authorities()

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

    def test_readiness_enumerates_all_success_scenarios_and_blocks_eighteen(self) -> None:
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
        self.assertEqual(
            len(audit.unresolved_unchanged_scenario_ids),
            23 - len(audit.promoted_modified_scenario_ids),
        )
        self.assertEqual(
            set(audit.promoted_modified_scenario_ids)
            | set(audit.unresolved_unchanged_scenario_ids),
            set(expected),
        )
        self.assertFalse(audit.can_issue)
        self.assertEqual(audit.finalization_inputs_state, "NOT_INJECTED")

    def test_five_modified_authorities_are_exact_live_candidate_v2_promotions(self) -> None:
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
                self.assertRegex(authority.source_candidate_v1_scenario_sha, r"^[0-9a-f]{64}$")
                self.assertRegex(authority.source_candidate_v2_refreeze_sha, r"^[0-9a-f]{64}$")
                response = authority.response_contract
                self.assertGreater(response.expected_actual_shell_rank, 0)
                self.assertGreater(response.expected_matched_shell_rank, 0)
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
            ("expected_matched_shell_rank", original.response_contract.expected_matched_shell_rank + 1),
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
                        current_scenario_response_contract_v2_payload(
                            changed_response
                        )
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

    def test_complete_registry_gate_rejects_missing_duplicate_and_extra(self) -> None:
        from rulespace_v3.parent_freeze_v2 import (
            _require_complete_block_success_registry,
        )

        with self.assertRaisesRegex(ValueError, "missing"):
            _require_complete_block_success_registry(self.modified)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            _require_complete_block_success_registry(
                (*self.modified, self.modified[0])
            )
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
            "rulespace_v3/application_recipes.py",
            "rulespace_v3/c05_projector_recipe.py",
            "rulespace_v3/geometry_application_recipes.py",
            "rulespace_v3/evidence.py",
            "rulespace_v3/factory.py",
            "rulespace_v3/geometry.py",
            "rulespace_v3/response.py",
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

    def test_draft_and_uninjected_finalization_inputs_make_issuance_impossible(self) -> None:
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
        self.assertEqual(len(inspect.signature(issue_v3m0_parent_freeze_v2).parameters), 0)
        with self.assertRaises(ParentV2IssuanceBlocked) as caught:
            issue_v3m0_parent_freeze_v2()
        joined = " | ".join(caught.exception.reasons)
        self.assertIn("SIGNED", joined)
        self.assertRegex(joined, r"\d+ BLOCK_SUCCESS")

    def test_current_facade_rejects_v1_candidate_forgery_and_subclass(self) -> None:
        from rulespace_v3.parent_authority import (
            VerifiedParentFreezeV2,
            require_current_parent,
        )
        from rulespace_v3.parent_candidate_v2 import (
            build_v3m0_parent_freeze_candidate_v2,
        )
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze

        for foreign in (
            issue_v3m0_parent_freeze(),
            build_v3m0_parent_freeze_candidate_v2(),
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
