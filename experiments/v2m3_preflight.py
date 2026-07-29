"""M3′ Round 0 read-only certificate and family-admission preflight.

This probe may unlock the 30-cell pilot, but it never runs that pilot.  Under
the current repository state it is expected to stop at family admission
because RC3-(ii) R2 is spectral bookkeeping, not an executable strict-local
real-space family.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone
from typing import Any

os.environ.setdefault("RULESPACE_BACKEND", "numpy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rulespace_v2.m3_family import (  # noqa: E402
    Q_LEVELS,
    audit_family_descriptor,
    build_pilot_manifest,
    legacy_rc3ii_descriptor,
)

RESULT_PATH = ROOT / "data" / "results" / "v2m3_preflight.json"
STATE_PATH = ROOT / "data" / "runtime" / "v2m3_state.json"

PINNED_SHA256 = {
    "docsv2/v2-收口-M2-2026-07-27.md": (
        "f791c355bd57d49f9c7b63ee733631c4c13dfe06d8ea611d05e73c28a4ed88d8"
    ),
    "data/runtime/v2m2_state.json": (
        "c4a518a4206d4e2bdf6590a0b0a8607baabb395a308a14b2510cc32e66831835"
    ),
    "experiments/rc3ii_relaxation_framework.py": (
        "23cfc187db9454f5a89bb1b7467db6887efd465b8cbe964ec74633ce54a994a6"
    ),
    "data/results/rc3ii_results.json": (
        "89c58556da3d8ad1cdbda36d92600102c57e37deafb2ab2bf73efaa8a2207be6"
    ),
    "experiments/v2m2_coupled_loop.py": (
        "e3ae75932511f36e63f1775d3dc732808af1a4f3902f98922dc6099ffa263078"
    ),
    "data/results/v2m2_guns.json": (
        "86608e6098a2d3cd2e72afc14cde5c4839e388e348be2f259c8e541321b16b82"
    ),
}

EXPECTED_N_PROP = {
    "axis": [4, 4, 3, 3, 2],
    "face": [4, 4, 3, 2, 2],
    "body": [4, 3, 3, 2, 2],
}

R2_DIRECTION_KEYS = {
    "axis": "(2, 0, 0)",
    "face": "(2, 2, 0)",
    "body": "(2, 2, 2)",
}


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _json_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def audit_upstream_certificates() -> dict[str, Any]:
    pins: dict[str, dict[str, Any]] = {}
    for relative_path, expected in PINNED_SHA256.items():
        path = ROOT / relative_path
        actual = sha256_file(path) if path.is_file() else None
        pins[relative_path] = {
            "expected_sha256": expected,
            "actual_sha256": actual,
            "match": actual == expected,
        }

    state_path = ROOT / "data" / "runtime" / "v2m2_state.json"
    state_error = None
    try:
        m2_state = _json_file(state_path)
    except (OSError, ValueError, TypeError) as exc:
        m2_state = {}
        state_error = f"{type(exc).__name__}: {exc}"

    gate_columns = m2_state.get("gate_columns", {})
    gate_verdicts = {
        name: (
            gate_columns.get(name, {}).get("verdict")
            if isinstance(gate_columns, dict)
            else None
        )
        for name in (f"M2-G{i}" for i in range(1, 9))
    }
    checks = {
        "pinned_sha256": all(item["match"] for item in pins.values()),
        "m2_lit": m2_state.get("lit") is True,
        "m2_gates_8_of_8": all(
            verdict == "PASS" for verdict in gate_verdicts.values()
        ),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "pins": pins,
        "m2_gate_verdicts": gate_verdicts,
        "m2_state_error": state_error,
        "note": (
            "M2 runtime prose retains historical pending text; the authoritative "
            "machine fields are lit=true and eight PASS gate verdicts."
        ),
    }


def audit_topology_anchor() -> dict[str, Any]:
    try:
        from rulespace_v2.frozen import mod

        rc3ii = mod("rc3ii_relaxation_framework")
        r2 = rc3ii.candidate_R2(rc3ii.C0)
        per_k = r2["per_k"]
        observed = {
            direction: [
                int(per_k[key]["N_prop_by_handbuilt_count"][str(q)])
                for q in Q_LEVELS
            ]
            for direction, key in R2_DIRECTION_KEYS.items()
        }
        metadata = {
            direction: {
                "source_k": key,
                "min_handbuilt_DOF_for_2": per_k[key][
                    "min_handbuilt_DOF_for_2"
                ],
                "handbuilt_fraction": per_k[key]["handbuilt_fraction"],
                "TT_emergent_energy": per_k[key]["TT_emergent_energy"],
            }
            for direction, key in R2_DIRECTION_KEYS.items()
        }
        error = None
    except Exception as exc:  # preserve a diagnostic result instead of a partial run
        observed = {}
        metadata = {}
        error = f"{type(exc).__name__}: {exc}"

    checks = {
        direction: observed.get(direction) == expected
        for direction, expected in EXPECTED_N_PROP.items()
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "expected_N_prop_by_q": EXPECTED_N_PROP,
        "observed_N_prop_by_q": observed,
        "metadata": metadata,
        "error": error,
        "interpretation": (
            "This reproduces the frozen RC3-(ii) topology ledger only. "
            "It does not make R2 an executable real-space family."
        ),
    }


def _pilot_manifest_record() -> dict[str, Any]:
    cells = [cell.as_dict() for cell in build_pilot_manifest()]
    canonical = json.dumps(
        cells, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "cell_count": len(cells),
        "q_levels": list(Q_LEVELS),
        "kappa_c_levels": sorted({cell["kappa_c"] for cell in cells}),
        "eta_core": 0.0,
        "epsilon_mat_fixed": 1.0,
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "cells": cells,
        "measured_coordinates_present": False,
    }


def evaluate_preflight() -> dict[str, Any]:
    """Evaluate Round 0 without writing files or running the main pilot."""

    upstream = audit_upstream_certificates()
    topology = audit_topology_anchor()
    manifest = _pilot_manifest_record()
    legacy_descriptor = legacy_rc3ii_descriptor()
    family_admission = audit_family_descriptor(legacy_descriptor)

    if not upstream["pass"]:
        status = "HALT-UPSTREAM-CERTIFICATE"
    elif not topology["pass"]:
        status = "HALT-TOPOLOGY-ANCHOR"
    elif not family_admission["pass"]:
        status = "HALT-FAMILY-ADMISSION"
    else:
        status = "READY-PILOT"

    return {
        "_schema": "v2m3_preflight v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "experiments/v2m3_preflight.py",
        "backend": "numpy fp64",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "taskbook": "docsv2/v2-任务书-M3-涌现边界制图.md",
        "round": 0,
        "status": status,
        "main_pilot_unlocked": status == "READY-PILOT",
        "main_pilot_executed": False,
        "claim_ceiling": (
            "family-admission preflight only; neither M3′ PASS nor M3′ FAIL"
        ),
        "upstream_certificates": upstream,
        "topology_anchor": topology,
        "pilot_manifest": manifest,
        "family_descriptor": legacy_descriptor,
        "family_admission": family_admission,
        "next_unlock_condition": (
            "Provide one same-state-space strict-local real-space q-family with "
            "an executable step factory, explicit local shears, L-independent "
            "support, fp64 unitarity <=1e-12, no per-k projection, and measured "
            "rather than injected epsilon_geo/sigma coordinates."
        ),
        "eta_diagnostic": {
            "part_of_core_map": False,
            "locked_until_core_stable_point": True,
            "future_levels": [0.05, 0.10],
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_outputs(result: dict[str, Any]) -> dict[str, Any]:
    """Write the preflight evidence and recoverable state, without reset semantics."""

    _write_json(RESULT_PATH, result)
    result_sha256 = sha256_file(RESULT_PATH)
    state = {
        "_schema": "v2m3_state v1",
        "generated_utc": result["generated_utc"],
        "generator": result["generator"],
        "lit": False,
        "status": result["status"],
        "round": result["round"],
        "main_pilot_unlocked": result["main_pilot_unlocked"],
        "main_pilot_executed": result["main_pilot_executed"],
        "pilot_manifest_cell_count": result["pilot_manifest"]["cell_count"],
        "result": {
            "path": str(RESULT_PATH.relative_to(ROOT)),
            "sha256": result_sha256,
        },
        "next_unlock_condition": result["next_unlock_condition"],
        "wording": (
            "M3′ Round 0 started. M3′ has neither passed nor failed; "
            "the main pilot was not run."
        ),
    }
    _write_json(STATE_PATH, state)
    return state


def main() -> int:
    result = evaluate_preflight()
    state = write_outputs(result)
    print(
        f"M3′ Round 0: {result['status']} | "
        f"upstream={result['upstream_certificates']['pass']} | "
        f"topology={result['topology_anchor']['pass']} | "
        f"family={result['family_admission']['pass']} | "
        f"pilot_unlocked={result['main_pilot_unlocked']}"
    )
    print(
        f"wrote {RESULT_PATH.relative_to(ROOT)} "
        f"(sha256={state['result']['sha256']})"
    )
    print(f"wrote {STATE_PATH.relative_to(ROOT)}")
    return 0 if result["status"] == "READY-PILOT" else 2


if __name__ == "__main__":
    sys.exit(main())
