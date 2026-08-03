"""D1 capture-to-route wiring for the B7 schema laboratory."""

from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pytest

from experiments.v3m0_b7_schema_lab import common


CASE_IDS = tuple(row[1] for row in common._CASE_CONTRACTS_V1)
ROUTE_IDS = ("A_FLAT", "B_PROGRESS", "C_UNION")


def _mutation(
    ordinal: int,
    *,
    probe_kind: str,
    mutation_class: str = "TERMINAL_TAG",
) -> dict[str, object]:
    return {
        "mutation_schema_version": "experimental.v3m0.b7.mutation.v1",
        "mutation_ordinal": ordinal,
        "mutation_id": f"M{ordinal:06d}-{mutation_class}",
        "base_case_id": None if probe_kind.startswith("UPSTREAM_") else "success",
        "probe_kind": probe_kind,
        "mutation_class": mutation_class,
        "target_json_pointer": None if probe_kind.startswith("UPSTREAM_") else "/x",
        "operation": "UPSTREAM_ZERO"
        if probe_kind.startswith("UPSTREAM_")
        else "SET_VALUE",
        "replacement_json": None,
        "expected_boundary": (
            "UPSTREAM_HARNESS"
            if probe_kind.startswith("UPSTREAM_")
            else "ROUTE_VERIFICATION"
        ),
        "mutation_sha": f"{ordinal + 1:x}" * 64,
    }


def _source_sets() -> list[list[dict[str, object]]]:
    return [
        [
            {
                "case_id": case_id,
                "capture_marker": capture_ordinal,
                "ordered_leaf_digests": [
                    {
                        "leaf_id": "reference",
                        "call_ordinal": 0,
                        "input_body_sha": f"{capture_ordinal + 1:x}" * 64,
                        "output_body_sha": f"{case_ordinal + 1:x}" * 64,
                    }
                ],
            }
            for case_ordinal, case_id in enumerate(CASE_IDS)
        ]
        for capture_ordinal in range(3)
    ]


def _source_bytes() -> list[list[bytes]]:
    return [
        [common.canonical_json_bytes_v1(source) for source in source_set]
        for source_set in _source_sets()
    ]


def _install_capture_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, object], dict[str, int]]:
    source_sets = _source_sets()
    d0_sources = copy.deepcopy(source_sets[0])
    for source in d0_sources:
        source["capture_marker"] = "D0"
    mutations = [
        _mutation(0, probe_kind="MUTATION_MUST_REJECT"),
        _mutation(1, probe_kind="ROUNDTRIP_MUST_EQUAL", mutation_class="ROUNDTRIP"),
        _mutation(2, probe_kind="REPEAT_MUST_EQUAL", mutation_class="REPEAT"),
        _mutation(
            3,
            probe_kind="UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT",
            mutation_class="UPSTREAM_INVALID",
        ),
    ]
    fixture = {
        "corpus_spec": {"corpus_spec_sha": "c" * 64},
        "environment_manifest": {"environment_sha": "e" * 64},
        "synthetic_graph_manifest": {
            "selected_fejer_order": 256,
            "graph_sha": "f" * 64,
        },
        "ordered_d0_transcripts": d0_sources,
        "mutation_universe": {
            "ordered_mutations": copy.deepcopy(mutations),
            "mutation_count": len(mutations),
            "mutation_universe_sha": "a" * 64,
        },
    }
    counters = {"mutation_materializations": 0, "presence_candidates": 0}

    monkeypatch.setattr(common, "validate_case_contract_v1", copy.deepcopy)
    monkeypatch.setattr(
        common,
        "validate_synthetic_graph_manifest_v1",
        copy.deepcopy,
    )
    monkeypatch.setattr(
        common,
        "_validate_normalized_transcript_against_validated_graph_v1",
        lambda raw, **_kwargs: copy.deepcopy(raw),
    )
    monkeypatch.setattr(
        common,
        "_validated_d0_fixture_source_domain_v1",
        lambda observed: (observed, [copy.deepcopy(d0_sources)]),
    )
    monkeypatch.setattr(
        common,
        "_validated_gate_fixture_source_domain_v1",
        lambda phase, observed, supplied: (
            (observed, copy.deepcopy(supplied))
            if phase == "D1"
            else (observed, [copy.deepcopy(d0_sources)])
        ),
    )
    monkeypatch.setattr(common, "validate_mutation_v1", copy.deepcopy)
    monkeypatch.setattr(
        common,
        "generate_ordered_mutations_v1",
        lambda _sources: copy.deepcopy(mutations),
    )
    monkeypatch.setattr(
        common,
        "discover_record_self_hashes_v1",
        lambda source: {"case_id": source["case_id"]},
    )

    def materialize(base, mutation, _success, _snapshot):
        counters["mutation_materializations"] += 1
        return {
            "case_id": base["case_id"],
            "capture_marker": base["capture_marker"],
            "mutation_id": mutation["mutation_id"],
        }

    def candidates(success):
        for ordinal in range(1393):
            counters["presence_candidates"] += 1
            yield {
                "terminal_tag": "success",
                "bit_integer": ordinal,
                "presence_bits": f"{ordinal % 512:09b}",
                "half_pair": False,
                "transcript": {
                    "case_id": "invalid-presence",
                    "capture_marker": success["capture_marker"],
                    "candidate_ordinal": ordinal,
                },
            }

    monkeypatch.setattr(common, "apply_transcript_mutation_v1", materialize)
    monkeypatch.setattr(
        common,
        "iter_constructible_invalid_presence_candidates_v1",
        candidates,
    )
    return fixture, counters


