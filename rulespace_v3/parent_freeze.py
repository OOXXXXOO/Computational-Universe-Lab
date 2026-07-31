"""Closed, pre-response application manifests for the V3-M0 instrument.

The public dataclasses are inert, recursively complete wire records.
``VerifiedParentFreeze`` is a live-identity capability: a valid raw manifest
must still be hydrated by this module before registry or prestructure code may
consume it.
"""

from __future__ import annotations

import copy  # noqa: F401  # Compatibility probe; authority cloning is closed below.
import math
import re
import struct
import threading
import weakref
from dataclasses import dataclass, replace
from types import FunctionType
from typing import Callable, Literal, Optional

import numpy as np

from .contracts import UndefinedReason
from .evidence import (
    _canonical_json_utf8_size,
    _make_exact_wire_cloner,
    canonical_sha,
)
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    basis_manifest_array,
    basis_manifest_payload,
    build_basis_manifest,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_basis_manifest,
    verify_frozen_tensor,
)


PARENT_FREEZE_SCHEMA_VERSION = "v3m0.parent-freeze.v1"
PARENT_FREEZE_CANDIDATE_SCHEMA_VERSION = "v3m0.parent-freeze-candidate.v1"
PARENT_FREEZE_CANDIDATE_APPLICATION_SCHEMA_VERSION = (
    "v3m0.parent-freeze-candidate-application.v1"
)
PARENT_FREEZE_CANDIDATE_SCENARIO_SCHEMA_VERSION = (
    "v3m0.parent-freeze-candidate-scenario.v1"
)
SCENARIO_BASIS_SELECTOR_SCHEMA_VERSION = "v3m0.scenario-basis-selector.v1"
SCENARIO_RESPONSE_TEMPLATE_SCHEMA_VERSION = "v3m0.scenario-response-template.v1"
SCENARIO_PREDICTION_QUANTITY_SCHEMA_VERSION = (
    "v3m0.scenario-prediction-quantity.v1"
)
SCENARIO_PREDICTION_PROFILE_SCHEMA_VERSION = (
    "v3m0.scenario-prediction-profile.v1"
)
APPLICATION_OPERATION_SCHEMA_VERSION = "v3m0.synthetic-application-operation.v1"
APPLICATION_BASIS_PROTOCOL_SCHEMA_VERSION = (
    "v3m0.synthetic-application-basis-protocol.v1"
)
APPLICATION_GRID_PROTOCOL_SCHEMA_VERSION = "v3m0.synthetic-application-grid-protocol.v1"
APPLICATION_READOUT_PROTOCOL_SCHEMA_VERSION = (
    "v3m0.synthetic-application-readout-protocol.v1"
)
APPLICATION_CONSTANTS_SCHEMA_VERSION = (
    "v3m0.synthetic-application-protocol-constants.v1"
)
APPLICATION_PREDICTION_PROFILE_SCHEMA_VERSION = (
    "v3m0.synthetic-application-prediction-profile.v1"
)
APPLICATION_SCENARIO_SCHEMA_VERSION = "v3m0.application-scenario-execution-spec.v1"
APPLICATION_SPEC_SCHEMA_VERSION = "v3m0.synthetic-control-application-spec.v1"
APPLICATION_REFERENCE_PHASE_BAND_SOURCE_ID: Literal[
    "analytic-quarter-turn-positive-band-v1"
] = "analytic-quarter-turn-positive-band-v1"
DM26_DETERMINISTIC_CONTROL_SOURCE_ID: Literal[
    "task15-dm26-deterministic-control-v1"
] = "task15-dm26-deterministic-control-v1"
PROGRAM_ID = "projective-rule-space-v3m0-v1"
TASK9_COMMIT_SHA = "39d1c1427aefa38cd46e1272affb9a10dd46a073"
TASKBOOK_SOURCE_PATH = "docsv3/v3-任务书-V3M0-因果响应与几何距离仪器.md"
IMPLEMENTATION_PLAN_SOURCE_PATH = "docsv3/v3-实施计划-V3M0-双轴仪器迁移-2026-07-30.md"
ERRATUM_SOURCE_PATH = (
    "docsv3/v3-勘误-application-scenario与typed-termination-2026-07-31.md"
)
TASKBOOK_SOURCE_SHA = "4177923fd674c963ac9232bcb2b24b802e7ab8510dd6d069118585690e0fdfbe"
IMPLEMENTATION_PLAN_SOURCE_SHA = (
    "32a9061bac1ac7bdfb0f0014de3dea55f8ca6113a806380906b594ff6a4b0f8f"
)
ERRATUM_SOURCE_SHA = "63bcda7cb83c7d725b546e18fda41bfccfc69f4a204ddd05056ed58b1499577b"
SCENARIO_RESPONSE_DESIGN_COMMIT_SHA = (
    "0842b1088bf3f6afee39cffebeab0f0ed1852060"
)
SCENARIO_RESPONSE_DESIGN_SOURCE_PATH = (
    "docsv3/v3-设计-scenario-response-refreeze-2026-07-31.md"
)
SCENARIO_RESPONSE_DESIGN_SOURCE_SHA = (
    "da374d880a052518a77461c1ea95d20918e5d1cba1ec7c759fd37127d6887381"
)
PARENT_V2_SHA = "bf5668fe03c108624426c2a38c67413818db833f8d0c178455dc424ef96ff1af"
EXPECTED_SHELL_RANK_SOURCE_ID = "parent-freeze-control-application-spec-v1"
CURVATURE_NORMALIZER_ID = "synthetic-identity-v1"

APPLICATION_CONTROL_CASE_IDS = (
    "C01_BLIND_HOLDOUT_FULL",
    "C02_CONDITIONED_ZERO",
    "C03_EQUAL_RANK_DIRECT_SUM",
    "C04_CANONICAL_ANGLE_025_075",
    "C05_PHASE_AND_SCALAR_GAIN",
    "C06_INTERNAL_NONSCALE_MIXING",
    "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
    "C08_RANK_R_MISSING_MODES",
    "C09_PURE_GAUGE_DRESSING",
    "C10_FULL_SOURCE_EXTRA_MODE",
    "C11_NULL_GREY_SIGNAL_AMPLITUDE",
    "C12_NU_INC_IR_NORMALIZATION",
    "C13_BOTH_ZERO_UNDEFINED",
    "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL",
    "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
    "C16_COVERAGE_025_075",
    "C17_QUOTIENT_GAUGE_COVERAGE",
    "C18_ABLATED_INDEPENDENT_UNARY",
    "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
    "C20_DM26_CLEAN_ZERO_TRUE_FLOOR",
)

_APPLICATION_SPEC_CANONICAL_FIELD_NAMES = (
    "application_schema_version",
    "control_case_id",
    "application_instance_id",
    "builder_id",
    "basis_protocol",
    "grid_protocol",
    "readout_protocol",
    "protocol_constant_payload",
    "operations",
    "output_operation_instance_ids",
    "scenario_execution_specs",
    "required_pipeline_stages",
    "expected_prediction_profile_id",
    "expected_prediction_profile",
    "expected_control_evidence_schema",
    "application_spec_sha",
)

ApplicationOperationKind = Literal[
    "identity-v1",
    "canonical-shear-v1",
    "phase-rotation-v1",
    "amplitude-rescale-v1",
    "source-linear-mix-v1",
    "direct-sum-v1",
    "geometry-subspace-v1",
    "coverage-subspace-v1",
    "deterministic-series-v1",
]
ApplicationExecutionLane = Literal[
    "BLOCK_SUCCESS",
    "EXPECTED_TYPED_TERMINATION",
    "ANALYSIS_CONTROL",
]
ApplicationTerminalStage = Literal[
    "activation",
    "trace",
    "stability",
    "endpoint_shell",
    "success",
]

