from __future__ import annotations

import dataclasses as _dataclasses
import hashlib as _hashlib
import json as _json

from .common import B7LabMutationRejected


ROUTE_ID = "C_UNION"
WIRE_SCHEMA_ID = "experimental.v3m0.b7.c-union.wire.v1"


@_dataclasses.dataclass(frozen=True)
class _ReferenceFailure:
    transcript_schema_version: str
    corpus_spec_sha: str
    case_id: str
    environment_manifest_sha: str
    provenance_fixture: object
    response_run_spec_fixture: object
    reference_outcome: object
    trace_items: object
    digest_items: object
    experimental_sha: str


@_dataclasses.dataclass(frozen=True)
class _ShellFailure:
    transcript_schema_version: str
    corpus_spec_sha: str
    case_id: str
    environment_manifest_sha: str
    provenance_fixture: object
    response_run_spec_fixture: object
    reference_outcome: object
    trace_items: object
    digest_items: object
    experimental_sha: str
    shell_outcome: object


@_dataclasses.dataclass(frozen=True)
class _ActualResponseValuesFailure:
    transcript_schema_version: str
    corpus_spec_sha: str
    case_id: str
    environment_manifest_sha: str
    provenance_fixture: object
    response_run_spec_fixture: object
    reference_outcome: object
    trace_items: object
    digest_items: object
    experimental_sha: str
    shell_outcome: object
    actual_branch_attempt_core: object


@_dataclasses.dataclass(frozen=True)
class _MatchedResponseValuesFailure:
    transcript_schema_version: str
    corpus_spec_sha: str
    case_id: str
    environment_manifest_sha: str
    provenance_fixture: object
    response_run_spec_fixture: object
    reference_outcome: object
    trace_items: object
    digest_items: object
    experimental_sha: str
    shell_outcome: object
    actual_branch_attempt_core: object
    actual_response_values: object
    matched_ablated_branch_attempt_core: object


@_dataclasses.dataclass(frozen=True)
class _ActualBridgeFailure:
    transcript_schema_version: str
    corpus_spec_sha: str
    case_id: str
    environment_manifest_sha: str
    provenance_fixture: object
    response_run_spec_fixture: object
    reference_outcome: object
    trace_items: object
    digest_items: object
    experimental_sha: str
    shell_outcome: object
    actual_branch_attempt_core: object
    actual_response_values: object
    matched_ablated_branch_attempt_core: object
    matched_ablated_response_values: object


@_dataclasses.dataclass(frozen=True)
class _MatchedBridgeFailure:
    transcript_schema_version: str
    corpus_spec_sha: str
    case_id: str
    environment_manifest_sha: str
    provenance_fixture: object
    response_run_spec_fixture: object
    reference_outcome: object
    trace_items: object
    digest_items: object
    experimental_sha: str
    shell_outcome: object
    actual_branch_attempt_core: object
    actual_response_values: object
    matched_ablated_branch_attempt_core: object
    matched_ablated_response_values: object
    actual_bridge_audit: object


@_dataclasses.dataclass(frozen=True)
class _Success:
    transcript_schema_version: str
    corpus_spec_sha: str
    case_id: str
    environment_manifest_sha: str
    provenance_fixture: object
    response_run_spec_fixture: object
    reference_outcome: object
    trace_items: object
    digest_items: object
    experimental_sha: str
    shell_outcome: object
    actual_branch_attempt_core: object
    actual_response_values: object
    matched_ablated_branch_attempt_core: object
    matched_ablated_response_values: object
    actual_bridge_audit: object
    matched_ablated_bridge_audit: object
    actual_completed_response: object
    matched_ablated_completed_response: object


def _reject(reason):
    raise B7LabMutationRejected(reason)


def _canonical(value):
    try:
        return bytes(
            _json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            "utf-8",
        )
    except (TypeError, ValueError, UnicodeError):
        _reject("NON_CANONICAL_JSON")


