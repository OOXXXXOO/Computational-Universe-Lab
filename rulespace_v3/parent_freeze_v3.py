"""Repository-closed raw Parent-v3 assembly.

No public function in this module accepts a candidate, receipt, commit, or
root.  The sole private builder consumes the private strict-signing audit and
returns detached issuance material for the opaque facade.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from pathlib import PurePosixPath

from .evidence import canonical_sha
from .parent_candidate_v3 import current_application_registry_v3_payload
from .parent_freeze_v3_contracts import (
    PARENT_FREEZE_V3_SCHEMA_VERSION,
    PARENT_V3_AUTHORITY_STATE,
    PARENT_V3_PROGRAM_ID,
    ParentFreezeV3Manifest,
    parent_freeze_v3_manifest_payload,
    verify_parent_freeze_v3_manifest,
)
from .parent_signing_audit_v1 import (
    _audit_current_parent_v3_signing_commits,
    _require_private_parent_signing_audit,
)


@dataclass(frozen=True)
class _ParentFreezeV3IssuanceMaterial:
    manifest: ParentFreezeV3Manifest
    protected_signing_tree: tuple[tuple[str, str], ...]


def _validate_parent_freeze_v3_issuance_material(
    value: object,
) -> _ParentFreezeV3IssuanceMaterial:
    if type(value) is not _ParentFreezeV3IssuanceMaterial:
        raise TypeError("Parent-v3 issuance material is not exact")
    verify_parent_freeze_v3_manifest(value.manifest)
    if (
        type(value.protected_signing_tree) is not tuple
        or not value.protected_signing_tree
    ):
        raise TypeError("Parent-v3 protected signing tree is not an exact tuple")
    paths: list[str] = []
    for index, entry in enumerate(value.protected_signing_tree):
        if (
            type(entry) is not tuple
            or len(entry) != 2
            or type(entry[0]) is not str
            or type(entry[1]) is not str
            or len(entry[1]) != 64
            or any(character not in "0123456789abcdef" for character in entry[1])
        ):
            raise TypeError(
                f"Parent-v3 protected signing tree[{index}] is not a path/SHA pair"
            )
        path = PurePosixPath(entry[0])
        if (
            not entry[0]
            or "\x00" in entry[0]
            or "\\" in entry[0]
            or path.is_absolute()
            or path.as_posix() != entry[0]
            or "." in path.parts
            or ".." in path.parts
        ):
            raise ValueError("Parent-v3 protected signing path is not canonical")
        paths.append(entry[0])
    if tuple(paths) != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
        raise ValueError("Parent-v3 protected signing tree order drifted")
    if len(paths) != len(set(paths)):
        raise ValueError("Parent-v3 protected signing tree contains duplicate paths")
    return copy.deepcopy(value)


def _build_repository_closed_parent_freeze_v3() -> _ParentFreezeV3IssuanceMaterial:
    audit_capability = _audit_current_parent_v3_signing_commits()
    audited = _require_private_parent_signing_audit(audit_capability)
    candidate_body = audited.reviewed_candidate_v3
    signing_audit = audited.signing_audit
    provisional = ParentFreezeV3Manifest(
        parent_freeze_schema_version=PARENT_FREEZE_V3_SCHEMA_VERSION,
        authority_state=PARENT_V3_AUTHORITY_STATE,
        program_id=PARENT_V3_PROGRAM_ID,
        preparation_commit_sha=candidate_body.preparation_commit_sha,
        signing_commit_sha=signing_audit.signing_commit_sha,
        reviewed_candidate_v3=candidate_body,
        signed_source_refs=audited.signed_source_refs,
        review_receipts=audited.review_receipts,
        signing_audit=signing_audit,
        current_application_registry_sha=canonical_sha(
            current_application_registry_v3_payload(candidate_body)
        ),
        parent_freeze_v3_sha="0" * 64,
    )
    manifest = replace(
        provisional,
        parent_freeze_v3_sha=canonical_sha(
            parent_freeze_v3_manifest_payload(provisional)
        ),
    )
    verify_parent_freeze_v3_manifest(manifest)
    material = _ParentFreezeV3IssuanceMaterial(
        manifest=manifest,
        protected_signing_tree=audited.protected_signing_tree,
    )
    return _validate_parent_freeze_v3_issuance_material(material)


__all__: tuple[str, ...] = ()
