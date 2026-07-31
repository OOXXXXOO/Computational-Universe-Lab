"""Independent, inert Parent refreeze candidate assembled after preflight.

This module deliberately produces no ``ParentFreezeManifest``, signed erratum,
or authority wrapper.  The candidate is a self-hashed review wire chained to
the already-issued Parent and to the unique v1 candidate.  Scenario-level
preflight bindings are added below without modifying the issued Parent module.
"""

from __future__ import annotations

import re
import hashlib
import math
import struct
from dataclasses import dataclass, fields as dataclass_fields, replace
from pathlib import Path
from typing import Literal, Optional

import numpy as np

from .candidate_scenario_dag import (
    CandidateScenarioDAG,
    build_candidate_scenario_dag,
    candidate_scenario_dag_payload,
    extract_candidate_scenario_contract,
    verify_candidate_scenario_dag,
    verify_compiled_candidate_scenario_contract,
)
from .c12_incidence_preflight import (
    C12_PREFLIGHT_STATE,
    C12_SCENARIO_ID,
    build_c12_incidence_preflight,
    verify_c12_incidence_preflight,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    freeze_complex_tensor,
    frozen_tensor_payload,
    verify_frozen_tensor,
)
from .interference_mode_preflight import (
    INTERFERENCE_MODE_PREFLIGHT_STATE,
    INTERFERENCE_MODE_SCENARIO_IDS,
    build_interference_mode_preflight_artifact,
    verify_interference_mode_preflight_artifact,
)
from .parent_freeze import (
    ParentFreezeCandidateManifest,
    ScenarioBasisSelectorSpec,
    build_v3m0_parent_freeze_candidate,
    scenario_basis_selector_spec_payload,
    verify_parent_freeze_candidate,
)


