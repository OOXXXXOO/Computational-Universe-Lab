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
    "callable",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "hasattr",
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

TASK3_PUBLIC_SYMBOLS = {
    "B7_V91_PURE_REPLAY_PROJECTION_SHA256",
    "canonical_json_bytes_v1",
    "canonical_sha_v1",
    "strict_json_loads_v1",
}

TASK3_FUNCTION_SIGNATURES = {
    "canonical_json_bytes_v1": "value",
    "canonical_sha_v1": "value",
    "strict_json_loads_v1": "canonical_json_utf8",
}

TASK3_NESTED_FUNCTION_SIGNATURES = {
    ("canonical_json_bytes_v1", "validate_object_keys"): ("candidate", "path"),
    ("strict_json_loads_v1", "reject_duplicate_object_pairs"): ("pairs",),
    ("strict_json_loads_v1", "reject_nonfinite_constant"): ("constant_text",),
}

TASK3_DIRECT_IMPORTS = ["__future__", "hashlib", "json"]

TASK3_ALLOWED_CALL_TARGETS_BY_FUNCTION = {
    "canonical_json_bytes_v1": {
        "ValueError",
        "json.dumps",
        "set",
        "str.encode",
        "validate_object_keys",
    },
    "validate_object_keys": {
        "TypeError",
        "ValueError",
        "dict.items",
        "enumerate",
        "id",
        "set.add",
        "set.remove",
        "type",
        "validate_object_keys",
    },
    "canonical_sha_v1": {
        "canonical_json_bytes_v1",
        "hashlib.sha256",
        "hashlib.sha256().hexdigest",
    },
    "strict_json_loads_v1": {
        "TypeError",
        "ValueError",
        "bytes.decode",
        "bytes.startswith",
        "canonical_json_bytes_v1",
        "json.loads",
        "type",
    },
    "reject_duplicate_object_pairs": {"ValueError"},
    "reject_nonfinite_constant": {"ValueError"},
}

TASK3_CALL_SHAPES = {
    "ValueError": (1, ()),
    "TypeError": (1, ()),
    "bytes.decode": (2, ()),
    "bytes.startswith": (2, ()),
    "canonical_json_bytes_v1": (1, ()),
    "dict.items": (1, ()),
    "enumerate": (1, ()),
    "hashlib.sha256": (1, ()),
    "hashlib.sha256().hexdigest": (0, ()),
    "id": (1, ()),
    "json.dumps": (
        1,
        ("ensure_ascii", "allow_nan", "sort_keys", "separators"),
    ),
    "json.loads": (1, ("object_pairs_hook", "parse_constant")),
    "set": (0, ()),
    "set.add": (2, ()),
    "set.remove": (2, ()),
    "str.encode": (2, ()),
    "type": (1, ()),
    "validate_object_keys": (2, ()),
}

TASK3_CAPABILITY_CALL_TOKENS = {
    "authority",
    "callback",
    "callable",
    "caller",
    "capability",
    "environment",
    "hydrate",
    "issuer",
    "promote",
    "registry",
    "resign",
    "seal",
    "token",
    "wrapper",
    "worktree",
}

TASK3_RESERVED_CALL_ROOTS = {
    "TypeError",
    "ValueError",
    "bytes",
    "canonical_json_bytes_v1",
    "dict",
    "enumerate",
    "hashlib",
    "id",
    "json",
    "reject_duplicate_object_pairs",
    "reject_nonfinite_constant",
    "set",
    "str",
    "type",
    "validate_object_keys",
}

