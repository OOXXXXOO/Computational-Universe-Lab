from __future__ import annotations

import base64
import copy
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import sysconfig
import time
from dataclasses import fields
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from rulespace_v3 import parent_v3_contracts as parent_v3_contracts
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.parent_freeze_v2 import (
    build_reviewed_current_application_authorities_v2_raw,
    verify_reviewed_current_application_authorities_v2_raw,
)
from rulespace_v3.parent_v3_contracts import (
    PROVISIONAL_AUTHORITY_STATE,
    _CONSTRUCTION_DEPENDENCY_PATHS,
    _replay_c19_current_application_authority_v3_at_preparation_commit,
)


_MANDATORY_DRAFT_STATUS_BY_PATH = {
    "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md": (
        "*Computational Universe Lab · 2026-07-31 · "
        "状态：DRAFT / 未签发 / 不生效*"
    ),
    "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：DRAFT / 未签发 / 非 Parent、permit 或 scientific authority*"
    ),
    "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*"
    ),
    "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*"
    ),
}
_MANDATORY_SIGNED_STATUS_BY_PATH = {
    "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md": (
        "*Computational Universe Lab · 2026-07-31 · "
        "状态：SIGNED / 已签发 / 生效*"
    ),
    "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：SIGNED / 已签发 / 非 Parent、permit 或 scientific authority*"
    ),
    "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：SIGNED / 已签发 / 非 Parent、permit、runtime 或 scientific authority*"
    ),
    "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：SIGNED / 已签发 / 非 Parent、permit、runtime 或 scientific authority*"
    ),
}
_PARENT_SIGNING_PLACEHOLDER_SOURCE = b"""\
from __future__ import annotations

PARENT_V3_PREPARATION_COMMIT_SHA: str | None = None
PARENT_V3_REVIEWED_CANDIDATE_SHA256: str | None = None
PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256: str | None = None
PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH: tuple[tuple[str, str], ...] = ()
PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE: tuple[tuple[str, str], ...] = ()
"""


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _write_fixture_path(repository: Path, relative_path: str, raw: bytes) -> None:
    destination = repository / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)


def _new_source_fixture_repository(
    root: Path,
    *,
    omitted_core_path: str | None = None,
) -> tuple[Path, str, dict[str, bytes]]:
    repository = root / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "V3-M0 Test")
    _git(repository, "config", "user.email", "v3m0@example.invalid")
    included = {
        "docsv3/direct.md": b"direct\n",
        "formal/v3m0/V3M0.lean": b"theorem fixture : True := by trivial\n",
        "formal/v3m0/sub/Proof.lean": b"theorem nested : True := by trivial\n",
        "rulespace_v3/nested/helper.py": b"VALUE = 1\n",
        "rulespace_gpu/v3_worker.py": b"WORKER = True\n",
        "rulespace_gpu/v3_exec.py": b"#!/usr/bin/env python3\n",
        "tests/test_v3m0_fixture.py": b"def test_fixture(): pass\n",
        "tests/test_v3_gpu_fixture.py": b"def test_gpu_fixture(): pass\n",
        "experiments/v3m0_fixture.py": b"EXPERIMENT = True\n",
        "data/results/v3m0_prerequisite.json": b"{}\n",
    }
    included.update(
        {
            path: (status + "\n\nfixture body\n").encode("utf-8")
            for path, status in _MANDATORY_DRAFT_STATUS_BY_PATH.items()
        }
    )
    for core_path in _CONSTRUCTION_DEPENDENCY_PATHS:
        included.setdefault(core_path, f"fixture:{core_path}\n".encode("utf-8"))
    for core_path in (
        "rulespace_v3/parent_candidate_v2.py",
        "rulespace_v3/parent_freeze.py",
        "rulespace_v3/parent_freeze_v2.py",
    ):
        included.setdefault(core_path, f"fixture:{core_path}\n".encode("utf-8"))
    if omitted_core_path is not None:
        included.pop(omitted_core_path)
    excluded = {
        "docsv3/nested/deep.md": b"not direct\n",
        "formal/v3m0/.lake/build/ignored.olean": b"ignored\n",
        "rulespace_v3/not_python.txt": b"ignored\n",
        "rulespace_gpu/not_v3.py": b"ignored\n",
        "tests/test_other.py": b"ignored\n",
        "experiments/not_v3m0.py": b"ignored\n",
        "data/results/not_v3m0.json": b"{}\n",
    }
    for relative_path, raw in {**included, **excluded}.items():
        _write_fixture_path(repository, relative_path, raw)
    (repository / "rulespace_gpu/v3_exec.py").chmod(0o755)
    _git(repository, "add", "--", ".")
    _git(repository, "commit", "-qm", "source fixture")
    commit_sha = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    return repository, commit_sha, included


def _new_full_candidate_repository(root: Path) -> Path:
    source_repository = Path(__file__).resolve().parents[1]
    repository = root / "full-candidate-repository"
    repository.mkdir()
    selected_paths = {
        *source_repository.glob("docsv3/*.md"),
        *(
            path
            for path in source_repository.glob("formal/v3m0/**/*")
            if ".lake" not in path.parts
        ),
        *source_repository.glob("rulespace_v3/**/*.py"),
        *source_repository.glob("rulespace_gpu/v3_*.py"),
        *source_repository.glob("tests/test_v3m0_*.py"),
        *source_repository.glob("tests/test_v3_gpu_*.py"),
        *source_repository.glob("experiments/v3m0_*.py"),
        *source_repository.glob("data/results/v3m0_*.json"),
    }
    for source_path in sorted(selected_paths):
        if not source_path.is_file() or source_path.is_symlink():
            continue
        relative_path = source_path.relative_to(source_repository)
        destination = repository / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
    for relative_path, draft_status in _MANDATORY_DRAFT_STATUS_BY_PATH.items():
        destination = repository / relative_path
        lines = destination.read_text(encoding="utf-8").splitlines()
        seen_heading = False
        for index, line in enumerate(lines):
            if line != draft_status:
                continue
            if not seen_heading:
                seen_heading = True
            else:
                lines[index] = "引用字面量：" + line
        assert seen_heading
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "V3-M0 Full E2E")
    _git(repository, "config", "user.email", "v3m0-full@example.invalid")
    _git(repository, "add", "--", ".")
    _git(repository, "commit", "-qm", "Parent-v3 preparation P")
    return repository


MODULE_NAME = "rulespace_v3.parent_candidate_v3"


def _candidate_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None, f"missing production module: {MODULE_NAME}"
    return importlib.import_module(MODULE_NAME)


def test_parent_candidate_v3_module_and_schema_constants_exist() -> None:
    candidate = _candidate_module()
    assert candidate.APPLICATION_SUPERSESSION_V3_SCHEMA_VERSION == (
        "v3m0.application-supersession.v3"
    )
    assert candidate.PARENT_FREEZE_CANDIDATE_V3_SCHEMA_VERSION == (
        "v3m0.parent-freeze-candidate.v3"
    )
    assert candidate.CURRENT_APPLICATION_REGISTRY_V3_SCHEMA_VERSION == (
        "v3m0.current-application-registry.v3"
    )
    assert candidate.PARENT_V3_SOURCE_CLOSURE_V1_SCHEMA_VERSION == (
        "v3m0.parent-v3-source-closure.v1"
    )
    assert candidate.REVIEWED_PATH_CLOSURE_V1_SCHEMA_VERSION == (
        "v3m0.parent-reviewed-path-closure.v1"
    )


def test_application_supersession_v3_has_the_exact_frozen_fields() -> None:
    candidate = _candidate_module()
    assert tuple(item.name for item in fields(candidate.ApplicationSupersessionV3)) == (
        "supersession_schema_version",
        "control_case_id",
        "superseded_application_instance_id",
        "superseded_application_authority_v2_sha",
        "replacement_application_instance_id",
        "replacement_application_authority_v3_sha",
        "reason_id",
        "supersession_sha",
    )
    assert candidate.ApplicationSupersessionV3.__dataclass_params__.frozen is True


def test_parent_freeze_candidate_v3_has_the_exact_frozen_fields() -> None:
    candidate = _candidate_module()
    assert tuple(
        item.name for item in fields(candidate.ParentFreezeCandidateV3Manifest)
    ) == (
        "candidate_schema_version",
        "authority_state",
        "program_id",
        "preparation_commit_sha",
        "historical_parent_v1",
        "reviewed_candidate_v1",
        "reviewed_candidate_v2",
        "inherited_current_application_authorities_v2",
        "superseded_application_authorities_v2",
        "refrozen_current_application_authorities_v3",
        "application_supersessions",
        "block_success_scenario_ids",
        "source_closure",
        "source_closure_sha",
        "candidate_sha",
    )
    assert candidate.ParentFreezeCandidateV3Manifest.__dataclass_params__.frozen is True


def test_parent_candidate_v3_exposes_only_the_frozen_build_verify_and_root_owners() -> None:
    candidate = _candidate_module()
    expected = {
        "build_v3m0_parent_freeze_candidate_v3",
        "verify_parent_freeze_candidate_v3",
        "current_application_registry_v3_payload",
        "parent_v3_source_closure_v1_payload",
        "reviewed_path_closure_v1_payload",
    }
    assert expected <= set(vars(candidate))
    assert "_replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit" not in (
        candidate.__all__
    )


def test_reviewed_path_root_owner_accepts_exact_pairs_and_has_a_golden_root() -> None:
    candidate = _candidate_module()
    source_closure = (
        ("alpha.py", "100644", "1" * 64),
        ("测量.md", "100755", "2" * 64),
    )
    expected_pairs = (
        ("alpha.py", "1" * 64),
        ("测量.md", "2" * 64),
    )
    projection_name = "_project_source_closure_to_reviewed_path_closure"
    assert hasattr(candidate, projection_name)
    assert projection_name not in candidate.__all__
    projection = getattr(candidate, projection_name)(source_closure)
    assert projection == expected_pairs
    payload = candidate.reviewed_path_closure_v1_payload(projection)
    assert payload == {
        "reviewed_path_closure_schema_version": (
            candidate.REVIEWED_PATH_CLOSURE_V1_SCHEMA_VERSION
        ),
        "entries": [
            {"relative_path": "alpha.py", "raw_sha256": "1" * 64},
            {"relative_path": "测量.md", "raw_sha256": "2" * 64},
        ],
    }
    assert canonical_sha(payload) == (
        "a054d1fe1ba1222194de046bd26643c3e4a64b581c5c34a53a1dbcb67cef20e1"
    )

    class HostilePairs(tuple):
        pass

    for invalid in (
        source_closure,
        tuple(reversed(expected_pairs)),
        (("alpha.py", "100644", "1" * 64),),
        HostilePairs(expected_pairs),
    ):
        with pytest.raises((TypeError, ValueError)):
            candidate.reviewed_path_closure_v1_payload(invalid)


def test_registry_owner_rejects_duplicate_control_ids_before_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_module = _candidate_module()
    forged = object.__new__(candidate_module.ParentFreezeCandidateV3Manifest)
    for field in fields(candidate_module.ParentFreezeCandidateV3Manifest):
        object.__setattr__(forged, field.name, None)
    duplicate = SimpleNamespace(control_case_id="C01_DUPLICATE")
    object.__setattr__(
        forged,
        "inherited_current_application_authorities_v2",
        (duplicate, duplicate),
    )
    object.__setattr__(forged, "refrozen_current_application_authorities_v3", ())
    object.__setattr__(
        forged,
        "reviewed_candidate_v1",
        SimpleNamespace(
            application_candidates=(
                SimpleNamespace(control_case_id="C01_DUPLICATE"),
            )
        ),
    )
    monkeypatch.setattr(
        candidate_module.ParentFreezeCandidateV3Manifest,
        "__post_init__",
        lambda self: None,
    )
    with pytest.raises(ValueError, match="duplicate"):
        candidate_module.current_application_registry_v3_payload(forged)


def test_slice3a_source_closure_snapshot_starts_as_exact_empty_tuple() -> None:
    candidate = _candidate_module()
    paths = candidate.PARENT_V3_SOURCE_CLOSURE_PATHS
    assert type(paths) is tuple
    assert paths == ()


