"""Production numerical runner for the frozen Task-11 window calibration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .ablation import _verify_construction_outcome
from .bridge import build_full_state_bridge_spec
from .calibration_authority import (
    CANDIDATE_ATTEMPT_AUDIT_SCHEMA_VERSION,
    BranchSpectrumAudit,
    CandidateAttemptAudit,
    ControlCandidateAudit,
    ControlCandidateFailure,
    ControlCandidateOutcome,
    PerControlReadoutSpectrumAudit,
    WindowCalibrationOutcome,
    WindowCandidateAudit,
    _expected_spectrum_values,
    _shell_comparison_values,
    branch_spectrum_audit_payload,
    calibrate_window_and_thresholds,
    candidate_attempt_audit_payload,
    compute_window_readout_calibration_audits,
    control_candidate_audit_payload,
    control_candidate_failure_reason,
    control_candidate_outcome_payload,
    issue_expected_rank_declaration,
    per_control_readout_spectrum_audit_payload,
    window_candidate_audit_payload,
)
from .certificate import (
    VerifiedDynamicsCertificate,
    certify_transition_dynamics,
)
from .contracts import BlockStatus
from .current_window_replay import (
    CurrentWindowCalibrationProtocolV2,
    VerifiedCurrentWindowCalibrationProtocolV2,
    _replay_current_window_calibration_protocol_v2,
    verify_current_window_calibration_protocol_v2_body,
)
from .dynamics import VerifiedTransition, measure_transition
from .evidence import canonical_sha
from .factory import VerifiedFactory, _reverify_verified_factory
from .frozen_call_graph import freeze_rulespace_call_graph
from .grids import build_dynamics_grid_manifest
from .metric import build_stability_metric_witness
from .parent_freeze import VerifiedParentFreeze, _reverify_verified_parent_freeze
from .prestructure import issue_synthetic_prestructure_authority
from .qualification import (
    VerifiedCertificateBackedQualification,
    qualify_ablation_from_certificate,
)
from .registry import (
    CONTROL_ORDER,
    ControlRegistryEntry,
    VerifiedControlRegistry,
    _reverify_verified_control_registry,
    build_closed_control_registry,
)
from .replay_scope import _scoped_replay_context
from .response import (
    PairedResponseFailure,
    build_endpoint_reference,
    build_endpoint_shell,
    build_endpoint_shell_spec,
    build_paired_filtered_response,
    build_response_run_spec,
)
from .runtime import issue_runtime_evidence_manifest
from .structure import build_structure_manifest
from .task8_control_replay import (
    CurrentControlRegistryV2,
    CurrentTask8ControlReplay,
    verify_current_control_registry_v2_body,
)
from .thresholds import T_CANDIDATES, verify_window_comparison_gates
from .window import (
    VerifiedWindowCalibrationProtocol,
    build_control_window_protocol_entries,
    build_window_calibration_protocol,
)


class Task11PrerequisiteUnresolved(RuntimeError):
    """Task 10 could not issue a certificate required by Task 11."""


@dataclass(frozen=True)
class _Task11ControlDynamics:
    control_id: Literal["full", "zero", "direct_sum"]
    construction: object
    actual_factory: VerifiedFactory
    ablated_factory: VerifiedFactory
    actual_transition: VerifiedTransition
    ablated_transition: VerifiedTransition
    actual_certificate: VerifiedDynamicsCertificate
    ablated_certificate: VerifiedDynamicsCertificate
    qualification: VerifiedCertificateBackedQualification


def _build_task11_numerical_roots(
    parent: VerifiedParentFreeze,
    task8_replay: CurrentTask8ControlReplay,
    current_registry: CurrentControlRegistryV2,
    current_window: CurrentWindowCalibrationProtocolV2,
):
    """Bind the numerical registry to each canonical pair's actual identity."""

    if type(parent) is not VerifiedParentFreeze:
        raise TypeError("Task-11 roots require the exact historical Parent")
    if type(task8_replay) is not CurrentTask8ControlReplay:
        raise TypeError("Task-11 roots require an exact Task-8 replay")
    if type(current_registry) is not CurrentControlRegistryV2:
        raise TypeError("Task-11 roots require an exact current registry body")
    if type(current_window) is not CurrentWindowCalibrationProtocolV2:
        raise TypeError("Task-11 roots require an exact current window body")
    _reverify_verified_parent_freeze(parent)
    replay_registry_view = _reverify_verified_control_registry(
        task8_replay.legacy_registry
    )
    if replay_registry_view.parent is not parent:
        raise ValueError("Task-11 replay is not bound to this historical Parent")
    verify_current_control_registry_v2_body(
        current_registry,
        current_registry.parent_freeze_v2_sha,
        task8_replay,
    )
    verify_current_window_calibration_protocol_v2_body(
        current_window,
        current_registry,
        task8_replay,
    )
    if current_window.current_control_registry != current_registry:
        raise ValueError("Task-11 current registry/window roots are spliced")
    if len(task8_replay.controls) != len(
        task8_replay.matched_ablation_outcomes
    ):
        raise ValueError("Task-11 replay control/construction counts differ")

    numerical_controls = []
    for control, construction in zip(
        task8_replay.controls,
        task8_replay.matched_ablation_outcomes,
    ):
        verified_construction = _verify_construction_outcome(construction)
        if (
            not verified_construction.status.defined
            or verified_construction.pair is None
        ):
            raise ValueError("Task-11 replay contains an undefined construction")
        original = _reverify_verified_factory(control.factory)
        pair_actual = _reverify_verified_factory(
            verified_construction.pair.actual
        )
        if (
            original.factory != pair_actual.factory
            or original.trace != pair_actual.trace
            or original.target != pair_actual.target
        ):
            raise ValueError("Task-11 pair actual differs from its control root")
        numerical_controls.append(
            replace(control, factory=verified_construction.pair.actual)
        )

    registry = build_closed_control_registry(tuple(numerical_controls), parent)
    if registry.registry != task8_replay.legacy_registry.registry:
        raise ValueError("Task-11 numerical registry body drifted during rebinding")
    entries = build_control_window_protocol_entries(registry)
    protocol = build_window_calibration_protocol(registry, entries)
    if protocol.protocol != current_window.legacy_window_protocol:
        raise ValueError("Task-11 numerical window body drifted during rebinding")
    return registry, protocol


