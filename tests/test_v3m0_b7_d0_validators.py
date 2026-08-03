"""Mechanical D0 closure for the B7 schema laboratory."""

from __future__ import annotations

import copy

import pytest


CASE_IDS = (
    "reference_failure",
    "shell_failure",
    "actual_response_values_failure",
    "matched_response_values_failure",
    "actual_bridge_failure",
    "matched_bridge_failure",
    "success",
)


def _common():
    from experiments.v3m0_b7_schema_lab import common

    return common


def _seal(raw: dict[str, object], field: str) -> dict[str, object]:
    common = _common()
    raw[field] = common.canonical_sha_v1(
        {name: value for name, value in raw.items() if name != field}
    )
    return raw


def _source_transcripts() -> list[dict[str, object]]:
    common = _common()
    transcripts = []
    for case_id, contract in zip(CASE_IDS, common._CASE_CONTRACTS_V1):
        bits = contract[4]
        actual = None
        if bits[1] == "1":
            actual = {
                "branch": "actual",
                "failure": contract[5],
                "response_values": {} if bits[2] == "1" else None,
                "bridge_audit": {} if bits[5] == "1" else None,
            }
        matched = None
        if bits[3] == "1":
            matched = {
                "branch": "matched_ablated",
                "failure": contract[6],
                "response_values": {} if bits[4] == "1" else None,
                "bridge_audit": {} if bits[6] == "1" else None,
            }
        transcripts.append(
            {
                "corpus_spec_sha": "4" * 64,
                "environment_manifest_sha": "5" * 64,
                "case_id": case_id,
                "terminal_tag": contract[2],
                "shell_outcome": {} if bits[0] == "1" else None,
                "actual_branch_attempt": actual,
                "matched_ablated_branch_attempt": matched,
                "actual_completed_response": {} if bits[7] == "1" else None,
                "matched_ablated_completed_response": ({} if bits[8] == "1" else None),
            }
        )
    return transcripts


def _validated_fixture(
    transcripts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    raw = {
        "fixture_schema_version": "experimental.v3m0.b7.corpus-fixture.v2",
        "corpus_spec": {"corpus_spec_sha": "4" * 64},
        "mutation_universe": {},
        "metric_spec": {},
        "environment_manifest": {"environment_sha": "5" * 64},
        "synthetic_graph_manifest": {},
        "ordered_d0_transcripts": (
            _source_transcripts() if transcripts is None else transcripts
        ),
        "fixture_sha": "",
    }
    return _seal(raw, "fixture_sha")


def _patch_simple_case_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    common = _common()

    def validate(raw: object) -> object:
        if type(raw) is not dict or raw.get("case_id") not in CASE_IDS:
            raise ValueError("invalid test case")
        return copy.deepcopy(raw)

    monkeypatch.setattr(common, "validate_case_contract_v1", validate)


def _call(kind: str, raw_bytes: bytes | None = None) -> dict[str, object]:
    return {"termination_kind": kind, "raw_bytes": raw_bytes}


def _legal_replays(route_id: str = "A_FLAT") -> list[dict[str, object]]:
    common = _common()
    rows = []
    for transcript in _source_transcripts():
        source = common.canonical_json_bytes_v1(transcript)
        wire = common.canonical_json_bytes_v1(
            {"route_id": route_id, "case_id": transcript["case_id"]}
        )
        rows.append(
            {
                "capture_ordinal": 0,
                "case_id": transcript["case_id"],
                "route_id": route_id,
                "source_transcript_bytes": source,
                "encode_result": _call("RETURNED_BYTES", wire),
                "decode_result": _call("RETURNED_BYTES", source),
            }
        )
    return rows


def test_e01_recomputes_legal_domain_and_rejects_self_report_flips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    fixture = _validated_fixture()
    rows = _legal_replays()

    outcome = common.build_gate_e01_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=rows,
    )

    assert outcome["passed"] is True
    assert outcome["observation"]["predicate_result_bits"] == "111"
    assert (
        common.validate_gate_e01_v1(
            outcome,
            validated_corpus_fixture=fixture,
            ordered_legal_replays=rows,
        )
        == outcome
    )

    for field, value in (
        ("passed", False),
        ("reason_codes", ["E01_LEGAL_ENCODE_FAILURE"]),
    ):
        hostile = copy.deepcopy(outcome)
        hostile[field] = value
        _seal(hostile, "gate_outcome_sha")
        with pytest.raises((TypeError, ValueError)):
            common.validate_gate_e01_v1(
                hostile,
                validated_corpus_fixture=fixture,
                ordered_legal_replays=rows,
            )


