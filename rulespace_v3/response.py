"""Task 11 endpoint-shell and atomic paired-response evidence.

This module owns the response-specific raw wires and opaque outcome
authorities.  A raw dataclass is never a runtime authority: run specifications
are replayed against the live pre-shell window protocol, endpoint outcomes are
recomputed from live transitions and dynamics certificates, and paired
response issuance atomically consumes the live certificate-backed
qualification and recursively binds both branches.
"""

from __future__ import annotations

import functools
import inspect
import math
import re
import threading
import types
import weakref
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import Callable, Literal, Optional

import numpy as np

from . import b7_replay_core_v1 as _b7_replay_core_v1
from .certificate import (
    DynamicsCertificate,
    VerifiedDynamicsCertificate,
    _reverify_verified_dynamics_certificate,
    dynamics_certificate_payload,
    verify_dynamics_certificate,
)
from .contracts import BlockStatus, UndefinedReason
from .dynamics import (
    MeasuredTransition,
    VerifiedTransition,
    _reverify_verified_transition,
    measured_transition_payload,
    transition_symbol,
    verify_measured_transition,
)
from .evidence import canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    VerifiedFactory,
    _reverify_verified_factory,
    apply_factory_step,
    basis_manifest_array,
    basis_manifest_payload,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_basis_manifest,
    verify_frozen_tensor,
)
from .fp64 import frobenius_sqrt_upper
from .grids import (
    BridgeKGridManifest,
    DirectionManifest,
    ResponseKGridManifest,
    bridge_grid_payload,
    response_grid_payload,
)
from .metric import StabilityMetricWitness
from .parent_freeze import DirectionPathClosure
from .prestructure import issue_synthetic_prestructure_authority
from .qualification import (
    VerifiedCertificateBackedQualification,
    _reverify_verified_certificate_backed_qualification,
)
from .registry import (
    CONTROL_ORDER,
    ControlReadoutCalibrationSpec,
    ControlRegistryEntry,
    VerifiedControlRegistry,
    _reverify_verified_control_registry,
    control_registry_entry_payload,
)
from .replay_scope import (
    _cached_replay_is_valid,
    _record_successful_replay,
)
from .thresholds import (
    phase_grid_step,
    phase_separation_min as phase_separation_min,
    preflight_fejer_work,
    preflight_shell_projector_entries,
    preflight_source_bridge_work,
)
from .window import (
    ControlWindowProtocolEntry,
    VerifiedWindowCalibrationProtocol,
    WindowCalibrationProtocol,
    _reverify_verified_window_calibration_protocol,
    window_calibration_protocol_payload,
)


def _require_b7_replay_core_v1(
    candidate,
    core_binding=_b7_replay_core_v1,
):
    if candidate is not core_binding:
        raise RuntimeError("B7 replay core module binding changed")
    return core_binding


RESPONSE_RUN_SPEC_SCHEMA_VERSION = "v3m0.response-run-spec.v1"
ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION = "v3m0.endpoint-reference-spec.v1"
ENDPOINT_REFERENCE_SCHEMA_VERSION = "v3m0.endpoint-reference-projector.v1"
ENDPOINT_REFERENCE_ATTEMPT_SCHEMA_VERSION = "v3m0.endpoint-reference-attempt.v1"
ENDPOINT_REFERENCE_OUTCOME_SCHEMA_VERSION = "v3m0.endpoint-reference-outcome.v1"
ENDPOINT_SHELL_SPEC_SCHEMA_VERSION = "v3m0.endpoint-shell-spec.v1"
ENDPOINT_SHELL_SCHEMA_VERSION = "v3m0.endpoint-shell-manifest.v1"
ENDPOINT_SHELL_ATTEMPT_SCHEMA_VERSION = "v3m0.endpoint-shell-attempt.v1"
ENDPOINT_SHELL_OUTCOME_SCHEMA_VERSION = "v3m0.endpoint-shell-outcome.v1"
SOURCE_FRAME_COVERAGE_SCHEMA_VERSION = "v3m0.source-frame-coverage.v1"
SOURCE_READOUT_BRIDGE_SCHEMA_VERSION = "v3m0.source-readout-bridge.v1"
SOURCE_READOUT_RESPONSE_SCHEMA_VERSION = "v3m0.source-readout-response.v1"
PAIRED_RESPONSE_SCHEMA_VERSION = "v3m0.paired-filtered-response.v1"
PAIRED_RESPONSE_ATTEMPT_SCHEMA_VERSION = "v3m0.paired-response-attempt.v1"
PAIRED_RESPONSE_OUTCOME_SCHEMA_VERSION = "v3m0.paired-response-outcome.v1"

PROJECTOR_COORDINATE_CONVENTION_ID = "g-whitened-state-v1"
SHELL_EXTRACTION_PROTOCOL_ID = "endpoint-single-node-reference-v1"
EIGENPHASE_CONVENTION_ID = "lambda-exp-plus-i-theta-principal-v1"
_EXPECTED_RANK_SOURCE_ID = "parent-freeze-control-application-spec-v1"
_ZERO_SHA = "0" * 64
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()

# Private immutable copies keep the scientific gates independent of public
# module-global monkeypatches.
_CLOSED_FEJER_ORDERS = (256, 512, 1024, 2048, 4096, 8192, 16384)
_BRIDGE_TOLERANCE = 1.0e-12
_PROJECTOR_GATE = 1.0e-12
_PARTICIPATION_GATE = 0.25
_OVERLAP_MARGIN_GATE = 0.2
_LOOP_GATE = 1.0e-10
_SOURCE_BRIDGE_WORK_CAP = 32_768
_GENERAL_BODY_CAP = 268_435_456
_SOURCE_FRAME_ENTRY_CAP = 16_777_216
_SOURCE_FRAME_WORK_CAP = 16_777_216
_RESPONSE_EVIDENCE_TEXT_CAP = 16_384
_RESPONSE_EVIDENCE_DEPTH_CAP = 128


def _exact_record(value: object, record_type: type, field: str) -> object:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(record_type.__dataclass_fields__)
    observed = frozenset(vars(value))
    if observed != expected:
        raise ValueError(f"{field} contains missing or unknown fields")
    return value


def _raw_dataclass_fields(
    record_type: type,
    _type_getattribute: Callable = type.__getattribute__,
) -> object:
    """Read dataclass metadata from class storage without descriptor dispatch."""

    for owner in _type_getattribute(record_type, "__mro__"):
        mapping = _type_getattribute(owner, "__dict__")
        if "__dataclass_fields__" in mapping:
            return mapping["__dataclass_fields__"]
    return None


def _exact_dataclass_storage_items(
    value: object,
    field: str,
    fields: dict[str, object],
    _field_reader: Callable[[type], object] = _raw_dataclass_fields,
    _type_fn: Callable = type,
    _type_getattribute: Callable = type.__getattribute__,
    _tuple_type: type = tuple,
    _list_type: type = list,
    _str_type: type = str,
    _dict_type: type = dict,
    _frozenset_type: Callable = frozenset,
    _any_fn: Callable = any,
    _dict_getitem: Callable = dict.__getitem__,
    _member_descriptor_type: type = types.MemberDescriptorType,
    _getset_descriptor_type: type = types.GetSetDescriptorType,
    _member_get: Callable = types.MemberDescriptorType.__get__,
    _getset_get: Callable = types.GetSetDescriptorType.__get__,
) -> tuple[tuple[str, object], ...]:
    """Read exact instance storage without dispatching user descriptors."""

    if (
        fields is not _field_reader(_type_fn(value))
        or _type_fn(fields) is not _dict_type
    ):
        raise TypeError(f"{field} dataclass fields must be an exact dict")
    expected_names = _tuple_type(fields)
    if _any_fn(_type_fn(name) is not _str_type for name in expected_names):
        raise TypeError(f"{field} dataclass field names must be strings")
    expected = _frozenset_type(expected_names)
    item_type = _type_fn(value)
    mro = _tuple_type(_type_getattribute(item_type, "__mro__"))
    owner_mappings = _tuple_type(
        (owner, _type_getattribute(owner, "__dict__")) for owner in mro
    )
    declared_slots: set[str] = set()
    slot_descriptors: dict[str, tuple[object, type]] = {}
    dict_storage: Optional[tuple[object, type]] = None
    for owner, mapping in owner_mappings:
        slots = mapping.get("__slots__", ())
        if _type_fn(slots) is _str_type:
            normalized_slots = (slots,)
        elif _type_fn(slots) in (_tuple_type, _list_type):
            normalized_slots = _tuple_type(slots)
        else:
            raise TypeError(f"{field} contains invalid slot declarations")
        for name in normalized_slots:
            if _type_fn(name) is not _str_type:
                raise TypeError(f"{field} contains a non-string slot declaration")
            declared_slots.add(name)
            if name in ("__dict__", "__weakref__"):
                continue
            descriptor = mapping.get(name)
            if _type_fn(descriptor) is not _member_descriptor_type:
                raise ValueError(f"{field} slot descriptor was replaced")
            if name in slot_descriptors:
                raise ValueError(f"{field} contains duplicate slot storage")
            slot_descriptors[name] = (descriptor, owner)
        candidate = mapping.get("__dict__")
        if _type_fn(candidate) is _getset_descriptor_type:
            if dict_storage is not None:
                raise ValueError(f"{field} contains duplicate dict storage")
            dict_storage = (candidate, owner)
        elif "__dict__" in mapping:
            raise ValueError(f"{field} dict descriptor was replaced")
    if declared_slots.difference(
        expected,
        {"__dict__", "__weakref__"},
    ):
        raise ValueError(f"{field} contains missing or unknown fields")
    if dict_storage is not None:
        if slot_descriptors:
            raise ValueError(f"{field} contains ambiguous field storage")
        descriptor, owner = dict_storage
        try:
            body = _getset_get(descriptor, value, owner)
        except AttributeError as exc:
            raise ValueError(f"{field} has no exact record body") from exc
        if _type_fn(body) is not _dict_type:
            raise TypeError(f"{field} has no exact record body")
        if _frozenset_type(body) != expected:
            raise ValueError(f"{field} contains missing or unknown fields")
        return _tuple_type((name, _dict_getitem(body, name)) for name in expected_names)
    if _frozenset_type(slot_descriptors) != expected:
        raise ValueError(f"{field} contains missing or unknown fields")
    result = []
    for name in expected_names:
        descriptor, owner = slot_descriptors[name]
        for binding_owner, mapping in owner_mappings:
            if name in mapping and mapping[name] is not descriptor:
                raise ValueError(
                    f"{field} slot storage is shadowed on {binding_owner.__name__}"
                )
        try:
            nested = _member_get(descriptor, value, owner)
        except AttributeError as exc:
            raise ValueError(f"{field} contains a missing field: {name}") from exc
        result.append((name, nested))
    return _tuple_type(result)


def _dataclass_has_unsafe_field_binding(
    value: object,
    field_names: tuple[object, ...],
    _type_fn: Callable = type,
    _type_getattribute: Callable = type.__getattribute__,
    _member_descriptor_type: type = types.MemberDescriptorType,
) -> bool:
    """Detect user descriptors without invoking their protocol."""

    item_type = _type_fn(value)
    for owner in _type_getattribute(item_type, "__mro__"):
        mapping = _type_getattribute(owner, "__dict__")
        for name in field_names:
            if name not in mapping:
                continue
            binding = mapping[name]
            if _type_fn(binding) is _member_descriptor_type:
                continue
            binding_type = _type_fn(binding)
            for binding_owner in _type_getattribute(binding_type, "__mro__"):
                binding_mapping = _type_getattribute(binding_owner, "__dict__")
                if "__set__" in binding_mapping or "__delete__" in binding_mapping:
                    return True
    return False


def _exact_dataclass_items(
    value: object,
    field: str,
    fields: dict[str, object],
    _storage_reader: Callable = _exact_dataclass_storage_items,
) -> tuple[tuple[str, object], ...]:
    """Read the exact trusted storage of a plain or slotted dataclass."""

    return _storage_reader(value, field, fields)


def _exact_dataclass_tree_impl(
    value: object,
    field: str,
    _storage_reader: Callable = _exact_dataclass_storage_items,
    _unsafe_binding_checker: Callable = _dataclass_has_unsafe_field_binding,
    _field_reader: Callable[[type], object] = _raw_dataclass_fields,
    _type_fn: Callable = type,
    _id_fn: Callable = id,
    _tuple_type: type = tuple,
    _list_type: type = list,
    _dict_type: type = dict,
    _str_type: type = str,
    _len_fn: Callable = len,
    _any_fn: Callable = any,
    _zip_fn: Callable = zip,
    _enumerate_fn: Callable = enumerate,
    _reversed_fn: Callable = reversed,
) -> None:
    """Reject unknown fields at every recursively embedded dataclass.

    Upstream payload helpers intentionally own their wire spelling, but some
    of them predate the V3-M0 exact-wire rule and ignore attributes injected
    with ``object.__setattr__``.  This response-local walk closes that gap
    before any hash is evaluated.
    """

    stack: list[tuple[bool, object, str]] = [(False, value, field)]
    # Strong references make identity memoization safe from object-id reuse.
    gray: dict[int, object] = {}
    black: dict[int, object] = {}
    subtree_logical_nodes: dict[int, int] = {}
    traversal_starts: dict[int, int] = {}
    shallow_snapshots: dict[
        int,
        tuple[str, tuple[object, ...], tuple[object, ...]],
    ] = {}
    storage_reader = _storage_reader
    unsafe_binding_checker = _unsafe_binding_checker
    field_reader = _field_reader

    def raw_dataclass_storage(
        item: object,
        path: str,
        expected_names: tuple[object, ...],
    ) -> tuple[object, ...]:
        item_type = _type_fn(item)
        fields = field_reader(item_type)
        if fields is None or _tuple_type(fields) != expected_names:
            raise ValueError(f"{path} dataclass schema changed after validation")
        items = storage_reader(item, path, fields, field_reader)
        if _tuple_type(name for name, _ in items) != expected_names:
            raise ValueError(f"{path} dataclass schema changed after validation")
        return _tuple_type(nested for _, nested in items)

    def guard_shallow(item: object, path: str) -> None:
        identity = _id_fn(item)
        try:
            kind, names, expected_values = shallow_snapshots[identity]
        except KeyError as exc:
            raise RuntimeError("recursive traversal snapshot invariant failed") from exc
        if kind == "dataclass":
            current_values = raw_dataclass_storage(item, path, names)
        elif kind in ("tuple", "list"):
            current_values = _tuple_type(item)
        elif kind == "dict":
            try:
                current_items = _tuple_type(item.items())
            except RuntimeError as exc:
                raise ValueError(f"{path} changed after validation") from exc
            current_names = _tuple_type(key for key, _ in current_items)
            if _any_fn(_type_fn(key) is not _str_type for key in current_names):
                raise TypeError(f"{path} mapping keys must be strings")
            if current_names != names:
                raise ValueError(f"{path} changed after validation")
            current_values = _tuple_type(nested for _, nested in current_items)
        else:
            raise RuntimeError("recursive traversal snapshot kind invariant failed")
        if _len_fn(current_values) != _len_fn(expected_values) or _any_fn(
            current is not expected
            for current, expected in _zip_fn(current_values, expected_values)
        ):
            raise ValueError(f"{path} changed after validation")
        if kind == "dataclass" and unsafe_binding_checker(item, names):
            raise ValueError(
                f"{path} contains missing or unknown fields; "
                "storage changed after validation"
            )

    visited = 0

    def charge_nodes(amount: int) -> None:
        nonlocal visited
        visited += amount
        if visited > 20_000_000:
            raise ValueError(f"{field} recursive body exceeds node cap")

    while stack:
        leaving, item, path = stack.pop()
        identity = _id_fn(item)
        if leaving:
            if identity not in gray or gray[identity] is not item:
                raise RuntimeError("recursive traversal identity invariant failed")
            guard_shallow(item, path)
            try:
                traversal_start = traversal_starts.pop(identity)
            except KeyError as exc:
                raise RuntimeError(
                    "recursive traversal charge invariant failed"
                ) from exc
            subtree_logical_nodes[identity] = visited - traversal_start
            del gray[identity]
            black[identity] = item
            continue
        charge_nodes(1)
        item_type = _type_fn(item)
        fields = field_reader(item_type)
        if identity in black:
            if black[identity] is not item:
                raise RuntimeError("recursive traversal identity invariant failed")
            guard_shallow(item, path)
            try:
                logical_nodes = subtree_logical_nodes[identity]
            except KeyError as exc:
                raise RuntimeError(
                    "recursive traversal charge invariant failed"
                ) from exc
            charge_nodes(logical_nodes - 1)
            continue
        if identity in gray:
            if gray[identity] is not item:
                raise RuntimeError("recursive traversal identity invariant failed")
            snapshot_kind = shallow_snapshots[identity][0]
            kind = "dataclass" if snapshot_kind == "dataclass" else "container"
            raise ValueError(f"{path} contains a cyclic {kind}")
        if fields is None and item_type not in (
            _tuple_type,
            _list_type,
            _dict_type,
        ):
            continue
        gray[identity] = item
        traversal_starts[identity] = visited - 1
        stack.append((True, item, path))
        if fields is not None:
            items = storage_reader(item, path, fields, field_reader)
            names = _tuple_type(fields)
            shallow_snapshots[identity] = (
                "dataclass",
                names,
                _tuple_type(nested for _, nested in items),
            )
            for name, nested in _reversed_fn(items):
                stack.append((False, nested, f"{path}.{name}"))
            continue
        if item_type is _tuple_type:
            if _len_fn(item) > 16_777_216:
                raise ValueError(f"{path} tuple exceeds recursive entry cap")
            entries = _tuple_type(_enumerate_fn(item))
            shallow_snapshots[identity] = (
                "tuple",
                (),
                _tuple_type(nested for _, nested in entries),
            )
            stack.extend(
                (False, nested, f"{path}[{index}]")
                for index, nested in _reversed_fn(entries)
            )
        elif item_type is _list_type:
            if _len_fn(item) > 16_777_216:
                raise ValueError(f"{path} list exceeds recursive entry cap")
            entries = _tuple_type(_enumerate_fn(item))
            shallow_snapshots[identity] = (
                "list",
                (),
                _tuple_type(nested for _, nested in entries),
            )
            stack.extend(
                (False, nested, f"{path}[{index}]")
                for index, nested in _reversed_fn(entries)
            )
        elif item_type is _dict_type:
            if _len_fn(item) > 262_144:
                raise ValueError(f"{path} mapping exceeds recursive entry cap")
            entries = _tuple_type(item.items())
            for key, _ in entries:
                if _type_fn(key) is not _str_type:
                    raise TypeError(f"{path} mapping keys must be strings")
            shallow_snapshots[identity] = (
                "dict",
                _tuple_type(key for key, _ in entries),
                _tuple_type(nested for _, nested in entries),
            )
            for key, nested in entries:
                stack.append((False, nested, f"{path}.{key}"))

    for item in _tuple_type(black.values()):
        guard_shallow(item, field)


def _make_exact_dataclass_tree(
    implementation: Callable,
    storage_reader: Callable,
    unsafe_binding_checker: Callable,
    field_reader: Callable[[type], object],
) -> Callable[[object, str], None]:
    """Freeze the exact-tree helper graph off later module rebinding."""

    def exact_dataclass_tree(value: object, field: str) -> None:
        implementation(
            value,
            field,
            storage_reader,
            unsafe_binding_checker,
            field_reader,
        )

    return exact_dataclass_tree


_exact_dataclass_tree = _make_exact_dataclass_tree(
    _exact_dataclass_tree_impl,
    _exact_dataclass_storage_items,
    _dataclass_has_unsafe_field_binding,
    _raw_dataclass_fields,
)


def _exact_response_grid_tree(
    value: ResponseKGridManifest,
    field: str = "response_grid",
) -> None:
    _exact_record(value, ResponseKGridManifest, field)
    direction = value.direction_manifest
    _exact_record(
        direction,
        DirectionManifest,
        f"{field}.direction_manifest",
    )
    if len(value.reciprocal_indices) > 262_144:
        raise ValueError(f"{field} exceeds point cap")
    for name in (
        "direction_ids",
        "primitive_directions",
        "path_ids",
        "ordered_paths",
        "closure_path_pairs",
    ):
        body = getattr(direction, name)
        if type(body) is not tuple:
            raise TypeError(f"{field}.direction_manifest.{name} must be a tuple")
        if len(body) > 262_144:
            raise ValueError(f"{field}.direction_manifest.{name} exceeds point cap")
    path_points = 0
    for path in direction.ordered_paths:
        if type(path) is not tuple:
            raise TypeError(f"{field} direction paths must be tuples")
        path_points += len(path)
        if path_points > 262_144:
            raise ValueError(f"{field} direction path points exceed cap")
    for index, closure in enumerate(direction.closure_path_pairs):
        _exact_record(
            closure,
            DirectionPathClosure,
            f"{field}.direction_manifest.closure_path_pairs[{index}]",
        )
    _exact_dataclass_tree(value, field)


def _exact_bridge_grid_tree(
    value: BridgeKGridManifest,
    field: str = "bridge_grid",
) -> None:
    _exact_record(value, BridgeKGridManifest, field)
    if len(value.reciprocal_indices) > 64:
        raise ValueError(f"{field} exceeds bridge point cap")
    _exact_dataclass_tree(value, field)


def _exact_registry_entry_tree(
    value: ControlRegistryEntry,
    field: str = "control_registry_entry",
) -> None:
    _exact_record(value, ControlRegistryEntry, field)
    _exact_record(value.source_basis, BasisManifest, f"{field}.source_basis")
    _exact_record(value.readout_basis, BasisManifest, f"{field}.readout_basis")
    for name, basis in (
        ("source_basis", value.source_basis),
        ("readout_basis", value.readout_basis),
    ):
        entries = len(basis.vectors_wire) * len(basis.channel_order)
        if entries > 16_777_216 or entries * 16 > _GENERAL_BODY_CAP:
            raise ValueError(f"{field}.{name} exceeds evidence body cap")
    spec = value.readout_calibration_spec
    _exact_record(
        spec,
        ControlReadoutCalibrationSpec,
        f"{field}.readout_calibration_spec",
    )
    for name in (
        "source_metric_whitener",
        "h_metric_whitener",
        "curvature_incidence_operator",
        "curvature_metric_whitener",
    ):
        tensor = getattr(spec, name)
        _exact_record(
            tensor,
            FrozenComplexTensor,
            f"{field}.readout_calibration_spec.{name}",
        )
        entries = math.prod(tensor.shape)
        if entries > 16_777_216 or entries * 16 > _GENERAL_BODY_CAP:
            raise ValueError(
                f"{field}.readout_calibration_spec.{name} exceeds body cap"
            )
        if len(tensor.values_wire) != entries:
            raise ValueError(
                f"{field}.readout_calibration_spec.{name} wire length mismatch"
            )
    _exact_dataclass_tree(value, field)


