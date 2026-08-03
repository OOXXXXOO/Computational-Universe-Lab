"""Task-3 skeleton contract for the import-pure B7 replay core."""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import math
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPOSITORY_ROOT / "docsv3" / "v3-机器合同-B7-v9.1-registry.json"
CORE_PATH = REPOSITORY_ROOT / "rulespace_v3" / "b7_replay_core_v1.py"

PROJECTION_SHA256 = "bafbaeb75e890715464c1fff6e6e0cbf1d4f56bb53a3817a9b2d12d2a3c27ff9"

FORBIDDEN_MODULE_ROOTS = {
    "_posixsubprocess",
    "asyncio",
    "concurrent",
    "ctypes",
    "importlib",
    "multiprocessing",
    "os",
    "posix",
    "pty",
    "runpy",
    "socket",
    "subprocess",
    "threading",
    "time",
}

FORBIDDEN_CALL_NAMES = {
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "print",
    "vars",
}

FUTURE_TASK_SYMBOLS = {
    "validate_response_run_spec_fixture_v1",
    "validate_endpoint_reference_outcome_raw_v1",
    "validate_endpoint_shell_outcome_raw_v1",
    "validate_source_readout_response_raw_v1",
    "validate_synthetic_parent_freeze_v3_body_v1",
    "validate_synthetic_component_body_v1",
    "validate_provenance_fixture_v1",
    "validate_branch_attempt_v1",
    "_select_endpoint_reference_from_raw",
    "_track_endpoint_shell_from_raw",
    "_build_fejer_branch_response_values_from_raw",
    "_audit_source_readout_bridge_from_raw",
    "_assemble_atomic_paired_response_attempt_from_raw",
}


def _registry() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _core_module():
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    return importlib.import_module("rulespace_v3.b7_replay_core_v1")


def _resolved_attribute_root(node: ast.Attribute) -> str | None:
    value: ast.AST = node
    while isinstance(value, ast.Attribute):
        value = value.value
    return value.id if isinstance(value, ast.Name) else None


def test_core_source_has_only_declared_pure_imports_and_top_level_shapes() -> None:
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    tree = ast.parse(CORE_PATH.read_text(encoding="utf-8"))
    contract = _registry()["lab_contract"]["pure_replay_core_contract"]
    allowed_imports = set(contract["allowed_external_import_modules_exact"])

    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "repository-local imports are forbidden"
            assert node.module is not None
            assert all(alias.name != "*" for alias in node.names)
            imported_modules.append(node.module)
    assert set(imported_modules).issubset(allowed_imports)
    assert not ({name.split(".", 1)[0] for name in imported_modules} & FORBIDDEN_MODULE_ROOTS)

    for node in tree.body:
        assert isinstance(
            node,
            (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef),
        )
        if isinstance(node, ast.Expr):
            assert isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        elif isinstance(node, ast.Assign):
            assert all(isinstance(target, ast.Name) for target in node.targets)
            ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign):
            assert isinstance(node.target, ast.Name)
            assert node.value is not None
            ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef):
            assert node.decorator_list == []
            assert node.args.defaults == []
            assert all(default is None for default in node.args.kw_defaults)

    top_level_functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert {
        "canonical_json_bytes_v1",
        "canonical_sha_v1",
        "strict_json_loads_v1",
    }.issubset(top_level_functions)
    assert top_level_functions.isdisjoint(FUTURE_TASK_SYMBOLS)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in FORBIDDEN_CALL_NAMES
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert _resolved_attribute_root(node.func) not in FORBIDDEN_MODULE_ROOTS


def test_projection_literal_recomputes_from_the_pinned_registry() -> None:
    registry = _registry()
    projection_contract = registry["lab_contract"]["pure_replay_core_contract"][
        "registry_literal_projection"
    ]
    projection: dict[str, object] = {}
    for field, pointer in zip(
        projection_contract["field_order"],
        projection_contract["source_pointers_in_field_order"],
    ):
        value: object = registry
        for token in pointer.removeprefix("/").split("/"):
            assert isinstance(value, dict)
            value = value[token]
        projection[field] = value

    canonical = json.dumps(
        projection,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    observed = hashlib.sha256(canonical).hexdigest()
    assert observed == PROJECTION_SHA256
    assert observed == projection_contract["canonical_sha256"]

    core = _core_module()
    assert core.B7_V91_PURE_REPLAY_PROJECTION_SHA256 == observed


def test_canonical_json_bytes_and_sha_match_the_registry_algorithm() -> None:
    core = _core_module()
    payload = {"β": "雪", "a": [1, -0.0, True, None]}
    expected = '{"a":[1,-0.0,true,null],"β":"雪"}'.encode("utf-8")

    assert core.canonical_json_bytes_v1(payload) == expected
    assert core.canonical_sha_v1(payload) == hashlib.sha256(expected).hexdigest()
    with pytest.raises(ValueError):
        core.canonical_json_bytes_v1({"bad": math.nan})
    with pytest.raises(TypeError, match="key"):
        core.canonical_json_bytes_v1({1: "not-a-JSON-object-key"})
    with pytest.raises(ValueError, match="UTF-8"):
        core.canonical_json_bytes_v1({"bad": "\ud800"})


def test_strict_json_loader_rejects_ambiguous_or_nonfinite_input() -> None:
    core = _core_module()

    assert core.strict_json_loads_v1(b'{"a":[1,true,null],"z":"\xe9\x9b\xaa"}') == {
        "a": [1, True, None],
        "z": "雪",
    }
    with pytest.raises(TypeError):
        core.strict_json_loads_v1('{"a":1}')
    with pytest.raises(ValueError, match="BOM"):
        core.strict_json_loads_v1(b"\xef\xbb\xbf{}")
    with pytest.raises(ValueError, match="duplicate"):
        core.strict_json_loads_v1(b'{"a":1,"a":2}')
    with pytest.raises(ValueError, match="UTF-8"):
        core.strict_json_loads_v1(b'"\\ud800"')
    for token in (b"NaN", b"Infinity", b"-Infinity"):
        with pytest.raises(ValueError, match="finite"):
            core.strict_json_loads_v1(token)
