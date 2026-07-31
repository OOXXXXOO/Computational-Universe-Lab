"""Candidate-only operation DAGs for the pending Parent-v2 refreeze.

The records in this module are inert review objects.  They compile typed,
fully-consumed operation parameters to construction contracts, but issue no
Parent, permit, response block, or scientific status.
"""

from __future__ import annotations

import math
import pickle
import re
import struct
from dataclasses import dataclass, fields as dataclass_fields, replace
from functools import lru_cache
from typing import Literal, Optional

import numpy as np

from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_frozen_tensor,
)


CANDIDATE_SCENARIO_DAG_SCHEMA_VERSION = "v3m0.candidate-scenario-dag.v1"
CANDIDATE_DAG_OPERATION_SCHEMA_VERSION = "v3m0.candidate-dag-operation.v1"
COMPILED_CANDIDATE_CONTRACT_SCHEMA_VERSION = (
    "v3m0.compiled-candidate-scenario-contract.v1"
)
CANDIDATE_SHEAR_STEP_SIGNATURE_SCHEMA_VERSION = (
    "v3m0.candidate-shear-step-signature.v1"
)
CANDIDATE_INCIDENCE_POINT_SCHEMA_VERSION = (
    "v3m0.candidate-incidence-point-contract.v1"
)
CANDIDATE_DAG_CONSTRUCTION_STATE = "PROPOSED_PARENT_DAG_EXTRACT_ONLY"

CANDIDATE_DAG_SCENARIO_IDS = (
    "v3m0.synthetic-control.c05.v1.scenario.phase.v1",
    "v3m0.synthetic-control.c05.v1.scenario.gain.v1",
    "v3m0.synthetic-control.c06.v1.scenario.nonscale-mixing.v1",
    "v3m0.synthetic-control.c07.v1.scenario.constructive.v1",
    "v3m0.synthetic-control.c07.v1.scenario.destructive.v1",
    "v3m0.synthetic-control.c08.v1.scenario.rank-missing.v1",
    "v3m0.synthetic-control.c09.v1.scenario.gauge-dressing.v1",
    "v3m0.synthetic-control.c10.v1.scenario.extra-mode.v1",
    "v3m0.synthetic-control.c11.v1.scenario.signal.v1",
    "v3m0.synthetic-control.c12.v1.scenario.ir-normalization.v1",
    "v3m0.synthetic-control.c15.v1.scenario.full-h.v1",
    "v3m0.synthetic-control.c15.v1.scenario.low-rank-tt.v1",
    "v3m0.synthetic-control.c15.v1.scenario.tt.v1",
    "v3m0.synthetic-control.c15.v1.scenario.tt-plus-row.v1",
    "v3m0.synthetic-control.c16.v1.scenario.coverage-low.v1",
    "v3m0.synthetic-control.c16.v1.scenario.coverage-high.v1",
    "v3m0.synthetic-control.c17.v1.scenario.quotient-gauge.v1",
    "v3m0.synthetic-control.c18.v1.scenario.independent-unary.v1",
    "v3m0.synthetic-control.c19.v1.scenario.observer-collapse.v1",
)

_REVIEWED_PREFLIGHT_SCENARIO_IDS = (
    "v3m0.synthetic-control.c07.v1.scenario.constructive.v1",
    "v3m0.synthetic-control.c07.v1.scenario.destructive.v1",
    "v3m0.synthetic-control.c08.v1.scenario.rank-missing.v1",
    "v3m0.synthetic-control.c10.v1.scenario.extra-mode.v1",
    "v3m0.synthetic-control.c12.v1.scenario.ir-normalization.v1",
)

_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_CHANNEL_ORDER = ("q0", "p0", "q1", "p1")
_CHANNEL_INDEX = {name: index for index, name in enumerate(_CHANNEL_ORDER)}

ParameterKind = Literal["integer", "fp64-bits", "text"]
OperationKind = Literal[
    "local-transition-recipe-v1",
    "closed-form-selector-v1",
    "analytic-causal-contract-v1",
    "incidence-analytic-contract-v1",
]


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
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
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    observed = frozenset(vars(value))
    if observed != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _fp64_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", float(value)))[0]


def _float_from_bits(value: int) -> float:
    if type(value) is not int or not 0 <= value < 2**64:
        raise TypeError("fp64 bits must be an unsigned 64-bit integer")
    result = struct.unpack(">d", struct.pack(">Q", value))[0]
    if not math.isfinite(result):
        raise ValueError("fp64 bits must encode a finite value")
    return result


@dataclass(frozen=True)
class CandidateDAGParameter:
    name: str
    value_kind: ParameterKind
    integer_value: Optional[int]
    fp64_bits_value: Optional[int]
    text_value: Optional[str]

    def __post_init__(self) -> None:
        _text(self.name, "parameter name")
        if self.value_kind not in ("integer", "fp64-bits", "text"):
            raise ValueError("candidate parameter kind is not frozen")
        present = (
            self.integer_value is not None,
            self.fp64_bits_value is not None,
            self.text_value is not None,
        )
        if sum(present) != 1 or not present[
            ("integer", "fp64-bits", "text").index(self.value_kind)
        ]:
            raise ValueError("candidate parameter value does not match its kind")
        if self.integer_value is not None and type(self.integer_value) is not int:
            raise TypeError("integer parameter must be an exact int")
        if self.fp64_bits_value is not None:
            _float_from_bits(self.fp64_bits_value)
        if self.text_value is not None:
            _text(self.text_value, "text parameter")


def candidate_dag_parameter_payload(
    parameter: CandidateDAGParameter,
) -> dict[str, object]:
    _exact_record(parameter, CandidateDAGParameter, "candidate DAG parameter")
    return {
        "name": parameter.name,
        "value_kind": parameter.value_kind,
        "integer_value": parameter.integer_value,
        "fp64_bits_value": parameter.fp64_bits_value,
        "text_value": parameter.text_value,
    }


@dataclass(frozen=True)
class CandidateDAGOperation:
    operation_schema_version: str
    operation_id: str
    operation_kind: OperationKind
    input_operation_ids: tuple[str, ...]
    parameters: tuple[CandidateDAGParameter, ...]
    operation_sha: str

    def __post_init__(self) -> None:
        if self.operation_schema_version != CANDIDATE_DAG_OPERATION_SCHEMA_VERSION:
            raise ValueError("candidate DAG operation schema is not frozen")
        _text(self.operation_id, "operation_id")
        if self.operation_kind not in (
            "local-transition-recipe-v1",
            "closed-form-selector-v1",
            "analytic-causal-contract-v1",
            "incidence-analytic-contract-v1",
        ):
            raise ValueError("candidate DAG operation kind is not frozen")
        if type(self.input_operation_ids) is not tuple:
            raise TypeError("input_operation_ids must be an exact tuple")
        if type(self.parameters) is not tuple or not all(
            type(item) is CandidateDAGParameter for item in self.parameters
        ):
            raise TypeError("parameters have the wrong strict type")
        names = tuple(item.name for item in self.parameters)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise ValueError("candidate operation parameter names are not canonical")
        _sha(self.operation_sha, "operation_sha")


def candidate_dag_operation_payload(
    operation: CandidateDAGOperation,
) -> dict[str, object]:
    _exact_record(operation, CandidateDAGOperation, "candidate DAG operation")
    return {
        "operation_schema_version": operation.operation_schema_version,
        "operation_id": operation.operation_id,
        "operation_kind": operation.operation_kind,
        "input_operation_ids": list(operation.input_operation_ids),
        "parameters": [
            candidate_dag_parameter_payload(item) for item in operation.parameters
        ],
    }


@dataclass(frozen=True)
class CandidateScenarioDAG:
    dag_schema_version: str
    construction_state: Literal["PROPOSED_PARENT_DAG_EXTRACT_ONLY"]
    scenario_id: str
    based_on_candidate_selector_sha: str
    operations: tuple[CandidateDAGOperation, ...]
    output_operation_ids: tuple[str, ...]
    dag_sha: str

    def __post_init__(self) -> None:
        if self.dag_schema_version != CANDIDATE_SCENARIO_DAG_SCHEMA_VERSION:
            raise ValueError("candidate scenario DAG schema is not frozen")
        if self.construction_state != CANDIDATE_DAG_CONSTRUCTION_STATE:
            raise ValueError("candidate scenario DAG claimed authority")
        if self.scenario_id not in CANDIDATE_DAG_SCENARIO_IDS:
            raise ValueError("candidate scenario is not registered")
        _sha(
            self.based_on_candidate_selector_sha,
            "based_on_candidate_selector_sha",
        )
        if type(self.operations) is not tuple or not all(
            type(item) is CandidateDAGOperation for item in self.operations
        ):
            raise TypeError("candidate DAG operations have the wrong strict type")
        if type(self.output_operation_ids) is not tuple:
            raise TypeError("output_operation_ids must be an exact tuple")
        _sha(self.dag_sha, "dag_sha")


def candidate_scenario_dag_payload(
    dag: CandidateScenarioDAG,
) -> dict[str, object]:
    _exact_record(dag, CandidateScenarioDAG, "candidate scenario DAG")
    return {
        "dag_schema_version": dag.dag_schema_version,
        "construction_state": dag.construction_state,
        "scenario_id": dag.scenario_id,
        "based_on_candidate_selector_sha": dag.based_on_candidate_selector_sha,
        "operations": [
            {
                **candidate_dag_operation_payload(item),
                "operation_sha": item.operation_sha,
            }
            for item in dag.operations
        ],
        "output_operation_ids": list(dag.output_operation_ids),
    }


@dataclass(frozen=True)
class CandidateShearStepSignature:
    """Derivation-independent physical signature of one ordered local shear."""

    signature_schema_version: str
    step_id: str
    source_channel: str
    destination_channel: str
    offset: tuple[int, ...]
    coefficient: float
    target_conditioned: bool
    signature_sha: str

    def __post_init__(self) -> None:
        if (
            self.signature_schema_version
            != CANDIDATE_SHEAR_STEP_SIGNATURE_SCHEMA_VERSION
        ):
            raise ValueError("candidate shear signature schema is not frozen")
        _text(self.step_id, "step_id")
        if self.source_channel not in _CHANNEL_INDEX:
            raise ValueError("candidate shear source channel is not frozen")
        if self.destination_channel not in _CHANNEL_INDEX:
            raise ValueError("candidate shear destination channel is not frozen")
        if self.source_channel == self.destination_channel:
            raise ValueError("candidate shear cannot target its source channel")
        if (
            type(self.offset) is not tuple
            or len(self.offset) != 1
            or type(self.offset[0]) is not int
        ):
            raise TypeError("candidate shear offset must be a 1D integer tuple")
        if (
            type(self.coefficient) is not float
            or not math.isfinite(self.coefficient)
            or self.coefficient == 0.0
        ):
            raise TypeError("candidate shear coefficient must be finite non-zero fp64")
        if type(self.target_conditioned) is not bool:
            raise TypeError("target_conditioned must be an exact bool")
        _sha(self.signature_sha, "signature_sha")


def candidate_shear_step_signature_payload(
    signature: CandidateShearStepSignature,
) -> dict[str, object]:
    _exact_record(
        signature,
        CandidateShearStepSignature,
        "candidate shear step signature",
    )
    return {
        "signature_schema_version": signature.signature_schema_version,
        "step_id": signature.step_id,
        "source_channel": signature.source_channel,
        "destination_channel": signature.destination_channel,
        "offset": list(signature.offset),
        "coefficient": signature.coefficient,
        "target_conditioned": signature.target_conditioned,
    }


def _signature(
    step_id: str,
    source_channel: str,
    destination_channel: str,
    coefficient: float,
    *,
    offset: int = 0,
    target_conditioned: bool,
) -> CandidateShearStepSignature:
    provisional = CandidateShearStepSignature(
        signature_schema_version=CANDIDATE_SHEAR_STEP_SIGNATURE_SCHEMA_VERSION,
        step_id=step_id,
        source_channel=source_channel,
        destination_channel=destination_channel,
        offset=(offset,),
        coefficient=float(coefficient),
        target_conditioned=target_conditioned,
        signature_sha="0" * 64,
    )
    return replace(
        provisional,
        signature_sha=canonical_sha(
            candidate_shear_step_signature_payload(provisional)
        ),
    )


@dataclass(frozen=True)
class CandidateIncidencePointContract:
    """Exact cyclotomic incidence wire, with no finite-window measurement."""

    point_schema_version: str
    reciprocal_index: tuple[int, ...]
    momentum: float
    exact_nu_expression: str
    nu_minimal_polynomial_coefficients: tuple[int, ...]
    nu_value: float
    point_sha: str

    def __post_init__(self) -> None:
        if self.point_schema_version != CANDIDATE_INCIDENCE_POINT_SCHEMA_VERSION:
            raise ValueError("candidate incidence point schema is not frozen")
        if (
            type(self.reciprocal_index) is not tuple
            or len(self.reciprocal_index) != 1
            or type(self.reciprocal_index[0]) is not int
        ):
            raise TypeError("reciprocal_index must be a 1D integer tuple")
        if type(self.momentum) is not float or not math.isfinite(self.momentum):
            raise TypeError("incidence momentum must be finite fp64")
        _text(self.exact_nu_expression, "exact_nu_expression")
        if (
            type(self.nu_minimal_polynomial_coefficients) is not tuple
            or not self.nu_minimal_polynomial_coefficients
            or not all(
                type(value) is int
                for value in self.nu_minimal_polynomial_coefficients
            )
        ):
            raise TypeError("incidence minimal polynomial is not an integer tuple")
        if (
            type(self.nu_value) is not float
            or not math.isfinite(self.nu_value)
            or self.nu_value <= 0.0
        ):
            raise TypeError("incidence nu must be positive finite fp64")
        _sha(self.point_sha, "point_sha")


def candidate_incidence_point_contract_payload(
    point: CandidateIncidencePointContract,
) -> dict[str, object]:
    _exact_record(
        point,
        CandidateIncidencePointContract,
        "candidate incidence point",
    )
    return {
        "point_schema_version": point.point_schema_version,
        "reciprocal_index": list(point.reciprocal_index),
        "momentum": point.momentum,
        "exact_nu_expression": point.exact_nu_expression,
        "nu_minimal_polynomial_coefficients": list(
            point.nu_minimal_polynomial_coefficients
        ),
        "nu_value": point.nu_value,
    }