def _parse(canonical_json_utf8):
    if type(canonical_json_utf8) is not bytes:
        _reject("NON_BYTES_INPUT")

    def reject_duplicate(pairs):
        value = {}
        for name, member in pairs:
            if name in value:
                _reject("NON_CANONICAL_JSON")
            value[name] = member
        return value

    def reject_nonfinite(_constant_text):
        _reject("NON_CANONICAL_JSON")

    try:
        text = canonical_json_utf8.decode("utf-8", "strict")
        value = _json.loads(
            text,
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_nonfinite,
        )
    except B7LabMutationRejected:
        raise
    except (TypeError, ValueError, UnicodeError):
        _reject("NON_CANONICAL_JSON")
    if _canonical(value) != canonical_json_utf8:
        _reject("NON_CANONICAL_JSON")
    return value


def _sha(value):
    digest = _hashlib.sha256(_canonical(value))
    return digest.hexdigest()


def _is_sha(value):
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact_fields(value, fields):
    if type(value) is not dict:
        _reject("UNKNOWN_OR_MISSING_FIELD")
    if len(value) != len(fields) or any(name not in value for name in fields):
        _reject("UNKNOWN_OR_MISSING_FIELD")


def _require_self_hash(value, hash_field):
    if hash_field not in value or not _is_sha(value[hash_field]):
        _reject("HASH_MISMATCH")
    payload = {name: member for name, member in value.items() if name != hash_field}
    if value[hash_field] != _sha(payload):
        _reject("HASH_MISMATCH")


def _schema_self_hash(
    value,
    _declared_fields=(
        ("application_authority_schema_version", ("application_authority_sha",)),
        ("attempt_schema_version", ("attempt_sha",)),
        ("audit_schema_version", ("audit_sha",)),
        ("basis_contract_schema_version", ("basis_contract_sha",)),
        ("binding_schema_version", ("binding_sha",)),
        ("branch_attempt_schema_version", ("attempt_sha",)),
        ("bridge_schema_version", ("bridge_sha",)),
        ("calibration_schema_version", ("calibration_manifest_sha",)),
        ("calibration_v3_schema_version", ("calibration_v3_sha",)),
        ("candidate_schema_version", ("candidate_sha",)),
        ("construction_schema_version", ("construction_sha",)),
        ("direction_schema_version", ("direction_manifest_sha",)),
        ("entry_schema_version", ("entry_sha",)),
        ("factory_schema_version", ("factory_sha",)),
        ("geometry_bundle_schema_version", ("geometry_bundle_sha",)),
        ("grid_authority_schema_version", ("grid_authority_sha",)),
        ("grid_schema_version", ("bridge_grid_sha", "response_grid_sha")),
        ("manifest_schema_version", ("manifest_sha",)),
        ("materialization_schema_version", ("materialization_sha",)),
        ("observation_schema_version", ("observation_sha",)),
        ("parent_freeze_schema_version", ("parent_freeze_v3_sha",)),
        ("permit_schema_version", ("permit_sha",)),
        ("protocol_schema_version", ("protocol_sha",)),
        ("provenance_fixture_schema_version", ("provenance_fixture_sha",)),
        ("receipt_schema_version", ("receipt_sha",)),
        ("reference_schema_version", ("reference_sha",)),
        ("reference_spec_schema_version", ("reference_spec_sha",)),
        ("registry_schema_version", ("registry_sha",)),
        ("response_contract_schema_version", ("response_contract_sha",)),
        ("response_schema_version", ("response_sha",)),
        ("run_spec_schema_version", ("run_spec_sha",)),
        ("scenario_authority_schema_version", ("scenario_authority_sha",)),
        ("shell_schema_version", ("shell_manifest_sha",)),
        ("shell_spec_schema_version", ("shell_spec_sha",)),
        ("snapshot_schema_version", ("snapshot_sha",)),
        ("source_ref_schema_version", ("source_ref_sha",)),
        ("spec_schema_version", ("spec_sha",)),
        ("tensor_schema_version", ("tensor_sha",)),
        ("transcript_schema_version", ("experimental_sha",)),
    ),
    _lineage_only_fields=("primitive_schema_version", "target_schema_version"),
    _validated_body_shas={},
):
    if type(value) is not dict:
        return
    body_sha = _sha(value)
    cached = _validated_body_shas.get(body_sha)
    if cached is True:
        return
    if type(cached) is str:
        _reject(cached)
    schema_names = [name for name in value if name.endswith("_schema_version")]
    try:
        if len(schema_names) > 1:
            _reject("SCHEMA_MISMATCH")
        if schema_names:
            schema_name = schema_names[0]
            if schema_name not in _lineage_only_fields:
                declared = None
                for candidate_name, candidate_fields in _declared_fields:
                    if schema_name == candidate_name:
                        declared = candidate_fields
                        break
                if declared is None:
                    _reject("SCHEMA_MISMATCH")
                present = [name for name in declared if name in value]
                if len(present) != 1:
                    _reject("HASH_MISMATCH")
                _require_self_hash(value, present[0])
        for member in value.values():
            if type(member) is dict:
                _schema_self_hash(member)
            elif type(member) is list:
                for item in member:
                    if type(item) is dict:
                        _schema_self_hash(item)
    except B7LabMutationRejected as error:
        reason = error.args[0] if len(error.args) == 1 else "HASH_MISMATCH"
        _validated_body_shas[body_sha] = reason
        raise
    _validated_body_shas[body_sha] = True


