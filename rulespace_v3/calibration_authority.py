"""Task 12 calibration and synthetic-application authorities.

Raw records in this module are serialization wires.  They never authorize a
run by themselves.  The two opaque wrappers used by Task 12 are backed by
live, weakly-held registries and are replayed against the closed parent and
the verified Task 11 calibration before every use.

The application permit is deliberately pre-response: its exact schema has no
transition, certificate, paired-response, or application-evidence field.
"""

from __future__ import annotations

import math
import re
import struct
import threading
import weakref
from dataclasses import dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional

import numpy as np
import sympy as sp

from .ablation import (
    AblationConstructionOutcome,
    AblationManifest,
    AblationReplacement,
    _verify_construction_outcome,
    matched_ablation,
)
from .contracts import BlockStatus, UndefinedReason
from .evidence import _make_exact_wire_cloner, canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    LinearRealspaceFactory,
    Primitive,
    PrimitiveInterface,
    PrimitiveOperatorWire,
    VerifiedFactory,
    _reverify_verified_factory,
    build_factory_from_trace,
    freeze_complex_tensor,
    frozen_tensor_array,
)
from .grids import (
    BridgeKGridManifest,
    DirectionManifest,
    ResponseKGridManifest,
    build_application_bridge_grid_manifest,
    build_response_grid_manifest,
)
from .parent_freeze import (
    ApplicationScenarioExecutionSpec,
    ParentFreezeManifest,
    SyntheticApplicationOperation,
    TaggedScalarWire,
    V3M0SyntheticControlApplicationSpec,
    VerifiedParentFreeze,
    _PARENT_WIRE_TYPES,
    _reverify_verified_parent_freeze,
    synthetic_application_operation_payload,
    verify_synthetic_control_application_spec,
)
from .pair_snapshot import (
    AblationPairSnapshot,
    _pair_snapshot,
)
from .registry import (
    CONTROL_ORDER,
    ClosedControlRegistry,
    ControlReadoutCalibrationSpec,
    VerifiedControlRegistry,
    _REGISTRY_WIRE_TYPES,
    _reverify_verified_control_registry,
    readout_calibration_spec_payload,
)
from .thresholds import (
    BRIDGE_TOLERANCE,
    EPS_FP64,
    SignalThresholdValues,
    T_CANDIDATES,
    compute_signal_threshold_values,
    phase_grid_step,
    phase_separation_min,
    verify_window_comparison_gates,
    verify_window_protocol_thresholds,
)
from .trace import (
    ConstructionTrace,
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
)
from .window import (
    WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION,
    ControlWindowProtocolEntry,
    VerifiedWindowCalibrationProtocol,
    WindowCalibrationProtocol,
    _reverify_verified_window_calibration_protocol,
    control_window_protocol_entry_payload,
    window_calibration_protocol_payload,
)

if TYPE_CHECKING:
    from .registry import ControlRegistryEntry
    from .response import (
        EndpointReferenceOutcome,
        EndpointShellOutcome,
        PairedResponseOutcome,
        ResponseRunSpec,
    )


SELECTED_EVIDENCE_REF_SCHEMA_VERSION = "v3m0.selected-control-evidence-ref.v1"
WINDOW_THRESHOLD_SELECTION_SCHEMA_VERSION = "v3m0.window-threshold-selection.v1"
WINDOW_THRESHOLD_CALIBRATION_SCHEMA_VERSION = (
    "v3m0.window-threshold-calibration-manifest.v1"
)
WINDOW_CALIBRATION_OUTCOME_SCHEMA_VERSION = "v3m0.window-calibration-outcome.v1"
EXPECTED_RANK_DECLARATION_SCHEMA_VERSION = "v3m0.expected-rank-declaration.v1"
CANDIDATE_ATTEMPT_AUDIT_SCHEMA_VERSION = "v3m0.candidate-attempt-audit.v1"
CALIBRATION_APPLICATION_PERMIT_SCHEMA_VERSION = "v3m0.calibration-application-permit.v1"
APPLICATION_RESPONSE_RUN_SPEC_SCHEMA_VERSION = "v3m0.application-response-run-spec.v1"
SCENARIO_OPERATION_EVALUATION_SCHEMA_VERSION = "v3m0.scenario-operation-evaluation.v1"
SCENARIO_CONSTRUCTION_SCHEMA_VERSION = "v3m0.scenario-construction.v1"
RESPONSE_BLOCK_ATTEMPT_PRECURSOR_SCHEMA_VERSION = (
    "v3m0.response-block-attempt-precursor.v1"
)
RESPONSE_BLOCK_ATTEMPT_OUTCOME_SCHEMA_VERSION = "v3m0.response-block-attempt-outcome.v1"
CALIBRATION_APPLICATION_SCOPE: Literal["v3m0-synthetic-control-application-v1"] = (
    "v3m0-synthetic-control-application-v1"
)
APPLICATION_EXPECTED_RANK_SOURCE_ID: Literal[
    "parent-freeze-control-application-spec-v1"
] = "parent-freeze-control-application-spec-v1"
APPLICATION_READOUT_DERIVATION_ID: Literal[
    "control-readout-calibration-spec-recursive-v1"
] = "control-readout-calibration-spec-recursive-v1"
C04_LOCAL_SHEAR_STEP_SCHEMA_VERSION = "v3m0.c04-local-shear-step.v1"
C04_CANONICAL_ANGLE_RECIPE_SCHEMA_VERSION = "v3m0.c04-canonical-angle-recipe.v1"
C04_CANONICAL_ANGLE_RECIPE_ID = "two-mode-split-step-canonical-angle-v1"

_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_GENERAL_BODY_CAP = 256 * 1024 * 1024
_TEXT_CAP = 16_384
_TREE_DEPTH_CAP = 128
_ISSUANCE_TOKEN = object()


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


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


@dataclass(frozen=True)
class C04LocalShearStep:
    step_schema_version: str
    step_id: str
    source_channel: str
    destination_channel: str
    offset: tuple[int, ...]
    coefficient: float
    target_conditioned: bool
    step_sha: str

    def __post_init__(self) -> None:
        if self.step_schema_version != C04_LOCAL_SHEAR_STEP_SCHEMA_VERSION:
            raise ValueError("C04 shear step schema is not frozen")
        _text(self.step_id, "step_id")
        _text(self.source_channel, "source_channel")
        _text(self.destination_channel, "destination_channel")
        if self.source_channel == self.destination_channel:
            raise ValueError("C04 shear source/destination must differ")
        if (
            type(self.offset) is not tuple
            or len(self.offset) != 1
            or type(self.offset[0]) is not int
            or abs(self.offset[0]) > 1
        ):
            raise ValueError("C04 primitive support radius exceeds one")
        if (
            type(self.coefficient) is not float
            or not math.isfinite(self.coefficient)
            or self.coefficient == 0.0
        ):
            raise ValueError("C04 shear coefficient must be finite and non-zero")
        if type(self.target_conditioned) is not bool:
            raise TypeError("target_conditioned must be an exact bool")
        _sha(self.step_sha, "step_sha")


def c04_local_shear_step_payload(
    step: C04LocalShearStep,
) -> dict[str, object]:
    _exact_record(step, C04LocalShearStep, "C04 local shear step")
    return {
        "step_schema_version": step.step_schema_version,
        "step_id": step.step_id,
        "source_channel": step.source_channel,
        "destination_channel": step.destination_channel,
        "offset": list(step.offset),
        "coefficient": step.coefficient,
        "target_conditioned": step.target_conditioned,
    }


@dataclass(frozen=True)
class C04CanonicalAngleRecipe:
    recipe_schema_version: str
    recipe_id: str
    channel_order: tuple[str, ...]
    alpha: float
    beta: float
    steps: tuple[C04LocalShearStep, ...]
    primitive_support_radius: int
    reference_phase_band: tuple[float, float]
    expected_shell_rank: int
    response_momenta: tuple[float, ...]
    canonical_structure: FrozenComplexTensor
    source_injection: FrozenComplexTensor
    readout: FrozenComplexTensor
    actual_effect_digest: str
    ablated_effect_digest: str
    recipe_sha: str

    def __post_init__(self) -> None:
        if self.recipe_schema_version != C04_CANONICAL_ANGLE_RECIPE_SCHEMA_VERSION:
            raise ValueError("C04 recipe schema is not frozen")
        if self.recipe_id != C04_CANONICAL_ANGLE_RECIPE_ID:
            raise ValueError("C04 recipe ID is not frozen")
        if self.channel_order != ("q0", "p0", "q1", "p1"):
            raise ValueError("C04 recipe channel order is not frozen")
        for field in ("alpha", "beta"):
            value = getattr(self, field)
            if type(value) is not float or not math.isfinite(value):
                raise ValueError(f"{field} must be finite fp64")
        if (
            type(self.steps) is not tuple
            or not self.steps
            or not all(type(item) is C04LocalShearStep for item in self.steps)
        ):
            raise TypeError("C04 recipe steps have the wrong strict type")
        if len({item.step_id for item in self.steps}) != len(self.steps):
            raise ValueError("C04 recipe step IDs repeat")
        if self.primitive_support_radius != 1:
            raise ValueError("C04 primitive support radius is not frozen")
        if (
            type(self.reference_phase_band) is not tuple
            or len(self.reference_phase_band) != 2
            or not all(
                type(item) is float and math.isfinite(item)
                for item in self.reference_phase_band
            )
            or self.reference_phase_band[0] >= self.reference_phase_band[1]
        ):
            raise ValueError("C04 reference phase band is invalid")
        if self.expected_shell_rank != 1:
            raise ValueError("C04 expected shell rank is not frozen")
        if (
            type(self.response_momenta) is not tuple
            or len(self.response_momenta) != 2
            or not all(
                type(item) is float and math.isfinite(item)
                for item in self.response_momenta
            )
        ):
            raise ValueError("C04 response momenta are not frozen")
        for field in ("canonical_structure", "source_injection", "readout"):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        for field in (
            "actual_effect_digest",
            "ablated_effect_digest",
            "recipe_sha",
        ):
            _sha(getattr(self, field), field)


def c04_canonical_angle_recipe_payload(
    recipe: C04CanonicalAngleRecipe,
) -> dict[str, object]:
    _exact_record(recipe, C04CanonicalAngleRecipe, "C04 canonical-angle recipe")
    return {
        "recipe_schema_version": recipe.recipe_schema_version,
        "recipe_id": recipe.recipe_id,
        "channel_order": list(recipe.channel_order),
        "alpha": recipe.alpha,
        "beta": recipe.beta,
        "steps": [
            {
                **c04_local_shear_step_payload(step),
                "step_sha": step.step_sha,
            }
            for step in recipe.steps
        ],
        "primitive_support_radius": recipe.primitive_support_radius,
        "reference_phase_band": list(recipe.reference_phase_band),
        "expected_shell_rank": recipe.expected_shell_rank,
        "response_momenta": list(recipe.response_momenta),
        "canonical_structure_sha": recipe.canonical_structure.tensor_sha,
        "source_injection_sha": recipe.source_injection.tensor_sha,
        "readout_sha": recipe.readout.tensor_sha,
        "actual_effect_digest": recipe.actual_effect_digest,
        "ablated_effect_digest": recipe.ablated_effect_digest,
    }


_C04_CHANNEL_ORDER = ("q0", "p0", "q1", "p1")
_C04_CHANNEL_INDEX = {
    channel: index for index, channel in enumerate(_C04_CHANNEL_ORDER)
}


def _c04_step(
    step_id: str,
    source_channel: str,
    destination_channel: str,
    *,
    offset: int,
    coefficient: float,
    target_conditioned: bool = False,
) -> C04LocalShearStep:
    provisional = C04LocalShearStep(
        step_schema_version=C04_LOCAL_SHEAR_STEP_SCHEMA_VERSION,
        step_id=step_id,
        source_channel=source_channel,
        destination_channel=destination_channel,
        offset=(offset,),
        coefficient=float(coefficient),
        target_conditioned=target_conditioned,
        step_sha="0" * 64,
    )
    return replace(
        provisional,
        step_sha=canonical_sha(c04_local_shear_step_payload(provisional)),
    )


def _c04_parallel_step(
    prefix: str,
    *,
    source_mode: int,
    destination_mode: int,
    offset: int,
    coefficient: float,
) -> tuple[C04LocalShearStep, ...]:
    if source_mode not in (0, 1) or destination_mode not in (0, 1):
        raise ValueError("C04 complex-mode index is not frozen")
    if source_mode == destination_mode:
        raise ValueError("C04 complex-mode shear must change modes")
    source_q = "q0" if source_mode == 0 else "q1"
    source_p = "p0" if source_mode == 0 else "p1"
    destination_q = "q0" if destination_mode == 0 else "q1"
    destination_p = "p0" if destination_mode == 0 else "p1"
    return (
        _c04_step(
            f"{prefix}.q",
            source_q,
            destination_q,
            offset=offset,
            coefficient=coefficient,
        ),
        _c04_step(
            f"{prefix}.p",
            source_p,
            destination_p,
            offset=offset,
            coefficient=coefficient,
        ),
    )


def _c04_mode_rotation_steps(
    angle: float,
    prefix: str,
) -> tuple[C04LocalShearStep, ...]:
    """Three-shear lift of one real rotation on the two complex modes."""

    tangent = float(math.tan(angle / 2.0))
    sine = float(math.sin(angle))
    return (
        *_c04_parallel_step(
            f"{prefix}.lower.0",
            source_mode=0,
            destination_mode=1,
            offset=0,
            coefficient=tangent,
        ),
        *_c04_parallel_step(
            f"{prefix}.upper",
            source_mode=1,
            destination_mode=0,
            offset=0,
            coefficient=-sine,
        ),
        *_c04_parallel_step(
            f"{prefix}.lower.1",
            source_mode=0,
            destination_mode=1,
            offset=0,
            coefficient=tangent,
        ),
    )


def _c04_reciprocal_swap_steps(
    prefix: str,
) -> tuple[C04LocalShearStep, ...]:
    """Local factor of D(k)=[[0,-exp(-ik)],[exp(ik),0]]."""

    return (
        *_c04_parallel_step(
            f"{prefix}.lower.0",
            source_mode=0,
            destination_mode=1,
            offset=1,
            coefficient=1.0,
        ),
        *_c04_parallel_step(
            f"{prefix}.upper",
            source_mode=1,
            destination_mode=0,
            offset=-1,
            coefficient=-1.0,
        ),
        *_c04_parallel_step(
            f"{prefix}.lower.1",
            source_mode=0,
            destination_mode=1,
            offset=1,
            coefficient=1.0,
        ),
    )


def _c04_inverse_steps(
    steps: tuple[C04LocalShearStep, ...],
    prefix: str,
) -> tuple[C04LocalShearStep, ...]:
    return tuple(
        _c04_step(
            f"{prefix}.{index:02d}",
            step.source_channel,
            step.destination_channel,
            offset=step.offset[0],
            coefficient=-step.coefficient,
            target_conditioned=step.target_conditioned,
        )
        for index, step in enumerate(reversed(steps))
    )


def _c04_quarter_turn_steps(
    mode: int,
    prefix: str,
    *,
    target_conditioned: bool = False,
) -> tuple[C04LocalShearStep, ...]:
    if mode not in (0, 1):
        raise ValueError("C04 quarter-turn mode is not frozen")
    q_channel = "q0" if mode == 0 else "q1"
    p_channel = "p0" if mode == 0 else "p1"
    return (
        _c04_step(
            f"{prefix}.lower.0",
            q_channel,
            p_channel,
            offset=0,
            coefficient=1.0,
            target_conditioned=target_conditioned,
        ),
        _c04_step(
            f"{prefix}.upper",
            p_channel,
            q_channel,
            offset=0,
            coefficient=-1.0,
            target_conditioned=target_conditioned,
        ),
        _c04_step(
            f"{prefix}.lower.1",
            q_channel,
            p_channel,
            offset=0,
            coefficient=1.0,
            target_conditioned=target_conditioned,
        ),
    )


def _c04_steps_from_angles(
    alpha: float,
    beta: float,
) -> tuple[C04LocalShearStep, ...]:
    d_steps = _c04_reciprocal_swap_steps("blind.d")
    blind = (
        *_c04_mode_rotation_steps(-alpha, "blind.r-minus-alpha"),
        *_c04_inverse_steps(d_steps, "blind.d-inverse"),
        *_c04_mode_rotation_steps(-beta, "blind.r-minus-beta"),
        *_c04_quarter_turn_steps(0, "blind.f.mode0"),
        *_c04_quarter_turn_steps(1, "blind.f.mode1.first"),
        *_c04_quarter_turn_steps(1, "blind.f.mode1.second"),
        *_c04_mode_rotation_steps(beta, "blind.r-beta"),
        *d_steps,
        *_c04_mode_rotation_steps(alpha, "blind.r-alpha"),
    )
    conditioned_left = (
        *_c04_quarter_turn_steps(
            1,
            "conditioned.c-left.first",
            target_conditioned=True,
        ),
        *_c04_quarter_turn_steps(
            1,
            "conditioned.c-left.second",
            target_conditioned=True,
        ),
    )
    conditioned_right = (
        *_c04_quarter_turn_steps(
            1,
            "conditioned.c-right.first",
            target_conditioned=True,
        ),
        *_c04_quarter_turn_steps(
            1,
            "conditioned.c-right.second",
            target_conditioned=True,
        ),
    )
    return (*conditioned_left, *blind, *conditioned_right)


def _c04_symbol_from_steps(
    steps: tuple[C04LocalShearStep, ...],
    momentum: float,
    branch: Literal["actual", "matched_ablated"],
) -> np.ndarray:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("C04 recipe branch is not frozen")
    if type(momentum) is not float or not math.isfinite(momentum):
        raise ValueError("C04 momentum must be finite fp64")
    matrix = np.eye(4, dtype=np.complex128)
    for step in steps:
        if branch == "matched_ablated" and step.target_conditioned:
            continue
        shear = np.eye(4, dtype=np.complex128)
        phase = complex(
            math.cos(momentum * step.offset[0]),
            math.sin(momentum * step.offset[0]),
        )
        source = _C04_CHANNEL_INDEX[step.source_channel]
        destination = _C04_CHANNEL_INDEX[step.destination_channel]
        shear[destination, source] += step.coefficient * phase
        matrix = shear @ matrix
    return matrix


def _c04_effect_digest(
    steps: tuple[C04LocalShearStep, ...],
    branch: Literal["actual", "matched_ablated"],
) -> str:
    """Hash the executed Laurent kernel, not merely recipe metadata."""

    if branch not in ("actual", "matched_ablated"):
        raise ValueError("C04 effect branch is not frozen")
    coefficients: dict[int, np.ndarray] = {0: np.eye(4, dtype=np.complex128)}
    for step in steps:
        if branch == "matched_ablated" and step.target_conditioned:
            continue
        source = _C04_CHANNEL_INDEX[step.source_channel]
        destination = _C04_CHANNEL_INDEX[step.destination_channel]
        previous = {
            offset: np.array(matrix, dtype=np.complex128, copy=True)
            for offset, matrix in coefficients.items()
        }
        updated = {
            offset: np.array(matrix, dtype=np.complex128, copy=True)
            for offset, matrix in previous.items()
        }
        for offset, matrix in previous.items():
            shifted = offset + step.offset[0]
            contribution = np.zeros((4, 4), dtype=np.complex128)
            contribution[destination] = step.coefficient * matrix[source]
            if shifted in updated:
                updated[shifted] += contribution
            else:
                updated[shifted] = contribution
        coefficients = updated
    support = tuple(sorted(coefficients))
    kernel = freeze_complex_tensor(
        np.stack(tuple(coefficients[offset] for offset in support), axis=0)
    )
    return canonical_sha(
        {
            "effect_schema_version": "v3m0.c04-laurent-effect.v1",
            "support_offsets": list(support),
            "kernel_tensor_sha": kernel.tensor_sha,
        }
    )


def _build_c04_canonical_angle_recipe_from_angles(
    alpha: float,
    beta: float,
) -> C04CanonicalAngleRecipe:
    if (
        type(alpha) is not float
        or not math.isfinite(alpha)
        or type(beta) is not float
        or not math.isfinite(beta)
    ):
        raise ValueError("C04 analytic angles must be finite fp64")
    steps = _c04_steps_from_angles(alpha, beta)
    canonical_structure = freeze_complex_tensor(
        np.kron(
            np.eye(2, dtype=np.complex128),
            np.asarray(((0.0, 1.0), (-1.0, 0.0)), dtype=np.complex128),
        )
    )
    inverse_sqrt_two = float(1.0 / math.sqrt(2.0))
    circular_transform = inverse_sqrt_two * np.asarray(
        (
            (1.0, 1.0j, 0.0, 0.0),
            (0.0, 0.0, 1.0, 1.0j),
            (1.0, -1.0j, 0.0, 0.0),
            (0.0, 0.0, 1.0, -1.0j),
        ),
        dtype=np.complex128,
    )
    source = circular_transform.conj().T[:, :2]
    readout = source.conj().T
    provisional = C04CanonicalAngleRecipe(
        recipe_schema_version=C04_CANONICAL_ANGLE_RECIPE_SCHEMA_VERSION,
        recipe_id=C04_CANONICAL_ANGLE_RECIPE_ID,
        channel_order=_C04_CHANNEL_ORDER,
        alpha=alpha,
        beta=beta,
        steps=steps,
        primitive_support_radius=1,
        reference_phase_band=(
            float(math.pi / 2.0 - 1.0 / 8.0),
            float(math.pi / 2.0 + 1.0 / 8.0),
        ),
        expected_shell_rank=1,
        response_momenta=(float(math.pi / 4.0), float(math.pi / 2.0)),
        canonical_structure=canonical_structure,
        source_injection=freeze_complex_tensor(source),
        readout=freeze_complex_tensor(readout),
        actual_effect_digest=_c04_effect_digest(steps, "actual"),
        ablated_effect_digest=_c04_effect_digest(
            steps,
            "matched_ablated",
        ),
        recipe_sha="0" * 64,
    )
    return replace(
        provisional,
        recipe_sha=canonical_sha(c04_canonical_angle_recipe_payload(provisional)),
    )


def build_c04_canonical_angle_recipe() -> C04CanonicalAngleRecipe:
    """Build the analytic, local C04 recipe frozen by the v3 erratum."""

    sum_angle = math.acos((math.sqrt(3.0) - 2.0) / 2.0)
    difference_angle = -5.0 * math.pi / 6.0
    alpha = float((sum_angle + difference_angle) / 4.0)
    beta = float((sum_angle - difference_angle) / 4.0)
    return _build_c04_canonical_angle_recipe_from_angles(alpha, beta)


def _verify_c04_canonical_angle_recipe(
    recipe: C04CanonicalAngleRecipe,
) -> C04CanonicalAngleRecipe:
    _exact_record(recipe, C04CanonicalAngleRecipe, "C04 canonical-angle recipe")
    recipe.__post_init__()
    expected = build_c04_canonical_angle_recipe()
    if recipe != expected:
        raise ValueError("C04 recipe differs from analytic replay")
    if recipe.recipe_sha != canonical_sha(c04_canonical_angle_recipe_payload(recipe)):
        raise ValueError("C04 recipe SHA mismatch")
    if recipe.actual_effect_digest != _c04_effect_digest(
        recipe.steps,
        "actual",
    ) or recipe.ablated_effect_digest != _c04_effect_digest(
        recipe.steps,
        "matched_ablated",
    ):
        raise ValueError("C04 executed effect digest mismatch")
    return recipe


