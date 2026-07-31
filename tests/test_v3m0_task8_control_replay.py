"""Current-Parent Task-8 control-root replay contracts."""

from __future__ import annotations

from dataclasses import replace
import unittest


class CurrentTask8ControlReplayTests(unittest.TestCase):
    @staticmethod
    def _inputs():
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
        from rulespace_v3.parent_freeze_v2 import (
            _build_reviewed_unchanged_scenario_authorities,
        )

        parent = issue_v3m0_parent_freeze()
        authorities = tuple(
            item
            for item in _build_reviewed_unchanged_scenario_authorities()
            if item.control_case_id
            in {
                "C01_BLIND_HOLDOUT_FULL",
                "C02_CONDITIONED_ZERO",
                "C03_EQUAL_RANK_DIRECT_SUM",
            }
        )
        return parent, authorities

    def test_replay_reconstructs_three_exact_current_control_roots(self) -> None:
        from rulespace_v3.task8_control_replay import (
            _replay_current_task8_control_roots,
        )

        parent, authorities = self._inputs()
        replay = _replay_current_task8_control_roots(parent, authorities)

        self.assertEqual(
            tuple(item.control_case_id for item in replay.case_replays),
            (
                "C01_BLIND_HOLDOUT_FULL",
                "C02_CONDITIONED_ZERO",
                "C03_EQUAL_RANK_DIRECT_SUM",
            ),
        )
        self.assertEqual(
            tuple(item.control_id for item in replay.case_replays),
            ("full", "zero", "direct_sum"),
        )
        self.assertEqual(
            tuple(item.actual_step_count for item in replay.case_replays),
            (3, 3, 6),
        )
        self.assertEqual(
            tuple(item.matched_ablated_step_count for item in replay.case_replays),
            (3, 0, 3),
        )
        self.assertEqual(
            tuple(item.expected_actual_shell_rank for item in replay.case_replays),
            (1, 1, 2),
        )
        self.assertEqual(
            tuple(item.expected_matched_shell_rank for item in replay.case_replays),
            (1, 0, 1),
        )
        self.assertEqual(
            replay.legacy_registry.registry.parent_freeze_sha,
            parent.manifest.parent_freeze_sha,
        )
        self.assertEqual(len(replay.controls), 3)
        self.assertEqual(len(replay.matched_ablation_outcomes), 3)

    def test_replay_rejects_order_splice_and_resigned_contract(self) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_v2_contracts import (
            current_scenario_authority_v2_payload,
            current_scenario_response_contract_v2_payload,
        )
        from rulespace_v3.task8_control_replay import (
            _replay_current_task8_control_roots,
        )

        parent, authorities = self._inputs()
        with self.assertRaisesRegex(ValueError, "order|C01|canonical"):
            _replay_current_task8_control_roots(
                parent,
                tuple(reversed(authorities)),
            )

        first = authorities[0]
        changed_response0 = replace(
            first.response_contract,
            expected_actual_shell_rank=2,
            response_contract_sha="0" * 64,
        )
        changed_response = replace(
            changed_response0,
            response_contract_sha=canonical_sha(
                current_scenario_response_contract_v2_payload(
                    changed_response0
                )
            ),
        )
        changed0 = replace(
            first,
            response_contract=changed_response,
            scenario_authority_sha="0" * 64,
        )
        changed = replace(
            changed0,
            scenario_authority_sha=canonical_sha(
                current_scenario_authority_v2_payload(changed0)
            ),
        )
        with self.assertRaises(ValueError):
            _replay_current_task8_control_roots(
                parent,
                (changed,) + authorities[1:],
            )


if __name__ == "__main__":
    unittest.main()
