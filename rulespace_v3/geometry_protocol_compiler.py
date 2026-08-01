"""Repository-closed pre-response compiler for geometry protocol v3.

The records emitted here are deliberately raw and authority-neutral.  The
public compiler consumes only live Parent-v2, permit-v2, and materialization-v2
capabilities, rebuilds the analytic geometry from the repository-frozen
Parent-v1 history, and records the exact lineage.  It does not run a response,
read a threshold, issue an opaque capability, or evaluate a scientific verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, replace
import re
from typing import Literal, Optional

import numpy as np

from .application_authority_v2 import (
    VerifiedCalibrationApplicationPermitV2,
    _require_calibration_application_permit_v2_for_parent,
)
from .application_materialization_v2 import (
    VerifiedV3M0ApplicationScenarioMaterializationV2,
    _require_application_scenario_materialization_v2_for_upstream,
)
from .evidence import canonical_sha
from .factory import FrozenComplexTensor, freeze_complex_tensor, frozen_tensor_array
from .frozen_call_graph import freeze_rulespace_call_graph
from .geometry_application_recipes import (
    C15_GEOMETRY_SCENARIO_IDS,
    C16_GEOMETRY_SCENARIO_IDS,
    C17_GEOMETRY_SCENARIO_IDS,
    C18_GEOMETRY_SCENARIO_IDS,
    C19_GEOMETRY_SCENARIO_IDS,
    _find_application_and_scenario,
    build_c15_analytic_geometry_bundle,
    build_c16_analytic_geometry_bundle,
    build_c17_analytic_geometry_bundle,
    build_geometry_application_recipe,
)
from .geometry_protocol_v3 import (
    C15_QUOTIENT_SPECTRUM,
    C16_COVERAGE_CONTROL,
    C17_QUOTIENT_GAUGE_GRAPH,
    C18_INDEPENDENT_UNARY,
    GEOMETRY_ANALYTIC_CONTEXT_V2_SCHEMA_VERSION,
    GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND,
    SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V3_SCHEMA_VERSION,
    GeometryAnalyticContextV2,
    ScenarioResponseGeometryBundleV3,
    geometry_analytic_context_v2_payload,
    scenario_response_geometry_bundle_v3_payload,
    verify_geometry_analytic_context_v2,
    verify_scenario_response_geometry_bundle_v3,
    verify_scenario_response_geometry_bundle_v3_for_context,
)
from .parent_authority import VerifiedParentFreezeV2, require_current_parent
from .parent_freeze import issue_v3m0_parent_freeze


REPOSITORY_CLOSED_GEOMETRY_COMPILATION_V1_SCHEMA_VERSION = (
    "v3m0.repository-closed-geometry-compilation.v1"
)
REPOSITORY_CLOSED_GEOMETRY_COMPILATION_AUTHORITY_STATE = (
    "RAW_REPOSITORY_CLOSED_NO_AUTHORITY"
)
GEOMETRY_PRE_RESPONSE_EVIDENCE_STATE = "NOT_RUN_PRE_RESPONSE"
GEOMETRY_SCIENTIFIC_VERDICT_STATE = "NOT_EVALUATED"
C19_PRODUCTION_EVALUATION_STATE = (
    "NOT_EVALUATED_PRE_RESPONSE_10D_PREREQUISITES_UNRESOLVED"
)

CANONICAL_GEOMETRY_PRODUCTION_SCENARIO_IDS = (
    *C15_GEOMETRY_SCENARIO_IDS,
    *C16_GEOMETRY_SCENARIO_IDS,
    *C17_GEOMETRY_SCENARIO_IDS,
    *C18_GEOMETRY_SCENARIO_IDS,
)

_SCENARIO_KIND = {
    **{identifier: C15_QUOTIENT_SPECTRUM for identifier in C15_GEOMETRY_SCENARIO_IDS},
    **{identifier: C16_COVERAGE_CONTROL for identifier in C16_GEOMETRY_SCENARIO_IDS},
    **{
        identifier: C17_QUOTIENT_GAUGE_GRAPH for identifier in C17_GEOMETRY_SCENARIO_IDS
    },
    **{identifier: C18_INDEPENDENT_UNARY for identifier in C18_GEOMETRY_SCENARIO_IDS},
}
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")


class GeometryProductionCompilationUnavailable(RuntimeError):
    """The reviewed production premises are not sufficient for compilation."""


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    try:
        observed = frozenset(vars(value))
    except TypeError as exc:
        raise TypeError(f"{field} has no exact record body") from exc
    if observed != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _sha(value: object, field: str, *, pattern=_LOWER_SHA, exact_type=type) -> str:
    if exact_type(value) is not str or pattern.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _sha_tuple(
    value: object,
    field: str,
    *,
    expected_length: int,
    sha_verifier=_sha,
    exact_type=type,
) -> tuple[str, ...]:
    if exact_type(value) is not tuple or len(value) != expected_length:
        raise ValueError(f"{field} must contain exactly {expected_length} SHAs")
    result = tuple(
        sha_verifier(item, f"{field}[{index}]") for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise ValueError(f"{field} contains duplicate SHAs")
    return result


@dataclass(frozen=True)
class RepositoryClosedGeometryCompilationV1:
    """Self-hashed raw replay; never an authority or a scientific verdict."""

    compilation_schema_version: str
    authority_state: Literal["RAW_REPOSITORY_CLOSED_NO_AUTHORITY"]
    formal_parent_v2_sha: str
    permit_v2_sha: str
    materialization_v2_sha: str
    geometry_kind: Literal[
        "C15_QUOTIENT_SPECTRUM",
        "C16_COVERAGE_CONTROL",
        "C17_QUOTIENT_GAUGE_GRAPH",
        "C18_INDEPENDENT_UNARY",
    ]
    c15_reference_compilation_shas: tuple[str, ...]
    analytic_context: GeometryAnalyticContextV2
    geometry_bundle: ScenarioResponseGeometryBundleV3
    response_evidence_state: Literal["NOT_RUN_PRE_RESPONSE"]
    scientific_verdict_state: Literal["NOT_EVALUATED"]
    compilation_sha: str

    def __post_init__(
        self,
        *,
        schema_version=REPOSITORY_CLOSED_GEOMETRY_COMPILATION_V1_SCHEMA_VERSION,
        authority_state=REPOSITORY_CLOSED_GEOMETRY_COMPILATION_AUTHORITY_STATE,
        kinds=frozenset(_SCENARIO_KIND.values()),
        c16_kind=C16_COVERAGE_CONTROL,
        context_type=GeometryAnalyticContextV2,
        bundle_type=ScenarioResponseGeometryBundleV3,
        evidence_state=GEOMETRY_PRE_RESPONSE_EVIDENCE_STATE,
        verdict_state=GEOMETRY_SCIENTIFIC_VERDICT_STATE,
        sha_verifier=_sha,
        sha_tuple_verifier=_sha_tuple,
        exact_type=type,
    ) -> None:
        if self.compilation_schema_version != schema_version:
            raise ValueError("geometry compilation schema drifted")
        if self.authority_state != authority_state:
            raise ValueError("raw geometry compilation cannot claim authority")
        for field in (
            "formal_parent_v2_sha",
            "permit_v2_sha",
            "materialization_v2_sha",
            "compilation_sha",
        ):
            sha_verifier(getattr(self, field), field)
        if self.geometry_kind not in kinds:
            raise ValueError("production geometry kind is not closed")
        expected_refs = 4 if self.geometry_kind == c16_kind else 0
        sha_tuple_verifier(
            self.c15_reference_compilation_shas,
            "c15_reference_compilation_shas",
            expected_length=expected_refs,
        )
        if exact_type(self.analytic_context) is not context_type:
            raise TypeError("analytic_context has the wrong strict type")
        if exact_type(self.geometry_bundle) is not bundle_type:
            raise TypeError("geometry_bundle has the wrong strict type")
        if self.response_evidence_state != evidence_state:
            raise ValueError("geometry compilation contains response evidence")
        if self.scientific_verdict_state != verdict_state:
            raise ValueError("geometry compilation claimed a scientific verdict")


def repository_closed_geometry_compilation_v1_payload(
    compilation: RepositoryClosedGeometryCompilationV1,
) -> dict[str, object]:
    _exact_record(
        compilation,
        RepositoryClosedGeometryCompilationV1,
        "repository-closed geometry compilation",
    )
    compilation.__post_init__()
    context = compilation.analytic_context
    bundle = compilation.geometry_bundle
    return {
        "compilation_schema_version": compilation.compilation_schema_version,
        "authority_state": compilation.authority_state,
        "formal_parent_v2_sha": compilation.formal_parent_v2_sha,
        "permit_v2_sha": compilation.permit_v2_sha,
        "materialization_v2_sha": compilation.materialization_v2_sha,
        "geometry_kind": compilation.geometry_kind,
        "c15_reference_compilation_shas": list(
            compilation.c15_reference_compilation_shas
        ),
        "analytic_context": {
            **geometry_analytic_context_v2_payload(context),
            "context_sha": context.context_sha,
        },
        "geometry_bundle": {
            **scenario_response_geometry_bundle_v3_payload(bundle),
            "geometry_bundle_sha": bundle.geometry_bundle_sha,
        },
        "response_evidence_state": compilation.response_evidence_state,
        "scientific_verdict_state": compilation.scientific_verdict_state,
    }


def _verify_compilation_body(
    compilation: RepositoryClosedGeometryCompilationV1,
    *,
    sha_builder=canonical_sha,
    context_verifier=verify_geometry_analytic_context_v2,
    bundle_verifier=verify_scenario_response_geometry_bundle_v3,
    context_bundle_verifier=verify_scenario_response_geometry_bundle_v3_for_context,
) -> RepositoryClosedGeometryCompilationV1:
    _exact_record(
        compilation,
        RepositoryClosedGeometryCompilationV1,
        "repository-closed geometry compilation",
    )
    compilation.__post_init__()
    context = context_verifier(compilation.analytic_context)
    bundle = bundle_verifier(compilation.geometry_bundle)
    context_bundle_verifier(context, bundle)
    if compilation.geometry_kind != context.geometry_kind:
        raise ValueError("outer geometry kind differs from analytic context")
    if compilation.compilation_sha != sha_builder(
        repository_closed_geometry_compilation_v1_payload(compilation)
    ):
        raise ValueError("geometry compilation SHA does not match its exact body")
    return compilation


@dataclass(frozen=True)
class _AnalyticGeometryRebuild:
    scenario_id: str
    source_recipe_sha: str
    operation_output_ids: tuple[str, ...]
    semantic_sector_names: tuple[str, ...]
    source_injection: FrozenComplexTensor
    readout_coisometry: FrozenComplexTensor
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


def _make_production_analytic_rebuilder(
    *,
    historical_parent_issuer=issue_v3m0_parent_freeze,
    scenario_resolver=_find_application_and_scenario,
    recipe_builder=build_geometry_application_recipe,
    c15_builder=build_c15_analytic_geometry_bundle,
    c16_builder=build_c16_analytic_geometry_bundle,
    c17_builder=build_c17_analytic_geometry_bundle,
    tensor_array=frozen_tensor_array,
    tensor_freezer=freeze_complex_tensor,
):
    """Close over the reviewed pre-permit analytic builders."""

    def rebuild(parent_manifest, scenario_id: str, selected_fejer_order: int):
        historical_parent = historical_parent_issuer()
        if historical_parent.manifest != parent_manifest.historical_parent_v1:
            raise ValueError("Parent-v2 historical Parent-v1 body drifted")
        _, historical_scenario = scenario_resolver(historical_parent, scenario_id)
        recipe = recipe_builder(historical_parent, scenario_id)
        kind = _SCENARIO_KIND[scenario_id]
        empty = {
            "coverage_control_id": None,
            "coverage_control_wire": (),
            "undressed_response_representatives": None,
            "gauge_basis": None,
            "gauge_amplitude": None,
            "expected_graph_rank": None,
            "analytic_graph_singular_values": (),
            "fejer_graph_slope_formula_id": None,
            "expected_actual_raw_graph_singular_values": (),
            "expected_ablated_raw_graph_singular_values": (),
        }
        if kind == C15_QUOTIENT_SPECTRUM:
            analytic = c15_builder(historical_parent, selected_fejer_order)
            kernel = tensor_array(analytic.kernel_basis)
            empty["gauge_basis"] = tensor_freezer(kernel[:, 2:3])
        elif kind == C16_COVERAGE_CONTROL:
            analytic = c16_builder(
                historical_parent,
                scenario_id,
                selected_fejer_order,
            )
            if len(historical_scenario.operation_output_ids) != 1:
                raise ValueError("C16 does not have one exact operation output")
            empty["coverage_control_id"] = historical_scenario.operation_output_ids[0]
            empty["coverage_control_wire"] = (analytic.coverage_control,)
        elif kind == C17_QUOTIENT_GAUGE_GRAPH:
            analytic = c17_builder(historical_parent, selected_fejer_order)
            empty.update(
                undressed_response_representatives=(
                    analytic.undressed_response_representatives
                ),
                gauge_basis=analytic.gauge_basis,
                gauge_amplitude=analytic.gauge_amplitude,
                expected_graph_rank=2,
                analytic_graph_singular_values=analytic.gauge_graph_singular_values,
                fejer_graph_slope_formula_id=analytic.finite_graph_formula_id,
                expected_actual_raw_graph_singular_values=(
                    analytic.expected_dressed_finite_graph_singular_values
                ),
                expected_ablated_raw_graph_singular_values=(
                    analytic.expected_undressed_finite_graph_singular_values
                ),
            )
        else:
            source = tensor_array(recipe.source_injection)
            if source.shape != (4, 2):
                raise ValueError("C18 analytic source directions are not 4x2")
            analytic = type("C18Analytic", (), {})()
            analytic.kernel_basis = tensor_freezer(source[:, :1])
            analytic.physical_quotient_map = tensor_freezer(
                np.eye(4, dtype=np.complex128)
            )
            analytic.physical_quotient_metric = tensor_freezer(
                np.eye(4, dtype=np.complex128)
            )
            analytic.target_physical_representatives = recipe.source_injection
        return _AnalyticGeometryRebuild(
            scenario_id=scenario_id,
            source_recipe_sha=recipe.recipe_sha,
            operation_output_ids=historical_scenario.operation_output_ids,
            semantic_sector_names=recipe.semantic_sector_names,
            source_injection=recipe.source_injection,
            readout_coisometry=recipe.readout,
            kernel_basis=analytic.kernel_basis,
            physical_quotient_map=analytic.physical_quotient_map,
            physical_quotient_metric=analytic.physical_quotient_metric,
            target_physical_representatives=(analytic.target_physical_representatives),
            **empty,
        )

    return rebuild


_production_analytic_rebuilder = _make_production_analytic_rebuilder()


def _exact_one(values: object, predicate, field: str):
    if type(values) is not tuple:
        raise TypeError(f"{field} registry must be an exact tuple")
    matches = tuple(item for item in values if predicate(item))
    if len(matches) != 1:
        raise ValueError(f"{field} does not resolve to one exact record")
    return matches[0]


def _kind_for_scenario(scenario_id: str) -> str:
    if scenario_id in C19_GEOMETRY_SCENARIO_IDS:
        raise GeometryProductionCompilationUnavailable(
            "C19 production compilation is "
            f"{C19_PRODUCTION_EVALUATION_STATE}: the reviewed Parent remains "
            "four-channel and cannot certify the required 10D observer-collapse "
            "premises"
        )
    try:
        return _SCENARIO_KIND[scenario_id]
    except KeyError as exc:
        raise ValueError(
            "scenario is not a C15-C18 production geometry scenario"
        ) from exc


def _validate_lineage(parent_manifest, permit_body, materialization_body):
    if (
        permit_body.parent_freeze_v2_sha != parent_manifest.parent_freeze_v2_sha
        or materialization_body.formal_parent_v2_sha
        != parent_manifest.parent_freeze_v2_sha
        or materialization_body.permit_v2_sha != permit_body.permit_sha
        or materialization_body.selected_fejer_order != permit_body.selected_fejer_order
    ):
        raise ValueError("geometry upstreams are spliced across Parent/permit/T")
    application = permit_body.application_authority
    current_application = _exact_one(
        parent_manifest.current_application_authorities,
        lambda item: (
            item.application_instance_id == application.application_instance_id
        ),
        "current application authority",
    )
    if current_application != application:
        raise ValueError("permit application differs from current Parent-v2")
    if (
        materialization_body.application_authority_sha
        != application.application_authority_sha
        or materialization_body.control_case_id != application.control_case_id
        or materialization_body.application_instance_id
        != application.application_instance_id
    ):
        raise ValueError("materialization is spliced across its application")
    scenario = _exact_one(
        application.scenario_authorities,
        lambda item: item.scenario_id == materialization_body.scenario_id,
        "current scenario authority",
    )
    response = scenario.response_contract
    recipe = materialization_body.scenario_recipe
    if (
        materialization_body.scenario_authority_sha != scenario.scenario_authority_sha
        or materialization_body.response_contract_sha != response.response_contract_sha
        or materialization_body.scenario_sha
        != scenario.scenario_execution_spec.scenario_sha
        or recipe.operation_dag_sha != response.operation_dag_sha
        or recipe.compiled_contract_sha != response.compiled_contract_sha
        or recipe.scenario_id != scenario.scenario_id
        or recipe.scenario_sha != materialization_body.scenario_sha
    ):
        raise ValueError("materialization is spliced across its scenario contract")
    kind = _kind_for_scenario(materialization_body.scenario_id)
    candidate_scenario = _exact_one(
        tuple(
            candidate_scenario
            for candidate_application in (
                parent_manifest.reviewed_candidate_v1.application_candidates
            )
            for candidate_scenario in candidate_application.scenario_candidates
        ),
        lambda item: (
            item.scenario_execution_spec.scenario_id == materialization_body.scenario_id
        ),
        "reviewed candidate-v1 geometry scenario",
    )
    expected_derivation = GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND[kind]
    if candidate_scenario.response_template.geometry_bundle_derivation_id != (
        expected_derivation
    ):
        raise ValueError("Parent-v2 geometry derivation source ID drifted")
    expected_ranks = (1, 2) if kind == C18_INDEPENDENT_UNARY else (2, 2)
    if (
        response.expected_actual_shell_rank,
        response.expected_matched_shell_rank,
    ) != expected_ranks:
        raise ValueError("Parent-v2 geometry shell-rank contract drifted")
    if (
        response.uses_global_fft_projection is not False
        or response.uses_per_k_time_step_projector is not False
    ):
        raise ValueError("geometry response contract contains a forbidden projector")
    return kind, scenario, response, recipe


def _validate_c15_references(parent_manifest, resolved_references, selected_t):
    if type(resolved_references) is not tuple or len(resolved_references) != 4:
        raise ValueError("C15/C16 requires four canonical C15 live references")
    observed = []
    for permit_body, materialization_body in resolved_references:
        kind, _, _, recipe = _validate_lineage(
            parent_manifest,
            permit_body,
            materialization_body,
        )
        if kind != C15_QUOTIENT_SPECTRUM:
            raise ValueError("C15 reference tuple contains a foreign geometry kind")
        if materialization_body.selected_fejer_order != selected_t:
            raise ValueError("C15 reference tuple is spliced across Fejer orders")
        observed.append((materialization_body.scenario_id, recipe.recipe_sha))
    if tuple(item[0] for item in observed) != C15_GEOMETRY_SCENARIO_IDS:
        raise ValueError("C15 reference tuple is not in canonical scenario order")
    return tuple(item[1] for item in observed)


def _build_context_and_bundle(
    parent_manifest,
    permit_body,
    materialization_body,
    resolved_c15_references,
    *,
    analytic_rebuilder,
    sha_builder=canonical_sha,
):
    kind, scenario, response, recipe = _validate_lineage(
        parent_manifest,
        permit_body,
        materialization_body,
    )
    selected_t = materialization_body.selected_fejer_order
    if kind in (C15_QUOTIENT_SPECTRUM, C16_COVERAGE_CONTROL):
        c15_recipe_shas = _validate_c15_references(
            parent_manifest,
            resolved_c15_references,
            selected_t,
        )
        source_recipe_shas = (
            c15_recipe_shas
            if kind == C15_QUOTIENT_SPECTRUM
            else (*c15_recipe_shas, recipe.recipe_sha)
        )
        if kind == C15_QUOTIENT_SPECTRUM:
            active_index = C15_GEOMETRY_SCENARIO_IDS.index(
                materialization_body.scenario_id
            )
            if source_recipe_shas[active_index] != recipe.recipe_sha:
                raise ValueError(
                    "active C15 materialization differs from its reference"
                )
    else:
        if resolved_c15_references:
            raise ValueError("non-C15/C16 compilation received C15 references")
        source_recipe_shas = (recipe.recipe_sha,)
    analytic = analytic_rebuilder(
        parent_manifest,
        materialization_body.scenario_id,
        selected_t,
    )
    if (
        analytic.scenario_id != materialization_body.scenario_id
        or analytic.source_recipe_sha != response.preflight_derivation_or_recipe_sha
        or analytic.operation_output_ids
        != scenario.scenario_execution_spec.operation_output_ids
        or analytic.source_injection != materialization_body.scenario_source_injection
        or analytic.readout_coisometry
        != materialization_body.scenario_readout_coisometry
    ):
        raise ValueError("analytic rebuild differs from current Parent/materialization")

    context0 = GeometryAnalyticContextV2(
        context_schema_version=GEOMETRY_ANALYTIC_CONTEXT_V2_SCHEMA_VERSION,
        geometry_kind=kind,
        control_case_id=materialization_body.control_case_id,
        scenario_id=materialization_body.scenario_id,
        scenario_sha=materialization_body.scenario_sha,
        recipe_sha=recipe.recipe_sha,
        operation_dag_sha=recipe.operation_dag_sha,
        compiled_contract_sha=recipe.compiled_contract_sha,
        geometry_derivation_source_id=(GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND[kind]),
        semantic_sector_names=analytic.semantic_sector_names,
        selected_fejer_order=selected_t,
        analytic_source_recipe_shas=source_recipe_shas,
        coverage_control=(
            analytic.coverage_control_wire[0] if kind == C16_COVERAGE_CONTROL else None
        ),
        gauge_amplitude=(
            analytic.gauge_amplitude if kind == C17_QUOTIENT_GAUGE_GRAPH else None
        ),
        observer_collapse_expected=False,
        context_sha="0" * 64,
    )
    context = replace(
        context0,
        context_sha=sha_builder(geometry_analytic_context_v2_payload(context0)),
    )
    bundle0 = ScenarioResponseGeometryBundleV3(
        geometry_bundle_schema_version=(
            SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V3_SCHEMA_VERSION
        ),
        geometry_kind=kind,
        analytic_context_sha=context.context_sha,
        scenario_id=context.scenario_id,
        scenario_sha=context.scenario_sha,
        recipe_sha=context.recipe_sha,
        geometry_derivation_source_id=context.geometry_derivation_source_id,
        semantic_sector_names=context.semantic_sector_names,
        selected_fejer_order=context.selected_fejer_order,
        analytic_source_recipe_shas=context.analytic_source_recipe_shas,
        kernel_basis=analytic.kernel_basis,
        physical_quotient_map=analytic.physical_quotient_map,
        physical_quotient_metric=analytic.physical_quotient_metric,
        target_physical_representatives=(analytic.target_physical_representatives),
        coverage_control_id=analytic.coverage_control_id,
        coverage_control_wire=analytic.coverage_control_wire,
        undressed_response_representatives=(
            analytic.undressed_response_representatives
        ),
        gauge_basis=analytic.gauge_basis,
        gauge_amplitude=analytic.gauge_amplitude,
        expected_graph_rank=analytic.expected_graph_rank,
        analytic_graph_singular_values=analytic.analytic_graph_singular_values,
        fejer_graph_slope_formula_id=(analytic.fejer_graph_slope_formula_id),
        expected_actual_raw_graph_singular_values=(
            analytic.expected_actual_raw_graph_singular_values
        ),
        expected_ablated_raw_graph_singular_values=(
            analytic.expected_ablated_raw_graph_singular_values
        ),
        observer_collapse_spec=None,
        geometry_bundle_sha="0" * 64,
    )
    bundle = replace(
        bundle0,
        geometry_bundle_sha=sha_builder(
            scenario_response_geometry_bundle_v3_payload(bundle0)
        ),
    )
    verify_geometry_analytic_context_v2(context)
    verify_scenario_response_geometry_bundle_v3_for_context(context, bundle)
    return context, bundle


def _make_resolved_geometry_compiler(
    *,
    context_bundle_builder=_build_context_and_bundle,
    record_type=RepositoryClosedGeometryCompilationV1,
    payload_builder=repository_closed_geometry_compilation_v1_payload,
    body_verifier=_verify_compilation_body,
    sha_builder=canonical_sha,
    replace_record=replace,
):
    """Close recursive C16→C15 compilation over immutable dependencies."""

    def compile_resolved(
        parent_manifest,
        permit_body,
        materialization_body,
        resolved_c15_references,
        *,
        analytic_rebuilder,
    ):
        context, bundle = context_bundle_builder(
            parent_manifest,
            permit_body,
            materialization_body,
            resolved_c15_references,
            analytic_rebuilder=analytic_rebuilder,
            sha_builder=sha_builder,
        )
        c15_compilation_shas: tuple[str, ...] = ()
        if context.geometry_kind == C16_COVERAGE_CONTROL:
            references = tuple(
                compile_resolved(
                    parent_manifest,
                    reference_permit,
                    reference_materialization,
                    resolved_c15_references,
                    analytic_rebuilder=analytic_rebuilder,
                )
                for reference_permit, reference_materialization in (
                    resolved_c15_references
                )
            )
            c15_compilation_shas = tuple(item.compilation_sha for item in references)
        provisional = record_type(
            compilation_schema_version=(
                REPOSITORY_CLOSED_GEOMETRY_COMPILATION_V1_SCHEMA_VERSION
            ),
            authority_state=REPOSITORY_CLOSED_GEOMETRY_COMPILATION_AUTHORITY_STATE,
            formal_parent_v2_sha=parent_manifest.parent_freeze_v2_sha,
            permit_v2_sha=permit_body.permit_sha,
            materialization_v2_sha=materialization_body.materialization_v2_sha,
            geometry_kind=context.geometry_kind,
            c15_reference_compilation_shas=c15_compilation_shas,
            analytic_context=context,
            geometry_bundle=bundle,
            response_evidence_state=GEOMETRY_PRE_RESPONSE_EVIDENCE_STATE,
            scientific_verdict_state=GEOMETRY_SCIENTIFIC_VERDICT_STATE,
            compilation_sha="0" * 64,
        )
        result = replace_record(
            provisional,
            compilation_sha=sha_builder(payload_builder(provisional)),
        )
        return body_verifier(result, sha_builder=sha_builder)

    return compile_resolved


_compile_resolved_geometry = _make_resolved_geometry_compiler()


def _validate_upstream_tuple(value: object, field: str) -> tuple[object, object]:
    if type(value) is not tuple or len(value) != 2:
        raise TypeError(f"{field} must be an exact (permit, materialization) tuple")
    return value


def _make_repository_closed_geometry_api(
    *,
    parent_type,
    permit_type,
    materialization_type,
    parent_reverifier,
    permit_parent_reverifier,
    materialization_upstream_reverifier,
    analytic_rebuilder,
    compile_resolved=_compile_resolved_geometry,
    verify_body=_verify_compilation_body,
    upstream_tuple_validator=_validate_upstream_tuple,
    call_graph_freezer=freeze_rulespace_call_graph,
):
    """Build a closed public facade; dependency injection is test-only."""

    exact_type = type

    def resolve(formal_parent_v2, permit_v2, materialization_v2):
        if exact_type(formal_parent_v2) is not parent_type:
            raise TypeError("formal_parent_v2 must be an exact live Parent-v2")
        if exact_type(permit_v2) is not permit_type:
            raise TypeError("permit_v2 must be an exact live permit-v2")
        if exact_type(materialization_v2) is not materialization_type:
            raise TypeError(
                "materialization_v2 must be an exact live materialization-v2"
            )
        parent_manifest = parent_reverifier(formal_parent_v2)
        permit_body = permit_parent_reverifier(permit_v2, formal_parent_v2)
        materialization_body = materialization_upstream_reverifier(
            formal_parent_v2,
            permit_v2,
            materialization_v2,
        )
        return parent_manifest, permit_body, materialization_body

    def resolve_references(formal_parent_v2, references):
        if type(references) is not tuple:
            raise TypeError("c15_reference_upstreams must be an exact tuple")
        result = []
        for index, value in enumerate(references):
            reference_permit, reference_materialization = upstream_tuple_validator(
                value,
                f"c15_reference_upstreams[{index}]",
            )
            _, permit_body, materialization_body = resolve(
                formal_parent_v2,
                reference_permit,
                reference_materialization,
            )
            result.append((permit_body, materialization_body))
        return tuple(result)

    def compile_repository_closed_geometry_v1(
        formal_parent_v2,
        permit_v2,
        materialization_v2,
        *,
        c15_reference_upstreams=(),
    ):
        parent_manifest, permit_body, materialization_body = resolve(
            formal_parent_v2,
            permit_v2,
            materialization_v2,
        )
        references = resolve_references(
            formal_parent_v2,
            c15_reference_upstreams,
        )
        return compile_resolved(
            parent_manifest,
            permit_body,
            materialization_body,
            references,
            analytic_rebuilder=analytic_rebuilder,
        )

    def verify_repository_closed_geometry_compilation_v1(
        formal_parent_v2,
        permit_v2,
        materialization_v2,
        compilation,
        *,
        c15_reference_upstreams=(),
    ):
        verify_body(compilation)
        expected = compile_repository_closed_geometry_v1(
            formal_parent_v2,
            permit_v2,
            materialization_v2,
            c15_reference_upstreams=c15_reference_upstreams,
        )
        if compilation != expected:
            raise ValueError("geometry compilation differs from closed live replay")
        return compilation

    def compile_repository_closed_geometry_batch_v1(
        formal_parent_v2,
        ordered_upstreams,
    ):
        if type(ordered_upstreams) is not tuple or len(ordered_upstreams) != len(
            CANONICAL_GEOMETRY_PRODUCTION_SCENARIO_IDS
        ):
            raise ValueError("geometry batch requires exactly eight ordered upstreams")
        c15_references = ordered_upstreams[:4]
        results = []
        for index, upstream in enumerate(ordered_upstreams):
            permit_v2, materialization_v2 = upstream_tuple_validator(
                upstream,
                f"ordered_upstreams[{index}]",
            )
            expected_scenario = CANONICAL_GEOMETRY_PRODUCTION_SCENARIO_IDS[index]
            result = compile_repository_closed_geometry_v1(
                formal_parent_v2,
                permit_v2,
                materialization_v2,
                c15_reference_upstreams=(c15_references if index < 6 else ()),
            )
            if result.analytic_context.scenario_id != expected_scenario:
                raise ValueError("geometry batch upstreams are not in canonical order")
            results.append(result)
        return tuple(results)

    return tuple(
        call_graph_freezer(item)
        for item in (
            compile_repository_closed_geometry_v1,
            verify_repository_closed_geometry_compilation_v1,
            compile_repository_closed_geometry_batch_v1,
        )
    )


(
    compile_repository_closed_geometry_v1,
    verify_repository_closed_geometry_compilation_v1,
    compile_repository_closed_geometry_batch_v1,
) = _make_repository_closed_geometry_api(
    parent_type=VerifiedParentFreezeV2,
    permit_type=VerifiedCalibrationApplicationPermitV2,
    materialization_type=VerifiedV3M0ApplicationScenarioMaterializationV2,
    parent_reverifier=require_current_parent,
    permit_parent_reverifier=_require_calibration_application_permit_v2_for_parent,
    materialization_upstream_reverifier=(
        _require_application_scenario_materialization_v2_for_upstream
    ),
    analytic_rebuilder=_production_analytic_rebuilder,
)


__all__ = [
    "CANONICAL_GEOMETRY_PRODUCTION_SCENARIO_IDS",
    "C19_PRODUCTION_EVALUATION_STATE",
    "GEOMETRY_PRE_RESPONSE_EVIDENCE_STATE",
    "GEOMETRY_SCIENTIFIC_VERDICT_STATE",
    "GeometryProductionCompilationUnavailable",
    "REPOSITORY_CLOSED_GEOMETRY_COMPILATION_AUTHORITY_STATE",
    "REPOSITORY_CLOSED_GEOMETRY_COMPILATION_V1_SCHEMA_VERSION",
    "RepositoryClosedGeometryCompilationV1",
    "compile_repository_closed_geometry_batch_v1",
    "compile_repository_closed_geometry_v1",
    "repository_closed_geometry_compilation_v1_payload",
    "verify_repository_closed_geometry_compilation_v1",
]
