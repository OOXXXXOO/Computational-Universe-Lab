"""Upstream matched-ablation snapshot shared by calibration and prestructure."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .ablation import (
    AblationConstructionOutcome,
    AblationManifest,
    _verify_construction_outcome,
    ablation_manifest_payload,
)
from .contracts import BlockStatus
from .evidence import canonical_sha
from .factory import (
    LinearRealspaceFactory,
    VerifiedFactory,
    _reverify_verified_factory,
    factory_payload,
)


PAIR_SNAPSHOT_SCHEMA_VERSION = "v3m0.ablation-pair-snapshot.v1"
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _status_payload(status: BlockStatus) -> dict[str, object]:
    if not isinstance(status, BlockStatus):
        raise TypeError("status must be a BlockStatus")
    return {
        "defined": status.defined,
        "reason": None if status.reason is None else status.reason.value,
    }


def _factory_record(
    factory: LinearRealspaceFactory,
) -> dict[str, object]:
    if not isinstance(factory, LinearRealspaceFactory):
        raise TypeError("factory must be a LinearRealspaceFactory")
    return {
        **factory_payload(factory),
        "factory_sha": factory.factory_sha,
    }


def _manifest_record(manifest: AblationManifest) -> dict[str, object]:
    if not isinstance(manifest, AblationManifest):
        raise TypeError("manifest must be an AblationManifest")
    return {
        **ablation_manifest_payload(manifest),
        "manifest_sha": manifest.manifest_sha,
    }


@dataclass(frozen=True)
class AblationPairSnapshot:
    snapshot_schema_version: str
    construction_status: BlockStatus
    actual_factory: LinearRealspaceFactory
    ablated_factory: LinearRealspaceFactory
    ablation_manifest: AblationManifest
    ablation_construction_sha: str
    snapshot_sha: str

    def __post_init__(self) -> None:
        _text(self.snapshot_schema_version, "snapshot_schema_version")
        if not isinstance(self.construction_status, BlockStatus):
            raise TypeError("construction_status must be a BlockStatus")
        if not isinstance(self.actual_factory, LinearRealspaceFactory):
            raise TypeError("actual_factory has the wrong record type")
        if not isinstance(self.ablated_factory, LinearRealspaceFactory):
            raise TypeError("ablated_factory has the wrong record type")
        if not isinstance(self.ablation_manifest, AblationManifest):
            raise TypeError("ablation_manifest has the wrong record type")
        _sha(self.ablation_construction_sha, "ablation_construction_sha")
        _sha(self.snapshot_sha, "snapshot_sha")


def ablation_construction_payload(
    construction_status: BlockStatus,
    actual_factory: LinearRealspaceFactory,
    ablated_factory: LinearRealspaceFactory,
    ablation_manifest: AblationManifest,
) -> dict[str, object]:
    return {
        "construction_status": _status_payload(construction_status),
        "actual_factory": _factory_record(actual_factory),
        "ablated_factory": _factory_record(ablated_factory),
        "ablation_manifest": _manifest_record(ablation_manifest),
    }


def ablation_pair_snapshot_payload(
    snapshot: AblationPairSnapshot,
) -> dict[str, object]:
    if not isinstance(snapshot, AblationPairSnapshot):
        raise TypeError("snapshot must be an AblationPairSnapshot")
    return {
        "snapshot_schema_version": snapshot.snapshot_schema_version,
        **ablation_construction_payload(
            snapshot.construction_status,
            snapshot.actual_factory,
            snapshot.ablated_factory,
            snapshot.ablation_manifest,
        ),
        "ablation_construction_sha": snapshot.ablation_construction_sha,
    }


def _pair_snapshot(
    construction: AblationConstructionOutcome,
) -> tuple[AblationPairSnapshot, VerifiedFactory, VerifiedFactory]:
    verified = _verify_construction_outcome(construction)
    if not verified.status.defined or verified.pair is None:
        raise ValueError("prestructure authority requires a defined pair")
    actual_view = _reverify_verified_factory(verified.pair.actual)
    ablated_view = _reverify_verified_factory(verified.pair.ablated)
    construction_body = ablation_construction_payload(
        verified.status,
        actual_view.factory,
        ablated_view.factory,
        verified.pair.manifest,
    )
    construction_sha = canonical_sha(construction_body)
    provisional = AblationPairSnapshot(
        snapshot_schema_version=PAIR_SNAPSHOT_SCHEMA_VERSION,
        construction_status=verified.status,
        actual_factory=actual_view.factory,
        ablated_factory=ablated_view.factory,
        ablation_manifest=verified.pair.manifest,
        ablation_construction_sha=construction_sha,
        snapshot_sha="0" * 64,
    )
    snapshot = replace(
        provisional,
        snapshot_sha=canonical_sha(ablation_pair_snapshot_payload(provisional)),
    )
    return snapshot, verified.pair.actual, verified.pair.ablated


__all__ = (
    "PAIR_SNAPSHOT_SCHEMA_VERSION",
    "AblationPairSnapshot",
    "ablation_construction_payload",
    "ablation_pair_snapshot_payload",
)
