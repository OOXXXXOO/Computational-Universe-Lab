"""TDD attacks for B7 reviewer receipts and terminal review decisions."""

from __future__ import annotations

import copy

import pytest

from experiments.v3m0_b7_schema_lab import common


def _git_object_oid(object_type, raw_bytes):
    header = f"{object_type} {len(raw_bytes)}\0".encode("ascii")
    return common._pure_core.hashlib.sha1(header + raw_bytes).hexdigest()


_COMMON_COMMIT_BYTES = b"tree " + b"0" * 40 + b"\n\ncommon\n"
COMMON = _git_object_oid("commit", _COMMON_COMMIT_BYTES)
_ROUTE_COMMIT_BYTES = tuple(
    (
        b"tree "
        + str(index + 1).encode("ascii") * 40
        + b"\nparent "
        + COMMON.encode("ascii")
        + b"\n\nroute\n"
    )
    for index in range(3)
)
ROUTES = tuple(_git_object_oid("commit", body) for body in _ROUTE_COMMIT_BYTES)
_EVIDENCE_COMMIT_BYTES = (
    b"tree "
    + b"4" * 40
    + b"\n"
    + b"".join(b"parent " + oid.encode("ascii") + b"\n" for oid in ROUTES)
    + b"\nevidence\n"
)
E = _git_object_oid("commit", _EVIDENCE_COMMIT_BYTES)
SHA = tuple(character * 64 for character in "123456789abcdef0")


def _sha_bytes(value: bytes) -> str:
    return common._pure_core.hashlib.sha256(value).hexdigest()


def _context():
    manifests = [
        {
            "route_id": route_id,
            "route_schema_domain": domain,
            "route_commit_sha": commit,
            "route_source_sha256": source_sha,
        }
        for route_id, domain, commit, source_sha in zip(
            ("A_FLAT", "B_PROGRESS", "C_UNION"),
            (
                "experimental.v3m0.b7.a-flat",
                "experimental.v3m0.b7.b-progress",
                "experimental.v3m0.b7.c-union",
            ),
            ROUTES,
            SHA[:3],
        )
    ]
    environment = {
        "environment_sha": SHA[11],
        "python_invocation_path": "/frozen/venv/bin/python",
    }
    d0 = {
        "d0_result_sha": SHA[3],
        "decision_payload_sha": SHA[4],
        "common_commit_sha": COMMON,
        "common_source_sha256": SHA[5],
        "compare_source_sha256": SHA[6],
        "corpus_fixture_raw_sha256": SHA[7],
        "corpus_spec_sha": SHA[8],
        "mutation_universe_sha": SHA[9],
        "metric_spec_sha": SHA[10],
        "environment_manifest": copy.deepcopy(environment),
        "ordered_route_results": [
            {"route_manifest": manifest} for manifest in manifests
        ],
        "surviving_route_ids": ["A_FLAT", "B_PROGRESS", "C_UNION"],
    }
    d1 = {
        "d1_result_sha": SHA[12],
        "decision_payload_sha": SHA[13],
        "common_commit_sha": COMMON,
        "common_source_sha256": SHA[5],
        "compare_source_sha256": SHA[6],
        "corpus_fixture_raw_sha256": SHA[7],
        "corpus_spec_sha": SHA[8],
        "mutation_universe_sha": SHA[9],
        "metric_spec_sha": SHA[10],
        "environment_manifest": copy.deepcopy(environment),
        "ordered_route_results": [
            {"route_manifest": copy.deepcopy(manifest)} for manifest in manifests
        ],
        "surviving_route_ids": ["A_FLAT"],
        "provisional_winner_route_id": "A_FLAT",
        "tie_detected": False,
    }
    return d0, d1, manifests


def _report(replay_input_root, role="CORPUS_REPLAY"):
    protocol = {
        "CORPUS_REPLAY": "v3m0-b7-corpus-replay-v2",
        "METRIC_REPLAY": "v3m0-b7-metric-replay-v2",
    }[role]
    body = {
        "replay_report_schema_version": "experimental.v3m0.b7.replay-report.v1",
        "reviewer_role": role,
        "review_protocol_id": protocol,
        "lab_evidence_commit_sha": E,
        "replay_input_root_sha": replay_input_root,
        "recomputed_d0_decision_payload_sha": SHA[4],
        "recomputed_d1_decision_payload_sha": SHA[13],
        "observed_surviving_route_ids": ["A_FLAT"],
        "observed_provisional_winner_route_id": "A_FLAT",
        "replay_output_root_sha": "",
        "replay_report_sha": "",
    }
    body["replay_output_root_sha"] = common.canonical_sha_v1(
        {key: body[key] for key in tuple(body)[:9]}
    )
    body["replay_report_sha"] = common.canonical_sha_v1(
        {key: value for key, value in body.items() if key != "replay_report_sha"}
    )
    return body