def _install_route_bytes_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.v3m0_b7_schema_lab import compare

    def pipeline(route_id, source_bytes):
        assert route_id in ROUTE_IDS
        assert type(source_bytes) is bytes
        return (
            {
                "termination_kind": "RETURNED_BYTES",
                "raw_bytes": route_id.encode() + b":" + source_bytes,
            },
            {"termination_kind": "RETURNED_BYTES", "raw_bytes": source_bytes},
        )

    def encode(route_id, source_bytes):
        assert route_id in ROUTE_IDS
        assert type(source_bytes) is bytes
        return {"termination_kind": "B7LabMutationRejected", "raw_bytes": None}

    monkeypatch.setattr(compare, "_call_d0_route_pipeline_v1", pipeline)
    monkeypatch.setattr(compare, "_call_d0_route_encode_v1", encode)


def test_d1_gate_input_iterator_has_fixed_harness_boundary_signature() -> None:
    from experiments.v3m0_b7_schema_lab.compare import iter_d1_gate_inputs_v1

    assert tuple(inspect.signature(iter_d1_gate_inputs_v1).parameters) == (
        "validated_corpus_fixture",
        "ordered_survivor_route_ids",
        "ordered_capture_source_bytes",
    )


def test_d1_route_input_builder_wires_only_d0_survivors_to_capture_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.v3m0_b7_schema_lab import compare

    manifests = {
        route_id: {"route_id": route_id, "route_manifest_sha": f"{ordinal + 1:x}" * 64}
        for ordinal, route_id in enumerate(ROUTE_IDS)
    }
    d0 = {
        "common_commit_sha": "a" * 40,
        "ordered_route_results": [
            {"route_id": route_id, "route_manifest": copy.deepcopy(manifests[route_id])}
            for route_id in ROUTE_IDS
        ],
        "surviving_route_ids": ["A_FLAT", "C_UNION"],
    }
    d0_inputs = [
        {
            "route_manifest": copy.deepcopy(manifests[route_id]),
            "route_blob": ("a" * 40, f"{route_id}.py", "100644", route_id.encode()),
            "production_blobs": (("a" * 40, "common.py", "100644", b"common"),),
            "gate_inputs": {
                "ordered_legal_replays": [],
                "ordered_mutation_probes": iter(()),
                "ordered_invalid_presence_probes": iter(()),
            },
        }
        for route_id in ROUTE_IDS
    ]
    gate_inputs = {
        route_id: {
            "ordered_legal_replays": [{"route_id": route_id}],
            "ordered_mutation_probes": iter(()),
            "ordered_invalid_presence_probes": iter(()),
        }
        for route_id in ("A_FLAT", "C_UNION")
    }
    monkeypatch.setattr(
        common,
        "validate_exact_lab_record_v1",
        lambda _record, observed: copy.deepcopy(observed),
    )
    monkeypatch.setattr(
        common, "validate_d0_decision_payload_projection_v1", lambda raw: raw
    )
    monkeypatch.setattr(
        common,
        "_validate_d0_route_inputs_v1",
        lambda observed, _commit: observed,
    )
    capture_calls = 0

    def capture(**kwargs):
        nonlocal capture_calls
        capture_calls += 1
        assert kwargs["ordered_survivor_route_ids"] == ["A_FLAT", "C_UNION"]
        for route_id in ("A_FLAT", "C_UNION"):
            yield route_id, gate_inputs[route_id]

    monkeypatch.setattr(compare, "iter_d1_gate_inputs_v1", capture)

    result = compare.build_d1_route_inputs_from_capture_v1(
        d0_comparison=d0,
        ordered_d0_route_inputs=d0_inputs,
        validated_corpus_fixture={"fixture": True},
        ordered_capture_source_bytes=_source_bytes(),
    )

    assert capture_calls == 1
    assert [row["route_manifest"]["route_id"] for row in result] == [
        "A_FLAT",
        "C_UNION",
    ]
    assert [row["gate_inputs"] for row in result] == [
        gate_inputs["A_FLAT"],
        gate_inputs["C_UNION"],
    ]
    assert result[0]["route_blob"] is d0_inputs[0]["route_blob"]
    assert result[1]["route_blob"] is d0_inputs[2]["route_blob"]


