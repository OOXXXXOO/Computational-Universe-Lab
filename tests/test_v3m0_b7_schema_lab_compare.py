"""Task-7 bounded process contracts for the B7 schema-lab comparator."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import signal
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


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


def test_bounded_runner_enforces_each_stream_hard_cap() -> None:
    program = "import os;os.write(1,b'x'*65);os.write(2,b'y'*65)"

    observed = _run(
        (sys.executable, "-s", "-c", program),
        stdout_hard_cap_bytes=64,
        stderr_hard_cap_bytes=64,
        io_chunk_bytes=16,
    )

    assert observed["replay_termination_kind"] == "OUTPUT_LIMIT_EXCEEDED"
    assert observed["replay_exit_code"] is None
    assert observed["replay_signal_number"] is None
    assert len(observed["replay_stdout_bytes"]) <= 64
    assert len(observed["replay_stderr_bytes"]) <= 64
    assert 64 in (
        len(observed["replay_stdout_bytes"]),
        len(observed["replay_stderr_bytes"]),
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


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("argv", []),
        ("argv", (sys.executable, 1)),
        ("timeout_seconds", 0.0),
        ("stdout_hard_cap_bytes", 0),
        ("io_chunk_bytes", 0),
        ("term_grace_seconds", -1.0),
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
