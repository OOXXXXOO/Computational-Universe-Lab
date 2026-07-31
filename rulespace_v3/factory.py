"""Immutable synthetic real-space factories for the V3-M0 instrument.

The public dataclasses in this module are inert wire records.  Runtime entry
points accept only :class:`VerifiedFactory`, an opaque wrapper issued after the
construction trace, target, coefficient sidecars, operator wire, and every
self-hash have been revalidated.
"""

from __future__ import annotations

import math
import re
import struct
import threading
import weakref
from dataclasses import dataclass, replace
from functools import reduce
from operator import mul
from typing import Callable, Literal, Optional, Sequence

import numpy as np

from .evidence import canonical_sha
from .trace import (
    ConstructionTrace,
    MechanismKind,
    construction_trace_payload,
    evaluate_closed_coefficient,
    verify_construction_trace,
)


ComplexWire = tuple[float, float]

BASIS_SCHEMA_VERSION = "v3m0.basis-manifest.v1"
TENSOR_SCHEMA_VERSION = "v3m0.frozen-complex-tensor.v1"
FACTORY_SCHEMA_VERSION = "v3m0.linear-realspace-factory.v1"
PRIMITIVE_SCHEMA_VERSION = "v3m0.local-linear-primitive.v1"
CALIBRATION_SCHEMA_VERSION = "v3m0.calibration-seed.v1"
OBSERVATION_SCHEMA_VERSION = "v3m0.calibration-observation.v1"
TARGET_SCHEMA_VERSION = "v3m0.synthetic-target.v1"
PERIODIC_BOUNDARY_ID = "periodic-v1"
NEUTRAL_IDENTITY_ID = "neutral-identity-v1"
FACTORY_SUPPORT_MAX_MACRO_STEPS = 16_384
FACTORY_SUPPORT_MAX_CARDINALITY = 100_000
FACTORY_SUPPORT_MAX_ALLOCATION_PRODUCT = 1_000_000

