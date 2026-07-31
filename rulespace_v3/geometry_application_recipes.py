"""Local real-space construction recipes for the C15--C19 geometry controls.

The records in this module are deliberately *pre-permit* construction inputs.
They bind an exact ParentFreeze scenario and emit a bounded sequence of real
canonical shears, but they do not issue a response block, a geometry result, or
scientific authority.  The current ParentFreeze still declares a rank-one
application shell for C15--C19.  These recipes therefore remain explicitly
pending until the rank-two correction is signed and a live permit supplies the
selected Fejer order.

C15--C17 share the four-channel state schema and rank-two shell contract.
C15/C16 use a momentum-dependent positive-frequency carrier; C17 uses a
dedicated on-site ``diag(J,-J)`` carrier and a canonical graph conjugation.
Every elementary operation has real-space radius at most one and the matched
branch is obtained only by deleting the target-conditioned shear slots.

C18 deliberately has a different endpoint contract.  Its actual branch is
``diag(J,I)`` and therefore has the Parent-frozen rank-one positive shell;
its matched ablation is ``diag(J,J)`` and exposes a second response direction
to the same full two-axis source/readout pair.  Both composites are on-site.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Literal, Optional

import numpy as np
import sympy as sp

from .application_recipes import (
    ApplicationLocalShearStep,
    _canonical_pair_rotation_steps,
    _executed_effect_digest,
    _inverse_steps,
    _reciprocal_swap_steps,
    _two_mode_rotation_steps,
    application_local_shear_step_payload,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    PrimitiveInterface,
    PrimitiveOperatorWire,
    freeze_complex_tensor,
    frozen_tensor_array,
    verify_frozen_tensor,
)
from .geometry import (
    GeometryNumericalThresholds,
    _compute_geometry_spectrum_from_matrices,
)
from .parent_freeze import (
    ApplicationScenarioExecutionSpec,
    SyntheticApplicationOperation,
    V3M0SyntheticControlApplicationSpec,
    VerifiedParentFreeze,
    _reverify_verified_parent_freeze,
    application_scenario_execution_spec_payload,
    synthetic_application_operation_payload,
    verify_synthetic_control_application_spec,
)
from .response import compute_fejer_filtered_response
from .trace import (
    ConstructionTrace,
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
)


GEOMETRY_APPLICATION_RECIPE_SCHEMA_VERSION = (
    "v3m0.geometry-application-recipe.v1"
)
GEOMETRY_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION = (
    "v3m0.geometry-operator-bundle-template.v1"
)
GEOMETRY_SCENARIO_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION = (
    "v3m0.geometry-scenario-operator-bundle-template.v1"
)
C17_FINITE_RESPONSE_PREFLIGHT_SCHEMA_VERSION = (
    "v3m0.c17-finite-response-preflight.v1"
)
GEOMETRY_APPLICATION_INTEGRATION_STATE = (
    "PENDING_PARENT_REFREEZE_AND_LIVE_PERMIT_T_BINDING"
)

C15_GEOMETRY_SCENARIO_IDS = (
    "v3m0.synthetic-control.c15.v1.scenario.full-h.v1",
    "v3m0.synthetic-control.c15.v1.scenario.low-rank-tt.v1",
    "v3m0.synthetic-control.c15.v1.scenario.tt.v1",
    "v3m0.synthetic-control.c15.v1.scenario.tt-plus-row.v1",
)
C16_GEOMETRY_SCENARIO_IDS = (
    "v3m0.synthetic-control.c16.v1.scenario.coverage-low.v1",
    "v3m0.synthetic-control.c16.v1.scenario.coverage-high.v1",
)
C17_GEOMETRY_SCENARIO_IDS = (
    "v3m0.synthetic-control.c17.v1.scenario.quotient-gauge.v1",
)
C18_GEOMETRY_SCENARIO_IDS = (
    "v3m0.synthetic-control.c18.v1.scenario.independent-unary.v1",
)
C19_GEOMETRY_SCENARIO_IDS = (
    "v3m0.synthetic-control.c19.v1.scenario.observer-collapse.v1",
)
GEOMETRY_APPLICATION_SCENARIO_IDS = (
    *C15_GEOMETRY_SCENARIO_IDS,
    *C16_GEOMETRY_SCENARIO_IDS,
    *C17_GEOMETRY_SCENARIO_IDS,
    *C18_GEOMETRY_SCENARIO_IDS,
    *C19_GEOMETRY_SCENARIO_IDS,
)

_CONTROL_CASES = frozenset(
    (
        "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
        "C16_COVERAGE_025_075",
        "C17_QUOTIENT_GAUGE_COVERAGE",
        "C18_ABLATED_INDEPENDENT_UNARY",
        "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
    )
)
_CHANNEL_ORDER = ("q0", "p0", "q1", "p1")
_CHANNEL_INDEX = {name: index for index, name in enumerate(_CHANNEL_ORDER)}
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_COMMON_MOMENTA = (math.pi / 4.0, math.pi / 2.0)
_COMMON_ALPHA = math.pi / 8.0
_COMMON_BETA = -math.pi / 4.0
_COMMON_CONDITIONING_ANGLE = 1.0 / 8.0
_C19_PHASE_TOOTH = 2.0**-14
_CANDIDATE_FEJER_ORDERS = (256, 512, 1024, 2048, 4096, 8192)

C15_EXPECTED_SPECTRA = {
    C15_GEOMETRY_SCENARIO_IDS[0]: (
        (1.0, 0.0, 0.0, 0.0),
        (1.0, 1.0),
    ),
    C15_GEOMETRY_SCENARIO_IDS[1]: ((0.0,), (0.0, 1.0)),
    C15_GEOMETRY_SCENARIO_IDS[2]: ((0.0, 0.0), (1.0, 1.0)),
    C15_GEOMETRY_SCENARIO_IDS[3]: (
        (1.0, 0.0, 0.0),
        (1.0, 1.0),
    ),
}


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


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    try:
        observed = frozenset(vars(value))
    except TypeError as exc:
        raise TypeError(f"{field} has no exact record body") from exc
    expected = frozenset(record_type.__dataclass_fields__)
    if observed != expected:
        raise ValueError(f"{field} contains missing or unknown fields")


def _operation_record(
    operation: SyntheticApplicationOperation,
) -> dict[str, object]:
    return {
        **synthetic_application_operation_payload(operation),
        "operation_sha": operation.operation_sha,
    }


def _scenario_operation_closure(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> tuple[SyntheticApplicationOperation, ...]:
    operation_by_id = {
        operation.operation_instance_id: operation
        for operation in application.operations
    }
    required = set(scenario.operation_output_ids)
    pending = list(scenario.operation_output_ids)
    while pending:
        identifier = pending.pop()
        try:
            operation = operation_by_id[identifier]
        except KeyError as exc:
            raise ValueError("scenario output is absent from its operation DAG") from exc
        for dependency in operation.input_operation_instance_ids:
            if dependency not in required:
                required.add(dependency)
                pending.append(dependency)
    closure = tuple(
        operation
        for operation in application.operations
        if operation.operation_instance_id in required
    )
    if not closure:
        raise ValueError("geometry scenario operation closure is empty")
    return closure


def _scenario_dag_sha(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> str:
    closure = _scenario_operation_closure(application, scenario)
    return canonical_sha(
        {
            "dag_schema_version": "v3m0.geometry-scenario-operation-dag.v1",
            "application_spec_sha": application.application_spec_sha,
            "scenario": {
                **application_scenario_execution_spec_payload(scenario),
                "scenario_sha": scenario.scenario_sha,
            },
            "operations": [_operation_record(operation) for operation in closure],
        }
    )


@dataclass(frozen=True)
class GeometryApplicationRecipeArtifact:
    recipe_schema_version: str
    control_case_id: str
    scenario_id: str
    application_spec_sha: str
    scenario_sha: str
    operation_dag_sha: str
    recipe_id: str
    construction_rule_id: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_ndim: int
    response_torus_denominator: int
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    reference_phase_bands: tuple[tuple[float, float], ...]
    expected_shell_rank: int
    primitive_support_radius: int
    semantic_sector_names: tuple[str, ...]
    actual_steps: tuple[ApplicationLocalShearStep, ...]
    matched_ablated_steps: tuple[ApplicationLocalShearStep, ...]
    source_injection: FrozenComplexTensor
    readout: FrozenComplexTensor
    coverage_control: Optional[float]
    gauge_amplitude: Optional[float]
    observer_collapse_expected: bool
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    integration_state: Literal[
        "PENDING_PARENT_REFREEZE_AND_LIVE_PERMIT_T_BINDING"
    ]
    recipe_sha: str

    def __post_init__(self) -> None:
        if self.recipe_schema_version != GEOMETRY_APPLICATION_RECIPE_SCHEMA_VERSION:
            raise ValueError("geometry application recipe schema is not frozen")
        if self.control_case_id not in _CONTROL_CASES:
            raise ValueError("geometry application control case is not registered")
        if self.scenario_id not in GEOMETRY_APPLICATION_SCENARIO_IDS:
            raise ValueError("geometry application scenario is not registered")
        for field in (
            "application_spec_sha",
            "scenario_sha",
            "operation_dag_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "recipe_sha",
        ):
            _sha(getattr(self, field), field)
        _text(self.recipe_id, "recipe_id")
        _text(self.construction_rule_id, "construction_rule_id")
        _text(self.state_schema_id, "state_schema_id")
        if self.channel_order != _CHANNEL_ORDER:
            raise ValueError("geometry recipe channel order is not frozen")
        if self.spatial_ndim != 1:
            raise ValueError("geometry recipe spatial dimension is not frozen")
        if self.response_torus_denominator != 8:
            raise ValueError("geometry recipe response denominator is not frozen")
        if self.response_reciprocal_indices != ((1,), (2,)):
            raise ValueError("geometry recipe response grid is not frozen")
        if (
            type(self.reference_phase_bands) is not tuple
            or len(self.reference_phase_bands) != 1
        ):
            raise ValueError("geometry recipe phase band is not unique")
        expected_shell_rank = (
            1 if self.scenario_id in C18_GEOMETRY_SCENARIO_IDS else 2
        )
        if self.expected_shell_rank != expected_shell_rank:
            raise ValueError("geometry recipe shell rank is not scenario-frozen")
        expected_support_radius = (
            0 if self.scenario_id in C18_GEOMETRY_SCENARIO_IDS else 1
        )
        if self.primitive_support_radius != expected_support_radius:
            raise ValueError("geometry primitive support radius is not frozen")
        if (
            type(self.semantic_sector_names) is not tuple
            or not self.semantic_sector_names
        ):
            raise ValueError("geometry semantic sectors are empty")
        if (
            type(self.actual_steps) is not tuple
            or not self.actual_steps
            or not all(
                type(step) is ApplicationLocalShearStep
                for step in self.actual_steps
            )
        ):
            raise TypeError("geometry actual steps have the wrong strict type")
        if self.matched_ablated_steps != tuple(
            step for step in self.actual_steps if not step.target_conditioned
        ):
            raise ValueError("geometry matched ablation is not mechanical")
        if not any(step.target_conditioned for step in self.actual_steps):
            raise ValueError("geometry recipe has no target-conditioned tooth")
        if len({step.step_id for step in self.actual_steps}) != len(
            self.actual_steps
        ):
            raise ValueError("geometry recipe step IDs repeat")
        for field in ("source_injection", "readout"):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        source_shape = frozen_tensor_array(self.source_injection).shape
        if source_shape[0] != 4:
            raise ValueError("geometry source state axis is not frozen")
        expected_readout_shape = (
            (2, 4)
            if self.scenario_id in C18_GEOMETRY_SCENARIO_IDS
            else (4, 4)
        )
        if frozen_tensor_array(self.readout).shape != expected_readout_shape:
            raise ValueError("geometry readout shape is not frozen")
        if (
            self.scenario_id in C18_GEOMETRY_SCENARIO_IDS
            and source_shape != (4, 2)
        ):
            raise ValueError("C18 full source selector shape is not frozen")
        for field in ("coverage_control", "gauge_amplitude"):
            value = getattr(self, field)
            if value is not None and (
                type(value) is not float or not math.isfinite(value)
            ):
                raise TypeError(f"{field} must be finite fp64 or None")
        if type(self.observer_collapse_expected) is not bool:
            raise TypeError("observer_collapse_expected must be an exact bool")
        if self.actual_effect_digest == self.matched_ablated_effect_digest:
            raise ValueError("geometry actual and ablated effects are identical")
        if self.integration_state != GEOMETRY_APPLICATION_INTEGRATION_STATE:
            raise ValueError("geometry recipe cannot claim live integration")


def geometry_application_recipe_payload(
    recipe: GeometryApplicationRecipeArtifact,
) -> dict[str, object]:
    if type(recipe) is not GeometryApplicationRecipeArtifact:
        raise TypeError("recipe must be an exact GeometryApplicationRecipeArtifact")
    return {
        "recipe_schema_version": recipe.recipe_schema_version,
        "control_case_id": recipe.control_case_id,
        "scenario_id": recipe.scenario_id,
        "application_spec_sha": recipe.application_spec_sha,
        "scenario_sha": recipe.scenario_sha,
        "operation_dag_sha": recipe.operation_dag_sha,
        "recipe_id": recipe.recipe_id,
        "construction_rule_id": recipe.construction_rule_id,
        "state_schema_id": recipe.state_schema_id,
        "channel_order": list(recipe.channel_order),
        "spatial_ndim": recipe.spatial_ndim,
        "response_torus_denominator": recipe.response_torus_denominator,
        "response_reciprocal_indices": [
            list(index) for index in recipe.response_reciprocal_indices
        ],
        "reference_phase_bands": [
            list(band) for band in recipe.reference_phase_bands
        ],
        "expected_shell_rank": recipe.expected_shell_rank,
        "primitive_support_radius": recipe.primitive_support_radius,
        "semantic_sector_names": list(recipe.semantic_sector_names),
        "actual_steps": [
            {
                **application_local_shear_step_payload(step),
                "step_sha": step.step_sha,
            }
            for step in recipe.actual_steps
        ],
        "matched_ablated_steps": [
            {
                **application_local_shear_step_payload(step),
                "step_sha": step.step_sha,
            }
            for step in recipe.matched_ablated_steps
        ],
        "source_injection_sha": recipe.source_injection.tensor_sha,
        "readout_sha": recipe.readout.tensor_sha,
        "coverage_control": recipe.coverage_control,
        "gauge_amplitude": recipe.gauge_amplitude,
        "observer_collapse_expected": recipe.observer_collapse_expected,
        "actual_effect_digest": recipe.actual_effect_digest,
        "matched_ablated_effect_digest": recipe.matched_ablated_effect_digest,
        "integration_state": recipe.integration_state,
    }


@dataclass(frozen=True)
class GeometryOperatorBundleTemplate:
    bundle_schema_version: str
    parent_freeze_sha: str
    application_spec_sha: str
    scenario_recipe_shas: tuple[str, ...]
    construction_rule_id: str
    selected_fejer_order: int
    observer_dimension: int
    kernel_basis: FrozenComplexTensor
    physical_quotient_map: FrozenComplexTensor
    physical_quotient_metric: FrozenComplexTensor
    target_physical_representatives: FrozenComplexTensor
    integration_state: Literal[
        "PENDING_PARENT_REFREEZE_AND_LIVE_PERMIT_T_BINDING"
    ]
    bundle_sha: str

    def __post_init__(self) -> None:
        if (
            self.bundle_schema_version
            != GEOMETRY_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION
        ):
            raise ValueError("geometry operator-bundle template schema is not frozen")
        _sha(self.parent_freeze_sha, "parent_freeze_sha")
        _sha(self.application_spec_sha, "application_spec_sha")
        if (
            type(self.scenario_recipe_shas) is not tuple
            or not self.scenario_recipe_shas
        ):
            raise ValueError("geometry bundle scenario recipes are empty")
        for index, digest in enumerate(self.scenario_recipe_shas):
            _sha(digest, f"scenario_recipe_shas[{index}]")
        _text(self.construction_rule_id, "construction_rule_id")
        if self.selected_fejer_order not in _CANDIDATE_FEJER_ORDERS:
            raise ValueError("geometry bundle Fejer order is not preregistered")
        if self.observer_dimension != 8:
            raise ValueError("geometry bundle observer dimension is not frozen")
        for field in (
            "kernel_basis",
            "physical_quotient_map",
            "physical_quotient_metric",
            "target_physical_representatives",
        ):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        if self.integration_state != GEOMETRY_APPLICATION_INTEGRATION_STATE:
            raise ValueError("geometry bundle template cannot claim live integration")
        _sha(self.bundle_sha, "bundle_sha")


@dataclass(frozen=True)
class GeometryScenarioOperatorBundleTemplate:
    """Scenario-bound pre-response geometry, never a live authority."""

    bundle_schema_version: str
    parent_freeze_sha: str
    control_case_id: str
    application_spec_sha: str
    scenario_id: str
    scenario_sha: str
    scenario_recipe_sha: str
    construction_rule_id: str
    selected_fejer_order: int
    observer_dimension: int
    kernel_basis: FrozenComplexTensor
    physical_quotient_map: FrozenComplexTensor
    physical_quotient_metric: FrozenComplexTensor
    target_physical_representatives: FrozenComplexTensor
    undressed_response_representatives: Optional[FrozenComplexTensor]
    dressed_response_representatives: Optional[FrozenComplexTensor]
    gauge_basis: Optional[FrozenComplexTensor]
    gauge_graph_singular_values: tuple[float, ...]
    finite_graph_formula_id: Optional[str]
    fejer_opposite_phase_leakage: Optional[float]
    expected_undressed_finite_graph_singular_values: tuple[float, ...]
    expected_dressed_finite_graph_singular_values: tuple[float, ...]
    coverage_control: Optional[float]
    gauge_amplitude: Optional[float]
    integration_state: Literal[
        "PENDING_PARENT_REFREEZE_AND_LIVE_PERMIT_T_BINDING"
    ]
    bundle_sha: str

    def __post_init__(self) -> None:
        if (
            self.bundle_schema_version
            != GEOMETRY_SCENARIO_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION
        ):
            raise ValueError("scenario geometry bundle schema is not frozen")
        for field in (
            "parent_freeze_sha",
            "application_spec_sha",
            "scenario_sha",
            "scenario_recipe_sha",
            "bundle_sha",
        ):
            _sha(getattr(self, field), field)
        if self.control_case_id not in _CONTROL_CASES:
            raise ValueError("scenario geometry control case is not registered")
        if self.scenario_id not in (
            *C16_GEOMETRY_SCENARIO_IDS,
            *C17_GEOMETRY_SCENARIO_IDS,
        ):
            raise ValueError("scenario geometry bundle is not C16 or C17")
        _text(self.construction_rule_id, "construction_rule_id")
        if self.selected_fejer_order not in _CANDIDATE_FEJER_ORDERS:
            raise ValueError("scenario geometry Fejer order is not preregistered")
        if self.observer_dimension != 8:
            raise ValueError("scenario geometry observer dimension is not frozen")
        for field in (
            "kernel_basis",
            "physical_quotient_map",
            "physical_quotient_metric",
            "target_physical_representatives",
        ):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        for field in (
            "undressed_response_representatives",
            "dressed_response_representatives",
            "gauge_basis",
        ):
            value = getattr(self, field)
            if value is not None and type(value) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        if type(self.gauge_graph_singular_values) is not tuple or not all(
            type(value) is float and math.isfinite(value) and value >= 0.0
            for value in self.gauge_graph_singular_values
        ):
            raise TypeError("gauge graph singular values must be finite fp64")
        if self.finite_graph_formula_id is not None:
            _text(self.finite_graph_formula_id, "finite_graph_formula_id")
        if self.fejer_opposite_phase_leakage is not None and (
            type(self.fejer_opposite_phase_leakage) is not float
            or not math.isfinite(self.fejer_opposite_phase_leakage)
            or self.fejer_opposite_phase_leakage < 0.0
        ):
            raise TypeError("Fejer opposite-phase leakage must be finite fp64")
        for field in (
            "expected_undressed_finite_graph_singular_values",
            "expected_dressed_finite_graph_singular_values",
        ):
            values = getattr(self, field)
            if type(values) is not tuple or not all(
                type(value) is float and math.isfinite(value) and value >= 0.0
                for value in values
            ):
                raise TypeError(
                    f"{field} must contain nonnegative finite fp64 values"
                )
        for field in ("coverage_control", "gauge_amplitude"):
            value = getattr(self, field)
            if value is not None and (
                type(value) is not float or not math.isfinite(value)
            ):
                raise TypeError(f"{field} must be finite fp64 or None")
        if self.integration_state != GEOMETRY_APPLICATION_INTEGRATION_STATE:
            raise ValueError("scenario geometry bundle cannot claim live integration")


@dataclass(frozen=True)
class C17FiniteResponsePreflight:
    """Saved raw two-branch diagnostic; explicitly not scientific authority."""

    preflight_schema_version: str
    parent_freeze_sha: str
    scenario_id: str
    scenario_sha: str
    scenario_recipe_sha: str
    bundle_sha: str
    selected_fejer_order: int
    finite_graph_formula_id: str
    fejer_opposite_phase_leakage: float
    raw_undressed_response: FrozenComplexTensor
    raw_dressed_response: FrozenComplexTensor
    undressed_active_singular_values: tuple[float, ...]
    dressed_active_singular_values: tuple[float, ...]
    undressed_graph_singular_values: tuple[float, ...]
    dressed_graph_singular_values: tuple[float, ...]
    expected_undressed_graph_singular_values: tuple[float, ...]
    expected_dressed_graph_singular_values: tuple[float, ...]
    undressed_physical_block_singular_values: tuple[float, ...]
    dressed_physical_block_singular_values: tuple[float, ...]
    expected_undressed_physical_block_singular_values: tuple[float, ...]
    expected_dressed_physical_block_singular_values: tuple[float, ...]
    undressed_g_spectrum: tuple[float, ...]
    dressed_g_spectrum: tuple[float, ...]
    undressed_c_spectrum: tuple[float, ...]
    dressed_c_spectrum: tuple[float, ...]
    graph_prediction_residual: float
    undressed_physical_block_prediction_residual: float
    dressed_physical_block_prediction_residual: float
    coverage_spectrum_drift: float
    integration_state: Literal[
        "PENDING_PARENT_REFREEZE_AND_LIVE_PERMIT_T_BINDING"
    ]
    preflight_sha: str

    def __post_init__(self) -> None:
        if self.preflight_schema_version != C17_FINITE_RESPONSE_PREFLIGHT_SCHEMA_VERSION:
            raise ValueError("C17 finite-response preflight schema is not frozen")
        for field in (
            "parent_freeze_sha",
            "scenario_sha",
            "scenario_recipe_sha",
            "bundle_sha",
            "preflight_sha",
        ):
            _sha(getattr(self, field), field)
        if self.scenario_id != C17_GEOMETRY_SCENARIO_IDS[0]:
            raise ValueError("C17 finite-response scenario is not frozen")
        if self.selected_fejer_order not in _CANDIDATE_FEJER_ORDERS:
            raise ValueError("C17 finite-response order is not preregistered")
        _text(self.finite_graph_formula_id, "finite_graph_formula_id")
        for field in (
            "fejer_opposite_phase_leakage",
            "graph_prediction_residual",
            "undressed_physical_block_prediction_residual",
            "dressed_physical_block_prediction_residual",
            "coverage_spectrum_drift",
        ):
            value = getattr(self, field)
            if type(value) is not float or not math.isfinite(value) or value < 0.0:
                raise TypeError(f"{field} must be nonnegative finite fp64")
        for field in ("raw_undressed_response", "raw_dressed_response"):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        for field in (
            "undressed_active_singular_values",
            "dressed_active_singular_values",
            "undressed_graph_singular_values",
            "dressed_graph_singular_values",
            "expected_undressed_graph_singular_values",
            "expected_dressed_graph_singular_values",
            "undressed_physical_block_singular_values",
            "dressed_physical_block_singular_values",
            "expected_undressed_physical_block_singular_values",
            "expected_dressed_physical_block_singular_values",
            "undressed_g_spectrum",
            "dressed_g_spectrum",
            "undressed_c_spectrum",
            "dressed_c_spectrum",
        ):
            values = getattr(self, field)
            if (
                type(values) is not tuple
                or len(values) != 2
                or not all(
                    type(value) is float
                    and math.isfinite(value)
                    and value >= 0.0
                    for value in values
                )
            ):
                raise TypeError(f"{field} must contain two nonnegative fp64 values")
        if self.integration_state != GEOMETRY_APPLICATION_INTEGRATION_STATE:
            raise ValueError("C17 preflight cannot claim live integration")


def geometry_scenario_operator_bundle_template_payload(
    bundle: GeometryScenarioOperatorBundleTemplate,
) -> dict[str, object]:
    if type(bundle) is not GeometryScenarioOperatorBundleTemplate:
        raise TypeError(
            "bundle must be an exact GeometryScenarioOperatorBundleTemplate"
        )
    return {
        "bundle_schema_version": bundle.bundle_schema_version,
        "parent_freeze_sha": bundle.parent_freeze_sha,
        "control_case_id": bundle.control_case_id,
        "application_spec_sha": bundle.application_spec_sha,
        "scenario_id": bundle.scenario_id,
        "scenario_sha": bundle.scenario_sha,
        "scenario_recipe_sha": bundle.scenario_recipe_sha,
        "construction_rule_id": bundle.construction_rule_id,
        "selected_fejer_order": bundle.selected_fejer_order,
        "observer_dimension": bundle.observer_dimension,
        "kernel_basis_sha": bundle.kernel_basis.tensor_sha,
        "physical_quotient_map_sha": bundle.physical_quotient_map.tensor_sha,
        "physical_quotient_metric_sha": (
            bundle.physical_quotient_metric.tensor_sha
        ),
        "target_physical_representatives_sha": (
            bundle.target_physical_representatives.tensor_sha
        ),
        "undressed_response_representatives_sha": (
            None
            if bundle.undressed_response_representatives is None
            else bundle.undressed_response_representatives.tensor_sha
        ),
        "dressed_response_representatives_sha": (
            None
            if bundle.dressed_response_representatives is None
            else bundle.dressed_response_representatives.tensor_sha
        ),
        "gauge_basis_sha": (
            None
            if bundle.gauge_basis is None
            else bundle.gauge_basis.tensor_sha
        ),
        "gauge_graph_singular_values": list(
            bundle.gauge_graph_singular_values
        ),
        "finite_graph_formula_id": bundle.finite_graph_formula_id,
        "fejer_opposite_phase_leakage": (
            bundle.fejer_opposite_phase_leakage
        ),
        "expected_undressed_finite_graph_singular_values": list(
            bundle.expected_undressed_finite_graph_singular_values
        ),
        "expected_dressed_finite_graph_singular_values": list(
            bundle.expected_dressed_finite_graph_singular_values
        ),
        "coverage_control": bundle.coverage_control,
        "gauge_amplitude": bundle.gauge_amplitude,
        "integration_state": bundle.integration_state,
    }


def c17_finite_response_preflight_payload(
    preflight: C17FiniteResponsePreflight,
) -> dict[str, object]:
    if type(preflight) is not C17FiniteResponsePreflight:
        raise TypeError("preflight must be an exact C17FiniteResponsePreflight")
    return {
        "preflight_schema_version": preflight.preflight_schema_version,
        "parent_freeze_sha": preflight.parent_freeze_sha,
        "scenario_id": preflight.scenario_id,
        "scenario_sha": preflight.scenario_sha,
        "scenario_recipe_sha": preflight.scenario_recipe_sha,
        "bundle_sha": preflight.bundle_sha,
        "selected_fejer_order": preflight.selected_fejer_order,
        "finite_graph_formula_id": preflight.finite_graph_formula_id,
        "fejer_opposite_phase_leakage": (
            preflight.fejer_opposite_phase_leakage
        ),
        "raw_undressed_response_sha": preflight.raw_undressed_response.tensor_sha,
        "raw_dressed_response_sha": preflight.raw_dressed_response.tensor_sha,
        "undressed_active_singular_values": list(
            preflight.undressed_active_singular_values
        ),
        "dressed_active_singular_values": list(
            preflight.dressed_active_singular_values
        ),
        "undressed_graph_singular_values": list(
            preflight.undressed_graph_singular_values
        ),
        "dressed_graph_singular_values": list(
            preflight.dressed_graph_singular_values
        ),
        "expected_undressed_graph_singular_values": list(
            preflight.expected_undressed_graph_singular_values
        ),
        "expected_dressed_graph_singular_values": list(
            preflight.expected_dressed_graph_singular_values
        ),
        "undressed_physical_block_singular_values": list(
            preflight.undressed_physical_block_singular_values
        ),
        "dressed_physical_block_singular_values": list(
            preflight.dressed_physical_block_singular_values
        ),
        "expected_undressed_physical_block_singular_values": list(
            preflight.expected_undressed_physical_block_singular_values
        ),
        "expected_dressed_physical_block_singular_values": list(
            preflight.expected_dressed_physical_block_singular_values
        ),
        "undressed_g_spectrum": list(preflight.undressed_g_spectrum),
        "dressed_g_spectrum": list(preflight.dressed_g_spectrum),
        "undressed_c_spectrum": list(preflight.undressed_c_spectrum),
        "dressed_c_spectrum": list(preflight.dressed_c_spectrum),
        "graph_prediction_residual": preflight.graph_prediction_residual,
        "undressed_physical_block_prediction_residual": (
            preflight.undressed_physical_block_prediction_residual
        ),
        "dressed_physical_block_prediction_residual": (
            preflight.dressed_physical_block_prediction_residual
        ),
        "coverage_spectrum_drift": preflight.coverage_spectrum_drift,
        "integration_state": preflight.integration_state,
    }


def _validate_c17_finite_response_preflight(
    preflight: C17FiniteResponsePreflight,
) -> None:
    _exact_record(preflight, C17FiniteResponsePreflight, "C17 preflight")
    for tensor in (
        preflight.raw_undressed_response,
        preflight.raw_dressed_response,
    ):
        _exact_record(tensor, FrozenComplexTensor, "C17 raw response tensor")
        verify_frozen_tensor(tensor)
        if frozen_tensor_array(tensor).shape != (8, 2):
            raise ValueError("C17 raw response shape is not frozen")
    if preflight.preflight_sha != canonical_sha(
        c17_finite_response_preflight_payload(preflight)
    ):
        raise ValueError("C17 finite-response preflight SHA does not match its body")


def _validate_geometry_scenario_operator_bundle_template(
    bundle: GeometryScenarioOperatorBundleTemplate,
) -> None:
    _exact_record(
        bundle,
        GeometryScenarioOperatorBundleTemplate,
        "scenario geometry bundle",
    )
    tensors = (
        bundle.kernel_basis,
        bundle.physical_quotient_map,
        bundle.physical_quotient_metric,
        bundle.target_physical_representatives,
        bundle.undressed_response_representatives,
        bundle.dressed_response_representatives,
        bundle.gauge_basis,
    )
    for tensor in tensors:
        if tensor is not None:
            _exact_record(tensor, FrozenComplexTensor, "scenario bundle tensor")
            verify_frozen_tensor(tensor)
    kernel = frozen_tensor_array(bundle.kernel_basis)
    quotient = frozen_tensor_array(bundle.physical_quotient_map)
    metric = frozen_tensor_array(bundle.physical_quotient_metric)
    targets = frozen_tensor_array(bundle.target_physical_representatives)
    if kernel.ndim != 2 or kernel.shape[0] != bundle.observer_dimension:
        raise ValueError("scenario geometry kernel shape is not frozen")
    if quotient.ndim != 2 or quotient.shape[1] != bundle.observer_dimension:
        raise ValueError("scenario geometry quotient shape is not frozen")
    if metric.shape != (quotient.shape[0], quotient.shape[0]):
        raise ValueError("scenario geometry metric shape is not frozen")
    if targets.ndim != 2 or targets.shape[0] != bundle.observer_dimension:
        raise ValueError("scenario geometry target shape is not frozen")
    if bundle.scenario_id in C16_GEOMETRY_SCENARIO_IDS:
        if (
            bundle.control_case_id != "C16_COVERAGE_025_075"
            or bundle.coverage_control not in (0.25, 0.75)
            or bundle.gauge_amplitude is not None
            or bundle.gauge_basis is not None
            or bundle.gauge_graph_singular_values != ()
            or bundle.finite_graph_formula_id is not None
            or bundle.fejer_opposite_phase_leakage is not None
            or bundle.expected_undressed_finite_graph_singular_values != ()
            or bundle.expected_dressed_finite_graph_singular_values != ()
            or bundle.undressed_response_representatives is not None
            or bundle.dressed_response_representatives is not None
            or targets.shape != (8, 1)
        ):
            raise ValueError("C16 scenario geometry semantics are not frozen")
        if abs(float(np.linalg.norm(targets)) - 1.0) > 1.0e-12:
            raise ValueError("C16 target representative is not normalized")
    else:
        undressed_tensor = bundle.undressed_response_representatives
        dressed_tensor = bundle.dressed_response_representatives
        gauge_tensor = bundle.gauge_basis
        if (
            bundle.control_case_id != "C17_QUOTIENT_GAUGE_COVERAGE"
            or bundle.coverage_control is not None
            or bundle.gauge_amplitude != 8.0
            or undressed_tensor is None
            or dressed_tensor is None
            or gauge_tensor is None
            or len(bundle.gauge_graph_singular_values) != 2
            or bundle.finite_graph_formula_id
            != "c17-fejer-shared-U-actual-a-ablated-a-over-Tplus1-v1"
            or bundle.fejer_opposite_phase_leakage is None
            or len(bundle.expected_undressed_finite_graph_singular_values) != 2
            or len(bundle.expected_dressed_finite_graph_singular_values) != 2
        ):
            raise ValueError("C17 scenario geometry semantics are not frozen")
        undressed = frozen_tensor_array(undressed_tensor)
        dressed = frozen_tensor_array(dressed_tensor)
        gauge = frozen_tensor_array(gauge_tensor)
        if (
            undressed.shape != (8, 2)
            or dressed.shape != (8, 2)
            or targets.shape != (8, 2)
        ):
            raise ValueError("C17 response/target representative shapes are not frozen")
        if gauge.shape != (8, 2):
            raise ValueError("C17 gauge basis shape is not frozen")
        identity_two = np.eye(2, dtype=np.complex128)
        if max(
            np.linalg.norm(undressed.conj().T @ undressed - identity_two, ord=2),
            np.linalg.norm(dressed.conj().T @ dressed - identity_two, ord=2),
            np.linalg.norm(gauge.conj().T @ gauge - identity_two, ord=2),
            np.linalg.norm(undressed.conj().T @ gauge, ord=2),
        ) > 1.0e-12:
            raise ValueError("C17 T/U/G frames are not orthonormal")
        graph_normalizer = math.sqrt(1.0 + bundle.gauge_amplitude**2)
        expected_dressed = (
            undressed + bundle.gauge_amplitude * gauge
        ) / graph_normalizer
        if np.linalg.norm(dressed - expected_dressed, ord=2) > 1.0e-12:
            raise ValueError("C17 dressed response does not contain its gauge tensor")
        physical_block = undressed.conj().T @ dressed
        if float(np.min(np.linalg.svd(physical_block, compute_uv=False))) <= 1.0e-12:
            raise ValueError("C17 analytic physical graph block is singular")
        analytic_graph = (gauge.conj().T @ dressed) @ np.linalg.inv(
            physical_block
        )
        replayed_graph_singular_values = tuple(
            float(value)
            for value in np.linalg.svd(analytic_graph, compute_uv=False)
        )
        if max(
            abs(observed - expected)
            for observed, expected in zip(
                replayed_graph_singular_values,
                bundle.gauge_graph_singular_values,
            )
        ) > 1.0e-12 or max(
            abs(value - bundle.gauge_amplitude)
            for value in replayed_graph_singular_values
        ) > 1.0e-12:
            raise ValueError("C17 normalized graph slopes do not equal amplitude")
        if np.linalg.norm(quotient @ gauge, ord=2) > 1.0e-12:
            raise ValueError("C17 gauge direction survives the physical quotient")
        quotient_projector = quotient.conj().T @ quotient
        if np.linalg.norm(
            quotient_projector @ undressed - undressed,
            ord=2,
        ) > 1.0e-12:
            raise ValueError("C17 quotient does not retain the physical target")
        kernel_gram = kernel.conj().T @ kernel
        if np.linalg.norm(
            kernel_gram - np.eye(kernel.shape[1], dtype=np.complex128),
            ord=2,
        ) > 1.0e-12:
            raise ValueError("C17 TT-plus-gauge kernel is not orthonormal")
        if np.linalg.norm(
            kernel - np.column_stack((undressed, gauge)),
            ord=2,
        ) > 1.0e-12:
            raise ValueError("C17 kernel does not equal TT plus Gauge")
        mapped_physical = quotient @ undressed
        mapped_targets = quotient @ targets
        if max(
            np.linalg.norm(
                mapped_physical.conj().T @ mapped_physical - identity_two,
                ord=2,
            ),
            np.linalg.norm(
                mapped_targets.conj().T @ mapped_targets - identity_two,
                ord=2,
            ),
        ) > 1.0e-12:
            raise ValueError("C17 quotient response/target frames are not normalized")
        target_overlap = mapped_physical.conj().T @ mapped_targets
        analytic_coverage = np.linalg.eigvalsh(
            target_overlap.conj().T @ target_overlap
        )
        if np.linalg.norm(
            analytic_coverage - np.asarray((0.25, 0.75)),
            ord=2,
        ) > 1.0e-12:
            raise ValueError("C17 shared target coverage is not 0.25/0.75")
        if np.linalg.norm(
            metric - np.eye(metric.shape[0], dtype=np.complex128),
            ord=2,
        ) > 1.0e-12:
            raise ValueError("C17 physical quotient metric is not identity")
        expected_leakage = 1.0 / float(bundle.selected_fejer_order + 1)
        expected_undressed_slope = (
            bundle.gauge_amplitude * expected_leakage
        )
        if (
            abs(bundle.fejer_opposite_phase_leakage - expected_leakage)
            > 1.0e-15
            or max(
                abs(value - expected_undressed_slope)
                for value in (
                    bundle.expected_undressed_finite_graph_singular_values
                )
            )
            > 1.0e-12
            or max(
                abs(value - bundle.gauge_amplitude)
                for value in (
                    bundle.expected_dressed_finite_graph_singular_values
                )
            )
            > 1.0e-12
        ):
            raise ValueError("C17 finite-T graph prediction does not replay")
    if bundle.bundle_sha != canonical_sha(
        geometry_scenario_operator_bundle_template_payload(bundle)
    ):
        raise ValueError("scenario geometry bundle SHA does not match its body")


def geometry_operator_bundle_template_payload(
    bundle: GeometryOperatorBundleTemplate,
) -> dict[str, object]:
    if type(bundle) is not GeometryOperatorBundleTemplate:
        raise TypeError(
            "bundle must be an exact GeometryOperatorBundleTemplate"
        )
    return {
        "bundle_schema_version": bundle.bundle_schema_version,
        "parent_freeze_sha": bundle.parent_freeze_sha,
        "application_spec_sha": bundle.application_spec_sha,
        "scenario_recipe_shas": list(bundle.scenario_recipe_shas),
        "construction_rule_id": bundle.construction_rule_id,
        "selected_fejer_order": bundle.selected_fejer_order,
        "observer_dimension": bundle.observer_dimension,
        "kernel_basis_sha": bundle.kernel_basis.tensor_sha,
        "physical_quotient_map_sha": bundle.physical_quotient_map.tensor_sha,
        "physical_quotient_metric_sha": (
            bundle.physical_quotient_metric.tensor_sha
        ),
        "target_physical_representatives_sha": (
            bundle.target_physical_representatives.tensor_sha
        ),
        "integration_state": bundle.integration_state,
    }


def _validate_geometry_operator_bundle_template(
    bundle: GeometryOperatorBundleTemplate,
) -> None:
    _exact_record(bundle, GeometryOperatorBundleTemplate, "bundle")
    for tensor in (
        bundle.kernel_basis,
        bundle.physical_quotient_map,
        bundle.physical_quotient_metric,
        bundle.target_physical_representatives,
    ):
        _exact_record(tensor, FrozenComplexTensor, "bundle tensor")
        verify_frozen_tensor(tensor)
    if bundle.bundle_sha != canonical_sha(
        geometry_operator_bundle_template_payload(bundle)
    ):
        raise ValueError("geometry operator bundle SHA does not match its body")


def _find_application_and_scenario(
    parent: VerifiedParentFreeze,
    scenario_id: str,
) -> tuple[
    V3M0SyntheticControlApplicationSpec,
    ApplicationScenarioExecutionSpec,
]:
    manifest = _reverify_verified_parent_freeze(parent)
    identifier = _text(scenario_id, "scenario_id")
    matches = tuple(
        (application, scenario)
        for application in manifest.synthetic_control_application_specs
        for scenario in application.scenario_execution_specs
        if scenario.scenario_id == identifier
    )
    if len(matches) != 1:
        raise ValueError("scenario_id is not uniquely parent-frozen")
    application, scenario = matches[0]
    verify_synthetic_control_application_spec(application)
    if (
        application.control_case_id not in _CONTROL_CASES
        or identifier not in GEOMETRY_APPLICATION_SCENARIO_IDS
        or scenario.execution_lane != "BLOCK_SUCCESS"
        or scenario.expected_terminal_stage != "success"
        or scenario.expected_undefined_reason is not None
        or scenario.expected_artifact_type != "VerifiedResponseBlock"
    ):
        raise ValueError("scenario is not a registered geometry BLOCK_SUCCESS lane")
    return application, scenario


def _parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> object:
    matches = tuple(value for key, value in operation.parameters if key == name)
    if len(matches) != 1:
        raise ValueError(f"operation parameter {name!r} is not unique")
    return matches[0]


def _fp64_parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> float:
    import struct

    wire = _parameter(operation, name)
    if wire.value_kind != "fp64-bits" or wire.fp64_bits_value is None:
        raise TypeError(f"{name} must be an fp64 wire")
    return struct.unpack(">d", struct.pack(">Q", wire.fp64_bits_value))[0]


def _integer_parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> int:
    wire = _parameter(operation, name)
    if wire.value_kind != "integer" or wire.integer_value is None:
        raise TypeError(f"{name} must be an integer wire")
    return wire.integer_value


def _text_parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> str:
    wire = _parameter(operation, name)
    if wire.value_kind != "text" or wire.text_value is None:
        raise TypeError(f"{name} must be a text wire")
    return wire.text_value


@dataclass(frozen=True)
class _C18OperationContract:
    actual_source_axis: int
    independent_source_axis: int
    new_axis_amplitude: float
    observer: str


def _extract_c18_operation_contract(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> _C18OperationContract:
    verify_synthetic_control_application_spec(application)

    def unique_operation(local_id: str) -> SyntheticApplicationOperation:
        identifier = f"{application.application_instance_id}.{local_id}"
        matches = tuple(
            operation
            for operation in application.operations
            if operation.operation_instance_id == identifier
        )
        if len(matches) != 1:
            raise ValueError("C18 operation is not Parent-unique")
        return matches[0]

    actual_domain = unique_operation("00-actual-source-domain")
    independent_axis = unique_operation("01-ablated-new-source-axis")
    observer_operation = unique_operation("02-unary-geometry-sigma")
    if (
        actual_domain.operation_kind != "identity-v1"
        or actual_domain.input_operation_instance_ids
        or tuple(name for name, _ in actual_domain.parameters)
        != ("source-axis",)
    ):
        raise ValueError("C18 actual source operation is not frozen")
    if (
        independent_axis.operation_kind != "source-linear-mix-v1"
        or independent_axis.input_operation_instance_ids
        != (actual_domain.operation_instance_id,)
        or tuple(name for name, _ in independent_axis.parameters)
        != ("independent-source-axis", "new-axis-amplitude")
    ):
        raise ValueError("C18 independent source dependency is not frozen")
    if (
        observer_operation.operation_kind != "geometry-subspace-v1"
        or observer_operation.input_operation_instance_ids
        != (
            actual_domain.operation_instance_id,
            independent_axis.operation_instance_id,
        )
        or tuple(name for name, _ in observer_operation.parameters)
        != ("observer",)
        or scenario.operation_output_ids
        != (observer_operation.operation_instance_id,)
    ):
        raise ValueError("C18 observer operation/output is not frozen")
    actual_axis = _integer_parameter(actual_domain, "source-axis")
    new_axis = _integer_parameter(
        independent_axis,
        "independent-source-axis",
    )
    amplitude = _fp64_parameter(independent_axis, "new-axis-amplitude")
    observer = _text_parameter(observer_operation, "observer")
    if (
        actual_axis != 0
        or new_axis != 1
        or actual_axis == new_axis
    ):
        raise ValueError("C18 source axes differ from the frozen q0/q1 selectors")
    if amplitude != 1.0:
        raise ValueError("C18 new-axis amplitude is not the frozen exact unit")
    if observer != "geometry-and-sigma":
        raise ValueError("C18 observer is not the frozen geometry-and-sigma pair")
    return _C18OperationContract(
        actual_source_axis=actual_axis,
        independent_source_axis=new_axis,
        new_axis_amplitude=amplitude,
        observer=observer,
    )


def _common_blind_steps(
    derivation_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    reciprocal = _reciprocal_swap_steps(
        "blind.geometry.reciprocal",
        derivation_effect_digest=derivation_digest,
    )
    return (
        *_two_mode_rotation_steps(
            -_COMMON_ALPHA,
            "blind.geometry.left.r-minus-alpha",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
        *_inverse_steps(
            reciprocal,
            "blind.geometry.left.reciprocal-inverse",
        ),
        *_two_mode_rotation_steps(
            -_COMMON_BETA,
            "blind.geometry.left.r-minus-beta",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
        *_canonical_pair_rotation_steps(
            0,
            math.pi / 2.0,
            "blind.geometry.carrier.mode0-positive",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
        *_canonical_pair_rotation_steps(
            1,
            -math.pi / 2.0,
            "blind.geometry.carrier.mode1-negative",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
        *_two_mode_rotation_steps(
            _COMMON_BETA,
            "blind.geometry.right.r-beta",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
        *reciprocal,
        *_two_mode_rotation_steps(
            _COMMON_ALPHA,
            "blind.geometry.right.r-alpha",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
    )


def _condition_common_carrier(
    blind: tuple[ApplicationLocalShearStep, ...],
    derivation_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    conditioned = _two_mode_rotation_steps(
        _COMMON_CONDITIONING_ANGLE,
        "conditioned.geometry.mix.forward",
        target_conditioned=True,
        derivation_effect_digest=derivation_digest,
    )
    inverse = _inverse_steps(
        conditioned,
        "conditioned.geometry.mix.inverse",
        target_conditioned=True,
    )
    return (*inverse, *blind, *conditioned)


def _c17_steps(
    derivation_digest: str,
    gauge_amplitude: float,
) -> tuple[
    tuple[ApplicationLocalShearStep, ...],
    tuple[ApplicationLocalShearStep, ...],
]:
    """Encode ``t + a*g`` as a unitary graph rotation with ``tan θ=a``."""

    if gauge_amplitude != 8.0:
        raise ValueError("C17 gauge amplitude is not the frozen value")
    blind = (
        *_canonical_pair_rotation_steps(
            0,
            math.pi / 2.0,
            "blind.c17.physical-positive",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
        *_canonical_pair_rotation_steps(
            1,
            -math.pi / 2.0,
            "blind.c17.gauge-negative",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
    )
    conditioned = _two_mode_rotation_steps(
        math.atan(gauge_amplitude),
        "conditioned.c17.quotient-gauge.forward",
        target_conditioned=True,
        derivation_effect_digest=derivation_digest,
    )
    inverse = _inverse_steps(
        conditioned,
        "conditioned.c17.quotient-gauge.inverse",
        target_conditioned=True,
    )
    return (*inverse, *blind, *conditioned), blind


def _c18_steps(
    derivation_digest: str,
    contract: _C18OperationContract,
) -> tuple[
    tuple[ApplicationLocalShearStep, ...],
    tuple[ApplicationLocalShearStep, ...],
]:
    quarter_turn = contract.new_axis_amplitude * math.pi / 2.0
    blind = (
        *_canonical_pair_rotation_steps(
            contract.actual_source_axis,
            quarter_turn,
            f"blind.c18.mode{contract.actual_source_axis}-quarter-turn",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
        *_canonical_pair_rotation_steps(
            contract.independent_source_axis,
            quarter_turn,
            (
                "blind.c18."
                f"mode{contract.independent_source_axis}-quarter-turn"
            ),
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
    )
    conditioned = _canonical_pair_rotation_steps(
        contract.independent_source_axis,
        -quarter_turn,
        (
            "conditioned.c18."
            f"mode{contract.independent_source_axis}-cancel-quarter-turn"
        ),
        target_conditioned=True,
        derivation_effect_digest=derivation_digest,
    )
    return (*blind, *conditioned), blind


def _c19_steps(
    derivation_digest: str,
) -> tuple[
    tuple[ApplicationLocalShearStep, ...],
    tuple[ApplicationLocalShearStep, ...],
]:
    blind = (
        *_canonical_pair_rotation_steps(
            0,
            math.pi / 2.0,
            "blind.c19.mode0-full-positive",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
        *_canonical_pair_rotation_steps(
            1,
            math.pi / 2.0,
            "blind.c19.mode1-full-positive",
            target_conditioned=False,
            derivation_effect_digest=derivation_digest,
        ),
    )
    tooth = (
        *_canonical_pair_rotation_steps(
            0,
            _C19_PHASE_TOOTH,
            "conditioned.c19.mode0-phase-tooth",
            target_conditioned=True,
            derivation_effect_digest=derivation_digest,
        ),
        *_canonical_pair_rotation_steps(
            1,
            _C19_PHASE_TOOTH,
            "conditioned.c19.mode1-phase-tooth",
            target_conditioned=True,
            derivation_effect_digest=derivation_digest,
        ),
    )
    return (*blind, *tooth), blind


def _symbol_from_steps(
    steps: tuple[ApplicationLocalShearStep, ...],
    momentum: float,
) -> np.ndarray:
    matrix = np.eye(4, dtype=np.complex128)
    for step in steps:
        shear = np.eye(4, dtype=np.complex128)
        phase = complex(
            math.cos(momentum * step.offset[0]),
            math.sin(momentum * step.offset[0]),
        )
        source = _CHANNEL_INDEX[step.source_channel]
        destination = _CHANNEL_INDEX[step.destination_channel]
        shear[destination, source] += step.coefficient * phase
        matrix = shear @ matrix
    return matrix


def _positive_projector(matrix: np.ndarray) -> np.ndarray:
    projector = (np.eye(4, dtype=np.complex128) - 1.0j * matrix) / 2.0
    projector = (projector + projector.conj().T) / 2.0
    if (
        np.linalg.norm(projector @ projector - projector, ord=2) > 2.0e-12
        or abs(np.trace(projector).real - 2.0) > 2.0e-12
    ):
        raise ValueError("analytic positive-frequency projector is invalid")
    return projector


def _canonical_projector_columns(
    projector: np.ndarray,
    rank: int,
) -> np.ndarray:
    columns: list[np.ndarray] = []
    for anchor in np.eye(projector.shape[0], dtype=np.complex128).T:
        vector = projector @ anchor
        for prior in columns:
            vector -= prior * np.vdot(prior, vector)
        norm = float(np.linalg.norm(vector))
        if norm <= 1.0e-10:
            continue
        vector /= norm
        pivot = int(np.argmax(np.abs(vector)))
        vector *= np.exp(-1.0j * np.angle(vector[pivot]))
        columns.append(vector)
        if len(columns) == rank:
            break
    if len(columns) != rank:
        raise ValueError("projector did not yield the requested canonical rank")
    result = np.column_stack(columns)
    if np.linalg.norm(result.conj().T @ result - np.eye(rank), ord=2) > 1.0e-12:
        raise ValueError("canonical projector columns are not orthonormal")
    return result


def _common_semantic_basis(
    blind_steps: tuple[ApplicationLocalShearStep, ...],
) -> np.ndarray:
    projectors = tuple(
        _positive_projector(_symbol_from_steps(blind_steps, momentum))
        for momentum in _COMMON_MOMENTA
    )
    aggregate = projectors[0] + projectors[1]
    eigenvalues = np.linalg.eigvalsh(aggregate)
    lower = float(eigenvalues[0])
    upper = float(eigenvalues[-1])
    if upper - lower <= 0.5:
        raise ValueError("common shell aggregate has no semantic split")
    top_projector = (
        aggregate - lower * np.eye(4, dtype=np.complex128)
    ) / (upper - lower)
    top_projector = (top_projector + top_projector.conj().T) / 2.0
    bottom_projector = np.eye(4, dtype=np.complex128) - top_projector
    tt = _canonical_projector_columns(top_projector, 2)
    gauge_row = _canonical_projector_columns(bottom_projector, 2)
    result = np.column_stack((tt, gauge_row))
    if np.linalg.norm(result.conj().T @ result - np.eye(4), ord=2) > 2.0e-12:
        raise ValueError("semantic source basis is not orthonormal")
    return result


def _source_and_sectors(
    scenario_id: str,
    actual_steps: tuple[ApplicationLocalShearStep, ...],
    blind_steps: tuple[ApplicationLocalShearStep, ...],
    c18_contract: Optional[_C18OperationContract] = None,
) -> tuple[np.ndarray, tuple[str, ...]]:
    if scenario_id in C17_GEOMETRY_SCENARIO_IDS:
        dressed_positive = _canonical_projector_columns(
            _positive_projector(_symbol_from_steps(actual_steps, 0.0)),
            2,
        )
        return dressed_positive, (
            "dressed-coverage-probe-0",
            "dressed-coverage-probe-1",
        )
    if scenario_id in (
        *C15_GEOMETRY_SCENARIO_IDS,
        *C16_GEOMETRY_SCENARIO_IDS,
    ):
        semantic = _common_semantic_basis(blind_steps)
        if scenario_id == C15_GEOMETRY_SCENARIO_IDS[0]:
            return semantic, ("TT0", "TT1", "Gauge", "Row")
        if scenario_id == C15_GEOMETRY_SCENARIO_IDS[1]:
            return semantic[:, :1], ("TT0",)
        if scenario_id == C15_GEOMETRY_SCENARIO_IDS[2]:
            return semantic[:, :2], ("TT0", "TT1")
        if scenario_id == C15_GEOMETRY_SCENARIO_IDS[3]:
            return semantic[:, (0, 1, 3)], ("TT0", "TT1", "Row")
        if scenario_id in C16_GEOMETRY_SCENARIO_IDS:
            return semantic[:, :1], ("coverage-probe",)
        raise AssertionError("unreachable C15/C16 geometry source scenario")
    if scenario_id in C18_GEOMETRY_SCENARIO_IDS:
        if c18_contract is None:
            raise ValueError("C18 source selector lacks its Parent operation contract")
        source_indices = (
            2 * c18_contract.actual_source_axis,
            2 * c18_contract.independent_source_axis,
        )
        return (
            np.eye(4, dtype=np.complex128)[:, source_indices],
            (
                f"actual-source-q{c18_contract.actual_source_axis}",
                (
                    "matched-new-source-"
                    f"q{c18_contract.independent_source_axis}"
                ),
            ),
        )
    if c18_contract is not None:
        raise ValueError("non-C18 geometry recipe received a C18 contract")
    # C19 shifts the two positive phases by the same tiny amount.  The
    # eigenspace is unchanged, while ``(I-iM)/2`` is a projector only at the
    # unshifted quarter turn; derive the source from that exact blind carrier.
    positive = _canonical_projector_columns(
        _positive_projector(_symbol_from_steps(blind_steps, 0.0)),
        2,
    )
    return positive, ("full-positive-0", "full-positive-1")


def _coverage_and_gauge(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> tuple[Optional[float], Optional[float]]:
    operation_by_id = {
        operation.operation_instance_id: operation
        for operation in application.operations
    }
    output = operation_by_id[scenario.operation_output_ids[0]]
    if scenario.scenario_id in C16_GEOMETRY_SCENARIO_IDS:
        return _fp64_parameter(
            output,
            "coverage-squared-correlation",
        ), None
    if scenario.scenario_id in C17_GEOMETRY_SCENARIO_IDS:
        dressing = next(
            operation
            for operation in application.operations
            if operation.operation_instance_id.endswith("01-gauge-dressing")
        )
        return None, _fp64_parameter(dressing, "gauge-amplitude")
    return None, None


def build_geometry_application_recipe(
    parent: VerifiedParentFreeze,
    scenario_id: str,
) -> GeometryApplicationRecipeArtifact:
    """Compile one exact C15--C19 scenario to a pre-permit local recipe."""

    application, scenario = _find_application_and_scenario(parent, scenario_id)
    dag_sha = _scenario_dag_sha(application, scenario)
    coverage_control, gauge_amplitude = _coverage_and_gauge(
        application,
        scenario,
    )
    c18_contract: Optional[_C18OperationContract] = None
    if scenario.scenario_id in C18_GEOMETRY_SCENARIO_IDS:
        c18_contract = _extract_c18_operation_contract(
            application,
            scenario,
        )
        actual_steps, blind_steps = _c18_steps(dag_sha, c18_contract)
        rule_id = "c18-on-site-actual-rank1-matched-rank2-v1"
    elif scenario.scenario_id in C19_GEOMETRY_SCENARIO_IDS:
        actual_steps, blind_steps = _c19_steps(dag_sha)
        rule_id = "rank-two-full-positive-observer-collapse-v1"
    elif scenario.scenario_id in C17_GEOMETRY_SCENARIO_IDS:
        if gauge_amplitude is None:
            raise ValueError("C17 gauge amplitude is absent from its Parent DAG")
        actual_steps, blind_steps = _c17_steps(dag_sha, gauge_amplitude)
        rule_id = "rank-two-quotient-gauge-graph-carrier-v1"
    else:
        blind_steps = _common_blind_steps(dag_sha)
        actual_steps = _condition_common_carrier(blind_steps, dag_sha)
        rule_id = "rank-two-two-k-geometry-carrier-v1"
    source_values, semantic_sectors = _source_and_sectors(
        scenario.scenario_id,
        actual_steps,
        blind_steps,
        c18_contract,
    )
    source_manifest = application.basis_protocol.source_basis
    readout_manifest = application.basis_protocol.readout_basis
    if (
        source_manifest.state_schema_id != readout_manifest.state_schema_id
        or source_manifest.channel_order != _CHANNEL_ORDER
        or readout_manifest.channel_order != _CHANNEL_ORDER
    ):
        raise ValueError("geometry application basis interface is not frozen")
    grid = application.grid_protocol
    if (
        grid.spatial_ndim != 1
        or grid.spatial_shape != (8,)
        or grid.response_torus_denominators != (8,)
        or grid.response_reciprocal_indices != ((1,), (2,))
        or len(grid.preregistered_phase_bands) != 1
    ):
        raise ValueError("geometry application grid differs from its recipe")
    if (
        scenario.scenario_id in C18_GEOMETRY_SCENARIO_IDS
        and grid.expected_shell_rank != 1
    ):
        raise ValueError("C18 Parent expected shell rank is not one")
    ablated_steps = tuple(
        step for step in actual_steps if not step.target_conditioned
    )
    if ablated_steps != blind_steps:
        raise AssertionError("geometry matched ablation changed a blind slot")
    provisional = GeometryApplicationRecipeArtifact(
        recipe_schema_version=GEOMETRY_APPLICATION_RECIPE_SCHEMA_VERSION,
        control_case_id=application.control_case_id,
        scenario_id=scenario.scenario_id,
        application_spec_sha=application.application_spec_sha,
        scenario_sha=scenario.scenario_sha,
        operation_dag_sha=dag_sha,
        recipe_id=scenario.execution_recipe_id,
        construction_rule_id=rule_id,
        state_schema_id=source_manifest.state_schema_id,
        channel_order=_CHANNEL_ORDER,
        spatial_ndim=1,
        response_torus_denominator=8,
        response_reciprocal_indices=((1,), (2,)),
        reference_phase_bands=grid.preregistered_phase_bands,
        expected_shell_rank=(
            1 if scenario.scenario_id in C18_GEOMETRY_SCENARIO_IDS else 2
        ),
        primitive_support_radius=(
            0 if scenario.scenario_id in C18_GEOMETRY_SCENARIO_IDS else 1
        ),
        semantic_sector_names=semantic_sectors,
        actual_steps=actual_steps,
        matched_ablated_steps=ablated_steps,
        source_injection=freeze_complex_tensor(source_values),
        readout=freeze_complex_tensor(
            np.eye(4, dtype=np.complex128)[
                (
                    2 * c18_contract.actual_source_axis + 1,
                    2 * c18_contract.independent_source_axis + 1,
                ),
                :,
            ]
            if scenario.scenario_id in C18_GEOMETRY_SCENARIO_IDS
            else np.eye(4, dtype=np.complex128)
        ),
        coverage_control=coverage_control,
        gauge_amplitude=gauge_amplitude,
        observer_collapse_expected=(
            scenario.scenario_id in C19_GEOMETRY_SCENARIO_IDS
        ),
        actual_effect_digest=_executed_effect_digest(actual_steps, "actual"),
        matched_ablated_effect_digest=_executed_effect_digest(
            actual_steps,
            "matched_ablated",
        ),
        integration_state=GEOMETRY_APPLICATION_INTEGRATION_STATE,
        recipe_sha="0" * 64,
    )
    recipe = replace(
        provisional,
        recipe_sha=canonical_sha(
            geometry_application_recipe_payload(provisional)
        ),
    )
    _validate_recipe(recipe)
    return recipe


def _validate_recipe(recipe: GeometryApplicationRecipeArtifact) -> None:
    _exact_record(recipe, GeometryApplicationRecipeArtifact, "geometry recipe")
    for step in recipe.actual_steps:
        _exact_record(step, ApplicationLocalShearStep, "geometry shear step")
        if step.step_sha != canonical_sha(application_local_shear_step_payload(step)):
            raise ValueError("geometry shear step SHA does not match its body")
    for field in ("source_injection", "readout"):
        tensor = getattr(recipe, field)
        _exact_record(tensor, FrozenComplexTensor, field)
        verify_frozen_tensor(tensor)
    if recipe.actual_effect_digest != _executed_effect_digest(
        recipe.actual_steps,
        "actual",
    ):
        raise ValueError("geometry actual effect digest does not replay")
    if recipe.matched_ablated_effect_digest != _executed_effect_digest(
        recipe.actual_steps,
        "matched_ablated",
    ):
        raise ValueError("geometry ablated effect digest does not replay")
    if recipe.recipe_sha != canonical_sha(
        geometry_application_recipe_payload(recipe)
    ):
        raise ValueError("geometry recipe SHA does not match its complete body")


def verify_geometry_application_recipe(
    parent: VerifiedParentFreeze,
    recipe: GeometryApplicationRecipeArtifact,
) -> GeometryApplicationRecipeArtifact:
    """Replay a raw pre-permit recipe against the live ParentFreeze."""

    _validate_recipe(recipe)
    expected = build_geometry_application_recipe(parent, recipe.scenario_id)
    if recipe != expected:
        raise ValueError("geometry recipe differs from the live parent compilation")
    return recipe


def geometry_application_recipe_symbol(
    recipe: GeometryApplicationRecipeArtifact,
    momentum: float,
    branch: Literal["actual", "matched_ablated"],
) -> np.ndarray:
    """Evaluate the exact ordered local-shear program as a Laurent symbol."""

    _validate_recipe(recipe)
    if type(momentum) is not float or not math.isfinite(momentum):
        raise TypeError("momentum must be finite fp64")
    if branch == "actual":
        steps = recipe.actual_steps
    elif branch == "matched_ablated":
        steps = recipe.matched_ablated_steps
    else:
        raise ValueError("geometry recipe branch is not registered")
    return _symbol_from_steps(steps, momentum)


def build_geometry_recipe_trace_and_operators(
    parent: VerifiedParentFreeze,
    recipe: GeometryApplicationRecipeArtifact,
    *,
    target_spec_id: str,
    interface: PrimitiveInterface,
) -> tuple[ConstructionTrace, tuple[PrimitiveOperatorWire, ...]]:
    """Translate a replayed geometry recipe to the existing factory wires.

    Execution order is carried only by the returned tuple and its layer slots.
    Primitive DAG edges remain empty: adding sequential dependency edges would
    incorrectly taint blind factors to the right of a conditioned factor.
    """

    verified = verify_geometry_application_recipe(parent, recipe)
    target_id = _text(target_spec_id, "target_spec_id")
    if type(interface) is not PrimitiveInterface:
        raise TypeError("interface must be an exact PrimitiveInterface")
    if (
        interface.state_schema_id != verified.state_schema_id
        or interface.spatial_ndim != verified.spatial_ndim
        or interface.channel_order != verified.channel_order
        or interface.dtype != "complex128"
        or interface.backend != "numpy"
    ):
        raise ValueError("factory interface differs from the geometry recipe")
    application, scenario = _find_application_and_scenario(
        parent,
        verified.scenario_id,
    )
    closure = _scenario_operation_closure(application, scenario)
    provenance = [
        ProvenanceNode(
            provenance_id=operation.operation_instance_id,
            operation=ProvenanceOperation.GRAMMAR_PRIMITIVE,
            depends_on=operation.input_operation_instance_ids,
            target_refs=(),
            objective_tags=(),
            search_run_id=None,
            source_sha=operation.operation_sha,
        )
        for operation in closure
    ]
    blind_provenance_id = f"{verified.scenario_id}.local-geometry-recipe"
    conditioned_provenance_id = (
        f"{verified.scenario_id}.target-conditioned-geometry"
    )
    provenance.extend(
        (
            ProvenanceNode(
                provenance_id=blind_provenance_id,
                operation=ProvenanceOperation.GRAMMAR_CONSTANT,
                depends_on=scenario.operation_output_ids,
                target_refs=(),
                objective_tags=(),
                search_run_id=None,
                source_sha=verified.recipe_sha,
            ),
            ProvenanceNode(
                provenance_id=conditioned_provenance_id,
                operation=ProvenanceOperation.TARGET_SPEC_READ,
                depends_on=(blind_provenance_id,),
                target_refs=(f"target:{target_id}",),
                objective_tags=(),
                search_run_id=None,
                source_sha=verified.scenario_sha,
            ),
        )
    )
    zero = (0,) * interface.spatial_ndim
    primitive_specs: list[PrimitiveSpec] = []
    operators: list[PrimitiveOperatorWire] = []
    for index, step in enumerate(verified.actual_steps):
        mechanism_id = f"{verified.scenario_id}.geometry-shear.{index:03d}"
        production_id = (
            "target_operator"
            if step.target_conditioned
            else "local_canonical_shear"
        )
        layer_slot_id = f"{verified.scenario_id}.geometry-layer.{index:03d}"
        primitive_specs.append(
            PrimitiveSpec(
                mechanism_id=mechanism_id,
                production_id=production_id,
                depends_on=(),
                support_offsets=tuple(sorted({zero, step.offset})),
                state_channels=tuple(
                    sorted((step.source_channel, step.destination_channel))
                ),
                coefficient_expression=sp.Rational(
                    *step.coefficient.as_integer_ratio()
                ),
                coefficient_variable_order=(),
                symbolic_origin_tags=(),
                neutral_ablation="neutral-identity-v1",
                design_objective_tags=(),
                search_run_id=None,
                source_sha=step.step_sha,
                design_provenance=(
                    conditioned_provenance_id
                    if step.target_conditioned
                    else blind_provenance_id
                ),
            )
        )
        operators.append(
            PrimitiveOperatorWire(
                mechanism_id=mechanism_id,
                production_id=production_id,
                layer_slot_id=layer_slot_id,
                operation_id="local_canonical_shear",
                interface_id=interface.interface_id,
                source_channel=step.source_channel,
                destination_channel=step.destination_channel,
                offset=step.offset,
                coefficient_wire=(step.coefficient, 0.0),
            )
        )
    trace = build_construction_trace(
        target_spec_id=target_id,
        provenance_nodes=tuple(provenance),
        primitive_specs=tuple(primitive_specs),
    )
    return trace, tuple(operators)


def _analytic_orthonormal_columns(
    matrix: np.ndarray,
    *,
    expected_rank: int,
) -> np.ndarray:
    """Canonical Gram--Schmidt for an analytic pre-response column family."""

    values = np.asarray(matrix, dtype=np.complex128)
    if values.ndim != 2 or expected_rank <= 0:
        raise ValueError("analytic semantic family has an invalid shape or rank")
    columns: list[np.ndarray] = []
    for source in values.T:
        vector = source.copy()
        # Re-orthogonalize once so the frozen fp64 residual is insensitive to
        # the ordering of nearly aligned analytic semantic representatives.
        for _ in range(2):
            for prior in columns:
                vector -= prior * np.vdot(prior, vector)
        norm = float(np.linalg.norm(vector))
        if norm <= 1.0e-10:
            continue
        vector /= norm
        pivot = int(np.argmax(np.abs(vector)))
        vector *= np.exp(-1.0j * np.angle(vector[pivot]))
        columns.append(vector)
        if len(columns) == expected_rank:
            break
    if len(columns) != expected_rank:
        raise ValueError("analytic semantic family has the wrong rank")
    result = np.column_stack(columns)
    if (
        np.linalg.norm(
            result.conj().T @ result - np.eye(expected_rank),
            ord=2,
        )
        > 2.0e-12
    ):
        raise ValueError("analytic semantic basis is not orthonormal")
    return np.asarray(result, dtype=np.complex128)


def build_c15_analytic_geometry_bundle(
    parent: VerifiedParentFreeze,
    selected_fejer_order: int,
) -> GeometryOperatorBundleTemplate:
    """Build the C15 comparison geometry before any finite response exists.

    The builder consumes only the live ParentFreeze, its exact four C15
    scenario DAGs, and the replayed analytic local-shear recipes.  In
    particular it never calls the finite-Fejer response path and never reads a
    transition, response block, candidate response SVD, or measured geometry.
    The returned object remains a pending pre-permit template, not authority.
    """

    if selected_fejer_order not in _CANDIDATE_FEJER_ORDERS:
        raise ValueError("analytic bundle Fejer order is not preregistered")
    recipes = {
        scenario_id: build_geometry_application_recipe(parent, scenario_id)
        for scenario_id in C15_GEOMETRY_SCENARIO_IDS
    }
    full_recipe = recipes[C15_GEOMETRY_SCENARIO_IDS[0]]
    semantic = frozen_tensor_array(full_recipe.source_injection)
    if semantic.shape != (4, 4) or full_recipe.semantic_sector_names != (
        "TT0",
        "TT1",
        "Gauge",
        "Row",
    ):
        raise ValueError("C15 analytic semantic source frame is not frozen")

    expected_source_columns = {
        C15_GEOMETRY_SCENARIO_IDS[0]: (0, 1, 2, 3),
        C15_GEOMETRY_SCENARIO_IDS[1]: (0,),
        C15_GEOMETRY_SCENARIO_IDS[2]: (0, 1),
        C15_GEOMETRY_SCENARIO_IDS[3]: (0, 1, 3),
    }
    for scenario_id, indices in expected_source_columns.items():
        observed = frozen_tensor_array(recipes[scenario_id].source_injection)
        expected = semantic[:, indices]
        if not np.array_equal(observed, expected):
            raise ValueError("C15 scenario source is not its frozen semantic slice")

    # ``(I-iM(k))/2`` is the exact rank-two positive-shell projector of this
    # analytic quarter-turn carrier.  Stacking its action on the frozen
    # semantic source frame defines observer representatives without invoking
    # finite-T filtering or decomposing a measured candidate response.
    analytic_shell_representatives = np.vstack(
        tuple(
            _positive_projector(
                _symbol_from_steps(full_recipe.actual_steps, momentum)
            )
            @ semantic
            for momentum in _COMMON_MOMENTA
        )
    )
    tt = _analytic_orthonormal_columns(
        analytic_shell_representatives[:, :2],
        expected_rank=2,
    )
    row_residual = analytic_shell_representatives[:, 3:4] - tt @ (
        tt.conj().T @ analytic_shell_representatives[:, 3:4]
    )
    row = _analytic_orthonormal_columns(row_residual, expected_rank=1)
    tt_row = np.column_stack((tt, row))
    gauge_residual = analytic_shell_representatives[:, 2:3] - tt_row @ (
        tt_row.conj().T @ analytic_shell_representatives[:, 2:3]
    )
    gauge = _analytic_orthonormal_columns(gauge_residual, expected_rank=1)

    manifest = _reverify_verified_parent_freeze(parent)
    provisional = GeometryOperatorBundleTemplate(
        bundle_schema_version=(
            GEOMETRY_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION
        ),
        parent_freeze_sha=manifest.parent_freeze_sha,
        application_spec_sha=full_recipe.application_spec_sha,
        scenario_recipe_shas=tuple(
            recipes[scenario_id].recipe_sha
            for scenario_id in C15_GEOMETRY_SCENARIO_IDS
        ),
        construction_rule_id="c15-analytic-shell-semantic-bundle-v1",
        selected_fejer_order=selected_fejer_order,
        observer_dimension=8,
        kernel_basis=freeze_complex_tensor(np.column_stack((tt, gauge))),
        physical_quotient_map=freeze_complex_tensor(tt_row.conj().T),
        physical_quotient_metric=freeze_complex_tensor(
            np.eye(3, dtype=np.complex128)
        ),
        target_physical_representatives=freeze_complex_tensor(tt),
        integration_state=GEOMETRY_APPLICATION_INTEGRATION_STATE,
        bundle_sha="0" * 64,
    )
    bundle = replace(
        provisional,
        bundle_sha=canonical_sha(
            geometry_operator_bundle_template_payload(provisional)
        ),
    )
    _validate_geometry_operator_bundle_template(bundle)
    return bundle


def verify_c15_analytic_geometry_bundle(
    parent: VerifiedParentFreeze,
    bundle: GeometryOperatorBundleTemplate,
) -> GeometryOperatorBundleTemplate:
    """Replay a pending analytic C15 bundle against the live ParentFreeze."""

    _validate_geometry_operator_bundle_template(bundle)
    if bundle.construction_rule_id != "c15-analytic-shell-semantic-bundle-v1":
        raise ValueError("bundle is not a C15 analytic geometry template")
    expected = build_c15_analytic_geometry_bundle(
        parent,
        bundle.selected_fejer_order,
    )
    if bundle != expected:
        raise ValueError("analytic geometry bundle differs from live replay")
    return bundle


def _issue_geometry_scenario_bundle(
    provisional: GeometryScenarioOperatorBundleTemplate,
) -> GeometryScenarioOperatorBundleTemplate:
    bundle = replace(
        provisional,
        bundle_sha=canonical_sha(
            geometry_scenario_operator_bundle_template_payload(provisional)
        ),
    )
    _validate_geometry_scenario_operator_bundle_template(bundle)
    return bundle


def build_c16_analytic_geometry_bundle(
    parent: VerifiedParentFreeze,
    scenario_id: str,
    selected_fejer_order: int,
) -> GeometryScenarioOperatorBundleTemplate:
    """Freeze one C16 coverage target before measuring its response."""

    if scenario_id not in C16_GEOMETRY_SCENARIO_IDS:
        raise ValueError("C16 analytic bundle requires a frozen C16 scenario")
    recipe = build_geometry_application_recipe(parent, scenario_id)
    coverage = recipe.coverage_control
    if coverage not in (0.25, 0.75):
        raise ValueError("C16 coverage control is not the frozen low/high pair")
    c15 = build_c15_analytic_geometry_bundle(parent, selected_fejer_order)
    physical_response = frozen_tensor_array(
        c15.target_physical_representatives
    )[:, 0]
    quotient = frozen_tensor_array(c15.physical_quotient_map)
    physical_complement = quotient.conj().T[:, 2]
    target = (
        math.sqrt(coverage) * physical_response
        + math.sqrt(1.0 - coverage) * physical_complement
    )[:, None]
    manifest = _reverify_verified_parent_freeze(parent)
    return _issue_geometry_scenario_bundle(
        GeometryScenarioOperatorBundleTemplate(
            bundle_schema_version=(
                GEOMETRY_SCENARIO_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION
            ),
            parent_freeze_sha=manifest.parent_freeze_sha,
            control_case_id=recipe.control_case_id,
            application_spec_sha=recipe.application_spec_sha,
            scenario_id=recipe.scenario_id,
            scenario_sha=recipe.scenario_sha,
            scenario_recipe_sha=recipe.recipe_sha,
            construction_rule_id="c16-analytic-coverage-orientation-bundle-v1",
            selected_fejer_order=selected_fejer_order,
            observer_dimension=8,
            kernel_basis=c15.kernel_basis,
            physical_quotient_map=c15.physical_quotient_map,
            physical_quotient_metric=c15.physical_quotient_metric,
            target_physical_representatives=freeze_complex_tensor(target),
            undressed_response_representatives=None,
            dressed_response_representatives=None,
            gauge_basis=None,
            gauge_graph_singular_values=(),
            finite_graph_formula_id=None,
            fejer_opposite_phase_leakage=None,
            expected_undressed_finite_graph_singular_values=(),
            expected_dressed_finite_graph_singular_values=(),
            coverage_control=coverage,
            gauge_amplitude=None,
            integration_state=GEOMETRY_APPLICATION_INTEGRATION_STATE,
            bundle_sha="0" * 64,
        )
    )


def verify_c16_analytic_geometry_bundle(
    parent: VerifiedParentFreeze,
    bundle: GeometryScenarioOperatorBundleTemplate,
) -> GeometryScenarioOperatorBundleTemplate:
    """Replay one pending C16 bundle against its live ParentFreeze."""

    _validate_geometry_scenario_operator_bundle_template(bundle)
    if (
        bundle.scenario_id not in C16_GEOMETRY_SCENARIO_IDS
        or bundle.construction_rule_id
        != "c16-analytic-coverage-orientation-bundle-v1"
    ):
        raise ValueError("bundle is not a C16 analytic geometry template")
    expected = build_c16_analytic_geometry_bundle(
        parent,
        bundle.scenario_id,
        bundle.selected_fejer_order,
    )
    if bundle != expected:
        raise ValueError("C16 analytic geometry bundle differs from live replay")
    return bundle


def build_c17_analytic_geometry_bundle(
    parent: VerifiedParentFreeze,
    selected_fejer_order: int,
) -> GeometryScenarioOperatorBundleTemplate:
    """Freeze the normalized ``t + 8g`` graph before finite response.

    A literal raw-response displacement by a unit gauge vector has norm eight
    and is impossible for the two-momentum stack of contraction-valued Fejer
    responses.  The Parent amplitude is therefore the projective graph slope:
    the local conditioned conjugation uses ``theta=atan(8)``, so its active
    shell and the shared source have the canonical representative
    ``(t + 8g)/sqrt(65)``.  The actual finite response therefore has graph
    slope eight, while the matched branch receives only the deterministic
    opposite-phase Fejer leakage ``8/(T+1)``.  All frames below come from
    analytic shell projectors, never a measured response.
    """

    recipe = build_geometry_application_recipe(
        parent,
        C17_GEOMETRY_SCENARIO_IDS[0],
    )
    if recipe.gauge_amplitude != 8.0:
        raise ValueError("C17 gauge amplitude is not the frozen value")
    if selected_fejer_order not in _CANDIDATE_FEJER_ORDERS:
        raise ValueError("C17 analytic bundle Fejer order is not preregistered")
    source = frozen_tensor_array(recipe.source_injection)
    undressed_projector_output = np.vstack(
        tuple(
            _positive_projector(
                _symbol_from_steps(recipe.matched_ablated_steps, momentum)
            )
            @ source
            for momentum in _COMMON_MOMENTA
        )
    )
    dressed_projector_output = np.vstack(
        tuple(
            _positive_projector(
                _symbol_from_steps(recipe.actual_steps, momentum)
            )
            @ source
            for momentum in _COMMON_MOMENTA
        )
    )
    undressed_response = _analytic_orthonormal_columns(
        undressed_projector_output,
        expected_rank=2,
    )
    dressed_unaligned = _analytic_orthonormal_columns(
        dressed_projector_output,
        expected_rank=2,
    )
    overlap = undressed_response.conj().T @ dressed_unaligned
    overlap_left, _, overlap_right = np.linalg.svd(
        overlap,
        full_matrices=False,
    )
    dressed_response = dressed_unaligned @ (
        overlap_right.conj().T @ overlap_left.conj().T
    )
    amplitude = recipe.gauge_amplitude
    graph_normalizer = math.sqrt(1.0 + amplitude**2)
    expected_cosine = 1.0 / graph_normalizer
    expected_sine = amplitude / graph_normalizer
    physical_coefficients = undressed_response.conj().T @ dressed_response
    if np.linalg.norm(
        physical_coefficients
        - expected_cosine * np.eye(2, dtype=np.complex128),
        ord=2,
    ) > 1.0e-12:
        raise ValueError("C17 analytic physical graph block is not frozen")
    gauge_residual = dressed_response - undressed_response @ physical_coefficients
    gauge_basis = gauge_residual / expected_sine
    if np.linalg.norm(
        gauge_basis.conj().T @ gauge_basis
        - np.eye(2, dtype=np.complex128),
        ord=2,
    ) > 1.0e-12 or np.linalg.norm(
        undressed_response.conj().T @ gauge_basis,
        ord=2,
    ) > 1.0e-12:
        raise ValueError("C17 analytic T/G graph frame is not orthonormal")
    expected_dressed = (
        undressed_response + amplitude * gauge_basis
    ) / graph_normalizer
    if np.linalg.norm(dressed_response - expected_dressed, ord=2) > 1.0e-12:
        raise ValueError("C17 analytic dressed graph does not replay")
    analytic_graph = (gauge_basis.conj().T @ dressed_response) @ np.linalg.inv(
        undressed_response.conj().T @ dressed_response
    )
    graph_slopes = tuple(
        float(value)
        for value in np.linalg.svd(analytic_graph, compute_uv=False)
    )
    if max(abs(value - amplitude) for value in graph_slopes) > 1.0e-12:
        raise ValueError("C17 analytic shell does not realize the Parent graph slope")
    physical_projector = (
        np.eye(8, dtype=np.complex128)
        - gauge_basis @ gauge_basis.conj().T
    )
    physical_frame = _analytic_orthonormal_columns(
        physical_projector,
        expected_rank=6,
    )
    quotient = physical_frame.conj().T
    physical_complement = _analytic_orthonormal_columns(
        physical_projector
        - undressed_response @ undressed_response.conj().T,
        expected_rank=2,
    )
    targets = np.column_stack(
        (
            0.5 * undressed_response[:, 0]
            + math.sqrt(0.75) * physical_complement[:, 0],
            math.sqrt(0.75) * undressed_response[:, 1]
            + 0.5 * physical_complement[:, 1],
        )
    )
    leakage = 1.0 / float(selected_fejer_order + 1)
    expected_undressed_finite_slope = amplitude * leakage
    manifest = _reverify_verified_parent_freeze(parent)
    return _issue_geometry_scenario_bundle(
        GeometryScenarioOperatorBundleTemplate(
            bundle_schema_version=(
                GEOMETRY_SCENARIO_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION
            ),
            parent_freeze_sha=manifest.parent_freeze_sha,
            control_case_id=recipe.control_case_id,
            application_spec_sha=recipe.application_spec_sha,
            scenario_id=recipe.scenario_id,
            scenario_sha=recipe.scenario_sha,
            scenario_recipe_sha=recipe.recipe_sha,
            construction_rule_id="c17-analytic-quotient-gauge-bundle-v1",
            selected_fejer_order=selected_fejer_order,
            observer_dimension=8,
            kernel_basis=freeze_complex_tensor(
                np.column_stack((undressed_response, gauge_basis))
            ),
            physical_quotient_map=freeze_complex_tensor(quotient),
            physical_quotient_metric=freeze_complex_tensor(
                np.eye(6, dtype=np.complex128)
            ),
            target_physical_representatives=freeze_complex_tensor(targets),
            undressed_response_representatives=(
                freeze_complex_tensor(undressed_response)
            ),
            dressed_response_representatives=(
                freeze_complex_tensor(dressed_response)
            ),
            gauge_basis=freeze_complex_tensor(gauge_basis),
            gauge_graph_singular_values=graph_slopes,
            finite_graph_formula_id=(
                "c17-fejer-shared-U-actual-a-ablated-a-over-Tplus1-v1"
            ),
            fejer_opposite_phase_leakage=leakage,
            expected_undressed_finite_graph_singular_values=(
                expected_undressed_finite_slope,
                expected_undressed_finite_slope,
            ),
            expected_dressed_finite_graph_singular_values=(
                amplitude,
                amplitude,
            ),
            coverage_control=None,
            gauge_amplitude=recipe.gauge_amplitude,
            integration_state=GEOMETRY_APPLICATION_INTEGRATION_STATE,
            bundle_sha="0" * 64,
        )
    )


def verify_c17_analytic_geometry_bundle(
    parent: VerifiedParentFreeze,
    bundle: GeometryScenarioOperatorBundleTemplate,
) -> GeometryScenarioOperatorBundleTemplate:
    """Replay the pending C17 dressed/undressed bundle and its amplitude."""

    _validate_geometry_scenario_operator_bundle_template(bundle)
    if (
        bundle.scenario_id != C17_GEOMETRY_SCENARIO_IDS[0]
        or bundle.construction_rule_id
        != "c17-analytic-quotient-gauge-bundle-v1"
    ):
        raise ValueError("bundle is not a C17 analytic geometry template")
    expected = build_c17_analytic_geometry_bundle(
        parent,
        bundle.selected_fejer_order,
    )
    if bundle != expected:
        raise ValueError("C17 analytic geometry bundle differs from live replay")
    return bundle


def _finite_response(
    recipe: GeometryApplicationRecipeArtifact,
    branch: Literal["actual", "matched_ablated"],
    order: int,
) -> np.ndarray:
    if order not in _CANDIDATE_FEJER_ORDERS:
        raise ValueError("preflight order is not preregistered")
    source = frozen_tensor_array(recipe.source_injection)
    readout = frozen_tensor_array(recipe.readout)
    blocks = []
    for momentum in _COMMON_MOMENTA:
        actual = geometry_application_recipe_symbol(
            recipe,
            momentum,
            "actual",
        )
        values = np.linalg.eigvals(actual)
        selected = tuple(
            value
            for value in values
            if any(
                lower <= math.atan2(float(value.imag), float(value.real)) <= upper
                for lower, upper in recipe.reference_phase_bands
            )
        )
        if len(selected) != recipe.expected_shell_rank:
            raise ValueError("preflight actual shell rank differs from the recipe")
        phase_vector = sum(selected, 0.0 + 0.0j)
        shell_phase = math.atan2(
            float(phase_vector.imag),
            float(phase_vector.real),
        )
        blocks.append(
            compute_fejer_filtered_response(
                geometry_application_recipe_symbol(
                    recipe,
                    momentum,
                    branch,
                ),
                np.eye(4, dtype=np.complex128),
                shell_phase,
                order,
                source,
                readout,
            )
        )
    return np.vstack(blocks)


def _c17_active_frame(
    response: np.ndarray,
) -> tuple[np.ndarray, tuple[float, ...]]:
    left, singular_values, _ = np.linalg.svd(response, full_matrices=False)
    active = singular_values > 0.001
    if int(np.count_nonzero(active)) != 2:
        raise ValueError("C17 finite response does not have active rank two")
    return (
        np.asarray(left[:, active], dtype=np.complex128),
        tuple(float(value) for value in singular_values[active]),
    )


def _c17_graph_spectrum(
    frame: np.ndarray,
    physical_basis: np.ndarray,
    gauge_basis: np.ndarray,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    physical_block = physical_basis.conj().T @ frame
    physical_singular_values = np.linalg.svd(
        physical_block,
        compute_uv=False,
    )
    if float(np.min(physical_singular_values)) <= 1.0e-12:
        raise ValueError("C17 finite physical graph block is singular")
    graph = (gauge_basis.conj().T @ frame) @ np.linalg.inv(physical_block)
    return (
        tuple(float(value) for value in np.linalg.svd(graph, compute_uv=False)),
        tuple(float(value) for value in physical_singular_values),
    )


def measure_c17_finite_response_preflight(
    parent: VerifiedParentFreeze,
    bundle: GeometryScenarioOperatorBundleTemplate,
) -> C17FiniteResponsePreflight:
    """Run both real recipe branches and save a non-authoritative diagnostic."""

    verified = verify_c17_analytic_geometry_bundle(parent, bundle)
    recipe = verify_geometry_application_recipe(
        parent,
        build_geometry_application_recipe(parent, verified.scenario_id),
    )
    raw_undressed = _finite_response(
        recipe,
        "matched_ablated",
        verified.selected_fejer_order,
    )
    raw_dressed = _finite_response(
        recipe,
        "actual",
        verified.selected_fejer_order,
    )
    undressed_frame, undressed_active = _c17_active_frame(raw_undressed)
    dressed_frame, dressed_active = _c17_active_frame(raw_dressed)
    physical_basis = frozen_tensor_array(
        verified.undressed_response_representatives
    )
    gauge_basis = frozen_tensor_array(verified.gauge_basis)
    undressed_graph, undressed_physical_singular_values = _c17_graph_spectrum(
        undressed_frame,
        physical_basis,
        gauge_basis,
    )
    dressed_graph, dressed_physical_singular_values = _c17_graph_spectrum(
        dressed_frame,
        physical_basis,
        gauge_basis,
    )
    expected_undressed_graph = (
        verified.expected_undressed_finite_graph_singular_values
    )
    expected_dressed_graph = (
        verified.expected_dressed_finite_graph_singular_values
    )
    expected_undressed_physical_value = 1.0 / math.sqrt(
        1.0 + expected_undressed_graph[0] ** 2
    )
    expected_dressed_physical_value = 1.0 / math.sqrt(
        1.0 + expected_dressed_graph[0] ** 2
    )
    expected_undressed_physical_singular_values = (
        expected_undressed_physical_value,
        expected_undressed_physical_value,
    )
    expected_dressed_physical_singular_values = (
        expected_dressed_physical_value,
        expected_dressed_physical_value,
    )
    graph_residual = max(
        max(
            abs(observed - expected)
            for observed, expected in zip(
                undressed_graph,
                expected_undressed_graph,
            )
        ),
        max(
            abs(observed - expected)
            for observed, expected in zip(
                dressed_graph,
                expected_dressed_graph,
            )
        ),
    )
    undressed_physical_block_residual = max(
        abs(observed - expected)
        for observed, expected in zip(
            undressed_physical_singular_values,
            expected_undressed_physical_singular_values,
        )
    )
    dressed_physical_block_residual = max(
        abs(observed - expected)
        for observed, expected in zip(
            dressed_physical_singular_values,
            expected_dressed_physical_singular_values,
        )
    )
    thresholds = GeometryNumericalThresholds(
        signal_threshold=0.001,
        geometry_threshold=0.05,
        geometry_ambiguity_half_width=0.01,
        coverage_threshold=0.5,
        coverage_ambiguity_half_width=0.1,
    )
    kernel = frozen_tensor_array(verified.kernel_basis)
    quotient = frozen_tensor_array(verified.physical_quotient_map)
    metric = frozen_tensor_array(verified.physical_quotient_metric)
    targets = frozen_tensor_array(verified.target_physical_representatives)
    undressed_geometry = _compute_geometry_spectrum_from_matrices(
        undressed_frame,
        kernel,
        quotient,
        metric,
        targets,
        thresholds=thresholds,
    )
    dressed_geometry = _compute_geometry_spectrum_from_matrices(
        dressed_frame,
        kernel,
        quotient,
        metric,
        targets,
        thresholds=thresholds,
    )
    coverage_drift = max(
        abs(left - right)
        for left, right in zip(
            undressed_geometry.c_spectrum,
            dressed_geometry.c_spectrum,
        )
    )
    provisional = C17FiniteResponsePreflight(
        preflight_schema_version=C17_FINITE_RESPONSE_PREFLIGHT_SCHEMA_VERSION,
        parent_freeze_sha=verified.parent_freeze_sha,
        scenario_id=verified.scenario_id,
        scenario_sha=verified.scenario_sha,
        scenario_recipe_sha=verified.scenario_recipe_sha,
        bundle_sha=verified.bundle_sha,
        selected_fejer_order=verified.selected_fejer_order,
        finite_graph_formula_id=verified.finite_graph_formula_id,
        fejer_opposite_phase_leakage=(
            verified.fejer_opposite_phase_leakage
        ),
        raw_undressed_response=freeze_complex_tensor(raw_undressed),
        raw_dressed_response=freeze_complex_tensor(raw_dressed),
        undressed_active_singular_values=undressed_active,
        dressed_active_singular_values=dressed_active,
        undressed_graph_singular_values=undressed_graph,
        dressed_graph_singular_values=dressed_graph,
        expected_undressed_graph_singular_values=expected_undressed_graph,
        expected_dressed_graph_singular_values=expected_dressed_graph,
        undressed_physical_block_singular_values=(
            undressed_physical_singular_values
        ),
        dressed_physical_block_singular_values=(
            dressed_physical_singular_values
        ),
        expected_undressed_physical_block_singular_values=(
            expected_undressed_physical_singular_values
        ),
        expected_dressed_physical_block_singular_values=(
            expected_dressed_physical_singular_values
        ),
        undressed_g_spectrum=undressed_geometry.g_spectrum,
        dressed_g_spectrum=dressed_geometry.g_spectrum,
        undressed_c_spectrum=undressed_geometry.c_spectrum,
        dressed_c_spectrum=dressed_geometry.c_spectrum,
        graph_prediction_residual=float(graph_residual),
        undressed_physical_block_prediction_residual=float(
            undressed_physical_block_residual
        ),
        dressed_physical_block_prediction_residual=float(
            dressed_physical_block_residual
        ),
        coverage_spectrum_drift=float(coverage_drift),
        integration_state=GEOMETRY_APPLICATION_INTEGRATION_STATE,
        preflight_sha="0" * 64,
    )
    result = replace(
        provisional,
        preflight_sha=canonical_sha(
            c17_finite_response_preflight_payload(provisional)
        ),
    )
    _validate_c17_finite_response_preflight(result)
    return result


def verify_c17_finite_response_preflight(
    parent: VerifiedParentFreeze,
    bundle: GeometryScenarioOperatorBundleTemplate,
    preflight: C17FiniteResponsePreflight,
) -> C17FiniteResponsePreflight:
    """Hydrate only by replaying both real pending C17 branches."""

    _validate_c17_finite_response_preflight(preflight)
    expected = measure_c17_finite_response_preflight(parent, bundle)
    if preflight != expected:
        raise ValueError("C17 finite-response preflight differs from live replay")
    return preflight


def _orthonormal_columns(
    matrix: np.ndarray,
    *,
    expected_rank: int,
) -> np.ndarray:
    left, singular_values, _ = np.linalg.svd(matrix, full_matrices=False)
    active = singular_values > 0.001
    if int(np.count_nonzero(active)) != expected_rank:
        raise ValueError("preflight response failed the frozen signal rank")
    return np.asarray(left[:, active], dtype=np.complex128)


def _build_c15_preflight_bundle(
    parent: VerifiedParentFreeze,
    selected_fejer_order: int,
) -> tuple[
    GeometryOperatorBundleTemplate,
    dict[str, np.ndarray],
]:
    """Circular numerical reachability diagnostic; never an authority input.

    This deliberately derives comparison sectors from the analytic finite
    response in order to answer only whether the proposed carrier can realize
    the four semantic spectra.  Its bundle must never be copied into Task 12
    or Task 14.  The live geometry bundle has to be derived *before* response
    measurement from a separately frozen Parent/DAG semantic-basis recipe.
    """

    if selected_fejer_order not in _CANDIDATE_FEJER_ORDERS:
        raise ValueError("preflight order is not preregistered")
    recipes = {
        scenario_id: build_geometry_application_recipe(parent, scenario_id)
        for scenario_id in C15_GEOMETRY_SCENARIO_IDS
    }
    responses = {
        scenario_id: _finite_response(
            recipe,
            "actual",
            selected_fejer_order,
        )
        for scenario_id, recipe in recipes.items()
    }
    full_response = responses[C15_GEOMETRY_SCENARIO_IDS[0]]
    tt = _orthonormal_columns(full_response[:, :2], expected_rank=2)
    row_residual = full_response[:, 3:4] - tt @ (
        tt.conj().T @ full_response[:, 3:4]
    )
    row = _orthonormal_columns(row_residual, expected_rank=1)
    tt_row = np.column_stack((tt, row))
    gauge_residual = full_response[:, 2:3] - tt_row @ (
        tt_row.conj().T @ full_response[:, 2:3]
    )
    gauge = _orthonormal_columns(gauge_residual, expected_rank=1)
    kernel = np.column_stack((tt, gauge))
    quotient = np.column_stack((tt, row)).conj().T
    metric = np.eye(3, dtype=np.complex128)
    targets = tt
    manifest = _reverify_verified_parent_freeze(parent)
    provisional = GeometryOperatorBundleTemplate(
        bundle_schema_version=(
            GEOMETRY_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION
        ),
        parent_freeze_sha=manifest.parent_freeze_sha,
        application_spec_sha=recipes[
            C15_GEOMETRY_SCENARIO_IDS[0]
        ].application_spec_sha,
        scenario_recipe_shas=tuple(
            recipes[scenario_id].recipe_sha
            for scenario_id in C15_GEOMETRY_SCENARIO_IDS
        ),
        construction_rule_id="c15-tt-row-gauge-response-bundle-v1",
        selected_fejer_order=selected_fejer_order,
        observer_dimension=8,
        kernel_basis=freeze_complex_tensor(kernel),
        physical_quotient_map=freeze_complex_tensor(quotient),
        physical_quotient_metric=freeze_complex_tensor(metric),
        target_physical_representatives=freeze_complex_tensor(targets),
        integration_state=GEOMETRY_APPLICATION_INTEGRATION_STATE,
        bundle_sha="0" * 64,
    )
    bundle = replace(
        provisional,
        bundle_sha=canonical_sha(
            geometry_operator_bundle_template_payload(provisional)
        ),
    )
    return bundle, responses


__all__ = [
    "C15_EXPECTED_SPECTRA",
    "C15_GEOMETRY_SCENARIO_IDS",
    "C16_GEOMETRY_SCENARIO_IDS",
    "C17_GEOMETRY_SCENARIO_IDS",
    "C17_FINITE_RESPONSE_PREFLIGHT_SCHEMA_VERSION",
    "C18_GEOMETRY_SCENARIO_IDS",
    "C19_GEOMETRY_SCENARIO_IDS",
    "GEOMETRY_APPLICATION_INTEGRATION_STATE",
    "GEOMETRY_APPLICATION_RECIPE_SCHEMA_VERSION",
    "GEOMETRY_APPLICATION_SCENARIO_IDS",
    "GEOMETRY_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION",
    "GEOMETRY_SCENARIO_OPERATOR_BUNDLE_TEMPLATE_SCHEMA_VERSION",
    "C17FiniteResponsePreflight",
    "GeometryApplicationRecipeArtifact",
    "GeometryOperatorBundleTemplate",
    "GeometryScenarioOperatorBundleTemplate",
    "build_c15_analytic_geometry_bundle",
    "build_c16_analytic_geometry_bundle",
    "build_c17_analytic_geometry_bundle",
    "build_geometry_application_recipe",
    "build_geometry_recipe_trace_and_operators",
    "geometry_application_recipe_payload",
    "geometry_application_recipe_symbol",
    "geometry_operator_bundle_template_payload",
    "geometry_scenario_operator_bundle_template_payload",
    "c17_finite_response_preflight_payload",
    "measure_c17_finite_response_preflight",
    "verify_c15_analytic_geometry_bundle",
    "verify_c16_analytic_geometry_bundle",
    "verify_c17_analytic_geometry_bundle",
    "verify_c17_finite_response_preflight",
    "verify_geometry_application_recipe",
]