TASK3_EXACT_LOCAL_CALL_BINDINGS = {
    ("canonical_json_bytes_v1", "text"): "json.dumps",
    ("strict_json_loads_v1", "text"): "bytes.decode",
    ("strict_json_loads_v1", "value"): "json.loads",
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


def _task3_call_target(node: ast.Call) -> str | None:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if not isinstance(function, ast.Attribute):
        return None
    if isinstance(function.value, ast.Name):
        return f"{function.value.id}.{function.attr}"
    if isinstance(function.value, ast.Call):
        receiver = _task3_call_target(function.value)
        if receiver is not None:
            return f"{receiver}().{function.attr}"
    return None


def _enclosing_function_name(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> str | None:
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, ast.FunctionDef):
            return parent.name
        parent = parents.get(parent)
    return None


def _assert_exact_function_shape(
    node: ast.FunctionDef,
    expected_arguments: tuple[str, ...],
) -> None:
    assert node.decorator_list == []
    assert node.args.defaults == []
    assert all(default is None for default in node.args.kw_defaults)
    assert node.args.posonlyargs == []
    assert node.args.vararg is None
    assert node.args.kwonlyargs == []
    assert node.args.kwarg is None
    assert tuple(argument.arg for argument in node.args.args) == expected_arguments


def _assert_core_source_contract(source: str) -> None:
    tree = ast.parse(source)
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    contract = _registry()["lab_contract"]["pure_replay_core_contract"]
    allowed_imports = set(contract["allowed_external_import_modules_exact"])

    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.asname is None
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "repository-local imports are forbidden"
            assert node.module is not None
            assert all(alias.name != "*" for alias in node.names)
            assert all(alias.asname is None for alias in node.names)
            imported_modules.append(node.module)
    assert imported_modules == TASK3_DIRECT_IMPORTS
    assert set(imported_modules).issubset(allowed_imports)
    assert not (
        {name.split(".", 1)[0] for name in imported_modules} & FORBIDDEN_MODULE_ROOTS
    )

    top_level_assignments: set[str] = set()
    top_level_functions: list[str] = []
    for node in tree.body:
        assert isinstance(
            node,
            (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef),
        )
        if isinstance(node, ast.Expr):
            assert isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str
            )
        elif isinstance(node, ast.Assign):
            assert all(isinstance(target, ast.Name) for target in node.targets)
            top_level_assignments.update(target.id for target in node.targets)
            ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef):
            top_level_functions.append(node.name)
            assert node.name in TASK3_FUNCTION_SIGNATURES
            _assert_exact_function_shape(
                node,
                (TASK3_FUNCTION_SIGNATURES[node.name],),
            )

    assert top_level_assignments == {"B7_V91_PURE_REPLAY_PROJECTION_SHA256"}
    assert top_level_functions == list(TASK3_FUNCTION_SIGNATURES)
    assert set(top_level_functions).isdisjoint(FUTURE_TASK_SYMBOLS)

    observed_nested_functions: set[tuple[str, str]] = set()
    observed_exact_local_bindings: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
        assert not isinstance(node, (ast.Global, ast.Nonlocal))
        if isinstance(node, ast.FunctionDef) and node not in tree.body:
            parent_name = _enclosing_function_name(node, parents)
            assert parent_name is not None
            key = (parent_name, node.name)
            assert key in TASK3_NESTED_FUNCTION_SIGNATURES
            assert key not in observed_nested_functions
            observed_nested_functions.add(key)
            _assert_exact_function_shape(
                node,
                TASK3_NESTED_FUNCTION_SIGNATURES[key],
            )
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            assert node.id not in TASK3_RESERVED_CALL_ROOTS
            scope = _enclosing_function_name(node, parents)
            binding_key = (scope, node.id)
            if binding_key in TASK3_EXACT_LOCAL_CALL_BINDINGS:
                assert binding_key not in observed_exact_local_bindings
                assignment = parents[node]
                assert isinstance(assignment, ast.Assign)
                assert assignment.targets == [node]
                assert isinstance(assignment.value, ast.Call)
                assert (
                    _task3_call_target(assignment.value)
                    == TASK3_EXACT_LOCAL_CALL_BINDINGS[binding_key]
                )
                observed_exact_local_bindings.add(binding_key)
        if isinstance(node, ast.Attribute) and isinstance(
            node.ctx, (ast.Store, ast.Del)
        ):
            raise AssertionError("attribute mutation is forbidden in the Task-3 core")
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            attribute_parent = parents[node]
            assert isinstance(attribute_parent, ast.Call)
            assert attribute_parent.func is node
        if isinstance(node, ast.Call):
            target = _task3_call_target(node)
            assert target is not None, "dynamic call target is forbidden"
            lowered_target = target.casefold()
            assert not any(
                token in lowered_target for token in TASK3_CAPABILITY_CALL_TOKENS
            )
            if isinstance(node.func, ast.Name):
                assert node.func.id not in FORBIDDEN_CALL_NAMES
            if isinstance(node.func, ast.Attribute):
                assert _resolved_attribute_root(node.func) not in FORBIDDEN_MODULE_ROOTS
            scope = _enclosing_function_name(node, parents)
            assert scope is not None, "module-body calls are forbidden"
            assert target in TASK3_ALLOWED_CALL_TARGETS_BY_FUNCTION[scope]
            positional_count, keyword_names = TASK3_CALL_SHAPES[target]
            assert len(node.args) == positional_count
            assert not any(isinstance(argument, ast.Starred) for argument in node.args)
            assert tuple(keyword.arg for keyword in node.keywords) == keyword_names
            if target == "json.dumps":
                assert {
                    keyword.arg: ast.literal_eval(keyword.value)
                    for keyword in node.keywords
                } == {
                    "ensure_ascii": False,
                    "allow_nan": False,
                    "sort_keys": True,
                    "separators": (",", ":"),
                }
            elif target == "json.loads":
                observed_hooks = {
                    keyword.arg: keyword.value.id
                    for keyword in node.keywords
                    if isinstance(keyword.value, ast.Name)
                }
                assert observed_hooks == {
                    "object_pairs_hook": "reject_duplicate_object_pairs",
                    "parse_constant": "reject_nonfinite_constant",
                }
        if isinstance(node, ast.arg):
            lowered = node.arg.casefold()
            assert "authority" not in lowered
            assert "callback" not in lowered
            assert "callable" not in lowered

    assert observed_nested_functions == set(TASK3_NESTED_FUNCTION_SIGNATURES)
    assert observed_exact_local_bindings == set(TASK3_EXACT_LOCAL_CALL_BINDINGS)


