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

TASK4_FUNCTION_SIGNATURES = {
    "_split_wire_top_level_v1": ("value", "delimiter"),
    "_literal_wire_value_v1": ("value",),
    "_validate_wire_value_v1": (
        "value",
        "wire_type",
        "nested_record",
        "field",
        "schemas",
    ),
    "_validate_record_raw_v1": ("raw_body", "record_name", "field", "schemas"),
    "_record_schemas_v1": (),
    "_canonical_equal_v1": ("left", "right", "field"),
    "_component_by_id_v1": ("graph_raw", "component_id"),
    "validate_endpoint_reference_outcome_raw_v1": ("raw_body",),
    "validate_endpoint_shell_outcome_raw_v1": ("raw_body",),
    "validate_synthetic_parent_freeze_v3_body_v1": ("raw_body",),
    "validate_provenance_fixture_v1": ("raw_body",),
    "_resolve_json_pointer_v1": ("raw_body", "pointer", "field"),
    "validate_synthetic_component_body_v1": (
        "raw_body",
        "ordered_components_raw",
        "parent_raw",
    ),
    "_validate_synthetic_graph_raw_v1": ("graph_raw", "parent_raw"),
    "validate_response_run_spec_fixture_v1": (
        "raw_body",
        "provenance_raw",
        "graph_raw",
    ),
    "validate_source_readout_response_raw_v1": (
        "raw_body",
        "run_spec_raw",
        "provenance_raw",
        "graph_raw",
    ),
    "_require_exact_dict_fields_v1": ("raw_body", "fields", "field"),
    "_require_sha256_v1": ("value", "field"),
    "_require_self_hash_v1": ("raw_body", "hash_field", "field"),
    "_validate_frozen_complex_tensor_raw_v1": ("raw_body", "field"),
    "validate_branch_attempt_v1": ("raw_body",),
}

TASK4_PUBLIC_VALIDATOR_SYMBOLS = {
    "validate_response_run_spec_fixture_v1",
    "validate_endpoint_reference_outcome_raw_v1",
    "validate_endpoint_shell_outcome_raw_v1",
    "validate_source_readout_response_raw_v1",
    "validate_synthetic_parent_freeze_v3_body_v1",
    "validate_synthetic_component_body_v1",
    "validate_provenance_fixture_v1",
    "validate_branch_attempt_v1",
}

TASK4_LITERAL_ASSIGNMENTS = {
    "_B7_RECORD_SCHEMAS_JSON_V1",
    "_B7_COMPONENT_CONTRACTS_JSON_V1",
}

