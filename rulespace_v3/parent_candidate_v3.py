"""Authority-neutral contracts for the Parent-v3 preparation candidate.

This module owns the canonical Parent-v3 candidate and registry roots.  It does
not issue a Parent capability; the repository-closed P-epoch replay is added in
the next implementation slice.
"""

from __future__ import annotations

import ast
import base64
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import sysconfig
import tempfile
from dataclasses import (
    dataclass,
    fields as dataclass_fields,
    is_dataclass,
    replace,
)
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Literal

from .evidence import canonical_sha
from .parent_candidate_v2 import (
    ParentFreezeCandidateV2Manifest,
    build_v3m0_parent_freeze_candidate_v2,
    parent_candidate_v2_manifest_payload,
    verify_parent_freeze_candidate_v2,
)
from .parent_freeze import (
    APPLICATION_CONTROL_CASE_IDS,
    ParentFreezeCandidateManifest,
    ParentFreezeManifest,
    build_v3m0_parent_freeze_candidate,
    issue_v3m0_parent_freeze,
    parent_freeze_candidate_manifest_payload,
    parent_freeze_manifest_payload,
    verify_parent_freeze_candidate,
)
from .parent_freeze_v2 import (
    build_reviewed_current_application_authorities_v2_raw,
    verify_reviewed_current_application_authorities_v2_raw,
)
from .parent_v2_contracts import (
    CurrentApplicationAuthorityV2,
    current_application_authority_v2_payload,
)
from .parent_v3_contracts import (
    CurrentApplicationAuthorityV3,
    _TRUSTED_GIT_EXECUTABLE_IDENTITY,
    _TRUSTED_GIT_EXECUTABLE_REALPATH,
    _TRUSTED_GIT_MAX_STDERR_BYTES,
    _TRUSTED_GIT_MAX_STDOUT_BYTES,
    _TRUSTED_GIT_TIMEOUT_SECONDS,
    _TRUSTED_PYTHON_EXECUTABLE_IDENTITY,
    _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
    _TRUSTED_PYTHON_FRAMEWORK_IDENTITY,
    _TRUSTED_PYTHON_FRAMEWORK_REALPATH,
    _TRUSTED_PYTHON_LAUNCHER_PATH,
    _git_read_object,
    _minimal_process_environment,
    _read_preparation_commit_blob,
    _read_preparation_commit_regular_blob,
    _replay_c19_current_application_authority_v3_at_preparation_commit,
    _require_preparation_commit_sha,
    _run_bounded_process,
    _trusted_git_environment,
    _verify_trusted_executable_identity,
    current_application_authority_v3_payload,
)


APPLICATION_SUPERSESSION_V3_SCHEMA_VERSION = (
    "v3m0.application-supersession.v3"
)
PARENT_FREEZE_CANDIDATE_V3_SCHEMA_VERSION = (
    "v3m0.parent-freeze-candidate.v3"
)
CURRENT_APPLICATION_REGISTRY_V3_SCHEMA_VERSION = (
    "v3m0.current-application-registry.v3"
)
PARENT_V3_SOURCE_CLOSURE_V1_SCHEMA_VERSION = (
    "v3m0.parent-v3-source-closure.v1"
)
REVIEWED_PATH_CLOSURE_V1_SCHEMA_VERSION = (
    "v3m0.parent-reviewed-path-closure.v1"
)

PARENT_V3_CANDIDATE_AUTHORITY_STATE = "PROVISIONAL_NOT_ISSUED"
PARENT_V3_PROGRAM_ID = "projective-rule-space-v3m0-v3"
C19_CONTROL_CASE_ID = "C19_FULL_POSITIVE_OBSERVER_COLLAPSE"
C19_HISTORICAL_APPLICATION_INSTANCE_ID = "v3m0.synthetic-control.c19.v1"
C19_REPLACEMENT_APPLICATION_INSTANCE_ID = "v3m0.synthetic-control.c19.v2"
C19_SUPERSESSION_REASON_ID = "C19_REAL20_PARENT_WIRE_REFREEZE_V2"

# Installed exactly once from a mechanically verified P tree.  It is not an
# authority input: candidate roots always carry and revalidate the full closure.
PARENT_V3_SOURCE_CLOSURE_PATHS: tuple[str, ...] = ()

_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_GIT_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_REGULAR_GIT_MODES = frozenset(("100644", "100755"))
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FRESH_AUDIT_REQUIRED_DEPENDENCY_MODULES = ("numpy", "sympy")


def _resolve_fresh_audit_external_import_roots() -> tuple[str, ...]:
    repository_root = _REPOSITORY_ROOT.resolve(strict=True)
    raw_roots: list[Path] = []
    raw_roots.extend(
        Path(raw)
        for raw in sys.path
        if raw and Path(raw).is_absolute() and Path(raw).is_dir()
    )
    stdlib_root = sysconfig.get_path("stdlib")
    if stdlib_root and Path(stdlib_root).is_dir():
        raw_roots.append(Path(stdlib_root))
        if (Path(stdlib_root) / "lib-dynload").is_dir():
            raw_roots.append(Path(stdlib_root) / "lib-dynload")
    extension_root = sysconfig.get_config_var("DESTSHARED")
    if extension_root and Path(extension_root).is_dir():
        raw_roots.append(Path(extension_root))
    for module_name in _FRESH_AUDIT_REQUIRED_DEPENDENCY_MODULES:
        spec = importlib.util.find_spec(module_name)
        if spec is None or not spec.submodule_search_locations:
            continue
        raw_roots.extend(
            Path(location).parent
            for location in spec.submodule_search_locations
        )

    resolved_roots: set[str] = set()
    for raw_root in raw_roots:
        if not raw_root.is_absolute():
            raise RuntimeError("fresh-audit external root is not absolute")
        try:
            resolved = raw_root.resolve(strict=True)
            metadata = resolved.stat()
        except OSError as exc:
            raise RuntimeError("fresh-audit external root cannot be resolved") from exc
        if not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeError("fresh-audit external root is not a directory")
        if resolved.is_relative_to(repository_root) or repository_root.is_relative_to(
            resolved
        ):
            continue
        resolved_roots.add(os.fspath(resolved))
    if not resolved_roots:
        raise RuntimeError("fresh-audit external roots are empty")
    return tuple(sorted(resolved_roots, key=lambda item: item.encode("utf-8")))


_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS = (
    _resolve_fresh_audit_external_import_roots()
)
_FRESH_AUDIT_SYSTEM_LIBRARY_ROOTS = tuple(
    sorted(
        {
            os.fspath(Path(raw_root).resolve(strict=True))
            for raw_root in (
                "/usr/lib",
                "/System/Library",
                "/lib",
                "/lib64",
                "/opt/homebrew/lib",
            )
            if Path(raw_root).is_dir()
        },
        key=lambda item: item.encode("utf-8"),
    )
)
_FRESH_AUDIT_AVAILABLE_DEPENDENCY_MODULES = tuple(
    module_name
    for module_name in _FRESH_AUDIT_REQUIRED_DEPENDENCY_MODULES
    if importlib.util.find_spec(module_name) is not None
)
_PARENT_V3_REVIEW_RECEIPT_PATHS = (
    "data/results/v3m0_parent_v3_review_authority.json",
    "data/results/v3m0_parent_v3_review_mathematics.json",
)
_PARENT_V3_MANDATORY_DRAFT_STATUS_BY_PATH = {
    "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md": (
        "*Computational Universe Lab · 2026-07-31 · "
        "状态：DRAFT / 未签发 / 不生效*"
    ),
    "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：DRAFT / 未签发 / 非 Parent、permit 或 scientific authority*"
    ),
    "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*"
    ),
    "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*"
    ),
}
_PARENT_V3_MANDATORY_SIGNED_STATUS_BY_PATH = {
    "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md": (
        "*Computational Universe Lab · 2026-07-31 · "
        "状态：SIGNED / 已签发 / 生效*"
    ),
    "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：SIGNED / 已签发 / 非 Parent、permit 或 scientific authority*"
    ),
    "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：SIGNED / 已签发 / 非 Parent、permit、runtime 或 scientific authority*"
    ),
    "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · "
        "状态：SIGNED / 已签发 / 非 Parent、permit、runtime 或 scientific authority*"
    ),
}
_PARENT_V3_SIGNING_LITERALS_PATH = (
    "rulespace_v3/parent_signing_literals_v1.py"
)
_PARENT_V3_SIGNING_LITERAL_SPEC = (
    ("PARENT_V3_PREPARATION_COMMIT_SHA", "str | None", None),
    ("PARENT_V3_REVIEWED_CANDIDATE_SHA256", "str | None", None),
    ("PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256", "str | None", None),
    (
        "PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH",
        "tuple[tuple[str, str], ...]",
        (),
    ),
    (
        "PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE",
        "tuple[tuple[str, str], ...]",
        (),
    ),
)

