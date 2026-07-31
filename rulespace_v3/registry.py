"""Closed V3-M0 synthetic-control registry.

The public records in this module are serialization wires.  Only
``VerifiedControlRegistry`` is a runtime authority, and every consumer
replays the three closed control builders, their factory seals, the parent
freeze, and every recursive hash before using it.
"""

from __future__ import annotations

import re
import threading
import weakref
from dataclasses import dataclass, replace
from typing import Callable, Literal

import numpy as np

from .controls import SyntheticControlBundle
from .evidence import canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    _reverify_verified_factory,
    basis_manifest_payload,
    freeze_complex_tensor,
    frozen_tensor_payload,
    verify_basis_manifest,
)
from .parent_freeze import (
    VerifiedParentFreeze,
    _reverify_verified_parent_freeze,
)
from .trace import MechanismKind


READOUT_SPEC_SCHEMA_VERSION = "v3m0.control-readout-calibration-spec.v1"
CONTROL_ENTRY_SCHEMA_VERSION = "v3m0.control-registry-entry.v1"
CONTROL_REGISTRY_SCHEMA_VERSION = "v3m0.closed-control-registry.v1"
CURVATURE_NORMALIZER_ID: Literal["synthetic-identity-v1"] = (
    "synthetic-identity-v1"
)
CONTROL_ORDER = ("full", "zero", "direct_sum")
_BUILDERS = {
    "full": "synthetic-control-full-v1",
    "zero": "synthetic-control-zero-v1",
    "direct_sum": "synthetic-control-direct-sum-v1",
}
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


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _basis_record(value: BasisManifest) -> dict[str, object]:
    verified = verify_basis_manifest(value)
    return {
        **basis_manifest_payload(verified),
        "manifest_id": verified.manifest_id,
    }


def _tensor_record(value: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(value),
        "tensor_sha": value.tensor_sha,
    }


@dataclass(frozen=True)
class ControlReadoutCalibrationSpec:
    spec_schema_version: str
    source_metric_whitener: FrozenComplexTensor
    h_metric_whitener: FrozenComplexTensor
    curvature_incidence_operator: FrozenComplexTensor
    curvature_metric_whitener: FrozenComplexTensor
    curvature_normalizer_id: Literal["synthetic-identity-v1"]
    spec_sha: str

    def __post_init__(self) -> None:
        _text(self.spec_schema_version, "spec_schema_version")
        for field in (
            "source_metric_whitener",
            "h_metric_whitener",
            "curvature_incidence_operator",
            "curvature_metric_whitener",
        ):
            if not isinstance(getattr(self, field), FrozenComplexTensor):
                raise TypeError(f"{field} must be a FrozenComplexTensor")
        if self.curvature_normalizer_id != CURVATURE_NORMALIZER_ID:
            raise ValueError("curvature_normalizer_id is not closed")
        _sha(self.spec_sha, "spec_sha")


@dataclass(frozen=True)
class ControlRegistryEntry:
    entry_schema_version: str
    control_id: Literal["full", "zero", "direct_sum"]
    builder_id: str
    factory_sha: str
    source_basis: BasisManifest
    readout_basis: BasisManifest
    readout_calibration_spec: ControlReadoutCalibrationSpec
    mode_count: int
    expected_h_actual_rank: int
    expected_h_ablated_rank: int
    expected_curv_actual_rank: int
    expected_curv_ablated_rank: int
    parent_freeze_sha: str
    entry_sha: str

    def __post_init__(self) -> None:
        _text(self.entry_schema_version, "entry_schema_version")
        if self.control_id not in CONTROL_ORDER:
            raise ValueError("control_id is not in the closed registry")
        _text(self.builder_id, "builder_id")
        _sha(self.factory_sha, "factory_sha")
        if not isinstance(self.source_basis, BasisManifest):
            raise TypeError("source_basis must be a BasisManifest")
        if not isinstance(self.readout_basis, BasisManifest):
            raise TypeError("readout_basis must be a BasisManifest")
        if not isinstance(
            self.readout_calibration_spec,
            ControlReadoutCalibrationSpec,
        ):
            raise TypeError(
                "readout_calibration_spec has the wrong record type"
            )
        if type(self.mode_count) is not int or self.mode_count <= 0:
            raise ValueError("mode_count must be a positive int")
        for field in (
            "expected_h_actual_rank",
            "expected_h_ablated_rank",
            "expected_curv_actual_rank",
            "expected_curv_ablated_rank",
        ):
            _nonnegative_int(getattr(self, field), field)
        _sha(self.parent_freeze_sha, "parent_freeze_sha")
        _sha(self.entry_sha, "entry_sha")


