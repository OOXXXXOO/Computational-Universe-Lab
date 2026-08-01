"""Non-authoritative evidence envelope for the expensive Task-11 raw replay.

This module deliberately operates on the canonical JSON payload of a
``WindowCalibrationOutcome``.  Its SHA is an integrity checksum, not an
authority seal.  In particular, none of the builders below can issue a
current-Parent-v2 calibration capability or a scientific PASS/FAIL verdict.
"""

from __future__ import annotations

import json
import re
from typing import Mapping

from .evidence import canonical_sha
from .registry import CONTROL_ORDER
from .thresholds import T_CANDIDATES


TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION = "v3m0.task11-raw-replay-evidence.v1"
TASK11_RAW_REPLAY_AUTHORITY_STATE = (
    "RAW_HISTORICAL_PARENT_REPLAY_NO_CURRENT_V2_AUTHORITY"
)
TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT = "NOT_ISSUED"
TASK11_RAW_REPLAY_SCOPE = (
    "HISTORICAL_PARENT_V1_NUMERICAL_REPLAY_WITH_TEST_ONLY_V2_SHA_PLACEHOLDER"
)
TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA = "a" * 64
TASK11_RAW_REPLAY_CREATE_POLICY = "CREATE_ONLY"
TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS = (
    "experiments/v3m0_task11_raw_replay.py",
    "rulespace_v3/calibration_authority.py",
    "rulespace_v3/current_window_replay.py",
    "rulespace_v3/evidence.py",
    "rulespace_v3/frozen_call_graph.py",
    "rulespace_v3/parent_freeze.py",
    "rulespace_v3/parent_freeze_v2.py",
    "rulespace_v3/registry.py",
    "rulespace_v3/replay_scope.py",
    "rulespace_v3/response.py",
    "rulespace_v3/runtime.py",
    "rulespace_v3/task11_evidence.py",
    "rulespace_v3/task11_runner.py",
    "rulespace_v3/task8_control_replay.py",
    "rulespace_v3/thresholds.py",
)
_ENGINEERING_SCOPE = "SIX_T_THREE_CONTROL_INDEPENDENT_2T_RAW_REPLAY"
_CLAIM_SCOPE = (
    "ENGINEERING_REPLAY_EVIDENCE_ONLY; NOT A TASK11-V2 AUTHORITY OR "
    "SCIENTIFIC PASS/FAIL"
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_GIT_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_EVIDENCE_FIELDS = frozenset(
    (
        "evidence_schema_version",
        "authority_state",
        "scientific_verdict",
        "current_parent_v2_bound",
        "create_policy",
        "engineering_contract_scope",
        "claim_scope",
        "provenance",
        "outcome",
        "outcome_sha",
        "summary",
        "evidence_sha",
    )
)
_PROVENANCE_FIELDS = frozenset(
    (
        "replay_scope",
        "historical_parent_v1_sha",
        "placeholder_parent_freeze_v2_sha",
        "legacy_registry_sha",
        "current_control_registry_sha",
        "legacy_window_protocol_sha",
        "current_window_protocol_sha",
        "scenario_authority_shas",
        "git_head",
        "git_worktree_dirty",
        "source_files",
        "runtime_manifest",
        "command",
    )
)
_RUNTIME_MANIFEST_FIELDS = frozenset(
    (
        "runtime_schema_version",
        "evaluator_id",
        "source_closure",
        "python_version",
        "numpy_version",
        "scipy_version",
        "blas_config_sha",
        "lapack_config_sha",
        "platform_id",
        "runtime_manifest_sha",
    )
)
_AGGREGATE_FIELDS = (
    "readout_kind",
    "scale_ref",
    "null_max",
    "bridge_operator_error_max",
    "noise_ref",
    "signal_min",
    "tau_sig",
    "signal_noise_ratio",
    "raw_relative_gap",
    "absolute_signal_gate_passed",
    "relative_gap_gate_passed",
    "aggregate_sha",
)


def _json_clone(value: object, field: str) -> object:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be finite plain JSON") from exc
    return json.loads(encoded)


def _plain_dict(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise TypeError(f"{field} must be a plain dict")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{field} keys must be exact strings")
    return value


def _plain_list(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise TypeError(f"{field} must be a plain list")
    return value


def _exact_fields(
    value: dict[str, object], expected: frozenset[str], field: str
) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{field} schema mismatch; "
            f"unknown={sorted(observed - expected)}, "
            f"missing={sorted(expected - observed)}"
        )


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _LOWER_SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be a non-empty exact string")
    return value


def _git_object_id(value: object, field: str) -> str:
    if type(value) is not str or _GIT_OBJECT_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase Git object ID")
    return value


def _status_summary(value: object, field: str) -> dict[str, object]:
    status = _plain_dict(value, field)
    _exact_fields(status, frozenset(("defined", "reason")), field)
    defined = status["defined"]
    reason = status["reason"]
    if type(defined) is not bool:
        raise TypeError(f"{field}.defined must be an exact bool")
    if defined:
        if reason is not None:
            raise ValueError(f"{field}.reason must be null when defined")
    elif type(reason) is not str or not reason:
        raise ValueError(f"{field}.reason must name the undefined reason")
    return {"defined": defined, "reason": reason}


def _optional_hash(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _sha(value, field)


def _mapping_value(value: dict[str, object], key: str, field: str) -> dict[str, object]:
    return _plain_dict(value.get(key), f"{field}.{key}")


def _attempt_summary(
    value: object,
    *,
    expected_order: int,
    field: str,
) -> dict[str, object]:
    attempt = _plain_dict(value, field)
    status = _status_summary(attempt.get("status"), f"{field}.status")
    failure = attempt.get("failure")
    if failure is not None:
        _text(failure, f"{field}.failure")
    run_spec = _mapping_value(attempt, "run_spec", field)
    order = run_spec.get("fejer_order")
    if type(order) is not int or order != expected_order:
        raise ValueError(f"{field} does not retain the required T/2T order")
    run_spec_sha = _sha(run_spec.get("spec_sha"), f"{field}.run_spec.spec_sha")
    audit = _mapping_value(attempt, "attempt_audit", field)
    attempt_sha = _sha(audit.get("attempt_sha"), f"{field}.attempt_audit.attempt_sha")

    shell_outcome = audit.get("shell_outcome")
    shell_outcome_sha = None
    shell_manifest_sha = None
    if shell_outcome is not None:
        shell = _plain_dict(shell_outcome, f"{field}.shell_outcome")
        shell_outcome_sha = _sha(
            shell.get("outcome_sha"), f"{field}.shell_outcome.outcome_sha"
        )
        shell_manifest = shell.get("shell")
        if shell_manifest is not None:
            shell_manifest_body = _plain_dict(
                shell_manifest, f"{field}.shell_outcome.shell"
            )
            shell_manifest_sha = _sha(
                shell_manifest_body.get("shell_manifest_sha"),
                f"{field}.shell_outcome.shell.shell_manifest_sha",
            )

    paired_outcome = audit.get("paired_response_outcome")
    paired_outcome_sha = None
    paired_response_sha = None
    if paired_outcome is not None:
        paired = _plain_dict(paired_outcome, f"{field}.paired_response_outcome")
        _status_summary(paired.get("status"), f"{field}.paired_response_outcome.status")
        paired_outcome_sha = _sha(
            paired.get("outcome_sha"),
            f"{field}.paired_response_outcome.outcome_sha",
        )
        paired_response = paired.get("paired_response")
        if paired_response is not None:
            pair = _plain_dict(
                paired_response,
                f"{field}.paired_response_outcome.paired_response",
            )
            paired_response_sha = _sha(
                pair.get("pair_sha"),
                f"{field}.paired_response_outcome.paired_response.pair_sha",
            )

    return {
        "status": status,
        "failure": failure,
        "fejer_order": order,
        "run_spec_sha": run_spec_sha,
        "attempt_sha": attempt_sha,
        "shell_outcome_sha": shell_outcome_sha,
        "shell_manifest_sha": shell_manifest_sha,
        "paired_response_outcome_sha": paired_outcome_sha,
        "paired_response_sha": paired_response_sha,
        "outcome_sha": _sha(attempt.get("outcome_sha"), f"{field}.outcome_sha"),
    }


def _gate_number(value: object, field: str) -> float | None:
    if value is None:
        return None
    if type(value) is not float:
        raise TypeError(f"{field} must be an exact float or null")
    return value


def _aggregate_summary(value: object, field: str) -> dict[str, object]:
    aggregate = _plain_dict(value, field)
    result: dict[str, object] = {}
    for name in _AGGREGATE_FIELDS:
        if name not in aggregate:
            raise ValueError(f"{field}.{name} is missing")
        result[name] = aggregate[name]
    if result["readout_kind"] not in ("h", "curv"):
        raise ValueError(f"{field}.readout_kind is not closed")
    for name in (
        "scale_ref",
        "bridge_operator_error_max",
        "noise_ref",
        "signal_min",
        "tau_sig",
        "signal_noise_ratio",
        "raw_relative_gap",
    ):
        if type(result[name]) is not float:
            raise TypeError(f"{field}.{name} must be an exact float")
    _gate_number(result["null_max"], f"{field}.null_max")
    for name in ("absolute_signal_gate_passed", "relative_gap_gate_passed"):
        if type(result[name]) is not bool:
            raise TypeError(f"{field}.{name} must be an exact bool")
    _sha(result["aggregate_sha"], f"{field}.aggregate_sha")
    return result


def summarize_task11_outcome_payload(
    outcome_payload: Mapping[str, object],
) -> dict[str, object]:
    """Return a compact, complete gate index for one canonical raw outcome."""

    cloned = _json_clone(outcome_payload, "Task-11 outcome payload")
    outcome = _plain_dict(cloned, "Task-11 outcome payload")
    _exact_fields(
        outcome,
        frozenset(("status", "manifest", "selection")),
        "Task-11 outcome payload",
    )
    status = _status_summary(outcome["status"], "outcome.status")
    selection = outcome["selection"]
    if status["defined"]:
        selection_summary = _plain_dict(selection, "outcome.selection")
    else:
        if status["reason"] != "window_unresolved":
            raise ValueError("raw unresolved outcome has the wrong reason")
        if selection is not None:
            raise ValueError("raw unresolved outcome must not contain a selection")
        selection_summary = None

    manifest = _plain_dict(outcome["manifest"], "outcome.manifest")
    candidates = _plain_list(
        manifest.get("candidate_audits"), "outcome.manifest.candidate_audits"
    )
    if len(candidates) != len(T_CANDIDATES):
        raise ValueError("raw outcome must retain all six Task-11 orders")
    order_summaries: list[dict[str, object]] = []
    passing_orders: list[int] = []
    for candidate_index, (candidate_value, order) in enumerate(
        zip(candidates, T_CANDIDATES)
    ):
        field = f"outcome.manifest.candidate_audits[{candidate_index}]"
        candidate = _plain_dict(candidate_value, field)
        observed_order = candidate.get("fejer_order")
        if type(observed_order) is not int or observed_order != order:
            raise ValueError("raw candidate order table differs from T_CANDIDATES")
        passed = candidate.get("passed")
        if type(passed) is not bool:
            raise TypeError(f"{field}.passed must be an exact bool")
        if passed:
            passing_orders.append(order)
        controls = _plain_list(
            candidate.get("control_audits"), f"{field}.control_audits"
        )
        if len(controls) != len(CONTROL_ORDER):
            raise ValueError(f"{field} must retain all three controls")
        control_summaries: list[dict[str, object]] = []
        for control_index, (control_value, control_id) in enumerate(
            zip(controls, CONTROL_ORDER)
        ):
            control_field = f"{field}.control_audits[{control_index}]"
            control = _plain_dict(control_value, control_field)
            entry = _mapping_value(control, "control_registry_entry", control_field)
            if entry.get("control_id") != control_id:
                raise ValueError(f"{control_field} control order drifted")
            control_passed = control.get("passed")
            if type(control_passed) is not bool:
                raise TypeError(f"{control_field}.passed must be an exact bool")
            control_summaries.append(
                {
                    "control_id": control_id,
                    "control_registry_entry_sha": _sha(
                        entry.get("entry_sha"),
                        f"{control_field}.control_registry_entry.entry_sha",
                    ),
                    "candidate_t": _attempt_summary(
                        control.get("candidate_t"),
                        expected_order=order,
                        field=f"{control_field}.candidate_t",
                    ),
                    "comparison_2t": _attempt_summary(
                        control.get("comparison_2t"),
                        expected_order=2 * order,
                        field=f"{control_field}.comparison_2t",
                    ),
                    "gate_metrics": {
                        "phase_separation": _gate_number(
                            control.get("phase_separation"),
                            f"{control_field}.phase_separation",
                        ),
                        "overlap_margin": _gate_number(
                            control.get("overlap_margin"),
                            f"{control_field}.overlap_margin",
                        ),
                        "projector_t2t_distance": _gate_number(
                            control.get("projector_t2t_distance"),
                            f"{control_field}.projector_t2t_distance",
                        ),
                    },
                    "passed": control_passed,
                    "audit_sha": _sha(
                        control.get("audit_sha"), f"{control_field}.audit_sha"
                    ),
                }
            )
        aggregates = _plain_list(
            candidate.get("readout_aggregate_audits"),
            f"{field}.readout_aggregate_audits",
        )
        if aggregates and len(aggregates) != 2:
            raise ValueError(f"{field} aggregate gates must be empty or h/curv")
        aggregate_summaries = [
            _aggregate_summary(item, f"{field}.readout_aggregate_audits[{index}]")
            for index, item in enumerate(aggregates)
        ]
        if aggregate_summaries and tuple(
            item["readout_kind"] for item in aggregate_summaries
        ) != ("h", "curv"):
            raise ValueError(f"{field} aggregate gate order is not h/curv")
        order_summaries.append(
            {
                "fejer_order": order,
                "controls": control_summaries,
                "aggregate_gates": aggregate_summaries,
                "passed": passed,
                "audit_sha": _sha(candidate.get("audit_sha"), f"{field}.audit_sha"),
            }
        )

    if status["defined"]:
        assert selection_summary is not None
        selected_order = selection_summary.get("selected_fejer_order")
        if (
            type(selected_order) is not int
            or not passing_orders
            or selected_order != passing_orders[0]
        ):
            raise ValueError("selection does not name the first passing order")
    elif passing_orders:
        raise ValueError("unresolved outcome contains a passing candidate")

    return {
        "outcome_status": status,
        "selection": selection_summary,
        "orders": order_summaries,
    }


def _validated_provenance(value: object) -> dict[str, object]:
    cloned = _json_clone(value, "Task-11 raw replay provenance")
    provenance = _plain_dict(cloned, "Task-11 raw replay provenance")
    _exact_fields(provenance, _PROVENANCE_FIELDS, "Task-11 raw replay provenance")
    if provenance["replay_scope"] != TASK11_RAW_REPLAY_SCOPE:
        raise ValueError("raw replay scope is not frozen")
    for name in (
        "historical_parent_v1_sha",
        "placeholder_parent_freeze_v2_sha",
        "legacy_registry_sha",
        "current_control_registry_sha",
        "legacy_window_protocol_sha",
        "current_window_protocol_sha",
    ):
        _sha(provenance[name], f"provenance.{name}")
    _git_object_id(provenance["git_head"], "provenance.git_head")
    if (
        provenance["placeholder_parent_freeze_v2_sha"]
        != TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA
    ):
        raise ValueError("raw replay must disclose the exact Parent-v2 placeholder")
    if type(provenance["git_worktree_dirty"]) is not bool:
        raise TypeError("provenance.git_worktree_dirty must be an exact bool")
    scenario_shas = _plain_list(
        provenance["scenario_authority_shas"],
        "provenance.scenario_authority_shas",
    )
    if len(scenario_shas) != len(CONTROL_ORDER):
        raise ValueError("provenance must retain three scenario authority SHAs")
    for index, value in enumerate(scenario_shas):
        _sha(value, f"provenance.scenario_authority_shas[{index}]")
    source_files = _plain_list(provenance["source_files"], "provenance.source_files")
    if not source_files:
        raise ValueError("provenance.source_files must be non-empty")
    paths = []
    for index, item in enumerate(source_files):
        source = _plain_dict(item, f"provenance.source_files[{index}]")
        _exact_fields(
            source,
            frozenset(("relative_path", "sha256")),
            f"provenance.source_files[{index}]",
        )
        paths.append(_text(source["relative_path"], "source relative_path"))
        _sha(source["sha256"], "source sha256")
    if len(paths) != len(set(paths)):
        raise ValueError("provenance.source_files contains duplicate paths")
    if frozenset(paths) != frozenset(TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS):
        raise ValueError(
            "provenance.source_files does not bind the frozen Task-11 closure"
        )
    runtime = _plain_dict(provenance["runtime_manifest"], "provenance.runtime_manifest")
    _exact_fields(
        runtime,
        _RUNTIME_MANIFEST_FIELDS,
        "provenance.runtime_manifest",
    )
    for name in (
        "runtime_schema_version",
        "evaluator_id",
        "python_version",
        "numpy_version",
        "scipy_version",
        "platform_id",
    ):
        _text(runtime[name], f"provenance.runtime_manifest.{name}")
    for name in (
        "blas_config_sha",
        "lapack_config_sha",
        "runtime_manifest_sha",
    ):
        _sha(runtime[name], f"provenance.runtime_manifest.{name}")
    closure = _plain_list(
        runtime["source_closure"],
        "provenance.runtime_manifest.source_closure",
    )
    if not closure:
        raise ValueError("runtime source closure must be non-empty")
    closure_paths = []
    for index, item in enumerate(closure):
        entry = _plain_dict(
            item,
            f"provenance.runtime_manifest.source_closure[{index}]",
        )
        _exact_fields(
            entry,
            frozenset(("relative_path", "sha256")),
            f"provenance.runtime_manifest.source_closure[{index}]",
        )
        closure_paths.append(
            _text(entry["relative_path"], "runtime source relative_path")
        )
        _sha(entry["sha256"], "runtime source sha256")
    if len(closure_paths) != len(set(closure_paths)):
        raise ValueError("runtime source closure contains duplicate paths")
    runtime_body = {
        key: item for key, item in runtime.items() if key != "runtime_manifest_sha"
    }
    if canonical_sha(runtime_body) != runtime["runtime_manifest_sha"]:
        raise ValueError("runtime manifest SHA does not match its complete body")
    command = _plain_list(provenance["command"], "provenance.command")
    if not command:
        raise ValueError("provenance.command must be non-empty")
    for index, item in enumerate(command):
        _text(item, f"provenance.command[{index}]")
    return provenance


def build_task11_raw_replay_evidence_payload(
    outcome_payload: Mapping[str, object],
    *,
    outcome_sha: str,
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Wrap one raw outcome without promoting it to current-v2 authority."""

    outcome = _json_clone(outcome_payload, "Task-11 outcome payload")
    outcome_body = _plain_dict(outcome, "Task-11 outcome payload")
    observed_outcome_sha = _sha(outcome_sha, "outcome_sha")
    if canonical_sha(outcome_body) != observed_outcome_sha:
        raise ValueError("Task-11 raw outcome SHA does not match its complete body")
    summary = summarize_task11_outcome_payload(outcome_body)
    provenance_body = _validated_provenance(provenance)
    manifest = _mapping_value(outcome_body, "manifest", "outcome")
    registry = _mapping_value(manifest, "control_registry", "outcome.manifest")
    protocol = _mapping_value(manifest, "window_protocol", "outcome.manifest")
    if registry.get("registry_sha") != provenance_body["legacy_registry_sha"]:
        raise ValueError("raw outcome registry SHA differs from provenance")
    if protocol.get("protocol_sha") != provenance_body["legacy_window_protocol_sha"]:
        raise ValueError("raw outcome window SHA differs from provenance")

    body: dict[str, object] = {
        "evidence_schema_version": TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION,
        "authority_state": TASK11_RAW_REPLAY_AUTHORITY_STATE,
        "scientific_verdict": TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT,
        "current_parent_v2_bound": False,
        "create_policy": TASK11_RAW_REPLAY_CREATE_POLICY,
        "engineering_contract_scope": _ENGINEERING_SCOPE,
        "claim_scope": _CLAIM_SCOPE,
        "provenance": provenance_body,
        "outcome": outcome_body,
        "outcome_sha": observed_outcome_sha,
        "summary": summary,
    }
    return {**body, "evidence_sha": canonical_sha(body)}


def verify_task11_raw_replay_evidence_payload(
    evidence_payload: Mapping[str, object],
) -> dict[str, object]:
    """Verify integrity and non-authority labels; never hydrate a capability."""

    cloned = _json_clone(evidence_payload, "Task-11 raw replay evidence")
    evidence = _plain_dict(cloned, "Task-11 raw replay evidence")
    _exact_fields(evidence, _EVIDENCE_FIELDS, "Task-11 raw replay evidence")
    expected_constants = {
        "evidence_schema_version": TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION,
        "authority_state": TASK11_RAW_REPLAY_AUTHORITY_STATE,
        "scientific_verdict": TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT,
        "current_parent_v2_bound": False,
        "create_policy": TASK11_RAW_REPLAY_CREATE_POLICY,
        "engineering_contract_scope": _ENGINEERING_SCOPE,
        "claim_scope": _CLAIM_SCOPE,
    }
    for name, expected in expected_constants.items():
        if evidence[name] != expected or type(evidence[name]) is not type(expected):
            raise ValueError(f"Task-11 raw evidence {name} drifted")
    outcome = _plain_dict(evidence["outcome"], "evidence.outcome")
    outcome_sha = _sha(evidence["outcome_sha"], "evidence.outcome_sha")
    if canonical_sha(outcome) != outcome_sha:
        raise ValueError("Task-11 raw outcome SHA does not match its complete body")
    provenance = _validated_provenance(evidence["provenance"])
    expected_summary = summarize_task11_outcome_payload(outcome)
    if evidence["summary"] != expected_summary:
        raise ValueError("Task-11 raw evidence summary differs from its outcome")
    manifest = _mapping_value(outcome, "manifest", "evidence.outcome")
    registry = _mapping_value(manifest, "control_registry", "evidence.outcome.manifest")
    protocol = _mapping_value(manifest, "window_protocol", "evidence.outcome.manifest")
    if registry.get("registry_sha") != provenance["legacy_registry_sha"]:
        raise ValueError("raw outcome registry SHA differs from provenance")
    if protocol.get("protocol_sha") != provenance["legacy_window_protocol_sha"]:
        raise ValueError("raw outcome window SHA differs from provenance")
    evidence_sha = _sha(evidence["evidence_sha"], "evidence.evidence_sha")
    body = {key: value for key, value in evidence.items() if key != "evidence_sha"}
    if canonical_sha(body) != evidence_sha:
        raise ValueError("Task-11 raw evidence SHA does not match its complete body")
    return evidence


__all__ = [
    "TASK11_RAW_REPLAY_AUTHORITY_STATE",
    "TASK11_RAW_REPLAY_CREATE_POLICY",
    "TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION",
    "TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA",
    "TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS",
    "TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT",
    "TASK11_RAW_REPLAY_SCOPE",
    "build_task11_raw_replay_evidence_payload",
    "summarize_task11_outcome_payload",
    "verify_task11_raw_replay_evidence_payload",
]
