from __future__ import annotations

import dataclasses as _dataclasses
import hashlib as _hashlib
import json as _json

from .common import B7LabMutationRejected


ROUTE_ID = "B_PROGRESS"
WIRE_SCHEMA_ID = "experimental.v3m0.b7.b-progress.wire.v1"


@_dataclasses.dataclass(frozen=True)
class _ResponseBranchProgressV3:
    branch: object
    response_values: object
    bridge_audit: object
    completed_response: object
    branch_failure: object
    progress_sha: str


@_dataclasses.dataclass(frozen=True)
class _PairedBranchProgressWireV1:
    wire_schema_version: str
    route_id: str
    transcript_prefix: object
    actual_progress: object
    matched_ablated_progress: object
    terminal_failure: object
    transcript_sha: str
    wire_sha: str


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


def _schema_self_hash(value):
    if type(value) is not dict:
        return
    schema_names = [name for name in value if name.endswith("_schema_version")]
    hash_names = [
        name
        for name, member in value.items()
        if (name.endswith("_sha") or name.endswith("_sha256")) and _is_sha(member)
    ]
    if schema_names and hash_names:
        matches = []
        for name in hash_names:
            payload = {key: member for key, member in value.items() if key != name}
            if value[name] == _sha(payload):
                matches.append(name)
        if len(matches) != 1:
            _reject("HASH_MISMATCH")
    for member in value.values():
        if type(member) is dict:
            _schema_self_hash(member)
        elif type(member) is list:
            for item in member:
                if type(item) is dict:
                    _schema_self_hash(item)


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


def _validate_attempt(value, branch):
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
        ):
            _reject("EVIDENCE_MISMATCH")
        _schema_self_hash(value["bridge_audit"])
    _require_self_hash(value, "attempt_sha")


def _validate_response(value, branch):
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
    if type(value["response_schema_version"]) is not str or value["branch"] != branch:
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


def _validate_completed(transcript, field, attempt_field, branch):
    response = transcript[field]
    if response is None:
        return
    _validate_response(response, branch)
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
    _require_self_hash(transcript, "experimental_sha")
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
    if type(transcript["response_run_spec_fixture"]) is not dict:
        _reject("UNKNOWN_OR_MISSING_FIELD")
    _schema_self_hash(transcript["response_run_spec_fixture"])
    _validate_reference(transcript["reference_outcome"])
    if transcript["shell_outcome"] is not None:
        _validate_shell(transcript["shell_outcome"])
    actual = transcript["actual_branch_attempt"]
    if actual is not None:
        _validate_attempt(actual, "actual")
        if actual["failure"] != actual_failure:
            _reject("FAILURE_SCHEDULE_MISMATCH")
    matched = transcript["matched_ablated_branch_attempt"]
    if matched is not None:
        _validate_attempt(matched, "matched_ablated")
        if matched["failure"] != matched_failure:
            _reject("FAILURE_SCHEDULE_MISMATCH")
    if (
        type(transcript["callback_trace"]) is not list
        or tuple(transcript["callback_trace"]) != expected_trace
    ):
        _reject("FAILURE_SCHEDULE_MISMATCH")
    leaves = transcript["ordered_leaf_digests"]
    if type(leaves) is not list or len(leaves) != len(expected_trace):
        _reject("EVIDENCE_MISMATCH")
    for ordinal, leaf in enumerate(leaves):
        _exact_fields(
            leaf,
            ("leaf_id", "call_ordinal", "input_body_sha", "output_body_sha"),
        )
        if (
            leaf["leaf_id"] != expected_trace[ordinal]
            or type(leaf["call_ordinal"]) is not int
            or leaf["call_ordinal"] != ordinal
            or not _is_sha(leaf["input_body_sha"])
            or not _is_sha(leaf["output_body_sha"])
        ):
            _reject("EVIDENCE_MISMATCH")
    _validate_outcome_schedule(transcript, case_id)
    _validate_completed(
        transcript,
        "actual_completed_response",
        "actual_branch_attempt",
        "actual",
    )
    _validate_completed(
        transcript,
        "matched_ablated_completed_response",
        "matched_ablated_branch_attempt",
        "matched_ablated",
    )
    return row


