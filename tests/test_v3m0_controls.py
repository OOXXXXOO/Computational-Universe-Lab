from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from rulespace_v3.contracts import BlockStatus, UndefinedReason
from rulespace_v3.evidence import (
    FINAL_RESULT_EVIDENCE_FIELDS,
    canonical_sha,
)
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.series_control import (
    issue_v3m0_deterministic_series_control_outcomes,
)
from rulespace_v3.state import V3M0State

from experiments.v3m0_controls import (
    ANALYSIS_CONTROL_IDS,
    ANALYSIS_CONTROL_SCENARIO_IDS,
    APPLICATION_CONTROL_IDS,
    APPLICATION_PERMIT_CONTROL_IDS,
    APPLICATION_SCENARIO_IDS,
    BLOCK_SUCCESS_CONTROL_IDS,
    BLOCK_SUCCESS_SCENARIO_IDS,
    CONTROL_IDS,
    EXPECTED_TERMINATION_STAGES,
    EXPECTED_TYPED_TERMINATION_CONTROL_IDS,
    EXPECTED_TYPED_TERMINATION_MANIFEST,
    EXPECTED_TYPED_TERMINATION_SCENARIO_IDS,
    REPRESENTATION_INVARIANT_IDS,
    SCENARIO_IDS,
    SCENARIO_LANE_MANIFEST,
    SELECTED_BLOCK_SUCCESS_SCENARIO_IDS,
    SELECTED_CONTROL_IDS,
    V3M0AuditResult,
    V3M0CapabilityBundle,
    assemble_v3m0_controls,
    control_assembly_to_wire,
)
from experiments.v3m0_preflight import (
    DEFAULT_PHASE0,
    build_current_checkpoint,
    write_preflight_outputs,
)


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_CONTROL_IDS = (
    "C01_BLIND_HOLDOUT_FULL",
    "C02_CONDITIONED_ZERO",
    "C03_EQUAL_RANK_DIRECT_SUM",
    "C04_CANONICAL_ANGLE_025_075",
    "C05_PHASE_AND_SCALAR_GAIN",
    "C06_INTERNAL_NONSCALE_MIXING",
    "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
    "C08_RANK_R_MISSING_MODES",
    "C09_PURE_GAUGE_DRESSING",
    "C10_FULL_SOURCE_EXTRA_MODE",
    "C11_NULL_GREY_SIGNAL_AMPLITUDE",
    "C12_NU_INC_IR_NORMALIZATION",
    "C13_BOTH_ZERO_UNDEFINED",
    "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL",
    "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
    "C16_COVERAGE_025_075",
    "C17_QUOTIENT_GAUGE_COVERAGE",
    "C18_ABLATED_INDEPENDENT_UNARY",
    "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
    "C20_DM26_CLEAN_ZERO_TRUE_FLOOR",
)
EXPECTED_INVARIANT_IDS = (
    "I01_LAYER_SPLIT_MERGE",
    "I02_INSERT_S_SINV",
    "I03_COMMUTING_LAYER_REORDER",
    "I04_Q_LABEL_PERMUTATION",
    "I05_SOURCE_ISOMETRY",
    "I06_READOUT_ISOMETRY",
    "I07_PHASE_NONZERO_SCALAR",
    "I08_COVARIANT_CANONICAL_CHANGE",
    "I09_NO_WRAP_VOLUME_CHANGE",
)


def _passing_audit(audit_id: str) -> V3M0AuditResult:
    return V3M0AuditResult(
        audit_id=audit_id,
        status=BlockStatus(True, None),
        passed=True,
        raw_spectra=(("survival", (1.0,)),),
        margins=(("prediction_margin", 0.25),),
    )


