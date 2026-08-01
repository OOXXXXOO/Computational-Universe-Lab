"""Opaque live-identity facade for the repository-closed Parent-v3 epoch."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path, PurePosixPath
import stat
import threading
import weakref

from .evidence import canonical_sha as _canonical_sha
from .parent_candidate_v3 import _stable_regular_file_sha256
from .parent_freeze_v3 import (
    _ParentFreezeV3IssuanceMaterial,
    _build_repository_closed_parent_freeze_v3,
    _validate_parent_freeze_v3_issuance_material,
)
from .parent_freeze_v3_contracts import (
    ParentFreezeV3Manifest,
    parent_freeze_v3_manifest_payload as _parent_freeze_v3_manifest_payload,
    verify_parent_freeze_v3_manifest as _verify_parent_freeze_v3_manifest,
    verify_parent_v3_reviewer_key_registry as _verify_parent_v3_reviewer_key_registry,
)
from .parent_reviewer_keys_v1 import PARENT_V3_TRUSTED_REVIEWER_KEYS_V1
from .parent_signing_audit_v1 import (
    _git_command,
    _read_tree_blob,
    _snapshot_clean_head,
)
from .parent_signing_literals_v1 import (
    PARENT_V3_PREPARATION_COMMIT_SHA,
    PARENT_V3_REVIEWED_CANDIDATE_SHA256,
    PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256,
    PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE,
    PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH,
)


_ISSUANCE_TOKEN = object()
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FINAL_DOWNSTREAM_MODULE_PATHS = (
    "rulespace_v3/application_authority_v3.py",
    "rulespace_v3/application_materialization_v3.py",
    "rulespace_v3/transition_authority_v3.py",
    "rulespace_v3/metric_support_authority_v1.py",
    "rulespace_v3/runtime_grids_v3.py",
    "rulespace_v3/certificate_v3.py",
    "rulespace_v3/application_response_v3.py",
    "rulespace_v3/control_application_evidence_v3.py",
    "rulespace_v3/runtime_v3.py",
    "rulespace_v3/campaign_stage_authority_v1.py",
    "rulespace_v3/checkpoint_envelope_v1.py",
)


class ParentV3IssuanceBlocked(RuntimeError):
    """Typed engineering blocker; never a scientific PASS or HALT state."""

    def __init__(self, reason_id: str, detail: str) -> None:
        if type(reason_id) is not str or not reason_id:
            raise TypeError("Parent-v3 issuance blocker reason must be non-empty")
        if type(detail) is not str or not detail:
            raise TypeError("Parent-v3 issuance blocker detail must be non-empty")
        self.reason_id = reason_id
        self.detail = detail
        super().__init__(f"{reason_id}: {detail}")


def _parent_v3_readiness_reason() -> tuple[str, str] | None:
    try:
        registry = _verify_parent_v3_reviewer_key_registry(
            PARENT_V3_TRUSTED_REVIEWER_KEYS_V1
        )
    except (TypeError, ValueError) as exc:
        return "PARENT_V3_REVIEWER_REGISTRY_NOT_FROZEN", str(exc)
    if not registry:
        return (
            "PARENT_V3_REVIEWER_REGISTRY_NOT_FROZEN",
            "the P-epoch dual-role reviewer registry is still empty",
        )
    scalar_literals = (
        PARENT_V3_PREPARATION_COMMIT_SHA,
        PARENT_V3_REVIEWED_CANDIDATE_SHA256,
        PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256,
    )
    if any(type(value) is not str for value in scalar_literals) or not (
        PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH
        and PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE
    ):
        return (
            "PARENT_V3_SIGNING_LITERALS_NOT_INJECTED",
            "the five S-epoch signing literals remain in their P placeholders",
        )
    missing = tuple(
        path
        for path in _FINAL_DOWNSTREAM_MODULE_PATHS
        if not (_REPOSITORY_ROOT / path).is_file()
    )
    if missing:
        return (
            "PARENT_V3_DOWNSTREAM_CLOSURE_INCOMPLETE",
            "downstream production modules are absent: " + ", ".join(missing),
        )
    return None


def _current_head_without_clean_gate() -> str:
    completed = _git_command(_REPOSITORY_ROOT, "rev-parse", "--verify", "HEAD")
    if completed.returncode != 0 or completed.stderr != b"":
        raise ValueError("Parent-v3 live HEAD cannot be resolved")
    try:
        head = completed.stdout.removesuffix(b"\n").decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("Parent-v3 live HEAD is not ASCII") from exc
    if (
        completed.stdout != head.encode("ascii") + b"\n"
        or len(head) != 40
        or any(character not in "0123456789abcdef" for character in head)
    ):
        raise ValueError("Parent-v3 live HEAD is not one canonical Git SHA-1")
    return head


def _verify_live_protected_signing_tree(
    material: _ParentFreezeV3IssuanceMaterial,
) -> None:
    verified = _validate_parent_freeze_v3_issuance_material(material)
    signing_commit_sha = verified.manifest.signing_commit_sha
    if _current_head_without_clean_gate() != signing_commit_sha:
        raise ValueError("Parent-v3 live HEAD moved away from audited S")
    root = _REPOSITORY_ROOT.resolve(strict=True)
    for relative_path, expected_sha in verified.protected_signing_tree:
        parts = PurePosixPath(relative_path).parts
        if not parts or any(item in ("", ".", "..") for item in parts):
            raise ValueError("Parent-v3 protected path is not canonical")
        live_path = root.joinpath(*parts)
        try:
            lexical_metadata = live_path.lstat()
        except OSError as exc:
            raise ValueError("Parent-v3 protected live path is missing") from exc
        if not stat.S_ISREG(lexical_metadata.st_mode):
            raise ValueError("Parent-v3 protected live path is not regular")
        opened_metadata, live_sha = _stable_regular_file_sha256(
            live_path, lexical_metadata
        )
        signed_blob = _read_tree_blob(
            _REPOSITORY_ROOT,
            signing_commit_sha,
            relative_path,
        )
        if signed_blob is None:
            raise ValueError("Parent-v3 protected path is absent from S")
        signed_sha = hashlib.sha256(signed_blob.raw).hexdigest()
        live_mode = "100755" if opened_metadata.st_mode & 0o111 else "100644"
        if (
            live_sha != expected_sha
            or signed_sha != expected_sha
            or live_mode != signed_blob.mode
        ):
            raise ValueError("Parent-v3 protected path drifted from audited S")
    if _current_head_without_clean_gate() != signing_commit_sha:
        raise ValueError("Parent-v3 live HEAD changed during protected-path replay")


def _parent_v3_seal(material: _ParentFreezeV3IssuanceMaterial) -> str:
    verified = _validate_parent_freeze_v3_issuance_material(material)
    return _canonical_sha(
        {
            "authority_kind": "v3m0-current-parent-live-identity-v3",
            "manifest": {
                **_parent_freeze_v3_manifest_payload(verified.manifest),
                "parent_freeze_v3_sha": verified.manifest.parent_freeze_v3_sha,
            },
            "protected_signing_tree": [
                list(item) for item in verified.protected_signing_tree
            ],
        }
    )


class VerifiedParentFreezeV3:
    __slots__ = (
        "__manifest",
        "__protected_signing_tree",
        "__token",
        "__seal",
        "__weakref__",
    )

    def __init__(
        self,
        token: object,
        manifest: ParentFreezeV3Manifest,
        protected_signing_tree: tuple[tuple[str, str], ...],
        seal: str,
        *,
        _token: object = _ISSUANCE_TOKEN,
        _setattr=object.__setattr__,
    ) -> None:
        if token is not _token:
            raise TypeError("VerifiedParentFreezeV3 can only be issued internally")
        material = _validate_parent_freeze_v3_issuance_material(
            _ParentFreezeV3IssuanceMaterial(manifest, protected_signing_tree)
        )
        _setattr(self, "_VerifiedParentFreezeV3__manifest", material.manifest)
        _setattr(
            self,
            "_VerifiedParentFreezeV3__protected_signing_tree",
            material.protected_signing_tree,
        )
        _setattr(self, "_VerifiedParentFreezeV3__token", token)
        _setattr(self, "_VerifiedParentFreezeV3__seal", seal)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedParentFreezeV3 is immutable")

    @property
    def manifest(self) -> ParentFreezeV3Manifest:
        return require_current_parent_v3(self)


_registry: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedParentFreezeV3],
        _ParentFreezeV3IssuanceMaterial,
        str,
    ],
] = {}
_registry_lock = threading.RLock()


def _issue_parent_v3(
    material: _ParentFreezeV3IssuanceMaterial,
) -> VerifiedParentFreezeV3:
    snapshot = _validate_parent_freeze_v3_issuance_material(material)
    _verify_live_protected_signing_tree(snapshot)
    seal = _parent_v3_seal(snapshot)
    wrapper = VerifiedParentFreezeV3(
        _ISSUANCE_TOKEN,
        snapshot.manifest,
        snapshot.protected_signing_tree,
        seal,
    )
    identity = id(wrapper)

    def remove_stale(
        reference: weakref.ReferenceType[VerifiedParentFreezeV3],
        wrapper_id: int = identity,
    ) -> None:
        with _registry_lock:
            current = _registry.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _registry[wrapper_id]

    reference = weakref.ref(wrapper, remove_stale)
    registry_entry = (reference, copy.deepcopy(snapshot), seal)
    with _registry_lock:
        current = _registry.get(identity)
        if current is not None and current[0]() is not None:
            raise RuntimeError("live VerifiedParentFreezeV3 identity collision")
        if (
            _snapshot_clean_head(_REPOSITORY_ROOT)
            != snapshot.manifest.signing_commit_sha
        ):
            raise ValueError(
                "Parent-v3 final clean HEAD differs from audited signing commit"
            )
        _registry[identity] = registry_entry
    return wrapper


def _reverify_parent_v3(
    wrapper: VerifiedParentFreezeV3,
) -> _ParentFreezeV3IssuanceMaterial:
    if type(wrapper) is not VerifiedParentFreezeV3:
        raise TypeError("Parent-v3 consumer requires the exact live wrapper")
    with _registry_lock:
        current = _registry.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError(
                "VerifiedParentFreezeV3 identity is absent from the registry"
            )
        expected = copy.deepcopy(current[1])
        expected_seal = current[2]
    try:
        token = object.__getattribute__(wrapper, "_VerifiedParentFreezeV3__token")
        manifest = object.__getattribute__(wrapper, "_VerifiedParentFreezeV3__manifest")
        protected_tree = object.__getattribute__(
            wrapper, "_VerifiedParentFreezeV3__protected_signing_tree"
        )
        seal = object.__getattribute__(wrapper, "_VerifiedParentFreezeV3__seal")
    except AttributeError as exc:
        raise ValueError("VerifiedParentFreezeV3 record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("VerifiedParentFreezeV3 token drifted")
    observed = _validate_parent_freeze_v3_issuance_material(
        _ParentFreezeV3IssuanceMaterial(manifest, protected_tree)
    )
    if seal != expected_seal or seal != _parent_v3_seal(observed):
        raise ValueError("VerifiedParentFreezeV3 seal drifted")
    if observed != expected:
        raise ValueError("VerifiedParentFreezeV3 body drifted")
    _verify_live_protected_signing_tree(observed)
    return copy.deepcopy(expected)


def issue_v3m0_parent_freeze_v3() -> VerifiedParentFreezeV3:
    """Issue only the sole clean, fully audited repository Parent-v3."""

    blocker = _parent_v3_readiness_reason()
    if blocker is not None:
        raise ParentV3IssuanceBlocked(*blocker)
    try:
        material = _build_repository_closed_parent_freeze_v3()
        return _issue_parent_v3(material)
    except ParentV3IssuanceBlocked:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ParentV3IssuanceBlocked(
            "PARENT_V3_SIGNING_AUDIT_BLOCKED",
            str(exc),
        ) from exc


def require_current_parent_v3(
    parent: VerifiedParentFreezeV3,
) -> ParentFreezeV3Manifest:
    """Consume only a live module-issued Parent-v3 capability."""

    if type(parent) is not VerifiedParentFreezeV3:
        raise TypeError("Parent-v3 consumer rejects raw, old, and subclass values")
    material = _reverify_parent_v3(parent)
    return copy.deepcopy(_verify_parent_freeze_v3_manifest(material.manifest))


__all__ = (
    "ParentV3IssuanceBlocked",
    "VerifiedParentFreezeV3",
    "issue_v3m0_parent_freeze_v3",
    "require_current_parent_v3",
)
