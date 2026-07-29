"""M3′ Round 1: execute the frozen 30-cell strict-local real-space pilot.

This runner consumes ``READY-PILOT`` only.  It executes no formal scan and can
at most unlock a separate formal-preregistration step.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import sys
import tempfile
import time
from typing import Any

import numpy as np

os.environ.setdefault("RULESPACE_BACKEND", "numpy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rulespace_v2 import invariants as INV  # noqa: E402
from rulespace_v2 import frozen as FROZEN  # noqa: E402
from rulespace_v2 import m3_pilot as PILOT  # noqa: E402
from rulespace_v2.m3_family import build_pilot_manifest  # noqa: E402


PREFLIGHT_PATH = ROOT / "data" / "results" / "v2m3_preflight.json"
LOCAL_CERTIFICATE_PATH = (
    ROOT / "data" / "results" / "v2m3_local_family_certificate.json"
)
RESULT_PATH = ROOT / "data" / "results" / "v2m3_pilot.json"
STATE_PATH = ROOT / "data" / "runtime" / "v2m3_state.json"
FIGURE_PATH = ROOT / "visualizations" / "figs" / "v2m3_pilot_map.png"
DESIGN_PATH = ROOT / "docsv2" / "v2-设计-M3-30格pilot实测-2026-07-30.md"

WALL_BUDGET_SECONDS = 300.0
RSS_BUDGET_BYTES = 2 * 1024**3
RESOURCE_MARGIN_REQUIRED = 1.5


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return _restore_nonfinite(payload)


def _restore_nonfinite(value: Any) -> Any:
    """Invert the JSON-safe representation used for non-finite diagnostics."""

    if isinstance(value, dict):
        return {key: _restore_nonfinite(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_nonfinite(item) for item in value]
    if value == "inf":
        return float("inf")
    if value == "-inf":
        return float("-inf")
    if value == "nan":
        return float("nan")
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else str(number)
    return value


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(
                _json_safe(payload),
                handle,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def evaluate_input_payloads(
    preflight: dict[str, Any],
    state: dict[str, Any],
    local_certificate: dict[str, Any],
    file_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Pure Round-0 lineage audit, usable by tests and the runner."""

    expected_cells = [cell.as_dict() for cell in build_pilot_manifest()]
    observed_manifest = preflight.get("pilot_manifest", {})
    if state.get("generator") == "experiments/v2m3_preflight.py":
        state_lineage = bool(
            state.get("result", {}).get("sha256")
            == file_records["preflight"]["sha256"]
            and state.get("local_family_certificate", {}).get("sha256")
            == file_records["local_certificate"]["sha256"]
        )
    else:
        pilot_inputs = state.get("pilot_inputs", {})
        state_lineage = bool(
            pilot_inputs.get("preflight", {}).get("sha256")
            == file_records["preflight"]["sha256"]
            and pilot_inputs.get("local_certificate", {}).get("sha256")
            == file_records["local_certificate"]["sha256"]
        )
    checks = {
        "preflight_ready": preflight.get("status") == "READY-PILOT",
        "pilot_unlocked": preflight.get("main_pilot_unlocked") is True,
        "pilot_not_preexecuted": preflight.get("main_pilot_executed") is False,
        "manifest_exact": (
            observed_manifest.get("cell_count") == 30
            and observed_manifest.get("cells") == expected_cells
        ),
        "local_certificate_pass": local_certificate.get("pass") is True,
        "preflight_certificate_embedded_pass": (
            preflight.get("local_family_certificate", {}).get("pass") is True
        ),
        "certificate_sha_matches_preflight_record": (
            preflight.get("local_family_certificate_record", {}).get("sha256")
            == file_records["local_certificate"]["sha256"]
        ),
        "runtime_lineage_matches": state_lineage,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "manifest_cells": expected_cells,
    }


