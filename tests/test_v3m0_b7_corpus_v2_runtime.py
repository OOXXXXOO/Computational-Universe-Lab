"""Executable orchestration contract for the graph-bearing B7 corpus V2."""

from __future__ import annotations

import copy

import pytest

from rulespace_v3.b7_replay_core_v1 import canonical_sha_v1


CASE_IDS = (
    "reference_failure",
    "shell_failure",
    "actual_response_values_failure",
    "matched_response_values_failure",
    "actual_bridge_failure",
    "matched_bridge_failure",
    "success",
)
CORPUS_V2_FIELDS = (
    "fixture_schema_version",
    "corpus_spec",
    "mutation_universe",
    "metric_spec",
    "environment_manifest",
    "synthetic_graph_manifest",
    "ordered_d0_transcripts",
    "fixture_sha",
)


def _common():
    from experiments.v3m0_b7_schema_lab import common

    return common


def _seal_fixture(raw: dict[str, object]) -> dict[str, object]:
    raw["fixture_sha"] = canonical_sha_v1(
        {name: value for name, value in raw.items() if name != "fixture_sha"}
    )
    return raw


def _fixture() -> dict[str, object]:
    corpus_sha = "1" * 64
    environment_sha = "2" * 64
    return _seal_fixture(
        {
            "fixture_schema_version": ("experimental.v3m0.b7.corpus-fixture.v2"),
            "corpus_spec": {
                "metric_spec_sha": "3" * 64,
                "mutation_generation_contract_sha": "4" * 64,
                "corpus_spec_sha": corpus_sha,
            },
            "mutation_universe": {
                "corpus_spec_sha": corpus_sha,
                "mutation_universe_sha": "5" * 64,
            },
            "metric_spec": {"metric_spec_sha": "3" * 64},
            "environment_manifest": {"environment_sha": environment_sha},
            "synthetic_graph_manifest": {
                "graph_sha": "6" * 64,
                "complete_body": {"owner": "fixture"},
            },
            "ordered_d0_transcripts": [
                {
                    "case_id": case_id,
                    "corpus_spec_sha": corpus_sha,
                    "environment_manifest_sha": environment_sha,
                }
                for case_id in CASE_IDS
            ],
            "fixture_sha": "",
        }
    )


def _install_fixture_validator_spies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    event_log: list[tuple[str, object]],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    common = _common()
    identity = {"identity": "caller-owned"}
    probe = {"probe": "caller-owned"}
    verified_graph: dict[str, object] = {
        "graph_sha": "6" * 64,
        "complete_body": {"owner": "fixture"},
    }

    def validate_corpus(raw: object, metric_sha: object) -> object:
        event_log.append(("corpus", metric_sha))
        return raw

    def validate_mutation(
        raw: object,
        transcripts: object,
        corpus_sha: object,
        generation_sha: object,
        source_bytes: object,
    ) -> object:
        event_log.append(
            (
                "mutation",
                (transcripts, corpus_sha, generation_sha, source_bytes),
            )
        )
        return raw

    def validate_metric(
        raw: object,
        common_source: object,
        compare_source: object,
    ) -> object:
        event_log.append(("metric", (common_source, compare_source)))
        return raw

    def validate_environment(
        raw: object,
        *,
        python_identity_observation: object,
        python_probe_result: object,
    ) -> object:
        event_log.append(
            (
                "environment",
                (python_identity_observation, python_probe_result),
            )
        )
        return raw

    def validate_graph(raw: object) -> object:
        event_log.append(("graph", raw))
        verified_graph.clear()
        verified_graph.update(copy.deepcopy(raw))
        return verified_graph

    def validate_transcript(
        raw: object,
        *,
        corpus_spec_sha: object,
        environment_manifest_sha: object,
        validated_graph: object,
    ) -> object:
        event_log.append(
            (
                "transcript",
                (
                    raw["case_id"],
                    corpus_spec_sha,
                    environment_manifest_sha,
                    validated_graph,
                    validated_graph is verified_graph,
                ),
            )
        )
        return raw

    monkeypatch.setattr(common, "validate_corpus_spec_v1", validate_corpus)
    monkeypatch.setattr(common, "validate_mutation_universe_v1", validate_mutation)
    monkeypatch.setattr(common, "validate_metric_spec_v1", validate_metric)
    monkeypatch.setattr(
        common, "validate_environment_manifest_v2", validate_environment
    )
    monkeypatch.setattr(common, "validate_synthetic_graph_manifest_v1", validate_graph)
    monkeypatch.setattr(
        common,
        "_validate_normalized_transcript_against_validated_graph_v1",
        validate_transcript,
    )
    return identity, probe, verified_graph