TASK4_CALL_SHAPES = {
    "TypeError": ((1, ()),),
    "ValueError": ((1, ()),),
    "_canonical_equal_v1": ((3, ()),),
    "_component_by_id_v1": ((2, ()),),
    "_literal_wire_value_v1": ((1, ()),),
    "_record_schemas_v1": ((0, ()),),
    "_require_exact_dict_fields_v1": ((3, ()),),
    "_require_self_hash_v1": ((3, ()),),
    "_require_sha256_v1": ((2, ()),),
    "_resolve_json_pointer_v1": ((3, ()),),
    "_split_wire_top_level_v1": ((2, ()),),
    "_validate_frozen_complex_tensor_raw_v1": ((2, ()),),
    "_validate_record_raw_v1": ((4, ()),),
    "_validate_synthetic_graph_raw_v1": ((2, ()),),
    "_validate_wire_value_v1": ((5, ()),),
    "any": ((1, ()),),
    "canonical_json_bytes_v1": ((1, ()),),
    "canonical_sha_v1": ((1, ()),),
    "dimensions.split": ((1, ()),),
    "enumerate": ((1, ()),),
    "exact_text.isdigit": ((0, ()),),
    "failure.endswith": ((1, ()),),
    "int": ((1, ()),),
    "item.get": ((1, ()),),
    "json.loads": ((1, ()),),
    "len": ((1, ()),),
    "modifier.startswith": ((1, ()),),
    "pointer.removeprefix": ((1, ()),),
    "pointer.removeprefix().split": ((1, ()),),
    "pointer.startswith": ((1, ()),),
    "raw_body.items": ((0, ()),),
    "raw_token.replace": ((2, ()),),
    "raw_token.replace().replace": ((2, ()),),
    "result.append": ((1, ()),),
    "root_entries.append": ((1, ()),),
    "schemas.get": ((1, ()),),
    "set": ((1, ()),),
    "t_derivation.split": ((2, ()),),
    "t_derivation.startswith": ((1, ()),),
    "token.isdigit": ((0, ()),),
    "tuple": ((1, ()),),
    "type": ((1, ()),),
    "validate_endpoint_reference_outcome_raw_v1": ((1, ()),),
    "validate_provenance_fixture_v1": ((1, ()),),
    "validate_response_run_spec_fixture_v1": ((3, ()),),
    "validate_synthetic_component_body_v1": ((3, ()),),
    "validate_synthetic_parent_freeze_v3_body_v1": ((1, ()),),
    "value.lstrip": ((1, ()),),
    "value.lstrip().isdigit": ((0, ()),),
    "wire_type.removeprefix": ((1, ()),),
    "wire_type.startswith": ((1, ()),),
    "zip": ((2, ()),),
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
            if node.name in TASK3_FUNCTION_SIGNATURES:
                expected_arguments = (TASK3_FUNCTION_SIGNATURES[node.name],)
            else:
                expected_arguments = TASK4_FUNCTION_SIGNATURES[node.name]
            _assert_exact_function_shape(node, expected_arguments)

    assert top_level_assignments == {
        "B7_V91_PURE_REPLAY_PROJECTION_SHA256",
        *TASK4_LITERAL_ASSIGNMENTS,
    }
    assert top_level_functions == [
        *TASK3_FUNCTION_SIGNATURES,
        *TASK4_FUNCTION_SIGNATURES,
    ]
    assert TASK4_PUBLIC_VALIDATOR_SYMBOLS <= set(top_level_functions)

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
            scope = _enclosing_function_name(node, parents)
            if scope is None:
                assert node.id in {
                    "B7_V91_PURE_REPLAY_PROJECTION_SHA256",
                    *TASK4_LITERAL_ASSIGNMENTS,
                }
            elif scope in TASK3_FUNCTION_SIGNATURES or scope in {
                item[1] for item in TASK3_NESTED_FUNCTION_SIGNATURES
            }:
                assert node.id not in TASK3_RESERVED_CALL_ROOTS
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
            else:
                assert scope in TASK4_FUNCTION_SIGNATURES
                assert node.id not in FORBIDDEN_CALL_NAMES
                assert node.id not in FORBIDDEN_MODULE_ROOTS
        if isinstance(node, ast.Attribute) and isinstance(
            node.ctx, (ast.Store, ast.Del)
        ):
            raise AssertionError("attribute mutation is forbidden in the Task-3 core")
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            scope = _enclosing_function_name(node, parents)
            if scope in TASK3_FUNCTION_SIGNATURES or scope in {
                item[1] for item in TASK3_NESTED_FUNCTION_SIGNATURES
            }:
                attribute_parent = parents[node]
                assert isinstance(attribute_parent, ast.Call)
                assert attribute_parent.func is node
        if isinstance(node, ast.Call):
            target = _task3_call_target(node)
            assert target is not None, "dynamic call target is forbidden"
            if isinstance(node.func, ast.Name):
                assert node.func.id not in FORBIDDEN_CALL_NAMES
            if isinstance(node.func, ast.Attribute):
                assert _resolved_attribute_root(node.func) not in FORBIDDEN_MODULE_ROOTS
            scope = _enclosing_function_name(node, parents)
            assert scope is not None, "module-body calls are forbidden"
            if scope in TASK3_ALLOWED_CALL_TARGETS_BY_FUNCTION:
                lowered_target = target.casefold()
                assert not any(
                    token in lowered_target for token in TASK3_CAPABILITY_CALL_TOKENS
                )
                assert target in TASK3_ALLOWED_CALL_TARGETS_BY_FUNCTION[scope]
                shapes = (TASK3_CALL_SHAPES[target],)
            else:
                assert scope in TASK4_FUNCTION_SIGNATURES
                shapes = TASK4_CALL_SHAPES[target]
            assert (len(node.args), tuple(keyword.arg for keyword in node.keywords)) in shapes
            assert not any(isinstance(argument, ast.Starred) for argument in node.args)
            assert all(keyword.arg is not None for keyword in node.keywords)
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
            elif target == "json.loads" and scope == "strict_json_loads_v1":
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


def test_core_source_has_exact_task3_task4_symbols_imports_and_signatures() -> None:
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    _assert_core_source_contract(CORE_PATH.read_text(encoding="utf-8"))


def test_core_runtime_namespace_has_exact_task3_task4_symbols() -> None:
    core = _core_module()
    import_symbols = {"annotations", "hashlib", "json"}
    observed_public = {
        name
        for name in vars(core)
        if not name.startswith("__") and name not in import_symbols
        and not name.startswith("_")
    }
    expected_public = TASK3_PUBLIC_SYMBOLS | TASK4_PUBLIC_VALIDATOR_SYMBOLS
    assert observed_public == expected_public

    observed_private = {
        name for name in vars(core) if name.startswith("_") and not name.startswith("__")
    }
    expected_private = TASK4_LITERAL_ASSIGNMENTS | {
        name for name in TASK4_FUNCTION_SIGNATURES if name.startswith("_")
    }
    assert observed_private == expected_private


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
        source.replace(
            "def validate_response_run_spec_fixture_v1(\n    raw_body: object,",
            "def validate_response_run_spec_fixture_v1(\n    raw_body: object,\n    callback: object,",
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
            '    """Validate one B7 ResponseRunSpec-v3 raw fixture and supplied joins."""\n',
            '    """Validate one B7 ResponseRunSpec-v3 raw fixture and supplied joins."""\n'
            + "    if callable(raw_body):\n"
            + "        return raw_body()\n",
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


# Task 4 fixtures are deliberately independent of the not-yet-created Task 7
# D1 corpus.  They freeze legal raw production-body shapes without claiming D1
# corpus coverage.
def _task4_canonical_sha(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _task4_seal(raw_body: dict[str, object], hash_field: str) -> dict[str, object]:
    payload = {key: value for key, value in raw_body.items() if key != hash_field}
    sealed = dict(payload)
    sealed[hash_field] = _task4_canonical_sha(payload)
    return sealed


def _task4_tensor(shape: list[int]) -> dict[str, object]:
    entry_count = math.prod(shape)
    return _task4_seal(
        {
            "tensor_schema_version": "v3m0.frozen-complex-tensor.v1",
            "shape": shape,
            "values_wire": [[0.0, 0.0] for _ in range(entry_count)],
            "tensor_sha": "0" * 64,
        },
        "tensor_sha",
    )


def _task4_branch_attempt(
    branch: str = "actual",
) -> dict[str, object]:
    return _task4_seal(
        {
            "branch_attempt_schema_version": (
                "experimental.v3m0.b7.branch-attempt.v1"
            ),
            "branch": branch,
            "response_values": _task4_tensor([1, 1]),
            "bridge_audit": None,
            "failure": None,
            "attempt_sha": "0" * 64,
        },
        "attempt_sha",
    )


def test_task4_branch_attempt_accepts_fixture_independent_legal_raw_body() -> None:
    core = _core_module()
    raw_body = _task4_branch_attempt()

    assert core.validate_branch_attempt_v1(raw_body) is raw_body
    assert raw_body["attempt_sha"] == _task4_canonical_sha(
        {key: value for key, value in raw_body.items() if key != "attempt_sha"}
    )


@pytest.mark.parametrize(
    "attack",
    (
        "unknown",
        "missing",
        "field_order",
        "type",
        "nullability",
        "enum",
        "self_hash",
        "nested_self_hash",
        "cross_branch_failure",
        "response_failure_presence",
        "bridge_failure_presence",
    ),
)
def test_task4_branch_attempt_rejects_schema_hash_and_branch_attacks(
    attack: str,
) -> None:
    core = _core_module()
    raw_body = _task4_branch_attempt()
    if attack == "unknown":
        raw_body["caller_unknown"] = False
    elif attack == "missing":
        del raw_body["failure"]
    elif attack == "field_order":
        raw_body = {
            key: raw_body[key]
            for key in reversed(tuple(raw_body))
        }
    elif attack == "type":
        raw_body["branch"] = 1
    elif attack == "nullability":
        raw_body["response_values"] = None
    elif attack == "enum":
        raw_body["branch"] = "caller_branch"
    elif attack == "self_hash":
        raw_body["attempt_sha"] = "f" * 64
    elif attack == "nested_self_hash":
        assert isinstance(raw_body["response_values"], dict)
        raw_body["response_values"]["tensor_sha"] = "f" * 64
        raw_body = _task4_seal(raw_body, "attempt_sha")
    elif attack == "cross_branch_failure":
        raw_body["failure"] = "matched_ablated_response_failed"
        raw_body["response_values"] = None
        raw_body = _task4_seal(raw_body, "attempt_sha")
    elif attack == "response_failure_presence":
        raw_body["failure"] = "actual_response_failed"
        raw_body = _task4_seal(raw_body, "attempt_sha")
    elif attack == "bridge_failure_presence":
        raw_body["failure"] = "actual_bridge_failed"
        raw_body["response_values"] = None
        raw_body = _task4_seal(raw_body, "attempt_sha")

    with pytest.raises((TypeError, ValueError)):
        core.validate_branch_attempt_v1(raw_body)


_TASK4_V6_PATH = (
    REPOSITORY_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md"
)
_TASK4_V7_PATH = (
    REPOSITORY_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-prestructure-production-chain-v7-2026-08-02.md"
)
_TASK4_V8_PATH = (
    REPOSITORY_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-B7至B10-production-chain-v8-2026-08-02.md"
)
_TASK4_EMBEDDED_MARKERS = (
    (
        _TASK4_V6_PATH,
        "<!-- BEGIN V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->",
        "<!-- END V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->",
        "record_catalog",
    ),
    (
        _TASK4_V7_PATH,
        "<!-- BEGIN V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->",
        "<!-- END V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->",
        "record_catalog_delta",
    ),
    (
        _TASK4_V8_PATH,
        "<!-- BEGIN V3M0_PARENT_V3_B7_B10_V8_REGISTRY -->",
        "<!-- END V3M0_PARENT_V3_B7_B10_V8_REGISTRY -->",
        "record_catalog_delta",
    ),
)
_TASK4_NON_SELF_HASHED_RECORDS = {
    "AblationReplacement",
    "CoefficientRecord",
    "DirectionPathClosure",
    "Fp64RootIntervalEntry",
    "FrozenSyntheticTarget",
    "Primitive",
    "PrimitiveInterface",
    "PrimitiveTrace",
    "ProvenanceNode",
    "SelectedControlEvidenceRef",
    "ShellCandidatePointAttempt",
    "ShellPointAudit",
    "SourceReadoutBridgeMatrixAudit",
    "TaggedScalarWire",
}
_TASK4_CATALOG_CACHE: dict[str, dict[str, object]] | None = None


def _task4_embedded_registry(
    path: Path,
    begin: str,
    end: str,
) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    payload = text.split(begin, 1)[1].split(end, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("\n```")
    value = json.loads(payload.removeprefix("```json\n").removesuffix("\n```"))
    assert type(value) is dict
    return value


def _task4_effective_catalog() -> dict[str, dict[str, object]]:
    global _TASK4_CATALOG_CACHE
    if _TASK4_CATALOG_CACHE is not None:
        return _TASK4_CATALOG_CACHE
    catalog: dict[str, dict[str, object]] = {}
    for path, begin, end, key in _TASK4_EMBEDDED_MARKERS:
        registry = _task4_embedded_registry(path, begin, end)
        delta = registry[key]
        assert type(delta) is dict
        catalog.update(delta)
    p0_delta = _registry()["p0_record_catalog_delta"]
    assert type(p0_delta) is dict
    catalog.update(p0_delta)
    _TASK4_CATALOG_CACHE = catalog
    return catalog


def _task4_split_top_level(value: str, delimiter: str) -> list[str]:
    result: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(value):
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
        elif character == delimiter and depth == 0:
            result.append(value[start:index])
            start = index + 1
    result.append(value[start:])
    return result


def _task4_literal(token: str) -> object:
    if token == "true":
        return True
    if token == "false":
        return False
    if token.lstrip("-").isdigit():
        return int(token)
    return token


def _task4_minimal_wire(
    wire_type: str,
    nested_record: str | None,
    active: tuple[str, ...],
) -> object:
    if wire_type.startswith("Optional["):
        return None
    if nested_record is not None and wire_type.startswith("tuple["):
        body = wire_type[6:-1]
        parts = _task4_split_top_level(body, ";")
        modifiers = parts[1:]
        count = 0
        for modifier in modifiers:
            if modifier.startswith("exact=") and modifier[6:].isdigit():
                count = int(modifier[6:])
            elif modifier == "nonempty":
                count = max(count, 1)
        return [
            _task4_minimal_record(nested_record, active)
            for _ in range(count)
        ]
    if nested_record is not None:
        nested = _task4_minimal_record(nested_record, active)
        if nested_record == "FrozenComplexTensor":
            shape = [1]
            if wire_type.startswith("FrozenComplexTensor["):
                dimensions = wire_type.removeprefix("FrozenComplexTensor[")[:-1]
                shape = [int(item) for item in dimensions.split("x")]
            nested["shape"] = shape
            nested["values_wire"] = [[0.0, 0.0] for _ in range(math.prod(shape))]
            nested = _task4_resign_record("FrozenComplexTensor", nested)
        return nested
    if wire_type.startswith("Literal["):
        return _task4_literal(
            _task4_split_top_level(wire_type[8:-1], ",")[0]
        )
    if wire_type in {"sha256", "hex64"}:
        return "a" * 64
    if wire_type == "git-sha1":
        return "a" * 40
    if wire_type in {"str", "base64-be-f64-column"}:
        return "fixture-value"
    if wire_type == "UndefinedReason":
        return "response_null"
    if wire_type == "MechanismKind":
        return "target_blind"
    if wire_type == "ProvenanceOperation":
        return "derive"
    if wire_type == "bool":
        return False
    if wire_type == "int":
        return 1
    if wire_type in {"float", "float64"}:
        return 1.0
    if wire_type == "canonical-json-object":
        return {}
    if wire_type.startswith("tuple["):
        body = wire_type[6:-1]
        parts = _task4_split_top_level(body, ";")
        item_expression = parts[0]
        modifiers = parts[1:]
        count: int | None = None
        for modifier in modifiers:
            if modifier.startswith("exact=") and modifier[6:].isdigit():
                count = int(modifier[6:])
            elif modifier == "nonempty":
                count = max(count or 0, 1)
        items = _task4_split_top_level(item_expression, ",")
        if items[-1] == "...":
            count = 0 if count is None else count
            item_types = [items[0]] * count
        elif len(items) == 1:
            count = 1 if count is None else count
            item_types = [items[0]] * count
        else:
            item_types = items
        result = [
            _task4_minimal_wire(item_type, None, active)
            for item_type in item_types
        ]
        for modifier in modifiers:
            if modifier.startswith("value="):
                expected = _task4_literal(modifier[6:])
                result = [expected for _ in result]
        return result
    return "fixture-enum"


def _task4_self_hash_field(record_name: str) -> str | None:
    if record_name in _TASK4_NON_SELF_HASHED_RECORDS:
        return None
    if record_name == "BasisManifest":
        return "manifest_id"
    record = _task4_effective_catalog()[record_name]
    fields = record["field_specs"]
    assert type(fields) is list and fields
    final = fields[-1]
    if final["wire_type"] == "sha256":
        return final["name"]
    return None


def _task4_resign_record(
    record_name: str,
    raw_body: dict[str, object],
) -> dict[str, object]:
    hash_field = _task4_self_hash_field(record_name)
    if hash_field is None:
        return raw_body
    return _task4_seal(raw_body, hash_field)


def _task4_minimal_record(
    record_name: str,
    active: tuple[str, ...] = (),
) -> dict[str, object]:
    assert record_name not in active, f"unbroken required cycle at {record_name}"
    if record_name == "BlockStatus":
        return {"defined": False, "reason": "response_null"}
    record = _task4_effective_catalog()[record_name]
    fields = record["field_specs"]
    assert type(fields) is list
    raw_body = {
        field["name"]: _task4_minimal_wire(
            field["wire_type"],
            field.get("nested_record"),
            (*active, record_name),
        )
        for field in fields
    }
    if record_name == "FrozenComplexTensor":
        raw_body["tensor_schema_version"] = "v3m0.frozen-complex-tensor.v1"
    elif record_name == "BasisManifest":
        raw_body["channel_order"] = ["q0"]
        raw_body["vectors_wire"] = [[[0.0, 0.0]]]
    return _task4_resign_record(record_name, raw_body)


def _task4_clone(value: object) -> object:
    return json.loads(
        json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    )


def _task4_resign_tree(record_name: str, raw_body: dict[str, object]) -> None:
    catalog = _task4_effective_catalog()
    for field in catalog[record_name]["field_specs"]:
        nested = field.get("nested_record")
        value = raw_body[field["name"]]
        if nested is None or value is None:
            continue
        if type(value) is list:
            for item in value:
                assert type(item) is dict
                _task4_resign_tree(nested, item)
        else:
            assert type(value) is dict
            _task4_resign_tree(nested, value)
    hash_field = _task4_self_hash_field(record_name)
    if hash_field is not None:
        raw_body[hash_field] = _task4_canonical_sha(
            {key: value for key, value in raw_body.items() if key != hash_field}
        )


def _task4_status(defined: bool) -> dict[str, object]:
    return {"defined": defined, "reason": None if defined else "response_null"}


def _task4_endpoint_reference_outcome() -> dict[str, object]:
    outcome = _task4_minimal_record("EndpointReferenceOutcome")
    spec = outcome["reference_spec"]
    attempt = outcome["attempt_audit"]
    assert type(spec) is dict and type(attempt) is dict
    reference = _task4_minimal_record("EndpointReferenceProjector")
    spec["reference_reciprocal_index"] = [0]
    spec["preregistered_phase_bands"] = [[0.1, 0.2]]
    spec["expected_shell_rank"] = 1
    _task4_resign_tree("EndpointReferenceSpec", spec)
    attempt["reference_spec"] = _task4_clone(spec)
    attempt["candidate_phases"] = [0.15]
    attempt["candidate_ranks"] = [1]
    attempt["expected_shell_rank"] = 1
    attempt["candidate_participations"] = [1.0]
    attempt["runner_up_overlaps"] = [None]
    attempt["hermitian_residuals"] = [0.0]
    attempt["idempotent_residuals"] = [0.0]
    attempt["g_invariance_residuals"] = [0.0]
    attempt["eigenphase_residuals"] = [0.0]
    attempt["observed_competitor_gaps"] = [None]
    _task4_resign_tree("EndpointReferenceAttemptAudit", attempt)
    reference["control_registry_entry_sha"] = spec["control_registry_entry"]["entry_sha"]
    reference["actual_transition_sha"] = spec["actual_transition_sha"]
    reference["actual_dynamics_certificate_sha"] = spec[
        "actual_dynamics_certificate_sha"
    ]
    reference["reference_reciprocal_index"] = [0]
    reference["reference_phase"] = 0.15
    reference["rank"] = 1
    reference["projector"] = _task4_tensor([1, 1])
    _task4_resign_tree("EndpointReferenceProjector", reference)
    outcome["status"] = _task4_status(True)
    outcome["failure"] = None
    outcome["reference"] = reference
    _task4_resign_tree("EndpointReferenceOutcome", outcome)
    return outcome


def _task4_endpoint_shell_outcome() -> dict[str, object]:
    outcome = _task4_minimal_record("EndpointShellOutcome")
    reference_outcome = _task4_endpoint_reference_outcome()
    reference = reference_outcome["reference"]
    assert type(reference) is dict
    attempt = outcome["attempt_audit"]
    assert type(attempt) is dict
    shell_spec = attempt["shell_spec"]
    assert type(shell_spec) is dict
    shell_spec["endpoint_reference_projector"] = _task4_clone(reference)
    shell_spec["preregistered_phase_bands"] = [[0.1, 0.2]]
    shell_spec["candidate_fejer_order"] = 256
    _task4_resign_tree("EndpointShellSpec", shell_spec)
    attempt["point_attempts"] = []
    _task4_resign_tree("EndpointShellAttemptAudit", attempt)
    shell = _task4_minimal_record("EndpointShellManifest")
    shell["shell_spec"] = _task4_clone(shell_spec)
    shell["shell_phases"] = [0.15]
    shell["shell_projectors"] = _task4_tensor([1, 1, 1])
    shell["point_audits"] = [_task4_minimal_record("ShellPointAudit")]
    _task4_resign_tree("EndpointShellManifest", shell)
    outcome["status"] = _task4_status(True)
    outcome["failure"] = None
    outcome["reference_outcome"] = reference_outcome
    outcome["shell"] = shell
    _task4_resign_tree("EndpointShellOutcome", outcome)
    return outcome


def _task4_parent_body() -> dict[str, object]:
    parent = _task4_minimal_record("ParentFreezeV3Manifest")
    candidate = parent["reviewed_candidate_v3"]
    audit = parent["signing_audit"]
    assert type(candidate) is dict and type(audit) is dict
    parent["parent_freeze_schema_version"] = "v3m0.parent-freeze.v3"
    parent["preparation_commit_sha"] = "1" * 40
    parent["signing_commit_sha"] = "2" * 40
    candidate["candidate_schema_version"] = "v3m0.parent-freeze-candidate.v3"
    candidate["preparation_commit_sha"] = parent["preparation_commit_sha"]
    _task4_resign_tree("ParentFreezeCandidateV3Manifest", candidate)
    source_specs = (
        (
            "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md",
            "SIGNED_INCREMENTAL_ERRATUM",
            "C05_C18_SCENARIO_RESPONSE_GEOMETRY",
        ),
        (
            "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md",
            "SIGNED_CONSTRUCTION_ERRATUM",
            "C19_REAL20_REFREEZE_V2",
        ),
        (
            "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md",
            "SIGNED_ISSUANCE_PROTOCOL",
            "PARENT_V3_P_EPOCH_SIGNING",
        ),
        (
            "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md",
            "SIGNED_RUNTIME_AUTHORITY_PROTOCOL",
            "C19_METRIC_SUPPORT_AUTHORITY_V1",
        ),
    )
    references: list[dict[str, object]] = []
    for index, (path, role, scope) in enumerate(source_specs):
        reference = _task4_minimal_record("SignedSourceRefV2")
        reference.update(
            {
                "source_ref_schema_version": "v3m0.signed-source-ref.v2",
                "source_role": role,
                "source_scope": scope,
                "relative_path": path,
                "raw_sha256": f"{index + 1:x}" * 64,
                "preparation_commit_sha": parent["preparation_commit_sha"],
                "signing_commit_sha": parent["signing_commit_sha"],
            }
        )
        _task4_resign_tree("SignedSourceRefV2", reference)
        references.append(reference)
    parent["signed_source_refs"] = references

    closure = [["docsv3/fixture-reviewed.md", "9" * 64]]
    closure_root = _task4_canonical_sha(
        {
            "reviewed_path_closure_schema_version": (
                "v3m0.parent-reviewed-path-closure.v1"
            ),
            "entries": [
                {"relative_path": path, "raw_sha256": raw_sha}
                for path, raw_sha in closure
            ],
        }
    )
    receipts: list[dict[str, object]] = []
    for index, role in enumerate(
        (
            "MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW",
            "AUTHORITY_AND_BOUNDARY_REVIEW",
        )
    ):
        receipt = _task4_minimal_record("ParentReviewReceiptV1")
        receipt.update(
            {
                "receipt_schema_version": "v3m0.parent-review-receipt.v1",
                "review_role": role,
                "reviewer_id": f"fixture-reviewer-{index}",
                "reviewer_key_id": "SHA256:" + "A" * 43,
                "signature_algorithm": "openssh-ed25519-v1",
                "preparation_commit_sha": parent["preparation_commit_sha"],
                "reviewed_candidate_sha": candidate["candidate_sha"],
                "reviewed_path_closure": _task4_clone(closure),
                "reviewed_path_closure_sha": closure_root,
                "verdict": "PASS",
                "signature_armor": (
                    "-----BEGIN SSH SIGNATURE-----\nfixture\n"
                    "-----END SSH SIGNATURE-----"
                ),
            }
        )
        statement = {
            key: receipt[key]
            for key in (
                "receipt_schema_version",
                "review_role",
                "reviewer_id",
                "reviewer_key_id",
                "signature_algorithm",
                "preparation_commit_sha",
                "reviewed_candidate_sha",
                "reviewed_path_closure",
                "reviewed_path_closure_sha",
                "verdict",
            )
        }
        receipt["signed_statement_sha"] = _task4_canonical_sha(statement)
        _task4_resign_tree("ParentReviewReceiptV1", receipt)
        receipts.append(receipt)
    parent["review_receipts"] = receipts
    audit["audit_schema_version"] = "v3m0.parent-signing-audit.v1"
    audit["preparation_commit_sha"] = parent["preparation_commit_sha"]
    audit["signing_commit_sha"] = parent["signing_commit_sha"]
    audit["diff_allowlist_id"] = "parent-v3-signing-diff-v1"
    audit["review_receipt_shas"] = [item["receipt_sha"] for item in receipts]
    audit["signed_source_refs_root_sha"] = _task4_canonical_sha(
        {
            "signed_source_refs_schema_version": (
                "v3m0.signed-source-ref-tuple.v1"
            ),
            "entries": references,
        }
    )
    audit["reviewed_candidate_sha"] = candidate["candidate_sha"]
    audit["reviewed_path_closure_sha"] = closure_root
    audit["source_closure_sha"] = candidate["source_closure_sha"]
    _task4_resign_tree("ParentSigningAuditV1", audit)
    _task4_resign_tree("ParentFreezeV3Manifest", parent)
    return parent


def _task4_provenance_fixture() -> dict[str, object]:
    parent = _task4_parent_body()
    permit = _task4_minimal_record("CalibrationApplicationPermitV3")
    calibration = permit["calibration"]
    assert type(calibration) is dict
    calibration_outcome = calibration["calibration_outcome"]
    assert type(calibration_outcome) is dict
    selection = _task4_minimal_record("WindowThresholdSelection")
    selection["selected_fejer_order"] = 256
    _task4_resign_tree("WindowThresholdSelection", selection)
    calibration_outcome["status"] = _task4_status(True)
    calibration_outcome["selection"] = selection
    _task4_resign_tree("WindowCalibrationOutcome", calibration_outcome)
    permit["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
    permit["selected_fejer_order"] = 256
    contract = permit["current_scenario_response_contract"]
    assert type(contract) is dict
    response_grid = contract["response_grid"]
    assert type(response_grid) is dict
    response_grid["spatial_ndim"] = 1
    response_grid["torus_denominators"] = [8]
    response_grid["reciprocal_indices"] = [[0]]
    _task4_resign_tree("ResponseKGridManifest", response_grid)
    contract["response_reference_reciprocal_index"] = [0]
    contract["preregistered_phase_bands"] = [[0.1, 0.2]]
    calibration_spec = contract["current_readout_calibration_spec"]
    assert type(calibration_spec) is dict
    calibration_spec["source_metric_whitener"] = _task4_tensor([10, 10])
    calibration_spec["h_metric_whitener"] = _task4_tensor([10, 10])
    calibration_spec["curvature_incidence_operator"] = _task4_tensor([6, 10])
    calibration_spec["curvature_metric_whitener"] = _task4_tensor([6, 6])
    _task4_resign_tree("CurrentReadoutCalibrationSpecV3", calibration_spec)
    _task4_resign_tree("CurrentScenarioResponseContractV3", contract)
    _task4_resign_tree("CalibrationApplicationPermitV3", permit)

    materialization = _task4_minimal_record("ApplicationScenarioMaterializationV3")
    materialization["permit"] = _task4_clone(permit)
    materialization["current_application_authority"] = _task4_clone(
        permit["current_application_authority"]
    )
    materialization["current_scenario_authority"] = _task4_clone(
        permit["current_scenario_authority"]
    )
    materialization["current_scenario_response_contract"] = _task4_clone(
        permit["current_scenario_response_contract"]
    )
    basis = materialization["basis_contract"]
    assert type(basis) is dict
    channels = [f"q{index}" for index in range(20)]
    basis["state_schema_id"] = "v3m0.c19-real-canonical-state.v2"
    basis["channel_order"] = channels
    for role, field in (
        ("source", "scenario_source_basis"),
        ("readout", "scenario_readout_basis"),
    ):
        basis_body = basis[field]
        assert type(basis_body) is dict
        basis_body["role"] = role
        basis_body["state_schema_id"] = basis["state_schema_id"]
        basis_body["channel_order"] = channels
        basis_body["vectors_wire"] = [
            [[0.0, 0.0] for _ in channels] for _ in range(10)
        ]
        _task4_resign_tree("BasisManifest", basis_body)
    basis["source_injection"] = _task4_tensor([20, 10])
    basis["readout_coisometry"] = _task4_tensor([10, 20])
    basis["source_trial_vectors"] = _task4_tensor([10, 10])
    basis["expected_actual_shell_rank"] = 10
    basis["expected_matched_shell_rank"] = 10
    _task4_resign_tree("C19BasisContractV2", basis)
    _task4_resign_tree("ApplicationScenarioMaterializationV3", materialization)

    actual_bridge = _task4_minimal_record("BridgeGridAuthorityV3")
    actual_bridge["materialization"] = _task4_clone(materialization)
    actual_binding = actual_bridge["factory_binding"]
    assert type(actual_binding) is dict
    actual_binding["branch"] = "actual"
    _task4_resign_tree("FactoryBranchBindingV3", actual_binding)
    bridge_grid = actual_bridge["bridge_grid"]
    assert type(bridge_grid) is dict
    bridge_grid["spatial_shape"] = [8]
    bridge_grid["torus_denominators"] = [8]
    bridge_grid["reciprocal_indices"] = [[0]]
    _task4_resign_tree("BridgeKGridManifest", bridge_grid)
    _task4_resign_tree("BridgeGridAuthorityV3", actual_bridge)

    matched_bridge = _task4_clone(actual_bridge)
    assert type(matched_bridge) is dict
    matched_binding = matched_bridge["factory_binding"]
    assert type(matched_binding) is dict
    matched_binding["branch"] = "matched_ablated"
    _task4_resign_tree("FactoryBranchBindingV3", matched_binding)
    _task4_resign_tree("BridgeGridAuthorityV3", matched_bridge)

    fixture = {
        "provenance_fixture_schema_version": (
            "experimental.v3m0.b7.provenance-fixture.v1"
        ),
        "parent_freeze_v3_body": parent,
        "permit_body": permit,
        "materialization_body": materialization,
        "current_scenario_response_contract_v3_body": _task4_clone(
            permit["current_scenario_response_contract"]
        ),
        "actual_bridge_grid_authority_body": actual_bridge,
        "matched_ablated_bridge_grid_authority_body": matched_bridge,
        "provenance_fixture_sha": "0" * 64,
    }
    return _task4_seal(fixture, "provenance_fixture_sha")


def _task4_component_wrapper(
    component_id: str,
    complete_body: dict[str, object],
) -> dict[str, object]:
    entry = next(
        item
        for item in _registry()["lab_contract"]["synthetic_component_registry"]
        if item["component_id"] == component_id
    )
    hash_field = entry["self_hash_field"]
    body = {
        "component_body_schema_version": (
            "experimental.v3m0.b7.synthetic-component-body.v1"
        ),
        "component_id": component_id,
        "body_type": entry["body_type"],
        "complete_body": complete_body,
        "body_raw_canonical_sha256": _task4_canonical_sha(complete_body),
        "body_self_hash_field": hash_field,
        "body_self_hash_value": complete_body[hash_field],
        "lineage_parent_component_ids": entry["lineage_parent_component_ids"],
        "fejer_order": 256,
        "component_sha": "0" * 64,
    }
    return _task4_seal(body, "component_sha")


def _task4_graph_manifest(
    provenance: dict[str, object],
) -> dict[str, object]:
    parent = provenance["parent_freeze_v3_body"]
    permit = provenance["permit_body"]
    materialization = provenance["materialization_body"]
    actual_bridge = provenance["actual_bridge_grid_authority_body"]
    matched_bridge = provenance["matched_ablated_bridge_grid_authority_body"]
    assert all(
        type(item) is dict
        for item in (parent, permit, materialization, actual_bridge, matched_bridge)
    )
    selection = permit["calibration"]["calibration_outcome"]["selection"]
    assert type(selection) is dict

    actual_transition = _task4_minimal_record("TransitionAuthorityV3")
    actual_transition["materialization"] = _task4_clone(materialization)
    actual_transition["factory_binding"]["branch"] = "actual"
    _task4_resign_tree("TransitionAuthorityV3", actual_transition)
    matched_transition = _task4_clone(actual_transition)
    assert type(matched_transition) is dict
    matched_transition["factory_binding"]["branch"] = "matched_ablated"
    _task4_resign_tree("TransitionAuthorityV3", matched_transition)

    actual_metric = _task4_minimal_record("MetricSignedSupportAttestationV1")
    actual_metric["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
    actual_metric["application_scenario_materialization_v3_sha"] = materialization[
        "materialization_sha"
    ]
    actual_metric["factory_role"] = "actual"
    _task4_resign_tree("MetricSignedSupportAttestationV1", actual_metric)
    matched_metric = _task4_clone(actual_metric)
    assert type(matched_metric) is dict
    matched_metric["factory_role"] = "matched_ablated"
    _task4_resign_tree("MetricSignedSupportAttestationV1", matched_metric)

    def certification(
        transition: dict[str, object],
        metric: dict[str, object],
        bridge: dict[str, object],
    ) -> dict[str, object]:
        certificate = _task4_minimal_record("DynamicsCertificateV3")
        certificate["parent_freeze_v3"] = _task4_clone(parent)
        certificate["materialization"] = _task4_clone(materialization)
        certificate["transition_authority"] = _task4_clone(transition)
        certificate["metric_attestation"] = _task4_clone(metric)
        certificate["bridge_grid_authority"] = _task4_clone(bridge)
        dynamics_grid = certificate["dynamics_grid_authority"]
        assert type(dynamics_grid) is dict
        dynamics_grid["transition_authority"] = _task4_clone(transition)
        dynamics_grid["metric_support_attestation"] = _task4_clone(metric)
        _task4_resign_tree("DynamicsGridAuthorityV3", dynamics_grid)
        bridge_spec = certificate["full_state_bridge_spec"]
        assert type(bridge_spec) is dict
        bridge_spec["bridge_grid"] = _task4_clone(bridge["bridge_grid"])
        bridge_spec["macro_steps"] = [1]
        bridge_spec["bridge_tolerance"] = permit[
            "current_scenario_response_contract"
        ]["bridge_tolerance"]
        _task4_resign_tree("FullStateBridgeSpec", bridge_spec)
        _task4_resign_tree("DynamicsCertificateV3", certificate)
        outcome = _task4_minimal_record("DynamicsCertificationOutcomeV3")
        attempt = outcome["attempt_audit"]
        assert type(attempt) is dict
        attempt["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
        attempt["materialization_sha"] = materialization["materialization_sha"]
        attempt["transition_authority_sha"] = transition[
            "transition_authority_sha"
        ]
        attempt["metric_attestation_sha"] = metric["attestation_sha"]
        attempt["bridge_grid_authority_sha"] = bridge["grid_authority_sha"]
        attempt["first_failure"] = None
        _task4_resign_tree("DynamicsCertificationAttemptAuditV3", attempt)
        outcome["status"] = _task4_status(True)
        outcome["failure"] = None
        outcome["certificate"] = certificate
        _task4_resign_tree("DynamicsCertificationOutcomeV3", outcome)
        return outcome

    actual_certificate = certification(actual_transition, actual_metric, actual_bridge)
    matched_certificate = certification(
        matched_transition,
        matched_metric,
        matched_bridge,
    )
    complete_bodies = {
        "calibration_selection": selection,
        "permit": permit,
        "materialization": materialization,
        "actual_transition_outcome": actual_transition,
        "matched_ablated_transition_outcome": matched_transition,
        "actual_metric_authority": actual_metric,
        "matched_ablated_metric_authority": matched_metric,
        "actual_bridge_grid_authority": actual_bridge,
        "matched_ablated_bridge_grid_authority": matched_bridge,
        "actual_certificate_outcome": actual_certificate,
        "matched_ablated_certificate_outcome": matched_certificate,
    }
    component_order = _registry()["lab_contract"]["synthetic_graph_contract"][
        "component_order"
    ]
    components = [
        _task4_component_wrapper(component_id, complete_bodies[component_id])
        for component_id in component_order
    ]
    root_entries = [
        {
            "component_id": component["component_id"],
            "body_self_hash_value": component["body_self_hash_value"],
        }
        for component in components
    ]
    bindings = [
        _task4_seal(
            {
                "binding_schema_version": (
                    "experimental.v3m0.b7.t-bearer-binding.v1"
                ),
                "component_id": component["component_id"],
                "body_sha": component["body_self_hash_value"],
                "fejer_order": 256,
                "binding_sha": "0" * 64,
            },
            "binding_sha",
        )
        for component in components
    ]
    by_id = {component["component_id"]: component for component in components}
    graph = {
        "graph_manifest_schema_version": (
            "experimental.v3m0.b7.synthetic-graph-manifest.v1"
        ),
        "graph_profile_id": (
            "v3m0-b7-d1-nonauthority-synthetic-private-graph-v1"
        ),
        "authority_state": "NON_AUTHORITY_SYNTHETIC",
        "parent_freeze_v3_body": _task4_clone(parent),
        "parent_freeze_v3_sha": parent["parent_freeze_v3_sha"],
        "synthetic_graph_component_root_sha": _task4_canonical_sha(root_entries),
        "selected_fejer_order": 256,
        "calibration_selection_sha": by_id["calibration_selection"][
            "body_self_hash_value"
        ],
        "permit_sha": by_id["permit"]["body_self_hash_value"],
        "permit_fejer_order": 256,
        "materialization_sha": by_id["materialization"]["body_self_hash_value"],
        "materialization_fejer_order": 256,
        "actual_transition_outcome_sha": by_id["actual_transition_outcome"][
            "body_self_hash_value"
        ],
        "matched_ablated_transition_outcome_sha": by_id[
            "matched_ablated_transition_outcome"
        ]["body_self_hash_value"],
        "actual_metric_authority_sha": by_id["actual_metric_authority"][
            "body_self_hash_value"
        ],
        "matched_ablated_metric_authority_sha": by_id[
            "matched_ablated_metric_authority"
        ]["body_self_hash_value"],
        "actual_bridge_grid_authority_sha": by_id[
            "actual_bridge_grid_authority"
        ]["body_self_hash_value"],
        "matched_ablated_bridge_grid_authority_sha": by_id[
            "matched_ablated_bridge_grid_authority"
        ]["body_self_hash_value"],
        "actual_certificate_outcome_sha": by_id["actual_certificate_outcome"][
            "body_self_hash_value"
        ],
        "matched_ablated_certificate_outcome_sha": by_id[
            "matched_ablated_certificate_outcome"
        ]["body_self_hash_value"],
        "ordered_component_bodies": components,
        "ordered_t_bearer_bindings": bindings,
        "graph_sha": "0" * 64,
    }
    return _task4_seal(graph, "graph_sha")


def _task4_response_run_spec(
    provenance: dict[str, object],
    graph: dict[str, object],
) -> dict[str, object]:
    spec = _task4_minimal_record("ResponseRunSpecV3")
    parent = provenance["parent_freeze_v3_body"]
    permit = provenance["permit_body"]
    materialization = provenance["materialization_body"]
    contract = provenance["current_scenario_response_contract_v3_body"]
    actual_bridge = provenance["actual_bridge_grid_authority_body"]
    assert all(
        type(item) is dict
        for item in (parent, permit, materialization, contract, actual_bridge)
    )
    calibration = permit["calibration"]
    outcome = calibration["calibration_outcome"]
    selection = outcome["selection"]
    window_protocol = outcome["manifest"]["window_protocol"]
    basis = materialization["basis_contract"]
    assert all(
        type(item) is dict
        for item in (calibration, outcome, selection, window_protocol, basis)
    )
    spec.update(
        {
            "parent_freeze_v3_sha": parent["parent_freeze_v3_sha"],
            "permit_sha": permit["permit_sha"],
            "materialization_sha": materialization["materialization_sha"],
            "window_calibration_v3_sha": calibration["calibration_v3_sha"],
            "window_protocol_sha": window_protocol["protocol_sha"],
            "window_selection_sha": selection["selection_sha"],
            "current_scenario_response_contract_v3_sha": contract[
                "response_contract_sha"
            ],
            "application_instance_id": contract["application_instance_id"],
            "scenario_id": contract["scenario_id"],
            "scenario_sha": permit["current_scenario_authority"][
                "scenario_authority_sha"
            ],
            "selected_fejer_order": 256,
            "channel_order": list(basis["channel_order"]),
            "spatial_shape": [8],
            "source_basis": _task4_clone(basis["scenario_source_basis"]),
            "readout_basis": _task4_clone(basis["scenario_readout_basis"]),
            "source_injection_isometry": _task4_clone(basis["source_injection"]),
            "readout_coisometry": _task4_clone(basis["readout_coisometry"]),
            "response_grid": _task4_clone(contract["response_grid"]),
            "source_readout_bridge_grid": _task4_clone(
                actual_bridge["bridge_grid"]
            ),
            "source_readout_bridge_steps": [1],
            "reference_reciprocal_index": list(
                contract["response_reference_reciprocal_index"]
            ),
            "preregistered_phase_bands": _task4_clone(
                contract["preregistered_phase_bands"]
            ),
            "expected_shell_rank": 10,
            "source_trial_vectors": _task4_clone(basis["source_trial_vectors"]),
            "bridge_tolerance": contract["bridge_tolerance"],
            "current_readout_calibration_spec": _task4_clone(
                contract["current_readout_calibration_spec"]
            ),
            "actual_bridge_grid_authority_sha": graph[
                "actual_bridge_grid_authority_sha"
            ],
            "matched_ablated_bridge_grid_authority_sha": graph[
                "matched_ablated_bridge_grid_authority_sha"
            ],
        }
    )
    channels = [f"q{index}" for index in range(20)]
    spec["channel_order"] = channels
    for role, field in (("source", "source_basis"), ("readout", "readout_basis")):
        basis_body = spec[field]
        assert type(basis_body) is dict
        basis_body["role"] = role
        basis_body["state_schema_id"] = spec["state_schema_id"]
        basis_body["channel_order"] = channels
        basis_body["vectors_wire"] = [
            [[0.0, 0.0] for _ in channels] for _ in range(10)
        ]
        _task4_resign_tree("BasisManifest", basis_body)
    spec["source_injection_isometry"] = _task4_tensor([20, 10])
    spec["readout_coisometry"] = _task4_tensor([10, 20])
    spec["source_trial_vectors"] = _task4_tensor([10, 10])
    response_grid = spec["response_grid"]
    assert type(response_grid) is dict
    response_grid["spatial_ndim"] = 1
    response_grid["torus_denominators"] = [8]
    response_grid["reciprocal_indices"] = [[0]]
    _task4_resign_tree("ResponseKGridManifest", response_grid)
    spec["reference_reciprocal_index"] = [0]
    spec["preregistered_phase_bands"] = [[0.1, 0.2]]
    calibration_spec = spec["current_readout_calibration_spec"]
    assert type(calibration_spec) is dict
    calibration_spec["source_metric_whitener"] = _task4_tensor([10, 10])
    calibration_spec["h_metric_whitener"] = _task4_tensor([10, 10])
    calibration_spec["curvature_incidence_operator"] = _task4_tensor([6, 10])
    calibration_spec["curvature_metric_whitener"] = _task4_tensor([6, 6])
    _task4_resign_tree("CurrentReadoutCalibrationSpecV3", calibration_spec)
    _task4_resign_tree("ResponseRunSpecV3", spec)
    return spec


def _task4_component_by_id(
    graph: dict[str, object],
    component_id: str,
) -> dict[str, object]:
    return next(
        component
        for component in graph["ordered_component_bodies"]
        if component["component_id"] == component_id
    )


def _task4_source_response(
    branch: str,
    run_spec: dict[str, object],
    graph: dict[str, object],
) -> dict[str, object]:
    response = _task4_minimal_record("SourceReadoutResponse")
    prefix = "actual" if branch == "actual" else "matched_ablated"
    transition = _task4_component_by_id(
        graph,
        f"{prefix}_transition_outcome",
    )["complete_body"]
    certificate_outcome = _task4_component_by_id(
        graph,
        f"{prefix}_certificate_outcome",
    )["complete_body"]
    assert type(transition) is dict and type(certificate_outcome) is dict
    certificate = certificate_outcome["certificate"]
    assert type(certificate) is dict
    factory_sha = transition["factory_binding"]["factory"]["factory_sha"]
    transition_sha = transition["measured_transition"]["transition_sha"]
    certificate_sha = certificate["certificate_sha"]
    response.update(
        {
            "branch": branch,
            "factory_sha": factory_sha,
            "transition_sha": transition_sha,
            "dynamics_certificate_sha": certificate_sha,
            "source_basis": _task4_clone(run_spec["source_basis"]),
            "readout_basis": _task4_clone(run_spec["readout_basis"]),
            "run_spec_sha": run_spec["run_spec_sha"],
        }
    )
    bridge = response["bridge_audit"]
    assert type(bridge) is dict
    bridge.update(
        {
            "branch": branch,
            "factory_sha": factory_sha,
            "transition_sha": transition_sha,
            "dynamics_certificate_sha": certificate_sha,
            "run_spec_sha": run_spec["run_spec_sha"],
            "source_metric_whitener_sha": run_spec[
                "current_readout_calibration_spec"
            ]["source_metric_whitener"]["tensor_sha"],
            "readout_calibration_spec_sha": run_spec[
                "current_readout_calibration_spec"
            ]["spec_sha"],
        }
    )
    matrix = _task4_minimal_record("SourceReadoutBridgeMatrixAudit")
    matrix["reciprocal_index"] = [0]
    matrix["macro_steps"] = 1
    matrix["raw_difference_matrix"] = _task4_tensor([10, 10])
    bridge["matrix_audits"] = [matrix]
    _task4_resign_tree("SourceReadoutBridgeAudit", bridge)
    response["values"] = _task4_tensor([1, 10, 10])
    _task4_resign_tree("SourceReadoutResponse", response)
    return response


def test_task4_embedded_schema_literals_recompute_from_pinned_registries() -> None:
    core = _core_module()
    catalog = _task4_effective_catalog()
    roots = [
        "ParentFreezeV3Manifest",
        "WindowThresholdSelection",
        "CalibrationApplicationPermitV3",
        "ApplicationScenarioMaterializationV3",
        "TransitionAuthorityV3",
        "MetricSignedSupportAttestationV1",
        "BridgeGridAuthorityV3",
        "DynamicsCertificationOutcomeV3",
        "ResponseRunSpecV3",
        "EndpointReferenceOutcome",
        "EndpointShellOutcome",
        "SourceReadoutResponse",
        "CurrentScenarioResponseContractV3",
    ]
    closure: set[str] = set()
    pending = list(roots)
    while pending:
        record_name = pending.pop()
        if record_name in closure:
            continue
        closure.add(record_name)
        for field in catalog[record_name]["field_specs"]:
            nested = field.get("nested_record")
            if nested is not None:
                pending.append(nested)
    expected_schemas: dict[str, object] = {}
    for record_name in sorted(closure):
        fields = catalog[record_name]["field_specs"]
        hash_field = _task4_self_hash_field(record_name)
        expected_schemas[record_name] = [
            hash_field,
            [
                [field["name"], field["wire_type"], field.get("nested_record")]
                for field in fields
            ],
        ]
    assert json.loads(core._B7_RECORD_SCHEMAS_JSON_V1) == expected_schemas

    expected_components = [
        [
            entry["component_id"],
            entry["body_type"],
            entry["body_type"].rsplit(".", 1)[1],
            entry["self_hash_field"],
            entry["lineage_parent_component_ids"],
            entry["lineage_bindings"],
            entry["required_body_predicates"],
            entry["t_derivation"],
        ]
        for entry in _registry()["lab_contract"]["synthetic_component_registry"]
    ]
    assert json.loads(core._B7_COMPONENT_CONTRACTS_JSON_V1) == expected_components


def test_task4_branch_attempt_strictly_validates_present_bridge_raw_tree() -> None:
    core = _core_module()
    raw = _task4_branch_attempt()
    bridge = _task4_minimal_record("SourceReadoutBridgeAudit")
    bridge["branch"] = "actual"
    matrix = _task4_minimal_record("SourceReadoutBridgeMatrixAudit")
    matrix["reciprocal_index"] = [0]
    matrix["macro_steps"] = 1
    matrix["raw_difference_matrix"] = _task4_tensor([1, 1])
    bridge["matrix_audits"] = [matrix]
    _task4_resign_tree("SourceReadoutBridgeAudit", bridge)
    raw["bridge_audit"] = bridge
    raw = _task4_seal(raw, "attempt_sha")
    assert core.validate_branch_attempt_v1(raw) is raw

    hostile = _task4_clone(raw)
    assert type(hostile) is dict
    hostile["bridge_audit"]["bridge_sha"] = "f" * 64
    hostile = _task4_seal(hostile, "attempt_sha")
    with pytest.raises((TypeError, ValueError)):
        core.validate_branch_attempt_v1(hostile)


def test_task4_endpoint_reference_validator_covers_legal_and_hostile_raw_trees() -> None:
    core = _core_module()
    legal = _task4_endpoint_reference_outcome()
    assert core.validate_endpoint_reference_outcome_raw_v1(legal) is legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "status_presence",
        "attempt_spec_splice",
        "reference_binding_splice",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["failure"] = 1
        elif attack == "self_hash":
            raw["outcome_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["reference_spec"]["reference_spec_sha"] = "f" * 64
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "status_presence":
            raw["status"] = _task4_status(False)
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "attempt_spec_splice":
            raw["attempt_audit"]["reference_spec"]["actual_factory_sha"] = "f" * 64
            _task4_resign_tree(
                "EndpointReferenceAttemptAudit",
                raw["attempt_audit"],
            )
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "reference_binding_splice":
            raw["reference"]["actual_transition_sha"] = "f" * 64
            _task4_resign_tree("EndpointReferenceProjector", raw["reference"])
            raw = _task4_seal(raw, "outcome_sha")
        with pytest.raises((TypeError, ValueError)):
            core.validate_endpoint_reference_outcome_raw_v1(raw)


def test_task4_endpoint_shell_validator_covers_legal_and_hostile_raw_trees() -> None:
    core = _core_module()
    legal = _task4_endpoint_shell_outcome()
    assert core.validate_endpoint_shell_outcome_raw_v1(legal) is legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "status_presence",
        "attempt_shell_spec_splice",
        "shell_reference_splice",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["failure"] = 1
        elif attack == "self_hash":
            raw["outcome_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["attempt_audit"]["attempt_sha"] = "f" * 64
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "status_presence":
            raw["status"] = _task4_status(False)
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "attempt_shell_spec_splice":
            raw["attempt_audit"]["shell_spec"]["candidate_fejer_order"] = 128
            _task4_resign_tree("EndpointShellAttemptAudit", raw["attempt_audit"])
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "shell_reference_splice":
            raw["shell"]["shell_spec"]["endpoint_reference_projector"][
                "actual_transition_sha"
            ] = "f" * 64
            _task4_resign_tree("EndpointShellManifest", raw["shell"])
            raw = _task4_seal(raw, "outcome_sha")
        with pytest.raises((TypeError, ValueError)):
            core.validate_endpoint_shell_outcome_raw_v1(raw)


def test_task4_synthetic_parent_validator_covers_recursive_and_join_attacks() -> None:
    core = _core_module()
    legal = _task4_parent_body()
    assert core.validate_synthetic_parent_freeze_v3_body_v1(legal) is legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "candidate_preparation_join",
        "audit_signing_join",
        "audit_candidate_join",
        "source_ref_commit_join",
        "signed_source_root",
        "receipt_statement_root",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["authority_state"] = 1
        elif attack == "self_hash":
            raw["parent_freeze_v3_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["reviewed_candidate_v3"]["candidate_sha"] = "f" * 64
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "candidate_preparation_join":
            raw["reviewed_candidate_v3"]["preparation_commit_sha"] = "3" * 40
            _task4_resign_tree(
                "ParentFreezeCandidateV3Manifest",
                raw["reviewed_candidate_v3"],
            )
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "audit_signing_join":
            raw["signing_audit"]["signing_commit_sha"] = "3" * 40
            _task4_resign_tree("ParentSigningAuditV1", raw["signing_audit"])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "audit_candidate_join":
            raw["signing_audit"]["reviewed_candidate_sha"] = "f" * 64
            _task4_resign_tree("ParentSigningAuditV1", raw["signing_audit"])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "source_ref_commit_join":
            raw["signed_source_refs"][0]["signing_commit_sha"] = "3" * 40
            _task4_resign_tree("SignedSourceRefV2", raw["signed_source_refs"][0])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "signed_source_root":
            raw["signing_audit"]["signed_source_refs_root_sha"] = "f" * 64
            _task4_resign_tree("ParentSigningAuditV1", raw["signing_audit"])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "receipt_statement_root":
            receipt = raw["review_receipts"][0]
            receipt["signed_statement_sha"] = "f" * 64
            _task4_resign_tree("ParentReviewReceiptV1", receipt)
            raw["signing_audit"]["review_receipt_shas"][0] = receipt[
                "receipt_sha"
            ]
            _task4_resign_tree("ParentSigningAuditV1", raw["signing_audit"])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        with pytest.raises((TypeError, ValueError)):
            core.validate_synthetic_parent_freeze_v3_body_v1(raw)


def test_task4_provenance_validator_covers_recursive_and_lineage_attacks() -> None:
    core = _core_module()
    legal = _task4_provenance_fixture()
    assert core.validate_provenance_fixture_v1(legal) is legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "permit_parent_join",
        "materialization_permit_join",
        "current_contract_join",
        "bridge_identity",
        "bridge_grid_join",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["permit_body"] = []
        elif attack == "self_hash":
            raw["provenance_fixture_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["permit_body"]["permit_sha"] = "f" * 64
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "permit_parent_join":
            raw["permit_body"]["parent_freeze_v3_sha"] = "f" * 64
            _task4_resign_tree("CalibrationApplicationPermitV3", raw["permit_body"])
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "materialization_permit_join":
            raw["materialization_body"]["permit"]["permit_scope_id"] = "splice"
            _task4_resign_tree(
                "ApplicationScenarioMaterializationV3",
                raw["materialization_body"],
            )
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "current_contract_join":
            raw["current_scenario_response_contract_v3_body"][
                "application_instance_id"
            ] = "splice"
            _task4_resign_tree(
                "CurrentScenarioResponseContractV3",
                raw["current_scenario_response_contract_v3_body"],
            )
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "bridge_identity":
            raw["matched_ablated_bridge_grid_authority_body"] = _task4_clone(
                raw["actual_bridge_grid_authority_body"]
            )
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "bridge_grid_join":
            raw["matched_ablated_bridge_grid_authority_body"]["bridge_grid"][
                "reciprocal_indices"
            ] = [[1]]
            _task4_resign_tree(
                "BridgeGridAuthorityV3",
                raw["matched_ablated_bridge_grid_authority_body"],
            )
            raw = _task4_seal(raw, "provenance_fixture_sha")
        with pytest.raises((TypeError, ValueError)):
            core.validate_provenance_fixture_v1(raw)


def test_task4_synthetic_component_validator_covers_metadata_body_and_t() -> None:
    core = _core_module()
    parent = _task4_parent_body()
    selection = _task4_minimal_record("WindowThresholdSelection")
    selection["selected_fejer_order"] = 256
    _task4_resign_tree("WindowThresholdSelection", selection)
    legal = _task4_component_wrapper("calibration_selection", selection)
    ordered = [legal]
    assert core.validate_synthetic_component_body_v1(legal, ordered, parent) is legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "body_type",
        "raw_sha",
        "self_hash_field",
        "lineage",
        "fejer_order",
        "duplicate_order",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["component_id"] = 1
        elif attack == "self_hash":
            raw["component_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["complete_body"]["selection_sha"] = "f" * 64
            raw["body_raw_canonical_sha256"] = _task4_canonical_sha(
                raw["complete_body"]
            )
            raw["body_self_hash_value"] = "f" * 64
            raw = _task4_seal(raw, "component_sha")
        elif attack == "body_type":
            raw["body_type"] = "caller.Type"
            raw = _task4_seal(raw, "component_sha")
        elif attack == "raw_sha":
            raw["body_raw_canonical_sha256"] = "f" * 64
            raw = _task4_seal(raw, "component_sha")
        elif attack == "self_hash_field":
            raw["body_self_hash_field"] = "caller_sha"
            raw = _task4_seal(raw, "component_sha")
        elif attack == "lineage":
            raw["lineage_parent_component_ids"] = ["permit"]
            raw = _task4_seal(raw, "component_sha")
        elif attack == "fejer_order":
            raw["fejer_order"] = 128
            raw = _task4_seal(raw, "component_sha")
        elif attack == "duplicate_order":
            pass
        ordered_attack = [raw, _task4_clone(raw)] if attack == "duplicate_order" else [raw]
        with pytest.raises((TypeError, ValueError)):
            core.validate_synthetic_component_body_v1(raw, ordered_attack, parent)


def test_task4_all_eleven_synthetic_components_validate_in_frozen_order() -> None:
    core = _core_module()
    provenance = _task4_provenance_fixture()
    graph = _task4_graph_manifest(provenance)
    ordered = graph["ordered_component_bodies"]
    parent = provenance["parent_freeze_v3_body"]
    expected_order = _registry()["lab_contract"]["synthetic_graph_contract"][
        "component_order"
    ]
    assert [item["component_id"] for item in ordered] == expected_order
    for component in ordered:
        assert (
            core.validate_synthetic_component_body_v1(component, ordered, parent)
            is component
        )


def test_task4_response_run_spec_validator_covers_external_join_attacks() -> None:
    core = _core_module()
    provenance = _task4_provenance_fixture()
    graph = _task4_graph_manifest(provenance)
    legal = _task4_response_run_spec(provenance, graph)
    assert (
        core.validate_response_run_spec_fixture_v1(legal, provenance, graph)
        is legal
    )

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "parent_join",
        "permit_join",
        "materialization_join",
        "contract_join",
        "t_join",
        "basis_rank",
        "bridge_grid_join",
        "bridge_authority_join",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["selected_fejer_order"] = 256.0
        elif attack == "self_hash":
            raw["run_spec_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["source_basis"]["manifest_id"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "parent_join":
            raw["parent_freeze_v3_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "permit_join":
            raw["permit_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "materialization_join":
            raw["materialization_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "contract_join":
            raw["current_scenario_response_contract_v3_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "t_join":
            raw["selected_fejer_order"] = 128
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "basis_rank":
            raw["source_basis"]["vectors_wire"] = raw["source_basis"][
                "vectors_wire"
            ][:-1]
            _task4_resign_tree("BasisManifest", raw["source_basis"])
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "bridge_grid_join":
            raw["source_readout_bridge_grid"]["reciprocal_indices"] = [[1]]
            _task4_resign_tree(
                "BridgeKGridManifest",
                raw["source_readout_bridge_grid"],
            )
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "bridge_authority_join":
            raw["actual_bridge_grid_authority_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        with pytest.raises((TypeError, ValueError)):
            core.validate_response_run_spec_fixture_v1(raw, provenance, graph)

    hostile_graph = _task4_clone(graph)
    assert type(hostile_graph) is dict
    hostile_components = hostile_graph["ordered_component_bodies"]
    assert type(hostile_components) is list
    hostile_transition = next(
        item
        for item in hostile_components
        if item["component_id"] == "actual_transition_outcome"
    )
    hostile_transition_body = hostile_transition["complete_body"]
    hostile_transition_body["materialization"]["current_application_authority"][
        "application_instance_id"
    ] = "hostile-lineage"
    _task4_resign_tree("TransitionAuthorityV3", hostile_transition_body)
    hostile_transition["body_raw_canonical_sha256"] = _task4_canonical_sha(
        hostile_transition_body
    )
    hostile_transition["body_self_hash_value"] = hostile_transition_body[
        "transition_authority_sha"
    ]
    hostile_transition = _task4_seal(hostile_transition, "component_sha")
    hostile_index = next(
        index
        for index, item in enumerate(hostile_components)
        if item["component_id"] == "actual_transition_outcome"
    )
    hostile_components[hostile_index] = hostile_transition
    hostile_graph["actual_transition_outcome_sha"] = hostile_transition[
        "body_self_hash_value"
    ]
    hostile_binding = hostile_graph["ordered_t_bearer_bindings"][hostile_index]
    hostile_binding["body_sha"] = hostile_transition["body_self_hash_value"]
    hostile_graph["ordered_t_bearer_bindings"][hostile_index] = _task4_seal(
        hostile_binding,
        "binding_sha",
    )
    hostile_graph["synthetic_graph_component_root_sha"] = _task4_canonical_sha(
        [
            {
                "component_id": item["component_id"],
                "body_self_hash_value": item["body_self_hash_value"],
            }
            for item in hostile_components
        ]
    )
    hostile_graph = _task4_seal(hostile_graph, "graph_sha")
    with pytest.raises((TypeError, ValueError)):
        core.validate_response_run_spec_fixture_v1(legal, provenance, hostile_graph)


def test_task4_source_response_validator_covers_branch_shape_and_lineage_attacks() -> None:
    core = _core_module()
    provenance = _task4_provenance_fixture()
    graph = _task4_graph_manifest(provenance)
    run_spec = _task4_response_run_spec(provenance, graph)
    for branch in ("actual", "matched_ablated"):
        legal = _task4_source_response(branch, run_spec, graph)
        assert (
            core.validate_source_readout_response_raw_v1(
                legal,
                run_spec,
                provenance,
                graph,
            )
            is legal
        )
        for attack in (
            "unknown",
            "field_order",
            "type",
            "self_hash",
            "nested_self_hash",
            "branch_bridge_join",
            "factory_join",
            "transition_join",
            "certificate_join",
            "run_spec_join",
            "basis_join",
            "calibration_join",
            "values_shape",
        ):
            raw = _task4_clone(legal)
            assert type(raw) is dict
            if attack == "unknown":
                raw["caller_unknown"] = False
            elif attack == "field_order":
                raw = {key: raw[key] for key in reversed(tuple(raw))}
            elif attack == "type":
                raw["branch"] = 1
            elif attack == "self_hash":
                raw["response_sha"] = "f" * 64
            elif attack == "nested_self_hash":
                raw["values"]["tensor_sha"] = "f" * 64
                raw = _task4_seal(raw, "response_sha")
            elif attack == "branch_bridge_join":
                raw["bridge_audit"]["branch"] = (
                    "matched_ablated" if branch == "actual" else "actual"
                )
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "factory_join":
                raw["factory_sha"] = "f" * 64
                raw["bridge_audit"]["factory_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "transition_join":
                raw["transition_sha"] = "f" * 64
                raw["bridge_audit"]["transition_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "certificate_join":
                raw["dynamics_certificate_sha"] = "f" * 64
                raw["bridge_audit"]["dynamics_certificate_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "run_spec_join":
                raw["run_spec_sha"] = "f" * 64
                raw["bridge_audit"]["run_spec_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "basis_join":
                raw["source_basis"]["role"] = "holdout_source"
                _task4_resign_tree("BasisManifest", raw["source_basis"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "calibration_join":
                raw["bridge_audit"]["readout_calibration_spec_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "values_shape":
                raw["values"] = _task4_tensor([2, 10, 10])
                raw = _task4_seal(raw, "response_sha")
            with pytest.raises((TypeError, ValueError)):
                core.validate_source_readout_response_raw_v1(
                    raw,
                    run_spec,
                    provenance,
                    graph,
                )


def test_task4_all_seven_legacy_endpoint_payloads_match_production_golden() -> None:
    fixture_path = (
        REPOSITORY_ROOT
        / "tests"
        / "fixtures"
        / "v3m0_b7_legacy_response_18b0d43.json"
    )
    if not fixture_path.is_file():
        pytest.skip("Task-2 legacy golden is integrated after this isolated Task-4 branch")
    core = _core_module()
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)
    assert [item["case_id"] for item in fixture["cases"]] == [
        "qualification_invalid",
        "input_binding_invalid",
        "actual_response_failed",
        "ablated_response_failed",
        "actual_bridge_failed",
        "ablated_bridge_failed",
        "success",
    ]
    for case in fixture["cases"]:
        shell = case["complete_input_wire"]["shell_outcome"]
        reference = shell["reference_outcome"]
        before_shell = core.canonical_json_bytes_v1(shell)
        before_reference = core.canonical_json_bytes_v1(reference)
        assert core.validate_endpoint_reference_outcome_raw_v1(reference) is reference
        assert core.validate_endpoint_shell_outcome_raw_v1(shell) is shell
        assert core.canonical_json_bytes_v1(reference) == before_reference
        assert core.canonical_json_bytes_v1(shell) == before_shell
        assert reference["outcome_sha"] == core.canonical_sha_v1(
            {
                key: value
                for key, value in reference.items()
                if key != "outcome_sha"
            }
        )
        assert shell["outcome_sha"] == core.canonical_sha_v1(
            {
                key: value
                for key, value in shell.items()
                if key != "outcome_sha"
            }
        )