def test_d1_route_input_builder_rejects_d0_manifest_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.v3m0_b7_schema_lab import compare

    d0 = {
        "common_commit_sha": "a" * 40,
        "ordered_route_results": [
            {
                "route_id": "A_FLAT",
                "route_manifest": {"route_id": "A_FLAT", "identity": "D0"},
            }
        ],
        "surviving_route_ids": ["A_FLAT"],
    }
    d0_inputs = [
        {
            "route_manifest": {"route_id": "A_FLAT", "identity": "DRIFT"},
            "route_blob": (),
            "production_blobs": (),
            "gate_inputs": {},
        }
    ]
    monkeypatch.setattr(
        common,
        "validate_exact_lab_record_v1",
        lambda _record, observed: copy.deepcopy(observed),
    )
    monkeypatch.setattr(
        common, "validate_d0_decision_payload_projection_v1", lambda raw: raw
    )
    monkeypatch.setattr(
        common,
        "_validate_d0_route_inputs_v1",
        lambda observed, _commit: observed,
    )
    monkeypatch.setattr(
        compare,
        "iter_d1_gate_inputs_v1",
        lambda **_kwargs: iter((("A_FLAT", {}),)),
    )

    with pytest.raises(ValueError, match="manifest"):
        compare.build_d1_route_inputs_from_capture_v1(
            d0_comparison=d0,
            ordered_d0_route_inputs=d0_inputs,
            validated_corpus_fixture={},
            ordered_capture_source_bytes=_source_bytes(),
        )


def test_d1_capture_broadcasts_21_bytes_and_uses_capture_specific_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import iter_d1_gate_inputs_v1

    fixture, _counters = _install_capture_domain(monkeypatch)
    _install_route_bytes_stubs(monkeypatch)
    captured = iter_d1_gate_inputs_v1(
        validated_corpus_fixture=fixture,
        ordered_survivor_route_ids=["A_FLAT", "C_UNION"],
        ordered_capture_source_bytes=_source_bytes(),
    )

    for expected_route_id in ("A_FLAT", "C_UNION"):
        route_id, inputs = next(captured)
        assert route_id == expected_route_id
        assert tuple(inputs) == (
            "ordered_legal_replays",
            "ordered_mutation_probes",
            "ordered_invalid_presence_probes",
        )
        legal = inputs["ordered_legal_replays"]
        assert len(legal) == 21
        assert [row["capture_ordinal"] for row in legal] == [
            capture_ordinal
            for capture_ordinal in range(3)
            for _case_ordinal in range(7)
        ]
        assert [row["case_id"] for row in legal] == list(CASE_IDS) * 3
        assert all(type(row["source_transcript_bytes"]) is bytes for row in legal)

        mutations = inputs["ordered_mutation_probes"]
        presence = inputs["ordered_invalid_presence_probes"]
        assert iter(mutations) is mutations
        assert iter(presence) is presence
        mutation_rows = list(mutations)
        assert len(mutation_rows) == 12
        first_by_capture = [mutation_rows[offset] for offset in (0, 4, 8)]
        assert [
            common.strict_json_loads_v1(row["materialized_transcript_bytes"])[
                "capture_marker"
            ]
            for row in first_by_capture
        ] == [0, 1, 2]
        assert list(mutations) == []

        presence_rows = list(presence)
        assert len(presence_rows) == 3 * 1393
        assert [
            presence_rows[offset]["capture_ordinal"] for offset in (0, 1393, 2786)
        ] == [
            0,
            1,
            2,
        ]
        assert [
            common.strict_json_loads_v1(
                presence_rows[offset]["candidate_transcript_bytes"]
            )["capture_marker"]
            for offset in (0, 1393, 2786)
        ] == [0, 1, 2]
        assert list(presence) == []
    with pytest.raises(StopIteration):
        next(captured)


