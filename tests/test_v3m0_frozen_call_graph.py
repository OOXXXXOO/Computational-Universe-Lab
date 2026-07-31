"""Adversarial tests for the shared v3 authority call-graph freezer."""

from __future__ import annotations

import unittest
from unittest import mock


class FrozenCallGraphAuthorityTests(unittest.TestCase):
    def test_public_protocol_authority_ignores_freezer_any_rebinding(self) -> None:
        # Assemble the complete public dependency graph before the attack.
        # This mirrors the repository import boundary under audit and avoids
        # making an unrelated lazy import inherit the temporary test binding.
        import rulespace_v3.application_authority_v2  # noqa: F401
        import rulespace_v3.application_materialization_v2  # noqa: F401
        import rulespace_v3.frozen_call_graph as freezer_module
        from rulespace_v3.scenario_response_protocol import (
            VerifiedApplicationScenarioResponseProtocolV2,
            issue_v3m0_scenario_response_protocol,
            verify_v3m0_scenario_response_protocol,
        )

        calls: list[str] = []

        def hostile_any(*args, **kwargs):
            del args, kwargs
            calls.append("any")
            raise AssertionError("shared-freezer module global reached")

        forged = object.__new__(
            VerifiedApplicationScenarioResponseProtocolV2
        )
        with mock.patch.object(
            freezer_module,
            "any",
            hostile_any,
            create=True,
        ):
            with self.assertRaisesRegex(
                TypeError,
                "formal_parent_v2 must be an exact live Parent-v2",
            ):
                issue_v3m0_scenario_response_protocol(
                    object(),
                    object(),
                    object(),
                )
            with self.assertRaisesRegex(
                ValueError,
                "scenario response protocol capability is not live",
            ):
                verify_v3m0_scenario_response_protocol(forged)

        self.assertEqual(calls, [])

    def test_public_replay_properties_ignore_module_builtin_rebinding(self) -> None:
        import rulespace_v3.current_window_replay as current_window_module
        import rulespace_v3.task8_control_replay as task8_module
        from rulespace_v3.current_window_replay import (
            VerifiedCurrentWindowCalibrationProtocolV2,
        )
        from rulespace_v3.task8_control_replay import (
            VerifiedCurrentControlRegistryV2,
        )

        cases = (
            (
                task8_module,
                VerifiedCurrentControlRegistryV2,
                "registry",
                "current control-registry identity is not live",
            ),
            (
                current_window_module,
                VerifiedCurrentWindowCalibrationProtocolV2,
                "protocol",
                "current window protocol identity is not live",
            ),
        )
        for module, capability_type, attribute, expected_error in cases:
            with self.subTest(capability=capability_type.__name__):
                calls: list[str] = []

                def hostile_len(*args, **kwargs):
                    del args, kwargs
                    calls.append("len")
                    return 0

                def hostile_runtime_error(*args, **kwargs):
                    del args, kwargs
                    calls.append("RuntimeError")
                    return AssertionError("property module global reached")

                forged = object.__new__(capability_type)
                with mock.patch.object(
                    module,
                    "len",
                    hostile_len,
                    create=True,
                ), mock.patch.object(
                    module,
                    "RuntimeError",
                    hostile_runtime_error,
                ):
                    with self.assertRaisesRegex(ValueError, expected_error):
                        getattr(forged, attribute)

                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
