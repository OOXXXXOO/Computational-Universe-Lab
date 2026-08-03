"""Mechanical E02/E06 gates over the exact mutation-probe domain."""

from __future__ import annotations

import copy
import inspect

import pytest


def _common():
    from experiments.v3m0_b7_schema_lab import common

    return common


def _call(kind: str, raw_bytes: bytes | None = None) -> dict[str, object]:
    return {"termination_kind": kind, "raw_bytes": raw_bytes}


def _mutation(
    ordinal: int,
    *,
    probe_kind: str,
    mutation_class: str,
    operation: str,
    base_case_id: str | None = "success",
) -> dict[str, object]:
    return {
        "mutation_ordinal": ordinal,
        "mutation_id": f"M{ordinal:06d}-{mutation_class}",
        "mutation_sha": f"{ordinal + 1:x}" * 64,
        "base_case_id": base_case_id,
        "probe_kind": probe_kind,
        "mutation_class": mutation_class,
        "operation": operation,
    }


def _fixture() -> dict[str, object]:
    mutations = [
        _mutation(
            0,
            probe_kind="MUTATION_MUST_REJECT",
            mutation_class="TERMINAL_TAG",
            operation="SET_VALUE",
        ),
        _mutation(
            1,
            probe_kind="MUTATION_MUST_REJECT",
            mutation_class="NESTED_BODY_SHA_SPLICE",
            operation="SET_VALUE",
        ),
        _mutation(
            2,
            probe_kind="ROUNDTRIP_MUST_EQUAL",
            mutation_class="CANONICAL_ROUNDTRIP",
            operation="REENCODE",
        ),
        _mutation(
            3,
            probe_kind="REPEAT_MUST_EQUAL",
            mutation_class="CANONICAL_REPEAT",
            operation="REPEAT",
        ),
        _mutation(
            4,
            probe_kind="UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT",
            mutation_class="UPSTREAM_INVALID",
            operation="RAISE_UPSTREAM",
            base_case_id=None,
        ),
    ]
    transcripts = [
        {"case_id": name, "body": name}
        for name in (
            "reference_failure",
            "shell_failure",
            "actual_response_values_failure",
            "matched_response_values_failure",
            "actual_bridge_failure",
            "matched_bridge_failure",
            "success",
        )
    ]
    return {
        "mutation_universe": {
            "ordered_mutations": mutations,
            "mutation_count": len(mutations),
            "mutation_universe_sha": "a" * 64,
        },
        "ordered_d0_transcripts": transcripts,
    }


def _install_domain_spies(monkeypatch: pytest.MonkeyPatch) -> None:
    common = _common()

    monkeypatch.setattr(
        common,
        "_validated_d0_fixture_source_domain_v1",
        lambda fixture: (fixture, [fixture["ordered_d0_transcripts"]]),
    )
    monkeypatch.setattr(common, "validate_mutation_v1", copy.deepcopy)
    monkeypatch.setattr(
        common,
        "generate_ordered_mutations_v1",
        lambda transcripts: (
            copy.deepcopy(fixture_mutations)
            if (
                fixture_mutations := _fixture()["mutation_universe"][
                    "ordered_mutations"
                ]
            )
            else []
        ),
    )

    def materialize(base, mutation, _success, _snapshot):
        return {"base": base["case_id"], "mutation": mutation["mutation_id"]}

    monkeypatch.setattr(common, "apply_transcript_mutation_v1", materialize)
    monkeypatch.setattr(
        common,
        "discover_record_self_hashes_v1",
        lambda transcript: (("", transcript["case_id"]),),
    )


def _candidate_bytes(mutation: dict[str, object]) -> bytes:
    common = _common()
    return common.canonical_json_bytes_v1(
        {"base": mutation["base_case_id"], "mutation": mutation["mutation_id"]}
    )


