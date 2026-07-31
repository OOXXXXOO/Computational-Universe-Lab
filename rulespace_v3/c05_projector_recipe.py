"""Pending C05 equal-spectrum projector-orientation construction.

This module emits only a raw, self-hashed local-shear recipe and its existing
trace/factory wire representation.  It deliberately issues no permit,
evidence record, response block, or scientific status.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, fields as dataclass_fields, replace
from typing import Literal

import numpy as np
import sympy as sp

from .application_recipes import (
    APPLICATION_LOCAL_SHEAR_STEP_SCHEMA_VERSION,
    ApplicationLocalShearStep,
    _executed_effect_digest,
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
from .trace import (
    ConstructionTrace,
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
)


C05_PROJECTOR_RECIPE_SCHEMA_VERSION = "v3m0.c05-projector-orientation-recipe.v1"
C05_PROJECTOR_RECIPE_STATE = "PENDING_PARENT_REFREEZE"
C05_PROJECTOR_STATE_SCHEMA_ID = "state.v3m0.synthetic-control.v1"
C05_PROJECTOR_PUBLIC_BASIS_CONTRACT_ID = "permit-public-identity-basis-v1"
C05_PROJECTOR_SOURCE_DERIVATION_ID = "identity-column-combination-v1"
C05_PROJECTOR_READOUT_DERIVATION_ID = "identity-normalized-row-combination-v1"

_CHANNEL_ORDER = ("q0", "p0", "q1", "p1")
_CHANNEL_INDEX = {name: index for index, name in enumerate(_CHANNEL_ORDER)}
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")


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


def _require_exact_record_fields(
    value: object,
    record_type: type,
    field: str,
) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = {item.name for item in dataclass_fields(record_type)}
    observed = set(vars(value))
    unknown = observed - expected
    missing = expected - observed
    if unknown:
        raise ValueError(f"{field} has unknown fields: {sorted(unknown)!r}")
    if missing:
        raise ValueError(f"{field} is missing fields: {sorted(missing)!r}")


def _step(
    step_id: str,
    source_channel: str,
    destination_channel: str,
    coefficient: int,
    *,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> ApplicationLocalShearStep:
    if coefficient not in (-1, 1):
        raise ValueError("C05 exact shear coefficient must be +1 or -1")
    provisional = ApplicationLocalShearStep(
        step_schema_version=APPLICATION_LOCAL_SHEAR_STEP_SCHEMA_VERSION,
        step_id=step_id,
        source_channel=source_channel,
        destination_channel=destination_channel,
        offset=(0,),
        coefficient=float(coefficient),
        target_conditioned=target_conditioned,
        derivation_effect_digest=derivation_effect_digest,
        step_sha="0" * 64,
    )
    return replace(
        provisional,
        step_sha=canonical_sha(application_local_shear_step_payload(provisional)),
    )


def _exact_pair_quarter_turn(
    mode: int,
    sign: Literal[-1, 1],
    prefix: str,
    *,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    q_channel = "q0" if mode == 0 else "q1"
    p_channel = "p0" if mode == 0 else "p1"
    return (
        _step(
            f"{prefix}.lower.0",
            q_channel,
            p_channel,
            sign,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.upper",
            p_channel,
            q_channel,
            -sign,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.lower.1",
            q_channel,
            p_channel,
            sign,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
    )


def _exact_mode_quarter_turn(
    prefix: str,
    *,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    result: list[ApplicationLocalShearStep] = []
    for suffix, source_mode, destination_mode, coefficient in (
        ("lower.0", 0, 1, 1),
        ("upper", 1, 0, -1),
        ("lower.1", 0, 1, 1),
    ):
        for coordinate in ("q", "p"):
            result.append(
                _step(
                    f"{prefix}.{suffix}.{coordinate}",
                    f"{coordinate}{source_mode}",
                    f"{coordinate}{destination_mode}",
                    coefficient,
                    target_conditioned=target_conditioned,
                    derivation_effect_digest=derivation_effect_digest,
                )
            )
    return tuple(result)


@dataclass(frozen=True)
class C05ProjectorOrientationRecipe:
    recipe_schema_version: str
    construction_state: str
    scenario_kind: Literal["phase", "gain"]
    recipe_id: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_ndim: int
    public_basis_contract_id: str
    source_basis_derivation_id: str
    readout_basis_derivation_id: str
    actual_steps: tuple[ApplicationLocalShearStep, ...]
    matched_ablated_steps: tuple[ApplicationLocalShearStep, ...]
    primitive_support_radius: int
    source_injection: FrozenComplexTensor
    readout: FrozenComplexTensor
    canonical_structure: FrozenComplexTensor
    reference_phase: float
    reference_phase_band: tuple[float, float]
    expected_shell_rank: int
    response_ratio_numerator_role: Literal["matched_ablated"]
    response_ratio_denominator_role: Literal["actual"]
    expected_response_scalar_y0_over_y1: float
    candidate_derivation_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    recipe_sha: str

    def __post_init__(self) -> None:
        if self.recipe_schema_version != C05_PROJECTOR_RECIPE_SCHEMA_VERSION:
            raise ValueError("C05 projector recipe schema is not frozen")
        if self.construction_state != C05_PROJECTOR_RECIPE_STATE:
            raise ValueError("C05 projector recipe is outside the pending lane")
        if self.scenario_kind not in ("phase", "gain"):
            raise ValueError("C05 projector scenario kind is not closed")
        _text(self.recipe_id, "recipe_id")
        _text(self.state_schema_id, "state_schema_id")
        if type(self.channel_order) is not tuple:
            raise TypeError("channel_order must be an exact tuple")
        if self.channel_order != _CHANNEL_ORDER or self.spatial_ndim != 1:
            raise ValueError("C05 projector state space is not frozen")
        if self.public_basis_contract_id != C05_PROJECTOR_PUBLIC_BASIS_CONTRACT_ID:
            raise ValueError("C05 public basis contract is not frozen")
        if self.source_basis_derivation_id != C05_PROJECTOR_SOURCE_DERIVATION_ID:
            raise ValueError("C05 source derivation is not frozen")
        if self.readout_basis_derivation_id != C05_PROJECTOR_READOUT_DERIVATION_ID:
            raise ValueError("C05 readout derivation is not frozen")
        if self.primitive_support_radius != 0:
            raise ValueError("C05 primitive support radius is not frozen")
        for field in ("source_injection", "readout", "canonical_structure"):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict type")
        if type(self.reference_phase) is not float or not math.isfinite(
            self.reference_phase
        ):
            raise TypeError("reference_phase must be a finite exact float")
        if (
            type(self.reference_phase_band) is not tuple
            or len(self.reference_phase_band) != 2
            or not all(type(value) is float for value in self.reference_phase_band)
        ):
            raise TypeError("reference_phase_band has the wrong strict type")
        if self.expected_shell_rank != 2:
            raise ValueError("C05 expected shell rank is not frozen")
        if self.response_ratio_numerator_role != "matched_ablated":
            raise ValueError("C05 Y0 numerator must be matched-ablated")
        if self.response_ratio_denominator_role != "actual":
            raise ValueError("C05 Y1 denominator must be actual")
        if self.expected_response_scalar_y0_over_y1 not in (-1.0, 2.0):
            raise ValueError("C05 expected Y0/Y1 scalar is not frozen")
        for field in (
            "candidate_derivation_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "recipe_sha",
        ):
            _sha(getattr(self, field), field)


def c05_projector_orientation_recipe_payload(
    recipe: C05ProjectorOrientationRecipe,
) -> dict[str, object]:
    if type(recipe) is not C05ProjectorOrientationRecipe:
        raise TypeError("recipe must be an exact C05ProjectorOrientationRecipe")
    return {
        "recipe_schema_version": recipe.recipe_schema_version,
        "construction_state": recipe.construction_state,
        "scenario_kind": recipe.scenario_kind,
        "recipe_id": recipe.recipe_id,
        "state_schema_id": recipe.state_schema_id,
        "channel_order": list(recipe.channel_order),
        "spatial_ndim": recipe.spatial_ndim,
        "public_basis_contract_id": recipe.public_basis_contract_id,
        "source_basis_derivation_id": recipe.source_basis_derivation_id,
        "readout_basis_derivation_id": recipe.readout_basis_derivation_id,
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
        "primitive_support_radius": recipe.primitive_support_radius,
        "source_injection_sha": recipe.source_injection.tensor_sha,
        "readout_sha": recipe.readout.tensor_sha,
        "canonical_structure_sha": recipe.canonical_structure.tensor_sha,
        "reference_phase": recipe.reference_phase,
        "reference_phase_band": list(recipe.reference_phase_band),
        "expected_shell_rank": recipe.expected_shell_rank,
        "response_ratio_numerator_role": recipe.response_ratio_numerator_role,
        "response_ratio_denominator_role": recipe.response_ratio_denominator_role,
        "expected_response_scalar_y0_over_y1": (
            recipe.expected_response_scalar_y0_over_y1
        ),
        "candidate_derivation_sha": recipe.candidate_derivation_sha,
        "actual_effect_digest": recipe.actual_effect_digest,
        "matched_ablated_effect_digest": recipe.matched_ablated_effect_digest,
    }


def _compile_recipe(
    scenario_kind: Literal["phase", "gain"],
) -> C05ProjectorOrientationRecipe:
    if scenario_kind not in ("phase", "gain"):
        raise ValueError("scenario_kind must be phase or gain")
    derivation_sha = canonical_sha(
        {
            "construction_schema": "v3m0.c05-exact-projector-orientation.v1",
            "construction_state": C05_PROJECTOR_RECIPE_STATE,
            "scenario_kind": scenario_kind,
            "matched_transition": "exact-signed-permutation-diag-minusJ-plusJ",
            "actual_transition": "exact-signed-permutation-cross-pair",
            "conditioned_operation": "exact-plus-one-mode-quarter-turn",
        }
    )
    carrier = (
        *_exact_pair_quarter_turn(
            0,
            1,
            "blind.carrier.mode0",
            target_conditioned=False,
            derivation_effect_digest=derivation_sha,
        ),
        *_exact_pair_quarter_turn(
            1,
            -1,
            "blind.carrier.mode1",
            target_conditioned=False,
            derivation_effect_digest=derivation_sha,
        ),
    )
    conditioned = _exact_mode_quarter_turn(
        "conditioned.projector-orientation",
        target_conditioned=True,
        derivation_effect_digest=derivation_sha,
    )
    actual_steps = (*carrier, *conditioned)
    if scenario_kind == "phase":
        source_values = np.asarray(
            ((0.0,), (1.0 + 1.0j,), (1.0j,), (0.0,)),
            dtype=np.complex128,
        ) / math.sqrt(3.0)
        readout_values = np.asarray(
            ((3.0, 1.0 + 1.0j, -2.0, 2.0j),),
            dtype=np.complex128,
        ) / math.sqrt(19.0)
        expected = -1.0
    else:
        source_values = np.asarray(
            ((0.0,), (1.0,), (-1.0 + 1.0j,), (0.0,)),
            dtype=np.complex128,
        ) / math.sqrt(3.0)
        readout_values = np.asarray(
            ((-3.0 + 5.0j, -1.0 + 1.0j, -1.0, -1.0),),
            dtype=np.complex128,
        ) / math.sqrt(38.0)
        expected = 2.0
    canonical = np.asarray(
        (
            (0.0, 1.0, 0.0, 0.0),
            (-1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
            (0.0, 0.0, -1.0, 0.0),
        ),
        dtype=np.complex128,
    )
    provisional = C05ProjectorOrientationRecipe(
        recipe_schema_version=C05_PROJECTOR_RECIPE_SCHEMA_VERSION,
        construction_state=C05_PROJECTOR_RECIPE_STATE,
        scenario_kind=scenario_kind,
        recipe_id=f"c05-exact-projector-orientation-{scenario_kind}-v1",
        state_schema_id=C05_PROJECTOR_STATE_SCHEMA_ID,
        channel_order=_CHANNEL_ORDER,
        spatial_ndim=1,
        public_basis_contract_id=C05_PROJECTOR_PUBLIC_BASIS_CONTRACT_ID,
        source_basis_derivation_id=C05_PROJECTOR_SOURCE_DERIVATION_ID,
        readout_basis_derivation_id=C05_PROJECTOR_READOUT_DERIVATION_ID,
        actual_steps=actual_steps,
        matched_ablated_steps=carrier,
        primitive_support_radius=0,
        source_injection=freeze_complex_tensor(source_values),
        readout=freeze_complex_tensor(readout_values),
        canonical_structure=freeze_complex_tensor(canonical),
        reference_phase=float(math.pi / 2.0),
        reference_phase_band=(
            float(math.pi / 2.0 - 1.0 / 8.0),
            float(math.pi / 2.0 + 1.0 / 8.0),
        ),
        expected_shell_rank=2,
        response_ratio_numerator_role="matched_ablated",
        response_ratio_denominator_role="actual",
        expected_response_scalar_y0_over_y1=expected,
        candidate_derivation_sha=derivation_sha,
        actual_effect_digest=_executed_effect_digest(actual_steps, "actual"),
        matched_ablated_effect_digest=_executed_effect_digest(
            actual_steps,
            "matched_ablated",
        ),
        recipe_sha="0" * 64,
    )
    return replace(
        provisional,
        recipe_sha=canonical_sha(
            c05_projector_orientation_recipe_payload(provisional)
        ),
    )


def _validate_recipe(recipe: C05ProjectorOrientationRecipe) -> None:
    _require_exact_record_fields(
        recipe,
        C05ProjectorOrientationRecipe,
        "recipe",
    )
    if type(recipe.channel_order) is not tuple:
        raise TypeError("channel_order must be an exact tuple")
    for field in ("actual_steps", "matched_ablated_steps"):
        steps = getattr(recipe, field)
        if type(steps) is not tuple:
            raise TypeError(f"{field} must be an exact tuple")
        for index, step in enumerate(steps):
            _require_exact_record_fields(
                step,
                ApplicationLocalShearStep,
                f"{field}[{index}]",
            )
    for field in ("source_injection", "readout", "canonical_structure"):
        tensor = getattr(recipe, field)
        _require_exact_record_fields(
            tensor,
            FrozenComplexTensor,
            field,
        )
        verify_frozen_tensor(tensor)
    if recipe.recipe_sha != canonical_sha(
        c05_projector_orientation_recipe_payload(recipe)
    ):
        raise ValueError("C05 projector recipe SHA does not match its body")
    if recipe.matched_ablated_steps != tuple(
        step for step in recipe.actual_steps if not step.target_conditioned
    ):
        raise ValueError("C05 matched ablation is not mechanical")
    if len(recipe.actual_steps) != 12 or len(recipe.matched_ablated_steps) != 6:
        raise ValueError("C05 exact shear program length is not frozen")
    if any(step.offset != (0,) for step in recipe.actual_steps):
        raise ValueError("C05 shear support is not on-site")
    for step in recipe.actual_steps:
        if step.coefficient not in (-1.0, 1.0):
            raise ValueError("C05 shear coefficient lost exact sign form")
        if step.step_sha != canonical_sha(
            application_local_shear_step_payload(step)
        ):
            raise ValueError("C05 shear step SHA does not match its body")
    source = frozen_tensor_array(recipe.source_injection)
    readout = frozen_tensor_array(recipe.readout)
    canonical = frozen_tensor_array(recipe.canonical_structure)
    if source.shape != (4, 1) or readout.shape != (1, 4):
        raise ValueError("C05 source/readout shape is not frozen")
    if not np.array_equal(canonical, np.asarray(
        (
            (0.0, 1.0, 0.0, 0.0),
            (-1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
            (0.0, 0.0, -1.0, 0.0),
        ),
        dtype=np.complex128,
    )):
        raise ValueError("C05 canonical structure is not frozen")
    if float(np.linalg.norm(source.conj().T @ source - np.eye(1), 2)) > 1.0e-12:
        raise ValueError("C05 source injection is not an isometry")
    if float(np.linalg.norm(readout @ readout.conj().T - np.eye(1), 2)) > 1.0e-12:
        raise ValueError("C05 readout is not a coisometry")
    if recipe.actual_effect_digest != _executed_effect_digest(
        recipe.actual_steps,
        "actual",
    ):
        raise ValueError("C05 actual effect digest does not replay")
    if recipe.matched_ablated_effect_digest != _executed_effect_digest(
        recipe.actual_steps,
        "matched_ablated",
    ):
        raise ValueError("C05 ablated effect digest does not replay")


def build_c05_projector_orientation_recipe(
    scenario_kind: Literal["phase", "gain"],
) -> C05ProjectorOrientationRecipe:
    recipe = _compile_recipe(scenario_kind)
    _validate_recipe(recipe)
    return recipe


def verify_c05_projector_orientation_recipe(
    recipe: C05ProjectorOrientationRecipe,
) -> C05ProjectorOrientationRecipe:
    _validate_recipe(recipe)
    if recipe != _compile_recipe(recipe.scenario_kind):
        raise ValueError("C05 projector recipe differs from canonical compilation")
    return recipe


def derive_c05_projector_source_readout_from_public_identity(
    recipe: C05ProjectorOrientationRecipe,
    public_identity_basis: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Mechanically derive scenario-bound maps from the permit identity basis."""

    verified = verify_c05_projector_orientation_recipe(recipe)
    if type(public_identity_basis) is not np.ndarray:
        raise TypeError("public_identity_basis must be a NumPy ndarray")
    if public_identity_basis.dtype != np.dtype(np.complex128):
        raise TypeError("public_identity_basis dtype must be complex128")
    identity = np.eye(4, dtype=np.complex128)
    if not np.array_equal(public_identity_basis, identity):
        raise ValueError("public_identity_basis must be the exact public identity")
    return (
        public_identity_basis @ frozen_tensor_array(verified.source_injection),
        frozen_tensor_array(verified.readout) @ public_identity_basis,
    )


