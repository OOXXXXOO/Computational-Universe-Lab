"""Task-8 contract tests for the isolated B_PROGRESS route."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import inspect
import json
from pathlib import Path

import pytest

from experiments.v3m0_b7_schema_lab.common import B7LabMutationRejected


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ROUTE_PATH = REPOSITORY_ROOT / "experiments/v3m0_b7_schema_lab/b_progress.py"
ROUTE_ID = "B_PROGRESS"
WIRE_SCHEMA_ID = "experimental.v3m0.b7.b-progress.wire.v1"
CASE_ROWS = (
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


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _seal(body: dict[str, object], field: str) -> dict[str, object]:
    body[field] = _sha({name: value for name, value in body.items() if name != field})
    return body


def _route_module():
    return importlib.import_module("experiments.v3m0_b7_schema_lab.b_progress")


def _attempt(
    branch: str,
    *,
    values_present: bool,
    audit_present: bool,
    failure: str | None,
) -> dict[str, object]:
    values = None
    if values_present:
        values = _seal(
            {
                "tensor_schema_version": "experimental.v3m0.b7.test-tensor.v1",
                "shape": [1, 1, 1],
                "values_wire": [[0.0, 0.0]],
                "tensor_sha": "",
            },
            "tensor_sha",
        )
    audit = None
    if audit_present:
        audit = _seal(
            {
                "audit_schema_version": "experimental.v3m0.b7.test-audit.v1",
                "branch": branch,
                "run_spec_sha": "3" * 64,
                "matrix_audits": [],
                "audit_sha": "",
            },
            "audit_sha",
        )
    return _seal(
        {
            "branch_attempt_schema_version": ("experimental.v3m0.b7.branch-attempt.v1"),
            "branch": branch,
            "response_values": values,
            "bridge_audit": audit,
            "failure": failure,
            "attempt_sha": "",
        },
        "attempt_sha",
    )


def _transcript(case_id: str) -> dict[str, object]:
    row = next(candidate for candidate in CASE_ROWS if candidate[0] == case_id)
    _, bits, actual_failure, matched_failure, trace = row
    reference = _seal(
        {
            "status": {"defined": case_id != "reference_failure"},
            "failure": "reference_failed" if case_id == "reference_failure" else None,
            "reference_spec": {"protocol_sha": "1" * 64},
            "attempt_audit": {"protocol_sha": "1" * 64},
            "reference": None if case_id == "reference_failure" else {"rank": 1},
            "outcome_sha": "",
        },
        "outcome_sha",
    )
    shell = None
    if bits[0] == "1":
        shell_body = None
        if case_id != "shell_failure":
            shell_body = _seal(
                {
                    "shell_schema_version": "experimental.v3m0.b7.test-shell.v1",
                    "shell_manifest_sha": "",
                },
                "shell_manifest_sha",
            )
        shell = _seal(
            {
                "status": {"defined": case_id != "shell_failure"},
                "failure": "shell_failed" if case_id == "shell_failure" else None,
                "reference_outcome": copy.deepcopy(reference),
                "attempt_audit": {"protocol_sha": "1" * 64},
                "shell": shell_body,
                "outcome_sha": "",
            },
            "outcome_sha",
        )
    actual = (
        _attempt(
            "actual",
            values_present=bits[2] == "1",
            audit_present=bits[5] == "1",
            failure=actual_failure,
        )
        if bits[1] == "1"
        else None
    )
    matched = (
        _attempt(
            "matched_ablated",
            values_present=bits[4] == "1",
            audit_present=bits[6] == "1",
            failure=matched_failure,
        )
        if bits[3] == "1"
        else None
    )
    actual_response = None
    matched_response = None
    if case_id == "success":
        shell_sha = shell["shell"]["shell_manifest_sha"]
        actual_response = _seal(
            {
                "response_schema_version": "experimental.v3m0.b7.test-response.v1",
                "branch": "actual",
                "factory_sha": "a" * 64,
                "transition_sha": "b" * 64,
                "dynamics_certificate_sha": "c" * 64,
                "source_basis": {"vectors_wire": [[1.0]]},
                "readout_basis": {"vectors_wire": [[1.0]]},
                "run_spec_sha": "3" * 64,
                "shell_manifest_sha": shell_sha,
                "bridge_audit": copy.deepcopy(actual["bridge_audit"]),
                "values": copy.deepcopy(actual["response_values"]),
                "response_sha": "",
            },
            "response_sha",
        )
        matched_response = copy.deepcopy(actual_response)
        matched_response["branch"] = "matched_ablated"
        matched_response["factory_sha"] = "d" * 64
        matched_response["transition_sha"] = "e" * 64
        matched_response["dynamics_certificate_sha"] = "f" * 64
        matched_response["bridge_audit"] = copy.deepcopy(matched["bridge_audit"])
        matched_response["values"] = copy.deepcopy(matched["response_values"])
        _seal(matched_response, "response_sha")
    provenance = _seal(
        {
            "provenance_fixture_schema_version": (
                "experimental.v3m0.b7.provenance-fixture.v1"
            ),
            "parent_freeze_v3_body": {},
            "permit_body": {},
            "materialization_body": {},
            "current_scenario_response_contract_v3_body": {},
            "actual_bridge_grid_authority_body": {},
            "matched_ablated_bridge_grid_authority_body": {},
            "provenance_fixture_sha": "",
        },
        "provenance_fixture_sha",
    )
    run_spec = _seal(
        {
            "run_spec_schema_version": "experimental.v3m0.b7.test-run-spec.v1",
            "run_spec_sha": "",
        },
        "run_spec_sha",
    )
    transcript = {
        "transcript_schema_version": "experimental.v3m0.b7.normalized-transcript.v1",
        "corpus_spec_sha": "4" * 64,
        "case_id": case_id,
        "environment_manifest_sha": "5" * 64,
        "provenance_fixture": provenance,
        "response_run_spec_fixture": run_spec,
        "reference_outcome": reference,
        "shell_outcome": shell,
        "actual_branch_attempt": actual,
        "matched_ablated_branch_attempt": matched,
        "actual_completed_response": actual_response,
        "matched_ablated_completed_response": matched_response,
        "terminal_tag": case_id,
        "callback_trace": list(trace),
        "ordered_leaf_digests": [
            {
                "leaf_id": stage,
                "call_ordinal": ordinal,
                "input_body_sha": hashlib.sha256(
                    f"{case_id}:{stage}:input".encode()
                ).hexdigest(),
                "output_body_sha": hashlib.sha256(
                    f"{case_id}:{stage}:output".encode()
                ).hexdigest(),
            }
            for ordinal, stage in enumerate(trace)
        ],
        "experimental_sha": "",
    }
    return _seal(transcript, "experimental_sha")


def _assert_rejected(call, payload: object, reason: str) -> None:
    with pytest.raises(B7LabMutationRejected) as caught:
        call(payload)
    assert caught.value.args == (reason,)


def _resign_progress(progress: dict[str, object]) -> None:
    _seal(progress, "progress_sha")


def _resign_wire(wire: dict[str, object]) -> bytes:
    _seal(wire, "wire_sha")
    return _canonical(wire)


def test_b_progress_exports_exact_bytes_only_api_and_passes_frozen_static_scan() -> (
    None
):
    route = _route_module()
    assert route.ROUTE_ID == ROUTE_ID
    assert route.WIRE_SCHEMA_ID == WIRE_SCHEMA_ID
    assert tuple(inspect.signature(route.encode_normalized_transcript).parameters) == (
        "canonical_transcript_utf8",
    )
    assert tuple(inspect.signature(route.verify_and_decode_route_wire).parameters) == (
        "canonical_route_wire_utf8",
    )

    source = ROUTE_PATH.read_bytes()
    tree = ast.parse(source)
    common_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "common"
    ]
    assert len(common_imports) == 1
    assert [(item.name, item.asname) for item in common_imports[0].names] == [
        ("B7LabMutationRejected", None)
    ]

    common = importlib.import_module("experiments.v3m0_b7_schema_lab.common")
    fields = common._compute_route_static_fields_v1(
        ROUTE_ID,
        "b" * 40,
        ("a" * 40, str(ROUTE_PATH.relative_to(REPOSITORY_ROOT)), "100644", source),
        (
            ("b" * 40, "rulespace_v3/__init__.py", "100644", b""),
            ("b" * 40, "rulespace_gpu/__init__.py", "100644", b""),
        ),
    )
    assert fields["authority_surface_count"] == 0
    assert fields["wrapper_surface_count"] == 0
    assert fields["production_imported_by_route"] is False
    assert fields["route_imported_by_production"] is False
    metrics = common.compute_route_static_metrics_v1(
        ROUTE_ID,
        (
            "a" * 40,
            str(ROUTE_PATH.relative_to(REPOSITORY_ROOT)),
            "100644",
            source,
        ),
    )
    assert set(metrics) == {
        "b8_consumer_assertion_count",
        "b8_consumer_changed_loc",
        "verifier_branch_count",
        "route_record_count",
        "route_hash_layer_count",
    }
    assert metrics["route_record_count"] >= 2
    assert metrics["route_hash_layer_count"] >= 2


@pytest.mark.parametrize("case_id", [row[0] for row in CASE_ROWS])
def test_b_progress_roundtrips_each_terminal_case_as_raw_branch_progress(
    case_id: str,
) -> None:
    route = _route_module()
    transcript = _transcript(case_id)
    source = _canonical(transcript)

    wire_bytes = route.encode_normalized_transcript(source)
    wire = json.loads(wire_bytes)

    assert type(wire_bytes) is bytes
    assert wire_bytes == _canonical(wire)
    assert set(wire) == {
        "wire_schema_version",
        "route_id",
        "transcript_prefix",
        "actual_progress",
        "matched_ablated_progress",
        "terminal_failure",
        "transcript_sha",
        "wire_sha",
    }
    assert wire["wire_schema_version"] == WIRE_SCHEMA_ID
    assert wire["route_id"] == ROUTE_ID
    assert wire["terminal_failure"] == (None if case_id == "success" else case_id)
    for field, attempt_field, response_field, branch in (
        (
            "actual_progress",
            "actual_branch_attempt",
            "actual_completed_response",
            "actual",
        ),
        (
            "matched_ablated_progress",
            "matched_ablated_branch_attempt",
            "matched_ablated_completed_response",
            "matched_ablated",
        ),
    ):
        progress = wire[field]
        attempt = transcript[attempt_field]
        if attempt is None:
            assert progress is None
            continue
        assert set(progress) == {
            "branch",
            "response_values",
            "bridge_audit",
            "completed_response",
            "branch_failure",
            "progress_sha",
        }
        assert progress["branch"] == branch
        assert progress["response_values"] == attempt["response_values"]
        assert progress["bridge_audit"] == attempt["bridge_audit"]
        assert progress["completed_response"] == transcript[response_field]
        assert progress["branch_failure"] == attempt["failure"]
    assert route.verify_and_decode_route_wire(wire_bytes) == source
    assert route.encode_normalized_transcript(source) == wire_bytes
    assert route.verify_and_decode_route_wire(wire_bytes) == source


@pytest.mark.parametrize(
    "api_name", ("encode_normalized_transcript", "verify_and_decode_route_wire")
)
@pytest.mark.parametrize("payload", (None, "{}", bytearray(b"{}"), memoryview(b"{}")))
def test_b_progress_rejects_every_non_bytes_input(
    api_name: str, payload: object
) -> None:
    route = _route_module()
    _assert_rejected(getattr(route, api_name), payload, "NON_BYTES_INPUT")


@pytest.mark.parametrize(
    "mutate",
    (
        lambda raw: raw + b"\n",
        lambda raw: b"\xef\xbb\xbf" + raw,
        lambda raw: raw + raw,
        lambda raw: raw.replace(b'"case_id":', b'"case_id":"success","case_id":', 1),
        lambda raw: b'{"x":NaN}',
        lambda raw: b"\xff",
    ),
)
def test_b_progress_rejects_noncanonical_duplicate_concat_and_invalid_json(
    mutate,
) -> None:
    route = _route_module()
    source = _canonical(_transcript("success"))
    _assert_rejected(
        route.encode_normalized_transcript, mutate(source), "NON_CANONICAL_JSON"
    )
    wire = route.encode_normalized_transcript(source)
    _assert_rejected(
        route.verify_and_decode_route_wire, mutate(wire), "NON_CANONICAL_JSON"
    )


@pytest.mark.parametrize("operation", ("unknown", "missing"))
def test_b_progress_rejects_unknown_or_missing_transcript_and_wire_fields(
    operation: str,
) -> None:
    route = _route_module()
    transcript = _transcript("success")
    if operation == "unknown":
        transcript["unexpected"] = None
    else:
        del transcript["reference_outcome"]
    _assert_rejected(
        route.encode_normalized_transcript,
        _canonical(transcript),
        "UNKNOWN_OR_MISSING_FIELD",
    )

    wire = json.loads(
        route.encode_normalized_transcript(_canonical(_transcript("success")))
    )
    if operation == "unknown":
        wire["unexpected"] = None
    else:
        del wire["route_id"]
    _assert_rejected(
        route.verify_and_decode_route_wire,
        _canonical(wire),
        "UNKNOWN_OR_MISSING_FIELD",
    )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    (
        ("transcript_schema_version", "wrong", "SCHEMA_MISMATCH"),
        ("case_id", "eighth_case", "PRESENCE_MISMATCH"),
        ("terminal_tag", "eighth_case", "PRESENCE_MISMATCH"),
    ),
)
def test_b_progress_rejects_schema_and_case_domain_drift(
    field: str, value: object, reason: str
) -> None:
    route = _route_module()
    transcript = _transcript("success")
    transcript[field] = value
    _seal(transcript, "experimental_sha")
    _assert_rejected(route.encode_normalized_transcript, _canonical(transcript), reason)


@pytest.mark.parametrize(
    "attack",
    (
        "outer_hash",
        "provenance_hash",
        "run_spec_hash",
        "attempt_hash",
        "tensor_hash",
        "progress_hash",
        "wire_hash",
    ),
)
def test_b_progress_rejects_every_self_hash_layer_drift(attack: str) -> None:
    route = _route_module()
    transcript = _transcript("success")
    if attack == "outer_hash":
        transcript["experimental_sha"] = "0" * 64
    elif attack == "provenance_hash":
        transcript["provenance_fixture"]["provenance_fixture_sha"] = "0" * 64
        _seal(transcript, "experimental_sha")
    elif attack == "run_spec_hash":
        transcript["response_run_spec_fixture"]["run_spec_sha"] = "0" * 64
        _seal(transcript, "experimental_sha")
    elif attack == "attempt_hash":
        transcript["actual_branch_attempt"]["attempt_sha"] = "0" * 64
        _seal(transcript, "experimental_sha")
    elif attack == "tensor_hash":
        transcript["actual_branch_attempt"]["response_values"]["tensor_sha"] = "0" * 64
        _seal(transcript["actual_branch_attempt"], "attempt_sha")
        _seal(transcript, "experimental_sha")
    else:
        wire = json.loads(route.encode_normalized_transcript(_canonical(transcript)))
        if attack == "progress_hash":
            wire["actual_progress"]["progress_sha"] = "0" * 64
        else:
            wire["wire_sha"] = "0" * 64
        _assert_rejected(
            route.verify_and_decode_route_wire,
            _canonical(wire),
            "HASH_MISMATCH",
        )
        return
    _assert_rejected(
        route.encode_normalized_transcript,
        _canonical(transcript),
        "HASH_MISMATCH",
    )


def test_b_progress_distinguishes_lineage_shas_from_declared_self_hashes() -> None:
    route = _route_module()
    transcript = _transcript("success")
    provenance = transcript["provenance_fixture"]
    provenance["parent_freeze_v3_body"] = {
        "target_schema_version": "b7-synthetic-capture",
        "target_spec_sha": "1" * 64,
        "seed_sha": "2" * 64,
        "runtime_operator_sha": "3" * 64,
        "primitive": {
            "primitive_schema_version": "b7-synthetic-capture",
            "coefficient_digest": "4" * 64,
        },
        "basis": {
            "basis_schema_version": "b7-synthetic-capture",
            "basis_digest": "5" * 64,
        },
        "attestation": _seal(
            {
                "attestation_schema_version": "b7-synthetic-capture",
                "payload": "frozen",
                "attestation_sha": "",
            },
            "attestation_sha",
        ),
    }
    _seal(provenance, "provenance_fixture_sha")
    _seal(transcript, "experimental_sha")
    source = _canonical(transcript)

    wire = route.encode_normalized_transcript(source)
    assert route.verify_and_decode_route_wire(wire) == source

    renamed = copy.deepcopy(transcript)
    renamed_target = renamed["provenance_fixture"]["parent_freeze_v3_body"]
    renamed_target["renamed_schema_version"] = renamed_target.pop(
        "target_schema_version"
    )
    _seal(renamed["provenance_fixture"], "provenance_fixture_sha")
    _seal(renamed, "experimental_sha")
    _assert_rejected(
        route.encode_normalized_transcript,
        _canonical(renamed),
        "SCHEMA_MISMATCH",
    )

    bad_attestation = copy.deepcopy(transcript)
    bad_parent = bad_attestation["provenance_fixture"]["parent_freeze_v3_body"]
    bad_parent["attestation"]["attestation_sha"] = "0" * 64
    _seal(bad_attestation["provenance_fixture"], "provenance_fixture_sha")
    _seal(bad_attestation, "experimental_sha")
    _assert_rejected(
        route.encode_normalized_transcript,
        _canonical(bad_attestation),
        "HASH_MISMATCH",
    )

    transcript["actual_branch_attempt"]["response_values"]["tensor_sha"] = "0" * 64
    _seal(transcript["actual_branch_attempt"], "attempt_sha")
    _seal(transcript, "experimental_sha")
    _assert_rejected(
        route.encode_normalized_transcript,
        _canonical(transcript),
        "HASH_MISMATCH",
    )


@pytest.mark.parametrize("case_id", [row[0] for row in CASE_ROWS])
def test_b_progress_rejects_presence_terminal_and_branch_failure_mutations(
    case_id: str,
) -> None:
    route = _route_module()
    transcript = _transcript(case_id)
    terminal = copy.deepcopy(transcript)
    terminal["terminal_tag"] = "success" if case_id != "success" else "shell_failure"
    _seal(terminal, "experimental_sha")
    _assert_rejected(
        route.encode_normalized_transcript, _canonical(terminal), "PRESENCE_MISMATCH"
    )

    presence = copy.deepcopy(transcript)
    presence["actual_completed_response"] = (
        None
        if presence["actual_completed_response"] is not None
        else {"injected": True}
    )
    _seal(presence, "experimental_sha")
    _assert_rejected(
        route.encode_normalized_transcript, _canonical(presence), "PRESENCE_MISMATCH"
    )

    if transcript["actual_branch_attempt"] is not None:
        failure = copy.deepcopy(transcript)
        failure["actual_branch_attempt"]["failure"] = "actual_bridge_failed"
        _seal(failure["actual_branch_attempt"], "attempt_sha")
        _seal(failure, "experimental_sha")
        expected = next(row[2] for row in CASE_ROWS if row[0] == case_id)
        if failure["actual_branch_attempt"]["failure"] != expected:
            _assert_rejected(
                route.encode_normalized_transcript,
                _canonical(failure),
                "FAILURE_SCHEDULE_MISMATCH",
            )


@pytest.mark.parametrize(
    "attack",
    (
        "outer_failure",
        "cross_branch_failure",
        "delete_prior_progress",
        "inject_downstream_progress",
        "completed_values_splice",
        "completed_audit_splice",
        "completed_shell_splice",
        "progress_branch_splice",
    ),
)
def test_b_progress_decoder_rejects_outer_progress_and_cross_root_splices(
    attack: str,
) -> None:
    route = _route_module()
    case_id = "success"
    if attack == "inject_downstream_progress":
        case_id = "actual_response_values_failure"
    wire = json.loads(
        route.encode_normalized_transcript(_canonical(_transcript(case_id)))
    )
    if attack == "outer_failure":
        wire["terminal_failure"] = "shell_failure"
    elif attack == "cross_branch_failure":
        wire["actual_progress"]["branch_failure"] = "matched_ablated_response_failed"
        _resign_progress(wire["actual_progress"])
    elif attack == "delete_prior_progress":
        wire["actual_progress"] = None
    elif attack == "inject_downstream_progress":
        wire["matched_ablated_progress"] = copy.deepcopy(wire["actual_progress"])
        wire["matched_ablated_progress"]["branch"] = "matched_ablated"
        wire["matched_ablated_progress"]["branch_failure"] = None
        _resign_progress(wire["matched_ablated_progress"])
    elif attack == "completed_values_splice":
        wire["actual_progress"]["completed_response"]["values"]["values_wire"] = [
            [1.0, 0.0]
        ]
        _seal(
            wire["actual_progress"]["completed_response"]["values"],
            "tensor_sha",
        )
        _seal(wire["actual_progress"]["completed_response"], "response_sha")
        _resign_progress(wire["actual_progress"])
    elif attack == "completed_audit_splice":
        wire["actual_progress"]["completed_response"]["bridge_audit"] = copy.deepcopy(
            wire["matched_ablated_progress"]["bridge_audit"]
        )
        _seal(wire["actual_progress"]["completed_response"], "response_sha")
        _resign_progress(wire["actual_progress"])
    elif attack == "completed_shell_splice":
        wire["actual_progress"]["completed_response"]["shell_manifest_sha"] = "0" * 64
        _seal(wire["actual_progress"]["completed_response"], "response_sha")
        _resign_progress(wire["actual_progress"])
    else:
        wire["actual_progress"]["branch"] = "matched_ablated"
        _resign_progress(wire["actual_progress"])
    _assert_rejected(
        route.verify_and_decode_route_wire,
        _resign_wire(wire),
        "EVIDENCE_MISMATCH"
        if attack
        in (
            "completed_values_splice",
            "completed_audit_splice",
            "completed_shell_splice",
            "progress_branch_splice",
        )
        else "FAILURE_SCHEDULE_MISMATCH",
    )


def test_b_progress_source_contains_no_forbidden_half_pair_surface() -> None:
    source = ROUTE_PATH.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "verified" not in lowered
    assert "issuer" not in lowered
    assert "capability" not in lowered
    tree = ast.parse(source)
    public = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
    ]
    assert public == ["encode_normalized_transcript", "verify_and_decode_route_wire"]
