"""Closed construction and readiness audit for the current Parent-v2.

This module has no public promotion or hydration API.  It mechanically replays
the independently reviewed candidate-v2 scenarios plus the four unchanged
Parent-v1 success lanes, inventories every historical ``BLOCK_SUCCESS``
scenario, and refuses to build a Parent until signed-source inputs are closed.
The live identity facade is isolated in :mod:`parent_authority`.
"""

from __future__ import annotations

import hashlib
import math
import pickle
import re
import struct
import subprocess
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

from .ablation import matched_ablation, verify_ablation_pair
from .calibration_authority import (
    _verify_c04_canonical_angle_recipe,
    build_c04_canonical_angle_recipe,
    c04_canonical_angle_recipe_symbol,
    c04_local_shear_step_payload,
)
from .candidate_scenario_dag import extract_candidate_scenario_contract
from .controls import (
    build_direct_sum_control,
    build_full_control,
    build_zero_control,
)
from .evidence import canonical_sha
from .factory import (
    PrimitiveInterface,
    PrimitiveOperatorWire,
    basis_manifest_array,
    build_basis_manifest,
    build_calibration_seed,
    freeze_complex_tensor,
    freeze_synthetic_target,
    measure_calibration_holdout,
    primitive_payload,
    primitive_sha,
)
from .parent_candidate_v2 import (
    ParentFreezeCandidateV2Manifest,
    build_v3m0_parent_freeze_candidate_v2,
    verify_parent_freeze_candidate_v2,
)
from .parent_freeze import (
    ParentFreezeCandidateApplication,
    ParentFreezeCandidateManifest,
    ParentFreezeCandidateScenario,
    ParentFreezeManifest,
    ScenarioBasisSelectorSpec,
    application_scenario_execution_spec_payload,
    build_v3m0_parent_freeze_candidate,
    issue_v3m0_parent_freeze,
    scenario_basis_selector_spec_payload,
    synthetic_control_application_spec_payload,
    verify_parent_freeze_candidate,
)
from .parent_v2_contracts import (
    CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION,
    CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION,
    CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION,
    PARENT_FREEZE_V2_SCHEMA_VERSION,
    PARENT_V2_READINESS_AUDIT_SCHEMA_VERSION,
    SIGNED_SOURCE_REF_SCHEMA_VERSION,
    CurrentApplicationAuthorityV2,
    CurrentScenarioAuthorityV2,
    CurrentScenarioResponseContractV2,
    ParentFreezeV2Manifest,
    ParentV2ReadinessAudit,
    SignedSourceRefV1,
    current_application_authority_v2_payload,
    current_scenario_authority_v2_payload,
    current_scenario_response_contract_v2_payload,
    parent_freeze_v2_manifest_payload,
    parent_v2_readiness_audit_payload,
    signed_source_ref_v1_payload,
    verify_parent_v2_readiness_audit,
)
from .registry import build_closed_control_registry


PARENT_V2_SIGNED_ERRATUM_SOURCE_PATH = (
    "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md"
)

# Phase-P is a non-authoritative preparation commit.  D and the final reviewed
# candidate root are intentionally absent until the atomic signing tree exists.
PARENT_V2_PREPARATION_COMMIT_SHA: Optional[str] = (
    "93cc836d8dfeac49f8f5d60b41c5f5bdfe9d077d"
)
PARENT_V2_SIGNED_ERRATUM_RAW_SHA256: Optional[str] = None
PARENT_V2_REVIEWED_CANDIDATE_V2_SHA256: Optional[str] = None

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_SOURCE_CLOSURE_PATHS = (
    "rulespace_v3/ablation.py",
    "rulespace_v3/application_recipes.py",
    "rulespace_v3/c05_projector_recipe.py",
    "rulespace_v3/c12_incidence_preflight.py",
    "rulespace_v3/calibration_authority.py",
    "rulespace_v3/candidate_scenario_dag.py",
    "rulespace_v3/controls.py",
    "rulespace_v3/evidence.py",
    "rulespace_v3/factory.py",
    "rulespace_v3/geometry.py",
    "rulespace_v3/geometry_application_recipes.py",
    "rulespace_v3/interference_mode_preflight.py",
    "rulespace_v3/parent_candidate_v2.py",
    "rulespace_v3/parent_freeze.py",
    "rulespace_v3/parent_v2_contracts.py",
    "rulespace_v3/registry.py",
    "rulespace_v3/response.py",
    "rulespace_v3/thresholds.py",
    "rulespace_v3/trace.py",
)
_PREPARATION_REQUIRED_PATHS = (
    PARENT_V2_SIGNED_ERRATUM_SOURCE_PATH,
    "rulespace_v3/candidate_scenario_dag.py",
    "rulespace_v3/parent_candidate_v2.py",
    "rulespace_v3/parent_v2_contracts.py",
    "rulespace_v3/parent_freeze_v2.py",
    "rulespace_v3/parent_authority.py",
    "tests/test_v3m0_candidate_scenario_dag.py",
    "tests/test_v3m0_parent_candidate_v2.py",
    "tests/test_v3m0_parent_freeze_v2.py",
)


class ParentV2IssuanceBlocked(RuntimeError):
    """Structured scientific/authority gate; never a partial Parent."""

    def __init__(self, reasons: tuple[str, ...]) -> None:
        if (
            type(reasons) is not tuple
            or not reasons
            or not all(type(item) is str and bool(item.strip()) for item in reasons)
        ):
            raise TypeError("issuance-block reasons must be a non-empty text tuple")
        self.reasons = reasons
        super().__init__("Parent-v2 issuance blocked: " + " | ".join(reasons))


def _exact_record(value: object, record_type: type, field: str) -> None:
    from dataclasses import fields as dataclass_fields

    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    observed = frozenset(vars(value))
    if expected != observed:
        raise ValueError(f"{field} contains unknown or missing fields")


@lru_cache(maxsize=1)
def _live_candidate_v1_bytes() -> bytes:
    candidate = build_v3m0_parent_freeze_candidate()
    return pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL)


def _live_candidate_v1() -> ParentFreezeCandidateManifest:
    candidate = pickle.loads(_live_candidate_v1_bytes())
    return verify_parent_freeze_candidate(candidate)


@lru_cache(maxsize=1)
def _live_candidate_v2_bytes() -> bytes:
    candidate = build_v3m0_parent_freeze_candidate_v2()
    return pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL)


def _live_candidate_v2() -> ParentFreezeCandidateV2Manifest:
    candidate = pickle.loads(_live_candidate_v2_bytes())
    return verify_parent_freeze_candidate_v2(candidate)