def _preflight_response_evidence_body(
    value: object,
    field: str,
    *,
    body_cap: int = _GENERAL_BODY_CAP,
    text_cap: int = _RESPONSE_EVIDENCE_TEXT_CAP,
    depth_cap: int = _RESPONSE_EVIDENCE_DEPTH_CAP,
) -> None:
    """Stream an exact finite body cap without hashing or payload allocation."""

    used = 0
    active: set[int] = set()
    pending: list[tuple[object, str, int, bool]] = [(value, field, 0, False)]

    def charge(amount: int) -> None:
        nonlocal used
        used += amount
        if used > body_cap:
            raise ValueError(f"{field} serialized body exceeds resource cap")

    def text_bytes(text: str, path: str) -> int:
        total = 0
        for character in text:
            codepoint = ord(character)
            if codepoint <= 0x7F:
                total += 1
            elif codepoint <= 0x7FF:
                total += 2
            elif 0xD800 <= codepoint <= 0xDFFF:
                raise ValueError(f"{path} contains invalid UTF-8 text")
            elif codepoint <= 0xFFFF:
                total += 3
            else:
                total += 4
            if total > text_cap:
                raise ValueError(f"{path} text exceeds resource cap")
        return total

    while pending:
        item, path, depth, leaving = pending.pop()
        identity = id(item)
        if leaving:
            active.remove(identity)
            continue
        if depth > depth_cap:
            raise ValueError(f"{path} nesting exceeds resource cap")
        charge(32)
        item_type = type(item)
        if item is None or item_type is bool:
            continue
        if isinstance(item, Enum):
            pending.append((item.value, f"{path}.value", depth + 1, False))
            continue
        if isinstance(item, Fraction):
            pending.append((item.denominator, f"{path}.denominator", depth + 1, False))
            pending.append((item.numerator, f"{path}.numerator", depth + 1, False))
            continue
        if item_type is str:
            charge(text_bytes(item, path))
            continue
        if item_type is int:
            charge(4 + (item.bit_length() * 30_103) // 100_000)
            continue
        if item_type is float:
            if not math.isfinite(item):
                raise ValueError(f"{path} must be finite")
            charge(32)
            continue
        fields = getattr(item_type, "__dataclass_fields__", None)
        if fields is not None:
            if identity in active:
                raise ValueError(f"{path} contains a cyclic record")
            items = _exact_dataclass_items(item, path, fields)
            charge(8 * len(fields))
            active.add(identity)
            pending.append((item, path, depth, True))
            for name, nested in reversed(items):
                charge(text_bytes(name, f"{path}.{name}"))
                pending.append(
                    (
                        nested,
                        f"{path}.{name}",
                        depth + 1,
                        False,
                    )
                )
            continue
        if item_type in (tuple, list):
            if identity in active:
                raise ValueError(f"{path} contains a cyclic sequence")
            charge(4 * len(item))
            active.add(identity)
            pending.append((item, path, depth, True))
            for index in range(len(item) - 1, -1, -1):
                pending.append(
                    (
                        item[index],
                        f"{path}[{index}]",
                        depth + 1,
                        False,
                    )
                )
            continue
        if item_type is dict:
            if identity in active:
                raise ValueError(f"{path} contains a cyclic mapping")
            charge(8 * len(item))
            active.add(identity)
            pending.append((item, path, depth, True))
            for key in reversed(item):
                if type(key) is not str:
                    raise TypeError(f"{path} mapping keys must be strings")
                charge(text_bytes(key, f"{path}.{key}"))
                pending.append(
                    (
                        item[key],
                        f"{path}.{key}",
                        depth + 1,
                        False,
                    )
                )
            continue
        raise TypeError(f"{path} contains unsupported type {item_type.__name__}")


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _finite_float(value: object, field: str, *, nonnegative: bool = False) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    if nonnegative and value < 0.0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _optional_nonnegative(value: object, field: str) -> Optional[float]:
    if value is None:
        return None
    return _finite_float(value, field, nonnegative=True)


def _tuple(value: object, field: str, *, nonempty: bool = False) -> tuple:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if nonempty and not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _index(value: object, field: str, *, ndim: Optional[int] = None) -> tuple[int, ...]:
    checked = _tuple(value, field, nonempty=True)
    if ndim is not None and len(checked) != ndim:
        raise ValueError(f"{field} dimension mismatch")
    result: list[int] = []
    for axis, item in enumerate(checked):
        if type(item) is not int:
            raise TypeError(f"{field}[{axis}] must be an int")
        if item < 0:
            raise ValueError(f"{field}[{axis}] must be non-negative")
        result.append(item)
    return tuple(result)


def _float_tuple(
    value: object,
    field: str,
    *,
    nonnegative: bool = False,
) -> tuple[float, ...]:
    checked = _tuple(value, field)
    return tuple(
        _finite_float(item, f"{field}[{index}]", nonnegative=nonnegative)
        for index, item in enumerate(checked)
    )


def _optional_float_tuple(
    value: object,
    field: str,
) -> tuple[Optional[float], ...]:
    checked = _tuple(value, field)
    return tuple(
        _optional_nonnegative(item, f"{field}[{index}]")
        for index, item in enumerate(checked)
    )


def _int_tuple(value: object, field: str, *, positive: bool = False) -> tuple[int, ...]:
    checked = _tuple(value, field)
    validate = _positive_int if positive else _nonnegative_int
    return tuple(
        validate(item, f"{field}[{index}]") for index, item in enumerate(checked)
    )


def _phase_bands(value: object, field: str) -> tuple[tuple[float, float], ...]:
    checked = _tuple(value, field, nonempty=True)
    result: list[tuple[float, float]] = []
    for index, band in enumerate(checked):
        if type(band) is not tuple or len(band) != 2:
            raise TypeError(f"{field}[{index}] must be a pair")
        lower = _finite_float(band[0], f"{field}[{index}][0]")
        upper = _finite_float(band[1], f"{field}[{index}][1]")
        if not -math.pi <= lower < upper <= math.pi:
            raise ValueError(f"{field}[{index}] is not a principal phase band")
        result.append((lower, upper))
    answer = tuple(result)
    if answer != tuple(sorted(set(answer))):
        raise ValueError(f"{field} must be unique and canonical")
    return answer


def _closed_order(value: object, field: str = "fejer_order") -> int:
    order = _positive_int(value, field)
    if order not in _CLOSED_FEJER_ORDERS:
        raise ValueError(f"{field} is not a frozen Fejer order")
    return order


def _basis_record(value: BasisManifest) -> dict[str, object]:
    _exact_record(value, BasisManifest, "basis")
    _exact_dataclass_tree(value, "basis")
    verified = verify_basis_manifest(value)
    return {
        **basis_manifest_payload(verified),
        "manifest_id": verified.manifest_id,
    }


def _tensor_record(value: FrozenComplexTensor) -> dict[str, object]:
    _exact_record(value, FrozenComplexTensor, "tensor")
    _exact_dataclass_tree(value, "tensor")
    verified = verify_frozen_tensor(value)
    return {
        **frozen_tensor_payload(verified),
        "tensor_sha": verified.tensor_sha,
    }


def _frozen_tensor_from_raw_v1(raw_body: object) -> FrozenComplexTensor:
    core = _require_b7_replay_core_v1(_b7_replay_core_v1)
    checked = core._validate_frozen_complex_tensor_raw_v1(raw_body, "tensor")
    return verify_frozen_tensor(
        FrozenComplexTensor(
            tensor_schema_version=checked["tensor_schema_version"],
            shape=tuple(checked["shape"]),
            values_wire=tuple((wire[0], wire[1]) for wire in checked["values_wire"]),
            tensor_sha=checked["tensor_sha"],
        )
    )


def _build_fejer_branch_response_values_from_raw(
    branch,
    response_grid,
    fejer_order,
    source_basis,
    readout_basis,
    shell_phases,
    ordered_transition_matrices,
    ordered_metric_matrices,
):
    return _require_b7_replay_core_v1(
        _b7_replay_core_v1
    )._build_fejer_branch_response_values_from_raw(
        branch,
        response_grid,
        fejer_order,
        source_basis,
        readout_basis,
        shell_phases,
        ordered_transition_matrices,
        ordered_metric_matrices,
    )


def _select_endpoint_reference_from_raw(
    reference_spec,
    transition_matrix,
    metric_matrix,
    source_injection_matrix,
    readout_matrix,
):
    return _require_b7_replay_core_v1(
        _b7_replay_core_v1
    )._select_endpoint_reference_from_raw(
        reference_spec,
        transition_matrix,
        metric_matrix,
        source_injection_matrix,
        readout_matrix,
    )


def _track_endpoint_shell_from_raw(
    reference_outcome,
    shell_spec,
    ordered_transition_matrices,
    ordered_metric_matrices,
    source_injection_matrix,
    readout_matrix,
    actual_factory_sha,
    actual_transition_sha,
    actual_dynamics_certificate_sha,
    dt,
):
    return _require_b7_replay_core_v1(
        _b7_replay_core_v1
    )._track_endpoint_shell_from_raw(
        reference_outcome,
        shell_spec,
        ordered_transition_matrices,
        ordered_metric_matrices,
        source_injection_matrix,
        readout_matrix,
        actual_factory_sha,
        actual_transition_sha,
        actual_dynamics_certificate_sha,
        dt,
    )


def _assemble_atomic_paired_response_attempt_from_raw(
    actual_response_values,
    matched_ablated_response_values,
    actual_bridge_audit,
    matched_ablated_bridge_audit,
    first_failure,
):
    return _require_b7_replay_core_v1(
        _b7_replay_core_v1
    )._assemble_atomic_paired_response_attempt_from_raw(
        actual_response_values,
        matched_ablated_response_values,
        actual_bridge_audit,
        matched_ablated_bridge_audit,
        first_failure,
    )


def _audit_source_readout_bridge_from_raw(
    branch,
    factory_sha,
    transition_sha,
    dynamics_certificate_sha,
    run_spec_sha,
    bridge_grid,
    bridge_steps,
    source_trial_vectors,
    current_readout_calibration_spec,
    ordered_raw_differences,
):
    return _require_b7_replay_core_v1(
        _b7_replay_core_v1
    )._audit_source_readout_bridge_from_raw(
        branch,
        factory_sha,
        transition_sha,
        dynamics_certificate_sha,
        run_spec_sha,
        bridge_grid,
        bridge_steps,
        source_trial_vectors,
        current_readout_calibration_spec,
        ordered_raw_differences,
    )


def _response_grid_record(value: ResponseKGridManifest) -> dict[str, object]:
    _exact_response_grid_tree(value)
    return {
        **response_grid_payload(value),
        "response_grid_sha": value.response_grid_sha,
    }


def _bridge_grid_record(value: BridgeKGridManifest) -> dict[str, object]:
    _exact_bridge_grid_tree(value)
    return {
        **bridge_grid_payload(value),
        "bridge_grid_sha": value.bridge_grid_sha,
    }


def _registry_entry_record(value: ControlRegistryEntry) -> dict[str, object]:
    _exact_registry_entry_tree(value)
    return {
        **control_registry_entry_payload(value),
        "entry_sha": value.entry_sha,
    }


def _transition_record(value: MeasuredTransition) -> dict[str, object]:
    _exact_record(value, MeasuredTransition, "transition")
    _exact_dataclass_tree(value, "transition")
    return {
        **measured_transition_payload(value),
        "transition_sha": value.transition_sha,
    }


def _certificate_record(value: DynamicsCertificate) -> dict[str, object]:
    _exact_record(value, DynamicsCertificate, "dynamics_certificate")
    _exact_dataclass_tree(value, "dynamics_certificate")
    return {
        **dynamics_certificate_payload(value),
        "certificate_sha": value.certificate_sha,
    }


def _window_protocol_record(value: WindowCalibrationProtocol) -> dict[str, object]:
    _exact_record(value, WindowCalibrationProtocol, "window_protocol")
    _exact_dataclass_tree(value, "window_protocol")
    return {
        **window_calibration_protocol_payload(value),
        "protocol_sha": value.protocol_sha,
    }


def _status_record(value: BlockStatus) -> dict[str, object]:
    _exact_record(value, BlockStatus, "status")
    return {
        "defined": value.defined,
        "reason": None if value.reason is None else value.reason.value,
    }


@dataclass(frozen=True)
class ResponseRunSpec:
    run_spec_schema_version: str
    run_spec_id: str
    window_protocol_sha: str
    control_registry_entry_sha: str
    fejer_order: int
    state_schema_id: str
    channel_order: tuple[str, ...]
    source_basis: BasisManifest
    readout_basis: BasisManifest
    spatial_shape: tuple[int, ...]
    response_grid: ResponseKGridManifest
    source_readout_bridge_grid: BridgeKGridManifest
    source_readout_bridge_steps: tuple[int, ...]
    source_trial_vectors: FrozenComplexTensor
    bridge_tolerance: float
    spec_sha: str

    def __post_init__(self) -> None:
        _text(self.run_spec_schema_version, "run_spec_schema_version")
        _text(self.run_spec_id, "run_spec_id")
        _sha(self.window_protocol_sha, "window_protocol_sha")
        _sha(
            self.control_registry_entry_sha,
            "control_registry_entry_sha",
        )
        _closed_order(self.fejer_order)
        _text(self.state_schema_id, "state_schema_id")
        channels = _tuple(self.channel_order, "channel_order", nonempty=True)
        if not all(type(item) is str and item for item in channels):
            raise TypeError("channel_order must contain non-empty strings")
        if len(set(channels)) != len(channels):
            raise ValueError("channel_order must be unique")
        if type(self.source_basis) is not BasisManifest:
            raise TypeError("source_basis must be an exact BasisManifest")
        if type(self.readout_basis) is not BasisManifest:
            raise TypeError("readout_basis must be an exact BasisManifest")
        shape = _int_tuple(self.spatial_shape, "spatial_shape", positive=True)
        if not shape:
            raise ValueError("spatial_shape must be non-empty")
        if type(self.response_grid) is not ResponseKGridManifest:
            raise TypeError("response_grid has the wrong strict type")
        if type(self.source_readout_bridge_grid) is not BridgeKGridManifest:
            raise TypeError("source_readout_bridge_grid has the wrong strict type")
        steps = _int_tuple(
            self.source_readout_bridge_steps,
            "source_readout_bridge_steps",
            positive=True,
        )
        if not steps or steps != tuple(sorted(set(steps))):
            raise ValueError("source_readout_bridge_steps must be ascending")
        if steps[-1] > 16384 or not any(step > 1 for step in steps):
            raise ValueError("source bridge steps must contain t>1 through 16384")
        if type(self.source_trial_vectors) is not FrozenComplexTensor:
            raise TypeError("source_trial_vectors has the wrong strict type")
        if _finite_float(self.bridge_tolerance, "bridge_tolerance") != (
            _BRIDGE_TOLERANCE
        ):
            raise ValueError("bridge_tolerance is not frozen")
        _sha(self.spec_sha, "spec_sha")


@dataclass(frozen=True)
class EndpointReferenceSpec:
    reference_spec_schema_version: str
    window_protocol_sha: str
    control_registry_entry: ControlRegistryEntry
    actual_factory_sha: str
    actual_transition_sha: str
    actual_dynamics_certificate_sha: str
    candidate_fejer_order: int
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    expected_shell_rank: int
    expected_shell_rank_source_id: Literal["parent-freeze-control-application-spec-v1"]
    reference_spec_sha: str

    def __post_init__(self) -> None:
        _text(
            self.reference_spec_schema_version,
            "reference_spec_schema_version",
        )
        _sha(self.window_protocol_sha, "window_protocol_sha")
        if type(self.control_registry_entry) is not ControlRegistryEntry:
            raise TypeError("control_registry_entry has the wrong strict type")
        _sha(self.actual_factory_sha, "actual_factory_sha")
        _sha(self.actual_transition_sha, "actual_transition_sha")
        _sha(
            self.actual_dynamics_certificate_sha,
            "actual_dynamics_certificate_sha",
        )
        _closed_order(self.candidate_fejer_order, "candidate_fejer_order")
        _index(self.reference_reciprocal_index, "reference_reciprocal_index")
        _phase_bands(
            self.preregistered_phase_bands,
            "preregistered_phase_bands",
        )
        _positive_int(self.expected_shell_rank, "expected_shell_rank")
        if self.expected_shell_rank_source_id != _EXPECTED_RANK_SOURCE_ID:
            raise ValueError("expected_shell_rank_source_id is not frozen")
        _sha(self.reference_spec_sha, "reference_spec_sha")


@dataclass(frozen=True)
class EndpointReferenceProjector:
    reference_schema_version: str
    control_registry_entry_sha: str
    actual_transition_sha: str
    actual_dynamics_certificate_sha: str
    reference_reciprocal_index: tuple[int, ...]
    reference_phase: float
    projector_coordinate_convention_id: Literal["g-whitened-state-v1"]
    rank: int
    projector: FrozenComplexTensor
    reference_sha: str

    def __post_init__(self) -> None:
        _text(self.reference_schema_version, "reference_schema_version")
        _sha(
            self.control_registry_entry_sha,
            "control_registry_entry_sha",
        )
        _sha(self.actual_transition_sha, "actual_transition_sha")
        _sha(
            self.actual_dynamics_certificate_sha,
            "actual_dynamics_certificate_sha",
        )
        _index(self.reference_reciprocal_index, "reference_reciprocal_index")
        _finite_float(self.reference_phase, "reference_phase")
        if (
            self.projector_coordinate_convention_id
            != PROJECTOR_COORDINATE_CONVENTION_ID
        ):
            raise ValueError("projector coordinate convention is not frozen")
        rank = _positive_int(self.rank, "rank")
        if type(self.projector) is not FrozenComplexTensor:
            raise TypeError("projector has the wrong strict tensor type")
        if len(self.projector.shape) != 2:
            raise ValueError("projector must be a matrix")
        if self.projector.shape[0] != self.projector.shape[1]:
            raise ValueError("projector must be square")
        if rank > self.projector.shape[0]:
            raise ValueError("projector rank exceeds state dimension")
        _sha(self.reference_sha, "reference_sha")


class EndpointReferenceFailure(str, Enum):
    PHASE_BAND_EMPTY = "phase_band_empty"
    PHASE_BAND_NONUNIQUE = "phase_band_nonunique"
    RANK_MISMATCH = "rank_mismatch"
    PARTICIPATION_FAILED = "participation_failed"
    RUNNER_UP_MARGIN_FAILED = "runner_up_margin_failed"
    PROJECTOR_INVALID = "projector_invalid"


@dataclass(frozen=True)
class EndpointReferenceAttemptAudit:
    attempt_schema_version: str
    reference_spec: EndpointReferenceSpec
    candidate_phases: tuple[float, ...]
    candidate_ranks: tuple[int, ...]
    expected_shell_rank: int
    expected_shell_rank_source_id: Literal["parent-freeze-control-application-spec-v1"]
    candidate_participations: tuple[float, ...]
    runner_up_overlaps: tuple[Optional[float], ...]
    hermitian_residuals: tuple[float, ...]
    idempotent_residuals: tuple[float, ...]
    g_invariance_residuals: tuple[float, ...]
    eigenphase_residuals: tuple[float, ...]
    observed_competitor_gaps: tuple[Optional[float], ...]
    attempt_sha: str

    def __post_init__(self) -> None:
        _text(self.attempt_schema_version, "attempt_schema_version")
        if type(self.reference_spec) is not EndpointReferenceSpec:
            raise TypeError("reference_spec has the wrong strict type")
        phases = _float_tuple(self.candidate_phases, "candidate_phases")
        fields = (
            _int_tuple(self.candidate_ranks, "candidate_ranks", positive=True),
            _float_tuple(
                self.candidate_participations,
                "candidate_participations",
                nonnegative=True,
            ),
            _optional_float_tuple(
                self.runner_up_overlaps,
                "runner_up_overlaps",
            ),
            _float_tuple(
                self.hermitian_residuals,
                "hermitian_residuals",
                nonnegative=True,
            ),
            _float_tuple(
                self.idempotent_residuals,
                "idempotent_residuals",
                nonnegative=True,
            ),
            _float_tuple(
                self.g_invariance_residuals,
                "g_invariance_residuals",
                nonnegative=True,
            ),
            _float_tuple(
                self.eigenphase_residuals,
                "eigenphase_residuals",
                nonnegative=True,
            ),
            _optional_float_tuple(
                self.observed_competitor_gaps,
                "observed_competitor_gaps",
            ),
        )
        if any(len(item) != len(phases) for item in fields):
            raise ValueError("reference candidate audit columns must align")
        _positive_int(self.expected_shell_rank, "expected_shell_rank")
        if self.expected_shell_rank_source_id != _EXPECTED_RANK_SOURCE_ID:
            raise ValueError("expected shell rank source is not frozen")
        _sha(self.attempt_sha, "attempt_sha")


@dataclass(frozen=True)
class EndpointReferenceOutcome:
    status: BlockStatus
    failure: Optional[EndpointReferenceFailure]
    reference_spec: EndpointReferenceSpec
    attempt_audit: EndpointReferenceAttemptAudit
    reference: Optional[EndpointReferenceProjector]
    outcome_sha: str

    def __post_init__(self) -> None:
        if type(self.status) is not BlockStatus:
            raise TypeError("status has the wrong strict type")
        if (
            self.failure is not None
            and type(self.failure) is not EndpointReferenceFailure
        ):
            raise TypeError("failure has the wrong enum type")
        if type(self.reference_spec) is not EndpointReferenceSpec:
            raise TypeError("reference_spec has the wrong strict type")
        if type(self.attempt_audit) is not EndpointReferenceAttemptAudit:
            raise TypeError("attempt_audit has the wrong strict type")
        if self.reference is not None and (
            type(self.reference) is not EndpointReferenceProjector
        ):
            raise TypeError("reference has the wrong strict type")
        success = self.failure is None
        if self.status.defined != success:
            raise ValueError("reference status/failure presence mismatch")
        if success != (self.reference is not None):
            raise ValueError("reference payload presence mismatch")
        _sha(self.outcome_sha, "outcome_sha")


@dataclass(frozen=True)
class EndpointShellSpec:
    shell_spec_schema_version: str
    window_protocol_sha: str
    control_registry_entry: ControlRegistryEntry
    response_grid: ResponseKGridManifest
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    candidate_fejer_order: int
    endpoint_reference_projector: EndpointReferenceProjector
    extraction_protocol_id: Literal["endpoint-single-node-reference-v1"]
    shell_spec_sha: str

    def __post_init__(self) -> None:
        _text(self.shell_spec_schema_version, "shell_spec_schema_version")
        _sha(self.window_protocol_sha, "window_protocol_sha")
        if type(self.control_registry_entry) is not ControlRegistryEntry:
            raise TypeError("control_registry_entry has the wrong strict type")
        if type(self.response_grid) is not ResponseKGridManifest:
            raise TypeError("response_grid has the wrong strict type")
        _phase_bands(
            self.preregistered_phase_bands,
            "preregistered_phase_bands",
        )
        _closed_order(self.candidate_fejer_order, "candidate_fejer_order")
        if type(self.endpoint_reference_projector) is not EndpointReferenceProjector:
            raise TypeError("endpoint_reference_projector has the wrong strict type")
        if self.extraction_protocol_id != SHELL_EXTRACTION_PROTOCOL_ID:
            raise ValueError("shell extraction protocol is not frozen")
        _sha(self.shell_spec_sha, "shell_spec_sha")


@dataclass(frozen=True)
class ShellPointAudit:
    reciprocal_index: tuple[int, ...]
    momentum_path_id: str
    momentum_path_position: int
    shell_phase: float
    rank: int
    hermitian_residual: float
    idempotent_residual: float
    g_invariance_residual: float
    eigenphase_residual: float
    participation: float
    nearest_competitor_gap: Optional[float]
    reference_overlap: float
    runner_up_overlap: Optional[float]
    predecessor_overlap: Optional[float]
    loop_residual: Optional[float]

    def __post_init__(self) -> None:
        _index(self.reciprocal_index, "reciprocal_index")
        _text(self.momentum_path_id, "momentum_path_id")
        _nonnegative_int(
            self.momentum_path_position,
            "momentum_path_position",
        )
        _finite_float(self.shell_phase, "shell_phase")
        _positive_int(self.rank, "rank")
        for field in (
            "hermitian_residual",
            "idempotent_residual",
            "g_invariance_residual",
            "eigenphase_residual",
            "participation",
            "reference_overlap",
        ):
            _finite_float(getattr(self, field), field, nonnegative=True)
        for field in (
            "nearest_competitor_gap",
            "runner_up_overlap",
            "predecessor_overlap",
            "loop_residual",
        ):
            _optional_nonnegative(getattr(self, field), field)


@dataclass(frozen=True)
class EndpointShellManifest:
    shell_schema_version: str
    actual_factory_sha: str
    actual_transition_sha: str
    actual_dynamics_certificate_sha: str
    shell_spec: EndpointShellSpec
    dt: float
    eigenphase_convention_id: Literal["lambda-exp-plus-i-theta-principal-v1"]
    shell_phases: tuple[float, ...]
    shell_projectors: FrozenComplexTensor
    point_audits: tuple[ShellPointAudit, ...]
    hermitian_residual_max: float
    idempotent_residual_max: float
    g_invariance_residual_max: float
    eigenphase_residual_max: float
    participation_min: float
    nearest_competitor_gap_min: Optional[float]
    reference_overlap_min: float
    runner_up_overlap_max: Optional[float]
    predecessor_overlap_min: Optional[float]
    overlap_margin_min: Optional[float]
    loop_residual_max: Optional[float]
    ambiguous: bool
    shell_manifest_sha: str

    def __post_init__(self) -> None:
        _text(self.shell_schema_version, "shell_schema_version")
        _sha(self.actual_factory_sha, "actual_factory_sha")
        _sha(self.actual_transition_sha, "actual_transition_sha")
        _sha(
            self.actual_dynamics_certificate_sha,
            "actual_dynamics_certificate_sha",
        )
        if type(self.shell_spec) is not EndpointShellSpec:
            raise TypeError("shell_spec has the wrong strict type")
        if _finite_float(self.dt, "dt") <= 0.0:
            raise ValueError("dt must be positive")
        if self.eigenphase_convention_id != EIGENPHASE_CONVENTION_ID:
            raise ValueError("eigenphase convention is not frozen")
        phases = _float_tuple(self.shell_phases, "shell_phases")
        if type(self.shell_projectors) is not FrozenComplexTensor:
            raise TypeError("shell_projectors has the wrong strict type")
        audits = _tuple(self.point_audits, "point_audits", nonempty=True)
        if not all(type(item) is ShellPointAudit for item in audits):
            raise TypeError("point_audits contains the wrong strict type")
        if len(phases) != len(audits):
            raise ValueError("shell phases and point audits must align")
        if (
            len(self.shell_projectors.shape) != 3
            or self.shell_projectors.shape[0] != len(audits)
            or self.shell_projectors.shape[1] != self.shell_projectors.shape[2]
        ):
            raise ValueError("shell_projectors shape mismatch")
        for field in (
            "hermitian_residual_max",
            "idempotent_residual_max",
            "g_invariance_residual_max",
            "eigenphase_residual_max",
            "participation_min",
            "reference_overlap_min",
        ):
            _finite_float(getattr(self, field), field, nonnegative=True)
        for field in (
            "nearest_competitor_gap_min",
            "runner_up_overlap_max",
            "predecessor_overlap_min",
            "overlap_margin_min",
            "loop_residual_max",
        ):
            _optional_nonnegative(getattr(self, field), field)
        if type(self.ambiguous) is not bool:
            raise TypeError("ambiguous must be a bool")
        _sha(self.shell_manifest_sha, "shell_manifest_sha")


class EndpointShellFailure(str, Enum):
    PHASE_BAND_EMPTY = "phase_band_empty"
    PHASE_SEPARATION_FAILED = "phase_separation_failed"
    GAP_FAILED = "gap_failed"
    PARTICIPATION_FAILED = "participation_failed"
    REFERENCE_AMBIGUOUS = "reference_ambiguous"
    RUNNER_UP_MARGIN = "runner_up_margin"
    LOOP_INCONSISTENT = "loop_inconsistent"
    PROJECTOR_INVALID = "projector_invalid"


@dataclass(frozen=True)
class ShellCandidatePointAttempt:
    reciprocal_index: tuple[int, ...]
    momentum_path_id: str
    momentum_path_position: int
    candidate_phases: tuple[float, ...]
    candidate_ranks: tuple[int, ...]
    candidate_participations: tuple[float, ...]
    candidate_reference_overlaps: tuple[float, ...]
    candidate_predecessor_overlaps: tuple[Optional[float], ...]

    def __post_init__(self) -> None:
        _index(self.reciprocal_index, "reciprocal_index")
        _text(self.momentum_path_id, "momentum_path_id")
        _nonnegative_int(
            self.momentum_path_position,
            "momentum_path_position",
        )
        phases = _float_tuple(self.candidate_phases, "candidate_phases")
        aligned = (
            _int_tuple(self.candidate_ranks, "candidate_ranks", positive=True),
            _float_tuple(
                self.candidate_participations,
                "candidate_participations",
                nonnegative=True,
            ),
            _float_tuple(
                self.candidate_reference_overlaps,
                "candidate_reference_overlaps",
                nonnegative=True,
            ),
            _optional_float_tuple(
                self.candidate_predecessor_overlaps,
                "candidate_predecessor_overlaps",
            ),
        )
        if any(len(item) != len(phases) for item in aligned):
            raise ValueError("shell candidate point columns must align")


@dataclass(frozen=True)
class EndpointShellAttemptAudit:
    attempt_schema_version: str
    shell_spec: EndpointShellSpec
    point_attempts: tuple[ShellCandidatePointAttempt, ...]
    projector_residual_max: float
    loop_residual_max_observed: Optional[float]
    attempt_sha: str

    def __post_init__(self) -> None:
        _text(self.attempt_schema_version, "attempt_schema_version")
        if type(self.shell_spec) is not EndpointShellSpec:
            raise TypeError("shell_spec has the wrong strict type")
        attempts = _tuple(self.point_attempts, "point_attempts")
        if not all(type(item) is ShellCandidatePointAttempt for item in attempts):
            raise TypeError("point_attempts contains the wrong strict type")
        _finite_float(
            self.projector_residual_max,
            "projector_residual_max",
            nonnegative=True,
        )
        _optional_nonnegative(
            self.loop_residual_max_observed,
            "loop_residual_max_observed",
        )
        _sha(self.attempt_sha, "attempt_sha")


@dataclass(frozen=True)
class EndpointShellOutcome:
    status: BlockStatus
    failure: Optional[EndpointShellFailure]
    reference_outcome: EndpointReferenceOutcome
    attempt_audit: EndpointShellAttemptAudit
    shell: Optional[EndpointShellManifest]
    outcome_sha: str

    def __post_init__(self) -> None:
        if type(self.status) is not BlockStatus:
            raise TypeError("status has the wrong strict type")
        if self.failure is not None and type(self.failure) is not EndpointShellFailure:
            raise TypeError("failure has the wrong enum type")
        if type(self.reference_outcome) is not EndpointReferenceOutcome:
            raise TypeError("reference_outcome has the wrong strict type")
        if type(self.attempt_audit) is not EndpointShellAttemptAudit:
            raise TypeError("attempt_audit has the wrong strict type")
        if self.shell is not None and type(self.shell) is not EndpointShellManifest:
            raise TypeError("shell has the wrong strict type")
        success = self.failure is None
        if self.status.defined != success:
            raise ValueError("shell status/failure presence mismatch")
        if success != (self.shell is not None):
            raise ValueError("shell payload presence mismatch")
        _sha(self.outcome_sha, "outcome_sha")


@dataclass(frozen=True)
class SourceFrameCoverageCertificate:
    certificate_schema_version: str
    source_basis_sha: str
    trial_matrix: FrozenComplexTensor
    frame_operator_lower: float
    canonical_dual_residual_upper: float
    certificate_sha: str

    def __post_init__(self) -> None:
        _text(
            self.certificate_schema_version,
            "certificate_schema_version",
        )
        _sha(self.source_basis_sha, "source_basis_sha")
        if type(self.trial_matrix) is not FrozenComplexTensor:
            raise TypeError("trial_matrix has the wrong strict type")
        if (
            _finite_float(
                self.frame_operator_lower,
                "frame_operator_lower",
            )
            <= 0.0
        ):
            raise ValueError("frame_operator_lower must be positive")
        _finite_float(
            self.canonical_dual_residual_upper,
            "canonical_dual_residual_upper",
            nonnegative=True,
        )
        _sha(self.certificate_sha, "certificate_sha")


@dataclass(frozen=True)
class SourceReadoutBridgeMatrixAudit:
    reciprocal_index: tuple[int, ...]
    macro_steps: int
    raw_difference_matrix: FrozenComplexTensor
    frame_coverage: Optional[SourceFrameCoverageCertificate]
    raw_frobenius_upper: float
    raw_operator_norm_upper: float
    h_whitened_operator_error_upper: float
    curv_whitened_operator_error_upper: float

    def __post_init__(self) -> None:
        _index(self.reciprocal_index, "reciprocal_index")
        _positive_int(self.macro_steps, "macro_steps")
        if type(self.raw_difference_matrix) is not FrozenComplexTensor:
            raise TypeError("raw_difference_matrix has the wrong strict type")
        if self.frame_coverage is not None and (
            type(self.frame_coverage) is not SourceFrameCoverageCertificate
        ):
            raise TypeError("frame_coverage has the wrong strict type")
        for field in (
            "raw_frobenius_upper",
            "raw_operator_norm_upper",
            "h_whitened_operator_error_upper",
            "curv_whitened_operator_error_upper",
        ):
            _finite_float(getattr(self, field), field, nonnegative=True)


@dataclass(frozen=True)
class SourceReadoutBridgeAudit:
    bridge_schema_version: str
    branch: Literal["actual", "matched_ablated"]
    factory_sha: str
    transition_sha: str
    dynamics_certificate_sha: str
    run_spec_sha: str
    source_metric_whitener_sha: str
    readout_calibration_spec_sha: str
    matrix_audits: tuple[SourceReadoutBridgeMatrixAudit, ...]
    h_operator_error_max: float
    curv_operator_error_max: float
    bridge_sha: str

    def __post_init__(self) -> None:
        _text(self.bridge_schema_version, "bridge_schema_version")
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("branch is not closed")
        for field in (
            "factory_sha",
            "transition_sha",
            "dynamics_certificate_sha",
            "run_spec_sha",
            "source_metric_whitener_sha",
            "readout_calibration_spec_sha",
            "bridge_sha",
        ):
            _sha(getattr(self, field), field)
        audits = _tuple(self.matrix_audits, "matrix_audits", nonempty=True)
        if not all(type(item) is SourceReadoutBridgeMatrixAudit for item in audits):
            raise TypeError("matrix_audits contains the wrong strict type")
        _finite_float(
            self.h_operator_error_max,
            "h_operator_error_max",
            nonnegative=True,
        )
        _finite_float(
            self.curv_operator_error_max,
            "curv_operator_error_max",
            nonnegative=True,
        )


@dataclass(frozen=True)
class SourceReadoutResponse:
    response_schema_version: str
    branch: Literal["actual", "matched_ablated"]
    factory_sha: str
    transition_sha: str
    dynamics_certificate_sha: str
    source_basis: BasisManifest
    readout_basis: BasisManifest
    run_spec_sha: str
    shell_manifest_sha: str
    bridge_audit: SourceReadoutBridgeAudit
    values: FrozenComplexTensor
    response_sha: str

    def __post_init__(self) -> None:
        _text(self.response_schema_version, "response_schema_version")
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("branch is not closed")
        for field in (
            "factory_sha",
            "transition_sha",
            "dynamics_certificate_sha",
            "run_spec_sha",
            "shell_manifest_sha",
            "response_sha",
        ):
            _sha(getattr(self, field), field)
        if type(self.source_basis) is not BasisManifest:
            raise TypeError("source_basis has the wrong strict type")
        if type(self.readout_basis) is not BasisManifest:
            raise TypeError("readout_basis has the wrong strict type")
        if type(self.bridge_audit) is not SourceReadoutBridgeAudit:
            raise TypeError("bridge_audit has the wrong strict type")
        if type(self.values) is not FrozenComplexTensor:
            raise TypeError("values has the wrong strict type")


@dataclass(frozen=True)
class PairedFilteredResponse:
    pair_schema_version: str
    ablation_manifest_sha: str
    qualification_sha: str
    actual_dynamics_certificate: DynamicsCertificate
    ablated_dynamics_certificate: DynamicsCertificate
    actual: SourceReadoutResponse
    ablated: SourceReadoutResponse
    run_spec: ResponseRunSpec
    shell_manifest: EndpointShellManifest
    pair_sha: str

    def __post_init__(self) -> None:
        _text(self.pair_schema_version, "pair_schema_version")
        _sha(self.ablation_manifest_sha, "ablation_manifest_sha")
        _sha(self.qualification_sha, "qualification_sha")
        if type(self.actual_dynamics_certificate) is not DynamicsCertificate:
            raise TypeError("actual_dynamics_certificate has the wrong strict type")
        if type(self.ablated_dynamics_certificate) is not DynamicsCertificate:
            raise TypeError("ablated_dynamics_certificate has the wrong strict type")
        if type(self.actual) is not SourceReadoutResponse:
            raise TypeError("actual has the wrong strict type")
        if type(self.ablated) is not SourceReadoutResponse:
            raise TypeError("ablated has the wrong strict type")
        if type(self.run_spec) is not ResponseRunSpec:
            raise TypeError("run_spec has the wrong strict type")
        if type(self.shell_manifest) is not EndpointShellManifest:
            raise TypeError("shell_manifest has the wrong strict type")
        _sha(self.pair_sha, "pair_sha")


class PairedResponseFailure(str, Enum):
    QUALIFICATION_INVALID = "qualification_invalid"
    INPUT_BINDING_INVALID = "input_binding_invalid"
    ACTUAL_RESPONSE_FAILED = "actual_response_failed"
    ABLATED_RESPONSE_FAILED = "ablated_response_failed"
    ACTUAL_BRIDGE_FAILED = "actual_bridge_failed"
    ABLATED_BRIDGE_FAILED = "ablated_bridge_failed"


@dataclass(frozen=True)
class SourceReadoutBranchAttemptAudit:
    branch: Literal["actual", "matched_ablated"]
    response_values: Optional[FrozenComplexTensor]
    bridge_audit: Optional[SourceReadoutBridgeAudit]
    failure: Optional[PairedResponseFailure]
    attempt_sha: str

    def __post_init__(self) -> None:
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("branch is not closed")
        if self.response_values is not None and (
            type(self.response_values) is not FrozenComplexTensor
        ):
            raise TypeError("response_values has the wrong strict type")
        if self.bridge_audit is not None and (
            type(self.bridge_audit) is not SourceReadoutBridgeAudit
        ):
            raise TypeError("bridge_audit has the wrong strict type")
        if self.failure is not None and type(self.failure) is not PairedResponseFailure:
            raise TypeError("failure has the wrong enum type")
        _sha(self.attempt_sha, "attempt_sha")


@dataclass(frozen=True)
class PairedResponseAttemptAudit:
    attempt_schema_version: str
    window_protocol: WindowCalibrationProtocol
    qualification_sha: str
    actual_factory_sha: str
    ablated_factory_sha: str
    actual_transition: MeasuredTransition
    ablated_transition: MeasuredTransition
    actual_dynamics_certificate: DynamicsCertificate
    ablated_dynamics_certificate: DynamicsCertificate
    run_spec: ResponseRunSpec
    shell_outcome: EndpointShellOutcome
    actual_branch_attempt: Optional[SourceReadoutBranchAttemptAudit]
    ablated_branch_attempt: Optional[SourceReadoutBranchAttemptAudit]
    first_failure: Optional[PairedResponseFailure]
    attempt_sha: str

    def __post_init__(self) -> None:
        _text(self.attempt_schema_version, "attempt_schema_version")
        if type(self.window_protocol) is not WindowCalibrationProtocol:
            raise TypeError("window_protocol has the wrong strict type")
        for field in (
            "qualification_sha",
            "actual_factory_sha",
            "ablated_factory_sha",
            "attempt_sha",
        ):
            _sha(getattr(self, field), field)
        if type(self.actual_transition) is not MeasuredTransition:
            raise TypeError("actual_transition has the wrong strict type")
        if type(self.ablated_transition) is not MeasuredTransition:
            raise TypeError("ablated_transition has the wrong strict type")
        if type(self.actual_dynamics_certificate) is not DynamicsCertificate:
            raise TypeError("actual dynamics certificate has the wrong type")
        if type(self.ablated_dynamics_certificate) is not DynamicsCertificate:
            raise TypeError("ablated dynamics certificate has the wrong type")
        if type(self.run_spec) is not ResponseRunSpec:
            raise TypeError("run_spec has the wrong strict type")
        if type(self.shell_outcome) is not EndpointShellOutcome:
            raise TypeError("shell_outcome has the wrong strict type")
        for field in ("actual_branch_attempt", "ablated_branch_attempt"):
            item = getattr(self, field)
            if item is not None and type(item) is not SourceReadoutBranchAttemptAudit:
                raise TypeError(f"{field} has the wrong strict type")
        if self.first_failure is not None and (
            type(self.first_failure) is not PairedResponseFailure
        ):
            raise TypeError("first_failure has the wrong enum type")


@dataclass(frozen=True)
class PairedResponseOutcome:
    status: BlockStatus
    failure: Optional[PairedResponseFailure]
    attempt_audit: PairedResponseAttemptAudit
    paired_response: Optional[PairedFilteredResponse]
    outcome_sha: str

    def __post_init__(self) -> None:
        if type(self.status) is not BlockStatus:
            raise TypeError("status has the wrong strict type")
        if self.failure is not None and type(self.failure) is not PairedResponseFailure:
            raise TypeError("failure has the wrong enum type")
        if type(self.attempt_audit) is not PairedResponseAttemptAudit:
            raise TypeError("attempt_audit has the wrong strict type")
        if self.paired_response is not None and (
            type(self.paired_response) is not PairedFilteredResponse
        ):
            raise TypeError("paired_response has the wrong strict type")
        success = self.failure is None
        if self.status.defined != success:
            raise ValueError("paired status/failure presence mismatch")
        if success != (self.paired_response is not None):
            raise ValueError("paired payload presence mismatch")
        _sha(self.outcome_sha, "outcome_sha")


def response_run_spec_payload(spec: ResponseRunSpec) -> dict[str, object]:
    _exact_record(spec, ResponseRunSpec, "spec")
    return {
        "run_spec_schema_version": spec.run_spec_schema_version,
        "run_spec_id": spec.run_spec_id,
        "window_protocol_sha": spec.window_protocol_sha,
        "control_registry_entry_sha": spec.control_registry_entry_sha,
        "fejer_order": spec.fejer_order,
        "state_schema_id": spec.state_schema_id,
        "channel_order": list(spec.channel_order),
        "source_basis": _basis_record(spec.source_basis),
        "readout_basis": _basis_record(spec.readout_basis),
        "spatial_shape": list(spec.spatial_shape),
        "response_grid": _response_grid_record(spec.response_grid),
        "source_readout_bridge_grid": _bridge_grid_record(
            spec.source_readout_bridge_grid
        ),
        "source_readout_bridge_steps": list(spec.source_readout_bridge_steps),
        "source_trial_vectors": _tensor_record(spec.source_trial_vectors),
        "bridge_tolerance": spec.bridge_tolerance,
    }


def _response_run_spec_record(spec: ResponseRunSpec) -> dict[str, object]:
    return {
        **response_run_spec_payload(spec),
        "spec_sha": spec.spec_sha,
    }


def endpoint_reference_spec_payload(
    spec: EndpointReferenceSpec,
) -> dict[str, object]:
    _exact_record(spec, EndpointReferenceSpec, "reference_spec")
    return {
        "reference_spec_schema_version": (spec.reference_spec_schema_version),
        "window_protocol_sha": spec.window_protocol_sha,
        "control_registry_entry": _registry_entry_record(spec.control_registry_entry),
        "actual_factory_sha": spec.actual_factory_sha,
        "actual_transition_sha": spec.actual_transition_sha,
        "actual_dynamics_certificate_sha": (spec.actual_dynamics_certificate_sha),
        "candidate_fejer_order": spec.candidate_fejer_order,
        "reference_reciprocal_index": list(spec.reference_reciprocal_index),
        "preregistered_phase_bands": [
            list(item) for item in spec.preregistered_phase_bands
        ],
        "expected_shell_rank": spec.expected_shell_rank,
        "expected_shell_rank_source_id": (spec.expected_shell_rank_source_id),
    }


def _endpoint_reference_spec_record(
    spec: EndpointReferenceSpec,
) -> dict[str, object]:
    return {
        **endpoint_reference_spec_payload(spec),
        "reference_spec_sha": spec.reference_spec_sha,
    }


def endpoint_reference_projector_payload(
    reference: EndpointReferenceProjector,
) -> dict[str, object]:
    _exact_record(
        reference,
        EndpointReferenceProjector,
        "endpoint_reference_projector",
    )
    return {
        "reference_schema_version": reference.reference_schema_version,
        "control_registry_entry_sha": (reference.control_registry_entry_sha),
        "actual_transition_sha": reference.actual_transition_sha,
        "actual_dynamics_certificate_sha": (reference.actual_dynamics_certificate_sha),
        "reference_reciprocal_index": list(reference.reference_reciprocal_index),
        "reference_phase": reference.reference_phase,
        "projector_coordinate_convention_id": (
            reference.projector_coordinate_convention_id
        ),
        "rank": reference.rank,
        "projector": _tensor_record(reference.projector),
    }


def _endpoint_reference_projector_record(
    reference: EndpointReferenceProjector,
) -> dict[str, object]:
    return {
        **endpoint_reference_projector_payload(reference),
        "reference_sha": reference.reference_sha,
    }


def endpoint_reference_attempt_audit_payload(
    audit: EndpointReferenceAttemptAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        EndpointReferenceAttemptAudit,
        "endpoint_reference_attempt",
    )
    return {
        "attempt_schema_version": audit.attempt_schema_version,
        "reference_spec": _endpoint_reference_spec_record(audit.reference_spec),
        "candidate_phases": list(audit.candidate_phases),
        "candidate_ranks": list(audit.candidate_ranks),
        "expected_shell_rank": audit.expected_shell_rank,
        "expected_shell_rank_source_id": (audit.expected_shell_rank_source_id),
        "candidate_participations": list(audit.candidate_participations),
        "runner_up_overlaps": list(audit.runner_up_overlaps),
        "hermitian_residuals": list(audit.hermitian_residuals),
        "idempotent_residuals": list(audit.idempotent_residuals),
        "g_invariance_residuals": list(audit.g_invariance_residuals),
        "eigenphase_residuals": list(audit.eigenphase_residuals),
        "observed_competitor_gaps": list(audit.observed_competitor_gaps),
    }


def _endpoint_reference_attempt_record(
    audit: EndpointReferenceAttemptAudit,
) -> dict[str, object]:
    return {
        **endpoint_reference_attempt_audit_payload(audit),
        "attempt_sha": audit.attempt_sha,
    }


def endpoint_reference_outcome_payload(
    outcome: EndpointReferenceOutcome,
) -> dict[str, object]:
    _exact_record(
        outcome,
        EndpointReferenceOutcome,
        "endpoint_reference_outcome",
    )
    return {
        "status": _status_record(outcome.status),
        "failure": (None if outcome.failure is None else outcome.failure.value),
        "reference_spec": _endpoint_reference_spec_record(outcome.reference_spec),
        "attempt_audit": _endpoint_reference_attempt_record(outcome.attempt_audit),
        "reference": (
            None
            if outcome.reference is None
            else _endpoint_reference_projector_record(outcome.reference)
        ),
    }


def _endpoint_reference_outcome_record(
    outcome: EndpointReferenceOutcome,
) -> dict[str, object]:
    return {
        **endpoint_reference_outcome_payload(outcome),
        "outcome_sha": outcome.outcome_sha,
    }


def _endpoint_reference_outcome_from_raw_v1(
    raw_body: object,
    live_spec: EndpointReferenceSpec,
    expected_raw_spec: dict[str, object],
) -> EndpointReferenceOutcome:
    core = _require_b7_replay_core_v1(_b7_replay_core_v1)
    checked = core.validate_endpoint_reference_outcome_raw_v1(raw_body)
    for embedded in (
        checked["reference_spec"],
        checked["attempt_audit"]["reference_spec"],
    ):
        if core.canonical_json_bytes_v1(embedded) != core.canonical_json_bytes_v1(
            expected_raw_spec
        ):
            raise ValueError("raw reference leaf changed its live spec binding")
    raw_attempt = checked["attempt_audit"]
    attempt = EndpointReferenceAttemptAudit(
        attempt_schema_version=raw_attempt["attempt_schema_version"],
        reference_spec=live_spec,
        candidate_phases=tuple(raw_attempt["candidate_phases"]),
        candidate_ranks=tuple(raw_attempt["candidate_ranks"]),
        expected_shell_rank=raw_attempt["expected_shell_rank"],
        expected_shell_rank_source_id=raw_attempt["expected_shell_rank_source_id"],
        candidate_participations=tuple(raw_attempt["candidate_participations"]),
        runner_up_overlaps=tuple(raw_attempt["runner_up_overlaps"]),
        hermitian_residuals=tuple(raw_attempt["hermitian_residuals"]),
        idempotent_residuals=tuple(raw_attempt["idempotent_residuals"]),
        g_invariance_residuals=tuple(raw_attempt["g_invariance_residuals"]),
        eigenphase_residuals=tuple(raw_attempt["eigenphase_residuals"]),
        observed_competitor_gaps=tuple(raw_attempt["observed_competitor_gaps"]),
        attempt_sha=raw_attempt["attempt_sha"],
    )
    if attempt.attempt_sha != canonical_sha(
        endpoint_reference_attempt_audit_payload(attempt)
    ):
        raise ValueError("raw reference leaf returned a noncanonical attempt SHA")
    raw_reference = checked["reference"]
    reference = None
    if raw_reference is not None:
        reference = EndpointReferenceProjector(
            reference_schema_version=raw_reference["reference_schema_version"],
            control_registry_entry_sha=raw_reference["control_registry_entry_sha"],
            actual_transition_sha=raw_reference["actual_transition_sha"],
            actual_dynamics_certificate_sha=raw_reference[
                "actual_dynamics_certificate_sha"
            ],
            reference_reciprocal_index=tuple(
                raw_reference["reference_reciprocal_index"]
            ),
            reference_phase=raw_reference["reference_phase"],
            projector_coordinate_convention_id=raw_reference[
                "projector_coordinate_convention_id"
            ],
            rank=raw_reference["rank"],
            projector=_frozen_tensor_from_raw_v1(raw_reference["projector"]),
            reference_sha=raw_reference["reference_sha"],
        )
        if reference.reference_sha != canonical_sha(
            endpoint_reference_projector_payload(reference)
        ):
            raise ValueError("raw reference leaf returned a noncanonical projector SHA")
    raw_status = checked["status"]
    status = BlockStatus(
        raw_status["defined"],
        (
            None
            if raw_status["reason"] is None
            else UndefinedReason(raw_status["reason"])
        ),
    )
    failure = (
        None
        if checked["failure"] is None
        else EndpointReferenceFailure(checked["failure"])
    )
    outcome = EndpointReferenceOutcome(
        status=status,
        failure=failure,
        reference_spec=live_spec,
        attempt_audit=attempt,
        reference=reference,
        outcome_sha=checked["outcome_sha"],
    )
    if outcome.outcome_sha != canonical_sha(
        endpoint_reference_outcome_payload(outcome)
    ):
        raise ValueError("raw reference leaf returned a noncanonical outcome SHA")
    return outcome


def endpoint_shell_spec_payload(
    spec: EndpointShellSpec,
) -> dict[str, object]:
    _exact_record(spec, EndpointShellSpec, "endpoint_shell_spec")
    return {
        "shell_spec_schema_version": spec.shell_spec_schema_version,
        "window_protocol_sha": spec.window_protocol_sha,
        "control_registry_entry": _registry_entry_record(spec.control_registry_entry),
        "response_grid": _response_grid_record(spec.response_grid),
        "preregistered_phase_bands": [
            list(item) for item in spec.preregistered_phase_bands
        ],
        "candidate_fejer_order": spec.candidate_fejer_order,
        "endpoint_reference_projector": (
            _endpoint_reference_projector_record(spec.endpoint_reference_projector)
        ),
        "extraction_protocol_id": spec.extraction_protocol_id,
    }


def _endpoint_shell_spec_record(
    spec: EndpointShellSpec,
) -> dict[str, object]:
    return {
        **endpoint_shell_spec_payload(spec),
        "shell_spec_sha": spec.shell_spec_sha,
    }


def shell_point_audit_payload(
    audit: ShellPointAudit,
) -> dict[str, object]:
    _exact_record(audit, ShellPointAudit, "shell_point_audit")
    return {
        "reciprocal_index": list(audit.reciprocal_index),
        "momentum_path_id": audit.momentum_path_id,
        "momentum_path_position": audit.momentum_path_position,
        "shell_phase": audit.shell_phase,
        "rank": audit.rank,
        "hermitian_residual": audit.hermitian_residual,
        "idempotent_residual": audit.idempotent_residual,
        "g_invariance_residual": audit.g_invariance_residual,
        "eigenphase_residual": audit.eigenphase_residual,
        "participation": audit.participation,
        "nearest_competitor_gap": audit.nearest_competitor_gap,
        "reference_overlap": audit.reference_overlap,
        "runner_up_overlap": audit.runner_up_overlap,
        "predecessor_overlap": audit.predecessor_overlap,
        "loop_residual": audit.loop_residual,
    }


def endpoint_shell_manifest_payload(
    shell: EndpointShellManifest,
) -> dict[str, object]:
    _exact_record(shell, EndpointShellManifest, "endpoint_shell_manifest")
    return {
        "shell_schema_version": shell.shell_schema_version,
        "actual_factory_sha": shell.actual_factory_sha,
        "actual_transition_sha": shell.actual_transition_sha,
        "actual_dynamics_certificate_sha": (shell.actual_dynamics_certificate_sha),
        "shell_spec": _endpoint_shell_spec_record(shell.shell_spec),
        "dt": shell.dt,
        "eigenphase_convention_id": shell.eigenphase_convention_id,
        "shell_phases": list(shell.shell_phases),
        "shell_projectors": _tensor_record(shell.shell_projectors),
        "point_audits": [
            shell_point_audit_payload(item) for item in shell.point_audits
        ],
        "hermitian_residual_max": shell.hermitian_residual_max,
        "idempotent_residual_max": shell.idempotent_residual_max,
        "g_invariance_residual_max": shell.g_invariance_residual_max,
        "eigenphase_residual_max": shell.eigenphase_residual_max,
        "participation_min": shell.participation_min,
        "nearest_competitor_gap_min": (shell.nearest_competitor_gap_min),
        "reference_overlap_min": shell.reference_overlap_min,
        "runner_up_overlap_max": shell.runner_up_overlap_max,
        "predecessor_overlap_min": shell.predecessor_overlap_min,
        "overlap_margin_min": shell.overlap_margin_min,
        "loop_residual_max": shell.loop_residual_max,
        "ambiguous": shell.ambiguous,
    }


def _endpoint_shell_manifest_record(
    shell: EndpointShellManifest,
) -> dict[str, object]:
    return {
        **endpoint_shell_manifest_payload(shell),
        "shell_manifest_sha": shell.shell_manifest_sha,
    }


def shell_candidate_point_attempt_payload(
    attempt: ShellCandidatePointAttempt,
) -> dict[str, object]:
    _exact_record(
        attempt,
        ShellCandidatePointAttempt,
        "shell_candidate_point_attempt",
    )
    return {
        "reciprocal_index": list(attempt.reciprocal_index),
        "momentum_path_id": attempt.momentum_path_id,
        "momentum_path_position": attempt.momentum_path_position,
        "candidate_phases": list(attempt.candidate_phases),
        "candidate_ranks": list(attempt.candidate_ranks),
        "candidate_participations": list(attempt.candidate_participations),
        "candidate_reference_overlaps": list(attempt.candidate_reference_overlaps),
        "candidate_predecessor_overlaps": list(attempt.candidate_predecessor_overlaps),
    }


def endpoint_shell_attempt_audit_payload(
    audit: EndpointShellAttemptAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        EndpointShellAttemptAudit,
        "endpoint_shell_attempt",
    )
    return {
        "attempt_schema_version": audit.attempt_schema_version,
        "shell_spec": _endpoint_shell_spec_record(audit.shell_spec),
        "point_attempts": [
            shell_candidate_point_attempt_payload(item) for item in audit.point_attempts
        ],
        "projector_residual_max": audit.projector_residual_max,
        "loop_residual_max_observed": (audit.loop_residual_max_observed),
    }


def _endpoint_shell_attempt_record(
    audit: EndpointShellAttemptAudit,
) -> dict[str, object]:
    return {
        **endpoint_shell_attempt_audit_payload(audit),
        "attempt_sha": audit.attempt_sha,
    }


def endpoint_shell_outcome_payload(
    outcome: EndpointShellOutcome,
) -> dict[str, object]:
    _exact_record(
        outcome,
        EndpointShellOutcome,
        "endpoint_shell_outcome",
    )
    return {
        "status": _status_record(outcome.status),
        "failure": (None if outcome.failure is None else outcome.failure.value),
        "reference_outcome": _endpoint_reference_outcome_record(
            outcome.reference_outcome
        ),
        "attempt_audit": _endpoint_shell_attempt_record(outcome.attempt_audit),
        "shell": (
            None
            if outcome.shell is None
            else _endpoint_shell_manifest_record(outcome.shell)
        ),
    }


def _endpoint_shell_outcome_record(
    outcome: EndpointShellOutcome,
) -> dict[str, object]:
    return {
        **endpoint_shell_outcome_payload(outcome),
        "outcome_sha": outcome.outcome_sha,
    }


def _endpoint_shell_outcome_from_raw_v1(
    raw_body: object,
    live_reference_outcome: EndpointReferenceOutcome,
    live_shell_spec: EndpointShellSpec,
    expected_raw_reference: dict[str, object],
    expected_raw_shell_spec: dict[str, object],
) -> EndpointShellOutcome:
    core = _require_b7_replay_core_v1(_b7_replay_core_v1)
    checked = core.validate_endpoint_shell_outcome_raw_v1(raw_body)
    if core.canonical_json_bytes_v1(
        checked["reference_outcome"]
    ) != core.canonical_json_bytes_v1(expected_raw_reference):
        raise ValueError("raw shell leaf changed its reference binding")
    raw_attempt = checked["attempt_audit"]
    for embedded in (
        raw_attempt["shell_spec"],
        None if checked["shell"] is None else checked["shell"]["shell_spec"],
    ):
        if embedded is not None and core.canonical_json_bytes_v1(
            embedded
        ) != core.canonical_json_bytes_v1(expected_raw_shell_spec):
            raise ValueError("raw shell leaf changed its shell-spec binding")
    point_attempts = tuple(
        ShellCandidatePointAttempt(
            reciprocal_index=tuple(item["reciprocal_index"]),
            momentum_path_id=item["momentum_path_id"],
            momentum_path_position=item["momentum_path_position"],
            candidate_phases=tuple(item["candidate_phases"]),
            candidate_ranks=tuple(item["candidate_ranks"]),
            candidate_participations=tuple(item["candidate_participations"]),
            candidate_reference_overlaps=tuple(item["candidate_reference_overlaps"]),
            candidate_predecessor_overlaps=tuple(
                item["candidate_predecessor_overlaps"]
            ),
        )
        for item in raw_attempt["point_attempts"]
    )
    attempt = EndpointShellAttemptAudit(
        attempt_schema_version=raw_attempt["attempt_schema_version"],
        shell_spec=live_shell_spec,
        point_attempts=point_attempts,
        projector_residual_max=raw_attempt["projector_residual_max"],
        loop_residual_max_observed=raw_attempt["loop_residual_max_observed"],
        attempt_sha=raw_attempt["attempt_sha"],
    )
    if attempt.attempt_sha != canonical_sha(
        endpoint_shell_attempt_audit_payload(attempt)
    ):
        raise ValueError("raw shell leaf returned a noncanonical attempt SHA")
    raw_shell = checked["shell"]
    shell = None
    if raw_shell is not None:
        point_audits = tuple(
            ShellPointAudit(
                reciprocal_index=tuple(item["reciprocal_index"]),
                momentum_path_id=item["momentum_path_id"],
                momentum_path_position=item["momentum_path_position"],
                shell_phase=item["shell_phase"],
                rank=item["rank"],
                hermitian_residual=item["hermitian_residual"],
                idempotent_residual=item["idempotent_residual"],
                g_invariance_residual=item["g_invariance_residual"],
                eigenphase_residual=item["eigenphase_residual"],
                participation=item["participation"],
                nearest_competitor_gap=item["nearest_competitor_gap"],
                reference_overlap=item["reference_overlap"],
                runner_up_overlap=item["runner_up_overlap"],
                predecessor_overlap=item["predecessor_overlap"],
                loop_residual=item["loop_residual"],
            )
            for item in raw_shell["point_audits"]
        )
        shell = EndpointShellManifest(
            shell_schema_version=raw_shell["shell_schema_version"],
            actual_factory_sha=raw_shell["actual_factory_sha"],
            actual_transition_sha=raw_shell["actual_transition_sha"],
            actual_dynamics_certificate_sha=raw_shell[
                "actual_dynamics_certificate_sha"
            ],
            shell_spec=live_shell_spec,
            dt=raw_shell["dt"],
            eigenphase_convention_id=raw_shell["eigenphase_convention_id"],
            shell_phases=tuple(raw_shell["shell_phases"]),
            shell_projectors=_frozen_tensor_from_raw_v1(raw_shell["shell_projectors"]),
            point_audits=point_audits,
            hermitian_residual_max=raw_shell["hermitian_residual_max"],
            idempotent_residual_max=raw_shell["idempotent_residual_max"],
            g_invariance_residual_max=raw_shell["g_invariance_residual_max"],
            eigenphase_residual_max=raw_shell["eigenphase_residual_max"],
            participation_min=raw_shell["participation_min"],
            nearest_competitor_gap_min=raw_shell["nearest_competitor_gap_min"],
            reference_overlap_min=raw_shell["reference_overlap_min"],
            runner_up_overlap_max=raw_shell["runner_up_overlap_max"],
            predecessor_overlap_min=raw_shell["predecessor_overlap_min"],
            overlap_margin_min=raw_shell["overlap_margin_min"],
            loop_residual_max=raw_shell["loop_residual_max"],
            ambiguous=raw_shell["ambiguous"],
            shell_manifest_sha=raw_shell["shell_manifest_sha"],
        )
        if shell.shell_manifest_sha != canonical_sha(
            endpoint_shell_manifest_payload(shell)
        ):
            raise ValueError("raw shell leaf returned a noncanonical manifest SHA")
    raw_status = checked["status"]
    status = BlockStatus(
        raw_status["defined"],
        (
            None
            if raw_status["reason"] is None
            else UndefinedReason(raw_status["reason"])
        ),
    )
    failure = (
        None if checked["failure"] is None else EndpointShellFailure(checked["failure"])
    )
    outcome = EndpointShellOutcome(
        status=status,
        failure=failure,
        reference_outcome=live_reference_outcome,
        attempt_audit=attempt,
        shell=shell,
        outcome_sha=checked["outcome_sha"],
    )
    if outcome.outcome_sha != canonical_sha(endpoint_shell_outcome_payload(outcome)):
        raise ValueError("raw shell leaf returned a noncanonical outcome SHA")
    return outcome


def source_frame_coverage_payload(
    certificate: SourceFrameCoverageCertificate,
) -> dict[str, object]:
    _exact_record(
        certificate,
        SourceFrameCoverageCertificate,
        "source_frame_coverage",
    )
    return {
        "certificate_schema_version": (certificate.certificate_schema_version),
        "source_basis_sha": certificate.source_basis_sha,
        "trial_matrix": _tensor_record(certificate.trial_matrix),
        "frame_operator_lower": certificate.frame_operator_lower,
        "canonical_dual_residual_upper": (certificate.canonical_dual_residual_upper),
    }


def _exact_frobenius_upper(values: np.ndarray) -> float:
    if type(values) is not np.ndarray:
        raise TypeError("Frobenius input must be a NumPy ndarray")
    if values.dtype != np.dtype(np.complex128):
        raise TypeError("Frobenius input dtype must be complex128")
    total = Fraction(0, 1)
    for value in values.reshape(-1, order="C"):
        real = Fraction.from_float(float(value.real))
        imaginary = Fraction.from_float(float(value.imag))
        total += real * real + imaginary * imaginary
    return frobenius_sqrt_upper(total)


_ExactComplex = tuple[Fraction, Fraction]


def _exact_frame_matrix(trials: np.ndarray) -> tuple[tuple[_ExactComplex, ...], ...]:
    rows, columns = trials.shape
    result: list[tuple[_ExactComplex, ...]] = []
    for left in range(rows):
        row: list[_ExactComplex] = []
        for right in range(rows):
            real = Fraction(0, 1)
            imaginary = Fraction(0, 1)
            for column in range(columns):
                first = trials[left, column]
                second = trials[right, column]
                ar = Fraction.from_float(float(first.real))
                ai = Fraction.from_float(float(first.imag))
                br = Fraction.from_float(float(second.real))
                bi = Fraction.from_float(float(second.imag))
                real += ar * br + ai * bi
                imaginary += ai * br - ar * bi
            row.append((real, imaginary))
        result.append(tuple(row))
    return tuple(result)


def _exact_complex_mul_conjugate(
    left: _ExactComplex,
    right: _ExactComplex,
) -> _ExactComplex:
    ar, ai = left
    br, bi = right
    return (ar * br + ai * bi, ai * br - ar * bi)


def _exact_gram_minus_scalar_is_positive_definite(
    gram: tuple[tuple[_ExactComplex, ...], ...],
    scalar: Fraction,
) -> bool:
    """Exact rational unpivoted LDL proof for ``gram - scalar I > 0``."""

    size = len(gram)
    lower: list[list[_ExactComplex]] = [
        [(Fraction(0, 1), Fraction(0, 1)) for _ in range(size)] for _ in range(size)
    ]
    diagonal: list[Fraction] = []
    for pivot_index in range(size):
        pivot_real, pivot_imag = gram[pivot_index][pivot_index]
        if pivot_imag != 0:
            raise ValueError("exact source frame diagonal is not real")
        pivot = pivot_real - scalar
        for column in range(pivot_index):
            lr, li = lower[pivot_index][column]
            pivot -= (lr * lr + li * li) * diagonal[column]
        if pivot <= 0:
            return False
        diagonal.append(pivot)
        lower[pivot_index][pivot_index] = (Fraction(1, 1), Fraction(0, 1))
        for row in range(pivot_index + 1, size):
            residual_real, residual_imag = gram[row][pivot_index]
            for column in range(pivot_index):
                product_real, product_imag = _exact_complex_mul_conjugate(
                    lower[row][column],
                    lower[pivot_index][column],
                )
                residual_real -= product_real * diagonal[column]
                residual_imag -= product_imag * diagonal[column]
            lower[row][pivot_index] = (
                residual_real / pivot,
                residual_imag / pivot,
            )
    return True


def _directed_source_frame_lower(
    trials: np.ndarray,
    approximate_minimum: float,
) -> float:
    """Produce a proved binary64 lower bound for ``lambda_min(FF*)``.

    A candidate is accepted only after an exact-rational LDL proof.  The
    numerical eigensolver merely proposes a starting point and therefore
    cannot make the bound inward.
    """

    gram = _exact_frame_matrix(trials)
    if not _exact_gram_minus_scalar_is_positive_definite(
        gram,
        Fraction(0, 1),
    ):
        raise ValueError("source frame is not full rank")
    off_diagonal_zero = all(
        gram[row][column] == (Fraction(0, 1), Fraction(0, 1))
        for row in range(len(gram))
        for column in range(len(gram))
        if row != column
    )
    if off_diagonal_zero:
        exact_minimum = min(gram[index][index][0] for index in range(len(gram)))
        candidate = float(exact_minimum)
        while Fraction.from_float(candidate) > exact_minimum:
            candidate = math.nextafter(candidate, -math.inf)
        if candidate <= 0.0 or not math.isfinite(candidate):
            raise ValueError("directed frame lower is not positive")
        return candidate

    if not math.isfinite(approximate_minimum):
        raise ValueError("source frame eigenvalue estimate is not finite")
    exact_diagonal_minimum = min(gram[index][index][0] for index in range(len(gram)))
    proposal = min(
        max(0.0, approximate_minimum),
        float(exact_diagonal_minimum),
    )
    candidate = proposal * 0.5
    for _ in range(2_048):
        if (
            candidate > 0.0
            and math.isfinite(candidate)
            and _exact_gram_minus_scalar_is_positive_definite(
                gram,
                Fraction.from_float(candidate),
            )
        ):
            return candidate
        candidate *= 0.5
    raise ValueError("no positive fp64 source-frame lower could be certified")


def _preflight_source_frame_inputs(
    source_basis: BasisManifest,
    trial_matrix: FrozenComplexTensor,
) -> tuple[int, int]:
    """Bound and validate the full source-frame wire before hashing/decoding."""

    _exact_record(source_basis, BasisManifest, "source_basis")
    _exact_record(trial_matrix, FrozenComplexTensor, "trial_matrix")
    if type(source_basis.channel_order) is not tuple:
        raise TypeError("source_basis.channel_order must be a tuple")
    if type(source_basis.vectors_wire) is not tuple:
        raise TypeError("source_basis.vectors_wire must be a tuple")
    source_count = len(source_basis.vectors_wire)
    channel_count = len(source_basis.channel_order)
    if source_count <= 0 or channel_count <= 0:
        raise ValueError("source basis dimensions must be positive")
    basis_entries = source_count * channel_count
    if (
        basis_entries > _SOURCE_FRAME_ENTRY_CAP
        or basis_entries * 16 > _GENERAL_BODY_CAP
    ):
        raise ValueError("source basis exceeds source-frame body cap")

    if type(trial_matrix.shape) is not tuple or len(trial_matrix.shape) != 2:
        raise ValueError("trial matrix must declare exactly two dimensions")
    rows = _positive_int(trial_matrix.shape[0], "trial_matrix.shape[0]")
    columns = _positive_int(trial_matrix.shape[1], "trial_matrix.shape[1]")
    if rows != source_count:
        raise ValueError("trial matrix source dimension mismatch")
    if columns < source_count:
        raise ValueError("source frame has fewer trials than source dimension")
    entries = rows * columns
    if entries > _SOURCE_FRAME_ENTRY_CAP or entries * 16 > _GENERAL_BODY_CAP:
        raise ValueError("trial matrix exceeds source-frame body cap")
    if type(trial_matrix.values_wire) is not tuple:
        raise TypeError("trial_matrix.values_wire must be a tuple")
    if len(trial_matrix.values_wire) != entries:
        raise ValueError("trial matrix wire length mismatch")
    frame_work = source_count * source_count * columns
    if frame_work > _SOURCE_FRAME_WORK_CAP:
        raise ValueError("source-frame exact work exceeds cap")
    for row_index, row in enumerate(source_basis.vectors_wire):
        if type(row) is not tuple:
            raise TypeError(f"source_basis.vectors_wire[{row_index}] must be a tuple")
        if len(row) != channel_count:
            raise ValueError("source basis vector width mismatch")
    BasisManifest.__post_init__(source_basis)
    FrozenComplexTensor.__post_init__(trial_matrix)
    return source_count, columns


def _expected_source_frame_coverage(
    source_basis: BasisManifest,
    trial_matrix: FrozenComplexTensor,
) -> SourceFrameCoverageCertificate:
    _preflight_source_frame_inputs(source_basis, trial_matrix)
    basis = verify_basis_manifest(source_basis)
    tensor = verify_frozen_tensor(trial_matrix)
    source_count = len(basis.vectors_wire)
    trials = frozen_tensor_array(tensor)
    if trials.ndim != 2 or trials.shape[0] != source_count:
        raise ValueError("trial matrix must have shape (n_source,n_trial)")
    if trials.shape[1] < source_count:
        raise ValueError("source frame has fewer trials than source dimension")
    frame = trials @ trials.conj().T
    eigenvalues = np.linalg.eigvalsh(frame)
    if not np.isfinite(eigenvalues).all() or float(eigenvalues[0]) <= 0.0:
        raise ValueError("source frame is not full rank")
    frame_lower = _directed_source_frame_lower(
        trials,
        float(eigenvalues[0]),
    )
    if not math.isfinite(frame_lower) or frame_lower <= 0.0:
        raise ValueError("directed frame lower is not positive")
    dual = trials.conj().T @ np.linalg.inv(frame)
    dual_residual = _exact_frobenius_upper(
        np.asarray(
            trials @ dual - np.eye(source_count, dtype=np.complex128),
            dtype=np.complex128,
        )
    )
    provisional = SourceFrameCoverageCertificate(
        certificate_schema_version=SOURCE_FRAME_COVERAGE_SCHEMA_VERSION,
        source_basis_sha=basis.manifest_id,
        trial_matrix=tensor,
        frame_operator_lower=frame_lower,
        canonical_dual_residual_upper=dual_residual,
        certificate_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        certificate_sha=canonical_sha(source_frame_coverage_payload(provisional)),
    )


def build_source_frame_coverage_certificate(
    source_basis: BasisManifest,
    trial_matrix: FrozenComplexTensor,
) -> SourceFrameCoverageCertificate:
    """Certify a non-identity full source frame without granting authority."""

    return _expected_source_frame_coverage(source_basis, trial_matrix)


def verify_source_frame_coverage_certificate(
    certificate: SourceFrameCoverageCertificate,
    source_basis: BasisManifest,
    trial_matrix: FrozenComplexTensor,
) -> SourceFrameCoverageCertificate:
    """Replay the frame lower and canonical-dual reconstruction."""

    _exact_record(
        certificate,
        SourceFrameCoverageCertificate,
        "source_frame_coverage",
    )
    _preflight_source_frame_inputs(source_basis, trial_matrix)
    _preflight_source_frame_inputs(
        source_basis,
        certificate.trial_matrix,
    )
    SourceFrameCoverageCertificate.__post_init__(certificate)
    if certificate.certificate_schema_version != SOURCE_FRAME_COVERAGE_SCHEMA_VERSION:
        raise ValueError("unexpected source frame coverage schema")
    if certificate.certificate_sha != canonical_sha(
        source_frame_coverage_payload(certificate)
    ):
        raise ValueError("source frame certificate SHA mismatch")
    expected = _expected_source_frame_coverage(
        source_basis,
        trial_matrix,
    )
    if certificate != expected:
        raise ValueError("source frame certificate differs from replay")
    return certificate


def _build_source_readout_bridge_audit_from_differences(
    *,
    branch: Literal["actual", "matched_ablated"],
    factory_sha: str,
    transition_sha: str,
    dynamics_certificate_sha: str,
    run_spec: ResponseRunSpec,
    registry_entry: ControlRegistryEntry,
    differences: tuple[
        tuple[tuple[int, ...], int, np.ndarray],
        ...,
    ],
) -> SourceReadoutBridgeAudit:
    """Freeze dimensional bridge matrices after executor replay."""

    if branch not in ("actual", "matched_ablated"):
        raise ValueError("branch is not closed")
    _sha(factory_sha, "factory_sha")
    _sha(transition_sha, "transition_sha")
    _sha(dynamics_certificate_sha, "dynamics_certificate_sha")
    _exact_record(run_spec, ResponseRunSpec, "run_spec")
    matrix_count, readout_count, source_count = _preflight_bridge_output_body(run_spec)
    _exact_registry_entry_tree(registry_entry)
    if run_spec.control_registry_entry_sha != registry_entry.entry_sha:
        raise ValueError("bridge registry entry binding mismatch")
    if type(differences) is not tuple:
        raise TypeError("differences must be a tuple")
    expected_keys = tuple(
        (reciprocal_index, steps)
        for reciprocal_index in (run_spec.source_readout_bridge_grid.reciprocal_indices)
        for steps in run_spec.source_readout_bridge_steps
    )
    if len(expected_keys) != matrix_count or len(differences) != matrix_count:
        raise ValueError("bridge differences do not cover grid × steps")
    for expected_key, item in zip(expected_keys, differences):
        if type(item) is not tuple or len(item) != 3:
            raise TypeError("bridge differences entries must be triples")
        reciprocal_index, steps, raw = item
        if (reciprocal_index, steps) != expected_key:
            raise ValueError("bridge differences are missing or reordered")
        if type(raw) is not np.ndarray:
            raise TypeError("raw_difference_matrix must be a NumPy ndarray")
        if raw.dtype != np.dtype(np.complex128):
            raise TypeError("raw_difference_matrix dtype must be complex128")
        if raw.ndim != 2 or raw.shape != (readout_count, source_count):
            raise ValueError("raw difference matrix shape mismatch")
    raw_entry = _registry_entry_record(registry_entry)
    raw_audit = _audit_source_readout_bridge_from_raw(
        branch,
        factory_sha,
        transition_sha,
        dynamics_certificate_sha,
        run_spec.spec_sha,
        _bridge_grid_record(run_spec.source_readout_bridge_grid),
        list(run_spec.source_readout_bridge_steps),
        _tensor_record(run_spec.source_trial_vectors),
        raw_entry["readout_calibration_spec"],
        differences,
    )
    return _source_readout_bridge_audit_from_raw_v1(raw_audit)


def _preflight_source_readout_bridge_audit_body(
    audit: SourceReadoutBridgeAudit,
    run_spec: ResponseRunSpec,
    registry_entry: ControlRegistryEntry,
) -> None:
    _exact_record(
        audit,
        SourceReadoutBridgeAudit,
        "source_readout_bridge_audit",
    )
    matrix_count, readout_count, source_count = _preflight_bridge_output_body(run_spec)
    _exact_registry_entry_tree(registry_entry)
    if len(audit.matrix_audits) != matrix_count:
        raise ValueError("bridge audit does not cover exact grid × steps")
    expected_keys = tuple(
        (reciprocal_index, steps)
        for reciprocal_index in (run_spec.source_readout_bridge_grid.reciprocal_indices)
        for steps in run_spec.source_readout_bridge_steps
    )
    for index, (expected_key, item) in enumerate(
        zip(expected_keys, audit.matrix_audits)
    ):
        _exact_record(
            item,
            SourceReadoutBridgeMatrixAudit,
            f"source_readout_bridge_audit.matrix_audits[{index}]",
        )
        if (item.reciprocal_index, item.macro_steps) != expected_key:
            raise ValueError("bridge matrix audits are missing or reordered")
        _preflight_frozen_tensor_body(
            item.raw_difference_matrix,
            expected_shape=(readout_count, source_count),
            field=(
                "source_readout_bridge_audit."
                f"matrix_audits[{index}].raw_difference_matrix"
            ),
        )
        if item.frame_coverage is not None:
            _exact_record(
                item.frame_coverage,
                SourceFrameCoverageCertificate,
                (f"source_readout_bridge_audit.matrix_audits[{index}].frame_coverage"),
            )
            _exact_dataclass_tree(
                item.frame_coverage,
                (f"source_readout_bridge_audit.matrix_audits[{index}].frame_coverage"),
            )
    _exact_dataclass_tree(audit, "source_readout_bridge_audit")


def verify_source_readout_bridge_audit_body(
    audit: SourceReadoutBridgeAudit,
    run_spec: ResponseRunSpec,
    registry_entry: ControlRegistryEntry,
) -> SourceReadoutBridgeAudit:
    """Replay bounds/hashes over already measured dimensional matrices."""

    _preflight_source_readout_bridge_audit_body(
        audit,
        run_spec,
        registry_entry,
    )
    if audit.bridge_schema_version != SOURCE_READOUT_BRIDGE_SCHEMA_VERSION:
        raise ValueError("unexpected source/readout bridge schema")
    if audit.bridge_sha != canonical_sha(source_readout_bridge_audit_payload(audit)):
        raise ValueError("source/readout bridge SHA mismatch")
    differences = tuple(
        (
            item.reciprocal_index,
            item.macro_steps,
            frozen_tensor_array(item.raw_difference_matrix),
        )
        for item in audit.matrix_audits
    )
    expected = _build_source_readout_bridge_audit_from_differences(
        branch=audit.branch,
        factory_sha=audit.factory_sha,
        transition_sha=audit.transition_sha,
        dynamics_certificate_sha=audit.dynamics_certificate_sha,
        run_spec=run_spec,
        registry_entry=registry_entry,
        differences=differences,
    )
    if audit != expected:
        raise ValueError("source/readout bridge body differs from replay")
    return audit


def _build_source_readout_response_from_values(
    *,
    branch: Literal["actual", "matched_ablated"],
    factory_sha: str,
    transition_sha: str,
    dynamics_certificate_sha: str,
    run_spec: ResponseRunSpec,
    shell_manifest_sha: str,
    bridge_audit: SourceReadoutBridgeAudit,
    values: FrozenComplexTensor,
) -> SourceReadoutResponse:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("branch is not closed")
    for field, value in (
        ("factory_sha", factory_sha),
        ("transition_sha", transition_sha),
        ("dynamics_certificate_sha", dynamics_certificate_sha),
        ("shell_manifest_sha", shell_manifest_sha),
    ):
        _sha(value, field)
    _exact_record(run_spec, ResponseRunSpec, "run_spec")
    _exact_record(
        bridge_audit,
        SourceReadoutBridgeAudit,
        "bridge_audit",
    )
    expected_shape = _preflight_response_values_body(run_spec, values)
    tensor = verify_frozen_tensor(values)
    if tensor.shape != expected_shape:
        raise ValueError("source/readout response values shape mismatch")
    if (
        bridge_audit.branch != branch
        or bridge_audit.factory_sha != factory_sha
        or bridge_audit.transition_sha != transition_sha
        or bridge_audit.dynamics_certificate_sha != dynamics_certificate_sha
        or bridge_audit.run_spec_sha != run_spec.spec_sha
    ):
        raise ValueError("response bridge binding mismatch")
    provisional = SourceReadoutResponse(
        response_schema_version=SOURCE_READOUT_RESPONSE_SCHEMA_VERSION,
        branch=branch,
        factory_sha=factory_sha,
        transition_sha=transition_sha,
        dynamics_certificate_sha=dynamics_certificate_sha,
        source_basis=run_spec.source_basis,
        readout_basis=run_spec.readout_basis,
        run_spec_sha=run_spec.spec_sha,
        shell_manifest_sha=shell_manifest_sha,
        bridge_audit=bridge_audit,
        values=tensor,
        response_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        response_sha=canonical_sha(source_readout_response_payload(provisional)),
    )


def _source_frame_coverage_record(
    certificate: SourceFrameCoverageCertificate,
) -> dict[str, object]:
    return {
        **source_frame_coverage_payload(certificate),
        "certificate_sha": certificate.certificate_sha,
    }


def source_readout_bridge_matrix_audit_payload(
    audit: SourceReadoutBridgeMatrixAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        SourceReadoutBridgeMatrixAudit,
        "source_readout_bridge_matrix_audit",
    )
    return {
        "reciprocal_index": list(audit.reciprocal_index),
        "macro_steps": audit.macro_steps,
        "raw_difference_matrix": _tensor_record(audit.raw_difference_matrix),
        "frame_coverage": (
            None
            if audit.frame_coverage is None
            else _source_frame_coverage_record(audit.frame_coverage)
        ),
        "raw_frobenius_upper": audit.raw_frobenius_upper,
        "raw_operator_norm_upper": audit.raw_operator_norm_upper,
        "h_whitened_operator_error_upper": (audit.h_whitened_operator_error_upper),
        "curv_whitened_operator_error_upper": (
            audit.curv_whitened_operator_error_upper
        ),
    }


def source_readout_bridge_audit_payload(
    audit: SourceReadoutBridgeAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        SourceReadoutBridgeAudit,
        "source_readout_bridge_audit",
    )
    return {
        "bridge_schema_version": audit.bridge_schema_version,
        "branch": audit.branch,
        "factory_sha": audit.factory_sha,
        "transition_sha": audit.transition_sha,
        "dynamics_certificate_sha": audit.dynamics_certificate_sha,
        "run_spec_sha": audit.run_spec_sha,
        "source_metric_whitener_sha": (audit.source_metric_whitener_sha),
        "readout_calibration_spec_sha": (audit.readout_calibration_spec_sha),
        "matrix_audits": [
            source_readout_bridge_matrix_audit_payload(item)
            for item in audit.matrix_audits
        ],
        "h_operator_error_max": audit.h_operator_error_max,
        "curv_operator_error_max": audit.curv_operator_error_max,
    }


def _source_readout_bridge_audit_record(
    audit: SourceReadoutBridgeAudit,
) -> dict[str, object]:
    return {
        **source_readout_bridge_audit_payload(audit),
        "bridge_sha": audit.bridge_sha,
    }


def _source_readout_bridge_audit_from_raw_v1(
    raw_body: object,
) -> SourceReadoutBridgeAudit:
    core = _require_b7_replay_core_v1(_b7_replay_core_v1)
    checked = core._validate_record_raw_v1(
        raw_body,
        "SourceReadoutBridgeAudit",
        "source_readout_bridge_audit",
        core._record_schemas_v1(),
    )
    matrix_audits: list[SourceReadoutBridgeMatrixAudit] = []
    for item in checked["matrix_audits"]:
        if item["frame_coverage"] is not None:
            raise ValueError("raw bridge leaf returned unexpected frame coverage")
        matrix_audits.append(
            SourceReadoutBridgeMatrixAudit(
                reciprocal_index=tuple(item["reciprocal_index"]),
                macro_steps=item["macro_steps"],
                raw_difference_matrix=_frozen_tensor_from_raw_v1(
                    item["raw_difference_matrix"]
                ),
                frame_coverage=None,
                raw_frobenius_upper=item["raw_frobenius_upper"],
                raw_operator_norm_upper=item["raw_operator_norm_upper"],
                h_whitened_operator_error_upper=(
                    item["h_whitened_operator_error_upper"]
                ),
                curv_whitened_operator_error_upper=(
                    item["curv_whitened_operator_error_upper"]
                ),
            )
        )
    audit = SourceReadoutBridgeAudit(
        bridge_schema_version=checked["bridge_schema_version"],
        branch=checked["branch"],
        factory_sha=checked["factory_sha"],
        transition_sha=checked["transition_sha"],
        dynamics_certificate_sha=checked["dynamics_certificate_sha"],
        run_spec_sha=checked["run_spec_sha"],
        source_metric_whitener_sha=checked["source_metric_whitener_sha"],
        readout_calibration_spec_sha=checked["readout_calibration_spec_sha"],
        matrix_audits=tuple(matrix_audits),
        h_operator_error_max=checked["h_operator_error_max"],
        curv_operator_error_max=checked["curv_operator_error_max"],
        bridge_sha=checked["bridge_sha"],
    )
    if audit.bridge_sha != canonical_sha(source_readout_bridge_audit_payload(audit)):
        raise ValueError("raw bridge leaf returned a noncanonical audit SHA")
    return audit


def source_readout_response_payload(
    response: SourceReadoutResponse,
) -> dict[str, object]:
    _exact_record(
        response,
        SourceReadoutResponse,
        "source_readout_response",
    )
    return {
        "response_schema_version": response.response_schema_version,
        "branch": response.branch,
        "factory_sha": response.factory_sha,
        "transition_sha": response.transition_sha,
        "dynamics_certificate_sha": (response.dynamics_certificate_sha),
        "source_basis": _basis_record(response.source_basis),
        "readout_basis": _basis_record(response.readout_basis),
        "run_spec_sha": response.run_spec_sha,
        "shell_manifest_sha": response.shell_manifest_sha,
        "bridge_audit": _source_readout_bridge_audit_record(response.bridge_audit),
        "values": _tensor_record(response.values),
    }


def _source_readout_response_record(
    response: SourceReadoutResponse,
) -> dict[str, object]:
    return {
        **source_readout_response_payload(response),
        "response_sha": response.response_sha,
    }


def paired_filtered_response_payload(
    response: PairedFilteredResponse,
) -> dict[str, object]:
    _exact_record(
        response,
        PairedFilteredResponse,
        "paired_filtered_response",
    )
    return {
        "pair_schema_version": response.pair_schema_version,
        "ablation_manifest_sha": response.ablation_manifest_sha,
        "qualification_sha": response.qualification_sha,
        "actual_dynamics_certificate": _certificate_record(
            response.actual_dynamics_certificate
        ),
        "ablated_dynamics_certificate": _certificate_record(
            response.ablated_dynamics_certificate
        ),
        "actual": _source_readout_response_record(response.actual),
        "ablated": _source_readout_response_record(response.ablated),
        "run_spec": _response_run_spec_record(response.run_spec),
        "shell_manifest": _endpoint_shell_manifest_record(response.shell_manifest),
    }


def source_readout_branch_attempt_audit_payload(
    audit: SourceReadoutBranchAttemptAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        SourceReadoutBranchAttemptAudit,
        "source_readout_branch_attempt",
    )
    return {
        "branch": audit.branch,
        "response_values": (
            None
            if audit.response_values is None
            else _tensor_record(audit.response_values)
        ),
        "bridge_audit": (
            None
            if audit.bridge_audit is None
            else _source_readout_bridge_audit_record(audit.bridge_audit)
        ),
        "failure": (None if audit.failure is None else audit.failure.value),
    }


def _source_readout_branch_attempt_record(
    audit: SourceReadoutBranchAttemptAudit,
) -> dict[str, object]:
    return {
        **source_readout_branch_attempt_audit_payload(audit),
        "attempt_sha": audit.attempt_sha,
    }


def paired_response_attempt_audit_payload(
    audit: PairedResponseAttemptAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        PairedResponseAttemptAudit,
        "paired_response_attempt",
    )
    return {
        "attempt_schema_version": audit.attempt_schema_version,
        "window_protocol": _window_protocol_record(audit.window_protocol),
        "qualification_sha": audit.qualification_sha,
        "actual_factory_sha": audit.actual_factory_sha,
        "ablated_factory_sha": audit.ablated_factory_sha,
        "actual_transition": _transition_record(audit.actual_transition),
        "ablated_transition": _transition_record(audit.ablated_transition),
        "actual_dynamics_certificate": _certificate_record(
            audit.actual_dynamics_certificate
        ),
        "ablated_dynamics_certificate": _certificate_record(
            audit.ablated_dynamics_certificate
        ),
        "run_spec": _response_run_spec_record(audit.run_spec),
        "shell_outcome": _endpoint_shell_outcome_record(audit.shell_outcome),
        "actual_branch_attempt": (
            None
            if audit.actual_branch_attempt is None
            else _source_readout_branch_attempt_record(audit.actual_branch_attempt)
        ),
        "ablated_branch_attempt": (
            None
            if audit.ablated_branch_attempt is None
            else _source_readout_branch_attempt_record(audit.ablated_branch_attempt)
        ),
        "first_failure": (
            None if audit.first_failure is None else audit.first_failure.value
        ),
    }


def _paired_response_attempt_record(
    audit: PairedResponseAttemptAudit,
) -> dict[str, object]:
    return {
        **paired_response_attempt_audit_payload(audit),
        "attempt_sha": audit.attempt_sha,
    }


def paired_response_outcome_payload(
    outcome: PairedResponseOutcome,
) -> dict[str, object]:
    _exact_record(
        outcome,
        PairedResponseOutcome,
        "paired_response_outcome",
    )
    return {
        "status": _status_record(outcome.status),
        "failure": (None if outcome.failure is None else outcome.failure.value),
        "attempt_audit": _paired_response_attempt_record(outcome.attempt_audit),
        "paired_response": (
            None
            if outcome.paired_response is None
            else {
                **paired_filtered_response_payload(outcome.paired_response),
                "pair_sha": outcome.paired_response.pair_sha,
            }
        ),
    }


def _source_readout_branch_attempt(
    *,
    branch: Literal["actual", "matched_ablated"],
    response_values: Optional[FrozenComplexTensor],
    bridge_audit: Optional[SourceReadoutBridgeAudit],
    failure: Optional[PairedResponseFailure],
) -> SourceReadoutBranchAttemptAudit:
    provisional = SourceReadoutBranchAttemptAudit(
        branch=branch,
        response_values=response_values,
        bridge_audit=bridge_audit,
        failure=failure,
        attempt_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        attempt_sha=canonical_sha(
            source_readout_branch_attempt_audit_payload(provisional)
        ),
    )


def _legacy_branch_attempt_from_neutral_raw_v1(
    raw_body: object,
) -> SourceReadoutBranchAttemptAudit:
    core = _require_b7_replay_core_v1(_b7_replay_core_v1)
    checked = core.validate_branch_attempt_v1(raw_body)
    failure_map = {
        "actual_response_failed": PairedResponseFailure.ACTUAL_RESPONSE_FAILED,
        "matched_ablated_response_failed": (
            PairedResponseFailure.ABLATED_RESPONSE_FAILED
        ),
        "actual_bridge_failed": PairedResponseFailure.ACTUAL_BRIDGE_FAILED,
        "matched_ablated_bridge_failed": (PairedResponseFailure.ABLATED_BRIDGE_FAILED),
    }
    raw_failure = checked["failure"]
    failure = None if raw_failure is None else failure_map[raw_failure]
    return _source_readout_branch_attempt(
        branch=checked["branch"],
        response_values=(
            None
            if checked["response_values"] is None
            else _frozen_tensor_from_raw_v1(checked["response_values"])
        ),
        bridge_audit=(
            None
            if checked["bridge_audit"] is None
            else _source_readout_bridge_audit_from_raw_v1(checked["bridge_audit"])
        ),
        failure=failure,
    )


def _legacy_atomic_assembly_from_raw_prefix_v1(
    actual_response_values: object,
    matched_ablated_response_values: object,
    actual_bridge_audit: object,
    matched_ablated_bridge_audit: object,
    first_failure: Optional[str],
) -> tuple[
    SourceReadoutBranchAttemptAudit,
    Optional[SourceReadoutBranchAttemptAudit],
    Optional[PairedResponseFailure],
]:
    actual_raw, matched_raw, observed_failure = (
        _assemble_atomic_paired_response_attempt_from_raw(
            actual_response_values,
            matched_ablated_response_values,
            actual_bridge_audit,
            matched_ablated_bridge_audit,
            first_failure,
        )
    )
    failure_map = {
        "actual_response_failed": PairedResponseFailure.ACTUAL_RESPONSE_FAILED,
        "matched_ablated_response_failed": (
            PairedResponseFailure.ABLATED_RESPONSE_FAILED
        ),
        "actual_bridge_failed": PairedResponseFailure.ACTUAL_BRIDGE_FAILED,
        "matched_ablated_bridge_failed": (PairedResponseFailure.ABLATED_BRIDGE_FAILED),
    }
    return (
        _legacy_branch_attempt_from_neutral_raw_v1(actual_raw),
        (
            None
            if matched_raw is None
            else _legacy_branch_attempt_from_neutral_raw_v1(matched_raw)
        ),
        (None if observed_failure is None else failure_map[observed_failure]),
    )


def _run_atomic_paired_branch_attempts(
    *,
    actual_values_call: Callable[[], FrozenComplexTensor],
    actual_bridge_call: Callable[[], SourceReadoutBridgeAudit],
    ablated_values_call: Callable[[], FrozenComplexTensor],
    ablated_bridge_call: Callable[[], SourceReadoutBridgeAudit],
) -> tuple[
    SourceReadoutBranchAttemptAudit,
    Optional[SourceReadoutBranchAttemptAudit],
    Optional[PairedResponseFailure],
]:
    """Construct both responses before entering either executor bridge."""

    stage_errors = (TypeError, ValueError, RuntimeError, ArithmeticError)
    try:
        actual_values = actual_values_call()
        _exact_record(
            actual_values,
            FrozenComplexTensor,
            "actual_response_values",
        )
        actual_values_raw = _tensor_record(actual_values)
    except stage_errors:
        return _legacy_atomic_assembly_from_raw_prefix_v1(
            None,
            None,
            None,
            None,
            "actual_response_failed",
        )
    try:
        ablated_values = ablated_values_call()
        _exact_record(
            ablated_values,
            FrozenComplexTensor,
            "ablated_response_values",
        )
        ablated_values_raw = _tensor_record(ablated_values)
    except stage_errors:
        return _legacy_atomic_assembly_from_raw_prefix_v1(
            actual_values_raw,
            None,
            None,
            None,
            "matched_ablated_response_failed",
        )
    try:
        actual_bridge = actual_bridge_call()
        _exact_record(
            actual_bridge,
            SourceReadoutBridgeAudit,
            "actual_bridge_audit",
        )
        if actual_bridge.branch != "actual":
            raise ValueError("actual bridge has the wrong branch")
        actual_bridge_raw = _source_readout_bridge_audit_record(actual_bridge)
    except stage_errors:
        return _legacy_atomic_assembly_from_raw_prefix_v1(
            actual_values_raw,
            ablated_values_raw,
            None,
            None,
            "actual_bridge_failed",
        )
    try:
        ablated_bridge = ablated_bridge_call()
        _exact_record(
            ablated_bridge,
            SourceReadoutBridgeAudit,
            "ablated_bridge_audit",
        )
        if ablated_bridge.branch != "matched_ablated":
            raise ValueError("ablated bridge has the wrong branch")
        ablated_bridge_raw = _source_readout_bridge_audit_record(ablated_bridge)
    except stage_errors:
        return _legacy_atomic_assembly_from_raw_prefix_v1(
            actual_values_raw,
            ablated_values_raw,
            actual_bridge_raw,
            None,
            "matched_ablated_bridge_failed",
        )
    return _legacy_atomic_assembly_from_raw_prefix_v1(
        actual_values_raw,
        ablated_values_raw,
        actual_bridge_raw,
        ablated_bridge_raw,
        None,
    )


def _protocol_entry_for_spec(
    spec: ResponseRunSpec,
    protocol_view: object,
) -> tuple[ControlWindowProtocolEntry, ControlRegistryEntry]:
    protocol = protocol_view.protocol
    matches = tuple(
        entry
        for entry in protocol.control_entries
        if entry.control_registry_entry_sha == spec.control_registry_entry_sha
    )
    if len(matches) != 1:
        raise ValueError("run spec registry entry binding is not unique")
    registry_matches = tuple(
        entry
        for entry in protocol_view.registry.registry.entries
        if entry.entry_sha == spec.control_registry_entry_sha
    )
    if len(registry_matches) != 1:
        raise ValueError("live registry entry binding is not unique")
    return matches[0], registry_matches[0]


def _preflight_run_spec(spec: ResponseRunSpec) -> None:
    _exact_record(spec, ResponseRunSpec, "spec")
    _exact_record(spec.source_basis, BasisManifest, "spec.source_basis")
    _exact_record(spec.readout_basis, BasisManifest, "spec.readout_basis")
    _exact_response_grid_tree(spec.response_grid, "spec.response_grid")
    _exact_bridge_grid_tree(
        spec.source_readout_bridge_grid,
        "spec.source_readout_bridge_grid",
    )
    _exact_record(
        spec.source_trial_vectors,
        FrozenComplexTensor,
        "spec.source_trial_vectors",
    )
    if len(spec.response_grid.reciprocal_indices) > 262_144:
        raise ValueError("response grid exceeds point cap")
    if len(spec.source_readout_bridge_grid.reciprocal_indices) > 64:
        raise ValueError("source/readout bridge grid exceeds point cap")
    source_count = len(spec.source_basis.vectors_wire)
    if source_count <= 0:
        raise ValueError("source basis is empty")
    if source_count * source_count > 16_777_216:
        raise ValueError("source trial tensor exceeds entry cap")
    expected_trial_shape = (source_count, source_count)
    if spec.source_trial_vectors.shape != expected_trial_shape:
        raise ValueError("source trial tensor shape mismatch")
    if len(spec.source_trial_vectors.values_wire) != source_count * source_count:
        raise ValueError("source trial tensor body length mismatch")
    work = (
        len(spec.source_readout_bridge_grid.reciprocal_indices)
        * source_count
        * max(spec.source_readout_bridge_steps)
    )
    if work > _SOURCE_BRIDGE_WORK_CAP:
        raise ValueError("source bridge work exceeds the frozen cap")
    estimated_bytes = (
        len(spec.source_trial_vectors.values_wire) * 16
        + len(spec.response_grid.reciprocal_indices) * 32
        + len(spec.source_readout_bridge_grid.reciprocal_indices) * 32
    )
    if estimated_bytes > _GENERAL_BODY_CAP:
        raise ValueError("run spec exceeds general evidence body cap")
    _exact_dataclass_tree(spec, "spec")


def _preflight_frozen_tensor_body(
    tensor: FrozenComplexTensor,
    *,
    expected_shape: tuple[int, ...],
    field: str,
    entry_cap: int = 16_777_216,
) -> int:
    _exact_record(tensor, FrozenComplexTensor, field)
    shape = _int_tuple(tensor.shape, f"{field}.shape", positive=True)
    if shape != expected_shape:
        raise ValueError(f"{field} shape mismatch")
    entries = math.prod(shape)
    if entries > entry_cap:
        raise ValueError(f"{field} exceeds tensor entry cap")
    if len(tensor.values_wire) != entries:
        raise ValueError(f"{field} wire length mismatch")
    if entries * 16 > _GENERAL_BODY_CAP:
        raise ValueError(f"{field} exceeds general body cap")
    _exact_dataclass_tree(tensor, field)
    return entries


def _preflight_bridge_output_body(
    run_spec: ResponseRunSpec,
) -> tuple[int, int, int]:
    _preflight_run_spec(run_spec)
    source_count = len(run_spec.source_basis.vectors_wire)
    readout_count = len(run_spec.readout_basis.vectors_wire)
    matrix_count = len(run_spec.source_readout_bridge_grid.reciprocal_indices) * len(
        run_spec.source_readout_bridge_steps
    )
    entries = matrix_count * source_count * readout_count
    if entries > 16_777_216:
        raise ValueError("bridge matrix evidence exceeds entry cap")
    if entries * 16 > _GENERAL_BODY_CAP:
        raise ValueError("bridge matrix evidence exceeds body cap")
    preflight_source_bridge_work(
        n_k=len(run_spec.source_readout_bridge_grid.reciprocal_indices),
        n_trial=source_count,
        steps=run_spec.source_readout_bridge_steps,
    )
    return matrix_count, readout_count, source_count


def _preflight_response_values_body(
    run_spec: ResponseRunSpec,
    values: Optional[FrozenComplexTensor] = None,
) -> tuple[int, int, int]:
    _preflight_run_spec(run_spec)
    shape = (
        len(run_spec.response_grid.reciprocal_indices),
        len(run_spec.readout_basis.vectors_wire),
        len(run_spec.source_basis.vectors_wire),
    )
    entries = math.prod(shape)
    if entries > 16_777_216:
        raise ValueError("source/readout response exceeds entry cap")
    if entries * 16 > _GENERAL_BODY_CAP:
        raise ValueError("source/readout response exceeds body cap")
    preflight_fejer_work(
        n_k=shape[0],
        n_state=len(run_spec.channel_order),
        order=run_spec.fejer_order,
    )
    if values is not None:
        _preflight_frozen_tensor_body(
            values,
            expected_shape=shape,
            field="response.values",
        )
    return shape


def _paired_failure_reason(
    failure: PairedResponseFailure,
) -> UndefinedReason:
    if failure in (
        PairedResponseFailure.ACTUAL_BRIDGE_FAILED,
        PairedResponseFailure.ABLATED_BRIDGE_FAILED,
    ):
        return UndefinedReason.RESPONSE_BRIDGE_FAILED
    return UndefinedReason.PAIRED_RESPONSE_FAILED


def _preflight_source_readout_response_body(
    response: SourceReadoutResponse,
    run_spec: ResponseRunSpec,
    registry_entry: ControlRegistryEntry,
    field: str,
) -> None:
    _exact_record(response, SourceReadoutResponse, field)
    _exact_record(response.source_basis, BasisManifest, f"{field}.source_basis")
    _exact_record(response.readout_basis, BasisManifest, f"{field}.readout_basis")
    _preflight_response_values_body(run_spec, response.values)
    _preflight_source_readout_bridge_audit_body(
        response.bridge_audit,
        run_spec,
        registry_entry,
    )
    response.__post_init__()


def _preflight_paired_branch_attempt(
    attempt: SourceReadoutBranchAttemptAudit,
    *,
    branch: Literal["actual", "matched_ablated"],
    run_spec: ResponseRunSpec,
    registry_entry: ControlRegistryEntry,
    field: str,
) -> None:
    _exact_record(attempt, SourceReadoutBranchAttemptAudit, field)
    if attempt.branch != branch:
        raise ValueError(f"{field} has the wrong branch")
    if attempt.response_values is not None:
        _preflight_response_values_body(
            run_spec,
            attempt.response_values,
        )
    if attempt.bridge_audit is not None:
        _preflight_source_readout_bridge_audit_body(
            attempt.bridge_audit,
            run_spec,
            registry_entry,
        )
    attempt.__post_init__()


def _preflight_paired_outcome_body(
    outcome: PairedResponseOutcome,
) -> None:
    _preflight_response_evidence_body(
        outcome,
        "paired response evidence",
    )
    _exact_record(outcome, PairedResponseOutcome, "paired_response_outcome")
    attempt = outcome.attempt_audit
    _exact_record(
        attempt,
        PairedResponseAttemptAudit,
        "paired_response_attempt",
    )
    _preflight_run_spec(attempt.run_spec)
    _preflight_shell_outcome_body(attempt.shell_outcome)
    registry_entry = (
        attempt.shell_outcome.attempt_audit.shell_spec.control_registry_entry
    )
    actual_attempt = attempt.actual_branch_attempt
    ablated_attempt = attempt.ablated_branch_attempt
    if actual_attempt is not None:
        _preflight_paired_branch_attempt(
            actual_attempt,
            branch="actual",
            run_spec=attempt.run_spec,
            registry_entry=registry_entry,
            field="paired_response_attempt.actual_branch_attempt",
        )
    if ablated_attempt is not None:
        _preflight_paired_branch_attempt(
            ablated_attempt,
            branch="matched_ablated",
            run_spec=attempt.run_spec,
            registry_entry=registry_entry,
            field="paired_response_attempt.ablated_branch_attempt",
        )
    attempt.__post_init__()
    outcome.__post_init__()
    if attempt.first_failure is not outcome.failure:
        raise ValueError("paired attempt first failure differs from outcome")

    if outcome.failure is None:
        if actual_attempt is None or ablated_attempt is None:
            raise ValueError("successful pair requires both branch attempts")
        for branch_attempt in (actual_attempt, ablated_attempt):
            if (
                branch_attempt.failure is not None
                or branch_attempt.response_values is None
                or branch_attempt.bridge_audit is None
            ):
                raise ValueError("successful pair has incomplete branch evidence")
        paired = outcome.paired_response
        if paired is None:
            raise ValueError("successful pair lacks paired response")
        _exact_record(paired, PairedFilteredResponse, "paired_filtered_response")
        _preflight_run_spec(paired.run_spec)
        _preflight_shell_manifest_body(paired.shell_manifest)
        _preflight_source_readout_response_body(
            paired.actual,
            paired.run_spec,
            registry_entry,
            "paired_filtered_response.actual",
        )
        _preflight_source_readout_response_body(
            paired.ablated,
            paired.run_spec,
            registry_entry,
            "paired_filtered_response.ablated",
        )
        paired.__post_init__()
        if (
            paired.run_spec != attempt.run_spec
            or attempt.shell_outcome.shell is None
            or paired.shell_manifest != attempt.shell_outcome.shell
            or paired.actual_dynamics_certificate != attempt.actual_dynamics_certificate
            or paired.ablated_dynamics_certificate
            != attempt.ablated_dynamics_certificate
            or paired.actual.values != actual_attempt.response_values
            or paired.actual.bridge_audit != actual_attempt.bridge_audit
            or paired.ablated.values != ablated_attempt.response_values
            or paired.ablated.bridge_audit != ablated_attempt.bridge_audit
        ):
            raise ValueError("paired success body differs from attempt evidence")
        return

    expected_status = BlockStatus(
        False,
        _paired_failure_reason(outcome.failure),
    )
    if outcome.status != expected_status or outcome.paired_response is not None:
        raise ValueError("failed pair has the wrong status or payload presence")
    if outcome.failure in (
        PairedResponseFailure.QUALIFICATION_INVALID,
        PairedResponseFailure.INPUT_BINDING_INVALID,
    ):
        if actual_attempt is not None or ablated_attempt is not None:
            raise ValueError("pre-branch failure cannot contain branch attempts")
    elif outcome.failure is PairedResponseFailure.ACTUAL_RESPONSE_FAILED:
        if (
            actual_attempt is None
            or actual_attempt.failure is not outcome.failure
            or actual_attempt.response_values is not None
            or actual_attempt.bridge_audit is not None
            or ablated_attempt is not None
        ):
            raise ValueError("actual response failure evidence is inconsistent")
    elif outcome.failure is PairedResponseFailure.ACTUAL_BRIDGE_FAILED:
        if (
            actual_attempt is None
            or actual_attempt.failure is not outcome.failure
            or actual_attempt.response_values is None
            or actual_attempt.bridge_audit is not None
            or ablated_attempt is None
            or ablated_attempt.failure is not None
            or ablated_attempt.response_values is None
            or ablated_attempt.bridge_audit is not None
        ):
            raise ValueError("actual bridge failure evidence is inconsistent")
    elif outcome.failure is PairedResponseFailure.ABLATED_RESPONSE_FAILED:
        if (
            actual_attempt is None
            or actual_attempt.failure is not None
            or actual_attempt.response_values is None
            or actual_attempt.bridge_audit is not None
            or ablated_attempt is None
            or ablated_attempt.failure is not outcome.failure
            or ablated_attempt.response_values is not None
            or ablated_attempt.bridge_audit is not None
        ):
            raise ValueError("ablated response failure evidence is inconsistent")
    elif outcome.failure is PairedResponseFailure.ABLATED_BRIDGE_FAILED:
        if (
            actual_attempt is None
            or actual_attempt.failure is not None
            or actual_attempt.response_values is None
            or actual_attempt.bridge_audit is None
            or ablated_attempt is None
            or ablated_attempt.failure is not outcome.failure
            or ablated_attempt.response_values is None
            or ablated_attempt.bridge_audit is not None
        ):
            raise ValueError("ablated bridge failure evidence is inconsistent")


def build_response_run_spec(
    protocol: VerifiedWindowCalibrationProtocol,
    transition: VerifiedTransition,
    certificate: VerifiedDynamicsCertificate,
    control_id: Literal["full", "zero", "direct_sum"],
    fejer_order: int,
) -> ResponseRunSpec:
    """Derive the unique source/readout run body from live authorities."""

    if control_id not in CONTROL_ORDER:
        raise ValueError("control_id is outside the closed registry")
    protocol_view = _reverify_verified_window_calibration_protocol(protocol)
    transition_record = _reverify_verified_transition(transition)
    certificate_record = _reverify_verified_dynamics_certificate(certificate)
    if transition_record.factory is not certificate_record.factory:
        raise ValueError("run spec transition/certificate factories differ")
    if transition_record.transition != certificate_record.certificate.transition:
        raise ValueError("run spec transition/certificate bodies differ")
    index = CONTROL_ORDER.index(control_id)
    registry_view = _reverify_verified_control_registry(protocol_view.registry)
    registry_entry = registry_view.registry.entries[index]
    protocol_entry = protocol_view.protocol.control_entries[index]
    registry_factory = _reverify_verified_factory(registry_view.controls[index].factory)
    transition_factory = _reverify_verified_factory(transition_record.factory)
    if registry_factory.factory != transition_factory.factory:
        raise ValueError("run spec factory body is not the closed control factory body")
    raw_transition = transition_record.transition
    if raw_transition.factory_sha != registry_entry.factory_sha:
        raise ValueError("run spec factory SHA differs from registry")
    if raw_transition.state_schema_id != (registry_entry.source_basis.state_schema_id):
        raise ValueError("run spec state schema differs from registry")
    if raw_transition.channel_order != (registry_entry.source_basis.channel_order):
        raise ValueError("run spec channel order differs from registry")
    if raw_transition.spatial_shape != (
        protocol_entry.source_readout_bridge_grid.spatial_shape
    ):
        raise ValueError("run spec transition spatial shape mismatch")
    order = _closed_order(fejer_order)
    source_count = len(registry_entry.source_basis.vectors_wire)
    provisional = ResponseRunSpec(
        run_spec_schema_version=RESPONSE_RUN_SPEC_SCHEMA_VERSION,
        run_spec_id=(f"v3m0.response-run.{control_id}.T{order}.v1"),
        window_protocol_sha=protocol_view.protocol.protocol_sha,
        control_registry_entry_sha=registry_entry.entry_sha,
        fejer_order=order,
        state_schema_id=raw_transition.state_schema_id,
        channel_order=raw_transition.channel_order,
        source_basis=registry_entry.source_basis,
        readout_basis=registry_entry.readout_basis,
        spatial_shape=raw_transition.spatial_shape,
        response_grid=protocol_entry.response_grid,
        source_readout_bridge_grid=(protocol_entry.source_readout_bridge_grid),
        source_readout_bridge_steps=(protocol_entry.source_readout_bridge_steps),
        source_trial_vectors=freeze_complex_tensor(
            np.eye(source_count, dtype=np.complex128)
        ),
        bridge_tolerance=_BRIDGE_TOLERANCE,
        spec_sha=_ZERO_SHA,
    )
    result = replace(
        provisional,
        spec_sha=canonical_sha(response_run_spec_payload(provisional)),
    )
    return verify_response_run_spec(result, protocol)


def verify_response_run_spec(
    spec: ResponseRunSpec,
    protocol: VerifiedWindowCalibrationProtocol,
) -> ResponseRunSpec:
    """Replay a raw run spec against the live pre-shell protocol authority."""

    _preflight_run_spec(spec)
    view = _reverify_verified_window_calibration_protocol(protocol)
    if spec.run_spec_schema_version != RESPONSE_RUN_SPEC_SCHEMA_VERSION:
        raise ValueError("unexpected response run spec schema")
    if spec.window_protocol_sha != view.protocol.protocol_sha:
        raise ValueError("run spec window protocol binding mismatch")
    protocol_entry, registry_entry = _protocol_entry_for_spec(spec, view)
    verify_basis_manifest(spec.source_basis)
    verify_basis_manifest(spec.readout_basis)
    if spec.source_basis != registry_entry.source_basis:
        raise ValueError("source basis differs from the closed registry")
    if spec.readout_basis != registry_entry.readout_basis:
        raise ValueError("readout basis differs from the closed registry")
    if spec.state_schema_id != registry_entry.source_basis.state_schema_id:
        raise ValueError("run spec state schema mismatch")
    if spec.channel_order != registry_entry.source_basis.channel_order:
        raise ValueError("run spec channel order mismatch")
    if registry_entry.readout_basis.state_schema_id != spec.state_schema_id:
        raise ValueError("readout state schema mismatch")
    if registry_entry.readout_basis.channel_order != spec.channel_order:
        raise ValueError("readout channel order mismatch")
    if spec.spatial_shape != (protocol_entry.source_readout_bridge_grid.spatial_shape):
        raise ValueError("run spec spatial shape mismatch")
    if spec.response_grid != protocol_entry.response_grid:
        raise ValueError("run spec response grid differs from protocol")
    if spec.source_readout_bridge_grid != (protocol_entry.source_readout_bridge_grid):
        raise ValueError("run spec bridge grid differs from protocol")
    if spec.source_readout_bridge_steps != (protocol_entry.source_readout_bridge_steps):
        raise ValueError("run spec bridge steps differ from protocol")
    if spec.source_readout_bridge_grid.torus_denominators != spec.spatial_shape:
        raise ValueError("bridge denominators must equal spatial_shape")
    if spec.source_readout_bridge_grid.spatial_shape != spec.spatial_shape:
        raise ValueError("bridge spatial shape differs from run spec")
    source_count = len(spec.source_basis.vectors_wire)
    trials = frozen_tensor_array(spec.source_trial_vectors)
    if trials.shape != (source_count, source_count):
        raise ValueError("source trials must cover the complete source domain")
    if not np.array_equal(
        trials,
        np.eye(source_count, dtype=np.complex128),
    ):
        raise ValueError("source trials are not the frozen identity frame")
    preflight_source_bridge_work(
        n_k=len(spec.source_readout_bridge_grid.reciprocal_indices),
        n_trial=source_count,
        steps=spec.source_readout_bridge_steps,
    )
    expected_id = (
        f"v3m0.response-run.{registry_entry.control_id}.T{spec.fejer_order}.v1"
    )
    if spec.run_spec_id != expected_id:
        raise ValueError("run_spec_id is not the canonical derivation")
    if spec.bridge_tolerance != _BRIDGE_TOLERANCE:
        raise ValueError("run spec bridge tolerance is not frozen")
    if spec.spec_sha != canonical_sha(response_run_spec_payload(spec)):
        raise ValueError("spec_sha does not match the complete body")
    return spec


def _strict_complex_matrix(
    value: object,
    field: str,
    *,
    square: bool = False,
) -> np.ndarray:
    if type(value) is not np.ndarray:
        raise TypeError(f"{field} must be a NumPy ndarray")
    if value.dtype != np.dtype(np.complex128):
        raise TypeError(f"{field} dtype must be complex128")
    if value.ndim != 2 or any(length <= 0 for length in value.shape):
        raise ValueError(f"{field} must be a non-empty matrix")
    if square and value.shape[0] != value.shape[1]:
        raise ValueError(f"{field} must be square")
    if not np.isfinite(value.real).all() or not np.isfinite(value.imag).all():
        raise ValueError(f"{field} must be finite")
    return value


def _hermitian_sqrt_pair(metric: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values, vectors = np.linalg.eigh(metric)
    if not np.isfinite(values).all():
        raise ValueError("metric eigendecomposition is non-finite")
    if float(values[0]) <= 0.0:
        raise ValueError("metric must be positive definite")
    root_values = np.sqrt(values)
    sqrt_metric = (
        vectors @ np.diag(root_values.astype(np.complex128)) @ vectors.conj().T
    ).astype(np.complex128)
    inverse_sqrt = (
        vectors @ np.diag((1.0 / root_values).astype(np.complex128)) @ vectors.conj().T
    ).astype(np.complex128)
    hermitian_residual = float(np.linalg.norm(metric - metric.conj().T, 2))
    sqrt_residual = float(np.linalg.norm(sqrt_metric @ sqrt_metric - metric, 2))
    inverse_residual = float(
        np.linalg.norm(sqrt_metric @ inverse_sqrt - np.eye(metric.shape[0]), 2)
    )
    if max(hermitian_residual, sqrt_residual, inverse_residual) > 1.0e-10:
        raise ValueError("deterministic Hermitian square-root residual failed")
    return sqrt_metric, inverse_sqrt


def _fejer_scalar(
    eigenvalue: complex,
    center_phase: float,
    order: int,
) -> complex:
    phase = complex(
        math.cos(-center_phase),
        math.sin(-center_phase),
    )
    ratio = complex(eigenvalue) * phase
    power = 1.0 + 0.0j
    real_terms: list[float] = []
    imag_terms: list[float] = []
    for step in range(order):
        weight = 1.0 - float(step) / float(order)
        term = weight * power
        real_terms.append(float(term.real))
        imag_terms.append(float(term.imag))
        power *= ratio
    normalization = (float(order) + 1.0) / 2.0
    return complex(
        math.fsum(real_terms) / normalization,
        math.fsum(imag_terms) / normalization,
    )


def _principal_phase(value: float) -> float:
    result = math.atan2(math.sin(value), math.cos(value))
    if result == -math.pi:
        return math.pi
    return result


def _phase_distance(first: float, second: float) -> float:
    return abs(_principal_phase(first - second))


def _in_phase_bands(
    phase: float,
    bands: tuple[tuple[float, float], ...],
) -> bool:
    return any(lower <= phase <= upper for lower, upper in bands)


def _orthogonal_projector(matrix: np.ndarray) -> np.ndarray:
    if matrix.ndim != 2 or matrix.shape[1] <= 0:
        raise ValueError("projector basis must contain columns")
    gram = matrix.conj().T @ matrix
    values, vectors = np.linalg.eigh(gram)
    largest = float(values[-1])
    if largest <= 0.0:
        raise ValueError("projector basis has zero rank")
    tolerance = 64.0 * np.finfo(np.float64).eps * float(max(matrix.shape)) * largest
    active = values > tolerance
    if not bool(np.any(active)):
        raise ValueError("projector basis is numerically rank deficient")
    basis = matrix @ vectors[:, active]
    normalizers = 1.0 / np.sqrt(values[active])
    orthonormal = basis * normalizers.reshape((1, -1))
    projector = orthonormal @ orthonormal.conj().T
    return np.asarray(projector, dtype=np.complex128)


@dataclass(frozen=True)
class _ProjectorCandidate:
    phase: float
    rank: int
    projector: np.ndarray
    participation: float
    runner_up_overlap: Optional[float]
    hermitian_residual: float
    idempotent_residual: float
    g_invariance_residual: float
    eigenphase_residual: float
    nearest_competitor_gap: Optional[float]


def _extract_projector_candidates(
    transition: np.ndarray,
    metric: np.ndarray,
    phase_bands: tuple[tuple[float, float], ...],
    order: int,
    source_injection: np.ndarray,
    readout: np.ndarray,
) -> tuple[_ProjectorCandidate, ...]:
    """Extract phase-cluster projectors without selecting basis vectors."""

    matrix = _strict_complex_matrix(
        transition,
        "transition",
        square=True,
    )
    gram = _strict_complex_matrix(metric, "metric", square=True)
    source = _strict_complex_matrix(source_injection, "source_injection")
    projection = _strict_complex_matrix(readout, "readout")
    state_count = matrix.shape[0]
    if gram.shape != matrix.shape:
        raise ValueError("metric and transition shapes differ")
    if source.shape[0] != state_count:
        raise ValueError("source injection state axis mismatch")
    if projection.shape[1] != state_count:
        raise ValueError("readout state axis mismatch")
    bands = _phase_bands(phase_bands, "phase_bands")
    closed_order = _closed_order(order)
    search_grid_step = phase_grid_step(closed_order)
    if not math.isfinite(search_grid_step) or search_grid_step <= 0.0:
        raise ValueError("phase search grid step is invalid")
    preflight_shell_projector_entries(n_k=1, n_state=state_count)
    preflight_fejer_work(
        n_k=1,
        n_state=state_count,
        order=closed_order,
    )
    sqrt_metric, inverse_sqrt = _hermitian_sqrt_pair(gram)
    whitened = sqrt_metric @ matrix @ inverse_sqrt

    from scipy.linalg import schur

    triangular, unitary = schur(whitened, output="complex")
    triangular = np.asarray(triangular, dtype=np.complex128)
    unitary = np.asarray(unitary, dtype=np.complex128)
    off_diagonal = triangular - np.diag(np.diag(triangular))
    if float(np.linalg.norm(off_diagonal, 2)) > 1.0e-10:
        raise ValueError("metric-unitary Schur form is not diagonal enough")
    raw_phases = tuple(
        _principal_phase(math.atan2(float(value.imag), float(value.real)))
        for value in np.diag(triangular)
    )
    selected = tuple(
        sorted(
            (
                (phase, index)
                for index, phase in enumerate(raw_phases)
                if _in_phase_bands(phase, bands)
            ),
            key=lambda item: (item[0], item[1]),
        )
    )
    if not selected:
        return ()
    cluster_tolerance = 128.0 * np.finfo(np.float64).eps * float(max(1, state_count))
    clusters: list[list[tuple[float, int]]] = []
    for item in selected:
        if (
            not clusters
            or _phase_distance(item[0], clusters[-1][-1][0]) > cluster_tolerance
        ):
            clusters.append([item])
        else:
            clusters[-1].append(item)
    source_projector = _orthogonal_projector(sqrt_metric @ source)
    readout_projector = _orthogonal_projector((projection @ inverse_sqrt).conj().T)
    identity = np.eye(state_count, dtype=np.complex128)
    preliminaries: list[dict[str, object]] = []
    for cluster in clusters:
        indices = tuple(item[1] for item in cluster)
        columns = unitary[:, indices]
        projector = np.asarray(
            columns @ columns.conj().T,
            dtype=np.complex128,
        )
        phase_vector = sum(
            (complex(math.cos(item[0]), math.sin(item[0])) for item in cluster),
            0.0 + 0.0j,
        )
        phase = _principal_phase(
            math.atan2(float(phase_vector.imag), float(phase_vector.real))
        )
        rank = len(indices)
        injection_participation = float(
            np.trace(projector @ source_projector).real / rank
        )
        readout_participation = float(
            np.trace(projector @ readout_projector).real / rank
        )
        participation = float(
            max(
                0.0,
                min(1.0, injection_participation, readout_participation),
            )
        )
        preliminaries.append(
            {
                "phase": phase,
                "rank": rank,
                "projector": projector,
                "participation": participation,
                "hermitian_residual": float(
                    np.linalg.norm(projector - projector.conj().T, 2)
                ),
                "idempotent_residual": float(
                    np.linalg.norm(projector @ projector - projector, 2)
                ),
                "g_invariance_residual": float(
                    np.linalg.norm(
                        (identity - projector) @ whitened @ projector,
                        2,
                    )
                ),
                "eigenphase_residual": float(
                    np.linalg.norm(
                        whitened @ projector
                        - complex(math.cos(phase), math.sin(phase)) * projector,
                        2,
                    )
                ),
            }
        )
    candidates: list[_ProjectorCandidate] = []
    for index, item in enumerate(preliminaries):
        competitors = tuple(
            other
            for other_index, other in enumerate(preliminaries)
            if other_index != index
        )
        gaps = tuple(
            _phase_distance(
                float(item["phase"]),
                float(other["phase"]),
            )
            for other in competitors
        )
        overlaps = tuple(float(other["participation"]) for other in competitors)
        candidates.append(
            _ProjectorCandidate(
                phase=float(item["phase"]),
                rank=int(item["rank"]),
                projector=np.asarray(
                    item["projector"],
                    dtype=np.complex128,
                ),
                participation=float(item["participation"]),
                runner_up_overlap=(None if not overlaps else float(max(overlaps))),
                hermitian_residual=float(item["hermitian_residual"]),
                idempotent_residual=float(item["idempotent_residual"]),
                g_invariance_residual=float(item["g_invariance_residual"]),
                eigenphase_residual=float(item["eigenphase_residual"]),
                nearest_competitor_gap=(None if not gaps else float(min(gaps))),
            )
        )
    return tuple(candidates)


def _phase_grid_collision(
    candidates: tuple[_ProjectorCandidate, ...],
    order: int,
) -> bool:
    step = phase_grid_step(_closed_order(order))
    return any(
        _phase_distance(first.phase, second.phase) < step
        for index, first in enumerate(candidates)
        for second in candidates[index + 1 :]
    )


def _endpoint_undefined_status() -> BlockStatus:
    try:
        reason = UndefinedReason["ENDPOINT_SHELL_AMBIGUOUS"]
    except KeyError as exc:
        raise RuntimeError(
            "contracts.UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS "
            "must be implemented before failed endpoint outcomes can issue"
        ) from exc
    return BlockStatus(False, reason)


def _build_endpoint_reference_outcome_from_matrices(
    spec: EndpointReferenceSpec,
    transition: np.ndarray,
    metric: np.ndarray,
    source_injection: np.ndarray,
    readout: np.ndarray,
) -> EndpointReferenceOutcome:
    """Pure raw builder used by the live endpoint authority and its verifier."""

    _exact_record(spec, EndpointReferenceSpec, "reference_spec")
    if spec.reference_spec_schema_version != ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION:
        raise ValueError("unexpected endpoint reference spec schema")
    if spec.reference_spec_sha != canonical_sha(endpoint_reference_spec_payload(spec)):
        raise ValueError("reference_spec_sha does not match complete body")
    raw_spec = _endpoint_reference_spec_record(spec)
    raw_outcome = _select_endpoint_reference_from_raw(
        raw_spec,
        transition,
        metric,
        source_injection,
        readout,
    )
    return _endpoint_reference_outcome_from_raw_v1(
        raw_outcome,
        spec,
        raw_spec,
    )


def _metric_symbol(
    witness: StabilityMetricWitness,
    momentum: np.ndarray,
) -> np.ndarray:
    if type(witness) is not StabilityMetricWitness:
        raise TypeError("stability metric witness has the wrong strict type")
    if type(momentum) is not np.ndarray or (momentum.dtype != np.dtype(np.float64)):
        raise TypeError("momentum must be a float64 NumPy vector")
    support = witness.metric_support_offsets
    if momentum.shape != (len(support[0]),):
        raise ValueError("momentum dimension differs from metric support")
    coefficients = frozen_tensor_array(witness.metric_kernel)
    if (
        coefficients.ndim != 3
        or coefficients.shape[0] != len(support)
        or coefficients.shape[1] != coefficients.shape[2]
    ):
        raise ValueError("metric kernel/support shape mismatch")
    result = np.zeros(coefficients.shape[1:], dtype=np.complex128)
    for coefficient, offset in zip(coefficients, support):
        argument = -float(
            sum(
                float(momentum[axis]) * coordinate
                for axis, coordinate in enumerate(offset)
            )
        )
        result += coefficient * complex(
            math.cos(argument),
            math.sin(argument),
        )
    return result


def _plane_wave(
    vector: np.ndarray,
    reciprocal_index: tuple[int, ...],
    spatial_shape: tuple[int, ...],
) -> np.ndarray:
    if type(vector) is not np.ndarray or (vector.dtype != np.dtype(np.complex128)):
        raise TypeError("plane-wave vector must be a complex128 ndarray")
    if vector.ndim != 1:
        raise ValueError("plane-wave vector must be one-dimensional")
    index = _index(
        reciprocal_index,
        "reciprocal_index",
        ndim=len(spatial_shape),
    )
    shape = _int_tuple(spatial_shape, "spatial_shape", positive=True)
    phase = np.ones(shape, dtype=np.complex128)
    for axis, (coordinate, length) in enumerate(zip(index, shape)):
        if coordinate >= length:
            raise ValueError("reciprocal index is outside the periodic grid")
        arguments = (
            2.0
            * math.pi
            * float(coordinate)
            / float(length)
            * np.arange(length, dtype=np.float64)
        )
        axis_phase = np.exp(np.complex128(1.0j) * arguments)
        reshape = [1] * len(shape)
        reshape[axis] = length
        phase *= axis_phase.reshape(tuple(reshape))
    normalization = np.float64(1.0 / math.sqrt(math.prod(shape)))
    return np.asarray(
        vector.reshape((vector.shape[0],) + (1,) * len(shape)) * phase * normalization,
        dtype=np.complex128,
    )


def _readback_plane_wave(
    field: np.ndarray,
    reciprocal_index: tuple[int, ...],
    spatial_shape: tuple[int, ...],
) -> np.ndarray:
    if type(field) is not np.ndarray or (field.dtype != np.dtype(np.complex128)):
        raise TypeError("plane-wave field must be a complex128 ndarray")
    shape = _int_tuple(spatial_shape, "spatial_shape", positive=True)
    if field.ndim != len(shape) + 1 or field.shape[1:] != shape:
        raise ValueError("plane-wave field spatial shape mismatch")
    index = _index(
        reciprocal_index,
        "reciprocal_index",
        ndim=len(shape),
    )
    phase = np.ones(shape, dtype=np.complex128)
    for axis, (coordinate, length) in enumerate(zip(index, shape)):
        if coordinate >= length:
            raise ValueError("reciprocal index is outside the periodic grid")
        arguments = (
            -2.0
            * math.pi
            * float(coordinate)
            / float(length)
            * np.arange(length, dtype=np.float64)
        )
        axis_phase = np.exp(np.complex128(1.0j) * arguments)
        reshape = [1] * len(shape)
        reshape[axis] = length
        phase *= axis_phase.reshape(tuple(reshape))
    normalization = np.float64(1.0 / math.sqrt(math.prod(shape)))
    return np.asarray(
        tuple(
            np.sum(field[channel] * phase, dtype=np.complex128) * normalization
            for channel in range(field.shape[0])
        ),
        dtype=np.complex128,
    )


def _bind_reference_inputs(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    actual_factory: VerifiedFactory,
    actual_transition: VerifiedTransition,
    actual_certificate: VerifiedDynamicsCertificate,
    control_id: Literal["full", "zero", "direct_sum"],
) -> tuple[
    object,
    object,
    object,
    object,
    ControlRegistryEntry,
    ControlWindowProtocolEntry,
]:
    if control_id not in CONTROL_ORDER:
        raise ValueError("control_id is outside the closed registry")
    registry_view = _reverify_verified_control_registry(registry)
    protocol_view = _reverify_verified_window_calibration_protocol(protocol)
    if protocol_view.registry is not registry:
        raise ValueError("window protocol is not bound to this registry")
    factory_view = _reverify_verified_factory(actual_factory)
    if factory_view.role != "actual":
        raise ValueError("endpoint reference requires the actual branch")
    index = CONTROL_ORDER.index(control_id)
    registry_entry = registry_view.registry.entries[index]
    protocol_entry = protocol_view.protocol.control_entries[index]
    registry_factory_view = _reverify_verified_factory(
        registry_view.controls[index].factory
    )
    if registry_factory_view.factory != factory_view.factory:
        raise ValueError("actual factory body is not the closed control factory body")
    if registry_entry.factory_sha != factory_view.factory.factory_sha:
        raise ValueError("registry entry factory SHA mismatch")
    if protocol_entry.control_registry_entry_sha != registry_entry.entry_sha:
        raise ValueError("window entry registry binding mismatch")
    transition_record = _reverify_verified_transition(actual_transition)
    if transition_record.factory is not actual_factory:
        raise ValueError("actual transition is not factory-bound")
    certificate_record = _reverify_verified_dynamics_certificate(actual_certificate)
    if certificate_record.factory is not actual_factory:
        raise ValueError("actual dynamics certificate is not factory-bound")
    if certificate_record.certificate.transition != transition_record.transition:
        raise ValueError("certificate transition body differs from live input")
    if transition_record.transition.factory_sha != registry_entry.factory_sha:
        raise ValueError("transition factory SHA differs from registry")
    return (
        registry_view,
        protocol_view,
        factory_view,
        transition_record,
        registry_entry,
        protocol_entry,
    )


def _expected_reference_spec(
    protocol_view: object,
    transition_record: object,
    actual_certificate: VerifiedDynamicsCertificate,
    registry_entry: ControlRegistryEntry,
    protocol_entry: ControlWindowProtocolEntry,
    order: int,
) -> EndpointReferenceSpec:
    certificate_record = _reverify_verified_dynamics_certificate(actual_certificate)
    provisional = EndpointReferenceSpec(
        reference_spec_schema_version=(ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION),
        window_protocol_sha=protocol_view.protocol.protocol_sha,
        control_registry_entry=registry_entry,
        actual_factory_sha=registry_entry.factory_sha,
        actual_transition_sha=transition_record.transition.transition_sha,
        actual_dynamics_certificate_sha=(
            certificate_record.certificate.certificate_sha
        ),
        candidate_fejer_order=_closed_order(
            order,
            "candidate_fejer_order",
        ),
        reference_reciprocal_index=(protocol_entry.reference_reciprocal_index),
        preregistered_phase_bands=(protocol_entry.preregistered_phase_bands),
        expected_shell_rank=protocol_entry.expected_shell_rank,
        expected_shell_rank_source_id=(protocol_entry.expected_shell_rank_source_id),
        reference_spec_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        reference_spec_sha=canonical_sha(endpoint_reference_spec_payload(provisional)),
    )


def _expected_reference_outcome(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    actual_factory: VerifiedFactory,
    actual_transition: VerifiedTransition,
    actual_certificate: VerifiedDynamicsCertificate,
    control_id: Literal["full", "zero", "direct_sum"],
    order: int,
) -> EndpointReferenceOutcome:
    (
        _registry_view,
        protocol_view,
        _factory_view,
        transition_record,
        registry_entry,
        protocol_entry,
    ) = _bind_reference_inputs(
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
        control_id,
    )
    spec = _expected_reference_spec(
        protocol_view,
        transition_record,
        actual_certificate,
        registry_entry,
        protocol_entry,
        order,
    )
    reciprocal_index = spec.reference_reciprocal_index
    denominators = protocol_entry.response_grid.torus_denominators
    momentum = np.asarray(
        tuple(
            2.0 * math.pi * float(index) / float(denominator)
            for index, denominator in zip(
                reciprocal_index,
                denominators,
            )
        ),
        dtype=np.float64,
    )
    matrix = transition_symbol(actual_transition, momentum)
    certificate_record = _reverify_verified_dynamics_certificate(actual_certificate)
    gram = _metric_symbol(
        certificate_record.certificate.stability_metric,
        momentum,
    )
    source = basis_manifest_array(registry_entry.source_basis).T.copy()
    readout = basis_manifest_array(registry_entry.readout_basis).conj().copy()
    return _build_endpoint_reference_outcome_from_matrices(
        spec,
        matrix,
        gram,
        source,
        readout,
    )


def _reference_authority_seal(
    outcome: EndpointReferenceOutcome,
) -> str:
    return canonical_sha(
        {
            "authority_schema_version": ("v3m0.verified-endpoint-reference-outcome.v1"),
            "outcome": _endpoint_reference_outcome_record(outcome),
        }
    )


def _make_reference_authority() -> tuple[
    Callable[
        [
            EndpointReferenceOutcome,
            VerifiedControlRegistry,
            VerifiedWindowCalibrationProtocol,
            VerifiedFactory,
            VerifiedTransition,
            VerifiedDynamicsCertificate,
        ],
        VerifiedEndpointReferenceOutcome,
    ],
    Callable[
        [VerifiedEndpointReferenceOutcome],
        _ReferenceAuthority,
    ],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedEndpointReferenceOutcome],
            _ReferenceAuthority,
        ],
    ] = {}
    lock = threading.RLock()
    canonical = canonical_sha

    def issue(
        outcome: EndpointReferenceOutcome,
        registry: VerifiedControlRegistry,
        protocol: VerifiedWindowCalibrationProtocol,
        factory: VerifiedFactory,
        transition: VerifiedTransition,
        certificate: VerifiedDynamicsCertificate,
    ) -> VerifiedEndpointReferenceOutcome:
        control_id = outcome.reference_spec.control_registry_entry.control_id
        expected = _expected_reference_outcome(
            registry,
            protocol,
            factory,
            transition,
            certificate,
            control_id,
            outcome.reference_spec.candidate_fejer_order,
        )
        if outcome != expected:
            raise ValueError("reference outcome differs from live replay")
        seal = canonical(
            {
                "authority_schema_version": (
                    "v3m0.verified-endpoint-reference-outcome.v1"
                ),
                "outcome": _endpoint_reference_outcome_record(outcome),
            }
        )
        wrapper = VerifiedEndpointReferenceOutcome(
            _ISSUANCE_TOKEN,
            outcome,
            seal,
        )
        identity = id(wrapper)
        authority = _ReferenceAuthority(
            outcome=outcome,
            registry=registry,
            protocol=protocol,
            factory=factory,
            transition=transition,
            certificate=certificate,
            seal=seal,
        )

        def remove(
            reference: weakref.ReferenceType[VerifiedEndpointReferenceOutcome],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        return wrapper

    def reverify(
        wrapper: VerifiedEndpointReferenceOutcome,
    ) -> _ReferenceAuthority:
        if type(wrapper) is not VerifiedEndpointReferenceOutcome:
            raise TypeError("endpoint reference requires a module-issued capability")
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError("endpoint reference identity is not live")
            authority = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedEndpointReferenceOutcome__token",
            )
            raw = object.__getattribute__(
                wrapper,
                "_VerifiedEndpointReferenceOutcome__outcome",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedEndpointReferenceOutcome__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "endpoint reference authority record is incomplete"
            ) from exc
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("endpoint reference token mismatch")
        control_id = authority.outcome.reference_spec.control_registry_entry.control_id
        expected = _expected_reference_outcome(
            authority.registry,
            authority.protocol,
            authority.factory,
            authority.transition,
            authority.certificate,
            control_id,
            authority.outcome.reference_spec.candidate_fejer_order,
        )
        expected_seal = canonical(
            {
                "authority_schema_version": (
                    "v3m0.verified-endpoint-reference-outcome.v1"
                ),
                "outcome": _endpoint_reference_outcome_record(expected),
            }
        )
        if (
            raw != authority.outcome
            or raw != expected
            or seal != authority.seal
            or seal != expected_seal
        ):
            raise ValueError("endpoint reference immutable seal mismatch")
        return authority

    return issue, reverify