def _validate_with_spies(
    monkeypatch: pytest.MonkeyPatch,
    raw: dict[str, object],
    event_log: list[tuple[str, object]],
) -> dict[str, object]:
    common = _common()
    identity, probe, _verified_graph = _install_fixture_validator_spies(
        monkeypatch,
        event_log=event_log,
    )
    return common.validate_corpus_fixture_v2(
        raw,
        b"common-source",
        b"compare-source",
        python_identity_observation=identity,
        python_probe_result=probe,
    )


def test_corpus_v2_runs_frozen_validation_order_and_reuses_one_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, object]] = []
    raw = _fixture()

    observed = _validate_with_spies(monkeypatch, raw, events)

    assert observed == raw
    assert [name for name, _detail in events] == [
        "corpus",
        "mutation",
        "metric",
        "environment",
        "graph",
        *("transcript" for _ in CASE_IDS),
    ]
    graph_events = [detail for name, detail in events if name == "graph"]
    assert graph_events == [raw["synthetic_graph_manifest"]]
    transcript_events = [detail for name, detail in events if name == "transcript"]
    assert [detail[0] for detail in transcript_events] == list(CASE_IDS)
    assert all(detail[-1] is True for detail in transcript_events)
    environment_event = next(detail for name, detail in events if name == "environment")
    assert environment_event[0] == {"identity": "caller-owned"}
    assert environment_event[1] == {"probe": "caller-owned"}


def test_corpus_v2_rejects_nonexact_top_level_before_nested_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    raw = _fixture()
    raw["unknown"] = None
    monkeypatch.setattr(
        common,
        "validate_corpus_spec_v1",
        lambda *_args, **_kwargs: pytest.fail("nested validation ran"),
    )

    with pytest.raises((TypeError, ValueError)):
        common.validate_corpus_fixture_v2(
            raw,
            b"common-source",
            b"compare-source",
            python_identity_observation={},
            python_probe_result={},
        )


def test_corpus_v2_normalizes_top_level_field_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, object]] = []
    raw = _fixture()
    reordered = {name: raw[name] for name in reversed(CORPUS_V2_FIELDS)}

    observed = _validate_with_spies(monkeypatch, reordered, events)

    assert tuple(observed) == CORPUS_V2_FIELDS


@pytest.mark.parametrize(
    "mutator",
    (
        lambda raw: raw["ordered_d0_transcripts"].reverse(),
        lambda raw: raw["ordered_d0_transcripts"][0].update(corpus_spec_sha="0" * 64),
        lambda raw: raw["ordered_d0_transcripts"][0].update(
            environment_manifest_sha="0" * 64
        ),
    ),
)
def test_corpus_v2_rejects_resigned_case_order_and_cross_root_attacks(
    monkeypatch: pytest.MonkeyPatch,
    mutator,
) -> None:
    events: list[tuple[str, object]] = []
    raw = _fixture()
    mutator(raw)
    _seal_fixture(raw)

    with pytest.raises((TypeError, ValueError)):
        _validate_with_spies(monkeypatch, raw, events)


def test_corpus_v2_self_hash_covers_complete_graph_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, object]] = []
    raw = _fixture()
    raw["synthetic_graph_manifest"]["complete_body"]["owner"] = "substituted"

    with pytest.raises((TypeError, ValueError)):
        _validate_with_spies(monkeypatch, raw, events)