@dataclass(frozen=True)
class ClosedControlRegistry:
    registry_schema_version: str
    entries: tuple[ControlRegistryEntry, ...]
    parent_freeze_sha: str
    registry_sha: str

    def __post_init__(self) -> None:
        _text(self.registry_schema_version, "registry_schema_version")
        if type(self.entries) is not tuple:
            raise TypeError("entries must be a tuple")
        if not all(isinstance(item, ControlRegistryEntry) for item in self.entries):
            raise TypeError("entries must contain ControlRegistryEntry records")
        if tuple(item.control_id for item in self.entries) != CONTROL_ORDER:
            raise ValueError("entries are not in the unique closed order")
        _sha(self.parent_freeze_sha, "parent_freeze_sha")
        _sha(self.registry_sha, "registry_sha")


def readout_calibration_spec_payload(
    spec: ControlReadoutCalibrationSpec,
) -> dict[str, object]:
    if not isinstance(spec, ControlReadoutCalibrationSpec):
        raise TypeError("spec must be a ControlReadoutCalibrationSpec")
    return {
        "spec_schema_version": spec.spec_schema_version,
        "source_metric_whitener": _tensor_record(
            spec.source_metric_whitener
        ),
        "h_metric_whitener": _tensor_record(spec.h_metric_whitener),
        "curvature_incidence_operator": _tensor_record(
            spec.curvature_incidence_operator
        ),
        "curvature_metric_whitener": _tensor_record(
            spec.curvature_metric_whitener
        ),
        "curvature_normalizer_id": spec.curvature_normalizer_id,
    }


def _readout_spec_record(
    spec: ControlReadoutCalibrationSpec,
) -> dict[str, object]:
    return {
        **readout_calibration_spec_payload(spec),
        "spec_sha": spec.spec_sha,
    }


def control_registry_entry_payload(
    entry: ControlRegistryEntry,
) -> dict[str, object]:
    if not isinstance(entry, ControlRegistryEntry):
        raise TypeError("entry must be a ControlRegistryEntry")
    return {
        "entry_schema_version": entry.entry_schema_version,
        "control_id": entry.control_id,
        "builder_id": entry.builder_id,
        "factory_sha": entry.factory_sha,
        "source_basis": _basis_record(entry.source_basis),
        "readout_basis": _basis_record(entry.readout_basis),
        "readout_calibration_spec": _readout_spec_record(
            entry.readout_calibration_spec
        ),
        "mode_count": entry.mode_count,
        "expected_h_actual_rank": entry.expected_h_actual_rank,
        "expected_h_ablated_rank": entry.expected_h_ablated_rank,
        "expected_curv_actual_rank": entry.expected_curv_actual_rank,
        "expected_curv_ablated_rank": entry.expected_curv_ablated_rank,
        "parent_freeze_sha": entry.parent_freeze_sha,
    }


def _entry_record(entry: ControlRegistryEntry) -> dict[str, object]:
    return {
        **control_registry_entry_payload(entry),
        "entry_sha": entry.entry_sha,
    }


def closed_control_registry_payload(
    registry: ClosedControlRegistry,
) -> dict[str, object]:
    if not isinstance(registry, ClosedControlRegistry):
        raise TypeError("registry must be a ClosedControlRegistry")
    return {
        "registry_schema_version": registry.registry_schema_version,
        "entries": [_entry_record(item) for item in registry.entries],
        "parent_freeze_sha": registry.parent_freeze_sha,
    }


def _identity_tensor(size: int) -> FrozenComplexTensor:
    if type(size) is not int or size <= 0:
        raise ValueError("identity size must be positive")
    return freeze_complex_tensor(np.eye(size, dtype=np.complex128))


def _build_readout_spec(
    source_count: int,
    readout_count: int,
) -> ControlReadoutCalibrationSpec:
    provisional = ControlReadoutCalibrationSpec(
        spec_schema_version=READOUT_SPEC_SCHEMA_VERSION,
        source_metric_whitener=_identity_tensor(source_count),
        h_metric_whitener=_identity_tensor(readout_count),
        curvature_incidence_operator=_identity_tensor(readout_count),
        curvature_metric_whitener=_identity_tensor(readout_count),
        curvature_normalizer_id=CURVATURE_NORMALIZER_ID,
        spec_sha="0" * 64,
    )
    return replace(
        provisional,
        spec_sha=canonical_sha(readout_calibration_spec_payload(provisional)),
    )


