"""Production Task-11 six-order numerical replay tests."""

from __future__ import annotations

import inspect
import unittest
from dataclasses import dataclass, replace


class Task11RunnerContractTests(unittest.TestCase):
    @classmethod
    def _current_inputs(cls):
        cached = getattr(cls, "_cached_current_inputs", None)
        if cached is not None:
            return cached
        from rulespace_v3.current_window_replay import (
            _build_current_window_calibration_protocol_v2_body,
        )
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
        from rulespace_v3.parent_freeze_v2 import (
            _build_reviewed_unchanged_scenario_authorities,
        )
        from rulespace_v3.task8_control_replay import (
            _build_current_control_registry_v2_body,
            _replay_current_task8_control_roots,
        )

        parent = issue_v3m0_parent_freeze()
        authorities = tuple(
            item
            for item in _build_reviewed_unchanged_scenario_authorities()
            if item.control_case_id.startswith(("C01_", "C02_", "C03_"))
        )
        replay = _replay_current_task8_control_roots(parent, authorities)
        current_registry = _build_current_control_registry_v2_body(
            "a" * 64,
            replay,
        )
        current_window = _build_current_window_calibration_protocol_v2_body(
            current_registry,
            replay,
        )
        result = (parent, replay, current_registry, current_window)
        cls._cached_current_inputs = result
        return result

    def test_response_exact_tree_accepts_plain_and_slotted_dataclasses(self) -> None:
        from rulespace_v3.response import _exact_dataclass_tree
        from rulespace_v3.runtime import issue_runtime_evidence_manifest

        @dataclass(frozen=True)
        class PlainRecord:
            value: int

        @dataclass(frozen=True)
        class SlottedRecord:
            __slots__ = ("value",)

            value: int

        _exact_dataclass_tree(PlainRecord(1), "plain")
        _exact_dataclass_tree(SlottedRecord(1), "slotted")
        _exact_dataclass_tree(issue_runtime_evidence_manifest(), "runtime")

        injected = PlainRecord(1)
        object.__setattr__(injected, "caller_extra", 2)
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            _exact_dataclass_tree(injected, "plain")

        incomplete = object.__new__(SlottedRecord)
        with self.assertRaisesRegex(ValueError, "missing field"):
            _exact_dataclass_tree(incomplete, "slotted")

    def test_runner_has_closed_current_replay_boundary(self) -> None:
        from rulespace_v3.task11_runner import run_task11_window_calibration

        self.assertEqual(
            tuple(inspect.signature(run_task11_window_calibration).parameters),
            (
                "parent",
                "task8_replay",
                "current_registry",
                "current_window",
            ),
        )
        with self.assertRaises(TypeError):
            run_task11_window_calibration(
                object(),
                object(),
                object(),
                object(),
            )

    def test_numerical_registry_rebinds_only_canonical_pair_actual_identities(
        self,
    ) -> None:
        from rulespace_v3.registry import _reverify_verified_control_registry
        from rulespace_v3.task11_runner import _build_task11_numerical_roots

        parent, replay, current_registry, current_window = self._current_inputs()

        registry, protocol = _build_task11_numerical_roots(
            parent,
            replay,
            current_registry,
            current_window,
        )
        registry_view = _reverify_verified_control_registry(registry)
        self.assertEqual(registry.registry, replay.legacy_registry.registry)
        self.assertEqual(
            protocol.protocol,
            current_window.legacy_window_protocol,
        )
        for control, construction in zip(
            registry_view.controls,
            replay.matched_ablation_outcomes,
        ):
            self.assertIsNotNone(construction.pair)
            assert construction.pair is not None
            self.assertIs(control.factory, construction.pair.actual)

        spliced = replace(
            replay,
            matched_ablation_outcomes=tuple(
                reversed(replay.matched_ablation_outcomes)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            _build_task11_numerical_roots(
                parent,
                spliced,
                current_registry,
                current_window,
            )

    def test_real_replay_retains_six_orders_three_controls_and_independent_2t(
        self,
    ) -> None:
        from rulespace_v3.calibration_authority import WindowCalibrationOutcome
        from rulespace_v3.contracts import UndefinedReason
        from rulespace_v3.task11_runner import run_task11_window_calibration
        from rulespace_v3.thresholds import T_CANDIDATES

        parent, replay, current_registry, current_window = self._current_inputs()
        outcome = run_task11_window_calibration(
            parent,
            replay,
            current_registry,
            current_window,
        )
        self.assertIs(type(outcome), WindowCalibrationOutcome)
        self.assertEqual(
            tuple(item.fejer_order for item in outcome.manifest.candidate_audits),
            T_CANDIDATES,
        )
        for window_audit, order in zip(
            outcome.manifest.candidate_audits,
            T_CANDIDATES,
        ):
            self.assertEqual(len(window_audit.control_audits), 3)
            self.assertEqual(
                tuple(
                    item.control_registry_entry.control_id
                    for item in window_audit.control_audits
                ),
                ("full", "zero", "direct_sum"),
            )
            for control in window_audit.control_audits:
                self.assertEqual(control.candidate_t.run_spec.fejer_order, order)
                self.assertEqual(
                    control.comparison_2t.run_spec.fejer_order,
                    2 * order,
                )
        first_passing = next(
            (
                item
                for item in outcome.manifest.candidate_audits
                if item.passed
            ),
            None,
        )
        if first_passing is None:
            self.assertFalse(outcome.status.defined)
            self.assertIs(outcome.status.reason, UndefinedReason.WINDOW_UNRESOLVED)
            self.assertIsNone(outcome.selection)
        else:
            self.assertTrue(outcome.status.defined)
            self.assertIsNotNone(outcome.selection)
            assert outcome.selection is not None
            self.assertEqual(
                outcome.selection.selected_fejer_order,
                first_passing.fejer_order,
            )


if __name__ == "__main__":
    unittest.main()