def _candidate_v1_indices(
    candidate: ParentFreezeCandidateManifest,
) -> tuple[
    dict[str, ParentFreezeCandidateApplication],
    dict[str, tuple[ParentFreezeCandidateApplication, ParentFreezeCandidateScenario]],
]:
    applications: dict[str, ParentFreezeCandidateApplication] = {}
    scenarios: dict[
        str,
        tuple[ParentFreezeCandidateApplication, ParentFreezeCandidateScenario],
    ] = {}
    for application in candidate.application_candidates:
        if application.control_case_id in applications:
            raise ValueError("candidate v1 contains duplicate applications")
        applications[application.control_case_id] = application
        for scenario in application.scenario_candidates:
            scenario_id = scenario.scenario_execution_spec.scenario_id
            if scenario_id in scenarios:
                raise ValueError("candidate v1 contains duplicate scenarios")
            scenarios[scenario_id] = (application, scenario)
    return applications, scenarios


def expected_block_success_scenario_ids() -> tuple[str, ...]:
    """Replay the reviewed v1 registry and enumerate all success lanes."""

    candidate = _live_candidate_v1()
    result = tuple(
        scenario.scenario_execution_spec.scenario_id
        for application in candidate.application_candidates
        for scenario in application.scenario_candidates
        if scenario.scenario_execution_spec.execution_lane == "BLOCK_SUCCESS"
    )
    if len(result) != 23 or len(result) != len(set(result)):
        raise ValueError("historical BLOCK_SUCCESS registry is not the reviewed 23")
    return result


def _build_response_contract_from_refreeze(
    refreeze,
) -> CurrentScenarioResponseContractV2:
    template = refreeze.response_template
    compiled = extract_candidate_scenario_contract(refreeze.operation_dag)
    if (
        template.scenario_id != refreeze.scenario_id
        or template.dag_sha != refreeze.operation_dag.dag_sha
        or template.compiled_contract_sha != compiled.contract_sha
    ):
        raise ValueError("candidate-v2 response template is spliced from its DAG")
    provisional = CurrentScenarioResponseContractV2(
        response_contract_schema_version=(
            CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION
        ),
        contract_state="CURRENT_REVIEWED_RESPONSE_CONTRACT",
        scenario_id=refreeze.scenario_id,
        selector_sha=template.selector_sha,
        selector_spec=refreeze.proposed_selector_spec,
        source_trial_vectors=template.source_trial_vectors,
        response_torus_denominators=template.response_torus_denominators,
        response_reciprocal_indices=template.response_reciprocal_indices,
        source_readout_bridge_reciprocal_indices=(
            template.source_readout_bridge_reciprocal_indices
        ),
        source_readout_bridge_steps=template.source_readout_bridge_steps,
        reference_reciprocal_index=template.reference_reciprocal_index,
        preregistered_phase_bands=template.preregistered_phase_bands,
        operation_dag_sha=refreeze.operation_dag.dag_sha,
        compiled_contract_sha=template.compiled_contract_sha,
        construction_rule_id=template.construction_rule_id,
        construction_family_id=template.construction_family_id,
        expected_actual_shell_rank=template.expected_actual_shell_rank,
        expected_matched_shell_rank=template.expected_matched_shell_rank,
        actual_step_count=len(compiled.actual_step_signatures),
        matched_ablated_step_count=len(compiled.matched_ablated_step_signatures),
        actual_program_sha=template.actual_program_sha,
        matched_ablated_program_sha=template.matched_ablated_program_sha,
        preflight_derivation_or_recipe_sha=(
            template.preflight_derivation_or_recipe_sha
        ),
        actual_effect_digest=template.preflight_actual_effect_digest,
        matched_ablated_effect_digest=(template.preflight_matched_effect_digest),
        response_template_sha=template.template_sha,
        prediction_profile_sha=refreeze.prediction_profile.profile_sha,
        uses_global_fft_projection=template.uses_global_fft_projection,
        uses_per_k_time_step_projector=(template.uses_per_k_time_step_projector),
        response_contract_sha="0" * 64,
    )
    return replace(
        provisional,
        response_contract_sha=canonical_sha(
            current_scenario_response_contract_v2_payload(provisional)
        ),
    )


def _build_reviewed_modified_scenario_authorities_live() -> tuple[
    CurrentScenarioAuthorityV2, ...
]:
    candidate_v1 = _live_candidate_v1()
    candidate_v2 = _live_candidate_v2()
    _, scenario_index = _candidate_v1_indices(candidate_v1)
    result: list[CurrentScenarioAuthorityV2] = []
    observed: set[str] = set()
    for refreeze in candidate_v2.scenario_refreezes:
        scenario_id = refreeze.scenario_id
        if scenario_id in observed:
            raise ValueError("candidate v2 contains duplicate scenario refreezes")
        observed.add(scenario_id)
        source = scenario_index.get(scenario_id)
        if source is None:
            raise ValueError("candidate v2 scenario is absent from candidate v1")
        application, candidate_scenario = source
        execution = candidate_scenario.scenario_execution_spec
        if execution.execution_lane != "BLOCK_SUCCESS":
            raise ValueError("candidate v2 attempted to promote a non-success lane")
        response = _build_response_contract_from_refreeze(refreeze)
        provisional = CurrentScenarioAuthorityV2(
            scenario_authority_schema_version=(
                CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION
            ),
            authority_state="CURRENT_REVIEWED_SCENARIO",
            control_case_id=application.control_case_id,
            application_instance_id=application.application_instance_id,
            based_on_application_spec_sha=application.based_on_application_spec_sha,
            scenario_id=scenario_id,
            scenario_execution_spec=execution,
            source_disposition="CANDIDATE_V2_REVIEWED_MODIFIED",
            source_candidate_v1_scenario_sha=(
                candidate_scenario.candidate_scenario_sha
            ),
            source_candidate_v2_refreeze_sha=refreeze.scenario_refreeze_sha,
            response_contract=response,
            scenario_authority_sha="0" * 64,
        )
        result.append(
            replace(
                provisional,
                scenario_authority_sha=canonical_sha(
                    current_scenario_authority_v2_payload(provisional)
                ),
            )
        )
    if not result:
        raise ValueError("reviewed candidate v2 contains no scenario refreezes")
    return tuple(result)


def _verify_cached_authority_sequence(
    authorities: object,
    *,
    field: str,
) -> tuple[CurrentScenarioAuthorityV2, ...]:
    if type(authorities) is not tuple or not authorities:
        raise TypeError(f"{field} must be a non-empty exact tuple")
    for index, authority in enumerate(authorities):
        _exact_record(
            authority,
            CurrentScenarioAuthorityV2,
            f"{field}[{index}]",
        )
        authority.__post_init__()
        response = authority.response_contract
        _exact_record(
            response,
            CurrentScenarioResponseContractV2,
            f"{field}[{index}].response_contract",
        )
        response.__post_init__()
        if response.response_contract_sha != canonical_sha(
            current_scenario_response_contract_v2_payload(response)
        ):
            raise ValueError(f"{field} response-contract SHA drifted")
        if authority.scenario_authority_sha != canonical_sha(
            current_scenario_authority_v2_payload(authority)
        ):
            raise ValueError(f"{field} scenario-authority SHA drifted")
    return authorities