def _verify_bundle(
    bundle: SyntheticControlBundle,
    expected_control_id: str,
) -> object:
    if not isinstance(bundle, SyntheticControlBundle):
        raise TypeError("controls must contain SyntheticControlBundle records")
    if bundle.control_id != expected_control_id:
        raise ValueError("controls are not in the unique closed order")
    view = _reverify_verified_factory(bundle.factory)
    if view.role != "actual":
        raise ValueError("closed control factory must have actual role")
    if bundle.target != view.target:
        raise ValueError("control target does not match factory authority")
    if bundle.construction_trace != view.trace:
        raise ValueError("control trace does not match factory authority")
    source = verify_basis_manifest(bundle.source_basis)
    readout = verify_basis_manifest(view.factory.readout_basis)
    if source.manifest_id != view.factory.source_manifest_id:
        raise ValueError("control source basis does not match factory")
    if source.state_schema_id != view.factory.state_schema_id:
        raise ValueError("control source state schema mismatch")
    if source.channel_order != view.factory.channel_order:
        raise ValueError("control source channel order mismatch")
    if readout.state_schema_id != view.factory.state_schema_id:
        raise ValueError("factory readout state schema mismatch")
    if readout.channel_order != view.factory.channel_order:
        raise ValueError("factory readout channel order mismatch")
    channel_count = len(view.factory.channel_order)
    if channel_count % 2:
        raise ValueError("synthetic control channel count must be even")
    if expected_control_id in ("full", "zero"):
        derived_mode_count = channel_count // 2
    else:
        if channel_count % 4:
            raise ValueError(
                "direct_sum channel count must contain two equal sectors"
            )
        derived_mode_count = channel_count // 4
    if bundle.mode_count != derived_mode_count:
        raise ValueError("control mode_count is not mechanically derived")
    expected_ranks = {
        "full": (derived_mode_count, derived_mode_count),
        "zero": (derived_mode_count, 0),
        "direct_sum": (2 * derived_mode_count, derived_mode_count),
    }[expected_control_id]
    if (
        bundle.expected_actual_rank,
        bundle.expected_ablated_rank,
    ) != expected_ranks:
        raise ValueError("control expected ranks are not mechanically derived")
    if len(source.vectors_wire) != expected_ranks[0]:
        raise ValueError("control source dimension does not match construction")
    if len(readout.vectors_wire) != expected_ranks[0]:
        raise ValueError("control readout dimension does not match construction")
    _verify_closed_control_operator(
        expected_control_id,
        derived_mode_count,
        view,
    )
    return view


def _verify_closed_control_operator(
    control_id: str,
    mode_count: int,
    view: object,
) -> None:
    factory = view.factory
    if control_id in ("full", "zero"):
        expected_channels = tuple(
            channel
            for mode in range(mode_count)
            for channel in (f"x.{mode:03d}", f"y.{mode:03d}")
        )
        sector_profiles = tuple(
            (mode, control_id == "zero")
            for mode in range(mode_count)
        )
    else:
        blind_channels = tuple(
            channel
            for mode in range(mode_count)
            for channel in (f"x.b.{mode:03d}", f"y.b.{mode:03d}")
        )
        conditioned_channels = tuple(
            channel
            for mode in range(mode_count, 2 * mode_count)
            for channel in (f"x.c.{mode:03d}", f"y.c.{mode:03d}")
        )
        expected_channels = blind_channels + conditioned_channels
        sector_profiles = tuple(
            (mode, False) for mode in range(mode_count)
        ) + tuple(
            (mode, True)
            for mode in range(mode_count, 2 * mode_count)
        )
    if factory.channel_order != expected_channels:
        raise ValueError("control channel_order is not the closed builder order")
    if len(factory.primitives) != 3 * len(sector_profiles):
        raise ValueError("control does not contain three shears per pair")
    coefficients = ((1.0, 0.0), (-1.0, 0.0), (1.0, 0.0))
    for local_pair, (global_pair, conditioned) in enumerate(sector_profiles):
        first = expected_channels[2 * local_pair]
        second = expected_channels[2 * local_pair + 1]
        sources = (first, second, first)
        destinations = (second, first, second)
        for layer in range(3):
            index = 3 * local_pair + layer
            primitive = factory.primitives[index]
            traced = view.trace.primitives[index]
            if (
                primitive.mechanism_id
                != f"pair.{global_pair:03d}.shear.{layer}"
                or primitive.layer_slot_id
                != f"layer.{global_pair:03d}.{layer}"
                or primitive.operation_id != "local_canonical_shear"
                or primitive.source_channel != sources[layer]
                or primitive.destination_channel != destinations[layer]
                or primitive.offset != (0,) * factory.spatial_ndim
                or primitive.coefficient_wire != coefficients[layer]
            ):
                raise ValueError("control primitive is not the closed builder")
            expected_production = (
                "target_operator"
                if conditioned
                else "local_canonical_shear"
            )
            expected_kind = (
                MechanismKind.TARGET_CONDITIONED
                if conditioned
                else MechanismKind.TARGET_BLIND
            )
            if (
                primitive.production_id != expected_production
                or traced.production_id != expected_production
                or traced.kind is not expected_kind
            ):
                raise ValueError("control provenance sector is not closed")


