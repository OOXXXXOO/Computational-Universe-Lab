"""Exact pre-response protocol contract for the current V3-M0 design.

This module intentionally separates an authority-neutral, self-hashing wire
format from the opaque live capability.  Raw or re-signed records can be
audited with :func:`verify_application_scenario_response_protocol_v2_body`,
but they cannot be promoted.  Issuance is closed over the exact live
Parent-v2, permit-v2 and materialization-v2 replayers.  The exact compiler is
dependency-injected and audits the complete upstream lineage before returning
any body.  Public issuance still fails closed while the cross-module live
identity bridge and repository-closed complete input resolver are unavailable.

No measured response, singular value, verdict, threshold override or caller
supplied numerical construction enters the issuer API.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields
import math
import re
import struct
from typing import Literal, Optional
from weakref import WeakKeyDictionary

import numpy as np

from .application_authority_v2 import (
    CalibrationApplicationPermitV2,
    VerifiedCalibrationApplicationPermitV2,
    _require_calibration_application_permit_v2_for_parent,
    require_calibration_application_permit_v2,
)
from .application_materialization_v2 import (
    ApplicationScenarioMaterializationV2,
    VerifiedV3M0ApplicationScenarioMaterializationV2,
    _require_application_scenario_materialization_v2_for_upstream,
    verify_v3m0_application_scenario_materialization_v2,
)
from .evidence import canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    basis_manifest_array,
    basis_manifest_payload,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_basis_manifest,
    verify_frozen_tensor,
)
from .grids import (
    build_application_bridge_grid_manifest,
    build_response_grid_manifest,
)
from .frozen_call_graph import freeze_rulespace_call_graph
from .parent_authority import VerifiedParentFreezeV2, require_current_parent
from .parent_v2_contracts import ParentFreezeV2Manifest
from .thresholds import BRIDGE_TOLERANCE


SCENARIO_RESPONSE_MOMENTUM_WIRE_V2_SCHEMA_VERSION = (
    "v3m0.scenario-response-momentum-wire.v2"
)
SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V2_SCHEMA_VERSION = (
    "v3m0.scenario-response-geometry-bundle.v2"
)
APPLICATION_SCENARIO_RESPONSE_PROTOCOL_V2_SCHEMA_VERSION = (
    "v3m0.application-scenario-response-protocol.v2"
)
APPLICATION_SCENARIO_RESPONSE_PROTOCOL_V2_STATE = (
    "FORMAL_PARENT_V2_BOUND_PRE_RESPONSE"
)
SELECTOR_RESIDUAL_TOLERANCE = 1.0e-12

_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTITY_INCIDENCE_FAMILY = "identity-incidence-v1"
_IDENTITY_NORMALIZER_FORMULA = "identity-positive-normalizer-v1"
_IDENTITY_DERIVATION = "identity-incidence-derivation-v1"
_LAPLACIAN_INCIDENCE_FAMILY = "synthetic-lattice-laplacian-incidence-v1"
_LAPLACIAN_NORMALIZER_FORMULA = "nu-inc-4-sum-sin2-half-v1"
_LAPLACIAN_DERIVATION = (
    "2-exp(+ik)-exp(-ik)-centered-second-difference-v1"
)
_C12_CONTROL_CASE_ID = "C12_NU_INC_IR_NORMALIZATION"

# These exact names are the only upstream assembly points.  Keeping them here
# is deliberate: a v1 permit/materialization, a provisional candidate or a
# duck-typed replacement must never become an accidental fallback authority.
UPSTREAM_V2_WIRING_POINTS = (
    "rulespace_v3.application_authority_v2.VerifiedCalibrationApplicationPermitV2",
    "rulespace_v3.application_authority_v2.require_calibration_application_permit_v2",
    "rulespace_v3.application_materialization_v2.VerifiedV3M0ApplicationScenarioMaterializationV2",
    "rulespace_v3.application_materialization_v2.verify_v3m0_application_scenario_materialization_v2",
)


class ScenarioResponseProtocolUpstreamUnavailable(RuntimeError):
    """The exact live v2 authority chain is not implemented yet."""


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _optional_text(value: object, field: str) -> Optional[str]:
    if value is None:
        return None
    return _text(value, field)


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA256.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an exact int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _finite_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an exact fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _positive_float(value: object, field: str) -> float:
    result = _finite_float(value, field)
    if result <= 0.0:
        raise ValueError(f"{field} must be positive")
    return result


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    observed = frozenset(vars(value))
    if observed != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _exact_basis(value: object, field: str) -> BasisManifest:
    _exact_record(value, BasisManifest, field)
    return verify_basis_manifest(value)


def _exact_tensor(value: object, field: str) -> FrozenComplexTensor:
    _exact_record(value, FrozenComplexTensor, field)
    return verify_frozen_tensor(value)


def _basis_record(value: BasisManifest) -> dict[str, object]:
    _exact_basis(value, "basis")
    return {**basis_manifest_payload(value), "manifest_id": value.manifest_id}


def _tensor_record(value: FrozenComplexTensor) -> dict[str, object]:
    _exact_tensor(value, "tensor")
    return {**frozen_tensor_payload(value), "tensor_sha": value.tensor_sha}


def _optional_tensor_record(
    value: Optional[FrozenComplexTensor],
) -> Optional[dict[str, object]]:
    if value is None:
        return None
    return _tensor_record(value)


def _fp64_equal(left: float, right: float) -> bool:
    return struct.pack(">d", left) == struct.pack(">d", right)


def _integer_tuple(
    value: object,
    field: str,
    *,
    allow_zero: bool = True,
) -> tuple[int, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty exact tuple")
    result = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise TypeError(f"{field}[{index}] must be an exact int")
        if not allow_zero and item <= 0:
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
    normalized = []
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
        normalized.append(tuple(point))
    result = tuple(normalized)
    if result != tuple(sorted(set(result))):
        raise ValueError(f"{field} must be unique lexicographic order")
    return result


def _float_tuple(
    value: object,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[float, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    if not value and not allow_empty:
        raise ValueError(f"{field} must be non-empty")
    return tuple(
        _finite_float(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    )


def _matrix(value: FrozenComplexTensor, field: str) -> np.ndarray:
    _exact_tensor(value, field)
    result = frozen_tensor_array(value)
    if result.ndim != 2:
        raise ValueError(f"{field} must be a matrix")
    return result


def _spectral_residual(value: np.ndarray) -> float:
    if not value.size:
        return 0.0
    return float(np.linalg.norm(value, ord=2))


def _require_hermitian_positive(value: np.ndarray, field: str) -> None:
    if value.ndim != 2 or value.shape[0] != value.shape[1]:
        raise ValueError(f"{field} must be square")
    if _spectral_residual(value - value.conj().T) > SELECTOR_RESIDUAL_TOLERANCE:
        raise ValueError(f"{field} must be Hermitian")
    eigenvalues = np.linalg.eigvalsh(value)
    if not np.all(eigenvalues > 0.0):
        raise ValueError(f"{field} must be positive definite")


@dataclass(frozen=True)
class ScenarioResponseMomentumWireV2:
    """All pre-response momentum-local analysis operators and contracts."""

    momentum_wire_schema_version: str
    scenario_id: str
    reciprocal_index: tuple[int, ...]
    momentum_wire: tuple[float, ...]
    phase_band: tuple[float, float]
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    curvature_incidence_family_id: Literal[
        "identity-incidence-v1",
        "synthetic-lattice-laplacian-incidence-v1",
    ]
    curvature_incidence_operator: FrozenComplexTensor
    curvature_normalizer_formula_id: str
    curvature_normalizer_derivation_id: str
    curvature_normalizer_value: float
    normalized_curvature_incidence_operator: FrozenComplexTensor
    curvature_ir_limit_formula_id: str
    curvature_ir_certificate_sha: str
    momentum_wire_sha: str

    def __post_init__(self) -> None:
        if (
            self.momentum_wire_schema_version
            != SCENARIO_RESPONSE_MOMENTUM_WIRE_V2_SCHEMA_VERSION
        ):
            raise ValueError("momentum wire schema drifted")
        _text(self.scenario_id, "scenario_id")
        _integer_tuple(self.reciprocal_index, "reciprocal_index")
        _float_tuple(self.momentum_wire, "momentum_wire")
        if len(self.reciprocal_index) != len(self.momentum_wire):
            raise ValueError("momentum wire dimension mismatch")
        if type(self.phase_band) is not tuple or len(self.phase_band) != 2:
            raise ValueError("phase_band must be an exact pair")
        lower = _finite_float(self.phase_band[0], "phase_band[0]")
        upper = _finite_float(self.phase_band[1], "phase_band[1]")
        if not lower < upper:
            raise ValueError("phase_band must be strictly ordered")
        _positive_int(
            self.expected_actual_shell_rank,
            "expected_actual_shell_rank",
        )
        _positive_int(
            self.expected_matched_shell_rank,
            "expected_matched_shell_rank",
        )
        if self.curvature_incidence_family_id not in (
            _IDENTITY_INCIDENCE_FAMILY,
            _LAPLACIAN_INCIDENCE_FAMILY,
        ):
            raise ValueError("curvature incidence family is not closed")
        _text(
            self.curvature_normalizer_formula_id,
            "curvature_normalizer_formula_id",
        )
        _text(
            self.curvature_normalizer_derivation_id,
            "curvature_normalizer_derivation_id",
        )
        _positive_float(
            self.curvature_normalizer_value,
            "curvature_normalizer_value",
        )
        _text(
            self.curvature_ir_limit_formula_id,
            "curvature_ir_limit_formula_id",
        )
        _sha(self.curvature_ir_certificate_sha, "curvature_ir_certificate_sha")
        _sha(self.momentum_wire_sha, "momentum_wire_sha")


def scenario_response_momentum_wire_v2_payload(
    wire: ScenarioResponseMomentumWireV2,
) -> dict[str, object]:
    _exact_record(wire, ScenarioResponseMomentumWireV2, "momentum wire")
    return {
        "momentum_wire_schema_version": wire.momentum_wire_schema_version,
        "scenario_id": wire.scenario_id,
        "reciprocal_index": list(wire.reciprocal_index),
        "momentum_wire": list(wire.momentum_wire),
        "phase_band": list(wire.phase_band),
        "expected_actual_shell_rank": wire.expected_actual_shell_rank,
        "expected_matched_shell_rank": wire.expected_matched_shell_rank,
        "curvature_incidence_family_id": wire.curvature_incidence_family_id,
        "curvature_incidence_operator": _tensor_record(
            wire.curvature_incidence_operator
        ),
        "curvature_normalizer_formula_id": (
            wire.curvature_normalizer_formula_id
        ),
        "curvature_normalizer_derivation_id": (
            wire.curvature_normalizer_derivation_id
        ),
        "curvature_normalizer_value": wire.curvature_normalizer_value,
        "normalized_curvature_incidence_operator": _tensor_record(
            wire.normalized_curvature_incidence_operator
        ),
        "curvature_ir_limit_formula_id": wire.curvature_ir_limit_formula_id,
        "curvature_ir_certificate_sha": wire.curvature_ir_certificate_sha,
    }


def _verify_momentum_wire(
    wire: ScenarioResponseMomentumWireV2,
) -> ScenarioResponseMomentumWireV2:
    _exact_record(wire, ScenarioResponseMomentumWireV2, "momentum wire")
    wire.__post_init__()
    if wire.momentum_wire_sha != canonical_sha(
        scenario_response_momentum_wire_v2_payload(wire)
    ):
        raise ValueError("momentum wire SHA does not match its body")
    if not any(value != 0.0 for value in wire.momentum_wire):
        raise ValueError("curvature momentum must be nonzero")
    if any(not -math.pi <= value <= math.pi for value in wire.momentum_wire):
        raise ValueError("curvature momentum is outside the first BZ")

    incidence = _matrix(
        wire.curvature_incidence_operator,
        "curvature_incidence_operator",
    )
    normalized = _matrix(
        wire.normalized_curvature_incidence_operator,
        "normalized_curvature_incidence_operator",
    )
    if incidence.shape != normalized.shape:
        raise ValueError("normalized incidence operator shape drifted")

    if wire.curvature_incidence_family_id == _IDENTITY_INCIDENCE_FAMILY:
        if (
            wire.curvature_normalizer_formula_id
            != _IDENTITY_NORMALIZER_FORMULA
            or wire.curvature_normalizer_derivation_id != _IDENTITY_DERIVATION
            or not _fp64_equal(wire.curvature_normalizer_value, 1.0)
        ):
            raise ValueError("identity curvature normalizer is inconsistent")
    else:
        if (
            wire.curvature_normalizer_formula_id
            != _LAPLACIAN_NORMALIZER_FORMULA
            or wire.curvature_normalizer_derivation_id != _LAPLACIAN_DERIVATION
        ):
            raise ValueError("Laplacian curvature normalizer derivation drifted")
        expected = float(
            4.0
            * sum(
                np.sin(np.float64(value) / np.float64(2.0)) ** 2
                for value in wire.momentum_wire
            )
        )
        if not _fp64_equal(wire.curvature_normalizer_value, expected):
            raise ValueError("curvature normalizer fp64 wire is not analytic nu")

    expected_normalized = incidence / np.float64(
        wire.curvature_normalizer_value
    )
    if not np.array_equal(normalized, expected_normalized):
        raise ValueError("normalized incidence is not exact incidence/normalizer")
    return wire


@dataclass(frozen=True)
class ScenarioResponseGeometryBundleV2:
    """Optional analytic geometry inputs frozen before either response branch."""

    geometry_bundle_schema_version: str
    geometry_kind: Literal[
        "C15_QUOTIENT_SPECTRUM",
        "C16_COVERAGE_CONTROL",
        "C17_QUOTIENT_GAUGE_GRAPH",
    ]
    scenario_id: str
    scenario_sha: str
    recipe_sha: str
    kernel_basis: FrozenComplexTensor
    physical_quotient_map: FrozenComplexTensor
    physical_quotient_metric: FrozenComplexTensor
    target_physical_representatives: FrozenComplexTensor
    coverage_control_id: Optional[str]
    coverage_control_wire: tuple[float, ...]
    undressed_response_representatives: Optional[FrozenComplexTensor]
    gauge_basis: Optional[FrozenComplexTensor]
    gauge_amplitude: Optional[float]
    expected_graph_rank: Optional[int]
    analytic_graph_singular_values: tuple[float, ...]
    fejer_graph_slope_formula_id: Optional[str]
    expected_actual_raw_graph_singular_values: tuple[float, ...]
    expected_ablated_raw_graph_singular_values: tuple[float, ...]
    geometry_bundle_sha: str

    def __post_init__(self) -> None:
        if (
            self.geometry_bundle_schema_version
            != SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V2_SCHEMA_VERSION
        ):
            raise ValueError("geometry bundle schema drifted")
        if self.geometry_kind not in (
            "C15_QUOTIENT_SPECTRUM",
            "C16_COVERAGE_CONTROL",
            "C17_QUOTIENT_GAUGE_GRAPH",
        ):
            raise ValueError("geometry kind is not closed")
        _text(self.scenario_id, "scenario_id")
        _sha(self.scenario_sha, "scenario_sha")
        _sha(self.recipe_sha, "recipe_sha")
        _optional_text(self.coverage_control_id, "coverage_control_id")
        _float_tuple(
            self.coverage_control_wire,
            "coverage_control_wire",
            allow_empty=True,
        )
        if self.gauge_amplitude is not None:
            _positive_float(self.gauge_amplitude, "gauge_amplitude")
        if self.expected_graph_rank is not None:
            _positive_int(self.expected_graph_rank, "expected_graph_rank")
        for field in (
            "analytic_graph_singular_values",
            "expected_actual_raw_graph_singular_values",
            "expected_ablated_raw_graph_singular_values",
        ):
            values = _float_tuple(
                getattr(self, field),
                field,
                allow_empty=True,
            )
            if any(item < 0.0 for item in values):
                raise ValueError(f"{field} must be non-negative")
        _optional_text(
            self.fejer_graph_slope_formula_id,
            "fejer_graph_slope_formula_id",
        )
        _sha(self.geometry_bundle_sha, "geometry_bundle_sha")


def scenario_response_geometry_bundle_v2_payload(
    bundle: ScenarioResponseGeometryBundleV2,
) -> dict[str, object]:
    _exact_record(bundle, ScenarioResponseGeometryBundleV2, "geometry bundle")
    return {
        "geometry_bundle_schema_version": bundle.geometry_bundle_schema_version,
        "geometry_kind": bundle.geometry_kind,
        "scenario_id": bundle.scenario_id,
        "scenario_sha": bundle.scenario_sha,
        "recipe_sha": bundle.recipe_sha,
        "kernel_basis": _tensor_record(bundle.kernel_basis),
        "physical_quotient_map": _tensor_record(
            bundle.physical_quotient_map
        ),
        "physical_quotient_metric": _tensor_record(
            bundle.physical_quotient_metric
        ),
        "target_physical_representatives": _tensor_record(
            bundle.target_physical_representatives
        ),
        "coverage_control_id": bundle.coverage_control_id,
        "coverage_control_wire": list(bundle.coverage_control_wire),
        "undressed_response_representatives": _optional_tensor_record(
            bundle.undressed_response_representatives
        ),
        "gauge_basis": _optional_tensor_record(bundle.gauge_basis),
        "gauge_amplitude": bundle.gauge_amplitude,
        "expected_graph_rank": bundle.expected_graph_rank,
        "analytic_graph_singular_values": list(
            bundle.analytic_graph_singular_values
        ),
        "fejer_graph_slope_formula_id": bundle.fejer_graph_slope_formula_id,
        "expected_actual_raw_graph_singular_values": list(
            bundle.expected_actual_raw_graph_singular_values
        ),
        "expected_ablated_raw_graph_singular_values": list(
            bundle.expected_ablated_raw_graph_singular_values
        ),
    }


def _verify_geometry_bundle(
    bundle: ScenarioResponseGeometryBundleV2,
) -> ScenarioResponseGeometryBundleV2:
    _exact_record(bundle, ScenarioResponseGeometryBundleV2, "geometry bundle")
    bundle.__post_init__()
    if bundle.geometry_bundle_sha != canonical_sha(
        scenario_response_geometry_bundle_v2_payload(bundle)
    ):
        raise ValueError("geometry bundle SHA does not match its body")

    kernel = _matrix(bundle.kernel_basis, "kernel_basis")
    quotient = _matrix(bundle.physical_quotient_map, "physical_quotient_map")
    metric = _matrix(bundle.physical_quotient_metric, "physical_quotient_metric")
    targets = _matrix(
        bundle.target_physical_representatives,
        "target_physical_representatives",
    )
    state_count = kernel.shape[0]
    if quotient.shape[1] != state_count or targets.shape[0] != state_count:
        raise ValueError("geometry state dimensions are inconsistent")
    if metric.shape != (quotient.shape[0], quotient.shape[0]):
        raise ValueError("physical quotient metric dimension drifted")
    _require_hermitian_positive(metric, "physical_quotient_metric")
    if _spectral_residual(quotient @ kernel) > SELECTOR_RESIDUAL_TOLERANCE:
        raise ValueError("kernel is not annihilated by physical quotient")

    if bundle.geometry_kind == "C15_QUOTIENT_SPECTRUM":
        if any(
            value is not None
            for value in (
                bundle.coverage_control_id,
                bundle.undressed_response_representatives,
                bundle.gauge_basis,
                bundle.gauge_amplitude,
                bundle.expected_graph_rank,
                bundle.fejer_graph_slope_formula_id,
            )
        ) or any(
            (
                bundle.coverage_control_wire,
                bundle.analytic_graph_singular_values,
                bundle.expected_actual_raw_graph_singular_values,
                bundle.expected_ablated_raw_graph_singular_values,
            )
        ):
            raise ValueError("C15 geometry contains C16/C17 fields")
    elif bundle.geometry_kind == "C16_COVERAGE_CONTROL":
        if bundle.coverage_control_id is None or not bundle.coverage_control_wire:
            raise ValueError("C16 geometry lacks its coverage control")
        if any(
            value is not None
            for value in (
                bundle.undressed_response_representatives,
                bundle.gauge_basis,
                bundle.gauge_amplitude,
                bundle.expected_graph_rank,
                bundle.fejer_graph_slope_formula_id,
            )
        ) or any(
            (
                bundle.analytic_graph_singular_values,
                bundle.expected_actual_raw_graph_singular_values,
                bundle.expected_ablated_raw_graph_singular_values,
            )
        ):
            raise ValueError("C16 geometry contains C17 fields")
    else:
        if bundle.coverage_control_id is not None or bundle.coverage_control_wire:
            raise ValueError("C17 geometry contains a C16 coverage control")
        required = (
            bundle.undressed_response_representatives,
            bundle.gauge_basis,
            bundle.gauge_amplitude,
            bundle.expected_graph_rank,
            bundle.fejer_graph_slope_formula_id,
        )
        if any(value is None for value in required):
            raise ValueError("C17 geometry graph bundle is incomplete")
        rank = bundle.expected_graph_rank
        assert rank is not None
        for field in (
            "analytic_graph_singular_values",
            "expected_actual_raw_graph_singular_values",
            "expected_ablated_raw_graph_singular_values",
        ):
            if len(getattr(bundle, field)) != rank:
                raise ValueError(f"C17 {field} length differs from graph rank")
        undressed = _matrix(
            bundle.undressed_response_representatives,
            "undressed_response_representatives",
        )
        gauge = _matrix(bundle.gauge_basis, "gauge_basis")
        if undressed.shape != gauge.shape or gauge.shape != (state_count, rank):
            raise ValueError("C17 graph representatives have wrong shape")
        identity = np.eye(rank, dtype=np.complex128)
        if (
            _spectral_residual(undressed.conj().T @ undressed - identity)
            > SELECTOR_RESIDUAL_TOLERANCE
            or _spectral_residual(gauge.conj().T @ gauge - identity)
            > SELECTOR_RESIDUAL_TOLERANCE
            or _spectral_residual(undressed.conj().T @ gauge)
            > SELECTOR_RESIDUAL_TOLERANCE
        ):
            raise ValueError("C17 undressed/gauge frames are not orthogonal")
    return bundle


@dataclass(frozen=True)
class ApplicationScenarioResponseProtocolV2:
    """Atomic, complete, pre-evolution protocol body for one scenario."""

    protocol_schema_version: str
    protocol_state: Literal["FORMAL_PARENT_V2_BOUND_PRE_RESPONSE"]
    formal_parent_v2_sha: str
    permit_v2_sha: str
    application_spec_sha: str
    application_instance_id: str
    control_case_id: str
    scenario_id: str
    scenario_sha: str
    operation_dag_sha: str
    compiled_contract_sha: str
    materialization_v2_sha: str
    recipe_sha: str
    construction_trace_sha: str
    actual_factory_sha: str
    matched_ablated_factory_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    selected_fejer_order: int
    common_source_basis: BasisManifest
    common_readout_basis: BasisManifest
    source_selector: FrozenComplexTensor
    readout_selector: FrozenComplexTensor
    source_injection_isometry: FrozenComplexTensor
    readout_coisometry: FrozenComplexTensor
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    response_torus_denominators: tuple[int, ...]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    response_grid_sha: str
    source_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_bridge_grid_sha: str
    readout_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    readout_bridge_grid_sha: str
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    source_trial_vectors: FrozenComplexTensor
    bridge_tolerance: float
    source_metric_whitener: FrozenComplexTensor
    h_metric_whitener: FrozenComplexTensor
    curvature_metric_whitener: FrozenComplexTensor
    momentum_wires: tuple[ScenarioResponseMomentumWireV2, ...]
    geometry_bundle: Optional[ScenarioResponseGeometryBundleV2]
    protocol_sha: str

    def __post_init__(self) -> None:
        if (
            self.protocol_schema_version
            != APPLICATION_SCENARIO_RESPONSE_PROTOCOL_V2_SCHEMA_VERSION
        ):
            raise ValueError("scenario response protocol schema drifted")
        if self.protocol_state != APPLICATION_SCENARIO_RESPONSE_PROTOCOL_V2_STATE:
            raise ValueError("scenario response protocol state is not formal v2")
        for field in (
            "formal_parent_v2_sha",
            "permit_v2_sha",
            "application_spec_sha",
            "scenario_sha",
            "operation_dag_sha",
            "compiled_contract_sha",
            "materialization_v2_sha",
            "recipe_sha",
            "construction_trace_sha",
            "actual_factory_sha",
            "matched_ablated_factory_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "response_grid_sha",
            "source_bridge_grid_sha",
            "readout_bridge_grid_sha",
            "protocol_sha",
        ):
            _sha(getattr(self, field), field)
        for field in (
            "application_instance_id",
            "control_case_id",
            "scenario_id",
            "state_schema_id",
        ):
            _text(getattr(self, field), field)
        _positive_int(self.selected_fejer_order, "selected_fejer_order")
        _positive_float(self.bridge_tolerance, "bridge_tolerance")


@dataclass(frozen=True)
class ExpectedScenarioProtocolInputs:
    """Complete upstream-derived inputs consumed by the exact compiler."""

    response_grid_sha: str
    source_bridge_grid_sha: str
    readout_bridge_grid_sha: str
    bridge_tolerance: float
    source_metric_whitener: FrozenComplexTensor
    h_metric_whitener: FrozenComplexTensor
    curvature_metric_whitener: FrozenComplexTensor
    momentum_wires: tuple[ScenarioResponseMomentumWireV2, ...]
    geometry_bundle: Optional[ScenarioResponseGeometryBundleV2]

    def __post_init__(self) -> None:
        _exact_record(
            self,
            ExpectedScenarioProtocolInputs,
            "expected scenario protocol inputs",
        )
        for field in (
            "response_grid_sha",
            "source_bridge_grid_sha",
            "readout_bridge_grid_sha",
        ):
            _sha(getattr(self, field), field)
        _positive_float(self.bridge_tolerance, "bridge_tolerance")
        for value, field in (
            (self.source_metric_whitener, "source_metric_whitener"),
            (self.h_metric_whitener, "h_metric_whitener"),
            (self.curvature_metric_whitener, "curvature_metric_whitener"),
        ):
            _matrix(value, field)
        if type(self.momentum_wires) is not tuple or not self.momentum_wires:
            raise ValueError("momentum_wires must be a non-empty exact tuple")
        for wire in self.momentum_wires:
            _verify_momentum_wire(wire)
        if self.geometry_bundle is not None:
            _verify_geometry_bundle(self.geometry_bundle)


def application_scenario_response_protocol_v2_payload(
    protocol: ApplicationScenarioResponseProtocolV2,
) -> dict[str, object]:
    _exact_record(
        protocol,
        ApplicationScenarioResponseProtocolV2,
        "scenario response protocol",
    )
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "protocol_state": protocol.protocol_state,
        "formal_parent_v2_sha": protocol.formal_parent_v2_sha,
        "permit_v2_sha": protocol.permit_v2_sha,
        "application_spec_sha": protocol.application_spec_sha,
        "application_instance_id": protocol.application_instance_id,
        "control_case_id": protocol.control_case_id,
        "scenario_id": protocol.scenario_id,
        "scenario_sha": protocol.scenario_sha,
        "operation_dag_sha": protocol.operation_dag_sha,
        "compiled_contract_sha": protocol.compiled_contract_sha,
        "materialization_v2_sha": protocol.materialization_v2_sha,
        "recipe_sha": protocol.recipe_sha,
        "construction_trace_sha": protocol.construction_trace_sha,
        "actual_factory_sha": protocol.actual_factory_sha,
        "matched_ablated_factory_sha": protocol.matched_ablated_factory_sha,
        "actual_effect_digest": protocol.actual_effect_digest,
        "matched_ablated_effect_digest": (
            protocol.matched_ablated_effect_digest
        ),
        "selected_fejer_order": protocol.selected_fejer_order,
        "common_source_basis": _basis_record(protocol.common_source_basis),
        "common_readout_basis": _basis_record(protocol.common_readout_basis),
        "source_selector": _tensor_record(protocol.source_selector),
        "readout_selector": _tensor_record(protocol.readout_selector),
        "source_injection_isometry": _tensor_record(
            protocol.source_injection_isometry
        ),
        "readout_coisometry": _tensor_record(protocol.readout_coisometry),
        "state_schema_id": protocol.state_schema_id,
        "channel_order": list(protocol.channel_order),
        "spatial_shape": list(protocol.spatial_shape),
        "response_torus_denominators": list(
            protocol.response_torus_denominators
        ),
        "response_reciprocal_indices": [
            list(item) for item in protocol.response_reciprocal_indices
        ],
        "response_grid_sha": protocol.response_grid_sha,
        "source_bridge_reciprocal_indices": [
            list(item) for item in protocol.source_bridge_reciprocal_indices
        ],
        "source_bridge_grid_sha": protocol.source_bridge_grid_sha,
        "readout_bridge_reciprocal_indices": [
            list(item) for item in protocol.readout_bridge_reciprocal_indices
        ],
        "readout_bridge_grid_sha": protocol.readout_bridge_grid_sha,
        "source_readout_bridge_steps": list(
            protocol.source_readout_bridge_steps
        ),
        "reference_reciprocal_index": list(
            protocol.reference_reciprocal_index
        ),
        "source_trial_vectors": _tensor_record(protocol.source_trial_vectors),
        "bridge_tolerance": protocol.bridge_tolerance,
        "source_metric_whitener": _tensor_record(
            protocol.source_metric_whitener
        ),
        "h_metric_whitener": _tensor_record(protocol.h_metric_whitener),
        "curvature_metric_whitener": _tensor_record(
            protocol.curvature_metric_whitener
        ),
        "momentum_wires": [
            {
                **scenario_response_momentum_wire_v2_payload(item),
                "momentum_wire_sha": item.momentum_wire_sha,
            }
            for item in protocol.momentum_wires
        ],
        "geometry_bundle": (
            None
            if protocol.geometry_bundle is None
            else {
                **scenario_response_geometry_bundle_v2_payload(
                    protocol.geometry_bundle
                ),
                "geometry_bundle_sha": protocol.geometry_bundle.geometry_bundle_sha,
            }
        ),
    }


def _verify_basis_and_selectors(
    protocol: ApplicationScenarioResponseProtocolV2,
) -> None:
    source_basis = _exact_basis(
        protocol.common_source_basis,
        "common_source_basis",
    )
    readout_basis = _exact_basis(
        protocol.common_readout_basis,
        "common_readout_basis",
    )
    if source_basis.role != "source" or readout_basis.role != "readout":
        raise ValueError("common basis roles drifted")
    if (
        source_basis.state_schema_id != protocol.state_schema_id
        or readout_basis.state_schema_id != protocol.state_schema_id
        or source_basis.channel_order != protocol.channel_order
        or readout_basis.channel_order != protocol.channel_order
    ):
        raise ValueError("common bases are spliced across state schemas")

    b_source = basis_manifest_array(source_basis)
    w_readout = basis_manifest_array(readout_basis)
    c_source = _matrix(protocol.source_selector, "source_selector")
    c_readout = _matrix(protocol.readout_selector, "readout_selector")
    injection = _matrix(
        protocol.source_injection_isometry,
        "source_injection_isometry",
    )
    coisometry = _matrix(protocol.readout_coisometry, "readout_coisometry")
    state_count = len(protocol.channel_order)
    if b_source.shape[1] != state_count or w_readout.shape[1] != state_count:
        raise ValueError("common basis state dimension drifted")
    if c_source.shape[0] != b_source.shape[0]:
        raise ValueError("source selector common-basis dimension drifted")
    if c_readout.shape[1] != w_readout.shape[0]:
        raise ValueError("readout selector common-basis dimension drifted")

    source_identity = np.eye(c_source.shape[1], dtype=np.complex128)
    readout_identity = np.eye(c_readout.shape[0], dtype=np.complex128)
    if (
        _spectral_residual(c_source.conj().T @ c_source - source_identity)
        > SELECTOR_RESIDUAL_TOLERANCE
    ):
        raise ValueError("source selector isometry residual exceeds 1e-12")
    if (
        _spectral_residual(c_readout @ c_readout.conj().T - readout_identity)
        > SELECTOR_RESIDUAL_TOLERANCE
    ):
        raise ValueError("readout selector coisometry residual exceeds 1e-12")

    expected_injection = b_source.T @ c_source
    expected_coisometry = c_readout @ np.conjugate(w_readout)
    if not np.array_equal(injection, expected_injection):
        raise ValueError("source_injection_isometry is not B_source.T @ C_source")
    if not np.array_equal(coisometry, expected_coisometry):
        raise ValueError(
            "readout_coisometry is not C_readout @ conj(W_readout)"
        )

    trial_vectors = _matrix(protocol.source_trial_vectors, "source_trial_vectors")
    source_count = c_source.shape[1]
    if trial_vectors.shape != (source_count, source_count) or not np.array_equal(
        trial_vectors,
        np.eye(source_count, dtype=np.complex128),
    ):
        raise ValueError("source_trial_vectors are not the complete identity frame")

    source_whitener = _matrix(
        protocol.source_metric_whitener,
        "source_metric_whitener",
    )
    h_whitener = _matrix(protocol.h_metric_whitener, "h_metric_whitener")
    curvature_whitener = _matrix(
        protocol.curvature_metric_whitener,
        "curvature_metric_whitener",
    )
    if source_whitener.shape != (source_count, source_count):
        raise ValueError("source_metric_whitener dimension drifted")
    if h_whitener.shape != (c_readout.shape[0], c_readout.shape[0]):
        raise ValueError("h_metric_whitener dimension drifted")
    if type(protocol.momentum_wires) is not tuple:
        raise TypeError("momentum_wires must be an exact tuple")
    for wire in protocol.momentum_wires:
        incidence = _matrix(
            wire.curvature_incidence_operator,
            "curvature_incidence_operator",
        )
        if incidence.shape[1] != h_whitener.shape[0]:
            raise ValueError(
                "h_metric_whitener dimension does not match incidence input"
            )
        if incidence.shape[0] != curvature_whitener.shape[0]:
            raise ValueError(
                "curvature_metric_whitener dimension does not match "
                "incidence output"
            )
    for value, field in (
        (source_whitener, "source_metric_whitener"),
        (h_whitener, "h_metric_whitener"),
        (curvature_whitener, "curvature_metric_whitener"),
    ):
        _require_hermitian_positive(value, field)


def _verify_grids_and_momenta(
    protocol: ApplicationScenarioResponseProtocolV2,
) -> None:
    spatial_shape = _integer_tuple(
        protocol.spatial_shape,
        "spatial_shape",
        allow_zero=False,
    )
    denominators = _integer_tuple(
        protocol.response_torus_denominators,
        "response_torus_denominators",
        allow_zero=False,
    )
    if len(spatial_shape) != len(denominators):
        raise ValueError("response-grid spatial dimension drifted")
    response_indices = _index_grid(
        protocol.response_reciprocal_indices,
        "response_reciprocal_indices",
        denominators,
    )
    _index_grid(
        protocol.source_bridge_reciprocal_indices,
        "source_bridge_reciprocal_indices",
        spatial_shape,
    )
    _index_grid(
        protocol.readout_bridge_reciprocal_indices,
        "readout_bridge_reciprocal_indices",
        spatial_shape,
    )
    steps = _integer_tuple(
        protocol.source_readout_bridge_steps,
        "source_readout_bridge_steps",
        allow_zero=False,
    )
    if tuple(sorted(set(steps))) != steps:
        raise ValueError("source_readout_bridge_steps must be unique ordered")
    reference = _integer_tuple(
        protocol.reference_reciprocal_index,
        "reference_reciprocal_index",
    )
    if reference not in response_indices:
        raise ValueError("reference reciprocal index is outside response grid")
    if (
        type(protocol.momentum_wires) is not tuple
        or len(protocol.momentum_wires) != len(response_indices)
    ):
        raise ValueError("momentum wires do not cover response grid exactly")

    observed_indices = []
    for wire, reciprocal_index in zip(protocol.momentum_wires, response_indices):
        _verify_momentum_wire(wire)
        if wire.scenario_id != protocol.scenario_id:
            raise ValueError("momentum wire is spliced across scenarios")
        if wire.reciprocal_index != reciprocal_index:
            raise ValueError("momentum wire reciprocal index is spliced")
        expected_momentum = []
        for index, denominator in zip(reciprocal_index, denominators):
            signed_index = index if index <= denominator // 2 else index - denominator
            expected_momentum.append(2.0 * math.pi * signed_index / denominator)
        if any(
            not _fp64_equal(observed, expected)
            for observed, expected in zip(wire.momentum_wire, expected_momentum)
        ):
            raise ValueError("momentum fp64 wire does not match response grid")
        observed_indices.append(wire.reciprocal_index)
    if tuple(observed_indices) != response_indices:
        raise ValueError("momentum wires are not in response-grid order")

    if protocol.control_case_id == _C12_CONTROL_CASE_ID and any(
        item.curvature_incidence_family_id != _LAPLACIAN_INCIDENCE_FAMILY
        for item in protocol.momentum_wires
    ):
        raise ValueError("C12 protocol lacks momentum-local Laplacian incidence")


def verify_application_scenario_response_protocol_v2_body(
    protocol: ApplicationScenarioResponseProtocolV2,
) -> ApplicationScenarioResponseProtocolV2:
    """Replay an authority-neutral raw body without promoting it."""

    _exact_record(
        protocol,
        ApplicationScenarioResponseProtocolV2,
        "scenario response protocol",
    )
    protocol.__post_init__()
    if protocol.protocol_sha != canonical_sha(
        application_scenario_response_protocol_v2_payload(protocol)
    ):
        raise ValueError("scenario response protocol SHA does not match its body")
    if type(protocol.channel_order) is not tuple or not protocol.channel_order:
        raise ValueError("channel_order must be a non-empty exact tuple")
    if len(protocol.channel_order) != len(set(protocol.channel_order)):
        raise ValueError("channel_order contains duplicates")
    for index, channel in enumerate(protocol.channel_order):
        _text(channel, f"channel_order[{index}]")

    _verify_basis_and_selectors(protocol)
    _verify_grids_and_momenta(protocol)
    if protocol.geometry_bundle is not None:
        _verify_geometry_bundle(protocol.geometry_bundle)
        if (
            protocol.geometry_bundle.scenario_id != protocol.scenario_id
            or protocol.geometry_bundle.scenario_sha != protocol.scenario_sha
            or protocol.geometry_bundle.recipe_sha != protocol.recipe_sha
        ):
            raise ValueError("geometry bundle is spliced across scenario lineage")
    return protocol


@dataclass(frozen=True)
class _LiveProtocolBinding:
    formal_parent_v2: object
    permit_v2: object
    materialization_v2: object
    issued_protocol_sha: str


class VerifiedApplicationScenarioResponseProtocolV2:
    """Opaque capability; raw protocol records are never accepted in its place."""

    __slots__ = ("_authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("scenario response protocol capabilities are issuer-only")

    @property
    def protocol(self) -> ApplicationScenarioResponseProtocolV2:
        return verify_v3m0_scenario_response_protocol(self)


def _lineage_equal(observed: object, expected: object, field: str) -> None:
    if observed != expected:
        raise ValueError(f"scenario response protocol {field} lineage drifted")


def _unique_by_identifier(
    values: object,
    identifier: str,
    field: str,
) -> object:
    if type(values) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    matches = tuple(
        item for item in values if getattr(item, field, None) == identifier
    )
    if len(matches) != 1:
        raise ValueError(f"{field} does not resolve to exactly one live body")
    return matches[0]


def _restrict_metric_whitener(
    common_whitener: FrozenComplexTensor,
    scenario_embedding: np.ndarray,
    *,
    field: str,
    tensor_builder=freeze_complex_tensor,
) -> FrozenComplexTensor:
    """Return the canonical positive whitener of an induced metric.

    ``scenario_embedding`` maps scenario coordinates into the historical
    common coordinate space.  Restricting the metric, rather than slicing or
    substituting an identity, keeps non-trivial historical calibration data
    visible after a scenario selector is applied.
    """

    common = _matrix(common_whitener, f"historical {field}")
    if type(scenario_embedding) is not np.ndarray:
        raise TypeError(f"{field} embedding must be a NumPy ndarray")
    if (
        scenario_embedding.dtype != np.dtype(np.complex128)
        or scenario_embedding.ndim != 2
        or any(size <= 0 for size in scenario_embedding.shape)
    ):
        raise ValueError(f"{field} embedding must be a non-empty complex128 matrix")
    if common.shape[1] != scenario_embedding.shape[0]:
        raise ValueError(f"{field} embedding common dimension drifted")
    metric = (
        scenario_embedding.conj().T
        @ common.conj().T
        @ common
        @ scenario_embedding
    )
    _require_hermitian_positive(metric, f"restricted {field} metric")
    eigenvalues, eigenvectors = np.linalg.eigh(metric)
    root = np.asarray(
        (eigenvectors * np.sqrt(eigenvalues)) @ eigenvectors.conj().T,
        dtype=np.complex128,
    )
    _require_hermitian_positive(root, f"restricted {field} whitener")
    if (
        _spectral_residual(root.conj().T @ root - metric)
        > SELECTOR_RESIDUAL_TOLERANCE
    ):
        raise ValueError(f"restricted {field} whitener does not factor its metric")
    return tensor_builder(root)


def _build_expected_scenario_protocol_inputs(
    parent_body: object,
    permit_body: object,
    materialization_body: object,
    *,
    momentum_wires: tuple[ScenarioResponseMomentumWireV2, ...],
    geometry_bundle: Optional[ScenarioResponseGeometryBundleV2],
    unique_by_identifier=_unique_by_identifier,
    lineage_equal=_lineage_equal,
    response_grid_builder=build_response_grid_manifest,
    bridge_grid_builder=build_application_bridge_grid_manifest,
    metric_restrictor=_restrict_metric_whitener,
) -> ExpectedScenarioProtocolInputs:
    """Derive every structural protocol input from the reviewed lineage.

    Momentum and geometry remain supplied by the separate analytic resolver;
    this helper composes them with grids, threshold and metric restrictions
    that can be reconstructed mechanically from Parent-v1 plus the live
    scenario recipe.  It is private dependency injection only and is not a
    repository issuance fallback.
    """

    application = permit_body.application_authority
    historical_application = unique_by_identifier(
        parent_body.historical_parent_v1.synthetic_control_application_specs,
        materialization_body.application_instance_id,
        "application_instance_id",
    )
    for observed, expected, field in (
        (
            historical_application.control_case_id,
            application.control_case_id,
            "historical control case",
        ),
        (
            historical_application.application_spec_sha,
            application.based_on_application_spec_sha,
            "historical application spec SHA",
        ),
        (
            historical_application.application_instance_id,
            materialization_body.application_instance_id,
            "historical application instance",
        ),
    ):
        lineage_equal(observed, expected, field)

    scenario = unique_by_identifier(
        application.scenario_authorities,
        materialization_body.scenario_id,
        "scenario_id",
    )
    response = scenario.response_contract
    response_grid = response_grid_builder(historical_application)
    bridge_grid = bridge_grid_builder(historical_application)
    grid_protocol = historical_application.grid_protocol
    for observed, expected, field in (
        (
            response.response_torus_denominators,
            response_grid.torus_denominators,
            "response grid torus",
        ),
        (
            response.response_reciprocal_indices,
            response_grid.reciprocal_indices,
            "response grid indices",
        ),
        (
            response.source_readout_bridge_reciprocal_indices,
            bridge_grid.reciprocal_indices,
            "source/readout bridge indices",
        ),
        (
            response.source_readout_bridge_steps,
            grid_protocol.bridge_steps,
            "source/readout bridge steps",
        ),
        (
            response.reference_reciprocal_index,
            grid_protocol.reference_reciprocal_index,
            "reference reciprocal index",
        ),
        (
            materialization_body.construction_trace.state_shape[1:],
            bridge_grid.spatial_shape,
            "bridge spatial shape",
        ),
    ):
        lineage_equal(observed, expected, field)

    basis_protocol = historical_application.basis_protocol
    for observed, expected, field in (
        (
            materialization_body.common_source_basis,
            basis_protocol.source_basis,
            "historical common source basis",
        ),
        (
            materialization_body.common_readout_basis,
            basis_protocol.readout_basis,
            "historical common readout basis",
        ),
    ):
        lineage_equal(observed, expected, field)

    recipe = materialization_body.scenario_recipe
    c_source = _matrix(recipe.source_selector, "source_selector")
    c_readout = _matrix(recipe.readout_selector, "readout_selector")
    b_source = basis_manifest_array(materialization_body.common_source_basis)
    w_readout = basis_manifest_array(materialization_body.common_readout_basis)
    expected_injection = b_source.T @ c_source
    expected_coisometry = c_readout @ np.conjugate(w_readout)
    if not np.array_equal(
        frozen_tensor_array(materialization_body.scenario_source_injection),
        expected_injection,
    ):
        raise ValueError("source injection is not historical B_source.T @ C_source")
    if not np.array_equal(
        frozen_tensor_array(materialization_body.scenario_readout_coisometry),
        expected_coisometry,
    ):
        raise ValueError(
            "readout coisometry is not historical C_readout @ conj(W_readout)"
        )

    readout_protocol = historical_application.readout_protocol
    source_whitener = metric_restrictor(
        readout_protocol.source_metric_whitener,
        c_source,
        field="source metric",
    )
    h_whitener = metric_restrictor(
        readout_protocol.h_metric_whitener,
        np.asarray(c_readout.conj().T, dtype=np.complex128),
        field="h metric",
    )
    common_incidence = _matrix(
        readout_protocol.curvature_incidence_operator,
        "historical curvature incidence operator",
    )
    normalized_incidence = common_incidence @ c_readout.conj().T
    curvature_embedding = np.eye(
        normalized_incidence.shape[0],
        dtype=np.complex128,
    )
    curvature_whitener = metric_restrictor(
        readout_protocol.curvature_metric_whitener,
        curvature_embedding,
        field="curvature metric",
    )
    if type(momentum_wires) is not tuple or not momentum_wires:
        raise ValueError("analytic momentum resolver returned no exact wires")
    for wire in momentum_wires:
        _verify_momentum_wire(wire)
        expected_incidence = (
            np.float64(wire.curvature_normalizer_value) * normalized_incidence
        )
        if not np.array_equal(
            frozen_tensor_array(wire.curvature_incidence_operator),
            expected_incidence,
        ):
            raise ValueError(
                "analytic momentum incidence is not the historical restriction"
            )
        if not np.array_equal(
            frozen_tensor_array(
                wire.normalized_curvature_incidence_operator
            ),
            normalized_incidence,
        ):
            raise ValueError(
                "normalized momentum incidence is not the historical restriction"
            )
        if (
            normalized_incidence.shape[1]
            != frozen_tensor_array(h_whitener).shape[0]
        ):
            raise ValueError("h metric does not match incidence input dimension")
        if (
            normalized_incidence.shape[0]
            != frozen_tensor_array(curvature_whitener).shape[0]
        ):
            raise ValueError(
                "curvature metric does not match incidence output dimension"
            )

    return ExpectedScenarioProtocolInputs(
        response_grid_sha=response_grid.response_grid_sha,
        source_bridge_grid_sha=bridge_grid.bridge_grid_sha,
        readout_bridge_grid_sha=bridge_grid.bridge_grid_sha,
        bridge_tolerance=BRIDGE_TOLERANCE,
        source_metric_whitener=source_whitener,
        h_metric_whitener=h_whitener,
        curvature_metric_whitener=curvature_whitener,
        momentum_wires=momentum_wires,
        geometry_bundle=geometry_bundle,
    )


def _verify_exact_protocol_upstream_lineage(
    protocol: ApplicationScenarioResponseProtocolV2,
    parent_body: object,
    permit_body: object,
    materialization_body: object,
    *,
    unique_by_identifier=_unique_by_identifier,
    lineage_equal=_lineage_equal,
) -> None:
    """Bind one verified protocol body to one complete live upstream tuple.

    The upstream reverifiers remain responsible for recursively validating
    their own exact wire types and hashes.  This function is the cross-object
    compiler boundary: every field duplicated between Parent, permit,
    materialization, recipe, trace, factory bindings and protocol must agree.
    """

    application = permit_body.application_authority
    parent_application = unique_by_identifier(
        parent_body.current_application_authorities,
        application.application_instance_id,
        "application_instance_id",
    )
    lineage_equal(
        parent_application,
        application,
        "Parent/application authority",
    )
    lineage_equal(
        permit_body.parent_freeze_v2_sha,
        parent_body.parent_freeze_v2_sha,
        "Parent/permit root",
    )
    lineage_equal(
        permit_body.scenario_authority_shas,
        tuple(item.scenario_authority_sha for item in application.scenario_authorities),
        "permit scenario-authority tuple",
    )

    scenario = unique_by_identifier(
        application.scenario_authorities,
        materialization_body.scenario_id,
        "scenario_id",
    )
    execution = scenario.scenario_execution_spec
    response = scenario.response_contract
    if execution.execution_lane != "BLOCK_SUCCESS":
        raise ValueError("scenario response protocol requires a BLOCK_SUCCESS lane")

    shared = (
        (
            protocol.formal_parent_v2_sha,
            parent_body.parent_freeze_v2_sha,
            "Parent root",
        ),
        (
            materialization_body.formal_parent_v2_sha,
            parent_body.parent_freeze_v2_sha,
            "materialization Parent root",
        ),
        (protocol.permit_v2_sha, permit_body.permit_sha, "permit SHA"),
        (
            materialization_body.permit_v2_sha,
            permit_body.permit_sha,
            "materialization permit SHA",
        ),
        (
            protocol.application_spec_sha,
            application.based_on_application_spec_sha,
            "application spec SHA",
        ),
        (
            materialization_body.application_spec_sha,
            application.based_on_application_spec_sha,
            "materialization application spec SHA",
        ),
        (
            materialization_body.application_authority_sha,
            application.application_authority_sha,
            "materialization application authority SHA",
        ),
        (
            protocol.application_instance_id,
            application.application_instance_id,
            "application instance",
        ),
        (
            materialization_body.application_instance_id,
            application.application_instance_id,
            "materialization application instance",
        ),
        (protocol.control_case_id, application.control_case_id, "control case"),
        (permit_body.control_case_id, application.control_case_id, "permit control case"),
        (
            materialization_body.control_case_id,
            application.control_case_id,
            "materialization control case",
        ),
        (protocol.scenario_id, scenario.scenario_id, "scenario ID"),
        (
            materialization_body.scenario_id,
            scenario.scenario_id,
            "materialization scenario ID",
        ),
        (protocol.scenario_sha, execution.scenario_sha, "scenario SHA"),
        (
            materialization_body.scenario_sha,
            execution.scenario_sha,
            "materialization scenario SHA",
        ),
        (
            materialization_body.scenario_authority_sha,
            scenario.scenario_authority_sha,
            "materialization scenario authority SHA",
        ),
        (
            materialization_body.response_contract_sha,
            response.response_contract_sha,
            "materialization response contract SHA",
        ),
        (
            protocol.selected_fejer_order,
            permit_body.selected_fejer_order,
            "selected Fejer order",
        ),
        (
            materialization_body.selected_fejer_order,
            permit_body.selected_fejer_order,
            "materialization selected Fejer order",
        ),
        (
            protocol.materialization_v2_sha,
            materialization_body.materialization_v2_sha,
            "materialization SHA",
        ),
    )
    for observed, expected, field in shared:
        lineage_equal(observed, expected, field)

    recipe = materialization_body.scenario_recipe
    recipe_lineage = (
        (recipe.formal_parent_v2_sha, protocol.formal_parent_v2_sha, "recipe Parent"),
        (recipe.permit_v2_sha, protocol.permit_v2_sha, "recipe permit"),
        (
            recipe.application_spec_sha,
            protocol.application_spec_sha,
            "recipe application spec",
        ),
        (
            recipe.scenario_authority_sha,
            scenario.scenario_authority_sha,
            "recipe scenario authority",
        ),
        (
            recipe.response_contract_sha,
            response.response_contract_sha,
            "recipe response contract",
        ),
        (recipe.control_case_id, protocol.control_case_id, "recipe control case"),
        (
            recipe.application_instance_id,
            protocol.application_instance_id,
            "recipe application instance",
        ),
        (recipe.scenario_id, protocol.scenario_id, "recipe scenario ID"),
        (recipe.scenario_sha, protocol.scenario_sha, "recipe scenario SHA"),
        (recipe.recipe_sha, protocol.recipe_sha, "recipe SHA"),
        (
            recipe.operation_dag_sha,
            protocol.operation_dag_sha,
            "recipe operation DAG",
        ),
        (
            recipe.compiled_contract_sha,
            protocol.compiled_contract_sha,
            "recipe compiled contract",
        ),
        (
            recipe.actual_effect.effect_digest,
            protocol.actual_effect_digest,
            "recipe actual effect",
        ),
        (
            recipe.matched_ablated_effect.effect_digest,
            protocol.matched_ablated_effect_digest,
            "recipe matched effect",
        ),
        (recipe.source_selector, protocol.source_selector, "recipe source selector"),
        (
            recipe.readout_selector,
            protocol.readout_selector,
            "recipe readout selector",
        ),
    )
    for observed, expected, field in recipe_lineage:
        lineage_equal(observed, expected, field)

    response_lineage = (
        (response.scenario_id, protocol.scenario_id, "response scenario"),
        (response.operation_dag_sha, protocol.operation_dag_sha, "response DAG"),
        (
            response.compiled_contract_sha,
            protocol.compiled_contract_sha,
            "response compiled contract",
        ),
        (
            response.selector_spec.source_selector,
            protocol.source_selector,
            "response source selector",
        ),
        (
            response.selector_spec.readout_selector,
            protocol.readout_selector,
            "response readout selector",
        ),
        (
            response.selector_spec.source_injection,
            protocol.source_injection_isometry,
            "response source injection",
        ),
        (
            response.selector_spec.readout_coisometry,
            protocol.readout_coisometry,
            "response readout coisometry",
        ),
        (
            response.source_trial_vectors,
            protocol.source_trial_vectors,
            "response source trials",
        ),
        (
            response.response_torus_denominators,
            protocol.response_torus_denominators,
            "response torus",
        ),
        (
            response.response_reciprocal_indices,
            protocol.response_reciprocal_indices,
            "response grid",
        ),
        (
            response.source_readout_bridge_reciprocal_indices,
            protocol.source_bridge_reciprocal_indices,
            "source bridge grid",
        ),
        (
            response.source_readout_bridge_reciprocal_indices,
            protocol.readout_bridge_reciprocal_indices,
            "readout bridge grid",
        ),
        (
            response.source_readout_bridge_steps,
            protocol.source_readout_bridge_steps,
            "bridge steps",
        ),
        (
            response.reference_reciprocal_index,
            protocol.reference_reciprocal_index,
            "reference reciprocal index",
        ),
    )
    for observed, expected, field in response_lineage:
        lineage_equal(observed, expected, field)

    bands = response.preregistered_phase_bands
    if len(bands) == 1:
        expected_bands = bands * len(protocol.momentum_wires)
    elif len(bands) == len(protocol.momentum_wires):
        expected_bands = bands
    else:
        raise ValueError("response phase bands do not cover momentum wires")
    for wire, phase_band in zip(protocol.momentum_wires, expected_bands):
        lineage_equal(wire.phase_band, phase_band, "momentum phase band")
        lineage_equal(
            wire.expected_actual_shell_rank,
            response.expected_actual_shell_rank,
            "actual shell rank",
        )
        lineage_equal(
            wire.expected_matched_shell_rank,
            response.expected_matched_shell_rank,
            "matched shell rank",
        )

    lineage_equal(
        materialization_body.common_source_basis,
        protocol.common_source_basis,
        "common source basis",
    )
    lineage_equal(
        materialization_body.common_readout_basis,
        protocol.common_readout_basis,
        "common readout basis",
    )
    lineage_equal(
        materialization_body.scenario_source_injection,
        protocol.source_injection_isometry,
        "materialization source injection",
    )
    lineage_equal(
        materialization_body.scenario_readout_coisometry,
        protocol.readout_coisometry,
        "materialization readout coisometry",
    )

    trace = materialization_body.construction_trace
    trace_lineage = (
        (trace.scenario_id, protocol.scenario_id, "trace scenario ID"),
        (trace.scenario_sha, protocol.scenario_sha, "trace scenario SHA"),
        (trace.recipe_sha, protocol.recipe_sha, "trace recipe SHA"),
        (trace.operation_dag_sha, protocol.operation_dag_sha, "trace DAG"),
        (
            trace.compiled_contract_sha,
            protocol.compiled_contract_sha,
            "trace compiled contract",
        ),
        (
            trace.construction_trace_sha,
            protocol.construction_trace_sha,
            "construction trace SHA",
        ),
        (trace.state_schema_id, protocol.state_schema_id, "trace state schema"),
        (trace.channel_order, protocol.channel_order, "trace channel order"),
        (trace.state_shape[1:], protocol.spatial_shape, "trace spatial shape"),
        (
            trace.actual_effect_digest,
            protocol.actual_effect_digest,
            "trace actual effect",
        ),
        (
            trace.matched_ablated_effect_digest,
            protocol.matched_ablated_effect_digest,
            "trace matched effect",
        ),
    )
    if trace.state_shape[0] != len(protocol.channel_order):
        raise ValueError("trace state shape channel axis drifted")
    for observed, expected, field in trace_lineage:
        lineage_equal(observed, expected, field)

    bindings = (
        (
            materialization_body.actual_factory_binding,
            "actual",
            protocol.actual_factory_sha,
            protocol.actual_effect_digest,
        ),
        (
            materialization_body.matched_ablated_factory_binding,
            "matched_ablated",
            protocol.matched_ablated_factory_sha,
            protocol.matched_ablated_effect_digest,
        ),
    )
    for binding, branch, factory_sha, effect_digest in bindings:
        for observed, expected, field in (
            (binding.branch, branch, f"{branch} factory branch"),
            (binding.scenario_id, protocol.scenario_id, f"{branch} scenario ID"),
            (binding.scenario_sha, protocol.scenario_sha, f"{branch} scenario SHA"),
            (binding.recipe_sha, protocol.recipe_sha, f"{branch} recipe SHA"),
            (
                binding.construction_trace_sha,
                protocol.construction_trace_sha,
                f"{branch} construction trace",
            ),
            (binding.factory_sha, factory_sha, f"{branch} factory SHA"),
            (binding.effect_digest, effect_digest, f"{branch} effect digest"),
        ):
            lineage_equal(observed, expected, field)


def _make_exact_scenario_response_protocol_compiler(
    *,
    parent_body_type: type,
    permit_body_type: type,
    materialization_body_type: type,
    protocol_body_builder,
    expected_inputs_resolver,
    protocol_body_verifier=verify_application_scenario_response_protocol_v2_body,
    upstream_lineage_verifier=_verify_exact_protocol_upstream_lineage,
    lineage_equal=_lineage_equal,
):
    """Create the private pure compiler used after all live reverifiers.

    ``protocol_body_builder`` is deliberately private dependency injection.
    Public issuance never exposes it, so tests can exercise a positive exact
    compilation without creating a caller-controlled production hydration
    path while the complete expected-input resolver is still under
    construction.
    """

    for value, field in (
        (parent_body_type, "parent_body_type"),
        (permit_body_type, "permit_body_type"),
        (materialization_body_type, "materialization_body_type"),
    ):
        if type(value) is not type:
            raise TypeError(f"{field} must be an exact class")
    if (
        not callable(protocol_body_builder)
        or not callable(expected_inputs_resolver)
        or not callable(protocol_body_verifier)
        or not callable(upstream_lineage_verifier)
        or not callable(lineage_equal)
    ):
        raise TypeError("protocol compiler dependencies must be callable")

    def compile_exact(parent_body, permit_body, materialization_body):
        if type(parent_body) is not parent_body_type:
            raise TypeError("Parent replay returned the wrong exact body type")
        if type(permit_body) is not permit_body_type:
            raise TypeError("permit replay returned the wrong exact body type")
        if type(materialization_body) is not materialization_body_type:
            raise TypeError("materialization replay returned the wrong exact body type")
        protocol = protocol_body_verifier(
            protocol_body_builder(parent_body, permit_body, materialization_body)
        )
        upstream_lineage_verifier(
            protocol,
            parent_body,
            permit_body,
            materialization_body,
        )
        expected_inputs = expected_inputs_resolver(
            parent_body,
            permit_body,
            materialization_body,
        )
        if type(expected_inputs) is not ExpectedScenarioProtocolInputs:
            raise TypeError(
                "expected input resolver must return exact "
                "ExpectedScenarioProtocolInputs"
            )
        expected_inputs.__post_init__()
        for field in (
            "response_grid_sha",
            "source_bridge_grid_sha",
            "readout_bridge_grid_sha",
            "source_metric_whitener",
            "h_metric_whitener",
            "curvature_metric_whitener",
            "momentum_wires",
            "geometry_bundle",
        ):
            lineage_equal(
                getattr(protocol, field),
                getattr(expected_inputs, field),
                field,
            )
        if not _fp64_equal(
            protocol.bridge_tolerance,
            expected_inputs.bridge_tolerance,
        ):
            raise ValueError(
                "scenario response protocol bridge_tolerance lineage drifted"
            )
        return protocol

    return compile_exact


def _make_live_scenario_response_protocol_replayer(
    *,
    parent_capability_type: type,
    permit_capability_type: type,
    materialization_capability_type: type,
    parent_reverifier,
    permit_reverifier,
    materialization_reverifier,
    upstream_relationship_verifier,
    exact_compiler,
):
    """Close exact live identities over the pure protocol compiler."""

    dependencies = (
        parent_reverifier,
        permit_reverifier,
        materialization_reverifier,
        upstream_relationship_verifier,
        exact_compiler,
    )
    if not all(callable(item) for item in dependencies):
        raise TypeError("live protocol replay dependencies must be callable")

    def replay(formal_parent_v2, permit_v2, materialization_v2):
        if type(formal_parent_v2) is not parent_capability_type:
            raise TypeError("formal_parent_v2 must be an exact live Parent-v2")
        if type(permit_v2) is not permit_capability_type:
            raise TypeError("permit_v2 must be an exact live permit-v2")
        if type(materialization_v2) is not materialization_capability_type:
            raise TypeError(
                "materialization_v2 must be an exact live materialization-v2"
            )
        parent_body = parent_reverifier(formal_parent_v2)
        permit_body = permit_reverifier(permit_v2)
        materialization_body = materialization_reverifier(materialization_v2)
        upstream_relationship_verifier(
            formal_parent_v2,
            permit_v2,
            materialization_v2,
        )
        return exact_compiler(parent_body, permit_body, materialization_body)

    return replay


def _load_exact_v2_upstream() -> tuple[object, ...]:
    return (
        VerifiedCalibrationApplicationPermitV2,
        require_calibration_application_permit_v2,
        VerifiedV3M0ApplicationScenarioMaterializationV2,
        verify_v3m0_application_scenario_materialization_v2,
    )


def _repository_closed_protocol_body_builder(
    parent_body: object,
    permit_body: object,
    materialization_body: object,
) -> ApplicationScenarioResponseProtocolV2:
    del parent_body, permit_body, materialization_body
    raise ScenarioResponseProtocolUpstreamUnavailable(
        "repository-closed momentum/geometry protocol input resolver is not connected"
    )


def _repository_closed_expected_protocol_inputs(
    parent_body: object,
    permit_body: object,
    materialization_body: object,
) -> ExpectedScenarioProtocolInputs:
    del parent_body, permit_body, materialization_body
    raise ScenarioResponseProtocolUpstreamUnavailable(
        "repository-closed complete expected protocol inputs are not connected"
    )


def _make_repository_closed_live_relationship_verifier(
    *,
    permit_parent_reverifier,
    materialization_upstream_reverifier,
):
    if not callable(permit_parent_reverifier) or not callable(
        materialization_upstream_reverifier
    ):
        raise TypeError("repository relationship reverifiers must be callable")

    def verify(
        formal_parent_v2: object,
        permit_v2: object,
        materialization_v2: object,
    ) -> None:
        permit_parent_reverifier(permit_v2, formal_parent_v2)
        materialization_upstream_reverifier(
            formal_parent_v2,
            permit_v2,
            materialization_v2,
        )

    verify.__name__ = "_repository_closed_live_relationship_verifier"
    return verify


_repository_closed_live_relationship_verifier = (
    _make_repository_closed_live_relationship_verifier(
        permit_parent_reverifier=(
            _require_calibration_application_permit_v2_for_parent
        ),
        materialization_upstream_reverifier=(
            _require_application_scenario_materialization_v2_for_upstream
        ),
    )
)


def _make_repository_closed_live_upstream_replayer(
    *,
    parent_capability_type: type,
    parent_body_type: type,
    parent_reverifier,
    permit_capability_type: type,
    permit_body_type: type,
    permit_reverifier,
    materialization_capability_type: type,
    materialization_body_type: type,
    materialization_reverifier,
    protocol_body_builder,
    expected_inputs_resolver,
    upstream_relationship_verifier,
    compiler_factory,
    live_replayer_factory,
):
    """Resolve and close every exact upstream dependency once at assembly."""

    compiler = compiler_factory(
        parent_body_type=parent_body_type,
        permit_body_type=permit_body_type,
        materialization_body_type=materialization_body_type,
        protocol_body_builder=protocol_body_builder,
        expected_inputs_resolver=expected_inputs_resolver,
    )
    return live_replayer_factory(
        parent_capability_type=parent_capability_type,
        permit_capability_type=permit_capability_type,
        materialization_capability_type=materialization_capability_type,
        parent_reverifier=parent_reverifier,
        permit_reverifier=permit_reverifier,
        materialization_reverifier=materialization_reverifier,
        upstream_relationship_verifier=upstream_relationship_verifier,
        exact_compiler=compiler,
    )


_replay_from_live_upstream = _make_repository_closed_live_upstream_replayer(
    parent_capability_type=VerifiedParentFreezeV2,
    parent_body_type=ParentFreezeV2Manifest,
    parent_reverifier=require_current_parent,
    permit_capability_type=VerifiedCalibrationApplicationPermitV2,
    permit_body_type=CalibrationApplicationPermitV2,
    permit_reverifier=require_calibration_application_permit_v2,
    materialization_capability_type=(
        VerifiedV3M0ApplicationScenarioMaterializationV2
    ),
    materialization_body_type=ApplicationScenarioMaterializationV2,
    materialization_reverifier=(
        verify_v3m0_application_scenario_materialization_v2
    ),
    protocol_body_builder=_repository_closed_protocol_body_builder,
    expected_inputs_resolver=_repository_closed_expected_protocol_inputs,
    upstream_relationship_verifier=(
        _repository_closed_live_relationship_verifier
    ),
    compiler_factory=_make_exact_scenario_response_protocol_compiler,
    live_replayer_factory=_make_live_scenario_response_protocol_replayer,
)

del _make_repository_closed_live_relationship_verifier


def _make_closed_protocol_api(
    replay_from_live_upstream=_replay_from_live_upstream,
):
    registry: WeakKeyDictionary[
        VerifiedApplicationScenarioResponseProtocolV2,
        _LiveProtocolBinding,
    ] = WeakKeyDictionary()
    authority_seal = object()

    def issue_v3m0_scenario_response_protocol(
        formal_parent_v2: object,
        permit_v2: object,
        materialization_v2: object,
    ) -> VerifiedApplicationScenarioResponseProtocolV2:
        protocol = replay_from_live_upstream(
            formal_parent_v2,
            permit_v2,
            materialization_v2,
        )
        capability = object.__new__(VerifiedApplicationScenarioResponseProtocolV2)
        object.__setattr__(capability, "_authority_seal", authority_seal)
        registry[capability] = _LiveProtocolBinding(
            formal_parent_v2=formal_parent_v2,
            permit_v2=permit_v2,
            materialization_v2=materialization_v2,
            issued_protocol_sha=protocol.protocol_sha,
        )
        return capability

    def verify_v3m0_scenario_response_protocol(
        value: object,
    ) -> ApplicationScenarioResponseProtocolV2:
        if type(value) is not VerifiedApplicationScenarioResponseProtocolV2:
            raise TypeError(
                "value must be an exact live scenario response protocol capability"
            )
        try:
            seal = value._authority_seal
            binding = registry[value]
        except (AttributeError, KeyError) as exc:
            raise ValueError("scenario response protocol capability is not live") from exc
        if seal is not authority_seal:
            raise ValueError("scenario response protocol authority seal is forged")
        replayed = replay_from_live_upstream(
            binding.formal_parent_v2,
            binding.permit_v2,
            binding.materialization_v2,
        )
        if replayed.protocol_sha != binding.issued_protocol_sha:
            raise ValueError("closed protocol replay changed after issuance")
        return replayed

    return issue_v3m0_scenario_response_protocol, verify_v3m0_scenario_response_protocol


_closed_replay_from_live_upstream = freeze_rulespace_call_graph(
    _replay_from_live_upstream
)
(
    _raw_issue_v3m0_scenario_response_protocol,
    _raw_verify_v3m0_scenario_response_protocol,
) = _make_closed_protocol_api(
    replay_from_live_upstream=_closed_replay_from_live_upstream.__call__,
)


def _make_protocol_property_binding(
    *,
    builtin_len=len,
    runtime_error=RuntimeError,
):
    consumer_holder = []

    def protocol_property(self):
        if builtin_len(consumer_holder) != 1:
            raise runtime_error("scenario protocol property is not bound exactly once")
        return consumer_holder[0](self)

    def bind(consumer):
        if consumer_holder:
            raise runtime_error("scenario protocol property is already bound")
        consumer_holder.append(consumer)

    return property(protocol_property), bind


(
    _protocol_property,
    _bind_protocol_property,
) = _make_protocol_property_binding()
VerifiedApplicationScenarioResponseProtocolV2.protocol = _protocol_property
del _protocol_property
del _make_protocol_property_binding

issue_v3m0_scenario_response_protocol = freeze_rulespace_call_graph(
    _raw_issue_v3m0_scenario_response_protocol
)
verify_v3m0_scenario_response_protocol = freeze_rulespace_call_graph(
    _raw_verify_v3m0_scenario_response_protocol
)
_bind_protocol_property(verify_v3m0_scenario_response_protocol)
del _bind_protocol_property
del _raw_issue_v3m0_scenario_response_protocol
del _raw_verify_v3m0_scenario_response_protocol
del _closed_replay_from_live_upstream


__all__ = [
    "APPLICATION_SCENARIO_RESPONSE_PROTOCOL_V2_SCHEMA_VERSION",
    "APPLICATION_SCENARIO_RESPONSE_PROTOCOL_V2_STATE",
    "SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V2_SCHEMA_VERSION",
    "SCENARIO_RESPONSE_MOMENTUM_WIRE_V2_SCHEMA_VERSION",
    "SELECTOR_RESIDUAL_TOLERANCE",
    "UPSTREAM_V2_WIRING_POINTS",
    "ApplicationScenarioResponseProtocolV2",
    "ScenarioResponseGeometryBundleV2",
    "ScenarioResponseMomentumWireV2",
    "ScenarioResponseProtocolUpstreamUnavailable",
    "VerifiedApplicationScenarioResponseProtocolV2",
    "application_scenario_response_protocol_v2_payload",
    "issue_v3m0_scenario_response_protocol",
    "scenario_response_geometry_bundle_v2_payload",
    "scenario_response_momentum_wire_v2_payload",
    "verify_application_scenario_response_protocol_v2_body",
    "verify_v3m0_scenario_response_protocol",
]
