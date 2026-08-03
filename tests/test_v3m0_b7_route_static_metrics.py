"""Exact hand-computed tests for the frozen B7 route static metrics."""

from __future__ import annotations

import builtins
import importlib
import inspect

import pytest


ROUTE_COMMIT = "a" * 40
ROUTE_PATH = "experiments/v3m0_b7_schema_lab/a_flat.py"

HAND_COMPUTED_ROUTE = b"""import dataclasses as dc
import enum as en

ROUTE_ID = "A_FLAT"
WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"
_FLAG: bool = True
_ALIAS = _branch

def encode_normalized_transcript(canonical_transcript_utf8):
    assert canonical_transcript_utf8
    return _ALIAS(canonical_transcript_utf8) if _FLAG and canonical_transcript_utf8 else canonical_transcript_utf8

def verify_and_decode_route_wire(canonical_route_wire_utf8):
    try:
        if canonical_route_wire_utf8:
            return _Record(canonical_route_wire_utf8, "").payload
    except ValueError:
        return _Kind.OK.value
    return canonical_route_wire_utf8

def _branch(value):
    return [item for item in (value,) if item][0]

@dc.dataclass(frozen=True)
class _Record:
    payload: bytes
    payload_sha256: str

class _Kind(en.Enum):
    OK = b""
"""


def _common_module():
    return importlib.import_module("experiments.v3m0_b7_schema_lab.common")


def _route_blob(source: bytes = HAND_COMPUTED_ROUTE):
    return (ROUTE_COMMIT, ROUTE_PATH, "100644", source)


def test_route_static_metrics_expose_blob_only_public_api() -> None:
    common = _common_module()

    assert tuple(
        inspect.signature(common.compute_route_static_metrics_v1).parameters
    ) == ("route_id", "route_blob")


def test_route_static_metrics_match_hand_computed_five_coordinate_vector() -> None:
    common = _common_module()

    assert common.compute_route_static_metrics_v1("A_FLAT", _route_blob()) == {
        "b8_consumer_assertion_count": 8,
        "b8_consumer_changed_loc": 0,
        "verifier_branch_count": 6,
        "route_record_count": 2,
        "route_hash_layer_count": 1,
    }


def test_reachable_closure_uses_frozen_breadth_first_utf8_name_order() -> None:
    common = _common_module()
    tree = common._parse_python_blob_v1(HAND_COMPUTED_ROUTE, ROUTE_PATH)

    _aliases, _bindings, ordered = common._route_local_reachable_closure_v1(
        tree,
        "experiments.v3m0_b7_schema_lab.a_flat",
    )

    assert [name for name, _node in ordered] == [
        "encode_normalized_transcript",
        "verify_and_decode_route_wire",
        "_ALIAS",
        "_FLAG",
        "_Kind",
        "_Record",
        "_branch",
    ]


def test_annassign_annotation_and_entire_class_body_enter_the_closure() -> None:
    common = _common_module()
    source = HAND_COMPUTED_ROUTE.replace(b"_FLAG: bool", b"_FLAG: _FlagType") + (
        b"\n"
        b"class _FlagType:\n"
        b"    def choose(self, value):\n"
        b"        if value:\n"
        b"            return value\n"
        b"        return b''\n"
    )

    metrics = common.compute_route_static_metrics_v1(
        "A_FLAT",
        _route_blob(source),
    )

    assert metrics["verifier_branch_count"] == 7


@pytest.mark.parametrize("route_id", ("A_FLAT", "B_PROGRESS", "C_UNION"))
def test_b8_metrics_use_the_frozen_renderer_and_normalize_route_literals(
    route_id: str,
) -> None:
    common = _common_module()
    entry = common._route_static_registry_entry_v1(route_id)
    source = HAND_COMPUTED_ROUTE.replace(
        b'ROUTE_ID = "A_FLAT"', b'ROUTE_ID = "' + route_id.encode("utf-8") + b'"'
    ).replace(b"experimental.v3m0.b7.a-flat.wire.v1", entry[4].encode("utf-8"))
    route_blob = (ROUTE_COMMIT, entry[3], "100644", source)

    metrics = common.compute_route_static_metrics_v1(route_id, route_blob)

    assert metrics["b8_consumer_assertion_count"] == 8
    assert metrics["b8_consumer_changed_loc"] == 0


