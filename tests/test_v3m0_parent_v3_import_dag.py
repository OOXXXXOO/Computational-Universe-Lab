from __future__ import annotations

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DIRECT_LOCAL_IMPORTS = {
    "rulespace_v3.parent_signing_audit_v1": {
        "rulespace_v3.evidence",
        "rulespace_v3.parent_candidate_v3",
        "rulespace_v3.parent_freeze_v3_contracts",
        "rulespace_v3.parent_v3_contracts",
    },
    "rulespace_v3.parent_freeze_v3": {
        "rulespace_v3.evidence",
        "rulespace_v3.parent_candidate_v3",
        "rulespace_v3.parent_freeze_v3_contracts",
        "rulespace_v3.parent_signing_audit_v1",
    },
    "rulespace_v3.parent_authority_v3": {
        "rulespace_v3.evidence",
        "rulespace_v3.parent_candidate_v3",
        "rulespace_v3.parent_freeze_v3",
        "rulespace_v3.parent_freeze_v3_contracts",
        "rulespace_v3.parent_reviewer_keys_v1",
        "rulespace_v3.parent_signing_audit_v1",
        "rulespace_v3.parent_signing_literals_v1",
    },
}


def _module_path(module_name: str) -> Path:
    return ROOT / (module_name.replace(".", "/") + ".py")


def _direct_local_imports(module_name: str) -> set[str]:
    module = ast.parse(_module_path(module_name).read_text(encoding="utf-8"))
    package = module_name.rpartition(".")[0]
    result: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            result.update(
                alias.name
                for alias in node.names
                if alias.name.startswith("rulespace_v3")
            )
        elif isinstance(node, ast.ImportFrom) and node.level:
            base_parts = package.split(".")
            prefix = ".".join(base_parts[: len(base_parts) - node.level + 1])
            suffix = node.module or ""
            resolved = ".".join(item for item in (prefix, suffix) if item)
            if resolved.startswith("rulespace_v3"):
                result.add(resolved)
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("rulespace_v3")
        ):
            result.add(node.module)
    return result


@pytest.mark.parametrize("module_name", tuple(EXPECTED_DIRECT_LOCAL_IMPORTS))
def test_slice_a5_parent_v3_direct_import_dag_is_exact_and_acyclic(
    module_name: str,
) -> None:
    assert (
        _direct_local_imports(module_name) == EXPECTED_DIRECT_LOCAL_IMPORTS[module_name]
    )


def test_slice_a5_parent_v3_root_modules_have_no_dynamic_import_or_code_eval() -> None:
    forbidden_calls = {"__import__", "eval", "exec", "compile"}
    for module_name in EXPECTED_DIRECT_LOCAL_IMPORTS:
        module = ast.parse(_module_path(module_name).read_text(encoding="utf-8"))
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in forbidden_calls
            for node in ast.walk(module)
        )
        assert not any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            and (
                any(alias.name == "importlib" for alias in node.names)
                if isinstance(node, ast.Import)
                else node.module == "importlib"
            )
            for node in ast.walk(module)
        )


def test_slice_a5_authority_layers_do_not_depend_on_old_opaque_facade() -> None:
    forbidden = {
        "rulespace_v3.parent_authority",
        "rulespace_v3.application_authority_v2",
        "rulespace_v3.application_materialization_v2",
    }
    for module_name in EXPECTED_DIRECT_LOCAL_IMPORTS:
        assert _direct_local_imports(module_name).isdisjoint(forbidden)
