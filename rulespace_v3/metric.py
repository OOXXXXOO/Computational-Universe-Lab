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
    SYNTHETIC_APPLICATION_AUTHORITY_KIND,
    VerifiedPrestructureAuthority,
    _reverify_verified_prestructure_authority,
)
from .structure import (
    StructureManifest,
    _freeze_owner_call_graph,
    structure_manifest_payload,
    verify_structure_manifest,
)


METRIC_ORIGIN_SCHEMA_VERSION = "v3m0.metric-origin-manifest.v1"
STABILITY_METRIC_SCHEMA_VERSION = "v3m0.stability-metric-witness.v1"
METRIC_SUPPORT_SCHEMA_VERSION = "v3m0.metric-support.v1"
METRIC_NORMALIZATION_ID: Literal["trace-at-zero-equals-state-dim-v1"] = (
    "trace-at-zero-equals-state-dim-v1"
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
            raise TypeError("metric_kernel must be an exact FrozenComplexTensor")
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


# Freeze record validation before the owner-neutral constructor captures these
# classes.  Dataclass ``__init__`` resolves ``__post_init__`` on the class, so
# this closes both direct calls and construction against module shadowing.
MetricOriginManifest.__post_init__ = _freeze_owner_call_graph(
    MetricOriginManifest.__post_init__
)
StabilityMetricWitness.__post_init__ = _freeze_owner_call_graph(
    StabilityMetricWitness.__post_init__
)


def metric_origin_payload(
    origin: MetricOriginManifest,
) -> dict[str, object]:
    if type(origin) is not MetricOriginManifest:
        raise TypeError("origin must be an exact MetricOriginManifest")
    return {
        "origin_schema_version": origin.origin_schema_version,
        "origin_kind": origin.origin_kind,
        "parent_freeze_sha": origin.parent_freeze_sha,
        "prestructure_authority_sha": (origin.prestructure_authority_sha),
        "factory_sha": origin.factory_sha,
        "structure_manifest_sha": origin.structure_manifest_sha,
        "evidence_lane": origin.evidence_lane,
        "derivation_or_preregistration_sha": (origin.derivation_or_preregistration_sha),
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


_OWNER_FROZEN_CANONICAL_SHA = _freeze_owner_call_graph(canonical_sha)
_OWNER_FROZEN_SUPPORT_PAYLOAD = _freeze_owner_call_graph(metric_support_payload)
_OWNER_FROZEN_STRUCTURE_PAYLOAD = _freeze_owner_call_graph(structure_manifest_payload)
_OWNER_FROZEN_ORIGIN_PAYLOAD = _freeze_owner_call_graph(metric_origin_payload)
_OWNER_FROZEN_WITNESS_PAYLOAD = _freeze_owner_call_graph(
    stability_metric_witness_payload
)


def _make_bound_synthetic_identity_metric_core(
    *,
    factory_reverifier,
    tensor_array_builder,
    tensor_freezer,
    sha_builder,
    support_payload_builder,
    structure_payload_builder,
    origin_payload_builder,
    witness_payload_builder,
    origin_type,
    witness_type,
    structure_type,
    tensor_type,
    replace_fn,
    np_module,
    exact_type,
    type_error,
    value_error,
    length,
    complex_builder,
    float_builder,
    origin_schema,
    witness_schema,
    normalization_id,
):
    def _build_bound_synthetic_identity_metric(
        factory: VerifiedFactory,
        structure: StructureManifest,
        state_metric: FrozenComplexTensor,
        *,
        parent_freeze_sha: str,
        prestructure_authority_sha: str,
        derivation_or_preregistration_sha: str,
        metric_support_offsets: tuple[tuple[int, ...], ...],
    ) -> StabilityMetricWitness:
        """Build the identity metric from inputs already joined by an authority owner."""

        factory_view = factory_reverifier(factory)
        payload = factory_view.factory
        if exact_type(structure) is not structure_type:
            raise type_error("structure must be an exact StructureManifest")
        if exact_type(state_metric) is not tensor_type:
            raise type_error("state_metric must be an exact FrozenComplexTensor")
        if (
            structure.structure_manifest_sha
            != sha_builder(structure_payload_builder(structure))
            or structure.evidence_lane != "synthetic-classical"
            or structure.structure_kind != "symplectic"
            or structure.target_spec_sha != payload.target_spec_sha
            or structure.state_schema_id != payload.state_schema_id
            or structure.channel_order != payload.channel_order
            or structure.prestructure_authority_sha != prestructure_authority_sha
        ):
            raise value_error("structure does not exactly join the metric inputs")
        state_count = length(payload.channel_order)
        values = tensor_array_builder(state_metric)
        identity = np_module.eye(state_count, dtype=np_module.complex128)
        expected_state_metric = tensor_freezer(identity)
        if values.shape != (state_count, state_count):
            raise value_error("synthetic state metric shape mismatch")
        if (
            not np_module.array_equal(values, identity)
            or state_metric.tensor_sha != expected_state_metric.tensor_sha
        ):
            raise value_error("synthetic state metric is not bit-exact identity")
        if complex_builder(np_module.trace(values)) != complex_builder(
            float_builder(state_count), 0.0
        ):
            raise value_error("synthetic metric trace normalization failed")
        expected_support = ((0,) * payload.spatial_ndim,)
        if metric_support_offsets != expected_support:
            raise value_error(
                "synthetic metric support is not the exact origin singleton"
            )
        kernel = tensor_freezer(values[None, :, :])
        support_sha = sha_builder(support_payload_builder(metric_support_offsets))
        provisional_origin = origin_type(
            origin_schema_version=origin_schema,
            origin_kind="synthetic-identity-v1",
            parent_freeze_sha=parent_freeze_sha,
            prestructure_authority_sha=prestructure_authority_sha,
            factory_sha=payload.factory_sha,
            structure_manifest_sha=structure.structure_manifest_sha,
            evidence_lane=structure.evidence_lane,
            derivation_or_preregistration_sha=derivation_or_preregistration_sha,
            metric_kernel_sha=kernel.tensor_sha,
            metric_support_sha=support_sha,
            origin_sha="0" * 64,
        )
        origin = replace_fn(
            provisional_origin,
            origin_sha=sha_builder(origin_payload_builder(provisional_origin)),
        )
        provisional = witness_type(
            witness_schema_version=witness_schema,
            structure_manifest_sha=structure.structure_manifest_sha,
            metric_kind="constant-state-v1",
            metric_kernel=kernel,
            metric_support_offsets=metric_support_offsets,
            metric_support_sha=support_sha,
            normalization_id=normalization_id,
            positive_eigenvalue_floor=1.0,
            condition_number_max=1.0,
            metric_origin=origin,
            witness_sha="0" * 64,
        )
        return replace_fn(
            provisional,
            witness_sha=sha_builder(witness_payload_builder(provisional)),
        )

    return _build_bound_synthetic_identity_metric


_build_bound_synthetic_identity_metric = _freeze_owner_call_graph(
    _make_bound_synthetic_identity_metric_core(
        factory_reverifier=_reverify_verified_factory,
        tensor_array_builder=frozen_tensor_array,
        tensor_freezer=freeze_complex_tensor,
        sha_builder=_OWNER_FROZEN_CANONICAL_SHA,
        support_payload_builder=_OWNER_FROZEN_SUPPORT_PAYLOAD,
        structure_payload_builder=_OWNER_FROZEN_STRUCTURE_PAYLOAD,
        origin_payload_builder=_OWNER_FROZEN_ORIGIN_PAYLOAD,
        witness_payload_builder=_OWNER_FROZEN_WITNESS_PAYLOAD,
        origin_type=MetricOriginManifest,
        witness_type=StabilityMetricWitness,
        structure_type=StructureManifest,
        tensor_type=FrozenComplexTensor,
        replace_fn=replace,
        np_module=np,
        exact_type=type,
        type_error=TypeError,
        value_error=ValueError,
        length=len,
        complex_builder=complex,
        float_builder=float,
        origin_schema=METRIC_ORIGIN_SCHEMA_VERSION,
        witness_schema=STABILITY_METRIC_SCHEMA_VERSION,
        normalization_id=METRIC_NORMALIZATION_ID,
    )
)


def _bind_metric_inputs(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    structure: StructureManifest,
    *,
    _factory_reverifier=_reverify_verified_factory,
    _authority_reverifier=_reverify_verified_prestructure_authority,
    _structure_verifier=verify_structure_manifest,
) -> tuple[object, object, StructureManifest]:
    factory_view = _factory_reverifier(factory)
    authority_view = _authority_reverifier(authority)
    if factory is not authority_view.factory:
        raise ValueError("metric factory is not authority-bound")
    verified_structure = _structure_verifier(
        structure,
        factory,
        authority,
    )
    return factory_view, authority_view, verified_structure


def _make_expected_metric(
    input_binder,
    metric_core,
    *,
    tensor_freezer,
    np_module,
    synthetic_authority_kind=SYNTHETIC_APPLICATION_AUTHORITY_KIND,
):
    def _expected_metric(
        factory: VerifiedFactory,
        authority: VerifiedPrestructureAuthority,
        structure: StructureManifest,
    ) -> StabilityMetricWitness:
        factory_view, authority_view, verified_structure = input_binder(
            factory,
            authority,
            structure,
        )
        prereg = authority_view.authority.synthetic_preregistration
        if verified_structure.evidence_lane != "synthetic-classical":
            raise ValueError("this metric slice requires synthetic-classical authority")
        if prereg is not None:
            derivation_sha = prereg.preregistration_sha
        elif authority_view.authority.authority_kind == synthetic_authority_kind:
            application = authority_view.authority.synthetic_application_spec
            permit_sha = authority_view.authority.synthetic_application_permit_sha
            if application is None or permit_sha is None:
                raise ValueError("synthetic application authority body is incomplete")
            derivation_sha = application.application_spec_sha
        else:
            raise ValueError("this metric slice requires synthetic-classical authority")
        state_count = len(factory_view.factory.channel_order)
        state_metric = tensor_freezer(
            np_module.eye(state_count, dtype=np_module.complex128)
        )
        zero_support = ((0,) * factory_view.factory.spatial_ndim,)
        return metric_core(
            factory,
            verified_structure,
            state_metric,
            parent_freeze_sha=(
                authority_view.authority.parent_freeze.parent_freeze_sha
            ),
            prestructure_authority_sha=authority_view.authority.authority_sha,
            derivation_or_preregistration_sha=derivation_sha,
            metric_support_offsets=zero_support,
        )

    return _expected_metric


_expected_metric = _make_expected_metric(
    _bind_metric_inputs,
    _build_bound_synthetic_identity_metric,
    tensor_freezer=freeze_complex_tensor,
    np_module=np,
)


def _make_metric_public_apis(
    *,
    expected_builder,
    witness_type,
    witness_schema,
    sha_builder,
    support_payload_builder,
    origin_payload_builder,
    witness_payload_builder,
):
    def build_stability_metric_witness(
        factory: VerifiedFactory,
        authority: VerifiedPrestructureAuthority,
        structure: StructureManifest,
    ) -> StabilityMetricWitness:
        """Build the closed identity metric for synthetic controls."""

        return expected_builder(factory, authority, structure)

    def verify_stability_metric_witness(
        witness: StabilityMetricWitness,
        factory: VerifiedFactory,
        authority: VerifiedPrestructureAuthority,
        structure: StructureManifest,
    ) -> StabilityMetricWitness:
        if type(witness) is not witness_type:
            raise TypeError("witness must be a StabilityMetricWitness")
        if witness.witness_schema_version != witness_schema:
            raise ValueError("unexpected stability metric schema")
        if witness.metric_support_sha != sha_builder(
            support_payload_builder(witness.metric_support_offsets)
        ):
            raise ValueError("metric_support_sha does not match support body")
        if witness.metric_origin.origin_sha != sha_builder(
            origin_payload_builder(witness.metric_origin)
        ):
            raise ValueError("metric origin SHA does not match complete body")
        if witness.witness_sha != sha_builder(witness_payload_builder(witness)):
            raise ValueError("witness_sha does not match complete body")
        expected = expected_builder(factory, authority, structure)
        if witness != expected:
            raise ValueError("metric witness is not authority-derived")
        return witness

    return build_stability_metric_witness, verify_stability_metric_witness


(
    build_stability_metric_witness,
    verify_stability_metric_witness,
) = _make_metric_public_apis(
    expected_builder=_expected_metric,
    witness_type=StabilityMetricWitness,
    witness_schema=STABILITY_METRIC_SCHEMA_VERSION,
    sha_builder=canonical_sha,
    support_payload_builder=metric_support_payload,
    origin_payload_builder=metric_origin_payload,
    witness_payload_builder=stability_metric_witness_payload,
)


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
