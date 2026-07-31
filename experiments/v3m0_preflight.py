#!/usr/bin/env python3
"""Write the current V3-M0 control/state checkpoint without physical anchors."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rulespace_v3.evidence import canonical_sha  # noqa: E402

from experiments.v3m0_controls import (  # noqa: E402
    V3M0CapabilityBundle,
    V3M0ControlAssembly,
    assemble_v3m0_controls,
    control_assembly_to_wire,
)


DEFAULT_PHASE0 = ROOT / "data" / "results" / "v3m0_formal_nogo.json"
DEFAULT_RESULT = ROOT / "data" / "results" / "v3m0_controls.json"
DEFAULT_STATE = ROOT / "data" / "runtime" / "v3m0_state.json"
V3M0_STATE_EVIDENCE_SCHEMA_VERSION = "v3m0.state-evidence.v1"
EXPECTED_PHASE0_CERTIFICATE_SHA = (
    "01fc27a26778058cb7567251d5fd2550408b11f30a119c7c08dfb9528f74962f"
)

FORBIDDEN_HISTORICAL_FACTORY_MODULES = frozenset(
    (
        "photon_control",
        "r23_maxwell_control",
        "r30_tensor_complex_dynamical",
        "r25_realspace_step",
        "r25_dynamic_symbol",
        "r25_auxiliary_wilson_complex",
    )
)


def _json_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _stage_bytes(path: Path, content: bytes) -> Path:
    if not path.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {path.parent}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise
    return temporary


def _fsync_directories(paths: tuple[Path, ...]) -> None:
    seen: set[Path] = set()
    for path in paths:
        parent = path.parent.resolve()
        if parent in seen:
            continue
        seen.add(parent)
        descriptor = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _result_and_state_payloads(
    assembly: V3M0ControlAssembly,
) -> tuple[dict[str, object], dict[str, object]]:
    result_body = control_assembly_to_wire(assembly)
    result_sha = canonical_sha(result_body)
    result = {**result_body, "result_sha": result_sha}
    first_undefined = assembly.decision.first_undefined
    state = {
        "schema_version": V3M0_STATE_EVIDENCE_SCHEMA_VERSION,
        "state": assembly.decision.state.value,
        "ready": assembly.decision.ready,
        "result_sha": result_sha,
        "first_undefined": (
            None
            if first_undefined is None
            else {
                "block_id": first_undefined[0],
                "reason": first_undefined[1].value,
            }
        ),
        "formal_all_pass": assembly.formal_all_pass,
        "exact_all_pass": assembly.exact_all_pass,
        "identifiability_all_pass": assembly.identifiability_all_pass,
        "all_block_success_artifacts_verified": (
            assembly.all_block_success_artifacts_verified
        ),
        "all_required_controls_pass": assembly.all_required_controls_pass,
        "all_expected_terminations_verified": (
            assembly.all_expected_terminations_verified
        ),
        "all_analysis_controls_verified": (
            assembly.all_analysis_controls_verified
        ),
        "representation_invariants_pass": (
            assembly.representation_invariants_pass
        ),
        "no_unexpected_downstream_capability": (
            assembly.no_unexpected_downstream_capability
        ),
        "no_physical_anchor_run": assembly.no_physical_anchor_run,
    }
    return result, state


def write_preflight_outputs(
    assembly: V3M0ControlAssembly,
    *,
    result_path: Path,
    state_path: Path,
) -> None:
    """Stage, fsync, and atomically replace both linked evidence records."""

    if type(assembly) is not V3M0ControlAssembly:
        raise TypeError("assembly must be an exact V3M0ControlAssembly")
    if not isinstance(result_path, Path) or not isinstance(state_path, Path):
        raise TypeError("result_path and state_path must be pathlib.Path values")
    if result_path.resolve() == state_path.resolve():
        raise ValueError("result and state targets must be distinct")
    result, state = _result_and_state_payloads(assembly)
    staged: list[Path] = []
    try:
        result_temporary = _stage_bytes(result_path, _json_bytes(result))
        staged.append(result_temporary)
        state_temporary = _stage_bytes(state_path, _json_bytes(state))
        staged.append(state_temporary)
        os.replace(result_temporary, result_path)
        staged.remove(result_temporary)
        os.replace(state_temporary, state_path)
        staged.remove(state_temporary)
        _fsync_directories((result_path, state_path))
    except BaseException:
        for temporary in staged:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        raise


def _read_phase0_flags(path: Path) -> tuple[bool, bool, bool]:
    """Read the frozen Phase-0 artifact; never import its historical closure."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if type(payload) is not dict:
            return False, False, False
        certificate_sha = payload.get("certificate_sha")
        body = dict(payload)
        body.pop("certificate_sha", None)
        digest_ok = (
            type(certificate_sha) is str
            and certificate_sha == EXPECTED_PHASE0_CERTIFICATE_SHA
            and certificate_sha == canonical_sha(body)
        )
        gates = payload.get("gates")
        if type(gates) is not dict:
            return False, False, False
        gates_all_pass = bool(gates) and all(
            type(value) is bool and value for value in gates.values()
        )
        ready = (
            digest_ok
            and gates_all_pass
            and payload.get("status") == "READY-V3M0-CONTROLS"
        )
        formal = payload.get("formal")
        formal_pass = (
            ready
            and type(formal) is dict
            and formal.get("build_pass") is True
            and formal.get("forbidden_token_pass") is True
            and formal.get("lean_version_pass") is True
        )
        exact_pass = ready and gates.get("exact_reconstruction") is True
        identifiability_pass = (
            ready and gates.get("whitened_coisometry_90") is True
        )
        return formal_pass, exact_pass, identifiability_pass
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False, False, False


