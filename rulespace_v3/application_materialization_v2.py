"""Exact scenario-bound application materialization contract for Parent-v2.

The raw records in this module are authority-neutral.  They freeze the formal
scenario lineage, local-shear recipe, scenario selectors, mechanically derived
source/readout maps, construction trace and both factory bindings.  Only an
opaque capability produced by a closed replay of a live Parent-v2 and live
permit-v2 may be consumed downstream.

The formal Parent-v2 and DAG/recipe-to-factory compiler are not yet live.  The
public issuer therefore fails closed; it never falls back to the v1
materializer, a candidate DAG, a raw permit, or caller-supplied construction
data.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields
import math
import re
import struct
from typing import Literal
from weakref import WeakKeyDictionary

import numpy as np

from .evidence import canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    VerifiedFactory,
    _reverify_verified_factory,
    basis_manifest_array,
    basis_manifest_payload,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_basis_manifest,
    verify_frozen_tensor,
)


SCENARIO_LOCAL_SHEAR_STEP_V2_SCHEMA_VERSION = (
    "v3m0.scenario-local-shear-step.v2"
)
SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION = (
    "v3m0.scenario-construction-effect.v2"
)
SCENARIO_CONSTRUCTION_RECIPE_V2_SCHEMA_VERSION = (
    "v3m0.scenario-construction-recipe.v2"
)
SCENARIO_CONSTRUCTION_TRACE_V2_SCHEMA_VERSION = (
    "v3m0.scenario-construction-trace.v2"
)
SCENARIO_FACTORY_BINDING_V2_SCHEMA_VERSION = (
    "v3m0.scenario-factory-binding.v2"
)
APPLICATION_SCENARIO_MATERIALIZATION_V2_SCHEMA_VERSION = (
    "v3m0.application-scenario-materialization.v2"
)
APPLICATION_SCENARIO_MATERIALIZATION_V2_STATE = (
    "FORMAL_PARENT_V2_LIVE_MATERIALIZED"
)
SELECTOR_RESIDUAL_TOLERANCE = 1.0e-12

UPSTREAM_V2_WIRING_POINTS = (
    "rulespace_v3.parent_authority.VerifiedParentFreezeV2",
    "rulespace_v3.parent_authority.require_current_parent",
    "rulespace_v3.application_authority_v2.VerifiedCalibrationApplicationPermitV2",
    "rulespace_v3.application_authority_v2.require_calibration_application_permit_v2",
    "formal Parent-v2 scenario DAG/recipe-to-factory compiler",
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
        if (
            self.effect_schema_version
            != SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION
        ):
            raise ValueError("construction effect schema drifted")
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("construction effect branch is not closed")
        _text(self.scenario_id, "scenario_id")
        _sha(self.scenario_sha, "scenario_sha")
        _text(self.construction_rule_id, "construction_rule_id")
        _text(self.construction_family_id, "construction_family_id")
        if type(self.ordered_steps) is not tuple or not self.ordered_steps:
            raise ValueError("construction effect must contain local steps")
        if not all(type(item) is ScenarioLocalShearStepV2 for item in self.ordered_steps):
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
        if (
            self.recipe_schema_version
            != SCENARIO_CONSTRUCTION_RECIPE_V2_SCHEMA_VERSION
        ):
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
        "uses_per_k_time_step_projector": (
            recipe.uses_per_k_time_step_projector
        ),
        "source_selector": _tensor_record(recipe.source_selector),
        "readout_selector": _tensor_record(recipe.readout_selector),
        "actual_effect": {
            **scenario_construction_effect_v2_payload(recipe.actual_effect),
            "effect_digest": recipe.actual_effect.effect_digest,
        },
        "matched_ablated_effect": {
            **scenario_construction_effect_v2_payload(
                recipe.matched_ablated_effect
            ),
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
        abs(coordinate)
        for step in actual.ordered_steps
        for coordinate in step.offset
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
        "common_readout_basis": _basis_record(
            materialization.common_readout_basis
        ),
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
        "scenario_source_basis": _basis_record(
            materialization.scenario_source_basis
        ),
        "scenario_readout_basis": _basis_record(
            materialization.scenario_readout_basis
        ),
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
        or recipe.scenario_authority_sha
        != materialization.scenario_authority_sha
        or recipe.response_contract_sha != materialization.response_contract_sha
        or recipe.control_case_id != materialization.control_case_id
        or recipe.application_instance_id
        != materialization.application_instance_id
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


def _expected_live_materialization_v2(
    formal_parent_v2: object,
    permit_v2: object,
    scenario_id: str,
) -> _LiveMaterializationReplayV2:
    _text(scenario_id, "scenario_id")
    _require_exact_live_upstream(formal_parent_v2, permit_v2)
    raise ApplicationMaterializationV2UpstreamUnavailable(
        "formal Parent-v2 scenario DAG/recipe-to-factory compiler is not connected"
    )


def _verify_live_factories(
    replay: _LiveMaterializationReplayV2,
) -> None:
    body = verify_application_scenario_materialization_v2_body(
        replay.materialization
    )
    actual = _reverify_verified_factory(replay.actual_factory)
    matched = _reverify_verified_factory(replay.matched_ablated_factory)
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

    def materialize_v3m0_application_scenario_v2(
        formal_parent_v2: object,
        permit_v2: object,
        scenario_id: str,
    ) -> VerifiedV3M0ApplicationScenarioMaterializationV2:
        replay = _expected_live_materialization_v2(
            formal_parent_v2,
            permit_v2,
            scenario_id,
        )
        _verify_live_factories(replay)
        body = replay.materialization
        capability = object.__new__(
            VerifiedV3M0ApplicationScenarioMaterializationV2
        )
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
            raise TypeError(
                "value must be an exact live materialization-v2 capability"
            )
        try:
            seal = value._authority_seal
            binding = registry[value]
        except (AttributeError, KeyError) as exc:
            raise ValueError("materialization-v2 capability identity is not live") from exc
        if seal is not authority_seal:
            raise ValueError("materialization-v2 capability authority seal is forged")
        replay = _expected_live_materialization_v2(
            binding.formal_parent_v2,
            binding.permit_v2,
            binding.scenario_id,
        )
        _verify_live_factories(replay)
        if (
            replay.materialization.materialization_v2_sha
            != binding.materialization_v2_sha
            or replay.actual_factory.factory.factory_sha
            != binding.actual_factory_sha
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
