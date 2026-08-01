"""Fast tests for the non-authoritative Task-11 raw replay artifact."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.thresholds import T_CANDIDATES


SHA0 = "0" * 64
SHA1 = "1" * 64
SHA2 = "2" * 64
SHA3 = "3" * 64
SHA4 = "4" * 64
SHA5 = "5" * 64
SHA6 = "6" * 64
SHA7 = "7" * 64
SHA8 = "8" * 64
SHA9 = "9" * 64
SHAA = "a" * 64
SHAB = "b" * 64
SHAC = "c" * 64
SHAD = "d" * 64
SHAE = "e" * 64
SHAF = "f" * 64


def _attempt(order: int, suffix: str) -> dict[str, object]:
    return {
        "status": {"defined": True, "reason": None},
        "failure": None,
        "run_spec": {
            "fejer_order": order,
            "spec_sha": (suffix * 64)[:64],
        },
        "attempt_audit": {
            "attempt_sha": ((suffix.upper() if suffix != "a" else "b") * 64)[
                :64
            ].lower(),
            "shell_outcome": {
                "outcome_sha": SHA6,
                "shell": {"shell_manifest_sha": SHA7},
            },
            "paired_response_outcome": {
                "status": {"defined": True, "reason": None},
                "failure": None,
                "paired_response": {"pair_sha": SHA8},
                "outcome_sha": SHA9,
            },
        },
        "outcome_sha": SHAA,
    }


def _aggregate(kind: str, order: int) -> dict[str, object]:
    scale = float(order)
    return {
        "readout_kind": kind,
        "scale_ref": scale,
        "null_max": scale / 1000.0,
        "bridge_operator_error_max": 1.0e-14,
        "noise_ref": scale / 500.0,
        "signal_min": scale / 2.0,
        "tau_sig": scale / 100.0,
        "signal_noise_ratio": 250.0,
        "raw_relative_gap": 500.0,
        "absolute_signal_gate_passed": True,
        "relative_gap_gate_passed": False,
        "aggregate_sha": SHAB if kind == "h" else SHAC,
    }


def _outcome_payload(*, resolved: bool = False) -> dict[str, object]:
    candidates = []
    for order in T_CANDIDATES:
        controls = []
        for index, control_id in enumerate(("full", "zero", "direct_sum")):
            controls.append(
                {
                    "control_registry_entry": {
                        "control_id": control_id,
                        "entry_sha": (str(index + 1) * 64)[:64],
                    },
                    "candidate_t": _attempt(order, str(index + 1)),
                    "comparison_2t": _attempt(2 * order, str(index + 4)),
                    "phase_separation": float(order) / 10.0,
                    "overlap_margin": 0.25 + index / 100.0,
                    "projector_t2t_distance": 1.0e-13 * (index + 1),
                    "passed": index != 2,
                    "audit_sha": SHAE,
                    "readout_spectrum_audits": [],
                    "comparison_2t_readout_spectrum_audits": [],
                }
            )
        candidates.append(
            {
                "fejer_order": order,
                "control_audits": controls,
                "readout_aggregate_audits": [
                    _aggregate("h", order),
                    _aggregate("curv", order),
                ],
                "passed": resolved and order == T_CANDIDATES[2],
                "audit_sha": SHAD,
            }
        )
    selection = None
    status = {"defined": False, "reason": "window_unresolved"}
    if resolved:
        selection = {
            "selected_fejer_order": T_CANDIDATES[2],
            "h_scale_ref": 1.0,
            "h_noise_ref": 2.0,
            "h_signal_min": 3.0,
            "h_tau_sig": 4.0,
            "curv_scale_ref": 5.0,
            "curv_noise_ref": 6.0,
            "curv_signal_min": 7.0,
            "curv_tau_sig": 8.0,
            "selected_evidence_refs": [],
            "selection_sha": SHAF,
        }
        status = {"defined": True, "reason": None}
    return {
        "status": status,
        "manifest": {
            "calibration_schema_version": (
                "v3m0.window-threshold-calibration-manifest.v1"
            ),
            "control_registry": {"registry_sha": SHA1},
            "window_protocol": {"protocol_sha": SHA2},
            "candidate_audits": candidates,
            "calibration_manifest_sha": SHA3,
        },
        "selection": selection,
    }


def _provenance() -> dict[str, object]:
    from rulespace_v3.task11_evidence import (
        TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS,
        TASK11_RAW_REPLAY_SCOPE,
    )

    runtime_body = {
        "runtime_schema_version": "v3m0.runtime-evidence.v1",
        "evaluator_id": "rulespace-v3m0-certificate-closure-v1",
        "source_closure": [
            {"relative_path": "rulespace_v3/runtime.py", "sha256": SHA9}
        ],
        "python_version": "3.11-test",
        "numpy_version": "2-test",
        "scipy_version": "1-test",
        "blas_config_sha": SHAB,
        "lapack_config_sha": SHAC,
        "platform_id": "test-platform",
    }
    runtime_manifest = {
        **runtime_body,
        "runtime_manifest_sha": canonical_sha(runtime_body),
    }

    return {
        "replay_scope": TASK11_RAW_REPLAY_SCOPE,
        "historical_parent_v1_sha": SHA4,
        "placeholder_parent_freeze_v2_sha": SHAA,
        "legacy_registry_sha": SHA1,
        "current_control_registry_sha": SHA3,
        "legacy_window_protocol_sha": SHA2,
        "current_window_protocol_sha": SHA5,
        "scenario_authority_shas": [SHA6, SHA7, SHA8],
        "git_head": "9" * 40,
        "git_worktree_dirty": False,
        "source_files": [
            {
                "relative_path": relative_path,
                "sha256": f"{index + 1:x}" * 64,
            }
            for index, relative_path in enumerate(
                TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS
            )
        ],
        "runtime_manifest": runtime_manifest,
        "command": ["python", "experiments/v3m0_task11_raw_replay.py"],
    }


class Task11RawReplayEvidenceTests(unittest.TestCase):
    def test_summary_retains_six_orders_controls_2t_and_gate_metrics(self) -> None:
        from rulespace_v3.task11_evidence import (
            summarize_task11_outcome_payload,
        )

        summary = summarize_task11_outcome_payload(_outcome_payload())

        self.assertEqual(
            tuple(item["fejer_order"] for item in summary["orders"]),
            T_CANDIDATES,
        )
        for order_summary, order in zip(summary["orders"], T_CANDIDATES):
            self.assertEqual(
                tuple(item["control_id"] for item in order_summary["controls"]),
                ("full", "zero", "direct_sum"),
            )
            for control in order_summary["controls"]:
                self.assertEqual(control["candidate_t"]["fejer_order"], order)
                self.assertEqual(control["comparison_2t"]["fejer_order"], 2 * order)
                self.assertIn("phase_separation", control["gate_metrics"])
                self.assertIn("paired_response_sha", control["candidate_t"])
            self.assertEqual(
                tuple(
                    item["readout_kind"] for item in order_summary["aggregate_gates"]
                ),
                ("h", "curv"),
            )
            self.assertFalse(
                order_summary["aggregate_gates"][0]["relative_gap_gate_passed"]
            )
        self.assertEqual(
            summary["outcome_status"],
            {"defined": False, "reason": "window_unresolved"},
        )
        self.assertIsNone(summary["selection"])

    def test_envelope_is_explicitly_non_authoritative_and_tamper_evident(
        self,
    ) -> None:
        from rulespace_v3.task11_evidence import (
            TASK11_RAW_REPLAY_AUTHORITY_STATE,
            TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT,
            build_task11_raw_replay_evidence_payload,
            verify_task11_raw_replay_evidence_payload,
        )

        outcome = _outcome_payload(resolved=True)
        outcome_sha = canonical_sha(outcome)
        evidence = build_task11_raw_replay_evidence_payload(
            outcome,
            outcome_sha=outcome_sha,
            provenance=_provenance(),
        )

        self.assertEqual(evidence["authority_state"], TASK11_RAW_REPLAY_AUTHORITY_STATE)
        self.assertEqual(
            evidence["scientific_verdict"],
            TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT,
        )
        self.assertIs(evidence["current_parent_v2_bound"], False)
        self.assertEqual(evidence["create_policy"], "CREATE_ONLY")
        self.assertEqual(evidence["outcome"], outcome)
        self.assertEqual(evidence["outcome_sha"], outcome_sha)
        self.assertEqual(
            evidence["provenance"]["runtime_manifest"]["python_version"],
            "3.11-test",
        )
        from rulespace_v3.task11_evidence import (
            TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS,
        )

        self.assertEqual(
            frozenset(
                item["relative_path"] for item in evidence["provenance"]["source_files"]
            ),
            frozenset(TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS),
        )
        self.assertEqual(
            evidence["evidence_sha"],
            canonical_sha(
                {key: value for key, value in evidence.items() if key != "evidence_sha"}
            ),
        )
        self.assertEqual(
            evidence["summary"]["selection"]["selected_fejer_order"],
            T_CANDIDATES[2],
        )
        self.assertEqual(verify_task11_raw_replay_evidence_payload(evidence), evidence)

        attacked = copy.deepcopy(evidence)
        attacked["summary"]["orders"][0]["passed"] = True
        with self.assertRaisesRegex(ValueError, "summary|SHA"):
            verify_task11_raw_replay_evidence_payload(attacked)

        attacked = copy.deepcopy(evidence)
        attacked["outcome"]["manifest"]["candidate_audits"][0]["passed"] = True
        with self.assertRaisesRegex(ValueError, "outcome SHA"):
            verify_task11_raw_replay_evidence_payload(attacked)

    def test_builder_rejects_wrong_outcome_sha_and_nonfinite_metrics(self) -> None:
        from rulespace_v3.task11_evidence import (
            build_task11_raw_replay_evidence_payload,
        )

        outcome = _outcome_payload()
        with self.assertRaisesRegex(ValueError, "outcome SHA"):
            build_task11_raw_replay_evidence_payload(
                outcome,
                outcome_sha=SHA0,
                provenance=_provenance(),
            )

        outcome["manifest"]["candidate_audits"][0]["control_audits"][0][
            "phase_separation"
        ] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite|NaN|nan"):
            build_task11_raw_replay_evidence_payload(
                outcome,
                outcome_sha=SHA0,
                provenance=_provenance(),
            )

    def test_writer_is_atomic_create_only_and_keeps_existing_bytes(self) -> None:
        from experiments.v3m0_task11_raw_replay import (
            write_task11_raw_replay_evidence_create_only,
        )
        from rulespace_v3.task11_evidence import (
            build_task11_raw_replay_evidence_payload,
        )

        outcome = _outcome_payload()
        evidence = build_task11_raw_replay_evidence_payload(
            outcome,
            outcome_sha=canonical_sha(outcome),
            provenance=_provenance(),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task11.json"
            write_task11_raw_replay_evidence_create_only(path, evidence)
            first_bytes = path.read_bytes()
            self.assertEqual(json.loads(first_bytes), evidence)
            with self.assertRaises(FileExistsError):
                write_task11_raw_replay_evidence_create_only(path, evidence)
            self.assertEqual(path.read_bytes(), first_bytes)
            self.assertEqual(
                tuple(item.name for item in path.parent.iterdir()),
                (path.name,),
            )

    def test_cli_runner_accepts_injected_fast_execution_and_preflights_output(
        self,
    ) -> None:
        from experiments.v3m0_task11_raw_replay import run_raw_replay

        outcome = _outcome_payload()
        calls = []

        def execute():
            calls.append("execute")
            return outcome, canonical_sha(outcome), _provenance()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task11.json"
            result = run_raw_replay(path, execute=execute)
            self.assertEqual(calls, ["execute"])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), result)

            with self.assertRaises(FileExistsError):
                run_raw_replay(path, execute=execute)
            self.assertEqual(calls, ["execute"])

            missing_parent = Path(directory) / "missing" / "task11.json"
            with self.assertRaises(FileNotFoundError):
                run_raw_replay(missing_parent, execute=execute)
            self.assertEqual(calls, ["execute"])


if __name__ == "__main__":
    unittest.main()
