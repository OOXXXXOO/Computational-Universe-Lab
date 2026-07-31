"""Closed real-space recipe compiler for V3-M0 application controls.

C06--C12 records are construction inputs, not response evidence.  A recipe
can only be built from a live ``VerifiedParentFreeze`` and one exact frozen
scenario ID.  Its logical operation DAG is evaluated before a bounded local
canonical-shear program is emitted for the existing factory path.  C05 is
deliberately weaker: it exports only a parent-bound analytic template until
the live calibration permit supplies the selected Fejer order.
"""

from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass, replace
from typing import Literal, Optional

import numpy as np
import sympy as sp

from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    PrimitiveInterface,
    PrimitiveOperatorWire,
    basis_manifest_array,
    freeze_complex_tensor,
    frozen_tensor_array,
)
from .parent_freeze import (
    ApplicationScenarioExecutionSpec,
    SyntheticApplicationOperation,
    TaggedScalarWire,
    V3M0SyntheticControlApplicationSpec,
    VerifiedParentFreeze,
    _reverify_verified_parent_freeze,
    synthetic_application_operation_payload,
    verify_synthetic_control_application_spec,
)
from .trace import (
    ConstructionTrace,
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
)


APPLICATION_OPERATION_EFFECT_SCHEMA_VERSION = "v3m0.application-operation-effect.v1"
APPLICATION_LOCAL_SHEAR_STEP_SCHEMA_VERSION = "v3m0.application-local-shear-step.v1"
APPLICATION_RECIPE_ARTIFACT_SCHEMA_VERSION = "v3m0.application-recipe-artifact.v1"
APPLICATION_C05_FEJER_TEMPLATE_SCHEMA_VERSION = "v3m0.application-c05-fejer-template.v1"

APPLICATION_C05_TEMPLATE_SCENARIO_IDS = (
    "v3m0.synthetic-control.c05.v1.scenario.phase.v1",
    "v3m0.synthetic-control.c05.v1.scenario.gain.v1",
)

APPLICATION_RECIPE_SCENARIO_IDS = (
    "v3m0.synthetic-control.c06.v1.scenario.nonscale-mixing.v1",
    "v3m0.synthetic-control.c07.v1.scenario.interference.v1",
    "v3m0.synthetic-control.c08.v1.scenario.rank-missing.v1",
    "v3m0.synthetic-control.c09.v1.scenario.gauge-dressing.v1",
    "v3m0.synthetic-control.c10.v1.scenario.extra-mode.v1",
    "v3m0.synthetic-control.c11.v1.scenario.signal.v1",
    "v3m0.synthetic-control.c12.v1.scenario.ir-normalization.v1",
)

_RECIPE_ID_BY_SCENARIO = {
    APPLICATION_C05_TEMPLATE_SCENARIO_IDS[0]: "two-mode-phase-rotation-v1",
    APPLICATION_C05_TEMPLATE_SCENARIO_IDS[1]: "two-mode-scalar-gain-v1",
    APPLICATION_RECIPE_SCENARIO_IDS[0]: "two-mode-source-linear-mix-v1",
    APPLICATION_RECIPE_SCENARIO_IDS[1]: "two-mode-coherent-interference-v1",
    APPLICATION_RECIPE_SCENARIO_IDS[2]: "two-mode-rank-deletion-v1",
    APPLICATION_RECIPE_SCENARIO_IDS[3]: "two-mode-pure-gauge-dressing-v1",
    APPLICATION_RECIPE_SCENARIO_IDS[4]: "two-mode-full-source-extra-mode-v1",
    APPLICATION_RECIPE_SCENARIO_IDS[5]: "two-mode-amplitude-activation-v1",
    APPLICATION_RECIPE_SCENARIO_IDS[6]: "two-mode-ir-normalization-v1",
}

_CHANNEL_ORDER = ("q0", "p0", "q1", "p1")
_CHANNEL_INDEX = {name: index for index, name in enumerate(_CHANNEL_ORDER)}
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_C05_PERMIT_FEJER_ORDERS = (256, 512, 1024, 2048, 4096, 8192)


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


def _finite_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an exact float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _operation_record(operation: SyntheticApplicationOperation) -> dict[str, object]:
    return {
        **synthetic_application_operation_payload(operation),
        "operation_sha": operation.operation_sha,
    }


@dataclass(frozen=True)
class ApplicationOperationEffect:
    effect_schema_version: str
    operation: SyntheticApplicationOperation
    input_effect_digests: tuple[str, ...]
    effect_kind: str
    effect_tensor: FrozenComplexTensor
    effect_digest: str
    evaluation_sha: str

    def __post_init__(self) -> None:
        if self.effect_schema_version != APPLICATION_OPERATION_EFFECT_SCHEMA_VERSION:
            raise ValueError("application operation effect schema is not frozen")
        if type(self.operation) is not SyntheticApplicationOperation:
            raise TypeError("operation has the wrong strict type")
        if type(self.input_effect_digests) is not tuple:
            raise TypeError("input_effect_digests must be a tuple")
        for index, digest in enumerate(self.input_effect_digests):
            _sha(digest, f"input_effect_digests[{index}]")
        _text(self.effect_kind, "effect_kind")
        if type(self.effect_tensor) is not FrozenComplexTensor:
            raise TypeError("effect_tensor has the wrong strict type")
        _sha(self.effect_digest, "effect_digest")
        _sha(self.evaluation_sha, "evaluation_sha")


def application_operation_effect_payload(
    effect: ApplicationOperationEffect,
) -> dict[str, object]:
    if type(effect) is not ApplicationOperationEffect:
        raise TypeError("effect must be an exact ApplicationOperationEffect")
    return {
        "effect_schema_version": effect.effect_schema_version,
        "operation": _operation_record(effect.operation),
        "input_effect_digests": list(effect.input_effect_digests),
        "effect_kind": effect.effect_kind,
        "effect_tensor_sha": effect.effect_tensor.tensor_sha,
        "effect_digest": effect.effect_digest,
    }


@dataclass(frozen=True)
class ApplicationLocalShearStep:
    step_schema_version: str
    step_id: str
    source_channel: str
    destination_channel: str
    offset: tuple[int, ...]
    coefficient: float
    target_conditioned: bool
    derivation_effect_digest: str
    step_sha: str

    def __post_init__(self) -> None:
        if self.step_schema_version != APPLICATION_LOCAL_SHEAR_STEP_SCHEMA_VERSION:
            raise ValueError("application shear step schema is not frozen")
        _text(self.step_id, "step_id")
        if self.source_channel not in _CHANNEL_ORDER:
            raise ValueError("source_channel is outside the frozen channel order")
        if self.destination_channel not in _CHANNEL_ORDER:
            raise ValueError("destination_channel is outside the frozen channel order")
        if self.source_channel == self.destination_channel:
            raise ValueError("local shear must change channels")
        if (
            type(self.offset) is not tuple
            or len(self.offset) != 1
            or type(self.offset[0]) is not int
            or abs(self.offset[0]) > 1
        ):
            raise ValueError("primitive support exceeds the frozen radius")
        coefficient = _finite_float(self.coefficient, "coefficient")
        if coefficient == 0.0:
            raise ValueError("local shear coefficient must be bitwise non-zero")
        if type(self.target_conditioned) is not bool:
            raise TypeError("target_conditioned must be an exact bool")
        _sha(self.derivation_effect_digest, "derivation_effect_digest")
        _sha(self.step_sha, "step_sha")


