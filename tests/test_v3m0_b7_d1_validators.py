"""Mechanical D1 closure for the B7 schema laboratory."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path

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
            "corpus_spec_sha": "4" * 64,
            "environment_manifest_sha": "5" * 64,
            "provenance_fixture": {"capture": capture_ordinal},
            "response_run_spec_fixture": {"selected_fejer_order": 256},
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


def _route_manifest(
    route_id: str = "A_FLAT",
    *,
    common_commit_sha: str = "b" * 40,
    common_source_sha256: str = "2" * 64,
    compare_source_sha256: str = "3" * 64,
) -> dict[str, object]:
    routes = {
        "A_FLAT": (
            "experimental.v3m0.b7.a-flat",
            "experiments.v3m0_b7_schema_lab.a_flat",
            "experiments/v3m0_b7_schema_lab/a_flat.py",
            "experimental.v3m0.b7.a-flat.wire.v1",
        ),
        "B_PROGRESS": (
            "experimental.v3m0.b7.b-progress",
            "experiments.v3m0_b7_schema_lab.b_progress",
            "experiments/v3m0_b7_schema_lab/b_progress.py",
            "experimental.v3m0.b7.b-progress.wire.v1",
        ),
        "C_UNION": (
            "experimental.v3m0.b7.c-union",
            "experiments.v3m0_b7_schema_lab.c_union",
            "experiments/v3m0_b7_schema_lab/c_union.py",
            "experimental.v3m0.b7.c-union.wire.v1",
        ),
    }
    domain, module, path, wire = routes[route_id]
    return _seal(
        {
            "route_manifest_schema_version": "experimental.v3m0.b7.route-manifest.v1",
            "route_id": route_id,
            "route_schema_domain": domain,
            "route_module": module,
            "route_source_path": path,
            "wire_schema_id": wire,
            "route_commit_sha": "a" * 40,
            "route_source_sha256": "1" * 64,
            "common_commit_sha": common_commit_sha,
            "common_source_sha256": common_source_sha256,
            "compare_source_sha256": compare_source_sha256,
            "corpus_spec_sha": "4" * 64,
            "mutation_universe_sha": "6" * 64,
            "metric_spec_sha": "7" * 64,
            "encoder_symbol": "encode_normalized_transcript",
            "verifier_decoder_symbol": "verify_and_decode_route_wire",
            "input_schema_version": "experimental.v3m0.b7.normalized-transcript.v1",
            "output_schema_version": wire,
            "static_api_scan_sha": "8" * 64,
            "static_import_scan_sha": "9" * 64,
            "static_authority_surface_scan_sha": "a" * 64,
            "production_import_scan_sha": "b" * 64,
            "production_imported_by_route": False,
            "route_imported_by_production": False,
            "authority_surface_count": 0,
            "wrapper_surface_count": 0,
            "route_manifest_sha": "",
        },
        "route_manifest_sha",
    )


def _d0_route_result(route_id: str = "A_FLAT") -> dict[str, object]:
    common = _common()
    manifest = _route_manifest(route_id)
    gates = [
        common.build_gate_outcome_v1(
            gate_id=gate_id,
            phase="D0",
            route_id=route_id,
            domain_root_sha=f"{ordinal + 1:x}" * 64,
            predicate_results=[True for _ in common._gate_contract_v1(gate_id)[3]],
        )
        for ordinal, gate_id in enumerate(
            ("E01", "E02", "E03", "E04", "E06", "E07", "E08")
        )
    ]
    return _seal(
        {
            "route_result_schema_version": "experimental.v3m0.b7.d0-route-result.v1",
            "route_id": route_id,
            "route_manifest": manifest,
            "route_manifest_sha": manifest["route_manifest_sha"],
            "route_commit_sha": manifest["route_commit_sha"],
            "legal_case_count": 7,
            "legal_case_accept_count": 7,
            "mutation_probe_count": 0,
            "mutation_accept_count": 0,
            "upstream_invalid_probe_count": 0,
            "upstream_invalid_transcript_count": 0,
            "evidence_loss_count": 0,
            "constructible_invalid_presence_count": 0,
            "half_pair_state_count": 0,
            "gate_outcomes": gates,
            "survives_d0": True,
            "route_result_sha": "",
        },
        "route_result_sha",
    )


def _validated_fixture() -> dict[str, object]:
    return _seal(
        {
            "fixture_schema_version": "experimental.v3m0.b7.corpus-fixture.v2",
            "corpus_spec": {"corpus_spec_sha": "4" * 64},
            "mutation_universe": {"mutation_universe_sha": "6" * 64},
            "metric_spec": {"metric_spec_sha": "7" * 64},
            "environment_manifest": {"environment_sha": "5" * 64},
            "synthetic_graph_manifest": {
                "selected_fejer_order": 256,
                "graph_sha": "a" * 64,
            },
            "ordered_d0_transcripts": _capture_transcripts(0),
            "fixture_sha": "",
        },
        "fixture_sha",
    )


def _environment_v2() -> dict[str, object]:
    return _seal(
        {
            "environment_schema_version": "experimental.v3m0.b7.environment-manifest.v2",
            "python_implementation": "CPython",
            "python_version": "3.test",
            "python_invocation_path": "/tmp/b7-venv/bin/python",
            "python_executable_realpath": "/usr/bin/python3",
            "python_executable_raw_sha256": "c" * 64,
            "python_invocation_identity_sha": "d" * 64,
            "python_venv_prefix": "/tmp/b7-venv",
            "python_pyvenv_cfg_path": "/tmp/b7-venv/pyvenv.cfg",
            "python_pyvenv_cfg_raw_sha256": "e" * 64,
            "numpy_version": "test",
            "scipy_version": "test",
            "platform_system": "test",
            "platform_release": "test",
            "platform_machine": "test",
            "numpy_float64_dtype_str": "<f8",
            "numpy_float64_itemsize": 8,
            "byteorder": "little",
            "python_hash_seed": "0",
            "blas_thread_settings": [
                ["OPENBLAS_NUM_THREADS", "1"],
                ["OMP_NUM_THREADS", "1"],
                ["MKL_NUM_THREADS", "1"],
                ["VECLIB_MAXIMUM_THREADS", "1"],
                ["NUMEXPR_NUM_THREADS", "1"],
            ],
            "threadpool_info": [],
            "fresh_process_per_capture": True,
            "environment_sha": "",
        },
        "environment_sha",
    )


def _comparison_fixture(environment: dict[str, object]) -> dict[str, object]:
    raw = _validated_fixture()
    raw["environment_manifest"] = copy.deepcopy(environment)
    raw["synthetic_graph_manifest"] = _full_synthetic_graph()
    for transcript in raw["ordered_d0_transcripts"]:
        transcript["environment_manifest_sha"] = environment["environment_sha"]
    return _seal(raw, "fixture_sha")


_FULL_GRAPH_CACHE: dict[str, object] | None = None


def _full_synthetic_graph() -> dict[str, object]:
    global _FULL_GRAPH_CACHE
    if _FULL_GRAPH_CACHE is None:
        support_path = Path(__file__).with_name("test_v3m0_b7_pure_replay_core.py")
        spec = importlib.util.spec_from_file_location("_b7_task4_support", support_path)
        assert spec is not None and spec.loader is not None
        support = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(support)
        provenance = support._task4_provenance_fixture()
        _FULL_GRAPH_CACHE = support._task4_graph_manifest(provenance)
    return copy.deepcopy(_FULL_GRAPH_CACHE)


def _d0_comparison(
    *,
    fixture_raw_bytes: bytes,
    common_commit_sha: str,
    common_source_sha256: str,
    compare_source_sha256: str,
    environment: dict[str, object],
    survivor_ids: tuple[str, ...] = ROUTE_IDS,
) -> dict[str, object]:
    route_results = []
    for route_id in ROUTE_IDS:
        route = _d0_route_result(route_id)
        route["route_manifest"] = _route_manifest(
            route_id,
            common_commit_sha=common_commit_sha,
            common_source_sha256=common_source_sha256,
            compare_source_sha256=compare_source_sha256,
        )
        route["route_manifest_sha"] = route["route_manifest"]["route_manifest_sha"]
        route["route_commit_sha"] = route["route_manifest"]["route_commit_sha"]
        route["survives_d0"] = route_id in survivor_ids
        _seal(route, "route_result_sha")
        route_results.append(route)
    raw = {
        "d0_result_schema_version": "experimental.v3m0.b7.d0-comparison.v1",
        "common_commit_sha": common_commit_sha,
        "common_source_sha256": common_source_sha256,
        "compare_source_sha256": compare_source_sha256,
        "corpus_fixture_raw_sha256": hashlib.sha256(fixture_raw_bytes).hexdigest(),
        "corpus_spec_sha": "4" * 64,
        "mutation_universe_sha": "6" * 64,
        "metric_spec_sha": "7" * 64,
        "environment_manifest": copy.deepcopy(environment),
        "ordered_route_results": route_results,
        "surviving_route_ids": list(survivor_ids),
        "decision_payload_sha": "",
        "auxiliary_benchmark": {},
        "d0_result_sha": "",
    }
    common = _common()
    raw["decision_payload_sha"] = common.canonical_sha_v1(
        {name: raw[name] for name in common._D0_DECISION_FIELDS}
    )
    return _seal(raw, "d0_result_sha")


def _d1_auxiliary(route_ids: tuple[str, ...]) -> dict[str, object]:
    return {
        "warm_up": 5,
        "repeat": 30,
        "reported_statistics": ["median", "p95", "tracemalloc_peak"],
        "ordered_route_statistics": [
            {
                "route_id": route_id,
                "median": float(ordinal + 1) / 1000.0,
                "p95": float(ordinal + 2) / 1000.0,
                "tracemalloc_peak": ordinal + 1,
            }
            for ordinal, route_id in enumerate(route_ids)
        ],
    }


def _patch_d1_route_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    common = _common()
    monkeypatch.setattr(
        common,
        "validate_route_static_surface_v1",
        lambda manifest, _route_blob, _production_blobs: copy.deepcopy(manifest),
    )

    def gate_builder(gate_id: str):
        def build(*, phase: str, route_id: str | None = None, **kwargs):
            if route_id is None:
                route_id = kwargs["route_manifest"]["route_id"]
            return common.build_gate_outcome_v1(
                gate_id=gate_id,
                phase=phase,
                route_id=route_id,
                domain_root_sha=gate_id[-1].lower() * 64,
                predicate_results=[True for _ in common._gate_contract_v1(gate_id)[3]],
            )

        return build

    for gate_id in ("E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08"):
        monkeypatch.setattr(
            common, f"build_gate_{gate_id.lower()}_v1", gate_builder(gate_id)
        )
    monkeypatch.setattr(
        common,
        "_validate_legal_replay_domain_v1",
        lambda **_kwargs: {
            "domain_root_sha": "1" * 64,
            "predicate_results": (True, True, True),
            "accepted_count": 21,
        },
    )
    monkeypatch.setattr(
        common,
        "_validate_mutation_probe_domain_v1",
        lambda **_kwargs: {
            "domain_root_sha": "2" * 64,
            "predicate_results": (True, True, True),
            "mutation_probe_count": 0,
            "mutation_accept_count": 0,
            "normalized": [],
        },
    )
    monkeypatch.setattr(
        common,
        "_validate_e03_domain_v1",
        lambda **_kwargs: {
            "domain_root_sha": "3" * 64,
            "predicate_results": (True, True),
            "evidence_loss_count": 0,
        },
    )
    monkeypatch.setattr(
        common,
        "_derive_e03_domain_from_legal_v1",
        lambda **_kwargs: {
            "domain_root_sha": "3" * 64,
            "predicate_results": (True, True),
            "evidence_loss_count": 0,
        },
    )
    monkeypatch.setattr(
        common,
        "_validate_e04_domain_v1",
        lambda **_kwargs: {
            "domain_root_sha": "4" * 64,
            "predicate_results": (True, True, True),
            "canonical_accept_count": 0,
            "half_pair_state_count": 0,
        },
    )
    monkeypatch.setattr(
        common,
        "_validate_invalid_presence_domain_v1",
        lambda **_kwargs: {
            "normalized": [],
            "canonical_accept_count": 0,
            "half_pair_state_count": 0,
            "all_exact_rejections": True,
        },
    )
    monkeypatch.setattr(
        common,
        "_derive_e04_domain_from_legal_and_invalid_v1",
        lambda **_kwargs: {
            "domain_root_sha": "4" * 64,
            "predicate_results": (True, True, True),
            "canonical_accept_count": 0,
            "half_pair_state_count": 0,
        },
    )
    monkeypatch.setattr(
        common,
        "_validate_e06_domain_v1",
        lambda _summary: {
            "domain_root_sha": "6" * 64,
            "predicate_results": (True, True, True),
        },
    )
    monkeypatch.setattr(
        common,
        "compute_route_static_metrics_v1",
        lambda _route_id, _route_blob: {
            "b8_consumer_assertion_count": 8,
            "b8_consumer_changed_loc": 0,
            "verifier_branch_count": 3,
            "route_record_count": 2,
            "route_hash_layer_count": 1,
        },
    )


def test_d1_route_result_assembles_cells_gates_metric_and_survival(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    _patch_d1_route_dependencies(monkeypatch)
    d0 = _d0_route_result()
    manifest = d0["route_manifest"]
    gate_inputs = {
        "ordered_legal_replays": _route_replays("A_FLAT"),
        "ordered_mutation_probes": [],
        "ordered_invalid_presence_probes": [],
    }
    capture_inputs = [
        {
            "route_id": "A_FLAT",
            "route_manifest_sha": manifest["route_manifest_sha"],
            "ordered_legal_replays": gate_inputs["ordered_legal_replays"],
        }
    ]

    result = common.build_d1_route_result_v1(
        d0_route_result=d0,
        route_blob=("a" * 40, manifest["route_source_path"], "100644", b"route"),
        production_blobs=(("b" * 40, "rulespace_v3/x.py", "100644", b"x"),),
        validated_corpus_fixture=_validated_fixture(),
        ordered_capture_source_bytes=_ordered_capture_source_bytes(),
        gate_inputs=gate_inputs,
        ordered_survivor_route_ids=["A_FLAT"],
        ordered_route_capture_inputs=capture_inputs,
    )

    assert [gate["gate_id"] for gate in result["gate_outcomes"]] == [
        "E01",
        "E02",
        "E03",
        "E04",
        "E05",
        "E06",
        "E07",
        "E08",
    ]
    assert [
        cell["capture_ordinal"] for cell in result["ordered_cross_replay_cells"]
    ] == [0, 1, 2]
    assert [result["metric_vector"][name] for name in common._METRIC_ORDER_V1] == [
        0,
        0,
        0,
        0,
        8,
        0,
        3,
        2,
        1,
        sum(
            len(row["encode_result"]["raw_bytes"])
            for row in gate_inputs["ordered_legal_replays"]
        ),
    ]
    assert result["survives_d1"] is True


def test_d0_route_reports_only_must_reject_mutation_probe_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_d1_route_dependencies(monkeypatch)
    fixture = _validated_fixture()
    monkeypatch.setattr(
        common,
        "_validated_d0_fixture_source_domain_v1",
        lambda raw: (copy.deepcopy(raw), [_capture_transcripts(0)]),
    )
    monkeypatch.setattr(
        common,
        "_validate_legal_replay_domain_v1",
        lambda **_kwargs: {
            "domain_root_sha": "1" * 64,
            "predicate_results": (True, True, True),
            "accepted_count": 7,
        },
    )
    monkeypatch.setattr(
        common,
        "_validate_mutation_probe_domain_v1",
        lambda **_kwargs: {
            "domain_root_sha": "2" * 64,
            "predicate_results": (True, True, True),
            "total_observation_count": 5,
            "mutation_probe_count": 2,
            "mutation_must_reject_count": 2,
            "mutation_accept_count": 0,
            "invalid_rejection_surface_count": 0,
            "upstream_invalid_probe_count": 1,
            "upstream_invalid_transcript_count": 0,
            "all_upstream_route_entry_counts_zero": True,
            "normalized": [],
        },
    )
    monkeypatch.setattr(
        common,
        "_derive_e03_domain_from_legal_v1",
        lambda **_kwargs: {
            "domain_root_sha": "3" * 64,
            "predicate_results": (True, True),
            "evidence_loss_count": 0,
        },
    )
    monkeypatch.setattr(
        common,
        "_validate_invalid_presence_domain_v1",
        lambda **_kwargs: {
            "normalized": [],
            "all_exact_rejections": True,
            "canonical_accept_count": 0,
            "half_pair_state_count": 0,
        },
    )
    monkeypatch.setattr(
        common,
        "_derive_e04_domain_from_legal_and_invalid_v1",
        lambda **_kwargs: {
            "domain_root_sha": "4" * 64,
            "predicate_results": (True, True, True),
            "canonical_accept_count": 0,
            "half_pair_state_count": 0,
        },
    )
    for gate_id in ("E07", "E08"):
        monkeypatch.setattr(
            common,
            f"_validate_{gate_id.lower()}_static_domain_v1",
            lambda *_args, gate_id=gate_id: {
                "domain_root_sha": gate_id[-1].lower() * 64,
                "predicate_results": tuple(
                    True for _ in common._gate_contract_v1(gate_id)[3]
                ),
            },
        )
    manifest = _route_manifest()

    result = common.build_d0_route_result_v1(
        route_manifest=manifest,
        route_blob=("a" * 40, manifest["route_source_path"], "100644", b"route"),
        production_blobs=(("b" * 40, "rulespace_v3/x.py", "100644", b"x"),),
        validated_corpus_fixture=fixture,
        gate_inputs={
            "ordered_legal_replays": [],
            "ordered_mutation_probes": [],
            "ordered_invalid_presence_probes": [],
        },
    )

    assert result["mutation_probe_count"] == 2


def test_d1_route_consumes_each_dynamic_domain_once_and_reuses_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    _patch_d1_route_dependencies(monkeypatch)
    calls = {name: 0 for name in ("legal", "mutation", "evidence", "presence")}

    def domain(name: str, body: dict[str, object]):
        def validate(**_kwargs):
            calls[name] += 1
            return copy.deepcopy(body)

        return validate

    monkeypatch.setattr(
        common,
        "_validate_legal_replay_domain_v1",
        domain(
            "legal",
            {
                "domain_root_sha": "1" * 64,
                "predicate_results": (True, True, True),
                "accepted_count": 21,
            },
        ),
    )
    monkeypatch.setattr(
        common,
        "_validate_mutation_probe_domain_v1",
        lambda **kwargs: (
            calls.__setitem__("mutation", calls["mutation"] + 1)
            or tuple(kwargs["ordered_mutation_probes"])
            or {
                "domain_root_sha": "2" * 64,
                "predicate_results": (True, True, True),
                "mutation_accept_count": 0,
                "normalized": [],
            }
        ),
    )
    monkeypatch.setattr(
        common,
        "_derive_e03_domain_from_legal_v1",
        domain(
            "evidence",
            {
                "domain_root_sha": "3" * 64,
                "predicate_results": (True, True),
                "evidence_loss_count": 0,
            },
        ),
    )
    monkeypatch.setattr(
        common,
        "_validate_invalid_presence_domain_v1",
        lambda **kwargs: (
            calls.__setitem__("presence", calls["presence"] + 1)
            or tuple(kwargs["ordered_invalid_presence_probes"])
            or {
                "normalized": [],
                "canonical_accept_count": 0,
                "half_pair_state_count": 0,
                "all_exact_rejections": True,
            }
        ),
    )
    monkeypatch.setattr(
        common,
        "_derive_e04_domain_from_legal_and_invalid_v1",
        lambda **_kwargs: {
            "domain_root_sha": "4" * 64,
            "predicate_results": (True, True, True),
            "canonical_accept_count": 0,
            "half_pair_state_count": 0,
        },
    )
    monkeypatch.setattr(
        common,
        "_validate_e06_domain_v1",
        lambda summary: {
            "domain_root_sha": "6" * 64,
            "predicate_results": (True, True, True),
        },
    )

    def must_not_reconsume(**_kwargs):
        raise AssertionError("D1 gate builder re-consumed a dynamic domain")

    for gate_id in ("e01", "e02", "e03", "e04", "e06"):
        monkeypatch.setattr(common, f"build_gate_{gate_id}_v1", must_not_reconsume)
    monkeypatch.setattr(common, "_validate_e03_domain_v1", must_not_reconsume)
    monkeypatch.setattr(common, "_validate_e04_domain_v1", must_not_reconsume)

    d0 = _d0_route_result()
    manifest = d0["route_manifest"]
    replays = _route_replays("A_FLAT")
    result = common.build_d1_route_result_v1(
        d0_route_result=d0,
        route_blob=("a" * 40, manifest["route_source_path"], "100644", b"route"),
        production_blobs=(("b" * 40, "rulespace_v3/x.py", "100644", b"x"),),
        validated_corpus_fixture=_validated_fixture(),
        ordered_capture_source_bytes=_ordered_capture_source_bytes(),
        gate_inputs={
            "ordered_legal_replays": replays,
            "ordered_mutation_probes": iter(()),
            "ordered_invalid_presence_probes": iter(()),
        },
        ordered_survivor_route_ids=["A_FLAT"],
        ordered_route_capture_inputs=[
            {
                "route_id": "A_FLAT",
                "route_manifest_sha": manifest["route_manifest_sha"],
                "ordered_legal_replays": replays,
            }
        ],
    )

    assert calls == {"legal": 1, "mutation": 1, "evidence": 1, "presence": 1}
    assert [gate["gate_id"] for gate in result["gate_outcomes"]] == [
        "E01",
        "E02",
        "E03",
        "E04",
        "E05",
        "E06",
        "E07",
        "E08",
    ]


def test_d1_mutation_domain_materializes_from_each_capture_not_d0(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    case_ids = list(CASE_IDS)
    d0_sources = [{"case_id": case_id, "capture": "D0"} for case_id in case_ids]
    source_sets = [
        [{"case_id": case_id, "capture": capture_ordinal} for case_id in case_ids]
        for capture_ordinal in range(3)
    ]
    mutation = {
        "mutation_ordinal": 0,
        "mutation_id": "M000000-CANONICAL_ROUNDTRIP",
        "mutation_sha": "a" * 64,
        "base_case_id": "success",
        "probe_kind": "ROUNDTRIP_MUST_EQUAL",
        "mutation_class": "CANONICAL_ROUNDTRIP",
        "operation": "REENCODE",
    }
    fixture = {
        "mutation_universe": {
            "ordered_mutations": [mutation],
            "mutation_count": 1,
            "mutation_universe_sha": "b" * 64,
        },
        "ordered_d0_transcripts": d0_sources,
    }
    monkeypatch.setattr(
        common,
        "_validated_d0_fixture_source_domain_v1",
        lambda _fixture: (fixture, [d0_sources]),
    )
    monkeypatch.setattr(
        common,
        "_validated_gate_fixture_source_domain_v1",
        lambda phase, _fixture, supplied: (
            (fixture, supplied) if phase == "D1" else (fixture, [d0_sources])
        ),
    )
    monkeypatch.setattr(common, "validate_mutation_v1", copy.deepcopy)
    monkeypatch.setattr(
        common,
        "generate_ordered_mutations_v1",
        lambda _sources: [copy.deepcopy(mutation)],
    )
    probes = []
    for capture_ordinal, sources in enumerate(source_sets):
        source = common.canonical_json_bytes_v1(sources[-1])
        probes.append(
            {
                "capture_ordinal": capture_ordinal,
                "mutation_ordinal": 0,
                "mutation_id": mutation["mutation_id"],
                "mutation_sha": mutation["mutation_sha"],
                "route_id": "A_FLAT",
                "materialized_transcript_bytes": source,
                "upstream_transcript_count": 1,
                "first_encode_result": {
                    "termination_kind": "RETURNED_BYTES",
                    "raw_bytes": b'{"wire":true}',
                },
                "first_decode_result": {
                    "termination_kind": "RETURNED_BYTES",
                    "raw_bytes": source,
                },
                "second_encode_result": {
                    "termination_kind": "NOT_CALLED",
                    "raw_bytes": None,
                },
                "second_decode_result": {
                    "termination_kind": "NOT_CALLED",
                    "raw_bytes": None,
                },
            }
        )

    one_shot_probes = iter(probes)
    domain = common._validate_mutation_probe_domain_v1(
        phase="D1",
        route_id="A_FLAT",
        validated_corpus_fixture=fixture,
        ordered_source_transcript_sets=source_sets,
        ordered_mutation_probes=one_shot_probes,
    )
    with pytest.raises(StopIteration):
        next(one_shot_probes)
    assert (
        len({row["materialized_transcript_raw_sha256"] for row in domain["normalized"]})
        == 3
    )

    hostile = copy.deepcopy(probes)
    hostile[1]["materialized_transcript_bytes"] = hostile[0][
        "materialized_transcript_bytes"
    ]
    hostile[1]["first_decode_result"]["raw_bytes"] = hostile[0][
        "materialized_transcript_bytes"
    ]
    with pytest.raises((TypeError, ValueError)):
        common._validate_mutation_probe_domain_v1(
            phase="D1",
            route_id="A_FLAT",
            validated_corpus_fixture=fixture,
            ordered_source_transcript_sets=source_sets,
            ordered_mutation_probes=hostile,
        )


def _d1_route_inputs(
    d0: dict[str, object],
    route_ids: tuple[str, ...],
) -> list[dict[str, object]]:
    by_id = {row["route_id"]: row for row in d0["ordered_route_results"]}
    inputs = []
    for route_id in route_ids:
        manifest = by_id[route_id]["route_manifest"]
        inputs.append(
            {
                "route_manifest": manifest,
                "route_blob": (
                    manifest["route_commit_sha"],
                    manifest["route_source_path"],
                    "100644",
                    f"route-{route_id}".encode(),
                ),
                "production_blobs": (
                    (
                        d0["common_commit_sha"],
                        "rulespace_v3/x.py",
                        "100644",
                        b"x",
                    ),
                ),
                "gate_inputs": {
                    "ordered_legal_replays": _route_replays(route_id),
                    "ordered_mutation_probes": [],
                    "ordered_invalid_presence_probes": [],
                },
            }
        )
    return inputs


def _fake_d1_route_result(
    d0_route: dict[str, object],
    cells: list[dict[str, object]],
    metric_values: tuple[int, ...],
    survives: bool,
) -> dict[str, object]:
    common = _common()
    route_id = d0_route["route_id"]
    gates = [
        common.build_gate_outcome_v1(
            gate_id=gate_id,
            phase="D1",
            route_id=route_id,
            domain_root_sha=f"{ordinal + 1:x}" * 64,
            predicate_results=[survives for _ in common._gate_contract_v1(gate_id)[3]],
        )
        for ordinal, gate_id in enumerate(
            ("E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08")
        )
    ]
    metric = {
        name: value for name, value in zip(common._METRIC_ORDER_V1, metric_values)
    }
    metric["metric_vector_sha"] = ""
    _seal(metric, "metric_vector_sha")
    return _seal(
        {
            "route_result_schema_version": "experimental.v3m0.b7.d1-route-result.v1",
            "route_id": route_id,
            "route_manifest": copy.deepcopy(d0_route["route_manifest"]),
            "route_manifest_sha": d0_route["route_manifest_sha"],
            "route_commit_sha": d0_route["route_commit_sha"],
            "ordered_cross_replay_cells": copy.deepcopy(cells),
            "gate_outcomes": gates,
            "metric_vector": metric,
            "survives_d1": survives,
            "route_result_sha": "",
        },
        "route_result_sha",
    )


@pytest.mark.parametrize(
    ("state", "survival", "metric_rows", "winner", "tie"),
    (
        (
            "no_survivor",
            {"A_FLAT": False, "B_PROGRESS": False},
            {"A_FLAT": (0,) * 10, "B_PROGRESS": (1,) * 10},
            None,
            False,
        ),
        (
            "unique",
            {"A_FLAT": True, "B_PROGRESS": True},
            {"A_FLAT": (0,) * 10, "B_PROGRESS": (0,) * 9 + (1,)},
            "A_FLAT",
            False,
        ),
        (
            "tie",
            {"A_FLAT": True, "B_PROGRESS": True},
            {"A_FLAT": (0,) * 10, "B_PROGRESS": (0,) * 10},
            None,
            True,
        ),
    ),
)
def test_d1_comparison_derives_no_survivor_unique_and_tie(
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    survival: dict[str, bool],
    metric_rows: dict[str, tuple[int, ...]],
    winner: str | None,
    tie: bool,
) -> None:
    del state
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    common_source = b"frozen-common"
    compare_source = b"frozen-compare"
    leaf_source = b"frozen-leaf-provider"
    common_sha = hashlib.sha256(common_source).hexdigest()
    compare_sha = hashlib.sha256(compare_source).hexdigest()
    environment = _environment_v2()
    fixture = _comparison_fixture(environment)
    fixture_bytes = common.canonical_json_bytes_v1(fixture) + b"\n"
    d0 = _d0_comparison(
        fixture_raw_bytes=fixture_bytes,
        common_commit_sha="b" * 40,
        common_source_sha256=common_sha,
        compare_source_sha256=compare_sha,
        environment=environment,
        survivor_ids=("A_FLAT", "B_PROGRESS"),
    )
    d0_bytes = common.canonical_json_bytes_v1(d0) + b"\n"
    route_inputs = _d1_route_inputs(d0, ("A_FLAT", "B_PROGRESS"))
    capture_inputs = [
        {
            "route_id": row["route_manifest"]["route_id"],
            "route_manifest_sha": row["route_manifest"]["route_manifest_sha"],
            "ordered_legal_replays": row["gate_inputs"]["ordered_legal_replays"],
        }
        for row in route_inputs
    ]
    cross = common._build_d1_cross_replay_domain_v1(
        synthetic_graph_manifest_sha=fixture["synthetic_graph_manifest"]["graph_sha"],
        ordered_survivor_route_ids=["A_FLAT", "B_PROGRESS"],
        ordered_capture_source_bytes=_ordered_capture_source_bytes(),
        ordered_route_capture_inputs=capture_inputs,
    )
    d0_by_id = {row["route_id"]: row for row in d0["ordered_route_results"]}

    def build_route(*, d0_route_result: dict[str, object], **_kwargs):
        route_id = d0_route_result["route_id"]
        ordinal = ("A_FLAT", "B_PROGRESS").index(route_id)
        return _fake_d1_route_result(
            d0_by_id[route_id],
            cross["route_cells"][ordinal],
            metric_rows[route_id],
            survival[route_id],
        )

    monkeypatch.setattr(common, "build_d1_route_result_v1", build_route, raising=False)
    monkeypatch.setattr(
        common,
        "validate_corpus_fixture_v2",
        lambda raw, *_args, **_kwargs: copy.deepcopy(raw),
    )
    monkeypatch.setattr(
        common,
        "validate_synthetic_graph_manifest_v1",
        lambda raw: copy.deepcopy(raw),
    )
    lineage_calls = []

    def validate_transcript(raw: object, **kwargs):
        lineage_calls.append((raw["case_id"], kwargs["validated_graph"]))
        assert raw["response_run_spec_fixture"]["selected_fejer_order"] == 256
        return copy.deepcopy(raw)

    monkeypatch.setattr(
        common,
        "_validate_normalized_transcript_against_validated_graph_v1",
        validate_transcript,
    )
    common_blob = ("b" * 40, common._COMMON_SOURCE_PATH_V1, "100644", common_source)
    compare_blob = ("b" * 40, common._COMPARE_SOURCE_PATH_V1, "100644", compare_source)
    leaf_blob = (
        "b" * 40,
        "rulespace_v3/b7_replay_core_v1.py",
        "100644",
        leaf_source,
    )

    def build_comparison(
        *,
        d0_raw: bytes = d0_bytes,
        fixture_raw: bytes = fixture_bytes,
    ) -> dict[str, object]:
        return common.build_d1_comparison_v1(
            d0_result_raw_bytes=d0_raw,
            corpus_fixture_raw_bytes=fixture_raw,
            common_blob=common_blob,
            compare_blob=compare_blob,
            leaf_provider_blob=leaf_blob,
            python_identity_observation={},
            python_probe_result={},
            ordered_capture_source_bytes=_ordered_capture_source_bytes(),
            ordered_route_inputs=route_inputs,
            auxiliary_benchmark=_d1_auxiliary(("A_FLAT", "B_PROGRESS")),
        )

    result = build_comparison()

    for hostile_d0 in (d0_bytes[:-1], d0_bytes + b"\n"):
        with pytest.raises(ValueError, match="D0 input.*exactly one LF"):
            build_comparison(d0_raw=hostile_d0)
    for hostile_fixture in (fixture_bytes[:-1], fixture_bytes + b"\n"):
        with pytest.raises(ValueError, match="fixture.*exactly one LF"):
            build_comparison(fixture_raw=hostile_fixture)

    assert len(lineage_calls) == 21
    assert result["provisional_winner_route_id"] == winner
    assert result["tie_detected"] is tie
    assert result["surviving_route_ids"] == [
        route_id for route_id in ("A_FLAT", "B_PROGRESS") if survival[route_id]
    ]
    if winner is None and not any(survival.values()):
        assert result["minimum_metric_vector"] is None
    else:
        assert result["minimum_metric_vector"] is not None