class V3M0ControlInventoryTests(unittest.TestCase):
    def test_twenty_controls_and_nine_invariants_are_exact_and_ordered(self) -> None:
        self.assertEqual(CONTROL_IDS, EXPECTED_CONTROL_IDS)
        self.assertEqual(REPRESENTATION_INVARIANT_IDS, EXPECTED_INVARIANT_IDS)
        self.assertEqual(len(CONTROL_IDS), 20)
        self.assertEqual(len(set(CONTROL_IDS)), 20)
        self.assertEqual(len(REPRESENTATION_INVARIANT_IDS), 9)
        self.assertEqual(len(set(REPRESENTATION_INVARIANT_IDS)), 9)
        self.assertEqual(SELECTED_CONTROL_IDS, CONTROL_IDS[:3])
        self.assertEqual(APPLICATION_CONTROL_IDS, CONTROL_IDS[3:])
        self.assertEqual(APPLICATION_PERMIT_CONTROL_IDS, CONTROL_IDS[3:19])
        self.assertEqual(
            EXPECTED_TYPED_TERMINATION_CONTROL_IDS,
            (CONTROL_IDS[10], CONTROL_IDS[12], CONTROL_IDS[13]),
        )
        self.assertEqual(ANALYSIS_CONTROL_IDS, (CONTROL_IDS[19],))
        self.assertEqual(
            BLOCK_SUCCESS_CONTROL_IDS,
            (*CONTROL_IDS[:12], *CONTROL_IDS[14:19]),
        )
        self.assertIn(CONTROL_IDS[10], BLOCK_SUCCESS_CONTROL_IDS)
        self.assertIn(
            CONTROL_IDS[10],
            EXPECTED_TYPED_TERMINATION_CONTROL_IDS,
        )
        self.assertEqual(
            EXPECTED_TERMINATION_STAGES,
            ("activation", "trace", "stability", "endpoint_shell", "success"),
        )
        self.assertEqual(len(SCENARIO_LANE_MANIFEST), 31)
        self.assertEqual(len(SCENARIO_IDS), 31)
        self.assertEqual(len(set(SCENARIO_IDS)), 31)
        self.assertEqual(len(BLOCK_SUCCESS_SCENARIO_IDS), 22)
        self.assertEqual(len(EXPECTED_TYPED_TERMINATION_SCENARIO_IDS), 7)
        self.assertEqual(len(ANALYSIS_CONTROL_SCENARIO_IDS), 2)
        self.assertEqual(
            SELECTED_BLOCK_SUCCESS_SCENARIO_IDS,
            BLOCK_SUCCESS_SCENARIO_IDS[:3],
        )
        self.assertEqual(
            EXPECTED_TYPED_TERMINATION_MANIFEST,
            (
                (
                    CONTROL_IDS[10],
                    (
                        ("null", "activation", UndefinedReason.RESPONSE_NULL),
                        ("grey", "activation", UndefinedReason.RESPONSE_GREY),
                    ),
                ),
                (
                    CONTROL_IDS[12],
                    (
                        (
                            "both-zero",
                            "activation",
                            UndefinedReason.RESPONSE_NULL,
                        ),
                    ),
                ),
                (
                    CONTROL_IDS[13],
                    (
                        (
                            "endpoint-ambiguous",
                            "endpoint_shell",
                            UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS,
                        ),
                        (
                            "response-null",
                            "activation",
                            UndefinedReason.RESPONSE_NULL,
                        ),
                        (
                            "trace-unclassified",
                            "trace",
                            UndefinedReason.TRACE_UNCLASSIFIED,
                        ),
                        ("unstable", "stability", UndefinedReason.UNSTABLE),
                    ),
                ),
            ),
        )

    def test_audit_wire_retains_spectra_margins_and_scenario_identity(self) -> None:
        undefined = V3M0AuditResult(
            audit_id=BLOCK_SUCCESS_SCENARIO_IDS[0],
            status=BlockStatus(False, UndefinedReason.RESPONSE_GREY),
            passed=False,
            raw_spectra=(("activation_amplitude", (0.5,)),),
            margins=(("grey_band_margin", 0.05),),
        )
        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=V3M0CapabilityBundle(),
            control_results=(undefined,),
            invariant_results=(),
            evidence=None,
            no_physical_anchor_run=True,
        )
        wire = control_assembly_to_wire(assembly)
        c01 = wire["BLOCK_SUCCESS"][0]

        self.assertEqual(c01["scenario_id"], BLOCK_SUCCESS_SCENARIO_IDS[0])
        self.assertEqual(c01["control_id"], CONTROL_IDS[0])
        self.assertEqual(c01["undefined_reason"], "window_unresolved")
        self.assertEqual(
            c01["raw_spectra"],
            [{"spectrum_id": "activation_amplitude", "values": [0.5]}],
        )
        self.assertEqual(
            c01["margins"],
            [{"margin_id": "grey_band_margin", "value": 0.05}],
        )
        self.assertEqual(c01["termination_events"], [])
        self.assertEqual(
            tuple(row["scenario_id"] for row in wire["scenario_manifest"]),
            SCENARIO_IDS,
        )
        c11_null = wire["scenario_manifest"][11]
        self.assertEqual(c11_null["control_id"], CONTROL_IDS[10])
        self.assertEqual(c11_null["execution_lane"], "EXPECTED_TYPED_TERMINATION")
        self.assertEqual(c11_null["expected_terminal_stage"], "activation")
        self.assertEqual(c11_null["expected_undefined_reason"], "response_null")

    def test_pass_requires_nonzero_finite_margin(self) -> None:
        for margin in (0.0, -0.1, float("inf"), float("nan")):
            with self.subTest(margin=margin):
                with self.assertRaises(ValueError):
                    V3M0AuditResult(
                        audit_id=CONTROL_IDS[0],
                        status=BlockStatus(True, None),
                        passed=True,
                        raw_spectra=(("s", (1.0,)),),
                        margins=(("margin", margin),),
                    )