def _validate_provenance(value):
    _exact_fields(
        value,
        (
            "provenance_fixture_schema_version",
            "parent_freeze_v3_body",
            "permit_body",
            "materialization_body",
            "current_scenario_response_contract_v3_body",
            "actual_bridge_grid_authority_body",
            "matched_ablated_bridge_grid_authority_body",
            "provenance_fixture_sha",
        ),
    )
    if value["provenance_fixture_schema_version"] != (
        "experimental.v3m0.b7.provenance-fixture.v1"
    ):
        _reject("SCHEMA_MISMATCH")
    for name in (
        "parent_freeze_v3_body",
        "permit_body",
        "materialization_body",
        "current_scenario_response_contract_v3_body",
        "actual_bridge_grid_authority_body",
        "matched_ablated_bridge_grid_authority_body",
    ):
        if type(value[name]) is not dict:
            _reject("UNKNOWN_OR_MISSING_FIELD")
    _require_self_hash(value, "provenance_fixture_sha")
    _schema_self_hash(value)


def _validate_reference(value):
    _exact_fields(
        value,
        (
            "status",
            "failure",
            "reference_spec",
            "attempt_audit",
            "reference",
            "outcome_sha",
        ),
    )
    if (
        type(value["status"]) is not dict
        or type(value["reference_spec"]) is not dict
        or type(value["attempt_audit"]) is not dict
        or (value["reference"] is not None and type(value["reference"]) is not dict)
    ):
        _reject("EVIDENCE_MISMATCH")
    _require_self_hash(value, "outcome_sha")
    _schema_self_hash(value)


def _validate_shell(value):
    _exact_fields(
        value,
        (
            "status",
            "failure",
            "reference_outcome",
            "attempt_audit",
            "shell",
            "outcome_sha",
        ),
    )
    if (
        type(value["status"]) is not dict
        or type(value["reference_outcome"]) is not dict
        or type(value["attempt_audit"]) is not dict
        or (value["shell"] is not None and type(value["shell"]) is not dict)
    ):
        _reject("EVIDENCE_MISMATCH")
    _require_self_hash(value, "outcome_sha")
    _schema_self_hash(value)


