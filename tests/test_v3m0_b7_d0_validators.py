"""Mechanical D0 closure for the B7 schema laboratory."""

from __future__ import annotations

import copy
import hashlib

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


def _source_transcripts(
    *,
    corpus_spec_sha: str = "4" * 64,
    environment_manifest_sha: str = "5" * 64,
) -> list[dict[str, object]]:
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
                "corpus_spec_sha": corpus_spec_sha,
                "environment_manifest_sha": environment_manifest_sha,
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


def _environment_v2() -> dict[str, object]:
    return _seal(
        {
            "environment_schema_version": (
                "experimental.v3m0.b7.environment-manifest.v2"
            ),
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


def _comparison_fixture() -> dict[str, object]:
    environment = _environment_v2()
    raw = {
        "fixture_schema_version": "experimental.v3m0.b7.corpus-fixture.v2",
        "corpus_spec": {"corpus_spec_sha": "4" * 64},
        "mutation_universe": {"mutation_universe_sha": "6" * 64},
        "metric_spec": {"metric_spec_sha": "7" * 64},
        "environment_manifest": environment,
        "synthetic_graph_manifest": {},
        "ordered_d0_transcripts": _source_transcripts(
            environment_manifest_sha=environment["environment_sha"]
        ),
        "fixture_sha": "",
    }
    return _seal(raw, "fixture_sha")


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
    monkeypatch.setattr(
        _common(),
        "iter_constructible_invalid_presence_candidates_v1",
        lambda _success: (copy.deepcopy(candidate) for candidate in candidates),
        raising=False,
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


def test_invalid_presence_metric_counts_only_canonical_encoder_accepts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    _patch_invalid_presence_generator(monkeypatch)
    fixture = _validated_fixture()
    invalid = _invalid_presence_probes()
    invalid[0]["encode_result"] = _call("WRONG_EXCEPTION")
    invalid[1]["encode_result"] = _call("RETURNED_NONBYTES")
    invalid[2]["encode_result"] = _call("RETURNED_BYTES", b"not-json")
    invalid[3]["encode_result"] = _call("RETURNED_BYTES", b'{"accepted":true}')

    domain = common._validate_invalid_presence_domain_v1(
        phase="D0",
        route_id="A_FLAT",
        ordered_source_transcript_sets=[fixture["ordered_d0_transcripts"]],
        ordered_invalid_presence_probes=invalid,
    )

    assert domain["canonical_accept_count"] == 1
    assert domain["all_exact_rejections"] is False


def test_invalid_presence_domain_consumes_one_shot_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    _patch_invalid_presence_generator(monkeypatch)
    fixture = _validated_fixture()
    one_shot = iter(_invalid_presence_probes())

    domain = common._validate_invalid_presence_domain_v1(
        phase="D0",
        route_id="A_FLAT",
        ordered_source_transcript_sets=[fixture["ordered_d0_transcripts"]],
        ordered_invalid_presence_probes=one_shot,
    )

    assert len(domain["normalized"]) == 1393
    assert all(
        "candidate_transcript_bytes" not in normalized
        for normalized in domain["normalized"]
    )
    with pytest.raises((TypeError, ValueError), match="cardinality|exhaust"):
        common._validate_invalid_presence_domain_v1(
            phase="D0",
            route_id="A_FLAT",
            ordered_source_transcript_sets=[fixture["ordered_d0_transcripts"]],
            ordered_invalid_presence_probes=one_shot,
        )


def test_invalid_presence_candidate_iterator_is_lazy_and_list_api_is_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_simple_case_validation(monkeypatch)
    success = _source_transcripts()[-1]

    one_shot = common.iter_constructible_invalid_presence_candidates_v1(success)
    assert iter(one_shot) is one_shot
    first = next(one_shot)
    remainder = list(one_shot)
    eager = common.generate_constructible_invalid_presence_candidates_v1(success)

    assert len(remainder) == 1392
    assert eager == [first, *remainder]


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
            "route_manifest_schema_version": ("experimental.v3m0.b7.route-manifest.v1"),
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
            "input_schema_version": ("experimental.v3m0.b7.normalized-transcript.v1"),
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


def _gate_inputs() -> dict[str, object]:
    return {
        "ordered_legal_replays": [],
        "ordered_mutation_probes": [],
        "ordered_invalid_presence_probes": [],
    }


def _patch_d0_route_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    mutation_accept_count: int = 0,
    mutation_accept_by_route: dict[str, int] | None = None,
) -> None:
    common = _common()
    monkeypatch.setattr(
        common,
        "validate_route_static_surface_v1",
        lambda manifest, _route_blob, _production_blobs: copy.deepcopy(manifest),
    )
    monkeypatch.setattr(
        common,
        "_validate_legal_replay_domain_v1",
        lambda **_kwargs: {
            "accepted_count": 7,
            "domain_root_sha": "1" * 64,
            "predicate_results": (True, True, True),
            "validated_source_sets": [],
        },
    )
    monkeypatch.setattr(
        common,
        "_derive_e03_domain_from_legal_v1",
        lambda **_kwargs: {
            "domain_root_sha": "3" * 64,
            "predicate_results": (True, True),
            "evidence_loss_count": 0,
            "normalized": [],
        },
        raising=False,
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
        raising=False,
    )

    def mutation_domain(**kwargs):
        route_mutation_count = mutation_accept_count
        if mutation_accept_by_route is not None:
            route_mutation_count = mutation_accept_by_route[kwargs["route_id"]]
        return {
            "mutation_probe_count": 300,
            "mutation_must_reject_count": 300,
            "total_observation_count": 303,
            "mutation_accept_count": route_mutation_count,
            "upstream_invalid_probe_count": 1,
            "upstream_invalid_transcript_count": 0,
            "all_upstream_route_entry_counts_zero": True,
            "domain_root_sha": "2" * 64,
            "predicate_results": (True, route_mutation_count == 0, True),
            "normalized": [],
        }

    monkeypatch.setattr(
        common,
        "_validate_mutation_probe_domain_v1",
        mutation_domain,
        raising=False,
    )

    monkeypatch.setattr(
        common,
        "_validate_e06_domain_v1",
        lambda _mutation: {
            "domain_root_sha": "6" * 64,
            "predicate_results": (True, True, True),
            "normalized": [],
        },
    )

    for gate_id in ("E07", "E08"):
        monkeypatch.setattr(
            common,
            f"_validate_{gate_id.lower()}_static_domain_v1",
            lambda manifest, _route_blob, _production_blobs, frozen=gate_id: {
                "domain_root_sha": frozen[-1] * 64,
                "predicate_results": tuple(
                    True for _predicate in common._gate_contract_v1(frozen)[3]
                ),
                "validated_route_manifest": copy.deepcopy(manifest),
            },
            raising=False,
        )


def test_d0_route_result_recomputes_gate_order_metrics_survival_and_self_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_d0_route_dependencies(monkeypatch)
    manifest = _route_manifest()

    result = common.build_d0_route_result_v1(
        route_manifest=manifest,
        route_blob=("a" * 40, manifest["route_source_path"], "100644", b"route"),
        production_blobs=(("b" * 40, "rulespace_v3/x.py", "100644", b"x"),),
        validated_corpus_fixture=_validated_fixture(),
        gate_inputs=_gate_inputs(),
    )

    assert [gate["gate_id"] for gate in result["gate_outcomes"]] == [
        "E01",
        "E02",
        "E03",
        "E04",
        "E06",
        "E07",
        "E08",
    ]
    assert result["legal_case_count"] == 7
    assert result["legal_case_accept_count"] == 7
    assert result["mutation_probe_count"] == 300
    assert result["upstream_invalid_probe_count"] == 1
    assert result["survives_d0"] is True
    assert common.validate_exact_lab_record_v1("B7LabD0RouteResultV1", result) == result
    assert (
        common.validate_d0_route_result_v1(
            result,
            route_blob=(
                "a" * 40,
                manifest["route_source_path"],
                "100644",
                b"route",
            ),
            production_blobs=(("b" * 40, "rulespace_v3/x.py", "100644", b"x"),),
            validated_corpus_fixture=_validated_fixture(),
            gate_inputs=_gate_inputs(),
        )
        == result
    )


@pytest.mark.parametrize("gate_ordinal", range(7))
def test_d0_route_result_rejects_each_gate_self_report_flip(
    monkeypatch: pytest.MonkeyPatch,
    gate_ordinal: int,
) -> None:
    common = _common()
    _patch_d0_route_dependencies(monkeypatch)
    manifest = _route_manifest()
    route_blob = ("a" * 40, manifest["route_source_path"], "100644", b"route")
    production = (("b" * 40, "rulespace_v3/x.py", "100644", b"x"),)
    result = common.build_d0_route_result_v1(
        route_manifest=manifest,
        route_blob=route_blob,
        production_blobs=production,
        validated_corpus_fixture=_validated_fixture(),
        gate_inputs=_gate_inputs(),
    )
    result["gate_outcomes"][gate_ordinal]["passed"] = False
    _seal(result["gate_outcomes"][gate_ordinal], "gate_outcome_sha")
    _seal(result, "route_result_sha")

    with pytest.raises((TypeError, ValueError)):
        common.validate_d0_route_result_v1(
            result,
            route_blob=route_blob,
            production_blobs=production,
            validated_corpus_fixture=_validated_fixture(),
            gate_inputs=_gate_inputs(),
        )


def test_d0_route_result_rejects_gate_reorder_and_count_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_d0_route_dependencies(monkeypatch)
    manifest = _route_manifest()
    route_blob = ("a" * 40, manifest["route_source_path"], "100644", b"route")
    production = (("b" * 40, "rulespace_v3/x.py", "100644", b"x"),)
    legal = common.build_d0_route_result_v1(
        route_manifest=manifest,
        route_blob=route_blob,
        production_blobs=production,
        validated_corpus_fixture=_validated_fixture(),
        gate_inputs=_gate_inputs(),
    )
    reordered = copy.deepcopy(legal)
    reordered["gate_outcomes"][0], reordered["gate_outcomes"][1] = (
        reordered["gate_outcomes"][1],
        reordered["gate_outcomes"][0],
    )
    _seal(reordered, "route_result_sha")
    substituted = copy.deepcopy(legal)
    substituted["mutation_probe_count"] += 1
    _seal(substituted, "route_result_sha")

    for hostile in (reordered, substituted):
        with pytest.raises((TypeError, ValueError)):
            common.validate_d0_route_result_v1(
                hostile,
                route_blob=route_blob,
                production_blobs=production,
                validated_corpus_fixture=_validated_fixture(),
                gate_inputs=_gate_inputs(),
            )


def test_d0_route_result_derives_non_survival_from_mutation_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_d0_route_dependencies(monkeypatch, mutation_accept_count=1)
    manifest = _route_manifest()
    result = common.build_d0_route_result_v1(
        route_manifest=manifest,
        route_blob=("a" * 40, manifest["route_source_path"], "100644", b"route"),
        production_blobs=(("b" * 40, "rulespace_v3/x.py", "100644", b"x"),),
        validated_corpus_fixture=_validated_fixture(),
        gate_inputs=_gate_inputs(),
    )

    assert result["mutation_accept_count"] == 1
    assert result["survives_d0"] is False


def test_d0_route_result_consumes_each_dynamic_domain_once_and_cannot_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_d0_route_dependencies(monkeypatch)
    calls = {"legal": 0, "mutation": 0, "evidence": 0, "invalid": 0, "presence": 0}

    def legal(**_kwargs):
        calls["legal"] += 1
        return {
            "accepted_count": 7,
            "domain_root_sha": "1" * 64,
            "predicate_results": (True, True, True),
            "validated_source_sets": [],
        }

    def mutation(**kwargs):
        calls["mutation"] += 1
        if list(kwargs["ordered_mutation_probes"]) != ["mutation-once"]:
            raise ValueError("mutation one-shot exhausted")
        return {
            "mutation_probe_count": 1,
            "mutation_must_reject_count": 1,
            "total_observation_count": 1,
            "mutation_accept_count": 0,
            "upstream_invalid_probe_count": 0,
            "upstream_invalid_transcript_count": 0,
            "all_upstream_route_entry_counts_zero": True,
            "domain_root_sha": "2" * 64,
            "predicate_results": (True, True, True),
            "normalized": [],
        }

    def evidence(**_kwargs):
        calls["evidence"] += 1
        return {
            "domain_root_sha": "3" * 64,
            "predicate_results": (True, True),
            "evidence_loss_count": 0,
            "normalized": [],
        }

    def invalid(**kwargs):
        calls["invalid"] += 1
        if list(kwargs["ordered_invalid_presence_probes"]) != ["presence-once"]:
            raise ValueError("presence one-shot exhausted")
        return {
            "normalized": [],
            "canonical_accept_count": 0,
            "half_pair_state_count": 0,
            "all_exact_rejections": True,
        }

    def presence(**_kwargs):
        calls["presence"] += 1
        return {
            "domain_root_sha": "4" * 64,
            "predicate_results": (True, True, True),
            "canonical_accept_count": 0,
            "half_pair_state_count": 0,
        }

    monkeypatch.setattr(common, "_validate_legal_replay_domain_v1", legal)
    monkeypatch.setattr(common, "_validate_mutation_probe_domain_v1", mutation)
    monkeypatch.setattr(common, "_derive_e03_domain_from_legal_v1", evidence, raising=False)
    monkeypatch.setattr(common, "_validate_invalid_presence_domain_v1", invalid)
    monkeypatch.setattr(
        common,
        "_derive_e04_domain_from_legal_and_invalid_v1",
        presence,
        raising=False,
    )
    manifest = _route_manifest()
    inputs = {
        "ordered_legal_replays": [],
        "ordered_mutation_probes": iter(["mutation-once"]),
        "ordered_invalid_presence_probes": iter(["presence-once"]),
    }
    arguments = {
        "route_manifest": manifest,
        "route_blob": ("a" * 40, manifest["route_source_path"], "100644", b"route"),
        "production_blobs": (("b" * 40, "rulespace_v3/x.py", "100644", b"x"),),
        "validated_corpus_fixture": _validated_fixture(),
        "gate_inputs": inputs,
    }

    common.build_d0_route_result_v1(**arguments)
    assert calls == {"legal": 1, "mutation": 1, "evidence": 1, "invalid": 1, "presence": 1}
    with pytest.raises(ValueError, match="one-shot exhausted"):
        common.build_d0_route_result_v1(**arguments)


def _comparison_inputs() -> tuple[
    tuple[str, str, str, bytes],
    tuple[str, str, str, bytes],
    list[dict[str, object]],
]:
    common_commit = "b" * 40
    common_source = b"frozen-common-source"
    compare_source = b"frozen-compare-source"
    common_sha = hashlib.sha256(common_source).hexdigest()
    compare_sha = hashlib.sha256(compare_source).hexdigest()
    common_blob = (
        common_commit,
        "experiments/v3m0_b7_schema_lab/common.py",
        "100644",
        common_source,
    )
    compare_blob = (
        common_commit,
        "experiments/v3m0_b7_schema_lab/compare.py",
        "100644",
        compare_source,
    )
    route_inputs = []
    for route_id in ("A_FLAT", "B_PROGRESS", "C_UNION"):
        manifest = _route_manifest(
            route_id,
            common_commit_sha=common_commit,
            common_source_sha256=common_sha,
            compare_source_sha256=compare_sha,
        )
        route_inputs.append(
            {
                "route_manifest": manifest,
                "route_blob": (
                    manifest["route_commit_sha"],
                    manifest["route_source_path"],
                    "100644",
                    f"route-{route_id}".encode(),
                ),
                "production_blobs": (
                    (common_commit, "rulespace_v3/x.py", "100644", b"x"),
                ),
                "gate_inputs": _gate_inputs(),
            }
        )
    return common_blob, compare_blob, route_inputs


def _patch_corpus_fixture_validation(
    monkeypatch: pytest.MonkeyPatch,
    events: list[tuple[object, ...]],
) -> None:
    common = _common()

    def validate(
        raw: object,
        common_source: object,
        compare_source: object,
        *,
        python_identity_observation: object,
        python_probe_result: object,
    ) -> object:
        events.append(
            (
                common_source,
                compare_source,
                python_identity_observation,
                python_probe_result,
            )
        )
        return copy.deepcopy(raw)

    monkeypatch.setattr(common, "validate_corpus_fixture_v2", validate)


def _reseal_d0_comparison(raw: dict[str, object]) -> None:
    common = _common()
    raw["decision_payload_sha"] = common.canonical_sha_v1(
        {name: raw[name] for name in common._D0_DECISION_FIELDS}
    )
    _seal(raw, "d0_result_sha")


def _auxiliary_benchmark() -> dict[str, object]:
    return {
        "warm_up": 5,
        "repeat": 30,
        "reported_statistics": ["median", "p95", "tracemalloc_peak"],
        "ordered_route_statistics": [
            {
                "route_id": route_id,
                "median": float(ordinal + 1) / 1000.0,
                "p95": float(ordinal + 2) / 1000.0,
                "tracemalloc_peak": (ordinal + 1) * 1024,
            }
            for ordinal, route_id in enumerate(("A_FLAT", "B_PROGRESS", "C_UNION"))
        ],
    }


def test_d0_comparison_revalidates_corpus_v2_and_stable_filters_survivors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    events: list[tuple[object, ...]] = []
    _patch_corpus_fixture_validation(monkeypatch, events)
    _patch_d0_route_dependencies(
        monkeypatch,
        mutation_accept_by_route={"A_FLAT": 0, "B_PROGRESS": 1, "C_UNION": 0},
    )
    fixture_bytes = common.canonical_json_bytes_v1(_comparison_fixture())
    common_blob, compare_blob, route_inputs = _comparison_inputs()
    identity = {"identity": "caller-observed"}
    probe = {"probe": "caller-observed"}

    result = common.build_d0_comparison_v1(
        corpus_fixture_raw_bytes=fixture_bytes,
        common_blob=common_blob,
        compare_blob=compare_blob,
        python_identity_observation=identity,
        python_probe_result=probe,
        ordered_route_inputs=route_inputs,
        auxiliary_benchmark=_auxiliary_benchmark(),
    )

    assert [route["route_id"] for route in result["ordered_route_results"]] == [
        "A_FLAT",
        "B_PROGRESS",
        "C_UNION",
    ]
    assert result["surviving_route_ids"] == ["A_FLAT", "C_UNION"]
    assert events == [(common_blob[3], compare_blob[3], identity, probe)]
    assert common.validate_d0_decision_payload_projection_v1(result) == result
    assert common.validate_exact_lab_record_v1("B7LabD0ComparisonV1", result) == result
    validated_route_ids: list[str] = []
    original_route_validator = common.validate_d0_route_result_v1

    def validate_route(raw_body: object, **kwargs: object) -> object:
        validated_route_ids.append(raw_body["route_id"])
        return original_route_validator(raw_body, **kwargs)

    monkeypatch.setattr(common, "validate_d0_route_result_v1", validate_route)
    assert (
        common.validate_d0_comparison_v1(
            result,
            corpus_fixture_raw_bytes=fixture_bytes,
            common_blob=common_blob,
            compare_blob=compare_blob,
            python_identity_observation=identity,
            python_probe_result=probe,
            ordered_route_inputs=route_inputs,
        )
        == result
    )
    assert validated_route_ids == []


@pytest.mark.parametrize(
    "mutator",
    (
        lambda inputs: inputs.reverse(),
        lambda inputs: inputs[0].update(unknown=None),
        lambda inputs: inputs[0].update(
            route_blob=(
                inputs[0]["route_blob"][0],
                inputs[1]["route_blob"][1],
                inputs[0]["route_blob"][2],
                inputs[0]["route_blob"][3],
            )
        ),
    ),
)
def test_d0_comparison_rejects_route_input_order_shape_and_blob_splice(
    monkeypatch: pytest.MonkeyPatch,
    mutator,
) -> None:
    common = _common()
    _patch_corpus_fixture_validation(monkeypatch, [])
    _patch_d0_route_dependencies(monkeypatch)
    common_blob, compare_blob, route_inputs = _comparison_inputs()
    mutator(route_inputs)

    with pytest.raises((TypeError, ValueError)):
        common.build_d0_comparison_v1(
            corpus_fixture_raw_bytes=common.canonical_json_bytes_v1(
                _comparison_fixture()
            ),
            common_blob=common_blob,
            compare_blob=compare_blob,
            python_identity_observation={},
            python_probe_result={},
            ordered_route_inputs=route_inputs,
            auxiliary_benchmark=_auxiliary_benchmark(),
        )


def test_d0_comparison_rejects_survivor_decision_and_route_result_attacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_corpus_fixture_validation(monkeypatch, [])
    _patch_d0_route_dependencies(
        monkeypatch,
        mutation_accept_by_route={"A_FLAT": 0, "B_PROGRESS": 1, "C_UNION": 0},
    )
    fixture_bytes = common.canonical_json_bytes_v1(_comparison_fixture())
    common_blob, compare_blob, route_inputs = _comparison_inputs()
    result = common.build_d0_comparison_v1(
        corpus_fixture_raw_bytes=fixture_bytes,
        common_blob=common_blob,
        compare_blob=compare_blob,
        python_identity_observation={},
        python_probe_result={},
        ordered_route_inputs=route_inputs,
        auxiliary_benchmark=_auxiliary_benchmark(),
    )
    survivor_attack = copy.deepcopy(result)
    survivor_attack["surviving_route_ids"] = ["C_UNION", "A_FLAT"]
    _reseal_d0_comparison(survivor_attack)
    route_order_attack = copy.deepcopy(result)
    route_order_attack["ordered_route_results"].reverse()
    route_order_attack["surviving_route_ids"] = ["C_UNION", "A_FLAT"]
    _reseal_d0_comparison(route_order_attack)

    for hostile in (survivor_attack, route_order_attack):
        with pytest.raises((TypeError, ValueError)):
            common.validate_d0_comparison_v1(
                hostile,
                corpus_fixture_raw_bytes=fixture_bytes,
                common_blob=common_blob,
                compare_blob=compare_blob,
                python_identity_observation={},
                python_probe_result={},
                ordered_route_inputs=route_inputs,
            )


def test_d0_comparison_rejects_fixture_body_and_manifest_root_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common()
    _patch_corpus_fixture_validation(monkeypatch, [])
    _patch_d0_route_dependencies(monkeypatch)
    fixture = _comparison_fixture()
    fixture_bytes = common.canonical_json_bytes_v1(fixture)
    common_blob, compare_blob, route_inputs = _comparison_inputs()
    result = common.build_d0_comparison_v1(
        corpus_fixture_raw_bytes=fixture_bytes,
        common_blob=common_blob,
        compare_blob=compare_blob,
        python_identity_observation={},
        python_probe_result={},
        ordered_route_inputs=route_inputs,
        auxiliary_benchmark=_auxiliary_benchmark(),
    )
    substituted_fixture = copy.deepcopy(fixture)
    substituted_fixture["metric_spec"]["metric_spec_sha"] = "f" * 64
    _seal(substituted_fixture, "fixture_sha")
    manifest_attack_inputs = copy.deepcopy(route_inputs)
    manifest_attack_inputs[1]["route_manifest"]["corpus_spec_sha"] = "f" * 64
    _seal(manifest_attack_inputs[1]["route_manifest"], "route_manifest_sha")

    for changed_fixture_bytes, changed_route_inputs in (
        (
            common.canonical_json_bytes_v1(substituted_fixture),
            route_inputs,
        ),
        (fixture_bytes, manifest_attack_inputs),
    ):
        with pytest.raises((TypeError, ValueError)):
            common.validate_d0_comparison_v1(
                result,
                corpus_fixture_raw_bytes=changed_fixture_bytes,
                common_blob=common_blob,
                compare_blob=compare_blob,
                python_identity_observation={},
                python_probe_result={},
                ordered_route_inputs=changed_route_inputs,
            )


@pytest.mark.parametrize(
    "mutator",
    (
        lambda benchmark: benchmark.update(unknown=None),
        lambda benchmark: benchmark.__setitem__("warm_up", benchmark.pop("warm_up")),
        lambda benchmark: benchmark.__setitem__("warm_up", 5.0),
        lambda benchmark: benchmark.__setitem__(
            "reported_statistics",
            ["p95", "median", "tracemalloc_peak"],
        ),
        lambda benchmark: benchmark["ordered_route_statistics"].reverse(),
        lambda benchmark: benchmark["ordered_route_statistics"][0].update(median=1),
        lambda benchmark: benchmark["ordered_route_statistics"][0].update(
            tracemalloc_peak=1.0
        ),
    ),
)
def test_d0_comparison_rejects_auxiliary_benchmark_protocol_drift(
    monkeypatch: pytest.MonkeyPatch,
    mutator,
) -> None:
    common = _common()
    _patch_corpus_fixture_validation(monkeypatch, [])
    _patch_d0_route_dependencies(monkeypatch)
    common_blob, compare_blob, route_inputs = _comparison_inputs()
    benchmark = _auxiliary_benchmark()
    mutator(benchmark)

    with pytest.raises((TypeError, ValueError)):
        common.build_d0_comparison_v1(
            corpus_fixture_raw_bytes=common.canonical_json_bytes_v1(
                _comparison_fixture()
            ),
            common_blob=common_blob,
            compare_blob=compare_blob,
            python_identity_observation={},
            python_probe_result={},
            ordered_route_inputs=route_inputs,
            auxiliary_benchmark=benchmark,
        )
