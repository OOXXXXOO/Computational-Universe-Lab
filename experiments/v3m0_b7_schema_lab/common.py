"""Owner-neutral common contracts for the B7 schema laboratory."""

from __future__ import annotations

import rulespace_v3.b7_replay_core_v1 as _pure_core


class B7LabMutationRejected(ValueError):
    """Frozen route-level rejection surface for one invalid lab wire."""


_D0_COMPARISON_FIELDS = (
    "d0_result_schema_version",
    "common_commit_sha",
    "common_source_sha256",
    "compare_source_sha256",
    "corpus_fixture_raw_sha256",
    "corpus_spec_sha",
    "mutation_universe_sha",
    "metric_spec_sha",
    "environment_manifest",
    "ordered_route_results",
    "surviving_route_ids",
    "decision_payload_sha",
    "auxiliary_benchmark",
    "d0_result_sha",
)
_D0_DECISION_FIELDS = _D0_COMPARISON_FIELDS[:11]
_D1_COMPARISON_FIELDS = (
    "d1_result_schema_version",
    "d0_result_raw_sha256",
    "d0_result_sha",
    "d0_decision_payload_sha",
    "common_commit_sha",
    "common_source_sha256",
    "compare_source_sha256",
    "leaf_provider_source_sha256",
    "corpus_fixture_raw_sha256",
    "corpus_spec_sha",
    "mutation_universe_sha",
    "metric_spec_sha",
    "synthetic_graph_manifest",
    "environment_manifest",
    "ordered_capture_transcript_set_shas",
    "ordered_capture_leaf_digest_set_shas",
    "ordered_route_results",
    "surviving_route_ids",
    "minimum_metric_vector",
    "provisional_winner_route_id",
    "tie_detected",
    "decision_payload_sha",
    "auxiliary_benchmark",
    "d1_result_sha",
)
_D1_DECISION_FIELDS = (
    _D1_COMPARISON_FIELDS[0],
    *_D1_COMPARISON_FIELDS[3:21],
)

B8_CONSUMER_SKELETON_UTF8 = (
    b"import json\n"
    b"from __ROUTE_MODULE__ import verify_and_decode_route_wire\n"
    b"from experiments.v3m0_b7_schema_lab.common import "
    b"_b8_require_absent, _b8_require_exact, _b8_require_present\n"
    b"\n"
    b'ROUTE_ID = "__ROUTE_ID__"\n'
    b'WIRE_SCHEMA_ID = "__WIRE_SCHEMA_ID__"\n'
    b"\n"
    b"def consume_b7_paired_response(canonical_route_wire_utf8):\n"
    b"    decoded = verify_and_decode_route_wire(canonical_route_wire_utf8)\n"
    b'    transcript = json.loads(decoded.decode("utf-8"))\n'
    b'    _b8_require_exact(transcript.get("transcript_schema_version"), '
    b'"experimental.v3m0.b7.normalized-transcript.v1", '
    b'"transcript_schema_version")\n'
    b'    _b8_require_exact(transcript.get("terminal_tag"), "success", '
    b'"terminal_tag")\n'
    b'    _b8_require_present(transcript.get("actual_branch_attempt"), '
    b'"actual_branch_attempt")\n'
    b'    _b8_require_present(transcript.get("matched_ablated_branch_attempt"), '
    b'"matched_ablated_branch_attempt")\n'
    b'    _b8_require_absent(transcript["actual_branch_attempt"].get("failure"), '
    b'"actual_failure")\n'
    b"    _b8_require_absent("
    b'transcript["matched_ablated_branch_attempt"].get("failure"), '
    b'"matched_failure")\n'
    b'    _b8_require_present(transcript.get("actual_completed_response"), '
    b'"actual_completed_response")\n'
    b"    _b8_require_present("
    b'transcript.get("matched_ablated_completed_response"), '
    b'"matched_ablated_completed_response")\n'
    b'    return (transcript["actual_completed_response"], '
    b'transcript["matched_ablated_completed_response"])\n'
)

_ROUTE_RENDER_TRIPLES = (
    (
        "A_FLAT",
        "experiments.v3m0_b7_schema_lab.a_flat",
        "experimental.v3m0.b7.a-flat.wire.v1",
    ),
    (
        "B_PROGRESS",
        "experiments.v3m0_b7_schema_lab.b_progress",
        "experimental.v3m0.b7.b-progress.wire.v1",
    ),
    (
        "C_UNION",
        "experiments.v3m0_b7_schema_lab.c_union",
        "experimental.v3m0.b7.c-union.wire.v1",
    ),
)