def _validate_attempt(value, branch, run_spec_sha):
    _exact_fields(
        value,
        (
            "branch_attempt_schema_version",
            "branch",
            "response_values",
            "bridge_audit",
            "failure",
            "attempt_sha",
        ),
    )
    if value["branch_attempt_schema_version"] != (
        "experimental.v3m0.b7.branch-attempt.v1"
    ):
        _reject("SCHEMA_MISMATCH")
    if value["branch"] != branch:
        _reject("EVIDENCE_MISMATCH")
    if value["response_values"] is not None:
        if type(value["response_values"]) is not dict:
            _reject("EVIDENCE_MISMATCH")
        _schema_self_hash(value["response_values"])
    if value["bridge_audit"] is not None:
        if type(value["bridge_audit"]) is not dict:
            _reject("EVIDENCE_MISMATCH")
        if (
            "branch" not in value["bridge_audit"]
            or value["bridge_audit"]["branch"] != branch
            or "run_spec_sha" not in value["bridge_audit"]
            or value["bridge_audit"]["run_spec_sha"] != run_spec_sha
        ):
            _reject("EVIDENCE_MISMATCH")
        _schema_self_hash(value["bridge_audit"])
    _require_self_hash(value, "attempt_sha")


def _validate_response(value, branch, run_spec_sha):
    _exact_fields(
        value,
        (
            "response_schema_version",
            "branch",
            "factory_sha",
            "transition_sha",
            "dynamics_certificate_sha",
            "source_basis",
            "readout_basis",
            "run_spec_sha",
            "shell_manifest_sha",
            "bridge_audit",
            "values",
            "response_sha",
        ),
    )
    if value["branch"] != branch or value["run_spec_sha"] != run_spec_sha:
        _reject("EVIDENCE_MISMATCH")
    for name in (
        "factory_sha",
        "transition_sha",
        "dynamics_certificate_sha",
        "run_spec_sha",
        "shell_manifest_sha",
    ):
        if not _is_sha(value[name]):
            _reject("EVIDENCE_MISMATCH")
    for name in ("source_basis", "readout_basis", "bridge_audit", "values"):
        if type(value[name]) is not dict:
            _reject("EVIDENCE_MISMATCH")
    _require_self_hash(value, "response_sha")
    _schema_self_hash(value["bridge_audit"])
    _schema_self_hash(value["values"])


def _presence_bits(transcript):
    actual = transcript["actual_branch_attempt"]
    matched = transcript["matched_ablated_branch_attempt"]
    bits = "1" if transcript["shell_outcome"] is not None else "0"
    bits += "1" if actual is not None else "0"
    bits += "1" if actual is not None and actual["response_values"] is not None else "0"
    bits += "1" if matched is not None else "0"
    bits += (
        "1" if matched is not None and matched["response_values"] is not None else "0"
    )
    bits += "1" if actual is not None and actual["bridge_audit"] is not None else "0"
    bits += "1" if matched is not None and matched["bridge_audit"] is not None else "0"
    bits += "1" if transcript["actual_completed_response"] is not None else "0"
    bits += "1" if transcript["matched_ablated_completed_response"] is not None else "0"
    return bits


def _case_row(case_id):
    rows = (
        ("reference_failure", "000000000", None, None, ("reference",)),
        ("shell_failure", "100000000", None, None, ("reference", "shell")),
        (
            "actual_response_values_failure",
            "110000000",
            "actual_response_failed",
            None,
            ("reference", "shell", "actual_response_values"),
        ),
        (
            "matched_response_values_failure",
            "111100000",
            None,
            "matched_ablated_response_failed",
            (
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
            ),
        ),
        (
            "actual_bridge_failure",
            "111110000",
            "actual_bridge_failed",
            None,
            (
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
                "actual_bridge",
            ),
        ),
        (
            "matched_bridge_failure",
            "111111000",
            None,
            "matched_ablated_bridge_failed",
            (
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
                "actual_bridge",
                "matched_ablated_bridge",
            ),
        ),
        (
            "success",
            "111111111",
            None,
            None,
            (
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
                "actual_bridge",
                "matched_ablated_bridge",
            ),
        ),
    )
    for row in rows:
        if row[0] == case_id:
            return row
    _reject("PRESENCE_MISMATCH")


