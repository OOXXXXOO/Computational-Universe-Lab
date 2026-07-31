"""Strict, non-interchangeable momentum-grid manifests for V3-M0."""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, replace
from typing import Literal

from .evidence import canonical_sha


DYNAMICS_GRID_SCHEMA_VERSION = "v3m0.dynamics-k-grid.v1"
BRIDGE_GRID_SCHEMA_VERSION = "v3m0.bridge-k-grid.v1"
DYNAMICS_GRID_DENOMINATOR = 64
DYNAMICS_GRID_MAX_POINT_COUNT = 262_144
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
        _sha(self.bridge_grid_sha, "bridge_grid_sha")


def dynamics_grid_payload(
    grid: DynamicsKGridManifest,
) -> dict[str, object]:
    if not isinstance(grid, DynamicsKGridManifest):
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


def bridge_grid_payload(
    grid: BridgeKGridManifest,
) -> dict[str, object]:
    if not isinstance(grid, BridgeKGridManifest):
        raise TypeError("grid must be a BridgeKGridManifest")
    return {
        "grid_schema_version": grid.grid_schema_version,
        "spatial_shape": list(grid.spatial_shape),
        "torus_denominators": list(grid.torus_denominators),
        "reciprocal_indices": [
            list(item) for item in grid.reciprocal_indices
        ],
    }


def _expected_dynamics_grid(
    transition_support: tuple[tuple[int, ...], ...],
    metric_support: tuple[tuple[int, ...], ...],
) -> DynamicsKGridManifest:
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
    if type(grid) is not DynamicsKGridManifest:
        raise TypeError("grid must be a DynamicsKGridManifest")
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
    provisional = BridgeKGridManifest(
        grid_schema_version=BRIDGE_GRID_SCHEMA_VERSION,
        spatial_shape=shape,
        torus_denominators=shape,
        reciprocal_indices=tuple(sorted(points)),
        bridge_grid_sha="0" * 64,
    )
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
    if type(grid) is not BridgeKGridManifest:
        raise TypeError("grid must be a BridgeKGridManifest")
    if grid.grid_schema_version != BRIDGE_GRID_SCHEMA_VERSION:
        raise ValueError("unexpected bridge grid schema")
    if grid.bridge_grid_sha != canonical_sha(bridge_grid_payload(grid)):
        raise ValueError("bridge_grid_sha does not match complete body")
    expected = _expected_bridge_grid(spatial_shape, signed_support)
    if grid != expected:
        raise ValueError("bridge grid is not the unique support-derived grid")
    return grid


__all__ = [
    "BRIDGE_GRID_SCHEMA_VERSION",
    "DYNAMICS_GRID_DENOMINATOR",
    "DYNAMICS_GRID_MAX_POINT_COUNT",
    "DYNAMICS_GRID_SCHEMA_VERSION",
    "BridgeKGridManifest",
    "DynamicsKGridManifest",
    "bridge_grid_payload",
    "build_bridge_grid_manifest",
    "build_dynamics_grid_manifest",
    "dynamics_grid_payload",
    "verify_bridge_grid_manifest",
    "verify_dynamics_grid_manifest",
]
