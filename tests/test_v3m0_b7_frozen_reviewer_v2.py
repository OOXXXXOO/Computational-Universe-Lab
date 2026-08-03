"""Adversarial tests for the active v9.2 frozen reviewer wrapper."""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import shutil
import sys

import pytest


@pytest.fixture(scope="module")
def live_environment_manifest() -> dict[str, object]:
    from experiments.v3m0_b7_schema_lab.compare import (
        capture_environment_manifest_v2,
    )

    return capture_environment_manifest_v2(python_invocation_path=sys.executable)


def _empty_probe_process() -> dict[str, object]:
    empty_sha = hashlib.sha256(b"").hexdigest()
    return {
        "replay_termination_kind": "EXITED",
        "replay_exit_code": 0,
        "replay_signal_number": None,
        "replay_stdout_bytes": b"",
        "replay_stderr_bytes": b"",
        "replay_stdout_sha256": empty_sha,
        "replay_stderr_sha256": empty_sha,
        "process_cleanup_deadline_exceeded": False,
    }


def _fake_manifest(
    invocation: Path,
    target: Path,
    prefix: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    from experiments.v3m0_b7_schema_lab.common import canonical_sha_v1
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
    )

    cfg = prefix / "pyvenv.cfg"
    identity = precheck_python_invocation_identity_v2(
        python_invocation_path=str(invocation),
        recorded_realpath=str(target),
        recorded_raw_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        recorded_venv_prefix=str(prefix),
        recorded_pyvenv_cfg_path=str(cfg),
        recorded_pyvenv_cfg_raw_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),
    )
    assert identity["precheck_passed"] is True
    report = {
        "byteorder": sys.byteorder,
        "numpy_float64_dtype_str": "<f8" if sys.byteorder == "little" else ">f8",
        "numpy_float64_itemsize": 8,
        "numpy_version": "frozen-test",
        "platform_machine": "frozen-test",
        "platform_release": "frozen-test",
        "platform_system": "frozen-test",
        "python_executable_realpath": str(target),
        "python_implementation": "CPython",
        "python_invocation_path": str(invocation),
        "python_venv_prefix": str(prefix),
        "python_version": "frozen-test",
        "scipy_version": "frozen-test",
        "threadpool_info": [],
    }
    manifest = {
        "environment_schema_version": ("experimental.v3m0.b7.environment-manifest.v2"),
        "python_implementation": report["python_implementation"],
        "python_version": report["python_version"],
        "python_invocation_path": str(invocation),
        "python_executable_realpath": str(target),
        "python_executable_raw_sha256": identity["recorded_raw_sha256"],
        "python_invocation_identity_sha": identity["python_invocation_identity_sha"],
        "python_venv_prefix": str(prefix),
        "python_pyvenv_cfg_path": str(cfg),
        "python_pyvenv_cfg_raw_sha256": identity["recorded_pyvenv_cfg_raw_sha256"],
        "numpy_version": report["numpy_version"],
        "scipy_version": report["scipy_version"],
        "platform_system": report["platform_system"],
        "platform_release": report["platform_release"],
        "platform_machine": report["platform_machine"],
        "numpy_float64_dtype_str": report["numpy_float64_dtype_str"],
        "numpy_float64_itemsize": 8,
        "byteorder": report["byteorder"],
        "python_hash_seed": "0",
        "blas_thread_settings": [
            ["OPENBLAS_NUM_THREADS", "1"],
            ["OMP_NUM_THREADS", "1"],
            ["MKL_NUM_THREADS", "1"],
            ["VECLIB_MAXIMUM_THREADS", "1"],
            ["NUMEXPR_NUM_THREADS", "1"],
        ],
        "threadpool_info": [],
        "fresh_process_per_capture": True,
        "environment_sha": "",
    }
    manifest["environment_sha"] = canonical_sha_v1(
        {key: value for key, value in manifest.items() if key != "environment_sha"}
    )
    return manifest, report