def test_d1_capture_keeps_large_domains_lazy_and_one_shot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import iter_d1_gate_inputs_v1

    fixture, counters = _install_capture_domain(monkeypatch)
    _install_route_bytes_stubs(monkeypatch)
    _route_id, inputs = next(
        iter_d1_gate_inputs_v1(
            validated_corpus_fixture=fixture,
            ordered_survivor_route_ids=["B_PROGRESS"],
            ordered_capture_source_bytes=_source_bytes(),
        )
    )
    mutation_stream = inputs["ordered_mutation_probes"]
    presence_stream = inputs["ordered_invalid_presence_probes"]
    assert counters == {"mutation_materializations": 0, "presence_candidates": 0}

    first_mutation = next(mutation_stream)
    assert first_mutation["capture_ordinal"] == 0
    assert counters["mutation_materializations"] == 1
    first_presence = next(presence_stream)
    assert first_presence["capture_ordinal"] == 0
    assert counters["presence_candidates"] == 1


def test_d1_capture_validates_all_21_t256_graph_lineages_before_route_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.v3m0_b7_schema_lab import compare

    fixture, _counters = _install_capture_domain(monkeypatch)
    lineage_calls = []
    route_calls = 0

    def validate_lineage(raw, **kwargs):
        lineage_calls.append((raw["case_id"], kwargs["validated_graph"]["graph_sha"]))
        return copy.deepcopy(raw)

    def route(*_args):
        nonlocal route_calls
        route_calls += 1
        return (
            {"termination_kind": "RETURNED_BYTES", "raw_bytes": b"wire"},
            {"termination_kind": "RETURNED_BYTES", "raw_bytes": b"decoded"},
        )

    monkeypatch.setattr(
        common,
        "_validate_normalized_transcript_against_validated_graph_v1",
        validate_lineage,
    )
    monkeypatch.setattr(compare, "_call_d0_route_pipeline_v1", route)

    _route_id, _inputs = next(
        compare.iter_d1_gate_inputs_v1(
            validated_corpus_fixture=fixture,
            ordered_survivor_route_ids=["A_FLAT"],
            ordered_capture_source_bytes=_source_bytes(),
        )
    )

    assert len(lineage_calls) == 21
    assert [case_id for case_id, _graph_sha in lineage_calls] == list(CASE_IDS) * 3
    assert {graph_sha for _case_id, graph_sha in lineage_calls} == {"f" * 64}
    assert route_calls == 21


