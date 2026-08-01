"""Production Task-11 six-order numerical replay tests."""

from __future__ import annotations

import inspect
import unittest
from dataclasses import dataclass, replace
from types import FunctionType


_redirect_window_payload = None
_redirect_parent_target = None


def _redirect_window_replayer_template(_value):
    return _redirect_window_payload


def _redirect_parent_resolver_template(_replay):
    return _redirect_parent_target


def _redirect_numerical_executor_template(
    parent,
    replay,
    registry,
    protocol,
):
    return parent, replay, registry, protocol


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
        from rulespace_v3.response import (
            _exact_dataclass_tree,
            _preflight_response_evidence_body,
        )
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
        runtime = issue_runtime_evidence_manifest()
        _exact_dataclass_tree(runtime, "runtime")
        _preflight_response_evidence_body(runtime, "runtime")

        injected = PlainRecord(1)
        object.__setattr__(injected, "caller_extra", 2)
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            _exact_dataclass_tree(injected, "plain")
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            _preflight_response_evidence_body(injected, "plain")

        incomplete = object.__new__(SlottedRecord)
        with self.assertRaisesRegex(ValueError, "missing field"):
            _exact_dataclass_tree(incomplete, "slotted")
        with self.assertRaisesRegex(ValueError, "missing field"):
            _preflight_response_evidence_body(incomplete, "slotted")

    def test_runner_has_closed_current_replay_boundary(self) -> None:
        from rulespace_v3.current_window_replay import (
            VerifiedCurrentWindowCalibrationProtocolV2,
        )
        from rulespace_v3.task11_runner import run_task11_window_calibration

        self.assertEqual(
            tuple(inspect.signature(run_task11_window_calibration).parameters),
            ("current_window",),
        )
        with self.assertRaises(TypeError):
            run_task11_window_calibration(object())
        forged = object.__new__(VerifiedCurrentWindowCalibrationProtocolV2)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            run_task11_window_calibration(forged)

    def test_public_runner_freezes_canonical_replay_against_module_redirects(
        self,
    ) -> None:
        from rulespace_v3.task11_runner import _make_public_task11_runner

        @dataclass(frozen=True)
        class EqualReplay:
            value: str

        class FakeLiveWindow:
            pass

        live_window = FakeLiveWindow()
        protocol = object()
        registry = object()
        canonical_replay = EqualReplay("same-body")
        fresh_value_equal_replay = EqualReplay("same-body")
        historical_parent = object()
        redirected_parent = object()
        self.assertEqual(fresh_value_equal_replay, canonical_replay)
        self.assertIsNot(fresh_value_equal_replay, canonical_replay)

        redirect_globals = {
            "__builtins__": {},
            "__name__": "rulespace_v3._task11_redirect_probe",
            "_redirect_window_payload": (
                protocol,
                registry,
                canonical_replay,
            ),
            "_redirect_parent_target": historical_parent,
        }
        window_replayer = FunctionType(
            _redirect_window_replayer_template.__code__,
            redirect_globals,
        )
        parent_resolver = FunctionType(
            _redirect_parent_resolver_template.__code__,
            redirect_globals,
        )
        numerical_executor = FunctionType(
            _redirect_numerical_executor_template.__code__,
            redirect_globals,
        )
        runner = _make_public_task11_runner(
            window_type=FakeLiveWindow,
            window_replayer=window_replayer,
            parent_resolver=parent_resolver,
            numerical_executor=numerical_executor,
        )

        redirect_globals["_redirect_window_payload"] = (
            protocol,
            registry,
            fresh_value_equal_replay,
        )
        redirect_globals["_redirect_parent_target"] = redirected_parent
        result = runner(live_window)

        self.assertIs(result[0], historical_parent)
        self.assertIs(result[1], canonical_replay)
        self.assertIsNot(result[0], redirected_parent)
        self.assertIsNot(result[1], fresh_value_equal_replay)
        with self.assertRaises(TypeError):
            runner(object())

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
            matched_ablation_outcomes=tuple(reversed(replay.matched_ablation_outcomes)),
        )
        with self.assertRaises((TypeError, ValueError)):
            _build_task11_numerical_roots(
                parent,
                spliced,
                current_registry,
                current_window,
            )

    def test_task8_private_helper_has_exact_authority_neutral_boundary(
        self,
    ) -> None:
        from rulespace_v3.parent_freeze import VerifiedParentFreeze
        from rulespace_v3.task11_runner import (
            _run_task11_window_calibration_from_task8_replay,
        )
        from rulespace_v3.task8_control_replay import CurrentTask8ControlReplay

        self.assertEqual(
            tuple(
                inspect.signature(
                    _run_task11_window_calibration_from_task8_replay
                ).parameters
            ),
            ("historical_parent", "task8_replay"),
        )
        parent, replay, _, _ = self._current_inputs()
        with self.assertRaises(TypeError):
            _run_task11_window_calibration_from_task8_replay(object(), replay)
        with self.assertRaises(TypeError):
            _run_task11_window_calibration_from_task8_replay(parent, object())
        forged_parent = object.__new__(VerifiedParentFreeze)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            _run_task11_window_calibration_from_task8_replay(
                forged_parent,
                replay,
            )
        forged_replay = object.__new__(CurrentTask8ControlReplay)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            _run_task11_window_calibration_from_task8_replay(
                parent,
                forged_replay,
            )

    def test_task8_and_current_v2_routes_share_one_numerical_core(self) -> None:
        from rulespace_v3.task11_runner import (
            _run_task11_window_calibration_core,
            _run_task11_window_calibration_from_current_v2_replay,
            _run_task11_window_calibration_from_replay,
            _run_task11_window_calibration_from_task8_replay,
        )

        core_name = _run_task11_window_calibration_core.__name__
        self.assertIn(
            core_name,
            _run_task11_window_calibration_from_task8_replay.__code__.co_names,
        )
        self.assertIn(
            core_name,
            _run_task11_window_calibration_from_current_v2_replay.__code__.co_names,
        )
        self.assertEqual(
            tuple(
                inspect.signature(_run_task11_window_calibration_from_replay).parameters
            ),
            ("parent", "task8_replay", "current_registry", "current_window"),
        )
        self.assertIn(
            "_run_task11_window_calibration_from_current_v2_replay",
            _run_task11_window_calibration_from_replay.__code__.co_names,
        )

    def test_raw_task8_replay_retains_six_orders_and_independent_2t(
        self,
    ) -> None:
        from rulespace_v3.calibration_authority import WindowCalibrationOutcome
        from rulespace_v3.contracts import UndefinedReason
        from rulespace_v3.task11_runner import (
            _run_task11_window_calibration_from_task8_replay,
        )
        from rulespace_v3.thresholds import T_CANDIDATES

        parent, replay, _, _ = self._current_inputs()
        outcome = _run_task11_window_calibration_from_task8_replay(
            historical_parent=parent,
            task8_replay=replay,
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
            (item for item in outcome.manifest.candidate_audits if item.passed),
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