def _validate_outcome_schedule(transcript, case_id):
    reference = transcript["reference_outcome"]
    reference_defined = (
        reference["status"]["defined"] if "defined" in reference["status"] else None
    )
    if case_id == "reference_failure":
        if (
            reference_defined is not False
            or reference["failure"] is None
            or reference["reference"] is not None
        ):
            _reject("EVIDENCE_MISMATCH")
        return
    if (
        reference_defined is not True
        or reference["failure"] is not None
        or type(reference["reference"]) is not dict
    ):
        _reject("EVIDENCE_MISMATCH")
    shell = transcript["shell_outcome"]
    if _canonical(shell["reference_outcome"]) != _canonical(reference):
        _reject("EVIDENCE_MISMATCH")
    shell_defined = shell["status"]["defined"] if "defined" in shell["status"] else None
    if case_id == "shell_failure":
        if (
            shell_defined is not False
            or shell["failure"] is None
            or shell["shell"] is not None
        ):
            _reject("EVIDENCE_MISMATCH")
    elif (
        shell_defined is not True
        or shell["failure"] is not None
        or type(shell["shell"]) is not dict
    ):
        _reject("EVIDENCE_MISMATCH")


def _validate_completed(transcript, field, attempt_field, branch, run_spec_sha):
    response = transcript[field]
    if response is None:
        return
    _validate_response(response, branch, run_spec_sha)
    attempt = transcript[attempt_field]
    if attempt is None:
        _reject("EVIDENCE_MISMATCH")
    if _canonical(response["values"]) != _canonical(attempt["response_values"]):
        _reject("EVIDENCE_MISMATCH")
    if _canonical(response["bridge_audit"]) != _canonical(attempt["bridge_audit"]):
        _reject("EVIDENCE_MISMATCH")
    shell = transcript["shell_outcome"]
    if shell is None or type(shell["shell"]) is not dict:
        _reject("EVIDENCE_MISMATCH")
    shell_manifest_sha = (
        shell["shell"]["shell_manifest_sha"]
        if "shell_manifest_sha" in shell["shell"]
        else None
    )
    if response["shell_manifest_sha"] != shell_manifest_sha:
        _reject("EVIDENCE_MISMATCH")


def _validate_transcript(transcript):
    _exact_fields(
        transcript,
        (
            "transcript_schema_version",
            "corpus_spec_sha",
            "case_id",
            "environment_manifest_sha",
            "provenance_fixture",
            "response_run_spec_fixture",
            "reference_outcome",
            "shell_outcome",
            "actual_branch_attempt",
            "matched_ablated_branch_attempt",
            "actual_completed_response",
            "matched_ablated_completed_response",
            "terminal_tag",
            "callback_trace",
            "ordered_leaf_digests",
            "experimental_sha",
        ),
    )
    if transcript["transcript_schema_version"] != (
        "experimental.v3m0.b7.normalized-transcript.v1"
    ):
        _reject("SCHEMA_MISMATCH")
    if not _is_sha(transcript["corpus_spec_sha"]) or not _is_sha(
        transcript["environment_manifest_sha"]
    ):
        _reject("HASH_MISMATCH")
    row = _case_row(transcript["case_id"])
    case_id, expected_bits, actual_failure, matched_failure, expected_trace = row
    if transcript["terminal_tag"] != case_id:
        _reject("PRESENCE_MISMATCH")
    if _presence_bits(transcript) != expected_bits:
        _reject("PRESENCE_MISMATCH")
    _validate_provenance(transcript["provenance_fixture"])
    run_spec = transcript["response_run_spec_fixture"]
    if type(run_spec) is not dict or "run_spec_sha" not in run_spec:
        _reject("UNKNOWN_OR_MISSING_FIELD")
    _schema_self_hash(run_spec)
    if not _is_sha(run_spec["run_spec_sha"]):
        _reject("HASH_MISMATCH")
    run_spec_sha = run_spec["run_spec_sha"]
    _validate_reference(transcript["reference_outcome"])
    if transcript["shell_outcome"] is not None:
        _validate_shell(transcript["shell_outcome"])
    actual = transcript["actual_branch_attempt"]
    if actual is not None:
        _validate_attempt(actual, "actual", run_spec_sha)
        if actual["failure"] != actual_failure:
            _reject("FAILURE_SCHEDULE_MISMATCH")
    matched = transcript["matched_ablated_branch_attempt"]
    if matched is not None:
        _validate_attempt(matched, "matched_ablated", run_spec_sha)
        if matched["failure"] != matched_failure:
            _reject("FAILURE_SCHEDULE_MISMATCH")
    trace_items = transcript["callback_trace"]
    if type(trace_items) is not list or tuple(trace_items) != expected_trace:
        _reject("FAILURE_SCHEDULE_MISMATCH")
    digest_items = transcript["ordered_leaf_digests"]
    if type(digest_items) is not list or len(digest_items) != len(expected_trace):
        _reject("EVIDENCE_MISMATCH")
    for ordinal, digest_item in enumerate(digest_items):
        _exact_fields(
            digest_item,
            ("leaf_id", "call_ordinal", "input_body_sha", "output_body_sha"),
        )
        if (
            digest_item["leaf_id"] != expected_trace[ordinal]
            or type(digest_item["call_ordinal"]) is not int
            or digest_item["call_ordinal"] != ordinal
            or not _is_sha(digest_item["input_body_sha"])
            or not _is_sha(digest_item["output_body_sha"])
        ):
            _reject("EVIDENCE_MISMATCH")
    _validate_outcome_schedule(transcript, case_id)
    _validate_completed(
        transcript,
        "actual_completed_response",
        "actual_branch_attempt",
        "actual",
        run_spec_sha,
    )
    _validate_completed(
        transcript,
        "matched_ablated_completed_response",
        "matched_ablated_branch_attempt",
        "matched_ablated",
        run_spec_sha,
    )
    _require_self_hash(transcript, "experimental_sha")
    return expected_bits


