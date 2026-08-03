"""Frozen comparison and reviewer-process machinery for the B7 schema lab."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import experiments.v3m0_b7_schema_lab.common as _common


REVIEWER_PROCESS_TIMEOUT_SECONDS_V1 = 1800
REVIEWER_PROCESS_STDOUT_HARD_CAP_BYTES_V1 = 1048576
REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1 = 1048576
REVIEWER_PROCESS_IO_CHUNK_BYTES_V1 = 65536
REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1 = 5
REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1 = 5
REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1 = 5
D1_CAPTURE_PROCESS_STDOUT_HARD_CAP_BYTES_V1 = 8 * 1024 * 1024
_SANITIZED_REVIEWER_ENVIRONMENT_V1 = (
    ("PYTHONHASHSEED", "0"),
    ("PYTHONNOUSERSITE", "1"),
    ("PYTHONDONTWRITEBYTECODE", "1"),
    ("PYTHONUTF8", "1"),
    ("OPENBLAS_NUM_THREADS", "1"),
    ("OMP_NUM_THREADS", "1"),
    ("MKL_NUM_THREADS", "1"),
    ("VECLIB_MAXIMUM_THREADS", "1"),
    ("NUMEXPR_NUM_THREADS", "1"),
    ("LANG", "C"),
    ("LC_ALL", "C"),
)
_REVIEWER_SUBCOMMANDS_V1 = (
    ("CORPUS_REPLAY", "review-corpus"),
    ("METRIC_REPLAY", "review-metric"),
)
_REVIEWER_PROTOCOLS_V1 = (
    ("CORPUS_REPLAY", "v3m0-b7-corpus-replay-v1"),
    ("METRIC_REPLAY", "v3m0-b7-metric-replay-v1"),
)
_REVIEWER_PROTOCOLS_V2 = (
    ("CORPUS_REPLAY", "v3m0-b7-corpus-replay-v2"),
    ("METRIC_REPLAY", "v3m0-b7-metric-replay-v2"),
)
_REPLAY_REPORT_OUTPUT_PROJECTION_FIELDS_V1 = (
    "replay_report_schema_version",
    "reviewer_role",
    "review_protocol_id",
    "lab_evidence_commit_sha",
    "replay_input_root_sha",
    "recomputed_d0_decision_payload_sha",
    "recomputed_d1_decision_payload_sha",
    "observed_surviving_route_ids",
    "observed_provisional_winner_route_id",
)
_PYTHON_EXECUTABLE_HASH_CHUNK_BYTES_V1 = 1048576
_PYTHON_INVOCATION_MAX_SYMLINK_HOPS_V2 = 40
_PYTHON_ENVIRONMENT_PROBE_TIMEOUT_SECONDS_V2 = 30
_PYTHON_ENVIRONMENT_PROBE_STDOUT_HARD_CAP_BYTES_V2 = 262144
_PYTHON_ENVIRONMENT_PROBE_STDERR_HARD_CAP_BYTES_V2 = 262144
_PYTHON_ENVIRONMENT_IMPORT_PROBE_UTF8_V2 = (
    "import json,os,platform,sys;import numpy as np;import scipy;"
    "from threadpoolctl import threadpool_info;"
    "payload={'python_implementation':platform.python_implementation(),"
    "'python_version':platform.python_version(),"
    "'python_invocation_path':os.path.normpath(os.path.abspath(sys.executable)),"
    "'python_executable_realpath':os.path.realpath(sys.executable),"
    "'python_venv_prefix':os.path.normpath(os.path.abspath(sys.prefix)),"
    "'numpy_version':str(np.__version__),'scipy_version':str(scipy.__version__),"
    "'platform_system':platform.system(),'platform_release':platform.release(),"
    "'platform_machine':platform.machine(),"
    "'numpy_float64_dtype_str':np.dtype(np.float64).str,"
    "'numpy_float64_itemsize':np.dtype(np.float64).itemsize,"
    "'byteorder':sys.byteorder,'threadpool_info':threadpool_info()};"
    "sys.stdout.buffer.write(json.dumps(payload,allow_nan=False,ensure_ascii=False,"
    "sort_keys=True,separators=(',',':')).encode('utf-8')+b'\\n')"
)
_PYTHON_ENVIRONMENT_PROBE_FIELDS_V2 = (
    "byteorder",
    "numpy_float64_dtype_str",
    "numpy_float64_itemsize",
    "numpy_version",
    "platform_machine",
    "platform_release",
    "platform_system",
    "python_executable_realpath",
    "python_implementation",
    "python_invocation_path",
    "python_venv_prefix",
    "python_version",
    "scipy_version",
    "threadpool_info",
)
_REVIEWER_INPUT_PATHS_V1 = (
    (
        "d0",
        "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json",
    ),
    (
        "d1",
        "data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json",
    ),
    ("registry_base", "docsv3/v3-机器合同-B7-v9.1-registry.json"),
    ("registry_overlay", "docsv3/v3-机器合同-B7-v9.2-overlay.json"),
    ("registry_overlay_v921", "docsv3/v3-机器合同-B7-v9.2.1-overlay.json"),
    ("common", "experiments/v3m0_b7_schema_lab/common.py"),
    ("compare", "experiments/v3m0_b7_schema_lab/compare.py"),
    ("corpus", "tests/fixtures/v3m0_b7_schema_lab_corpus.json"),
)
_REVIEWER_CONTRACT_INPUTS_V1 = (
    (
        "registry_base",
        "222cd47e95de63eaedee41f6ca4b207a0eccceb7a77089aed43a480a77f69d72",
        "experimental.v3m0.b7.v9.1-machine-contract-registry.v1",
    ),
    (
        "registry_overlay",
        "b7a0d0a1a319ccb4ee56804a8e994bcf3bb90b138284f14841c87be594705b5f",
        "experimental.v3m0.b7.v9.2-machine-contract-overlay.v1",
    ),
    (
        "registry_overlay_v921",
        "1231ee2e6c1b6f2eef86d1906990cb425128a643f4981b3552541d2ec0c689b6",
        "experimental.v3m0.b7.v9.2.1-machine-contract-overlay.v1",
    ),
)
_TRUSTED_GIT_EXECUTABLE_V1 = "/usr/bin/git"
_TRUSTED_GIT_GLOBAL_ARGV_V1 = (
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
_SANITIZED_GIT_ENVIRONMENT_V1 = (
    ("GIT_NO_REPLACE_OBJECTS", "1"),
    ("GIT_CONFIG_NOSYSTEM", "1"),
    ("GIT_CONFIG_GLOBAL", "/dev/null"),
    ("GIT_ALTERNATE_OBJECT_DIRECTORIES", ""),
    ("LANG", "C"),
    ("LC_ALL", "C"),
)
_REVIEWER_EXPORT_INCLUDED_PATHS_V1 = (
    "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json",
    "data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json",
    "docsv3/v3-机器合同-B7-v9.1-registry.json",
    "docsv3/v3-机器合同-B7-v9.2-overlay.json",
    "docsv3/v3-机器合同-B7-v9.2.1-overlay.json",
    "experiments/v3m0_b7_schema_lab",
    "rulespace_v3",
    "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
)
_REVIEWER_REQUIRED_INPUT_PATHS_V1 = (
    ("d0", _REVIEWER_EXPORT_INCLUDED_PATHS_V1[0]),
    ("d1", _REVIEWER_EXPORT_INCLUDED_PATHS_V1[1]),
    ("registry_base", _REVIEWER_EXPORT_INCLUDED_PATHS_V1[2]),
    ("registry_overlay", _REVIEWER_EXPORT_INCLUDED_PATHS_V1[3]),
    ("registry_overlay_v921", _REVIEWER_EXPORT_INCLUDED_PATHS_V1[4]),
    ("corpus", _REVIEWER_EXPORT_INCLUDED_PATHS_V1[7]),
)
_OWNED_REVIEWER_EXPORT_ROOTS_V1 = {}
_REPLAY_INPUT_PROJECTION_FIELDS_V1 = (
    "reviewer_role",
    "review_protocol_id",
    "reviewed_lab_evidence_commit_sha",
    "review_environment_manifest_sha",
    "reviewed_d0_result_raw_sha256",
    "reviewed_d0_result_sha",
    "reviewed_d0_decision_payload_sha",
    "reviewed_d1_result_raw_sha256",
    "reviewed_d1_result_sha",
    "reviewed_d1_decision_payload_sha",
    "reviewed_common_commit_sha",
    "reviewed_route_commit_shas",
    "reviewed_corpus_spec_sha",
    "reviewed_mutation_universe_sha",
    "reviewed_metric_spec_sha",
    "reviewed_compare_source_sha256",
    "reviewed_executable_source_closure_sha",
    "replay_source_sha256",
)
_D0_COMPARISON_FIELDS_V1 = (
    "d0_result_schema_version",
    "common_commit_sha",
    "common_source_sha256",
    "compare_source_sha256",
    "corpus_fixture_raw_sha256",
    "corpus_spec_sha",
    "mutation_universe_sha",
    "metric_spec_sha",
    "environment_manifest",
    "ordered_route_results",
    "surviving_route_ids",
    "decision_payload_sha",
    "auxiliary_benchmark",
    "d0_result_sha",
)
_D1_COMPARISON_FIELDS_V1 = (
    "d1_result_schema_version",
    "d0_result_raw_sha256",
    "d0_result_sha",
    "d0_decision_payload_sha",
    "common_commit_sha",
    "common_source_sha256",
    "compare_source_sha256",
    "leaf_provider_source_sha256",
    "corpus_fixture_raw_sha256",
    "corpus_spec_sha",
    "mutation_universe_sha",
    "metric_spec_sha",
    "synthetic_graph_manifest",
    "environment_manifest",
    "ordered_capture_transcript_set_shas",
    "ordered_capture_leaf_digest_set_shas",
    "ordered_route_results",
    "surviving_route_ids",
    "minimum_metric_vector",
    "provisional_winner_route_id",
    "tie_detected",
    "decision_payload_sha",
    "auxiliary_benchmark",
    "d1_result_sha",
)
_D1_DECISION_FIELDS_V1 = (
    _D1_COMPARISON_FIELDS_V1[0],
    *_D1_COMPARISON_FIELDS_V1[3:21],
)
_REPLAY_REPORT_FIELDS_V1 = (
    *_REPLAY_REPORT_OUTPUT_PROJECTION_FIELDS_V1,
    "replay_output_root_sha",
    "replay_report_sha",
)


def _canonical_json_bytes_v1(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_sha_v1(value):
    return hashlib.sha256(_canonical_json_bytes_v1(value)).hexdigest()


def _strict_json_loads_v1(raw_bytes):
    def reject_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("reviewer JSON has a duplicate object key")
            result[key] = value
        return result

    def reject_constant(_constant):
        raise ValueError("reviewer JSON contains a non-finite number")

    if type(raw_bytes) is not bytes or raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError("reviewer JSON must be strict UTF-8 without BOM")
    return json.loads(
        raw_bytes.decode("utf-8"),
        object_pairs_hook=reject_pairs,
        parse_constant=reject_constant,
    )


def _require_exact_object_fields_v1(raw_body, fields, field):
    if (
        type(raw_body) is not dict
        or len(raw_body) != len(fields)
        or any(name not in raw_body for name in fields)
    ):
        raise ValueError(f"reviewer {field} fields drifted")
    return raw_body

_D0_CAPTURE_ROUTE_ORDER_V1 = ("A_FLAT", "B_PROGRESS", "C_UNION")
_D1_CAPTURE_CHILD_PROGRAM_UTF8_V1 = (
    "import sys;"
    "from experiments.v3m0_b7_schema_lab import common;"
    "raw=open(sys.argv[1],'rb').read();"
    "payload=raw[:-1] if raw.endswith(b'\\n') and b'\\n' not in raw[:-1] else (_ for _ in ()).throw(ValueError('fixture framing drifted'));"
    "fixture=common.strict_json_loads_v1(payload);"
    "common.canonical_json_bytes_v1(fixture)==payload or (_ for _ in ()).throw(ValueError('fixture is not canonical'));"
    "ordinal=int(sys.argv[2]);"
    "str(ordinal)==sys.argv[2] or (_ for _ in ()).throw(ValueError('capture ordinal drifted'));"
    "transcripts=common.capture_d1_transcript_set_v1(capture_ordinal=ordinal,validated_corpus_fixture=fixture);"
    "out=common.canonical_json_bytes_v1({'capture_ordinal':ordinal,'ordered_transcripts':transcripts})+b'\\n';"
    "sys.stdout.buffer.write(out)"
)


def _returned_route_call_v1(result):
    if type(result) is bytes:
        return {"termination_kind": "RETURNED_BYTES", "raw_bytes": result}
    return {"termination_kind": "RETURNED_NONBYTES", "raw_bytes": None}


def _rejected_route_call_v1():
    return {"termination_kind": "B7LabMutationRejected", "raw_bytes": None}


def _wrong_exception_route_call_v1():
    return {"termination_kind": "WRONG_EXCEPTION", "raw_bytes": None}


def _not_called_route_call_v1():
    return {"termination_kind": "NOT_CALLED", "raw_bytes": None}


def _call_a_flat_encode_v1(raw_bytes):
    from .a_flat import encode_normalized_transcript as route_call

    try:
        result = route_call(raw_bytes)
    except _common.B7LabMutationRejected:
        return _rejected_route_call_v1()
    except Exception:
        return _wrong_exception_route_call_v1()
    return _returned_route_call_v1(result)


def _call_a_flat_decode_v1(raw_bytes):
    from .a_flat import verify_and_decode_route_wire as route_call

    try:
        result = route_call(raw_bytes)
    except _common.B7LabMutationRejected:
        return _rejected_route_call_v1()
    except Exception:
        return _wrong_exception_route_call_v1()
    return _returned_route_call_v1(result)


def _call_b_progress_encode_v1(raw_bytes):
    from .b_progress import encode_normalized_transcript as route_call

    try:
        result = route_call(raw_bytes)
    except _common.B7LabMutationRejected:
        return _rejected_route_call_v1()
    except Exception:
        return _wrong_exception_route_call_v1()
    return _returned_route_call_v1(result)


def _call_b_progress_decode_v1(raw_bytes):
    from .b_progress import verify_and_decode_route_wire as route_call

    try:
        result = route_call(raw_bytes)
    except _common.B7LabMutationRejected:
        return _rejected_route_call_v1()
    except Exception:
        return _wrong_exception_route_call_v1()
    return _returned_route_call_v1(result)


def _call_c_union_encode_v1(raw_bytes):
    from .c_union import encode_normalized_transcript as route_call

    try:
        result = route_call(raw_bytes)
    except _common.B7LabMutationRejected:
        return _rejected_route_call_v1()
    except Exception:
        return _wrong_exception_route_call_v1()
    return _returned_route_call_v1(result)


def _call_c_union_decode_v1(raw_bytes):
    from .c_union import verify_and_decode_route_wire as route_call

    try:
        result = route_call(raw_bytes)
    except _common.B7LabMutationRejected:
        return _rejected_route_call_v1()
    except Exception:
        return _wrong_exception_route_call_v1()
    return _returned_route_call_v1(result)


def _call_d0_route_encode_v1(route_id, raw_bytes):
    if route_id == "A_FLAT":
        return _call_a_flat_encode_v1(raw_bytes)
    if route_id == "B_PROGRESS":
        return _call_b_progress_encode_v1(raw_bytes)
    if route_id == "C_UNION":
        return _call_c_union_encode_v1(raw_bytes)
    raise ValueError("D0 capture route is not frozen")


def _call_d0_route_decode_v1(route_id, raw_bytes):
    if route_id == "A_FLAT":
        return _call_a_flat_decode_v1(raw_bytes)
    if route_id == "B_PROGRESS":
        return _call_b_progress_decode_v1(raw_bytes)
    if route_id == "C_UNION":
        return _call_c_union_decode_v1(raw_bytes)
    raise ValueError("D0 capture route is not frozen")


def _call_d0_route_pipeline_v1(route_id, source_bytes):
    encode = _call_d0_route_encode_v1(route_id, source_bytes)
    if encode["termination_kind"] != "RETURNED_BYTES":
        return encode, _not_called_route_call_v1()
    return encode, _call_d0_route_decode_v1(route_id, encode["raw_bytes"])


def _prepare_d0_capture_domain_v1(validated_corpus_fixture):
    fixture, source_sets = _common._validated_d0_fixture_source_domain_v1(
        validated_corpus_fixture
    )
    if type(source_sets) is not list or len(source_sets) != 1:
        raise ValueError("D0 capture requires exactly one source transcript set")
    source_set = _common.strict_json_loads_v1(
        _common.canonical_json_bytes_v1(source_sets[0])
    )
    universe = fixture.get("mutation_universe")
    if type(universe) is not dict:
        raise TypeError("D0 capture mutation universe must be an exact dict")
    raw_mutations = universe.get("ordered_mutations")
    mutation_count = universe.get("mutation_count")
    if type(raw_mutations) is not list or type(mutation_count) is not int:
        raise TypeError("D0 capture mutation universe domain is not exact")
    mutations = [_common.validate_mutation_v1(raw) for raw in raw_mutations]
    expected_mutations = _common.generate_ordered_mutations_v1(source_set)
    if (
        mutation_count != len(mutations)
        or mutation_count != len(expected_mutations)
        or _common.canonical_json_bytes_v1(mutations)
        != _common.canonical_json_bytes_v1(expected_mutations)
        or [mutation["mutation_ordinal"] for mutation in mutations]
        != list(range(mutation_count))
    ):
        raise ValueError("D0 capture mutation universe differs from source domain")
    sources_by_case = {source["case_id"]: source for source in source_set}
    if len(sources_by_case) != 7 or "success" not in sources_by_case:
        raise ValueError("D0 capture source case domain drifted")
    success = sources_by_case["success"]
    snapshots = {
        case_id: _common.discover_record_self_hashes_v1(source)
        for case_id, source in sources_by_case.items()
    }
    success_snapshot = snapshots["success"]
    effective_snapshots = {
        case_id: snapshot
        + tuple(item for item in success_snapshot if item not in snapshot)
        for case_id, snapshot in snapshots.items()
    }
    return {
        "source_set": source_set,
        "sources_by_case": sources_by_case,
        "success": success,
        "effective_snapshots": effective_snapshots,
        "mutations": mutations,
    }


def _capture_d0_legal_replays_v1(route_id, domain):
    observations = []
    for source in domain["source_set"]:
        source_bytes = _common.canonical_json_bytes_v1(source)
        encode, decode = _call_d0_route_pipeline_v1(route_id, source_bytes)
        observations.append(
            {
                "capture_ordinal": 0,
                "case_id": source["case_id"],
                "route_id": route_id,
                "source_transcript_bytes": source_bytes,
                "encode_result": encode,
                "decode_result": decode,
            }
        )
    return observations


def _capture_d0_mutation_probes_v1(route_id, domain):
    for mutation in domain["mutations"]:
        probe_kind = mutation["probe_kind"]
        not_called = _not_called_route_call_v1
        if probe_kind == "UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT":
            materialized_bytes = None
            upstream_transcript_count = 0
            first_encode = not_called()
            first_decode = not_called()
            second_encode = not_called()
            second_decode = not_called()
        else:
            base_case_id = mutation["base_case_id"]
            if base_case_id not in domain["sources_by_case"]:
                raise ValueError("D0 mutation base case is outside the corpus")
            base = domain["sources_by_case"][base_case_id]
            if probe_kind in ("ROUNDTRIP_MUST_EQUAL", "REPEAT_MUST_EQUAL"):
                materialized = base
            else:
                materialized = _common._apply_validated_transcript_mutation_v1(
                    base,
                    mutation,
                    domain["success"],
                    domain["effective_snapshots"][base_case_id],
                )
            materialized_bytes = _common.canonical_json_bytes_v1(materialized)
            upstream_transcript_count = 1
            first_encode, first_decode = _call_d0_route_pipeline_v1(
                route_id,
                materialized_bytes,
            )
            if probe_kind == "REPEAT_MUST_EQUAL":
                second_encode, second_decode = _call_d0_route_pipeline_v1(
                    route_id,
                    materialized_bytes,
                )
            else:
                second_encode = not_called()
                second_decode = not_called()
        yield {
            "capture_ordinal": 0,
            "mutation_ordinal": mutation["mutation_ordinal"],
            "mutation_id": mutation["mutation_id"],
            "mutation_sha": mutation["mutation_sha"],
            "route_id": route_id,
            "materialized_transcript_bytes": materialized_bytes,
            "upstream_transcript_count": upstream_transcript_count,
            "first_encode_result": first_encode,
            "first_decode_result": first_decode,
            "second_encode_result": second_encode,
            "second_decode_result": second_decode,
        }


def _capture_d0_invalid_presence_probes_v1(route_id, domain):
    candidate_count = 0
    candidates = _common.iter_constructible_invalid_presence_candidates_v1(
        domain["success"]
    )
    if iter(candidates) is not candidates:
        raise TypeError("D0 invalid-presence producer must be one-shot")
    for candidate in candidates:
        if candidate_count >= 1393:
            raise ValueError("D0 invalid-presence domain cardinality drifted")
        candidate_count += 1
        candidate_bytes = _common.canonical_json_bytes_v1(candidate["transcript"])
        yield {
            "capture_ordinal": 0,
            "terminal_tag": candidate["terminal_tag"],
            "bit_integer": candidate["bit_integer"],
            "presence_bits": candidate["presence_bits"],
            "route_id": route_id,
            "candidate_transcript_bytes": candidate_bytes,
            "encode_result": _call_d0_route_encode_v1(
                route_id,
                candidate_bytes,
            ),
        }
    if candidate_count != 1393:
        raise ValueError("D0 invalid-presence domain cardinality drifted")


def _capture_d0_route_gate_inputs_v1(route_id, domain):
    if route_id not in _D0_CAPTURE_ROUTE_ORDER_V1:
        raise ValueError("D0 capture route is not frozen")
    return {
        "ordered_legal_replays": _capture_d0_legal_replays_v1(route_id, domain),
        "ordered_mutation_probes": _capture_d0_mutation_probes_v1(
            route_id,
            domain,
        ),
        "ordered_invalid_presence_probes": (
            _capture_d0_invalid_presence_probes_v1(route_id, domain)
        ),
    }


def iter_d0_gate_inputs_v1(*, validated_corpus_fixture):
    """Yield the three D0 route gate-input domains in frozen route order."""

    domain = _prepare_d0_capture_domain_v1(validated_corpus_fixture)
    yield "A_FLAT", _capture_d0_route_gate_inputs_v1("A_FLAT", domain)
    yield "B_PROGRESS", _capture_d0_route_gate_inputs_v1("B_PROGRESS", domain)
    yield "C_UNION", _capture_d0_route_gate_inputs_v1("C_UNION", domain)


def _validate_d1_survivor_route_order_v1(ordered_survivor_route_ids):
    if (
        type(ordered_survivor_route_ids) is not list
        or not ordered_survivor_route_ids
        or any(type(route_id) is not str for route_id in ordered_survivor_route_ids)
        or len(set(ordered_survivor_route_ids)) != len(ordered_survivor_route_ids)
    ):
        raise TypeError("D1 capture survivor domain must be a nonempty unique list")
    expected = [
        route_id
        for route_id in _D0_CAPTURE_ROUTE_ORDER_V1
        if route_id in ordered_survivor_route_ids
    ]
    if expected != ordered_survivor_route_ids:
        raise ValueError("D1 capture survivor order is not the frozen D0 order")
    return list(ordered_survivor_route_ids)


def _prepare_d1_capture_domain_v1(
    validated_corpus_fixture,
    ordered_capture_source_bytes,
):
    captures = _common._validate_d1_capture_source_bytes_v1(
        ordered_capture_source_bytes
    )
    supplied_source_sets = [capture["transcripts"] for capture in captures]
    fixture, source_sets = _common._validated_gate_fixture_source_domain_v1(
        "D1",
        validated_corpus_fixture,
        supplied_source_sets,
    )
    if _common.canonical_json_bytes_v1(source_sets) != _common.canonical_json_bytes_v1(
        supplied_source_sets
    ):
        raise ValueError("D1 capture source bodies changed during fixture validation")
    graph = _common.validate_synthetic_graph_manifest_v1(
        fixture["synthetic_graph_manifest"]
    )
    if graph.get("selected_fejer_order") != 256 or _common.canonical_json_bytes_v1(
        graph
    ) != _common.canonical_json_bytes_v1(fixture["synthetic_graph_manifest"]):
        raise ValueError("D1 capture graph is not the exact fixture T=256 graph")
    corpus_spec_sha = fixture["corpus_spec"]["corpus_spec_sha"]
    environment_sha = fixture["environment_manifest"]["environment_sha"]
    for source_set in source_sets:
        for source in source_set:
            validated = (
                _common._validate_normalized_transcript_against_validated_graph_v1(
                    source,
                    corpus_spec_sha=corpus_spec_sha,
                    environment_manifest_sha=environment_sha,
                    validated_graph=graph,
                )
            )
            if _common.canonical_json_bytes_v1(
                validated
            ) != _common.canonical_json_bytes_v1(source):
                raise ValueError("D1 capture lineage validator substituted a source")

    _d0_fixture, d0_source_sets = _common._validated_d0_fixture_source_domain_v1(
        validated_corpus_fixture
    )
    if type(d0_source_sets) is not list or len(d0_source_sets) != 1:
        raise ValueError("D1 capture mutation universe has no unique D0 source")
    universe = fixture.get("mutation_universe")
    if type(universe) is not dict:
        raise TypeError("D1 capture mutation universe must be an exact dict")
    raw_mutations = universe.get("ordered_mutations")
    mutation_count = universe.get("mutation_count")
    if type(raw_mutations) is not list or type(mutation_count) is not int:
        raise TypeError("D1 capture mutation universe domain is not exact")
    mutations = [_common.validate_mutation_v1(raw) for raw in raw_mutations]
    expected_mutations = _common.generate_ordered_mutations_v1(d0_source_sets[0])
    if (
        mutation_count != len(mutations)
        or mutation_count != len(expected_mutations)
        or _common.canonical_json_bytes_v1(mutations)
        != _common.canonical_json_bytes_v1(expected_mutations)
        or [mutation["mutation_ordinal"] for mutation in mutations]
        != list(range(mutation_count))
    ):
        raise ValueError("D1 capture mutation universe differs from its D0 freeze")

    capture_domains = []
    for capture, source_set in zip(captures, source_sets):
        sources_by_case = {source["case_id"]: source for source in source_set}
        if len(sources_by_case) != 7 or "success" not in sources_by_case:
            raise ValueError("D1 capture source case domain drifted")
        source_bytes = [
            _common.canonical_json_bytes_v1(source) for source in source_set
        ]
        if source_bytes != capture["source_bytes"]:
            raise ValueError("D1 capture canonical source bytes drifted")
        capture_domains.append(
            {
                "capture_ordinal": capture["capture_ordinal"],
                "source_set": source_set,
                "source_bytes": source_bytes,
                "sources_by_case": sources_by_case,
                "success": sources_by_case["success"],
                "snapshots": {
                    case_id: _common.discover_record_self_hashes_v1(source)
                    for case_id, source in sources_by_case.items()
                },
            }
        )
    return {"captures": capture_domains, "mutations": mutations}


def _capture_d1_legal_replays_v1(route_id, domain):
    observations = []
    for capture in domain["captures"]:
        for source, source_bytes in zip(
            capture["source_set"],
            capture["source_bytes"],
        ):
            encode, decode = _call_d0_route_pipeline_v1(route_id, source_bytes)
            observations.append(
                {
                    "capture_ordinal": capture["capture_ordinal"],
                    "case_id": source["case_id"],
                    "route_id": route_id,
                    "source_transcript_bytes": source_bytes,
                    "encode_result": encode,
                    "decode_result": decode,
                }
            )
    if len(observations) != 21:
        raise ValueError("D1 legal replay capture cardinality drifted")
    return observations


def _capture_d1_mutation_probes_v1(route_id, domain):
    for capture in domain["captures"]:
        for mutation in domain["mutations"]:
            probe_kind = mutation["probe_kind"]
            not_called = _not_called_route_call_v1
            if probe_kind == "UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT":
                materialized_bytes = None
                upstream_transcript_count = 0
                first_encode = not_called()
                first_decode = not_called()
                second_encode = not_called()
                second_decode = not_called()
            else:
                base_case_id = mutation["base_case_id"]
                if base_case_id not in capture["sources_by_case"]:
                    raise ValueError("D1 mutation base case is outside the capture")
                base = capture["sources_by_case"][base_case_id]
                if probe_kind in ("ROUNDTRIP_MUST_EQUAL", "REPEAT_MUST_EQUAL"):
                    materialized = base
                else:
                    materialized = _common.apply_transcript_mutation_v1(
                        base,
                        mutation,
                        capture["success"],
                        capture["snapshots"][base_case_id],
                    )
                materialized_bytes = _common.canonical_json_bytes_v1(materialized)
                upstream_transcript_count = 1
                first_encode, first_decode = _call_d0_route_pipeline_v1(
                    route_id,
                    materialized_bytes,
                )
                if probe_kind == "REPEAT_MUST_EQUAL":
                    second_encode, second_decode = _call_d0_route_pipeline_v1(
                        route_id,
                        materialized_bytes,
                    )
                else:
                    second_encode = not_called()
                    second_decode = not_called()
            yield {
                "capture_ordinal": capture["capture_ordinal"],
                "mutation_ordinal": mutation["mutation_ordinal"],
                "mutation_id": mutation["mutation_id"],
                "mutation_sha": mutation["mutation_sha"],
                "route_id": route_id,
                "materialized_transcript_bytes": materialized_bytes,
                "upstream_transcript_count": upstream_transcript_count,
                "first_encode_result": first_encode,
                "first_decode_result": first_decode,
                "second_encode_result": second_encode,
                "second_decode_result": second_decode,
            }


def _capture_d1_invalid_presence_probes_v1(route_id, domain):
    for capture in domain["captures"]:
        candidate_count = 0
        candidates = _common.iter_constructible_invalid_presence_candidates_v1(
            capture["success"]
        )
        if iter(candidates) is not candidates:
            raise TypeError("D1 invalid-presence producer must be one-shot")
        for candidate in candidates:
            if candidate_count >= 1393:
                raise ValueError("D1 invalid-presence capture cardinality drifted")
            candidate_count += 1
            candidate_bytes = _common.canonical_json_bytes_v1(candidate["transcript"])
            yield {
                "capture_ordinal": capture["capture_ordinal"],
                "terminal_tag": candidate["terminal_tag"],
                "bit_integer": candidate["bit_integer"],
                "presence_bits": candidate["presence_bits"],
                "route_id": route_id,
                "candidate_transcript_bytes": candidate_bytes,
                "encode_result": _call_d0_route_encode_v1(
                    route_id,
                    candidate_bytes,
                ),
            }
        if candidate_count != 1393:
            raise ValueError("D1 invalid-presence capture cardinality drifted")


def _capture_d1_route_gate_inputs_v1(route_id, domain):
    return {
        "ordered_legal_replays": _capture_d1_legal_replays_v1(route_id, domain),
        "ordered_mutation_probes": _capture_d1_mutation_probes_v1(
            route_id,
            domain,
        ),
        "ordered_invalid_presence_probes": (
            _capture_d1_invalid_presence_probes_v1(route_id, domain)
        ),
    }


def iter_d1_gate_inputs_v1(
    *,
    validated_corpus_fixture,
    ordered_survivor_route_ids,
    ordered_capture_source_bytes,
):
    """Broadcast three fresh-harness capture sets to D0 survivors in order."""

    route_ids = _validate_d1_survivor_route_order_v1(ordered_survivor_route_ids)
    domain = _prepare_d1_capture_domain_v1(
        validated_corpus_fixture,
        ordered_capture_source_bytes,
    )
    for route_id in route_ids:
        yield route_id, _capture_d1_route_gate_inputs_v1(route_id, domain)


def build_d1_route_inputs_from_capture_v1(
    *,
    d0_comparison,
    ordered_d0_route_inputs,
    validated_corpus_fixture,
    ordered_capture_source_bytes,
):
    """Join D0 survivor manifests/blobs to their fresh D1 capture streams."""

    d0 = _common.validate_exact_lab_record_v1(
        "B7LabD0ComparisonV1",
        d0_comparison,
    )
    _common.validate_d0_decision_payload_projection_v1(d0)
    survivor_ids = _validate_d1_survivor_route_order_v1(d0["surviving_route_ids"])
    d0_inputs = _common._validate_d0_route_inputs_v1(
        ordered_d0_route_inputs,
        d0["common_commit_sha"],
    )
    input_by_route = {
        route_input["route_manifest"]["route_id"]: route_input
        for route_input in d0_inputs
    }
    result_by_route = {
        route_result["route_id"]: route_result
        for route_result in d0["ordered_route_results"]
    }
    captured = iter_d1_gate_inputs_v1(
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_survivor_route_ids=survivor_ids,
        ordered_capture_source_bytes=ordered_capture_source_bytes,
    )
    route_inputs = []
    for expected_route_id in survivor_ids:
        try:
            captured_route_id, gate_inputs = next(captured)
        except StopIteration:
            raise ValueError("D1 capture omitted a D0 survivor") from None
        if captured_route_id != expected_route_id:
            raise ValueError("D1 capture survivor order drifted")
        if (
            expected_route_id not in input_by_route
            or expected_route_id not in result_by_route
        ):
            raise ValueError("D1 capture survivor has no D0 route identity")
        d0_input = input_by_route[expected_route_id]
        d0_manifest = result_by_route[expected_route_id]["route_manifest"]
        if _common.canonical_json_bytes_v1(
            d0_input["route_manifest"]
        ) != _common.canonical_json_bytes_v1(d0_manifest):
            raise ValueError("D1 capture route manifest differs from D0")
        route_inputs.append(
            {
                "route_manifest": d0_manifest,
                "route_blob": d0_input["route_blob"],
                "production_blobs": d0_input["production_blobs"],
                "gate_inputs": gate_inputs,
            }
        )
    try:
        next(captured)
    except StopIteration:
        return route_inputs
    raise ValueError("D1 capture emitted a non-survivor route")


def _read_immutable_d1_capture_fixture_v1(
    export_root,
    fixture_path,
    validated_corpus_fixture,
):
    import os
    import stat

    root = _require_normalized_absolute_path_v2(export_root, "D1 export root")
    path = _require_normalized_absolute_path_v2(fixture_path, "D1 fixture path")
    try:
        if (
            os.path.realpath(root) != root
            or os.path.realpath(path) != path
            or os.path.commonpath((root, path)) != root
            or path == root
        ):
            raise ValueError("D1 fixture is not inside one resolved export root")
    except (OSError, ValueError):
        raise ValueError("D1 fixture export path identity drifted") from None

    descriptor = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        before = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o222:
            raise ValueError("D1 fixture must be an immutable regular file")
        remaining = before.st_size
        chunks = []
        while remaining:
            chunk = os.read(descriptor, min(1048576, remaining))
            if not chunk:
                raise ValueError("D1 fixture read ended before its frozen size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise ValueError("D1 fixture grew during its identity read")
        after = os.fstat(descriptor)
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if after_identity != before_identity:
            raise ValueError("D1 fixture identity changed during its read")
    except OSError:
        raise ValueError(
            "D1 fixture could not be read without following links"
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    raw_bytes = b"".join(chunks)
    expected = _common.canonical_json_bytes_v1(validated_corpus_fixture) + b"\n"
    if raw_bytes != expected:
        raise ValueError("D1 child fixture bytes differ from the validated fixture")
    return root, path


def _parse_d1_capture_child_stdout_v1(capture_ordinal, stdout_bytes):
    if type(stdout_bytes) is not bytes:
        raise TypeError("D1 capture child stdout must be exact bytes")
    if (
        not stdout_bytes.endswith(b"\n")
        or not stdout_bytes[:-1]
        or b"\n" in stdout_bytes[:-1]
    ):
        raise ValueError("D1 capture child stdout framing is not canonical")
    payload_bytes = stdout_bytes[:-1]
    payload = _common.strict_json_loads_v1(payload_bytes)
    if _common.canonical_json_bytes_v1(payload) != payload_bytes:
        raise ValueError("D1 capture child stdout is not canonical JSON")
    if type(payload) is not dict or tuple(payload) != (
        "capture_ordinal",
        "ordered_transcripts",
    ):
        raise ValueError("D1 capture child stdout fields drifted")
    if (
        type(payload["capture_ordinal"]) is not int
        or payload["capture_ordinal"] != capture_ordinal
    ):
        raise ValueError("D1 capture child ordinal differs from its process")
    transcripts = payload["ordered_transcripts"]
    if (
        type(transcripts) is not list
        or len(transcripts) != 7
        or any(type(transcript) is not dict for transcript in transcripts)
    ):
        raise TypeError("D1 capture child must emit exactly seven transcripts")
    return [_common.canonical_json_bytes_v1(transcript) for transcript in transcripts]


def run_d1_fresh_capture_processes_v1(
    *,
    python_invocation_path,
    export_root,
    fixture_path,
    validated_corpus_fixture,
    python_precheck_observation,
):
    """Run exactly three fresh common-harness children and return canonical bytes."""

    invocation = _require_normalized_absolute_path_v2(
        python_invocation_path,
        "D1 Python invocation",
    )
    if type(validated_corpus_fixture) is not dict:
        raise TypeError("D1 validated corpus fixture must be an exact dict")
    fixture_environment = validated_corpus_fixture.get("environment_manifest")
    if (
        type(fixture_environment) is not dict
        or fixture_environment.get("python_invocation_path") != invocation
    ):
        raise ValueError("D1 capture Python invocation differs from its fixture")
    root, path = _read_immutable_d1_capture_fixture_v1(
        export_root,
        fixture_path,
        validated_corpus_fixture,
    )
    environment = build_sanitized_reviewer_environment_v1()
    ordered_capture_source_bytes = []
    for capture_ordinal in (0, 1, 2):
        argv = (
            invocation,
            "-s",
            "-B",
            "-c",
            _D1_CAPTURE_CHILD_PROGRAM_UTF8_V1,
            path,
            str(capture_ordinal),
        )
        observation = run_bounded_reviewer_process_v1(
            argv=argv,
            cwd=root,
            environment=environment,
            timeout_seconds=REVIEWER_PROCESS_TIMEOUT_SECONDS_V1,
            stdout_hard_cap_bytes=D1_CAPTURE_PROCESS_STDOUT_HARD_CAP_BYTES_V1,
            stderr_hard_cap_bytes=REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1,
            io_chunk_bytes=REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
            term_grace_seconds=REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
            kill_grace_seconds=REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
            final_pipe_close_deadline_seconds=(
                REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1
            ),
            python_precheck_observation=python_precheck_observation,
        )
        if not (
            observation["replay_termination_kind"] == "EXITED"
            and observation["replay_exit_code"] == 0
            and observation["replay_signal_number"] is None
            and observation["replay_stderr_bytes"] == b""
            and observation["process_cleanup_deadline_exceeded"] is False
        ):
            raise ValueError(
                f"D1 fresh capture process {capture_ordinal} did not exit cleanly"
            )
        ordered_capture_source_bytes.append(
            _parse_d1_capture_child_stdout_v1(
                capture_ordinal,
                observation["replay_stdout_bytes"],
            )
        )
    _read_immutable_d1_capture_fixture_v1(
        export_root,
        fixture_path,
        validated_corpus_fixture,
    )
    _common._validate_d1_capture_source_bytes_v1(ordered_capture_source_bytes)
    _prepare_d1_capture_domain_v1(
        validated_corpus_fixture,
        ordered_capture_source_bytes,
    )
    return ordered_capture_source_bytes


def build_d1_route_inputs_from_fresh_processes_v1(
    *,
    d0_comparison,
    ordered_d0_route_inputs,
    python_invocation_path,
    export_root,
    fixture_path,
    validated_corpus_fixture,
    python_precheck_observation,
):
    """Capture first; only then expose completed transcript bytes to routes."""

    source_bytes = run_d1_fresh_capture_processes_v1(
        python_invocation_path=python_invocation_path,
        export_root=export_root,
        fixture_path=fixture_path,
        validated_corpus_fixture=validated_corpus_fixture,
        python_precheck_observation=python_precheck_observation,
    )
    return build_d1_route_inputs_from_capture_v1(
        d0_comparison=d0_comparison,
        ordered_d0_route_inputs=ordered_d0_route_inputs,
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_capture_source_bytes=source_bytes,
    )


def _require_lower_hex_v1(value, width, field):
    if (
        type(value) is not str
        or len(value) != width
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be exact lowercase hexadecimal width {width}")


def validate_replay_report_v1(raw_body):
    """Validate the exact replay-report roots and reviewer identity."""

    report = _require_exact_object_fields_v1(
        raw_body,
        _REPLAY_REPORT_FIELDS_V1,
        "replay report",
    )
    expected_protocol = _reviewer_protocol_id_v1(report["reviewer_role"])
    if report["review_protocol_id"] != expected_protocol:
        raise ValueError("replay report reviewer role/protocol mismatch")
    _require_lower_hex_v1(report["lab_evidence_commit_sha"], 40, "report evidence")
    for field in (
        "replay_input_root_sha",
        "recomputed_d0_decision_payload_sha",
        "recomputed_d1_decision_payload_sha",
        "replay_output_root_sha",
        "replay_report_sha",
    ):
        _require_lower_hex_v1(report[field], 64, field)
    if (
        type(report["observed_surviving_route_ids"]) is not list
        or report["observed_provisional_winner_route_id"]
        not in report["observed_surviving_route_ids"]
    ):
        raise ValueError("replay report winner is not a survivor")
    output_projection = {
        name: report[name] for name in _REPLAY_REPORT_OUTPUT_PROJECTION_FIELDS_V1
    }
    if report["replay_output_root_sha"] != _canonical_sha_v1(output_projection):
        raise ValueError("replay report output root mismatch")
    expected_report_sha = _canonical_sha_v1(
        {
            name: value
            for name, value in report.items()
            if name != "replay_report_sha"
        }
    )
    if report["replay_report_sha"] != expected_report_sha:
        raise ValueError("replay report self root mismatch")
    return report


def encode_replay_report_stdout_v1(raw_body):
    """Encode one validated report as canonical JSON plus exactly one LF."""

    report = validate_replay_report_v1(raw_body)
    return _canonical_json_bytes_v1(report) + b"\n"


def decode_replay_report_stdout_v1(stdout_bytes):
    """Strictly decode one canonical replay-report stdout frame."""

    if (
        type(stdout_bytes) is not bytes
        or not stdout_bytes.endswith(b"\n")
        or b"\n" in stdout_bytes[:-1]
    ):
        raise ValueError("replay report stdout must end in exactly one LF")
    payload = stdout_bytes[:-1]
    parsed = _strict_json_loads_v1(payload)
    if _canonical_json_bytes_v1(parsed) != payload:
        raise ValueError("replay report stdout JSON is not canonical")
    return validate_replay_report_v1(parsed)


def build_sanitized_reviewer_environment_v1():
    """Build the exact caller-independent reviewer child environment."""

    return {name: value for name, value in _SANITIZED_REVIEWER_ENVIRONMENT_V1}


def build_sanitized_git_environment_v1():
    """Build the exact caller-independent environment for trusted Git reads."""

    return {name: value for name, value in _SANITIZED_GIT_ENVIRONMENT_V1}


def _precheck_trusted_git_executable_v1():
    import os
    import stat

    observation = os.stat(_TRUSTED_GIT_EXECUTABLE_V1, follow_symlinks=False)
    if (
        not stat.S_ISREG(observation.st_mode)
        or observation.st_uid != 0
        or observation.st_mode & 0o022
        or not os.access(_TRUSTED_GIT_EXECUTABLE_V1, os.X_OK)
    ):
        raise ValueError("trusted Git executable identity or mode drifted")
    return (
        observation.st_dev,
        observation.st_ino,
        observation.st_mode,
        observation.st_uid,
    )


def _normalize_reviewer_repository_root_v1(repository_root):
    import os
    import stat

    if type(repository_root) is not str:
        raise TypeError("reviewer repository root must be an exact string")
    normalized = os.path.normpath(os.path.abspath(repository_root))
    if repository_root != normalized or normalized == "/":
        raise ValueError("reviewer repository root must be normalized absolute")
    observation = os.stat(normalized, follow_symlinks=False)
    if not stat.S_ISDIR(observation.st_mode):
        raise ValueError("reviewer repository root is not a directory")
    return normalized


def _trusted_git_argv_v1(*arguments):
    if any(type(argument) is not str for argument in arguments):
        raise TypeError("trusted Git arguments must be exact strings")
    return (
        _TRUSTED_GIT_EXECUTABLE_V1,
        *_TRUSTED_GIT_GLOBAL_ARGV_V1,
        *arguments,
    )


def _run_trusted_git_capture_v1(repository_root, *arguments):
    import subprocess

    completed = subprocess.run(
        _trusted_git_argv_v1(*arguments),
        cwd=repository_root,
        env=build_sanitized_git_environment_v1(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise ValueError("trusted Git object read failed closed")
    return completed.stdout


def _require_safe_reviewer_repo_path_v1(path, field):
    if (
        type(path) is not str
        or not path
        or path.startswith("/")
        or path.endswith("/")
        or pathlib.PurePosixPath(path).as_posix() != path
        or any(part in ("", ".", "..") for part in path.split("/"))
    ):
        raise ValueError(f"reviewer {field} path is not normalized relative")
    return path


def _parse_reviewer_ls_tree_v1(raw_bytes, evidence_commit_sha, included_paths):
    if type(raw_bytes) is not bytes or not raw_bytes.endswith(b"\0"):
        raise ValueError("trusted Git ls-tree frame is malformed")
    records = []
    observed_paths = set()
    matched = {path: False for path in included_paths}
    for frame in raw_bytes[:-1].split(b"\0"):
        metadata, separator, raw_path = frame.partition(b"\t")
        fields = metadata.split(b" ")
        if separator != b"\t" or len(fields) != 3:
            raise ValueError("trusted Git ls-tree record is malformed")
        try:
            mode, object_type, object_oid = (
                field.decode("ascii") for field in fields
            )
            path = raw_path.decode("utf-8")
        except UnicodeError as error:
            raise ValueError("trusted Git ls-tree encoding drifted") from error
        _require_safe_reviewer_repo_path_v1(path, "Git tree")
        if (
            mode not in ("100644", "100755")
            or object_type != "blob"
            or len(object_oid) != 40
            or any(character not in "0123456789abcdef" for character in object_oid)
        ):
            raise ValueError("trusted Git tree leaf mode, type, or OID drifted")
        if path in observed_paths:
            raise ValueError("trusted Git tree contains a duplicate path")
        owners = [
            selector
            for selector in included_paths
            if path == selector or path.startswith(selector + "/")
        ]
        if len(owners) != 1:
            raise ValueError("trusted Git tree path escapes or overlaps export scope")
        matched[owners[0]] = True
        observed_paths.add(path)
        records.append(
            (evidence_commit_sha, path, mode, object_type, object_oid)
        )
    if not records or not all(matched.values()):
        raise ValueError("trusted Git tree omits an included export path")
    if records != sorted(records, key=lambda record: record[1].encode("utf-8")):
        raise ValueError("trusted Git tree paths are not in raw-byte order")
    return tuple(records)


def read_immutable_git_tree_blobs_v1(
    *,
    repository_root,
    commit_sha,
    included_paths,
):
    """Read one scoped tree exclusively through sanitized literal trusted Git."""

    root = _normalize_reviewer_repository_root_v1(repository_root)
    _precheck_trusted_git_executable_v1()
    _require_lower_hex_v1(commit_sha, 40, "immutable Git commit")
    if type(included_paths) is not tuple or not included_paths:
        raise TypeError("immutable Git included paths must be a nonempty tuple")
    for ordinal, path in enumerate(included_paths):
        _require_safe_reviewer_repo_path_v1(path, f"included path {ordinal}")
    if len(set(included_paths)) != len(included_paths):
        raise ValueError("immutable Git included paths are duplicated")
    if _run_trusted_git_capture_v1(root, "cat-file", "-t", commit_sha) != b"commit\n":
        raise ValueError("immutable Git source object is not a commit")
    tree = _parse_reviewer_ls_tree_v1(
        _run_trusted_git_capture_v1(
            root,
            "ls-tree",
            "-r",
            "-z",
            commit_sha,
            "--",
            *included_paths,
        ),
        commit_sha,
        included_paths,
    )
    blobs = []
    for record in tree:
        raw_bytes = _run_trusted_git_capture_v1(
            root,
            "cat-file",
            "blob",
            record[4],
        )
        header = f"blob {len(raw_bytes)}\0".encode("ascii")
        if hashlib.sha1(header + raw_bytes).hexdigest() != record[4]:
            raise ValueError("immutable Git blob OID/body mismatch")
        blobs.append((*record, raw_bytes))
    return tuple(blobs)


def _expected_reviewer_export_directories_v1(expected_file_paths):
    directories = set()
    for path in expected_file_paths:
        parts = path.split("/")[:-1]
        for stop in range(1, len(parts) + 1):
            directories.add("/".join(parts[:stop]))
    return directories


def _validate_reviewer_tar_members_v1(members, *, expected_file_paths):
    if type(members) is not list or type(expected_file_paths) is not tuple:
        raise TypeError("reviewer tar observations must be exact containers")
    expected_files = set(expected_file_paths)
    expected_directories = _expected_reviewer_export_directories_v1(
        expected_file_paths
    )
    observed = set()
    observed_files = set()
    validated = []
    for member in members:
        if member.isdir():
            name = member.name[:-1] if member.name.endswith("/") else member.name
            member_kind = "directory"
        elif member.isreg():
            name = member.name
            member_kind = "file"
        else:
            raise ValueError("reviewer tar contains a non-regular entry")
        _require_safe_reviewer_repo_path_v1(name, "tar member")
        if name in observed:
            raise ValueError("reviewer tar contains a duplicate path")
        observed.add(name)
        if member_kind == "file":
            if name not in expected_files:
                raise ValueError("reviewer tar contains an unexpected file")
            observed_files.add(name)
        elif name not in expected_directories:
            raise ValueError("reviewer tar contains an unexpected directory")
        validated.append(member)
    if observed_files != expected_files:
        raise ValueError("reviewer tar omits an immutable Git leaf")
    return validated


def _run_trusted_git_archive_v1(
    repository_root,
    evidence_commit_sha,
    included_paths,
    archive_stream,
):
    import subprocess

    completed = subprocess.run(
        _trusted_git_argv_v1(
            "archive",
            "--format=tar",
            evidence_commit_sha,
            "--",
            *included_paths,
        ),
        cwd=repository_root,
        env=build_sanitized_git_environment_v1(),
        stdin=subprocess.DEVNULL,
        stdout=archive_stream,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise ValueError("trusted Git archive failed closed")
    archive_stream.seek(0)


def _remove_immutable_reviewer_tree_v1(export_root, root_identity):
    import os
    import shutil
    import stat
    import tempfile

    normalized = os.path.normpath(os.path.abspath(export_root))
    temporary_parent = os.path.normpath(tempfile.gettempdir())
    if (
        export_root != normalized
        or os.path.dirname(normalized) != temporary_parent
        or not os.path.basename(normalized).startswith("v3m0-b7-reviewer-")
    ):
        raise ValueError("reviewer cleanup target is not an owned mkdtemp root")
    root_stat = os.stat(normalized, follow_symlinks=False)
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or (root_stat.st_dev, root_stat.st_ino) != root_identity
    ):
        raise ValueError("reviewer cleanup root identity drifted")
    for current_root, directory_names, file_names in os.walk(
        normalized,
        topdown=False,
        followlinks=False,
    ):
        for name in file_names:
            path = os.path.join(current_root, name)
            observation = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(observation.st_mode):
                raise ValueError("reviewer cleanup encountered a non-regular file")
            os.chmod(path, 0o600, follow_symlinks=False)
        for name in directory_names:
            path = os.path.join(current_root, name)
            observation = os.stat(path, follow_symlinks=False)
            if not stat.S_ISDIR(observation.st_mode):
                raise ValueError("reviewer cleanup encountered a non-directory")
            os.chmod(path, 0o700, follow_symlinks=False)
    os.chmod(normalized, 0o700, follow_symlinks=False)
    shutil.rmtree(normalized)
    return not os.path.exists(normalized)


def cleanup_immutable_reviewer_export_v1(export_observation):
    """Remove only a root created and identity-bound by this process."""

    if (
        type(export_observation) is not dict
        or export_observation.get("export_schema_version")
        != "experimental.v3m0.b7.immutable-reviewer-export.v1"
    ):
        return False
    export_root = export_observation.get("export_root")
    root_identity = export_observation.get("root_identity")
    if (
        type(export_root) is not str
        or type(root_identity) is not tuple
        or len(root_identity) != 2
        or _OWNED_REVIEWER_EXPORT_ROOTS_V1.get(export_root) != root_identity
    ):
        return False
    del _OWNED_REVIEWER_EXPORT_ROOTS_V1[export_root]
    try:
        return _remove_immutable_reviewer_tree_v1(export_root, root_identity)
    except (OSError, TypeError, ValueError):
        return False


def materialize_immutable_reviewer_export_v1(
    *,
    repository_root,
    evidence_commit_sha,
):
    """Materialize the exact reviewer tree from E, never from the worktree."""

    import os
    import stat
    import tarfile
    import tempfile

    root = _normalize_reviewer_repository_root_v1(repository_root)
    blobs = read_immutable_git_tree_blobs_v1(
        repository_root=root,
        commit_sha=evidence_commit_sha,
        included_paths=_REVIEWER_EXPORT_INCLUDED_PATHS_V1,
    )
    blob_by_path = {blob[1]: blob for blob in blobs}
    export_root = tempfile.mkdtemp(prefix="v3m0-b7-reviewer-")
    root_stat = os.stat(export_root, follow_symlinks=False)
    root_identity = (root_stat.st_dev, root_stat.st_ino)
    _OWNED_REVIEWER_EXPORT_ROOTS_V1[export_root] = root_identity
    partial = {
        "export_schema_version": (
            "experimental.v3m0.b7.immutable-reviewer-export.v1"
        ),
        "export_root": export_root,
        "root_identity": root_identity,
    }
    try:
        with tempfile.TemporaryFile() as archive_stream:
            _run_trusted_git_archive_v1(
                root,
                evidence_commit_sha,
                _REVIEWER_EXPORT_INCLUDED_PATHS_V1,
                archive_stream,
            )
            with tarfile.open(fileobj=archive_stream, mode="r:") as archive:
                members = _validate_reviewer_tar_members_v1(
                    archive.getmembers(),
                    expected_file_paths=tuple(blob_by_path),
                )
                archive.extractall(path=export_root, members=members)
        observed_files = set()
        observed_directories = []
        for current_root, directory_names, file_names in os.walk(
            export_root,
            topdown=False,
            followlinks=False,
        ):
            for name in file_names:
                path = os.path.join(current_root, name)
                observation = os.stat(path, follow_symlinks=False)
                if not stat.S_ISREG(observation.st_mode):
                    raise ValueError("reviewer export contains a non-regular file")
                relative = os.path.relpath(path, export_root).replace(os.sep, "/")
                if relative not in blob_by_path:
                    raise ValueError("reviewer export contains an unscoped file")
                if pathlib.Path(path).read_bytes() != blob_by_path[relative][5]:
                    raise ValueError("reviewer export bytes differ from E blob")
                observed_files.add(relative)
                frozen_mode = 0o555 if blob_by_path[relative][2] == "100755" else 0o444
                os.chmod(path, frozen_mode, follow_symlinks=False)
            for name in directory_names:
                path = os.path.join(current_root, name)
                observation = os.stat(path, follow_symlinks=False)
                if not stat.S_ISDIR(observation.st_mode):
                    raise ValueError("reviewer export contains a non-directory")
                observed_directories.append(path)
        if observed_files != set(blob_by_path):
            raise ValueError("reviewer export leaf set differs from E tree")
        experiments_initializer = os.path.join(
            export_root,
            "experiments",
            "__init__.py",
        )
        if os.path.exists(experiments_initializer):
            raise ValueError("reviewer export contains experiments initializer")
        required_input_bytes = {}
        for role, path in _REVIEWER_REQUIRED_INPUT_PATHS_V1:
            raw_bytes = pathlib.Path(export_root, path).read_bytes()
            if raw_bytes != blob_by_path[path][5]:
                raise ValueError("reviewer required input differs from E blob")
            required_input_bytes[role] = raw_bytes
        for path in observed_directories:
            os.chmod(path, 0o555, follow_symlinks=False)
        os.chmod(export_root, 0o555, follow_symlinks=False)
        return {
            **partial,
            "evidence_commit_sha": evidence_commit_sha,
            "included_path_order": list(_REVIEWER_EXPORT_INCLUDED_PATHS_V1),
            "tree_blobs": blobs,
            "required_input_bytes": required_input_bytes,
            "namespace_observation": {
                "fresh_export_root_count": 1,
                "experiments_init_present": False,
                "experiments_namespace_portion_count": 1,
                "shadowing_paths": [],
            },
        }
    except (OSError, TypeError, ValueError, tarfile.TarError):
        cleanup_immutable_reviewer_export_v1(partial)
        raise


def materialize_reviewer_command_v1(
    *,
    reviewer_role,
    frozen_python_executable,
    evidence_commit_sha,
    reviewed_executable_source_closure_sha,
):
    """Materialize one exact role-specific reviewer argv tuple."""

    subcommand = None
    for frozen_role, frozen_subcommand in _REVIEWER_SUBCOMMANDS_V1:
        if reviewer_role == frozen_role and type(reviewer_role) is str:
            subcommand = frozen_subcommand
            break
    if subcommand is None:
        raise ValueError("reviewer role is not frozen")
    if (
        type(frozen_python_executable) is not str
        or not frozen_python_executable.startswith("/")
        or frozen_python_executable.startswith("//")
        or any(
            part in ("", ".", "..") for part in frozen_python_executable.split("/")[1:]
        )
    ):
        raise ValueError("frozen Python executable path is not normalized absolute")
    _require_lower_hex_v1(evidence_commit_sha, 40, "evidence commit SHA")
    _require_lower_hex_v1(
        reviewed_executable_source_closure_sha,
        64,
        "reviewed executable source closure SHA",
    )
    return (
        frozen_python_executable,
        "-s",
        "-m",
        "experiments.v3m0_b7_schema_lab.compare",
        subcommand,
        "--evidence-commit",
        evidence_commit_sha,
        "--reviewed-executable-source-closure-sha",
        reviewed_executable_source_closure_sha,
        "--emit-replay-report",
    )


def _reviewer_protocol_id_v1(reviewer_role):
    for frozen_role, protocol_id in _REVIEWER_PROTOCOLS_V2:
        if reviewer_role == frozen_role and type(reviewer_role) is str:
            return protocol_id
    raise ValueError("reviewer role is not frozen")


def _validate_reviewer_contract_inputs_v1(raw_inputs):
    if type(raw_inputs) is not dict:
        raise TypeError("reviewer raw inputs must be an exact dict")
    parsed = {}
    for role, expected_sha, expected_schema in _REVIEWER_CONTRACT_INPUTS_V1:
        raw_bytes = raw_inputs[role]
        if (
            type(raw_bytes) is not bytes
            or hashlib.sha256(raw_bytes).hexdigest() != expected_sha
        ):
            raise ValueError(f"reviewer {role} raw root drifted")
        body = _strict_json_loads_v1(raw_bytes)
        if (
            type(body) is not dict
            or body.get("registry_schema_version") != expected_schema
        ):
            raise ValueError(f"reviewer {role} schema drifted")
        parsed[role] = body
    materialization = parsed["registry_overlay_v921"].get(
        "ordered_materialization_contract"
    )
    if (
        type(materialization) is not dict
        or materialization.get("input_role_order")
        != ["BASE_V91", "OVERLAY_V92", "OVERLAY_V921"]
        or materialization.get("algorithm")
        != "VERIFY_EXACT_RAW_SHA_IN_INPUT_ROLE_ORDER_AND_APPLY_OVERLAYS_SEQUENTIALLY"
    ):
        raise ValueError("reviewer ordered contract materialization drifted")
    return parsed


def _validate_record_self_hash_v1(raw_body, hash_field, field):
    expected = _canonical_sha_v1(
        {name: value for name, value in raw_body.items() if name != hash_field}
    )
    if raw_body[hash_field] != expected:
        raise ValueError(f"reviewer {field} self root drifted")


def _validate_reviewer_comparison_joins_v1(d0, d1, d0_raw_bytes):
    if (
        d1["d0_result_raw_sha256"]
        != hashlib.sha256(d0_raw_bytes).hexdigest()
        or d1["d0_result_sha"] != d0["d0_result_sha"]
        or d1["d0_decision_payload_sha"] != d0["decision_payload_sha"]
    ):
        raise ValueError("reviewer D1 embedded D0 roots drifted")
    shared = (
        "common_commit_sha",
        "common_source_sha256",
        "compare_source_sha256",
        "corpus_fixture_raw_sha256",
        "corpus_spec_sha",
        "mutation_universe_sha",
        "metric_spec_sha",
    )
    if any(d1[name] != d0[name] for name in shared):
        raise ValueError("reviewer D0/D1 shared roots drifted")
    if _canonical_json_bytes_v1(
        d1["environment_manifest"]
    ) != _canonical_json_bytes_v1(d0["environment_manifest"]):
        raise ValueError("reviewer D0/D1 environment body drifted")


def _validate_reviewer_d0_outcome_v1(d0):
    rows = d0["ordered_route_results"]
    survivors = []
    for row in rows:
        checked = row
        if type(checked) is not dict:
            raise TypeError("reviewer D0 route result must be an exact object")
        _validate_record_self_hash_v1(checked, "route_result_sha", "D0 route")
        manifest = checked["route_manifest"]
        _validate_record_self_hash_v1(
            manifest,
            "route_manifest_sha",
            "D0 route manifest",
        )
        if checked["survives_d0"] is True:
            survivors.append(checked["route_id"])
    if survivors != d0["surviving_route_ids"]:
        raise ValueError("reviewer D0 survivors drifted")
    return rows


def _validate_reviewer_d1_outcome_v1(d0, d1, metric_spec):
    rows = d1["ordered_route_results"]
    if [row["route_id"] for row in rows] != d0["surviving_route_ids"]:
        raise ValueError("reviewer D1 route order drifted")
    survivors = []
    for row in rows:
        checked = row
        if type(checked) is not dict:
            raise TypeError("reviewer D1 route result must be an exact object")
        _validate_record_self_hash_v1(checked, "route_result_sha", "D1 route")
        vector = checked["metric_vector"]
        _validate_record_self_hash_v1(vector, "metric_vector_sha", "metric vector")
        if checked["survives_d1"] is True:
            survivors.append((checked["route_id"], vector))
    survivor_ids = [route_id for route_id, _vector in survivors]
    if survivor_ids != d1["surviving_route_ids"] or not survivors:
        raise ValueError("reviewer D1 survivors drifted")
    metric_order = metric_spec["metric_order"]
    minimum_tuple = min(
        tuple(vector[name] for name in metric_order)
        for _route_id, vector in survivors
    )
    minima = [
        (route_id, vector)
        for route_id, vector in survivors
        if tuple(vector[name] for name in metric_order) == minimum_tuple
    ]
    tie_detected = len(minima) > 1
    winner = None if tie_detected else minima[0][0]
    minimum_vector = minima[0][1]
    if (
        d1["minimum_metric_vector"] != minimum_vector
        or d1["tie_detected"] is not tie_detected
        or d1["provisional_winner_route_id"] != winner
        or winner is None
    ):
        raise ValueError("reviewer D1 metric selection drifted")
    return survivor_ids, winner


def _replay_all_routes_v1(ordered_transcripts):
    from experiments.v3m0_b7_schema_lab.a_flat import (
        encode_normalized_transcript as encode_a,
        verify_and_decode_route_wire as decode_a,
    )
    from experiments.v3m0_b7_schema_lab.b_progress import (
        encode_normalized_transcript as encode_b,
        verify_and_decode_route_wire as decode_b,
    )
    from experiments.v3m0_b7_schema_lab.c_union import (
        encode_normalized_transcript as encode_c,
        verify_and_decode_route_wire as decode_c,
    )

    for transcript in ordered_transcripts:
        source = _canonical_json_bytes_v1(transcript)
        wire_a = encode_a(source)
        wire_b = encode_b(source)
        wire_c = encode_c(source)
        if (
            decode_a(wire_a) != source
            or decode_b(wire_b) != source
            or decode_c(wire_c) != source
        ):
            raise ValueError("reviewer route roundtrip differs from corpus bytes")


def _build_reviewer_replay_report_v1(
    *,
    reviewer_role,
    evidence_commit_sha,
    replay_input_root_sha,
    d0_decision_payload_sha,
    d1_decision_payload_sha,
    surviving_route_ids,
    provisional_winner_route_id,
):
    protocol_id = _reviewer_protocol_id_v1(reviewer_role)
    _require_lower_hex_v1(evidence_commit_sha, 40, "reviewed evidence commit")
    for value, field in (
        (replay_input_root_sha, "reviewer replay input root"),
        (d0_decision_payload_sha, "reviewer D0 decision root"),
        (d1_decision_payload_sha, "reviewer D1 decision root"),
    ):
        _require_lower_hex_v1(value, 64, field)
    if (
        type(surviving_route_ids) is not list
        or type(provisional_winner_route_id) is not str
        or provisional_winner_route_id not in surviving_route_ids
    ):
        raise ValueError("reviewer report requires a unique surviving winner")
    report = {
        "replay_report_schema_version": "experimental.v3m0.b7.replay-report.v1",
        "reviewer_role": reviewer_role,
        "review_protocol_id": protocol_id,
        "lab_evidence_commit_sha": evidence_commit_sha,
        "replay_input_root_sha": replay_input_root_sha,
        "recomputed_d0_decision_payload_sha": d0_decision_payload_sha,
        "recomputed_d1_decision_payload_sha": d1_decision_payload_sha,
        "observed_surviving_route_ids": surviving_route_ids,
        "observed_provisional_winner_route_id": provisional_winner_route_id,
        "replay_output_root_sha": "",
        "replay_report_sha": "",
    }
    report["replay_output_root_sha"] = _canonical_sha_v1(
        {name: report[name] for name in _REPLAY_REPORT_OUTPUT_PROJECTION_FIELDS_V1}
    )
    report["replay_report_sha"] = _canonical_sha_v1(
        {
            name: value
            for name, value in report.items()
            if name != "replay_report_sha"
        }
    )
    return validate_replay_report_v1(report)


def _read_reviewer_inputs_v1():
    return {
        role: pathlib.Path.read_bytes(pathlib.Path(path))
        for role, path in _REVIEWER_INPUT_PATHS_V1
    }


def _execute_reviewer_replay_v1(
    *,
    reviewer_role,
    evidence_commit_sha,
    source_closure_sha,
):
    _require_lower_hex_v1(evidence_commit_sha, 40, "reviewed evidence commit")
    _require_lower_hex_v1(source_closure_sha, 64, "reviewed source closure")
    protocol_id = _reviewer_protocol_id_v1(reviewer_role)
    raw_inputs = _read_reviewer_inputs_v1()
    _validate_reviewer_contract_inputs_v1(raw_inputs)
    d0_raw = raw_inputs["d0"]
    d1_raw = raw_inputs["d1"]
    d0 = _require_exact_object_fields_v1(
        _strict_json_loads_v1(d0_raw),
        _D0_COMPARISON_FIELDS_V1,
        "D0 comparison",
    )
    d1 = _require_exact_object_fields_v1(
        _strict_json_loads_v1(d1_raw),
        _D1_COMPARISON_FIELDS_V1,
        "D1 comparison",
    )
    if (
        d0["d0_result_schema_version"]
        != "experimental.v3m0.b7.d0-comparison.v1"
        or d1["d1_result_schema_version"]
        != "experimental.v3m0.b7.d1-comparison.v1"
    ):
        raise ValueError("reviewer comparison schema drifted")
    _validate_record_self_hash_v1(d0, "d0_result_sha", "D0 comparison")
    _validate_record_self_hash_v1(d1, "d1_result_sha", "D1 comparison")
    if d0["decision_payload_sha"] != _canonical_sha_v1(
        {name: d0[name] for name in _D0_COMPARISON_FIELDS_V1[:11]}
    ):
        raise ValueError("reviewer D0 decision root drifted")
    if d1["decision_payload_sha"] != _canonical_sha_v1(
        {name: d1[name] for name in _D1_DECISION_FIELDS_V1}
    ):
        raise ValueError("reviewer D1 decision root drifted")
    _validate_reviewer_comparison_joins_v1(d0, d1, d0_raw)
    fixture_raw = raw_inputs["corpus"]
    if hashlib.sha256(fixture_raw).hexdigest() != d0["corpus_fixture_raw_sha256"]:
        raise ValueError("reviewer corpus raw root drifted")
    fixture = _require_exact_object_fields_v1(
        _strict_json_loads_v1(fixture_raw),
        (
            "fixture_schema_version",
            "corpus_spec",
            "mutation_universe",
            "metric_spec",
            "environment_manifest",
            "synthetic_graph_manifest",
            "ordered_d0_transcripts",
            "fixture_sha",
        ),
        "corpus fixture",
    )
    if fixture["fixture_schema_version"] != "experimental.v3m0.b7.corpus-fixture.v2":
        raise ValueError("reviewer corpus fixture schema drifted")
    _validate_record_self_hash_v1(fixture, "fixture_sha", "corpus fixture")
    for body, hash_field, field in (
        (fixture["corpus_spec"], "corpus_spec_sha", "corpus spec"),
        (
            fixture["mutation_universe"],
            "mutation_universe_sha",
            "mutation universe",
        ),
        (fixture["metric_spec"], "metric_spec_sha", "metric spec"),
        (fixture["environment_manifest"], "environment_sha", "environment"),
    ):
        _validate_record_self_hash_v1(body, hash_field, field)
    if (
        fixture["corpus_spec"]["corpus_spec_sha"] != d0["corpus_spec_sha"]
        or fixture["mutation_universe"]["mutation_universe_sha"]
        != d0["mutation_universe_sha"]
        or fixture["metric_spec"]["metric_spec_sha"] != d0["metric_spec_sha"]
        or _canonical_json_bytes_v1(fixture["environment_manifest"])
        != _canonical_json_bytes_v1(d0["environment_manifest"])
    ):
        raise ValueError("reviewer corpus fixture joins drifted")
    if (
        hashlib.sha256(raw_inputs["common"]).hexdigest()
        != d0["common_source_sha256"]
        or hashlib.sha256(raw_inputs["compare"]).hexdigest()
        != d0["compare_source_sha256"]
    ):
        raise ValueError("reviewer common/compare source root drifted")
    d0_rows = _validate_reviewer_d0_outcome_v1(d0)
    survivor_ids, winner = _validate_reviewer_d1_outcome_v1(
        d0,
        d1,
        fixture["metric_spec"],
    )
    if reviewer_role == "CORPUS_REPLAY":
        if [row["route_id"] for row in d0_rows] != [
            "A_FLAT",
            "B_PROGRESS",
            "C_UNION",
        ]:
            raise ValueError("reviewer D0 corpus route order drifted")
    elif reviewer_role != "METRIC_REPLAY":
        raise ValueError("reviewer role drifted after validation")
    _replay_all_routes_v1(fixture["ordered_d0_transcripts"])
    manifests = [row["route_manifest"] for row in d0_rows]
    projection = {
        "reviewer_role": reviewer_role,
        "review_protocol_id": protocol_id,
        "reviewed_lab_evidence_commit_sha": evidence_commit_sha,
        "review_environment_manifest_sha": d0["environment_manifest"][
            "environment_sha"
        ],
        "reviewed_d0_result_raw_sha256": hashlib.sha256(d0_raw).hexdigest(),
        "reviewed_d0_result_sha": d0["d0_result_sha"],
        "reviewed_d0_decision_payload_sha": d0["decision_payload_sha"],
        "reviewed_d1_result_raw_sha256": hashlib.sha256(d1_raw).hexdigest(),
        "reviewed_d1_result_sha": d1["d1_result_sha"],
        "reviewed_d1_decision_payload_sha": d1["decision_payload_sha"],
        "reviewed_common_commit_sha": d0["common_commit_sha"],
        "reviewed_route_commit_shas": [
            manifest["route_commit_sha"] for manifest in manifests
        ],
        "reviewed_corpus_spec_sha": d0["corpus_spec_sha"],
        "reviewed_mutation_universe_sha": d0["mutation_universe_sha"],
        "reviewed_metric_spec_sha": d0["metric_spec_sha"],
        "reviewed_compare_source_sha256": d0["compare_source_sha256"],
        "reviewed_executable_source_closure_sha": source_closure_sha,
        "replay_source_sha256": hashlib.sha256(raw_inputs["compare"]).hexdigest(),
    }
    if tuple(projection) != _REPLAY_INPUT_PROJECTION_FIELDS_V1:
        raise RuntimeError("reviewer replay input projection order drifted")
    return _build_reviewer_replay_report_v1(
        reviewer_role=reviewer_role,
        evidence_commit_sha=evidence_commit_sha,
        replay_input_root_sha=_canonical_sha_v1(projection),
        d0_decision_payload_sha=d0["decision_payload_sha"],
        d1_decision_payload_sha=d1["decision_payload_sha"],
        surviving_route_ids=survivor_ids,
        provisional_winner_route_id=winner,
    )


def _emit_reviewer_replay_report_v1(report):
    payload = _canonical_json_bytes_v1(validate_replay_report_v1(report))
    return sys.stdout.buffer.write(payload + b"\n")


def _review_corpus_replay_cli(*, evidence_commit_sha, source_closure_sha):
    report = _execute_reviewer_replay_v1(
        reviewer_role="CORPUS_REPLAY",
        evidence_commit_sha=evidence_commit_sha,
        source_closure_sha=source_closure_sha,
    )
    return _emit_reviewer_replay_report_v1(report)


def _review_metric_replay_cli(*, evidence_commit_sha, source_closure_sha):
    report = _execute_reviewer_replay_v1(
        reviewer_role="METRIC_REPLAY",
        evidence_commit_sha=evidence_commit_sha,
        source_closure_sha=source_closure_sha,
    )
    return _emit_reviewer_replay_report_v1(report)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="v3m0-b7-reviewer")
    parser.add_argument("subcommand", choices=("review-corpus", "review-metric"))
    parser.add_argument("--evidence-commit", required=True)
    parser.add_argument(
        "--reviewed-executable-source-closure-sha",
        required=True,
    )
    parser.add_argument("--emit-replay-report", action="store_true", required=True)
    arguments = parser.parse_args(argv)
    if arguments.subcommand == "review-corpus":
        _review_corpus_replay_cli(
            evidence_commit_sha=arguments.evidence_commit,
            source_closure_sha=(
                arguments.reviewed_executable_source_closure_sha
            ),
        )
    elif arguments.subcommand == "review-metric":
        _review_metric_replay_cli(
            evidence_commit_sha=arguments.evidence_commit,
            source_closure_sha=(
                arguments.reviewed_executable_source_closure_sha
            ),
        )
    else:
        raise ValueError("reviewer subcommand escaped parser choices")
    return 0


def precheck_frozen_python_executable_v1(
    *,
    recorded_realpath,
    recorded_raw_sha256,
):
    """Totalize the frozen reviewer-Python realpath, mode, and raw-SHA check."""

    import os
    import stat

    if type(recorded_realpath) is not str or not recorded_realpath.startswith("/"):
        raise ValueError("recorded Python realpath must be an absolute exact string")
    if (
        type(recorded_raw_sha256) is not str
        or len(recorded_raw_sha256) != 64
        or any(character not in "0123456789abcdef" for character in recorded_raw_sha256)
    ):
        raise ValueError("recorded Python raw SHA must be lowercase SHA-256")
    empty_observation = {
        "observed_realpath": None,
        "observed_raw_sha256": None,
        "observed_device": None,
        "observed_inode": None,
        "observed_mode": None,
        "observed_size": None,
        "observed_mtime_ns": None,
        "observed_ctime_ns": None,
        "regular_file": False,
        "executable": False,
        "precheck_passed": False,
    }
    file_descriptor = None
    try:
        observed_realpath = os.path.realpath(recorded_realpath)
        if observed_realpath != recorded_realpath:
            return empty_observation
        file_descriptor = os.open(
            recorded_realpath,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        before = os.fstat(file_descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        regular_file = stat.S_ISREG(before.st_mode)
        executable = regular_file and bool(before.st_mode & 0o111)
        observed_raw_sha256 = None
        complete_read = False
        if regular_file:
            hash_state = hashlib.sha256()
            remaining = before.st_size
            complete_read = True
            while remaining:
                chunk = os.read(
                    file_descriptor,
                    min(_PYTHON_EXECUTABLE_HASH_CHUNK_BYTES_V1, remaining),
                )
                if not chunk:
                    complete_read = False
                    break
                hash_state.update(chunk)
                remaining -= len(chunk)
            if complete_read and os.read(file_descriptor, 1):
                complete_read = False
            if complete_read:
                observed_raw_sha256 = hash_state.hexdigest()
        after = os.fstat(file_descriptor)
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        path_status = os.stat(recorded_realpath, follow_symlinks=False)
        path_identity = (
            path_status.st_dev,
            path_status.st_ino,
            path_status.st_mode,
            path_status.st_size,
            path_status.st_mtime_ns,
            path_status.st_ctime_ns,
        )
        path_executable = os.access(recorded_realpath, os.X_OK)
        final_status = os.stat(recorded_realpath, follow_symlinks=False)
        final_identity = (
            final_status.st_dev,
            final_status.st_ino,
            final_status.st_mode,
            final_status.st_size,
            final_status.st_mtime_ns,
            final_status.st_ctime_ns,
        )
        final_realpath = os.path.realpath(recorded_realpath)
        stable_identity = (
            before_identity == after_identity == path_identity == final_identity
            and final_realpath == recorded_realpath
        )
        return {
            "observed_realpath": observed_realpath,
            "observed_raw_sha256": observed_raw_sha256,
            "observed_device": before.st_dev,
            "observed_inode": before.st_ino,
            "observed_mode": before.st_mode,
            "observed_size": before.st_size,
            "observed_mtime_ns": before.st_mtime_ns,
            "observed_ctime_ns": before.st_ctime_ns,
            "regular_file": regular_file,
            "executable": executable,
            "precheck_passed": (
                stable_identity
                and complete_read
                and executable
                and path_executable
                and observed_raw_sha256 == recorded_raw_sha256
            ),
        }
    except OSError:
        return empty_observation
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass


def recheck_frozen_python_executable_identity_v1(
    *,
    recorded_realpath,
    precheck_observation,
):
    """Recheck the descriptor-bound identity immediately before child spawn."""

    import os
    import stat

    if (
        type(recorded_realpath) is not str
        or type(precheck_observation) is not dict
        or precheck_observation.get("precheck_passed") is not True
    ):
        return False
    fields = (
        "observed_device",
        "observed_inode",
        "observed_mode",
        "observed_size",
        "observed_mtime_ns",
        "observed_ctime_ns",
    )
    try:
        expected_identity = tuple(precheck_observation[name] for name in fields)
    except KeyError:
        return False
    if any(type(item) is not int for item in expected_identity):
        return False
    try:
        if os.path.realpath(recorded_realpath) != recorded_realpath:
            return False
        before = os.stat(recorded_realpath, follow_symlinks=False)
        executable = os.access(recorded_realpath, os.X_OK)
        after = os.stat(recorded_realpath, follow_symlinks=False)
    except OSError:
        return False
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    return (
        expected_identity == before_identity == after_identity
        and stat.S_ISREG(after.st_mode)
        and bool(after.st_mode & 0o111)
        and executable
    )


def _require_normalized_absolute_path_v2(value, field):
    import os

    parts = value.split("/")[1:] if type(value) is str else ()
    if (
        type(value) is not str
        or not os.path.isabs(value)
        or value.startswith("//")
        or "\\" in value
        or "\x00" in value
        or os.path.normpath(value) != value
        or not parts
        or any(part in ("", ".", "..") for part in parts)
    ):
        raise ValueError(f"{field} must be an absolute lexically normalized path")
    return value


def _stable_regular_file_observation_v2(path, *, executable_required):
    import os
    import stat

    empty = {
        "raw_sha256": None,
        "device": None,
        "inode": None,
        "mode": None,
        "size": None,
        "mtime_ns": None,
        "ctime_ns": None,
        "regular_file": False,
        "executable": False,
        "stable": False,
    }
    file_descriptor = None
    try:
        file_descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        before = os.fstat(file_descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        regular_file = stat.S_ISREG(before.st_mode)
        executable = regular_file and bool(before.st_mode & 0o111)
        complete_read = regular_file
        observed_raw_sha256 = None
        if regular_file:
            hash_state = hashlib.sha256()
            remaining = before.st_size
            while remaining:
                chunk = os.read(
                    file_descriptor,
                    min(_PYTHON_EXECUTABLE_HASH_CHUNK_BYTES_V1, remaining),
                )
                if not chunk:
                    complete_read = False
                    break
                hash_state.update(chunk)
                remaining -= len(chunk)
            if complete_read and os.read(file_descriptor, 1):
                complete_read = False
            if complete_read:
                observed_raw_sha256 = hash_state.hexdigest()
        after = os.fstat(file_descriptor)
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        final = os.stat(path, follow_symlinks=False)
        final_identity = (
            final.st_dev,
            final.st_ino,
            final.st_mode,
            final.st_size,
            final.st_mtime_ns,
            final.st_ctime_ns,
        )
        path_executable = os.access(path, os.X_OK)
        stable = (
            complete_read
            and before_identity == after_identity == final_identity
            and regular_file
            and (not executable_required or (executable and path_executable))
        )
        return {
            "raw_sha256": observed_raw_sha256,
            "device": before.st_dev,
            "inode": before.st_ino,
            "mode": before.st_mode,
            "size": before.st_size,
            "mtime_ns": before.st_mtime_ns,
            "ctime_ns": before.st_ctime_ns,
            "regular_file": regular_file,
            "executable": executable,
            "stable": stable,
        }
    except OSError:
        return empty
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass


def _resolve_python_invocation_chain_v2(python_invocation_path):
    import os
    import stat

    cursor = python_invocation_path
    observed_inodes = set()
    ordered_hops = []
    symlink_count = 0
    try:
        while True:
            status = os.lstat(cursor)
            inode_identity = (status.st_dev, status.st_ino)
            if inode_identity in observed_inodes:
                return ordered_hops, None, False
            observed_inodes.add(inode_identity)
            is_symlink = stat.S_ISLNK(status.st_mode)
            symlink_target = os.readlink(cursor) if is_symlink else None
            ordered_hops.append(
                {
                    "hop_ordinal": len(ordered_hops),
                    "absolute_normalized_path": cursor,
                    "lstat_device": status.st_dev,
                    "lstat_inode": status.st_ino,
                    "lstat_mode": status.st_mode,
                    "lstat_size": status.st_size,
                    "lstat_mtime_ns": status.st_mtime_ns,
                    "lstat_ctime_ns": status.st_ctime_ns,
                    "symlink_target_or_null": symlink_target,
                }
            )
            if not is_symlink:
                return ordered_hops, cursor, True
            symlink_count += 1
            if symlink_count > _PYTHON_INVOCATION_MAX_SYMLINK_HOPS_V2:
                return ordered_hops, None, False
            if os.path.isabs(symlink_target):
                cursor = os.path.normpath(symlink_target)
            else:
                cursor = os.path.normpath(
                    os.path.join(os.path.dirname(cursor), symlink_target)
                )
            if not os.path.isabs(cursor) or cursor.startswith("//"):
                return ordered_hops, None, False
    except OSError:
        return ordered_hops, None, False


def _nearest_pyvenv_cfg_v2(python_invocation_path):
    import os

    cursor = os.path.dirname(python_invocation_path)
    while True:
        candidate = os.path.join(cursor, "pyvenv.cfg")
        try:
            os.lstat(candidate)
        except FileNotFoundError:
            pass
        except OSError:
            return candidate, cursor, None
        else:
            return (
                candidate,
                cursor,
                _stable_regular_file_observation_v2(
                    candidate,
                    executable_required=False,
                ),
            )
        parent = os.path.dirname(cursor)
        if parent == cursor:
            return None, None, None
        cursor = parent


def precheck_python_invocation_identity_v2(
    *,
    python_invocation_path,
    recorded_realpath,
    recorded_raw_sha256,
    recorded_venv_prefix,
    recorded_pyvenv_cfg_path,
    recorded_pyvenv_cfg_raw_sha256,
):
    """Observe the v9.2 venv invocation and resolved-target identities."""

    import os

    invocation = _require_normalized_absolute_path_v2(
        python_invocation_path,
        "Python invocation",
    )
    target = _require_normalized_absolute_path_v2(
        recorded_realpath,
        "recorded Python target",
    )
    venv_prefix = _require_normalized_absolute_path_v2(
        recorded_venv_prefix,
        "recorded venv prefix",
    )
    pyvenv_cfg = _require_normalized_absolute_path_v2(
        recorded_pyvenv_cfg_path,
        "recorded pyvenv.cfg",
    )
    _require_lower_hex_v1(recorded_raw_sha256, 64, "recorded Python raw SHA")
    _require_lower_hex_v1(
        recorded_pyvenv_cfg_raw_sha256,
        64,
        "recorded pyvenv.cfg raw SHA",
    )
    ordered_hops, observed_target, chain_complete = _resolve_python_invocation_chain_v2(
        invocation
    )
    invocation_resolves_to_recorded_target = (
        os.path.realpath(invocation) == target and os.path.realpath(target) == target
    )
    target_observation = _stable_regular_file_observation_v2(
        observed_target or target,
        executable_required=True,
    )
    observed_cfg, observed_prefix, cfg_observation = _nearest_pyvenv_cfg_v2(invocation)
    if cfg_observation is None:
        cfg_observation = _stable_regular_file_observation_v2(
            pyvenv_cfg,
            executable_required=False,
        )
    complete_identity = (
        chain_complete
        and observed_target is not None
        and target_observation["stable"] is True
        and observed_cfg is not None
        and observed_prefix is not None
        and cfg_observation["stable"] is True
    )
    projection = None
    identity_sha = None
    if complete_identity:
        projection = {
            "python_invocation_path": invocation,
            "ordered_lstat_hops": ordered_hops,
            "python_executable_realpath": observed_target,
            "python_executable_raw_sha256": target_observation["raw_sha256"],
            "python_venv_prefix": observed_prefix,
            "python_pyvenv_cfg_path": observed_cfg,
            "python_pyvenv_cfg_raw_sha256": cfg_observation["raw_sha256"],
        }
        identity_sha = _common.canonical_sha_v1(projection)
    precheck_passed = (
        complete_identity
        and invocation_resolves_to_recorded_target
        and observed_target == target
        and target_observation["raw_sha256"] == recorded_raw_sha256
        and observed_prefix == venv_prefix
        and observed_cfg == pyvenv_cfg
        and cfg_observation["raw_sha256"] == recorded_pyvenv_cfg_raw_sha256
    )
    return {
        "profile_id": "v3m0-b7-python-venv-invocation-identity-v1",
        "python_invocation_path": invocation,
        "recorded_realpath": target,
        "recorded_raw_sha256": recorded_raw_sha256,
        "recorded_venv_prefix": venv_prefix,
        "recorded_pyvenv_cfg_path": pyvenv_cfg,
        "recorded_pyvenv_cfg_raw_sha256": recorded_pyvenv_cfg_raw_sha256,
        "ordered_lstat_hops": ordered_hops,
        "observed_realpath": observed_target,
        "observed_raw_sha256": target_observation["raw_sha256"],
        "observed_venv_prefix": observed_prefix,
        "observed_pyvenv_cfg_path": observed_cfg,
        "observed_pyvenv_cfg_raw_sha256": cfg_observation["raw_sha256"],
        "python_invocation_identity_projection": projection,
        "python_invocation_identity_sha": identity_sha,
        "target_identity": target_observation,
        "pyvenv_cfg_identity": cfg_observation,
        "precheck_passed": precheck_passed,
    }


def _python_environment_probe_report_is_well_typed_v2(report):
    string_fields = (
        "numpy_float64_dtype_str",
        "numpy_version",
        "platform_machine",
        "platform_release",
        "platform_system",
        "python_executable_realpath",
        "python_implementation",
        "python_invocation_path",
        "python_venv_prefix",
        "python_version",
        "scipy_version",
    )
    return (
        type(report) is dict
        and tuple(sorted(report)) == _PYTHON_ENVIRONMENT_PROBE_FIELDS_V2
        and all(type(report[name]) is str and report[name] for name in string_fields)
        and type(report["numpy_float64_itemsize"]) is int
        and report["numpy_float64_itemsize"] == 8
        and type(report["byteorder"]) is str
        and report["byteorder"] in ("little", "big")
        and type(report["threadpool_info"]) is list
    )


def recheck_python_invocation_identity_v2(*, precheck_observation):
    """Immediately recompute the full v9.2 path identity before Popen."""

    if (
        type(precheck_observation) is not dict
        or precheck_observation.get("profile_id")
        != "v3m0-b7-python-venv-invocation-identity-v1"
        or precheck_observation.get("precheck_passed") is not True
    ):
        return False
    required = (
        "python_invocation_path",
        "recorded_realpath",
        "recorded_raw_sha256",
        "recorded_venv_prefix",
        "recorded_pyvenv_cfg_path",
        "recorded_pyvenv_cfg_raw_sha256",
    )
    try:
        arguments = {name: precheck_observation[name] for name in required}
        refreshed = precheck_python_invocation_identity_v2(**arguments)
    except (KeyError, OSError, TypeError, ValueError):
        return False
    if refreshed["precheck_passed"] is not True:
        return False
    compared_fields = (
        "ordered_lstat_hops",
        "python_invocation_identity_projection",
        "python_invocation_identity_sha",
        "target_identity",
        "pyvenv_cfg_identity",
    )
    try:
        return all(
            _common.canonical_json_bytes_v1(refreshed[field])
            == _common.canonical_json_bytes_v1(precheck_observation.get(field))
            for field in compared_fields
        )
    except (TypeError, ValueError):
        return False


def _empty_process_observation_v1(termination_kind):
    empty = b""
    empty_sha = hashlib.sha256(empty).hexdigest()
    return {
        "replay_termination_kind": termination_kind,
        "replay_exit_code": None,
        "replay_signal_number": None,
        "replay_stdout_bytes": empty,
        "replay_stderr_bytes": empty,
        "replay_stdout_sha256": empty_sha,
        "replay_stderr_sha256": empty_sha,
        "process_cleanup_deadline_exceeded": False,
    }


def _process_observation_v1(
    termination_kind,
    exit_code,
    signal_number,
    stdout_bytes,
    stderr_bytes,
    cleanup_deadline_exceeded,
):
    return {
        "replay_termination_kind": termination_kind,
        "replay_exit_code": exit_code,
        "replay_signal_number": signal_number,
        "replay_stdout_bytes": stdout_bytes,
        "replay_stderr_bytes": stderr_bytes,
        "replay_stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
        "replay_stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
        "process_cleanup_deadline_exceeded": cleanup_deadline_exceeded,
    }


def _validate_bounded_process_configuration_v1(
    argv,
    cwd,
    environment,
    timeout_seconds,
    stdout_hard_cap_bytes,
    stderr_hard_cap_bytes,
    io_chunk_bytes,
    term_grace_seconds,
    kill_grace_seconds,
    final_pipe_close_deadline_seconds,
):
    if (
        type(argv) is not tuple
        or not argv
        or any(type(item) is not str or not item for item in argv)
    ):
        raise TypeError("reviewer argv must be a non-empty tuple of exact strings")
    if type(cwd) is not str or not cwd:
        raise TypeError("reviewer cwd must be a non-empty exact string")
    if type(environment) is not dict or any(
        type(key) is not str or type(value) is not str
        for key, value in environment.items()
    ):
        raise TypeError("reviewer environment must be an exact str-to-str dict")
    if type(timeout_seconds) not in (int, float) or timeout_seconds <= 0.0:
        raise ValueError("reviewer timeout must be a positive int or float")
    for name, value in (
        ("stdout_hard_cap_bytes", stdout_hard_cap_bytes),
        ("stderr_hard_cap_bytes", stderr_hard_cap_bytes),
        ("io_chunk_bytes", io_chunk_bytes),
    ):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive exact int")
    for name, value in (
        ("term_grace_seconds", term_grace_seconds),
        ("kill_grace_seconds", kill_grace_seconds),
        ("final_pipe_close_deadline_seconds", final_pipe_close_deadline_seconds),
    ):
        if type(value) not in (int, float) or value <= 0.0:
            raise ValueError(f"{name} must be a positive int or float")


def run_bounded_reviewer_process_v1(
    *,
    argv,
    cwd,
    environment,
    timeout_seconds,
    stdout_hard_cap_bytes,
    stderr_hard_cap_bytes,
    io_chunk_bytes,
    term_grace_seconds,
    kill_grace_seconds,
    final_pipe_close_deadline_seconds,
    python_precheck_observation=None,
):
    """Run one reviewer child with bounded nonblocking pipes and cleanup."""

    import os
    import selectors
    import signal
    import subprocess
    import time

    _validate_bounded_process_configuration_v1(
        argv,
        cwd,
        environment,
        timeout_seconds,
        stdout_hard_cap_bytes,
        stderr_hard_cap_bytes,
        io_chunk_bytes,
        term_grace_seconds,
        kill_grace_seconds,
        final_pipe_close_deadline_seconds,
    )
    timeout_seconds = float(timeout_seconds)
    term_grace_seconds = float(term_grace_seconds)
    kill_grace_seconds = float(kill_grace_seconds)
    final_pipe_close_deadline_seconds = float(final_pipe_close_deadline_seconds)
    if python_precheck_observation is not None:
        v2_identity = (
            type(python_precheck_observation) is dict
            and python_precheck_observation.get("profile_id")
            == "v3m0-b7-python-venv-invocation-identity-v1"
        )
        if v2_identity:
            identity_passed = python_precheck_observation.get(
                "python_invocation_path"
            ) == argv[0] and recheck_python_invocation_identity_v2(
                precheck_observation=python_precheck_observation,
            )
        else:
            identity_passed = (
                type(python_precheck_observation) is dict
                and python_precheck_observation.get("observed_realpath") == argv[0]
                and recheck_frozen_python_executable_identity_v1(
                    recorded_realpath=argv[0],
                    precheck_observation=python_precheck_observation,
                )
            )
        if not identity_passed:
            return _empty_process_observation_v1("PRECHECK_FAILED")
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
    except OSError:
        return _empty_process_observation_v1("SPAWN_FAILED")
    if process.stdout is None or process.stderr is None:
        raise AssertionError("reviewer pipes were not created")

    streams = {
        "stdout": {
            "pipe": process.stdout,
            "buffer": bytearray(),
            "cap": stdout_hard_cap_bytes,
        },
        "stderr": {
            "pipe": process.stderr,
            "buffer": bytearray(),
            "cap": stderr_hard_cap_bytes,
        },
    }
    selector = selectors.DefaultSelector()
    for name, state in streams.items():
        pipe = state["pipe"]
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ, name)

    overflow = False

    def drain_once(wait_seconds):
        nonlocal overflow
        for key, _mask in selector.select(wait_seconds):
            state = streams[key.data]
            buffer = state["buffer"]
            remaining = state["cap"] - len(buffer)
            read_size = min(io_chunk_bytes, remaining + 1)
            try:
                chunk = os.read(key.fileobj.fileno(), read_size)
            except BlockingIOError:
                continue
            if not chunk:
                try:
                    selector.unregister(key.fileobj)
                except KeyError:
                    pass
                continue
            if len(chunk) > remaining:
                buffer.extend(chunk[:remaining])
                overflow = True
            else:
                buffer.extend(chunk)

    overall_deadline = time.monotonic() + timeout_seconds
    forced_kind = None
    while True:
        if overflow:
            forced_kind = "OUTPUT_LIMIT_EXCEEDED"
            break
        return_code = process.poll()
        if return_code is not None and not selector.get_map():
            break
        remaining = overall_deadline - time.monotonic()
        if remaining <= 0.0:
            forced_kind = "TIMED_OUT"
            break
        drain_once(min(remaining, 0.05))

    cleanup_deadline_exceeded = False
    if forced_kind is not None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
        term_deadline = time.monotonic() + term_grace_seconds
        while process.poll() is None and time.monotonic() < term_deadline:
            drain_once(min(term_deadline - time.monotonic(), 0.05))
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            kill_deadline = time.monotonic() + kill_grace_seconds
            while process.poll() is None and time.monotonic() < kill_deadline:
                drain_once(min(kill_deadline - time.monotonic(), 0.05))
        cleanup_deadline_exceeded = process.poll() is None

    close_deadline = time.monotonic() + final_pipe_close_deadline_seconds
    while selector.get_map() and time.monotonic() < close_deadline:
        wait = min(close_deadline - time.monotonic(), 0.05)
        drain_once(wait)
        if overflow and forced_kind is None:
            forced_kind = "OUTPUT_LIMIT_EXCEEDED"
            break
    for state in streams.values():
        try:
            selector.unregister(state["pipe"])
        except KeyError:
            pass
        state["pipe"].close()
    selector.close()

    stdout_bytes = bytes(streams["stdout"]["buffer"])
    stderr_bytes = bytes(streams["stderr"]["buffer"])
    if forced_kind is not None:
        return _process_observation_v1(
            forced_kind,
            None,
            None,
            stdout_bytes,
            stderr_bytes,
            cleanup_deadline_exceeded,
        )
    return_code = process.poll()
    if return_code is None:
        return _process_observation_v1(
            "TIMED_OUT",
            None,
            None,
            stdout_bytes,
            stderr_bytes,
            True,
        )
    if return_code < 0:
        return _process_observation_v1(
            "SIGNALED",
            None,
            -return_code,
            stdout_bytes,
            stderr_bytes,
            False,
        )
    return _process_observation_v1(
        "EXITED",
        return_code,
        None,
        stdout_bytes,
        stderr_bytes,
        False,
    )


def run_python_environment_import_probe_v2(
    *,
    python_invocation_path,
    python_identity_observation,
):
    """Run and strictly decode the bounded v9.2 NumPy/SciPy import probe."""

    invocation = _require_normalized_absolute_path_v2(
        python_invocation_path,
        "Python invocation",
    )
    invalid = {
        "probe_passed": False,
        "process_observation": _empty_process_observation_v1("PRECHECK_FAILED"),
        "report": None,
    }
    if (
        type(python_identity_observation) is not dict
        or python_identity_observation.get("precheck_passed") is not True
        or python_identity_observation.get("python_invocation_path") != invocation
        or not recheck_python_invocation_identity_v2(
            precheck_observation=python_identity_observation,
        )
    ):
        return invalid
    process_observation = run_bounded_reviewer_process_v1(
        argv=(
            invocation,
            "-s",
            "-c",
            _PYTHON_ENVIRONMENT_IMPORT_PROBE_UTF8_V2,
        ),
        cwd=python_identity_observation["recorded_venv_prefix"],
        environment=build_sanitized_reviewer_environment_v1(),
        timeout_seconds=_PYTHON_ENVIRONMENT_PROBE_TIMEOUT_SECONDS_V2,
        stdout_hard_cap_bytes=(_PYTHON_ENVIRONMENT_PROBE_STDOUT_HARD_CAP_BYTES_V2),
        stderr_hard_cap_bytes=(_PYTHON_ENVIRONMENT_PROBE_STDERR_HARD_CAP_BYTES_V2),
        io_chunk_bytes=REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
        term_grace_seconds=REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
        kill_grace_seconds=REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
        final_pipe_close_deadline_seconds=(
            REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1
        ),
        python_precheck_observation=python_identity_observation,
    )
    if not (
        process_observation["replay_termination_kind"] == "EXITED"
        and process_observation["replay_exit_code"] == 0
        and process_observation["replay_signal_number"] is None
        and process_observation["replay_stderr_bytes"] == b""
        and process_observation["process_cleanup_deadline_exceeded"] is False
    ):
        return {
            "probe_passed": False,
            "process_observation": process_observation,
            "report": None,
        }
    stdout_bytes = process_observation["replay_stdout_bytes"]
    try:
        if (
            not stdout_bytes.endswith(b"\n")
            or b"\n" in stdout_bytes[:-1]
            or not stdout_bytes[:-1]
        ):
            raise ValueError("environment probe stdout framing drifted")
        payload = stdout_bytes[:-1]
        report = _common.strict_json_loads_v1(payload)
        if (
            not _python_environment_probe_report_is_well_typed_v2(report)
            or _common.canonical_json_bytes_v1(report) != payload
            or report["python_invocation_path"] != invocation
            or report["python_executable_realpath"]
            != python_identity_observation["recorded_realpath"]
            or report["python_venv_prefix"]
            != python_identity_observation["recorded_venv_prefix"]
        ):
            raise ValueError("environment probe report identity drifted")
    except (KeyError, TypeError, ValueError):
        return {
            "probe_passed": False,
            "process_observation": process_observation,
            "report": None,
        }
    return {
        "probe_passed": True,
        "process_observation": process_observation,
        "report": report,
    }


def capture_environment_manifest_v2(*, python_invocation_path):
    """Capture one complete live EnvironmentManifestV2 from a venv invocation."""

    invocation = _require_normalized_absolute_path_v2(
        python_invocation_path,
        "Python invocation",
    )
    _ordered_hops, observed_target, chain_complete = (
        _resolve_python_invocation_chain_v2(invocation)
    )
    if not chain_complete or observed_target is None or observed_target == invocation:
        raise ValueError("environment capture requires a resolved venv invocation")
    target_observation = _stable_regular_file_observation_v2(
        observed_target,
        executable_required=True,
    )
    observed_cfg, observed_prefix, cfg_observation = _nearest_pyvenv_cfg_v2(invocation)
    if (
        target_observation["stable"] is not True
        or target_observation["raw_sha256"] is None
        or observed_cfg is None
        or observed_prefix is None
        or cfg_observation is None
        or cfg_observation["stable"] is not True
        or cfg_observation["raw_sha256"] is None
    ):
        raise ValueError("environment capture identity observation is incomplete")
    identity = precheck_python_invocation_identity_v2(
        python_invocation_path=invocation,
        recorded_realpath=observed_target,
        recorded_raw_sha256=target_observation["raw_sha256"],
        recorded_venv_prefix=observed_prefix,
        recorded_pyvenv_cfg_path=observed_cfg,
        recorded_pyvenv_cfg_raw_sha256=cfg_observation["raw_sha256"],
    )
    if identity["precheck_passed"] is not True:
        raise ValueError("environment capture identity changed during observation")
    probe = run_python_environment_import_probe_v2(
        python_invocation_path=invocation,
        python_identity_observation=identity,
    )
    if probe["probe_passed"] is not True:
        raise ValueError("environment capture import probe failed")
    report = probe["report"]
    manifest = {
        "environment_schema_version": "experimental.v3m0.b7.environment-manifest.v2",
        "python_implementation": report["python_implementation"],
        "python_version": report["python_version"],
        "python_invocation_path": invocation,
        "python_executable_realpath": observed_target,
        "python_executable_raw_sha256": target_observation["raw_sha256"],
        "python_invocation_identity_sha": identity["python_invocation_identity_sha"],
        "python_venv_prefix": observed_prefix,
        "python_pyvenv_cfg_path": observed_cfg,
        "python_pyvenv_cfg_raw_sha256": cfg_observation["raw_sha256"],
        "numpy_version": report["numpy_version"],
        "scipy_version": report["scipy_version"],
        "platform_system": report["platform_system"],
        "platform_release": report["platform_release"],
        "platform_machine": report["platform_machine"],
        "numpy_float64_dtype_str": report["numpy_float64_dtype_str"],
        "numpy_float64_itemsize": report["numpy_float64_itemsize"],
        "byteorder": report["byteorder"],
        "python_hash_seed": "0",
        "blas_thread_settings": [
            ["OPENBLAS_NUM_THREADS", "1"],
            ["OMP_NUM_THREADS", "1"],
            ["MKL_NUM_THREADS", "1"],
            ["VECLIB_MAXIMUM_THREADS", "1"],
            ["NUMEXPR_NUM_THREADS", "1"],
        ],
        "threadpool_info": report["threadpool_info"],
        "fresh_process_per_capture": True,
        "environment_sha": "",
    }
    manifest["environment_sha"] = _common.canonical_sha_v1(
        {
            field: value
            for field, value in manifest.items()
            if field != "environment_sha"
        }
    )
    return _common.validate_environment_manifest_v2(
        manifest,
        python_identity_observation=identity,
        python_probe_result=probe,
    )


def run_frozen_reviewer_process_v1(
    *,
    argv,
    cwd,
    environment,
    recorded_python_raw_sha256,
):
    """Run one reviewer child with the exact frozen v9.1 process limits."""

    if type(argv) is not tuple or not argv or type(argv[0]) is not str:
        raise TypeError("frozen reviewer argv must contain its Python realpath")
    python_precheck_observation = precheck_frozen_python_executable_v1(
        recorded_realpath=argv[0],
        recorded_raw_sha256=recorded_python_raw_sha256,
    )
    if python_precheck_observation["precheck_passed"] is not True:
        return _empty_process_observation_v1("PRECHECK_FAILED")

    return run_bounded_reviewer_process_v1(
        argv=argv,
        cwd=cwd,
        environment=environment,
        timeout_seconds=REVIEWER_PROCESS_TIMEOUT_SECONDS_V1,
        stdout_hard_cap_bytes=REVIEWER_PROCESS_STDOUT_HARD_CAP_BYTES_V1,
        stderr_hard_cap_bytes=REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1,
        io_chunk_bytes=REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
        term_grace_seconds=REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
        kill_grace_seconds=REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
        final_pipe_close_deadline_seconds=(
            REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1
        ),
        python_precheck_observation=python_precheck_observation,
    )


def run_frozen_reviewer_process_v2(
    *,
    argv,
    cwd,
    environment,
    environment_manifest,
):
    """Run one active reviewer only after the complete v9.2 environment join."""

    _validate_bounded_process_configuration_v1(
        argv,
        cwd,
        environment,
        REVIEWER_PROCESS_TIMEOUT_SECONDS_V1,
        REVIEWER_PROCESS_STDOUT_HARD_CAP_BYTES_V1,
        REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1,
        REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
        REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
        REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
        REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1,
    )
    if environment != build_sanitized_reviewer_environment_v1():
        return _empty_process_observation_v1("PRECHECK_FAILED")
    try:
        manifest = _common.validate_exact_lab_record_v1(
            "B7LabEnvironmentManifestV2",
            environment_manifest,
        )
        if argv[0] != manifest["python_invocation_path"]:
            return _empty_process_observation_v1("PRECHECK_FAILED")
        python_precheck_observation = precheck_python_invocation_identity_v2(
            python_invocation_path=manifest["python_invocation_path"],
            recorded_realpath=manifest["python_executable_realpath"],
            recorded_raw_sha256=manifest["python_executable_raw_sha256"],
            recorded_venv_prefix=manifest["python_venv_prefix"],
            recorded_pyvenv_cfg_path=manifest["python_pyvenv_cfg_path"],
            recorded_pyvenv_cfg_raw_sha256=(manifest["python_pyvenv_cfg_raw_sha256"]),
        )
        if python_precheck_observation["precheck_passed"] is not True:
            return _empty_process_observation_v1("PRECHECK_FAILED")
        python_probe_result = run_python_environment_import_probe_v2(
            python_invocation_path=manifest["python_invocation_path"],
            python_identity_observation=python_precheck_observation,
        )
        _common.validate_environment_manifest_v2(
            manifest,
            python_identity_observation=python_precheck_observation,
            python_probe_result=python_probe_result,
        )
    except (KeyError, OSError, TypeError, ValueError):
        return _empty_process_observation_v1("PRECHECK_FAILED")

    return run_bounded_reviewer_process_v1(
        argv=argv,
        cwd=cwd,
        environment=environment,
        timeout_seconds=REVIEWER_PROCESS_TIMEOUT_SECONDS_V1,
        stdout_hard_cap_bytes=REVIEWER_PROCESS_STDOUT_HARD_CAP_BYTES_V1,
        stderr_hard_cap_bytes=REVIEWER_PROCESS_STDERR_HARD_CAP_BYTES_V1,
        io_chunk_bytes=REVIEWER_PROCESS_IO_CHUNK_BYTES_V1,
        term_grace_seconds=REVIEWER_PROCESS_TERM_GRACE_SECONDS_V1,
        kill_grace_seconds=REVIEWER_PROCESS_KILL_GRACE_SECONDS_V1,
        final_pipe_close_deadline_seconds=(
            REVIEWER_PROCESS_FINAL_PIPE_CLOSE_DEADLINE_SECONDS_V1
        ),
        python_precheck_observation=python_precheck_observation,
    )


if __name__ == "__main__":
    raise SystemExit(main())