_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ACTUAL_OPERATION: Literal["local_canonical_shear"] = "local_canonical_shear"
_NEUTRAL_OPERATION: Literal["neutral_identity"] = "neutral_identity"
_BLIND_SEED_PRODUCTIONS = frozenset(("local_canonical_shear",))
_ISSUANCE_TOKEN = object()


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    text = _text(value, field)
    if _LOWER_SHA.fullmatch(text) is None:
        raise ValueError(
            f"{field} must be a 64-digit lowercase hexadecimal SHA"
        )
    return text


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _finite_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _strings(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    result = tuple(_text(item, f"{field}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise ValueError(f"{field} must not contain duplicates")
    return result


def _shape(value: object, field: str) -> tuple[int, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return tuple(
        _positive_int(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    )


def _offset(
    value: object,
    field: str,
    *,
    ndim: Optional[int] = None,
) -> tuple[int, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    if ndim is not None and len(value) != ndim:
        raise ValueError(f"{field} dimension does not match spatial_ndim")
    result = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise TypeError(f"{field}[{index}] must be an int")
        result.append(item)
    return tuple(result)


def _support(
    value: object,
    field: str,
    *,
    ndim: Optional[int] = None,
) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    result = tuple(
        _offset(item, f"{field}[{index}]", ndim=ndim)
        for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise ValueError(f"{field} must not contain duplicates")
    if result != tuple(sorted(result)):
        raise ValueError(f"{field} must be lexicographically canonical")
    return result


def _complex_wire(value: object, field: str) -> ComplexWire:
    if type(value) is not tuple or len(value) != 2:
        raise TypeError(f"{field} must be a (real, imag) tuple")
    return (
        _finite_float(value[0], f"{field}[0]"),
        _finite_float(value[1], f"{field}[1]"),
    )


def _wire_from_complex(value: complex) -> ComplexWire:
    result = (float(value.real), float(value.imag))
    _complex_wire(result, "coefficient_wire")
    return result


def _wire_record(value: ComplexWire) -> list[float]:
    return [value[0], value[1]]


def _wire_equal(left: ComplexWire, right: ComplexWire) -> bool:
    return all(
        struct.pack(">d", first) == struct.pack(">d", second)
        for first, second in zip(left, right)
    )


def _wire_is_zero(value: ComplexWire) -> bool:
    return value[0] == 0.0 and value[1] == 0.0


def _interface_record(interface: "PrimitiveInterface") -> dict[str, object]:
    _verify_interface(interface)
    return {
        "interface_id": interface.interface_id,
        "state_schema_id": interface.state_schema_id,
        "spatial_ndim": interface.spatial_ndim,
        "channel_order": list(interface.channel_order),
        "dtype": interface.dtype,
        "backend": interface.backend,
    }


@dataclass(frozen=True)
class BasisManifest:
    basis_schema_version: str
    role: Literal["source", "holdout_source", "readout"]
    state_schema_id: str
    channel_order: tuple[str, ...]
    vectors_wire: tuple[tuple[ComplexWire, ...], ...]
    manifest_id: str

    def __post_init__(self) -> None:
        _text(self.basis_schema_version, "basis_schema_version")
        if self.role not in ("source", "holdout_source", "readout"):
            raise ValueError("role is not a frozen basis role")
        _text(self.state_schema_id, "state_schema_id")
        channels = _strings(self.channel_order, "channel_order")
        if not channels:
            raise ValueError("channel_order must be non-empty")
        if type(self.vectors_wire) is not tuple or not self.vectors_wire:
            raise ValueError("vectors_wire must be a non-empty tuple")
        for row_index, row in enumerate(self.vectors_wire):
            if type(row) is not tuple:
                raise TypeError(f"vectors_wire[{row_index}] must be a tuple")
            if len(row) != len(channels):
                raise ValueError(
                    "vectors_wire must have shape (n_vector,n_channel)"
                )
            for column_index, wire in enumerate(row):
                _complex_wire(
                    wire,
                    f"vectors_wire[{row_index}][{column_index}]",
                )
        _sha(self.manifest_id, "manifest_id")


@dataclass(frozen=True)
class FrozenComplexTensor:
    tensor_schema_version: str
    shape: tuple[int, ...]
    values_wire: tuple[ComplexWire, ...]
    tensor_sha: str

    def __post_init__(self) -> None:
        _text(self.tensor_schema_version, "tensor_schema_version")
        shape = _shape(self.shape, "shape")
        if type(self.values_wire) is not tuple:
            raise TypeError("values_wire must be a tuple")
        if reduce(mul, shape, 1) != len(self.values_wire):
            raise ValueError("values_wire length must equal prod(shape)")
        for index, wire in enumerate(self.values_wire):
            _complex_wire(wire, f"values_wire[{index}]")
        _sha(self.tensor_sha, "tensor_sha")


@dataclass(frozen=True)
class PrimitiveInterface:
    interface_id: str
    state_schema_id: str
    spatial_ndim: int
    channel_order: tuple[str, ...]
    dtype: Literal["complex128"]
    backend: Literal["numpy"]

    def __post_init__(self) -> None:
        _verify_interface(self)


@dataclass(frozen=True)
class Primitive:
    primitive_schema_version: str
    mechanism_id: str
    production_id: str
    layer_slot_id: str
    operation_id: Literal["local_canonical_shear", "neutral_identity"]
    interface_id: str
    source_channel: str
    destination_channel: str
    offset: tuple[int, ...]
    support_offsets: tuple[tuple[int, ...], ...]
    coefficient_wire: ComplexWire
    coefficient_digest: str
    neutral_identity_id: Optional[str]

    def __post_init__(self) -> None:
        _text(self.primitive_schema_version, "primitive_schema_version")
        _text(self.mechanism_id, "mechanism_id")
        _text(self.production_id, "production_id")
        _text(self.layer_slot_id, "layer_slot_id")
        if self.operation_id not in (_ACTUAL_OPERATION, _NEUTRAL_OPERATION):
            raise ValueError("operation_id is not a frozen primitive operation")
        _text(self.interface_id, "interface_id")
        _text(self.source_channel, "source_channel")
        _text(self.destination_channel, "destination_channel")
        offset = _offset(self.offset, "offset")
        _support(self.support_offsets, "support_offsets", ndim=len(offset))
        _complex_wire(self.coefficient_wire, "coefficient_wire")
        _sha(self.coefficient_digest, "coefficient_digest")
        if self.neutral_identity_id is not None:
            _text(self.neutral_identity_id, "neutral_identity_id")


@dataclass(frozen=True)
class LinearRealspaceFactory:
    factory_schema_version: str
    factory_role: Literal["actual", "matched_ablated"]
    factory_id: str
    construction_trace_sha: str
    grammar_id: str
    target_spec_id: str
    target_spec_sha: str
    runtime_operator_sha: str
    interface: PrimitiveInterface
    state_schema_id: str
    spatial_ndim: int
    channel_order: tuple[str, ...]
    state_shape: tuple[int, ...]
    dtype: str
    backend: str
    dt: float
    target_blind_parameters: tuple[tuple[str, float], ...]
    layer_slot_ids: tuple[str, ...]
    source_manifest_id: str
    readout_basis: BasisManifest
    boundary_manifest_id: str
    run_length: int
    primitives: tuple[Primitive, ...]
    factory_sha: str

    def __post_init__(self) -> None:
        _text(self.factory_schema_version, "factory_schema_version")
        if self.factory_role not in ("actual", "matched_ablated"):
            raise ValueError("factory_role is not frozen")
        _text(self.factory_id, "factory_id")
        _sha(self.construction_trace_sha, "construction_trace_sha")
        _text(self.grammar_id, "grammar_id")
        _text(self.target_spec_id, "target_spec_id")
        _sha(self.target_spec_sha, "target_spec_sha")
        _sha(self.runtime_operator_sha, "runtime_operator_sha")
        if not isinstance(self.interface, PrimitiveInterface):
            raise TypeError("interface must be a PrimitiveInterface")
        _text(self.state_schema_id, "state_schema_id")
        _positive_int(self.spatial_ndim, "spatial_ndim")
        _strings(self.channel_order, "channel_order")
        _shape(self.state_shape, "state_shape")
        _text(self.dtype, "dtype")
        _text(self.backend, "backend")
        _finite_float(self.dt, "dt")
        _blind_parameters(self.target_blind_parameters)
        slots = _strings(self.layer_slot_ids, "layer_slot_ids")
        _sha(self.source_manifest_id, "source_manifest_id")
        if not isinstance(self.readout_basis, BasisManifest):
            raise TypeError("readout_basis must be a BasisManifest")
        _text(self.boundary_manifest_id, "boundary_manifest_id")
        if type(self.run_length) is not int:
            raise TypeError("run_length must be an int")
        if type(self.primitives) is not tuple:
            raise TypeError("primitives must be a tuple")
        if not self.primitives:
            raise ValueError("primitives must be non-empty")
        if not all(isinstance(item, Primitive) for item in self.primitives):
            raise TypeError("primitives must contain Primitive records")
        if len(slots) != len(self.primitives):
            raise ValueError("layer_slot_ids length must match primitives")
        _sha(self.factory_sha, "factory_sha")


@dataclass(frozen=True)
class PrimitiveOperatorWire:
    mechanism_id: str
    production_id: str
    layer_slot_id: str
    operation_id: Literal["local_canonical_shear"]
    interface_id: str
    source_channel: str
    destination_channel: str
    offset: tuple[int, ...]
    coefficient_wire: ComplexWire

    def __post_init__(self) -> None:
        _text(self.mechanism_id, "mechanism_id")
        _text(self.production_id, "production_id")
        _text(self.layer_slot_id, "layer_slot_id")
        if self.operation_id != _ACTUAL_OPERATION:
            raise ValueError("public operator wire only supports actual shear")
        _text(self.interface_id, "interface_id")
        _text(self.source_channel, "source_channel")
        _text(self.destination_channel, "destination_channel")
        _offset(self.offset, "offset")
        _complex_wire(self.coefficient_wire, "coefficient_wire")


@dataclass(frozen=True)
class CalibrationSeed:
    calibration_schema_version: str
    calibration_protocol_id: str
    interface: PrimitiveInterface
    state_shape: tuple[int, ...]
    dt: float
    target_blind_parameters: tuple[tuple[str, float], ...]
    source_basis: BasisManifest
    holdout_source_basis: BasisManifest
    readout_basis: BasisManifest
    boundary_manifest_id: Literal["periodic-v1"]
    runtime_operator_payload: tuple[PrimitiveOperatorWire, ...]
    runtime_operator_sha: str
    seed_sha: str

    def __post_init__(self) -> None:
        _text(self.calibration_schema_version, "calibration_schema_version")
        _text(self.calibration_protocol_id, "calibration_protocol_id")
        if not isinstance(self.interface, PrimitiveInterface):
            raise TypeError("interface must be a PrimitiveInterface")
        _shape(self.state_shape, "state_shape")
        _finite_float(self.dt, "dt")
        _blind_parameters(self.target_blind_parameters)
        for field in ("source_basis", "holdout_source_basis", "readout_basis"):
            if not isinstance(getattr(self, field), BasisManifest):
                raise TypeError(f"{field} must be a BasisManifest")
        if self.boundary_manifest_id != PERIODIC_BOUNDARY_ID:
            raise ValueError("boundary_manifest_id must be periodic-v1")
        if type(self.runtime_operator_payload) is not tuple:
            raise TypeError("runtime_operator_payload must be a tuple")
        if not self.runtime_operator_payload:
            raise ValueError("runtime_operator_payload must be non-empty")
        if not all(
            isinstance(item, PrimitiveOperatorWire)
            for item in self.runtime_operator_payload
        ):
            raise TypeError("runtime_operator_payload has the wrong record type")
        _sha(self.runtime_operator_sha, "runtime_operator_sha")
        _sha(self.seed_sha, "seed_sha")


@dataclass(frozen=True)
class CalibrationObservation:
    observation_schema_version: str
    seed_sha: str
    runtime_operator_sha: str
    holdout_source_manifest_id: str
    readout_manifest_id: str
    response_tensor: FrozenComplexTensor
    observation_sha: str

    def __post_init__(self) -> None:
        _text(self.observation_schema_version, "observation_schema_version")
        _sha(self.seed_sha, "seed_sha")
        _sha(self.runtime_operator_sha, "runtime_operator_sha")
        _sha(self.holdout_source_manifest_id, "holdout_source_manifest_id")
        _sha(self.readout_manifest_id, "readout_manifest_id")
        if not isinstance(self.response_tensor, FrozenComplexTensor):
            raise TypeError("response_tensor must be a FrozenComplexTensor")
        _sha(self.observation_sha, "observation_sha")


@dataclass(frozen=True)
class FrozenSyntheticTarget:
    target_schema_version: str
    target_spec_id: str
    target_spec_sha: str
    calibration_protocol_id: str
    seed_sha: str
    observation: CalibrationObservation
    target_response: FrozenComplexTensor
    runtime_operator_sha: str

    def __post_init__(self) -> None:
        _text(self.target_schema_version, "target_schema_version")
        _text(self.target_spec_id, "target_spec_id")
        _sha(self.target_spec_sha, "target_spec_sha")
        _text(self.calibration_protocol_id, "calibration_protocol_id")
        _sha(self.seed_sha, "seed_sha")
        if not isinstance(self.observation, CalibrationObservation):
            raise TypeError("observation must be a CalibrationObservation")
        if not isinstance(self.target_response, FrozenComplexTensor):
            raise TypeError("target_response must be a FrozenComplexTensor")
        _sha(self.runtime_operator_sha, "runtime_operator_sha")


def _snapshot_basis_manifest(basis: BasisManifest) -> BasisManifest:
    return BasisManifest(
        basis_schema_version=basis.basis_schema_version,
        role=basis.role,
        state_schema_id=basis.state_schema_id,
        channel_order=tuple(basis.channel_order),
        vectors_wire=tuple(
            tuple((real, imag) for real, imag in row)
            for row in basis.vectors_wire
        ),
        manifest_id=basis.manifest_id,
    )


def _snapshot_complex_tensor(
    tensor: FrozenComplexTensor,
) -> FrozenComplexTensor:
    return FrozenComplexTensor(
        tensor_schema_version=tensor.tensor_schema_version,
        shape=tuple(tensor.shape),
        values_wire=tuple(
            (real, imag) for real, imag in tensor.values_wire
        ),
        tensor_sha=tensor.tensor_sha,
    )


def _snapshot_interface(interface: PrimitiveInterface) -> PrimitiveInterface:
    return PrimitiveInterface(
        interface_id=interface.interface_id,
        state_schema_id=interface.state_schema_id,
        spatial_ndim=interface.spatial_ndim,
        channel_order=tuple(interface.channel_order),
        dtype=interface.dtype,
        backend=interface.backend,
    )


def _snapshot_primitive(primitive: Primitive) -> Primitive:
    return Primitive(
        primitive_schema_version=primitive.primitive_schema_version,
        mechanism_id=primitive.mechanism_id,
        production_id=primitive.production_id,
        layer_slot_id=primitive.layer_slot_id,
        operation_id=primitive.operation_id,
        interface_id=primitive.interface_id,
        source_channel=primitive.source_channel,
        destination_channel=primitive.destination_channel,
        offset=tuple(primitive.offset),
        support_offsets=tuple(
            tuple(offset) for offset in primitive.support_offsets
        ),
        coefficient_wire=(
            primitive.coefficient_wire[0],
            primitive.coefficient_wire[1],
        ),
        coefficient_digest=primitive.coefficient_digest,
        neutral_identity_id=primitive.neutral_identity_id,
    )


def _snapshot_factory(
    factory: LinearRealspaceFactory,
) -> LinearRealspaceFactory:
    return LinearRealspaceFactory(
        factory_schema_version=factory.factory_schema_version,
        factory_role=factory.factory_role,
        factory_id=factory.factory_id,
        construction_trace_sha=factory.construction_trace_sha,
        grammar_id=factory.grammar_id,
        target_spec_id=factory.target_spec_id,
        target_spec_sha=factory.target_spec_sha,
        runtime_operator_sha=factory.runtime_operator_sha,
        interface=_snapshot_interface(factory.interface),
        state_schema_id=factory.state_schema_id,
        spatial_ndim=factory.spatial_ndim,
        channel_order=tuple(factory.channel_order),
        state_shape=tuple(factory.state_shape),
        dtype=factory.dtype,
        backend=factory.backend,
        dt=factory.dt,
        target_blind_parameters=tuple(
            (name, value)
            for name, value in factory.target_blind_parameters
        ),
        layer_slot_ids=tuple(factory.layer_slot_ids),
        source_manifest_id=factory.source_manifest_id,
        readout_basis=_snapshot_basis_manifest(factory.readout_basis),
        boundary_manifest_id=factory.boundary_manifest_id,
        run_length=factory.run_length,
        primitives=tuple(
            _snapshot_primitive(primitive)
            for primitive in factory.primitives
        ),
        factory_sha=factory.factory_sha,
    )


def _snapshot_observation(
    observation: CalibrationObservation,
) -> CalibrationObservation:
    return CalibrationObservation(
        observation_schema_version=observation.observation_schema_version,
        seed_sha=observation.seed_sha,
        runtime_operator_sha=observation.runtime_operator_sha,
        holdout_source_manifest_id=observation.holdout_source_manifest_id,
        readout_manifest_id=observation.readout_manifest_id,
        response_tensor=_snapshot_complex_tensor(
            observation.response_tensor
        ),
        observation_sha=observation.observation_sha,
    )


def _snapshot_target(
    target: FrozenSyntheticTarget,
) -> FrozenSyntheticTarget:
    return FrozenSyntheticTarget(
        target_schema_version=target.target_schema_version,
        target_spec_id=target.target_spec_id,
        target_spec_sha=target.target_spec_sha,
        calibration_protocol_id=target.calibration_protocol_id,
        seed_sha=target.seed_sha,
        observation=_snapshot_observation(target.observation),
        target_response=_snapshot_complex_tensor(target.target_response),
        runtime_operator_sha=target.runtime_operator_sha,
    )


class VerifiedFactory:
    """Opaque module-issued wrapper; public construction is forbidden."""

    __slots__ = (
        "__factory",
        "__trace",
        "__target",
        "__token",
        "__seal",
        "__weakref__",
    )
    __factory: LinearRealspaceFactory
    __trace: ConstructionTrace
    __target: FrozenSyntheticTarget
    __token: object
    __seal: str

    def __init__(
        self,
        token: object,
        factory: LinearRealspaceFactory,
        trace: ConstructionTrace,
        target: FrozenSyntheticTarget,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("VerifiedFactory can only be issued by this module")
        object.__setattr__(self, "_VerifiedFactory__factory", factory)
        object.__setattr__(self, "_VerifiedFactory__trace", trace)
        object.__setattr__(self, "_VerifiedFactory__target", target)
        object.__setattr__(self, "_VerifiedFactory__token", token)
        object.__setattr__(
            self,
            "_VerifiedFactory__seal",
            _verified_factory_seal(factory, trace, target),
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedFactory is immutable")

    @property
    def factory(self) -> LinearRealspaceFactory:
        return self.__factory

    @property
    def role(self) -> Literal["actual", "matched_ablated"]:
        return self.__factory.factory_role

    def _bound_records(
        self,
    ) -> tuple[ConstructionTrace, FrozenSyntheticTarget]:
        return self.__trace, self.__target


@dataclass(frozen=True)
class _VerifiedFactoryAuthority:
    factory: LinearRealspaceFactory
    trace: ConstructionTrace
    target: FrozenSyntheticTarget
    role: Literal["actual", "matched_ablated"]
    fingerprint: str


@dataclass(frozen=True)
class _VerifiedFactoryView:
    factory: LinearRealspaceFactory
    trace: ConstructionTrace
    target: FrozenSyntheticTarget
    role: Literal["actual", "matched_ablated"]


def _make_verified_factory_authority_registry() -> tuple[
    Callable[..., VerifiedFactory],
    Callable[[VerifiedFactory], _VerifiedFactoryView],
]:
    registry: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedFactory],
            _VerifiedFactoryAuthority,
        ],
    ] = {}
    lock = threading.RLock()

    def issue_authorized(
        factory: LinearRealspaceFactory,
        trace: ConstructionTrace,
        target: FrozenSyntheticTarget,
        *,
        role: Literal["actual", "matched_ablated"],
    ) -> VerifiedFactory:
        if not isinstance(factory, LinearRealspaceFactory):
            raise TypeError("factory must be a LinearRealspaceFactory")
        if not isinstance(trace, ConstructionTrace):
            raise TypeError("trace must be a ConstructionTrace")
        if not isinstance(target, FrozenSyntheticTarget):
            raise TypeError("target must be a FrozenSyntheticTarget")
        try:
            authority_trace = verify_construction_trace(
                construction_trace_payload(trace)
            )
            authority_target = _snapshot_target(target)
            authority_factory = _snapshot_factory(factory)
        except (AttributeError, IndexError) as exc:
            raise ValueError(
                "factory issuance record is incomplete"
            ) from exc
        _verify_factory_payload(
            authority_factory,
            authority_trace,
            authority_target,
            expected_role=role,
        )
        authority = _VerifiedFactoryAuthority(
            factory=authority_factory,
            trace=authority_trace,
            target=authority_target,
            role=role,
            fingerprint=_verified_factory_seal(
                authority_factory,
                authority_trace,
                authority_target,
            ),
        )
        wrapper = VerifiedFactory(
            _ISSUANCE_TOKEN,
            _snapshot_factory(authority_factory),
            verify_construction_trace(
                construction_trace_payload(authority_trace)
            ),
            _snapshot_target(authority_target),
        )
        identity = id(wrapper)

        def remove_stale(
            reference: weakref.ReferenceType[VerifiedFactory],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = registry.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del registry[wrapper_id]

        reference = weakref.ref(wrapper, remove_stale)
        with lock:
            current = registry.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("live VerifiedFactory identity collision")
            registry[identity] = (reference, authority)
        return wrapper

    def reverify_authorized(
        wrapper: VerifiedFactory,
    ) -> _VerifiedFactoryView:
        if type(wrapper) is not VerifiedFactory:
            raise TypeError("runtime requires a module-issued VerifiedFactory")
        with lock:
            current = registry.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError(
                    "VerifiedFactory identity is absent from the authority "
                    "registry"
                )
            authority = current[1]
            authority_factory = _snapshot_factory(authority.factory)
            authority_trace = verify_construction_trace(
                construction_trace_payload(authority.trace)
            )
            authority_target = _snapshot_target(authority.target)
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedFactory__token",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedFactory__seal",
            )
            payload = object.__getattribute__(
                wrapper,
                "_VerifiedFactory__factory",
            )
            trace = object.__getattribute__(
                wrapper,
                "_VerifiedFactory__trace",
            )
            target = object.__getattribute__(
                wrapper,
                "_VerifiedFactory__target",
            )
        except AttributeError as exc:
            raise ValueError(
                "VerifiedFactory authority record is incomplete"
            ) from exc
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("VerifiedFactory authority token mismatch")
        if payload.factory_role != authority.role:
            raise ValueError(
                "VerifiedFactory identity does not match its authority registry"
            )
        _verify_factory_payload(
            authority_factory,
            authority_trace,
            authority_target,
            expected_role=authority.role,
        )
        authority_fingerprint = _verified_factory_seal(
            authority_factory,
            authority_trace,
            authority_target,
        )
        if authority_fingerprint != authority.fingerprint:
            raise ValueError(
                "VerifiedFactory authority snapshot fingerprint mismatch"
            )
        wrapper_fingerprint = _verified_factory_seal(payload, trace, target)
        if (
            seal != wrapper_fingerprint
            or seal != authority.fingerprint
            or seal != authority_fingerprint
        ):
            raise ValueError("VerifiedFactory immutable seal mismatch")
        return _VerifiedFactoryView(
            factory=authority_factory,
            trace=authority_trace,
            target=authority_target,
            role=authority.role,
        )

    def issue(
        factory: LinearRealspaceFactory,
        trace: ConstructionTrace,
        target: FrozenSyntheticTarget,
        *,
        role: Literal["actual", "matched_ablated"],
    ) -> VerifiedFactory:
        return issue_authorized(
            factory,
            trace,
            target,
            role=role,
        )

    def reverify(
        wrapper: VerifiedFactory,
    ) -> _VerifiedFactoryView:
        return reverify_authorized(wrapper)

    return issue, reverify


(
    _issue_verified_factory_wrapper,
    _reverify_verified_factory,
) = _make_verified_factory_authority_registry()


def _verify_interface(interface: PrimitiveInterface) -> PrimitiveInterface:
    if not isinstance(interface, PrimitiveInterface):
        raise TypeError("interface must be a PrimitiveInterface")
    _text(interface.interface_id, "interface_id")
    _text(interface.state_schema_id, "state_schema_id")
    _positive_int(interface.spatial_ndim, "spatial_ndim")
    channels = _strings(interface.channel_order, "channel_order")
    if not channels:
        raise ValueError("channel_order must be non-empty")
    if interface.dtype != "complex128":
        raise ValueError("dtype must be complex128")
    if interface.backend != "numpy":
        raise ValueError("backend must be numpy")
    return interface


def _blind_parameters(
    parameters: object,
) -> tuple[tuple[str, float], ...]:
    if type(parameters) is not tuple:
        raise TypeError("target_blind_parameters must be a tuple")
    normalized = []
    seen = set()
    for index, entry in enumerate(parameters):
        if type(entry) is not tuple or len(entry) != 2:
            raise TypeError(
                f"target_blind_parameters[{index}] must be a pair"
            )
        name = _text(entry[0], f"target_blind_parameters[{index}][0]")
        value = _finite_float(
            entry[1],
            f"target_blind_parameters[{index}][1]",
        )
        if name in seen:
            raise ValueError("target_blind_parameters contains duplicate names")
        seen.add(name)
        normalized.append((name, value))
    result = tuple(normalized)
    if result != tuple(sorted(result)):
        raise ValueError("target_blind_parameters must be canonical")
    return result


def basis_manifest_payload(basis: BasisManifest) -> dict[str, object]:
    """Return the complete basis body, excluding only ``manifest_id``."""

    if not isinstance(basis, BasisManifest):
        raise TypeError("basis must be a BasisManifest")
    return {
        "basis_schema_version": basis.basis_schema_version,
        "role": basis.role,
        "state_schema_id": basis.state_schema_id,
        "channel_order": list(basis.channel_order),
        "vectors_wire": [
            [_wire_record(wire) for wire in row] for row in basis.vectors_wire
        ],
    }


def _basis_record(basis: BasisManifest) -> dict[str, object]:
    return {**basis_manifest_payload(basis), "manifest_id": basis.manifest_id}


def verify_basis_manifest(basis: BasisManifest) -> BasisManifest:
    if not isinstance(basis, BasisManifest):
        raise TypeError("basis must be a BasisManifest")
    if basis.basis_schema_version != BASIS_SCHEMA_VERSION:
        raise ValueError("unexpected basis_schema_version")
    expected = canonical_sha(basis_manifest_payload(basis))
    if basis.manifest_id != expected:
        raise ValueError("manifest_id does not match complete basis body")
    return basis


def build_basis_manifest(
    *,
    role: Literal["source", "holdout_source", "readout"],
    state_schema_id: str,
    channel_order: Sequence[str],
    vectors: np.ndarray,
) -> BasisManifest:
    channels = tuple(channel_order)
    _strings(channels, "channel_order")
    array = np.asarray(vectors)
    if array.ndim != 2:
        raise ValueError("vectors must have shape (n_vector,n_channel)")
    if array.shape[0] <= 0 or array.shape[1] <= 0:
        raise ValueError("vectors must have non-empty dimensions")
    if array.shape[1] != len(channels):
        raise ValueError("vectors channel dimension does not match channel_order")
    complex_array = np.asarray(array, dtype=np.complex128)
    if not np.isfinite(complex_array.real).all() or not np.isfinite(
        complex_array.imag
    ).all():
        raise ValueError("vectors must contain finite complex128 values")
    wire = tuple(
        tuple(_wire_from_complex(complex(value)) for value in row)
        for row in complex_array
    )
    provisional = BasisManifest(
        basis_schema_version=BASIS_SCHEMA_VERSION,
        role=role,
        state_schema_id=_text(state_schema_id, "state_schema_id"),
        channel_order=channels,
        vectors_wire=wire,
        manifest_id="0" * 64,
    )
    return replace(
        provisional,
        manifest_id=canonical_sha(basis_manifest_payload(provisional)),
    )


def basis_manifest_array(basis: BasisManifest) -> np.ndarray:
    verified = verify_basis_manifest(basis)
    return np.asarray(
        [
            [complex(real, imag) for real, imag in row]
            for row in verified.vectors_wire
        ],
        dtype=np.complex128,
    ).copy()


def frozen_tensor_payload(tensor: FrozenComplexTensor) -> dict[str, object]:
    """Return the complete tensor body, excluding only ``tensor_sha``."""

    if type(tensor) is not FrozenComplexTensor:
        raise TypeError("tensor must be an exact FrozenComplexTensor")
    return {
        "tensor_schema_version": tensor.tensor_schema_version,
        "shape": list(tensor.shape),
        "values_wire": [_wire_record(wire) for wire in tensor.values_wire],
    }


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {**frozen_tensor_payload(tensor), "tensor_sha": tensor.tensor_sha}


def verify_frozen_tensor(tensor: FrozenComplexTensor) -> FrozenComplexTensor:
    if type(tensor) is not FrozenComplexTensor:
        raise TypeError("tensor must be an exact FrozenComplexTensor")
    if tensor.tensor_schema_version != TENSOR_SCHEMA_VERSION:
        raise ValueError("unexpected tensor_schema_version")
    if tensor.tensor_sha != canonical_sha(frozen_tensor_payload(tensor)):
        raise ValueError("tensor_sha does not match complete tensor body")
    return tensor


def freeze_complex_tensor(values: np.ndarray) -> FrozenComplexTensor:
    array = np.asarray(values)
    if array.ndim <= 0 or any(length <= 0 for length in array.shape):
        raise ValueError("tensor shape must have non-empty positive dimensions")
    complex_array = np.asarray(array, dtype=np.complex128)
    if not np.isfinite(complex_array.real).all() or not np.isfinite(
        complex_array.imag
    ).all():
        raise ValueError("tensor values must be finite")
    wire = tuple(
        _wire_from_complex(complex(value))
        for value in complex_array.reshape(-1, order="C")
    )
    provisional = FrozenComplexTensor(
        tensor_schema_version=TENSOR_SCHEMA_VERSION,
        shape=tuple(int(item) for item in complex_array.shape),
        values_wire=wire,
        tensor_sha="0" * 64,
    )
    return replace(
        provisional,
        tensor_sha=canonical_sha(frozen_tensor_payload(provisional)),
    )


def frozen_tensor_array(tensor: FrozenComplexTensor) -> np.ndarray:
    verified = verify_frozen_tensor(tensor)
    return np.asarray(
        [complex(real, imag) for real, imag in verified.values_wire],
        dtype=np.complex128,
    ).reshape(verified.shape, order="C").copy()


def primitive_operator_payload(
    operators: Sequence[PrimitiveOperatorWire],
) -> tuple[dict[str, object], ...]:
    values = tuple(operators)
    if not values:
        raise ValueError("operators must be non-empty")
    result: list[dict[str, object]] = []
    for operator in values:
        if not isinstance(operator, PrimitiveOperatorWire):
            raise TypeError("operators must contain PrimitiveOperatorWire")
        result.append(
            {
                "mechanism_id": operator.mechanism_id,
                "production_id": operator.production_id,
                "layer_slot_id": operator.layer_slot_id,
                "operation_id": operator.operation_id,
                "interface_id": operator.interface_id,
                "source_channel": operator.source_channel,
                "destination_channel": operator.destination_channel,
                "offset": list(operator.offset),
                "coefficient_wire": _wire_record(operator.coefficient_wire),
            }
        )
    return tuple(result)


def primitive_payload(primitive: Primitive) -> dict[str, object]:
    if not isinstance(primitive, Primitive):
        raise TypeError("primitive must be a Primitive")
    return {
        "primitive_schema_version": primitive.primitive_schema_version,
        "mechanism_id": primitive.mechanism_id,
        "production_id": primitive.production_id,
        "layer_slot_id": primitive.layer_slot_id,
        "operation_id": primitive.operation_id,
        "interface_id": primitive.interface_id,
        "source_channel": primitive.source_channel,
        "destination_channel": primitive.destination_channel,
        "offset": list(primitive.offset),
        "support_offsets": [list(item) for item in primitive.support_offsets],
        "coefficient_wire": _wire_record(primitive.coefficient_wire),
        "coefficient_digest": primitive.coefficient_digest,
        "neutral_identity_id": primitive.neutral_identity_id,
    }


def primitive_sha(primitive: Primitive) -> str:
    return canonical_sha(primitive_payload(primitive))


def runtime_operator_payload(
    primitives: Sequence[Primitive],
) -> tuple[dict[str, object], ...]:
    values = tuple(primitives)
    if not values:
        raise ValueError("primitives must be non-empty")
    return tuple(
        {
            "mechanism_id": item.mechanism_id,
            "production_id": item.production_id,
            "layer_slot_id": item.layer_slot_id,
            "operation_id": item.operation_id,
            "interface_id": item.interface_id,
            "source_channel": item.source_channel,
            "destination_channel": item.destination_channel,
            "offset": list(item.offset),
            "coefficient_wire": _wire_record(item.coefficient_wire),
        }
        for item in values
    )


def runtime_operator_sha(
    operators: Sequence[object],
) -> str:
    values = tuple(operators)
    if not values:
        raise ValueError("runtime operator must be non-empty")
    if all(isinstance(item, PrimitiveOperatorWire) for item in values):
        payload = primitive_operator_payload(values)  # type: ignore[arg-type]
    elif all(isinstance(item, Primitive) for item in values):
        payload = runtime_operator_payload(values)  # type: ignore[arg-type]
    else:
        raise TypeError(
            "runtime operator must contain one homogeneous frozen wire type"
        )
    return canonical_sha({"runtime_operator_payload": list(payload)})


def calibration_seed_payload(seed: CalibrationSeed) -> dict[str, object]:
    if not isinstance(seed, CalibrationSeed):
        raise TypeError("seed must be a CalibrationSeed")
    return {
        "calibration_schema_version": seed.calibration_schema_version,
        "calibration_protocol_id": seed.calibration_protocol_id,
        "interface": _interface_record(seed.interface),
        "state_shape": list(seed.state_shape),
        "dt": seed.dt,
        "target_blind_parameters": [
            [name, value] for name, value in seed.target_blind_parameters
        ],
        "source_basis": _basis_record(seed.source_basis),
        "holdout_source_basis": _basis_record(seed.holdout_source_basis),
        "readout_basis": _basis_record(seed.readout_basis),
        "boundary_manifest_id": seed.boundary_manifest_id,
        "runtime_operator_payload": list(
            primitive_operator_payload(seed.runtime_operator_payload)
        ),
        "runtime_operator_sha": seed.runtime_operator_sha,
    }


def calibration_observation_payload(
    observation: CalibrationObservation,
) -> dict[str, object]:
    if not isinstance(observation, CalibrationObservation):
        raise TypeError("observation must be a CalibrationObservation")
    return {
        "observation_schema_version": observation.observation_schema_version,
        "seed_sha": observation.seed_sha,
        "runtime_operator_sha": observation.runtime_operator_sha,
        "holdout_source_manifest_id": observation.holdout_source_manifest_id,
        "readout_manifest_id": observation.readout_manifest_id,
        "response_tensor": _tensor_record(observation.response_tensor),
    }


def synthetic_target_payload(
    target: FrozenSyntheticTarget,
) -> dict[str, object]:
    if not isinstance(target, FrozenSyntheticTarget):
        raise TypeError("target must be a FrozenSyntheticTarget")
    return {
        "target_schema_version": target.target_schema_version,
        "target_spec_id": target.target_spec_id,
        "calibration_protocol_id": target.calibration_protocol_id,
        "seed_sha": target.seed_sha,
        "observation": {
            **calibration_observation_payload(target.observation),
            "observation_sha": target.observation.observation_sha,
        },
        "target_response": _tensor_record(target.target_response),
        "runtime_operator_sha": target.runtime_operator_sha,
    }


def _verify_basis_for_interface(
    basis: BasisManifest,
    interface: PrimitiveInterface,
    expected_role: str,
    field: str,
) -> None:
    verify_basis_manifest(basis)
    if basis.role != expected_role:
        raise ValueError(f"{field}.role mismatch")
    if basis.state_schema_id != interface.state_schema_id:
        raise ValueError(f"{field}.state_schema_id mismatch")
    if basis.channel_order != interface.channel_order:
        raise ValueError(f"{field}.channel_order mismatch")


def _validate_state_shape(
    state_shape: tuple[int, ...],
    interface: PrimitiveInterface,
) -> tuple[int, ...]:
    normalized = _shape(state_shape, "state_shape")
    if len(normalized) != interface.spatial_ndim + 1:
        raise ValueError("state_shape rank does not match spatial_ndim")
    if normalized[0] != len(interface.channel_order):
        raise ValueError("state_shape channel axis does not match channel_order")
    return normalized


def _validate_operator(
    operator: PrimitiveOperatorWire,
    interface: PrimitiveInterface,
    *,
    seed_mode: bool,
) -> None:
    if not isinstance(operator, PrimitiveOperatorWire):
        raise TypeError("operator_payload has the wrong record type")
    if operator.operation_id != _ACTUAL_OPERATION:
        raise ValueError("operator operation_id must be local_canonical_shear")
    if seed_mode and operator.production_id not in _BLIND_SEED_PRODUCTIONS:
        raise ValueError("calibration seed operator is not target-free")
    if operator.interface_id != interface.interface_id:
        raise ValueError("operator interface_id mismatch")
    if operator.source_channel not in interface.channel_order:
        raise ValueError("operator source_channel is not in interface")
    if operator.destination_channel not in interface.channel_order:
        raise ValueError("operator destination_channel is not in interface")
    if operator.source_channel == operator.destination_channel:
        raise ValueError("canonical shear requires distinct channels")
    _offset(operator.offset, "operator.offset", ndim=interface.spatial_ndim)
    if _wire_is_zero(operator.coefficient_wire):
        raise ValueError(
            "local_canonical_shear coefficient_wire must be non-zero"
        )


def _verify_calibration_seed(seed: CalibrationSeed) -> CalibrationSeed:
    if not isinstance(seed, CalibrationSeed):
        raise TypeError("seed must be a CalibrationSeed")
    if seed.calibration_schema_version != CALIBRATION_SCHEMA_VERSION:
        raise ValueError("unexpected calibration_schema_version")
    interface = _verify_interface(seed.interface)
    _validate_state_shape(seed.state_shape, interface)
    if seed.dt <= 0.0:
        raise ValueError("dt must be positive")
    _blind_parameters(seed.target_blind_parameters)
    _verify_basis_for_interface(seed.source_basis, interface, "source", "source_basis")
    _verify_basis_for_interface(
        seed.holdout_source_basis,
        interface,
        "holdout_source",
        "holdout_source_basis",
    )
    _verify_basis_for_interface(
        seed.readout_basis,
        interface,
        "readout",
        "readout_basis",
    )
    if seed.boundary_manifest_id != PERIODIC_BOUNDARY_ID:
        raise ValueError("boundary_manifest_id must be periodic-v1")
    mechanisms = []
    slots = []
    for operator in seed.runtime_operator_payload:
        _validate_operator(operator, interface, seed_mode=True)
        mechanisms.append(operator.mechanism_id)
        slots.append(operator.layer_slot_id)
    if len(set(mechanisms)) != len(mechanisms):
        raise ValueError("runtime operator mechanism_id values must be unique")
    if len(set(slots)) != len(slots):
        raise ValueError("runtime operator layer_slot_id values must be unique")
    expected_runtime_sha = runtime_operator_sha(seed.runtime_operator_payload)
    if seed.runtime_operator_sha != expected_runtime_sha:
        raise ValueError("runtime_operator_sha mismatch")
    if seed.seed_sha != canonical_sha(calibration_seed_payload(seed)):
        raise ValueError("seed_sha does not match complete seed body")
    return seed


def build_calibration_seed(
    *,
    calibration_protocol_id: str,
    interface: PrimitiveInterface,
    state_shape: Sequence[int],
    dt: float,
    target_blind_parameters: Sequence[tuple[str, float]],
    source_basis: BasisManifest,
    holdout_source_basis: BasisManifest,
    readout_basis: BasisManifest,
    boundary_manifest_id: str,
    operator_payload: Sequence[PrimitiveOperatorWire],
) -> CalibrationSeed:
    verified_interface = _verify_interface(interface)
    shape = tuple(state_shape)
    parameters = tuple(target_blind_parameters)
    operators = tuple(operator_payload)
    provisional = CalibrationSeed(
        calibration_schema_version=CALIBRATION_SCHEMA_VERSION,
        calibration_protocol_id=_text(
            calibration_protocol_id,
            "calibration_protocol_id",
        ),
        interface=verified_interface,
        state_shape=shape,
        dt=_finite_float(dt, "dt"),
        target_blind_parameters=parameters,
        source_basis=verify_basis_manifest(source_basis),
        holdout_source_basis=verify_basis_manifest(holdout_source_basis),
        readout_basis=verify_basis_manifest(readout_basis),
        boundary_manifest_id=boundary_manifest_id,  # type: ignore[arg-type]
        runtime_operator_payload=operators,
        runtime_operator_sha=runtime_operator_sha(operators),
        seed_sha="0" * 64,
    )
    provisional = replace(
        provisional,
        seed_sha=canonical_sha(calibration_seed_payload(provisional)),
    )
    return _verify_calibration_seed(provisional)


def _primitive_from_operator(
    operator: PrimitiveOperatorWire,
    coefficient_digest: str,
    support_offsets: tuple[tuple[int, ...], ...],
) -> Primitive:
    return Primitive(
        primitive_schema_version=PRIMITIVE_SCHEMA_VERSION,
        mechanism_id=operator.mechanism_id,
        production_id=operator.production_id,
        layer_slot_id=operator.layer_slot_id,
        operation_id=_ACTUAL_OPERATION,
        interface_id=operator.interface_id,
        source_channel=operator.source_channel,
        destination_channel=operator.destination_channel,
        offset=operator.offset,
        support_offsets=support_offsets,
        coefficient_wire=operator.coefficient_wire,
        coefficient_digest=coefficient_digest,
        neutral_identity_id=None,
    )


def _calibration_primitive(operator: PrimitiveOperatorWire) -> Primitive:
    ndim = len(operator.offset)
    zero = (0,) * ndim
    return Primitive(
        primitive_schema_version=PRIMITIVE_SCHEMA_VERSION,
        mechanism_id=operator.mechanism_id,
        production_id=operator.production_id,
        layer_slot_id=operator.layer_slot_id,
        operation_id=_ACTUAL_OPERATION,
        interface_id=operator.interface_id,
        source_channel=operator.source_channel,
        destination_channel=operator.destination_channel,
        offset=operator.offset,
        support_offsets=tuple(sorted({zero, operator.offset})),
        coefficient_wire=operator.coefficient_wire,
        coefficient_digest="0" * 64,
        neutral_identity_id=None,
    )


def _minkowski(
    left: Sequence[tuple[int, ...]],
    right: Sequence[tuple[int, ...]],
) -> tuple[tuple[int, ...], ...]:
    allocation_product = len(left) * len(right)
    if allocation_product > FACTORY_SUPPORT_MAX_ALLOCATION_PRODUCT:
        raise ValueError("Minkowski allocation product limit exceeded")
    result: set[tuple[int, ...]] = set()
    for first in left:
        for second in right:
            result.add(
                tuple(a + b for a, b in zip(first, second))
            )
            if len(result) > FACTORY_SUPPORT_MAX_CARDINALITY:
                raise ValueError("support cardinality limit exceeded")
    return tuple(sorted(result))


def _primitive_sequence_support(
    primitives: Sequence[Primitive],
    ndim: int,
) -> tuple[tuple[int, ...], ...]:
    """Return a channel-aware structural support enclosure.

    A global Minkowski sum treats independent row shears as if every stencil
    composed with every later stencil.  That can grow with primitive count
    even when the executed matrix Laurent polynomial has fixed radius.  Track
    source-channel lineage instead; this remains conservative (it does not
    cancel coefficients) while respecting which rows actually feed a shear.
    """

    zero = (0,) * ndim
    channels = tuple(
        dict.fromkeys(
            channel
            for primitive in primitives
            for channel in (
                primitive.source_channel,
                primitive.destination_channel,
            )
        )
    )
    lineage: dict[str, set[tuple[str, tuple[int, ...]]]] = {
        channel: {(channel, zero)} for channel in channels
    }
    for primitive in primitives:
        if primitive.operation_id == _NEUTRAL_OPERATION:
            continue
        source = lineage[primitive.source_channel]
        destination = lineage[primitive.destination_channel]
        shifted = {
            (
                origin_channel,
                tuple(
                    coordinate + delta
                    for coordinate, delta in zip(offset, primitive.offset)
                ),
            )
            for origin_channel, offset in source
        }
        destination.update(shifted)
        if sum(len(entries) for entries in lineage.values()) > (
            FACTORY_SUPPORT_MAX_CARDINALITY
        ):
            raise ValueError("support cardinality limit exceeded")
    return tuple(
        sorted({offset for entries in lineage.values() for _, offset in entries})
    )


def _assert_no_wrap(
    spatial_shape: Sequence[int],
    support: Sequence[tuple[int, ...]],
) -> None:
    for axis, length in enumerate(spatial_shape):
        radius = max(abs(offset[axis]) for offset in support)
        if length <= 2 * radius:
            raise ValueError(
                f"spatial axis {axis} violates no-wrap L_i > 2 r_i"
            )


def _apply_primitive(
    primitive: Primitive,
    interface: PrimitiveInterface,
    state: np.ndarray,
) -> np.ndarray:
    """Apply one already-bound primitive; intentionally module-private."""

    if not isinstance(primitive, Primitive):
        raise TypeError("primitive must be a Primitive")
    verified_interface = _verify_interface(interface)
    if type(state) is not np.ndarray:
        raise TypeError("state must be a NumPy ndarray")
    if state.dtype != np.dtype(np.complex128):
        raise TypeError("state dtype must be complex128")
    expected_rank = verified_interface.spatial_ndim + 1
    if state.ndim != expected_rank:
        raise ValueError("state rank does not match interface")
    if state.shape[0] != len(verified_interface.channel_order):
        raise ValueError("state channel axis does not match interface")
    if primitive.interface_id != verified_interface.interface_id:
        raise ValueError("primitive interface_id mismatch")
    output = state.copy()
    if primitive.operation_id == _NEUTRAL_OPERATION:
        return output
    source_index = verified_interface.channel_order.index(
        primitive.source_channel
    )
    destination_index = verified_interface.channel_order.index(
        primitive.destination_channel
    )
    shifted = state[source_index]
    for axis, coordinate in enumerate(primitive.offset):
        shifted = np.roll(shifted, shift=-coordinate, axis=axis)
    coefficient = complex(*primitive.coefficient_wire)
    output[destination_index] += coefficient * shifted
    return output


def measure_calibration_holdout(
    seed: CalibrationSeed,
) -> CalibrationObservation:
    verified = _verify_calibration_seed(seed)
    holdout = basis_manifest_array(verified.holdout_source_basis)
    readout = basis_manifest_array(verified.readout_basis)
    primitives = tuple(
        _calibration_primitive(item)
        for item in verified.runtime_operator_payload
    )
    spatial_shape = verified.state_shape[1:]
    support = _primitive_sequence_support(
        primitives,
        verified.interface.spatial_ndim,
    )
    _assert_no_wrap(spatial_shape, support)
    response = np.zeros(
        (readout.shape[0], holdout.shape[0]) + spatial_shape,
        dtype=np.complex128,
    )
    origin = (0,) * verified.interface.spatial_ndim
    for source_index, vector in enumerate(holdout):
        state = np.zeros(verified.state_shape, dtype=np.complex128)
        state[(slice(None),) + origin] = vector
        for primitive in primitives:
            state = _apply_primitive(primitive, verified.interface, state)
        response[(slice(None), source_index) + (slice(None),) * len(spatial_shape)] = (
            np.einsum("ac,c...->a...", readout.conj(), state)
        )
    tensor = freeze_complex_tensor(response)
    provisional = CalibrationObservation(
        observation_schema_version=OBSERVATION_SCHEMA_VERSION,
        seed_sha=verified.seed_sha,
        runtime_operator_sha=verified.runtime_operator_sha,
        holdout_source_manifest_id=verified.holdout_source_basis.manifest_id,
        readout_manifest_id=verified.readout_basis.manifest_id,
        response_tensor=tensor,
        observation_sha="0" * 64,
    )
    return replace(
        provisional,
        observation_sha=canonical_sha(
            calibration_observation_payload(provisional)
        ),
    )


def _verify_observation(
    observation: CalibrationObservation,
) -> CalibrationObservation:
    if not isinstance(observation, CalibrationObservation):
        raise TypeError("observation must be a CalibrationObservation")
    if observation.observation_schema_version != OBSERVATION_SCHEMA_VERSION:
        raise ValueError("unexpected observation_schema_version")
    verify_frozen_tensor(observation.response_tensor)
    if observation.observation_sha != canonical_sha(
        calibration_observation_payload(observation)
    ):
        raise ValueError("observation_sha does not match complete body")
    return observation


def freeze_synthetic_target(
    seed: CalibrationSeed,
    observation: CalibrationObservation,
    target_spec_id: str,
) -> FrozenSyntheticTarget:
    verified_seed = _verify_calibration_seed(seed)
    verified_observation = _verify_observation(observation)
    expected = measure_calibration_holdout(verified_seed)
    if verified_observation != expected:
        raise ValueError("observation does not match frozen calibration seed")
    provisional = FrozenSyntheticTarget(
        target_schema_version=TARGET_SCHEMA_VERSION,
        target_spec_id=_text(target_spec_id, "target_spec_id"),
        target_spec_sha="0" * 64,
        calibration_protocol_id=verified_seed.calibration_protocol_id,
        seed_sha=verified_seed.seed_sha,
        observation=verified_observation,
        target_response=verified_observation.response_tensor,
        runtime_operator_sha=verified_seed.runtime_operator_sha,
    )
    return replace(
        provisional,
        target_spec_sha=canonical_sha(synthetic_target_payload(provisional)),
    )


def verify_synthetic_target(
    target: FrozenSyntheticTarget,
) -> FrozenSyntheticTarget:
    if not isinstance(target, FrozenSyntheticTarget):
        raise TypeError("target must be a FrozenSyntheticTarget")
    if target.target_schema_version != TARGET_SCHEMA_VERSION:
        raise ValueError("unexpected target_schema_version")
    observation = _verify_observation(target.observation)
    verify_frozen_tensor(target.target_response)
    if target.seed_sha != observation.seed_sha:
        raise ValueError("target seed_sha does not match observation")
    if target.runtime_operator_sha != observation.runtime_operator_sha:
        raise ValueError("target runtime_operator_sha does not match observation")
    if target.target_response != observation.response_tensor:
        raise ValueError("target_response must equal observation.response_tensor")
    if target.target_spec_sha != canonical_sha(synthetic_target_payload(target)):
        raise ValueError("target_spec_sha does not match complete target body")
    return target


def factory_payload(factory: LinearRealspaceFactory) -> dict[str, object]:
    """Return the complete factory body, excluding only ``factory_sha``."""

    if not isinstance(factory, LinearRealspaceFactory):
        raise TypeError("factory must be a LinearRealspaceFactory")
    return {
        "factory_schema_version": factory.factory_schema_version,
        "factory_role": factory.factory_role,
        "factory_id": factory.factory_id,
        "construction_trace_sha": factory.construction_trace_sha,
        "grammar_id": factory.grammar_id,
        "target_spec_id": factory.target_spec_id,
        "target_spec_sha": factory.target_spec_sha,
        "runtime_operator_sha": factory.runtime_operator_sha,
        "interface": _interface_record(factory.interface),
        "state_schema_id": factory.state_schema_id,
        "spatial_ndim": factory.spatial_ndim,
        "channel_order": list(factory.channel_order),
        "state_shape": list(factory.state_shape),
        "dtype": factory.dtype,
        "backend": factory.backend,
        "dt": factory.dt,
        "target_blind_parameters": [
            [name, value] for name, value in factory.target_blind_parameters
        ],
        "layer_slot_ids": list(factory.layer_slot_ids),
        "source_manifest_id": factory.source_manifest_id,
        "readout_basis": _basis_record(factory.readout_basis),
        "boundary_manifest_id": factory.boundary_manifest_id,
        "run_length": factory.run_length,
        "primitives": [primitive_payload(item) for item in factory.primitives],
    }


def factory_sha(factory: LinearRealspaceFactory) -> str:
    return canonical_sha(factory_payload(factory))


def _verified_factory_seal(
    factory: LinearRealspaceFactory,
    trace: ConstructionTrace,
    target: FrozenSyntheticTarget,
) -> str:
    """Seal every authority-bearing wrapper component, not only its token."""

    return canonical_sha(
        {
            "wrapper_schema_version": "v3m0.verified-factory.v1",
            "role": factory.factory_role,
            "factory": {
                **factory_payload(factory),
                "factory_sha": factory.factory_sha,
            },
            "construction_trace": construction_trace_payload(trace),
            "target": {
                **synthetic_target_payload(target),
                "target_spec_sha": target.target_spec_sha,
            },
        }
    )


def _verify_factory_payload(
    factory: LinearRealspaceFactory,
    trace: ConstructionTrace,
    target: FrozenSyntheticTarget,
    *,
    expected_role: Literal["actual", "matched_ablated"],
) -> None:
    if not isinstance(factory, LinearRealspaceFactory):
        raise TypeError("factory must be a LinearRealspaceFactory")
    verified_trace = verify_construction_trace(trace)
    verified_target = verify_synthetic_target(target)
    if factory.factory_schema_version != FACTORY_SCHEMA_VERSION:
        raise ValueError("factory_schema_version mismatch")
    if factory.factory_role != expected_role:
        raise ValueError("factory_role mismatch")
    if factory.construction_trace_sha != verified_trace.trace_sha:
        raise ValueError("construction_trace_sha mismatch")
    if factory.grammar_id != verified_trace.grammar_id:
        raise ValueError("grammar_id mismatch")
    if factory.target_spec_id != verified_trace.target_spec_id:
        raise ValueError("target_spec_id mismatch")
    if factory.target_spec_id != verified_target.target_spec_id:
        raise ValueError("target_spec_id does not match target")
    if factory.target_spec_sha != verified_target.target_spec_sha:
        raise ValueError("target_spec_sha mismatch")

    interface = _verify_interface(factory.interface)
    for field, expected in (
        ("state_schema_id", interface.state_schema_id),
        ("spatial_ndim", interface.spatial_ndim),
        ("channel_order", interface.channel_order),
        ("dtype", interface.dtype),
        ("backend", interface.backend),
    ):
        if getattr(factory, field) != expected:
            raise ValueError(f"{field} mismatch")
    _validate_state_shape(factory.state_shape, interface)
    if factory.dt <= 0.0:
        raise ValueError("dt must be positive")
    _blind_parameters(factory.target_blind_parameters)
    if factory.boundary_manifest_id != PERIODIC_BOUNDARY_ID:
        raise ValueError("boundary_manifest_id mismatch")
    if factory.run_length != 1:
        raise ValueError("run_length must equal one macro step")
    _verify_basis_for_interface(
        factory.readout_basis,
        interface,
        "readout",
        "readout_basis",
    )
    if tuple(item.layer_slot_id for item in factory.primitives) != (
        factory.layer_slot_ids
    ):
        raise ValueError("layer_slot_ids mismatch")
    if len(factory.primitives) != len(verified_trace.primitives):
        raise ValueError("primitive count mismatch")

    records = {
        record.mechanism_id: record
        for record in verified_trace.coefficient_records
    }
    for index, (primitive, traced) in enumerate(
        zip(factory.primitives, verified_trace.primitives)
    ):
        prefix = f"primitive[{index}]"
        if primitive.primitive_schema_version != PRIMITIVE_SCHEMA_VERSION:
            raise ValueError(f"{prefix}.primitive_schema_version mismatch")
        if primitive.mechanism_id != traced.mechanism_id:
            raise ValueError(f"{prefix}.mechanism_id mismatch")
        if primitive.production_id != traced.production_id:
            raise ValueError(f"{prefix}.production_id mismatch")
        if primitive.interface_id != interface.interface_id:
            raise ValueError(f"{prefix}.interface_id mismatch")
        if primitive.source_channel not in interface.channel_order:
            raise ValueError(f"{prefix}.source_channel mismatch")
        if primitive.destination_channel not in interface.channel_order:
            raise ValueError(f"{prefix}.destination_channel mismatch")
        if primitive.source_channel == primitive.destination_channel:
            raise ValueError(f"{prefix} canonical shear channels must differ")
        if tuple(
            sorted((primitive.source_channel, primitive.destination_channel))
        ) != traced.state_channels:
            raise ValueError(f"{prefix}.state_channels mismatch")
        if primitive.coefficient_digest != traced.coefficient_digest:
            raise ValueError(f"{prefix}.coefficient_digest mismatch")
        record = records[primitive.mechanism_id]
        if primitive.operation_id == _ACTUAL_OPERATION:
            zero = (0,) * interface.spatial_ndim
            if primitive.offset != _offset(
                primitive.offset,
                f"{prefix}.offset",
                ndim=interface.spatial_ndim,
            ):
                raise AssertionError("offset validation lost")
            expected_support = tuple(sorted({zero, primitive.offset}))
            if primitive.support_offsets != expected_support:
                raise ValueError(f"{prefix}.support_offsets mismatch")
            if traced.support_offsets != expected_support:
                raise ValueError(f"{prefix}.trace support mismatch")
            expected_wire = _wire_from_complex(
                evaluate_closed_coefficient(record)
            )
            if _wire_is_zero(primitive.coefficient_wire):
                raise ValueError(
                    f"{prefix}.coefficient_wire must be bitwise non-zero"
                )
            if not _wire_equal(primitive.coefficient_wire, expected_wire):
                raise ValueError(f"{prefix}.coefficient_wire mismatch")
            if primitive.neutral_identity_id is not None:
                raise ValueError(f"{prefix}.neutral_identity_id mismatch")
        elif (
            expected_role == "matched_ablated"
            and primitive.operation_id == _NEUTRAL_OPERATION
        ):
            zero = (0,) * interface.spatial_ndim
            if traced.kind is not MechanismKind.TARGET_CONDITIONED:
                raise ValueError(f"{prefix} neutralized a non-conditioned slot")
            if traced.neutral_ablation != NEUTRAL_IDENTITY_ID:
                raise ValueError(f"{prefix} has no legal neutral construction")
            if primitive.offset != zero:
                raise ValueError(f"{prefix}.offset is not canonical neutral")
            if primitive.support_offsets != (zero,):
                raise ValueError(
                    f"{prefix}.support_offsets is not canonical neutral"
                )
            if not _wire_equal(
                primitive.coefficient_wire,
                (0.0, 0.0),
            ):
                raise ValueError(
                    f"{prefix}.coefficient_wire is not canonical neutral"
                )
            if primitive.neutral_identity_id != NEUTRAL_IDENTITY_ID:
                raise ValueError(f"{prefix}.neutral_identity_id mismatch")
        else:
            raise ValueError(f"{prefix}.operation_id is not permitted")
        if expected_role == "matched_ablated":
            if (
                traced.kind is MechanismKind.TARGET_CONDITIONED
                and primitive.operation_id != _NEUTRAL_OPERATION
            ):
                raise ValueError(
                    f"{prefix} did not neutralize a target-conditioned slot"
                )
            if (
                traced.kind is not MechanismKind.TARGET_CONDITIONED
                and primitive.operation_id != _ACTUAL_OPERATION
            ):
                raise ValueError(f"{prefix} changed a target-blind slot")

    expected_runtime_sha = runtime_operator_sha(factory.primitives)
    if factory.runtime_operator_sha != expected_runtime_sha:
        raise ValueError("runtime_operator_sha mismatch")
    if factory.factory_sha != factory_sha(factory):
        raise ValueError("factory_sha does not match complete body")


def _issue(
    factory: LinearRealspaceFactory,
    trace: ConstructionTrace,
    target: FrozenSyntheticTarget,
    *,
    role: Literal["actual", "matched_ablated"],
) -> VerifiedFactory:
    return _issue_verified_factory_wrapper(
        factory,
        trace,
        target,
        role=role,
    )


def build_factory_from_trace(
    trace: ConstructionTrace,
    target: FrozenSyntheticTarget,
    *,
    factory_id: str,
    interface: PrimitiveInterface,
    state_shape: Sequence[int],
    dt: float,
    target_blind_parameters: Sequence[tuple[str, float]],
    layer_slot_ids: Sequence[str],
    operator_payload: Sequence[PrimitiveOperatorWire],
    source_manifest_id: str,
    readout_basis: BasisManifest,
    boundary_manifest_id: str,
) -> VerifiedFactory:
    verified_trace = verify_construction_trace(trace)
    verified_target = verify_synthetic_target(target)
    verified_interface = _verify_interface(interface)
    shape = tuple(state_shape)
    _validate_state_shape(shape, verified_interface)
    parameters = tuple(target_blind_parameters)
    _blind_parameters(parameters)
    slots = tuple(layer_slot_ids)
    _strings(slots, "layer_slot_ids")
    operators = tuple(operator_payload)
    if len(operators) != len(verified_trace.primitives):
        raise ValueError("operator_payload count does not match trace")
    if len(slots) != len(operators):
        raise ValueError("layer_slot_ids count does not match operator_payload")
    records = {
        record.mechanism_id: record
        for record in verified_trace.coefficient_records
    }
    primitives = []
    for index, (operator, traced) in enumerate(
        zip(operators, verified_trace.primitives)
    ):
        _validate_operator(operator, verified_interface, seed_mode=False)
        if operator.mechanism_id != traced.mechanism_id:
            raise ValueError(f"operator[{index}].mechanism_id mismatch")
        if operator.production_id != traced.production_id:
            raise ValueError(f"operator[{index}].production_id mismatch")
        if operator.layer_slot_id != slots[index]:
            raise ValueError(f"operator[{index}].layer_slot_id mismatch")
        expected_wire = _wire_from_complex(
            evaluate_closed_coefficient(records[operator.mechanism_id])
        )
        if _wire_is_zero(operator.coefficient_wire):
            raise ValueError(
                f"operator[{index}].coefficient_wire must be bitwise non-zero"
            )
        if not _wire_equal(operator.coefficient_wire, expected_wire):
            raise ValueError(f"operator[{index}].coefficient_wire mismatch")
        primitives.append(
            _primitive_from_operator(
                operator,
                traced.coefficient_digest,
                traced.support_offsets,
            )
        )
    primitive_tuple = tuple(primitives)
    provisional = LinearRealspaceFactory(
        factory_schema_version=FACTORY_SCHEMA_VERSION,
        factory_role="actual",
        factory_id=_text(factory_id, "factory_id"),
        construction_trace_sha=verified_trace.trace_sha,
        grammar_id=verified_trace.grammar_id,
        target_spec_id=verified_target.target_spec_id,
        target_spec_sha=verified_target.target_spec_sha,
        runtime_operator_sha=runtime_operator_sha(primitive_tuple),
        interface=verified_interface,
        state_schema_id=verified_interface.state_schema_id,
        spatial_ndim=verified_interface.spatial_ndim,
        channel_order=verified_interface.channel_order,
        state_shape=shape,
        dtype=verified_interface.dtype,
        backend=verified_interface.backend,
        dt=_finite_float(dt, "dt"),
        target_blind_parameters=parameters,
        layer_slot_ids=slots,
        source_manifest_id=_sha(source_manifest_id, "source_manifest_id"),
        readout_basis=verify_basis_manifest(readout_basis),
        boundary_manifest_id=boundary_manifest_id,
        run_length=1,
        primitives=primitive_tuple,
        factory_sha="0" * 64,
    )
    provisional = replace(provisional, factory_sha=factory_sha(provisional))
    return _issue(provisional, verified_trace, verified_target, role="actual")


def build_full_factory_from_seed(
    trace: ConstructionTrace,
    target: FrozenSyntheticTarget,
    seed: CalibrationSeed,
    *,
    factory_id: str,
    layer_slot_ids: Sequence[str],
) -> VerifiedFactory:
    verified_seed = _verify_calibration_seed(seed)
    verified_target = verify_synthetic_target(target)
    verified_trace = verify_construction_trace(trace)
    if any(
        primitive.kind is not MechanismKind.TARGET_BLIND
        for primitive in verified_trace.primitives
    ):
        raise ValueError("FULL construction trace must be entirely target-blind")
    if verified_target.seed_sha != verified_seed.seed_sha:
        raise ValueError("target seed_sha does not match calibration seed")
    if (
        verified_target.calibration_protocol_id
        != verified_seed.calibration_protocol_id
    ):
        raise ValueError(
            "target calibration_protocol_id does not match calibration seed"
        )
    if verified_target.observation != measure_calibration_holdout(verified_seed):
        raise ValueError("target observation does not match calibration seed")
    if verified_target.runtime_operator_sha != verified_seed.runtime_operator_sha:
        raise ValueError("target runtime_operator_sha mismatch")
    result = build_factory_from_trace(
        verified_trace,
        verified_target,
        factory_id=factory_id,
        interface=verified_seed.interface,
        state_shape=verified_seed.state_shape,
        dt=verified_seed.dt,
        target_blind_parameters=verified_seed.target_blind_parameters,
        layer_slot_ids=layer_slot_ids,
        operator_payload=verified_seed.runtime_operator_payload,
        source_manifest_id=verified_seed.source_basis.manifest_id,
        readout_basis=verified_seed.readout_basis,
        boundary_manifest_id=verified_seed.boundary_manifest_id,
    )
    if result.factory.runtime_operator_sha != verified_seed.runtime_operator_sha:
        raise ValueError("FULL factory runtime operator does not match seed")
    return result


def verify_factory(
    factory: LinearRealspaceFactory,
    trace: ConstructionTrace,
    target: FrozenSyntheticTarget,
) -> VerifiedFactory:
    """Verify and issue an actual-only runtime wrapper."""

    return _issue(factory, trace, target, role="actual")


def _verify_matched_ablated_factory(
    factory: LinearRealspaceFactory,
    trace: ConstructionTrace,
    target: FrozenSyntheticTarget,
) -> VerifiedFactory:
    return _issue(factory, trace, target, role="matched_ablated")


def apply_factory_step(
    factory: VerifiedFactory,
    state: np.ndarray,
) -> np.ndarray:
    snapshot = _reverify_verified_factory(factory)
    payload = snapshot.factory
    if type(state) is not np.ndarray:
        raise TypeError("state must be a NumPy ndarray")
    if state.dtype != np.dtype(np.complex128):
        raise TypeError("state dtype must be complex128")
    if state.shape != payload.state_shape:
        raise ValueError("state shape does not match factory state_shape")
    result = state.copy()
    for primitive in payload.primitives:
        result = _apply_primitive(primitive, payload.interface, result)
    return result


def factory_support_offsets(
    factory: VerifiedFactory,
    macro_steps: int,
) -> tuple[tuple[int, ...], ...]:
    snapshot = _reverify_verified_factory(factory)
    steps = _positive_int(macro_steps, "macro_steps")
    if steps > FACTORY_SUPPORT_MAX_MACRO_STEPS:
        raise ValueError("factory support macro_steps limit exceeded")
    one_step = _primitive_sequence_support(
        snapshot.factory.primitives,
        snapshot.factory.spatial_ndim,
    )
    result: tuple[tuple[int, ...], ...] = (
        (0,) * snapshot.factory.spatial_ndim,
    )
    for _ in range(steps):
        result = _minkowski(result, one_step)
    return result


__all__ = [
    "BASIS_SCHEMA_VERSION",
    "CALIBRATION_SCHEMA_VERSION",
    "FACTORY_SCHEMA_VERSION",
    "FACTORY_SUPPORT_MAX_ALLOCATION_PRODUCT",
    "FACTORY_SUPPORT_MAX_CARDINALITY",
    "FACTORY_SUPPORT_MAX_MACRO_STEPS",
    "NEUTRAL_IDENTITY_ID",
    "OBSERVATION_SCHEMA_VERSION",
    "PERIODIC_BOUNDARY_ID",
    "PRIMITIVE_SCHEMA_VERSION",
    "TARGET_SCHEMA_VERSION",
    "TENSOR_SCHEMA_VERSION",
    "BasisManifest",
    "CalibrationObservation",
    "CalibrationSeed",
    "ComplexWire",
    "FrozenComplexTensor",
    "FrozenSyntheticTarget",
    "LinearRealspaceFactory",
    "Primitive",
    "PrimitiveInterface",
    "PrimitiveOperatorWire",
    "VerifiedFactory",
    "apply_factory_step",
    "basis_manifest_array",
    "basis_manifest_payload",
    "build_basis_manifest",
    "build_calibration_seed",
    "build_factory_from_trace",
    "build_full_factory_from_seed",
    "calibration_observation_payload",
    "calibration_seed_payload",
    "factory_payload",
    "factory_sha",
    "factory_support_offsets",
    "freeze_complex_tensor",
    "freeze_synthetic_target",
    "frozen_tensor_array",
    "frozen_tensor_payload",
    "measure_calibration_holdout",
    "primitive_operator_payload",
    "primitive_payload",
    "primitive_sha",
    "runtime_operator_payload",
    "runtime_operator_sha",
    "synthetic_target_payload",
    "verify_basis_manifest",
    "verify_factory",
    "verify_frozen_tensor",
    "verify_synthetic_target",
]