def audit_inputs() -> dict[str, Any]:
    preflight = _read_json(PREFLIGHT_PATH)
    state = _read_json(STATE_PATH)
    local_certificate = _read_json(LOCAL_CERTIFICATE_PATH)
    file_records = {
        "preflight": {
            "path": str(PREFLIGHT_PATH.relative_to(ROOT)),
            "sha256": sha256_file(PREFLIGHT_PATH),
        },
        "local_certificate": {
            "path": str(LOCAL_CERTIFICATE_PATH.relative_to(ROOT)),
            "sha256": sha256_file(LOCAL_CERTIFICATE_PATH),
        },
        "design": {
            "path": str(DESIGN_PATH.relative_to(ROOT)),
            "sha256": sha256_file(DESIGN_PATH),
        },
    }
    audit = evaluate_input_payloads(
        preflight,
        state,
        local_certificate,
        file_records,
    )
    pair = validate_checkpoint_pair(state, RESULT_PATH.is_file())
    audit["checks"]["state_result_pair"] = pair["pass"]
    audit["pass"] = bool(audit["pass"] and pair["pass"])
    return {
        **audit,
        "checkpoint_pair": pair,
        "preflight": preflight,
        "state": state,
        "local_certificate": local_certificate,
        "file_records": file_records,
    }


def _environment_fingerprint() -> dict[str, Any]:
    environment = INV.environment_record()
    return {
        key: environment[key]
        for key in (
            "numpy_version",
            "blas",
            "lapack",
            "python",
            "platform",
            "machine",
        )
    }


def _protocol_record() -> dict[str, Any]:
    source_paths = (
        "experiments/v2m3_pilot.py",
        "rulespace_v2/m3_pilot.py",
        "rulespace_v2/m3_local_family.py",
        "rulespace_v2/m3_family.py",
        "rulespace_v2/invariants.py",
        "rulespace_v2/epsilon.py",
        "rulespace_v2/frozen.py",
    )
    return {
        "kind": "measured-realspace-impulse-response",
        "impulse_L": PILOT.IMPULSE_L,
        "canonical_delta_runs_per_cell": PILOT.N_CHANNELS,
        "production_step_fft": False,
        "post_run_transform": "finite measured-kernel sum; no FFT required",
        "directions": {
            name: list(direction)
            for name, direction in PILOT.DIRECTIONS.items()
        },
        "epsilon_reference_ratio": [1, 8],
        "sin_threshold": INV.SIN_THRESH,
        "floquet_modulus_tolerance": PILOT.FLOQUET_MODULUS_TOL,
        "basis_drift_tolerance": INV.DRIFT_TOL,
        "plane_bridge_tolerance": 1e-12,
        "sigma_teeth_absolute_margin": PILOT.SIGMA_TEETH_ABSOLUTE_MARGIN,
        "resource_limits": {
            "wall_budget_seconds": WALL_BUDGET_SECONDS,
            "rss_budget_bytes": RSS_BUDGET_BYTES,
            "margin_factor_required": RESOURCE_MARGIN_REQUIRED,
        },
        "environment_fingerprint": _environment_fingerprint(),
        "code": {
            relative_path: {
                "path": relative_path,
                "sha256": sha256_file(ROOT / relative_path),
            }
            for relative_path in source_paths
        },
        "frozen_verification": FROZEN.verify_frozen(),
    }


def _resource_review(
    wall_seconds: float,
    peak_rss_bytes: int,
    *,
    extrapolated: bool,
) -> dict[str, Any]:
    wall_margin = WALL_BUDGET_SECONDS / max(wall_seconds, 1e-300)
    rss_margin = RSS_BUDGET_BYTES / max(peak_rss_bytes, 1)
    margin = min(wall_margin, rss_margin)
    return {
        "kind": "30-cell extrapolation" if extrapolated else "30-cell actual",
        "wall_seconds": float(wall_seconds),
        "peak_rss_bytes": int(peak_rss_bytes),
        "wall_margin_factor": float(wall_margin),
        "rss_margin_factor": float(rss_margin),
        "margin_factor": float(margin),
        "required_margin_factor": RESOURCE_MARGIN_REQUIRED,
        "pass": bool(margin >= RESOURCE_MARGIN_REQUIRED),
    }


def _update_resource_ledger(
    payload: dict[str, Any],
    prior_wall_seconds: float,
    prior_peak_rss_bytes: int,
    segment_started: float,
) -> None:
    payload["resource_ledger"] = {
        "cumulative_wall_seconds": float(
            prior_wall_seconds + (time.perf_counter() - segment_started)
        ),
        "peak_rss_bytes": int(
            max(prior_peak_rss_bytes, _peak_rss_bytes())
        ),
        "wall_definition": (
            "cumulative end-to-end runner segments through the latest checkpoint"
        ),
        "resume_safe": True,
    }