@dataclass(frozen=True)
class CompiledCandidateScenarioContract:
    contract_schema_version: str
    construction_state: Literal["PROPOSED_PARENT_DAG_EXTRACT_ONLY"]
    scenario_id: str
    dag_sha: str
    based_on_candidate_selector_sha: str
    primitive_support_radius: int
    uses_global_fft_projection: bool
    uses_per_k_time_step_projector: bool
    actual_sector_source_columns: tuple[int, ...]
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    expected_matched_actual_sector_rank: int
    expected_matched_full_source_rank: int
    expected_survival_spectrum: tuple[float, ...]
    expected_chi_extra: Optional[float]
    expected_d_proc_state: Literal["defined-v1", "undefined-v1"]
    expected_d_proc_sq: Optional[float]
    proposed_source_selection: FrozenComplexTensor
    proposed_readout_selection: FrozenComplexTensor
    actual_step_signatures: tuple[CandidateShearStepSignature, ...]
    matched_ablated_step_signatures: tuple[CandidateShearStepSignature, ...]
    actual_program_sha: str
    matched_ablated_program_sha: str
    construction_evidence_kind: str
    construction_rule_id: str
    construction_family_id: str
    construction_recipe_sha: str
    construction_operation_dag_sha: str
    recipe_source_injection_sha: str
    recipe_readout_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    response_torus_denominators: tuple[int, ...]
    source_readout_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    source_trial_vectors: FrozenComplexTensor
    geometry_bundle_derivation_id: Optional[str]
    geometry_operation_dag_sha: Optional[str]
    geometry_semantic_sector_names: tuple[str, ...]
    geometry_coverage_control: Optional[float]
    geometry_gauge_amplitude: Optional[float]
    geometry_observer_collapse_expected: Optional[bool]
    incidence_family_id: Optional[str]
    incidence_normalizer_formula_id: Optional[str]
    incidence_application_stage: Optional[
        Literal["POST_RESPONSE_READOUT_ONLY"]
    ]
    incidence_stencil_offsets: tuple[tuple[int, ...], ...]
    incidence_stencil_coefficients: tuple[int, ...]
    ir_limit_order: Optional[int]
    ir_limit_formula_id: Optional[str]
    response_torus_denominator: Optional[int]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    absolute_signal_threshold_authority_ref: Optional[str]
    raw_bridge_noise_evidence_ref: Optional[str]
    raw_noise_absolute_threshold_authority_ref: Optional[str]
    relative_gap_threshold_authority_ref: Optional[str]
    incidence_points: tuple[CandidateIncidencePointContract, ...]
    consumed_parameter_names: tuple[tuple[str, tuple[str, ...]], ...]
    contract_sha: str

    def __post_init__(self) -> None:
        if (
            self.contract_schema_version
            != COMPILED_CANDIDATE_CONTRACT_SCHEMA_VERSION
        ):
            raise ValueError("compiled candidate contract schema is not frozen")
        if self.construction_state != CANDIDATE_DAG_CONSTRUCTION_STATE:
            raise ValueError("compiled candidate contract claimed authority")
        if self.scenario_id not in CANDIDATE_DAG_SCENARIO_IDS:
            raise ValueError("compiled candidate scenario is not registered")
        _sha(self.dag_sha, "dag_sha")
        _sha(
            self.based_on_candidate_selector_sha,
            "based_on_candidate_selector_sha",
        )
        if type(self.primitive_support_radius) is not int:
            raise TypeError("primitive_support_radius must be an exact int")
        if type(self.uses_global_fft_projection) is not bool:
            raise TypeError("uses_global_fft_projection must be an exact bool")
        if type(self.uses_per_k_time_step_projector) is not bool:
            raise TypeError("uses_per_k_time_step_projector must be an exact bool")
        for tensor in (
            self.proposed_source_selection,
            self.proposed_readout_selection,
        ):
            if type(tensor) is not FrozenComplexTensor:
                raise TypeError("compiled selector maps must be frozen tensors")
        for field in (
            "expected_actual_shell_rank",
            "expected_matched_shell_rank",
            "expected_matched_actual_sector_rank",
            "expected_matched_full_source_rank",
        ):
            value = getattr(self, field)
            if type(value) is not int or value < 0:
                raise TypeError(f"{field} must be a nonnegative exact int")
        if self.expected_d_proc_state == "defined-v1":
            if (
                type(self.expected_d_proc_sq) is not float
                or not math.isfinite(self.expected_d_proc_sq)
                or self.expected_d_proc_sq < 0.0
            ):
                raise TypeError("defined d_proc must carry nonnegative fp64")
        elif self.expected_d_proc_state == "undefined-v1":
            if self.expected_d_proc_sq is not None:
                raise ValueError("undefined d_proc cannot carry a value")
        else:
            raise ValueError("expected_d_proc_state is not frozen")
        if (
            type(self.actual_step_signatures) is not tuple
            or not self.actual_step_signatures
            or not all(
                type(item) is CandidateShearStepSignature
                for item in self.actual_step_signatures
            )
        ):
            raise TypeError("actual_step_signatures have the wrong strict type")
        if type(self.matched_ablated_step_signatures) is not tuple or not all(
            type(item) is CandidateShearStepSignature
            for item in self.matched_ablated_step_signatures
        ):
            raise TypeError("matched step signatures have the wrong strict type")
        if self.matched_ablated_step_signatures != tuple(
            item
            for item in self.actual_step_signatures
            if not item.target_conditioned
        ):
            raise ValueError("matched program is not mechanical conditioned deletion")
        _sha(self.actual_program_sha, "actual_program_sha")
        _sha(self.matched_ablated_program_sha, "matched_ablated_program_sha")
        for field in (
            "construction_evidence_kind",
            "construction_rule_id",
            "construction_family_id",
        ):
            _text(getattr(self, field), field)
        for field in (
            "construction_recipe_sha",
            "construction_operation_dag_sha",
            "recipe_source_injection_sha",
            "recipe_readout_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
        ):
            _sha(getattr(self, field), field)
        if (
            type(self.response_torus_denominators) is not tuple
            or not self.response_torus_denominators
            or not all(
                type(value) is int and value > 0
                for value in self.response_torus_denominators
            )
        ):
            raise TypeError("response torus denominators are not frozen")
        for field in (
            "response_reciprocal_indices",
            "source_readout_bridge_reciprocal_indices",
        ):
            indices = getattr(self, field)
            if type(indices) is not tuple or not all(
                type(index) is tuple
                and index
                and all(type(value) is int for value in index)
                for index in indices
            ):
                raise TypeError(f"{field} is not an exact reciprocal grid")
        if (
            type(self.source_readout_bridge_steps) is not tuple
            or not all(
                type(value) is int and value > 0
                for value in self.source_readout_bridge_steps
            )
        ):
            raise TypeError("source/readout bridge steps are not frozen")
        if (
            type(self.reference_reciprocal_index) is not tuple
            or not self.reference_reciprocal_index
            or not all(type(value) is int for value in self.reference_reciprocal_index)
        ):
            raise TypeError("reference reciprocal index is not frozen")
        if type(self.preregistered_phase_bands) is not tuple or not all(
            type(band) is tuple
            and len(band) == 2
            and all(type(value) is float and math.isfinite(value) for value in band)
            and band[0] < band[1]
            for band in self.preregistered_phase_bands
        ):
            raise TypeError("preregistered phase bands are not frozen")
        if type(self.source_trial_vectors) is not FrozenComplexTensor:
            raise TypeError("source trial vectors have the wrong strict type")
        if self.geometry_operation_dag_sha is None:
            if (
                self.geometry_bundle_derivation_id is not None
                or self.geometry_semantic_sector_names
                or self.geometry_coverage_control is not None
                or self.geometry_gauge_amplitude is not None
                or self.geometry_observer_collapse_expected is not None
            ):
                raise ValueError("non-geometry contract carries geometry evidence")
        else:
            _sha(self.geometry_operation_dag_sha, "geometry_operation_dag_sha")
            _text(
                self.geometry_bundle_derivation_id,
                "geometry_bundle_derivation_id",
            )
            if (
                type(self.geometry_semantic_sector_names) is not tuple
                or not self.geometry_semantic_sector_names
                or not all(
                    type(value) is str and bool(value.strip())
                    for value in self.geometry_semantic_sector_names
                )
            ):
                raise TypeError("geometry semantic sectors are not frozen")
            for field in ("geometry_coverage_control", "geometry_gauge_amplitude"):
                value = getattr(self, field)
                if value is not None and (
                    type(value) is not float or not math.isfinite(value)
                ):
                    raise TypeError(f"{field} must be finite fp64 or None")
            if type(self.geometry_observer_collapse_expected) is not bool:
                raise TypeError("geometry observer-collapse flag is not frozen")
        if type(self.incidence_points) is not tuple or not all(
            type(item) is CandidateIncidencePointContract
            for item in self.incidence_points
        ):
            raise TypeError("incidence_points have the wrong strict type")
        has_incidence = self.incidence_family_id is not None
        incidence_fields = (
            self.incidence_normalizer_formula_id,
            self.incidence_application_stage,
            self.ir_limit_order,
            self.ir_limit_formula_id,
            self.response_torus_denominator,
            self.absolute_signal_threshold_authority_ref,
            self.raw_bridge_noise_evidence_ref,
            self.raw_noise_absolute_threshold_authority_ref,
            self.relative_gap_threshold_authority_ref,
        )
        if has_incidence:
            if (
                any(value is None for value in incidence_fields)
                or not self.incidence_points
                or not self.incidence_stencil_offsets
                or not self.incidence_stencil_coefficients
                or not self.response_reciprocal_indices
            ):
                raise ValueError("incidence contract is incomplete")
        elif (
            any(value is not None for value in incidence_fields)
            or self.incidence_points
            or self.incidence_stencil_offsets
            or self.incidence_stencil_coefficients
        ):
            raise ValueError("non-incidence contract carries incidence payload")
        if type(self.consumed_parameter_names) is not tuple:
            raise TypeError("consumed_parameter_names must be an exact tuple")
        _sha(self.contract_sha, "contract_sha")


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {**frozen_tensor_payload(tensor), "tensor_sha": tensor.tensor_sha}


def compiled_candidate_scenario_contract_payload(
    contract: CompiledCandidateScenarioContract,
) -> dict[str, object]:
    _exact_record(
        contract,
        CompiledCandidateScenarioContract,
        "compiled candidate scenario contract",
    )
    return {
        "contract_schema_version": contract.contract_schema_version,
        "construction_state": contract.construction_state,
        "scenario_id": contract.scenario_id,
        "dag_sha": contract.dag_sha,
        "based_on_candidate_selector_sha": (
            contract.based_on_candidate_selector_sha
        ),
        "primitive_support_radius": contract.primitive_support_radius,
        "uses_global_fft_projection": contract.uses_global_fft_projection,
        "uses_per_k_time_step_projector": (
            contract.uses_per_k_time_step_projector
        ),
        "actual_sector_source_columns": list(
            contract.actual_sector_source_columns
        ),
        "expected_actual_shell_rank": contract.expected_actual_shell_rank,
        "expected_matched_shell_rank": contract.expected_matched_shell_rank,
        "expected_matched_actual_sector_rank": (
            contract.expected_matched_actual_sector_rank
        ),
        "expected_matched_full_source_rank": (
            contract.expected_matched_full_source_rank
        ),
        "expected_survival_spectrum": list(
            contract.expected_survival_spectrum
        ),
        "expected_chi_extra": contract.expected_chi_extra,
        "expected_d_proc_state": contract.expected_d_proc_state,
        "expected_d_proc_sq": contract.expected_d_proc_sq,
        "proposed_source_selection": _tensor_record(
            contract.proposed_source_selection
        ),
        "proposed_readout_selection": _tensor_record(
            contract.proposed_readout_selection
        ),
        "actual_step_signatures": [
            {
                **candidate_shear_step_signature_payload(item),
                "signature_sha": item.signature_sha,
            }
            for item in contract.actual_step_signatures
        ],
        "matched_ablated_step_signatures": [
            {
                **candidate_shear_step_signature_payload(item),
                "signature_sha": item.signature_sha,
            }
            for item in contract.matched_ablated_step_signatures
        ],
        "actual_program_sha": contract.actual_program_sha,
        "matched_ablated_program_sha": contract.matched_ablated_program_sha,
        "construction_evidence_kind": contract.construction_evidence_kind,
        "construction_rule_id": contract.construction_rule_id,
        "construction_family_id": contract.construction_family_id,
        "construction_recipe_sha": contract.construction_recipe_sha,
        "construction_operation_dag_sha": (
            contract.construction_operation_dag_sha
        ),
        "recipe_source_injection_sha": contract.recipe_source_injection_sha,
        "recipe_readout_sha": contract.recipe_readout_sha,
        "actual_effect_digest": contract.actual_effect_digest,
        "matched_ablated_effect_digest": contract.matched_ablated_effect_digest,
        "response_torus_denominators": list(
            contract.response_torus_denominators
        ),
        "source_readout_bridge_reciprocal_indices": [
            list(index)
            for index in contract.source_readout_bridge_reciprocal_indices
        ],
        "source_readout_bridge_steps": list(
            contract.source_readout_bridge_steps
        ),
        "reference_reciprocal_index": list(contract.reference_reciprocal_index),
        "preregistered_phase_bands": [
            list(band) for band in contract.preregistered_phase_bands
        ],
        "source_trial_vectors": _tensor_record(contract.source_trial_vectors),
        "geometry_bundle_derivation_id": contract.geometry_bundle_derivation_id,
        "geometry_operation_dag_sha": contract.geometry_operation_dag_sha,
        "geometry_semantic_sector_names": list(
            contract.geometry_semantic_sector_names
        ),
        "geometry_coverage_control": contract.geometry_coverage_control,
        "geometry_gauge_amplitude": contract.geometry_gauge_amplitude,
        "geometry_observer_collapse_expected": (
            contract.geometry_observer_collapse_expected
        ),
        "incidence_family_id": contract.incidence_family_id,
        "incidence_normalizer_formula_id": (
            contract.incidence_normalizer_formula_id
        ),
        "incidence_application_stage": contract.incidence_application_stage,
        "incidence_stencil_offsets": [
            list(item) for item in contract.incidence_stencil_offsets
        ],
        "incidence_stencil_coefficients": list(
            contract.incidence_stencil_coefficients
        ),
        "ir_limit_order": contract.ir_limit_order,
        "ir_limit_formula_id": contract.ir_limit_formula_id,
        "response_torus_denominator": contract.response_torus_denominator,
        "response_reciprocal_indices": [
            list(item) for item in contract.response_reciprocal_indices
        ],
        "absolute_signal_threshold_authority_ref": (
            contract.absolute_signal_threshold_authority_ref
        ),
        "raw_bridge_noise_evidence_ref": (
            contract.raw_bridge_noise_evidence_ref
        ),
        "raw_noise_absolute_threshold_authority_ref": (
            contract.raw_noise_absolute_threshold_authority_ref
        ),
        "relative_gap_threshold_authority_ref": (
            contract.relative_gap_threshold_authority_ref
        ),
        "incidence_points": [
            {
                **candidate_incidence_point_contract_payload(item),
                "point_sha": item.point_sha,
            }
            for item in contract.incidence_points
        ],
        "consumed_parameter_names": [
            [operation_id, list(names)]
            for operation_id, names in contract.consumed_parameter_names
        ],
    }


def _integer(name: str, value: int) -> CandidateDAGParameter:
    return CandidateDAGParameter(name, "integer", int(value), None, None)


def _fp64(name: str, value: float) -> CandidateDAGParameter:
    return CandidateDAGParameter(name, "fp64-bits", None, _fp64_bits(value), None)


def _string(name: str, value: str) -> CandidateDAGParameter:
    return CandidateDAGParameter(name, "text", None, None, value)


def _operation(
    operation_id: str,
    operation_kind: OperationKind,
    input_operation_ids: tuple[str, ...],
    parameters: tuple[CandidateDAGParameter, ...],
) -> CandidateDAGOperation:
    ordered = tuple(sorted(parameters, key=lambda item: item.name))
    provisional = CandidateDAGOperation(
        operation_schema_version=CANDIDATE_DAG_OPERATION_SCHEMA_VERSION,
        operation_id=operation_id,
        operation_kind=operation_kind,
        input_operation_ids=input_operation_ids,
        parameters=ordered,
        operation_sha="0" * 64,
    )
    return replace(
        provisional,
        operation_sha=canonical_sha(candidate_dag_operation_payload(provisional)),
    )


@dataclass(frozen=True)
class _LiveConstructionEvidence:
    scenario_id: str
    based_on_candidate_selector_sha: str
    source_selection: np.ndarray
    readout_selection: np.ndarray
    actual_sector_source_columns: tuple[int, ...]
    actual_steps: tuple[object, ...]
    matched_steps: tuple[object, ...]
    primitive_support_radius: int
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    construction_evidence_kind: str
    construction_rule_id: str
    construction_family_id: str
    construction_recipe_sha: str
    construction_operation_dag_sha: str
    recipe_source_injection_sha: str
    recipe_readout_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    response_torus_denominators: tuple[int, ...]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    geometry_bundle_derivation_id: Optional[str]
    geometry_operation_dag_sha: Optional[str]
    geometry_semantic_sector_names: tuple[str, ...]
    geometry_coverage_control: Optional[float]
    geometry_gauge_amplitude: Optional[float]
    geometry_observer_collapse_expected: Optional[bool]


