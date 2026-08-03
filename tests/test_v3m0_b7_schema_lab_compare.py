"""Task-7 bounded process contracts for the B7 schema-lab comparator."""

from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import signal
import sys
import time

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_reviewer_spawn_environment_is_exact_and_caller_independent() -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        build_sanitized_reviewer_environment_v1,
    )

    first = build_sanitized_reviewer_environment_v1()
    second = build_sanitized_reviewer_environment_v1()

    assert first == {
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "LANG": "C",
        "LC_ALL": "C",
    }
    assert second == first
    assert second is not first


@pytest.mark.parametrize(
    ("reviewer_role", "subcommand"),
    (("CORPUS_REPLAY", "review-corpus"), ("METRIC_REPLAY", "review-metric")),
)
def test_reviewer_command_materialization_is_exact_registry_template(
    reviewer_role: str,
    subcommand: str,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        materialize_reviewer_command_v1,
    )

    argv = materialize_reviewer_command_v1(
        reviewer_role=reviewer_role,
        frozen_python_executable="/frozen/python",
        evidence_commit_sha="1" * 40,
        reviewed_executable_source_closure_sha="2" * 64,
    )

    assert argv == (
        "/frozen/python",
        "-s",
        "-m",
        "experiments.v3m0_b7_schema_lab.compare",
        subcommand,
        "--evidence-commit",
        "1" * 40,
        "--reviewed-executable-source-closure-sha",
        "2" * 64,
        "--emit-replay-report",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("reviewer_role", "UNKNOWN"),
        ("frozen_python_executable", "relative/python"),
        ("evidence_commit_sha", "BAD"),
        ("reviewed_executable_source_closure_sha", "BAD"),
    ),
)
def test_reviewer_command_materialization_rejects_unfrozen_inputs(
    field: str,
    value: str,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        materialize_reviewer_command_v1,
    )

    arguments = {
        "reviewer_role": "CORPUS_REPLAY",
        "frozen_python_executable": "/frozen/python",
        "evidence_commit_sha": "1" * 40,
        "reviewed_executable_source_closure_sha": "2" * 64,
    }
    arguments[field] = value
    with pytest.raises((TypeError, ValueError)):
        materialize_reviewer_command_v1(**arguments)


def _python_precheck(path: Path, raw_sha256: str) -> dict[str, object]:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_frozen_python_executable_v1,
    )

    return precheck_frozen_python_executable_v1(
        recorded_realpath=str(path),
        recorded_raw_sha256=raw_sha256,
    )


def test_frozen_python_precheck_accepts_exact_executable_file(tmp_path: Path) -> None:
    executable = tmp_path / "python"
    payload = b"frozen-python-bytes"
    executable.write_bytes(payload)
    executable.chmod(0o755)

    observed = _python_precheck(executable, hashlib.sha256(payload).hexdigest())

    assert observed == {
        "observed_realpath": str(executable),
        "observed_raw_sha256": hashlib.sha256(payload).hexdigest(),
        "regular_file": True,
        "executable": True,
        "precheck_passed": True,
    }