def application_local_shear_step_payload(
    step: ApplicationLocalShearStep,
) -> dict[str, object]:
    if type(step) is not ApplicationLocalShearStep:
        raise TypeError("step must be an exact ApplicationLocalShearStep")
    return {
        "step_schema_version": step.step_schema_version,
        "step_id": step.step_id,
        "source_channel": step.source_channel,
        "destination_channel": step.destination_channel,
        "offset": list(step.offset),
        "coefficient": step.coefficient,
        "target_conditioned": step.target_conditioned,
        "derivation_effect_digest": step.derivation_effect_digest,
    }


@dataclass(frozen=True)
class ApplicationRecipeArtifact:
    recipe_schema_version: str
    control_case_id: str
    scenario_id: str
    application_spec_sha: str
    scenario_sha: str
    recipe_id: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_ndim: int
    operation_evaluations: tuple[ApplicationOperationEffect, ...]
    actual_steps: tuple[ApplicationLocalShearStep, ...]
    matched_ablated_steps: tuple[ApplicationLocalShearStep, ...]
    primitive_support_radius: int
    source_injection: FrozenComplexTensor
    readout: FrozenComplexTensor
    reference_phase_band: tuple[float, float]
    expected_shell_rank: int
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    recipe_sha: str

    def __post_init__(self) -> None:
        if self.recipe_schema_version != APPLICATION_RECIPE_ARTIFACT_SCHEMA_VERSION:
            raise ValueError("application recipe artifact schema is not frozen")
        _text(self.control_case_id, "control_case_id")
        _text(self.scenario_id, "scenario_id")
        _sha(self.application_spec_sha, "application_spec_sha")
        _sha(self.scenario_sha, "scenario_sha")
        _text(self.recipe_id, "recipe_id")
        _text(self.state_schema_id, "state_schema_id")
        if self.channel_order != _CHANNEL_ORDER:
            raise ValueError("application recipe channel order is not frozen")
        if self.spatial_ndim != 1:
            raise ValueError("application recipe spatial dimension is not frozen")
        if (
            type(self.operation_evaluations) is not tuple
            or not self.operation_evaluations
            or not all(
                type(item) is ApplicationOperationEffect
                for item in self.operation_evaluations
            )
        ):
            raise TypeError("operation_evaluations have the wrong strict type")
        for field in ("actual_steps", "matched_ablated_steps"):
            steps = getattr(self, field)
            if (
                type(steps) is not tuple
                or not steps
                or not all(type(item) is ApplicationLocalShearStep for item in steps)
            ):
                raise TypeError(f"{field} has the wrong strict type")
        if self.primitive_support_radius != 1:
            raise ValueError("primitive support radius is not frozen")
        for field in ("source_injection", "readout"):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        if (
            type(self.reference_phase_band) is not tuple
            or len(self.reference_phase_band) != 2
            or not all(
                type(value) is float and math.isfinite(value)
                for value in self.reference_phase_band
            )
            or self.reference_phase_band[0] >= self.reference_phase_band[1]
        ):
            raise ValueError("reference phase band is invalid")
        if self.expected_shell_rank != 1:
            raise ValueError("expected shell rank is not frozen")
        _sha(self.actual_effect_digest, "actual_effect_digest")
        _sha(
            self.matched_ablated_effect_digest,
            "matched_ablated_effect_digest",
        )
        _sha(self.recipe_sha, "recipe_sha")


def application_recipe_artifact_payload(
    recipe: ApplicationRecipeArtifact,
) -> dict[str, object]:
    if type(recipe) is not ApplicationRecipeArtifact:
        raise TypeError("recipe must be an exact ApplicationRecipeArtifact")
    return {
        "recipe_schema_version": recipe.recipe_schema_version,
        "control_case_id": recipe.control_case_id,
        "scenario_id": recipe.scenario_id,
        "application_spec_sha": recipe.application_spec_sha,
        "scenario_sha": recipe.scenario_sha,
        "recipe_id": recipe.recipe_id,
        "state_schema_id": recipe.state_schema_id,
        "channel_order": list(recipe.channel_order),
        "spatial_ndim": recipe.spatial_ndim,
        "operation_evaluations": [
            {
                **application_operation_effect_payload(item),
                "evaluation_sha": item.evaluation_sha,
            }
            for item in recipe.operation_evaluations
        ],
        "actual_steps": [
            {
                **application_local_shear_step_payload(item),
                "step_sha": item.step_sha,
            }
            for item in recipe.actual_steps
        ],
        "matched_ablated_steps": [
            {
                **application_local_shear_step_payload(item),
                "step_sha": item.step_sha,
            }
            for item in recipe.matched_ablated_steps
        ],
        "primitive_support_radius": recipe.primitive_support_radius,
        "source_injection_sha": recipe.source_injection.tensor_sha,
        "readout_sha": recipe.readout.tensor_sha,
        "reference_phase_band": list(recipe.reference_phase_band),
        "expected_shell_rank": recipe.expected_shell_rank,
        "actual_effect_digest": recipe.actual_effect_digest,
        "matched_ablated_effect_digest": recipe.matched_ablated_effect_digest,
    }


@dataclass(frozen=True)
class ApplicationC05FejerTemplate:
    template_schema_version: str
    control_case_id: str
    scenario_id: str
    application_spec_sha: str
    scenario_sha: str
    recipe_id: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    operation_evaluations: tuple[ApplicationOperationEffect, ...]
    coupling_kind: Literal["phase", "gain"]
    requested_value: float
    phase_offset_rule_id: str
    source_injection: FrozenComplexTensor
    readout: FrozenComplexTensor
    reference_phase_band: tuple[float, float]
    expected_shell_rank: int
    integration_state: Literal["PENDING_LIVE_PERMIT_T_BINDING"]
    template_sha: str

    def __post_init__(self) -> None:
        if (
            self.template_schema_version
            != APPLICATION_C05_FEJER_TEMPLATE_SCHEMA_VERSION
        ):
            raise ValueError("C05 Fejer template schema is not frozen")
        if self.control_case_id != "C05_PHASE_AND_SCALAR_GAIN":
            raise ValueError("C05 template control case is not frozen")
        if self.scenario_id not in APPLICATION_C05_TEMPLATE_SCENARIO_IDS:
            raise ValueError("C05 template scenario is outside the closed registry")
        _sha(self.application_spec_sha, "application_spec_sha")
        _sha(self.scenario_sha, "scenario_sha")
        _text(self.recipe_id, "recipe_id")
        _text(self.state_schema_id, "state_schema_id")
        if self.channel_order != _CHANNEL_ORDER:
            raise ValueError("C05 template channel order is not frozen")
        if (
            type(self.operation_evaluations) is not tuple
            or not self.operation_evaluations
            or not all(
                type(item) is ApplicationOperationEffect
                for item in self.operation_evaluations
            )
        ):
            raise TypeError("C05 operation evaluations have the wrong strict type")
        if self.coupling_kind not in ("phase", "gain"):
            raise ValueError("C05 coupling kind is not frozen")
        _finite_float(self.requested_value, "requested_value")
        _text(self.phase_offset_rule_id, "phase_offset_rule_id")
        for field in ("source_injection", "readout"):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        if (
            type(self.reference_phase_band) is not tuple
            or len(self.reference_phase_band) != 2
            or not all(
                type(value) is float and math.isfinite(value)
                for value in self.reference_phase_band
            )
            or self.reference_phase_band[0] >= self.reference_phase_band[1]
        ):
            raise ValueError("C05 reference phase band is invalid")
        if self.expected_shell_rank != 1:
            raise ValueError("C05 expected shell rank is not frozen")
        if self.integration_state != "PENDING_LIVE_PERMIT_T_BINDING":
            raise ValueError("C05 template cannot claim executable integration")
        _sha(self.template_sha, "template_sha")


