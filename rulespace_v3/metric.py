"""Closed stability-metric witnesses for V3-M0 synthetic controls."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    VerifiedFactory,
    _reverify_verified_factory,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
)
from .prestructure import (
    VerifiedPrestructureAuthority,
    _reverify_verified_prestructure_authority,
)
from .structure import (
    StructureManifest,
    verify_structure_manifest,
)


METRIC_ORIGIN_SCHEMA_VERSION = "v3m0.metric-origin-manifest.v1"
STABILITY_METRIC_SCHEMA_VERSION = "v3m0.stability-metric-witness.v1"
METRIC_SUPPORT_SCHEMA_VERSION = "v3m0.metric-support.v1"
METRIC_NORMALIZATION_ID: Literal[
    "trace-at-zero-equals-state-dim-v1"
] = "trace-at-zero-equals-state-dim-v1"
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


def _finite_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


def metric_support_payload(
    support_offsets: tuple[tuple[int, ...], ...],
) -> dict[str, object]:
    if type(support_offsets) is not tuple or not support_offsets:
        raise ValueError("metric support must be a non-empty tuple")
    return {
        "support_schema_version": METRIC_SUPPORT_SCHEMA_VERSION,
        "support_offsets": [list(item) for item in support_offsets],
    }


@dataclass(frozen=True)
class MetricOriginManifest:
    origin_schema_version: str
    origin_kind: Literal[
        "synthetic-identity-v1",
        "adapter-preregistered-v1",
    ]
    parent_freeze_sha: str
    prestructure_authority_sha: str
    factory_sha: str
    structure_manifest_sha: str
    evidence_lane: Literal[
        "synthetic-classical",
        "classical-adapter",
        "quantum",
    ]
    derivation_or_preregistration_sha: str
    metric_kernel_sha: str
    metric_support_sha: str
    origin_sha: str

    def __post_init__(self) -> None:
        _text(self.origin_schema_version, "origin_schema_version")
        if self.origin_kind not in (
            "synthetic-identity-v1",
            "adapter-preregistered-v1",
        ):
            raise ValueError("origin_kind is not closed")
        for field in (
            "parent_freeze_sha",
            "prestructure_authority_sha",
            "factory_sha",
            "structure_manifest_sha",
            "derivation_or_preregistration_sha",
            "metric_kernel_sha",
            "metric_support_sha",
            "origin_sha",
        ):
            _sha(getattr(self, field), field)
        if self.evidence_lane not in (
            "synthetic-classical",
            "classical-adapter",
            "quantum",
        ):
            raise ValueError("evidence_lane is not closed")


@dataclass(frozen=True)
class StabilityMetricWitness:
    witness_schema_version: str
    structure_manifest_sha: str
    metric_kind: Literal[
        "constant-state-v1",
        "finite-support-laurent-v1",
    ]
    metric_kernel: FrozenComplexTensor
    metric_support_offsets: tuple[tuple[int, ...], ...]
    metric_support_sha: str
    normalization_id: Literal["trace-at-zero-equals-state-dim-v1"]
    positive_eigenvalue_floor: float
    condition_number_max: float
    metric_origin: MetricOriginManifest
    witness_sha: str

    def __post_init__(self) -> None:
        _text(self.witness_schema_version, "witness_schema_version")
        _sha(self.structure_manifest_sha, "structure_manifest_sha")
        if self.metric_kind not in (
            "constant-state-v1",
            "finite-support-laurent-v1",
        ):
            raise ValueError("metric_kind is not closed")
        if type(self.metric_kernel) is not FrozenComplexTensor:
            raise TypeError(
                "metric_kernel must be an exact FrozenComplexTensor"
            )
        if (
            type(self.metric_support_offsets) is not tuple
            or not self.metric_support_offsets
        ):
            raise ValueError("metric_support_offsets must be non-empty")
        ndim = len(self.metric_support_offsets[0])
        for row in self.metric_support_offsets:
            if type(row) is not tuple or len(row) != ndim:
                raise ValueError("metric support dimension mismatch")
            if not all(type(item) is int for item in row):
                raise TypeError("metric support must contain ints")
        if self.metric_support_offsets != tuple(
            sorted(set(self.metric_support_offsets))
        ):
            raise ValueError("metric support must be unique and canonical")
        _sha(self.metric_support_sha, "metric_support_sha")
        if self.normalization_id != METRIC_NORMALIZATION_ID:
            raise ValueError("normalization_id is not frozen")
        floor = _finite_float(
            self.positive_eigenvalue_floor,
            "positive_eigenvalue_floor",
        )
        condition = _finite_float(
            self.condition_number_max,
            "condition_number_max",
        )
        if floor <= 0.0:
            raise ValueError("positive eigenvalue floor must be positive")
        if condition < 1.0 or condition > 1e8:
            raise ValueError("metric condition number is outside the hard gate")
        if type(self.metric_origin) is not MetricOriginManifest:
            raise TypeError("metric_origin must be an exact record type")
        _sha(self.witness_sha, "witness_sha")


def metric_origin_payload(
    origin: MetricOriginManifest,
) -> dict[str, object]:
    if type(origin) is not MetricOriginManifest:
        raise TypeError("origin must be an exact MetricOriginManifest")
    return {
        "origin_schema_version": origin.origin_schema_version,
        "origin_kind": origin.origin_kind,
        "parent_freeze_sha": origin.parent_freeze_sha,
        "prestructure_authority_sha": (
            origin.prestructure_authority_sha
        ),
        "factory_sha": origin.factory_sha,
        "structure_manifest_sha": origin.structure_manifest_sha,
        "evidence_lane": origin.evidence_lane,
        "derivation_or_preregistration_sha": (
            origin.derivation_or_preregistration_sha
        ),
        "metric_kernel_sha": origin.metric_kernel_sha,
        "metric_support_sha": origin.metric_support_sha,
    }


def _origin_record(origin: MetricOriginManifest) -> dict[str, object]:
    return {
        **metric_origin_payload(origin),
        "origin_sha": origin.origin_sha,
    }


def stability_metric_witness_payload(
    witness: StabilityMetricWitness,
) -> dict[str, object]:
    if not isinstance(witness, StabilityMetricWitness):
        raise TypeError("witness must be a StabilityMetricWitness")
    return {
        "witness_schema_version": witness.witness_schema_version,
        "structure_manifest_sha": witness.structure_manifest_sha,
        "metric_kind": witness.metric_kind,
        "metric_kernel": _tensor_record(witness.metric_kernel),
        "metric_support_offsets": [
            list(item) for item in witness.metric_support_offsets
        ],
        "metric_support_sha": witness.metric_support_sha,
        "normalization_id": witness.normalization_id,
        "positive_eigenvalue_floor": witness.positive_eigenvalue_floor,
        "condition_number_max": witness.condition_number_max,
        "metric_origin": _origin_record(witness.metric_origin),
    }


def _expected_metric(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    structure: StructureManifest,
) -> StabilityMetricWitness:
    factory_view = _reverify_verified_factory(factory)
    authority_view = _reverify_verified_prestructure_authority(authority)
    if factory is not authority_view.factory:
        raise ValueError("metric factory is not authority-bound")
    verified_structure = verify_structure_manifest(
        structure,
        factory,
        authority,
    )
    prereg = authority_view.authority.synthetic_preregistration
    if prereg is None or verified_structure.evidence_lane != "synthetic-classical":
        raise ValueError("this metric slice requires synthetic-classical authority")
    state_count = len(factory_view.factory.channel_order)
    kernel = freeze_complex_tensor(
        np.eye(state_count, dtype=np.complex128)[None, :, :]
    )
    zero_support = ((0,) * factory_view.factory.spatial_ndim,)
    support_sha = canonical_sha(metric_support_payload(zero_support))
    provisional_origin = MetricOriginManifest(
        origin_schema_version=METRIC_ORIGIN_SCHEMA_VERSION,
        origin_kind="synthetic-identity-v1",
        parent_freeze_sha=(
            authority_view.authority.parent_freeze.parent_freeze_sha
        ),
        prestructure_authority_sha=(
            authority_view.authority.authority_sha
        ),
        factory_sha=factory_view.factory.factory_sha,
        structure_manifest_sha=(
            verified_structure.structure_manifest_sha
        ),
        evidence_lane=verified_structure.evidence_lane,
        derivation_or_preregistration_sha=prereg.preregistration_sha,
        metric_kernel_sha=kernel.tensor_sha,
        metric_support_sha=support_sha,
        origin_sha="0" * 64,
    )
    origin = replace(
        provisional_origin,
        origin_sha=canonical_sha(metric_origin_payload(provisional_origin)),
    )
    provisional = StabilityMetricWitness(
        witness_schema_version=STABILITY_METRIC_SCHEMA_VERSION,
        structure_manifest_sha=verified_structure.structure_manifest_sha,
        metric_kind="constant-state-v1",
        metric_kernel=kernel,
        metric_support_offsets=zero_support,
        metric_support_sha=support_sha,
        normalization_id=METRIC_NORMALIZATION_ID,
        positive_eigenvalue_floor=1.0,
        condition_number_max=1.0,
        metric_origin=origin,
        witness_sha="0" * 64,
    )
    result = replace(
        provisional,
        witness_sha=canonical_sha(
            stability_metric_witness_payload(provisional)
        ),
    )
    values = frozen_tensor_array(result.metric_kernel)
    if values.shape != (1, state_count, state_count):
        raise ValueError("synthetic metric kernel shape mismatch")
    if not np.array_equal(values[0], np.eye(state_count)):
        raise ValueError("synthetic metric is not identity")
    if complex(np.trace(values[0])) != complex(float(state_count), 0.0):
        raise ValueError("synthetic metric trace normalization failed")
    return result


def build_stability_metric_witness(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    structure: StructureManifest,
) -> StabilityMetricWitness:
    """Build the closed identity metric for synthetic controls."""

    return _expected_metric(factory, authority, structure)


def verify_stability_metric_witness(
    witness: StabilityMetricWitness,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    structure: StructureManifest,
) -> StabilityMetricWitness:
    if type(witness) is not StabilityMetricWitness:
        raise TypeError("witness must be a StabilityMetricWitness")
    if witness.witness_schema_version != STABILITY_METRIC_SCHEMA_VERSION:
        raise ValueError("unexpected stability metric schema")
    if witness.metric_support_sha != canonical_sha(
        metric_support_payload(witness.metric_support_offsets)
    ):
        raise ValueError("metric_support_sha does not match support body")
    if witness.metric_origin.origin_sha != canonical_sha(
        metric_origin_payload(witness.metric_origin)
    ):
        raise ValueError("metric origin SHA does not match complete body")
    if witness.witness_sha != canonical_sha(
        stability_metric_witness_payload(witness)
    ):
        raise ValueError("witness_sha does not match complete body")
    expected = _expected_metric(factory, authority, structure)
    if witness.witness_sha != expected.witness_sha:
        raise ValueError("metric witness is not authority-derived")
    return witness


__all__ = [
    "METRIC_NORMALIZATION_ID",
    "METRIC_ORIGIN_SCHEMA_VERSION",
    "METRIC_SUPPORT_SCHEMA_VERSION",
    "STABILITY_METRIC_SCHEMA_VERSION",
    "MetricOriginManifest",
    "StabilityMetricWitness",
    "build_stability_metric_witness",
    "metric_origin_payload",
    "metric_support_payload",
    "stability_metric_witness_payload",
    "verify_stability_metric_witness",
]