def _attempt_core(attempt):
    return {
        "branch_attempt_schema_version": attempt["branch_attempt_schema_version"],
        "branch": attempt["branch"],
        "failure": attempt["failure"],
        "attempt_sha": attempt["attempt_sha"],
    }


def _base_variant_values(transcript):
    return (
        transcript["transcript_schema_version"],
        transcript["corpus_spec_sha"],
        transcript["case_id"],
        transcript["environment_manifest_sha"],
        transcript["provenance_fixture"],
        transcript["response_run_spec_fixture"],
        transcript["reference_outcome"],
        transcript["callback_trace"],
        transcript["ordered_leaf_digests"],
        transcript["experimental_sha"],
    )


def _make_variant(transcript):
    base_values = _base_variant_values(transcript)
    variant = transcript["case_id"]
    actual = transcript["actual_branch_attempt"]
    matched = transcript["matched_ablated_branch_attempt"]
    if variant == "reference_failure":
        return _ReferenceFailure(*base_values)
    if variant == "shell_failure":
        return _ShellFailure(*base_values, transcript["shell_outcome"])
    if variant == "actual_response_values_failure":
        return _ActualResponseValuesFailure(
            *base_values,
            transcript["shell_outcome"],
            _attempt_core(actual),
        )
    if variant == "matched_response_values_failure":
        return _MatchedResponseValuesFailure(
            *base_values,
            transcript["shell_outcome"],
            _attempt_core(actual),
            actual["response_values"],
            _attempt_core(matched),
        )
    if variant == "actual_bridge_failure":
        return _ActualBridgeFailure(
            *base_values,
            transcript["shell_outcome"],
            _attempt_core(actual),
            actual["response_values"],
            _attempt_core(matched),
            matched["response_values"],
        )
    if variant == "matched_bridge_failure":
        return _MatchedBridgeFailure(
            *base_values,
            transcript["shell_outcome"],
            _attempt_core(actual),
            actual["response_values"],
            _attempt_core(matched),
            matched["response_values"],
            actual["bridge_audit"],
        )
    if variant == "success":
        return _Success(
            *base_values,
            transcript["shell_outcome"],
            _attempt_core(actual),
            actual["response_values"],
            _attempt_core(matched),
            matched["response_values"],
            actual["bridge_audit"],
            matched["bridge_audit"],
            transcript["actual_completed_response"],
            transcript["matched_ablated_completed_response"],
        )
    _reject("PRESENCE_MISMATCH")


