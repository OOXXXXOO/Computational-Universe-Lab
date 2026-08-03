"""Mechanical D1 closure for the B7 schema laboratory."""

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
ROUTE_IDS = ("A_FLAT", "B_PROGRESS", "C_UNION")


def _common():
    from experiments.v3m0_b7_schema_lab import common

    return common


def _seal(raw: dict[str, object], field: str) -> dict[str, object]:
    common = _common()
    raw[field] = common.canonical_sha_v1(
        {name: value for name, value in raw.items() if name != field}
    )
    return raw


def _patch_simple_case_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    common = _common()

    def validate(raw: object) -> object:
        if type(raw) is not dict or raw.get("case_id") not in CASE_IDS:
            raise ValueError("invalid test transcript")
        if type(raw.get("ordered_leaf_digests")) is not list:
            raise ValueError("missing leaf digest list")
        return copy.deepcopy(raw)

    monkeypatch.setattr(common, "validate_case_contract_v1", validate)


def _capture_transcripts(capture_ordinal: int) -> list[dict[str, object]]:
    return [
        {
            "case_id": case_id,
            "capture_ordinal": capture_ordinal,
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


def _route_replays(route_id: str) -> list[dict[str, object]]:
    common = _common()
    rows = []
    for capture_ordinal in range(3):
        for case_ordinal, transcript in enumerate(
            _capture_transcripts(capture_ordinal)
        ):
            source = common.canonical_json_bytes_v1(transcript)
            wire = common.canonical_json_bytes_v1(
                {
                    "route_id": route_id,
                    "capture_ordinal": capture_ordinal,
                    "case_ordinal": case_ordinal,
                }
            )
            rows.append(
                {
                    "capture_ordinal": capture_ordinal,
                    "case_id": transcript["case_id"],
                    "route_id": route_id,
                    "source_transcript_bytes": source,
                    "encode_result": {
                        "termination_kind": "RETURNED_BYTES",
                        "raw_bytes": wire,
                    },
                    "decode_result": {
                        "termination_kind": "RETURNED_BYTES",
                        "raw_bytes": source,
                    },
                }
            )
    return rows


def _route_capture_inputs(
    route_ids: tuple[str, ...] = ROUTE_IDS,
) -> list[dict[str, object]]:
    return [
        {
            "route_id": route_id,
            "route_manifest_sha": f"{ordinal + 1:x}" * 64,
            "ordered_legal_replays": _route_replays(route_id),
        }
        for ordinal, route_id in enumerate(route_ids)
    ]


def _ordered_capture_source_bytes() -> list[list[bytes]]:
    common = _common()
    return [
        [common.canonical_json_bytes_v1(raw) for raw in _capture_transcripts(capture)]
        for capture in range(3)
    ]


def test_e05_recomputes_three_capture_cross_route_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    inputs = _route_capture_inputs()

    outcome = common.build_gate_e05_v1(
        phase="D1",
        route_id="A_FLAT",
        synthetic_graph_manifest_sha="a" * 64,
        ordered_survivor_route_ids=list(ROUTE_IDS),
        ordered_capture_source_bytes=_ordered_capture_source_bytes(),
        ordered_route_capture_inputs=inputs,
    )

    assert outcome["passed"] is True
    assert outcome["observation"]["predicate_result_bits"] == "111111"
    assert (
        common.validate_gate_e05_v1(
            outcome,
            synthetic_graph_manifest_sha="a" * 64,
            ordered_survivor_route_ids=list(ROUTE_IDS),
            ordered_capture_source_bytes=_ordered_capture_source_bytes(),
            ordered_route_capture_inputs=inputs,
        )
        == outcome
    )


def test_e05_records_exact_decoded_byte_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    inputs = _route_capture_inputs()
    inputs[1]["ordered_legal_replays"][9]["decode_result"]["raw_bytes"] += b" "

    outcome = common.build_gate_e05_v1(
        phase="D1",
        route_id="B_PROGRESS",
        synthetic_graph_manifest_sha="a" * 64,
        ordered_survivor_route_ids=list(ROUTE_IDS),
        ordered_capture_source_bytes=_ordered_capture_source_bytes(),
        ordered_route_capture_inputs=inputs,
    )

    assert outcome["passed"] is False
    assert outcome["observation"]["predicate_result_bits"] == "110011"
    assert outcome["reason_codes"] == [
        "E05_TRANSCRIPT_BYTE_MISMATCH",
        "E05_TRANSCRIPT_ROOT_MISMATCH",
    ]


@pytest.mark.parametrize(
    "mutator",
    (
        lambda rows: rows.reverse(),
        lambda rows: rows[0].update(route_id="B_PROGRESS"),
        lambda rows: rows[0]["ordered_legal_replays"].reverse(),
        lambda rows: rows[0].update(unknown=None),
    ),
)
def test_e05_rejects_survivor_route_capture_order_and_shape_attacks(
    monkeypatch: pytest.MonkeyPatch,
    mutator,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    inputs = _route_capture_inputs()
    mutator(inputs)

    with pytest.raises((TypeError, ValueError)):
        common.build_gate_e05_v1(
            phase="D1",
            route_id="A_FLAT",
            synthetic_graph_manifest_sha="a" * 64,
            ordered_survivor_route_ids=list(ROUTE_IDS),
            ordered_capture_source_bytes=_ordered_capture_source_bytes(),
            ordered_route_capture_inputs=inputs,
        )
