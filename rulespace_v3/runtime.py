"""Fresh-process runtime evidence for the V3-M0 certificate closure.

The public manifest is an inert, recursively complete wire record.  Issuance
has no caller-controlled evaluator or toolchain arguments: a fresh isolated
Python process imports the closed certificate roots, inventories every loaded
repository-local source file, and records environment attribution.  Every
verification repeats that probe and compares the complete body.

The manifest hash is content identity only.  It carries no timestamp,
sequence, or wall-clock ordering claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from .evidence import canonical_sha as _evidence_canonical_sha


# Kept as a compatibility/testing surface only.  Security-sensitive public
# APIs use the module-frozen runtime hasher constructed below.
canonical_sha = _evidence_canonical_sha


RUNTIME_SCHEMA_VERSION = "v3m0.runtime-evidence-manifest.v1"
RUNTIME_EVALUATOR_ID = "rulespace-v3m0-certificate-closure-v1"

RUNTIME_MAX_IMPORT_ROOTS = 64
RUNTIME_MAX_SOURCE_FILES = 256
RUNTIME_MAX_SOURCE_FILE_BYTES = 4_194_304
RUNTIME_MAX_TOTAL_SOURCE_BYTES = 67_108_864
RUNTIME_MAX_PROBE_JSON_BYTES = 1_048_576
RUNTIME_MAX_CANONICAL_BODY_BYTES = 524_288
RUNTIME_MAX_RELATIVE_PATH_BYTES = 512
RUNTIME_MAX_TEXT_BYTES = 16_384
RUNTIME_PROBE_TIMEOUT_SECONDS = 60
RUNTIME_MAX_PACKAGE_DIRECTORIES = 64
RUNTIME_MAX_PACKAGE_ENTRIES = 4_096
RUNTIME_MAX_SUBPROCESS_STDERR_BYTES = 65_536
RUNTIME_MAX_SUBPROCESS_FILE_BYTES = 1_048_576
RUNTIME_MAX_ENVIRONMENT_ENTRIES = 4_096
RUNTIME_MAX_ENVIRONMENT_BYTES = 1_048_576
RUNTIME_MAX_CONFIG_NODES = 10_000
RUNTIME_MAX_CONFIG_DEPTH = 32
RUNTIME_MAX_CONFIG_TEXT_BYTES = 1_048_576
RUNTIME_MAX_CONFIG_JSON_BYTES = 2_097_152
RUNTIME_MAX_LOADED_MODULES = 4_096


class _RuntimeCaps(NamedTuple):
    max_import_roots: int
    max_source_files: int
    max_source_file_bytes: int
    max_total_source_bytes: int
    max_probe_json_bytes: int
    max_canonical_body_bytes: int
    max_relative_path_bytes: int
    max_text_bytes: int
    probe_timeout_seconds: int
    max_package_directories: int
    max_package_entries: int
    max_subprocess_stderr_bytes: int
    max_subprocess_file_bytes: int
    max_environment_entries: int
    max_environment_bytes: int
    max_config_nodes: int
    max_config_depth: int
    max_config_text_bytes: int
    max_config_json_bytes: int
    max_loaded_modules: int


_RUNTIME_CAPS = _RuntimeCaps(
    max_import_roots=RUNTIME_MAX_IMPORT_ROOTS,
    max_source_files=RUNTIME_MAX_SOURCE_FILES,
    max_source_file_bytes=RUNTIME_MAX_SOURCE_FILE_BYTES,
    max_total_source_bytes=RUNTIME_MAX_TOTAL_SOURCE_BYTES,
    max_probe_json_bytes=RUNTIME_MAX_PROBE_JSON_BYTES,
    max_canonical_body_bytes=RUNTIME_MAX_CANONICAL_BODY_BYTES,
    max_relative_path_bytes=RUNTIME_MAX_RELATIVE_PATH_BYTES,
    max_text_bytes=RUNTIME_MAX_TEXT_BYTES,
    probe_timeout_seconds=RUNTIME_PROBE_TIMEOUT_SECONDS,
    max_package_directories=RUNTIME_MAX_PACKAGE_DIRECTORIES,
    max_package_entries=RUNTIME_MAX_PACKAGE_ENTRIES,
    max_subprocess_stderr_bytes=RUNTIME_MAX_SUBPROCESS_STDERR_BYTES,
    max_subprocess_file_bytes=RUNTIME_MAX_SUBPROCESS_FILE_BYTES,
    max_environment_entries=RUNTIME_MAX_ENVIRONMENT_ENTRIES,
    max_environment_bytes=RUNTIME_MAX_ENVIRONMENT_BYTES,
    max_config_nodes=RUNTIME_MAX_CONFIG_NODES,
    max_config_depth=RUNTIME_MAX_CONFIG_DEPTH,
    max_config_text_bytes=RUNTIME_MAX_CONFIG_TEXT_BYTES,
    max_config_json_bytes=RUNTIME_MAX_CONFIG_JSON_BYTES,
    max_loaded_modules=RUNTIME_MAX_LOADED_MODULES,
)

_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_MODULE_NAME = re.compile(r"rulespace_v3(?:\.[a-z_][a-z0-9_]*)+\Z")


def _make_runtime_json_primitives(
    *,
    _sha256=hashlib.sha256,
    _type=type,
    _bool_type=bool,
    _int_type=int,
    _str_type=str,
    _list_type=list,
    _tuple_type=tuple,
    _dict_type=dict,
    _sorted=sorted,
    _ord=ord,
    _type_error=TypeError,
):
    escapes = {
        '"': '\\"',
        "\\": "\\\\",
        "\b": "\\b",
        "\f": "\\f",
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }

    def encode_string(value: str) -> str:
        encoded: list[str] = ['"']
        for character in value:
            escaped = escapes.get(character)
            if escaped is not None:
                encoded.append(escaped)
                continue
            codepoint = _ord(character)
            if codepoint < 0x20:
                encoded.append(f"\\u{codepoint:04x}")
            else:
                encoded.append(character)
        encoded.append('"')
        return "".join(encoded)

    def encode_value(value: object) -> str:
        if value is None:
            return "null"
        if _type(value) is _bool_type:
            return "true" if value else "false"
        if _type(value) is _int_type:
            return _str_type(value)
        if _type(value) is _str_type:
            return encode_string(value)
        if _type(value) in (_list_type, _tuple_type):
            return "[" + ",".join(encode_value(item) for item in value) + "]"
        if _type(value) is _dict_type:
            for key in value:
                if _type(key) is not _str_type:
                    raise _type_error("runtime JSON mapping keys must be strings")
            return (
                "{"
                + ",".join(
                    f"{encode_string(key)}:{encode_value(value[key])}"
                    for key in _sorted(value)
                )
                + "}"
            )
        raise _type_error(
            f"runtime JSON contains unsupported value type {_type(value).__name__}"
        )

    def encode_text(value: object) -> str:
        return encode_value(value)

    def encode_bytes(value: object) -> bytes:
        return encode_value(value).encode("utf-8")

    def canonical_sha256(payload: object) -> str:
        if _type(payload) is not _dict_type:
            raise _type_error("runtime hash payload must be a plain dict")
        return _sha256(encode_bytes(payload)).hexdigest()

    return encode_text, encode_bytes, canonical_sha256


(
    _RUNTIME_JSON_TEXT,
    _RUNTIME_JSON_BYTES,
    _RUNTIME_CANONICAL_SHA,
) = _make_runtime_json_primitives()

_WIRE_FIELDS = frozenset(
    (
        "runtime_schema_version",
        "evaluator_id",
        "source_closure",
        "python_version",
        "numpy_version",
        "scipy_version",
        "blas_config_sha",
        "lapack_config_sha",
        "platform_id",
        "runtime_manifest_sha",
    )
)
_PROBE_FIELDS = frozenset(
    (
        "source_closure",
        "python_version",
        "numpy_version",
        "scipy_version",
        "blas_config_sha",
        "lapack_config_sha",
        "platform_id",
    )
)
_SOURCE_ENTRY_FIELDS = frozenset(("relative_path", "sha256"))

# ``certificate`` is an optional final assembly root while Task 10 is being
# constructed.  Once its source file exists it is mechanically included; it
# is never selected by a caller.
_FROZEN_IMPORT_ROOT_CANDIDATES = (
    "rulespace_v3.bridge",
    "rulespace_v3.certificate",
    "rulespace_v3.dynamics",
    "rulespace_v3.fp64_protocol",
    "rulespace_v3.grids",
    "rulespace_v3.instability",
    "rulespace_v3.laurent",
    "rulespace_v3.metric",
    "rulespace_v3.parent_freeze",
    "rulespace_v3.prestructure",
    "rulespace_v3.qualification",
    "rulespace_v3.registry",
    "rulespace_v3.runtime",
    "rulespace_v3.spectral",
    "rulespace_v3.structure",
)
_OPTIONAL_IMPORT_ROOTS = frozenset(("rulespace_v3.certificate",))
_MODULE_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _repository_root() -> Path:
    return _MODULE_REPOSITORY_ROOT


def _freeze_module_import_roots() -> tuple[str, ...]:
    if _FROZEN_IMPORT_ROOT_CANDIDATES != tuple(
        sorted(set(_FROZEN_IMPORT_ROOT_CANDIDATES))
    ):
        raise RuntimeError("runtime import-root authority is not canonical")
    result: list[str] = []
    for module_name in _FROZEN_IMPORT_ROOT_CANDIDATES:
        relative = Path(*module_name.split(".")).with_suffix(".py")
        exists = (_MODULE_REPOSITORY_ROOT / relative).is_file()
        if not exists and module_name in _OPTIONAL_IMPORT_ROOTS:
            continue
        if not exists:
            raise RuntimeError(f"frozen runtime import root is missing: {module_name}")
        result.append(module_name)
    return tuple(result)


_MODULE_IMPORT_ROOTS = _freeze_module_import_roots()

# Parent-v3 uses a parallel private authority.  Its single fresh-process root
# is deliberately not folded into the legacy public authority above: doing so
# would silently change the meaning of every legacy runtime manifest.
_V3_RUNTIME_IMPORT_ROOTS = ("rulespace_v3.certificate_v3",)


def _text(
    value: object,
    field: str,
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _type=type,
    _str_type=str,
    _len=len,
    _type_error=TypeError,
    _value_error=ValueError,
) -> str:
    if _type(value) is not _str_type:
        raise _type_error(f"{field} must be a string")
    if not value:
        raise _value_error(f"{field} must be non-empty")
    if _len(value) > _caps.max_text_bytes:
        raise _value_error(f"{field} exceeds its resource cap")
    if _len(value.encode("utf-8")) > _caps.max_text_bytes:
        raise _value_error(f"{field} exceeds its resource cap")
    return value


def _sha(
    value: object,
    field: str,
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _text_validator=_text,
    _sha_fullmatch=_LOWER_SHA.fullmatch,
    _value_error=ValueError,
) -> str:
    result = _text_validator(value, field, _caps=_caps)
    if _sha_fullmatch(result) is None:
        raise _value_error(f"{field} must be a lowercase SHA-256")
    return result


def _relative_source_path(
    value: object,
    field: str,
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _text_validator=_text,
    _path_type=PurePosixPath,
    _len=len,
    _str_type=str,
    _any=any,
    _value_error=ValueError,
) -> str:
    result = _text_validator(value, field, _caps=_caps)
    if _len(result) > _caps.max_relative_path_bytes:
        raise _value_error(f"{field} exceeds its path resource cap")
    if _len(result.encode("utf-8")) > _caps.max_relative_path_bytes:
        raise _value_error(f"{field} exceeds its path resource cap")
    if "\\" in result:
        raise _value_error(f"{field} must use POSIX separators")
    pure = _path_type(result)
    if pure.is_absolute() or _str_type(pure) != result:
        raise _value_error(f"{field} must be a normalized relative path")
    if _any(part in ("", ".", "..") for part in pure.parts):
        raise _value_error(f"{field} must remain inside the repository")
    if not pure.parts or pure.parts[0] != "rulespace_v3":
        raise _value_error(f"{field} is outside the certificate package")
    if pure.suffix != ".py":
        raise _value_error(f"{field} must identify a Python source file")
    return result


def _source_closure(
    value: object,
    field: str = "source_closure",
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _relative_path_validator=_relative_source_path,
    _sha_validator=_sha,
    _type=type,
    _tuple_type=tuple,
    _len=len,
    _enumerate=enumerate,
    _sorted=sorted,
    _type_error=TypeError,
    _value_error=ValueError,
) -> tuple[tuple[str, str], ...]:
    if _type(value) is not _tuple_type:
        raise _type_error(f"{field} must be a tuple")
    if not value:
        raise _value_error(f"{field} must be non-empty")
    if _len(value) > _caps.max_source_files:
        raise _value_error(f"{field} exceeds its file-count resource cap")

    result: list[tuple[str, str]] = []
    for index, entry in _enumerate(value):
        if _type(entry) is not _tuple_type or _len(entry) != 2:
            raise _type_error(f"{field}[{index}] must be a path/SHA tuple")
        path = _relative_path_validator(
            entry[0],
            f"{field}[{index}].relative_path",
            _caps=_caps,
        )
        source_sha = _sha_validator(
            entry[1],
            f"{field}[{index}].sha256",
            _caps=_caps,
        )
        result.append((path, source_sha))

    answer = _tuple_type(result)
    if answer != _tuple_type(_sorted(answer)):
        raise _value_error(f"{field} must be canonical and lexicographic")
    if _len({path for path, _ in answer}) != _len(answer):
        raise _value_error(f"{field} contains duplicate paths")
    return answer


def _preflight_canonical_payload(
    payload: dict[str, object],
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _canonical_bytes=_RUNTIME_JSON_BYTES,
    _len=len,
    _value_error=ValueError,
) -> None:
    encoded = _canonical_bytes(payload)
    if _len(encoded) > _caps.max_canonical_body_bytes:
        raise _value_error("runtime manifest canonical body exceeds resource cap")


def _validate_runtime_manifest_fields(
    manifest: RuntimeEvidenceManifest,
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _text_validator=_text,
    _source_validator=_source_closure,
    _sha_validator=_sha,
) -> None:
    _text_validator(
        manifest.runtime_schema_version,
        "runtime_schema_version",
        _caps=_caps,
    )
    _text_validator(manifest.evaluator_id, "evaluator_id", _caps=_caps)
    _source_validator(manifest.source_closure, _caps=_caps)
    _text_validator(manifest.python_version, "python_version", _caps=_caps)
    _text_validator(manifest.numpy_version, "numpy_version", _caps=_caps)
    _text_validator(manifest.scipy_version, "scipy_version", _caps=_caps)
    _sha_validator(
        manifest.blas_config_sha,
        "blas_config_sha",
        _caps=_caps,
    )
    _sha_validator(
        manifest.lapack_config_sha,
        "lapack_config_sha",
        _caps=_caps,
    )
    _text_validator(manifest.platform_id, "platform_id", _caps=_caps)
    _sha_validator(
        manifest.runtime_manifest_sha,
        "runtime_manifest_sha",
        _caps=_caps,
    )


@dataclass(frozen=True)
class RuntimeEvidenceManifest:
    __slots__ = (
        "runtime_schema_version",
        "evaluator_id",
        "source_closure",
        "python_version",
        "numpy_version",
        "scipy_version",
        "blas_config_sha",
        "lapack_config_sha",
        "platform_id",
        "runtime_manifest_sha",
    )

    runtime_schema_version: str
    evaluator_id: str
    source_closure: tuple[tuple[str, str], ...]
    python_version: str
    numpy_version: str
    scipy_version: str
    blas_config_sha: str
    lapack_config_sha: str
    platform_id: str
    runtime_manifest_sha: str

    def __post_init__(
        self,
        _validator=_validate_runtime_manifest_fields,
    ) -> None:
        _validator(self)


@dataclass(frozen=True)
class _RuntimeProbe:
    __slots__ = (
        "source_closure",
        "python_version",
        "numpy_version",
        "scipy_version",
        "blas_config_sha",
        "lapack_config_sha",
        "platform_id",
    )

    source_closure: tuple[tuple[str, str], ...]
    python_version: str
    numpy_version: str
    scipy_version: str
    blas_config_sha: str
    lapack_config_sha: str
    platform_id: str

    def __post_init__(
        self,
        _source_validator=_source_closure,
        _text_validator=_text,
        _sha_validator=_sha,
    ) -> None:
        _source_validator(self.source_closure)
        _text_validator(self.python_version, "python_version")
        _text_validator(self.numpy_version, "numpy_version")
        _text_validator(self.scipy_version, "scipy_version")
        _sha_validator(self.blas_config_sha, "blas_config_sha")
        _sha_validator(self.lapack_config_sha, "lapack_config_sha")
        _text_validator(self.platform_id, "platform_id")


def _runtime_evidence_manifest_payload_raw(
    manifest: RuntimeEvidenceManifest,
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _record_type=RuntimeEvidenceManifest,
    _validator=_validate_runtime_manifest_fields,
    _canonical_preflight=_preflight_canonical_payload,
    _type=type,
    _type_error=TypeError,
) -> dict[str, object]:
    if _type(manifest) is not _record_type:
        raise _type_error("manifest must be a RuntimeEvidenceManifest")
    _validator(manifest, _caps=_caps)
    payload: dict[str, object] = {
        "runtime_schema_version": manifest.runtime_schema_version,
        "evaluator_id": manifest.evaluator_id,
        "source_closure": [
            {
                "relative_path": path,
                "sha256": source_sha,
            }
            for path, source_sha in manifest.source_closure
        ],
        "python_version": manifest.python_version,
        "numpy_version": manifest.numpy_version,
        "scipy_version": manifest.scipy_version,
        "blas_config_sha": manifest.blas_config_sha,
        "lapack_config_sha": manifest.lapack_config_sha,
        "platform_id": manifest.platform_id,
    }
    _canonical_preflight(payload, _caps=_caps)
    return payload


def _exact_mapping_fields(
    value: object,
    expected: frozenset[str],
    field: str,
    *,
    _type=type,
    _dict_type=dict,
    _len=len,
    _set_type=set,
    _sorted=sorted,
    _type_error=TypeError,
    _value_error=ValueError,
) -> dict[str, object]:
    if _type(value) is not _dict_type:
        raise _type_error(f"{field} must be a plain dict")
    if _len(value) > _len(expected):
        raise _value_error(
            f"{field} schema mismatch; unknown field count exceeds the exact schema"
        )
    actual = _set_type(value)
    unknown = _sorted(actual - expected)
    missing = _sorted(expected - actual)
    if unknown or missing:
        raise _value_error(
            f"{field} schema mismatch; unknown={unknown}, missing={missing}"
        )
    return _dict_type(value)


def _probe_module_roots() -> tuple[str, ...]:
    return _MODULE_IMPORT_ROOTS


def _preflight_import_roots(
    roots: object,
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _text_validator=_text,
    _module_name_fullmatch=_MODULE_NAME.fullmatch,
    _type=type,
    _tuple_type=tuple,
    _len=len,
    _enumerate=enumerate,
    _sorted=sorted,
    _set_type=set,
    _type_error=TypeError,
    _value_error=ValueError,
) -> tuple[str, ...]:
    if _type(roots) is not _tuple_type:
        raise _type_error("import roots must be a tuple")
    if not roots:
        raise _value_error("import roots must be non-empty")
    if _len(roots) > _caps.max_import_roots:
        raise _value_error("import root count exceeds resource cap")
    result: list[str] = []
    for index, value in _enumerate(roots):
        name = _text_validator(
            value,
            f"import_roots[{index}]",
            _caps=_caps,
        )
        if _module_name_fullmatch(name) is None:
            raise _value_error(f"import_roots[{index}] is outside rulespace_v3")
        result.append(name)
    answer = _tuple_type(result)
    if answer != _tuple_type(_sorted(_set_type(answer))):
        raise _value_error("import roots must be unique and canonical")
    return answer


def _preflight_import_sources(
    repository_root: Path,
    roots: tuple[str, ...],
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _path_type=Path,
    _root_validator=_preflight_import_roots,
    _scandir=os.scandir,
    _isinstance=isinstance,
    _set_type=set,
    _sorted=sorted,
    _type_error=TypeError,
    _value_error=ValueError,
    _file_not_found_error=FileNotFoundError,
) -> None:
    """Conservatively bound package sources before executing any import."""

    if not _isinstance(repository_root, _path_type):
        raise _type_error("repository_root must be a Path")
    verified_roots = _root_validator(roots, _caps=_caps)
    try:
        root = repository_root.resolve(strict=True)
    except _file_not_found_error as exc:
        raise _value_error("before import repository root is missing") from exc
    package_root = root / "rulespace_v3"
    if not package_root.is_dir():
        raise _value_error("before import certificate package is missing")

    expected_paths = {
        _path_type(*module_name.split(".")).with_suffix(".py").as_posix()
        for module_name in verified_roots
    }
    seen_roots: set[str] = _set_type()
    pending = [package_root]
    directory_count = 1
    entry_count = 0
    source_count = 0
    total_source_bytes = 0

    while pending:
        directory = pending.pop()
        with _scandir(directory) as entries:
            for entry in entries:
                entry_count += 1
                if entry_count > _caps.max_package_entries:
                    raise _value_error(
                        "before import package entry count exceeds resource cap"
                    )
                if entry.is_symlink():
                    raise _value_error("before import package symlinks are forbidden")
                if entry.is_dir(follow_symlinks=False):
                    directory_count += 1
                    if directory_count > _caps.max_package_directories:
                        raise _value_error(
                            "before import package directory count exceeds resource cap"
                        )
                    pending.append(_path_type(entry.path))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                path = _path_type(entry.path)
                if path.suffix != ".py":
                    continue
                source_count += 1
                if source_count > _caps.max_source_files:
                    raise _value_error(
                        "before import source count exceeds resource cap"
                    )
                source_size = entry.stat(follow_symlinks=False).st_size
                if source_size > _caps.max_source_file_bytes:
                    raise _value_error("before import source file exceeds resource cap")
                total_source_bytes += source_size
                if total_source_bytes > _caps.max_total_source_bytes:
                    raise _value_error(
                        "before import source total exceeds resource cap"
                    )
                relative = path.relative_to(root).as_posix()
                if relative in expected_paths:
                    seen_roots.add(relative)

    missing = _sorted(expected_paths - seen_roots)
    if missing:
        raise _value_error(f"before import frozen roots are missing: {missing}")


_PROBE_SCRIPT_TEMPLATE = r"""
import hashlib
import importlib
import importlib.util
import io
import json
import math
import platform
import resource
import sys
from contextlib import redirect_stdout
from pathlib import Path

