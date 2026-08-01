"""Strict, private P-to-S signing audit for the Parent-v3 release epoch.

This module intentionally exposes no public issuer or hydrator.  The final
Parent-v3 facade consumes its private audited bundle only after the complete
downstream source closure has been frozen.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import replace
import hashlib
import io
import json
import os
import re
import selectors
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import tokenize
import weakref
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Callable, Final

from .evidence import canonical_sha
from .parent_freeze_v3_contracts import (
    PARENT_SIGNING_AUDIT_V1_SCHEMA_VERSION,
    PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS,
    PARENT_V3_REVIEW_RECEIPT_PATHS_BY_ROLE,
    PARENT_V3_SIGNING_DIFF_ALLOWLIST_ID,
    PARENT_V3_REVIEW_SIGNATURE_NAMESPACE,
    SIGNED_SOURCE_REF_V2_SCHEMA_VERSION,
    ParentSigningAuditV1,
    ParentReviewReceiptV1,
    SignedSourceRefV2,
    openssh_sha256_fingerprint,
    parent_signing_audit_v1_payload,
    parent_review_receipt_v1_signed_statement_payload,
    parse_parent_review_receipt_v1_json,
    signed_source_ref_v2_payload,
    signed_source_refs_v2_root_payload,
    verify_parent_review_receipt_v1,
    verify_parent_review_receipts_v1,
    verify_parent_signing_audit_v1,
    verify_parent_v3_reviewer_key_registry,
    verify_parent_v3_signing_bundle,
    verify_signed_source_refs_v2,
)
from .parent_candidate_v3 import (
    ParentFreezeCandidateV3Manifest,
    _replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit,
    _verify_parent_candidate_v3_roots_and_registry,
    verify_parent_freeze_candidate_v3,
)
from .parent_v3_contracts import (
    _TRUSTED_GIT_EXECUTABLE_IDENTITY,
    _TRUSTED_GIT_EXECUTABLE_REALPATH,
    _minimal_process_environment,
    _run_bounded_process as _run_identity_bounded_process,
    _trusted_git_environment,
)


_REGULAR_GIT_MODES: Final = frozenset(("100644", "100755"))
_LOWER_GIT_SHA1: Final = re.compile(r"[0-9a-f]{40}\Z")
_ZERO_GIT_SHA1: Final = "0" * 40
_PARENT_V3_SIGNING_LITERALS_PATH: Final = "rulespace_v3/parent_signing_literals_v1.py"
_SSH_KEYGEN_EXECUTABLE: Final = "/usr/bin/ssh-keygen"
_SSH_VERIFY_PRINCIPAL: Final = "culab-parent-v3-reviewer"
_PRIVATE_AUDIT_TOKEN: Final = object()
_REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]
_PARENT_V3_REVIEWER_REGISTRY_PATH: Final = "rulespace_v3/parent_reviewer_keys_v1.py"
_MAX_INERT_PYTHON_SOURCE_BYTES: Final = 1 << 20
_HARDENED_GIT_CONFIG_ARGUMENTS: Final = (
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.untrackedCache=false",
    "-c",
    "core.ignoreStat=false",
    "-c",
    "core.trustctime=true",
    "-c",
    "core.checkStat=default",
    "-c",
    "core.fileMode=true",
)

_MANDATORY_STATUS_TRANSFORMS_BY_PATH: Final = {
    "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md": (
        "*Computational Universe Lab · 2026-07-31 · 状态：DRAFT / 未签发 / 不生效*",
        "*Computational Universe Lab · 2026-07-31 · 状态：SIGNED / 已签发 / 生效*",
    ),
    "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · 状态：DRAFT / 未签发 / 非 Parent、permit 或 scientific authority*",
        "*Computational Universe Lab · 2026-08-01 · 状态：SIGNED / 已签发 / 非 Parent、permit 或 scientific authority*",
    ),
    "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · 状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*",
        "*Computational Universe Lab · 2026-08-01 · 状态：SIGNED / 已签发 / 非 Parent、permit、runtime 或 scientific authority*",
    ),
    "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md": (
        "*Computational Universe Lab · 2026-08-01 · 状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*",
        "*Computational Universe Lab · 2026-08-01 · 状态：SIGNED / 已签发 / 非 Parent、permit、runtime 或 scientific authority*",
    ),
}

_SIGNING_LITERAL_SPECS: Final = (
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


def _canonical_relative_path(value: object) -> str:
    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        raise ValueError("Git diff path is not a canonical repository-relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or "." in path.parts
        or ".." in path.parts
    ):
        raise ValueError("Git diff path is not a canonical repository-relative path")
    return value


@dataclass(frozen=True)
class _RawTreeDiffEntry:
    relative_path: str
    old_mode: str | None
    new_mode: str | None
    old_git_blob_oid: str | None
    new_git_blob_oid: str | None
    status: str
    old_blob_sha256: str | None = None
    new_blob_sha256: str | None = None


def _parse_raw_diff_tree_z(raw: bytes) -> tuple[_RawTreeDiffEntry, ...]:
    """Parse the one-path, SHA-1 ``git diff-tree --raw -z`` wire form."""

    if type(raw) is not bytes:
        raise TypeError("raw Git diff must be exact bytes")
    if not raw:
        return ()
    if not raw.endswith(b"\x00"):
        raise ValueError("raw Git diff is not NUL terminated")
    fields = raw.split(b"\x00")
    if fields[-1] != b"":
        raise ValueError("raw Git diff framing drifted")
    fields.pop()
    if len(fields) % 2:
        raise ValueError("raw Git diff does not contain header/path pairs")
    entries: list[_RawTreeDiffEntry] = []
    for index in range(0, len(fields), 2):
        header = fields[index]
        raw_path = fields[index + 1]
        if not header.startswith(b":") or b"\t" in header or b"\n" in header:
            raise ValueError("raw Git diff header is malformed")
        parts = header[1:].split(b" ")
        if len(parts) != 5 or any(not item for item in parts):
            raise ValueError("raw Git diff header fields drifted")
        old_mode_raw, new_mode_raw, old_oid_raw, new_oid_raw, status_raw = parts
        try:
            old_mode_text = old_mode_raw.decode("ascii")
            new_mode_text = new_mode_raw.decode("ascii")
            old_oid_text = old_oid_raw.decode("ascii")
            new_oid_text = new_oid_raw.decode("ascii")
            status = status_raw.decode("ascii")
            relative_path = _canonical_relative_path(raw_path.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError("raw Git diff contains non-canonical text") from exc
        if status not in ("A", "D", "M"):
            raise ValueError("raw Git diff contains rename/copy or unknown status")
        if (
            _LOWER_GIT_SHA1.fullmatch(old_oid_text) is None
            or _LOWER_GIT_SHA1.fullmatch(new_oid_text) is None
        ):
            raise ValueError("raw Git diff contains a malformed object ID")

        old_missing = old_mode_text == "000000" and old_oid_text == _ZERO_GIT_SHA1
        new_missing = new_mode_text == "000000" and new_oid_text == _ZERO_GIT_SHA1
        if status == "A":
            if (
                not old_missing
                or new_missing
                or new_mode_text not in _REGULAR_GIT_MODES
            ):
                raise ValueError("raw Git addition shape drifted")
        elif status == "D":
            if (
                old_missing
                or not new_missing
                or old_mode_text not in _REGULAR_GIT_MODES
            ):
                raise ValueError("raw Git deletion shape drifted")
        elif (
            old_missing
            or new_missing
            or old_mode_text not in _REGULAR_GIT_MODES
            or new_mode_text not in _REGULAR_GIT_MODES
        ):
            raise ValueError("raw Git modification is not between regular blobs")
        entries.append(
            _RawTreeDiffEntry(
                relative_path=relative_path,
                old_mode=None if old_missing else old_mode_text,
                new_mode=None if new_missing else new_mode_text,
                old_git_blob_oid=None if old_missing else old_oid_text,
                new_git_blob_oid=None if new_missing else new_oid_text,
                status=status,
            )
        )
    paths = tuple(item.relative_path for item in entries)
    if paths != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
        raise ValueError("raw Git diff paths are not in UTF-8 order")
    if len(paths) != len(set(paths)):
        raise ValueError("raw Git diff contains duplicate paths")
    return tuple(entries)


def _repository_path(value: object) -> Path:
    if not isinstance(value, Path):
        raise TypeError("repository root must be a Path")
    try:
        result = value.resolve(strict=True)
    except OSError as exc:
        raise ValueError("repository root cannot be resolved") from exc
    if not result.is_dir():
        raise ValueError("repository root is not a directory")
    return result


def _stop_bounded_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=1)
    except OSError:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=1)


def _run_bounded_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
    environment: dict[str, str],
    input_bytes: bytes | None,
    maximum_stdout_bytes: int,
    maximum_stderr_bytes: int,
    timeout_seconds: int | float,
) -> subprocess.CompletedProcess[bytes]:
    """Drain a child incrementally and kill it at the first byte over a cap."""

    if (
        type(command) is not tuple
        or not command
        or any(type(item) is not str or not item for item in command)
    ):
        raise TypeError("bounded-process command must be an exact string tuple")
    root = _repository_path(cwd)
    if type(environment) is not dict or any(
        type(key) is not str or type(value) is not str
        for key, value in environment.items()
    ):
        raise TypeError("bounded-process environment must be an exact string dict")
    if input_bytes is not None and type(input_bytes) is not bytes:
        raise TypeError("bounded-process input must be exact bytes or None")
    if (
        type(maximum_stdout_bytes) is not int
        or type(maximum_stderr_bytes) is not int
        or maximum_stdout_bytes < 0
        or maximum_stderr_bytes < 0
    ):
        raise TypeError("bounded-process stream limits must be non-negative integers")
    if type(timeout_seconds) not in (int, float) or timeout_seconds <= 0:
        raise TypeError("bounded-process timeout must be positive")
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            shell=False,
            env=environment,
            stdin=(subprocess.DEVNULL if input_bytes is None else subprocess.PIPE),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ValueError("bounded child could not start") from exc
    assert process.stdout is not None
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    streams = {
        "stdout": (process.stdout, maximum_stdout_bytes),
        "stderr": (process.stderr, maximum_stderr_bytes),
    }
    input_offset = 0
    deadline = time.monotonic() + float(timeout_seconds)
    try:
        for stream_name, (stream, _limit) in streams.items():
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, stream_name)
        if input_bytes is not None:
            assert process.stdin is not None
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _stop_bounded_process(process)
                raise ValueError("bounded child timed out")
            events = selector.select(min(remaining, 0.1))
            if not events:
                continue
            for key, _mask in events:
                stream_name = key.data
                stream = key.fileobj
                if stream_name == "stdin":
                    assert input_bytes is not None
                    try:
                        written = os.write(
                            stream.fileno(),
                            input_bytes[input_offset : input_offset + 65536],
                        )
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        written = 0
                    input_offset += written
                    if written == 0 or input_offset == len(input_bytes):
                        selector.unregister(stream)
                        stream.close()
                    continue
                limit = streams[stream_name][1]
                try:
                    chunk = os.read(stream.fileno(), min(65536, limit + 1))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    continue
                room = limit + 1 - len(buffers[stream_name])
                buffers[stream_name].extend(chunk[: max(room, 0)])
                if len(buffers[stream_name]) > limit:
                    _stop_bounded_process(process)
                    raise ValueError(
                        f"bounded child {stream_name} exceeded stream limit"
                    )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _stop_bounded_process(process)
            raise ValueError("bounded child timed out")
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _stop_bounded_process(process)
            raise ValueError("bounded child timed out") from exc
        return subprocess.CompletedProcess(
            args=command,
            returncode=returncode,
            stdout=bytes(buffers["stdout"]),
            stderr=bytes(buffers["stderr"]),
        )
    finally:
        selector.close()
        for stream, _limit in streams.values():
            stream.close()
        if (
            input_bytes is not None
            and process.stdin is not None
            and not process.stdin.closed
        ):
            process.stdin.close()
        if process.poll() is None:
            _stop_bounded_process(process)


def _git_command(
    repository_root: Path, *arguments: str
) -> subprocess.CompletedProcess[bytes]:
    root = _repository_path(repository_root)
    if not arguments or any(type(item) is not str or not item for item in arguments):
        raise TypeError("Git command arguments must be exact non-empty strings")
    environment = _trusted_git_environment()
    environment["GIT_LITERAL_PATHSPECS"] = "1"
    environment["GIT_WORK_TREE"] = os.fspath(root)
    return _run_identity_bounded_process(
        (
            _TRUSTED_GIT_EXECUTABLE_REALPATH,
            *_HARDENED_GIT_CONFIG_ARGUMENTS,
            *arguments,
        ),
        cwd=root,
        env=environment,
        input_bytes=b"",
        timeout_seconds=60,
        max_stdout_bytes=8 << 20,
        max_stderr_bytes=1 << 20,
        executable_identity=_TRUSTED_GIT_EXECUTABLE_IDENTITY,
    )


def _canonical_git_stdout_sha(raw: bytes, field: str) -> str:
    if type(raw) is not bytes:
        raise TypeError(f"{field} output must be exact bytes")
    try:
        value = raw.removesuffix(b"\n").decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{field} output is not ASCII") from exc
    if raw != value.encode("ascii") + b"\n" or _LOWER_GIT_SHA1.fullmatch(value) is None:
        raise ValueError(f"{field} output is not one canonical Git SHA-1")
    return value


def _snapshot_clean_head(repository_root: Path) -> str:
    root = _repository_path(repository_root)

    top_level = _git_command(root, "rev-parse", "--show-toplevel")
    expected_top_level = os.fspath(root).encode("utf-8") + b"\n"
    if (
        top_level.returncode != 0
        or top_level.stderr != b""
        or top_level.stdout != expected_top_level
    ):
        raise ValueError("strict signing worktree root binding drifted")

    def read_head() -> str:
        head = _git_command(root, "rev-parse", "--verify", "HEAD")
        if head.returncode != 0 or head.stderr != b"":
            raise ValueError("strict signing HEAD cannot be resolved")
        return _canonical_git_stdout_sha(head.stdout, "strict signing HEAD")

    def require_clean_status() -> None:
        status = _git_command(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        )
        if status.returncode != 0 or status.stderr != b"" or status.stdout != b"":
            raise ValueError("strict signing worktree is not exactly clean")

    def require_visible_index_entries() -> None:
        listed = _git_command(root, "ls-files", "-v", "-z")
        if listed.returncode != 0 or listed.stderr != b"":
            raise ValueError("strict signing index visibility cannot be audited")
        if listed.stdout and not listed.stdout.endswith(b"\x00"):
            raise ValueError("strict signing index visibility framing drifted")
        records = listed.stdout.split(b"\x00")
        if records and records[-1] == b"":
            records.pop()
        if any(not record.startswith(b"H ") or len(record) <= 2 for record in records):
            raise ValueError(
                "strict signing index contains hidden or non-canonical entries"
            )

    commit_sha = read_head()
    require_visible_index_entries()
    require_clean_status()
    object_type = _git_command(root, "cat-file", "-t", commit_sha)
    if (
        object_type.returncode != 0
        or object_type.stderr != b""
        or object_type.stdout != b"commit\n"
    ):
        raise ValueError("strict signing HEAD is not a commit")
    require_visible_index_entries()
    require_clean_status()
    final_commit_sha = read_head()
    if final_commit_sha != commit_sha:
        raise ValueError("strict signing HEAD changed during clean snapshot")
    return final_commit_sha


def _single_parent_commit(repository_root: Path, signing_commit_sha: str) -> str:
    if (
        type(signing_commit_sha) is not str
        or _LOWER_GIT_SHA1.fullmatch(signing_commit_sha) is None
    ):
        raise ValueError("signing commit is not a lowercase Git SHA-1")
    object_type = _git_command(repository_root, "cat-file", "-t", signing_commit_sha)
    if (
        object_type.returncode != 0
        or object_type.stderr != b""
        or object_type.stdout != b"commit\n"
    ):
        raise ValueError("signing object is not a commit")
    commit = _git_command(repository_root, "cat-file", "commit", signing_commit_sha)
    if commit.returncode != 0 or commit.stderr != b"":
        raise ValueError("signing commit body cannot be read")
    header, separator, _message = commit.stdout.partition(b"\n\n")
    if separator != b"\n\n" or not header:
        raise ValueError("signing commit body is malformed")
    parents = tuple(line for line in header.splitlines() if line.startswith(b"parent "))
    malformed = tuple(
        line
        for line in header.splitlines()
        if line.startswith(b"parent") and not line.startswith(b"parent ")
    )
    if malformed or len(parents) != 1:
        raise ValueError("signing commit must have one exact single parent")
    try:
        parent = parents[0].removeprefix(b"parent ").decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("signing parent is not ASCII") from exc
    if _LOWER_GIT_SHA1.fullmatch(parent) is None:
        raise ValueError("signing parent is not a lowercase Git SHA-1")
    return parent


@dataclass(frozen=True)
class _TreeBlob:
    mode: str
    object_id: str
    raw: bytes


def _read_tree_blob(
    repository_root: Path,
    commit_sha: str,
    relative_path: str,
) -> _TreeBlob | None:
    if type(commit_sha) is not str or _LOWER_GIT_SHA1.fullmatch(commit_sha) is None:
        raise ValueError("tree commit is not a lowercase Git SHA-1")
    path = _canonical_relative_path(relative_path)
    result = _git_command(repository_root, "ls-tree", "-z", commit_sha, "--", path)
    if result.returncode != 0 or result.stderr != b"":
        raise ValueError("strict signing tree probe failed")
    if result.stdout == b"":
        return None
    records = result.stdout.split(b"\x00")
    if len(records) != 2 or records[-1] != b"" or not records[0]:
        raise ValueError("strict signing tree path is not one exact entry")
    metadata, separator, observed_path = records[0].partition(b"\t")
    if separator != b"\t" or observed_path != path.encode("utf-8"):
        raise ValueError("strict signing tree path drifted")
    fields = metadata.split(b" ")
    if len(fields) != 3:
        raise ValueError("strict signing tree metadata is malformed")
    try:
        mode = fields[0].decode("ascii")
        object_type = fields[1].decode("ascii")
        object_id = fields[2].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("strict signing tree metadata is not ASCII") from exc
    if (
        mode not in _REGULAR_GIT_MODES
        or object_type != "blob"
        or _LOWER_GIT_SHA1.fullmatch(object_id) is None
    ):
        raise ValueError("strict signing path is not a regular SHA-1 blob")
    blob = _git_command(repository_root, "cat-file", "blob", object_id)
    if blob.returncode != 0 or blob.stderr != b"":
        raise ValueError("strict signing blob cannot be read")
    return _TreeBlob(mode=mode, object_id=object_id, raw=blob.stdout)


def _replay_git_tree_diff(
    repository_root: Path,
    preparation_commit_sha: str,
    signing_commit_sha: str,
) -> tuple[_RawTreeDiffEntry, ...]:
    if (
        _single_parent_commit(repository_root, signing_commit_sha)
        != preparation_commit_sha
    ):
        raise ValueError("signing commit direct parent is not the reviewed preparation")
    diff = _git_command(
        repository_root,
        "-c",
        "core.quotePath=false",
        "-c",
        "diff.renames=false",
        "diff-tree",
        "--no-commit-id",
        "-r",
        "--raw",
        "-z",
        "--no-renames",
        "--no-ext-diff",
        preparation_commit_sha,
        signing_commit_sha,
        "--",
    )
    if diff.returncode != 0 or diff.stderr != b"":
        raise ValueError("strict signing raw tree diff failed")
    parsed = _parse_raw_diff_tree_z(diff.stdout)
    replayed: list[_RawTreeDiffEntry] = []
    for item in parsed:
        old = _read_tree_blob(
            repository_root, preparation_commit_sha, item.relative_path
        )
        new = _read_tree_blob(repository_root, signing_commit_sha, item.relative_path)
        if (
            (None if old is None else old.mode) != item.old_mode
            or (None if new is None else new.mode) != item.new_mode
            or (None if old is None else old.object_id) != item.old_git_blob_oid
            or (None if new is None else new.object_id) != item.new_git_blob_oid
        ):
            raise ValueError("raw tree diff disagrees with immutable tree replay")
        replayed.append(
            replace(
                item,
                old_blob_sha256=(
                    None if old is None else hashlib.sha256(old.raw).hexdigest()
                ),
                new_blob_sha256=(
                    None if new is None else hashlib.sha256(new.raw).hexdigest()
                ),
            )
        )
    return tuple(replayed)


def _signing_tree_diff_digest(entries: tuple[_RawTreeDiffEntry, ...]) -> str:
    if type(entries) is not tuple or any(
        type(item) is not _RawTreeDiffEntry for item in entries
    ):
        raise TypeError("signing tree diff must be an exact entry tuple")
    paths = tuple(item.relative_path for item in entries)
    if paths != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))) or len(
        paths
    ) != len(set(paths)):
        raise ValueError("signing tree diff paths are not canonical")
    return canonical_sha(
        {
            "tree_diff_schema_version": "v3m0.parent-signing-tree-diff.v1",
            "entries": [
                [
                    item.relative_path,
                    item.old_mode,
                    item.new_mode,
                    item.old_git_blob_oid,
                    item.new_git_blob_oid,
                    item.old_blob_sha256,
                    item.new_blob_sha256,
                ]
                for item in entries
            ],
        }
    )


def _parse_reviewer_registry_source(
    raw: bytes,
) -> tuple[tuple[str, str, str, str], ...]:
    """Read the P registry as one inert AST literal, never by importing it."""

    if type(raw) is not bytes:
        raise TypeError("reviewer registry source must be exact bytes")
    if len(raw) > _MAX_INERT_PYTHON_SOURCE_BYTES:
        raise ValueError("reviewer registry source exceeds the 1 MiB cap")
    if b"\r" in raw or not raw.endswith(b"\n"):
        raise ValueError("reviewer registry source must use canonical LF framing")
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("reviewer registry source is not strict UTF-8") from exc
    if source.startswith("\ufeff"):
        raise ValueError("reviewer registry source contains a BOM")
    try:
        module = ast.parse(source, filename="rulespace_v3/parent_reviewer_keys_v1.py")
    except SyntaxError as exc:
        raise ValueError("reviewer registry source is invalid Python") from exc
    body = module.body
    if len(body) != 4:
        raise ValueError("reviewer registry module statement shape drifted")
    docstring, future, registry_assignment, all_assignment = body
    if (
        type(docstring) is not ast.Expr
        or type(docstring.value) is not ast.Constant
        or type(docstring.value.value) is not str
        or type(future) is not ast.ImportFrom
        or future.module != "__future__"
        or future.level != 0
        or tuple((item.name, item.asname) for item in future.names)
        != (("annotations", None),)
    ):
        raise ValueError("reviewer registry imports or docstring drifted")
    if (
        type(registry_assignment) is not ast.AnnAssign
        or registry_assignment.simple != 1
        or type(registry_assignment.target) is not ast.Name
        or registry_assignment.target.id != "PARENT_V3_TRUSTED_REVIEWER_KEYS_V1"
        or registry_assignment.value is None
    ):
        raise ValueError("reviewer registry declaration drifted")
    expected_annotation = ast.parse(
        "tuple[tuple[str, str, str, str], ...]", mode="eval"
    ).body
    if ast.dump(registry_assignment.annotation, include_attributes=False) != ast.dump(
        expected_annotation, include_attributes=False
    ):
        raise ValueError("reviewer registry annotation drifted")
    if (
        type(all_assignment) is not ast.Assign
        or len(all_assignment.targets) != 1
        or type(all_assignment.targets[0]) is not ast.Name
        or all_assignment.targets[0].id != "__all__"
    ):
        raise ValueError("reviewer registry __all__ declaration drifted")
    try:
        exported = ast.literal_eval(all_assignment.value)
        registry = ast.literal_eval(registry_assignment.value)
    except (TypeError, ValueError) as exc:
        raise ValueError("reviewer registry module contains executable values") from exc
    if exported != ["PARENT_V3_TRUSTED_REVIEWER_KEYS_V1"]:
        raise ValueError("reviewer registry __all__ value drifted")
    return verify_parent_v3_reviewer_key_registry(registry)


def _parent_review_signed_statement_bytes(receipt: ParentReviewReceiptV1) -> bytes:
    if type(receipt) is not ParentReviewReceiptV1:
        raise TypeError("review receipt must be an exact ParentReviewReceiptV1")
    payload = parent_review_receipt_v1_signed_statement_payload(receipt)
    if receipt.signed_statement_sha != canonical_sha(payload):
        raise ValueError("review receipt signed-statement root drifted")
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("review signed statement is not canonical JSON") from exc


def _verify_review_receipt_signature(
    receipt: ParentReviewReceiptV1,
    registry_entry: tuple[str, str, str, str],
) -> ParentReviewReceiptV1:
    verified = verify_parent_review_receipt_v1(receipt)
    if (
        type(registry_entry) is not tuple
        or len(registry_entry) != 4
        or any(type(item) is not str for item in registry_entry)
    ):
        raise TypeError("reviewer registry entry must be one exact four-string tuple")
    role, reviewer_id, reviewer_key_id, public_key_text = registry_entry
    if (
        verified.review_role != role
        or verified.reviewer_id != reviewer_id
        or verified.reviewer_key_id != reviewer_key_id
    ):
        raise ValueError("review receipt identity does not match the P registry")
    if openssh_sha256_fingerprint(public_key_text) != reviewer_key_id:
        raise ValueError("reviewer registry public-key fingerprint drifted")
    statement = _parent_review_signed_statement_bytes(verified)
    executable = Path(_SSH_KEYGEN_EXECUTABLE)
    try:
        resolved_executable = executable.resolve(strict=True)
        resolved_executable.stat()
    except OSError as exc:
        raise ValueError("trusted ssh-keygen executable is unavailable") from exc
    if (
        not resolved_executable.is_file()
        or not os.access(resolved_executable, os.X_OK)
        or resolved_executable.as_posix() != _SSH_KEYGEN_EXECUTABLE
    ):
        raise ValueError("trusted ssh-keygen executable identity drifted")
    with tempfile.TemporaryDirectory(prefix="culab-parent-v3-signature-") as raw_temp:
        directory = Path(raw_temp).resolve(strict=True)
        allowed_signers = directory / "allowed_signers"
        signature = directory / "receipt.sig"
        allowed_signers.write_bytes(
            f"{_SSH_VERIFY_PRINCIPAL} {public_key_text}\n".encode("ascii")
        )
        signature.write_bytes(verified.signature_armor.encode("ascii"))
        allowed_signers.chmod(0o600)
        signature.chmod(0o600)
        completed = _run_bounded_process(
            (
                _SSH_KEYGEN_EXECUTABLE,
                "-Y",
                "verify",
                "-f",
                os.fspath(allowed_signers),
                "-I",
                _SSH_VERIFY_PRINCIPAL,
                "-n",
                PARENT_V3_REVIEW_SIGNATURE_NAMESPACE,
                "-s",
                os.fspath(signature),
            ),
            cwd=directory,
            environment=_minimal_process_environment(),
            input_bytes=statement,
            maximum_stdout_bytes=65536,
            maximum_stderr_bytes=65536,
            timeout_seconds=30,
        )
    if completed.returncode != 0:
        raise ValueError("review receipt Ed25519 signature is invalid")
    return receipt


@dataclass(frozen=True)
class _ParentV3SigningAuditBundle:
    reviewed_candidate_v3: ParentFreezeCandidateV3Manifest
    signed_source_refs: tuple[SignedSourceRefV2, ...]
    review_receipts: tuple[ParentReviewReceiptV1, ...]
    signing_audit: ParentSigningAuditV1
    protected_signing_tree: tuple[tuple[str, str], ...]


def _validate_signing_audit_bundle(
    value: object,
) -> _ParentV3SigningAuditBundle:
    if type(value) is not _ParentV3SigningAuditBundle:
        raise TypeError("signing audit bundle must be the exact private record")
    candidate = value.reviewed_candidate_v3
    if type(candidate) is not ParentFreezeCandidateV3Manifest:
        raise TypeError("signing audit bundle candidate is not exact")
    _verify_parent_candidate_v3_roots_and_registry(candidate)
    references = verify_signed_source_refs_v2(value.signed_source_refs)
    receipts = verify_parent_review_receipts_v1(value.review_receipts, candidate)
    audit = verify_parent_signing_audit_v1(value.signing_audit)
    verify_parent_v3_signing_bundle(candidate, references, receipts, audit)
    if (
        type(value.protected_signing_tree) is not tuple
        or not value.protected_signing_tree
    ):
        raise TypeError("protected signing tree must be a non-empty exact tuple")
    paths: list[str] = []
    for index, entry in enumerate(value.protected_signing_tree):
        if (
            type(entry) is not tuple
            or len(entry) != 2
            or type(entry[0]) is not str
            or type(entry[1]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", entry[1]) is None
        ):
            raise TypeError(
                f"protected signing tree[{index}] is not an exact path/SHA pair"
            )
        paths.append(_canonical_relative_path(entry[0]))
    if tuple(paths) != tuple(
        sorted(paths, key=lambda item: item.encode("utf-8"))
    ) or len(paths) != len(set(paths)):
        raise ValueError("protected signing tree paths are not canonical")
    return copy.deepcopy(value)


def _signing_audit_bundle_seal(value: object) -> str:
    bundle = _validate_signing_audit_bundle(value)
    return canonical_sha(
        {
            "authority_kind": "v3m0-private-parent-signing-audit.v1",
            "candidate_sha": bundle.reviewed_candidate_v3.candidate_sha,
            "audit_sha": bundle.signing_audit.audit_sha,
            "protected_signing_tree": [
                list(item) for item in bundle.protected_signing_tree
            ],
        }
    )


def _build_signed_source_refs(
    *,
    preparation_commit_sha: str,
    signing_commit_sha: str,
    signing_blobs_by_path: dict[str, _TreeBlob],
) -> tuple[SignedSourceRefV2, ...]:
    references: list[SignedSourceRefV2] = []
    for path, role, scope in PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS:
        blob = signing_blobs_by_path.get(path)
        if blob is None:
            raise ValueError("mandatory signed source blob is missing")
        provisional = SignedSourceRefV2(
            source_ref_schema_version=SIGNED_SOURCE_REF_V2_SCHEMA_VERSION,
            source_role=role,
            source_scope=scope,
            relative_path=path,
            raw_sha256=hashlib.sha256(blob.raw).hexdigest(),
            preparation_commit_sha=preparation_commit_sha,
            signing_commit_sha=signing_commit_sha,
            source_ref_sha="0" * 64,
        )
        references.append(
            replace(
                provisional,
                source_ref_sha=canonical_sha(signed_source_ref_v2_payload(provisional)),
            )
        )
    return verify_signed_source_refs_v2(tuple(references))


def _required_allowlist_paths() -> tuple[str, ...]:
    result = (
        *tuple(_MANDATORY_STATUS_TRANSFORMS_BY_PATH),
        *tuple(path for _role, path in PARENT_V3_REVIEW_RECEIPT_PATHS_BY_ROLE),
        _PARENT_V3_SIGNING_LITERALS_PATH,
    )
    return tuple(sorted(result, key=lambda item: item.encode("utf-8")))


def _audit_repository_signing_bundle(
    repository_root: Path,
    *,
    candidate_replayer: Callable[[str], ParentFreezeCandidateV3Manifest],
    candidate_verifier: Callable[
        [ParentFreezeCandidateV3Manifest], ParentFreezeCandidateV3Manifest
    ],
) -> _ParentV3SigningAuditBundle:
    """Audit one clean S repository.  Injection points are private test seams."""

    if not callable(candidate_replayer) or not callable(candidate_verifier):
        raise TypeError("candidate replay dependencies must be callable")
    signing_commit_sha = _snapshot_clean_head(repository_root)
    preparation_commit_sha = _single_parent_commit(repository_root, signing_commit_sha)
    candidate = candidate_replayer(preparation_commit_sha)
    if type(candidate) is not ParentFreezeCandidateV3Manifest:
        raise TypeError("candidate replayer did not return the exact v3 record")
    if candidate.preparation_commit_sha != preparation_commit_sha:
        raise ValueError("replayed candidate does not bind the signing parent")
    verified_candidate = candidate_verifier(candidate)
    if verified_candidate is not candidate and verified_candidate != candidate:
        raise ValueError("candidate verifier returned a different body")
    _verify_parent_candidate_v3_roots_and_registry(candidate)

    source_closure_by_path = {
        path: (mode, raw_sha) for path, mode, raw_sha in candidate.source_closure
    }
    mandatory_preparation_paths = (
        *tuple(_MANDATORY_STATUS_TRANSFORMS_BY_PATH),
        _PARENT_V3_SIGNING_LITERALS_PATH,
        _PARENT_V3_REVIEWER_REGISTRY_PATH,
    )
    if any(path not in source_closure_by_path for path in mandatory_preparation_paths):
        raise ValueError("candidate source closure omits a signing authority path")

    tree_diff = _replay_git_tree_diff(
        repository_root,
        preparation_commit_sha,
        signing_commit_sha,
    )
    observed_paths = tuple(item.relative_path for item in tree_diff)
    if observed_paths != _required_allowlist_paths():
        raise ValueError("P-to-S changed paths differ from the exact signing allowlist")

    preparation_blobs: dict[str, _TreeBlob | None] = {}
    signing_blobs: dict[str, _TreeBlob | None] = {}
    for path in observed_paths:
        preparation_blobs[path] = _read_tree_blob(
            repository_root, preparation_commit_sha, path
        )
        signing_blobs[path] = _read_tree_blob(repository_root, signing_commit_sha, path)
    diff_by_path = {item.relative_path: item for item in tree_diff}
    for path in _MANDATORY_STATUS_TRANSFORMS_BY_PATH:
        item = diff_by_path[path]
        old = preparation_blobs[path]
        new = signing_blobs[path]
        if (
            item.status != "M"
            or old is None
            or new is None
            or old.mode != new.mode
            or source_closure_by_path[path]
            != (
                old.mode,
                hashlib.sha256(old.raw).hexdigest(),
            )
        ):
            raise ValueError("mandatory signed-source tree binding drifted")
        _audit_exact_document_transform(path, old.raw, new.raw)

    receipt_by_role: list[ParentReviewReceiptV1] = []
    for role, path in PARENT_V3_REVIEW_RECEIPT_PATHS_BY_ROLE:
        item = diff_by_path[path]
        old = preparation_blobs[path]
        new = signing_blobs[path]
        if item.status != "A" or old is not None or new is None or new.mode != "100644":
            raise ValueError("review receipt is not one exact S-only regular addition")
        receipt = parse_parent_review_receipt_v1_json(new.raw)
        if receipt.review_role != role:
            raise ValueError("review receipt path/role mapping drifted")
        receipt_by_role.append(receipt)
    receipts = verify_parent_review_receipts_v1(tuple(receipt_by_role), candidate)

    registry_preparation = _read_tree_blob(
        repository_root,
        preparation_commit_sha,
        _PARENT_V3_REVIEWER_REGISTRY_PATH,
    )
    registry_signing = _read_tree_blob(
        repository_root,
        signing_commit_sha,
        _PARENT_V3_REVIEWER_REGISTRY_PATH,
    )
    if (
        registry_preparation is None
        or registry_signing is None
        or registry_preparation != registry_signing
        or source_closure_by_path[_PARENT_V3_REVIEWER_REGISTRY_PATH]
        != (
            registry_preparation.mode,
            hashlib.sha256(registry_preparation.raw).hexdigest(),
        )
    ):
        raise ValueError("P reviewer registry changed or escaped the source closure")
    reviewer_registry = _parse_reviewer_registry_source(registry_preparation.raw)
    if len(reviewer_registry) != len(receipts):
        raise ValueError("P reviewer registry is not complete")
    for receipt, registry_entry in zip(receipts, reviewer_registry):
        _verify_review_receipt_signature(receipt, registry_entry)

    signed_source_blobs = {
        path: blob
        for path, blob in signing_blobs.items()
        if path in _MANDATORY_STATUS_TRANSFORMS_BY_PATH and blob is not None
    }
    references = _build_signed_source_refs(
        preparation_commit_sha=preparation_commit_sha,
        signing_commit_sha=signing_commit_sha,
        signing_blobs_by_path=signed_source_blobs,
    )
    literals_item = diff_by_path[_PARENT_V3_SIGNING_LITERALS_PATH]
    literals_preparation = preparation_blobs[_PARENT_V3_SIGNING_LITERALS_PATH]
    literals_signing = signing_blobs[_PARENT_V3_SIGNING_LITERALS_PATH]
    if (
        literals_item.status != "M"
        or literals_preparation is None
        or literals_signing is None
        or literals_preparation.mode != literals_signing.mode
        or source_closure_by_path[_PARENT_V3_SIGNING_LITERALS_PATH]
        != (
            literals_preparation.mode,
            hashlib.sha256(literals_preparation.raw).hexdigest(),
        )
    ):
        raise ValueError("signing literal tree binding drifted")
    _audit_signing_literals_transform(
        literals_preparation.raw,
        literals_signing.raw,
        preparation_commit_sha=preparation_commit_sha,
        reviewed_candidate_sha=candidate.candidate_sha,
        reviewed_path_closure_sha=receipts[0].reviewed_path_closure_sha,
        signed_source_sha256_by_path=tuple(
            (reference.relative_path, reference.raw_sha256) for reference in references
        ),
        review_receipt_sha256_by_role=tuple(
            (receipt.review_role, receipt.receipt_sha) for receipt in receipts
        ),
    )

    diff_digest = _signing_tree_diff_digest(tree_diff)
    provisional_audit = ParentSigningAuditV1(
        audit_schema_version=PARENT_SIGNING_AUDIT_V1_SCHEMA_VERSION,
        preparation_commit_sha=preparation_commit_sha,
        signing_commit_sha=signing_commit_sha,
        review_receipt_shas=tuple(item.receipt_sha for item in receipts),
        diff_digest=diff_digest,
        diff_allowlist_id=PARENT_V3_SIGNING_DIFF_ALLOWLIST_ID,
        signed_source_refs_root_sha=canonical_sha(
            signed_source_refs_v2_root_payload(references)
        ),
        reviewed_candidate_sha=candidate.candidate_sha,
        reviewed_path_closure_sha=receipts[0].reviewed_path_closure_sha,
        source_closure_sha=candidate.source_closure_sha,
        audit_sha="0" * 64,
    )
    audit = replace(
        provisional_audit,
        audit_sha=canonical_sha(parent_signing_audit_v1_payload(provisional_audit)),
    )
    verify_parent_v3_signing_bundle(candidate, references, receipts, audit)

    protected_paths = tuple(
        sorted(
            set(source_closure_by_path) | set(observed_paths),
            key=lambda item: item.encode("utf-8"),
        )
    )
    protected_signing_tree: list[tuple[str, str]] = []
    for path in protected_paths:
        blob = _read_tree_blob(repository_root, signing_commit_sha, path)
        if blob is None:
            raise ValueError("protected signing path is absent from S")
        protected_signing_tree.append((path, hashlib.sha256(blob.raw).hexdigest()))
    bundle = _ParentV3SigningAuditBundle(
        reviewed_candidate_v3=candidate,
        signed_source_refs=references,
        review_receipts=receipts,
        signing_audit=audit,
        protected_signing_tree=tuple(protected_signing_tree),
    )
    _validate_signing_audit_bundle(bundle)
    if _snapshot_clean_head(repository_root) != signing_commit_sha:
        raise ValueError("signing HEAD changed during strict P-to-S audit")
    return bundle


class _VerifiedParentSigningAuditV1:
    __slots__ = ("__snapshot", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        snapshot: object,
        seal: str,
        *,
        _token: object = _PRIVATE_AUDIT_TOKEN,
        _setattr=object.__setattr__,
    ) -> None:
        if token is not _token:
            raise TypeError("Parent signing-audit capability is private")
        _setattr(
            self, "_VerifiedParentSigningAuditV1__snapshot", copy.deepcopy(snapshot)
        )
        _setattr(self, "_VerifiedParentSigningAuditV1__token", token)
        _setattr(self, "_VerifiedParentSigningAuditV1__seal", seal)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("Parent signing-audit capability is immutable")


def _make_private_audit_registry(
    *,
    validator: Callable[[object], object],
    seal_builder: Callable[[object], str],
) -> tuple[
    Callable[[object], _VerifiedParentSigningAuditV1],
    Callable[[_VerifiedParentSigningAuditV1], object],
    type[_VerifiedParentSigningAuditV1],
]:
    if not callable(validator) or not callable(seal_builder):
        raise TypeError("private audit registry dependencies must be callable")
    registry: dict[
        int,
        tuple[weakref.ReferenceType[_VerifiedParentSigningAuditV1], object, str],
    ] = {}
    lock = threading.RLock()

    def issue(snapshot: object) -> _VerifiedParentSigningAuditV1:
        validated = validator(snapshot)
        detached = copy.deepcopy(validated)
        seal = seal_builder(detached)
        if type(seal) is not str or re.fullmatch(r"[0-9a-f]{64}", seal) is None:
            raise ValueError("private audit seal is not a lowercase SHA-256")
        wrapper = _VerifiedParentSigningAuditV1(
            _PRIVATE_AUDIT_TOKEN,
            detached,
            seal,
        )
        identity = id(wrapper)

        def remove_stale(
            reference: weakref.ReferenceType[_VerifiedParentSigningAuditV1],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = registry.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del registry[wrapper_id]

        reference = weakref.ref(wrapper, remove_stale)
        with lock:
            current = registry.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("private audit live-identity collision")
            registry[identity] = (reference, detached, seal)
        return wrapper

    def require(wrapper: _VerifiedParentSigningAuditV1) -> object:
        if type(wrapper) is not _VerifiedParentSigningAuditV1:
            raise TypeError("private audit consumer requires the exact wrapper")
        with lock:
            current = registry.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError("private audit identity is absent from the registry")
            expected_snapshot = copy.deepcopy(current[1])
            expected_seal = current[2]
        try:
            token = object.__getattribute__(
                wrapper, "_VerifiedParentSigningAuditV1__token"
            )
            snapshot = object.__getattribute__(
                wrapper, "_VerifiedParentSigningAuditV1__snapshot"
            )
            seal = object.__getattribute__(
                wrapper, "_VerifiedParentSigningAuditV1__seal"
            )
        except AttributeError as exc:
            raise ValueError("private audit capability is incomplete") from exc
        if token is not _PRIVATE_AUDIT_TOKEN:
            raise ValueError("private audit token drifted")
        validated = validator(snapshot)
        observed_seal = seal_builder(validated)
        if seal != expected_seal or seal != observed_seal:
            raise ValueError("private audit seal drifted")
        if validated != expected_snapshot:
            raise ValueError("private audit snapshot drifted")
        return copy.deepcopy(expected_snapshot)

    return issue, require, _VerifiedParentSigningAuditV1


def _audit_exact_document_transform(
    relative_path: str,
    preparation_blob: bytes,
    signing_blob: bytes,
) -> None:
    if relative_path not in _MANDATORY_STATUS_TRANSFORMS_BY_PATH:
        raise ValueError("document path is not in the signing allowlist")
    if type(preparation_blob) is not bytes or type(signing_blob) is not bytes:
        raise TypeError("signed source blobs must be exact bytes")

    def authority_markers(raw: bytes, epoch: str) -> tuple[tuple[str, int, int], ...]:
        if b"\r" in raw or not raw.endswith(b"\n"):
            raise ValueError(f"{epoch} document must use canonical LF framing")
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{epoch} document is not strict UTF-8") from exc
        if source.startswith("\ufeff"):
            raise ValueError(f"{epoch} document contains a BOM")
        markers: list[tuple[str, int, int]] = []
        fence_character: str | None = None
        fence_length = 0
        byte_cursor = 0
        for line in source.splitlines(keepends=True):
            content = line.removesuffix("\n")
            leading = len(content) - len(content.lstrip(" "))
            stripped = content[leading:] if leading <= 3 else content
            if stripped and stripped[0] in ("`", "~"):
                run_character = stripped[0]
                run_length = len(stripped) - len(stripped.lstrip(run_character))
                remainder = stripped[run_length:]
                if fence_character is None and leading <= 3 and run_length >= 3:
                    fence_character = run_character
                    fence_length = run_length
                    byte_cursor += len(line.encode("utf-8"))
                    continue
                if (
                    fence_character == run_character
                    and leading <= 3
                    and run_length >= fence_length
                    and not remainder.strip()
                ):
                    fence_character = None
                    fence_length = 0
                    byte_cursor += len(line.encode("utf-8"))
                    continue
            if (
                fence_character is None
                and "Computational Universe Lab · " in content
                and " · 状态：" in content
            ):
                if not content.startswith("*Computational Universe Lab · "):
                    raise ValueError(
                        f"{epoch} document contains an alternate authority header"
                    )
                encoded = content.encode("utf-8")
                markers.append((content, byte_cursor, byte_cursor + len(encoded)))
            byte_cursor += len(line.encode("utf-8"))
        if fence_character is not None:
            raise ValueError(f"{epoch} document contains an unclosed Markdown fence")
        return tuple(markers)

    draft, signed = _MANDATORY_STATUS_TRANSFORMS_BY_PATH[relative_path]
    preparation_markers = authority_markers(preparation_blob, "preparation")
    signing_markers = authority_markers(signing_blob, "signing")
    if tuple(item[0] for item in preparation_markers) != (draft,):
        raise ValueError("preparation document authority header is not exact DRAFT")
    if tuple(item[0] for item in signing_markers) != (signed,):
        raise ValueError("signing document authority header is not exact SIGNED")
    _marker, start, end = preparation_markers[0]
    expected = (
        preparation_blob[:start] + signed.encode("utf-8") + preparation_blob[end:]
    )
    if signing_blob != expected:
        raise ValueError("signed document changed outside the exact status transform")


def _parse_signing_literal_module(
    raw: bytes,
) -> tuple[ast.Module, tuple[ast.AnnAssign, ...]]:
    if type(raw) is not bytes:
        raise TypeError("signing literals source must be exact bytes")
    if len(raw) > _MAX_INERT_PYTHON_SOURCE_BYTES:
        raise ValueError("signing literals source exceeds the 1 MiB cap")
    if b"\r" in raw or not raw.endswith(b"\n"):
        raise ValueError("signing literals source must use canonical LF framing")
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("signing literals source is not strict UTF-8") from exc
    if source.startswith("\ufeff"):
        raise ValueError("signing literals source contains a BOM")
    try:
        module = ast.parse(source, filename=_PARENT_V3_SIGNING_LITERALS_PATH)
    except SyntaxError as exc:
        raise ValueError("signing literals source is invalid Python") from exc
    if len(module.body) != len(_SIGNING_LITERAL_SPECS) + 1:
        raise ValueError("signing literal module statement shape drifted")
    future, *raw_assignments = module.body
    if (
        type(future) is not ast.ImportFrom
        or future.module != "__future__"
        or future.level != 0
        or tuple((item.name, item.asname) for item in future.names)
        != (("annotations", None),)
    ):
        raise ValueError("signing literal future import drifted")
    if any(type(statement) is not ast.AnnAssign for statement in raw_assignments):
        raise ValueError("signing literal module contains executable statements")
    assignments = tuple(raw_assignments)
    for assignment, (name, annotation_source, _placeholder) in zip(
        assignments, _SIGNING_LITERAL_SPECS
    ):
        if (
            assignment.simple != 1
            or type(assignment.target) is not ast.Name
            or assignment.target.id != name
            or assignment.value is None
        ):
            raise ValueError("signing literal declaration name/order drifted")
        expected_annotation = ast.parse(annotation_source, mode="eval").body
        if ast.dump(assignment.annotation, include_attributes=False) != ast.dump(
            expected_annotation, include_attributes=False
        ):
            raise ValueError("signing literal annotation drifted")
    return module, assignments


def _literal_value(assignment: ast.AnnAssign, field: str) -> object:
    try:
        return ast.literal_eval(assignment.value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is not one inert literal") from exc


def _value_spans(
    raw: bytes, assignments: tuple[ast.AnnAssign, ...]
) -> tuple[tuple[int, int], ...]:
    source = raw.decode("utf-8")
    source_lines = source.splitlines(keepends=True)
    line_byte_offsets = [0]
    for line in source_lines:
        line_byte_offsets.append(line_byte_offsets[-1] + len(line.encode("utf-8")))

    def byte_offset(position: tuple[int, int]) -> int:
        row, column = position
        if row <= 0 or row > len(source_lines):
            raise ValueError("signing literal token row is out of range")
        return line_byte_offsets[row - 1] + len(
            source_lines[row - 1][:column].encode("utf-8")
        )

    try:
        tokens = tuple(tokenize.generate_tokens(io.StringIO(source).readline))
    except (IndentationError, tokenize.TokenError) as exc:
        raise ValueError("signing literals token stream is invalid") from exc
    spans: list[tuple[int, int]] = []
    for assignment in assignments:
        assert isinstance(assignment.target, ast.Name)
        name = assignment.target.id
        name_index = next(
            (
                index
                for index, token in enumerate(tokens)
                if token.type == tokenize.NAME
                and token.string == name
                and token.start[0] == assignment.lineno
                and token.start[1] == 0
            ),
            None,
        )
        if name_index is None:
            raise ValueError("signing literal target token is missing")
        equals_index = next(
            (
                index
                for index in range(name_index + 1, len(tokens))
                if tokens[index].type == tokenize.OP and tokens[index].string == "="
            ),
            None,
        )
        if equals_index is None:
            raise ValueError("signing literal assignment token is missing")
        significant = []
        nesting = 0
        for token in tokens[equals_index + 1 :]:
            if token.type == tokenize.OP and token.string in "([{":
                nesting += 1
            elif token.type == tokenize.OP and token.string in ")]}":
                nesting -= 1
                if nesting < 0:
                    raise ValueError("signing literal RHS delimiters drifted")
            if token.type == tokenize.NEWLINE and nesting == 0:
                break
            if token.type not in (
                tokenize.NL,
                tokenize.COMMENT,
                tokenize.INDENT,
                tokenize.DEDENT,
            ):
                significant.append(token)
        if not significant or nesting != 0:
            raise ValueError("signing literal RHS token span is incomplete")
        start = byte_offset(significant[0].start)
        end = byte_offset(significant[-1].end)
        if not 0 <= start < end <= len(raw):
            raise ValueError("signing literal RHS source span drifted")
        spans.append((start, end))
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise ValueError("signing literal RHS spans overlap")
    return tuple(spans)


def _normalized_signing_literal_ast(module: ast.Module) -> str:
    for statement in module.body:
        if type(statement) is ast.AnnAssign and isinstance(statement.target, ast.Name):
            if statement.target.id in {item[0] for item in _SIGNING_LITERAL_SPECS}:
                statement.value = ast.Constant(value="__PARENT_V3_SIGNING_RHS__")
    return ast.dump(module, include_attributes=False)


def _static_segments(
    raw: bytes, spans: tuple[tuple[int, int], ...]
) -> tuple[bytes, ...]:
    result: list[bytes] = []
    cursor = 0
    for start, end in spans:
        result.append(raw[cursor:start])
        cursor = end
    result.append(raw[cursor:])
    return tuple(result)


def _exact_pair_tuple(
    value: object, field: str, expected_length: int
) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple or len(value) != expected_length:
        raise TypeError(f"{field} must be an exact {expected_length}-entry tuple")
    result: list[tuple[str, str]] = []
    for index, entry in enumerate(value):
        if (
            type(entry) is not tuple
            or len(entry) != 2
            or any(type(item) is not str for item in entry)
        ):
            raise TypeError(f"{field}[{index}] must be an exact string pair")
        result.append(entry)
    return tuple(result)


def _audit_signing_literals_transform(
    preparation_blob: bytes,
    signing_blob: bytes,
    *,
    preparation_commit_sha: str,
    reviewed_candidate_sha: str,
    reviewed_path_closure_sha: str,
    signed_source_sha256_by_path: tuple[tuple[str, str], ...],
    review_receipt_sha256_by_role: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    """Prove that only the five frozen annotated RHS spans changed."""

    if _LOWER_GIT_SHA1.fullmatch(preparation_commit_sha) is None:
        raise ValueError("preparation commit is not a lowercase Git SHA-1")
    if (
        re.fullmatch(r"[0-9a-f]{64}", reviewed_candidate_sha) is None
        or re.fullmatch(r"[0-9a-f]{64}", reviewed_path_closure_sha) is None
    ):
        raise ValueError("reviewed roots are not lowercase SHA-256 values")
    source_items = _exact_pair_tuple(
        signed_source_sha256_by_path,
        "signed_source_sha256_by_path",
        len(_MANDATORY_STATUS_TRANSFORMS_BY_PATH),
    )
    receipt_items = _exact_pair_tuple(
        review_receipt_sha256_by_role,
        "review_receipt_sha256_by_role",
        2,
    )
    old_module, old_assignments = _parse_signing_literal_module(preparation_blob)
    new_module, new_assignments = _parse_signing_literal_module(signing_blob)
    old_values = tuple(
        _literal_value(assignment, name)
        for assignment, (name, _annotation, _placeholder) in zip(
            old_assignments, _SIGNING_LITERAL_SPECS
        )
    )
    if old_values != tuple(item[2] for item in _SIGNING_LITERAL_SPECS):
        raise ValueError("preparation signing literals are not exact placeholders")
    expected_values = (
        preparation_commit_sha,
        reviewed_candidate_sha,
        reviewed_path_closure_sha,
        source_items,
        receipt_items,
    )
    new_values = tuple(
        _literal_value(assignment, name)
        for assignment, (name, _annotation, _placeholder) in zip(
            new_assignments, _SIGNING_LITERAL_SPECS
        )
    )
    if new_values != expected_values:
        raise ValueError("signing literal RHS values do not match audited roots")
    if any(
        type(value) is not expected_type
        for value, expected_type in zip(new_values[:3], (str, str, str))
    ):
        raise TypeError("scalar signing literals must be exact strings")
    if _normalized_signing_literal_ast(old_module) != _normalized_signing_literal_ast(
        new_module
    ):
        raise ValueError("signing literals AST changed outside frozen RHS values")
    old_spans = _value_spans(preparation_blob, old_assignments)
    new_spans = _value_spans(signing_blob, new_assignments)
    if _static_segments(preparation_blob, old_spans) != _static_segments(
        signing_blob, new_spans
    ):
        raise ValueError("signing literal bytes changed outside frozen RHS spans")
    return {
        name: value
        for (name, _annotation, _placeholder), value in zip(
            _SIGNING_LITERAL_SPECS, new_values
        )
    }


_issue_private_parent_signing_audit, _require_private_audit_snapshot, _ = (
    _make_private_audit_registry(
        validator=_validate_signing_audit_bundle,
        seal_builder=_signing_audit_bundle_seal,
    )
)


def _audit_current_parent_v3_signing_commits() -> _VerifiedParentSigningAuditV1:
    bundle = _audit_repository_signing_bundle(
        _REPOSITORY_ROOT,
        candidate_replayer=(
            _replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit
        ),
        candidate_verifier=verify_parent_freeze_candidate_v3,
    )
    return _issue_private_parent_signing_audit(bundle)


def _require_private_parent_signing_audit(
    capability: _VerifiedParentSigningAuditV1,
) -> _ParentV3SigningAuditBundle:
    snapshot = _require_private_audit_snapshot(capability)
    if type(snapshot) is not _ParentV3SigningAuditBundle:
        raise TypeError("private signing-audit registry returned the wrong body")
    return snapshot


__all__: tuple[str, ...] = ()