def application_c05_fejer_template_payload(
    template: ApplicationC05FejerTemplate,
) -> dict[str, object]:
    if type(template) is not ApplicationC05FejerTemplate:
        raise TypeError("template must be an exact ApplicationC05FejerTemplate")
    return {
        "template_schema_version": template.template_schema_version,
        "control_case_id": template.control_case_id,
        "scenario_id": template.scenario_id,
        "application_spec_sha": template.application_spec_sha,
        "scenario_sha": template.scenario_sha,
        "recipe_id": template.recipe_id,
        "state_schema_id": template.state_schema_id,
        "channel_order": list(template.channel_order),
        "operation_evaluations": [
            {
                **application_operation_effect_payload(item),
                "evaluation_sha": item.evaluation_sha,
            }
            for item in template.operation_evaluations
        ],
        "coupling_kind": template.coupling_kind,
        "requested_value": template.requested_value,
        "phase_offset_rule_id": template.phase_offset_rule_id,
        "source_injection_sha": template.source_injection.tensor_sha,
        "readout_sha": template.readout.tensor_sha,
        "reference_phase_band": list(template.reference_phase_band),
        "expected_shell_rank": template.expected_shell_rank,
        "integration_state": template.integration_state,
    }


def _parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> TaggedScalarWire:
    matches = tuple(value for key, value in operation.parameters if key == name)
    if len(matches) != 1:
        raise ValueError(f"operation parameter {name!r} is not unique")
    return matches[0]


def _integer_parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> int:
    wire = _parameter(operation, name)
    if wire.value_kind != "integer" or wire.integer_value is None:
        raise TypeError(f"{name} must be an integer wire")
    return wire.integer_value


def _fp64_parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> float:
    wire = _parameter(operation, name)
    if wire.value_kind != "fp64-bits" or wire.fp64_bits_value is None:
        raise TypeError(f"{name} must be an fp64-bits wire")
    return struct.unpack(">d", struct.pack(">Q", wire.fp64_bits_value))[0]


def _text_parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> str:
    wire = _parameter(operation, name)
    if wire.value_kind != "text" or wire.text_value is None:
        raise TypeError(f"{name} must be a text wire")
    return wire.text_value


def _require_parameter_names(
    operation: SyntheticApplicationOperation,
    expected: tuple[str, ...],
) -> None:
    names = tuple(name for name, _ in operation.parameters)
    if names != tuple(sorted(expected)):
        raise ValueError("operation parameter registry is not exact")


def _finite_array(value: np.ndarray, field: str) -> np.ndarray:
    if type(value) is not np.ndarray:
        raise TypeError(f"{field} must be a NumPy ndarray")
    array = np.asarray(value, dtype=np.complex128)
    if array.ndim < 1 or any(length <= 0 for length in array.shape):
        raise ValueError(f"{field} must have a non-empty shape")
    if not np.isfinite(array.real).all() or not np.isfinite(array.imag).all():
        raise ValueError(f"{field} must be finite")
    return array.copy()


def _block_diagonal(inputs: tuple[np.ndarray, ...]) -> np.ndarray:
    if not inputs or not all(item.ndim == 2 for item in inputs):
        raise ValueError("direct-sum inputs must be non-empty matrices")
    rows = sum(item.shape[0] for item in inputs)
    columns = sum(item.shape[1] for item in inputs)
    output = np.zeros((rows, columns), dtype=np.complex128)
    row = 0
    column = 0
    for item in inputs:
        output[
            row : row + item.shape[0],
            column : column + item.shape[1],
        ] = item
        row += item.shape[0]
        column += item.shape[1]
    return output