_APPLICATION_OPERATION_KINDS = (
    "identity-v1",
    "canonical-shear-v1",
    "phase-rotation-v1",
    "amplitude-rescale-v1",
    "source-linear-mix-v1",
    "direct-sum-v1",
    "geometry-subspace-v1",
    "coverage-subspace-v1",
    "deterministic-series-v1",
)
_VALUE_KINDS = (
    "integer",
    "fp64-bits",
    "text",
    "complex128-bits",
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_UINT64_MAX = (1 << 64) - 1
_FP64_EXPONENT_MASK = 0x7FF0000000000000
_ISSUANCE_TOKEN = object()

_SOURCE_CLOSURE = (
    (
        "rulespace_v3/ablation.py",
        "1d4953eac3110b7fbb80612827e2d3c9f91bf8897fae2eb45d6ae3e5cc48a372",
    ),
    (
        "rulespace_v3/contracts.py",
        "7f0f77fceeb19d1490b84096cda0679e2b1875fba4e3d4b3753242bd54598d71",
    ),
    (
        "rulespace_v3/controls.py",
        "393533e4ba2fec0d522bdaa9e4cf76e8b77cfeb96728dcab643b7e0a1419c192",
    ),
    (
        "rulespace_v3/evidence.py",
        "8b006b55ade0983dc590b2e284c0c13268b45a5b4c9498f966f181ab7ee67004",
    ),
    (
        "rulespace_v3/factory.py",
        "c5d3b034e93782d226b183cad2a767952afad8e17177dca69fb6593f897700cc",
    ),
    (
        "rulespace_v3/trace.py",
        "671dad102c056af3a06bb912c3f10d4810380ef882fc58933fde128ec0bc66bb",
    ),
)


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    text = _text(value, field)
    if _LOWER_SHA.fullmatch(text) is None:
        raise ValueError(f"{field} must be a 64-digit lowercase hexadecimal SHA")
    return text


def _git_sha(value: object, field: str) -> str:
    text = _text(value, field)
    if _LOWER_GIT_SHA.fullmatch(text) is None:
        raise ValueError(f"{field} must be a 40-digit lowercase Git SHA")
    return text


def _int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    return value


def _positive_int(value: object, field: str) -> int:
    result = _int(value, field)
    if result <= 0:
        raise ValueError(f"{field} must be positive")
    return result


def _nonnegative_int(value: object, field: str) -> int:
    result = _int(value, field)
    if result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _uint64(value: object, field: str) -> int:
    result = _int(value, field)
    if not 0 <= result <= _UINT64_MAX:
        raise ValueError(f"{field} must be an unsigned 64-bit integer")
    return result


def _finite_fp64_bits(value: object, field: str) -> int:
    result = _uint64(value, field)
    if result & _FP64_EXPONENT_MASK == _FP64_EXPONENT_MASK:
        raise ValueError(f"{field} must encode a finite IEEE-754 binary64 value")
    return result


def _finite_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _string_tuple(
    value: object,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    result = tuple(_text(item, f"{field}[{index}]") for index, item in enumerate(value))
    if not allow_empty and not result:
        raise ValueError(f"{field} must be non-empty")
    return result


def _canonical_unique_strings(
    value: tuple[str, ...],
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    result = _string_tuple(value, field, allow_empty=allow_empty)
    if len(set(result)) != len(result):
        raise ValueError(f"{field} contains duplicate values")
    if result != tuple(sorted(result)):
        raise ValueError(f"{field} must be canonical")
    return result


def _index_tuple(
    value: object,
    field: str,
    *,
    ndim: int,
) -> tuple[int, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if len(value) != ndim:
        raise ValueError(f"{field} dimension does not match spatial_ndim")
    return tuple(_int(item, f"{field}[{index}]") for index, item in enumerate(value))


def _basis_record(basis: BasisManifest) -> dict[str, object]:
    return {**basis_manifest_payload(basis), "manifest_id": basis.manifest_id}


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {**frozen_tensor_payload(tensor), "tensor_sha": tensor.tensor_sha}


@dataclass(frozen=True)
class TaggedScalarWire:
    value_kind: Literal["integer", "fp64-bits", "text", "complex128-bits"]
    integer_value: Optional[int]
    fp64_bits_value: Optional[int]
    text_value: Optional[str]
    complex128_bits_value: Optional[tuple[int, int]]

    def __post_init__(self) -> None:
        if self.value_kind not in _VALUE_KINDS:
            raise ValueError("value_kind is not a closed tagged-scalar kind")
        present = tuple(
            value is not None
            for value in (
                self.integer_value,
                self.fp64_bits_value,
                self.text_value,
                self.complex128_bits_value,
            )
        )
        if sum(present) != 1:
            raise ValueError("TaggedScalarWire requires exactly one value")
        expected_index = _VALUE_KINDS.index(self.value_kind)
        if not present[expected_index]:
            raise ValueError("TaggedScalarWire value does not match value_kind")
        if self.integer_value is not None:
            _int(self.integer_value, "integer_value")
        if self.fp64_bits_value is not None:
            _finite_fp64_bits(self.fp64_bits_value, "fp64_bits_value")
        if self.text_value is not None:
            _text(self.text_value, "text_value")
        if self.complex128_bits_value is not None:
            value = self.complex128_bits_value
            if type(value) is not tuple or len(value) != 2:
                raise TypeError("complex128_bits_value must be a two-item tuple")
            _finite_fp64_bits(value[0], "complex128_bits_value[0]")
            _finite_fp64_bits(value[1], "complex128_bits_value[1]")


@dataclass(frozen=True)
class SyntheticApplicationOperation:
    operation_schema_version: str
    operation_instance_id: str
    operation_kind: ApplicationOperationKind
    input_operation_instance_ids: tuple[str, ...]
    parameters: tuple[tuple[str, TaggedScalarWire], ...]
    operation_sha: str

    def __post_init__(self) -> None:
        _text(self.operation_schema_version, "operation_schema_version")
        _text(self.operation_instance_id, "operation_instance_id")
        if self.operation_kind not in _APPLICATION_OPERATION_KINDS:
            raise ValueError("operation_kind is not in the closed registry")
        _string_tuple(
            self.input_operation_instance_ids,
            "input_operation_instance_ids",
            allow_empty=True,
        )
        if type(self.parameters) is not tuple:
            raise TypeError("parameters must be a tuple")
        for index, entry in enumerate(self.parameters):
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError(f"parameters[{index}] must be a name/value pair")
            _text(entry[0], f"parameters[{index}][0]")
            if type(entry[1]) is not TaggedScalarWire:
                raise TypeError(f"parameters[{index}][1] must be a TaggedScalarWire")
        _sha(self.operation_sha, "operation_sha")


@dataclass(frozen=True)
class SyntheticApplicationBasisProtocol:
    protocol_schema_version: str
    source_basis: BasisManifest
    readout_basis: BasisManifest
    protocol_sha: str

    def __post_init__(self) -> None:
        _text(self.protocol_schema_version, "protocol_schema_version")
        if type(self.source_basis) is not BasisManifest:
            raise TypeError("source_basis must be a BasisManifest")
        if type(self.readout_basis) is not BasisManifest:
            raise TypeError("readout_basis must be a BasisManifest")
        _sha(self.protocol_sha, "protocol_sha")


@dataclass(frozen=True)
class DirectionPathClosure:
    closure_id: str
    first_path_id: str
    first_path_position: int
    second_path_id: str
    second_path_position: int
    reciprocal_index: tuple[int, ...]

    def __post_init__(self) -> None:
        _text(self.closure_id, "closure_id")
        _text(self.first_path_id, "first_path_id")
        _nonnegative_int(self.first_path_position, "first_path_position")
        _text(self.second_path_id, "second_path_id")
        _nonnegative_int(self.second_path_position, "second_path_position")
        if type(self.reciprocal_index) is not tuple:
            raise TypeError("reciprocal_index must be a tuple")
        for index, value in enumerate(self.reciprocal_index):
            _int(value, f"reciprocal_index[{index}]")


@dataclass(frozen=True)
class SyntheticApplicationGridProtocol:
    protocol_schema_version: str
    spatial_ndim: int
    spatial_shape: tuple[int, ...]
    response_torus_denominators: tuple[int, ...]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    direction_ids: tuple[str, ...]
    primitive_directions: tuple[tuple[int, ...], ...]
    path_ids: tuple[str, ...]
    ordered_paths: tuple[tuple[tuple[int, ...], ...], ...]
    closure_path_pairs: tuple[DirectionPathClosure, ...]
    bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    reference_phase_band_source_id: Literal["analytic-quarter-turn-positive-band-v1"]
    expected_shell_rank: int
    expected_shell_rank_source_id: Literal["parent-freeze-control-application-spec-v1"]
    protocol_sha: str

    def __post_init__(self) -> None:
        _text(self.protocol_schema_version, "protocol_schema_version")
        _positive_int(self.spatial_ndim, "spatial_ndim")
        if type(self.spatial_shape) is not tuple:
            raise TypeError("spatial_shape must be a tuple")
        if type(self.response_torus_denominators) is not tuple:
            raise TypeError("response_torus_denominators must be a tuple")
        for field in (
            "response_reciprocal_indices",
            "primitive_directions",
            "ordered_paths",
            "closure_path_pairs",
            "bridge_reciprocal_indices",
            "bridge_steps",
            "preregistered_phase_bands",
        ):
            if type(getattr(self, field)) is not tuple:
                raise TypeError(f"{field} must be a tuple")
        if (
            self.reference_phase_band_source_id
            != APPLICATION_REFERENCE_PHASE_BAND_SOURCE_ID
        ):
            raise ValueError("reference phase-band source is not analytic")
        _string_tuple(self.direction_ids, "direction_ids")
        _string_tuple(self.path_ids, "path_ids")
        _positive_int(self.expected_shell_rank, "expected_shell_rank")
        _text(
            self.expected_shell_rank_source_id,
            "expected_shell_rank_source_id",
        )
        _sha(self.protocol_sha, "protocol_sha")


@dataclass(frozen=True)
class SyntheticApplicationReadoutProtocol:
    protocol_schema_version: str
    source_metric_whitener: FrozenComplexTensor
    h_metric_whitener: FrozenComplexTensor
    curvature_incidence_operator: FrozenComplexTensor
    curvature_metric_whitener: FrozenComplexTensor
    curvature_normalizer_id: str
    protocol_sha: str

    def __post_init__(self) -> None:
        _text(self.protocol_schema_version, "protocol_schema_version")
        for field in (
            "source_metric_whitener",
            "h_metric_whitener",
            "curvature_incidence_operator",
            "curvature_metric_whitener",
        ):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} must be a FrozenComplexTensor")
        _text(self.curvature_normalizer_id, "curvature_normalizer_id")
        _sha(self.protocol_sha, "protocol_sha")


@dataclass(frozen=True)
class SyntheticApplicationProtocolConstants:
    constants_schema_version: str
    tagged_constants: tuple[tuple[str, TaggedScalarWire], ...]
    max_operation_count: int
    max_dependency_edge_count: int
    max_parameter_count: int
    max_serialized_bytes: int
    constants_sha: str

    def __post_init__(self) -> None:
        _text(self.constants_schema_version, "constants_schema_version")
        if type(self.tagged_constants) is not tuple:
            raise TypeError("tagged_constants must be a tuple")
        for index, entry in enumerate(self.tagged_constants):
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError(f"tagged_constants[{index}] must be a name/value pair")
            _text(entry[0], f"tagged_constants[{index}][0]")
            if type(entry[1]) is not TaggedScalarWire:
                raise TypeError(
                    f"tagged_constants[{index}][1] must be a TaggedScalarWire"
                )
        _nonnegative_int(self.max_operation_count, "max_operation_count")
        _nonnegative_int(
            self.max_dependency_edge_count,
            "max_dependency_edge_count",
        )
        _nonnegative_int(self.max_parameter_count, "max_parameter_count")
        _nonnegative_int(self.max_serialized_bytes, "max_serialized_bytes")
        _sha(self.constants_sha, "constants_sha")


@dataclass(frozen=True)
class SyntheticApplicationPredictionProfile:
    prediction_schema_version: str
    prediction_profile_id: str
    control_case_id: str
    expected_exact_values: tuple[tuple[str, tuple[TaggedScalarWire, ...]], ...]
    expected_qualitative_labels: tuple[tuple[str, tuple[str, ...]], ...]
    prediction_profile_sha: str

    def __post_init__(self) -> None:
        _text(self.prediction_schema_version, "prediction_schema_version")
        _text(self.prediction_profile_id, "prediction_profile_id")
        _text(self.control_case_id, "control_case_id")
        if type(self.expected_exact_values) is not tuple:
            raise TypeError("expected_exact_values must be a tuple")
        for index, entry in enumerate(self.expected_exact_values):
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError(
                    f"expected_exact_values[{index}] must be a name/value pair"
                )
            _text(entry[0], f"expected_exact_values[{index}][0]")
            if type(entry[1]) is not tuple or not entry[1]:
                raise ValueError(
                    f"expected_exact_values[{index}][1] must be a non-empty tuple"
                )
            if not all(type(value) is TaggedScalarWire for value in entry[1]):
                raise TypeError(
                    f"expected_exact_values[{index}][1] has the wrong wire type"
                )
        if type(self.expected_qualitative_labels) is not tuple:
            raise TypeError("expected_qualitative_labels must be a tuple")
        for index, entry in enumerate(self.expected_qualitative_labels):
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError(
                    f"expected_qualitative_labels[{index}] must be a name/labels pair"
                )
            _text(entry[0], f"expected_qualitative_labels[{index}][0]")
            _string_tuple(
                entry[1],
                f"expected_qualitative_labels[{index}][1]",
            )
        if not self.expected_exact_values and not self.expected_qualitative_labels:
            raise ValueError("prediction profile body must be non-empty")
        _sha(self.prediction_profile_sha, "prediction_profile_sha")


@dataclass(frozen=True)
class ApplicationScenarioExecutionSpec:
    scenario_schema_version: str
    scenario_id: str
    operation_output_ids: tuple[str, ...]
    execution_lane: ApplicationExecutionLane
    execution_recipe_id: str
    recipe_parameter_wires: tuple[tuple[str, TaggedScalarWire], ...]
    recipe_derivation_source_id: str
    expected_terminal_stage: Optional[ApplicationTerminalStage]
    expected_undefined_reason: Optional[UndefinedReason]
    expected_artifact_type: str
    scenario_sha: str

    def __post_init__(self) -> None:
        if self.scenario_schema_version != APPLICATION_SCENARIO_SCHEMA_VERSION:
            raise ValueError("application scenario schema is not frozen")
        _text(self.scenario_id, "scenario_id")
        outputs = _string_tuple(
            self.operation_output_ids,
            "operation_output_ids",
        )
        if len(set(outputs)) != len(outputs):
            raise ValueError("operation_output_ids contains duplicates")
        if self.execution_lane not in (
            "BLOCK_SUCCESS",
            "EXPECTED_TYPED_TERMINATION",
            "ANALYSIS_CONTROL",
        ):
            raise ValueError("execution_lane is outside the closed registry")
        _text(self.execution_recipe_id, "execution_recipe_id")
        if type(self.recipe_parameter_wires) is not tuple:
            raise TypeError("recipe_parameter_wires must be a tuple")
        parameter_names: list[str] = []
        for index, entry in enumerate(self.recipe_parameter_wires):
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError(
                    f"recipe_parameter_wires[{index}] must be a name/wire pair"
                )
            parameter_names.append(
                _text(entry[0], f"recipe_parameter_wires[{index}][0]")
            )
            if type(entry[1]) is not TaggedScalarWire:
                raise TypeError(
                    f"recipe_parameter_wires[{index}][1] has the wrong wire type"
                )
        if len(set(parameter_names)) != len(parameter_names):
            raise ValueError("recipe_parameter_wires contains duplicate names")
        if tuple(parameter_names) != tuple(sorted(parameter_names)):
            raise ValueError("recipe_parameter_wires must be canonical")
        _text(
            self.recipe_derivation_source_id,
            "recipe_derivation_source_id",
        )
        _text(self.expected_artifact_type, "expected_artifact_type")
        if self.expected_terminal_stage is not None and (
            self.expected_terminal_stage
            not in (
                "activation",
                "trace",
                "stability",
                "endpoint_shell",
                "success",
            )
        ):
            raise ValueError("expected terminal stage is outside the frozen registry")
        if self.execution_lane == "BLOCK_SUCCESS":
            if (
                self.expected_terminal_stage != "success"
                or self.expected_undefined_reason is not None
                or self.expected_artifact_type != "VerifiedResponseBlock"
            ):
                raise ValueError("BLOCK_SUCCESS scenario contract is inconsistent")
        elif self.execution_lane == "EXPECTED_TYPED_TERMINATION":
            _text(self.expected_terminal_stage, "expected_terminal_stage")
            if self.expected_terminal_stage == "success":
                raise ValueError("typed termination cannot use success stage")
            if type(self.expected_undefined_reason) is not UndefinedReason:
                raise TypeError("typed termination requires an exact UndefinedReason")
            if self.expected_artifact_type != "VerifiedResponseBlockAttemptOutcome":
                raise ValueError("typed termination artifact type is not frozen")
        else:
            if (
                self.expected_terminal_stage is not None
                or self.expected_undefined_reason is not None
                or self.expected_artifact_type
                != "VerifiedDeterministicSeriesControlOutcome"
            ):
                raise ValueError("ANALYSIS_CONTROL scenario contract is inconsistent")
        _sha(self.scenario_sha, "scenario_sha")


@dataclass(frozen=True)
class V3M0SyntheticControlApplicationSpec:
    application_schema_version: str
    control_case_id: str
    application_instance_id: str
    builder_id: str
    basis_protocol: SyntheticApplicationBasisProtocol
    grid_protocol: SyntheticApplicationGridProtocol
    readout_protocol: SyntheticApplicationReadoutProtocol
    protocol_constant_payload: SyntheticApplicationProtocolConstants
    operations: tuple[SyntheticApplicationOperation, ...]
    output_operation_instance_ids: tuple[str, ...]
    scenario_execution_specs: tuple[ApplicationScenarioExecutionSpec, ...]
    required_pipeline_stages: tuple[str, ...]
    expected_prediction_profile_id: str
    expected_prediction_profile: SyntheticApplicationPredictionProfile
    expected_control_evidence_schema: str
    application_spec_sha: str

    def __post_init__(self) -> None:
        _text(self.application_schema_version, "application_schema_version")
        _text(self.control_case_id, "control_case_id")
        _text(self.application_instance_id, "application_instance_id")
        _text(self.builder_id, "builder_id")
        if type(self.basis_protocol) is not SyntheticApplicationBasisProtocol:
            raise TypeError(
                "basis_protocol must be a SyntheticApplicationBasisProtocol"
            )
        if type(self.grid_protocol) is not SyntheticApplicationGridProtocol:
            raise TypeError("grid_protocol must be a SyntheticApplicationGridProtocol")
        if type(self.readout_protocol) is not SyntheticApplicationReadoutProtocol:
            raise TypeError(
                "readout_protocol must be a SyntheticApplicationReadoutProtocol"
            )
        if (
            type(self.protocol_constant_payload)
            is not SyntheticApplicationProtocolConstants
        ):
            raise TypeError(
                "protocol_constant_payload must be a "
                "SyntheticApplicationProtocolConstants"
            )
        if type(self.operations) is not tuple:
            raise TypeError("operations must be a tuple")
        if not all(
            type(operation) is SyntheticApplicationOperation
            for operation in self.operations
        ):
            raise TypeError("operations has the wrong record type")
        _string_tuple(
            self.output_operation_instance_ids,
            "output_operation_instance_ids",
            allow_empty=True,
        )
        if type(self.scenario_execution_specs) is not tuple:
            raise TypeError("scenario_execution_specs must be a tuple")
        if not self.scenario_execution_specs:
            raise ValueError("scenario_execution_specs must be non-empty")
        if not all(
            type(scenario) is ApplicationScenarioExecutionSpec
            for scenario in self.scenario_execution_specs
        ):
            raise TypeError("scenario_execution_specs has the wrong record type")
        _string_tuple(
            self.required_pipeline_stages,
            "required_pipeline_stages",
            allow_empty=True,
        )
        _text(
            self.expected_prediction_profile_id,
            "expected_prediction_profile_id",
        )
        if (
            type(self.expected_prediction_profile)
            is not SyntheticApplicationPredictionProfile
        ):
            raise TypeError(
                "expected_prediction_profile must be a "
                "SyntheticApplicationPredictionProfile"
            )
        _text(
            self.expected_control_evidence_schema,
            "expected_control_evidence_schema",
        )
        _sha(self.application_spec_sha, "application_spec_sha")


@dataclass(frozen=True)
class ParentFreezeManifest:
    parent_freeze_schema_version: str
    program_id: Literal["projective-rule-space-v3m0-v1"]
    parent_v2_sha: str
    task9_commit_sha: Literal["39d1c1427aefa38cd46e1272affb9a10dd46a073"]
    taskbook_source_sha: str
    implementation_plan_source_sha: str
    erratum_source_sha: str
    synthetic_control_application_specs: tuple[V3M0SyntheticControlApplicationSpec, ...]
    protocol_constant_payload: SyntheticApplicationProtocolConstants
    source_closure: tuple[tuple[str, str], ...]
    parent_freeze_sha: str

    def __post_init__(self) -> None:
        _text(
            self.parent_freeze_schema_version,
            "parent_freeze_schema_version",
        )
        _text(self.program_id, "program_id")
        _sha(self.parent_v2_sha, "parent_v2_sha")
        _git_sha(self.task9_commit_sha, "task9_commit_sha")
        _sha(self.taskbook_source_sha, "taskbook_source_sha")
        _sha(
            self.implementation_plan_source_sha,
            "implementation_plan_source_sha",
        )
        _sha(self.erratum_source_sha, "erratum_source_sha")
        if type(self.synthetic_control_application_specs) is not tuple:
            raise TypeError("synthetic_control_application_specs must be a tuple")
        if not all(
            type(spec) is V3M0SyntheticControlApplicationSpec
            for spec in self.synthetic_control_application_specs
        ):
            raise TypeError(
                "synthetic_control_application_specs has the wrong record type"
            )
        if (
            type(self.protocol_constant_payload)
            is not SyntheticApplicationProtocolConstants
        ):
            raise TypeError("protocol_constant_payload has the wrong record type")
        if type(self.source_closure) is not tuple:
            raise TypeError("source_closure must be a tuple")
        for index, entry in enumerate(self.source_closure):
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError(f"source_closure[{index}] must be a path/SHA pair")
            _text(entry[0], f"source_closure[{index}][0]")
            _sha(entry[1], f"source_closure[{index}][1]")
        _sha(self.parent_freeze_sha, "parent_freeze_sha")


CandidatePreflightState = Literal[
    "PROVISIONAL_ANALYTIC_TEMPLATE",
    "PENDING_CONSTRUCTION_PREFLIGHT",
]
CandidatePredictionState = Literal[
    "PROVISIONAL_ANALYTIC_PREDICTION",
    "PENDING_CONSTRUCTION_PREFLIGHT",
]
CandidatePredictionSemantics = Literal[
    "MEASURED_EXACT",
    "ANALYTIC_SIDE",
    "FORMULA_DERIVED",
    "QUALITATIVE_REQUIRED",
]


@dataclass(frozen=True)
class ScenarioBasisSelectorSpec:
    selector_schema_version: str
    scenario_id: str
    public_source_basis_manifest_id: str
    public_readout_basis_manifest_id: str
    source_selector_derivation_id: str
    readout_selector_derivation_id: str
    source_selector: FrozenComplexTensor
    readout_selector: FrozenComplexTensor
    source_injection: FrozenComplexTensor
    readout_coisometry: FrozenComplexTensor
    selector_sha: str

    def __post_init__(self) -> None:
        _text(self.selector_schema_version, "selector_schema_version")
        _text(self.scenario_id, "scenario_id")
        _sha(
            self.public_source_basis_manifest_id,
            "public_source_basis_manifest_id",
        )
        _sha(
            self.public_readout_basis_manifest_id,
            "public_readout_basis_manifest_id",
        )
        _text(
            self.source_selector_derivation_id,
            "source_selector_derivation_id",
        )
        _text(
            self.readout_selector_derivation_id,
            "readout_selector_derivation_id",
        )
        for field in (
            "source_selector",
            "readout_selector",
            "source_injection",
            "readout_coisometry",
        ):
            tensor = getattr(self, field)
            if type(tensor) is not FrozenComplexTensor:
                raise TypeError(f"{field} must be a FrozenComplexTensor")
            verify_frozen_tensor(tensor)
        _sha(self.selector_sha, "selector_sha")


@dataclass(frozen=True)
class ScenarioResponseTemplate:
    template_schema_version: str
    scenario_id: str
    selector_sha: str
    construction_preflight_state: CandidatePreflightState
    response_torus_denominators: tuple[int, ...]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    expected_actual_shell_rank: int
    source_trial_vectors: FrozenComplexTensor
    curvature_incidence_family_id: str
    curvature_normalizer_formula_id: str
    geometry_bundle_derivation_id: Optional[str]
    template_sha: str

    def __post_init__(self) -> None:
        _text(self.template_schema_version, "template_schema_version")
        _text(self.scenario_id, "scenario_id")
        _sha(self.selector_sha, "selector_sha")
        if self.construction_preflight_state not in (
            "PROVISIONAL_ANALYTIC_TEMPLATE",
            "PENDING_CONSTRUCTION_PREFLIGHT",
        ):
            raise ValueError("construction preflight state is not frozen")
        for field in (
            "response_torus_denominators",
            "response_reciprocal_indices",
            "source_readout_bridge_reciprocal_indices",
            "source_readout_bridge_steps",
            "reference_reciprocal_index",
            "preregistered_phase_bands",
        ):
            if type(getattr(self, field)) is not tuple:
                raise TypeError(f"{field} must be a tuple")
        _positive_int(
            self.expected_actual_shell_rank,
            "expected_actual_shell_rank",
        )
        if type(self.source_trial_vectors) is not FrozenComplexTensor:
            raise TypeError("source_trial_vectors must be a FrozenComplexTensor")
        verify_frozen_tensor(self.source_trial_vectors)
        _text(
            self.curvature_incidence_family_id,
            "curvature_incidence_family_id",
        )
        _text(
            self.curvature_normalizer_formula_id,
            "curvature_normalizer_formula_id",
        )
        if self.geometry_bundle_derivation_id is not None:
            _text(
                self.geometry_bundle_derivation_id,
                "geometry_bundle_derivation_id",
            )
        _sha(self.template_sha, "template_sha")


@dataclass(frozen=True)
class ScenarioPredictionQuantity:
    quantity_schema_version: str
    quantity_id: str
    branch_scope: str
    semantics: CandidatePredictionSemantics
    exact_values: tuple[TaggedScalarWire, ...]
    side_labels: tuple[str, ...]
    formula_id: Optional[str]
    formula_parameter_wires: tuple[tuple[str, TaggedScalarWire], ...]
    qualitative_labels: tuple[str, ...]
    quantity_sha: str

    def __post_init__(self) -> None:
        _text(self.quantity_schema_version, "quantity_schema_version")
        _text(self.quantity_id, "quantity_id")
        _text(self.branch_scope, "branch_scope")
        if self.semantics not in (
            "MEASURED_EXACT",
            "ANALYTIC_SIDE",
            "FORMULA_DERIVED",
            "QUALITATIVE_REQUIRED",
        ):
            raise ValueError("prediction quantity semantics is not frozen")
        if type(self.exact_values) is not tuple or not all(
            type(item) is TaggedScalarWire for item in self.exact_values
        ):
            raise TypeError("exact_values has the wrong strict wire type")
        _string_tuple(self.side_labels, "side_labels", allow_empty=True)
        if self.formula_id is not None:
            _text(self.formula_id, "formula_id")
        if type(self.formula_parameter_wires) is not tuple:
            raise TypeError("formula_parameter_wires must be a tuple")
        parameter_names = tuple(
            _text(entry[0], "formula parameter name")
            for entry in self.formula_parameter_wires
            if type(entry) is tuple
            and len(entry) == 2
            and type(entry[1]) is TaggedScalarWire
        )
        if len(parameter_names) != len(self.formula_parameter_wires):
            raise TypeError("formula_parameter_wires has the wrong strict shape")
        if parameter_names != tuple(sorted(set(parameter_names))):
            raise ValueError("formula_parameter_wires must be unique canonical")
        _string_tuple(
            self.qualitative_labels,
            "qualitative_labels",
            allow_empty=True,
        )
        populated = (
            bool(self.exact_values),
            bool(self.side_labels),
            self.formula_id is not None,
            bool(self.qualitative_labels),
        )
        expected_index = {
            "MEASURED_EXACT": 0,
            "ANALYTIC_SIDE": 1,
            "FORMULA_DERIVED": 2,
            "QUALITATIVE_REQUIRED": 3,
        }[self.semantics]
        if not populated[expected_index] or any(
            value for index, value in enumerate(populated) if index != expected_index
        ):
            raise ValueError("prediction quantity payload contradicts semantics")
        _sha(self.quantity_sha, "quantity_sha")


@dataclass(frozen=True)
class ScenarioPredictionProfile:
    profile_schema_version: str
    scenario_id: str
    prediction_state: CandidatePredictionState
    quantities: tuple[ScenarioPredictionQuantity, ...]
    profile_sha: str

    def __post_init__(self) -> None:
        _text(self.profile_schema_version, "profile_schema_version")
        _text(self.scenario_id, "scenario_id")
        if self.prediction_state not in (
            "PROVISIONAL_ANALYTIC_PREDICTION",
            "PENDING_CONSTRUCTION_PREFLIGHT",
        ):
            raise ValueError("prediction state is not frozen")
        if type(self.quantities) is not tuple or not all(
            type(item) is ScenarioPredictionQuantity for item in self.quantities
        ):
            raise TypeError("quantities has the wrong strict type")
        if (
            self.prediction_state == "PENDING_CONSTRUCTION_PREFLIGHT"
            and self.quantities
        ):
            raise ValueError("pending construction cannot carry predictions")
        _sha(self.profile_sha, "profile_sha")


@dataclass(frozen=True)
class ParentFreezeCandidateScenario:
    candidate_scenario_schema_version: str
    control_case_id: str
    application_instance_id: str
    based_on_application_spec_sha: str
    scenario_execution_spec: ApplicationScenarioExecutionSpec
    selector_spec: ScenarioBasisSelectorSpec
    response_template: ScenarioResponseTemplate
    prediction_profile: ScenarioPredictionProfile
    candidate_scenario_sha: str

    def __post_init__(self) -> None:
        _text(
            self.candidate_scenario_schema_version,
            "candidate_scenario_schema_version",
        )
        _text(self.control_case_id, "control_case_id")
        _text(self.application_instance_id, "application_instance_id")
        _sha(
            self.based_on_application_spec_sha,
            "based_on_application_spec_sha",
        )
        if type(self.scenario_execution_spec) is not ApplicationScenarioExecutionSpec:
            raise TypeError("scenario_execution_spec has the wrong strict type")
        if type(self.selector_spec) is not ScenarioBasisSelectorSpec:
            raise TypeError("selector_spec has the wrong strict type")
        if type(self.response_template) is not ScenarioResponseTemplate:
            raise TypeError("response_template has the wrong strict type")
        if type(self.prediction_profile) is not ScenarioPredictionProfile:
            raise TypeError("prediction_profile has the wrong strict type")
        _sha(self.candidate_scenario_sha, "candidate_scenario_sha")


@dataclass(frozen=True)
class ParentFreezeCandidateApplication:
    candidate_application_schema_version: str
    control_case_id: str
    application_instance_id: str
    based_on_application_spec_sha: str
    scenario_candidates: tuple[ParentFreezeCandidateScenario, ...]
    candidate_application_sha: str

    def __post_init__(self) -> None:
        _text(
            self.candidate_application_schema_version,
            "candidate_application_schema_version",
        )
        _text(self.control_case_id, "control_case_id")
        _text(self.application_instance_id, "application_instance_id")
        _sha(
            self.based_on_application_spec_sha,
            "based_on_application_spec_sha",
        )
        if type(self.scenario_candidates) is not tuple or not all(
            type(item) is ParentFreezeCandidateScenario
            for item in self.scenario_candidates
        ):
            raise TypeError("scenario_candidates has the wrong strict type")
        if not self.scenario_candidates:
            raise ValueError("scenario_candidates must not be empty")
        _sha(self.candidate_application_sha, "candidate_application_sha")


@dataclass(frozen=True)
class ParentFreezeCandidateManifest:
    """Inert review body; it is deliberately not a ParentFreeze manifest."""

    candidate_schema_version: str
    authority_state: Literal["PROVISIONAL_NOT_ISSUED"]
    based_on_parent_freeze_sha: str
    scenario_response_design_commit_sha: str
    scenario_response_design_source_path: str
    scenario_response_design_source_sha: str
    proposed_parent_freeze_schema_version: str
    proposed_application_scenario_schema_version: str
    required_finalization_state: Literal[
        "SIGNED_INCREMENTAL_ERRATUM_AND_SINGLE_PARENT_REFREEZE"
    ]
    application_candidates: tuple[ParentFreezeCandidateApplication, ...]
    candidate_sha: str

    def __post_init__(self) -> None:
        _text(self.candidate_schema_version, "candidate_schema_version")
        if self.authority_state != "PROVISIONAL_NOT_ISSUED":
            raise ValueError("parent candidate cannot claim issued authority")
        _sha(self.based_on_parent_freeze_sha, "based_on_parent_freeze_sha")
        _git_sha(
            self.scenario_response_design_commit_sha,
            "scenario_response_design_commit_sha",
        )
        _text(
            self.scenario_response_design_source_path,
            "scenario_response_design_source_path",
        )
        _sha(
            self.scenario_response_design_source_sha,
            "scenario_response_design_source_sha",
        )
        _text(
            self.proposed_parent_freeze_schema_version,
            "proposed_parent_freeze_schema_version",
        )
        _text(
            self.proposed_application_scenario_schema_version,
            "proposed_application_scenario_schema_version",
        )
        if self.required_finalization_state != (
            "SIGNED_INCREMENTAL_ERRATUM_AND_SINGLE_PARENT_REFREEZE"
        ):
            raise ValueError("parent candidate finalization gate is not frozen")
        if type(self.application_candidates) is not tuple:
            raise TypeError("application_candidates must be a tuple")
        if not all(
            type(item) is ParentFreezeCandidateApplication
            for item in self.application_candidates
        ):
            raise TypeError("application_candidates has the wrong strict type")
        _sha(self.candidate_sha, "candidate_sha")


_PARENT_WIRE_TYPES = (
    ParentFreezeManifest,
    V3M0SyntheticControlApplicationSpec,
    ApplicationScenarioExecutionSpec,
    SyntheticApplicationPredictionProfile,
    SyntheticApplicationProtocolConstants,
    SyntheticApplicationReadoutProtocol,
    SyntheticApplicationGridProtocol,
    DirectionPathClosure,
    SyntheticApplicationBasisProtocol,
    SyntheticApplicationOperation,
    TaggedScalarWire,
    BasisManifest,
    FrozenComplexTensor,
)
_clone_parent_wire = _make_exact_wire_cloner(
    _PARENT_WIRE_TYPES,
    atomic_types=(UndefinedReason,),
)


def _require_exact_parent_schema(
    value: object,
    field: str,
    *,
    _allowed_types: tuple[type[object], ...] = _PARENT_WIRE_TYPES,
    _type=type,
    _tuple_type=tuple,
    _list_type=list,
    _dict_type=dict,
    _vars=vars,
    _getattr=getattr,
    _frozenset=frozenset,
    _sorted=sorted,
    _enumerate=enumerate,
    _hasattr=hasattr,
    _type_error=TypeError,
    _value_error=ValueError,
) -> None:
    """Reject subclasses and unknown fields throughout a parent wire."""

    pending: list[tuple[object, str]] = _list_type(((value, field),))
    while pending:
        current, current_field = pending.pop()
        current_type = _type(current)
        if current_type in _allowed_types:
            expected = _frozenset(current_type.__dataclass_fields__)
            try:
                observed = _frozenset(_vars(current))
            except _type_error as exc:
                raise _type_error(f"{current_field} has no exact record body") from exc
            if observed != expected:
                raise _value_error(
                    f"{current_field} fields are not exact: "
                    f"missing={_sorted(expected - observed)!r}, "
                    f"unknown={_sorted(observed - expected)!r}"
                )
            for name in current_type.__dataclass_fields__:
                pending.append(
                    (
                        _getattr(current, name),
                        f"{current_field}.{name}",
                    )
                )
        elif _hasattr(current_type, "__dataclass_fields__"):
            raise _type_error(f"{current_field} has a non-exact parent record type")
        elif current_type is _tuple_type or current_type is _list_type:
            for index, item in _enumerate(current):
                pending.append((item, f"{current_field}[{index}]"))
        elif current_type is _dict_type:
            for key, item in current.items():
                pending.append((item, f"{current_field}[{key!r}]"))


def tagged_scalar_wire_payload(wire: TaggedScalarWire) -> dict[str, object]:
    if type(wire) is not TaggedScalarWire:
        raise TypeError("wire must be a TaggedScalarWire")
    complex_bits = wire.complex128_bits_value
    return {
        "value_kind": wire.value_kind,
        "integer_value": wire.integer_value,
        "fp64_bits_value": wire.fp64_bits_value,
        "text_value": wire.text_value,
        "complex128_bits_value": (None if complex_bits is None else list(complex_bits)),
    }


def synthetic_application_operation_payload(
    operation: SyntheticApplicationOperation,
) -> dict[str, object]:
    if type(operation) is not SyntheticApplicationOperation:
        raise TypeError("operation must be a SyntheticApplicationOperation")
    return {
        "operation_schema_version": operation.operation_schema_version,
        "operation_instance_id": operation.operation_instance_id,
        "operation_kind": operation.operation_kind,
        "input_operation_instance_ids": list(operation.input_operation_instance_ids),
        "parameters": [
            [name, tagged_scalar_wire_payload(value)]
            for name, value in operation.parameters
        ],
    }


def _operation_record(
    operation: SyntheticApplicationOperation,
) -> dict[str, object]:
    return {
        **synthetic_application_operation_payload(operation),
        "operation_sha": operation.operation_sha,
    }


def synthetic_application_basis_protocol_payload(
    protocol: SyntheticApplicationBasisProtocol,
) -> dict[str, object]:
    if type(protocol) is not SyntheticApplicationBasisProtocol:
        raise TypeError("protocol must be a SyntheticApplicationBasisProtocol")
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "source_basis": _basis_record(protocol.source_basis),
        "readout_basis": _basis_record(protocol.readout_basis),
    }


def _basis_protocol_record(
    protocol: SyntheticApplicationBasisProtocol,
) -> dict[str, object]:
    return {
        **synthetic_application_basis_protocol_payload(protocol),
        "protocol_sha": protocol.protocol_sha,
    }


def _closure_record(closure: DirectionPathClosure) -> dict[str, object]:
    if type(closure) is not DirectionPathClosure:
        raise TypeError("closure must be a DirectionPathClosure")
    return {
        "closure_id": closure.closure_id,
        "first_path_id": closure.first_path_id,
        "first_path_position": closure.first_path_position,
        "second_path_id": closure.second_path_id,
        "second_path_position": closure.second_path_position,
        "reciprocal_index": list(closure.reciprocal_index),
    }


def synthetic_application_grid_protocol_payload(
    protocol: SyntheticApplicationGridProtocol,
) -> dict[str, object]:
    if type(protocol) is not SyntheticApplicationGridProtocol:
        raise TypeError("protocol must be a SyntheticApplicationGridProtocol")
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "spatial_ndim": protocol.spatial_ndim,
        "spatial_shape": list(protocol.spatial_shape),
        "response_torus_denominators": list(protocol.response_torus_denominators),
        "response_reciprocal_indices": [
            list(index) for index in protocol.response_reciprocal_indices
        ],
        "direction_ids": list(protocol.direction_ids),
        "primitive_directions": [
            list(direction) for direction in protocol.primitive_directions
        ],
        "path_ids": list(protocol.path_ids),
        "ordered_paths": [
            [list(index) for index in path] for path in protocol.ordered_paths
        ],
        "closure_path_pairs": [
            _closure_record(closure) for closure in protocol.closure_path_pairs
        ],
        "bridge_reciprocal_indices": [
            list(index) for index in protocol.bridge_reciprocal_indices
        ],
        "bridge_steps": list(protocol.bridge_steps),
        "reference_reciprocal_index": list(protocol.reference_reciprocal_index),
        "preregistered_phase_bands": [
            list(band) for band in protocol.preregistered_phase_bands
        ],
        "reference_phase_band_source_id": (protocol.reference_phase_band_source_id),
        "expected_shell_rank": protocol.expected_shell_rank,
        "expected_shell_rank_source_id": (protocol.expected_shell_rank_source_id),
    }


def _grid_protocol_record(
    protocol: SyntheticApplicationGridProtocol,
) -> dict[str, object]:
    return {
        **synthetic_application_grid_protocol_payload(protocol),
        "protocol_sha": protocol.protocol_sha,
    }


def synthetic_application_readout_protocol_payload(
    protocol: SyntheticApplicationReadoutProtocol,
) -> dict[str, object]:
    if type(protocol) is not SyntheticApplicationReadoutProtocol:
        raise TypeError("protocol must be a SyntheticApplicationReadoutProtocol")
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "source_metric_whitener": _tensor_record(protocol.source_metric_whitener),
        "h_metric_whitener": _tensor_record(protocol.h_metric_whitener),
        "curvature_incidence_operator": _tensor_record(
            protocol.curvature_incidence_operator
        ),
        "curvature_metric_whitener": _tensor_record(protocol.curvature_metric_whitener),
        "curvature_normalizer_id": protocol.curvature_normalizer_id,
    }


