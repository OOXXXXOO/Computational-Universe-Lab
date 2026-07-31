"""Strict, non-interchangeable momentum-grid manifests for V3-M0."""

from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass, replace
from enum import Enum
from types import FunctionType
from typing import Literal

from .evidence import canonical_sha
from .parent_freeze import (
    DirectionPathClosure,
    SyntheticApplicationGridProtocol,
    V3M0SyntheticControlApplicationSpec,
    verify_synthetic_control_application_spec,
)
from .thresholds import (
    GENERAL_EVIDENCE_BODY_BYTES_MAX,
    preflight_general_evidence_body,
)


DYNAMICS_GRID_SCHEMA_VERSION = "v3m0.dynamics-k-grid.v1"
RESPONSE_GRID_SCHEMA_VERSION = "v3m0.response-k-grid.v1"
DIRECTION_MANIFEST_SCHEMA_VERSION = "v3m0.direction-manifest.v1"
BRIDGE_GRID_SCHEMA_VERSION = "v3m0.bridge-k-grid.v1"
DYNAMICS_GRID_DENOMINATOR = 64
DYNAMICS_GRID_MAX_POINT_COUNT = 262_144
RESPONSE_GRID_MAX_POINT_COUNT = 262_144
BRIDGE_GRID_MAX_POINT_COUNT = 64
_GENERAL_EVIDENCE_TEXT_BYTES_MAX = 16_384
_GENERAL_EVIDENCE_SPATIAL_NDIM_MAX = 64
_GENERAL_EVIDENCE_MAX_DEPTH = 128
_FROZEN_GENERAL_EVIDENCE_BODY_BYTES_MAX = (
    GENERAL_EVIDENCE_BODY_BYTES_MAX
)
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


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _positive_tuple(value: object, field: str) -> tuple[int, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty tuple")
    return tuple(
        _positive_int(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    )


def _indices(
    value: object,
    field: str,
    denominators: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty tuple")
    result: list[tuple[int, ...]] = []
    for row_index, row in enumerate(value):
        if type(row) is not tuple or len(row) != len(denominators):
            raise ValueError(f"{field}[{row_index}] dimension mismatch")
        normalized: list[int] = []
        for axis, (item, denominator) in enumerate(
            zip(row, denominators)
        ):
            if type(item) is not int:
                raise TypeError(
                    f"{field}[{row_index}][{axis}] must be an int"
                )
            if not 0 <= item < denominator:
                raise ValueError(
                    f"{field}[{row_index}][{axis}] is outside its torus"
                )
            normalized.append(item)
        result.append(tuple(normalized))
    answer = tuple(result)
    if answer != tuple(sorted(set(answer))):
        raise ValueError(f"{field} must be unique and lexicographic")
    return answer


def _signed_support(
    value: object,
    field: str,
    *,
    ndim: int | None = None,
) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty tuple")
    result: list[tuple[int, ...]] = []
    inferred = ndim
    for row_index, row in enumerate(value):
        if type(row) is not tuple or not row:
            raise ValueError(f"{field}[{row_index}] must be non-empty")
        if inferred is None:
            inferred = len(row)
        if len(row) != inferred:
            raise ValueError(f"{field}[{row_index}] dimension mismatch")
        normalized: list[int] = []
        for axis, item in enumerate(row):
            if type(item) is not int:
                raise TypeError(
                    f"{field}[{row_index}][{axis}] must be an int"
                )
            normalized.append(item)
        result.append(tuple(normalized))
    answer = tuple(result)
    if answer != tuple(sorted(set(answer))):
        raise ValueError(f"{field} must be unique and lexicographic")
    return answer


def _is_zero_support(
    support: tuple[tuple[int, ...], ...],
) -> bool:
    return support == ((0,) * len(support[0]),)


def _string_tuple(
    value: object,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if not allow_empty and not value:
        raise ValueError(f"{field} must be non-empty")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_text(item, f"{field}[{index}]"))
    return tuple(result)


def _integer_vector(
    value: object,
    field: str,
    *,
    ndim: int,
) -> tuple[int, ...]:
    if type(value) is not tuple or len(value) != ndim:
        raise ValueError(f"{field} dimension mismatch")
    result: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise TypeError(f"{field}[{index}] must be an int")
        result.append(item)
    return tuple(result)


def _require_exact_record_fields(
    record: object,
    record_type: type[object],
    field: str,
) -> None:
    if type(record) is not record_type:
        raise TypeError(f"{field} has the wrong record type")
    expected = frozenset(record_type.__dataclass_fields__)
    try:
        observed = frozenset(vars(record))
    except TypeError as exc:
        raise TypeError(f"{field} has no strict record body") from exc
    if observed != expected:
        raise ValueError(
            f"{field} fields are not exact: "
            f"missing={sorted(expected - observed)!r}, "
            f"unknown={sorted(observed - expected)!r}"
        )


def _bounded_tuple(
    value: object,
    field: str,
    cap: int,
) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if len(value) > cap:
        raise ValueError(f"{field} exceeds point cap")
    return value


def _preflight_spatial_dimension(
    ndim: object,
    dimension_values: tuple[object, ...],
    field: str,
    *,
    _ndim_cap: int = _GENERAL_EVIDENCE_SPATIAL_NDIM_MAX,
    _type=type,
    _int_type=int,
    _tuple_type=tuple,
    _enumerate=enumerate,
    _len=len,
    _type_error=TypeError,
    _value_error=ValueError,
) -> int:
    if _type(ndim) is not _int_type:
        raise _type_error(f"{field} dimension must be an int")
    if ndim <= 0:
        raise _value_error(f"{field} dimension must be positive")
    if ndim > _ndim_cap:
        raise _value_error(f"{field} dimension exceeds resource cap")
    for index, value in _enumerate(dimension_values):
        if _type(value) is not _tuple_type:
            raise _type_error(f"{field}[{index}] must be a tuple")
        if _len(value) > _ndim_cap:
            raise _value_error(f"{field} dimension exceeds resource cap")
    return ndim


def _preflight_vector_dimension(
    value: object,
    ndim: int,
    field: str,
    *,
    _ndim_cap: int = _GENERAL_EVIDENCE_SPATIAL_NDIM_MAX,
    _type=type,
    _tuple_type=tuple,
    _len=len,
    _type_error=TypeError,
    _value_error=ValueError,
) -> None:
    if _type(value) is not _tuple_type:
        raise _type_error(f"{field} must be a tuple")
    if _len(value) > _ndim_cap:
        raise _value_error(f"{field} dimension exceeds resource cap")
    if _len(value) != ndim:
        raise _value_error(f"{field} dimension mismatch")


def _preflight_general_evidence_value(
    value: object,
    field: str,
    *,
    byte_cap: int = _FROZEN_GENERAL_EVIDENCE_BODY_BYTES_MAX,
    text_bytes_cap: int = _GENERAL_EVIDENCE_TEXT_BYTES_MAX,
    max_depth: int = _GENERAL_EVIDENCE_MAX_DEPTH,
    _body_cap_checker=preflight_general_evidence_body,
    _frozen_body_cap: int = _FROZEN_GENERAL_EVIDENCE_BODY_BYTES_MAX,
    _type=type,
    _int_type=int,
    _bool_type=bool,
    _str_type=str,
    _float_type=float,
    _tuple_type=tuple,
    _list_type=list,
    _set_type=set,
    _iter=iter,
    _next=next,
    _len=len,
    _max=max,
    _ord=ord,
    _id=id,
    _hasattr=hasattr,
    _isinstance=isinstance,
    _enum_type=Enum,
    _vars=vars,
    _isfinite=math.isfinite,
    _stop_iteration=StopIteration,
    _type_error=TypeError,
    _value_error=ValueError,
) -> int:
    """Stream a conservative canonical-JSON upper bound without a payload copy."""

    if _type(byte_cap) is not _int_type or byte_cap <= 0:
        raise _value_error("general evidence byte cap must be positive")
    if byte_cap > _frozen_body_cap:
        byte_cap = _frozen_body_cap
    used = 0

    def charge(amount: int) -> None:
        nonlocal used
        used += amount
        if used > byte_cap:
            raise _value_error(
                f"{field} serialized body exceeds resource cap"
            )

    def utf8_byte_length(text: str) -> int:
        length = 0
        for character in text:
            codepoint = _ord(character)
            if codepoint <= 0x7F:
                length += 1
            elif codepoint <= 0x7FF:
                length += 2
            elif 0xD800 <= codepoint <= 0xDFFF:
                raise _value_error(
                    f"{field} contains invalid UTF-8 text"
                )
            elif codepoint <= 0xFFFF:
                length += 3
            else:
                length += 4
            if length > text_bytes_cap:
                raise _value_error(
                    f"{field} text exceeds resource cap"
                )
        return length

    stack: list[tuple[object, int | None]] = _list_type(
        ((_iter((value,)), None),)
    )
    active: set[int] = _set_type()
    while stack:
        iterator, container_id = stack[-1]
        try:
            item = _next(iterator)  # type: ignore[arg-type]
        except _stop_iteration:
            stack.pop()
            if container_id is not None:
                active.remove(container_id)
            continue
        item_type = _type(item)
        if item is None:
            charge(4)
        elif _isinstance(item, _enum_type):
            if _len(stack) >= max_depth:
                raise _value_error(
                    f"{field} nesting exceeds resource cap"
                )
            stack.append((_iter((item.value,)), None))
        elif item_type is _bool_type:
            charge(5)
        elif item_type is _str_type:
            utf8_byte_length(item)
            text_length = _len(item)
            charge(2 + 6 * text_length)
        elif item_type is _int_type:
            bits = item.bit_length()
            digits_upper = _max(
                1,
                (bits * 30_103 + 99_999) // 100_000 + 1,
            )
            charge(digits_upper + (1 if item < 0 else 0))
        elif item_type is _float_type:
            if not _isfinite(item):
                raise _value_error(
                    f"{field} contains a non-finite float"
                )
            charge(32)
        elif item_type is _tuple_type:
            if _len(stack) >= max_depth:
                raise _value_error(
                    f"{field} nesting exceeds resource cap"
                )
            item_id = _id(item)
            if item_id in active:
                raise _value_error(
                    f"{field} contains a cyclic record"
                )
            active.add(item_id)
            charge(2 + _max(0, _len(item) - 1))
            stack.append((_iter(item), item_id))
        elif _hasattr(item_type, "__dataclass_fields__"):
            try:
                body = _vars(item)
            except _type_error as exc:
                raise _type_error(
                    f"{field} record has no strict body"
                ) from exc
            if _len(stack) >= max_depth:
                raise _value_error(
                    f"{field} nesting exceeds resource cap"
                )
            item_id = _id(item)
            if item_id in active:
                raise _value_error(
                    f"{field} contains a cyclic record"
                )
            active.add(item_id)
            charge(2 + _max(0, _len(body) - 1))
            for key in body:
                if _type(key) is not _str_type:
                    raise _type_error(
                        f"{field} record key must be a string"
                    )
                utf8_byte_length(key)
                key_length = _len(key)
                charge(3 + 6 * key_length)
            stack.append((_iter(body.values()), item_id))
        else:
            raise _type_error(
                f"{field} contains an unsupported evidence value"
            )
    _body_cap_checker(used)
    return used


def _preflight_direction_collections(
    direction: DirectionManifest,
) -> None:
    _require_exact_record_fields(
        direction,
        DirectionManifest,
        "direction_manifest",
    )
    for field, label in (
        ("direction_ids", "response directions"),
        ("primitive_directions", "response directions"),
        ("path_ids", "response direction paths"),
        ("ordered_paths", "response direction paths"),
        ("closure_path_pairs", "response closures"),
    ):
        _bounded_tuple(
            getattr(direction, field),
            label,
            RESPONSE_GRID_MAX_POINT_COUNT,
        )
    total = 0
    for path in direction.ordered_paths:
        if type(path) is not tuple:
            raise TypeError("response ordered_paths entries must be tuples")
        total += len(path)
        if total > RESPONSE_GRID_MAX_POINT_COUNT:
            raise ValueError(
                "response direction paths exceed point cap"
            )


@dataclass(frozen=True)
class DirectionManifest:
    direction_schema_version: str
    direction_ids: tuple[str, ...]
    primitive_directions: tuple[tuple[int, ...], ...]
    path_ids: tuple[str, ...]
    ordered_paths: tuple[tuple[tuple[int, ...], ...], ...]
    closure_path_pairs: tuple[DirectionPathClosure, ...]
    direction_manifest_sha: str

    def __post_init__(self) -> None:
        _text(self.direction_schema_version, "direction_schema_version")
        _string_tuple(self.direction_ids, "direction_ids")
        if type(self.primitive_directions) is not tuple:
            raise TypeError("primitive_directions must be a tuple")
        _string_tuple(self.path_ids, "path_ids")
        if type(self.ordered_paths) is not tuple:
            raise TypeError("ordered_paths must be a tuple")
        if type(self.closure_path_pairs) is not tuple:
            raise TypeError("closure_path_pairs must be a tuple")
        if not all(
            type(item) is DirectionPathClosure
            for item in self.closure_path_pairs
        ):
            raise TypeError(
                "closure_path_pairs must contain DirectionPathClosure records"
            )
        _sha(self.direction_manifest_sha, "direction_manifest_sha")


@dataclass(frozen=True)
class ResponseKGridManifest:
    grid_schema_version: str
    qualification_profile: Literal[
        "directional-momentum-shell-path-v1"
    ]
    spatial_ndim: int
    torus_denominators: tuple[int, ...]
    reciprocal_indices: tuple[tuple[int, ...], ...]
    direction_manifest: DirectionManifest
    response_grid_sha: str

    def __post_init__(self) -> None:
        _text(self.grid_schema_version, "grid_schema_version")
        if (
            self.qualification_profile
            != "directional-momentum-shell-path-v1"
        ):
            raise ValueError("qualification_profile is not closed")
        ndim = _positive_int(self.spatial_ndim, "spatial_ndim")
        denominators = _positive_tuple(
            self.torus_denominators,
            "torus_denominators",
        )
        if len(denominators) != ndim:
            raise ValueError("torus_denominators dimension mismatch")
        if len(self.reciprocal_indices) > RESPONSE_GRID_MAX_POINT_COUNT:
            raise ValueError("response grid exceeds point cap")
        _indices(
            self.reciprocal_indices,
            "reciprocal_indices",
            denominators,
        )
        if type(self.direction_manifest) is not DirectionManifest:
            raise TypeError(
                "direction_manifest must be a DirectionManifest"
            )
        _sha(self.response_grid_sha, "response_grid_sha")


@dataclass(frozen=True)
class DynamicsKGridManifest:
    grid_schema_version: str
    qualification_profile: Literal[
        "exact-offset-zero-v1",
        "cartesian-full-64-v1",
    ]
    spatial_ndim: int
    torus_denominators: tuple[int, ...]
    reciprocal_indices: tuple[tuple[int, ...], ...]
    dynamics_grid_sha: str

    def __post_init__(self) -> None:
        _text(self.grid_schema_version, "grid_schema_version")
        if self.qualification_profile not in (
            "exact-offset-zero-v1",
            "cartesian-full-64-v1",
        ):
            raise ValueError("qualification_profile is not closed")
        ndim = _positive_int(self.spatial_ndim, "spatial_ndim")
        denominators = _positive_tuple(
            self.torus_denominators,
            "torus_denominators",
        )
        if len(denominators) != ndim:
            raise ValueError("torus_denominators dimension mismatch")
        _indices(
            self.reciprocal_indices,
            "reciprocal_indices",
            denominators,
        )
        _sha(self.dynamics_grid_sha, "dynamics_grid_sha")


@dataclass(frozen=True)
class BridgeKGridManifest:
    grid_schema_version: str
    spatial_shape: tuple[int, ...]
    torus_denominators: tuple[int, ...]
    reciprocal_indices: tuple[tuple[int, ...], ...]
    bridge_grid_sha: str

    def __post_init__(self) -> None:
        _text(self.grid_schema_version, "grid_schema_version")
        shape = _positive_tuple(self.spatial_shape, "spatial_shape")
        denominators = _positive_tuple(
            self.torus_denominators,
            "torus_denominators",
        )
        if denominators != shape:
            raise ValueError(
                "bridge torus_denominators must equal spatial_shape"
            )
        _indices(
            self.reciprocal_indices,
            "reciprocal_indices",
            denominators,
        )
        if len(self.reciprocal_indices) > BRIDGE_GRID_MAX_POINT_COUNT:
            raise ValueError("bridge grid exceeds point cap")
        _sha(self.bridge_grid_sha, "bridge_grid_sha")


def dynamics_grid_payload(
    grid: DynamicsKGridManifest,
) -> dict[str, object]:
    if type(grid) is not DynamicsKGridManifest:
        raise TypeError("grid must be a DynamicsKGridManifest")
    return {
        "grid_schema_version": grid.grid_schema_version,
        "qualification_profile": grid.qualification_profile,
        "spatial_ndim": grid.spatial_ndim,
        "torus_denominators": list(grid.torus_denominators),
        "reciprocal_indices": [
            list(item) for item in grid.reciprocal_indices
        ],
    }


def _closure_payload(closure: DirectionPathClosure) -> dict[str, object]:
    if type(closure) is not DirectionPathClosure:
        raise TypeError("closure must be a DirectionPathClosure")
    return {
        "closure_id": closure.closure_id,
        "first_path_id": closure.first_path_id,
        "first_path_position": closure.first_path_position,
        "second_path_id": closure.second_path_id,
        "second_path_position": closure.second_path_position,
        "reciprocal_index": list(closure.reciprocal_index),
    }


def direction_manifest_payload(
    manifest: DirectionManifest,
) -> dict[str, object]:
    if type(manifest) is not DirectionManifest:
        raise TypeError("manifest must be a DirectionManifest")
    return {
        "direction_schema_version": manifest.direction_schema_version,
        "direction_ids": list(manifest.direction_ids),
        "primitive_directions": [
            list(item) for item in manifest.primitive_directions
        ],
        "path_ids": list(manifest.path_ids),
        "ordered_paths": [
            [list(point) for point in path]
            for path in manifest.ordered_paths
        ],
        "closure_path_pairs": [
            _closure_payload(item) for item in manifest.closure_path_pairs
        ],
    }


def _direction_record(
    manifest: DirectionManifest,
) -> dict[str, object]:
    return {
        **direction_manifest_payload(manifest),
        "direction_manifest_sha": manifest.direction_manifest_sha,
    }


def response_grid_payload(
    grid: ResponseKGridManifest,
) -> dict[str, object]:
    if type(grid) is not ResponseKGridManifest:
        raise TypeError("grid must be a ResponseKGridManifest")
    return {
        "grid_schema_version": grid.grid_schema_version,
        "qualification_profile": grid.qualification_profile,
        "spatial_ndim": grid.spatial_ndim,
        "torus_denominators": list(grid.torus_denominators),
        "reciprocal_indices": [
            list(item) for item in grid.reciprocal_indices
        ],
        "direction_manifest": _direction_record(
            grid.direction_manifest
        ),
    }


def bridge_grid_payload(
    grid: BridgeKGridManifest,
) -> dict[str, object]:
    if type(grid) is not BridgeKGridManifest:
        raise TypeError("grid must be a BridgeKGridManifest")
    return {
        "grid_schema_version": grid.grid_schema_version,
        "spatial_shape": list(grid.spatial_shape),
        "torus_denominators": list(grid.torus_denominators),
        "reciprocal_indices": [
            list(item) for item in grid.reciprocal_indices
        ],
    }


def _preflight_application_grid_body(
    application: V3M0SyntheticControlApplicationSpec,
) -> SyntheticApplicationGridProtocol:
    _require_exact_record_fields(
        application,
        V3M0SyntheticControlApplicationSpec,
        "application",
    )
    protocol = application.grid_protocol
    _require_exact_record_fields(
        protocol,
        SyntheticApplicationGridProtocol,
        "application grid_protocol",
    )
    _bounded_tuple(
        protocol.response_reciprocal_indices,
        "response grid",
        RESPONSE_GRID_MAX_POINT_COUNT,
    )
    for field, label in (
        ("direction_ids", "response directions"),
        ("primitive_directions", "response directions"),
        ("path_ids", "response direction paths"),
        ("ordered_paths", "response direction paths"),
        ("closure_path_pairs", "response closures"),
        ("preregistered_phase_bands", "response phase bands"),
    ):
        _bounded_tuple(
            getattr(protocol, field),
            label,
            RESPONSE_GRID_MAX_POINT_COUNT,
        )
    total = 0
    for path in protocol.ordered_paths:
        if type(path) is not tuple:
            raise TypeError("response ordered_paths entries must be tuples")
        total += len(path)
        if total > RESPONSE_GRID_MAX_POINT_COUNT:
            raise ValueError(
                "response direction paths exceed point cap"
            )
    _bounded_tuple(
        protocol.bridge_reciprocal_indices,
        "application bridge grid",
        BRIDGE_GRID_MAX_POINT_COUNT,
    )
    _bounded_tuple(
        protocol.bridge_steps,
        "application bridge steps",
        16_384,
    )
    for closure in protocol.closure_path_pairs:
        _require_exact_record_fields(
            closure,
            DirectionPathClosure,
            "application direction closure",
        )
    ndim = _preflight_spatial_dimension(
        protocol.spatial_ndim,
        (
            protocol.spatial_shape,
            protocol.response_torus_denominators,
        ),
        "application grid",
    )
    for index, point in enumerate(protocol.response_reciprocal_indices):
        _preflight_vector_dimension(
            point,
            ndim,
            f"application response point[{index}]",
        )
    for index, direction in enumerate(protocol.primitive_directions):
        _preflight_vector_dimension(
            direction,
            ndim,
            f"application primitive direction[{index}]",
        )
    for path_index, path in enumerate(protocol.ordered_paths):
        for point_index, point in enumerate(path):
            _preflight_vector_dimension(
                point,
                ndim,
                f"application path[{path_index}][{point_index}]",
            )
    for index, closure in enumerate(protocol.closure_path_pairs):
        _preflight_vector_dimension(
            closure.reciprocal_index,
            ndim,
            f"application closure[{index}]",
        )
    for index, point in enumerate(protocol.bridge_reciprocal_indices):
        _preflight_vector_dimension(
            point,
            ndim,
            f"application bridge point[{index}]",
        )
    _preflight_vector_dimension(
        protocol.reference_reciprocal_index,
        ndim,
        "application reference point",
    )
    _preflight_general_evidence_value(
        application,
        "application grid evidence",
    )
    return protocol


def _preflight_application_grid(
    application: V3M0SyntheticControlApplicationSpec,
) -> SyntheticApplicationGridProtocol:
    protocol = _preflight_application_grid_body(application)
    verify_synthetic_control_application_spec(application)
    return protocol


def _preflight_raw_response_grid(
    grid: ResponseKGridManifest,
) -> None:
    _require_exact_record_fields(
        grid,
        ResponseKGridManifest,
        "response grid",
    )
    _bounded_tuple(
        grid.reciprocal_indices,
        "response grid",
        RESPONSE_GRID_MAX_POINT_COUNT,
    )
    direction = grid.direction_manifest
    _preflight_direction_collections(direction)
    for closure in direction.closure_path_pairs:
        _require_exact_record_fields(
            closure,
            DirectionPathClosure,
            "response direction closure",
        )
    ndim = _preflight_spatial_dimension(
        grid.spatial_ndim,
        (grid.torus_denominators,),
        "response grid",
    )
    for index, point in enumerate(grid.reciprocal_indices):
        _preflight_vector_dimension(
            point,
            ndim,
            f"response grid point[{index}]",
        )
    for index, primitive in enumerate(direction.primitive_directions):
        _preflight_vector_dimension(
            primitive,
            ndim,
            f"response primitive direction[{index}]",
        )
    for path_index, path in enumerate(direction.ordered_paths):
        for point_index, point in enumerate(path):
            _preflight_vector_dimension(
                point,
                ndim,
                f"response path[{path_index}][{point_index}]",
            )
    for index, closure in enumerate(direction.closure_path_pairs):
        _preflight_vector_dimension(
            closure.reciprocal_index,
            ndim,
            f"response closure[{index}]",
        )
    _preflight_general_evidence_value(
        grid,
        "response grid evidence",
    )


def _preflight_raw_bridge_grid(
    grid: BridgeKGridManifest,
    field: str,
) -> None:
    _require_exact_record_fields(
        grid,
        BridgeKGridManifest,
        field,
    )
    _bounded_tuple(
        grid.reciprocal_indices,
        field,
        BRIDGE_GRID_MAX_POINT_COUNT,
    )
    ndim = _preflight_spatial_dimension(
        len(grid.spatial_shape)
        if type(grid.spatial_shape) is tuple
        else grid.spatial_shape,
        (grid.spatial_shape, grid.torus_denominators),
        field,
    )
    for index, point in enumerate(grid.reciprocal_indices):
        _preflight_vector_dimension(
            point,
            ndim,
            f"{field} point[{index}]",
        )
    _preflight_general_evidence_value(
        grid,
        f"{field} evidence",
    )


def _preflight_raw_dynamics_grid(
    grid: DynamicsKGridManifest,
) -> None:
    _require_exact_record_fields(
        grid,
        DynamicsKGridManifest,
        "dynamics grid",
    )
    _bounded_tuple(
        grid.reciprocal_indices,
        "dynamics grid",
        DYNAMICS_GRID_MAX_POINT_COUNT,
    )
    ndim = _preflight_spatial_dimension(
        grid.spatial_ndim,
        (grid.torus_denominators,),
        "dynamics grid",
    )
    for index, point in enumerate(grid.reciprocal_indices):
        _preflight_vector_dimension(
            point,
            ndim,
            f"dynamics grid point[{index}]",
        )
    _preflight_general_evidence_value(
        grid,
        "dynamics grid evidence",
    )


def _preflight_support(
    value: object,
    field: str,
) -> int:
    support = _bounded_tuple(
        value,
        field,
        DYNAMICS_GRID_MAX_POINT_COUNT,
    )
    if not support:
        raise ValueError(f"{field} must be non-empty")
    first = support[0]
    if type(first) is not tuple:
        raise TypeError(f"{field}[0] must be a tuple")
    ndim = _preflight_spatial_dimension(
        len(first),
        (first,),
        field,
    )
    for index, row in enumerate(support):
        _preflight_vector_dimension(
            row,
            ndim,
            f"{field}[{index}]",
        )
    _preflight_general_evidence_value(
        support,
        f"{field} evidence",
    )
    return ndim


def _preflight_shape_and_support(
    spatial_shape: object,
    signed_support: object,
) -> None:
    if type(spatial_shape) is not tuple:
        raise TypeError("spatial_shape must be a tuple")
    ndim = _preflight_spatial_dimension(
        len(spatial_shape),
        (spatial_shape,),
        "bridge input",
    )
    support_ndim = _preflight_support(
        signed_support,
        "signed_support",
    )
    if support_ndim != ndim:
        raise ValueError("signed_support dimension mismatch")
    _preflight_general_evidence_value(
        (spatial_shape, signed_support),
        "bridge input evidence",
    )


def _verify_direction_manifest(
    manifest: DirectionManifest,
    denominators: tuple[int, ...],
    reciprocal_indices: tuple[tuple[int, ...], ...],
) -> DirectionManifest:
    _preflight_direction_collections(manifest)
    manifest.__post_init__()
    if manifest.direction_schema_version != DIRECTION_MANIFEST_SCHEMA_VERSION:
        raise ValueError("unexpected direction manifest schema")
    if tuple(DirectionManifest.__dataclass_fields__) != (
        "direction_schema_version",
        "direction_ids",
        "primitive_directions",
        "path_ids",
        "ordered_paths",
        "closure_path_pairs",
        "direction_manifest_sha",
    ):
        raise RuntimeError("direction manifest field registry is incomplete")
    ndim = len(denominators)
    direction_ids = _string_tuple(
        manifest.direction_ids,
        "direction_ids",
    )
    if direction_ids != tuple(sorted(set(direction_ids))):
        raise ValueError("direction_ids must be unique and canonical")
    if len(direction_ids) != len(manifest.primitive_directions):
        raise ValueError(
            "direction_ids and primitive_directions must align"
        )
    for index, direction in enumerate(manifest.primitive_directions):
        checked = _integer_vector(
            direction,
            f"primitive_directions[{index}]",
            ndim=ndim,
        )
        if not any(checked):
            raise ValueError("primitive_directions must be nonzero")
    path_ids = _string_tuple(manifest.path_ids, "path_ids")
    if path_ids != tuple(sorted(set(path_ids))):
        raise ValueError("path_ids must be unique and canonical")
    if len(path_ids) != len(manifest.ordered_paths):
        raise ValueError("path_ids and ordered_paths must align")
    point_set = frozenset(reciprocal_indices)
    path_lookup: dict[str, tuple[tuple[int, ...], ...]] = {}
    for path_id, path in zip(path_ids, manifest.ordered_paths):
        if type(path) is not tuple or not path:
            raise ValueError("ordered_paths entries must be non-empty tuples")
        checked_path = tuple(
            _integer_vector(
                point,
                f"ordered_paths[{path_id}][{index}]",
                ndim=ndim,
            )
            for index, point in enumerate(path)
        )
        if any(point not in point_set for point in checked_path):
            raise ValueError("ordered_paths must use response grid points")
        path_lookup[path_id] = checked_path
    closure_ids: list[str] = []
    for closure in manifest.closure_path_pairs:
        _require_exact_record_fields(
            closure,
            DirectionPathClosure,
            "direction closure",
        )
        closure.__post_init__()
        closure_ids.append(_text(closure.closure_id, "closure_id"))
        if (
            closure.first_path_id not in path_lookup
            or closure.second_path_id not in path_lookup
        ):
            raise ValueError("closure references a missing path")
        first = path_lookup[closure.first_path_id]
        second = path_lookup[closure.second_path_id]
        if not 0 <= closure.first_path_position < len(first):
            raise ValueError("closure first position is out of range")
        if not 0 <= closure.second_path_position < len(second):
            raise ValueError("closure second position is out of range")
        index = _integer_vector(
            closure.reciprocal_index,
            "closure.reciprocal_index",
            ndim=ndim,
        )
        if (
            first[closure.first_path_position] != index
            or second[closure.second_path_position] != index
        ):
            raise ValueError("closure paths do not meet at reciprocal_index")
    if tuple(closure_ids) != tuple(sorted(set(closure_ids))):
        raise ValueError("closure IDs must be unique and canonical")
    if manifest.direction_manifest_sha != canonical_sha(
        direction_manifest_payload(manifest)
    ):
        raise ValueError(
            "direction_manifest_sha does not match complete body"
        )
    return manifest


def _expected_response_grid(
    application: V3M0SyntheticControlApplicationSpec,
) -> ResponseKGridManifest:
    protocol = _preflight_application_grid(application)
    provisional_direction = DirectionManifest(
        direction_schema_version=DIRECTION_MANIFEST_SCHEMA_VERSION,
        direction_ids=protocol.direction_ids,
        primitive_directions=protocol.primitive_directions,
        path_ids=protocol.path_ids,
        ordered_paths=protocol.ordered_paths,
        closure_path_pairs=protocol.closure_path_pairs,
        direction_manifest_sha="0" * 64,
    )
    direction = replace(
        provisional_direction,
        direction_manifest_sha=canonical_sha(
            direction_manifest_payload(provisional_direction)
        ),
    )
    provisional = ResponseKGridManifest(
        grid_schema_version=RESPONSE_GRID_SCHEMA_VERSION,
        qualification_profile="directional-momentum-shell-path-v1",
        spatial_ndim=protocol.spatial_ndim,
        torus_denominators=protocol.response_torus_denominators,
        reciprocal_indices=protocol.response_reciprocal_indices,
        direction_manifest=direction,
        response_grid_sha="0" * 64,
    )
    return replace(
        provisional,
        response_grid_sha=canonical_sha(response_grid_payload(provisional)),
    )


def build_response_grid_manifest(
    application: V3M0SyntheticControlApplicationSpec,
) -> ResponseKGridManifest:
    """Build the unique directional grid from a closed application spec."""

    return _expected_response_grid(application)


def verify_response_grid_manifest(
    grid: ResponseKGridManifest,
    application: V3M0SyntheticControlApplicationSpec,
) -> ResponseKGridManifest:
    _preflight_raw_response_grid(grid)
    _preflight_application_grid_body(application)
    grid.__post_init__()
    if grid.grid_schema_version != RESPONSE_GRID_SCHEMA_VERSION:
        raise ValueError("unexpected response grid schema")
    if tuple(ResponseKGridManifest.__dataclass_fields__) != (
        "grid_schema_version",
        "qualification_profile",
        "spatial_ndim",
        "torus_denominators",
        "reciprocal_indices",
        "direction_manifest",
        "response_grid_sha",
    ):
        raise RuntimeError("response grid field registry is incomplete")
    _verify_direction_manifest(
        grid.direction_manifest,
        grid.torus_denominators,
        grid.reciprocal_indices,
    )
    if grid.response_grid_sha != canonical_sha(response_grid_payload(grid)):
        raise ValueError("response_grid_sha does not match complete body")
    expected = _expected_response_grid(application)
    if grid != expected:
        raise ValueError(
            "response grid is not the unique application-derived grid"
        )
    return grid


def _expected_application_bridge_grid(
    application: V3M0SyntheticControlApplicationSpec,
) -> BridgeKGridManifest:
    protocol = _preflight_application_grid(application)
    provisional = BridgeKGridManifest(
        grid_schema_version=BRIDGE_GRID_SCHEMA_VERSION,
        spatial_shape=protocol.spatial_shape,
        torus_denominators=protocol.spatial_shape,
        reciprocal_indices=protocol.bridge_reciprocal_indices,
        bridge_grid_sha="0" * 64,
    )
    return replace(
        provisional,
        bridge_grid_sha=canonical_sha(bridge_grid_payload(provisional)),
    )


def build_application_bridge_grid_manifest(
    application: V3M0SyntheticControlApplicationSpec,
) -> BridgeKGridManifest:
    """Build the source/readout bridge grid frozen by an application spec."""

    return _expected_application_bridge_grid(application)


def verify_application_bridge_grid_manifest(
    grid: BridgeKGridManifest,
    application: V3M0SyntheticControlApplicationSpec,
) -> BridgeKGridManifest:
    _preflight_raw_bridge_grid(
        grid,
        "application bridge grid",
    )
    _preflight_application_grid_body(application)
    grid.__post_init__()
    if grid.grid_schema_version != BRIDGE_GRID_SCHEMA_VERSION:
        raise ValueError("unexpected bridge grid schema")
    if grid.bridge_grid_sha != canonical_sha(bridge_grid_payload(grid)):
        raise ValueError("bridge_grid_sha does not match complete body")
    expected = _expected_application_bridge_grid(application)
    if grid != expected:
        raise ValueError(
            "bridge grid is not the unique application-derived grid"
        )
    return grid


def _expected_dynamics_grid(
    transition_support: tuple[tuple[int, ...], ...],
    metric_support: tuple[tuple[int, ...], ...],
) -> DynamicsKGridManifest:
    transition_ndim = _preflight_support(
        transition_support,
        "transition_support",
    )
    metric_ndim = _preflight_support(
        metric_support,
        "metric_support",
    )
    if metric_ndim != transition_ndim:
        raise ValueError("metric_support dimension mismatch")
    _preflight_general_evidence_value(
        (transition_support, metric_support),
        "dynamics support evidence",
    )
    transition = _signed_support(
        transition_support,
        "transition_support",
    )
    ndim = len(transition[0])
    metric = _signed_support(
        metric_support,
        "metric_support",
        ndim=ndim,
    )
    zero = _is_zero_support(transition) and _is_zero_support(metric)
    if zero:
        profile: Literal[
            "exact-offset-zero-v1",
            "cartesian-full-64-v1",
        ] = "exact-offset-zero-v1"
        denominators = (1,) * ndim
        points = ((0,) * ndim,)
    else:
        profile = "cartesian-full-64-v1"
        point_count = DYNAMICS_GRID_DENOMINATOR**ndim
        if point_count > DYNAMICS_GRID_MAX_POINT_COUNT:
            raise ValueError(
                "full-64 dynamics grid exceeds allocation point cap"
            )
        denominators = (DYNAMICS_GRID_DENOMINATOR,) * ndim
        points = tuple(
            itertools.product(
                range(DYNAMICS_GRID_DENOMINATOR),
                repeat=ndim,
            )
        )
    provisional = DynamicsKGridManifest(
        grid_schema_version=DYNAMICS_GRID_SCHEMA_VERSION,
        qualification_profile=profile,
        spatial_ndim=ndim,
        torus_denominators=denominators,
        reciprocal_indices=points,
        dynamics_grid_sha="0" * 64,
    )
    _preflight_raw_dynamics_grid(provisional)
    return replace(
        provisional,
        dynamics_grid_sha=canonical_sha(
            dynamics_grid_payload(provisional)
        ),
    )


def build_dynamics_grid_manifest(
    transition_support: tuple[tuple[int, ...], ...],
    metric_support: tuple[tuple[int, ...], ...],
) -> DynamicsKGridManifest:
    """Build the exact singleton or complete denominator-64 Cartesian grid."""

    return _expected_dynamics_grid(transition_support, metric_support)


def verify_dynamics_grid_manifest(
    grid: DynamicsKGridManifest,
    transition_support: tuple[tuple[int, ...], ...],
    metric_support: tuple[tuple[int, ...], ...],
) -> DynamicsKGridManifest:
    _preflight_raw_dynamics_grid(grid)
    transition_ndim = _preflight_support(
        transition_support,
        "transition_support",
    )
    metric_ndim = _preflight_support(metric_support, "metric_support")
    if transition_ndim != metric_ndim:
        raise ValueError("metric_support dimension mismatch")
    _preflight_general_evidence_value(
        (transition_support, metric_support),
        "dynamics support evidence",
    )
    grid.__post_init__()
    if grid.grid_schema_version != DYNAMICS_GRID_SCHEMA_VERSION:
        raise ValueError("unexpected dynamics grid schema")
    if grid.dynamics_grid_sha != canonical_sha(dynamics_grid_payload(grid)):
        raise ValueError("dynamics_grid_sha does not match complete body")
    expected = _expected_dynamics_grid(
        transition_support,
        metric_support,
    )
    if grid != expected:
        raise ValueError("dynamics grid is not the unique support-derived grid")
    return grid


def _expected_bridge_grid(
    spatial_shape: tuple[int, ...],
    signed_support: tuple[tuple[int, ...], ...],
) -> BridgeKGridManifest:
    _preflight_shape_and_support(spatial_shape, signed_support)
    shape = _positive_tuple(spatial_shape, "spatial_shape")
    support = _signed_support(
        signed_support,
        "signed_support",
        ndim=len(shape),
    )
    origin = (0,) * len(shape)
    points: set[tuple[int, ...]] = {origin}
    for axis, length in enumerate(shape):
        active = any(offset[axis] != 0 for offset in support)
        if not active:
            continue
        if length < 3:
            raise ValueError(
                "active bridge axes require L_i >= 3 (non-Nyquist)"
            )
        positive = [0] * len(shape)
        negative = [0] * len(shape)
        positive[axis] = 1
        negative[axis] = length - 1
        points.add(tuple(positive))
        points.add(tuple(negative))
    if len(points) > BRIDGE_GRID_MAX_POINT_COUNT:
        raise ValueError("bridge grid exceeds point cap")
    provisional = BridgeKGridManifest(
        grid_schema_version=BRIDGE_GRID_SCHEMA_VERSION,
        spatial_shape=shape,
        torus_denominators=shape,
        reciprocal_indices=tuple(sorted(points)),
        bridge_grid_sha="0" * 64,
    )
    _preflight_raw_bridge_grid(provisional, "bridge grid")
    return replace(
        provisional,
        bridge_grid_sha=canonical_sha(bridge_grid_payload(provisional)),
    )


def build_bridge_grid_manifest(
    spatial_shape: tuple[int, ...],
    signed_support: tuple[tuple[int, ...], ...],
) -> BridgeKGridManifest:
    """Build origin plus the support-active axial ±1 periodic neighbors."""

    return _expected_bridge_grid(spatial_shape, signed_support)


def verify_bridge_grid_manifest(
    grid: BridgeKGridManifest,
    spatial_shape: tuple[int, ...],
    signed_support: tuple[tuple[int, ...], ...],
) -> BridgeKGridManifest:
    _preflight_raw_bridge_grid(grid, "bridge grid")
    _preflight_shape_and_support(spatial_shape, signed_support)
    grid.__post_init__()
    if grid.grid_schema_version != BRIDGE_GRID_SCHEMA_VERSION:
        raise ValueError("unexpected bridge grid schema")
    if grid.bridge_grid_sha != canonical_sha(bridge_grid_payload(grid)):
        raise ValueError("bridge_grid_sha does not match complete body")
    expected = _expected_bridge_grid(spatial_shape, signed_support)
    if grid != expected:
        raise ValueError("bridge grid is not the unique support-derived grid")
    return grid


def _freeze_grid_authority_functions(
    *roots: FunctionType,
) -> tuple[FunctionType, ...]:
    """Detach authority-critical grid call graphs from module rebinding."""

    cache: dict[int, FunctionType] = {}
    module_name = __name__

    def freeze_value(value):
        if (
            type(value) is FunctionType
            and value.__module__ == module_name
        ):
            return freeze_function(value)
        if type(value) is tuple:
            return tuple(freeze_value(item) for item in value)
        if type(value) is dict:
            return {
                key: freeze_value(item)
                for key, item in value.items()
            }
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
            if (
                type(value) is FunctionType
                and value.__module__ == module_name
            ):
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
    direction_manifest_payload,
    response_grid_payload,
    bridge_grid_payload,
    dynamics_grid_payload,
    build_response_grid_manifest,
    verify_response_grid_manifest,
    build_application_bridge_grid_manifest,
    verify_application_bridge_grid_manifest,
    build_dynamics_grid_manifest,
    verify_dynamics_grid_manifest,
    build_bridge_grid_manifest,
    verify_bridge_grid_manifest,
) = _freeze_grid_authority_functions(
    direction_manifest_payload,
    response_grid_payload,
    bridge_grid_payload,
    dynamics_grid_payload,
    build_response_grid_manifest,
    verify_response_grid_manifest,
    build_application_bridge_grid_manifest,
    verify_application_bridge_grid_manifest,
    build_dynamics_grid_manifest,
    verify_dynamics_grid_manifest,
    build_bridge_grid_manifest,
    verify_bridge_grid_manifest,
)


__all__ = [
    "BRIDGE_GRID_SCHEMA_VERSION",
    "BRIDGE_GRID_MAX_POINT_COUNT",
    "DIRECTION_MANIFEST_SCHEMA_VERSION",
    "DYNAMICS_GRID_DENOMINATOR",
    "DYNAMICS_GRID_MAX_POINT_COUNT",
    "DYNAMICS_GRID_SCHEMA_VERSION",
    "RESPONSE_GRID_MAX_POINT_COUNT",
    "RESPONSE_GRID_SCHEMA_VERSION",
    "BridgeKGridManifest",
    "DirectionManifest",
    "DirectionPathClosure",
    "DynamicsKGridManifest",
    "ResponseKGridManifest",
    "bridge_grid_payload",
    "build_application_bridge_grid_manifest",
    "build_bridge_grid_manifest",
    "build_dynamics_grid_manifest",
    "build_response_grid_manifest",
    "direction_manifest_payload",
    "dynamics_grid_payload",
    "response_grid_payload",
    "verify_application_bridge_grid_manifest",
    "verify_bridge_grid_manifest",
    "verify_dynamics_grid_manifest",
    "verify_response_grid_manifest",
]