(
    _issue_verified_endpoint_reference_outcome,
    _reference_reverify_impl,
) = _make_reference_authority()
_reverify_reference_authority = _reference_reverify_impl


def _legacy_build_endpoint_reference(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    actual_factory: VerifiedFactory,
    actual_transition: VerifiedTransition,
    actual_certificate: VerifiedDynamicsCertificate,
    control_id: Literal["full", "zero", "direct_sum"],
    candidate_fejer_order: int,
) -> VerifiedEndpointReferenceOutcome:
    """Build and seal one actual-derived endpoint reference attempt."""

    outcome = _expected_reference_outcome(
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
        control_id,
        candidate_fejer_order,
    )
    return _issue_verified_endpoint_reference_outcome(
        outcome,
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
    )


def _legacy_verify_endpoint_reference_outcome(
    outcome: EndpointReferenceOutcome,
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    actual_factory: VerifiedFactory,
    actual_transition: VerifiedTransition,
    actual_certificate: VerifiedDynamicsCertificate,
) -> VerifiedEndpointReferenceOutcome:
    """Hydrate only after replaying actual ``M/G`` and every raw field."""

    _exact_record(
        outcome,
        EndpointReferenceOutcome,
        "endpoint_reference_outcome",
    )
    expected = _expected_reference_outcome(
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
        outcome.reference_spec.control_registry_entry.control_id,
        outcome.reference_spec.candidate_fejer_order,
    )
    if outcome != expected:
        raise ValueError("raw endpoint reference outcome differs from replay")
    return _issue_verified_endpoint_reference_outcome(
        outcome,
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
    )


