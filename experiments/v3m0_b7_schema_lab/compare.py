"""Frozen comparison and reviewer-process machinery for the B7 schema lab."""

from __future__ import annotations

import hashlib
import pathlib


REVIEWER_PROCESS_TIMEOUT_SECONDS_V1 = 1800
REVIEWER_PROCESS_STDOUT_HARD_CAP_BYTES_V1 = 1048576
REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1 = 1048576
REVIEWER_PROCESS_IO_CHUNK_BYTES_V1 = 65536
REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1 = 5
REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1 = 5
REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1 = 5
_SANITIZED_REVIEWER_ENVIRONMENT_V1 = (
    ("PYTHONHASHSEED", "0"),
    ("PYTHONNOUSERSITE", "1"),
    ("PYTHONDONTWRITEBYTECODE", "1"),
    ("PYTHONUTF8", "1"),
    ("OPENBLAS_NUM_THREADS", "1"),
    ("OMP_NUM_THREADS", "1"),
    ("MKL_NUM_THREADS", "1"),
    ("VECLIB_MAXIMUM_THREADS", "1"),
    ("NUMEXPR_NUM_THREADS", "1"),
    ("LANG", "C"),
    ("LC_ALL", "C"),
)
_REVIEWER_SUBCOMMANDS_V1 = (
    ("CORPUS_REPLAY", "review-corpus"),
    ("METRIC_REPLAY", "review-metric"),
)