def _live_candidate_roots() -> tuple[object, object, dict[str, tuple[object, object]]]:
    from .parent_freeze import (
        build_v3m0_parent_freeze_candidate,
        issue_v3m0_parent_freeze,
        verify_parent_freeze_candidate,
    )

    candidate = verify_parent_freeze_candidate(
        build_v3m0_parent_freeze_candidate()
    )
    parent = issue_v3m0_parent_freeze()
    scenarios = {
        scenario.scenario_execution_spec.scenario_id: (application, scenario)
        for application in candidate.application_candidates
        for scenario in application.scenario_candidates
    }
    return candidate, parent, scenarios


def _candidate_operation_binding_sha(
    application: object,
    scenario: object,
) -> str:
    execution = scenario.scenario_execution_spec
    return canonical_sha(
        {
            "dag_schema_version": "v3m0.candidate-v1-operation-dag-binding.v1",
            "candidate_application_sha": application.candidate_application_sha,
            "candidate_scenario_sha": scenario.candidate_scenario_sha,
            "based_on_application_spec_sha": scenario.based_on_application_spec_sha,
            "scenario_execution_spec_sha": execution.scenario_sha,
            "operation_output_ids": list(execution.operation_output_ids),
        }
    )


def _build_live_construction_evidence(
    scenario_id: str,
    based_on_candidate_selector_sha: str,
    *,
    _roots: Optional[
        tuple[object, object, dict[str, tuple[object, object]]]
    ] = None,
) -> _LiveConstructionEvidence:
    """Replay one existing construction source without issuing new authority."""

    from .application_recipes import (
        APPLICATION_C05_TEMPLATE_SCENARIO_IDS,
        APPLICATION_RECIPE_SCENARIO_IDS,
        build_application_recipe,
        build_c05_fejer_recipe_template,
        verify_application_recipe,
        verify_c05_fejer_recipe_template,
    )
    from .c05_projector_recipe import (
        build_c05_projector_orientation_recipe,
        verify_c05_projector_orientation_recipe,
    )
    from .c12_incidence_preflight import (
        C12_SCENARIO_ID,
        build_c12_incidence_preflight,
        verify_c12_incidence_preflight,
    )
    from .geometry_application_recipes import (
        C18_GEOMETRY_SCENARIO_IDS,
        GEOMETRY_APPLICATION_SCENARIO_IDS,
        build_geometry_application_recipe,
        verify_geometry_application_recipe,
    )
    from .interference_mode_preflight import (
        INTERFERENCE_MODE_SCENARIO_IDS,
        build_interference_mode_preflight_artifact,
        verify_interference_mode_preflight_artifact,
    )

    candidate, parent, scenarios = (
        _live_candidate_roots() if _roots is None else _roots
    )
    if scenario_id not in CANDIDATE_DAG_SCENARIO_IDS:
        raise ValueError("scenario is outside the complete success registry")
    try:
        application, candidate_scenario = scenarios[scenario_id]
    except KeyError as exc:
        raise ValueError("scenario is absent from candidate-v1") from exc
    if candidate_scenario.selector_spec.selector_sha != based_on_candidate_selector_sha:
        raise ValueError("candidate DAG selector root differs from candidate-v1")

    template = candidate_scenario.response_template
    selector = candidate_scenario.selector_spec
    source_selection = frozen_tensor_array(selector.source_selector)
    readout_selection = frozen_tensor_array(selector.readout_selector)
    actual_sector = tuple(range(source_selection.shape[1]))
    geometry_bundle_id: Optional[str] = None
    geometry_dag_sha: Optional[str] = None
    geometry_sectors: tuple[str, ...] = ()
    geometry_coverage: Optional[float] = None
    geometry_gauge: Optional[float] = None
    geometry_observer: Optional[bool] = None

    if scenario_id in INTERFERENCE_MODE_SCENARIO_IDS:
        artifact = build_interference_mode_preflight_artifact(candidate, scenario_id)
        verify_interference_mode_preflight_artifact(artifact, candidate)
        source_selection = frozen_tensor_array(artifact.proposed_source_selection)
        readout_selection = frozen_tensor_array(artifact.proposed_readout_selection)
        actual_sector = artifact.actual_sector_source_columns
        actual_steps = artifact.actual_steps
        matched_steps = artifact.matched_ablated_steps
        support = artifact.primitive_support_radius
        actual_rank = artifact.expected_actual_shell_rank
        matched_rank = artifact.expected_matched_shell_rank
        evidence_kind = "INTERFERENCE_MODE_CONSTRUCTION"
        rule_id = artifact.execution_recipe_id
        family_id = f"interference-mode-{artifact.scenario_kind}-v1"
        recipe_sha = artifact.candidate_derivation_sha
        operation_dag_sha = _candidate_operation_binding_sha(
            application,
            candidate_scenario,
        )
        recipe_source_sha = artifact.source_injection.tensor_sha
        recipe_readout_sha = artifact.readout.tensor_sha
        actual_effect = artifact.actual_effect_digest
        matched_effect = artifact.matched_ablated_effect_digest
    elif scenario_id == C12_SCENARIO_ID:
        preflight = build_c12_incidence_preflight(candidate)
        verify_c12_incidence_preflight(candidate, preflight)
        recipe = preflight.recipe
        selector = recipe.proposed_selector_spec
        source_selection = frozen_tensor_array(selector.source_selector)
        readout_selection = frozen_tensor_array(selector.readout_selector)
        actual_sector = tuple(range(source_selection.shape[1]))
        actual_steps = recipe.actual_steps
        matched_steps = recipe.matched_ablated_steps
        support = recipe.primitive_support_radius
        actual_rank = recipe.proposed_expected_shell_rank
        matched_rank = recipe.proposed_expected_shell_rank
        evidence_kind = "C12_INCIDENCE_CONSTRUCTION"
        rule_id = recipe.construction_rule_id
        family_id = recipe.recipe_id
        recipe_sha = recipe.recipe_sha
        operation_dag_sha = _candidate_operation_binding_sha(
            application,
            candidate_scenario,
        )
        recipe_source_sha = selector.source_injection.tensor_sha
        recipe_readout_sha = selector.readout_coisometry.tensor_sha
        actual_effect = recipe.actual_effect_digest
        matched_effect = recipe.matched_ablated_effect_digest
    elif scenario_id in APPLICATION_C05_TEMPLATE_SCENARIO_IDS:
        kind = "phase" if scenario_id.endswith(".phase.v1") else "gain"
        recipe = build_c05_projector_orientation_recipe(kind)
        verify_c05_projector_orientation_recipe(recipe)
        fejer_template = build_c05_fejer_recipe_template(parent, scenario_id)
        verify_c05_fejer_recipe_template(parent, fejer_template)
        actual_steps = recipe.actual_steps
        matched_steps = recipe.matched_ablated_steps
        support = recipe.primitive_support_radius
        actual_rank = recipe.expected_shell_rank
        matched_rank = recipe.expected_shell_rank
        evidence_kind = "C05_PROJECTOR_RECIPE"
        rule_id = recipe.recipe_id
        family_id = recipe.recipe_schema_version
        recipe_sha = recipe.recipe_sha
        operation_dag_sha = fejer_template.template_sha
        recipe_source_sha = recipe.source_injection.tensor_sha
        recipe_readout_sha = recipe.readout.tensor_sha
        actual_effect = recipe.actual_effect_digest
        matched_effect = recipe.matched_ablated_effect_digest
    elif scenario_id in APPLICATION_RECIPE_SCENARIO_IDS:
        recipe = build_application_recipe(parent, scenario_id)
        verify_application_recipe(parent, recipe)
        actual_steps = recipe.actual_steps
        matched_steps = recipe.matched_ablated_steps
        support = recipe.primitive_support_radius
        actual_rank = recipe.expected_shell_rank
        matched_rank = recipe.expected_shell_rank
        evidence_kind = "APPLICATION_LOCAL_RECIPE"
        rule_id = recipe.recipe_id
        family_id = recipe.recipe_schema_version
        recipe_sha = recipe.recipe_sha
        operation_dag_sha = canonical_sha(
            {
                "dag_schema_version": "v3m0.application-evaluated-operation-dag.v1",
                "application_spec_sha": recipe.application_spec_sha,
                "scenario_sha": recipe.scenario_sha,
                "operation_evaluation_shas": [
                    item.evaluation_sha for item in recipe.operation_evaluations
                ],
            }
        )
        recipe_source_sha = recipe.source_injection.tensor_sha
        recipe_readout_sha = recipe.readout.tensor_sha
        actual_effect = recipe.actual_effect_digest
        matched_effect = recipe.matched_ablated_effect_digest
    elif scenario_id in GEOMETRY_APPLICATION_SCENARIO_IDS:
        recipe = build_geometry_application_recipe(parent, scenario_id)
        verify_geometry_application_recipe(parent, recipe)
        actual_steps = recipe.actual_steps
        matched_steps = recipe.matched_ablated_steps
        support = recipe.primitive_support_radius
        actual_rank = recipe.expected_shell_rank
        matched_rank = 2
        actual_sector = (
            (0,)
            if scenario_id in C18_GEOMETRY_SCENARIO_IDS
            else tuple(range(source_selection.shape[1]))
        )
        evidence_kind = "GEOMETRY_LOCAL_RECIPE"
        rule_id = recipe.construction_rule_id
        family_id = recipe.recipe_id
        recipe_sha = recipe.recipe_sha
        operation_dag_sha = recipe.operation_dag_sha
        recipe_source_sha = recipe.source_injection.tensor_sha
        recipe_readout_sha = recipe.readout.tensor_sha
        actual_effect = recipe.actual_effect_digest
        matched_effect = recipe.matched_ablated_effect_digest
        geometry_bundle_id = template.geometry_bundle_derivation_id
        geometry_dag_sha = recipe.operation_dag_sha
        geometry_sectors = recipe.semantic_sector_names
        geometry_coverage = recipe.coverage_control
        geometry_gauge = recipe.gauge_amplitude
        geometry_observer = recipe.observer_collapse_expected
        if scenario_id in C18_GEOMETRY_SCENARIO_IDS and (
            support != 0 or actual_rank != 1 or matched_rank != 2
        ):
            raise ValueError("C18 live support/rank contract is not frozen at 0/1/2")
    else:
        raise ValueError("success scenario has no live construction recipe")

    if matched_steps != tuple(
        step for step in actual_steps if not step.target_conditioned
    ):
        raise ValueError("live recipe matched branch is not mechanical deletion")
    if max(abs(step.offset[0]) for step in actual_steps) > support:
        raise ValueError("live recipe exceeds its declared support radius")
    return _LiveConstructionEvidence(
        scenario_id=scenario_id,
        based_on_candidate_selector_sha=based_on_candidate_selector_sha,
        source_selection=np.array(
            source_selection,
            dtype=np.complex128,
            copy=True,
        ),
        readout_selection=np.array(
            readout_selection,
            dtype=np.complex128,
            copy=True,
        ),
        actual_sector_source_columns=actual_sector,
        actual_steps=actual_steps,
        matched_steps=matched_steps,
        primitive_support_radius=support,
        expected_actual_shell_rank=actual_rank,
        expected_matched_shell_rank=matched_rank,
        construction_evidence_kind=evidence_kind,
        construction_rule_id=rule_id,
        construction_family_id=family_id,
        construction_recipe_sha=recipe_sha,
        construction_operation_dag_sha=operation_dag_sha,
        recipe_source_injection_sha=recipe_source_sha,
        recipe_readout_sha=recipe_readout_sha,
        actual_effect_digest=actual_effect,
        matched_ablated_effect_digest=matched_effect,
        response_torus_denominators=template.response_torus_denominators,
        response_reciprocal_indices=template.response_reciprocal_indices,
        source_readout_bridge_reciprocal_indices=(
            template.source_readout_bridge_reciprocal_indices
        ),
        source_readout_bridge_steps=template.source_readout_bridge_steps,
        reference_reciprocal_index=template.reference_reciprocal_index,
        preregistered_phase_bands=template.preregistered_phase_bands,
        geometry_bundle_derivation_id=geometry_bundle_id,
        geometry_operation_dag_sha=geometry_dag_sha,
        geometry_semantic_sector_names=geometry_sectors,
        geometry_coverage_control=geometry_coverage,
        geometry_gauge_amplitude=geometry_gauge,
        geometry_observer_collapse_expected=geometry_observer,
    )


def _verify_live_construction_evidence(
    evidence: _LiveConstructionEvidence,
    scenario_id: str,
    based_on_candidate_selector_sha: str,
) -> _LiveConstructionEvidence:
    if type(evidence) is not _LiveConstructionEvidence:
        raise TypeError("live construction evidence has the wrong strict type")
    if (
        evidence.scenario_id != scenario_id
        or evidence.based_on_candidate_selector_sha
        != based_on_candidate_selector_sha
    ):
        raise ValueError("live construction evidence is spliced from another root")
    for field in (
        "construction_recipe_sha",
        "construction_operation_dag_sha",
        "recipe_source_injection_sha",
        "recipe_readout_sha",
        "actual_effect_digest",
        "matched_ablated_effect_digest",
    ):
        _sha(getattr(evidence, field), field)
    if (
        type(evidence.source_selection) is not np.ndarray
        or evidence.source_selection.dtype != np.dtype(np.complex128)
        or evidence.source_selection.ndim != 2
        or evidence.source_selection.shape[0] != len(_CHANNEL_ORDER)
        or type(evidence.readout_selection) is not np.ndarray
        or evidence.readout_selection.dtype != np.dtype(np.complex128)
        or evidence.readout_selection.ndim != 2
        or evidence.readout_selection.shape[1] != len(_CHANNEL_ORDER)
    ):
        raise TypeError("live construction selector arrays are not exact complex128 maps")
    if (
        type(evidence.actual_steps) is not tuple
        or not evidence.actual_steps
        or type(evidence.matched_steps) is not tuple
    ):
        raise TypeError("live construction step programs have the wrong strict type")
    for step in evidence.actual_steps:
        for field in (
            "step_id",
            "source_channel",
            "destination_channel",
            "offset",
            "coefficient",
            "target_conditioned",
        ):
            if not hasattr(step, field):
                raise TypeError("live construction step is missing a physical field")
        post_init = getattr(step, "__post_init__", None)
        if post_init is not None:
            post_init()
    if evidence.matched_steps != tuple(
        step for step in evidence.actual_steps if not step.target_conditioned
    ):
        raise ValueError("live evidence matched branch is not mechanical deletion")
    if (
        type(evidence.primitive_support_radius) is not int
        or evidence.primitive_support_radius < 0
        or max(abs(step.offset[0]) for step in evidence.actual_steps)
        > evidence.primitive_support_radius
    ):
        raise ValueError("live evidence support radius does not cover its program")
    for field in (
        "expected_actual_shell_rank",
        "expected_matched_shell_rank",
    ):
        value = getattr(evidence, field)
        if type(value) is not int or value <= 0:
            raise TypeError(f"{field} must be a positive exact integer")
    if scenario_id == (
        "v3m0.synthetic-control.c18.v1.scenario.independent-unary.v1"
    ) and (
        evidence.primitive_support_radius != 0
        or evidence.expected_actual_shell_rank != 1
        or evidence.expected_matched_shell_rank != 2
    ):
        raise ValueError("C18 live support/rank contract is not frozen at 0/1/2")
    return evidence


