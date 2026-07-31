"""Current-Parent Task-8 control-root replay contracts."""

from __future__ import annotations

from dataclasses import replace
import gc
import inspect
import unittest
from unittest import mock


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

    def test_current_registry_body_binds_parent_and_every_replayed_root(self) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.task8_control_replay import (
            CURRENT_CONTROL_REGISTRY_V2_SCHEMA_VERSION,
            _build_current_control_registry_v2_body,
            current_control_registry_v2_payload,
        )

        parent, authorities = self._inputs()
        from rulespace_v3.task8_control_replay import (
            _replay_current_task8_control_roots,
        )

        replay = _replay_current_task8_control_roots(parent, authorities)
        parent_v2_sha = "a" * 64
        registry = _build_current_control_registry_v2_body(
            parent_v2_sha,
            replay,
        )

        self.assertEqual(
            registry.registry_schema_version,
            CURRENT_CONTROL_REGISTRY_V2_SCHEMA_VERSION,
        )
        self.assertEqual(registry.parent_freeze_v2_sha, parent_v2_sha)
        self.assertEqual(
            registry.historical_parent_v1_sha,
            parent.manifest.parent_freeze_sha,
        )
        self.assertEqual(
            tuple(item.control_case_id for item in registry.entries),
            tuple(item.control_case_id for item in replay.case_replays),
        )
        self.assertEqual(
            tuple(item.scenario_authority_sha for item in registry.entries),
            tuple(item.scenario_authority_sha for item in replay.case_replays),
        )
        self.assertEqual(
            registry.registry_sha,
            canonical_sha(current_control_registry_v2_payload(registry)),
        )

    def test_current_registry_rejects_replay_body_and_parent_splices(self) -> None:
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.task8_control_replay import (
            _build_current_control_registry_v2_body,
            current_control_registry_v2_payload,
            verify_current_control_registry_v2_body,
        )

        parent, authorities = self._inputs()
        from rulespace_v3.task8_control_replay import (
            _replay_current_task8_control_roots,
        )

        replay = _replay_current_task8_control_roots(parent, authorities)
        registry = _build_current_control_registry_v2_body("a" * 64, replay)
        first = registry.entries[0]
        changed_entry0 = replace(
            first,
            actual_program_sha="b" * 64,
            entry_sha="0" * 64,
        )
        from rulespace_v3.task8_control_replay import (
            current_control_registry_entry_v2_payload,
        )

        changed_entry = replace(
            changed_entry0,
            entry_sha=canonical_sha(
                current_control_registry_entry_v2_payload(changed_entry0)
            ),
        )
        changed0 = replace(
            registry,
            entries=(changed_entry,) + registry.entries[1:],
            registry_sha="0" * 64,
        )
        changed = replace(
            changed0,
            registry_sha=canonical_sha(
                current_control_registry_v2_payload(changed0)
            ),
        )
        with self.assertRaises(ValueError):
            verify_current_control_registry_v2_body(
                changed,
                "a" * 64,
                replay,
            )
        with self.assertRaises(ValueError):
            verify_current_control_registry_v2_body(
                registry,
                "b" * 64,
                replay,
            )

    def test_public_current_registry_accepts_only_live_current_parent(self) -> None:
        import rulespace_v3.task8_control_replay as task8
        from rulespace_v3.task8_control_replay import (
            VerifiedCurrentControlRegistryV2,
            build_current_control_registry_v2,
            require_current_control_registry_v2,
        )

        self.assertEqual(
            tuple(inspect.signature(build_current_control_registry_v2).parameters),
            ("parent_v2",),
        )
        with mock.patch.object(
            task8,
            "_replay_current_task8_control_roots",
            side_effect=AssertionError("numerical replay ran before Parent gate"),
        ) as replay:
            with self.assertRaises(TypeError):
                build_current_control_registry_v2(object())
        replay.assert_not_called()

        with self.assertRaises(TypeError):
            VerifiedCurrentControlRegistryV2()  # type: ignore[call-arg]
        forged = object.__new__(VerifiedCurrentControlRegistryV2)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            require_current_control_registry_v2(forged)

    def test_registry_capability_factory_replays_and_requires_live_identity(self) -> None:
        from rulespace_v3.task8_control_replay import (
            VerifiedCurrentControlRegistryV2,
            _build_current_control_registry_v2_body,
            _make_current_control_registry_v2_api,
            _replay_current_task8_control_roots,
            verify_current_control_registry_v2_body,
        )

        parent, authorities = self._inputs()
        replay = _replay_current_task8_control_roots(parent, authorities)

        class FakeCurrentParent:
            pass

        fake_parent = FakeCurrentParent()
        manifest = type(
            "Manifest",
            (),
            {"parent_freeze_v2_sha": "a" * 64},
        )()
        calls = []

        def replayer(observed_parent, observed_manifest):
            self.assertIs(observed_parent, fake_parent)
            self.assertIs(observed_manifest, manifest)
            calls.append("replay")
            return replay

        build, require, replay_capability = _make_current_control_registry_v2_api(
            parent_type=FakeCurrentParent,
            parent_reverifier=lambda value: manifest
            if value is fake_parent
            else self.fail("wrong parent identity"),
            replay_builder=replayer,
            body_builder=_build_current_control_registry_v2_body,
            body_verifier=verify_current_control_registry_v2_body,
        )
        capability = build(fake_parent)
        body = require(capability)
        self.assertEqual(body.parent_freeze_v2_sha, "a" * 64)
        replayed_body, replayed_graph = replay_capability(capability)
        self.assertEqual(replayed_body, body)
        self.assertIs(replayed_graph, replay)
        self.assertEqual(calls, ["replay", "replay", "replay"])

        forged = object.__new__(VerifiedCurrentControlRegistryV2)
        object.__setattr__(forged, "_registry_sha", body.registry_sha)
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            require(forged)

        del capability
        gc.collect()
        replacement = object.__new__(VerifiedCurrentControlRegistryV2)
        object.__setattr__(replacement, "_registry_sha", body.registry_sha)
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            require(replacement)

    def test_registry_capability_factory_freezes_replay_dependencies(self) -> None:
        import rulespace_v3.task8_control_replay as task8
        from rulespace_v3.task8_control_replay import (
            _build_current_control_registry_v2_body,
            _make_current_control_registry_v2_api,
            _replay_current_task8_control_roots,
            verify_current_control_registry_v2_body,
        )

        parent, authorities = self._inputs()
        replay = _replay_current_task8_control_roots(parent, authorities)

        class FakeCurrentParent:
            pass

        fake_parent = FakeCurrentParent()
        manifest = type(
            "Manifest",
            (),
            {"parent_freeze_v2_sha": "b" * 64},
        )()
        build, require, _ = _make_current_control_registry_v2_api(
            parent_type=FakeCurrentParent,
            parent_reverifier=lambda value: manifest,
            replay_builder=lambda value, observed: replay,
            body_builder=_build_current_control_registry_v2_body,
            body_verifier=verify_current_control_registry_v2_body,
        )
        with mock.patch.object(
            task8,
            "_build_current_control_registry_v2_body",
            side_effect=AssertionError("module global redirect reached"),
        ):
            capability = build(fake_parent)
            self.assertEqual(require(capability).parent_freeze_v2_sha, "b" * 64)

    def test_shared_call_graph_freezer_closes_builder_module_globals(self) -> None:
        import rulespace_v3.task8_control_replay as task8
        from rulespace_v3.frozen_call_graph import freeze_rulespace_call_graph
        from rulespace_v3.task8_control_replay import (
            _build_current_control_registry_v2_body,
            _replay_current_task8_control_roots,
        )

        parent, authorities = self._inputs()
        replay = _replay_current_task8_control_roots(parent, authorities)
        frozen_builder = freeze_rulespace_call_graph(
            _build_current_control_registry_v2_body
        )
        with mock.patch.object(
            task8,
            "_sha",
            side_effect=AssertionError("module SHA validator redirect reached"),
        ):
            body = frozen_builder("c" * 64, replay)
        self.assertEqual(body.parent_freeze_v2_sha, "c" * 64)

    def test_shared_call_graph_freezer_rejects_class_behavior_drift(self) -> None:
        from rulespace_v3.frozen_call_graph import freeze_rulespace_call_graph
        from rulespace_v3.task8_control_replay import (
            CurrentControlRegistryEntryV2,
            _build_current_control_registry_v2_body,
            _replay_current_task8_control_roots,
        )

        parent, authorities = self._inputs()
        replay = _replay_current_task8_control_roots(parent, authorities)
        frozen_builder = freeze_rulespace_call_graph(
            _build_current_control_registry_v2_body
        )
        self.assertFalse(hasattr(frozen_builder, "__wrapped__"))
        with mock.patch.object(
            CurrentControlRegistryEntryV2,
            "__post_init__",
            return_value=None,
        ):
            with self.assertRaisesRegex(RuntimeError, "class dependency drifted"):
                frozen_builder("d" * 64, replay)
        with mock.patch.object(
            CurrentControlRegistryEntryV2,
            "unexpected_runtime_hook",
            object(),
            create=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "class dependency drifted"):
                frozen_builder("d" * 64, replay)

        closure_type = CurrentControlRegistryEntryV2

        def closure_root():
            return closure_type

        frozen_closure_root = freeze_rulespace_call_graph(closure_root)
        with mock.patch.object(
            CurrentControlRegistryEntryV2,
            "__post_init__",
            return_value=None,
        ):
            with self.assertRaisesRegex(RuntimeError, "class dependency drifted"):
                frozen_closure_root()


if __name__ == "__main__":
    unittest.main()