def _probes(
    fixture: dict[str, object], route_id: str = "A_FLAT"
) -> list[dict[str, object]]:
    common = _common()
    source = common.canonical_json_bytes_v1({"case_id": "success", "body": "success"})
    wire = b'{"wire":true}'
    rows = []
    for mutation in fixture["mutation_universe"]["ordered_mutations"]:
        kind = mutation["probe_kind"]
        if kind == "MUTATION_MUST_REJECT":
            candidate = _candidate_bytes(mutation)
            first_encode = _call("B7LabMutationRejected")
            first_decode = _call("NOT_CALLED")
            second_encode = _call("NOT_CALLED")
            second_decode = _call("NOT_CALLED")
            upstream_count = 1
        elif kind == "ROUNDTRIP_MUST_EQUAL":
            candidate = source
            first_encode = _call("RETURNED_BYTES", wire)
            first_decode = _call("RETURNED_BYTES", source)
            second_encode = _call("NOT_CALLED")
            second_decode = _call("NOT_CALLED")
            upstream_count = 1
        elif kind == "REPEAT_MUST_EQUAL":
            candidate = source
            first_encode = _call("RETURNED_BYTES", wire)
            first_decode = _call("RETURNED_BYTES", source)
            second_encode = _call("RETURNED_BYTES", wire)
            second_decode = _call("RETURNED_BYTES", source)
            upstream_count = 1
        else:
            candidate = None
            first_encode = _call("NOT_CALLED")
            first_decode = _call("NOT_CALLED")
            second_encode = _call("NOT_CALLED")
            second_decode = _call("NOT_CALLED")
            upstream_count = 0
        rows.append(
            {
                "capture_ordinal": 0,
                "mutation_ordinal": mutation["mutation_ordinal"],
                "mutation_id": mutation["mutation_id"],
                "mutation_sha": mutation["mutation_sha"],
                "route_id": route_id,
                "materialized_transcript_bytes": candidate,
                "upstream_transcript_count": upstream_count,
                "first_encode_result": first_encode,
                "first_decode_result": first_decode,
                "second_encode_result": second_encode,
                "second_decode_result": second_decode,
            }
        )
    return rows


def test_mutation_gate_signatures_are_exact() -> None:
    common = _common()
    for symbol in ("build_gate_e02_v1", "build_gate_e06_v1"):
        assert tuple(inspect.signature(getattr(common, symbol)).parameters) == (
            "phase",
            "route_id",
            "validated_corpus_fixture",
            "ordered_mutation_probes",
        )
    for symbol in ("validate_gate_e02_v1", "validate_gate_e06_v1"):
        assert tuple(inspect.signature(getattr(common, symbol)).parameters) == (
            "raw_body",
            "validated_corpus_fixture",
            "ordered_mutation_probes",
        )


def test_e02_uses_dynamic_fixture_count_and_recomputes_all_probe_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _install_domain_spies(monkeypatch)
    fixture = _fixture()
    probes = _probes(fixture)

    domain = common._validate_mutation_probe_domain_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=probes,
    )
    outcome = common.build_gate_e02_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=probes,
    )

    assert domain["mutation_probe_count"] == 5
    assert domain["mutation_accept_count"] == 0
    assert domain["upstream_invalid_probe_count"] == 1
    assert domain["upstream_invalid_transcript_count"] == 0
    assert domain["all_upstream_route_entry_counts_zero"] is True
    assert len(domain["normalized"]) == 5
    assert outcome["passed"] is True
    assert outcome["observation"]["domain_root_sha"] == domain["domain_root_sha"]
    assert (
        common.validate_gate_e02_v1(
            outcome,
            validated_corpus_fixture=fixture,
            ordered_mutation_probes=probes,
        )
        == outcome
    )


def test_e02_records_acceptance_wrong_exception_and_nonbytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _install_domain_spies(monkeypatch)
    fixture = _fixture()
    probes = _probes(fixture)
    probes[0]["first_encode_result"] = _call("RETURNED_BYTES", b"wire")
    probes[0]["first_decode_result"] = _call(
        "RETURNED_BYTES", probes[0]["materialized_transcript_bytes"]
    )
    probes[1]["first_encode_result"] = _call("RETURNED_NONBYTES")
    probes[2]["first_decode_result"] = _call("WRONG_EXCEPTION")

    outcome = common.build_gate_e02_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=probes,
    )

    assert outcome["observation"]["predicate_result_bits"] == "100"
    assert outcome["reason_codes"] == [
        "E02_MUTATION_ACCEPTED",
        "E02_INVALID_REJECTION_SURFACE",
    ]