def c04_canonical_angle_recipe_symbol(
    recipe: C04CanonicalAngleRecipe,
    momentum: float,
    branch: Literal["actual", "matched_ablated"],
) -> np.ndarray:
    """Evaluate the pure shear sequence; this is not a runtime authority."""

    verified = _verify_c04_canonical_angle_recipe(recipe)
    return _c04_symbol_from_steps(verified.steps, momentum, branch)


def c04_reciprocal_swap_symbol(momentum: float) -> np.ndarray:
    """Evaluate the three-shear D factor under executor offset convention."""

    if type(momentum) is not float or not math.isfinite(momentum):
        raise ValueError("C04 reciprocal-swap momentum must be finite fp64")
    matrix = np.eye(2, dtype=np.complex128)
    for source, destination, offset, coefficient in (
        (0, 1, 1, 1.0),
        (1, 0, -1, -1.0),
        (0, 1, 1, 1.0),
    ):
        shear = np.eye(2, dtype=np.complex128)
        shear[destination, source] += coefficient * complex(
            math.cos(momentum * offset),
            math.sin(momentum * offset),
        )
        matrix = shear @ matrix
    return matrix


def _finite_positive(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{field} must be finite and positive")
    return value


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    try:
        observed = frozenset(vars(value))
    except TypeError as exc:
        raise TypeError(f"{field} has no exact record body") from exc
    expected = frozenset(record_type.__dataclass_fields__)
    if observed != expected:
        raise ValueError(
            f"{field} fields are not exact: "
            f"missing={sorted(expected - observed)!r}, "
            f"unknown={sorted(observed - expected)!r}"
        )


def _preflight_tree(value: object, field: str) -> None:
    """Reject unknown recursive fields and cap a body before hashing."""

    used = 0
    active: set[int] = set()
    stack: list[tuple[object, str, int, bool]] = [(value, field, 0, False)]

    def charge(amount: int) -> None:
        nonlocal used
        used += amount
        if used > _GENERAL_BODY_CAP:
            raise ValueError(f"{field} serialized body exceeds resource cap")

    while stack:
        item, path, depth, leaving = stack.pop()
        identity = id(item)
        if leaving:
            active.remove(identity)
            continue
        if depth > _TREE_DEPTH_CAP:
            raise ValueError(f"{path} nesting exceeds resource cap")
        charge(32)
        item_type = type(item)
        if item is None or item_type is bool:
            continue
        if isinstance(item, Enum):
            stack.append((item.value, f"{path}.value", depth + 1, False))
            continue
        if item_type is str:
            encoded = item.encode("utf-8")
            if len(encoded) > _TEXT_CAP:
                raise ValueError(f"{path} text exceeds resource cap")
            charge(len(encoded))
            continue
        if item_type is int:
            charge(4 + item.bit_length() // 3)
            continue
        if item_type is float:
            if not math.isfinite(item):
                raise ValueError(f"{path} must be finite")
            charge(32)
            continue
        fields = getattr(item_type, "__dataclass_fields__", None)
        if fields is not None:
            if identity in active:
                raise ValueError(f"{path} contains a cyclic record")
            try:
                body = vars(item)
            except TypeError as exc:
                raise TypeError(f"{path} has no exact record body") from exc
            if frozenset(body) != frozenset(fields):
                raise ValueError(f"{path} contains missing or unknown fields")
            active.add(identity)
            stack.append((item, path, depth, True))
            for name in reversed(tuple(fields)):
                charge(len(name.encode("utf-8")))
                stack.append(
                    (
                        body[name],
                        f"{path}.{name}",
                        depth + 1,
                        False,
                    )
                )
            continue
        if item_type is tuple:
            if identity in active:
                raise ValueError(f"{path} contains a cyclic tuple")
            charge(8 * len(item))
            active.add(identity)
            stack.append((item, path, depth, True))
            for index in range(len(item) - 1, -1, -1):
                stack.append(
                    (
                        item[index],
                        f"{path}[{index}]",
                        depth + 1,
                        False,
                    )
                )
            continue
        raise TypeError(f"{path} contains unsupported type {item_type.__name__}")


def _wire(value: object) -> object:
    """Return a strict JSON tree, including nested evidence hashes."""

    if value is None or type(value) in (str, int, float, bool):
        return value
    if isinstance(value, Enum):
        return value.value
    if type(value) is tuple:
        return [_wire(item) for item in value]
    fields = getattr(type(value), "__dataclass_fields__", None)
    if fields is None:
        raise TypeError(f"unsupported evidence value {type(value).__name__}")
    _exact_record(value, type(value), type(value).__name__)
    return {name: _wire(getattr(value, name)) for name in fields}


def _payload_without_hash(value: object, hash_field: str) -> dict[str, object]:
    _preflight_tree(value, type(value).__name__)
    fields = getattr(type(value), "__dataclass_fields__", None)
    if fields is None or hash_field not in fields:
        raise TypeError("payload requires an exact hashed dataclass")
    return {name: _wire(getattr(value, name)) for name in fields if name != hash_field}


def _record_with_hash(
    value: object,
    payload_builder,
    hash_field: str,
) -> dict[str, object]:
    return {
        **payload_builder(value),
        hash_field: getattr(value, hash_field),
    }


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _finite_nonnegative(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{field} must be finite and non-negative")
    return value


def _optional_nonnegative(value: object, field: str) -> Optional[float]:
    if value is None:
        return None
    return _finite_nonnegative(value, field)


def _task11_response_types():
    """Load response wires lazily to keep the prestructure import DAG acyclic."""

    from . import response

    return response


@dataclass(frozen=True)
class ExpectedRankDeclaration:
    declaration_schema_version: str
    control_registry_sha: str
    control_registry_entry_sha: str
    control_id: Literal["full", "zero", "direct_sum"]
    expected_h_actual_rank: int
    expected_h_ablated_rank: int
    expected_curv_actual_rank: int
    expected_curv_ablated_rank: int
    parent_freeze_sha: str
    declaration_sha: str

    def __post_init__(self) -> None:
        if self.declaration_schema_version != EXPECTED_RANK_DECLARATION_SCHEMA_VERSION:
            raise ValueError("expected-rank declaration schema is not frozen")
        for name in (
            "control_registry_sha",
            "control_registry_entry_sha",
            "parent_freeze_sha",
            "declaration_sha",
        ):
            _sha(getattr(self, name), name)
        if self.control_id not in CONTROL_ORDER:
            raise ValueError("expected-rank control ID is not closed")
        for name in (
            "expected_h_actual_rank",
            "expected_h_ablated_rank",
            "expected_curv_actual_rank",
            "expected_curv_ablated_rank",
        ):
            _nonnegative_int(getattr(self, name), name)


@dataclass(frozen=True)
class CandidateAttemptAudit:
    attempt_schema_version: str
    control_registry_entry_sha: str
    fejer_order: int
    reference_outcome: EndpointReferenceOutcome
    shell_outcome: Optional[EndpointShellOutcome]
    paired_response_outcome: Optional[PairedResponseOutcome]
    attempt_sha: str

    def __post_init__(self) -> None:
        response = _task11_response_types()
        if self.attempt_schema_version != CANDIDATE_ATTEMPT_AUDIT_SCHEMA_VERSION:
            raise ValueError("candidate attempt schema is not frozen")
        _sha(self.control_registry_entry_sha, "control_registry_entry_sha")
        if type(self.fejer_order) is not int or self.fejer_order not in (
            *T_CANDIDATES,
            16384,
        ):
            raise ValueError("candidate attempt Fejer order is not closed")
        _exact_record(
            self.reference_outcome,
            response.EndpointReferenceOutcome,
            "reference_outcome",
        )
        if self.shell_outcome is not None:
            _exact_record(
                self.shell_outcome,
                response.EndpointShellOutcome,
                "shell_outcome",
            )
        if self.paired_response_outcome is not None:
            _exact_record(
                self.paired_response_outcome,
                response.PairedResponseOutcome,
                "paired_response_outcome",
            )
        if self.reference_outcome.status.defined != (self.shell_outcome is not None):
            raise ValueError("shell outcome presence differs from reference success")
        if self.shell_outcome is None:
            if self.paired_response_outcome is not None:
                raise ValueError("paired response cannot precede a shell outcome")
        elif self.shell_outcome.status.defined != (
            self.paired_response_outcome is not None
        ):
            raise ValueError("paired response presence differs from shell success")
        _sha(self.attempt_sha, "attempt_sha")


class ControlCandidateFailure(str, Enum):
    REFERENCE_FAILED = "reference_failed"
    SHELL_FAILED = "shell_failed"
    RESPONSE_FAILED = "response_failed"
    BRIDGE_FAILED = "bridge_failed"


def control_candidate_failure_reason(
    failure: ControlCandidateFailure,
) -> UndefinedReason:
    if type(failure) is not ControlCandidateFailure:
        raise TypeError("failure must be a ControlCandidateFailure")
    return {
        ControlCandidateFailure.REFERENCE_FAILED: (
            UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS
        ),
        ControlCandidateFailure.SHELL_FAILED: (
            UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS
        ),
        ControlCandidateFailure.RESPONSE_FAILED: (
            UndefinedReason.PAIRED_RESPONSE_FAILED
        ),
        ControlCandidateFailure.BRIDGE_FAILED: (UndefinedReason.RESPONSE_BRIDGE_FAILED),
    }[failure]


@dataclass(frozen=True)
class ControlCandidateOutcome:
    status: BlockStatus
    failure: Optional[ControlCandidateFailure]
    run_spec: ResponseRunSpec
    attempt_audit: CandidateAttemptAudit
    outcome_sha: str

    def __post_init__(self) -> None:
        response = _task11_response_types()
        if type(self.status) is not BlockStatus:
            raise TypeError("control candidate status has the wrong strict type")
        if (
            self.failure is not None
            and type(self.failure) is not ControlCandidateFailure
        ):
            raise TypeError("control candidate failure has the wrong enum type")
        _exact_record(self.run_spec, response.ResponseRunSpec, "run_spec")
        _exact_record(
            self.attempt_audit,
            CandidateAttemptAudit,
            "attempt_audit",
        )
        if self.status.defined != (self.failure is None):
            raise ValueError("control candidate status/failure presence mismatch")
        if self.failure is not None and self.status.reason is not (
            control_candidate_failure_reason(self.failure)
        ):
            raise ValueError("control candidate failure reason is not mechanical")
        if self.run_spec.fejer_order != self.attempt_audit.fejer_order:
            raise ValueError("control candidate run/attempt order mismatch")
        if (
            self.run_spec.control_registry_entry_sha
            != self.attempt_audit.control_registry_entry_sha
        ):
            raise ValueError("control candidate run/attempt registry mismatch")
        _sha(self.outcome_sha, "outcome_sha")


@dataclass(frozen=True)
class BranchSpectrumAudit:
    branch: Literal["actual", "matched_ablated"]
    declared_rank: int
    spectrum_shape: tuple[int, int]
    spectrum_order_id: Literal["k-major-singular-descending-v1"]
    raw_spectrum: tuple[float, ...]
    active_min: Optional[float]
    inactive_max: Optional[float]
    branch_sha: str

    def __post_init__(self) -> None:
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("spectrum branch is not closed")
        rank = _nonnegative_int(self.declared_rank, "declared_rank")
        if (
            type(self.spectrum_shape) is not tuple
            or len(self.spectrum_shape) != 2
            or any(type(item) is not int or item <= 0 for item in self.spectrum_shape)
        ):
            raise ValueError("spectrum_shape must contain two positive ints")
        if self.spectrum_order_id != "k-major-singular-descending-v1":
            raise ValueError("spectrum ordering is not frozen")
        if type(self.raw_spectrum) is not tuple:
            raise TypeError("raw_spectrum must be a tuple")
        values = tuple(
            _finite_nonnegative(item, f"raw_spectrum[{index}]")
            for index, item in enumerate(self.raw_spectrum)
        )
        n_k, n_singular = self.spectrum_shape
        if len(values) != n_k * n_singular:
            raise ValueError("raw_spectrum length differs from spectrum_shape")
        if rank > n_singular:
            raise ValueError("declared rank exceeds singular-value count")
        rows = tuple(
            values[index * n_singular : (index + 1) * n_singular]
            for index in range(n_k)
        )
        if any(row != tuple(sorted(row, reverse=True)) for row in rows):
            raise ValueError("raw singular values are not descending per k")
        active = tuple(value for row in rows for value in row[:rank])
        inactive = tuple(value for row in rows for value in row[rank:])
        expected_active = None if not active else float(min(active))
        expected_inactive = None if not inactive else float(max(inactive))
        if self.active_min != expected_active:
            raise ValueError("active_min differs from declared-rank partition")
        if self.inactive_max != expected_inactive:
            raise ValueError("inactive_max differs from declared-rank partition")
        _sha(self.branch_sha, "branch_sha")


@dataclass(frozen=True)
class PerControlReadoutSpectrumAudit:
    readout_kind: Literal["h", "curv"]
    control_registry_entry_sha: str
    expected_rank_declaration_sha: str
    fejer_order: int
    run_spec_sha: str
    paired_response_sha: str
    actual: BranchSpectrumAudit
    ablated: BranchSpectrumAudit
    actual_bridge_operator_error_upper: float
    ablated_bridge_operator_error_upper: float
    audit_sha: str

    def __post_init__(self) -> None:
        if self.readout_kind not in ("h", "curv"):
            raise ValueError("readout kind is not closed")
        for name in (
            "control_registry_entry_sha",
            "expected_rank_declaration_sha",
            "run_spec_sha",
            "paired_response_sha",
            "audit_sha",
        ):
            _sha(getattr(self, name), name)
        if type(self.fejer_order) is not int or self.fejer_order not in (
            *T_CANDIDATES,
            16384,
        ):
            raise ValueError("spectrum Fejer order is not closed")
        _exact_record(self.actual, BranchSpectrumAudit, "actual spectrum")
        _exact_record(self.ablated, BranchSpectrumAudit, "ablated spectrum")
        if self.actual.branch != "actual" or self.ablated.branch != "matched_ablated":
            raise ValueError("spectrum branch order is not canonical")
        _finite_nonnegative(
            self.actual_bridge_operator_error_upper,
            "actual_bridge_operator_error_upper",
        )
        _finite_nonnegative(
            self.ablated_bridge_operator_error_upper,
            "ablated_bridge_operator_error_upper",
        )


@dataclass(frozen=True)
class ReadoutAggregateCalibrationAudit:
    readout_kind: Literal["h", "curv"]
    per_control: tuple[PerControlReadoutSpectrumAudit, ...]
    scale_ref: float
    null_max: Optional[float]
    bridge_operator_error_max: float
    noise_ref: float
    signal_min: float
    tau_sig: float
    signal_noise_ratio: float
    raw_relative_gap: float
    absolute_signal_gate_passed: bool
    relative_gap_gate_passed: bool
    aggregate_sha: str

    def __post_init__(self) -> None:
        if self.readout_kind not in ("h", "curv"):
            raise ValueError("aggregate readout kind is not closed")
        if type(self.per_control) is not tuple or len(self.per_control) != len(
            CONTROL_ORDER
        ):
            raise ValueError("aggregate must retain exactly three controls")
        if not all(
            type(item) is PerControlReadoutSpectrumAudit for item in self.per_control
        ):
            raise TypeError("aggregate per_control has a wrong strict type")
        if any(item.readout_kind != self.readout_kind for item in self.per_control):
            raise ValueError("aggregate mixes readout kinds")
        for name in (
            "scale_ref",
            "noise_ref",
            "signal_min",
            "tau_sig",
            "signal_noise_ratio",
            "raw_relative_gap",
        ):
            _finite_positive(getattr(self, name), name)
        _optional_nonnegative(self.null_max, "null_max")
        _finite_nonnegative(
            self.bridge_operator_error_max,
            "bridge_operator_error_max",
        )
        for name in (
            "absolute_signal_gate_passed",
            "relative_gap_gate_passed",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a bool")
        _sha(self.aggregate_sha, "aggregate_sha")


@dataclass(frozen=True)
class ControlCandidateAudit:
    control_registry_entry: ControlRegistryEntry
    expected_rank_declaration: ExpectedRankDeclaration
    candidate_t: ControlCandidateOutcome
    comparison_2t: ControlCandidateOutcome
    readout_spectrum_audits: tuple[PerControlReadoutSpectrumAudit, ...]
    comparison_2t_readout_spectrum_audits: tuple[PerControlReadoutSpectrumAudit, ...]
    phase_separation: Optional[float]
    overlap_margin: Optional[float]
    projector_t2t_distance: Optional[float]
    passed: bool
    audit_sha: str

    def __post_init__(self) -> None:
        from .registry import ControlRegistryEntry

        _exact_record(
            self.control_registry_entry,
            ControlRegistryEntry,
            "control_registry_entry",
        )
        _exact_record(
            self.expected_rank_declaration,
            ExpectedRankDeclaration,
            "expected_rank_declaration",
        )
        _exact_record(self.candidate_t, ControlCandidateOutcome, "candidate_t")
        _exact_record(self.comparison_2t, ControlCandidateOutcome, "comparison_2t")
        for name in (
            "readout_spectrum_audits",
            "comparison_2t_readout_spectrum_audits",
        ):
            value = getattr(self, name)
            if type(value) is not tuple or not all(
                type(item) is PerControlReadoutSpectrumAudit for item in value
            ):
                raise TypeError(f"{name} must contain exact spectrum audits")
        for name in (
            "phase_separation",
            "overlap_margin",
            "projector_t2t_distance",
        ):
            _optional_nonnegative(getattr(self, name), name)
        if type(self.passed) is not bool:
            raise TypeError("control candidate passed must be a bool")
        _sha(self.audit_sha, "audit_sha")


@dataclass(frozen=True)
class WindowCandidateAudit:
    fejer_order: int
    control_audits: tuple[ControlCandidateAudit, ...]
    readout_aggregate_audits: tuple[ReadoutAggregateCalibrationAudit, ...]
    passed: bool
    audit_sha: str

    def __post_init__(self) -> None:
        if type(self.fejer_order) is not int or self.fejer_order not in T_CANDIDATES:
            raise ValueError("window candidate order is not frozen")
        if type(self.control_audits) is not tuple or len(self.control_audits) != len(
            CONTROL_ORDER
        ):
            raise ValueError("window candidate must retain exactly three controls")
        if not all(type(item) is ControlCandidateAudit for item in self.control_audits):
            raise TypeError("window candidate control audit has a wrong strict type")
        if type(self.readout_aggregate_audits) is not tuple or not all(
            type(item) is ReadoutAggregateCalibrationAudit
            for item in self.readout_aggregate_audits
        ):
            raise TypeError("window candidate aggregate audit has a wrong type")
        if type(self.passed) is not bool:
            raise TypeError("window candidate passed must be a bool")
        _sha(self.audit_sha, "audit_sha")


def expected_rank_declaration_payload(
    declaration: ExpectedRankDeclaration,
) -> dict[str, object]:
    _exact_record(declaration, ExpectedRankDeclaration, "expected rank declaration")
    return _payload_without_hash(declaration, "declaration_sha")


def candidate_attempt_audit_payload(
    audit: CandidateAttemptAudit,
) -> dict[str, object]:
    _exact_record(audit, CandidateAttemptAudit, "candidate attempt audit")
    return _payload_without_hash(audit, "attempt_sha")


def control_candidate_outcome_payload(
    outcome: ControlCandidateOutcome,
) -> dict[str, object]:
    _exact_record(outcome, ControlCandidateOutcome, "control candidate outcome")
    return _payload_without_hash(outcome, "outcome_sha")


def branch_spectrum_audit_payload(audit: BranchSpectrumAudit) -> dict[str, object]:
    _exact_record(audit, BranchSpectrumAudit, "branch spectrum audit")
    return _payload_without_hash(audit, "branch_sha")


def per_control_readout_spectrum_audit_payload(
    audit: PerControlReadoutSpectrumAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        PerControlReadoutSpectrumAudit,
        "per-control readout spectrum audit",
    )
    return _payload_without_hash(audit, "audit_sha")


def readout_aggregate_calibration_audit_payload(
    audit: ReadoutAggregateCalibrationAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        ReadoutAggregateCalibrationAudit,
        "readout aggregate calibration audit",
    )
    return _payload_without_hash(audit, "aggregate_sha")


def control_candidate_audit_payload(
    audit: ControlCandidateAudit,
) -> dict[str, object]:
    _exact_record(audit, ControlCandidateAudit, "control candidate audit")
    return _payload_without_hash(audit, "audit_sha")


def window_candidate_audit_payload(audit: WindowCandidateAudit) -> dict[str, object]:
    _exact_record(audit, WindowCandidateAudit, "window candidate audit")
    return _payload_without_hash(audit, "audit_sha")


_UPSTREAM_TASK12_WIRE_TYPES = (
    *_PARENT_WIRE_TYPES,
    *_REGISTRY_WIRE_TYPES,
    BlockStatus,
    ControlWindowProtocolEntry,
    WindowCalibrationProtocol,
    DirectionManifest,
    ResponseKGridManifest,
    BridgeKGridManifest,
    AblationPairSnapshot,
    AblationReplacement,
    AblationManifest,
    PrimitiveInterface,
    Primitive,
    LinearRealspaceFactory,
    BasisManifest,
    FrozenComplexTensor,
)


def _clone_task12_wire(
    value: object,
    *,
    local_record_types: tuple[type, ...],
    candidate_record_types: tuple[type, ...] = (),
    _builder=_make_exact_wire_cloner,
    _upstream_types=_UPSTREAM_TASK12_WIRE_TYPES,
) -> object:
    """Clone one authority wire without invoking user copy/deepcopy hooks."""

    ordered: list[type] = []
    candidate_atoms: list[type] = []
    for candidate_type in candidate_record_types:
        if hasattr(candidate_type, "__dataclass_fields__"):
            continue
        if issubclass(candidate_type, Enum) and candidate_type not in candidate_atoms:
            candidate_atoms.append(candidate_type)
    for record_type in (
        *_upstream_types,
        *local_record_types,
        *(
            item
            for item in candidate_record_types
            if hasattr(item, "__dataclass_fields__")
        ),
    ):
        if record_type not in ordered:
            ordered.append(record_type)
    clone = _builder(
        tuple(ordered),
        atomic_types=(UndefinedReason, *candidate_atoms),
    )
    return clone(value)


@dataclass(frozen=True)
class SelectedControlEvidenceRef:
    control_id: Literal["full", "zero", "direct_sum"]
    control_registry_entry_sha: str
    expected_rank_declaration_sha: str
    run_spec_sha: str
    paired_response_sha: str
    shell_manifest_sha: str
    comparison_2t_run_spec_sha: str
    comparison_2t_response_sha: str
    comparison_2t_shell_manifest_sha: str

    def __post_init__(self) -> None:
        if self.control_id not in CONTROL_ORDER:
            raise ValueError("selected control ID is not closed")
        for name in tuple(self.__dataclass_fields__)[1:]:
            _sha(getattr(self, name), name)


@dataclass(frozen=True)
class WindowThresholdSelection:
    selected_fejer_order: int
    h_scale_ref: float
    h_noise_ref: float
    h_signal_min: float
    h_tau_sig: float
    curv_scale_ref: float
    curv_noise_ref: float
    curv_signal_min: float
    curv_tau_sig: float
    selected_evidence_refs: tuple[SelectedControlEvidenceRef, ...]
    selection_sha: str

    def __post_init__(self) -> None:
        if (
            type(self.selected_fejer_order) is not int
            or self.selected_fejer_order not in T_CANDIDATES
        ):
            raise ValueError("selected Fejer order is not a candidate")
        for name in (
            "h_scale_ref",
            "h_noise_ref",
            "h_signal_min",
            "h_tau_sig",
            "curv_scale_ref",
            "curv_noise_ref",
            "curv_signal_min",
            "curv_tau_sig",
        ):
            _finite_positive(getattr(self, name), name)
        if type(self.selected_evidence_refs) is not tuple:
            raise TypeError("selected_evidence_refs must be a tuple")
        if (
            tuple(item.control_id for item in self.selected_evidence_refs)
            != CONTROL_ORDER
        ):
            raise ValueError("selected_evidence_refs are not in registry order")
        if not all(
            type(item) is SelectedControlEvidenceRef
            for item in self.selected_evidence_refs
        ):
            raise TypeError("selected_evidence_refs has a wrong record type")
        _sha(self.selection_sha, "selection_sha")


@dataclass(frozen=True)
class WindowThresholdCalibrationManifest:
    calibration_schema_version: str
    control_registry: ClosedControlRegistry
    window_protocol: WindowCalibrationProtocol
    candidate_audits: tuple[WindowCandidateAudit, ...]
    calibration_manifest_sha: str

    def __post_init__(self) -> None:
        if (
            self.calibration_schema_version
            != WINDOW_THRESHOLD_CALIBRATION_SCHEMA_VERSION
        ):
            raise ValueError("calibration manifest schema is not frozen")
        if type(self.control_registry) is not ClosedControlRegistry:
            raise TypeError("control_registry has the wrong strict type")
        if type(self.window_protocol) is not WindowCalibrationProtocol:
            raise TypeError("window_protocol has the wrong strict type")
        if type(self.candidate_audits) is not tuple:
            raise TypeError("candidate_audits must be a tuple")
        if not all(
            type(item) is WindowCandidateAudit for item in self.candidate_audits
        ):
            raise TypeError(
                "candidate_audits must contain exact WindowCandidateAudit records"
            )
        _sha(self.calibration_manifest_sha, "calibration_manifest_sha")


@dataclass(frozen=True)
class WindowCalibrationOutcome:
    status: BlockStatus
    manifest: WindowThresholdCalibrationManifest
    selection: Optional[WindowThresholdSelection]
    outcome_sha: str

    def __post_init__(self) -> None:
        if type(self.status) is not BlockStatus:
            raise TypeError("status has the wrong strict type")
        if type(self.manifest) is not WindowThresholdCalibrationManifest:
            raise TypeError("manifest has the wrong strict type")
        if self.selection is not None and (
            type(self.selection) is not WindowThresholdSelection
        ):
            raise TypeError("selection has the wrong strict type")
        if self.status.defined != (self.selection is not None):
            raise ValueError("calibration status/selection presence mismatch")
        if not self.status.defined and (
            self.status.reason is not UndefinedReason.WINDOW_UNRESOLVED
        ):
            raise ValueError("undefined calibration has the wrong reason")
        _sha(self.outcome_sha, "outcome_sha")


def window_threshold_selection_payload(
    selection: WindowThresholdSelection,
) -> dict[str, object]:
    _exact_record(
        selection,
        WindowThresholdSelection,
        "window threshold selection",
    )
    return _payload_without_hash(selection, "selection_sha")


def window_threshold_calibration_manifest_payload(
    manifest: WindowThresholdCalibrationManifest,
) -> dict[str, object]:
    _exact_record(
        manifest,
        WindowThresholdCalibrationManifest,
        "window threshold calibration manifest",
    )
    return _payload_without_hash(manifest, "calibration_manifest_sha")


def window_calibration_outcome_payload(
    outcome: WindowCalibrationOutcome,
) -> dict[str, object]:
    _exact_record(
        outcome,
        WindowCalibrationOutcome,
        "window calibration outcome",
    )
    return _payload_without_hash(outcome, "outcome_sha")


class VerifiedWindowThresholdCalibration:
    """Opaque successful Task 11 calibration capability."""

    __slots__ = ("__outcome", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        outcome: WindowCalibrationOutcome,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("VerifiedWindowThresholdCalibration is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedWindowThresholdCalibration__outcome",
            outcome,
        )
        object.__setattr__(
            self,
            "_VerifiedWindowThresholdCalibration__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedWindowThresholdCalibration__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("calibration authority is immutable")

    @property
    def outcome(self) -> WindowCalibrationOutcome:
        return _reverify_verified_window_threshold_calibration(self).outcome

    @property
    def manifest_sha(self) -> str:
        return self.outcome.manifest.calibration_manifest_sha

    @property
    def selection(self) -> WindowThresholdSelection:
        selection = self.outcome.selection
        if selection is None:
            raise ValueError("successful calibration lost its selection")
        return selection


@dataclass(frozen=True)
class _CalibrationView:
    outcome: WindowCalibrationOutcome
    registry: VerifiedControlRegistry
    protocol: VerifiedWindowCalibrationProtocol


@dataclass(frozen=True)
class _CalibrationAuthority:
    outcome: WindowCalibrationOutcome
    registry: VerifiedControlRegistry
    protocol: VerifiedWindowCalibrationProtocol
    digest: str
    seal: str


_CALIBRATION_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedWindowThresholdCalibration],
        _CalibrationAuthority,
    ],
] = {}
_CALIBRATION_LOCK = threading.RLock()


def _validate_response_run_spec_body(
    spec: ResponseRunSpec,
    protocol_body: WindowCalibrationProtocol,
    registry_body: ClosedControlRegistry,
):
    """Replay a run spec against already-reverified protocol/registry bodies.

    Calling the public response verifier once per T/control would recursively
    reverify the same live Parent 36 times.  The enclosing calibration verifier
    has already reverified those two capabilities, so this performs the same
    closed-body checks without weakening the authority boundary.
    """

    response = _task11_response_types()
    response._preflight_run_spec(spec)
    spec.__post_init__()
    if spec.run_spec_schema_version != response.RESPONSE_RUN_SPEC_SCHEMA_VERSION:
        raise ValueError("unexpected response run spec schema")
    if spec.window_protocol_sha != protocol_body.protocol_sha:
        raise ValueError("run spec window protocol binding mismatch")
    protocol_matches = tuple(
        item
        for item in protocol_body.control_entries
        if item.control_registry_entry_sha == spec.control_registry_entry_sha
    )
    registry_matches = tuple(
        item
        for item in registry_body.entries
        if item.entry_sha == spec.control_registry_entry_sha
    )
    if len(protocol_matches) != 1 or len(registry_matches) != 1:
        raise ValueError("run spec registry entry binding is not unique")
    protocol_entry = protocol_matches[0]
    registry_entry = registry_matches[0]
    response.verify_basis_manifest(spec.source_basis)
    response.verify_basis_manifest(spec.readout_basis)
    if (
        spec.source_basis != registry_entry.source_basis
        or spec.readout_basis != registry_entry.readout_basis
        or spec.state_schema_id != registry_entry.source_basis.state_schema_id
        or spec.channel_order != registry_entry.source_basis.channel_order
        or registry_entry.readout_basis.state_schema_id != spec.state_schema_id
        or registry_entry.readout_basis.channel_order != spec.channel_order
    ):
        raise ValueError("run spec source/readout basis binding mismatch")
    if (
        spec.spatial_shape != protocol_entry.source_readout_bridge_grid.spatial_shape
        or spec.response_grid != protocol_entry.response_grid
        or spec.source_readout_bridge_grid != protocol_entry.source_readout_bridge_grid
        or spec.source_readout_bridge_steps
        != protocol_entry.source_readout_bridge_steps
        or spec.source_readout_bridge_grid.torus_denominators != spec.spatial_shape
        or spec.source_readout_bridge_grid.spatial_shape != spec.spatial_shape
    ):
        raise ValueError("run spec grid/bridge binding mismatch")
    source_count = len(spec.source_basis.vectors_wire)
    trials = frozen_tensor_array(spec.source_trial_vectors)
    if trials.shape != (source_count, source_count) or not np.array_equal(
        trials,
        np.eye(source_count, dtype=np.complex128),
    ):
        raise ValueError("source trials are not the frozen complete identity frame")
    response.preflight_source_bridge_work(
        n_k=len(spec.source_readout_bridge_grid.reciprocal_indices),
        n_trial=source_count,
        steps=spec.source_readout_bridge_steps,
    )
    expected_id = (
        f"v3m0.response-run.{registry_entry.control_id}.T{spec.fejer_order}.v1"
    )
    if spec.run_spec_id != expected_id:
        raise ValueError("run spec ID is not the canonical derivation")
    if spec.bridge_tolerance != BRIDGE_TOLERANCE:
        raise ValueError("run spec bridge tolerance is not frozen")
    if spec.spec_sha != canonical_sha(response.response_run_spec_payload(spec)):
        raise ValueError("control candidate run spec self-hash mismatch")
    return protocol_entry, registry_entry


def _validate_raw_window_protocol_body(
    protocol_body: WindowCalibrationProtocol,
    registry_body: ClosedControlRegistry,
) -> None:
    _exact_record(
        protocol_body,
        WindowCalibrationProtocol,
        "window calibration protocol",
    )
    protocol_body.__post_init__()
    if (
        protocol_body.protocol_schema_version
        != WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION
        or protocol_body.control_registry_sha != registry_body.registry_sha
        or protocol_body.parent_freeze_sha != registry_body.parent_freeze_sha
        or protocol_body.protocol_sha
        != canonical_sha(window_calibration_protocol_payload(protocol_body))
    ):
        raise ValueError("window protocol differs from the live registry")
    if (
        tuple(item.control_id for item in protocol_body.control_entries)
        != CONTROL_ORDER
    ):
        raise ValueError("window protocol controls are not canonical")
    for protocol_entry, registry_entry in zip(
        protocol_body.control_entries,
        registry_body.entries,
    ):
        if (
            protocol_entry.control_registry_entry_sha != registry_entry.entry_sha
            or protocol_entry.entry_sha
            != canonical_sha(control_window_protocol_entry_payload(protocol_entry))
        ):
            raise ValueError("window protocol entry differs from the live registry")
    verify_window_protocol_thresholds(
        t_candidates=protocol_body.t_candidates,
        phase_grid_protocol_id=protocol_body.phase_grid_protocol_id,
        phase_separation_protocol_id=protocol_body.phase_separation_protocol_id,
        participation_min_required=protocol_body.participation_min_required,
        overlap_margin_required=protocol_body.overlap_margin_required,
        loop_residual_max=protocol_body.loop_residual_max,
        projector_residual_max=protocol_body.projector_residual_max,
    )


def _validate_shell_attempt_and_manifest_summaries(
    shell_outcome,
    protocol_body: WindowCalibrationProtocol,
) -> None:
    """Reject re-signed shell summaries that differ from their point records."""

    shell_spec = shell_outcome.attempt_audit.shell_spec
    direction = shell_spec.response_grid.direction_manifest
    expected_keys = tuple(
        (path_id, position, reciprocal_index)
        for path_id, path in zip(direction.path_ids, direction.ordered_paths)
        for position, reciprocal_index in enumerate(path)
    )
    attempt_keys = tuple(
        (
            item.momentum_path_id,
            item.momentum_path_position,
            item.reciprocal_index,
        )
        for item in shell_outcome.attempt_audit.point_attempts
    )
    if attempt_keys != expected_keys[: len(attempt_keys)]:
        raise ValueError("endpoint shell attempt points are missing or reordered")
    shell = shell_outcome.shell
    if shell is None:
        return
    if attempt_keys != expected_keys:
        raise ValueError("successful endpoint shell attempt does not cover the grid")
    point_keys = tuple(
        (
            item.momentum_path_id,
            item.momentum_path_position,
            item.reciprocal_index,
        )
        for item in shell.point_audits
    )
    if point_keys != expected_keys:
        raise ValueError("successful endpoint shell does not cover the canonical grid")
    if (
        shell.shell_spec != shell_spec
        or shell.shell_phases != tuple(item.shell_phase for item in shell.point_audits)
        or shell.ambiguous
    ):
        raise ValueError("endpoint shell body differs from its attempt/point records")
    if any(
        item.rank != shell_spec.endpoint_reference_projector.rank
        for item in shell.point_audits
    ):
        raise ValueError("endpoint shell point rank differs from the reference")
    gaps = tuple(
        item.nearest_competitor_gap
        for item in shell.point_audits
        if item.nearest_competitor_gap is not None
    )
    runners = tuple(
        item.runner_up_overlap
        for item in shell.point_audits
        if item.runner_up_overlap is not None
    )
    predecessors = tuple(
        item.predecessor_overlap
        for item in shell.point_audits
        if item.predecessor_overlap is not None
    )
    margins = tuple(
        (
            item.reference_overlap
            if item.predecessor_overlap is None
            else item.predecessor_overlap
        )
        - item.runner_up_overlap
        for item in shell.point_audits
        if item.runner_up_overlap is not None
    )
    loops = tuple(
        item.loop_residual
        for item in shell.point_audits
        if item.loop_residual is not None
    )
    expected = (
        max(item.hermitian_residual for item in shell.point_audits),
        max(item.idempotent_residual for item in shell.point_audits),
        max(item.g_invariance_residual for item in shell.point_audits),
        max(item.eigenphase_residual for item in shell.point_audits),
        min(item.participation for item in shell.point_audits),
        None if not gaps else min(gaps),
        min(item.reference_overlap for item in shell.point_audits),
        None if not runners else max(runners),
        None if not predecessors else min(predecessors),
        None if not margins else min(margins),
        None if not loops else max(loops),
    )
    observed = (
        shell.hermitian_residual_max,
        shell.idempotent_residual_max,
        shell.g_invariance_residual_max,
        shell.eigenphase_residual_max,
        shell.participation_min,
        shell.nearest_competitor_gap_min,
        shell.reference_overlap_min,
        shell.runner_up_overlap_max,
        shell.predecessor_overlap_min,
        shell.overlap_margin_min,
        shell.loop_residual_max,
    )
    if observed != expected:
        raise ValueError("endpoint shell summaries differ from point evidence")
    if shell_outcome.attempt_audit.loop_residual_max_observed != (
        None if not loops else max(loops)
    ):
        raise ValueError("endpoint shell attempt loop summary mismatch")
    if (
        max(
            shell.hermitian_residual_max,
            shell.idempotent_residual_max,
            shell.g_invariance_residual_max,
            shell.eigenphase_residual_max,
        )
        > protocol_body.projector_residual_max
        or shell.participation_min < protocol_body.participation_min_required
        or (
            shell.nearest_competitor_gap_min is not None
            and shell.nearest_competitor_gap_min
            < phase_separation_min(shell_spec.candidate_fejer_order)
        )
        or (
            shell.overlap_margin_min is not None
            and shell.overlap_margin_min < protocol_body.overlap_margin_required
        )
        or (
            shell.loop_residual_max is not None
            and shell.loop_residual_max > protocol_body.loop_residual_max
        )
    ):
        raise ValueError("successful endpoint shell violates a frozen hard gate")


def _validate_reference_attempt_and_selection(
    reference,
    protocol_body: WindowCalibrationProtocol,
) -> None:
    """Replay the reference candidate table and its first-error selection."""

    response = _task11_response_types()
    spec = reference.reference_spec
    attempt = reference.attempt_audit
    if (
        spec.reference_spec_schema_version
        != response.ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION
        or attempt.attempt_schema_version
        != response.ENDPOINT_REFERENCE_ATTEMPT_SCHEMA_VERSION
        or attempt.expected_shell_rank != spec.expected_shell_rank
        or attempt.expected_shell_rank_source_id != spec.expected_shell_rank_source_id
    ):
        raise ValueError("endpoint reference attempt differs from its frozen spec")

    phases = attempt.candidate_phases
    participations = attempt.candidate_participations

    def phase_distance(first: float, second: float) -> float:
        return abs(math.atan2(math.sin(first - second), math.cos(first - second)))

    expected_runner_ups = tuple(
        (
            None
            if len(participations) == 1
            else max(
                value
                for other_index, value in enumerate(participations)
                if other_index != index
            )
        )
        for index in range(len(participations))
    )
    expected_competitor_gaps = tuple(
        (
            None
            if len(phases) == 1
            else min(
                phase_distance(phase, other)
                for other_index, other in enumerate(phases)
                if other_index != index
            )
        )
        for index, phase in enumerate(phases)
    )
    if (
        attempt.runner_up_overlaps != expected_runner_ups
        or attempt.observed_competitor_gaps != expected_competitor_gaps
    ):
        raise ValueError("endpoint reference competitor summaries are not mechanical")

    selected_index: Optional[int] = None
    expected_failure = None
    if not phases:
        expected_failure = response.EndpointReferenceFailure.PHASE_BAND_EMPTY
    elif any(
        phase_distance(first, second) < phase_grid_step(spec.candidate_fejer_order)
        for index, first in enumerate(phases)
        for second in phases[index + 1 :]
    ):
        expected_failure = response.EndpointReferenceFailure.PHASE_BAND_NONUNIQUE
    else:
        selected_index = min(
            range(len(phases)),
            key=lambda index: (-participations[index], phases[index]),
        )
        if attempt.candidate_ranks[selected_index] != spec.expected_shell_rank:
            expected_failure = response.EndpointReferenceFailure.RANK_MISMATCH
        elif participations[selected_index] < protocol_body.participation_min_required:
            expected_failure = response.EndpointReferenceFailure.PARTICIPATION_FAILED
        elif (
            expected_runner_ups[selected_index] is not None
            and participations[selected_index] - expected_runner_ups[selected_index]
            < protocol_body.overlap_margin_required
        ):
            expected_failure = response.EndpointReferenceFailure.RUNNER_UP_MARGIN_FAILED
        elif (
            max(
                attempt.hermitian_residuals[selected_index],
                attempt.idempotent_residuals[selected_index],
                attempt.g_invariance_residuals[selected_index],
                attempt.eigenphase_residuals[selected_index],
            )
            > protocol_body.projector_residual_max
        ):
            expected_failure = response.EndpointReferenceFailure.PROJECTOR_INVALID

    if reference.failure is not expected_failure:
        raise ValueError("endpoint reference failure is not mechanical")
    if expected_failure is None:
        selected = reference.reference
        if selected is None or selected_index is None:
            raise ValueError("successful endpoint reference lost its selection")
        if (
            selected.reference_schema_version
            != response.ENDPOINT_REFERENCE_SCHEMA_VERSION
            or selected.reference_phase != phases[selected_index]
            or selected.rank != attempt.candidate_ranks[selected_index]
        ):
            raise ValueError("endpoint reference selection differs from candidates")


def _validate_response_attempt_graph(
    audit: CandidateAttemptAudit,
    run_spec: ResponseRunSpec,
    protocol_body: WindowCalibrationProtocol,
    registry_entry: ControlRegistryEntry,
    protocol_entry: ControlWindowProtocolEntry,
) -> None:
    """Validate the exact typed first-error graph without hydrating authorities."""

    response = _task11_response_types()
    audit.__post_init__()
    reference = audit.reference_outcome
    response._preflight_reference_outcome_body(reference)
    if reference.reference_spec.reference_spec_sha != canonical_sha(
        response.endpoint_reference_spec_payload(reference.reference_spec)
    ):
        raise ValueError("endpoint reference spec self-hash mismatch")
    if reference.attempt_audit.attempt_sha != canonical_sha(
        response.endpoint_reference_attempt_audit_payload(reference.attempt_audit)
    ):
        raise ValueError("endpoint reference attempt self-hash mismatch")
    if reference.reference is not None and (
        reference.reference.reference_sha
        != canonical_sha(
            response.endpoint_reference_projector_payload(reference.reference)
        )
    ):
        raise ValueError("endpoint reference projector self-hash mismatch")
    if reference.outcome_sha != canonical_sha(
        response.endpoint_reference_outcome_payload(reference)
    ):
        raise ValueError("endpoint reference outcome self-hash mismatch")
    if reference.attempt_audit.reference_spec != reference.reference_spec:
        raise ValueError("endpoint reference attempt/spec body mismatch")
    if reference.reference_spec.control_registry_entry.entry_sha != (
        audit.control_registry_entry_sha
    ):
        raise ValueError("endpoint reference is bound to another registry entry")
    if reference.reference_spec.candidate_fejer_order != audit.fejer_order:
        raise ValueError("endpoint reference order differs from candidate attempt")
    if not reference.status.defined and (
        reference.status.reason is not UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS
    ):
        raise ValueError("endpoint reference has the wrong undefined reason")
    reference_spec = reference.reference_spec
    _validate_reference_attempt_and_selection(reference, protocol_body)
    if (
        reference_spec.window_protocol_sha != protocol_body.protocol_sha
        or reference_spec.control_registry_entry != registry_entry
        or reference_spec.actual_factory_sha != registry_entry.factory_sha
        or reference_spec.reference_reciprocal_index
        != protocol_entry.reference_reciprocal_index
        or reference_spec.preregistered_phase_bands
        != protocol_entry.preregistered_phase_bands
        or reference_spec.expected_shell_rank != protocol_entry.expected_shell_rank
        or reference_spec.expected_shell_rank_source_id
        != protocol_entry.expected_shell_rank_source_id
    ):
        raise ValueError("endpoint reference differs from the closed protocol entry")
    if reference.reference is not None and (
        reference.reference.control_registry_entry_sha != registry_entry.entry_sha
        or reference.reference.actual_transition_sha
        != reference_spec.actual_transition_sha
        or reference.reference.actual_dynamics_certificate_sha
        != reference_spec.actual_dynamics_certificate_sha
        or reference.reference.reference_reciprocal_index
        != reference_spec.reference_reciprocal_index
        or reference.reference.rank != reference_spec.expected_shell_rank
    ):
        raise ValueError("endpoint reference projector binding mismatch")
    if reference.reference is not None:
        frozen_tensor_array(reference.reference.projector)

    shell = audit.shell_outcome
    if shell is None:
        if audit.attempt_sha != canonical_sha(candidate_attempt_audit_payload(audit)):
            raise ValueError("candidate attempt self-hash mismatch")
        return
    response._preflight_shell_outcome_body(shell)
    _validate_shell_attempt_and_manifest_summaries(shell, protocol_body)
    if shell.reference_outcome != reference:
        raise ValueError("endpoint shell lost its reference outcome")
    shell_spec = shell.attempt_audit.shell_spec
    if shell_spec.shell_spec_sha != canonical_sha(
        response.endpoint_shell_spec_payload(shell_spec)
    ):
        raise ValueError("endpoint shell spec self-hash mismatch")
    if shell.attempt_audit.attempt_sha != canonical_sha(
        response.endpoint_shell_attempt_audit_payload(shell.attempt_audit)
    ):
        raise ValueError("endpoint shell attempt self-hash mismatch")
    if shell.shell is not None and shell.shell.shell_manifest_sha != canonical_sha(
        response.endpoint_shell_manifest_payload(shell.shell)
    ):
        raise ValueError("endpoint shell manifest self-hash mismatch")
    if shell.shell is not None:
        frozen_tensor_array(shell.shell.shell_projectors)
        if (
            shell.shell.actual_factory_sha != reference_spec.actual_factory_sha
            or shell.shell.actual_transition_sha != reference_spec.actual_transition_sha
            or shell.shell.actual_dynamics_certificate_sha
            != reference_spec.actual_dynamics_certificate_sha
        ):
            raise ValueError("endpoint shell actual evidence binding mismatch")
    if shell.outcome_sha != canonical_sha(
        response.endpoint_shell_outcome_payload(shell)
    ):
        raise ValueError("endpoint shell outcome self-hash mismatch")
    if not shell.status.defined and (
        shell.status.reason is not UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS
    ):
        raise ValueError("endpoint shell has the wrong undefined reason")
    if (
        shell_spec.window_protocol_sha != protocol_body.protocol_sha
        or shell_spec.control_registry_entry != registry_entry
        or shell_spec.response_grid != protocol_entry.response_grid
        or shell_spec.preregistered_phase_bands
        != protocol_entry.preregistered_phase_bands
        or shell_spec.candidate_fejer_order != run_spec.fejer_order
        or shell_spec.endpoint_reference_projector != reference.reference
    ):
        raise ValueError("endpoint shell differs from reference/protocol binding")

    paired = audit.paired_response_outcome
    if paired is not None:
        response._preflight_paired_outcome_body(paired)
        response._verify_paired_declared_hashes(paired)
        if paired.attempt_audit.shell_outcome != shell:
            raise ValueError("paired response lost its endpoint shell outcome")
        if (
            paired.attempt_audit.window_protocol != protocol_body
            or paired.attempt_audit.run_spec != run_spec
        ):
            raise ValueError("paired response differs from protocol/run spec binding")
        paired_attempt = paired.attempt_audit
        for transition in (
            paired_attempt.actual_transition,
            paired_attempt.ablated_transition,
        ):
            if transition.transition_sha != canonical_sha(
                response.measured_transition_payload(transition)
            ):
                raise ValueError("paired transition self-hash mismatch")
        if (
            paired_attempt.actual_transition.factory_sha
            != paired_attempt.actual_factory_sha
            or paired_attempt.actual_transition.factory_role != "actual"
            or paired_attempt.ablated_transition.factory_sha
            != paired_attempt.ablated_factory_sha
            or paired_attempt.ablated_transition.factory_role != "matched_ablated"
        ):
            raise ValueError("paired transition/factory branch binding mismatch")
        for certificate, transition in (
            (
                paired_attempt.actual_dynamics_certificate,
                paired_attempt.actual_transition,
            ),
            (
                paired_attempt.ablated_dynamics_certificate,
                paired_attempt.ablated_transition,
            ),
        ):
            if (
                certificate.transition != transition
                or certificate.certificate_sha
                != canonical_sha(response.dynamics_certificate_payload(certificate))
            ):
                raise ValueError("paired dynamics certificate self-hash mismatch")
        if (
            paired_attempt.actual_factory_sha != reference_spec.actual_factory_sha
            or paired_attempt.actual_transition.transition_sha
            != reference_spec.actual_transition_sha
            or paired_attempt.actual_dynamics_certificate.certificate_sha
            != reference_spec.actual_dynamics_certificate_sha
            or shell.shell is None
            or shell.shell.dt != paired_attempt.actual_transition.dt
        ):
            raise ValueError("paired actual branch differs from endpoint reference")
        for branch_attempt in (
            paired_attempt.actual_branch_attempt,
            paired_attempt.ablated_branch_attempt,
        ):
            if branch_attempt is None:
                continue
            if branch_attempt.response_values is not None:
                frozen_tensor_array(branch_attempt.response_values)
            if branch_attempt.bridge_audit is not None:
                response.verify_source_readout_bridge_audit_body(
                    branch_attempt.bridge_audit,
                    run_spec,
                    registry_entry,
                )
        if paired.paired_response is not None and (
            paired.paired_response.run_spec != run_spec
            or paired.paired_response.shell_manifest != shell.shell
        ):
            raise ValueError("paired response payload lost its run/shell binding")
        if paired.paired_response is not None:
            payload = paired.paired_response
            if (
                payload.qualification_sha != paired_attempt.qualification_sha
                or payload.actual_dynamics_certificate
                != paired_attempt.actual_dynamics_certificate
                or payload.ablated_dynamics_certificate
                != paired_attempt.ablated_dynamics_certificate
            ):
                raise ValueError("paired payload differs from attempt evidence")
            for branch_response in (payload.actual, payload.ablated):
                frozen_tensor_array(branch_response.values)
                response.verify_source_readout_bridge_audit_body(
                    branch_response.bridge_audit,
                    run_spec,
                    registry_entry,
                )
    if audit.attempt_sha != canonical_sha(candidate_attempt_audit_payload(audit)):
        raise ValueError("candidate attempt self-hash mismatch")


def _expected_control_candidate_failure(
    audit: CandidateAttemptAudit,
) -> Optional[ControlCandidateFailure]:
    response = _task11_response_types()
    if not audit.reference_outcome.status.defined:
        return ControlCandidateFailure.REFERENCE_FAILED
    if audit.shell_outcome is None:
        raise ValueError("successful reference lost its shell outcome")
    if not audit.shell_outcome.status.defined:
        return ControlCandidateFailure.SHELL_FAILED
    paired = audit.paired_response_outcome
    if paired is None:
        raise ValueError("successful shell lost its paired response outcome")
    if paired.status.defined:
        return None
    if paired.failure in (
        response.PairedResponseFailure.ACTUAL_BRIDGE_FAILED,
        response.PairedResponseFailure.ABLATED_BRIDGE_FAILED,
    ):
        return ControlCandidateFailure.BRIDGE_FAILED
    return ControlCandidateFailure.RESPONSE_FAILED


def _validate_control_candidate_outcome(
    outcome: ControlCandidateOutcome,
    protocol_body: WindowCalibrationProtocol,
    registry_body: ClosedControlRegistry,
) -> None:
    outcome.__post_init__()
    protocol_entry, registry_entry = _validate_response_run_spec_body(
        outcome.run_spec,
        protocol_body,
        registry_body,
    )
    _validate_response_attempt_graph(
        outcome.attempt_audit,
        outcome.run_spec,
        protocol_body,
        registry_entry,
        protocol_entry,
    )
    expected_failure = _expected_control_candidate_failure(outcome.attempt_audit)
    if outcome.failure is not expected_failure:
        raise ValueError("control candidate failure differs from first error")
    if outcome.outcome_sha != canonical_sha(control_candidate_outcome_payload(outcome)):
        raise ValueError("control candidate outcome self-hash mismatch")


def _validate_expected_rank_declaration(
    declaration: ExpectedRankDeclaration,
    registry_body: ClosedControlRegistry,
    entry,
) -> None:
    declaration.__post_init__()
    if (
        declaration.control_registry_sha != registry_body.registry_sha
        or declaration.control_registry_entry_sha != entry.entry_sha
        or declaration.control_id != entry.control_id
        or declaration.parent_freeze_sha != registry_body.parent_freeze_sha
        or declaration.expected_h_actual_rank != entry.expected_h_actual_rank
        or declaration.expected_h_ablated_rank != entry.expected_h_ablated_rank
        or declaration.expected_curv_actual_rank != entry.expected_curv_actual_rank
        or declaration.expected_curv_ablated_rank != entry.expected_curv_ablated_rank
    ):
        raise ValueError("expected-rank declaration differs from registry")
    if declaration.declaration_sha != canonical_sha(
        expected_rank_declaration_payload(declaration)
    ):
        raise ValueError("expected-rank declaration self-hash mismatch")


def _validate_branch_spectrum(audit: BranchSpectrumAudit) -> None:
    audit.__post_init__()
    if audit.branch_sha != canonical_sha(branch_spectrum_audit_payload(audit)):
        raise ValueError("branch spectrum self-hash mismatch")


def _expected_spectrum_values(
    values: FrozenComplexTensor,
    readout_kind: Literal["h", "curv"],
    readout_spec: ControlReadoutCalibrationSpec,
) -> tuple[tuple[int, int], tuple[float, ...]]:
    response_values = frozen_tensor_array(values)
    if response_values.ndim != 3:
        raise ValueError("source/readout response values must be rank three")
    source_whitener = frozen_tensor_array(readout_spec.source_metric_whitener)
    if readout_kind == "h":
        readout_chain = frozen_tensor_array(readout_spec.h_metric_whitener)
    else:
        readout_chain = frozen_tensor_array(
            readout_spec.curvature_metric_whitener
        ) @ frozen_tensor_array(readout_spec.curvature_incidence_operator)
    transformed = tuple(
        readout_chain @ response_values[index] @ source_whitener
        for index in range(response_values.shape[0])
    )
    rows = tuple(
        tuple(float(item) for item in np.linalg.svd(matrix, compute_uv=False))
        for matrix in transformed
    )
    n_singular = min(response_values.shape[1], response_values.shape[2])
    return (
        (response_values.shape[0], n_singular),
        tuple(item for row in rows for item in row),
    )


def _validate_per_control_spectrum(
    audit: PerControlReadoutSpectrumAudit,
    declaration: ExpectedRankDeclaration,
    entry,
    outcome: ControlCandidateOutcome,
) -> None:
    audit.__post_init__()
    _validate_branch_spectrum(audit.actual)
    _validate_branch_spectrum(audit.ablated)
    paired_outcome = outcome.attempt_audit.paired_response_outcome
    if paired_outcome is None or paired_outcome.paired_response is None:
        raise ValueError("spectrum audit requires a successful paired response")
    paired = paired_outcome.paired_response
    expected_ranks = (
        (
            declaration.expected_h_actual_rank,
            declaration.expected_h_ablated_rank,
        )
        if audit.readout_kind == "h"
        else (
            declaration.expected_curv_actual_rank,
            declaration.expected_curv_ablated_rank,
        )
    )
    if (
        audit.control_registry_entry_sha != entry.entry_sha
        or audit.expected_rank_declaration_sha != declaration.declaration_sha
        or audit.fejer_order != outcome.run_spec.fejer_order
        or audit.run_spec_sha != outcome.run_spec.spec_sha
        or audit.paired_response_sha != paired.pair_sha
        or audit.actual.declared_rank != expected_ranks[0]
        or audit.ablated.declared_rank != expected_ranks[1]
    ):
        raise ValueError("per-control spectrum binding differs from closed inputs")
    for branch_audit, branch_response in (
        (audit.actual, paired.actual),
        (audit.ablated, paired.ablated),
    ):
        shape, raw = _expected_spectrum_values(
            branch_response.values,
            audit.readout_kind,
            entry.readout_calibration_spec,
        )
        if branch_audit.spectrum_shape != shape or branch_audit.raw_spectrum != raw:
            raise ValueError("raw spectrum differs from paired response replay")
    expected_bridge = (
        (
            paired.actual.bridge_audit.h_operator_error_max,
            paired.ablated.bridge_audit.h_operator_error_max,
        )
        if audit.readout_kind == "h"
        else (
            paired.actual.bridge_audit.curv_operator_error_max,
            paired.ablated.bridge_audit.curv_operator_error_max,
        )
    )
    if (
        audit.actual_bridge_operator_error_upper != expected_bridge[0]
        or audit.ablated_bridge_operator_error_upper != expected_bridge[1]
    ):
        raise ValueError("spectrum bridge error differs from paired response")
    if audit.audit_sha != canonical_sha(
        per_control_readout_spectrum_audit_payload(audit)
    ):
        raise ValueError("per-control spectrum self-hash mismatch")


def _aggregate_values(
    audits: tuple[PerControlReadoutSpectrumAudit, ...],
) -> tuple[float, Optional[float], float, SignalThresholdValues]:
    active_values = tuple(
        value
        for audit in audits
        for branch in (audit.actual, audit.ablated)
        for row_start in range(
            0,
            len(branch.raw_spectrum),
            branch.spectrum_shape[1],
        )
        for value in branch.raw_spectrum[row_start : row_start + branch.declared_rank]
    )
    inactive = tuple(
        value
        for audit in audits
        for value in (audit.actual.inactive_max, audit.ablated.inactive_max)
        if value is not None
    )
    if not active_values:
        raise ValueError("aggregate lacks a declared active singular value")
    scale = max(active_values)
    signal = min(active_values)
    null = None if not inactive else max(inactive)
    bridge = max(
        value
        for audit in audits
        for value in (
            audit.actual_bridge_operator_error_upper,
            audit.ablated_bridge_operator_error_upper,
        )
    )
    raw_denominator = max(0.0 if null is None else null, EPS_FP64 * scale)
    thresholds = compute_signal_threshold_values(
        scale_ref=float(scale),
        null_max=None if null is None else float(null),
        bridge_operator_error_max=float(bridge),
        signal_min=float(signal),
        raw_relative_gap=float(signal / raw_denominator),
    )
    return (
        float(scale),
        None if null is None else float(null),
        float(bridge),
        thresholds,
    )


def _validate_aggregate(
    aggregate: ReadoutAggregateCalibrationAudit,
    expected_per_control: tuple[PerControlReadoutSpectrumAudit, ...],
) -> None:
    aggregate.__post_init__()
    if aggregate.per_control != expected_per_control:
        raise ValueError("aggregate does not recursively retain control audits")
    scale, null, bridge, thresholds = _aggregate_values(expected_per_control)
    expected = (
        scale,
        null,
        bridge,
        thresholds.noise_ref,
        thresholds.signal_min,
        thresholds.tau_sig,
        thresholds.signal_noise_ratio,
        thresholds.raw_relative_gap,
        thresholds.absolute_signal_gate_passed,
        thresholds.relative_gap_gate_passed,
    )
    observed = (
        aggregate.scale_ref,
        aggregate.null_max,
        aggregate.bridge_operator_error_max,
        aggregate.noise_ref,
        aggregate.signal_min,
        aggregate.tau_sig,
        aggregate.signal_noise_ratio,
        aggregate.raw_relative_gap,
        aggregate.absolute_signal_gate_passed,
        aggregate.relative_gap_gate_passed,
    )
    if observed != expected:
        raise ValueError("aggregate threshold values differ from raw spectra")
    if aggregate.aggregate_sha != canonical_sha(
        readout_aggregate_calibration_audit_payload(aggregate)
    ):
        raise ValueError("aggregate calibration self-hash mismatch")


def _shell_comparison_values(
    candidate: ControlCandidateOutcome,
    comparison: ControlCandidateOutcome,
) -> tuple[float, float, float]:
    first_outcome = candidate.attempt_audit.shell_outcome
    second_outcome = comparison.attempt_audit.shell_outcome
    if (
        first_outcome is None
        or first_outcome.shell is None
        or second_outcome is None
        or second_outcome.shell is None
    ):
        raise ValueError("window comparison requires two successful shells")
    first = first_outcome.shell
    second = second_outcome.shell
    phase_separation = (
        math.pi
        if first.nearest_competitor_gap_min is None
        else first.nearest_competitor_gap_min
    )
    overlap_margin = (
        1.0 if first.overlap_margin_min is None else first.overlap_margin_min
    )
    first_projectors = frozen_tensor_array(first.shell_projectors)
    second_projectors = frozen_tensor_array(second.shell_projectors)
    if first_projectors.shape != second_projectors.shape:
        raise ValueError("T/2T shell projector shapes differ")
    distance = float(
        max(
            np.linalg.norm(first_item - second_item, 2)
            for first_item, second_item in zip(
                first_projectors,
                second_projectors,
            )
        )
    )
    return float(phase_separation), float(overlap_margin), distance


def _validate_control_candidate_audit(
    audit: ControlCandidateAudit,
    registry_body: ClosedControlRegistry,
    entry,
    protocol_body: WindowCalibrationProtocol,
    order: int,
) -> None:
    audit.__post_init__()
    if audit.control_registry_entry != entry:
        raise ValueError("control candidate embeds another registry entry")
    _validate_expected_rank_declaration(
        audit.expected_rank_declaration,
        registry_body,
        entry,
    )
    _validate_control_candidate_outcome(
        audit.candidate_t,
        protocol_body,
        registry_body,
    )
    _validate_control_candidate_outcome(
        audit.comparison_2t,
        protocol_body,
        registry_body,
    )
    if (
        audit.candidate_t.run_spec.fejer_order != order
        or audit.comparison_2t.run_spec.fejer_order != 2 * order
    ):
        raise ValueError("control candidate T/2T orders are not exact")
    both_success = (
        audit.candidate_t.status.defined and audit.comparison_2t.status.defined
    )
    spectra = audit.readout_spectrum_audits
    spectra_2t = audit.comparison_2t_readout_spectrum_audits
    if not both_success:
        if spectra or spectra_2t:
            raise ValueError("failed control candidate cannot carry spectra")
        if any(
            value is not None
            for value in (
                audit.phase_separation,
                audit.overlap_margin,
                audit.projector_t2t_distance,
            )
        ):
            raise ValueError("failed control candidate cannot carry comparisons")
        expected_passed = False
    else:
        if tuple(item.readout_kind for item in spectra) != ("h", "curv") or tuple(
            item.readout_kind for item in spectra_2t
        ) != ("h", "curv"):
            raise ValueError("successful control requires h/curv T and 2T spectra")
        for item in spectra:
            _validate_per_control_spectrum(
                item,
                audit.expected_rank_declaration,
                entry,
                audit.candidate_t,
            )
        for item in spectra_2t:
            _validate_per_control_spectrum(
                item,
                audit.expected_rank_declaration,
                entry,
                audit.comparison_2t,
            )
        comparisons = _shell_comparison_values(
            audit.candidate_t,
            audit.comparison_2t,
        )
        if (
            audit.phase_separation,
            audit.overlap_margin,
            audit.projector_t2t_distance,
        ) != comparisons:
            raise ValueError("control comparison values differ from shell replay")
        bridge_signal_passed = all(
            branch.active_min is None or branch.active_min > bridge
            for item in (*spectra, *spectra_2t)
            for branch, bridge in (
                (item.actual, item.actual_bridge_operator_error_upper),
                (item.ablated, item.ablated_bridge_operator_error_upper),
            )
        )
        expected_passed = bridge_signal_passed and verify_window_comparison_gates(
            order=order,
            phase_separation=comparisons[0],
            overlap_margin=comparisons[1],
            projector_t2t_distance=comparisons[2],
        )
    if audit.passed != expected_passed:
        raise ValueError("control candidate pass flag is not mechanical")
    if audit.audit_sha != canonical_sha(control_candidate_audit_payload(audit)):
        raise ValueError("control candidate audit self-hash mismatch")


def _validate_window_candidate_audit(
    audit: WindowCandidateAudit,
    registry_body: ClosedControlRegistry,
    protocol_body: WindowCalibrationProtocol,
) -> None:
    audit.__post_init__()
    if (
        tuple(item.control_registry_entry.control_id for item in audit.control_audits)
        != CONTROL_ORDER
    ):
        raise ValueError("window control audits are not in registry order")
    for item, entry in zip(audit.control_audits, registry_body.entries):
        _validate_control_candidate_audit(
            item,
            registry_body,
            entry,
            protocol_body,
            audit.fejer_order,
        )
    reached_spectra = all(
        item.candidate_t.status.defined and item.comparison_2t.status.defined
        for item in audit.control_audits
    )
    if reached_spectra:
        if tuple(item.readout_kind for item in audit.readout_aggregate_audits) != (
            "h",
            "curv",
        ):
            raise ValueError("reached window candidate requires h/curv aggregates")
        for aggregate in audit.readout_aggregate_audits:
            expected_per_control = tuple(
                next(
                    spectrum
                    for spectrum in control.readout_spectrum_audits
                    if spectrum.readout_kind == aggregate.readout_kind
                )
                for control in audit.control_audits
            )
            _validate_aggregate(aggregate, expected_per_control)
    elif audit.readout_aggregate_audits:
        raise ValueError("failed window candidate cannot carry aggregate audits")
    aggregate_passed = reached_spectra and all(
        item.absolute_signal_gate_passed and item.relative_gap_gate_passed
        for item in audit.readout_aggregate_audits
    )
    expected_passed = aggregate_passed and all(
        item.passed for item in audit.control_audits
    )
    if audit.passed != expected_passed:
        raise ValueError("window candidate pass flag is not mechanical")
    if audit.audit_sha != canonical_sha(window_candidate_audit_payload(audit)):
        raise ValueError("window candidate audit self-hash mismatch")


def _selected_evidence_ref(
    audit: ControlCandidateAudit,
) -> SelectedControlEvidenceRef:
    candidate_pair = audit.candidate_t.attempt_audit.paired_response_outcome
    comparison_pair = audit.comparison_2t.attempt_audit.paired_response_outcome
    candidate_shell = audit.candidate_t.attempt_audit.shell_outcome
    comparison_shell = audit.comparison_2t.attempt_audit.shell_outcome
    if (
        candidate_pair is None
        or candidate_pair.paired_response is None
        or comparison_pair is None
        or comparison_pair.paired_response is None
        or candidate_shell is None
        or candidate_shell.shell is None
        or comparison_shell is None
        or comparison_shell.shell is None
    ):
        raise ValueError("selected control evidence is incomplete")
    return SelectedControlEvidenceRef(
        control_id=audit.control_registry_entry.control_id,
        control_registry_entry_sha=audit.control_registry_entry.entry_sha,
        expected_rank_declaration_sha=(audit.expected_rank_declaration.declaration_sha),
        run_spec_sha=audit.candidate_t.run_spec.spec_sha,
        paired_response_sha=candidate_pair.paired_response.pair_sha,
        shell_manifest_sha=candidate_shell.shell.shell_manifest_sha,
        comparison_2t_run_spec_sha=audit.comparison_2t.run_spec.spec_sha,
        comparison_2t_response_sha=(comparison_pair.paired_response.pair_sha),
        comparison_2t_shell_manifest_sha=(comparison_shell.shell.shell_manifest_sha),
    )


def _expected_selection(
    candidate: WindowCandidateAudit,
) -> WindowThresholdSelection:
    aggregate = {item.readout_kind: item for item in candidate.readout_aggregate_audits}
    if tuple(aggregate) != ("h", "curv"):
        raise ValueError("selected candidate lacks canonical aggregates")
    provisional = WindowThresholdSelection(
        selected_fejer_order=candidate.fejer_order,
        h_scale_ref=aggregate["h"].scale_ref,
        h_noise_ref=aggregate["h"].noise_ref,
        h_signal_min=aggregate["h"].signal_min,
        h_tau_sig=aggregate["h"].tau_sig,
        curv_scale_ref=aggregate["curv"].scale_ref,
        curv_noise_ref=aggregate["curv"].noise_ref,
        curv_signal_min=aggregate["curv"].signal_min,
        curv_tau_sig=aggregate["curv"].tau_sig,
        selected_evidence_refs=tuple(
            _selected_evidence_ref(item) for item in candidate.control_audits
        ),
        selection_sha="0" * 64,
    )
    return replace(
        provisional,
        selection_sha=canonical_sha(window_threshold_selection_payload(provisional)),
    )


def _validate_window_calibration(
    outcome: WindowCalibrationOutcome,
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
) -> None:
    _preflight_tree(outcome, "window calibration")
    _exact_record(
        outcome,
        WindowCalibrationOutcome,
        "window calibration outcome",
    )
    outcome.__post_init__()
    registry_view = _reverify_verified_control_registry(registry)
    protocol_view = _reverify_verified_window_calibration_protocol(protocol)
    manifest = outcome.manifest
    _exact_record(
        manifest,
        WindowThresholdCalibrationManifest,
        "calibration manifest",
    )
    manifest.__post_init__()
    if manifest.control_registry != registry_view.registry:
        raise ValueError("calibration registry body mismatch")
    if manifest.window_protocol != protocol_view.protocol:
        raise ValueError("calibration window protocol body mismatch")
    if protocol_view.registry is not registry:
        raise ValueError("calibration protocol is not bound to registry")
    _validate_raw_window_protocol_body(
        protocol_view.protocol,
        registry_view.registry,
    )
    if len(manifest.candidate_audits) != len(T_CANDIDATES):
        raise ValueError("calibration manifest must retain all six candidate audits")
    if not all(
        type(candidate) is WindowCandidateAudit
        for candidate in manifest.candidate_audits
    ):
        raise TypeError(
            "calibration candidate_audits must contain exact "
            "WindowCandidateAudit records"
        )
    if tuple(candidate.fejer_order for candidate in manifest.candidate_audits) != (
        T_CANDIDATES
    ):
        raise ValueError(
            "calibration candidate audits are not the frozen six-order table"
        )
    for candidate in manifest.candidate_audits:
        _validate_window_candidate_audit(
            candidate,
            registry_view.registry,
            protocol_view.protocol,
        )
    if manifest.calibration_manifest_sha != canonical_sha(
        window_threshold_calibration_manifest_payload(manifest)
    ):
        raise ValueError("calibration_manifest_sha does not match complete body")
    selection = outcome.selection
    first_passing = next(
        (item for item in manifest.candidate_audits if item.passed),
        None,
    )
    if first_passing is None:
        if selection is not None or outcome.status != BlockStatus(
            False,
            UndefinedReason.WINDOW_UNRESOLVED,
        ):
            raise ValueError("unresolved window outcome has a forged selection")
    else:
        if selection is None or not outcome.status.defined:
            raise ValueError("first passing candidate lacks a selection")
        expected_selection = _expected_selection(first_passing)
        if selection != expected_selection:
            raise ValueError("selection differs from the first passing candidate")
    if selection is not None:
        _exact_record(
            selection,
            WindowThresholdSelection,
            "window threshold selection",
        )
        selection.__post_init__()
        if selection.selection_sha != canonical_sha(
            window_threshold_selection_payload(selection)
        ):
            raise ValueError("selection_sha does not match complete body")
        for entry, reference in zip(
            registry_view.registry.entries,
            selection.selected_evidence_refs,
        ):
            if (
                reference.control_id != entry.control_id
                or reference.control_registry_entry_sha != entry.entry_sha
            ):
                raise ValueError("selected evidence is not registry ordered/bound")
    if outcome.outcome_sha != canonical_sha(
        window_calibration_outcome_payload(outcome)
    ):
        raise ValueError("outcome_sha does not match complete body")


def _candidate_record_types(
    manifest: WindowThresholdCalibrationManifest,
) -> tuple[type, ...]:
    """Collect the already-validated recursive candidate wire type graph."""

    result: list[type] = []
    active: set[int] = set()
    stack: list[object] = list(manifest.candidate_audits)
    while stack:
        value = stack.pop()
        value_type = type(value)
        if isinstance(value, Enum):
            if value_type not in result:
                result.append(value_type)
            continue
        fields = getattr(value_type, "__dataclass_fields__", None)
        if fields is not None:
            identity = id(value)
            if identity in active:
                continue
            active.add(identity)
            if value_type not in result:
                result.append(value_type)
            stack.extend(getattr(value, name) for name in fields)
            continue
        if value_type in (tuple, list):
            stack.extend(value)
        elif value_type is dict:
            stack.extend(value)
            stack.extend(value.values())
    return tuple(result)


def _clone_window_calibration_outcome(
    outcome: WindowCalibrationOutcome,
) -> WindowCalibrationOutcome:
    # The response authority clone is structural, exact-field checked, and
    # deliberately bypasses user ``deepcopy`` dispatch.  Validation above has
    # already restricted every Task-11 node to the closed type graph.
    return _task11_response_types()._authority_structural_clone(outcome)


def issue_expected_rank_declaration(
    registry: VerifiedControlRegistry,
    control_id: Literal["full", "zero", "direct_sum"],
) -> ExpectedRankDeclaration:
    """Issue ranks only from the live closed registry; no rank is accepted."""

    registry_view = _reverify_verified_control_registry(registry)
    if control_id not in CONTROL_ORDER:
        raise ValueError("control ID is outside the closed registry")
    entry = registry_view.registry.entries[CONTROL_ORDER.index(control_id)]
    provisional = ExpectedRankDeclaration(
        declaration_schema_version=EXPECTED_RANK_DECLARATION_SCHEMA_VERSION,
        control_registry_sha=registry_view.registry.registry_sha,
        control_registry_entry_sha=entry.entry_sha,
        control_id=control_id,
        expected_h_actual_rank=entry.expected_h_actual_rank,
        expected_h_ablated_rank=entry.expected_h_ablated_rank,
        expected_curv_actual_rank=entry.expected_curv_actual_rank,
        expected_curv_ablated_rank=entry.expected_curv_ablated_rank,
        parent_freeze_sha=registry_view.registry.parent_freeze_sha,
        declaration_sha="0" * 64,
    )
    result = replace(
        provisional,
        declaration_sha=canonical_sha(expected_rank_declaration_payload(provisional)),
    )
    _validate_expected_rank_declaration(result, registry_view.registry, entry)
    return result


def compute_window_readout_calibration_audits(
    registry: VerifiedControlRegistry,
    control_audits: tuple[ControlCandidateAudit, ...],
) -> tuple[ReadoutAggregateCalibrationAudit, ...]:
    """Derive both common signal lines from three exact control spectra."""

    registry_view = _reverify_verified_control_registry(registry)
    if type(control_audits) is not tuple or len(control_audits) != len(CONTROL_ORDER):
        raise ValueError("aggregate builder requires exactly three controls")
    if not all(type(item) is ControlCandidateAudit for item in control_audits):
        raise TypeError("aggregate builder requires exact control candidate audits")
    if (
        tuple(item.control_registry_entry.control_id for item in control_audits)
        != CONTROL_ORDER
    ):
        raise ValueError("aggregate builder controls are not canonical")
    first_pair = control_audits[0].candidate_t.attempt_audit.paired_response_outcome
    if first_pair is None:
        raise ValueError("aggregate builder requires successful paired responses")
    protocol_body = first_pair.attempt_audit.window_protocol
    _validate_raw_window_protocol_body(protocol_body, registry_view.registry)
    order = control_audits[0].candidate_t.run_spec.fejer_order
    if order not in T_CANDIDATES:
        raise ValueError("aggregate source is not a frozen candidate order")
    for item, entry in zip(control_audits, registry_view.registry.entries):
        if item.control_registry_entry != entry:
            raise ValueError("aggregate control differs from registry")
        _validate_control_candidate_audit(
            item,
            registry_view.registry,
            entry,
            protocol_body,
            order,
        )
        if not item.candidate_t.status.defined or not item.comparison_2t.status.defined:
            raise ValueError("aggregate builder requires successful T/2T outcomes")
        if tuple(audit.readout_kind for audit in item.readout_spectrum_audits) != (
            "h",
            "curv",
        ):
            raise ValueError("aggregate source lacks h/curv spectra")
    result: list[ReadoutAggregateCalibrationAudit] = []
    for kind in ("h", "curv"):
        per_control = tuple(
            next(
                audit
                for audit in control.readout_spectrum_audits
                if audit.readout_kind == kind
            )
            for control in control_audits
        )
        scale, null, bridge, thresholds = _aggregate_values(per_control)
        provisional = ReadoutAggregateCalibrationAudit(
            readout_kind=kind,
            per_control=per_control,
            scale_ref=scale,
            null_max=null,
            bridge_operator_error_max=bridge,
            noise_ref=thresholds.noise_ref,
            signal_min=thresholds.signal_min,
            tau_sig=thresholds.tau_sig,
            signal_noise_ratio=thresholds.signal_noise_ratio,
            raw_relative_gap=thresholds.raw_relative_gap,
            absolute_signal_gate_passed=(thresholds.absolute_signal_gate_passed),
            relative_gap_gate_passed=thresholds.relative_gap_gate_passed,
            aggregate_sha="0" * 64,
        )
        aggregate = replace(
            provisional,
            aggregate_sha=canonical_sha(
                readout_aggregate_calibration_audit_payload(provisional)
            ),
        )
        _validate_aggregate(aggregate, per_control)
        result.append(aggregate)
    return tuple(result)


def calibrate_window_and_thresholds(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    candidate_audits: tuple[WindowCandidateAudit, ...],
) -> WindowCalibrationOutcome:
    """Build the six-candidate outcome and select the first common PASS."""

    registry_view = _reverify_verified_control_registry(registry)
    protocol_view = _reverify_verified_window_calibration_protocol(protocol)
    if protocol_view.registry is not registry:
        raise ValueError("window protocol is not bound to this registry")
    if (
        type(candidate_audits) is not tuple
        or tuple(
            item.fejer_order if type(item) is WindowCandidateAudit else None
            for item in candidate_audits
        )
        != T_CANDIDATES
    ):
        raise ValueError("calibrator requires the frozen six-candidate table")
    for candidate in candidate_audits:
        _validate_window_candidate_audit(
            candidate,
            registry_view.registry,
            protocol_view.protocol,
        )
    provisional_manifest = WindowThresholdCalibrationManifest(
        calibration_schema_version=WINDOW_THRESHOLD_CALIBRATION_SCHEMA_VERSION,
        control_registry=registry_view.registry,
        window_protocol=protocol_view.protocol,
        candidate_audits=candidate_audits,
        calibration_manifest_sha="0" * 64,
    )
    manifest = replace(
        provisional_manifest,
        calibration_manifest_sha=canonical_sha(
            window_threshold_calibration_manifest_payload(provisional_manifest)
        ),
    )
    first_passing = next((item for item in candidate_audits if item.passed), None)
    selection = None if first_passing is None else _expected_selection(first_passing)
    provisional_outcome = WindowCalibrationOutcome(
        status=(
            BlockStatus(False, UndefinedReason.WINDOW_UNRESOLVED)
            if selection is None
            else BlockStatus(True, None)
        ),
        manifest=manifest,
        selection=selection,
        outcome_sha="0" * 64,
    )
    outcome = replace(
        provisional_outcome,
        outcome_sha=canonical_sha(
            window_calibration_outcome_payload(provisional_outcome)
        ),
    )
    _validate_window_calibration(outcome, registry, protocol)
    return outcome


def verify_window_threshold_calibration(
    outcome: WindowCalibrationOutcome,
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
) -> VerifiedWindowThresholdCalibration:
    """Hydrate a successful raw calibration against live upstream seals."""

    _validate_window_calibration(outcome, registry, protocol)
    if not outcome.status.defined or outcome.selection is None:
        raise ValueError("only a successful calibration is an authority")
    snapshot = _clone_window_calibration_outcome(outcome)
    digest = canonical_sha(window_calibration_outcome_payload(snapshot))
    seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-window-threshold-calibration.v1"
            ),
            "body_digest": digest,
            "registry_sha": snapshot.manifest.control_registry.registry_sha,
            "protocol_sha": snapshot.manifest.window_protocol.protocol_sha,
        }
    )
    wrapper = VerifiedWindowThresholdCalibration(
        _ISSUANCE_TOKEN,
        _clone_window_calibration_outcome(snapshot),
        seal,
    )
    identity = id(wrapper)
    authority = _CalibrationAuthority(
        outcome=snapshot,
        registry=registry,
        protocol=protocol,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[VerifiedWindowThresholdCalibration],
        wrapper_id: int = identity,
    ) -> None:
        with _CALIBRATION_LOCK:
            current = _CALIBRATION_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _CALIBRATION_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _CALIBRATION_LOCK:
        _CALIBRATION_LIVE[identity] = (reference, authority)
    return wrapper


