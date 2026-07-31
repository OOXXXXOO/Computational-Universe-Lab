"""Pre-response structure authority for V3-M0.

This module is deliberately upstream of dynamics.  It binds a closed parent,
control-registry entry, mechanically matched ablation pair, role-specific
factory, and canonical classical structure before any transition is measured.
Raw records are serializable evidence; only the opaque live wrapper is an
authority.
"""

from __future__ import annotations

import re
import threading
import weakref
from dataclasses import dataclass, replace
from typing import Callable, Literal, Optional

import numpy as np

from .ablation import (
    AblationConstructionOutcome,
    AblationManifest,
    _verify_construction_outcome,
    ablation_manifest_payload,
)
from .contracts import BlockStatus
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    LinearRealspaceFactory,
    VerifiedFactory,
    _reverify_verified_factory,
    factory_payload,
    freeze_complex_tensor,
    frozen_tensor_payload,
)
from .parent_freeze import (
    ParentFreezeManifest,
    V3M0SyntheticControlApplicationSpec,
    VerifiedParentFreeze,
    _reverify_verified_parent_freeze,
    parent_freeze_manifest_payload,
    synthetic_control_application_spec_payload,
    verify_synthetic_control_application_spec,
)
from .registry import (
    ClosedControlRegistry,
    VerifiedControlRegistry,
    _reverify_verified_control_registry,
    closed_control_registry_payload,
)


