from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
import hashlib
import inspect
import os
from pathlib import Path
import subprocess

import pytest

from rulespace_v3.parent_authority_v3 import (
    ParentV3IssuanceBlocked,
    VerifiedParentFreezeV3,
    issue_v3m0_parent_freeze_v3,
    require_current_parent_v3,
)
from rulespace_v3.parent_authority import VerifiedParentFreezeV2
from rulespace_v3.parent_freeze import VerifiedParentFreeze


@dataclass
class _FixtureManifest:
    signing_commit_sha: str
    parent_freeze_v3_sha: str
    body: str


def _git(repository: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        env={
            "GIT_CONFIG_NOSYSTEM": "1",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": os.defpath,
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", "-A")
    _git(
        repository,
        "-c",
        "user.name=A5 Test",
        "-c",
        "user.email=a5@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD").decode("ascii").strip()


@pytest.fixture
def private_live_parent_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import rulespace_v3.parent_authority_v3 as facade
    from rulespace_v3.parent_freeze_v3 import _ParentFreezeV3IssuanceMaterial

    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    protected_relative_path = "rulespace_v3/protected.py"
    protected_path = repository / protected_relative_path
    protected_path.parent.mkdir(parents=True)
    protected_bytes = b"SIGNED_PARENT = True\n"
    protected_path.write_bytes(protected_bytes)
    signing_commit_sha = _commit(repository, "signed Parent S")
    manifest = _FixtureManifest(
        signing_commit_sha=signing_commit_sha,
        parent_freeze_v3_sha="a" * 64,
        body="signed-body",
    )
    material = _ParentFreezeV3IssuanceMaterial(
        manifest=manifest,
        protected_signing_tree=(
            (protected_relative_path, hashlib.sha256(protected_bytes).hexdigest()),
        ),
    )

    def verify_manifest(value):
        if type(value) is not _FixtureManifest:
            raise TypeError("fixture manifest is not exact")
        if value.signing_commit_sha != signing_commit_sha:
            raise ValueError("fixture signing commit drifted")
        return value

    def validate_material(value):
        if type(value) is not _ParentFreezeV3IssuanceMaterial:
            raise TypeError("fixture issuance material is not exact")
        verify_manifest(value.manifest)
        if value.protected_signing_tree != material.protected_signing_tree:
            raise ValueError("fixture protected signing tree drifted")
        return copy.deepcopy(value)

    monkeypatch.setattr(facade, "_REPOSITORY_ROOT", repository)
    monkeypatch.setattr(
        facade,
        "_validate_parent_freeze_v3_issuance_material",
        validate_material,
    )
    monkeypatch.setattr(facade, "_verify_parent_freeze_v3_manifest", verify_manifest)
    monkeypatch.setattr(
        facade,
        "_parent_freeze_v3_manifest_payload",
        lambda value: {
            "body": value.body,
            "signing_commit_sha": value.signing_commit_sha,
        },
    )
    monkeypatch.setattr(facade, "_registry", {})
    yield facade, repository, material, protected_path
    facade._registry.clear()


def test_slice_a5_zero_argument_issuer_is_typed_blocked_before_real_p_s() -> None:
    assert tuple(inspect.signature(issue_v3m0_parent_freeze_v3).parameters) == ()
    with pytest.raises(ParentV3IssuanceBlocked) as caught:
        issue_v3m0_parent_freeze_v3()
    assert caught.value.reason_id in {
        "PARENT_V3_REVIEWER_REGISTRY_NOT_FROZEN",
        "PARENT_V3_SIGNING_LITERALS_NOT_INJECTED",
        "PARENT_V3_SIGNING_AUDIT_BLOCKED",
        "PARENT_V3_DOWNSTREAM_CLOSURE_INCOMPLETE",
    }


def test_slice_a5_facade_exports_only_one_issuer_and_one_consumer() -> None:
    import rulespace_v3.parent_authority_v3 as facade

    assert tuple(facade.__all__) == (
        "ParentV3IssuanceBlocked",
        "VerifiedParentFreezeV3",
        "issue_v3m0_parent_freeze_v3",
        "require_current_parent_v3",
    )
    public_functions = {
        name
        for name, value in vars(facade).items()
        if inspect.isfunction(value) and not name.startswith("_")
    }
    assert public_functions == {
        "issue_v3m0_parent_freeze_v3",
        "require_current_parent_v3",
    }
    assert not any(
        token in name.lower()
        for name in vars(facade)
        for token in ("hydrate", "promote", "resign", "adapter")
    )


def test_slice_a5_constructor_raw_old_parent_and_subclass_attacks_fail() -> None:
    with pytest.raises(TypeError):
        VerifiedParentFreezeV3(object(), object(), (), "0" * 64)
    for hostile in (
        {},
        object.__new__(VerifiedParentFreeze),
        object.__new__(VerifiedParentFreezeV2),
        object.__new__(VerifiedParentFreezeV3),
    ):
        with pytest.raises((TypeError, ValueError)):
            require_current_parent_v3(hostile)

    class HostileParent(VerifiedParentFreezeV3):
        pass

    with pytest.raises((TypeError, ValueError)):
        require_current_parent_v3(object.__new__(HostileParent))


def test_slice_a5_wrapper_source_has_no_copy_or_pickle_escape() -> None:
    forged = object.__new__(VerifiedParentFreezeV3)
    for copier in (copy.copy, copy.deepcopy):
        try:
            clone = copier(forged)
        except Exception:
            continue
        with pytest.raises((TypeError, ValueError)):
            require_current_parent_v3(clone)


def test_slice_a5_raw_manifest_builder_is_private_and_has_no_caller_roots() -> None:
    module_path = Path(__file__).parents[1] / "rulespace_v3/parent_freeze_v3.py"
    module = ast.parse(module_path.read_text(encoding="utf-8"))
    public_functions = {
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert public_functions == set()
    forbidden_parameters = {
        "candidate",
        "manifest",
        "preparation_commit_sha",
        "signing_commit_sha",
        "parent_freeze_v3_sha",
        "review_receipts",
        "signed_source_refs",
    }
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert not forbidden_parameters.intersection(
                argument.arg for argument in node.args.args
            )


def test_slice_a5_private_material_issues_one_detached_live_wrapper_and_allows_runtime_output(
    private_live_parent_fixture,
) -> None:
    facade, repository, material, _protected_path = private_live_parent_fixture

    wrapper = facade._issue_parent_v3(material)
    assert type(wrapper) is facade.VerifiedParentFreezeV3
    assert facade._registry[id(wrapper)][0]() is wrapper
    assert facade.require_current_parent_v3(wrapper).body == "signed-body"

    # Caller-owned material and consumer-returned bodies are both detached.
    material.manifest.body = "caller mutation"
    detached = facade.require_current_parent_v3(wrapper)
    detached.body = "consumer mutation"
    assert facade.require_current_parent_v3(wrapper).body == "signed-body"

    # Runtime outputs are intentionally outside the protected signing tree.
    runtime_output = repository / "data/runtime/v3m0-runtime-output.json"
    runtime_output.parent.mkdir(parents=True)
    runtime_output.write_bytes(b"{}\n")
    assert facade.require_current_parent_v3(wrapper).body == "signed-body"


@pytest.mark.parametrize("attack", ("registry", "seal", "body", "protected-tree"))
def test_slice_a5_live_wrapper_rejects_registry_seal_and_body_attacks(
    private_live_parent_fixture,
    attack: str,
) -> None:
    facade, _repository, material, _protected_path = private_live_parent_fixture
    wrapper = facade._issue_parent_v3(material)

    if attack == "registry":
        facade._registry.pop(id(wrapper))
    elif attack == "seal":
        object.__setattr__(
            wrapper,
            "_VerifiedParentFreezeV3__seal",
            "f" * 64,
        )
    elif attack == "body":
        internal = object.__getattribute__(
            wrapper,
            "_VerifiedParentFreezeV3__manifest",
        )
        internal.body = "hostile body"
    else:
        object.__setattr__(
            wrapper,
            "_VerifiedParentFreezeV3__protected_signing_tree",
            (("rulespace_v3/protected.py", "f" * 64),),
        )

    with pytest.raises((TypeError, ValueError), match="registry|seal|body|tree|drift"):
        facade.require_current_parent_v3(wrapper)


@pytest.mark.parametrize("attack", ("protected-path", "head"))
def test_slice_a5_require_rejects_live_protected_path_or_head_drift(
    private_live_parent_fixture,
    attack: str,
) -> None:
    facade, repository, material, protected_path = private_live_parent_fixture
    wrapper = facade._issue_parent_v3(material)

    if attack == "protected-path":
        protected_path.write_bytes(b"SIGNED_PARENT = False\n")
    else:
        (repository / "unprotected-committed-output").write_bytes(b"new HEAD\n")
        _commit(repository, "move away from audited S")

    with pytest.raises(ValueError, match="HEAD|protected|drift|changed"):
        facade.require_current_parent_v3(wrapper)


def test_slice_a5_require_rejects_protected_inode_swap_during_open(
    private_live_parent_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade, repository, material, protected_path = private_live_parent_fixture
    wrapper = facade._issue_parent_v3(material)
    replacement = repository / "replacement.py"
    replacement.write_bytes(b"HOSTILE_PARENT = True\n")
    real_stable_hash = facade._stable_regular_file_sha256
    swapped = False

    def swap_before_open(live_path, lexical_metadata):
        nonlocal swapped
        if not swapped and Path(live_path) == protected_path:
            swapped = True
            os.replace(replacement, protected_path)
        return real_stable_hash(live_path, lexical_metadata)

    monkeypatch.setattr(
        facade,
        "_stable_regular_file_sha256",
        swap_before_open,
    )
    with pytest.raises(ValueError, match="changed|inode|protected"):
        facade.require_current_parent_v3(wrapper)
    assert swapped is True


@pytest.mark.parametrize("late_attack", ("dirty", "new-head"))
def test_slice_a5_issuer_takes_final_clean_s_snapshot_after_protected_replay(
    private_live_parent_fixture,
    monkeypatch: pytest.MonkeyPatch,
    late_attack: str,
) -> None:
    facade, repository, material, _protected_path = private_live_parent_fixture
    monkeypatch.setattr(facade, "_parent_v3_readiness_reason", lambda: None)
    monkeypatch.setattr(
        facade,
        "_build_repository_closed_parent_freeze_v3",
        lambda: material,
    )

    def replay_then_drift(_material) -> None:
        if late_attack == "dirty":
            (repository / "late-untracked-output").write_bytes(b"dirty\n")
        else:
            (repository / "late-committed-output").write_bytes(b"new HEAD\n")
            _commit(repository, "late clean HEAD drift")

    monkeypatch.setattr(
        facade,
        "_verify_live_protected_signing_tree",
        replay_then_drift,
    )
    with pytest.raises(ParentV3IssuanceBlocked) as caught:
        facade.issue_v3m0_parent_freeze_v3()
    assert caught.value.reason_id == "PARENT_V3_SIGNING_AUDIT_BLOCKED"
    assert facade._registry == {}


def test_slice_a5_final_a4_snapshot_is_the_last_step_before_registration(
    private_live_parent_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade, _repository, material, _protected_path = private_live_parent_fixture
    from rulespace_v3.parent_signing_audit_v1 import _snapshot_clean_head

    events: list[str] = []
    real_replay = facade._verify_live_protected_signing_tree
    real_deepcopy = facade.copy.deepcopy
    final_snapshot_seen = False

    def replay(value) -> None:
        real_replay(value)
        events.append("protected-replay")

    def final_snapshot(repository_root: Path) -> str:
        nonlocal final_snapshot_seen
        events.append("final-snapshot")
        result = _snapshot_clean_head(repository_root)
        final_snapshot_seen = True
        return result

    def monitored_deepcopy(value):
        if final_snapshot_seen:
            events.append("deepcopy-after-final-snapshot")
        return real_deepcopy(value)

    class RecordingRegistry(dict):
        def __setitem__(self, key, value) -> None:
            events.append("register")
            super().__setitem__(key, value)

    monkeypatch.setattr(facade, "_verify_live_protected_signing_tree", replay)
    monkeypatch.setattr(
        facade,
        "_snapshot_clean_head",
        final_snapshot,
        raising=False,
    )
    monkeypatch.setattr(facade.copy, "deepcopy", monitored_deepcopy)
    monkeypatch.setattr(facade, "_registry", RecordingRegistry())

    wrapper = facade._issue_parent_v3(material)
    assert type(wrapper) is facade.VerifiedParentFreezeV3
    assert "protected-replay" in events
    assert "deepcopy-after-final-snapshot" not in events
    assert events[-2:] == ["final-snapshot", "register"]