@lru_cache(maxsize=1)
def _reviewed_modified_scenario_authority_bytes() -> bytes:
    """Cache only immutable serialization, never caller-reachable records."""

    authorities = _build_reviewed_modified_scenario_authorities_live()
    return pickle.dumps(authorities, protocol=pickle.HIGHEST_PROTOCOL)


def _build_reviewed_modified_scenario_authorities() -> tuple[
    CurrentScenarioAuthorityV2, ...
]:
    return _verify_cached_authority_sequence(
        pickle.loads(_reviewed_modified_scenario_authority_bytes()),
        field="reviewed modified scenario authorities",
    )


def verify_reviewed_modified_scenario_authority(
    authority: CurrentScenarioAuthorityV2,
) -> CurrentScenarioAuthorityV2:
    """Verify one exact modified authority against the closed reviewed replay."""

    _exact_record(authority, CurrentScenarioAuthorityV2, "scenario authority")
    authority.__post_init__()
    response = authority.response_contract
    _exact_record(
        response,
        CurrentScenarioResponseContractV2,
        "response contract",
    )
    response.__post_init__()
    if response.response_contract_sha != canonical_sha(
        current_scenario_response_contract_v2_payload(response)
    ):
        raise ValueError("response-contract SHA does not match its exact body")
    if authority.scenario_authority_sha != canonical_sha(
        current_scenario_authority_v2_payload(authority)
    ):
        raise ValueError("scenario-authority SHA does not match its exact body")
    canonical = {
        item.scenario_id: item
        for item in _build_reviewed_modified_scenario_authorities()
    }.get(authority.scenario_id)
    if canonical is None or authority != canonical:
        raise ValueError("scenario authority differs from reviewed candidate-v2 replay")
    return authority


_TASK8_CASES = (
    ("C01_BLIND_HOLDOUT_FULL", "full"),
    ("C02_CONDITIONED_ZERO", "zero"),
    ("C03_EQUAL_RANK_DIRECT_SUM", "direct_sum"),
)


def _fp64_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _application_operation_dag_sha(
    parent_application,
    candidate_application: ParentFreezeCandidateApplication,
    candidate_scenario: ParentFreezeCandidateScenario,
    construction_sha: str,
) -> str:
    execution = candidate_scenario.scenario_execution_spec
    parent_matches = tuple(
        item
        for item in parent_application.scenario_execution_specs
        if item.scenario_id == execution.scenario_id
    )
    if (
        candidate_application.based_on_application_spec_sha
        != parent_application.application_spec_sha
        or candidate_scenario.based_on_application_spec_sha
        != parent_application.application_spec_sha
        or parent_matches != (execution,)
    ):
        raise ValueError("candidate scenario differs from live Parent-v1 operation DAG")
    return canonical_sha(
        {
            "operation_dag_schema_version": (
                "v3m0.current-parent-v2-operation-dag-binding.v1"
            ),
            "parent_v1_application": {
                **synthetic_control_application_spec_payload(parent_application),
                "application_spec_sha": parent_application.application_spec_sha,
            },
            "candidate_v1_application_sha": (
                candidate_application.candidate_application_sha
            ),
            "candidate_v1_scenario_sha": candidate_scenario.candidate_scenario_sha,
            "scenario_execution_spec": {
                **application_scenario_execution_spec_payload(execution),
                "scenario_sha": execution.scenario_sha,
            },
            "construction_sha": construction_sha,
        }
    )


def _task8_actual_step_record(primitive, target_conditioned: bool) -> dict[str, object]:
    if primitive.operation_id != "local_canonical_shear":
        raise ValueError("Task 8 actual program contains a non-shear primitive")
    return {
        **primitive_payload(primitive),
        "primitive_sha": primitive_sha(primitive),
        "target_conditioned": target_conditioned,
    }


def _task8_program_sha(
    branch: str,
    steps: tuple[tuple[object, bool], ...],
) -> str:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("Task 8 program branch is not frozen")
    return canonical_sha(
        {
            "program_schema_version": (
                "v3m0.task8-channel-generic-local-shear-program.v1"
            ),
            "branch": branch,
            "steps": [
                _task8_actual_step_record(primitive, conditioned)
                for primitive, conditioned in steps
            ],
        }
    )


def _task8_effect_digest(
    channel_order: tuple[str, ...],
    steps: tuple[tuple[object, bool], ...],
    branch: str,
) -> str:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("Task 8 effect branch is not frozen")
    channel_index = {channel: index for index, channel in enumerate(channel_order)}
    if len(channel_index) != len(channel_order):
        raise ValueError("Task 8 factory channel order repeats")
    spatial_ndim = len(steps[0][0].offset) if steps else 1
    zero = (0,) * spatial_ndim
    coefficients: dict[tuple[int, ...], np.ndarray] = {
        zero: np.eye(len(channel_order), dtype=np.complex128)
    }
    for primitive, _ in steps:
        source = channel_index[primitive.source_channel]
        destination = channel_index[primitive.destination_channel]
        coefficient = complex(*primitive.coefficient_wire)
        previous = {
            offset: np.asarray(matrix, dtype=np.complex128).copy()
            for offset, matrix in coefficients.items()
        }
        updated = {
            offset: np.asarray(matrix, dtype=np.complex128).copy()
            for offset, matrix in previous.items()
        }
        for offset, matrix in previous.items():
            shifted = tuple(
                left + right for left, right in zip(offset, primitive.offset)
            )
            contribution = np.zeros_like(matrix)
            contribution[destination] = coefficient * matrix[source]
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
            "effect_schema_version": ("v3m0.task8-channel-generic-laurent-effect.v1"),
            "branch": branch,
            "channel_order": list(channel_order),
            "support_offsets": [list(item) for item in support],
            "kernel_tensor_sha": kernel.tensor_sha,
        }
    )