def test_validated_graph_path_calls_every_graph_dependent_validator_without_recheck(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    graph = {"graph_sha": "6" * 64, "complete_body": {"owner": "fixture"}}
    provenance = {"provenance": "body"}
    run_spec = {"run": "spec"}
    reference = {"reference": "body"}
    shell = {
        "reference_outcome": reference,
        "shell": {"shell_manifest_sha": "7" * 64},
    }
    actual_attempt = {
        "branch": "actual",
        "response_values": {"branch": "actual"},
        "bridge_audit": {"branch": "actual"},
    }
    matched_attempt = {
        "branch": "matched_ablated",
        "response_values": {"branch": "matched_ablated"},
        "bridge_audit": {"branch": "matched_ablated"},
    }
    transcript = {
        "case_id": "success",
        "corpus_spec_sha": "1" * 64,
        "environment_manifest_sha": "2" * 64,
        "provenance_fixture": provenance,
        "response_run_spec_fixture": run_spec,
        "reference_outcome": reference,
        "shell_outcome": shell,
        "actual_branch_attempt": actual_attempt,
        "matched_ablated_branch_attempt": matched_attempt,
        "actual_completed_response": {
            "branch": "actual",
            "values": actual_attempt["response_values"],
            "bridge_audit": actual_attempt["bridge_audit"],
            "shell_manifest_sha": "7" * 64,
        },
        "matched_ablated_completed_response": {
            "branch": "matched_ablated",
            "values": matched_attempt["response_values"],
            "bridge_audit": matched_attempt["bridge_audit"],
            "shell_manifest_sha": "7" * 64,
        },
    }
    graph_calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        common,
        "validate_synthetic_graph_manifest_v1",
        lambda _raw: pytest.fail("validated graph was rechecked"),
    )
    monkeypatch.setattr(common, "validate_case_contract_v1", lambda raw: raw)
    monkeypatch.setattr(common, "validate_provenance_fixture_v1", lambda raw: raw)

    def validate_run(raw: object, joined_provenance: object, joined_graph: object):
        graph_calls.append(("run", joined_graph))
        assert joined_provenance is provenance
        return raw

    def validate_response(
        raw: object,
        joined_run: object,
        joined_provenance: object,
        joined_graph: object,
    ):
        graph_calls.append((raw["branch"], joined_graph))
        assert joined_run is run_spec
        assert joined_provenance is provenance
        return raw

    monkeypatch.setattr(common, "validate_response_run_spec_fixture_v1", validate_run)
    monkeypatch.setattr(
        common,
        "validate_source_readout_response_raw_v1",
        validate_response,
    )
    monkeypatch.setattr(
        common,
        "validate_endpoint_reference_outcome_raw_v1",
        lambda raw: raw,
    )
    monkeypatch.setattr(
        common,
        "validate_endpoint_shell_outcome_raw_v1",
        lambda raw: raw,
    )
    monkeypatch.setattr(common, "validate_branch_attempt_v1", lambda raw: raw)
    monkeypatch.setattr(
        common,
        "_reference_lineage_context_v1",
        lambda *_args: {"actual": {}, "matched_ablated": {}},
    )
    monkeypatch.setattr(common, "_validate_shell_lineage_v1", lambda *_args: None)
    monkeypatch.setattr(
        common,
        "_validate_branch_attempt_lineage_v1",
        lambda *_args: None,
    )

    observed = common._validate_normalized_transcript_against_validated_graph_v1(
        transcript,
        corpus_spec_sha="1" * 64,
        environment_manifest_sha="2" * 64,
        validated_graph=graph,
    )

    assert observed == transcript
    assert graph_calls == [
        ("run", graph),
        ("actual", graph),
        ("matched_ablated", graph),
    ]
    assert all(joined_graph is graph for _name, joined_graph in graph_calls)


def test_corpus_v2_rejects_graph_mutation_after_single_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    events: list[tuple[str, object]] = []
    raw = _fixture()
    identity, probe, _verified = _install_fixture_validator_spies(
        monkeypatch,
        event_log=events,
    )

    def mutate_graph(
        transcript: object,
        *,
        corpus_spec_sha: object,
        environment_manifest_sha: object,
        validated_graph: object,
    ) -> object:
        del corpus_spec_sha, environment_manifest_sha
        validated_graph["complete_body"]["owner"] = transcript["case_id"]
        return transcript

    monkeypatch.setattr(
        common,
        "_validate_normalized_transcript_against_validated_graph_v1",
        mutate_graph,
    )

    with pytest.raises((TypeError, ValueError)):
        common.validate_corpus_fixture_v2(
            raw,
            b"common-source",
            b"compare-source",
            python_identity_observation=identity,
            python_probe_result=probe,
        )


def test_corpus_v2_rejects_validated_transcript_body_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    events: list[tuple[str, object]] = []
    raw = _fixture()
    identity, probe, _verified = _install_fixture_validator_spies(
        monkeypatch,
        event_log=events,
    )

    def substitute_transcript(
        transcript: object,
        *,
        corpus_spec_sha: object,
        environment_manifest_sha: object,
        validated_graph: object,
    ) -> object:
        del corpus_spec_sha, environment_manifest_sha, validated_graph
        substituted = copy.deepcopy(transcript)
        substituted["body_substitution"] = True
        return substituted

    monkeypatch.setattr(
        common,
        "_validate_normalized_transcript_against_validated_graph_v1",
        substitute_transcript,
    )

    with pytest.raises((TypeError, ValueError)):
        common.validate_corpus_fixture_v2(
            raw,
            b"common-source",
            b"compare-source",
            python_identity_observation=identity,
            python_probe_result=probe,
        )