def _historical_factory_scope_is_clean() -> bool:
    loaded_leaves = {name.split(".")[-1] for name in sys.modules}
    return FORBIDDEN_HISTORICAL_FACTORY_MODULES.isdisjoint(loaded_leaves)


def build_current_checkpoint(
    phase0_path: Path = DEFAULT_PHASE0,
) -> V3M0ControlAssembly:
    formal, exact, identifiable = _read_phase0_flags(phase0_path)
    return assemble_v3m0_controls(
        formal_all_pass=formal,
        exact_all_pass=exact,
        identifiability_all_pass=identifiable,
        capabilities=V3M0CapabilityBundle(),
        control_results=(),
        invariant_results=(),
        evidence=None,
        no_physical_anchor_run=_historical_factory_scope_is_clean(),
    )


def _check_file(path: Path, expected: bytes) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.read_bytes() != expected:
        raise ValueError(f"stored checkpoint differs from assembly: {path}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--phase0", type=Path, default=DEFAULT_PHASE0)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--state-output", type=Path, default=DEFAULT_STATE)
    arguments = parser.parse_args(argv)

    assembly = build_current_checkpoint(arguments.phase0)
    if arguments.generate:
        write_preflight_outputs(
            assembly,
            result_path=arguments.output,
            state_path=arguments.state_output,
        )
    else:
        result, state = _result_and_state_payloads(assembly)
        _check_file(arguments.output, _json_bytes(result))
        _check_file(arguments.state_output, _json_bytes(state))
    print(
        f"{assembly.decision.state.value} "
        f"undefined={len(assembly.required_blocks.undefined)} "
        "physical_anchor_run=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DEFAULT_PHASE0",
    "DEFAULT_RESULT",
    "DEFAULT_STATE",
    "EXPECTED_PHASE0_CERTIFICATE_SHA",
    "FORBIDDEN_HISTORICAL_FACTORY_MODULES",
    "V3M0_STATE_EVIDENCE_SCHEMA_VERSION",
    "build_current_checkpoint",
    "main",
    "write_preflight_outputs",
]
