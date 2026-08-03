from __future__ import annotations

import hashlib as _hashlib
import json as _json

from .common import B7LabMutationRejected


ROUTE_ID = "A_FLAT"
WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"


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
    if value["branch"] != branch:
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
        (
            "reference_failure",
            "000000000",
            None,
            None,
            ("reference",),
        ),
        (
            "shell_failure",
            "100000000",
            None,
            None,
            ("reference", "shell"),
        ),
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
    return expected_bits


def _wire(transcript, presence_bits):
    wire = {
        "wire_schema_version": WIRE_SCHEMA_ID,
        "route_id": ROUTE_ID,
        "terminal_tag": transcript["terminal_tag"],
        "presence_bits": presence_bits,
        "transcript_sha": transcript["experimental_sha"],
        "transcript": transcript,
        "wire_sha": "",
    }
    wire["wire_sha"] = _sha(
        {name: value for name, value in wire.items() if name != "wire_sha"}
    )
    return wire


def encode_normalized_transcript(canonical_transcript_utf8):
    transcript = _parse(canonical_transcript_utf8)
    presence_bits = _validate_transcript(transcript)
    return _canonical(_wire(transcript, presence_bits))


def verify_and_decode_route_wire(canonical_route_wire_utf8):
    wire = _parse(canonical_route_wire_utf8)
    _exact_fields(
        wire,
        (
            "wire_schema_version",
            "route_id",
            "terminal_tag",
            "presence_bits",
            "transcript_sha",
            "transcript",
            "wire_sha",
        ),
    )
    if wire["wire_schema_version"] != WIRE_SCHEMA_ID or wire["route_id"] != ROUTE_ID:
        _reject("SCHEMA_MISMATCH")
    _require_self_hash(wire, "wire_sha")
    presence_bits = _validate_transcript(wire["transcript"])
    if (
        wire["terminal_tag"] != wire["transcript"]["terminal_tag"]
        or wire["presence_bits"] != presence_bits
        or wire["transcript_sha"] != wire["transcript"]["experimental_sha"]
    ):
        _reject("EVIDENCE_MISMATCH")
    decoded = _canonical(wire["transcript"])
    if _parse(decoded) != wire["transcript"]:
        _reject("ROUNDTRIP_MISMATCH")
    return decoded