def _evaluate_operation_values(
    operation: SyntheticApplicationOperation,
    inputs: tuple[np.ndarray, ...],
) -> np.ndarray:
    """Evaluate one logical operation without issuing any capability."""

    if type(operation) is not SyntheticApplicationOperation:
        raise TypeError("operation must be an exact SyntheticApplicationOperation")
    if operation.operation_sha != canonical_sha(
        synthetic_application_operation_payload(operation)
    ):
        raise ValueError("operation SHA does not match its complete body")
    if type(inputs) is not tuple:
        raise TypeError("operation inputs must be a tuple")
    arrays = tuple(
        _finite_array(value, f"inputs[{index}]") for index, value in enumerate(inputs)
    )

    if operation.operation_kind == "identity-v1":
        if arrays:
            raise ValueError("identity operation cannot have inputs")
        names = tuple(name for name, _ in operation.parameters)
        if names == ("response-rank",):
            rank = _integer_parameter(operation, "response-rank")
            if rank <= 0:
                raise ValueError("response rank must be positive")
            return np.eye(rank, dtype=np.complex128)
        if names == ("source-rank",):
            rank = _integer_parameter(operation, "source-rank")
            if rank <= 0:
                raise ValueError("source rank must be positive")
            return np.eye(rank, dtype=np.complex128)
        if names == ("target-rank",):
            rank = _integer_parameter(operation, "target-rank")
            if rank <= 0:
                raise ValueError("target rank must be positive")
            return np.eye(rank, dtype=np.complex128)
        if names == ("direction-count", "window-count"):
            directions = _integer_parameter(operation, "direction-count")
            windows = _integer_parameter(operation, "window-count")
            if directions <= 0 or windows <= 0:
                raise ValueError("direction/window counts must be positive")
            return np.ones((windows, directions), dtype=np.complex128)
        raise ValueError("identity parameter registry is not closed")

    if operation.operation_kind == "phase-rotation-v1":
        _require_parameter_names(operation, ("phase-radians",))
        if len(arrays) != 1:
            raise ValueError("phase rotation requires exactly one input")
        phase = _fp64_parameter(operation, "phase-radians")
        scalar = complex(math.cos(phase), math.sin(phase))
        return scalar * arrays[0]

    if operation.operation_kind == "amplitude-rescale-v1":
        _require_parameter_names(operation, ("amplitude-scale",))
        amplitude = _fp64_parameter(operation, "amplitude-scale")
        if len(arrays) == 0:
            return amplitude * np.asarray(((1.0,), (0.0,)), dtype=np.complex128)
        if len(arrays) != 1:
            raise ValueError("amplitude rescale accepts zero or one input")
        return amplitude * arrays[0]

    if operation.operation_kind == "source-linear-mix-v1":
        names = tuple(name for name, _ in operation.parameters)
        matrix_names = (
            ("matrix-00", "matrix-01", "matrix-10", "matrix-11")
            if names and names[0].startswith("matrix-")
            else ("combiner-00", "combiner-01", "combiner-10", "combiner-11")
        )
        if names == tuple(sorted(matrix_names)):
            if len(arrays) != 1 or arrays[0].ndim != 2:
                raise ValueError("linear mix requires one matrix input")
            prefix = "matrix" if names[0].startswith("matrix-") else "combiner"
            matrix = np.asarray(
                (
                    (
                        _integer_parameter(operation, f"{prefix}-00"),
                        _integer_parameter(operation, f"{prefix}-01"),
                    ),
                    (
                        _integer_parameter(operation, f"{prefix}-10"),
                        _integer_parameter(operation, f"{prefix}-11"),
                    ),
                ),
                dtype=np.complex128,
            )
            if arrays[0].shape[0] != 2:
                raise ValueError("linear mix input row count is not two")
            return matrix @ arrays[0]
        if names == ("new-source-axis", "orthogonal-amplitude"):
            if len(arrays) != 1 or arrays[0].shape != (2, 1):
                raise ValueError("extra-source operation input is malformed")
            axis = _integer_parameter(operation, "new-source-axis")
            amplitude = _fp64_parameter(operation, "orthogonal-amplitude")
            if axis not in (0, 1):
                raise ValueError("new source axis is outside the two-mode domain")
            output = arrays[0].copy()
            output[axis, 0] += amplitude
            return output
        raise ValueError("source-linear-mix parameter registry is not closed")

    if operation.operation_kind == "direct-sum-v1":
        names = tuple(name for name, _ in operation.parameters)
        if names == ("combination",):
            if _text_parameter(operation, "combination") != "coherent-pair":
                raise ValueError("direct-sum combination is not frozen")
            if len(arrays) != 2:
                raise ValueError("coherent pair requires two inputs")
            return _block_diagonal(arrays)
        if names == ("component-count",):
            if _integer_parameter(operation, "component-count") != len(arrays):
                raise ValueError("direct-sum component count mismatch")
            return _block_diagonal(arrays)
        raise ValueError("direct-sum parameter registry is not closed")

    if operation.operation_kind == "canonical-shear-v1":
        _require_parameter_names(
            operation,
            ("gauge-amplitude", "gauge-sector"),
        )
        if len(arrays) != 1 or arrays[0].shape != (2, 2):
            raise ValueError("gauge dressing input is malformed")
        amplitude = _fp64_parameter(operation, "gauge-amplitude")
        if _text_parameter(operation, "gauge-sector") != "readout-nullspace":
            raise ValueError("gauge sector is not the frozen nullspace")
        gauge_row = amplitude * np.asarray(((1.0, -1.0),), dtype=np.complex128)
        return np.concatenate((arrays[0], gauge_row), axis=0)

    if operation.operation_kind == "geometry-subspace-v1":
        names = tuple(name for name, _ in operation.parameters)
        if names == ("missing-rank", "selection"):
            if len(arrays) != 1 or arrays[0].shape != (2, 2):
                raise ValueError("rank-deletion input is malformed")
            missing = _integer_parameter(operation, "missing-rank")
            if missing < 0 or missing > arrays[0].shape[0]:
                raise ValueError("missing rank is outside the input rank")
            if _text_parameter(operation, "selection") != "target-conditioned":
                raise ValueError("rank-deletion selection is not frozen")
            output = arrays[0].copy()
            if missing:
                output[-missing:, :] = 0.0
            return output
        if names == ("quotient",):
            if len(arrays) != 1 or arrays[0].shape != (3, 2):
                raise ValueError("curvature quotient input is malformed")
            if _text_parameter(operation, "quotient") != "curvature":
                raise ValueError("geometry quotient is not frozen")
            return arrays[0][0:2].copy()
        if names == ("source-domain",):
            if len(arrays) != 2 or any(item.shape != (2, 1) for item in arrays):
                raise ValueError("full-source inputs are malformed")
            if _text_parameter(operation, "source-domain") != "full":
                raise ValueError("source domain is not frozen")
            return np.concatenate(arrays, axis=1)
        if names == (
            "curvature-mode-count",
            "normalizer",
            "raw-noise-gates",
        ):
            if len(arrays) != 1 or arrays[0].ndim != 2:
                raise ValueError("IR normalization input is malformed")
            mode_count = _integer_parameter(operation, "curvature-mode-count")
            if mode_count <= 0:
                raise ValueError("curvature mode count must be positive")
            if _text_parameter(operation, "normalizer") != "nu-inc":
                raise ValueError("IR normalizer is not frozen")
            if _text_parameter(operation, "raw-noise-gates") != "absolute-and-relative":
                raise ValueError("raw-noise gates are not frozen")
            return np.full(
                (arrays[0].shape[0],),
                float(mode_count),
                dtype=np.complex128,
            )
        raise ValueError("geometry-subspace parameter registry is not closed")

    raise ValueError("operation kind has no closed application evaluator")


