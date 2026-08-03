"""Execute the B7 D0 schema lab from immutable Git inputs.

The executable intentionally owns only orchestration.  Scientific domains,
route capture and every D0 decision remain owned by ``compare.py`` and
``common.py``.  Git source bytes are read through the literal trusted Git
entrypoint before either lab module is imported.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import tracemalloc
from types import ModuleType


_TRUSTED_GIT_V1 = "/usr/bin/git"
_TRUSTED_GIT_GLOBAL_ARGUMENTS_V1 = (
    "--no-replace-objects",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "diff.external=",
    "-c",
    "core.attributesFile=/dev/null",
)
_TRUSTED_GIT_ENVIRONMENT_V1 = {
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES": "",
    "LANG": "C",
    "LC_ALL": "C",
}
_GIT_TIMEOUT_SECONDS_V1 = 30.0
_GIT_STDOUT_LIMIT_V1 = 64 << 20
_GIT_STDERR_LIMIT_V1 = 1 << 20

_COMMON_SOURCE_PATH_V1 = "experiments/v3m0_b7_schema_lab/common.py"
_COMPARE_SOURCE_PATH_V1 = "experiments/v3m0_b7_schema_lab/compare.py"
_LAB_INITIALIZER_PATH_V1 = "experiments/v3m0_b7_schema_lab/__init__.py"
_PRODUCTION_ROOTS_V1 = ("rulespace_v3", "rulespace_gpu")
_ROUTE_SPECS_V1 = (
    (
        "A_FLAT",
        "experimental.v3m0.b7.a-flat",
        "experiments.v3m0_b7_schema_lab.a_flat",
        "experiments/v3m0_b7_schema_lab/a_flat.py",
        "experimental.v3m0.b7.a-flat.wire.v1",
    ),
    (
        "B_PROGRESS",
        "experimental.v3m0.b7.b-progress",
        "experiments.v3m0_b7_schema_lab.b_progress",
        "experiments/v3m0_b7_schema_lab/b_progress.py",
        "experimental.v3m0.b7.b-progress.wire.v1",
    ),
    (
        "C_UNION",
        "experimental.v3m0.b7.c-union",
        "experiments.v3m0_b7_schema_lab.c_union",
        "experiments/v3m0_b7_schema_lab/c_union.py",
        "experimental.v3m0.b7.c-union.wire.v1",
    ),
)
_FIXTURE_RELATIVE_PATH_V1 = Path("tests/fixtures/v3m0_b7_schema_lab_corpus.json")
_D0_RESULT_RELATIVE_PATH_V1 = Path(
    "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json"
)
_SUMMARY_FIELDS_V1 = (
    "d0_result_raw_sha256",
    "d0_result_sha",
    "surviving_route_ids",
)


def _modules_v1():
    from experiments.v3m0_b7_schema_lab import common, compare

    return common, compare


def _prepare_single_experiments_namespace_v1(repository_root: Path) -> None:
    """Avoid executing the unrelated repository-root experiments initializer."""

    root = Path(repository_root).resolve(strict=True)
    experiments_root = root / "experiments"
    if not experiments_root.is_dir():
        raise ValueError("repository experiments namespace is absent")
    existing = sys.modules.get("experiments")
    if existing is not None:
        existing_paths = getattr(existing, "__path__", None)
        if existing_paths is None or tuple(
            Path(path).resolve() for path in existing_paths
        ) != (experiments_root.resolve(),):
            raise RuntimeError(
                "experiments namespace was imported before D0 source checks"
            )
        return
    namespace = ModuleType("experiments")
    namespace.__package__ = "experiments"
    namespace.__path__ = [str(experiments_root)]
    namespace.__file__ = None
    sys.modules["experiments"] = namespace
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def _require_git_sha_v1(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be an exact lowercase Git SHA-1")
    return value


def _verify_trusted_git_v1() -> None:
    try:
        metadata = os.lstat(_TRUSTED_GIT_V1)
    except OSError as exc:
        raise RuntimeError("literal trusted Git is unavailable") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_mode & 0o022
        or metadata.st_mode & 0o111 == 0
    ):
        raise RuntimeError("literal trusted Git identity or permissions drifted")


def _run_git_v1(
    repository_root: Path,
    *arguments: str,
    allowed_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    _verify_trusted_git_v1()
    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository root must be a directory")
    if not arguments or any(
        type(argument) is not str or "\0" in argument for argument in arguments
    ):
        raise TypeError("Git arguments must be exact NUL-free strings")
    try:
        completed = subprocess.run(
            (
                _TRUSTED_GIT_V1,
                *_TRUSTED_GIT_GLOBAL_ARGUMENTS_V1,
                *arguments,
            ),
            cwd=root,
            env=dict(_TRUSTED_GIT_ENVIRONMENT_V1),
            shell=False,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=_GIT_TIMEOUT_SECONDS_V1,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("trusted Git invocation did not complete") from exc
    if (
        len(completed.stdout) > _GIT_STDOUT_LIMIT_V1
        or len(completed.stderr) > _GIT_STDERR_LIMIT_V1
    ):
        raise ValueError("trusted Git output exceeded its hard cap")
    if completed.returncode not in allowed_returncodes:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise ValueError(
            f"trusted Git rejected {arguments[0]}" + (f": {detail}" if detail else "")
        )
    return completed


def _decode_one_line_v1(raw_bytes: bytes, field: str) -> str:
    if not raw_bytes.endswith(b"\n") or b"\n" in raw_bytes[:-1]:
        raise ValueError(f"{field} output framing drifted")
    try:
        value = raw_bytes[:-1].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{field} output is not UTF-8") from exc
    if not value or "\0" in value:
        raise ValueError(f"{field} output is empty or contains NUL")
    return value


def _guard_repository_object_sources_v1(repository_root: Path) -> None:
    raw = _run_git_v1(repository_root, "rev-parse", "--git-common-dir").stdout
    common_dir_text = _decode_one_line_v1(raw, "Git common directory")
    common_dir = Path(common_dir_text)
    if not common_dir.is_absolute():
        common_dir = Path(repository_root).resolve(strict=True) / common_dir
    common_dir = common_dir.resolve(strict=True)
    if not common_dir.is_dir():
        raise ValueError("Git common directory is not a directory")
    for relative in (Path("objects/info/alternates"), Path("info/grafts")):
        try:
            os.lstat(common_dir / relative)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ValueError(
                "Git object indirection guard could not be observed"
            ) from exc
        raise ValueError(f"forbidden Git object indirection exists: {relative}")


def _require_commit_v1(repository_root: Path, commit_sha: str, field: str) -> None:
    _require_git_sha_v1(commit_sha, field)
    object_type = _decode_one_line_v1(
        _run_git_v1(repository_root, "cat-file", "-t", commit_sha).stdout,
        field,
    )
    if object_type != "commit":
        raise ValueError(f"{field} is not a Git commit")


def _is_ancestor_v1(repository_root: Path, ancestor: str, descendant: str) -> bool:
    completed = _run_git_v1(
        repository_root,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        allowed_returncodes=(0, 1),
    )
    return completed.returncode == 0


def _parse_tree_entry_v1(raw_record: bytes, expected_path: str | None = None):
    if not raw_record or raw_record.endswith(b"\n"):
        raise ValueError("Git tree entry framing drifted")
    try:
        header, path_bytes = raw_record.split(b"\t", 1)
        mode_bytes, type_bytes, oid_bytes = header.split(b" ")
        mode = mode_bytes.decode("ascii")
        object_type = type_bytes.decode("ascii")
        oid = oid_bytes.decode("ascii")
        path = path_bytes.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("Git tree entry could not be decoded exactly") from exc
    _require_git_sha_v1(oid, "Git blob object ID")
    if object_type != "blob" or mode != "100644":
        raise ValueError("Git source entry must be one mode-100644 blob")
    canonical = Path(path)
    if (
        not path
        or canonical.is_absolute()
        or canonical.as_posix() != path
        or "." in canonical.parts
        or ".." in canonical.parts
    ):
        raise ValueError("Git source path is not canonical repository-relative POSIX")
    if expected_path is not None and path != expected_path:
        raise ValueError("Git tree entry path differs from its literal request")
    return mode, oid, path


def _read_blob_v1(repository_root: Path, commit_sha: str, path: str):
    listing = _run_git_v1(
        repository_root,
        "ls-tree",
        "-z",
        commit_sha,
        "--",
        path,
    ).stdout
    records = listing.split(b"\0")
    if not listing.endswith(b"\0") or len(records) != 2 or records[-1] != b"":
        raise ValueError(f"Git source path is absent or ambiguous: {path}")
    mode, object_id, observed_path = _parse_tree_entry_v1(records[0], path)
    raw_bytes = _run_git_v1(
        repository_root,
        "cat-file",
        "blob",
        f"{commit_sha}:{path}",
    ).stdout
    expected_object_id = hashlib.sha1(
        b"blob " + str(len(raw_bytes)).encode("ascii") + b"\0" + raw_bytes
    ).hexdigest()
    if expected_object_id != object_id:
        raise ValueError("Git blob bytes differ from their tree object ID")
    return commit_sha, observed_path, mode, raw_bytes


def _read_recursive_blobs_v1(repository_root: Path, commit_sha: str):
    blobs = []
    observed_paths: set[str] = set()
    for root in _PRODUCTION_ROOTS_V1:
        listing = _run_git_v1(
            repository_root,
            "ls-tree",
            "-r",
            "-z",
            commit_sha,
            "--",
            root,
        ).stdout
        if not listing.endswith(b"\0"):
            raise ValueError(f"production root is absent: {root}")
        records = listing[:-1].split(b"\0") if listing[:-1] else []
        if not records:
            raise ValueError(f"production root is empty: {root}")
        root_blobs = []
        for record in records:
            _mode, _oid, path = _parse_tree_entry_v1(record)
            if not path.startswith(root + "/") or path in observed_paths:
                raise ValueError("recursive production tree path drifted")
            observed_paths.add(path)
            root_blobs.append(_read_blob_v1(repository_root, commit_sha, path))
        expected_order = sorted(root_blobs, key=lambda blob: blob[1].encode("utf-8"))
        if root_blobs != expected_order:
            raise ValueError("recursive production tree order drifted")
        blobs.extend(root_blobs)
    return tuple(blobs)


def _same_blob_body_v1(left, right) -> bool:
    return left[1:] == right[1:]


def _verify_worktree_blob_v1(repository_root: Path, blob, field: str) -> None:
    path = Path(repository_root).resolve(strict=True) / blob[1]
    raw_bytes = _read_stable_regular_file_v1(path, field)
    if raw_bytes != blob[3]:
        raise ValueError(f"worktree {field} differs from its frozen Git blob")


def _read_git_inputs_v1(
    *,
    repository_root: Path,
    common_commit_sha: str,
    ordered_route_commit_shas: tuple[str, str, str],
):
    """Read C and three route origins and prove HEAD executes those bytes."""

    root = Path(repository_root).resolve(strict=True)
    common_sha = _require_git_sha_v1(common_commit_sha, "common commit C")
    if (
        type(ordered_route_commit_shas) is not tuple
        or len(ordered_route_commit_shas) != 3
    ):
        raise TypeError("exactly three ordered route commit SHAs are required")
    route_shas = tuple(
        _require_git_sha_v1(value, f"route commit {ordinal}")
        for ordinal, value in enumerate(ordered_route_commit_shas)
    )
    if len(set((common_sha, *route_shas))) != 4:
        raise ValueError("common and route commits must be four distinct origins")

    _guard_repository_object_sources_v1(root)
    _require_commit_v1(root, common_sha, "common commit C")
    for ordinal, route_sha in enumerate(route_shas):
        _require_commit_v1(root, route_sha, f"route commit {ordinal}")
    head_sha = _require_git_sha_v1(
        _decode_one_line_v1(
            _run_git_v1(root, "rev-parse", "--verify", "HEAD^{commit}").stdout,
            "HEAD commit",
        ),
        "HEAD commit",
    )
    _require_commit_v1(root, head_sha, "HEAD commit")
    for ordinal, route_sha in enumerate(route_shas):
        if not _is_ancestor_v1(root, common_sha, route_sha):
            raise ValueError(f"common C is not an ancestor of route commit {ordinal}")
        if not _is_ancestor_v1(root, route_sha, head_sha):
            raise ValueError(f"route commit {ordinal} is not an ancestor of HEAD")

    common_blob = _read_blob_v1(root, common_sha, _COMMON_SOURCE_PATH_V1)
    compare_blob = _read_blob_v1(root, common_sha, _COMPARE_SOURCE_PATH_V1)
    lab_initializer_blob = _read_blob_v1(root, common_sha, _LAB_INITIALIZER_PATH_V1)
    production_blobs = _read_recursive_blobs_v1(root, common_sha)
    ordered_route_blobs = tuple(
        _read_blob_v1(root, route_sha, spec[3])
        for route_sha, spec in zip(route_shas, _ROUTE_SPECS_V1)
    )

    head_common = _read_blob_v1(root, head_sha, _COMMON_SOURCE_PATH_V1)
    head_compare = _read_blob_v1(root, head_sha, _COMPARE_SOURCE_PATH_V1)
    head_lab_initializer = _read_blob_v1(root, head_sha, _LAB_INITIALIZER_PATH_V1)
    if not _same_blob_body_v1(common_blob, head_common):
        raise ValueError("HEAD common source differs from frozen common C")
    if not _same_blob_body_v1(compare_blob, head_compare):
        raise ValueError("HEAD compare source differs from frozen common C")
    if not _same_blob_body_v1(lab_initializer_blob, head_lab_initializer):
        raise ValueError("HEAD lab initializer differs from frozen common C")
    for route_blob, spec in zip(ordered_route_blobs, _ROUTE_SPECS_V1):
        head_route = _read_blob_v1(root, head_sha, spec[3])
        if not _same_blob_body_v1(route_blob, head_route):
            raise ValueError(f"HEAD route source differs from frozen {spec[0]} origin")
    head_production = _read_recursive_blobs_v1(root, head_sha)
    if [blob[1:] for blob in production_blobs] != [
        blob[1:] for blob in head_production
    ]:
        raise ValueError("HEAD production source closure differs from frozen common C")

    for blob, field in (
        (common_blob, "common source"),
        (compare_blob, "compare source"),
        (lab_initializer_blob, "lab initializer"),
        *(
            (blob, f"route source {spec[0]}")
            for blob, spec in zip(ordered_route_blobs, _ROUTE_SPECS_V1)
        ),
        *((blob, f"production source {blob[1]}") for blob in production_blobs),
    ):
        _verify_worktree_blob_v1(root, blob, field)

    return {
        "head_commit_sha": head_sha,
        "common_blob": common_blob,
        "compare_blob": compare_blob,
        "lab_initializer_blob": lab_initializer_blob,
        "production_blobs": production_blobs,
        "ordered_route_blobs": ordered_route_blobs,
    }


def _read_stable_regular_file_v1(path: Path, field: str) -> bytes:
    try:
        initial = os.lstat(path)
    except OSError as exc:
        raise ValueError(f"{field} is unavailable") from exc
    if stat.S_ISLNK(initial.st_mode) or not stat.S_ISREG(initial.st_mode):
        raise ValueError(f"{field} must be a nonsymlink regular file")
    descriptor = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        before = os.fstat(descriptor)
        identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if not stat.S_ISREG(before.st_mode) or before.st_size > _GIT_STDOUT_LIMIT_V1:
            raise ValueError(f"{field} size or type drifted")
        chunks = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1 << 20, remaining))
            if not chunk:
                raise ValueError(f"{field} ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise ValueError(f"{field} grew while being read")
        after = os.fstat(descriptor)
        if identity != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError(f"{field} changed while being read")
        return b"".join(chunks)
    except OSError as exc:
        raise ValueError(f"{field} could not be read without following links") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_fixture_v1(repository_root: Path):
    common, _compare = _modules_v1()
    raw_bytes = _read_stable_regular_file_v1(
        Path(repository_root).resolve(strict=True) / _FIXTURE_RELATIVE_PATH_V1,
        "fixed B7 corpus fixture",
    )
    if not raw_bytes.endswith(b"\n") or not raw_bytes[:-1]:
        raise ValueError("fixed B7 corpus fixture framing drifted")
    parsed = common.strict_json_loads_v1(raw_bytes)
    if (
        type(parsed) is not dict
        or common.canonical_json_bytes_v1(parsed) + b"\n" != raw_bytes
    ):
        raise ValueError("fixed B7 corpus fixture is not canonical JSON plus one LF")
    return raw_bytes, parsed


def _observe_fixture_environment_v1(fixture, python_invocation_path: str):
    _common, compare = _modules_v1()
    if (
        type(fixture) is not dict
        or type(fixture.get("environment_manifest")) is not dict
    ):
        raise TypeError("fixture environment manifest is absent")
    manifest = fixture["environment_manifest"]
    if manifest.get("python_invocation_path") != python_invocation_path:
        raise ValueError("executor Python invocation differs from frozen fixture")
    identity = compare.precheck_python_invocation_identity_v2(
        python_invocation_path=manifest["python_invocation_path"],
        recorded_realpath=manifest["python_executable_realpath"],
        recorded_raw_sha256=manifest["python_executable_raw_sha256"],
        recorded_venv_prefix=manifest["python_venv_prefix"],
        recorded_pyvenv_cfg_path=manifest["python_pyvenv_cfg_path"],
        recorded_pyvenv_cfg_raw_sha256=manifest["python_pyvenv_cfg_raw_sha256"],
    )
    if identity.get("precheck_passed") is not True:
        raise ValueError("executor Python identity precheck failed")
    probe = compare.run_python_environment_import_probe_v2(
        python_invocation_path=manifest["python_invocation_path"],
        python_identity_observation=identity,
    )
    if probe.get("probe_passed") is not True:
        raise ValueError("executor Python environment import probe failed")
    return identity, probe


def _route_spec_v1(route_id: str):
    matches = [spec for spec in _ROUTE_SPECS_V1 if spec[0] == route_id]
    if len(matches) != 1:
        raise ValueError("route ID is outside the frozen D0 order")
    return matches[0]


def _build_route_manifest_v1(
    *,
    route_id: str,
    common_blob,
    compare_blob,
    route_blob,
    production_blobs,
    validated_corpus_fixture,
):
    common, _compare = _modules_v1()
    spec = _route_spec_v1(route_id)
    static_fields = common._compute_route_static_fields_v1(
        route_id,
        common_blob[0],
        route_blob,
        production_blobs,
    )
    manifest = {
        "route_manifest_schema_version": "experimental.v3m0.b7.route-manifest.v1",
        "route_id": route_id,
        "route_schema_domain": spec[1],
        "route_module": spec[2],
        "route_source_path": spec[3],
        "wire_schema_id": spec[4],
        "route_commit_sha": route_blob[0],
        "route_source_sha256": static_fields["route_source_sha256"],
        "common_commit_sha": common_blob[0],
        "common_source_sha256": hashlib.sha256(common_blob[3]).hexdigest(),
        "compare_source_sha256": hashlib.sha256(compare_blob[3]).hexdigest(),
        "corpus_spec_sha": validated_corpus_fixture["corpus_spec"]["corpus_spec_sha"],
        "mutation_universe_sha": validated_corpus_fixture["mutation_universe"][
            "mutation_universe_sha"
        ],
        "metric_spec_sha": validated_corpus_fixture["metric_spec"]["metric_spec_sha"],
        "encoder_symbol": "encode_normalized_transcript",
        "verifier_decoder_symbol": "verify_and_decode_route_wire",
        "input_schema_version": "experimental.v3m0.b7.normalized-transcript.v1",
        "output_schema_version": spec[4],
        "static_api_scan_sha": static_fields["static_api_scan_sha"],
        "static_import_scan_sha": static_fields["static_import_scan_sha"],
        "static_authority_surface_scan_sha": static_fields[
            "static_authority_surface_scan_sha"
        ],
        "production_import_scan_sha": static_fields["production_import_scan_sha"],
        "production_imported_by_route": static_fields["production_imported_by_route"],
        "route_imported_by_production": static_fields["route_imported_by_production"],
        "authority_surface_count": static_fields["authority_surface_count"],
        "wrapper_surface_count": static_fields["wrapper_surface_count"],
        "route_manifest_sha": "",
    }
    manifest["route_manifest_sha"] = common.canonical_sha_v1(
        {
            field: value
            for field, value in manifest.items()
            if field != "route_manifest_sha"
        }
    )
    common.validate_exact_lab_record_v1("B7LabRouteManifestV1", manifest)
    validated = common.validate_route_static_surface_v1(
        manifest,
        route_blob,
        production_blobs,
    )
    if common.canonical_json_bytes_v1(validated) != common.canonical_json_bytes_v1(
        manifest
    ):
        raise ValueError("route static validator substituted its manifest")
    return manifest


def _measure_route_batch_v1(
    route_id: str,
    ordered_source_bytes: tuple[bytes, ...],
) -> tuple[float, int]:
    _common, compare = _modules_v1()
    if tracemalloc.is_tracing():
        raise RuntimeError(
            "D0 auxiliary benchmark requires exclusive tracemalloc ownership"
        )
    tracemalloc.start()
    try:
        started = time.perf_counter()
        for source_bytes in ordered_source_bytes:
            compare._call_d0_route_pipeline_v1(route_id, source_bytes)
        elapsed = time.perf_counter() - started
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if elapsed < 0.0 or peak < 0:
        raise RuntimeError("D0 auxiliary benchmark clock or memory counter regressed")
    return float(elapsed), int(peak)


def _nearest_rank_p95_v1(samples: list[float]) -> float:
    if len(samples) != 30 or any(
        type(sample) is not float or sample < 0.0 for sample in samples
    ):
        raise TypeError("D0 p95 requires exactly thirty nonnegative float samples")
    ordered = sorted(samples)
    return float(ordered[math.ceil(0.95 * len(ordered)) - 1])


def _build_auxiliary_benchmark_v1(validated_corpus_fixture):
    common, _compare = _modules_v1()
    transcripts = validated_corpus_fixture.get("ordered_d0_transcripts")
    if (
        type(transcripts) is not list
        or len(transcripts) != 7
        or any(type(transcript) is not dict for transcript in transcripts)
    ):
        raise TypeError("D0 benchmark requires the exact seven-transcript fixture")
    source_bytes = tuple(common.canonical_json_bytes_v1(item) for item in transcripts)
    statistics = []
    for route_id, *_rest in _ROUTE_SPECS_V1:
        for _ordinal in range(5):
            _measure_route_batch_v1(route_id, source_bytes)
        elapsed_samples = []
        peak_samples = []
        for _ordinal in range(30):
            elapsed, peak = _measure_route_batch_v1(route_id, source_bytes)
            elapsed_samples.append(elapsed)
            peak_samples.append(peak)
        ordered = sorted(elapsed_samples)
        statistics.append(
            {
                "route_id": route_id,
                "median": float((ordered[14] + ordered[15]) / 2.0),
                "p95": _nearest_rank_p95_v1(elapsed_samples),
                "tracemalloc_peak": max(peak_samples),
            }
        )
    benchmark = {
        "warm_up": 5,
        "repeat": 30,
        "reported_statistics": ["median", "p95", "tracemalloc_peak"],
        "ordered_route_statistics": statistics,
    }
    return common._validate_d0_auxiliary_benchmark_v1(benchmark)


def _new_ordered_route_inputs_v1(
    *,
    validated_corpus_fixture,
    ordered_route_manifests,
    ordered_route_blobs,
    production_blobs,
):
    _common, compare = _modules_v1()
    captures = list(
        compare.iter_d0_gate_inputs_v1(
            validated_corpus_fixture=validated_corpus_fixture
        )
    )
    if [route_id for route_id, _gate_inputs in captures] != [
        spec[0] for spec in _ROUTE_SPECS_V1
    ]:
        raise ValueError("D0 capture route order drifted")
    return [
        {
            "route_manifest": manifest,
            "route_blob": route_blob,
            "production_blobs": production_blobs,
            "gate_inputs": gate_inputs,
        }
        for manifest, route_blob, (_route_id, gate_inputs) in zip(
            ordered_route_manifests,
            ordered_route_blobs,
            captures,
        )
    ]


def _build_d0_result_v1(
    *,
    corpus_fixture_raw_bytes,
    validated_corpus_fixture,
    git_inputs,
    python_identity_observation,
    python_probe_result,
):
    common, _compare = _modules_v1()
    manifests = tuple(
        _build_route_manifest_v1(
            route_id=spec[0],
            common_blob=git_inputs["common_blob"],
            compare_blob=git_inputs["compare_blob"],
            route_blob=route_blob,
            production_blobs=git_inputs["production_blobs"],
            validated_corpus_fixture=validated_corpus_fixture,
        )
        for spec, route_blob in zip(
            _ROUTE_SPECS_V1,
            git_inputs["ordered_route_blobs"],
        )
    )
    benchmark = _build_auxiliary_benchmark_v1(validated_corpus_fixture)
    route_inputs = _new_ordered_route_inputs_v1(
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_route_manifests=manifests,
        ordered_route_blobs=git_inputs["ordered_route_blobs"],
        production_blobs=git_inputs["production_blobs"],
    )
    result = common.build_d0_comparison_v1(
        corpus_fixture_raw_bytes=corpus_fixture_raw_bytes,
        common_blob=git_inputs["common_blob"],
        compare_blob=git_inputs["compare_blob"],
        python_identity_observation=python_identity_observation,
        python_probe_result=python_probe_result,
        ordered_route_inputs=route_inputs,
        auxiliary_benchmark=benchmark,
    )
    replay_inputs = _new_ordered_route_inputs_v1(
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_route_manifests=manifests,
        ordered_route_blobs=git_inputs["ordered_route_blobs"],
        production_blobs=git_inputs["production_blobs"],
    )
    validated = common.validate_d0_comparison_v1(
        result,
        corpus_fixture_raw_bytes=corpus_fixture_raw_bytes,
        common_blob=git_inputs["common_blob"],
        compare_blob=git_inputs["compare_blob"],
        python_identity_observation=python_identity_observation,
        python_probe_result=python_probe_result,
        ordered_route_inputs=replay_inputs,
    )
    if common.canonical_json_bytes_v1(validated) != common.canonical_json_bytes_v1(
        result
    ):
        raise ValueError("D0 fresh replay substituted the built result")
    return result


def _fsync_directory_v1(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_result_parent_v1(root: Path) -> Path:
    current = root
    for component in _D0_RESULT_RELATIVE_PATH_V1.parts[:-1]:
        candidate = current / component
        try:
            observed = os.lstat(candidate)
        except FileNotFoundError:
            try:
                os.mkdir(candidate, 0o755)
            except FileExistsError:
                pass
            else:
                _fsync_directory_v1(current)
            observed = os.lstat(candidate)
        if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
            raise ValueError(
                "fixed D0 result parent must contain only real directories"
            )
        current = candidate
    return current


def _materialize_d0_result_v1(*, repository_root: Path, d0_result):
    """Create only the canonical D0 path; identical bytes are idempotent."""

    common, _compare = _modules_v1()
    if type(d0_result) is not dict:
        raise TypeError("D0 result must be an exact object")
    d0_result_sha = d0_result.get("d0_result_sha")
    survivors = d0_result.get("surviving_route_ids")
    if (
        type(d0_result_sha) is not str
        or len(d0_result_sha) != 64
        or any(character not in "0123456789abcdef" for character in d0_result_sha)
        or type(survivors) is not list
        or any(type(route_id) is not str for route_id in survivors)
    ):
        raise ValueError("D0 result summary fields are malformed")
    raw_bytes = common.canonical_json_bytes_v1(d0_result) + b"\n"
    summary = {
        "d0_result_raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "d0_result_sha": d0_result_sha,
        "surviving_route_ids": list(survivors),
    }
    root = Path(repository_root).resolve(strict=True)
    parent = _ensure_result_parent_v1(root)
    target = parent / _D0_RESULT_RELATIVE_PATH_V1.name
    try:
        existing = _read_stable_regular_file_v1(target, "fixed D0 result")
    except ValueError:
        try:
            os.lstat(target)
        except FileNotFoundError:
            existing = None
        else:
            raise
    if existing is not None:
        if existing != raw_bytes:
            raise FileExistsError("fixed D0 result already exists with different bytes")
        return summary

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".v3m0-b7-d0-",
        suffix=".tmp",
        dir=parent,
    )
    temporary = Path(temporary_name)
    linked = False
    try:
        os.fchmod(descriptor, 0o444)
        view = memoryview(raw_bytes)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written:])
            if count <= 0:
                raise OSError("D0 temporary write made no progress")
            written += count
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, target, follow_symlinks=False)
            linked = True
        except FileExistsError:
            raced = _read_stable_regular_file_v1(target, "fixed D0 result")
            if raced != raw_bytes:
                raise FileExistsError(
                    "fixed D0 result raced with different bytes"
                ) from None
        if linked:
            _fsync_directory_v1(parent)
        os.unlink(temporary)
        _fsync_directory_v1(parent)
        if _read_stable_regular_file_v1(target, "fixed D0 result") != raw_bytes:
            raise ValueError("published D0 result bytes changed")
        return summary
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def execute_d0_v1(
    *,
    repository_root: Path,
    python_invocation_path: str,
    common_commit_sha: str,
    ordered_route_commit_shas: tuple[str, str, str],
):
    """Run one complete D0 build/replay and create only its fixed artifact."""

    root = Path(repository_root).resolve(strict=True)
    git_inputs = _read_git_inputs_v1(
        repository_root=root,
        common_commit_sha=common_commit_sha,
        ordered_route_commit_shas=ordered_route_commit_shas,
    )
    _prepare_single_experiments_namespace_v1(root)
    common, _compare = _modules_v1()
    fixture_raw_bytes, fixture = _read_fixture_v1(root)
    identity, probe = _observe_fixture_environment_v1(
        fixture,
        python_invocation_path,
    )
    validated_fixture = common.validate_corpus_fixture_v2(
        fixture,
        git_inputs["common_blob"][3],
        git_inputs["compare_blob"][3],
        python_identity_observation=identity,
        python_probe_result=probe,
    )
    if common.canonical_json_bytes_v1(
        validated_fixture
    ) != common.canonical_json_bytes_v1(fixture):
        raise ValueError("fixture validator substituted the execution corpus")
    result = _build_d0_result_v1(
        corpus_fixture_raw_bytes=fixture_raw_bytes,
        validated_corpus_fixture=validated_fixture,
        git_inputs=git_inputs,
        python_identity_observation=identity,
        python_probe_result=probe,
    )
    return _materialize_d0_result_v1(repository_root=root, d0_result=result)


def render_summary_v1(summary) -> bytes:
    common, _compare = _modules_v1()
    if type(summary) is not dict or tuple(summary) != _SUMMARY_FIELDS_V1:
        raise ValueError("D0 execution summary fields or order drifted")
    for field in ("d0_result_raw_sha256", "d0_result_sha"):
        value = summary[field]
        if (
            type(value) is not str
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError(f"D0 execution summary {field} is malformed")
    if type(summary["surviving_route_ids"]) is not list:
        raise TypeError("D0 execution summary survivors must be an exact list")
    return common.canonical_json_bytes_v1(summary) + b"\n"


def _argument_parser_v1() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "从显式 common/三路线 Git commit 执行 B7 D0，并仅新建固定 canonical 结果。"
        )
    )
    parser.add_argument(
        "--repository-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--python-invocation-path", default=sys.executable)
    parser.add_argument("--common-commit-sha", required=True)
    parser.add_argument("--a-flat-commit-sha", required=True)
    parser.add_argument("--b-progress-commit-sha", required=True)
    parser.add_argument("--c-union-commit-sha", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _argument_parser_v1().parse_args(argv)
    summary = execute_d0_v1(
        repository_root=Path(arguments.repository_root),
        python_invocation_path=arguments.python_invocation_path,
        common_commit_sha=arguments.common_commit_sha,
        ordered_route_commit_shas=(
            arguments.a_flat_commit_sha,
            arguments.b_progress_commit_sha,
            arguments.c_union_commit_sha,
        ),
    )
    sys.stdout.buffer.write(render_summary_v1(summary))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
