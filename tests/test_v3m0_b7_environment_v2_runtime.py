"""Runtime attacks for the B7 v9.2 Python invocation identity."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _actual_venv_identity() -> dict[str, str]:
    invocation = Path(sys.executable)
    target = Path(os.path.realpath(invocation))
    prefix = Path(sys.prefix)
    pyvenv_cfg = prefix / "pyvenv.cfg"
    assert invocation.is_absolute()
    assert invocation != target
    assert pyvenv_cfg.is_file()
    return {
        "python_invocation_path": str(invocation),
        "recorded_realpath": str(target),
        "recorded_raw_sha256": _sha256(target),
        "recorded_venv_prefix": str(prefix),
        "recorded_pyvenv_cfg_path": str(pyvenv_cfg),
        "recorded_pyvenv_cfg_raw_sha256": _sha256(pyvenv_cfg),
    }


def test_v92_invocation_identity_accepts_repository_venv_symlink_chain() -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
        recheck_python_invocation_identity_v2,
    )

    expected = _actual_venv_identity()
    observed = precheck_python_invocation_identity_v2(**expected)

    assert observed["profile_id"] == "v3m0-b7-python-venv-invocation-identity-v1"
    assert observed["python_invocation_path"] == expected["python_invocation_path"]
    assert observed["observed_realpath"] == expected["recorded_realpath"]
    assert observed["observed_raw_sha256"] == expected["recorded_raw_sha256"]
    assert observed["observed_venv_prefix"] == expected["recorded_venv_prefix"]
    assert (
        observed["observed_pyvenv_cfg_raw_sha256"]
        == expected["recorded_pyvenv_cfg_raw_sha256"]
    )
    assert observed["precheck_passed"] is True
    assert len(observed["ordered_lstat_hops"]) >= 2
    assert recheck_python_invocation_identity_v2(precheck_observation=observed)


def test_v92_import_probe_runs_through_invocation_not_resolved_target() -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
        run_python_environment_import_probe_v2,
    )

    expected = _actual_venv_identity()
    identity = precheck_python_invocation_identity_v2(**expected)
    probe = run_python_environment_import_probe_v2(
        python_invocation_path=expected["python_invocation_path"],
        python_identity_observation=identity,
    )

    assert probe["probe_passed"] is True
    assert probe["process_observation"]["replay_termination_kind"] == "EXITED"
    assert probe["process_observation"]["replay_exit_code"] == 0
    assert probe["process_observation"]["replay_stderr_bytes"] == b""
    assert (
        probe["report"]["python_invocation_path"] == expected["python_invocation_path"]
    )
    assert (
        probe["report"]["python_executable_realpath"] == expected["recorded_realpath"]
    )
    assert probe["report"]["python_venv_prefix"] == expected["recorded_venv_prefix"]
    assert probe["report"]["numpy_version"]
    assert probe["report"]["scipy_version"]


def test_v92_identity_recheck_rejects_changed_invocation_symlink(
    tmp_path: Path,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
        recheck_python_invocation_identity_v2,
    )

    prefix = tmp_path / "venv"
    bin_dir = prefix / "bin"
    bin_dir.mkdir(parents=True)
    target = tmp_path / "python-target"
    target.write_bytes(b"python-one")
    target.chmod(0o755)
    other_target = tmp_path / "python-other"
    other_target.write_bytes(b"python-two")
    other_target.chmod(0o755)
    invocation = bin_dir / "python"
    invocation.symlink_to(target)
    pyvenv_cfg = prefix / "pyvenv.cfg"
    pyvenv_cfg.write_bytes(b"home = frozen\n")

    observed = precheck_python_invocation_identity_v2(
        python_invocation_path=str(invocation),
        recorded_realpath=str(target),
        recorded_raw_sha256=_sha256(target),
        recorded_venv_prefix=str(prefix),
        recorded_pyvenv_cfg_path=str(pyvenv_cfg),
        recorded_pyvenv_cfg_raw_sha256=_sha256(pyvenv_cfg),
    )
    assert observed["precheck_passed"] is True

    invocation.unlink()
    invocation.symlink_to(other_target)
    assert not recheck_python_invocation_identity_v2(precheck_observation=observed)


def test_v92_identity_recheck_rejects_changed_pyvenv_cfg(tmp_path: Path) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
        recheck_python_invocation_identity_v2,
    )

    prefix = tmp_path / "venv"
    bin_dir = prefix / "bin"
    bin_dir.mkdir(parents=True)
    target = tmp_path / "python-target"
    target.write_bytes(b"python")
    target.chmod(0o755)
    invocation = bin_dir / "python"
    invocation.symlink_to(target)
    pyvenv_cfg = prefix / "pyvenv.cfg"
    pyvenv_cfg.write_bytes(b"home = first\n")

    observed = precheck_python_invocation_identity_v2(
        python_invocation_path=str(invocation),
        recorded_realpath=str(target),
        recorded_raw_sha256=_sha256(target),
        recorded_venv_prefix=str(prefix),
        recorded_pyvenv_cfg_path=str(pyvenv_cfg),
        recorded_pyvenv_cfg_raw_sha256=_sha256(pyvenv_cfg),
    )
    assert observed["precheck_passed"] is True

    pyvenv_cfg.write_bytes(b"home = second\n")
    assert not recheck_python_invocation_identity_v2(precheck_observation=observed)


def test_v92_identity_rejects_loop_and_wrong_nearest_pyvenv(tmp_path: Path) -> None:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
    )

    prefix = tmp_path / "venv"
    bin_dir = prefix / "bin"
    bin_dir.mkdir(parents=True)
    first = bin_dir / "python"
    second = bin_dir / "python-next"
    first.symlink_to(second.name)
    second.symlink_to(first.name)
    pyvenv_cfg = prefix / "pyvenv.cfg"
    pyvenv_cfg.write_bytes(b"home = frozen\n")

    looped = precheck_python_invocation_identity_v2(
        python_invocation_path=str(first),
        recorded_realpath=str(first),
        recorded_raw_sha256="0" * 64,
        recorded_venv_prefix=str(prefix),
        recorded_pyvenv_cfg_path=str(pyvenv_cfg),
        recorded_pyvenv_cfg_raw_sha256=_sha256(pyvenv_cfg),
    )
    assert looped["precheck_passed"] is False

    target = tmp_path / "python-target"
    target.write_bytes(b"python")
    target.chmod(0o755)
    first.unlink()
    second.unlink()
    first.symlink_to(target)
    wrong_cfg = tmp_path / "pyvenv.cfg"
    wrong_cfg.write_bytes(b"home = wrong\n")
    wrong = precheck_python_invocation_identity_v2(
        python_invocation_path=str(first),
        recorded_realpath=str(target),
        recorded_raw_sha256=_sha256(target),
        recorded_venv_prefix=str(tmp_path),
        recorded_pyvenv_cfg_path=str(wrong_cfg),
        recorded_pyvenv_cfg_raw_sha256=_sha256(wrong_cfg),
    )
    assert wrong["observed_pyvenv_cfg_path"] == str(pyvenv_cfg)
    assert wrong["precheck_passed"] is False
