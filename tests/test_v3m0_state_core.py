from __future__ import annotations

import unittest

from rulespace_v3.contracts import (
    BlockStatus,
    RequiredBlockReport,
    UndefinedReason,
)
from rulespace_v3.state import V3M0State, resolve_v3m0_state


def _report(*undefined):
    return RequiredBlockReport(
        status=(
            BlockStatus(False, undefined[0][1])
            if undefined
            else BlockStatus(True, None)
        ),
        undefined=tuple(undefined),
    )


class V3M0StateCoreTests(unittest.TestCase):
    def decide(self, **overrides):
        inputs = {
            "formal_all_pass": True,
            "exact_all_pass": True,
            "identifiability_all_pass": True,
            "required_blocks": _report(),
            "all_required_controls_pass": True,
            "representation_invariants_pass": True,
            "no_physical_anchor_run": True,
        }
        inputs.update(overrides)
        return resolve_v3m0_state(**inputs)

    def test_only_complete_scope_clean_evidence_reaches_ready(self):
        result = self.decide()

        self.assertEqual(
            result.state,
            V3M0State.READY_V3_M1_ANCHOR_CERTIFICATION,
        )
        self.assertTrue(result.ready)
        self.assertIsNone(result.first_undefined)

    def test_formal_and_identifiability_failures_have_ordered_halts(self):
        self.assertEqual(
            self.decide(formal_all_pass=False).state,
            V3M0State.HALT_FORMAL,
        )
        self.assertEqual(
            self.decide(exact_all_pass=False).state,
            V3M0State.HALT_FORMAL,
        )
        self.assertEqual(
            self.decide(identifiability_all_pass=False).state,
            V3M0State.HALT_IDENTIFIABILITY,
        )

    def test_window_halt_has_one_and_only_one_undefined_reason(self):
        window = self.decide(
            required_blocks=_report(
                ("window", UndefinedReason.WINDOW_UNRESOLVED),
            )
        )
        endpoint = self.decide(
            required_blocks=_report(
                ("shell", UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS),
            )
        )

        self.assertEqual(window.state, V3M0State.HALT_WINDOW)
        self.assertEqual(endpoint.state, V3M0State.HALT_CONTROL)

    def test_any_control_invariant_or_scope_violation_halts_control(self):
        for overrides in (
            {"all_required_controls_pass": False},
            {"representation_invariants_pass": False},
            {"no_physical_anchor_run": False},
        ):
            with self.subTest(overrides=overrides):
                self.assertEqual(
                    self.decide(**overrides).state,
                    V3M0State.HALT_CONTROL,
                )

    def test_inputs_are_exact_and_report_body_is_preserved(self):
        report = _report(
            ("a", UndefinedReason.RESPONSE_NULL),
            ("b", UndefinedReason.UNSTABLE),
        )
        result = self.decide(required_blocks=report)

        self.assertEqual(
            result.first_undefined,
            ("a", UndefinedReason.RESPONSE_NULL),
        )
        self.assertEqual(result.undefined, report.undefined)
        with self.assertRaises(TypeError):
            self.decide(formal_all_pass=1)


if __name__ == "__main__":
    unittest.main()
