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
from types import FunctionType
from typing import Callable, Literal

import numpy as np

from .controls import CONTROL_SCHEMA_VERSION, SyntheticControlBundle
from .evidence import _make_exact_wire_cloner, canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    FrozenSyntheticTarget,
    LinearRealspaceFactory,
    VerifiedFactory,
    _reverify_verified_factory,
    basis_manifest_payload,
    freeze_complex_tensor,
    frozen_tensor_payload,
    verify_basis_manifest,
)
from .parent_freeze import (
    ParentFreezeManifest,
    VerifiedParentFreeze,
    _reverify_verified_parent_freeze,
)
from .replay_scope import (
    _cached_replay_is_valid,
    _record_successful_replay,
)
from .trace import ConstructionTrace, MechanismKind


READOUT_SPEC_SCHEMA_VERSION = "v3m0.control-readout-calibration-spec.v1"
CONTROL_ENTRY_SCHEMA_VERSION = "v3m0.control-registry-entry.v1"
CONTROL_REGISTRY_SCHEMA_VERSION = "v3m0.closed-control-registry.v1"
CURVATURE_NORMALIZER_ID: Literal["synthetic-identity-v1"] = "synthetic-identity-v1"
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
            raise TypeError("readout_calibration_spec has the wrong record type")
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


_REGISTRY_WIRE_TYPES = (
    ClosedControlRegistry,
    ControlRegistryEntry,
    ControlReadoutCalibrationSpec,
    BasisManifest,
    FrozenComplexTensor,
)
_clone_registry_wire = _make_exact_wire_cloner(_REGISTRY_WIRE_TYPES)


def _require_exact_control_bundle(
    control: object,
    expected_control_id: str,
    *,
    _control_type=SyntheticControlBundle,
    _target_type=FrozenSyntheticTarget,
    _trace_type=ConstructionTrace,
    _factory_type=VerifiedFactory,
    _basis_type=BasisManifest,
    _schema_version=CONTROL_SCHEMA_VERSION,
    _type=type,
    _vars=vars,
    _frozenset=frozenset,
    _sorted=sorted,
    _str_type=str,
    _int_type=int,
    _type_error=TypeError,
    _value_error=ValueError,
) -> SyntheticControlBundle:
    """Close the complete top-level control wire before authority use."""

    if _type(control) is not _control_type:
        raise _type_error("control dependency must be an exact SyntheticControlBundle")
    expected_fields = _frozenset(_control_type.__dataclass_fields__)
    observed_fields = _frozenset(_vars(control))
    if observed_fields != expected_fields:
        raise _value_error(
            "control dependency fields are not exact: "
            f"missing={_sorted(expected_fields - observed_fields)!r}, "
            f"unknown={_sorted(observed_fields - expected_fields)!r}"
        )
    if control.control_schema_version != _schema_version:
        raise _value_error("control_schema_version is not closed")
    if _type(control.control_schema_version) is not _str_type:
        raise _type_error("control_schema_version must be an exact string")
    if (
        _type(control.control_id) is not _str_type
        or control.control_id != expected_control_id
    ):
        raise _value_error("control_id is not in the closed position")
    if _type(control.mode_count) is not _int_type or control.mode_count <= 0:
        raise _value_error("control mode_count must be a positive exact int")
    if _type(control.target) is not _target_type:
        raise _type_error("control target has the wrong exact type")
    if _type(control.construction_trace) is not _trace_type:
        raise _type_error("control construction_trace has the wrong exact type")
    if _type(control.factory) is not _factory_type:
        raise _type_error("control factory has the wrong exact type")
    if _type(control.source_basis) is not _basis_type:
        raise _type_error("control source_basis has the wrong exact type")
    for field in ("expected_actual_rank", "expected_ablated_rank"):
        value = getattr(control, field)
        if _type(value) is not _int_type or value < 0:
            raise _value_error(f"control {field} must be a non-negative exact int")
    return control


