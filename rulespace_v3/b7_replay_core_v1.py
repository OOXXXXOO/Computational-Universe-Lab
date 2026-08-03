"""Import-pure canonical primitives for B7 reviewer-child replay."""

from __future__ import annotations

import hashlib
import json


B7_V91_PURE_REPLAY_PROJECTION_SHA256 = (
    "bafbaeb75e890715464c1fff6e6e0cbf1d4f56bb53a3817a9b2d12d2a3c27ff9"
)


def _reject_duplicate_object_pairs_v1(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant_v1(token: str) -> object:
    raise ValueError(f"JSON number must be finite: {token}")


def _validate_json_object_keys_v1(value: object, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{path} JSON object key must be a str")
            _validate_json_object_keys_v1(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_object_keys_v1(item, f"{path}[{index}]")


def strict_json_loads_v1(canonical_json_utf8: bytes) -> object:
    """Decode strict UTF-8 JSON while rejecting BOMs, duplicates and NaN."""

    if type(canonical_json_utf8) is not bytes:
        raise TypeError("canonical_json_utf8 must be exact bytes")
    if canonical_json_utf8.startswith(b"\xef\xbb\xbf"):
        raise ValueError("JSON UTF-8 BOM is forbidden")
    try:
        text = canonical_json_utf8.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("JSON input must be strict UTF-8") from exc
    value = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_object_pairs_v1,
        parse_constant=_reject_nonfinite_constant_v1,
    )
    canonical_json_bytes_v1(value)
    return value


def canonical_json_bytes_v1(value: object) -> bytes:
    """Encode one JSON value using the frozen B7 canonical byte algorithm."""

    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    _validate_json_object_keys_v1(value, "$")
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("canonical JSON text must be valid UTF-8") from exc


def canonical_sha_v1(value: object) -> str:
    """Hash the frozen canonical JSON bytes for one B7 raw value."""

    return hashlib.sha256(canonical_json_bytes_v1(value)).hexdigest()