@lru_cache(maxsize=1)
def _all_live_construction_evidence_bytes(
) -> tuple[tuple[str, str, bytes], ...]:
    """Build the registry once and retain only deeply immutable snapshots."""

    roots = _live_candidate_roots()
    scenarios = roots[2]
    snapshots: list[tuple[str, str, bytes]] = []
    for scenario_id in CANDIDATE_DAG_SCENARIO_IDS:
        try:
            _, source = scenarios[scenario_id]
        except KeyError as exc:
            raise ValueError("scenario is absent from candidate-v1") from exc
        selector_sha = source.selector_spec.selector_sha
        evidence = _verify_live_construction_evidence(
            _build_live_construction_evidence(
                scenario_id,
                selector_sha,
                _roots=roots,
            ),
            scenario_id,
            selector_sha,
        )
        snapshots.append(
            (
                scenario_id,
                selector_sha,
                pickle.dumps(evidence, protocol=pickle.HIGHEST_PROTOCOL),
            )
        )
    if tuple(item[0] for item in snapshots) != CANDIDATE_DAG_SCENARIO_IDS:
        raise ValueError("immutable evidence snapshot registry is incomplete")
    return tuple(snapshots)


def _live_construction_evidence_bytes(
    scenario_id: str,
    based_on_candidate_selector_sha: str,
) -> bytes:
    """Cache only immutable trusted bytes; never a caller-mutable object."""

    matches = tuple(
        payload
        for registered_id, selector_sha, payload in (
            _all_live_construction_evidence_bytes()
        )
        if registered_id == scenario_id
        and selector_sha == based_on_candidate_selector_sha
    )
    if len(matches) != 1:
        raise ValueError("scenario/selector is absent from immutable evidence registry")
    return matches[0]


def _live_construction_evidence(
    scenario_id: str,
    based_on_candidate_selector_sha: str,
) -> _LiveConstructionEvidence:
    """Rebuild and validate a fresh evidence object from immutable cache bytes."""

    evidence = pickle.loads(
        _live_construction_evidence_bytes(
            scenario_id,
            based_on_candidate_selector_sha,
        )
    )
    return _verify_live_construction_evidence(
        evidence,
        scenario_id,
        based_on_candidate_selector_sha,
    )


def _selector_parameters(
    based_on_candidate_selector_sha: str,
    *,
    source: np.ndarray,
    readout: np.ndarray,
    actual_sector_columns: tuple[int, ...],
    source_domain: str,
    selector_disposition: str,
    selector_derivation_id: str,
) -> tuple[CandidateDAGParameter, ...]:
    source_array = np.asarray(source, dtype=np.complex128)
    readout_array = np.asarray(readout, dtype=np.complex128)
    parameters: list[CandidateDAGParameter] = [
        _string(
            "based-on-candidate-selector-sha",
            based_on_candidate_selector_sha,
        ),
        _integer("source-column-count", source_array.shape[1]),
        _string("source-domain", source_domain),
        _integer("full-source-column-count", source_array.shape[1]),
        _integer("readout-row-count", readout_array.shape[0]),
        _integer("actual-sector-column-count", len(actual_sector_columns)),
        _string("selector-disposition", selector_disposition),
        _string("selector-derivation-id", selector_derivation_id),
        _string("source-readout-role", "proposed-parent-selector-v1"),
    ]
    source_terms = tuple(
        (row, column, complex(source_array[row, column]))
        for row in range(source_array.shape[0])
        for column in range(source_array.shape[1])
        if source_array[row, column] != 0.0
    )
    parameters.append(_integer("source-term-count", len(source_terms)))
    for index, (row, column, value) in enumerate(source_terms):
        prefix = f"source-term-{index:03d}"
        parameters.extend(
            (
                _string(f"{prefix}-channel", _CHANNEL_ORDER[row]),
                _integer(f"{prefix}-column", column),
                _fp64(f"{prefix}-real", value.real),
                _fp64(f"{prefix}-imag", value.imag),
            )
        )
    readout_terms = tuple(
        (row, column, complex(readout_array[row, column]))
        for row in range(readout_array.shape[0])
        for column in range(readout_array.shape[1])
        if readout_array[row, column] != 0.0
    )
    parameters.append(_integer("readout-term-count", len(readout_terms)))
    for index, (row, column, value) in enumerate(readout_terms):
        prefix = f"readout-term-{index:03d}"
        parameters.extend(
            (
                _string(f"{prefix}-channel", _CHANNEL_ORDER[column]),
                _integer(f"{prefix}-row", row),
                _fp64(f"{prefix}-real", value.real),
                _fp64(f"{prefix}-imag", value.imag),
            )
        )
    parameters.extend(
        _integer(f"actual-sector-column-{index:03d}", column)
        for index, column in enumerate(actual_sector_columns)
    )
    return tuple(parameters)


def _analytic_contract_parameters(
    *,
    contract_family: str,
    candidate_expected_actual_rank: int,
    expected_actual_rank: int,
    expected_matched_rank: int,
    expected_matched_actual_sector_rank: int,
    expected_matched_full_source_rank: int,
    survival: tuple[float, ...],
    chi_extra: Optional[float],
    d_proc_state: Literal["defined-v1", "undefined-v1"],
    d_proc_sq: Optional[float],
    rank_disposition: str,
) -> tuple[CandidateDAGParameter, ...]:
    parameters: list[CandidateDAGParameter] = [
        _string("contract-family", contract_family),
        _integer(
            "candidate-expected-actual-shell-rank",
            candidate_expected_actual_rank,
        ),
        _integer("expected-actual-shell-rank", expected_actual_rank),
        _integer("expected-matched-shell-rank", expected_matched_rank),
        _integer(
            "expected-matched-actual-sector-rank",
            expected_matched_actual_sector_rank,
        ),
        _integer(
            "expected-matched-full-source-rank",
            expected_matched_full_source_rank,
        ),
        _integer("expected-survival-count", len(survival)),
        _string(
            "expected-chi-extra-state",
            "defined-v1" if chi_extra is not None else "not-frozen-v1",
        ),
        _string("expected-d-proc-state", d_proc_state),
        _string("prediction-semantics", "analytic-preresponse-v1"),
        _string("rank-disposition", rank_disposition),
    ]
    parameters.extend(
        _fp64(f"expected-survival-{index:03d}", value)
        for index, value in enumerate(survival)
    )
    if chi_extra is not None:
        parameters.append(_fp64("expected-chi-extra", chi_extra))
    if d_proc_sq is not None:
        parameters.append(_fp64("expected-d-proc-sq", d_proc_sq))
    return tuple(parameters)


def _common_transition_parameters(
    family: str,
    *,
    support_radius: int,
) -> list[CandidateDAGParameter]:
    return [
        _string("ablation-policy", "delete-target-conditioned-slots-v1"),
        _string("channel-order", "q0,p0,q1,p1"),
        _integer("primitive-support-radius", support_radius),
        _string("transition-family", family),
        _integer("uses-global-fft-projection", 0),
        _integer("uses-per-k-timestep-projector", 0),
    ]


def _indexed_tuple_parameters(
    prefix: str,
    values: tuple[tuple[int, ...], ...],
) -> tuple[CandidateDAGParameter, ...]:
    parameters: list[CandidateDAGParameter] = [
        _integer(f"{prefix}-count", len(values))
    ]
    for index, value in enumerate(values):
        parameters.append(_integer(f"{prefix}-{index:03d}-dimension", len(value)))
        parameters.extend(
            _integer(f"{prefix}-{index:03d}-{axis:03d}", coordinate)
            for axis, coordinate in enumerate(value)
        )
    return tuple(parameters)


def _construction_context_parameters(
    evidence: _LiveConstructionEvidence,
) -> tuple[CandidateDAGParameter, ...]:
    parameters: list[CandidateDAGParameter] = [
        _string("context-construction-evidence-kind", evidence.construction_evidence_kind),
        _string("context-construction-rule-id", evidence.construction_rule_id),
        _string("context-construction-family-id", evidence.construction_family_id),
        _string("context-construction-recipe-sha", evidence.construction_recipe_sha),
        _string(
            "context-construction-operation-dag-sha",
            evidence.construction_operation_dag_sha,
        ),
        _string(
            "context-recipe-source-injection-sha",
            evidence.recipe_source_injection_sha,
        ),
        _string("context-recipe-readout-sha", evidence.recipe_readout_sha),
        _string("context-actual-effect-digest", evidence.actual_effect_digest),
        _string(
            "context-matched-ablated-effect-digest",
            evidence.matched_ablated_effect_digest,
        ),
        _integer(
            "context-response-torus-denominator-count",
            len(evidence.response_torus_denominators),
        ),
        _integer(
            "context-source-readout-bridge-step-count",
            len(evidence.source_readout_bridge_steps),
        ),
        _integer(
            "context-reference-reciprocal-index-dimension",
            len(evidence.reference_reciprocal_index),
        ),
        _integer(
            "context-preregistered-phase-band-count",
            len(evidence.preregistered_phase_bands),
        ),
        _string(
            "context-source-trial-vector-rule",
            "identity-in-proposed-source-column-space-v1",
        ),
        _integer(
            "context-source-trial-vector-count",
            evidence.source_selection.shape[1],
        ),
    ]
    parameters.extend(
        _integer(f"context-response-torus-denominator-{index:03d}", value)
        for index, value in enumerate(evidence.response_torus_denominators)
    )
    parameters.extend(
        _indexed_tuple_parameters(
            "context-response-reciprocal-index",
            evidence.response_reciprocal_indices,
        )
    )
    parameters.extend(
        _indexed_tuple_parameters(
            "context-source-readout-bridge-reciprocal-index",
            evidence.source_readout_bridge_reciprocal_indices,
        )
    )
    parameters.extend(
        _integer(f"context-source-readout-bridge-step-{index:03d}", value)
        for index, value in enumerate(evidence.source_readout_bridge_steps)
    )
    parameters.extend(
        _integer(f"context-reference-reciprocal-index-{index:03d}", value)
        for index, value in enumerate(evidence.reference_reciprocal_index)
    )
    for index, band in enumerate(evidence.preregistered_phase_bands):
        parameters.extend(
            (
                _fp64(f"context-preregistered-phase-band-{index:03d}-lower", band[0]),
                _fp64(f"context-preregistered-phase-band-{index:03d}-upper", band[1]),
            )
        )
    has_geometry = evidence.geometry_operation_dag_sha is not None
    parameters.append(_integer("context-geometry-present", int(has_geometry)))
    if has_geometry:
        assert evidence.geometry_bundle_derivation_id is not None
        assert evidence.geometry_operation_dag_sha is not None
        assert evidence.geometry_observer_collapse_expected is not None
        parameters.extend(
            (
                _string(
                    "context-geometry-bundle-derivation-id",
                    evidence.geometry_bundle_derivation_id,
                ),
                _string(
                    "context-geometry-operation-dag-sha",
                    evidence.geometry_operation_dag_sha,
                ),
                _integer(
                    "context-geometry-semantic-sector-count",
                    len(evidence.geometry_semantic_sector_names),
                ),
                _integer(
                    "context-geometry-observer-collapse-expected",
                    int(evidence.geometry_observer_collapse_expected),
                ),
                _integer(
                    "context-geometry-coverage-control-present",
                    int(evidence.geometry_coverage_control is not None),
                ),
                _integer(
                    "context-geometry-gauge-amplitude-present",
                    int(evidence.geometry_gauge_amplitude is not None),
                ),
            )
        )
        parameters.extend(
            _string(f"context-geometry-semantic-sector-{index:03d}", value)
            for index, value in enumerate(evidence.geometry_semantic_sector_names)
        )
        if evidence.geometry_coverage_control is not None:
            parameters.append(
                _fp64(
                    "context-geometry-coverage-control",
                    evidence.geometry_coverage_control,
                )
            )
        if evidence.geometry_gauge_amplitude is not None:
            parameters.append(
                _fp64(
                    "context-geometry-gauge-amplitude",
                    evidence.geometry_gauge_amplitude,
                )
            )
    return tuple(parameters)


def _live_step_parameters(
    steps: tuple[object, ...],
) -> tuple[CandidateDAGParameter, ...]:
    parameters: list[CandidateDAGParameter] = [
        _integer("live-step-count", len(steps))
    ]
    for index, step in enumerate(steps):
        prefix = f"live-step-{index:03d}"
        parameters.extend(
            (
                _string(f"{prefix}-id", step.step_id),
                _string(f"{prefix}-source-channel", step.source_channel),
                _string(f"{prefix}-destination-channel", step.destination_channel),
                _integer(f"{prefix}-offset", step.offset[0]),
                _fp64(f"{prefix}-coefficient", step.coefficient),
                _integer(
                    f"{prefix}-target-conditioned",
                    int(step.target_conditioned),
                ),
            )
        )
    return tuple(parameters)


def _generic_live_recipe_operations(
    evidence: _LiveConstructionEvidence,
) -> tuple[CandidateDAGOperation, ...]:
    scenario_id = evidence.scenario_id
    transition_id = f"{scenario_id}.00-local-transition"
    selector_id = f"{scenario_id}.01-closed-form-selector"
    contract_id = f"{scenario_id}.02-analytic-contract"
    transition_parameters = _common_transition_parameters(
        "closed-live-recipe-shear-program-v1",
        support_radius=evidence.primitive_support_radius,
    )
    transition_parameters.extend(_live_step_parameters(evidence.actual_steps))
    transition = _operation(
        transition_id,
        "local-transition-recipe-v1",
        (),
        tuple(transition_parameters),
    )
    selector = _operation(
        selector_id,
        "closed-form-selector-v1",
        (),
        _selector_parameters(
            evidence.based_on_candidate_selector_sha,
            source=evidence.source_selection,
            readout=evidence.readout_selection,
            actual_sector_columns=evidence.actual_sector_source_columns,
            source_domain="candidate-v1-exact-selector-v1",
            selector_disposition="requires-parent-selector-refreeze-v1",
            selector_derivation_id="candidate-v1-selector-closed-replay-v1",
        ),
    )
    source_count = evidence.source_selection.shape[1]
    sector_count = len(evidence.actual_sector_source_columns)
    contract = _operation(
        contract_id,
        "analytic-causal-contract-v1",
        (transition_id, selector_id),
        (
            *_analytic_contract_parameters(
                contract_family="live-recipe-construction-contract-v1",
                candidate_expected_actual_rank=evidence.expected_actual_shell_rank,
                expected_actual_rank=evidence.expected_actual_shell_rank,
                expected_matched_rank=evidence.expected_matched_shell_rank,
                expected_matched_actual_sector_rank=min(
                    evidence.expected_matched_shell_rank,
                    sector_count,
                ),
                expected_matched_full_source_rank=min(
                    evidence.expected_matched_shell_rank,
                    source_count,
                ),
                survival=(),
                chi_extra=None,
                d_proc_state="undefined-v1",
                d_proc_sq=None,
                rank_disposition="live-recipe-rank-closure-v1",
            ),
            *_construction_context_parameters(evidence),
        ),
    )
    return transition, selector, contract


def _attach_construction_context(
    operations: tuple[CandidateDAGOperation, ...],
    evidence: _LiveConstructionEvidence,
) -> tuple[CandidateDAGOperation, ...]:
    contract = operations[-1]
    enriched = _operation(
        contract.operation_id,
        contract.operation_kind,
        contract.input_operation_ids,
        (*contract.parameters, *_construction_context_parameters(evidence)),
    )
    return (*operations[:-1], enriched)