def _operation_closure(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> tuple[SyntheticApplicationOperation, ...]:
    operations = {
        operation.operation_instance_id: operation
        for operation in application.operations
    }
    required: set[str] = set()
    pending = list(scenario.operation_output_ids)
    while pending:
        identifier = pending.pop()
        if identifier in required:
            continue
        operation = operations.get(identifier)
        if operation is None:
            raise ValueError("scenario closure references a missing operation")
        required.add(identifier)
        pending.extend(operation.input_operation_instance_ids)
    closure = tuple(
        operation
        for operation in application.operations
        if operation.operation_instance_id in required
    )
    if not closure:
        raise ValueError("scenario operation closure is empty")
    return closure


def _evaluate_operation_closure(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> tuple[ApplicationOperationEffect, ...]:
    arrays: dict[str, np.ndarray] = {}
    digests: dict[str, str] = {}
    evaluations: list[ApplicationOperationEffect] = []
    for operation in _operation_closure(application, scenario):
        try:
            input_arrays = tuple(
                arrays[identifier]
                for identifier in operation.input_operation_instance_ids
            )
            input_digests = tuple(
                digests[identifier]
                for identifier in operation.input_operation_instance_ids
            )
        except KeyError as exc:
            raise ValueError("operation closure is not topologically ordered") from exc
        values = _evaluate_operation_values(operation, input_arrays)
        tensor = freeze_complex_tensor(values)
        effect_digest = canonical_sha(
            {
                "effect_schema_version": "v3m0.executed-application-operation.v1",
                "operation": _operation_record(operation),
                "input_effect_digests": list(input_digests),
                "effect_kind": f"logical-{operation.operation_kind}",
                "effect_tensor_sha": tensor.tensor_sha,
            }
        )
        provisional = ApplicationOperationEffect(
            effect_schema_version=APPLICATION_OPERATION_EFFECT_SCHEMA_VERSION,
            operation=operation,
            input_effect_digests=input_digests,
            effect_kind=f"logical-{operation.operation_kind}",
            effect_tensor=tensor,
            effect_digest=effect_digest,
            evaluation_sha="0" * 64,
        )
        evaluation = replace(
            provisional,
            evaluation_sha=canonical_sha(
                application_operation_effect_payload(provisional)
            ),
        )
        arrays[operation.operation_instance_id] = values
        digests[operation.operation_instance_id] = effect_digest
        evaluations.append(evaluation)
    if tuple(arrays) != tuple(
        operation.operation_instance_id
        for operation in _operation_closure(application, scenario)
    ):
        raise AssertionError("operation evaluator lost the frozen DAG order")
    return tuple(evaluations)


def _step(
    step_id: str,
    source_channel: str,
    destination_channel: str,
    *,
    offset: int,
    coefficient: float,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> ApplicationLocalShearStep:
    provisional = ApplicationLocalShearStep(
        step_schema_version=APPLICATION_LOCAL_SHEAR_STEP_SCHEMA_VERSION,
        step_id=step_id,
        source_channel=source_channel,
        destination_channel=destination_channel,
        offset=(offset,),
        coefficient=float(coefficient),
        target_conditioned=target_conditioned,
        derivation_effect_digest=derivation_effect_digest,
        step_sha="0" * 64,
    )
    return replace(
        provisional,
        step_sha=canonical_sha(application_local_shear_step_payload(provisional)),
    )


def _parallel_mode_shears(
    prefix: str,
    *,
    source_mode: int,
    destination_mode: int,
    offset: int,
    coefficient: float,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    if source_mode not in (0, 1) or destination_mode not in (0, 1):
        raise ValueError("complex mode index is outside the frozen pair")
    if source_mode == destination_mode:
        raise ValueError("complex mode shear must change modes")
    source_q = "q0" if source_mode == 0 else "q1"
    source_p = "p0" if source_mode == 0 else "p1"
    destination_q = "q0" if destination_mode == 0 else "q1"
    destination_p = "p0" if destination_mode == 0 else "p1"
    return (
        _step(
            f"{prefix}.q",
            source_q,
            destination_q,
            offset=offset,
            coefficient=coefficient,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.p",
            source_p,
            destination_p,
            offset=offset,
            coefficient=coefficient,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
    )


def _two_mode_rotation_steps(
    angle: float,
    prefix: str,
    *,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    tangent = float(math.tan(angle / 2.0))
    sine = float(math.sin(angle))
    if tangent == 0.0 or sine == 0.0:
        raise ValueError("two-mode rotation angle collapsed to identity")
    return (
        *_parallel_mode_shears(
            f"{prefix}.lower.0",
            source_mode=0,
            destination_mode=1,
            offset=0,
            coefficient=tangent,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        *_parallel_mode_shears(
            f"{prefix}.upper",
            source_mode=1,
            destination_mode=0,
            offset=0,
            coefficient=-sine,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        *_parallel_mode_shears(
            f"{prefix}.lower.1",
            source_mode=0,
            destination_mode=1,
            offset=0,
            coefficient=tangent,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
    )


def _canonical_pair_rotation_steps(
    mode: int,
    angle: float,
    prefix: str,
    *,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    if mode not in (0, 1):
        raise ValueError("canonical pair index is outside the frozen pair")
    tangent = float(math.tan(angle / 2.0))
    sine = float(math.sin(angle))
    if tangent == 0.0 or sine == 0.0:
        raise ValueError("canonical rotation angle collapsed to identity")
    q_channel = "q0" if mode == 0 else "q1"
    p_channel = "p0" if mode == 0 else "p1"
    return (
        _step(
            f"{prefix}.lower.0",
            q_channel,
            p_channel,
            offset=0,
            coefficient=tangent,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.upper",
            p_channel,
            q_channel,
            offset=0,
            coefficient=-sine,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.lower.1",
            q_channel,
            p_channel,
            offset=0,
            coefficient=tangent,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
    )


def _reciprocal_swap_steps(
    prefix: str,
    *,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    return (
        *_parallel_mode_shears(
            f"{prefix}.lower.0",
            source_mode=0,
            destination_mode=1,
            offset=1,
            coefficient=1.0,
            target_conditioned=False,
            derivation_effect_digest=derivation_effect_digest,
        ),
        *_parallel_mode_shears(
            f"{prefix}.upper",
            source_mode=1,
            destination_mode=0,
            offset=-1,
            coefficient=-1.0,
            target_conditioned=False,
            derivation_effect_digest=derivation_effect_digest,
        ),
        *_parallel_mode_shears(
            f"{prefix}.lower.1",
            source_mode=0,
            destination_mode=1,
            offset=1,
            coefficient=1.0,
            target_conditioned=False,
            derivation_effect_digest=derivation_effect_digest,
        ),
    )


def _inverse_steps(
    steps: tuple[ApplicationLocalShearStep, ...],
    prefix: str,
    *,
    target_conditioned: Optional[bool] = None,
) -> tuple[ApplicationLocalShearStep, ...]:
    return tuple(
        _step(
            f"{prefix}.{index:02d}",
            item.source_channel,
            item.destination_channel,
            offset=item.offset[0],
            coefficient=-item.coefficient,
            target_conditioned=(
                item.target_conditioned
                if target_conditioned is None
                else target_conditioned
            ),
            derivation_effect_digest=item.derivation_effect_digest,
        )
        for index, item in enumerate(reversed(steps))
    )


def _quarter_turn_steps(
    mode: int,
    prefix: str,
    *,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    return _canonical_pair_rotation_steps(
        mode,
        math.pi / 2.0,
        prefix,
        target_conditioned=False,
        derivation_effect_digest=derivation_effect_digest,
    )


def _operations_by_suffix(
    evaluations: tuple[ApplicationOperationEffect, ...],
) -> dict[str, SyntheticApplicationOperation]:
    return {
        item.operation.operation_instance_id.rsplit(".", maxsplit=1)[-1]: (
            item.operation
        )
        for item in evaluations
    }


def _causal_fejer_scalar(offset: float, order: int) -> complex:
    ratio = complex(math.cos(-offset), math.sin(-offset))
    power = 1.0 + 0.0j
    real_terms: list[float] = []
    imag_terms: list[float] = []
    for step in range(order):
        weight = 1.0 - float(step) / float(order)
        term = weight * power
        real_terms.append(float(term.real))
        imag_terms.append(float(term.imag))
        power *= ratio
    normalization = (float(order) + 1.0) / 2.0
    return complex(
        math.fsum(real_terms) / normalization,
        math.fsum(imag_terms) / normalization,
    )


def _gain_phase_offset(gain: float, order: int) -> float:
    if not math.isfinite(gain) or gain <= 1.0:
        raise ValueError("scalar gain must be finite and greater than one")
    target = 1.0 / gain
    lower = 0.0
    upper = 2.0 * math.pi / float(order)
    if abs(_causal_fejer_scalar(upper, order)) >= target:
        raise ValueError("gain target has no root in the frozen first lobe")
    for _ in range(96):
        midpoint = (lower + upper) / 2.0
        if abs(_causal_fejer_scalar(midpoint, order)) > target:
            lower = midpoint
        else:
            upper = midpoint
    result = (lower + upper) / 2.0
    if abs(abs(_causal_fejer_scalar(result, order)) - target) > 2.0e-14:
        raise ValueError("gain phase offset failed its analytic root check")
    return result


def _validate_c05_template_body(template: ApplicationC05FejerTemplate) -> None:
    if type(template) is not ApplicationC05FejerTemplate:
        raise TypeError("template must be an exact ApplicationC05FejerTemplate")
    expected_kind = (
        "phase"
        if template.scenario_id == APPLICATION_C05_TEMPLATE_SCENARIO_IDS[0]
        else "gain"
    )
    expected_rule = (
        "parent-phase-over-live-permit-fejer-order-v1"
        if expected_kind == "phase"
        else "first-lobe-inverse-gain-root-live-permit-fejer-order-v1"
    )
    if template.coupling_kind != expected_kind:
        raise ValueError("C05 coupling kind differs from its frozen scenario")
    if template.phase_offset_rule_id != expected_rule:
        raise ValueError("C05 phase-offset rule differs from its frozen scenario")
    if frozen_tensor_array(template.source_injection).shape != (4, 4):
        raise ValueError("C05 source injection shape is not frozen")
    if frozen_tensor_array(template.readout).shape != (4, 4):
        raise ValueError("C05 readout shape is not frozen")
    if template.template_sha != canonical_sha(
        application_c05_fejer_template_payload(template)
    ):
        raise ValueError("C05 template SHA does not match its complete body")


def _c05_phase_offset_for_order(
    template: ApplicationC05FejerTemplate,
    selected_fejer_order: int,
) -> float:
    """Pure draft for the permit-owning materializer; this issues no recipe."""

    _validate_c05_template_body(template)
    if type(selected_fejer_order) is not int:
        raise TypeError("selected Fejer order must be an exact int")
    if selected_fejer_order not in _C05_PERMIT_FEJER_ORDERS:
        raise ValueError("selected Fejer order is not a live-permit candidate")
    if template.coupling_kind == "phase":
        return abs(template.requested_value) / float(selected_fejer_order)
    return _gain_phase_offset(
        template.requested_value,
        selected_fejer_order,
    )


def _modification(
    scenario_id: str,
    evaluations: tuple[ApplicationOperationEffect, ...],
) -> tuple[
    Literal[
        "inactive-phase",
        "conjugation",
        "external-sign",
    ],
    float,
]:
    operations = _operations_by_suffix(evaluations)
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[0]:
        operation = operations["01-nonscalar-mix"]
        numerator = float(
            _integer_parameter(operation, "matrix-01")
            - _integer_parameter(operation, "matrix-10")
        )
        denominator = float(
            _integer_parameter(operation, "matrix-00")
            + _integer_parameter(operation, "matrix-11")
        )
        return "conjugation", math.atan2(numerator, denominator)
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[1]:
        operation = operations["04-interference-combiner"]
        numerator = float(
            abs(_integer_parameter(operation, "combiner-01"))
            + abs(_integer_parameter(operation, "combiner-10"))
        )
        denominator = float(
            abs(_integer_parameter(operation, "combiner-00"))
            + abs(_integer_parameter(operation, "combiner-11"))
        )
        return "external-sign", math.atan2(numerator, denominator)
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[2]:
        missing = _integer_parameter(
            operations["01-rank-one-deletion"],
            "missing-rank",
        )
        return "external-sign", missing * math.pi / 2.0
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[3]:
        amplitude = _fp64_parameter(
            operations["01-pure-gauge-dressing"],
            "gauge-amplitude",
        )
        return "inactive-phase", math.atan(abs(amplitude)) / 2.0
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[4]:
        operation = operations["01-ablated-orthogonal-mode"]
        axis = _integer_parameter(operation, "new-source-axis")
        amplitude = _fp64_parameter(operation, "orthogonal-amplitude")
        return "conjugation", (axis + abs(amplitude)) * math.pi / 4.0
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[5]:
        amplitude = _fp64_parameter(
            operations["03-signal-amplitude"],
            "amplitude-scale",
        )
        return "inactive-phase", amplitude * math.pi / 8.0
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[6]:
        operation = operations["01-nu-inc-normalized"]
        modes = _integer_parameter(operation, "curvature-mode-count")
        return "inactive-phase", math.atan(float(modes)) / 2.0
    raise ValueError("scenario has no closed local modification")


def _carrier_angles(
    scenario_id: str,
    evaluations: tuple[ApplicationOperationEffect, ...],
) -> tuple[float, float]:
    operations = _operations_by_suffix(evaluations)
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[1]:
        operation = operations["04-interference-combiner"]
        numerator = float(
            abs(_integer_parameter(operation, "combiner-01"))
            + abs(_integer_parameter(operation, "combiner-10"))
        )
        denominator = float(
            abs(_integer_parameter(operation, "combiner-00"))
            + abs(_integer_parameter(operation, "combiner-11"))
        )
        angle = math.atan2(numerator, denominator)
        return -angle, -angle
    if scenario_id == APPLICATION_RECIPE_SCENARIO_IDS[2]:
        missing = _integer_parameter(
            operations["01-rank-one-deletion"],
            "missing-rank",
        )
        angle = missing * math.pi / 4.0
        return angle, -angle
    return 0.271, -0.193


def _build_steps(
    scenario_id: str,
    evaluations: tuple[ApplicationOperationEffect, ...],
) -> tuple[ApplicationLocalShearStep, ...]:
    effect_digest = evaluations[-1].effect_digest
    alpha, beta = _carrier_angles(scenario_id, evaluations)
    reciprocal = _reciprocal_swap_steps(
        "blind.reciprocal",
        derivation_effect_digest=effect_digest,
    )
    left = (
        *_two_mode_rotation_steps(
            -alpha,
            "blind.left.r-minus-alpha",
            target_conditioned=False,
            derivation_effect_digest=effect_digest,
        ),
        *_inverse_steps(reciprocal, "blind.left.reciprocal-inverse"),
        *_two_mode_rotation_steps(
            -beta,
            "blind.left.r-minus-beta",
            target_conditioned=False,
            derivation_effect_digest=effect_digest,
        ),
    )
    carrier = (
        *_quarter_turn_steps(
            0,
            "blind.carrier.mode0",
            derivation_effect_digest=effect_digest,
        ),
        *_quarter_turn_steps(
            1,
            "blind.carrier.mode1.first",
            derivation_effect_digest=effect_digest,
        ),
        *_quarter_turn_steps(
            1,
            "blind.carrier.mode1.second",
            derivation_effect_digest=effect_digest,
        ),
    )
    right = (
        *_two_mode_rotation_steps(
            beta,
            "blind.right.r-beta",
            target_conditioned=False,
            derivation_effect_digest=effect_digest,
        ),
        *reciprocal,
        *_two_mode_rotation_steps(
            alpha,
            "blind.right.r-alpha",
            target_conditioned=False,
            derivation_effect_digest=effect_digest,
        ),
    )
    kind, angle = _modification(scenario_id, evaluations)
    if not math.isfinite(angle) or angle == 0.0:
        raise ValueError("scenario modification angle is not finite non-zero")
    if kind == "inactive-phase":
        conditioned = _canonical_pair_rotation_steps(
            1,
            angle,
            "conditioned.phase",
            target_conditioned=True,
            derivation_effect_digest=effect_digest,
        )
        return (*left, *carrier, *conditioned, *right)
    if kind == "external-sign":
        sign = (
            *_canonical_pair_rotation_steps(
                1,
                math.pi / 2.0,
                "conditioned.sign.first",
                target_conditioned=True,
                derivation_effect_digest=effect_digest,
            ),
            *_canonical_pair_rotation_steps(
                1,
                math.pi / 2.0,
                "conditioned.sign.second",
                target_conditioned=True,
                derivation_effect_digest=effect_digest,
            ),
        )
        inverse_sign = _inverse_steps(
            sign,
            "conditioned.sign.inverse",
            target_conditioned=True,
        )
        return (*inverse_sign, *left, *carrier, *right, *sign)
    conditioned = _two_mode_rotation_steps(
        angle,
        "conditioned.mix.forward",
        target_conditioned=True,
        derivation_effect_digest=effect_digest,
    )
    inverse = _inverse_steps(
        conditioned,
        "conditioned.mix.inverse",
        target_conditioned=True,
    )
    return (*left, *inverse, *carrier, *conditioned, *right)


def _executed_effect_digest(
    steps: tuple[ApplicationLocalShearStep, ...],
    branch: Literal["actual", "matched_ablated"],
) -> str:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("execution branch is not frozen")
    coefficients: dict[int, np.ndarray] = {
        0: np.eye(len(_CHANNEL_ORDER), dtype=np.complex128)
    }
    for step in steps:
        if branch == "matched_ablated" and step.target_conditioned:
            continue
        source = _CHANNEL_INDEX[step.source_channel]
        destination = _CHANNEL_INDEX[step.destination_channel]
        previous = {
            offset: np.asarray(matrix, dtype=np.complex128).copy()
            for offset, matrix in coefficients.items()
        }
        updated = {
            offset: np.asarray(matrix, dtype=np.complex128).copy()
            for offset, matrix in previous.items()
        }
        for offset, matrix in previous.items():
            shifted = offset + step.offset[0]
            contribution = np.zeros_like(matrix)
            contribution[destination] = step.coefficient * matrix[source]
            if shifted in updated:
                updated[shifted] += contribution
            else:
                updated[shifted] = contribution
        coefficients = updated
    support = tuple(sorted(coefficients))
    tensor = freeze_complex_tensor(
        np.stack(tuple(coefficients[offset] for offset in support), axis=0)
    )
    return canonical_sha(
        {
            "effect_schema_version": "v3m0.application-laurent-effect.v1",
            "branch": branch,
            "support_offsets": list(support),
            "kernel_tensor_sha": tensor.tensor_sha,
        }
    )


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
    expected_recipe_id = _RECIPE_ID_BY_SCENARIO.get(identifier)
    if (
        scenario.execution_lane != "BLOCK_SUCCESS"
        or expected_recipe_id is None
        or scenario.execution_recipe_id != expected_recipe_id
        or scenario.expected_terminal_stage != "success"
        or scenario.expected_undefined_reason is not None
        or scenario.expected_artifact_type != "VerifiedResponseBlock"
    ):
        raise ValueError("scenario is not a registered BLOCK_SUCCESS recipe")
    return application, scenario


def _validate_recipe_body(recipe: ApplicationRecipeArtifact) -> None:
    if type(recipe) is not ApplicationRecipeArtifact:
        raise TypeError("recipe must be an exact ApplicationRecipeArtifact")
    if recipe.scenario_id not in APPLICATION_RECIPE_SCENARIO_IDS:
        raise ValueError("recipe scenario is outside the closed registry")
    if _RECIPE_ID_BY_SCENARIO[recipe.scenario_id] != recipe.recipe_id:
        raise ValueError("recipe ID differs from its frozen scenario")
    expected_ablated = tuple(
        step for step in recipe.actual_steps if not step.target_conditioned
    )
    if recipe.matched_ablated_steps != expected_ablated:
        raise ValueError("recipe matched-ablation steps are not mechanical")
    if len({step.step_id for step in recipe.actual_steps}) != len(recipe.actual_steps):
        raise ValueError("recipe step IDs repeat")
    if frozen_tensor_array(recipe.source_injection).shape != (4, 4):
        raise ValueError("recipe source injection shape is not frozen")
    if frozen_tensor_array(recipe.readout).shape != (4, 4):
        raise ValueError("recipe readout shape is not frozen")
    for step in recipe.actual_steps:
        if step.step_sha != canonical_sha(application_local_shear_step_payload(step)):
            raise ValueError("recipe step SHA does not match its body")
    known_digests: dict[str, str] = {}
    for evaluation in recipe.operation_evaluations:
        operation = evaluation.operation
        expected_inputs = tuple(
            known_digests[identifier]
            for identifier in operation.input_operation_instance_ids
        )
        if evaluation.input_effect_digests != expected_inputs:
            raise ValueError("recipe operation effect inputs are not closed")
        values = _evaluate_operation_values(
            operation,
            tuple(
                frozen_tensor_array(
                    next(
                        prior.effect_tensor
                        for prior in recipe.operation_evaluations
                        if prior.operation.operation_instance_id == identifier
                    )
                )
                for identifier in operation.input_operation_instance_ids
            ),
        )
        if not np.array_equal(values, frozen_tensor_array(evaluation.effect_tensor)):
            raise ValueError("recipe operation effect tensor does not replay")
        expected_digest = canonical_sha(
            {
                "effect_schema_version": "v3m0.executed-application-operation.v1",
                "operation": _operation_record(operation),
                "input_effect_digests": list(expected_inputs),
                "effect_kind": evaluation.effect_kind,
                "effect_tensor_sha": evaluation.effect_tensor.tensor_sha,
            }
        )
        if evaluation.effect_digest != expected_digest:
            raise ValueError("recipe operation effect digest does not replay")
        if evaluation.evaluation_sha != canonical_sha(
            application_operation_effect_payload(evaluation)
        ):
            raise ValueError("recipe operation evaluation SHA does not replay")
        known_digests[operation.operation_instance_id] = expected_digest
    if recipe.actual_effect_digest != _executed_effect_digest(
        recipe.actual_steps,
        "actual",
    ):
        raise ValueError("recipe actual execution digest does not replay")
    if recipe.matched_ablated_effect_digest != _executed_effect_digest(
        recipe.actual_steps,
        "matched_ablated",
    ):
        raise ValueError("recipe ablated execution digest does not replay")
    if recipe.actual_effect_digest == recipe.matched_ablated_effect_digest:
        raise ValueError("recipe actual and ablated effects are identical")
    if recipe.recipe_sha != canonical_sha(application_recipe_artifact_payload(recipe)):
        raise ValueError("recipe SHA does not match its complete body")


def build_c05_fejer_recipe_template(
    parent: VerifiedParentFreeze,
    scenario_id: str,
) -> ApplicationC05FejerTemplate:
    """Bind C05 math to ParentFreeze without claiming executable integration."""

    application, scenario = _find_application_and_scenario(parent, scenario_id)
    if scenario.scenario_id not in APPLICATION_C05_TEMPLATE_SCENARIO_IDS:
        raise ValueError("scenario is not a frozen C05 Fejer template")
    evaluations = _evaluate_operation_closure(application, scenario)
    operations = _operations_by_suffix(evaluations)
    if scenario.scenario_id == APPLICATION_C05_TEMPLATE_SCENARIO_IDS[0]:
        coupling_kind: Literal["phase", "gain"] = "phase"
        requested_value = _fp64_parameter(
            operations["01-phase-flip"],
            "phase-radians",
        )
        rule_id = "parent-phase-over-live-permit-fejer-order-v1"
    else:
        coupling_kind = "gain"
        requested_value = _fp64_parameter(
            operations["02-scalar-gain"],
            "amplitude-scale",
        )
        rule_id = "first-lobe-inverse-gain-root-live-permit-fejer-order-v1"
    source = application.basis_protocol.source_basis
    readout = application.basis_protocol.readout_basis
    if (
        source.state_schema_id != readout.state_schema_id
        or source.channel_order != readout.channel_order
        or source.channel_order != _CHANNEL_ORDER
    ):
        raise ValueError("C05 source/readout interface is not frozen")
    phase_bands = application.grid_protocol.preregistered_phase_bands
    if len(phase_bands) != 1:
        raise ValueError("C05 reference phase band is not unique")
    provisional = ApplicationC05FejerTemplate(
        template_schema_version=APPLICATION_C05_FEJER_TEMPLATE_SCHEMA_VERSION,
        control_case_id=application.control_case_id,
        scenario_id=scenario.scenario_id,
        application_spec_sha=application.application_spec_sha,
        scenario_sha=scenario.scenario_sha,
        recipe_id=scenario.execution_recipe_id,
        state_schema_id=source.state_schema_id,
        channel_order=source.channel_order,
        operation_evaluations=evaluations,
        coupling_kind=coupling_kind,
        requested_value=requested_value,
        phase_offset_rule_id=rule_id,
        source_injection=freeze_complex_tensor(basis_manifest_array(source)),
        readout=freeze_complex_tensor(basis_manifest_array(readout)),
        reference_phase_band=phase_bands[0],
        expected_shell_rank=application.grid_protocol.expected_shell_rank,
        integration_state="PENDING_LIVE_PERMIT_T_BINDING",
        template_sha="0" * 64,
    )
    template = replace(
        provisional,
        template_sha=canonical_sha(application_c05_fejer_template_payload(provisional)),
    )
    _validate_c05_template_body(template)
    return template


def verify_c05_fejer_recipe_template(
    parent: VerifiedParentFreeze,
    template: ApplicationC05FejerTemplate,
) -> ApplicationC05FejerTemplate:
    """Replay a C05 template against ParentFreeze; no permit is inferred."""

    _validate_c05_template_body(template)
    expected = build_c05_fejer_recipe_template(parent, template.scenario_id)
    if template != expected:
        raise ValueError("C05 template differs from the live parent compilation")
    return template


def build_application_recipe(
    parent: VerifiedParentFreeze,
    scenario_id: str,
) -> ApplicationRecipeArtifact:
    """Compile one exact live-parent success scenario to local shear inputs."""

    identifier = _text(scenario_id, "scenario_id")
    if identifier in APPLICATION_C05_TEMPLATE_SCENARIO_IDS:
        _find_application_and_scenario(parent, identifier)
        raise ValueError(
            "C05 executable recipe integration pending live permit T binding"
        )
    application, scenario = _find_application_and_scenario(parent, identifier)
    evaluations = _evaluate_operation_closure(application, scenario)
    steps = _build_steps(scenario.scenario_id, evaluations)
    ablated = tuple(step for step in steps if not step.target_conditioned)
    source = application.basis_protocol.source_basis
    readout = application.basis_protocol.readout_basis
    if (
        source.state_schema_id != readout.state_schema_id
        or source.channel_order != readout.channel_order
        or source.channel_order != _CHANNEL_ORDER
    ):
        raise ValueError("application source/readout interface is not frozen")
    phase_bands = application.grid_protocol.preregistered_phase_bands
    if len(phase_bands) != 1:
        raise ValueError("application reference phase band is not unique")
    provisional = ApplicationRecipeArtifact(
        recipe_schema_version=APPLICATION_RECIPE_ARTIFACT_SCHEMA_VERSION,
        control_case_id=application.control_case_id,
        scenario_id=scenario.scenario_id,
        application_spec_sha=application.application_spec_sha,
        scenario_sha=scenario.scenario_sha,
        recipe_id=scenario.execution_recipe_id,
        state_schema_id=source.state_schema_id,
        channel_order=source.channel_order,
        spatial_ndim=application.grid_protocol.spatial_ndim,
        operation_evaluations=evaluations,
        actual_steps=steps,
        matched_ablated_steps=ablated,
        primitive_support_radius=1,
        source_injection=freeze_complex_tensor(basis_manifest_array(source)),
        readout=freeze_complex_tensor(basis_manifest_array(readout)),
        reference_phase_band=phase_bands[0],
        expected_shell_rank=application.grid_protocol.expected_shell_rank,
        actual_effect_digest=_executed_effect_digest(steps, "actual"),
        matched_ablated_effect_digest=_executed_effect_digest(
            steps,
            "matched_ablated",
        ),
        recipe_sha="0" * 64,
    )
    recipe = replace(
        provisional,
        recipe_sha=canonical_sha(application_recipe_artifact_payload(provisional)),
    )
    _validate_recipe_body(recipe)
    return recipe


def verify_application_recipe(
    parent: VerifiedParentFreeze,
    recipe: ApplicationRecipeArtifact,
) -> ApplicationRecipeArtifact:
    """Replay a raw recipe against the live parent and return that same record."""

    _validate_recipe_body(recipe)
    expected = build_application_recipe(parent, recipe.scenario_id)
    if recipe != expected:
        raise ValueError("recipe differs from the live parent compilation")
    return recipe


def application_recipe_symbol(
    recipe: ApplicationRecipeArtifact,
    momentum: float,
    branch: Literal["actual", "matched_ablated"],
) -> np.ndarray:
    """Evaluate the same ordered shear executor in Laurent-symbol form."""

    _validate_recipe_body(recipe)
    value = _finite_float(momentum, "momentum")
    if branch == "actual":
        steps = recipe.actual_steps
    elif branch == "matched_ablated":
        steps = recipe.matched_ablated_steps
    else:
        raise ValueError("branch is outside the application recipe registry")
    matrix = np.eye(len(recipe.channel_order), dtype=np.complex128)
    for step in steps:
        shear = np.eye(len(recipe.channel_order), dtype=np.complex128)
        phase = complex(
            math.cos(value * step.offset[0]),
            math.sin(value * step.offset[0]),
        )
        source = _CHANNEL_INDEX[step.source_channel]
        destination = _CHANNEL_INDEX[step.destination_channel]
        shear[destination, source] += step.coefficient * phase
        matrix = shear @ matrix
    return matrix


def build_application_recipe_trace_and_operators(
    parent: VerifiedParentFreeze,
    recipe: ApplicationRecipeArtifact,
    *,
    target_spec_id: str,
    interface: PrimitiveInterface,
) -> tuple[ConstructionTrace, tuple[PrimitiveOperatorWire, ...]]:
    """Translate a verified recipe into the existing trace/factory wire types."""

    verified = verify_application_recipe(parent, recipe)
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
        raise ValueError("factory interface differs from the verified recipe")
    application, scenario = _find_application_and_scenario(
        parent,
        verified.scenario_id,
    )
    closure = _operation_closure(application, scenario)
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
    blind_provenance_id = f"{verified.scenario_id}.local-recipe"
    conditioned_provenance_id = f"{verified.scenario_id}.target-conditioned"
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
    previous: Optional[str] = None
    for index, step in enumerate(verified.actual_steps):
        mechanism_id = f"{verified.scenario_id}.shear.{index:03d}"
        production_id = (
            "target_operator" if step.target_conditioned else "local_canonical_shear"
        )
        layer_slot_id = f"{verified.scenario_id}.layer.{index:03d}"
        primitive_specs.append(
            PrimitiveSpec(
                mechanism_id=mechanism_id,
                production_id=production_id,
                depends_on=() if previous is None else (previous,),
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
        previous = mechanism_id
    trace = build_construction_trace(
        target_spec_id=target_id,
        provenance_nodes=tuple(provenance),
        primitive_specs=tuple(primitive_specs),
    )
    return trace, tuple(operators)


__all__ = [
    "APPLICATION_C05_FEJER_TEMPLATE_SCHEMA_VERSION",
    "APPLICATION_C05_TEMPLATE_SCENARIO_IDS",
    "APPLICATION_LOCAL_SHEAR_STEP_SCHEMA_VERSION",
    "APPLICATION_OPERATION_EFFECT_SCHEMA_VERSION",
    "APPLICATION_RECIPE_ARTIFACT_SCHEMA_VERSION",
    "APPLICATION_RECIPE_SCENARIO_IDS",
    "ApplicationC05FejerTemplate",
    "ApplicationLocalShearStep",
    "ApplicationOperationEffect",
    "ApplicationRecipeArtifact",
    "application_c05_fejer_template_payload",
    "application_local_shear_step_payload",
    "application_operation_effect_payload",
    "application_recipe_artifact_payload",
    "application_recipe_symbol",
    "build_c05_fejer_recipe_template",
    "build_application_recipe",
    "build_application_recipe_trace_and_operators",
    "verify_c05_fejer_recipe_template",
    "verify_application_recipe",
]