def test_e01_records_each_fresh_predicate_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    fixture = _validated_fixture()

    encode_failure = _legal_replays()
    encode_failure[1]["encode_result"] = _call("WRONG_EXCEPTION")
    encode_failure[1]["decode_result"] = _call("NOT_CALLED")
    encoded = common.build_gate_e01_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=encode_failure,
    )
    assert encoded["observation"]["predicate_result_bits"] == "100"

    decode_failure = _legal_replays()
    decode_failure[2]["decode_result"] = _call("RETURNED_BYTES", b'{"different":true}')
    decoded = common.build_gate_e01_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=decode_failure,
    )
    assert decoded["observation"]["predicate_result_bits"] == "110"


@pytest.mark.parametrize(
    "mutator",
    (
        lambda rows: rows.reverse(),
        lambda rows: rows[0].update(route_id="B_PROGRESS"),
        lambda rows: rows[0].update(source_transcript_bytes=b'{"substitute":true}'),
        lambda rows: rows[0].update(unknown=None),
        lambda rows: rows[0].update(
            encode_result={
                "raw_bytes": rows[0]["encode_result"]["raw_bytes"],
                "termination_kind": "RETURNED_BYTES",
            }
        ),
    ),
)
def test_e01_rejects_order_route_body_and_exact_shape_attacks(
    monkeypatch: pytest.MonkeyPatch,
    mutator,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    fixture = _validated_fixture()
    rows = _legal_replays()
    mutator(rows)

    with pytest.raises((TypeError, ValueError)):
        common.build_gate_e01_v1(
            phase="D0",
            route_id="A_FLAT",
            validated_corpus_fixture=fixture,
            ordered_legal_replays=rows,
        )


def test_e01_domain_root_covers_source_wire_and_decoded_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    fixture = _validated_fixture()
    baseline = common.build_gate_e01_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=_legal_replays(),
    )
    changed_rows = _legal_replays()
    changed_rows[4]["encode_result"] = _call(
        "RETURNED_BYTES", b'{"canonical":"but-different"}'
    )
    changed = common.build_gate_e01_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=changed_rows,
    )

    assert (
        baseline["observation"]["domain_root_sha"]
        != changed["observation"]["domain_root_sha"]
    )


def _fake_invalid_presence_candidates() -> list[dict[str, object]]:
    common = _common()
    legal = {(row[2], row[4]) for row in common._CASE_CONTRACTS_V1}
    candidates = []
    for bit_integer in range(512):
        bits = f"{bit_integer:09b}"
        if not (
            bits[2] <= bits[1]
            and bits[5] <= bits[1]
            and bits[4] <= bits[3]
            and bits[6] <= bits[3]
        ):
            continue
        for terminal_tag in common._TERMINAL_TAG_ORDER_V1:
            if (terminal_tag, bits) in legal:
                continue
            candidates.append(
                {
                    "terminal_tag": terminal_tag,
                    "bit_integer": bit_integer,
                    "presence_bits": bits,
                    "half_pair": (bits[5] != bits[6] or bits[7] != bits[8]),
                    "transcript": {
                        "candidate": len(candidates),
                        "terminal_tag": terminal_tag,
                        "presence_bits": bits,
                    },
                }
            )
    assert len(candidates) == 1393
    return candidates


def _patch_invalid_presence_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    candidates = _fake_invalid_presence_candidates()
    monkeypatch.setattr(
        _common(),
        "generate_constructible_invalid_presence_candidates_v1",
        lambda _success: copy.deepcopy(candidates),
    )


def _invalid_presence_probes(
    route_id: str = "A_FLAT",
) -> list[dict[str, object]]:
    common = _common()
    rows = []
    for candidate in _fake_invalid_presence_candidates():
        rows.append(
            {
                "capture_ordinal": 0,
                "terminal_tag": candidate["terminal_tag"],
                "bit_integer": candidate["bit_integer"],
                "presence_bits": candidate["presence_bits"],
                "route_id": route_id,
                "candidate_transcript_bytes": common.canonical_json_bytes_v1(
                    candidate["transcript"]
                ),
                "encode_result": _call("B7LabMutationRejected"),
            }
        )
    return rows


