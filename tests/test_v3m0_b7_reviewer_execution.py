"""TDD coverage for the B7 immutable reviewer execution layer."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from experiments.v3m0_b7_schema_lab import common, compare


E = "e" * 40
CLOSURE = "c" * 64
REPO_ROOT = Path(__file__).resolve().parents[1]


def _seal(body, field):
    body[field] = common.canonical_sha_v1(
        {name: value for name, value in body.items() if name != field}
    )
    return body


def _synthetic_replay_inputs():
    environment = _seal(
        {
            "environment_schema_version": "test-environment.v1",
            "environment_sha": "",
        },
        "environment_sha",
    )
    metric_spec = _seal(
        {"metric_order": ["failures"], "metric_spec_sha": ""},
        "metric_spec_sha",
    )
    corpus_spec = _seal({"corpus_spec_sha": ""}, "corpus_spec_sha")
    mutation_universe = _seal(
        {"mutation_universe_sha": ""},
        "mutation_universe_sha",
    )
    fixture = _seal(
        {
            "fixture_schema_version": "experimental.v3m0.b7.corpus-fixture.v2",
            "corpus_spec": corpus_spec,
            "mutation_universe": mutation_universe,
            "metric_spec": metric_spec,
            "environment_manifest": environment,
            "synthetic_graph_manifest": {"graph": "test"},
            "ordered_d0_transcripts": [{"payload": "canonical"}],
            "fixture_sha": "",
        },
        "fixture_sha",
    )
    fixture_raw = common.canonical_json_bytes_v1(fixture)
    manifests = []
    d0_rows = []
    for ordinal, route_id in enumerate(("A_FLAT", "B_PROGRESS", "C_UNION")):
        manifest = _seal(
            {
                "route_id": route_id,
                "route_commit_sha": f"{ordinal + 1}" * 40,
                "route_manifest_sha": "",
            },
            "route_manifest_sha",
        )
        manifests.append(manifest)
        d0_rows.append(
            _seal(
                {
                    "route_id": route_id,
                    "route_manifest": manifest,
                    "survives_d0": route_id == "A_FLAT",
                    "route_result_sha": "",
                },
                "route_result_sha",
            )
        )
    common_raw = (
        REPO_ROOT / "experiments/v3m0_b7_schema_lab/common.py"
    ).read_bytes()
    compare_raw = (
        REPO_ROOT / "experiments/v3m0_b7_schema_lab/compare.py"
    ).read_bytes()
    d0 = {
        "d0_result_schema_version": "experimental.v3m0.b7.d0-comparison.v1",
        "common_commit_sha": "a" * 40,
        "common_source_sha256": hashlib.sha256(common_raw).hexdigest(),
        "compare_source_sha256": hashlib.sha256(compare_raw).hexdigest(),
        "corpus_fixture_raw_sha256": hashlib.sha256(fixture_raw).hexdigest(),
        "corpus_spec_sha": corpus_spec["corpus_spec_sha"],
        "mutation_universe_sha": mutation_universe["mutation_universe_sha"],
        "metric_spec_sha": metric_spec["metric_spec_sha"],
        "environment_manifest": environment,
        "ordered_route_results": d0_rows,
        "surviving_route_ids": ["A_FLAT"],
        "decision_payload_sha": "",
        "auxiliary_benchmark": None,
        "d0_result_sha": "",
    }
    d0["decision_payload_sha"] = common.canonical_sha_v1(
        {name: d0[name] for name in compare._D0_COMPARISON_FIELDS_V1[:11]}
    )
    _seal(d0, "d0_result_sha")
    d0_raw = common.canonical_json_bytes_v1(d0)
    metric_vector = _seal(
        {"failures": 0, "metric_vector_sha": ""},
        "metric_vector_sha",
    )
    d1_row = _seal(
        {
            "route_id": "A_FLAT",
            "metric_vector": metric_vector,
            "survives_d1": True,
            "route_result_sha": "",
        },
        "route_result_sha",
    )
    d1 = {
        "d1_result_schema_version": "experimental.v3m0.b7.d1-comparison.v1",
        "d0_result_raw_sha256": hashlib.sha256(d0_raw).hexdigest(),
        "d0_result_sha": d0["d0_result_sha"],
        "d0_decision_payload_sha": d0["decision_payload_sha"],
        "common_commit_sha": d0["common_commit_sha"],
        "common_source_sha256": d0["common_source_sha256"],
        "compare_source_sha256": d0["compare_source_sha256"],
        "leaf_provider_source_sha256": "b" * 64,
        "corpus_fixture_raw_sha256": d0["corpus_fixture_raw_sha256"],
        "corpus_spec_sha": d0["corpus_spec_sha"],
        "mutation_universe_sha": d0["mutation_universe_sha"],
        "metric_spec_sha": d0["metric_spec_sha"],
        "synthetic_graph_manifest": fixture["synthetic_graph_manifest"],
        "environment_manifest": environment,
        "ordered_capture_transcript_set_shas": [],
        "ordered_capture_leaf_digest_set_shas": [],
        "ordered_route_results": [d1_row],
        "surviving_route_ids": ["A_FLAT"],
        "minimum_metric_vector": metric_vector,
        "provisional_winner_route_id": "A_FLAT",
        "tie_detected": False,
        "decision_payload_sha": "",
        "auxiliary_benchmark": None,
        "d1_result_sha": "",
    }
    d1["decision_payload_sha"] = common.canonical_sha_v1(
        {name: d1[name] for name in compare._D1_DECISION_FIELDS_V1}
    )
    _seal(d1, "d1_result_sha")
    contract_inputs = {
        role: (REPO_ROOT / path).read_bytes()
        for role, path in (
            ("registry_base", "docsv3/v3-机器合同-B7-v9.1-registry.json"),
            ("registry_overlay", "docsv3/v3-机器合同-B7-v9.2-overlay.json"),
            (
                "registry_overlay_v921",
                "docsv3/v3-机器合同-B7-v9.2.1-overlay.json",
            ),
        )
    }
    return {
        "d0": d0_raw,
        "d1": common.canonical_json_bytes_v1(d1),
        "common": common_raw,
        "compare": compare_raw,
        "corpus": fixture_raw,
        **contract_inputs,
    }


def _report(role="CORPUS_REPLAY"):
    protocol = {
        "CORPUS_REPLAY": "v3m0-b7-corpus-replay-v2",
        "METRIC_REPLAY": "v3m0-b7-metric-replay-v2",
    }[role]
    report = {
        "replay_report_schema_version": "experimental.v3m0.b7.replay-report.v1",
        "reviewer_role": role,
        "review_protocol_id": protocol,
        "lab_evidence_commit_sha": E,
        "replay_input_root_sha": "1" * 64,
        "recomputed_d0_decision_payload_sha": "2" * 64,
        "recomputed_d1_decision_payload_sha": "3" * 64,
        "observed_surviving_route_ids": ["A_FLAT"],
        "observed_provisional_winner_route_id": "A_FLAT",
        "replay_output_root_sha": "",
        "replay_report_sha": "",
    }
    report["replay_output_root_sha"] = common.canonical_sha_v1(
        {key: report[key] for key in tuple(report)[:9]}
    )
    report["replay_report_sha"] = common.canonical_sha_v1(
        {
            key: value
            for key, value in report.items()
            if key != "replay_report_sha"
        }
    )
    return report


@pytest.mark.parametrize(
    ("subcommand", "role"),
    (("review-corpus", "CORPUS_REPLAY"), ("review-metric", "METRIC_REPLAY")),
)
def test_child_dispatch_emits_only_one_canonical_report_frame(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    subcommand: str,
    role: str,
) -> None:
    expected = _report(role)

    def fake_execute(*, reviewer_role, evidence_commit_sha, source_closure_sha):
        assert reviewer_role == role
        assert evidence_commit_sha == E
        assert source_closure_sha == CLOSURE
        return copy.deepcopy(expected)

    monkeypatch.setattr(compare, "_execute_reviewer_replay_v1", fake_execute)

    assert compare.main(
        [
            subcommand,
            "--evidence-commit",
            E,
            "--reviewed-executable-source-closure-sha",
            CLOSURE,
            "--emit-replay-report",
        ]
    ) == 0
    stdout, stderr = capfd.readouterr()
    assert stdout.encode("utf-8") == common.canonical_json_bytes_v1(expected) + b"\n"
    assert stderr == ""


@pytest.mark.parametrize(
    "argv",
    (
        [],
        ["review-corpus", "--evidence-commit", E],
        [
            "review-corpus",
            "--evidence-commit",
            E,
            "--reviewed-executable-source-closure-sha",
            CLOSURE,
        ],
    ),
)
def test_child_dispatch_rejects_incomplete_protocol(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        compare.main(argv)


def test_replay_report_builder_binds_role_input_and_decision_roots() -> None:
    report = compare._build_reviewer_replay_report_v1(
        reviewer_role="METRIC_REPLAY",
        evidence_commit_sha=E,
        replay_input_root_sha="1" * 64,
        d0_decision_payload_sha="2" * 64,
        d1_decision_payload_sha="3" * 64,
        surviving_route_ids=["A_FLAT"],
        provisional_winner_route_id="A_FLAT",
    )

    assert report == _report("METRIC_REPLAY")
    assert compare.validate_replay_report_v1(report) == report


def test_replay_report_builder_rejects_non_unique_winner() -> None:
    with pytest.raises((TypeError, ValueError)):
        compare._build_reviewer_replay_report_v1(
            reviewer_role="CORPUS_REPLAY",
            evidence_commit_sha=E,
            replay_input_root_sha="1" * 64,
            d0_decision_payload_sha="2" * 64,
            d1_decision_payload_sha="3" * 64,
            surviving_route_ids=[],
            provisional_winner_route_id="A_FLAT",
        )


@pytest.mark.parametrize("role", ("CORPUS_REPLAY", "METRIC_REPLAY"))
def test_execute_reviewer_replay_recomputes_frozen_roots(
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    replayed = []
    inputs = _synthetic_replay_inputs()
    monkeypatch.setattr(compare, "_read_reviewer_inputs_v1", lambda: inputs)
    monkeypatch.setattr(
        compare,
        "_replay_all_routes_v1",
        lambda transcripts: replayed.extend(transcripts),
    )

    report = compare._execute_reviewer_replay_v1(
        reviewer_role=role,
        evidence_commit_sha=E,
        source_closure_sha=CLOSURE,
    )

    d0 = common.strict_json_loads_v1(inputs["d0"])
    d1 = common.strict_json_loads_v1(inputs["d1"])
    assert replayed == [{"payload": "canonical"}]
    assert report["recomputed_d0_decision_payload_sha"] == d0[
        "decision_payload_sha"
    ]
    assert report["recomputed_d1_decision_payload_sha"] == d1[
        "decision_payload_sha"
    ]
    assert report["observed_provisional_winner_route_id"] == "A_FLAT"
    assert compare.validate_replay_report_v1(report) == report