def _expected_registry(
    controls: tuple[SyntheticControlBundle, ...],
    parent: VerifiedParentFreeze,
) -> ClosedControlRegistry:
    if type(controls) is not tuple:
        raise TypeError("controls must be a tuple")
    if len(controls) != len(CONTROL_ORDER):
        raise ValueError("closed registry requires exactly three controls")
    parent_manifest = _reverify_verified_parent_freeze(parent)
    entries: list[ControlRegistryEntry] = []
    for bundle, control_id in zip(controls, CONTROL_ORDER):
        view = _verify_bundle(bundle, control_id)
        readout = view.factory.readout_basis
        source_count = len(bundle.source_basis.vectors_wire)
        readout_count = len(readout.vectors_wire)
        spec = _build_readout_spec(source_count, readout_count)
        provisional = ControlRegistryEntry(
            entry_schema_version=CONTROL_ENTRY_SCHEMA_VERSION,
            control_id=control_id,  # type: ignore[arg-type]
            builder_id=_BUILDERS[control_id],
            factory_sha=view.factory.factory_sha,
            source_basis=bundle.source_basis,
            readout_basis=readout,
            readout_calibration_spec=spec,
            mode_count=bundle.mode_count,
            expected_h_actual_rank=bundle.expected_actual_rank,
            expected_h_ablated_rank=bundle.expected_ablated_rank,
            expected_curv_actual_rank=bundle.expected_actual_rank,
            expected_curv_ablated_rank=bundle.expected_ablated_rank,
            parent_freeze_sha=parent_manifest.parent_freeze_sha,
            entry_sha="0" * 64,
        )
        entries.append(
            replace(
                provisional,
                entry_sha=canonical_sha(
                    control_registry_entry_payload(provisional)
                ),
            )
        )
    provisional_registry = ClosedControlRegistry(
        registry_schema_version=CONTROL_REGISTRY_SCHEMA_VERSION,
        entries=tuple(entries),
        parent_freeze_sha=parent_manifest.parent_freeze_sha,
        registry_sha="0" * 64,
    )
    return replace(
        provisional_registry,
        registry_sha=canonical_sha(
            closed_control_registry_payload(provisional_registry)
        ),
    )