def _receipt_fixture(
    role="CORPUS_REPLAY",
    reviewer_id="independent-reviewer-corpus",
):
    d0, d1, manifests = _context()
    replay_source = b"placeholder"
    compare_sha = _sha_bytes(replay_source)
    d0["compare_source_sha256"] = compare_sha
    d1["compare_source_sha256"] = compare_sha
    d0_bytes = common.canonical_json_bytes_v1(d0) + b"\n"
    d1["d0_result_raw_sha256"] = _sha_bytes(d0_bytes)
    d1["d0_result_sha"] = d0["d0_result_sha"]
    d1["d0_decision_payload_sha"] = d0["decision_payload_sha"]
    d1_bytes = common.canonical_json_bytes_v1(d1) + b"\n"
    closure = SHA[14]
    protocol, subcommand = {
        "CORPUS_REPLAY": ("v3m0-b7-corpus-replay-v2", "review-corpus"),
        "METRIC_REPLAY": ("v3m0-b7-metric-replay-v2", "review-metric"),
    }[role]
    projection = {
        "reviewer_role": role,
        "review_protocol_id": protocol,
        "reviewed_lab_evidence_commit_sha": E,
        "review_environment_manifest_sha": SHA[11],
        "reviewed_d0_result_raw_sha256": _sha_bytes(d0_bytes),
        "reviewed_d0_result_sha": SHA[3],
        "reviewed_d0_decision_payload_sha": SHA[4],
        "reviewed_d1_result_raw_sha256": _sha_bytes(d1_bytes),
        "reviewed_d1_result_sha": SHA[12],
        "reviewed_d1_decision_payload_sha": SHA[13],
        "reviewed_common_commit_sha": COMMON,
        "reviewed_route_commit_shas": list(ROUTES),
        "reviewed_corpus_spec_sha": SHA[8],
        "reviewed_mutation_universe_sha": SHA[9],
        "reviewed_metric_spec_sha": SHA[10],
        "reviewed_compare_source_sha256": compare_sha,
        "reviewed_executable_source_closure_sha": closure,
        "replay_source_sha256": compare_sha,
    }
    input_root = common.canonical_sha_v1(projection)
    report = _report(input_root, role)
    stdout = common.canonical_json_bytes_v1(report) + b"\n"
    body = {
        "receipt_schema_version": "experimental.v3m0.b7.reviewer-receipt.v1",
        "reviewer_id": reviewer_id,
        **{key: projection[key] for key in tuple(projection)[:3]},
        "review_environment_manifest_sha": SHA[11],
        "observed_review_environment_manifest_sha": SHA[11],
        "review_environment_precheck_passed": True,
        **{key: projection[key] for key in tuple(projection)[4:17]},
        "observed_executable_source_closure_sha": closure,
        "executable_source_origin_precheck_passed": True,
        "replay_source_path": "experiments/v3m0_b7_schema_lab/compare.py",
        "replay_source_sha256": compare_sha,
        "replay_command_argv": [
            "/frozen/venv/bin/python", "-s", "-m",
            "experiments.v3m0_b7_schema_lab.compare", subcommand,
            "--evidence-commit", E,
            "--reviewed-executable-source-closure-sha", closure,
            "--emit-replay-report",
        ],
        "fresh_process_protocol_id": "fresh-python-s-immutable-E-venv-invocation-v2",
        "replay_input_root_sha": input_root,
        "observed_report_reviewer_role": report["reviewer_role"],
        "observed_report_review_protocol_id": report["review_protocol_id"],
        "observed_report_lab_evidence_commit_sha": E,
        "observed_report_replay_input_root_sha": input_root,
        "replay_output_root_sha": report["replay_output_root_sha"],
        "replay_stdout_sha256": _sha_bytes(stdout),
        "replay_stderr_sha256": _sha_bytes(b""),
        "replay_termination_kind": "EXITED",
        "replay_exit_code": 0,
        "replay_signal_number": None,
        "replayed_d0_decision_payload_sha": SHA[4],
        "replayed_d1_decision_payload_sha": SHA[13],
        "observed_surviving_route_ids": ["A_FLAT"],
        "observed_provisional_winner_route_id": "A_FLAT",
        "verdict": "ACCEPT",
        "reason_codes": [],
        "receipt_sha": "",
    }
    body["receipt_sha"] = common.canonical_sha_v1(
        {key: value for key, value in body.items() if key != "receipt_sha"}
    )
    return body, {
        "evidence_commit_sha": E,
        "validated_d0_result": d0,
        "validated_d1_result": d1,
        "d0_raw_bytes": d0_bytes,
        "d1_raw_bytes": d1_bytes,
        "environment_observation": {
            "expected_sha": SHA[11], "observed_sha": SHA[11], "passed": True,
        },
        "source_origin_observation": {
            "reviewed_executable_source_closure_sha": closure,
            "observed_executable_source_closure_sha": closure,
            "executable_source_origin_precheck_passed": True,
        },
        "replay_source_blob": (E, "experiments/v3m0_b7_schema_lab/compare.py", "100644", replay_source),
        "process_observation": {
            "termination_kind": "EXITED", "exit_code": 0, "signal_number": None,
            "stdout_bytes": stdout, "stderr_bytes": b"",
            "cleanup_deadline_passed": True, "export_cleanup_passed": True,
            "required_input_precheck_passed": True,
        },
    }