def _base_payload(record):
    return {
        "transcript_schema_version": record.transcript_schema_version,
        "corpus_spec_sha": record.corpus_spec_sha,
        "case_id": record.case_id,
        "environment_manifest_sha": record.environment_manifest_sha,
        "provenance_fixture": record.provenance_fixture,
        "response_run_spec_fixture": record.response_run_spec_fixture,
        "reference_outcome": record.reference_outcome,
        "callback_trace": record.trace_items,
        "ordered_leaf_digests": record.digest_items,
        "experimental_sha": record.experimental_sha,
    }


def _variant_payload(record):
    base_payload = _base_payload(record)
    if type(record) is _ReferenceFailure:
        return base_payload
    if type(record) is _ShellFailure:
        return {**base_payload, "shell_outcome": record.shell_outcome}
    if type(record) is _ActualResponseValuesFailure:
        return {
            **base_payload,
            "shell_outcome": record.shell_outcome,
            "actual_branch_attempt_core": record.actual_branch_attempt_core,
        }
    if type(record) is _MatchedResponseValuesFailure:
        return {
            **base_payload,
            "shell_outcome": record.shell_outcome,
            "actual_branch_attempt_core": record.actual_branch_attempt_core,
            "actual_response_values": record.actual_response_values,
            "matched_ablated_branch_attempt_core": (
                record.matched_ablated_branch_attempt_core
            ),
        }
    if type(record) is _ActualBridgeFailure:
        return {
            **base_payload,
            "shell_outcome": record.shell_outcome,
            "actual_branch_attempt_core": record.actual_branch_attempt_core,
            "actual_response_values": record.actual_response_values,
            "matched_ablated_branch_attempt_core": (
                record.matched_ablated_branch_attempt_core
            ),
            "matched_ablated_response_values": (record.matched_ablated_response_values),
        }
    if type(record) is _MatchedBridgeFailure:
        return {
            **base_payload,
            "shell_outcome": record.shell_outcome,
            "actual_branch_attempt_core": record.actual_branch_attempt_core,
            "actual_response_values": record.actual_response_values,
            "matched_ablated_branch_attempt_core": (
                record.matched_ablated_branch_attempt_core
            ),
            "matched_ablated_response_values": (record.matched_ablated_response_values),
            "actual_bridge_audit": record.actual_bridge_audit,
        }
    if type(record) is _Success:
        return {
            **base_payload,
            "shell_outcome": record.shell_outcome,
            "actual_branch_attempt_core": record.actual_branch_attempt_core,
            "actual_response_values": record.actual_response_values,
            "matched_ablated_branch_attempt_core": (
                record.matched_ablated_branch_attempt_core
            ),
            "matched_ablated_response_values": (record.matched_ablated_response_values),
            "actual_bridge_audit": record.actual_bridge_audit,
            "matched_ablated_bridge_audit": record.matched_ablated_bridge_audit,
            "actual_completed_response": record.actual_completed_response,
            "matched_ablated_completed_response": (
                record.matched_ablated_completed_response
            ),
        }
    _reject("PRESENCE_MISMATCH")


def _expected_payload_fields(variant):
    base_fields = (
        "transcript_schema_version",
        "corpus_spec_sha",
        "case_id",
        "environment_manifest_sha",
        "provenance_fixture",
        "response_run_spec_fixture",
        "reference_outcome",
        "callback_trace",
        "ordered_leaf_digests",
        "experimental_sha",
    )
    presence_fields = (
        "shell_outcome",
        "actual_branch_attempt_core",
        "actual_response_values",
        "matched_ablated_branch_attempt_core",
        "matched_ablated_response_values",
        "actual_bridge_audit",
        "matched_ablated_bridge_audit",
        "actual_completed_response",
        "matched_ablated_completed_response",
    )
    bits = _case_row(variant)[1]
    selected_fields = tuple(
        field for field, bit in zip(presence_fields, bits) if bit == "1"
    )
    return base_fields + selected_fields


