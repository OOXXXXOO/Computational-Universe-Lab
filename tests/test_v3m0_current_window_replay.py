"""Current-Parent Task-11 window replay envelope tests."""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
import gc
import unittest
from unittest import mock


class CurrentWindowReplayV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
        from rulespace_v3.parent_freeze_v2 import (
            _build_reviewed_unchanged_scenario_authorities,
        )
        from rulespace_v3.task8_control_replay import (
            _build_current_control_registry_v2_body,
            _replay_current_task8_control_roots,
        )

        cls.parent = issue_v3m0_parent_freeze()
        authorities = tuple(
            item
            for item in _build_reviewed_unchanged_scenario_authorities()
            if item.control_case_id.startswith(("C01_", "C02_", "C03_"))
        )
        cls.replay = _replay_current_task8_control_roots(
            cls.parent,
            authorities,
        )
        cls.parent_v2_sha = "a" * 64
        cls.registry = _build_current_control_registry_v2_body(
            cls.parent_v2_sha,
            cls.replay,
        )

    def test_window_protocol_binds_current_and_legacy_roots(self) -> None:
        from rulespace_v3.current_window_replay import (
            CURRENT_WINDOW_CALIBRATION_PROTOCOL_V2_SCHEMA_VERSION,
            _build_current_window_calibration_protocol_v2_body,
            current_window_calibration_protocol_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.thresholds import T_CANDIDATES

        protocol = _build_current_window_calibration_protocol_v2_body(
            self.registry,
            self.replay,
        )
        self.assertEqual(
            protocol.protocol_schema_version,
            CURRENT_WINDOW_CALIBRATION_PROTOCOL_V2_SCHEMA_VERSION,
        )
        self.assertEqual(protocol.parent_freeze_v2_sha, self.parent_v2_sha)
        self.assertEqual(protocol.t_candidates, T_CANDIDATES)
        self.assertEqual(
            protocol.current_control_registry.registry_sha,
            self.registry.registry_sha,
        )
        self.assertEqual(
            protocol.legacy_window_protocol.parent_freeze_sha,
            self.parent.manifest.parent_freeze_sha,
        )
        self.assertEqual(
            tuple(item.control_case_id for item in protocol.control_bindings),
            (
                "C01_BLIND_HOLDOUT_FULL",
                "C02_CONDITIONED_ZERO",
                "C03_EQUAL_RANK_DIRECT_SUM",
            ),
        )
        self.assertEqual(
            protocol.protocol_sha,
            canonical_sha(
                current_window_calibration_protocol_v2_payload(protocol)
            ),
        )

    def test_resigned_binding_or_candidate_table_splice_is_rejected(self) -> None:
        from rulespace_v3.current_window_replay import (
            _build_current_window_calibration_protocol_v2_body,
            current_window_calibration_protocol_v2_payload,
            verify_current_window_calibration_protocol_v2_body,
        )
        from rulespace_v3.evidence import canonical_sha

        protocol = _build_current_window_calibration_protocol_v2_body(
            self.registry,
            self.replay,
        )
        def bypass_frozen_constructor(**changes: object) -> object:
            forged = object.__new__(type(protocol))
            for field in dataclass_fields(type(protocol)):
                object.__setattr__(
                    forged,
                    field.name,
                    changes.get(field.name, getattr(protocol, field.name)),
                )
            return forged

        for field, value in (
            ("t_candidates", tuple(reversed(protocol.t_candidates))),
            ("control_bindings", tuple(reversed(protocol.control_bindings))),
        ):
            with self.subTest(field=field):
                changed0 = bypass_frozen_constructor(
                    **{field: value, "protocol_sha": "0" * 64}
                )
                changed = bypass_frozen_constructor(
                    **{
                        field: value,
                        "protocol_sha": canonical_sha(
                            current_window_calibration_protocol_v2_payload(
                                changed0
                            )
                        ),
                    }
                )
                with self.assertRaises((TypeError, ValueError)):
                    verify_current_window_calibration_protocol_v2_body(
                        changed,
                        self.registry,
                        self.replay,
                    )

    def test_live_window_factory_replays_registry_and_requires_live_identity(
        self,
    ) -> None:
        from rulespace_v3.current_window_replay import (
            VerifiedCurrentWindowCalibrationProtocolV2,
            _build_current_window_calibration_protocol_v2_body,
            _make_current_window_calibration_protocol_v2_api,
            verify_current_window_calibration_protocol_v2_body,
        )

        class FakeRegistryCapability:
            pass

        registry_capability = FakeRegistryCapability()
        calls = []

        def replay_registry(value):
            self.assertIs(value, registry_capability)
            calls.append("replay")
            return self.registry, self.replay

        build, require, replay = _make_current_window_calibration_protocol_v2_api(
            registry_type=FakeRegistryCapability,
            registry_replayer=replay_registry,
            body_builder=_build_current_window_calibration_protocol_v2_body,
            body_verifier=verify_current_window_calibration_protocol_v2_body,
        )
        capability = build(registry_capability)
        protocol = require(capability)
        self.assertEqual(protocol.parent_freeze_v2_sha, self.parent_v2_sha)
        replayed_protocol, replayed_registry, replayed_task8 = replay(capability)
        self.assertEqual(replayed_protocol, protocol)
        self.assertEqual(replayed_registry, self.registry)
        self.assertIs(replayed_task8, self.replay)
        self.assertEqual(calls, ["replay", "replay", "replay"])

        forged = object.__new__(VerifiedCurrentWindowCalibrationProtocolV2)
        object.__setattr__(forged, "_protocol_sha", protocol.protocol_sha)
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            require(forged)
        del capability
        gc.collect()
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            require(forged)

    def test_live_window_factory_freezes_body_builder_and_public_gate(self) -> None:
        import rulespace_v3.current_window_replay as current_window
        from rulespace_v3.current_window_replay import (
            VerifiedCurrentWindowCalibrationProtocolV2,
            _build_current_window_calibration_protocol_v2_body,
            _make_current_window_calibration_protocol_v2_api,
            build_current_window_calibration_protocol_v2,
            require_current_window_calibration_protocol_v2,
            verify_current_window_calibration_protocol_v2_body,
        )

        class FakeRegistryCapability:
            pass

        registry_capability = FakeRegistryCapability()
        build, require, _ = _make_current_window_calibration_protocol_v2_api(
            registry_type=FakeRegistryCapability,
            registry_replayer=lambda value: (self.registry, self.replay),
            body_builder=_build_current_window_calibration_protocol_v2_body,
            body_verifier=verify_current_window_calibration_protocol_v2_body,
        )
        with mock.patch.object(
            current_window,
            "_build_current_window_calibration_protocol_v2_body",
            side_effect=AssertionError("module global redirect reached"),
        ):
            capability = build(registry_capability)
            self.assertEqual(
                require(capability).parent_freeze_v2_sha,
                self.parent_v2_sha,
            )

        with self.assertRaises(TypeError):
            build_current_window_calibration_protocol_v2(object())
        forged = object.__new__(VerifiedCurrentWindowCalibrationProtocolV2)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            require_current_window_calibration_protocol_v2(forged)

    def test_shared_call_graph_freezer_closes_window_builder_globals(self) -> None:
        import rulespace_v3.current_window_replay as current_window
        from rulespace_v3.current_window_replay import (
            _build_current_window_calibration_protocol_v2_body,
        )
        from rulespace_v3.frozen_call_graph import freeze_rulespace_call_graph

        frozen_builder = freeze_rulespace_call_graph(
            _build_current_window_calibration_protocol_v2_body
        )
        with mock.patch.object(
            current_window,
            "canonical_sha",
            side_effect=AssertionError("module canonical hash redirect reached"),
        ):
            protocol = frozen_builder(self.registry, self.replay)
        self.assertEqual(protocol.parent_freeze_v2_sha, self.parent_v2_sha)

    def test_shared_call_graph_freezer_rejects_window_class_behavior_drift(
        self,
    ) -> None:
        from rulespace_v3.current_window_replay import (
            CurrentWindowControlBindingV2,
            _build_current_window_calibration_protocol_v2_body,
        )
        from rulespace_v3.frozen_call_graph import freeze_rulespace_call_graph

        frozen_builder = freeze_rulespace_call_graph(
            _build_current_window_calibration_protocol_v2_body
        )
        with mock.patch.object(
            CurrentWindowControlBindingV2,
            "__post_init__",
            return_value=None,
        ):
            with self.assertRaisesRegex(RuntimeError, "class dependency drifted"):
                frozen_builder(self.registry, self.replay)


if __name__ == "__main__":
    unittest.main()