def test_slice3a_source_selector_uses_only_p_tree_regular_blobs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository, commit_sha, included = _new_source_fixture_repository(tmp_path)
    _write_fixture_path(repository, "data/results/v3m0_untracked.json", b"{}\n")
    _write_fixture_path(repository, "docsv3/direct.md", b"live drift\n")
    monkeypatch.setattr(parent_v3_contracts, "_REPOSITORY_ROOT", repository)

    selector_name = "_select_parent_v3_source_closure_at_preparation_commit"
    assert hasattr(candidate, selector_name)
    closure = getattr(candidate, selector_name)(commit_sha)
    expected = tuple(
        (
            relative_path,
            "100755" if relative_path == "rulespace_gpu/v3_exec.py" else "100644",
            hashlib.sha256(raw).hexdigest(),
        )
        for relative_path, raw in sorted(
            included.items(),
            key=lambda item: item[0].encode("utf-8"),
        )
    )
    assert closure == expected
    assert "data/results/v3m0_untracked.json" not in {
        item[0] for item in closure
    }
    assert closure == tuple(sorted(closure, key=lambda item: item[0].encode("utf-8")))
    monkeypatch.setattr(candidate, "PARENT_V3_SOURCE_CLOSURE_PATHS", ())
    installed = candidate._freeze_parent_v3_source_closure_paths(closure)
    expected_paths = tuple(item[0] for item in closure)
    assert installed == expected_paths
    assert candidate.PARENT_V3_SOURCE_CLOSURE_PATHS == expected_paths
    with pytest.raises(ValueError, match="changed"):
        candidate._freeze_parent_v3_source_closure_paths(
            (("different.py", "100644", "f" * 64),)
        )
    assert candidate.PARENT_V3_SOURCE_CLOSURE_PATHS == expected_paths


@pytest.mark.parametrize("bad_kind", ("symlink", "gitlink"))
def test_slice3a_source_selector_rejects_selected_nonregular_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_kind: str,
) -> None:
    candidate = _candidate_module()
    repository, base_commit, _included = _new_source_fixture_repository(tmp_path)
    if bad_kind == "symlink":
        (repository / "rulespace_v3/selected_link.py").symlink_to(
            "parent_freeze.py"
        )
        _git(repository, "add", "--", "rulespace_v3/selected_link.py")
    elif bad_kind == "gitlink":
        _git(
            repository,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{base_commit},formal/v3m0/selected-submodule",
        )
    _git(repository, "commit", "-qm", f"selected {bad_kind}")
    bad_commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    monkeypatch.setattr(parent_v3_contracts, "_REPOSITORY_ROOT", repository)
    selector = getattr(
        candidate,
        "_select_parent_v3_source_closure_at_preparation_commit",
    )
    with pytest.raises(ValueError, match="regular"):
        selector(bad_commit)


def test_slice3a_source_selector_ignores_nonmatching_children_of_patterned_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository, _base_commit, included = _new_source_fixture_repository(tmp_path)
    _write_fixture_path(
        repository,
        "rulespace_v3/ordinary_tree.py/child.txt",
        b"not a selected Python blob\n",
    )
    _git(repository, "add", "--", "rulespace_v3/ordinary_tree.py")
    _git(repository, "commit", "-qm", "ordinary patterned tree")
    commit_sha = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    monkeypatch.setattr(parent_v3_contracts, "_REPOSITORY_ROOT", repository)
    selector = getattr(
        candidate,
        "_select_parent_v3_source_closure_at_preparation_commit",
    )
    closure = selector(commit_sha)
    assert tuple(item[0] for item in closure) == tuple(
        sorted(included, key=lambda item: item.encode("utf-8"))
    )


def test_slice3a_source_selector_rejects_missing_core_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    missing = "rulespace_v3/parent_freeze_v2.py"
    repository, commit_sha, _included = _new_source_fixture_repository(
        tmp_path,
        omitted_core_path=missing,
    )
    monkeypatch.setattr(parent_v3_contracts, "_REPOSITORY_ROOT", repository)
    selector = getattr(
        candidate,
        "_select_parent_v3_source_closure_at_preparation_commit",
    )
    with pytest.raises(ValueError, match="core replay"):
        selector(commit_sha)


@pytest.mark.parametrize("bad_shape", ("dirty", "untracked", "merge", "signed"))
def test_slice3a_clean_preparation_snapshot_rejects_bad_head_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_shape: str,
) -> None:
    candidate = _candidate_module()
    fixture_root = tmp_path / bad_shape
    fixture_root.mkdir()
    repository, _commit_sha, _included = _new_source_fixture_repository(
        fixture_root
    )
    if bad_shape == "dirty":
        _write_fixture_path(repository, "docsv3/direct.md", b"dirty\n")
    elif bad_shape == "untracked":
        _write_fixture_path(repository, "untracked.txt", b"untracked\n")
    elif bad_shape == "signed":
        _write_fixture_path(
            repository,
            "data/results/v3m0_parent_v3_review_mathematics.json",
            b"{}\n",
        )
        _git(repository, "add", "--", ".")
        _git(repository, "commit", "-qm", "signing-shaped tree")
    else:
        main_branch = (
            _git(repository, "branch", "--show-current").decode("ascii").strip()
        )
        _git(repository, "checkout", "-qb", "side")
        _write_fixture_path(repository, "side.txt", b"side\n")
        _git(repository, "add", "--", "side.txt")
        _git(repository, "commit", "-qm", "side")
        _git(repository, "checkout", "-q", main_branch)
        _write_fixture_path(repository, "main.txt", b"main\n")
        _git(repository, "add", "--", "main.txt")
        _git(repository, "commit", "-qm", "main")
        _git(repository, "merge", "--no-ff", "-qm", "merge fixture", "side")
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    with pytest.raises(ValueError):
        candidate._snapshot_clean_preparation_head()


def test_security_s4p0_snapshot_binds_work_tree_against_core_worktree_redirect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository, _commit_sha, _included = _new_source_fixture_repository(tmp_path)
    alternate = tmp_path / "attacker-clean-worktree"
    alternate.mkdir()
    _git(
        repository,
        "--work-tree",
        str(alternate),
        "checkout",
        "-f",
        "HEAD",
        "--",
        ".",
    )
    _git(repository, "config", "core.worktree", str(alternate))
    _write_fixture_path(repository, "docsv3/direct.md", b"dirty current root\n")
    assert _git(
        repository,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
    ) == b""

    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    with pytest.raises(ValueError, match="clean|dirty|worktree"):
        candidate._snapshot_clean_preparation_head()


def test_security_s4p1_snapshot_tree_listing_is_output_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository, _commit_sha, _included = _new_source_fixture_repository(tmp_path)
    for index in range(32):
        _write_fixture_path(
            repository,
            f"untracked/attacker-{index:03d}.txt",
            b"x\n",
        )
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    monkeypatch.setattr(candidate, "_TRUSTED_GIT_MAX_STDOUT_BYTES", 128)
    with pytest.raises(ValueError, match="stdout limit"):
        candidate._snapshot_clean_preparation_head()


def test_slice3a_public_builder_uses_two_identical_clean_snapshots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    first_p = "1" * 40
    changed_p = "2" * 40
    sentinel = SimpleNamespace(
        source_closure=(("alpha.py", "100644", "0" * 64),)
    )
    snapshots = iter((first_p, first_p))
    observed_replays: list[str] = []
    events: list[str] = []
    monkeypatch.setattr(candidate, "PARENT_V3_SOURCE_CLOSURE_PATHS", ())
    monkeypatch.setattr(
        candidate,
        "_snapshot_clean_preparation_head",
        lambda: events.append("snapshot") or next(snapshots),
    )
    monkeypatch.setattr(
        candidate,
        "_replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit",
        lambda commit_sha: (
            events.append("replay")
            or observed_replays.append(commit_sha)
            or sentinel
        ),
    )
    monkeypatch.setattr(
        candidate,
        "_run_fresh_interpreter_completeness_audit",
        lambda value: events.append("audit") or {"candidate": value},
    )
    original_freeze = candidate._freeze_parent_v3_source_closure_paths
    monkeypatch.setattr(
        candidate,
        "_freeze_parent_v3_source_closure_paths",
        lambda closure: events.append("freeze") or original_freeze(closure),
    )
    assert candidate.build_v3m0_parent_freeze_candidate_v3() is sentinel
    assert observed_replays == [first_p]
    assert events == ["snapshot", "replay", "audit", "snapshot", "freeze"]
    assert candidate.PARENT_V3_SOURCE_CLOSURE_PATHS == ("alpha.py",)

    snapshots = iter((first_p, changed_p))
    events.clear()
    monkeypatch.setattr(candidate, "PARENT_V3_SOURCE_CLOSURE_PATHS", ())
    monkeypatch.setattr(
        candidate,
        "_snapshot_clean_preparation_head",
        lambda: events.append("snapshot") or next(snapshots),
    )
    with pytest.raises(ValueError, match="changed"):
        candidate.build_v3m0_parent_freeze_candidate_v3()
    assert events == ["snapshot", "replay", "audit", "snapshot"]
    assert candidate.PARENT_V3_SOURCE_CLOSURE_PATHS == ()

    snapshots = iter((first_p,))
    events.clear()
    monkeypatch.setattr(candidate, "PARENT_V3_SOURCE_CLOSURE_PATHS", ())
    monkeypatch.setattr(
        candidate,
        "_run_fresh_interpreter_completeness_audit",
        lambda _value: events.append("audit")
        or (_ for _ in ()).throw(ValueError("audit failed")),
    )
    with pytest.raises(ValueError, match="audit failed"):
        candidate.build_v3m0_parent_freeze_candidate_v3()
    assert events == ["snapshot", "replay", "audit"]
    assert candidate.PARENT_V3_SOURCE_CLOSURE_PATHS == ()