def test_e04_recomputes_case_map_and_all_1393_invalid_presence_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    _patch_invalid_presence_generator(monkeypatch)
    fixture = _validated_fixture()
    legal = _legal_replays()
    invalid = _invalid_presence_probes()

    outcome = common.build_gate_e04_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=legal,
        ordered_invalid_presence_probes=invalid,
    )

    assert outcome["passed"] is True
    assert outcome["observation"]["predicate_result_bits"] == "111"
    assert (
        common.validate_gate_e04_v1(
            outcome,
            validated_corpus_fixture=fixture,
            ordered_legal_replays=legal,
            ordered_invalid_presence_probes=invalid,
        )
        == outcome
    )


def test_e04_records_unlisted_accepted_presence_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    _patch_invalid_presence_generator(monkeypatch)
    invalid = _invalid_presence_probes()
    invalid[37]["encode_result"] = _call("RETURNED_BYTES", b'{"accepted":true}')

    outcome = common.build_gate_e04_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=_validated_fixture(),
        ordered_legal_replays=_legal_replays(),
        ordered_invalid_presence_probes=invalid,
    )

    assert outcome["observation"]["predicate_result_bits"] == "110"
    assert outcome["reason_codes"] == ["E04_UNLISTED_LEGAL_STATE"]


@pytest.mark.parametrize(
    "mutator",
    (
        lambda rows: rows.reverse(),
        lambda rows: rows[0].update(bit_integer=511),
        lambda rows: rows[0].update(route_id="C_UNION"),
        lambda rows: rows[0].update(candidate_transcript_bytes=b"{}"),
        lambda rows: rows[0].update(unknown=None),
    ),
)
def test_e04_rejects_invalid_presence_order_root_and_shape_attacks(
    monkeypatch: pytest.MonkeyPatch,
    mutator,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    _patch_invalid_presence_generator(monkeypatch)
    invalid = _invalid_presence_probes()
    mutator(invalid)

    with pytest.raises((TypeError, ValueError)):
        common.build_gate_e04_v1(
            phase="D0",
            route_id="A_FLAT",
            validated_corpus_fixture=_validated_fixture(),
            ordered_legal_replays=_legal_replays(),
            ordered_invalid_presence_probes=invalid,
        )


def test_e03_recomputes_evidence_pointer_domain_and_loss_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    fixture = _validated_fixture()
    sources = [fixture["ordered_d0_transcripts"]]
    rows = _legal_replays()

    outcome = common.build_gate_e03_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=rows,
    )
    assert outcome["observation"]["predicate_result_bits"] == "11"
    assert (
        common.validate_gate_e03_v1(
            outcome,
            validated_corpus_fixture=fixture,
            ordered_legal_replays=rows,
        )
        == outcome
    )

    decoded = copy.deepcopy(sources[0][3])
    decoded["terminal_tag"] = "success"
    rows[3]["decode_result"] = _call(
        "RETURNED_BYTES", common.canonical_json_bytes_v1(decoded)
    )
    failed = common.build_gate_e03_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=rows,
    )
    assert failed["observation"]["predicate_result_bits"] == "10"
    assert failed["reason_codes"] == ["E03_EVIDENCE_LOSS"]


def test_e03_domain_root_changes_on_decoded_evidence_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    fixture = _validated_fixture()
    sources = [fixture["ordered_d0_transcripts"]]
    baseline = common.build_gate_e03_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=_legal_replays(),
    )
    rows = _legal_replays()
    decoded = copy.deepcopy(sources[0][0])
    decoded["terminal_tag"] = "success"
    rows[0]["decode_result"] = _call(
        "RETURNED_BYTES", common.canonical_json_bytes_v1(decoded)
    )
    changed = common.build_gate_e03_v1(
        phase="D0",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_legal_replays=rows,
    )

    assert (
        baseline["observation"]["domain_root_sha"]
        != changed["observation"]["domain_root_sha"]
    )
