"""Inert local-shear construction preflights for C07, C08, and C10.

The records in this module consume the unique provisional Parent candidate and
bind its scenario/selector wires to explicit rectangular source and readout
maps.  They remain construction inputs only: no Parent, permit, response
block, evidence record, or scientific status is issued here.

All four constructions use the common on-site real canonical state
``(q0, p0, q1, p1)``.  Matched ablation is mechanical deletion of the
target-conditioned scalar shear slots.  Exact quarter turns use the signed
three-shear decomposition, avoiding finite-window leakage through a nominally
inactive quadrature.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, fields as dataclass_fields, replace
from typing import Literal, Optional

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
from .parent_freeze import (
    ParentFreezeCandidateManifest,
    ParentFreezeCandidateScenario,
    build_v3m0_parent_freeze_candidate,
    verify_parent_freeze_candidate,
)
from .trace import (
    ConstructionTrace,
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
)


INTERFERENCE_MODE_PREFLIGHT_SCHEMA_VERSION = (
    "v3m0.interference-mode-construction-preflight.v2"
)
INTERFERENCE_MODE_PREFLIGHT_STATE = "CONSTRUCTION_PREFLIGHT_ONLY_NO_AUTHORITY"
INTERFERENCE_MODE_STATE_SCHEMA_ID = "state.v3m0.synthetic-control.v1"
CANDIDATE_FEJER_ORDERS = (256, 512, 1024, 2048, 4096, 8192)
PREFLIGHT_MOMENTA = (math.pi / 4.0, math.pi / 2.0)
CONSTRUCTIVE_DELTA = math.pi / 8192.0

INTERFERENCE_MODE_SCENARIO_IDS = (
    "v3m0.synthetic-control.c07.v1.scenario.constructive.v1",
    "v3m0.synthetic-control.c07.v1.scenario.destructive.v1",
    "v3m0.synthetic-control.c08.v1.scenario.rank-missing.v1",
    "v3m0.synthetic-control.c10.v1.scenario.extra-mode.v1",
)

_CHANNEL_ORDER = ("q0", "p0", "q1", "p1")
_CHANNEL_INDEX = {name: index for index, name in enumerate(_CHANNEL_ORDER)}
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")

ScenarioKind = Literal[
    "constructive",
    "destructive",
    "rank_missing",
    "extra_mode",
]
CandidateRankDisposition = Literal[
    "CANDIDATE_RANK_UNCHANGED",
    "REQUIRES_PARENT_RANK_REFREEZE_1_TO_2",
]
CandidateSelectorDisposition = Literal["REQUIRES_PARENT_SELECTOR_REFREEZE"]
SourceReadoutRole = Literal["PROPOSED_PARENT_SELECTOR"]


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
    expected = {item.name for item in dataclass_fields(record_type)}
    observed = set(vars(value))
    unknown = observed - expected
    missing = expected - observed
    if unknown or missing:
        raise ValueError(
            f"{field} contains unknown or missing fields: "
            f"unknown={sorted(unknown)!r}, missing={sorted(missing)!r}"
        )


@dataclass(frozen=True)
class InterferenceModePreflightArtifact:
    preflight_schema_version: str
    construction_state: str
    scenario_kind: ScenarioKind
    control_case_id: str
    scenario_id: str
    parent_candidate_sha: str
    candidate_application_sha: str
    based_on_application_spec_sha: str
    scenario_sha: str
    based_on_candidate_selector_sha: str
    response_template_sha: str
    prediction_profile_sha: str
    execution_recipe_id: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_ndim: int
    actual_steps: tuple[ApplicationLocalShearStep, ...]
    matched_ablated_steps: tuple[ApplicationLocalShearStep, ...]
    primitive_support_radius: int
    candidate_selector_disposition: CandidateSelectorDisposition
    source_readout_role: SourceReadoutRole
    candidate_source_injection: FrozenComplexTensor
    candidate_readout_coisometry: FrozenComplexTensor
    proposed_source_selection: FrozenComplexTensor
    proposed_readout_selection: FrozenComplexTensor
    source_injection: FrozenComplexTensor
    readout: FrozenComplexTensor
    canonical_structure: FrozenComplexTensor
    actual_sector_source_columns: tuple[int, ...]
    reference_phase: float
    reference_phase_band: tuple[float, float]
    constructive_delta: Optional[float]
    candidate_expected_actual_shell_rank: int
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    candidate_rank_disposition: CandidateRankDisposition
    expected_survival_spectrum: tuple[float, ...]
    expected_chi_extra: float
    expected_d_proc_sq: Optional[float]
    candidate_fejer_orders: tuple[int, ...]
    response_momenta: tuple[float, ...]
    candidate_derivation_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    preflight_sha: str

    def __post_init__(self) -> None:
        if self.preflight_schema_version != (
            INTERFERENCE_MODE_PREFLIGHT_SCHEMA_VERSION
        ):
            raise ValueError("interference/mode preflight schema is not frozen")
        if self.construction_state != INTERFERENCE_MODE_PREFLIGHT_STATE:
            raise ValueError("interference/mode artifact claimed authority")
        if self.scenario_kind not in (
            "constructive",
            "destructive",
            "rank_missing",
            "extra_mode",
        ):
            raise ValueError("interference/mode scenario kind is not frozen")
        for field in (
            "control_case_id",
            "scenario_id",
            "execution_recipe_id",
            "state_schema_id",
        ):
            _text(getattr(self, field), field)
        for field in (
            "parent_candidate_sha",
            "candidate_application_sha",
            "based_on_application_spec_sha",
            "scenario_sha",
            "based_on_candidate_selector_sha",
            "response_template_sha",
            "prediction_profile_sha",
            "candidate_derivation_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "preflight_sha",
        ):
            _sha(getattr(self, field), field)
        if (
            type(self.channel_order) is not tuple
            or self.channel_order != _CHANNEL_ORDER
        ):
            raise ValueError("interference/mode channel order is not frozen")
        if self.spatial_ndim != 1 or self.primitive_support_radius != 0:
            raise ValueError("interference/mode locality contract is not on-site")
        for field in ("actual_steps", "matched_ablated_steps"):
            if type(getattr(self, field)) is not tuple:
                raise TypeError(f"{field} must be an exact tuple")
        if self.candidate_selector_disposition != "REQUIRES_PARENT_SELECTOR_REFREEZE":
            raise ValueError("candidate selector disposition claimed authority")
        if self.source_readout_role != "PROPOSED_PARENT_SELECTOR":
            raise ValueError("source/readout role claimed current Parent authority")
        for field in (
            "candidate_source_injection",
            "candidate_readout_coisometry",
            "proposed_source_selection",
            "proposed_readout_selection",
            "source_injection",
            "readout",
            "canonical_structure",
        ):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} must be an exact FrozenComplexTensor")
        if type(self.actual_sector_source_columns) is not tuple or not all(
            type(value) is int for value in self.actual_sector_source_columns
        ):
            raise TypeError("actual sector source columns have the wrong strict type")
        if not self.actual_sector_source_columns:
            raise ValueError("actual sector source columns must not be empty")
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
        if self.constructive_delta is not None and (
            type(self.constructive_delta) is not float
            or not math.isfinite(self.constructive_delta)
        ):
            raise TypeError("constructive_delta must be None or a finite exact float")
        for field in (
            "candidate_expected_actual_shell_rank",
            "expected_actual_shell_rank",
            "expected_matched_shell_rank",
        ):
            if type(getattr(self, field)) is not int or getattr(self, field) <= 0:
                raise TypeError(f"{field} must be a positive exact int")
        if self.candidate_rank_disposition not in (
            "CANDIDATE_RANK_UNCHANGED",
            "REQUIRES_PARENT_RANK_REFREEZE_1_TO_2",
        ):
            raise ValueError("candidate rank disposition is not frozen")
        if type(self.expected_survival_spectrum) is not tuple or not all(
            type(value) is float for value in self.expected_survival_spectrum
        ):
            raise TypeError("expected survival spectrum has the wrong strict type")
        if type(self.expected_chi_extra) is not float:
            raise TypeError("expected_chi_extra must be an exact float")
        if (
            self.expected_d_proc_sq is not None
            and type(self.expected_d_proc_sq) is not float
        ):
            raise TypeError("expected_d_proc_sq must be None or an exact float")
        if type(self.candidate_fejer_orders) is not tuple or not all(
            type(value) is int for value in self.candidate_fejer_orders
        ):
            raise TypeError("candidate_fejer_orders has the wrong strict type")
        if type(self.response_momenta) is not tuple or not all(
            type(value) is float for value in self.response_momenta
        ):
            raise TypeError("response_momenta has the wrong strict type")


def interference_mode_preflight_artifact_payload(
    artifact: InterferenceModePreflightArtifact,
) -> dict[str, object]:
    if type(artifact) is not InterferenceModePreflightArtifact:
        raise TypeError("artifact must be an exact InterferenceModePreflightArtifact")
    return {
        "preflight_schema_version": artifact.preflight_schema_version,
        "construction_state": artifact.construction_state,
        "scenario_kind": artifact.scenario_kind,
        "control_case_id": artifact.control_case_id,
        "scenario_id": artifact.scenario_id,
        "parent_candidate_sha": artifact.parent_candidate_sha,
        "candidate_application_sha": artifact.candidate_application_sha,
        "based_on_application_spec_sha": artifact.based_on_application_spec_sha,
        "scenario_sha": artifact.scenario_sha,
        "based_on_candidate_selector_sha": (artifact.based_on_candidate_selector_sha),
        "response_template_sha": artifact.response_template_sha,
        "prediction_profile_sha": artifact.prediction_profile_sha,
        "execution_recipe_id": artifact.execution_recipe_id,
        "state_schema_id": artifact.state_schema_id,
        "channel_order": list(artifact.channel_order),
        "spatial_ndim": artifact.spatial_ndim,
        "actual_steps": [
            {
                **application_local_shear_step_payload(step),
                "step_sha": step.step_sha,
            }
            for step in artifact.actual_steps
        ],
        "matched_ablated_steps": [
            {
                **application_local_shear_step_payload(step),
                "step_sha": step.step_sha,
            }
            for step in artifact.matched_ablated_steps
        ],
        "primitive_support_radius": artifact.primitive_support_radius,
        "candidate_selector_disposition": (artifact.candidate_selector_disposition),
        "source_readout_role": artifact.source_readout_role,
        "candidate_source_injection_sha": (
            artifact.candidate_source_injection.tensor_sha
        ),
        "candidate_readout_coisometry_sha": (
            artifact.candidate_readout_coisometry.tensor_sha
        ),
        "proposed_source_selection_sha": (
            artifact.proposed_source_selection.tensor_sha
        ),
        "proposed_readout_selection_sha": (
            artifact.proposed_readout_selection.tensor_sha
        ),
        "source_injection_sha": artifact.source_injection.tensor_sha,
        "readout_sha": artifact.readout.tensor_sha,
        "canonical_structure_sha": artifact.canonical_structure.tensor_sha,
        "actual_sector_source_columns": list(artifact.actual_sector_source_columns),
        "reference_phase": artifact.reference_phase,
        "reference_phase_band": list(artifact.reference_phase_band),
        "constructive_delta": artifact.constructive_delta,
        "candidate_expected_actual_shell_rank": (
            artifact.candidate_expected_actual_shell_rank
        ),
        "expected_actual_shell_rank": artifact.expected_actual_shell_rank,
        "expected_matched_shell_rank": artifact.expected_matched_shell_rank,
        "candidate_rank_disposition": artifact.candidate_rank_disposition,
        "expected_survival_spectrum": list(artifact.expected_survival_spectrum),
        "expected_chi_extra": artifact.expected_chi_extra,
        "expected_d_proc_sq": artifact.expected_d_proc_sq,
        "candidate_fejer_orders": list(artifact.candidate_fejer_orders),
        "response_momenta": list(artifact.response_momenta),
        "candidate_derivation_sha": artifact.candidate_derivation_sha,
        "actual_effect_digest": artifact.actual_effect_digest,
        "matched_ablated_effect_digest": (artifact.matched_ablated_effect_digest),
    }


def _step(
    step_id: str,
    source_channel: str,
    destination_channel: str,
    coefficient: float,
    *,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> ApplicationLocalShearStep:
    value = float(coefficient)
    if not math.isfinite(value) or value == 0.0:
        raise ValueError("scalar shear coefficient must be finite and non-zero")
    provisional = ApplicationLocalShearStep(
        step_schema_version=APPLICATION_LOCAL_SHEAR_STEP_SCHEMA_VERSION,
        step_id=step_id,
        source_channel=source_channel,
        destination_channel=destination_channel,
        offset=(0,),
        coefficient=value,
        target_conditioned=target_conditioned,
        derivation_effect_digest=derivation_effect_digest,
        step_sha="0" * 64,
    )
    return replace(
        provisional,
        step_sha=canonical_sha(application_local_shear_step_payload(provisional)),
    )


def _quarter_turn_steps(
    mode: int,
    sign: Literal[-1, 1],
    prefix: str,
    *,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    if mode not in (0, 1) or sign not in (-1, 1):
        raise ValueError("quarter turn mode/sign is outside the frozen grammar")
    q_channel = f"q{mode}"
    p_channel = f"p{mode}"
    return (
        _step(
            f"{prefix}.lower.0",
            q_channel,
            p_channel,
            float(sign),
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.upper",
            p_channel,
            q_channel,
            float(-sign),
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.lower.1",
            q_channel,
            p_channel,
            float(sign),
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
    )


def _rotation_steps(
    mode: int,
    angle: float,
    prefix: str,
    *,
    target_conditioned: bool,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    if mode not in (0, 1) or type(angle) is not float or not math.isfinite(angle):
        raise ValueError("canonical rotation input is outside the frozen grammar")
    q_channel = f"q{mode}"
    p_channel = f"p{mode}"
    tangent = math.tan(angle / 2.0)
    sine = math.sin(angle)
    return (
        _step(
            f"{prefix}.lower.0",
            q_channel,
            p_channel,
            tangent,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.upper",
            p_channel,
            q_channel,
            -sine,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
        _step(
            f"{prefix}.lower.1",
            q_channel,
            p_channel,
            tangent,
            target_conditioned=target_conditioned,
            derivation_effect_digest=derivation_effect_digest,
        ),
    )


def _mode_swap_steps(
    prefix: str,
    *,
    inverse: bool,
    derivation_effect_digest: str,
) -> tuple[ApplicationLocalShearStep, ...]:
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
        _step(
            f"{prefix}.{index:02d}",
            source,
            destination,
            coefficient,
            target_conditioned=True,
            derivation_effect_digest=derivation_effect_digest,
        )
        for index, (source, destination, coefficient) in enumerate(operations)
    )


def _find_candidate_scenario(
    candidate: ParentFreezeCandidateManifest,
    scenario_id: str,
) -> tuple[object, ParentFreezeCandidateScenario]:
    if type(candidate) is not ParentFreezeCandidateManifest:
        raise TypeError("candidate must be an exact ParentFreezeCandidateManifest")
    matches = tuple(
        (application, scenario)
        for application in candidate.application_candidates
        for scenario in application.scenario_candidates
        if scenario.scenario_execution_spec.scenario_id == scenario_id
    )
    if len(matches) != 1:
        raise ValueError("scenario is not unique in the Parent candidate")
    return matches[0]


def _scenario_contract(
    scenario_id: str,
) -> tuple[
    ScenarioKind,
    str,
    str,
    np.ndarray,
    np.ndarray,
    tuple[int, ...],
    int,
    tuple[float, ...],
    float,
    Optional[float],
    Optional[float],
    CandidateRankDisposition,
]:
    if scenario_id == INTERFERENCE_MODE_SCENARIO_IDS[0]:
        return (
            "constructive",
            "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
            "two-mode-constructive-interference-v2",
            np.asarray(((1.0,), (0.0,), (0.0,), (0.0,)), dtype=np.complex128),
            np.asarray(((0.0, 1.0, 0.0, 0.0),), dtype=np.complex128),
            (0,),
            1,
            (1.0,),
            0.0,
            0.0,
            CONSTRUCTIVE_DELTA,
            "CANDIDATE_RANK_UNCHANGED",
        )
    if scenario_id == INTERFERENCE_MODE_SCENARIO_IDS[1]:
        return (
            "destructive",
            "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
            "two-mode-destructive-interference-v2",
            np.asarray(
                ((0.5,), (0.0,), (math.sqrt(3.0) / 2.0,), (0.0,)),
                dtype=np.complex128,
            ),
            np.asarray(
                ((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
                dtype=np.complex128,
            ),
            (0,),
            1,
            (0.0,),
            1.0,
            1.0,
            None,
            "CANDIDATE_RANK_UNCHANGED",
        )
    if scenario_id == INTERFERENCE_MODE_SCENARIO_IDS[2]:
        return (
            "rank_missing",
            "C08_RANK_R_MISSING_MODES",
            "two-mode-rank-deletion-v1",
            np.asarray(
                ((1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (0.0, 0.0)),
                dtype=np.complex128,
            ),
            np.asarray(
                ((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
                dtype=np.complex128,
            ),
            (0, 1),
            2,
            (0.0, 1.0),
            0.0,
            0.5,
            None,
            "REQUIRES_PARENT_RANK_REFREEZE_1_TO_2",
        )
    if scenario_id == INTERFERENCE_MODE_SCENARIO_IDS[3]:
        return (
            "extra_mode",
            "C10_FULL_SOURCE_EXTRA_MODE",
            "two-mode-full-source-extra-mode-v1",
            np.asarray(
                ((0.0, 1.0), (0.0, 0.0), (1.0, 0.0), (0.0, 0.0)),
                dtype=np.complex128,
            ),
            np.asarray(
                ((0.0, 0.0, 0.0, 1.0), (0.0, 1.0, 0.0, 0.0)),
                dtype=np.complex128,
            ),
            (0,),
            1,
            (0.0,),
            1.0,
            None,
            None,
            "CANDIDATE_RANK_UNCHANGED",
        )
    raise ValueError("scenario_id is outside the C07/C08/C10 preflight set")


def _program(
    scenario_kind: ScenarioKind,
    derivation_sha: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    if scenario_kind == "constructive":
        blind = (
            *_rotation_steps(
                0,
                float(math.pi / 2.0 - CONSTRUCTIVE_DELTA),
                "constructive.rotation.blind.mode0",
                target_conditioned=False,
                derivation_effect_digest=derivation_sha,
            ),
            *_quarter_turn_steps(
                1,
                1,
                "blind.mode1.quarter.0",
                target_conditioned=False,
                derivation_effect_digest=derivation_sha,
            ),
            *_quarter_turn_steps(
                1,
                1,
                "blind.mode1.quarter.1",
                target_conditioned=False,
                derivation_effect_digest=derivation_sha,
            ),
        )
        conditioned = _rotation_steps(
            0,
            CONSTRUCTIVE_DELTA,
            "constructive.rotation.conditioned.mode0",
            target_conditioned=True,
            derivation_effect_digest=derivation_sha,
        )
        return (*blind, *conditioned)
    blind = (
        *_quarter_turn_steps(
            0,
            1,
            "blind.mode0.quarter",
            target_conditioned=False,
            derivation_effect_digest=derivation_sha,
        ),
        *_quarter_turn_steps(
            1,
            1,
            "blind.mode1.quarter.0",
            target_conditioned=False,
            derivation_effect_digest=derivation_sha,
        ),
        *_quarter_turn_steps(
            1,
            1,
            "blind.mode1.quarter.1",
            target_conditioned=False,
            derivation_effect_digest=derivation_sha,
        ),
    )
    if scenario_kind == "rank_missing":
        conditioned = _quarter_turn_steps(
            1,
            -1,
            "conditioned.mode1.inverse-quarter",
            target_conditioned=True,
            derivation_effect_digest=derivation_sha,
        )
        return (*blind, *conditioned)
    if scenario_kind in ("destructive", "extra_mode"):
        inverse = _mode_swap_steps(
            "conditioned.mode-swap.inverse",
            inverse=True,
            derivation_effect_digest=derivation_sha,
        )
        forward = _mode_swap_steps(
            "conditioned.mode-swap.forward",
            inverse=False,
            derivation_effect_digest=derivation_sha,
        )
        return (*inverse, *blind, *forward)
    raise ValueError("scenario kind has no frozen shear program")


def _compile_artifact(
    candidate: ParentFreezeCandidateManifest,
    scenario_id: str,
) -> InterferenceModePreflightArtifact:
    verified_candidate = verify_parent_freeze_candidate(candidate)
    application, scenario = _find_candidate_scenario(
        verified_candidate,
        scenario_id,
    )
    (
        kind,
        control_case_id,
        recipe_id,
        source_selection,
        readout_selection,
        sector_columns,
        expected_actual_rank,
        expected_survival,
        expected_chi_extra,
        expected_d_proc,
        constructive_delta,
        rank_disposition,
    ) = _scenario_contract(scenario_id)
    if application.control_case_id != control_case_id:
        raise ValueError("candidate scenario was spliced across control cases")
    execution = scenario.scenario_execution_spec
    selector = scenario.selector_spec
    template = scenario.response_template
    profile = scenario.prediction_profile
    if (
        execution.execution_lane != "BLOCK_SUCCESS"
        or execution.execution_recipe_id != recipe_id
        or execution.expected_terminal_stage != "success"
        or template.construction_preflight_state != "PENDING_CONSTRUCTION_PREFLIGHT"
        or profile.prediction_state != "PENDING_CONSTRUCTION_PREFLIGHT"
        or profile.quantities != ()
    ):
        raise ValueError("candidate scenario is not the exact pending success contract")
    candidate_source = frozen_tensor_array(selector.source_injection)
    candidate_readout = frozen_tensor_array(selector.readout_coisometry)
    identity = np.eye(4, dtype=np.complex128)
    if not np.array_equal(candidate_source, identity) or not np.array_equal(
        candidate_readout,
        identity,
    ):
        raise ValueError(
            "candidate scenario selector is not the frozen public identity"
        )
    source = candidate_source @ source_selection
    readout = readout_selection @ candidate_readout
    derivation_sha = canonical_sha(
        {
            "construction_schema": "v3m0.c07-c08-c10-local-shear-math.v1",
            "parent_candidate_sha": verified_candidate.candidate_sha,
            "candidate_application_sha": application.candidate_application_sha,
            "scenario_sha": execution.scenario_sha,
            "based_on_candidate_selector_sha": selector.selector_sha,
            "scenario_kind": kind,
            "recipe_id": recipe_id,
            "source_selection_sha": freeze_complex_tensor(source_selection).tensor_sha,
            "readout_selection_sha": freeze_complex_tensor(
                readout_selection
            ).tensor_sha,
            "constructive_delta": constructive_delta,
            "actual_transition": {
                "constructive": "diag(J,-I)",
                "destructive": "C-diag(J,-I)-C^-1=diag(-I,J)",
                "rank_missing": "diag(J,J)",
                "extra_mode": "C-diag(J,-I)-C^-1=diag(-I,J)",
            }[kind],
            "matched_transition": {
                "constructive": "diag(R(pi/2-delta),-I)",
                "destructive": "diag(J,-I)",
                "rank_missing": "diag(J,-I)",
                "extra_mode": "diag(J,-I)",
            }[kind],
        }
    )
    actual_steps = _program(kind, derivation_sha)
    matched_steps = tuple(step for step in actual_steps if not step.target_conditioned)
    canonical = np.asarray(
        (
            (0.0, 1.0, 0.0, 0.0),
            (-1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
            (0.0, 0.0, -1.0, 0.0),
        ),
        dtype=np.complex128,
    )
    phase_band = template.preregistered_phase_bands
    if len(phase_band) != 1:
        raise ValueError("candidate scenario must freeze exactly one phase band")
    candidate_rank = template.expected_actual_shell_rank
    if kind == "rank_missing":
        if candidate_rank != 1 or expected_actual_rank != 2:
            raise ValueError("C08 rank mismatch preflight contract drifted")
    elif candidate_rank != expected_actual_rank:
        raise ValueError("candidate shell rank differs from the construction")
    provisional = InterferenceModePreflightArtifact(
        preflight_schema_version=INTERFERENCE_MODE_PREFLIGHT_SCHEMA_VERSION,
        construction_state=INTERFERENCE_MODE_PREFLIGHT_STATE,
        scenario_kind=kind,
        control_case_id=control_case_id,
        scenario_id=scenario_id,
        parent_candidate_sha=verified_candidate.candidate_sha,
        candidate_application_sha=application.candidate_application_sha,
        based_on_application_spec_sha=application.based_on_application_spec_sha,
        scenario_sha=execution.scenario_sha,
        based_on_candidate_selector_sha=selector.selector_sha,
        response_template_sha=template.template_sha,
        prediction_profile_sha=profile.profile_sha,
        execution_recipe_id=recipe_id,
        state_schema_id=INTERFERENCE_MODE_STATE_SCHEMA_ID,
        channel_order=_CHANNEL_ORDER,
        spatial_ndim=1,
        actual_steps=actual_steps,
        matched_ablated_steps=matched_steps,
        primitive_support_radius=0,
        candidate_selector_disposition="REQUIRES_PARENT_SELECTOR_REFREEZE",
        source_readout_role="PROPOSED_PARENT_SELECTOR",
        candidate_source_injection=freeze_complex_tensor(candidate_source),
        candidate_readout_coisometry=freeze_complex_tensor(candidate_readout),
        proposed_source_selection=freeze_complex_tensor(source_selection),
        proposed_readout_selection=freeze_complex_tensor(readout_selection),
        source_injection=freeze_complex_tensor(source),
        readout=freeze_complex_tensor(readout),
        canonical_structure=freeze_complex_tensor(canonical),
        actual_sector_source_columns=sector_columns,
        reference_phase=float(math.pi / 2.0),
        reference_phase_band=phase_band[0],
        constructive_delta=constructive_delta,
        candidate_expected_actual_shell_rank=candidate_rank,
        expected_actual_shell_rank=expected_actual_rank,
        expected_matched_shell_rank=1,
        candidate_rank_disposition=rank_disposition,
        expected_survival_spectrum=expected_survival,
        expected_chi_extra=expected_chi_extra,
        expected_d_proc_sq=expected_d_proc,
        candidate_fejer_orders=CANDIDATE_FEJER_ORDERS,
        response_momenta=PREFLIGHT_MOMENTA,
        candidate_derivation_sha=derivation_sha,
        actual_effect_digest=_executed_effect_digest(actual_steps, "actual"),
        matched_ablated_effect_digest=_executed_effect_digest(
            actual_steps,
            "matched_ablated",
        ),
        preflight_sha="0" * 64,
    )
    return replace(
        provisional,
        preflight_sha=canonical_sha(
            interference_mode_preflight_artifact_payload(provisional)
        ),
    )


def _matrix_from_steps(
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
        shear[
            _CHANNEL_INDEX[step.destination_channel],
            _CHANNEL_INDEX[step.source_channel],
        ] += step.coefficient * phase
        matrix = shear @ matrix
    return matrix


def _validate_artifact(artifact: InterferenceModePreflightArtifact) -> None:
    _exact_record(
        artifact,
        InterferenceModePreflightArtifact,
        "interference/mode artifact",
    )
    artifact.__post_init__()
    for field in ("actual_steps", "matched_ablated_steps"):
        steps = getattr(artifact, field)
        if type(steps) is not tuple:
            raise TypeError(f"{field} must be an exact tuple")
        for index, step in enumerate(steps):
            _exact_record(step, ApplicationLocalShearStep, f"{field}[{index}]")
            step.__post_init__()
            if step.offset != (0,):
                raise ValueError("interference/mode support escaped the on-site cell")
            if step.step_sha != canonical_sha(
                application_local_shear_step_payload(step)
            ):
                raise ValueError("scalar shear step SHA mismatch")
    for field in (
        "candidate_source_injection",
        "candidate_readout_coisometry",
        "proposed_source_selection",
        "proposed_readout_selection",
        "source_injection",
        "readout",
        "canonical_structure",
    ):
        tensor = getattr(artifact, field)
        _exact_record(tensor, FrozenComplexTensor, field)
        verify_frozen_tensor(tensor)
    if artifact.preflight_sha != canonical_sha(
        interference_mode_preflight_artifact_payload(artifact)
    ):
        raise ValueError("interference/mode preflight SHA mismatch")
    if artifact.matched_ablated_steps != tuple(
        step for step in artifact.actual_steps if not step.target_conditioned
    ):
        raise ValueError("matched branch is not conditioned-slot deletion")
    if artifact.actual_effect_digest != _executed_effect_digest(
        artifact.actual_steps,
        "actual",
    ):
        raise ValueError("actual effect digest does not replay")
    if artifact.matched_ablated_effect_digest != _executed_effect_digest(
        artifact.actual_steps,
        "matched_ablated",
    ):
        raise ValueError("matched effect digest does not replay")
    candidate_source = frozen_tensor_array(artifact.candidate_source_injection)
    candidate_readout = frozen_tensor_array(artifact.candidate_readout_coisometry)
    proposed_source_selection = frozen_tensor_array(artifact.proposed_source_selection)
    proposed_readout_selection = frozen_tensor_array(
        artifact.proposed_readout_selection
    )
    source = frozen_tensor_array(artifact.source_injection)
    readout = frozen_tensor_array(artifact.readout)
    canonical = frozen_tensor_array(artifact.canonical_structure)
    if (
        candidate_source.shape != (4, 4)
        or candidate_readout.shape != (4, 4)
        or proposed_source_selection.shape[0] != 4
        or proposed_readout_selection.shape[1] != 4
        or source.shape[0] != 4
        or readout.shape[1] != 4
        or canonical.shape != (4, 4)
    ):
        raise ValueError("interference/mode rectangular maps have wrong state axis")
    if not np.array_equal(
        source,
        candidate_source @ proposed_source_selection,
    ):
        raise ValueError(
            "proposed source is not mechanically derived from candidate selector"
        )
    if not np.array_equal(
        readout,
        proposed_readout_selection @ candidate_readout,
    ):
        raise ValueError(
            "proposed readout is not mechanically derived from candidate selector"
        )
    if (
        float(np.linalg.norm(source.conj().T @ source - np.eye(source.shape[1]), 2))
        > 1.0e-12
    ):
        raise ValueError("source injection is not an isometry")
    if (
        float(np.linalg.norm(readout @ readout.conj().T - np.eye(readout.shape[0]), 2))
        > 1.0e-12
    ):
        raise ValueError("readout is not a coisometry")
    if tuple(sorted(set(artifact.actual_sector_source_columns))) != (
        artifact.actual_sector_source_columns
    ) or any(
        index >= source.shape[1] for index in artifact.actual_sector_source_columns
    ):
        raise ValueError("actual-sector source columns are not canonical")
    identity = np.eye(4, dtype=np.complex128)
    for branch_steps in (artifact.actual_steps, artifact.matched_ablated_steps):
        matrix = _matrix_from_steps(branch_steps, 0.0)
        if float(np.linalg.norm(matrix.conj().T @ matrix - identity, 2)) > 1.0e-12:
            raise ValueError("compiled scalar-shear composite is not unitary")
        if (
            float(np.linalg.norm(matrix.T @ canonical @ matrix - canonical, 2))
            > 1.0e-12
        ):
            raise ValueError("compiled scalar-shear composite is not symplectic")
        if float(np.linalg.norm(matrix.imag, 2)) > 1.0e-12:
            raise ValueError("compiled scalar-shear composite lost reality")


def build_interference_mode_preflight_artifact(
    candidate: ParentFreezeCandidateManifest,
    scenario_id: str,
) -> InterferenceModePreflightArtifact:
    """Compile one inert preflight from the exact provisional candidate."""

    if type(candidate) is not ParentFreezeCandidateManifest:
        raise TypeError("candidate must be an exact ParentFreezeCandidateManifest")
    identifier = _text(scenario_id, "scenario_id")
    artifact = _compile_artifact(candidate, identifier)
    _validate_artifact(artifact)
    return artifact


def verify_interference_mode_preflight_artifact(
    artifact: InterferenceModePreflightArtifact,
    candidate: Optional[ParentFreezeCandidateManifest] = None,
) -> InterferenceModePreflightArtifact:
    """Verify a preflight without materializing any authority-bearing object."""

    _validate_artifact(artifact)
    exact_candidate = (
        build_v3m0_parent_freeze_candidate() if candidate is None else candidate
    )
    if type(exact_candidate) is not ParentFreezeCandidateManifest:
        raise TypeError("candidate must be an exact ParentFreezeCandidateManifest")
    if artifact.parent_candidate_sha != exact_candidate.candidate_sha:
        raise ValueError("artifact is spliced to a different Parent candidate")
    canonical = _compile_artifact(exact_candidate, artifact.scenario_id)
    if artifact != canonical:
        raise ValueError("artifact differs from the canonical scenario prediction")
    return artifact


def interference_mode_preflight_symbol(
    artifact: InterferenceModePreflightArtifact,
    momentum: float,
    branch: Literal["actual", "matched_ablated"],
) -> np.ndarray:
    verified = verify_interference_mode_preflight_artifact(artifact)
    if type(momentum) is not float or not math.isfinite(momentum):
        raise TypeError("momentum must be a finite exact float")
    if branch == "actual":
        steps = verified.actual_steps
    elif branch == "matched_ablated":
        steps = verified.matched_ablated_steps
    else:
        raise ValueError("branch is outside the interference/mode preflight")
    return _matrix_from_steps(steps, momentum)


def build_interference_mode_preflight_trace_and_operators(
    artifact: InterferenceModePreflightArtifact,
    *,
    target_spec_id: str,
    interface: PrimitiveInterface,
) -> tuple[ConstructionTrace, tuple[PrimitiveOperatorWire, ...]]:
    """Bridge the frozen scalar layers into the real factory execution path."""

    verified = verify_interference_mode_preflight_artifact(artifact)
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
        raise ValueError("factory interface differs from the preflight artifact")
    prefix = f"v3m0.interference-mode.{verified.scenario_kind}.v1"
    blind_provenance_id = f"{prefix}.candidate-bound-local-grammar"
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
            source_sha=verified.preflight_sha,
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
        coefficient = sp.Rational(*step.coefficient.as_integer_ratio())
        specs.append(
            PrimitiveSpec(
                mechanism_id=mechanism_id,
                production_id=production_id,
                depends_on=(),
                support_offsets=((0,),),
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
    "CANDIDATE_FEJER_ORDERS",
    "CandidateRankDisposition",
    "CandidateSelectorDisposition",
    "CONSTRUCTIVE_DELTA",
    "INTERFERENCE_MODE_PREFLIGHT_SCHEMA_VERSION",
    "INTERFERENCE_MODE_PREFLIGHT_STATE",
    "INTERFERENCE_MODE_SCENARIO_IDS",
    "INTERFERENCE_MODE_STATE_SCHEMA_ID",
    "InterferenceModePreflightArtifact",
    "PREFLIGHT_MOMENTA",
    "SourceReadoutRole",
    "build_interference_mode_preflight_artifact",
    "build_interference_mode_preflight_trace_and_operators",
    "interference_mode_preflight_artifact_payload",
    "interference_mode_preflight_symbol",
    "verify_interference_mode_preflight_artifact",
]
