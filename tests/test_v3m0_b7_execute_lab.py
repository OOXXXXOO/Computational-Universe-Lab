"""Tests for the create-only B7 D0 lab executor."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

from experiments.v3m0_b7_schema_lab import common
from tools import v3m0_b7_execute_lab as execute


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("/usr/bin/git", *arguments),
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _write(repository: Path, relative_path: str, body: bytes) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", message)
    return _git(repository, "rev-parse", "HEAD")


def _lab_repository(tmp_path: Path) -> tuple[Path, str, tuple[str, str, str]]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "B7 Test")
    _git(repository, "config", "user.email", "b7@example.invalid")
    _write(
        repository,
        "experiments/v3m0_b7_schema_lab/common.py",
        b"COMMON = 1\n",
    )
    _write(
        repository,
        "experiments/v3m0_b7_schema_lab/compare.py",
        b"COMPARE = 1\n",
    )
    _write(repository, "experiments/v3m0_b7_schema_lab/__init__.py", b"")
    _write(repository, "tests/fixtures/v3m0_b7_schema_lab_corpus.json", b"{}\n")
    _write(repository, "rulespace_v3/core.py", b"CORE = 1\n")
    _write(repository, "rulespace_gpu/kernel.py", b"KERNEL = 1\n")
    common_commit = _commit(repository, "common")

    route_commits: list[str] = []
    for route_path, marker in (
        ("experiments/v3m0_b7_schema_lab/a_flat.py", b"A = 1\n"),
        ("experiments/v3m0_b7_schema_lab/b_progress.py", b"B = 1\n"),
        ("experiments/v3m0_b7_schema_lab/c_union.py", b"C = 1\n"),
    ):
        _write(repository, route_path, marker)
        route_commits.append(_commit(repository, route_path))
    return repository, common_commit, tuple(route_commits)  # type: ignore[return-value]


def test_git_bundle_reads_exact_commit_blobs_and_recursive_production_roots(
    tmp_path: Path,
) -> None:
    repository, common_commit, route_commits = _lab_repository(tmp_path)

    bundle = execute._read_git_inputs_v1(
        repository_root=repository,
        common_commit_sha=common_commit,
        ordered_route_commit_shas=route_commits,
    )

    assert bundle["head_commit_sha"] == route_commits[-1]
    assert bundle["common_blob"] == (
        common_commit,
        "experiments/v3m0_b7_schema_lab/common.py",
        "100644",
        b"COMMON = 1\n",
    )
    assert bundle["compare_blob"] == (
        common_commit,
        "experiments/v3m0_b7_schema_lab/compare.py",
        "100644",
        b"COMPARE = 1\n",
    )
    assert bundle["fixture_blob"] == (
        common_commit,
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
        "100644",
        b"{}\n",
    )
    assert [blob[1] for blob in bundle["production_blobs"]] == [
        "rulespace_v3/core.py",
        "rulespace_gpu/kernel.py",
    ]
    assert all(blob[0] == common_commit for blob in bundle["production_blobs"])
    assert [blob[:3] for blob in bundle["ordered_route_blobs"]] == [
        (
            route_commits[0],
            "experiments/v3m0_b7_schema_lab/a_flat.py",
            "100644",
        ),
        (
            route_commits[1],
            "experiments/v3m0_b7_schema_lab/b_progress.py",
            "100644",
        ),
        (
            route_commits[2],
            "experiments/v3m0_b7_schema_lab/c_union.py",
            "100644",
        ),
    ]


def test_git_bundle_rejects_route_not_reachable_from_head(tmp_path: Path) -> None:
    repository, common_commit, route_commits = _lab_repository(tmp_path)
    head = route_commits[-1]
    _git(repository, "checkout", "--detach", common_commit)
    _write(
        repository,
        "experiments/v3m0_b7_schema_lab/c_union.py",
        b"SIDE = 1\n",
    )
    side_route = _commit(repository, "side route")
    _git(repository, "checkout", "--detach", head)

    with pytest.raises(ValueError, match="HEAD"):
        execute._read_git_inputs_v1(
            repository_root=repository,
            common_commit_sha=common_commit,
            ordered_route_commit_shas=(
                route_commits[0],
                route_commits[1],
                side_route,
            ),
        )


def test_git_bundle_rejects_head_source_drift_after_route_commit(
    tmp_path: Path,
) -> None:
    repository, common_commit, route_commits = _lab_repository(tmp_path)
    _write(
        repository,
        "experiments/v3m0_b7_schema_lab/common.py",
        b"COMMON = 2\n",
    )
    _commit(repository, "drift common at head")

    with pytest.raises(ValueError, match="HEAD.*common|common.*HEAD"):
        execute._read_git_inputs_v1(
            repository_root=repository,
            common_commit_sha=common_commit,
            ordered_route_commit_shas=route_commits,
        )


def test_git_bundle_rejects_dirty_worktree_source_bytes(tmp_path: Path) -> None:
    repository, common_commit, route_commits = _lab_repository(tmp_path)
    _write(
        repository,
        "experiments/v3m0_b7_schema_lab/common.py",
        b"DIRTY = 1\n",
    )

    with pytest.raises(ValueError, match="worktree.*common"):
        execute._read_git_inputs_v1(
            repository_root=repository,
            common_commit_sha=common_commit,
            ordered_route_commit_shas=route_commits,
        )


def test_git_bundle_rejects_dirty_fixture_bytes(tmp_path: Path) -> None:
    repository, common_commit, route_commits = _lab_repository(tmp_path)
    _write(
        repository,
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
        b'{"dirty":true}\n',
    )

    with pytest.raises(ValueError, match="worktree.*fixture"):
        execute._read_git_inputs_v1(
            repository_root=repository,
            common_commit_sha=common_commit,
            ordered_route_commit_shas=route_commits,
        )


def test_git_bundle_rejects_head_fixture_drift(tmp_path: Path) -> None:
    repository, common_commit, route_commits = _lab_repository(tmp_path)
    _write(
        repository,
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
        b'{"head_drift":true}\n',
    )
    _commit(repository, "drift fixture at head")

    with pytest.raises(ValueError, match="HEAD fixture"):
        execute._read_git_inputs_v1(
            repository_root=repository,
            common_commit_sha=common_commit,
            ordered_route_commit_shas=route_commits,
        )


@pytest.mark.parametrize("module_name", execute._LAB_EXECUTION_MODULE_NAMES_V1)
def test_namespace_bootstrap_rejects_each_preloaded_lab_module(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
) -> None:
    for name in execute._LAB_EXECUTION_MODULE_NAMES_V1:
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setitem(sys.modules, module_name, ModuleType(module_name))

    with pytest.raises(RuntimeError, match=module_name):
        execute._prepare_single_experiments_namespace_v1(REPOSITORY_ROOT)


def test_git_bundle_rejects_symbolic_or_malformed_commit_identity(
    tmp_path: Path,
) -> None:
    repository, _common_commit, route_commits = _lab_repository(tmp_path)

    for hostile in ("HEAD", "A" * 40, "0" * 39, "../HEAD"):
        with pytest.raises((TypeError, ValueError)):
            execute._read_git_inputs_v1(
                repository_root=repository,
                common_commit_sha=hostile,
                ordered_route_commit_shas=route_commits,
            )


def test_route_manifest_is_derived_from_fixture_and_static_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    route_blob = (
        "a" * 40,
        "experiments/v3m0_b7_schema_lab/a_flat.py",
        "100644",
        b"ROUTE\n",
    )
    production_blobs = (
        ("b" * 40, "rulespace_v3/core.py", "100644", b"CORE\n"),
        ("b" * 40, "rulespace_gpu/kernel.py", "100644", b"GPU\n"),
    )
    fixture = {
        "corpus_spec": {"corpus_spec_sha": "c" * 64},
        "mutation_universe": {"mutation_universe_sha": "d" * 64},
        "metric_spec": {"metric_spec_sha": "e" * 64},
    }
    static_fields = {
        "route_source_sha256": hashlib.sha256(b"ROUTE\n").hexdigest(),
        "static_api_scan_sha": "1" * 64,
        "static_import_scan_sha": "2" * 64,
        "static_authority_surface_scan_sha": "3" * 64,
        "production_import_scan_sha": "4" * 64,
        "production_imported_by_route": False,
        "route_imported_by_production": False,
        "authority_surface_count": 0,
        "wrapper_surface_count": 0,
    }
    monkeypatch.setattr(
        common,
        "_compute_route_static_fields_v1",
        lambda *args: static_fields.copy(),
    )
    validated: list[dict[str, object]] = []

    def validate(manifest, observed_route_blob, observed_production_blobs):
        assert observed_route_blob == route_blob
        assert observed_production_blobs == production_blobs
        validated.append(manifest.copy())
        return manifest

    monkeypatch.setattr(common, "validate_route_static_surface_v1", validate)

    manifest = execute._build_route_manifest_v1(
        route_id="A_FLAT",
        common_blob=(
            "b" * 40,
            "experiments/v3m0_b7_schema_lab/common.py",
            "100644",
            b"COMMON\n",
        ),
        compare_blob=(
            "b" * 40,
            "experiments/v3m0_b7_schema_lab/compare.py",
            "100644",
            b"COMPARE\n",
        ),
        route_blob=route_blob,
        production_blobs=production_blobs,
        validated_corpus_fixture=fixture,
    )

    assert validated == [manifest]
    assert manifest["common_commit_sha"] == "b" * 40
    assert manifest["route_commit_sha"] == "a" * 40
    assert manifest["corpus_spec_sha"] == "c" * 64
    assert manifest["mutation_universe_sha"] == "d" * 64
    assert manifest["metric_spec_sha"] == "e" * 64
    assert manifest["common_source_sha256"] == hashlib.sha256(b"COMMON\n").hexdigest()
    assert manifest["compare_source_sha256"] == hashlib.sha256(b"COMPARE\n").hexdigest()
    assert manifest["route_manifest_sha"] == common.canonical_sha_v1(
        {
            field: value
            for field, value in manifest.items()
            if field != "route_manifest_sha"
        }
    )


def test_auxiliary_benchmark_runs_exact_warmup_and_repeat_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = {
        "ordered_d0_transcripts": [
            {"case_id": f"case-{ordinal}"} for ordinal in range(7)
        ]
    }
    calls: dict[str, int] = {
        "A_FLAT": 0,
        "B_PROGRESS": 0,
        "C_UNION": 0,
    }

    def measure(route_id: str, source_bytes: tuple[bytes, ...]) -> tuple[float, int]:
        assert len(source_bytes) == 7
        ordinal = calls[route_id]
        calls[route_id] += 1
        return float(ordinal + 1), ordinal

    monkeypatch.setattr(execute, "_measure_route_batch_v1", measure)

    benchmark = execute._build_auxiliary_benchmark_v1(fixture)

    assert calls == {"A_FLAT": 35, "B_PROGRESS": 35, "C_UNION": 35}
    assert benchmark["warm_up"] == 5
    assert benchmark["repeat"] == 30
    assert benchmark["reported_statistics"] == [
        "median",
        "p95",
        "tracemalloc_peak",
    ]
    assert [item["route_id"] for item in benchmark["ordered_route_statistics"]] == [
        "A_FLAT",
        "B_PROGRESS",
        "C_UNION",
    ]
    assert all(
        item["median"] == 20.5
        and item["p95"] == 34.0
        and item["tracemalloc_peak"] == 34
        for item in benchmark["ordered_route_statistics"]
    )


def test_d0_builder_uses_fresh_one_shot_inputs_for_final_recomputation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifests = [
        {"route_id": route_id, "route_manifest_sha": marker * 64}
        for route_id, marker in (
            ("A_FLAT", "1"),
            ("B_PROGRESS", "2"),
            ("C_UNION", "3"),
        )
    ]
    monkeypatch.setattr(
        execute,
        "_build_route_manifest_v1",
        lambda route_id, **_kwargs: next(
            manifest for manifest in manifests if manifest["route_id"] == route_id
        ),
    )
    benchmark = {
        "warm_up": 5,
        "repeat": 30,
        "reported_statistics": ["median", "p95", "tracemalloc_peak"],
        "ordered_route_statistics": [],
    }
    monkeypatch.setattr(
        execute,
        "_build_auxiliary_benchmark_v1",
        lambda _fixture: benchmark,
    )
    input_generations: list[list[dict[str, object]]] = []

    def route_inputs(**_kwargs):
        generation = len(input_generations)
        inputs = [
            {"generation": generation, "route_id": spec[0]}
            for spec in execute._ROUTE_SPECS_V1
        ]
        input_generations.append(inputs)
        return inputs

    monkeypatch.setattr(execute, "_new_ordered_route_inputs_v1", route_inputs)
    result = {"d0_result_sha": "a" * 64, "surviving_route_ids": ["A_FLAT"]}
    calls: list[tuple[str, object]] = []

    def build(**kwargs):
        calls.append(("build", kwargs["ordered_route_inputs"]))
        assert kwargs["auxiliary_benchmark"] is benchmark
        return result

    def validate(observed, **kwargs):
        assert observed is result
        calls.append(("validate", kwargs["ordered_route_inputs"]))
        return observed

    monkeypatch.setattr(common, "build_d0_comparison_v1", build)
    monkeypatch.setattr(common, "validate_d0_comparison_v1", validate)
    git_inputs = {
        "common_blob": ("b" * 40, "common.py", "100644", b"common"),
        "compare_blob": ("b" * 40, "compare.py", "100644", b"compare"),
        "production_blobs": (("b" * 40, "rulespace_v3/x.py", "100644", b"x"),),
        "ordered_route_blobs": tuple(
            (marker * 40, spec[3], "100644", marker.encode())
            for marker, spec in zip("123", execute._ROUTE_SPECS_V1)
        ),
    }

    observed = execute._build_d0_result_v1(
        corpus_fixture_raw_bytes=b"{}\n",
        validated_corpus_fixture={},
        git_inputs=git_inputs,
        python_identity_observation={"identity": True},
        python_probe_result={"probe": True},
    )

    assert observed is result
    assert len(input_generations) == 2
    assert input_generations[0] is not input_generations[1]
    assert calls == [
        ("build", input_generations[0]),
        ("validate", input_generations[1]),
    ]


def test_executor_parses_fixture_from_git_blob_without_second_path_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fixture_raw_bytes = b'{"fixture":"from-git"}\n'
    fixture = {"fixture": "from-git"}
    git_inputs = {
        "fixture_blob": (
            "a" * 40,
            "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
            "100644",
            fixture_raw_bytes,
        ),
        "common_blob": ("a" * 40, "common.py", "100644", b"common"),
        "compare_blob": ("a" * 40, "compare.py", "100644", b"compare"),
    }
    monkeypatch.setattr(execute, "_read_git_inputs_v1", lambda **_kwargs: git_inputs)
    monkeypatch.setattr(
        execute,
        "_prepare_single_experiments_namespace_v1",
        lambda _root: None,
    )
    monkeypatch.setattr(
        execute,
        "_read_stable_regular_file_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("fixture path was read after Git audit")
        ),
    )
    monkeypatch.setattr(
        execute,
        "_observe_fixture_environment_v1",
        lambda observed, _python: (
            {"identity": observed["fixture"]},
            {"probe": True},
        ),
    )
    monkeypatch.setattr(
        common,
        "validate_corpus_fixture_v2",
        lambda observed, *_args, **_kwargs: observed,
    )
    build_calls: list[dict[str, object]] = []

    def build(**kwargs):
        build_calls.append(kwargs)
        return {"d0_result_sha": "b" * 64, "surviving_route_ids": []}

    monkeypatch.setattr(execute, "_build_d0_result_v1", build)
    summary = {
        "d0_result_raw_sha256": "c" * 64,
        "d0_result_sha": "b" * 64,
        "surviving_route_ids": [],
    }
    monkeypatch.setattr(execute, "_materialize_d0_result_v1", lambda **_kwargs: summary)

    observed = execute.execute_d0_v1(
        repository_root=tmp_path,
        python_invocation_path=sys.executable,
        common_commit_sha="a" * 40,
        ordered_route_commit_shas=("1" * 40, "2" * 40, "3" * 40),
    )

    assert observed is summary
    assert len(build_calls) == 1
    assert build_calls[0]["corpus_fixture_raw_bytes"] == fixture_raw_bytes
    assert build_calls[0]["validated_corpus_fixture"] == fixture


def test_materializer_is_fixed_create_only_and_idempotent(tmp_path: Path) -> None:
    result = {"d0_result_sha": "a" * 64, "surviving_route_ids": ["A_FLAT"]}

    first = execute._materialize_d0_result_v1(
        repository_root=tmp_path,
        d0_result=result,
    )
    second = execute._materialize_d0_result_v1(
        repository_root=tmp_path,
        d0_result=result,
    )

    target = (
        tmp_path / "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json"
    )
    expected = common.canonical_json_bytes_v1(result) + b"\n"
    assert target.read_bytes() == expected
    assert (
        first
        == second
        == {
            "d0_result_raw_sha256": hashlib.sha256(expected).hexdigest(),
            "d0_result_sha": "a" * 64,
            "surviving_route_ids": ["A_FLAT"],
        }
    )

    target.chmod(0o644)
    target.write_bytes(b"different\n")
    with pytest.raises(FileExistsError, match="different|不同"):
        execute._materialize_d0_result_v1(
            repository_root=tmp_path,
            d0_result=result,
        )
    assert target.read_bytes() == b"different\n"


def test_materializer_rejects_parent_swap_to_external_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = {"d0_result_sha": "a" * 64, "surviving_route_ids": []}
    external = tmp_path / "external"
    external.mkdir()
    parent = tmp_path / "data/results/experimental/v3m0_b7_schema_lab"
    backup = tmp_path / "data/results/experimental/v3m0_b7_schema_lab.backup"
    original_create = execute._create_temporary_at_v1
    swapped = False

    def swap_then_create(parent_fd: int):
        nonlocal swapped
        assert not swapped
        swapped = True
        parent.rename(backup)
        parent.symlink_to(external, target_is_directory=True)
        return original_create(parent_fd)

    monkeypatch.setattr(execute, "_create_temporary_at_v1", swap_then_create)

    with pytest.raises(ValueError, match="parent|directory|changed"):
        execute._materialize_d0_result_v1(
            repository_root=tmp_path,
            d0_result=result,
        )

    assert swapped is True
    assert list(external.iterdir()) == []


def test_cli_requires_explicit_four_commits_and_emits_canonical_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    calls: list[dict[str, object]] = []
    summary = {
        "d0_result_raw_sha256": "1" * 64,
        "d0_result_sha": "2" * 64,
        "surviving_route_ids": ["A_FLAT"],
    }

    def run(**kwargs):
        calls.append(kwargs)
        return summary

    monkeypatch.setattr(execute, "execute_d0_v1", run)
    commits = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)

    assert (
        execute.main(
            [
                "--repository-root",
                str(tmp_path),
                "--python-invocation-path",
                sys.executable,
                "--common-commit-sha",
                commits[0],
                "--a-flat-commit-sha",
                commits[1],
                "--b-progress-commit-sha",
                commits[2],
                "--c-union-commit-sha",
                commits[3],
            ]
        )
        == 0
    )

    assert calls == [
        {
            "repository_root": tmp_path,
            "python_invocation_path": sys.executable,
            "common_commit_sha": commits[0],
            "ordered_route_commit_shas": commits[1:],
        }
    ]
    assert (
        capsysbinary.readouterr().out == common.canonical_json_bytes_v1(summary) + b"\n"
    )
