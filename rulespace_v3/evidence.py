"""Canonical hashing and required evidence envelopes for V3-M0."""

from __future__ import annotations

import hashlib
import json
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


def _canonical_json_value(
    value: object,
    path: str,
    active_containers: set[int],
) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain only finite numbers")
        return value

    if isinstance(value, Mapping):
        container_id = id(value)
        if container_id in active_containers:
            raise ValueError(f"{path} contains a cyclic container")
        active_containers.add(container_id)
        try:
            normalized: dict[str, Any] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise TypeError(f"{path} mapping key must be a str")
                normalized[key] = _canonical_json_value(
                    item,
                    f"{path}.{key}",
                    active_containers,
                )
            return normalized
        finally:
            active_containers.remove(container_id)

    if type(value) in (list, tuple):
        container_id = id(value)
        if container_id in active_containers:
            raise ValueError(f"{path} contains a cyclic container")
        active_containers.add(container_id)
        try:
            return [
                _canonical_json_value(
                    item,
                    f"{path}[{index}]",
                    active_containers,
                )
                for index, item in enumerate(value)
            ]
        finally:
            active_containers.remove(container_id)

    raise TypeError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def canonical_sha(payload: Mapping[str, object]) -> str:
    """Return the SHA-256 of the complete payload's canonical UTF-8 JSON.

    Encoding is ``json.dumps(sort_keys=True, separators=(',', ':'),
    ensure_ascii=False, allow_nan=False)`` followed by UTF-8 encoding.
    Mapping keys are sorted while list/tuple array order is preserved; ``-0.0``
    and ``0.0`` remain distinct.  This repository contract is not RFC 8785.
    """

    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    normalized = _canonical_json_value(payload, "$", set())
    canonical = json.dumps(
        normalized,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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