def _readout_protocol_record(
    protocol: SyntheticApplicationReadoutProtocol,
) -> dict[str, object]:
    return {
        **synthetic_application_readout_protocol_payload(protocol),
        "protocol_sha": protocol.protocol_sha,
    }


def synthetic_application_protocol_constants_payload(
    constants: SyntheticApplicationProtocolConstants,
) -> dict[str, object]:
    if type(constants) is not SyntheticApplicationProtocolConstants:
        raise TypeError("constants must be a SyntheticApplicationProtocolConstants")
    return {
        "constants_schema_version": constants.constants_schema_version,
        "tagged_constants": [
            [name, tagged_scalar_wire_payload(value)]
            for name, value in constants.tagged_constants
        ],
        "max_operation_count": constants.max_operation_count,
        "max_dependency_edge_count": constants.max_dependency_edge_count,
        "max_parameter_count": constants.max_parameter_count,
        "max_serialized_bytes": constants.max_serialized_bytes,
    }


def _constants_record(
    constants: SyntheticApplicationProtocolConstants,
) -> dict[str, object]:
    return {
        **synthetic_application_protocol_constants_payload(constants),
        "constants_sha": constants.constants_sha,
    }


def synthetic_application_prediction_profile_payload(
    profile: SyntheticApplicationPredictionProfile,
) -> dict[str, object]:
    if type(profile) is not SyntheticApplicationPredictionProfile:
        raise TypeError("profile must be a SyntheticApplicationPredictionProfile")
    return {
        "prediction_schema_version": profile.prediction_schema_version,
        "prediction_profile_id": profile.prediction_profile_id,
        "control_case_id": profile.control_case_id,
        "expected_exact_values": [
            [
                name,
                [tagged_scalar_wire_payload(value) for value in values],
            ]
            for name, values in profile.expected_exact_values
        ],
        "expected_qualitative_labels": [
            [name, list(labels)] for name, labels in profile.expected_qualitative_labels
        ],
    }


def _prediction_profile_record(
    profile: SyntheticApplicationPredictionProfile,
) -> dict[str, object]:
    return {
        **synthetic_application_prediction_profile_payload(profile),
        "prediction_profile_sha": profile.prediction_profile_sha,
    }


def application_scenario_execution_spec_payload(
    scenario: ApplicationScenarioExecutionSpec,
) -> dict[str, object]:
    _require_exact_parent_schema(scenario, "application scenario")
    if type(scenario) is not ApplicationScenarioExecutionSpec:
        raise TypeError("scenario must be an ApplicationScenarioExecutionSpec")
    scenario.__post_init__()
    reason = scenario.expected_undefined_reason
    return {
        "scenario_schema_version": scenario.scenario_schema_version,
        "scenario_id": scenario.scenario_id,
        "operation_output_ids": list(scenario.operation_output_ids),
        "execution_lane": scenario.execution_lane,
        "execution_recipe_id": scenario.execution_recipe_id,
        "recipe_parameter_wires": [
            [name, tagged_scalar_wire_payload(wire)]
            for name, wire in scenario.recipe_parameter_wires
        ],
        "recipe_derivation_source_id": (scenario.recipe_derivation_source_id),
        "expected_terminal_stage": scenario.expected_terminal_stage,
        "expected_undefined_reason": None if reason is None else reason.value,
        "expected_artifact_type": scenario.expected_artifact_type,
    }


def _scenario_record(
    scenario: ApplicationScenarioExecutionSpec,
) -> dict[str, object]:
    return {
        **application_scenario_execution_spec_payload(scenario),
        "scenario_sha": scenario.scenario_sha,
    }


def synthetic_control_application_spec_payload(
    spec: V3M0SyntheticControlApplicationSpec,
) -> dict[str, object]:
    if type(spec) is not V3M0SyntheticControlApplicationSpec:
        raise TypeError("spec must be a V3M0SyntheticControlApplicationSpec")
    return {
        "application_schema_version": spec.application_schema_version,
        "control_case_id": spec.control_case_id,
        "application_instance_id": spec.application_instance_id,
        "builder_id": spec.builder_id,
        "basis_protocol": _basis_protocol_record(spec.basis_protocol),
        "grid_protocol": _grid_protocol_record(spec.grid_protocol),
        "readout_protocol": _readout_protocol_record(spec.readout_protocol),
        "protocol_constant_payload": _constants_record(spec.protocol_constant_payload),
        "operations": [_operation_record(operation) for operation in spec.operations],
        "output_operation_instance_ids": list(spec.output_operation_instance_ids),
        "scenario_execution_specs": [
            _scenario_record(scenario) for scenario in spec.scenario_execution_specs
        ],
        "required_pipeline_stages": list(spec.required_pipeline_stages),
        "expected_prediction_profile_id": (spec.expected_prediction_profile_id),
        "expected_prediction_profile": _prediction_profile_record(
            spec.expected_prediction_profile
        ),
        "expected_control_evidence_schema": (spec.expected_control_evidence_schema),
    }


def _application_spec_record(
    spec: V3M0SyntheticControlApplicationSpec,
) -> dict[str, object]:
    return {
        **synthetic_control_application_spec_payload(spec),
        "application_spec_sha": spec.application_spec_sha,
    }


def parent_freeze_manifest_payload(
    manifest: ParentFreezeManifest,
) -> dict[str, object]:
    if type(manifest) is not ParentFreezeManifest:
        raise TypeError("manifest must be a ParentFreezeManifest")
    return {
        "parent_freeze_schema_version": manifest.parent_freeze_schema_version,
        "program_id": manifest.program_id,
        "parent_v2_sha": manifest.parent_v2_sha,
        "task9_commit_sha": manifest.task9_commit_sha,
        "taskbook_source_sha": manifest.taskbook_source_sha,
        "implementation_plan_source_sha": (manifest.implementation_plan_source_sha),
        "erratum_source_sha": manifest.erratum_source_sha,
        "synthetic_control_application_specs": [
            _application_spec_record(spec)
            for spec in manifest.synthetic_control_application_specs
        ],
        "protocol_constant_payload": _constants_record(
            manifest.protocol_constant_payload
        ),
        "source_closure": [list(entry) for entry in manifest.source_closure],
    }


def scenario_basis_selector_spec_payload(
    selector: ScenarioBasisSelectorSpec,
) -> dict[str, object]:
    if type(selector) is not ScenarioBasisSelectorSpec:
        raise TypeError("selector must be a ScenarioBasisSelectorSpec")
    return {
        "selector_schema_version": selector.selector_schema_version,
        "scenario_id": selector.scenario_id,
        "public_source_basis_manifest_id": (
            selector.public_source_basis_manifest_id
        ),
        "public_readout_basis_manifest_id": (
            selector.public_readout_basis_manifest_id
        ),
        "source_selector_derivation_id": (
            selector.source_selector_derivation_id
        ),
        "readout_selector_derivation_id": (
            selector.readout_selector_derivation_id
        ),
        "source_selector": _tensor_record(selector.source_selector),
        "readout_selector": _tensor_record(selector.readout_selector),
        "source_injection": _tensor_record(selector.source_injection),
        "readout_coisometry": _tensor_record(selector.readout_coisometry),
    }


def _candidate_selector_record(
    selector: ScenarioBasisSelectorSpec,
) -> dict[str, object]:
    return {
        **scenario_basis_selector_spec_payload(selector),
        "selector_sha": selector.selector_sha,
    }


def scenario_response_template_payload(
    template: ScenarioResponseTemplate,
) -> dict[str, object]:
    if type(template) is not ScenarioResponseTemplate:
        raise TypeError("template must be a ScenarioResponseTemplate")
    return {
        "template_schema_version": template.template_schema_version,
        "scenario_id": template.scenario_id,
        "selector_sha": template.selector_sha,
        "construction_preflight_state": template.construction_preflight_state,
        "response_torus_denominators": list(
            template.response_torus_denominators
        ),
        "response_reciprocal_indices": [
            list(item) for item in template.response_reciprocal_indices
        ],
        "source_readout_bridge_reciprocal_indices": [
            list(item)
            for item in template.source_readout_bridge_reciprocal_indices
        ],
        "source_readout_bridge_steps": list(
            template.source_readout_bridge_steps
        ),
        "reference_reciprocal_index": list(
            template.reference_reciprocal_index
        ),
        "preregistered_phase_bands": [
            list(item) for item in template.preregistered_phase_bands
        ],
        "expected_actual_shell_rank": template.expected_actual_shell_rank,
        "source_trial_vectors": _tensor_record(template.source_trial_vectors),
        "curvature_incidence_family_id": (
            template.curvature_incidence_family_id
        ),
        "curvature_normalizer_formula_id": (
            template.curvature_normalizer_formula_id
        ),
        "geometry_bundle_derivation_id": (
            template.geometry_bundle_derivation_id
        ),
    }


def _candidate_response_template_record(
    template: ScenarioResponseTemplate,
) -> dict[str, object]:
    return {
        **scenario_response_template_payload(template),
        "template_sha": template.template_sha,
    }


def scenario_prediction_quantity_payload(
    quantity: ScenarioPredictionQuantity,
) -> dict[str, object]:
    if type(quantity) is not ScenarioPredictionQuantity:
        raise TypeError("quantity must be a ScenarioPredictionQuantity")
    return {
        "quantity_schema_version": quantity.quantity_schema_version,
        "quantity_id": quantity.quantity_id,
        "branch_scope": quantity.branch_scope,
        "semantics": quantity.semantics,
        "exact_values": [
            tagged_scalar_wire_payload(item) for item in quantity.exact_values
        ],
        "side_labels": list(quantity.side_labels),
        "formula_id": quantity.formula_id,
        "formula_parameter_wires": [
            [name, tagged_scalar_wire_payload(wire)]
            for name, wire in quantity.formula_parameter_wires
        ],
        "qualitative_labels": list(quantity.qualitative_labels),
    }


def _candidate_prediction_quantity_record(
    quantity: ScenarioPredictionQuantity,
) -> dict[str, object]:
    return {
        **scenario_prediction_quantity_payload(quantity),
        "quantity_sha": quantity.quantity_sha,
    }


def scenario_prediction_profile_payload(
    profile: ScenarioPredictionProfile,
) -> dict[str, object]:
    if type(profile) is not ScenarioPredictionProfile:
        raise TypeError("profile must be a ScenarioPredictionProfile")
    return {
        "profile_schema_version": profile.profile_schema_version,
        "scenario_id": profile.scenario_id,
        "prediction_state": profile.prediction_state,
        "quantities": [
            _candidate_prediction_quantity_record(item)
            for item in profile.quantities
        ],
    }


def _candidate_prediction_profile_record(
    profile: ScenarioPredictionProfile,
) -> dict[str, object]:
    return {
        **scenario_prediction_profile_payload(profile),
        "profile_sha": profile.profile_sha,
    }


def parent_freeze_candidate_scenario_payload(
    scenario: ParentFreezeCandidateScenario,
) -> dict[str, object]:
    if type(scenario) is not ParentFreezeCandidateScenario:
        raise TypeError("scenario must be a ParentFreezeCandidateScenario")
    return {
        "candidate_scenario_schema_version": (
            scenario.candidate_scenario_schema_version
        ),
        "control_case_id": scenario.control_case_id,
        "application_instance_id": scenario.application_instance_id,
        "based_on_application_spec_sha": scenario.based_on_application_spec_sha,
        "scenario_execution_spec": _scenario_record(
            scenario.scenario_execution_spec
        ),
        "selector_spec": _candidate_selector_record(scenario.selector_spec),
        "response_template": _candidate_response_template_record(
            scenario.response_template
        ),
        "prediction_profile": _candidate_prediction_profile_record(
            scenario.prediction_profile
        ),
    }


def _candidate_scenario_record(
    scenario: ParentFreezeCandidateScenario,
) -> dict[str, object]:
    return {
        **parent_freeze_candidate_scenario_payload(scenario),
        "candidate_scenario_sha": scenario.candidate_scenario_sha,
    }


def parent_freeze_candidate_application_payload(
    application: ParentFreezeCandidateApplication,
) -> dict[str, object]:
    if type(application) is not ParentFreezeCandidateApplication:
        raise TypeError("application must be a ParentFreezeCandidateApplication")
    return {
        "candidate_application_schema_version": (
            application.candidate_application_schema_version
        ),
        "control_case_id": application.control_case_id,
        "application_instance_id": application.application_instance_id,
        "based_on_application_spec_sha": (
            application.based_on_application_spec_sha
        ),
        "scenario_candidates": [
            _candidate_scenario_record(item)
            for item in application.scenario_candidates
        ],
    }


def _candidate_application_record(
    application: ParentFreezeCandidateApplication,
) -> dict[str, object]:
    return {
        **parent_freeze_candidate_application_payload(application),
        "candidate_application_sha": application.candidate_application_sha,
    }


def parent_freeze_candidate_manifest_payload(
    candidate: ParentFreezeCandidateManifest,
) -> dict[str, object]:
    """Serialize the inert review candidate without producing a Parent root."""

    if type(candidate) is not ParentFreezeCandidateManifest:
        raise TypeError("candidate must be a ParentFreezeCandidateManifest")
    return {
        "candidate_schema_version": candidate.candidate_schema_version,
        "authority_state": candidate.authority_state,
        "based_on_parent_freeze_sha": candidate.based_on_parent_freeze_sha,
        "scenario_response_design_commit_sha": (
            candidate.scenario_response_design_commit_sha
        ),
        "scenario_response_design_source_path": (
            candidate.scenario_response_design_source_path
        ),
        "scenario_response_design_source_sha": (
            candidate.scenario_response_design_source_sha
        ),
        "proposed_parent_freeze_schema_version": (
            candidate.proposed_parent_freeze_schema_version
        ),
        "proposed_application_scenario_schema_version": (
            candidate.proposed_application_scenario_schema_version
        ),
        "required_finalization_state": candidate.required_finalization_state,
        "application_candidates": [
            _candidate_application_record(item)
            for item in candidate.application_candidates
        ],
    }


def _manifest_record(manifest: ParentFreezeManifest) -> dict[str, object]:
    return {
        **parent_freeze_manifest_payload(manifest),
        "parent_freeze_sha": manifest.parent_freeze_sha,
    }


def _verify_basis_protocol(
    protocol: SyntheticApplicationBasisProtocol,
) -> None:
    if type(protocol) is not SyntheticApplicationBasisProtocol:
        raise TypeError("basis_protocol must be a SyntheticApplicationBasisProtocol")
    if protocol.protocol_schema_version != APPLICATION_BASIS_PROTOCOL_SCHEMA_VERSION:
        raise ValueError("unexpected basis protocol_schema_version")
    verify_basis_manifest(protocol.source_basis)
    verify_basis_manifest(protocol.readout_basis)
    if protocol.source_basis.role != "source":
        raise ValueError("source_basis role must be source")
    if protocol.readout_basis.role != "readout":
        raise ValueError("readout_basis role must be readout")
    if (
        protocol.source_basis.state_schema_id != protocol.readout_basis.state_schema_id
        or protocol.source_basis.channel_order != protocol.readout_basis.channel_order
    ):
        raise ValueError("source/readout basis state schema mismatch")
    expected = canonical_sha(synthetic_application_basis_protocol_payload(protocol))
    if protocol.protocol_sha != expected:
        raise ValueError("basis protocol_sha does not match complete body")


