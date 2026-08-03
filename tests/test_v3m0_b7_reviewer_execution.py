"""TDD coverage for the B7 immutable reviewer execution layer."""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile

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
            "python_invocation_path": "/frozen/python",
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


def _git(repository: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ("/usr/bin/git", *arguments),
        cwd=repository,
        env={"LANG": "C", "LC_ALL": "C"},
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def _make_export_repository(tmp_path: Path, *, hostile_symlink=False):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    bodies = {
        "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json": b"d0\n",
        "data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json": b"d1\n",
        "docsv3/v3-机器合同-B7-v9.1-registry.json": b"v91\n",
        "docsv3/v3-机器合同-B7-v9.2-overlay.json": b"v92\n",
        "docsv3/v3-机器合同-B7-v9.2.1-overlay.json": b"v921\n",
        "experiments/v3m0_b7_schema_lab/__init__.py": b"",
        "experiments/v3m0_b7_schema_lab/common.py": b"COMMON = True\n",
        "experiments/v3m0_b7_schema_lab/compare.py": b"COMPARE = True\n",
        "rulespace_v3/__init__.py": b"",
        "rulespace_v3/runner.sh": b"#!/bin/sh\nexit 0\n",
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json": b"corpus\n",
    }
    for relative, body in bodies.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    os.chmod(repository / "rulespace_v3/runner.sh", 0o755)
    if hostile_symlink:
        os.symlink(
            "/etc/passwd",
            repository / "experiments/v3m0_b7_schema_lab/escape",
        )
    _git(repository, "add", "--all")
    _git(
        repository,
        "-c",
        "user.name=Reviewer Test",
        "-c",
        "user.email=reviewer@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    evidence_commit = _git(repository, "rev-parse", "HEAD").decode().strip()
    return repository, evidence_commit, bodies


def test_immutable_export_reads_only_git_E_and_restores_git_modes(
    tmp_path: Path,
) -> None:
    repository, evidence_commit, bodies = _make_export_repository(tmp_path)
    (repository / "experiments/v3m0_b7_schema_lab/common.py").write_bytes(
        b"HOSTILE WORKTREE DRIFT\n"
    )

    export = compare.materialize_immutable_reviewer_export_v1(
        repository_root=str(repository),
        evidence_commit_sha=evidence_commit,
    )
    export_root = Path(export["export_root"])
    try:
        assert export_root != repository
        assert export["required_input_bytes"] == {
            role: bodies[path]
            for role, path in compare._REVIEWER_REQUIRED_INPUT_PATHS_V1
        }
        assert (
            export_root / "experiments/v3m0_b7_schema_lab/common.py"
        ).read_bytes() == b"COMMON = True\n"
        assert (export_root / "experiments/__init__.py").exists() is False
        assert export["namespace_observation"] == {
            "fresh_export_root_count": 1,
            "experiments_init_present": False,
            "experiments_namespace_portion_count": 1,
            "shadowing_paths": [],
        }
        assert (export_root / "rulespace_v3/runner.sh").stat().st_mode & 0o777 == 0o555
        assert (
            export_root / "experiments/v3m0_b7_schema_lab/common.py"
        ).stat().st_mode & 0o777 == 0o444
    finally:
        assert compare.cleanup_immutable_reviewer_export_v1(export) is True
    assert export_root.exists() is False


def test_immutable_export_rejects_git_symlink_before_archive(tmp_path: Path) -> None:
    repository, evidence_commit, _bodies = _make_export_repository(
        tmp_path,
        hostile_symlink=True,
    )

    with pytest.raises(ValueError, match="mode|blob"):
        compare.materialize_immutable_reviewer_export_v1(
            repository_root=str(repository),
            evidence_commit_sha=evidence_commit,
        )


@pytest.mark.parametrize(
    "name",
    ("/absolute", "../escape", "safe/../../escape", "safe"),
)
def test_tar_member_validator_rejects_unsafe_or_duplicate_paths(name: str) -> None:
    first = tarfile.TarInfo(name)
    first.type = tarfile.REGTYPE
    members = [first]
    if name == "safe":
        duplicate = tarfile.TarInfo(name)
        duplicate.type = tarfile.REGTYPE
        members.append(duplicate)

    with pytest.raises(ValueError):
        compare._validate_reviewer_tar_members_v1(
            members,
            expected_file_paths=("safe",),
        )


def test_trusted_git_environment_and_global_argv_are_literal() -> None:
    assert compare._TRUSTED_GIT_EXECUTABLE_V1 == "/usr/bin/git"
    assert compare.build_sanitized_git_environment_v1() == {
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "",
        "LANG": "C",
        "LC_ALL": "C",
    }
    assert compare._TRUSTED_GIT_GLOBAL_ARGV_V1 == (
        "--no-replace-objects",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "diff.external=",
        "-c",
        "core.attributesFile=/dev/null",
    )


def _receipt_builder_context(role="CORPUS_REPLAY"):
    inputs = _synthetic_replay_inputs()
    d0 = common.strict_json_loads_v1(inputs["d0"])
    d1 = common.strict_json_loads_v1(inputs["d1"])
    source = inputs["compare"]
    source_sha = hashlib.sha256(source).hexdigest()
    closure = CLOSURE
    protocol = {
        "CORPUS_REPLAY": "v3m0-b7-corpus-replay-v2",
        "METRIC_REPLAY": "v3m0-b7-metric-replay-v2",
    }[role]
    projection = {
        "reviewer_role": role,
        "review_protocol_id": protocol,
        "reviewed_lab_evidence_commit_sha": E,
        "review_environment_manifest_sha": d1["environment_manifest"][
            "environment_sha"
        ],
        "reviewed_d0_result_raw_sha256": hashlib.sha256(inputs["d0"]).hexdigest(),
        "reviewed_d0_result_sha": d0["d0_result_sha"],
        "reviewed_d0_decision_payload_sha": d0["decision_payload_sha"],
        "reviewed_d1_result_raw_sha256": hashlib.sha256(inputs["d1"]).hexdigest(),
        "reviewed_d1_result_sha": d1["d1_result_sha"],
        "reviewed_d1_decision_payload_sha": d1["decision_payload_sha"],
        "reviewed_common_commit_sha": d0["common_commit_sha"],
        "reviewed_route_commit_shas": [
            row["route_manifest"]["route_commit_sha"]
            for row in d0["ordered_route_results"]
        ],
        "reviewed_corpus_spec_sha": d0["corpus_spec_sha"],
        "reviewed_mutation_universe_sha": d0["mutation_universe_sha"],
        "reviewed_metric_spec_sha": d0["metric_spec_sha"],
        "reviewed_compare_source_sha256": source_sha,
        "reviewed_executable_source_closure_sha": closure,
        "replay_source_sha256": source_sha,
    }
    report = compare._build_reviewer_replay_report_v1(
        reviewer_role=role,
        evidence_commit_sha=E,
        replay_input_root_sha=common.canonical_sha_v1(projection),
        d0_decision_payload_sha=d0["decision_payload_sha"],
        d1_decision_payload_sha=d1["decision_payload_sha"],
        surviving_route_ids=d1["surviving_route_ids"],
        provisional_winner_route_id=d1["provisional_winner_route_id"],
    )
    stdout = common.canonical_json_bytes_v1(report) + b"\n"
    return {
        "reviewer_id": f"reviewer-{role.lower()}",
        "reviewer_role": role,
        "evidence_commit_sha": E,
        "validated_d0_result": d0,
        "validated_d1_result": d1,
        "d0_raw_bytes": inputs["d0"],
        "d1_raw_bytes": inputs["d1"],
        "environment_observation": {
            "expected_sha": d1["environment_manifest"]["environment_sha"],
            "observed_sha": d1["environment_manifest"]["environment_sha"],
            "passed": True,
        },
        "source_origin_observation": {
            "reviewed_executable_source_closure_sha": closure,
            "observed_executable_source_closure_sha": closure,
            "executable_source_origin_precheck_passed": True,
        },
        "replay_source_blob": (
            E,
            "experiments/v3m0_b7_schema_lab/compare.py",
            "100644",
            source,
        ),
        "process_observation": {
            "termination_kind": "EXITED",
            "exit_code": 0,
            "signal_number": None,
            "stdout_bytes": stdout,
            "stderr_bytes": b"",
            "cleanup_deadline_passed": True,
            "export_cleanup_passed": True,
            "required_input_precheck_passed": True,
        },
    }


def test_receipt_builder_self_audits_canonical_success() -> None:
    context = _receipt_builder_context()

    receipt = compare.build_reviewer_receipt_v1(**context)

    assert receipt["verdict"] == "ACCEPT"
    assert receipt["reason_codes"] == []
    assert receipt["receipt_sha"] == common.canonical_sha_v1(
        {name: value for name, value in receipt.items() if name != "receipt_sha"}
    )


@pytest.mark.parametrize(
    ("termination_kind", "reason"),
    (
        ("TIMED_OUT", "REPLAY_PROCESS_TIMED_OUT"),
        ("OUTPUT_LIMIT_EXCEEDED", "REPLAY_PROCESS_OUTPUT_LIMIT_EXCEEDED"),
    ),
)
def test_receipt_builder_totalizes_timeout_and_output_limit(
    termination_kind: str,
    reason: str,
) -> None:
    context = _receipt_builder_context()
    context["process_observation"] = {
        "termination_kind": termination_kind,
        "exit_code": None,
        "signal_number": None,
        "stdout_bytes": b"bounded-prefix",
        "stderr_bytes": b"",
        "cleanup_deadline_passed": True,
        "export_cleanup_passed": True,
        "required_input_precheck_passed": True,
    }

    receipt = compare.build_reviewer_receipt_v1(**context)

    assert receipt["verdict"] == "REJECT"
    assert reason in receipt["reason_codes"]
    assert "REPLAY_STDOUT_NOT_CANONICAL_REPORT" in receipt["reason_codes"]


_ROUTE_ROWS = (
    (
        "A_FLAT",
        "experimental.v3m0.b7.a-flat",
        "experiments.v3m0_b7_schema_lab.a_flat",
        "experiments/v3m0_b7_schema_lab/a_flat.py",
        "experimental.v3m0.b7.a-flat.wire.v1",
    ),
    (
        "B_PROGRESS",
        "experimental.v3m0.b7.b-progress",
        "experiments.v3m0_b7_schema_lab.b_progress",
        "experiments/v3m0_b7_schema_lab/b_progress.py",
        "experimental.v3m0.b7.b-progress.wire.v1",
    ),
    (
        "C_UNION",
        "experimental.v3m0.b7.c-union",
        "experiments.v3m0_b7_schema_lab.c_union",
        "experiments/v3m0_b7_schema_lab/c_union.py",
        "experimental.v3m0.b7.c-union.wire.v1",
    ),
)


def _route_source(row) -> bytes:
    route_id, _domain, _module, _path, wire_schema = row
    return f'''from __future__ import annotations

ROUTE_ID = "{route_id}"
WIRE_SCHEMA_ID = "{wire_schema}"

def encode_normalized_transcript(canonical_transcript_utf8):
    return canonical_transcript_utf8

def verify_and_decode_route_wire(canonical_route_wire_utf8):
    return canonical_route_wire_utf8
'''.encode()


def _full_route_manifest(
    row,
    *,
    route_commit,
    route_source,
    common_commit,
    common_source_sha,
    compare_source_sha,
    corpus_spec_sha,
    mutation_universe_sha,
    metric_spec_sha,
    production_blobs,
):
    route_id, domain, module, path, wire_schema = row
    computed = common._compute_route_static_fields_v1(
        route_id,
        common_commit,
        (route_commit, path, "100644", route_source),
        production_blobs,
    )
    return _seal(
        {
            "route_manifest_schema_version": (
                "experimental.v3m0.b7.route-manifest.v1"
            ),
            "route_id": route_id,
            "route_schema_domain": domain,
            "route_module": module,
            "route_source_path": path,
            "wire_schema_id": wire_schema,
            "route_commit_sha": route_commit,
            "route_source_sha256": computed["route_source_sha256"],
            "common_commit_sha": common_commit,
            "common_source_sha256": common_source_sha,
            "compare_source_sha256": compare_source_sha,
            "corpus_spec_sha": corpus_spec_sha,
            "mutation_universe_sha": mutation_universe_sha,
            "metric_spec_sha": metric_spec_sha,
            "encoder_symbol": "encode_normalized_transcript",
            "verifier_decoder_symbol": "verify_and_decode_route_wire",
            "input_schema_version": (
                "experimental.v3m0.b7.normalized-transcript.v1"
            ),
            "output_schema_version": wire_schema,
            **computed,
            "route_manifest_sha": "",
        },
        "route_manifest_sha",
    )


def _evidence_comparisons(
    *,
    manifests,
    common_commit,
    common_raw,
    compare_raw,
    fixture,
    fixture_raw,
):
    d0_rows = [
        _seal(
            {
                "route_id": manifest["route_id"],
                "route_manifest": manifest,
                "survives_d0": manifest["route_id"] == "A_FLAT",
                "route_result_sha": "",
            },
            "route_result_sha",
        )
        for manifest in manifests
    ]
    d0 = {
        "d0_result_schema_version": "experimental.v3m0.b7.d0-comparison.v1",
        "common_commit_sha": common_commit,
        "common_source_sha256": hashlib.sha256(common_raw).hexdigest(),
        "compare_source_sha256": hashlib.sha256(compare_raw).hexdigest(),
        "corpus_fixture_raw_sha256": hashlib.sha256(fixture_raw).hexdigest(),
        "corpus_spec_sha": fixture["corpus_spec"]["corpus_spec_sha"],
        "mutation_universe_sha": fixture["mutation_universe"][
            "mutation_universe_sha"
        ],
        "metric_spec_sha": fixture["metric_spec"]["metric_spec_sha"],
        "environment_manifest": fixture["environment_manifest"],
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
            "route_manifest": manifests[0],
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
        "common_commit_sha": common_commit,
        "common_source_sha256": d0["common_source_sha256"],
        "compare_source_sha256": d0["compare_source_sha256"],
        "leaf_provider_source_sha256": hashlib.sha256(
            (REPO_ROOT / "rulespace_v3/b7_replay_core_v1.py").read_bytes()
        ).hexdigest(),
        "corpus_fixture_raw_sha256": d0["corpus_fixture_raw_sha256"],
        "corpus_spec_sha": d0["corpus_spec_sha"],
        "mutation_universe_sha": d0["mutation_universe_sha"],
        "metric_spec_sha": d0["metric_spec_sha"],
        "synthetic_graph_manifest": fixture["synthetic_graph_manifest"],
        "environment_manifest": fixture["environment_manifest"],
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
    return d0, d1, d0_raw, common.canonical_json_bytes_v1(d1)


def _make_reviewer_evidence_repository(tmp_path: Path):
    repository = tmp_path / "evidence-repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    environment = compare.capture_environment_manifest_v2(
        python_invocation_path=sys.executable
    )
    corpus_spec = _seal({"corpus_spec_sha": ""}, "corpus_spec_sha")
    mutation_universe = _seal(
        {"mutation_universe_sha": ""}, "mutation_universe_sha"
    )
    metric_spec = _seal(
        {"metric_order": ["failures"], "metric_spec_sha": ""},
        "metric_spec_sha",
    )
    fixture = _seal(
        {
            "fixture_schema_version": "experimental.v3m0.b7.corpus-fixture.v2",
            "corpus_spec": corpus_spec,
            "mutation_universe": mutation_universe,
            "metric_spec": metric_spec,
            "environment_manifest": environment,
            "synthetic_graph_manifest": {"graph": "reviewer-e2e"},
            "ordered_d0_transcripts": [{"payload": "canonical"}],
            "fixture_sha": "",
        },
        "fixture_sha",
    )
    fixture_raw = common.canonical_json_bytes_v1(fixture)
    common_raw = (
        REPO_ROOT / "experiments/v3m0_b7_schema_lab/common.py"
    ).read_bytes()
    compare_raw = (
        REPO_ROOT / "experiments/v3m0_b7_schema_lab/compare.py"
    ).read_bytes()
    base_bodies = {
        "docsv3/v3-机器合同-B7-v9.1-registry.json": (
            REPO_ROOT / "docsv3/v3-机器合同-B7-v9.1-registry.json"
        ).read_bytes(),
        "docsv3/v3-机器合同-B7-v9.2-overlay.json": (
            REPO_ROOT / "docsv3/v3-机器合同-B7-v9.2-overlay.json"
        ).read_bytes(),
        "docsv3/v3-机器合同-B7-v9.2.1-overlay.json": (
            REPO_ROOT / "docsv3/v3-机器合同-B7-v9.2.1-overlay.json"
        ).read_bytes(),
        "experiments/v3m0_b7_schema_lab/__init__.py": b"",
        "experiments/v3m0_b7_schema_lab/common.py": common_raw,
        "experiments/v3m0_b7_schema_lab/compare.py": compare_raw,
        "rulespace_v3/__init__.py": (
            REPO_ROOT / "rulespace_v3/__init__.py"
        ).read_bytes(),
        "rulespace_v3/b7_replay_core_v1.py": (
            REPO_ROOT / "rulespace_v3/b7_replay_core_v1.py"
        ).read_bytes(),
        "rulespace_gpu/__init__.py": b"",
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json": fixture_raw,
    }
    for relative, body in base_bodies.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    _git(repository, "add", "--all")
    _git(
        repository,
        "-c",
        "user.name=Reviewer Test",
        "-c",
        "user.email=reviewer@example.invalid",
        "commit",
        "-q",
        "-m",
        "common",
    )
    common_commit = _git(repository, "rev-parse", "HEAD").decode().strip()
    production_blobs = tuple(
        (
            common_commit,
            path,
            "100644",
            base_bodies[path],
        )
        for path in (
            "rulespace_v3/__init__.py",
            "rulespace_v3/b7_replay_core_v1.py",
            "rulespace_gpu/__init__.py",
        )
    )
    manifests = []
    for row in _ROUTE_ROWS:
        source = _route_source(row)
        path = repository / row[3]
        path.write_bytes(source)
        _git(repository, "add", row[3])
        _git(
            repository,
            "-c",
            "user.name=Reviewer Test",
            "-c",
            "user.email=reviewer@example.invalid",
            "commit",
            "-q",
            "-m",
            row[0],
        )
        route_commit = _git(repository, "rev-parse", "HEAD").decode().strip()
        manifests.append(
            _full_route_manifest(
                row,
                route_commit=route_commit,
                route_source=source,
                common_commit=common_commit,
                common_source_sha=hashlib.sha256(common_raw).hexdigest(),
                compare_source_sha=hashlib.sha256(compare_raw).hexdigest(),
                corpus_spec_sha=corpus_spec["corpus_spec_sha"],
                mutation_universe_sha=mutation_universe[
                    "mutation_universe_sha"
                ],
                metric_spec_sha=metric_spec["metric_spec_sha"],
                production_blobs=production_blobs,
            )
        )
    d0, d1, d0_raw, d1_raw = _evidence_comparisons(
        manifests=manifests,
        common_commit=common_commit,
        common_raw=common_raw,
        compare_raw=compare_raw,
        fixture=fixture,
        fixture_raw=fixture_raw,
    )
    for relative, body in (
        (
            "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json",
            d0_raw,
        ),
        (
            "data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json",
            d1_raw,
        ),
    ):
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    _git(repository, "add", "--all")
    _git(
        repository,
        "-c",
        "user.name=Reviewer Test",
        "-c",
        "user.email=reviewer@example.invalid",
        "commit",
        "-q",
        "-m",
        "evidence",
    )
    evidence_commit = _git(repository, "rev-parse", "HEAD").decode().strip()
    return repository, evidence_commit, d0, d1


def test_real_E_runs_two_fresh_reviewers_and_joins_identity_and_closure(
    tmp_path: Path,
) -> None:
    repository, evidence_commit, d0, d1 = _make_reviewer_evidence_repository(
        tmp_path
    )

    pair = compare.run_immutable_reviewer_pair_v1(
        reviewer_ids=("independent-corpus", "independent-metric"),
        repository_root=str(repository),
        evidence_commit_sha=evidence_commit,
        validated_d0_result=d0,
        validated_d1_result=d1,
    )

    receipts = pair["reviewer_receipts"]
    contexts = pair["reviewer_receipt_contexts"]
    assert [receipt["reviewer_role"] for receipt in receipts] == [
        "CORPUS_REPLAY",
        "METRIC_REPLAY",
    ]
    assert [receipt["reviewer_id"] for receipt in receipts] == [
        "independent-corpus",
        "independent-metric",
    ]
    assert all(receipt["verdict"] == "ACCEPT" for receipt in receipts)
    assert len(
        {
            receipt["reviewed_executable_source_closure_sha"]
            for receipt in receipts
        }
    ) == 1
    assert pair["all_exports_cleaned"] is True
    assert all(not Path(root).exists() for root in pair["export_roots"])
    for context in contexts:
        process = context["process_observation"]
        assert process["termination_kind"] == "EXITED"
        assert process["exit_code"] == 0
        assert process["stderr_bytes"] == b""
        assert process["stdout_bytes"].endswith(b"\n")
        assert b"\n" not in process["stdout_bytes"][:-1]
        compare.decode_replay_report_stdout_v1(process["stdout_bytes"])