def test_core_source_has_exact_task3_symbols_imports_and_signatures() -> None:
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    _assert_core_source_contract(CORE_PATH.read_text(encoding="utf-8"))


def test_core_runtime_namespace_has_exact_task3_public_symbols() -> None:
    core = _core_module()
    import_symbols = {"annotations", "hashlib", "json"}
    observed = {
        name
        for name in vars(core)
        if not name.startswith("__") and name not in import_symbols
    }

    assert observed == TASK3_PUBLIC_SYMBOLS


def test_static_contract_rejects_extra_helper_callback_and_capability_imports() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'
    attacks = (
        source + "\ndef _extra_callback_helper(value):\n    return value\n",
        source.replace(
            "def canonical_json_bytes_v1(value: object)",
            "def canonical_json_bytes_v1(value: object, callback=None)",
            1,
        ),
        source.replace("import json", "import json\nimport time", 1),
        source.replace("import json", "import json\nimport random", 1),
        source.replace("import json", "import json\nimport os", 1),
        source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    if callable(value):\n        return value()\n",
            1,
        ),
        source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    if hasattr(value, 'issue_authority'):\n"
            + "        return value.issue_authority()\n",
            1,
        ),
    )

    for attacked_source in attacks:
        with pytest.raises((AssertionError, KeyError)):
            _assert_core_source_contract(attacked_source)


def test_static_contract_rejects_definition_use_capability_escapes() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'
    strict_load_anchor = "    value = json.loads(\n"
    canonical_try_anchor = '    try:\n        return str.encode(text, "utf-8")\n'

    receiver_rebinding = source.replace(
        canonical_try_anchor,
        '    if value == "__escape__":\n        text = value\n' + canonical_try_anchor,
        1,
    )
    attacks = {
        "callee_alias": source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    hidden_hook = value\n"
            + "    if False:\n"
            + "        return hidden_hook()\n",
            1,
        ),
        "parameter_attribute_call": source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    if False:\n"
            + "        return value.issue_authority()\n",
            1,
        ),
        "parameter_attribute_load": source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    if False:\n"
            + "        value.issue_authority\n",
            1,
        ),
        "kwargs_hook_replacement": source.replace(
            "object_pairs_hook=reject_duplicate_object_pairs,",
            "object_pairs_hook=json.loads,",
            1,
        ),
        "nested_hook_rebinding": source.replace(
            strict_load_anchor,
            '    if canonical_json_utf8 == b"__escape__":\n'
            "        reject_duplicate_object_pairs = canonical_json_utf8.__class__\n"
            + strict_load_anchor,
            1,
        ),
        "allowlisted_receiver_rebinding": receiver_rebinding,
    }

    for attack_id, attacked_source in attacks.items():
        assert attacked_source != source, (
            f"attack fixture did not mutate source: {attack_id}"
        )
        with pytest.raises((AssertionError, KeyError)):
            _assert_core_source_contract(attacked_source)


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


def test_canonical_json_rejects_subclasses_before_caller_dispatch() -> None:
    core = _core_module()
    callback_trace: list[str] = []

    class CallerDict(dict):
        def items(self):
            callback_trace.append("dict.items")
            return super().items()

    class CallerList(list):
        def __iter__(self):
            callback_trace.append("list.__iter__")
            return super().__iter__()

    class CallerTuple(tuple):
        def __iter__(self):
            callback_trace.append("tuple.__iter__")
            return super().__iter__()

    class CallerString(str):
        def encode(self, encoding="utf-8", errors="strict"):
            callback_trace.append("str.encode")
            return super().encode(encoding, errors)

    subclass_values = (
        CallerDict(a=1),
        CallerList((1, 2)),
        CallerTuple((1, 2)),
        CallerString("caller-owned"),
        {"nested": CallerDict(a=1)},
        {"nested": CallerList((1, 2))},
        {"nested": CallerTuple((1, 2))},
        {"nested": CallerString("caller-owned")},
    )

    for value in subclass_values:
        callback_trace.clear()
        with pytest.raises(TypeError, match="exact built-in JSON"):
            core.canonical_json_bytes_v1(value)
        assert callback_trace == []


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
