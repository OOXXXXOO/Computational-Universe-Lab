"""Task-7 contracts for the B7 owner-neutral schema-lab common layer."""

from __future__ import annotations

import ast
import copy
import importlib
import inspect
import json
from pathlib import Path

import pytest

from rulespace_v3.b7_replay_core_v1 import canonical_sha_v1


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPOSITORY_ROOT / "experiments" / "v3m0_b7_schema_lab"
INITIALIZER_PATH = LAB_ROOT / "__init__.py"
COMMON_PATH = LAB_ROOT / "common.py"
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
        "actual_response_values_failure": (
            2,
            "actual_response_values_failure",
            "actual_response_values",
            "110000000",
            "actual_response_failed",
            None,
            ["reference", "shell", "actual_response_values"],
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


def _mutation() -> dict[str, object]:
    return _seal(
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
        "mutation_sha",
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
def test_common_basic_record_validators_reject_order_type_and_self_hash_attacks(
    symbol: str,
    factory,
    typed_field: str,
    bad_value: object,
) -> None:
    validator = getattr(_common_module(), symbol)
    legal = factory()
    hash_field = next(reversed(legal))
    reordered = {name: legal[name] for name in reversed(legal)}
    wrong_type = copy.deepcopy(legal)
    wrong_type[typed_field] = bad_value
    _seal(wrong_type, hash_field)
    wrong_hash = copy.deepcopy(legal)
    wrong_hash[hash_field] = "0" * 64

    for hostile in (reordered, wrong_type, wrong_hash):
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
    _seal(wrong_mutation, "mutation_sha")

    attacks = (
        (common.validate_environment_manifest_v1, wrong_schema),
        (common.validate_corpus_case_v1, wrong_case),
        (common.validate_nested_body_rule_v1, wrong_pointer),
        (common.validate_mutation_v1, wrong_mutation),
    )
    for validator, hostile in attacks:
        with pytest.raises((TypeError, ValueError)):
            validator(hostile)


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
    reordered = {name: success[name] for name in reversed(success)}
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
        reordered,
        half_completed,
        short_trace,
        wrong_leaf,
        wrong_hash,
        post_failure,
    ):
        with pytest.raises((TypeError, ValueError)):
            validator(hostile)


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
def test_decision_projection_validators_reject_order_hash_and_alias_attacks(
    symbol: str,
    field_order: tuple[str, ...],
    projection_order: tuple[str, ...],
) -> None:
    common = _common_module()
    validator = getattr(common, symbol)
    legal = _decision_record(field_order, projection_order)

    reordered = {name: legal[name] for name in reversed(field_order)}
    wrong_hash = copy.deepcopy(legal)
    wrong_hash["decision_payload_sha"] = "0" * 64
    missing = copy.deepcopy(legal)
    missing.pop(projection_order[0])

    for hostile in (reordered, wrong_hash, missing):
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