_RECEIPT_OBSERVATION_FIELDS = (
    "environment_observation",
    "source_origin_observation",
    "replay_source_blob",
    "process_observation",
)


def _receipt_observation_context(context):
    return {field: context[field] for field in _RECEIPT_OBSERVATION_FIELDS}


def _make_precheck_reject(body, context):
    body = copy.deepcopy(body)
    context = copy.deepcopy(context)
    context["environment_observation"] = {
        "expected_sha": SHA[11], "observed_sha": None, "passed": False,
    }
    context["process_observation"] = {
        "termination_kind": "PRECHECK_FAILED",
        "exit_code": None,
        "signal_number": None,
        "stdout_bytes": b"",
        "stderr_bytes": b"",
        "cleanup_deadline_passed": True,
        "export_cleanup_passed": True,
        "required_input_precheck_passed": True,
    }
    body["observed_review_environment_manifest_sha"] = None
    body["review_environment_precheck_passed"] = False
    for field in (
        "observed_report_reviewer_role",
        "observed_report_review_protocol_id",
        "observed_report_lab_evidence_commit_sha",
        "observed_report_replay_input_root_sha",
        "replay_output_root_sha",
        "replayed_d0_decision_payload_sha",
        "replayed_d1_decision_payload_sha",
        "observed_surviving_route_ids",
        "observed_provisional_winner_route_id",
    ):
        body[field] = None
    body["replay_stdout_sha256"] = _sha_bytes(b"")
    body["replay_termination_kind"] = "PRECHECK_FAILED"
    body["replay_exit_code"] = None
    body["reason_codes"] = [
        "REVIEW_ENVIRONMENT_MISMATCH",
        "REPLAY_PROCESS_PRECHECK_FAILED",
        "REPLAY_STDOUT_NOT_CANONICAL_REPORT",
    ]
    body["verdict"] = "REJECT"
    body["receipt_sha"] = common.canonical_sha_v1(
        {key: value for key, value in body.items() if key != "receipt_sha"}
    )
    return body, context


