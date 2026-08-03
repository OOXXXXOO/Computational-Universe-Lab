"""Tests for the create-only B7 D1 lab executor."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
from types import ModuleType

import pytest

from experiments.v3m0_b7_schema_lab import common
from tools import v3m0_b7_execute_d1 as execute


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _d0_result(survivors: list[str]) -> dict[str, object]:
    return {
        "d0_result_sha": "a" * 64,
        "decision_payload_sha": "b" * 64,
        "surviving_route_ids": list(survivors),
        "ordered_route_results": [
            {
                "route_id": route_id,
                "route_manifest": {
                    "route_id": route_id,
                    "route_manifest_sha": marker * 64,
                },
            }
            for route_id, marker in (
                ("A_FLAT", "1"),
                ("B_PROGRESS", "2"),
                ("C_UNION", "3"),
            )
        ],
    }


def _git_inputs() -> dict[str, object]:
    common_sha = "c" * 40
    return {
        "head_commit_sha": "f" * 40,
        "common_blob": (
            common_sha,
            "experiments/v3m0_b7_schema_lab/common.py",
            "100644",
            b"COMMON\n",
        ),
        "compare_blob": (
            common_sha,
            "experiments/v3m0_b7_schema_lab/compare.py",
            "100644",
            b"COMPARE\n",
        ),
        "lab_initializer_blob": (
            common_sha,
            "experiments/v3m0_b7_schema_lab/__init__.py",
            "100644",
            b"",
        ),
        "fixture_blob": (
            common_sha,
            "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
            "100644",
            b"{}\n",
        ),
        "production_blobs": (
            (
                common_sha,
                "rulespace_v3/b7_replay_core_v1.py",
                "100644",
                b"LEAF\n",
            ),
            (common_sha, "rulespace_gpu/kernel.py", "100644", b"GPU\n"),
        ),
        "ordered_route_blobs": tuple(
            (
                marker * 40,
                path,
                "100644",
                marker.encode("ascii") + b"\n",
            )
            for marker, path in (
                ("1", "experiments/v3m0_b7_schema_lab/a_flat.py"),
                ("2", "experiments/v3m0_b7_schema_lab/b_progress.py"),
                ("3", "experiments/v3m0_b7_schema_lab/c_union.py"),
            )
        ),
    }


def test_d0_artifact_parser_requires_canonical_json_plus_exactly_one_lf() -> None:
    body = {"d0_result_sha": "a" * 64, "surviving_route_ids": ["A_FLAT"]}
    payload = common.canonical_json_bytes_v1(body)

    assert execute._parse_d0_artifact_bytes_v1(payload + b"\n") == (payload, body)
    for hostile in (payload, payload + b"\n\n", b'{"z":0,"a":1}\n'):
        with pytest.raises(ValueError):
            execute._parse_d0_artifact_bytes_v1(hostile)


@pytest.mark.parametrize("module_name", execute._LAB_EXECUTION_MODULE_NAMES_V1)
def test_d1_bootstrap_rejects_each_preloaded_lab_module(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
) -> None:
    for name in execute._LAB_EXECUTION_MODULE_NAMES_V1:
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setitem(sys.modules, module_name, ModuleType(module_name))

    with pytest.raises(RuntimeError, match=module_name):
        execute._prepare_single_experiments_namespace_v1(REPOSITORY_ROOT)


def test_fixed_d0_reader_is_stable_and_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / execute._D0_RESULT_RELATIVE_PATH_V1
    target.parent.mkdir(parents=True)
    expected = b'{"d0":true}\n'
    target.write_bytes(expected)

    assert execute._read_fixed_d0_result_v1(tmp_path) == expected

    target.unlink()
    external = tmp_path / "external.json"
    external.write_bytes(expected)
    target.symlink_to(external)
    with pytest.raises(ValueError, match="link|opened|fixed D0"):
        execute._read_fixed_d0_result_v1(tmp_path)


def test_no_survivor_is_typed_precondition_and_never_captures_or_writes(
    monkeypatch: pytest.MonPatch,
    tmp_path: Path,
) -> None:
    context = {
        "d0_result": _d0_result([]),
        "d0_result_raw_bytes": b"{}",
        "git_inputs": _git_inputs(),
        "fixture_raw_bytes": b"{}\n",
        "validated_fixture": {},
        "python_identity_observation": {},
        "python_probe_result": {},
    }
    monkeypatch.setattr(execute, "_load_and_validate_inputs_v1", lambda **_kw: context)
    monkeypatch.setattr(
        execute,
        "_capture_d1_sources_v1",
        lambda **_kw: (_ for _ in ()).throw(AssertionError("capture ran")),
    )
    monkeypatch.setattr(
        execute,
        "_materialize_d1_result_v1",
        lambda **_kw: (_ for _ in ()).throw(AssertionError("output was built")),
    )

    with pytest.raises(execute.D1PreconditionError, match="no survivor"):
        execute.execute_d1_v1(
            repository_root=tmp_path,
            python_invocation_path="/frozen/python",
            common_commit_sha="a" * 40,
            ordered_route_commit_shas=("1" * 40, "2" * 40, "3" * 40),
        )
    assert not (tmp_path / execute._D1_RESULT_RELATIVE_PATH_V1).exists()


def test_loader_full_validates_d0_from_fresh_one_shot_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fixture_raw = b'{"fixture":true}\n'
    fixture = {"fixture": True}
    d0 = _d0_result(["A_FLAT"])
    d0_payload = common.canonical_json_bytes_v1(d0)
    git_inputs = _git_inputs()
    git_inputs["fixture_blob"] = (
        "c" * 40,
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
        "100644",
        fixture_raw,
    )
    monkeypatch.setattr(execute, "_read_git_inputs_v1", lambda **_kw: git_inputs)
    monkeypatch.setattr(execute, "_prepare_single_experiments_namespace_v1", lambda _r: None)
    monkeypatch.setattr(
        execute,
        "_observe_fixture_environment_v1",
        lambda *_args: ({"identity": True}, {"probe": True}),
    )
    monkeypatch.setattr(
        common,
        "validate_corpus_fixture_v2",
        lambda observed, *_args, **_kwargs: observed,
    )
    monkeypatch.setattr(
        execute,
        "_read_fixed_d0_result_v1",
        lambda _root: d0_payload + b"\n",
    )
    generations: list[object] = []

    def fresh_inputs(**_kwargs):
        result = [{"generation": len(generations)}]
        generations.append(result)
        return result

    monkeypatch.setattr(execute, "_new_ordered_d0_route_inputs_v1", fresh_inputs)
    validated_calls: list[dict[str, object]] = []

    def validate(observed, **kwargs):
        assert observed == d0
        validated_calls.append(kwargs)
        return observed

    monkeypatch.setattr(common, "validate_d0_comparison_v1", validate)

    context = execute._load_and_validate_inputs_v1(
        repository_root=tmp_path,
        python_invocation_path="/frozen/python",
        common_commit_sha="a" * 40,
        ordered_route_commit_shas=("1" * 40, "2" * 40, "3" * 40),
    )

    assert context["d0_result"] == d0
    assert context["d0_result_raw_bytes"] == d0_payload
    assert len(generations) == 1
    assert validated_calls[0]["ordered_route_inputs"] is generations[0]
    assert validated_calls[0]["corpus_fixture_raw_bytes"] == fixture_raw


def test_capture_uses_readonly_exact_git_export_and_three_process_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    git_inputs = _git_inputs()
    observed: list[dict[str, object]] = []
    captures = [[b"capture-0"], [b"capture-1"], [b"capture-2"]]

    def run(**kwargs):
        observed.append(kwargs)
        root = Path(kwargs["export_root"])
        fixture = Path(kwargs["fixture_path"])
        assert fixture.read_bytes() == b"{}\n"
        assert fixture.stat().st_mode & 0o222 == 0
        assert not (root / "experiments/__init__.py").exists()
        for blob in (
            git_inputs["common_blob"],
            git_inputs["compare_blob"],
            git_inputs["lab_initializer_blob"],
            *git_inputs["ordered_route_blobs"],
            *git_inputs["production_blobs"],
        ):
            path = root / blob[1]
            assert path.read_bytes() == blob[3]
            assert path.stat().st_mode & 0o222 == 0
        return captures

    monkeypatch.setattr(execute, "_run_d1_fresh_capture_processes_v1", run)

    result = execute._capture_d1_sources_v1(
        repository_root=tmp_path,
        python_invocation_path="/frozen/python",
        git_inputs=git_inputs,
        validated_corpus_fixture={"fixture": True},
        python_identity_observation={"precheck": True},
    )

    assert result == captures
    assert len(observed) == 1
    assert not any(tmp_path.iterdir())


def test_d1_builder_uses_survivors_only_and_fresh_route_inputs_for_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d0 = _d0_result(["A_FLAT", "C_UNION"])
    context = {
        "d0_result": d0,
        "d0_result_raw_bytes": common.canonical_json_bytes_v1(d0),
        "git_inputs": _git_inputs(),
        "fixture_raw_bytes": b"{}\n",
        "validated_fixture": {},
        "python_identity_observation": {"identity": True},
        "python_probe_result": {"probe": True},
    }
    captures = [[b"a"], [b"b"], [b"c"]]
    generations: list[list[dict[str, object]]] = []

    def route_inputs(**kwargs):
        assert kwargs["ordered_capture_source_bytes"] is captures
        result = [{"generation": len(generations), "route_id": route_id} for route_id in d0["surviving_route_ids"]]
        generations.append(result)
        return result

    monkeypatch.setattr(execute, "_new_ordered_d1_route_inputs_v1", route_inputs)
    benchmark = {"survivors": ["A_FLAT", "C_UNION"]}
    monkeypatch.setattr(
        execute,
        "_build_d1_auxiliary_benchmark_v1",
        lambda **kwargs: benchmark if kwargs["ordered_survivor_route_ids"] == ["A_FLAT", "C_UNION"] else None,
    )
    result = {
        "d1_result_sha": "d" * 64,
        "decision_payload_sha": "e" * 64,
        "surviving_route_ids": ["A_FLAT"],
        "provisional_winner_route_id": "A_FLAT",
        "tie_detected": False,
    }
    calls: list[tuple[str, object]] = []

    def build(**kwargs):
        calls.append(("build", kwargs["ordered_route_inputs"]))
        assert kwargs["auxiliary_benchmark"] is benchmark
        return result

    def validate(observed_result, **kwargs):
        assert observed_result is result
        calls.append(("validate", kwargs["ordered_route_inputs"]))
        return observed_result

    monkeypatch.setattr(common, "build_d1_comparison_v1", build)
    monkeypatch.setattr(common, "validate_d1_comparison_v1", validate)

    observed_result = execute._build_d1_result_v1(
        context=context,
        ordered_capture_source_bytes=captures,
    )

    assert observed_result is result
    assert len(generations) == 2
    assert generations[0] is not generations[1]
    assert calls == [("build", generations[0]), ("validate", generations[1])]


def test_materializer_is_fixed_create_only_idempotent_and_typed(tmp_path: Path) -> None:
    result = {
        "d1_result_sha": "a" * 64,
        "decision_payload_sha": "b" * 64,
        "surviving_route_ids": ["A_FLAT"],
        "provisional_winner_route_id": "A_FLAT",
        "tie_detected": False,
    }
    first = execute._materialize_d1_result_v1(repository_root=tmp_path, d1_result=result)
    second = execute._materialize_d1_result_v1(repository_root=tmp_path, d1_result=result)
    target = tmp_path / execute._D1_RESULT_RELATIVE_PATH_V1
    expected = common.canonical_json_bytes_v1(result) + b"\n"
    assert target.read_bytes() == expected
    assert first == second == {
        "d1_result_raw_sha256": hashlib.sha256(expected).hexdigest(),
        "d1_result_sha": "a" * 64,
        "decision_payload_sha": "b" * 64,
        "surviving_route_ids": ["A_FLAT"],
        "provisional_winner_route_id": "A_FLAT",
        "tie_detected": False,
    }

    target.chmod(0o644)
    target.write_bytes(b"different\n")
    with pytest.raises(FileExistsError):
        execute._materialize_d1_result_v1(repository_root=tmp_path, d1_result=result)


def test_materializer_rejects_parent_swap_to_external_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = {
        "d1_result_sha": "a" * 64,
        "decision_payload_sha": "b" * 64,
        "surviving_route_ids": [],
        "provisional_winner_route_id": None,
        "tie_detected": False,
    }
    external = tmp_path / "external"
    external.mkdir()
    parent = tmp_path / execute._D1_RESULT_RELATIVE_PATH_V1.parent
    backup = parent.with_name(parent.name + ".backup")
    original_create = execute._create_temporary_at_v1

    def swap_then_create(parent_fd: int):
        parent.rename(backup)
        parent.symlink_to(external, target_is_directory=True)
        return original_create(parent_fd)

    monkeypatch.setattr(execute, "_create_temporary_at_v1", swap_then_create)
    with pytest.raises(ValueError, match="parent|directory|changed"):
        execute._materialize_d1_result_v1(repository_root=tmp_path, d1_result=result)
    assert list(external.iterdir()) == []


def test_cli_requires_four_commits_and_emits_canonical_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    summary = {
        "d1_result_raw_sha256": "1" * 64,
        "d1_result_sha": "2" * 64,
        "decision_payload_sha": "3" * 64,
        "surviving_route_ids": ["A_FLAT"],
        "provisional_winner_route_id": "A_FLAT",
        "tie_detected": False,
    }
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        execute,
        "execute_d1_v1",
        lambda **kwargs: calls.append(kwargs) or summary,
    )
    commits = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)

    assert execute.main(
        [
            "--repository-root",
            str(tmp_path),
            "--python-invocation-path",
            "/frozen/python",
            "--common-commit-sha",
            commits[0],
            "--a-flat-commit-sha",
            commits[1],
            "--b-progress-commit-sha",
            commits[2],
            "--c-union-commit-sha",
            commits[3],
        ]
    ) == 0
    assert calls[0]["ordered_route_commit_shas"] == commits[1:]
    assert capsysbinary.readouterr().out == common.canonical_json_bytes_v1(summary) + b"\n"