def _partial_state(
    payload: dict[str, Any],
    input_records: dict[str, Any],
) -> dict[str, Any]:
    return {
        "_schema": "v2m3_state v3",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "experiments/v2m3_pilot.py",
        "lit": False,
        "status": payload["status"],
        "round": 1,
        "main_pilot_unlocked": False,
        "main_pilot_executed": False,
        "completed_cells": len(payload["cells"]),
        "pilot_manifest_cell_count": 30,
        "pilot_inputs": input_records,
        "result": {
            "path": str(RESULT_PATH.relative_to(ROOT)),
            "sha256": sha256_file(RESULT_PATH),
        },
        "formal_preregistration_unlocked": False,
        "formal_scan_unlocked": False,
        "wording": "30 格 pilot 正在运行；正式扫描锁定。",
    }


def _summary(cells: list[dict[str, Any]]) -> dict[str, Any]:
    valid_cells = [cell for cell in cells if cell.get("valid") is True]
    epsilon_range = (
        [
            min(cell["epsilon_geo_min_max"][0] for cell in valid_cells),
            max(cell["epsilon_geo_min_max"][1] for cell in valid_cells),
        ]
        if valid_cells
        else None
    )
    sigma = {}
    for direction in PILOT.DIRECTIONS:
        rows = [
            cell["sigma_by_direction"][direction] for cell in valid_cells
        ]
        sigma[direction] = (
            {
                "alpha_min_max": [
                    min(row["alpha"] for row in rows),
                    max(row["alpha"] for row in rows),
                ],
                "A_min_max": [
                    min(row["A"] for row in rows),
                    max(row["A"] for row in rows),
                ],
                "verdict_counts": dict(
                    Counter(row["verdict"] for row in rows)
                ),
            }
            if rows
            else None
        )
    return {
        "cell_count": len(cells),
        "valid_cell_count": len(valid_cells),
        "invalid_cell_ids": [
            cell["cell_id"] for cell in cells if cell.get("valid") is not True
        ],
        "delta_realspace_runs": sum(
            cell["runtime"].get("delta_realspace_runs", 0) for cell in cells
        ),
        "validation_realspace_runs": sum(
            cell["runtime"].get("validation_realspace_runs", 0)
            for cell in cells
        ),
        "epsilon_geo_global_min_max": epsilon_range,
        "unique_epsilon_signature_count": len(
            {
                tuple(
                    (
                        row["direction"],
                        row["N_curv"],
                        row["j_hand_invariant"],
                    )
                    for row in cell["epsilon_signature"]
                )
                for cell in valid_cells
            }
        ),
        "sigma_by_direction": sigma,
        "max_support_radius": (
            max(cell["runtime"]["support_radius"] for cell in valid_cells)
            if valid_cells
            else None
        ),
        "max_plane_bridge_residual": (
            max(
                cell["runtime"]["plane_bridge_residual"]
                for cell in valid_cells
            )
            if valid_cells
            else None
        ),
        "max_floquet_modulus_error": (
            max(
                cell["runtime"]["max_floquet_modulus_error"]
                for cell in valid_cells
            )
            if valid_cells
            else None
        ),
    }


