"""Task-7 contracts for the B7 owner-neutral schema-lab common layer."""

from __future__ import annotations

import ast
import copy
import importlib
import inspect
from pathlib import Path

import pytest

from rulespace_v3.b7_replay_core_v1 import canonical_sha_v1


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPOSITORY_ROOT / "experiments" / "v3m0_b7_schema_lab"
INITIALIZER_PATH = LAB_ROOT / "__init__.py"
COMMON_PATH = LAB_ROOT / "common.py"

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