def _reverify_verified_window_threshold_calibration(
    wrapper: VerifiedWindowThresholdCalibration,
) -> _CalibrationView:
    if type(wrapper) is not VerifiedWindowThresholdCalibration:
        raise TypeError("Task 12 requires a live window-threshold calibration")
    with _CALIBRATION_LOCK:
        current = _CALIBRATION_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("window-threshold calibration identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedWindowThresholdCalibration__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedWindowThresholdCalibration__outcome",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedWindowThresholdCalibration__seal",
        )
    except AttributeError as exc:
        raise ValueError("calibration authority record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("calibration authority token mismatch")
    _validate_window_calibration(
        authority.outcome,
        authority.registry,
        authority.protocol,
    )
    _preflight_tree(raw, "exposed window calibration")
    observed = canonical_sha(window_calibration_outcome_payload(raw))
    expected = canonical_sha(window_calibration_outcome_payload(authority.outcome))
    expected_seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-window-threshold-calibration.v1"
            ),
            "body_digest": expected,
            "registry_sha": (authority.outcome.manifest.control_registry.registry_sha),
            "protocol_sha": (authority.outcome.manifest.window_protocol.protocol_sha),
        }
    )
    if (
        observed != authority.digest
        or expected != authority.digest
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("calibration immutable seal mismatch")
    return _CalibrationView(
        outcome=_clone_window_calibration_outcome(authority.outcome),
        registry=authority.registry,
        protocol=authority.protocol,
    )


@dataclass(frozen=True)
class CalibrationApplicationPermit:
    permit_schema_version: str
    scope: Literal["v3m0-synthetic-control-application-v1"]
    parent_freeze: ParentFreezeManifest
    application_spec: V3M0SyntheticControlApplicationSpec
    calibration_manifest: WindowThresholdCalibrationManifest
    selection: WindowThresholdSelection
    selected_fejer_order: int
    window_protocol: WindowCalibrationProtocol
    response_grid: ResponseKGridManifest
    source_readout_bridge_grid: BridgeKGridManifest
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    expected_shell_rank: int
    expected_shell_rank_source_id: Literal["parent-freeze-control-application-spec-v1"]
    source_basis: BasisManifest
    readout_basis: BasisManifest
    readout_calibration_spec: ControlReadoutCalibrationSpec
    permit_sha: str

    def __post_init__(self) -> None:
        _text(self.permit_schema_version, "permit_schema_version")
        if self.scope != CALIBRATION_APPLICATION_SCOPE:
            raise ValueError("application permit scope is not V3-M0 synthetic")
        if type(self.parent_freeze) is not ParentFreezeManifest:
            raise TypeError("parent_freeze has the wrong strict type")
        if type(self.application_spec) is not V3M0SyntheticControlApplicationSpec:
            raise TypeError("application_spec has the wrong strict type")
        if type(self.calibration_manifest) is not WindowThresholdCalibrationManifest:
            raise TypeError("calibration_manifest has the wrong strict type")
        if type(self.selection) is not WindowThresholdSelection:
            raise TypeError("selection has the wrong strict type")
        if self.selected_fejer_order not in T_CANDIDATES:
            raise ValueError("selected_fejer_order is not preregistered")
        if type(self.window_protocol) is not WindowCalibrationProtocol:
            raise TypeError("window_protocol has the wrong strict type")
        if type(self.response_grid) is not ResponseKGridManifest:
            raise TypeError("response_grid has the wrong strict type")
        if type(self.source_readout_bridge_grid) is not BridgeKGridManifest:
            raise TypeError("source_readout_bridge_grid has the wrong strict type")
        if (
            type(self.source_readout_bridge_steps) is not tuple
            or not self.source_readout_bridge_steps
            or self.source_readout_bridge_steps
            != tuple(sorted(set(self.source_readout_bridge_steps)))
        ):
            raise ValueError("source_readout_bridge_steps must be unique ascending")
        if not all(
            type(item) is int and 0 < item <= 16384
            for item in self.source_readout_bridge_steps
        ):
            raise ValueError("source bridge steps are outside the closed range")
        if (
            type(self.reference_reciprocal_index) is not tuple
            or not self.reference_reciprocal_index
        ):
            raise ValueError("reference_reciprocal_index must be non-empty")
        if (
            type(self.preregistered_phase_bands) is not tuple
            or not self.preregistered_phase_bands
        ):
            raise ValueError("preregistered_phase_bands must be non-empty")
        _positive_int(self.expected_shell_rank, "expected_shell_rank")
        if self.expected_shell_rank_source_id != APPLICATION_EXPECTED_RANK_SOURCE_ID:
            raise ValueError("expected shell rank source is not frozen")
        if type(self.source_basis) is not BasisManifest:
            raise TypeError("source_basis has the wrong strict type")
        if type(self.readout_basis) is not BasisManifest:
            raise TypeError("readout_basis has the wrong strict type")
        if type(self.readout_calibration_spec) is not ControlReadoutCalibrationSpec:
            raise TypeError("readout_calibration_spec has the wrong type")
        _sha(self.permit_sha, "permit_sha")


def calibration_application_permit_payload(
    permit: CalibrationApplicationPermit,
) -> dict[str, object]:
    _exact_record(
        permit,
        CalibrationApplicationPermit,
        "calibration application permit",
    )
    return _payload_without_hash(permit, "permit_sha")


def _clone_application_permit(
    permit: CalibrationApplicationPermit,
) -> CalibrationApplicationPermit:
    return _clone_task12_wire(
        permit,
        local_record_types=(
            SelectedControlEvidenceRef,
            WindowThresholdSelection,
            WindowThresholdCalibrationManifest,
            CalibrationApplicationPermit,
        ),
        candidate_record_types=_candidate_record_types(permit.calibration_manifest),
    )  # type: ignore[return-value]


@dataclass(frozen=True)
class _PermitAuthority:
    permit: CalibrationApplicationPermit
    parent: VerifiedParentFreeze
    calibration: VerifiedWindowThresholdCalibration
    digest: str
    seal: str


class VerifiedCalibrationApplicationPermit:
    """Opaque, live, V3-M0-only pre-response capability."""

    __slots__ = ("__permit", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        permit: CalibrationApplicationPermit,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError(
                "VerifiedCalibrationApplicationPermit is module-issued only"
            )
        object.__setattr__(
            self,
            "_VerifiedCalibrationApplicationPermit__permit",
            permit,
        )
        object.__setattr__(
            self,
            "_VerifiedCalibrationApplicationPermit__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedCalibrationApplicationPermit__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("application permit is immutable")

    @property
    def permit(self) -> CalibrationApplicationPermit:
        return _reverify_verified_calibration_application_permit(self).permit


_PERMIT_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedCalibrationApplicationPermit],
        _PermitAuthority,
    ],
] = {}
_PERMIT_LOCK = threading.RLock()