def _projector_overlap(
    first: np.ndarray,
    second: np.ndarray,
    rank: int,
) -> float:
    value = float(np.trace(first @ second).real / rank)
    return float(max(0.0, min(1.0, value)))


def _build_endpoint_shell_outcome_from_matrices(
    reference_outcome: EndpointReferenceOutcome,
    shell_spec: EndpointShellSpec,
    matrices: tuple[np.ndarray, ...],
    metrics: tuple[np.ndarray, ...],
    source_injection: np.ndarray,
    readout: np.ndarray,
    *,
    actual_factory_sha: str,
    actual_transition_sha: str,
    actual_dynamics_certificate_sha: str,
    dt: float,
) -> EndpointShellOutcome:
    """Build the raw per-path shell graph from replayed actual matrices."""

    _exact_record(
        reference_outcome,
        EndpointReferenceOutcome,
        "reference_outcome",
    )
    _exact_record(shell_spec, EndpointShellSpec, "shell_spec")
    if not reference_outcome.status.defined or (reference_outcome.reference is None):
        raise ValueError("shell requires a successful reference outcome")
    if shell_spec.endpoint_reference_projector != (reference_outcome.reference):
        raise ValueError("shell spec reference differs from upstream outcome")
    if shell_spec.shell_spec_sha != canonical_sha(
        endpoint_shell_spec_payload(shell_spec)
    ):
        raise ValueError("shell_spec_sha does not match complete body")
    _sha(actual_factory_sha, "actual_factory_sha")
    _sha(actual_transition_sha, "actual_transition_sha")
    _sha(
        actual_dynamics_certificate_sha,
        "actual_dynamics_certificate_sha",
    )
    time_step = _finite_float(dt, "dt")
    if time_step <= 0.0:
        raise ValueError("dt must be positive")
    raw_reference = _endpoint_reference_outcome_record(reference_outcome)
    raw_shell_spec = _endpoint_shell_spec_record(shell_spec)
    raw_outcome = _track_endpoint_shell_from_raw(
        raw_reference,
        raw_shell_spec,
        matrices,
        metrics,
        source_injection,
        readout,
        actual_factory_sha,
        actual_transition_sha,
        actual_dynamics_certificate_sha,
        time_step,
    )
    return _endpoint_shell_outcome_from_raw_v1(
        raw_outcome,
        reference_outcome,
        shell_spec,
        raw_reference,
        raw_shell_spec,
    )