def _certify_task11_branch(
    factory: VerifiedFactory,
    authority,
    runtime_manifest,
) -> tuple[VerifiedTransition, VerifiedDynamicsCertificate]:
    transition = measure_transition(factory, authority)
    structure = build_structure_manifest(factory, authority)
    metric = build_stability_metric_witness(factory, authority, structure)
    bridge = build_full_state_bridge_spec(factory, authority)
    grid = build_dynamics_grid_manifest(
        transition.transition.support_offsets,
        metric.metric_support_offsets,
    )
    certification = certify_transition_dynamics(
        factory,
        transition,
        authority,
        structure,
        metric,
        bridge,
        grid,
        runtime_manifest,
    )
    certificate = certification.certificate
    if certificate is None:
        raw = certification.outcome
        raise Task11PrerequisiteUnresolved(
            "Task-11 prerequisite certificate is undefined: "
            f"{raw.failure!s} ({raw.outcome_sha})"
        )
    return transition, certificate


def _build_task11_dynamics_chains(
    parent: VerifiedParentFreeze,
    task8_replay: CurrentTask8ControlReplay,
    registry: VerifiedControlRegistry,
) -> tuple[_Task11ControlDynamics, ...]:
    registry_view = _reverify_verified_control_registry(registry)
    runtime_manifest = issue_runtime_evidence_manifest()
    result = []
    for control_id, control, construction in zip(
        CONTROL_ORDER,
        registry_view.controls,
        task8_replay.matched_ablation_outcomes,
    ):
        verified_construction = _verify_construction_outcome(construction)
        if verified_construction.pair is None:
            raise Task11PrerequisiteUnresolved(
                f"Task-11 {control_id} matched construction is undefined"
            )
        pair = verified_construction.pair
        if control.factory is not pair.actual:
            raise ValueError(
                f"Task-11 {control_id} registry lost canonical actual identity"
            )
        actual_authority = issue_synthetic_prestructure_authority(
            parent,
            registry,
            control_id,
            verified_construction,
            "actual",
        )
        ablated_authority = issue_synthetic_prestructure_authority(
            parent,
            registry,
            control_id,
            verified_construction,
            "matched_ablated",
        )
        actual_transition, actual_certificate = _certify_task11_branch(
            pair.actual,
            actual_authority,
            runtime_manifest,
        )
        ablated_transition, ablated_certificate = _certify_task11_branch(
            pair.ablated,
            ablated_authority,
            runtime_manifest,
        )
        qualification = qualify_ablation_from_certificate(
            verified_construction,
            ablated_certificate,
        )
        if not qualification.outcome.status.defined:
            raise Task11PrerequisiteUnresolved(
                f"Task-11 {control_id} certificate-backed qualification failed"
            )
        result.append(
            _Task11ControlDynamics(
                control_id=control_id,
                construction=verified_construction,
                actual_factory=pair.actual,
                ablated_factory=pair.ablated,
                actual_transition=actual_transition,
                ablated_transition=ablated_transition,
                actual_certificate=actual_certificate,
                ablated_certificate=ablated_certificate,
                qualification=qualification,
            )
        )
    return tuple(result)


