"""Import-pure canonical primitives for B7 reviewer-child replay."""

from __future__ import annotations

import hashlib
import json


B7_V91_PURE_REPLAY_PROJECTION_SHA256 = (
    "bafbaeb75e890715464c1fff6e6e0cbf1d4f56bb53a3817a9b2d12d2a3c27ff9"
)


def canonical_json_bytes_v1(value: object) -> bytes:
    """Encode one JSON value using the frozen B7 canonical byte algorithm."""

    def validate_object_keys(candidate: object, path: str) -> None:
        if isinstance(candidate, dict):
            for key, item in candidate.items():
                if type(key) is not str:
                    raise TypeError(f"{path} JSON object key must be a str")
                validate_object_keys(item, f"{path}.{key}")
        elif isinstance(candidate, (list, tuple)):
            for index, item in enumerate(candidate):
                validate_object_keys(item, f"{path}[{index}]")

    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    validate_object_keys(value, "$")
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("canonical JSON text must be valid UTF-8") from exc


def canonical_sha_v1(value: object) -> str:
    """Hash the frozen canonical JSON bytes for one B7 raw value."""

    return hashlib.sha256(canonical_json_bytes_v1(value)).hexdigest()


def strict_json_loads_v1(canonical_json_utf8: bytes) -> object:
    """Decode strict UTF-8 JSON while rejecting BOMs, duplicates and NaN."""

    def reject_duplicate_object_pairs(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    def reject_nonfinite_constant(constant_text: str) -> object:
        raise ValueError(f"JSON number must be finite: {constant_text}")

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
        object_pairs_hook=reject_duplicate_object_pairs,
        parse_constant=reject_nonfinite_constant,
    )
    canonical_json_bytes_v1(value)
    return value