BRANCH_ROUTE = (
    b'ROUTE_ID = "A_FLAT"\n'
    b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"\n'
    b"\n"
    b"def encode_normalized_transcript(canonical_transcript_utf8):\n"
    b"    assert canonical_transcript_utf8\n"
    b"    if canonical_transcript_utf8:\n"
    b"        canonical_transcript_utf8 = canonical_transcript_utf8 "
    b"if canonical_transcript_utf8 and canonical_transcript_utf8 "
    b"and canonical_transcript_utf8 else b''\n"
    b"    try:\n"
    b"        return [item for item in (canonical_transcript_utf8,) "
    b"if item if canonical_transcript_utf8][0]\n"
    b"    except ValueError:\n"
    b"        return canonical_transcript_utf8\n"
    b"\n"
    b"def verify_and_decode_route_wire(canonical_route_wire_utf8):\n"
    b"    return _identity(canonical_route_wire_utf8)\n"
    b"\n"
    b"def _identity(value):\n"
    b"    return value\n"
)


def test_branch_metric_counts_each_frozen_python39_contribution_once() -> None:
    common = _common_module()

    metrics = common.compute_route_static_metrics_v1(
        "A_FLAT",
        _route_blob(BRANCH_ROUTE),
    )

    assert metrics["verifier_branch_count"] == 8


def test_reachable_closure_ignores_unreachable_branches_and_forbidden_calls() -> None:
    common = _common_module()
    source = BRANCH_ROUTE + (
        b"\n"
        b"def _unreachable(value):\n"
        b"    if value:\n"
        b"        return eval(value)\n"
        b"    return value\n"
    )

    metrics = common.compute_route_static_metrics_v1(
        "A_FLAT",
        _route_blob(source),
    )

    assert metrics["verifier_branch_count"] == 8


@pytest.mark.parametrize(
    "forbidden_call",
    ("eval", "exec", "compile", "__import__", "globals", "locals", "getattr"),
)
def test_reachable_closure_rejects_each_frozen_forbidden_call(
    forbidden_call: str,
) -> None:
    common = _common_module()
    source = BRANCH_ROUTE.replace(
        b"return _identity(canonical_route_wire_utf8)",
        f"return {forbidden_call}(canonical_route_wire_utf8)".encode("utf-8"),
    )

    with pytest.raises(ValueError, match="forbidden"):
        common.compute_route_static_metrics_v1("A_FLAT", _route_blob(source))


def test_reachable_closure_resolves_assignment_alias_before_forbidden_test() -> None:
    common = _common_module()
    source = BRANCH_ROUTE.replace(
        b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"',
        b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"\n_BAD = eval',
    ).replace(
        b"return _identity(canonical_route_wire_utf8)",
        b"return _BAD(canonical_route_wire_utf8)",
    )

    with pytest.raises(ValueError, match="forbidden"):
        common.compute_route_static_metrics_v1("A_FLAT", _route_blob(source))


def test_reachable_closure_resolves_class_attribute_callable_aliases() -> None:
    common = _common_module()
    source = BRANCH_ROUTE.replace(
        b"return _identity(canonical_route_wire_utf8)",
        b"return _CallableStore.danger(canonical_route_wire_utf8)",
    ) + (b"\nclass _CallableStore:\n    danger = eval\n")

    with pytest.raises(ValueError, match="forbidden"):
        common.compute_route_static_metrics_v1("A_FLAT", _route_blob(source))