def _run_control_response_order(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    chain: _Task11ControlDynamics,
    order: int,
) -> ControlCandidateOutcome:
    run_spec = build_response_run_spec(
        protocol,
        chain.actual_transition,
        chain.actual_certificate,
        chain.control_id,
        order,
    )
    reference_capability = build_endpoint_reference(
        registry,
        protocol,
        chain.actual_factory,
        chain.actual_transition,
        chain.actual_certificate,
        chain.control_id,
        order,
    )
    reference = reference_capability.outcome
    shell = None
    paired = None
    failure = None
    if not reference.status.defined:
        failure = ControlCandidateFailure.REFERENCE_FAILED
    else:
        shell_spec = build_endpoint_shell_spec(protocol, reference_capability)
        shell_capability = build_endpoint_shell(
            registry,
            protocol,
            reference_capability,
            chain.actual_factory,
            chain.actual_transition,
            chain.actual_certificate,
            shell_spec,
        )
        shell = shell_capability.outcome
        if not shell.status.defined:
            failure = ControlCandidateFailure.SHELL_FAILED
        else:
            paired_capability = build_paired_filtered_response(
                registry,
                protocol,
                chain.qualification,
                chain.actual_transition,
                chain.ablated_transition,
                chain.actual_certificate,
                chain.ablated_certificate,
                run_spec,
                shell_capability,
            )
            paired = paired_capability.outcome
            if not paired.status.defined:
                failure = (
                    ControlCandidateFailure.BRIDGE_FAILED
                    if paired.failure
                    in (
                        PairedResponseFailure.ACTUAL_BRIDGE_FAILED,
                        PairedResponseFailure.ABLATED_BRIDGE_FAILED,
                    )
                    else ControlCandidateFailure.RESPONSE_FAILED
                )
    provisional_attempt = CandidateAttemptAudit(
        attempt_schema_version=CANDIDATE_ATTEMPT_AUDIT_SCHEMA_VERSION,
        control_registry_entry_sha=run_spec.control_registry_entry_sha,
        fejer_order=order,
        reference_outcome=reference,
        shell_outcome=shell,
        paired_response_outcome=paired,
        attempt_sha="0" * 64,
    )
    attempt = replace(
        provisional_attempt,
        attempt_sha=canonical_sha(
            candidate_attempt_audit_payload(provisional_attempt)
        ),
    )
    provisional_outcome = ControlCandidateOutcome(
        status=(
            BlockStatus(True, None)
            if failure is None
            else BlockStatus(False, control_candidate_failure_reason(failure))
        ),
        failure=failure,
        run_spec=run_spec,
        attempt_audit=attempt,
        outcome_sha="0" * 64,
    )
    return replace(
        provisional_outcome,
        outcome_sha=canonical_sha(
            control_candidate_outcome_payload(provisional_outcome)
        ),
    )


def _branch_spectrum(
    *,
    branch: Literal["actual", "matched_ablated"],
    values,
    readout_kind: Literal["h", "curv"],
    entry: ControlRegistryEntry,
    declared_rank: int,
) -> BranchSpectrumAudit:
    shape, raw = _expected_spectrum_values(
        values,
        readout_kind,
        entry.readout_calibration_spec,
    )
    n_singular = shape[1]
    rows = tuple(
        raw[index : index + n_singular]
        for index in range(0, len(raw), n_singular)
    )
    active = tuple(value for row in rows for value in row[:declared_rank])
    inactive = tuple(value for row in rows for value in row[declared_rank:])
    provisional = BranchSpectrumAudit(
        branch=branch,
        declared_rank=declared_rank,
        spectrum_shape=shape,
        spectrum_order_id="k-major-singular-descending-v1",
        raw_spectrum=raw,
        active_min=None if not active else float(min(active)),
        inactive_max=None if not inactive else float(max(inactive)),
        branch_sha="0" * 64,
    )
    return replace(
        provisional,
        branch_sha=canonical_sha(branch_spectrum_audit_payload(provisional)),
    )