def _derive_readout_spec(
    application: V3M0SyntheticControlApplicationSpec,
) -> ControlReadoutCalibrationSpec:
    protocol = application.readout_protocol
    provisional = ControlReadoutCalibrationSpec(
        spec_schema_version="v3m0.control-readout-calibration-spec.v1",
        source_metric_whitener=protocol.source_metric_whitener,
        h_metric_whitener=protocol.h_metric_whitener,
        curvature_incidence_operator=protocol.curvature_incidence_operator,
        curvature_metric_whitener=protocol.curvature_metric_whitener,
        curvature_normalizer_id=protocol.curvature_normalizer_id,
        spec_sha="0" * 64,
    )
    return replace(
        provisional,
        spec_sha=canonical_sha(readout_calibration_spec_payload(provisional)),
    )


def _application_spec(
    parent: ParentFreezeManifest,
    application_instance_id: str,
) -> V3M0SyntheticControlApplicationSpec:
    instance_id = _text(
        application_instance_id,
        "application_instance_id",
    )
    matches = tuple(
        item
        for item in parent.synthetic_control_application_specs
        if item.application_instance_id == instance_id
    )
    if len(matches) != 1:
        raise ValueError("application_instance_id is not uniquely frozen")
    application = verify_synthetic_control_application_spec(matches[0])
    ordinal = parent.synthetic_control_application_specs.index(application)
    if ordinal < 3:
        raise ValueError(
            "C01-C03 are selected calibration controls, not permitted "
            "application controls"
        )
    if application.expected_control_evidence_schema != (
        "v3m0.control-application-evidence.v1"
    ):
        raise ValueError("application is outside the Task 12 evidence lane")
    return application