def _terminal_review_fixture(*, halt=False):
    corpus_receipt, corpus_context = _receipt_fixture()
    metric_receipt, metric_context = _receipt_fixture(
        role="METRIC_REPLAY",
        reviewer_id="independent-reviewer-metric",
    )
    if halt:
        metric_receipt, metric_context = _make_precheck_reject(
            metric_receipt,
            metric_context,
        )
    d0 = corpus_context["validated_d0_result"]
    d1 = corpus_context["validated_d1_result"]
    d0_bytes = corpus_context["d0_raw_bytes"]
    d1_bytes = corpus_context["d1_raw_bytes"]
    manifests = [
        row["route_manifest"] for row in d0["ordered_route_results"]
    ]
    common_fields = {
        "lab_evidence_commit_sha": E,
        "d0_result_raw_sha256": _sha_bytes(d0_bytes),
        "d0_result_sha": d0["d0_result_sha"],
        "d0_decision_payload_sha": d0["decision_payload_sha"],
        "d1_result_raw_sha256": _sha_bytes(d1_bytes),
        "d1_result_sha": d1["d1_result_sha"],
        "d1_decision_payload_sha": d1["decision_payload_sha"],
        "common_commit_sha": d0["common_commit_sha"],
        "common_source_sha256": d0["common_source_sha256"],
        "compare_source_sha256": d0["compare_source_sha256"],
        "corpus_fixture_raw_sha256": d0["corpus_fixture_raw_sha256"],
        "corpus_spec_sha": d0["corpus_spec_sha"],
        "mutation_universe_sha": d0["mutation_universe_sha"],
        "metric_spec_sha": d0["metric_spec_sha"],
        "environment_manifest_sha": d0["environment_manifest"]["environment_sha"],
        "ordered_route_commit_shas": [
            manifest["route_commit_sha"] for manifest in manifests
        ],
        "ordered_route_source_sha256s": [
            manifest["route_source_sha256"] for manifest in manifests
        ],
        "provisional_winner_route_id": d1["provisional_winner_route_id"],
        "reviewer_receipts": [corpus_receipt, metric_receipt],
    }
    context = {
        "evidence_commit_sha": E,
        "validated_d0_result": d0,
        "validated_d1_result": d1,
        "d0_raw_bytes": d0_bytes,
        "d1_raw_bytes": d1_bytes,
        "reviewer_receipt_contexts": (
            _receipt_observation_context(corpus_context),
            _receipt_observation_context(metric_context),
        ),
    }
    if halt:
        body = {
            "review_halt_schema_version": "experimental.v3m0.b7.review-halt.v1",
            **common_fields,
            "halt_reason": "HALT_REPLAY_MISMATCH",
            "production_implementation_allowed": False,
            "review_halt_sha": "",
        }
        self_hash_field = "review_halt_sha"
    else:
        selected = manifests[0]
        body = {
            "selection_review_schema_version": (
                "experimental.v3m0.b7.selection-review.v1"
            ),
            **common_fields,
            "review_outcome": "UNIQUE_SCHEMA_SELECTED",
            "selected_route_id": selected["route_id"],
            "selected_route_schema_domain": selected["route_schema_domain"],
            "selected_route_commit_sha": selected["route_commit_sha"],
            "selected_route_source_sha256": selected["route_source_sha256"],
            "engineering_disposition": (
                "B7_UNIQUE_SCHEMA_SELECTED_FOR_IMPLEMENTATION"
            ),
            "production_implementation_allowed": True,
            "selection_review_sha": "",
        }
        self_hash_field = "selection_review_sha"
    body[self_hash_field] = common.canonical_sha_v1(
        {key: value for key, value in body.items() if key != self_hash_field}
    )
    return body, context


def _git_blob(commit, path, raw_bytes):
    return (
        commit,
        path,
        "100644",
        "blob",
        common._git_blob_oid_v1(raw_bytes),
        raw_bytes,
    )


