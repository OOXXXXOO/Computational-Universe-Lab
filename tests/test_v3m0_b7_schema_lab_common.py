"""Task-7 contracts for the B7 owner-neutral schema-lab common layer."""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path


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
