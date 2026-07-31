"""Exact, authority-neutral wire contracts for the current V3-M0 Parent-v2.

These records carry no issuance capability.  In particular, constructing or
re-signing one of them never promotes a provisional candidate.  The sole live
issuer lives in :mod:`rulespace_v3.parent_authority` and closes over the one
repository-reviewed body.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, fields as dataclass_fields
from pathlib import PurePosixPath
from typing import Literal, Optional

from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    frozen_tensor_payload,
    verify_frozen_tensor,
)
from .parent_candidate_v2 import (
    ParentFreezeCandidateV2Manifest,
    parent_candidate_v2_manifest_payload,
)
from .parent_freeze import (
    ApplicationScenarioExecutionSpec,
    ParentFreezeCandidateManifest,
    ParentFreezeManifest,
    ScenarioBasisSelectorSpec,
    application_scenario_execution_spec_payload,
    parent_freeze_candidate_manifest_payload,
    parent_freeze_manifest_payload,
    scenario_basis_selector_spec_payload,
)


SIGNED_SOURCE_REF_SCHEMA_VERSION = "v3m0.signed-source-ref.v1"
CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION = (
    "v3m0.current-scenario-response-contract.v2"
)
CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION = "v3m0.current-scenario-authority.v2"
CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION = "v3m0.current-application-authority.v2"
PARENT_FREEZE_V2_SCHEMA_VERSION = "v3m0.parent-freeze.v2"
PARENT_V2_READINESS_AUDIT_SCHEMA_VERSION = "v3m0.parent-v2-readiness-audit.v1"

_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


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


def _git_sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_GIT_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase full Git SHA")
    return result


def _relative_path(value: object, field: str) -> str:
    result = _text(value, field)
    path = PurePosixPath(result)
    if path.is_absolute() or result != path.as_posix() or ".." in path.parts:
        raise ValueError(f"{field} must be a canonical repository-relative path")
    return result


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    observed = frozenset(vars(value))
    if observed != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _string_tuple(
    value: object,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(value) is not tuple or not all(
        type(item) is str and bool(item.strip()) for item in value
    ):
        raise TypeError(f"{field} must be an exact tuple of non-empty strings")
    if not allow_empty and not value:
        raise ValueError(f"{field} must not be empty")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} must be unique")
    return value


@dataclass(frozen=True)
class SignedSourceRefV1:
    """Raw signed erratum bytes and the reviewed preparation commit."""

    source_ref_schema_version: str
    source_role: Literal["SIGNED_INCREMENTAL_ERRATUM"]
    relative_path: str
    raw_sha256: str
    preparation_commit_sha: str
    source_ref_sha: str

    def __post_init__(self) -> None:
        if self.source_ref_schema_version != SIGNED_SOURCE_REF_SCHEMA_VERSION:
            raise ValueError("signed source-ref schema drifted")
        if self.source_role != "SIGNED_INCREMENTAL_ERRATUM":
            raise ValueError("signed source-ref role is not frozen")
        _relative_path(self.relative_path, "relative_path")
        _sha(self.raw_sha256, "raw_sha256")
        _git_sha(self.preparation_commit_sha, "preparation_commit_sha")
        _sha(self.source_ref_sha, "source_ref_sha")


def signed_source_ref_v1_payload(reference: SignedSourceRefV1) -> dict[str, object]:
    _exact_record(reference, SignedSourceRefV1, "signed source ref")
    return {
        "source_ref_schema_version": reference.source_ref_schema_version,
        "source_role": reference.source_role,
        "relative_path": reference.relative_path,
        "raw_sha256": reference.raw_sha256,
        "preparation_commit_sha": reference.preparation_commit_sha,
    }


@dataclass(frozen=True)
class CurrentScenarioResponseContractV2:
    """Complete current response construction for one success scenario."""

    response_contract_schema_version: str
    contract_state: Literal["CURRENT_REVIEWED_RESPONSE_CONTRACT"]
    scenario_id: str
    selector_sha: str
    selector_spec: ScenarioBasisSelectorSpec
    source_trial_vectors: FrozenComplexTensor
    response_torus_denominators: tuple[int, ...]
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    operation_dag_sha: str
    compiled_contract_sha: str
    construction_rule_id: str
    construction_family_id: str
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    actual_step_count: int
    matched_ablated_step_count: int
    actual_program_sha: str
    matched_ablated_program_sha: str
    preflight_derivation_or_recipe_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    response_template_sha: str
    prediction_profile_sha: str
    uses_global_fft_projection: Literal[False]
    uses_per_k_time_step_projector: Literal[False]
    response_contract_sha: str

    def __post_init__(self) -> None:
        if self.response_contract_schema_version != (
            CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION
        ):
            raise ValueError("current response-contract schema drifted")
        if self.contract_state != "CURRENT_REVIEWED_RESPONSE_CONTRACT":
            raise ValueError("current response contract claimed another state")
        for field in (
            "scenario_id",
            "construction_rule_id",
            "construction_family_id",
        ):
            _text(getattr(self, field), field)
        for field in (
            "operation_dag_sha",
            "compiled_contract_sha",
            "actual_program_sha",
            "matched_ablated_program_sha",
            "preflight_derivation_or_recipe_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "response_template_sha",
            "prediction_profile_sha",
            "response_contract_sha",
        ):
            _sha(getattr(self, field), field)
        _sha(self.selector_sha, "selector_sha")
        _exact_record(
            self.selector_spec,
            ScenarioBasisSelectorSpec,
            "selector_spec",
        )
        self.selector_spec.__post_init__()
        if self.selector_sha != self.selector_spec.selector_sha:
            raise ValueError("selector SHA differs from its exact selector body")
        if self.selector_sha != canonical_sha(
            scenario_basis_selector_spec_payload(self.selector_spec)
        ):
            raise ValueError("selector SHA does not match its exact body")
        for field in (
            "source_selector",
            "readout_selector",
            "source_injection",
            "readout_coisometry",
        ):
            tensor = getattr(self.selector_spec, field)
            _exact_record(tensor, FrozenComplexTensor, f"selector_spec.{field}")
            verify_frozen_tensor(tensor)
        _exact_record(
            self.source_trial_vectors,
            FrozenComplexTensor,
            "source_trial_vectors",
        )
        verify_frozen_tensor(self.source_trial_vectors)
        if len(self.selector_spec.source_injection.shape) != 2:
            raise ValueError("source injection must be a matrix")
        source_columns = self.selector_spec.source_injection.shape[1]
        if self.source_trial_vectors.shape != (source_columns, source_columns):
            raise ValueError("source trials do not span the selected source columns")
        if (
            type(self.response_torus_denominators) is not tuple
            or not self.response_torus_denominators
            or not all(
                type(item) is int and item > 0
                for item in self.response_torus_denominators
            )
        ):
            raise TypeError("response_torus_denominators are not positive ints")
        for field in (
            "response_reciprocal_indices",
            "source_readout_bridge_reciprocal_indices",
        ):
            value = getattr(self, field)
            if (
                type(value) is not tuple
                or not value
                or not all(
                    type(item) is tuple
                    and item
                    and all(type(index) is int for index in item)
                    for item in value
                )
            ):
                raise TypeError(f"{field} is not an exact integer grid")
        if (
            type(self.source_readout_bridge_steps) is not tuple
            or not self.source_readout_bridge_steps
            or not all(
                type(item) is int and item > 0
                for item in self.source_readout_bridge_steps
            )
        ):
            raise TypeError("source_readout_bridge_steps are not positive ints")
        if (
            type(self.reference_reciprocal_index) is not tuple
            or not self.reference_reciprocal_index
            or not all(type(item) is int for item in self.reference_reciprocal_index)
        ):
            raise TypeError("reference_reciprocal_index is not an integer tuple")
        if (
            type(self.preregistered_phase_bands) is not tuple
            or not self.preregistered_phase_bands
            or not all(
                type(item) is tuple
                and len(item) == 2
                and all(type(value) is float and math.isfinite(value) for value in item)
                and item[0] < item[1]
                for item in self.preregistered_phase_bands
            )
        ):
            raise TypeError("preregistered_phase_bands are not ordered fp64 pairs")
        if (
            type(self.expected_actual_shell_rank) is not int
            or self.expected_actual_shell_rank <= 0
        ):
            raise ValueError("expected_actual_shell_rank must be positive")
        if (
            type(self.expected_matched_shell_rank) is not int
            or self.expected_matched_shell_rank < 0
        ):
            raise ValueError("expected_matched_shell_rank must be non-negative")
        if type(self.actual_step_count) is not int or self.actual_step_count <= 0:
            raise ValueError("actual_step_count must be positive")
        if (
            type(self.matched_ablated_step_count) is not int
            or self.matched_ablated_step_count < 0
        ):
            raise ValueError("matched_ablated_step_count must be non-negative")
        if self.uses_global_fft_projection is not False:
            raise ValueError("current response cannot use global FFT projection")
        if self.uses_per_k_time_step_projector is not False:
            raise ValueError("current response cannot use a per-k timestep projector")


def current_scenario_response_contract_v2_payload(
    contract: CurrentScenarioResponseContractV2,
) -> dict[str, object]:
    _exact_record(
        contract,
        CurrentScenarioResponseContractV2,
        "current scenario response contract",
    )
    return {
        "response_contract_schema_version": contract.response_contract_schema_version,
        "contract_state": contract.contract_state,
        "scenario_id": contract.scenario_id,
        "selector_sha": contract.selector_sha,
        "selector_spec": {
            **scenario_basis_selector_spec_payload(contract.selector_spec),
            "selector_sha": contract.selector_spec.selector_sha,
        },
        "source_trial_vectors": {
            **frozen_tensor_payload(contract.source_trial_vectors),
            "tensor_sha": contract.source_trial_vectors.tensor_sha,
        },
        "response_torus_denominators": list(contract.response_torus_denominators),
        "response_reciprocal_indices": [
            list(item) for item in contract.response_reciprocal_indices
        ],
        "source_readout_bridge_reciprocal_indices": [
            list(item) for item in contract.source_readout_bridge_reciprocal_indices
        ],
        "source_readout_bridge_steps": list(contract.source_readout_bridge_steps),
        "reference_reciprocal_index": list(contract.reference_reciprocal_index),
        "preregistered_phase_bands": [
            list(item) for item in contract.preregistered_phase_bands
        ],
        "operation_dag_sha": contract.operation_dag_sha,
        "compiled_contract_sha": contract.compiled_contract_sha,
        "construction_rule_id": contract.construction_rule_id,
        "construction_family_id": contract.construction_family_id,
        "expected_actual_shell_rank": contract.expected_actual_shell_rank,
        "expected_matched_shell_rank": contract.expected_matched_shell_rank,
        "actual_step_count": contract.actual_step_count,
        "matched_ablated_step_count": contract.matched_ablated_step_count,
        "actual_program_sha": contract.actual_program_sha,
        "matched_ablated_program_sha": contract.matched_ablated_program_sha,
        "preflight_derivation_or_recipe_sha": (
            contract.preflight_derivation_or_recipe_sha
        ),
        "actual_effect_digest": contract.actual_effect_digest,
        "matched_ablated_effect_digest": contract.matched_ablated_effect_digest,
        "response_template_sha": contract.response_template_sha,
        "prediction_profile_sha": contract.prediction_profile_sha,
        "uses_global_fft_projection": contract.uses_global_fft_projection,
        "uses_per_k_time_step_projector": (contract.uses_per_k_time_step_projector),
    }


ScenarioSourceDisposition = Literal[
    "CANDIDATE_V2_REVIEWED_MODIFIED",
    "CANDIDATE_V1_REVIEWED_UNCHANGED",
    "PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE",
    "PARENT_V1_C04_CLOSED_RECIPE",
]


@dataclass(frozen=True)
class CurrentScenarioAuthorityV2:
    scenario_authority_schema_version: str
    authority_state: Literal["CURRENT_REVIEWED_SCENARIO"]
    control_case_id: str
    application_instance_id: str
    based_on_application_spec_sha: str
    scenario_id: str
    scenario_execution_spec: ApplicationScenarioExecutionSpec
    source_disposition: ScenarioSourceDisposition
    source_candidate_v1_scenario_sha: str
    source_candidate_v2_refreeze_sha: Optional[str]
    response_contract: CurrentScenarioResponseContractV2
    scenario_authority_sha: str

    def __post_init__(self) -> None:
        if self.scenario_authority_schema_version != (
            CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION
        ):
            raise ValueError("current scenario-authority schema drifted")
        if self.authority_state != "CURRENT_REVIEWED_SCENARIO":
            raise ValueError("current scenario authority state drifted")
        for field in (
            "control_case_id",
            "application_instance_id",
            "scenario_id",
        ):
            _text(getattr(self, field), field)
        _sha(self.based_on_application_spec_sha, "based_on_application_spec_sha")
        _exact_record(
            self.scenario_execution_spec,
            ApplicationScenarioExecutionSpec,
            "scenario_execution_spec",
        )
        if self.scenario_execution_spec.scenario_id != self.scenario_id:
            raise ValueError("scenario ID differs from execution spec")
        if self.scenario_execution_spec.execution_lane != "BLOCK_SUCCESS":
            raise ValueError("current scenario authority is not BLOCK_SUCCESS")
        if self.source_disposition not in (
            "CANDIDATE_V2_REVIEWED_MODIFIED",
            "CANDIDATE_V1_REVIEWED_UNCHANGED",
            "PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE",
            "PARENT_V1_C04_CLOSED_RECIPE",
        ):
            raise ValueError("scenario source disposition is not frozen")
        _sha(
            self.source_candidate_v1_scenario_sha,
            "source_candidate_v1_scenario_sha",
        )
        if self.source_disposition == "CANDIDATE_V2_REVIEWED_MODIFIED":
            _sha(
                self.source_candidate_v2_refreeze_sha,
                "source_candidate_v2_refreeze_sha",
            )
        elif self.source_candidate_v2_refreeze_sha is not None:
            raise ValueError("unchanged scenario carries a candidate-v2 refreeze")
        _exact_record(
            self.response_contract,
            CurrentScenarioResponseContractV2,
            "response_contract",
        )
        if self.response_contract.scenario_id != self.scenario_id:
            raise ValueError("response contract is spliced to another scenario")
        _sha(self.scenario_authority_sha, "scenario_authority_sha")


def current_scenario_authority_v2_payload(
    authority: CurrentScenarioAuthorityV2,
) -> dict[str, object]:
    _exact_record(
        authority,
        CurrentScenarioAuthorityV2,
        "current scenario authority",
    )
    return {
        "scenario_authority_schema_version": (
            authority.scenario_authority_schema_version
        ),
        "authority_state": authority.authority_state,
        "control_case_id": authority.control_case_id,
        "application_instance_id": authority.application_instance_id,
        "based_on_application_spec_sha": authority.based_on_application_spec_sha,
        "scenario_id": authority.scenario_id,
        "scenario_execution_spec": {
            **application_scenario_execution_spec_payload(
                authority.scenario_execution_spec
            ),
            "scenario_sha": authority.scenario_execution_spec.scenario_sha,
        },
        "source_disposition": authority.source_disposition,
        "source_candidate_v1_scenario_sha": (
            authority.source_candidate_v1_scenario_sha
        ),
        "source_candidate_v2_refreeze_sha": (
            authority.source_candidate_v2_refreeze_sha
        ),
        "response_contract": {
            **current_scenario_response_contract_v2_payload(
                authority.response_contract
            ),
            "response_contract_sha": authority.response_contract.response_contract_sha,
        },
    }


@dataclass(frozen=True)
class CurrentApplicationAuthorityV2:
    application_authority_schema_version: str
    authority_state: Literal["CURRENT_REVIEWED_APPLICATION"]
    control_case_id: str
    application_instance_id: str
    based_on_application_spec_sha: str
    source_candidate_v1_application_sha: str
    complete_scenario_execution_specs: tuple[
        ApplicationScenarioExecutionSpec, ...
    ]
    scenario_authorities: tuple[CurrentScenarioAuthorityV2, ...]
    application_authority_sha: str

    def __post_init__(self) -> None:
        if self.application_authority_schema_version != (
            CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION
        ):
            raise ValueError("current application-authority schema drifted")
        if self.authority_state != "CURRENT_REVIEWED_APPLICATION":
            raise ValueError("current application authority state drifted")
        for field in ("control_case_id", "application_instance_id"):
            _text(getattr(self, field), field)
        _sha(self.based_on_application_spec_sha, "based_on_application_spec_sha")
        _sha(
            self.source_candidate_v1_application_sha,
            "source_candidate_v1_application_sha",
        )
        if (
            type(self.complete_scenario_execution_specs) is not tuple
            or not self.complete_scenario_execution_specs
            or not all(
                type(item) is ApplicationScenarioExecutionSpec
                for item in self.complete_scenario_execution_specs
            )
        ):
            raise TypeError(
                "complete_scenario_execution_specs must be a non-empty "
                "exact tuple"
            )
        complete_ids: list[str] = []
        for index, spec in enumerate(self.complete_scenario_execution_specs):
            _exact_record(
                spec,
                ApplicationScenarioExecutionSpec,
                f"complete scenario execution spec[{index}]",
            )
            spec.__post_init__()
            if spec.scenario_sha != canonical_sha(
                application_scenario_execution_spec_payload(spec)
            ):
                raise ValueError("complete scenario execution SHA drifted")
            if not spec.scenario_id.startswith(self.application_instance_id + "."):
                raise ValueError(
                    "complete scenario execution spec is outside its application"
                )
            complete_ids.append(spec.scenario_id)
        if len(complete_ids) != len(set(complete_ids)):
            raise ValueError("complete scenario execution specs contain duplicate IDs")
        if type(self.scenario_authorities) is not tuple:
            raise TypeError("scenario_authorities must be an exact tuple")
        if not all(
            type(item) is CurrentScenarioAuthorityV2
            for item in self.scenario_authorities
        ):
            raise TypeError("scenario_authorities have the wrong strict type")
        scenario_ids = tuple(item.scenario_id for item in self.scenario_authorities)
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("scenario_authorities contain duplicate IDs")
        for item in self.scenario_authorities:
            if (
                item.control_case_id != self.control_case_id
                or item.application_instance_id != self.application_instance_id
                or item.based_on_application_spec_sha
                != self.based_on_application_spec_sha
            ):
                raise ValueError("scenario authority is spliced across applications")
        expected_success_specs = tuple(
            item
            for item in self.complete_scenario_execution_specs
            if item.execution_lane == "BLOCK_SUCCESS"
        )
        if tuple(
            item.scenario_execution_spec for item in self.scenario_authorities
        ) != expected_success_specs:
            raise ValueError(
                "scenario authorities are not the exact ordered BLOCK_SUCCESS subset"
            )
        _sha(self.application_authority_sha, "application_authority_sha")


def current_application_authority_v2_payload(
    authority: CurrentApplicationAuthorityV2,
) -> dict[str, object]:
    _exact_record(
        authority,
        CurrentApplicationAuthorityV2,
        "current application authority",
    )
    return {
        "application_authority_schema_version": (
            authority.application_authority_schema_version
        ),
        "authority_state": authority.authority_state,
        "control_case_id": authority.control_case_id,
        "application_instance_id": authority.application_instance_id,
        "based_on_application_spec_sha": authority.based_on_application_spec_sha,
        "source_candidate_v1_application_sha": (
            authority.source_candidate_v1_application_sha
        ),
        "complete_scenario_execution_specs": [
            {
                **application_scenario_execution_spec_payload(item),
                "scenario_sha": item.scenario_sha,
            }
            for item in authority.complete_scenario_execution_specs
        ],
        "scenario_authorities": [
            {
                **current_scenario_authority_v2_payload(item),
                "scenario_authority_sha": item.scenario_authority_sha,
            }
            for item in authority.scenario_authorities
        ],
    }


@dataclass(frozen=True)
class ParentFreezeV2Manifest:
    parent_freeze_schema_version: str
    authority_state: Literal["CURRENT_PARENT_V2_ISSUED"]
    program_id: Literal["projective-rule-space-v3m0-v2"]
    historical_parent_v1: ParentFreezeManifest
    reviewed_candidate_v1: ParentFreezeCandidateManifest
    reviewed_candidate_v2: ParentFreezeCandidateV2Manifest
    signed_incremental_erratum: SignedSourceRefV1
    current_application_authorities: tuple[CurrentApplicationAuthorityV2, ...]
    block_success_scenario_ids: tuple[str, ...]
    source_closure: tuple[tuple[str, str], ...]
    parent_freeze_v2_sha: str

    def __post_init__(self) -> None:
        if self.parent_freeze_schema_version != PARENT_FREEZE_V2_SCHEMA_VERSION:
            raise ValueError("Parent-v2 schema drifted")
        if self.authority_state != "CURRENT_PARENT_V2_ISSUED":
            raise ValueError("Parent-v2 authority state drifted")
        if self.program_id != "projective-rule-space-v3m0-v2":
            raise ValueError("Parent-v2 program ID drifted")
        _exact_record(
            self.historical_parent_v1,
            ParentFreezeManifest,
            "historical_parent_v1",
        )
        _exact_record(
            self.reviewed_candidate_v1,
            ParentFreezeCandidateManifest,
            "reviewed_candidate_v1",
        )
        _exact_record(
            self.reviewed_candidate_v2,
            ParentFreezeCandidateV2Manifest,
            "reviewed_candidate_v2",
        )
        _exact_record(
            self.signed_incremental_erratum,
            SignedSourceRefV1,
            "signed_incremental_erratum",
        )
        if (
            type(self.current_application_authorities) is not tuple
            or not self.current_application_authorities
            or not all(
                type(item) is CurrentApplicationAuthorityV2
                for item in self.current_application_authorities
            )
        ):
            raise TypeError("current_application_authorities have the wrong type")
        control_ids = tuple(
            item.control_case_id for item in self.current_application_authorities
        )
        if len(control_ids) != len(set(control_ids)):
            raise ValueError("current applications contain duplicate control IDs")
        _string_tuple(
            self.block_success_scenario_ids,
            "block_success_scenario_ids",
        )
        if type(self.source_closure) is not tuple or not self.source_closure:
            raise TypeError("source_closure must be a non-empty tuple")
        paths: list[str] = []
        for index, entry in enumerate(self.source_closure):
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError(f"source_closure[{index}] must be a path/SHA pair")
            paths.append(_relative_path(entry[0], f"source_closure[{index}][0]"))
            _sha(entry[1], f"source_closure[{index}][1]")
        if tuple(paths) != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ValueError("source_closure must be unique canonical path order")
        _sha(self.parent_freeze_v2_sha, "parent_freeze_v2_sha")


def parent_freeze_v2_manifest_payload(
    manifest: ParentFreezeV2Manifest,
) -> dict[str, object]:
    _exact_record(manifest, ParentFreezeV2Manifest, "Parent-v2 manifest")
    return {
        "parent_freeze_schema_version": manifest.parent_freeze_schema_version,
        "authority_state": manifest.authority_state,
        "program_id": manifest.program_id,
        "historical_parent_v1": {
            **parent_freeze_manifest_payload(manifest.historical_parent_v1),
            "parent_freeze_sha": manifest.historical_parent_v1.parent_freeze_sha,
        },
        "reviewed_candidate_v1": {
            **parent_freeze_candidate_manifest_payload(manifest.reviewed_candidate_v1),
            "candidate_sha": manifest.reviewed_candidate_v1.candidate_sha,
        },
        "reviewed_candidate_v2": {
            **parent_candidate_v2_manifest_payload(manifest.reviewed_candidate_v2),
            "candidate_sha": manifest.reviewed_candidate_v2.candidate_sha,
        },
        "signed_incremental_erratum": {
            **signed_source_ref_v1_payload(manifest.signed_incremental_erratum),
            "source_ref_sha": manifest.signed_incremental_erratum.source_ref_sha,
        },
        "current_application_authorities": [
            {
                **current_application_authority_v2_payload(item),
                "application_authority_sha": item.application_authority_sha,
            }
            for item in manifest.current_application_authorities
        ],
        "block_success_scenario_ids": list(manifest.block_success_scenario_ids),
        "source_closure": [list(item) for item in manifest.source_closure],
    }


@dataclass(frozen=True)
class ParentV2ReadinessAudit:
    audit_schema_version: str
    finalization_inputs_state: Literal[
        "NOT_INJECTED",
        "DOCUMENT_NOT_SIGNED",
        "READY",
    ]
    expected_block_success_scenario_ids: tuple[str, ...]
    promoted_modified_scenario_ids: tuple[str, ...]
    unresolved_unchanged_scenario_ids: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    can_issue: bool
    audit_sha: str

    def __post_init__(self) -> None:
        if self.audit_schema_version != PARENT_V2_READINESS_AUDIT_SCHEMA_VERSION:
            raise ValueError("Parent-v2 readiness schema drifted")
        if self.finalization_inputs_state not in (
            "NOT_INJECTED",
            "DOCUMENT_NOT_SIGNED",
            "READY",
        ):
            raise ValueError("Parent-v2 finalization input state is unknown")
        for field in (
            "expected_block_success_scenario_ids",
            "promoted_modified_scenario_ids",
            "unresolved_unchanged_scenario_ids",
        ):
            _string_tuple(getattr(self, field), field, allow_empty=True)
        if type(self.blocking_reasons) is not tuple or not all(
            type(item) is str and bool(item.strip()) for item in self.blocking_reasons
        ):
            raise TypeError("blocking_reasons must be an exact text tuple")
        if type(self.can_issue) is not bool:
            raise TypeError("can_issue must be an exact bool")
        if self.can_issue != (not self.blocking_reasons):
            raise ValueError("can_issue contradicts blocking reasons")
        _sha(self.audit_sha, "audit_sha")


def parent_v2_readiness_audit_payload(
    audit: ParentV2ReadinessAudit,
) -> dict[str, object]:
    _exact_record(audit, ParentV2ReadinessAudit, "Parent-v2 readiness audit")
    return {
        "audit_schema_version": audit.audit_schema_version,
        "finalization_inputs_state": audit.finalization_inputs_state,
        "expected_block_success_scenario_ids": list(
            audit.expected_block_success_scenario_ids
        ),
        "promoted_modified_scenario_ids": list(audit.promoted_modified_scenario_ids),
        "unresolved_unchanged_scenario_ids": list(
            audit.unresolved_unchanged_scenario_ids
        ),
        "blocking_reasons": list(audit.blocking_reasons),
        "can_issue": audit.can_issue,
    }


def verify_parent_v2_readiness_audit(
    audit: ParentV2ReadinessAudit,
) -> ParentV2ReadinessAudit:
    _exact_record(audit, ParentV2ReadinessAudit, "Parent-v2 readiness audit")
    audit.__post_init__()
    if audit.audit_sha != canonical_sha(parent_v2_readiness_audit_payload(audit)):
        raise ValueError("Parent-v2 readiness audit SHA does not match its body")
    return audit


__all__ = [
    "CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION",
    "CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION",
    "CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION",
    "PARENT_FREEZE_V2_SCHEMA_VERSION",
    "PARENT_V2_READINESS_AUDIT_SCHEMA_VERSION",
    "SIGNED_SOURCE_REF_SCHEMA_VERSION",
    "CurrentApplicationAuthorityV2",
    "CurrentScenarioAuthorityV2",
    "CurrentScenarioResponseContractV2",
    "ParentFreezeV2Manifest",
    "ParentV2ReadinessAudit",
    "SignedSourceRefV1",
    "current_application_authority_v2_payload",
    "current_scenario_authority_v2_payload",
    "current_scenario_response_contract_v2_payload",
    "parent_freeze_v2_manifest_payload",
    "parent_v2_readiness_audit_payload",
    "signed_source_ref_v1_payload",
    "verify_parent_v2_readiness_audit",
]
