"""Task-7 contracts for the B7 owner-neutral schema-lab common layer."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import inspect
import json
from pathlib import Path

import pytest

from rulespace_v3.b7_replay_core_v1 import (
    canonical_json_bytes_v1,
    canonical_sha_v1,
    strict_json_loads_v1,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPOSITORY_ROOT / "experiments" / "v3m0_b7_schema_lab"
INITIALIZER_PATH = LAB_ROOT / "__init__.py"
COMMON_PATH = LAB_ROOT / "common.py"
COMPARE_PATH = LAB_ROOT / "compare.py"
REGISTRY_PATH = REPOSITORY_ROOT / "docsv3" / "v3-机器合同-B7-v9.1-registry.json"

PURE_VALIDATOR_SIGNATURES = {
    "validate_response_run_spec_fixture_v1": (
        "raw_body",
        "provenance_raw",
        "graph_raw",
    ),
    "validate_endpoint_reference_outcome_raw_v1": ("raw_body",),
    "validate_endpoint_shell_outcome_raw_v1": ("raw_body",),
    "validate_source_readout_response_raw_v1": (
        "raw_body",
        "run_spec_raw",
        "provenance_raw",
        "graph_raw",
    ),
    "validate_synthetic_parent_freeze_v3_body_v1": ("raw_body",),
    "validate_synthetic_component_body_v1": (
        "raw_body",
        "ordered_components_raw",
        "parent_raw",
    ),
    "validate_provenance_fixture_v1": ("raw_body",),
    "validate_branch_attempt_v1": ("raw_body",),
}

D0_FIELD_ORDER = (
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
D0_PROJECTION_ORDER = D0_FIELD_ORDER[:11]
D1_FIELD_ORDER = (
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
D1_PROJECTION_ORDER = (
    D1_FIELD_ORDER[0],
    *D1_FIELD_ORDER[3:21],
)


def _common_module():
    return importlib.import_module("experiments.v3m0_b7_schema_lab.common")


def test_lab_initializer_is_exact_empty_blob() -> None:
    assert INITIALIZER_PATH.is_file()
    assert INITIALIZER_PATH.read_bytes() == b""


def test_common_exposes_exact_thin_pure_core_validator_signatures() -> None:
    common = _common_module()

    for symbol, expected_parameters in PURE_VALIDATOR_SIGNATURES.items():
        wrapper = getattr(common, symbol)
        assert tuple(inspect.signature(wrapper).parameters) == expected_parameters


def test_common_pure_validator_wrappers_are_single_static_delegations() -> None:
    tree = ast.parse(COMMON_PATH.read_text(encoding="utf-8"))
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }

    for symbol, expected_parameters in PURE_VALIDATOR_SIGNATURES.items():
        function = functions[symbol]
        assert function.decorator_list == []
        assert tuple(argument.arg for argument in function.args.args) == (
            expected_parameters
        )
        assert function.args.defaults == []
        assert function.args.kwonlyargs == []
        assert function.args.vararg is None
        assert function.args.kwarg is None
        statements = function.body
        assert len(statements) == 2
        assert isinstance(statements[0], ast.Expr)
        assert isinstance(statements[0].value, ast.Constant)
        assert isinstance(statements[0].value.value, str)
        returned = statements[1]
        assert isinstance(returned, ast.Return)
        assert isinstance(returned.value, ast.Call)
        assert isinstance(returned.value.func, ast.Attribute)
        assert isinstance(returned.value.func.value, ast.Name)
        assert returned.value.func.value.id == "_pure_core"
        assert returned.value.func.attr == symbol
        assert (
            tuple(
                argument.id
                for argument in returned.value.args
                if isinstance(argument, ast.Name)
            )
            == expected_parameters
        )
        assert returned.value.keywords == []


def test_synthetic_graph_manifest_validator_delegates_complete_embedded_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common_module()
    parent = {"parent_freeze_v3_sha": "1" * 64}
    graph = {"parent_freeze_v3_body": parent}
    calls: list[tuple[object, object]] = []

    def validate(raw_graph: object, raw_parent: object) -> object:
        calls.append((raw_graph, raw_parent))
        return raw_graph

    monkeypatch.setattr(common._pure_core, "_validate_synthetic_graph_raw_v1", validate)

    assert common.validate_synthetic_graph_manifest_v1(graph) is graph
    assert calls == [(graph, parent)]


@pytest.mark.parametrize("hostile", (None, [], {}, {"parent_freeze_v3_body": None}))
def test_synthetic_graph_manifest_validator_rejects_missing_embedded_parent(
    hostile: object,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        _common_module().validate_synthetic_graph_manifest_v1(hostile)


def test_common_imports_no_production_authority_owner() -> None:
    tree = ast.parse(COMMON_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module)

    assert imported == ["__future__", "rulespace_v3.b7_replay_core_v1"]
    forbidden_tokens = ("authority", "issuer", "hydrate", "promote", "seal")
    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            lowered = node.arg.casefold()
            assert not any(token in lowered for token in forbidden_tokens)


def test_common_mechanically_freezes_all_v91_exact_record_catalogs() -> None:
    common = _common_module()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    expected_records = registry["lab_contract"]["exact_records"]

    observed = {}
    for (
        record_name,
        schema_id,
        self_hash_field,
        field_specs,
    ) in common.LAB_EXACT_RECORD_CATALOGS_V1:
        observed[record_name] = {
            "schema_id": schema_id,
            "self_hash_field": self_hash_field,
            "field_specs": [
                {
                    "name": name,
                    "wire_type": wire_type,
                    "presence": presence,
                    "nested_record": nested_record,
                }
                for name, wire_type, presence, nested_record in field_specs
            ],
        }

    expected = {
        record_name: {
            "schema_id": contract["schema_id"],
            "self_hash_field": (
                None
                if record_name == "B7LeafDigestV1"
                else contract["field_specs"][-1]["name"]
            ),
            "field_specs": contract["field_specs"],
        }
        for record_name, contract in expected_records.items()
    }
    assert len(observed) == 29
    assert observed == expected


@pytest.mark.parametrize(
    ("wire_type", "legal", "hostile"),
    (
        ("branch-failure", "actual_response_failed", "NOT_A_FAILURE"),
        ("case-id", "success", "NOT_A_CASE"),
        ("expected-boundary", "TRANSCRIPT_CONSTRUCTION", "NOT_A_BOUNDARY"),
        ("gate-id", "E05", "E99"),
        ("metric-id", "canonical_wire_bytes", "wall_time"),
        ("mutation-class", "TERMINAL_TAG", "NOT_A_CLASS"),
        ("mutation-operation", "SET_VALUE", "EXECUTE"),
        ("probe-kind", "MUTATION_MUST_REJECT", "MAY_ACCEPT"),
        ("review-protocol-id", "v3m0-b7-corpus-replay-v1", "review-anything"),
        ("route-domain", "experimental.v3m0.b7.a-flat", "production.route"),
        ("route-id", "A_FLAT", "NOT_A_ROUTE"),
        (
            "route-wire-schema-id",
            "experimental.v3m0.b7.a-flat.wire.v1",
            "production.wire.v1",
        ),
        ("scheduler-stage-id", "reference", "shell_again"),
        ("synthetic-graph-component-id", "permit", "hidden_component"),
        ("terminal-tag", "success", "partial_success"),
        ("validator-id", "validate_gate_e01_v1", "accept_everything"),
    ),
)
def test_lab_semantic_wire_domains_are_exact_registry_sets(
    wire_type: str,
    legal: str,
    hostile: str,
) -> None:
    validate = _common_module()._validate_lab_wire_semantics_v1

    validate(legal, wire_type, None, "field")
    with pytest.raises((TypeError, ValueError)):
        validate(hostile, wire_type, None, "field")


@pytest.mark.parametrize(
    ("wire_type", "legal", "hostile"),
    (
        ("absolute-normalized-path", "/opt/python/bin/python3", "//opt/python"),
        ("absolute-normalized-path", "/opt/python/bin/python3", "/opt/../evil"),
        (
            "fully-qualified-type-name",
            "rulespace_v3.response.EndpointShellOutcome",
            "rulespace-v3.response.EndpointShellOutcome",
        ),
        ("json-pointer", "", "relative/path"),
        ("json-pointer", "/a~1b", "/a~2b"),
        ("module-name", "experiments.v3m0_b7_schema_lab.a_flat", "a/../b"),
        ("repo-relative-posix-path", "experiments/a.py", "/experiments/a.py"),
        ("repo-relative-posix-path", "experiments/a.py", "experiments/../a.py"),
    ),
)
def test_lab_semantic_wire_paths_are_normalized(
    wire_type: str,
    legal: str,
    hostile: str,
) -> None:
    validate = _common_module()._validate_lab_wire_semantics_v1

    validate(legal, wire_type, None, "field")
    with pytest.raises((TypeError, ValueError)):
        validate(hostile, wire_type, None, "field")


def _seal(raw: dict[str, object], hash_field: str) -> dict[str, object]:
    raw[hash_field] = canonical_sha_v1(
        {name: value for name, value in raw.items() if name != hash_field}
    )
    return raw


def _environment_manifest() -> dict[str, object]:
    return _seal(
        {
            "environment_schema_version": (
                "experimental.v3m0.b7.environment-manifest.v1"
            ),
            "python_implementation": "CPython",
            "python_version": "3.13.5",
            "python_executable_realpath": "/opt/python/bin/python3",
            "python_executable_raw_sha256": "1" * 64,
            "numpy_version": "2.3.1",
            "scipy_version": "1.16.0",
            "platform_system": "Darwin",
            "platform_release": "24.5.0",
            "platform_machine": "arm64",
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


def _corpus_case(case_id: str) -> dict[str, object]:
    rows = {
        "reference_failure": (
            0,
            "reference_failure",
            "reference",
            "000000000",
            None,
            None,
            ["reference"],
        ),
        "shell_failure": (
            1,
            "shell_failure",
            "shell",
            "100000000",
            None,
            None,
            ["reference", "shell"],
        ),
        "actual_response_values_failure": (
            2,
            "actual_response_values_failure",
            "actual_response_values",
            "110000000",
            "actual_response_failed",
            None,
            ["reference", "shell", "actual_response_values"],
        ),
        "matched_response_values_failure": (
            3,
            "matched_response_values_failure",
            "matched_ablated_response_values",
            "111100000",
            None,
            "matched_ablated_response_failed",
            [
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
            ],
        ),
        "actual_bridge_failure": (
            4,
            "actual_bridge_failure",
            "actual_bridge",
            "111110000",
            "actual_bridge_failed",
            None,
            [
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
                "actual_bridge",
            ],
        ),
        "matched_bridge_failure": (
            5,
            "matched_bridge_failure",
            "matched_ablated_bridge",
            "111111000",
            None,
            "matched_ablated_bridge_failed",
            [
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
                "actual_bridge",
                "matched_ablated_bridge",
            ],
        ),
        "success": (
            6,
            "success",
            None,
            "111111111",
            None,
            None,
            [
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
                "actual_bridge",
                "matched_ablated_bridge",
            ],
        ),
    }
    (
        ordinal,
        terminal_tag,
        injected_stage,
        presence_bits,
        actual_failure,
        matched_failure,
        trace,
    ) = rows[case_id]
    return _seal(
        {
            "case_schema_version": "experimental.v3m0.b7.corpus-case.v1",
            "case_ordinal": ordinal,
            "case_id": case_id,
            "terminal_tag": terminal_tag,
            "injected_failure_stage": injected_stage,
            "presence_bits": presence_bits,
            "actual_attempt_failure": actual_failure,
            "matched_ablated_attempt_failure": matched_failure,
            "expected_callback_trace": trace,
            "expected_leaf_ids": list(trace),
            "case_sha": "",
        },
        "case_sha",
    )


def _nested_rule() -> dict[str, object]:
    return _seal(
        {
            "rule_schema_version": "experimental.v3m0.b7.nested-body-rule.v1",
            "json_pointer": "/shell_outcome",
            "body_kind": "rulespace_v3.response.EndpointShellOutcome",
            "hash_field": "outcome_sha",
            "nullable": True,
            "full_body_required": True,
            "rule_sha": "",
        },
        "rule_sha",
    )


def _seal_mutation_identity(raw: dict[str, object]) -> dict[str, object]:
    projection = {
        name: raw[name]
        for name in (
            "base_case_id",
            "probe_kind",
            "mutation_class",
            "target_json_pointer",
            "operation",
            "replacement_json",
            "expected_boundary",
        )
    }
    case_token = "GLOBAL" if raw["base_case_id"] is None else raw["base_case_id"]
    raw["mutation_id"] = (
        f"M{raw['mutation_ordinal']:06d}-{raw['mutation_class']}-{case_token}-"
        f"{canonical_sha_v1(projection)[:16]}"
    )
    return _seal(raw, "mutation_sha")


def _mutation() -> dict[str, object]:
    return _seal_mutation_identity(
        {
            "mutation_schema_version": "experimental.v3m0.b7.mutation.v1",
            "mutation_ordinal": 0,
            "mutation_id": "M000000-TERMINAL_TAG-success-0123456789abcdef",
            "base_case_id": "success",
            "probe_kind": "MUTATION_MUST_REJECT",
            "mutation_class": "TERMINAL_TAG",
            "target_json_pointer": "/terminal_tag",
            "operation": "SET_VALUE",
            "replacement_json": "reference_failure",
            "expected_boundary": "ROUTE_VERIFICATION",
            "mutation_sha": "",
        },
    )


def _metric_vector() -> dict[str, object]:
    return _seal(
        {
            "mutation_accept_count": 0,
            "evidence_loss_count": 0,
            "constructible_invalid_presence_count": 0,
            "half_pair_state_count": 0,
            "b8_consumer_assertion_count": 8,
            "b8_consumer_changed_loc": 0,
            "verifier_branch_count": 7,
            "route_record_count": 1,
            "route_hash_layer_count": 1,
            "canonical_wire_bytes": 4096,
            "metric_vector_sha": "",
        },
        "metric_vector_sha",
    )


@pytest.mark.parametrize(
    ("symbol", "factory"),
    (
        ("validate_environment_manifest_v1", _environment_manifest),
        ("validate_corpus_case_v1", lambda: _corpus_case("success")),
        ("validate_nested_body_rule_v1", _nested_rule),
        ("validate_mutation_v1", _mutation),
        ("validate_metric_vector_v1", _metric_vector),
    ),
)
def test_common_basic_record_validators_accept_detached_minimal_bodies(
    symbol: str,
    factory,
) -> None:
    validator = getattr(_common_module(), symbol)
    raw = factory()

    observed = validator(copy.deepcopy(raw))

    assert observed == raw
    assert observed is not raw


@pytest.mark.parametrize(
    ("symbol", "factory"),
    (
        ("validate_environment_manifest_v1", _environment_manifest),
        ("validate_corpus_case_v1", lambda: _corpus_case("success")),
        ("validate_nested_body_rule_v1", _nested_rule),
        ("validate_mutation_v1", _mutation),
        ("validate_metric_vector_v1", _metric_vector),
    ),
)
def test_common_basic_record_validators_accept_canonical_wire_and_are_idempotent(
    symbol: str,
    factory,
) -> None:
    validator = getattr(_common_module(), symbol)
    decoded = strict_json_loads_v1(canonical_json_bytes_v1(factory()))

    first = validator(decoded)
    second = validator(first)

    assert second == first


@pytest.mark.parametrize(
    ("symbol", "factory", "typed_field", "bad_value"),
    (
        (
            "validate_environment_manifest_v1",
            _environment_manifest,
            "numpy_float64_itemsize",
            True,
        ),
        (
            "validate_corpus_case_v1",
            lambda: _corpus_case("success"),
            "case_ordinal",
            True,
        ),
        (
            "validate_nested_body_rule_v1",
            _nested_rule,
            "nullable",
            1,
        ),
        (
            "validate_mutation_v1",
            _mutation,
            "mutation_ordinal",
            True,
        ),
        (
            "validate_metric_vector_v1",
            _metric_vector,
            "canonical_wire_bytes",
            True,
        ),
    ),
)
def test_common_basic_record_validators_reject_shape_type_and_self_hash_attacks(
    symbol: str,
    factory,
    typed_field: str,
    bad_value: object,
) -> None:
    validator = getattr(_common_module(), symbol)
    legal = factory()
    hash_field = next(reversed(legal))
    extra = copy.deepcopy(legal)
    extra["unexpected"] = None
    wrong_type = copy.deepcopy(legal)
    wrong_type[typed_field] = bad_value
    _seal(wrong_type, hash_field)
    wrong_hash = copy.deepcopy(legal)
    wrong_hash[hash_field] = "0" * 64

    for hostile in (extra, wrong_type, wrong_hash):
        with pytest.raises((TypeError, ValueError)):
            validator(hostile)


def test_common_basic_record_validators_reject_schema_and_domain_drift() -> None:
    common = _common_module()
    wrong_schema = _environment_manifest()
    wrong_schema["environment_schema_version"] = "experimental.v3m0.b7.bad.v1"
    _seal(wrong_schema, "environment_sha")
    wrong_case = _corpus_case("success")
    wrong_case["terminal_tag"] = "reference_failure"
    _seal(wrong_case, "case_sha")
    wrong_pointer = _nested_rule()
    wrong_pointer["json_pointer"] = "shell_outcome"
    _seal(wrong_pointer, "rule_sha")
    wrong_mutation = _mutation()
    wrong_mutation["mutation_class"] = "UNKNOWN"
    _seal_mutation_identity(wrong_mutation)

    attacks = (
        (common.validate_environment_manifest_v1, wrong_schema),
        (common.validate_corpus_case_v1, wrong_case),
        (common.validate_nested_body_rule_v1, wrong_pointer),
        (common.validate_mutation_v1, wrong_mutation),
    )
    for validator, hostile in attacks:
        with pytest.raises((TypeError, ValueError)):
            validator(hostile)


@pytest.mark.parametrize(
    (
        "probe_kind",
        "mutation_class",
        "operation",
        "expected_boundary",
        "base_case_id",
    ),
    (
        (
            "ROUNDTRIP_MUST_EQUAL",
            "CANONICAL_ROUNDTRIP",
            "REENCODE",
            "EQUALITY_CHECK",
            "success",
        ),
        (
            "REPEAT_MUST_EQUAL",
            "CANONICAL_REPEAT",
            "REPEAT",
            "EQUALITY_CHECK",
            "success",
        ),
        (
            "UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT",
            "UPSTREAM_INVALID",
            "RAISE_UPSTREAM",
            "UPSTREAM_JOIN",
            None,
        ),
    ),
)
def test_mutation_validator_accepts_exact_empty_pointer_global_operations(
    probe_kind: str,
    mutation_class: str,
    operation: str,
    expected_boundary: str,
    base_case_id: str | None,
) -> None:
    raw = _mutation()
    raw.update(
        {
            "base_case_id": base_case_id,
            "probe_kind": probe_kind,
            "mutation_class": mutation_class,
            "target_json_pointer": "",
            "operation": operation,
            "replacement_json": None,
            "expected_boundary": expected_boundary,
        }
    )
    _seal_mutation_identity(raw)

    assert _common_module().validate_mutation_v1(raw) == raw


def test_mutation_validator_pointer_domain_and_boundary_enum_are_exact() -> None:
    common = _common_module()
    construction = _mutation()
    construction["expected_boundary"] = "TRANSCRIPT_CONSTRUCTION"
    _seal_mutation_identity(construction)
    assert common.validate_mutation_v1(construction) == construction

    rooted_operation_with_empty_pointer = _mutation()
    rooted_operation_with_empty_pointer["target_json_pointer"] = ""
    _seal_mutation_identity(rooted_operation_with_empty_pointer)
    global_operation_with_rooted_pointer = _mutation()
    global_operation_with_rooted_pointer.update(
        {
            "probe_kind": "ROUNDTRIP_MUST_EQUAL",
            "mutation_class": "CANONICAL_ROUNDTRIP",
            "target_json_pointer": "/terminal_tag",
            "operation": "REENCODE",
            "replacement_json": None,
            "expected_boundary": "EQUALITY_CHECK",
        }
    )
    _seal_mutation_identity(global_operation_with_rooted_pointer)

    for hostile in (
        rooted_operation_with_empty_pointer,
        global_operation_with_rooted_pointer,
    ):
        with pytest.raises((TypeError, ValueError)):
            common.validate_mutation_v1(hostile)


def test_mutation_validator_rejects_forged_projection_prefix() -> None:
    hostile = _mutation()
    hostile["mutation_id"] = "M000000-TERMINAL_TAG-success-ffffffffffffffff"
    _seal(hostile, "mutation_sha")

    with pytest.raises((TypeError, ValueError)):
        _common_module().validate_mutation_v1(hostile)


def test_generic_record_validator_rejects_semantic_id_type_confusion() -> None:
    hostile_leaf = {
        "leaf_id": 0,
        "call_ordinal": 0,
        "input_body_sha": "0" * 64,
        "output_body_sha": "1" * 64,
    }

    with pytest.raises((TypeError, ValueError)):
        _common_module()._validate_exact_lab_record_v1(
            "B7LeafDigestV1",
            hostile_leaf,
        )


def test_rfc6901_resolver_and_walk_freeze_escape_and_utf8_order() -> None:
    common = _common_module()
    raw = {
        "~": {"/": ["zero", {"β": 2, "a": 1}]},
        "a": 0,
    }

    assert common.resolve_json_pointer_v1(raw, "") is raw
    assert common.resolve_json_pointer_v1(raw, "/~0/~1/1/a") == 1
    assert tuple(
        pointer for pointer, _value in common.walk_json_pointer_items_v1(raw)
    ) == (
        "",
        "/a",
        "/~0",
        "/~0/~1",
        "/~0/~1/0",
        "/~0/~1/1",
        "/~0/~1/1/a",
        "/~0/~1/1/β",
    )

    for invalid in ("relative", "/~2", "/~", "/~0/~1/01", "/~0/~1/-"):
        with pytest.raises((TypeError, ValueError)):
            common.resolve_json_pointer_v1(raw, invalid)


def test_self_hash_snapshot_excludes_leaf_reference_hashes() -> None:
    common = _common_module()
    child = _seal(
        {
            "kind": "child",
            "child_sha": "",
        },
        "child_sha",
    )
    leaf = {
        "leaf_id": "reference",
        "call_ordinal": 0,
        "input_body_sha": canonical_sha_v1({"input": True}),
        "output_body_sha": canonical_sha_v1({"output": True}),
    }
    root = _seal(
        {
            "child": child,
            "ordered_leaf_digests": [leaf],
            "experimental_sha": "",
        },
        "experimental_sha",
    )

    assert common.discover_record_self_hashes_v1(root) == (
        ("", "experimental_sha"),
        ("/child", "child_sha"),
    )


def _seven_transcripts() -> list[dict[str, object]]:
    return [
        _transcript(case_id)
        for case_id in (
            "reference_failure",
            "shell_failure",
            "actual_response_values_failure",
            "matched_response_values_failure",
            "actual_bridge_failure",
            "matched_bridge_failure",
            "success",
        )
    ]


def _lab_registry() -> dict[str, object]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return registry["lab_contract"]


def _raw_sha256(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _metric_spec(
    common_source_bytes: bytes | None = None,
    compare_source_bytes: bytes | None = None,
) -> dict[str, object]:
    lab = _lab_registry()
    metric_algorithm = lab["metric_algorithm"]
    common_bytes = (
        COMMON_PATH.read_bytes() if common_source_bytes is None else common_source_bytes
    )
    compare_bytes = (
        COMPARE_PATH.read_bytes()
        if compare_source_bytes is None
        else compare_source_bytes
    )
    return _seal(
        {
            "metric_spec_schema_version": "experimental.v3m0.b7.metric-spec.v1",
            "metric_algorithm_id": metric_algorithm["algorithm_id"],
            "metric_contract_sha": canonical_sha_v1(metric_algorithm),
            "metric_order": copy.deepcopy(lab["metric_order"]),
            "evidence_pointer_order": copy.deepcopy(
                metric_algorithm["evidence_pointer_order"]
            ),
            "invalid_presence_bit_width": metric_algorithm["invalid_presence_domain"][
                "bit_width"
            ],
            "reachable_closure_algorithm_id": (
                "python-ast-route-local-reachable-closure-v1"
            ),
            "branch_count_algorithm_id": "python-ast-branch-contribution-v1",
            "b8_diff_algorithm_id": "python-difflib-unified-n0-v1",
            "common_source_sha256": _raw_sha256(common_bytes),
            "compare_source_sha256": _raw_sha256(compare_bytes),
            "metric_spec_sha": "",
        },
        "metric_spec_sha",
    )


_NESTED_HASH_FIELDS = {
    "/provenance_fixture": "provenance_fixture_sha",
    "/response_run_spec_fixture": "run_spec_sha",
    "/reference_outcome": "outcome_sha",
    "/shell_outcome": "outcome_sha",
    "/actual_branch_attempt": "attempt_sha",
    "/matched_ablated_branch_attempt": "attempt_sha",
    "/actual_completed_response": "response_sha",
    "/matched_ablated_completed_response": "response_sha",
}


def _frozen_nested_rules() -> list[dict[str, object]]:
    rules = []
    for registry_rule in _lab_registry()["normalized_nested_body_registry"]:
        rules.append(
            _seal(
                {
                    "rule_schema_version": ("experimental.v3m0.b7.nested-body-rule.v1"),
                    "json_pointer": registry_rule["json_pointer"],
                    "body_kind": registry_rule["body_kind"],
                    "hash_field": _NESTED_HASH_FIELDS[registry_rule["json_pointer"]],
                    "nullable": registry_rule["nullable"],
                    "full_body_required": True,
                    "rule_sha": "",
                },
                "rule_sha",
            )
        )
    return rules


def _frozen_case_specs() -> list[dict[str, object]]:
    cases = []
    for registry_case in _lab_registry()["case_contracts"]:
        cases.append(
            _seal(
                {
                    "case_schema_version": "experimental.v3m0.b7.corpus-case.v1",
                    **copy.deepcopy(registry_case),
                    "case_sha": "",
                },
                "case_sha",
            )
        )
    return cases


def _corpus_spec(metric_spec_sha: str) -> dict[str, object]:
    lab = _lab_registry()
    mutation_contract = lab["mutation_generation_contract"]
    return _seal(
        {
            "corpus_spec_schema_version": "experimental.v3m0.b7.corpus-spec.v1",
            "transcript_schema_version": (
                "experimental.v3m0.b7.normalized-transcript.v1"
            ),
            "canonical_json_profile_id": lab["canonical_json_profile_id"],
            "scheduler_stage_order": copy.deepcopy(lab["scheduler_stage_order"]),
            "presence_pointer_order": copy.deepcopy(lab["presence_pointer_order"]),
            "terminal_tag_order": copy.deepcopy(lab["terminal_tag_order"]),
            "case_contract_sha": canonical_sha_v1(lab["case_contracts"]),
            "ordered_case_specs": _frozen_case_specs(),
            "nested_body_rules": _frozen_nested_rules(),
            "mutation_algorithm_id": mutation_contract["algorithm_id"],
            "mutation_class_order": copy.deepcopy(lab["mutation_class_order"]),
            "mutation_operation_order": copy.deepcopy(lab["mutation_operation_order"]),
            "mutation_generation_contract_sha": canonical_sha_v1(mutation_contract),
            "mutation_generation_rules": [
                rule["rule_id"] for rule in mutation_contract["generation_rules"]
            ],
            "upstream_invalid_probe_rule": ("M10_UPSTREAM_INVALID_ZERO_TRANSCRIPT"),
            "metric_spec_sha": metric_spec_sha,
            "corpus_spec_sha": "",
        },
        "corpus_spec_sha",
    )


def _mutation_universe(
    transcripts: list[dict[str, object]],
    corpus_spec_sha: str,
    mutation_generation_contract_sha: str,
    generator_source_bytes: bytes | None = None,
) -> dict[str, object]:
    common = _common_module()
    source_bytes = (
        COMMON_PATH.read_bytes()
        if generator_source_bytes is None
        else generator_source_bytes
    )
    mutations = common.generate_ordered_mutations_v1(transcripts)
    assert len(mutations) == 326
    return _seal(
        {
            "mutation_universe_schema_version": (
                "experimental.v3m0.b7.mutation-universe.v1"
            ),
            "corpus_spec_sha": corpus_spec_sha,
            "mutation_generation_contract_sha": (mutation_generation_contract_sha),
            "generator_source_sha256": _raw_sha256(source_bytes),
            "ordered_mutations": mutations,
            "mutation_count": len(mutations),
            "mutation_universe_sha": "",
        },
        "mutation_universe_sha",
    )


def test_spec_join_validators_accept_registry_materialization_and_canonical_roundtrip() -> (
    None
):
    common = _common_module()
    common_source = COMMON_PATH.read_bytes()
    compare_source = COMPARE_PATH.read_bytes()
    metric = _metric_spec(common_source, compare_source)
    corpus = _corpus_spec(metric["metric_spec_sha"])
    transcripts = _seven_transcripts()
    universe = _mutation_universe(
        transcripts,
        corpus["corpus_spec_sha"],
        corpus["mutation_generation_contract_sha"],
        common_source,
    )

    metric_decoded = strict_json_loads_v1(canonical_json_bytes_v1(metric))
    corpus_decoded = strict_json_loads_v1(canonical_json_bytes_v1(corpus))
    universe_decoded = strict_json_loads_v1(canonical_json_bytes_v1(universe))
    validated_metric = common.validate_metric_spec_v1(
        metric_decoded,
        common_source,
        compare_source,
    )
    validated_corpus = common.validate_corpus_spec_v1(
        corpus_decoded,
        metric["metric_spec_sha"],
    )
    validated_universe = common.validate_mutation_universe_v1(
        universe_decoded,
        transcripts,
        corpus["corpus_spec_sha"],
        corpus["mutation_generation_contract_sha"],
        common_source,
    )

    assert validated_metric == metric
    assert validated_corpus == corpus
    assert validated_universe == universe
    assert (
        common.validate_metric_spec_v1(
            validated_metric,
            common_source,
            compare_source,
        )
        == validated_metric
    )
    assert (
        common.validate_corpus_spec_v1(
            validated_corpus,
            metric["metric_spec_sha"],
        )
        == validated_corpus
    )
    assert (
        common.validate_mutation_universe_v1(
            validated_universe,
            transcripts,
            corpus["corpus_spec_sha"],
            corpus["mutation_generation_contract_sha"],
            common_source,
        )
        == validated_universe
    )


def test_spec_join_validators_reject_unknown_fields() -> None:
    common = _common_module()
    common_source = COMMON_PATH.read_bytes()
    compare_source = COMPARE_PATH.read_bytes()
    metric = _metric_spec(common_source, compare_source)
    corpus = _corpus_spec(metric["metric_spec_sha"])
    transcripts = _seven_transcripts()
    universe = _mutation_universe(
        transcripts,
        corpus["corpus_spec_sha"],
        corpus["mutation_generation_contract_sha"],
        common_source,
    )

    for raw, invocation in (
        (
            metric,
            lambda attacked: common.validate_metric_spec_v1(
                attacked,
                common_source,
                compare_source,
            ),
        ),
        (
            corpus,
            lambda attacked: common.validate_corpus_spec_v1(
                attacked,
                metric["metric_spec_sha"],
            ),
        ),
        (
            universe,
            lambda attacked: common.validate_mutation_universe_v1(
                attacked,
                transcripts,
                corpus["corpus_spec_sha"],
                corpus["mutation_generation_contract_sha"],
                common_source,
            ),
        ),
    ):
        attacked = copy.deepcopy(raw)
        attacked["unexpected"] = None
        with pytest.raises((TypeError, ValueError)):
            invocation(attacked)


def test_metric_spec_validator_rejects_every_registry_join_root_and_source_attack() -> (
    None
):
    common = _common_module()
    common_source = COMMON_PATH.read_bytes()
    compare_source = COMPARE_PATH.read_bytes()
    legal = _metric_spec(common_source, compare_source)
    attacks = []
    for field, hostile in (
        ("metric_algorithm_id", "not-the-frozen-algorithm"),
        ("metric_contract_sha", "0" * 64),
        ("metric_order", list(reversed(legal["metric_order"]))),
        (
            "evidence_pointer_order",
            list(reversed(legal["evidence_pointer_order"])),
        ),
        ("invalid_presence_bit_width", 8),
        ("reachable_closure_algorithm_id", "not-the-frozen-closure"),
        ("branch_count_algorithm_id", "not-the-frozen-branch-count"),
        ("b8_diff_algorithm_id", "not-the-frozen-diff"),
        ("common_source_sha256", "0" * 64),
        ("compare_source_sha256", "0" * 64),
    ):
        attacked = copy.deepcopy(legal)
        attacked[field] = hostile
        attacks.append(_seal(attacked, "metric_spec_sha"))
    wrong_self_hash = copy.deepcopy(legal)
    wrong_self_hash["metric_spec_sha"] = "0" * 64
    attacks.append(wrong_self_hash)

    for attacked in attacks:
        with pytest.raises((TypeError, ValueError)):
            common.validate_metric_spec_v1(
                attacked,
                common_source,
                compare_source,
            )
    with pytest.raises((TypeError, ValueError)):
        common.validate_metric_spec_v1(legal, b"wrong common", compare_source)
    with pytest.raises((TypeError, ValueError)):
        common.validate_metric_spec_v1(legal, common_source, b"wrong compare")


def test_corpus_spec_validator_rejects_every_registry_join_and_root_attack() -> None:
    common = _common_module()
    metric = _metric_spec()
    legal = _corpus_spec(metric["metric_spec_sha"])
    attacks = []
    for field, hostile in (
        ("transcript_schema_version", "not-the-frozen-transcript"),
        ("canonical_json_profile_id", "not-the-frozen-profile"),
        (
            "scheduler_stage_order",
            list(reversed(legal["scheduler_stage_order"])),
        ),
        (
            "presence_pointer_order",
            list(reversed(legal["presence_pointer_order"])),
        ),
        ("terminal_tag_order", list(reversed(legal["terminal_tag_order"]))),
        ("case_contract_sha", "0" * 64),
        ("mutation_algorithm_id", "not-the-frozen-mutation-algorithm"),
        (
            "mutation_class_order",
            list(reversed(legal["mutation_class_order"])),
        ),
        (
            "mutation_operation_order",
            list(reversed(legal["mutation_operation_order"])),
        ),
        ("mutation_generation_contract_sha", "0" * 64),
        (
            "mutation_generation_rules",
            list(reversed(legal["mutation_generation_rules"])),
        ),
        ("upstream_invalid_probe_rule", "M09_CANONICAL_REPEAT"),
        ("metric_spec_sha", "0" * 64),
    ):
        attacked = copy.deepcopy(legal)
        attacked[field] = hostile
        attacks.append(_seal(attacked, "corpus_spec_sha"))
    for case_ordinal in range(7):
        attacked = copy.deepcopy(legal)
        attacked["ordered_case_specs"][case_ordinal] = copy.deepcopy(
            legal["ordered_case_specs"][(case_ordinal + 1) % 7]
        )
        attacks.append(_seal(attacked, "corpus_spec_sha"))
    for rule_ordinal in range(len(legal["nested_body_rules"])):
        attacked = copy.deepcopy(legal)
        rule = attacked["nested_body_rules"][rule_ordinal]
        rule["body_kind"] = f"attacked.body.Kind{rule_ordinal}"
        _seal(rule, "rule_sha")
        attacks.append(_seal(attacked, "corpus_spec_sha"))
    wrong_self_hash = copy.deepcopy(legal)
    wrong_self_hash["corpus_spec_sha"] = "0" * 64
    attacks.append(wrong_self_hash)

    for attacked in attacks:
        with pytest.raises((TypeError, ValueError)):
            common.validate_corpus_spec_v1(
                attacked,
                metric["metric_spec_sha"],
            )
    with pytest.raises((TypeError, ValueError)):
        common.validate_corpus_spec_v1(legal, "f" * 64)


def test_mutation_universe_validator_rejects_generation_root_source_and_identity_attacks() -> (
    None
):
    common = _common_module()
    common_source = COMMON_PATH.read_bytes()
    metric = _metric_spec()
    corpus = _corpus_spec(metric["metric_spec_sha"])
    transcripts = _seven_transcripts()
    legal = _mutation_universe(
        transcripts,
        corpus["corpus_spec_sha"],
        corpus["mutation_generation_contract_sha"],
        common_source,
    )
    attacks = []
    for field, hostile in (
        ("corpus_spec_sha", "0" * 64),
        ("mutation_generation_contract_sha", "0" * 64),
        ("generator_source_sha256", "0" * 64),
        ("mutation_count", 325),
    ):
        attacked = copy.deepcopy(legal)
        attacked[field] = hostile
        attacks.append(_seal(attacked, "mutation_universe_sha"))
    reordered = copy.deepcopy(legal)
    reordered["ordered_mutations"][0], reordered["ordered_mutations"][1] = (
        reordered["ordered_mutations"][1],
        reordered["ordered_mutations"][0],
    )
    attacks.append(_seal(reordered, "mutation_universe_sha"))
    duplicate = copy.deepcopy(legal)
    duplicate["ordered_mutations"][1] = copy.deepcopy(duplicate["ordered_mutations"][0])
    attacks.append(_seal(duplicate, "mutation_universe_sha"))
    wrong_self_hash = copy.deepcopy(legal)
    wrong_self_hash["mutation_universe_sha"] = "0" * 64
    attacks.append(wrong_self_hash)

    for attacked in attacks:
        with pytest.raises((TypeError, ValueError)):
            common.validate_mutation_universe_v1(
                attacked,
                transcripts,
                corpus["corpus_spec_sha"],
                corpus["mutation_generation_contract_sha"],
                common_source,
            )
    for wrong_corpus_root, wrong_generation_root, wrong_source in (
        ("f" * 64, corpus["mutation_generation_contract_sha"], common_source),
        (corpus["corpus_spec_sha"], "f" * 64, common_source),
        (
            corpus["corpus_spec_sha"],
            corpus["mutation_generation_contract_sha"],
            b"wrong generator source",
        ),
    ):
        with pytest.raises((TypeError, ValueError)):
            common.validate_mutation_universe_v1(
                legal,
                transcripts,
                wrong_corpus_root,
                wrong_generation_root,
                wrong_source,
            )


def _mutation_projection(raw: dict[str, object]) -> dict[str, object]:
    return {
        name: raw[name]
        for name in (
            "base_case_id",
            "probe_kind",
            "mutation_class",
            "target_json_pointer",
            "operation",
            "replacement_json",
            "expected_boundary",
        )
    }


def test_mutation_generator_freezes_exact_count_order_ids_and_global_probe() -> None:
    common = _common_module()
    case_ids = (
        "reference_failure",
        "shell_failure",
        "actual_response_values_failure",
        "matched_response_values_failure",
        "actual_bridge_failure",
        "matched_bridge_failure",
        "success",
    )
    class_order = (
        "SINGLE_FIELD_PRESENCE",
        "TERMINAL_TAG",
        "OUTER_BRANCH_FAILURE_SPLICE",
        "DELETE_SUCCESSFUL_PREFIX_BODY",
        "INJECT_POST_FAILURE_BODY",
        "NESTED_BODY_SHA_SPLICE",
        "CANONICAL_ROUNDTRIP",
        "CANONICAL_REPEAT",
        "UPSTREAM_INVALID",
    )
    operation_order = (
        "DELETE",
        "SET_NULL",
        "SET_VALUE",
        "INSERT_BODY",
        "REPLACE_BODY_AND_RESIGN",
        "REENCODE",
        "REPEAT",
        "RAISE_UPSTREAM",
    )

    observed = common.generate_ordered_mutations_v1(_seven_transcripts())

    assert type(observed) is list
    assert len(observed) == 326
    class_counts = {mutation_class: 0 for mutation_class in class_order}
    sort_keys = []
    mutation_ids = set()
    for ordinal, mutation in enumerate(observed):
        assert common.validate_mutation_v1(mutation) == mutation
        assert mutation["mutation_ordinal"] == ordinal
        projection = _mutation_projection(mutation)
        projection_prefix = canonical_sha_v1(projection)[:16]
        case_id = mutation["base_case_id"]
        case_token = "GLOBAL" if case_id is None else case_id
        assert mutation["mutation_id"] == (
            f"M{ordinal:06d}-{mutation['mutation_class']}-{case_token}-"
            f"{projection_prefix}"
        )
        assert mutation["mutation_id"] not in mutation_ids
        mutation_ids.add(mutation["mutation_id"])
        class_counts[mutation["mutation_class"]] += 1
        sort_keys.append(
            (
                7 if case_id is None else case_ids.index(case_id),
                class_order.index(mutation["mutation_class"]),
                mutation["target_json_pointer"].encode("utf-8"),
                operation_order.index(mutation["operation"]),
                canonical_json_bytes_v1(mutation["replacement_json"]),
            )
        )

    assert sort_keys == sorted(sort_keys)
    assert class_counts == {
        "SINGLE_FIELD_PRESENCE": 63,
        "TERMINAL_TAG": 42,
        "OUTER_BRANCH_FAILURE_SPLICE": 36,
        "DELETE_SUCCESSFUL_PREFIX_BODY": 23,
        "INJECT_POST_FAILURE_BODY": 36,
        "NESTED_BODY_SHA_SPLICE": 111,
        "CANONICAL_ROUNDTRIP": 7,
        "CANONICAL_REPEAT": 7,
        "UPSTREAM_INVALID": 1,
    }
    global_probes = [item for item in observed if item["base_case_id"] is None]
    assert len(global_probes) == 1
    assert global_probes[0] is observed[-1]
    assert global_probes[0]["operation"] == "RAISE_UPSTREAM"
    assert global_probes[0]["target_json_pointer"] == ""
    assert any(
        mutation["mutation_class"] == "NESTED_BODY_SHA_SPLICE"
        and mutation["operation"] == "SET_VALUE"
        and "/ordered_leaf_digests/0/input_body_sha" in mutation["target_json_pointer"]
        for mutation in observed
    )


def _assert_self_hash(raw: dict[str, object], hash_field: str) -> None:
    assert raw[hash_field] == canonical_sha_v1(
        {name: value for name, value in raw.items() if name != hash_field}
    )


def test_mutation_materializer_resigns_deepest_first_and_preserves_donor_body() -> None:
    common = _common_module()
    transcripts = _seven_transcripts()
    mutations = common.generate_ordered_mutations_v1(transcripts)
    by_case = {transcript["case_id"]: transcript for transcript in transcripts}

    donor_splice = next(
        mutation
        for mutation in mutations
        if mutation["base_case_id"] == "actual_response_values_failure"
        and mutation["operation"] == "REPLACE_BODY_AND_RESIGN"
        and mutation["target_json_pointer"] == "/actual_branch_attempt"
    )
    base = by_case["actual_response_values_failure"]
    base_before = copy.deepcopy(base)
    spliced = common.apply_transcript_mutation_v1(
        base,
        donor_splice,
        by_case["success"],
        common.discover_record_self_hashes_v1(base),
    )
    assert base == base_before
    assert spliced["actual_branch_attempt"] == donor_splice["replacement_json"]
    assert tuple(spliced["actual_branch_attempt"]) == tuple(
        donor_splice["replacement_json"]
    )
    _assert_self_hash(spliced["actual_branch_attempt"], "attempt_sha")
    _assert_self_hash(spliced, "experimental_sha")

    nested_failure = next(
        mutation
        for mutation in mutations
        if mutation["base_case_id"] == "success"
        and mutation["mutation_class"] == "OUTER_BRANCH_FAILURE_SPLICE"
        and mutation["target_json_pointer"] == "/actual_branch_attempt/failure"
        and mutation["replacement_json"] == "actual_response_failed"
    )
    success = by_case["success"]
    changed = common.apply_transcript_mutation_v1(
        success,
        nested_failure,
        success,
        common.discover_record_self_hashes_v1(success),
    )
    assert (
        changed["actual_branch_attempt"]["attempt_sha"]
        != success["actual_branch_attempt"]["attempt_sha"]
    )
    _assert_self_hash(changed["actual_branch_attempt"], "attempt_sha")
    _assert_self_hash(changed, "experimental_sha")


def test_m06_leaf_reference_sha_mutates_without_becoming_a_self_hash() -> None:
    common = _common_module()
    transcripts = _seven_transcripts()
    success = transcripts[-1]
    mutation = next(
        item
        for item in common.generate_ordered_mutations_v1(transcripts)
        if item["base_case_id"] == "success"
        and item["operation"] == "SET_VALUE"
        and item["target_json_pointer"] == "/ordered_leaf_digests/0/input_body_sha"
    )

    changed = common.apply_transcript_mutation_v1(
        success,
        mutation,
        success,
        common.discover_record_self_hashes_v1(success),
    )

    assert (
        changed["ordered_leaf_digests"][0]["input_body_sha"]
        == (mutation["replacement_json"])
    )
    assert all(
        record_pointer != "/ordered_leaf_digests/0"
        for record_pointer, _hash_field in common.discover_record_self_hashes_v1(
            success
        )
    )
    _assert_self_hash(changed, "experimental_sha")


def _provenance_fixture() -> dict[str, object]:
    return _seal(
        {
            "provenance_fixture_schema_version": (
                "experimental.v3m0.b7.provenance-fixture.v1"
            ),
            "parent_freeze_v3_body": {},
            "permit_body": {},
            "materialization_body": {},
            "current_scenario_response_contract_v3_body": {},
            "actual_bridge_grid_authority_body": {},
            "matched_ablated_bridge_grid_authority_body": {},
            "provenance_fixture_sha": "",
        },
        "provenance_fixture_sha",
    )


def _branch_attempt(
    branch: str,
    response_present: bool,
    bridge_present: bool,
    failure: str | None,
) -> dict[str, object]:
    return _seal(
        {
            "branch_attempt_schema_version": ("experimental.v3m0.b7.branch-attempt.v1"),
            "branch": branch,
            "response_values": {} if response_present else None,
            "bridge_audit": {} if bridge_present else None,
            "failure": failure,
            "attempt_sha": "",
        },
        "attempt_sha",
    )


def _transcript(case_id: str) -> dict[str, object]:
    case = _corpus_case(case_id)
    bits = case["presence_bits"]
    actual = (
        _branch_attempt(
            "actual",
            bits[2] == "1",
            bits[5] == "1",
            case["actual_attempt_failure"],
        )
        if bits[1] == "1"
        else None
    )
    matched = (
        _branch_attempt(
            "matched_ablated",
            bits[4] == "1",
            bits[6] == "1",
            case["matched_ablated_attempt_failure"],
        )
        if bits[3] == "1"
        else None
    )
    trace = case["expected_callback_trace"]
    leaves = [
        {
            "leaf_id": leaf_id,
            "call_ordinal": ordinal,
            "input_body_sha": "2" * 64,
            "output_body_sha": "3" * 64,
        }
        for ordinal, leaf_id in enumerate(trace)
    ]
    return _seal(
        {
            "transcript_schema_version": (
                "experimental.v3m0.b7.normalized-transcript.v1"
            ),
            "corpus_spec_sha": "4" * 64,
            "case_id": case_id,
            "environment_manifest_sha": "5" * 64,
            "provenance_fixture": _provenance_fixture(),
            "response_run_spec_fixture": {},
            "reference_outcome": {},
            "shell_outcome": {} if bits[0] == "1" else None,
            "actual_branch_attempt": actual,
            "matched_ablated_branch_attempt": matched,
            "actual_completed_response": {} if bits[7] == "1" else None,
            "matched_ablated_completed_response": ({} if bits[8] == "1" else None),
            "terminal_tag": case["terminal_tag"],
            "callback_trace": list(trace),
            "ordered_leaf_digests": leaves,
            "experimental_sha": "",
        },
        "experimental_sha",
    )


@pytest.mark.parametrize(
    "case_id",
    ("actual_response_values_failure", "success"),
)
def test_case_contract_accepts_detached_legal_minimal_transcripts(
    case_id: str,
) -> None:
    raw = _transcript(case_id)

    observed = _common_module().validate_case_contract_v1(copy.deepcopy(raw))

    assert observed == raw
    assert observed is not raw


def test_case_contract_rejects_presence_trace_leaf_and_hash_attacks() -> None:
    validator = _common_module().validate_case_contract_v1
    success = _transcript("success")
    extra_field = copy.deepcopy(success)
    extra_field["unexpected"] = None
    half_completed = copy.deepcopy(success)
    half_completed["matched_ablated_completed_response"] = None
    _seal(half_completed, "experimental_sha")
    short_trace = copy.deepcopy(success)
    short_trace["callback_trace"].pop()
    short_trace["ordered_leaf_digests"].pop()
    _seal(short_trace, "experimental_sha")
    wrong_leaf = copy.deepcopy(success)
    wrong_leaf["ordered_leaf_digests"][-1]["call_ordinal"] = 0
    _seal(wrong_leaf, "experimental_sha")
    wrong_hash = copy.deepcopy(success)
    wrong_hash["experimental_sha"] = "0" * 64

    failed = _transcript("actual_response_values_failure")
    post_failure = copy.deepcopy(failed)
    post_failure["matched_ablated_branch_attempt"] = _branch_attempt(
        "matched_ablated",
        True,
        False,
        None,
    )
    post_failure["callback_trace"].append("matched_ablated_response_values")
    post_failure["ordered_leaf_digests"].append(
        {
            "leaf_id": "matched_ablated_response_values",
            "call_ordinal": 3,
            "input_body_sha": "2" * 64,
            "output_body_sha": "3" * 64,
        }
    )
    _seal(post_failure, "experimental_sha")

    for hostile in (
        extra_field,
        half_completed,
        short_trace,
        wrong_leaf,
        wrong_hash,
        post_failure,
    ):
        with pytest.raises((TypeError, ValueError)):
            validator(hostile)


def test_invalid_presence_generator_freezes_all_1393_constructible_states() -> None:
    common = _common_module()
    success = _transcript("success")
    original = copy.deepcopy(success)

    candidates = common.generate_constructible_invalid_presence_candidates_v1(success)

    assert len(candidates) == 1393
    assert success == original
    assert tuple(candidates[0]) == (
        "terminal_tag",
        "bit_integer",
        "presence_bits",
        "half_pair",
        "transcript",
    )
    assert (
        candidates[0]["bit_integer"],
        candidates[0]["terminal_tag"],
        candidates[0]["presence_bits"],
    ) == (0, "shell_failure", "000000000")
    assert (
        candidates[-1]["bit_integer"],
        candidates[-1]["terminal_tag"],
        candidates[-1]["presence_bits"],
    ) == (511, "matched_bridge_failure", "111111111")

    observed_pairs = [
        (candidate["terminal_tag"], candidate["presence_bits"])
        for candidate in candidates
    ]
    assert len(set(observed_pairs)) == 1393
    legal_pairs = {
        (case["terminal_tag"], case["presence_bits"])
        for case in (
            _corpus_case(case_id)
            for case_id in (
                "reference_failure",
                "shell_failure",
                "actual_response_values_failure",
                "matched_response_values_failure",
                "actual_bridge_failure",
                "matched_bridge_failure",
                "success",
            )
        )
    }
    assert legal_pairs.isdisjoint(observed_pairs)
    assert all(
        candidate["half_pair"]
        == (
            (candidate["presence_bits"][5] != candidate["presence_bits"][6])
            or (candidate["presence_bits"][7] != candidate["presence_bits"][8])
        )
        for candidate in candidates
    )
    assert all(
        common.validate_exact_lab_record_v1(
            "NormalizedB7ExecutionTranscriptV1",
            candidate["transcript"],
        )
        == candidate["transcript"]
        for candidate in candidates
    )


def test_invalid_presence_generator_applies_parent_child_bits_and_rehashes() -> None:
    common = _common_module()
    candidates = common.generate_constructible_invalid_presence_candidates_v1(
        _transcript("success")
    )
    candidate = next(
        item
        for item in candidates
        if item["presence_bits"] == "010000000" and item["terminal_tag"] == "success"
    )
    transcript = candidate["transcript"]

    assert transcript["actual_branch_attempt"] is not None
    assert transcript["actual_branch_attempt"]["response_values"] is None
    assert transcript["actual_branch_attempt"]["bridge_audit"] is None
    assert transcript["matched_ablated_branch_attempt"] is None
    _assert_self_hash(transcript["actual_branch_attempt"], "attempt_sha")
    _assert_self_hash(transcript, "experimental_sha")
    assert not any(item["presence_bits"] == "001000000" for item in candidates)


def test_invalid_presence_generator_requires_the_legal_success_base() -> None:
    common = _common_module()
    for hostile in (None, _transcript("shell_failure")):
        with pytest.raises((TypeError, ValueError)):
            common.generate_constructible_invalid_presence_candidates_v1(hostile)


def _decision_record(
    field_order: tuple[str, ...],
    projection_order: tuple[str, ...],
) -> dict[str, object]:
    raw = {name: {"field": name, "nested": [name]} for name in field_order}
    raw["decision_payload_sha"] = canonical_sha_v1(
        {name: raw[name] for name in projection_order}
    )
    return raw


@pytest.mark.parametrize(
    ("symbol", "field_order", "projection_order"),
    (
        (
            "validate_d0_decision_payload_projection_v1",
            D0_FIELD_ORDER,
            D0_PROJECTION_ORDER,
        ),
        (
            "validate_d1_decision_payload_projection_v1",
            D1_FIELD_ORDER,
            D1_PROJECTION_ORDER,
        ),
    ),
)
def test_decision_projection_validators_freeze_exact_deep_projection(
    symbol: str,
    field_order: tuple[str, ...],
    projection_order: tuple[str, ...],
) -> None:
    common = _common_module()
    validator = getattr(common, symbol)
    raw = _decision_record(field_order, projection_order)

    observed = validator(copy.deepcopy(raw))

    assert observed == raw
    assert observed is not raw
    for field in projection_order:
        if isinstance(raw[field], dict):
            assert observed[field] is not raw[field]

    decoded = strict_json_loads_v1(canonical_json_bytes_v1(raw))
    first = validator(decoded)
    assert validator(first) == first


@pytest.mark.parametrize(
    ("symbol", "field_order", "projection_order"),
    (
        (
            "validate_d0_decision_payload_projection_v1",
            D0_FIELD_ORDER,
            D0_PROJECTION_ORDER,
        ),
        (
            "validate_d1_decision_payload_projection_v1",
            D1_FIELD_ORDER,
            D1_PROJECTION_ORDER,
        ),
    ),
)
def test_decision_projection_validators_reject_shape_hash_and_alias_attacks(
    symbol: str,
    field_order: tuple[str, ...],
    projection_order: tuple[str, ...],
) -> None:
    common = _common_module()
    validator = getattr(common, symbol)
    legal = _decision_record(field_order, projection_order)

    extra = copy.deepcopy(legal)
    extra["unexpected"] = None
    wrong_hash = copy.deepcopy(legal)
    wrong_hash["decision_payload_sha"] = "0" * 64
    missing = copy.deepcopy(legal)
    missing.pop(projection_order[0])

    for hostile in (extra, wrong_hash, missing):
        with pytest.raises((TypeError, ValueError)):
            validator(hostile)

    untouched = copy.deepcopy(legal)
    excluded_field = next(
        name
        for name in field_order
        if name not in projection_order and name != "decision_payload_sha"
    )
    untouched[excluded_field] = {"changed": True}
    assert validator(untouched)["decision_payload_sha"] == legal["decision_payload_sha"]


def test_b8_consumer_skeleton_is_bytes_only_and_renders_exact_route_literals() -> None:
    common = _common_module()
    skeleton = common.B8_CONSUMER_SKELETON_UTF8

    assert type(skeleton) is bytes
    assert skeleton.endswith(b"\n")
    assert skeleton.count(b"__ROUTE_MODULE__") == 1
    assert skeleton.count(b"__ROUTE_ID__") == 1
    assert skeleton.count(b"__WIRE_SCHEMA_ID__") == 1

    rendered = common.render_b8_consumer_adapter_utf8(
        "A_FLAT",
        "experiments.v3m0_b7_schema_lab.a_flat",
        "experimental.v3m0.b7.a-flat.wire.v1",
    )

    assert type(rendered) is bytes
    assert b"__ROUTE_MODULE__" not in rendered
    assert b"__ROUTE_ID__" not in rendered
    assert b"__WIRE_SCHEMA_ID__" not in rendered
    ast.parse(rendered.decode("utf-8"), mode="exec")
    normalized = (
        rendered.replace(
            b"experiments.v3m0_b7_schema_lab.a_flat",
            b"__ROUTE_MODULE__",
        )
        .replace(b"A_FLAT", b"__ROUTE_ID__")
        .replace(
            b"experimental.v3m0.b7.a-flat.wire.v1",
            b"__WIRE_SCHEMA_ID__",
        )
    )
    assert normalized == skeleton


@pytest.mark.parametrize(
    ("route_id", "route_module", "wire_schema_id"),
    (
        ("A_FLAT\n", "experiments.v3m0_b7_schema_lab.a_flat", "wire"),
        ("A_FLAT", "bad-module", "wire"),
        ("A_FLAT", "experiments.v3m0_b7_schema_lab.a_flat", 'wire"quote'),
        (1, "experiments.v3m0_b7_schema_lab.a_flat", "wire"),
    ),
)
def test_b8_consumer_renderer_rejects_nonliteral_injection(
    route_id: object,
    route_module: object,
    wire_schema_id: object,
) -> None:
    common = _common_module()
    with pytest.raises((TypeError, ValueError)):
        common.render_b8_consumer_adapter_utf8(
            route_id,
            route_module,
            wire_schema_id,
        )


def test_b8_require_helpers_fail_closed_without_truthiness_dispatch() -> None:
    common = _common_module()

    common._b8_require_exact("x", "x", "field")
    common._b8_require_present({}, "field")
    common._b8_require_absent(None, "field")
    with pytest.raises(ValueError):
        common._b8_require_exact("x", "y", "field")
    with pytest.raises(ValueError):
        common._b8_require_present(None, "field")
    with pytest.raises(ValueError):
        common._b8_require_absent({}, "field")