def _preflight_shell_spec(spec: EndpointShellSpec) -> None:
    _exact_record(spec, EndpointShellSpec, "endpoint_shell_spec")
    _exact_registry_entry_tree(
        spec.control_registry_entry,
        "endpoint_shell_spec.control_registry_entry",
    )
    _exact_response_grid_tree(
        spec.response_grid,
        "endpoint_shell_spec.response_grid",
    )
    _exact_record(
        spec.endpoint_reference_projector,
        EndpointReferenceProjector,
        "endpoint_shell_spec.endpoint_reference_projector",
    )
    point_count = sum(
        len(path) for path in spec.response_grid.direction_manifest.ordered_paths
    )
    if point_count <= 0 or point_count > 262_144:
        raise ValueError("shell path points exceed the frozen cap")
    reference = spec.endpoint_reference_projector
    if len(reference.projector.shape) != 2:
        raise ValueError("reference projector must be a matrix")
    state_count = len(spec.control_registry_entry.source_basis.channel_order)
    _preflight_frozen_tensor_body(
        reference.projector,
        expected_shape=(state_count, state_count),
        field="endpoint_shell_spec.endpoint_reference_projector.projector",
    )
    preflight_shell_projector_entries(
        n_k=point_count,
        n_state=state_count,
    )
    estimated_bytes = point_count * state_count**2 * 16
    if estimated_bytes > _GENERAL_BODY_CAP:
        raise ValueError("shell evidence exceeds general body cap")
    _exact_dataclass_tree(spec, "endpoint_shell_spec")