@pytest.mark.parametrize(
    "dynamic_source",
    (
        BRANCH_ROUTE.replace(
            b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"',
            b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"\n'
            b"_TARGET = eval if True else len",
        ).replace(
            b"return _identity(canonical_route_wire_utf8)",
            b"return _TARGET(canonical_route_wire_utf8)",
        ),
        BRANCH_ROUTE.replace(
            b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"',
            b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"\n'
            b"_LEFT, _RIGHT = (1, 2)",
        ),
        BRANCH_ROUTE + b"\nif True:\n    _DYNAMIC = 1\n",
    ),
)
def test_reachable_closure_rejects_dynamic_binding_resolution(
    dynamic_source: bytes,
) -> None:
    common = _common_module()

    with pytest.raises(ValueError, match="dynamic"):
        common.compute_route_static_metrics_v1(
            "A_FLAT",
            _route_blob(dynamic_source),
        )


@pytest.mark.parametrize(
    "duplicate_source",
    (
        BRANCH_ROUTE + b"\ndef _identity(value):\n    return bytes(value)\n",
        b"import json as _identity\n" + BRANCH_ROUTE,
        b"import json as helper, enum as helper\n" + BRANCH_ROUTE,
    ),
)
def test_reachable_closure_rejects_duplicate_bindings(
    duplicate_source: bytes,
) -> None:
    common = _common_module()

    with pytest.raises(ValueError, match="duplicate"):
        common.compute_route_static_metrics_v1(
            "A_FLAT",
            _route_blob(duplicate_source),
        )


RECORD_ROUTE = (
    b"from dataclasses import dataclass as record\n"
    b"from enum import Enum as Enumeration\n"
    b"from enum import IntEnum as IntegerEnumeration\n"
    b"from enum import StrEnum as TextEnumeration\n"
    b"\n"
    b'ROUTE_ID = "A_FLAT"\n'
    b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"\n'
    b"\n"
    b"def encode_normalized_transcript(canonical_transcript_utf8):\n"
    b"    return (_Data, _IntKind, _Plain, canonical_transcript_utf8)\n"
    b"\n"
    b"def verify_and_decode_route_wire(canonical_route_wire_utf8):\n"
    b"    return (_Kind, _TextKind, canonical_route_wire_utf8)\n"
    b"\n"
    b"@record(frozen=True)\n"
    b"class _Data:\n"
    b"    payload: bytes\n"
    b"    payload_sha: str\n"
    b"\n"
    b"class _Kind(Enumeration):\n"
    b"    OK = 1\n"
    b"\n"
    b"class _IntKind(IntegerEnumeration):\n"
    b"    OK = 1\n"
    b'    code_sha256 = ""\n'
    b"\n"
    b"class _TextKind(TextEnumeration):\n"
    b'    OK = "ok"\n'
    b"    def label(self):\n"
    b'        method_sha = "not-a-direct-field"\n'
    b"        return method_sha\n"
    b"\n"
    b"class _Plain:\n"
    b'    ignored_sha = "not-a-record"\n'
)


def test_record_and_hash_metrics_resolve_import_aliases_and_direct_fields() -> None:
    common = _common_module()

    metrics = common.compute_route_static_metrics_v1(
        "A_FLAT",
        _route_blob(RECORD_ROUTE),
    )

    assert metrics["route_record_count"] == 4
    assert metrics["route_hash_layer_count"] == 2