def test_frozen_python_precheck_totalizes_missing_and_wrong_sha(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert _python_precheck(missing, "0" * 64) == {
        "observed_realpath": None,
        "observed_raw_sha256": None,
        "regular_file": False,
        "executable": False,
        "precheck_passed": False,
    }

    executable = tmp_path / "python"
    executable.write_bytes(b"python")
    executable.chmod(0o755)
    observed = _python_precheck(executable, "0" * 64)
    assert observed["observed_raw_sha256"] == hashlib.sha256(b"python").hexdigest()
    assert observed["precheck_passed"] is False


def test_frozen_python_precheck_rejects_nonregular_nonexecutable_and_alias(
    tmp_path: Path,
) -> None:
    nonexecutable = tmp_path / "python"
    payload = b"python"
    nonexecutable.write_bytes(payload)
    nonexecutable.chmod(0o644)
    expected_sha = hashlib.sha256(payload).hexdigest()
    assert _python_precheck(nonexecutable, expected_sha)["precheck_passed"] is False
    assert _python_precheck(tmp_path, expected_sha)["regular_file"] is False

    alias = tmp_path / "python-alias"
    alias.symlink_to(nonexecutable)
    aliased = _python_precheck(alias, expected_sha)
    assert aliased["observed_realpath"] == str(nonexecutable)
    assert aliased["precheck_passed"] is False


@pytest.mark.parametrize(
    ("recorded_realpath", "recorded_raw_sha256"),
    ((Path("relative-python"), "0" * 64), (Path("/bin/sh"), "BAD")),
)
def test_frozen_python_precheck_rejects_invalid_record_configuration(
    recorded_realpath: Path,
    recorded_raw_sha256: str,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        _python_precheck(recorded_realpath, recorded_raw_sha256)


def test_frozen_runner_uses_exact_v91_process_limits() -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1,
        REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
        REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
        REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1,
        REVIEWER_PROCESS_STDOUT_HARD_CAP_BYTES_V1,
        REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
        REVIEWER_PROCESS_TIMEOUT_SECONDS_V1,
        run_frozen_reviewer_process_v1,
    )

    assert (
        REVIEWER_PROCESS_TIMEOUT_SECONDS_V1,
        REVIEWER_PROCESS_STDOUT_HARD_CAP_BYTES_V1,
        REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1,
        REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
        REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
        REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
        REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1,
    ) == (1800, 1048576, 1048576, 65536, 5, 5, 5)

    observed = run_frozen_reviewer_process_v1(
        argv=(sys.executable, "-s", "-c", "pass"),
        cwd=str(REPOSITORY_ROOT),
        environment={"PATH": os.environ.get("PATH", "")},
    )

    assert observed["replay_termination_kind"] == "EXITED"
    assert observed["replay_exit_code"] == 0


def _run(argv: tuple[str, ...], **overrides: object) -> dict[str, object]:
    from experiments.v3m0_b7_schema_lab.compare import (
        run_bounded_reviewer_process_v1,
    )

    arguments = {
        "argv": argv,
        "cwd": str(REPOSITORY_ROOT),
        "environment": {"PATH": os.environ.get("PATH", "")},
        "timeout_seconds": 2.0,
        "stdout_hard_cap_bytes": 1024,
        "stderr_hard_cap_bytes": 1024,
        "io_chunk_bytes": 64,
        "term_grace_seconds": 0.2,
        "kill_grace_seconds": 0.2,
        "final_pipe_close_deadline_seconds": 0.2,
    }
    arguments.update(overrides)
    return run_bounded_reviewer_process_v1(**arguments)


@pytest.mark.parametrize("exit_code", (0, 7))
def test_bounded_runner_captures_complete_exited_streams(exit_code: int) -> None:
    stdout = b"canonical-stdout"
    stderr = b"bounded-stderr"
    program = (
        "import os,sys;"
        f"os.write(1,{stdout!r});"
        f"os.write(2,{stderr!r});"
        f"sys.exit({exit_code})"
    )

    observed = _run((sys.executable, "-s", "-c", program))

    assert observed == {
        "replay_termination_kind": "EXITED",
        "replay_exit_code": exit_code,
        "replay_signal_number": None,
        "replay_stdout_bytes": stdout,
        "replay_stderr_bytes": stderr,
        "replay_stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "replay_stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "process_cleanup_deadline_exceeded": False,
    }


def test_bounded_runner_totalizes_spawn_failure_without_child() -> None:
    observed = _run(("/definitely/not/a/b7-python",))

    assert observed["replay_termination_kind"] == "SPAWN_FAILED"
    assert observed["replay_exit_code"] is None
    assert observed["replay_signal_number"] is None
    assert observed["replay_stdout_bytes"] == b""
    assert observed["replay_stderr_bytes"] == b""
    assert observed["replay_stdout_sha256"] == hashlib.sha256(b"").hexdigest()
    assert observed["replay_stderr_sha256"] == hashlib.sha256(b"").hexdigest()


def test_bounded_runner_normalizes_signal_exit() -> None:
    program = "import os,signal;os.kill(os.getpid(),signal.SIGTERM)"

    observed = _run((sys.executable, "-s", "-c", program))

    assert observed["replay_termination_kind"] == "SIGNALED"
    assert observed["replay_exit_code"] is None
    assert observed["replay_signal_number"] == signal.SIGTERM


@pytest.mark.parametrize(
    ("file_descriptor", "stream_name", "unit"),
    ((1, "stdout", b"x"), (2, "stderr", b"y")),
)
def test_bounded_runner_detects_exact_cap_plus_one_per_stream(
    file_descriptor: int,
    stream_name: str,
    unit: bytes,
) -> None:
    program = f"import os;os.write({file_descriptor},{unit!r}*65)"

    observed = _run(
        (sys.executable, "-s", "-c", program),
        stdout_hard_cap_bytes=64,
        stderr_hard_cap_bytes=64,
        io_chunk_bytes=16,
    )

    assert observed["replay_termination_kind"] == "OUTPUT_LIMIT_EXCEEDED"
    assert observed["replay_exit_code"] is None
    assert observed["replay_signal_number"] is None
    retained = unit * 64
    assert observed[f"replay_{stream_name}_bytes"] == retained
    assert (
        observed[f"replay_{stream_name}_sha256"] == hashlib.sha256(retained).hexdigest()
    )


def test_bounded_runner_totalizes_timeout_with_null_exit_and_signal() -> None:
    program = "import time;time.sleep(5)"

    observed = _run(
        (sys.executable, "-s", "-c", program),
        timeout_seconds=0.1,
    )

    assert observed["replay_termination_kind"] == "TIMED_OUT"
    assert observed["replay_exit_code"] is None
    assert observed["replay_signal_number"] is None
    assert observed["process_cleanup_deadline_exceeded"] is False


def test_timeout_kills_sigterm_ignoring_child_but_stays_normalized() -> None:
    program = (
        "import os,signal,time;"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
        "os.write(1,b'ready');"
        "time.sleep(5)"
    )

    started = time.monotonic()
    observed = _run(
        (sys.executable, "-s", "-c", program),
        timeout_seconds=0.1,
        term_grace_seconds=0.05,
        kill_grace_seconds=0.2,
        final_pipe_close_deadline_seconds=0.05,
    )
    elapsed = time.monotonic() - started

    assert observed["replay_termination_kind"] == "TIMED_OUT"
    assert observed["replay_exit_code"] is None
    assert observed["replay_signal_number"] is None
    assert observed["replay_stdout_bytes"] == b"ready"
    assert observed["process_cleanup_deadline_exceeded"] is False
    assert elapsed < 1.0


def test_final_pipe_close_is_bounded_for_detached_inheritor() -> None:
    program = (
        "import os,signal,time\n"
        "ready_r,ready_w=os.pipe()\n"
        "pid=os.fork()\n"
        "if pid == 0:\n"
        " os.close(ready_r)\n"
        " os.setsid()\n"
        " signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        " os.write(ready_w,b'1')\n"
        " os.close(ready_w)\n"
        " time.sleep(5)\n"
        " os._exit(0)\n"
        "os.close(ready_w)\n"
        "os.read(ready_r,1)\n"
        "os.close(ready_r)\n"
        "os.write(1,f'{pid}:{os.getpid()}:{os.getpgrp()}\\n'.encode())\n"
        "time.sleep(5)\n"
    )

    started = time.monotonic()
    observed = _run(
        (sys.executable, "-s", "-c", program),
        timeout_seconds=0.1,
        term_grace_seconds=0.05,
        kill_grace_seconds=0.2,
        final_pipe_close_deadline_seconds=0.05,
    )
    elapsed = time.monotonic() - started
    detached_pid, child_pid, child_process_group = map(
        int, observed["replay_stdout_bytes"].strip().split(b":")
    )
    try:
        assert observed["replay_termination_kind"] == "TIMED_OUT"
        assert observed["replay_exit_code"] is None
        assert observed["replay_signal_number"] is None
        assert observed["process_cleanup_deadline_exceeded"] is False
        assert child_process_group == child_pid
        assert elapsed < 1.0
    finally:
        try:
            os.kill(detached_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_parent_process_imports_are_function_local_and_bounded() -> None:
    compare_path = REPOSITORY_ROOT / "experiments" / "v3m0_b7_schema_lab" / "compare.py"
    tree = ast.parse(compare_path.read_text(encoding="utf-8"))
    top_level_imports = [
        node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    runner = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_bounded_reviewer_process_v1"
    )
    runner_imports = [
        node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
        for node in runner.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]

    parent_only_modules = {
        "os",
        "selectors",
        "shutil",
        "signal",
        "stat",
        "subprocess",
        "tarfile",
        "tempfile",
        "time",
    }
    assert parent_only_modules.isdisjoint(top_level_imports)
    assert runner_imports == ["os", "selectors", "signal", "subprocess", "time"]
    assert all(
        not isinstance(node, ast.Attribute) or node.attr != "communicate"
        for node in ast.walk(runner)
    )
    os_reads = [
        node
        for node in ast.walk(runner)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
        and node.func.attr == "read"
    ]
    assert len(os_reads) == 1
    assert len(os_reads[0].args) == 2
    assert isinstance(os_reads[0].args[1], ast.Name)
    assert os_reads[0].args[1].id == "read_size"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("argv", []),
        ("argv", (sys.executable, 1)),
        ("timeout_seconds", 0.0),
        ("timeout_seconds", True),
        ("stdout_hard_cap_bytes", 0),
        ("stdout_hard_cap_bytes", True),
        ("stderr_hard_cap_bytes", True),
        ("io_chunk_bytes", 0),
        ("io_chunk_bytes", True),
        ("term_grace_seconds", 0),
        ("term_grace_seconds", -1.0),
        ("term_grace_seconds", True),
        ("kill_grace_seconds", 0.0),
        ("kill_grace_seconds", True),
        ("final_pipe_close_deadline_seconds", 0),
        ("final_pipe_close_deadline_seconds", True),
    ),
)
def test_bounded_runner_rejects_invalid_parent_configuration(
    field: str,
    value: object,
) -> None:
    arguments = {
        "argv": (sys.executable, "-s", "-c", "pass"),
        "cwd": str(REPOSITORY_ROOT),
        "environment": {},
        "timeout_seconds": 2.0,
        "stdout_hard_cap_bytes": 64,
        "stderr_hard_cap_bytes": 64,
        "io_chunk_bytes": 16,
        "term_grace_seconds": 0.1,
        "kill_grace_seconds": 0.1,
        "final_pipe_close_deadline_seconds": 0.1,
    }
    arguments[field] = value

    from experiments.v3m0_b7_schema_lab.compare import (
        run_bounded_reviewer_process_v1,
    )

    with pytest.raises((TypeError, ValueError)):
        run_bounded_reviewer_process_v1(**arguments)