def _rebuild_attempt(payload, core_field, values_field, audit_field):
    if core_field not in payload:
        return None
    core = payload[core_field]
    if type(core) is not dict or set(core) != {
        "branch_attempt_schema_version",
        "branch",
        "failure",
        "attempt_sha",
    }:
        _reject("EVIDENCE_MISMATCH")
    return {
        "branch_attempt_schema_version": core["branch_attempt_schema_version"],
        "branch": core["branch"],
        "response_values": payload[values_field] if values_field in payload else None,
        "bridge_audit": payload[audit_field] if audit_field in payload else None,
        "failure": core["failure"],
        "attempt_sha": core["attempt_sha"],
    }


def _rebuild_transcript(variant, payload):
    fields = _expected_payload_fields(variant)
    if (
        type(payload) is not dict
        or len(payload) != len(fields)
        or any(name not in payload for name in fields)
    ):
        _reject("PRESENCE_MISMATCH")
    if payload["case_id"] != variant:
        _reject("PRESENCE_MISMATCH")
    actual = _rebuild_attempt(
        payload,
        "actual_branch_attempt_core",
        "actual_response_values",
        "actual_bridge_audit",
    )
    matched = _rebuild_attempt(
        payload,
        "matched_ablated_branch_attempt_core",
        "matched_ablated_response_values",
        "matched_ablated_bridge_audit",
    )
    return {
        "transcript_schema_version": payload["transcript_schema_version"],
        "corpus_spec_sha": payload["corpus_spec_sha"],
        "case_id": payload["case_id"],
        "environment_manifest_sha": payload["environment_manifest_sha"],
        "provenance_fixture": payload["provenance_fixture"],
        "response_run_spec_fixture": payload["response_run_spec_fixture"],
        "reference_outcome": payload["reference_outcome"],
        "shell_outcome": payload["shell_outcome"]
        if "shell_outcome" in payload
        else None,
        "actual_branch_attempt": actual,
        "matched_ablated_branch_attempt": matched,
        "actual_completed_response": (
            payload["actual_completed_response"]
            if "actual_completed_response" in payload
            else None
        ),
        "matched_ablated_completed_response": (
            payload["matched_ablated_completed_response"]
            if "matched_ablated_completed_response" in payload
            else None
        ),
        "terminal_tag": variant,
        "callback_trace": payload["callback_trace"],
        "ordered_leaf_digests": payload["ordered_leaf_digests"],
        "experimental_sha": payload["experimental_sha"],
    }


def _wire(transcript):
    record = _make_variant(transcript)
    payload = _variant_payload(record)
    wire = {
        "wire_schema_version": WIRE_SCHEMA_ID,
        "route_id": ROUTE_ID,
        "variant": transcript["terminal_tag"],
        "payload": payload,
        "transcript_sha": transcript["experimental_sha"],
        "wire_sha": "",
    }
    wire["wire_sha"] = _sha(
        {name: member for name, member in wire.items() if name != "wire_sha"}
    )
    return wire


def encode_normalized_transcript(canonical_transcript_utf8):
    transcript = _parse(canonical_transcript_utf8)
    _validate_transcript(transcript)
    return _canonical(_wire(transcript))


def verify_and_decode_route_wire(canonical_route_wire_utf8):
    wire = _parse(canonical_route_wire_utf8)
    _exact_fields(
        wire,
        (
            "wire_schema_version",
            "route_id",
            "variant",
            "payload",
            "transcript_sha",
            "wire_sha",
        ),
    )
    if wire["wire_schema_version"] != WIRE_SCHEMA_ID or wire["route_id"] != ROUTE_ID:
        _reject("SCHEMA_MISMATCH")
    _require_self_hash(wire, "wire_sha")
    transcript = _rebuild_transcript(wire["variant"], wire["payload"])
    _validate_transcript(transcript)
    if wire["transcript_sha"] != transcript["experimental_sha"]:
        _reject("EVIDENCE_MISMATCH")
    decoded = _canonical(transcript)
    if _parse(decoded) != transcript:
        _reject("ROUNDTRIP_MISMATCH")
    return decoded