@pytest.mark.parametrize(
    "route_ids",
    (
        [],
        ["C_UNION", "A_FLAT"],
        ["A_FLAT", "A_FLAT"],
        ["NOT_FROZEN"],
        ("A_FLAT",),
    ),
)
def test_d1_capture_rejects_noncanonical_survivor_route_domains_before_route_entry(
    monkeypatch: pytest.MonkeyPatch,
    route_ids,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import iter_d1_gate_inputs_v1

    fixture, _counters = _install_capture_domain(monkeypatch)
    route_calls = 0

    def forbidden(*_args):
        nonlocal route_calls
        route_calls += 1
        raise AssertionError("route entered before survivor validation")

    from experiments.v3m0_b7_schema_lab import compare

    monkeypatch.setattr(compare, "_call_d0_route_pipeline_v1", forbidden)
    with pytest.raises((TypeError, ValueError)):
        next(
            iter_d1_gate_inputs_v1(
                validated_corpus_fixture=fixture,
                ordered_survivor_route_ids=route_ids,
                ordered_capture_source_bytes=_source_bytes(),
            )
        )
    assert route_calls == 0


def _capture_stdout(capture_ordinal: int) -> bytes:
    return (
        common.canonical_json_bytes_v1(
            {
                "capture_ordinal": capture_ordinal,
                "ordered_transcripts": _source_sets()[capture_ordinal],
            }
        )
        + b"\n"
    )


def test_fresh_process_capture_outer_spawns_three_fixed_children_and_validates_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from experiments.v3m0_b7_schema_lab import compare

    fixture = {
        "environment_manifest": {"python_invocation_path": "/frozen/python"},
        "fixture": "validated",
    }
    fixture_path = tmp_path / "corpus.json"
    fixture_path.write_bytes(common.canonical_json_bytes_v1(fixture) + b"\n")
    fixture_path.chmod(0o444)
    observations: list[tuple[str, ...]] = []

    def run(**kwargs):
        argv = kwargs["argv"]
        observations.append(argv)
        ordinal = int(argv[-1])
        assert kwargs["cwd"] == str(tmp_path)
        assert (
            kwargs["environment"] == compare.build_sanitized_reviewer_environment_v1()
        )
        assert kwargs["stdout_hard_cap_bytes"] == 8 * 1024 * 1024
        return compare._process_observation_v1(
            "EXITED",
            0,
            None,
            _capture_stdout(ordinal),
            b"",
            False,
        )

    validated_domains: list[list[list[bytes]]] = []
    monkeypatch.setattr(compare, "run_bounded_reviewer_process_v1", run)
    monkeypatch.setattr(
        common,
        "_validate_d1_capture_source_bytes_v1",
        lambda observed: observed,
    )
    monkeypatch.setattr(
        compare,
        "_prepare_d1_capture_domain_v1",
        lambda observed_fixture, observed_sources: (
            validated_domains.append(observed_sources)
            or {"captures": [], "mutations": []}
        ),
    )

    observed = compare.run_d1_fresh_capture_processes_v1(
        python_invocation_path="/frozen/python",
        export_root=str(tmp_path),
        fixture_path=str(fixture_path),
        validated_corpus_fixture=fixture,
        python_precheck_observation={"precheck": "validated"},
    )

    assert observed == _source_bytes()
    assert len(observations) == 3
    assert [argv[-1] for argv in observations] == ["0", "1", "2"]
    assert all(
        argv[:4] == ("/frozen/python", "-s", "-B", "-c") for argv in observations
    )
    assert len({id(argv) for argv in observations}) == 3
    assert validated_domains == [_source_bytes()]


def test_fresh_process_capture_rejects_noncanonical_child_before_route_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from experiments.v3m0_b7_schema_lab import compare

    fixture = {
        "environment_manifest": {"python_invocation_path": "/frozen/python"},
        "fixture": "validated",
    }
    fixture_path = tmp_path / "corpus.json"
    fixture_path.write_bytes(common.canonical_json_bytes_v1(fixture) + b"\n")
    fixture_path.chmod(0o444)
    process_calls = 0
    route_calls = 0

    def run(**kwargs):
        nonlocal process_calls
        process_calls += 1
        ordinal = int(kwargs["argv"][-1])
        stdout = _capture_stdout(ordinal) if ordinal == 0 else b'{"not":"canonical"} \n'
        return compare._process_observation_v1("EXITED", 0, None, stdout, b"", False)

    def forbidden(**_kwargs):
        nonlocal route_calls
        route_calls += 1
        raise AssertionError("route entered after invalid child output")

    monkeypatch.setattr(compare, "run_bounded_reviewer_process_v1", run)
    monkeypatch.setattr(compare, "build_d1_route_inputs_from_capture_v1", forbidden)

    with pytest.raises(ValueError, match="canonical"):
        compare.build_d1_route_inputs_from_fresh_processes_v1(
            d0_comparison={},
            ordered_d0_route_inputs=[],
            python_invocation_path="/frozen/python",
            export_root=str(tmp_path),
            fixture_path=str(fixture_path),
            validated_corpus_fixture=fixture,
            python_precheck_observation={"precheck": "validated"},
        )
    assert process_calls == 2
    assert route_calls == 0