def _transcript_prefix(transcript):
    return {
        "transcript_schema_version": transcript["transcript_schema_version"],
        "corpus_spec_sha": transcript["corpus_spec_sha"],
        "case_id": transcript["case_id"],
        "environment_manifest_sha": transcript["environment_manifest_sha"],
        "provenance_fixture": transcript["provenance_fixture"],
        "response_run_spec_fixture": transcript["response_run_spec_fixture"],
        "reference_outcome": transcript["reference_outcome"],
        "shell_outcome": transcript["shell_outcome"],
        "callback_trace": transcript["callback_trace"],
        "ordered_leaf_digests": transcript["ordered_leaf_digests"],
    }


def _build_progress(attempt, completed_response):
    if attempt is None:
        return None
    payload = {
        "branch": attempt["branch"],
        "response_values": attempt["response_values"],
        "bridge_audit": attempt["bridge_audit"],
        "completed_response": completed_response,
        "branch_failure": attempt["failure"],
    }
    progress = _ResponseBranchProgressV3(
        branch=payload["branch"],
        response_values=payload["response_values"],
        bridge_audit=payload["bridge_audit"],
        completed_response=payload["completed_response"],
        branch_failure=payload["branch_failure"],
        progress_sha=_sha(payload),
    )
    return _dataclasses.asdict(progress)


def _terminal_failure(case_id):
    return None if case_id == "success" else case_id


def _build_wire(transcript):
    payload = {
        "wire_schema_version": WIRE_SCHEMA_ID,
        "route_id": ROUTE_ID,
        "transcript_prefix": _transcript_prefix(transcript),
        "actual_progress": _build_progress(
            transcript["actual_branch_attempt"],
            transcript["actual_completed_response"],
        ),
        "matched_ablated_progress": _build_progress(
            transcript["matched_ablated_branch_attempt"],
            transcript["matched_ablated_completed_response"],
        ),
        "terminal_failure": _terminal_failure(transcript["case_id"]),
        "transcript_sha": transcript["experimental_sha"],
    }
    wire = _PairedBranchProgressWireV1(
        wire_schema_version=payload["wire_schema_version"],
        route_id=payload["route_id"],
        transcript_prefix=payload["transcript_prefix"],
        actual_progress=payload["actual_progress"],
        matched_ablated_progress=payload["matched_ablated_progress"],
        terminal_failure=payload["terminal_failure"],
        transcript_sha=payload["transcript_sha"],
        wire_sha=_sha(payload),
    )
    return _dataclasses.asdict(wire)


def _validate_progress(progress, branch):
    if progress is None:
        return
    _exact_fields(
        progress,
        (
            "branch",
            "response_values",
            "bridge_audit",
            "completed_response",
            "branch_failure",
            "progress_sha",
        ),
    )
    _require_self_hash(progress, "progress_sha")
    if progress["branch"] != branch:
        _reject("EVIDENCE_MISMATCH")
    if progress["response_values"] is not None:
        if type(progress["response_values"]) is not dict:
            _reject("EVIDENCE_MISMATCH")
        _schema_self_hash(progress["response_values"])
    if progress["bridge_audit"] is not None:
        if type(progress["bridge_audit"]) is not dict:
            _reject("EVIDENCE_MISMATCH")
        if (
            "branch" not in progress["bridge_audit"]
            or progress["bridge_audit"]["branch"] != branch
        ):
            _reject("EVIDENCE_MISMATCH")
        _schema_self_hash(progress["bridge_audit"])
    if progress["completed_response"] is not None:
        _validate_response(progress["completed_response"], branch)


def _progress_presence_bits(wire):
    actual = wire["actual_progress"]
    matched = wire["matched_ablated_progress"]
    prefix = wire["transcript_prefix"]
    bits = "1" if prefix["shell_outcome"] is not None else "0"
    bits += "1" if actual is not None else "0"
    bits += "1" if actual is not None and actual["response_values"] is not None else "0"
    bits += "1" if matched is not None else "0"
    bits += (
        "1" if matched is not None and matched["response_values"] is not None else "0"
    )
    bits += "1" if actual is not None and actual["bridge_audit"] is not None else "0"
    bits += "1" if matched is not None and matched["bridge_audit"] is not None else "0"
    bits += (
        "1" if actual is not None and actual["completed_response"] is not None else "0"
    )
    bits += (
        "1"
        if matched is not None and matched["completed_response"] is not None
        else "0"
    )
    return bits


