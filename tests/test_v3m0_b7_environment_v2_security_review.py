"""Independent adversarial review of the B7 v9.2 environment runtime."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from rulespace_v3.b7_replay_core_v1 import canonical_json_bytes_v1


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _actual_venv_identity() -> dict[str, str]:
    invocation = Path(sys.executable)
    target = Path(os.path.realpath(invocation))
    prefix = Path(sys.prefix)
    pyvenv_cfg = prefix / "pyvenv.cfg"
    return {
        "python_invocation_path": str(invocation),
        "recorded_realpath": str(target),
        "recorded_raw_sha256": _sha256(target),
        "recorded_venv_prefix": str(prefix),
        "recorded_pyvenv_cfg_path": str(pyvenv_cfg),
        "recorded_pyvenv_cfg_raw_sha256": _sha256(pyvenv_cfg),
    }


def _identity_for_chain(invocation: Path, target: Path, prefix: Path) -> dict[str, str]:
    cfg = prefix / "pyvenv.cfg"
    return {
        "python_invocation_path": str(invocation),
        "recorded_realpath": str(target),
        "recorded_raw_sha256": _sha256(target),
        "recorded_venv_prefix": str(prefix),
        "recorded_pyvenv_cfg_path": str(cfg),
        "recorded_pyvenv_cfg_raw_sha256": _sha256(cfg),
    }


def _probe_report(identity: dict[str, str]) -> dict[str, object]:
    return {
        "byteorder": sys.byteorder,
        "numpy_float64_dtype_str": "<f8" if sys.byteorder == "little" else ">f8",
        "numpy_float64_itemsize": 8,
        "numpy_version": "review",
        "platform_machine": "review",
        "platform_release": "review",
        "platform_system": "review",
        "python_executable_realpath": identity["recorded_realpath"],
        "python_implementation": "CPython",
        "python_invocation_path": identity["python_invocation_path"],
        "python_venv_prefix": identity["recorded_venv_prefix"],
        "python_version": "review",
        "scipy_version": "review",
        "threadpool_info": [],
    }


def _process_observation(
    stdout: bytes,
    *,
    stderr: bytes = b"",
    exit_code: int = 0,
) -> dict[str, object]:
    return {
        "replay_termination_kind": "EXITED",
        "replay_exit_code": exit_code,
        "replay_signal_number": None,
        "replay_stdout_bytes": stdout,
        "replay_stderr_bytes": stderr,
        "replay_stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "replay_stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "process_cleanup_deadline_exceeded": False,
    }


def test_v92_rejects_unobserved_parent_directory_symlink_alias(
    tmp_path: Path,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
    )

    real_prefix = tmp_path / "real-venv"
    (real_prefix / "bin").mkdir(parents=True)
    target = real_prefix / "bin" / "python"
    target.write_bytes(b"python")
    target.chmod(0o755)
    (real_prefix / "pyvenv.cfg").write_bytes(b"home = frozen\n")
    alias_prefix = tmp_path / "alias-venv"
    alias_prefix.symlink_to(real_prefix, target_is_directory=True)
    aliased_invocation = alias_prefix / "bin" / "python"
    aliased_cfg = alias_prefix / "pyvenv.cfg"

    observed = precheck_python_invocation_identity_v2(
        python_invocation_path=str(aliased_invocation),
        recorded_realpath=str(aliased_invocation),
        recorded_raw_sha256=_sha256(target),
        recorded_venv_prefix=str(alias_prefix),
        recorded_pyvenv_cfg_path=str(aliased_cfg),
        recorded_pyvenv_cfg_raw_sha256=_sha256(aliased_cfg),
    )

    assert observed["precheck_passed"] is False


@pytest.mark.parametrize(
    "hostile_path", ("/tmp/hostile\\python", "/tmp/hostile\x00python")
)
def test_v92_rejects_paths_outside_absolute_normalized_wire_domain(
    hostile_path: str,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
    )

    with pytest.raises(ValueError, match="absolute lexically normalized path"):
        precheck_python_invocation_identity_v2(
            python_invocation_path=hostile_path,
            recorded_realpath="/tmp/python-target",
            recorded_raw_sha256="0" * 64,
            recorded_venv_prefix="/tmp/venv",
            recorded_pyvenv_cfg_path="/tmp/venv/pyvenv.cfg",
            recorded_pyvenv_cfg_raw_sha256="0" * 64,
        )


@pytest.mark.parametrize("symlink_count", (40, 41))
def test_v92_enforces_exact_symlink_hop_boundary(
    tmp_path: Path,
    symlink_count: int,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
    )

    target = tmp_path / "python-target"
    target.write_bytes(b"python")
    target.chmod(0o755)
    (tmp_path / "pyvenv.cfg").write_bytes(b"home = frozen\n")
    links = [tmp_path / f"python-{ordinal:02d}" for ordinal in range(symlink_count)]
    for ordinal, link in enumerate(links):
        destination = (
            links[ordinal + 1].name if ordinal + 1 < len(links) else target.name
        )
        link.symlink_to(destination)

    observed = precheck_python_invocation_identity_v2(
        **_identity_for_chain(links[0], target, tmp_path)
    )

    assert observed["precheck_passed"] is (symlink_count == 40)


def test_v92_rejects_inode_loop_even_below_hop_limit(tmp_path: Path) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
    )

    first = tmp_path / "python-first"
    second = tmp_path / "python-second"
    first.symlink_to(second.name)
    second.symlink_to(first.name)
    cfg = tmp_path / "pyvenv.cfg"
    cfg.write_bytes(b"home = frozen\n")
    observed = precheck_python_invocation_identity_v2(
        python_invocation_path=str(first),
        recorded_realpath=str(first),
        recorded_raw_sha256="0" * 64,
        recorded_venv_prefix=str(tmp_path),
        recorded_pyvenv_cfg_path=str(cfg),
        recorded_pyvenv_cfg_raw_sha256=_sha256(cfg),
    )

    assert observed["precheck_passed"] is False
    assert observed["observed_realpath"] is None


@pytest.mark.parametrize("entry_kind", ("symlink", "fifo"))
def test_v92_rejects_nonregular_nearest_pyvenv_cfg(
    tmp_path: Path,
    entry_kind: str,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
    )

    prefix = tmp_path / "venv"
    (prefix / "bin").mkdir(parents=True)
    target = tmp_path / "python-target"
    target.write_bytes(b"python")
    target.chmod(0o755)
    invocation = prefix / "bin" / "python"
    invocation.symlink_to(target)
    cfg = prefix / "pyvenv.cfg"
    cfg_payload = tmp_path / "cfg-payload"
    cfg_payload.write_bytes(b"home = frozen\n")
    if entry_kind == "symlink":
        cfg.symlink_to(cfg_payload)
    else:
        os.mkfifo(cfg)

    observed = precheck_python_invocation_identity_v2(
        python_invocation_path=str(invocation),
        recorded_realpath=str(target),
        recorded_raw_sha256=_sha256(target),
        recorded_venv_prefix=str(prefix),
        recorded_pyvenv_cfg_path=str(cfg),
        recorded_pyvenv_cfg_raw_sha256=_sha256(cfg_payload),
    )

    assert observed["precheck_passed"] is False
    assert observed["pyvenv_cfg_identity"]["regular_file"] is False


@pytest.mark.parametrize("mutation", ("replace", "grow", "truncate"))
@pytest.mark.parametrize("executable_required", (False, True))
def test_v92_same_fd_hash_rejects_concurrent_file_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    executable_required: bool,
) -> None:
    import experiments.v3m0_b7_schema_lab.compare as compare

    subject = tmp_path / ("python" if executable_required else "pyvenv.cfg")
    subject.write_bytes(b"frozen-bytes")
    if executable_required:
        subject.chmod(0o755)
    replacement = tmp_path / "replacement"
    replacement.write_bytes(b"frozen-bytes")
    if executable_required:
        replacement.chmod(0o755)
    real_read = os.read
    attacked = False

    def attacking_read(file_descriptor: int, size: int) -> bytes:
        nonlocal attacked
        chunk = real_read(file_descriptor, size)
        if not attacked:
            attacked = True
            if mutation == "replace":
                os.replace(replacement, subject)
            elif mutation == "grow":
                with subject.open("ab") as stream:
                    stream.write(b"+")
            else:
                subject.write_bytes(b"")
        return chunk

    monkeypatch.setattr(os, "read", attacking_read)
    observed = compare._stable_regular_file_observation_v2(
        str(subject), executable_required=executable_required
    )

    assert attacked
    assert observed["stable"] is False


def test_v92_probe_totalizes_incomplete_forged_identity() -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        run_python_environment_import_probe_v2,
    )

    invocation = str(Path(sys.executable))
    probe = run_python_environment_import_probe_v2(
        python_invocation_path=invocation,
        python_identity_observation={
            "precheck_passed": True,
            "python_invocation_path": invocation,
        },
    )

    assert probe["probe_passed"] is False
    assert probe["process_observation"]["replay_termination_kind"] == (
        "PRECHECK_FAILED"
    )


def test_v92_recheck_totalizes_non_json_forged_observation() -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
        recheck_python_invocation_identity_v2,
    )

    observed = precheck_python_invocation_identity_v2(**_actual_venv_identity())
    observed["ordered_lstat_hops"] = object()

    assert not recheck_python_invocation_identity_v2(precheck_observation=observed)


@pytest.mark.parametrize(
    ("field", "hostile_value"),
    (
        ("numpy_float64_itemsize", 4),
        ("byteorder", "middle"),
        ("threadpool_info", {}),
        ("python_version", 3),
    ),
)
def test_v92_probe_rejects_invalid_report_field_types_and_literals(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    hostile_value: object,
) -> None:
    import experiments.v3m0_b7_schema_lab.compare as compare

    expected = _actual_venv_identity()
    identity = compare.precheck_python_invocation_identity_v2(**expected)
    report = _probe_report(expected)
    report[field] = hostile_value
    stdout = canonical_json_bytes_v1(report) + b"\n"
    monkeypatch.setattr(
        compare,
        "run_bounded_reviewer_process_v1",
        lambda **_arguments: _process_observation(stdout),
    )

    probe = compare.run_python_environment_import_probe_v2(
        python_invocation_path=expected["python_invocation_path"],
        python_identity_observation=identity,
    )

    assert probe["probe_passed"] is False
    assert probe["report"] is None


@pytest.mark.parametrize(
    ("stdout_mutator", "stderr", "exit_code"),
    (
        (lambda payload: payload, b"", 0),
        (lambda payload: payload + b"\n\n", b"", 0),
        (lambda payload: b" " + payload + b"\n", b"", 0),
        (lambda _payload: b'{"x":1,"x":2}\n', b"", 0),
        (lambda payload: payload + b"\n", b"probe-stderr", 0),
        (lambda payload: payload + b"\n", b"", 1),
    ),
)
def test_v92_probe_rejects_noncanonical_or_failed_process_observations(
    monkeypatch: pytest.MonkeyPatch,
    stdout_mutator,
    stderr: bytes,
    exit_code: int,
) -> None:
    import experiments.v3m0_b7_schema_lab.compare as compare

    expected = _actual_venv_identity()
    identity = compare.precheck_python_invocation_identity_v2(**expected)
    payload = canonical_json_bytes_v1(_probe_report(expected))
    stdout = stdout_mutator(payload)
    monkeypatch.setattr(
        compare,
        "run_bounded_reviewer_process_v1",
        lambda **_arguments: _process_observation(
            stdout, stderr=stderr, exit_code=exit_code
        ),
    )

    probe = compare.run_python_environment_import_probe_v2(
        python_invocation_path=expected["python_invocation_path"],
        python_identity_observation=identity,
    )

    assert probe["probe_passed"] is False
    assert probe["report"] is None


def test_v92_final_recheck_is_observably_adjacent_to_popen(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import experiments.v3m0_b7_schema_lab.compare as compare

    events: list[str] = []
    invocation = str(Path(sys.executable))
    precheck = {
        "profile_id": "v3m0-b7-python-venv-invocation-identity-v1",
        "python_invocation_path": invocation,
    }

    def recheck(*, precheck_observation) -> bool:
        assert precheck_observation is precheck
        events.append("recheck")
        return True

    def popen(*_args, **_kwargs):
        events.append("popen")
        raise OSError("review sentinel")

    monkeypatch.setattr(compare, "recheck_python_invocation_identity_v2", recheck)
    monkeypatch.setattr(subprocess, "Popen", popen)
    observed = compare.run_bounded_reviewer_process_v1(
        argv=(invocation, "-s", "-c", "pass"),
        cwd=str(tmp_path),
        environment={},
        timeout_seconds=1,
        stdout_hard_cap_bytes=1,
        stderr_hard_cap_bytes=1,
        io_chunk_bytes=1,
        term_grace_seconds=1,
        kill_grace_seconds=1,
        final_pipe_close_deadline_seconds=1,
        python_precheck_observation=precheck,
    )

    assert events == ["recheck", "popen"]
    assert observed["replay_termination_kind"] == "SPAWN_FAILED"


def test_v92_argv0_swap_rejects_before_recheck_or_spawn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import experiments.v3m0_b7_schema_lab.compare as compare

    events: list[str] = []
    expected_invocation = str(Path(sys.executable))
    hostile_argv0 = str(tmp_path / "python-other")
    precheck = {
        "profile_id": "v3m0-b7-python-venv-invocation-identity-v1",
        "python_invocation_path": expected_invocation,
    }
    monkeypatch.setattr(
        compare,
        "recheck_python_invocation_identity_v2",
        lambda **_arguments: events.append("recheck") or True,
    )
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *_args, **_kwargs: events.append("popen"),
    )

    observed = compare.run_bounded_reviewer_process_v1(
        argv=(hostile_argv0, "-s", "-c", "pass"),
        cwd=str(tmp_path),
        environment={},
        timeout_seconds=1,
        stdout_hard_cap_bytes=1,
        stderr_hard_cap_bytes=1,
        io_chunk_bytes=1,
        term_grace_seconds=1,
        kill_grace_seconds=1,
        final_pipe_close_deadline_seconds=1,
        python_precheck_observation=precheck,
    )

    assert events == []
    assert observed["replay_termination_kind"] == "PRECHECK_FAILED"
