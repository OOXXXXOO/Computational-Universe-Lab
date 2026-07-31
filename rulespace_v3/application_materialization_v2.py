"""Exact scenario-bound application materialization contract for Parent-v2.

The raw records in this module are authority-neutral.  They freeze the formal
scenario lineage, local-shear recipe, scenario selectors, mechanically derived
source/readout maps, construction trace and both factory bindings.  Only an
opaque capability produced by a closed replay of a live Parent-v2 and live
permit-v2 may be consumed downstream.

The compiler consumes only a live Parent-v2 and live permit-v2.  It resolves
the exact current application/scenario authority, replays its reviewed local
recipe, lowers the ordered scalar layers through the real factory executor,
and constructs the matched ablation before any response evolution begins.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, replace
import math
import re
import struct
import sympy as sp
from typing import Literal
from weakref import WeakKeyDictionary

import numpy as np

from .ablation import (
    AblationConstructionOutcome,
    _verify_construction_outcome,
    matched_ablation,
    verify_ablation_pair,
)
from .calibration_authority import (
    _verify_c04_canonical_angle_recipe,
    build_c04_canonical_angle_recipe,
    c04_local_shear_step_payload,
)
from .candidate_scenario_dag import (
    extract_candidate_scenario_contract,
    verify_compiled_candidate_scenario_contract,
)
from .evidence import canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    PrimitiveInterface,
    PrimitiveOperatorWire,
    VerifiedFactory,
    _reverify_verified_factory,
    basis_manifest_array,
    basis_manifest_payload,
    build_basis_manifest,
    build_factory_from_trace,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_basis_manifest,
    verify_frozen_tensor,
)
from .parent_freeze import issue_v3m0_parent_freeze
from .parent_candidate_v2 import (
    CandidateV2ScenarioRefreeze,
    candidate_v2_scenario_refreeze_payload,
)
from .parent_v2_contracts import (
    CurrentApplicationAuthorityV2,
    CurrentScenarioAuthorityV2,
    CurrentScenarioResponseContractV2,
    current_application_authority_v2_payload,
    current_scenario_authority_v2_payload,
    current_scenario_response_contract_v2_payload,
)
from .task8_control_replay import _build_task8_controls
from .trace import (
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
)


SCENARIO_LOCAL_SHEAR_STEP_V2_SCHEMA_VERSION = "v3m0.scenario-local-shear-step.v2"
SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION = "v3m0.scenario-construction-effect.v2"
SCENARIO_CONSTRUCTION_RECIPE_V2_SCHEMA_VERSION = "v3m0.scenario-construction-recipe.v2"
SCENARIO_CONSTRUCTION_TRACE_V2_SCHEMA_VERSION = "v3m0.scenario-construction-trace.v2"
SCENARIO_FACTORY_BINDING_V2_SCHEMA_VERSION = "v3m0.scenario-factory-binding.v2"
APPLICATION_SCENARIO_MATERIALIZATION_V2_SCHEMA_VERSION = (
    "v3m0.application-scenario-materialization.v2"
)
APPLICATION_SCENARIO_MATERIALIZATION_V2_STATE = "FORMAL_PARENT_V2_LIVE_MATERIALIZED"
SELECTOR_RESIDUAL_TOLERANCE = 1.0e-12

UPSTREAM_V2_WIRING_POINTS = (
    "rulespace_v3.parent_authority.VerifiedParentFreezeV2",
    "rulespace_v3.parent_authority.require_current_parent",
    "rulespace_v3.application_authority_v2.VerifiedCalibrationApplicationPermitV2",
    "rulespace_v3.application_authority_v2.require_calibration_application_permit_v2",
    "closed permit-v2 to expected-Parent-v2 identity bridge",
)

_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ApplicationMaterializationV2UpstreamUnavailable(RuntimeError):
    """The exact live permit-v2/construction replay is not connected."""


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


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an exact int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


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


def _fp64_equal(left: float, right: float) -> bool:
    return struct.pack(">d", left) == struct.pack(">d", right)


def _string_tuple(
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
    if len(result) != len(set(result)):
        raise ValueError(f"{field} must contain unique values")
    return result


def _state_shape(value: object, field: str) -> tuple[int, ...]:
    if type(value) is not tuple or len(value) < 2:
        raise ValueError(f"{field} must include channel and spatial axes")
    result = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise TypeError(f"{field}[{index}] must be an exact int")
        if item <= 0:
            raise ValueError(f"{field}[{index}] must be positive")
        result.append(item)
    return tuple(result)


def _target_blind_parameters(
    value: object,
) -> tuple[tuple[str, float], ...]:
    if type(value) is not tuple:
        raise TypeError("target_blind_parameters must be an exact tuple")
    result = []
    names = []
    for index, item in enumerate(value):
        if type(item) is not tuple or len(item) != 2:
            raise TypeError(f"target_blind_parameters[{index}] must be a pair")
        name = _text(item[0], f"target_blind_parameters[{index}][0]")
        number = _finite_float(item[1], f"target_blind_parameters[{index}][1]")
        names.append(name)
        result.append((name, number))
    answer = tuple(result)
    if names != sorted(set(names)):
        raise ValueError("target_blind_parameters must be unique canonical order")
    return answer


@dataclass(frozen=True)
class ScenarioLocalShearStepV2:
    """One ordered, strictly local real-space canonical shear."""

    step_schema_version: str
    scenario_id: str
    step_id: str
    ordinal: int
    source_channel: str
    destination_channel: str
    offset: tuple[int, ...]
    coefficient_wire: tuple[float, float]
    target_conditioned: bool
    step_sha: str

    def __post_init__(self) -> None:
        if self.step_schema_version != SCENARIO_LOCAL_SHEAR_STEP_V2_SCHEMA_VERSION:
            raise ValueError("local shear step schema drifted")
        _text(self.scenario_id, "scenario_id")
        _text(self.step_id, "step_id")
        if type(self.ordinal) is not int or self.ordinal < 0:
            raise ValueError("step ordinal must be a non-negative exact int")
        _text(self.source_channel, "source_channel")
        _text(self.destination_channel, "destination_channel")
        if self.source_channel == self.destination_channel:
            raise ValueError("local shear source and destination must differ")
        if type(self.offset) is not tuple or not self.offset:
            raise ValueError("local shear offset must be a non-empty tuple")
        if not all(type(item) is int for item in self.offset):
            raise TypeError("local shear offset must contain exact ints")
        if type(self.coefficient_wire) is not tuple or len(self.coefficient_wire) != 2:
            raise ValueError("coefficient_wire must be an exact complex pair")
        real = _finite_float(self.coefficient_wire[0], "coefficient_wire[0]")
        imag = _finite_float(self.coefficient_wire[1], "coefficient_wire[1]")
        if real == 0.0 and imag == 0.0:
            raise ValueError("local shear coefficient must be nonzero")
        if type(self.target_conditioned) is not bool:
            raise TypeError("target_conditioned must be an exact bool")
        _sha(self.step_sha, "step_sha")


def scenario_local_shear_step_v2_payload(
    step: ScenarioLocalShearStepV2,
) -> dict[str, object]:
    _exact_record(step, ScenarioLocalShearStepV2, "local shear step")
    return {
        "step_schema_version": step.step_schema_version,
        "scenario_id": step.scenario_id,
        "step_id": step.step_id,
        "ordinal": step.ordinal,
        "source_channel": step.source_channel,
        "destination_channel": step.destination_channel,
        "offset": list(step.offset),
        "coefficient_wire": list(step.coefficient_wire),
        "target_conditioned": step.target_conditioned,
    }


def _verify_step(step: ScenarioLocalShearStepV2) -> ScenarioLocalShearStepV2:
    _exact_record(step, ScenarioLocalShearStepV2, "local shear step")
    step.__post_init__()
    if step.step_sha != canonical_sha(scenario_local_shear_step_v2_payload(step)):
        raise ValueError("local shear step SHA does not match its body")
    return step


@dataclass(frozen=True)
class ScenarioConstructionEffectV2:
    effect_schema_version: str
    branch: Literal["actual", "matched_ablated"]
    scenario_id: str
    scenario_sha: str
    construction_rule_id: str
    construction_family_id: str
    ordered_steps: tuple[ScenarioLocalShearStepV2, ...]
    program_sha: str
    effect_digest: str

    def __post_init__(self) -> None:
        if self.effect_schema_version != SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION:
            raise ValueError("construction effect schema drifted")
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("construction effect branch is not closed")
        _text(self.scenario_id, "scenario_id")
        _sha(self.scenario_sha, "scenario_sha")
        _text(self.construction_rule_id, "construction_rule_id")
        _text(self.construction_family_id, "construction_family_id")
        if type(self.ordered_steps) is not tuple or not self.ordered_steps:
            raise ValueError("construction effect must contain local steps")
        if not all(
            type(item) is ScenarioLocalShearStepV2 for item in self.ordered_steps
        ):
            raise TypeError("construction effect steps have the wrong strict type")
        _sha(self.program_sha, "program_sha")
        _sha(self.effect_digest, "effect_digest")


def _effect_program_sha(effect: ScenarioConstructionEffectV2) -> str:
    return canonical_sha(
        {
            "scenario_id": effect.scenario_id,
            "branch": effect.branch,
            "ordered_step_shas": [item.step_sha for item in effect.ordered_steps],
        }
    )


def scenario_construction_effect_v2_payload(
    effect: ScenarioConstructionEffectV2,
) -> dict[str, object]:
    _exact_record(effect, ScenarioConstructionEffectV2, "construction effect")
    return {
        "effect_schema_version": effect.effect_schema_version,
        "branch": effect.branch,
        "scenario_id": effect.scenario_id,
        "scenario_sha": effect.scenario_sha,
        "construction_rule_id": effect.construction_rule_id,
        "construction_family_id": effect.construction_family_id,
        "ordered_steps": [
            {
                **scenario_local_shear_step_v2_payload(item),
                "step_sha": item.step_sha,
            }
            for item in effect.ordered_steps
        ],
        "program_sha": effect.program_sha,
    }


def _verify_effect(
    effect: ScenarioConstructionEffectV2,
) -> ScenarioConstructionEffectV2:
    _exact_record(effect, ScenarioConstructionEffectV2, "construction effect")
    effect.__post_init__()
    for step in effect.ordered_steps:
        _verify_step(step)
        if step.scenario_id != effect.scenario_id:
            raise ValueError("construction effect step is spliced across scenarios")
    ordinals = tuple(item.ordinal for item in effect.ordered_steps)
    if ordinals != tuple(sorted(set(ordinals))):
        raise ValueError("construction effect step order is not canonical")
    if effect.program_sha != _effect_program_sha(effect):
        raise ValueError("construction effect program SHA drifted")
    if effect.effect_digest != canonical_sha(
        scenario_construction_effect_v2_payload(effect)
    ):
        raise ValueError("construction effect digest does not match its body")
    return effect


def scenario_selector_v2_sha(
    source_selector: FrozenComplexTensor,
    readout_selector: FrozenComplexTensor,
) -> str:
    return canonical_sha(
        {
            "selector_schema_version": "v3m0.scenario-selector.v2",
            "source_selector": _tensor_record(source_selector),
            "readout_selector": _tensor_record(readout_selector),
        }
    )


@dataclass(frozen=True)
class ScenarioConstructionRecipeV2:
    recipe_schema_version: str
    recipe_state: Literal["FORMAL_SCENARIO_AUTHORITY_DERIVED"]
    formal_parent_v2_sha: str
    permit_v2_sha: str
    application_spec_sha: str
    scenario_authority_sha: str
    response_contract_sha: str
    control_case_id: str
    application_instance_id: str
    scenario_id: str
    scenario_sha: str
    selector_sha: str
    operation_dag_sha: str
    compiled_contract_sha: str
    construction_rule_id: str
    construction_family_id: str
    primitive_support_radius: int
    uses_global_fft_projection: Literal[False]
    uses_per_k_time_step_projector: Literal[False]
    source_selector: FrozenComplexTensor
    readout_selector: FrozenComplexTensor
    actual_effect: ScenarioConstructionEffectV2
    matched_ablated_effect: ScenarioConstructionEffectV2
    recipe_sha: str

    def __post_init__(self) -> None:
        if self.recipe_schema_version != SCENARIO_CONSTRUCTION_RECIPE_V2_SCHEMA_VERSION:
            raise ValueError("scenario construction recipe schema drifted")
        if self.recipe_state != "FORMAL_SCENARIO_AUTHORITY_DERIVED":
            raise ValueError("scenario construction recipe state is not formal")
        for field in (
            "formal_parent_v2_sha",
            "permit_v2_sha",
            "application_spec_sha",
            "scenario_authority_sha",
            "response_contract_sha",
            "scenario_sha",
            "selector_sha",
            "operation_dag_sha",
            "compiled_contract_sha",
            "recipe_sha",
        ):
            _sha(getattr(self, field), field)
        for field in (
            "control_case_id",
            "application_instance_id",
            "scenario_id",
            "construction_rule_id",
            "construction_family_id",
        ):
            _text(getattr(self, field), field)
        if type(self.primitive_support_radius) is not int:
            raise TypeError("primitive_support_radius must be an exact int")
        if self.primitive_support_radius < 0:
            raise ValueError("primitive_support_radius must be non-negative")
        if self.uses_global_fft_projection is not False:
            raise ValueError("global FFT projection is forbidden")
        if self.uses_per_k_time_step_projector is not False:
            raise ValueError("per-k timestep projection is forbidden")


def scenario_construction_recipe_v2_payload(
    recipe: ScenarioConstructionRecipeV2,
) -> dict[str, object]:
    _exact_record(recipe, ScenarioConstructionRecipeV2, "construction recipe")
    return {
        "recipe_schema_version": recipe.recipe_schema_version,
        "recipe_state": recipe.recipe_state,
        "formal_parent_v2_sha": recipe.formal_parent_v2_sha,
        "permit_v2_sha": recipe.permit_v2_sha,
        "application_spec_sha": recipe.application_spec_sha,
        "scenario_authority_sha": recipe.scenario_authority_sha,
        "response_contract_sha": recipe.response_contract_sha,
        "control_case_id": recipe.control_case_id,
        "application_instance_id": recipe.application_instance_id,
        "scenario_id": recipe.scenario_id,
        "scenario_sha": recipe.scenario_sha,
        "selector_sha": recipe.selector_sha,
        "operation_dag_sha": recipe.operation_dag_sha,
        "compiled_contract_sha": recipe.compiled_contract_sha,
        "construction_rule_id": recipe.construction_rule_id,
        "construction_family_id": recipe.construction_family_id,
        "primitive_support_radius": recipe.primitive_support_radius,
        "uses_global_fft_projection": recipe.uses_global_fft_projection,
        "uses_per_k_time_step_projector": (recipe.uses_per_k_time_step_projector),
        "source_selector": _tensor_record(recipe.source_selector),
        "readout_selector": _tensor_record(recipe.readout_selector),
        "actual_effect": {
            **scenario_construction_effect_v2_payload(recipe.actual_effect),
            "effect_digest": recipe.actual_effect.effect_digest,
        },
        "matched_ablated_effect": {
            **scenario_construction_effect_v2_payload(recipe.matched_ablated_effect),
            "effect_digest": recipe.matched_ablated_effect.effect_digest,
        },
    }


def _verify_recipe(
    recipe: ScenarioConstructionRecipeV2,
) -> ScenarioConstructionRecipeV2:
    _exact_record(recipe, ScenarioConstructionRecipeV2, "construction recipe")
    recipe.__post_init__()
    _exact_tensor(recipe.source_selector, "source_selector")
    _exact_tensor(recipe.readout_selector, "readout_selector")
    if recipe.selector_sha != scenario_selector_v2_sha(
        recipe.source_selector,
        recipe.readout_selector,
    ):
        raise ValueError("scenario selector SHA does not match selector tensors")
    actual = _verify_effect(recipe.actual_effect)
    matched = _verify_effect(recipe.matched_ablated_effect)
    for effect, branch in ((actual, "actual"), (matched, "matched_ablated")):
        if effect.branch != branch:
            raise ValueError("construction effect branch is spliced")
        if (
            effect.scenario_id != recipe.scenario_id
            or effect.scenario_sha != recipe.scenario_sha
            or effect.construction_rule_id != recipe.construction_rule_id
            or effect.construction_family_id != recipe.construction_family_id
        ):
            raise ValueError("construction effect is spliced across recipe lineage")
    expected_matched = tuple(
        item for item in actual.ordered_steps if not item.target_conditioned
    )
    if not any(item.target_conditioned for item in actual.ordered_steps):
        raise ValueError("actual recipe lacks a target-conditioned local shear")
    if matched.ordered_steps != expected_matched:
        raise ValueError("matched effect is not mechanical conditioned deletion")
    if actual.effect_digest == matched.effect_digest:
        raise ValueError("actual and matched effects must be distinct")
    maximum_radius = max(
        abs(coordinate) for step in actual.ordered_steps for coordinate in step.offset
    )
    if maximum_radius > recipe.primitive_support_radius:
        raise ValueError("recipe local support exceeds primitive_support_radius")
    if recipe.recipe_sha != canonical_sha(
        scenario_construction_recipe_v2_payload(recipe)
    ):
        raise ValueError("scenario construction recipe SHA does not match its body")
    return recipe


@dataclass(frozen=True)
class ScenarioConstructionTraceV2:
    trace_schema_version: str
    trace_state: Literal["FORMAL_RECIPE_REPLAYED_PRE_EVOLUTION"]
    scenario_id: str
    scenario_sha: str
    recipe_sha: str
    operation_dag_sha: str
    compiled_contract_sha: str
    construction_rule_id: str
    construction_family_id: str
    target_spec_id: str
    target_spec_sha: str
    interface_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    state_shape: tuple[int, ...]
    dt: float
    target_blind_parameters: tuple[tuple[str, float], ...]
    boundary_manifest_id: Literal["periodic-v1"]
    actual_step_shas: tuple[str, ...]
    matched_ablated_step_shas: tuple[str, ...]
    actual_program_sha: str
    matched_ablated_program_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    construction_trace_sha: str

    def __post_init__(self) -> None:
        if self.trace_schema_version != SCENARIO_CONSTRUCTION_TRACE_V2_SCHEMA_VERSION:
            raise ValueError("scenario construction trace schema drifted")
        if self.trace_state != "FORMAL_RECIPE_REPLAYED_PRE_EVOLUTION":
            raise ValueError("scenario construction trace state drifted")
        for field in (
            "scenario_id",
            "construction_rule_id",
            "construction_family_id",
            "target_spec_id",
            "state_schema_id",
        ):
            _text(getattr(self, field), field)
        for field in (
            "scenario_sha",
            "recipe_sha",
            "operation_dag_sha",
            "compiled_contract_sha",
            "target_spec_sha",
            "interface_sha",
            "actual_program_sha",
            "matched_ablated_program_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "construction_trace_sha",
        ):
            _sha(getattr(self, field), field)
        _string_tuple(self.channel_order, "channel_order")
        shape = _state_shape(self.state_shape, "state_shape")
        if shape[0] != len(self.channel_order):
            raise ValueError("state_shape channel axis differs from channel_order")
        if _finite_float(self.dt, "dt") <= 0.0:
            raise ValueError("dt must be positive")
        _target_blind_parameters(self.target_blind_parameters)
        if self.boundary_manifest_id != "periodic-v1":
            raise ValueError("boundary manifest is not periodic-v1")
        for field in ("actual_step_shas", "matched_ablated_step_shas"):
            values = _string_tuple(getattr(self, field), field)
            for index, value in enumerate(values):
                _sha(value, f"{field}[{index}]")


def scenario_construction_trace_v2_payload(
    trace: ScenarioConstructionTraceV2,
) -> dict[str, object]:
    _exact_record(trace, ScenarioConstructionTraceV2, "construction trace")
    return {
        "trace_schema_version": trace.trace_schema_version,
        "trace_state": trace.trace_state,
        "scenario_id": trace.scenario_id,
        "scenario_sha": trace.scenario_sha,
        "recipe_sha": trace.recipe_sha,
        "operation_dag_sha": trace.operation_dag_sha,
        "compiled_contract_sha": trace.compiled_contract_sha,
        "construction_rule_id": trace.construction_rule_id,
        "construction_family_id": trace.construction_family_id,
        "target_spec_id": trace.target_spec_id,
        "target_spec_sha": trace.target_spec_sha,
        "interface_sha": trace.interface_sha,
        "state_schema_id": trace.state_schema_id,
        "channel_order": list(trace.channel_order),
        "state_shape": list(trace.state_shape),
        "dt": trace.dt,
        "target_blind_parameters": [
            [name, value] for name, value in trace.target_blind_parameters
        ],
        "boundary_manifest_id": trace.boundary_manifest_id,
        "actual_step_shas": list(trace.actual_step_shas),
        "matched_ablated_step_shas": list(trace.matched_ablated_step_shas),
        "actual_program_sha": trace.actual_program_sha,
        "matched_ablated_program_sha": trace.matched_ablated_program_sha,
        "actual_effect_digest": trace.actual_effect_digest,
        "matched_ablated_effect_digest": trace.matched_ablated_effect_digest,
    }


def _verify_trace(
    trace: ScenarioConstructionTraceV2,
) -> ScenarioConstructionTraceV2:
    _exact_record(trace, ScenarioConstructionTraceV2, "construction trace")
    trace.__post_init__()
    if trace.construction_trace_sha != canonical_sha(
        scenario_construction_trace_v2_payload(trace)
    ):
        raise ValueError("construction trace SHA does not match its body")
    return trace


@dataclass(frozen=True)
class ScenarioFactoryBindingV2:
    binding_schema_version: str
    branch: Literal["actual", "matched_ablated"]
    scenario_id: str
    scenario_sha: str
    recipe_sha: str
    construction_trace_sha: str
    program_sha: str
    effect_digest: str
    factory_sha: str
    runtime_operator_sha: str
    interface_sha: str
    state_schema_id: str
    state_shape: tuple[int, ...]
    source_manifest_id: str
    readout_manifest_id: str
    factory_binding_sha: str

    def __post_init__(self) -> None:
        if self.binding_schema_version != SCENARIO_FACTORY_BINDING_V2_SCHEMA_VERSION:
            raise ValueError("scenario factory binding schema drifted")
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("scenario factory binding branch is not closed")
        _text(self.scenario_id, "scenario_id")
        _text(self.state_schema_id, "state_schema_id")
        for field in (
            "scenario_sha",
            "recipe_sha",
            "construction_trace_sha",
            "program_sha",
            "effect_digest",
            "factory_sha",
            "runtime_operator_sha",
            "interface_sha",
            "source_manifest_id",
            "readout_manifest_id",
            "factory_binding_sha",
        ):
            _sha(getattr(self, field), field)
        _state_shape(self.state_shape, "state_shape")


def scenario_factory_binding_v2_payload(
    binding: ScenarioFactoryBindingV2,
) -> dict[str, object]:
    _exact_record(binding, ScenarioFactoryBindingV2, "factory binding")
    return {
        "binding_schema_version": binding.binding_schema_version,
        "branch": binding.branch,
        "scenario_id": binding.scenario_id,
        "scenario_sha": binding.scenario_sha,
        "recipe_sha": binding.recipe_sha,
        "construction_trace_sha": binding.construction_trace_sha,
        "program_sha": binding.program_sha,
        "effect_digest": binding.effect_digest,
        "factory_sha": binding.factory_sha,
        "runtime_operator_sha": binding.runtime_operator_sha,
        "interface_sha": binding.interface_sha,
        "state_schema_id": binding.state_schema_id,
        "state_shape": list(binding.state_shape),
        "source_manifest_id": binding.source_manifest_id,
        "readout_manifest_id": binding.readout_manifest_id,
    }


def _verify_factory_binding(
    binding: ScenarioFactoryBindingV2,
) -> ScenarioFactoryBindingV2:
    _exact_record(binding, ScenarioFactoryBindingV2, "factory binding")
    binding.__post_init__()
    if binding.factory_binding_sha != canonical_sha(
        scenario_factory_binding_v2_payload(binding)
    ):
        raise ValueError("factory binding SHA does not match its body")
    return binding


@dataclass(frozen=True)
class ApplicationScenarioMaterializationV2:
    materialization_schema_version: str
    materialization_state: Literal["FORMAL_PARENT_V2_LIVE_MATERIALIZED"]
    formal_parent_v2_sha: str
    permit_v2_sha: str
    application_authority_sha: str
    application_spec_sha: str
    control_case_id: str
    application_instance_id: str
    scenario_authority_sha: str
    response_contract_sha: str
    scenario_id: str
    scenario_sha: str
    selected_fejer_order: int
    common_source_basis: BasisManifest
    common_readout_basis: BasisManifest
    scenario_recipe: ScenarioConstructionRecipeV2
    scenario_source_injection: FrozenComplexTensor
    scenario_readout_coisometry: FrozenComplexTensor
    scenario_source_basis: BasisManifest
    scenario_readout_basis: BasisManifest
    construction_trace: ScenarioConstructionTraceV2
    actual_factory_binding: ScenarioFactoryBindingV2
    matched_ablated_factory_binding: ScenarioFactoryBindingV2
    materialization_v2_sha: str

    def __post_init__(self) -> None:
        if (
            self.materialization_schema_version
            != APPLICATION_SCENARIO_MATERIALIZATION_V2_SCHEMA_VERSION
        ):
            raise ValueError("application scenario materialization-v2 schema drifted")
        if self.materialization_state != APPLICATION_SCENARIO_MATERIALIZATION_V2_STATE:
            raise ValueError("application scenario materialization-v2 state drifted")
        for field in (
            "formal_parent_v2_sha",
            "permit_v2_sha",
            "application_authority_sha",
            "application_spec_sha",
            "scenario_authority_sha",
            "response_contract_sha",
            "scenario_sha",
            "materialization_v2_sha",
        ):
            _sha(getattr(self, field), field)
        for field in (
            "control_case_id",
            "application_instance_id",
            "scenario_id",
        ):
            _text(getattr(self, field), field)
        _positive_int(self.selected_fejer_order, "selected_fejer_order")


def application_scenario_materialization_v2_payload(
    materialization: ApplicationScenarioMaterializationV2,
) -> dict[str, object]:
    _exact_record(
        materialization,
        ApplicationScenarioMaterializationV2,
        "application scenario materialization-v2",
    )
    recipe = materialization.scenario_recipe
    trace = materialization.construction_trace
    actual = materialization.actual_factory_binding
    matched = materialization.matched_ablated_factory_binding
    return {
        "materialization_schema_version": (
            materialization.materialization_schema_version
        ),
        "materialization_state": materialization.materialization_state,
        "formal_parent_v2_sha": materialization.formal_parent_v2_sha,
        "permit_v2_sha": materialization.permit_v2_sha,
        "application_authority_sha": materialization.application_authority_sha,
        "application_spec_sha": materialization.application_spec_sha,
        "control_case_id": materialization.control_case_id,
        "application_instance_id": materialization.application_instance_id,
        "scenario_authority_sha": materialization.scenario_authority_sha,
        "response_contract_sha": materialization.response_contract_sha,
        "scenario_id": materialization.scenario_id,
        "scenario_sha": materialization.scenario_sha,
        "selected_fejer_order": materialization.selected_fejer_order,
        "common_source_basis": _basis_record(materialization.common_source_basis),
        "common_readout_basis": _basis_record(materialization.common_readout_basis),
        "scenario_recipe": {
            **scenario_construction_recipe_v2_payload(recipe),
            "recipe_sha": recipe.recipe_sha,
        },
        "scenario_source_injection": _tensor_record(
            materialization.scenario_source_injection
        ),
        "scenario_readout_coisometry": _tensor_record(
            materialization.scenario_readout_coisometry
        ),
        "scenario_source_basis": _basis_record(materialization.scenario_source_basis),
        "scenario_readout_basis": _basis_record(materialization.scenario_readout_basis),
        "construction_trace": {
            **scenario_construction_trace_v2_payload(trace),
            "construction_trace_sha": trace.construction_trace_sha,
        },
        "actual_factory_binding": {
            **scenario_factory_binding_v2_payload(actual),
            "factory_binding_sha": actual.factory_binding_sha,
        },
        "matched_ablated_factory_binding": {
            **scenario_factory_binding_v2_payload(matched),
            "factory_binding_sha": matched.factory_binding_sha,
        },
    }


def _verify_recipe_lineage(
    materialization: ApplicationScenarioMaterializationV2,
) -> ScenarioConstructionRecipeV2:
    recipe = materialization.scenario_recipe
    _exact_record(recipe, ScenarioConstructionRecipeV2, "scenario recipe")
    if (
        recipe.formal_parent_v2_sha != materialization.formal_parent_v2_sha
        or recipe.permit_v2_sha != materialization.permit_v2_sha
        or recipe.application_spec_sha != materialization.application_spec_sha
        or recipe.scenario_authority_sha != materialization.scenario_authority_sha
        or recipe.response_contract_sha != materialization.response_contract_sha
        or recipe.control_case_id != materialization.control_case_id
        or recipe.application_instance_id != materialization.application_instance_id
        or recipe.scenario_id != materialization.scenario_id
        or recipe.scenario_sha != materialization.scenario_sha
    ):
        raise ValueError("scenario recipe is spliced across formal lineage")
    return _verify_recipe(recipe)


def _verify_scenario_basis_derivation(
    materialization: ApplicationScenarioMaterializationV2,
    recipe: ScenarioConstructionRecipeV2,
    trace: ScenarioConstructionTraceV2,
) -> None:
    common_source = _exact_basis(
        materialization.common_source_basis,
        "common_source_basis",
    )
    common_readout = _exact_basis(
        materialization.common_readout_basis,
        "common_readout_basis",
    )
    scenario_source = _exact_basis(
        materialization.scenario_source_basis,
        "scenario_source_basis",
    )
    scenario_readout = _exact_basis(
        materialization.scenario_readout_basis,
        "scenario_readout_basis",
    )
    if common_source.role != "source" or common_readout.role != "readout":
        raise ValueError("common case basis roles drifted")
    if scenario_source.role != "source" or scenario_readout.role != "readout":
        raise ValueError("scenario basis roles drifted")
    for basis in (common_source, common_readout, scenario_source, scenario_readout):
        if (
            basis.state_schema_id != trace.state_schema_id
            or basis.channel_order != trace.channel_order
        ):
            raise ValueError("basis is spliced across the trace state schema")

    b_source = basis_manifest_array(common_source)
    w_readout = basis_manifest_array(common_readout)
    c_source = _matrix(recipe.source_selector, "source_selector")
    c_readout = _matrix(recipe.readout_selector, "readout_selector")
    injection = _matrix(
        materialization.scenario_source_injection,
        "scenario_source_injection",
    )
    coisometry = _matrix(
        materialization.scenario_readout_coisometry,
        "scenario_readout_coisometry",
    )
    if c_source.shape[0] != b_source.shape[0]:
        raise ValueError("source selector does not act on common case basis")
    if c_readout.shape[1] != w_readout.shape[0]:
        raise ValueError("readout selector does not act on common case basis")
    source_identity = np.eye(c_source.shape[1], dtype=np.complex128)
    readout_identity = np.eye(c_readout.shape[0], dtype=np.complex128)
    if (
        _spectral_residual(c_source.conj().T @ c_source - source_identity)
        > SELECTOR_RESIDUAL_TOLERANCE
    ):
        raise ValueError("scenario source selector isometry exceeds 1e-12")
    if (
        _spectral_residual(c_readout @ c_readout.conj().T - readout_identity)
        > SELECTOR_RESIDUAL_TOLERANCE
    ):
        raise ValueError("scenario readout selector coisometry exceeds 1e-12")
    expected_injection = b_source.T @ c_source
    expected_coisometry = c_readout @ np.conjugate(w_readout)
    if not np.array_equal(injection, expected_injection):
        raise ValueError(
            "scenario_source_injection is not common B_source.T @ C_source"
        )
    if not np.array_equal(coisometry, expected_coisometry):
        raise ValueError(
            "scenario_readout_coisometry is not C_readout @ conj(W_readout)"
        )
    if not np.array_equal(basis_manifest_array(scenario_source), injection.T):
        raise ValueError("scenario source basis does not match selector-derived J")
    if not np.array_equal(
        basis_manifest_array(scenario_readout),
        np.conjugate(coisometry),
    ):
        raise ValueError("scenario readout basis does not match conj(P)")


def _verify_trace_and_factories(
    materialization: ApplicationScenarioMaterializationV2,
    recipe: ScenarioConstructionRecipeV2,
) -> None:
    trace = _verify_trace(materialization.construction_trace)
    if (
        trace.scenario_id != materialization.scenario_id
        or trace.scenario_sha != materialization.scenario_sha
        or trace.recipe_sha != recipe.recipe_sha
        or trace.operation_dag_sha != recipe.operation_dag_sha
        or trace.compiled_contract_sha != recipe.compiled_contract_sha
        or trace.construction_rule_id != recipe.construction_rule_id
        or trace.construction_family_id != recipe.construction_family_id
    ):
        raise ValueError("construction trace is spliced across recipe lineage")
    actual_effect = recipe.actual_effect
    matched_effect = recipe.matched_ablated_effect
    if (
        trace.actual_step_shas
        != tuple(item.step_sha for item in actual_effect.ordered_steps)
        or trace.matched_ablated_step_shas
        != tuple(item.step_sha for item in matched_effect.ordered_steps)
        or trace.actual_program_sha != actual_effect.program_sha
        or trace.matched_ablated_program_sha != matched_effect.program_sha
        or trace.actual_effect_digest != actual_effect.effect_digest
        or trace.matched_ablated_effect_digest != matched_effect.effect_digest
    ):
        raise ValueError("construction trace differs from recipe effects")
    parameters = dict(trace.target_blind_parameters)
    if parameters.get("selected_fejer_order") != float(
        materialization.selected_fejer_order
    ):
        raise ValueError("construction trace selected Fejer order drifted")

    bindings = (
        (materialization.actual_factory_binding, actual_effect, "actual"),
        (
            materialization.matched_ablated_factory_binding,
            matched_effect,
            "matched_ablated",
        ),
    )
    for binding, effect, branch in bindings:
        _verify_factory_binding(binding)
        if (
            binding.branch != branch
            or binding.scenario_id != materialization.scenario_id
            or binding.scenario_sha != materialization.scenario_sha
            or binding.recipe_sha != recipe.recipe_sha
            or binding.construction_trace_sha != trace.construction_trace_sha
        ):
            raise ValueError("factory binding is spliced across scenario lineage")
        if (
            binding.program_sha != effect.program_sha
            or binding.effect_digest != effect.effect_digest
        ):
            raise ValueError("factory binding effect differs from recipe effect")
        if (
            binding.interface_sha != trace.interface_sha
            or binding.state_schema_id != trace.state_schema_id
            or binding.state_shape != trace.state_shape
        ):
            raise ValueError("factory binding runtime shape is spliced")
        if (
            binding.source_manifest_id
            != materialization.scenario_source_basis.manifest_id
            or binding.readout_manifest_id
            != materialization.scenario_readout_basis.manifest_id
        ):
            raise ValueError(
                "factory binding forced common case basis over scenario selector"
            )
    if (
        materialization.actual_factory_binding.factory_sha
        == materialization.matched_ablated_factory_binding.factory_sha
    ):
        raise ValueError("actual and matched factory bindings are identical")
    _verify_scenario_basis_derivation(materialization, recipe, trace)


def verify_application_scenario_materialization_v2_body(
    materialization: ApplicationScenarioMaterializationV2,
) -> ApplicationScenarioMaterializationV2:
    """Verify an authority-neutral body without hydrating a capability."""

    _exact_record(
        materialization,
        ApplicationScenarioMaterializationV2,
        "application scenario materialization-v2",
    )
    materialization.__post_init__()
    if materialization.materialization_v2_sha != canonical_sha(
        application_scenario_materialization_v2_payload(materialization)
    ):
        raise ValueError("materialization-v2 SHA does not match its body")
    recipe = _verify_recipe_lineage(materialization)
    _verify_trace_and_factories(materialization, recipe)
    return materialization


@dataclass(frozen=True)
class _LiveMaterializationReplayV2:
    materialization: ApplicationScenarioMaterializationV2
    ablation_outcome: AblationConstructionOutcome
    actual_factory: VerifiedFactory
    matched_ablated_factory: VerifiedFactory


@dataclass(frozen=True)
class _LiveMaterializationBindingV2:
    formal_parent_v2: object
    permit_v2: object
    scenario_id: str
    materialization_v2_sha: str
    actual_factory_sha: str
    matched_ablated_factory_sha: str


class VerifiedV3M0ApplicationScenarioMaterializationV2:
    """Opaque live scenario materialization; raw records cannot substitute."""

    __slots__ = ("_authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("application materialization-v2 is issuer-only")

    @property
    def materialization(self) -> ApplicationScenarioMaterializationV2:
        return verify_v3m0_application_scenario_materialization_v2(self)

    @property
    def actual_factory(self) -> VerifiedFactory:
        return _reverify_live_materialization_v2(self).actual_factory

    @property
    def matched_ablated_factory(self) -> VerifiedFactory:
        return _reverify_live_materialization_v2(self).matched_ablated_factory


def _require_exact_live_upstream(
    formal_parent_v2: object,
    permit_v2: object,
) -> tuple[object, object]:
    parent_type = type(formal_parent_v2)
    if (
        parent_type.__module__ != "rulespace_v3.parent_authority"
        or parent_type.__name__ != "VerifiedParentFreezeV2"
    ):
        raise TypeError("formal_parent_v2 must be an exact live Parent-v2")
    from .parent_authority import VerifiedParentFreezeV2, require_current_parent

    if type(formal_parent_v2) is not VerifiedParentFreezeV2:
        raise TypeError("formal_parent_v2 must be an exact live Parent-v2")
    try:
        from .application_authority_v2 import (
            VerifiedCalibrationApplicationPermitV2,
            require_calibration_application_permit_v2,
        )
    except (ImportError, AttributeError) as exc:
        raise ApplicationMaterializationV2UpstreamUnavailable(
            "exact permit-v2 authority is not implemented; required wiring: "
            + ", ".join(UPSTREAM_V2_WIRING_POINTS)
        ) from exc
    if type(permit_v2) is not VerifiedCalibrationApplicationPermitV2:
        raise TypeError("permit_v2 must be an exact live permit-v2")
    parent_manifest = require_current_parent(formal_parent_v2)
    permit_body = require_calibration_application_permit_v2(permit_v2)
    return parent_manifest, permit_body


def _exact_one(values: object, predicate, field: str):
    if type(values) is not tuple:
        raise TypeError(f"{field} registry must be an exact tuple")
    matches = tuple(item for item in values if predicate(item))
    if len(matches) != 1:
        raise ValueError(f"{field} does not resolve to one exact record")
    return matches[0]


def _interface_sha(interface: PrimitiveInterface) -> str:
    if type(interface) is not PrimitiveInterface:
        raise TypeError("interface must be an exact PrimitiveInterface")
    return canonical_sha(
        {
            "interface_id": interface.interface_id,
            "state_schema_id": interface.state_schema_id,
            "spatial_ndim": interface.spatial_ndim,
            "channel_order": list(interface.channel_order),
            "dtype": interface.dtype,
            "backend": interface.backend,
        }
    )


def _resign_local_step(
    *,
    scenario_id: str,
    ordinal: int,
    source_step: object,
) -> ScenarioLocalShearStepV2:
    provisional = ScenarioLocalShearStepV2(
        step_schema_version=SCENARIO_LOCAL_SHEAR_STEP_V2_SCHEMA_VERSION,
        scenario_id=scenario_id,
        step_id=source_step.step_id,
        ordinal=ordinal,
        source_channel=source_step.source_channel,
        destination_channel=source_step.destination_channel,
        offset=tuple(source_step.offset),
        coefficient_wire=(float(source_step.coefficient), 0.0),
        target_conditioned=source_step.target_conditioned,
        step_sha="0" * 64,
    )
    return replace(
        provisional,
        step_sha=canonical_sha(scenario_local_shear_step_v2_payload(provisional)),
    )


def _build_effect(
    *,
    branch: Literal["actual", "matched_ablated"],
    scenario_id: str,
    scenario_sha: str,
    construction_rule_id: str,
    construction_family_id: str,
    ordered_steps: tuple[ScenarioLocalShearStepV2, ...],
) -> ScenarioConstructionEffectV2:
    provisional = ScenarioConstructionEffectV2(
        effect_schema_version=SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION,
        branch=branch,
        scenario_id=scenario_id,
        scenario_sha=scenario_sha,
        construction_rule_id=construction_rule_id,
        construction_family_id=construction_family_id,
        ordered_steps=ordered_steps,
        program_sha="0" * 64,
        effect_digest="0" * 64,
    )
    with_program = replace(
        provisional,
        program_sha=_effect_program_sha(provisional),
    )
    return replace(
        with_program,
        effect_digest=canonical_sha(
            scenario_construction_effect_v2_payload(with_program)
        ),
    )


def _c04_source_recipe(
    scenario_authority: object,
) -> tuple[
    object,
    tuple[ScenarioLocalShearStepV2, ...],
    tuple[ScenarioLocalShearStepV2, ...],
]:
    response = scenario_authority.response_contract
    recipe = _verify_c04_canonical_angle_recipe(build_c04_canonical_angle_recipe())
    source_steps = recipe.steps
    matched_source_steps = tuple(
        item for item in source_steps if not item.target_conditioned
    )

    def authority_program_sha(branch: str, steps: tuple[object, ...]) -> str:
        return canonical_sha(
            {
                "program_schema_version": (
                    "v3m0.c04-canonical-angle-local-shear-program.v1"
                ),
                "branch": branch,
                "steps": [
                    {
                        **c04_local_shear_step_payload(item),
                        "step_sha": item.step_sha,
                    }
                    for item in steps
                ],
            }
        )

    if (
        scenario_authority.source_disposition != "PARENT_V1_C04_CLOSED_RECIPE"
        or response.construction_rule_id != recipe.recipe_id
        or response.construction_family_id
        != "c04-canonical-angle-local-shear-family-v1"
        or response.preflight_derivation_or_recipe_sha != recipe.recipe_sha
        or response.actual_step_count != len(source_steps)
        or response.matched_ablated_step_count != len(matched_source_steps)
        or response.actual_program_sha != authority_program_sha("actual", source_steps)
        or response.matched_ablated_program_sha
        != authority_program_sha("matched_ablated", matched_source_steps)
        or response.actual_effect_digest != recipe.actual_effect_digest
        or response.matched_ablated_effect_digest != recipe.ablated_effect_digest
        or response.uses_global_fft_projection is not False
        or response.uses_per_k_time_step_projector is not False
    ):
        raise ValueError("C04 current response authority differs from closed recipe")
    actual = tuple(
        _resign_local_step(
            scenario_id=scenario_authority.scenario_id,
            ordinal=index,
            source_step=step,
        )
        for index, step in enumerate(source_steps)
    )
    matched = tuple(item for item in actual if not item.target_conditioned)
    return recipe, actual, matched


def _candidate_v2_source_recipe(
    parent_manifest: object,
    scenario_authority: CurrentScenarioAuthorityV2,
) -> tuple[
    object,
    tuple[ScenarioLocalShearStepV2, ...],
    tuple[ScenarioLocalShearStepV2, ...],
]:
    """Replay one reviewed candidate-v2 refreeze into exact local steps."""

    if scenario_authority.source_disposition != ("CANDIDATE_V2_REVIEWED_MODIFIED"):
        raise ValueError("scenario is not a reviewed candidate-v2 refreeze")
    reviewed = parent_manifest.reviewed_candidate_v2
    refreeze = _exact_one(
        reviewed.scenario_refreezes,
        lambda item: item.scenario_id == scenario_authority.scenario_id,
        "reviewed candidate-v2 scenario refreeze",
    )
    _exact_record(
        refreeze,
        CandidateV2ScenarioRefreeze,
        "reviewed candidate-v2 scenario refreeze",
    )
    refreeze.__post_init__()
    if refreeze.scenario_refreeze_sha != canonical_sha(
        candidate_v2_scenario_refreeze_payload(refreeze)
    ):
        raise ValueError("candidate-v2 scenario-refreeze SHA drifted")
    response = scenario_authority.response_contract
    compiled = verify_compiled_candidate_scenario_contract(
        refreeze.operation_dag,
        extract_candidate_scenario_contract(refreeze.operation_dag),
    )
    template = refreeze.response_template
    selector = refreeze.proposed_selector_spec
    if (
        scenario_authority.source_candidate_v2_refreeze_sha
        != refreeze.scenario_refreeze_sha
        or refreeze.control_case_id != scenario_authority.control_case_id
        or refreeze.scenario_id != scenario_authority.scenario_id
        or compiled.scenario_id != scenario_authority.scenario_id
        or refreeze.operation_dag.dag_sha != response.operation_dag_sha
        or compiled.contract_sha != response.compiled_contract_sha
        or template.compiled_contract_sha != compiled.contract_sha
        or template.dag_sha != refreeze.operation_dag.dag_sha
        or selector != response.selector_spec
        or selector.selector_sha != response.selector_sha
        or template.selector_sha != selector.selector_sha
        or compiled.proposed_source_selection != selector.source_selector
        or compiled.proposed_readout_selection != selector.readout_selector
        or template.source_trial_vectors != response.source_trial_vectors
        or template.response_torus_denominators != response.response_torus_denominators
        or template.response_reciprocal_indices != response.response_reciprocal_indices
        or template.source_readout_bridge_reciprocal_indices
        != response.source_readout_bridge_reciprocal_indices
        or template.source_readout_bridge_steps != response.source_readout_bridge_steps
        or template.reference_reciprocal_index != response.reference_reciprocal_index
        or template.preregistered_phase_bands != response.preregistered_phase_bands
        or compiled.construction_rule_id != response.construction_rule_id
        or template.construction_rule_id != response.construction_rule_id
        or compiled.construction_family_id != response.construction_family_id
        or template.construction_family_id != response.construction_family_id
        or compiled.expected_actual_shell_rank != response.expected_actual_shell_rank
        or template.expected_actual_shell_rank != response.expected_actual_shell_rank
        or compiled.expected_matched_shell_rank != response.expected_matched_shell_rank
        or template.expected_matched_shell_rank != response.expected_matched_shell_rank
        or len(compiled.actual_step_signatures) != response.actual_step_count
        or len(compiled.matched_ablated_step_signatures)
        != response.matched_ablated_step_count
        or compiled.actual_program_sha != response.actual_program_sha
        or template.actual_program_sha != response.actual_program_sha
        or compiled.matched_ablated_program_sha != response.matched_ablated_program_sha
        or template.matched_ablated_program_sha != response.matched_ablated_program_sha
        or compiled.construction_recipe_sha
        != response.preflight_derivation_or_recipe_sha
        or template.preflight_derivation_or_recipe_sha
        != response.preflight_derivation_or_recipe_sha
        or compiled.actual_effect_digest != response.actual_effect_digest
        or template.preflight_actual_effect_digest != response.actual_effect_digest
        or compiled.matched_ablated_effect_digest
        != response.matched_ablated_effect_digest
        or template.preflight_matched_effect_digest
        != response.matched_ablated_effect_digest
        or template.template_sha != response.response_template_sha
        or refreeze.prediction_profile.profile_sha != response.prediction_profile_sha
        or compiled.uses_global_fft_projection is not False
        or template.uses_global_fft_projection is not False
        or response.uses_global_fft_projection is not False
        or compiled.uses_per_k_time_step_projector is not False
        or template.uses_per_k_time_step_projector is not False
        or response.uses_per_k_time_step_projector is not False
    ):
        raise ValueError(
            "candidate-v2 current response differs from its exact refreeze"
        )
    actual = tuple(
        _resign_local_step(
            scenario_id=scenario_authority.scenario_id,
            ordinal=index,
            source_step=step,
        )
        for index, step in enumerate(compiled.actual_step_signatures)
    )
    matched = tuple(item for item in actual if not item.target_conditioned)
    return compiled, actual, matched


def _build_execution_trace_and_operators(
    *,
    historical_application: object,
    scenario_authority: object,
    source_recipe_sha: str,
    actual_steps: tuple[ScenarioLocalShearStepV2, ...],
    target_spec_id: str,
    interface: PrimitiveInterface,
):
    scenario = scenario_authority.scenario_execution_spec
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
        for operation in historical_application.operations
    ]
    blind_provenance_id = f"{scenario.scenario_id}.current-v2-recipe"
    conditioned_provenance_id = f"{scenario.scenario_id}.current-v2-target"
    provenance.extend(
        (
            ProvenanceNode(
                provenance_id=blind_provenance_id,
                operation=ProvenanceOperation.GRAMMAR_CONSTANT,
                depends_on=scenario.operation_output_ids,
                target_refs=(),
                objective_tags=(),
                search_run_id=None,
                source_sha=source_recipe_sha,
            ),
            ProvenanceNode(
                provenance_id=conditioned_provenance_id,
                operation=ProvenanceOperation.TARGET_SPEC_READ,
                depends_on=(blind_provenance_id,),
                target_refs=(f"target:{target_spec_id}",),
                objective_tags=(),
                search_run_id=None,
                source_sha=scenario_authority.scenario_authority_sha,
            ),
        )
    )
    zero = (0,) * interface.spatial_ndim
    specifications = []
    operators = []
    for index, step in enumerate(actual_steps):
        mechanism_id = f"{scenario.scenario_id}.v2-shear.{index:03d}"
        production_id = (
            "target_operator" if step.target_conditioned else "local_canonical_shear"
        )
        layer_slot_id = f"{scenario.scenario_id}.v2-layer.{index:03d}"
        specifications.append(
            PrimitiveSpec(
                mechanism_id=mechanism_id,
                production_id=production_id,
                depends_on=(),
                support_offsets=tuple(sorted({zero, step.offset})),
                state_channels=tuple(
                    sorted((step.source_channel, step.destination_channel))
                ),
                coefficient_expression=sp.Rational(
                    *step.coefficient_wire[0].as_integer_ratio()
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
                coefficient_wire=step.coefficient_wire,
            )
        )
    trace = build_construction_trace(
        target_spec_id=target_spec_id,
        provenance_nodes=tuple(provenance),
        primitive_specs=tuple(specifications),
    )
    return trace, tuple(operators)


def _binding_from_live_factory(
    *,
    branch: Literal["actual", "matched_ablated"],
    factory: VerifiedFactory,
    scenario_id: str,
    scenario_sha: str,
    recipe_sha: str,
    construction_trace_sha: str,
    effect: ScenarioConstructionEffectV2,
) -> ScenarioFactoryBindingV2:
    view = _reverify_verified_factory(factory)
    provisional = ScenarioFactoryBindingV2(
        binding_schema_version=SCENARIO_FACTORY_BINDING_V2_SCHEMA_VERSION,
        branch=branch,
        scenario_id=scenario_id,
        scenario_sha=scenario_sha,
        recipe_sha=recipe_sha,
        construction_trace_sha=construction_trace_sha,
        program_sha=effect.program_sha,
        effect_digest=effect.effect_digest,
        factory_sha=view.factory.factory_sha,
        runtime_operator_sha=view.factory.runtime_operator_sha,
        interface_sha=_interface_sha(view.factory.interface),
        state_schema_id=view.factory.state_schema_id,
        state_shape=view.factory.state_shape,
        source_manifest_id=view.factory.source_manifest_id,
        readout_manifest_id=view.factory.readout_basis.manifest_id,
        factory_binding_sha="0" * 64,
    )
    return replace(
        provisional,
        factory_binding_sha=canonical_sha(
            scenario_factory_binding_v2_payload(provisional)
        ),
    )


def _compile_expected_live_materialization_v2(
    parent_manifest: object,
    permit_body: object,
    scenario_id: str,
) -> _LiveMaterializationReplayV2:
    """Authority-neutral exact compiler used behind a live-identity bridge."""

    identifier = _text(scenario_id, "scenario_id")
    parent_sha = _sha(parent_manifest.parent_freeze_v2_sha, "parent_freeze_v2_sha")
    if permit_body.parent_freeze_v2_sha != parent_sha:
        raise ValueError("permit-v2 is spliced across Parent-v2 roots")
    application = permit_body.application_authority
    _exact_record(
        application,
        CurrentApplicationAuthorityV2,
        "current application authority",
    )
    application.__post_init__()
    if application.application_authority_sha != canonical_sha(
        current_application_authority_v2_payload(application)
    ):
        raise ValueError("current application-authority SHA drifted")
    if (
        permit_body.control_case_id != application.control_case_id
        or permit_body.permit_sha != _sha(permit_body.permit_sha, "permit_sha")
        or permit_body.selected_fejer_order <= 0
    ):
        raise ValueError("permit-v2 body is not exact for its application")
    current_application = _exact_one(
        parent_manifest.current_application_authorities,
        lambda item: (
            item.application_instance_id == application.application_instance_id
        ),
        "current application authority",
    )
    if current_application != application:
        raise ValueError("permit-v2 application differs from current Parent-v2")
    scenario = _exact_one(
        application.scenario_authorities,
        lambda item: item.scenario_id == identifier,
        "current BLOCK_SUCCESS scenario authority",
    )
    _exact_record(
        scenario,
        CurrentScenarioAuthorityV2,
        "current scenario authority",
    )
    scenario.__post_init__()
    if scenario.scenario_authority_sha != canonical_sha(
        current_scenario_authority_v2_payload(scenario)
    ):
        raise ValueError("current scenario-authority SHA drifted")
    if scenario.scenario_authority_sha not in permit_body.scenario_authority_shas:
        raise ValueError("scenario authority is absent from the live permit-v2")
    response = scenario.response_contract
    _exact_record(
        response,
        CurrentScenarioResponseContractV2,
        "current response contract",
    )
    response.__post_init__()
    if response.response_contract_sha != canonical_sha(
        current_scenario_response_contract_v2_payload(response)
    ):
        raise ValueError("current response-contract SHA drifted")
    if (
        scenario.control_case_id != application.control_case_id
        or scenario.application_instance_id != application.application_instance_id
        or scenario.based_on_application_spec_sha
        != application.based_on_application_spec_sha
        or scenario.scenario_execution_spec.execution_lane != "BLOCK_SUCCESS"
        or scenario.scenario_execution_spec.scenario_id != identifier
        or response.scenario_id != identifier
    ):
        raise ValueError("scenario authority is spliced across permit lineage")
    historical_application = _exact_one(
        parent_manifest.historical_parent_v1.synthetic_control_application_specs,
        lambda item: (
            item.application_instance_id == application.application_instance_id
        ),
        "historical application spec",
    )
    if (
        historical_application.control_case_id != application.control_case_id
        or historical_application.application_spec_sha
        != application.based_on_application_spec_sha
    ):
        raise ValueError("current application is spliced from historical Parent-v1")

    if scenario.source_disposition == "PARENT_V1_C04_CLOSED_RECIPE":
        source_recipe, actual_steps, matched_steps = _c04_source_recipe(scenario)
    elif scenario.source_disposition == "CANDIDATE_V2_REVIEWED_MODIFIED":
        source_recipe, actual_steps, matched_steps = _candidate_v2_source_recipe(
            parent_manifest, scenario
        )
    else:
        raise ApplicationMaterializationV2UpstreamUnavailable(
            "current scenario source disposition has no exact materializer"
        )
    common_source = historical_application.basis_protocol.source_basis
    common_readout = historical_application.basis_protocol.readout_basis
    selector = response.selector_spec
    if (
        selector.scenario_id != identifier
        or selector.public_source_basis_manifest_id != common_source.manifest_id
        or selector.public_readout_basis_manifest_id != common_readout.manifest_id
    ):
        raise ValueError("scenario selector is spliced from its common case basis")
    source_selector = selector.source_selector
    readout_selector = selector.readout_selector
    source_injection = selector.source_injection
    readout_coisometry = selector.readout_coisometry
    scenario_source = build_basis_manifest(
        role="source",
        state_schema_id=common_source.state_schema_id,
        channel_order=common_source.channel_order,
        vectors=frozen_tensor_array(source_injection).T,
    )
    scenario_readout = build_basis_manifest(
        role="readout",
        state_schema_id=common_readout.state_schema_id,
        channel_order=common_readout.channel_order,
        vectors=np.conjugate(frozen_tensor_array(readout_coisometry)),
    )
    actual_effect = _build_effect(
        branch="actual",
        scenario_id=identifier,
        scenario_sha=scenario.scenario_execution_spec.scenario_sha,
        construction_rule_id=response.construction_rule_id,
        construction_family_id=response.construction_family_id,
        ordered_steps=actual_steps,
    )
    matched_effect = _build_effect(
        branch="matched_ablated",
        scenario_id=identifier,
        scenario_sha=scenario.scenario_execution_spec.scenario_sha,
        construction_rule_id=response.construction_rule_id,
        construction_family_id=response.construction_family_id,
        ordered_steps=matched_steps,
    )
    recipe_provisional = ScenarioConstructionRecipeV2(
        recipe_schema_version=SCENARIO_CONSTRUCTION_RECIPE_V2_SCHEMA_VERSION,
        recipe_state="FORMAL_SCENARIO_AUTHORITY_DERIVED",
        formal_parent_v2_sha=parent_sha,
        permit_v2_sha=permit_body.permit_sha,
        application_spec_sha=application.based_on_application_spec_sha,
        scenario_authority_sha=scenario.scenario_authority_sha,
        response_contract_sha=response.response_contract_sha,
        control_case_id=application.control_case_id,
        application_instance_id=application.application_instance_id,
        scenario_id=identifier,
        scenario_sha=scenario.scenario_execution_spec.scenario_sha,
        selector_sha=scenario_selector_v2_sha(
            source_selector,
            readout_selector,
        ),
        operation_dag_sha=response.operation_dag_sha,
        compiled_contract_sha=response.compiled_contract_sha,
        construction_rule_id=response.construction_rule_id,
        construction_family_id=response.construction_family_id,
        primitive_support_radius=source_recipe.primitive_support_radius,
        uses_global_fft_projection=False,
        uses_per_k_time_step_projector=False,
        source_selector=source_selector,
        readout_selector=readout_selector,
        actual_effect=actual_effect,
        matched_ablated_effect=matched_effect,
        recipe_sha="0" * 64,
    )
    recipe = replace(
        recipe_provisional,
        recipe_sha=canonical_sha(
            scenario_construction_recipe_v2_payload(recipe_provisional)
        ),
    )

    historical_parent = issue_v3m0_parent_freeze()
    if historical_parent.manifest != parent_manifest.historical_parent_v1:
        raise ValueError("historical Parent-v1 replay differs from Parent-v2")
    carrier = _build_task8_controls(historical_parent)[0]
    carrier_view = _reverify_verified_factory(carrier.factory)
    interface = PrimitiveInterface(
        interface_id=f"interface.{identifier}.v2",
        state_schema_id=common_source.state_schema_id,
        spatial_ndim=historical_application.grid_protocol.spatial_ndim,
        channel_order=common_source.channel_order,
        dtype="complex128",
        backend="numpy",
    )
    runtime_trace, operators = _build_execution_trace_and_operators(
        historical_application=historical_application,
        scenario_authority=scenario,
        source_recipe_sha=response.preflight_derivation_or_recipe_sha,
        actual_steps=actual_steps,
        target_spec_id=carrier.target.target_spec_id,
        interface=interface,
    )
    target_blind_parameters = (
        ("selected_fejer_order", float(permit_body.selected_fejer_order)),
    )
    actual = build_factory_from_trace(
        runtime_trace,
        carrier.target,
        factory_id=f"factory.{identifier}.v2",
        interface=interface,
        state_shape=(len(common_source.channel_order),)
        + historical_application.grid_protocol.spatial_shape,
        dt=carrier_view.factory.dt,
        target_blind_parameters=target_blind_parameters,
        layer_slot_ids=tuple(item.layer_slot_id for item in operators),
        operator_payload=operators,
        source_manifest_id=scenario_source.manifest_id,
        readout_basis=scenario_readout,
        boundary_manifest_id="periodic-v1",
    )
    outcome = _verify_construction_outcome(matched_ablation(actual))
    if not outcome.status.defined or outcome.pair is None:
        raise ValueError("scenario local recipe did not form a matched ablation pair")
    pair = verify_ablation_pair(outcome.pair)
    # Downstream must retain the wrappers owned by the verified construction
    # outcome.  The ablation builder snapshots the input actual factory, so the
    # pre-ablation wrapper is deliberately not exposed as the live pair.
    actual = pair.actual
    matched = pair.ablated

    trace_provisional = ScenarioConstructionTraceV2(
        trace_schema_version=SCENARIO_CONSTRUCTION_TRACE_V2_SCHEMA_VERSION,
        trace_state="FORMAL_RECIPE_REPLAYED_PRE_EVOLUTION",
        scenario_id=identifier,
        scenario_sha=scenario.scenario_execution_spec.scenario_sha,
        recipe_sha=recipe.recipe_sha,
        operation_dag_sha=response.operation_dag_sha,
        compiled_contract_sha=response.compiled_contract_sha,
        construction_rule_id=response.construction_rule_id,
        construction_family_id=response.construction_family_id,
        target_spec_id=carrier.target.target_spec_id,
        target_spec_sha=carrier.target.target_spec_sha,
        interface_sha=_interface_sha(interface),
        state_schema_id=common_source.state_schema_id,
        channel_order=common_source.channel_order,
        state_shape=(len(common_source.channel_order),)
        + historical_application.grid_protocol.spatial_shape,
        dt=carrier_view.factory.dt,
        target_blind_parameters=target_blind_parameters,
        boundary_manifest_id="periodic-v1",
        actual_step_shas=tuple(item.step_sha for item in actual_steps),
        matched_ablated_step_shas=tuple(item.step_sha for item in matched_steps),
        actual_program_sha=actual_effect.program_sha,
        matched_ablated_program_sha=matched_effect.program_sha,
        actual_effect_digest=actual_effect.effect_digest,
        matched_ablated_effect_digest=matched_effect.effect_digest,
        construction_trace_sha="0" * 64,
    )
    construction_trace = replace(
        trace_provisional,
        construction_trace_sha=canonical_sha(
            scenario_construction_trace_v2_payload(trace_provisional)
        ),
    )
    actual_binding = _binding_from_live_factory(
        branch="actual",
        factory=actual,
        scenario_id=identifier,
        scenario_sha=scenario.scenario_execution_spec.scenario_sha,
        recipe_sha=recipe.recipe_sha,
        construction_trace_sha=construction_trace.construction_trace_sha,
        effect=actual_effect,
    )
    matched_binding = _binding_from_live_factory(
        branch="matched_ablated",
        factory=matched,
        scenario_id=identifier,
        scenario_sha=scenario.scenario_execution_spec.scenario_sha,
        recipe_sha=recipe.recipe_sha,
        construction_trace_sha=construction_trace.construction_trace_sha,
        effect=matched_effect,
    )
    body_provisional = ApplicationScenarioMaterializationV2(
        materialization_schema_version=(
            APPLICATION_SCENARIO_MATERIALIZATION_V2_SCHEMA_VERSION
        ),
        materialization_state=APPLICATION_SCENARIO_MATERIALIZATION_V2_STATE,
        formal_parent_v2_sha=parent_sha,
        permit_v2_sha=permit_body.permit_sha,
        application_authority_sha=application.application_authority_sha,
        application_spec_sha=application.based_on_application_spec_sha,
        control_case_id=application.control_case_id,
        application_instance_id=application.application_instance_id,
        scenario_authority_sha=scenario.scenario_authority_sha,
        response_contract_sha=response.response_contract_sha,
        scenario_id=identifier,
        scenario_sha=scenario.scenario_execution_spec.scenario_sha,
        selected_fejer_order=permit_body.selected_fejer_order,
        common_source_basis=common_source,
        common_readout_basis=common_readout,
        scenario_recipe=recipe,
        scenario_source_injection=source_injection,
        scenario_readout_coisometry=readout_coisometry,
        scenario_source_basis=scenario_source,
        scenario_readout_basis=scenario_readout,
        construction_trace=construction_trace,
        actual_factory_binding=actual_binding,
        matched_ablated_factory_binding=matched_binding,
        materialization_v2_sha="0" * 64,
    )
    body = replace(
        body_provisional,
        materialization_v2_sha=canonical_sha(
            application_scenario_materialization_v2_payload(body_provisional)
        ),
    )
    verify_application_scenario_materialization_v2_body(body)
    replay = _LiveMaterializationReplayV2(
        materialization=body,
        ablation_outcome=outcome,
        actual_factory=actual,
        matched_ablated_factory=matched,
    )
    _verify_live_factories(replay)
    return replay


def _make_expected_live_materialization_v2(upstream_resolver):
    """Build a private exact replayer; it cannot issue an opaque capability."""

    if not callable(upstream_resolver):
        raise TypeError("upstream_resolver must be callable")

    def replay(formal_parent_v2: object, permit_v2: object, scenario_id: str):
        parent_manifest, permit_body = upstream_resolver(
            formal_parent_v2,
            permit_v2,
        )
        return _compile_expected_live_materialization_v2(
            parent_manifest,
            permit_body,
            scenario_id,
        )

    return replay


def _expected_live_materialization_v2(
    formal_parent_v2: object,
    permit_v2: object,
    scenario_id: str,
) -> _LiveMaterializationReplayV2:
    _text(scenario_id, "scenario_id")
    _require_exact_live_upstream(formal_parent_v2, permit_v2)
    raise ApplicationMaterializationV2UpstreamUnavailable(
        "permit-v2 consumer lacks a closed expected-Parent identity bridge; "
        "authority-neutral exact compilation is implemented but public issuance "
        "remains fail-closed"
    )


def _verify_live_factories(
    replay: _LiveMaterializationReplayV2,
) -> None:
    body = verify_application_scenario_materialization_v2_body(replay.materialization)
    actual = _reverify_verified_factory(replay.actual_factory)
    matched = _reverify_verified_factory(replay.matched_ablated_factory)
    outcome = _verify_construction_outcome(replay.ablation_outcome)
    if (
        not outcome.status.defined
        or outcome.pair is None
        or outcome.pair.actual is not replay.actual_factory
        or outcome.pair.ablated is not replay.matched_ablated_factory
    ):
        raise ValueError("live matched-ablation pair identity changed")
    if actual.role != "actual" or matched.role != "matched_ablated":
        raise ValueError("live factory roles differ from materialization branches")
    if (
        actual.factory.factory_sha != body.actual_factory_binding.factory_sha
        or matched.factory.factory_sha
        != body.matched_ablated_factory_binding.factory_sha
        or actual.factory.runtime_operator_sha
        != body.actual_factory_binding.runtime_operator_sha
        or matched.factory.runtime_operator_sha
        != body.matched_ablated_factory_binding.runtime_operator_sha
    ):
        raise ValueError("live factories differ from materialization bindings")
    for view, binding in (
        (actual, body.actual_factory_binding),
        (matched, body.matched_ablated_factory_binding),
    ):
        if (
            view.factory.source_manifest_id != binding.source_manifest_id
            or view.factory.readout_basis.manifest_id != binding.readout_manifest_id
            or view.factory.state_schema_id != binding.state_schema_id
            or view.factory.state_shape != binding.state_shape
        ):
            raise ValueError("live factory scenario selector binding drifted")


def _make_closed_materialization_v2_api():
    registry: WeakKeyDictionary[
        VerifiedV3M0ApplicationScenarioMaterializationV2,
        _LiveMaterializationBindingV2,
    ] = WeakKeyDictionary()
    authority_seal = object()
    expected_replayer = _expected_live_materialization_v2
    live_factory_verifier = _verify_live_factories

    def materialize_v3m0_application_scenario_v2(
        formal_parent_v2: object,
        permit_v2: object,
        scenario_id: str,
    ) -> VerifiedV3M0ApplicationScenarioMaterializationV2:
        replay = expected_replayer(
            formal_parent_v2,
            permit_v2,
            scenario_id,
        )
        live_factory_verifier(replay)
        body = replay.materialization
        capability = object.__new__(VerifiedV3M0ApplicationScenarioMaterializationV2)
        object.__setattr__(capability, "_authority_seal", authority_seal)
        registry[capability] = _LiveMaterializationBindingV2(
            formal_parent_v2=formal_parent_v2,
            permit_v2=permit_v2,
            scenario_id=scenario_id,
            materialization_v2_sha=body.materialization_v2_sha,
            actual_factory_sha=body.actual_factory_binding.factory_sha,
            matched_ablated_factory_sha=(
                body.matched_ablated_factory_binding.factory_sha
            ),
        )
        return capability

    def reverify(
        value: object,
    ) -> _LiveMaterializationReplayV2:
        if type(value) is not VerifiedV3M0ApplicationScenarioMaterializationV2:
            raise TypeError("value must be an exact live materialization-v2 capability")
        try:
            seal = value._authority_seal
            binding = registry[value]
        except (AttributeError, KeyError) as exc:
            raise ValueError(
                "materialization-v2 capability identity is not live"
            ) from exc
        if seal is not authority_seal:
            raise ValueError("materialization-v2 capability authority seal is forged")
        replay = expected_replayer(
            binding.formal_parent_v2,
            binding.permit_v2,
            binding.scenario_id,
        )
        live_factory_verifier(replay)
        if (
            replay.materialization.materialization_v2_sha
            != binding.materialization_v2_sha
            or replay.actual_factory.factory.factory_sha != binding.actual_factory_sha
            or replay.matched_ablated_factory.factory.factory_sha
            != binding.matched_ablated_factory_sha
        ):
            raise ValueError("closed materialization-v2 replay changed")
        return replay

    def verify_v3m0_application_scenario_materialization_v2(
        value: object,
    ) -> ApplicationScenarioMaterializationV2:
        return reverify(value).materialization

    return (
        materialize_v3m0_application_scenario_v2,
        verify_v3m0_application_scenario_materialization_v2,
        reverify,
    )


(
    materialize_v3m0_application_scenario_v2,
    verify_v3m0_application_scenario_materialization_v2,
    _reverify_live_materialization_v2,
) = _make_closed_materialization_v2_api()


__all__ = [
    "APPLICATION_SCENARIO_MATERIALIZATION_V2_SCHEMA_VERSION",
    "APPLICATION_SCENARIO_MATERIALIZATION_V2_STATE",
    "SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION",
    "SCENARIO_CONSTRUCTION_RECIPE_V2_SCHEMA_VERSION",
    "SCENARIO_CONSTRUCTION_TRACE_V2_SCHEMA_VERSION",
    "SCENARIO_FACTORY_BINDING_V2_SCHEMA_VERSION",
    "SCENARIO_LOCAL_SHEAR_STEP_V2_SCHEMA_VERSION",
    "SELECTOR_RESIDUAL_TOLERANCE",
    "UPSTREAM_V2_WIRING_POINTS",
    "ApplicationMaterializationV2UpstreamUnavailable",
    "ApplicationScenarioMaterializationV2",
    "ScenarioConstructionEffectV2",
    "ScenarioConstructionRecipeV2",
    "ScenarioConstructionTraceV2",
    "ScenarioFactoryBindingV2",
    "ScenarioLocalShearStepV2",
    "VerifiedV3M0ApplicationScenarioMaterializationV2",
    "application_scenario_materialization_v2_payload",
    "materialize_v3m0_application_scenario_v2",
    "scenario_construction_effect_v2_payload",
    "scenario_construction_recipe_v2_payload",
    "scenario_construction_trace_v2_payload",
    "scenario_factory_binding_v2_payload",
    "scenario_local_shear_step_v2_payload",
    "scenario_selector_v2_sha",
    "verify_application_scenario_materialization_v2_body",
    "verify_v3m0_application_scenario_materialization_v2",
]