def _validate_wire_schedule(wire):
    prefix = wire["transcript_prefix"]
    if type(prefix) is not dict or "case_id" not in prefix:
        _reject("UNKNOWN_OR_MISSING_FIELD")
    row = _case_row(prefix["case_id"])
    case_id, expected_bits, actual_failure, matched_failure, _trace = row
    if wire["terminal_failure"] != _terminal_failure(case_id):
        _reject("FAILURE_SCHEDULE_MISMATCH")
    if _progress_presence_bits(wire) != expected_bits:
        _reject("FAILURE_SCHEDULE_MISMATCH")
    actual = wire["actual_progress"]
    matched = wire["matched_ablated_progress"]
    if actual is not None and actual["branch_failure"] != actual_failure:
        _reject("FAILURE_SCHEDULE_MISMATCH")
    if matched is not None and matched["branch_failure"] != matched_failure:
        _reject("FAILURE_SCHEDULE_MISMATCH")


def _attempt_from_progress(progress, branch):
    if progress is None:
        return None
    attempt = {
        "branch_attempt_schema_version": "experimental.v3m0.b7.branch-attempt.v1",
        "branch": branch,
        "response_values": progress["response_values"],
        "bridge_audit": progress["bridge_audit"],
        "failure": progress["branch_failure"],
        "attempt_sha": "",
    }
    attempt["attempt_sha"] = _sha(
        {name: member for name, member in attempt.items() if name != "attempt_sha"}
    )
    return attempt


def _transcript_from_wire(wire):
    prefix = wire["transcript_prefix"]
    _exact_fields(
        prefix,
        (
            "transcript_schema_version",
            "corpus_spec_sha",
            "case_id",
            "environment_manifest_sha",
            "provenance_fixture",
            "response_run_spec_fixture",
            "reference_outcome",
            "shell_outcome",
            "callback_trace",
            "ordered_leaf_digests",
        ),
    )
    actual_progress = wire["actual_progress"]
    matched_progress = wire["matched_ablated_progress"]
    transcript = {
        "transcript_schema_version": prefix["transcript_schema_version"],
        "corpus_spec_sha": prefix["corpus_spec_sha"],
        "case_id": prefix["case_id"],
        "environment_manifest_sha": prefix["environment_manifest_sha"],
        "provenance_fixture": prefix["provenance_fixture"],
        "response_run_spec_fixture": prefix["response_run_spec_fixture"],
        "reference_outcome": prefix["reference_outcome"],
        "shell_outcome": prefix["shell_outcome"],
        "actual_branch_attempt": _attempt_from_progress(actual_progress, "actual"),
        "matched_ablated_branch_attempt": _attempt_from_progress(
            matched_progress,
            "matched_ablated",
        ),
        "actual_completed_response": (
            None if actual_progress is None else actual_progress["completed_response"]
        ),
        "matched_ablated_completed_response": (
            None if matched_progress is None else matched_progress["completed_response"]
        ),
        "terminal_tag": prefix["case_id"],
        "callback_trace": prefix["callback_trace"],
        "ordered_leaf_digests": prefix["ordered_leaf_digests"],
        "experimental_sha": "",
    }
    transcript["experimental_sha"] = _sha(
        {
            name: member
            for name, member in transcript.items()
            if name != "experimental_sha"
        }
    )
    return transcript


def encode_normalized_transcript(canonical_transcript_utf8):
    transcript = _parse(canonical_transcript_utf8)
    _validate_transcript(transcript)
    return _canonical(_build_wire(transcript))


def verify_and_decode_route_wire(canonical_route_wire_utf8):
    wire = _parse(canonical_route_wire_utf8)
    _exact_fields(
        wire,
        (
            "wire_schema_version",
            "route_id",
            "transcript_prefix",
            "actual_progress",
            "matched_ablated_progress",
            "terminal_failure",
            "transcript_sha",
            "wire_sha",
        ),
    )
    if wire["wire_schema_version"] != WIRE_SCHEMA_ID or wire["route_id"] != ROUTE_ID:
        _reject("SCHEMA_MISMATCH")
    _require_self_hash(wire, "wire_sha")
    if not _is_sha(wire["transcript_sha"]):
        _reject("HASH_MISMATCH")
    _validate_progress(wire["actual_progress"], "actual")
    _validate_progress(wire["matched_ablated_progress"], "matched_ablated")
    _validate_wire_schedule(wire)
    transcript = _transcript_from_wire(wire)
    if transcript["experimental_sha"] != wire["transcript_sha"]:
        _reject("EVIDENCE_MISMATCH")
    _validate_transcript(transcript)
    decoded = _canonical(transcript)
    if _parse(decoded) != transcript:
        _reject("ROUNDTRIP_MISMATCH")
    return decoded