def _preflight_shell_manifest_body(shell: EndpointShellManifest) -> None:
    _exact_record(shell, EndpointShellManifest, "endpoint_shell_manifest")
    _preflight_shell_spec(shell.shell_spec)
    point_count = sum(
        len(path)
        for path in shell.shell_spec.response_grid.direction_manifest.ordered_paths
    )
    if len(shell.shell_phases) != point_count:
        raise ValueError("shell phases do not cover exact path points")
    if len(shell.point_audits) != point_count:
        raise ValueError("shell audits do not cover exact path points")
    state_count = len(
        shell.shell_spec.control_registry_entry.source_basis.channel_order
    )
    _preflight_frozen_tensor_body(
        shell.shell_projectors,
        expected_shape=(point_count, state_count, state_count),
        field="endpoint_shell_manifest.shell_projectors",
    )
    for index, audit in enumerate(shell.point_audits):
        _exact_record(
            audit,
            ShellPointAudit,
            f"endpoint_shell_manifest.point_audits[{index}]",
        )
    _exact_dataclass_tree(shell, "endpoint_shell_manifest")


def _preflight_reference_outcome_body(
    outcome: EndpointReferenceOutcome,
) -> None:
    _exact_record(
        outcome,
        EndpointReferenceOutcome,
        "endpoint_reference_outcome",
    )
    spec = outcome.reference_spec
    _exact_record(spec, EndpointReferenceSpec, "endpoint_reference_spec")
    _exact_registry_entry_tree(
        spec.control_registry_entry,
        "endpoint_reference_spec.control_registry_entry",
    )
    state_count = len(spec.control_registry_entry.source_basis.channel_order)
    attempt = outcome.attempt_audit
    _exact_record(
        attempt,
        EndpointReferenceAttemptAudit,
        "endpoint_reference_attempt",
    )
    candidate_count = len(attempt.candidate_phases)
    if candidate_count > state_count:
        raise ValueError("reference candidate count exceeds state dimension")
    for name in (
        "candidate_ranks",
        "candidate_participations",
        "runner_up_overlaps",
        "hermitian_residuals",
        "idempotent_residuals",
        "g_invariance_residuals",
        "eigenphase_residuals",
        "observed_competitor_gaps",
    ):
        if len(getattr(attempt, name)) != candidate_count:
            raise ValueError("reference candidate audit columns do not align")
    if outcome.reference is not None:
        _exact_record(
            outcome.reference,
            EndpointReferenceProjector,
            "endpoint_reference_projector",
        )
        _preflight_frozen_tensor_body(
            outcome.reference.projector,
            expected_shape=(state_count, state_count),
            field="endpoint_reference_projector.projector",
        )
    outcome.__post_init__()
    attempt.__post_init__()
    spec.__post_init__()
    _exact_dataclass_tree(outcome, "endpoint_reference_outcome")


def _preflight_shell_outcome_body(
    outcome: EndpointShellOutcome,
) -> None:
    _exact_record(outcome, EndpointShellOutcome, "endpoint_shell_outcome")
    _preflight_reference_outcome_body(outcome.reference_outcome)
    attempt = outcome.attempt_audit
    _exact_record(
        attempt,
        EndpointShellAttemptAudit,
        "endpoint_shell_attempt",
    )
    _preflight_shell_spec(attempt.shell_spec)
    point_count = sum(
        len(path)
        for path in attempt.shell_spec.response_grid.direction_manifest.ordered_paths
    )
    if len(attempt.point_attempts) > point_count:
        raise ValueError("shell attempt contains too many path points")
    state_count = len(
        attempt.shell_spec.control_registry_entry.source_basis.channel_order
    )
    for point_index, point in enumerate(attempt.point_attempts):
        _exact_record(
            point,
            ShellCandidatePointAttempt,
            f"endpoint_shell_attempt.point_attempts[{point_index}]",
        )
        candidate_count = len(point.candidate_phases)
        if candidate_count > state_count:
            raise ValueError("shell candidate count exceeds state dimension")
        for name in (
            "candidate_ranks",
            "candidate_participations",
            "candidate_reference_overlaps",
            "candidate_predecessor_overlaps",
        ):
            if len(getattr(point, name)) != candidate_count:
                raise ValueError("shell candidate point columns do not align")
        point.__post_init__()
    if outcome.shell is not None:
        _preflight_shell_manifest_body(outcome.shell)
    outcome.__post_init__()
    attempt.__post_init__()
    _exact_dataclass_tree(outcome, "endpoint_shell_outcome")


def verify_endpoint_shell_spec(
    spec: EndpointShellSpec,
    protocol: VerifiedWindowCalibrationProtocol,
) -> EndpointShellSpec:
    """Replay the raw shell spec against the pre-shell protocol body."""

    _preflight_shell_spec(spec)
    view = _reverify_verified_window_calibration_protocol(protocol)
    if spec.shell_spec_schema_version != ENDPOINT_SHELL_SPEC_SCHEMA_VERSION:
        raise ValueError("unexpected endpoint shell spec schema")
    if spec.window_protocol_sha != view.protocol.protocol_sha:
        raise ValueError("shell spec window protocol binding mismatch")
    matches = tuple(
        entry
        for entry in view.protocol.control_entries
        if entry.control_registry_entry_sha == spec.control_registry_entry.entry_sha
    )
    if len(matches) != 1:
        raise ValueError("shell spec registry entry binding is not unique")
    protocol_entry = matches[0]
    registry_matches = tuple(
        entry
        for entry in view.registry.registry.entries
        if entry.entry_sha == spec.control_registry_entry.entry_sha
    )
    if registry_matches != (spec.control_registry_entry,):
        raise ValueError("shell spec registry entry differs from live body")
    if spec.response_grid != protocol_entry.response_grid:
        raise ValueError("shell response grid differs from protocol")
    if spec.preregistered_phase_bands != (protocol_entry.preregistered_phase_bands):
        raise ValueError("shell phase bands differ from protocol")
    reference = spec.endpoint_reference_projector
    if reference.control_registry_entry_sha != spec.control_registry_entry.entry_sha:
        raise ValueError("shell reference registry entry binding mismatch")
    if reference.reference_reciprocal_index != (
        protocol_entry.reference_reciprocal_index
    ):
        raise ValueError("shell reference reciprocal node mismatch")
    if reference.rank != protocol_entry.expected_shell_rank:
        raise ValueError("shell reference rank differs from parent freeze")
    if reference.reference_sha != canonical_sha(
        endpoint_reference_projector_payload(reference)
    ):
        raise ValueError("shell reference SHA does not match complete body")
    if spec.extraction_protocol_id != SHELL_EXTRACTION_PROTOCOL_ID:
        raise ValueError("shell extraction protocol is not frozen")
    if spec.shell_spec_sha != canonical_sha(endpoint_shell_spec_payload(spec)):
        raise ValueError("shell_spec_sha does not match complete body")
    return spec


def _legacy_build_endpoint_shell_spec(
    protocol: VerifiedWindowCalibrationProtocol,
    reference: VerifiedEndpointReferenceOutcome,
) -> EndpointShellSpec:
    """Freeze a shell spec only from a successful live reference outcome."""

    authority = _reverify_verified_endpoint_reference_outcome(reference)
    if authority.protocol is not protocol:
        raise ValueError("reference is not bound to this window protocol")
    outcome = authority.outcome
    if not outcome.status.defined or outcome.reference is None:
        raise ValueError("failed endpoint reference cannot seed a shell")
    reference_spec = outcome.reference_spec
    protocol_view = _reverify_verified_window_calibration_protocol(protocol)
    matches = tuple(
        item
        for item in protocol_view.protocol.control_entries
        if item.control_registry_entry_sha
        == reference_spec.control_registry_entry.entry_sha
    )
    if len(matches) != 1:
        raise ValueError("reference protocol entry binding is not unique")
    protocol_entry = matches[0]
    provisional = EndpointShellSpec(
        shell_spec_schema_version=ENDPOINT_SHELL_SPEC_SCHEMA_VERSION,
        window_protocol_sha=protocol_view.protocol.protocol_sha,
        control_registry_entry=reference_spec.control_registry_entry,
        response_grid=protocol_entry.response_grid,
        preregistered_phase_bands=(protocol_entry.preregistered_phase_bands),
        candidate_fejer_order=reference_spec.candidate_fejer_order,
        endpoint_reference_projector=outcome.reference,
        extraction_protocol_id=SHELL_EXTRACTION_PROTOCOL_ID,
        shell_spec_sha=_ZERO_SHA,
    )
    result = replace(
        provisional,
        shell_spec_sha=canonical_sha(endpoint_shell_spec_payload(provisional)),
    )
    return verify_endpoint_shell_spec(result, protocol)


def _expected_shell_outcome(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    reference: VerifiedEndpointReferenceOutcome,
    actual_factory: VerifiedFactory,
    actual_transition: VerifiedTransition,
    actual_certificate: VerifiedDynamicsCertificate,
    shell_spec: EndpointShellSpec,
) -> EndpointShellOutcome:
    reference_authority = _reverify_verified_endpoint_reference_outcome(reference)
    if (
        reference_authority.registry is not registry
        or reference_authority.protocol is not protocol
        or reference_authority.factory is not actual_factory
        or reference_authority.transition is not actual_transition
        or reference_authority.certificate is not actual_certificate
    ):
        raise ValueError("shell inputs differ from reference authority")
    verified_spec = verify_endpoint_shell_spec(shell_spec, protocol)
    expected_spec = _legacy_build_endpoint_shell_spec(protocol, reference)
    if verified_spec != expected_spec:
        raise ValueError("shell spec is not the unique reference derivation")
    transition_record = _reverify_verified_transition(actual_transition)
    certificate_record = _reverify_verified_dynamics_certificate(actual_certificate)
    point_indices = tuple(
        reciprocal_index
        for path in verified_spec.response_grid.direction_manifest.ordered_paths
        for reciprocal_index in path
    )
    denominators = verified_spec.response_grid.torus_denominators
    matrices: list[np.ndarray] = []
    metrics: list[np.ndarray] = []
    for reciprocal_index in point_indices:
        momentum = np.asarray(
            tuple(
                2.0 * math.pi * float(index) / float(denominator)
                for index, denominator in zip(
                    reciprocal_index,
                    denominators,
                )
            ),
            dtype=np.float64,
        )
        matrices.append(transition_symbol(actual_transition, momentum))
        metrics.append(
            _metric_symbol(
                certificate_record.certificate.stability_metric,
                momentum,
            )
        )
    registry_entry = verified_spec.control_registry_entry
    source = basis_manifest_array(registry_entry.source_basis).T.copy()
    readout = basis_manifest_array(registry_entry.readout_basis).conj().copy()
    return _build_endpoint_shell_outcome_from_matrices(
        reference_authority.outcome,
        verified_spec,
        tuple(matrices),
        tuple(metrics),
        source,
        readout,
        actual_factory_sha=transition_record.transition.factory_sha,
        actual_transition_sha=transition_record.transition.transition_sha,
        actual_dynamics_certificate_sha=(
            certificate_record.certificate.certificate_sha
        ),
        dt=transition_record.transition.dt,
    )


def _make_shell_authority() -> tuple[
    Callable[
        [
            EndpointShellOutcome,
            VerifiedEndpointReferenceOutcome,
            VerifiedControlRegistry,
            VerifiedWindowCalibrationProtocol,
            VerifiedFactory,
            VerifiedTransition,
            VerifiedDynamicsCertificate,
        ],
        VerifiedEndpointShellOutcome,
    ],
    Callable[
        [VerifiedEndpointShellOutcome],
        _ShellAuthority,
    ],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedEndpointShellOutcome],
            _ShellAuthority,
        ],
    ] = {}
    lock = threading.RLock()
    canonical = canonical_sha

    def issue(
        outcome: EndpointShellOutcome,
        reference: VerifiedEndpointReferenceOutcome,
        registry: VerifiedControlRegistry,
        protocol: VerifiedWindowCalibrationProtocol,
        factory: VerifiedFactory,
        transition: VerifiedTransition,
        certificate: VerifiedDynamicsCertificate,
    ) -> VerifiedEndpointShellOutcome:
        expected = _expected_shell_outcome(
            registry,
            protocol,
            reference,
            factory,
            transition,
            certificate,
            outcome.attempt_audit.shell_spec,
        )
        if outcome != expected:
            raise ValueError("shell outcome differs from live replay")
        seal = canonical(
            {
                "authority_schema_version": ("v3m0.verified-endpoint-shell-outcome.v1"),
                "outcome": _endpoint_shell_outcome_record(outcome),
            }
        )
        wrapper = VerifiedEndpointShellOutcome(
            _ISSUANCE_TOKEN,
            outcome,
            seal,
        )
        identity = id(wrapper)
        authority = _ShellAuthority(
            outcome=outcome,
            reference=reference,
            registry=registry,
            protocol=protocol,
            factory=factory,
            transition=transition,
            certificate=certificate,
            seal=seal,
        )

        def remove(
            weak: weakref.ReferenceType[VerifiedEndpointShellOutcome],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is weak:
                    del live[wrapper_id]

        weak = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (weak, authority)
        return wrapper

    def reverify(
        wrapper: VerifiedEndpointShellOutcome,
    ) -> _ShellAuthority:
        if type(wrapper) is not VerifiedEndpointShellOutcome:
            raise TypeError("endpoint shell requires a module-issued capability")
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError("endpoint shell identity is not live")
            authority = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedEndpointShellOutcome__token",
            )
            raw = object.__getattribute__(
                wrapper,
                "_VerifiedEndpointShellOutcome__outcome",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedEndpointShellOutcome__seal",
            )
        except AttributeError as exc:
            raise ValueError("endpoint shell authority record is incomplete") from exc
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("endpoint shell token mismatch")
        expected = _expected_shell_outcome(
            authority.registry,
            authority.protocol,
            authority.reference,
            authority.factory,
            authority.transition,
            authority.certificate,
            authority.outcome.attempt_audit.shell_spec,
        )
        expected_seal = canonical(
            {
                "authority_schema_version": ("v3m0.verified-endpoint-shell-outcome.v1"),
                "outcome": _endpoint_shell_outcome_record(expected),
            }
        )
        if (
            raw != authority.outcome
            or raw != expected
            or seal != authority.seal
            or seal != expected_seal
        ):
            raise ValueError("endpoint shell immutable seal mismatch")
        return authority

    return issue, reverify


(
    _issue_verified_endpoint_shell_outcome,
    _shell_reverify_impl,
) = _make_shell_authority()
_reverify_shell_authority = _shell_reverify_impl


def _legacy_build_endpoint_shell(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    reference: VerifiedEndpointReferenceOutcome,
    actual_factory: VerifiedFactory,
    actual_transition: VerifiedTransition,
    actual_certificate: VerifiedDynamicsCertificate,
    shell_spec: EndpointShellSpec,
) -> VerifiedEndpointShellOutcome:
    """Extract and seal one actual endpoint shell over every declared path."""

    outcome = _expected_shell_outcome(
        registry,
        protocol,
        reference,
        actual_factory,
        actual_transition,
        actual_certificate,
        shell_spec,
    )
    return _issue_verified_endpoint_shell_outcome(
        outcome,
        reference,
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
    )


def _legacy_verify_endpoint_shell_outcome(
    outcome: EndpointShellOutcome,
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    reference: VerifiedEndpointReferenceOutcome,
    actual_factory: VerifiedFactory,
    actual_transition: VerifiedTransition,
    actual_certificate: VerifiedDynamicsCertificate,
) -> VerifiedEndpointShellOutcome:
    """Hydrate only after replaying the reference and every shell path."""

    _exact_record(
        outcome,
        EndpointShellOutcome,
        "endpoint_shell_outcome",
    )
    expected = _expected_shell_outcome(
        registry,
        protocol,
        reference,
        actual_factory,
        actual_transition,
        actual_certificate,
        outcome.attempt_audit.shell_spec,
    )
    if outcome != expected:
        raise ValueError("raw endpoint shell outcome differs from replay")
    return _issue_verified_endpoint_shell_outcome(
        outcome,
        reference,
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
    )


def _measure_source_readout_bridge(
    *,
    branch: Literal["actual", "matched_ablated"],
    factory: VerifiedFactory,
    transition: VerifiedTransition,
    dynamics_certificate_sha: str,
    run_spec: ResponseRunSpec,
    registry_entry: ControlRegistryEntry,
) -> SourceReadoutBridgeAudit:
    """Replay every ``(k,t,source-column)`` through the real-space executor."""

    if branch not in ("actual", "matched_ablated"):
        raise ValueError("branch is not closed")
    _sha(dynamics_certificate_sha, "dynamics_certificate_sha")
    _preflight_bridge_output_body(run_spec)
    _exact_registry_entry_tree(registry_entry)
    if run_spec.spec_sha != canonical_sha(response_run_spec_payload(run_spec)):
        raise ValueError("source bridge run spec SHA mismatch")
    factory_view = _reverify_verified_factory(factory)
    transition_record = _reverify_verified_transition(transition)
    if transition_record.factory is not factory:
        raise ValueError("source bridge transition is not factory-bound")
    expected_role = "actual" if branch == "actual" else "matched_ablated"
    if factory_view.role != expected_role:
        raise ValueError("source bridge branch/factory role mismatch")
    if run_spec.control_registry_entry_sha != registry_entry.entry_sha:
        raise ValueError("source bridge registry entry binding mismatch")
    if run_spec.source_basis != registry_entry.source_basis:
        raise ValueError("source bridge basis differs from registry")
    if run_spec.readout_basis != registry_entry.readout_basis:
        raise ValueError("source bridge readout differs from registry")
    payload = factory_view.factory
    if payload.factory_sha != transition_record.transition.factory_sha:
        raise ValueError("source bridge transition factory SHA mismatch")
    if payload.state_shape[1:] != run_spec.spatial_shape:
        raise ValueError("source bridge spatial shape mismatch")
    source_vectors = basis_manifest_array(run_spec.source_basis)
    readout_vectors = basis_manifest_array(run_spec.readout_basis)
    source_injection = source_vectors.T.copy()
    readout = readout_vectors.conj().copy()
    trials = frozen_tensor_array(run_spec.source_trial_vectors)
    source_count = source_injection.shape[1]
    if not np.array_equal(
        trials,
        np.eye(source_count, dtype=np.complex128),
    ):
        raise ValueError("V3-M0 source bridge requires the complete identity frame")
    differences: list[tuple[tuple[int, ...], int, np.ndarray]] = []
    for reciprocal_index in run_spec.source_readout_bridge_grid.reciprocal_indices:
        momentum = np.asarray(
            tuple(
                2.0 * math.pi * float(index) / float(length)
                for index, length in zip(
                    reciprocal_index,
                    run_spec.spatial_shape,
                )
            ),
            dtype=np.float64,
        )
        symbol = transition_symbol(transition, momentum)
        for steps in run_spec.source_readout_bridge_steps:
            difference = np.zeros(
                (readout.shape[0], source_count),
                dtype=np.complex128,
            )
            for trial_index, trial in enumerate(trials):
                state_vector = source_injection @ trial
                executor = _plane_wave(
                    np.asarray(state_vector, dtype=np.complex128),
                    reciprocal_index,
                    run_spec.spatial_shape,
                )
                symbolic_vector = np.asarray(
                    state_vector,
                    dtype=np.complex128,
                )
                for _ in range(steps):
                    executor = apply_factory_step(factory, executor)
                    symbolic_vector = symbol @ symbolic_vector
                executor_vector = _readback_plane_wave(
                    executor,
                    reciprocal_index,
                    run_spec.spatial_shape,
                )
                executor_readout = readout @ executor_vector
                symbolic_readout = readout @ symbolic_vector
                difference[:, trial_index] = executor_readout - symbolic_readout
            differences.append((reciprocal_index, steps, difference))
    return _build_source_readout_bridge_audit_from_differences(
        branch=branch,
        factory_sha=payload.factory_sha,
        transition_sha=transition_record.transition.transition_sha,
        dynamics_certificate_sha=dynamics_certificate_sha,
        run_spec=run_spec,
        registry_entry=registry_entry,
        differences=tuple(differences),
    )


def _shell_phase_map(
    shell: EndpointShellManifest,
    response_grid: ResponseKGridManifest,
) -> dict[tuple[int, ...], float]:
    if shell.shell_spec.response_grid != response_grid:
        raise ValueError("shell and response grids differ")
    result: dict[tuple[int, ...], float] = {}
    grouped: dict[tuple[int, ...], list[float]] = {}
    for audit in shell.point_audits:
        grouped.setdefault(audit.reciprocal_index, []).append(audit.shell_phase)
    for reciprocal_index in response_grid.reciprocal_indices:
        phases = grouped.get(reciprocal_index)
        if not phases:
            raise ValueError("shell lacks a response-grid reciprocal point")
        first = phases[0]
        if any(phase != first for phase in phases[1:]):
            raise ValueError("closure paths disagree on shell phase")
        result[reciprocal_index] = first
    if frozenset(grouped) != frozenset(response_grid.reciprocal_indices):
        raise ValueError("shell contains points outside response grid")
    return result


def _compute_source_readout_response_values(
    branch: Literal["actual", "matched_ablated"],
    transition: VerifiedTransition,
    certificate: VerifiedDynamicsCertificate,
    run_spec: ResponseRunSpec,
    shell: EndpointShellManifest,
) -> FrozenComplexTensor:
    """Compute ``P F_T(M_full;theta_shell) J`` on the canonical k order."""

    if branch not in ("actual", "matched_ablated"):
        raise ValueError("response branch is not closed")
    expected_shape = _preflight_response_values_body(run_spec)
    _preflight_shell_manifest_body(shell)
    transition_record = _reverify_verified_transition(transition)
    certificate_record = _reverify_verified_dynamics_certificate(certificate)
    if transition_record.factory is not certificate_record.factory:
        raise ValueError("response transition/certificate factories differ")
    raw_transition = transition_record.transition
    raw_certificate = certificate_record.certificate
    if raw_certificate.transition != raw_transition:
        raise ValueError("response transition differs from certificate")
    if branch == "actual":
        if shell.actual_transition_sha != raw_transition.transition_sha:
            raise ValueError("response shell transition binding mismatch")
        if shell.actual_dynamics_certificate_sha != raw_certificate.certificate_sha:
            raise ValueError("response shell certificate binding mismatch")
    if shell.shell_spec.candidate_fejer_order != run_spec.fejer_order:
        raise ValueError("response shell/run Fejer order mismatch")
    if shell.shell_spec.control_registry_entry.entry_sha != (
        run_spec.control_registry_entry_sha
    ):
        raise ValueError("response shell/run registry entry mismatch")
    if shell.dt != raw_transition.dt:
        raise ValueError("response shell/transition dt mismatch")
    phases = _shell_phase_map(shell, run_spec.response_grid)
    ordered_matrices: list[np.ndarray] = []
    ordered_metrics: list[np.ndarray] = []
    ordered_phases: list[float] = []
    for reciprocal_index in run_spec.response_grid.reciprocal_indices:
        momentum = np.asarray(
            tuple(
                2.0 * math.pi * float(index) / float(denominator)
                for index, denominator in zip(
                    reciprocal_index,
                    run_spec.response_grid.torus_denominators,
                )
            ),
            dtype=np.float64,
        )
        matrix = transition_symbol(transition, momentum)
        metric = _metric_symbol(
            raw_certificate.stability_metric,
            momentum,
        )
        ordered_matrices.append(matrix)
        ordered_metrics.append(metric)
        ordered_phases.append(phases[reciprocal_index])
    raw_values = _build_fejer_branch_response_values_from_raw(
        branch,
        _response_grid_record(run_spec.response_grid),
        run_spec.fejer_order,
        _basis_record(run_spec.source_basis),
        _basis_record(run_spec.readout_basis),
        ordered_phases,
        tuple(ordered_matrices),
        tuple(ordered_metrics),
    )
    tensor = _frozen_tensor_from_raw_v1(raw_values)
    if tensor.shape != expected_shape:
        raise ValueError("raw Fejer leaf returned the wrong tensor shape")
    return tensor


def _paired_attempt_audit(
    *,
    window_protocol: WindowCalibrationProtocol,
    qualification_sha: str,
    actual_factory_sha: str,
    ablated_factory_sha: str,
    actual_transition: MeasuredTransition,
    ablated_transition: MeasuredTransition,
    actual_dynamics_certificate: DynamicsCertificate,
    ablated_dynamics_certificate: DynamicsCertificate,
    run_spec: ResponseRunSpec,
    shell_outcome: EndpointShellOutcome,
    actual_branch_attempt: Optional[SourceReadoutBranchAttemptAudit],
    ablated_branch_attempt: Optional[SourceReadoutBranchAttemptAudit],
    first_failure: Optional[PairedResponseFailure],
) -> PairedResponseAttemptAudit:
    provisional = PairedResponseAttemptAudit(
        attempt_schema_version=PAIRED_RESPONSE_ATTEMPT_SCHEMA_VERSION,
        window_protocol=window_protocol,
        qualification_sha=qualification_sha,
        actual_factory_sha=actual_factory_sha,
        ablated_factory_sha=ablated_factory_sha,
        actual_transition=actual_transition,
        ablated_transition=ablated_transition,
        actual_dynamics_certificate=actual_dynamics_certificate,
        ablated_dynamics_certificate=ablated_dynamics_certificate,
        run_spec=run_spec,
        shell_outcome=shell_outcome,
        actual_branch_attempt=actual_branch_attempt,
        ablated_branch_attempt=ablated_branch_attempt,
        first_failure=first_failure,
        attempt_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        attempt_sha=canonical_sha(paired_response_attempt_audit_payload(provisional)),
    )


def _paired_outcome(
    attempt: PairedResponseAttemptAudit,
    failure: Optional[PairedResponseFailure],
    paired_response: Optional[PairedFilteredResponse],
) -> PairedResponseOutcome:
    status = (
        BlockStatus(True, None)
        if failure is None
        else BlockStatus(False, _paired_failure_reason(failure))
    )
    provisional = PairedResponseOutcome(
        status=status,
        failure=failure,
        attempt_audit=attempt,
        paired_response=paired_response,
        outcome_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        outcome_sha=canonical_sha(paired_response_outcome_payload(provisional)),
    )


def _paired_prebranch_failure(
    *,
    failure: Literal[
        PairedResponseFailure.QUALIFICATION_INVALID,
        PairedResponseFailure.INPUT_BINDING_INVALID,
    ],
    window_protocol: WindowCalibrationProtocol,
    qualification_sha: str,
    actual_factory_sha: str,
    ablated_factory_sha: str,
    actual_transition: MeasuredTransition,
    ablated_transition: MeasuredTransition,
    actual_dynamics_certificate: DynamicsCertificate,
    ablated_dynamics_certificate: DynamicsCertificate,
    run_spec: ResponseRunSpec,
    shell_outcome: EndpointShellOutcome,
) -> PairedResponseOutcome:
    attempt = _paired_attempt_audit(
        window_protocol=window_protocol,
        qualification_sha=qualification_sha,
        actual_factory_sha=actual_factory_sha,
        ablated_factory_sha=ablated_factory_sha,
        actual_transition=actual_transition,
        ablated_transition=ablated_transition,
        actual_dynamics_certificate=actual_dynamics_certificate,
        ablated_dynamics_certificate=ablated_dynamics_certificate,
        run_spec=run_spec,
        shell_outcome=shell_outcome,
        actual_branch_attempt=None,
        ablated_branch_attempt=None,
        first_failure=failure,
    )
    return _paired_outcome(attempt, failure, None)


