"""Authority-neutral C19 refreeze-v2 candidate over real runtime factories.

The zero-argument builder performs a complete local construction replay, but
returns only an inert, self-hashed raw dataclass tree.  In particular this
module has no Parent, permit, evidence, or raw-hydration issuer.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, replace
from typing import Literal

import numpy as np
import sympy as sp

from .ablation import (
    AblationManifest,
    AblationReplacement,
    ablation_manifest_payload,
    matched_ablation,
    verify_ablation_pair,
)
from .evidence import canonical_sha
from .factory import (
    NEUTRAL_IDENTITY_ID,
    BasisManifest,
    CalibrationObservation,
    FrozenComplexTensor,
    FrozenSyntheticTarget,
    LinearRealspaceFactory,
    Primitive,
    PrimitiveInterface,
    PrimitiveOperatorWire,
    _reverify_verified_factory,
    apply_factory_step,
    basis_manifest_array,
    build_basis_manifest,
    build_calibration_seed,
    build_factory_from_trace,
    factory_payload,
    factory_support_offsets,
    freeze_complex_tensor,
    freeze_synthetic_target,
    frozen_tensor_array,
    frozen_tensor_payload,
    measure_calibration_holdout,
    synthetic_target_payload,
)
from .grids import (
    DIRECTION_MANIFEST_SCHEMA_VERSION,
    RESPONSE_GRID_SCHEMA_VERSION,
    DirectionManifest,
    ResponseKGridManifest,
    direction_manifest_payload,
    response_grid_payload,
)
from .trace import (
    CoefficientRecord,
    ConstructionTrace,
    PrimitiveTrace,
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
    construction_trace_payload,
)


C19_REFREEZE_V2_CANDIDATE_SCHEMA_VERSION = "v3m0.c19-refreeze-v2-candidate.v1"
C19_RUNTIME_CONSTRUCTION_V2_SCHEMA_VERSION = "v3m0.c19-runtime-construction.v2"
C19_BASIS_CONTRACT_V2_SCHEMA_VERSION = "v3m0.c19-basis-contract.v2"
DYNAMICS_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION = (
    "v3m0.dynamics-k-grid-derivation-protocol.v1"
)
BRIDGE_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION = (
    "v3m0.bridge-k-grid-derivation-protocol.v1"
)
C19_OBSERVER_GEOMETRY_BUNDLE_V1_SCHEMA_VERSION = "v3m0.c19-observer-geometry-bundle.v1"
C19_AUTHORITY_STATE_V2 = "PROVISIONAL_NOT_ISSUED"
C19_CLAIM_CEILING_V2 = "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY"
C19_CAUSAL_CONTRAST_ROLE_V2 = "NULL_INTERVENTION_INVARIANCE_CONTROL"
C19_PHYSICAL_ANCHOR_ELIGIBILITY_V2 = "INELIGIBLE"
C19_FAMILY_ELIGIBILITY_V2 = "INELIGIBLE"
C19_STATE_SCHEMA_ID_V2 = "v3m0.c19-real-canonical-state.v2"
C19_CHANNEL_ORDER_V2 = tuple(
    channel for pair in range(10) for channel in (f"q{pair}", f"p{pair}")
)
C19_SPATIAL_SHAPE_V2 = (8,)
C19_TARGET_TOOTH_V2 = 2.0**-14
C19_CONTROL_CASE_ID_V2 = "C19_FULL_POSITIVE_OBSERVER_COLLAPSE"
C19_APPLICATION_INSTANCE_ID_V2 = "v3m0.synthetic-control.c19.v2"
C19_SCENARIO_ID_V2 = "v3m0.synthetic-control.c19.v2.scenario.observer-collapse.v2"
C19_DESIGN_SOURCE_PATH_V2 = "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md"
C19_DESIGN_SOURCE_SHA_V2 = (
    "c79dd64067c5b01cbff7629c85b82e73c03e9960096566147ca31d3ce666051b"
)
C19_DESIGN_FREEZE_COMMIT_SHA_V2 = "87a60dc50b025a360b4aad1e280837b32681bb85"


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    _exact_record(tensor, FrozenComplexTensor, "frozen tensor")
    return {**frozen_tensor_payload(tensor), "tensor_sha": tensor.tensor_sha}


def _factory_record(factory: LinearRealspaceFactory) -> dict[str, object]:
    _exact_record(factory, LinearRealspaceFactory, "factory")
    _exact_record(factory.interface, PrimitiveInterface, "factory interface")
    _basis_record(factory.readout_basis)
    for index, primitive in enumerate(factory.primitives):
        _exact_record(primitive, Primitive, f"factory primitive[{index}]")
    return {**factory_payload(factory), "factory_sha": factory.factory_sha}


def _target_record(target: FrozenSyntheticTarget) -> dict[str, object]:
    _exact_record(target, FrozenSyntheticTarget, "synthetic target")
    _exact_record(
        target.observation,
        CalibrationObservation,
        "synthetic target observation",
    )
    _tensor_record(target.observation.response_tensor)
    _tensor_record(target.target_response)
    return {
        **synthetic_target_payload(target),
        "target_spec_sha": target.target_spec_sha,
    }


def _basis_record(basis: BasisManifest) -> dict[str, object]:
    _exact_record(basis, BasisManifest, "basis manifest")
    return {
        "basis_schema_version": basis.basis_schema_version,
        "role": basis.role,
        "state_schema_id": basis.state_schema_id,
        "channel_order": list(basis.channel_order),
        "vectors_wire": [[list(wire) for wire in row] for row in basis.vectors_wire],
        "manifest_id": basis.manifest_id,
    }


def _ablation_record(manifest: AblationManifest) -> dict[str, object]:
    _exact_record(manifest, AblationManifest, "ablation manifest")
    for index, replacement in enumerate(manifest.replacements):
        _exact_record(
            replacement,
            AblationReplacement,
            f"ablation replacement[{index}]",
        )
    return {
        **ablation_manifest_payload(manifest),
        "manifest_sha": manifest.manifest_sha,
    }


def _trace_record(trace: ConstructionTrace) -> dict[str, object]:
    _exact_record(trace, ConstructionTrace, "construction trace")
    for index, node in enumerate(trace.provenance_nodes):
        _exact_record(node, ProvenanceNode, f"provenance node[{index}]")
    for index, record in enumerate(trace.coefficient_records):
        _exact_record(
            record,
            CoefficientRecord,
            f"coefficient record[{index}]",
        )
    for index, primitive in enumerate(trace.primitives):
        _exact_record(
            primitive,
            PrimitiveTrace,
            f"construction trace primitive[{index}]",
        )
    return construction_trace_payload(trace)


@dataclass(frozen=True)
class C19RuntimeConstructionV2:
    construction_schema_version: str
    state_shape: tuple[int, ...]
    construction_trace: ConstructionTrace
    frozen_target: FrozenSyntheticTarget
    actual_factory: LinearRealspaceFactory
    matched_factory: LinearRealspaceFactory
    ablation_manifest: AblationManifest
    actual_active_step_count: int
    matched_active_step_count: int
    actual_layer_slot_count: int
    matched_layer_slot_count: int
    actual_primitive_count: int
    matched_primitive_count: int
    actual_slot_program_sha: str
    matched_slot_program_sha: str
    actual_active_effect_digest: str
    matched_active_effect_digest: str
    actual_support_offsets: tuple[tuple[int, ...], ...]
    matched_support_offsets: tuple[tuple[int, ...], ...]
    actual_apply_factory_step_kernel: FrozenComplexTensor
    matched_apply_factory_step_kernel: FrozenComplexTensor
    actual_independent_replay_kernel: FrozenComplexTensor
    matched_independent_replay_kernel: FrozenComplexTensor
    construction_sha: str


@dataclass(frozen=True)
class C19BasisContractV2:
    basis_contract_schema_version: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    common_source_basis: BasisManifest
    common_readout_basis: BasisManifest
    common_source_tensor: FrozenComplexTensor
    common_readout_tensor: FrozenComplexTensor
    source_selector_b_plus: FrozenComplexTensor
    readout_selector_p: FrozenComplexTensor
    source_injection: FrozenComplexTensor
    readout_coisometry: FrozenComplexTensor
    scenario_source_basis: BasisManifest
    scenario_readout_basis: BasisManifest
    source_trial_vectors: FrozenComplexTensor
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    basis_contract_sha: str


@dataclass(frozen=True)
class DynamicsKGridDerivationProtocolV1:
    protocol_schema_version: str
    branch_roles: tuple[Literal["actual", "matched_ablated"], ...]
    transition_support_source: str
    metric_support_source: str
    derivation_algorithm: str
    exact_zero_qualification_profile: str
    nonzero_fallback_profile: str
    caller_supplied_points_allowed: Literal[False]
    fail_closed_condition_ids: tuple[str, ...]
    protocol_sha: str


def dynamics_k_grid_derivation_protocol_v1_payload(
    protocol: DynamicsKGridDerivationProtocolV1,
) -> dict[str, object]:
    _exact_record(
        protocol,
        DynamicsKGridDerivationProtocolV1,
        "dynamics grid derivation protocol",
    )
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "branch_roles": list(protocol.branch_roles),
        "transition_support_source": protocol.transition_support_source,
        "metric_support_source": protocol.metric_support_source,
        "derivation_algorithm": protocol.derivation_algorithm,
        "exact_zero_qualification_profile": (protocol.exact_zero_qualification_profile),
        "nonzero_fallback_profile": protocol.nonzero_fallback_profile,
        "caller_supplied_points_allowed": protocol.caller_supplied_points_allowed,
        "fail_closed_condition_ids": list(protocol.fail_closed_condition_ids),
    }


@dataclass(frozen=True)
class BridgeKGridDerivationProtocolV1:
    protocol_schema_version: str
    branch_roles: tuple[Literal["actual", "matched_ablated"], ...]
    spatial_shape: tuple[int, ...]
    support_source: str
    derivation_algorithm: str
    bridge_steps: tuple[int, ...]
    caller_supplied_points_allowed: Literal[False]
    fail_closed_condition_ids: tuple[str, ...]
    protocol_sha: str


def bridge_k_grid_derivation_protocol_v1_payload(
    protocol: BridgeKGridDerivationProtocolV1,
) -> dict[str, object]:
    _exact_record(
        protocol,
        BridgeKGridDerivationProtocolV1,
        "bridge grid derivation protocol",
    )
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "branch_roles": list(protocol.branch_roles),
        "spatial_shape": list(protocol.spatial_shape),
        "support_source": protocol.support_source,
        "derivation_algorithm": protocol.derivation_algorithm,
        "bridge_steps": list(protocol.bridge_steps),
        "caller_supplied_points_allowed": protocol.caller_supplied_points_allowed,
        "fail_closed_condition_ids": list(protocol.fail_closed_condition_ids),
    }


@dataclass(frozen=True)
class C19ObserverGeometryBundleV1:
    geometry_bundle_schema_version: str
    kind: Literal["C19_OBSERVER_COLLAPSE_CONDITIONS"]
    claim_ceiling: Literal["CONDITIONAL_PREREQUISITES_ONLY"]
    evaluation_state: Literal["NOT_EVALUATED_PRE_RESPONSE"]
    conditional_prediction_state: Literal["CONDITIONAL_ANALYTIC_IDENTITY_ONLY"]
    state_dim: int
    ambient_h_dim: int
    curvature_dim: int
    tt_dim: int
    gauge_dim: int
    row_dim: int
    omega_j20: FrozenComplexTensor
    source_b_plus: FrozenComplexTensor
    readout_p: FrozenComplexTensor
    tt_basis: FrozenComplexTensor
    gauge_basis: FrozenComplexTensor
    row_basis: FrozenComplexTensor
    incidence_q: FrozenComplexTensor
    ker_c_projector: FrozenComplexTensor
    curvature_frame: FrozenComplexTensor
    conditional_principal_sine_squared: FrozenComplexTensor
    conditional_principal_spectrum: tuple[float, ...]
    state_metric: FrozenComplexTensor
    state_whitener: FrozenComplexTensor
    source_metric: FrozenComplexTensor
    source_whitener: FrozenComplexTensor
    h_metric: FrozenComplexTensor
    h_whitener: FrozenComplexTensor
    curvature_metric: FrozenComplexTensor
    curvature_whitener: FrozenComplexTensor
    control_case_id: str
    application_instance_id: str
    scenario_id: str
    operation_dag_sha: str
    actual_active_step_count: int
    matched_active_step_count: int
    actual_layer_slot_count: int
    matched_layer_slot_count: int
    actual_slot_program_sha: str
    matched_slot_program_sha: str
    actual_active_effect_digest: str
    matched_active_effect_digest: str
    common_source_i20_sha: str
    common_readout_i20_sha: str
    source_b_plus_sha: str
    readout_p_sha: str
    response_grid_sha: str
    dynamics_derivation_protocol_sha: str
    bridge_derivation_protocol_sha: str
    geometry_bundle_sha: str


def c19_observer_geometry_bundle_v1_payload(
    bundle: C19ObserverGeometryBundleV1,
) -> dict[str, object]:
    _exact_record(
        bundle,
        C19ObserverGeometryBundleV1,
        "C19 observer geometry bundle",
    )
    tensor_fields = (
        "omega_j20",
        "source_b_plus",
        "readout_p",
        "tt_basis",
        "gauge_basis",
        "row_basis",
        "incidence_q",
        "ker_c_projector",
        "curvature_frame",
        "conditional_principal_sine_squared",
        "state_metric",
        "state_whitener",
        "source_metric",
        "source_whitener",
        "h_metric",
        "h_whitener",
        "curvature_metric",
        "curvature_whitener",
    )
    return {
        "geometry_bundle_schema_version": bundle.geometry_bundle_schema_version,
        "kind": bundle.kind,
        "claim_ceiling": bundle.claim_ceiling,
        "evaluation_state": bundle.evaluation_state,
        "conditional_prediction_state": bundle.conditional_prediction_state,
        "state_dim": bundle.state_dim,
        "ambient_h_dim": bundle.ambient_h_dim,
        "curvature_dim": bundle.curvature_dim,
        "tt_dim": bundle.tt_dim,
        "gauge_dim": bundle.gauge_dim,
        "row_dim": bundle.row_dim,
        **{field: _tensor_record(getattr(bundle, field)) for field in tensor_fields},
        "conditional_principal_spectrum": list(bundle.conditional_principal_spectrum),
        "control_case_id": bundle.control_case_id,
        "application_instance_id": bundle.application_instance_id,
        "scenario_id": bundle.scenario_id,
        "operation_dag_sha": bundle.operation_dag_sha,
        "actual_active_step_count": bundle.actual_active_step_count,
        "matched_active_step_count": bundle.matched_active_step_count,
        "actual_layer_slot_count": bundle.actual_layer_slot_count,
        "matched_layer_slot_count": bundle.matched_layer_slot_count,
        "actual_slot_program_sha": bundle.actual_slot_program_sha,
        "matched_slot_program_sha": bundle.matched_slot_program_sha,
        "actual_active_effect_digest": bundle.actual_active_effect_digest,
        "matched_active_effect_digest": bundle.matched_active_effect_digest,
        "common_source_i20_sha": bundle.common_source_i20_sha,
        "common_readout_i20_sha": bundle.common_readout_i20_sha,
        "source_b_plus_sha": bundle.source_b_plus_sha,
        "readout_p_sha": bundle.readout_p_sha,
        "response_grid_sha": bundle.response_grid_sha,
        "dynamics_derivation_protocol_sha": (bundle.dynamics_derivation_protocol_sha),
        "bridge_derivation_protocol_sha": bundle.bridge_derivation_protocol_sha,
    }


def c19_basis_contract_v2_payload(
    contract: C19BasisContractV2,
) -> dict[str, object]:
    _exact_record(contract, C19BasisContractV2, "C19 basis contract")
    return {
        "basis_contract_schema_version": contract.basis_contract_schema_version,
        "state_schema_id": contract.state_schema_id,
        "channel_order": list(contract.channel_order),
        "common_source_basis": _basis_record(contract.common_source_basis),
        "common_readout_basis": _basis_record(contract.common_readout_basis),
        "common_source_tensor": _tensor_record(contract.common_source_tensor),
        "common_readout_tensor": _tensor_record(contract.common_readout_tensor),
        "source_selector_b_plus": _tensor_record(contract.source_selector_b_plus),
        "readout_selector_p": _tensor_record(contract.readout_selector_p),
        "source_injection": _tensor_record(contract.source_injection),
        "readout_coisometry": _tensor_record(contract.readout_coisometry),
        "scenario_source_basis": _basis_record(contract.scenario_source_basis),
        "scenario_readout_basis": _basis_record(contract.scenario_readout_basis),
        "source_trial_vectors": _tensor_record(contract.source_trial_vectors),
        "expected_actual_shell_rank": contract.expected_actual_shell_rank,
        "expected_matched_shell_rank": contract.expected_matched_shell_rank,
    }


def c19_runtime_construction_v2_payload(
    construction: C19RuntimeConstructionV2,
) -> dict[str, object]:
    _exact_record(
        construction,
        C19RuntimeConstructionV2,
        "C19 runtime construction",
    )
    return {
        "construction_schema_version": construction.construction_schema_version,
        "state_shape": list(construction.state_shape),
        "construction_trace": _trace_record(construction.construction_trace),
        "frozen_target": _target_record(construction.frozen_target),
        "actual_factory": _factory_record(construction.actual_factory),
        "matched_factory": _factory_record(construction.matched_factory),
        "ablation_manifest": _ablation_record(construction.ablation_manifest),
        "actual_active_step_count": construction.actual_active_step_count,
        "matched_active_step_count": construction.matched_active_step_count,
        "actual_layer_slot_count": construction.actual_layer_slot_count,
        "matched_layer_slot_count": construction.matched_layer_slot_count,
        "actual_primitive_count": construction.actual_primitive_count,
        "matched_primitive_count": construction.matched_primitive_count,
        "actual_slot_program_sha": construction.actual_slot_program_sha,
        "matched_slot_program_sha": construction.matched_slot_program_sha,
        "actual_active_effect_digest": construction.actual_active_effect_digest,
        "matched_active_effect_digest": construction.matched_active_effect_digest,
        "actual_support_offsets": [
            list(item) for item in construction.actual_support_offsets
        ],
        "matched_support_offsets": [
            list(item) for item in construction.matched_support_offsets
        ],
        "actual_apply_factory_step_kernel": _tensor_record(
            construction.actual_apply_factory_step_kernel
        ),
        "matched_apply_factory_step_kernel": _tensor_record(
            construction.matched_apply_factory_step_kernel
        ),
        "actual_independent_replay_kernel": _tensor_record(
            construction.actual_independent_replay_kernel
        ),
        "matched_independent_replay_kernel": _tensor_record(
            construction.matched_independent_replay_kernel
        ),
    }


@dataclass(frozen=True)
class C19RefreezeV2Candidate:
    candidate_schema_version: str
    authority_state: Literal["PROVISIONAL_NOT_ISSUED"]
    claim_ceiling: Literal["OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY"]
    causal_contrast_role: Literal["NULL_INTERVENTION_INVARIANCE_CONTROL"]
    physical_anchor_eligibility: Literal["INELIGIBLE"]
    family_eligibility: Literal["INELIGIBLE"]
    control_case_id: str
    application_instance_id: str
    scenario_id: str
    design_source_path: str
    design_source_sha: str
    design_freeze_commit_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    basis_contract: C19BasisContractV2
    runtime_construction: C19RuntimeConstructionV2
    dynamics_grid_derivation: DynamicsKGridDerivationProtocolV1
    response_grid: ResponseKGridManifest
    response_reference_reciprocal_index: tuple[int, ...]
    bridge_grid_derivation: BridgeKGridDerivationProtocolV1
    geometry_bundle: C19ObserverGeometryBundleV1
    candidate_sha: str


def c19_refreeze_v2_candidate_payload(
    candidate: C19RefreezeV2Candidate,
) -> dict[str, object]:
    _exact_record(candidate, C19RefreezeV2Candidate, "C19 refreeze-v2 candidate")
    return {
        "candidate_schema_version": candidate.candidate_schema_version,
        "authority_state": candidate.authority_state,
        "claim_ceiling": candidate.claim_ceiling,
        "causal_contrast_role": candidate.causal_contrast_role,
        "physical_anchor_eligibility": candidate.physical_anchor_eligibility,
        "family_eligibility": candidate.family_eligibility,
        "control_case_id": candidate.control_case_id,
        "application_instance_id": candidate.application_instance_id,
        "scenario_id": candidate.scenario_id,
        "design_source_path": candidate.design_source_path,
        "design_source_sha": candidate.design_source_sha,
        "design_freeze_commit_sha": candidate.design_freeze_commit_sha,
        "state_schema_id": candidate.state_schema_id,
        "channel_order": list(candidate.channel_order),
        "spatial_shape": list(candidate.spatial_shape),
        "basis_contract": {
            **c19_basis_contract_v2_payload(candidate.basis_contract),
            "basis_contract_sha": candidate.basis_contract.basis_contract_sha,
        },
        "runtime_construction": {
            **c19_runtime_construction_v2_payload(candidate.runtime_construction),
            "construction_sha": candidate.runtime_construction.construction_sha,
        },
        "dynamics_grid_derivation": {
            **dynamics_k_grid_derivation_protocol_v1_payload(
                candidate.dynamics_grid_derivation
            ),
            "protocol_sha": candidate.dynamics_grid_derivation.protocol_sha,
        },
        "response_grid": {
            **response_grid_payload(candidate.response_grid),
            "response_grid_sha": candidate.response_grid.response_grid_sha,
        },
        "response_reference_reciprocal_index": list(
            candidate.response_reference_reciprocal_index
        ),
        "bridge_grid_derivation": {
            **bridge_k_grid_derivation_protocol_v1_payload(
                candidate.bridge_grid_derivation
            ),
            "protocol_sha": candidate.bridge_grid_derivation.protocol_sha,
        },
        "geometry_bundle": {
            **c19_observer_geometry_bundle_v1_payload(candidate.geometry_bundle),
            "geometry_bundle_sha": candidate.geometry_bundle.geometry_bundle_sha,
        },
    }


def _positive_frequency_basis() -> tuple[np.ndarray, np.ndarray]:
    source = np.zeros((20, 10), dtype=np.complex128)
    normalizer = np.float64(1.0 / np.sqrt(2.0))
    for pair in range(10):
        source[2 * pair, pair] = normalizer
        source[2 * pair + 1, pair] = -1.0j * normalizer
    return source, source.conj().T


def _build_basis_contract() -> C19BasisContractV2:
    identity = np.eye(20, dtype=np.complex128)
    common_source = build_basis_manifest(
        role="source",
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        channel_order=C19_CHANNEL_ORDER_V2,
        vectors=identity,
    )
    common_readout = build_basis_manifest(
        role="readout",
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        channel_order=C19_CHANNEL_ORDER_V2,
        vectors=identity,
    )
    source, readout = _positive_frequency_basis()
    scenario_raw = source.T
    scenario_source = build_basis_manifest(
        role="source",
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        channel_order=C19_CHANNEL_ORDER_V2,
        vectors=scenario_raw,
    )
    scenario_readout = build_basis_manifest(
        role="readout",
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        channel_order=C19_CHANNEL_ORDER_V2,
        vectors=scenario_raw,
    )
    common_source_array = basis_manifest_array(common_source)
    common_readout_array = basis_manifest_array(common_readout)
    injection = np.einsum(
        "ab,bi->ai",
        common_source_array.T,
        source,
        optimize=False,
    )
    coisometry = np.einsum(
        "ia,ab->ib",
        readout,
        np.conjugate(common_readout_array),
        optimize=False,
    )
    identity10 = np.eye(10, dtype=np.complex128)
    j20 = np.zeros((20, 20), dtype=np.complex128)
    j2 = np.asarray(((0.0, -1.0), (1.0, 0.0)), dtype=np.complex128)
    for pair_index in range(10):
        start = 2 * pair_index
        j20[start : start + 2, start : start + 2] = j2
    source_gram = np.einsum("ai,aj->ij", source.conj(), source, optimize=False)
    readout_gram = np.einsum(
        "ia,ja->ij",
        readout,
        readout.conj(),
        optimize=False,
    )
    j_source = np.einsum("ab,bi->ai", j20, source, optimize=False)
    reduced = np.einsum("ia,aj->ij", readout, j_source, optimize=False)
    residuals = (
        np.linalg.norm(source_gram - identity10, ord=2),
        np.linalg.norm(readout_gram - identity10, ord=2),
        np.linalg.norm(j_source - 1.0j * source, ord=2),
        np.linalg.norm(reduced - 1.0j * identity10, ord=2),
    )
    if any(not np.isfinite(value) or value > 1.0e-12 for value in residuals):
        raise ValueError("C19 positive-frequency basis residual exceeds 1e-12")
    if (
        np.linalg.matrix_rank(source) != 10
        or np.linalg.matrix_rank(readout) != 10
        or np.linalg.matrix_rank(reduced) != 10
    ):
        raise ValueError("C19 positive-frequency basis rank is not 10/10")
    if injection.tobytes() != source.tobytes():
        raise ValueError("C19 source injection is not I20.T @ B+")
    if not np.array_equal(coisometry, readout):
        raise ValueError("C19 readout coisometry is not P @ conj(I20)")
    if basis_manifest_array(scenario_source).tobytes() != scenario_raw.tobytes():
        raise ValueError("C19 scenario source raw rows are not B+.T")
    if basis_manifest_array(scenario_readout).tobytes() != scenario_raw.tobytes():
        raise ValueError("C19 scenario readout raw rows are not conj(P)")
    provisional = C19BasisContractV2(
        basis_contract_schema_version=C19_BASIS_CONTRACT_V2_SCHEMA_VERSION,
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        channel_order=C19_CHANNEL_ORDER_V2,
        common_source_basis=common_source,
        common_readout_basis=common_readout,
        common_source_tensor=freeze_complex_tensor(common_source_array),
        common_readout_tensor=freeze_complex_tensor(common_readout_array),
        source_selector_b_plus=freeze_complex_tensor(source),
        readout_selector_p=freeze_complex_tensor(readout),
        source_injection=freeze_complex_tensor(injection),
        readout_coisometry=freeze_complex_tensor(coisometry),
        scenario_source_basis=scenario_source,
        scenario_readout_basis=scenario_readout,
        source_trial_vectors=freeze_complex_tensor(identity10),
        expected_actual_shell_rank=10,
        expected_matched_shell_rank=10,
        basis_contract_sha="0" * 64,
    )
    return replace(
        provisional,
        basis_contract_sha=canonical_sha(c19_basis_contract_v2_payload(provisional)),
    )


def _runtime_inputs(
    basis: C19BasisContractV2,
) -> tuple[
    PrimitiveInterface,
    BasisManifest,
    BasisManifest,
    FrozenSyntheticTarget,
]:
    interface = PrimitiveInterface(
        interface_id="interface.c19-refreeze-v2",
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        spatial_ndim=1,
        channel_order=C19_CHANNEL_ORDER_V2,
        dtype="complex128",
        backend="numpy",
    )
    identity = np.eye(20, dtype=np.complex128)
    common_source = basis.common_source_basis
    holdout = build_basis_manifest(
        role="holdout_source",
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        channel_order=C19_CHANNEL_ORDER_V2,
        vectors=identity,
    )
    common_readout = basis.common_readout_basis
    scenario_source = basis.scenario_source_basis
    scenario_readout = basis.scenario_readout_basis
    seed_operator = PrimitiveOperatorWire(
        mechanism_id="c19-target-carrier-blind",
        production_id="local_canonical_shear",
        layer_slot_id="c19-target-carrier-slot",
        operation_id="local_canonical_shear",
        interface_id=interface.interface_id,
        source_channel="q0",
        destination_channel="p0",
        offset=(0,),
        coefficient_wire=(1.0, 0.0),
    )
    seed = build_calibration_seed(
        calibration_protocol_id="c19-refreeze-v2-target-carrier",
        interface=interface,
        state_shape=(20, 8),
        dt=1.0,
        target_blind_parameters=(),
        source_basis=common_source,
        holdout_source_basis=holdout,
        readout_basis=common_readout,
        boundary_manifest_id="periodic-v1",
        operator_payload=(seed_operator,),
    )
    observation = measure_calibration_holdout(seed)
    target = freeze_synthetic_target(
        seed,
        observation,
        "c19-refreeze-v2-frozen-target",
    )
    return interface, scenario_source, scenario_readout, target


def _program_specs(
    target_spec_id: str,
) -> tuple[
    tuple[ProvenanceNode, ...],
    tuple[PrimitiveSpec, ...],
    tuple[tuple[str, str, str, float], ...],
]:
    blind_root = ProvenanceNode(
        provenance_id="c19-blind-quarter-turn-root",
        operation=ProvenanceOperation.GRAMMAR_PRIMITIVE,
        depends_on=(),
        target_refs=(),
        objective_tags=(),
        search_run_id=None,
        source_sha=C19_DESIGN_SOURCE_SHA_V2,
    )
    target_root = ProvenanceNode(
        provenance_id="c19-target-tooth-root",
        operation=ProvenanceOperation.TARGET_SPEC_READ,
        depends_on=(),
        target_refs=(target_spec_id,),
        objective_tags=(),
        search_run_id=None,
        source_sha=C19_DESIGN_SOURCE_SHA_V2,
    )
    specs: list[PrimitiveSpec] = []
    operator_rows: list[tuple[str, str, str, float]] = []
    for pair in range(10):
        q = f"q{pair}"
        p = f"p{pair}"
        rows = (
            ("blind-lower-a", q, p, 1.0, False),
            ("blind-upper", p, q, -1.0, False),
            ("blind-lower-b", q, p, 1.0, False),
            ("target-tooth-plus", p, q, C19_TARGET_TOOTH_V2, True),
            ("target-tooth-minus", p, q, -C19_TARGET_TOOTH_V2, True),
        )
        for local_index, (
            label,
            source,
            destination,
            coefficient,
            conditioned,
        ) in enumerate(rows):
            mechanism_id = f"c19-pair-{pair:02d}-slot-{local_index:02d}-{label}"
            production_id = (
                "placed_target_coefficient" if conditioned else "local_canonical_shear"
            )
            exact_coefficient = (
                sp.Rational(1, 16384)
                if coefficient == C19_TARGET_TOOTH_V2
                else sp.Rational(-1, 16384)
                if coefficient == -C19_TARGET_TOOTH_V2
                else sp.Integer(int(coefficient))
            )
            specs.append(
                PrimitiveSpec(
                    mechanism_id=mechanism_id,
                    production_id=production_id,
                    depends_on=(),
                    support_offsets=((0,),),
                    state_channels=tuple(sorted((source, destination))),
                    coefficient_expression=exact_coefficient,
                    coefficient_variable_order=(),
                    symbolic_origin_tags=("target:c19-tooth",) if conditioned else (),
                    neutral_ablation=NEUTRAL_IDENTITY_ID if conditioned else None,
                    design_objective_tags=(),
                    search_run_id=None,
                    source_sha=C19_DESIGN_SOURCE_SHA_V2,
                    design_provenance=(
                        target_root.provenance_id
                        if conditioned
                        else blind_root.provenance_id
                    ),
                )
            )
            operator_rows.append((mechanism_id, source, destination, coefficient))
    return (blind_root, target_root), tuple(specs), tuple(operator_rows)


def _apply_kernel(factory) -> np.ndarray:
    result = np.zeros((20, 20), dtype=np.complex128)
    for source_index in range(20):
        state = np.zeros((20, 8), dtype=np.complex128)
        state[source_index, 0] = 1.0
        evolved = apply_factory_step(factory, state)
        result[:, source_index] = evolved[:, 0]
    return result


def _independent_kernel(factory: LinearRealspaceFactory) -> np.ndarray:
    result = np.eye(20, dtype=np.complex128)
    channel_index = {
        channel: index for index, channel in enumerate(C19_CHANNEL_ORDER_V2)
    }
    for primitive in factory.primitives:
        if primitive.operation_id == "neutral_identity":
            continue
        source = channel_index[primitive.source_channel]
        destination = channel_index[primitive.destination_channel]
        result[destination] += complex(*primitive.coefficient_wire) * result[source]
    return result


def _slot_program_sha(factory: LinearRealspaceFactory) -> str:
    return canonical_sha(
        {
            "branch": factory.factory_role,
            "layer_slot_ids": list(factory.layer_slot_ids),
            "runtime_operator_sha": factory.runtime_operator_sha,
            "primitive_operation_ids": [
                item.operation_id for item in factory.primitives
            ],
        }
    )


def _active_effect_digest(factory: LinearRealspaceFactory) -> str:
    return canonical_sha(
        {
            "branch": factory.factory_role,
            "active_primitives": [
                {
                    "layer_slot_id": item.layer_slot_id,
                    "mechanism_id": item.mechanism_id,
                    "coefficient_wire": list(item.coefficient_wire),
                }
                for item in factory.primitives
                if item.operation_id == "local_canonical_shear"
            ],
        }
    )


def _build_dynamics_grid_derivation() -> DynamicsKGridDerivationProtocolV1:
    provisional = DynamicsKGridDerivationProtocolV1(
        protocol_schema_version=(DYNAMICS_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION),
        branch_roles=("actual", "matched_ablated"),
        transition_support_source="live-measured-transition-signed-support",
        metric_support_source="live-verified-metric-signed-support",
        derivation_algorithm="transition-and-metric-support-derived-v1",
        exact_zero_qualification_profile="exact-offset-zero-v1",
        nonzero_fallback_profile="cartesian-full-64-v1",
        caller_supplied_points_allowed=False,
        fail_closed_condition_ids=(
            "derive-after-measured-transition",
            "derive-after-verified-metric",
            "derive-each-branch-independently",
            "nonzero-support-forbids-exact-zero-profile",
        ),
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            dynamics_k_grid_derivation_protocol_v1_payload(provisional)
        ),
    )


def _build_response_grid() -> ResponseKGridManifest:
    provisional_direction = DirectionManifest(
        direction_schema_version=DIRECTION_MANIFEST_SCHEMA_VERSION,
        direction_ids=("positive-axis",),
        primitive_directions=((1,),),
        path_ids=("positive-axis-path",),
        ordered_paths=(((1,),),),
        closure_path_pairs=(),
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
        spatial_ndim=1,
        torus_denominators=(8,),
        reciprocal_indices=((1,),),
        direction_manifest=direction,
        response_grid_sha="0" * 64,
    )
    return replace(
        provisional,
        response_grid_sha=canonical_sha(response_grid_payload(provisional)),
    )


def _build_bridge_grid_derivation() -> BridgeKGridDerivationProtocolV1:
    provisional = BridgeKGridDerivationProtocolV1(
        protocol_schema_version=BRIDGE_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION,
        branch_roles=("actual", "matched_ablated"),
        spatial_shape=C19_SPATIAL_SHAPE_V2,
        support_source="live-verified-factory-signed-support",
        derivation_algorithm="support-active-axes-origin-plus-pm1-v1",
        bridge_steps=(1, 2, 4),
        caller_supplied_points_allowed=False,
        fail_closed_condition_ids=(
            "derive-after-live-factory",
            "derive-each-branch-independently",
            "shape-must-match-live-factory",
            "caller-points-forbidden",
        ),
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            bridge_k_grid_derivation_protocol_v1_payload(provisional)
        ),
    )


def _matrix_product(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.einsum("ij,jk->ik", left, right, optimize=False)


def _build_geometry_bundle(
    basis: C19BasisContractV2,
    runtime: C19RuntimeConstructionV2,
    dynamics_derivation: DynamicsKGridDerivationProtocolV1,
    response_grid: ResponseKGridManifest,
    bridge_derivation: BridgeKGridDerivationProtocolV1,
) -> C19ObserverGeometryBundleV1:
    omega = frozen_tensor_array(runtime.actual_apply_factory_step_kernel)
    source = frozen_tensor_array(basis.source_selector_b_plus)
    readout = frozen_tensor_array(basis.readout_selector_p)
    ambient = np.eye(10, dtype=np.complex128)
    tt_basis = ambient[:, (0, 1)]
    gauge_basis = ambient[:, (2, 3, 4, 5)]
    row_basis = ambient[:, (6, 7, 8, 9)]
    incidence = ambient[(0, 1, 6, 7, 8, 9), :]
    ker_c = np.zeros((10, 10), dtype=np.complex128)
    ker_c[:6, :6] = np.eye(6, dtype=np.complex128)
    curvature = incidence.conj().T.copy()
    principal = np.eye(6, dtype=np.complex128) - _matrix_product(
        _matrix_product(curvature.conj().T, ker_c), curvature
    )

    identity20 = np.eye(20, dtype=np.complex128)
    identity10 = np.eye(10, dtype=np.complex128)
    identity6 = np.eye(6, dtype=np.complex128)
    complete = np.concatenate((tt_basis, gauge_basis, row_basis), axis=1)
    range_projector = _matrix_product(curvature, curvature.conj().T)
    expected_range_projector = _matrix_product(tt_basis, tt_basis.conj().T)
    expected_range_projector += _matrix_product(row_basis, row_basis.conj().T)
    expected_gauge_projector = _matrix_product(gauge_basis, gauge_basis.conj().T)
    expected_ker_c = _matrix_product(tt_basis, tt_basis.conj().T)
    expected_ker_c += expected_gauge_projector
    residuals = (
        np.linalg.norm(_matrix_product(omega, source) - 1.0j * source, ord=2),
        np.linalg.norm(
            _matrix_product(readout, _matrix_product(omega, source))
            - 1.0j * identity10,
            ord=2,
        ),
    )
    if any(not np.isfinite(value) or value > 1.0e-12 for value in residuals):
        raise ValueError("C19 geometry symplectic/source residual exceeds 1e-12")
    exact_identities = (
        (omega.T, -omega, "J20 antisymmetry"),
        (_matrix_product(omega, omega), -identity20, "J20 square"),
        (
            _matrix_product(
                _matrix_product(omega.T, omega),
                omega,
            ),
            omega,
            "J20 symplectic identity",
        ),
        (
            _matrix_product(complete.conj().T, complete),
            identity10,
            "TT/Gauge/Row completeness",
        ),
        (
            _matrix_product(incidence, incidence.conj().T),
            identity6,
            "incidence coisometry",
        ),
        (
            _matrix_product(incidence, gauge_basis),
            np.zeros((6, 4), dtype=np.complex128),
            "Gauge kernel",
        ),
        (ker_c, expected_ker_c, "ker C projector"),
        (curvature, incidence.conj().T, "curvature frame"),
        (range_projector, expected_range_projector, "curvature range"),
        (
            identity10 - _matrix_product(incidence.conj().T, incidence),
            expected_gauge_projector,
            "incidence null projector",
        ),
        (
            principal,
            np.diag((0.0, 0.0, 1.0, 1.0, 1.0, 1.0)).astype(np.complex128),
            "conditional principal spectrum",
        ),
    )
    for observed, expected, label in exact_identities:
        if not np.array_equal(observed, expected):
            raise ValueError(f"C19 geometry {label} does not replay")
    if (
        np.linalg.matrix_rank(source) != 10
        or np.linalg.matrix_rank(readout) != 10
        or np.linalg.matrix_rank(incidence) != 6
        or np.linalg.matrix_rank(curvature) != 6
    ):
        raise ValueError("C19 geometry rank contract does not replay")

    provisional = C19ObserverGeometryBundleV1(
        geometry_bundle_schema_version=(C19_OBSERVER_GEOMETRY_BUNDLE_V1_SCHEMA_VERSION),
        kind="C19_OBSERVER_COLLAPSE_CONDITIONS",
        claim_ceiling="CONDITIONAL_PREREQUISITES_ONLY",
        evaluation_state="NOT_EVALUATED_PRE_RESPONSE",
        conditional_prediction_state="CONDITIONAL_ANALYTIC_IDENTITY_ONLY",
        state_dim=20,
        ambient_h_dim=10,
        curvature_dim=6,
        tt_dim=2,
        gauge_dim=4,
        row_dim=4,
        omega_j20=freeze_complex_tensor(omega),
        source_b_plus=freeze_complex_tensor(source),
        readout_p=freeze_complex_tensor(readout),
        tt_basis=freeze_complex_tensor(tt_basis),
        gauge_basis=freeze_complex_tensor(gauge_basis),
        row_basis=freeze_complex_tensor(row_basis),
        incidence_q=freeze_complex_tensor(incidence),
        ker_c_projector=freeze_complex_tensor(ker_c),
        curvature_frame=freeze_complex_tensor(curvature),
        conditional_principal_sine_squared=freeze_complex_tensor(principal),
        conditional_principal_spectrum=(0.0, 0.0, 1.0, 1.0, 1.0, 1.0),
        state_metric=freeze_complex_tensor(identity20),
        state_whitener=freeze_complex_tensor(identity20),
        source_metric=freeze_complex_tensor(identity10),
        source_whitener=freeze_complex_tensor(identity10),
        h_metric=freeze_complex_tensor(identity10),
        h_whitener=freeze_complex_tensor(identity10),
        curvature_metric=freeze_complex_tensor(identity6),
        curvature_whitener=freeze_complex_tensor(identity6),
        control_case_id=C19_CONTROL_CASE_ID_V2,
        application_instance_id=C19_APPLICATION_INSTANCE_ID_V2,
        scenario_id=C19_SCENARIO_ID_V2,
        operation_dag_sha=runtime.construction_trace.trace_sha,
        actual_active_step_count=runtime.actual_active_step_count,
        matched_active_step_count=runtime.matched_active_step_count,
        actual_layer_slot_count=runtime.actual_layer_slot_count,
        matched_layer_slot_count=runtime.matched_layer_slot_count,
        actual_slot_program_sha=runtime.actual_slot_program_sha,
        matched_slot_program_sha=runtime.matched_slot_program_sha,
        actual_active_effect_digest=runtime.actual_active_effect_digest,
        matched_active_effect_digest=runtime.matched_active_effect_digest,
        common_source_i20_sha=basis.common_source_tensor.tensor_sha,
        common_readout_i20_sha=basis.common_readout_tensor.tensor_sha,
        source_b_plus_sha=basis.source_selector_b_plus.tensor_sha,
        readout_p_sha=basis.readout_selector_p.tensor_sha,
        response_grid_sha=response_grid.response_grid_sha,
        dynamics_derivation_protocol_sha=dynamics_derivation.protocol_sha,
        bridge_derivation_protocol_sha=bridge_derivation.protocol_sha,
        geometry_bundle_sha="0" * 64,
    )
    return replace(
        provisional,
        geometry_bundle_sha=canonical_sha(
            c19_observer_geometry_bundle_v1_payload(provisional)
        ),
    )


def _build_runtime_construction(
    basis: C19BasisContractV2,
) -> C19RuntimeConstructionV2:
    interface, scenario_source, scenario_readout, target = _runtime_inputs(basis)
    nodes, specifications, operator_rows = _program_specs(target.target_spec_id)
    trace = build_construction_trace(
        target_spec_id=target.target_spec_id,
        provenance_nodes=nodes,
        primitive_specs=specifications,
    )
    operators = tuple(
        PrimitiveOperatorWire(
            mechanism_id=mechanism_id,
            production_id=trace.primitives[index].production_id,
            layer_slot_id=f"c19-layer-slot-{index:02d}",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=source,
            destination_channel=destination,
            offset=(0,),
            coefficient_wire=(float(coefficient), 0.0),
        )
        for index, (mechanism_id, source, destination, coefficient) in enumerate(
            operator_rows
        )
    )
    actual_input = build_factory_from_trace(
        trace,
        target,
        factory_id="factory.c19-refreeze-v2.actual",
        interface=interface,
        state_shape=(20, 8),
        dt=1.0,
        target_blind_parameters=(),
        layer_slot_ids=tuple(item.layer_slot_id for item in operators),
        operator_payload=operators,
        source_manifest_id=scenario_source.manifest_id,
        readout_basis=scenario_readout,
        boundary_manifest_id="periodic-v1",
    )
    outcome = matched_ablation(actual_input)
    if not outcome.status.defined or outcome.pair is None:
        raise RuntimeError("C19 real factory did not form a matched ablation pair")
    pair = verify_ablation_pair(outcome.pair)
    actual_view = _reverify_verified_factory(pair.actual)
    matched_view = _reverify_verified_factory(pair.ablated)
    actual_kernel = _apply_kernel(pair.actual)
    matched_kernel = _apply_kernel(pair.ablated)
    actual_independent = _independent_kernel(actual_view.factory)
    matched_independent = _independent_kernel(matched_view.factory)
    j2 = np.asarray(((0.0, -1.0), (1.0, 0.0)), dtype=np.complex128)
    j20 = np.zeros((20, 20), dtype=np.complex128)
    for pair_index in range(10):
        start = 2 * pair_index
        j20[start : start + 2, start : start + 2] = j2
    for observed in (
        actual_kernel,
        matched_kernel,
        actual_independent,
        matched_independent,
    ):
        if observed.tobytes() != j20.tobytes():
            raise ValueError("C19 runtime factory does not replay bit-exact J20")
    actual = actual_view.factory
    matched = matched_view.factory
    provisional = C19RuntimeConstructionV2(
        construction_schema_version=C19_RUNTIME_CONSTRUCTION_V2_SCHEMA_VERSION,
        state_shape=(20, 8),
        construction_trace=actual_view.trace,
        frozen_target=actual_view.target,
        actual_factory=actual,
        matched_factory=matched,
        ablation_manifest=pair.manifest,
        actual_active_step_count=sum(
            item.operation_id == "local_canonical_shear" for item in actual.primitives
        ),
        matched_active_step_count=sum(
            item.operation_id == "local_canonical_shear" for item in matched.primitives
        ),
        actual_layer_slot_count=len(actual.layer_slot_ids),
        matched_layer_slot_count=len(matched.layer_slot_ids),
        actual_primitive_count=len(actual.primitives),
        matched_primitive_count=len(matched.primitives),
        actual_slot_program_sha=_slot_program_sha(actual),
        matched_slot_program_sha=_slot_program_sha(matched),
        actual_active_effect_digest=_active_effect_digest(actual),
        matched_active_effect_digest=_active_effect_digest(matched),
        actual_support_offsets=factory_support_offsets(pair.actual, 1),
        matched_support_offsets=factory_support_offsets(pair.ablated, 1),
        actual_apply_factory_step_kernel=freeze_complex_tensor(actual_kernel),
        matched_apply_factory_step_kernel=freeze_complex_tensor(matched_kernel),
        actual_independent_replay_kernel=freeze_complex_tensor(actual_independent),
        matched_independent_replay_kernel=freeze_complex_tensor(matched_independent),
        construction_sha="0" * 64,
    )
    return replace(
        provisional,
        construction_sha=canonical_sha(
            c19_runtime_construction_v2_payload(provisional)
        ),
    )


def _build_c19_refreeze_v2_candidate() -> C19RefreezeV2Candidate:
    basis = _build_basis_contract()
    runtime = _build_runtime_construction(basis)
    dynamics_derivation = _build_dynamics_grid_derivation()
    response_grid = _build_response_grid()
    bridge_derivation = _build_bridge_grid_derivation()
    geometry_bundle = _build_geometry_bundle(
        basis,
        runtime,
        dynamics_derivation,
        response_grid,
        bridge_derivation,
    )
    provisional = C19RefreezeV2Candidate(
        candidate_schema_version=C19_REFREEZE_V2_CANDIDATE_SCHEMA_VERSION,
        authority_state=C19_AUTHORITY_STATE_V2,
        claim_ceiling=C19_CLAIM_CEILING_V2,
        causal_contrast_role=C19_CAUSAL_CONTRAST_ROLE_V2,
        physical_anchor_eligibility=C19_PHYSICAL_ANCHOR_ELIGIBILITY_V2,
        family_eligibility=C19_FAMILY_ELIGIBILITY_V2,
        control_case_id=C19_CONTROL_CASE_ID_V2,
        application_instance_id=C19_APPLICATION_INSTANCE_ID_V2,
        scenario_id=C19_SCENARIO_ID_V2,
        design_source_path=C19_DESIGN_SOURCE_PATH_V2,
        design_source_sha=C19_DESIGN_SOURCE_SHA_V2,
        design_freeze_commit_sha=C19_DESIGN_FREEZE_COMMIT_SHA_V2,
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        channel_order=C19_CHANNEL_ORDER_V2,
        spatial_shape=C19_SPATIAL_SHAPE_V2,
        basis_contract=basis,
        runtime_construction=runtime,
        dynamics_grid_derivation=dynamics_derivation,
        response_grid=response_grid,
        response_reference_reciprocal_index=(1,),
        bridge_grid_derivation=bridge_derivation,
        geometry_bundle=geometry_bundle,
        candidate_sha="0" * 64,
    )
    return replace(
        provisional,
        candidate_sha=canonical_sha(c19_refreeze_v2_candidate_payload(provisional)),
    )


def build_c19_refreeze_v2_candidate() -> C19RefreezeV2Candidate:
    """Build the sole inert C19 candidate; issue no authority capability."""

    return _build_c19_refreeze_v2_candidate()


def _verify_geometry_bundle_mechanics(
    bundle: C19ObserverGeometryBundleV1,
) -> None:
    _exact_record(
        bundle,
        C19ObserverGeometryBundleV1,
        "C19 observer geometry bundle",
    )
    if bundle.geometry_bundle_sha != canonical_sha(
        c19_observer_geometry_bundle_v1_payload(bundle)
    ):
        raise ValueError("C19 geometry bundle SHA does not match its body")
    if (
        bundle.geometry_bundle_schema_version
        != C19_OBSERVER_GEOMETRY_BUNDLE_V1_SCHEMA_VERSION
        or bundle.kind != "C19_OBSERVER_COLLAPSE_CONDITIONS"
        or bundle.claim_ceiling != "CONDITIONAL_PREREQUISITES_ONLY"
        or bundle.evaluation_state != "NOT_EVALUATED_PRE_RESPONSE"
        or bundle.conditional_prediction_state != "CONDITIONAL_ANALYTIC_IDENTITY_ONLY"
    ):
        raise ValueError("C19 geometry bundle is not conditional pre-response")
    if (
        bundle.state_dim,
        bundle.ambient_h_dim,
        bundle.curvature_dim,
        bundle.tt_dim,
        bundle.gauge_dim,
        bundle.row_dim,
    ) != (20, 10, 6, 2, 4, 4):
        raise ValueError("C19 geometry dimensions drifted")
    if (
        bundle.control_case_id != C19_CONTROL_CASE_ID_V2
        or bundle.application_instance_id != C19_APPLICATION_INSTANCE_ID_V2
        or bundle.scenario_id != C19_SCENARIO_ID_V2
        or bundle.actual_active_step_count != 50
        or bundle.matched_active_step_count != 30
        or bundle.actual_layer_slot_count != 50
        or bundle.matched_layer_slot_count != 50
    ):
        raise ValueError("C19 geometry leaf identity/count lineage drifted")

    omega = frozen_tensor_array(bundle.omega_j20)
    source = frozen_tensor_array(bundle.source_b_plus)
    readout = frozen_tensor_array(bundle.readout_p)
    tt_basis = frozen_tensor_array(bundle.tt_basis)
    gauge_basis = frozen_tensor_array(bundle.gauge_basis)
    row_basis = frozen_tensor_array(bundle.row_basis)
    incidence = frozen_tensor_array(bundle.incidence_q)
    ker_c = frozen_tensor_array(bundle.ker_c_projector)
    curvature = frozen_tensor_array(bundle.curvature_frame)
    principal = frozen_tensor_array(bundle.conditional_principal_sine_squared)
    expected_source, expected_readout = _positive_frequency_basis()
    identity20 = np.eye(20, dtype=np.complex128)
    identity10 = np.eye(10, dtype=np.complex128)
    identity6 = np.eye(6, dtype=np.complex128)
    expected_omega = np.zeros((20, 20), dtype=np.complex128)
    block = np.asarray(((0.0, -1.0), (1.0, 0.0)), dtype=np.complex128)
    for pair_index in range(10):
        start = 2 * pair_index
        expected_omega[start : start + 2, start : start + 2] = block
    ambient = identity10
    expected_tt = ambient[:, (0, 1)]
    expected_gauge = ambient[:, (2, 3, 4, 5)]
    expected_row = ambient[:, (6, 7, 8, 9)]
    expected_incidence = ambient[(0, 1, 6, 7, 8, 9), :]
    expected_ker_c = np.zeros((10, 10), dtype=np.complex128)
    expected_ker_c[:6, :6] = identity6
    expected_curvature = expected_incidence.conj().T.copy()
    expected_principal = np.diag((0.0, 0.0, 1.0, 1.0, 1.0, 1.0)).astype(np.complex128)
    exact_tensors = (
        (omega, expected_omega, "Omega/J20"),
        (source, expected_source, "B+"),
        (readout, expected_readout, "P"),
        (tt_basis, expected_tt, "TT basis"),
        (gauge_basis, expected_gauge, "Gauge basis"),
        (row_basis, expected_row, "Row basis"),
        (incidence, expected_incidence, "incidence Q"),
        (ker_c, expected_ker_c, "ker C projector"),
        (curvature, expected_curvature, "curvature frame"),
        (principal, expected_principal, "conditional principal tensor"),
    )
    for observed, expected, label in exact_tensors:
        if observed.tobytes() != expected.tobytes():
            raise ValueError(f"C19 geometry {label} tensor drifted")

    complete = np.concatenate((tt_basis, gauge_basis, row_basis), axis=1)
    tt_projector = _matrix_product(tt_basis, tt_basis.conj().T)
    gauge_projector = _matrix_product(gauge_basis, gauge_basis.conj().T)
    row_projector = _matrix_product(row_basis, row_basis.conj().T)
    replayed_principal = identity6 - _matrix_product(
        _matrix_product(curvature.conj().T, ker_c), curvature
    )
    exact_identities = (
        (omega.T, -omega, "J20 antisymmetry"),
        (_matrix_product(omega, omega), -identity20, "J20 square"),
        (
            _matrix_product(_matrix_product(omega.T, omega), omega),
            omega,
            "symplectic identity",
        ),
        (
            _matrix_product(complete.conj().T, complete),
            identity10,
            "sector completeness",
        ),
        (
            _matrix_product(incidence, incidence.conj().T),
            identity6,
            "incidence coisometry",
        ),
        (
            _matrix_product(incidence, gauge_basis),
            np.zeros((6, 4), dtype=np.complex128),
            "Gauge kernel",
        ),
        (ker_c, tt_projector + gauge_projector, "ker C decomposition"),
        (
            _matrix_product(curvature, curvature.conj().T),
            tt_projector + row_projector,
            "curvature range",
        ),
        (
            identity10 - _matrix_product(incidence.conj().T, incidence),
            gauge_projector,
            "incidence kernel",
        ),
        (replayed_principal, principal, "conditional principal replay"),
    )
    for observed, expected, label in exact_identities:
        if not np.array_equal(observed, expected):
            raise ValueError(f"C19 geometry {label} does not replay")
    residuals = (
        np.linalg.norm(_matrix_product(omega, source) - 1.0j * source, ord=2),
        np.linalg.norm(
            _matrix_product(readout, _matrix_product(omega, source))
            - 1.0j * identity10,
            ord=2,
        ),
    )
    if any(not np.isfinite(value) or value > 1.0e-12 for value in residuals):
        raise ValueError("C19 geometry source/symplectic residual exceeds 1e-12")
    if (
        np.linalg.matrix_rank(source) != 10
        or np.linalg.matrix_rank(readout) != 10
        or np.linalg.matrix_rank(incidence) != 6
        or np.linalg.matrix_rank(curvature) != 6
    ):
        raise ValueError("C19 geometry rank contract does not replay")
    if bundle.conditional_principal_spectrum != (
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
        1.0,
    ):
        raise ValueError("C19 conditional principal spectrum drifted")

    metric_specs = (
        (bundle.state_metric, bundle.state_whitener, identity20, "state"),
        (bundle.source_metric, bundle.source_whitener, identity10, "source"),
        (bundle.h_metric, bundle.h_whitener, identity10, "H_h"),
        (
            bundle.curvature_metric,
            bundle.curvature_whitener,
            identity6,
            "curvature",
        ),
    )
    for metric_tensor, whitener_tensor, identity, label in metric_specs:
        metric = frozen_tensor_array(metric_tensor)
        whitener = frozen_tensor_array(whitener_tensor)
        if (
            metric.tobytes() != identity.tobytes()
            or whitener.tobytes() != identity.tobytes()
            or not np.array_equal(metric.conj().T, metric)
            or not np.all(np.linalg.eigvalsh(metric) > 0.0)
            or not np.array_equal(
                _matrix_product(
                    _matrix_product(whitener.conj().T, metric),
                    whitener,
                ),
                identity,
            )
        ):
            raise ValueError(f"C19 {label} metric/whitener contract drifted")

    expected_i20_sha = freeze_complex_tensor(identity20).tensor_sha
    if (
        bundle.common_source_i20_sha != expected_i20_sha
        or bundle.common_readout_i20_sha != expected_i20_sha
        or bundle.source_b_plus_sha != bundle.source_b_plus.tensor_sha
        or bundle.readout_p_sha != bundle.readout_p.tensor_sha
    ):
        raise ValueError("C19 geometry tensor leaf lineage drifted")


def compile_c19_observer_geometry_bundle_v1(
    bundle: C19ObserverGeometryBundleV1,
) -> C19ObserverGeometryBundleV1:
    """Strictly compile the canonical raw conditional bundle, issuing no verdict."""

    _verify_geometry_bundle_mechanics(bundle)
    expected = _build_c19_refreeze_v2_candidate().geometry_bundle
    if bundle != expected:
        raise ValueError("C19 geometry differs from the canonical closed replay")
    return bundle


def verify_c19_refreeze_v2_candidate(
    candidate: C19RefreezeV2Candidate,
) -> C19RefreezeV2Candidate:
    """Verify a raw body by exact equality with a fresh closed replay."""

    _exact_record(candidate, C19RefreezeV2Candidate, "C19 refreeze-v2 candidate")
    if (
        candidate.authority_state != C19_AUTHORITY_STATE_V2
        or candidate.claim_ceiling != C19_CLAIM_CEILING_V2
        or candidate.causal_contrast_role != C19_CAUSAL_CONTRAST_ROLE_V2
        or candidate.physical_anchor_eligibility != C19_PHYSICAL_ANCHOR_ELIGIBILITY_V2
        or candidate.family_eligibility != C19_FAMILY_ELIGIBILITY_V2
    ):
        raise ValueError("C19 authority/claim ceiling drifted")
    _exact_record(
        candidate.runtime_construction,
        C19RuntimeConstructionV2,
        "C19 runtime construction",
    )
    _exact_record(
        candidate.basis_contract,
        C19BasisContractV2,
        "C19 basis contract",
    )
    _exact_record(
        candidate.dynamics_grid_derivation,
        DynamicsKGridDerivationProtocolV1,
        "dynamics grid derivation protocol",
    )
    _exact_record(
        candidate.response_grid,
        ResponseKGridManifest,
        "response grid",
    )
    _exact_record(
        candidate.response_grid.direction_manifest,
        DirectionManifest,
        "response direction manifest",
    )
    _exact_record(
        candidate.bridge_grid_derivation,
        BridgeKGridDerivationProtocolV1,
        "bridge grid derivation protocol",
    )
    _verify_geometry_bundle_mechanics(candidate.geometry_bundle)
    if candidate.candidate_sha != canonical_sha(
        c19_refreeze_v2_candidate_payload(candidate)
    ):
        raise ValueError("C19 candidate SHA does not match its complete body")
    if candidate.runtime_construction.construction_sha != canonical_sha(
        c19_runtime_construction_v2_payload(candidate.runtime_construction)
    ):
        raise ValueError("C19 runtime construction SHA does not match its body")
    if candidate.basis_contract.basis_contract_sha != canonical_sha(
        c19_basis_contract_v2_payload(candidate.basis_contract)
    ):
        raise ValueError("C19 basis contract SHA does not match its body")
    if candidate.dynamics_grid_derivation.protocol_sha != canonical_sha(
        dynamics_k_grid_derivation_protocol_v1_payload(
            candidate.dynamics_grid_derivation
        )
    ):
        raise ValueError("C19 dynamics derivation SHA does not match its body")
    if (
        candidate.response_grid.direction_manifest.direction_manifest_sha
        != canonical_sha(
            direction_manifest_payload(candidate.response_grid.direction_manifest)
        )
    ):
        raise ValueError("C19 response direction SHA does not match its body")
    if candidate.response_grid.response_grid_sha != canonical_sha(
        response_grid_payload(candidate.response_grid)
    ):
        raise ValueError("C19 response grid SHA does not match its body")
    if candidate.bridge_grid_derivation.protocol_sha != canonical_sha(
        bridge_k_grid_derivation_protocol_v1_payload(candidate.bridge_grid_derivation)
    ):
        raise ValueError("C19 bridge derivation SHA does not match its body")
    geometry = candidate.geometry_bundle
    runtime = candidate.runtime_construction
    basis = candidate.basis_contract
    if (
        geometry.operation_dag_sha != runtime.construction_trace.trace_sha
        or geometry.actual_slot_program_sha != runtime.actual_slot_program_sha
        or geometry.matched_slot_program_sha != runtime.matched_slot_program_sha
        or geometry.actual_active_effect_digest != runtime.actual_active_effect_digest
        or geometry.matched_active_effect_digest != runtime.matched_active_effect_digest
        or geometry.common_source_i20_sha != basis.common_source_tensor.tensor_sha
        or geometry.common_readout_i20_sha != basis.common_readout_tensor.tensor_sha
        or geometry.source_b_plus_sha != basis.source_selector_b_plus.tensor_sha
        or geometry.readout_p_sha != basis.readout_selector_p.tensor_sha
        or geometry.response_grid_sha != candidate.response_grid.response_grid_sha
        or geometry.dynamics_derivation_protocol_sha
        != candidate.dynamics_grid_derivation.protocol_sha
        or geometry.bridge_derivation_protocol_sha
        != candidate.bridge_grid_derivation.protocol_sha
    ):
        raise ValueError("C19 geometry leaf lineage differs from candidate")
    expected = _build_c19_refreeze_v2_candidate()
    if candidate != expected:
        raise ValueError("C19 candidate differs from the canonical closed replay")
    return candidate


__all__ = [
    "C19_APPLICATION_INSTANCE_ID_V2",
    "C19_AUTHORITY_STATE_V2",
    "C19_CAUSAL_CONTRAST_ROLE_V2",
    "C19_CLAIM_CEILING_V2",
    "C19_BASIS_CONTRACT_V2_SCHEMA_VERSION",
    "BRIDGE_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION",
    "C19_CHANNEL_ORDER_V2",
    "C19_CONTROL_CASE_ID_V2",
    "C19_DESIGN_FREEZE_COMMIT_SHA_V2",
    "C19_DESIGN_SOURCE_PATH_V2",
    "C19_DESIGN_SOURCE_SHA_V2",
    "C19_REFREEZE_V2_CANDIDATE_SCHEMA_VERSION",
    "C19_RUNTIME_CONSTRUCTION_V2_SCHEMA_VERSION",
    "C19_OBSERVER_GEOMETRY_BUNDLE_V1_SCHEMA_VERSION",
    "DYNAMICS_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION",
    "C19_SCENARIO_ID_V2",
    "C19_FAMILY_ELIGIBILITY_V2",
    "C19_PHYSICAL_ANCHOR_ELIGIBILITY_V2",
    "C19_SPATIAL_SHAPE_V2",
    "C19_STATE_SCHEMA_ID_V2",
    "C19RefreezeV2Candidate",
    "C19BasisContractV2",
    "C19ObserverGeometryBundleV1",
    "BridgeKGridDerivationProtocolV1",
    "DynamicsKGridDerivationProtocolV1",
    "C19RuntimeConstructionV2",
    "build_c19_refreeze_v2_candidate",
    "c19_basis_contract_v2_payload",
    "bridge_k_grid_derivation_protocol_v1_payload",
    "c19_refreeze_v2_candidate_payload",
    "c19_runtime_construction_v2_payload",
    "c19_observer_geometry_bundle_v1_payload",
    "compile_c19_observer_geometry_bundle_v1",
    "dynamics_k_grid_derivation_protocol_v1_payload",
    "verify_c19_refreeze_v2_candidate",
]
