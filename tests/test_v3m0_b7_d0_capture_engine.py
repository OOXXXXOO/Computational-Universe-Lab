"""Executable D0 byte-observation capture for all three frozen B7 routes."""

from __future__ import annotations

import ast
import copy
from pathlib import Path
import sys
from types import ModuleType

import pytest

from experiments.v3m0_b7_schema_lab import common


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ROUTE_IDS = ("A_FLAT", "B_PROGRESS", "C_UNION")
CASE_IDS = tuple(row[1] for row in common._CASE_CONTRACTS_V1)


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
        "base_case_id": None if ordinal == 4 else CASE_IDS[ordinal % 7],
        "probe_kind": probe_kind,
        "mutation_class": mutation_class,
        "target_json_pointer": None if ordinal == 4 else "/terminal_tag",
        "operation": "UPSTREAM_ZERO" if ordinal == 4 else "SET_VALUE",
        "replacement_json": None,
        "expected_boundary": "UPSTREAM_HARNESS" if ordinal == 4 else "ROUTE_VERIFICATION",
        "mutation_sha": f"{ordinal + 1:x}" * 64,
    }


def _install_small_domain(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    source_set = [
        {"case_id": case_id, "payload": f"source-{ordinal}"}
        for ordinal, case_id in enumerate(CASE_IDS)
    ]
    mutations = [
        _mutation(0, probe_kind="MUTATION_MUST_REJECT"),
        _mutation(1, probe_kind="ROUNDTRIP_MUST_EQUAL"),
        _mutation(2, probe_kind="REPEAT_MUST_EQUAL"),
        _mutation(
            3,
            probe_kind="MUTATION_MUST_REJECT",
            mutation_class="NESTED_BODY_SHA_SPLICE",
        ),
        _mutation(
            4,
            probe_kind="UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT",
            mutation_class="UPSTREAM_INVALID",
        ),
    ]
    fixture = {
        "ordered_d0_transcripts": copy.deepcopy(source_set),
        "mutation_universe": {
            "ordered_mutations": copy.deepcopy(mutations),
            "mutation_count": len(mutations),
            "mutation_universe_sha": "a" * 64,
        },
    }
    candidates = [
        {
            "terminal_tag": "success",
            "bit_integer": ordinal,
            "presence_bits": f"{ordinal % 512:09b}",
            "half_pair": False,
            "transcript": {
                "case_id": "invalid-presence",
                "candidate_ordinal": ordinal,
            },
        }
        for ordinal in range(1393)
    ]

    monkeypatch.setattr(
        common,
        "_validated_d0_fixture_source_domain_v1",
        lambda observed: (observed, [copy.deepcopy(source_set)]),
    )
    monkeypatch.setattr(
        common,
        "generate_ordered_mutations_v1",
        lambda _sources: copy.deepcopy(mutations),
    )
    monkeypatch.setattr(common, "validate_mutation_v1", copy.deepcopy)
    monkeypatch.setattr(
        common,
        "discover_record_self_hashes_v1",
        lambda source: {"case_id": source["case_id"]},
    )
    monkeypatch.setattr(
        common,
        "apply_transcript_mutation_v1",
        lambda base, mutation, _success, _snapshot: {
            "case_id": base["case_id"],
            "mutation_id": mutation["mutation_id"],
        },
    )
    monkeypatch.setattr(
        common,
        "generate_constructible_invalid_presence_candidates_v1",
        lambda _success: copy.deepcopy(candidates),
    )
    return fixture


def _install_route_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    encode=None,
    decode=None,
) -> dict[str, ModuleType]:
    modules = {}
    package = sys.modules["experiments.v3m0_b7_schema_lab"]
    for leaf_name, route_id in (
        ("a_flat", "A_FLAT"),
        ("b_progress", "B_PROGRESS"),
        ("c_union", "C_UNION"),
    ):
        module_name = f"experiments.v3m0_b7_schema_lab.{leaf_name}"
        module = ModuleType(module_name)
        module.ROUTE_ID = route_id
        module.encode_normalized_transcript = encode or (
            lambda raw_bytes, prefix=route_id.encode(): prefix + b":" + raw_bytes
        )
        module.verify_and_decode_route_wire = decode or (
            lambda wire_bytes: wire_bytes.split(b":", 1)[1]
        )
        monkeypatch.setitem(sys.modules, module_name, module)
        monkeypatch.setattr(package, leaf_name, module, raising=False)
        modules[route_id] = module
    return modules


def test_d0_capture_iterates_fixed_routes_and_exact_gate_input_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import iter_d0_gate_inputs_v1

    fixture = _install_small_domain(monkeypatch)
    _install_route_stubs(monkeypatch)

    captured = list(iter_d0_gate_inputs_v1(validated_corpus_fixture=fixture))

    assert tuple(route_id for route_id, _inputs in captured) == ROUTE_IDS
    for route_id, inputs in captured:
        assert tuple(inputs) == (
            "ordered_legal_replays",
            "ordered_mutation_probes",
            "ordered_invalid_presence_probes",
        )
        assert len(inputs["ordered_legal_replays"]) == 7
        assert len(inputs["ordered_mutation_probes"]) == 5
        assert len(inputs["ordered_invalid_presence_probes"]) == 1393
        assert {row["route_id"] for row in inputs["ordered_legal_replays"]} == {
            route_id
        }
        assert {row["route_id"] for row in inputs["ordered_mutation_probes"]} == {
            route_id
        }
        assert {
            row["route_id"] for row in inputs["ordered_invalid_presence_probes"]
        } == {route_id}