def test_hash_metric_excludes_method_inherited_and_outer_nested_fields() -> None:
    common = _common_module()
    source = (
        b"from dataclasses import dataclass as record\n"
        b"\n"
        b'ROUTE_ID = "A_FLAT"\n'
        b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"\n'
        b"\n"
        b"def encode_normalized_transcript(canonical_transcript_utf8):\n"
        b"    return (_Outer, _Child, canonical_transcript_utf8)\n"
        b"\n"
        b"def verify_and_decode_route_wire(canonical_route_wire_utf8):\n"
        b"    return canonical_route_wire_utf8\n"
        b"\n"
        b"@record(frozen=True)\n"
        b"class _Outer:\n"
        b"    @record(frozen=True)\n"
        b"    class Nested:\n"
        b"        nested_sha256: str\n"
        b"    def method(self):\n"
        b'        method_sha = "not-direct"\n'
        b"        return method_sha\n"
        b"\n"
        b"class _Child(_Outer):\n"
        b"    pass\n"
    )

    metrics = common.compute_route_static_metrics_v1(
        "A_FLAT",
        _route_blob(source),
    )

    assert metrics["route_record_count"] == 2
    assert metrics["route_hash_layer_count"] == 1


def test_hash_metric_rejects_multiple_assign_targets_as_a_direct_field() -> None:
    common = _common_module()
    source = HAND_COMPUTED_ROUTE.replace(
        b"    payload_sha256: str",
        b'    left_sha = right_sha256 = ""',
    )

    metrics = common.compute_route_static_metrics_v1(
        "A_FLAT",
        _route_blob(source),
    )

    assert metrics["route_record_count"] == 2
    assert metrics["route_hash_layer_count"] == 0


@pytest.mark.parametrize(
    "dynamic_record_source",
    (
        (
            b"from dataclasses import dataclass as record\n"
            + BRANCH_ROUTE.replace(
                b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"',
                b'WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"\n'
                b"_DECORATOR = record if True else object",
            ).replace(
                b"return _identity(canonical_route_wire_utf8)",
                b"return _Dynamic(canonical_route_wire_utf8)",
            )
            + b"\n@_DECORATOR\nclass _Dynamic:\n    value: bytes\n"
        ),
        BRANCH_ROUTE.replace(
            b"return _identity(canonical_route_wire_utf8)",
            b"return _Dynamic(canonical_route_wire_utf8)",
        )
        + b"\nclass _Dynamic(unknown.Base):\n    pass\n",
        BRANCH_ROUTE.replace(
            b"return _identity(canonical_route_wire_utf8)",
            b"return _Dynamic(canonical_route_wire_utf8)",
        )
        + b"\ndef _factory():\n    return object\n"
        + b"class _Dynamic(_factory()):\n    pass\n",
    ),
)
def test_record_metric_rejects_dynamic_decorator_and_base_resolution(
    dynamic_record_source: bytes,
) -> None:
    common = _common_module()

    with pytest.raises(ValueError, match="dynamic"):
        common.compute_route_static_metrics_v1(
            "A_FLAT",
            _route_blob(dynamic_record_source),
        )


def test_static_metrics_never_read_the_worktree_or_import_the_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    common = _common_module()
    original_import = builtins.__import__

    def forbidden_open(*_args, **_kwargs):
        raise AssertionError("route metric attempted ambient file I/O")

    def route_import_guard(name, *args, **kwargs):
        if name == "experiments.v3m0_b7_schema_lab.a_flat":
            raise AssertionError("route metric attempted to import the route")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", forbidden_open)
    monkeypatch.setattr(builtins, "__import__", route_import_guard)

    assert (
        common.compute_route_static_metrics_v1(
            "A_FLAT",
            _route_blob(),
        )["route_record_count"]
        == 2
    )


@pytest.mark.parametrize(
    "route_blob",
    (
        [ROUTE_COMMIT, ROUTE_PATH, "100644", HAND_COMPUTED_ROUTE],
        (
            ROUTE_COMMIT,
            "experiments/v3m0_b7_schema_lab/other.py",
            "100644",
            HAND_COMPUTED_ROUTE,
        ),
        (ROUTE_COMMIT, ROUTE_PATH, "100755", HAND_COMPUTED_ROUTE),
    ),
)
def test_static_metrics_reject_nonimmutable_or_wrong_route_blob(route_blob) -> None:
    common = _common_module()

    with pytest.raises((TypeError, ValueError)):
        common.compute_route_static_metrics_v1("A_FLAT", route_blob)
