"""Frozen comparison and reviewer-process machinery for the B7 schema lab."""

from __future__ import annotations

import hashlib

import experiments.v3m0_b7_schema_lab.common as _common


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
_REVIEWER_PROTOCOLS_V1 = (
    ("CORPUS_REPLAY", "v3m0-b7-corpus-replay-v1"),
    ("METRIC_REPLAY", "v3m0-b7-metric-replay-v1"),
)
_REPLAY_REPORT_OUTPUT_PROJECTION_FIELDS_V1 = (
    "replay_report_schema_version",
    "reviewer_role",
    "review_protocol_id",
    "lab_evidence_commit_sha",
    "replay_input_root_sha",
    "recomputed_d0_decision_payload_sha",
    "recomputed_d1_decision_payload_sha",
    "observed_surviving_route_ids",
    "observed_provisional_winner_route_id",
)
_PYTHON_EXECUTABLE_HASH_CHUNK_BYTES_V1 = 1048576
_PYTHON_INVOCATION_MAX_SYMLINK_HOPS_V2 = 40
_PYTHON_ENVIRONMENT_PROBE_TIMEOUT_SECONDS_V2 = 30
_PYTHON_ENVIRONMENT_PROBE_STDOUT_HARD_CAP_BYTES_V2 = 262144
_PYTHON_ENVIRONMENT_PROBE_STDERR_HARD_CAP_BYTES_V2 = 262144
_PYTHON_ENVIRONMENT_IMPORT_PROBE_UTF8_V2 = (
    "import json,os,platform,sys;import numpy as np;import scipy;"
    "from threadpoolctl import threadpool_info;"
    "payload={'python_implementation':platform.python_implementation(),"
    "'python_version':platform.python_version(),"
    "'python_invocation_path':os.path.normpath(os.path.abspath(sys.executable)),"
    "'python_executable_realpath':os.path.realpath(sys.executable),"
    "'python_venv_prefix':os.path.normpath(os.path.abspath(sys.prefix)),"
    "'numpy_version':str(np.__version__),'scipy_version':str(scipy.__version__),"
    "'platform_system':platform.system(),'platform_release':platform.release(),"
    "'platform_machine':platform.machine(),"
    "'numpy_float64_dtype_str':np.dtype(np.float64).str,"
    "'numpy_float64_itemsize':np.dtype(np.float64).itemsize,"
    "'byteorder':sys.byteorder,'threadpool_info':threadpool_info()};"
    "sys.stdout.buffer.write(json.dumps(payload,allow_nan=False,ensure_ascii=False,"
    "sort_keys=True,separators=(',',':')).encode('utf-8')+b'\\n')"
)
_PYTHON_ENVIRONMENT_PROBE_FIELDS_V2 = (
    "byteorder",
    "numpy_float64_dtype_str",
    "numpy_float64_itemsize",
    "numpy_version",
    "platform_machine",
    "platform_release",
    "platform_system",
    "python_executable_realpath",
    "python_implementation",
    "python_invocation_path",
    "python_venv_prefix",
    "python_version",
    "scipy_version",
    "threadpool_info",
)


