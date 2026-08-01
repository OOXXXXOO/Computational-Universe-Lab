"""Authority-neutral raw contracts for the provisional C19 Parent-v3 wire.

This module deliberately issues no capability.  Its zero-argument builder
returns a raw, self-hashed application tree and its verifier compares that tree
with a fresh closed replay of the committed C19 construction.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass, replace
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Literal

from .ablation import ablation_manifest_payload
from .c19_refreeze_v2 import (
    C19_DESIGN_SOURCE_PATH_V2,
    C19_SPATIAL_SHAPE_V2,
    C19_STATE_SCHEMA_ID_V2,
    BridgeKGridDerivationProtocolV1,
    C19BasisContractV2,
    C19ObserverGeometryBundleV1,
    C19RuntimeConstructionV2,
    DynamicsKGridDerivationProtocolV1,
    bridge_k_grid_derivation_protocol_v1_payload,
    build_c19_refreeze_v2_candidate,
    c19_basis_contract_v2_payload,
    c19_observer_geometry_bundle_v1_payload,
    c19_runtime_construction_v2_payload,
    dynamics_k_grid_derivation_protocol_v1_payload,
    verify_c19_refreeze_v2_candidate,
)
from .evidence import canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    Primitive,
    primitive_payload,
    primitive_sha,
)
from .grids import DirectionManifest, ResponseKGridManifest, response_grid_payload
from .metric import METRIC_SUPPORT_SCHEMA_VERSION, metric_support_payload


CURRENT_SCENARIO_RESPONSE_CONTRACT_V3_SCHEMA_VERSION = (
    "v3m0.current-scenario-response-contract.v3"
)
CURRENT_SCENARIO_AUTHORITY_V3_SCHEMA_VERSION = "v3m0.current-scenario-authority.v3"
CURRENT_APPLICATION_AUTHORITY_V3_SCHEMA_VERSION = (
    "v3m0.current-application-authority.v3"
)
PROVISIONAL_AUTHORITY_STATE = "PROVISIONAL_NOT_ISSUED"
CONSTRUCTION_DEPENDENCY_CLOSURE_STATE = (
    "PROVISIONAL_CONSTRUCTION_DEPENDENCIES_NOT_SIGNED"
)
RUNTIME_ARTIFACT_STATE = "DYNAMICS_AND_BRIDGE_NOT_DERIVED_PRE_RESPONSE"
MEASUREMENT_STATE = "NOT_EVALUATED_PRE_RESPONSE"
METRIC_SUPPORT_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION = (
    "v3m0.metric-support-derivation-protocol.v1"
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")

_CONSTRUCTION_DEPENDENCY_PATHS = (
    C19_DESIGN_SOURCE_PATH_V2,
    "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md",
    "rulespace_v3/ablation.py",
    "rulespace_v3/c19_refreeze_v2.py",
    "rulespace_v3/evidence.py",
    "rulespace_v3/factory.py",
    "rulespace_v3/grids.py",
    "rulespace_v3/metric.py",
    "rulespace_v3/parent_v3_contracts.py",
    "rulespace_v3/trace.py",
)


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an exact int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return tuple(_text(item, f"{field}[{index}]") for index, item in enumerate(value))


def _positive_int_tuple(value: object, field: str) -> tuple[int, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return tuple(
        _positive_int(item, f"{field}[{index}]") for index, item in enumerate(value)
    )


def _integer_tuple(value: object, field: str, *, ndim: int) -> tuple[int, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    if len(value) != ndim:
        raise ValueError(f"{field} dimension mismatch")
    result: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise TypeError(f"{field}[{index}] must be an exact int")
        result.append(item)
    return tuple(result)


def _support_offsets(
    value: object,
    field: str,
    *,
    ndim: int,
) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    result = tuple(
        _integer_tuple(row, f"{field}[{index}]", ndim=ndim)
        for index, row in enumerate(value)
    )
    if result != tuple(sorted(set(result))):
        raise ValueError(f"{field} must be unique and lexicographic")
    return result


def _require_plain_wire_tree(value: object, field: str) -> None:
    """Reject container subclasses and undeclared dataclass attributes."""

    if is_dataclass(value) and not isinstance(value, type):
        record_type = type(value)
        expected_fields = tuple(dataclass_fields(record_type))
        if frozenset(vars(value)) != frozenset(item.name for item in expected_fields):
            raise ValueError(f"{field} contains unknown or missing fields")
        for item in expected_fields:
            _require_plain_wire_tree(getattr(value, item.name), f"{field}.{item.name}")
        return
    if isinstance(value, tuple):
        if type(value) is not tuple:
            raise TypeError(f"{field} must be an exact tuple")
        for index, item in enumerate(value):
            _require_plain_wire_tree(item, f"{field}[{index}]")
        return
    if isinstance(value, Enum):
        return
    if type(value) in (str, int, float, bool, type(None)):
        return
    raise TypeError(f"{field} contains a non-wire value of type {type(value).__name__}")


def _require_exact_recursive_match(
    observed: object,
    expected: object,
    field: str,
) -> None:
    """Compare a raw tree without dataclass-equality or container coercion."""

    if type(observed) is not type(expected):
        raise TypeError(
            f"{field} type differs from the closed replay: "
            f"{type(observed).__name__} != {type(expected).__name__}"
        )
    if is_dataclass(expected) and not isinstance(expected, type):
        record_type = type(expected)
        _exact_record(observed, record_type, field)
        for item in dataclass_fields(record_type):
            _require_exact_recursive_match(
                getattr(observed, item.name),
                getattr(expected, item.name),
                f"{field}.{item.name}",
            )
        return
    if type(expected) is tuple:
        if len(observed) != len(expected):
            raise ValueError(f"{field} length differs from the closed replay")
        for index, (observed_item, expected_item) in enumerate(zip(observed, expected)):
            _require_exact_recursive_match(
                observed_item,
                expected_item,
                f"{field}[{index}]",
            )
        return
    if observed != expected:
        raise ValueError(f"{field} differs from the closed replay")


def _basis_record(basis: BasisManifest) -> dict[str, object]:
    _exact_record(basis, BasisManifest, "common basis")
    return {
        "basis_schema_version": basis.basis_schema_version,
        "role": basis.role,
        "state_schema_id": basis.state_schema_id,
        "channel_order": list(basis.channel_order),
        "vectors_wire": [[list(wire) for wire in row] for row in basis.vectors_wire],
        "manifest_id": basis.manifest_id,
    }


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    _exact_record(tensor, FrozenComplexTensor, "common basis tensor")
    return {
        "tensor_schema_version": tensor.tensor_schema_version,
        "shape": list(tensor.shape),
        "values_wire": [list(wire) for wire in tensor.values_wire],
        "tensor_sha": tensor.tensor_sha,
    }


def _basis_contract_record(contract: C19BasisContractV2) -> dict[str, object]:
    return {
        **c19_basis_contract_v2_payload(contract),
        "basis_contract_sha": contract.basis_contract_sha,
    }


def _runtime_record(runtime: C19RuntimeConstructionV2) -> dict[str, object]:
    return {
        **c19_runtime_construction_v2_payload(runtime),
        "construction_sha": runtime.construction_sha,
    }


def _dynamics_protocol_record(
    protocol: DynamicsKGridDerivationProtocolV1,
) -> dict[str, object]:
    return {
        **dynamics_k_grid_derivation_protocol_v1_payload(protocol),
        "protocol_sha": protocol.protocol_sha,
    }


def _response_grid_record(grid: ResponseKGridManifest) -> dict[str, object]:
    _exact_record(grid, ResponseKGridManifest, "response grid")
    _exact_record(
        grid.direction_manifest,
        DirectionManifest,
        "response direction manifest",
    )
    _require_plain_wire_tree(grid, "response grid")
    return {**response_grid_payload(grid), "response_grid_sha": grid.response_grid_sha}


def _bridge_protocol_record(
    protocol: BridgeKGridDerivationProtocolV1,
) -> dict[str, object]:
    return {
        **bridge_k_grid_derivation_protocol_v1_payload(protocol),
        "protocol_sha": protocol.protocol_sha,
    }


def _geometry_record(bundle: C19ObserverGeometryBundleV1) -> dict[str, object]:
    return {
        **c19_observer_geometry_bundle_v1_payload(bundle),
        "geometry_bundle_sha": bundle.geometry_bundle_sha,
    }


OperationRegistryRow = tuple[Literal["actual", "matched_ablated"], int, str, Primitive]


def _operation_registry_payload(
    registry: tuple[OperationRegistryRow, ...],
) -> list[dict[str, object]]:
    if type(registry) is not tuple or len(registry) != 100:
        raise TypeError("operation_registry must be the exact 100-row tuple")
    result: list[dict[str, object]] = []
    for index, row in enumerate(registry):
        if type(row) is not tuple or len(row) != 4:
            raise TypeError(f"operation_registry[{index}] has the wrong row type")
        branch, ordinal, slot_id, primitive = row
        if type(branch) is not str or branch not in ("actual", "matched_ablated"):
            raise ValueError(f"operation_registry[{index}] branch drifted")
        if type(ordinal) is not int or ordinal < 0:
            raise TypeError(f"operation_registry[{index}] ordinal drifted")
        if type(slot_id) is not str or not slot_id:
            raise TypeError(f"operation_registry[{index}] slot drifted")
        _exact_record(primitive, Primitive, f"operation_registry[{index}].primitive")
        result.append(
            {
                "branch_role": branch,
                "ordinal": ordinal,
                "layer_slot_id": slot_id,
                "primitive": {
                    **primitive_payload(primitive),
                    "primitive_sha": primitive_sha(primitive),
                },
            }
        )
    return result


@dataclass(frozen=True)
class MetricSupportDerivationProtocolV1:
    protocol_schema_version: str
    metric_kind: Literal["constant-state-v1"]
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    spatial_ndim: int
    state_metric: FrozenComplexTensor
    normalization_id: Literal["trace-at-zero-equals-state-dim-v1"]
    support_derivation_id: Literal["constant-kernel-origin-only-v1"]
    metric_support_offsets: tuple[tuple[int, ...], ...]
    metric_support_sha: str
    caller_supplied_support_allowed: Literal[False]
    protocol_sha: str


def metric_support_derivation_protocol_v1_payload(
    protocol: MetricSupportDerivationProtocolV1,
) -> dict[str, object]:
    _exact_record(
        protocol,
        MetricSupportDerivationProtocolV1,
        "metric support derivation protocol v1",
    )
    _text(protocol.protocol_schema_version, "metric protocol schema_version")
    _text(protocol.metric_kind, "metric protocol kind")
    _text(protocol.state_schema_id, "metric protocol state_schema_id")
    _string_tuple(protocol.channel_order, "metric protocol channel_order")
    spatial_shape = _positive_int_tuple(
        protocol.spatial_shape,
        "metric protocol spatial_shape",
    )
    spatial_ndim = _positive_int(
        protocol.spatial_ndim,
        "metric protocol spatial_ndim",
    )
    if len(spatial_shape) != spatial_ndim:
        raise ValueError("metric protocol spatial dimension mismatch")
    _exact_record(
        protocol.state_metric,
        FrozenComplexTensor,
        "metric protocol state_metric",
    )
    _text(protocol.normalization_id, "metric protocol normalization_id")
    _text(protocol.support_derivation_id, "metric protocol support_derivation_id")
    _support_offsets(
        protocol.metric_support_offsets,
        "metric protocol support_offsets",
        ndim=spatial_ndim,
    )
    _sha(protocol.metric_support_sha, "metric protocol support_sha")
    if protocol.caller_supplied_support_allowed is not False:
        raise ValueError("metric protocol permits caller-supplied support")
    _sha(protocol.protocol_sha, "metric protocol protocol_sha")
    _require_plain_wire_tree(protocol, "metric support derivation protocol v1")
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "metric_kind": protocol.metric_kind,
        "state_schema_id": protocol.state_schema_id,
        "channel_order": list(protocol.channel_order),
        "spatial_shape": list(protocol.spatial_shape),
        "spatial_ndim": protocol.spatial_ndim,
        "state_metric": _tensor_record(protocol.state_metric),
        "normalization_id": protocol.normalization_id,
        "support_derivation_id": protocol.support_derivation_id,
        "metric_support_offsets": [
            list(offset) for offset in protocol.metric_support_offsets
        ],
        "metric_support_sha": protocol.metric_support_sha,
        "caller_supplied_support_allowed": (protocol.caller_supplied_support_allowed),
    }


def _build_metric_support_protocol(
    state_metric: FrozenComplexTensor,
) -> MetricSupportDerivationProtocolV1:
    support_offsets = ((0,),)
    support_sha = canonical_sha(metric_support_payload(support_offsets))
    provisional = MetricSupportDerivationProtocolV1(
        protocol_schema_version=(METRIC_SUPPORT_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION),
        metric_kind="constant-state-v1",
        state_schema_id=C19_STATE_SCHEMA_ID_V2,
        channel_order=tuple(
            channel for pair in range(10) for channel in (f"q{pair}", f"p{pair}")
        ),
        spatial_shape=C19_SPATIAL_SHAPE_V2,
        spatial_ndim=1,
        state_metric=state_metric,
        normalization_id="trace-at-zero-equals-state-dim-v1",
        support_derivation_id="constant-kernel-origin-only-v1",
        metric_support_offsets=support_offsets,
        metric_support_sha=support_sha,
        caller_supplied_support_allowed=False,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            metric_support_derivation_protocol_v1_payload(provisional)
        ),
    )


def verify_metric_support_derivation_protocol_v1(
    protocol: MetricSupportDerivationProtocolV1,
) -> MetricSupportDerivationProtocolV1:
    """Verify the exact C19 pre-response metric-support derivation body."""

    payload = metric_support_derivation_protocol_v1_payload(protocol)
    support_payload = metric_support_payload(protocol.metric_support_offsets)
    if support_payload.get("support_schema_version") != (METRIC_SUPPORT_SCHEMA_VERSION):
        raise ValueError("metric support canonical owner schema drifted")
    if protocol.metric_support_sha != canonical_sha(support_payload):
        raise ValueError("metric support SHA does not match the canonical owner")
    if protocol.protocol_sha != canonical_sha(payload):
        raise ValueError("metric support protocol SHA does not match its body")
    candidate = verify_c19_refreeze_v2_candidate(build_c19_refreeze_v2_candidate())
    expected = _build_metric_support_protocol(candidate.geometry_bundle.state_metric)
    _require_exact_recursive_match(
        protocol,
        expected,
        "metric support derivation protocol v1",
    )
    return protocol


@dataclass(frozen=True)
class CurrentScenarioResponseContractV3:
    response_contract_schema_version: str
    contract_state: Literal["PROVISIONAL_NOT_ISSUED"]
    control_case_id: str
    application_instance_id: str
    scenario_id: str
    basis_contract: C19BasisContractV2
    dynamics_grid_derivation: DynamicsKGridDerivationProtocolV1
    metric_support_derivation: MetricSupportDerivationProtocolV1
    response_grid: ResponseKGridManifest
    response_reference_reciprocal_index: tuple[int, ...]
    bridge_grid_derivation: BridgeKGridDerivationProtocolV1
    geometry_bundle: C19ObserverGeometryBundleV1
    runtime_construction_sha: str
    actual_factory_sha: str
    matched_factory_sha: str
    operation_dag_sha: str
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    runtime_artifact_state: Literal["DYNAMICS_AND_BRIDGE_NOT_DERIVED_PRE_RESPONSE"]
    measurement_state: Literal["NOT_EVALUATED_PRE_RESPONSE"]
    uses_global_fft_projection: Literal[False]
    uses_per_k_time_step_projector: Literal[False]
    response_contract_sha: str


def current_scenario_response_contract_v3_payload(
    contract: CurrentScenarioResponseContractV3,
) -> dict[str, object]:
    _exact_record(
        contract,
        CurrentScenarioResponseContractV3,
        "current scenario response contract v3",
    )
    _require_plain_wire_tree(contract, "current scenario response contract v3")
    response_grid = _response_grid_record(contract.response_grid)
    reference_index = _integer_tuple(
        contract.response_reference_reciprocal_index,
        "response_reference_reciprocal_index",
        ndim=_positive_int(
            contract.response_grid.spatial_ndim,
            "response grid spatial_ndim",
        ),
    )
    return {
        "response_contract_schema_version": contract.response_contract_schema_version,
        "contract_state": contract.contract_state,
        "control_case_id": contract.control_case_id,
        "application_instance_id": contract.application_instance_id,
        "scenario_id": contract.scenario_id,
        "basis_contract": _basis_contract_record(contract.basis_contract),
        "dynamics_grid_derivation": _dynamics_protocol_record(
            contract.dynamics_grid_derivation
        ),
        "metric_support_derivation": {
            **metric_support_derivation_protocol_v1_payload(
                contract.metric_support_derivation
            ),
            "protocol_sha": contract.metric_support_derivation.protocol_sha,
        },
        "response_grid": response_grid,
        "response_reference_reciprocal_index": list(reference_index),
        "bridge_grid_derivation": _bridge_protocol_record(
            contract.bridge_grid_derivation
        ),
        "geometry_bundle": _geometry_record(contract.geometry_bundle),
        "runtime_construction_sha": contract.runtime_construction_sha,
        "actual_factory_sha": contract.actual_factory_sha,
        "matched_factory_sha": contract.matched_factory_sha,
        "operation_dag_sha": contract.operation_dag_sha,
        "expected_actual_shell_rank": contract.expected_actual_shell_rank,
        "expected_matched_shell_rank": contract.expected_matched_shell_rank,
        "runtime_artifact_state": contract.runtime_artifact_state,
        "measurement_state": contract.measurement_state,
        "uses_global_fft_projection": contract.uses_global_fft_projection,
        "uses_per_k_time_step_projector": contract.uses_per_k_time_step_projector,
    }


@dataclass(frozen=True)
class CurrentScenarioAuthorityV3:
    scenario_authority_schema_version: str
    authority_state: Literal["PROVISIONAL_NOT_ISSUED"]
    control_case_id: str
    application_instance_id: str
    scenario_id: str
    source_disposition: Literal["C19_REFREEZE_V2_REVIEWED"]
    source_candidate_sha: str
    source_runtime_construction_sha: str
    source_basis_contract_sha: str
    response_contract: CurrentScenarioResponseContractV3
    scenario_authority_sha: str


def current_scenario_authority_v3_payload(
    authority: CurrentScenarioAuthorityV3,
) -> dict[str, object]:
    _exact_record(
        authority,
        CurrentScenarioAuthorityV3,
        "current scenario authority v3",
    )
    return {
        "scenario_authority_schema_version": (
            authority.scenario_authority_schema_version
        ),
        "authority_state": authority.authority_state,
        "control_case_id": authority.control_case_id,
        "application_instance_id": authority.application_instance_id,
        "scenario_id": authority.scenario_id,
        "source_disposition": authority.source_disposition,
        "source_candidate_sha": authority.source_candidate_sha,
        "source_runtime_construction_sha": (authority.source_runtime_construction_sha),
        "source_basis_contract_sha": authority.source_basis_contract_sha,
        "response_contract": {
            **current_scenario_response_contract_v3_payload(
                authority.response_contract
            ),
            "response_contract_sha": authority.response_contract.response_contract_sha,
        },
    }


@dataclass(frozen=True)
class CurrentApplicationAuthorityV3:
    application_authority_schema_version: str
    authority_state: Literal["PROVISIONAL_NOT_ISSUED"]
    claim_ceiling: str
    causal_contrast_role: str
    physical_anchor_eligibility: str
    family_eligibility: str
    control_case_id: str
    application_instance_id: str
    source_disposition: Literal["C19_REFREEZE_V2_REVIEWED"]
    source_candidate_sha: str
    design_source_path: str
    design_source_sha: str
    design_freeze_commit_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    state_shape: tuple[int, ...]
    spatial_shape: tuple[int, ...]
    spatial_ndim: int
    common_source_basis: BasisManifest
    common_readout_basis: BasisManifest
    common_source_tensor: FrozenComplexTensor
    common_readout_tensor: FrozenComplexTensor
    runtime_construction: C19RuntimeConstructionV2
    runtime_construction_sha: str
    basis_contract_sha: str
    grid_protocol_root_sha: str
    operation_registry: tuple[OperationRegistryRow, ...]
    operation_registry_sha: str
    construction_dependency_closure_state: Literal[
        "PROVISIONAL_CONSTRUCTION_DEPENDENCIES_NOT_SIGNED"
    ]
    construction_dependency_closure: tuple[tuple[str, str], ...]
    construction_dependency_closure_sha: str
    actual_active_step_count: int
    matched_active_step_count: int
    actual_layer_slot_count: int
    matched_layer_slot_count: int
    actual_primitive_count: int
    matched_primitive_count: int
    matched_neutral_identity_count: int
    operation_dag_sha: str
    target_spec_sha: str
    actual_factory_sha: str
    matched_factory_sha: str
    ablation_manifest_sha: str
    actual_slot_program_sha: str
    matched_slot_program_sha: str
    actual_active_effect_digest: str
    matched_active_effect_digest: str
    scenario_authorities: tuple[CurrentScenarioAuthorityV3, ...]
    application_authority_sha: str


def current_application_authority_v3_payload(
    authority: CurrentApplicationAuthorityV3,
) -> dict[str, object]:
    _exact_record(
        authority,
        CurrentApplicationAuthorityV3,
        "current application authority v3",
    )
    _require_plain_wire_tree(authority, "current application authority v3")
    if type(authority.construction_dependency_closure) is not tuple:
        raise TypeError("construction_dependency_closure must be an exact tuple")
    closure_payload: list[list[str]] = []
    for index, entry in enumerate(authority.construction_dependency_closure):
        if type(entry) is not tuple or len(entry) != 2:
            raise TypeError(
                f"construction_dependency_closure[{index}] must be a path/SHA pair"
            )
        path = _text(entry[0], f"construction_dependency_closure[{index}].path")
        source_sha = _sha(
            entry[1],
            f"construction_dependency_closure[{index}].sha",
        )
        closure_payload.append([path, source_sha])
    if type(authority.scenario_authorities) is not tuple:
        raise TypeError("scenario_authorities must be an exact tuple")
    return {
        "application_authority_schema_version": (
            authority.application_authority_schema_version
        ),
        "authority_state": authority.authority_state,
        "claim_ceiling": authority.claim_ceiling,
        "causal_contrast_role": authority.causal_contrast_role,
        "physical_anchor_eligibility": authority.physical_anchor_eligibility,
        "family_eligibility": authority.family_eligibility,
        "control_case_id": authority.control_case_id,
        "application_instance_id": authority.application_instance_id,
        "source_disposition": authority.source_disposition,
        "source_candidate_sha": authority.source_candidate_sha,
        "design_source_path": authority.design_source_path,
        "design_source_sha": authority.design_source_sha,
        "design_freeze_commit_sha": authority.design_freeze_commit_sha,
        "state_schema_id": authority.state_schema_id,
        "channel_order": list(authority.channel_order),
        "state_shape": list(authority.state_shape),
        "spatial_shape": list(authority.spatial_shape),
        "spatial_ndim": authority.spatial_ndim,
        "common_source_basis": _basis_record(authority.common_source_basis),
        "common_readout_basis": _basis_record(authority.common_readout_basis),
        "common_source_tensor": _tensor_record(authority.common_source_tensor),
        "common_readout_tensor": _tensor_record(authority.common_readout_tensor),
        "runtime_construction": _runtime_record(authority.runtime_construction),
        "runtime_construction_sha": authority.runtime_construction_sha,
        "basis_contract_sha": authority.basis_contract_sha,
        "grid_protocol_root_sha": authority.grid_protocol_root_sha,
        "operation_registry": _operation_registry_payload(authority.operation_registry),
        "operation_registry_sha": authority.operation_registry_sha,
        "construction_dependency_closure_state": (
            authority.construction_dependency_closure_state
        ),
        "construction_dependency_closure": closure_payload,
        "construction_dependency_closure_sha": (
            authority.construction_dependency_closure_sha
        ),
        "actual_active_step_count": authority.actual_active_step_count,
        "matched_active_step_count": authority.matched_active_step_count,
        "actual_layer_slot_count": authority.actual_layer_slot_count,
        "matched_layer_slot_count": authority.matched_layer_slot_count,
        "actual_primitive_count": authority.actual_primitive_count,
        "matched_primitive_count": authority.matched_primitive_count,
        "matched_neutral_identity_count": authority.matched_neutral_identity_count,
        "operation_dag_sha": authority.operation_dag_sha,
        "target_spec_sha": authority.target_spec_sha,
        "actual_factory_sha": authority.actual_factory_sha,
        "matched_factory_sha": authority.matched_factory_sha,
        "ablation_manifest_sha": authority.ablation_manifest_sha,
        "actual_slot_program_sha": authority.actual_slot_program_sha,
        "matched_slot_program_sha": authority.matched_slot_program_sha,
        "actual_active_effect_digest": authority.actual_active_effect_digest,
        "matched_active_effect_digest": authority.matched_active_effect_digest,
        "scenario_authorities": [
            {
                **current_scenario_authority_v3_payload(item),
                "scenario_authority_sha": item.scenario_authority_sha,
            }
            for item in authority.scenario_authorities
        ],
    }


def _grid_protocol_root(
    candidate,
    metric_support: MetricSupportDerivationProtocolV1,
) -> str:
    return canonical_sha(
        {
            "dynamics_grid_derivation": _dynamics_protocol_record(
                candidate.dynamics_grid_derivation
            ),
            "metric_support_derivation": {
                **metric_support_derivation_protocol_v1_payload(metric_support),
                "protocol_sha": metric_support.protocol_sha,
            },
            "response_grid": _response_grid_record(candidate.response_grid),
            "bridge_grid_derivation": _bridge_protocol_record(
                candidate.bridge_grid_derivation
            ),
        }
    )


def _operation_registry(
    runtime: C19RuntimeConstructionV2,
) -> tuple[OperationRegistryRow, ...]:
    rows: list[OperationRegistryRow] = []
    for branch, factory in (
        ("actual", runtime.actual_factory),
        ("matched_ablated", runtime.matched_factory),
    ):
        rows.extend(
            (branch, index, slot_id, primitive)
            for index, (slot_id, primitive) in enumerate(
                zip(factory.layer_slot_ids, factory.primitives)
            )
        )
    return tuple(rows)


def _operation_registry_root(
    registry: tuple[OperationRegistryRow, ...],
    runtime: C19RuntimeConstructionV2,
) -> str:
    return canonical_sha(
        {
            "operation_registry": _operation_registry_payload(registry),
            "ablation_manifest": {
                **ablation_manifest_payload(runtime.ablation_manifest),
                "manifest_sha": runtime.ablation_manifest.manifest_sha,
            },
        }
    )


def _build_dependency_closure() -> tuple[tuple[str, str], ...]:
    repository = Path(__file__).resolve().parents[1]
    if tuple(sorted(_CONSTRUCTION_DEPENDENCY_PATHS)) != (
        _CONSTRUCTION_DEPENDENCY_PATHS
    ):
        raise RuntimeError("construction dependency paths are not canonical")
    result: list[tuple[str, str]] = []
    for relative_path in _CONSTRUCTION_DEPENDENCY_PATHS:
        path = PurePosixPath(relative_path)
        if path.is_absolute() or path.as_posix() != relative_path or ".." in path.parts:
            raise ValueError("construction dependency path is not repository-relative")
        result.append(
            (
                relative_path,
                hashlib.sha256((repository / relative_path).read_bytes()).hexdigest(),
            )
        )
    return tuple(result)


def _build_c19_current_application_authority_v3() -> CurrentApplicationAuthorityV3:
    candidate = verify_c19_refreeze_v2_candidate(build_c19_refreeze_v2_candidate())
    runtime = candidate.runtime_construction
    basis = candidate.basis_contract
    metric_support = _build_metric_support_protocol(
        candidate.geometry_bundle.state_metric
    )
    response_provisional = CurrentScenarioResponseContractV3(
        response_contract_schema_version=(
            CURRENT_SCENARIO_RESPONSE_CONTRACT_V3_SCHEMA_VERSION
        ),
        contract_state=PROVISIONAL_AUTHORITY_STATE,
        control_case_id=candidate.control_case_id,
        application_instance_id=candidate.application_instance_id,
        scenario_id=candidate.scenario_id,
        basis_contract=basis,
        dynamics_grid_derivation=candidate.dynamics_grid_derivation,
        metric_support_derivation=metric_support,
        response_grid=candidate.response_grid,
        response_reference_reciprocal_index=(
            candidate.response_reference_reciprocal_index
        ),
        bridge_grid_derivation=candidate.bridge_grid_derivation,
        geometry_bundle=candidate.geometry_bundle,
        runtime_construction_sha=runtime.construction_sha,
        actual_factory_sha=runtime.actual_factory.factory_sha,
        matched_factory_sha=runtime.matched_factory.factory_sha,
        operation_dag_sha=runtime.construction_trace.trace_sha,
        expected_actual_shell_rank=basis.expected_actual_shell_rank,
        expected_matched_shell_rank=basis.expected_matched_shell_rank,
        runtime_artifact_state=RUNTIME_ARTIFACT_STATE,
        measurement_state=MEASUREMENT_STATE,
        uses_global_fft_projection=False,
        uses_per_k_time_step_projector=False,
        response_contract_sha="0" * 64,
    )
    response = replace(
        response_provisional,
        response_contract_sha=canonical_sha(
            current_scenario_response_contract_v3_payload(response_provisional)
        ),
    )
    scenario_provisional = CurrentScenarioAuthorityV3(
        scenario_authority_schema_version=CURRENT_SCENARIO_AUTHORITY_V3_SCHEMA_VERSION,
        authority_state=PROVISIONAL_AUTHORITY_STATE,
        control_case_id=candidate.control_case_id,
        application_instance_id=candidate.application_instance_id,
        scenario_id=candidate.scenario_id,
        source_disposition="C19_REFREEZE_V2_REVIEWED",
        source_candidate_sha=candidate.candidate_sha,
        source_runtime_construction_sha=runtime.construction_sha,
        source_basis_contract_sha=basis.basis_contract_sha,
        response_contract=response,
        scenario_authority_sha="0" * 64,
    )
    scenario = replace(
        scenario_provisional,
        scenario_authority_sha=canonical_sha(
            current_scenario_authority_v3_payload(scenario_provisional)
        ),
    )
    registry = _operation_registry(runtime)
    closure = _build_dependency_closure()
    closure_sha = canonical_sha(
        {
            "closure_state": CONSTRUCTION_DEPENDENCY_CLOSURE_STATE,
            "construction_dependencies": [list(item) for item in closure],
        }
    )
    application_provisional = CurrentApplicationAuthorityV3(
        application_authority_schema_version=(
            CURRENT_APPLICATION_AUTHORITY_V3_SCHEMA_VERSION
        ),
        authority_state=PROVISIONAL_AUTHORITY_STATE,
        claim_ceiling=candidate.claim_ceiling,
        causal_contrast_role=candidate.causal_contrast_role,
        physical_anchor_eligibility=candidate.physical_anchor_eligibility,
        family_eligibility=candidate.family_eligibility,
        control_case_id=candidate.control_case_id,
        application_instance_id=candidate.application_instance_id,
        source_disposition="C19_REFREEZE_V2_REVIEWED",
        source_candidate_sha=candidate.candidate_sha,
        design_source_path=candidate.design_source_path,
        design_source_sha=candidate.design_source_sha,
        design_freeze_commit_sha=candidate.design_freeze_commit_sha,
        state_schema_id=candidate.state_schema_id,
        channel_order=candidate.channel_order,
        state_shape=runtime.state_shape,
        spatial_shape=C19_SPATIAL_SHAPE_V2,
        spatial_ndim=1,
        common_source_basis=basis.common_source_basis,
        common_readout_basis=basis.common_readout_basis,
        common_source_tensor=basis.common_source_tensor,
        common_readout_tensor=basis.common_readout_tensor,
        runtime_construction=runtime,
        runtime_construction_sha=runtime.construction_sha,
        basis_contract_sha=basis.basis_contract_sha,
        grid_protocol_root_sha=_grid_protocol_root(candidate, metric_support),
        operation_registry=registry,
        operation_registry_sha=_operation_registry_root(registry, runtime),
        construction_dependency_closure_state=(CONSTRUCTION_DEPENDENCY_CLOSURE_STATE),
        construction_dependency_closure=closure,
        construction_dependency_closure_sha=closure_sha,
        actual_active_step_count=runtime.actual_active_step_count,
        matched_active_step_count=runtime.matched_active_step_count,
        actual_layer_slot_count=runtime.actual_layer_slot_count,
        matched_layer_slot_count=runtime.matched_layer_slot_count,
        actual_primitive_count=runtime.actual_primitive_count,
        matched_primitive_count=runtime.matched_primitive_count,
        matched_neutral_identity_count=sum(
            primitive.operation_id == "neutral_identity"
            for primitive in runtime.matched_factory.primitives
        ),
        operation_dag_sha=runtime.construction_trace.trace_sha,
        target_spec_sha=runtime.frozen_target.target_spec_sha,
        actual_factory_sha=runtime.actual_factory.factory_sha,
        matched_factory_sha=runtime.matched_factory.factory_sha,
        ablation_manifest_sha=runtime.ablation_manifest.manifest_sha,
        actual_slot_program_sha=runtime.actual_slot_program_sha,
        matched_slot_program_sha=runtime.matched_slot_program_sha,
        actual_active_effect_digest=runtime.actual_active_effect_digest,
        matched_active_effect_digest=runtime.matched_active_effect_digest,
        scenario_authorities=(scenario,),
        application_authority_sha="0" * 64,
    )
    return replace(
        application_provisional,
        application_authority_sha=canonical_sha(
            current_application_authority_v3_payload(application_provisional)
        ),
    )


def build_c19_current_application_authority_v3() -> CurrentApplicationAuthorityV3:
    """Build the sole raw provisional C19 application body."""

    return _build_c19_current_application_authority_v3()


def verify_current_application_authority_v3(
    authority: CurrentApplicationAuthorityV3,
) -> CurrentApplicationAuthorityV3:
    """Verify exact types, self-hashes, lineage, and a fresh C19 replay."""

    _exact_record(
        authority,
        CurrentApplicationAuthorityV3,
        "current application authority v3",
    )
    if authority.authority_state != PROVISIONAL_AUTHORITY_STATE:
        raise ValueError("application authority state is not provisional")
    if authority.construction_dependency_closure_state != (
        CONSTRUCTION_DEPENDENCY_CLOSURE_STATE
    ):
        raise ValueError("construction dependency closure claimed authority")
    if authority.application_authority_sha != canonical_sha(
        current_application_authority_v3_payload(authority)
    ):
        raise ValueError("application authority SHA does not match its body")
    expected = _build_c19_current_application_authority_v3()
    _require_exact_recursive_match(
        authority,
        expected,
        "current application authority v3",
    )
    return authority


__all__ = [
    "CONSTRUCTION_DEPENDENCY_CLOSURE_STATE",
    "CURRENT_APPLICATION_AUTHORITY_V3_SCHEMA_VERSION",
    "CURRENT_SCENARIO_AUTHORITY_V3_SCHEMA_VERSION",
    "CURRENT_SCENARIO_RESPONSE_CONTRACT_V3_SCHEMA_VERSION",
    "CurrentApplicationAuthorityV3",
    "CurrentScenarioAuthorityV3",
    "CurrentScenarioResponseContractV3",
    "METRIC_SUPPORT_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION",
    "MetricSupportDerivationProtocolV1",
    "build_c19_current_application_authority_v3",
    "current_application_authority_v3_payload",
    "current_scenario_authority_v3_payload",
    "current_scenario_response_contract_v3_payload",
    "metric_support_derivation_protocol_v1_payload",
    "verify_metric_support_derivation_protocol_v1",
    "verify_current_application_authority_v3",
]