def _build_task8_registry_contracts(parent, parent_applications) -> dict[str, object]:
    c01 = parent_applications["C01_BLIND_HOLDOUT_FULL"]
    spatial_shape = c01.grid_protocol.spatial_shape
    source = c01.basis_protocol.source_basis
    readout = c01.basis_protocol.readout_basis
    interface = PrimitiveInterface(
        interface_id="interface.synthetic.local-linear.v1",
        state_schema_id=source.state_schema_id,
        spatial_ndim=len(spatial_shape),
        channel_order=source.channel_order,
        dtype="complex128",
        backend="numpy",
    )
    holdout = build_basis_manifest(
        role="holdout_source",
        state_schema_id=source.state_schema_id,
        channel_order=source.channel_order,
        vectors=basis_manifest_array(source),
    )
    coefficients = (1.0, -1.0, 1.0)
    sources = (
        source.channel_order[0],
        source.channel_order[1],
        source.channel_order[0],
    )
    destinations = (
        source.channel_order[1],
        source.channel_order[0],
        source.channel_order[1],
    )
    operators = tuple(
        PrimitiveOperatorWire(
            mechanism_id=f"pair.000.shear.{layer}",
            production_id="local_canonical_shear",
            layer_slot_id=f"layer.000.{layer}",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=sources[layer],
            destination_channel=destinations[layer],
            offset=(0,) * interface.spatial_ndim,
            coefficient_wire=(coefficients[layer], 0.0),
        )
        for layer in range(3)
    )
    seed = build_calibration_seed(
        calibration_protocol_id="calibration.synthetic.v1",
        interface=interface,
        state_shape=(len(interface.channel_order), *spatial_shape),
        dt=0.25,
        target_blind_parameters=(("mass", 1.0),),
        source_basis=source,
        holdout_source_basis=holdout,
        readout_basis=readout,
        boundary_manifest_id="periodic-v1",
        operator_payload=operators,
    )
    observation = measure_calibration_holdout(seed)
    target = freeze_synthetic_target(seed, observation, "target.synthetic.v1")
    controls = (
        build_full_control(seed, observation, target),
        build_zero_control(1, target, spatial_shape, 0.25),
        build_direct_sum_control(1, target, spatial_shape, 0.25),
    )
    registry = build_closed_control_registry(controls, parent)
    raw_registry = registry.registry
    result: dict[str, object] = {}
    for (case_id, control_id), control, entry in zip(
        _TASK8_CASES,
        controls,
        raw_registry.entries,
    ):
        application = parent_applications[case_id]
        if (
            control.control_id != control_id
            or entry.control_id != control_id
            or entry.source_basis != application.basis_protocol.source_basis
            or entry.readout_basis != application.basis_protocol.readout_basis
            or entry.expected_h_actual_rank != entry.expected_curv_actual_rank
            or entry.expected_h_ablated_rank != entry.expected_curv_ablated_rank
        ):
            raise ValueError("Task 8 registry differs from live Parent-v1 application")
        outcome = matched_ablation(control.factory)
        if not outcome.status.defined or outcome.pair is None:
            raise ValueError("Task 8 matched ablation is unexpectedly undefined")
        pair = verify_ablation_pair(outcome.pair)
        actual_factory = pair.actual.factory
        conditioned = frozenset(
            item.mechanism_id for item in pair.manifest.replacements
        )
        actual_steps = tuple(
            (primitive, primitive.mechanism_id in conditioned)
            for primitive in actual_factory.primitives
        )
        matched_steps = tuple(item for item in actual_steps if not item[1])
        if (
            actual_factory.factory_sha != entry.factory_sha
            or pair.manifest.actual_factory_sha != entry.factory_sha
            or len(pair.ablated.factory.primitives) != len(actual_factory.primitives)
        ):
            raise ValueError("Task 8 registry/factory/ablation roots are spliced")
        actual_program_sha = _task8_program_sha("actual", actual_steps)
        matched_program_sha = _task8_program_sha(
            "matched_ablated",
            matched_steps,
        )
        actual_effect_digest = _task8_effect_digest(
            actual_factory.channel_order,
            actual_steps,
            "actual",
        )
        matched_effect_digest = _task8_effect_digest(
            actual_factory.channel_order,
            matched_steps,
            "matched_ablated",
        )
        derivation_sha = canonical_sha(
            {
                "derivation_schema_version": (
                    "v3m0.task8-selected-calibration-lane-derivation.v1"
                ),
                "control_case_id": case_id,
                "control_id": control_id,
                "registry_builder_id": entry.builder_id,
                "registry_sha": raw_registry.registry_sha,
                "registry_entry_sha": entry.entry_sha,
                "actual_factory_sha": actual_factory.factory_sha,
                "matched_ablated_factory_sha": pair.ablated.factory.factory_sha,
                "matched_ablation_manifest_sha": pair.manifest.manifest_sha,
                "ablation_policy": "delete-target-conditioned-slots-v1",
                "actual_program_sha": actual_program_sha,
                "matched_ablated_program_sha": matched_program_sha,
                "actual_effect_digest": actual_effect_digest,
                "matched_ablated_effect_digest": matched_effect_digest,
                "expected_actual_shell_rank": entry.expected_h_actual_rank,
                "expected_matched_shell_rank": entry.expected_h_ablated_rank,
                "factory_protocol": {
                    "spatial_shape": list(spatial_shape),
                    "dt": 0.25,
                    "target_blind_parameters": [["mass", 1.0]],
                },
                "source_closure": [
                    [
                        relative_path,
                        hashlib.sha256(
                            (_REPOSITORY_ROOT / relative_path).read_bytes()
                        ).hexdigest(),
                    ]
                    for relative_path in (
                        "rulespace_v3/ablation.py",
                        "rulespace_v3/controls.py",
                        "rulespace_v3/registry.py",
                    )
                ],
            }
        )
        result[case_id] = {
            "actual_steps": actual_steps,
            "matched_steps": matched_steps,
            "actual_program_sha": actual_program_sha,
            "matched_program_sha": matched_program_sha,
            "actual_effect_digest": actual_effect_digest,
            "matched_effect_digest": matched_effect_digest,
            "derivation_sha": derivation_sha,
            "actual_rank": entry.expected_h_actual_rank,
            "matched_rank": entry.expected_h_ablated_rank,
            "construction_family_id": (
                "task8-channel-generic-local-canonical-shear-v1"
            ),
        }
    return result