class V3M0FailClosedAssemblyTests(unittest.TestCase):
    def test_missing_upstream_capabilities_halt_without_fabricating_pass(self) -> None:
        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=V3M0CapabilityBundle(),
            control_results=(),
            invariant_results=(),
            evidence=None,
            no_physical_anchor_run=True,
        )

        self.assertEqual(assembly.decision.state, V3M0State.HALT_WINDOW)
        self.assertFalse(assembly.all_required_controls_pass)
        self.assertFalse(assembly.representation_invariants_pass)
        self.assertEqual(
            assembly.required_blocks.undefined[0],
            (
                "window_threshold_calibration",
                UndefinedReason.WINDOW_UNRESOLVED,
            ),
        )
        self.assertEqual(
            tuple(result.audit_id for result in assembly.controls),
            CONTROL_IDS,
        )
        wire = control_assembly_to_wire(assembly)
        self.assertEqual(
            tuple(row["scenario_id"] for row in wire["BLOCK_SUCCESS"]),
            BLOCK_SUCCESS_SCENARIO_IDS,
        )
        self.assertEqual(
            tuple(
                row["scenario_id"]
                for row in wire["EXPECTED_TYPED_TERMINATION"]
            ),
            EXPECTED_TYPED_TERMINATION_SCENARIO_IDS,
        )
        self.assertEqual(
            tuple(row["scenario_id"] for row in wire["ANALYSIS_CONTROL"]),
            ANALYSIS_CONTROL_SCENARIO_IDS,
        )
        self.assertFalse(assembly.all_expected_terminations_verified)
        self.assertFalse(assembly.all_analysis_controls_verified)
        self.assertEqual(
            tuple(result.audit_id for result in assembly.invariants),
            REPRESENTATION_INVARIANT_IDS,
        )
        self.assertTrue(all(not result.passed for result in assembly.controls))

    def test_raw_substitutes_and_fake_pass_rows_cannot_unlock_ready(self) -> None:
        raw_pair = ({"branch": "actual"}, {"branch": "matched_ablated"})
        capabilities = V3M0CapabilityBundle(
            window_calibration={"status": "verified"},
            parent_freeze={"status": "verified"},
            survival_calibration={"tau_surv": 0.5},
            geometry_calibration={"tau_geom": 0.05},
            selected_blocks=tuple(
                (scenario_id, *raw_pair)
                for scenario_id in SELECTED_BLOCK_SUCCESS_SCENARIO_IDS
            ),
            application_permits=tuple(
                (control_id, {"status": "verified"})
                for control_id in APPLICATION_PERMIT_CONTROL_IDS
            ),
            application_blocks=tuple(
                (scenario_id, *raw_pair)
                for scenario_id in APPLICATION_SCENARIO_IDS
            ),
            expected_terminations=tuple(
                (scenario_id, {"status": "expected"})
                for scenario_id in EXPECTED_TYPED_TERMINATION_SCENARIO_IDS
            ),
            analysis_controls=tuple(
                (scenario_id, {"status": "verified"})
                for scenario_id in ANALYSIS_CONTROL_SCENARIO_IDS
            ),
        )
        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=capabilities,
            control_results=tuple(
                _passing_audit(item) for item in BLOCK_SUCCESS_SCENARIO_IDS
            ),
            invariant_results=tuple(
                _passing_audit(item) for item in REPRESENTATION_INVARIANT_IDS
            ),
            evidence={"caller": "raw substitute"},
            no_physical_anchor_run=True,
        )

        self.assertEqual(assembly.decision.state, V3M0State.HALT_CONTROL)
        self.assertFalse(assembly.decision.ready)
        undefined = dict(assembly.required_blocks.undefined)
        self.assertEqual(
            undefined["window_threshold_calibration"],
            UndefinedReason.MANIFEST_MISMATCH,
        )
        self.assertEqual(
            undefined["parent_freeze"],
            UndefinedReason.MANIFEST_MISMATCH,
        )
        self.assertEqual(
            undefined[
                f"{BLOCK_SUCCESS_SCENARIO_IDS[0]}.actual_response_block"
            ],
            UndefinedReason.MANIFEST_MISMATCH,
        )
        self.assertEqual(
            undefined[f"{CONTROL_IDS[3]}.application_permit"],
            UndefinedReason.MANIFEST_MISMATCH,
        )
        self.assertEqual(
            undefined["final_evidence_envelope"],
            UndefinedReason.MANIFEST_MISMATCH,
        )
        self.assertEqual(
            undefined[
                "v3m0.synthetic-control.c11.v1.scenario.signal.v1."
                "actual_response_block"
            ],
            UndefinedReason.MANIFEST_MISMATCH,
        )
        lane_failures = dict(assembly.lane_failures)
        self.assertEqual(
            lane_failures[
                f"{EXPECTED_TYPED_TERMINATION_SCENARIO_IDS[2]}."
                "unexpected_downstream_response_block"
            ],
            UndefinedReason.MANIFEST_MISMATCH,
        )
        self.assertEqual(
            lane_failures[
                f"{ANALYSIS_CONTROL_SCENARIO_IDS[0]}."
                "unexpected_downstream_response_block"
            ],
            UndefinedReason.MANIFEST_MISMATCH,
        )
        self.assertFalse(assembly.no_unexpected_downstream_capability)
        self.assertNotIn(
            f"{CONTROL_IDS[19]}.application_permit",
            undefined,
        )
        self.assertTrue(all(not result.passed for result in assembly.controls))

    def test_c20_uses_live_parent_but_not_window_permit_or_response(self) -> None:
        parent = issue_v3m0_parent_freeze()
        outcomes = issue_v3m0_deterministic_series_control_outcomes(parent)
        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=V3M0CapabilityBundle(
                parent_freeze=parent,
                analysis_controls=tuple(
                    zip(ANALYSIS_CONTROL_SCENARIO_IDS, outcomes)
                ),
            ),
            control_results=(),
            invariant_results=(),
            evidence=None,
            no_physical_anchor_run=True,
        )
        c20_clean, c20_floor = assembly.analysis_control
        required = dict(assembly.required_blocks.undefined)

        self.assertTrue(c20_clean.passed)
        self.assertTrue(c20_floor.passed)
        self.assertEqual(c20_clean.audit_id, ANALYSIS_CONTROL_SCENARIO_IDS[0])
        self.assertEqual(c20_floor.audit_id, ANALYSIS_CONTROL_SCENARIO_IDS[1])
        self.assertEqual(c20_clean.raw_spectra[1][0], "raw_samples")
        self.assertEqual(c20_floor.raw_spectra[1][0], "raw_samples")
        self.assertTrue(assembly.all_analysis_controls_verified)
        self.assertFalse(
            any(".c20." in lane_id for lane_id, _ in assembly.lane_failures)
        )
        self.assertNotIn(
            f"{ANALYSIS_CONTROL_SCENARIO_IDS[0]}.verified_series_evidence",
            required,
        )
        self.assertNotIn(f"{CONTROL_IDS[19]}.application_permit", required)
        self.assertNotIn(f"{CONTROL_IDS[19]}.actual_response_block", required)
        self.assertNotIn(f"{CONTROL_IDS[19]}.ablated_response_block", required)

    def test_c20_raw_analysis_substitutes_fail_strict_reverification(self) -> None:
        parent = issue_v3m0_parent_freeze()
        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=V3M0CapabilityBundle(
                parent_freeze=parent,
                analysis_controls=tuple(
                    (scenario_id, {"caller": "raw"})
                    for scenario_id in ANALYSIS_CONTROL_SCENARIO_IDS
                ),
            ),
            control_results=(),
            invariant_results=(),
            evidence=None,
            no_physical_anchor_run=True,
        )

        self.assertFalse(assembly.all_analysis_controls_verified)
        failures = dict(assembly.lane_failures)
        for scenario_id in ANALYSIS_CONTROL_SCENARIO_IDS:
            self.assertEqual(
                failures[f"{scenario_id}.verified_series_evidence"],
                UndefinedReason.MANIFEST_MISMATCH,
            )

    def test_non_window_reasons_never_borrow_window_halt(self) -> None:
        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=V3M0CapabilityBundle(
                window_calibration=object(),
            ),
            control_results=(),
            invariant_results=(),
            evidence=None,
            no_physical_anchor_run=True,
        )

        self.assertEqual(assembly.decision.state, V3M0State.HALT_CONTROL)
        self.assertNotEqual(
            assembly.required_blocks.undefined[0][1],
            UndefinedReason.WINDOW_UNRESOLVED,
        )