def _readout_spectrum(
    *,
    outcome: ControlCandidateOutcome,
    entry: ControlRegistryEntry,
    declaration,
    readout_kind: Literal["h", "curv"],
) -> PerControlReadoutSpectrumAudit:
    paired_outcome = outcome.attempt_audit.paired_response_outcome
    if (
        paired_outcome is None
        or not paired_outcome.status.defined
        or paired_outcome.paired_response is None
    ):
        raise ValueError("Task-11 spectrum requires a successful paired response")
    paired = paired_outcome.paired_response
    actual_rank, ablated_rank = (
        (
            declaration.expected_h_actual_rank,
            declaration.expected_h_ablated_rank,
        )
        if readout_kind == "h"
        else (
            declaration.expected_curv_actual_rank,
            declaration.expected_curv_ablated_rank,
        )
    )
    actual = _branch_spectrum(
        branch="actual",
        values=paired.actual.values,
        readout_kind=readout_kind,
        entry=entry,
        declared_rank=actual_rank,
    )
    ablated = _branch_spectrum(
        branch="matched_ablated",
        values=paired.ablated.values,
        readout_kind=readout_kind,
        entry=entry,
        declared_rank=ablated_rank,
    )
    actual_bridge, ablated_bridge = (
        (
            paired.actual.bridge_audit.h_operator_error_max,
            paired.ablated.bridge_audit.h_operator_error_max,
        )
        if readout_kind == "h"
        else (
            paired.actual.bridge_audit.curv_operator_error_max,
            paired.ablated.bridge_audit.curv_operator_error_max,
        )
    )
    provisional = PerControlReadoutSpectrumAudit(
        readout_kind=readout_kind,
        control_registry_entry_sha=entry.entry_sha,
        expected_rank_declaration_sha=declaration.declaration_sha,
        fejer_order=outcome.run_spec.fejer_order,
        run_spec_sha=outcome.run_spec.spec_sha,
        paired_response_sha=paired.pair_sha,
        actual=actual,
        ablated=ablated,
        actual_bridge_operator_error_upper=float(actual_bridge),
        ablated_bridge_operator_error_upper=float(ablated_bridge),
        audit_sha="0" * 64,
    )
    return replace(
        provisional,
        audit_sha=canonical_sha(
            per_control_readout_spectrum_audit_payload(provisional)
        ),
    )


def _build_control_candidate_audit(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    entry: ControlRegistryEntry,
    chain: _Task11ControlDynamics,
    order: int,
) -> ControlCandidateAudit:
    declaration = issue_expected_rank_declaration(registry, chain.control_id)
    candidate = _run_control_response_order(registry, protocol, chain, order)
    comparison = _run_control_response_order(
        registry,
        protocol,
        chain,
        2 * order,
    )
    spectra = ()
    comparison_spectra = ()
    phase_separation = None
    overlap_margin = None
    projector_distance = None
    passed = False
    if candidate.status.defined and comparison.status.defined:
        spectra = tuple(
            _readout_spectrum(
                outcome=candidate,
                entry=entry,
                declaration=declaration,
                readout_kind=kind,
            )
            for kind in ("h", "curv")
        )
        comparison_spectra = tuple(
            _readout_spectrum(
                outcome=comparison,
                entry=entry,
                declaration=declaration,
                readout_kind=kind,
            )
            for kind in ("h", "curv")
        )
        phase_separation, overlap_margin, projector_distance = (
            _shell_comparison_values(candidate, comparison)
        )
        bridge_signal_passed = all(
            branch.active_min is None or branch.active_min > bridge
            for spectrum in (*spectra, *comparison_spectra)
            for branch, bridge in (
                (
                    spectrum.actual,
                    spectrum.actual_bridge_operator_error_upper,
                ),
                (
                    spectrum.ablated,
                    spectrum.ablated_bridge_operator_error_upper,
                ),
            )
        )
        passed = bridge_signal_passed and verify_window_comparison_gates(
            order=order,
            phase_separation=phase_separation,
            overlap_margin=overlap_margin,
            projector_t2t_distance=projector_distance,
        )
    provisional = ControlCandidateAudit(
        control_registry_entry=entry,
        expected_rank_declaration=declaration,
        candidate_t=candidate,
        comparison_2t=comparison,
        readout_spectrum_audits=spectra,
        comparison_2t_readout_spectrum_audits=comparison_spectra,
        phase_separation=phase_separation,
        overlap_margin=overlap_margin,
        projector_t2t_distance=projector_distance,
        passed=passed,
        audit_sha="0" * 64,
    )
    return replace(
        provisional,
        audit_sha=canonical_sha(control_candidate_audit_payload(provisional)),
    )