def _handoff_fixture():
    selection, selection_context = _terminal_review_fixture()
    d0 = selection_context["validated_d0_result"]
    d1 = selection_context["validated_d1_result"]
    d0_bytes = selection_context["d0_raw_bytes"]
    d1_bytes = selection_context["d1_raw_bytes"]
    selection_bytes = common.canonical_json_bytes_v1(selection) + b"\n"
    selection_commit_bytes = (
        b"tree "
        + b"5" * 40
        + b"\nparent "
        + E.encode("ascii")
        + b"\n\nselection\n"
    )
    selection_commit = _git_object_oid("commit", selection_commit_bytes)
    tag_object_bytes = (
        b"object "
        + selection_commit.encode("ascii")
        + b"\ntype commit\ntag v3m0-b7-schema-selection-v1\n\nselection\n"
    )
    tag_object = _git_object_oid("tag", tag_object_bytes)
    d0_path = "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json"
    d1_path = "data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json"
    selection_path = (
        "data/results/experimental/v3m0_b7_schema_lab/selection_review.json"
    )
    route_commits = selection["ordered_route_commit_shas"]
    repository_observation = {
        "trusted_git_protocol_passed": True,
        "objects_info_alternates_absent": True,
        "info_grafts_absent": True,
        "evidence_commit_object": (E, "commit", _EVIDENCE_COMMIT_BYTES),
        "common_commit_object": (COMMON, "commit", _COMMON_COMMIT_BYTES),
        "ordered_route_commit_objects": tuple(
            (oid, "commit", raw_bytes)
            for oid, raw_bytes in zip(ROUTES, _ROUTE_COMMIT_BYTES)
        ),
        "common_is_ancestor_of_ordered_routes": [True, True, True],
        "ordered_routes_are_ancestors_of_evidence": [True, True, True],
        "selection_commit_object": (
            selection_commit,
            "commit",
            selection_commit_bytes,
        ),
        "selection_tree_delta": [
            {"status": "A", "mode": "100644", "path": selection_path}
        ],
        "selection_tag_ref_object_oid": tag_object,
        "selection_tag_object": (tag_object, "tag", tag_object_bytes),
        "selection_tag_peeled_target": selection_commit,
        "selection_review_absent_at_evidence": True,
        "review_halt_absent_at_evidence": True,
        "review_halt_absent_at_selection": True,
    }
    assert len(set(route_commits)) == 3
    selected_fields = (
        "selected_route_id",
        "selected_route_schema_domain",
        "selected_route_commit_sha",
        "selected_route_source_sha256",
    )
    handoff = {
        "handoff_schema_version": (
            "experimental.v3m0.b7.production-handoff-review.v1"
        ),
        "git_object_verifier_protocol_id": (
            "v3m0-b7-schema-selection-git-object-handoff-v1"
        ),
        "git_object_format": "sha1",
        "lab_evidence_tag": "v3m0-b7-schema-selection-v1",
        "lab_evidence_tag_object_sha": tag_object,
        "lab_evidence_commit_sha": E,
        "lab_selection_commit_sha": selection_commit,
        "d0_result_path": d0_path,
        "d0_result_raw_sha256": _sha_bytes(d0_bytes),
        "d0_result_sha": d0["d0_result_sha"],
        "d0_decision_payload_sha": d0["decision_payload_sha"],
        "d1_result_path": d1_path,
        "d1_result_raw_sha256": _sha_bytes(d1_bytes),
        "d1_result_sha": d1["d1_result_sha"],
        "d1_decision_payload_sha": d1["decision_payload_sha"],
        "selection_review_path": selection_path,
        "selection_review_raw_sha256": _sha_bytes(selection_bytes),
        "selection_review_sha": selection["selection_review_sha"],
        **{field: selection[field] for field in selected_fields},
        "ordered_reviewer_receipt_shas": [
            receipt["receipt_sha"] for receipt in selection["reviewer_receipts"]
        ],
        "handoff_sha": "",
    }
    handoff["handoff_sha"] = common.canonical_sha_v1(
        {key: value for key, value in handoff.items() if key != "handoff_sha"}
    )
    return handoff, {
        "evidence_commit_sha": E,
        "selection_commit_sha": selection_commit,
        "validated_d0_result": d0,
        "validated_d1_result": d1,
        "d0_blob_observation": _git_blob(E, d0_path, d0_bytes),
        "d1_blob_observation": _git_blob(E, d1_path, d1_bytes),
        "selection_blob_observation": _git_blob(
            selection_commit,
            selection_path,
            selection_bytes,
        ),
        "repository_observation": repository_observation,
        "reviewer_receipt_contexts": selection_context[
            "reviewer_receipt_contexts"
        ],
    }


def test_reviewer_receipt_accepts_fully_joined_accept() -> None:
    body, context = _receipt_fixture()
    assert common.validate_reviewer_receipt_v1(body, **context) == body


def test_reviewer_receipt_accepts_totalized_precheck_reject() -> None:
    body, context = _receipt_fixture()
    body, context = _make_precheck_reject(body, context)

    assert common.validate_reviewer_receipt_v1(body, **context) == body


def test_reviewer_receipt_rejects_non_normalized_process_observation() -> None:
    body, context = _receipt_fixture()
    context["process_observation"]["signal_number"] = 9
    with pytest.raises((TypeError, ValueError)):
        common.validate_reviewer_receipt_v1(body, **context)