def _expected_permit(
    parent: VerifiedParentFreeze,
    calibration: VerifiedWindowThresholdCalibration,
    application_instance_id: str,
) -> CalibrationApplicationPermit:
    parent_manifest = _reverify_verified_parent_freeze(parent)
    calibration_view = _reverify_verified_window_threshold_calibration(calibration)
    outcome = calibration_view.outcome
    selection = outcome.selection
    if selection is None:
        raise ValueError("application permit requires selected calibration")
    if (
        outcome.manifest.control_registry.parent_freeze_sha
        != parent_manifest.parent_freeze_sha
        or outcome.manifest.window_protocol.parent_freeze_sha
        != parent_manifest.parent_freeze_sha
    ):
        raise ValueError("calibration and parent freeze are not bound")
    application = _application_spec(
        parent_manifest,
        application_instance_id,
    )
    response_grid = build_response_grid_manifest(application)
    bridge_grid = build_application_bridge_grid_manifest(application)
    readout_spec = _derive_readout_spec(application)
    grid = application.grid_protocol
    provisional = CalibrationApplicationPermit(
        permit_schema_version=(CALIBRATION_APPLICATION_PERMIT_SCHEMA_VERSION),
        scope=CALIBRATION_APPLICATION_SCOPE,
        parent_freeze=parent_manifest,
        application_spec=application,
        calibration_manifest=outcome.manifest,
        selection=selection,
        selected_fejer_order=selection.selected_fejer_order,
        window_protocol=outcome.manifest.window_protocol,
        response_grid=response_grid,
        source_readout_bridge_grid=bridge_grid,
        source_readout_bridge_steps=grid.bridge_steps,
        reference_reciprocal_index=grid.reference_reciprocal_index,
        preregistered_phase_bands=grid.preregistered_phase_bands,
        expected_shell_rank=grid.expected_shell_rank,
        expected_shell_rank_source_id=(APPLICATION_EXPECTED_RANK_SOURCE_ID),
        source_basis=application.basis_protocol.source_basis,
        readout_basis=application.basis_protocol.readout_basis,
        readout_calibration_spec=readout_spec,
        permit_sha="0" * 64,
    )
    return replace(
        provisional,
        permit_sha=canonical_sha(calibration_application_permit_payload(provisional)),
    )


def _issue_permit(
    expected: CalibrationApplicationPermit,
    parent: VerifiedParentFreeze,
    calibration: VerifiedWindowThresholdCalibration,
) -> VerifiedCalibrationApplicationPermit:
    _preflight_tree(expected, "application permit")
    digest = canonical_sha(calibration_application_permit_payload(expected))
    if digest != expected.permit_sha:
        raise ValueError("permit self-hash mismatch")
    seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-calibration-application-permit.v1"
            ),
            "permit_sha": expected.permit_sha,
            "body_digest": digest,
        }
    )
    wrapper = VerifiedCalibrationApplicationPermit(
        _ISSUANCE_TOKEN,
        _clone_application_permit(expected),
        seal,
    )
    identity = id(wrapper)
    authority = _PermitAuthority(
        permit=_clone_application_permit(expected),
        parent=parent,
        calibration=calibration,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[VerifiedCalibrationApplicationPermit],
        wrapper_id: int = identity,
    ) -> None:
        with _PERMIT_LOCK:
            current = _PERMIT_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _PERMIT_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _PERMIT_LOCK:
        _PERMIT_LIVE[identity] = (reference, authority)
    return wrapper


def issue_v3m0_calibration_application_permit(
    parent: VerifiedParentFreeze,
    calibration: VerifiedWindowThresholdCalibration,
    application_instance_id: str,
) -> VerifiedCalibrationApplicationPermit:
    """Issue a pre-response permit from the unique parent application spec."""

    expected = _expected_permit(
        parent,
        calibration,
        application_instance_id,
    )
    return _issue_permit(expected, parent, calibration)


def verify_calibration_application_permit(
    permit: CalibrationApplicationPermit,
    parent: VerifiedParentFreeze,
    calibration: VerifiedWindowThresholdCalibration,
) -> VerifiedCalibrationApplicationPermit:
    """Hydrate only by reconstructing the complete permit body."""

    _preflight_tree(permit, "raw application permit")
    _exact_record(
        permit,
        CalibrationApplicationPermit,
        "raw application permit",
    )
    expected = _expected_permit(
        parent,
        calibration,
        permit.application_spec.application_instance_id,
    )
    if permit != expected:
        raise ValueError("raw application permit differs from reconstruction")
    if permit.permit_sha != canonical_sha(
        calibration_application_permit_payload(permit)
    ):
        raise ValueError("permit_sha does not match complete body")
    return _issue_permit(expected, parent, calibration)