def _interference_operations(
    scenario_id: str,
    based_on_candidate_selector_sha: str,
    *,
    family: str,
    source: np.ndarray,
    readout: np.ndarray,
    actual_sector_columns: tuple[int, ...],
    source_domain: str,
    selector_derivation_id: str,
    contract_family: str,
    expected_actual_rank: int,
    expected_matched_rank: int,
    expected_matched_actual_sector_rank: int,
    expected_matched_full_source_rank: int,
    survival: tuple[float, ...],
    chi_extra: float,
    d_proc_state: Literal["defined-v1", "undefined-v1"],
    d_proc_sq: Optional[float],
    rank_disposition: str,
) -> tuple[CandidateDAGOperation, ...]:
    prefix = scenario_id
    transition_id = f"{prefix}.00-local-transition"
    selector_id = f"{prefix}.01-closed-form-selector"
    contract_id = f"{prefix}.02-analytic-contract"
    transition_parameters = _common_transition_parameters(
        family,
        support_radius=0,
    )
    if family == "c07-constructive-complementary-rotation-v1":
        transition_parameters.extend(
            (
                _integer("carrier-mode", 0),
                _integer("conditioned-mode", 0),
                _fp64("delta-radians", math.pi / 8192.0),
                _string(
                    "matched-angle-formula",
                    "pi-over-two-minus-delta-v1",
                ),
                _integer("spectator-mode", 1),
                _integer("spectator-quarter-turn-count", 2),
                _integer("spectator-quarter-turn-sign", 1),
            )
        )
    elif family in (
        "c07-destructive-swap-conjugation-v1",
        "c10-extra-mode-swap-conjugation-v1",
    ):
        transition_parameters.extend(
            (
                _integer("blind-mode0-quarter-turn-sign", 1),
                _integer("blind-mode1-quarter-turn-count", 2),
                _integer("blind-mode1-quarter-turn-sign", 1),
                _string(
                    "conditioned-conjugation",
                    "inverse-swap-before-forward-swap-after-v1",
                ),
                _string(
                    "mode-swap-shear-grammar",
                    "six-shear-two-canonical-pairs-v1",
                ),
            )
        )
        if family == "c10-extra-mode-swap-conjugation-v1":
            transition_parameters.extend(
                (
                    _integer("actual-source-axis", 0),
                    _integer("independent-new-source-axis", 1),
                    _fp64("new-source-axis-amplitude", 1.0),
                )
            )
    elif family == "c08-conditioned-mode1-deletion-v1":
        transition_parameters.extend(
            (
                _integer("blind-mode0-quarter-turn-sign", 1),
                _integer("blind-mode1-quarter-turn-count", 2),
                _integer("blind-mode1-quarter-turn-sign", 1),
                _integer("conditioned-delete-mode", 1),
                _integer("conditioned-quarter-turn-sign", -1),
            )
        )
    else:
        raise ValueError("interference transition family is not registered")
    transition = _operation(
        transition_id,
        "local-transition-recipe-v1",
        (),
        tuple(transition_parameters),
    )
    selector = _operation(
        selector_id,
        "closed-form-selector-v1",
        (),
        _selector_parameters(
            based_on_candidate_selector_sha,
            source=source,
            readout=readout,
            actual_sector_columns=actual_sector_columns,
            source_domain=source_domain,
            selector_disposition="requires-parent-selector-refreeze-v1",
            selector_derivation_id=selector_derivation_id,
        ),
    )
    contract = _operation(
        contract_id,
        "analytic-causal-contract-v1",
        (transition_id, selector_id),
        _analytic_contract_parameters(
            contract_family=contract_family,
            candidate_expected_actual_rank=1,
            expected_actual_rank=expected_actual_rank,
            expected_matched_rank=expected_matched_rank,
            expected_matched_actual_sector_rank=(
                expected_matched_actual_sector_rank
            ),
            expected_matched_full_source_rank=expected_matched_full_source_rank,
            survival=survival,
            chi_extra=chi_extra,
            d_proc_state=d_proc_state,
            d_proc_sq=d_proc_sq,
            rank_disposition=rank_disposition,
        ),
    )
    return (transition, selector, contract)


def _closed_c12_source() -> np.ndarray:
    root_two = math.sqrt(2.0)
    half_root_two = 1.0 / (2.0 * root_two)
    frame = np.asarray(
        (
            (1.0 / root_two, 0.0, 1.0 / root_two, 0.0),
            (
                -1.0j * half_root_two,
                -0.5 + 1.0j * half_root_two,
                1.0j * half_root_two,
                0.5 - 1.0j * half_root_two,
            ),
            (0.0, 1.0 / root_two, 0.0, 1.0 / root_two),
            (
                0.5 + 1.0j * half_root_two,
                1.0j * half_root_two,
                -0.5 - 1.0j * half_root_two,
                -1.0j * half_root_two,
            ),
        ),
        dtype=np.complex128,
    )
    return frame[:, :2]


def _c12_operations(
    scenario_id: str,
    based_on_candidate_selector_sha: str,
) -> tuple[CandidateDAGOperation, ...]:
    transition_id = f"{scenario_id}.00-local-transition"
    selector_id = f"{scenario_id}.01-closed-form-selector"
    contract_id = f"{scenario_id}.02-incidence-analytic-contract"
    transition_parameters = _common_transition_parameters(
        "c12-common-geometry-incidence-carrier-v1",
        support_radius=1,
    )
    transition_parameters.extend(
        (
            _string("construction-rule-id", "c12-rank-two-local-incidence-carrier-v1"),
            _integer("state-count", 4),
            _fp64("common-alpha-radians", math.pi / 8.0),
            _fp64("common-beta-radians", -math.pi / 4.0),
            _fp64("conditioning-angle-radians", 1.0 / 8.0),
            _fp64("carrier-mode0-angle-radians", math.pi / 2.0),
            _fp64("carrier-mode1-angle-radians", -math.pi / 2.0),
            _integer("reciprocal-shear-radius", 1),
            _string(
                "ordered-composite",
                "mix-inverse-common-blind-mix-forward-v1",
            ),
        )
    )
    transition = _operation(
        transition_id,
        "local-transition-recipe-v1",
        (),
        tuple(transition_parameters),
    )
    selector = _operation(
        selector_id,
        "closed-form-selector-v1",
        (),
        _selector_parameters(
            based_on_candidate_selector_sha,
            source=_closed_c12_source(),
            readout=np.eye(4, dtype=np.complex128),
            actual_sector_columns=(0, 1),
            source_domain="rank-two-semantic-frame-v1",
            selector_disposition=(
                "requires-parent-selector-and-rank-refreeze-v1"
            ),
            selector_derivation_id=(
                "analytic-common-geometry-semantic-frame-first-two-columns-v1"
            ),
        ),
    )
    contract_parameters = list(
        _analytic_contract_parameters(
            contract_family="c12-incidence-analytic-contract-v1",
            candidate_expected_actual_rank=1,
            expected_actual_rank=2,
            expected_matched_rank=2,
            expected_matched_actual_sector_rank=2,
            expected_matched_full_source_rank=2,
            survival=(),
            chi_extra=0.0,
            d_proc_state="undefined-v1",
            d_proc_sq=None,
            rank_disposition="requires-parent-rank-refreeze-1-to-2-v1",
        )
    )
    contract_parameters.extend(
        (
            _string(
                "incidence-family-id",
                "synthetic-lattice-laplacian-incidence-v1",
            ),
            _string(
                "incidence-normalizer-formula-id",
                "nu-inc-4-sum-sin2-half-v1",
            ),
            _string(
                "incidence-application-stage",
                "POST_RESPONSE_READOUT_ONLY",
            ),
            _integer("response-torus-denominator", 8),
            _integer("response-reciprocal-index-count", 2),
            _integer("stencil-point-count", 3),
            _integer("stencil-offset-000", -1),
            _integer("stencil-offset-001", 0),
            _integer("stencil-offset-002", 1),
            _integer("stencil-coefficient-000", -1),
            _integer("stencil-coefficient-001", 2),
            _integer("stencil-coefficient-002", -1),
            _integer("ir-limit-order", 2),
            _fp64("ir-limit-value", 1.0),
            _string(
                "ir-limit-formula-id",
                "lim-k-to-zero-nu-inc-over-k-squared-equals-one-v1",
            ),
            _string(
                "first-brillouin-domain-id",
                "one-dimensional-minus-pi-open-pi-closed-v1",
            ),
            _string(
                "absolute-signal-threshold-authority-ref",
                "WindowThresholdSelection.curv_tau_sig",
            ),
            _string(
                "raw-bridge-noise-evidence-ref",
                "SourceReadoutBridgeAudit.curv_operator_error_max",
            ),
            _string(
                "raw-noise-absolute-threshold-authority-ref",
                "rulespace_v3.thresholds.BRIDGE_TOLERANCE",
            ),
            _string(
                "relative-gap-threshold-authority-ref",
                "rulespace_v3.thresholds.RAW_GAP_MIN",
            ),
            _integer("mode-0-reciprocal-index", 1),
            _fp64("mode-0-momentum", math.pi / 4.0),
            _integer("mode-0-root-of-unity-order", 8),
            _integer("mode-0-root-of-unity-power", 1),
            _string("mode-0-exact-nu-expression", "2 - sqrt(2)"),
            _integer("mode-0-minpoly-count", 3),
            _integer("mode-0-minpoly-000", 1),
            _integer("mode-0-minpoly-001", -4),
            _integer("mode-0-minpoly-002", 2),
            _fp64("mode-0-nu", 2.0 - math.sqrt(2.0)),
            _integer("mode-1-reciprocal-index", 2),
            _fp64("mode-1-momentum", math.pi / 2.0),
            _integer("mode-1-root-of-unity-order", 8),
            _integer("mode-1-root-of-unity-power", 2),
            _string("mode-1-exact-nu-expression", "2"),
            _integer("mode-1-minpoly-count", 2),
            _integer("mode-1-minpoly-000", 1),
            _integer("mode-1-minpoly-001", -2),
            _fp64("mode-1-nu", 2.0),
        )
    )
    contract = _operation(
        contract_id,
        "incidence-analytic-contract-v1",
        (transition_id, selector_id),
        tuple(contract_parameters),
    )
    return (transition, selector, contract)