repo_root = Path(sys.argv[1]).resolve()
requested_module_roots = json.loads(sys.argv[2])
module_roots = __FROZEN_IMPORT_ROOTS__
if requested_module_roots != list(module_roots):
    raise ValueError(
        "requested import roots do not match frozen child authority"
    )
caps = json.loads(sys.argv[3])
output_path = Path(sys.argv[4])
file_limit = caps["max_subprocess_file_bytes"]
_, hard_file_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
if hard_file_limit == resource.RLIM_INFINITY:
    bounded_file_limit = file_limit
else:
    bounded_file_limit = min(file_limit, hard_file_limit)
resource.setrlimit(
    resource.RLIMIT_FSIZE,
    (bounded_file_limit, bounded_file_limit),
)
sys.path.insert(0, str(repo_root))

for module_name in module_roots:
    importlib.import_module(module_name)

import numpy as np
import scipy


config_budget = {"nodes": 0, "text_bytes": 0}


def bounded_text(value):
    if type(value) is not str:
        raise TypeError("configuration text must be a string")
    if len(value) > caps["max_config_text_bytes"]:
        raise ValueError("configuration text exceeds resource cap")
    size = len(value.encode("utf-8"))
    config_budget["text_bytes"] += size
    if (
        config_budget["text_bytes"]
        > caps["max_config_text_bytes"]
    ):
        raise ValueError("configuration text total exceeds resource cap")
    return value


