#!/usr/bin/env python3
"""Run and create, exactly once, a non-authoritative Task-11 raw artifact.

This is intentionally a historical-Parent numerical replay.  The output is
always labelled ``NOT_ISSUED`` and cannot unlock current-Parent-v2 Task 12.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rulespace_v3.task11_evidence import (  # noqa: E402
    TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA,
    TASK11_RAW_REPLAY_REPOSITORY_MEASUREMENT_SCOPE,
    TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS,
    TASK11_RAW_REPLAY_SCOPE,
    build_task11_raw_replay_evidence_payload,
    verify_task11_raw_replay_evidence_payload,
)


DEFAULT_OUTPUT = ROOT / "data" / "results" / "v3m0_task11_raw_replay.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_output_bytes(*arguments: str) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def _git_output(*arguments: str) -> str:
    return _git_output_bytes(*arguments).decode("utf-8").strip()


def _source_provenance(command: tuple[str, ...]) -> dict[str, object]:
    from rulespace_v3.runtime import (
        issue_runtime_evidence_manifest,
        runtime_evidence_manifest_to_wire,
    )

    if (
        type(command) is not tuple
        or not command
        or not all(type(item) is str and item for item in command)
    ):
        raise TypeError("command must be a non-empty exact string tuple")
    status_porcelain = _git_output_bytes(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    return {
        "git_head": _git_output("rev-parse", "HEAD"),
        "git_worktree_dirty": bool(status_porcelain),
        "git_status_porcelain_sha256": hashlib.sha256(status_porcelain).hexdigest(),
        "source_files": [
            {
                "relative_path": relative_path,
                "sha256": _sha256_file(ROOT / relative_path),
            }
            for relative_path in TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS
        ],
        "runtime_manifest": runtime_evidence_manifest_to_wire(
            issue_runtime_evidence_manifest()
        ),
        "repository_measurement_scope": (
            TASK11_RAW_REPLAY_REPOSITORY_MEASUREMENT_SCOPE
        ),
        "command": list(command),
    }


def _execute_with_stable_source_provenance(
    command: tuple[str, ...],
    execute: Callable[[dict[str, object]], object],
    *,
    measure: Callable[[tuple[str, ...]], dict[str, object]] = _source_provenance,
) -> object:
    """Bracket one execution with exact repository/runtime measurements."""

    before = measure(command)
    result = execute(before)
    after = measure(command)
    if before != after:
        raise RuntimeError(
            "Task-11 replay source/runtime provenance drifted during execution"
        )
    return result


def execute_raw_historical_replay(
    *,
    command: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Execute and production-validate one non-authoritative raw artifact."""

    from rulespace_v3.current_window_replay import (
        _build_current_window_calibration_protocol_v2_body,
        current_window_calibration_protocol_v2_payload,
    )
    from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
    from rulespace_v3.parent_freeze_v2 import (
        _build_reviewed_unchanged_scenario_authorities,
    )
    from rulespace_v3.task11_runner import (
        _build_task11_numerical_roots,
        _run_task11_window_calibration_from_replay,
    )
    from rulespace_v3.task8_control_replay import (
        _build_current_control_registry_v2_body,
        _replay_current_task8_control_roots,
        current_control_registry_v2_payload,
    )

    launch_command = (
        tuple(sys.orig_argv)
        if command is None and getattr(sys, "orig_argv", None)
        else tuple(sys.argv)
        if command is None
        else command
    )

    def numerical_replay(source: dict[str, object]) -> dict[str, object]:
        parent = issue_v3m0_parent_freeze()
        authorities = tuple(
            item
            for item in _build_reviewed_unchanged_scenario_authorities()
            if item.control_case_id.startswith(("C01_", "C02_", "C03_"))
        )
        if len(authorities) != 3:
            raise RuntimeError("raw Task-11 replay did not resolve C01-C03 exactly")
        replay = _replay_current_task8_control_roots(parent, authorities)
        current_registry = _build_current_control_registry_v2_body(
            TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA,
            replay,
        )
        current_window = _build_current_window_calibration_protocol_v2_body(
            current_registry,
            replay,
        )
        outcome = _run_task11_window_calibration_from_replay(
            parent,
            replay,
            current_registry,
            current_window,
        )
        registry_cap, protocol_cap = _build_task11_numerical_roots(
            parent,
            replay,
            current_registry,
            current_window,
        )
        current_registry_wire = {
            **current_control_registry_v2_payload(current_registry),
            "registry_sha": current_registry.registry_sha,
        }
        current_window_wire = {
            **current_window_calibration_protocol_v2_payload(current_window),
            "protocol_sha": current_window.protocol_sha,
        }
        provenance = {
            "replay_scope": TASK11_RAW_REPLAY_SCOPE,
            "historical_parent_v1_sha": parent.manifest.parent_freeze_sha,
            "placeholder_parent_freeze_v2_sha": (
                TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA
            ),
            "legacy_registry_sha": replay.legacy_registry.registry.registry_sha,
            "current_control_registry_sha": current_registry.registry_sha,
            "legacy_window_protocol_sha": (
                current_window.legacy_window_protocol.protocol_sha
            ),
            "current_window_protocol_sha": current_window.protocol_sha,
            "current_control_registry": current_registry_wire,
            "current_window_protocol": current_window_wire,
            "scenario_authority_shas": [
                item.scenario_authority_sha for item in authorities
            ],
            **source,
        }
        return build_task11_raw_replay_evidence_payload(
            outcome,
            registry_cap,
            protocol_cap,
            provenance=provenance,
        )

    return _execute_with_stable_source_provenance(
        launch_command,
        numerical_replay,
    )


def write_task11_raw_replay_evidence_create_only(
    path: Path,
    payload: Mapping[str, object],
) -> None:
    """Publish a verified JSON file atomically and refuse every overwrite."""

    if not isinstance(path, Path):
        raise TypeError("Task-11 output path must be a pathlib.Path")
    if not path.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {path.parent}")
    if os.path.lexists(path):
        raise FileExistsError(f"Task-11 evidence already exists: {path}")
    verified = verify_task11_raw_replay_evidence_payload(payload)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            os.fchmod(stream.fileno(), 0o644)
            json.dump(
                verified,
                stream,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        temporary.unlink()
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def run_raw_replay(
    output: Path,
    *,
    command: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Preflight create-only policy before starting the expensive execution."""

    if not isinstance(output, Path):
        raise TypeError("Task-11 output path must be a pathlib.Path")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {output.parent}")
    if os.path.lexists(output):
        raise FileExistsError(f"Task-11 evidence already exists: {output}")
    evidence = execute_raw_historical_replay(command=command)
    write_task11_raw_replay_evidence_create_only(output, evidence)
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "运行历史 Parent 的 Task-11 原始数值复放并 create-only 落盘；"
            "该结果不是 current-Parent-v2 科学签发件。"
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"create-only JSON 路径（默认：{DEFAULT_OUTPUT}）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    launch_arguments = sys.argv[1:] if argv is None else argv
    command = (
        sys.executable,
        str(Path(__file__).resolve()),
        *launch_arguments,
    )
    evidence = run_raw_replay(
        arguments.output,
        command=command,
    )
    print(
        json.dumps(
            {
                "输出": str(arguments.output),
                "权威状态": evidence["authority_state"],
                "科学裁定": evidence["scientific_verdict"],
                "数值终态": evidence["outcome"]["status"],
                "evidence_sha": evidence["evidence_sha"],
            },
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