def _verify_grid_protocol(
    protocol: SyntheticApplicationGridProtocol,
) -> None:
    if type(protocol) is not SyntheticApplicationGridProtocol:
        raise TypeError("grid_protocol must be a SyntheticApplicationGridProtocol")
    if protocol.protocol_schema_version != APPLICATION_GRID_PROTOCOL_SCHEMA_VERSION:
        raise ValueError("unexpected grid protocol_schema_version")
    ndim = _positive_int(protocol.spatial_ndim, "spatial_ndim")
    if len(protocol.spatial_shape) != ndim:
        raise ValueError("spatial_shape dimension mismatch")
    shape = tuple(
        _positive_int(value, f"spatial_shape[{index}]")
        for index, value in enumerate(protocol.spatial_shape)
    )
    if len(protocol.response_torus_denominators) != ndim:
        raise ValueError("response_torus_denominators dimension mismatch")
    denominators = tuple(
        _positive_int(value, f"response_torus_denominators[{index}]")
        for index, value in enumerate(protocol.response_torus_denominators)
    )

    def verified_indices(
        values: tuple[tuple[int, ...], ...],
        field: str,
        moduli: tuple[int, ...],
    ) -> tuple[tuple[int, ...], ...]:
        if type(values) is not tuple or not values:
            raise ValueError(f"{field} must be a non-empty tuple")
        result = tuple(
            _index_tuple(value, f"{field}[{index}]", ndim=ndim)
            for index, value in enumerate(values)
        )
        if len(set(result)) != len(result):
            raise ValueError(f"{field} contains duplicate indices")
        if result != tuple(sorted(result)):
            raise ValueError(f"{field} must be canonical")
        for item in result:
            if any(
                not 0 <= coordinate < modulus
                for coordinate, modulus in zip(item, moduli)
            ):
                raise ValueError(f"{field} contains an out-of-range index")
        return result

    response_indices = verified_indices(
        protocol.response_reciprocal_indices,
        "response_reciprocal_indices",
        denominators,
    )
    bridge_indices = verified_indices(
        protocol.bridge_reciprocal_indices,
        "bridge_reciprocal_indices",
        shape,
    )
    del bridge_indices
    direction_ids = _canonical_unique_strings(
        protocol.direction_ids,
        "direction_ids",
    )
    if len(direction_ids) != len(protocol.primitive_directions):
        raise ValueError("direction_ids and primitive_directions must align")
    for index, direction in enumerate(protocol.primitive_directions):
        verified = _index_tuple(
            direction,
            f"primitive_directions[{index}]",
            ndim=ndim,
        )
        if not any(verified):
            raise ValueError("primitive_directions must be nonzero")
    path_ids = _canonical_unique_strings(protocol.path_ids, "path_ids")
    if len(path_ids) != len(protocol.ordered_paths):
        raise ValueError("path_ids and ordered_paths must align")
    path_lookup: dict[str, tuple[tuple[int, ...], ...]] = {}
    for path_id, path in zip(path_ids, protocol.ordered_paths):
        if type(path) is not tuple or not path:
            raise ValueError("ordered_paths entries must be non-empty tuples")
        points = tuple(
            _index_tuple(
                point,
                f"ordered_paths[{path_id}][{index}]",
                ndim=ndim,
            )
            for index, point in enumerate(path)
        )
        if any(point not in response_indices for point in points):
            raise ValueError("ordered_paths must use response grid indices")
        path_lookup[path_id] = points
    closure_ids: list[str] = []
    for closure in protocol.closure_path_pairs:
        if type(closure) is not DirectionPathClosure:
            raise TypeError("closure_path_pairs entries must be DirectionPathClosure")
        closure_ids.append(closure.closure_id)
        if (
            closure.first_path_id not in path_lookup
            or closure.second_path_id not in path_lookup
        ):
            raise ValueError("closure references a missing path")
        first = path_lookup[closure.first_path_id]
        second = path_lookup[closure.second_path_id]
        if not 0 <= closure.first_path_position < len(first):
            raise ValueError("closure first_path_position is out of range")
        if not 0 <= closure.second_path_position < len(second):
            raise ValueError("closure second_path_position is out of range")
        reciprocal_index = _index_tuple(
            closure.reciprocal_index,
            "closure.reciprocal_index",
            ndim=ndim,
        )
        if (
            first[closure.first_path_position] != reciprocal_index
            or second[closure.second_path_position] != reciprocal_index
        ):
            raise ValueError("closure paths do not meet at reciprocal_index")
    if len(set(closure_ids)) != len(closure_ids):
        raise ValueError("closure_path_pairs contains duplicate closure IDs")
    if tuple(closure_ids) != tuple(sorted(closure_ids)):
        raise ValueError("closure_path_pairs must be canonical")
    if type(protocol.bridge_steps) is not tuple or not protocol.bridge_steps:
        raise ValueError("bridge_steps must be a non-empty tuple")
    bridge_steps = tuple(
        _positive_int(value, f"bridge_steps[{index}]")
        for index, value in enumerate(protocol.bridge_steps)
    )
    if len(set(bridge_steps)) != len(bridge_steps):
        raise ValueError("bridge_steps contains duplicates")
    if bridge_steps != tuple(sorted(bridge_steps)):
        raise ValueError("bridge_steps must be canonical")
    reference = _index_tuple(
        protocol.reference_reciprocal_index,
        "reference_reciprocal_index",
        ndim=ndim,
    )
    if reference not in response_indices:
        raise ValueError("reference_reciprocal_index is absent from response grid")
    if (
        type(protocol.preregistered_phase_bands) is not tuple
        or not protocol.preregistered_phase_bands
    ):
        raise ValueError("preregistered_phase_bands must be non-empty")
    bands: list[tuple[float, float]] = []
    for index, band in enumerate(protocol.preregistered_phase_bands):
        if type(band) is not tuple or len(band) != 2:
            raise TypeError(f"preregistered_phase_bands[{index}] must be a pair")
        lower = _finite_float(
            band[0],
            f"preregistered_phase_bands[{index}][0]",
        )
        upper = _finite_float(
            band[1],
            f"preregistered_phase_bands[{index}][1]",
        )
        if not lower < upper:
            raise ValueError("phase band lower endpoint must be below upper")
        bands.append((lower, upper))
    if tuple(bands) != tuple(sorted(bands)):
        raise ValueError("preregistered_phase_bands must be canonical")
    if (
        protocol.reference_phase_band_source_id
        != APPLICATION_REFERENCE_PHASE_BAND_SOURCE_ID
    ):
        raise ValueError("reference phase-band source is not analytic")
    _positive_int(protocol.expected_shell_rank, "expected_shell_rank")
    if protocol.expected_shell_rank_source_id != EXPECTED_SHELL_RANK_SOURCE_ID:
        raise ValueError("unexpected expected_shell_rank_source_id")
    expected = canonical_sha(synthetic_application_grid_protocol_payload(protocol))
    if protocol.protocol_sha != expected:
        raise ValueError("grid protocol_sha does not match complete body")


def _verify_readout_protocol(
    protocol: SyntheticApplicationReadoutProtocol,
) -> None:
    if type(protocol) is not SyntheticApplicationReadoutProtocol:
        raise TypeError(
            "readout_protocol must be a SyntheticApplicationReadoutProtocol"
        )
    if protocol.protocol_schema_version != APPLICATION_READOUT_PROTOCOL_SCHEMA_VERSION:
        raise ValueError("unexpected readout protocol_schema_version")
    tensors = (
        protocol.source_metric_whitener,
        protocol.h_metric_whitener,
        protocol.curvature_incidence_operator,
        protocol.curvature_metric_whitener,
    )
    for tensor in tensors:
        verify_frozen_tensor(tensor)
        if len(tensor.shape) != 2:
            raise ValueError("readout protocol tensors must be matrices")
    for tensor in (
        protocol.source_metric_whitener,
        protocol.h_metric_whitener,
        protocol.curvature_metric_whitener,
    ):
        if tensor.shape[0] != tensor.shape[1]:
            raise ValueError("metric whiteners must be square")
    incidence = protocol.curvature_incidence_operator
    if incidence.shape[1] != protocol.h_metric_whitener.shape[0]:
        raise ValueError("curvature incidence input dimension mismatch")
    if incidence.shape[0] != protocol.curvature_metric_whitener.shape[0]:
        raise ValueError("curvature incidence output dimension mismatch")
    _text(protocol.curvature_normalizer_id, "curvature_normalizer_id")
    expected = canonical_sha(synthetic_application_readout_protocol_payload(protocol))
    if protocol.protocol_sha != expected:
        raise ValueError("readout protocol_sha does not match complete body")


def _verify_protocol_constants(
    constants: SyntheticApplicationProtocolConstants,
) -> None:
    if type(constants) is not SyntheticApplicationProtocolConstants:
        raise TypeError("constants must be a SyntheticApplicationProtocolConstants")
    if constants.constants_schema_version != APPLICATION_CONSTANTS_SCHEMA_VERSION:
        raise ValueError("unexpected constants_schema_version")
    names = tuple(name for name, _ in constants.tagged_constants)
    if not names:
        raise ValueError("tagged_constants must be non-empty")
    if len(set(names)) != len(names):
        raise ValueError("tagged_constants contains duplicate names")
    if names != tuple(sorted(names)):
        raise ValueError("tagged_constants must be canonical")
    for _, wire in constants.tagged_constants:
        if type(wire) is not TaggedScalarWire:
            raise TypeError("tagged_constants has the wrong wire type")
    for field in (
        "max_operation_count",
        "max_dependency_edge_count",
        "max_parameter_count",
        "max_serialized_bytes",
    ):
        _nonnegative_int(getattr(constants, field), field)
    expected = canonical_sha(
        synthetic_application_protocol_constants_payload(constants)
    )
    if constants.constants_sha != expected:
        raise ValueError("constants_sha does not match complete body")


def _verify_prediction_profile(
    profile: SyntheticApplicationPredictionProfile,
    *,
    control_case_id: str,
) -> None:
    if type(profile) is not SyntheticApplicationPredictionProfile:
        raise TypeError(
            "expected_prediction_profile must be a "
            "SyntheticApplicationPredictionProfile"
        )
    if (
        profile.prediction_schema_version
        != APPLICATION_PREDICTION_PROFILE_SCHEMA_VERSION
    ):
        raise ValueError("unexpected prediction_schema_version")
    if profile.control_case_id != control_case_id:
        raise ValueError(
            "prediction profile control_case_id does not match application"
        )
    exact_names = tuple(name for name, _ in profile.expected_exact_values)
    if len(set(exact_names)) != len(exact_names):
        raise ValueError("expected_exact_values contains duplicate names")
    if exact_names != tuple(sorted(exact_names)):
        raise ValueError("expected_exact_values must be canonical")
    for name, values in profile.expected_exact_values:
        _text(name, "expected_exact_values name")
        if type(values) is not tuple or not values:
            raise ValueError("expected exact value sequences must be non-empty")
        if not all(type(value) is TaggedScalarWire for value in values):
            raise TypeError("expected exact values have the wrong wire type")
    label_names = tuple(name for name, _ in profile.expected_qualitative_labels)
    if len(set(label_names)) != len(label_names):
        raise ValueError("expected_qualitative_labels contains duplicate names")
    if label_names != tuple(sorted(label_names)):
        raise ValueError("expected_qualitative_labels must be canonical")
    for name, labels in profile.expected_qualitative_labels:
        _text(name, "expected_qualitative_labels name")
        _string_tuple(labels, f"expected_qualitative_labels[{name!r}]")
    expected_sha = canonical_sha(
        synthetic_application_prediction_profile_payload(profile)
    )
    if profile.prediction_profile_sha != expected_sha:
        raise ValueError(
            "prediction_profile_sha does not match complete prediction body"
        )


def verify_application_scenario_execution_spec(
    scenario: ApplicationScenarioExecutionSpec,
    operations: tuple[SyntheticApplicationOperation, ...],
) -> ApplicationScenarioExecutionSpec:
    """Verify one inert scenario against the exact enclosing operation DAG."""

    _require_exact_parent_schema(scenario, "application scenario")
    if type(scenario) is not ApplicationScenarioExecutionSpec:
        raise TypeError("scenario must be an ApplicationScenarioExecutionSpec")
    scenario.__post_init__()
    if type(operations) is not tuple or not operations:
        raise ValueError("operations must be a non-empty exact tuple")
    if not all(
        type(operation) is SyntheticApplicationOperation for operation in operations
    ):
        raise TypeError("operations has the wrong exact record type")
    known_ids = {operation.operation_instance_id for operation in operations}
    outputs = _string_tuple(
        scenario.operation_output_ids,
        "scenario.operation_output_ids",
    )
    missing = tuple(output for output in outputs if output not in known_ids)
    if missing:
        raise ValueError("scenario operation_output_ids references a missing operation")
    expected_sha = canonical_sha(application_scenario_execution_spec_payload(scenario))
    if scenario.scenario_sha != expected_sha:
        raise ValueError("scenario_sha does not match complete scenario body")
    return _clone_parent_wire(scenario)


def _serialized_size(payload: dict[str, object]) -> int:
    return _canonical_json_utf8_size(payload)


def verify_synthetic_control_application_spec(
    spec: V3M0SyntheticControlApplicationSpec,
) -> V3M0SyntheticControlApplicationSpec:
    """Verify one complete lazy application graph against frozen caps."""

    _require_exact_parent_schema(spec, "application")
    if type(spec) is not V3M0SyntheticControlApplicationSpec:
        raise TypeError("spec must be a V3M0SyntheticControlApplicationSpec")
    constants = spec.protocol_constant_payload
    _verify_protocol_constants(constants)
    if spec.control_case_id not in APPLICATION_CONTROL_CASE_IDS:
        raise ValueError("control_case_id is outside the closed C01-C20 registry")
    canonical_spec = _build_canonical_application_spec(spec.control_case_id)
    if spec.application_schema_version != APPLICATION_SPEC_SCHEMA_VERSION:
        raise ValueError("unexpected application_schema_version")
    _text(spec.application_instance_id, "application_instance_id")
    _text(spec.builder_id, "builder_id")

    operations = spec.operations
    if not operations:
        raise ValueError("operations must be non-empty")
    operation_count = len(operations)
    edge_count = sum(
        len(operation.input_operation_instance_ids) for operation in operations
    )
    parameter_count = sum(len(operation.parameters) for operation in operations)
    if operation_count > constants.max_operation_count:
        raise ValueError("operation count exceeds operation cap")
    if edge_count > constants.max_dependency_edge_count:
        raise ValueError("dependency edge count exceeds dependency edge cap")
    if parameter_count > constants.max_parameter_count:
        raise ValueError("parameter count exceeds parameter cap")
    spec_payload = synthetic_control_application_spec_payload(spec)
    if _serialized_size(spec_payload) > constants.max_serialized_bytes:
        raise ValueError("serialized application body exceeds serialized cap")

    _verify_basis_protocol(spec.basis_protocol)
    _verify_grid_protocol(spec.grid_protocol)
    _verify_readout_protocol(spec.readout_protocol)
    _verify_prediction_profile(
        spec.expected_prediction_profile,
        control_case_id=spec.control_case_id,
    )

    operation_ids: list[str] = []
    dependencies: dict[str, tuple[str, ...]] = {}
    for operation in operations:
        if type(operation) is not SyntheticApplicationOperation:
            raise TypeError("operations has the wrong record type")
        if operation.operation_schema_version != APPLICATION_OPERATION_SCHEMA_VERSION:
            raise ValueError("unexpected operation_schema_version")
        if operation.operation_kind not in _APPLICATION_OPERATION_KINDS:
            raise ValueError("operation_kind is outside the closed registry")
        expected_operation_sha = canonical_sha(
            synthetic_application_operation_payload(operation)
        )
        if operation.operation_sha != expected_operation_sha:
            raise ValueError("operation_sha does not match complete body")
        dependency_ids = _canonical_unique_strings(
            operation.input_operation_instance_ids,
            "input_operation_instance_ids",
            allow_empty=True,
        )
        parameter_names = tuple(name for name, _ in operation.parameters)
        if len(set(parameter_names)) != len(parameter_names):
            raise ValueError("parameters contains duplicate names")
        if parameter_names != tuple(sorted(parameter_names)):
            raise ValueError("parameters must be canonical")
        operation_ids.append(operation.operation_instance_id)
        dependencies[operation.operation_instance_id] = dependency_ids
    if len(set(operation_ids)) != len(operation_ids):
        raise ValueError("operations contains duplicate operation_instance_id")
    if tuple(operation_ids) != tuple(sorted(operation_ids)):
        raise ValueError("operations must be in canonical operation_instance_id order")
    known_ids = frozenset(operation_ids)
    for operation_id, dependency_ids in dependencies.items():
        missing = tuple(
            dependency for dependency in dependency_ids if dependency not in known_ids
        )
        if missing:
            raise ValueError(
                f"operation {operation_id!r} has missing dependency {missing[0]!r}"
            )

    outputs = _canonical_unique_strings(
        spec.output_operation_instance_ids,
        "output_operation_instance_ids",
    )
    if any(output not in known_ids for output in outputs):
        raise ValueError("output_operation_instance_ids references a missing operation")

    remaining = set(known_ids)
    while remaining:
        ready = tuple(
            operation_id
            for operation_id in sorted(remaining)
            if all(
                dependency not in remaining for dependency in dependencies[operation_id]
            )
        )
        if not ready:
            raise ValueError("application operation graph is cyclic, not acyclic")
        remaining.difference_update(ready)

    reachable: set[str] = set()
    stack = list(reversed(outputs))
    while stack:
        operation_id = stack.pop()
        if operation_id in reachable:
            continue
        reachable.add(operation_id)
        stack.extend(reversed(dependencies[operation_id]))
    if reachable != known_ids:
        raise ValueError(
            "application graph contains dead nodes not reachable from outputs"
        )

    scenarios = spec.scenario_execution_specs
    if type(scenarios) is not tuple or not scenarios:
        raise ValueError("scenario_execution_specs must be a non-empty tuple")
    scenario_ids: list[str] = []
    for scenario in scenarios:
        verified_scenario = verify_application_scenario_execution_spec(
            scenario,
            operations,
        )
        if not verified_scenario.scenario_id.startswith(
            f"{spec.application_instance_id}.scenario."
        ):
            raise ValueError("scenario_id is outside the application namespace")
        scenario_ids.append(verified_scenario.scenario_id)
    if len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("scenario_execution_specs contains duplicate scenario_id")

    stages = _string_tuple(
        spec.required_pipeline_stages,
        "required_pipeline_stages",
    )
    if len(set(stages)) != len(stages):
        raise ValueError("required_pipeline_stages contains duplicates")
    _text(
        spec.expected_prediction_profile_id,
        "expected_prediction_profile_id",
    )
    if (
        spec.expected_prediction_profile_id
        != spec.expected_prediction_profile.prediction_profile_id
    ):
        raise ValueError("expected_prediction_profile_id does not bind prediction body")
    _text(
        spec.expected_control_evidence_schema,
        "expected_control_evidence_schema",
    )
    expected_spec_sha = canonical_sha(spec_payload)
    if spec.application_spec_sha != expected_spec_sha:
        raise ValueError("application_spec_sha does not match complete body")
    dataclass_field_names = tuple(
        V3M0SyntheticControlApplicationSpec.__dataclass_fields__
    )
    if dataclass_field_names != _APPLICATION_SPEC_CANONICAL_FIELD_NAMES:
        raise RuntimeError("canonical application field registry is incomplete")
    for field_name in _APPLICATION_SPEC_CANONICAL_FIELD_NAMES:
        if getattr(spec, field_name) != getattr(canonical_spec, field_name):
            raise ValueError(
                f"{field_name} body/SHA does not match canonical "
                "control application spec"
            )
    return _clone_parent_wire(spec)


def _validate_parent_freeze_manifest(
    manifest: ParentFreezeManifest,
    *,
    require_closed_body: bool,
) -> ParentFreezeManifest:
    _require_exact_parent_schema(manifest, "parent freeze manifest")
    if type(manifest) is not ParentFreezeManifest:
        raise TypeError("manifest must be a ParentFreezeManifest")
    if manifest.parent_freeze_schema_version != PARENT_FREEZE_SCHEMA_VERSION:
        raise ValueError("unexpected parent_freeze_schema_version")
    if manifest.program_id != PROGRAM_ID:
        raise ValueError("unexpected program_id")
    if manifest.parent_v2_sha != PARENT_V2_SHA:
        raise ValueError("parent_v2_sha does not match the frozen parent")
    if manifest.task9_commit_sha != TASK9_COMMIT_SHA:
        raise ValueError("task9_commit_sha does not match the frozen Task 9")
    if manifest.taskbook_source_sha != TASKBOOK_SOURCE_SHA:
        raise ValueError("taskbook_source_sha does not match the frozen taskbook")
    if manifest.implementation_plan_source_sha != IMPLEMENTATION_PLAN_SOURCE_SHA:
        raise ValueError(
            "implementation_plan_source_sha does not match the frozen plan"
        )
    if manifest.erratum_source_sha != ERRATUM_SOURCE_SHA:
        raise ValueError("erratum_source_sha does not match the frozen erratum")
    _verify_protocol_constants(manifest.protocol_constant_payload)
    specs = manifest.synthetic_control_application_specs
    case_ids = tuple(spec.control_case_id for spec in specs)
    if case_ids != APPLICATION_CONTROL_CASE_IDS:
        raise ValueError("synthetic applications are not in fixed C01-C20 order")
    instance_ids: list[str] = []
    global_operation_ids: list[str] = []
    verified_specs = []
    for spec in specs:
        if spec.protocol_constant_payload != manifest.protocol_constant_payload:
            raise ValueError(
                "application protocol constants do not match parent constants"
            )
        verified = verify_synthetic_control_application_spec(spec)
        verified_specs.append(verified)
        instance_ids.append(verified.application_instance_id)
        global_operation_ids.extend(
            operation.operation_instance_id for operation in verified.operations
        )
    if len(set(instance_ids)) != len(instance_ids):
        raise ValueError("application_instance_id values must be globally unique")
    if len(set(global_operation_ids)) != len(global_operation_ids):
        raise ValueError("operation_instance_id values must be globally unique")
    if manifest.source_closure != _SOURCE_CLOSURE:
        raise ValueError("source_closure does not match the closed Task 9 source body")
    if tuple(path for path, _ in manifest.source_closure) != tuple(
        sorted(path for path, _ in manifest.source_closure)
    ):
        raise ValueError("source_closure must be in canonical path order")
    expected_sha = canonical_sha(parent_freeze_manifest_payload(manifest))
    if manifest.parent_freeze_sha != expected_sha:
        raise ValueError(
            "parent freeze manifest parent_freeze_sha does not match complete body"
        )
    snapshot = _clone_parent_wire(manifest)
    if require_closed_body and snapshot != _CLOSED_PARENT_FREEZE:
        raise ValueError("closed parent freeze body mismatch")
    return snapshot


def _float_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _bits_float(value: int) -> float:
    return struct.unpack(">d", struct.pack(">Q", value))[0]


def _fp64_wire(value: float) -> TaggedScalarWire:
    return TaggedScalarWire(
        "fp64-bits",
        None,
        _float_bits(value),
        None,
        None,
    )


def _integer_wire(value: int) -> TaggedScalarWire:
    return TaggedScalarWire("integer", value, None, None, None)


def _text_wire(value: str) -> TaggedScalarWire:
    return TaggedScalarWire("text", None, None, value, None)