def _expected_paired_outcome(
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    qualified_ablation: VerifiedCertificateBackedQualification,
    actual_transition: VerifiedTransition,
    ablated_transition: VerifiedTransition,
    actual_certificate: VerifiedDynamicsCertificate,
    ablated_certificate: VerifiedDynamicsCertificate,
    run_spec: ResponseRunSpec,
    shell: VerifiedEndpointShellOutcome,
) -> PairedResponseOutcome:
    """Recompute one indivisible actual/ablated response evidence graph."""

    _preflight_bridge_output_body(run_spec)
    _preflight_response_values_body(run_spec)
    registry_view = _reverify_verified_control_registry(registry)
    protocol_view = _reverify_verified_window_calibration_protocol(protocol)
    qualification_view = _reverify_verified_certificate_backed_qualification(
        qualified_ablation
    )
    actual_transition_view = _reverify_verified_transition(actual_transition)
    ablated_transition_view = _reverify_verified_transition(ablated_transition)
    actual_certificate_view = _reverify_verified_dynamics_certificate(
        actual_certificate
    )
    ablated_certificate_view = _reverify_verified_dynamics_certificate(
        ablated_certificate
    )
    shell_view = _reverify_verified_endpoint_shell_outcome(shell)

    qualification_outcome = qualification_view.outcome
    qualification_evidence = qualification_outcome.evidence
    construction = qualification_view.construction
    if qualification_evidence is None or construction.pair is None:
        raise ValueError("live qualification lacks matched-pair evidence")
    actual_factory = construction.pair.actual
    ablated_factory = construction.pair.ablated
    actual_factory_view = _reverify_verified_factory(actual_factory)
    ablated_factory_view = _reverify_verified_factory(ablated_factory)
    raw_actual_transition = actual_transition_view.transition
    raw_ablated_transition = ablated_transition_view.transition
    raw_actual_certificate = actual_certificate_view.certificate
    raw_ablated_certificate = ablated_certificate_view.certificate
    qualified_ablated_certificate = _reverify_verified_dynamics_certificate(
        qualification_view.certificate
    ).certificate
    shell_outcome = shell_view.outcome
    protocol_body = protocol_view.protocol
    qualification_sha = qualification_outcome.outcome_sha

    qualification_invalid = (
        qualified_ablated_certificate != raw_ablated_certificate
        or qualification_evidence.verified_certificate_sha
        != raw_ablated_certificate.certificate_sha
        or qualification_evidence.pair_snapshot.actual_factory
        != actual_factory_view.factory
        or qualification_evidence.pair_snapshot.ablated_factory
        != ablated_factory_view.factory
        or qualification_evidence.pair_snapshot.ablation_manifest
        != construction.pair.manifest
    )
    if qualification_invalid:
        return _paired_prebranch_failure(
            failure=PairedResponseFailure.QUALIFICATION_INVALID,
            window_protocol=protocol_body,
            qualification_sha=qualification_sha,
            actual_factory_sha=actual_factory_view.factory.factory_sha,
            ablated_factory_sha=ablated_factory_view.factory.factory_sha,
            actual_transition=raw_actual_transition,
            ablated_transition=raw_ablated_transition,
            actual_dynamics_certificate=raw_actual_certificate,
            ablated_dynamics_certificate=raw_ablated_certificate,
            run_spec=run_spec,
            shell_outcome=shell_outcome,
        )

    try:
        if protocol_view.registry is not registry:
            raise ValueError("window protocol is not bound to this registry")
        if shell_view.registry is not registry or shell_view.protocol is not protocol:
            raise ValueError("endpoint shell registry/protocol binding mismatch")
        if (
            actual_transition_view.factory is not actual_factory
            or actual_certificate_view.factory is not actual_factory
            or ablated_transition_view.factory is not ablated_factory
            or ablated_certificate_view.factory is not ablated_factory
        ):
            raise ValueError("paired transition/certificate factory binding mismatch")
        if (
            raw_actual_certificate.transition != raw_actual_transition
            or raw_ablated_certificate.transition != raw_ablated_transition
        ):
            raise ValueError("paired certificate transition body mismatch")
        if (
            shell_view.factory is not actual_factory
            or shell_view.transition is not actual_transition
            or shell_view.certificate is not actual_certificate
        ):
            raise ValueError("endpoint shell live input binding mismatch")
        if not shell_outcome.status.defined or shell_outcome.shell is None:
            raise ValueError("paired response requires a successful endpoint shell")
        verified_run_spec = verify_response_run_spec(run_spec, protocol)
        if verified_run_spec is not run_spec:
            raise ValueError("run spec verifier did not preserve the raw body")
        _protocol_entry, registry_entry = _protocol_entry_for_spec(
            run_spec,
            protocol_view,
        )
        control_index = CONTROL_ORDER.index(registry_entry.control_id)
        registry_factory = registry_view.controls[control_index].factory
        if registry_factory is not actual_factory:
            raise ValueError("paired actual factory is not the closed control factory")
        if run_spec.source_basis != registry_entry.source_basis or (
            run_spec.readout_basis != registry_entry.readout_basis
        ):
            raise ValueError("paired source/readout basis differs from registry")
        if (
            raw_actual_transition.state_schema_id != run_spec.state_schema_id
            or raw_ablated_transition.state_schema_id != run_spec.state_schema_id
            or raw_actual_transition.channel_order != run_spec.channel_order
            or raw_ablated_transition.channel_order != run_spec.channel_order
            or raw_actual_transition.spatial_shape != run_spec.spatial_shape
            or raw_ablated_transition.spatial_shape != run_spec.spatial_shape
            or raw_actual_transition.dt != raw_ablated_transition.dt
        ):
            raise ValueError("paired transition state contract mismatch")
        shell_manifest = shell_outcome.shell
        if (
            shell_manifest.shell_spec.control_registry_entry != registry_entry
            or shell_manifest.shell_spec.response_grid != run_spec.response_grid
            or shell_manifest.shell_spec.candidate_fejer_order != run_spec.fejer_order
            or shell_manifest.dt != raw_actual_transition.dt
        ):
            raise ValueError("paired shell/run binding mismatch")
    except (TypeError, ValueError):
        return _paired_prebranch_failure(
            failure=PairedResponseFailure.INPUT_BINDING_INVALID,
            window_protocol=protocol_body,
            qualification_sha=qualification_sha,
            actual_factory_sha=actual_factory_view.factory.factory_sha,
            ablated_factory_sha=ablated_factory_view.factory.factory_sha,
            actual_transition=raw_actual_transition,
            ablated_transition=raw_ablated_transition,
            actual_dynamics_certificate=raw_actual_certificate,
            ablated_dynamics_certificate=raw_ablated_certificate,
            run_spec=run_spec,
            shell_outcome=shell_outcome,
        )

    actual_attempt, ablated_attempt, failure = _run_atomic_paired_branch_attempts(
        actual_values_call=lambda: _compute_source_readout_response_values(
            "actual",
            actual_transition,
            actual_certificate,
            run_spec,
            shell_manifest,
        ),
        actual_bridge_call=lambda: _measure_source_readout_bridge(
            branch="actual",
            factory=actual_factory,
            transition=actual_transition,
            dynamics_certificate_sha=(raw_actual_certificate.certificate_sha),
            run_spec=run_spec,
            registry_entry=registry_entry,
        ),
        ablated_values_call=lambda: _compute_source_readout_response_values(
            "matched_ablated",
            ablated_transition,
            ablated_certificate,
            run_spec,
            shell_manifest,
        ),
        ablated_bridge_call=lambda: _measure_source_readout_bridge(
            branch="matched_ablated",
            factory=ablated_factory,
            transition=ablated_transition,
            dynamics_certificate_sha=(raw_ablated_certificate.certificate_sha),
            run_spec=run_spec,
            registry_entry=registry_entry,
        ),
    )
    if failure is not None:
        attempt = _paired_attempt_audit(
            window_protocol=protocol_body,
            qualification_sha=qualification_sha,
            actual_factory_sha=actual_factory_view.factory.factory_sha,
            ablated_factory_sha=ablated_factory_view.factory.factory_sha,
            actual_transition=raw_actual_transition,
            ablated_transition=raw_ablated_transition,
            actual_dynamics_certificate=raw_actual_certificate,
            ablated_dynamics_certificate=raw_ablated_certificate,
            run_spec=run_spec,
            shell_outcome=shell_outcome,
            actual_branch_attempt=actual_attempt,
            ablated_branch_attempt=ablated_attempt,
            first_failure=failure,
        )
        return _paired_outcome(attempt, failure, None)

    if ablated_attempt is None:
        raise AssertionError("successful paired stages lost ablated evidence")
    if (
        actual_attempt.response_values is None
        or actual_attempt.bridge_audit is None
        or ablated_attempt.response_values is None
        or ablated_attempt.bridge_audit is None
    ):
        raise AssertionError("successful paired stages are incomplete")
    actual_response = _build_source_readout_response_from_values(
        branch="actual",
        factory_sha=actual_factory_view.factory.factory_sha,
        transition_sha=raw_actual_transition.transition_sha,
        dynamics_certificate_sha=raw_actual_certificate.certificate_sha,
        run_spec=run_spec,
        shell_manifest_sha=shell_manifest.shell_manifest_sha,
        bridge_audit=actual_attempt.bridge_audit,
        values=actual_attempt.response_values,
    )
    ablated_response = _build_source_readout_response_from_values(
        branch="matched_ablated",
        factory_sha=ablated_factory_view.factory.factory_sha,
        transition_sha=raw_ablated_transition.transition_sha,
        dynamics_certificate_sha=raw_ablated_certificate.certificate_sha,
        run_spec=run_spec,
        shell_manifest_sha=shell_manifest.shell_manifest_sha,
        bridge_audit=ablated_attempt.bridge_audit,
        values=ablated_attempt.response_values,
    )
    provisional_pair = PairedFilteredResponse(
        pair_schema_version=PAIRED_RESPONSE_SCHEMA_VERSION,
        ablation_manifest_sha=construction.pair.manifest.manifest_sha,
        qualification_sha=qualification_sha,
        actual_dynamics_certificate=raw_actual_certificate,
        ablated_dynamics_certificate=raw_ablated_certificate,
        actual=actual_response,
        ablated=ablated_response,
        run_spec=run_spec,
        shell_manifest=shell_manifest,
        pair_sha=_ZERO_SHA,
    )
    paired = replace(
        provisional_pair,
        pair_sha=canonical_sha(paired_filtered_response_payload(provisional_pair)),
    )
    attempt = _paired_attempt_audit(
        window_protocol=protocol_body,
        qualification_sha=qualification_sha,
        actual_factory_sha=actual_factory_view.factory.factory_sha,
        ablated_factory_sha=ablated_factory_view.factory.factory_sha,
        actual_transition=raw_actual_transition,
        ablated_transition=raw_ablated_transition,
        actual_dynamics_certificate=raw_actual_certificate,
        ablated_dynamics_certificate=raw_ablated_certificate,
        run_spec=run_spec,
        shell_outcome=shell_outcome,
        actual_branch_attempt=actual_attempt,
        ablated_branch_attempt=ablated_attempt,
        first_failure=None,
    )
    return _paired_outcome(attempt, None, paired)


def _verify_paired_declared_hashes(
    outcome: PairedResponseOutcome,
) -> None:
    attempt = outcome.attempt_audit
    for branch_attempt in (
        attempt.actual_branch_attempt,
        attempt.ablated_branch_attempt,
    ):
        if branch_attempt is None:
            continue
        if branch_attempt.attempt_sha != canonical_sha(
            source_readout_branch_attempt_audit_payload(branch_attempt)
        ):
            raise ValueError("paired branch attempt SHA mismatch")
    paired = outcome.paired_response
    if paired is not None:
        for response in (paired.actual, paired.ablated):
            if response.response_sha != canonical_sha(
                source_readout_response_payload(response)
            ):
                raise ValueError("source/readout response SHA mismatch")
        if paired.pair_sha != canonical_sha(paired_filtered_response_payload(paired)):
            raise ValueError("paired response SHA mismatch")
    if attempt.attempt_sha != canonical_sha(
        paired_response_attempt_audit_payload(attempt)
    ):
        raise ValueError("paired attempt SHA mismatch")
    if outcome.outcome_sha != canonical_sha(paired_response_outcome_payload(outcome)):
        raise ValueError("paired outcome SHA mismatch")


def _hydrate_paired_inputs_from_raw(
    outcome: PairedResponseOutcome,
    registry: VerifiedControlRegistry,
    protocol: VerifiedWindowCalibrationProtocol,
    qualified_ablation: VerifiedCertificateBackedQualification,
) -> tuple[object, ...]:
    """Recover every live input from the recursively bound raw attempt."""

    _preflight_paired_outcome_body(outcome)
    _verify_paired_declared_hashes(outcome)
    qualification_view = _reverify_verified_certificate_backed_qualification(
        qualified_ablation
    )
    construction = qualification_view.construction
    if construction.pair is None:
        raise ValueError("live qualification lacks a matched construction")
    registry_view = _reverify_verified_control_registry(registry)
    protocol_view = _reverify_verified_window_calibration_protocol(protocol)
    if protocol_view.registry is not registry:
        raise ValueError("window protocol is not bound to this registry")
    control_id = outcome.attempt_audit.run_spec.control_registry_entry_sha
    matches = tuple(
        entry.control_id
        for entry in registry_view.registry.entries
        if entry.entry_sha == control_id
    )
    if len(matches) != 1:
        raise ValueError("paired raw run spec registry binding is not unique")
    selected_control = matches[0]
    actual_factory = construction.pair.actual
    ablated_factory = construction.pair.ablated
    actual_authority = issue_synthetic_prestructure_authority(
        registry_view.parent,
        registry,
        selected_control,
        construction,
        "actual",
    )
    ablated_authority = issue_synthetic_prestructure_authority(
        registry_view.parent,
        registry,
        selected_control,
        construction,
        "matched_ablated",
    )
    attempt = outcome.attempt_audit
    live_actual_transition = verify_measured_transition(
        attempt.actual_transition,
        actual_factory,
        actual_authority,
    )
    live_ablated_transition = verify_measured_transition(
        attempt.ablated_transition,
        ablated_factory,
        ablated_authority,
    )
    live_actual_certificate = verify_dynamics_certificate(
        attempt.actual_dynamics_certificate,
        actual_factory,
        actual_authority,
    )
    live_ablated_certificate = verify_dynamics_certificate(
        attempt.ablated_dynamics_certificate,
        ablated_factory,
        ablated_authority,
    )
    raw_reference = attempt.shell_outcome.reference_outcome
    live_reference = verify_endpoint_reference_outcome(
        raw_reference,
        registry,
        protocol,
        actual_factory,
        live_actual_transition,
        live_actual_certificate,
    )
    live_shell = verify_endpoint_shell_outcome(
        attempt.shell_outcome,
        registry,
        protocol,
        live_reference,
        actual_factory,
        live_actual_transition,
        live_actual_certificate,
    )
    verify_response_run_spec(attempt.run_spec, protocol)
    return (
        registry,
        protocol,
        qualified_ablation,
        live_actual_transition,
        live_ablated_transition,
        live_actual_certificate,
        live_ablated_certificate,
        attempt.run_spec,
        live_shell,
    )


def compute_fejer_filtered_response(
    transition: np.ndarray,
    metric: np.ndarray,
    shell_phase: float,
    order: int,
    source_injection: np.ndarray,
    readout: np.ndarray,
) -> np.ndarray:
    """Evaluate the frozen Fejér polynomial through a whitened Schur path.

    Only scalar powers of Schur eigenvalues are formed.  The function never
    takes powers of ``P M J`` and never exports a time-step operator.
    """

    matrix = _strict_complex_matrix(
        transition,
        "transition",
        square=True,
    )
    gram = _strict_complex_matrix(metric, "metric", square=True)
    source = _strict_complex_matrix(source_injection, "source_injection")
    projection = _strict_complex_matrix(readout, "readout")
    state_count = matrix.shape[0]
    if gram.shape != matrix.shape:
        raise ValueError("metric and transition shapes differ")
    if source.shape[0] != state_count:
        raise ValueError("source injection state axis mismatch")
    if projection.shape[1] != state_count:
        raise ValueError("readout state axis mismatch")
    theta = _finite_float(shell_phase, "shell_phase")
    if not -math.pi <= theta <= math.pi:
        raise ValueError("shell_phase is outside the principal interval")
    closed_order = _closed_order(order)
    preflight_fejer_work(
        n_k=1,
        n_state=state_count,
        order=closed_order,
    )
    sqrt_metric, inverse_sqrt = _hermitian_sqrt_pair(gram)
    whitened = sqrt_metric @ matrix @ inverse_sqrt

    from scipy.linalg import schur

    triangular, unitary = schur(whitened, output="complex")
    triangular = np.asarray(triangular, dtype=np.complex128)
    unitary = np.asarray(unitary, dtype=np.complex128)
    off_diagonal = triangular - np.diag(np.diag(triangular))
    if float(np.linalg.norm(off_diagonal, 2)) > 1.0e-10:
        raise ValueError("metric-unitary Schur form is not diagonal enough")
    unitary_residual = float(
        np.linalg.norm(
            unitary.conj().T @ unitary - np.eye(state_count),
            2,
        )
    )
    reconstruction_residual = float(
        np.linalg.norm(
            unitary @ triangular @ unitary.conj().T - whitened,
            2,
        )
    )
    if max(unitary_residual, reconstruction_residual) > 1.0e-10:
        raise ValueError("Schur functional-calculus residual failed")
    scalars = np.asarray(
        tuple(
            _fejer_scalar(complex(value), theta, closed_order)
            for value in np.diag(triangular)
        ),
        dtype=np.complex128,
    )
    filtered_whitened = (unitary @ np.diag(scalars) @ unitary.conj().T).astype(
        np.complex128
    )
    filtered = inverse_sqrt @ filtered_whitened @ sqrt_metric
    result = projection @ filtered @ source
    return np.asarray(result, dtype=np.complex128)


class _OpaqueOutcomeBase:
    __slots__ = ()

    def __new__(cls, *args: object, **kwargs: object):
        if not args or args[0] is not _ISSUANCE_TOKEN:
            raise TypeError(f"{cls.__name__} is module-issued only")
        return super().__new__(cls)