def _slice3b1_expectation(
    candidate_module,
    repository: Path,
):
    raw_by_relative_path = {
        "rulespace_v3/audit_fixture.py": b"AUDIT_FIXTURE = True\n",
        "rulespace_v3/parent_candidate_v3.py": b"CANDIDATE = True\n",
        "rulespace_v3/parent_v3_contracts.py": b"CONTRACTS = True\n",
    }
    for relative_path, raw in raw_by_relative_path.items():
        _write_fixture_path(repository, relative_path, raw)
    return candidate_module._FreshInterpreterAuditExpectation(
        preparation_commit_sha="1" * 40,
        preparation_tree_sha="5" * 40,
        candidate_sha="2" * 64,
        source_closure_sha="3" * 64,
        source_closure=tuple(
            (relative_path, "100644", hashlib.sha256(raw).hexdigest())
            for relative_path, raw in sorted(raw_by_relative_path.items())
        ),
        trusted_git_executable_realpath=(
            candidate_module._TRUSTED_GIT_EXECUTABLE_REALPATH
        ),
        trusted_python_executable_realpath=(
            candidate_module._TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    )


def _slice3b1_payload(
    candidate_module,
    expectation,
    nonce: str,
    *,
    module_paths: list[str] | None = None,
    file_paths: list[str] | None = None,
    git_commands: list[dict[str, object]] | None = None,
    p_data_states: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    if module_paths is None:
        module_paths = [
            "rulespace_v3/audit_fixture.py",
            "rulespace_v3/parent_candidate_v3.py",
            "rulespace_v3/parent_v3_contracts.py",
        ]
    if file_paths is None:
        file_paths = []
    if git_commands is None:
        git_commands = [
            {
                "argv": [
                    expectation.trusted_git_executable_realpath,
                    "cat-file",
                    "-t",
                    expectation.preparation_commit_sha,
                ],
                "cwd_state": "EXACT_REPOSITORY_ROOT",
                "executable_realpath": (
                    expectation.trusted_git_executable_realpath
                ),
                "shell": False,
            }
        ]
    if p_data_states is None:
        p_data_states = []
    payload = {
        "audit_schema_version": (
            candidate_module._FRESH_INTERPRETER_AUDIT_SCHEMA_VERSION
        ),
        "audit_mode": candidate_module._FRESH_INTERPRETER_AUDIT_MODE,
        "nonce": nonce,
        "preparation_commit_sha": expectation.preparation_commit_sha,
        "preparation_tree_sha": expectation.preparation_tree_sha,
        "python_executable_realpath": (
            expectation.trusted_python_executable_realpath
        ),
        "candidate_sha": expectation.candidate_sha,
        "source_closure_sha": expectation.source_closure_sha,
        "hook_installation_state": candidate_module._FRESH_INTERPRETER_HOOK_STATE,
        "observed_module_paths": module_paths,
        "observed_file_read_paths": file_paths,
        "observed_git_commands": git_commands,
        "observed_p_data_states": p_data_states,
        "observed_dynamic_library_paths": [],
        "observed_repository_directory_scans": [".", "rulespace_v3"],
    }
    payload["observation_sha"] = canonical_sha(payload)
    return payload


def _resign_slice3b1_payload(payload: dict[str, object]) -> None:
    unsigned = {key: value for key, value in payload.items() if key != "observation_sha"}
    payload["observation_sha"] = canonical_sha(unsigned)


def _canonical_json_line(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def test_slice3b1_bootstrap_installs_hook_before_repo_paths_and_imports() -> None:
    candidate = _candidate_module()
    source = candidate._FRESH_AUDIT_BOOTSTRAP
    assert type(source) is str
    hook_index = source.index("sys.addaudithook")
    path_index = source.index("sys.path.insert")
    import_index = source.index("from rulespace_v3")
    assert hook_index < path_index < import_index
    assert "HOOK_INSTALLED_BEFORE_REPOSITORY_IMPORT" in source


def test_security_s3p0_bootstrap_has_no_reviewed_code_mutable_transcript() -> None:
    candidate = _candidate_module()
    source = candidate._FRESH_AUDIT_BOOTSTRAP
    assert "_CULAB_FRESH_AUDIT_STATE" not in source
    assert "_observed_module_paths" not in source
    assert "_observed_file_read_paths" not in source
    assert "_observed_git_commands" not in source
    assert "class _StableRepositorySourceLoader" in source
    assert "compile(source_bytes" in source


def _security_s3p0_framed_completed(
    candidate,
    expectation,
    nonce: str,
    repository: Path,
    *,
    payload: dict[str, object] | None = None,
):
    if payload is None:
        payload = _slice3b1_payload(candidate, expectation, nonce)
    events: list[tuple[str, object]] = [
        (
            "start",
            {"hook_installation_state": candidate._FRESH_INTERPRETER_HOOK_STATE},
        )
    ]
    events.extend(("module_path", path) for path in payload["observed_module_paths"])
    events.extend(("file_read_path", path) for path in payload["observed_file_read_paths"])
    events.extend(("git_command", item) for item in payload["observed_git_commands"])
    events.extend(
        ("p_data_state", item)
        for item in payload["observed_p_data_states"]
    )
    events.extend(
        ("dynamic_library", {"path": path})
        for path in payload["observed_dynamic_library_paths"]
    )
    events.extend(
        ("repository_directory_scan", path)
        for path in payload["observed_repository_directory_scans"]
    )
    for path in payload["observed_module_paths"]:
        source_path = repository / path
        metadata = source_path.stat()
        events.append(
            (
                "source_execution",
                {
                    "path": path,
                    "st_dev": metadata.st_dev,
                    "st_ino": metadata.st_ino,
                    "st_mode": metadata.st_mode,
                    "st_size": metadata.st_size,
                    "st_mtime_ns": metadata.st_mtime_ns,
                    "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                },
            )
        )
    final_core = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "hook_installation_state",
            "observed_module_paths",
            "observed_file_read_paths",
            "observed_git_commands",
            "observed_p_data_states",
            "observed_dynamic_library_paths",
            "observed_repository_directory_scans",
            "observation_sha",
        }
    }
    events.append(("final", final_core))
    previous_sha = "0" * 64
    lines: list[bytes] = []
    for sequence, (kind, event_payload) in enumerate(events):
        line, previous_sha = candidate._encode_fresh_audit_frame(
            nonce=nonce,
            sequence=sequence,
            kind=kind,
            payload=event_payload,
            previous_frame_sha=previous_sha,
        )
        lines.append(line)
    return subprocess.CompletedProcess(
        args=(candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH,),
        returncode=0,
        stdout=b"".join(lines),
        stderr=b"",
    )


def _slice3b1_p_data_expectation(candidate, repository: Path):
    expectation = _slice3b1_expectation(candidate, repository)
    literal_path = candidate._PARENT_V3_SIGNING_LITERALS_PATH
    _write_fixture_path(repository, literal_path, _PARENT_SIGNING_PLACEHOLDER_SOURCE)
    literal_entry = (
        literal_path,
        "100644",
        hashlib.sha256(_PARENT_SIGNING_PLACEHOLDER_SOURCE).hexdigest(),
    )
    return replace(
        expectation,
        source_closure=tuple(
            sorted(
                (*expectation.source_closure, literal_entry),
                key=lambda item: item[0].encode("utf-8"),
            )
        ),
    )


def _slice3b1_p_data_record(candidate, expectation) -> dict[str, str]:
    mode, raw_sha = {
        path: (mode, raw_sha)
        for path, mode, raw_sha in expectation.source_closure
    }[candidate._PARENT_V3_SIGNING_LITERALS_PATH]
    return {
        "execution_state": candidate._FRESH_AUDIT_P_DATA_STATE,
        "mode": mode,
        "path": candidate._PARENT_V3_SIGNING_LITERALS_PATH,
        "sha256": raw_sha,
    }


def test_security_s3p0_parent_assembles_exact_inert_p_data_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_p_data_expectation(candidate, tmp_path)
    nonce = "4" * 64
    record = _slice3b1_p_data_record(candidate, expectation)
    payload = _slice3b1_payload(
        candidate,
        expectation,
        nonce,
        p_data_states=[record],
    )
    completed = _security_s3p0_framed_completed(
        candidate,
        expectation,
        nonce,
        tmp_path,
        payload=payload,
    )
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)

    observed = candidate._assemble_fresh_audit_transcript(
        expectation,
        nonce,
        completed,
    )

    assert observed == payload
    assert observed["observed_p_data_states"] == [record]


@pytest.mark.parametrize(
    "attack",
    (
        "missing",
        "duplicate",
        "wrong-path",
        "wrong-sha",
        "wrong-mode",
        "wrong-state",
        "executed",
    ),
)
def test_security_s3p0_parent_rejects_inert_p_data_join_attacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_p_data_expectation(candidate, tmp_path)
    nonce = "4" * 64
    record = _slice3b1_p_data_record(candidate, expectation)
    records = [record]
    module_paths = None
    if attack == "missing":
        records = []
    elif attack == "duplicate":
        records = [record, dict(record)]
    elif attack == "wrong-path":
        records = [{**record, "path": "rulespace_v3/audit_fixture.py"}]
    elif attack == "wrong-sha":
        records = [{**record, "sha256": "9" * 64}]
    elif attack == "wrong-mode":
        records = [{**record, "mode": "100755"}]
    elif attack == "wrong-state":
        records = [{**record, "execution_state": "EXECUTED"}]
    else:
        module_paths = [
            "rulespace_v3/audit_fixture.py",
            "rulespace_v3/parent_candidate_v3.py",
            "rulespace_v3/parent_signing_literals_v1.py",
            "rulespace_v3/parent_v3_contracts.py",
        ]
    payload = _slice3b1_payload(
        candidate,
        expectation,
        nonce,
        module_paths=module_paths,
        p_data_states=records,
    )
    completed = _security_s3p0_framed_completed(
        candidate,
        expectation,
        nonce,
        tmp_path,
        payload=payload,
    )
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)

    with pytest.raises(ValueError, match="inert P data"):
        candidate._assemble_fresh_audit_transcript(
            expectation,
            nonce,
            completed,
        )


@pytest.mark.parametrize("attack", ("inject", "erase"))
def test_security_s3p0_parent_frame_chain_rejects_injection_and_erasure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    nonce = "4" * 64
    completed = _security_s3p0_framed_completed(
        candidate,
        expectation,
        nonce,
        tmp_path,
    )
    lines = completed.stdout.splitlines(keepends=True)
    if attack == "erase":
        del lines[2]
    else:
        fake_line, _ = candidate._encode_fresh_audit_frame(
            nonce=nonce,
            sequence=2,
            kind="file_read_path",
            payload="untracked-attacker.py",
            previous_frame_sha="f" * 64,
        )
        lines.insert(2, fake_line)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    with pytest.raises(ValueError, match="frame|chain|sequence"):
        candidate._assemble_fresh_audit_transcript(
            expectation,
            nonce,
            subprocess.CompletedProcess(
                completed.args,
                0,
                b"".join(lines),
                b"",
            ),
        )


def test_security_s3p0_parent_rejects_execute_bad_bytes_then_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    nonce = "4" * 64
    completed = _security_s3p0_framed_completed(
        candidate,
        expectation,
        nonce,
        tmp_path,
    )
    frames = [json.loads(line) for line in completed.stdout.splitlines()]
    target = next(
        frame
        for frame in frames
        if frame["kind"] == "source_execution"
        and frame["payload"]["path"] == "rulespace_v3/parent_candidate_v3.py"
    )
    target["payload"]["sha256"] = hashlib.sha256(b"attacker executed bytes").hexdigest()
    previous_sha = "0" * 64
    rebuilt: list[bytes] = []
    for sequence, frame in enumerate(frames):
        line, previous_sha = candidate._encode_fresh_audit_frame(
            nonce=nonce,
            sequence=sequence,
            kind=frame["kind"],
            payload=frame["payload"],
            previous_frame_sha=previous_sha,
        )
        rebuilt.append(line)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    with pytest.raises(ValueError, match="executed source bytes"):
        candidate._assemble_fresh_audit_transcript(
            expectation,
            nonce,
            subprocess.CompletedProcess(completed.args, 0, b"".join(rebuilt), b""),
        )


def test_security_s3p0_reviewed_code_cannot_forge_via_main_or_direct_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    _write_fixture_path(repository, "rulespace_v3/probe.py", b"PROBE = True\n")
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    with pytest.raises(ValueError, match="frame.*sequence|chain"):
        candidate._run_fresh_interpreter_event_boundary_probe(
            "authority-frame-forgery"
        )


def test_slice3b2_s2a_parent_freezes_exact_interpreter_and_dependency_roots() -> None:
    candidate = _candidate_module()
    roots = candidate._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS
    assert type(roots) is tuple
    assert roots
    assert roots == tuple(sorted(set(roots), key=lambda item: item.encode("utf-8")))
    repository_root = Path(candidate._REPOSITORY_ROOT).resolve(strict=True)
    for root in roots:
        assert type(root) is str
        path = Path(root)
        assert path.is_absolute()
        assert path.resolve(strict=True) == path
        assert path.is_dir()
        assert not path.is_relative_to(repository_root)
        assert not repository_root.is_relative_to(path)

    active_interpreter_roots = {
        str(Path(raw).resolve(strict=True))
        for raw in sys.path
        if raw
        and Path(raw).is_absolute()
        and Path(raw).is_dir()
        and not Path(raw).resolve(strict=True).is_relative_to(repository_root)
        and not repository_root.is_relative_to(Path(raw).resolve(strict=True))
    }
    assert active_interpreter_roots <= set(roots)

    configured = sysconfig.get_paths()
    inactive_configured_roots = {
        str(Path(configured[key]).resolve(strict=True))
        for key in ("stdlib", "platstdlib", "purelib", "platlib")
        if key in configured
        and Path(configured[key]).is_dir()
        and str(Path(configured[key]).resolve(strict=True))
        not in active_interpreter_roots
    }
    assert inactive_configured_roots.isdisjoint(roots)

    for module_name in ("numpy", "sympy"):
        spec = importlib.util.find_spec(module_name)
        if spec is None or not spec.submodule_search_locations:
            continue
        dependency_roots = {
            str(Path(location).resolve(strict=True).parent)
            for location in spec.submodule_search_locations
        }
        assert dependency_roots <= set(roots)