_FRESH_INTERPRETER_AUDIT_SCHEMA_VERSION = (
    "v3m0.parent-candidate-fresh-interpreter-audit.v1"
)
_FRESH_INTERPRETER_AUDIT_MODE = "PARENT_V3_CANDIDATE_P_REPLAY"
_FRESH_INTERPRETER_IMPORT_SMOKE_MODE = "DEPENDENCY_IMPORT_PATH_SMOKE"
_FRESH_INTERPRETER_CANDIDATE_IMPORT_SMOKE_MODE = (
    "REPOSITORY_CANDIDATE_IMPORT_SMOKE"
)
_FRESH_INTERPRETER_EVENT_PROBE_MODE = "SECURITY_EVENT_BOUNDARY_PROBE"
_FRESH_INTERPRETER_HOOK_STATE = "HOOK_INSTALLED_BEFORE_REPOSITORY_IMPORT"
_FRESH_AUDIT_FRAME_SCHEMA_VERSION = "v3m0.fresh-audit-frame.v1"
_FRESH_AUDIT_P_DATA_STATE = "P_DATA_VERIFIED_NOT_EXECUTED"
_FRESH_AUDIT_MAX_STDOUT_BYTES = 1 << 20
_FRESH_AUDIT_MAX_STDERR_BYTES = 1 << 16
_FRESH_AUDIT_TIMEOUT_SECONDS = 900
_FRESH_AUDIT_REQUIRED_REPOSITORY_MODULE_PATHS = frozenset(
    (
        "rulespace_v3/parent_candidate_v3.py",
        "rulespace_v3/parent_v3_contracts.py",
    )
)
# The active bootstrap keeps the audit authority inside one live function frame.
# Reviewed repository code can append untrusted stdout noise, but it cannot obtain
# the frame writer or its hash-chain state through ``__main__``/builtins.
_FRESH_AUDIT_BOOTSTRAP = r'''
import ast
import base64
import binascii
import collections
import contextlib
import contextvars
import copy
import ctypes
import dataclasses
import enum
import fractions
import functools
import hashlib
import importlib.abc
import importlib.util
import inspect
import io
import itertools
import json
import math
import operator
import os
import pathlib
import pickle
import re
import secrets
import selectors
import shutil
import signal
import stat
import struct
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
import tokenize
import types
import typing
import weakref

def _bootstrap():
    repository_root = os.path.realpath(os.getcwd())

    def reject_duplicate_pairs(pairs):
        result = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in result:
                raise RuntimeError("fresh audit request has duplicate/non-string keys")
            result[key] = value
        return result

    raw_request = sys.stdin.buffer.read(65537)
    if (
        not raw_request
        or len(raw_request) > 65536
        or raw_request.count(b"\n") != 1
        or not raw_request.endswith(b"\n")
    ):
        raise RuntimeError("fresh audit request wire is not one bounded JSON line")
    try:
        request = json.loads(
            raw_request[:-1].decode("utf-8"),
            object_pairs_hook=reject_duplicate_pairs,
        )
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise RuntimeError("fresh audit request is not strict JSON") from exc
    if not isinstance(request, dict):
        raise RuntimeError("fresh audit request is not an object")

    def canonical_bytes(value):
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

    if canonical_bytes(request) + b"\n" != raw_request:
        raise RuntimeError("fresh audit request JSON is not canonical")

    audit_mode = request.get("audit_mode")
    main_mode = "PARENT_V3_CANDIDATE_P_REPLAY"
    smoke_mode = "DEPENDENCY_IMPORT_PATH_SMOKE"
    candidate_import_mode = "REPOSITORY_CANDIDATE_IMPORT_SMOKE"
    event_probe_mode = "SECURITY_EVENT_BOUNDARY_PROBE"
    common_fields = {
        "audit_mode",
        "external_import_roots",
        "nonce",
        "p_data_not_executed",
        "source_closure",
        "trusted_git_executable_realpath",
        "trusted_python_executable_realpath",
    }
    if audit_mode == main_mode:
        expected_fields = common_fields | {
            "preparation_commit_sha",
            "preparation_tree_sha",
        }
    elif audit_mode == smoke_mode:
        expected_fields = common_fields | {"dependency_modules"}
    elif audit_mode == candidate_import_mode:
        expected_fields = common_fields
    elif audit_mode == event_probe_mode:
        expected_fields = common_fields | {"probe"}
    else:
        raise RuntimeError("fresh audit request mode is not allowlisted")
    if set(request) != expected_fields:
        raise RuntimeError("fresh audit request fields drifted")

    nonce = request["nonce"]
    if (
        not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
    ):
        raise RuntimeError("fresh audit request nonce is malformed")
    if audit_mode == main_mode:
        preparation_commit_sha = request["preparation_commit_sha"]
        preparation_tree_sha = request["preparation_tree_sha"]
        for name, object_id in (
            ("commit", preparation_commit_sha),
            ("tree", preparation_tree_sha),
        ):
            if (
                not isinstance(object_id, str)
                or len(object_id) != 40
                or any(character not in "0123456789abcdef" for character in object_id)
            ):
                raise RuntimeError("fresh audit preparation " + name + " is malformed")
    else:
        preparation_commit_sha = None
        preparation_tree_sha = None

    trusted_git = request["trusted_git_executable_realpath"]
    trusted_python = request["trusted_python_executable_realpath"]
    for label, executable in (("Git", trusted_git), ("Python", trusted_python)):
        if (
            not isinstance(executable, str)
            or not os.path.isabs(executable)
            or os.path.realpath(executable) != executable
        ):
            raise RuntimeError("fresh audit trusted " + label + " path drifted")
        try:
            metadata = os.stat(executable)
        except OSError as exc:
            raise RuntimeError("fresh audit trusted " + label + " is missing") from exc
        if not stat.S_ISREG(metadata.st_mode) or not os.access(executable, os.X_OK):
            raise RuntimeError("fresh audit trusted " + label + " is not executable")
    running_python = os.path.realpath(sys.executable)
    if running_python != trusted_python:
        running_python_directory = os.path.dirname(running_python)
        framework_application = os.path.realpath(
            os.path.join(
                running_python_directory,
                "..",
                "Resources",
                "Python.app",
                "Contents",
                "MacOS",
                "Python",
            )
        )
        if (
            os.path.basename(running_python_directory) != "bin"
            or framework_application != trusted_python
        ):
            raise RuntimeError("fresh audit Python executable identity drifted")
    trusted_python_framework = os.path.realpath(
        os.path.join(os.path.dirname(trusted_python), "../../../..", "Python3")
    )
    if not os.path.isfile(trusted_python_framework):
        trusted_python_framework = None

    expected_git_environment = {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_WORK_TREE": repository_root,
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.defpath,
    }
    expected_xcrun_environment = {
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.defpath,
    }

    def within(path, root):
        return path == root or path.startswith(root + os.sep)

    raw_external_roots = request["external_import_roots"]
    if (
        not isinstance(raw_external_roots, list)
        or not raw_external_roots
        or raw_external_roots
        != sorted(set(raw_external_roots), key=lambda item: item.encode("utf-8"))
    ):
        raise RuntimeError("fresh audit external roots are not canonical")
    external_roots = []
    for root in raw_external_roots:
        if (
            not isinstance(root, str)
            or not os.path.isabs(root)
            or os.path.realpath(root) != root
            or not os.path.isdir(root)
            or within(root, repository_root)
            or within(repository_root, root)
        ):
            raise RuntimeError("fresh audit external root drifted")
        external_roots.append(root)
    configured_paths = sysconfig.get_paths()
    required_interpreter_roots = []
    for configured in sys.path:
        if configured and os.path.isdir(configured):
            required_interpreter_roots.append(configured)
    for key in ("stdlib", "platstdlib"):
        configured = configured_paths.get(key)
        if configured and os.path.isdir(configured):
            required_interpreter_roots.append(configured)
    for configured in required_interpreter_roots:
        if os.path.realpath(configured) not in external_roots:
            raise RuntimeError("fresh audit omitted an active interpreter root")
    extension_root = sysconfig.get_config_var("DESTSHARED")
    if extension_root and os.path.isdir(extension_root):
        if os.path.realpath(extension_root) not in external_roots:
            raise RuntimeError("fresh audit omitted the extension root")

    pycache_root = getattr(sys, "pycache_prefix", None)
    if not isinstance(pycache_root, str) or not os.path.isabs(pycache_root):
        raise RuntimeError("fresh audit pycache root is not absolute")
    pycache_root = os.path.realpath(pycache_root)
    if (
        not os.path.isdir(pycache_root)
        or within(pycache_root, repository_root)
        or within(repository_root, pycache_root)
    ):
        raise RuntimeError("fresh audit pycache root drifted")

    system_library_roots = []
    for root in (
        "/usr/lib",
        "/System/Library",
        "/lib",
        "/lib64",
        "/opt/homebrew/lib",
    ):
        if os.path.isdir(root):
            resolved = os.path.realpath(root)
            if resolved not in system_library_roots:
                system_library_roots.append(resolved)
    system_entropy_device = "/dev/urandom"
    try:
        entropy_metadata = os.lstat(system_entropy_device)
    except OSError:
        system_entropy_device = None
    else:
        if (
            os.path.realpath(system_entropy_device) != system_entropy_device
            or not stat.S_ISCHR(entropy_metadata.st_mode)
        ):
            system_entropy_device = None

    def canonical_relative_path(value):
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
            or "\\" in value
            or value.startswith("/")
        ):
            return None
        parts = value.split("/")
        if any(part in ("", ".", "..") for part in parts):
            return None
        return value

    def classify_path(raw_path):
        if isinstance(raw_path, int):
            return "file-descriptor", None
        if not isinstance(raw_path, (str, bytes, os.PathLike)):
            raise RuntimeError("fresh audit observed a non-path value")
        path = os.path.abspath(os.fsdecode(raw_path))
        resolved = os.path.realpath(path)
        if (
            system_entropy_device is not None
            and path == system_entropy_device
            and resolved == system_entropy_device
        ):
            return "system-entropy", None
        if resolved in (
            trusted_git,
            trusted_python,
            trusted_python_framework,
            "/usr/bin/xcrun",
        ):
            return "trusted-executable", resolved
        if within(path, repository_root):
            relative = os.path.relpath(path, repository_root).replace(os.sep, "/")
            if relative == ".git" or relative.startswith(".git/"):
                raise RuntimeError("fresh audit observed repository Git metadata")
            if resolved != path or not within(resolved, repository_root):
                raise RuntimeError("fresh audit repository path used a symlink escape")
            return "repository", relative
        for root in external_roots:
            if within(path, root) and within(resolved, root):
                return "external", resolved
        if within(path, pycache_root) and within(resolved, pycache_root):
            return "pycache", resolved
        raise RuntimeError("fresh audit observed an unknown external path")

    def stable_file_identity(raw_path):
        path = os.path.realpath(os.fspath(raw_path))
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        lexical = os.lstat(path)
        descriptor = os.open(path, flags)
        digest = hashlib.sha256()
        try:
            opened = os.fstat(descriptor)
            fingerprint = (
                opened.st_dev,
                opened.st_ino,
                opened.st_mode,
                opened.st_size,
                opened.st_mtime_ns,
            )
            if (
                stat.S_ISLNK(lexical.st_mode)
                or not stat.S_ISREG(opened.st_mode)
                or (
                    lexical.st_dev,
                    lexical.st_ino,
                    lexical.st_mode,
                    lexical.st_size,
                    lexical.st_mtime_ns,
                ) != fingerprint
            ):
                raise RuntimeError("fresh audit stable file open raced")
            chunks = []
            while True:
                chunk = os.read(descriptor, 1 << 20)
                if not chunk:
                    break
                chunks.append(chunk)
                digest.update(chunk)
            final_opened = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final_lexical = os.lstat(path)
        if (
            (
                final_opened.st_dev,
                final_opened.st_ino,
                final_opened.st_mode,
                final_opened.st_size,
                final_opened.st_mtime_ns,
            ) != fingerprint
            or (
                final_lexical.st_dev,
                final_lexical.st_ino,
                final_lexical.st_mode,
                final_lexical.st_size,
                final_lexical.st_mtime_ns,
            ) != fingerprint
            or os.path.realpath(path) != path
        ):
            raise RuntimeError("fresh audit stable file pathname changed")
        record = {
            "path": path,
            "st_dev": opened.st_dev,
            "st_ino": opened.st_ino,
            "st_mode": opened.st_mode,
            "st_size": opened.st_size,
            "st_mtime_ns": opened.st_mtime_ns,
            "sha256": digest.hexdigest(),
        }
        return b"".join(chunks), record

    extension_suffixes = tuple(
        suffix
        for suffix in (
            ".so",
            ".dylib",
            ".dll",
            ".pyd",
        )
    )

    def make_frame_authority():
        sequence = 0
        previous_frame_sha = "0" * 64
        registered_code = {}
        dependency_phase = False
        lscpu_blocked = False
        scan_phase = False
        scan_index = 0
        dynamic_loading_locked = False

        def emit(kind, payload):
            nonlocal sequence, previous_frame_sha
            unsigned = {
                "frame_schema_version": "v3m0.fresh-audit-frame.v1",
                "kind": kind,
                "nonce": nonce,
                "payload": payload,
                "previous_frame_sha": previous_frame_sha,
                "sequence": sequence,
            }
            frame_sha = hashlib.sha256(canonical_bytes(unsigned)).hexdigest()
            frame = dict(unsigned)
            frame["frame_sha"] = frame_sha
            os.write(1, canonical_bytes(frame) + b"\n")
            previous_frame_sha = frame_sha
            sequence += 1

        def register_code(code, record):
            registered_code[id(code)] = (code, record)

        def set_dependency_phase(value):
            nonlocal dependency_phase
            dependency_phase = value

        def require_lscpu_blocked():
            if not lscpu_blocked:
                raise RuntimeError("fresh audit did not block NumPy lscpu")

        def set_scan_phase(value):
            nonlocal scan_phase
            scan_phase = value

        def require_exact_scans():
            if scan_index != 2:
                raise RuntimeError("fresh audit repository scan count drifted")

        def lock_dynamic_loading():
            nonlocal dynamic_loading_locked
            dynamic_loading_locked = True

        def hook(event, arguments):
            nonlocal lscpu_blocked, scan_index
            if dynamic_loading_locked and event in {
                "sys._getframe",
                "sys._current_frames",
                "gc.get_objects",
                "sys.settrace",
                "sys.setprofile",
            }:
                raise RuntimeError("fresh audit blocked authority introspection")
            if event == "open" and arguments:
                classification, relative = classify_path(arguments[0])
                if classification == "repository":
                    emit("file_read_path", relative)
            elif event == "import" and len(arguments) > 1 and arguments[1]:
                classification, observed = classify_path(arguments[1])
                if classification == "repository":
                    emit("module_path", observed)
                elif (
                    classification == "external"
                    and observed.endswith(extension_suffixes)
                ):
                    if dynamic_loading_locked:
                        raise RuntimeError("fresh audit rejected post-freeze extension import")
                    _, record = stable_file_identity(observed)
                    emit("dynamic_library", record)
            elif event == "exec" and arguments:
                code = arguments[0]
                filename = getattr(code, "co_filename", None)
                if (
                    isinstance(filename, str)
                    and not (filename.startswith("<") and filename.endswith(">"))
                    and within(
                    os.path.abspath(filename),
                    repository_root,
                    )
                ):
                    registered = registered_code.get(id(code))
                    if registered is None or registered[0] is not code:
                        raise RuntimeError("fresh audit rejected unregistered repository code")
                    emit("source_execution", registered[1])
            elif event in ("os.listdir", "os.scandir"):
                raw_path = arguments[0] if arguments and arguments[0] is not None else "."
                classification, relative = classify_path(raw_path)
                if classification == "repository":
                    expected_paths = (".", "rulespace_v3")
                    if (
                        event != "os.listdir"
                        or not scan_phase
                        or scan_index >= len(expected_paths)
                        or relative != expected_paths[scan_index]
                    ):
                        raise RuntimeError("fresh audit observed repository enumeration")
                    emit("repository_directory_scan", relative)
                    scan_index += 1
            elif event == "os.chdir":
                raise RuntimeError("fresh audit observed a working-directory change")
            elif event == "ctypes.dlopen":
                if dynamic_loading_locked:
                    raise RuntimeError("fresh audit rejected post-freeze dlopen")
                if not arguments or not isinstance(arguments[0], (str, bytes, os.PathLike)):
                    raise RuntimeError("fresh audit observed a non-path dlopen")
                dynamic_path = os.path.realpath(os.path.abspath(os.fsdecode(arguments[0])))
                allowed = any(
                    within(dynamic_path, root)
                    for root in (*external_roots, *system_library_roots)
                )
                if not allowed:
                    raise RuntimeError("fresh audit observed dlopen outside trusted roots")
                _, record = stable_file_identity(dynamic_path)
                emit("dynamic_library", record)
            elif event == "subprocess.Popen":
                executable, argv, cwd, environment = arguments
                executable = os.fsdecode(executable)
                if isinstance(argv, (str, bytes, os.PathLike)):
                    argv = (os.fsdecode(argv),)
                else:
                    argv = tuple(os.fsdecode(item) for item in argv)
                executable_realpath = os.path.realpath(executable)
                if (
                    dependency_phase
                    and not lscpu_blocked
                    and executable == "lscpu"
                    and argv == ("lscpu",)
                    and cwd is None
                    and environment is None
                ):
                    lscpu_blocked = True
                    raise OSError("fresh audit blocked optional NumPy lscpu")
                if (
                    executable_realpath == trusted_git
                    and argv
                    and argv[0] == trusted_git
                    and environment == expected_git_environment
                    and os.path.realpath(os.fspath(cwd)) == repository_root
                ):
                    emit(
                        "git_command",
                        {
                            "argv": list(argv),
                            "cwd_state": "EXACT_REPOSITORY_ROOT",
                            "executable_realpath": executable_realpath,
                            "shell": False,
                        },
                    )
                elif (
                    sys.platform == "darwin"
                    and executable_realpath == "/usr/bin/xcrun"
                    and argv == ("/usr/bin/xcrun", "--find", "git")
                    and os.path.realpath(os.fspath(cwd)) == "/"
                    and environment == expected_xcrun_environment
                ):
                    return
                else:
                    raise RuntimeError("fresh audit observed a non-allowlisted subprocess")

        return (
            hook,
            emit,
            register_code,
            set_dependency_phase,
            require_lscpu_blocked,
            set_scan_phase,
            require_exact_scans,
            lock_dynamic_loading,
        )

    (
        authority_hook,
        frame_writer,
        register_code,
        set_dependency_phase,
        require_lscpu_blocked,
        set_scan_phase,
        require_exact_scans,
        lock_dynamic_loading,
    ) = make_frame_authority()
    sys.addaudithook(authority_hook)
    frame_writer(
        "start",
        {"hook_installation_state": "HOOK_INSTALLED_BEFORE_REPOSITORY_IMPORT"},
    )

    sys.path[:] = []
    for path in reversed(tuple(external_roots)):
        sys.path.insert(0, path)

    if audit_mode in (main_mode, smoke_mode, candidate_import_mode):
        set_dependency_phase(True)
        try:
            __import__("numpy.testing")
        finally:
            set_dependency_phase(False)
        require_lscpu_blocked()
        try:
            __import__("sympy")
        except ImportError:
            pass

    raw_source_closure = request["source_closure"]
    if not isinstance(raw_source_closure, list):
        raise RuntimeError("fresh audit source closure is not an array")
    raw_p_data_not_executed = request["p_data_not_executed"]
    if not isinstance(raw_p_data_not_executed, list):
        raise RuntimeError("fresh audit inert P data is not an array")
    if audit_mode not in (main_mode, candidate_import_mode) and raw_p_data_not_executed:
        raise RuntimeError("fresh audit mode cannot carry inert P data")
    p_data_not_executed = {}
    for entry in raw_p_data_not_executed:
        if not isinstance(entry, dict) or set(entry) != {
            "execution_state",
            "mode",
            "path",
            "sha256",
            "source_base64",
        }:
            raise RuntimeError("fresh audit transported P data drifted")
        relative = canonical_relative_path(entry["path"])
        mode = entry["mode"]
        raw_sha = entry["sha256"]
        encoded_source = entry["source_base64"]
        if (
            relative != "rulespace_v3/parent_signing_literals_v1.py"
            or entry["execution_state"] != "P_DATA_VERIFIED_NOT_EXECUTED"
            or mode not in ("100644", "100755")
            or not isinstance(raw_sha, str)
            or len(raw_sha) != 64
            or any(character not in "0123456789abcdef" for character in raw_sha)
            or not isinstance(encoded_source, str)
            or relative in p_data_not_executed
        ):
            raise RuntimeError("fresh audit transported P data drifted")
        try:
            source_bytes = base64.b64decode(encoded_source, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise RuntimeError("fresh audit transported P data is not base64") from exc
        if (
            len(source_bytes) > 16384
            or base64.b64encode(source_bytes).decode("ascii") != encoded_source
            or hashlib.sha256(source_bytes).hexdigest() != raw_sha
        ):
            raise RuntimeError("fresh audit transported P data bytes drifted")
        p_data_not_executed[relative] = (mode, raw_sha)
    preloaded = {}
    observed_p_data_paths = set()
    previous_path = None
    for entry in raw_source_closure:
        if not isinstance(entry, dict) or set(entry) != {"mode", "path", "sha256"}:
            raise RuntimeError("fresh audit source entry drifted")
        relative = canonical_relative_path(entry["path"])
        mode = entry["mode"]
        raw_sha = entry["sha256"]
        if (
            relative is None
            or previous_path is not None
            and relative.encode("utf-8") <= previous_path.encode("utf-8")
            or mode not in ("100644", "100755")
            or not isinstance(raw_sha, str)
            or len(raw_sha) != 64
            or any(character not in "0123456789abcdef" for character in raw_sha)
        ):
            raise RuntimeError("fresh audit source closure is not canonical")
        previous_path = relative
        if not relative.endswith(".py"):
            continue
        inert_p_data = p_data_not_executed.get(relative)
        if inert_p_data is not None:
            if inert_p_data != (mode, raw_sha):
                raise RuntimeError("fresh audit transported P data entry drifted")
            observed_p_data_paths.add(relative)
            frame_writer(
                "p_data_state",
                {
                    "execution_state": "P_DATA_VERIFIED_NOT_EXECUTED",
                    "mode": mode,
                    "path": relative,
                    "sha256": raw_sha,
                },
            )
            continue
        absolute = os.path.join(repository_root, *relative.split("/"))
        source_bytes, record = stable_file_identity(absolute)
        observed_mode = "100755" if record["st_mode"] & 0o111 else "100644"
        if record["sha256"] != raw_sha or observed_mode != mode:
            raise RuntimeError("fresh audit live source differs from P")
        record["path"] = relative
        code = compile(source_bytes, absolute, "exec", dont_inherit=True)
        register_code(code, record)
        if relative == "rulespace_v3/__init__.py":
            module_name = "rulespace_v3"
            is_package = True
        elif relative.startswith("rulespace_v3/"):
            suffix = relative.removeprefix("rulespace_v3/")
            if suffix.endswith("/__init__.py"):
                module_name = "rulespace_v3." + suffix.removesuffix("/__init__.py").replace("/", ".")
                is_package = True
            else:
                module_name = "rulespace_v3." + suffix.removesuffix(".py").replace("/", ".")
                is_package = False
        else:
            continue
        if module_name in preloaded:
            raise RuntimeError("fresh audit duplicate module source")
        preloaded[module_name] = (code, absolute, is_package)
    if observed_p_data_paths != set(p_data_not_executed):
        raise RuntimeError("fresh audit transported P data is outside source closure")

    class _StableRepositorySourceLoader(importlib.abc.Loader):
        def __init__(self, code, source_path, is_package):
            self.code = code
            self.source_path = source_path
            self.is_package = is_package

        def create_module(self, spec):
            return None

        def exec_module(self, module):
            code = self.code
            self.code = None
            module.__file__ = self.source_path
            module.__cached__ = None
            module.__loader__ = self
            if self.is_package:
                module.__path__ = [os.path.dirname(self.source_path)]
            exec(code, module.__dict__)

    class _StableRepositorySourceFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname != "rulespace_v3" and not fullname.startswith("rulespace_v3."):
                return None
            selected = preloaded.get(fullname)
            if selected is None:
                raise ImportError("repository module is outside stable source closure")
            code, source_path, is_package = selected
            loader = _StableRepositorySourceLoader(code, source_path, is_package)
            return importlib.util.spec_from_loader(
                fullname,
                loader,
                origin=source_path,
                is_package=is_package,
            )

    if audit_mode in (main_mode, candidate_import_mode):
        if "rulespace_v3" not in preloaded:
            raise RuntimeError("fresh audit source closure omitted package root")
        sys.meta_path.insert(0, _StableRepositorySourceFinder())
        set_scan_phase(True)
        try:
            os.listdir(repository_root)
            os.listdir(os.path.join(repository_root, "rulespace_v3"))
        finally:
            set_scan_phase(False)
        require_exact_scans()
        lock_dynamic_loading()

    if audit_mode == smoke_mode:
        dependency_modules = request["dependency_modules"]
        if dependency_modules not in (["numpy"], ["numpy", "sympy"]):
            raise RuntimeError("fresh audit dependency smoke modules drifted")
        for module_name in dependency_modules:
            __import__(module_name)
        frame_writer(
            "final",
            {
                "audit_mode": smoke_mode,
                "dependency_initialization_state": (
                    "NUMPY_TESTING_IMPORTED_WITH_LSCPU_EXECUTION_BLOCKED"
                ),
                "hook_installation_state": "HOOK_INSTALLED_BEFORE_REPOSITORY_IMPORT",
                "imported_dependency_modules": dependency_modules,
                "python_executable_realpath": trusted_python,
            },
        )
        return

    if audit_mode == candidate_import_mode:
        candidate_module = __import__(
            "rulespace_v3.parent_candidate_v3",
            fromlist=("_validate_fresh_audit_process_identity",),
        )
        candidate_module._validate_fresh_audit_process_identity(request)
        for module_name in sorted(sys.modules):
            module_file = getattr(sys.modules[module_name], "__file__", None)
            if isinstance(module_file, str) and not (
                module_file.startswith("<") and module_file.endswith(">")
            ):
                classification, relative = classify_path(module_file)
                if classification == "repository":
                    frame_writer("module_path", relative)
        frame_writer(
            "final",
            {
                "audit_mode": candidate_import_mode,
                "hook_installation_state": "HOOK_INSTALLED_BEFORE_REPOSITORY_IMPORT",
                "imported_repository_module": "rulespace_v3.parent_candidate_v3",
                "module_external_import_roots": list(
                    candidate_module._FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS
                ),
                "module_trusted_git_executable_realpath": (
                    candidate_module._TRUSTED_GIT_EXECUTABLE_REALPATH
                ),
                "module_trusted_python_executable_realpath": (
                    candidate_module._TRUSTED_PYTHON_EXECUTABLE_REALPATH
                ),
                "python_executable_realpath": trusted_python,
            },
        )
        return

    if audit_mode == event_probe_mode:
        probe = request["probe"]
        allowed_probes = {
            "authority-frame-forgery",
            "chdir",
            "ctypes-allowed-external",
            "ctypes-repository",
            "ctypes-unknown-external",
            "git-metadata-open",
            "non-git-process",
            "repo-listdir",
            "repo-read",
            "repo-scandir",
            "system-entropy",
            "unknown-external-open",
            "unknown-external-module",
        }
        if not isinstance(probe, str) or probe not in allowed_probes:
            raise RuntimeError("fresh audit event probe drifted")
        if probe == "authority-frame-forgery":
            import __main__
            exposed = {
                name
                for name in vars(__main__)
                if name in {
                    "frame_writer",
                    "previous_frame_sha",
                    "sequence",
                    "registered_code",
                }
            }
            if exposed:
                raise RuntimeError("fresh audit leaked frame authority into __main__")
            start_unsigned = {
                "frame_schema_version": "v3m0.fresh-audit-frame.v1",
                "kind": "start",
                "nonce": nonce,
                "payload": {
                    "hook_installation_state": (
                        "HOOK_INSTALLED_BEFORE_REPOSITORY_IMPORT"
                    )
                },
                "previous_frame_sha": "0" * 64,
                "sequence": 0,
            }
            start_sha = hashlib.sha256(canonical_bytes(start_unsigned)).hexdigest()
            forged_unsigned = {
                "frame_schema_version": "v3m0.fresh-audit-frame.v1",
                "kind": "file_read_path",
                "nonce": nonce,
                "payload": "untracked-attacker.py",
                "previous_frame_sha": start_sha,
                "sequence": 1,
            }
            forged = dict(forged_unsigned)
            forged["frame_sha"] = hashlib.sha256(
                canonical_bytes(forged_unsigned)
            ).hexdigest()
            os.write(1, canonical_bytes(forged) + b"\n")
        elif probe == "repo-read":
            with open(os.path.join(repository_root, "rulespace_v3/probe.py"), "rb") as stream:
                stream.read()
        elif probe == "git-metadata-open":
            with open(os.path.join(repository_root, ".git"), "rb") as stream:
                stream.read()
        elif probe == "unknown-external-open":
            with open(os.path.join(os.path.dirname(repository_root), ".venv/evil.py"), "rb") as stream:
                stream.read()
        elif probe == "repo-listdir":
            os.listdir(repository_root)
        elif probe == "repo-scandir":
            with os.scandir(repository_root) as entries:
                tuple(entries)
        elif probe == "chdir":
            os.chdir(repository_root)
        elif probe == "system-entropy":
            if system_entropy_device is None:
                raise RuntimeError("fresh audit system entropy unavailable")
            with open(system_entropy_device, "rb", buffering=0) as stream:
                stream.read(1)
        elif probe.startswith("ctypes-"):
            if probe == "ctypes-allowed-external":
                import math
                ctypes.CDLL(math.__file__)
            elif probe == "ctypes-repository":
                ctypes.CDLL(os.path.join(repository_root, "rulespace_v3/probe.py"))
            else:
                ctypes.CDLL(os.path.join(os.path.dirname(repository_root), ".venv/evil.py"))
        elif probe == "unknown-external-module":
            import types
            attacker = types.ModuleType("fresh_audit_attacker")
            attacker.__file__ = os.path.join(os.path.dirname(repository_root), ".venv/evil.py")
            sys.modules[attacker.__name__] = attacker
            classify_path(attacker.__file__)
        else:
            import subprocess
            marker = os.path.join(repository_root, "process-marker")
            subprocess.run(
                (trusted_python, "-c", "open(" + repr(marker) + ", 'wb').write(b'executed')"),
                cwd=repository_root,
                check=False,
                shell=False,
                env={"PATH": os.defpath, "LANG": "C", "LC_ALL": "C"},
            )
        frame_writer("final", {"audit_mode": event_probe_mode, "probe": probe})
        return

    from rulespace_v3.parent_candidate_v3 import _fresh_audit_child_main
    result = _fresh_audit_child_main(request)
    for module_name in sorted(sys.modules):
        module_file = getattr(sys.modules[module_name], "__file__", None)
        if isinstance(module_file, str) and not (
            module_file.startswith("<") and module_file.endswith(">")
        ):
            classification, relative = classify_path(module_file)
            if classification == "repository":
                frame_writer("module_path", relative)
    frame_writer("final", result)

_bootstrap()
'''.strip()


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha256(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA256.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _git_sha1(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_GIT_SHA1.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase Git SHA-1")
    return result


def _require_exact_wire_tree(
    value: object,
    field: str,
    *,
    active: set[int] | None = None,
) -> None:
    """Reject unknown dataclass fields and every non-exact wire container."""

    if active is None:
        active = set()
    if is_dataclass(value) and not isinstance(value, type):
        identity = id(value)
        if identity in active:
            raise ValueError(f"{field} contains a recursive dataclass cycle")
        active.add(identity)
        try:
            record_type = type(value)
            _exact_record(value, record_type, field)
            for item in dataclass_fields(record_type):
                _require_exact_wire_tree(
                    getattr(value, item.name),
                    f"{field}.{item.name}",
                    active=active,
                )
        finally:
            active.remove(identity)
        return
    if type(value) in (tuple, list):
        identity = id(value)
        if identity in active:
            raise ValueError(f"{field} contains a recursive container cycle")
        active.add(identity)
        try:
            for index, item in enumerate(value):
                _require_exact_wire_tree(
                    item,
                    f"{field}[{index}]",
                    active=active,
                )
        finally:
            active.remove(identity)
        return
    if type(value) is dict:
        identity = id(value)
        if identity in active:
            raise ValueError(f"{field} contains a recursive dictionary cycle")
        active.add(identity)
        try:
            for index, (key, item) in enumerate(value.items()):
                _require_exact_wire_tree(
                    key,
                    f"{field}.key[{index}]",
                    active=active,
                )
                _require_exact_wire_tree(
                    item,
                    f"{field}[{key!r}]",
                    active=active,
                )
        finally:
            active.remove(identity)
        return
    if isinstance(value, Enum):
        return
    if type(value) in (str, int, float, bool, type(None)):
        return
    raise TypeError(
        f"{field} contains a non-exact wire value of type {type(value).__name__}"
    )


def _require_exact_recursive_match(
    observed: object,
    expected: object,
    field: str,
) -> None:
    if type(observed) is not type(expected):
        raise TypeError(
            f"{field} type differs from the P replay: "
            f"{type(observed).__name__} != {type(expected).__name__}"
        )
    if is_dataclass(expected) and not isinstance(expected, type):
        record_type = type(expected)
        _exact_record(observed, record_type, field)
        for item in dataclass_fields(record_type):
            _require_exact_recursive_match(
                getattr(observed, item.name),
                getattr(expected, item.name),
                f"{field}.{item.name}",
            )
        return
    if type(expected) in (tuple, list):
        if len(observed) != len(expected):
            raise ValueError(f"{field} length differs from the P replay")
        for index, (observed_item, expected_item) in enumerate(
            zip(observed, expected)
        ):
            _require_exact_recursive_match(
                observed_item,
                expected_item,
                f"{field}[{index}]",
            )
        return
    if type(expected) is dict:
        if tuple(observed) != tuple(expected):
            raise ValueError(f"{field} keys differ from the P replay")
        for key in expected:
            _require_exact_recursive_match(
                observed[key],
                expected[key],
                f"{field}[{key!r}]",
            )
        return
    if observed != expected:
        raise ValueError(f"{field} differs from the P replay")


def _relative_path(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value or "\x00" in value or "\\" in value:
        raise ValueError(f"{field} is not a canonical repository-relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or "." in path.parts
        or ".." in path.parts
    ):
        raise ValueError(f"{field} is not a canonical repository-relative path")
    return value


SourceClosureV1 = tuple[tuple[str, str, str], ...]
ReviewedPathClosureV1 = tuple[tuple[str, str], ...]


def _validated_source_closure(source_closure: object) -> SourceClosureV1:
    if type(source_closure) is not tuple or not source_closure:
        raise TypeError("source_closure must be a non-empty exact tuple")
    paths: list[str] = []
    result: list[tuple[str, str, str]] = []
    for index, entry in enumerate(source_closure):
        if type(entry) is not tuple or len(entry) != 3:
            raise TypeError(
                f"source_closure[{index}] must be an exact path/mode/SHA tuple"
            )
        path = _relative_path(entry[0], f"source_closure[{index}].relative_path")
        mode = _text(entry[1], f"source_closure[{index}].git_mode")
        if mode not in _REGULAR_GIT_MODES:
            raise ValueError(f"source_closure[{index}].git_mode is not regular")
        raw_sha = _sha256(entry[2], f"source_closure[{index}].raw_sha256")
        paths.append(path)
        result.append((path, mode, raw_sha))
    if tuple(paths) != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
        raise ValueError("source_closure is not in UTF-8 path order")
    if len(paths) != len(set(paths)):
        raise ValueError("source_closure contains duplicate paths")
    return tuple(result)


@dataclass(frozen=True)
class _FreshInterpreterAuditExpectation:
    preparation_commit_sha: str
    preparation_tree_sha: str
    candidate_sha: str
    source_closure_sha: str
    source_closure: SourceClosureV1
    trusted_git_executable_realpath: str
    trusted_python_executable_realpath: str

    def __post_init__(self) -> None:
        _git_sha1(self.preparation_commit_sha, "audit preparation_commit_sha")
        _git_sha1(self.preparation_tree_sha, "audit preparation_tree_sha")
        _sha256(self.candidate_sha, "audit candidate_sha")
        _sha256(self.source_closure_sha, "audit source_closure_sha")
        _validated_source_closure(self.source_closure)
        trusted_git = _text(
            self.trusted_git_executable_realpath,
            "audit trusted_git_executable_realpath",
        )
        if trusted_git != _TRUSTED_GIT_EXECUTABLE_REALPATH:
            raise ValueError("fresh audit trusted Git executable drifted")
        trusted_python = _text(
            self.trusted_python_executable_realpath,
            "audit trusted_python_executable_realpath",
        )
        if trusted_python != _TRUSTED_PYTHON_EXECUTABLE_REALPATH:
            raise ValueError("fresh audit trusted Python executable drifted")


def _fresh_audit_expectation_from_candidate(
    candidate: ParentFreezeCandidateV3Manifest,
) -> _FreshInterpreterAuditExpectation:
    _exact_record(candidate, ParentFreezeCandidateV3Manifest, "Parent-v3 candidate")
    _commit_sha, tree_sha = _require_preparation_commit_sha(
        candidate.preparation_commit_sha
    )
    return _FreshInterpreterAuditExpectation(
        preparation_commit_sha=candidate.preparation_commit_sha,
        preparation_tree_sha=tree_sha,
        candidate_sha=candidate.candidate_sha,
        source_closure_sha=candidate.source_closure_sha,
        source_closure=candidate.source_closure,
        trusted_git_executable_realpath=_TRUSTED_GIT_EXECUTABLE_REALPATH,
        trusted_python_executable_realpath=(
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    )


def _validate_fresh_audit_process_identity(request: object) -> None:
    if type(request) is not dict:
        raise RuntimeError("fresh-audit child frozen process identity drifted")
    required = {
        "external_import_roots",
        "trusted_git_executable_realpath",
        "trusted_python_executable_realpath",
    }
    if not required.issubset(request):
        raise RuntimeError("fresh-audit child frozen process identity drifted")
    if (
        request["trusted_git_executable_realpath"]
        != _TRUSTED_GIT_EXECUTABLE_REALPATH
        or request["trusted_python_executable_realpath"]
        != _TRUSTED_PYTHON_EXECUTABLE_REALPATH
        or request["external_import_roots"]
        != list(_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS)
    ):
        raise RuntimeError("fresh-audit child frozen process identity drifted")


def _build_fresh_audit_p_data_not_executed(
    expectation: _FreshInterpreterAuditExpectation,
) -> list[dict[str, str]]:
    """Transport the unique P-only signing module as verified, inert data."""

    _exact_record(
        expectation,
        _FreshInterpreterAuditExpectation,
        "fresh-audit expectation",
    )
    expectation.__post_init__()
    closure = {
        path: (mode, raw_sha)
        for path, mode, raw_sha in _validated_source_closure(
            expectation.source_closure
        )
    }
    expected = closure.get(_PARENT_V3_SIGNING_LITERALS_PATH)
    if expected is None:
        return []
    expected_mode, expected_sha = expected
    observed_mode, raw = _read_preparation_commit_regular_blob(
        expectation.preparation_commit_sha,
        _PARENT_V3_SIGNING_LITERALS_PATH,
    )
    if len(raw) > 16384:
        raise ValueError("fresh-audit inert P data exceeds its bound")
    observed_sha = hashlib.sha256(raw).hexdigest()
    if observed_mode != expected_mode or observed_sha != expected_sha:
        raise ValueError("fresh-audit inert P data differs from source closure")
    _validate_parent_signing_placeholder_blob(raw)
    return [
        {
            "execution_state": _FRESH_AUDIT_P_DATA_STATE,
            "mode": observed_mode,
            "path": _PARENT_V3_SIGNING_LITERALS_PATH,
            "sha256": observed_sha,
            "source_base64": base64.b64encode(raw).decode("ascii"),
        }
    ]


def _validated_reviewed_path_closure(
    reviewed_path_closure: object,
) -> ReviewedPathClosureV1:
    if type(reviewed_path_closure) is not tuple or not reviewed_path_closure:
        raise TypeError("reviewed_path_closure must be a non-empty exact tuple")
    paths: list[str] = []
    result: list[tuple[str, str]] = []
    for index, entry in enumerate(reviewed_path_closure):
        if type(entry) is not tuple or len(entry) != 2:
            raise TypeError(
                f"reviewed_path_closure[{index}] must be an exact path/SHA pair"
            )
        path = _relative_path(
            entry[0],
            f"reviewed_path_closure[{index}].relative_path",
        )
        raw_sha = _sha256(
            entry[1],
            f"reviewed_path_closure[{index}].raw_sha256",
        )
        paths.append(path)
        result.append((path, raw_sha))
    if tuple(paths) != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
        raise ValueError("reviewed_path_closure is not in UTF-8 path order")
    if len(paths) != len(set(paths)):
        raise ValueError("reviewed_path_closure contains duplicate paths")
    return tuple(result)


def _project_source_closure_to_reviewed_path_closure(
    source_closure: SourceClosureV1,
) -> ReviewedPathClosureV1:
    entries = _validated_source_closure(source_closure)
    return tuple((path, raw_sha) for path, _mode, raw_sha in entries)


_SLICE2_CORE_REPLAY_SOURCE_PATHS = (
    "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md",
    "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md",
    "rulespace_v3/c19_refreeze_v2.py",
    "rulespace_v3/parent_candidate_v2.py",
    "rulespace_v3/parent_freeze.py",
    "rulespace_v3/parent_freeze_v2.py",
    "rulespace_v3/parent_v3_contracts.py",
)


def _source_path_is_selected(relative_path: str) -> bool:
    path = PurePosixPath(relative_path)
    parts = path.parts
    if len(parts) == 2 and parts[0] == "docsv3" and path.suffix == ".md":
        return True
    if (
        len(parts) >= 3
        and parts[:2] == ("formal", "v3m0")
        and ".lake" not in parts[2:]
    ):
        return True
    if len(parts) >= 2 and parts[0] == "rulespace_v3" and path.suffix == ".py":
        return True
    if (
        len(parts) == 2
        and parts[0] == "rulespace_gpu"
        and parts[1].startswith("v3_")
        and path.suffix == ".py"
    ):
        return True
    if (
        len(parts) == 2
        and parts[0] == "tests"
        and (
            parts[1].startswith("test_v3m0_")
            or parts[1].startswith("test_v3_gpu_")
        )
        and path.suffix == ".py"
    ):
        return True
    if (
        len(parts) == 2
        and parts[0] == "experiments"
        and parts[1].startswith("v3m0_")
        and path.suffix == ".py"
    ):
        return True
    return bool(
        len(parts) == 3
        and parts[:2] == ("data", "results")
        and parts[2].startswith("v3m0_")
        and path.suffix == ".json"
    )


def _enumerate_parent_v3_source_entries_at_preparation_commit(
    preparation_commit_sha: str,
) -> tuple[tuple[str, str, str], ...]:
    """Enumerate selected P paths/modes/blob OIDs without reading blob bytes."""

    commit_sha, tree_sha = _require_preparation_commit_sha(
        preparation_commit_sha
    )
    tree = _git_read_object(
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        tree_sha,
        "--",
    )
    if tree.returncode != 0 or tree.stderr != b"":
        raise ValueError("preparation source tree cannot be enumerated")
    raw_records = tree.stdout.split(b"\x00")
    if not raw_records or raw_records[-1] != b"":
        raise ValueError("preparation source tree is not NUL terminated")
    selected: list[tuple[str, str, str]] = []
    seen_paths: set[str] = set()
    for index, raw_record in enumerate(raw_records[:-1]):
        metadata, separator, raw_path = raw_record.partition(b"\t")
        if separator != b"\t" or not raw_path:
            raise ValueError(f"preparation tree entry {index} is malformed")
        fields = metadata.split(b" ")
        if len(fields) != 3:
            raise ValueError(f"preparation tree metadata {index} is malformed")
        raw_mode, object_type, raw_object_id = fields
        try:
            relative_path = raw_path.decode("utf-8")
            git_mode = raw_mode.decode("ascii")
            object_id = raw_object_id.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("preparation source tree metadata is not UTF-8/ASCII") from exc
        canonical_path = _relative_path(relative_path, "preparation source path")
        if canonical_path in seen_paths:
            raise ValueError("preparation source tree contains duplicate paths")
        seen_paths.add(canonical_path)
        if not _source_path_is_selected(canonical_path):
            continue
        if git_mode not in _REGULAR_GIT_MODES or object_type != b"blob":
            raise ValueError("selected preparation source is not a regular Git blob")
        if _LOWER_GIT_SHA1.fullmatch(object_id) is None:
            raise ValueError("selected preparation blob OID is not Git SHA-1")
        selected.append((canonical_path, git_mode, object_id))
    selected.sort(key=lambda item: item[0].encode("utf-8"))
    selected_paths = frozenset(item[0] for item in selected)
    missing_core = tuple(
        path
        for path in _SLICE2_CORE_REPLAY_SOURCE_PATHS
        if path not in selected_paths
    )
    if missing_core:
        raise ValueError(
            "preparation source closure lacks core replay paths: "
            + ", ".join(missing_core)
        )
    return tuple(selected)


def _select_parent_v3_source_closure_at_preparation_commit(
    preparation_commit_sha: str,
) -> SourceClosureV1:
    """Mechanically select the complete regular-blob family from one P tree."""

    commit_sha = _git_sha1(
        preparation_commit_sha,
        "preparation source commit",
    )
    entries = _enumerate_parent_v3_source_entries_at_preparation_commit(
        commit_sha
    )
    selected = tuple(
        (
            canonical_path,
            git_mode,
            hashlib.sha256(
                _read_preparation_commit_blob(commit_sha, canonical_path)
            ).hexdigest(),
        )
        for canonical_path, git_mode, _object_id in entries
    )
    return _validated_source_closure(selected)


def _freeze_parent_v3_source_closure_paths(
    source_closure: SourceClosureV1,
) -> tuple[str, ...]:
    """Freeze a path snapshot only after its full candidate replay succeeds."""

    closure = _validated_source_closure(source_closure)
    paths = tuple(item[0] for item in closure)
    if paths != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
        raise ValueError("Parent-v3 source path snapshot is not in UTF-8 order")
    if len(paths) != len(set(paths)):
        raise ValueError("Parent-v3 source path snapshot contains duplicates")
    global PARENT_V3_SOURCE_CLOSURE_PATHS
    installed = PARENT_V3_SOURCE_CLOSURE_PATHS
    if type(installed) is not tuple:
        raise TypeError("Parent-v3 source path snapshot has the wrong type")
    if installed and installed != paths:
        raise ValueError("Parent-v3 source path snapshot changed after installation")
    PARENT_V3_SOURCE_CLOSURE_PATHS = paths
    return paths


@dataclass(frozen=True)
class ApplicationSupersessionV3:
    supersession_schema_version: str
    control_case_id: str
    superseded_application_instance_id: str
    superseded_application_authority_v2_sha: str
    replacement_application_instance_id: str
    replacement_application_authority_v3_sha: str
    reason_id: str
    supersession_sha: str

    def __post_init__(self) -> None:
        if self.supersession_schema_version != (
            APPLICATION_SUPERSESSION_V3_SCHEMA_VERSION
        ):
            raise ValueError("application supersession schema drifted")
        if self.control_case_id != C19_CONTROL_CASE_ID:
            raise ValueError("application supersession control ID drifted")
        if self.superseded_application_instance_id != (
            C19_HISTORICAL_APPLICATION_INSTANCE_ID
        ):
            raise ValueError("superseded C19 application ID drifted")
        if self.replacement_application_instance_id != (
            C19_REPLACEMENT_APPLICATION_INSTANCE_ID
        ):
            raise ValueError("replacement C19 application ID drifted")
        if self.reason_id != C19_SUPERSESSION_REASON_ID:
            raise ValueError("application supersession reason drifted")
        _sha256(
            self.superseded_application_authority_v2_sha,
            "superseded_application_authority_v2_sha",
        )
        _sha256(
            self.replacement_application_authority_v3_sha,
            "replacement_application_authority_v3_sha",
        )
        _sha256(self.supersession_sha, "supersession_sha")


def application_supersession_v3_payload(
    supersession: ApplicationSupersessionV3,
) -> dict[str, object]:
    """Canonical supersession body, excluding only its self hash."""

    _exact_record(
        supersession,
        ApplicationSupersessionV3,
        "application supersession v3",
    )
    supersession.__post_init__()
    return {
        "supersession_schema_version": supersession.supersession_schema_version,
        "control_case_id": supersession.control_case_id,
        "superseded_application_instance_id": (
            supersession.superseded_application_instance_id
        ),
        "superseded_application_authority_v2_sha": (
            supersession.superseded_application_authority_v2_sha
        ),
        "replacement_application_instance_id": (
            supersession.replacement_application_instance_id
        ),
        "replacement_application_authority_v3_sha": (
            supersession.replacement_application_authority_v3_sha
        ),
        "reason_id": supersession.reason_id,
    }


@dataclass(frozen=True)
class ParentFreezeCandidateV3Manifest:
    candidate_schema_version: str
    authority_state: Literal["PROVISIONAL_NOT_ISSUED"]
    program_id: Literal["projective-rule-space-v3m0-v3"]
    preparation_commit_sha: str
    historical_parent_v1: ParentFreezeManifest
    reviewed_candidate_v1: ParentFreezeCandidateManifest
    reviewed_candidate_v2: ParentFreezeCandidateV2Manifest
    inherited_current_application_authorities_v2: tuple[
        CurrentApplicationAuthorityV2, ...
    ]
    superseded_application_authorities_v2: tuple[
        CurrentApplicationAuthorityV2, ...
    ]
    refrozen_current_application_authorities_v3: tuple[
        CurrentApplicationAuthorityV3, ...
    ]
    application_supersessions: tuple[ApplicationSupersessionV3, ...]
    block_success_scenario_ids: tuple[str, ...]
    source_closure: SourceClosureV1
    source_closure_sha: str
    candidate_sha: str

    def __post_init__(self) -> None:
        if self.candidate_schema_version != (
            PARENT_FREEZE_CANDIDATE_V3_SCHEMA_VERSION
        ):
            raise ValueError("Parent-v3 candidate schema drifted")
        if self.authority_state != PARENT_V3_CANDIDATE_AUTHORITY_STATE:
            raise ValueError("Parent-v3 candidate cannot claim authority")
        if self.program_id != PARENT_V3_PROGRAM_ID:
            raise ValueError("Parent-v3 candidate program ID drifted")
        _git_sha1(self.preparation_commit_sha, "preparation_commit_sha")
        _exact_record(
            self.historical_parent_v1,
            ParentFreezeManifest,
            "historical_parent_v1",
        )
        _exact_record(
            self.reviewed_candidate_v1,
            ParentFreezeCandidateManifest,
            "reviewed_candidate_v1",
        )
        _exact_record(
            self.reviewed_candidate_v2,
            ParentFreezeCandidateV2Manifest,
            "reviewed_candidate_v2",
        )
        for value, record_type, field in (
            (
                self.inherited_current_application_authorities_v2,
                CurrentApplicationAuthorityV2,
                "inherited_current_application_authorities_v2",
            ),
            (
                self.superseded_application_authorities_v2,
                CurrentApplicationAuthorityV2,
                "superseded_application_authorities_v2",
            ),
            (
                self.refrozen_current_application_authorities_v3,
                CurrentApplicationAuthorityV3,
                "refrozen_current_application_authorities_v3",
            ),
            (
                self.application_supersessions,
                ApplicationSupersessionV3,
                "application_supersessions",
            ),
        ):
            if type(value) is not tuple or not value:
                raise TypeError(f"{field} must be a non-empty exact tuple")
            if not all(type(item) is record_type for item in value):
                raise TypeError(f"{field} contains a non-exact record")
        if type(self.block_success_scenario_ids) is not tuple or not (
            self.block_success_scenario_ids
        ):
            raise TypeError("block_success_scenario_ids must be a non-empty tuple")
        if not all(type(item) is str and item for item in self.block_success_scenario_ids):
            raise TypeError("block_success_scenario_ids must contain exact strings")
        if len(self.block_success_scenario_ids) != len(
            set(self.block_success_scenario_ids)
        ):
            raise ValueError("block_success_scenario_ids contains duplicates")
        _validated_source_closure(self.source_closure)
        _sha256(self.source_closure_sha, "source_closure_sha")
        _sha256(self.candidate_sha, "candidate_sha")


def parent_v3_source_closure_v1_payload(
    preparation_commit_sha: str,
    source_closure: SourceClosureV1,
) -> dict[str, object]:
    """Canonical owner for the P-epoch path/mode/blob closure root."""

    commit_sha = _git_sha1(preparation_commit_sha, "preparation_commit_sha")
    entries = _validated_source_closure(source_closure)
    return {
        "source_closure_schema_version": (
            PARENT_V3_SOURCE_CLOSURE_V1_SCHEMA_VERSION
        ),
        "preparation_commit_sha": commit_sha,
        "entries": [
            {
                "relative_path": path,
                "git_mode": mode,
                "raw_sha256": raw_sha,
            }
            for path, mode, raw_sha in entries
        ],
    }


def reviewed_path_closure_v1_payload(
    reviewed_path_closure: ReviewedPathClosureV1,
) -> dict[str, object]:
    """Canonical owner for the exact path/P-blob-SHA pair closure."""

    entries = _validated_reviewed_path_closure(reviewed_path_closure)
    return {
        "reviewed_path_closure_schema_version": (
            REVIEWED_PATH_CLOSURE_V1_SCHEMA_VERSION
        ),
        "entries": [
            {"relative_path": path, "raw_sha256": raw_sha}
            for path, raw_sha in entries
        ],
    }


def current_application_registry_v3_payload(
    candidate: ParentFreezeCandidateV3Manifest,
) -> dict[str, object]:
    """Canonical owner for full tagged current V2/V3 application entries."""

    _exact_record(candidate, ParentFreezeCandidateV3Manifest, "Parent-v3 candidate")
    candidate.__post_init__()
    inherited_control_ids = tuple(
        item.control_case_id
        for item in candidate.inherited_current_application_authorities_v2
    )
    refrozen_control_ids = tuple(
        item.control_case_id
        for item in candidate.refrozen_current_application_authorities_v3
    )
    if len(inherited_control_ids) != len(set(inherited_control_ids)):
        raise ValueError("inherited current registry contains duplicate control IDs")
    if len(refrozen_control_ids) != len(set(refrozen_control_ids)):
        raise ValueError("refrozen current registry contains duplicate control IDs")
    if set(inherited_control_ids) & set(refrozen_control_ids):
        raise ValueError("current registry duplicates a control ID across tags")
    inherited = {
        item.control_case_id: item
        for item in candidate.inherited_current_application_authorities_v2
    }
    refrozen = {
        item.control_case_id: item
        for item in candidate.refrozen_current_application_authorities_v3
    }
    entries: list[dict[str, object]] = []
    for ordinal, application in enumerate(
        candidate.reviewed_candidate_v1.application_candidates
    ):
        control_case_id = application.control_case_id
        if control_case_id in inherited and control_case_id not in refrozen:
            authority = inherited[control_case_id]
            entries.append(
                {
                    "parent_v1_ordinal": ordinal,
                    "authority_tag": "INHERITED_CURRENT_V2",
                    "application_authority": {
                        **current_application_authority_v2_payload(authority),
                        "application_authority_sha": (
                            authority.application_authority_sha
                        ),
                    },
                }
            )
        elif control_case_id in refrozen and control_case_id not in inherited:
            authority_v3 = refrozen[control_case_id]
            entries.append(
                {
                    "parent_v1_ordinal": ordinal,
                    "authority_tag": "REFROZEN_CURRENT_V3",
                    "application_authority": {
                        **current_application_authority_v3_payload(authority_v3),
                        "application_authority_sha": (
                            authority_v3.application_authority_sha
                        ),
                    },
                }
            )
        else:
            raise ValueError("current registry is missing or duplicates an application")
    if len(entries) != len(inherited) + len(refrozen):
        raise ValueError("current registry contains applications outside Parent-v1")
    return {
        "current_application_registry_schema_version": (
            CURRENT_APPLICATION_REGISTRY_V3_SCHEMA_VERSION
        ),
        "entries": entries,
    }


def parent_freeze_candidate_v3_manifest_payload(
    candidate: ParentFreezeCandidateV3Manifest,
) -> dict[str, object]:
    """Canonical candidate body, excluding only its self hash."""

    _exact_record(candidate, ParentFreezeCandidateV3Manifest, "Parent-v3 candidate")
    candidate.__post_init__()
    return {
        "candidate_schema_version": candidate.candidate_schema_version,
        "authority_state": candidate.authority_state,
        "program_id": candidate.program_id,
        "preparation_commit_sha": candidate.preparation_commit_sha,
        "historical_parent_v1": {
            **parent_freeze_manifest_payload(candidate.historical_parent_v1),
            "parent_freeze_sha": candidate.historical_parent_v1.parent_freeze_sha,
        },
        "reviewed_candidate_v1": {
            **parent_freeze_candidate_manifest_payload(
                candidate.reviewed_candidate_v1
            ),
            "candidate_sha": candidate.reviewed_candidate_v1.candidate_sha,
        },
        "reviewed_candidate_v2": {
            **parent_candidate_v2_manifest_payload(candidate.reviewed_candidate_v2),
            "candidate_sha": candidate.reviewed_candidate_v2.candidate_sha,
        },
        "inherited_current_application_authorities_v2": [
            {
                **current_application_authority_v2_payload(item),
                "application_authority_sha": item.application_authority_sha,
            }
            for item in candidate.inherited_current_application_authorities_v2
        ],
        "superseded_application_authorities_v2": [
            {
                **current_application_authority_v2_payload(item),
                "application_authority_sha": item.application_authority_sha,
            }
            for item in candidate.superseded_application_authorities_v2
        ],
        "refrozen_current_application_authorities_v3": [
            {
                **current_application_authority_v3_payload(item),
                "application_authority_sha": item.application_authority_sha,
            }
            for item in candidate.refrozen_current_application_authorities_v3
        ],
        "application_supersessions": [
            {
                **application_supersession_v3_payload(item),
                "supersession_sha": item.supersession_sha,
            }
            for item in candidate.application_supersessions
        ],
        "block_success_scenario_ids": list(candidate.block_success_scenario_ids),
        "source_closure": [list(item) for item in candidate.source_closure],
        "source_closure_sha": candidate.source_closure_sha,
    }


def _replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit(
    preparation_commit_sha: str,
) -> ParentFreezeCandidateV3Manifest:
    """Freshly construct the authority-neutral core candidate from one P commit."""

    commit_sha, _tree_sha = _require_preparation_commit_sha(
        preparation_commit_sha
    )
    historical_parent_v1 = issue_v3m0_parent_freeze().manifest
    reviewed_candidate_v1 = verify_parent_freeze_candidate(
        build_v3m0_parent_freeze_candidate()
    )
    reviewed_candidate_v2 = verify_parent_freeze_candidate_v2(
        build_v3m0_parent_freeze_candidate_v2()
    )
    raw_v2 = verify_reviewed_current_application_authorities_v2_raw(
        build_reviewed_current_application_authorities_v2_raw()
    )
    raw_control_ids = tuple(item.control_case_id for item in raw_v2)
    if raw_control_ids != APPLICATION_CONTROL_CASE_IDS:
        raise ValueError("Parent-v2 raw applications drifted from Parent-v1 ordinals")
    candidate_v1_control_ids = tuple(
        item.control_case_id
        for item in reviewed_candidate_v1.application_candidates
    )
    if candidate_v1_control_ids != APPLICATION_CONTROL_CASE_IDS:
        raise ValueError("reviewed candidate-v1 application ordinals drifted")

    c19_matches = tuple(
        (index, item)
        for index, item in enumerate(raw_v2)
        if item.control_case_id == C19_CONTROL_CASE_ID
    )
    if len(c19_matches) != 1:
        raise ValueError("Parent-v2 raw applications do not contain exactly one C19")
    c19_ordinal, superseded_c19 = c19_matches[0]
    expected_c19_ordinal = APPLICATION_CONTROL_CASE_IDS.index(C19_CONTROL_CASE_ID)
    if c19_ordinal != expected_c19_ordinal:
        raise ValueError("historical C19 ordinal drifted")
    if superseded_c19.application_instance_id != (
        C19_HISTORICAL_APPLICATION_INSTANCE_ID
    ):
        raise ValueError("historical C19 application instance drifted")

    replacement_c19 = (
        _replay_c19_current_application_authority_v3_at_preparation_commit(
            commit_sha
        )
    )
    if (
        replacement_c19.control_case_id != C19_CONTROL_CASE_ID
        or replacement_c19.application_instance_id
        != C19_REPLACEMENT_APPLICATION_INSTANCE_ID
        or replacement_c19.authority_state != PARENT_V3_CANDIDATE_AUTHORITY_STATE
    ):
        raise ValueError("replacement C19 P-epoch body drifted")
    if (
        len(superseded_c19.scenario_authorities) != 1
        or len(replacement_c19.scenario_authorities) != 1
    ):
        raise ValueError("C19 supersession must replace one exact success scenario")

    inherited_v2 = raw_v2[:c19_ordinal] + raw_v2[c19_ordinal + 1 :]
    supersession_provisional = ApplicationSupersessionV3(
        supersession_schema_version=(
            APPLICATION_SUPERSESSION_V3_SCHEMA_VERSION
        ),
        control_case_id=C19_CONTROL_CASE_ID,
        superseded_application_instance_id=(
            superseded_c19.application_instance_id
        ),
        superseded_application_authority_v2_sha=(
            superseded_c19.application_authority_sha
        ),
        replacement_application_instance_id=(
            replacement_c19.application_instance_id
        ),
        replacement_application_authority_v3_sha=(
            replacement_c19.application_authority_sha
        ),
        reason_id=C19_SUPERSESSION_REASON_ID,
        supersession_sha="0" * 64,
    )
    supersession = replace(
        supersession_provisional,
        supersession_sha=canonical_sha(
            application_supersession_v3_payload(supersession_provisional)
        ),
    )
    block_success_scenario_ids = tuple(
        scenario.scenario_id
        for application in raw_v2
        for scenario in (
            replacement_c19.scenario_authorities
            if application.control_case_id == C19_CONTROL_CASE_ID
            else application.scenario_authorities
        )
    )
    if (
        len(block_success_scenario_ids) != 23
        or len(block_success_scenario_ids)
        != len(set(block_success_scenario_ids))
    ):
        raise ValueError("Parent-v3 current registry is not the exact 23 success lanes")
    historical_c19_scenario_id = superseded_c19.scenario_authorities[0].scenario_id
    replacement_c19_scenario_id = replacement_c19.scenario_authorities[0].scenario_id
    if (
        historical_c19_scenario_id in block_success_scenario_ids
        or replacement_c19_scenario_id not in block_success_scenario_ids
        or any("c20" in item.lower() for item in block_success_scenario_ids)
    ):
        raise ValueError("C19/C20 success-scenario registry drifted")

    source_closure = _select_parent_v3_source_closure_at_preparation_commit(
        commit_sha
    )
    source_closure_sha = canonical_sha(
        parent_v3_source_closure_v1_payload(commit_sha, source_closure)
    )
    provisional = ParentFreezeCandidateV3Manifest(
        candidate_schema_version=PARENT_FREEZE_CANDIDATE_V3_SCHEMA_VERSION,
        authority_state=PARENT_V3_CANDIDATE_AUTHORITY_STATE,
        program_id=PARENT_V3_PROGRAM_ID,
        preparation_commit_sha=commit_sha,
        historical_parent_v1=historical_parent_v1,
        reviewed_candidate_v1=reviewed_candidate_v1,
        reviewed_candidate_v2=reviewed_candidate_v2,
        inherited_current_application_authorities_v2=inherited_v2,
        superseded_application_authorities_v2=(superseded_c19,),
        refrozen_current_application_authorities_v3=(replacement_c19,),
        application_supersessions=(supersession,),
        block_success_scenario_ids=block_success_scenario_ids,
        source_closure=source_closure,
        source_closure_sha=source_closure_sha,
        candidate_sha="0" * 64,
    )
    candidate = replace(
        provisional,
        candidate_sha=canonical_sha(
            parent_freeze_candidate_v3_manifest_payload(provisional)
        ),
    )
    # Exercise every canonical owner now; later Parent issuance must reuse them.
    canonical_sha(current_application_registry_v3_payload(candidate))
    canonical_sha(
        reviewed_path_closure_v1_payload(
            _project_source_closure_to_reviewed_path_closure(
                candidate.source_closure
            )
        )
    )
    return candidate


def _verify_parent_candidate_v3_roots_and_registry(
    candidate: ParentFreezeCandidateV3Manifest,
) -> None:
    candidate.__post_init__()
    reviewed_control_ids = tuple(
        item.control_case_id
        for item in candidate.reviewed_candidate_v1.application_candidates
    )
    if reviewed_control_ids != APPLICATION_CONTROL_CASE_IDS:
        raise ValueError("reviewed candidate-v1 application ordinals drifted")
    expected_inherited_ids = tuple(
        item for item in APPLICATION_CONTROL_CASE_IDS if item != C19_CONTROL_CASE_ID
    )
    inherited_ids = tuple(
        item.control_case_id
        for item in candidate.inherited_current_application_authorities_v2
    )
    if inherited_ids != expected_inherited_ids:
        raise ValueError("inherited current V2 application ordinals drifted")
    if (
        len(candidate.superseded_application_authorities_v2) != 1
        or candidate.superseded_application_authorities_v2[0].control_case_id
        != C19_CONTROL_CASE_ID
        or candidate.superseded_application_authorities_v2[0].application_instance_id
        != C19_HISTORICAL_APPLICATION_INSTANCE_ID
    ):
        raise ValueError("historical C19 superseded partition drifted")
    if (
        len(candidate.refrozen_current_application_authorities_v3) != 1
        or candidate.refrozen_current_application_authorities_v3[0].control_case_id
        != C19_CONTROL_CASE_ID
        or candidate.refrozen_current_application_authorities_v3[0].application_instance_id
        != C19_REPLACEMENT_APPLICATION_INSTANCE_ID
        or candidate.refrozen_current_application_authorities_v3[0].authority_state
        != PARENT_V3_CANDIDATE_AUTHORITY_STATE
    ):
        raise ValueError("replacement C19 current partition drifted")
    if len(candidate.application_supersessions) != 1:
        raise ValueError("Parent-v3 candidate must contain one supersession")
    historical_c19 = candidate.superseded_application_authorities_v2[0]
    replacement_c19 = candidate.refrozen_current_application_authorities_v3[0]
    supersession = candidate.application_supersessions[0]
    supersession.__post_init__()
    if (
        supersession.control_case_id != C19_CONTROL_CASE_ID
        or supersession.superseded_application_instance_id
        != historical_c19.application_instance_id
        or supersession.superseded_application_authority_v2_sha
        != historical_c19.application_authority_sha
        or supersession.replacement_application_instance_id
        != replacement_c19.application_instance_id
        or supersession.replacement_application_authority_v3_sha
        != replacement_c19.application_authority_sha
        or supersession.supersession_sha
        != canonical_sha(application_supersession_v3_payload(supersession))
    ):
        raise ValueError("C19 application supersession root or lineage drifted")

    inherited_by_control = {
        item.control_case_id: item
        for item in candidate.inherited_current_application_authorities_v2
    }
    expected_success_ids: list[str] = []
    for control_case_id in APPLICATION_CONTROL_CASE_IDS:
        authority = (
            replacement_c19
            if control_case_id == C19_CONTROL_CASE_ID
            else inherited_by_control[control_case_id]
        )
        expected_success_ids.extend(
            item.scenario_id for item in authority.scenario_authorities
        )
    if candidate.block_success_scenario_ids != tuple(expected_success_ids):
        raise ValueError("block-success scenario IDs drifted from current registry")
    if (
        len(expected_success_ids) != 23
        or len(expected_success_ids) != len(set(expected_success_ids))
        or any("c20" in item.lower() for item in expected_success_ids)
    ):
        raise ValueError("current registry is not the exact 23 success lanes")

    expected_source_root = canonical_sha(
        parent_v3_source_closure_v1_payload(
            candidate.preparation_commit_sha,
            candidate.source_closure,
        )
    )
    if candidate.source_closure_sha != expected_source_root:
        raise ValueError("Parent-v3 source closure root drifted")
    if candidate.candidate_sha != canonical_sha(
        parent_freeze_candidate_v3_manifest_payload(candidate)
    ):
        raise ValueError("Parent-v3 candidate root drifted")
    canonical_sha(current_application_registry_v3_payload(candidate))
    canonical_sha(
        reviewed_path_closure_v1_payload(
            _project_source_closure_to_reviewed_path_closure(
                candidate.source_closure
            )
        )
    )


def _fresh_audit_child_main(request: dict[str, object]) -> dict[str, object]:
    """Replay P without receiving any authority-owned transcript object."""

    if type(request) is not dict:
        raise RuntimeError("fresh-audit child request is malformed")
    expected_request_fields = {
        "audit_mode",
        "external_import_roots",
        "nonce",
        "p_data_not_executed",
        "preparation_commit_sha",
        "preparation_tree_sha",
        "source_closure",
        "trusted_git_executable_realpath",
        "trusted_python_executable_realpath",
    }
    if set(request) != expected_request_fields:
        raise RuntimeError("fresh-audit child request fields drifted")
    if request["audit_mode"] != _FRESH_INTERPRETER_AUDIT_MODE:
        raise RuntimeError("fresh-audit child mode drifted")
    nonce = _sha256(request["nonce"], "fresh-audit child nonce")
    preparation_commit_sha = _git_sha1(
        request["preparation_commit_sha"],
        "fresh-audit child preparation commit",
    )
    preparation_tree_sha = _git_sha1(
        request["preparation_tree_sha"],
        "fresh-audit child preparation tree",
    )
    _validate_fresh_audit_process_identity(request)

    observed_commit_sha, observed_tree_sha = _require_preparation_commit_sha(
        preparation_commit_sha
    )
    if (
        observed_commit_sha != preparation_commit_sha
        or observed_tree_sha != preparation_tree_sha
    ):
        raise RuntimeError("fresh-audit child P/tree identity drifted")
    selected_entries = (
        _enumerate_parent_v3_source_entries_at_preparation_commit(
            preparation_commit_sha
        )
    )
    requested_source_closure = request["source_closure"]
    if type(requested_source_closure) is not list:
        raise RuntimeError("fresh-audit child source closure is malformed")

    candidate = _replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit(
        preparation_commit_sha
    )
    _exact_record(candidate, ParentFreezeCandidateV3Manifest, "fresh Parent-v3 candidate")
    _require_exact_wire_tree(candidate, "fresh Parent-v3 candidate")
    _verify_parent_candidate_v3_roots_and_registry(candidate)
    if candidate.preparation_commit_sha != preparation_commit_sha:
        raise RuntimeError("fresh-audit child candidate P drifted")
    expected_requested_source_closure = [
        {"path": path, "mode": mode, "sha256": raw_sha}
        for path, mode, raw_sha in candidate.source_closure
    ]
    if requested_source_closure != expected_requested_source_closure:
        raise RuntimeError("fresh-audit child requested source closure drifted")
    if tuple(item[0] for item in selected_entries) != tuple(
        path for path, _mode, _sha in candidate.source_closure
    ):
        raise RuntimeError("fresh-audit child selected source paths drifted")

    return {
        "audit_schema_version": _FRESH_INTERPRETER_AUDIT_SCHEMA_VERSION,
        "audit_mode": _FRESH_INTERPRETER_AUDIT_MODE,
        "nonce": nonce,
        "preparation_commit_sha": preparation_commit_sha,
        "preparation_tree_sha": preparation_tree_sha,
        "python_executable_realpath": _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
        "candidate_sha": candidate.candidate_sha,
        "source_closure_sha": candidate.source_closure_sha,
    }


def _canonical_json_line(payload: dict[str, object]) -> bytes:
    if type(payload) is not dict:
        raise TypeError("fresh-audit payload must be an exact dict")
    try:
        return (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("fresh-audit payload is not canonical JSON") from exc


def _encode_fresh_audit_frame(
    *,
    nonce: str,
    sequence: int,
    kind: str,
    payload: object,
    previous_frame_sha: str,
) -> tuple[bytes, str]:
    _sha256(nonce, "fresh-audit frame nonce")
    _sha256(previous_frame_sha, "fresh-audit previous frame root")
    if type(sequence) is not int or sequence < 0:
        raise ValueError("fresh-audit frame sequence is invalid")
    _text(kind, "fresh-audit frame kind")
    unsigned = {
        "frame_schema_version": _FRESH_AUDIT_FRAME_SCHEMA_VERSION,
        "kind": kind,
        "nonce": nonce,
        "payload": payload,
        "previous_frame_sha": previous_frame_sha,
        "sequence": sequence,
    }
    frame_sha = canonical_sha(unsigned)
    return _canonical_json_line({**unsigned, "frame_sha": frame_sha}), frame_sha


def _decode_fresh_audit_frames(
    expected_nonce: str,
    completed: subprocess.CompletedProcess[bytes],
) -> list[dict[str, object]]:
    _sha256(expected_nonce, "fresh-audit nonce")
    if type(completed) is not subprocess.CompletedProcess:
        raise TypeError("fresh-audit process result has the wrong type")
    if completed.returncode != 0 or completed.stderr != b"":
        raise ValueError("fresh-audit framed child did not exit cleanly")
    if (
        type(completed.stdout) is not bytes
        or not completed.stdout
        or len(completed.stdout) > _FRESH_AUDIT_MAX_STDOUT_BYTES
        or not completed.stdout.endswith(b"\n")
    ):
        raise ValueError("fresh-audit frame transcript wire is invalid")
    raw_lines = completed.stdout.splitlines(keepends=True)
    if len(raw_lines) < 2:
        raise ValueError("fresh-audit frame transcript is incomplete")
    previous_sha = "0" * 64
    frames: list[dict[str, object]] = []
    for sequence, raw_line in enumerate(raw_lines):
        try:
            frame = json.loads(
                raw_line[:-1].decode("utf-8"),
                object_pairs_hook=_reject_duplicate_json_pairs,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError("fresh-audit frame is not strict JSON") from exc
        if type(frame) is not dict or set(frame) != {
            "frame_schema_version",
            "kind",
            "nonce",
            "payload",
            "previous_frame_sha",
            "sequence",
            "frame_sha",
        }:
            raise ValueError("fresh-audit frame fields drifted")
        if _canonical_json_line(frame) != raw_line:
            raise ValueError("fresh-audit frame is not canonical")
        unsigned = {key: value for key, value in frame.items() if key != "frame_sha"}
        frame_sha = _sha256(frame["frame_sha"], "fresh-audit frame root")
        if (
            frame["frame_schema_version"] != _FRESH_AUDIT_FRAME_SCHEMA_VERSION
            or frame["nonce"] != expected_nonce
            or frame["sequence"] != sequence
            or frame["previous_frame_sha"] != previous_sha
            or frame_sha != canonical_sha(unsigned)
        ):
            raise ValueError("fresh-audit frame chain/sequence drifted")
        frames.append(frame)
        previous_sha = frame_sha
    if (
        frames[0]["kind"] != "start"
        or frames[0]["payload"]
        != {"hook_installation_state": _FRESH_INTERPRETER_HOOK_STATE}
        or frames[-1]["kind"] != "final"
        or any(frame["kind"] in ("start", "final") for frame in frames[1:-1])
    ):
        raise ValueError("fresh-audit frame boundary drifted")
    return frames


def _validate_source_execution_record(
    expectation: _FreshInterpreterAuditExpectation,
    value: object,
) -> str:
    if type(value) is not dict or set(value) != {
        "path",
        "st_dev",
        "st_ino",
        "st_mode",
        "st_size",
        "st_mtime_ns",
        "sha256",
    }:
        raise ValueError("fresh-audit source-execution record drifted")
    relative_path = _relative_path(value["path"], "source-execution path")
    for field in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns"):
        if type(value[field]) is not int or value[field] < 0:
            raise ValueError("fresh-audit source-execution metadata drifted")
    observed_sha = _sha256(value["sha256"], "source-execution sha256")
    closure = {
        path: (mode, raw_sha)
        for path, mode, raw_sha in _validated_source_closure(
            expectation.source_closure
        )
    }
    expected = closure.get(relative_path)
    if expected is None:
        raise ValueError("fresh-audit executed source outside P closure")
    expected_mode, expected_sha = expected
    observed_git_mode = "100755" if value["st_mode"] & 0o111 else "100644"
    if observed_git_mode != expected_mode or observed_sha != expected_sha:
        raise ValueError("fresh-audit executed source bytes differ from P")
    live_path = _REPOSITORY_ROOT.joinpath(*PurePosixPath(relative_path).parts)
    try:
        live_metadata = live_path.lstat()
    except OSError as exc:
        raise ValueError("fresh-audit executed source pathname disappeared") from exc
    if (
        stat.S_ISLNK(live_metadata.st_mode)
        or not stat.S_ISREG(live_metadata.st_mode)
        or (
            live_metadata.st_dev,
            live_metadata.st_ino,
            live_metadata.st_mode,
            live_metadata.st_size,
            live_metadata.st_mtime_ns,
        )
        != (
            value["st_dev"],
            value["st_ino"],
            value["st_mode"],
            value["st_size"],
            value["st_mtime_ns"],
        )
    ):
        raise ValueError("fresh-audit executed source inode/path binding drifted")
    return relative_path


def _expected_inert_p_data_states(
    expectation: _FreshInterpreterAuditExpectation,
) -> tuple[dict[str, str], ...]:
    closure = {
        path: (mode, raw_sha)
        for path, mode, raw_sha in _validated_source_closure(
            expectation.source_closure
        )
    }
    expected = closure.get(_PARENT_V3_SIGNING_LITERALS_PATH)
    if expected is None:
        return ()
    mode, raw_sha = expected
    return (
        {
            "execution_state": _FRESH_AUDIT_P_DATA_STATE,
            "mode": mode,
            "path": _PARENT_V3_SIGNING_LITERALS_PATH,
            "sha256": raw_sha,
        },
    )


def _validate_inert_p_data_state(
    expectation: _FreshInterpreterAuditExpectation,
    value: object,
) -> str:
    if type(value) is not dict or set(value) != {
        "execution_state",
        "mode",
        "path",
        "sha256",
    }:
        raise ValueError("fresh-audit inert P data state drifted")
    path = _relative_path(value["path"], "inert P data path")
    _sha256(value["sha256"], "inert P data sha256")
    expected = _expected_inert_p_data_states(expectation)
    if len(expected) != 1 or value != expected[0]:
        raise ValueError("fresh-audit inert P data state differs from P closure")
    return path


def _validate_dynamic_library_execution_record(value: object) -> str:
    if type(value) is not dict or set(value) != {
        "path",
        "st_dev",
        "st_ino",
        "st_mode",
        "st_size",
        "st_mtime_ns",
        "sha256",
    }:
        raise ValueError("fresh-audit dynamic-library identity drifted")
    path = _text(value["path"], "dynamic-library path")
    if not Path(path).is_absolute():
        raise ValueError("fresh-audit dynamic-library path is not absolute")
    for field in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns"):
        if type(value[field]) is not int or value[field] < 0:
            raise ValueError("fresh-audit dynamic-library metadata drifted")
    _sha256(value["sha256"], "dynamic-library sha256")
    live_path = Path(path)
    try:
        lexical = live_path.lstat()
        opened, observed_sha = _stable_regular_file_sha256(live_path, lexical)
    except (OSError, ValueError) as exc:
        raise ValueError("fresh-audit dynamic-library identity is unstable") from exc
    if (
        (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
            observed_sha,
        )
        != (
            value["st_dev"],
            value["st_ino"],
            value["st_mode"],
            value["st_size"],
            value["st_mtime_ns"],
            value["sha256"],
        )
    ):
        raise ValueError("fresh-audit dynamic-library loader identity drifted")
    return path


def _assemble_fresh_audit_transcript(
    expectation: _FreshInterpreterAuditExpectation,
    expected_nonce: str,
    completed: subprocess.CompletedProcess[bytes],
) -> dict[str, object]:
    """Validate the child hash chain and aggregate it only in the parent."""

    _exact_record(
        expectation,
        _FreshInterpreterAuditExpectation,
        "fresh-audit expectation",
    )
    expectation.__post_init__()
    frames = _decode_fresh_audit_frames(expected_nonce, completed)
    allowed_kinds = {
        "start",
        "module_path",
        "file_read_path",
        "git_command",
        "p_data_state",
        "dynamic_library",
        "repository_directory_scan",
        "source_execution",
        "final",
    }
    module_paths: set[str] = set()
    file_paths: set[str] = set()
    git_commands: list[object] = []
    inert_p_data_states: list[object] = []
    dynamic_library_records: dict[str, object] = {}
    directory_scans: list[object] = []
    executed_paths: set[str] = set()
    repository_execution_started = False
    final_core: object = None
    for frame in frames:
        kind = frame["kind"]
        if type(kind) is not str or kind not in allowed_kinds:
            raise ValueError("fresh-audit frame kind drifted")
        payload = frame["payload"]
        if kind == "module_path":
            module_paths.add(_relative_path(payload, "observed module path"))
        elif kind == "file_read_path":
            file_paths.add(_relative_path(payload, "observed file path"))
        elif kind == "git_command":
            git_commands.append(payload)
        elif kind == "p_data_state":
            if repository_execution_started:
                raise ValueError("fresh-audit inert P data followed execution")
            _validate_inert_p_data_state(expectation, payload)
            inert_p_data_states.append(payload)
        elif kind == "dynamic_library":
            if repository_execution_started:
                raise ValueError("fresh-audit observed post-freeze dynamic loading")
            dynamic_path = _validate_dynamic_library_execution_record(payload)
            previous_record = dynamic_library_records.get(dynamic_path)
            if previous_record is not None and previous_record != payload:
                raise ValueError("fresh-audit dynamic-library identity forked")
            dynamic_library_records[dynamic_path] = payload
        elif kind == "repository_directory_scan":
            directory_scans.append(payload)
        elif kind == "source_execution":
            repository_execution_started = True
            executed_path = _validate_source_execution_record(
                expectation,
                payload,
            )
            if executed_path in executed_paths:
                raise ValueError("fresh-audit source executed more than once")
            executed_paths.add(executed_path)
            module_paths.add(executed_path)
        elif kind == "final":
            final_core = payload

    if type(final_core) is not dict or set(final_core) != {
        "audit_schema_version",
        "audit_mode",
        "nonce",
        "preparation_commit_sha",
        "preparation_tree_sha",
        "python_executable_realpath",
        "candidate_sha",
        "source_closure_sha",
    }:
        raise ValueError("fresh-audit final core drifted")
    if not _FRESH_AUDIT_REQUIRED_REPOSITORY_MODULE_PATHS.issubset(executed_paths):
        raise ValueError("fresh-audit lacks stable execution records for required modules")
    expected_inert_p_data_states = _expected_inert_p_data_states(expectation)
    if tuple(inert_p_data_states) != expected_inert_p_data_states:
        raise ValueError("fresh-audit inert P data state count/order drifted")
    inert_paths = {record["path"] for record in expected_inert_p_data_states}
    if inert_paths.intersection(executed_paths):
        raise ValueError("fresh-audit inert P data was executed")
    unsigned_observation = {
        **final_core,
        "hook_installation_state": _FRESH_INTERPRETER_HOOK_STATE,
        "observed_module_paths": sorted(
            module_paths,
            key=lambda item: item.encode("utf-8"),
        ),
        "observed_file_read_paths": sorted(
            file_paths,
            key=lambda item: item.encode("utf-8"),
        ),
        "observed_git_commands": git_commands,
        "observed_p_data_states": inert_p_data_states,
        "observed_dynamic_library_paths": sorted(
            dynamic_library_records,
            key=lambda item: item.encode("utf-8"),
        ),
        "observed_repository_directory_scans": directory_scans,
    }
    observation = {
        **unsigned_observation,
        "observation_sha": canonical_sha(unsigned_observation),
    }
    return _validate_fresh_interpreter_audit_output(
        expectation,
        expected_nonce,
        subprocess.CompletedProcess(
            completed.args,
            0,
            _canonical_json_line(observation),
            b"",
        ),
    )


def _reject_duplicate_json_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise ValueError("fresh-audit JSON contains a non-string key")
        if key in result:
            raise ValueError("fresh-audit JSON contains duplicate keys")
        result[key] = value
    return result


@contextmanager
def _pinned_trusted_python_executable(
    *,
    temporary_parent: Path | None = None,
):
    """Yield a private hardlink to the frozen Python inode, never a fallback."""

    if temporary_parent is not None and (
        not isinstance(temporary_parent, Path) or not temporary_parent.is_dir()
    ):
        raise TypeError("Python hardlink pin parent must be an existing exact Path")
    _verify_trusted_executable_identity(_TRUSTED_PYTHON_EXECUTABLE_IDENTITY)
    try:
        with tempfile.TemporaryDirectory(
            prefix="culab-parent-v3-python-pin-",
            dir=temporary_parent,
        ) as pin_directory:
            os.chmod(pin_directory, 0o700)
            pin_root = Path(pin_directory)
            if _TRUSTED_PYTHON_FRAMEWORK_IDENTITY is None:
                pinned_path = pin_root / "python3-pinned"
                framework_pin = None
            else:
                pinned_path = (
                    pin_root
                    / "Resources"
                    / "Python.app"
                    / "Contents"
                    / "MacOS"
                    / "Python"
                )
                pinned_path.parent.mkdir(parents=True, mode=0o700)
                framework_pin = pin_root / "Python3"
            try:
                os.link(
                    _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
                    pinned_path,
                    follow_symlinks=True,
                )
                if framework_pin is not None:
                    assert _TRUSTED_PYTHON_FRAMEWORK_REALPATH is not None
                    os.link(
                        _TRUSTED_PYTHON_FRAMEWORK_REALPATH,
                        framework_pin,
                        follow_symlinks=True,
                    )
            except OSError as exc:
                raise ValueError("trusted Python hardlink pin failed closed") from exc
            _verify_trusted_executable_identity(
                _TRUSTED_PYTHON_EXECUTABLE_IDENTITY,
                pinned_path,
            )
            if framework_pin is not None:
                assert _TRUSTED_PYTHON_FRAMEWORK_IDENTITY is not None
                _verify_trusted_executable_identity(
                    _TRUSTED_PYTHON_FRAMEWORK_IDENTITY,
                    framework_pin,
                )
            yield os.fspath(pinned_path)
    except OSError as exc:
        raise ValueError("trusted Python hardlink pin failed closed") from exc


def _run_bounded_fresh_interpreter(
    command: tuple[str, ...],
    *,
    cwd: Path,
    input_bytes: bytes,
    timeout_seconds: int | float,
) -> subprocess.CompletedProcess[bytes]:
    if (
        type(command) is not tuple
        or not command
        or not all(type(item) is str and item for item in command)
        or command[0] != _TRUSTED_PYTHON_EXECUTABLE_REALPATH
    ):
        raise TypeError("fresh-interpreter command is not exact trusted Python")
    if not isinstance(cwd, Path) or not cwd.is_dir():
        raise TypeError("fresh-interpreter cwd must be an existing exact Path")
    if type(input_bytes) is not bytes or len(input_bytes) > 65536:
        raise TypeError("fresh-interpreter input must be bounded exact bytes")
    if (
        type(timeout_seconds) not in (int, float)
        or timeout_seconds <= 0
    ):
        raise TypeError("fresh-interpreter timeout must be positive")
    with _pinned_trusted_python_executable() as pinned_python:
        pinned_command = (pinned_python, *command[1:])
        environment = _minimal_process_environment()
        if sysconfig.get_platform().startswith("macosx"):
            environment["__PYVENV_LAUNCHER__"] = (
                _TRUSTED_PYTHON_LAUNCHER_PATH
            )
        completed = _run_bounded_process(
            pinned_command,
            cwd=cwd,
            env=environment,
            input_bytes=input_bytes,
            timeout_seconds=timeout_seconds,
            max_stdout_bytes=_FRESH_AUDIT_MAX_STDOUT_BYTES,
            max_stderr_bytes=_FRESH_AUDIT_MAX_STDERR_BYTES,
            executable_identity=_TRUSTED_PYTHON_EXECUTABLE_IDENTITY,
        )
    return subprocess.CompletedProcess(
        command,
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


def _canonical_observed_paths(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{field} must be an exact JSON array")
    paths = tuple(_relative_path(item, f"{field}[{index}]") for index, item in enumerate(value))
    if paths != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
        raise ValueError(f"{field} is not in UTF-8 path order")
    if len(paths) != len(set(paths)):
        raise ValueError(f"{field} contains duplicate paths")
    return paths


def _validate_observed_dynamic_library_paths(value: object) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError("observed_dynamic_library_paths must be an exact array")
    if not all(type(item) is str and item for item in value):
        raise TypeError("observed_dynamic_library_paths contains a non-string")
    paths = tuple(value)
    if paths != tuple(sorted(set(paths), key=lambda item: item.encode("utf-8"))):
        raise ValueError("observed_dynamic_library_paths is not canonical")
    allowed_roots = tuple(
        Path(root)
        for root in (
            *_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS,
            *_FRESH_AUDIT_SYSTEM_LIBRARY_ROOTS,
        )
    )
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_absolute():
            raise ValueError("observed dynamic library path is not absolute")
        try:
            resolved = path.resolve(strict=True)
            metadata = path.lstat()
        except OSError as exc:
            raise ValueError("observed dynamic library path is missing") from exc
        if resolved != path or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("observed dynamic library path is not canonical regular")
        if not any(path.is_relative_to(root) for root in allowed_roots):
            raise ValueError("observed dynamic library path is outside trusted roots")
    return paths


def _validate_observed_repository_directory_scans(value: object) -> None:
    if value != [".", "rulespace_v3"] or type(value) is not list:
        raise ValueError("observed repository directory scans drifted")
    if any(type(item) is not str for item in value):
        raise TypeError("observed repository directory scans are not exact strings")


def _valid_fresh_audit_git_argv(
    expectation: _FreshInterpreterAuditExpectation,
    argv: tuple[str, ...],
) -> bool:
    if (
        len(argv) < 2
        or argv[0] != expectation.trusted_git_executable_realpath
    ):
        return False
    trusted_git = expectation.trusted_git_executable_realpath
    if argv in (
        (
            trusted_git,
            "cat-file",
            "-t",
            expectation.preparation_commit_sha,
        ),
        (
            trusted_git,
            "cat-file",
            "commit",
            expectation.preparation_commit_sha,
        ),
        (
            trusted_git,
            "ls-tree",
            "-r",
            "-z",
            "--full-tree",
            expectation.preparation_tree_sha,
            "--",
        ),
    ):
        return True
    closure_paths = frozenset(path for path, _mode, _sha in expectation.source_closure)
    if len(argv) == 4 and argv[1:3] == ("cat-file", "blob"):
        commit_sha, separator, path = argv[3].partition(":")
        return bool(
            separator == ":"
            and commit_sha == expectation.preparation_commit_sha
            and path in closure_paths
        )
    return bool(
        len(argv) == 6
        and argv[1:3] == ("ls-tree", "-z")
        and argv[3] == expectation.preparation_tree_sha
        and argv[4] == "--"
        and argv[5] in closure_paths
    )


def _validate_observed_git_commands(
    expectation: _FreshInterpreterAuditExpectation,
    value: object,
) -> None:
    if type(value) is not list or not value:
        raise TypeError("observed_git_commands must be a non-empty exact array")
    for index, record in enumerate(value):
        if type(record) is not dict or set(record) != {
            "argv",
            "cwd_state",
            "executable_realpath",
            "shell",
        }:
            raise TypeError(f"observed_git_commands[{index}] has the wrong fields")
        argv_value = record["argv"]
        if type(argv_value) is not list or not all(
            type(item) is str and item for item in argv_value
        ):
            raise TypeError(f"observed_git_commands[{index}].argv is not exact")
        argv = tuple(argv_value)
        executable_realpath = record["executable_realpath"]
        if (
            type(executable_realpath) is not str
            or executable_realpath
            != expectation.trusted_git_executable_realpath
        ):
            raise ValueError(
                f"observed_git_commands[{index}] executable drifted"
            )
        if not _valid_fresh_audit_git_argv(expectation, argv):
            raise ValueError(f"observed_git_commands[{index}].argv is not allowlisted")
        if record["cwd_state"] != "EXACT_REPOSITORY_ROOT":
            raise ValueError(f"observed_git_commands[{index}] used another worktree")
        if record["shell"] is not False:
            raise ValueError(f"observed_git_commands[{index}] used a shell")


def _stable_regular_file_sha256(
    live_path: Path,
    lexical_metadata: os.stat_result,
) -> tuple[os.stat_result, str]:
    """Hash one inode while detecting ordinary rename/write races.

    This binds the lexical lstat, opened descriptor, bounded-size read, final
    descriptor stat, and final pathname stat.  It does not claim protection
    against a privileged ABA adversary capable of restoring inode/stat state;
    the clean verification-epoch snapshots are the separate outer guard.
    """

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(live_path, flags)
    except OSError as exc:
        raise ValueError("fresh-audit live source changed before open") from exc

    def fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
        return (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )

    try:
        opened_metadata = os.fstat(descriptor)
        if not stat.S_ISREG(opened_metadata.st_mode):
            raise ValueError("fresh-audit opened source is not a regular file")
        if fingerprint(opened_metadata) != fingerprint(lexical_metadata):
            raise ValueError("fresh-audit live source inode changed before open")
        remaining = opened_metadata.st_size
        digest = hashlib.sha256()
        while remaining:
            try:
                chunk = os.read(descriptor, min(remaining, 1 << 20))
            except OSError as exc:
                raise ValueError("fresh-audit live source read failed") from exc
            if not chunk:
                raise ValueError("fresh-audit live source shrank during read")
            digest.update(chunk)
            remaining -= len(chunk)
        try:
            trailing = os.read(descriptor, 1)
        except OSError as exc:
            raise ValueError("fresh-audit live source tail read failed") from exc
        if trailing:
            raise ValueError("fresh-audit live source grew during read")
        final_descriptor_metadata = os.fstat(descriptor)
        if fingerprint(final_descriptor_metadata) != fingerprint(opened_metadata):
            raise ValueError("fresh-audit live source changed during read")
    finally:
        os.close(descriptor)

    try:
        final_lexical_metadata = live_path.lstat()
        final_resolved_path = live_path.resolve(strict=True)
    except OSError as exc:
        raise ValueError("fresh-audit live source changed after read") from exc
    if (
        fingerprint(final_lexical_metadata) != fingerprint(opened_metadata)
        or final_resolved_path != live_path
    ):
        raise ValueError("fresh-audit live source pathname changed during read")
    return opened_metadata, digest.hexdigest()


def _live_repository_python_source_closure() -> list[dict[str, str]]:
    """Build a bounded smoke-only loader map using stable live-file reads."""

    root = _REPOSITORY_ROOT.resolve(strict=True)
    package_root = root / "rulespace_v3"
    entries: list[dict[str, str]] = []
    for path in sorted(
        package_root.rglob("*.py"),
        key=lambda item: item.relative_to(root).as_posix().encode("utf-8"),
    ):
        relative = path.relative_to(root).as_posix()
        lexical = path.lstat()
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError) as exc:
            raise ValueError("fresh-audit smoke source escaped repository") from exc
        if (
            stat.S_ISLNK(lexical.st_mode)
            or not stat.S_ISREG(lexical.st_mode)
            or resolved != root.joinpath(*PurePosixPath(relative).parts)
        ):
            raise ValueError("fresh-audit smoke source is not canonical regular file")
        opened, raw_sha = _stable_regular_file_sha256(path, lexical)
        entries.append(
            {
                "path": relative,
                "mode": "100755" if opened.st_mode & 0o111 else "100644",
                "sha256": raw_sha,
            }
        )
    if not entries or entries[0]["path"] != "rulespace_v3/__init__.py":
        raise ValueError("fresh-audit smoke source closure lacks package root")
    return entries


def _validate_observed_live_paths(
    expectation: _FreshInterpreterAuditExpectation,
    module_paths: tuple[str, ...],
    file_paths: tuple[str, ...],
) -> None:
    closure = {
        path: (mode, raw_sha)
        for path, mode, raw_sha in _validated_source_closure(
            expectation.source_closure
        )
    }
    root = _REPOSITORY_ROOT.resolve()
    for relative_path in tuple(dict.fromkeys((*module_paths, *file_paths))):
        parts = PurePosixPath(relative_path).parts
        if "__pycache__" in parts or relative_path.endswith((".pyc", ".pyo")):
            raise ValueError("fresh audit observed a repository bytecode cache")
        expected = closure.get(relative_path)
        if expected is None:
            raise ValueError("fresh audit observed a path outside source closure")
        live_path = _REPOSITORY_ROOT.joinpath(*parts)
        canonical_live_path = root.joinpath(*parts)
        try:
            metadata = live_path.lstat()
        except OSError as exc:
            raise ValueError("fresh-audit live source is missing") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("fresh-audit live source is not a regular file")
        try:
            resolved_live_path = live_path.resolve(strict=True)
            resolved_live_path.relative_to(root)
        except (OSError, ValueError) as exc:
            raise ValueError("fresh-audit live source escaped this worktree") from exc
        if resolved_live_path != canonical_live_path:
            raise ValueError(
                "fresh-audit live source has a symlinked parent component"
            )
        expected_mode, expected_sha = expected
        opened_metadata, observed_sha = _stable_regular_file_sha256(
            live_path,
            metadata,
        )
        observed_mode = (
            "100755" if opened_metadata.st_mode & 0o111 else "100644"
        )
        if observed_mode != expected_mode:
            raise ValueError("fresh-audit live source mode differs from P")
        if observed_sha != expected_sha:
            raise ValueError("fresh-audit live source bytes differ from P")


def _validate_fresh_interpreter_audit_output(
    expectation: _FreshInterpreterAuditExpectation,
    expected_nonce: str,
    completed: subprocess.CompletedProcess[bytes],
) -> dict[str, object]:
    _exact_record(
        expectation,
        _FreshInterpreterAuditExpectation,
        "fresh-audit expectation",
    )
    expectation.__post_init__()
    _sha256(expected_nonce, "fresh-audit nonce")
    if type(completed) is not subprocess.CompletedProcess:
        raise TypeError("fresh-audit process result has the wrong type")
    if type(completed.returncode) is not int or completed.returncode != 0:
        raise ValueError("fresh-audit child exited nonzero")
    if type(completed.stderr) is not bytes or completed.stderr != b"":
        raise ValueError("fresh-audit child wrote stderr")
    if type(completed.stdout) is not bytes:
        raise TypeError("fresh-audit child stdout must be exact bytes")
    if not completed.stdout or len(completed.stdout) > _FRESH_AUDIT_MAX_STDOUT_BYTES:
        raise ValueError("fresh-audit child stdout has invalid size")
    if completed.stdout.count(b"\n") != 1 or not completed.stdout.endswith(b"\n"):
        raise ValueError("fresh-audit child stdout is not one JSON line")
    try:
        text = completed.stdout[:-1].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("fresh-audit child stdout is not UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("fresh-audit child stdout contains a BOM")
    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_json_pairs)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError("fresh-audit child stdout is not strict JSON") from exc
    if type(payload) is not dict:
        raise TypeError("fresh-audit observation must be an exact object")
    expected_fields = {
        "audit_schema_version",
        "audit_mode",
        "nonce",
        "preparation_commit_sha",
        "preparation_tree_sha",
        "python_executable_realpath",
        "candidate_sha",
        "source_closure_sha",
        "hook_installation_state",
        "observed_module_paths",
        "observed_file_read_paths",
        "observed_git_commands",
        "observed_p_data_states",
        "observed_dynamic_library_paths",
        "observed_repository_directory_scans",
        "observation_sha",
    }
    if set(payload) != expected_fields:
        raise ValueError("fresh-audit observation fields drifted")
    if _canonical_json_line(payload) != completed.stdout:
        raise ValueError("fresh-audit observation JSON is not canonical")
    observation_sha = _sha256(payload["observation_sha"], "observation_sha")
    unsigned = {key: value for key, value in payload.items() if key != "observation_sha"}
    if observation_sha != canonical_sha(unsigned):
        raise ValueError("fresh-audit observation root drifted")
    if payload["audit_schema_version"] != _FRESH_INTERPRETER_AUDIT_SCHEMA_VERSION:
        raise ValueError("fresh-audit schema drifted")
    if payload["audit_mode"] != _FRESH_INTERPRETER_AUDIT_MODE:
        raise ValueError("fresh-audit mode drifted")
    if payload["nonce"] != expected_nonce:
        raise ValueError("fresh-audit nonce drifted")
    if payload["preparation_commit_sha"] != expectation.preparation_commit_sha:
        raise ValueError("fresh-audit preparation commit drifted")
    if payload["preparation_tree_sha"] != expectation.preparation_tree_sha:
        raise ValueError("fresh-audit preparation tree drifted")
    if (
        payload["python_executable_realpath"]
        != expectation.trusted_python_executable_realpath
    ):
        raise ValueError("fresh-audit Python executable identity drifted")
    if payload["candidate_sha"] != expectation.candidate_sha:
        raise ValueError("fresh-audit candidate root drifted")
    if payload["source_closure_sha"] != expectation.source_closure_sha:
        raise ValueError("fresh-audit source root drifted")
    if payload["hook_installation_state"] != _FRESH_INTERPRETER_HOOK_STATE:
        raise ValueError("fresh-audit hook was not installed first")
    module_paths = _canonical_observed_paths(
        payload["observed_module_paths"],
        "observed_module_paths",
    )
    if not module_paths:
        raise ValueError("fresh-audit observed no repository modules")
    if not _FRESH_AUDIT_REQUIRED_REPOSITORY_MODULE_PATHS.issubset(module_paths):
        raise ValueError("fresh-audit omitted a mandatory replay module")
    file_paths = _canonical_observed_paths(
        payload["observed_file_read_paths"],
        "observed_file_read_paths",
    )
    _validate_observed_dynamic_library_paths(
        payload["observed_dynamic_library_paths"]
    )
    _validate_observed_repository_directory_scans(
        payload["observed_repository_directory_scans"]
    )
    _validate_observed_git_commands(
        expectation,
        payload["observed_git_commands"],
    )
    observed_inert_p_data_states = payload["observed_p_data_states"]
    if type(observed_inert_p_data_states) is not list:
        raise TypeError("observed_p_data_states must be an exact list")
    for record in observed_inert_p_data_states:
        _validate_inert_p_data_state(expectation, record)
    if tuple(observed_inert_p_data_states) != _expected_inert_p_data_states(
        expectation
    ):
        raise ValueError("fresh-audit inert P data observation drifted")
    inert_paths = {
        record["path"] for record in _expected_inert_p_data_states(expectation)
    }
    if inert_paths.intersection(module_paths) or inert_paths.intersection(file_paths):
        raise ValueError("fresh-audit inert P data was observed as executable source")
    _validate_observed_live_paths(expectation, module_paths, file_paths)
    return payload


def _run_fresh_interpreter_dependency_import_smoke() -> dict[str, object]:
    dependency_modules = _FRESH_AUDIT_AVAILABLE_DEPENDENCY_MODULES
    if not dependency_modules or dependency_modules[0] != "numpy":
        raise ValueError("fresh-audit dependency smoke requires NumPy")
    nonce = secrets.token_hex(32)
    request = {
        "audit_mode": _FRESH_INTERPRETER_IMPORT_SMOKE_MODE,
        "dependency_modules": list(dependency_modules),
        "external_import_roots": list(_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS),
        "nonce": nonce,
        "p_data_not_executed": [],
        "source_closure": [],
        "trusted_git_executable_realpath": _TRUSTED_GIT_EXECUTABLE_REALPATH,
        "trusted_python_executable_realpath": (
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    }
    request_bytes = _canonical_json_line(request)
    with tempfile.TemporaryDirectory(prefix="culab-parent-v3-smoke-pycache-") as pycache:
        pycache_realpath = os.fspath(Path(pycache).resolve(strict=True))
        command = (
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
            "-I",
            "-S",
            "-B",
            "-X",
            f"pycache_prefix={pycache_realpath}",
            "-c",
            _FRESH_AUDIT_BOOTSTRAP,
        )
        completed = _run_bounded_fresh_interpreter(
            command,
            cwd=_REPOSITORY_ROOT,
            input_bytes=request_bytes,
            timeout_seconds=120,
        )
    if completed.returncode != 0:
        raise ValueError(
            "fresh-audit dependency smoke exited nonzero: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    frames = _decode_fresh_audit_frames(nonce, completed)
    observed = frames[-1]["payload"]
    expected = {
        "audit_mode": _FRESH_INTERPRETER_IMPORT_SMOKE_MODE,
        "dependency_initialization_state": (
            "NUMPY_TESTING_IMPORTED_WITH_LSCPU_EXECUTION_BLOCKED"
        ),
        "hook_installation_state": _FRESH_INTERPRETER_HOOK_STATE,
        "imported_dependency_modules": list(dependency_modules),
        "python_executable_realpath": _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
    }
    if type(observed) is not dict or observed != expected:
        raise ValueError("fresh-audit dependency smoke output drifted")
    return observed


def _run_fresh_interpreter_candidate_import_smoke() -> dict[str, object]:
    nonce = secrets.token_hex(32)
    request = {
        "audit_mode": _FRESH_INTERPRETER_CANDIDATE_IMPORT_SMOKE_MODE,
        "external_import_roots": list(_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS),
        "nonce": nonce,
        "p_data_not_executed": [],
        "source_closure": _live_repository_python_source_closure(),
        "trusted_git_executable_realpath": _TRUSTED_GIT_EXECUTABLE_REALPATH,
        "trusted_python_executable_realpath": (
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    }
    request_bytes = _canonical_json_line(request)
    with tempfile.TemporaryDirectory(prefix="culab-parent-v3-import-pycache-") as pycache:
        pycache_realpath = os.fspath(Path(pycache).resolve(strict=True))
        command = (
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
            "-I",
            "-S",
            "-B",
            "-X",
            f"pycache_prefix={pycache_realpath}",
            "-c",
            _FRESH_AUDIT_BOOTSTRAP,
        )
        completed = _run_bounded_fresh_interpreter(
            command,
            cwd=_REPOSITORY_ROOT,
            input_bytes=request_bytes,
            timeout_seconds=120,
        )
    if completed.returncode != 0:
        raise ValueError(
            "fresh-audit candidate import exited nonzero: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    frames = _decode_fresh_audit_frames(nonce, completed)
    final_core = frames[-1]["payload"]
    if type(final_core) is not dict:
        raise ValueError("fresh-audit candidate import final frame drifted")
    observed = {
        **final_core,
        "observed_git_commands": [
            frame["payload"] for frame in frames if frame["kind"] == "git_command"
        ],
        "observed_repository_directory_scans": [
            frame["payload"]
            for frame in frames
            if frame["kind"] == "repository_directory_scan"
        ],
    }
    expected = {
        "audit_mode": _FRESH_INTERPRETER_CANDIDATE_IMPORT_SMOKE_MODE,
        "hook_installation_state": _FRESH_INTERPRETER_HOOK_STATE,
        "imported_repository_module": "rulespace_v3.parent_candidate_v3",
        "module_external_import_roots": list(
            _FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS
        ),
        "module_trusted_git_executable_realpath": (
            _TRUSTED_GIT_EXECUTABLE_REALPATH
        ),
        "module_trusted_python_executable_realpath": (
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
        "observed_git_commands": [],
        "observed_repository_directory_scans": [".", "rulespace_v3"],
        "python_executable_realpath": _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
    }
    if type(observed) is not dict or observed != expected:
        raise ValueError("fresh-audit candidate import output drifted")
    return observed


def _run_fresh_interpreter_event_boundary_probe(
    probe: str,
) -> subprocess.CompletedProcess[bytes]:
    allowed_probes = frozenset(
        (
            "authority-frame-forgery",
            "chdir",
            "ctypes-allowed-external",
            "ctypes-repository",
            "ctypes-unknown-external",
            "git-metadata-open",
            "non-git-process",
            "repo-listdir",
            "repo-read",
            "repo-scandir",
            "system-entropy",
            "unknown-external-open",
            "unknown-external-module",
        )
    )
    if type(probe) is not str or probe not in allowed_probes:
        raise ValueError("fresh-audit event probe is not allowlisted")
    nonce = secrets.token_hex(32)
    request = {
        "audit_mode": _FRESH_INTERPRETER_EVENT_PROBE_MODE,
        "external_import_roots": list(_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS),
        "nonce": nonce,
        "p_data_not_executed": [],
        "probe": probe,
        "source_closure": [],
        "trusted_git_executable_realpath": _TRUSTED_GIT_EXECUTABLE_REALPATH,
        "trusted_python_executable_realpath": (
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH
        ),
    }
    request_bytes = _canonical_json_line(request)
    with tempfile.TemporaryDirectory(prefix="culab-parent-v3-probe-pycache-") as pycache:
        pycache_realpath = os.fspath(Path(pycache).resolve(strict=True))
        command = (
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
            "-I",
            "-S",
            "-B",
            "-X",
            f"pycache_prefix={pycache_realpath}",
            "-c",
            _FRESH_AUDIT_BOOTSTRAP,
        )
        completed = _run_bounded_fresh_interpreter(
            command,
            cwd=_REPOSITORY_ROOT,
            input_bytes=request_bytes,
            timeout_seconds=120,
        )
    if completed.returncode != 0:
        return subprocess.CompletedProcess(
            completed.args,
            completed.returncode,
            b"",
            completed.stderr,
        )
    frames = _decode_fresh_audit_frames(nonce, completed)
    final_core = frames[-1]["payload"]
    if type(final_core) is not dict:
        raise ValueError("fresh-audit event-probe final frame drifted")
    observed = {
        **final_core,
        "observed_file_read_paths": sorted(
            {
                frame["payload"]
                for frame in frames
                if frame["kind"] == "file_read_path"
            },
            key=lambda item: item.encode("utf-8"),
        ),
        "observed_dynamic_library_paths": sorted(
            {
                frame["payload"]["path"]
                for frame in frames
                if frame["kind"] == "dynamic_library"
            },
            key=lambda item: item.encode("utf-8"),
        ),
    }
    return subprocess.CompletedProcess(
        completed.args,
        0,
        _canonical_json_line(observed),
        b"",
    )


def _run_fresh_interpreter_completeness_audit(
    candidate: ParentFreezeCandidateV3Manifest,
) -> dict[str, object]:
    expectation = _fresh_audit_expectation_from_candidate(candidate)
    nonce = secrets.token_hex(32)
    request = {
        "audit_mode": _FRESH_INTERPRETER_AUDIT_MODE,
        "preparation_commit_sha": expectation.preparation_commit_sha,
        "preparation_tree_sha": expectation.preparation_tree_sha,
        "nonce": nonce,
        "trusted_git_executable_realpath": (
            expectation.trusted_git_executable_realpath
        ),
        "trusted_python_executable_realpath": (
            expectation.trusted_python_executable_realpath
        ),
        "external_import_roots": list(_FRESH_AUDIT_EXTERNAL_IMPORT_ROOTS),
        "p_data_not_executed": _build_fresh_audit_p_data_not_executed(
            expectation
        ),
        "source_closure": [
            {"path": path, "mode": mode, "sha256": raw_sha}
            for path, mode, raw_sha in expectation.source_closure
        ],
    }
    request_bytes = _canonical_json_line(request)
    with tempfile.TemporaryDirectory(prefix="culab-parent-v3-pycache-") as pycache:
        pycache_realpath = os.fspath(Path(pycache).resolve(strict=True))
        command = (
            _TRUSTED_PYTHON_EXECUTABLE_REALPATH,
            "-I",
            "-S",
            "-B",
            "-X",
            f"pycache_prefix={pycache_realpath}",
            "-c",
            _FRESH_AUDIT_BOOTSTRAP,
        )
        completed = _run_bounded_fresh_interpreter(
            command,
            cwd=_REPOSITORY_ROOT,
            input_bytes=request_bytes,
            timeout_seconds=_FRESH_AUDIT_TIMEOUT_SECONDS,
        )
    return _assemble_fresh_audit_transcript(
        expectation,
        nonce,
        completed,
    )


def _git_repository_command(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    environment = _trusted_git_environment()
    environment["GIT_WORK_TREE"] = os.fspath(_REPOSITORY_ROOT.resolve(strict=True))
    return _run_bounded_process(
        (_TRUSTED_GIT_EXECUTABLE_REALPATH, *arguments),
        cwd=_REPOSITORY_ROOT,
        env=environment,
        input_bytes=b"",
        timeout_seconds=_TRUSTED_GIT_TIMEOUT_SECONDS,
        max_stdout_bytes=_TRUSTED_GIT_MAX_STDOUT_BYTES,
        max_stderr_bytes=_TRUSTED_GIT_MAX_STDERR_BYTES,
        executable_identity=_TRUSTED_GIT_EXECUTABLE_IDENTITY,
    )


def _read_preparation_head_regular_blob(
    preparation_commit_sha: str,
    relative_path: str,
    *,
    required: bool,
) -> bytes | None:
    """Read one regular blob from P without consulting live worktree bytes."""

    commit_sha = _git_sha1(
        preparation_commit_sha,
        "preparation authority commit",
    )
    canonical_path = _relative_path(relative_path, "preparation authority path")
    entry = _git_repository_command(
        "ls-tree",
        "-z",
        commit_sha,
        "--",
        canonical_path,
    )
    if entry.returncode != 0 or entry.stderr != b"":
        raise ValueError("preparation authority-tree probe failed")
    if entry.stdout == b"":
        if required:
            raise ValueError("mandatory preparation authority blob is missing")
        return None
    records = entry.stdout.split(b"\x00")
    if len(records) != 2 or records[1] != b"" or not records[0]:
        raise ValueError("preparation authority path is not one exact tree entry")
    metadata, separator, observed_path = records[0].partition(b"\t")
    if separator != b"\t" or observed_path != canonical_path.encode("utf-8"):
        raise ValueError("preparation authority tree path drifted")
    fields = metadata.split(b" ")
    if len(fields) != 3:
        raise ValueError("preparation authority tree metadata is malformed")
    raw_mode, object_type, raw_object_id = fields
    try:
        mode = raw_mode.decode("ascii")
        object_id = raw_object_id.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("preparation authority metadata is not ASCII") from exc
    if mode not in _REGULAR_GIT_MODES or object_type != b"blob":
        raise ValueError("preparation authority path is not a regular Git blob")
    if _LOWER_GIT_SHA1.fullmatch(object_id) is None:
        raise ValueError("preparation authority blob OID is malformed")
    blob = _git_repository_command("cat-file", "blob", object_id)
    if blob.returncode != 0 or blob.stderr != b"":
        raise ValueError("preparation authority blob cannot be read")
    return blob.stdout


def _validate_parent_signing_placeholder_blob(raw: bytes) -> None:
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Parent-v3 signing literals are not UTF-8") from exc
    if source.startswith("\ufeff"):
        raise ValueError("Parent-v3 signing literals contain a BOM")
    try:
        module = ast.parse(
            source,
            filename=_PARENT_V3_SIGNING_LITERALS_PATH,
            mode="exec",
        )
    except (SyntaxError, ValueError) as exc:
        raise ValueError("Parent-v3 signing literals are not valid Python") from exc

    top_level = tuple(
        statement
        for statement in module.body
        if isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and statement.target.id.startswith("PARENT_V3_")
    )
    all_authority_stores = tuple(
        node
        for node in ast.walk(module)
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Store)
        and node.id.startswith("PARENT_V3_")
    )
    if len(top_level) != len(_PARENT_V3_SIGNING_LITERAL_SPEC) or tuple(
        statement.target for statement in top_level
    ) != all_authority_stores:
        raise ValueError("Parent-v3 signing literal declarations are not exact")

    for statement, (expected_name, annotation_source, placeholder) in zip(
        top_level,
        _PARENT_V3_SIGNING_LITERAL_SPEC,
    ):
        if statement.simple != 1 or statement.target.id != expected_name:
            raise ValueError("Parent-v3 signing literal order or name drifted")
        expected_annotation = ast.parse(annotation_source, mode="eval").body
        if ast.dump(statement.annotation, include_attributes=False) != ast.dump(
            expected_annotation,
            include_attributes=False,
        ):
            raise ValueError("Parent-v3 signing literal annotation drifted")
        if placeholder is None:
            if not (
                type(statement.value) is ast.Constant
                and statement.value.value is None
            ):
                raise ValueError("Parent-v3 signing literal is not a placeholder")
        elif not (
            type(statement.value) is ast.Tuple
            and statement.value.elts == []
            and type(statement.value.ctx) is ast.Load
        ):
            raise ValueError("Parent-v3 signing tuple is not an empty placeholder")


def _validate_preparation_authority_blobs(
    preparation_commit_sha: str,
) -> None:
    """Reject any P tree that already carries partial signing authority."""

    commit_sha = _git_sha1(
        preparation_commit_sha,
        "preparation authority commit",
    )
    for relative_path, draft_status in (
        _PARENT_V3_MANDATORY_DRAFT_STATUS_BY_PATH.items()
    ):
        raw = _read_preparation_head_regular_blob(
            commit_sha,
            relative_path,
            required=True,
        )
        assert raw is not None
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("mandatory preparation authority doc is not UTF-8") from exc
        lines = text.splitlines()
        signed_status = _PARENT_V3_MANDATORY_SIGNED_STATUS_BY_PATH[relative_path]
        if lines.count(draft_status) != 1 or signed_status in lines:
            raise ValueError("mandatory preparation authority doc is not exact DRAFT")

    signing_literals = _read_preparation_head_regular_blob(
        commit_sha,
        _PARENT_V3_SIGNING_LITERALS_PATH,
        required=False,
    )
    if signing_literals is not None:
        _validate_parent_signing_placeholder_blob(signing_literals)


def _snapshot_clean_preparation_head() -> str:
    """Return clean non-merge HEAD=P, rejecting every signing-shaped tree."""

    status = _git_repository_command(
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status.returncode != 0 or status.stderr != b"" or status.stdout != b"":
        raise ValueError("preparation worktree is not exactly clean")
    head = _git_repository_command("rev-parse", "--verify", "HEAD")
    if head.returncode != 0 or head.stderr != b"":
        raise ValueError("preparation HEAD cannot be resolved")
    try:
        commit_sha = head.stdout.removesuffix(b"\n").decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("preparation HEAD is not ASCII") from exc
    if head.stdout != commit_sha.encode("ascii") + b"\n":
        raise ValueError("preparation HEAD output is not canonical")
    if _LOWER_GIT_SHA1.fullmatch(commit_sha) is None:
        raise ValueError("preparation HEAD is not a lowercase Git SHA-1")
    object_type = _git_repository_command("cat-file", "-t", commit_sha)
    if (
        object_type.returncode != 0
        or object_type.stderr != b""
        or object_type.stdout != b"commit\n"
    ):
        raise ValueError("preparation HEAD is not a commit")
    commit = _git_repository_command("cat-file", "commit", commit_sha)
    if commit.returncode != 0 or commit.stderr != b"":
        raise ValueError("preparation commit object cannot be read")
    header, separator, _body = commit.stdout.partition(b"\n\n")
    if separator != b"\n\n" or not header:
        raise ValueError("preparation commit object is malformed")
    parent_headers = tuple(
        line for line in header.splitlines() if line.startswith(b"parent ")
    )
    malformed_parent_headers = tuple(
        line
        for line in header.splitlines()
        if line.startswith(b"parent") and not line.startswith(b"parent ")
    )
    if malformed_parent_headers or len(parent_headers) > 1:
        raise ValueError("preparation HEAD must be a non-merge commit")
    _validate_preparation_authority_blobs(commit_sha)
    for path in _PARENT_V3_REVIEW_RECEIPT_PATHS:
        receipt = _git_repository_command("ls-tree", "-z", commit_sha, "--", path)
        if receipt.returncode != 0 or receipt.stderr != b"":
            raise ValueError("preparation receipt-tree probe failed")
        if receipt.stdout != b"":
            raise ValueError("preparation HEAD already has signing-receipt shape")
    return commit_sha


def _snapshot_clean_verification_head() -> str:
    """Snapshot one clean, non-merge verification epoch without requiring S=P."""

    status = _git_repository_command(
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status.returncode != 0 or status.stderr != b"" or status.stdout != b"":
        raise ValueError("verification worktree is not exactly clean")
    head = _git_repository_command("rev-parse", "--verify", "HEAD")
    if head.returncode != 0 or head.stderr != b"":
        raise ValueError("verification HEAD cannot be resolved")
    try:
        commit_sha = head.stdout.removesuffix(b"\n").decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("verification HEAD is not ASCII") from exc
    if (
        head.stdout != commit_sha.encode("ascii") + b"\n"
        or _LOWER_GIT_SHA1.fullmatch(commit_sha) is None
    ):
        raise ValueError("verification HEAD output is not canonical")
    object_type = _git_repository_command("cat-file", "-t", commit_sha)
    if (
        object_type.returncode != 0
        or object_type.stderr != b""
        or object_type.stdout != b"commit\n"
    ):
        raise ValueError("verification HEAD is not a commit")
    commit = _git_repository_command("cat-file", "commit", commit_sha)
    if commit.returncode != 0 or commit.stderr != b"":
        raise ValueError("verification commit object cannot be read")
    header, separator, _body = commit.stdout.partition(b"\n\n")
    if separator != b"\n\n" or not header:
        raise ValueError("verification commit object is malformed")
    parent_headers = tuple(
        line for line in header.splitlines() if line.startswith(b"parent ")
    )
    malformed_parent_headers = tuple(
        line
        for line in header.splitlines()
        if line.startswith(b"parent") and not line.startswith(b"parent ")
    )
    if malformed_parent_headers or len(parent_headers) > 1:
        raise ValueError("verification HEAD must be a non-merge commit")
    return commit_sha


def build_v3m0_parent_freeze_candidate_v3() -> ParentFreezeCandidateV3Manifest:
    """Build the sole raw candidate across two identical clean P snapshots."""

    initial_commit_sha = _snapshot_clean_preparation_head()
    candidate = _replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit(
        initial_commit_sha
    )
    _run_fresh_interpreter_completeness_audit(candidate)
    final_commit_sha = _snapshot_clean_preparation_head()
    if final_commit_sha != initial_commit_sha:
        raise ValueError("preparation HEAD changed during candidate replay")
    _freeze_parent_v3_source_closure_paths(candidate.source_closure)
    return candidate


def verify_parent_freeze_candidate_v3(
    candidate: ParentFreezeCandidateV3Manifest,
) -> ParentFreezeCandidateV3Manifest:
    """Fail closed against a fresh private replay of the declared P commit."""

    initial_verification_commit_sha = _snapshot_clean_verification_head()
    _exact_record(candidate, ParentFreezeCandidateV3Manifest, "Parent-v3 candidate")
    _require_exact_wire_tree(candidate, "Parent-v3 candidate")
    _verify_parent_candidate_v3_roots_and_registry(candidate)
    expected = _replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit(
        candidate.preparation_commit_sha
    )
    _require_exact_wire_tree(expected, "fresh Parent-v3 candidate replay")
    _require_exact_recursive_match(
        candidate,
        expected,
        "Parent-v3 candidate",
    )
    _run_fresh_interpreter_completeness_audit(candidate)
    final_verification_commit_sha = _snapshot_clean_verification_head()
    if final_verification_commit_sha != initial_verification_commit_sha:
        raise ValueError("verification HEAD changed during candidate verification")
    _freeze_parent_v3_source_closure_paths(candidate.source_closure)
    return candidate


__all__ = [
    "APPLICATION_SUPERSESSION_V3_SCHEMA_VERSION",
    "CURRENT_APPLICATION_REGISTRY_V3_SCHEMA_VERSION",
    "PARENT_FREEZE_CANDIDATE_V3_SCHEMA_VERSION",
    "PARENT_V3_SOURCE_CLOSURE_PATHS",
    "PARENT_V3_SOURCE_CLOSURE_V1_SCHEMA_VERSION",
    "REVIEWED_PATH_CLOSURE_V1_SCHEMA_VERSION",
    "ApplicationSupersessionV3",
    "ParentFreezeCandidateV3Manifest",
    "application_supersession_v3_payload",
    "build_v3m0_parent_freeze_candidate_v3",
    "current_application_registry_v3_payload",
    "parent_freeze_candidate_v3_manifest_payload",
    "parent_v3_source_closure_v1_payload",
    "reviewed_path_closure_v1_payload",
    "verify_parent_freeze_candidate_v3",
]
