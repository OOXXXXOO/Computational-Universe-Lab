"""Application-v2 endpoint, shell, and atomic paired-response authority."""

from __future__ import annotations

import copy
import math
import re
import struct
from dataclasses import dataclass, fields as dataclass_fields
from typing import Literal
from weakref import WeakKeyDictionary

import numpy as np

from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_frozen_tensor,
)


APPLICATION_RESPONSE_RUN_SPEC_V2_SCHEMA_VERSION = (
    "v3m0.application-response-run-spec.v2"
)
APPLICATION_RESPONSE_AUTHORITY_BINDING_V2_SCHEMA_VERSION = (
    "v3m0.application-response-authority-binding.v2"
)
APPLICATION_ENDPOINT_REFERENCE_V2_SCHEMA_VERSION = (
    "v3m0.application-endpoint-reference.v2"
)
APPLICATION_ENDPOINT_SHELL_V2_SCHEMA_VERSION = (
    "v3m0.application-endpoint-shell.v2"
)
APPLICATION_BRANCH_SOURCE_READOUT_RESPONSE_V2_SCHEMA_VERSION = (
    "v3m0.application-branch-source-readout-response.v2"
)
APPLICATION_PAIRED_RESPONSE_OUTCOME_V2_SCHEMA_VERSION = (
    "v3m0.application-paired-response-outcome.v2"
)
_AUTHORITY_STATE = "CURRENT_PARENT_V2_RESPONSE_CHAIN_BOUND"
_FEJER_ORDERS = frozenset((256, 512, 1024, 2048, 4096, 8192))
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ISOMETRY_TOLERANCE = 1.0e-12
_PROJECTOR_RANK_TOLERANCE = 1.0e-10

UPSTREAM_V2_WIRING_POINTS = (
    "live Parent-v2/permit-v2/materialization-v2/protocol-v2 replayers",
    "actual and matched-ablated live prestructure authorities",
    "actual and matched-ablated live transition authorities",
    "actual and matched-ablated live dynamics certificates",
    "live certificate-backed paired qualification",
    "actual-only endpoint/shell and source-readout numerical replay core",
)


class ApplicationResponseV2UpstreamUnavailable(RuntimeError):
    """The live Task-10 dynamics/qualification chain is not connected."""


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA256.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _finite_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an exact fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _nonnegative_float(value: object, field: str) -> float:
    result = _finite_float(value, field)
    if result < 0.0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    observed = frozenset(vars(value))
    if observed != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _exact_tensor(value: object, field: str) -> FrozenComplexTensor:
    _exact_record(value, FrozenComplexTensor, field)
    FrozenComplexTensor.__post_init__(value)
    return verify_frozen_tensor(value)