def test_v92_frozen_runner_uses_invocation_and_complete_live_manifest(
    live_environment_manifest: dict[str, object],
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        build_sanitized_reviewer_environment_v1,
        run_frozen_reviewer_process_v2,
    )

    invocation = live_environment_manifest["python_invocation_path"]
    assert isinstance(invocation, str)
    observed = run_frozen_reviewer_process_v2(
        argv=(invocation, "-s", "-c", "pass"),
        cwd=str(Path(__file__).resolve().parents[1]),
        environment=build_sanitized_reviewer_environment_v1(),
        environment_manifest=live_environment_manifest,
    )

    assert observed["replay_termination_kind"] == "EXITED"
    assert observed["replay_exit_code"] == 0


def test_v92_frozen_runner_rejects_resolved_target_as_argv0(
    live_environment_manifest: dict[str, object],
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        build_sanitized_reviewer_environment_v1,
        run_frozen_reviewer_process_v2,
    )

    target = live_environment_manifest["python_executable_realpath"]
    assert isinstance(target, str)
    observed = run_frozen_reviewer_process_v2(
        argv=(target, "-s", "-c", "print('must-not-run')"),
        cwd=str(Path(__file__).resolve().parents[1]),
        environment=build_sanitized_reviewer_environment_v1(),
        environment_manifest=live_environment_manifest,
    )

    assert observed["replay_termination_kind"] == "PRECHECK_FAILED"
    assert observed["replay_stdout_bytes"] == b""


def test_v92_frozen_runner_rejects_environment_self_root_drift(
    live_environment_manifest: dict[str, object],
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        build_sanitized_reviewer_environment_v1,
        run_frozen_reviewer_process_v2,
    )

    drifted = copy.deepcopy(live_environment_manifest)
    drifted["environment_sha"] = "0" * 64
    invocation = drifted["python_invocation_path"]
    assert isinstance(invocation, str)
    observed = run_frozen_reviewer_process_v2(
        argv=(invocation, "-s", "-c", "print('must-not-run')"),
        cwd=str(Path(__file__).resolve().parents[1]),
        environment=build_sanitized_reviewer_environment_v1(),
        environment_manifest=drifted,
    )

    assert observed["replay_termination_kind"] == "PRECHECK_FAILED"


def test_v92_frozen_runner_rechecks_identity_after_environment_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import experiments.v3m0_b7_schema_lab.compare as compare

    prefix = tmp_path / "venv"
    (prefix / "bin").mkdir(parents=True)
    target = tmp_path / "python-target"
    shutil.copyfile(os.path.realpath(sys.executable), target)
    target.chmod(0o755)
    replacement = tmp_path / "python-replacement"
    shutil.copyfile(os.path.realpath(sys.executable), replacement)
    replacement.chmod(0o755)
    invocation = prefix / "bin" / "python"
    invocation.symlink_to(target)
    (prefix / "pyvenv.cfg").write_bytes(b"home = frozen\n")
    manifest, report = _fake_manifest(invocation, target, prefix)

    def probe_then_replace(**_arguments: object) -> dict[str, object]:
        invocation.unlink()
        invocation.symlink_to(replacement)
        return {
            "probe_passed": True,
            "process_observation": _empty_probe_process(),
            "report": report,
        }

    monkeypatch.setattr(
        compare,
        "run_python_environment_import_probe_v2",
        probe_then_replace,
    )
    observed = compare.run_frozen_reviewer_process_v2(
        argv=(str(invocation), "-s", "-c", "print('must-not-run')"),
        cwd=str(tmp_path),
        environment=compare.build_sanitized_reviewer_environment_v1(),
        environment_manifest=manifest,
    )

    assert observed["replay_termination_kind"] == "PRECHECK_FAILED"
    assert observed["replay_stdout_bytes"] == b""


def test_v92_frozen_runner_rejects_nonliteral_environment(
    live_environment_manifest: dict[str, object],
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        run_frozen_reviewer_process_v2,
    )

    invocation = live_environment_manifest["python_invocation_path"]
    assert isinstance(invocation, str)
    observed = run_frozen_reviewer_process_v2(
        argv=(invocation, "-s", "-c", "print('must-not-run')"),
        cwd=str(Path(__file__).resolve().parents[1]),
        environment={"PATH": os.environ.get("PATH", "")},
        environment_manifest=live_environment_manifest,
    )

    assert observed["replay_termination_kind"] == "PRECHECK_FAILED"
