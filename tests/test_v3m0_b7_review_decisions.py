"""TDD attacks for B7 reviewer receipts and terminal review decisions."""

from __future__ import annotations

import copy

import pytest

from experiments.v3m0_b7_schema_lab import common


E = "e" * 40
COMMON = "c" * 40
ROUTES = ("a" * 40, "b" * 40, "d" * 40)
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
        "environment_manifest": {"environment_sha": SHA[11]},
        "ordered_route_results": [
            {"route_manifest": manifest} for manifest in manifests
        ],
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
        "environment_manifest": {
            "environment_sha": SHA[11],
            "python_invocation_path": "/frozen/venv/bin/python",
        },
        "surviving_route_ids": ["A_FLAT"],
        "provisional_winner_route_id": "A_FLAT",
        "tie_detected": False,
    }
    return d0, d1, manifests


def _report(replay_input_root):
    body = {
        "replay_report_schema_version": "experimental.v3m0.b7.replay-report.v1",
        "reviewer_role": "CORPUS_REPLAY",
        "review_protocol_id": "v3m0-b7-corpus-replay-v2",
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


def _receipt_fixture():
    d0, d1, manifests = _context()
    replay_source = b"placeholder"
    compare_sha = _sha_bytes(replay_source)
    d0["compare_source_sha256"] = compare_sha
    d1["compare_source_sha256"] = compare_sha
    d0_bytes = common.canonical_json_bytes_v1(d0) + b"\n"
    d1_bytes = common.canonical_json_bytes_v1(d1) + b"\n"
    closure = SHA[14]
    projection = {
        "reviewer_role": "CORPUS_REPLAY",
        "review_protocol_id": "v3m0-b7-corpus-replay-v2",
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
    report = _report(input_root)
    stdout = common.canonical_json_bytes_v1(report) + b"\n"
    body = {
        "receipt_schema_version": "experimental.v3m0.b7.reviewer-receipt.v1",
        "reviewer_id": "independent-reviewer-corpus",
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
            "experiments.v3m0_b7_schema_lab.compare", "review-corpus",
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


def test_reviewer_receipt_accepts_fully_joined_accept() -> None:
    body, context = _receipt_fixture()
    assert common.validate_reviewer_receipt_v1(body, **context) == body


def test_reviewer_receipt_accepts_totalized_precheck_reject() -> None:
    body, context = _receipt_fixture()
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

    assert common.validate_reviewer_receipt_v1(body, **context) == body


def test_reviewer_receipt_rejects_non_normalized_process_observation() -> None:
    body, context = _receipt_fixture()
    context["process_observation"]["signal_number"] = 9
    with pytest.raises((TypeError, ValueError)):
        common.validate_reviewer_receipt_v1(body, **context)


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
