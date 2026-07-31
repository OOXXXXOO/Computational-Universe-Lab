"""Closed construction and readiness audit for the current Parent-v2.

This module has no public promotion or hydration API.  It can mechanically
lift only scenario contracts present in the independently reviewed candidate
v2, inventories every historical ``BLOCK_SUCCESS`` scenario, and refuses to
build a Parent until all remaining scenarios and the signed-source inputs are
closed.  The live identity facade is isolated in :mod:`parent_authority`.
"""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import replace
from pathlib import Path
from typing import Optional

from .candidate_scenario_dag import extract_candidate_scenario_contract
from .evidence import canonical_sha
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
    build_v3m0_parent_freeze_candidate,
    issue_v3m0_parent_freeze,
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
    "rulespace_v3/application_recipes.py",
    "rulespace_v3/c05_projector_recipe.py",
    "rulespace_v3/c12_incidence_preflight.py",
    "rulespace_v3/candidate_scenario_dag.py",
    "rulespace_v3/evidence.py",
    "rulespace_v3/factory.py",
    "rulespace_v3/geometry.py",
    "rulespace_v3/geometry_application_recipes.py",
    "rulespace_v3/interference_mode_preflight.py",
    "rulespace_v3/parent_candidate_v2.py",
    "rulespace_v3/parent_freeze.py",
    "rulespace_v3/parent_v2_contracts.py",
    "rulespace_v3/response.py",
    "rulespace_v3/thresholds.py",
    "rulespace_v3/trace.py",
)


class ParentV2IssuanceBlocked(RuntimeError):
    """Structured scientific/authority gate; never a partial Parent."""

    def __init__(self, reasons: tuple[str, ...]) -> None:
        if type(reasons) is not tuple or not reasons or not all(
            type(item) is str and bool(item.strip()) for item in reasons
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


def _live_candidate_v1() -> ParentFreezeCandidateManifest:
    return verify_parent_freeze_candidate(build_v3m0_parent_freeze_candidate())


def _live_candidate_v2() -> ParentFreezeCandidateV2Manifest:
    return verify_parent_freeze_candidate_v2(
        build_v3m0_parent_freeze_candidate_v2()
    )


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


def _build_response_contract_from_refreeze(refreeze) -> CurrentScenarioResponseContractV2:
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
        operation_dag_sha=refreeze.operation_dag.dag_sha,
        compiled_contract_sha=template.compiled_contract_sha,
        construction_rule_id=template.construction_rule_id,
        construction_family_id=template.construction_family_id,
        expected_actual_shell_rank=template.expected_actual_shell_rank,
        expected_matched_shell_rank=template.expected_matched_shell_rank,
        actual_program_sha=template.actual_program_sha,
        matched_ablated_program_sha=template.matched_ablated_program_sha,
        preflight_derivation_or_recipe_sha=(
            template.preflight_derivation_or_recipe_sha
        ),
        actual_effect_digest=template.preflight_actual_effect_digest,
        matched_ablated_effect_digest=(
            template.preflight_matched_effect_digest
        ),
        response_template_sha=template.template_sha,
        prediction_profile_sha=refreeze.prediction_profile.profile_sha,
        uses_global_fft_projection=template.uses_global_fft_projection,
        uses_per_k_time_step_projector=(
            template.uses_per_k_time_step_projector
        ),
        response_contract_sha="0" * 64,
    )
    return replace(
        provisional,
        response_contract_sha=canonical_sha(
            current_scenario_response_contract_v2_payload(provisional)
        ),
    )


def _build_reviewed_modified_scenario_authorities_live(
) -> tuple[CurrentScenarioAuthorityV2, ...]:
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


# A private immutable-by-convention replay snapshot amortizes the expensive
# preflights.  Every public/internal return is detached, and live verification
# below compares against this closed canonical body rather than caller hashes.
_REVIEWED_MODIFIED_SCENARIO_AUTHORITY_SNAPSHOT = (
    _build_reviewed_modified_scenario_authorities_live()
)


def _build_reviewed_modified_scenario_authorities(
) -> tuple[CurrentScenarioAuthorityV2, ...]:
    return copy.deepcopy(_REVIEWED_MODIFIED_SCENARIO_AUTHORITY_SNAPSHOT)


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
        for item in _REVIEWED_MODIFIED_SCENARIO_AUTHORITY_SNAPSHOT
    }.get(authority.scenario_id)
    if canonical is None or authority != canonical:
        raise ValueError("scenario authority differs from reviewed candidate-v2 replay")
    return authority


def _build_reviewed_unchanged_scenario_authorities(
) -> tuple[CurrentScenarioAuthorityV2, ...]:
    """Future exact replay hook; absence is an intentional issuance blocker.

    C01--C04 (and any scenario not yet present in candidate v2) need their own
    mechanically replayed matched rank/program/effect/construction contract.
    Returning an empty tuple is safer than projecting those fields out of v1.
    """

    return ()


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
        raise ValueError(f"current scenario registry is missing {len(missing)} IDs: {missing!r}")
    if observed != expected:
        raise ValueError("current scenario registry is not in canonical Parent-v1 order")
    return authorities


def _finalization_input_state(
    candidate_v2: ParentFreezeCandidateV2Manifest,
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if (
        PARENT_V2_PREPARATION_COMMIT_SHA is None
        or _LOWER_GIT_SHA.fullmatch(PARENT_V2_PREPARATION_COMMIT_SHA) is None
    ):
        reasons.append("reviewed preparation commit P is not injected")
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
    promoted_ids = tuple(item.scenario_id for item in modified)
    expected = expected_block_success_scenario_ids()
    unresolved = tuple(item for item in expected if item not in promoted_ids)
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
        raise ParentV2IssuanceBlocked(
            ("SIGNED source constants P/D are not injected",)
        )
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
    scenario_authorities = (
        *_build_reviewed_modified_scenario_authorities(),
        *_build_reviewed_unchanged_scenario_authorities(),
    )
    _require_complete_block_success_registry(scenario_authorities)
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
]