def test_selection_review_accepts_two_independent_accept_receipts() -> None:
    body, context = _terminal_review_fixture()
    assert common.validate_selection_review_v1(body, **context) == body


@pytest.mark.parametrize(
    "field",
    (
        "d1_result_raw_sha256",
        "ordered_route_source_sha256s",
        "selected_route_id",
        "production_implementation_allowed",
        "selection_review_sha",
    ),
)
def test_selection_review_rejects_terminal_join_attacks(field: str) -> None:
    body, context = _terminal_review_fixture()
    attacked = copy.deepcopy(body)
    if type(attacked[field]) is bool:
        attacked[field] = not attacked[field]
    elif type(attacked[field]) is list:
        attacked[field][0] = "0" * 64
    else:
        attacked[field] = "0" * 64
    with pytest.raises((TypeError, ValueError)):
        common.validate_selection_review_v1(attacked, **context)


def test_selection_review_rejects_reviewer_context_substitution() -> None:
    body, context = _terminal_review_fixture()
    attacked_context = copy.deepcopy(context)
    attacked_context["reviewer_receipt_contexts"] = (
        context["reviewer_receipt_contexts"][0],
        context["reviewer_receipt_contexts"][0],
    )
    with pytest.raises((TypeError, ValueError)):
        common.validate_selection_review_v1(body, **attacked_context)


def test_review_halt_accepts_completed_reviewer_reject() -> None:
    body, context = _terminal_review_fixture(halt=True)
    assert common.validate_review_halt_v1(body, **context) == body


def test_review_halt_classifies_two_nonnull_replay_observations_as_divergence(
) -> None:
    body, context = _terminal_review_fixture()
    metric_receipt = body["reviewer_receipts"][1]
    metric_context = context["reviewer_receipt_contexts"][1]
    stdout = metric_context["process_observation"]["stdout_bytes"]
    report = common.strict_json_loads_v1(stdout[:-1])
    report["observed_provisional_winner_route_id"] = "B_PROGRESS"
    report["replay_output_root_sha"] = common.canonical_sha_v1(
        {
            key: report[key]
            for key in (
                "replay_report_schema_version",
                "reviewer_role",
                "review_protocol_id",
                "lab_evidence_commit_sha",
                "replay_input_root_sha",
                "recomputed_d0_decision_payload_sha",
                "recomputed_d1_decision_payload_sha",
                "observed_surviving_route_ids",
                "observed_provisional_winner_route_id",
            )
        }
    )
    report["replay_report_sha"] = common.canonical_sha_v1(
        {
            key: value
            for key, value in report.items()
            if key != "replay_report_sha"
        }
    )
    attacked_stdout = common.canonical_json_bytes_v1(report) + b"\n"
    metric_context["process_observation"]["stdout_bytes"] = attacked_stdout
    metric_receipt["observed_provisional_winner_route_id"] = "B_PROGRESS"
    metric_receipt["replay_output_root_sha"] = report["replay_output_root_sha"]
    metric_receipt["replay_stdout_sha256"] = _sha_bytes(attacked_stdout)
    metric_receipt["reason_codes"] = ["REPLAY_WINNER_MISMATCH"]
    metric_receipt["verdict"] = "REJECT"
    metric_receipt["receipt_sha"] = common.canonical_sha_v1(
        {
            key: value
            for key, value in metric_receipt.items()
            if key != "receipt_sha"
        }
    )
    halt = {
        "review_halt_schema_version": "experimental.v3m0.b7.review-halt.v1",
        **{
            key: value
            for key, value in body.items()
            if key
            not in (
                "selection_review_schema_version",
                "review_outcome",
                "selected_route_id",
                "selected_route_schema_domain",
                "selected_route_commit_sha",
                "selected_route_source_sha256",
                "engineering_disposition",
                "production_implementation_allowed",
                "selection_review_sha",
            )
        },
        "halt_reason": "HALT_REVIEW_DIVERGENCE",
        "production_implementation_allowed": False,
        "review_halt_sha": "",
    }
    halt["review_halt_sha"] = common.canonical_sha_v1(
        {key: value for key, value in halt.items() if key != "review_halt_sha"}
    )

    assert common.validate_review_halt_v1(halt, **context) == halt