def _require_lower_hex_v1(value, width, field):
    if (
        type(value) is not str
        or len(value) != width
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be exact lowercase hexadecimal width {width}")


def validate_replay_report_v1(raw_body):
    """Validate the exact replay-report roots and reviewer identity."""

    report = _common.validate_exact_lab_record_v1("B7LabReplayReportV1", raw_body)
    expected_protocol = None
    for reviewer_role, review_protocol_id in _REVIEWER_PROTOCOLS_V1:
        if report["reviewer_role"] == reviewer_role:
            expected_protocol = review_protocol_id
            break
    if report["review_protocol_id"] != expected_protocol:
        raise ValueError("replay report reviewer role/protocol mismatch")
    output_projection = {
        name: report[name] for name in _REPLAY_REPORT_OUTPUT_PROJECTION_FIELDS_V1
    }
    if report["replay_output_root_sha"] != _common.canonical_sha_v1(output_projection):
        raise ValueError("replay report output root mismatch")
    return report


def encode_replay_report_stdout_v1(raw_body):
    """Encode one validated report as canonical JSON plus exactly one LF."""

    report = validate_replay_report_v1(raw_body)
    return _common.canonical_json_bytes_v1(report) + b"\n"


def decode_replay_report_stdout_v1(stdout_bytes):
    """Strictly decode one canonical replay-report stdout frame."""

    if (
        type(stdout_bytes) is not bytes
        or not stdout_bytes.endswith(b"\n")
        or b"\n" in stdout_bytes[:-1]
    ):
        raise ValueError("replay report stdout must end in exactly one LF")
    payload = stdout_bytes[:-1]
    parsed = _common.strict_json_loads_v1(payload)
    if _common.canonical_json_bytes_v1(parsed) != payload:
        raise ValueError("replay report stdout JSON is not canonical")
    return validate_replay_report_v1(parsed)


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
    empty_observation = {
        "observed_realpath": None,
        "observed_raw_sha256": None,
        "observed_device": None,
        "observed_inode": None,
        "observed_mode": None,
        "observed_size": None,
        "observed_mtime_ns": None,
        "observed_ctime_ns": None,
        "regular_file": False,
        "executable": False,
        "precheck_passed": False,
    }
    file_descriptor = None
    try:
        observed_realpath = os.path.realpath(recorded_realpath)
        if observed_realpath != recorded_realpath:
            return empty_observation
        file_descriptor = os.open(
            recorded_realpath,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        before = os.fstat(file_descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        regular_file = stat.S_ISREG(before.st_mode)
        executable = regular_file and bool(before.st_mode & 0o111)
        observed_raw_sha256 = None
        complete_read = False
        if regular_file:
            hash_state = hashlib.sha256()
            remaining = before.st_size
            complete_read = True
            while remaining:
                chunk = os.read(
                    file_descriptor,
                    min(_PYTHON_EXECUTABLE_HASH_CHUNK_BYTES_V1, remaining),
                )
                if not chunk:
                    complete_read = False
                    break
                hash_state.update(chunk)
                remaining -= len(chunk)
            if complete_read and os.read(file_descriptor, 1):
                complete_read = False
            if complete_read:
                observed_raw_sha256 = hash_state.hexdigest()
        after = os.fstat(file_descriptor)
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        path_status = os.stat(recorded_realpath, follow_symlinks=False)
        path_identity = (
            path_status.st_dev,
            path_status.st_ino,
            path_status.st_mode,
            path_status.st_size,
            path_status.st_mtime_ns,
            path_status.st_ctime_ns,
        )
        path_executable = os.access(recorded_realpath, os.X_OK)
        final_status = os.stat(recorded_realpath, follow_symlinks=False)
        final_identity = (
            final_status.st_dev,
            final_status.st_ino,
            final_status.st_mode,
            final_status.st_size,
            final_status.st_mtime_ns,
            final_status.st_ctime_ns,
        )
        final_realpath = os.path.realpath(recorded_realpath)
        stable_identity = (
            before_identity == after_identity == path_identity == final_identity
            and final_realpath == recorded_realpath
        )
        return {
            "observed_realpath": observed_realpath,
            "observed_raw_sha256": observed_raw_sha256,
            "observed_device": before.st_dev,
            "observed_inode": before.st_ino,
            "observed_mode": before.st_mode,
            "observed_size": before.st_size,
            "observed_mtime_ns": before.st_mtime_ns,
            "observed_ctime_ns": before.st_ctime_ns,
            "regular_file": regular_file,
            "executable": executable,
            "precheck_passed": (
                stable_identity
                and complete_read
                and executable
                and path_executable
                and observed_raw_sha256 == recorded_raw_sha256
            ),
        }
    except OSError:
        return empty_observation
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass


def recheck_frozen_python_executable_identity_v1(
    *,
    recorded_realpath,
    precheck_observation,
):
    """Recheck the descriptor-bound identity immediately before child spawn."""

    import os
    import stat

    if (
        type(recorded_realpath) is not str
        or type(precheck_observation) is not dict
        or precheck_observation.get("precheck_passed") is not True
    ):
        return False
    fields = (
        "observed_device",
        "observed_inode",
        "observed_mode",
        "observed_size",
        "observed_mtime_ns",
        "observed_ctime_ns",
    )
    try:
        expected_identity = tuple(precheck_observation[name] for name in fields)
    except KeyError:
        return False
    if any(type(item) is not int for item in expected_identity):
        return False
    try:
        if os.path.realpath(recorded_realpath) != recorded_realpath:
            return False
        before = os.stat(recorded_realpath, follow_symlinks=False)
        executable = os.access(recorded_realpath, os.X_OK)
        after = os.stat(recorded_realpath, follow_symlinks=False)
    except OSError:
        return False
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    return (
        expected_identity == before_identity == after_identity
        and stat.S_ISREG(after.st_mode)
        and bool(after.st_mode & 0o111)
        and executable
    )


def _require_normalized_absolute_path_v2(value, field):
    import os

    if (
        type(value) is not str
        or not os.path.isabs(value)
        or value.startswith("//")
        or os.path.normpath(value) != value
    ):
        raise ValueError(f"{field} must be an absolute lexically normalized path")
    return value


def _stable_regular_file_observation_v2(path, *, executable_required):
    import os
    import stat

    empty = {
        "raw_sha256": None,
        "device": None,
        "inode": None,
        "mode": None,
        "size": None,
        "mtime_ns": None,
        "ctime_ns": None,
        "regular_file": False,
        "executable": False,
        "stable": False,
    }
    file_descriptor = None
    try:
        file_descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        before = os.fstat(file_descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        regular_file = stat.S_ISREG(before.st_mode)
        executable = regular_file and bool(before.st_mode & 0o111)
        complete_read = regular_file
        observed_raw_sha256 = None
        if regular_file:
            hash_state = hashlib.sha256()
            remaining = before.st_size
            while remaining:
                chunk = os.read(
                    file_descriptor,
                    min(_PYTHON_EXECUTABLE_HASH_CHUNK_BYTES_V1, remaining),
                )
                if not chunk:
                    complete_read = False
                    break
                hash_state.update(chunk)
                remaining -= len(chunk)
            if complete_read and os.read(file_descriptor, 1):
                complete_read = False
            if complete_read:
                observed_raw_sha256 = hash_state.hexdigest()
        after = os.fstat(file_descriptor)
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        final = os.stat(path, follow_symlinks=False)
        final_identity = (
            final.st_dev,
            final.st_ino,
            final.st_mode,
            final.st_size,
            final.st_mtime_ns,
            final.st_ctime_ns,
        )
        path_executable = os.access(path, os.X_OK)
        stable = (
            complete_read
            and before_identity == after_identity == final_identity
            and regular_file
            and (not executable_required or (executable and path_executable))
        )
        return {
            "raw_sha256": observed_raw_sha256,
            "device": before.st_dev,
            "inode": before.st_ino,
            "mode": before.st_mode,
            "size": before.st_size,
            "mtime_ns": before.st_mtime_ns,
            "ctime_ns": before.st_ctime_ns,
            "regular_file": regular_file,
            "executable": executable,
            "stable": stable,
        }
    except OSError:
        return empty
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass


def _resolve_python_invocation_chain_v2(python_invocation_path):
    import os
    import stat

    cursor = python_invocation_path
    observed_inodes = set()
    ordered_hops = []
    symlink_count = 0
    try:
        while True:
            status = os.lstat(cursor)
            inode_identity = (status.st_dev, status.st_ino)
            if inode_identity in observed_inodes:
                return ordered_hops, None, False
            observed_inodes.add(inode_identity)
            is_symlink = stat.S_ISLNK(status.st_mode)
            symlink_target = os.readlink(cursor) if is_symlink else None
            ordered_hops.append(
                {
                    "hop_ordinal": len(ordered_hops),
                    "absolute_normalized_path": cursor,
                    "lstat_device": status.st_dev,
                    "lstat_inode": status.st_ino,
                    "lstat_mode": status.st_mode,
                    "lstat_size": status.st_size,
                    "lstat_mtime_ns": status.st_mtime_ns,
                    "lstat_ctime_ns": status.st_ctime_ns,
                    "symlink_target_or_null": symlink_target,
                }
            )
            if not is_symlink:
                return ordered_hops, cursor, True
            symlink_count += 1
            if symlink_count > _PYTHON_INVOCATION_MAX_SYMLINK_HOPS_V2:
                return ordered_hops, None, False
            if os.path.isabs(symlink_target):
                cursor = os.path.normpath(symlink_target)
            else:
                cursor = os.path.normpath(
                    os.path.join(os.path.dirname(cursor), symlink_target)
                )
            if not os.path.isabs(cursor) or cursor.startswith("//"):
                return ordered_hops, None, False
    except OSError:
        return ordered_hops, None, False


def _nearest_pyvenv_cfg_v2(python_invocation_path):
    import os

    cursor = os.path.dirname(python_invocation_path)
    while True:
        candidate = os.path.join(cursor, "pyvenv.cfg")
        try:
            os.lstat(candidate)
        except FileNotFoundError:
            pass
        except OSError:
            return candidate, cursor, None
        else:
            return (
                candidate,
                cursor,
                _stable_regular_file_observation_v2(
                    candidate,
                    executable_required=False,
                ),
            )
        parent = os.path.dirname(cursor)
        if parent == cursor:
            return None, None, None
        cursor = parent


def precheck_python_invocation_identity_v2(
    *,
    python_invocation_path,
    recorded_realpath,
    recorded_raw_sha256,
    recorded_venv_prefix,
    recorded_pyvenv_cfg_path,
    recorded_pyvenv_cfg_raw_sha256,
):
    """Observe the v9.2 venv invocation and resolved-target identities."""

    invocation = _require_normalized_absolute_path_v2(
        python_invocation_path,
        "Python invocation",
    )
    target = _require_normalized_absolute_path_v2(
        recorded_realpath,
        "recorded Python target",
    )
    venv_prefix = _require_normalized_absolute_path_v2(
        recorded_venv_prefix,
        "recorded venv prefix",
    )
    pyvenv_cfg = _require_normalized_absolute_path_v2(
        recorded_pyvenv_cfg_path,
        "recorded pyvenv.cfg",
    )
    _require_lower_hex_v1(recorded_raw_sha256, 64, "recorded Python raw SHA")
    _require_lower_hex_v1(
        recorded_pyvenv_cfg_raw_sha256,
        64,
        "recorded pyvenv.cfg raw SHA",
    )
    ordered_hops, observed_target, chain_complete = _resolve_python_invocation_chain_v2(
        invocation
    )
    target_observation = _stable_regular_file_observation_v2(
        observed_target or target,
        executable_required=True,
    )
    observed_cfg, observed_prefix, cfg_observation = _nearest_pyvenv_cfg_v2(invocation)
    if cfg_observation is None:
        cfg_observation = _stable_regular_file_observation_v2(
            pyvenv_cfg,
            executable_required=False,
        )
    complete_identity = (
        chain_complete
        and observed_target is not None
        and target_observation["stable"] is True
        and observed_cfg is not None
        and observed_prefix is not None
        and cfg_observation["stable"] is True
    )
    projection = None
    identity_sha = None
    if complete_identity:
        projection = {
            "python_invocation_path": invocation,
            "ordered_lstat_hops": ordered_hops,
            "python_executable_realpath": observed_target,
            "python_executable_raw_sha256": target_observation["raw_sha256"],
            "python_venv_prefix": observed_prefix,
            "python_pyvenv_cfg_path": observed_cfg,
            "python_pyvenv_cfg_raw_sha256": cfg_observation["raw_sha256"],
        }
        identity_sha = _common.canonical_sha_v1(projection)
    precheck_passed = (
        complete_identity
        and observed_target == target
        and target_observation["raw_sha256"] == recorded_raw_sha256
        and observed_prefix == venv_prefix
        and observed_cfg == pyvenv_cfg
        and cfg_observation["raw_sha256"] == recorded_pyvenv_cfg_raw_sha256
    )
    return {
        "profile_id": "v3m0-b7-python-venv-invocation-identity-v1",
        "python_invocation_path": invocation,
        "recorded_realpath": target,
        "recorded_raw_sha256": recorded_raw_sha256,
        "recorded_venv_prefix": venv_prefix,
        "recorded_pyvenv_cfg_path": pyvenv_cfg,
        "recorded_pyvenv_cfg_raw_sha256": recorded_pyvenv_cfg_raw_sha256,
        "ordered_lstat_hops": ordered_hops,
        "observed_realpath": observed_target,
        "observed_raw_sha256": target_observation["raw_sha256"],
        "observed_venv_prefix": observed_prefix,
        "observed_pyvenv_cfg_path": observed_cfg,
        "observed_pyvenv_cfg_raw_sha256": cfg_observation["raw_sha256"],
        "python_invocation_identity_projection": projection,
        "python_invocation_identity_sha": identity_sha,
        "target_identity": target_observation,
        "pyvenv_cfg_identity": cfg_observation,
        "precheck_passed": precheck_passed,
    }


def recheck_python_invocation_identity_v2(*, precheck_observation):
    """Immediately recompute the full v9.2 path identity before Popen."""

    if (
        type(precheck_observation) is not dict
        or precheck_observation.get("profile_id")
        != "v3m0-b7-python-venv-invocation-identity-v1"
        or precheck_observation.get("precheck_passed") is not True
    ):
        return False
    required = (
        "python_invocation_path",
        "recorded_realpath",
        "recorded_raw_sha256",
        "recorded_venv_prefix",
        "recorded_pyvenv_cfg_path",
        "recorded_pyvenv_cfg_raw_sha256",
    )
    try:
        arguments = {name: precheck_observation[name] for name in required}
        refreshed = precheck_python_invocation_identity_v2(**arguments)
    except (KeyError, OSError, TypeError, ValueError):
        return False
    if refreshed["precheck_passed"] is not True:
        return False
    compared_fields = (
        "ordered_lstat_hops",
        "python_invocation_identity_projection",
        "python_invocation_identity_sha",
        "target_identity",
        "pyvenv_cfg_identity",
    )
    return all(
        _common.canonical_json_bytes_v1(refreshed[field])
        == _common.canonical_json_bytes_v1(precheck_observation.get(field))
        for field in compared_fields
    )


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
    python_precheck_observation=None,
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
    if python_precheck_observation is not None:
        v2_identity = (
            type(python_precheck_observation) is dict
            and python_precheck_observation.get("profile_id")
            == "v3m0-b7-python-venv-invocation-identity-v1"
        )
        if v2_identity:
            identity_passed = python_precheck_observation.get(
                "python_invocation_path"
            ) == argv[0] and recheck_python_invocation_identity_v2(
                precheck_observation=python_precheck_observation,
            )
        else:
            identity_passed = (
                type(python_precheck_observation) is dict
                and python_precheck_observation.get("observed_realpath") == argv[0]
                and recheck_frozen_python_executable_identity_v1(
                    recorded_realpath=argv[0],
                    precheck_observation=python_precheck_observation,
                )
            )
        if not identity_passed:
            return _empty_process_observation_v1("PRECHECK_FAILED")
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


def run_python_environment_import_probe_v2(
    *,
    python_invocation_path,
    python_identity_observation,
):
    """Run and strictly decode the bounded v9.2 NumPy/SciPy import probe."""

    invocation = _require_normalized_absolute_path_v2(
        python_invocation_path,
        "Python invocation",
    )
    invalid = {
        "probe_passed": False,
        "process_observation": _empty_process_observation_v1("PRECHECK_FAILED"),
        "report": None,
    }
    if (
        type(python_identity_observation) is not dict
        or python_identity_observation.get("precheck_passed") is not True
        or python_identity_observation.get("python_invocation_path") != invocation
    ):
        return invalid
    process_observation = run_bounded_reviewer_process_v1(
        argv=(
            invocation,
            "-s",
            "-c",
            _PYTHON_ENVIRONMENT_IMPORT_PROBE_UTF8_V2,
        ),
        cwd=python_identity_observation["recorded_venv_prefix"],
        environment=build_sanitized_reviewer_environment_v1(),
        timeout_seconds=_PYTHON_ENVIRONMENT_PROBE_TIMEOUT_SECONDS_V2,
        stdout_hard_cap_bytes=(_PYTHON_ENVIRONMENT_PROBE_STDOUT_HARD_CAP_BYTES_V2),
        stderr_hard_cap_bytes=(_PYTHON_ENVIRONMENT_PROBE_STDERR_HARD_CAP_BYTES_V2),
        io_chunk_bytes=REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
        term_grace_seconds=REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
        kill_grace_seconds=REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
        final_pipe_close_deadline_seconds=(
            REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1
        ),
        python_precheck_observation=python_identity_observation,
    )
    if not (
        process_observation["replay_termination_kind"] == "EXITED"
        and process_observation["replay_exit_code"] == 0
        and process_observation["replay_signal_number"] is None
        and process_observation["replay_stderr_bytes"] == b""
        and process_observation["process_cleanup_deadline_exceeded"] is False
    ):
        return {
            "probe_passed": False,
            "process_observation": process_observation,
            "report": None,
        }
    stdout_bytes = process_observation["replay_stdout_bytes"]
    try:
        if (
            not stdout_bytes.endswith(b"\n")
            or b"\n" in stdout_bytes[:-1]
            or not stdout_bytes[:-1]
        ):
            raise ValueError("environment probe stdout framing drifted")
        payload = stdout_bytes[:-1]
        report = _common.strict_json_loads_v1(payload)
        if (
            type(report) is not dict
            or tuple(sorted(report)) != _PYTHON_ENVIRONMENT_PROBE_FIELDS_V2
            or _common.canonical_json_bytes_v1(report) != payload
            or report["python_invocation_path"] != invocation
            or report["python_executable_realpath"]
            != python_identity_observation["recorded_realpath"]
            or report["python_venv_prefix"]
            != python_identity_observation["recorded_venv_prefix"]
        ):
            raise ValueError("environment probe report identity drifted")
    except (KeyError, TypeError, ValueError):
        return {
            "probe_passed": False,
            "process_observation": process_observation,
            "report": None,
        }
    return {
        "probe_passed": True,
        "process_observation": process_observation,
        "report": report,
    }


def capture_environment_manifest_v2(*, python_invocation_path):
    """Capture one complete live EnvironmentManifestV2 from a venv invocation."""

    invocation = _require_normalized_absolute_path_v2(
        python_invocation_path,
        "Python invocation",
    )
    _ordered_hops, observed_target, chain_complete = (
        _resolve_python_invocation_chain_v2(invocation)
    )
    if not chain_complete or observed_target is None or observed_target == invocation:
        raise ValueError("environment capture requires a resolved venv invocation")
    target_observation = _stable_regular_file_observation_v2(
        observed_target,
        executable_required=True,
    )
    observed_cfg, observed_prefix, cfg_observation = _nearest_pyvenv_cfg_v2(invocation)
    if (
        target_observation["stable"] is not True
        or target_observation["raw_sha256"] is None
        or observed_cfg is None
        or observed_prefix is None
        or cfg_observation is None
        or cfg_observation["stable"] is not True
        or cfg_observation["raw_sha256"] is None
    ):
        raise ValueError("environment capture identity observation is incomplete")
    identity = precheck_python_invocation_identity_v2(
        python_invocation_path=invocation,
        recorded_realpath=observed_target,
        recorded_raw_sha256=target_observation["raw_sha256"],
        recorded_venv_prefix=observed_prefix,
        recorded_pyvenv_cfg_path=observed_cfg,
        recorded_pyvenv_cfg_raw_sha256=cfg_observation["raw_sha256"],
    )
    if identity["precheck_passed"] is not True:
        raise ValueError("environment capture identity changed during observation")
    probe = run_python_environment_import_probe_v2(
        python_invocation_path=invocation,
        python_identity_observation=identity,
    )
    if probe["probe_passed"] is not True:
        raise ValueError("environment capture import probe failed")
    report = probe["report"]
    manifest = {
        "environment_schema_version": "experimental.v3m0.b7.environment-manifest.v2",
        "python_implementation": report["python_implementation"],
        "python_version": report["python_version"],
        "python_invocation_path": invocation,
        "python_executable_realpath": observed_target,
        "python_executable_raw_sha256": target_observation["raw_sha256"],
        "python_invocation_identity_sha": identity["python_invocation_identity_sha"],
        "python_venv_prefix": observed_prefix,
        "python_pyvenv_cfg_path": observed_cfg,
        "python_pyvenv_cfg_raw_sha256": cfg_observation["raw_sha256"],
        "numpy_version": report["numpy_version"],
        "scipy_version": report["scipy_version"],
        "platform_system": report["platform_system"],
        "platform_release": report["platform_release"],
        "platform_machine": report["platform_machine"],
        "numpy_float64_dtype_str": report["numpy_float64_dtype_str"],
        "numpy_float64_itemsize": report["numpy_float64_itemsize"],
        "byteorder": report["byteorder"],
        "python_hash_seed": "0",
        "blas_thread_settings": [
            ["OPENBLAS_NUM_THREADS", "1"],
            ["OMP_NUM_THREADS", "1"],
            ["MKL_NUM_THREADS", "1"],
            ["VECLIB_MAXIMUM_THREADS", "1"],
            ["NUMEXPR_NUM_THREADS", "1"],
        ],
        "threadpool_info": report["threadpool_info"],
        "fresh_process_per_capture": True,
        "environment_sha": "",
    }
    manifest["environment_sha"] = _common.canonical_sha_v1(
        {
            field: value
            for field, value in manifest.items()
            if field != "environment_sha"
        }
    )
    return _common.validate_environment_manifest_v2(
        manifest,
        python_identity_observation=identity,
        python_probe_result=probe,
    )


def run_frozen_reviewer_process_v1(
    *,
    argv,
    cwd,
    environment,
    recorded_python_raw_sha256,
):
    """Run one reviewer child with the exact frozen v9.1 process limits."""

    if type(argv) is not tuple or not argv or type(argv[0]) is not str:
        raise TypeError("frozen reviewer argv must contain its Python realpath")
    python_precheck_observation = precheck_frozen_python_executable_v1(
        recorded_realpath=argv[0],
        recorded_raw_sha256=recorded_python_raw_sha256,
    )
    if python_precheck_observation["precheck_passed"] is not True:
        return _empty_process_observation_v1("PRECHECK_FAILED")

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
        python_precheck_observation=python_precheck_observation,
    )