def _require_exact_registry_schema(
    registry: object,
    *,
    _allowed_types: tuple[type[object], ...] = _REGISTRY_WIRE_TYPES,
    _type=type,
    _tuple_type=tuple,
    _list_type=list,
    _dict_type=dict,
    _vars=vars,
    _getattr=getattr,
    _frozenset=frozenset,
    _sorted=sorted,
    _type_error=TypeError,
    _value_error=ValueError,
) -> ClosedControlRegistry:
    """Reject subclasses and unknown fields throughout the raw registry."""

    if _type(registry) is not ClosedControlRegistry:
        raise _type_error("registry must be an exact ClosedControlRegistry record")
    pending: list[tuple[object, str]] = _list_type(((registry, "registry"),))
    while pending:
        value, field = pending.pop()
        value_type = _type(value)
        if value_type in _allowed_types:
            expected = _frozenset(value_type.__dataclass_fields__)
            try:
                observed = _frozenset(_vars(value))
            except _type_error as exc:
                raise _type_error(f"{field} has no exact record body") from exc
            if observed != expected:
                raise _value_error(
                    f"{field} fields are not exact: "
                    f"missing={_sorted(expected - observed)!r}, "
                    f"unknown={_sorted(observed - expected)!r}"
                )
            for name in value_type.__dataclass_fields__:
                pending.append((_getattr(value, name), f"{field}.{name}"))
        elif hasattr(value_type, "__dataclass_fields__"):
            raise _type_error(f"{field} has a non-exact registry record type")
        elif value_type is _tuple_type or value_type is _list_type:
            for index, item in enumerate(value):
                pending.append((item, f"{field}[{index}]"))
        elif value_type is _dict_type:
            for key, item in value.items():
                pending.append((item, f"{field}[{key!r}]"))
    return registry


def readout_calibration_spec_payload(
    spec: ControlReadoutCalibrationSpec,
) -> dict[str, object]:
    if not isinstance(spec, ControlReadoutCalibrationSpec):
        raise TypeError("spec must be a ControlReadoutCalibrationSpec")
    return {
        "spec_schema_version": spec.spec_schema_version,
        "source_metric_whitener": _tensor_record(spec.source_metric_whitener),
        "h_metric_whitener": _tensor_record(spec.h_metric_whitener),
        "curvature_incidence_operator": _tensor_record(
            spec.curvature_incidence_operator
        ),
        "curvature_metric_whitener": _tensor_record(spec.curvature_metric_whitener),
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
    *,
    exact_control=_require_exact_control_bundle,
) -> object:
    exact_control(bundle, expected_control_id)
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
            raise ValueError("direct_sum channel count must contain two equal sectors")
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
            (mode, control_id == "zero") for mode in range(mode_count)
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
        sector_profiles = tuple((mode, False) for mode in range(mode_count)) + tuple(
            (mode, True) for mode in range(mode_count, 2 * mode_count)
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
                primitive.mechanism_id != f"pair.{global_pair:03d}.shear.{layer}"
                or primitive.layer_slot_id != f"layer.{global_pair:03d}.{layer}"
                or primitive.operation_id != "local_canonical_shear"
                or primitive.source_channel != sources[layer]
                or primitive.destination_channel != destinations[layer]
                or primitive.offset != (0,) * factory.spatial_ndim
                or primitive.coefficient_wire != coefficients[layer]
            ):
                raise ValueError("control primitive is not the closed builder")
            expected_production = (
                "target_operator" if conditioned else "local_canonical_shear"
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
                entry_sha=canonical_sha(control_registry_entry_payload(provisional)),
            )
        )
    provisional_registry = ClosedControlRegistry(
        registry_schema_version=CONTROL_REGISTRY_SCHEMA_VERSION,
        entries=tuple(entries),
        parent_freeze_sha=parent_manifest.parent_freeze_sha,
        registry_sha="0" * 64,
    )
    expected = replace(
        provisional_registry,
        registry_sha=canonical_sha(
            closed_control_registry_payload(provisional_registry)
        ),
    )
    _require_exact_registry_schema(expected)
    return expected