@pytest.mark.parametrize(
    ("behavior", "termination_kind", "raw_bytes"),
    (
        ("bytes", "RETURNED_BYTES", b"wire"),
        ("rejected", "B7LabMutationRejected", None),
        ("wrong-exception", "WRONG_EXCEPTION", None),
        ("nonbytes", "RETURNED_NONBYTES", None),
    ),
)
def test_route_call_totalizer_has_exact_closed_outcomes(
    monkeypatch: pytest.MonkeyPatch,
    behavior: str,
    termination_kind: str,
    raw_bytes: bytes | None,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import _call_a_flat_encode_v1

    def attacked(_source: bytes) -> object:
        if behavior == "rejected":
            raise common.B7LabMutationRejected("frozen rejection")
        if behavior == "wrong-exception":
            raise RuntimeError("wrong exception")
        if behavior == "nonbytes":
            return bytearray(b"wire")
        return b"wire"

    modules = _install_route_stubs(monkeypatch)
    modules["A_FLAT"].encode_normalized_transcript = attacked

    assert _call_a_flat_encode_v1(b"source") == {
        "termination_kind": termination_kind,
        "raw_bytes": raw_bytes,
    }


def test_rejected_encoder_prevents_decoder_and_upstream_probe_never_enters_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import iter_d0_gate_inputs_v1

    fixture = _install_small_domain(monkeypatch)
    decode_calls = 0

    def reject(_source: bytes) -> bytes:
        raise common.B7LabMutationRejected("reject")

    def forbidden_decode(_wire: bytes) -> bytes:
        nonlocal decode_calls
        decode_calls += 1
        return b"unexpected"

    _install_route_stubs(monkeypatch, encode=reject, decode=forbidden_decode)

    _route_id, inputs = next(
        iter_d0_gate_inputs_v1(validated_corpus_fixture=fixture)
    )

    assert decode_calls == 0
    for row in inputs["ordered_legal_replays"]:
        assert row["decode_result"] == {
            "termination_kind": "NOT_CALLED",
            "raw_bytes": None,
        }
    upstream = inputs["ordered_mutation_probes"][-1]
    assert upstream["upstream_transcript_count"] == 0
    assert upstream["materialized_transcript_bytes"] is None
    assert {
        upstream[field]["termination_kind"]
        for field in (
            "first_encode_result",
            "first_decode_result",
            "second_encode_result",
            "second_decode_result",
        )
    } == {"NOT_CALLED"}


def test_capture_rejects_mutation_universe_order_substitution_before_route_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.v3m0_b7_schema_lab.compare import iter_d0_gate_inputs_v1

    fixture = _install_small_domain(monkeypatch)
    fixture["mutation_universe"]["ordered_mutations"].reverse()
    route_calls = 0

    def count_call(_source: bytes) -> bytes:
        nonlocal route_calls
        route_calls += 1
        return b"wire"

    modules = _install_route_stubs(monkeypatch)
    modules["A_FLAT"].encode_normalized_transcript = count_call

    with pytest.raises(ValueError, match="mutation universe"):
        next(iter_d0_gate_inputs_v1(validated_corpus_fixture=fixture))
    assert route_calls == 0


def test_capture_route_imports_are_static_function_local_and_callback_free() -> None:
    source_path = (
        REPOSITORY_ROOT / "experiments/v3m0_b7_schema_lab/compare.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    expected = {
        "_call_a_flat_encode_v1": (".a_flat", "encode_normalized_transcript"),
        "_call_a_flat_decode_v1": (".a_flat", "verify_and_decode_route_wire"),
        "_call_b_progress_encode_v1": (
            ".b_progress",
            "encode_normalized_transcript",
        ),
        "_call_b_progress_decode_v1": (
            ".b_progress",
            "verify_and_decode_route_wire",
        ),
        "_call_c_union_encode_v1": (".c_union", "encode_normalized_transcript"),
        "_call_c_union_decode_v1": (
            ".c_union",
            "verify_and_decode_route_wire",
        ),
    }
    for symbol, (module, imported) in expected.items():
        function = functions[symbol]
        assert [argument.arg for argument in function.args.args] == ["raw_bytes"]
        imports = [node for node in ast.walk(function) if isinstance(node, ast.ImportFrom)]
        assert len(imports) == 1
        assert "." * imports[0].level + (imports[0].module or "") == module
        assert [(alias.name, alias.asname) for alias in imports[0].names] == [
            (imported, "route_call")
        ]
    assert all(
        not isinstance(node, (ast.Import, ast.ImportFrom))
        or all(alias.name != "importlib" for alias in node.names)
        for node in ast.walk(tree)
    )