def json_value(value, depth=0):
    if depth > caps["max_config_depth"]:
        raise ValueError("configuration depth exceeds resource cap")
    config_budget["nodes"] += 1
    if config_budget["nodes"] > caps["max_config_nodes"]:
        raise ValueError("configuration node count exceeds resource cap")
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        return bounded_text(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("configuration contains non-finite float")
        return value
    if isinstance(value, dict):
        if len(value) > caps["max_config_nodes"]:
            raise ValueError(
                "configuration mapping exceeds resource cap"
            )
        result = {}
        for key, item in value.items():
            checked_key = bounded_text(key)
            result[checked_key] = json_value(item, depth + 1)
        return result
    if type(value) in (list, tuple):
        if len(value) > caps["max_config_nodes"]:
            raise ValueError(
                "configuration array exceeds resource cap"
            )
        return [json_value(item, depth + 1) for item in value]
    raise TypeError(
        "configuration contains unsupported type "
        + type(value).__name__
    )


class BoundedTextIO(io.StringIO):
    def __init__(self):
        super().__init__()
        self.byte_count = 0

    def write(self, value):
        if type(value) is not str:
            raise TypeError("configuration output must be text")
        if len(value) > caps["max_config_text_bytes"]:
            raise ValueError(
                "configuration output exceeds resource cap"
            )
        self.byte_count += len(value.encode("utf-8"))
        if self.byte_count > caps["max_config_text_bytes"]:
            raise ValueError(
                "configuration output total exceeds resource cap"
            )
        return super().write(value)


def package_config(package):
    try:
        result = package.show_config(mode="dicts")
    except TypeError:
        stream = BoundedTextIO()
        with redirect_stdout(stream):
            package.show_config()
        result = {"legacy_text": stream.getvalue()}
    return json_value(result)


build_config = {
    "numpy": package_config(np),
    "scipy": package_config(scipy),
}


def config_sha(target):
    payload = {
        "build_config": build_config,
        "domain": target + "-configuration-v1",
    }
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(encoded) > caps["max_config_json_bytes"]:
        raise ValueError(
            "configuration canonical JSON exceeds resource cap"
        )
    return hashlib.sha256(encoded).hexdigest()


local_paths = set()
if len(sys.modules) > caps["max_loaded_modules"]:
    raise RuntimeError("loaded module count exceeds resource cap")
for module in tuple(sys.modules.values()):
    raw_path = getattr(module, "__file__", None)
    if type(raw_path) is not str:
        continue
    candidate = Path(raw_path)
    if candidate.suffix in (".pyc", ".pyo"):
        try:
            candidate = Path(importlib.util.source_from_cache(str(candidate)))
        except (ValueError, NotImplementedError):
            continue
    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(repo_root).as_posix()
    except (FileNotFoundError, ValueError):
        continue
    if resolved.suffix == ".py":
        item = (relative, resolved)
        if item not in local_paths:
            if len(local_paths) >= caps["max_source_files"]:
                raise RuntimeError(
                    "fresh probe source count exceeds resource cap"
                )
            local_paths.add(item)

if not local_paths:
    raise RuntimeError("fresh probe found no repository-local source files")
ordered_paths = sorted(local_paths, key=lambda item: item[0])
total_source_bytes = 0
closure = []
for relative, source_path in ordered_paths:
    source_size = source_path.stat().st_size
    if source_size > caps["max_source_file_bytes"]:
        raise RuntimeError("fresh probe source file exceeds resource cap")
    total_source_bytes += source_size
    if total_source_bytes > caps["max_total_source_bytes"]:
        raise RuntimeError("fresh probe source total exceeds resource cap")
    source = source_path.read_bytes()
    if len(source) != source_size:
        raise RuntimeError("fresh probe source changed while being read")
    closure.append([relative, hashlib.sha256(source).hexdigest()])

platform_id = json.dumps(
    {
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "pointer_bits": 64 if sys.maxsize > 2**32 else 32,
        "release": platform.release(),
        "sys_platform": sys.platform,
        "system": platform.system(),
    },
    allow_nan=False,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)
payload = {
    "source_closure": closure,
    "python_version": sys.version,
    "numpy_version": np.__version__,
    "scipy_version": scipy.__version__,
    "blas_config_sha": config_sha("blas"),
    "lapack_config_sha": config_sha("lapack"),
    "platform_id": platform_id,
}
encoded = json.dumps(
    payload,
    allow_nan=False,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
).encode("utf-8")
if len(encoded) > caps["max_probe_json_bytes"]:
    raise RuntimeError("fresh probe output exceeds resource cap")
with output_path.open("xb") as handle:
    handle.write(encoded)
"""


_PROBE_SCRIPT = _PROBE_SCRIPT_TEMPLATE.replace(
    "__FROZEN_IMPORT_ROOTS__",
    repr(_MODULE_IMPORT_ROOTS),
)
if "__FROZEN_IMPORT_ROOTS__" in _PROBE_SCRIPT:
    raise RuntimeError("fresh probe root authority was not frozen")

_V3_PROBE_SCRIPT = _PROBE_SCRIPT_TEMPLATE.replace(
    "__FROZEN_IMPORT_ROOTS__",
    repr(_V3_RUNTIME_IMPORT_ROOTS),
)
if "__FROZEN_IMPORT_ROOTS__" in _V3_PROBE_SCRIPT:
    raise RuntimeError("V3 fresh probe root authority was not frozen")


class _RuntimeAuthority(NamedTuple):
    runtime_schema_version: str
    evaluator_id: str
    repository_root: Path
    import_roots: tuple[str, ...]
    probe_script: str
    caps: _RuntimeCaps
    wire_fields: frozenset[str]
    probe_fields: frozenset[str]
    source_entry_fields: frozenset[str]
    manifest_slots: tuple[str, ...]


_MODULE_RUNTIME_AUTHORITY = _RuntimeAuthority(
    runtime_schema_version="v3m0.runtime-evidence-manifest.v1",
    evaluator_id="rulespace-v3m0-certificate-closure-v1",
    repository_root=_MODULE_REPOSITORY_ROOT,
    import_roots=_MODULE_IMPORT_ROOTS,
    probe_script=_PROBE_SCRIPT,
    caps=_RUNTIME_CAPS,
    wire_fields=_WIRE_FIELDS,
    probe_fields=_PROBE_FIELDS,
    source_entry_fields=_SOURCE_ENTRY_FIELDS,
    manifest_slots=tuple(RuntimeEvidenceManifest.__slots__),
)

_V3_RUNTIME_AUTHORITY = _RuntimeAuthority(
    runtime_schema_version="v3m0.runtime-evidence-manifest.v1",
    evaluator_id="rulespace-v3m0-parent-v3-certificate-closure-v1",
    repository_root=_MODULE_REPOSITORY_ROOT,
    import_roots=_V3_RUNTIME_IMPORT_ROOTS,
    probe_script=_V3_PROBE_SCRIPT,
    caps=_RUNTIME_CAPS,
    wire_fields=_WIRE_FIELDS,
    probe_fields=_PROBE_FIELDS,
    source_entry_fields=_SOURCE_ENTRY_FIELDS,
    manifest_slots=tuple(RuntimeEvidenceManifest.__slots__),
)


def _bounded_probe_environment(
    *,
    _environ=os.environ,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _type=type,
    _str_type=str,
    _len=len,
    _type_error=TypeError,
    _value_error=ValueError,
) -> dict[str, str]:
    if _len(_environ) > _caps.max_environment_entries:
        raise _value_error("probe environment entry count exceeds resource cap")
    result: dict[str, str] = {}
    total_bytes = 0
    for key, value in _environ.items():
        if _type(key) is not _str_type or _type(value) is not _str_type:
            raise _type_error("probe environment keys and values must be strings")
        if (
            _len(key) > _caps.max_environment_bytes
            or _len(value) > _caps.max_environment_bytes
        ):
            raise _value_error("probe environment item exceeds resource cap")
        total_bytes += _len(key.encode("utf-8"))
        total_bytes += _len(value.encode("utf-8"))
        if total_bytes > _caps.max_environment_bytes:
            raise _value_error("probe environment exceeds resource cap")
        if key != "PYTHONPATH":
            result[key] = value
    return result


def _run_frozen_subprocess(
    command: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str],
    stdin: int,
    stdout: int,
    stderr,
    check: bool,
    timeout: int,
    _popen_type=subprocess.Popen,
    _completed_process_type=subprocess.CompletedProcess,
    _timeout_expired=subprocess.TimeoutExpired,
    _value_error=ValueError,
):
    if check:
        raise _value_error(
            "the frozen probe runner requires explicit return-code handling"
        )
    process = _popen_type(
        command,
        cwd=cwd,
        env=env,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )
    try:
        returncode = process.wait(timeout=timeout)
    except _timeout_expired:
        process.kill()
        process.wait()
        raise
    return _completed_process_type(command, returncode)


def _launch_probe_subprocess(
    roots: tuple[str, ...],
    output_path: Path,
    *,
    _runner=_run_frozen_subprocess,
    _timeout_expired=subprocess.TimeoutExpired,
    _devnull: int = subprocess.DEVNULL,
    _authority: _RuntimeAuthority = _MODULE_RUNTIME_AUTHORITY,
    _root_validator=_preflight_import_roots,
    _environment_builder=_bounded_probe_environment,
    _json_encode=_RUNTIME_JSON_TEXT,
    _executable: str = sys.executable,
    _list_type=list,
    _str_type=str,
    _min=min,
    _value_error=ValueError,
    _runtime_error=RuntimeError,
) -> None:
    root = _authority.repository_root
    caps_authority = _authority.caps
    verified_roots = _root_validator(
        roots,
        _caps=caps_authority,
    )
    if verified_roots != _authority.import_roots:
        raise _value_error("import roots do not match the module-frozen authority")
    caps = {
        "max_source_files": caps_authority.max_source_files,
        "max_source_file_bytes": (caps_authority.max_source_file_bytes),
        "max_total_source_bytes": (caps_authority.max_total_source_bytes),
        "max_probe_json_bytes": caps_authority.max_probe_json_bytes,
        "max_subprocess_file_bytes": (caps_authority.max_subprocess_file_bytes),
        "max_config_nodes": caps_authority.max_config_nodes,
        "max_config_depth": caps_authority.max_config_depth,
        "max_config_text_bytes": (caps_authority.max_config_text_bytes),
        "max_config_json_bytes": (caps_authority.max_config_json_bytes),
        "max_loaded_modules": caps_authority.max_loaded_modules,
    }
    command = (
        _executable,
        "-I",
        "-B",
        "-c",
        _authority.probe_script,
        _str_type(root),
        _json_encode(_list_type(verified_roots)),
        _json_encode(caps),
        _str_type(output_path),
    )
    environment = _environment_builder(_caps=caps_authority)
    stderr_path = output_path.with_name("runtime-probe.stderr")
    try:
        with stderr_path.open("xb") as stderr_stream:
            completed = _runner(
                command,
                cwd=root,
                env=environment,
                stdin=_devnull,
                stdout=_devnull,
                stderr=stderr_stream,
                check=False,
                timeout=caps_authority.probe_timeout_seconds,
            )
            stderr_stream.flush()
    except _timeout_expired as exc:
        raise _runtime_error("fresh runtime probe timed out") from exc
    stderr_size = stderr_path.stat().st_size
    if stderr_size > caps_authority.max_subprocess_stderr_bytes:
        raise _runtime_error("fresh runtime probe stderr exceeds resource cap")
    if completed.returncode != 0:
        with stderr_path.open("rb") as handle:
            stderr = handle.read(_min(stderr_size, 4096))
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise _runtime_error(
            f"fresh runtime probe failed ({completed.returncode}): {detail}"
        )


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
    *,
    _value_error=ValueError,
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _value_error(f"probe output contains duplicate key {key!r}")
        result[key] = value
    return result


def _make_strict_probe_json_loader(
    *,
    _decoder_type=json.JSONDecoder,
    _object_pairs_hook=_reject_duplicate_json_keys,
    _type=type,
    _str_type=str,
    _len=len,
    _type_error=TypeError,
    _value_error=ValueError,
    _stop_iteration=StopIteration,
):
    decoder = _decoder_type(object_pairs_hook=_object_pairs_hook)
    scan_once = decoder.scan_once

    def strict_loads(value: str) -> object:
        if _type(value) is not _str_type:
            raise _type_error("probe JSON input must be a string")
        try:
            decoded, end = scan_once(value, 0)
        except _stop_iteration as exc:
            raise _value_error("probe JSON is malformed") from exc
        if end != _len(value):
            raise _value_error("probe JSON must contain exactly one compact value")
        return decoded

    return strict_loads


_STRICT_PROBE_JSON_LOADS = _make_strict_probe_json_loader()


def _load_probe_output(
    path: Path,
    *,
    _caps: _RuntimeCaps = _RUNTIME_CAPS,
    _json_loads=_STRICT_PROBE_JSON_LOADS,
    _exact_fields=_exact_mapping_fields,
    _relative_path_validator=_relative_source_path,
    _sha_validator=_sha,
    _text_validator=_text,
    _probe_type=_RuntimeProbe,
    _probe_fields: frozenset[str] = _PROBE_FIELDS,
    _path_type=Path,
    _isinstance=isinstance,
    _type=type,
    _list_type=list,
    _tuple_type=tuple,
    _len=len,
    _enumerate=enumerate,
    _type_error=TypeError,
    _value_error=ValueError,
    _unicode_decode_error=UnicodeDecodeError,
) -> _RuntimeProbe:
    if not _isinstance(path, _path_type):
        raise _type_error("probe output path must be a Path")
    size = path.stat().st_size
    if size <= 0 or size > _caps.max_probe_json_bytes:
        raise _value_error("probe output size is outside its resource cap")
    raw = path.read_bytes()
    if _len(raw) != size:
        raise _value_error("probe output changed while being read")
    try:
        decoded = raw.decode("utf-8", errors="strict")
        value = _json_loads(decoded)
    except (_unicode_decode_error, _value_error) as exc:
        raise _value_error("probe output is not strict UTF-8 JSON") from exc
    snapshot = _exact_fields(
        value,
        _probe_fields,
        "probe output",
    )

    raw_closure = snapshot["source_closure"]
    if _type(raw_closure) is not _list_type:
        raise _type_error("probe source_closure must be a list")
    if not raw_closure:
        raise _value_error("probe source_closure must be non-empty")
    if _len(raw_closure) > _caps.max_source_files:
        raise _value_error("probe source_closure exceeds its resource cap")
    closure: list[tuple[str, str]] = []
    for index, entry in _enumerate(raw_closure):
        if _type(entry) is not _list_type or _len(entry) != 2:
            raise _type_error(f"probe source_closure[{index}] must be a two-item list")
        closure.append(
            (
                _relative_path_validator(
                    entry[0],
                    f"probe source_closure[{index}].relative_path",
                    _caps=_caps,
                ),
                _sha_validator(
                    entry[1],
                    f"probe source_closure[{index}].sha256",
                    _caps=_caps,
                ),
            )
        )
    return _probe_type(
        source_closure=_tuple_type(closure),
        python_version=_text_validator(
            snapshot["python_version"],
            "probe python_version",
            _caps=_caps,
        ),
        numpy_version=_text_validator(
            snapshot["numpy_version"],
            "probe numpy_version",
            _caps=_caps,
        ),
        scipy_version=_text_validator(
            snapshot["scipy_version"],
            "probe scipy_version",
            _caps=_caps,
        ),
        blas_config_sha=_sha_validator(
            snapshot["blas_config_sha"],
            "probe blas_config_sha",
            _caps=_caps,
        ),
        lapack_config_sha=_sha_validator(
            snapshot["lapack_config_sha"],
            "probe lapack_config_sha",
            _caps=_caps,
        ),
        platform_id=_text_validator(
            snapshot["platform_id"],
            "probe platform_id",
            _caps=_caps,
        ),
    )


def _run_fresh_probe(
    *,
    _authority: _RuntimeAuthority = _MODULE_RUNTIME_AUTHORITY,
    _preflight_sources=_preflight_import_sources,
    _temporary_directory=tempfile.TemporaryDirectory,
    _launch=_launch_probe_subprocess,
    _load=_load_probe_output,
    _path_type=Path,
) -> _RuntimeProbe:
    roots = _authority.import_roots
    _preflight_sources(
        _authority.repository_root,
        roots,
        _caps=_authority.caps,
    )
    with _temporary_directory(prefix="v3m0-runtime-probe-") as directory:
        output_path = _path_type(directory) / "runtime-evidence.json"
        _launch(
            roots,
            output_path,
            _authority=_authority,
        )
        return _load(
            output_path,
            _caps=_authority.caps,
            _probe_fields=_authority.probe_fields,
        )


def _preflight_source_closure(
    closure: tuple[tuple[str, str], ...],
    *,
    _authority: _RuntimeAuthority = _MODULE_RUNTIME_AUTHORITY,
    _sha256=hashlib.sha256,
    _closure_validator=_source_closure,
    _len=len,
    _value_error=ValueError,
    _file_not_found_error=FileNotFoundError,
) -> None:
    """Hash the claimed closure before executing it in the fresh probe."""

    verified = _closure_validator(
        closure,
        _caps=_authority.caps,
    )
    root = _authority.repository_root
    caps_authority = _authority.caps
    total_source_bytes = 0
    for relative_path, expected_sha in verified:
        candidate = root / relative_path
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
        except (_file_not_found_error, _value_error) as exc:
            raise _value_error(
                f"source preflight missing/outside repository: {relative_path}"
            ) from exc
        if not resolved.is_file():
            raise _value_error(f"source preflight is not a file: {relative_path}")
        source_size = resolved.stat().st_size
        if source_size > caps_authority.max_source_file_bytes:
            raise _value_error(
                f"source preflight file exceeds resource cap: {relative_path}"
            )
        total_source_bytes += source_size
        if total_source_bytes > caps_authority.max_total_source_bytes:
            raise _value_error("source preflight total exceeds resource cap")
        source = resolved.read_bytes()
        if _len(source) != source_size:
            raise _value_error(f"source preflight changed while read: {relative_path}")
        actual_sha = _sha256(source).hexdigest()
        if actual_sha != expected_sha:
            raise _value_error(f"source preflight SHA mismatch: {relative_path}")


def _manifest_from_probe(
    probe: _RuntimeProbe,
    *,
    _authority: _RuntimeAuthority = _MODULE_RUNTIME_AUTHORITY,
    _payload=_runtime_evidence_manifest_payload_raw,
    _canonical_sha=_RUNTIME_CANONICAL_SHA,
    _probe_type=_RuntimeProbe,
    _record_type=RuntimeEvidenceManifest,
    _type=type,
    _type_error=TypeError,
) -> RuntimeEvidenceManifest:
    if _type(probe) is not _probe_type:
        raise _type_error("probe has the wrong record type")
    provisional = _record_type(
        runtime_schema_version=_authority.runtime_schema_version,
        evaluator_id=_authority.evaluator_id,
        source_closure=probe.source_closure,
        python_version=probe.python_version,
        numpy_version=probe.numpy_version,
        scipy_version=probe.scipy_version,
        blas_config_sha=probe.blas_config_sha,
        lapack_config_sha=probe.lapack_config_sha,
        platform_id=probe.platform_id,
        runtime_manifest_sha="0" * 64,
    )
    runtime_manifest_sha = _canonical_sha(_payload(provisional, _caps=_authority.caps))
    return _record_type(
        runtime_schema_version=provisional.runtime_schema_version,
        evaluator_id=provisional.evaluator_id,
        source_closure=provisional.source_closure,
        python_version=provisional.python_version,
        numpy_version=provisional.numpy_version,
        scipy_version=provisional.scipy_version,
        blas_config_sha=provisional.blas_config_sha,
        lapack_config_sha=provisional.lapack_config_sha,
        platform_id=provisional.platform_id,
        runtime_manifest_sha=runtime_manifest_sha,
    )


def _make_runtime_wire_api(
    authority: _RuntimeAuthority,
    *,
    _raw_payload=_runtime_evidence_manifest_payload_raw,
    _exact_fields=_exact_mapping_fields,
    _text_validator=_text,
    _relative_path_validator=_relative_source_path,
    _sha_validator=_sha,
    _record_validator=_validate_runtime_manifest_fields,
    _record_type=RuntimeEvidenceManifest,
    _canonical_sha=_RUNTIME_CANONICAL_SHA,
    _type=type,
    _list_type=list,
    _tuple_type=tuple,
    _len=len,
    _enumerate=enumerate,
    _hasattr=hasattr,
    _type_error=TypeError,
    _value_error=ValueError,
):
    exact_slots = authority.manifest_slots

    def validate_record(
        manifest: RuntimeEvidenceManifest,
    ) -> None:
        if _type(manifest) is not _record_type:
            raise _type_error("manifest must be a RuntimeEvidenceManifest")
        if (
            _hasattr(manifest, "__dict__")
            or _tuple_type(_type(manifest).__slots__) != exact_slots
        ):
            raise _value_error("RuntimeEvidenceManifest contains unknown record slots")
        _record_validator(manifest, _caps=authority.caps)
        if manifest.runtime_schema_version != authority.runtime_schema_version:
            raise _value_error("runtime_schema_version is not frozen")
        if manifest.evaluator_id != authority.evaluator_id:
            raise _value_error("evaluator_id is not frozen")

    def runtime_evidence_manifest_payload(
        manifest: RuntimeEvidenceManifest,
    ) -> dict[str, object]:
        validate_record(manifest)
        return _raw_payload(manifest, _caps=authority.caps)

    def runtime_evidence_manifest_to_wire(
        manifest: RuntimeEvidenceManifest,
    ) -> dict[str, object]:
        payload = runtime_evidence_manifest_payload(manifest)
        return {
            **payload,
            "runtime_manifest_sha": manifest.runtime_manifest_sha,
        }

    def runtime_evidence_manifest_from_wire(
        wire: object,
    ) -> RuntimeEvidenceManifest:
        snapshot = _exact_fields(
            wire,
            authority.wire_fields,
            "runtime wire",
        )
        schema_version = _text_validator(
            snapshot["runtime_schema_version"],
            "runtime_schema_version",
            _caps=authority.caps,
        )
        if schema_version != authority.runtime_schema_version:
            raise _value_error("runtime_schema_version is not frozen")
        evaluator_id = _text_validator(
            snapshot["evaluator_id"],
            "evaluator_id",
            _caps=authority.caps,
        )
        if evaluator_id != authority.evaluator_id:
            raise _value_error("evaluator_id is not frozen")

        raw_closure = snapshot["source_closure"]
        if _type(raw_closure) is not _list_type:
            raise _type_error("source_closure wire must be a list")
        if not raw_closure:
            raise _value_error("source_closure wire must be non-empty")
        if _len(raw_closure) > authority.caps.max_source_files:
            raise _value_error("source_closure exceeds its resource cap")

        closure: list[tuple[str, str]] = []
        for index, raw_entry in _enumerate(raw_closure):
            entry = _exact_fields(
                raw_entry,
                authority.source_entry_fields,
                f"source_closure[{index}]",
            )
            relative_path = _relative_path_validator(
                entry["relative_path"],
                f"source_closure[{index}].relative_path",
                _caps=authority.caps,
            )
            source_sha = _sha_validator(
                entry["sha256"],
                f"source_closure[{index}].sha256",
                _caps=authority.caps,
            )
            closure.append((relative_path, source_sha))

        manifest = _record_type(
            runtime_schema_version=schema_version,
            evaluator_id=evaluator_id,
            source_closure=_tuple_type(closure),
            python_version=snapshot["python_version"],
            numpy_version=snapshot["numpy_version"],
            scipy_version=snapshot["scipy_version"],
            blas_config_sha=snapshot["blas_config_sha"],
            lapack_config_sha=snapshot["lapack_config_sha"],
            platform_id=snapshot["platform_id"],
            runtime_manifest_sha=snapshot["runtime_manifest_sha"],
        )
        validate_record(manifest)
        expected_sha = _canonical_sha(runtime_evidence_manifest_payload(manifest))
        if manifest.runtime_manifest_sha != expected_sha:
            raise _value_error(
                "runtime_manifest_sha does not match the complete wire body"
            )
        return manifest

    return (
        runtime_evidence_manifest_payload,
        runtime_evidence_manifest_to_wire,
        runtime_evidence_manifest_from_wire,
    )


(
    runtime_evidence_manifest_payload,
    runtime_evidence_manifest_to_wire,
    runtime_evidence_manifest_from_wire,
) = _make_runtime_wire_api(_MODULE_RUNTIME_AUTHORITY)

_runtime_evidence_manifest_v3_payload = _make_runtime_wire_api(_V3_RUNTIME_AUTHORITY)[0]


def _make_runtime_public_api(
    authority: _RuntimeAuthority,
    *,
    _run_probe=_run_fresh_probe,
    _manifest_builder=_manifest_from_probe,
    _validator=_validate_runtime_manifest_fields,
    _payload=runtime_evidence_manifest_payload,
    _canonical_sha=_RUNTIME_CANONICAL_SHA,
    _preflight_source=_preflight_source_closure,
    _record_type=RuntimeEvidenceManifest,
    _type=type,
    _tuple_type=tuple,
    _hasattr=hasattr,
    _getattr=getattr,
    _type_error=TypeError,
    _value_error=ValueError,
):
    exact_slots = authority.manifest_slots

    def issue_runtime_evidence_manifest() -> RuntimeEvidenceManifest:
        """Issue from the module-frozen, resource-capped authority."""

        probe = _run_probe(_authority=authority)
        return _manifest_builder(probe, _authority=authority)

    def verify_runtime_evidence_manifest(
        manifest: RuntimeEvidenceManifest,
    ) -> RuntimeEvidenceManifest:
        """Recompute the complete body under the frozen authority."""

        if _type(manifest) is not _record_type:
            raise _type_error("manifest must be a RuntimeEvidenceManifest")
        if (
            _hasattr(manifest, "__dict__")
            or _tuple_type(_type(manifest).__slots__) != exact_slots
        ):
            raise _value_error("RuntimeEvidenceManifest contains unknown record slots")
        _validator(manifest, _caps=authority.caps)
        if manifest.runtime_schema_version != authority.runtime_schema_version:
            raise _value_error("runtime_schema_version is not frozen")
        if manifest.evaluator_id != authority.evaluator_id:
            raise _value_error("evaluator_id is not frozen")
        expected_hash = _canonical_sha(_payload(manifest))
        if manifest.runtime_manifest_sha != expected_hash:
            raise _value_error("runtime_manifest_sha does not match the complete body")

        _preflight_source(
            manifest.source_closure,
            _authority=authority,
        )
        expected = _manifest_builder(
            _run_probe(_authority=authority),
            _authority=authority,
        )
        for field in (
            "source_closure",
            "python_version",
            "numpy_version",
            "scipy_version",
            "blas_config_sha",
            "lapack_config_sha",
            "platform_id",
        ):
            if _getattr(manifest, field) != _getattr(expected, field):
                raise _value_error(f"fresh probe mismatch: {field}")
        if manifest.runtime_manifest_sha != expected.runtime_manifest_sha:
            raise _value_error("fresh probe mismatch: runtime_manifest_sha")
        return manifest

    return (
        issue_runtime_evidence_manifest,
        verify_runtime_evidence_manifest,
    )


(
    issue_runtime_evidence_manifest,
    verify_runtime_evidence_manifest,
) = _make_runtime_public_api(_MODULE_RUNTIME_AUTHORITY)

(
    _issue_runtime_evidence_manifest_v3,
    _verify_runtime_evidence_manifest_v3,
) = _make_runtime_public_api(
    _V3_RUNTIME_AUTHORITY,
    _payload=_runtime_evidence_manifest_v3_payload,
)


__all__ = [
    "RUNTIME_EVALUATOR_ID",
    "RUNTIME_MAX_CANONICAL_BODY_BYTES",
    "RUNTIME_MAX_IMPORT_ROOTS",
    "RUNTIME_MAX_PROBE_JSON_BYTES",
    "RUNTIME_MAX_SOURCE_FILE_BYTES",
    "RUNTIME_MAX_SOURCE_FILES",
    "RUNTIME_MAX_TOTAL_SOURCE_BYTES",
    "RUNTIME_SCHEMA_VERSION",
    "RuntimeEvidenceManifest",
    "issue_runtime_evidence_manifest",
    "runtime_evidence_manifest_from_wire",
    "runtime_evidence_manifest_payload",
    "runtime_evidence_manifest_to_wire",
    "verify_runtime_evidence_manifest",
]