def _freeze_registry_authority_functions(
    *roots: FunctionType,
) -> tuple[FunctionType, ...]:
    """Detach registry reconstruction from mutable module bindings."""

    cache: dict[int, FunctionType] = {}
    module_name = __name__

    def freeze_value(value):
        if type(value) is FunctionType and value.__module__ == module_name:
            return freeze_function(value)
        if type(value) is tuple:
            return tuple(freeze_value(item) for item in value)
        if type(value) is dict:
            return {key: freeze_value(item) for key, item in value.items()}
        return value

    def freeze_function(function):
        cached = cache.get(id(function))
        if cached is not None:
            return cached
        frozen_globals = dict(function.__globals__)
        frozen = FunctionType(
            function.__code__,
            frozen_globals,
            function.__name__,
            None,
            function.__closure__,
        )
        cache[id(function)] = frozen
        for name, value in tuple(frozen_globals.items()):
            if type(value) is FunctionType and value.__module__ == module_name:
                frozen_globals[name] = freeze_function(value)
        frozen.__defaults__ = freeze_value(function.__defaults__)
        frozen.__kwdefaults__ = freeze_value(function.__kwdefaults__)
        frozen.__annotations__ = dict(function.__annotations__)
        frozen.__dict__.update(function.__dict__)
        frozen.__doc__ = function.__doc__
        frozen.__module__ = function.__module__
        frozen.__qualname__ = function.__qualname__
        return frozen

    return tuple(freeze_function(root) for root in roots)


