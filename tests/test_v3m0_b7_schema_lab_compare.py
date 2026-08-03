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