def _current_response_contract(
    candidate_scenario: ParentFreezeCandidateScenario,
    selector: ScenarioBasisSelectorSpec,
    source_trial_vectors,
    *,
    operation_dag_sha: str,
    construction_rule_id: str,
    construction_family_id: str,
    expected_actual_shell_rank: int,
    expected_matched_shell_rank: int,
    actual_steps: tuple[object, ...],
    matched_steps: tuple[object, ...],
    actual_program_sha: str,
    matched_program_sha: str,
    derivation_or_recipe_sha: str,
    actual_effect_digest: str,
    matched_effect_digest: str,
) -> CurrentScenarioResponseContractV2:
    scenario_id = candidate_scenario.scenario_execution_spec.scenario_id
    template = candidate_scenario.response_template
    if selector.scenario_id != scenario_id:
        raise ValueError("current selector is spliced to another scenario")
    contract_basis = {
        "contract_schema_version": "v3m0.current-compiled-response-contract.v1",
        "scenario_id": scenario_id,
        "operation_dag_sha": operation_dag_sha,
        "selector_sha": selector.selector_sha,
        "source_trial_vectors_sha": source_trial_vectors.tensor_sha,
        "construction_rule_id": construction_rule_id,
        "construction_family_id": construction_family_id,
        "expected_actual_shell_rank": expected_actual_shell_rank,
        "expected_matched_shell_rank": expected_matched_shell_rank,
        "actual_step_count": len(actual_steps),
        "matched_ablated_step_count": len(matched_steps),
        "actual_program_sha": actual_program_sha,
        "matched_ablated_program_sha": matched_program_sha,
        "derivation_or_recipe_sha": derivation_or_recipe_sha,
        "actual_effect_digest": actual_effect_digest,
        "matched_ablated_effect_digest": matched_effect_digest,
        "response_torus_denominators": list(template.response_torus_denominators),
        "response_reciprocal_indices": [
            list(item) for item in template.response_reciprocal_indices
        ],
        "source_readout_bridge_reciprocal_indices": [
            list(item) for item in template.source_readout_bridge_reciprocal_indices
        ],
        "source_readout_bridge_steps": list(template.source_readout_bridge_steps),
        "reference_reciprocal_index": list(template.reference_reciprocal_index),
        "preregistered_phase_bands": [
            list(item) for item in template.preregistered_phase_bands
        ],
    }
    compiled_contract_sha = canonical_sha(contract_basis)
    response_template_sha = canonical_sha(
        {
            "template_schema_version": ("v3m0.current-reviewed-response-template.v1"),
            "source_candidate_v1_template_sha": template.template_sha,
            "compiled_contract_sha": compiled_contract_sha,
            **contract_basis,
        }
    )
    provisional = CurrentScenarioResponseContractV2(
        response_contract_schema_version=(
            CURRENT_SCENARIO_RESPONSE_CONTRACT_SCHEMA_VERSION
        ),
        contract_state="CURRENT_REVIEWED_RESPONSE_CONTRACT",
        scenario_id=scenario_id,
        selector_sha=selector.selector_sha,
        selector_spec=selector,
        source_trial_vectors=source_trial_vectors,
        response_torus_denominators=template.response_torus_denominators,
        response_reciprocal_indices=template.response_reciprocal_indices,
        source_readout_bridge_reciprocal_indices=(
            template.source_readout_bridge_reciprocal_indices
        ),
        source_readout_bridge_steps=template.source_readout_bridge_steps,
        reference_reciprocal_index=template.reference_reciprocal_index,
        preregistered_phase_bands=template.preregistered_phase_bands,
        operation_dag_sha=operation_dag_sha,
        compiled_contract_sha=compiled_contract_sha,
        construction_rule_id=construction_rule_id,
        construction_family_id=construction_family_id,
        expected_actual_shell_rank=expected_actual_shell_rank,
        expected_matched_shell_rank=expected_matched_shell_rank,
        actual_step_count=len(actual_steps),
        matched_ablated_step_count=len(matched_steps),
        actual_program_sha=actual_program_sha,
        matched_ablated_program_sha=matched_program_sha,
        preflight_derivation_or_recipe_sha=derivation_or_recipe_sha,
        actual_effect_digest=actual_effect_digest,
        matched_ablated_effect_digest=matched_effect_digest,
        response_template_sha=response_template_sha,
        prediction_profile_sha=candidate_scenario.prediction_profile.profile_sha,
        uses_global_fft_projection=False,
        uses_per_k_time_step_projector=False,
        response_contract_sha="0" * 64,
    )
    return replace(
        provisional,
        response_contract_sha=canonical_sha(
            current_scenario_response_contract_v2_payload(provisional)
        ),
    )


def _finish_unchanged_authority(
    application: ParentFreezeCandidateApplication,
    scenario: ParentFreezeCandidateScenario,
    response: CurrentScenarioResponseContractV2,
    source_disposition: str,
) -> CurrentScenarioAuthorityV2:
    execution = scenario.scenario_execution_spec
    provisional = CurrentScenarioAuthorityV2(
        scenario_authority_schema_version=(CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION),
        authority_state="CURRENT_REVIEWED_SCENARIO",
        control_case_id=application.control_case_id,
        application_instance_id=application.application_instance_id,
        based_on_application_spec_sha=application.based_on_application_spec_sha,
        scenario_id=execution.scenario_id,
        scenario_execution_spec=execution,
        source_disposition=source_disposition,
        source_candidate_v1_scenario_sha=scenario.candidate_scenario_sha,
        source_candidate_v2_refreeze_sha=None,
        response_contract=response,
        scenario_authority_sha="0" * 64,
    )
    return replace(
        provisional,
        scenario_authority_sha=canonical_sha(
            current_scenario_authority_v2_payload(provisional)
        ),
    )