def _build_constants() -> SyntheticApplicationProtocolConstants:
    provisional = SyntheticApplicationProtocolConstants(
        constants_schema_version=APPLICATION_CONSTANTS_SCHEMA_VERSION,
        tagged_constants=(
            (
                "amplitude-grey-control-fp64-bits",
                _fp64_wire(0.5),
            ),
            (
                "amplitude-null-control-fp64-bits",
                _fp64_wire(0.0),
            ),
            (
                "amplitude-null-upper-fp64-bits",
                _fp64_wire(0.25),
            ),
            (
                "amplitude-signal-control-fp64-bits",
                _fp64_wire(1.0),
            ),
            (
                "amplitude-signal-lower-fp64-bits",
                _fp64_wire(0.75),
            ),
            (
                "bridge-tolerance-fp64-bits",
                _fp64_wire(1.0e-12),
            ),
            (
                "c04-split-step-alpha-fp64-bits",
                TaggedScalarWire(
                    "fp64-bits",
                    None,
                    0xBFCD35CFF7CF27C0,
                    None,
                    None,
                ),
            ),
            (
                "c04-split-step-beta-fp64-bits",
                TaggedScalarWire(
                    "fp64-bits",
                    None,
                    0x3FF14AECC73EEB47,
                    None,
                    None,
                ),
            ),
            (
                "c04-split-step-residual-tolerance-fp64-bits",
                _fp64_wire(1.0e-15),
            ),
            (
                "c04-split-step-source-id",
                _text_wire("c04-two-mode-split-step-analytic-v1"),
            ),
            (
                "canonical-angle-high-squared-correlation-fp64-bits",
                _fp64_wire(0.75),
            ),
            (
                "canonical-angle-low-squared-correlation-fp64-bits",
                _fp64_wire(0.25),
            ),
            (
                "coverage-above-lower-fp64-bits",
                _fp64_wire(0.6),
            ),
            (
                "coverage-below-upper-fp64-bits",
                _fp64_wire(0.4),
            ),
            (
                "coverage-high-control-fp64-bits",
                _fp64_wire(0.75),
            ),
            (
                "coverage-low-control-fp64-bits",
                _fp64_wire(0.25),
            ),
            (
                "curvature-mode-count",
                _integer_wire(2),
            ),
            (
                "dm26-base-exponent",
                _integer_wire(2),
            ),
            (
                "dm26-floor-offset-fp64-bits",
                _fp64_wire(1.2e-4),
            ),
            (
                "dm26-high-order-4-coefficient-fp64-bits",
                _fp64_wire(-0.05),
            ),
            (
                "dm26-high-order-6-coefficient-fp64-bits",
                _fp64_wire(0.01),
            ),
            (
                "dm26-lattice-denominator-0",
                _integer_wire(16),
            ),
            (
                "dm26-lattice-denominator-1",
                _integer_wire(24),
            ),
            (
                "dm26-lattice-denominator-2",
                _integer_wire(32),
            ),
            (
                "dm26-lattice-denominator-3",
                _integer_wire(48),
            ),
            (
                "dm26-leading-coefficient-fp64-bits",
                _fp64_wire(0.236),
            ),
            (
                "dm26-series-source-id",
                _text_wire(DM26_DETERMINISTIC_CONTROL_SOURCE_ID),
            ),
            (
                "endpoint-extraction-protocol",
                _text_wire("endpoint-single-node-reference-v1"),
            ),
            (
                "phase-grid-denominator",
                _integer_wire(16),
            ),
            (
                "reference-phase-band-half-width-fp64-bits",
                _fp64_wire(1.0 / 8.0),
            ),
            (
                "reference-phase-band-source-id",
                _text_wire(APPLICATION_REFERENCE_PHASE_BAND_SOURCE_ID),
            ),
            (
                "reference-quarter-turn-phase-fp64-bits",
                _fp64_wire(math.pi / 2.0),
            ),
            (
                "survival-above-lower-fp64-bits",
                _fp64_wire(0.6),
            ),
            (
                "survival-below-upper-fp64-bits",
                _fp64_wire(0.4),
            ),
            (
                "unit-complex128-bits",
                TaggedScalarWire(
                    "complex128-bits",
                    None,
                    None,
                    None,
                    (_float_bits(1.0), _float_bits(0.0)),
                ),
            ),
        ),
        max_operation_count=4_096,
        max_dependency_edge_count=16_384,
        max_parameter_count=16_384,
        max_serialized_bytes=4_194_304,
        constants_sha="0" * 64,
    )
    return replace(
        provisional,
        constants_sha=canonical_sha(
            synthetic_application_protocol_constants_payload(provisional)
        ),
    )


def _build_basis_protocol() -> SyntheticApplicationBasisProtocol:
    channel_order = ("q0", "p0", "q1", "p1")
    source = build_basis_manifest(
        role="source",
        state_schema_id="state.v3m0.synthetic-control.v1",
        channel_order=channel_order,
        vectors=np.eye(4, dtype=np.complex128),
    )
    readout = build_basis_manifest(
        role="readout",
        state_schema_id="state.v3m0.synthetic-control.v1",
        channel_order=channel_order,
        vectors=np.eye(4, dtype=np.complex128),
    )
    provisional = SyntheticApplicationBasisProtocol(
        protocol_schema_version=APPLICATION_BASIS_PROTOCOL_SCHEMA_VERSION,
        source_basis=source,
        readout_basis=readout,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            synthetic_application_basis_protocol_payload(provisional)
        ),
    )


def _build_grid_protocol(
    constants: SyntheticApplicationProtocolConstants,
) -> SyntheticApplicationGridProtocol:
    phase_center = _constant_float(
        constants,
        "reference-quarter-turn-phase-fp64-bits",
    )
    half_width = _constant_float(
        constants,
        "reference-phase-band-half-width-fp64-bits",
    )
    source_wire = _constant_wire(
        constants,
        "reference-phase-band-source-id",
    )
    if (
        source_wire.value_kind != "text"
        or source_wire.text_value != APPLICATION_REFERENCE_PHASE_BAND_SOURCE_ID
    ):
        raise ValueError("reference phase-band source constant is not frozen")
    provisional = SyntheticApplicationGridProtocol(
        protocol_schema_version=APPLICATION_GRID_PROTOCOL_SCHEMA_VERSION,
        spatial_ndim=1,
        spatial_shape=(8,),
        response_torus_denominators=(8,),
        response_reciprocal_indices=((1,), (2,)),
        direction_ids=("positive-axis",),
        primitive_directions=((1,),),
        path_ids=("positive-axis-path",),
        ordered_paths=(((1,), (2,)),),
        closure_path_pairs=(),
        bridge_reciprocal_indices=((0,), (1,), (7,)),
        bridge_steps=(1, 2, 4),
        reference_reciprocal_index=(1,),
        preregistered_phase_bands=(
            (phase_center - half_width, phase_center + half_width),
        ),
        reference_phase_band_source_id=(APPLICATION_REFERENCE_PHASE_BAND_SOURCE_ID),
        expected_shell_rank=1,
        expected_shell_rank_source_id=EXPECTED_SHELL_RANK_SOURCE_ID,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            synthetic_application_grid_protocol_payload(provisional)
        ),
    )


def _build_readout_protocol() -> SyntheticApplicationReadoutProtocol:
    identity = freeze_complex_tensor(np.eye(4, dtype=np.complex128))
    provisional = SyntheticApplicationReadoutProtocol(
        protocol_schema_version=APPLICATION_READOUT_PROTOCOL_SCHEMA_VERSION,
        source_metric_whitener=identity,
        h_metric_whitener=identity,
        curvature_incidence_operator=identity,
        curvature_metric_whitener=identity,
        curvature_normalizer_id=CURVATURE_NORMALIZER_ID,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            synthetic_application_readout_protocol_payload(provisional)
        ),
    )


def _build_task8_anchor_basis_protocol(
    control_case_id: str,
) -> SyntheticApplicationBasisProtocol:
    if control_case_id in (
        "C01_BLIND_HOLDOUT_FULL",
        "C02_CONDITIONED_ZERO",
    ):
        channel_order = ("x.000", "y.000")
        source_vectors = np.asarray(((1.0, 0.0),), dtype=np.complex128)
        readout_vectors = np.asarray(((0.0, 1.0),), dtype=np.complex128)
    elif control_case_id == "C03_EQUAL_RANK_DIRECT_SUM":
        channel_order = (
            "x.b.000",
            "y.b.000",
            "x.c.001",
            "y.c.001",
        )
        source_vectors = np.asarray(
            (
                (1.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
            ),
            dtype=np.complex128,
        )
        readout_vectors = np.asarray(
            (
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            dtype=np.complex128,
        )
    else:
        raise ValueError("control_case_id is not a Task 8 window anchor")

    state_schema_id = "state.synthetic.local-linear.v1"
    source = build_basis_manifest(
        role="source",
        state_schema_id=state_schema_id,
        channel_order=channel_order,
        vectors=source_vectors,
    )
    readout = build_basis_manifest(
        role="readout",
        state_schema_id=state_schema_id,
        channel_order=channel_order,
        vectors=readout_vectors,
    )
    provisional = SyntheticApplicationBasisProtocol(
        protocol_schema_version=APPLICATION_BASIS_PROTOCOL_SCHEMA_VERSION,
        source_basis=source,
        readout_basis=readout,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            synthetic_application_basis_protocol_payload(provisional)
        ),
    )


def _build_task8_anchor_grid_protocol(
    control_case_id: str,
    constants: SyntheticApplicationProtocolConstants,
) -> SyntheticApplicationGridProtocol:
    expected_shell_rank = {
        "C01_BLIND_HOLDOUT_FULL": 1,
        "C02_CONDITIONED_ZERO": 1,
        "C03_EQUAL_RANK_DIRECT_SUM": 2,
    }.get(control_case_id)
    if expected_shell_rank is None:
        raise ValueError("control_case_id is not a Task 8 window anchor")
    provisional = replace(
        _build_grid_protocol(constants),
        expected_shell_rank=expected_shell_rank,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            synthetic_application_grid_protocol_payload(provisional)
        ),
    )


def _build_task8_anchor_readout_protocol(
    control_case_id: str,
) -> SyntheticApplicationReadoutProtocol:
    dimension = {
        "C01_BLIND_HOLDOUT_FULL": 1,
        "C02_CONDITIONED_ZERO": 1,
        "C03_EQUAL_RANK_DIRECT_SUM": 2,
    }.get(control_case_id)
    if dimension is None:
        raise ValueError("control_case_id is not a Task 8 window anchor")
    identity = freeze_complex_tensor(np.eye(dimension, dtype=np.complex128))
    provisional = SyntheticApplicationReadoutProtocol(
        protocol_schema_version=APPLICATION_READOUT_PROTOCOL_SCHEMA_VERSION,
        source_metric_whitener=identity,
        h_metric_whitener=identity,
        curvature_incidence_operator=identity,
        curvature_metric_whitener=identity,
        curvature_normalizer_id=CURVATURE_NORMALIZER_ID,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            synthetic_application_readout_protocol_payload(provisional)
        ),
    )


def _build_application_protocols(
    control_case_id: str,
    constants: SyntheticApplicationProtocolConstants,
) -> tuple[
    SyntheticApplicationBasisProtocol,
    SyntheticApplicationGridProtocol,
    SyntheticApplicationReadoutProtocol,
]:
    if control_case_id in APPLICATION_CONTROL_CASE_IDS[:3]:
        return (
            _build_task8_anchor_basis_protocol(control_case_id),
            _build_task8_anchor_grid_protocol(control_case_id, constants),
            _build_task8_anchor_readout_protocol(control_case_id),
        )
    return (
        _build_basis_protocol(),
        _build_grid_protocol(constants),
        _build_readout_protocol(),
    )


def _constant_wire(
    constants: SyntheticApplicationProtocolConstants,
    name: str,
) -> TaggedScalarWire:
    matches = tuple(
        value
        for constant_name, value in constants.tagged_constants
        if constant_name == name
    )
    if len(matches) != 1:
        raise ValueError(f"missing or duplicate frozen constant {name!r}")
    return matches[0]


def _constant_float(
    constants: SyntheticApplicationProtocolConstants,
    name: str,
) -> float:
    wire = _constant_wire(constants, name)
    if wire.value_kind != "fp64-bits" or wire.fp64_bits_value is None:
        raise TypeError(f"frozen constant {name!r} is not fp64-bits")
    return _bits_float(wire.fp64_bits_value)


def _constant_integer(
    constants: SyntheticApplicationProtocolConstants,
    name: str,
) -> int:
    wire = _constant_wire(constants, name)
    if wire.value_kind != "integer" or wire.integer_value is None:
        raise TypeError(f"frozen constant {name!r} is not an integer")
    return wire.integer_value


def _constant_text(
    constants: SyntheticApplicationProtocolConstants,
    name: str,
) -> str:
    wire = _constant_wire(constants, name)
    if wire.value_kind != "text" or wire.text_value is None:
        raise TypeError(f"frozen constant {name!r} is not text")
    return wire.text_value