def validate_existing_payload(
    payload: dict[str, Any],
    input_records: dict[str, Any],
    current_protocol: dict[str, Any],
) -> dict[str, Any]:
    """Decide whether an existing result is terminal, complete, or resumable."""

    failures = []
    if payload.get("inputs") != input_records:
        failures.append("input_lineage_changed")
    stored_protocol = payload.get("protocol", {})
    protocol_equal = stored_protocol == current_protocol
    stored_without_runner = {
        **stored_protocol,
        "code": {
            path: record
            for path, record in stored_protocol.get("code", {}).items()
            if path != "experiments/v2m3_pilot.py"
        },
    }
    current_without_runner = {
        **current_protocol,
        "code": {
            path: record
            for path, record in current_protocol.get("code", {}).items()
            if path != "experiments/v2m3_pilot.py"
        },
    }
    stored_runner_record = stored_protocol.get("code", {}).get(
        "experiments/v2m3_pilot.py"
    )
    current_runner_record = current_protocol.get("code", {}).get(
        "experiments/v2m3_pilot.py"
    )
    old_runner_sha = (
        stored_runner_record.get("sha256")
        if isinstance(stored_runner_record, dict)
        else None
    )
    new_runner_sha = (
        current_runner_record.get("sha256")
        if isinstance(current_runner_record, dict)
        else None
    )

    def valid_sha256(value: object) -> bool:
        return bool(
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )

    runner_records_match_except_sha = bool(
        isinstance(stored_runner_record, dict)
        and isinstance(current_runner_record, dict)
        and set(stored_runner_record) == set(current_runner_record)
        and stored_runner_record.get("path") == "experiments/v2m3_pilot.py"
        and current_runner_record.get("path") == "experiments/v2m3_pilot.py"
        and {
            key: value
            for key, value in stored_runner_record.items()
            if key != "sha256"
        }
        == {
            key: value
            for key, value in current_runner_record.items()
            if key != "sha256"
        }
        and valid_sha256(old_runner_sha)
        and valid_sha256(new_runner_sha)
        and old_runner_sha != new_runner_sha
    )
    runner_only_change = bool(
        not protocol_equal
        and stored_without_runner == current_without_runner
        and runner_records_match_except_sha
    )
    recorded_amendment = payload.get("finalization_amendment", {})
    amendment_already_applied = bool(
        runner_only_change
        and payload.get("main_pilot_executed") is True
        and recorded_amendment.get("old_runner_sha256") == old_runner_sha
        and recorded_amendment.get("new_runner_sha256") == new_runner_sha
        and recorded_amendment.get("measurement_cells_reexecuted") is False
    )
    amendment_is_eligible = bool(
        runner_only_change
        and payload.get("status") == "RUNNING-PILOT"
        and payload.get("main_pilot_executed") is False
        and len(payload.get("cells", [])) == 30
    )
    if not protocol_equal and not (
        amendment_is_eligible or amendment_already_applied
    ):
        failures.append("protocol_changed")
    status = payload.get("status")
    resource_halt = bool(
        status == "HALT-PILOT-RESOURCE"
        or (
            payload.get("resource_preflight") is not None
            and payload["resource_preflight"].get("pass") is False
        )
    )
    if failures:
        action = "reject"
    elif resource_halt:
        action = "halt-resource"
    elif amendment_is_eligible:
        action = "finalize-runner-amendment"
    elif payload.get("main_pilot_executed") is True:
        action = "complete"
    elif status == "RUNNING-PILOT":
        action = "resume"
    else:
        failures.append("invalid_existing_status")
        action = "reject"
    return {
        "pass": not failures,
        "action": action,
        "failures": failures,
        "runner_only_change": runner_only_change,
        "old_runner_sha256": old_runner_sha,
        "new_runner_sha256": new_runner_sha,
    }


def validate_checkpoint_pair(
    state: dict[str, Any],
    result_exists: bool,
) -> dict[str, Any]:
    """Require recoverable pilot state and pilot result to exist as one pair."""

    state_is_pilot = state.get("generator") == "experiments/v2m3_pilot.py"
    pair_matches = bool(state_is_pilot == result_exists)
    return {
        "pass": pair_matches,
        "failures": [] if pair_matches else ["state_result_pair_mismatch"],
        "state_is_pilot": state_is_pilot,
        "result_exists": result_exists,
    }


def validate_checkpoint(
    payload: dict[str, Any],
    state: dict[str, Any],
    manifest_cells: list[dict[str, Any]],
    result_sha256: str,
) -> dict[str, Any]:
    """Cross-check one persisted result/state checkpoint before resuming."""

    failures = []
    cells = payload.get("cells", [])
    prefix_matches = len(cells) <= len(manifest_cells)
    if prefix_matches:
        for cell, manifest_cell in zip(cells, manifest_cells):
            construction = cell.get("construction", {})
            if (
                cell.get("cell_id") != manifest_cell["cell_id"]
                or construction.get("q") != manifest_cell["q"]
                or construction.get("kappa_c") != manifest_cell["kappa_c"]
            ):
                prefix_matches = False
                break
    if not prefix_matches:
        failures.append("cells_not_manifest_prefix")
    if state.get("result", {}).get("sha256") != result_sha256:
        failures.append("checkpoint_result_sha_mismatch")
    if state.get("status") != payload.get("status"):
        failures.append("checkpoint_status_mismatch")
    if state.get("completed_cells") != len(cells):
        failures.append("checkpoint_cell_count_mismatch")
    if state.get("main_pilot_executed") is not payload.get(
        "main_pilot_executed"
    ):
        failures.append("checkpoint_execution_flag_mismatch")
    return {
        "pass": not failures,
        "failures": failures,
        "observed_cells": len(cells),
    }