class VerifiedControlRegistry:
    """Opaque live authority for the unique three-control registry."""

    __slots__ = ("__registry", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        registry: ClosedControlRegistry,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError(
                "VerifiedControlRegistry can only be issued by this module"
            )
        object.__setattr__(
            self,
            "_VerifiedControlRegistry__registry",
            registry,
        )
        object.__setattr__(
            self,
            "_VerifiedControlRegistry__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedControlRegistry__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedControlRegistry is immutable")

    @property
    def registry(self) -> ClosedControlRegistry:
        return self.__registry


@dataclass(frozen=True)
class _VerifiedRegistryView:
    registry: ClosedControlRegistry
    controls: tuple[SyntheticControlBundle, ...]
    parent: VerifiedParentFreeze


@dataclass(frozen=True)
class _RegistryAuthority:
    registry: ClosedControlRegistry
    controls: tuple[SyntheticControlBundle, ...]
    parent: VerifiedParentFreeze
    seal: str


def _registry_seal(
    registry: ClosedControlRegistry,
    controls: tuple[SyntheticControlBundle, ...],
    parent: VerifiedParentFreeze,
) -> str:
    expected = _expected_registry(controls, parent)
    if registry.registry_sha != expected.registry_sha:
        raise ValueError("registry does not match closed reconstruction")
    return canonical_sha(
        {
            "authority_schema_version": "v3m0.verified-control-registry.v1",
            "registry": {
                **closed_control_registry_payload(registry),
                "registry_sha": registry.registry_sha,
            },
            "factory_shas": [
                _reverify_verified_factory(item.factory).factory.factory_sha
                for item in controls
            ],
            "parent_freeze_sha": _reverify_verified_parent_freeze(
                parent
            ).parent_freeze_sha,
        }
    )


def _make_registry_authority() -> tuple[
    Callable[..., VerifiedControlRegistry],
    Callable[[VerifiedControlRegistry], _VerifiedRegistryView],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedControlRegistry],
            _RegistryAuthority,
        ],
    ] = {}
    lock = threading.RLock()

    def issue(
        registry: ClosedControlRegistry,
        controls: tuple[SyntheticControlBundle, ...],
        parent: VerifiedParentFreeze,
    ) -> VerifiedControlRegistry:
        seal = _registry_seal(registry, controls, parent)
        authority = _RegistryAuthority(
            registry=registry,
            controls=controls,
            parent=parent,
            seal=seal,
        )
        wrapper = VerifiedControlRegistry(_ISSUANCE_TOKEN, registry, seal)
        identity = id(wrapper)

        def remove(
            reference: weakref.ReferenceType[VerifiedControlRegistry],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        return wrapper

    def reverify(
        wrapper: VerifiedControlRegistry,
    ) -> _VerifiedRegistryView:
        if type(wrapper) is not VerifiedControlRegistry:
            raise TypeError(
                "runtime requires a module-issued VerifiedControlRegistry"
            )
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError(
                    "VerifiedControlRegistry identity is not live"
                )
            authority = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedControlRegistry__token",
            )
            raw = object.__getattribute__(
                wrapper,
                "_VerifiedControlRegistry__registry",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedControlRegistry__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "VerifiedControlRegistry authority record is incomplete"
            ) from exc
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("VerifiedControlRegistry token mismatch")
        expected_seal = _registry_seal(
            authority.registry,
            authority.controls,
            authority.parent,
        )
        if (
            raw != authority.registry
            or seal != authority.seal
            or seal != expected_seal
        ):
            raise ValueError("VerifiedControlRegistry immutable seal mismatch")
        return _VerifiedRegistryView(
            registry=authority.registry,
            controls=authority.controls,
            parent=authority.parent,
        )

    return issue, reverify


(
    _issue_verified_control_registry,
    _reverify_verified_control_registry,
) = _make_registry_authority()


def build_closed_control_registry(
    controls: tuple[SyntheticControlBundle, ...],
    parent: VerifiedParentFreeze,
) -> VerifiedControlRegistry:
    """Build the unique ordered registry; there is no append API."""

    expected = _expected_registry(controls, parent)
    return _issue_verified_control_registry(expected, controls, parent)


def verify_closed_control_registry(
    registry: ClosedControlRegistry,
    controls: tuple[SyntheticControlBundle, ...],
    parent: VerifiedParentFreeze,
) -> VerifiedControlRegistry:
    """Hydrate a raw registry only by replaying all three live controls."""

    if not isinstance(registry, ClosedControlRegistry):
        raise TypeError("registry must be a ClosedControlRegistry")
    expected = _expected_registry(controls, parent)
    if registry.registry_sha != expected.registry_sha:
        raise ValueError("registry does not match closed reconstruction")
    if registry.registry_sha != canonical_sha(
        closed_control_registry_payload(registry)
    ):
        raise ValueError("registry_sha does not match complete body")
    return _issue_verified_control_registry(registry, controls, parent)


__all__ = [
    "CONTROL_ENTRY_SCHEMA_VERSION",
    "CONTROL_ORDER",
    "CONTROL_REGISTRY_SCHEMA_VERSION",
    "CURVATURE_NORMALIZER_ID",
    "READOUT_SPEC_SCHEMA_VERSION",
    "ClosedControlRegistry",
    "ControlReadoutCalibrationSpec",
    "ControlRegistryEntry",
    "VerifiedControlRegistry",
    "build_closed_control_registry",
    "closed_control_registry_payload",
    "control_registry_entry_payload",
    "readout_calibration_spec_payload",
    "verify_closed_control_registry",
]