def _build_reviewed_unchanged_scenario_authorities_live() -> tuple[
    CurrentScenarioAuthorityV2, ...
]:
    candidate = _live_candidate_v1()
    candidate_applications, scenario_index = _candidate_v1_indices(candidate)
    parent = issue_v3m0_parent_freeze()
    parent_applications = {
        item.control_case_id: item
        for item in parent.manifest.synthetic_control_application_specs
    }
    task8 = _build_task8_registry_contracts(parent, parent_applications)
    result: list[CurrentScenarioAuthorityV2] = []
    for case_id, _ in _TASK8_CASES:
        application = candidate_applications[case_id]
        success = tuple(
            item
            for item in application.scenario_candidates
            if item.scenario_execution_spec.execution_lane == "BLOCK_SUCCESS"
        )
        if len(success) != 1:
            raise ValueError("Task 8 application lacks its unique success scenario")
        scenario = success[0]
        evidence = task8[case_id]
        operation_dag_sha = _application_operation_dag_sha(
            parent_applications[case_id],
            application,
            scenario,
            evidence["derivation_sha"],
        )
        response = _current_response_contract(
            scenario,
            scenario.selector_spec,
            scenario.response_template.source_trial_vectors,
            operation_dag_sha=operation_dag_sha,
            construction_rule_id=(scenario.scenario_execution_spec.execution_recipe_id),
            construction_family_id=evidence["construction_family_id"],
            expected_actual_shell_rank=evidence["actual_rank"],
            expected_matched_shell_rank=evidence["matched_rank"],
            actual_steps=evidence["actual_steps"],
            matched_steps=evidence["matched_steps"],
            actual_program_sha=evidence["actual_program_sha"],
            matched_program_sha=evidence["matched_program_sha"],
            derivation_or_recipe_sha=evidence["derivation_sha"],
            actual_effect_digest=evidence["actual_effect_digest"],
            matched_effect_digest=evidence["matched_effect_digest"],
        )
        result.append(
            _finish_unchanged_authority(
                application,
                scenario,
                response,
                "PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE",
            )
        )

    c04_case_id = "C04_CANONICAL_ANGLE_025_075"
    c04_application = candidate_applications[c04_case_id]
    c04_scenarios = tuple(
        item
        for item in c04_application.scenario_candidates
        if item.scenario_execution_spec.execution_lane == "BLOCK_SUCCESS"
    )
    if len(c04_scenarios) != 1:
        raise ValueError("C04 application lacks its unique success scenario")
    c04_scenario = c04_scenarios[0]
    recipe = _verify_c04_canonical_angle_recipe(build_c04_canonical_angle_recipe())
    execution = c04_scenario.scenario_execution_spec
    parameters = dict(execution.recipe_parameter_wires)
    if (
        execution.recipe_derivation_source_id != "c04-two-mode-split-step-analytic-v1"
        or parameters["alpha"].fp64_bits_value != _fp64_bits(recipe.alpha)
        or parameters["beta"].fp64_bits_value != _fp64_bits(recipe.beta)
    ):
        raise ValueError("C04 recipe differs from live Parent-v1 fp64 parameters")
    template = c04_scenario.response_template
    if (
        template.preregistered_phase_bands != (recipe.reference_phase_band,)
        or tuple(
            2.0 * math.pi * index[0] / template.response_torus_denominators[0]
            for index in template.response_reciprocal_indices
        )
        != recipe.response_momenta
    ):
        raise ValueError("C04 recipe differs from the Parent-v1 response grid")
    for branch in ("actual", "matched_ablated"):
        for momentum in recipe.response_momenta:
            symbol = c04_canonical_angle_recipe_symbol(recipe, momentum, branch)
            phases = np.angle(np.linalg.eigvals(symbol))
            in_band = np.count_nonzero(
                (phases > recipe.reference_phase_band[0])
                & (phases < recipe.reference_phase_band[1])
            )
            if int(in_band) != recipe.expected_shell_rank:
                raise ValueError("C04 positive shell rank differs from analytic recipe")
    base_selector = c04_scenario.selector_spec
    public_source = basis_manifest_array(
        parent_applications[c04_case_id].basis_protocol.source_basis
    )
    public_readout = basis_manifest_array(
        parent_applications[c04_case_id].basis_protocol.readout_basis
    )
    if not (
        np.array_equal(public_source, np.eye(4, dtype=np.complex128))
        and np.array_equal(public_readout, np.eye(4, dtype=np.complex128))
    ):
        raise ValueError("C04 public Parent-v1 basis is not identity-4")
    provisional_selector = ScenarioBasisSelectorSpec(
        selector_schema_version=base_selector.selector_schema_version,
        scenario_id=execution.scenario_id,
        public_source_basis_manifest_id=(base_selector.public_source_basis_manifest_id),
        public_readout_basis_manifest_id=(
            base_selector.public_readout_basis_manifest_id
        ),
        source_selector_derivation_id=(
            "c04-canonical-angle-circular-source-selector-v2"
        ),
        readout_selector_derivation_id=(
            "c04-canonical-angle-circular-readout-selector-v2"
        ),
        source_selector=recipe.source_injection,
        readout_selector=recipe.readout,
        source_injection=recipe.source_injection,
        readout_coisometry=recipe.readout,
        selector_sha="0" * 64,
    )
    c04_selector = replace(
        provisional_selector,
        selector_sha=canonical_sha(
            scenario_basis_selector_spec_payload(provisional_selector)
        ),
    )
    c04_trials = freeze_complex_tensor(np.eye(2, dtype=np.complex128))
    c04_actual_steps = recipe.steps
    c04_matched_steps = tuple(
        item for item in recipe.steps if not item.target_conditioned
    )

    def c04_program_sha(branch: str, steps) -> str:
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

    c04_actual_program_sha = c04_program_sha("actual", c04_actual_steps)
    c04_matched_program_sha = c04_program_sha(
        "matched_ablated",
        c04_matched_steps,
    )
    c04_operation_dag_sha = _application_operation_dag_sha(
        parent_applications[c04_case_id],
        c04_application,
        c04_scenario,
        recipe.recipe_sha,
    )
    c04_response = _current_response_contract(
        c04_scenario,
        c04_selector,
        c04_trials,
        operation_dag_sha=c04_operation_dag_sha,
        construction_rule_id=recipe.recipe_id,
        construction_family_id="c04-canonical-angle-local-shear-family-v1",
        expected_actual_shell_rank=recipe.expected_shell_rank,
        expected_matched_shell_rank=recipe.expected_shell_rank,
        actual_steps=c04_actual_steps,
        matched_steps=c04_matched_steps,
        actual_program_sha=c04_actual_program_sha,
        matched_program_sha=c04_matched_program_sha,
        derivation_or_recipe_sha=recipe.recipe_sha,
        actual_effect_digest=recipe.actual_effect_digest,
        matched_effect_digest=recipe.ablated_effect_digest,
    )
    result.append(
        _finish_unchanged_authority(
            c04_application,
            c04_scenario,
            c04_response,
            "PARENT_V1_C04_CLOSED_RECIPE",
        )
    )
    expected_c04_id = execution.scenario_id
    if expected_c04_id not in scenario_index:
        raise ValueError("C04 scenario is absent from candidate-v1 index")
    return tuple(result)


@lru_cache(maxsize=1)
def _reviewed_unchanged_scenario_authority_bytes() -> bytes:
    """Cache only immutable serialization, never caller-reachable records."""

    authorities = _build_reviewed_unchanged_scenario_authorities_live()
    return pickle.dumps(authorities, protocol=pickle.HIGHEST_PROTOCOL)


def _build_reviewed_unchanged_scenario_authorities() -> tuple[
    CurrentScenarioAuthorityV2, ...
]:
    """Return detached exact replays of the four unchanged success lanes."""

    return _verify_cached_authority_sequence(
        pickle.loads(_reviewed_unchanged_scenario_authority_bytes()),
        field="reviewed unchanged scenario authorities",
    )