def measure_manifest_cell(
    manifest_cell: dict[str, Any],
) -> dict[str, Any]:
    """Convert measurement exceptions into an explicit invalid cell record."""

    started = time.perf_counter()
    try:
        cell = PILOT.measure_cell(
            q=manifest_cell["q"],
            kappa_c=manifest_cell["kappa_c"],
        )
    except Exception as exc:
        cell = {
            "cell_id": manifest_cell["cell_id"],
            "construction": {
                "q": manifest_cell["q"],
                "kappa_c": manifest_cell["kappa_c"],
            },
            "fixed": {
                "eta": manifest_cell.get("eta", 0.0),
                "matter_epsilon": manifest_cell.get(
                    "matter_epsilon_fixed",
                    1.0,
                ),
            },
            "valid": False,
            "failures": ["measurement_exception"],
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "runtime": {
                "wall_seconds": float(time.perf_counter() - started),
            },
        }
    cell["runtime"]["process_peak_rss_bytes"] = _peak_rss_bytes()
    return cell


def make_figure(payload: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cells = [cell for cell in payload["cells"] if cell.get("valid") is True]
    background = "#0B1013"
    panel = "#111B22"
    line = "#1E2C35"
    ink = "#DDE6EC"
    muted = "#7F909D"
    cyan = "#45D4C6"
    sealed = "#E5687A"

    figure, axes = plt.subplots(1, 2, figsize=(15.5, 6.8), facecolor=background)
    for axis in axes:
        axis.set_facecolor(panel)
        axis.tick_params(colors=muted)
        axis.grid(color=line, alpha=0.55, linewidth=0.7)
        for spine in axis.spines.values():
            spine.set_color(line)

    left = axes[0]
    for cell in cells:
        q = cell["construction"]["q"]
        kappa = cell["construction"]["kappa_c"]
        epsilon_low, epsilon_high = cell["epsilon_geo_min_max"]
        axial = cell["sigma_by_direction"]["axial"]
        color = sealed if axial["verdict"] == "FAIL" else cyan
        left.plot(
            [epsilon_low, epsilon_high],
            [axial["A"], axial["A"]],
            color=color,
            linewidth=1.7,
            alpha=0.8,
        )
        left.scatter(
            [(epsilon_low + epsilon_high) / 2.0],
            [axial["A"]],
            s=22 + 5 * q,
            color=color,
            edgecolor=background,
            linewidth=0.5,
        )
        left.annotate(
            f"q{q}/{kappa:g}",
            ((epsilon_low + epsilon_high) / 2.0, axial["A"]),
            xytext=(3, 3),
            textcoords="offset points",
            color=muted,
            fontsize=5.8,
        )
    left.set_xlabel("measured ε_geo interval", color=ink)
    left.set_ylabel("measured axial A", color=ink)
    left.set_title("POST-RUN COORDINATE MAP", color=ink, loc="left", fontsize=12)

    right = axes[1]
    markers = {"axial": "o", "face-diagonal": "s", "body-diagonal": "^"}
    for direction, marker in markers.items():
        alphas = [
            cell["sigma_by_direction"][direction]["alpha"] for cell in cells
        ]
        amplitudes = [
            cell["sigma_by_direction"][direction]["A"] for cell in cells
        ]
        colors = [
            sealed
            if cell["sigma_by_direction"][direction]["verdict"] == "FAIL"
            else cyan
            for cell in cells
        ]
        right.scatter(
            alphas,
            amplitudes,
            marker=marker,
            c=colors,
            s=34,
            alpha=0.8,
            label=direction,
        )
    right.set_xlabel("measured α", color=ink)
    right.set_ylabel("measured A", color=ink)
    right.set_title("σ=(α,A) · THREE FROZEN RAYS", color=ink, loc="left", fontsize=12)
    if cells:
        legend = right.legend(facecolor=panel, edgecolor=line, fontsize=8)
        for text in legend.get_texts():
            text.set_color(ink)
    else:
        for axis in axes:
            axis.text(
                0.5,
                0.5,
                "NO VALID COORDINATES\nHALT-PILOT-INVALID",
                transform=axis.transAxes,
                ha="center",
                va="center",
                color=sealed,
                fontsize=12,
                family="monospace",
            )

    figure.suptitle(
        "COMPUTATIONAL UNIVERSE LAB  /  M3′ 30-CELL PILOT",
        color=ink,
        fontsize=16,
        x=0.06,
        ha="left",
    )
    figure.text(
        0.06,
        0.925,
        "q and κ are construction labels; ε_geo and σ are measured after real-space execution.",
        color=muted,
        fontsize=9,
    )
    figure.text(
        0.94,
        0.035,
        payload["status"],
        color=sealed if payload["status"].startswith("HALT") else cyan,
        fontsize=10,
        ha="right",
        family="monospace",
    )
    figure.tight_layout(rect=(0.04, 0.06, 0.97, 0.89))
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURE_PATH, dpi=160, facecolor=background)
    plt.close(figure)