(
    _require_exact_registry_schema,
    readout_calibration_spec_payload,
    control_registry_entry_payload,
    closed_control_registry_payload,
    _expected_registry,
) = _freeze_registry_authority_functions(
    _require_exact_registry_schema,
    readout_calibration_spec_payload,
    control_registry_entry_payload,
    closed_control_registry_payload,
    _expected_registry,
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
            raise TypeError("VerifiedControlRegistry can only be issued by this module")
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
class _ControlDependencySnapshot:
    control: SyntheticControlBundle
    target: FrozenSyntheticTarget
    construction_trace: ConstructionTrace
    factory: VerifiedFactory
    source_basis: BasisManifest
    source_basis_identity: BasisManifest
    control_schema_version: str
    control_id: str
    mode_count: int
    expected_actual_rank: int
    expected_ablated_rank: int
    factory_body: LinearRealspaceFactory
    factory_trace: ConstructionTrace
    factory_target: FrozenSyntheticTarget
    factory_role: str


@dataclass(frozen=True)
class _RegistryAuthority:
    registry: ClosedControlRegistry
    registry_snapshot: ClosedControlRegistry
    controls: tuple[SyntheticControlBundle, ...]
    parent: VerifiedParentFreeze
    control_snapshots: tuple[_ControlDependencySnapshot, ...]
    parent_snapshot: ParentFreezeManifest
    seal: str
    replay_fingerprint: str


def _registry_seal(
    registry: ClosedControlRegistry,
    controls: tuple[SyntheticControlBundle, ...],
    parent: VerifiedParentFreeze,
    *,
    expected_registry_builder=_expected_registry,
    canonical_hash=canonical_sha,
    registry_payload=closed_control_registry_payload,
    factory_reverifier=_reverify_verified_factory,
    parent_reverifier=_reverify_verified_parent_freeze,
    exact_schema=_require_exact_registry_schema,
    value_error=ValueError,
) -> str:
    exact_schema(registry)
    expected = expected_registry_builder(controls, parent)
    if registry.registry_sha != expected.registry_sha:
        raise value_error("registry does not match closed reconstruction")
    return canonical_hash(
        {
            "authority_schema_version": "v3m0.verified-control-registry.v1",
            "registry": {
                **registry_payload(registry),
                "registry_sha": registry.registry_sha,
            },
            "factory_shas": [
                factory_reverifier(item.factory).factory.factory_sha
                for item in controls
            ],
            "parent_freeze_sha": parent_reverifier(parent).parent_freeze_sha,
        }
    )


def _capture_registry_dependencies(
    controls: tuple[SyntheticControlBundle, ...],
    parent: VerifiedParentFreeze,
    *,
    factory_reverifier=_reverify_verified_factory,
    parent_reverifier=_reverify_verified_parent_freeze,
    basis_verifier=verify_basis_manifest,
    exact_control=_require_exact_control_bundle,
    clone_registry_wire=_clone_registry_wire,
    type_fn=type,
    value_error=ValueError,
) -> tuple[tuple[_ControlDependencySnapshot, ...], ParentFreezeManifest]:
    """Take issuer-private snapshots after the complete registry replay."""

    if type_fn(controls) is not tuple or len(controls) != len(CONTROL_ORDER):
        raise value_error("closed registry dependency tuple drifted")
    parent_snapshot = parent_reverifier(parent)
    snapshots = []
    for control, expected_control_id in zip(controls, CONTROL_ORDER):
        exact_control(control, expected_control_id)
        factory_view = factory_reverifier(control.factory)
        source_basis = basis_verifier(control.source_basis)
        if (
            control.control_id != expected_control_id
            or control.target != factory_view.target
            or control.construction_trace != factory_view.trace
            or factory_view.role != "actual"
        ):
            raise value_error("control dependency differs from factory authority")
        snapshots.append(
            _ControlDependencySnapshot(
                control=control,
                target=control.target,
                construction_trace=control.construction_trace,
                factory=control.factory,
                source_basis=clone_registry_wire(source_basis),
                source_basis_identity=control.source_basis,
                control_schema_version=control.control_schema_version,
                control_id=control.control_id,
                mode_count=control.mode_count,
                expected_actual_rank=control.expected_actual_rank,
                expected_ablated_rank=control.expected_ablated_rank,
                factory_body=factory_view.factory,
                factory_trace=factory_view.trace,
                factory_target=factory_view.target,
                factory_role=factory_view.role,
            )
        )
    return tuple(snapshots), parent_snapshot


def _registry_replay_fingerprint(
    registry: ClosedControlRegistry,
    control_snapshots: tuple[_ControlDependencySnapshot, ...],
    parent: VerifiedParentFreeze,
    parent_snapshot: ParentFreezeManifest,
    seal: str,
    *,
    canonical_hash=canonical_sha,
    id_fn=id,
    type_fn=type,
    value_error=ValueError,
) -> str:
    if type_fn(control_snapshots) is not tuple or len(control_snapshots) != len(
        CONTROL_ORDER
    ):
        raise value_error("control dependency snapshots drifted")
    dependencies = []
    for snapshot, expected_control_id in zip(control_snapshots, CONTROL_ORDER):
        if type_fn(snapshot) is not _ControlDependencySnapshot:
            raise TypeError("control dependency snapshot has the wrong exact type")
        dependencies.append(
            {
                "control_identity": id_fn(snapshot.control),
                "target_identity": id_fn(snapshot.target),
                "trace_identity": id_fn(snapshot.construction_trace),
                "factory_identity": id_fn(snapshot.factory),
                "source_basis_identity": id_fn(snapshot.source_basis_identity),
                "control_schema_version": snapshot.control_schema_version,
                "control_id": snapshot.control_id,
                "expected_control_id": expected_control_id,
                "mode_count": snapshot.mode_count,
                "expected_actual_rank": snapshot.expected_actual_rank,
                "expected_ablated_rank": snapshot.expected_ablated_rank,
                "source_manifest_id": snapshot.source_basis.manifest_id,
                "factory_sha": snapshot.factory_body.factory_sha,
                "factory_trace_sha": snapshot.factory_trace.trace_sha,
                "factory_target_sha": snapshot.factory_target.target_spec_sha,
                "factory_role": snapshot.factory_role,
            }
        )
    return canonical_hash(
        {
            "replay_schema_version": "v3m0.verified-control-registry-replay.v1",
            "registry_sha": registry.registry_sha,
            "registry_seal": seal,
            "parent_identity": id_fn(parent),
            "parent_freeze_sha": parent_snapshot.parent_freeze_sha,
            "dependencies": dependencies,
        }
    )


def _validate_registry_dependency_snapshots(
    authority: _RegistryAuthority,
    *,
    replay_dependencies: bool,
    factory_reverifier=_reverify_verified_factory,
    parent_reverifier=_reverify_verified_parent_freeze,
    basis_verifier=verify_basis_manifest,
    exact_control=_require_exact_control_bundle,
    fingerprint_builder=_registry_replay_fingerprint,
    type_fn=type,
    str_type=str,
    int_type=int,
    value_error=ValueError,
) -> None:
    if type_fn(authority.controls) is not tuple or len(authority.controls) != len(
        CONTROL_ORDER
    ):
        raise value_error("registry control dependencies drifted")
    if type_fn(authority.control_snapshots) is not tuple or len(
        authority.control_snapshots
    ) != len(CONTROL_ORDER):
        raise value_error("registry control snapshots drifted")
    observed_fingerprint = fingerprint_builder(
        authority.registry_snapshot,
        authority.control_snapshots,
        authority.parent,
        authority.parent_snapshot,
        authority.seal,
    )
    if observed_fingerprint != authority.replay_fingerprint:
        raise value_error("registry dependency snapshot fingerprint mismatch")

    if replay_dependencies:
        parent_snapshot = parent_reverifier(authority.parent)
    else:
        parent_snapshot = authority.parent_snapshot
    if parent_snapshot != authority.parent_snapshot:
        raise value_error("registry parent dependency snapshot mismatch")

    for index, (control, snapshot, entry, expected_control_id) in enumerate(
        zip(
            authority.controls,
            authority.control_snapshots,
            authority.registry_snapshot.entries,
            CONTROL_ORDER,
        )
    ):
        exact_control(control, expected_control_id)
        if control is not snapshot.control:
            raise value_error("registry control dependency identity mismatch")
        if (
            control.target is not snapshot.target
            or control.construction_trace is not snapshot.construction_trace
            or control.factory is not snapshot.factory
            or control.source_basis is not snapshot.source_basis_identity
            or type_fn(control.control_schema_version) is not str_type
            or type_fn(control.control_id) is not str_type
            or type_fn(control.mode_count) is not int_type
            or type_fn(control.expected_actual_rank) is not int_type
            or type_fn(control.expected_ablated_rank) is not int_type
            or control.control_schema_version != snapshot.control_schema_version
            or control.control_id != snapshot.control_id
            or control.control_id != expected_control_id
            or control.mode_count != snapshot.mode_count
            or control.expected_actual_rank != snapshot.expected_actual_rank
            or control.expected_ablated_rank != snapshot.expected_ablated_rank
            or control.target != snapshot.factory_target
            or control.construction_trace != snapshot.factory_trace
        ):
            raise value_error("registry control dependency snapshot mismatch")
        source_basis = basis_verifier(control.source_basis)
        if source_basis != snapshot.source_basis:
            raise value_error("registry source-basis dependency snapshot mismatch")
        if replay_dependencies:
            factory_view = factory_reverifier(control.factory)
            if (
                factory_view.factory != snapshot.factory_body
                or factory_view.trace != snapshot.factory_trace
                or factory_view.target != snapshot.factory_target
                or factory_view.role != snapshot.factory_role
            ):
                raise value_error("registry factory dependency snapshot mismatch")
        else:
            factory_view = snapshot
        factory_body = (
            factory_view.factory if replay_dependencies else snapshot.factory_body
        )
        factory_role = (
            factory_view.role if replay_dependencies else snapshot.factory_role
        )
        if (
            factory_role != "actual"
            or entry.control_id != expected_control_id
            or entry.factory_sha != factory_body.factory_sha
            or entry.source_basis != source_basis
            or entry.readout_basis != factory_body.readout_basis
            or entry.mode_count != control.mode_count
            or entry.expected_h_actual_rank != control.expected_actual_rank
            or entry.expected_h_ablated_rank != control.expected_ablated_rank
            or entry.expected_curv_actual_rank != control.expected_actual_rank
            or entry.expected_curv_ablated_rank != control.expected_ablated_rank
            or entry.parent_freeze_sha != parent_snapshot.parent_freeze_sha
        ):
            raise value_error("registry dependency binding mismatch")


(
    _capture_registry_dependencies,
    _registry_replay_fingerprint,
    _validate_registry_dependency_snapshots,
) = _freeze_registry_authority_functions(
    _capture_registry_dependencies,
    _registry_replay_fingerprint,
    _validate_registry_dependency_snapshots,
)


def _make_registry_authority(
    *,
    seal_builder=_registry_seal,
    dependency_snapshot_builder=_capture_registry_dependencies,
    dependency_snapshot_validator=_validate_registry_dependency_snapshots,
    replay_fingerprint_builder=_registry_replay_fingerprint,
    authority_type=_RegistryAuthority,
    wrapper_type=VerifiedControlRegistry,
    view_type=_VerifiedRegistryView,
    issuance_token=_ISSUANCE_TOKEN,
    weak_reference=weakref.ref,
    lock_builder=threading.RLock,
    exact_schema=_require_exact_registry_schema,
    clone=_clone_registry_wire,
    type_fn=type,
    id_fn=id,
    object_type=object,
    type_error=TypeError,
    value_error=ValueError,
    attribute_error=AttributeError,
    canonical_hash=canonical_sha,
    registry_payload=closed_control_registry_payload,
    cached_replay_is_valid=_cached_replay_is_valid,
    record_successful_replay=_record_successful_replay,
) -> tuple[
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
    lock = lock_builder()

    def issue(
        registry: ClosedControlRegistry,
        controls: tuple[SyntheticControlBundle, ...],
        parent: VerifiedParentFreeze,
    ) -> VerifiedControlRegistry:
        exact_schema(registry)
        exposed = clone(registry)
        snapshot = clone(registry)
        exact_schema(exposed)
        exact_schema(snapshot)
        seal = seal_builder(snapshot, controls, parent)
        control_snapshots, parent_snapshot = dependency_snapshot_builder(
            controls,
            parent,
        )
        replay_fingerprint = replay_fingerprint_builder(
            snapshot,
            control_snapshots,
            parent,
            parent_snapshot,
            seal,
        )
        authority = authority_type(
            registry=exposed,
            registry_snapshot=snapshot,
            controls=controls,
            parent=parent,
            control_snapshots=control_snapshots,
            parent_snapshot=parent_snapshot,
            seal=seal,
            replay_fingerprint=replay_fingerprint,
        )
        wrapper = wrapper_type(issuance_token, exposed, seal)
        identity = id_fn(wrapper)

        def remove(
            reference: weakref.ReferenceType[VerifiedControlRegistry],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weak_reference(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        record_successful_replay(
            namespace="rulespace_v3.registry.VerifiedControlRegistry",
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=issuance_token,
            exposed_bodies=(exposed,),
            seal=seal,
            authority=authority,
            authority_digest=replay_fingerprint,
        )
        return wrapper

    def reverify(
        wrapper: VerifiedControlRegistry,
    ) -> _VerifiedRegistryView:
        if type_fn(wrapper) is not wrapper_type:
            raise type_error("runtime requires a module-issued VerifiedControlRegistry")
        with lock:
            current = live.get(id_fn(wrapper))
            if current is None or current[0]() is not wrapper:
                raise value_error("VerifiedControlRegistry identity is not live")
            authority = current[1]
        try:
            token = object_type.__getattribute__(
                wrapper,
                "_VerifiedControlRegistry__token",
            )
            raw = object_type.__getattribute__(
                wrapper,
                "_VerifiedControlRegistry__registry",
            )
            seal = object_type.__getattribute__(
                wrapper,
                "_VerifiedControlRegistry__seal",
            )
        except attribute_error as exc:
            raise value_error(
                "VerifiedControlRegistry authority record is incomplete"
            ) from exc
        if token is not issuance_token:
            raise value_error("VerifiedControlRegistry token mismatch")
        namespace = "rulespace_v3.registry.VerifiedControlRegistry"

        def validate_registry_body() -> None:
            exact_schema(raw)
            exact_schema(authority.registry)
            exact_schema(authority.registry_snapshot)
            raw_snapshot = clone(raw)
            exposed_snapshot = clone(authority.registry)
            closed_snapshot = clone(authority.registry_snapshot)
            if (
                raw is not authority.registry
                or raw_snapshot != exposed_snapshot
                or raw_snapshot != closed_snapshot
                or raw.registry_sha != canonical_hash(registry_payload(raw))
                or seal != authority.seal
            ):
                raise value_error("VerifiedControlRegistry immutable seal mismatch")

        def cheap_validator() -> None:
            validate_registry_body()
            dependency_snapshot_validator(
                authority,
                replay_dependencies=True,
            )

        def verified_view() -> _VerifiedRegistryView:
            return view_type(
                registry=clone(authority.registry_snapshot),
                controls=authority.controls,
                parent=authority.parent,
            )

        if cached_replay_is_valid(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=token,
            exposed_bodies=(raw,),
            seal=seal,
            authority=authority,
            authority_digest=authority.replay_fingerprint,
            cheap_validator=cheap_validator,
        ):
            return verified_view()
        validate_registry_body()
        expected_seal = seal_builder(
            authority.registry_snapshot,
            authority.controls,
            authority.parent,
        )
        dependency_snapshot_validator(
            authority,
            replay_dependencies=False,
        )
        if (
            seal != expected_seal
        ):
            raise value_error("VerifiedControlRegistry immutable seal mismatch")
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=token,
            exposed_bodies=(raw,),
            seal=seal,
            authority=authority,
            authority_digest=authority.replay_fingerprint,
        )
        return verified_view()

    return issue, reverify


(
    _issue_verified_control_registry,
    _reverify_verified_control_registry,
) = _make_registry_authority()


def build_closed_control_registry(
    controls: tuple[SyntheticControlBundle, ...],
    parent: VerifiedParentFreeze,
    *,
    _expected_builder=_expected_registry,
    _issuer=_issue_verified_control_registry,
) -> VerifiedControlRegistry:
    """Build the unique ordered registry; there is no append API."""

    expected = _expected_builder(controls, parent)
    return _issuer(expected, controls, parent)


def verify_closed_control_registry(
    registry: ClosedControlRegistry,
    controls: tuple[SyntheticControlBundle, ...],
    parent: VerifiedParentFreeze,
    *,
    _registry_type=ClosedControlRegistry,
    _exact_schema=_require_exact_registry_schema,
    _expected_builder=_expected_registry,
    _canonical_hash=canonical_sha,
    _registry_payload=closed_control_registry_payload,
    _issuer=_issue_verified_control_registry,
    _type=type,
    _type_error=TypeError,
    _value_error=ValueError,
) -> VerifiedControlRegistry:
    """Hydrate a raw registry only by replaying all three live controls."""

    if _type(registry) is not _registry_type:
        raise _type_error("registry must be an exact ClosedControlRegistry record")
    _exact_schema(registry)
    expected = _expected_builder(controls, parent)
    if registry.registry_sha != expected.registry_sha:
        raise _value_error("registry does not match closed reconstruction")
    if registry.registry_sha != _canonical_hash(_registry_payload(registry)):
        raise _value_error("registry_sha does not match complete body")
    return _issuer(registry, controls, parent)


def _make_registry_property(
    reverify=_reverify_verified_control_registry,
):
    def registry_property(
        wrapper: VerifiedControlRegistry,
    ) -> ClosedControlRegistry:
        return reverify(wrapper).registry

    return registry_property


setattr(
    VerifiedControlRegistry,
    "registry",
    property(_make_registry_property()),
)


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