def _build_dm26_deterministic_control_fixture(
    constants: SyntheticApplicationProtocolConstants,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    """Mechanically derive the exact Task 15 four-point DM26 control pair."""

    denominators = tuple(
        _constant_integer(constants, f"dm26-lattice-denominator-{index}")
        for index in range(4)
    )
    base_exponent = _constant_integer(constants, "dm26-base-exponent")
    leading = _constant_float(
        constants,
        "dm26-leading-coefficient-fp64-bits",
    )
    high_order_4 = _constant_float(
        constants,
        "dm26-high-order-4-coefficient-fp64-bits",
    )
    high_order_6 = _constant_float(
        constants,
        "dm26-high-order-6-coefficient-fp64-bits",
    )
    floor_offset = _constant_float(
        constants,
        "dm26-floor-offset-fp64-bits",
    )
    k_values = np.asarray(
        [2.0 * math.pi / denominator for denominator in denominators],
        dtype=np.float64,
    )
    clean = (
        leading * k_values**base_exponent
        + high_order_4 * k_values ** (base_exponent + 2)
        + high_order_6 * k_values ** (base_exponent + 4)
    ).astype(np.float64)
    floor = (clean + np.float64(floor_offset)).astype(np.float64)
    return (
        tuple(float(value) for value in k_values),
        tuple(float(value) for value in clean),
        tuple(float(value) for value in floor),
    )


def _make_operation(
    application_instance_id: str,
    local_id: str,
    operation_kind: ApplicationOperationKind,
    *,
    inputs: tuple[str, ...] = (),
    parameters: tuple[tuple[str, TaggedScalarWire], ...] = (),
) -> SyntheticApplicationOperation:
    operation = SyntheticApplicationOperation(
        operation_schema_version=APPLICATION_OPERATION_SCHEMA_VERSION,
        operation_instance_id=f"{application_instance_id}.{local_id}",
        operation_kind=operation_kind,
        input_operation_instance_ids=tuple(
            sorted(f"{application_instance_id}.{item}" for item in inputs)
        ),
        parameters=tuple(sorted(parameters, key=lambda entry: entry[0])),
        operation_sha="0" * 64,
    )
    return replace(
        operation,
        operation_sha=canonical_sha(synthetic_application_operation_payload(operation)),
    )


def _build_control_operation_graph(
    control_case_id: str,
    application_instance_id: str,
    constants: SyntheticApplicationProtocolConstants,
) -> tuple[
    tuple[SyntheticApplicationOperation, ...],
    tuple[str, ...],
]:
    """Build the closed, typed, replayable DAG for one synthetic control."""

    def op(
        local_id: str,
        kind: ApplicationOperationKind,
        inputs: tuple[str, ...] = (),
        parameters: tuple[tuple[str, TaggedScalarWire], ...] = (),
    ) -> SyntheticApplicationOperation:
        return _make_operation(
            application_instance_id,
            local_id,
            kind,
            inputs=inputs,
            parameters=parameters,
        )

    one = _fp64_wire(1.0)
    zero = _fp64_wire(0.0)
    two = _fp64_wire(2.0)
    operations: tuple[SyntheticApplicationOperation, ...]
    output_local_id: str

    if control_case_id == "C01_BLIND_HOLDOUT_FULL":
        operations = (
            op(
                "00-blind-response",
                "identity-v1",
                parameters=(
                    ("response-rank", _integer_wire(1)),
                    ("target-visibility", _text_wire("blind")),
                ),
            ),
            op(
                "01-actual-branch",
                "identity-v1",
                ("00-blind-response",),
                (("branch-role", _text_wire("actual")),),
            ),
            op(
                "02-ablated-branch",
                "identity-v1",
                ("00-blind-response",),
                (("branch-role", _text_wire("ablated")),),
            ),
            op(
                "03-holdout-span",
                "geometry-subspace-v1",
                ("01-actual-branch", "02-ablated-branch"),
                (
                    ("construction", _text_wire("holdout-span")),
                    ("target-rank", _integer_wire(1)),
                ),
            ),
        )
        output_local_id = "03-holdout-span"
    elif control_case_id == "C02_CONDITIONED_ZERO":
        operations = (
            op(
                "00-conditioned-actual",
                "identity-v1",
                parameters=(
                    ("response-rank", _integer_wire(1)),
                    ("target-visibility", _text_wire("conditioned")),
                ),
            ),
            op(
                "01-ablated-zero",
                "amplitude-rescale-v1",
                ("00-conditioned-actual",),
                (("amplitude-scale", zero),),
            ),
            op(
                "02-paired-output",
                "direct-sum-v1",
                ("00-conditioned-actual", "01-ablated-zero"),
                (("component-count", _integer_wire(2)),),
            ),
        )
        output_local_id = "02-paired-output"
    elif control_case_id == "C03_EQUAL_RANK_DIRECT_SUM":
        operations = (
            op(
                "00-rank-two-source",
                "identity-v1",
                parameters=(("response-rank", _integer_wire(2)),),
            ),
            op(
                "01-missing-half",
                "amplitude-rescale-v1",
                ("00-rank-two-source",),
                (("amplitude-scale", zero),),
            ),
            op(
                "02-surviving-half",
                "amplitude-rescale-v1",
                ("00-rank-two-source",),
                (("amplitude-scale", one),),
            ),
            op(
                "03-equal-rank-direct-sum",
                "direct-sum-v1",
                ("01-missing-half", "02-surviving-half"),
                (
                    ("left-rank", _integer_wire(1)),
                    ("right-rank", _integer_wire(1)),
                ),
            ),
        )
        output_local_id = "03-equal-rank-direct-sum"
    elif control_case_id == "C04_CANONICAL_ANGLE_025_075":
        operations = (
            op(
                "00-orthonormal-source",
                "identity-v1",
                parameters=(("response-rank", _integer_wire(2)),),
            ),
            op(
                "01-canonical-angle-pair",
                "canonical-shear-v1",
                ("00-orthonormal-source",),
                (
                    (
                        "survival-squared-correlation-0",
                        _constant_wire(
                            constants,
                            "canonical-angle-low-squared-correlation-fp64-bits",
                        ),
                    ),
                    (
                        "survival-squared-correlation-1",
                        _constant_wire(
                            constants,
                            "canonical-angle-high-squared-correlation-fp64-bits",
                        ),
                    ),
                ),
            ),
            op(
                "02-survival-readout",
                "geometry-subspace-v1",
                ("01-canonical-angle-pair",),
                (("readout", _text_wire("squared-canonical-correlation")),),
            ),
        )
        output_local_id = "02-survival-readout"
    elif control_case_id == "C05_PHASE_AND_SCALAR_GAIN":
        operations = (
            op(
                "00-reference-response",
                "identity-v1",
                parameters=(("response-rank", _integer_wire(2)),),
            ),
            op(
                "01-phase-flip",
                "phase-rotation-v1",
                ("00-reference-response",),
                (("phase-radians", _fp64_wire(math.pi)),),
            ),
            op(
                "02-scalar-gain",
                "amplitude-rescale-v1",
                ("00-reference-response",),
                (("amplitude-scale", two),),
            ),
            op(
                "03-auxiliary-pair",
                "direct-sum-v1",
                ("01-phase-flip", "02-scalar-gain"),
                (("component-count", _integer_wire(2)),),
            ),
        )
        output_local_id = "03-auxiliary-pair"
    elif control_case_id == "C06_INTERNAL_NONSCALE_MIXING":
        operations = (
            op(
                "00-source-frame",
                "identity-v1",
                parameters=(("source-rank", _integer_wire(2)),),
            ),
            op(
                "01-nonscalar-mix",
                "source-linear-mix-v1",
                ("00-source-frame",),
                (
                    ("matrix-00", _integer_wire(2)),
                    ("matrix-01", _integer_wire(1)),
                    ("matrix-10", _integer_wire(0)),
                    ("matrix-11", _integer_wire(1)),
                ),
            ),
        )
        output_local_id = "01-nonscalar-mix"
    elif control_case_id == "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE":
        operations = (
            op(
                "00-reference-wave",
                "identity-v1",
                parameters=(("response-rank", _integer_wire(1)),),
            ),
            op(
                "01-constructive",
                "phase-rotation-v1",
                ("00-reference-wave",),
                (("phase-radians", zero),),
            ),
            op(
                "02-destructive",
                "phase-rotation-v1",
                ("00-reference-wave",),
                (("phase-radians", _fp64_wire(math.pi)),),
            ),
            op(
                "03-interference-pair",
                "direct-sum-v1",
                ("01-constructive", "02-destructive"),
                (("combination", _text_wire("coherent-pair")),),
            ),
            op(
                "04-interference-combiner",
                "source-linear-mix-v1",
                ("03-interference-pair",),
                (
                    ("combiner-00", _integer_wire(1)),
                    ("combiner-01", _integer_wire(1)),
                    ("combiner-10", _integer_wire(1)),
                    ("combiner-11", _integer_wire(-1)),
                ),
            ),
        )
        output_local_id = "04-interference-combiner"
    elif control_case_id == "C08_RANK_R_MISSING_MODES":
        operations = (
            op(
                "00-rank-two-target",
                "identity-v1",
                parameters=(("target-rank", _integer_wire(2)),),
            ),
            op(
                "01-rank-one-deletion",
                "geometry-subspace-v1",
                ("00-rank-two-target",),
                (
                    ("missing-rank", _integer_wire(1)),
                    ("selection", _text_wire("target-conditioned")),
                ),
            ),
        )
        output_local_id = "01-rank-one-deletion"
    elif control_case_id == "C09_PURE_GAUGE_DRESSING":
        operations = (
            op(
                "00-curvature-response",
                "identity-v1",
                parameters=(("response-rank", _integer_wire(2)),),
            ),
            op(
                "01-pure-gauge-dressing",
                "canonical-shear-v1",
                ("00-curvature-response",),
                (
                    ("gauge-amplitude", _fp64_wire(8.0)),
                    ("gauge-sector", _text_wire("readout-nullspace")),
                ),
            ),
            op(
                "02-curvature-quotient",
                "geometry-subspace-v1",
                ("01-pure-gauge-dressing",),
                (("quotient", _text_wire("curvature")),),
            ),
        )
        output_local_id = "02-curvature-quotient"
    elif control_case_id == "C10_FULL_SOURCE_EXTRA_MODE":
        operations = (
            op(
                "00-actual-inactive-source",
                "amplitude-rescale-v1",
                parameters=(("amplitude-scale", zero),),
            ),
            op(
                "01-ablated-orthogonal-mode",
                "source-linear-mix-v1",
                ("00-actual-inactive-source",),
                (
                    ("new-source-axis", _integer_wire(1)),
                    ("orthogonal-amplitude", one),
                ),
            ),
            op(
                "02-full-source-extra-readout",
                "geometry-subspace-v1",
                ("00-actual-inactive-source", "01-ablated-orthogonal-mode"),
                (("source-domain", _text_wire("full")),),
            ),
        )
        output_local_id = "02-full-source-extra-readout"
    elif control_case_id == "C11_NULL_GREY_SIGNAL_AMPLITUDE":
        operations = (
            op(
                "00-unit-response",
                "identity-v1",
                parameters=(("response-rank", _integer_wire(1)),),
            ),
            op(
                "01-null-amplitude",
                "amplitude-rescale-v1",
                ("00-unit-response",),
                (
                    (
                        "amplitude-scale",
                        _constant_wire(
                            constants,
                            "amplitude-null-control-fp64-bits",
                        ),
                    ),
                ),
            ),
            op(
                "02-grey-amplitude",
                "amplitude-rescale-v1",
                ("00-unit-response",),
                (
                    (
                        "amplitude-scale",
                        _constant_wire(
                            constants,
                            "amplitude-grey-control-fp64-bits",
                        ),
                    ),
                ),
            ),
            op(
                "03-signal-amplitude",
                "amplitude-rescale-v1",
                ("00-unit-response",),
                (
                    (
                        "amplitude-scale",
                        _constant_wire(
                            constants,
                            "amplitude-signal-control-fp64-bits",
                        ),
                    ),
                ),
            ),
            op(
                "04-amplitude-regime-bundle",
                "direct-sum-v1",
                (
                    "01-null-amplitude",
                    "02-grey-amplitude",
                    "03-signal-amplitude",
                ),
                (("component-count", _integer_wire(3)),),
            ),
        )
        output_local_id = "04-amplitude-regime-bundle"
    elif control_case_id == "C12_NU_INC_IR_NORMALIZATION":
        operations = (
            op(
                "00-all-window-response",
                "identity-v1",
                parameters=(
                    ("direction-count", _integer_wire(1)),
                    ("window-count", _integer_wire(2)),
                ),
            ),
            op(
                "01-nu-inc-normalized",
                "geometry-subspace-v1",
                ("00-all-window-response",),
                (
                    (
                        "curvature-mode-count",
                        _integer_wire(
                            _constant_integer(
                                constants,
                                "curvature-mode-count",
                            )
                        ),
                    ),
                    ("normalizer", _text_wire("nu-inc")),
                    ("raw-noise-gates", _text_wire("absolute-and-relative")),
                ),
            ),
        )
        output_local_id = "01-nu-inc-normalized"
    elif control_case_id == "C13_BOTH_ZERO_UNDEFINED":
        operations = (
            op(
                "00-zero-seed",
                "identity-v1",
                parameters=(("response-rank", _integer_wire(1)),),
            ),
            op(
                "01-actual-zero",
                "amplitude-rescale-v1",
                ("00-zero-seed",),
                (("amplitude-scale", zero),),
            ),
            op(
                "02-ablated-zero",
                "amplitude-rescale-v1",
                ("00-zero-seed",),
                (("amplitude-scale", zero),),
            ),
            op(
                "03-zero-pair",
                "direct-sum-v1",
                ("01-actual-zero", "02-ablated-zero"),
                (("component-count", _integer_wire(2)),),
            ),
        )
        output_local_id = "03-zero-pair"
    elif control_case_id == "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL":
        operations = (
            op(
                "00-endpoint-ambiguous",
                "deterministic-series-v1",
                parameters=(
                    ("fault-mode", _text_wire("endpoint-shell-ambiguous")),
                    ("series-code", _text_wire("phase-band-empty")),
                ),
            ),
            op(
                "01-response-null",
                "deterministic-series-v1",
                parameters=(
                    ("fault-mode", _text_wire("response-null")),
                    ("series-code", _text_wire("actual-rank-zero")),
                ),
            ),
            op(
                "02-trace-unclassified",
                "deterministic-series-v1",
                parameters=(
                    ("fault-mode", _text_wire("trace-unclassified")),
                    ("series-code", _text_wire("unclassified")),
                ),
            ),
            op(
                "03-unstable",
                "deterministic-series-v1",
                parameters=(
                    ("fault-mode", _text_wire("unstable")),
                    ("series-code", _text_wire("spectral-radius-above-one")),
                ),
            ),
            op(
                "04-fault-bundle",
                "direct-sum-v1",
                (
                    "00-endpoint-ambiguous",
                    "01-response-null",
                    "02-trace-unclassified",
                    "03-unstable",
                ),
                (("component-count", _integer_wire(4)),),
            ),
        )
        output_local_id = "04-fault-bundle"
    elif control_case_id == "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY":
        operations = (
            op(
                "00-full-h",
                "geometry-subspace-v1",
                parameters=(
                    ("geometry-variant", _text_wire("full-h")),
                    ("physical-rank", _integer_wire(2)),
                ),
            ),
            op(
                "01-low-rank-tt",
                "geometry-subspace-v1",
                parameters=(
                    ("geometry-variant", _text_wire("low-rank-TT")),
                    ("physical-rank", _integer_wire(1)),
                ),
            ),
            op(
                "02-tt",
                "geometry-subspace-v1",
                parameters=(
                    ("geometry-variant", _text_wire("TT")),
                    ("physical-rank", _integer_wire(2)),
                ),
            ),
            op(
                "03-tt-plus-row",
                "geometry-subspace-v1",
                parameters=(
                    ("geometry-variant", _text_wire("TT⊕row")),
                    ("physical-rank", _integer_wire(2)),
                    ("row-rank", _integer_wire(1)),
                ),
            ),
            op(
                "04-geometry-bundle",
                "direct-sum-v1",
                ("00-full-h", "01-low-rank-tt", "02-tt", "03-tt-plus-row"),
                (
                    (
                        "frozen-spectrum-length",
                        _integer_wire(
                            _constant_integer(
                                constants,
                                "curvature-mode-count",
                            )
                        ),
                    ),
                ),
            ),
        )
        output_local_id = "04-geometry-bundle"
    elif control_case_id == "C16_COVERAGE_025_075":
        operations = (
            op(
                "00-coverage-low",
                "coverage-subspace-v1",
                parameters=(
                    (
                        "coverage-squared-correlation",
                        _constant_wire(
                            constants,
                            "coverage-low-control-fp64-bits",
                        ),
                    ),
                ),
            ),
            op(
                "01-coverage-high",
                "coverage-subspace-v1",
                parameters=(
                    (
                        "coverage-squared-correlation",
                        _constant_wire(
                            constants,
                            "coverage-high-control-fp64-bits",
                        ),
                    ),
                ),
            ),
            op(
                "02-coverage-pair",
                "direct-sum-v1",
                ("00-coverage-low", "01-coverage-high"),
                (("component-count", _integer_wire(2)),),
            ),
        )
        output_local_id = "02-coverage-pair"
    elif control_case_id == "C17_QUOTIENT_GAUGE_COVERAGE":
        operations = (
            op(
                "00-physical-target",
                "coverage-subspace-v1",
                parameters=(("quotient", _text_wire("curvature")),),
            ),
            op(
                "01-gauge-dressing",
                "canonical-shear-v1",
                ("00-physical-target",),
                (
                    ("gauge-amplitude", _fp64_wire(8.0)),
                    ("gauge-sector", _text_wire("readout-nullspace")),
                ),
            ),
            op(
                "02-dressed-quotient",
                "coverage-subspace-v1",
                ("00-physical-target", "01-gauge-dressing"),
                (("quotient", _text_wire("curvature")),),
            ),
        )
        output_local_id = "02-dressed-quotient"
    elif control_case_id == "C18_ABLATED_INDEPENDENT_UNARY":
        operations = (
            op(
                "00-actual-source-domain",
                "identity-v1",
                parameters=(("source-axis", _integer_wire(0)),),
            ),
            op(
                "01-ablated-new-source-axis",
                "source-linear-mix-v1",
                ("00-actual-source-domain",),
                (
                    ("independent-source-axis", _integer_wire(1)),
                    ("new-axis-amplitude", one),
                ),
            ),
            op(
                "02-unary-geometry-sigma",
                "geometry-subspace-v1",
                ("00-actual-source-domain", "01-ablated-new-source-axis"),
                (("observer", _text_wire("geometry-and-sigma")),),
            ),
        )
        output_local_id = "02-unary-geometry-sigma"
    elif control_case_id == "C19_FULL_POSITIVE_OBSERVER_COLLAPSE":
        operations = (
            op(
                "00-full-positive-h",
                "identity-v1",
                parameters=(
                    ("frequency-sector", _text_wire("positive-full")),
                    ("h-rank", _integer_wire(2)),
                ),
            ),
            op(
                "01-observer-collapse-check",
                "geometry-subspace-v1",
                ("00-full-positive-h",),
                (("certificate", _text_wire("observer-collapse")),),
            ),
        )
        output_local_id = "01-observer-collapse-check"
    elif control_case_id == "C20_DM26_CLEAN_ZERO_TRUE_FLOOR":
        k_values, clean_samples, floor_samples = (
            _build_dm26_deterministic_control_fixture(constants)
        )

        def series_parameters(
            series_class: str,
            samples: tuple[float, ...],
        ) -> tuple[tuple[str, TaggedScalarWire], ...]:
            return (
                *tuple(
                    (f"k-{index}", _fp64_wire(value))
                    for index, value in enumerate(k_values)
                ),
                *tuple(
                    (f"sample-{index}", _fp64_wire(value))
                    for index, value in enumerate(samples)
                ),
                ("series-class", _text_wire(series_class)),
            )

        operations = (
            op(
                "00-clean-zero-series",
                "deterministic-series-v1",
                parameters=series_parameters(
                    "clean-zero",
                    clean_samples,
                ),
            ),
            op(
                "01-true-floor-series",
                "deterministic-series-v1",
                parameters=series_parameters(
                    "true-floor",
                    floor_samples,
                ),
            ),
            op(
                "02-dm26-pair",
                "direct-sum-v1",
                ("00-clean-zero-series", "01-true-floor-series"),
                (("decision-rule", _text_wire("D-M2-6")),),
            ),
        )
        output_local_id = "02-dm26-pair"
    else:
        raise ValueError("control_case_id is outside the closed C01-C20 registry")

    canonical_operations = tuple(
        sorted(operations, key=lambda operation: operation.operation_instance_id)
    )
    return (
        canonical_operations,
        (f"{application_instance_id}.{output_local_id}",),
    )


def _make_scenario_execution_spec(
    application_instance_id: str,
    *,
    slug: str,
    output_local_id: str,
    execution_lane: ApplicationExecutionLane,
    execution_recipe_id: str,
    recipe_parameter_wires: tuple[tuple[str, TaggedScalarWire], ...] = (),
    recipe_derivation_source_id: str = "parent-frozen-operation-dag-v1",
    expected_terminal_stage: Optional[ApplicationTerminalStage] = None,
    expected_undefined_reason: Optional[UndefinedReason] = None,
) -> ApplicationScenarioExecutionSpec:
    artifact_type = {
        "BLOCK_SUCCESS": "VerifiedResponseBlock",
        "EXPECTED_TYPED_TERMINATION": ("VerifiedResponseBlockAttemptOutcome"),
        "ANALYSIS_CONTROL": "VerifiedDeterministicSeriesControlOutcome",
    }[execution_lane]
    provisional = ApplicationScenarioExecutionSpec(
        scenario_schema_version=APPLICATION_SCENARIO_SCHEMA_VERSION,
        scenario_id=f"{application_instance_id}.scenario.{slug}.v1",
        operation_output_ids=(f"{application_instance_id}.{output_local_id}",),
        execution_lane=execution_lane,
        execution_recipe_id=execution_recipe_id,
        recipe_parameter_wires=recipe_parameter_wires,
        recipe_derivation_source_id=recipe_derivation_source_id,
        expected_terminal_stage=expected_terminal_stage,
        expected_undefined_reason=expected_undefined_reason,
        expected_artifact_type=artifact_type,
        scenario_sha="0" * 64,
    )
    return replace(
        provisional,
        scenario_sha=canonical_sha(
            application_scenario_execution_spec_payload(provisional)
        ),
    )


def _build_scenario_execution_specs(
    control_case_id: str,
    application_instance_id: str,
    constants: SyntheticApplicationProtocolConstants,
) -> tuple[ApplicationScenarioExecutionSpec, ...]:
    """Freeze the ordered terminal lane and execution recipe for every case."""

    def block(
        slug: str,
        output: str,
        recipe: str,
        *,
        parameters: tuple[tuple[str, TaggedScalarWire], ...] = (),
        source: str = "parent-frozen-operation-dag-v1",
    ) -> ApplicationScenarioExecutionSpec:
        return _make_scenario_execution_spec(
            application_instance_id,
            slug=slug,
            output_local_id=output,
            execution_lane="BLOCK_SUCCESS",
            execution_recipe_id=recipe,
            recipe_parameter_wires=parameters,
            recipe_derivation_source_id=source,
            expected_terminal_stage="success",
        )

    def terminate(
        slug: str,
        output: str,
        recipe: str,
        stage: ApplicationTerminalStage,
        reason: UndefinedReason,
    ) -> ApplicationScenarioExecutionSpec:
        return _make_scenario_execution_spec(
            application_instance_id,
            slug=slug,
            output_local_id=output,
            execution_lane="EXPECTED_TYPED_TERMINATION",
            execution_recipe_id=recipe,
            expected_terminal_stage=stage,
            expected_undefined_reason=reason,
        )

    def analysis(
        slug: str,
        output: str,
        recipe: str,
        *,
        parameters: tuple[tuple[str, TaggedScalarWire], ...] = (),
        source: str = "parent-frozen-operation-dag-v1",
    ) -> ApplicationScenarioExecutionSpec:
        return _make_scenario_execution_spec(
            application_instance_id,
            slug=slug,
            output_local_id=output,
            execution_lane="ANALYSIS_CONTROL",
            execution_recipe_id=recipe,
            recipe_parameter_wires=parameters,
            recipe_derivation_source_id=source,
        )

    if control_case_id == "C01_BLIND_HOLDOUT_FULL":
        return (
            block(
                "holdout-span",
                "03-holdout-span",
                "task8-blind-holdout-v1",
            ),
        )
    if control_case_id == "C02_CONDITIONED_ZERO":
        return (
            block(
                "conditioned-zero",
                "02-paired-output",
                "task8-conditioned-zero-v1",
            ),
        )
    if control_case_id == "C03_EQUAL_RANK_DIRECT_SUM":
        return (
            block(
                "equal-rank-direct-sum",
                "03-equal-rank-direct-sum",
                "task8-equal-rank-direct-sum-v1",
            ),
        )
    if control_case_id == "C04_CANONICAL_ANGLE_025_075":
        source_wire = _constant_wire(constants, "c04-split-step-source-id")
        if source_wire.value_kind != "text" or source_wire.text_value is None:
            raise ValueError("C04 recipe source constant is not text")
        return (
            block(
                "canonical-angle",
                "02-survival-readout",
                "two-mode-split-step-canonical-angle-v1",
                parameters=(
                    (
                        "alpha",
                        _constant_wire(
                            constants,
                            "c04-split-step-alpha-fp64-bits",
                        ),
                    ),
                    (
                        "analytic-residual-tolerance",
                        _constant_wire(
                            constants,
                            ("c04-split-step-residual-tolerance-fp64-bits"),
                        ),
                    ),
                    (
                        "beta",
                        _constant_wire(
                            constants,
                            "c04-split-step-beta-fp64-bits",
                        ),
                    ),
                ),
                source=source_wire.text_value,
            ),
        )
    if control_case_id == "C05_PHASE_AND_SCALAR_GAIN":
        return (
            block("phase", "01-phase-flip", "two-mode-phase-rotation-v1"),
            block("gain", "02-scalar-gain", "two-mode-scalar-gain-v1"),
        )
    if control_case_id == "C06_INTERNAL_NONSCALE_MIXING":
        return (
            block(
                "nonscale-mixing",
                "01-nonscalar-mix",
                "two-mode-source-linear-mix-v1",
            ),
        )
    if control_case_id == "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE":
        return (
            block(
                "interference",
                "04-interference-combiner",
                "two-mode-coherent-interference-v1",
            ),
        )
    if control_case_id == "C08_RANK_R_MISSING_MODES":
        return (
            block(
                "rank-missing",
                "01-rank-one-deletion",
                "two-mode-rank-deletion-v1",
            ),
        )
    if control_case_id == "C09_PURE_GAUGE_DRESSING":
        return (
            block(
                "gauge-dressing",
                "02-curvature-quotient",
                "two-mode-pure-gauge-dressing-v1",
            ),
        )
    if control_case_id == "C10_FULL_SOURCE_EXTRA_MODE":
        return (
            block(
                "extra-mode",
                "02-full-source-extra-readout",
                "two-mode-full-source-extra-mode-v1",
            ),
        )
    if control_case_id == "C11_NULL_GREY_SIGNAL_AMPLITUDE":
        recipe = "two-mode-amplitude-activation-v1"
        return (
            terminate(
                "null",
                "01-null-amplitude",
                recipe,
                "activation",
                UndefinedReason.RESPONSE_NULL,
            ),
            terminate(
                "grey",
                "02-grey-amplitude",
                recipe,
                "activation",
                UndefinedReason.RESPONSE_GREY,
            ),
            block("signal", "03-signal-amplitude", recipe),
        )
    if control_case_id == "C12_NU_INC_IR_NORMALIZATION":
        return (
            block(
                "ir-normalization",
                "01-nu-inc-normalized",
                "two-mode-ir-normalization-v1",
            ),
        )
    if control_case_id == "C13_BOTH_ZERO_UNDEFINED":
        return (
            terminate(
                "both-zero",
                "03-zero-pair",
                "two-mode-both-zero-v1",
                "activation",
                UndefinedReason.RESPONSE_NULL,
            ),
        )
    if control_case_id == "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL":
        return (
            terminate(
                "endpoint-ambiguous",
                "00-endpoint-ambiguous",
                "endpoint-shell-fault-injection-v1",
                "endpoint_shell",
                UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS,
            ),
            terminate(
                "response-null",
                "01-response-null",
                "response-null-fault-injection-v1",
                "activation",
                UndefinedReason.RESPONSE_NULL,
            ),
            terminate(
                "trace-unclassified",
                "02-trace-unclassified",
                "trace-unclassified-fault-injection-v1",
                "trace",
                UndefinedReason.TRACE_UNCLASSIFIED,
            ),
            terminate(
                "unstable",
                "03-unstable",
                "unstable-fault-injection-v1",
                "stability",
                UndefinedReason.UNSTABLE,
            ),
        )
    if control_case_id == "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY":
        return (
            block("full-h", "00-full-h", "geometry-full-h-v1"),
            block(
                "low-rank-tt",
                "01-low-rank-tt",
                "geometry-low-rank-tt-v1",
            ),
            block("tt", "02-tt", "geometry-tt-v1"),
            block(
                "tt-plus-row",
                "03-tt-plus-row",
                "geometry-tt-plus-row-v1",
            ),
        )
    if control_case_id == "C16_COVERAGE_025_075":
        recipe = "coverage-canonical-angle-v1"
        return (
            block("coverage-low", "00-coverage-low", recipe),
            block("coverage-high", "01-coverage-high", recipe),
        )
    if control_case_id == "C17_QUOTIENT_GAUGE_COVERAGE":
        return (
            block(
                "quotient-gauge",
                "02-dressed-quotient",
                "quotient-gauge-coverage-v1",
            ),
        )
    if control_case_id == "C18_ABLATED_INDEPENDENT_UNARY":
        return (
            block(
                "independent-unary",
                "02-unary-geometry-sigma",
                "ablated-independent-unary-v1",
            ),
        )
    if control_case_id == "C19_FULL_POSITIVE_OBSERVER_COLLAPSE":
        return (
            block(
                "observer-collapse",
                "01-observer-collapse-check",
                "full-positive-observer-collapse-v1",
            ),
        )
    if control_case_id == "C20_DM26_CLEAN_ZERO_TRUE_FLOOR":
        recipe = "deterministic-series-dm26-v1"
        source = _constant_text(constants, "dm26-series-source-id")
        k_values, clean_samples, floor_samples = (
            _build_dm26_deterministic_control_fixture(constants)
        )

        def scenario_parameters(
            samples: tuple[float, ...],
            *,
            expected_both_pollution: bool,
        ) -> tuple[tuple[str, TaggedScalarWire], ...]:
            return (
                (
                    "expected-both-pollution",
                    _integer_wire(1 if expected_both_pollution else 0),
                ),
                *tuple(
                    (f"k-{index}", _fp64_wire(value))
                    for index, value in enumerate(k_values)
                ),
                *tuple(
                    (f"sample-{index}", _fp64_wire(value))
                    for index, value in enumerate(samples)
                ),
            )

        return (
            analysis(
                "clean-zero",
                "00-clean-zero-series",
                recipe,
                parameters=scenario_parameters(
                    clean_samples,
                    expected_both_pollution=True,
                ),
                source=source,
            ),
            analysis(
                "true-floor",
                "01-true-floor-series",
                recipe,
                parameters=scenario_parameters(
                    floor_samples,
                    expected_both_pollution=False,
                ),
                source=source,
            ),
        )
    raise ValueError("control_case_id is outside the closed C01-C20 registry")


def _side_label(
    value: float,
    *,
    below_upper: float,
    above_lower: float,
) -> str:
    if value < below_upper:
        return "below"
    if value > above_lower:
        return "above"
    return "grey"


def _amplitude_regime(
    value: float,
    *,
    null_upper: float,
    signal_lower: float,
) -> str:
    if value < null_upper:
        return "null"
    if value > signal_lower:
        return "signal"
    return "grey"


def _make_prediction_profile(
    control_case_id: str,
    *,
    exact_values: dict[str, tuple[TaggedScalarWire, ...]],
    qualitative_labels: dict[str, tuple[str, ...]],
) -> SyntheticApplicationPredictionProfile:
    ordinal = APPLICATION_CONTROL_CASE_IDS.index(control_case_id) + 1
    provisional = SyntheticApplicationPredictionProfile(
        prediction_schema_version=(APPLICATION_PREDICTION_PROFILE_SCHEMA_VERSION),
        prediction_profile_id=(f"v3m0.synthetic-prediction.c{ordinal:02d}.v1"),
        control_case_id=control_case_id,
        expected_exact_values=tuple(sorted(exact_values.items())),
        expected_qualitative_labels=tuple(sorted(qualitative_labels.items())),
        prediction_profile_sha="0" * 64,
    )
    return replace(
        provisional,
        prediction_profile_sha=canonical_sha(
            synthetic_application_prediction_profile_payload(provisional)
        ),
    )


def _build_prediction_profile(
    control_case_id: str,
    constants: SyntheticApplicationProtocolConstants,
) -> SyntheticApplicationPredictionProfile:
    """Derive expected values and labels from the frozen control constants."""

    def fp(*values: float) -> tuple[TaggedScalarWire, ...]:
        return tuple(_fp64_wire(value) for value in values)

    def integer(*values: int) -> tuple[TaggedScalarWire, ...]:
        return tuple(_integer_wire(value) for value in values)

    exact: dict[str, tuple[TaggedScalarWire, ...]]
    labels: dict[str, tuple[str, ...]]

    if control_case_id == "C01_BLIND_HOLDOUT_FULL":
        exact = {
            "causal-epsilon": fp(1.0),
            "geometry-delta": fp(0.0),
            "survival-spectrum": fp(1.0),
        }
        labels = {"target-construction": ("blind-holdout",)}
    elif control_case_id == "C02_CONDITIONED_ZERO":
        exact = {
            "causal-epsilon": fp(0.0),
            "geometry-delta": fp(0.0),
            "survival-spectrum": fp(0.0),
        }
        labels = {"target-construction": ("conditioned",)}
    elif control_case_id == "C03_EQUAL_RANK_DIRECT_SUM":
        exact = {
            "causal-epsilon": fp(0.5),
            "survival-spectrum": fp(0.0, 1.0),
        }
        labels = {"rank-partition": ("equal", "equal")}
    elif control_case_id == "C04_CANONICAL_ANGLE_025_075":
        values = (
            _constant_float(
                constants,
                "canonical-angle-low-squared-correlation-fp64-bits",
            ),
            _constant_float(
                constants,
                "canonical-angle-high-squared-correlation-fp64-bits",
            ),
        )
        below_upper = _constant_float(
            constants,
            "survival-below-upper-fp64-bits",
        )
        above_lower = _constant_float(
            constants,
            "survival-above-lower-fp64-bits",
        )
        exact = {"survival-spectrum": fp(*values)}
        labels = {
            "survival-side": tuple(
                _side_label(
                    value,
                    below_upper=below_upper,
                    above_lower=above_lower,
                )
                for value in values
            )
        }
    elif control_case_id == "C05_PHASE_AND_SCALAR_GAIN":
        exact = {
            "map-congruence": fp(1.0, 1.0),
            "survival-spectrum": fp(1.0, 1.0),
        }
        labels = {"auxiliary-change": ("phase", "scalar-gain")}
    elif control_case_id == "C06_INTERNAL_NONSCALE_MIXING":
        exact = {"survival-spectrum": fp(1.0, 1.0)}
        labels = {"map-congruence": ("strictly-below-one",)}
    elif control_case_id == "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE":
        exact = {
            "chi-extra": fp(0.0, 1.0),
            "procrustes-residual": fp(0.0, 1.0),
            "survival-spectrum": fp(1.0, 0.0),
        }
        labels = {"interference-order": ("constructive", "destructive")}
    elif control_case_id == "C08_RANK_R_MISSING_MODES":
        exact = {
            "missing-rank": integer(1),
            "survival-spectrum": fp(0.0, 1.0),
        }
        labels = {"zero-count": ("equals-missing-rank",)}
    elif control_case_id == "C09_PURE_GAUGE_DRESSING":
        exact = {
            "survival-after-dressing": fp(1.0, 1.0),
            "survival-before-dressing": fp(1.0, 1.0),
        }
        labels = {"curvature-spectrum": ("gauge-invariant",)}
    elif control_case_id == "C10_FULL_SOURCE_EXTRA_MODE":
        exact = {"chi-extra": fp(1.0)}
        labels = {"new-orthogonal-mode": ("detected-by-full-source-readout",)}
    elif control_case_id == "C11_NULL_GREY_SIGNAL_AMPLITUDE":
        amplitudes = (
            _constant_float(
                constants,
                "amplitude-null-control-fp64-bits",
            ),
            _constant_float(
                constants,
                "amplitude-grey-control-fp64-bits",
            ),
            _constant_float(
                constants,
                "amplitude-signal-control-fp64-bits",
            ),
        )
        null_upper = _constant_float(
            constants,
            "amplitude-null-upper-fp64-bits",
        )
        signal_lower = _constant_float(
            constants,
            "amplitude-signal-lower-fp64-bits",
        )
        regimes = tuple(
            _amplitude_regime(
                value,
                null_upper=null_upper,
                signal_lower=signal_lower,
            )
            for value in amplitudes
        )
        coordinate_by_regime = {
            "null": _fp64_wire(0.0),
            "grey": _text_wire("undefined"),
            "signal": _fp64_wire(1.0),
        }
        exact = {
            "causal-coordinate": tuple(
                coordinate_by_regime[regime] for regime in regimes
            ),
            "input-amplitude": fp(*amplitudes),
        }
        labels = {"amplitude-regime": regimes}
    elif control_case_id == "C12_NU_INC_IR_NORMALIZATION":
        mode_count = _constant_integer(constants, "curvature-mode-count")
        exact = {
            "curvature-mode-count-by-window": integer(
                mode_count,
                mode_count,
            )
        }
        labels = {
            "raw-noise-gates": (
                "absolute-gate-not-bypassed",
                "relative-gate-not-bypassed",
            )
        }
    elif control_case_id == "C13_BOTH_ZERO_UNDEFINED":
        exact = {
            "ablated-response-norm": fp(0.0),
            "actual-response-norm": fp(0.0),
        }
        labels = {
            "coordinate-status": (
                "causal-undefined",
                "geometry-undefined",
                "sigma-undefined",
            )
        }
    elif control_case_id == "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL":
        exact = {}
        labels = {
            "fault-outcome": (
                "UNSTABLE",
                "TRACE_UNCLASSIFIED",
                "ENDPOINT_SHELL_AMBIGUOUS",
                "RESPONSE_NULL",
            ),
            "coordinate-status": (
                "causal-undefined",
                "causal-undefined",
                "all-undefined",
                "all-undefined",
            ),
        }
    elif control_case_id == "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY":
        exact = {
            "g-spectrum.full-h": fp(1.0, 1.0),
            "g-spectrum.low-rank-tt": fp(0.0, 1.0),
            "g-spectrum.tt": fp(1.0, 1.0),
            "g-spectrum.tt-plus-row": fp(1.0, 1.0),
        }
        labels = {
            "geometry-variant": (
                "full-h",
                "low-rank-tt",
                "tt",
                "tt-plus-row",
            )
        }
    elif control_case_id == "C16_COVERAGE_025_075":
        values = (
            _constant_float(constants, "coverage-low-control-fp64-bits"),
            _constant_float(constants, "coverage-high-control-fp64-bits"),
        )
        below_upper = _constant_float(
            constants,
            "coverage-below-upper-fp64-bits",
        )
        above_lower = _constant_float(
            constants,
            "coverage-above-lower-fp64-bits",
        )
        exact = {"coverage-spectrum": fp(*values)}
        labels = {
            "coverage-side": tuple(
                _side_label(
                    value,
                    below_upper=below_upper,
                    above_lower=above_lower,
                )
                for value in values
            ),
            "grey-policy": ("neither-below-nor-above",),
        }
    elif control_case_id == "C17_QUOTIENT_GAUGE_COVERAGE":
        values = (
            _constant_float(constants, "coverage-low-control-fp64-bits"),
            _constant_float(constants, "coverage-high-control-fp64-bits"),
        )
        exact = {
            "coverage-after-dressing": fp(*values),
            "coverage-before-dressing": fp(*values),
        }
        labels = {"quotient-coverage": ("gauge-invariant",)}
    elif control_case_id == "C18_ABLATED_INDEPENDENT_UNARY":
        exact = {}
        labels = {
            "independent-source-direction": (
                "detected-by-geometry",
                "detected-by-sigma",
            )
        }
    elif control_case_id == "C19_FULL_POSITIVE_OBSERVER_COLLAPSE":
        exact = {"full-positive-h-rank": integer(2)}
        labels = {"observer-collapse": ("triggered",)}
    elif control_case_id == "C20_DM26_CLEAN_ZERO_TRUE_FLOOR":
        k_values, clean_samples, floor_samples = (
            _build_dm26_deterministic_control_fixture(constants)
        )
        exact = {
            "clean-zero-series": fp(*clean_samples),
            "dm26-both-pollution": integer(1, 0),
            "dm26-k-values": fp(*k_values),
            "true-floor-series": fp(*floor_samples),
        }
        labels = {
            "D-M2-6-decision": (
                "clean-zero-excluded",
                "true-floor-retained",
            )
        }
    else:
        raise ValueError("control_case_id is outside the closed C01-C20 registry")

    return _make_prediction_profile(
        control_case_id,
        exact_values=exact,
        qualitative_labels=labels,
    )


def _assemble_canonical_application_spec(
    control_case_id: str,
    constants: SyntheticApplicationProtocolConstants,
    basis_protocol: SyntheticApplicationBasisProtocol,
    grid_protocol: SyntheticApplicationGridProtocol,
    readout_protocol: SyntheticApplicationReadoutProtocol,
) -> V3M0SyntheticControlApplicationSpec:
    if control_case_id not in APPLICATION_CONTROL_CASE_IDS:
        raise ValueError("control_case_id is outside the closed C01-C20 registry")
    ordinal = APPLICATION_CONTROL_CASE_IDS.index(control_case_id) + 1
    application_instance_id = f"v3m0.synthetic-control.c{ordinal:02d}.v1"
    operations, outputs = _build_control_operation_graph(
        control_case_id,
        application_instance_id,
        constants,
    )
    scenarios = _build_scenario_execution_specs(
        control_case_id,
        application_instance_id,
        constants,
    )
    prediction_profile = _build_prediction_profile(
        control_case_id,
        constants,
    )
    stages = (
        "construction",
        "matched-ablation",
        "dynamics",
        "endpoint-shell",
        "paired-response",
        ("window-calibration" if ordinal <= 3 else "control-application-evidence"),
    )
    provisional = V3M0SyntheticControlApplicationSpec(
        application_schema_version=APPLICATION_SPEC_SCHEMA_VERSION,
        control_case_id=control_case_id,
        application_instance_id=application_instance_id,
        builder_id=f"v3m0.synthetic-control-builder.c{ordinal:02d}.v1",
        basis_protocol=basis_protocol,
        grid_protocol=grid_protocol,
        readout_protocol=readout_protocol,
        protocol_constant_payload=constants,
        operations=operations,
        output_operation_instance_ids=outputs,
        scenario_execution_specs=scenarios,
        required_pipeline_stages=stages,
        expected_prediction_profile_id=(prediction_profile.prediction_profile_id),
        expected_prediction_profile=prediction_profile,
        expected_control_evidence_schema=(
            "v3m0.window-control-evidence.v1"
            if ordinal <= 3
            else "v3m0.control-application-evidence.v1"
        ),
        application_spec_sha="0" * 64,
    )
    return replace(
        provisional,
        application_spec_sha=canonical_sha(
            synthetic_control_application_spec_payload(provisional)
        ),
    )


def _build_canonical_application_spec(
    control_case_id: str,
) -> V3M0SyntheticControlApplicationSpec:
    """Rebuild one complete spec solely from its closed case ordinal."""

    constants = _build_constants()
    basis_protocol, grid_protocol, readout_protocol = _build_application_protocols(
        control_case_id,
        constants,
    )
    return _assemble_canonical_application_spec(
        control_case_id,
        constants,
        basis_protocol,
        grid_protocol,
        readout_protocol,
    )


def _build_application_specs(
    constants: SyntheticApplicationProtocolConstants,
) -> tuple[V3M0SyntheticControlApplicationSpec, ...]:
    specs: list[V3M0SyntheticControlApplicationSpec] = []
    for control_case_id in APPLICATION_CONTROL_CASE_IDS:
        basis_protocol, grid_protocol, readout_protocol = _build_application_protocols(
            control_case_id,
            constants,
        )
        specs.append(
            _assemble_canonical_application_spec(
                control_case_id,
                constants,
                basis_protocol,
                grid_protocol,
                readout_protocol,
            )
        )
    return tuple(specs)


def _build_closed_parent_freeze() -> ParentFreezeManifest:
    constants = _build_constants()
    provisional = ParentFreezeManifest(
        parent_freeze_schema_version=PARENT_FREEZE_SCHEMA_VERSION,
        program_id=PROGRAM_ID,
        parent_v2_sha=PARENT_V2_SHA,
        task9_commit_sha=TASK9_COMMIT_SHA,
        taskbook_source_sha=TASKBOOK_SOURCE_SHA,
        implementation_plan_source_sha=IMPLEMENTATION_PLAN_SOURCE_SHA,
        erratum_source_sha=ERRATUM_SOURCE_SHA,
        synthetic_control_application_specs=_build_application_specs(constants),
        protocol_constant_payload=constants,
        source_closure=_SOURCE_CLOSURE,
        parent_freeze_sha="0" * 64,
    )
    return replace(
        provisional,
        parent_freeze_sha=canonical_sha(parent_freeze_manifest_payload(provisional)),
    )


_CLOSED_PARENT_FREEZE = _build_closed_parent_freeze()


_CANDIDATE_PENDING_CONSTRUCTION_CASES = frozenset(
    {
        "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
        "C08_RANK_R_MISSING_MODES",
        "C10_FULL_SOURCE_EXTRA_MODE",
        "C12_NU_INC_IR_NORMALIZATION",
    }
)


def _candidate_scenario_execution_specs(
    application: V3M0SyntheticControlApplicationSpec,
) -> tuple[ApplicationScenarioExecutionSpec, ...]:
    if application.control_case_id != (
        "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE"
    ):
        return application.scenario_execution_specs
    instance_id = application.application_instance_id
    return (
        _make_scenario_execution_spec(
            instance_id,
            slug="constructive",
            output_local_id="01-constructive",
            execution_lane="BLOCK_SUCCESS",
            execution_recipe_id="two-mode-constructive-interference-v2",
            recipe_derivation_source_id="signed-scenario-response-design-v1",
            expected_terminal_stage="success",
        ),
        _make_scenario_execution_spec(
            instance_id,
            slug="destructive",
            output_local_id="02-destructive",
            execution_lane="BLOCK_SUCCESS",
            execution_recipe_id="two-mode-destructive-interference-v2",
            recipe_derivation_source_id="signed-scenario-response-design-v1",
            expected_terminal_stage="success",
        ),
    )


def _build_candidate_selector(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> ScenarioBasisSelectorSpec:
    source_basis = application.basis_protocol.source_basis
    readout_basis = application.basis_protocol.readout_basis
    public_source = basis_manifest_array(source_basis)
    public_readout = basis_manifest_array(readout_basis)
    source_selector = np.eye(public_source.shape[0], dtype=np.complex128)
    readout_selector = np.eye(public_readout.shape[0], dtype=np.complex128)
    source_derivation_id = "permit-public-basis-identity-selector-v1"
    readout_derivation_id = "permit-public-coisometry-identity-selector-v1"
    case_id = application.control_case_id
    identifier = scenario.scenario_id
    if case_id == "C05_PHASE_AND_SCALAR_GAIN":
        if identifier.endswith(".scenario.phase.v1"):
            source_selector = np.asarray(
                ((0.0,), (1.0 + 1.0j,), (1.0j,), (0.0,)),
                dtype=np.complex128,
            ) / math.sqrt(3.0)
            readout_selector = np.asarray(
                ((3.0, 1.0 + 1.0j, -2.0, 2.0j),),
                dtype=np.complex128,
            ) / math.sqrt(19.0)
        else:
            source_selector = np.asarray(
                ((0.0,), (1.0,), (-1.0 + 1.0j,), (0.0,)),
                dtype=np.complex128,
            ) / math.sqrt(3.0)
            readout_selector = np.asarray(
                ((-3.0 + 5.0j, -1.0 + 1.0j, -1.0, -1.0),),
                dtype=np.complex128,
            ) / math.sqrt(38.0)
        source_derivation_id = "identity-column-combination-v1"
        readout_derivation_id = "identity-normalized-row-combination-v1"
    elif case_id in {
        "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
        "C16_COVERAGE_025_075",
    }:
        root_two = math.sqrt(2.0)
        half_root_two = 1.0 / (2.0 * root_two)
        semantic = np.asarray(
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
        if case_id == "C16_COVERAGE_025_075" or identifier.endswith(
            ".scenario.low-rank-tt.v1"
        ):
            source_selector = semantic[:, :1]
        elif identifier.endswith(".scenario.tt.v1"):
            source_selector = semantic[:, :2]
        elif identifier.endswith(".scenario.tt-plus-row.v1"):
            source_selector = semantic[:, (0, 1, 3)]
        else:
            source_selector = semantic
        source_derivation_id = "analytic-common-geometry-semantic-frame-v1"
    elif case_id == "C17_QUOTIENT_GAUGE_COVERAGE":
        cosine = 1.0 / math.sqrt(65.0)
        sine = 8.0 / math.sqrt(65.0)
        normalizer = 1.0 / math.sqrt(2.0)
        source_selector = normalizer * np.asarray(
            (
                (cosine, -sine),
                (-1.0j * cosine, -1.0j * sine),
                (sine, cosine),
                (-1.0j * sine, 1.0j * cosine),
            ),
            dtype=np.complex128,
        )
        source_derivation_id = "c17-analytic-actual-positive-shell-v1"
    elif case_id == "C18_ABLATED_INDEPENDENT_UNARY":
        source_selector = np.asarray(
            ((1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (0.0, 0.0)),
            dtype=np.complex128,
        )
        readout_selector = np.asarray(
            ((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
            dtype=np.complex128,
        )
        source_derivation_id = "c18-q0-q1-independent-source-selector-v2"
        readout_derivation_id = "c18-p0-p1-readout-selector-v2"
    elif case_id == "C19_FULL_POSITIVE_OBSERVER_COLLAPSE":
        normalizer = 1.0 / math.sqrt(2.0)
        source_selector = normalizer * np.asarray(
            (
                (1.0, 0.0),
                (-1.0j, 0.0),
                (0.0, 1.0),
                (0.0, -1.0j),
            ),
            dtype=np.complex128,
        )
        source_derivation_id = "c19-analytic-full-positive-shell-v1"
    source_injection = public_source.T @ source_selector
    readout_coisometry = readout_selector @ np.conj(public_readout)
    provisional = ScenarioBasisSelectorSpec(
        selector_schema_version=SCENARIO_BASIS_SELECTOR_SCHEMA_VERSION,
        scenario_id=scenario.scenario_id,
        public_source_basis_manifest_id=source_basis.manifest_id,
        public_readout_basis_manifest_id=readout_basis.manifest_id,
        source_selector_derivation_id=source_derivation_id,
        readout_selector_derivation_id=readout_derivation_id,
        source_selector=freeze_complex_tensor(source_selector),
        readout_selector=freeze_complex_tensor(readout_selector),
        source_injection=freeze_complex_tensor(source_injection),
        readout_coisometry=freeze_complex_tensor(readout_coisometry),
        selector_sha="0" * 64,
    )
    return replace(
        provisional,
        selector_sha=canonical_sha(
            scenario_basis_selector_spec_payload(provisional)
        ),
    )


def _candidate_expected_actual_shell_rank(control_case_id: str, fallback: int) -> int:
    if control_case_id in {
        "C05_PHASE_AND_SCALAR_GAIN",
        "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
        "C16_COVERAGE_025_075",
        "C17_QUOTIENT_GAUGE_COVERAGE",
        "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
    }:
        return 2
    if control_case_id == "C18_ABLATED_INDEPENDENT_UNARY":
        return 1
    return fallback


def _candidate_geometry_bundle_id(control_case_id: str) -> Optional[str]:
    return {
        "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY": (
            "c15-analytic-shell-semantic-bundle-v1"
        ),
        "C16_COVERAGE_025_075": "c16-analytic-coverage-target-bundle-v1",
        "C17_QUOTIENT_GAUGE_COVERAGE": (
            "c17-analytic-quotient-gauge-bundle-v1"
        ),
        "C18_ABLATED_INDEPENDENT_UNARY": (
            "c18-independent-unary-direct-sum-bundle-v2"
        ),
        "C19_FULL_POSITIVE_OBSERVER_COLLAPSE": (
            "c19-full-positive-observer-collapse-bundle-v1"
        ),
    }.get(control_case_id)


def _build_candidate_response_template(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
    selector: ScenarioBasisSelectorSpec,
) -> ScenarioResponseTemplate:
    grid = application.grid_protocol
    pending = application.control_case_id in _CANDIDATE_PENDING_CONSTRUCTION_CASES
    source_count = frozen_tensor_array(selector.source_selector).shape[1]
    incidence_family_id = "inherit-case-readout-incidence-v1"
    normalizer_formula_id = application.readout_protocol.curvature_normalizer_id
    if application.control_case_id == "C12_NU_INC_IR_NORMALIZATION":
        incidence_family_id = "synthetic-lattice-laplacian-incidence-v1"
        normalizer_formula_id = "nu-inc-4-sum-sin2-half-v1"
    provisional = ScenarioResponseTemplate(
        template_schema_version=SCENARIO_RESPONSE_TEMPLATE_SCHEMA_VERSION,
        scenario_id=scenario.scenario_id,
        selector_sha=selector.selector_sha,
        construction_preflight_state=(
            "PENDING_CONSTRUCTION_PREFLIGHT"
            if pending
            else "PROVISIONAL_ANALYTIC_TEMPLATE"
        ),
        response_torus_denominators=grid.response_torus_denominators,
        response_reciprocal_indices=grid.response_reciprocal_indices,
        source_readout_bridge_reciprocal_indices=(
            grid.bridge_reciprocal_indices
        ),
        source_readout_bridge_steps=grid.bridge_steps,
        reference_reciprocal_index=grid.reference_reciprocal_index,
        preregistered_phase_bands=grid.preregistered_phase_bands,
        expected_actual_shell_rank=_candidate_expected_actual_shell_rank(
            application.control_case_id,
            grid.expected_shell_rank,
        ),
        source_trial_vectors=freeze_complex_tensor(
            np.eye(source_count, dtype=np.complex128)
        ),
        curvature_incidence_family_id=incidence_family_id,
        curvature_normalizer_formula_id=normalizer_formula_id,
        geometry_bundle_derivation_id=_candidate_geometry_bundle_id(
            application.control_case_id
        ),
        template_sha="0" * 64,
    )
    return replace(
        provisional,
        template_sha=canonical_sha(
            scenario_response_template_payload(provisional)
        ),
    )


def _build_candidate_prediction_profile(
    control_case_id: str,
    scenario_id: str,
) -> ScenarioPredictionProfile:
    pending = control_case_id in _CANDIDATE_PENDING_CONSTRUCTION_CASES
    provisional = ScenarioPredictionProfile(
        profile_schema_version=SCENARIO_PREDICTION_PROFILE_SCHEMA_VERSION,
        scenario_id=scenario_id,
        prediction_state=(
            "PENDING_CONSTRUCTION_PREFLIGHT"
            if pending
            else "PROVISIONAL_ANALYTIC_PREDICTION"
        ),
        quantities=(),
        profile_sha="0" * 64,
    )
    return replace(
        provisional,
        profile_sha=canonical_sha(
            scenario_prediction_profile_payload(provisional)
        ),
    )


def _build_candidate_scenario(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> ParentFreezeCandidateScenario:
    selector = _build_candidate_selector(application, scenario)
    response_template = _build_candidate_response_template(
        application,
        scenario,
        selector,
    )
    prediction_profile = _build_candidate_prediction_profile(
        application.control_case_id,
        scenario.scenario_id,
    )
    provisional = ParentFreezeCandidateScenario(
        candidate_scenario_schema_version=(
            PARENT_FREEZE_CANDIDATE_SCENARIO_SCHEMA_VERSION
        ),
        control_case_id=application.control_case_id,
        application_instance_id=application.application_instance_id,
        based_on_application_spec_sha=application.application_spec_sha,
        scenario_execution_spec=scenario,
        selector_spec=selector,
        response_template=response_template,
        prediction_profile=prediction_profile,
        candidate_scenario_sha="0" * 64,
    )
    return replace(
        provisional,
        candidate_scenario_sha=canonical_sha(
            parent_freeze_candidate_scenario_payload(provisional)
        ),
    )


def _build_candidate_application(
    application: V3M0SyntheticControlApplicationSpec,
) -> ParentFreezeCandidateApplication:
    scenarios = tuple(
        _build_candidate_scenario(application, scenario)
        for scenario in _candidate_scenario_execution_specs(application)
    )
    provisional = ParentFreezeCandidateApplication(
        candidate_application_schema_version=(
            PARENT_FREEZE_CANDIDATE_APPLICATION_SCHEMA_VERSION
        ),
        control_case_id=application.control_case_id,
        application_instance_id=application.application_instance_id,
        based_on_application_spec_sha=application.application_spec_sha,
        scenario_candidates=scenarios,
        candidate_application_sha="0" * 64,
    )
    return replace(
        provisional,
        candidate_application_sha=canonical_sha(
            parent_freeze_candidate_application_payload(provisional)
        ),
    )


def verify_parent_freeze_candidate(
    candidate: ParentFreezeCandidateManifest,
) -> ParentFreezeCandidateManifest:
    """Validate an inert candidate body without hydrating any capability."""

    if type(candidate) is not ParentFreezeCandidateManifest:
        raise TypeError("candidate must be an exact ParentFreezeCandidateManifest")
    candidate.__post_init__()
    if candidate.candidate_schema_version != (
        PARENT_FREEZE_CANDIDATE_SCHEMA_VERSION
    ):
        raise ValueError("unexpected parent candidate schema")
    if candidate.based_on_parent_freeze_sha != (
        _CLOSED_PARENT_FREEZE.parent_freeze_sha
    ):
        raise ValueError("candidate is not based on the closed Parent root")
    if candidate.scenario_response_design_commit_sha != (
        SCENARIO_RESPONSE_DESIGN_COMMIT_SHA
    ):
        raise ValueError("candidate design commit is not frozen")
    if candidate.scenario_response_design_source_path != (
        SCENARIO_RESPONSE_DESIGN_SOURCE_PATH
    ):
        raise ValueError("candidate design source path is not frozen")
    if candidate.scenario_response_design_source_sha != (
        SCENARIO_RESPONSE_DESIGN_SOURCE_SHA
    ):
        raise ValueError("candidate design source SHA is not frozen")
    if candidate.proposed_parent_freeze_schema_version != (
        "v3m0.parent-freeze.v2"
    ):
        raise ValueError("candidate proposed Parent schema is not frozen")
    if candidate.proposed_application_scenario_schema_version != (
        "v3m0.application-scenario-execution-spec.v2"
    ):
        raise ValueError("candidate proposed scenario schema is not frozen")
    applications = candidate.application_candidates
    if tuple(item.control_case_id for item in applications) != (
        APPLICATION_CONTROL_CASE_IDS
    ):
        raise ValueError("candidate applications are not in C01-C20 order")
    base_by_case = {
        item.control_case_id: item
        for item in _CLOSED_PARENT_FREEZE.synthetic_control_application_specs
    }
    scenario_ids: list[str] = []
    for application in applications:
        application.__post_init__()
        base = base_by_case[application.control_case_id]
        if (
            application.application_instance_id != base.application_instance_id
            or application.based_on_application_spec_sha
            != base.application_spec_sha
        ):
            raise ValueError("candidate application base binding mismatch")
        if application.candidate_application_sha != canonical_sha(
            parent_freeze_candidate_application_payload(application)
        ):
            raise ValueError("candidate application SHA mismatch")
        for scenario in application.scenario_candidates:
            scenario.__post_init__()
            if (
                scenario.control_case_id != application.control_case_id
                or scenario.application_instance_id
                != application.application_instance_id
                or scenario.based_on_application_spec_sha
                != application.based_on_application_spec_sha
            ):
                raise ValueError("candidate scenario application binding mismatch")
            identifier = scenario.scenario_execution_spec.scenario_id
            if not identifier.startswith(application.application_instance_id + "."):
                raise ValueError("candidate scenario ID is outside its application")
            if (
                scenario.selector_spec.scenario_id != identifier
                or scenario.response_template.scenario_id != identifier
                or scenario.prediction_profile.scenario_id != identifier
            ):
                raise ValueError("candidate scenario child ID binding mismatch")
            if scenario.response_template.selector_sha != (
                scenario.selector_spec.selector_sha
            ):
                raise ValueError("candidate response selector binding mismatch")
            selector = scenario.selector_spec
            selector.__post_init__()
            if selector.selector_sha != canonical_sha(
                scenario_basis_selector_spec_payload(selector)
            ):
                raise ValueError("candidate selector SHA mismatch")
            source_basis = base.basis_protocol.source_basis
            readout_basis = base.basis_protocol.readout_basis
            if (
                selector.public_source_basis_manifest_id
                != source_basis.manifest_id
                or selector.public_readout_basis_manifest_id
                != readout_basis.manifest_id
            ):
                raise ValueError("candidate selector public basis binding mismatch")
            public_source = basis_manifest_array(source_basis)
            public_readout = basis_manifest_array(readout_basis)
            source_selector = frozen_tensor_array(selector.source_selector)
            readout_selector = frozen_tensor_array(selector.readout_selector)
            if (
                source_selector.ndim != 2
                or source_selector.shape[0] != public_source.shape[0]
                or readout_selector.ndim != 2
                or readout_selector.shape[1] != public_readout.shape[0]
            ):
                raise ValueError("candidate selector shape mismatch")
            if max(
                float(
                    np.linalg.norm(
                        source_selector.conj().T @ source_selector
                        - np.eye(source_selector.shape[1]),
                        ord=2,
                    )
                ),
                float(
                    np.linalg.norm(
                        readout_selector @ readout_selector.conj().T
                        - np.eye(readout_selector.shape[0]),
                        ord=2,
                    )
                ),
            ) > 1.0e-12:
                raise ValueError("candidate selector is not isometric/coisometric")
            expected_source = public_source.T @ source_selector
            expected_readout = readout_selector @ np.conj(public_readout)
            if not np.array_equal(
                frozen_tensor_array(selector.source_injection),
                expected_source,
            ):
                raise ValueError("candidate source selector direction mismatch")
            if not np.array_equal(
                frozen_tensor_array(selector.readout_coisometry),
                expected_readout,
            ):
                raise ValueError("candidate readout selector direction mismatch")
            template = scenario.response_template
            template.__post_init__()
            if template.template_sha != canonical_sha(
                scenario_response_template_payload(template)
            ):
                raise ValueError("candidate response template SHA mismatch")
            expected_pending = (
                application.control_case_id
                in _CANDIDATE_PENDING_CONSTRUCTION_CASES
            )
            if (
                template.construction_preflight_state
                == "PENDING_CONSTRUCTION_PREFLIGHT"
            ) != expected_pending:
                raise ValueError("candidate construction preflight state mismatch")
            trials = frozen_tensor_array(template.source_trial_vectors)
            if not np.array_equal(
                trials,
                np.eye(source_selector.shape[1], dtype=np.complex128),
            ):
                raise ValueError("candidate source trials are not identity")
            profile = scenario.prediction_profile
            profile.__post_init__()
            if profile.profile_sha != canonical_sha(
                scenario_prediction_profile_payload(profile)
            ):
                raise ValueError("candidate prediction profile SHA mismatch")
            if (
                profile.prediction_state
                == "PENDING_CONSTRUCTION_PREFLIGHT"
            ) != expected_pending:
                raise ValueError("candidate prediction state mismatch")
            for quantity in profile.quantities:
                quantity.__post_init__()
                if quantity.quantity_sha != canonical_sha(
                    scenario_prediction_quantity_payload(quantity)
                ):
                    raise ValueError("candidate prediction quantity SHA mismatch")
            if scenario.candidate_scenario_sha != canonical_sha(
                parent_freeze_candidate_scenario_payload(scenario)
            ):
                raise ValueError("candidate scenario SHA mismatch")
            scenario_ids.append(identifier)
    if len(scenario_ids) != 32 or len(set(scenario_ids)) != 32:
        raise ValueError("candidate must carry exactly 32 unique scenarios")
    if candidate.candidate_sha != canonical_sha(
        parent_freeze_candidate_manifest_payload(candidate)
    ):
        raise ValueError("candidate_sha does not match the complete body")
    return candidate


def build_v3m0_parent_freeze_candidate() -> ParentFreezeCandidateManifest:
    """Build the sole inert Phase-B review candidate; issue no authority."""

    provisional = ParentFreezeCandidateManifest(
        candidate_schema_version=PARENT_FREEZE_CANDIDATE_SCHEMA_VERSION,
        authority_state="PROVISIONAL_NOT_ISSUED",
        based_on_parent_freeze_sha=_CLOSED_PARENT_FREEZE.parent_freeze_sha,
        scenario_response_design_commit_sha=(
            SCENARIO_RESPONSE_DESIGN_COMMIT_SHA
        ),
        scenario_response_design_source_path=(
            SCENARIO_RESPONSE_DESIGN_SOURCE_PATH
        ),
        scenario_response_design_source_sha=(
            SCENARIO_RESPONSE_DESIGN_SOURCE_SHA
        ),
        proposed_parent_freeze_schema_version="v3m0.parent-freeze.v2",
        proposed_application_scenario_schema_version=(
            "v3m0.application-scenario-execution-spec.v2"
        ),
        required_finalization_state=(
            "SIGNED_INCREMENTAL_ERRATUM_AND_SINGLE_PARENT_REFREEZE"
        ),
        application_candidates=tuple(
            _build_candidate_application(application)
            for application in (
                _CLOSED_PARENT_FREEZE.synthetic_control_application_specs
            )
        ),
        candidate_sha="0" * 64,
    )
    candidate = replace(
        provisional,
        candidate_sha=canonical_sha(
            parent_freeze_candidate_manifest_payload(provisional)
        ),
    )
    return verify_parent_freeze_candidate(candidate)


def _freeze_parent_authority_functions(
    *roots: FunctionType,
) -> tuple[FunctionType, ...]:
    """Detach parent verification from mutable module bindings."""

    cache: dict[int, FunctionType] = {}
    module_name = __name__

    def freeze_value(value):
        if type(value) is FunctionType and value.__module__ == module_name:
            return freeze_function(value)
        if type(value) is tuple:
            return tuple(freeze_value(item) for item in value)
        if type(value) is dict:
            return {key: freeze_value(item) for key, item in value.items()}
        return value

    def freeze_function(function):
        cached = cache.get(id(function))
        if cached is not None:
            return cached
        frozen_globals = dict(function.__globals__)
        frozen = FunctionType(
            function.__code__,
            frozen_globals,
            function.__name__,
            None,
            function.__closure__,
        )
        cache[id(function)] = frozen
        for name, value in tuple(frozen_globals.items()):
            if type(value) is FunctionType and value.__module__ == module_name:
                frozen_globals[name] = freeze_function(value)
        frozen.__defaults__ = freeze_value(function.__defaults__)
        frozen.__kwdefaults__ = freeze_value(function.__kwdefaults__)
        frozen.__annotations__ = dict(function.__annotations__)
        frozen.__dict__.update(function.__dict__)
        frozen.__doc__ = function.__doc__
        frozen.__module__ = function.__module__
        frozen.__qualname__ = function.__qualname__
        return frozen

    return tuple(freeze_function(root) for root in roots)


(
    _require_exact_parent_schema,
    verify_synthetic_control_application_spec,
    _validate_parent_freeze_manifest,
    _manifest_record,
) = _freeze_parent_authority_functions(
    _require_exact_parent_schema,
    verify_synthetic_control_application_spec,
    _validate_parent_freeze_manifest,
    _manifest_record,
)

_CLOSED_PARENT_FREEZE_SNAPSHOT = _clone_parent_wire(_CLOSED_PARENT_FREEZE)


class VerifiedParentFreeze:
    """Opaque live capability for the one closed V3-M0 parent body."""

    __slots__ = ("__manifest", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        manifest: ParentFreezeManifest,
        seal: str,
        *,
        _issuance_token=_ISSUANCE_TOKEN,
        _clone=_clone_parent_wire,
        _object_setattr=object.__setattr__,
        _type_error=TypeError,
    ) -> None:
        if token is not _issuance_token:
            raise _type_error("VerifiedParentFreeze can only be issued by this module")
        _object_setattr(
            self,
            "_VerifiedParentFreeze__manifest",
            _clone(manifest),
        )
        _object_setattr(
            self,
            "_VerifiedParentFreeze__token",
            token,
        )
        _object_setattr(self, "_VerifiedParentFreeze__seal", seal)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedParentFreeze is immutable")

    @property
    def manifest(self) -> ParentFreezeManifest:
        return _reverify_verified_parent_freeze(self)


@dataclass(frozen=True)
class _ParentFreezeAuthority:
    manifest: ParentFreezeManifest
    fingerprint: str


def _parent_freeze_seal(
    manifest: ParentFreezeManifest,
    *,
    canonical_hash=canonical_sha,
    manifest_record=_manifest_record,
) -> str:
    return canonical_hash(
        {
            "authority_kind": "v3m0-parent-freeze-live-identity-v1",
            "manifest": manifest_record(manifest),
        }
    )


def _make_parent_freeze_registry(
    *,
    manifest_validator=_validate_parent_freeze_manifest,
    seal_builder=_parent_freeze_seal,
    authority_type=_ParentFreezeAuthority,
    wrapper_type=VerifiedParentFreeze,
    issuance_token=_ISSUANCE_TOKEN,
    clone=_clone_parent_wire,
    weak_reference=weakref.ref,
    lock_builder=threading.RLock,
    type_fn=type,
    id_fn=id,
    object_type=object,
    type_error=TypeError,
    value_error=ValueError,
    runtime_error=RuntimeError,
    attribute_error=AttributeError,
) -> tuple[
    Callable[[ParentFreezeManifest], VerifiedParentFreeze],
    Callable[[VerifiedParentFreeze], ParentFreezeManifest],
]:
    registry: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedParentFreeze],
            _ParentFreezeAuthority,
        ],
    ] = {}
    lock = lock_builder()

    def issue_authorized(
        manifest: ParentFreezeManifest,
    ) -> VerifiedParentFreeze:
        snapshot = manifest_validator(
            manifest,
            require_closed_body=True,
        )
        fingerprint = seal_builder(snapshot)
        wrapper = wrapper_type(
            issuance_token,
            snapshot,
            fingerprint,
        )
        identity = id_fn(wrapper)

        def remove_stale(
            reference: weakref.ReferenceType[VerifiedParentFreeze],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = registry.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del registry[wrapper_id]

        reference = weak_reference(wrapper, remove_stale)
        authority = authority_type(
            manifest=clone(snapshot),
            fingerprint=fingerprint,
        )
        with lock:
            current = registry.get(identity)
            if current is not None and current[0]() is not None:
                raise runtime_error("live VerifiedParentFreeze identity collision")
            registry[identity] = (reference, authority)
        return wrapper

    def reverify_authorized(
        wrapper: VerifiedParentFreeze,
    ) -> ParentFreezeManifest:
        if type_fn(wrapper) is not wrapper_type:
            raise type_error(
                "parent-freeze consumer requires a module-issued VerifiedParentFreeze"
            )
        with lock:
            current = registry.get(id_fn(wrapper))
            if current is None or current[0]() is not wrapper:
                raise value_error(
                    "VerifiedParentFreeze identity is absent from the "
                    "authority registry"
                )
            authority = current[1]
        try:
            token = object_type.__getattribute__(
                wrapper,
                "_VerifiedParentFreeze__token",
            )
            seal = object_type.__getattribute__(
                wrapper,
                "_VerifiedParentFreeze__seal",
            )
            manifest = object_type.__getattribute__(
                wrapper,
                "_VerifiedParentFreeze__manifest",
            )
        except attribute_error as exc:
            raise value_error(
                "VerifiedParentFreeze authority record is incomplete"
            ) from exc
        if token is not issuance_token:
            raise value_error("VerifiedParentFreeze authority token mismatch")
        snapshot = manifest_validator(
            manifest,
            require_closed_body=True,
        )
        expected_seal = seal_builder(snapshot)
        if seal != expected_seal or seal != authority.fingerprint:
            raise value_error("VerifiedParentFreeze authority seal mismatch")
        if snapshot != authority.manifest:
            raise value_error("VerifiedParentFreeze manifest authority mismatch")
        return clone(authority.manifest)

    return issue_authorized, reverify_authorized


_issue_verified_parent_freeze, _reverify_verified_parent_freeze = (
    _make_parent_freeze_registry()
)


def _make_parent_public_api(
    *,
    closed_snapshot=_clone_parent_wire(_CLOSED_PARENT_FREEZE_SNAPSHOT),
    manifest_validator=_validate_parent_freeze_manifest,
    issuer=_issue_verified_parent_freeze,
    reverifier=_reverify_verified_parent_freeze,
    clone=_clone_parent_wire,
):
    def issue_v3m0_parent_freeze() -> VerifiedParentFreeze:
        """Issue the one no-argument, module-closed V3-M0 parent."""

        return issuer(clone(closed_snapshot))

    def verify_parent_freeze(
        manifest: ParentFreezeManifest,
    ) -> VerifiedParentFreeze:
        """Hydrate only the exact recursive closed parent body."""

        snapshot = manifest_validator(
            manifest,
            require_closed_body=True,
        )
        return issuer(snapshot)

    def parent_property(
        wrapper: VerifiedParentFreeze,
    ) -> ParentFreezeManifest:
        return reverifier(wrapper)

    return (
        issue_v3m0_parent_freeze,
        verify_parent_freeze,
        parent_property,
    )


(
    issue_v3m0_parent_freeze,
    verify_parent_freeze,
    _closed_parent_property,
) = _make_parent_public_api()

setattr(
    VerifiedParentFreeze,
    "manifest",
    property(_closed_parent_property),
)


__all__ = [
    "APPLICATION_CONTROL_CASE_IDS",
    "APPLICATION_PREDICTION_PROFILE_SCHEMA_VERSION",
    "APPLICATION_REFERENCE_PHASE_BAND_SOURCE_ID",
    "APPLICATION_SCENARIO_SCHEMA_VERSION",
    "DM26_DETERMINISTIC_CONTROL_SOURCE_ID",
    "ERRATUM_SOURCE_PATH",
    "IMPLEMENTATION_PLAN_SOURCE_PATH",
    "PARENT_FREEZE_CANDIDATE_SCHEMA_VERSION",
    "PARENT_FREEZE_SCHEMA_VERSION",
    "PROGRAM_ID",
    "TASK9_COMMIT_SHA",
    "TASKBOOK_SOURCE_PATH",
    "ApplicationExecutionLane",
    "ApplicationOperationKind",
    "ApplicationScenarioExecutionSpec",
    "ApplicationTerminalStage",
    "DirectionPathClosure",
    "ParentFreezeCandidateApplication",
    "ParentFreezeCandidateManifest",
    "ParentFreezeCandidateScenario",
    "ParentFreezeManifest",
    "ScenarioBasisSelectorSpec",
    "ScenarioPredictionProfile",
    "ScenarioPredictionQuantity",
    "ScenarioResponseTemplate",
    "SyntheticApplicationBasisProtocol",
    "SyntheticApplicationGridProtocol",
    "SyntheticApplicationOperation",
    "SyntheticApplicationPredictionProfile",
    "SyntheticApplicationProtocolConstants",
    "SyntheticApplicationReadoutProtocol",
    "TaggedScalarWire",
    "V3M0SyntheticControlApplicationSpec",
    "VerifiedParentFreeze",
    "application_scenario_execution_spec_payload",
    "build_v3m0_parent_freeze_candidate",
    "issue_v3m0_parent_freeze",
    "parent_freeze_candidate_application_payload",
    "parent_freeze_candidate_manifest_payload",
    "parent_freeze_candidate_scenario_payload",
    "parent_freeze_manifest_payload",
    "scenario_basis_selector_spec_payload",
    "scenario_prediction_profile_payload",
    "scenario_prediction_quantity_payload",
    "scenario_response_template_payload",
    "synthetic_application_basis_protocol_payload",
    "synthetic_application_grid_protocol_payload",
    "synthetic_application_operation_payload",
    "synthetic_application_prediction_profile_payload",
    "synthetic_application_protocol_constants_payload",
    "synthetic_application_readout_protocol_payload",
    "synthetic_control_application_spec_payload",
    "tagged_scalar_wire_payload",
    "verify_parent_freeze",
    "verify_parent_freeze_candidate",
    "verify_application_scenario_execution_spec",
    "verify_synthetic_control_application_spec",
]