def run() -> dict[str, Any]:
    run_started = time.perf_counter()
    audit = audit_inputs()
    if not audit["pass"]:
        failed = [name for name, passed in audit["checks"].items() if not passed]
        raise RuntimeError(f"Round 0 lineage audit failed: {failed}")

    input_records = audit["file_records"]
    current_protocol = _protocol_record()
    if current_protocol["frozen_verification"]["pass"] is not True:
        raise RuntimeError("frozen evaluator/source SHA verification failed")
    if RESULT_PATH.is_file():
        payload = _read_json(RESULT_PATH)
        checkpoint = validate_checkpoint(
            payload,
            audit["state"],
            audit["manifest_cells"],
            sha256_file(RESULT_PATH),
        )
        if not checkpoint["pass"]:
            raise RuntimeError(
                f"pilot checkpoint is inconsistent: {checkpoint['failures']}"
            )
        decision = validate_existing_payload(
            payload,
            input_records,
            current_protocol,
        )
        if not decision["pass"]:
            raise RuntimeError(
                f"existing pilot result cannot resume: {decision['failures']}"
            )
        if decision["action"] == "halt-resource":
            return payload
        if decision["action"] == "complete":
            if not FIGURE_PATH.is_file():
                make_figure(payload)
            return payload
        if decision["action"] == "finalize-runner-amendment":
            payload["finalization_amendment"] = {
                "kind": "runner-only JSON nonfinite recovery finalizer",
                "reason": (
                    "30/30 measured cells were persisted under the original "
                    "protocol; JSON-safe 'inf' diagnostics must be restored "
                    "before the preregistered 2-sigma meta-judge."
                ),
                "old_runner_sha256": decision["old_runner_sha256"],
                "new_runner_sha256": decision["new_runner_sha256"],
                "scientific_protocol_unchanged": True,
                "measurement_cells_reexecuted": False,
                "applied_utc": datetime.now(timezone.utc).isoformat(),
            }
    else:
        payload = {
            "_schema": "v2m3_pilot v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "generator": "experiments/v2m3_pilot.py",
            "backend": "numpy fp64 CPU",
            "environment": {
                **INV.environment_record(),
                "platform_short": platform.platform(),
            },
            "round": 1,
            "status": "RUNNING-PILOT",
            "main_pilot_executed": False,
            "formal_preregistration_unlocked": False,
            "formal_scan_unlocked": False,
            "claim_ceiling": (
                "30-cell pilot resolvability only; never an M3′ PASS"
            ),
            "inputs": input_records,
            "manifest": {
                "cell_count": 30,
                "cells": audit["manifest_cells"],
                "manifest_sha256": audit["preflight"]["pilot_manifest"][
                    "manifest_sha256"
                ],
            },
            "protocol": current_protocol,
            "cells": [],
            "resource_ledger": {
                "cumulative_wall_seconds": 0.0,
                "peak_rss_bytes": _peak_rss_bytes(),
                "wall_definition": (
                    "cumulative end-to-end runner segments through the latest checkpoint"
                ),
                "resume_safe": True,
            },
        }

    prior_wall_seconds = float(
        payload.get("resource_ledger", {}).get(
            "cumulative_wall_seconds",
            0.0,
        )
    )
    prior_peak_rss_bytes = int(
        payload.get("resource_ledger", {}).get("peak_rss_bytes", 0)
    )
    completed = {cell["cell_id"] for cell in payload["cells"]}
    for manifest_cell in audit["manifest_cells"]:
        if manifest_cell["cell_id"] in completed:
            continue
        cell = measure_manifest_cell(manifest_cell)
        payload["cells"].append(cell)
        payload["status"] = "RUNNING-PILOT"
        _update_resource_ledger(
            payload,
            prior_wall_seconds,
            prior_peak_rss_bytes,
            run_started,
        )

        if len(payload["cells"]) == 1:
            extrapolated_wall = 30.0 * cell["runtime"]["wall_seconds"]
            payload["resource_preflight"] = _resource_review(
                extrapolated_wall,
                payload["resource_ledger"]["peak_rss_bytes"],
                extrapolated=True,
            )
            if not payload["resource_preflight"]["pass"]:
                payload["status"] = "HALT-PILOT-RESOURCE"

        _write_json_atomic(RESULT_PATH, payload)
        _write_json_atomic(STATE_PATH, _partial_state(payload, input_records))
        print(
            f"[{len(payload['cells']):02d}/30] {cell['cell_id']} "
            f"valid={cell['valid']} wall={cell['runtime']['wall_seconds']:.3f}s"
        )
        if payload["status"] == "HALT-PILOT-RESOURCE":
            return payload

    _update_resource_ledger(
        payload,
        prior_wall_seconds,
        prior_peak_rss_bytes,
        run_started,
    )
    provisional_resource_review = _resource_review(
        payload["resource_ledger"]["cumulative_wall_seconds"],
        payload["resource_ledger"]["peak_rss_bytes"],
        extrapolated=False,
    )
    # Execute the meta-judge once before freezing its resource record, so the
    # final cumulative wall includes the judge itself.  The second invocation
    # below is the sole authoritative verdict and uses that refreshed record.
    PILOT.assess_resolvability(
        payload["cells"],
        provisional_resource_review,
    )
    _update_resource_ledger(
        payload,
        prior_wall_seconds,
        prior_peak_rss_bytes,
        run_started,
    )
    resource_review = _resource_review(
        payload["resource_ledger"]["cumulative_wall_seconds"],
        payload["resource_ledger"]["peak_rss_bytes"],
        extrapolated=False,
    )
    resource_review["wall_definition"] = (
        "cumulative end-to-end runner segments through the final meta-judge"
    )
    resolvability = PILOT.assess_resolvability(
        payload["cells"],
        resource_review,
    )
    payload["resource_review"] = resource_review
    payload["resolvability"] = resolvability
    payload["summary"] = _summary(payload["cells"])
    payload["status"] = resolvability["status"]
    payload["main_pilot_executed"] = True
    payload["formal_preregistration_unlocked"] = resolvability[
        "formal_preregistration_unlocked"
    ]
    payload["formal_scan_unlocked"] = False
    payload["completed_utc"] = datetime.now(timezone.utc).isoformat()
    payload["next_action"] = (
        "另行冻结 10²–10³ 正式扫描预注册；本轮不得直接运行"
        if payload["formal_preregistration_unlocked"]
        else "回 M0′ evaluator/构造族追因；禁止扩展正式扫描"
    )
    _write_json_atomic(RESULT_PATH, payload)
    result_sha = sha256_file(RESULT_PATH)
    final_state = {
        "_schema": "v2m3_state v3",
        "generated_utc": payload["completed_utc"],
        "generator": payload["generator"],
        "lit": False,
        "status": payload["status"],
        "round": 1,
        "main_pilot_unlocked": False,
        "main_pilot_executed": True,
        "completed_cells": len(payload["cells"]),
        "pilot_manifest_cell_count": 30,
        "pilot_inputs": input_records,
        "result": {
            "path": str(RESULT_PATH.relative_to(ROOT)),
            "sha256": result_sha,
        },
        "formal_preregistration_unlocked": payload[
            "formal_preregistration_unlocked"
        ],
        "formal_scan_unlocked": False,
        "next_unlock_condition": payload["next_action"],
        "wording": (
            "M3′ 30 格 pilot 已执行；该结果不是 M3′ PASS，正式扫描仍锁定。"
        ),
    }
    _write_json_atomic(STATE_PATH, final_state)
    make_figure(payload)
    return payload


def main() -> int:
    payload = run()
    print("=" * 72)
    print(f"status: {payload['status']}")
    print(f"cells: {len(payload.get('cells', []))}/30")
    print(f"formal_scan_unlocked: {payload.get('formal_scan_unlocked', False)}")
    return 0 if payload.get("main_pilot_executed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