@pytest.mark.parametrize(
    "identity_attack",
    ("missing-root", "extra-root", "wrong-git", "wrong-python"),
)
def test_security_s2p0_frozen_process_identity_join_rejects_drift(
    identity_attack: str,
) -> None:
    candidate = _candidate_module()
    roots = list(candidate._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS)
    trusted_git = candidate._TRUSTED_GIT_EXECUTABLE_REALPATH
    trusted_python = candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH
    if identity_attack == "missing-root":
        roots.pop()
    elif identity_attack == "extra-root":
        roots.append("/nonexistent-attacker-root")
    elif identity_attack == "wrong-git":
        trusted_git = "/attacker/git"
    else:
        trusted_python = "/attacker/python"
    request = {
        "external_import_roots": roots,
        "trusted_git_executable_realpath": trusted_git,
        "trusted_python_executable_realpath": trusted_python,
    }

    with pytest.raises(RuntimeError, match="frozen process identity"):
        candidate._validate_fresh_audit_process_identity(request)


def test_slice3b2_s2b_real_isolated_dependency_import_smoke() -> None:
    candidate = _candidate_module()
    observed = candidate._run_fresh_interpreter_dependency_import_smoke()
    expected_modules = tuple(
        module_name
        for module_name in ("numpy", "scipy.linalg", "sympy")
        if importlib.util.find_spec(module_name) is not None
    )
    assert observed == {
        "audit_mode": candidate._FRESH_INTERPRETER_IMPORT_SMOKE_MODE,
        "dependency_initialization_state": (
            "NUMPY_TESTING_AND_SCIPY_LINALG_PRELOADED_WITH_LSCPU_BLOCKED_"
            "AND_SCHUR_EXECUTED_AFTER_DYNAMIC_LOCK"
        ),
        "hook_installation_state": candidate._FRESH_INTERPRETER_HOOK_STATE,
        "imported_dependency_modules": list(expected_modules),
        "python_executable_realpath": (
            candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    }


def test_slice3b2_s2b_scipy_linalg_is_preloaded_and_rechecked_after_lock() -> None:
    candidate = _candidate_module()
    source = candidate._FRESH_AUDIT_BOOTSTRAP
    dependency_phase_index = source.index("if audit_mode in (main_mode")
    scipy_preload_index = source.find(
        '__import__("scipy.linalg")',
        dependency_phase_index,
    )
    main_lock_index = source.find(
        "        lock_dynamic_loading()",
        dependency_phase_index,
    )
    smoke_index = source.index("if audit_mode == smoke_mode:")
    smoke_lock_index = source.find("        lock_dynamic_loading()", smoke_index)
    smoke_reimport_index = source.index(
        "        for module_name in dependency_modules:",
        smoke_index,
    )
    smoke_schur_index = source.find(".schur(", smoke_reimport_index)
    smoke_final_index = source.index(
        '        frame_writer(\n            "final",',
        smoke_index,
    )

    assert dependency_phase_index < scipy_preload_index < main_lock_index
    assert smoke_index < smoke_lock_index < smoke_reimport_index
    assert smoke_reimport_index < smoke_schur_index < smoke_final_index


def test_slice3b2_s2c_fresh_candidate_import_reuses_parent_direct_git() -> None:
    candidate = _candidate_module()
    observed = candidate._run_fresh_interpreter_candidate_import_smoke()
    assert observed == {
        "audit_mode": candidate._FRESH_INTERPRETER_CANDIDATE_IMPORT_SMOKE_MODE,
        "hook_installation_state": candidate._FRESH_INTERPRETER_HOOK_STATE,
        "imported_repository_module": "rulespace_v3.parent_candidate_v3",
        "module_external_import_roots": list(
            candidate._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS
        ),
        "module_trusted_git_executable_realpath": (
            candidate._TRUSTED_GIT_EXECUTABLE_REALPATH
        ),
        "module_trusted_python_executable_realpath": (
            candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
        "observed_git_commands": [],
        "observed_repository_directory_scans": [".", "rulespace_v3"],
        "python_executable_realpath": (
            candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    }


@pytest.mark.parametrize(
    "probe",
    (
        "git-metadata-open",
        "unknown-external-open",
        "repo-listdir",
        "repo-scandir",
        "chdir",
        "non-git-process",
    ),
)
def test_slice3b2_s2d_hook_rejects_forbidden_path_and_process_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    _write_fixture_path(
        repository,
        "rulespace_v3/probe.py",
        b"PROBE = True\n",
    )
    _write_fixture_path(repository, ".git", b"gitdir: elsewhere\n")
    _write_fixture_path(tmp_path, ".venv/evil.py", b"EVIL = True\n")
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    completed = candidate._run_fresh_interpreter_event_boundary_probe(probe)
    assert completed.returncode != 0
    assert completed.stdout == b""
    assert b"RuntimeError" in completed.stderr
    assert not (repository / "process-marker").exists()


def test_slice3b2_s2d_hook_records_allowed_repository_file_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    _write_fixture_path(
        repository,
        "rulespace_v3/probe.py",
        b"PROBE = True\n",
    )
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    completed = candidate._run_fresh_interpreter_event_boundary_probe("repo-read")
    assert completed.returncode == 0
    assert completed.stderr == b""
    observed = json.loads(completed.stdout)
    assert observed["observed_file_read_paths"] == [
        "rulespace_v3/probe.py"
    ]


def test_slice3b2_s2d_hook_allows_only_exact_system_entropy_device(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    _write_fixture_path(repository, "rulespace_v3/probe.py", b"PROBE = True\n")
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    completed = candidate._run_fresh_interpreter_event_boundary_probe(
        "system-entropy"
    )
    assert completed.returncode == 0
    assert completed.stderr == b""
    observed = json.loads(completed.stdout)
    assert observed["observed_file_read_paths"] == []


@pytest.mark.parametrize(
    "probe",
    (
        "ctypes-repository",
        "ctypes-unknown-external",
        "unknown-external-module",
    ),
)
def test_slice3b2_s2e_hook_rejects_dlopen_and_postscan_escapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    _write_fixture_path(
        repository,
        "rulespace_v3/probe.py",
        b"PROBE = True\n",
    )
    _write_fixture_path(tmp_path, ".venv/evil.py", b"EVIL = True\n")
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    completed = candidate._run_fresh_interpreter_event_boundary_probe(probe)
    assert completed.returncode != 0
    assert completed.stdout == b""
    assert b"RuntimeError" in completed.stderr


def test_slice3b2_s2e_hook_allows_and_records_external_root_dlopen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    _write_fixture_path(
        repository,
        "rulespace_v3/probe.py",
        b"PROBE = True\n",
    )
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    completed = candidate._run_fresh_interpreter_event_boundary_probe(
        "ctypes-allowed-external"
    )
    assert completed.returncode == 0
    assert completed.stderr == b""
    observed = json.loads(completed.stdout)
    assert len(observed["observed_dynamic_library_paths"]) == 1
    dynamic_library = Path(observed["observed_dynamic_library_paths"][0])
    assert dynamic_library.is_absolute()
    assert dynamic_library.resolve(strict=True) == dynamic_library
    assert any(
        dynamic_library.is_relative_to(Path(root))
        for root in candidate._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS
    )


@pytest.mark.parametrize("stream_name", ("stdout", "stderr"))
def test_slice3b2_s2g_bounded_runner_kills_stream_overflow_immediately(
    tmp_path: Path,
    stream_name: str,
) -> None:
    candidate = _candidate_module()
    marker = tmp_path / f"{stream_name}-child-survived"
    limit = (
        candidate._FRESH_AUDIT_MAX_STDOUT_BYTES
        if stream_name == "stdout"
        else candidate._FRESH_AUDIT_MAX_STDERR_BYTES
    )
    script = (
        "import sys,time\n"
        "stream = getattr(sys, sys.argv[2]).buffer\n"
        "stream.write(b'x' * (int(sys.argv[3]) + 1))\n"
        "stream.flush()\n"
        "time.sleep(30)\n"
        "open(sys.argv[1], 'wb').write(b'survived')\n"
    )
    command = (
        candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH,
        "-I",
        "-S",
        "-c",
        script,
        str(marker),
        stream_name,
        str(limit),
    )
    started = time.monotonic()
    with pytest.raises(ValueError, match=f"{stream_name}.*limit"):
        candidate._run_bounded_fresh_interpreter(
            command,
            cwd=tmp_path,
            input_bytes=b"",
            timeout_seconds=20,
        )
    assert time.monotonic() - started < 5
    assert not marker.exists()


def test_security_s3p0_fresh_python_pin_is_secure_same_inode_hardlink(
    tmp_path: Path,
) -> None:
    candidate = _candidate_module()
    with candidate._pinned_trusted_python_executable(
        temporary_parent=tmp_path,
    ) as pinned:
        pinned_path = Path(pinned)
        source = os.stat(candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH)
        observed = pinned_path.stat()
        assert pinned_path != Path(candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH)
        assert (observed.st_dev, observed.st_ino) == (source.st_dev, source.st_ino)
        assert stat.S_IMODE(pinned_path.parent.stat().st_mode) == 0o700
    assert tuple(tmp_path.iterdir()) == ()


def test_security_s3p0_fresh_python_pin_fails_closed_and_cleans_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()

    def denied_link(*_args, **_kwargs):
        raise OSError("cross-device or denied")

    monkeypatch.setattr(candidate.os, "link", denied_link)
    with pytest.raises(ValueError, match="hardlink pin"):
        with candidate._pinned_trusted_python_executable(
            temporary_parent=tmp_path,
        ):
            pytest.fail("pinning must not fall back to a pathname exec")
    assert tuple(tmp_path.iterdir()) == ()


def test_security_s3p0_nonframework_python_pin_reuses_existing_secure_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    monkeypatch.setattr(candidate, "_TRUSTED_PYTHON_FRAMEWORK_IDENTITY", None)
    monkeypatch.setattr(candidate, "_TRUSTED_PYTHON_FRAMEWORK_REALPATH", None)
    with candidate._pinned_trusted_python_executable(
        temporary_parent=tmp_path,
    ) as pinned:
        assert Path(pinned).parent.parent == tmp_path
        assert Path(pinned).is_file()
    assert tuple(tmp_path.iterdir()) == ()


def test_security_s3p0_fresh_runner_executes_only_the_private_python_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    observed: list[tuple[str, ...]] = []

    def bounded(command, **_kwargs):
        command = tuple(command)
        observed.append(command)
        executable = Path(command[0])
        assert executable != Path(candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH)
        assert (executable.stat().st_dev, executable.stat().st_ino) == (
            candidate._TRUSTED_PYTHON_EXECUTABLE_IDENTITY.st_dev,
            candidate._TRUSTED_PYTHON_EXECUTABLE_IDENTITY.st_ino,
        )
        return subprocess.CompletedProcess(command, 0, b"ok", b"")

    monkeypatch.setattr(candidate, "_run_bounded_process", bounded)
    result = candidate._run_bounded_fresh_interpreter(
        (
            candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH,
            "-I",
            "-S",
            "-c",
            "pass",
        ),
        cwd=tmp_path,
        input_bytes=b"",
        timeout_seconds=1,
    )
    assert result.stdout == b"ok"
    assert len(observed) == 1
    assert not Path(observed[0][0]).exists()


def _signed_literal_preload_fixture(
    candidate,
    repository: Path,
    *,
    candidate_source: bytes = b"CANDIDATE_IMPORT_SMOKE = True\n",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    literal_path = candidate._PARENT_V3_SIGNING_LITERALS_PATH
    identity_source = (
        f"_TRUSTED_GIT_EXECUTABLE_REALPATH = "
        f"{candidate._TRUSTED_GIT_EXECUTABLE_REALPATH!r}\n"
        f"_TRUSTED_PYTHON_EXECUTABLE_REALPATH = "
        f"{candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH!r}\n"
        f"_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS = "
        f"{candidate._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS!r}\n"
        "def _validate_fresh_audit_process_identity(request):\n"
        "    if (request['trusted_git_executable_realpath'] != "
        "_TRUSTED_GIT_EXECUTABLE_REALPATH or "
        "request['trusted_python_executable_realpath'] != "
        "_TRUSTED_PYTHON_EXECUTABLE_REALPATH or "
        "request['external_import_roots'] != "
        "list(_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS)):\n"
        "        raise RuntimeError('fresh-audit child frozen process identity drifted')\n"
    ).encode("utf-8")
    live_by_path = {
        "rulespace_v3/__init__.py": b"",
        "rulespace_v3/parent_candidate_v3.py": identity_source + candidate_source,
        literal_path: b"SIGNED_LITERAL = 'S'\n",
    }
    for relative_path, raw in live_by_path.items():
        _write_fixture_path(repository, relative_path, raw)
    source_closure = [
        {
            "path": relative_path,
            "mode": "100644",
            "sha256": hashlib.sha256(
                _PARENT_SIGNING_PLACEHOLDER_SOURCE
                if relative_path == literal_path
                else raw
            ).hexdigest(),
        }
        for relative_path, raw in sorted(live_by_path.items())
    ]
    p_data_not_executed = [
        {
            "execution_state": candidate._FRESH_AUDIT_P_DATA_STATE,
            "mode": "100644",
            "path": literal_path,
            "sha256": hashlib.sha256(
                _PARENT_SIGNING_PLACEHOLDER_SOURCE
            ).hexdigest(),
            "source_base64": base64.b64encode(
                _PARENT_SIGNING_PLACEHOLDER_SOURCE
            ).decode("ascii"),
        }
    ]
    return source_closure, p_data_not_executed


def _run_signed_literal_preload_probe(
    candidate,
    repository: Path,
    pycache_root: Path,
    *,
    source_closure: list[dict[str, str]],
    p_data_not_executed: list[dict[str, str]],
) -> tuple[str, subprocess.CompletedProcess[bytes]]:
    pycache_root.mkdir()
    nonce = "7" * 64
    request = {
        "audit_mode": candidate._FRESH_INTERPRETER_CANDIDATE_IMPORT_SMOKE_MODE,
        "external_import_roots": list(candidate._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS),
        "nonce": nonce,
        "p_data_not_executed": p_data_not_executed,
        "source_closure": source_closure,
        "trusted_git_executable_realpath": candidate._TRUSTED_GIT_EXECUTABLE_REALPATH,
        "trusted_python_executable_realpath": (
            candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    }
    command = (
        candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH,
        "-I",
        "-S",
        "-B",
        "-X",
        f"pycache_prefix={pycache_root.resolve(strict=True)}",
        "-c",
        candidate._FRESH_AUDIT_BOOTSTRAP,
    )
    completed = candidate._run_bounded_fresh_interpreter(
        command,
        cwd=repository,
        input_bytes=_canonical_json_line(request),
        timeout_seconds=30,
    )
    return nonce, completed


def test_security_s3p0_signed_literal_transport_reads_p_blob_not_live_s(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "V3-M0 Test")
    _git(repository, "config", "user.email", "v3m0@example.invalid")
    literal_path = candidate._PARENT_V3_SIGNING_LITERALS_PATH
    _write_fixture_path(repository, literal_path, _PARENT_SIGNING_PLACEHOLDER_SOURCE)
    _git(repository, "add", "--", ".")
    _git(repository, "commit", "-qm", "preparation P")
    preparation_commit = _git(repository, "rev-parse", "HEAD").decode().strip()
    live_s = b"SIGNED_LITERAL = 'S'\n"
    _write_fixture_path(repository, literal_path, live_s)
    _git(repository, "add", "--", literal_path)
    _git(repository, "commit", "-qm", "signing S")
    expected_sha = hashlib.sha256(_PARENT_SIGNING_PLACEHOLDER_SOURCE).hexdigest()
    preparation_tree = _git(
        repository,
        "rev-parse",
        f"{preparation_commit}^{{tree}}",
    ).decode().strip()
    expectation = candidate._FreshInterpreterAuditExpectation(
        preparation_commit_sha=preparation_commit,
        preparation_tree_sha=preparation_tree,
        candidate_sha="1" * 64,
        source_closure_sha="2" * 64,
        source_closure=((literal_path, "100644", expected_sha),),
        trusted_git_executable_realpath=(
            candidate._TRUSTED_GIT_EXECUTABLE_REALPATH
        ),
        trusted_python_executable_realpath=(
            candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    )
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    monkeypatch.setattr(parent_v3_contracts, "_REPOSITORY_ROOT", repository)

    observed = candidate._build_fresh_audit_p_data_not_executed(expectation)

    assert observed == [
        {
            "execution_state": candidate._FRESH_AUDIT_P_DATA_STATE,
            "mode": "100644",
            "path": literal_path,
            "sha256": expected_sha,
            "source_base64": base64.b64encode(
                _PARENT_SIGNING_PLACEHOLDER_SOURCE
            ).decode("ascii"),
        }
    ]
    assert base64.b64decode(observed[0]["source_base64"], validate=True) != live_s


def test_security_s3p0_signed_literal_p_data_is_verified_but_not_preloaded(
    tmp_path: Path,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    repository.mkdir()
    closure, p_data = _signed_literal_preload_fixture(candidate, repository)

    nonce, completed = _run_signed_literal_preload_probe(
        candidate,
        repository,
        tmp_path / "pycache",
        source_closure=closure,
        p_data_not_executed=p_data,
    )

    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    frames = candidate._decode_fresh_audit_frames(nonce, completed)
    state_frames = [frame for frame in frames if frame["kind"] == "p_data_state"]
    assert [frame["payload"] for frame in state_frames] == [
        {
            "execution_state": candidate._FRESH_AUDIT_P_DATA_STATE,
            "mode": p_data[0]["mode"],
            "path": p_data[0]["path"],
            "sha256": p_data[0]["sha256"],
        }
    ]
    assert all(
        frame["payload"].get("path") != candidate._PARENT_V3_SIGNING_LITERALS_PATH
        for frame in frames
        if frame["kind"] == "source_execution"
    )


def test_security_s3p0_import_of_nonexecuted_signed_literal_fails_closed(
    tmp_path: Path,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    repository.mkdir()
    closure, p_data = _signed_literal_preload_fixture(
        candidate,
        repository,
        candidate_source=b"from . import parent_signing_literals_v1\n",
    )

    _nonce, completed = _run_signed_literal_preload_probe(
        candidate,
        repository,
        tmp_path / "pycache",
        source_closure=closure,
        p_data_not_executed=p_data,
    )

    assert completed.returncode != 0
    assert b"outside stable source closure" in completed.stderr


def test_security_s3p0_nonallowlisted_python_live_drift_still_fails_closed(
    tmp_path: Path,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    repository.mkdir()
    closure, p_data = _signed_literal_preload_fixture(candidate, repository)
    other_path = "rulespace_v3/other.py"
    live_other = b"LIVE_OTHER = 'S'\n"
    _write_fixture_path(repository, other_path, live_other)
    closure.append(
        {
            "path": other_path,
            "mode": "100644",
            "sha256": hashlib.sha256(b"P_OTHER = True\n").hexdigest(),
        }
    )
    closure.sort(key=lambda item: item["path"].encode("utf-8"))

    _nonce, completed = _run_signed_literal_preload_probe(
        candidate,
        repository,
        tmp_path / "pycache",
        source_closure=closure,
        p_data_not_executed=p_data,
    )

    assert completed.returncode != 0
    assert b"live source differs from P" in completed.stderr


def test_security_s3p0_corrupt_signed_literal_p_transport_fails_closed(
    tmp_path: Path,
) -> None:
    candidate = _candidate_module()
    repository = tmp_path / "repository"
    repository.mkdir()
    closure, p_data = _signed_literal_preload_fixture(candidate, repository)
    p_data[0]["source_base64"] = base64.b64encode(b"attacker P bytes\n").decode(
        "ascii"
    )

    _nonce, completed = _run_signed_literal_preload_probe(
        candidate,
        repository,
        tmp_path / "pycache",
        source_closure=closure,
        p_data_not_executed=p_data,
    )

    assert completed.returncode != 0
    assert b"transported P data" in completed.stderr


def test_slice3b1_validator_accepts_one_canonical_nonce_bound_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    nonce = "4" * 64
    payload = _slice3b1_payload(candidate, expectation, nonce)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    observed = candidate._validate_fresh_interpreter_audit_output(
        expectation,
        nonce,
        subprocess.CompletedProcess(
            args=("python",),
            returncode=0,
            stdout=_canonical_json_line(payload),
            stderr=b"",
        ),
    )
    assert observed == payload


@pytest.mark.parametrize(
    "attacker_argv",
    (
        lambda candidate, expectation: [
            expectation.trusted_git_executable_realpath,
            "cat-file",
            "-t",
            "9" * 40,
        ],
        lambda candidate, expectation: [
            expectation.trusted_git_executable_realpath,
            "cat-file",
            "blob",
            expectation.preparation_commit_sha + ":outside/attacker.py",
        ],
        lambda candidate, expectation: [
            expectation.trusted_git_executable_realpath,
            "ls-tree",
            "-z",
            "9" * 40,
            "--",
            expectation.source_closure[0][0],
        ],
        lambda candidate, expectation: [
            expectation.trusted_git_executable_realpath,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        ],
    ),
)
def test_security_s2p0_validator_rejects_git_targets_outside_private_p_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attacker_argv,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    nonce = "4" * 64
    payload = _slice3b1_payload(candidate, expectation, nonce)
    payload["observed_git_commands"][0]["argv"] = attacker_argv(
        candidate,
        expectation,
    )
    _resign_slice3b1_payload(payload)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    with pytest.raises(ValueError, match="allowlisted"):
        candidate._validate_fresh_interpreter_audit_output(
            expectation,
            nonce,
            subprocess.CompletedProcess(
                args=(candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH,),
                returncode=0,
                stdout=_canonical_json_line(payload),
                stderr=b"",
            ),
        )


@pytest.mark.parametrize(
    "wire_kind",
    ("nonzero", "stderr", "noisy", "noncanonical", "oversize", "duplicate-key"),
)
def test_slice3b1_validator_rejects_bad_process_and_json_wires(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wire_kind: str,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    nonce = "4" * 64
    payload = _slice3b1_payload(candidate, expectation, nonce)
    stdout = _canonical_json_line(payload)
    returncode = 0
    stderr = b""
    if wire_kind == "nonzero":
        returncode = 7
    elif wire_kind == "stderr":
        stderr = b"diagnostic"
    elif wire_kind == "noisy":
        stdout = b"noise\n" + stdout
    elif wire_kind == "noncanonical":
        stdout = json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"
    elif wire_kind == "oversize":
        stdout = b"x" * (candidate._FRESH_AUDIT_MAX_STDOUT_BYTES + 1)
    else:
        stdout = stdout.replace(
            b'{"audit_mode":',
            b'{"audit_mode":"duplicate","audit_mode":',
            1,
        )
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    with pytest.raises(ValueError):
        candidate._validate_fresh_interpreter_audit_output(
            expectation,
            nonce,
            subprocess.CompletedProcess(
                args=("python",),
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            ),
        )


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    (
        ("wrong-nonce", ValueError),
        ("wrong-schema", ValueError),
        ("wrong-mode", ValueError),
        ("wrong-p", ValueError),
        ("wrong-tree", ValueError),
        ("wrong-python", ValueError),
        ("wrong-candidate", ValueError),
        ("wrong-source", ValueError),
        ("wrong-hook", ValueError),
        ("omit-required-module", ValueError),
        ("wrong-observation-sha", ValueError),
        ("unsorted", ValueError),
        ("duplicate", ValueError),
        ("outside-closure", ValueError),
        ("repo-pyc", ValueError),
        ("sibling-worktree", ValueError),
        ("directory-scan-drift", ValueError),
        ("repo-dlopen", ValueError),
        ("bad-git-command", ValueError),
        ("bad-git-shape", ValueError),
        ("bad-git-executable", ValueError),
        ("bad-git-argv0", ValueError),
        ("bad-git-cwd", ValueError),
        ("shell", ValueError),
    ),
)
def test_slice3b1_validator_rejects_protocol_and_observation_attacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected_error: type[Exception],
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    nonce = "4" * 64
    payload = _slice3b1_payload(candidate, expectation, nonce)
    if mutation == "wrong-nonce":
        payload["nonce"] = "5" * 64
    elif mutation == "wrong-schema":
        payload["audit_schema_version"] = "attacker"
    elif mutation == "wrong-mode":
        payload["audit_mode"] = "attacker"
    elif mutation == "wrong-p":
        payload["preparation_commit_sha"] = "6" * 40
    elif mutation == "wrong-tree":
        payload["preparation_tree_sha"] = "6" * 40
    elif mutation == "wrong-python":
        payload["python_executable_realpath"] = "/tmp/attacker/python"
    elif mutation == "wrong-candidate":
        payload["candidate_sha"] = "6" * 64
    elif mutation == "wrong-source":
        payload["source_closure_sha"] = "6" * 64
    elif mutation == "wrong-hook":
        payload["hook_installation_state"] = "IMPORT_BEFORE_HOOK"
    elif mutation == "omit-required-module":
        payload["observed_module_paths"].remove(
            "rulespace_v3/parent_candidate_v3.py"
        )
    elif mutation == "wrong-observation-sha":
        payload["observation_sha"] = "f" * 64
    elif mutation == "unsorted":
        payload["observed_module_paths"] = [
            "rulespace_v3/z.py",
            "rulespace_v3/audit_fixture.py",
        ]
    elif mutation == "duplicate":
        payload["observed_module_paths"] = [
            "rulespace_v3/audit_fixture.py",
            "rulespace_v3/audit_fixture.py",
        ]
    elif mutation == "outside-closure":
        payload["observed_file_read_paths"] = ["untracked.py"]
        _write_fixture_path(tmp_path, "untracked.py", b"untracked\n")
    elif mutation == "repo-pyc":
        payload["observed_file_read_paths"] = [
            "rulespace_v3/__pycache__/audit_fixture.pyc"
        ]
        _write_fixture_path(
            tmp_path,
            "rulespace_v3/__pycache__/audit_fixture.pyc",
            b"pyc",
        )
    elif mutation == "sibling-worktree":
        payload["observed_file_read_paths"] = ["../sibling/worktree.py"]
    elif mutation == "directory-scan-drift":
        payload["observed_repository_directory_scans"] = ["rulespace_v3"]
    elif mutation == "repo-dlopen":
        payload["observed_dynamic_library_paths"] = [
            str((tmp_path / "rulespace_v3/audit_fixture.py").resolve())
        ]
    elif mutation == "bad-git-command":
        payload["observed_git_commands"][0]["argv"] = [
            expectation.trusted_git_executable_realpath,
            "show",
            "HEAD",
        ]
    elif mutation == "bad-git-shape":
        payload["observed_git_commands"][0]["argv"] = [
            expectation.trusted_git_executable_realpath,
            "cat-file",
            "--batch",
        ]
    elif mutation == "bad-git-executable":
        payload["observed_git_commands"][0]["executable_realpath"] = (
            "/tmp/attacker/git"
        )
    elif mutation == "bad-git-argv0":
        payload["observed_git_commands"][0]["argv"][0] = "/tmp/attacker/git"
    elif mutation == "bad-git-cwd":
        payload["observed_git_commands"][0]["cwd_state"] = "SIBLING_WORKTREE"
    else:
        payload["observed_git_commands"][0]["shell"] = True
    if mutation != "wrong-observation-sha":
        _resign_slice3b1_payload(payload)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    with pytest.raises(expected_error):
        candidate._validate_fresh_interpreter_audit_output(
            expectation,
            nonce,
            subprocess.CompletedProcess(
                args=("python",),
                returncode=0,
                stdout=_canonical_json_line(payload),
                stderr=b"",
            ),
        )


@pytest.mark.parametrize("filesystem_attack", ("missing", "symlink", "sha", "mode"))
def test_slice3b1_validator_rejects_live_file_drift_from_p_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filesystem_attack: str,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    path = tmp_path / "rulespace_v3/audit_fixture.py"
    if filesystem_attack == "missing":
        path.unlink()
    elif filesystem_attack == "symlink":
        path.unlink()
        path.symlink_to(tmp_path / "outside.py")
    elif filesystem_attack == "sha":
        path.write_bytes(b"drift\n")
    else:
        path.chmod(0o755)
    nonce = "4" * 64
    payload = _slice3b1_payload(candidate, expectation, nonce)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    with pytest.raises(ValueError):
        candidate._validate_fresh_interpreter_audit_output(
            expectation,
            nonce,
            subprocess.CompletedProcess(
                args=("python",),
                returncode=0,
                stdout=_canonical_json_line(payload),
                stderr=b"",
            ),
        )


def test_slice3b3_live_validator_binds_inode_across_lstat_open_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    live_path = tmp_path / "rulespace_v3/audit_fixture.py"
    replacement = tmp_path / "replacement.py"
    replacement.write_bytes(b"ATTACK_FIXTURE = 000\n")
    assert replacement.stat().st_size == live_path.stat().st_size
    real_open = os.open
    swapped = False

    def swapping_open(raw_path, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and Path(raw_path) == live_path:
            swapped = True
            os.replace(replacement, live_path)
        return real_open(raw_path, flags, *args, **kwargs)

    monkeypatch.setattr(candidate.os, "open", swapping_open)
    nonce = "4" * 64
    payload = _slice3b1_payload(candidate, expectation, nonce)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    with pytest.raises(ValueError, match="changed|race|inode"):
        candidate._validate_fresh_interpreter_audit_output(
            expectation,
            nonce,
            subprocess.CompletedProcess(
                args=("python",),
                returncode=0,
                stdout=_canonical_json_line(payload),
                stderr=b"",
            ),
        )
    assert swapped is True


def test_slice3b1_runner_uses_fixed_isolated_command_and_rejects_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(
        candidate,
        "_fresh_audit_expectation_from_candidate",
        lambda _candidate: expectation,
    )
    observed_calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def successful_run(command, **kwargs):
        command = tuple(command)
        observed_calls.append((command, kwargs))
        request = json.loads(kwargs["input_bytes"])
        nonce = request["nonce"]
        completed = _security_s3p0_framed_completed(
            candidate,
            expectation,
            nonce,
            tmp_path,
        )
        return subprocess.CompletedProcess(
            command,
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )

    monkeypatch.setattr(candidate, "_run_bounded_fresh_interpreter", successful_run)
    result = candidate._run_fresh_interpreter_completeness_audit(object())
    assert result["candidate_sha"] == expectation.candidate_sha
    command, kwargs = observed_calls[0]
    assert command[0] == candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH
    assert command[1:5] == ("-I", "-S", "-B", "-X")
    assert command[6:] == ("-c", candidate._FRESH_AUDIT_BOOTSTRAP)
    assert kwargs["cwd"] == tmp_path
    assert kwargs["timeout_seconds"] == candidate._FRESH_AUDIT_TIMEOUT_SECONDS
    request = json.loads(kwargs["input_bytes"])
    assert set(request) == {
        "audit_mode",
        "preparation_commit_sha",
            "preparation_tree_sha",
            "nonce",
            "p_data_not_executed",
        "trusted_git_executable_realpath",
        "trusted_python_executable_realpath",
        "external_import_roots",
        "source_closure",
    }
    assert request["audit_mode"] == candidate._FRESH_INTERPRETER_AUDIT_MODE
    assert request["preparation_commit_sha"] == expectation.preparation_commit_sha
    assert request["preparation_tree_sha"] == expectation.preparation_tree_sha
    assert (
        request["trusted_git_executable_realpath"]
        == expectation.trusted_git_executable_realpath
    )
    assert (
        request["trusted_python_executable_realpath"]
        == expectation.trusted_python_executable_realpath
    )
    assert request["external_import_roots"] == list(
        candidate._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS
    )
    assert request["source_closure"] == [
        {"path": path, "mode": mode, "sha256": raw_sha}
        for path, mode, raw_sha in expectation.source_closure
    ]
    assert request["p_data_not_executed"] == []
    assert all(
        not Path(root).is_relative_to(tmp_path.resolve())
        for root in request["external_import_roots"]
    )
    assert kwargs["input_bytes"] == _canonical_json_line(request)

    def timeout_run(*_args, **_kwargs):
        raise ValueError("fresh-interpreter child timed out")

    monkeypatch.setattr(candidate, "_run_bounded_fresh_interpreter", timeout_run)
    with pytest.raises(ValueError, match="timed out"):
        candidate._run_fresh_interpreter_completeness_audit(object())


def test_slice3b3_child_receives_no_authority_transcript_and_returns_only_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    preparation_commit_sha = "1" * 40
    preparation_tree_sha = "2" * 40
    source_closure = (("rulespace_v3/a.py", "100644", "3" * 64),)
    replayed = SimpleNamespace(
        preparation_commit_sha=preparation_commit_sha,
        candidate_sha="4" * 64,
        source_closure_sha="5" * 64,
        source_closure=source_closure,
    )
    events: list[str] = []
    request = {
        "audit_mode": candidate._FRESH_INTERPRETER_AUDIT_MODE,
        "external_import_roots": list(candidate._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS),
        "nonce": "6" * 64,
        "p_data_not_executed": [],
        "preparation_commit_sha": preparation_commit_sha,
        "preparation_tree_sha": preparation_tree_sha,
        "source_closure": [
            {
                "path": "rulespace_v3/a.py",
                "mode": "100644",
                "sha256": "3" * 64,
            }
        ],
        "trusted_git_executable_realpath": candidate._TRUSTED_GIT_EXECUTABLE_REALPATH,
        "trusted_python_executable_realpath": (
            candidate._TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    }
    monkeypatch.setattr(
        candidate,
        "_require_preparation_commit_sha",
        lambda value: events.append("require-p")
        or (value, preparation_tree_sha),
    )
    monkeypatch.setattr(
        candidate,
        "_enumerate_parent_v3_source_entries_at_preparation_commit",
        lambda value: events.append("enumerate")
        or (("rulespace_v3/a.py", "100644", "7" * 40),),
        raising=False,
    )
    monkeypatch.setattr(
        candidate,
        "_replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit",
        lambda value: events.append("replay") or replayed,
    )
    monkeypatch.setattr(
        candidate,
        "_exact_record",
        lambda *_args: events.append("exact-record"),
    )
    monkeypatch.setattr(
        candidate,
        "_require_exact_wire_tree",
        lambda *_args: events.append("recursive-exact"),
    )
    monkeypatch.setattr(
        candidate,
        "_verify_parent_candidate_v3_roots_and_registry",
        lambda *_args: events.append("roots"),
    )

    payload = candidate._fresh_audit_child_main(request)
    assert events == [
        "require-p",
        "enumerate",
        "replay",
        "exact-record",
        "recursive-exact",
        "roots",
    ]
    assert payload["candidate_sha"] == replayed.candidate_sha
    assert payload["source_closure_sha"] == replayed.source_closure_sha
    assert set(payload) == {
        "audit_schema_version",
        "audit_mode",
        "nonce",
        "preparation_commit_sha",
        "preparation_tree_sha",
        "python_executable_realpath",
        "candidate_sha",
        "source_closure_sha",
    }


def test_slice3b3_public_verifier_audits_then_snapshots_then_freezes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    preparation_commit_sha = "1" * 40
    source_closure = (("alpha.py", "100644", "2" * 64),)
    declared = SimpleNamespace(
        preparation_commit_sha=preparation_commit_sha,
        source_closure=source_closure,
    )
    replayed = object()
    events: list[str] = []
    monkeypatch.setattr(candidate, "PARENT_V3_SOURCE_CLOSURE_PATHS", ())
    monkeypatch.setattr(
        candidate,
        "_exact_record",
        lambda *_args: events.append("declared-exact"),
    )
    monkeypatch.setattr(
        candidate,
        "_require_exact_wire_tree",
        lambda value, *_args: events.append(
            "declared-wire" if value is declared else "replay-wire"
        ),
    )
    monkeypatch.setattr(
        candidate,
        "_verify_parent_candidate_v3_roots_and_registry",
        lambda *_args: events.append("declared-roots"),
    )
    monkeypatch.setattr(
        candidate,
        "_replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit",
        lambda value: events.append("replay") or replayed,
    )
    monkeypatch.setattr(
        candidate,
        "_require_exact_recursive_match",
        lambda *_args: events.append("recursive-match"),
    )
    monkeypatch.setattr(
        candidate,
        "_run_fresh_interpreter_completeness_audit",
        lambda value: events.append("audit") or {"candidate": value},
    )
    monkeypatch.setattr(
        candidate,
        "_snapshot_clean_verification_head",
        lambda: events.append("snapshot") or preparation_commit_sha,
        raising=False,
    )
    monkeypatch.setattr(
        candidate,
        "_freeze_parent_v3_source_closure_paths",
        lambda closure: events.append("freeze") or tuple(item[0] for item in closure),
    )
    assert candidate.verify_parent_freeze_candidate_v3(declared) is declared
    assert events == [
        "snapshot",
        "declared-exact",
        "declared-wire",
        "declared-roots",
        "replay",
        "replay-wire",
        "recursive-match",
        "audit",
        "snapshot",
        "freeze",
    ]

    events.clear()
    monkeypatch.setattr(
        candidate,
        "_run_fresh_interpreter_completeness_audit",
        lambda _value: events.append("audit")
        or (_ for _ in ()).throw(ValueError("audit failed")),
    )
    with pytest.raises(ValueError, match="audit failed"):
        candidate.verify_parent_freeze_candidate_v3(declared)
    assert events[-1] == "audit"
    assert events.count("snapshot") == 1
    assert "freeze" not in events
    assert candidate.PARENT_V3_SOURCE_CLOSURE_PATHS == ()

    events.clear()
    successor_snapshots = iter(("7" * 40, "8" * 40))
    monkeypatch.setattr(
        candidate,
        "_run_fresh_interpreter_completeness_audit",
        lambda value: events.append("audit") or {"candidate": value},
    )
    monkeypatch.setattr(
        candidate,
        "_snapshot_clean_verification_head",
        lambda: events.append("snapshot") or next(successor_snapshots),
    )
    with pytest.raises(ValueError, match="verification HEAD changed"):
        candidate.verify_parent_freeze_candidate_v3(declared)
    assert events[-2:] == ["audit", "snapshot"]
    assert "freeze" not in events
    assert candidate.PARENT_V3_SOURCE_CLOSURE_PATHS == ()


def test_slice3b3_verification_snapshot_accepts_clean_signed_successor_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository, preparation_commit_sha, _included = (
        _new_source_fixture_repository(tmp_path)
    )
    for path, signed_status in _MANDATORY_SIGNED_STATUS_BY_PATH.items():
        _write_fixture_path(
            repository,
            path,
            (signed_status + "\n\nallowlisted signing successor\n").encode("utf-8"),
        )
    for receipt_path in (
        "data/results/v3m0_parent_v3_review_authority.json",
        "data/results/v3m0_parent_v3_review_mathematics.json",
    ):
        _write_fixture_path(repository, receipt_path, b"{}\n")
    _write_fixture_path(
        repository,
        "rulespace_v3/parent_signing_literals_v1.py",
        _PARENT_SIGNING_PLACEHOLDER_SOURCE.replace(
            b"PARENT_V3_PREPARATION_COMMIT_SHA: str | None = None",
            (
                b'PARENT_V3_PREPARATION_COMMIT_SHA: str | None = "'
                + preparation_commit_sha.encode("ascii")
                + b'"'
            ),
        ),
    )
    _git(repository, "add", "--", ".")
    _git(repository, "commit", "-qm", "allowlisted signed successor")
    signed_commit_sha = _git(repository, "rev-parse", "HEAD").decode().strip()
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    assert candidate._snapshot_clean_verification_head() == signed_commit_sha
    assert signed_commit_sha != preparation_commit_sha


def test_slice3b4_real_p_candidate_verifies_from_clean_signed_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_module = _candidate_module()
    repository = _new_full_candidate_repository(tmp_path)
    monkeypatch.setattr(candidate_module, "_REPOSITORY_ROOT", repository)
    monkeypatch.setattr(parent_v3_contracts, "_REPOSITORY_ROOT", repository)
    monkeypatch.setattr(candidate_module, "PARENT_V3_SOURCE_CLOSURE_PATHS", ())

    # The verifier below executes the same actual fresh child against P.  Avoid
    # paying for an identical child twice in this already-full replay e2e; the
    # builder's audit ordering/fail-closed behavior is covered independently.
    real_fresh_audit = candidate_module._run_fresh_interpreter_completeness_audit
    monkeypatch.setattr(
        candidate_module,
        "_run_fresh_interpreter_completeness_audit",
        lambda _candidate: {"deduplicated_in_e2e": True},
    )
    parent_candidate = candidate_module.build_v3m0_parent_freeze_candidate_v3()
    monkeypatch.setattr(
        candidate_module,
        "_run_fresh_interpreter_completeness_audit",
        real_fresh_audit,
    )
    preparation_commit_sha = parent_candidate.preparation_commit_sha
    candidate_sha = parent_candidate.candidate_sha
    source_closure_sha = parent_candidate.source_closure_sha
    assert preparation_commit_sha == _git(
        repository, "rev-parse", "HEAD"
    ).decode("ascii").strip()

    for path, signed_status in _MANDATORY_SIGNED_STATUS_BY_PATH.items():
        live_path = repository / path
        text = live_path.read_text(encoding="utf-8")
        draft_status = _MANDATORY_DRAFT_STATUS_BY_PATH[path]
        lines = text.splitlines()
        assert lines.count(draft_status) == 1
        lines[lines.index(draft_status)] = signed_status
        live_path.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
    receipt_payloads = {
        "data/results/v3m0_parent_v3_review_authority.json": {
            "review_role": "authority",
            "candidate_sha": candidate_sha,
        },
        "data/results/v3m0_parent_v3_review_mathematics.json": {
            "review_role": "mathematics",
            "candidate_sha": candidate_sha,
        },
    }
    for path, payload in receipt_payloads.items():
        _write_fixture_path(repository, path, _canonical_json_line(payload))
    signed_source_pairs = tuple(
        (path, raw_sha)
        for path, _mode, raw_sha in parent_candidate.source_closure
    )
    signing_literals = (
        "from __future__ import annotations\n\n"
        f"PARENT_V3_PREPARATION_COMMIT_SHA: str | None = {preparation_commit_sha!r}\n"
        f"PARENT_V3_REVIEWED_CANDIDATE_SHA256: str | None = {candidate_sha!r}\n"
        "PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256: str | None = "
        f"{source_closure_sha!r}\n"
        "PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH: "
        "tuple[tuple[str, str], ...] = "
        f"{signed_source_pairs!r}\n"
        "PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE: "
        "tuple[tuple[str, str], ...] = ()\n"
    )
    _write_fixture_path(
        repository,
        "rulespace_v3/parent_signing_literals_v1.py",
        signing_literals.encode("utf-8"),
    )
    _git(repository, "add", "--", ".")
    _git(repository, "commit", "-qm", "allowlisted signed successor S")
    successor_commit_sha = _git(repository, "rev-parse", "HEAD").decode().strip()
    assert successor_commit_sha != preparation_commit_sha

    verified = candidate_module.verify_parent_freeze_candidate_v3(parent_candidate)
    assert verified is parent_candidate
    assert verified.preparation_commit_sha == preparation_commit_sha
    assert verified.candidate_sha == candidate_sha
    assert verified.source_closure_sha == source_closure_sha


def test_slice3b15_preparation_authority_gate_reads_immutable_head_blobs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository, commit_sha, _included = _new_source_fixture_repository(tmp_path)
    path = next(iter(_MANDATORY_DRAFT_STATUS_BY_PATH))
    _write_fixture_path(
        repository,
        path,
        (_MANDATORY_SIGNED_STATUS_BY_PATH[path] + "\nlive drift\n").encode(
            "utf-8"
        ),
    )
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    candidate._validate_preparation_authority_blobs(commit_sha)


def test_slice3b3_draft_to_signed_live_mutation_preserves_p_source_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository, commit_sha, _included = _new_source_fixture_repository(tmp_path)
    monkeypatch.setattr(parent_v3_contracts, "_REPOSITORY_ROOT", repository)
    initial_closure = candidate._select_parent_v3_source_closure_at_preparation_commit(
        commit_sha
    )
    initial_root = canonical_sha(
        candidate.parent_v3_source_closure_v1_payload(commit_sha, initial_closure)
    )
    for path, signed_status in _MANDATORY_SIGNED_STATUS_BY_PATH.items():
        _write_fixture_path(
            repository,
            path,
            (signed_status + "\n\nlive signing mutation\n").encode("utf-8"),
        )
    assert _git(repository, "status", "--porcelain") != b""
    replayed_closure = candidate._select_parent_v3_source_closure_at_preparation_commit(
        commit_sha
    )
    replayed_root = canonical_sha(
        candidate.parent_v3_source_closure_v1_payload(commit_sha, replayed_closure)
    )
    assert replayed_closure == initial_closure
    assert replayed_root == initial_root


@pytest.mark.parametrize(
    ("doc_index", "attack"),
    (
        (0, "signed"),
        (1, "signed"),
        (2, "signed"),
        (3, "signed"),
        (0, "hybrid"),
        (0, "missing"),
        (1, "malformed"),
    ),
)
def test_slice3b15_snapshot_rejects_partial_signed_missing_or_malformed_docs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    doc_index: int,
    attack: str,
) -> None:
    candidate = _candidate_module()
    repository, _commit_sha, _included = _new_source_fixture_repository(tmp_path)
    path = tuple(_MANDATORY_DRAFT_STATUS_BY_PATH)[doc_index]
    if attack == "missing":
        _git(repository, "rm", "-q", "--", path)
    elif attack == "signed":
        _write_fixture_path(
            repository,
            path,
            (_MANDATORY_SIGNED_STATUS_BY_PATH[path] + "\nfixture body\n").encode(
                "utf-8"
            ),
        )
        _git(repository, "add", "--", path)
    elif attack == "hybrid":
        _write_fixture_path(
            repository,
            path,
            (
                _MANDATORY_DRAFT_STATUS_BY_PATH[path]
                + "\n"
                + _MANDATORY_SIGNED_STATUS_BY_PATH[path]
                + "\nfixture body\n"
            ).encode("utf-8"),
        )
        _git(repository, "add", "--", path)
    else:
        draft = _MANDATORY_DRAFT_STATUS_BY_PATH[path]
        _write_fixture_path(
            repository,
            path,
            (draft + "\n" + draft + "\nfixture body\n").encode("utf-8"),
        )
        _git(repository, "add", "--", path)
    _git(repository, "commit", "-qm", f"authority doc {attack}")
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    with pytest.raises(ValueError):
        candidate._snapshot_clean_preparation_head()


def test_slice3b15_snapshot_accepts_optional_absent_or_exact_placeholder_literals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    repository, initial_commit, _included = _new_source_fixture_repository(tmp_path)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    assert candidate._snapshot_clean_preparation_head() == initial_commit
    literal_path = "rulespace_v3/parent_signing_literals_v1.py"
    _write_fixture_path(repository, literal_path, _PARENT_SIGNING_PLACEHOLDER_SOURCE)
    _git(repository, "add", "--", literal_path)
    _git(repository, "commit", "-qm", "placeholder signing literals")
    placeholder_commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    assert candidate._snapshot_clean_preparation_head() == placeholder_commit


@pytest.mark.parametrize(
    "literal_attack",
    ("injected", "missing", "reordered", "extra", "annotation"),
)
def test_slice3b15_snapshot_rejects_nonplaceholder_signing_literals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    literal_attack: str,
) -> None:
    candidate = _candidate_module()
    repository, _commit_sha, _included = _new_source_fixture_repository(tmp_path)
    source = _PARENT_SIGNING_PLACEHOLDER_SOURCE.decode("utf-8")
    lines = source.splitlines()
    authority_lines = [line for line in lines if line.startswith("PARENT_V3_")]
    if literal_attack == "injected":
        source = source.replace(" = None", f' = "{"1" * 40}"', 1)
    elif literal_attack == "missing":
        source = source.replace(authority_lines[1] + "\n", "")
    elif literal_attack == "reordered":
        first_index = lines.index(authority_lines[0])
        second_index = lines.index(authority_lines[1])
        lines[first_index], lines[second_index] = lines[second_index], lines[first_index]
        source = "\n".join(lines) + "\n"
    elif literal_attack == "extra":
        source += "PARENT_V3_ATTACKER_LITERAL: str | None = None\n"
    else:
        source = source.replace(
            "PARENT_V3_PREPARATION_COMMIT_SHA: str | None",
            "PARENT_V3_PREPARATION_COMMIT_SHA: str",
        )
    literal_path = "rulespace_v3/parent_signing_literals_v1.py"
    _write_fixture_path(repository, literal_path, source.encode("utf-8"))
    _git(repository, "add", "--", literal_path)
    _git(repository, "commit", "-qm", f"bad signing literal {literal_attack}")
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", repository)
    with pytest.raises(ValueError):
        candidate._snapshot_clean_preparation_head()


def test_slice3b15_validator_rejects_symlinked_parent_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate_module()
    expectation = _slice3b1_expectation(candidate, tmp_path)
    lexical_parent = tmp_path / "rulespace_v3"
    real_parent = tmp_path / "real_rulespace_v3"
    lexical_parent.rename(real_parent)
    lexical_parent.symlink_to(real_parent, target_is_directory=True)
    nonce = "4" * 64
    payload = _slice3b1_payload(candidate, expectation, nonce)
    monkeypatch.setattr(candidate, "_REPOSITORY_ROOT", tmp_path)
    with pytest.raises(ValueError, match="symlink"):
        candidate._validate_fresh_interpreter_audit_output(
            expectation,
            nonce,
            subprocess.CompletedProcess(
                args=("python",),
                returncode=0,
                stdout=_canonical_json_line(payload),
                stderr=b"",
            ),
        )


@pytest.fixture(scope="module")
def preparation_commit_sha() -> str:
    commit_sha = subprocess.run(
        ("git", "rev-list", "--no-merges", "-n", "1", "HEAD"),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    assert len(commit_sha) == 40
    assert subprocess.run(
        ("git", "cat-file", "-t", commit_sha),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout == "commit\n"
    raw_commit = subprocess.run(
        ("git", "cat-file", "commit", commit_sha),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    header, separator, _body = raw_commit.partition(b"\n\n")
    assert separator == b"\n\n"
    parent_headers = tuple(
        line for line in header.splitlines() if line.startswith(b"parent ")
    )
    assert len(parent_headers) <= 1, "slice-2 fixture P must be non-merge"
    core_replay_paths = (
        *_CONSTRUCTION_DEPENDENCY_PATHS,
        "rulespace_v3/parent_candidate_v2.py",
        "rulespace_v3/parent_freeze.py",
        "rulespace_v3/parent_freeze_v2.py",
    )
    assert len(core_replay_paths) == len(set(core_replay_paths))
    for relative_path in core_replay_paths:
        assert subprocess.run(
            ("git", "cat-file", "-e", f"{commit_sha}:{relative_path}"),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).returncode == 0, f"P lacks core replay dependency {relative_path}"
    return commit_sha


@pytest.fixture(scope="module")
def replayed_candidate(preparation_commit_sha: str):
    candidate_module = _candidate_module()
    replay_name = (
        "_replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit"
    )
    assert hasattr(candidate_module, replay_name), "missing private P-epoch replay"
    assert replay_name not in candidate_module.__all__
    return getattr(candidate_module, replay_name)(preparation_commit_sha)


def test_private_p_replay_splits_c19_and_preserves_parent_v1_ordinals(
    preparation_commit_sha: str,
    replayed_candidate,
) -> None:
    candidate_module = _candidate_module()
    raw_v2 = verify_reviewed_current_application_authorities_v2_raw(
        build_reviewed_current_application_authorities_v2_raw()
    )
    raw_control_ids = tuple(item.control_case_id for item in raw_v2)
    assert len(raw_control_ids) == 20
    c19_ordinal = raw_control_ids.index(candidate_module.C19_CONTROL_CASE_ID)
    assert c19_ordinal == 18
    assert raw_control_ids[-1] == "C20_DM26_CLEAN_ZERO_TRUE_FLOOR"

    old_c19 = raw_v2[c19_ordinal]
    new_c19 = _replay_c19_current_application_authority_v3_at_preparation_commit(
        preparation_commit_sha
    )
    assert replayed_candidate.inherited_current_application_authorities_v2 == (
        raw_v2[:c19_ordinal] + raw_v2[c19_ordinal + 1 :]
    )
    assert replayed_candidate.superseded_application_authorities_v2 == (old_c19,)
    assert replayed_candidate.refrozen_current_application_authorities_v3 == (
        new_c19,
    )
    assert new_c19.authority_state == PROVISIONAL_AUTHORITY_STATE

    registry = candidate_module.current_application_registry_v3_payload(
        replayed_candidate
    )
    assert registry["current_application_registry_schema_version"] == (
        candidate_module.CURRENT_APPLICATION_REGISTRY_V3_SCHEMA_VERSION
    )
    entries = registry["entries"]
    assert tuple(item["parent_v1_ordinal"] for item in entries) == tuple(range(20))
    assert tuple(item["authority_tag"] for item in entries) == (
        *("INHERITED_CURRENT_V2" for _ in range(18)),
        "REFROZEN_CURRENT_V3",
        "INHERITED_CURRENT_V2",
    )
    assert tuple(
        item["application_authority"]["control_case_id"] for item in entries
    ) == raw_control_ids
    assert entries[c19_ordinal]["application_authority"][
        "application_instance_id"
    ] == candidate_module.C19_REPLACEMENT_APPLICATION_INSTANCE_ID
    assert entries[-1]["application_authority"]["scenario_authorities"] == []


def test_private_p_replay_has_one_exact_supersession_and_replaces_only_c19_success(
    replayed_candidate,
) -> None:
    candidate_module = _candidate_module()
    raw_v2 = build_reviewed_current_application_authorities_v2_raw()
    old_c19 = next(
        item
        for item in raw_v2
        if item.control_case_id == candidate_module.C19_CONTROL_CASE_ID
    )
    new_c19 = replayed_candidate.refrozen_current_application_authorities_v3[0]

    assert len(replayed_candidate.application_supersessions) == 1
    supersession = replayed_candidate.application_supersessions[0]
    assert supersession.control_case_id == candidate_module.C19_CONTROL_CASE_ID
    assert supersession.superseded_application_instance_id == (
        old_c19.application_instance_id
    )
    assert supersession.superseded_application_authority_v2_sha == (
        old_c19.application_authority_sha
    )
    assert supersession.replacement_application_instance_id == (
        new_c19.application_instance_id
    )
    assert supersession.replacement_application_authority_v3_sha == (
        new_c19.application_authority_sha
    )
    assert supersession.reason_id == candidate_module.C19_SUPERSESSION_REASON_ID
    assert supersession.supersession_sha == canonical_sha(
        candidate_module.application_supersession_v3_payload(supersession)
    )

    old_success_ids = tuple(
        scenario.scenario_id
        for application in raw_v2
        for scenario in application.scenario_authorities
    )
    old_c19_success_ids = tuple(
        item.scenario_id for item in old_c19.scenario_authorities
    )
    new_c19_success_ids = tuple(
        item.scenario_id for item in new_c19.scenario_authorities
    )
    assert len(old_success_ids) == 23
    assert len(old_c19_success_ids) == len(new_c19_success_ids) == 1
    old_c19_success_ordinal = old_success_ids.index(old_c19_success_ids[0])
    expected = (
        old_success_ids[:old_c19_success_ordinal]
        + new_c19_success_ids
        + old_success_ids[old_c19_success_ordinal + 1 :]
    )
    assert replayed_candidate.block_success_scenario_ids == expected
    assert len(expected) == len(set(expected)) == 23
    assert old_c19_success_ids[0] not in expected
    assert new_c19_success_ids[0] in expected
    assert not any("c20" in item.lower() for item in expected)


def test_private_p_replay_recomputes_source_and_candidate_roots(
    preparation_commit_sha: str,
    replayed_candidate,
) -> None:
    candidate_module = _candidate_module()
    assert replayed_candidate.preparation_commit_sha == preparation_commit_sha
    assert replayed_candidate.source_closure_sha == canonical_sha(
        candidate_module.parent_v3_source_closure_v1_payload(
            preparation_commit_sha,
            replayed_candidate.source_closure,
        )
    )
    assert replayed_candidate.candidate_sha == canonical_sha(
        candidate_module.parent_freeze_candidate_v3_manifest_payload(
            replayed_candidate
        )
    )


def test_registry_owner_rejects_duplicate_control_ids_before_building_maps(
    replayed_candidate,
) -> None:
    candidate_module = _candidate_module()
    forged = copy.deepcopy(replayed_candidate)
    inherited = forged.inherited_current_application_authorities_v2
    object.__setattr__(
        forged,
        "inherited_current_application_authorities_v2",
        (*inherited, inherited[0]),
    )
    with pytest.raises(ValueError, match="duplicate"):
        candidate_module.current_application_registry_v3_payload(forged)


def test_public_verifier_rejects_resigned_registry_attacks(
    replayed_candidate,
) -> None:
    candidate_module = _candidate_module()
    old_c19 = replayed_candidate.superseded_application_authorities_v2[0]

    def resigned(**changes):
        provisional = replace(
            replayed_candidate,
            candidate_sha="0" * 64,
            **changes,
        )
        return replace(
            provisional,
            candidate_sha=canonical_sha(
                candidate_module.parent_freeze_candidate_v3_manifest_payload(
                    provisional
                )
            ),
        )

    old_and_new_current = resigned(
        inherited_current_application_authorities_v2=(
            *replayed_candidate.inherited_current_application_authorities_v2[:18],
            old_c19,
            *replayed_candidate.inherited_current_application_authorities_v2[18:],
        )
    )
    inherited = replayed_candidate.inherited_current_application_authorities_v2
    wrong_order = resigned(
        inherited_current_application_authorities_v2=(
            inherited[1],
            inherited[0],
            *inherited[2:],
        )
    )
    c20_as_success = resigned(
        block_success_scenario_ids=(
            *replayed_candidate.block_success_scenario_ids,
            "v3m0.synthetic-control.c20.analysis-only.forbidden-block-success",
        )
    )
    resigned_root = replace(replayed_candidate, candidate_sha="f" * 64)

    for forged in (
        old_and_new_current,
        wrong_order,
        c20_as_success,
        resigned_root,
    ):
        with pytest.raises((TypeError, ValueError)):
            candidate_module.verify_parent_freeze_candidate_v3(forged)


def test_public_verifier_recursively_rejects_unknown_attrs_and_tuple_subclasses(
    replayed_candidate,
) -> None:
    candidate_module = _candidate_module()
    inherited = replayed_candidate.inherited_current_application_authorities_v2

    unknown_nested = copy.deepcopy(replayed_candidate)
    object.__setattr__(
        unknown_nested.inherited_current_application_authorities_v2[0],
        "unhashed_override",
        True,
    )

    class HostileTuple(tuple):
        pass

    hostile_container = copy.deepcopy(replayed_candidate)
    nested_application = hostile_container.inherited_current_application_authorities_v2[0]
    object.__setattr__(
        nested_application,
        "complete_scenario_execution_specs",
        HostileTuple(nested_application.complete_scenario_execution_specs),
    )

    class HostileCandidate(candidate_module.ParentFreezeCandidateV3Manifest):
        pass

    hostile_candidate = HostileCandidate(**vars(replayed_candidate))
    for forged, expected_error in (
        (vars(replayed_candidate), TypeError),
        (hostile_candidate, TypeError),
        (unknown_nested, ValueError),
        (hostile_container, TypeError),
    ):
        with pytest.raises(expected_error):
            candidate_module.verify_parent_freeze_candidate_v3(forged)

    # Keep a live reference so hostile edits cannot be hidden by a detached rebuild.
    assert inherited[0].control_case_id == (
        replayed_candidate.inherited_current_application_authorities_v2[0].control_case_id
    )