class VerifiedEndpointReferenceOutcome(_OpaqueOutcomeBase):
    __slots__ = ("__outcome", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        outcome: EndpointReferenceOutcome,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("reference outcome is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedEndpointReferenceOutcome__outcome",
            outcome,
        )
        object.__setattr__(
            self,
            "_VerifiedEndpointReferenceOutcome__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedEndpointReferenceOutcome__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedEndpointReferenceOutcome is immutable")

    @property
    def outcome(self) -> EndpointReferenceOutcome:
        return _reverify_verified_endpoint_reference_outcome(self).outcome

    @property
    def reference(self) -> Optional[EndpointReferenceProjector]:
        return self.outcome.reference


class VerifiedEndpointShellOutcome(_OpaqueOutcomeBase):
    __slots__ = ("__outcome", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        outcome: EndpointShellOutcome,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("shell outcome is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedEndpointShellOutcome__outcome",
            outcome,
        )
        object.__setattr__(
            self,
            "_VerifiedEndpointShellOutcome__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedEndpointShellOutcome__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedEndpointShellOutcome is immutable")

    @property
    def outcome(self) -> EndpointShellOutcome:
        return _reverify_verified_endpoint_shell_outcome(self).outcome

    @property
    def shell(self) -> Optional[EndpointShellManifest]:
        return self.outcome.shell


class VerifiedPairedResponseOutcome(_OpaqueOutcomeBase):
    __slots__ = ("__outcome", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        outcome: PairedResponseOutcome,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("paired outcome is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedPairedResponseOutcome__outcome",
            outcome,
        )
        object.__setattr__(
            self,
            "_VerifiedPairedResponseOutcome__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedPairedResponseOutcome__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedPairedResponseOutcome is immutable")

    @property
    def outcome(self) -> PairedResponseOutcome:
        return _reverify_verified_paired_response_outcome(self).outcome

    @property
    def paired_response(self) -> Optional[PairedFilteredResponse]:
        return self.outcome.paired_response


# Authority replayers are installed below the endpoint/paired builders.  The
# temporary declarations make property resolution explicit without exposing a
# caller-settable registration hook.
def _reverify_verified_endpoint_reference_outcome(
    wrapper: VerifiedEndpointReferenceOutcome,
) -> "_ReferenceAuthority":
    return _reverify_reference_authority(wrapper)


def _reverify_verified_endpoint_shell_outcome(
    wrapper: VerifiedEndpointShellOutcome,
) -> "_ShellAuthority":
    return _reverify_shell_authority(wrapper)


def _reverify_verified_paired_response_outcome(
    wrapper: VerifiedPairedResponseOutcome,
) -> "_PairedAuthority":
    return _reverify_paired_authority(wrapper)


@dataclass(frozen=True)
class _ReferenceAuthority:
    outcome: EndpointReferenceOutcome
    registry: VerifiedControlRegistry
    protocol: VerifiedWindowCalibrationProtocol
    factory: VerifiedFactory
    transition: VerifiedTransition
    certificate: VerifiedDynamicsCertificate
    body_digest: str
    seal: str


@dataclass(frozen=True)
class _ShellAuthority:
    outcome: EndpointShellOutcome
    reference: VerifiedEndpointReferenceOutcome
    registry: VerifiedControlRegistry
    protocol: VerifiedWindowCalibrationProtocol
    factory: VerifiedFactory
    transition: VerifiedTransition
    certificate: VerifiedDynamicsCertificate
    body_digest: str
    seal: str


@dataclass(frozen=True)
class _PairedAuthority:
    outcome: PairedResponseOutcome
    inputs: tuple[object, ...]
    body_digest: str
    seal: str


def _freeze_response_call_graph(
    root: Callable,
    *,
    _partial_type=functools.partial,
) -> object:
    """Clone every reachable project function into private globals.

    This closes public module-global rebinding and ordinary raw-object
    substitution.  Arbitrary same-process mutation through direct access to a
    private function's ``__globals__`` or closure cells remains part of the
    trusted Python interpreter boundary, as it does for the upstream
    certificate authorities.  Third-party callable internals are likewise
    part of that Python TCB.
    """

    function_memo: dict[int, Callable] = {}
    module_memo: dict[tuple[int, tuple[str, ...]], object] = {}

    def referenced_code_names(code: types.CodeType) -> tuple[str, ...]:
        names = list(code.co_names)
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                names.extend(referenced_code_names(constant))
        return tuple(dict.fromkeys(names))

    def freeze_value(
        value: object,
        referenced_names: tuple[str, ...] = (),
    ) -> object:
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if type(value) is _partial_type:
            keywords = value.keywords or {}
            return _partial_type(
                freeze_value(value.func),
                *(freeze_value(item) for item in value.args),
                **{key: freeze_value(item) for key, item in keywords.items()},
            )
        if inspect.ismodule(value):
            module_values = vars(value)
            key = (id(value), referenced_names)
            cached_module = module_memo.get(key)
            if cached_module is not None:
                return cached_module
            proxy = types.SimpleNamespace()
            module_memo[key] = proxy
            for name in referenced_names:
                if name in module_values:
                    setattr(
                        proxy,
                        name,
                        freeze_value(
                            module_values[name],
                            referenced_names,
                        ),
                    )
            return proxy
        if type(value) is tuple:
            return tuple(freeze_value(item) for item in value)
        if type(value) is list:
            return [freeze_value(item) for item in value]
        if type(value) is dict:
            return {key: freeze_value(item) for key, item in value.items()}
        return value

    def freeze_closure_value(
        value: object,
        referenced_names: tuple[str, ...],
    ) -> object:
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if type(value) is _partial_type:
            return freeze_value(value)
        if inspect.ismodule(value):
            return freeze_value(value, referenced_names)
        if type(value) is tuple:
            return tuple(freeze_closure_value(item, referenced_names) for item in value)
        return value

    def make_cell(value: object) -> object:
        def read_cell() -> object:
            return value

        return read_cell.__closure__[0]

    def freeze_function(function: Callable) -> Callable:
        cached = function_memo.get(id(function))
        if cached is not None:
            return cached
        source_globals = function.__globals__
        builtins_body = source_globals.get("__builtins__", {})
        private_builtins = (
            dict(builtins_body)
            if type(builtins_body) is dict
            else dict(vars(builtins_body))
        )
        private_globals: dict[str, object] = {
            "__builtins__": private_builtins,
            "__name__": source_globals.get("__name__", __name__),
            "__package__": source_globals.get("__package__", __package__),
        }
        source_closure = function.__closure__
        private_cells = (
            None
            if source_closure is None
            else tuple(make_cell(None) for _ in source_closure)
        )
        clone = types.FunctionType(
            function.__code__,
            private_globals,
            function.__name__,
            None,
            private_cells,
        )
        function_memo[id(function)] = clone
        referenced_names = referenced_code_names(function.__code__)
        if source_closure is not None:
            assert private_cells is not None
            for private_cell, source_cell in zip(private_cells, source_closure):
                private_cell.cell_contents = freeze_closure_value(
                    source_cell.cell_contents,
                    referenced_names,
                )
        for name in referenced_names:
            if name in source_globals:
                private_globals[name] = freeze_value(
                    source_globals[name],
                    referenced_names,
                )
        clone.__defaults__ = (
            None
            if function.__defaults__ is None
            else tuple(
                freeze_value(item, referenced_names) for item in function.__defaults__
            )
        )
        clone.__kwdefaults__ = (
            None
            if function.__kwdefaults__ is None
            else {
                key: freeze_value(item, referenced_names)
                for key, item in function.__kwdefaults__.items()
            }
        )
        return clone

    return functools.partial(freeze_function(root))


_closed_authority_preflight = _freeze_response_call_graph(
    _preflight_response_evidence_body
)
_closed_authority_dataclass_items = _freeze_response_call_graph(_exact_dataclass_items)


def _make_authority_structural_codec(
    *,
    preflight: Callable,
    dataclass_items: Callable,
    canonical_hash: Callable = canonical_sha,
    type_fn: Callable = type,
    getattr_fn: Callable = getattr,
    isinstance_fn: Callable = isinstance,
    enum_type: type = Enum,
    fraction_type: type = Fraction,
    isfinite: Callable = math.isfinite,
    sorted_fn: Callable = sorted,
    all_fn: Callable = all,
    frozenset_type: type = frozenset,
    str_type: type = str,
    bool_type: type = bool,
    int_type: type = int,
    float_type: type = float,
    tuple_type: type = tuple,
    list_type: type = list,
    dict_type: type = dict,
    type_error: type[Exception] = TypeError,
    value_error: type[Exception] = ValueError,
) -> tuple[Callable[[object], str], Callable[[str, str], str]]:
    def normalize(value):
        value_type = type_fn(value)
        fields = getattr_fn(value_type, "__dataclass_fields__", None)
        if fields is not None:
            items = dataclass_items(value, "authority record", fields)
            return {
                "__record__": (f"{value_type.__module__}.{value_type.__qualname__}"),
                "fields": [[name, normalize(item)] for name, item in items],
            }
        if isinstance_fn(value, enum_type):
            return {
                "__enum__": (f"{value_type.__module__}.{value_type.__qualname__}"),
                "value": normalize(value.value),
            }
        if isinstance_fn(value, fraction_type):
            return {
                "__fraction__": [value.numerator, value.denominator],
            }
        if value is None or value_type in (str_type, bool_type, int_type):
            return value
        if value_type is float_type:
            if not isfinite(value):
                raise value_error("authority body contains a non-finite float")
            return {"__fp64_hex__": value.hex()}
        if value_type is tuple_type:
            return {
                "__tuple__": [normalize(item) for item in value],
            }
        if value_type is list_type:
            return {
                "__list__": [normalize(item) for item in value],
            }
        if value_type is dict_type:
            if not all_fn(type_fn(key) is str_type for key in value):
                raise type_error("authority mapping keys must be strings")
            return {
                "__mapping__": [
                    [key, normalize(value[key])] for key in sorted_fn(value)
                ],
            }
        raise type_error(
            f"authority body contains unsupported {value_type.__qualname__}"
        )

    def digest(value):
        preflight(value, "authority_structural_body")
        return canonical_hash({"authority_structural_body": normalize(value)})

    def seal(kind, body_digest):
        return canonical_hash(
            {
                "authority_schema_version": kind,
                "structural_body_sha": body_digest,
            }
        )

    return digest, seal


def _make_authority_structural_clone(
    *,
    dataclass_items: Callable,
    type_fn: Callable = type,
    getattr_fn: Callable = getattr,
    isinstance_fn: Callable = isinstance,
    enum_type: type = Enum,
    fraction_type: type = Fraction,
    object_type: type = object,
    str_type: type = str,
    bool_type: type = bool,
    int_type: type = int,
    float_type: type = float,
    complex_type: type = complex,
    bytes_type: type = bytes,
    none_type: type = type(None),
    tuple_type: type = tuple,
    list_type: type = list,
    dict_type: type = dict,
    frozenset_type: type = frozenset,
    set_type: type = set,
    enumerate_fn: Callable = enumerate,
    sorted_fn: Callable = sorted,
    type_error: type[Exception] = TypeError,
    value_error: type[Exception] = ValueError,
) -> Callable[[object], object]:
    """Clone exact authority wires without stdlib dispatch or constructors."""

    atoms = (
        str_type,
        bool_type,
        int_type,
        float_type,
        complex_type,
        bytes_type,
        none_type,
    )

    def clone(value: object) -> object:
        memo: dict[int, object] = {}
        active: set[int] = set_type()

        def copy_value(current: object, path: str) -> object:
            current_type = type_fn(current)
            if current_type in atoms:
                return current
            if isinstance_fn(current, (enum_type, fraction_type)):
                return current
            identity = id(current)
            if identity in active:
                raise value_error(f"{path} contains a cyclic authority wire")
            if identity in memo:
                return memo[identity]

            fields = getattr_fn(current_type, "__dataclass_fields__", None)
            if fields is not None:
                items = dataclass_items(current, path, fields)
                result = object_type.__new__(current_type)
                memo[identity] = result
                active.add(identity)
                try:
                    for name, item in items:
                        object_type.__setattr__(
                            result,
                            name,
                            copy_value(item, f"{path}.{name}"),
                        )
                finally:
                    active.remove(identity)
                return result

            if current_type is tuple_type:
                active.add(identity)
                try:
                    result = tuple_type(
                        copy_value(item, f"{path}[{index}]")
                        for index, item in enumerate_fn(current)
                    )
                finally:
                    active.remove(identity)
                memo[identity] = result
                return result
            if current_type is list_type:
                result_list: list[object] = []
                memo[identity] = result_list
                active.add(identity)
                try:
                    result_list.extend(
                        copy_value(item, f"{path}[{index}]")
                        for index, item in enumerate_fn(current)
                    )
                finally:
                    active.remove(identity)
                return result_list
            if current_type is dict_type:
                result_dict: dict[object, object] = {}
                memo[identity] = result_dict
                active.add(identity)
                try:
                    for key, item in current.items():
                        cloned_key = copy_value(key, f"{path}.key")
                        result_dict[cloned_key] = copy_value(
                            item,
                            f"{path}[{key!r}]",
                        )
                finally:
                    active.remove(identity)
                return result_dict
            if current_type is frozenset_type:
                active.add(identity)
                try:
                    result = frozenset_type(
                        copy_value(item, f"{path}.item") for item in current
                    )
                finally:
                    active.remove(identity)
                memo[identity] = result
                return result
            raise type_error(
                f"{path} has unsupported exact authority type "
                f"{current_type.__qualname__}"
            )

        return copy_value(value, "$")

    return clone


_authority_structural_clone = _make_authority_structural_clone(
    dataclass_items=_closed_authority_dataclass_items,
)


def _response_authority_binding_digest(
    authority_kind,
    body_digest,
    bindings,
    *,
    canonical_hash=canonical_sha,
    type_fn=type,
    id_fn=id,
    str_type=str,
    tuple_type=tuple,
    type_error=TypeError,
    value_error=ValueError,
):
    """Seal process-local authority identities for one replay-scope proof."""

    if type_fn(authority_kind) is not str_type or not authority_kind:
        raise type_error("response authority kind must be exact nonempty text")
    if (
        type_fn(body_digest) is not str_type
        or _LOWER_SHA.fullmatch(body_digest) is None
    ):
        raise value_error("response authority body digest must be a SHA-256")
    if type_fn(bindings) is not tuple_type or not bindings:
        raise type_error("response authority bindings must be a nonempty tuple")
    return canonical_hash(
        {
            "binding_schema_version": "v3m0.response-authority-binding.v1",
            "authority_kind": authority_kind,
            "body_digest": body_digest,
            "binding_identities": [
                {
                    "exact_type": (
                        f"{type_fn(item).__module__}.{type_fn(item).__qualname__}"
                    ),
                    "identity": id_fn(item),
                }
                for item in bindings
            ],
        }
    )


def _validate_cached_reference_binding(authority):
    """Revalidate every live non-numerical endpoint-reference binding."""

    if type(authority) is not _ReferenceAuthority:
        raise TypeError("cached reference authority has the wrong exact type")
    spec = authority.outcome.reference_spec
    (
        _registry_view,
        protocol_view,
        _factory_view,
        transition_record,
        registry_entry,
        protocol_entry,
    ) = _bind_reference_inputs(
        authority.registry,
        authority.protocol,
        authority.factory,
        authority.transition,
        authority.certificate,
        spec.control_registry_entry.control_id,
    )
    expected_spec = _expected_reference_spec(
        protocol_view,
        transition_record,
        authority.certificate,
        registry_entry,
        protocol_entry,
        spec.candidate_fejer_order,
    )
    if spec != expected_spec:
        raise ValueError("cached reference authority binding changed")


def _validate_cached_shell_binding(authority):
    """Revalidate shell identities/specification without shell extraction."""

    if type(authority) is not _ShellAuthority:
        raise TypeError("cached shell authority has the wrong exact type")
    reference_authority = _reverify_verified_endpoint_reference_outcome(
        authority.reference
    )
    if (
        reference_authority.registry is not authority.registry
        or reference_authority.protocol is not authority.protocol
        or reference_authority.factory is not authority.factory
        or reference_authority.transition is not authority.transition
        or reference_authority.certificate is not authority.certificate
    ):
        raise ValueError("cached shell inputs differ from reference authority")
    outcome = authority.outcome
    if outcome.reference_outcome != reference_authority.outcome:
        raise ValueError("cached shell reference snapshot changed")
    spec = outcome.attempt_audit.shell_spec
    verified_spec = verify_endpoint_shell_spec(spec, authority.protocol)
    expected_spec = _legacy_build_endpoint_shell_spec(
        authority.protocol,
        authority.reference,
    )
    if verified_spec != expected_spec:
        raise ValueError("cached shell specification binding changed")
    transition_record = _reverify_verified_transition(authority.transition)
    certificate_record = _reverify_verified_dynamics_certificate(authority.certificate)
    if (
        transition_record.factory is not authority.factory
        or certificate_record.factory is not authority.factory
        or certificate_record.certificate.transition != transition_record.transition
    ):
        raise ValueError("cached shell dynamics binding changed")
    shell = outcome.shell
    if shell is not None and (
        shell.shell_spec != spec
        or shell.actual_factory_sha != transition_record.transition.factory_sha
        or shell.actual_transition_sha != transition_record.transition.transition_sha
        or shell.actual_dynamics_certificate_sha
        != certificate_record.certificate.certificate_sha
        or shell.dt != transition_record.transition.dt
    ):
        raise ValueError("cached shell manifest binding changed")


def _validate_cached_paired_binding(authority):
    """Revalidate paired input authorities without response recomputation."""

    if type(authority) is not _PairedAuthority:
        raise TypeError("cached paired authority has the wrong exact type")
    if type(authority.inputs) is not tuple or len(authority.inputs) != 9:
        raise ValueError("cached paired authority inputs are incomplete")
    (
        registry,
        protocol,
        qualified_ablation,
        actual_transition,
        ablated_transition,
        actual_certificate,
        ablated_certificate,
        run_spec,
        shell,
    ) = authority.inputs
    if type(qualified_ablation) is not VerifiedCertificateBackedQualification:
        raise TypeError("cached paired qualification has the wrong exact type")
    _preflight_bridge_output_body(run_spec)
    _preflight_response_values_body(run_spec)
    registry_view = _reverify_verified_control_registry(registry)
    protocol_view = _reverify_verified_window_calibration_protocol(protocol)
    qualification_view = _reverify_verified_certificate_backed_qualification(
        qualified_ablation
    )
    actual_transition_view = _reverify_verified_transition(actual_transition)
    ablated_transition_view = _reverify_verified_transition(ablated_transition)
    actual_certificate_view = _reverify_verified_dynamics_certificate(
        actual_certificate
    )
    ablated_certificate_view = _reverify_verified_dynamics_certificate(
        ablated_certificate
    )
    shell_view = _reverify_verified_endpoint_shell_outcome(shell)

    qualification_outcome = qualification_view.outcome
    qualification_evidence = qualification_outcome.evidence
    construction = qualification_view.construction
    if qualification_evidence is None or construction.pair is None:
        raise ValueError("cached paired qualification lost matched evidence")
    actual_factory = construction.pair.actual
    ablated_factory = construction.pair.ablated
    actual_factory_view = _reverify_verified_factory(actual_factory)
    ablated_factory_view = _reverify_verified_factory(ablated_factory)
    raw_actual_transition = actual_transition_view.transition
    raw_ablated_transition = ablated_transition_view.transition
    raw_actual_certificate = actual_certificate_view.certificate
    raw_ablated_certificate = ablated_certificate_view.certificate
    qualified_ablated_certificate = _reverify_verified_dynamics_certificate(
        qualification_view.certificate
    ).certificate
    shell_outcome = shell_view.outcome
    protocol_body = protocol_view.protocol
    outcome = authority.outcome
    attempt = outcome.attempt_audit
    if (
        attempt.window_protocol != protocol_body
        or attempt.qualification_sha != qualification_outcome.outcome_sha
        or attempt.actual_factory_sha != actual_factory_view.factory.factory_sha
        or attempt.ablated_factory_sha != ablated_factory_view.factory.factory_sha
        or attempt.actual_transition != raw_actual_transition
        or attempt.ablated_transition != raw_ablated_transition
        or attempt.actual_dynamics_certificate != raw_actual_certificate
        or attempt.ablated_dynamics_certificate != raw_ablated_certificate
        or attempt.run_spec != run_spec
        or attempt.shell_outcome != shell_outcome
    ):
        raise ValueError("cached paired evidence/input snapshot changed")

    qualification_invalid = (
        qualified_ablated_certificate != raw_ablated_certificate
        or qualification_evidence.verified_certificate_sha
        != raw_ablated_certificate.certificate_sha
        or qualification_evidence.pair_snapshot.actual_factory
        != actual_factory_view.factory
        or qualification_evidence.pair_snapshot.ablated_factory
        != ablated_factory_view.factory
        or qualification_evidence.pair_snapshot.ablation_manifest
        != construction.pair.manifest
    )
    if qualification_invalid:
        if outcome.failure is not PairedResponseFailure.QUALIFICATION_INVALID:
            raise ValueError("cached paired qualification disposition changed")
        return
    if outcome.failure is PairedResponseFailure.QUALIFICATION_INVALID:
        raise ValueError("cached paired qualification disposition changed")

    binding_invalid = False
    try:
        if protocol_view.registry is not registry:
            raise ValueError("window protocol is not bound to this registry")
        if shell_view.registry is not registry or shell_view.protocol is not protocol:
            raise ValueError("endpoint shell registry/protocol binding mismatch")
        if (
            actual_transition_view.factory is not actual_factory
            or actual_certificate_view.factory is not actual_factory
            or ablated_transition_view.factory is not ablated_factory
            or ablated_certificate_view.factory is not ablated_factory
        ):
            raise ValueError("paired transition/certificate factory binding mismatch")
        if (
            raw_actual_certificate.transition != raw_actual_transition
            or raw_ablated_certificate.transition != raw_ablated_transition
        ):
            raise ValueError("paired certificate transition body mismatch")
        if (
            shell_view.factory is not actual_factory
            or shell_view.transition is not actual_transition
            or shell_view.certificate is not actual_certificate
        ):
            raise ValueError("endpoint shell live input binding mismatch")
        if not shell_outcome.status.defined or shell_outcome.shell is None:
            raise ValueError("paired response requires a successful endpoint shell")
        if verify_response_run_spec(run_spec, protocol) is not run_spec:
            raise ValueError("run spec verifier did not preserve the raw body")
        _protocol_entry, registry_entry = _protocol_entry_for_spec(
            run_spec,
            protocol_view,
        )
        control_index = CONTROL_ORDER.index(registry_entry.control_id)
        if registry_view.controls[control_index].factory is not actual_factory:
            raise ValueError("paired actual factory is not the closed control factory")
        if (
            run_spec.source_basis != registry_entry.source_basis
            or run_spec.readout_basis != registry_entry.readout_basis
        ):
            raise ValueError("paired source/readout basis differs from registry")
        if (
            raw_actual_transition.state_schema_id != run_spec.state_schema_id
            or raw_ablated_transition.state_schema_id != run_spec.state_schema_id
            or raw_actual_transition.channel_order != run_spec.channel_order
            or raw_ablated_transition.channel_order != run_spec.channel_order
            or raw_actual_transition.spatial_shape != run_spec.spatial_shape
            or raw_ablated_transition.spatial_shape != run_spec.spatial_shape
            or raw_actual_transition.dt != raw_ablated_transition.dt
        ):
            raise ValueError("paired transition state contract mismatch")
        shell_manifest = shell_outcome.shell
        if (
            shell_manifest.shell_spec.control_registry_entry != registry_entry
            or shell_manifest.shell_spec.response_grid != run_spec.response_grid
            or shell_manifest.shell_spec.candidate_fejer_order != run_spec.fejer_order
            or shell_manifest.dt != raw_actual_transition.dt
        ):
            raise ValueError("paired shell/run binding mismatch")
    except (TypeError, ValueError):
        binding_invalid = True
    if binding_invalid != (
        outcome.failure is PairedResponseFailure.INPUT_BINDING_INVALID
    ):
        raise ValueError("cached paired input-binding disposition changed")


def _make_closed_reference_authority(
    expected_call,
    preflight_call,
    structural_digest,
    structural_seal,
    *,
    wrapper_type=VerifiedEndpointReferenceOutcome,
    authority_type=_ReferenceAuthority,
    clone=_authority_structural_clone,
    weak_reference=weakref.ref,
    lock_builder=threading.RLock,
    issuance_token=_ISSUANCE_TOKEN,
    type_fn=type,
    id_fn=id,
    object_type=object,
    getattr_fn=getattr,
    type_error=TypeError,
    value_error=ValueError,
    attribute_error=AttributeError,
    authority_schema=("v3m0.verified-endpoint-reference-outcome.v2"),
    binding_validator=None,
    authority_binding_digest=_response_authority_binding_digest,
    cached_replay_is_valid=_cached_replay_is_valid,
    record_successful_replay=_record_successful_replay,
):
    live = {}
    lock = lock_builder()
    namespace = "rulespace_v3.response.VerifiedEndpointReferenceOutcome"

    if binding_validator is None:

        def binding_validator(_authority):
            return None

    def exposed_bodies(raw):
        return raw, getattr_fn(raw, "reference", None)

    def authority_digest(authority):
        return authority_binding_digest(
            "endpoint-reference",
            authority.body_digest,
            (
                authority.outcome,
                authority.registry,
                authority.protocol,
                authority.factory,
                authority.transition,
                authority.certificate,
            ),
        )

    def authority_view(authority):
        return authority_type(
            outcome=clone(authority.outcome),
            registry=authority.registry,
            protocol=authority.protocol,
            factory=authority.factory,
            transition=authority.transition,
            certificate=authority.certificate,
            body_digest=authority.body_digest,
            seal=authority.seal,
        )

    def issue(
        registry,
        protocol,
        factory,
        transition,
        certificate,
        control_id,
        order,
        raw,
    ):
        if raw is not None:
            preflight_call(raw)
        expected = expected_call(
            registry,
            protocol,
            factory,
            transition,
            certificate,
            control_id,
            order,
        )
        preflight_call(expected)
        expected_digest = structural_digest(expected)
        if raw is not None and structural_digest(raw) != expected_digest:
            raise value_error("raw endpoint reference outcome differs from replay")
        authority_snapshot = clone(expected)
        exposed_snapshot = clone(expected)
        preflight_call(authority_snapshot)
        preflight_call(exposed_snapshot)
        body_digest = structural_digest(authority_snapshot)
        wrapper_seal = structural_seal(authority_schema, body_digest)
        wrapper = wrapper_type(
            issuance_token,
            exposed_snapshot,
            wrapper_seal,
        )
        identity = id_fn(wrapper)
        authority = authority_type(
            outcome=authority_snapshot,
            registry=registry,
            protocol=protocol,
            factory=factory,
            transition=transition,
            certificate=certificate,
            body_digest=body_digest,
            seal=wrapper_seal,
        )

        def remove(reference, wrapper_id=identity):
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weak_reference(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=issuance_token,
            exposed_bodies=exposed_bodies(exposed_snapshot),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=authority_digest(authority),
        )
        return wrapper

    def reverify(wrapper):
        if type_fn(wrapper) is not wrapper_type:
            raise type_error("endpoint reference requires a module-issued capability")
        with lock:
            current = live.get(id_fn(wrapper))
            if current is None or current[0]() is not wrapper:
                raise value_error("endpoint reference identity is not live")
            authority = current[1]
        try:
            token = object_type.__getattribute__(
                wrapper,
                "_VerifiedEndpointReferenceOutcome__token",
            )
            raw = object_type.__getattribute__(
                wrapper,
                "_VerifiedEndpointReferenceOutcome__outcome",
            )
            wrapper_seal = object_type.__getattribute__(
                wrapper,
                "_VerifiedEndpointReferenceOutcome__seal",
            )
        except attribute_error as exc:
            raise value_error(
                "endpoint reference authority record is incomplete"
            ) from exc
        if token is not issuance_token:
            raise value_error("endpoint reference token mismatch")
        preflight_call(raw)
        preflight_call(authority.outcome)

        def cheap_validator():
            raw_digest = structural_digest(raw)
            snapshot_digest = structural_digest(authority.outcome)
            expected_seal = structural_seal(
                authority_schema,
                authority.body_digest,
            )
            if (
                raw_digest != authority.body_digest
                or snapshot_digest != authority.body_digest
                or wrapper_seal != authority.seal
                or wrapper_seal != expected_seal
            ):
                raise value_error("endpoint reference cached immutable guard mismatch")
            if binding_validator(authority) is not None:
                raise type_error("reference binding validator must return None")

        current_authority_digest = authority_digest(authority)
        if cached_replay_is_valid(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=token,
            exposed_bodies=exposed_bodies(raw),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=current_authority_digest,
            cheap_validator=cheap_validator,
        ):
            return authority_view(authority)
        control_id = authority.outcome.reference_spec.control_registry_entry.control_id
        order = authority.outcome.reference_spec.candidate_fejer_order
        expected = expected_call(
            authority.registry,
            authority.protocol,
            authority.factory,
            authority.transition,
            authority.certificate,
            control_id,
            order,
        )
        preflight_call(expected)
        raw_digest = structural_digest(raw)
        snapshot_digest = structural_digest(authority.outcome)
        expected_digest = structural_digest(expected)
        expected_seal = structural_seal(authority_schema, expected_digest)
        if (
            raw_digest != authority.body_digest
            or snapshot_digest != authority.body_digest
            or expected_digest != authority.body_digest
            or wrapper_seal != authority.seal
            or wrapper_seal != expected_seal
        ):
            raise value_error("endpoint reference immutable snapshot mismatch")
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=token,
            exposed_bodies=exposed_bodies(raw),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=current_authority_digest,
        )
        return authority_view(authority)

    def build(
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
        control_id,
        candidate_fejer_order,
    ):
        return issue(
            registry,
            protocol,
            actual_factory,
            actual_transition,
            actual_certificate,
            control_id,
            candidate_fejer_order,
            None,
        )

    def verify(
        outcome,
        registry,
        protocol,
        actual_factory,
        actual_transition,
        actual_certificate,
    ):
        preflight_call(outcome)
        return issue(
            registry,
            protocol,
            actual_factory,
            actual_transition,
            actual_certificate,
            outcome.reference_spec.control_registry_entry.control_id,
            outcome.reference_spec.candidate_fejer_order,
            outcome,
        )

    def outcome_property(wrapper):
        return reverify(wrapper).outcome

    def reference_property(wrapper):
        return reverify(wrapper).outcome.reference

    return build, verify, issue, reverify, outcome_property, reference_property


def _make_closed_shell_authority(
    expected_call,
    build_spec_call,
    preflight_call,
    structural_digest,
    structural_seal,
    *,
    wrapper_type=VerifiedEndpointShellOutcome,
    authority_type=_ShellAuthority,
    clone=_authority_structural_clone,
    weak_reference=weakref.ref,
    lock_builder=threading.RLock,
    issuance_token=_ISSUANCE_TOKEN,
    type_fn=type,
    id_fn=id,
    object_type=object,
    getattr_fn=getattr,
    type_error=TypeError,
    value_error=ValueError,
    attribute_error=AttributeError,
    authority_schema="v3m0.verified-endpoint-shell-outcome.v2",
    binding_validator=None,
    authority_binding_digest=_response_authority_binding_digest,
    cached_replay_is_valid=_cached_replay_is_valid,
    record_successful_replay=_record_successful_replay,
):
    live = {}
    lock = lock_builder()
    namespace = "rulespace_v3.response.VerifiedEndpointShellOutcome"

    if binding_validator is None:

        def binding_validator(_authority):
            return None

    def exposed_bodies(raw):
        return raw, getattr_fn(raw, "shell", None)

    def authority_digest(authority):
        return authority_binding_digest(
            "endpoint-shell",
            authority.body_digest,
            (
                authority.outcome,
                authority.reference,
                authority.registry,
                authority.protocol,
                authority.factory,
                authority.transition,
                authority.certificate,
            ),
        )

    def authority_view(authority):
        return authority_type(
            outcome=clone(authority.outcome),
            reference=authority.reference,
            registry=authority.registry,
            protocol=authority.protocol,
            factory=authority.factory,
            transition=authority.transition,
            certificate=authority.certificate,
            body_digest=authority.body_digest,
            seal=authority.seal,
        )

    def issue(
        registry,
        protocol,
        reference,
        factory,
        transition,
        certificate,
        shell_spec,
        raw,
    ):
        if raw is not None:
            preflight_call(raw)
        expected = expected_call(
            registry,
            protocol,
            reference,
            factory,
            transition,
            certificate,
            shell_spec,
        )
        preflight_call(expected)
        expected_digest = structural_digest(expected)
        if raw is not None and structural_digest(raw) != expected_digest:
            raise value_error("raw endpoint shell outcome differs from replay")
        authority_snapshot = clone(expected)
        exposed_snapshot = clone(expected)
        preflight_call(authority_snapshot)
        preflight_call(exposed_snapshot)
        body_digest = structural_digest(authority_snapshot)
        wrapper_seal = structural_seal(authority_schema, body_digest)
        wrapper = wrapper_type(
            issuance_token,
            exposed_snapshot,
            wrapper_seal,
        )
        identity = id_fn(wrapper)
        authority = authority_type(
            outcome=authority_snapshot,
            reference=reference,
            registry=registry,
            protocol=protocol,
            factory=factory,
            transition=transition,
            certificate=certificate,
            body_digest=body_digest,
            seal=wrapper_seal,
        )

        def remove(weak, wrapper_id=identity):
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is weak:
                    del live[wrapper_id]

        weak = weak_reference(wrapper, remove)
        with lock:
            live[identity] = (weak, authority)
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=issuance_token,
            exposed_bodies=exposed_bodies(exposed_snapshot),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=authority_digest(authority),
        )
        return wrapper

    def reverify(wrapper):
        if type_fn(wrapper) is not wrapper_type:
            raise type_error("endpoint shell requires a module-issued capability")
        with lock:
            current = live.get(id_fn(wrapper))
            if current is None or current[0]() is not wrapper:
                raise value_error("endpoint shell identity is not live")
            authority = current[1]
        try:
            token = object_type.__getattribute__(
                wrapper,
                "_VerifiedEndpointShellOutcome__token",
            )
            raw = object_type.__getattribute__(
                wrapper,
                "_VerifiedEndpointShellOutcome__outcome",
            )
            wrapper_seal = object_type.__getattribute__(
                wrapper,
                "_VerifiedEndpointShellOutcome__seal",
            )
        except attribute_error as exc:
            raise value_error("endpoint shell authority record is incomplete") from exc
        if token is not issuance_token:
            raise value_error("endpoint shell token mismatch")
        preflight_call(raw)
        preflight_call(authority.outcome)

        def cheap_validator():
            raw_digest = structural_digest(raw)
            snapshot_digest = structural_digest(authority.outcome)
            expected_seal = structural_seal(
                authority_schema,
                authority.body_digest,
            )
            if (
                raw_digest != authority.body_digest
                or snapshot_digest != authority.body_digest
                or wrapper_seal != authority.seal
                or wrapper_seal != expected_seal
            ):
                raise value_error("endpoint shell cached immutable guard mismatch")
            if binding_validator(authority) is not None:
                raise type_error("shell binding validator must return None")

        current_authority_digest = authority_digest(authority)
        if cached_replay_is_valid(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=token,
            exposed_bodies=exposed_bodies(raw),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=current_authority_digest,
            cheap_validator=cheap_validator,
        ):
            return authority_view(authority)
        expected = expected_call(
            authority.registry,
            authority.protocol,
            authority.reference,
            authority.factory,
            authority.transition,
            authority.certificate,
            authority.outcome.attempt_audit.shell_spec,
        )
        preflight_call(expected)
        raw_digest = structural_digest(raw)
        snapshot_digest = structural_digest(authority.outcome)
        expected_digest = structural_digest(expected)
        expected_seal = structural_seal(authority_schema, expected_digest)
        if (
            raw_digest != authority.body_digest
            or snapshot_digest != authority.body_digest
            or expected_digest != authority.body_digest
            or wrapper_seal != authority.seal
            or wrapper_seal != expected_seal
        ):
            raise value_error("endpoint shell immutable snapshot mismatch")
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=token,
            exposed_bodies=exposed_bodies(raw),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=current_authority_digest,
        )
        return authority_view(authority)

    def build_spec(protocol, reference):
        return build_spec_call(protocol, reference)

    def build(
        registry,
        protocol,
        reference,
        actual_factory,
        actual_transition,
        actual_certificate,
        shell_spec,
    ):
        return issue(
            registry,
            protocol,
            reference,
            actual_factory,
            actual_transition,
            actual_certificate,
            shell_spec,
            None,
        )

    def verify(
        outcome,
        registry,
        protocol,
        reference,
        actual_factory,
        actual_transition,
        actual_certificate,
    ):
        preflight_call(outcome)
        return issue(
            registry,
            protocol,
            reference,
            actual_factory,
            actual_transition,
            actual_certificate,
            outcome.attempt_audit.shell_spec,
            outcome,
        )

    def outcome_property(wrapper):
        return reverify(wrapper).outcome

    def shell_property(wrapper):
        return reverify(wrapper).outcome.shell

    return (
        build_spec,
        build,
        verify,
        issue,
        reverify,
        outcome_property,
        shell_property,
    )


def _make_closed_paired_authority(
    expected_call,
    hydrate_call,
    preflight_call,
    structural_digest,
    structural_seal,
    *,
    wrapper_type=VerifiedPairedResponseOutcome,
    authority_type=_PairedAuthority,
    qualification_type=None,
    clone=_authority_structural_clone,
    weak_reference=weakref.ref,
    lock_builder=threading.RLock,
    issuance_token=_ISSUANCE_TOKEN,
    type_fn=type,
    id_fn=id,
    object_type=object,
    getattr_fn=getattr,
    type_error=TypeError,
    value_error=ValueError,
    attribute_error=AttributeError,
    authority_schema="v3m0.verified-paired-response-outcome.v2",
    binding_validator=None,
    authority_binding_digest=_response_authority_binding_digest,
    cached_replay_is_valid=_cached_replay_is_valid,
    record_successful_replay=_record_successful_replay,
):
    live = {}
    lock = lock_builder()
    namespace = "rulespace_v3.response.VerifiedPairedResponseOutcome"

    if binding_validator is None:

        def binding_validator(_authority):
            return None

    def exposed_bodies(raw):
        return raw, getattr_fn(raw, "paired_response", None)

    def authority_digest(authority):
        return authority_binding_digest(
            "paired-response",
            authority.body_digest,
            (authority.outcome, authority.inputs, *authority.inputs),
        )

    def authority_view(authority):
        return authority_type(
            outcome=clone(authority.outcome),
            inputs=authority.inputs,
            body_digest=authority.body_digest,
            seal=authority.seal,
        )

    def require_qualification(value):
        if qualification_type is not None and type_fn(value) is not qualification_type:
            raise type_error(
                "paired response requires a live certificate-backed qualification"
            )

    def issue(
        registry,
        protocol,
        qualified_ablation,
        actual_transition,
        ablated_transition,
        actual_certificate,
        ablated_certificate,
        run_spec,
        shell,
        raw,
    ):
        if raw is not None:
            preflight_call(raw)
        require_qualification(qualified_ablation)
        inputs = (
            registry,
            protocol,
            qualified_ablation,
            actual_transition,
            ablated_transition,
            actual_certificate,
            ablated_certificate,
            run_spec,
            shell,
        )
        expected = expected_call(*inputs)
        preflight_call(expected)
        expected_digest = structural_digest(expected)
        if raw is not None and structural_digest(raw) != expected_digest:
            raise value_error("raw paired response outcome differs from replay")
        authority_snapshot = clone(expected)
        exposed_snapshot = clone(expected)
        preflight_call(authority_snapshot)
        preflight_call(exposed_snapshot)
        body_digest = structural_digest(authority_snapshot)
        wrapper_seal = structural_seal(authority_schema, body_digest)
        wrapper = wrapper_type(
            issuance_token,
            exposed_snapshot,
            wrapper_seal,
        )
        identity = id_fn(wrapper)
        authority = authority_type(
            outcome=authority_snapshot,
            inputs=inputs,
            body_digest=body_digest,
            seal=wrapper_seal,
        )

        def remove(reference, wrapper_id=identity):
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weak_reference(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=issuance_token,
            exposed_bodies=exposed_bodies(exposed_snapshot),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=authority_digest(authority),
        )
        return wrapper

    def reverify(wrapper):
        if type_fn(wrapper) is not wrapper_type:
            raise type_error("paired response requires a module-issued capability")
        with lock:
            current = live.get(id_fn(wrapper))
            if current is None or current[0]() is not wrapper:
                raise value_error("paired response identity is not live")
            authority = current[1]
        try:
            token = object_type.__getattribute__(
                wrapper,
                "_VerifiedPairedResponseOutcome__token",
            )
            raw = object_type.__getattribute__(
                wrapper,
                "_VerifiedPairedResponseOutcome__outcome",
            )
            wrapper_seal = object_type.__getattribute__(
                wrapper,
                "_VerifiedPairedResponseOutcome__seal",
            )
        except attribute_error as exc:
            raise value_error("paired response authority record is incomplete") from exc
        if token is not issuance_token:
            raise value_error("paired response token mismatch")
        preflight_call(raw)
        preflight_call(authority.outcome)

        def cheap_validator():
            raw_digest = structural_digest(raw)
            snapshot_digest = structural_digest(authority.outcome)
            expected_seal = structural_seal(
                authority_schema,
                authority.body_digest,
            )
            if (
                raw_digest != authority.body_digest
                or snapshot_digest != authority.body_digest
                or wrapper_seal != authority.seal
                or wrapper_seal != expected_seal
            ):
                raise value_error("paired response cached immutable guard mismatch")
            if binding_validator(authority) is not None:
                raise type_error("paired binding validator must return None")

        current_authority_digest = authority_digest(authority)
        if cached_replay_is_valid(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=token,
            exposed_bodies=exposed_bodies(raw),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=current_authority_digest,
            cheap_validator=cheap_validator,
        ):
            return authority_view(authority)
        expected = expected_call(*authority.inputs)
        preflight_call(expected)
        raw_digest = structural_digest(raw)
        snapshot_digest = structural_digest(authority.outcome)
        expected_digest = structural_digest(expected)
        expected_seal = structural_seal(authority_schema, expected_digest)
        if (
            raw_digest != authority.body_digest
            or snapshot_digest != authority.body_digest
            or expected_digest != authority.body_digest
            or wrapper_seal != authority.seal
            or wrapper_seal != expected_seal
        ):
            raise value_error("paired response immutable snapshot mismatch")
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=wrapper_type,
            token=token,
            exposed_bodies=exposed_bodies(raw),
            seal=wrapper_seal,
            authority=authority,
            authority_digest=current_authority_digest,
        )
        return authority_view(authority)

    def build(
        registry,
        protocol,
        qualified_ablation,
        actual_transition,
        ablated_transition,
        actual_certificate,
        ablated_certificate,
        run_spec,
        shell,
    ):
        return issue(
            registry,
            protocol,
            qualified_ablation,
            actual_transition,
            ablated_transition,
            actual_certificate,
            ablated_certificate,
            run_spec,
            shell,
            None,
        )

    def verify(outcome, registry, protocol, qualified_ablation):
        preflight_call(outcome)
        require_qualification(qualified_ablation)
        inputs = hydrate_call(
            outcome,
            registry,
            protocol,
            qualified_ablation,
        )
        return issue(*inputs, outcome)

    def outcome_property(wrapper):
        return reverify(wrapper).outcome

    def paired_property(wrapper):
        return reverify(wrapper).outcome.paired_response

    return (
        build,
        verify,
        issue,
        reverify,
        outcome_property,
        paired_property,
    )


_authority_structural_digest, _authority_structural_seal = (
    _make_authority_structural_codec(
        preflight=_closed_authority_preflight,
        dataclass_items=_closed_authority_dataclass_items,
    )
)
_closed_authority_binding_digest = _freeze_response_call_graph(
    _response_authority_binding_digest
)
_closed_expected_reference = _freeze_response_call_graph(_expected_reference_outcome)
_closed_preflight_reference = _freeze_response_call_graph(
    _preflight_reference_outcome_body
)
_closed_validate_reference_binding = _freeze_response_call_graph(
    _validate_cached_reference_binding
)
(
    build_endpoint_reference,
    verify_endpoint_reference_outcome,
    _issue_verified_endpoint_reference_outcome,
    _reverify_verified_endpoint_reference_outcome,
    _closed_reference_outcome_property,
    _closed_reference_property,
) = _make_closed_reference_authority(
    _closed_expected_reference,
    _closed_preflight_reference,
    _authority_structural_digest,
    _authority_structural_seal,
    binding_validator=_closed_validate_reference_binding,
    authority_binding_digest=_closed_authority_binding_digest,
)
_reverify_reference_authority = _reverify_verified_endpoint_reference_outcome
setattr(
    VerifiedEndpointReferenceOutcome,
    "outcome",
    property(_closed_reference_outcome_property),
)
setattr(
    VerifiedEndpointReferenceOutcome,
    "reference",
    property(_closed_reference_property),
)

_closed_build_shell_spec = _freeze_response_call_graph(
    _legacy_build_endpoint_shell_spec
)
_closed_expected_shell = _freeze_response_call_graph(_expected_shell_outcome)
_closed_preflight_shell = _freeze_response_call_graph(_preflight_shell_outcome_body)
_closed_validate_shell_binding = _freeze_response_call_graph(
    _validate_cached_shell_binding
)
(
    build_endpoint_shell_spec,
    build_endpoint_shell,
    verify_endpoint_shell_outcome,
    _issue_verified_endpoint_shell_outcome,
    _reverify_verified_endpoint_shell_outcome,
    _closed_shell_outcome_property,
    _closed_shell_property,
) = _make_closed_shell_authority(
    _closed_expected_shell,
    _closed_build_shell_spec,
    _closed_preflight_shell,
    _authority_structural_digest,
    _authority_structural_seal,
    binding_validator=_closed_validate_shell_binding,
    authority_binding_digest=_closed_authority_binding_digest,
)
_reverify_shell_authority = _reverify_verified_endpoint_shell_outcome
setattr(
    VerifiedEndpointShellOutcome,
    "outcome",
    property(_closed_shell_outcome_property),
)
setattr(
    VerifiedEndpointShellOutcome,
    "shell",
    property(_closed_shell_property),
)

_closed_expected_paired = _freeze_response_call_graph(_expected_paired_outcome)
_closed_hydrate_paired = _freeze_response_call_graph(_hydrate_paired_inputs_from_raw)
_closed_preflight_paired = _freeze_response_call_graph(_preflight_paired_outcome_body)
_closed_validate_paired_binding = _freeze_response_call_graph(
    _validate_cached_paired_binding
)
(
    build_paired_filtered_response,
    verify_paired_filtered_response,
    _issue_verified_paired_response_outcome,
    _reverify_verified_paired_response_outcome,
    _closed_paired_outcome_property,
    _closed_paired_property,
) = _make_closed_paired_authority(
    _closed_expected_paired,
    _closed_hydrate_paired,
    _closed_preflight_paired,
    _authority_structural_digest,
    _authority_structural_seal,
    qualification_type=VerifiedCertificateBackedQualification,
    binding_validator=_closed_validate_paired_binding,
    authority_binding_digest=_closed_authority_binding_digest,
)
_reverify_paired_authority = _reverify_verified_paired_response_outcome
setattr(
    VerifiedPairedResponseOutcome,
    "outcome",
    property(_closed_paired_outcome_property),
)
setattr(
    VerifiedPairedResponseOutcome,
    "paired_response",
    property(_closed_paired_property),
)


__all__ = [
    "ENDPOINT_REFERENCE_ATTEMPT_SCHEMA_VERSION",
    "ENDPOINT_REFERENCE_OUTCOME_SCHEMA_VERSION",
    "ENDPOINT_REFERENCE_SCHEMA_VERSION",
    "ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION",
    "ENDPOINT_SHELL_ATTEMPT_SCHEMA_VERSION",
    "ENDPOINT_SHELL_OUTCOME_SCHEMA_VERSION",
    "ENDPOINT_SHELL_SCHEMA_VERSION",
    "ENDPOINT_SHELL_SPEC_SCHEMA_VERSION",
    "PAIRED_RESPONSE_ATTEMPT_SCHEMA_VERSION",
    "PAIRED_RESPONSE_OUTCOME_SCHEMA_VERSION",
    "PAIRED_RESPONSE_SCHEMA_VERSION",
    "RESPONSE_RUN_SPEC_SCHEMA_VERSION",
    "SOURCE_FRAME_COVERAGE_SCHEMA_VERSION",
    "SOURCE_READOUT_BRIDGE_SCHEMA_VERSION",
    "SOURCE_READOUT_RESPONSE_SCHEMA_VERSION",
    "EndpointReferenceAttemptAudit",
    "EndpointReferenceFailure",
    "EndpointReferenceOutcome",
    "EndpointReferenceProjector",
    "EndpointReferenceSpec",
    "EndpointShellAttemptAudit",
    "EndpointShellFailure",
    "EndpointShellManifest",
    "EndpointShellOutcome",
    "EndpointShellSpec",
    "PairedFilteredResponse",
    "PairedResponseAttemptAudit",
    "PairedResponseFailure",
    "PairedResponseOutcome",
    "ResponseRunSpec",
    "ShellCandidatePointAttempt",
    "ShellPointAudit",
    "SourceFrameCoverageCertificate",
    "SourceReadoutBranchAttemptAudit",
    "SourceReadoutBridgeAudit",
    "SourceReadoutBridgeMatrixAudit",
    "SourceReadoutResponse",
    "VerifiedEndpointReferenceOutcome",
    "VerifiedEndpointShellOutcome",
    "VerifiedPairedResponseOutcome",
    "build_endpoint_reference",
    "build_endpoint_shell",
    "build_endpoint_shell_spec",
    "build_paired_filtered_response",
    "build_response_run_spec",
    "build_source_frame_coverage_certificate",
    "compute_fejer_filtered_response",
    "endpoint_reference_attempt_audit_payload",
    "endpoint_reference_outcome_payload",
    "endpoint_reference_projector_payload",
    "endpoint_reference_spec_payload",
    "endpoint_shell_attempt_audit_payload",
    "endpoint_shell_manifest_payload",
    "endpoint_shell_outcome_payload",
    "endpoint_shell_spec_payload",
    "paired_filtered_response_payload",
    "paired_response_attempt_audit_payload",
    "paired_response_outcome_payload",
    "response_run_spec_payload",
    "shell_candidate_point_attempt_payload",
    "shell_point_audit_payload",
    "source_frame_coverage_payload",
    "source_readout_branch_attempt_audit_payload",
    "source_readout_bridge_audit_payload",
    "source_readout_bridge_matrix_audit_payload",
    "source_readout_response_payload",
    "verify_endpoint_reference_outcome",
    "verify_endpoint_shell_outcome",
    "verify_endpoint_shell_spec",
    "verify_paired_filtered_response",
    "verify_response_run_spec",
    "verify_source_frame_coverage_certificate",
    "verify_source_readout_bridge_audit_body",
]