def _tensor_record(value: FrozenComplexTensor) -> dict[str, object]:
    tensor = _exact_tensor(value, "tensor")
    return {**frozen_tensor_payload(tensor), "tensor_sha": tensor.tensor_sha}


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty exact tuple")
    result = tuple(
        _text(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    )
    if len(result) != len(set(result)):
        raise ValueError(f"{field} must contain unique values")
    return result


def _positive_shape(value: object, field: str) -> tuple[int, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty exact tuple")
    result = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise TypeError(f"{field}[{index}] must be an exact int")
        if item <= 0:
            raise ValueError(f"{field}[{index}] must be positive")
        result.append(item)
    return tuple(result)


def _index_grid(
    value: object,
    field: str,
    denominators: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty exact tuple")
    result = []
    for row_index, row in enumerate(value):
        if type(row) is not tuple or len(row) != len(denominators):
            raise ValueError(f"{field}[{row_index}] dimension mismatch")
        point = []
        for axis, (item, denominator) in enumerate(zip(row, denominators)):
            if type(item) is not int:
                raise TypeError(
                    f"{field}[{row_index}][{axis}] must be an exact int"
                )
            if not 0 <= item < denominator:
                raise ValueError(f"{field}[{row_index}] lies outside its torus")
            point.append(item)
        result.append(tuple(point))
    answer = tuple(result)
    if answer != tuple(sorted(set(answer))):
        raise ValueError(f"{field} must be unique lexicographic order")
    return answer


def _matrix(value: FrozenComplexTensor, field: str) -> np.ndarray:
    _exact_tensor(value, field)
    matrix = frozen_tensor_array(value)
    if matrix.ndim != 2:
        raise ValueError(f"{field} must be a matrix")
    return matrix


@dataclass(frozen=True)
class ApplicationResponseRunSpecV2:
    """Exact pre-response source/readout run binding."""

    run_spec_schema_version: str
    formal_parent_v2_sha: str
    permit_v2_sha: str
    materialization_v2_sha: str
    scenario_response_protocol_v2_sha: str
    control_case_id: str
    scenario_id: str
    scenario_sha: str
    selected_fejer_order: int
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    source_injection_isometry: FrozenComplexTensor
    readout_coisometry: FrozenComplexTensor
    run_spec_sha: str

    def __post_init__(self) -> None:
        if (
            self.run_spec_schema_version
            != APPLICATION_RESPONSE_RUN_SPEC_V2_SCHEMA_VERSION
        ):
            raise ValueError("application response run-spec schema drifted")
        for field in (
            "formal_parent_v2_sha",
            "permit_v2_sha",
            "materialization_v2_sha",
            "scenario_response_protocol_v2_sha",
            "scenario_sha",
            "run_spec_sha",
        ):
            _sha(getattr(self, field), field)
        for field in ("control_case_id", "scenario_id", "state_schema_id"):
            _text(getattr(self, field), field)
        if (
            type(self.selected_fejer_order) is not int
            or self.selected_fejer_order not in _FEJER_ORDERS
        ):
            raise ValueError("selected_fejer_order is outside the frozen table")
        channels = _string_tuple(self.channel_order, "channel_order")
        shape = _positive_shape(self.spatial_shape, "spatial_shape")
        response_grid = _index_grid(
            self.response_reciprocal_indices,
            "response_reciprocal_indices",
            shape,
        )
        _index_grid(
            self.source_readout_bridge_reciprocal_indices,
            "source_readout_bridge_reciprocal_indices",
            shape,
        )
        if (
            type(self.source_readout_bridge_steps) is not tuple
            or not self.source_readout_bridge_steps
            or any(type(item) is not int or item <= 0 for item in self.source_readout_bridge_steps)
            or self.source_readout_bridge_steps
            != tuple(sorted(set(self.source_readout_bridge_steps)))
            or not any(item > 1 for item in self.source_readout_bridge_steps)
        ):
            raise ValueError("source_readout_bridge_steps are not frozen canonical steps")
        if (
            type(self.reference_reciprocal_index) is not tuple
            or self.reference_reciprocal_index not in response_grid
        ):
            raise ValueError("reference reciprocal index is outside response grid")
        source = _matrix(
            self.source_injection_isometry,
            "source_injection_isometry",
        )
        readout = _matrix(self.readout_coisometry, "readout_coisometry")
        if source.shape[0] != len(channels) or readout.shape[1] != len(channels):
            raise ValueError("J/P state axes differ from channel_order")
        source_identity = np.eye(source.shape[1], dtype=np.complex128)
        readout_identity = np.eye(readout.shape[0], dtype=np.complex128)
        if float(np.linalg.norm(source.conj().T @ source - source_identity, 2)) > _ISOMETRY_TOLERANCE:
            raise ValueError("source injection isometry residual exceeds 1e-12")
        if float(np.linalg.norm(readout @ readout.conj().T - readout_identity, 2)) > _ISOMETRY_TOLERANCE:
            raise ValueError("readout coisometry residual exceeds 1e-12")


def application_response_run_spec_v2_payload(
    value: ApplicationResponseRunSpecV2,
) -> dict[str, object]:
    _exact_record(value, ApplicationResponseRunSpecV2, "response run spec")
    return {
        "run_spec_schema_version": value.run_spec_schema_version,
        "formal_parent_v2_sha": value.formal_parent_v2_sha,
        "permit_v2_sha": value.permit_v2_sha,
        "materialization_v2_sha": value.materialization_v2_sha,
        "scenario_response_protocol_v2_sha": (
            value.scenario_response_protocol_v2_sha
        ),
        "control_case_id": value.control_case_id,
        "scenario_id": value.scenario_id,
        "scenario_sha": value.scenario_sha,
        "selected_fejer_order": value.selected_fejer_order,
        "state_schema_id": value.state_schema_id,
        "channel_order": list(value.channel_order),
        "spatial_shape": list(value.spatial_shape),
        "response_reciprocal_indices": [
            list(item) for item in value.response_reciprocal_indices
        ],
        "source_readout_bridge_reciprocal_indices": [
            list(item)
            for item in value.source_readout_bridge_reciprocal_indices
        ],
        "source_readout_bridge_steps": list(value.source_readout_bridge_steps),
        "reference_reciprocal_index": list(value.reference_reciprocal_index),
        "source_injection_isometry": _tensor_record(
            value.source_injection_isometry
        ),
        "readout_coisometry": _tensor_record(value.readout_coisometry),
    }


def verify_application_response_run_spec_v2_body(
    value: ApplicationResponseRunSpecV2,
) -> ApplicationResponseRunSpecV2:
    _exact_record(value, ApplicationResponseRunSpecV2, "response run spec")
    value.__post_init__()
    if value.run_spec_sha != canonical_sha(
        application_response_run_spec_v2_payload(value)
    ):
        raise ValueError("application response run-spec SHA does not match its body")
    return copy.deepcopy(value)


@dataclass(frozen=True)
class ApplicationResponseAuthorityBindingV2:
    """Exact authority ancestry shared by every application response layer."""

    authority_schema_version: str
    authority_state: Literal["CURRENT_PARENT_V2_RESPONSE_CHAIN_BOUND"]
    formal_parent_v2_sha: str
    permit_v2_sha: str
    materialization_v2_sha: str
    scenario_response_protocol_v2_sha: str
    run_spec_sha: str
    control_case_id: str
    scenario_id: str
    scenario_sha: str
    actual_factory_sha: str
    matched_ablated_factory_sha: str
    actual_prestructure_authority_sha: str
    matched_ablated_prestructure_authority_sha: str
    actual_transition_sha: str
    matched_ablated_transition_sha: str
    actual_dynamics_certificate_sha: str
    matched_ablated_dynamics_certificate_sha: str
    certificate_backed_qualification_sha: str
    authority_binding_sha: str

    def __post_init__(self) -> None:
        if (
            self.authority_schema_version
            != APPLICATION_RESPONSE_AUTHORITY_BINDING_V2_SCHEMA_VERSION
        ):
            raise ValueError("application response authority schema drifted")
        if self.authority_state != _AUTHORITY_STATE:
            raise ValueError("application response authority state drifted")
        for field in (
            "formal_parent_v2_sha",
            "permit_v2_sha",
            "materialization_v2_sha",
            "scenario_response_protocol_v2_sha",
            "run_spec_sha",
            "scenario_sha",
            "actual_factory_sha",
            "matched_ablated_factory_sha",
            "actual_prestructure_authority_sha",
            "matched_ablated_prestructure_authority_sha",
            "actual_transition_sha",
            "matched_ablated_transition_sha",
            "actual_dynamics_certificate_sha",
            "matched_ablated_dynamics_certificate_sha",
            "certificate_backed_qualification_sha",
            "authority_binding_sha",
        ):
            _sha(getattr(self, field), field)
        _text(self.control_case_id, "control_case_id")
        _text(self.scenario_id, "scenario_id")
        if self.actual_factory_sha == self.matched_ablated_factory_sha:
            raise ValueError("actual and matched factories must be distinct")
        if self.actual_transition_sha == self.matched_ablated_transition_sha:
            raise ValueError("actual and matched transitions must be distinct")


def application_response_authority_binding_v2_payload(
    value: ApplicationResponseAuthorityBindingV2,
) -> dict[str, object]:
    _exact_record(
        value,
        ApplicationResponseAuthorityBindingV2,
        "response authority binding",
    )
    return {
        field.name: getattr(value, field.name)
        for field in dataclass_fields(ApplicationResponseAuthorityBindingV2)
        if field.name != "authority_binding_sha"
    }


def verify_application_response_authority_binding_v2_body(
    value: ApplicationResponseAuthorityBindingV2,
    run_spec: ApplicationResponseRunSpecV2,
) -> ApplicationResponseAuthorityBindingV2:
    _exact_record(
        value,
        ApplicationResponseAuthorityBindingV2,
        "response authority binding",
    )
    value.__post_init__()
    verified_run = verify_application_response_run_spec_v2_body(run_spec)
    if value.authority_binding_sha != canonical_sha(
        application_response_authority_binding_v2_payload(value)
    ):
        raise ValueError("response authority binding SHA does not match its body")
    lineage = (
        (value.formal_parent_v2_sha, verified_run.formal_parent_v2_sha),
        (value.permit_v2_sha, verified_run.permit_v2_sha),
        (value.materialization_v2_sha, verified_run.materialization_v2_sha),
        (
            value.scenario_response_protocol_v2_sha,
            verified_run.scenario_response_protocol_v2_sha,
        ),
        (value.run_spec_sha, verified_run.run_spec_sha),
        (value.control_case_id, verified_run.control_case_id),
        (value.scenario_id, verified_run.scenario_id),
        (value.scenario_sha, verified_run.scenario_sha),
    )
    if any(left != right for left, right in lineage):
        raise ValueError("response authority lineage is spliced from its run spec")
    return copy.deepcopy(value)


def _run_spec_record(value: ApplicationResponseRunSpecV2) -> dict[str, object]:
    verified = verify_application_response_run_spec_v2_body(value)
    return {
        **application_response_run_spec_v2_payload(verified),
        "run_spec_sha": verified.run_spec_sha,
    }


def _authority_binding_record(
    value: ApplicationResponseAuthorityBindingV2,
) -> dict[str, object]:
    _exact_record(
        value,
        ApplicationResponseAuthorityBindingV2,
        "response authority binding",
    )
    return {
        **application_response_authority_binding_v2_payload(value),
        "authority_binding_sha": value.authority_binding_sha,
    }


@dataclass(frozen=True)
class ApplicationEndpointReferenceV2:
    """Actual-only endpoint reference body."""

    endpoint_reference_schema_version: str
    branch: Literal["actual"]
    authority_binding: ApplicationResponseAuthorityBindingV2
    run_spec: ApplicationResponseRunSpecV2
    actual_transition_sha: str
    actual_dynamics_certificate_sha: str
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_band: tuple[float, float]
    reference_phase: float
    expected_shell_rank: int
    rank: int
    participation: float
    runner_up_overlap: float | None
    hermitian_residual: float
    idempotent_residual: float
    metric_invariance_residual: float
    eigenphase_residual: float
    projector: FrozenComplexTensor
    endpoint_reference_sha: str

    def __post_init__(self) -> None:
        if (
            self.endpoint_reference_schema_version
            != APPLICATION_ENDPOINT_REFERENCE_V2_SCHEMA_VERSION
        ):
            raise ValueError("application endpoint-reference schema drifted")
        if self.branch != "actual":
            raise ValueError("application endpoint reference is actual-only")
        if type(self.authority_binding) is not ApplicationResponseAuthorityBindingV2:
            raise TypeError("authority_binding has the wrong strict type")
        if type(self.run_spec) is not ApplicationResponseRunSpecV2:
            raise TypeError("run_spec has the wrong strict type")
        _sha(self.actual_transition_sha, "actual_transition_sha")
        _sha(
            self.actual_dynamics_certificate_sha,
            "actual_dynamics_certificate_sha",
        )
        if (
            type(self.reference_reciprocal_index) is not tuple
            or not self.reference_reciprocal_index
            or any(type(item) is not int for item in self.reference_reciprocal_index)
        ):
            raise TypeError("reference_reciprocal_index must be an exact int tuple")
        if (
            type(self.preregistered_phase_band) is not tuple
            or len(self.preregistered_phase_band) != 2
        ):
            raise TypeError("preregistered_phase_band must be an exact pair")
        lower = _finite_float(
            self.preregistered_phase_band[0],
            "preregistered_phase_band[0]",
        )
        upper = _finite_float(
            self.preregistered_phase_band[1],
            "preregistered_phase_band[1]",
        )
        if not -math.pi <= lower < upper <= math.pi:
            raise ValueError("preregistered_phase_band is outside principal order")
        phase = _finite_float(self.reference_phase, "reference_phase")
        if not lower <= phase <= upper:
            raise ValueError("reference phase is outside preregistered band")
        if type(self.expected_shell_rank) is not int or self.expected_shell_rank <= 0:
            raise ValueError("expected_shell_rank must be a positive exact int")
        if type(self.rank) is not int or self.rank <= 0:
            raise ValueError("rank must be a positive exact int")
        if self.rank != self.expected_shell_rank:
            raise ValueError("endpoint reference rank differs from expected shell rank")
        participation = _finite_float(self.participation, "participation")
        if not 0.0 <= participation <= 1.0:
            raise ValueError("participation must lie in [0, 1]")
        if self.runner_up_overlap is not None:
            overlap = _finite_float(self.runner_up_overlap, "runner_up_overlap")
            if not 0.0 <= overlap <= 1.0:
                raise ValueError("runner_up_overlap must lie in [0, 1]")
        for field in (
            "hermitian_residual",
            "idempotent_residual",
            "metric_invariance_residual",
            "eigenphase_residual",
        ):
            _nonnegative_float(getattr(self, field), field)
        projector = _matrix(self.projector, "projector")
        if (
            projector.shape[0] != projector.shape[1]
            or projector.shape[0] != len(self.run_spec.channel_order)
            or self.rank > projector.shape[0]
        ):
            raise ValueError("endpoint projector shape/rank differs from run spec")
        _sha(self.endpoint_reference_sha, "endpoint_reference_sha")


def application_endpoint_reference_v2_payload(
    value: ApplicationEndpointReferenceV2,
) -> dict[str, object]:
    _exact_record(value, ApplicationEndpointReferenceV2, "endpoint reference")
    return {
        "endpoint_reference_schema_version": (
            value.endpoint_reference_schema_version
        ),
        "branch": value.branch,
        "authority_binding": _authority_binding_record(value.authority_binding),
        "run_spec": _run_spec_record(value.run_spec),
        "actual_transition_sha": value.actual_transition_sha,
        "actual_dynamics_certificate_sha": (
            value.actual_dynamics_certificate_sha
        ),
        "reference_reciprocal_index": list(value.reference_reciprocal_index),
        "preregistered_phase_band": list(value.preregistered_phase_band),
        "reference_phase": value.reference_phase,
        "expected_shell_rank": value.expected_shell_rank,
        "rank": value.rank,
        "participation": value.participation,
        "runner_up_overlap": value.runner_up_overlap,
        "hermitian_residual": value.hermitian_residual,
        "idempotent_residual": value.idempotent_residual,
        "metric_invariance_residual": value.metric_invariance_residual,
        "eigenphase_residual": value.eigenphase_residual,
        "projector": _tensor_record(value.projector),
    }


def verify_application_endpoint_reference_v2_body(
    value: ApplicationEndpointReferenceV2,
) -> ApplicationEndpointReferenceV2:
    _exact_record(value, ApplicationEndpointReferenceV2, "endpoint reference")
    value.__post_init__()
    authority = verify_application_response_authority_binding_v2_body(
        value.authority_binding,
        value.run_spec,
    )
    if (
        value.actual_transition_sha != authority.actual_transition_sha
        or value.actual_dynamics_certificate_sha
        != authority.actual_dynamics_certificate_sha
        or value.reference_reciprocal_index
        != value.run_spec.reference_reciprocal_index
    ):
        raise ValueError("endpoint reference is spliced across actual authority")
    if value.endpoint_reference_sha != canonical_sha(
        application_endpoint_reference_v2_payload(value)
    ):
        raise ValueError("endpoint-reference SHA does not match its body")
    projector = frozen_tensor_array(value.projector)
    if (
        float(np.linalg.norm(projector - projector.conj().T, 2))
        > _ISOMETRY_TOLERANCE
        or float(np.linalg.norm(projector @ projector - projector, 2))
        > _ISOMETRY_TOLERANCE
    ):
        raise ValueError("endpoint projector is not Hermitian idempotent")
    if (
        int(
            np.linalg.matrix_rank(
                projector,
                tol=_PROJECTOR_RANK_TOLERANCE,
            )
        )
        != value.rank
    ):
        raise ValueError("endpoint projector rank differs from declared rank")
    return copy.deepcopy(value)


def _endpoint_reference_record(
    value: ApplicationEndpointReferenceV2,
) -> dict[str, object]:
    verified = verify_application_endpoint_reference_v2_body(value)
    return {
        **application_endpoint_reference_v2_payload(verified),
        "endpoint_reference_sha": verified.endpoint_reference_sha,
    }


@dataclass(frozen=True)
class ApplicationEndpointShellV2:
    """Actual-only endpoint shell body."""

    endpoint_shell_schema_version: str
    branch: Literal["actual"]
    authority_binding: ApplicationResponseAuthorityBindingV2
    run_spec: ApplicationResponseRunSpecV2
    endpoint_reference: ApplicationEndpointReferenceV2
    actual_transition_sha: str
    actual_dynamics_certificate_sha: str
    shell_phases: tuple[float, ...]
    shell_projectors: FrozenComplexTensor
    point_participations: tuple[float, ...]
    hermitian_residual_max: float
    idempotent_residual_max: float
    metric_invariance_residual_max: float
    eigenphase_residual_max: float
    endpoint_shell_sha: str

    def __post_init__(self) -> None:
        if (
            self.endpoint_shell_schema_version
            != APPLICATION_ENDPOINT_SHELL_V2_SCHEMA_VERSION
        ):
            raise ValueError("application endpoint-shell schema drifted")
        if self.branch != "actual":
            raise ValueError("application endpoint shell is actual-only")
        if type(self.authority_binding) is not ApplicationResponseAuthorityBindingV2:
            raise TypeError("authority_binding has the wrong strict type")
        if type(self.run_spec) is not ApplicationResponseRunSpecV2:
            raise TypeError("run_spec has the wrong strict type")
        if type(self.endpoint_reference) is not ApplicationEndpointReferenceV2:
            raise TypeError("endpoint_reference has the wrong strict type")
        if (
            self.authority_binding.run_spec_sha != self.run_spec.run_spec_sha
            or self.endpoint_reference.run_spec != self.run_spec
            or self.endpoint_reference.authority_binding != self.authority_binding
        ):
            raise ValueError("endpoint shell contains a run spec splice")
        _sha(self.actual_transition_sha, "actual_transition_sha")
        _sha(
            self.actual_dynamics_certificate_sha,
            "actual_dynamics_certificate_sha",
        )
        if type(self.shell_phases) is not tuple or not self.shell_phases:
            raise ValueError("shell_phases must be a non-empty exact tuple")
        for index, phase in enumerate(self.shell_phases):
            value = _finite_float(phase, f"shell_phases[{index}]")
            if not -math.pi <= value <= math.pi:
                raise ValueError("shell phase is outside the principal interval")
        if (
            type(self.point_participations) is not tuple
            or len(self.point_participations) != len(self.shell_phases)
        ):
            raise ValueError("point_participations do not align with shell phases")
        for index, participation in enumerate(self.point_participations):
            value = _finite_float(
                participation,
                f"point_participations[{index}]",
            )
            if not 0.0 <= value <= 1.0:
                raise ValueError("shell participation must lie in [0, 1]")
        for field in (
            "hermitian_residual_max",
            "idempotent_residual_max",
            "metric_invariance_residual_max",
            "eigenphase_residual_max",
        ):
            _nonnegative_float(getattr(self, field), field)
        _sha(self.endpoint_shell_sha, "endpoint_shell_sha")


def application_endpoint_shell_v2_payload(
    value: ApplicationEndpointShellV2,
) -> dict[str, object]:
    _exact_record(value, ApplicationEndpointShellV2, "endpoint shell")
    return {
        "endpoint_shell_schema_version": value.endpoint_shell_schema_version,
        "branch": value.branch,
        "authority_binding": _authority_binding_record(value.authority_binding),
        "run_spec": _run_spec_record(value.run_spec),
        "endpoint_reference": _endpoint_reference_record(
            value.endpoint_reference
        ),
        "actual_transition_sha": value.actual_transition_sha,
        "actual_dynamics_certificate_sha": (
            value.actual_dynamics_certificate_sha
        ),
        "shell_phases": list(value.shell_phases),
        "shell_projectors": _tensor_record(value.shell_projectors),
        "point_participations": list(value.point_participations),
        "hermitian_residual_max": value.hermitian_residual_max,
        "idempotent_residual_max": value.idempotent_residual_max,
        "metric_invariance_residual_max": value.metric_invariance_residual_max,
        "eigenphase_residual_max": value.eigenphase_residual_max,
    }


def verify_application_endpoint_shell_v2_body(
    value: ApplicationEndpointShellV2,
) -> ApplicationEndpointShellV2:
    _exact_record(value, ApplicationEndpointShellV2, "endpoint shell")
    value.__post_init__()
    authority = verify_application_response_authority_binding_v2_body(
        value.authority_binding,
        value.run_spec,
    )
    reference = verify_application_endpoint_reference_v2_body(
        value.endpoint_reference
    )
    if (
        reference.authority_binding != authority
        or reference.run_spec != value.run_spec
        or value.actual_transition_sha != authority.actual_transition_sha
        or value.actual_dynamics_certificate_sha
        != authority.actual_dynamics_certificate_sha
    ):
        raise ValueError("endpoint shell is spliced across actual authority")
    if len(value.shell_phases) != len(value.run_spec.response_reciprocal_indices):
        raise ValueError("endpoint shell does not cover the response grid")
    projectors = frozen_tensor_array(
        _exact_tensor(value.shell_projectors, "shell_projectors")
    )
    state_count = len(value.run_spec.channel_order)
    if projectors.shape != (
        len(value.shell_phases),
        state_count,
        state_count,
    ):
        raise ValueError("shell projector tensor shape differs from run spec")
    reference_rows = tuple(
        index
        for index, reciprocal_index in enumerate(
            value.run_spec.response_reciprocal_indices
        )
        if reciprocal_index == reference.reference_reciprocal_index
    )
    if len(reference_rows) != 1:
        raise ValueError("endpoint shell reference row is not unique")
    reference_row = reference_rows[0]
    row_width = state_count * state_count
    row_start = reference_row * row_width
    shell_reference_wire = value.shell_projectors.values_wire[
        row_start : row_start + row_width
    ]
    reference_wire = reference.projector.values_wire
    if (
        struct.pack(">d", value.shell_phases[reference_row])
        != struct.pack(">d", reference.reference_phase)
        or struct.pack(">d", value.point_participations[reference_row])
        != struct.pack(">d", reference.participation)
        or len(shell_reference_wire) != len(reference_wire)
        or any(
            struct.pack(">dd", *shell_value)
            != struct.pack(">dd", *reference_value)
            for shell_value, reference_value in zip(
                shell_reference_wire,
                reference_wire,
            )
        )
    ):
        raise ValueError(
            "endpoint shell reference row contains a cross-splice"
        )
    for projector in projectors:
        if (
            float(np.linalg.norm(projector - projector.conj().T, 2))
            > _ISOMETRY_TOLERANCE
            or float(np.linalg.norm(projector @ projector - projector, 2))
            > _ISOMETRY_TOLERANCE
            or int(
                np.linalg.matrix_rank(
                    projector,
                    tol=_PROJECTOR_RANK_TOLERANCE,
                )
            )
            != reference.expected_shell_rank
        ):
            raise ValueError("shell projector fails Hermitian/rank contract")
    if value.endpoint_shell_sha != canonical_sha(
        application_endpoint_shell_v2_payload(value)
    ):
        raise ValueError("endpoint-shell SHA does not match its body")
    return copy.deepcopy(value)


def _endpoint_shell_record(
    value: ApplicationEndpointShellV2,
) -> dict[str, object]:
    verified = verify_application_endpoint_shell_v2_body(value)
    return {
        **application_endpoint_shell_v2_payload(verified),
        "endpoint_shell_sha": verified.endpoint_shell_sha,
    }


@dataclass(frozen=True)
class ApplicationBranchSourceReadoutResponseV2:
    """One branch body; only an atomic paired issuer may produce it."""

    branch_response_schema_version: str
    branch: Literal["actual", "matched_ablated"]
    authority_binding: ApplicationResponseAuthorityBindingV2
    run_spec: ApplicationResponseRunSpecV2
    actual_endpoint_shell: ApplicationEndpointShellV2
    factory_sha: str
    prestructure_authority_sha: str
    transition_sha: str
    dynamics_certificate_sha: str
    source_readout_bridge_sha: str
    response_values: FrozenComplexTensor
    branch_response_sha: str

    def __post_init__(self) -> None:
        if (
            self.branch_response_schema_version
            != APPLICATION_BRANCH_SOURCE_READOUT_RESPONSE_V2_SCHEMA_VERSION
        ):
            raise ValueError("application branch-response schema drifted")
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("application response branch is not closed")
        if type(self.authority_binding) is not ApplicationResponseAuthorityBindingV2:
            raise TypeError("authority_binding has the wrong strict type")
        if type(self.run_spec) is not ApplicationResponseRunSpecV2:
            raise TypeError("run_spec has the wrong strict type")
        if type(self.actual_endpoint_shell) is not ApplicationEndpointShellV2:
            raise TypeError("actual_endpoint_shell has the wrong strict type")
        for field in (
            "factory_sha",
            "prestructure_authority_sha",
            "transition_sha",
            "dynamics_certificate_sha",
            "source_readout_bridge_sha",
            "branch_response_sha",
        ):
            _sha(getattr(self, field), field)
        _exact_tensor(self.response_values, "response_values")


def application_branch_source_readout_response_v2_payload(
    value: ApplicationBranchSourceReadoutResponseV2,
) -> dict[str, object]:
    _exact_record(
        value,
        ApplicationBranchSourceReadoutResponseV2,
        "branch source-readout response",
    )
    return {
        "branch_response_schema_version": value.branch_response_schema_version,
        "branch": value.branch,
        "authority_binding": _authority_binding_record(value.authority_binding),
        "run_spec": _run_spec_record(value.run_spec),
        "actual_endpoint_shell": _endpoint_shell_record(
            value.actual_endpoint_shell
        ),
        "factory_sha": value.factory_sha,
        "prestructure_authority_sha": value.prestructure_authority_sha,
        "transition_sha": value.transition_sha,
        "dynamics_certificate_sha": value.dynamics_certificate_sha,
        "source_readout_bridge_sha": value.source_readout_bridge_sha,
        "response_values": _tensor_record(value.response_values),
    }


def verify_application_branch_source_readout_response_v2_body(
    value: ApplicationBranchSourceReadoutResponseV2,
) -> ApplicationBranchSourceReadoutResponseV2:
    _exact_record(
        value,
        ApplicationBranchSourceReadoutResponseV2,
        "branch source-readout response",
    )
    value.__post_init__()
    authority = verify_application_response_authority_binding_v2_body(
        value.authority_binding,
        value.run_spec,
    )
    shell = verify_application_endpoint_shell_v2_body(
        value.actual_endpoint_shell
    )
    if shell.branch != "actual":
        raise ValueError("matched branch cannot supply an endpoint shell")
    if (
        shell.authority_binding != authority
        or shell.run_spec != value.run_spec
    ):
        raise ValueError("branch response contains a protocol/shell/run splice")
    if value.branch == "actual":
        expected = (
            authority.actual_factory_sha,
            authority.actual_prestructure_authority_sha,
            authority.actual_transition_sha,
            authority.actual_dynamics_certificate_sha,
        )
    else:
        expected = (
            authority.matched_ablated_factory_sha,
            authority.matched_ablated_prestructure_authority_sha,
            authority.matched_ablated_transition_sha,
            authority.matched_ablated_dynamics_certificate_sha,
        )
    observed = (
        value.factory_sha,
        value.prestructure_authority_sha,
        value.transition_sha,
        value.dynamics_certificate_sha,
    )
    if observed != expected:
        raise ValueError("branch certificate/factory authority is spliced")
    response = frozen_tensor_array(value.response_values)
    source = frozen_tensor_array(value.run_spec.source_injection_isometry)
    readout = frozen_tensor_array(value.run_spec.readout_coisometry)
    expected_shape = (
        len(value.run_spec.response_reciprocal_indices),
        readout.shape[0],
        source.shape[1],
    )
    if response.shape != expected_shape:
        raise ValueError("branch response tensor shape differs from J/P/run spec")
    if value.branch_response_sha != canonical_sha(
        application_branch_source_readout_response_v2_payload(value)
    ):
        raise ValueError("branch-response SHA does not match its body")
    return copy.deepcopy(value)


@dataclass(frozen=True)
class ApplicationPairedResponseOutcomeV2:
    """Atomic actual/matched source-readout response body."""

    paired_response_schema_version: str
    authority_binding: ApplicationResponseAuthorityBindingV2
    run_spec: ApplicationResponseRunSpecV2
    actual_endpoint_shell: ApplicationEndpointShellV2
    actual_response: ApplicationBranchSourceReadoutResponseV2
    matched_ablated_response: ApplicationBranchSourceReadoutResponseV2
    atomic_pair_sha: str

    def __post_init__(self) -> None:
        if (
            self.paired_response_schema_version
            != APPLICATION_PAIRED_RESPONSE_OUTCOME_V2_SCHEMA_VERSION
        ):
            raise ValueError("application paired-response schema drifted")
        if type(self.authority_binding) is not ApplicationResponseAuthorityBindingV2:
            raise TypeError("authority_binding has the wrong strict type")
        if type(self.run_spec) is not ApplicationResponseRunSpecV2:
            raise TypeError("run_spec has the wrong strict type")
        if type(self.actual_endpoint_shell) is not ApplicationEndpointShellV2:
            raise TypeError("actual_endpoint_shell has the wrong strict type")
        for field in ("actual_response", "matched_ablated_response"):
            if type(getattr(self, field)) is not ApplicationBranchSourceReadoutResponseV2:
                raise TypeError(f"{field} has the wrong strict type")
        _sha(self.atomic_pair_sha, "atomic_pair_sha")


def _branch_response_record(
    value: ApplicationBranchSourceReadoutResponseV2,
) -> dict[str, object]:
    _exact_record(
        value,
        ApplicationBranchSourceReadoutResponseV2,
        "branch source-readout response",
    )
    return {
        **application_branch_source_readout_response_v2_payload(value),
        "branch_response_sha": value.branch_response_sha,
    }


def application_paired_response_outcome_v2_payload(
    value: ApplicationPairedResponseOutcomeV2,
) -> dict[str, object]:
    _exact_record(
        value,
        ApplicationPairedResponseOutcomeV2,
        "atomic paired response",
    )
    return {
        "paired_response_schema_version": value.paired_response_schema_version,
        "authority_binding": _authority_binding_record(value.authority_binding),
        "run_spec": _run_spec_record(value.run_spec),
        "actual_endpoint_shell": _endpoint_shell_record(
            value.actual_endpoint_shell
        ),
        "actual_response": _branch_response_record(value.actual_response),
        "matched_ablated_response": _branch_response_record(
            value.matched_ablated_response
        ),
    }


def verify_application_paired_response_outcome_v2_body(
    value: ApplicationPairedResponseOutcomeV2,
) -> ApplicationPairedResponseOutcomeV2:
    _exact_record(
        value,
        ApplicationPairedResponseOutcomeV2,
        "atomic paired response",
    )
    value.__post_init__()
    authority = verify_application_response_authority_binding_v2_body(
        value.authority_binding,
        value.run_spec,
    )
    shell = verify_application_endpoint_shell_v2_body(
        value.actual_endpoint_shell
    )
    actual = verify_application_branch_source_readout_response_v2_body(
        value.actual_response
    )
    matched = verify_application_branch_source_readout_response_v2_body(
        value.matched_ablated_response
    )
    if actual.branch != "actual" or matched.branch != "matched_ablated":
        raise ValueError("atomic paired response branches are swapped")
    if any(
        item.authority_binding != authority
        or item.run_spec != value.run_spec
        or item.actual_endpoint_shell != shell
        for item in (actual, matched)
    ):
        raise ValueError("atomic pair contains a protocol/shell/J/P splice")
    if (
        shell.authority_binding != authority
        or shell.run_spec != value.run_spec
    ):
        raise ValueError("atomic pair endpoint shell is spliced")
    if value.atomic_pair_sha != canonical_sha(
        application_paired_response_outcome_v2_payload(value)
    ):
        raise ValueError("atomic pair SHA does not match both branch bodies")
    return copy.deepcopy(value)


class VerifiedApplicationEndpointReferenceV2:
    """Opaque actual-only endpoint-reference capability."""

    __slots__ = ("_authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("application endpoint-reference v2 is issuer-only")


class VerifiedApplicationEndpointShellV2:
    """Opaque actual-only endpoint-shell capability."""

    __slots__ = ("_authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("application endpoint-shell v2 is issuer-only")


class VerifiedApplicationBranchSourceReadoutResponseV2:
    """Opaque branch response, issued only inside an atomic pair."""

    __slots__ = ("_authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("application branch response v2 is issuer-only")


class VerifiedApplicationPairedResponseOutcomeV2:
    """Opaque atomic actual/matched response capability."""

    __slots__ = ("_authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("application paired response v2 is issuer-only")


def _replay_application_endpoint_reference_v2(
    formal_parent_v2,
    permit_v2,
    materialization_v2,
    protocol_v2,
    actual_prestructure_v2,
    matched_ablated_prestructure_v2,
    actual_transition_v2,
    matched_ablated_transition_v2,
    actual_certificate_v2,
    matched_ablated_certificate_v2,
    qualification_v2,
):
    del (
        formal_parent_v2,
        permit_v2,
        materialization_v2,
        protocol_v2,
        actual_prestructure_v2,
        matched_ablated_prestructure_v2,
        actual_transition_v2,
        matched_ablated_transition_v2,
        actual_certificate_v2,
        matched_ablated_certificate_v2,
        qualification_v2,
    )
    raise ApplicationResponseV2UpstreamUnavailable(
        "application response v2 requires " + "; ".join(UPSTREAM_V2_WIRING_POINTS)
    )


def _make_closed_response_v2_api(
    *,
    reference_replayer=_replay_application_endpoint_reference_v2,
):
    reference_live: WeakKeyDictionary[
        VerifiedApplicationEndpointReferenceV2,
        ApplicationEndpointReferenceV2,
    ] = WeakKeyDictionary()
    shell_live: WeakKeyDictionary[
        VerifiedApplicationEndpointShellV2,
        ApplicationEndpointShellV2,
    ] = WeakKeyDictionary()
    branch_response_live: WeakKeyDictionary[
        VerifiedApplicationBranchSourceReadoutResponseV2,
        ApplicationBranchSourceReadoutResponseV2,
    ] = WeakKeyDictionary()
    pair_live: WeakKeyDictionary[
        VerifiedApplicationPairedResponseOutcomeV2,
        ApplicationPairedResponseOutcomeV2,
    ] = WeakKeyDictionary()
    authority_seal = object()

    def _require_live_body(
        value: object,
        wrapper_type: type,
        registry: WeakKeyDictionary,
        verifier,
        field: str,
    ):
        if type(value) is not wrapper_type:
            raise TypeError(
                f"{field} requires an exact live opaque capability"
            )
        try:
            seal = value._authority_seal
            raw = registry[value]
        except (AttributeError, KeyError) as exc:
            raise ValueError(
                f"{field} capability identity is not live"
            ) from exc
        if seal is not authority_seal:
            raise ValueError(f"{field} capability seal is forged")
        return verifier(raw)

    def require_application_endpoint_reference_v2(
        value: VerifiedApplicationEndpointReferenceV2,
    ) -> ApplicationEndpointReferenceV2:
        return _require_live_body(
            value,
            VerifiedApplicationEndpointReferenceV2,
            reference_live,
            verify_application_endpoint_reference_v2_body,
            "application endpoint reference v2",
        )

    def require_application_endpoint_shell_v2(
        value: VerifiedApplicationEndpointShellV2,
    ) -> ApplicationEndpointShellV2:
        return _require_live_body(
            value,
            VerifiedApplicationEndpointShellV2,
            shell_live,
            verify_application_endpoint_shell_v2_body,
            "application endpoint shell v2",
        )

    def require_application_branch_source_readout_response_v2(
        value: VerifiedApplicationBranchSourceReadoutResponseV2,
    ) -> ApplicationBranchSourceReadoutResponseV2:
        return _require_live_body(
            value,
            VerifiedApplicationBranchSourceReadoutResponseV2,
            branch_response_live,
            verify_application_branch_source_readout_response_v2_body,
            "application branch response v2",
        )

    def require_application_paired_response_outcome_v2(
        value: VerifiedApplicationPairedResponseOutcomeV2,
    ) -> ApplicationPairedResponseOutcomeV2:
        return _require_live_body(
            value,
            VerifiedApplicationPairedResponseOutcomeV2,
            pair_live,
            verify_application_paired_response_outcome_v2_body,
            "application paired response v2",
        )

    def _reference_property(
        value: VerifiedApplicationEndpointReferenceV2,
    ) -> ApplicationEndpointReferenceV2:
        return require_application_endpoint_reference_v2(value)

    def _shell_property(
        value: VerifiedApplicationEndpointShellV2,
    ) -> ApplicationEndpointShellV2:
        return require_application_endpoint_shell_v2(value)

    def _response_property(
        value: VerifiedApplicationBranchSourceReadoutResponseV2,
    ) -> ApplicationBranchSourceReadoutResponseV2:
        return require_application_branch_source_readout_response_v2(value)

    def _outcome_property(
        value: VerifiedApplicationPairedResponseOutcomeV2,
    ) -> ApplicationPairedResponseOutcomeV2:
        return require_application_paired_response_outcome_v2(value)

    VerifiedApplicationEndpointReferenceV2.reference = property(
        _reference_property
    )
    VerifiedApplicationEndpointShellV2.shell = property(_shell_property)
    VerifiedApplicationBranchSourceReadoutResponseV2.response = property(
        _response_property
    )
    VerifiedApplicationPairedResponseOutcomeV2.outcome = property(
        _outcome_property
    )

    def _issue_live_body(raw, wrapper_type, registry, verifier):
        verified = verifier(raw)
        capability = object.__new__(wrapper_type)
        object.__setattr__(capability, "_authority_seal", authority_seal)
        registry[capability] = verified
        return capability

    def issue_v3m0_application_endpoint_reference_v2(
        formal_parent_v2,
        permit_v2,
        materialization_v2,
        protocol_v2,
        actual_prestructure_v2,
        matched_ablated_prestructure_v2,
        actual_transition_v2,
        matched_ablated_transition_v2,
        actual_certificate_v2,
        matched_ablated_certificate_v2,
        qualification_v2,
    ):
        raw = reference_replayer(
            formal_parent_v2,
            permit_v2,
            materialization_v2,
            protocol_v2,
            actual_prestructure_v2,
            matched_ablated_prestructure_v2,
            actual_transition_v2,
            matched_ablated_transition_v2,
            actual_certificate_v2,
            matched_ablated_certificate_v2,
            qualification_v2,
        )
        return _issue_live_body(
            raw,
            VerifiedApplicationEndpointReferenceV2,
            reference_live,
            verify_application_endpoint_reference_v2_body,
        )

    def issue_v3m0_application_endpoint_shell_v2(reference):
        require_application_endpoint_reference_v2(reference)
        raise ApplicationResponseV2UpstreamUnavailable(
            "actual-only endpoint shell numerical replay is not connected"
        )

    def issue_v3m0_application_paired_response_v2(shell):
        require_application_endpoint_shell_v2(shell)
        raise ApplicationResponseV2UpstreamUnavailable(
            "atomic actual/matched response numerical replay is not connected"
        )

    return (
        require_application_endpoint_reference_v2,
        require_application_endpoint_shell_v2,
        require_application_branch_source_readout_response_v2,
        require_application_paired_response_outcome_v2,
        issue_v3m0_application_endpoint_reference_v2,
        issue_v3m0_application_endpoint_shell_v2,
        issue_v3m0_application_paired_response_v2,
    )


(
    require_application_endpoint_reference_v2,
    require_application_endpoint_shell_v2,
    require_application_branch_source_readout_response_v2,
    require_application_paired_response_outcome_v2,
    issue_v3m0_application_endpoint_reference_v2,
    issue_v3m0_application_endpoint_shell_v2,
    issue_v3m0_application_paired_response_v2,
) = _make_closed_response_v2_api()

del _make_closed_response_v2_api


__all__ = [
    "APPLICATION_BRANCH_SOURCE_READOUT_RESPONSE_V2_SCHEMA_VERSION",
    "APPLICATION_ENDPOINT_REFERENCE_V2_SCHEMA_VERSION",
    "APPLICATION_ENDPOINT_SHELL_V2_SCHEMA_VERSION",
    "APPLICATION_PAIRED_RESPONSE_OUTCOME_V2_SCHEMA_VERSION",
    "APPLICATION_RESPONSE_AUTHORITY_BINDING_V2_SCHEMA_VERSION",
    "APPLICATION_RESPONSE_RUN_SPEC_V2_SCHEMA_VERSION",
    "UPSTREAM_V2_WIRING_POINTS",
    "ApplicationBranchSourceReadoutResponseV2",
    "ApplicationEndpointReferenceV2",
    "ApplicationEndpointShellV2",
    "ApplicationPairedResponseOutcomeV2",
    "ApplicationResponseV2UpstreamUnavailable",
    "ApplicationResponseAuthorityBindingV2",
    "ApplicationResponseRunSpecV2",
    "VerifiedApplicationBranchSourceReadoutResponseV2",
    "VerifiedApplicationEndpointReferenceV2",
    "VerifiedApplicationEndpointShellV2",
    "VerifiedApplicationPairedResponseOutcomeV2",
    "application_branch_source_readout_response_v2_payload",
    "application_endpoint_reference_v2_payload",
    "application_endpoint_shell_v2_payload",
    "application_paired_response_outcome_v2_payload",
    "application_response_authority_binding_v2_payload",
    "application_response_run_spec_v2_payload",
    "issue_v3m0_application_endpoint_reference_v2",
    "issue_v3m0_application_endpoint_shell_v2",
    "issue_v3m0_application_paired_response_v2",
    "require_application_branch_source_readout_response_v2",
    "require_application_endpoint_reference_v2",
    "require_application_endpoint_shell_v2",
    "require_application_paired_response_outcome_v2",
    "verify_application_branch_source_readout_response_v2_body",
    "verify_application_endpoint_reference_v2_body",
    "verify_application_endpoint_shell_v2_body",
    "verify_application_paired_response_outcome_v2_body",
    "verify_application_response_authority_binding_v2_body",
    "verify_application_response_run_spec_v2_body",
]