def _b8_require_exact(observed, expected, field):
    if type(field) is not str:
        raise TypeError("B8 exact field label must be an exact str")
    if observed != expected or type(observed) is not type(expected):
        raise ValueError(f"B8 {field} differs")


def _b8_require_present(observed, field):
    if type(field) is not str:
        raise TypeError("B8 present field label must be an exact str")
    if observed is None:
        raise ValueError(f"B8 {field} is absent")


def _b8_require_absent(observed, field):
    if type(field) is not str:
        raise TypeError("B8 absent field label must be an exact str")
    if observed is not None:
        raise ValueError(f"B8 {field} is present")


def render_b8_consumer_adapter_utf8(route_id, route_module, wire_schema_id):
    """Render the frozen test-only B8 adapter for one exact route triple."""
    if (
        type(route_id) is not str
        or type(route_module) is not str
        or type(wire_schema_id) is not str
    ):
        raise TypeError("B8 route renderer inputs must be exact strings")
    if (route_id, route_module, wire_schema_id) not in _ROUTE_RENDER_TRIPLES:
        raise ValueError("B8 route renderer triple is not frozen")
    return (
        B8_CONSUMER_SKELETON_UTF8.replace(
            b"__ROUTE_MODULE__",
            route_module.encode("utf-8"),
        )
        .replace(b"__ROUTE_ID__", route_id.encode("utf-8"))
        .replace(b"__WIRE_SCHEMA_ID__", wire_schema_id.encode("utf-8"))
    )


def _validate_decision_projection_v1(raw_body, fields, projection_fields):
    if type(raw_body) is not dict:
        raise TypeError("decision payload owner must be an exact dict")
    if tuple(raw_body) != fields:
        raise ValueError("decision payload owner field order drifted")
    projection = {name: raw_body[name] for name in projection_fields}
    if raw_body["decision_payload_sha"] != _pure_core.canonical_sha_v1(projection):
        raise ValueError("decision payload projection hash mismatch")
    return _pure_core.strict_json_loads_v1(_pure_core.canonical_json_bytes_v1(raw_body))


def validate_d0_decision_payload_projection_v1(raw_body):
    """Validate and detach the frozen D0 decision projection."""
    return _validate_decision_projection_v1(
        raw_body,
        _D0_COMPARISON_FIELDS,
        _D0_DECISION_FIELDS,
    )


def validate_d1_decision_payload_projection_v1(raw_body):
    """Validate and detach the frozen D1 decision projection."""
    return _validate_decision_projection_v1(
        raw_body,
        _D1_COMPARISON_FIELDS,
        _D1_DECISION_FIELDS,
    )


def validate_response_run_spec_fixture_v1(
    raw_body,
    provenance_raw,
    graph_raw,
):
    """Delegate one response-run-spec raw validation to the pure core."""
    return _pure_core.validate_response_run_spec_fixture_v1(
        raw_body,
        provenance_raw,
        graph_raw,
    )


def validate_endpoint_reference_outcome_raw_v1(raw_body):
    """Delegate one endpoint-reference raw validation to the pure core."""
    return _pure_core.validate_endpoint_reference_outcome_raw_v1(raw_body)


def validate_endpoint_shell_outcome_raw_v1(raw_body):
    """Delegate one endpoint-shell raw validation to the pure core."""
    return _pure_core.validate_endpoint_shell_outcome_raw_v1(raw_body)


def validate_source_readout_response_raw_v1(
    raw_body,
    run_spec_raw,
    provenance_raw,
    graph_raw,
):
    """Delegate one source/readout raw validation to the pure core."""
    return _pure_core.validate_source_readout_response_raw_v1(
        raw_body,
        run_spec_raw,
        provenance_raw,
        graph_raw,
    )


def validate_synthetic_parent_freeze_v3_body_v1(raw_body):
    """Delegate one synthetic Parent raw validation to the pure core."""
    return _pure_core.validate_synthetic_parent_freeze_v3_body_v1(raw_body)


def validate_synthetic_component_body_v1(
    raw_body,
    ordered_components_raw,
    parent_raw,
):
    """Delegate one synthetic component raw validation to the pure core."""
    return _pure_core.validate_synthetic_component_body_v1(
        raw_body,
        ordered_components_raw,
        parent_raw,
    )


def validate_provenance_fixture_v1(raw_body):
    """Delegate one provenance fixture validation to the pure core."""
    return _pure_core.validate_provenance_fixture_v1(raw_body)


def validate_branch_attempt_v1(raw_body):
    """Delegate one branch-attempt validation to the pure core."""
    return _pure_core.validate_branch_attempt_v1(raw_body)