def verify_reviewed_unchanged_scenario_authority(
    authority: CurrentScenarioAuthorityV2,
) -> CurrentScenarioAuthorityV2:
    """Verify C01--C04 against the closed registry/recipe replay snapshot."""

    _exact_record(authority, CurrentScenarioAuthorityV2, "scenario authority")
    authority.__post_init__()
    response = authority.response_contract
    _exact_record(
        response,
        CurrentScenarioResponseContractV2,
        "response contract",
    )
    response.__post_init__()
    if response.response_contract_sha != canonical_sha(
        current_scenario_response_contract_v2_payload(response)
    ):
        raise ValueError("response-contract SHA does not match its exact body")
    if authority.scenario_authority_sha != canonical_sha(
        current_scenario_authority_v2_payload(authority)
    ):
        raise ValueError("scenario-authority SHA does not match its exact body")
    canonical = {
        item.scenario_id: item
        for item in _build_reviewed_unchanged_scenario_authorities()
    }.get(authority.scenario_id)
    if canonical is None or authority != canonical:
        raise ValueError("scenario authority differs from closed Parent-v1 replay")
    return authority


def _ordered_current_scenario_authorities(
    modified: tuple[CurrentScenarioAuthorityV2, ...],
    unchanged: tuple[CurrentScenarioAuthorityV2, ...],
) -> tuple[CurrentScenarioAuthorityV2, ...]:
    if type(modified) is not tuple or type(unchanged) is not tuple:
        raise TypeError("current authority partitions must be exact tuples")
    combined = (*modified, *unchanged)
    if not all(type(item) is CurrentScenarioAuthorityV2 for item in combined):
        raise TypeError("current authority partitions contain a wrong record type")
    by_id: dict[str, CurrentScenarioAuthorityV2] = {}
    for authority in combined:
        if authority.scenario_id in by_id:
            raise ValueError("current authority partitions contain duplicate IDs")
        by_id[authority.scenario_id] = authority
    expected = expected_block_success_scenario_ids()
    outside = tuple(item for item in by_id if item not in expected)
    if outside:
        raise ValueError(f"current scenario registry is outside Parent-v1: {outside!r}")
    ordered = tuple(by_id[item] for item in expected if item in by_id)
    return _require_complete_block_success_registry(ordered)


def _require_complete_block_success_registry(
    authorities: tuple[CurrentScenarioAuthorityV2, ...],
) -> tuple[CurrentScenarioAuthorityV2, ...]:
    if type(authorities) is not tuple or not all(
        type(item) is CurrentScenarioAuthorityV2 for item in authorities
    ):
        raise TypeError("current scenario registry must be an exact authority tuple")
    observed = tuple(item.scenario_id for item in authorities)
    duplicates = tuple(
        scenario_id
        for index, scenario_id in enumerate(observed)
        if scenario_id in observed[:index]
    )
    if duplicates:
        raise ValueError(f"current scenario registry has duplicate IDs: {duplicates!r}")
    expected = expected_block_success_scenario_ids()
    outside = tuple(item for item in observed if item not in expected)
    if outside:
        raise ValueError(f"current scenario registry is outside Parent-v1: {outside!r}")
    missing = tuple(item for item in expected if item not in observed)
    if missing:
        raise ValueError(
            f"current scenario registry is missing {len(missing)} IDs: {missing!r}"
        )
    if observed != expected:
        raise ValueError(
            "current scenario registry is not in canonical Parent-v1 order"
        )
    return authorities