PAIR_SNAPSHOT_SCHEMA_VERSION = "v3m0.ablation-pair-snapshot.v1"
SYNTHETIC_PREREGISTRATION_SCHEMA_VERSION = "v3m0.synthetic-structure-preregistration.v1"
PRESTRUCTURE_AUTHORITY_SCHEMA_VERSION = "v3m0.prestructure-authority.v1"
SYNTHETIC_EVIDENCE_LANE: Literal["synthetic-classical"] = "synthetic-classical"
SYNTHETIC_AUTHORITY_KIND: Literal["synthetic-registry-v1"] = "synthetic-registry-v1"
SYNTHETIC_APPLICATION_AUTHORITY_KIND: Literal["synthetic-application-v1"] = (
    "synthetic-application-v1"
)
FOURIER_ADJOINT_CONVENTION_ID: Literal["minus-k-transpose-v1"] = "minus-k-transpose-v1"
REALITY_CONVENTION_ID: Literal["real-kernel-positive-zero-v1"] = (
    "real-kernel-positive-zero-v1"
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()


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


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


def _parent_record(parent: ParentFreezeManifest) -> dict[str, object]:
    return {
        **parent_freeze_manifest_payload(parent),
        "parent_freeze_sha": parent.parent_freeze_sha,
    }


def _registry_record(registry: ClosedControlRegistry) -> dict[str, object]:
    return {
        **closed_control_registry_payload(registry),
        "registry_sha": registry.registry_sha,
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


@dataclass(frozen=True)
class SyntheticStructurePreregistration:
    preregistration_schema_version: str
    evidence_lane: Literal["synthetic-classical"]
    control_registry_sha: str
    control_registry_entry_sha: str
    factory_sha: str
    factory_role: Literal["actual", "matched_ablated"]
    ablation_manifest_sha: str
    ablation_construction_sha: str
    target_spec_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    canonical_channel_pairs: tuple[tuple[str, str], ...]
    fourier_adjoint_convention_id: Literal["minus-k-transpose-v1"]
    structure_form: FrozenComplexTensor
    reality_convention_id: Literal["real-kernel-positive-zero-v1"]
    parent_freeze_sha: str
    preregistration_sha: str

    def __post_init__(self) -> None:
        _text(
            self.preregistration_schema_version,
            "preregistration_schema_version",
        )
        if self.evidence_lane != SYNTHETIC_EVIDENCE_LANE:
            raise ValueError("synthetic evidence lane is not closed")
        for field in (
            "control_registry_sha",
            "control_registry_entry_sha",
            "factory_sha",
            "ablation_manifest_sha",
            "ablation_construction_sha",
            "target_spec_sha",
            "parent_freeze_sha",
            "preregistration_sha",
        ):
            _sha(getattr(self, field), field)
        if self.factory_role not in ("actual", "matched_ablated"):
            raise ValueError("factory_role is not frozen")
        _text(self.state_schema_id, "state_schema_id")
        if type(self.channel_order) is not tuple or not self.channel_order:
            raise ValueError("channel_order must be a non-empty tuple")
        if type(self.canonical_channel_pairs) is not tuple:
            raise TypeError("canonical_channel_pairs must be a tuple")
        if self.fourier_adjoint_convention_id != FOURIER_ADJOINT_CONVENTION_ID:
            raise ValueError("Fourier adjoint convention is not closed")
        if not isinstance(self.structure_form, FrozenComplexTensor):
            raise TypeError("structure_form must be a FrozenComplexTensor")
        if self.reality_convention_id != REALITY_CONVENTION_ID:
            raise ValueError("reality convention is not closed")


@dataclass(frozen=True)
class PrestructureAuthority:
    authority_schema_version: str
    authority_kind: Literal[
        "synthetic-registry-v1",
        "synthetic-application-v1",
        "adapter-preregistration-v1",
    ]
    parent_freeze: ParentFreezeManifest
    factory_sha: str
    factory_role: Literal["actual", "matched_ablated"]
    ablation_pair_snapshot: AblationPairSnapshot
    ablation_manifest_sha: str
    ablation_construction_sha: str
    synthetic_registry: Optional[ClosedControlRegistry]
    synthetic_registry_entry_sha: Optional[str]
    synthetic_preregistration: Optional[SyntheticStructurePreregistration]
    synthetic_application_spec: Optional[V3M0SyntheticControlApplicationSpec]
    synthetic_application_permit_sha: Optional[str]
    adapter_preregistration: Optional[object]
    authority_sha: str

    def __post_init__(self) -> None:
        _text(self.authority_schema_version, "authority_schema_version")
        if self.authority_kind not in (
            "synthetic-registry-v1",
            "synthetic-application-v1",
            "adapter-preregistration-v1",
        ):
            raise ValueError("authority_kind is not closed")
        if not isinstance(self.parent_freeze, ParentFreezeManifest):
            raise TypeError("parent_freeze has the wrong record type")
        _sha(self.factory_sha, "factory_sha")
        if self.factory_role not in ("actual", "matched_ablated"):
            raise ValueError("factory_role is not frozen")
        if not isinstance(self.ablation_pair_snapshot, AblationPairSnapshot):
            raise TypeError("ablation_pair_snapshot has the wrong record type")
        _sha(self.ablation_manifest_sha, "ablation_manifest_sha")
        _sha(self.ablation_construction_sha, "ablation_construction_sha")
        presence = (
            self.synthetic_registry is not None,
            self.synthetic_application_spec is not None,
            self.adapter_preregistration is not None,
        )
        if sum(presence) != 1:
            raise ValueError("authority branches must be present exactly once")
        if self.authority_kind == SYNTHETIC_AUTHORITY_KIND:
            if not presence[0]:
                raise ValueError("synthetic registry authority body is absent")
            if self.synthetic_registry_entry_sha is None:
                raise ValueError("synthetic registry entry SHA is absent")
            _sha(
                self.synthetic_registry_entry_sha,
                "synthetic_registry_entry_sha",
            )
            if not isinstance(
                self.synthetic_preregistration,
                SyntheticStructurePreregistration,
            ):
                raise TypeError("synthetic preregistration body is absent")
            if (
                self.synthetic_application_permit_sha is not None
                or self.synthetic_application_spec is not None
                or self.adapter_preregistration is not None
            ):
                raise ValueError("synthetic registry authority is branch-mixed")
        elif self.authority_kind == SYNTHETIC_APPLICATION_AUTHORITY_KIND:
            if not presence[1]:
                raise ValueError("synthetic application authority body is absent")
            if (
                type(self.synthetic_application_spec)
                is not V3M0SyntheticControlApplicationSpec
            ):
                raise TypeError("synthetic application spec has the wrong record type")
            if self.synthetic_application_permit_sha is None:
                raise ValueError("synthetic application permit SHA is absent")
            _sha(
                self.synthetic_application_permit_sha,
                "synthetic_application_permit_sha",
            )
            if (
                self.synthetic_registry is not None
                or self.synthetic_registry_entry_sha is not None
                or self.synthetic_preregistration is not None
                or self.adapter_preregistration is not None
            ):
                raise ValueError("synthetic application authority is branch-mixed")
        _sha(self.authority_sha, "authority_sha")


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


def synthetic_preregistration_payload(
    preregistration: SyntheticStructurePreregistration,
) -> dict[str, object]:
    if not isinstance(
        preregistration,
        SyntheticStructurePreregistration,
    ):
        raise TypeError("preregistration must be a SyntheticStructurePreregistration")
    return {
        "preregistration_schema_version": (
            preregistration.preregistration_schema_version
        ),
        "evidence_lane": preregistration.evidence_lane,
        "control_registry_sha": preregistration.control_registry_sha,
        "control_registry_entry_sha": (preregistration.control_registry_entry_sha),
        "factory_sha": preregistration.factory_sha,
        "factory_role": preregistration.factory_role,
        "ablation_manifest_sha": preregistration.ablation_manifest_sha,
        "ablation_construction_sha": (preregistration.ablation_construction_sha),
        "target_spec_sha": preregistration.target_spec_sha,
        "state_schema_id": preregistration.state_schema_id,
        "channel_order": list(preregistration.channel_order),
        "canonical_channel_pairs": [
            list(item) for item in preregistration.canonical_channel_pairs
        ],
        "fourier_adjoint_convention_id": (
            preregistration.fourier_adjoint_convention_id
        ),
        "structure_form": _tensor_record(preregistration.structure_form),
        "reality_convention_id": preregistration.reality_convention_id,
        "parent_freeze_sha": preregistration.parent_freeze_sha,
    }


def _preregistration_record(
    preregistration: SyntheticStructurePreregistration,
) -> dict[str, object]:
    return {
        **synthetic_preregistration_payload(preregistration),
        "preregistration_sha": preregistration.preregistration_sha,
    }


def prestructure_authority_payload(
    authority: PrestructureAuthority,
) -> dict[str, object]:
    if not isinstance(authority, PrestructureAuthority):
        raise TypeError("authority must be a PrestructureAuthority")
    adapter: object = authority.adapter_preregistration
    if adapter is not None:
        raise ValueError(
            "adapter preregistration authority is not implemented in V3-M0"
        )
    return {
        "authority_schema_version": authority.authority_schema_version,
        "authority_kind": authority.authority_kind,
        "parent_freeze": _parent_record(authority.parent_freeze),
        "factory_sha": authority.factory_sha,
        "factory_role": authority.factory_role,
        "ablation_pair_snapshot": {
            **ablation_pair_snapshot_payload(authority.ablation_pair_snapshot),
            "snapshot_sha": authority.ablation_pair_snapshot.snapshot_sha,
        },
        "ablation_manifest_sha": authority.ablation_manifest_sha,
        "ablation_construction_sha": authority.ablation_construction_sha,
        "synthetic_registry": (
            None
            if authority.synthetic_registry is None
            else _registry_record(authority.synthetic_registry)
        ),
        "synthetic_registry_entry_sha": (authority.synthetic_registry_entry_sha),
        "synthetic_preregistration": (
            None
            if authority.synthetic_preregistration is None
            else _preregistration_record(authority.synthetic_preregistration)
        ),
        "synthetic_application_spec": (
            None
            if authority.synthetic_application_spec is None
            else {
                **synthetic_control_application_spec_payload(
                    authority.synthetic_application_spec
                ),
                "application_spec_sha": (
                    authority.synthetic_application_spec.application_spec_sha
                ),
            }
        ),
        "synthetic_application_permit_sha": (
            authority.synthetic_application_permit_sha
        ),
        "adapter_preregistration": None,
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


def _canonical_pairs(
    channels: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    if type(channels) is not tuple or not channels:
        raise ValueError("channel_order must be a non-empty tuple")
    if len(channels) % 2:
        raise ValueError("synthetic classical channels must be even")
    if len(set(channels)) != len(channels):
        raise ValueError("channel_order contains duplicates")
    return tuple(
        (channels[index], channels[index + 1]) for index in range(0, len(channels), 2)
    )


def _canonical_structure_form(
    channels: tuple[str, ...],
) -> FrozenComplexTensor:
    pairs = _canonical_pairs(channels)
    result = np.zeros(
        (len(channels), len(channels)),
        dtype=np.complex128,
    )
    for index, _ in enumerate(pairs):
        first = 2 * index
        second = first + 1
        result[first, second] = 1.0 + 0.0j
        result[second, first] = -1.0 + 0.0j
    return freeze_complex_tensor(result)


def _expected_authority(
    parent: VerifiedParentFreeze,
    registry: VerifiedControlRegistry,
    control_id: Literal["full", "zero", "direct_sum"],
    construction: AblationConstructionOutcome,
    factory_role: Literal["actual", "matched_ablated"],
) -> tuple[PrestructureAuthority, VerifiedFactory]:
    parent_manifest = _reverify_verified_parent_freeze(parent)
    registry_view = _reverify_verified_control_registry(registry)
    if registry_view.parent is not parent:
        raise ValueError("registry is not bound to this live parent")
    if registry_view.registry.parent_freeze_sha != parent_manifest.parent_freeze_sha:
        raise ValueError("registry parent freeze mismatch")
    if control_id not in ("full", "zero", "direct_sum"):
        raise ValueError("control_id is not in the closed registry")
    if factory_role not in ("actual", "matched_ablated"):
        raise ValueError("factory_role is not frozen")
    index = ("full", "zero", "direct_sum").index(control_id)
    entry = registry_view.registry.entries[index]
    bundle = registry_view.controls[index]
    snapshot, actual, ablated = _pair_snapshot(construction)
    registry_actual = _reverify_verified_factory(bundle.factory)
    pair_actual = _reverify_verified_factory(actual)
    if pair_actual.factory != registry_actual.factory:
        raise ValueError("ablation pair does not belong to registry entry")
    if entry.factory_sha != pair_actual.factory.factory_sha:
        raise ValueError("registry entry factory SHA mismatch")
    selected = actual if factory_role == "actual" else ablated
    selected_view = _reverify_verified_factory(selected)
    if selected_view.role != factory_role:
        raise ValueError("selected factory role mismatch")
    channels = selected_view.factory.channel_order
    pairs = _canonical_pairs(channels)
    structure_form = _canonical_structure_form(channels)
    provisional_prereg = SyntheticStructurePreregistration(
        preregistration_schema_version=(SYNTHETIC_PREREGISTRATION_SCHEMA_VERSION),
        evidence_lane=SYNTHETIC_EVIDENCE_LANE,
        control_registry_sha=registry_view.registry.registry_sha,
        control_registry_entry_sha=entry.entry_sha,
        factory_sha=selected_view.factory.factory_sha,
        factory_role=factory_role,
        ablation_manifest_sha=snapshot.ablation_manifest.manifest_sha,
        ablation_construction_sha=snapshot.ablation_construction_sha,
        target_spec_sha=selected_view.factory.target_spec_sha,
        state_schema_id=selected_view.factory.state_schema_id,
        channel_order=channels,
        canonical_channel_pairs=pairs,
        fourier_adjoint_convention_id=FOURIER_ADJOINT_CONVENTION_ID,
        structure_form=structure_form,
        reality_convention_id=REALITY_CONVENTION_ID,
        parent_freeze_sha=parent_manifest.parent_freeze_sha,
        preregistration_sha="0" * 64,
    )
    prereg = replace(
        provisional_prereg,
        preregistration_sha=canonical_sha(
            synthetic_preregistration_payload(provisional_prereg)
        ),
    )
    provisional_authority = PrestructureAuthority(
        authority_schema_version=PRESTRUCTURE_AUTHORITY_SCHEMA_VERSION,
        authority_kind=SYNTHETIC_AUTHORITY_KIND,
        parent_freeze=parent_manifest,
        factory_sha=selected_view.factory.factory_sha,
        factory_role=factory_role,
        ablation_pair_snapshot=snapshot,
        ablation_manifest_sha=snapshot.ablation_manifest.manifest_sha,
        ablation_construction_sha=snapshot.ablation_construction_sha,
        synthetic_registry=registry_view.registry,
        synthetic_registry_entry_sha=entry.entry_sha,
        synthetic_preregistration=prereg,
        synthetic_application_spec=None,
        synthetic_application_permit_sha=None,
        adapter_preregistration=None,
        authority_sha="0" * 64,
    )
    authority = replace(
        provisional_authority,
        authority_sha=canonical_sha(
            prestructure_authority_payload(provisional_authority)
        ),
    )
    return authority, selected


def _expected_application_authority(
    parent: VerifiedParentFreeze,
    application_spec: V3M0SyntheticControlApplicationSpec,
    application_permit_sha: str,
    construction: AblationConstructionOutcome,
    factory_role: Literal["actual", "matched_ablated"],
) -> tuple[PrestructureAuthority, VerifiedFactory]:
    """Reconstruct the application branch from its parent-bound matched pair."""

    parent_manifest = _reverify_verified_parent_freeze(parent)
    if type(application_spec) is not V3M0SyntheticControlApplicationSpec:
        raise TypeError(
            "application_spec must be an exact V3M0SyntheticControlApplicationSpec"
        )
    application = verify_synthetic_control_application_spec(application_spec)
    matches = tuple(
        item
        for item in parent_manifest.synthetic_control_application_specs
        if item.application_instance_id == application.application_instance_id
    )
    if len(matches) != 1 or matches[0] != application:
        raise ValueError("application spec is not the unique parent-frozen body")
    permit_sha = _sha(
        application_permit_sha,
        "synthetic_application_permit_sha",
    )
    if factory_role not in ("actual", "matched_ablated"):
        raise ValueError("factory_role is not frozen")
    snapshot, actual, ablated = _pair_snapshot(construction)
    selected = actual if factory_role == "actual" else ablated
    selected_view = _reverify_verified_factory(selected)
    if selected_view.role != factory_role:
        raise ValueError("selected application factory role mismatch")
    factory = selected_view.factory
    source = application.basis_protocol.source_basis
    readout = application.basis_protocol.readout_basis
    if (
        source.state_schema_id != readout.state_schema_id
        or source.channel_order != readout.channel_order
    ):
        raise ValueError("application source/readout basis interface mismatch")
    if (
        factory.state_schema_id != source.state_schema_id
        or factory.channel_order != source.channel_order
        or factory.source_manifest_id != source.manifest_id
        or factory.readout_basis != readout
        or factory.state_shape[1:] != application.grid_protocol.spatial_shape
    ):
        raise ValueError(
            "application matched pair does not implement the frozen interface"
        )
    provisional = PrestructureAuthority(
        authority_schema_version=PRESTRUCTURE_AUTHORITY_SCHEMA_VERSION,
        authority_kind=SYNTHETIC_APPLICATION_AUTHORITY_KIND,
        parent_freeze=parent_manifest,
        factory_sha=factory.factory_sha,
        factory_role=factory_role,
        ablation_pair_snapshot=snapshot,
        ablation_manifest_sha=snapshot.ablation_manifest.manifest_sha,
        ablation_construction_sha=snapshot.ablation_construction_sha,
        synthetic_registry=None,
        synthetic_registry_entry_sha=None,
        synthetic_preregistration=None,
        synthetic_application_spec=application,
        synthetic_application_permit_sha=permit_sha,
        adapter_preregistration=None,
        authority_sha="0" * 64,
    )
    authority = replace(
        provisional,
        authority_sha=canonical_sha(prestructure_authority_payload(provisional)),
    )
    return authority, selected


class VerifiedPrestructureAuthority:
    """Opaque live role-specific authority issued before measurement."""

    __slots__ = ("__authority", "__parent", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        authority: PrestructureAuthority,
        parent: VerifiedParentFreeze,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("VerifiedPrestructureAuthority can only be issued here")
        object.__setattr__(
            self,
            "_VerifiedPrestructureAuthority__authority",
            authority,
        )
        object.__setattr__(
            self,
            "_VerifiedPrestructureAuthority__parent",
            parent,
        )
        object.__setattr__(
            self,
            "_VerifiedPrestructureAuthority__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedPrestructureAuthority__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedPrestructureAuthority is immutable")

    @property
    def authority(self) -> PrestructureAuthority:
        return self.__authority

    @property
    def parent(self) -> VerifiedParentFreeze:
        return self.__parent

    @property
    def factory_sha(self) -> str:
        return self.__authority.factory_sha

    @property
    def factory_role(self) -> Literal["actual", "matched_ablated"]:
        return self.__authority.factory_role


@dataclass(frozen=True)
class _VerifiedPrestructureView:
    authority: PrestructureAuthority
    parent: VerifiedParentFreeze
    registry: Optional[VerifiedControlRegistry]
    construction: AblationConstructionOutcome
    factory: VerifiedFactory
    control_id: Optional[Literal["full", "zero", "direct_sum"]]
    application_spec: Optional[V3M0SyntheticControlApplicationSpec]
    application_permit_sha: Optional[str]


@dataclass(frozen=True)
class _PrestructureAuthorityRecord:
    authority: PrestructureAuthority
    parent: VerifiedParentFreeze
    registry: Optional[VerifiedControlRegistry]
    construction: AblationConstructionOutcome
    factory: VerifiedFactory
    control_id: Optional[Literal["full", "zero", "direct_sum"]]
    application_spec: Optional[V3M0SyntheticControlApplicationSpec]
    application_permit_sha: Optional[str]
    seal: str


def _authority_seal(
    authority: PrestructureAuthority,
    factory: VerifiedFactory,
) -> str:
    factory_view = _reverify_verified_factory(factory)
    if factory_view.factory.factory_sha != authority.factory_sha:
        raise ValueError("authority factory binding mismatch")
    if factory_view.role != authority.factory_role:
        raise ValueError("authority factory role mismatch")
    return canonical_sha(
        {
            "verified_authority_schema_version": (
                "v3m0.verified-prestructure-authority.v1"
            ),
            "authority": {
                **prestructure_authority_payload(authority),
                "authority_sha": authority.authority_sha,
            },
            "live_factory_sha": factory_view.factory.factory_sha,
            "live_factory_role": factory_view.role,
        }
    )


def _make_prestructure_authority() -> tuple[
    Callable[..., VerifiedPrestructureAuthority],
    Callable[..., VerifiedPrestructureAuthority],
    Callable[
        [VerifiedPrestructureAuthority],
        _VerifiedPrestructureView,
    ],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedPrestructureAuthority],
            _PrestructureAuthorityRecord,
        ],
    ] = {}
    lock = threading.RLock()

    def register(
        authority: PrestructureAuthority,
        parent: VerifiedParentFreeze,
        construction: AblationConstructionOutcome,
        factory: VerifiedFactory,
        *,
        registry: Optional[VerifiedControlRegistry],
        control_id: Optional[Literal["full", "zero", "direct_sum"]],
        application_spec: Optional[V3M0SyntheticControlApplicationSpec],
        application_permit_sha: Optional[str],
    ) -> VerifiedPrestructureAuthority:
        seal = _authority_seal(authority, factory)
        record = _PrestructureAuthorityRecord(
            authority=authority,
            parent=parent,
            registry=registry,
            construction=construction,
            factory=factory,
            control_id=control_id,
            application_spec=application_spec,
            application_permit_sha=application_permit_sha,
            seal=seal,
        )
        wrapper = VerifiedPrestructureAuthority(
            _ISSUANCE_TOKEN,
            authority,
            parent,
            seal,
        )
        identity = id(wrapper)

        def remove(
            reference: weakref.ReferenceType[VerifiedPrestructureAuthority],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (reference, record)
        return wrapper

    def issue_registry(
        parent: VerifiedParentFreeze,
        registry: VerifiedControlRegistry,
        control_id: Literal["full", "zero", "direct_sum"],
        construction: AblationConstructionOutcome,
        role: Literal["actual", "matched_ablated"],
        raw: Optional[PrestructureAuthority] = None,
    ) -> VerifiedPrestructureAuthority:
        expected, factory = _expected_authority(
            parent,
            registry,
            control_id,
            construction,
            role,
        )
        if raw is not None and raw != expected:
            raise ValueError("raw prestructure authority does not match reconstruction")
        authority = expected if raw is None else raw
        return register(
            authority,
            parent,
            construction,
            factory,
            registry=registry,
            control_id=control_id,
            application_spec=None,
            application_permit_sha=None,
        )

    def issue_application(
        parent: VerifiedParentFreeze,
        application_spec: V3M0SyntheticControlApplicationSpec,
        application_permit_sha: str,
        construction: AblationConstructionOutcome,
        role: Literal["actual", "matched_ablated"],
    ) -> VerifiedPrestructureAuthority:
        expected, factory = _expected_application_authority(
            parent,
            application_spec,
            application_permit_sha,
            construction,
            role,
        )
        return register(
            expected,
            parent,
            construction,
            factory,
            registry=None,
            control_id=None,
            application_spec=application_spec,
            application_permit_sha=application_permit_sha,
        )

    def reverify(
        wrapper: VerifiedPrestructureAuthority,
    ) -> _VerifiedPrestructureView:
        if type(wrapper) is not VerifiedPrestructureAuthority:
            raise TypeError(
                "runtime requires a module-issued VerifiedPrestructureAuthority"
            )
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError("VerifiedPrestructureAuthority identity is not live")
            record = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedPrestructureAuthority__token",
            )
            raw = object.__getattribute__(
                wrapper,
                "_VerifiedPrestructureAuthority__authority",
            )
            parent = object.__getattribute__(
                wrapper,
                "_VerifiedPrestructureAuthority__parent",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedPrestructureAuthority__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "VerifiedPrestructureAuthority record is incomplete"
            ) from exc
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("VerifiedPrestructureAuthority token mismatch")
        if record.authority.authority_kind == SYNTHETIC_AUTHORITY_KIND:
            if record.registry is None or record.control_id is None:
                raise ValueError("registry prestructure authority record is incomplete")
            expected, factory = _expected_authority(
                record.parent,
                record.registry,
                record.control_id,
                record.construction,
                record.authority.factory_role,
            )
        elif record.authority.authority_kind == SYNTHETIC_APPLICATION_AUTHORITY_KIND:
            if record.application_spec is None or record.application_permit_sha is None:
                raise ValueError(
                    "application prestructure authority record is incomplete"
                )
            expected, factory = _expected_application_authority(
                record.parent,
                record.application_spec,
                record.application_permit_sha,
                record.construction,
                record.authority.factory_role,
            )
        else:
            raise ValueError("prestructure authority branch is not implemented")
        expected_seal = _authority_seal(expected, factory)
        if (
            raw != record.authority
            or raw != expected
            or parent is not record.parent
            or factory is not record.factory
            or seal != record.seal
            or seal != expected_seal
        ):
            raise ValueError("VerifiedPrestructureAuthority immutable seal mismatch")
        return _VerifiedPrestructureView(
            authority=record.authority,
            parent=record.parent,
            registry=record.registry,
            construction=record.construction,
            factory=record.factory,
            control_id=record.control_id,
            application_spec=record.application_spec,
            application_permit_sha=record.application_permit_sha,
        )

    return issue_registry, issue_application, reverify


(
    _issue_verified_prestructure_authority,
    _issue_verified_application_prestructure_authority,
    _reverify_verified_prestructure_authority,
) = _make_prestructure_authority()


def issue_synthetic_prestructure_authority(
    parent: VerifiedParentFreeze,
    registry: VerifiedControlRegistry,
    control_id: Literal["full", "zero", "direct_sum"],
    construction: AblationConstructionOutcome,
    factory_role: Literal["actual", "matched_ablated"],
) -> VerifiedPrestructureAuthority:
    """Bind one matched-pair role before any structure-dependent run."""

    return _issue_verified_prestructure_authority(
        parent,
        registry,
        control_id,
        construction,
        factory_role,
    )


def _issue_synthetic_application_prestructure_authority(
    parent: VerifiedParentFreeze,
    application_spec: V3M0SyntheticControlApplicationSpec,
    application_permit_sha: str,
    construction: AblationConstructionOutcome,
    factory_role: Literal["actual", "matched_ablated"],
) -> VerifiedPrestructureAuthority:
    """Internal Task-12-only application authority issuer."""

    return _issue_verified_application_prestructure_authority(
        parent,
        application_spec,
        application_permit_sha,
        construction,
        factory_role,
    )


def verify_synthetic_prestructure_authority(
    authority: PrestructureAuthority,
    parent: VerifiedParentFreeze,
    registry: VerifiedControlRegistry,
    control_id: Literal["full", "zero", "direct_sum"],
    construction: AblationConstructionOutcome,
    factory_role: Literal["actual", "matched_ablated"],
) -> VerifiedPrestructureAuthority:
    """Hydrate only by replaying the live parent, registry and exact pair."""

    if not isinstance(authority, PrestructureAuthority):
        raise TypeError("authority must be a PrestructureAuthority")
    if authority.authority_sha != canonical_sha(
        prestructure_authority_payload(authority)
    ):
        raise ValueError("authority_sha does not match complete body")
    return _issue_verified_prestructure_authority(
        parent,
        registry,
        control_id,
        construction,
        factory_role,
        raw=authority,
    )


__all__ = [
    "FOURIER_ADJOINT_CONVENTION_ID",
    "PAIR_SNAPSHOT_SCHEMA_VERSION",
    "PRESTRUCTURE_AUTHORITY_SCHEMA_VERSION",
    "REALITY_CONVENTION_ID",
    "SYNTHETIC_APPLICATION_AUTHORITY_KIND",
    "SYNTHETIC_AUTHORITY_KIND",
    "SYNTHETIC_EVIDENCE_LANE",
    "SYNTHETIC_PREREGISTRATION_SCHEMA_VERSION",
    "AblationPairSnapshot",
    "PrestructureAuthority",
    "SyntheticStructurePreregistration",
    "VerifiedPrestructureAuthority",
    "ablation_construction_payload",
    "ablation_pair_snapshot_payload",
    "issue_synthetic_prestructure_authority",
    "prestructure_authority_payload",
    "synthetic_preregistration_payload",
    "verify_synthetic_prestructure_authority",
]