class V3M0AtomicEvidenceTests(unittest.TestCase):
    def test_result_and_state_are_staged_fsynced_and_atomically_replaced(
        self,
    ) -> None:
        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=V3M0CapabilityBundle(),
            control_results=(),
            invariant_results=(),
            evidence=None,
            no_physical_anchor_run=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "v3m0_controls.json"
            state_path = root / "v3m0_state.json"
            with (
                mock.patch(
                    "experiments.v3m0_preflight.os.replace",
                    wraps=os.replace,
                ) as replace_call,
                mock.patch(
                    "experiments.v3m0_preflight.os.fsync",
                    wraps=os.fsync,
                ) as fsync_call,
            ):
                write_preflight_outputs(
                    assembly,
                    result_path=result_path,
                    state_path=state_path,
                )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(result["state"], "HALT-V3M0-WINDOW")
            self.assertEqual(state["state"], result["state"])
            self.assertEqual(state["result_sha"], result["result_sha"])
            self.assertEqual(
                tuple(field for field in FINAL_RESULT_EVIDENCE_FIELDS),
                tuple(
                    field
                    for field in FINAL_RESULT_EVIDENCE_FIELDS
                    if field in result
                ),
            )
            self.assertTrue(
                all(result[field] is None for field in FINAL_RESULT_EVIDENCE_FIELDS)
            )
            self.assertEqual(replace_call.call_count, 2)
            self.assertGreaterEqual(fsync_call.call_count, 3)
            for call in replace_call.call_args_list:
                source, destination = call.args
                self.assertIn(".tmp", str(source))
                self.assertIn(destination, (result_path, state_path))
            self.assertEqual(tuple(root.glob("*.tmp")), ())

    def test_result_and_state_targets_must_be_distinct(self) -> None:
        assembly = assemble_v3m0_controls(
            formal_all_pass=False,
            exact_all_pass=False,
            identifiability_all_pass=False,
            capabilities=V3M0CapabilityBundle(),
            control_results=(),
            invariant_results=(),
            evidence=None,
            no_physical_anchor_run=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "same.json"
            with self.assertRaisesRegex(ValueError, "distinct"):
                write_preflight_outputs(
                    assembly,
                    result_path=path,
                    state_path=path,
                )

    def test_script_entrypoint_generates_then_checks_same_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = root / "result.json"
            state = root / "state.json"
            command = (
                sys.executable,
                str(ROOT / "experiments" / "v3m0_preflight.py"),
            )
            targets = (
                "--output",
                str(result),
                "--state-output",
                str(state),
            )
            generated = subprocess.run(
                (*command, "--generate", *targets),
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            checked = subprocess.run(
                (*command, "--check", *targets),
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                generated.returncode,
                0,
                msg=generated.stdout + generated.stderr,
            )
            self.assertEqual(
                checked.returncode,
                0,
                msg=checked.stdout + checked.stderr,
            )
            self.assertIn("HALT-V3M0-WINDOW", generated.stdout)

    def test_self_resigned_phase0_substitute_cannot_set_formal_pass(self) -> None:
        payload = json.loads(DEFAULT_PHASE0.read_text(encoding="utf-8"))
        payload["artifact_kind"] = "caller-resigned-substitute"
        body = dict(payload)
        body.pop("certificate_sha")
        payload["certificate_sha"] = canonical_sha(body)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase0.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
            assembly = build_current_checkpoint(path)

        self.assertFalse(assembly.formal_all_pass)
        self.assertFalse(assembly.exact_all_pass)
        self.assertEqual(assembly.decision.state, V3M0State.HALT_FORMAL)


class V3M0HistoricalFactoryBoundaryTests(unittest.TestCase):
    def test_import_does_not_load_or_execute_historical_factories(self) -> None:
        script = r"""
import builtins
import importlib
import sys

forbidden = {
    "photon_control",
    "r23_maxwell_control",
    "r30_tensor_complex_dynamical",
    "r25_realspace_step",
    "r25_dynamic_symbol",
    "r25_auxiliary_wilson_complex",
}
original_import = builtins.__import__
original_open = builtins.open

def guarded_import(name, *args, **kwargs):
    if name.split(".")[-1] in forbidden:
        raise AssertionError("historical physics import attempted: " + name)
    return original_import(name, *args, **kwargs)

def guarded_open(file, mode="r", *args, **kwargs):
    if any(flag in mode for flag in ("w", "a", "x", "+")):
        raise AssertionError("preflight import attempted a write")
    return original_open(file, mode, *args, **kwargs)

builtins.__import__ = guarded_import
builtins.open = guarded_open
importlib.import_module("experiments.v3m0_controls")
importlib.import_module("experiments.v3m0_preflight")
assert forbidden.isdisjoint({name.split(".")[-1] for name in sys.modules})
"""
        completed = subprocess.run(
            (sys.executable, "-c", script),
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=completed.stdout + completed.stderr,
        )

    def test_runner_has_no_historical_factory_import_or_execution_call(self) -> None:
        paths = (
            ROOT / "experiments" / "v3m0_controls.py",
            ROOT / "experiments" / "v3m0_preflight.py",
        )
        forbidden_leaves = {
            "photon_control",
            "r23_maxwell_control",
            "r30_tensor_complex_dynamical",
            "r25_realspace_step",
            "r25_dynamic_symbol",
            "r25_auxiliary_wilson_complex",
        }
        forbidden_calls = {
            "step_yee",
            "leap_M",
            "evolve_components",
            "batched_step",
            "realspace_step_factory",
        }
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported: set[str] = set()
            calls: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[-1] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[-1])
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        calls.add(node.func.attr)
            self.assertTrue(forbidden_leaves.isdisjoint(imported), msg=str(path))
            self.assertTrue(forbidden_calls.isdisjoint(calls), msg=str(path))


if __name__ == "__main__":
    unittest.main()