def _build_window_candidate_audit(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    chains: tuple[_Task11ControlDynamics, ...],
    order: int,
) -> WindowCandidateAudit:
    entries = registry.registry.entries
    controls = tuple(
        _build_control_candidate_audit(
            registry,
            protocol,
            entry,
            chain,
            order,
        )
        for entry, chain in zip(entries, chains)
    )
    reached_spectra = all(
        item.candidate_t.status.defined and item.comparison_2t.status.defined
        for item in controls
    )
    aggregates = (
        compute_window_readout_calibration_audits(registry, controls)
        if reached_spectra
        else ()
    )
    passed = (
        reached_spectra
        and all(item.passed for item in controls)
        and all(
            item.absolute_signal_gate_passed
            and item.relative_gap_gate_passed
            for item in aggregates
        )
    )
    provisional = WindowCandidateAudit(
        fejer_order=order,
        control_audits=controls,
        readout_aggregate_audits=aggregates,
        passed=passed,
        audit_sha="0" * 64,
    )
    return replace(
        provisional,
        audit_sha=canonical_sha(window_candidate_audit_payload(provisional)),
    )


def _run_task11_window_calibration_from_replay(
    parent: VerifiedParentFreeze,
    task8_replay: CurrentTask8ControlReplay,
    current_registry: CurrentControlRegistryV2,
    current_window: CurrentWindowCalibrationProtocolV2,
) -> WindowCalibrationOutcome:
    """Numerical body helper; raw replay values carry no authority semantics."""

    if type(parent) is not VerifiedParentFreeze:
        raise TypeError("Task-11 runner requires the exact historical Parent")
    if type(task8_replay) is not CurrentTask8ControlReplay:
        raise TypeError("Task-11 runner requires an exact Task-8 replay")
    if type(current_registry) is not CurrentControlRegistryV2:
        raise TypeError("Task-11 runner requires an exact current registry body")
    if type(current_window) is not CurrentWindowCalibrationProtocolV2:
        raise TypeError("Task-11 runner requires an exact current window body")
    with _scoped_replay_context():
        registry, protocol = _build_task11_numerical_roots(
            parent,
            task8_replay,
            current_registry,
            current_window,
        )
        chains = _build_task11_dynamics_chains(
            parent,
            task8_replay,
            registry,
        )
        candidates = tuple(
            _build_window_candidate_audit(
                registry,
                protocol,
                chains,
                order,
            )
            for order in T_CANDIDATES
        )
        return calibrate_window_and_thresholds(
            registry,
            protocol,
            candidates,
        )


def _historical_parent_from_task8_replay(
    replay: CurrentTask8ControlReplay,
) -> VerifiedParentFreeze:
    if type(replay) is not CurrentTask8ControlReplay:
        raise TypeError("Task-11 current-window replay returned the wrong type")
    parent = _reverify_verified_control_registry(replay.legacy_registry).parent
    if type(parent) is not VerifiedParentFreeze:
        raise TypeError("Task-11 replay lost its historical Parent capability")
    return parent


def _make_public_task11_runner(
    *,
    window_type: type,
    window_replayer,
    parent_resolver,
    numerical_executor,
):
    """Capture the sole live provenance route into the numerical body helper."""

    def run_task11_window_calibration(
        current_window: VerifiedCurrentWindowCalibrationProtocolV2,
    ) -> WindowCalibrationOutcome:
        if type(current_window) is not window_type:
            raise TypeError(
                "Task-11 runner requires an exact live current-window capability"
            )
        protocol, current_registry, task8_replay = window_replayer(
            current_window
        )
        parent = parent_resolver(task8_replay)
        return numerical_executor(
            parent,
            task8_replay,
            current_registry,
            protocol,
        )

    return freeze_rulespace_call_graph(run_task11_window_calibration)


run_task11_window_calibration = _make_public_task11_runner(
    window_type=VerifiedCurrentWindowCalibrationProtocolV2,
    # The replay bridge is already independently frozen.  Its bound call
    # wrapper composes that sealed graph without recursively re-freezing the
    # guard's private class snapshots.
    window_replayer=_replay_current_window_calibration_protocol_v2.__call__,
    parent_resolver=_historical_parent_from_task8_replay,
    numerical_executor=_run_task11_window_calibration_from_replay,
)


__all__ = [
    "Task11PrerequisiteUnresolved",
    "run_task11_window_calibration",
]