@pytest.mark.parametrize(
    "field",
    ("halt_reason", "production_implementation_allowed", "review_halt_sha"),
)
def test_review_halt_rejects_terminal_attacks(field: str) -> None:
    body, context = _terminal_review_fixture(halt=True)
    attacked = copy.deepcopy(body)
    if type(attacked[field]) is bool:
        attacked[field] = not attacked[field]
    else:
        attacked[field] = "0" * 64
    with pytest.raises((TypeError, ValueError)):
        common.validate_review_halt_v1(attacked, **context)


def test_review_halt_rejects_two_accept_receipts() -> None:
    body, _ = _terminal_review_fixture(halt=True)
    _, accept_context = _terminal_review_fixture()
    accept_body, _ = _terminal_review_fixture()
    attacked = copy.deepcopy(body)
    attacked["reviewer_receipts"] = accept_body["reviewer_receipts"]
    attacked["review_halt_sha"] = common.canonical_sha_v1(
        {key: value for key, value in attacked.items() if key != "review_halt_sha"}
    )
    with pytest.raises((TypeError, ValueError)):
        common.validate_review_halt_v1(attacked, **accept_context)


def test_production_handoff_accepts_git_bound_selection() -> None:
    body, context = _handoff_fixture()
    assert common.validate_production_handoff_v1(body, **context) == body


@pytest.mark.parametrize(
    "field",
    (
        "lab_evidence_tag_object_sha",
        "selection_review_raw_sha256",
        "selection_review_sha",
        "selected_route_source_sha256",
        "ordered_reviewer_receipt_shas",
        "handoff_sha",
    ),
)
def test_production_handoff_rejects_record_join_attacks(field: str) -> None:
    body, context = _handoff_fixture()
    attacked = copy.deepcopy(body)
    if type(attacked[field]) is list:
        attacked[field][0] = "0" * 64
    else:
        attacked[field] = "0" * len(attacked[field])
    with pytest.raises((TypeError, ValueError)):
        common.validate_production_handoff_v1(attacked, **context)


@pytest.mark.parametrize(
    "attack",
    (
        "parent",
        "tree_delta",
        "tag_target",
        "tag_bytes",
        "ancestry",
        "selection_blob_oid",
    ),
)
def test_production_handoff_rejects_git_observation_attacks(attack: str) -> None:
    body, context = _handoff_fixture()
    attacked = copy.deepcopy(context)
    repository = attacked["repository_observation"]
    if attack == "parent":
        object_oid, object_type, raw_bytes = repository["selection_commit_object"]
        repository["selection_commit_object"] = (
            object_oid,
            object_type,
            raw_bytes.replace(E.encode("ascii"), b"0" * 40),
        )
    elif attack == "tree_delta":
        repository["selection_tree_delta"][0]["mode"] = "100755"
    elif attack == "tag_target":
        repository["selection_tag_peeled_target"] = E
    elif attack == "tag_bytes":
        object_oid, object_type, raw_bytes = repository["selection_tag_object"]
        repository["selection_tag_object"] = (
            object_oid,
            object_type,
            raw_bytes.replace(b"type commit", b"type tree  "),
        )
    elif attack == "ancestry":
        repository["ordered_routes_are_ancestors_of_evidence"][1] = False
    else:
        blob = list(attacked["selection_blob_observation"])
        blob[4] = "0" * 40
        attacked["selection_blob_observation"] = tuple(blob)
    with pytest.raises((TypeError, ValueError)):
        common.validate_production_handoff_v1(body, **attacked)


def test_production_handoff_rejects_gpu_or_runtime_authority_field() -> None:
    body, context = _handoff_fixture()
    attacked = copy.deepcopy(body)
    attacked["gpu_permit"] = True
    with pytest.raises((TypeError, ValueError)):
        common.validate_production_handoff_v1(attacked, **context)


@pytest.mark.parametrize("field", (
    "review_protocol_id", "replay_command_argv", "replay_stdout_sha256",
    "observed_report_lab_evidence_commit_sha", "reason_codes", "receipt_sha",
))
def test_reviewer_receipt_rejects_join_attacks(field: str) -> None:
    body, context = _receipt_fixture()
    attacked = copy.deepcopy(body)
    attacked[field] = ["forged"] if isinstance(attacked[field], list) else "0" * 64
    with pytest.raises((TypeError, ValueError)):
        common.validate_reviewer_receipt_v1(attacked, **context)