def _git_read_object(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ("git", *arguments),
        cwd=_REPOSITORY_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _preparation_commit_blocking_reasons(
    commit_sha: object,
) -> tuple[str, ...]:
    """Prove that P exists, is ancestral, and freezes reviewed source bytes."""

    if (
        type(commit_sha) is not str
        or _LOWER_GIT_SHA.fullmatch(commit_sha) is None
    ):
        return ("reviewed preparation commit P is not injected",)
    commit = _git_read_object("cat-file", "-e", f"{commit_sha}^{{commit}}")
    if commit.returncode != 0:
        return ("reviewed preparation commit P is unavailable",)
    ancestry = _git_read_object(
        "merge-base",
        "--is-ancestor",
        commit_sha,
        "HEAD",
    )
    if ancestry.returncode != 0:
        return ("reviewed preparation commit P is not an ancestor of HEAD",)

    missing = tuple(
        relative_path
        for relative_path in _PREPARATION_REQUIRED_PATHS
        if _git_read_object(
            "cat-file",
            "-e",
            f"{commit_sha}:{relative_path}",
        ).returncode
        != 0
    )
    reasons: list[str] = []
    if missing:
        reasons.append(
            "reviewed preparation commit P lacks required preparation path(s): "
            + ", ".join(missing)
        )

    drifted: list[str] = []
    for relative_path in _SOURCE_CLOSURE_PATHS:
        reviewed = _git_read_object(
            "cat-file",
            "blob",
            f"{commit_sha}:{relative_path}",
        )
        current_path = _REPOSITORY_ROOT / relative_path
        if (
            reviewed.returncode != 0
            or not current_path.is_file()
            or hashlib.sha256(reviewed.stdout).hexdigest()
            != hashlib.sha256(current_path.read_bytes()).hexdigest()
        ):
            drifted.append(relative_path)
    if drifted:
        reasons.append(
            "reviewed source closure differs from preparation commit P: "
            + ", ".join(drifted)
        )
    return tuple(reasons)


def _finalization_input_state(
    candidate_v2: ParentFreezeCandidateV2Manifest,
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    reasons.extend(
        _preparation_commit_blocking_reasons(
            PARENT_V2_PREPARATION_COMMIT_SHA
        )
    )
    if (
        PARENT_V2_REVIEWED_CANDIDATE_V2_SHA256 is None
        or _LOWER_SHA256.fullmatch(PARENT_V2_REVIEWED_CANDIDATE_V2_SHA256) is None
    ):
        reasons.append("reviewed candidate-v2 SHA is not injected")
    elif candidate_v2.candidate_sha != PARENT_V2_REVIEWED_CANDIDATE_V2_SHA256:
        reasons.append("live candidate-v2 SHA differs from the reviewed root")
    if (
        PARENT_V2_SIGNED_ERRATUM_RAW_SHA256 is None
        or _LOWER_SHA256.fullmatch(PARENT_V2_SIGNED_ERRATUM_RAW_SHA256) is None
    ):
        reasons.append("SIGNED incremental erratum raw SHA D is not injected")
    if reasons:
        return "NOT_INJECTED", tuple(reasons)

    path = _REPOSITORY_ROOT / PARENT_V2_SIGNED_ERRATUM_SOURCE_PATH
    raw = path.read_bytes()
    observed_sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")
    if (
        observed_sha != PARENT_V2_SIGNED_ERRATUM_RAW_SHA256
        or "状态：SIGNED" not in text
        or "状态：DRAFT" in text
    ):
        return (
            "DOCUMENT_NOT_SIGNED",
            ("SIGNED incremental erratum bytes/status do not match D",),
        )
    return "READY", ()


def audit_v3m0_parent_v2_readiness() -> ParentV2ReadinessAudit:
    candidate_v2 = _live_candidate_v2()
    modified = _build_reviewed_modified_scenario_authorities()
    unchanged = _build_reviewed_unchanged_scenario_authorities()
    current = _ordered_current_scenario_authorities(modified, unchanged)
    promoted_ids = tuple(item.scenario_id for item in modified)
    expected = expected_block_success_scenario_ids()
    covered = frozenset(item.scenario_id for item in current)
    unresolved = tuple(item for item in expected if item not in covered)
    state, input_reasons = _finalization_input_state(candidate_v2)
    reasons = list(input_reasons)
    if unresolved:
        reasons.append(
            f"{len(unresolved)} BLOCK_SUCCESS scenarios lack exact current authorities"
        )
    provisional = ParentV2ReadinessAudit(
        audit_schema_version=PARENT_V2_READINESS_AUDIT_SCHEMA_VERSION,
        finalization_inputs_state=state,
        expected_block_success_scenario_ids=expected,
        promoted_modified_scenario_ids=promoted_ids,
        unresolved_unchanged_scenario_ids=unresolved,
        blocking_reasons=tuple(reasons),
        can_issue=not reasons,
        audit_sha="0" * 64,
    )
    finished = replace(
        provisional,
        audit_sha=canonical_sha(parent_v2_readiness_audit_payload(provisional)),
    )
    return verify_parent_v2_readiness_audit(finished)


def _build_signed_source_ref() -> SignedSourceRefV1:
    if (
        PARENT_V2_PREPARATION_COMMIT_SHA is None
        or PARENT_V2_SIGNED_ERRATUM_RAW_SHA256 is None
    ):
        raise ParentV2IssuanceBlocked(("SIGNED source constants P/D are not injected",))
    provisional = SignedSourceRefV1(
        source_ref_schema_version=SIGNED_SOURCE_REF_SCHEMA_VERSION,
        source_role="SIGNED_INCREMENTAL_ERRATUM",
        relative_path=PARENT_V2_SIGNED_ERRATUM_SOURCE_PATH,
        raw_sha256=PARENT_V2_SIGNED_ERRATUM_RAW_SHA256,
        preparation_commit_sha=PARENT_V2_PREPARATION_COMMIT_SHA,
        source_ref_sha="0" * 64,
    )
    return replace(
        provisional,
        source_ref_sha=canonical_sha(signed_source_ref_v1_payload(provisional)),
    )


def _build_source_closure() -> tuple[tuple[str, str], ...]:
    forbidden = {
        "rulespace_v3/parent_authority.py",
        "rulespace_v3/parent_freeze_v2.py",
    }
    if forbidden.intersection(_SOURCE_CLOSURE_PATHS):
        raise ValueError("root-bearing files must not enter Parent source closure")
    return tuple(
        (
            relative_path,
            hashlib.sha256((_REPOSITORY_ROOT / relative_path).read_bytes()).hexdigest(),
        )
        for relative_path in _SOURCE_CLOSURE_PATHS
    )


def _group_application_authorities(
    scenario_authorities: tuple[CurrentScenarioAuthorityV2, ...],
    candidate_v1: ParentFreezeCandidateManifest,
) -> tuple[CurrentApplicationAuthorityV2, ...]:
    application_index, _ = _candidate_v1_indices(candidate_v1)
    grouped: list[CurrentApplicationAuthorityV2] = []
    for source_application in candidate_v1.application_candidates:
        members = tuple(
            item
            for item in scenario_authorities
            if item.control_case_id == source_application.control_case_id
        )
        if not members:
            continue
        canonical_source = application_index[source_application.control_case_id]
        provisional = CurrentApplicationAuthorityV2(
            application_authority_schema_version=(
                CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION
            ),
            authority_state="CURRENT_REVIEWED_APPLICATION",
            control_case_id=source_application.control_case_id,
            application_instance_id=source_application.application_instance_id,
            based_on_application_spec_sha=(
                source_application.based_on_application_spec_sha
            ),
            source_candidate_v1_application_sha=(
                canonical_source.candidate_application_sha
            ),
            scenario_authorities=members,
            application_authority_sha="0" * 64,
        )
        grouped.append(
            replace(
                provisional,
                application_authority_sha=canonical_sha(
                    current_application_authority_v2_payload(provisional)
                ),
            )
        )
    return tuple(grouped)


def _build_closed_parent_v2_manifest() -> ParentFreezeV2Manifest:
    """Build the sole current raw body, or fail before any capability exists."""

    audit = audit_v3m0_parent_v2_readiness()
    if not audit.can_issue:
        raise ParentV2IssuanceBlocked(audit.blocking_reasons)
    candidate_v1 = _live_candidate_v1()
    candidate_v2 = _live_candidate_v2()
    scenario_authorities = _ordered_current_scenario_authorities(
        _build_reviewed_modified_scenario_authorities(),
        _build_reviewed_unchanged_scenario_authorities(),
    )
    applications = _group_application_authorities(
        scenario_authorities,
        candidate_v1,
    )
    historical_parent: ParentFreezeManifest = issue_v3m0_parent_freeze().manifest
    provisional = ParentFreezeV2Manifest(
        parent_freeze_schema_version=PARENT_FREEZE_V2_SCHEMA_VERSION,
        authority_state="CURRENT_PARENT_V2_ISSUED",
        program_id="projective-rule-space-v3m0-v2",
        historical_parent_v1=historical_parent,
        reviewed_candidate_v1=candidate_v1,
        reviewed_candidate_v2=candidate_v2,
        signed_incremental_erratum=_build_signed_source_ref(),
        current_application_authorities=applications,
        block_success_scenario_ids=expected_block_success_scenario_ids(),
        source_closure=_build_source_closure(),
        parent_freeze_v2_sha="0" * 64,
    )
    return replace(
        provisional,
        parent_freeze_v2_sha=canonical_sha(
            parent_freeze_v2_manifest_payload(provisional)
        ),
    )


__all__ = [
    "PARENT_V2_PREPARATION_COMMIT_SHA",
    "PARENT_V2_REVIEWED_CANDIDATE_V2_SHA256",
    "PARENT_V2_SIGNED_ERRATUM_RAW_SHA256",
    "PARENT_V2_SIGNED_ERRATUM_SOURCE_PATH",
    "ParentV2IssuanceBlocked",
    "audit_v3m0_parent_v2_readiness",
    "expected_block_success_scenario_ids",
    "verify_reviewed_modified_scenario_authority",
    "verify_reviewed_unchanged_scenario_authority",
]
