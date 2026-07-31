"""Canonical hashing and required evidence envelopes for V3-M0."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


FINAL_RESULT_EVIDENCE_FIELDS = (
    "evaluator_version",
    "grammar_id",
    "target_spec_id",
    "trace_sha",
    "response_manifest_id",
    "parent_v2_sha",
    "source_metric_id",
    "physical_h_metric_id",
    "curvature_metric_id",
    "physical_quotient_id",
    "physical_quotient_metric_id",
    "nu_inc_id",
    "window_manifest_sha",
    "actual_unary_manifest_id",
    "ablated_unary_manifest_id",
    "toolchain_manifest",
)

_FINAL_RESULT_STRING_FIELDS = FINAL_RESULT_EVIDENCE_FIELDS[:-1]
_SHA_FIELDS = frozenset(("trace_sha", "parent_v2_sha", "window_manifest_sha"))
_LOWER_HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _make_json_normalizer(
    *,
    _mapping_type=Mapping,
    _isinstance=isinstance,
    _type=type,
    _str_type=str,
    _bool_type=bool,
    _int_type=int,
    _float_type=float,
    _list_type=list,
    _tuple_type=tuple,
    _id=id,
    _enumerate=enumerate,
    _isfinite=math.isfinite,
    _type_error=TypeError,
    _value_error=ValueError,
) -> object:
    """Capture every executable dependency used to take one JSON snapshot."""

    def normalize(
        value: object,
        path: str,
        active_containers: set[int],
    ) -> Any:
        if value is None or _type(value) in (
            _str_type,
            _bool_type,
            _int_type,
        ):
            return value
        if _type(value) is _float_type:
            if not _isfinite(value):
                raise _value_error(f"{path} must contain only finite numbers")
            return value

        if _isinstance(value, _mapping_type):
            container_id = _id(value)
            if container_id in active_containers:
                raise _value_error(f"{path} contains a cyclic container")
            active_containers.add(container_id)
            try:
                normalized: dict[str, Any] = {}
                for key, item in value.items():
                    if _type(key) is not _str_type:
                        raise _type_error(f"{path} mapping key must be a str")
                    normalized[key] = normalize(
                        item,
                        f"{path}.{key}",
                        active_containers,
                    )
                return normalized
            finally:
                active_containers.remove(container_id)

        if _type(value) in (_list_type, _tuple_type):
            container_id = _id(value)
            if container_id in active_containers:
                raise _value_error(f"{path} contains a cyclic container")
            active_containers.add(container_id)
            try:
                return [
                    normalize(
                        item,
                        f"{path}[{index}]",
                        active_containers,
                    )
                    for index, item in _enumerate(value)
                ]
            finally:
                active_containers.remove(container_id)

        raise _type_error(
            f"{path} contains a non-JSON value of type {_type(value).__name__}"
        )

    return normalize


_canonical_json_value = _make_json_normalizer()


def _make_exact_json_tools(
    *,
    _sha256=hashlib.sha256,
    _type=type,
    _str_type=str,
    _bool_type=bool,
    _int_type=int,
    _float_type=float,
    _list_type=list,
    _tuple_type=tuple,
    _dict_type=dict,
    _id=id,
    _len=len,
    _ord=ord,
    _repr=repr,
    _sorted=sorted,
    _set=set,
    _range=range,
    _enumerate=enumerate,
    _any=any,
    _isfinite=math.isfinite,
    _type_error=TypeError,
    _value_error=ValueError,
) -> tuple[object, object]:
    """Build byte-exact JSON hashing/counting without mutable stdlib modules."""

    def quoted_chunks(value: str):
        yield '"'
        start = 0
        for index, character in _enumerate(value):
            codepoint = _ord(character)
            replacement = None
            if character == '"':
                replacement = '\\"'
            elif character == "\\":
                replacement = "\\\\"
            elif character == "\b":
                replacement = "\\b"
            elif character == "\f":
                replacement = "\\f"
            elif character == "\n":
                replacement = "\\n"
            elif character == "\r":
                replacement = "\\r"
            elif character == "\t":
                replacement = "\\t"
            elif codepoint < 0x20:
                replacement = f"\\u{codepoint:04x}"
            elif 0xD800 <= codepoint <= 0xDFFF:
                raise _value_error("canonical JSON text is not valid UTF-8")
            if replacement is not None:
                if start < index:
                    yield value[start:index]
                yield replacement
                start = index + 1
        if start < _len(value):
            yield value[start:]
        yield '"'

    def encoded_chunks(value: object, active: set[int], path: str):
        value_type = _type(value)
        if value is None:
            yield "null"
        elif value_type is _bool_type:
            yield "true" if value else "false"
        elif value_type is _str_type:
            yield from quoted_chunks(value)
        elif value_type is _int_type:
            yield _str_type(value)
        elif value_type is _float_type:
            if not _isfinite(value):
                raise _value_error(f"{path} must contain only finite numbers")
            yield _repr(value)
        elif value_type in (_list_type, _tuple_type):
            identity = _id(value)
            if identity in active:
                raise _value_error(f"{path} contains a cyclic array")
            active.add(identity)
            try:
                yield "["
                for index in _range(_len(value)):
                    if index:
                        yield ","
                    yield from encoded_chunks(
                        value[index],
                        active,
                        f"{path}[{index}]",
                    )
                yield "]"
            finally:
                active.remove(identity)
        elif value_type is _dict_type:
            identity = _id(value)
            if identity in active:
                raise _value_error(f"{path} contains a cyclic mapping")
            active.add(identity)
            try:
                keys = _sorted(value)
                if _any(_type(key) is not _str_type for key in keys):
                    raise _type_error(f"{path} mapping key must be a str")
                yield "{"
                for index, key in _enumerate(keys):
                    if index:
                        yield ","
                    yield from quoted_chunks(key)
                    yield ":"
                    yield from encoded_chunks(
                        value[key],
                        active,
                        f"{path}.{key}",
                    )
                yield "}"
            finally:
                active.remove(identity)
        else:
            raise _type_error(
                f"{path} contains a non-JSON value of type {value_type.__name__}"
            )

    def byte_count(
        value: object,
        *,
        maximum_bytes: int | None = None,
    ) -> int:
        if maximum_bytes is not None and (
            _type(maximum_bytes) is not _int_type or maximum_bytes <= 0
        ):
            raise _type_error("maximum_bytes must be a positive int or None")
        total = 0
        for chunk in encoded_chunks(value, _set(), "$"):
            total += _len(chunk.encode("utf-8"))
            if maximum_bytes is not None and total > maximum_bytes:
                raise _value_error("canonical evidence body exceeds resource cap")
        return total

    def sha(
        value: object,
        *,
        maximum_bytes: int | None = None,
    ) -> str:
        if maximum_bytes is not None:
            byte_count(value, maximum_bytes=maximum_bytes)
        digest = _sha256()
        for chunk in encoded_chunks(value, _set(), "$"):
            digest.update(chunk.encode("utf-8"))
        return digest.hexdigest()

    return sha, byte_count


_EXACT_JSON_SHA256, _EXACT_JSON_UTF8_SIZE = _make_exact_json_tools()


def _make_canonical_sha(
    *,
    _normalize=_canonical_json_value,
    _exact_sha=_EXACT_JSON_SHA256,
    _mapping_type=Mapping,
    _isinstance=isinstance,
    _type_error=TypeError,
    _set=set,
):
    def canonical_sha(payload: Mapping[str, object]) -> str:
        """Return the SHA-256 of the complete payload's canonical UTF-8 JSON.

        Encoding is equivalent to ``json.dumps(sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False)`` followed
        by UTF-8 encoding. Mapping keys are sorted while list/tuple array order
        is preserved; ``-0.0`` and ``0.0`` remain distinct. This repository
        contract is not RFC 8785.
        """

        if not _isinstance(payload, _mapping_type):
            raise _type_error("payload must be a mapping")
        normalized = _normalize(payload, "$", _set())
        return _exact_sha(normalized)

    return canonical_sha


canonical_sha = _make_canonical_sha()


def _canonical_json_utf8_size(
    payload: Mapping[str, object],
    *,
    _mapping_type=Mapping,
    _isinstance=isinstance,
    _type_error=TypeError,
    _normalize=_canonical_json_value,
    _set=set,
    _size=_EXACT_JSON_UTF8_SIZE,
) -> int:
    """Return the exact canonical UTF-8 size using the frozen encoder."""

    if not _isinstance(payload, _mapping_type):
        raise _type_error("payload must be a mapping")
    normalized = _normalize(payload, "$", _set())
    return _size(normalized)


def _make_exact_wire_cloner(
    record_types: tuple[type, ...],
    *,
    atomic_types: tuple[type, ...] = (),
    _type=type,
    _str_type=str,
    _bool_type=bool,
    _int_type=int,
    _float_type=float,
    _complex_type=complex,
    _bytes_type=bytes,
    _none_type=type(None),
    _tuple_type=tuple,
    _list_type=list,
    _dict_type=dict,
    _set_type=set,
    _id=id,
    _object=object,
    _frozenset=frozenset,
    _sorted=sorted,
    _enumerate=enumerate,
    _type_error=TypeError,
    _value_error=ValueError,
):
    """Build a no-dispatch clone for one closed exact wire-type registry."""

    registry = _tuple_type(
        (record_type, _tuple_type(record_type.__dataclass_fields__))
        for record_type in record_types
    )
    atoms = (
        _str_type,
        _bool_type,
        _int_type,
        _float_type,
        _complex_type,
        _bytes_type,
        _none_type,
        *atomic_types,
    )

    def clone(value: object) -> object:
        memo: dict[int, object] = {}
        active: set[int] = _set_type()

        def copy_value(current: object, path: str) -> object:
            current_type = _type(current)
            if current_type in atoms:
                return current
            identity = _id(current)
            if identity in active:
                raise _value_error(f"{path} contains a cyclic wire body")
            if identity in memo:
                return memo[identity]

            names = None
            for record_type, field_names in registry:
                if current_type is record_type:
                    names = field_names
                    break
            if names is not None:
                expected = _frozenset(names)
                actual = _frozenset(_object.__getattribute__(current, "__dict__"))
                if actual != expected:
                    raise _value_error(
                        f"{path} record fields differ; "
                        f"unknown={_sorted(actual - expected)}, "
                        f"missing={_sorted(expected - actual)}"
                    )
                result = _object.__new__(current_type)
                memo[identity] = result
                active.add(identity)
                try:
                    for name in names:
                        _object.__setattr__(
                            result,
                            name,
                            copy_value(
                                _object.__getattribute__(current, name),
                                f"{path}.{name}",
                            ),
                        )
                finally:
                    active.remove(identity)
                return result

            if current_type is _tuple_type:
                active.add(identity)
                try:
                    result = _tuple_type(
                        copy_value(item, f"{path}[{index}]")
                        for index, item in _enumerate(current)
                    )
                finally:
                    active.remove(identity)
                memo[identity] = result
                return result
            if current_type is _list_type:
                result_list: list[object] = []
                memo[identity] = result_list
                active.add(identity)
                try:
                    result_list.extend(
                        copy_value(item, f"{path}[{index}]")
                        for index, item in _enumerate(current)
                    )
                finally:
                    active.remove(identity)
                return result_list
            if current_type is _dict_type:
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
            raise _type_error(
                f"{path} has unsupported exact wire type {current_type.__name__}"
            )

        return copy_value(value, "$")

    return clone


def _validate_required_field_profile(required_fields: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(required_fields, Sequence) or isinstance(
        required_fields, (str, bytes, bytearray)
    ):
        raise TypeError("required_fields must be a sequence of field names")
    profile = tuple(required_fields)
    if not profile:
        raise ValueError("required_fields must not be empty")

    seen: set[str] = set()
    for field in profile:
        if not isinstance(field, str):
            raise TypeError("required field names must be strings")
        if not field.strip():
            raise ValueError("required field names must be non-empty strings")
        if field in seen:
            raise ValueError(f"duplicate required field: {field}")
        seen.add(field)
    return profile


def _validate_final_field(field: str, value: object) -> None:
    if field in _FINAL_RESULT_STRING_FIELDS:
        if not isinstance(value, str):
            raise TypeError(f"{field} must be a non-empty string")
        if not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        if field in _SHA_FIELDS and _LOWER_HEX_SHA256.fullmatch(value) is None:
            raise ValueError(f"{field} must be a 64-digit lowercase hexadecimal SHA")
    elif field == "toolchain_manifest":
        if not isinstance(value, Mapping):
            raise TypeError("toolchain_manifest must be a non-empty mapping")
        if not value:
            raise ValueError("toolchain_manifest must be a non-empty mapping")


def _validated_evidence_snapshot(
    payload: Mapping[str, object],
    *,
    required_fields: Sequence[str],
) -> dict[str, Any]:
    """Take one canonical snapshot and validate all fields against that snapshot."""

    if not isinstance(payload, Mapping):
        raise TypeError("evidence payload must be a mapping")
    profile = _validate_required_field_profile(required_fields)
    normalized = _canonical_json_value(payload, "$", set())
    if not isinstance(normalized, dict):
        raise TypeError("evidence payload must normalize to a mapping")

    missing = [field for field in profile if field not in normalized]
    if missing:
        raise ValueError(f"missing required evidence fields: {', '.join(missing)}")

    for field in profile:
        _validate_final_field(field, normalized[field])
    return normalized


def validate_evidence_fields(
    payload: Mapping[str, object],
    *,
    required_fields: Sequence[str],
) -> None:
    """Validate one explicit evidence profile without inventing other fields."""

    _validated_evidence_snapshot(
        payload,
        required_fields=required_fields,
    )


def _deep_freeze_json(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _deep_freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_deep_freeze_json(item) for item in value)
    return value


@dataclass(frozen=True)
class EvidenceEnvelope:
    """Required evidence for final response/control results only."""

    evaluator_version: str
    grammar_id: str
    target_spec_id: str
    trace_sha: str
    response_manifest_id: str
    parent_v2_sha: str
    source_metric_id: str
    physical_h_metric_id: str
    curvature_metric_id: str
    physical_quotient_id: str
    physical_quotient_metric_id: str
    nu_inc_id: str
    window_manifest_sha: str
    actual_unary_manifest_id: str
    ablated_unary_manifest_id: str
    toolchain_manifest: Mapping[str, object]

    def __post_init__(self) -> None:
        payload = {
            field: getattr(self, field) for field in FINAL_RESULT_EVIDENCE_FIELDS
        }
        snapshot = _validated_evidence_snapshot(
            payload,
            required_fields=FINAL_RESULT_EVIDENCE_FIELDS,
        )
        object.__setattr__(
            self,
            "toolchain_manifest",
            _deep_freeze_json(snapshot["toolchain_manifest"]),
        )


def validate_evidence_envelope(
    payload: Mapping[str, object],
) -> EvidenceEnvelope:
    """Validate and extract the required §8 envelope from a result payload."""

    snapshot = _validated_evidence_snapshot(
        payload,
        required_fields=FINAL_RESULT_EVIDENCE_FIELDS,
    )
    values = {field: snapshot[field] for field in FINAL_RESULT_EVIDENCE_FIELDS}
    return EvidenceEnvelope(**values)  # type: ignore[arg-type]