def _require_lower_hex_v1(value, width, field):
    if (
        type(value) is not str
        or len(value) != width
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be exact lowercase hexadecimal width {width}")


def build_sanitized_reviewer_environment_v1():
    """Build the exact caller-independent reviewer child environment."""

    return {name: value for name, value in _SANITIZED_REVIEWER_ENVIRONMENT_V1}


def materialize_reviewer_command_v1(
    *,
    reviewer_role,
    frozen_python_executable,
    evidence_commit_sha,
    reviewed_executable_source_closure_sha,
):
    """Materialize one exact role-specific reviewer argv tuple."""

    subcommand = None
    for frozen_role, frozen_subcommand in _REVIEWER_SUBCOMMANDS_V1:
        if reviewer_role == frozen_role and type(reviewer_role) is str:
            subcommand = frozen_subcommand
            break
    if subcommand is None:
        raise ValueError("reviewer role is not frozen")
    if (
        type(frozen_python_executable) is not str
        or not frozen_python_executable.startswith("/")
        or frozen_python_executable.startswith("//")
        or any(
            part in ("", ".", "..") for part in frozen_python_executable.split("/")[1:]
        )
    ):
        raise ValueError("frozen Python executable path is not normalized absolute")
    _require_lower_hex_v1(evidence_commit_sha, 40, "evidence commit SHA")
    _require_lower_hex_v1(
        reviewed_executable_source_closure_sha,
        64,
        "reviewed executable source closure SHA",
    )
    return (
        frozen_python_executable,
        "-s",
        "-m",
        "experiments.v3m0_b7_schema_lab.compare",
        subcommand,
        "--evidence-commit",
        evidence_commit_sha,
        "--reviewed-executable-source-closure-sha",
        reviewed_executable_source_closure_sha,
        "--emit-replay-report",
    )


def precheck_frozen_python_executable_v1(
    *,
    recorded_realpath,
    recorded_raw_sha256,
):
    """Totalize the frozen reviewer-Python realpath, mode, and raw-SHA check."""

    import os
    import stat

    if type(recorded_realpath) is not str or not recorded_realpath.startswith("/"):
        raise ValueError("recorded Python realpath must be an absolute exact string")
    if (
        type(recorded_raw_sha256) is not str
        or len(recorded_raw_sha256) != 64
        or any(character not in "0123456789abcdef" for character in recorded_raw_sha256)
    ):
        raise ValueError("recorded Python raw SHA must be lowercase SHA-256")
    try:
        observed_realpath = os.path.realpath(recorded_realpath)
        status = os.stat(recorded_realpath)
    except OSError:
        return {
            "observed_realpath": None,
            "observed_raw_sha256": None,
            "regular_file": False,
            "executable": False,
            "precheck_passed": False,
        }
    regular_file = stat.S_ISREG(status.st_mode)
    executable = os.access(recorded_realpath, os.X_OK)
    observed_raw_sha256 = None
    if regular_file:
        try:
            observed_raw_sha256 = hashlib.sha256(
                pathlib.Path(recorded_realpath).read_bytes()
            ).hexdigest()
        except OSError:
            observed_raw_sha256 = None
    return {
        "observed_realpath": observed_realpath,
        "observed_raw_sha256": observed_raw_sha256,
        "regular_file": regular_file,
        "executable": executable,
        "precheck_passed": (
            observed_realpath == recorded_realpath
            and regular_file
            and executable
            and observed_raw_sha256 == recorded_raw_sha256
        ),
    }


def _empty_process_observation_v1(termination_kind):
    empty = b""
    empty_sha = hashlib.sha256(empty).hexdigest()
    return {
        "replay_termination_kind": termination_kind,
        "replay_exit_code": None,
        "replay_signal_number": None,
        "replay_stdout_bytes": empty,
        "replay_stderr_bytes": empty,
        "replay_stdout_sha256": empty_sha,
        "replay_stderr_sha256": empty_sha,
        "process_cleanup_deadline_exceeded": False,
    }


def _process_observation_v1(
    termination_kind,
    exit_code,
    signal_number,
    stdout_bytes,
    stderr_bytes,
    cleanup_deadline_exceeded,
):
    return {
        "replay_termination_kind": termination_kind,
        "replay_exit_code": exit_code,
        "replay_signal_number": signal_number,
        "replay_stdout_bytes": stdout_bytes,
        "replay_stderr_bytes": stderr_bytes,
        "replay_stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
        "replay_stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
        "process_cleanup_deadline_exceeded": cleanup_deadline_exceeded,
    }


def _validate_bounded_process_configuration_v1(
    argv,
    cwd,
    environment,
    timeout_seconds,
    stdout_hard_cap_bytes,
    stderr_hard_cap_bytes,
    io_chunk_bytes,
    term_grace_seconds,
    kill_grace_seconds,
    final_pipe_close_deadline_seconds,
):
    if (
        type(argv) is not tuple
        or not argv
        or any(type(item) is not str or not item for item in argv)
    ):
        raise TypeError("reviewer argv must be a non-empty tuple of exact strings")
    if type(cwd) is not str or not cwd:
        raise TypeError("reviewer cwd must be a non-empty exact string")
    if type(environment) is not dict or any(
        type(key) is not str or type(value) is not str
        for key, value in environment.items()
    ):
        raise TypeError("reviewer environment must be an exact str-to-str dict")
    if type(timeout_seconds) not in (int, float) or timeout_seconds <= 0.0:
        raise ValueError("reviewer timeout must be a positive int or float")
    for name, value in (
        ("stdout_hard_cap_bytes", stdout_hard_cap_bytes),
        ("stderr_hard_cap_bytes", stderr_hard_cap_bytes),
        ("io_chunk_bytes", io_chunk_bytes),
    ):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive exact int")
    for name, value in (
        ("term_grace_seconds", term_grace_seconds),
        ("kill_grace_seconds", kill_grace_seconds),
        ("final_pipe_close_deadline_seconds", final_pipe_close_deadline_seconds),
    ):
        if type(value) not in (int, float) or value <= 0.0:
            raise ValueError(f"{name} must be a positive int or float")


def run_bounded_reviewer_process_v1(
    *,
    argv,
    cwd,
    environment,
    timeout_seconds,
    stdout_hard_cap_bytes,
    stderr_hard_cap_bytes,
    io_chunk_bytes,
    term_grace_seconds,
    kill_grace_seconds,
    final_pipe_close_deadline_seconds,
):
    """Run one reviewer child with bounded nonblocking pipes and cleanup."""

    import os
    import selectors
    import signal
    import subprocess
    import time

    _validate_bounded_process_configuration_v1(
        argv,
        cwd,
        environment,
        timeout_seconds,
        stdout_hard_cap_bytes,
        stderr_hard_cap_bytes,
        io_chunk_bytes,
        term_grace_seconds,
        kill_grace_seconds,
        final_pipe_close_deadline_seconds,
    )
    timeout_seconds = float(timeout_seconds)
    term_grace_seconds = float(term_grace_seconds)
    kill_grace_seconds = float(kill_grace_seconds)
    final_pipe_close_deadline_seconds = float(final_pipe_close_deadline_seconds)
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
    except OSError:
        return _empty_process_observation_v1("SPAWN_FAILED")
    if process.stdout is None or process.stderr is None:
        raise AssertionError("reviewer pipes were not created")

    streams = {
        "stdout": {
            "pipe": process.stdout,
            "buffer": bytearray(),
            "cap": stdout_hard_cap_bytes,
        },
        "stderr": {
            "pipe": process.stderr,
            "buffer": bytearray(),
            "cap": stderr_hard_cap_bytes,
        },
    }
    selector = selectors.DefaultSelector()
    for name, state in streams.items():
        pipe = state["pipe"]
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ, name)

    overflow = False

    def drain_once(wait_seconds):
        nonlocal overflow
        for key, _mask in selector.select(wait_seconds):
            state = streams[key.data]
            buffer = state["buffer"]
            remaining = state["cap"] - len(buffer)
            read_size = min(io_chunk_bytes, remaining + 1)
            try:
                chunk = os.read(key.fileobj.fileno(), read_size)
            except BlockingIOError:
                continue
            if not chunk:
                try:
                    selector.unregister(key.fileobj)
                except KeyError:
                    pass
                continue
            if len(chunk) > remaining:
                buffer.extend(chunk[:remaining])
                overflow = True
            else:
                buffer.extend(chunk)

    overall_deadline = time.monotonic() + timeout_seconds
    forced_kind = None
    while True:
        if overflow:
            forced_kind = "OUTPUT_LIMIT_EXCEEDED"
            break
        return_code = process.poll()
        if return_code is not None and not selector.get_map():
            break
        remaining = overall_deadline - time.monotonic()
        if remaining <= 0.0:
            forced_kind = "TIMED_OUT"
            break
        drain_once(min(remaining, 0.05))

    cleanup_deadline_exceeded = False
    if forced_kind is not None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
        term_deadline = time.monotonic() + term_grace_seconds
        while process.poll() is None and time.monotonic() < term_deadline:
            drain_once(min(term_deadline - time.monotonic(), 0.05))
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            kill_deadline = time.monotonic() + kill_grace_seconds
            while process.poll() is None and time.monotonic() < kill_deadline:
                drain_once(min(kill_deadline - time.monotonic(), 0.05))
        cleanup_deadline_exceeded = process.poll() is None

    close_deadline = time.monotonic() + final_pipe_close_deadline_seconds
    while selector.get_map() and time.monotonic() < close_deadline:
        wait = min(close_deadline - time.monotonic(), 0.05)
        drain_once(wait)
        if overflow and forced_kind is None:
            forced_kind = "OUTPUT_LIMIT_EXCEEDED"
            break
    for state in streams.values():
        try:
            selector.unregister(state["pipe"])
        except KeyError:
            pass
        state["pipe"].close()
    selector.close()

    stdout_bytes = bytes(streams["stdout"]["buffer"])
    stderr_bytes = bytes(streams["stderr"]["buffer"])
    if forced_kind is not None:
        return _process_observation_v1(
            forced_kind,
            None,
            None,
            stdout_bytes,
            stderr_bytes,
            cleanup_deadline_exceeded,
        )
    return_code = process.poll()
    if return_code is None:
        return _process_observation_v1(
            "TIMED_OUT",
            None,
            None,
            stdout_bytes,
            stderr_bytes,
            True,
        )
    if return_code < 0:
        return _process_observation_v1(
            "SIGNALED",
            None,
            -return_code,
            stdout_bytes,
            stderr_bytes,
            False,
        )
    return _process_observation_v1(
        "EXITED",
        return_code,
        None,
        stdout_bytes,
        stderr_bytes,
        False,
    )


def run_frozen_reviewer_process_v1(*, argv, cwd, environment):
    """Run one reviewer child with the exact frozen v9.1 process limits."""

    return run_bounded_reviewer_process_v1(
        argv=argv,
        cwd=cwd,
        environment=environment,
        timeout_seconds=REVIEWER_PROCESS_TIMEOUT_SECONDS_V1,
        stdout_hard_cap_bytes=REVIEWER_PROCESS_STDOUT_HARD_CAP_BYTES_V1,
        stderr_hard_cap_bytes=REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1,
        io_chunk_bytes=REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
        term_grace_seconds=REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
        kill_grace_seconds=REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
        final_pipe_close_deadline_seconds=(
            REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1
        ),
    )