def c05_projector_orientation_recipe_symbol(
    recipe: C05ProjectorOrientationRecipe,
    momentum: float,
    branch: Literal["actual", "matched_ablated"],
) -> np.ndarray:
    verified = verify_c05_projector_orientation_recipe(recipe)
    if type(momentum) is not float or not math.isfinite(momentum):
        raise TypeError("momentum must be a finite exact float")
    if branch == "actual":
        steps = verified.actual_steps
    elif branch == "matched_ablated":
        steps = verified.matched_ablated_steps
    else:
        raise ValueError("branch is outside the C05 projector recipe")
    matrix = np.eye(4, dtype=np.complex128)
    for step in steps:
        shear = np.eye(4, dtype=np.complex128)
        phase = complex(
            math.cos(momentum * step.offset[0]),
            math.sin(momentum * step.offset[0]),
        )
        shear[
            _CHANNEL_INDEX[step.destination_channel],
            _CHANNEL_INDEX[step.source_channel],
        ] += step.coefficient * phase
        matrix = shear @ matrix
    return matrix


def build_c05_projector_recipe_trace_and_operators(
    recipe: C05ProjectorOrientationRecipe,
    *,
    target_spec_id: str,
    interface: PrimitiveInterface,
) -> tuple[ConstructionTrace, tuple[PrimitiveOperatorWire, ...]]:
    verified = verify_c05_projector_orientation_recipe(recipe)
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
        raise ValueError("factory interface differs from the C05 recipe")
    prefix = f"v3m0.c05-projector.{verified.scenario_kind}.v1"
    blind_provenance_id = f"{prefix}.pending-local-recipe"
    conditioned_provenance_id = f"{prefix}.target-conditioned"
    provenance = (
        ProvenanceNode(
            provenance_id=blind_provenance_id,
            operation=ProvenanceOperation.GRAMMAR_CONSTANT,
            depends_on=(),
            target_refs=(),
            objective_tags=(),
            search_run_id=None,
            source_sha=verified.candidate_derivation_sha,
        ),
        ProvenanceNode(
            provenance_id=conditioned_provenance_id,
            operation=ProvenanceOperation.TARGET_SPEC_READ,
            depends_on=(blind_provenance_id,),
            target_refs=(f"target:{target_id}",),
            objective_tags=(),
            search_run_id=None,
            source_sha=verified.recipe_sha,
        ),
    )
    specs: list[PrimitiveSpec] = []
    operators: list[PrimitiveOperatorWire] = []
    for index, step in enumerate(verified.actual_steps):
        mechanism_id = f"{prefix}.shear.{index:03d}"
        production_id = (
            "target_operator" if step.target_conditioned else "local_canonical_shear"
        )
        layer_slot_id = f"{prefix}.layer.{index:03d}"
        specs.append(
            PrimitiveSpec(
                mechanism_id=mechanism_id,
                production_id=production_id,
                depends_on=(),
                support_offsets=((0,),),
                state_channels=tuple(
                    sorted((step.source_channel, step.destination_channel))
                ),
                coefficient_expression=sp.Integer(int(step.coefficient)),
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
                offset=(0,),
                coefficient_wire=(step.coefficient, 0.0),
            )
        )
    return (
        build_construction_trace(
            target_spec_id=target_id,
            provenance_nodes=provenance,
            primitive_specs=tuple(specs),
        ),
        tuple(operators),
    )


__all__ = [
    "C05_PROJECTOR_PUBLIC_BASIS_CONTRACT_ID",
    "C05_PROJECTOR_READOUT_DERIVATION_ID",
    "C05_PROJECTOR_RECIPE_SCHEMA_VERSION",
    "C05_PROJECTOR_RECIPE_STATE",
    "C05_PROJECTOR_SOURCE_DERIVATION_ID",
    "C05_PROJECTOR_STATE_SCHEMA_ID",
    "C05ProjectorOrientationRecipe",
    "build_c05_projector_orientation_recipe",
    "build_c05_projector_recipe_trace_and_operators",
    "c05_projector_orientation_recipe_payload",
    "c05_projector_orientation_recipe_symbol",
    "derive_c05_projector_source_readout_from_public_identity",
    "verify_c05_projector_orientation_recipe",
]
