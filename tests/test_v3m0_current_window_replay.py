"""Current-Parent Task-11 window replay envelope tests."""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
import unittest


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


if __name__ == "__main__":
    unittest.main()
