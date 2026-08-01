"""Authority-neutral analytic geometry schema for the V3-M0 response protocol.

This module is deliberately additive.  It does not alter or import the signed
scenario-response protocol v2, issue an authority capability, construct a
finite response, or evaluate a scientific verdict.  It freezes only the
analytic context and geometry inputs that must exist before either response
branch runs.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields
import math
import re
import struct
from typing import Literal, Optional

import numpy as np

from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_frozen_tensor,
)
from .thresholds import T_CANDIDATES


GEOMETRY_ANALYTIC_CONTEXT_V2_SCHEMA_VERSION = "v3m0.geometry-analytic-context.v2"
OBSERVER_COLLAPSE_PREREQUISITE_SPEC_V1_SCHEMA_VERSION = (
    "v3m0.observer-collapse-prerequisite-spec.v1"
)
SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V3_SCHEMA_VERSION = (
    "v3m0.scenario-response-geometry-bundle.v3"
)

C15_QUOTIENT_SPECTRUM = "C15_QUOTIENT_SPECTRUM"
C16_COVERAGE_CONTROL = "C16_COVERAGE_CONTROL"
C17_QUOTIENT_GAUGE_GRAPH = "C17_QUOTIENT_GAUGE_GRAPH"
C18_INDEPENDENT_UNARY = "C18_INDEPENDENT_UNARY"
C19_OBSERVER_COLLAPSE_CONDITIONS = "C19_OBSERVER_COLLAPSE_CONDITIONS"

GeometryKindV3 = Literal[
    "C15_QUOTIENT_SPECTRUM",
    "C16_COVERAGE_CONTROL",
    "C17_QUOTIENT_GAUGE_GRAPH",
    "C18_INDEPENDENT_UNARY",
    "C19_OBSERVER_COLLAPSE_CONDITIONS",
]

GEOMETRY_KINDS_V3 = (
    C15_QUOTIENT_SPECTRUM,
    C16_COVERAGE_CONTROL,
    C17_QUOTIENT_GAUGE_GRAPH,
    C18_INDEPENDENT_UNARY,
    C19_OBSERVER_COLLAPSE_CONDITIONS,
)

CANDIDATE_FEJER_ORDERS = T_CANDIDATES
C17_FEJER_GRAPH_SLOPE_FORMULA_ID = (
    "c17-fejer-shared-U-actual-a-ablated-a-over-Tplus1-v1"
)

GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND = {
    C15_QUOTIENT_SPECTRUM: "c15-analytic-shell-semantic-bundle-v1",
    C16_COVERAGE_CONTROL: "c16-analytic-coverage-target-bundle-v1",
    C17_QUOTIENT_GAUGE_GRAPH: "c17-analytic-quotient-gauge-bundle-v1",
    C18_INDEPENDENT_UNARY: "c18-independent-unary-direct-sum-bundle-v2",
    C19_OBSERVER_COLLAPSE_CONDITIONS: ("c19-full-positive-observer-collapse-bundle-v1"),
}

OBSERVER_COLLAPSE_CONDITIONAL_FORMULA_ID = (
    "observer-collapse-coisometry-conditional-squared-spectrum-v1"
)
OBSERVER_COLLAPSE_CONDITIONAL_CLAIM_CEILING = "CONDITIONAL_PREREQUISITES_ONLY"
OBSERVER_COLLAPSE_NOT_EVALUATED_STATE = "NOT_EVALUATED_PRE_RESPONSE"
OBSERVER_COLLAPSE_REQUIRED_PREDICATE_IDS = (
    "complete-nonzero-gram-support-selection",
    "whitened-coisometry-or-incidence-range-preservation",
    "incidence-rank-six",
    "gauge-contained-in-incidence-kernel-dimension-four",
    "tt2-gauge4-row4-pairwise-orthogonal-complete-decomposition",
    "constraint-kernel-tt-plus-gauge-compatible-projector-and-metric",
)

SELECTOR_RESIDUAL_TOLERANCE = 1.0e-12
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

_C15_SCENARIO_SECTORS = {
    "v3m0.synthetic-control.c15.v1.scenario.full-h.v1": (
        "TT0",
        "TT1",
        "Gauge",
        "Row",
    ),
    "v3m0.synthetic-control.c15.v1.scenario.low-rank-tt.v1": ("TT0",),
    "v3m0.synthetic-control.c15.v1.scenario.tt.v1": ("TT0", "TT1"),
    "v3m0.synthetic-control.c15.v1.scenario.tt-plus-row.v1": (
        "TT0",
        "TT1",
        "Row",
    ),
}
_C15_SCENARIO_ORDER = tuple(_C15_SCENARIO_SECTORS)
_C16_SCENARIO_COVERAGE = {
    "v3m0.synthetic-control.c16.v1.scenario.coverage-low.v1": (
        0.25,
        "00-coverage-low",
    ),
    "v3m0.synthetic-control.c16.v1.scenario.coverage-high.v1": (
        0.75,
        "01-coverage-high",
    ),
}
_C17_SCENARIO_ID = "v3m0.synthetic-control.c17.v1.scenario.quotient-gauge.v1"
_C18_SCENARIO_ID = "v3m0.synthetic-control.c18.v1.scenario.independent-unary.v1"
_C19_SCENARIO_ID = "v3m0.synthetic-control.c19.v1.scenario.observer-collapse.v1"
_CONTROL_CASE_ID_BY_KIND = {
    C15_QUOTIENT_SPECTRUM: "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
    C16_COVERAGE_CONTROL: "C16_COVERAGE_025_075",
    C17_QUOTIENT_GAUGE_GRAPH: "C17_QUOTIENT_GAUGE_COVERAGE",
    C18_INDEPENDENT_UNARY: "C18_ABLATED_INDEPENDENT_UNARY",
    C19_OBSERVER_COLLAPSE_CONDITIONS: ("C19_FULL_POSITIVE_OBSERVER_COLLAPSE"),
}
_ANALYTIC_SOURCE_RECIPE_COUNT_BY_KIND = {
    C15_QUOTIENT_SPECTRUM: 4,
    C16_COVERAGE_CONTROL: 5,
    C17_QUOTIENT_GAUGE_GRAPH: 1,
    C18_INDEPENDENT_UNARY: 1,
    C19_OBSERVER_COLLAPSE_CONDITIONS: 1,
}


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    observed = frozenset(vars(value))
    if observed != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


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


def _fp64_equal(left: float, right: float) -> bool:
    return struct.pack(">d", left) == struct.pack(">d", right)


def _fp64_tuple_equal(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> bool:
    return len(left) == len(right) and all(
        _fp64_equal(first, second) for first, second in zip(left, right)
    )


def _strings(
    value: object,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    if not value and not allow_empty:
        raise ValueError(f"{field} must be non-empty")
    result = tuple(_text(item, f"{field}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise ValueError(f"{field} contains duplicates")
    return result


def _shas(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty exact tuple")
    result = tuple(_sha(item, f"{field}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise ValueError(f"{field} contains duplicate recipe SHAs")
    return result


def _float_tuple(
    value: object,
    field: str,
    *,
    allow_empty: bool,
) -> tuple[float, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    if not value and not allow_empty:
        raise ValueError(f"{field} must be non-empty")
    return tuple(
        _finite_float(item, f"{field}[{index}]") for index, item in enumerate(value)
    )


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    _exact_record(tensor, FrozenComplexTensor, "tensor")
    verify_frozen_tensor(tensor)
    return {**frozen_tensor_payload(tensor), "tensor_sha": tensor.tensor_sha}


def _optional_tensor_record(
    tensor: Optional[FrozenComplexTensor],
) -> Optional[dict[str, object]]:
    if tensor is None:
        return None
    return _tensor_record(tensor)


def _matrix(tensor: FrozenComplexTensor, field: str) -> np.ndarray:
    _exact_record(tensor, FrozenComplexTensor, field)
    verify_frozen_tensor(tensor)
    result = frozen_tensor_array(tensor)
    if result.ndim != 2:
        raise ValueError(f"{field} must be a matrix")
    return np.asarray(result, dtype=np.complex128)


def _spectral_residual(matrix: np.ndarray) -> float:
    return float(np.linalg.norm(matrix, ord=2))


def _require_orthonormal_columns(matrix: np.ndarray, field: str) -> None:
    if matrix.shape[1] <= 0:
        raise ValueError(f"{field} must have a positive column count")
    identity = np.eye(matrix.shape[1], dtype=np.complex128)
    if (
        _spectral_residual(matrix.conj().T @ matrix - identity)
        > SELECTOR_RESIDUAL_TOLERANCE
    ):
        raise ValueError(f"{field} columns are not orthonormal")


def _require_hermitian_positive(matrix: np.ndarray, field: str) -> None:
    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"{field} must be square")
    if _spectral_residual(matrix - matrix.conj().T) > SELECTOR_RESIDUAL_TOLERANCE:
        raise ValueError(f"{field} must be Hermitian")
    eigenvalues = np.linalg.eigvalsh(matrix)
    if float(np.min(eigenvalues)) <= 0.0:
        raise ValueError(f"{field} must be positive definite")


def _require_same_subspace(
    first: np.ndarray,
    second: np.ndarray,
    field: str,
) -> None:
    if first.shape != second.shape:
        raise ValueError(f"{field} dimensions differ")
    first_projector = first @ first.conj().T
    second_projector = second @ second.conj().T
    if (
        _spectral_residual(first_projector - second_projector)
        > SELECTOR_RESIDUAL_TOLERANCE
    ):
        raise ValueError(f"{field} subspaces differ")


def _require_quotient_preserves_tt(
    quotient: np.ndarray,
    metric: np.ndarray,
    tt: np.ndarray,
) -> None:
    tt_metric = tt.conj().T @ quotient.conj().T @ metric @ quotient @ tt
    identity = np.eye(tt.shape[1], dtype=np.complex128)
    if _spectral_residual(tt_metric - identity) > SELECTOR_RESIDUAL_TOLERANCE:
        raise ValueError("physical quotient does not preserve the TT sector")


def _require_quotient_annihilates_gauge(
    quotient: np.ndarray,
    gauge: np.ndarray,
) -> None:
    if _spectral_residual(quotient @ gauge) > SELECTOR_RESIDUAL_TOLERANCE:
        raise ValueError("physical quotient does not annihilate the gauge sector")


def _expected_scenario_sectors(kind: str, scenario_id: str) -> tuple[str, ...]:
    if kind == C15_QUOTIENT_SPECTRUM:
        try:
            return _C15_SCENARIO_SECTORS[scenario_id]
        except KeyError as exc:
            raise ValueError("C15 scenario is not frozen") from exc
    if kind == C16_COVERAGE_CONTROL:
        if scenario_id not in _C16_SCENARIO_COVERAGE:
            raise ValueError("C16 scenario is not frozen")
        return ("coverage-probe",)
    if kind == C17_QUOTIENT_GAUGE_GRAPH and scenario_id == _C17_SCENARIO_ID:
        return ("dressed-coverage-probe-0", "dressed-coverage-probe-1")
    if kind == C18_INDEPENDENT_UNARY and scenario_id == _C18_SCENARIO_ID:
        return ("actual-source-q0", "matched-new-source-q1")
    if kind == C19_OBSERVER_COLLAPSE_CONDITIONS and scenario_id == _C19_SCENARIO_ID:
        return ("full-positive-0", "full-positive-1")
    raise ValueError("geometry scenario does not match its closed kind")


def _require_active_recipe_canonical_slot(
    kind: str,
    scenario_id: str,
    recipe_sha: str,
    source_recipe_shas: tuple[str, ...],
) -> None:
    if kind == C15_QUOTIENT_SPECTRUM:
        expected_index = _C15_SCENARIO_ORDER.index(scenario_id)
    elif kind == C16_COVERAGE_CONTROL:
        expected_index = 4
    else:
        expected_index = 0
    if source_recipe_shas[expected_index] != recipe_sha:
        raise ValueError("analytic source recipe is not in its canonical scenario slot")


@dataclass(frozen=True)
class GeometryAnalyticContextV2:
    """Narrow, authority-neutral input compiled from an exact Parent-v2 chain."""

    context_schema_version: str
    geometry_kind: GeometryKindV3
    control_case_id: str
    scenario_id: str
    scenario_sha: str
    recipe_sha: str
    operation_dag_sha: str
    compiled_contract_sha: str
    geometry_derivation_source_id: str
    semantic_sector_names: tuple[str, ...]
    selected_fejer_order: int
    analytic_source_recipe_shas: tuple[str, ...]
    coverage_control: Optional[float]
    gauge_amplitude: Optional[float]
    observer_collapse_expected: bool
    context_sha: str

    def __post_init__(self) -> None:
        _validate_geometry_analytic_context_v2_structure(self)


def _validate_geometry_analytic_context_v2_structure(
    context: GeometryAnalyticContextV2,
) -> None:
    if context.context_schema_version != (GEOMETRY_ANALYTIC_CONTEXT_V2_SCHEMA_VERSION):
        raise ValueError("geometry analytic context schema drifted")
    _text(context.geometry_kind, "geometry_kind")
    if context.geometry_kind not in GEOMETRY_KINDS_V3:
        raise ValueError("geometry kind is not closed")
    _text(context.control_case_id, "control_case_id")
    _text(context.scenario_id, "scenario_id")
    for field in (
        "scenario_sha",
        "recipe_sha",
        "operation_dag_sha",
        "compiled_contract_sha",
        "context_sha",
    ):
        _sha(getattr(context, field), field)
    _text(context.geometry_derivation_source_id, "geometry_derivation_source_id")
    sectors = _strings(context.semantic_sector_names, "semantic_sector_names")
    _positive_int(context.selected_fejer_order, "selected_fejer_order")
    source_shas = _shas(
        context.analytic_source_recipe_shas,
        "analytic_source_recipe_shas",
    )
    if type(context.observer_collapse_expected) is not bool:
        raise TypeError("observer_collapse_expected must be an exact bool")
    if context.coverage_control is not None:
        _finite_float(context.coverage_control, "coverage_control")
    if context.gauge_amplitude is not None:
        _finite_float(context.gauge_amplitude, "gauge_amplitude")

    kind = context.geometry_kind
    if context.control_case_id != _CONTROL_CASE_ID_BY_KIND[kind]:
        raise ValueError("control case does not match geometry kind")
    if (
        context.geometry_derivation_source_id
        != (GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND[kind])
    ):
        raise ValueError("geometry derivation source differs from reviewed Parent")
    if sectors != _expected_scenario_sectors(kind, context.scenario_id):
        raise ValueError("semantic sectors differ from the frozen scenario slice")
    if context.selected_fejer_order not in CANDIDATE_FEJER_ORDERS:
        raise ValueError("selected Fejer order is not preregistered")
    if len(source_shas) != _ANALYTIC_SOURCE_RECIPE_COUNT_BY_KIND[kind]:
        raise ValueError("analytic source recipe SHA count drifted")
    if context.recipe_sha not in source_shas:
        raise ValueError("active recipe SHA is absent from analytic sources")
    _require_active_recipe_canonical_slot(
        kind,
        context.scenario_id,
        context.recipe_sha,
        source_shas,
    )

    expected_coverage: Optional[float] = None
    if kind == C16_COVERAGE_CONTROL:
        expected_coverage = _C16_SCENARIO_COVERAGE[context.scenario_id][0]
    if expected_coverage is None:
        if context.coverage_control is not None:
            raise ValueError("non-C16 context contains a coverage control")
    elif context.coverage_control is None or not _fp64_equal(
        context.coverage_control,
        expected_coverage,
    ):
        raise ValueError("C16 coverage control differs from reviewed Parent")

    if kind == C17_QUOTIENT_GAUGE_GRAPH:
        if context.gauge_amplitude is None or not _fp64_equal(
            context.gauge_amplitude,
            8.0,
        ):
            raise ValueError("C17 gauge amplitude differs from reviewed Parent")
    elif context.gauge_amplitude is not None:
        raise ValueError("non-C17 context contains a gauge amplitude")

    expected_observer = kind == C19_OBSERVER_COLLAPSE_CONDITIONS
    if context.observer_collapse_expected is not expected_observer:
        raise ValueError("observer-collapse expectation differs from geometry kind")


def geometry_analytic_context_v2_payload(
    context: GeometryAnalyticContextV2,
) -> dict[str, object]:
    _exact_record(context, GeometryAnalyticContextV2, "geometry analytic context")
    context.__post_init__()
    return {
        "context_schema_version": context.context_schema_version,
        "geometry_kind": context.geometry_kind,
        "control_case_id": context.control_case_id,
        "scenario_id": context.scenario_id,
        "scenario_sha": context.scenario_sha,
        "recipe_sha": context.recipe_sha,
        "operation_dag_sha": context.operation_dag_sha,
        "compiled_contract_sha": context.compiled_contract_sha,
        "geometry_derivation_source_id": context.geometry_derivation_source_id,
        "semantic_sector_names": list(context.semantic_sector_names),
        "selected_fejer_order": context.selected_fejer_order,
        "analytic_source_recipe_shas": list(context.analytic_source_recipe_shas),
        "coverage_control": context.coverage_control,
        "gauge_amplitude": context.gauge_amplitude,
        "observer_collapse_expected": context.observer_collapse_expected,
    }


def verify_geometry_analytic_context_v2(
    context: GeometryAnalyticContextV2,
) -> GeometryAnalyticContextV2:
    _exact_record(context, GeometryAnalyticContextV2, "geometry analytic context")
    context.__post_init__()
    if context.context_sha != canonical_sha(
        geometry_analytic_context_v2_payload(context)
    ):
        raise ValueError("geometry analytic context SHA does not match its body")
    return context


@dataclass(frozen=True)
class ObserverCollapsePrerequisiteSpecV1:
    """Conditional theorem premises only; never a measured conclusion."""

    prerequisite_schema_version: str
    formula_or_certificate_id: str
    claim_ceiling: Literal["CONDITIONAL_PREREQUISITES_ONLY"]
    evaluation_state: Literal["NOT_EVALUATED_PRE_RESPONSE"]
    required_predicate_ids: tuple[str, ...]
    expected_incidence_rank: int
    expected_tt_dimension: int
    expected_gauge_dimension: int
    expected_row_dimension: int
    coisometry_residual_tolerance: float
    prerequisite_spec_sha: str

    def __post_init__(self) -> None:
        _validate_observer_collapse_prerequisite_structure(self)


def _validate_observer_collapse_prerequisite_structure(
    spec: ObserverCollapsePrerequisiteSpecV1,
) -> None:
    if spec.prerequisite_schema_version != (
        OBSERVER_COLLAPSE_PREREQUISITE_SPEC_V1_SCHEMA_VERSION
    ):
        raise ValueError("observer-collapse prerequisite schema drifted")
    _text(spec.formula_or_certificate_id, "formula_or_certificate_id")
    _text(spec.claim_ceiling, "claim_ceiling")
    _text(spec.evaluation_state, "evaluation_state")
    if spec.claim_ceiling != OBSERVER_COLLAPSE_CONDITIONAL_CLAIM_CEILING:
        raise ValueError("observer-collapse claim ceiling exceeds prerequisites")
    if spec.evaluation_state != OBSERVER_COLLAPSE_NOT_EVALUATED_STATE:
        raise ValueError("observer-collapse evaluation is not pre-response")
    _strings(spec.required_predicate_ids, "required_predicate_ids")
    for field in (
        "expected_incidence_rank",
        "expected_tt_dimension",
        "expected_gauge_dimension",
        "expected_row_dimension",
    ):
        _positive_int(getattr(spec, field), field)
    _finite_float(
        spec.coisometry_residual_tolerance,
        "coisometry_residual_tolerance",
    )
    _sha(spec.prerequisite_spec_sha, "prerequisite_spec_sha")


def observer_collapse_prerequisite_spec_v1_payload(
    spec: ObserverCollapsePrerequisiteSpecV1,
) -> dict[str, object]:
    _exact_record(
        spec,
        ObserverCollapsePrerequisiteSpecV1,
        "observer-collapse prerequisite",
    )
    spec.__post_init__()
    return {
        "prerequisite_schema_version": spec.prerequisite_schema_version,
        "formula_or_certificate_id": spec.formula_or_certificate_id,
        "claim_ceiling": spec.claim_ceiling,
        "evaluation_state": spec.evaluation_state,
        "required_predicate_ids": list(spec.required_predicate_ids),
        "expected_incidence_rank": spec.expected_incidence_rank,
        "expected_tt_dimension": spec.expected_tt_dimension,
        "expected_gauge_dimension": spec.expected_gauge_dimension,
        "expected_row_dimension": spec.expected_row_dimension,
        "coisometry_residual_tolerance": (spec.coisometry_residual_tolerance),
    }


def verify_observer_collapse_prerequisite_spec_v1(
    spec: ObserverCollapsePrerequisiteSpecV1,
) -> ObserverCollapsePrerequisiteSpecV1:
    _exact_record(
        spec,
        ObserverCollapsePrerequisiteSpecV1,
        "observer-collapse prerequisite",
    )
    spec.__post_init__()
    if spec.formula_or_certificate_id != (OBSERVER_COLLAPSE_CONDITIONAL_FORMULA_ID):
        raise ValueError("observer-collapse conditional formula drifted")
    if spec.required_predicate_ids != OBSERVER_COLLAPSE_REQUIRED_PREDICATE_IDS:
        raise ValueError("observer-collapse prerequisite list drifted")
    expected_dimensions = (6, 2, 4, 4)
    observed_dimensions = (
        spec.expected_incidence_rank,
        spec.expected_tt_dimension,
        spec.expected_gauge_dimension,
        spec.expected_row_dimension,
    )
    if observed_dimensions != expected_dimensions:
        raise ValueError("observer-collapse prerequisite dimensions drifted")
    if not _fp64_equal(spec.coisometry_residual_tolerance, 1.0e-12):
        raise ValueError("observer-collapse coisometry tolerance drifted")
    if spec.prerequisite_spec_sha != canonical_sha(
        observer_collapse_prerequisite_spec_v1_payload(spec)
    ):
        raise ValueError("observer-collapse prerequisite SHA does not match body")
    return spec


@dataclass(frozen=True)
class ScenarioResponseGeometryBundleV3:
    """Self-hashing analytic geometry inputs, frozen before any response."""

    geometry_bundle_schema_version: str
    geometry_kind: GeometryKindV3
    analytic_context_sha: str
    scenario_id: str
    scenario_sha: str
    recipe_sha: str
    geometry_derivation_source_id: str
    semantic_sector_names: tuple[str, ...]
    selected_fejer_order: int
    analytic_source_recipe_shas: tuple[str, ...]
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
    observer_collapse_spec: Optional[ObserverCollapsePrerequisiteSpecV1]
    geometry_bundle_sha: str

    def __post_init__(self) -> None:
        _validate_geometry_bundle_v3_structure(self)


def _validate_geometry_bundle_v3_structure(
    bundle: ScenarioResponseGeometryBundleV3,
) -> None:
    if bundle.geometry_bundle_schema_version != (
        SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V3_SCHEMA_VERSION
    ):
        raise ValueError("geometry bundle schema drifted")
    _text(bundle.geometry_kind, "geometry_kind")
    if bundle.geometry_kind not in GEOMETRY_KINDS_V3:
        raise ValueError("geometry kind is not closed")
    _sha(bundle.analytic_context_sha, "analytic_context_sha")
    _text(bundle.scenario_id, "scenario_id")
    for field in ("scenario_sha", "recipe_sha", "geometry_bundle_sha"):
        _sha(getattr(bundle, field), field)
    _text(bundle.geometry_derivation_source_id, "geometry_derivation_source_id")
    _strings(bundle.semantic_sector_names, "semantic_sector_names")
    _positive_int(bundle.selected_fejer_order, "selected_fejer_order")
    _shas(bundle.analytic_source_recipe_shas, "analytic_source_recipe_shas")
    for field in (
        "kernel_basis",
        "physical_quotient_map",
        "physical_quotient_metric",
        "target_physical_representatives",
    ):
        if type(getattr(bundle, field)) is not FrozenComplexTensor:
            raise TypeError(f"{field} must be an exact FrozenComplexTensor")
    _optional_text(bundle.coverage_control_id, "coverage_control_id")
    _float_tuple(
        bundle.coverage_control_wire,
        "coverage_control_wire",
        allow_empty=True,
    )
    for field in ("undressed_response_representatives", "gauge_basis"):
        value = getattr(bundle, field)
        if value is not None and type(value) is not FrozenComplexTensor:
            raise TypeError(f"{field} must be an exact FrozenComplexTensor or None")
    if bundle.gauge_amplitude is not None:
        _finite_float(bundle.gauge_amplitude, "gauge_amplitude")
    if bundle.expected_graph_rank is not None:
        _positive_int(bundle.expected_graph_rank, "expected_graph_rank")
    for field in (
        "analytic_graph_singular_values",
        "expected_actual_raw_graph_singular_values",
        "expected_ablated_raw_graph_singular_values",
    ):
        values = _float_tuple(getattr(bundle, field), field, allow_empty=True)
        if any(value < 0.0 for value in values):
            raise ValueError(f"{field} must be non-negative")
    _optional_text(
        bundle.fejer_graph_slope_formula_id,
        "fejer_graph_slope_formula_id",
    )
    if bundle.observer_collapse_spec is not None:
        _exact_record(
            bundle.observer_collapse_spec,
            ObserverCollapsePrerequisiteSpecV1,
            "observer_collapse_spec",
        )
        bundle.observer_collapse_spec.__post_init__()


def _observer_spec_record(
    spec: Optional[ObserverCollapsePrerequisiteSpecV1],
) -> Optional[dict[str, object]]:
    if spec is None:
        return None
    return {
        **observer_collapse_prerequisite_spec_v1_payload(spec),
        "prerequisite_spec_sha": spec.prerequisite_spec_sha,
    }


def scenario_response_geometry_bundle_v3_payload(
    bundle: ScenarioResponseGeometryBundleV3,
) -> dict[str, object]:
    _exact_record(bundle, ScenarioResponseGeometryBundleV3, "geometry bundle")
    bundle.__post_init__()
    return {
        "geometry_bundle_schema_version": bundle.geometry_bundle_schema_version,
        "geometry_kind": bundle.geometry_kind,
        "analytic_context_sha": bundle.analytic_context_sha,
        "scenario_id": bundle.scenario_id,
        "scenario_sha": bundle.scenario_sha,
        "recipe_sha": bundle.recipe_sha,
        "geometry_derivation_source_id": (bundle.geometry_derivation_source_id),
        "semantic_sector_names": list(bundle.semantic_sector_names),
        "selected_fejer_order": bundle.selected_fejer_order,
        "analytic_source_recipe_shas": list(bundle.analytic_source_recipe_shas),
        "kernel_basis": _tensor_record(bundle.kernel_basis),
        "physical_quotient_map": _tensor_record(bundle.physical_quotient_map),
        "physical_quotient_metric": _tensor_record(bundle.physical_quotient_metric),
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
        "analytic_graph_singular_values": list(bundle.analytic_graph_singular_values),
        "fejer_graph_slope_formula_id": bundle.fejer_graph_slope_formula_id,
        "expected_actual_raw_graph_singular_values": list(
            bundle.expected_actual_raw_graph_singular_values
        ),
        "expected_ablated_raw_graph_singular_values": list(
            bundle.expected_ablated_raw_graph_singular_values
        ),
        "observer_collapse_spec": _observer_spec_record(bundle.observer_collapse_spec),
    }


def _geometry_matrices(
    bundle: ScenarioResponseGeometryBundleV3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    kernel = _matrix(bundle.kernel_basis, "kernel_basis")
    quotient = _matrix(bundle.physical_quotient_map, "physical_quotient_map")
    metric = _matrix(
        bundle.physical_quotient_metric,
        "physical_quotient_metric",
    )
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
    _require_orthonormal_columns(kernel, "kernel_basis")
    _require_orthonormal_columns(targets, "target_physical_representatives")
    return kernel, quotient, metric, targets


def _forbid_fields(
    bundle: ScenarioResponseGeometryBundleV3,
    *,
    coverage: bool,
    graph: bool,
    gauge_basis: bool,
    observer: bool,
    kind_label: str,
) -> None:
    if coverage and (
        bundle.coverage_control_id is not None or bundle.coverage_control_wire
    ):
        raise ValueError(f"{kind_label} contains cross-kind coverage fields")
    graph_values = (
        bundle.undressed_response_representatives,
        bundle.gauge_amplitude,
        bundle.expected_graph_rank,
        bundle.fejer_graph_slope_formula_id,
    )
    graph_wires = (
        bundle.analytic_graph_singular_values,
        bundle.expected_actual_raw_graph_singular_values,
        bundle.expected_ablated_raw_graph_singular_values,
    )
    if graph and (any(value is not None for value in graph_values) or any(graph_wires)):
        raise ValueError(f"{kind_label} contains cross-kind graph fields")
    if gauge_basis and bundle.gauge_basis is not None:
        raise ValueError(f"{kind_label} contains a cross-kind gauge basis")
    if observer and bundle.observer_collapse_spec is not None:
        raise ValueError(f"{kind_label} contains cross-kind observer fields")


def _verify_c15_bundle(
    bundle: ScenarioResponseGeometryBundleV3,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> None:
    kernel, quotient, metric, targets = matrices
    _forbid_fields(
        bundle,
        coverage=True,
        graph=True,
        gauge_basis=False,
        observer=True,
        kind_label="C15",
    )
    if bundle.gauge_basis is None:
        raise ValueError("C15 geometry lacks its analytic gauge basis")
    gauge = _matrix(bundle.gauge_basis, "gauge_basis")
    if (
        kernel.shape[1] != 3
        or targets.shape[1] != 2
        or gauge.shape
        != (
            kernel.shape[0],
            1,
        )
    ):
        raise ValueError("C15 TT/gauge ranks drifted")
    _require_orthonormal_columns(gauge, "gauge_basis")
    _require_same_subspace(
        kernel,
        np.column_stack((targets, gauge)),
        "C15 kernel and TT/gauge",
    )
    _require_quotient_annihilates_gauge(quotient, gauge)
    _require_quotient_preserves_tt(quotient, metric, targets)


def _verify_c16_bundle(
    bundle: ScenarioResponseGeometryBundleV3,
) -> None:
    _forbid_fields(
        bundle,
        coverage=False,
        graph=True,
        gauge_basis=True,
        observer=True,
        kind_label="C16",
    )
    if bundle.coverage_control_id is None:
        raise ValueError("C16 geometry lacks its coverage control ID")
    try:
        coverage, local_id = _C16_SCENARIO_COVERAGE[bundle.scenario_id]
    except KeyError as exc:
        raise ValueError("C16 bundle scenario is not frozen") from exc
    application_instance_id = bundle.scenario_id.split(".scenario.", 1)[0]
    expected_control_id = f"{application_instance_id}.{local_id}"
    if bundle.coverage_control_id != expected_control_id:
        raise ValueError("C16 coverage control ID is not the scenario output")
    if not _fp64_tuple_equal(bundle.coverage_control_wire, (coverage,)):
        raise ValueError("C16 coverage control fp64 wire drifted")


def _verify_c17_bundle(
    bundle: ScenarioResponseGeometryBundleV3,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> None:
    kernel, quotient, metric, _ = matrices
    if bundle.coverage_control_id is not None or bundle.coverage_control_wire:
        raise ValueError("C17 contains cross-kind coverage fields")
    if bundle.observer_collapse_spec is not None:
        raise ValueError("C17 contains cross-kind observer fields")
    required = (
        bundle.undressed_response_representatives,
        bundle.gauge_basis,
        bundle.gauge_amplitude,
        bundle.expected_graph_rank,
        bundle.fejer_graph_slope_formula_id,
    )
    if any(value is None for value in required):
        raise ValueError("C17 graph bundle is incomplete")
    rank = bundle.expected_graph_rank
    assert rank is not None
    if rank != 2:
        raise ValueError("C17 expected graph rank drifted")
    undressed = _matrix(
        bundle.undressed_response_representatives,
        "undressed_response_representatives",
    )
    gauge = _matrix(bundle.gauge_basis, "gauge_basis")
    if undressed.shape != gauge.shape or gauge.shape != (kernel.shape[0], rank):
        raise ValueError("C17 T/G representatives have wrong shape")
    _require_orthonormal_columns(undressed, "undressed_response_representatives")
    _require_orthonormal_columns(gauge, "gauge_basis")
    if _spectral_residual(undressed.conj().T @ gauge) > SELECTOR_RESIDUAL_TOLERANCE:
        raise ValueError("C17 T/G frames are not orthogonal")
    _require_same_subspace(
        kernel,
        np.column_stack((undressed, gauge)),
        "C17 kernel and T/G",
    )
    _require_quotient_annihilates_gauge(quotient, gauge)
    _require_quotient_preserves_tt(quotient, metric, undressed)

    if bundle.gauge_amplitude is None or not _fp64_equal(
        bundle.gauge_amplitude,
        8.0,
    ):
        raise ValueError("C17 gauge amplitude drifted")
    if bundle.fejer_graph_slope_formula_id != (C17_FEJER_GRAPH_SLOPE_FORMULA_ID):
        raise ValueError("C17 Fejer graph formula drifted")
    leakage = 1.0 / float(bundle.selected_fejer_order + 1)
    ablated = 8.0 * leakage
    expected_analytic = (8.0, 8.0)
    expected_ablated = (ablated, ablated)
    if not _fp64_tuple_equal(
        bundle.analytic_graph_singular_values,
        expected_analytic,
    ):
        raise ValueError("C17 analytic graph slope drifted")
    if not _fp64_tuple_equal(
        bundle.expected_actual_raw_graph_singular_values,
        expected_analytic,
    ):
        raise ValueError("C17 actual Fejer graph slope drifted")
    if not _fp64_tuple_equal(
        bundle.expected_ablated_raw_graph_singular_values,
        expected_ablated,
    ):
        raise ValueError("C17 ablated Fejer graph slope formula drifted")


def _verify_c18_bundle(
    bundle: ScenarioResponseGeometryBundleV3,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> None:
    kernel, quotient, metric, targets = matrices
    _forbid_fields(
        bundle,
        coverage=True,
        graph=True,
        gauge_basis=True,
        observer=True,
        kind_label="C18",
    )
    identity = np.eye(4, dtype=np.complex128)
    if (
        kernel.shape != (4, 1)
        or quotient.shape != (4, 4)
        or metric.shape != (4, 4)
        or targets.shape != (4, 2)
    ):
        raise ValueError("C18 unary geometry dimensions drifted")
    if not np.array_equal(quotient, identity) or not np.array_equal(
        metric,
        identity,
    ):
        raise ValueError("C18 unary physical quotient and metric must be identity")
    _require_same_subspace(kernel, targets[:, :1], "C18 actual direction")


def _verify_c19_bundle(bundle: ScenarioResponseGeometryBundleV3) -> None:
    _forbid_fields(
        bundle,
        coverage=True,
        graph=True,
        gauge_basis=True,
        observer=False,
        kind_label="C19",
    )
    if bundle.observer_collapse_spec is None:
        raise ValueError("C19 lacks conditional observer-collapse prerequisites")
    verify_observer_collapse_prerequisite_spec_v1(bundle.observer_collapse_spec)


def verify_scenario_response_geometry_bundle_v3(
    bundle: ScenarioResponseGeometryBundleV3,
) -> ScenarioResponseGeometryBundleV3:
    """Verify a raw analytic body without promoting it to authority."""

    _exact_record(bundle, ScenarioResponseGeometryBundleV3, "geometry bundle")
    bundle.__post_init__()
    if bundle.observer_collapse_spec is not None:
        verify_observer_collapse_prerequisite_spec_v1(bundle.observer_collapse_spec)
    if bundle.geometry_bundle_sha != canonical_sha(
        scenario_response_geometry_bundle_v3_payload(bundle)
    ):
        raise ValueError("geometry bundle SHA does not match its body")

    if bundle.selected_fejer_order not in CANDIDATE_FEJER_ORDERS:
        raise ValueError("geometry bundle Fejer order is not preregistered")
    if (
        bundle.geometry_derivation_source_id
        != (GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND[bundle.geometry_kind])
    ):
        raise ValueError("geometry bundle derivation source drifted")
    if bundle.semantic_sector_names != _expected_scenario_sectors(
        bundle.geometry_kind,
        bundle.scenario_id,
    ):
        raise ValueError("geometry bundle semantic scenario slice drifted")
    if bundle.recipe_sha not in bundle.analytic_source_recipe_shas:
        raise ValueError("geometry bundle active recipe is absent from sources")
    expected_source_count = _ANALYTIC_SOURCE_RECIPE_COUNT_BY_KIND[bundle.geometry_kind]
    if len(bundle.analytic_source_recipe_shas) != expected_source_count:
        raise ValueError("geometry bundle analytic source count drifted")
    _require_active_recipe_canonical_slot(
        bundle.geometry_kind,
        bundle.scenario_id,
        bundle.recipe_sha,
        bundle.analytic_source_recipe_shas,
    )

    matrices = _geometry_matrices(bundle)
    if bundle.geometry_kind == C15_QUOTIENT_SPECTRUM:
        _verify_c15_bundle(bundle, matrices)
    elif bundle.geometry_kind == C16_COVERAGE_CONTROL:
        _verify_c16_bundle(bundle)
    elif bundle.geometry_kind == C17_QUOTIENT_GAUGE_GRAPH:
        _verify_c17_bundle(bundle, matrices)
    elif bundle.geometry_kind == C18_INDEPENDENT_UNARY:
        _verify_c18_bundle(bundle, matrices)
    elif bundle.geometry_kind == C19_OBSERVER_COLLAPSE_CONDITIONS:
        _verify_c19_bundle(bundle)
    else:  # pragma: no cover - closed by the exact kind check above.
        raise ValueError("geometry kind is not closed")
    return bundle


def verify_scenario_response_geometry_bundle_v3_for_context(
    context: GeometryAnalyticContextV2,
    bundle: ScenarioResponseGeometryBundleV3,
) -> ScenarioResponseGeometryBundleV3:
    """Bind a raw v3 geometry body to one exact analytic context."""

    verify_geometry_analytic_context_v2(context)
    verify_scenario_response_geometry_bundle_v3(bundle)
    expected = (
        context.geometry_kind,
        context.context_sha,
        context.scenario_id,
        context.scenario_sha,
        context.recipe_sha,
        context.geometry_derivation_source_id,
        context.semantic_sector_names,
        context.selected_fejer_order,
        context.analytic_source_recipe_shas,
    )
    observed = (
        bundle.geometry_kind,
        bundle.analytic_context_sha,
        bundle.scenario_id,
        bundle.scenario_sha,
        bundle.recipe_sha,
        bundle.geometry_derivation_source_id,
        bundle.semantic_sector_names,
        bundle.selected_fejer_order,
        bundle.analytic_source_recipe_shas,
    )
    if observed != expected:
        raise ValueError("geometry bundle differs from its analytic context")
    if context.geometry_kind == C16_COVERAGE_CONTROL:
        expected_coverage = context.coverage_control
        assert expected_coverage is not None
        if not _fp64_tuple_equal(
            bundle.coverage_control_wire,
            (expected_coverage,),
        ):
            raise ValueError("C16 bundle coverage differs from analytic context")
    if context.geometry_kind == C17_QUOTIENT_GAUGE_GRAPH:
        expected_amplitude = context.gauge_amplitude
        assert expected_amplitude is not None
        if bundle.gauge_amplitude is None or not _fp64_equal(
            bundle.gauge_amplitude,
            expected_amplitude,
        ):
            raise ValueError("C17 bundle gauge differs from analytic context")
    if context.geometry_kind == C19_OBSERVER_COLLAPSE_CONDITIONS and not (
        context.observer_collapse_expected
    ):
        raise ValueError("C19 context does not select observer-collapse")
    return bundle


__all__ = [
    "C15_QUOTIENT_SPECTRUM",
    "C16_COVERAGE_CONTROL",
    "C17_FEJER_GRAPH_SLOPE_FORMULA_ID",
    "C17_QUOTIENT_GAUGE_GRAPH",
    "C18_INDEPENDENT_UNARY",
    "C19_OBSERVER_COLLAPSE_CONDITIONS",
    "CANDIDATE_FEJER_ORDERS",
    "GEOMETRY_ANALYTIC_CONTEXT_V2_SCHEMA_VERSION",
    "GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND",
    "GEOMETRY_KINDS_V3",
    "GeometryAnalyticContextV2",
    "GeometryKindV3",
    "OBSERVER_COLLAPSE_CONDITIONAL_CLAIM_CEILING",
    "OBSERVER_COLLAPSE_CONDITIONAL_FORMULA_ID",
    "OBSERVER_COLLAPSE_NOT_EVALUATED_STATE",
    "OBSERVER_COLLAPSE_PREREQUISITE_SPEC_V1_SCHEMA_VERSION",
    "OBSERVER_COLLAPSE_REQUIRED_PREDICATE_IDS",
    "ObserverCollapsePrerequisiteSpecV1",
    "SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V3_SCHEMA_VERSION",
    "SELECTOR_RESIDUAL_TOLERANCE",
    "ScenarioResponseGeometryBundleV3",
    "geometry_analytic_context_v2_payload",
    "observer_collapse_prerequisite_spec_v1_payload",
    "scenario_response_geometry_bundle_v3_payload",
    "verify_geometry_analytic_context_v2",
    "verify_observer_collapse_prerequisite_spec_v1",
    "verify_scenario_response_geometry_bundle_v3",
    "verify_scenario_response_geometry_bundle_v3_for_context",
]