@pytest.mark.parametrize(
    "mutator",
    (
        lambda rows: rows.reverse(),
        lambda rows: rows[0].update(mutation_id="substituted"),
        lambda rows: rows[0].update(mutation_sha="f" * 64),
        lambda rows: rows[0].update(capture_ordinal=1),
        lambda rows: rows[0].update(route_id="C_UNION"),
        lambda rows: rows[0].update(materialized_transcript_bytes=b"{}"),
        lambda rows: rows[0].update(unknown=None),
        lambda rows: rows[0].update(
            first_encode_result={
                "raw_bytes": None,
                "termination_kind": "B7LabMutationRejected",
            }
        ),
    ),
)
def test_e02_rejects_probe_order_identity_body_route_and_shape_attacks(
    monkeypatch: pytest.MonkeyPatch,
    mutator,
) -> None:
    common = _common()
    _install_domain_spies(monkeypatch)
    fixture = _fixture()
    probes = _probes(fixture)
    mutator(probes)

    with pytest.raises((TypeError, ValueError)):
        common.build_gate_e02_v1(
            phase="D0",
            route_id="A_FLAT",
            validated_corpus_fixture=fixture,
            ordered_mutation_probes=probes,
        )


def test_e06_recomputes_roundtrip_repeat_and_m02_m07_subsets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _install_domain_spies(monkeypatch)
    fixture = _fixture()
    probes = _probes(fixture)

    outcome = common.build_gate_e06_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=probes,
    )
    assert outcome["passed"] is True
    assert outcome["observation"]["predicate_result_bits"] == "111"
    assert (
        common.validate_gate_e06_v1(
            outcome,
            validated_corpus_fixture=fixture,
            ordered_mutation_probes=probes,
        )
        == outcome
    )

    broken = _probes(fixture)
    broken[2]["first_decode_result"] = _call("RETURNED_BYTES", b"different")
    broken[3]["second_encode_result"] = _call("RETURNED_BYTES", b"different")
    broken[1]["first_encode_result"] = _call("RETURNED_BYTES", b"wire")
    broken[1]["first_decode_result"] = _call(
        "RETURNED_BYTES", broken[1]["materialized_transcript_bytes"]
    )
    failed = common.build_gate_e06_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=broken,
    )
    assert failed["observation"]["predicate_result_bits"] == "000"


@pytest.mark.parametrize("gate_id", ("e02", "e06"))
def test_mutation_gate_validator_rejects_self_report_flip(
    monkeypatch: pytest.MonkeyPatch,
    gate_id: str,
) -> None:
    common = _common()
    _install_domain_spies(monkeypatch)
    fixture = _fixture()
    probes = _probes(fixture)
    build = getattr(common, f"build_gate_{gate_id}_v1")
    validate = getattr(common, f"validate_gate_{gate_id}_v1")
    outcome = build(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=probes,
    )
    hostile = copy.deepcopy(outcome)
    hostile["passed"] = False
    hostile["gate_outcome_sha"] = common.canonical_sha_v1(
        {name: value for name, value in hostile.items() if name != "gate_outcome_sha"}
    )
    with pytest.raises((TypeError, ValueError)):
        validate(
            hostile,
            validated_corpus_fixture=fixture,
            ordered_mutation_probes=probes,
        )


def test_mutation_domain_repeats_exact_dynamic_universe_for_d1_captures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _install_domain_spies(monkeypatch)
    fixture = _fixture()
    one_capture = _probes(fixture)
    probes = []
    for capture_ordinal in (0, 1, 2):
        capture = copy.deepcopy(one_capture)
        for row in capture:
            row["capture_ordinal"] = capture_ordinal
        probes.extend(capture)

    domain = common._validate_mutation_probe_domain_v1(
        phase="D1",
        route_id="B_PROGRESS",
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=[{**row, "route_id": "B_PROGRESS"} for row in probes],
    )
    assert domain["mutation_probe_count"] == 15
    assert domain["upstream_invalid_probe_count"] == 3


def test_mutation_domain_totalizes_nonzero_upstream_and_route_entry_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _install_domain_spies(monkeypatch)
    fixture = _fixture()
    probes = _probes(fixture)
    probes[-1]["upstream_transcript_count"] = 1
    probes[-1]["first_encode_result"] = _call("B7LabMutationRejected")

    domain = common._validate_mutation_probe_domain_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=probes,
    )

    assert domain["upstream_invalid_transcript_count"] == 1
    assert domain["all_upstream_route_entry_counts_zero"] is False