@dataclass(frozen=True)
class _PermitView:
    permit: CalibrationApplicationPermit
    parent: VerifiedParentFreeze
    calibration: VerifiedWindowThresholdCalibration


def _reverify_verified_calibration_application_permit(
    wrapper: VerifiedCalibrationApplicationPermit,
) -> _PermitView:
    if type(wrapper) is not VerifiedCalibrationApplicationPermit:
        raise TypeError("Task 12 requires a live application permit")
    with _PERMIT_LOCK:
        current = _PERMIT_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("application permit identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedCalibrationApplicationPermit__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedCalibrationApplicationPermit__permit",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedCalibrationApplicationPermit__seal",
        )
    except AttributeError as exc:
        raise ValueError("application permit record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("application permit token mismatch")
    expected = _expected_permit(
        authority.parent,
        authority.calibration,
        authority.permit.application_spec.application_instance_id,
    )
    _preflight_tree(raw, "exposed application permit")
    raw_digest = canonical_sha(calibration_application_permit_payload(raw))
    expected_digest = canonical_sha(calibration_application_permit_payload(expected))
    expected_seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-calibration-application-permit.v1"
            ),
            "permit_sha": expected.permit_sha,
            "body_digest": expected_digest,
        }
    )
    if (
        raw != authority.permit
        or raw.permit_sha != authority.permit.permit_sha
        or raw_digest != authority.digest
        or expected_digest != authority.digest
        or expected != authority.permit
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("application permit immutable seal mismatch")
    return _PermitView(
        permit=_clone_application_permit(expected),
        parent=authority.parent,
        calibration=authority.calibration,
    )


def _make_prestructure_child_reverifier(
    wrapper_type: type,
    reverifier,
    name: str,
):
    def reverify(wrapper):
        if type(wrapper) is not wrapper_type:
            raise TypeError("prestructure child has the wrong exact type")
        return reverifier(wrapper)

    reverify.__name__ = name
    reverify.__qualname__ = name
    return reverify


VerifiedCalibrationApplicationPermit._prestructure_reverify = (  # type: ignore[attr-defined]
    _make_prestructure_child_reverifier(
        VerifiedCalibrationApplicationPermit,
        _reverify_verified_calibration_application_permit,
        "_prestructure_reverify_calibration_application_permit",
    )
)


@dataclass(frozen=True)
class V3M0ApplicationResponseRunSpec:
    run_spec_schema_version: str
    permit_sha: str
    application_spec_sha: str
    fejer_order: int
    source_basis: BasisManifest
    readout_basis: BasisManifest
    response_grid: ResponseKGridManifest
    source_readout_bridge_grid: BridgeKGridManifest
    source_readout_bridge_steps: tuple[int, ...]
    source_trial_vectors: FrozenComplexTensor
    bridge_tolerance: float
    run_spec_sha: str

    def __post_init__(self) -> None:
        _text(self.run_spec_schema_version, "run_spec_schema_version")
        _sha(self.permit_sha, "permit_sha")
        _sha(self.application_spec_sha, "application_spec_sha")
        if self.fejer_order not in T_CANDIDATES:
            raise ValueError("application Fejer order is not selected")
        if type(self.source_basis) is not BasisManifest:
            raise TypeError("source_basis has the wrong strict type")
        if type(self.readout_basis) is not BasisManifest:
            raise TypeError("readout_basis has the wrong strict type")
        if type(self.response_grid) is not ResponseKGridManifest:
            raise TypeError("response_grid has the wrong strict type")
        if type(self.source_readout_bridge_grid) is not BridgeKGridManifest:
            raise TypeError("bridge grid has the wrong strict type")
        if type(self.source_readout_bridge_steps) is not tuple:
            raise TypeError("source_readout_bridge_steps must be a tuple")
        if type(self.source_trial_vectors) is not FrozenComplexTensor:
            raise TypeError("source_trial_vectors has the wrong strict type")
        if self.bridge_tolerance != BRIDGE_TOLERANCE:
            raise ValueError("bridge_tolerance is not frozen")
        _sha(self.run_spec_sha, "run_spec_sha")


def v3m0_application_response_run_spec_payload(
    run_spec: V3M0ApplicationResponseRunSpec,
) -> dict[str, object]:
    _exact_record(
        run_spec,
        V3M0ApplicationResponseRunSpec,
        "application response run spec",
    )
    return _payload_without_hash(run_spec, "run_spec_sha")


def _clone_application_run_spec(
    run_spec: V3M0ApplicationResponseRunSpec,
) -> V3M0ApplicationResponseRunSpec:
    return _clone_task12_wire(
        run_spec,
        local_record_types=(V3M0ApplicationResponseRunSpec,),
    )  # type: ignore[return-value]


class VerifiedV3M0ApplicationResponseRunSpec:
    """Opaque response-run specification bound to one live permit."""

    __slots__ = ("__run_spec", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        run_spec: V3M0ApplicationResponseRunSpec,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("application run spec is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedV3M0ApplicationResponseRunSpec__run_spec",
            run_spec,
        )
        object.__setattr__(
            self,
            "_VerifiedV3M0ApplicationResponseRunSpec__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedV3M0ApplicationResponseRunSpec__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("application run spec is immutable")

    @property
    def run_spec(self) -> V3M0ApplicationResponseRunSpec:
        return _reverify_verified_application_response_run_spec(self).run_spec


@dataclass(frozen=True)
class _RunSpecAuthority:
    run_spec: V3M0ApplicationResponseRunSpec
    permit: VerifiedCalibrationApplicationPermit
    digest: str
    seal: str


_RUN_SPEC_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedV3M0ApplicationResponseRunSpec],
        _RunSpecAuthority,
    ],
] = {}
_RUN_SPEC_LOCK = threading.RLock()


def _expected_run_spec(
    permit: VerifiedCalibrationApplicationPermit,
    *,
    _permit_reverifier=_reverify_verified_calibration_application_permit,
) -> V3M0ApplicationResponseRunSpec:
    permit_view = _permit_reverifier(permit)
    raw = permit_view.permit
    source_count = len(raw.source_basis.vectors_wire)
    provisional = V3M0ApplicationResponseRunSpec(
        run_spec_schema_version=APPLICATION_RESPONSE_RUN_SPEC_SCHEMA_VERSION,
        permit_sha=raw.permit_sha,
        application_spec_sha=raw.application_spec.application_spec_sha,
        fejer_order=raw.selected_fejer_order,
        source_basis=raw.source_basis,
        readout_basis=raw.readout_basis,
        response_grid=raw.response_grid,
        source_readout_bridge_grid=raw.source_readout_bridge_grid,
        source_readout_bridge_steps=raw.source_readout_bridge_steps,
        source_trial_vectors=freeze_complex_tensor(
            np.eye(source_count, dtype=np.complex128)
        ),
        bridge_tolerance=BRIDGE_TOLERANCE,
        run_spec_sha="0" * 64,
    )
    return replace(
        provisional,
        run_spec_sha=canonical_sha(
            v3m0_application_response_run_spec_payload(provisional)
        ),
    )


def _issue_run_spec(
    raw: V3M0ApplicationResponseRunSpec,
    permit: VerifiedCalibrationApplicationPermit,
) -> VerifiedV3M0ApplicationResponseRunSpec:
    digest = canonical_sha(v3m0_application_response_run_spec_payload(raw))
    seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-application-response-run-spec.v1"
            ),
            "run_spec_sha": raw.run_spec_sha,
            "body_digest": digest,
        }
    )
    wrapper = VerifiedV3M0ApplicationResponseRunSpec(
        _ISSUANCE_TOKEN,
        _clone_application_run_spec(raw),
        seal,
    )
    identity = id(wrapper)
    authority = _RunSpecAuthority(
        run_spec=_clone_application_run_spec(raw),
        permit=permit,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[VerifiedV3M0ApplicationResponseRunSpec],
        wrapper_id: int = identity,
    ) -> None:
        with _RUN_SPEC_LOCK:
            current = _RUN_SPEC_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _RUN_SPEC_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _RUN_SPEC_LOCK:
        _RUN_SPEC_LIVE[identity] = (reference, authority)
    return wrapper


def build_v3m0_application_response_run_spec(
    permit: VerifiedCalibrationApplicationPermit,
) -> VerifiedV3M0ApplicationResponseRunSpec:
    expected = _expected_run_spec(permit)
    return _issue_run_spec(expected, permit)


def verify_v3m0_application_response_run_spec(
    raw: V3M0ApplicationResponseRunSpec,
    permit: VerifiedCalibrationApplicationPermit,
) -> VerifiedV3M0ApplicationResponseRunSpec:
    _preflight_tree(raw, "raw application response run spec")
    _exact_record(
        raw,
        V3M0ApplicationResponseRunSpec,
        "raw application response run spec",
    )
    expected = _expected_run_spec(permit)
    if raw != expected:
        raise ValueError("application response run spec differs from permit")
    return _issue_run_spec(expected, permit)


@dataclass(frozen=True)
class _RunSpecView:
    run_spec: V3M0ApplicationResponseRunSpec
    permit: VerifiedCalibrationApplicationPermit