def _scenario_operations(
    scenario_id: str,
    based_on_candidate_selector_sha: str,
) -> tuple[CandidateDAGOperation, ...]:
    evidence = _live_construction_evidence(
        scenario_id,
        based_on_candidate_selector_sha,
    )
    operations: Optional[tuple[CandidateDAGOperation, ...]] = None
    if scenario_id == _REVIEWED_PREFLIGHT_SCENARIO_IDS[0]:
        operations = _interference_operations(
            scenario_id,
            based_on_candidate_selector_sha,
            family="c07-constructive-complementary-rotation-v1",
            source=np.asarray(((1.0,), (0.0,), (0.0,), (0.0,))),
            readout=np.asarray(((0.0, 1.0, 0.0, 0.0),)),
            actual_sector_columns=(0,),
            source_domain="actual-equals-full-v1",
            selector_derivation_id="c07-constructive-q0-p0-selector-v1",
            contract_family="c07-constructive-analytic-contract-v1",
            expected_actual_rank=1,
            expected_matched_rank=1,
            expected_matched_actual_sector_rank=1,
            expected_matched_full_source_rank=1,
            survival=(1.0,),
            chi_extra=0.0,
            d_proc_state="defined-v1",
            d_proc_sq=0.0,
            rank_disposition="candidate-rank-unchanged-v1",
        )
    elif scenario_id == _REVIEWED_PREFLIGHT_SCENARIO_IDS[1]:
        operations = _interference_operations(
            scenario_id,
            based_on_candidate_selector_sha,
            family="c07-destructive-swap-conjugation-v1",
            source=np.asarray(
                ((0.5,), (0.0,), (math.sqrt(3.0) / 2.0,), (0.0,))
            ),
            readout=np.asarray(
                ((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
            ),
            actual_sector_columns=(0,),
            source_domain="actual-equals-full-v1",
            selector_derivation_id="c07-destructive-q0-q1-p0-p1-selector-v1",
            contract_family="c07-destructive-analytic-contract-v1",
            expected_actual_rank=1,
            expected_matched_rank=1,
            expected_matched_actual_sector_rank=1,
            expected_matched_full_source_rank=1,
            survival=(0.0,),
            chi_extra=1.0,
            d_proc_state="defined-v1",
            d_proc_sq=1.0,
            rank_disposition="candidate-rank-unchanged-v1",
        )
    elif scenario_id == _REVIEWED_PREFLIGHT_SCENARIO_IDS[2]:
        operations = _interference_operations(
            scenario_id,
            based_on_candidate_selector_sha,
            family="c08-conditioned-mode1-deletion-v1",
            source=np.asarray(
                ((1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (0.0, 0.0))
            ),
            readout=np.asarray(
                ((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
            ),
            actual_sector_columns=(0, 1),
            source_domain="actual-equals-full-v1",
            selector_derivation_id="c08-rank-two-q0-q1-p0-p1-selector-v1",
            contract_family="c08-rank-missing-analytic-contract-v1",
            expected_actual_rank=2,
            expected_matched_rank=1,
            expected_matched_actual_sector_rank=1,
            expected_matched_full_source_rank=1,
            survival=(0.0, 1.0),
            chi_extra=0.0,
            d_proc_state="defined-v1",
            d_proc_sq=0.5,
            rank_disposition="requires-parent-rank-refreeze-1-to-2-v1",
        )
    elif scenario_id == _REVIEWED_PREFLIGHT_SCENARIO_IDS[3]:
        operations = _interference_operations(
            scenario_id,
            based_on_candidate_selector_sha,
            family="c10-extra-mode-swap-conjugation-v1",
            source=np.asarray(
                ((0.0, 1.0), (0.0, 0.0), (1.0, 0.0), (0.0, 0.0))
            ),
            readout=np.asarray(
                ((0.0, 0.0, 0.0, 1.0), (0.0, 1.0, 0.0, 0.0))
            ),
            actual_sector_columns=(0,),
            source_domain="actual-first-column-full-two-column-v1",
            selector_derivation_id="c10-full-source-extra-mode-selector-v1",
            contract_family="c10-extra-mode-analytic-contract-v1",
            expected_actual_rank=1,
            expected_matched_rank=1,
            expected_matched_actual_sector_rank=0,
            expected_matched_full_source_rank=1,
            survival=(0.0,),
            chi_extra=1.0,
            d_proc_state="undefined-v1",
            d_proc_sq=None,
            rank_disposition="candidate-rank-unchanged-v1",
        )
    elif scenario_id == _REVIEWED_PREFLIGHT_SCENARIO_IDS[4]:
        operations = _c12_operations(
            scenario_id,
            based_on_candidate_selector_sha,
        )
    if operations is not None:
        return _attach_construction_context(operations, evidence)
    return _generic_live_recipe_operations(evidence)


def _build_candidate_scenario_dag(
    scenario_id: str,
    based_on_candidate_selector_sha: str,
) -> CandidateScenarioDAG:
    operations = _scenario_operations(
        scenario_id,
        based_on_candidate_selector_sha,
    )
    provisional = CandidateScenarioDAG(
        dag_schema_version=CANDIDATE_SCENARIO_DAG_SCHEMA_VERSION,
        construction_state=CANDIDATE_DAG_CONSTRUCTION_STATE,
        scenario_id=scenario_id,
        based_on_candidate_selector_sha=based_on_candidate_selector_sha,
        operations=operations,
        output_operation_ids=(operations[-1].operation_id,),
        dag_sha="0" * 64,
    )
    return replace(
        provisional,
        dag_sha=canonical_sha(candidate_scenario_dag_payload(provisional)),
    )


def build_candidate_scenario_dag(
    scenario_id: str,
    *,
    based_on_candidate_selector_sha: str,
) -> CandidateScenarioDAG:
    """Build one detached, candidate-only typed DAG."""

    return verify_candidate_scenario_dag(
        _build_candidate_scenario_dag(
            scenario_id,
            based_on_candidate_selector_sha,
        )
    )


def build_all_candidate_scenario_dags(
    selector_bindings: tuple[tuple[str, str], ...],
) -> tuple[CandidateScenarioDAG, ...]:
    """Build the exact nineteen-success-scenario registry in canonical order."""

    if (
        type(selector_bindings) is not tuple
        or tuple(item[0] for item in selector_bindings)
        != CANDIDATE_DAG_SCENARIO_IDS
        or not all(type(item) is tuple and len(item) == 2 for item in selector_bindings)
    ):
        raise ValueError("selector bindings do not cover the canonical registry")
    return tuple(
        build_candidate_scenario_dag(
            scenario_id,
            based_on_candidate_selector_sha=selector_sha,
        )
        for scenario_id, selector_sha in selector_bindings
    )


def _validate_operation(operation: CandidateDAGOperation) -> None:
    _exact_record(operation, CandidateDAGOperation, "candidate DAG operation")
    operation.__post_init__()
    for parameter in operation.parameters:
        _exact_record(parameter, CandidateDAGParameter, "candidate DAG parameter")
        parameter.__post_init__()
    if operation.operation_sha != canonical_sha(
        candidate_dag_operation_payload(operation)
    ):
        raise ValueError("candidate DAG operation SHA does not replay")


def verify_candidate_scenario_dag(
    dag: CandidateScenarioDAG,
) -> CandidateScenarioDAG:
    """Fail closed against the unique canonical candidate DAG."""

    _exact_record(dag, CandidateScenarioDAG, "candidate scenario DAG")
    dag.__post_init__()
    for operation in dag.operations:
        _validate_operation(operation)
    operation_ids = tuple(item.operation_id for item in dag.operations)
    if len(operation_ids) != 3 or len(set(operation_ids)) != 3:
        raise ValueError("candidate scenario DAG must contain exactly three nodes")
    known: set[str] = set()
    for operation in dag.operations:
        if any(item not in known for item in operation.input_operation_ids):
            raise ValueError("candidate scenario DAG is cyclic or out of order")
        known.add(operation.operation_id)
    if dag.output_operation_ids != (dag.operations[-1].operation_id,):
        raise ValueError("candidate scenario DAG output is not unique")
    if dag.dag_sha != canonical_sha(candidate_scenario_dag_payload(dag)):
        raise ValueError("candidate scenario DAG SHA does not replay")
    expected = _build_candidate_scenario_dag(
        dag.scenario_id,
        dag.based_on_candidate_selector_sha,
    )
    if dag != expected:
        raise ValueError("candidate scenario DAG differs from canonical replay")
    return dag


class _Reader:
    def __init__(self, operation: CandidateDAGOperation) -> None:
        self.operation = operation
        self.by_name = {item.name: item for item in operation.parameters}
        if len(self.by_name) != len(operation.parameters):
            raise ValueError("candidate DAG contains duplicate parameter names")
        self.consumed: set[str] = set()

    def _take(self, name: str, kind: ParameterKind) -> CandidateDAGParameter:
        try:
            parameter = self.by_name[name]
        except KeyError as exc:
            raise ValueError(f"candidate DAG parameter {name!r} is missing") from exc
        if parameter.value_kind != kind:
            raise ValueError(f"candidate DAG parameter {name!r} has the wrong kind")
        self.consumed.add(name)
        return parameter

    def integer(self, name: str) -> int:
        value = self._take(name, "integer").integer_value
        assert value is not None
        return value

    def fp64(self, name: str) -> float:
        value = self._take(name, "fp64-bits").fp64_bits_value
        assert value is not None
        return _float_from_bits(value)

    def text(self, name: str) -> str:
        value = self._take(name, "text").text_value
        assert value is not None
        return value

    def finish(self) -> tuple[str, ...]:
        names = tuple(item.name for item in self.operation.parameters)
        if self.consumed != set(names):
            unused = sorted(set(names) - self.consumed)
            raise ValueError(f"candidate DAG has unconsumed parameters: {unused!r}")
        return names


def _sparse_selector(
    reader: _Reader,
) -> tuple[np.ndarray, np.ndarray, tuple[int, ...]]:
    if reader.text("selector-disposition") not in (
        "requires-parent-selector-refreeze-v1",
        "requires-parent-selector-and-rank-refreeze-v1",
    ):
        raise ValueError("candidate selector disposition claimed authority")
    if reader.text("source-readout-role") != "proposed-parent-selector-v1":
        raise ValueError("candidate selector role claimed current authority")
    _text(reader.text("selector-derivation-id"), "selector derivation")
    _text(reader.text("source-domain"), "source domain")
    source_columns = reader.integer("source-column-count")
    source_terms = reader.integer("source-term-count")
    source = np.zeros((4, source_columns), dtype=np.complex128)
    for index in range(source_terms):
        prefix = f"source-term-{index:03d}"
        column = reader.integer(f"{prefix}-column")
        channel = reader.text(f"{prefix}-channel")
        value = complex(
            reader.fp64(f"{prefix}-real"),
            reader.fp64(f"{prefix}-imag"),
        )
        if channel not in _CHANNEL_INDEX or not 0 <= column < source_columns:
            raise ValueError("source selector sparse term is out of range")
        source[_CHANNEL_INDEX[channel], column] += value
    readout_rows = reader.integer("readout-row-count")
    readout_terms = reader.integer("readout-term-count")
    readout = np.zeros((readout_rows, 4), dtype=np.complex128)
    for index in range(readout_terms):
        prefix = f"readout-term-{index:03d}"
        row = reader.integer(f"{prefix}-row")
        channel = reader.text(f"{prefix}-channel")
        value = complex(
            reader.fp64(f"{prefix}-real"),
            reader.fp64(f"{prefix}-imag"),
        )
        if channel not in _CHANNEL_INDEX or not 0 <= row < readout_rows:
            raise ValueError("readout selector sparse term is out of range")
        readout[row, _CHANNEL_INDEX[channel]] += value
    sector_count = reader.integer("actual-sector-column-count")
    sector = tuple(
        reader.integer(f"actual-sector-column-{index:03d}")
        for index in range(sector_count)
    )
    full_count = reader.integer("full-source-column-count")
    based_selector = reader.text("based-on-candidate-selector-sha")
    _sha(based_selector, "based-on candidate selector")
    if full_count != source_columns:
        raise ValueError("full-source column count does not match selector")
    if (
        source_columns <= 0
        or readout_rows <= 0
        or len(set(sector)) != len(sector)
        or any(not 0 <= column < source_columns for column in sector)
    ):
        raise ValueError("candidate selector dimensions/sector are not frozen")
    if max(
        np.linalg.norm(source.conj().T @ source - np.eye(source_columns), ord=2),
        np.linalg.norm(readout @ readout.conj().T - np.eye(readout_rows), ord=2),
    ) > 1.0e-12:
        raise ValueError("candidate selector is not isometric/coisometric")
    return source, readout, sector


def _quarter_turn_signatures(
    mode: int,
    sign: int,
    prefix: str,
    *,
    target_conditioned: bool,
) -> tuple[CandidateShearStepSignature, ...]:
    if mode not in (0, 1) or sign not in (-1, 1):
        raise ValueError("quarter-turn grammar is not frozen")
    q_channel = f"q{mode}"
    p_channel = f"p{mode}"
    return (
        _signature(
            f"{prefix}.lower.0",
            q_channel,
            p_channel,
            float(sign),
            target_conditioned=target_conditioned,
        ),
        _signature(
            f"{prefix}.upper",
            p_channel,
            q_channel,
            float(-sign),
            target_conditioned=target_conditioned,
        ),
        _signature(
            f"{prefix}.lower.1",
            q_channel,
            p_channel,
            float(sign),
            target_conditioned=target_conditioned,
        ),
    )


def _rotation_signatures(
    mode: int,
    angle: float,
    prefix: str,
    *,
    target_conditioned: bool,
) -> tuple[CandidateShearStepSignature, ...]:
    tangent = math.tan(angle / 2.0)
    sine = math.sin(angle)
    q_channel = f"q{mode}"
    p_channel = f"p{mode}"
    return (
        _signature(
            f"{prefix}.lower.0",
            q_channel,
            p_channel,
            tangent,
            target_conditioned=target_conditioned,
        ),
        _signature(
            f"{prefix}.upper",
            p_channel,
            q_channel,
            -sine,
            target_conditioned=target_conditioned,
        ),
        _signature(
            f"{prefix}.lower.1",
            q_channel,
            p_channel,
            tangent,
            target_conditioned=target_conditioned,
        ),
    )


def _mode_swap_signatures(
    prefix: str,
    *,
    inverse: bool,
) -> tuple[CandidateShearStepSignature, ...]:
    forward = (
        ("q0", "q1", 1.0),
        ("p0", "p1", 1.0),
        ("q1", "q0", -1.0),
        ("p1", "p0", -1.0),
        ("q0", "q1", 1.0),
        ("p0", "p1", 1.0),
    )
    operations = (
        tuple(
            (source, destination, -coefficient)
            for source, destination, coefficient in reversed(forward)
        )
        if inverse
        else forward
    )
    return tuple(
        _signature(
            f"{prefix}.{index:02d}",
            source,
            destination,
            coefficient,
            target_conditioned=True,
        )
        for index, (source, destination, coefficient) in enumerate(operations)
    )


def _parallel_mode_signatures(
    prefix: str,
    *,
    source_mode: int,
    destination_mode: int,
    offset: int,
    coefficient: float,
    target_conditioned: bool,
) -> tuple[CandidateShearStepSignature, ...]:
    return (
        _signature(
            f"{prefix}.q",
            f"q{source_mode}",
            f"q{destination_mode}",
            coefficient,
            offset=offset,
            target_conditioned=target_conditioned,
        ),
        _signature(
            f"{prefix}.p",
            f"p{source_mode}",
            f"p{destination_mode}",
            coefficient,
            offset=offset,
            target_conditioned=target_conditioned,
        ),
    )


def _two_mode_rotation_signatures(
    angle: float,
    prefix: str,
    *,
    target_conditioned: bool,
) -> tuple[CandidateShearStepSignature, ...]:
    tangent = float(math.tan(angle / 2.0))
    sine = float(math.sin(angle))
    return (
        *_parallel_mode_signatures(
            f"{prefix}.lower.0",
            source_mode=0,
            destination_mode=1,
            offset=0,
            coefficient=tangent,
            target_conditioned=target_conditioned,
        ),
        *_parallel_mode_signatures(
            f"{prefix}.upper",
            source_mode=1,
            destination_mode=0,
            offset=0,
            coefficient=-sine,
            target_conditioned=target_conditioned,
        ),
        *_parallel_mode_signatures(
            f"{prefix}.lower.1",
            source_mode=0,
            destination_mode=1,
            offset=0,
            coefficient=tangent,
            target_conditioned=target_conditioned,
        ),
    )


def _canonical_pair_rotation_signatures(
    mode: int,
    angle: float,
    prefix: str,
    *,
    target_conditioned: bool,
) -> tuple[CandidateShearStepSignature, ...]:
    tangent = float(math.tan(angle / 2.0))
    sine = float(math.sin(angle))
    q_channel = f"q{mode}"
    p_channel = f"p{mode}"
    return (
        _signature(
            f"{prefix}.lower.0",
            q_channel,
            p_channel,
            tangent,
            target_conditioned=target_conditioned,
        ),
        _signature(
            f"{prefix}.upper",
            p_channel,
            q_channel,
            -sine,
            target_conditioned=target_conditioned,
        ),
        _signature(
            f"{prefix}.lower.1",
            q_channel,
            p_channel,
            tangent,
            target_conditioned=target_conditioned,
        ),
    )


def _reciprocal_swap_signatures(
    prefix: str,
) -> tuple[CandidateShearStepSignature, ...]:
    return (
        *_parallel_mode_signatures(
            f"{prefix}.lower.0",
            source_mode=0,
            destination_mode=1,
            offset=1,
            coefficient=1.0,
            target_conditioned=False,
        ),
        *_parallel_mode_signatures(
            f"{prefix}.upper",
            source_mode=1,
            destination_mode=0,
            offset=-1,
            coefficient=-1.0,
            target_conditioned=False,
        ),
        *_parallel_mode_signatures(
            f"{prefix}.lower.1",
            source_mode=0,
            destination_mode=1,
            offset=1,
            coefficient=1.0,
            target_conditioned=False,
        ),
    )


def _inverse_signatures(
    signatures: tuple[CandidateShearStepSignature, ...],
    prefix: str,
    *,
    target_conditioned: Optional[bool] = None,
) -> tuple[CandidateShearStepSignature, ...]:
    return tuple(
        _signature(
            f"{prefix}.{index:02d}",
            item.source_channel,
            item.destination_channel,
            -item.coefficient,
            offset=item.offset[0],
            target_conditioned=(
                item.target_conditioned
                if target_conditioned is None
                else target_conditioned
            ),
        )
        for index, item in enumerate(reversed(signatures))
    )


def _program_sha(
    branch: str,
    signatures: tuple[CandidateShearStepSignature, ...],
) -> str:
    return canonical_sha(
        {
            "program_schema_version": "v3m0.candidate-local-shear-program.v1",
            "branch": branch,
            "steps": [
                {
                    **candidate_shear_step_signature_payload(item),
                    "signature_sha": item.signature_sha,
                }
                for item in signatures
            ],
        }
    )


def _compile_transition(
    reader: _Reader,
) -> tuple[
    int,
    bool,
    bool,
    tuple[CandidateShearStepSignature, ...],
    tuple[CandidateShearStepSignature, ...],
]:
    family = reader.text("transition-family")
    if reader.text("ablation-policy") != "delete-target-conditioned-slots-v1":
        raise ValueError("candidate ablation policy is not frozen")
    if reader.text("channel-order") != "q0,p0,q1,p1":
        raise ValueError("candidate channel order is not frozen")
    support = reader.integer("primitive-support-radius")
    global_fft_wire = reader.integer("uses-global-fft-projection")
    per_k_wire = reader.integer("uses-per-k-timestep-projector")
    if global_fft_wire not in (0, 1) or per_k_wire not in (0, 1):
        raise ValueError("candidate projection flags must be Boolean wires")
    global_fft = bool(global_fft_wire)
    per_k = bool(per_k_wire)
    if family == "c07-constructive-complementary-rotation-v1":
        carrier_mode = reader.integer("carrier-mode")
        conditioned_mode = reader.integer("conditioned-mode")
        spectator_mode = reader.integer("spectator-mode")
        spectator_count = reader.integer("spectator-quarter-turn-count")
        spectator_sign = reader.integer("spectator-quarter-turn-sign")
        delta = reader.fp64("delta-radians")
        if (
            carrier_mode != 0
            or conditioned_mode != 0
            or spectator_mode != 1
            or spectator_count != 2
            or spectator_sign != 1
            or reader.text("matched-angle-formula")
            != "pi-over-two-minus-delta-v1"
            or delta != math.pi / 8192.0
            or support != 0
        ):
            raise ValueError("constructive transition is not frozen")
        blind = (
            *_rotation_signatures(
                carrier_mode,
                float(math.pi / 2.0 - delta),
                "constructive.rotation.blind.mode0",
                target_conditioned=False,
            ),
            *(
                step
                for count in range(spectator_count)
                for step in _quarter_turn_signatures(
                    spectator_mode,
                    spectator_sign,
                    f"blind.mode1.quarter.{count}",
                    target_conditioned=False,
                )
            ),
        )
        conditioned = _rotation_signatures(
            conditioned_mode,
            delta,
            "constructive.rotation.conditioned.mode0",
            target_conditioned=True,
        )
        actual = (*blind, *conditioned)
    elif family in (
        "c07-destructive-swap-conjugation-v1",
        "c10-extra-mode-swap-conjugation-v1",
    ):
        mode0_sign = reader.integer("blind-mode0-quarter-turn-sign")
        mode1_count = reader.integer("blind-mode1-quarter-turn-count")
        mode1_sign = reader.integer("blind-mode1-quarter-turn-sign")
        if (
            mode0_sign != 1
            or mode1_count != 2
            or mode1_sign != 1
            or reader.text("conditioned-conjugation")
            != "inverse-swap-before-forward-swap-after-v1"
            or reader.text("mode-swap-shear-grammar")
            != "six-shear-two-canonical-pairs-v1"
            or support != 0
        ):
            raise ValueError("swap-conjugated transition is not frozen")
        if family == "c10-extra-mode-swap-conjugation-v1":
            if (
                reader.integer("actual-source-axis") != 0
                or reader.integer("independent-new-source-axis") != 1
                or reader.fp64("new-source-axis-amplitude") != 1.0
            ):
                raise ValueError("C10 source-domain transition is not frozen")
        blind = (
            *_quarter_turn_signatures(
                0,
                mode0_sign,
                "blind.mode0.quarter",
                target_conditioned=False,
            ),
            *(
                step
                for count in range(mode1_count)
                for step in _quarter_turn_signatures(
                    1,
                    mode1_sign,
                    f"blind.mode1.quarter.{count}",
                    target_conditioned=False,
                )
            ),
        )
        actual = (
            *_mode_swap_signatures(
                "conditioned.mode-swap.inverse",
                inverse=True,
            ),
            *blind,
            *_mode_swap_signatures(
                "conditioned.mode-swap.forward",
                inverse=False,
            ),
        )
    elif family == "c08-conditioned-mode1-deletion-v1":
        mode0_sign = reader.integer("blind-mode0-quarter-turn-sign")
        mode1_count = reader.integer("blind-mode1-quarter-turn-count")
        mode1_sign = reader.integer("blind-mode1-quarter-turn-sign")
        conditioned_mode = reader.integer("conditioned-delete-mode")
        conditioned_sign = reader.integer("conditioned-quarter-turn-sign")
        if (
            mode0_sign != 1
            or mode1_count != 2
            or mode1_sign != 1
            or conditioned_mode != 1
            or conditioned_sign != -1
            or support != 0
        ):
            raise ValueError("C08 deletion transition is not frozen")
        blind = (
            *_quarter_turn_signatures(
                0,
                mode0_sign,
                "blind.mode0.quarter",
                target_conditioned=False,
            ),
            *(
                step
                for count in range(mode1_count)
                for step in _quarter_turn_signatures(
                    1,
                    mode1_sign,
                    f"blind.mode1.quarter.{count}",
                    target_conditioned=False,
                )
            ),
        )
        actual = (
            *blind,
            *_quarter_turn_signatures(
                conditioned_mode,
                conditioned_sign,
                "conditioned.mode1.inverse-quarter",
                target_conditioned=True,
            ),
        )
    elif family == "c12-common-geometry-incidence-carrier-v1":
        if (
            reader.text("construction-rule-id")
            != "c12-rank-two-local-incidence-carrier-v1"
            or reader.integer("state-count") != 4
            or reader.integer("reciprocal-shear-radius") != 1
            or reader.text("ordered-composite")
            != "mix-inverse-common-blind-mix-forward-v1"
        ):
            raise ValueError("C12 carrier grammar is not frozen")
        alpha = reader.fp64("common-alpha-radians")
        beta = reader.fp64("common-beta-radians")
        conditioning_angle = reader.fp64("conditioning-angle-radians")
        carrier0 = reader.fp64("carrier-mode0-angle-radians")
        carrier1 = reader.fp64("carrier-mode1-angle-radians")
        if (
            alpha != math.pi / 8.0
            or beta != -math.pi / 4.0
            or conditioning_angle != 1.0 / 8.0
            or carrier0 != math.pi / 2.0
            or carrier1 != -math.pi / 2.0
            or support != 1
        ):
            raise ValueError("C12 carrier constants are not frozen")
        reciprocal = _reciprocal_swap_signatures(
            "blind.geometry.reciprocal"
        )
        blind = (
            *_two_mode_rotation_signatures(
                -alpha,
                "blind.geometry.left.r-minus-alpha",
                target_conditioned=False,
            ),
            *_inverse_signatures(
                reciprocal,
                "blind.geometry.left.reciprocal-inverse",
            ),
            *_two_mode_rotation_signatures(
                -beta,
                "blind.geometry.left.r-minus-beta",
                target_conditioned=False,
            ),
            *_canonical_pair_rotation_signatures(
                0,
                carrier0,
                "blind.geometry.carrier.mode0-positive",
                target_conditioned=False,
            ),
            *_canonical_pair_rotation_signatures(
                1,
                carrier1,
                "blind.geometry.carrier.mode1-negative",
                target_conditioned=False,
            ),
            *_two_mode_rotation_signatures(
                beta,
                "blind.geometry.right.r-beta",
                target_conditioned=False,
            ),
            *reciprocal,
            *_two_mode_rotation_signatures(
                alpha,
                "blind.geometry.right.r-alpha",
                target_conditioned=False,
            ),
        )
        conditioned = _two_mode_rotation_signatures(
            conditioning_angle,
            "conditioned.geometry.mix.forward",
            target_conditioned=True,
        )
        actual = (
            *_inverse_signatures(
                conditioned,
                "conditioned.geometry.mix.inverse",
                target_conditioned=True,
            ),
            *blind,
            *conditioned,
        )
    elif family == "closed-live-recipe-shear-program-v1":
        count = reader.integer("live-step-count")
        if count <= 0:
            raise ValueError("live recipe transition has no shear steps")
        signatures: list[CandidateShearStepSignature] = []
        for index in range(count):
            prefix = f"live-step-{index:03d}"
            conditioned = reader.integer(f"{prefix}-target-conditioned")
            if conditioned not in (0, 1):
                raise ValueError("live recipe conditioned flag is not Boolean")
            signatures.append(
                _signature(
                    reader.text(f"{prefix}-id"),
                    reader.text(f"{prefix}-source-channel"),
                    reader.text(f"{prefix}-destination-channel"),
                    reader.fp64(f"{prefix}-coefficient"),
                    offset=reader.integer(f"{prefix}-offset"),
                    target_conditioned=bool(conditioned),
                )
            )
        actual = tuple(signatures)
        if max(abs(step.offset[0]) for step in actual) > support:
            raise ValueError("live recipe transition exceeds declared support")
    else:
        raise ValueError("candidate transition family is not registered")
    if global_fft or per_k:
        raise ValueError("candidate transition contains a forbidden projection")
    matched = tuple(item for item in actual if not item.target_conditioned)
    return support, global_fft, per_k, tuple(actual), matched


def _compile_analytic_core(
    reader: _Reader,
) -> tuple[
    int,
    int,
    int,
    int,
    tuple[float, ...],
    Optional[float],
    Literal["defined-v1", "undefined-v1"],
    Optional[float],
]:
    _text(reader.text("contract-family"), "contract family")
    if reader.text("prediction-semantics") != "analytic-preresponse-v1":
        raise ValueError("candidate prediction semantics are not analytic-only")
    _text(reader.text("rank-disposition"), "rank disposition")
    candidate_rank = reader.integer("candidate-expected-actual-shell-rank")
    expected_actual_rank = reader.integer("expected-actual-shell-rank")
    expected_matched_rank = reader.integer("expected-matched-shell-rank")
    expected_matched_actual_sector_rank = reader.integer(
        "expected-matched-actual-sector-rank"
    )
    expected_matched_full_source_rank = reader.integer(
        "expected-matched-full-source-rank"
    )
    survival_count = reader.integer("expected-survival-count")
    survival = tuple(
        reader.fp64(f"expected-survival-{index:03d}")
        for index in range(survival_count)
    )
    chi_state = reader.text("expected-chi-extra-state")
    if chi_state == "defined-v1":
        chi_extra: Optional[float] = reader.fp64("expected-chi-extra")
    elif chi_state == "not-frozen-v1":
        chi_extra = None
    else:
        raise ValueError("candidate chi-extra state is not frozen")
    state = reader.text("expected-d-proc-state")
    if state == "defined-v1":
        d_proc: Optional[float] = reader.fp64("expected-d-proc-sq")
    elif state == "undefined-v1":
        d_proc = None
    else:
        raise ValueError("candidate d_proc state is not frozen")
    ranks = (
        candidate_rank,
        expected_actual_rank,
        expected_matched_rank,
        expected_matched_actual_sector_rank,
        expected_matched_full_source_rank,
    )
    if any(type(rank) is not int or rank < 0 for rank in ranks):
        raise ValueError("candidate analytic ranks must be nonnegative integers")
    if any(not math.isfinite(value) or value < 0.0 for value in survival):
        raise ValueError("candidate survival spectrum is not nonnegative")
    if chi_extra is not None and (
        not math.isfinite(chi_extra) or chi_extra < 0.0
    ):
        raise ValueError("candidate chi-extra is not nonnegative")
    return (
        expected_actual_rank,
        expected_matched_rank,
        expected_matched_actual_sector_rank,
        expected_matched_full_source_rank,
        survival,
        chi_extra,
        state,
        d_proc,
    )


def _incidence_point(
    reader: _Reader,
    index: int,
    denominator: int,
) -> CandidateIncidencePointContract:
    prefix = f"mode-{index}"
    reciprocal_index = reader.integer(f"{prefix}-reciprocal-index")
    momentum = reader.fp64(f"{prefix}-momentum")
    root_order = reader.integer(f"{prefix}-root-of-unity-order")
    root_power = reader.integer(f"{prefix}-root-of-unity-power")
    exact_expression = reader.text(f"{prefix}-exact-nu-expression")
    count = reader.integer(f"{prefix}-minpoly-count")
    coefficients = tuple(
        reader.integer(f"{prefix}-minpoly-{coefficient_index:03d}")
        for coefficient_index in range(count)
    )
    nu_value = reader.fp64(f"{prefix}-nu")
    if (
        root_order != denominator
        or root_power != reciprocal_index
        or momentum != 2.0 * math.pi * reciprocal_index / denominator
    ):
        raise ValueError("candidate incidence root-of-unity wire is inconsistent")
    expected = {
        1: ("2 - sqrt(2)", (1, -4, 2), 2.0 - math.sqrt(2.0)),
        2: ("2", (1, -2), 2.0),
    }
    if reciprocal_index not in expected:
        raise ValueError("candidate incidence reciprocal index is not frozen")
    expression, polynomial, expected_nu = expected[reciprocal_index]
    if (
        exact_expression != expression
        or coefficients != polynomial
        or nu_value != expected_nu
    ):
        raise ValueError("candidate cyclotomic incidence wire is not exact")
    provisional = CandidateIncidencePointContract(
        point_schema_version=CANDIDATE_INCIDENCE_POINT_SCHEMA_VERSION,
        reciprocal_index=(reciprocal_index,),
        momentum=momentum,
        exact_nu_expression=exact_expression,
        nu_minimal_polynomial_coefficients=coefficients,
        nu_value=nu_value,
        point_sha="0" * 64,
    )
    return replace(
        provisional,
        point_sha=canonical_sha(
            candidate_incidence_point_contract_payload(provisional)
        ),
    )


def _read_indexed_tuples(
    reader: _Reader,
    prefix: str,
) -> tuple[tuple[int, ...], ...]:
    count = reader.integer(f"{prefix}-count")
    if count < 0:
        raise ValueError(f"{prefix} count is negative")
    result: list[tuple[int, ...]] = []
    for index in range(count):
        dimension = reader.integer(f"{prefix}-{index:03d}-dimension")
        if dimension <= 0:
            raise ValueError(f"{prefix} dimension is not positive")
        result.append(
            tuple(
                reader.integer(f"{prefix}-{index:03d}-{axis:03d}")
                for axis in range(dimension)
            )
        )
    return tuple(result)


@dataclass(frozen=True)
class _CompiledConstructionContext:
    construction_evidence_kind: str
    construction_rule_id: str
    construction_family_id: str
    construction_recipe_sha: str
    construction_operation_dag_sha: str
    recipe_source_injection_sha: str
    recipe_readout_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    response_torus_denominators: tuple[int, ...]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    source_trial_count: int
    geometry_bundle_derivation_id: Optional[str]
    geometry_operation_dag_sha: Optional[str]
    geometry_semantic_sector_names: tuple[str, ...]
    geometry_coverage_control: Optional[float]
    geometry_gauge_amplitude: Optional[float]
    geometry_observer_collapse_expected: Optional[bool]


def _compile_construction_context(
    reader: _Reader,
) -> _CompiledConstructionContext:
    evidence_kind = reader.text("context-construction-evidence-kind")
    rule_id = reader.text("context-construction-rule-id")
    family_id = reader.text("context-construction-family-id")
    recipe_sha = reader.text("context-construction-recipe-sha")
    operation_dag_sha = reader.text("context-construction-operation-dag-sha")
    recipe_source_sha = reader.text("context-recipe-source-injection-sha")
    recipe_readout_sha = reader.text("context-recipe-readout-sha")
    actual_effect = reader.text("context-actual-effect-digest")
    matched_effect = reader.text("context-matched-ablated-effect-digest")
    for value, field in (
        (recipe_sha, "construction recipe"),
        (operation_dag_sha, "construction operation DAG"),
        (recipe_source_sha, "recipe source injection"),
        (recipe_readout_sha, "recipe readout"),
        (actual_effect, "actual effect"),
        (matched_effect, "matched effect"),
    ):
        _sha(value, field)
    denominator_count = reader.integer("context-response-torus-denominator-count")
    denominators = tuple(
        reader.integer(f"context-response-torus-denominator-{index:03d}")
        for index in range(denominator_count)
    )
    response_indices = _read_indexed_tuples(
        reader,
        "context-response-reciprocal-index",
    )
    bridge_indices = _read_indexed_tuples(
        reader,
        "context-source-readout-bridge-reciprocal-index",
    )
    bridge_step_count = reader.integer("context-source-readout-bridge-step-count")
    bridge_steps = tuple(
        reader.integer(f"context-source-readout-bridge-step-{index:03d}")
        for index in range(bridge_step_count)
    )
    reference_dimension = reader.integer(
        "context-reference-reciprocal-index-dimension"
    )
    reference_index = tuple(
        reader.integer(f"context-reference-reciprocal-index-{index:03d}")
        for index in range(reference_dimension)
    )
    band_count = reader.integer("context-preregistered-phase-band-count")
    bands = tuple(
        (
            reader.fp64(f"context-preregistered-phase-band-{index:03d}-lower"),
            reader.fp64(f"context-preregistered-phase-band-{index:03d}-upper"),
        )
        for index in range(band_count)
    )
    if (
        reader.text("context-source-trial-vector-rule")
        != "identity-in-proposed-source-column-space-v1"
    ):
        raise ValueError("candidate source trial rule is not frozen")
    source_trial_count = reader.integer("context-source-trial-vector-count")
    if (
        not denominators
        or any(value <= 0 for value in denominators)
        or not response_indices
        or not bridge_indices
        or any(value <= 0 for value in bridge_steps)
        or not reference_index
        or not bands
        or any(lower >= upper for lower, upper in bands)
        or source_trial_count <= 0
    ):
        raise ValueError("candidate response context is incomplete")

    geometry_present = reader.integer("context-geometry-present")
    if geometry_present not in (0, 1):
        raise ValueError("geometry presence wire is not Boolean")
    geometry_bundle: Optional[str] = None
    geometry_dag: Optional[str] = None
    geometry_sectors: tuple[str, ...] = ()
    coverage: Optional[float] = None
    gauge: Optional[float] = None
    observer: Optional[bool] = None
    if geometry_present:
        geometry_bundle = reader.text("context-geometry-bundle-derivation-id")
        geometry_dag = reader.text("context-geometry-operation-dag-sha")
        _sha(geometry_dag, "geometry operation DAG")
        sector_count = reader.integer("context-geometry-semantic-sector-count")
        geometry_sectors = tuple(
            reader.text(f"context-geometry-semantic-sector-{index:03d}")
            for index in range(sector_count)
        )
        observer_wire = reader.integer(
            "context-geometry-observer-collapse-expected"
        )
        coverage_present = reader.integer(
            "context-geometry-coverage-control-present"
        )
        gauge_present = reader.integer("context-geometry-gauge-amplitude-present")
        if (
            not geometry_sectors
            or observer_wire not in (0, 1)
            or coverage_present not in (0, 1)
            or gauge_present not in (0, 1)
        ):
            raise ValueError("geometry construction context is incomplete")
        observer = bool(observer_wire)
        if coverage_present:
            coverage = reader.fp64("context-geometry-coverage-control")
        if gauge_present:
            gauge = reader.fp64("context-geometry-gauge-amplitude")
    return _CompiledConstructionContext(
        construction_evidence_kind=evidence_kind,
        construction_rule_id=rule_id,
        construction_family_id=family_id,
        construction_recipe_sha=recipe_sha,
        construction_operation_dag_sha=operation_dag_sha,
        recipe_source_injection_sha=recipe_source_sha,
        recipe_readout_sha=recipe_readout_sha,
        actual_effect_digest=actual_effect,
        matched_ablated_effect_digest=matched_effect,
        response_torus_denominators=denominators,
        response_reciprocal_indices=response_indices,
        source_readout_bridge_reciprocal_indices=bridge_indices,
        source_readout_bridge_steps=bridge_steps,
        reference_reciprocal_index=reference_index,
        preregistered_phase_bands=bands,
        source_trial_count=source_trial_count,
        geometry_bundle_derivation_id=geometry_bundle,
        geometry_operation_dag_sha=geometry_dag,
        geometry_semantic_sector_names=geometry_sectors,
        geometry_coverage_control=coverage,
        geometry_gauge_amplitude=gauge,
        geometry_observer_collapse_expected=observer,
    )


def _compile_contract(
    dag: CandidateScenarioDAG,
) -> CompiledCandidateScenarioContract:
    transition, selector, contract = dag.operations
    transition_reader = _Reader(transition)
    support, global_fft, per_k, actual_steps, matched_steps = (
        _compile_transition(transition_reader)
    )
    transition_names = transition_reader.finish()

    selector_reader = _Reader(selector)
    source, readout, sector = _sparse_selector(selector_reader)
    if selector_reader.text("based-on-candidate-selector-sha") != (
        dag.based_on_candidate_selector_sha
    ):
        raise ValueError("selector is spliced to another candidate")
    selector_names = selector_reader.finish()

    contract_reader = _Reader(contract)
    (
        expected_actual_rank,
        expected_matched_rank,
        expected_matched_actual_sector_rank,
        expected_matched_full_source_rank,
        survival,
        chi_extra,
        d_proc_state,
        d_proc,
    ) = _compile_analytic_core(contract_reader)
    context = _compile_construction_context(contract_reader)
    if context.source_trial_count != source.shape[1]:
        raise ValueError("source trial dimension differs from proposed selector")

    incidence_family: Optional[str] = None
    incidence_normalizer: Optional[str] = None
    incidence_stage: Optional[Literal["POST_RESPONSE_READOUT_ONLY"]] = None
    stencil_offsets: tuple[tuple[int, ...], ...] = ()
    stencil_coefficients: tuple[int, ...] = ()
    ir_limit_order: Optional[int] = None
    ir_limit_formula: Optional[str] = None
    response_denominator: Optional[int] = None
    incidence_response_indices: tuple[tuple[int, ...], ...] = ()
    absolute_signal_ref: Optional[str] = None
    raw_bridge_ref: Optional[str] = None
    raw_noise_ref: Optional[str] = None
    relative_gap_ref: Optional[str] = None
    incidence_points: tuple[CandidateIncidencePointContract, ...] = ()
    if contract.operation_kind == "incidence-analytic-contract-v1":
        incidence_family = contract_reader.text("incidence-family-id")
        incidence_normalizer = contract_reader.text(
            "incidence-normalizer-formula-id"
        )
        stage = contract_reader.text("incidence-application-stage")
        if (
            incidence_family != "synthetic-lattice-laplacian-incidence-v1"
            or incidence_normalizer != "nu-inc-4-sum-sin2-half-v1"
            or stage != "POST_RESPONSE_READOUT_ONLY"
        ):
            raise ValueError("candidate incidence family/stage is not frozen")
        incidence_stage = "POST_RESPONSE_READOUT_ONLY"
        response_denominator = contract_reader.integer(
            "response-torus-denominator"
        )
        response_count = contract_reader.integer(
            "response-reciprocal-index-count"
        )
        stencil_count = contract_reader.integer("stencil-point-count")
        stencil_offsets = tuple(
            (contract_reader.integer(f"stencil-offset-{index:03d}"),)
            for index in range(stencil_count)
        )
        stencil_coefficients = tuple(
            contract_reader.integer(f"stencil-coefficient-{index:03d}")
            for index in range(stencil_count)
        )
        ir_limit_order = contract_reader.integer("ir-limit-order")
        ir_limit_value = contract_reader.fp64("ir-limit-value")
        ir_limit_formula = contract_reader.text("ir-limit-formula-id")
        first_brillouin = contract_reader.text("first-brillouin-domain-id")
        absolute_signal_ref = contract_reader.text(
            "absolute-signal-threshold-authority-ref"
        )
        raw_bridge_ref = contract_reader.text(
            "raw-bridge-noise-evidence-ref"
        )
        raw_noise_ref = contract_reader.text(
            "raw-noise-absolute-threshold-authority-ref"
        )
        relative_gap_ref = contract_reader.text(
            "relative-gap-threshold-authority-ref"
        )
        if (
            response_denominator != 8
            or response_count != 2
            or stencil_offsets != ((-1,), (0,), (1,))
            or stencil_coefficients != (-1, 2, -1)
            or ir_limit_order != 2
            or ir_limit_value != 1.0
            or ir_limit_formula
            != "lim-k-to-zero-nu-inc-over-k-squared-equals-one-v1"
            or first_brillouin
            != "one-dimensional-minus-pi-open-pi-closed-v1"
            or absolute_signal_ref != "WindowThresholdSelection.curv_tau_sig"
            or raw_bridge_ref
            != "SourceReadoutBridgeAudit.curv_operator_error_max"
            or raw_noise_ref != "rulespace_v3.thresholds.BRIDGE_TOLERANCE"
            or relative_gap_ref != "rulespace_v3.thresholds.RAW_GAP_MIN"
        ):
            raise ValueError("candidate incidence analytic contract drifted")
        incidence_points = tuple(
            _incidence_point(contract_reader, index, response_denominator)
            for index in range(response_count)
        )
        incidence_response_indices = tuple(
            point.reciprocal_index for point in incidence_points
        )
        if (
            context.response_torus_denominators != (response_denominator,)
            or context.response_reciprocal_indices != incidence_response_indices
        ):
            raise ValueError("incidence response grid differs from scenario context")
    contract_names = contract_reader.finish()

    provisional = CompiledCandidateScenarioContract(
        contract_schema_version=COMPILED_CANDIDATE_CONTRACT_SCHEMA_VERSION,
        construction_state=CANDIDATE_DAG_CONSTRUCTION_STATE,
        scenario_id=dag.scenario_id,
        dag_sha=dag.dag_sha,
        based_on_candidate_selector_sha=dag.based_on_candidate_selector_sha,
        primitive_support_radius=support,
        uses_global_fft_projection=global_fft,
        uses_per_k_time_step_projector=per_k,
        actual_sector_source_columns=sector,
        expected_actual_shell_rank=expected_actual_rank,
        expected_matched_shell_rank=expected_matched_rank,
        expected_matched_actual_sector_rank=(
            expected_matched_actual_sector_rank
        ),
        expected_matched_full_source_rank=expected_matched_full_source_rank,
        expected_survival_spectrum=survival,
        expected_chi_extra=chi_extra,
        expected_d_proc_state=d_proc_state,
        expected_d_proc_sq=d_proc,
        proposed_source_selection=freeze_complex_tensor(source),
        proposed_readout_selection=freeze_complex_tensor(readout),
        actual_step_signatures=actual_steps,
        matched_ablated_step_signatures=matched_steps,
        actual_program_sha=_program_sha("actual", actual_steps),
        matched_ablated_program_sha=_program_sha(
            "matched_ablated",
            matched_steps,
        ),
        construction_evidence_kind=context.construction_evidence_kind,
        construction_rule_id=context.construction_rule_id,
        construction_family_id=context.construction_family_id,
        construction_recipe_sha=context.construction_recipe_sha,
        construction_operation_dag_sha=(
            context.construction_operation_dag_sha
        ),
        recipe_source_injection_sha=context.recipe_source_injection_sha,
        recipe_readout_sha=context.recipe_readout_sha,
        actual_effect_digest=context.actual_effect_digest,
        matched_ablated_effect_digest=(
            context.matched_ablated_effect_digest
        ),
        response_torus_denominators=context.response_torus_denominators,
        source_readout_bridge_reciprocal_indices=(
            context.source_readout_bridge_reciprocal_indices
        ),
        source_readout_bridge_steps=context.source_readout_bridge_steps,
        reference_reciprocal_index=context.reference_reciprocal_index,
        preregistered_phase_bands=context.preregistered_phase_bands,
        source_trial_vectors=freeze_complex_tensor(
            np.eye(context.source_trial_count, dtype=np.complex128)
        ),
        geometry_bundle_derivation_id=(
            context.geometry_bundle_derivation_id
        ),
        geometry_operation_dag_sha=context.geometry_operation_dag_sha,
        geometry_semantic_sector_names=(
            context.geometry_semantic_sector_names
        ),
        geometry_coverage_control=context.geometry_coverage_control,
        geometry_gauge_amplitude=context.geometry_gauge_amplitude,
        geometry_observer_collapse_expected=(
            context.geometry_observer_collapse_expected
        ),
        incidence_family_id=incidence_family,
        incidence_normalizer_formula_id=incidence_normalizer,
        incidence_application_stage=incidence_stage,
        incidence_stencil_offsets=stencil_offsets,
        incidence_stencil_coefficients=stencil_coefficients,
        ir_limit_order=ir_limit_order,
        ir_limit_formula_id=ir_limit_formula,
        response_torus_denominator=response_denominator,
        response_reciprocal_indices=context.response_reciprocal_indices,
        absolute_signal_threshold_authority_ref=absolute_signal_ref,
        raw_bridge_noise_evidence_ref=raw_bridge_ref,
        raw_noise_absolute_threshold_authority_ref=raw_noise_ref,
        relative_gap_threshold_authority_ref=relative_gap_ref,
        incidence_points=incidence_points,
        consumed_parameter_names=(
            (transition.operation_id, transition_names),
            (selector.operation_id, selector_names),
            (contract.operation_id, contract_names),
        ),
        contract_sha="0" * 64,
    )
    return replace(
        provisional,
        contract_sha=canonical_sha(
            compiled_candidate_scenario_contract_payload(provisional)
        ),
    )


def extract_candidate_scenario_contract(
    dag: CandidateScenarioDAG,
) -> CompiledCandidateScenarioContract:
    """Compile only typed DAG parameters; the scenario ID selects no constants."""

    verified = verify_candidate_scenario_dag(dag)
    transition, selector, contract = verified.operations
    if (
        transition.operation_kind != "local-transition-recipe-v1"
        or selector.operation_kind != "closed-form-selector-v1"
        or contract.operation_kind
        not in (
            "analytic-causal-contract-v1",
            "incidence-analytic-contract-v1",
        )
        or transition.input_operation_ids != ()
        or selector.input_operation_ids != ()
        or contract.input_operation_ids
        != (transition.operation_id, selector.operation_id)
    ):
        raise ValueError("candidate scenario DAG does not have the frozen closure")
    return _compile_contract(verified)


def verify_compiled_candidate_scenario_contract(
    dag: CandidateScenarioDAG,
    contract: CompiledCandidateScenarioContract,
) -> CompiledCandidateScenarioContract:
    _exact_record(
        contract,
        CompiledCandidateScenarioContract,
        "compiled candidate scenario contract",
    )
    contract.__post_init__()
    for tensor in (
        contract.proposed_source_selection,
        contract.proposed_readout_selection,
        contract.source_trial_vectors,
    ):
        _exact_record(tensor, FrozenComplexTensor, "compiled candidate tensor")
        verify_frozen_tensor(tensor)
    for field in (
        "actual_step_signatures",
        "matched_ablated_step_signatures",
    ):
        for index, signature in enumerate(getattr(contract, field)):
            _exact_record(
                signature,
                CandidateShearStepSignature,
                f"{field}[{index}]",
            )
            signature.__post_init__()
            if signature.signature_sha != canonical_sha(
                candidate_shear_step_signature_payload(signature)
            ):
                raise ValueError("candidate shear signature SHA does not replay")
    if contract.actual_program_sha != _program_sha(
        "actual",
        contract.actual_step_signatures,
    ):
        raise ValueError("candidate actual program SHA does not replay")
    if contract.matched_ablated_program_sha != _program_sha(
        "matched_ablated",
        contract.matched_ablated_step_signatures,
    ):
        raise ValueError("candidate matched program SHA does not replay")
    for index, point in enumerate(contract.incidence_points):
        _exact_record(
            point,
            CandidateIncidencePointContract,
            f"incidence_points[{index}]",
        )
        point.__post_init__()
        if point.point_sha != canonical_sha(
            candidate_incidence_point_contract_payload(point)
        ):
            raise ValueError("candidate incidence point SHA does not replay")
    if contract.contract_sha != canonical_sha(
        compiled_candidate_scenario_contract_payload(contract)
    ):
        raise ValueError("compiled candidate contract SHA does not replay")
    expected = extract_candidate_scenario_contract(dag)
    if contract != expected:
        raise ValueError("compiled candidate contract differs from live extraction")
    return contract


__all__ = [
    "CANDIDATE_DAG_CONSTRUCTION_STATE",
    "CANDIDATE_DAG_OPERATION_SCHEMA_VERSION",
    "CANDIDATE_DAG_SCENARIO_IDS",
    "CANDIDATE_INCIDENCE_POINT_SCHEMA_VERSION",
    "CANDIDATE_SCENARIO_DAG_SCHEMA_VERSION",
    "CANDIDATE_SHEAR_STEP_SIGNATURE_SCHEMA_VERSION",
    "COMPILED_CANDIDATE_CONTRACT_SCHEMA_VERSION",
    "CandidateDAGOperation",
    "CandidateDAGParameter",
    "CandidateIncidencePointContract",
    "CandidateScenarioDAG",
    "CandidateShearStepSignature",
    "CompiledCandidateScenarioContract",
    "build_all_candidate_scenario_dags",
    "build_candidate_scenario_dag",
    "candidate_dag_operation_payload",
    "candidate_dag_parameter_payload",
    "candidate_incidence_point_contract_payload",
    "candidate_scenario_dag_payload",
    "candidate_shear_step_signature_payload",
    "compiled_candidate_scenario_contract_payload",
    "extract_candidate_scenario_contract",
    "verify_candidate_scenario_dag",
    "verify_compiled_candidate_scenario_contract",
]