PARENT_CANDIDATE_V2_SCHEMA_VERSION = "v3m0.parent-freeze-candidate.v2"
PARENT_CANDIDATE_V2_AUTHORITY_STATE = "PROVISIONAL_NOT_ISSUED"
PARENT_CANDIDATE_V2_BINDING_SCHEMA_VERSION = (
    "v3m0.parent-candidate-construction-preflight-binding.v1"
)
PARENT_CANDIDATE_V2_PREDICTION_QUANTITY_SCHEMA_VERSION = (
    "v3m0.parent-candidate-v2-prediction-quantity.v1"
)
PARENT_CANDIDATE_V2_PREDICTION_PROFILE_SCHEMA_VERSION = (
    "v3m0.parent-candidate-v2-prediction-profile.v1"
)
PARENT_CANDIDATE_V2_SCENARIO_REFREEZE_SCHEMA_VERSION = (
    "v3m0.parent-candidate-v2-scenario-refreeze.v1"
)
PARENT_CANDIDATE_V2_RESPONSE_TEMPLATE_SCHEMA_VERSION = (
    "v3m0.parent-candidate-v2-response-template.v1"
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_INTERFERENCE_SOURCE_PATH = "rulespace_v3/interference_mode_preflight.py"
_INTERFERENCE_SOURCE_SHA = (
    "8becf224bf41620f1da74b60dbeade5804bdbe7ecf340c2052f4e07ec2f4cc19"
)
_INTERFERENCE_COMMIT_SHA = "c87e94f12f5705cce025d7bd8ee6c25ebd919c73"
_C12_SOURCE_PATH = "rulespace_v3/c12_incidence_preflight.py"
_C12_SOURCE_SHA = (
    "c7ea862e12d5c01be08e7316dfe4e0a674a9a415bd67fea385286de234423ffb"
)
_C12_COMMIT_SHA = "b9b221d362a1d9a76ae14f26f9a90644b5be79ce"
_EXPECTED_PREFLIGHT_ARTIFACT_SHAS = {
    INTERFERENCE_MODE_SCENARIO_IDS[0]: (
        "880434e85ee9cbde10cf968adaad5ea8d868db653535a257c461acf5199cb4bf"
    ),
    INTERFERENCE_MODE_SCENARIO_IDS[1]: (
        "601ec8e7e33dddb2355d8fcf25ea1dd814c835243c6fabdb1a5ee56b20609f60"
    ),
    INTERFERENCE_MODE_SCENARIO_IDS[2]: (
        "691625e4eb95c6cc58b30e5641c80b50d049cd6ab462a947b9e9b0376c783465"
    ),
    INTERFERENCE_MODE_SCENARIO_IDS[3]: (
        "78730d39f991f9e951c2594274fddf2a1d5249f57f9c38d3aa5979fe138a8c58"
    ),
    C12_SCENARIO_ID: (
        "a3546be452486fe8fa2dd0dff840e5cae41f74b88c5dcf40e53b700e0f8da693"
    ),
}


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


def _git_sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_GIT_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase full Git SHA")
    return result


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    observed = frozenset(vars(value))
    if observed != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


@dataclass(frozen=True)
class CandidateV2PredictionQuantity:
    """Analytic-only prediction wire; finite-window measurements are illegal."""

    quantity_schema_version: str
    quantity_id: str
    branch_scope: str
    semantics: Literal[
        "MEASURED_EXACT",
        "FORMULA_DERIVED",
        "ANALYTIC_SIDE",
        "QUALITATIVE_REQUIRED",
    ]
    formula_id: Optional[str]
    analytic_side_labels: tuple[str, ...]
    qualitative_requirements: tuple[str, ...]
    parameter_refs: tuple[str, ...]
    quantity_sha: str

    def __post_init__(self) -> None:
        if self.quantity_schema_version != (
            PARENT_CANDIDATE_V2_PREDICTION_QUANTITY_SCHEMA_VERSION
        ):
            raise ValueError("candidate v2 prediction quantity schema drifted")
        _text(self.quantity_id, "quantity_id")
        _text(self.branch_scope, "branch_scope")
        if self.semantics == "MEASURED_EXACT":
            raise ValueError("measured predictions are forbidden in candidate v2")
        if self.semantics not in (
            "FORMULA_DERIVED",
            "ANALYTIC_SIDE",
            "QUALITATIVE_REQUIRED",
        ):
            raise ValueError("prediction semantics are outside the analytic grammar")
        for field in (
            "analytic_side_labels",
            "qualitative_requirements",
            "parameter_refs",
        ):
            values = getattr(self, field)
            if type(values) is not tuple or not all(
                type(item) is str and bool(item.strip()) for item in values
            ):
                raise TypeError(f"{field} must be an exact tuple of text refs")
        if self.semantics == "FORMULA_DERIVED":
            _text(self.formula_id, "formula_id")
            if self.analytic_side_labels or self.qualitative_requirements:
                raise ValueError("formula prediction carries non-formula payload")
        elif self.semantics == "ANALYTIC_SIDE":
            if self.formula_id is not None or not self.analytic_side_labels:
                raise ValueError("analytic-side prediction payload is incomplete")
            if self.qualitative_requirements or self.parameter_refs:
                raise ValueError("analytic-side prediction carries foreign payload")
        else:
            if self.formula_id is not None or not self.qualitative_requirements:
                raise ValueError("qualitative prediction payload is incomplete")
            if self.analytic_side_labels or self.parameter_refs:
                raise ValueError("qualitative prediction carries foreign payload")
        _sha(self.quantity_sha, "quantity_sha")


def candidate_v2_prediction_quantity_payload(
    quantity: CandidateV2PredictionQuantity,
) -> dict[str, object]:
    _exact_record(
        quantity,
        CandidateV2PredictionQuantity,
        "candidate v2 prediction quantity",
    )
    return {
        "quantity_schema_version": quantity.quantity_schema_version,
        "quantity_id": quantity.quantity_id,
        "branch_scope": quantity.branch_scope,
        "semantics": quantity.semantics,
        "formula_id": quantity.formula_id,
        "analytic_side_labels": list(quantity.analytic_side_labels),
        "qualitative_requirements": list(quantity.qualitative_requirements),
        "parameter_refs": list(quantity.parameter_refs),
    }


@dataclass(frozen=True)
class CandidateV2PredictionProfile:
    profile_schema_version: str
    scenario_id: str
    prediction_state: Literal[
        "PROVISIONAL_ANALYTIC_ONLY_NO_FINITE_T_VALUES"
    ]
    quantities: tuple[CandidateV2PredictionQuantity, ...]
    profile_sha: str

    def __post_init__(self) -> None:
        if self.profile_schema_version != (
            PARENT_CANDIDATE_V2_PREDICTION_PROFILE_SCHEMA_VERSION
        ):
            raise ValueError("candidate v2 prediction profile schema drifted")
        _text(self.scenario_id, "scenario_id")
        if self.prediction_state != (
            "PROVISIONAL_ANALYTIC_ONLY_NO_FINITE_T_VALUES"
        ):
            raise ValueError("candidate v2 prediction profile claimed measurement")
        if (
            type(self.quantities) is not tuple
            or not self.quantities
            or not all(
                type(item) is CandidateV2PredictionQuantity
                for item in self.quantities
            )
        ):
            raise TypeError("prediction quantities have the wrong strict type")
        _sha(self.profile_sha, "profile_sha")


def candidate_v2_prediction_profile_payload(
    profile: CandidateV2PredictionProfile,
) -> dict[str, object]:
    _exact_record(
        profile,
        CandidateV2PredictionProfile,
        "candidate v2 prediction profile",
    )
    return {
        "profile_schema_version": profile.profile_schema_version,
        "scenario_id": profile.scenario_id,
        "prediction_state": profile.prediction_state,
        "quantities": [
            {
                **candidate_v2_prediction_quantity_payload(item),
                "quantity_sha": item.quantity_sha,
            }
            for item in profile.quantities
        ],
    }


def _prediction_quantity(
    quantity_id: str,
    branch_scope: str,
    semantics: Literal[
        "FORMULA_DERIVED",
        "ANALYTIC_SIDE",
        "QUALITATIVE_REQUIRED",
    ],
    *,
    formula_id: Optional[str] = None,
    analytic_side_labels: tuple[str, ...] = (),
    qualitative_requirements: tuple[str, ...] = (),
    parameter_refs: tuple[str, ...] = (),
) -> CandidateV2PredictionQuantity:
    provisional = CandidateV2PredictionQuantity(
        quantity_schema_version=(
            PARENT_CANDIDATE_V2_PREDICTION_QUANTITY_SCHEMA_VERSION
        ),
        quantity_id=quantity_id,
        branch_scope=branch_scope,
        semantics=semantics,
        formula_id=formula_id,
        analytic_side_labels=analytic_side_labels,
        qualitative_requirements=qualitative_requirements,
        parameter_refs=parameter_refs,
        quantity_sha="0" * 64,
    )
    return replace(
        provisional,
        quantity_sha=canonical_sha(
            candidate_v2_prediction_quantity_payload(provisional)
        ),
    )


def _build_candidate_v2_prediction_profile(
    scenario_id: str,
) -> CandidateV2PredictionProfile:
    registered = (*INTERFERENCE_MODE_SCENARIO_IDS, C12_SCENARIO_ID)
    if scenario_id not in registered:
        raise ValueError("scenario is outside the candidate v2 prediction registry")
    quantities = [
        _prediction_quantity(
            "expected-actual-shell-rank",
            "actual",
            "FORMULA_DERIVED",
            formula_id="rank-of-analytic-transition-selector-composite-v1",
            parameter_refs=(
                "operation-dag.local-transition-recipe",
                "operation-dag.closed-form-selector",
            ),
        ),
        _prediction_quantity(
            "expected-matched-shell-rank",
            "matched_ablated",
            "FORMULA_DERIVED",
            formula_id="rank-after-mechanical-target-slot-deletion-v1",
            parameter_refs=(
                "operation-dag.local-transition-recipe",
                "operation-dag.analytic-causal-contract",
            ),
        ),
    ]
    if scenario_id == C12_SCENARIO_ID:
        quantities.extend(
            (
                _prediction_quantity(
                    "incidence-normalized-ir-limit",
                    "actual_and_matched_ablated",
                    "FORMULA_DERIVED",
                    formula_id="nu-inc-cyclotomic-ir-limit-v1",
                    parameter_refs=(
                        "operation-dag.incidence-analytic-contract",
                        "threshold-registry.absolute-signal",
                        "threshold-registry.raw-bridge-noise",
                        "threshold-registry.relative-gap",
                    ),
                ),
                _prediction_quantity(
                    "incidence-application-side",
                    "actual_and_matched_ablated",
                    "ANALYTIC_SIDE",
                    analytic_side_labels=(
                        "POST_RESPONSE_READOUT_ONLY",
                        "NO_GLOBAL_FFT_PROJECTION",
                        "NO_PER_K_TIME_STEP_PROJECTOR",
                    ),
                ),
            )
        )
    else:
        quantities.append(
            _prediction_quantity(
                "causal-spectrum-signature",
                "actual_vs_matched_ablated",
                "FORMULA_DERIVED",
                formula_id="analytic-sector-singular-support-contract-v1",
                parameter_refs=("operation-dag.analytic-causal-contract",),
            )
        )
        if scenario_id == INTERFERENCE_MODE_SCENARIO_IDS[3]:
            quantities.append(
                _prediction_quantity(
                    "process-distance-domain",
                    "actual_vs_matched_ablated",
                    "QUALITATIVE_REQUIRED",
                    qualitative_requirements=(
                        "UNDEFINED_WHEN_MATCHED_ANALYTIC_SECTOR_VANISHES",
                    ),
                )
            )
    provisional = CandidateV2PredictionProfile(
        profile_schema_version=(
            PARENT_CANDIDATE_V2_PREDICTION_PROFILE_SCHEMA_VERSION
        ),
        scenario_id=scenario_id,
        prediction_state="PROVISIONAL_ANALYTIC_ONLY_NO_FINITE_T_VALUES",
        quantities=tuple(quantities),
        profile_sha="0" * 64,
    )
    return replace(
        provisional,
        profile_sha=canonical_sha(
            candidate_v2_prediction_profile_payload(provisional)
        ),
    )


def build_candidate_v2_prediction_profile(
    scenario_id: str,
) -> CandidateV2PredictionProfile:
    return verify_candidate_v2_prediction_profile(
        _build_candidate_v2_prediction_profile(scenario_id)
    )


def verify_candidate_v2_prediction_profile(
    profile: CandidateV2PredictionProfile,
) -> CandidateV2PredictionProfile:
    _exact_record(
        profile,
        CandidateV2PredictionProfile,
        "candidate v2 prediction profile",
    )
    profile.__post_init__()
    for quantity in profile.quantities:
        _exact_record(
            quantity,
            CandidateV2PredictionQuantity,
            "candidate v2 prediction quantity",
        )
        quantity.__post_init__()
        if quantity.quantity_sha != canonical_sha(
            candidate_v2_prediction_quantity_payload(quantity)
        ):
            raise ValueError("prediction quantity SHA does not match its body")
    if profile.profile_sha != canonical_sha(
        candidate_v2_prediction_profile_payload(profile)
    ):
        raise ValueError("prediction profile SHA does not match its body")
    if profile != _build_candidate_v2_prediction_profile(profile.scenario_id):
        raise ValueError("prediction profile differs from analytic registry")
    return profile


@dataclass(frozen=True)
class CandidateConstructionPreflightBinding:
    """Exact source/commit/artifact provenance from a live preflight replay."""

    binding_schema_version: str
    scenario_id: str
    preflight_kind: Literal[
        "INTERFERENCE_MODE_CONSTRUCTION",
        "C12_INCIDENCE_CONSTRUCTION",
    ]
    source_path: str
    source_sha: str
    source_commit_sha: str
    candidate_v1_sha: str
    candidate_application_sha: str
    candidate_scenario_sha: str
    scenario_execution_spec_sha: str
    based_on_application_spec_sha: str
    preflight_state: str
    preflight_artifact_sha: str
    derivation_or_recipe_sha: str
    binding_sha: str

    def __post_init__(self) -> None:
        if self.binding_schema_version != (
            PARENT_CANDIDATE_V2_BINDING_SCHEMA_VERSION
        ):
            raise ValueError("preflight binding schema is not frozen")
        _text(self.scenario_id, "scenario_id")
        if self.preflight_kind not in (
            "INTERFERENCE_MODE_CONSTRUCTION",
            "C12_INCIDENCE_CONSTRUCTION",
        ):
            raise ValueError("preflight kind is outside the candidate grammar")
        _text(self.source_path, "source_path")
        _sha(self.source_sha, "source_sha")
        _git_sha(self.source_commit_sha, "source_commit_sha")
        for field in (
            "candidate_v1_sha",
            "candidate_application_sha",
            "candidate_scenario_sha",
            "scenario_execution_spec_sha",
            "based_on_application_spec_sha",
            "preflight_artifact_sha",
            "derivation_or_recipe_sha",
            "binding_sha",
        ):
            _sha(getattr(self, field), field)
        _text(self.preflight_state, "preflight_state")


def candidate_construction_preflight_binding_payload(
    binding: CandidateConstructionPreflightBinding,
) -> dict[str, object]:
    _exact_record(
        binding,
        CandidateConstructionPreflightBinding,
        "construction preflight binding",
    )
    return {
        "binding_schema_version": binding.binding_schema_version,
        "scenario_id": binding.scenario_id,
        "preflight_kind": binding.preflight_kind,
        "source_path": binding.source_path,
        "source_sha": binding.source_sha,
        "source_commit_sha": binding.source_commit_sha,
        "candidate_v1_sha": binding.candidate_v1_sha,
        "candidate_application_sha": binding.candidate_application_sha,
        "candidate_scenario_sha": binding.candidate_scenario_sha,
        "scenario_execution_spec_sha": binding.scenario_execution_spec_sha,
        "based_on_application_spec_sha": binding.based_on_application_spec_sha,
        "preflight_state": binding.preflight_state,
        "preflight_artifact_sha": binding.preflight_artifact_sha,
        "derivation_or_recipe_sha": binding.derivation_or_recipe_sha,
    }


def _finish_binding(
    provisional: CandidateConstructionPreflightBinding,
) -> CandidateConstructionPreflightBinding:
    return replace(
        provisional,
        binding_sha=canonical_sha(
            candidate_construction_preflight_binding_payload(provisional)
        ),
    )


def _live_source_sha(source_path: str) -> str:
    path = (_REPOSITORY_ROOT / source_path).resolve()
    if path.parent != (_REPOSITORY_ROOT / "rulespace_v3").resolve():
        raise ValueError("preflight source path escapes rulespace_v3")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_live_preflight_bindings(
    candidate_v1: ParentFreezeCandidateManifest,
) -> tuple[CandidateConstructionPreflightBinding, ...]:
    if _live_source_sha(_INTERFERENCE_SOURCE_PATH) != _INTERFERENCE_SOURCE_SHA:
        raise ValueError("interference preflight source SHA drifted")
    if _live_source_sha(_C12_SOURCE_PATH) != _C12_SOURCE_SHA:
        raise ValueError("C12 preflight source SHA drifted")

    bindings: list[CandidateConstructionPreflightBinding] = []
    for scenario_id in INTERFERENCE_MODE_SCENARIO_IDS:
        artifact = build_interference_mode_preflight_artifact(
            candidate_v1,
            scenario_id,
        )
        verify_interference_mode_preflight_artifact(artifact, candidate_v1)
        if artifact.preflight_sha != _EXPECTED_PREFLIGHT_ARTIFACT_SHAS[scenario_id]:
            raise ValueError("interference live preflight artifact SHA drifted")
        _, candidate_scenario = _find_candidate_v1_scenario(
            candidate_v1,
            scenario_id,
        )
        bindings.append(
            _finish_binding(
                CandidateConstructionPreflightBinding(
                    binding_schema_version=(
                        PARENT_CANDIDATE_V2_BINDING_SCHEMA_VERSION
                    ),
                    scenario_id=scenario_id,
                    preflight_kind="INTERFERENCE_MODE_CONSTRUCTION",
                    source_path=_INTERFERENCE_SOURCE_PATH,
                    source_sha=_INTERFERENCE_SOURCE_SHA,
                    source_commit_sha=_INTERFERENCE_COMMIT_SHA,
                    candidate_v1_sha=candidate_v1.candidate_sha,
                    candidate_application_sha=artifact.candidate_application_sha,
                    candidate_scenario_sha=(
                        candidate_scenario.candidate_scenario_sha
                    ),
                    scenario_execution_spec_sha=artifact.scenario_sha,
                    based_on_application_spec_sha=(
                        artifact.based_on_application_spec_sha
                    ),
                    preflight_state=INTERFERENCE_MODE_PREFLIGHT_STATE,
                    preflight_artifact_sha=artifact.preflight_sha,
                    derivation_or_recipe_sha=artifact.candidate_derivation_sha,
                    binding_sha="0" * 64,
                )
            )
        )

    c12 = build_c12_incidence_preflight(candidate_v1)
    verify_c12_incidence_preflight(candidate_v1, c12)
    if c12.preflight_sha != _EXPECTED_PREFLIGHT_ARTIFACT_SHAS[C12_SCENARIO_ID]:
        raise ValueError("C12 live preflight artifact SHA drifted")
    bindings.append(
        _finish_binding(
            CandidateConstructionPreflightBinding(
                binding_schema_version=PARENT_CANDIDATE_V2_BINDING_SCHEMA_VERSION,
                scenario_id=C12_SCENARIO_ID,
                preflight_kind="C12_INCIDENCE_CONSTRUCTION",
                source_path=_C12_SOURCE_PATH,
                source_sha=_C12_SOURCE_SHA,
                source_commit_sha=_C12_COMMIT_SHA,
                candidate_v1_sha=candidate_v1.candidate_sha,
                candidate_application_sha=c12.candidate_application_sha,
                candidate_scenario_sha=c12.candidate_scenario_sha,
                scenario_execution_spec_sha=c12.recipe.scenario_sha,
                based_on_application_spec_sha=(
                    c12.recipe.based_on_application_spec_sha
                ),
                preflight_state=C12_PREFLIGHT_STATE,
                preflight_artifact_sha=c12.preflight_sha,
                derivation_or_recipe_sha=c12.recipe.recipe_sha,
                binding_sha="0" * 64,
            )
        )
    )
    return tuple(bindings)


@dataclass(frozen=True)
class CandidateV2ResponseTemplate:
    """V2-only response design bound to one extracted construction contract."""

    template_schema_version: str
    construction_state: Literal[
        "PROVISIONAL_ANALYTIC_TEMPLATE_AFTER_LIVE_PREFLIGHT"
    ]
    scenario_id: str
    selector_sha: str
    dag_sha: str
    compiled_contract_sha: str
    construction_rule_id: str
    construction_family_id: str
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    actual_program_sha: str
    matched_ablated_program_sha: str
    preflight_derivation_or_recipe_sha: str
    preflight_actual_effect_digest: str
    preflight_matched_effect_digest: str
    response_torus_denominators: tuple[int, ...]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    source_trial_vectors: FrozenComplexTensor
    incidence_family_id: Optional[str]
    incidence_normalizer_formula_id: Optional[str]
    incidence_application_stage: Optional[str]
    absolute_signal_threshold_authority_ref: Optional[str]
    raw_bridge_noise_evidence_ref: Optional[str]
    raw_noise_absolute_threshold_authority_ref: Optional[str]
    relative_gap_threshold_authority_ref: Optional[str]
    uses_global_fft_projection: Literal[False]
    uses_per_k_time_step_projector: Literal[False]
    template_sha: str

    def __post_init__(self) -> None:
        if self.template_schema_version != (
            PARENT_CANDIDATE_V2_RESPONSE_TEMPLATE_SCHEMA_VERSION
        ):
            raise ValueError("candidate v2 response template schema drifted")
        if self.construction_state != (
            "PROVISIONAL_ANALYTIC_TEMPLATE_AFTER_LIVE_PREFLIGHT"
        ):
            raise ValueError("candidate v2 response template claimed authority")
        for field in (
            "scenario_id",
            "construction_rule_id",
            "construction_family_id",
        ):
            _text(getattr(self, field), field)
        for field in (
            "selector_sha",
            "dag_sha",
            "compiled_contract_sha",
            "actual_program_sha",
            "matched_ablated_program_sha",
            "preflight_derivation_or_recipe_sha",
            "preflight_actual_effect_digest",
            "preflight_matched_effect_digest",
            "template_sha",
        ):
            _sha(getattr(self, field), field)
        for field in (
            "expected_actual_shell_rank",
            "expected_matched_shell_rank",
        ):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise TypeError(f"{field} must be a positive exact integer")
        if (
            type(self.response_torus_denominators) is not tuple
            or not self.response_torus_denominators
            or not all(
                type(item) is int and item > 0
                for item in self.response_torus_denominators
            )
        ):
            raise TypeError("response_torus_denominators are not positive integers")
        for field in (
            "response_reciprocal_indices",
            "source_readout_bridge_reciprocal_indices",
        ):
            value = getattr(self, field)
            if type(value) is not tuple or not all(
                type(item) is tuple
                and item
                and all(type(index) is int for index in item)
                for item in value
            ):
                raise TypeError(f"{field} is not an exact integer tuple grid")
        if (
            type(self.source_readout_bridge_steps) is not tuple
            or not all(
                type(item) is int and item > 0
                for item in self.source_readout_bridge_steps
            )
        ):
            raise TypeError("source_readout_bridge_steps are not positive integers")
        if (
            type(self.reference_reciprocal_index) is not tuple
            or not self.reference_reciprocal_index
            or not all(
                type(item) is int for item in self.reference_reciprocal_index
            )
        ):
            raise TypeError("reference_reciprocal_index is not an integer tuple")
        if (
            type(self.preregistered_phase_bands) is not tuple
            or not all(
                type(item) is tuple
                and len(item) == 2
                and all(type(value) is float and math.isfinite(value) for value in item)
                for item in self.preregistered_phase_bands
            )
        ):
            raise TypeError("preregistered_phase_bands are not finite fp64 pairs")
        if type(self.source_trial_vectors) is not FrozenComplexTensor:
            raise TypeError("source_trial_vectors has the wrong strict type")
        verify_frozen_tensor(self.source_trial_vectors)
        incidence_fields = (
            self.incidence_family_id,
            self.incidence_normalizer_formula_id,
            self.incidence_application_stage,
            self.absolute_signal_threshold_authority_ref,
            self.raw_bridge_noise_evidence_ref,
            self.raw_noise_absolute_threshold_authority_ref,
            self.relative_gap_threshold_authority_ref,
        )
        if self.scenario_id == C12_SCENARIO_ID:
            if any(item is None for item in incidence_fields):
                raise ValueError("C12 response template incidence refs are incomplete")
            for index, item in enumerate(incidence_fields):
                _text(item, f"incidence_fields[{index}]")
        elif any(item is not None for item in incidence_fields):
            raise ValueError("non-C12 response template carries incidence refs")
        if self.uses_global_fft_projection is not False:
            raise ValueError("response template cannot use global FFT projection")
        if self.uses_per_k_time_step_projector is not False:
            raise ValueError("response template cannot use per-k timestep projection")


def candidate_v2_response_template_payload(
    template: CandidateV2ResponseTemplate,
) -> dict[str, object]:
    _exact_record(
        template,
        CandidateV2ResponseTemplate,
        "candidate v2 response template",
    )
    return {
        "template_schema_version": template.template_schema_version,
        "construction_state": template.construction_state,
        "scenario_id": template.scenario_id,
        "selector_sha": template.selector_sha,
        "dag_sha": template.dag_sha,
        "compiled_contract_sha": template.compiled_contract_sha,
        "construction_rule_id": template.construction_rule_id,
        "construction_family_id": template.construction_family_id,
        "expected_actual_shell_rank": template.expected_actual_shell_rank,
        "expected_matched_shell_rank": template.expected_matched_shell_rank,
        "actual_program_sha": template.actual_program_sha,
        "matched_ablated_program_sha": template.matched_ablated_program_sha,
        "preflight_derivation_or_recipe_sha": (
            template.preflight_derivation_or_recipe_sha
        ),
        "preflight_actual_effect_digest": (
            template.preflight_actual_effect_digest
        ),
        "preflight_matched_effect_digest": (
            template.preflight_matched_effect_digest
        ),
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
        "source_trial_vectors": {
            **frozen_tensor_payload(template.source_trial_vectors),
            "tensor_sha": template.source_trial_vectors.tensor_sha,
        },
        "incidence_family_id": template.incidence_family_id,
        "incidence_normalizer_formula_id": (
            template.incidence_normalizer_formula_id
        ),
        "incidence_application_stage": template.incidence_application_stage,
        "absolute_signal_threshold_authority_ref": (
            template.absolute_signal_threshold_authority_ref
        ),
        "raw_bridge_noise_evidence_ref": (
            template.raw_bridge_noise_evidence_ref
        ),
        "raw_noise_absolute_threshold_authority_ref": (
            template.raw_noise_absolute_threshold_authority_ref
        ),
        "relative_gap_threshold_authority_ref": (
            template.relative_gap_threshold_authority_ref
        ),
        "uses_global_fft_projection": template.uses_global_fft_projection,
        "uses_per_k_time_step_projector": (
            template.uses_per_k_time_step_projector
        ),
    }


@dataclass(frozen=True)
class CandidateV2ScenarioRefreeze:
    """One proposed scenario refreeze, still carrying no authority."""

    scenario_refreeze_schema_version: str
    construction_state: Literal[
        "PROVISIONAL_REFREEZE_RECORD_NO_AUTHORITY"
    ]
    control_case_id: str
    scenario_id: str
    preflight_binding_sha: str
    operation_dag: CandidateScenarioDAG
    proposed_selector_spec: ScenarioBasisSelectorSpec
    response_template: CandidateV2ResponseTemplate
    prediction_profile: CandidateV2PredictionProfile
    scenario_refreeze_sha: str

    def __post_init__(self) -> None:
        if self.scenario_refreeze_schema_version != (
            PARENT_CANDIDATE_V2_SCENARIO_REFREEZE_SCHEMA_VERSION
        ):
            raise ValueError("candidate v2 scenario refreeze schema drifted")
        if self.construction_state != (
            "PROVISIONAL_REFREEZE_RECORD_NO_AUTHORITY"
        ):
            raise ValueError("candidate v2 scenario refreeze claimed authority")
        _text(self.control_case_id, "control_case_id")
        _text(self.scenario_id, "scenario_id")
        _sha(self.preflight_binding_sha, "preflight_binding_sha")
        if type(self.operation_dag) is not CandidateScenarioDAG:
            raise TypeError("operation_dag has the wrong strict type")
        if type(self.proposed_selector_spec) is not ScenarioBasisSelectorSpec:
            raise TypeError("proposed_selector_spec has the wrong strict type")
        if type(self.response_template) is not CandidateV2ResponseTemplate:
            raise TypeError("response_template has the wrong strict type")
        if type(self.prediction_profile) is not CandidateV2PredictionProfile:
            raise TypeError("prediction_profile has the wrong strict type")
        _sha(self.scenario_refreeze_sha, "scenario_refreeze_sha")


def candidate_v2_scenario_refreeze_payload(
    refreeze: CandidateV2ScenarioRefreeze,
) -> dict[str, object]:
    _exact_record(
        refreeze,
        CandidateV2ScenarioRefreeze,
        "candidate v2 scenario refreeze",
    )
    return {
        "scenario_refreeze_schema_version": (
            refreeze.scenario_refreeze_schema_version
        ),
        "construction_state": refreeze.construction_state,
        "control_case_id": refreeze.control_case_id,
        "scenario_id": refreeze.scenario_id,
        "preflight_binding_sha": refreeze.preflight_binding_sha,
        "operation_dag": {
            **candidate_scenario_dag_payload(refreeze.operation_dag),
            "dag_sha": refreeze.operation_dag.dag_sha,
        },
        "proposed_selector_spec": {
            **scenario_basis_selector_spec_payload(
                refreeze.proposed_selector_spec
            ),
            "selector_sha": refreeze.proposed_selector_spec.selector_sha,
        },
        "response_template": {
            **candidate_v2_response_template_payload(refreeze.response_template),
            "template_sha": refreeze.response_template.template_sha,
        },
        "prediction_profile": {
            **candidate_v2_prediction_profile_payload(
                refreeze.prediction_profile
            ),
            "profile_sha": refreeze.prediction_profile.profile_sha,
        },
    }


def _find_candidate_v1_scenario(
    candidate_v1: ParentFreezeCandidateManifest,
    scenario_id: str,
) -> tuple[object, object]:
    matches = tuple(
        (application, scenario)
        for application in candidate_v1.application_candidates
        for scenario in application.scenario_candidates
        if scenario.scenario_execution_spec.scenario_id == scenario_id
    )
    if len(matches) != 1:
        raise ValueError("candidate v1 scenario is not unique")
    return matches[0]


def _refrozen_selector(
    candidate_v1: ParentFreezeCandidateManifest,
    scenario_id: str,
    source_selector,
    readout_selector,
    source_injection,
    readout_coisometry,
) -> ScenarioBasisSelectorSpec:
    _, scenario = _find_candidate_v1_scenario(candidate_v1, scenario_id)
    base = scenario.selector_spec
    derivation_ids = {
        INTERFERENCE_MODE_SCENARIO_IDS[0]: (
            "c07-constructive-delta-pi-over-8192-source-selector-v1",
            "c07-constructive-p0-observer-selector-v1",
        ),
        INTERFERENCE_MODE_SCENARIO_IDS[1]: (
            "c07-destructive-weighted-q0-q1-source-selector-v1",
            "c07-destructive-orthogonal-p0-p1-observer-selector-v1",
        ),
        INTERFERENCE_MODE_SCENARIO_IDS[2]: (
            "c08-two-axis-rank2-missing-mode-source-selector-v1",
            "c08-two-axis-rank2-missing-mode-readout-selector-v1",
        ),
        INTERFERENCE_MODE_SCENARIO_IDS[3]: (
            "c10-full-source-actual-sector-first-column-source-selector-v1",
            "c10-full-source-actual-sector-first-column-readout-selector-v1",
        ),
    }
    source_derivation, readout_derivation = derivation_ids[scenario_id]
    provisional = ScenarioBasisSelectorSpec(
        selector_schema_version=base.selector_schema_version,
        scenario_id=scenario_id,
        public_source_basis_manifest_id=base.public_source_basis_manifest_id,
        public_readout_basis_manifest_id=base.public_readout_basis_manifest_id,
        source_selector_derivation_id=source_derivation,
        readout_selector_derivation_id=readout_derivation,
        source_selector=source_selector,
        readout_selector=readout_selector,
        source_injection=source_injection,
        readout_coisometry=readout_coisometry,
        selector_sha="0" * 64,
    )
    return replace(
        provisional,
        selector_sha=canonical_sha(
            scenario_basis_selector_spec_payload(provisional)
        ),
    )


def _refrozen_response_template(
    candidate_v1: ParentFreezeCandidateManifest,
    scenario_id: str,
    selector: ScenarioBasisSelectorSpec,
    contract: object,
    binding: CandidateConstructionPreflightBinding,
    *,
    construction_rule_id: str,
    construction_family_id: str,
    preflight_actual_effect_digest: str,
    preflight_matched_effect_digest: str,
) -> CandidateV2ResponseTemplate:
    _, scenario = _find_candidate_v1_scenario(candidate_v1, scenario_id)
    base = scenario.response_template
    source_columns = selector.source_selector.shape[1]
    provisional = CandidateV2ResponseTemplate(
        template_schema_version=(
            PARENT_CANDIDATE_V2_RESPONSE_TEMPLATE_SCHEMA_VERSION
        ),
        construction_state=(
            "PROVISIONAL_ANALYTIC_TEMPLATE_AFTER_LIVE_PREFLIGHT"
        ),
        scenario_id=scenario_id,
        selector_sha=selector.selector_sha,
        dag_sha=contract.dag_sha,
        compiled_contract_sha=contract.contract_sha,
        construction_rule_id=construction_rule_id,
        construction_family_id=construction_family_id,
        expected_actual_shell_rank=contract.expected_actual_shell_rank,
        expected_matched_shell_rank=contract.expected_matched_shell_rank,
        actual_program_sha=contract.actual_program_sha,
        matched_ablated_program_sha=contract.matched_ablated_program_sha,
        preflight_derivation_or_recipe_sha=binding.derivation_or_recipe_sha,
        preflight_actual_effect_digest=preflight_actual_effect_digest,
        preflight_matched_effect_digest=preflight_matched_effect_digest,
        response_torus_denominators=base.response_torus_denominators,
        response_reciprocal_indices=base.response_reciprocal_indices,
        source_readout_bridge_reciprocal_indices=(
            base.source_readout_bridge_reciprocal_indices
        ),
        source_readout_bridge_steps=base.source_readout_bridge_steps,
        reference_reciprocal_index=base.reference_reciprocal_index,
        preregistered_phase_bands=base.preregistered_phase_bands,
        source_trial_vectors=freeze_complex_tensor(
            np.eye(source_columns, dtype=np.complex128)
        ),
        incidence_family_id=contract.incidence_family_id,
        incidence_normalizer_formula_id=(
            contract.incidence_normalizer_formula_id
        ),
        incidence_application_stage=contract.incidence_application_stage,
        absolute_signal_threshold_authority_ref=(
            contract.absolute_signal_threshold_authority_ref
        ),
        raw_bridge_noise_evidence_ref=contract.raw_bridge_noise_evidence_ref,
        raw_noise_absolute_threshold_authority_ref=(
            contract.raw_noise_absolute_threshold_authority_ref
        ),
        relative_gap_threshold_authority_ref=(
            contract.relative_gap_threshold_authority_ref
        ),
        uses_global_fft_projection=False,
        uses_per_k_time_step_projector=False,
        template_sha="0" * 64,
    )
    return replace(
        provisional,
        template_sha=canonical_sha(
            candidate_v2_response_template_payload(provisional)
        ),
    )


def _step_signature_body(step: object) -> tuple[object, ...]:
    return (
        step.step_id,
        step.source_channel,
        step.destination_channel,
        step.offset,
        struct.pack(">d", step.coefficient),
        step.target_conditioned,
    )


def _require_live_step_program_match(
    contract: object,
    actual_steps: tuple[object, ...],
    matched_steps: tuple[object, ...],
) -> None:
    if tuple(
        _step_signature_body(item)
        for item in contract.actual_step_signatures
    ) != tuple(_step_signature_body(item) for item in actual_steps):
        raise ValueError("DAG actual shear program differs from live preflight")
    if tuple(
        _step_signature_body(item)
        for item in contract.matched_ablated_step_signatures
    ) != tuple(_step_signature_body(item) for item in matched_steps):
        raise ValueError("DAG matched shear program differs from live preflight")


def _build_scenario_refreeze(
    candidate_v1: ParentFreezeCandidateManifest,
    binding: CandidateConstructionPreflightBinding,
) -> CandidateV2ScenarioRefreeze:
    scenario_id = binding.scenario_id
    if scenario_id not in (*INTERFERENCE_MODE_SCENARIO_IDS, C12_SCENARIO_ID):
        raise ValueError("scenario binding is outside the refreeze registry")
    application, candidate_scenario = _find_candidate_v1_scenario(
        candidate_v1,
        scenario_id,
    )
    if (
        binding.candidate_scenario_sha
        != candidate_scenario.candidate_scenario_sha
        or binding.scenario_execution_spec_sha
        != candidate_scenario.scenario_execution_spec.scenario_sha
    ):
        raise ValueError("scenario binding is spliced from its candidate-v1 roots")
    dag = build_candidate_scenario_dag(
        scenario_id,
        based_on_candidate_selector_sha=(
            candidate_scenario.selector_spec.selector_sha
        ),
    )
    contract = extract_candidate_scenario_contract(dag)
    verify_compiled_candidate_scenario_contract(dag, contract)
    if scenario_id in INTERFERENCE_MODE_SCENARIO_IDS:
        artifact = build_interference_mode_preflight_artifact(
            candidate_v1,
            scenario_id,
        )
        verify_interference_mode_preflight_artifact(artifact, candidate_v1)
        if (
            binding.preflight_artifact_sha != artifact.preflight_sha
            or binding.derivation_or_recipe_sha
            != artifact.candidate_derivation_sha
        ):
            raise ValueError("scenario is spliced from its interference preflight")
        _require_live_step_program_match(
            contract,
            artifact.actual_steps,
            artifact.matched_ablated_steps,
        )
        if (
            contract.proposed_source_selection.tensor_sha
            != artifact.proposed_source_selection.tensor_sha
            or contract.proposed_readout_selection.tensor_sha
            != artifact.proposed_readout_selection.tensor_sha
        ):
            raise ValueError("DAG selector differs bitwise from live preflight")
        if (
            contract.actual_sector_source_columns
            != artifact.actual_sector_source_columns
            or contract.expected_actual_shell_rank
            != artifact.expected_actual_shell_rank
            or contract.expected_matched_shell_rank
            != artifact.expected_matched_shell_rank
            or contract.expected_survival_spectrum
            != artifact.expected_survival_spectrum
            or contract.expected_chi_extra != artifact.expected_chi_extra
            or contract.expected_d_proc_sq != artifact.expected_d_proc_sq
        ):
            raise ValueError("DAG analytic contract differs from live preflight")
        selector = _refrozen_selector(
            candidate_v1,
            scenario_id,
            contract.proposed_source_selection,
            contract.proposed_readout_selection,
            artifact.source_injection,
            artifact.readout,
        )
        construction_rule_id = artifact.execution_recipe_id
        construction_family_id = (
            f"interference-mode-{artifact.scenario_kind}-v1"
        )
        preflight_actual_effect_digest = artifact.actual_effect_digest
        preflight_matched_effect_digest = (
            artifact.matched_ablated_effect_digest
        )
    else:
        c12 = build_c12_incidence_preflight(candidate_v1)
        verify_c12_incidence_preflight(candidate_v1, c12)
        recipe = c12.recipe
        certificate = c12.ir_certificate
        if (
            binding.preflight_artifact_sha != c12.preflight_sha
            or binding.derivation_or_recipe_sha != recipe.recipe_sha
        ):
            raise ValueError("scenario is spliced from its C12 preflight")
        _require_live_step_program_match(
            contract,
            recipe.actual_steps,
            recipe.matched_ablated_steps,
        )
        selector = recipe.proposed_selector_spec
        if (
            contract.proposed_source_selection.tensor_sha
            != selector.source_selector.tensor_sha
            or contract.proposed_readout_selection.tensor_sha
            != selector.readout_selector.tensor_sha
            or contract.expected_actual_shell_rank
            != recipe.proposed_expected_shell_rank
            or contract.expected_matched_shell_rank
            != recipe.proposed_expected_shell_rank
            or contract.primitive_support_radius
            != recipe.primitive_support_radius
            or contract.uses_global_fft_projection
            != recipe.uses_global_fft_projection
            or contract.uses_per_k_time_step_projector
            != recipe.uses_per_k_time_step_projector
            or contract.incidence_family_id != certificate.incidence_family_id
            or contract.incidence_normalizer_formula_id
            != certificate.normalizer_formula_id
            or contract.incidence_application_stage
            != recipe.incidence_application_stage
            or contract.incidence_stencil_offsets != certificate.stencil_offsets
            or contract.incidence_stencil_coefficients
            != certificate.stencil_coefficients
            or contract.ir_limit_order != certificate.ir_limit_order
            or contract.ir_limit_formula_id != certificate.ir_limit_formula_id
            or contract.response_torus_denominator
            != recipe.response_torus_denominator
            or contract.response_reciprocal_indices
            != recipe.response_reciprocal_indices
            or contract.absolute_signal_threshold_authority_ref
            != "WindowThresholdSelection.curv_tau_sig"
            or contract.raw_bridge_noise_evidence_ref
            != "SourceReadoutBridgeAudit.curv_operator_error_max"
            or contract.raw_noise_absolute_threshold_authority_ref
            != "rulespace_v3.thresholds.BRIDGE_TOLERANCE"
            or contract.relative_gap_threshold_authority_ref
            != "rulespace_v3.thresholds.RAW_GAP_MIN"
        ):
            raise ValueError("DAG C12 contract differs from live recipe")
        contract_points = tuple(
            (
                item.reciprocal_index,
                struct.pack(">d", item.momentum),
                item.exact_nu_expression,
                item.nu_minimal_polynomial_coefficients,
                struct.pack(">d", item.nu_value),
            )
            for item in contract.incidence_points
        )
        preflight_points = tuple(
            (
                item.reciprocal_index,
                struct.pack(">d", item.momentum),
                item.exact_nu_expression,
                item.nu_minimal_polynomial_coefficients,
                struct.pack(">d", item.nu_value),
            )
            for item in certificate.point_wires
        )
        if contract_points != preflight_points:
            raise ValueError("DAG C12 cyclotomic points differ from live preflight")
        construction_rule_id = recipe.construction_rule_id
        construction_family_id = recipe.recipe_id
        preflight_actual_effect_digest = recipe.actual_effect_digest
        preflight_matched_effect_digest = (
            recipe.matched_ablated_effect_digest
        )
    response_template = _refrozen_response_template(
        candidate_v1,
        scenario_id,
        selector,
        contract,
        binding,
        construction_rule_id=construction_rule_id,
        construction_family_id=construction_family_id,
        preflight_actual_effect_digest=preflight_actual_effect_digest,
        preflight_matched_effect_digest=preflight_matched_effect_digest,
    )
    profile = build_candidate_v2_prediction_profile(scenario_id)
    provisional = CandidateV2ScenarioRefreeze(
        scenario_refreeze_schema_version=(
            PARENT_CANDIDATE_V2_SCENARIO_REFREEZE_SCHEMA_VERSION
        ),
        construction_state="PROVISIONAL_REFREEZE_RECORD_NO_AUTHORITY",
        control_case_id=application.control_case_id,
        scenario_id=scenario_id,
        preflight_binding_sha=binding.binding_sha,
        operation_dag=dag,
        proposed_selector_spec=selector,
        response_template=response_template,
        prediction_profile=profile,
        scenario_refreeze_sha="0" * 64,
    )
    return replace(
        provisional,
        scenario_refreeze_sha=canonical_sha(
            candidate_v2_scenario_refreeze_payload(provisional)
        ),
    )


@dataclass(frozen=True)
class ParentFreezeCandidateV2Manifest:
    """Non-authoritative review root; not accepted by Parent/permit issuers."""

    candidate_schema_version: str
    authority_state: Literal["PROVISIONAL_NOT_ISSUED"]
    based_on_issued_parent_freeze_sha: str
    based_on_candidate_v1_sha: str
    issuance_disposition: Literal[
        "NO_PARENT_OR_SIGNED_ERRATUM_ISSUED"
    ]
    preflight_bindings: tuple[CandidateConstructionPreflightBinding, ...]
    scenario_refreezes: tuple[CandidateV2ScenarioRefreeze, ...]
    candidate_sha: str

    def __post_init__(self) -> None:
        if self.candidate_schema_version != PARENT_CANDIDATE_V2_SCHEMA_VERSION:
            raise ValueError("candidate v2 schema is not frozen")
        if self.authority_state != PARENT_CANDIDATE_V2_AUTHORITY_STATE:
            raise ValueError("candidate v2 cannot claim authority")
        _sha(
            self.based_on_issued_parent_freeze_sha,
            "based_on_issued_parent_freeze_sha",
        )
        _sha(self.based_on_candidate_v1_sha, "based_on_candidate_v1_sha")
        if self.issuance_disposition != "NO_PARENT_OR_SIGNED_ERRATUM_ISSUED":
            raise ValueError("candidate v2 issuance disposition is not frozen")
        if (
            type(self.preflight_bindings) is not tuple
            or not all(
                type(item) is CandidateConstructionPreflightBinding
                for item in self.preflight_bindings
            )
        ):
            raise TypeError("preflight_bindings have the wrong strict type")
        if (
            type(self.scenario_refreezes) is not tuple
            or not all(
                type(item) is CandidateV2ScenarioRefreeze
                for item in self.scenario_refreezes
            )
        ):
            raise TypeError("scenario_refreezes have the wrong strict type")
        _sha(self.candidate_sha, "candidate_sha")


def parent_candidate_v2_manifest_payload(
    candidate: ParentFreezeCandidateV2Manifest,
) -> dict[str, object]:
    """Canonical body, excluding only its self hash."""

    _exact_record(candidate, ParentFreezeCandidateV2Manifest, "candidate v2")
    return {
        "candidate_schema_version": candidate.candidate_schema_version,
        "authority_state": candidate.authority_state,
        "based_on_issued_parent_freeze_sha": (
            candidate.based_on_issued_parent_freeze_sha
        ),
        "based_on_candidate_v1_sha": candidate.based_on_candidate_v1_sha,
        "issuance_disposition": candidate.issuance_disposition,
        "preflight_bindings": [
            {
                **candidate_construction_preflight_binding_payload(item),
                "binding_sha": item.binding_sha,
            }
            for item in candidate.preflight_bindings
        ],
        "scenario_refreezes": [
            {
                **candidate_v2_scenario_refreeze_payload(item),
                "scenario_refreeze_sha": item.scenario_refreeze_sha,
            }
            for item in candidate.scenario_refreezes
        ],
    }


def _verified_candidate_v1() -> ParentFreezeCandidateManifest:
    candidate = build_v3m0_parent_freeze_candidate()
    return verify_parent_freeze_candidate(candidate)


def _build_minimal_candidate_v2() -> ParentFreezeCandidateV2Manifest:
    candidate_v1 = _verified_candidate_v1()
    preflight_bindings = _build_live_preflight_bindings(candidate_v1)
    scenario_refreezes = tuple(
        _build_scenario_refreeze(candidate_v1, binding)
        for binding in preflight_bindings
    )
    provisional = ParentFreezeCandidateV2Manifest(
        candidate_schema_version=PARENT_CANDIDATE_V2_SCHEMA_VERSION,
        authority_state=PARENT_CANDIDATE_V2_AUTHORITY_STATE,
        based_on_issued_parent_freeze_sha=(
            candidate_v1.based_on_parent_freeze_sha
        ),
        based_on_candidate_v1_sha=candidate_v1.candidate_sha,
        issuance_disposition="NO_PARENT_OR_SIGNED_ERRATUM_ISSUED",
        preflight_bindings=preflight_bindings,
        scenario_refreezes=scenario_refreezes,
        candidate_sha="0" * 64,
    )
    return replace(
        provisional,
        candidate_sha=canonical_sha(
            parent_candidate_v2_manifest_payload(provisional)
        ),
    )


def build_v3m0_parent_freeze_candidate_v2() -> ParentFreezeCandidateV2Manifest:
    """Build the detached inert review root (never an authority capability)."""

    return verify_parent_freeze_candidate_v2(_build_minimal_candidate_v2())


def verify_parent_freeze_candidate_v2(
    candidate: ParentFreezeCandidateV2Manifest,
) -> ParentFreezeCandidateV2Manifest:
    """Replay the unique candidate roots and validate the exact review body."""

    _exact_record(candidate, ParentFreezeCandidateV2Manifest, "candidate v2")
    candidate.__post_init__()
    candidate_v1 = _verified_candidate_v1()
    if candidate.based_on_issued_parent_freeze_sha != (
        candidate_v1.based_on_parent_freeze_sha
    ):
        raise ValueError("candidate v2 is spliced to another issued Parent")
    if candidate.based_on_candidate_v1_sha != candidate_v1.candidate_sha:
        raise ValueError("candidate v2 is spliced to another candidate v1")
    for binding in candidate.preflight_bindings:
        _exact_record(
            binding,
            CandidateConstructionPreflightBinding,
            "construction preflight binding",
        )
        binding.__post_init__()
        if binding.binding_sha != canonical_sha(
            candidate_construction_preflight_binding_payload(binding)
        ):
            raise ValueError("preflight binding SHA does not match its body")
    binding_by_scenario = {
        item.scenario_id: item for item in candidate.preflight_bindings
    }
    expected_scenario_ids = (*INTERFERENCE_MODE_SCENARIO_IDS, C12_SCENARIO_ID)
    if tuple(binding_by_scenario) != expected_scenario_ids:
        raise ValueError("candidate v2 preflight bindings are not the five-case registry")
    if tuple(item.scenario_id for item in candidate.scenario_refreezes) != (
        expected_scenario_ids
    ):
        raise ValueError("candidate v2 refreezes are not the five-case registry")
    for refreeze in candidate.scenario_refreezes:
        _exact_record(
            refreeze,
            CandidateV2ScenarioRefreeze,
            "candidate v2 scenario refreeze",
        )
        refreeze.__post_init__()
        binding = binding_by_scenario.get(refreeze.scenario_id)
        if binding is None or refreeze.preflight_binding_sha != binding.binding_sha:
            raise ValueError("scenario refreeze is spliced to another binding")
        verify_candidate_scenario_dag(refreeze.operation_dag)
        contract = extract_candidate_scenario_contract(refreeze.operation_dag)
        verify_compiled_candidate_scenario_contract(
            refreeze.operation_dag,
            contract,
        )
        selector = refreeze.proposed_selector_spec
        _exact_record(selector, ScenarioBasisSelectorSpec, "proposed selector")
        selector.__post_init__()
        for field in (
            "source_selector",
            "readout_selector",
            "source_injection",
            "readout_coisometry",
        ):
            tensor = getattr(selector, field)
            _exact_record(tensor, FrozenComplexTensor, f"proposed selector {field}")
            verify_frozen_tensor(tensor)
        if selector.selector_sha != canonical_sha(
            scenario_basis_selector_spec_payload(selector)
        ):
            raise ValueError("proposed selector SHA does not match its body")
        if (
            selector.source_selector.tensor_sha
            != contract.proposed_source_selection.tensor_sha
            or selector.readout_selector.tensor_sha
            != contract.proposed_readout_selection.tensor_sha
        ):
            raise ValueError("scenario selector differs from DAG extraction")
        template = refreeze.response_template
        _exact_record(
            template,
            CandidateV2ResponseTemplate,
            "candidate v2 response template",
        )
        template.__post_init__()
        _exact_record(
            template.source_trial_vectors,
            FrozenComplexTensor,
            "response template source_trial_vectors",
        )
        verify_frozen_tensor(template.source_trial_vectors)
        if template.template_sha != canonical_sha(
            candidate_v2_response_template_payload(template)
        ):
            raise ValueError("response template SHA does not match its body")
        if (
            template.scenario_id != refreeze.scenario_id
            or template.selector_sha != selector.selector_sha
            or template.dag_sha != refreeze.operation_dag.dag_sha
            or template.compiled_contract_sha != contract.contract_sha
            or template.expected_actual_shell_rank
            != contract.expected_actual_shell_rank
            or template.expected_matched_shell_rank
            != contract.expected_matched_shell_rank
            or template.actual_program_sha != contract.actual_program_sha
            or template.matched_ablated_program_sha
            != contract.matched_ablated_program_sha
            or template.preflight_derivation_or_recipe_sha
            != binding.derivation_or_recipe_sha
            or template.incidence_family_id != contract.incidence_family_id
            or template.incidence_normalizer_formula_id
            != contract.incidence_normalizer_formula_id
            or template.incidence_application_stage
            != contract.incidence_application_stage
            or template.absolute_signal_threshold_authority_ref
            != contract.absolute_signal_threshold_authority_ref
            or template.raw_bridge_noise_evidence_ref
            != contract.raw_bridge_noise_evidence_ref
            or template.raw_noise_absolute_threshold_authority_ref
            != contract.raw_noise_absolute_threshold_authority_ref
            or template.relative_gap_threshold_authority_ref
            != contract.relative_gap_threshold_authority_ref
            or template.uses_global_fft_projection
            != contract.uses_global_fft_projection
            or template.uses_per_k_time_step_projector
            != contract.uses_per_k_time_step_projector
        ):
            raise ValueError("response template is spliced from scenario contract")
        if contract.response_torus_denominator is not None and (
            template.response_torus_denominators
            != (contract.response_torus_denominator,)
            or template.response_reciprocal_indices
            != contract.response_reciprocal_indices
        ):
            raise ValueError("C12 response grid is spliced from its contract")
        verify_candidate_v2_prediction_profile(refreeze.prediction_profile)
        if refreeze.prediction_profile.scenario_id != refreeze.scenario_id:
            raise ValueError("prediction profile is spliced to another scenario")
        if refreeze.scenario_refreeze_sha != canonical_sha(
            candidate_v2_scenario_refreeze_payload(refreeze)
        ):
            raise ValueError("scenario refreeze SHA does not match its body")
    if candidate.candidate_sha != canonical_sha(
        parent_candidate_v2_manifest_payload(candidate)
    ):
        raise ValueError("candidate v2 SHA does not match its complete body")
    if candidate != _build_minimal_candidate_v2():
        raise ValueError("candidate v2 differs from canonical live replay")
    return candidate


__all__ = [
    "PARENT_CANDIDATE_V2_AUTHORITY_STATE",
    "PARENT_CANDIDATE_V2_SCHEMA_VERSION",
    "PARENT_CANDIDATE_V2_BINDING_SCHEMA_VERSION",
    "PARENT_CANDIDATE_V2_PREDICTION_QUANTITY_SCHEMA_VERSION",
    "PARENT_CANDIDATE_V2_PREDICTION_PROFILE_SCHEMA_VERSION",
    "PARENT_CANDIDATE_V2_RESPONSE_TEMPLATE_SCHEMA_VERSION",
    "PARENT_CANDIDATE_V2_SCENARIO_REFREEZE_SCHEMA_VERSION",
    "CandidateConstructionPreflightBinding",
    "CandidateV2PredictionProfile",
    "CandidateV2PredictionQuantity",
    "CandidateV2ResponseTemplate",
    "CandidateV2ScenarioRefreeze",
    "ParentFreezeCandidateV2Manifest",
    "build_candidate_v2_prediction_profile",
    "build_v3m0_parent_freeze_candidate_v2",
    "candidate_construction_preflight_binding_payload",
    "candidate_v2_prediction_profile_payload",
    "candidate_v2_prediction_quantity_payload",
    "candidate_v2_response_template_payload",
    "candidate_v2_scenario_refreeze_payload",
    "parent_candidate_v2_manifest_payload",
    "verify_candidate_v2_prediction_profile",
    "verify_parent_freeze_candidate_v2",
]