def _reverify_verified_application_response_run_spec(
    wrapper: VerifiedV3M0ApplicationResponseRunSpec,
) -> _RunSpecView:
    if type(wrapper) is not VerifiedV3M0ApplicationResponseRunSpec:
        raise TypeError("Task 12 requires a live application run spec")
    with _RUN_SPEC_LOCK:
        current = _RUN_SPEC_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("application run spec identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ApplicationResponseRunSpec__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ApplicationResponseRunSpec__run_spec",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ApplicationResponseRunSpec__seal",
        )
    except AttributeError as exc:
        raise ValueError("application run spec record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("application run spec token mismatch")
    expected = _expected_run_spec(authority.permit)
    raw_digest = canonical_sha(v3m0_application_response_run_spec_payload(raw))
    expected_digest = canonical_sha(
        v3m0_application_response_run_spec_payload(expected)
    )
    expected_seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-application-response-run-spec.v1"
            ),
            "run_spec_sha": expected.run_spec_sha,
            "body_digest": expected_digest,
        }
    )
    if (
        raw_digest != authority.digest
        or expected_digest != authority.digest
        or expected != authority.run_spec
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("application run spec immutable seal mismatch")
    return _RunSpecView(
        run_spec=_clone_application_run_spec(expected),
        permit=authority.permit,
    )


@dataclass(frozen=True)
class V3M0ScenarioOperationEvaluation:
    evaluation_schema_version: str
    operation: SyntheticApplicationOperation
    input_effect_digests: tuple[str, ...]
    effect_kind: str
    effect_tensor: FrozenComplexTensor
    effect_digest: str
    evaluation_sha: str

    def __post_init__(self) -> None:
        if (
            self.evaluation_schema_version
            != SCENARIO_OPERATION_EVALUATION_SCHEMA_VERSION
        ):
            raise ValueError("scenario operation evaluation schema is not frozen")
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


def v3m0_scenario_operation_evaluation_payload(
    evaluation: V3M0ScenarioOperationEvaluation,
) -> dict[str, object]:
    _exact_record(
        evaluation,
        V3M0ScenarioOperationEvaluation,
        "scenario operation evaluation",
    )
    return _payload_without_hash(evaluation, "evaluation_sha")


def _operation_parameter(
    operation: SyntheticApplicationOperation,
    name: str,
) -> TaggedScalarWire:
    matches = tuple(wire for key, wire in operation.parameters if key == name)
    if len(matches) != 1:
        raise ValueError(f"operation parameter {name!r} is not unique")
    return matches[0]


def _wire_fp64(wire: TaggedScalarWire, field: str) -> float:
    if wire.value_kind != "fp64-bits" or wire.fp64_bits_value is None:
        raise TypeError(f"{field} must be an fp64-bits TaggedScalarWire")
    return struct.unpack(">d", struct.pack(">Q", wire.fp64_bits_value))[0]


def _wire_integer(wire: TaggedScalarWire, field: str) -> int:
    if wire.value_kind != "integer" or wire.integer_value is None:
        raise TypeError(f"{field} must be an integer TaggedScalarWire")
    return wire.integer_value


def _wire_text(wire: TaggedScalarWire, field: str) -> str:
    if wire.value_kind != "text" or wire.text_value is None:
        raise TypeError(f"{field} must be a text TaggedScalarWire")
    return wire.text_value


def _scenario_spec(
    application: V3M0SyntheticControlApplicationSpec,
    scenario_id: str,
) -> ApplicationScenarioExecutionSpec:
    identifier = _text(scenario_id, "scenario_id")
    matches = tuple(
        scenario
        for scenario in application.scenario_execution_specs
        if scenario.scenario_id == identifier
    )
    if len(matches) != 1:
        raise ValueError("scenario_id is not uniquely parent-frozen")
    return matches[0]


def _scenario_operation_closure(
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
            raise ValueError("scenario output closure references a missing operation")
        required.add(identifier)
        pending.extend(operation.input_operation_instance_ids)
    return tuple(
        operation
        for operation in application.operations
        if operation.operation_instance_id in required
    )


def _evaluated_effect_digest(
    operation: SyntheticApplicationOperation,
    input_effect_digests: tuple[str, ...],
    effect_kind: str,
    effect: FrozenComplexTensor,
) -> str:
    return canonical_sha(
        {
            "effect_schema_version": "v3m0.executed-operation-effect.v1",
            "operation": {
                **synthetic_application_operation_payload(operation),
                "operation_sha": operation.operation_sha,
            },
            "input_effect_digests": list(input_effect_digests),
            "effect_kind": effect_kind,
            "effect_tensor": _wire(effect),
        }
    )


def _evaluate_c04_operation(
    operation: SyntheticApplicationOperation,
    inputs: tuple[np.ndarray, ...],
) -> tuple[str, np.ndarray]:
    if operation.operation_kind == "identity-v1":
        if inputs:
            raise ValueError("C04 identity operation must have no inputs")
        rank = _wire_integer(
            _operation_parameter(operation, "response-rank"),
            "response-rank",
        )
        if rank != 2:
            raise ValueError("C04 response rank is not frozen at two")
        return "response-matrix", np.eye(rank, dtype=np.complex128)
    if operation.operation_kind == "canonical-shear-v1":
        if len(inputs) != 1 or inputs[0].shape != (2, 2):
            raise ValueError("C04 canonical-angle operation input is malformed")
        squared = np.asarray(
            (
                _wire_fp64(
                    _operation_parameter(
                        operation,
                        "survival-squared-correlation-0",
                    ),
                    "survival-squared-correlation-0",
                ),
                _wire_fp64(
                    _operation_parameter(
                        operation,
                        "survival-squared-correlation-1",
                    ),
                    "survival-squared-correlation-1",
                ),
            ),
            dtype=np.float64,
        )
        if np.any(squared < 0.0) or np.any(squared > 1.0):
            raise ValueError("C04 squared correlations are outside [0,1]")
        return (
            "canonical-correlation-matrix",
            np.diag(np.sqrt(squared)).astype(np.complex128),
        )
    if operation.operation_kind == "geometry-subspace-v1":
        if len(inputs) != 1 or inputs[0].shape != (2, 2):
            raise ValueError("C04 survival readout input is malformed")
        readout = _wire_text(
            _operation_parameter(operation, "readout"),
            "readout",
        )
        if readout != "squared-canonical-correlation":
            raise ValueError("C04 readout operation is not frozen")
        singular = np.linalg.svd(inputs[0], compute_uv=False)
        squared = np.sort(np.square(singular))
        return "squared-canonical-correlations", squared.astype(np.complex128)
    raise ValueError("C04 operation kind has no closed evaluator")


def _evaluate_c04_operation_closure(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> tuple[V3M0ScenarioOperationEvaluation, ...]:
    evaluations: list[V3M0ScenarioOperationEvaluation] = []
    arrays: dict[str, np.ndarray] = {}
    digests: dict[str, str] = {}
    for operation in _scenario_operation_closure(application, scenario):
        input_arrays = tuple(
            arrays[identifier] for identifier in operation.input_operation_instance_ids
        )
        input_digests = tuple(
            digests[identifier] for identifier in operation.input_operation_instance_ids
        )
        effect_kind, values = _evaluate_c04_operation(operation, input_arrays)
        effect = freeze_complex_tensor(values)
        effect_digest = _evaluated_effect_digest(
            operation,
            input_digests,
            effect_kind,
            effect,
        )
        provisional = V3M0ScenarioOperationEvaluation(
            evaluation_schema_version=(SCENARIO_OPERATION_EVALUATION_SCHEMA_VERSION),
            operation=operation,
            input_effect_digests=input_digests,
            effect_kind=effect_kind,
            effect_tensor=effect,
            effect_digest=effect_digest,
            evaluation_sha="0" * 64,
        )
        evaluation = replace(
            provisional,
            evaluation_sha=canonical_sha(
                v3m0_scenario_operation_evaluation_payload(provisional)
            ),
        )
        evaluations.append(evaluation)
        arrays[operation.operation_instance_id] = values
        digests[operation.operation_instance_id] = effect_digest
    if tuple(arrays) != tuple(
        operation.operation_instance_id
        for operation in _scenario_operation_closure(application, scenario)
    ):
        raise AssertionError("C04 evaluator lost canonical operation order")
    return tuple(evaluations)


def _c04_recipe_from_scenario(
    scenario: ApplicationScenarioExecutionSpec,
) -> C04CanonicalAngleRecipe:
    if (
        scenario.execution_lane != "BLOCK_SUCCESS"
        or scenario.execution_recipe_id != C04_CANONICAL_ANGLE_RECIPE_ID
        or scenario.recipe_derivation_source_id != "c04-two-mode-split-step-analytic-v1"
        or scenario.expected_terminal_stage != "success"
        or scenario.expected_undefined_reason is not None
    ):
        raise ValueError("scenario is not the frozen C04 success recipe")
    parameters = dict(scenario.recipe_parameter_wires)
    if tuple(sorted(parameters)) != (
        "alpha",
        "analytic-residual-tolerance",
        "beta",
    ):
        raise ValueError("C04 recipe parameter reads are not exact")
    alpha = _wire_fp64(parameters["alpha"], "alpha")
    beta = _wire_fp64(parameters["beta"], "beta")
    tolerance = _wire_fp64(
        parameters["analytic-residual-tolerance"],
        "analytic-residual-tolerance",
    )
    if tolerance != 1.0e-15:
        raise ValueError("C04 analytic residual tolerance is not frozen")
    residuals = (
        abs(math.cos(2.0 * alpha) * math.cos(2.0 * beta) + 0.5),
        abs(
            math.sin(2.0 * alpha) * math.sin(2.0 * beta) + (math.sqrt(3.0) - 1.0) / 2.0
        ),
        abs(2.0 * (alpha - beta) + 5.0 * math.pi / 6.0),
        abs(2.0 * (alpha + beta) - math.acos(math.sqrt(3.0) / 2.0 - 1.0)),
    )
    if max(residuals) > tolerance:
        raise ValueError("C04 analytic angle equations exceed frozen tolerance")
    recipe = _build_c04_canonical_angle_recipe_from_angles(alpha, beta)
    return _verify_c04_canonical_angle_recipe(recipe)


def _c04_trace_and_operators(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
    recipe: C04CanonicalAngleRecipe,
    target_spec_id: str,
    interface: PrimitiveInterface,
) -> tuple[ConstructionTrace, tuple[PrimitiveOperatorWire, ...]]:
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
        for operation in application.operations
    ]
    blind_provenance_id = f"{scenario.scenario_id}.recipe-source"
    conditioned_provenance_id = f"{scenario.scenario_id}.target-conditioned-sign"
    provenance.extend(
        (
            ProvenanceNode(
                provenance_id=blind_provenance_id,
                operation=ProvenanceOperation.GRAMMAR_CONSTANT,
                depends_on=(),
                target_refs=(),
                objective_tags=(),
                search_run_id=None,
                source_sha=recipe.recipe_sha,
            ),
            ProvenanceNode(
                provenance_id=conditioned_provenance_id,
                operation=ProvenanceOperation.TARGET_SPEC_READ,
                depends_on=scenario.operation_output_ids,
                target_refs=(f"target:{target_spec_id}",),
                objective_tags=(),
                search_run_id=None,
                source_sha=scenario.scenario_sha,
            ),
        )
    )
    zero = (0,) * interface.spatial_ndim
    primitive_specs: list[PrimitiveSpec] = []
    operators: list[PrimitiveOperatorWire] = []
    for index, step in enumerate(recipe.steps):
        mechanism_id = f"{scenario.scenario_id}.shear.{index:03d}"
        production_id = (
            "target_operator" if step.target_conditioned else "local_canonical_shear"
        )
        layer_slot_id = f"{scenario.scenario_id}.layer.{index:03d}"
        coefficient = sp.Rational(*step.coefficient.as_integer_ratio())
        primitive_specs.append(
            PrimitiveSpec(
                mechanism_id=mechanism_id,
                production_id=production_id,
                # Execution order is frozen by the ordered primitive tuple.
                # A provenance dependency here would incorrectly propagate
                # target taint from the left C factor through every blind step.
                depends_on=(),
                support_offsets=tuple(sorted({zero, step.offset})),
                state_channels=tuple(
                    sorted((step.source_channel, step.destination_channel))
                ),
                coefficient_expression=coefficient,
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
    return (
        build_construction_trace(
            target_spec_id=target_spec_id,
            provenance_nodes=tuple(provenance),
            primitive_specs=tuple(primitive_specs),
        ),
        tuple(operators),
    )


def _interface_sha(interface: PrimitiveInterface) -> str:
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


def _materialize_c04_outcome(
    permit_view: _PermitView,
    scenario: ApplicationScenarioExecutionSpec,
    recipe: C04CanonicalAngleRecipe,
) -> tuple[AblationConstructionOutcome, str]:
    permit = permit_view.permit
    application = permit.application_spec
    calibration_view = _reverify_verified_window_threshold_calibration(
        permit_view.calibration
    )
    registry_view = _reverify_verified_control_registry(calibration_view.registry)
    if registry_view.parent is not permit_view.parent:
        raise ValueError("scenario materializer parent/calibration identity mismatch")
    carrier_bundle = registry_view.controls[0]
    carrier_factory = _reverify_verified_factory(carrier_bundle.factory)
    source = permit.source_basis
    readout = permit.readout_basis
    if (
        source.state_schema_id != readout.state_schema_id
        or source.channel_order != readout.channel_order
        or source.channel_order != recipe.channel_order
    ):
        raise ValueError("C04 scenario interface differs from its frozen recipe")
    interface = PrimitiveInterface(
        interface_id=f"interface.{scenario.scenario_id}.v1",
        state_schema_id=source.state_schema_id,
        spatial_ndim=application.grid_protocol.spatial_ndim,
        channel_order=source.channel_order,
        dtype="complex128",
        backend="numpy",
    )
    trace, operators = _c04_trace_and_operators(
        application,
        scenario,
        recipe,
        carrier_bundle.target.target_spec_id,
        interface,
    )
    actual = build_factory_from_trace(
        trace,
        carrier_bundle.target,
        factory_id=f"factory.{scenario.scenario_id}.v1",
        interface=interface,
        state_shape=(len(source.channel_order),)
        + application.grid_protocol.spatial_shape,
        dt=carrier_factory.factory.dt,
        target_blind_parameters=(
            ("alpha", recipe.alpha),
            ("beta", recipe.beta),
        ),
        layer_slot_ids=tuple(operator.layer_slot_id for operator in operators),
        operator_payload=operators,
        source_manifest_id=source.manifest_id,
        readout_basis=readout,
        boundary_manifest_id="periodic-v1",
    )
    outcome = _verify_construction_outcome(matched_ablation(actual))
    if not outcome.status.defined or outcome.pair is None:
        raise ValueError("C04 scenario materializer did not form a matched pair")
    return outcome, _interface_sha(interface)


@dataclass(frozen=True)
class V3M0ScenarioConstruction:
    construction_schema_version: str
    permit: CalibrationApplicationPermit
    scenario_spec: ApplicationScenarioExecutionSpec
    operation_evaluations: tuple[V3M0ScenarioOperationEvaluation, ...]
    operation_effect_digests: tuple[tuple[str, str], ...]
    recipe_id: str
    recipe_derivation_source_id: str
    recipe_parameter_reads: tuple[tuple[str, TaggedScalarWire], ...]
    recipe_sha: str
    construction_status: BlockStatus
    ablation_pair_snapshot: AblationPairSnapshot
    interface_sha: str
    source_basis_sha: str
    readout_basis_sha: str
    response_grid_sha: str
    bridge_grid_sha: str
    run_spec_sha: str
    actual_effect_digest: str
    ablated_effect_digest: str
    actual_factory_sha: str
    ablated_factory_sha: str
    ablation_manifest_sha: str
    ablation_construction_sha: str
    construction_sha: str

    def __post_init__(self) -> None:
        if self.construction_schema_version != SCENARIO_CONSTRUCTION_SCHEMA_VERSION:
            raise ValueError("scenario construction schema is not frozen")
        if type(self.permit) is not CalibrationApplicationPermit:
            raise TypeError("scenario construction permit has the wrong strict type")
        if type(self.scenario_spec) is not ApplicationScenarioExecutionSpec:
            raise TypeError("scenario_spec has the wrong strict type")
        if self.scenario_spec.execution_lane != "BLOCK_SUCCESS":
            raise ValueError("scenario construction is only a success-path capability")
        if (
            type(self.operation_evaluations) is not tuple
            or not self.operation_evaluations
            or not all(
                type(item) is V3M0ScenarioOperationEvaluation
                for item in self.operation_evaluations
            )
        ):
            raise TypeError("operation_evaluations have the wrong strict type")
        expected_effect_digests = tuple(
            (
                item.operation.operation_instance_id,
                item.effect_digest,
            )
            for item in self.operation_evaluations
        )
        if self.operation_effect_digests != expected_effect_digests:
            raise ValueError("operation effect digest index does not match evaluations")
        if self.recipe_id != self.scenario_spec.execution_recipe_id:
            raise ValueError("construction recipe ID differs from scenario")
        if (
            self.recipe_derivation_source_id
            != self.scenario_spec.recipe_derivation_source_id
        ):
            raise ValueError("construction recipe source differs from scenario")
        if self.recipe_parameter_reads != self.scenario_spec.recipe_parameter_wires:
            raise ValueError("construction recipe parameter reads differ from scenario")
        if type(self.construction_status) is not BlockStatus:
            raise TypeError("construction_status has the wrong strict type")
        if type(self.ablation_pair_snapshot) is not AblationPairSnapshot:
            raise TypeError("ablation_pair_snapshot has the wrong strict type")
        for field in (
            "recipe_sha",
            "interface_sha",
            "source_basis_sha",
            "readout_basis_sha",
            "response_grid_sha",
            "bridge_grid_sha",
            "run_spec_sha",
            "actual_effect_digest",
            "ablated_effect_digest",
            "actual_factory_sha",
            "ablated_factory_sha",
            "ablation_manifest_sha",
            "ablation_construction_sha",
            "construction_sha",
        ):
            _sha(getattr(self, field), field)
        snapshot = self.ablation_pair_snapshot
        if (
            not self.construction_status.defined
            or self.construction_status != snapshot.construction_status
        ):
            raise ValueError("scenario construction did not produce a defined pair")
        if (
            self.actual_factory_sha != snapshot.actual_factory.factory_sha
            or self.ablated_factory_sha != snapshot.ablated_factory.factory_sha
            or self.ablation_manifest_sha != snapshot.ablation_manifest.manifest_sha
            or self.ablation_construction_sha != snapshot.ablation_construction_sha
        ):
            raise ValueError("scenario construction summary differs from pair snapshot")
        if self.actual_effect_digest == self.ablated_effect_digest:
            raise ValueError("C04 actual and ablated execution effects must differ")


def v3m0_scenario_construction_payload(
    construction: V3M0ScenarioConstruction,
) -> dict[str, object]:
    _exact_record(
        construction,
        V3M0ScenarioConstruction,
        "V3-M0 scenario construction",
    )
    return _payload_without_hash(construction, "construction_sha")


def _clone_scenario_construction(
    construction: V3M0ScenarioConstruction,
) -> V3M0ScenarioConstruction:
    return _clone_task12_wire(
        construction,
        local_record_types=(
            SelectedControlEvidenceRef,
            WindowThresholdSelection,
            WindowThresholdCalibrationManifest,
            CalibrationApplicationPermit,
            C04LocalShearStep,
            C04CanonicalAngleRecipe,
            V3M0ScenarioOperationEvaluation,
            V3M0ScenarioConstruction,
        ),
        candidate_record_types=_candidate_record_types(
            construction.permit.calibration_manifest
        ),
    )  # type: ignore[return-value]


def _expected_scenario_construction(
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
    *,
    _permit_reverifier=_reverify_verified_calibration_application_permit,
) -> tuple[
    V3M0ScenarioConstruction,
    AblationConstructionOutcome,
    VerifiedFactory,
    VerifiedFactory,
]:
    permit_view = _permit_reverifier(permit)
    application = permit_view.permit.application_spec
    scenario = _scenario_spec(application, scenario_id)
    if application.control_case_id != "C04_CANONICAL_ANGLE_025_075":
        raise ValueError("this closed materializer currently implements only C04")
    recipe = _c04_recipe_from_scenario(scenario)
    evaluations = _evaluate_c04_operation_closure(application, scenario)
    final_values = frozen_tensor_array(evaluations[-1].effect_tensor)
    np.testing.assert_allclose(
        final_values.real,
        np.asarray((0.25, 0.75), dtype=np.float64),
        rtol=0.0,
        atol=2.0e-15,
    )
    outcome, interface_sha = _materialize_c04_outcome(
        permit_view,
        scenario,
        recipe,
    )
    snapshot, actual, ablated = _pair_snapshot(outcome)
    run_spec = _expected_run_spec(permit)
    provisional = V3M0ScenarioConstruction(
        construction_schema_version=SCENARIO_CONSTRUCTION_SCHEMA_VERSION,
        permit=permit_view.permit,
        scenario_spec=scenario,
        operation_evaluations=evaluations,
        operation_effect_digests=tuple(
            (
                evaluation.operation.operation_instance_id,
                evaluation.effect_digest,
            )
            for evaluation in evaluations
        ),
        recipe_id=scenario.execution_recipe_id,
        recipe_derivation_source_id=scenario.recipe_derivation_source_id,
        recipe_parameter_reads=scenario.recipe_parameter_wires,
        recipe_sha=recipe.recipe_sha,
        construction_status=outcome.status,
        ablation_pair_snapshot=snapshot,
        interface_sha=interface_sha,
        source_basis_sha=permit_view.permit.source_basis.manifest_id,
        readout_basis_sha=permit_view.permit.readout_basis.manifest_id,
        response_grid_sha=permit_view.permit.response_grid.response_grid_sha,
        bridge_grid_sha=(permit_view.permit.source_readout_bridge_grid.bridge_grid_sha),
        run_spec_sha=run_spec.run_spec_sha,
        actual_effect_digest=recipe.actual_effect_digest,
        ablated_effect_digest=recipe.ablated_effect_digest,
        actual_factory_sha=snapshot.actual_factory.factory_sha,
        ablated_factory_sha=snapshot.ablated_factory.factory_sha,
        ablation_manifest_sha=snapshot.ablation_manifest.manifest_sha,
        ablation_construction_sha=snapshot.ablation_construction_sha,
        construction_sha="0" * 64,
    )
    construction = replace(
        provisional,
        construction_sha=canonical_sha(v3m0_scenario_construction_payload(provisional)),
    )
    return construction, outcome, actual, ablated


class VerifiedV3M0ScenarioConstruction:
    """Opaque capability for one exact parent-frozen application scenario."""

    __slots__ = ("__construction", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        construction: V3M0ScenarioConstruction,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("scenario construction is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedV3M0ScenarioConstruction__construction",
            construction,
        )
        object.__setattr__(
            self,
            "_VerifiedV3M0ScenarioConstruction__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedV3M0ScenarioConstruction__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("scenario construction is immutable")

    @property
    def construction(self) -> V3M0ScenarioConstruction:
        return _reverify_verified_scenario_construction(self).construction

    @property
    def actual_factory(self) -> VerifiedFactory:
        return _reverify_verified_scenario_construction(self).actual

    @property
    def ablated_factory(self) -> VerifiedFactory:
        return _reverify_verified_scenario_construction(self).ablated


@dataclass(frozen=True)
class _ScenarioConstructionAuthority:
    exposed: V3M0ScenarioConstruction
    snapshot: V3M0ScenarioConstruction
    permit: VerifiedCalibrationApplicationPermit
    scenario_id: str
    outcome: AblationConstructionOutcome
    actual: VerifiedFactory
    ablated: VerifiedFactory
    digest: str
    seal: str


@dataclass(frozen=True)
class _ScenarioConstructionView:
    construction: V3M0ScenarioConstruction
    permit: VerifiedCalibrationApplicationPermit
    outcome: AblationConstructionOutcome
    actual: VerifiedFactory
    ablated: VerifiedFactory


_SCENARIO_CONSTRUCTION_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedV3M0ScenarioConstruction],
        _ScenarioConstructionAuthority,
    ],
] = {}
_SCENARIO_CONSTRUCTION_LOCK = threading.RLock()


def _scenario_construction_seal(
    construction: V3M0ScenarioConstruction,
    outcome: AblationConstructionOutcome,
) -> str:
    snapshot, actual, ablated = _pair_snapshot(outcome)
    actual_view = _reverify_verified_factory(actual)
    ablated_view = _reverify_verified_factory(ablated)
    if (
        snapshot != construction.ablation_pair_snapshot
        or actual_view.factory.factory_sha != construction.actual_factory_sha
        or ablated_view.factory.factory_sha != construction.ablated_factory_sha
    ):
        raise ValueError("scenario construction/live pair mismatch")
    return canonical_sha(
        {
            "verified_schema_version": "v3m0.verified-scenario-construction.v1",
            "construction": {
                **v3m0_scenario_construction_payload(construction),
                "construction_sha": construction.construction_sha,
            },
            "live_actual_factory_sha": actual_view.factory.factory_sha,
            "live_ablated_factory_sha": ablated_view.factory.factory_sha,
            "live_ablation_manifest_sha": snapshot.ablation_manifest.manifest_sha,
        }
    )


def _issue_scenario_construction(
    construction: V3M0ScenarioConstruction,
    permit: VerifiedCalibrationApplicationPermit,
    outcome: AblationConstructionOutcome,
    actual: VerifiedFactory,
    ablated: VerifiedFactory,
) -> VerifiedV3M0ScenarioConstruction:
    exposed = _clone_scenario_construction(construction)
    snapshot = _clone_scenario_construction(construction)
    digest = canonical_sha(v3m0_scenario_construction_payload(snapshot))
    if digest != snapshot.construction_sha:
        raise ValueError("scenario construction self-hash mismatch")
    seal = _scenario_construction_seal(snapshot, outcome)
    wrapper = VerifiedV3M0ScenarioConstruction(
        _ISSUANCE_TOKEN,
        exposed,
        seal,
    )
    identity = id(wrapper)
    authority = _ScenarioConstructionAuthority(
        exposed=exposed,
        snapshot=snapshot,
        permit=permit,
        scenario_id=construction.scenario_spec.scenario_id,
        outcome=outcome,
        actual=actual,
        ablated=ablated,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[VerifiedV3M0ScenarioConstruction],
        wrapper_id: int = identity,
    ) -> None:
        with _SCENARIO_CONSTRUCTION_LOCK:
            current = _SCENARIO_CONSTRUCTION_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _SCENARIO_CONSTRUCTION_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _SCENARIO_CONSTRUCTION_LOCK:
        _SCENARIO_CONSTRUCTION_LIVE[identity] = (reference, authority)
    return wrapper


def materialize_v3m0_scenario_construction(
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
) -> VerifiedV3M0ScenarioConstruction:
    """Execute one exact ParentFreeze scenario into its matched local pair."""

    construction, outcome, actual, ablated = _expected_scenario_construction(
        permit,
        scenario_id,
    )
    return _issue_scenario_construction(
        construction,
        permit,
        outcome,
        actual,
        ablated,
    )


def verify_v3m0_scenario_construction(
    construction: V3M0ScenarioConstruction,
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
) -> VerifiedV3M0ScenarioConstruction:
    """Hydrate only by replaying the permit, scenario recipe and executor pair."""

    _preflight_tree(construction, "raw V3-M0 scenario construction")
    _exact_record(
        construction,
        V3M0ScenarioConstruction,
        "raw V3-M0 scenario construction",
    )
    construction.__post_init__()
    if construction.construction_sha != canonical_sha(
        v3m0_scenario_construction_payload(construction)
    ):
        raise ValueError("scenario construction SHA does not match complete body")
    expected, outcome, actual, ablated = _expected_scenario_construction(
        permit,
        scenario_id,
    )
    if construction != expected:
        raise ValueError("raw scenario construction differs from closed replay")
    return _issue_scenario_construction(
        expected,
        permit,
        outcome,
        actual,
        ablated,
    )


def _reverify_verified_scenario_construction(
    wrapper: VerifiedV3M0ScenarioConstruction,
    *,
    _expected_builder=_expected_scenario_construction,
) -> _ScenarioConstructionView:
    if type(wrapper) is not VerifiedV3M0ScenarioConstruction:
        raise TypeError("Task 12 requires a live scenario construction")
    with _SCENARIO_CONSTRUCTION_LOCK:
        current = _SCENARIO_CONSTRUCTION_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("scenario construction identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ScenarioConstruction__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ScenarioConstruction__construction",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ScenarioConstruction__seal",
        )
    except AttributeError as exc:
        raise ValueError("scenario construction record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("scenario construction token mismatch")
    expected, _, _, _ = _expected_builder(
        authority.permit,
        authority.scenario_id,
    )
    live_snapshot, live_actual, live_ablated = _pair_snapshot(authority.outcome)
    observed_digest = canonical_sha(v3m0_scenario_construction_payload(raw))
    snapshot_digest = canonical_sha(
        v3m0_scenario_construction_payload(authority.snapshot)
    )
    expected_digest = canonical_sha(v3m0_scenario_construction_payload(expected))
    expected_seal = _scenario_construction_seal(
        authority.snapshot,
        authority.outcome,
    )
    if (
        raw is not authority.exposed
        or raw != authority.snapshot
        or expected != authority.snapshot
        or observed_digest != authority.digest
        or snapshot_digest != authority.digest
        or expected_digest != authority.digest
        or live_snapshot != authority.snapshot.ablation_pair_snapshot
        or live_actual is not authority.actual
        or live_ablated is not authority.ablated
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("scenario construction immutable seal mismatch")
    return _ScenarioConstructionView(
        construction=_clone_scenario_construction(authority.snapshot),
        permit=authority.permit,
        outcome=authority.outcome,
        actual=authority.actual,
        ablated=authority.ablated,
    )


VerifiedV3M0ScenarioConstruction._prestructure_reverify = (  # type: ignore[attr-defined]
    _make_prestructure_child_reverifier(
        VerifiedV3M0ScenarioConstruction,
        _reverify_verified_scenario_construction,
        "_prestructure_reverify_scenario_construction",
    )
)


_ATTEMPT_ACTIVATION_LABELS = ("null", "grey", "signal")
_ATTEMPT_STAGE_PREFIXES = {
    "trace": ("trace",),
    "stability": ("trace", "stability"),
    "activation": ("trace", "stability", "activation"),
    "endpoint_shell": (
        "trace",
        "stability",
        "activation",
        "endpoint_shell",
    ),
}
_C14_TYPED_FAULTS = {
    ("endpoint-shell-ambiguous", "phase-band-empty"): (
        "endpoint_shell",
        UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS,
        "endpoint-shell-fault-injection-v1",
    ),
    ("response-null", "actual-rank-zero"): (
        "activation",
        UndefinedReason.RESPONSE_NULL,
        "response-null-fault-injection-v1",
    ),
    ("trace-unclassified", "unclassified"): (
        "trace",
        UndefinedReason.TRACE_UNCLASSIFIED,
        "trace-unclassified-fault-injection-v1",
    ),
    ("unstable", "spectral-radius-above-one"): (
        "stability",
        UndefinedReason.UNSTABLE,
        "unstable-fault-injection-v1",
    ),
}


def _validate_attempt_measurements(
    raw_singular_values: tuple[float, ...],
    activation_labels: tuple[str, ...],
) -> None:
    if type(raw_singular_values) is not tuple:
        raise TypeError("raw_singular_values must be a tuple")
    previous = math.inf
    for index, value in enumerate(raw_singular_values):
        if type(value) is not float or not math.isfinite(value) or value < 0.0:
            raise ValueError(
                f"raw_singular_values[{index}] must be finite non-negative fp64"
            )
        if value > previous:
            raise ValueError("raw_singular_values must be non-increasing")
        previous = value
    if type(activation_labels) is not tuple:
        raise TypeError("activation_labels must be a tuple")
    if len(activation_labels) != len(raw_singular_values):
        raise ValueError("activation labels must align with singular values")
    if not all(
        type(label) is str and label in _ATTEMPT_ACTIVATION_LABELS
        for label in activation_labels
    ):
        raise ValueError("activation label is outside the closed registry")


@dataclass(frozen=True)
class ResponseBlockAttemptPrecursorEvidence:
    precursor_schema_version: str
    permit: CalibrationApplicationPermit
    application_spec: V3M0SyntheticControlApplicationSpec
    scenario_spec: ApplicationScenarioExecutionSpec
    operation_evaluations: tuple[V3M0ScenarioOperationEvaluation, ...]
    reached_stages: tuple[str, ...]
    terminal_stage: str
    status: BlockStatus
    raw_singular_values: tuple[float, ...]
    activation_labels: tuple[Literal["null", "grey", "signal"], ...]
    fault_mode: Optional[str]
    series_code: Optional[str]
    precursor_sha: str

    def __post_init__(self) -> None:
        if (
            self.precursor_schema_version
            != RESPONSE_BLOCK_ATTEMPT_PRECURSOR_SCHEMA_VERSION
        ):
            raise ValueError("response attempt precursor schema is not frozen")
        if type(self.permit) is not CalibrationApplicationPermit:
            raise TypeError("response attempt permit has the wrong strict type")
        if type(self.application_spec) is not V3M0SyntheticControlApplicationSpec:
            raise TypeError("response attempt application has the wrong strict type")
        if type(self.scenario_spec) is not ApplicationScenarioExecutionSpec:
            raise TypeError("response attempt scenario has the wrong strict type")
        if self.application_spec != self.permit.application_spec:
            raise ValueError("response attempt application differs from permit")
        if (
            self.scenario_spec.execution_lane != "EXPECTED_TYPED_TERMINATION"
            or self.scenario_spec not in self.application_spec.scenario_execution_specs
        ):
            raise ValueError(
                "response attempt scenario is not parent-frozen typed lane"
            )
        if (
            type(self.operation_evaluations) is not tuple
            or not self.operation_evaluations
            or not all(
                type(item) is V3M0ScenarioOperationEvaluation
                for item in self.operation_evaluations
            )
        ):
            raise TypeError("response attempt operation evaluations are malformed")
        if self.terminal_stage not in _ATTEMPT_STAGE_PREFIXES:
            raise ValueError("response attempt terminal stage is outside the registry")
        if self.reached_stages != _ATTEMPT_STAGE_PREFIXES[self.terminal_stage]:
            raise ValueError("response attempt reached-stage prefix is not exact")
        if type(self.status) is not BlockStatus or self.status.defined:
            raise ValueError("response attempt precursor must have undefined status")
        if (
            self.terminal_stage != self.scenario_spec.expected_terminal_stage
            or self.status.reason is not self.scenario_spec.expected_undefined_reason
        ):
            raise ValueError(
                "response attempt precursor differs from scenario prophecy"
            )
        _validate_attempt_measurements(
            self.raw_singular_values,
            self.activation_labels,
        )
        if (self.fault_mode is None) != (self.series_code is None):
            raise ValueError("fault_mode and series_code must be present together")
        if self.fault_mode is not None:
            _text(self.fault_mode, "fault_mode")
            _text(self.series_code, "series_code")
        _sha(self.precursor_sha, "precursor_sha")


def response_block_attempt_precursor_evidence_payload(
    precursor: ResponseBlockAttemptPrecursorEvidence,
) -> dict[str, object]:
    _exact_record(
        precursor,
        ResponseBlockAttemptPrecursorEvidence,
        "response block attempt precursor",
    )
    return _payload_without_hash(precursor, "precursor_sha")


@dataclass(frozen=True)
class ResponseBlockAttemptOutcome:
    attempt_schema_version: str
    application_spec: V3M0SyntheticControlApplicationSpec
    scenario_spec: ApplicationScenarioExecutionSpec
    permit: CalibrationApplicationPermit
    terminal_stage: str
    status: BlockStatus
    raw_singular_values: tuple[float, ...]
    activation_labels: tuple[Literal["null", "grey", "signal"], ...]
    precursor_evidence_sha: str
    downstream_capability_issued: Literal[False]
    outcome_sha: str

    def __post_init__(self) -> None:
        if self.attempt_schema_version != RESPONSE_BLOCK_ATTEMPT_OUTCOME_SCHEMA_VERSION:
            raise ValueError("response block attempt schema is not frozen")
        if type(self.application_spec) is not V3M0SyntheticControlApplicationSpec:
            raise TypeError("response attempt application has the wrong strict type")
        if type(self.scenario_spec) is not ApplicationScenarioExecutionSpec:
            raise TypeError("response attempt scenario has the wrong strict type")
        if type(self.permit) is not CalibrationApplicationPermit:
            raise TypeError("response attempt permit has the wrong strict type")
        if self.application_spec != self.permit.application_spec:
            raise ValueError("response attempt application differs from permit")
        if (
            self.scenario_spec.execution_lane != "EXPECTED_TYPED_TERMINATION"
            or self.scenario_spec not in self.application_spec.scenario_execution_specs
        ):
            raise ValueError(
                "response attempt scenario is not parent-frozen typed lane"
            )
        if self.terminal_stage not in _ATTEMPT_STAGE_PREFIXES:
            raise ValueError("response attempt terminal stage is outside the registry")
        if type(self.status) is not BlockStatus or self.status.defined:
            raise ValueError("response block attempt must terminate undefined")
        if (
            self.terminal_stage != self.scenario_spec.expected_terminal_stage
            or self.status.reason is not self.scenario_spec.expected_undefined_reason
        ):
            raise ValueError("response attempt differs from parent-frozen prophecy")
        _validate_attempt_measurements(
            self.raw_singular_values,
            self.activation_labels,
        )
        _sha(self.precursor_evidence_sha, "precursor_evidence_sha")
        if self.downstream_capability_issued is not False:
            raise ValueError("typed termination cannot issue downstream capability")
        _sha(self.outcome_sha, "outcome_sha")


def response_block_attempt_outcome_payload(
    outcome: ResponseBlockAttemptOutcome,
) -> dict[str, object]:
    _exact_record(
        outcome,
        ResponseBlockAttemptOutcome,
        "response block attempt outcome",
    )
    return _payload_without_hash(outcome, "outcome_sha")


def _protocol_constant_fp64(
    application: V3M0SyntheticControlApplicationSpec,
    name: str,
) -> float:
    matches = tuple(
        wire
        for constant_name, wire in application.protocol_constant_payload.tagged_constants
        if constant_name == name
    )
    if len(matches) != 1:
        raise ValueError(f"protocol constant {name!r} is not unique")
    return _wire_fp64(matches[0], name)


def _evaluate_typed_termination_operation(
    operation: SyntheticApplicationOperation,
    inputs: tuple[np.ndarray, ...],
) -> tuple[str, np.ndarray]:
    if operation.operation_kind == "identity-v1":
        if inputs:
            raise ValueError("typed identity operation must have no inputs")
        rank = _wire_integer(
            _operation_parameter(operation, "response-rank"),
            "response-rank",
        )
        if rank <= 0:
            raise ValueError("typed identity response rank must be positive")
        return "response-matrix", np.eye(rank, dtype=np.complex128)
    if operation.operation_kind == "amplitude-rescale-v1":
        if len(inputs) != 1 or inputs[0].ndim != 2:
            raise ValueError("typed amplitude operation input is malformed")
        scale = _wire_fp64(
            _operation_parameter(operation, "amplitude-scale"),
            "amplitude-scale",
        )
        return "amplitude-rescaled-response", scale * inputs[0]
    if operation.operation_kind == "direct-sum-v1":
        if not inputs or not all(array.ndim == 2 for array in inputs):
            raise ValueError("typed direct-sum inputs are malformed")
        expected_count = _wire_integer(
            _operation_parameter(operation, "component-count"),
            "component-count",
        )
        if expected_count != len(inputs):
            raise ValueError("typed direct-sum component count is not exact")
        rows = sum(array.shape[0] for array in inputs)
        columns = sum(array.shape[1] for array in inputs)
        result = np.zeros((rows, columns), dtype=np.complex128)
        row = 0
        column = 0
        for array in inputs:
            next_row = row + array.shape[0]
            next_column = column + array.shape[1]
            result[row:next_row, column:next_column] = array
            row = next_row
            column = next_column
        return "direct-sum-response", result
    if operation.operation_kind == "deterministic-series-v1":
        if inputs:
            raise ValueError("typed deterministic fault operation has inputs")
        fault_mode = _wire_text(
            _operation_parameter(operation, "fault-mode"),
            "fault-mode",
        )
        series_code = _wire_text(
            _operation_parameter(operation, "series-code"),
            "series-code",
        )
        effect_by_fault = {
            ("endpoint-shell-ambiguous", "phase-band-empty"): np.asarray(
                ((1.0j,),),
                dtype=np.complex128,
            ),
            ("response-null", "actual-rank-zero"): np.zeros(
                (1, 1),
                dtype=np.complex128,
            ),
            ("trace-unclassified", "unclassified"): np.asarray(
                ((0.0, 1.0), (0.0, 0.0)),
                dtype=np.complex128,
            ),
            ("unstable", "spectral-radius-above-one"): np.asarray(
                ((1.125,),),
                dtype=np.complex128,
            ),
        }
        try:
            effect = effect_by_fault[(fault_mode, series_code)]
        except KeyError as exc:
            raise ValueError(
                "typed deterministic fault is outside the registry"
            ) from exc
        return f"deterministic-series:{fault_mode}:{series_code}", effect
    raise ValueError("typed termination operation kind has no closed evaluator")


def _evaluate_typed_termination_operation_closure(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
) -> tuple[V3M0ScenarioOperationEvaluation, ...]:
    closure = _scenario_operation_closure(application, scenario)
    evaluations: list[V3M0ScenarioOperationEvaluation] = []
    arrays: dict[str, np.ndarray] = {}
    digests: dict[str, str] = {}
    for operation in closure:
        input_arrays = tuple(
            arrays[identifier] for identifier in operation.input_operation_instance_ids
        )
        input_digests = tuple(
            digests[identifier] for identifier in operation.input_operation_instance_ids
        )
        effect_kind, values = _evaluate_typed_termination_operation(
            operation,
            input_arrays,
        )
        effect = freeze_complex_tensor(values)
        effect_digest = _evaluated_effect_digest(
            operation,
            input_digests,
            effect_kind,
            effect,
        )
        provisional = V3M0ScenarioOperationEvaluation(
            evaluation_schema_version=SCENARIO_OPERATION_EVALUATION_SCHEMA_VERSION,
            operation=operation,
            input_effect_digests=input_digests,
            effect_kind=effect_kind,
            effect_tensor=effect,
            effect_digest=effect_digest,
            evaluation_sha="0" * 64,
        )
        evaluation = replace(
            provisional,
            evaluation_sha=canonical_sha(
                v3m0_scenario_operation_evaluation_payload(provisional)
            ),
        )
        evaluations.append(evaluation)
        arrays[operation.operation_instance_id] = values
        digests[operation.operation_instance_id] = effect_digest
    return tuple(evaluations)


def _typed_attempt_measurements(
    application: V3M0SyntheticControlApplicationSpec,
    scenario: ApplicationScenarioExecutionSpec,
    evaluations: tuple[V3M0ScenarioOperationEvaluation, ...],
) -> tuple[
    tuple[float, ...],
    tuple[Literal["null", "grey", "signal"], ...],
    Optional[str],
    Optional[str],
]:
    if not evaluations:
        raise ValueError("typed attempt has no operation evaluation")
    final_evaluation = evaluations[-1]
    if (
        final_evaluation.operation.operation_instance_id
        not in scenario.operation_output_ids
    ):
        raise ValueError("typed attempt final evaluation is not a scenario output")
    fault_mode: Optional[str] = None
    series_code: Optional[str] = None
    if final_evaluation.operation.operation_kind == "deterministic-series-v1":
        fault_mode = _wire_text(
            _operation_parameter(final_evaluation.operation, "fault-mode"),
            "fault-mode",
        )
        series_code = _wire_text(
            _operation_parameter(final_evaluation.operation, "series-code"),
            "series-code",
        )
        try:
            expected_stage, expected_reason, expected_recipe = _C14_TYPED_FAULTS[
                (fault_mode, series_code)
            ]
        except KeyError as exc:
            raise ValueError("typed fault pair is outside the frozen registry") from exc
        if (
            application.control_case_id != "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL"
            or scenario.expected_terminal_stage != expected_stage
            or scenario.expected_undefined_reason is not expected_reason
            or scenario.execution_recipe_id != expected_recipe
        ):
            raise ValueError("typed fault does not match its parent-frozen scenario")

    if scenario.expected_terminal_stage in ("trace", "stability"):
        return (), (), fault_mode, series_code

    final = frozen_tensor_array(final_evaluation.effect_tensor)
    if final.ndim != 2:
        raise ValueError("activation attempt output is not a response matrix")
    singular_values = tuple(
        float(value) for value in np.linalg.svd(final, compute_uv=False)
    )
    null_upper = _protocol_constant_fp64(
        application,
        "amplitude-null-upper-fp64-bits",
    )
    signal_lower = _protocol_constant_fp64(
        application,
        "amplitude-signal-lower-fp64-bits",
    )
    if not 0.0 < null_upper < signal_lower:
        raise ValueError("activation thresholds are not ordered")
    labels: tuple[Literal["null", "grey", "signal"], ...] = tuple(
        ("null" if value < null_upper else "signal" if value > signal_lower else "grey")
        for value in singular_values
    )
    if scenario.expected_undefined_reason is UndefinedReason.RESPONSE_NULL:
        if not labels or any(label != "null" for label in labels):
            raise ValueError("RESPONSE_NULL attempt is not wholly null")
    elif scenario.expected_undefined_reason is UndefinedReason.RESPONSE_GREY:
        if "grey" not in labels:
            raise ValueError("RESPONSE_GREY attempt has no grey singular value")
    else:
        if fault_mode is None:
            raise ValueError("non-activation typed reason lacks a fault artifact")
    return singular_values, labels, fault_mode, series_code


def _expected_response_block_attempt(
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
) -> tuple[
    ResponseBlockAttemptOutcome,
    ResponseBlockAttemptPrecursorEvidence,
]:
    permit_view = _reverify_verified_calibration_application_permit(permit)
    raw_permit = permit_view.permit
    application = raw_permit.application_spec
    scenario = _scenario_spec(application, scenario_id)
    if scenario.execution_lane != "EXPECTED_TYPED_TERMINATION":
        raise ValueError("scenario is not an expected typed termination")
    if (
        scenario.expected_terminal_stage not in _ATTEMPT_STAGE_PREFIXES
        or type(scenario.expected_undefined_reason) is not UndefinedReason
    ):
        raise ValueError("typed termination prophecy is incomplete")
    evaluations = _evaluate_typed_termination_operation_closure(
        application,
        scenario,
    )
    singular_values, labels, fault_mode, series_code = _typed_attempt_measurements(
        application,
        scenario,
        evaluations,
    )
    status = BlockStatus(False, scenario.expected_undefined_reason)
    precursor_provisional = ResponseBlockAttemptPrecursorEvidence(
        precursor_schema_version=RESPONSE_BLOCK_ATTEMPT_PRECURSOR_SCHEMA_VERSION,
        permit=raw_permit,
        application_spec=application,
        scenario_spec=scenario,
        operation_evaluations=evaluations,
        reached_stages=_ATTEMPT_STAGE_PREFIXES[scenario.expected_terminal_stage],
        terminal_stage=scenario.expected_terminal_stage,
        status=status,
        raw_singular_values=singular_values,
        activation_labels=labels,
        fault_mode=fault_mode,
        series_code=series_code,
        precursor_sha="0" * 64,
    )
    precursor = replace(
        precursor_provisional,
        precursor_sha=canonical_sha(
            response_block_attempt_precursor_evidence_payload(precursor_provisional)
        ),
    )
    outcome_provisional = ResponseBlockAttemptOutcome(
        attempt_schema_version=RESPONSE_BLOCK_ATTEMPT_OUTCOME_SCHEMA_VERSION,
        application_spec=application,
        scenario_spec=scenario,
        permit=raw_permit,
        terminal_stage=scenario.expected_terminal_stage,
        status=status,
        raw_singular_values=singular_values,
        activation_labels=labels,
        precursor_evidence_sha=precursor.precursor_sha,
        downstream_capability_issued=False,
        outcome_sha="0" * 64,
    )
    outcome = replace(
        outcome_provisional,
        outcome_sha=canonical_sha(
            response_block_attempt_outcome_payload(outcome_provisional)
        ),
    )
    return outcome, precursor


def _clone_response_block_attempt_precursor(
    precursor: ResponseBlockAttemptPrecursorEvidence,
) -> ResponseBlockAttemptPrecursorEvidence:
    return _clone_task12_wire(
        precursor,
        local_record_types=(
            SelectedControlEvidenceRef,
            WindowThresholdSelection,
            WindowThresholdCalibrationManifest,
            CalibrationApplicationPermit,
            V3M0ScenarioOperationEvaluation,
            ResponseBlockAttemptPrecursorEvidence,
        ),
        candidate_record_types=_candidate_record_types(
            precursor.permit.calibration_manifest
        ),
    )  # type: ignore[return-value]


def _clone_response_block_attempt_outcome(
    outcome: ResponseBlockAttemptOutcome,
) -> ResponseBlockAttemptOutcome:
    return _clone_task12_wire(
        outcome,
        local_record_types=(
            SelectedControlEvidenceRef,
            WindowThresholdSelection,
            WindowThresholdCalibrationManifest,
            CalibrationApplicationPermit,
            ResponseBlockAttemptOutcome,
        ),
        candidate_record_types=_candidate_record_types(
            outcome.permit.calibration_manifest
        ),
    )  # type: ignore[return-value]


class VerifiedResponseBlockAttemptOutcome:
    """Opaque exact-stage termination; it can never authorize downstream work."""

    __slots__ = ("__outcome", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        outcome: ResponseBlockAttemptOutcome,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("response block attempt is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedResponseBlockAttemptOutcome__outcome",
            outcome,
        )
        object.__setattr__(
            self,
            "_VerifiedResponseBlockAttemptOutcome__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedResponseBlockAttemptOutcome__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("response block attempt is immutable")

    @property
    def outcome(self) -> ResponseBlockAttemptOutcome:
        return reverify_verified_response_block_attempt_outcome(self)

    @property
    def precursor_evidence(self) -> ResponseBlockAttemptPrecursorEvidence:
        return _reverify_verified_response_block_attempt_outcome(self).precursor


@dataclass(frozen=True)
class _ResponseBlockAttemptAuthority:
    exposed: ResponseBlockAttemptOutcome
    snapshot: ResponseBlockAttemptOutcome
    precursor: ResponseBlockAttemptPrecursorEvidence
    permit: VerifiedCalibrationApplicationPermit
    scenario_id: str
    digest: str
    seal: str


@dataclass(frozen=True)
class _ResponseBlockAttemptView:
    outcome: ResponseBlockAttemptOutcome
    precursor: ResponseBlockAttemptPrecursorEvidence
    permit: VerifiedCalibrationApplicationPermit


_RESPONSE_BLOCK_ATTEMPT_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedResponseBlockAttemptOutcome],
        _ResponseBlockAttemptAuthority,
    ],
] = {}
_RESPONSE_BLOCK_ATTEMPT_LOCK = threading.RLock()


def _response_block_attempt_seal(
    outcome: ResponseBlockAttemptOutcome,
    precursor: ResponseBlockAttemptPrecursorEvidence,
) -> str:
    if (
        outcome.precursor_evidence_sha != precursor.precursor_sha
        or outcome.application_spec != precursor.application_spec
        or outcome.scenario_spec != precursor.scenario_spec
        or outcome.permit != precursor.permit
        or outcome.terminal_stage != precursor.terminal_stage
        or outcome.status != precursor.status
        or outcome.raw_singular_values != precursor.raw_singular_values
        or outcome.activation_labels != precursor.activation_labels
        or outcome.downstream_capability_issued is not False
    ):
        raise ValueError("response attempt outcome/precursor mismatch")
    return canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-response-block-attempt-outcome.v1"
            ),
            "outcome": _record_with_hash(
                outcome,
                response_block_attempt_outcome_payload,
                "outcome_sha",
            ),
            "precursor": _record_with_hash(
                precursor,
                response_block_attempt_precursor_evidence_payload,
                "precursor_sha",
            ),
            "downstream_capability_issued": False,
        }
    )


def _issue_response_block_attempt(
    outcome: ResponseBlockAttemptOutcome,
    precursor: ResponseBlockAttemptPrecursorEvidence,
    permit: VerifiedCalibrationApplicationPermit,
) -> VerifiedResponseBlockAttemptOutcome:
    outcome.__post_init__()
    precursor.__post_init__()
    digest = canonical_sha(response_block_attempt_outcome_payload(outcome))
    if digest != outcome.outcome_sha:
        raise ValueError("response block attempt outcome SHA mismatch")
    if precursor.precursor_sha != canonical_sha(
        response_block_attempt_precursor_evidence_payload(precursor)
    ):
        raise ValueError("response block attempt precursor SHA mismatch")
    exposed = _clone_response_block_attempt_outcome(outcome)
    snapshot = _clone_response_block_attempt_outcome(outcome)
    precursor_snapshot = _clone_response_block_attempt_precursor(precursor)
    seal = _response_block_attempt_seal(snapshot, precursor_snapshot)
    wrapper = VerifiedResponseBlockAttemptOutcome(
        _ISSUANCE_TOKEN,
        exposed,
        seal,
    )
    identity = id(wrapper)
    authority = _ResponseBlockAttemptAuthority(
        exposed=exposed,
        snapshot=snapshot,
        precursor=precursor_snapshot,
        permit=permit,
        scenario_id=outcome.scenario_spec.scenario_id,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[VerifiedResponseBlockAttemptOutcome],
        wrapper_id: int = identity,
    ) -> None:
        with _RESPONSE_BLOCK_ATTEMPT_LOCK:
            current = _RESPONSE_BLOCK_ATTEMPT_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _RESPONSE_BLOCK_ATTEMPT_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _RESPONSE_BLOCK_ATTEMPT_LOCK:
        _RESPONSE_BLOCK_ATTEMPT_LIVE[identity] = (reference, authority)
    return wrapper


def issue_v3m0_response_block_attempt(
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
) -> VerifiedResponseBlockAttemptOutcome:
    """Replay and issue one exact ParentFreeze typed-termination artifact."""

    outcome, precursor = _expected_response_block_attempt(permit, scenario_id)
    return _issue_response_block_attempt(outcome, precursor, permit)


def verify_response_block_attempt_outcome(
    outcome: ResponseBlockAttemptOutcome,
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
) -> VerifiedResponseBlockAttemptOutcome:
    """Hydrate only by fully replaying the permit, operation DAG and terminator."""

    _preflight_tree(outcome, "raw response block attempt outcome")
    _exact_record(
        outcome,
        ResponseBlockAttemptOutcome,
        "raw response block attempt outcome",
    )
    outcome.__post_init__()
    if outcome.outcome_sha != canonical_sha(
        response_block_attempt_outcome_payload(outcome)
    ):
        raise ValueError("response block attempt outcome self-hash mismatch")
    expected, precursor = _expected_response_block_attempt(permit, scenario_id)
    if outcome != expected:
        raise ValueError("raw response attempt differs from complete replay")
    return _issue_response_block_attempt(expected, precursor, permit)


def _reverify_verified_response_block_attempt_outcome(
    wrapper: VerifiedResponseBlockAttemptOutcome,
) -> _ResponseBlockAttemptView:
    if type(wrapper) is not VerifiedResponseBlockAttemptOutcome:
        raise TypeError("Task 12 requires a live response block attempt")
    with _RESPONSE_BLOCK_ATTEMPT_LOCK:
        current = _RESPONSE_BLOCK_ATTEMPT_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("response block attempt identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedResponseBlockAttemptOutcome__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedResponseBlockAttemptOutcome__outcome",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedResponseBlockAttemptOutcome__seal",
        )
    except AttributeError as exc:
        raise ValueError("response block attempt record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("response block attempt token mismatch")
    expected, expected_precursor = _expected_response_block_attempt(
        authority.permit,
        authority.scenario_id,
    )
    observed_digest = canonical_sha(response_block_attempt_outcome_payload(raw))
    snapshot_digest = canonical_sha(
        response_block_attempt_outcome_payload(authority.snapshot)
    )
    expected_digest = canonical_sha(response_block_attempt_outcome_payload(expected))
    expected_seal = _response_block_attempt_seal(
        authority.snapshot,
        authority.precursor,
    )
    if (
        raw is not authority.exposed
        or raw != authority.snapshot
        or expected != authority.snapshot
        or expected_precursor != authority.precursor
        or observed_digest != authority.digest
        or snapshot_digest != authority.digest
        or expected_digest != authority.digest
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("response block attempt immutable seal mismatch")
    return _ResponseBlockAttemptView(
        outcome=_clone_response_block_attempt_outcome(authority.snapshot),
        precursor=_clone_response_block_attempt_precursor(authority.precursor),
        permit=authority.permit,
    )


def reverify_verified_response_block_attempt_outcome(
    wrapper: VerifiedResponseBlockAttemptOutcome,
) -> ResponseBlockAttemptOutcome:
    """Strict public consumer boundary for downstream Task 17 aggregation."""

    return _reverify_verified_response_block_attempt_outcome(wrapper).outcome


__all__ = [
    "APPLICATION_EXPECTED_RANK_SOURCE_ID",
    "APPLICATION_READOUT_DERIVATION_ID",
    "APPLICATION_RESPONSE_RUN_SPEC_SCHEMA_VERSION",
    "CANDIDATE_ATTEMPT_AUDIT_SCHEMA_VERSION",
    "CALIBRATION_APPLICATION_PERMIT_SCHEMA_VERSION",
    "CALIBRATION_APPLICATION_SCOPE",
    "C04_CANONICAL_ANGLE_RECIPE_ID",
    "C04_CANONICAL_ANGLE_RECIPE_SCHEMA_VERSION",
    "C04_LOCAL_SHEAR_STEP_SCHEMA_VERSION",
    "C04CanonicalAngleRecipe",
    "C04LocalShearStep",
    "BranchSpectrumAudit",
    "CalibrationApplicationPermit",
    "CandidateAttemptAudit",
    "ControlCandidateAudit",
    "ControlCandidateFailure",
    "ControlCandidateOutcome",
    "EXPECTED_RANK_DECLARATION_SCHEMA_VERSION",
    "ExpectedRankDeclaration",
    "PerControlReadoutSpectrumAudit",
    "RESPONSE_BLOCK_ATTEMPT_OUTCOME_SCHEMA_VERSION",
    "RESPONSE_BLOCK_ATTEMPT_PRECURSOR_SCHEMA_VERSION",
    "ResponseBlockAttemptOutcome",
    "ResponseBlockAttemptPrecursorEvidence",
    "ReadoutAggregateCalibrationAudit",
    "SCENARIO_CONSTRUCTION_SCHEMA_VERSION",
    "SCENARIO_OPERATION_EVALUATION_SCHEMA_VERSION",
    "SELECTED_EVIDENCE_REF_SCHEMA_VERSION",
    "SelectedControlEvidenceRef",
    "V3M0ApplicationResponseRunSpec",
    "V3M0ScenarioConstruction",
    "V3M0ScenarioOperationEvaluation",
    "VerifiedCalibrationApplicationPermit",
    "VerifiedResponseBlockAttemptOutcome",
    "VerifiedV3M0ApplicationResponseRunSpec",
    "VerifiedV3M0ScenarioConstruction",
    "VerifiedWindowThresholdCalibration",
    "WindowCalibrationOutcome",
    "WindowCandidateAudit",
    "WINDOW_CALIBRATION_OUTCOME_SCHEMA_VERSION",
    "WINDOW_THRESHOLD_CALIBRATION_SCHEMA_VERSION",
    "WINDOW_THRESHOLD_SELECTION_SCHEMA_VERSION",
    "WindowThresholdCalibrationManifest",
    "WindowThresholdSelection",
    "build_v3m0_application_response_run_spec",
    "build_c04_canonical_angle_recipe",
    "c04_canonical_angle_recipe_payload",
    "c04_canonical_angle_recipe_symbol",
    "c04_local_shear_step_payload",
    "c04_reciprocal_swap_symbol",
    "calibration_application_permit_payload",
    "calibrate_window_and_thresholds",
    "candidate_attempt_audit_payload",
    "branch_spectrum_audit_payload",
    "compute_window_readout_calibration_audits",
    "control_candidate_audit_payload",
    "control_candidate_failure_reason",
    "control_candidate_outcome_payload",
    "expected_rank_declaration_payload",
    "issue_v3m0_calibration_application_permit",
    "issue_expected_rank_declaration",
    "issue_v3m0_response_block_attempt",
    "materialize_v3m0_scenario_construction",
    "response_block_attempt_outcome_payload",
    "response_block_attempt_precursor_evidence_payload",
    "reverify_verified_response_block_attempt_outcome",
    "per_control_readout_spectrum_audit_payload",
    "readout_aggregate_calibration_audit_payload",
    "v3m0_application_response_run_spec_payload",
    "v3m0_scenario_construction_payload",
    "v3m0_scenario_operation_evaluation_payload",
    "verify_calibration_application_permit",
    "verify_response_block_attempt_outcome",
    "verify_v3m0_application_response_run_spec",
    "verify_v3m0_scenario_construction",
    "verify_window_threshold_calibration",
    "window_calibration_outcome_payload",
    "window_candidate_audit_payload",
    "window_threshold_calibration_manifest_payload",
    "window_threshold_selection_payload",
]
