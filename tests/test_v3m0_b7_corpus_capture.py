"""End-to-end tests for the auditable B7 v9.2 frozen-corpus capture."""

from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path
import sys

import pytest

from experiments.v3m0_b7_schema_lab import common
from tools import v3m0_b7_capture_corpus as capture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FROZEN_CORPUS_PATH = REPOSITORY_ROOT / "tests/fixtures/v3m0_b7_schema_lab_corpus.json"
FROZEN_CORPUS_RAW_SHA256 = (
    "0b9b3863acec01ec4f8eb898df036e24bdb490f51ca0cb71a8bb9559066fe156"
)


def test_frozen_corpus_raw_root_is_checked_before_json_decode() -> None:
    raw_bytes = FROZEN_CORPUS_PATH.read_bytes()
    assert hashlib.sha256(raw_bytes).hexdigest() == FROZEN_CORPUS_RAW_SHA256

    assert raw_bytes.endswith(b"\n")
    payload = raw_bytes[:-1]
    assert payload and b"\n" not in payload
    fixture = common.strict_json_loads_v1(payload)
    assert common.canonical_json_bytes_v1(fixture) == payload
    assert tuple(fixture) == (
        "corpus_spec",
        "environment_manifest",
        "fixture_schema_version",
        "fixture_sha",
        "metric_spec",
        "mutation_universe",
        "ordered_d0_transcripts",
        "synthetic_graph_manifest",
    )
    assert fixture["fixture_sha"] == common.canonical_sha_v1(
        {name: value for name, value in fixture.items() if name != "fixture_sha"}
    )


def test_capture_builder_materializes_one_complete_self_consistent_graph() -> None:
    bundle = capture.build_synthetic_graph_bundle_v1()

    graph = common.validate_synthetic_graph_manifest_v1(bundle["graph"])
    provenance = common.validate_provenance_fixture_v1(bundle["provenance"])
    run_spec = common.validate_response_run_spec_fixture_v1(
        bundle["run_spec"],
        provenance,
        graph,
    )

    assert graph["authority_state"] == "NON_AUTHORITY_SYNTHETIC"
    assert graph["selected_fejer_order"] == 256
    assert len(graph["ordered_component_bodies"]) == 11
    assert all(
        set(component["complete_body"]) != {"owner"}
        for component in graph["ordered_component_bodies"]
    )
    assert run_spec["selected_fejer_order"] == 256
    assert len(run_spec["channel_order"]) == 20
    manifest = provenance["permit_body"]["calibration"]["calibration_outcome"][
        "manifest"
    ]
    assert [
        entry["control_id"] for entry in manifest["control_registry"]["entries"]
    ] == ["full"]
    assert [
        entry["control_id"] for entry in manifest["window_protocol"]["control_entries"]
    ] == ["full"]


def test_capture_builder_emits_all_seven_strict_transcripts_from_one_graph() -> None:
    bundle = capture.build_synthetic_graph_bundle_v1()
    corpus_sha = "1" * 64
    environment_sha = "2" * 64

    transcripts = capture.build_ordered_d0_transcripts_v1(
        bundle,
        corpus_spec_sha=corpus_sha,
        environment_manifest_sha=environment_sha,
    )

    assert [transcript["case_id"] for transcript in transcripts] == [
        "reference_failure",
        "shell_failure",
        "actual_response_values_failure",
        "matched_response_values_failure",
        "actual_bridge_failure",
        "matched_bridge_failure",
        "success",
    ]
    for transcript in transcripts:
        assert (
            common.validate_normalized_transcript_v1(
                transcript,
                corpus_spec_sha=corpus_sha,
                environment_manifest_sha=environment_sha,
                graph_raw=bundle["graph"],
            )
            == transcript
        )
        assert all(
            leaf["input_body_sha"] != leaf["output_body_sha"]
            for leaf in transcript["ordered_leaf_digests"]
        )


def test_capture_builder_closes_corpus_specs_mutations_environment_and_self_root() -> (
    None
):
    fixture, identity, probe = capture.build_corpus_fixture_v2(
        repository_root=REPOSITORY_ROOT,
        python_invocation_path=sys.executable,
    )
    common_bytes = (
        REPOSITORY_ROOT / "experiments/v3m0_b7_schema_lab/common.py"
    ).read_bytes()
    compare_bytes = (
        REPOSITORY_ROOT / "experiments/v3m0_b7_schema_lab/compare.py"
    ).read_bytes()

    assert (
        common.validate_corpus_fixture_v2(
            fixture,
            common_bytes,
            compare_bytes,
            python_identity_observation=identity,
            python_probe_result=probe,
        )
        == fixture
    )
    assert fixture["mutation_universe"]["mutation_count"] == 11618
    assert len(fixture["ordered_d0_transcripts"]) == 7
    assert capture.render_fixture_bytes_v1(fixture).endswith(b"\n")


def _small_fixture(marker: str = "a") -> dict[str, object]:
    payload = {
        "mutation_universe": {"mutation_count": 11618},
        "payload": marker,
    }
    return {**payload, "fixture_sha": capture._core.canonical_sha_v1(payload)}


def test_materializer_has_no_arbitrary_target_argument_and_uses_fixed_path(
    tmp_path: Path,
) -> None:
    assert tuple(
        inspect.signature(capture.materialize_corpus_fixture_v1).parameters
    ) == (
        "repository_root",
        "fixture",
    )

    summary = capture.materialize_corpus_fixture_v1(
        repository_root=tmp_path,
        fixture=_small_fixture(),
    )

    target = tmp_path / "tests/fixtures/v3m0_b7_schema_lab_corpus.json"
    assert target.read_bytes() == capture.render_fixture_bytes_v1(_small_fixture())
    assert summary == {
        "fixture_raw_sha256": summary["fixture_raw_sha256"],
        "fixture_sha": _small_fixture()["fixture_sha"],
        "mutation_count": 11618,
    }
    assert len(summary["fixture_raw_sha256"]) == 64
    assert target.stat().st_mode & 0o777 == 0o444
    assert list(target.parent.glob(".v3m0-b7-corpus-*.tmp")) == []


def test_materializer_is_inode_preserving_idempotent_for_identical_bytes(
    tmp_path: Path,
) -> None:
    fixture = _small_fixture()
    first = capture.materialize_corpus_fixture_v1(
        repository_root=tmp_path,
        fixture=fixture,
    )
    target = tmp_path / "tests/fixtures/v3m0_b7_schema_lab_corpus.json"
    before = target.stat()

    second = capture.materialize_corpus_fixture_v1(
        repository_root=tmp_path,
        fixture=fixture,
    )
    after = target.stat()

    assert second == first
    assert (after.st_dev, after.st_ino, after.st_mtime_ns) == (
        before.st_dev,
        before.st_ino,
        before.st_mtime_ns,
    )


def test_materializer_rejects_existing_different_bytes_without_overwrite(
    tmp_path: Path,
) -> None:
    target = tmp_path / "tests/fixtures/v3m0_b7_schema_lab_corpus.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"frozen-other-bytes\n")
    target.chmod(0o444)
    before = target.stat()

    with pytest.raises(FileExistsError, match="不同"):
        capture.materialize_corpus_fixture_v1(
            repository_root=tmp_path,
            fixture=_small_fixture(),
        )

    after = target.stat()
    assert target.read_bytes() == b"frozen-other-bytes\n"
    assert (after.st_dev, after.st_ino, after.st_mtime_ns) == (
        before.st_dev,
        before.st_ino,
        before.st_mtime_ns,
    )
    assert list(target.parent.glob(".v3m0-b7-corpus-*.tmp")) == []


def test_materializer_rejects_target_symlink(tmp_path: Path) -> None:
    target = tmp_path / "tests/fixtures/v3m0_b7_schema_lab_corpus.json"
    target.parent.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_bytes(b"do-not-touch")
    target.symlink_to(elsewhere)

    with pytest.raises(ValueError, match="符号链接"):
        capture.materialize_corpus_fixture_v1(
            repository_root=tmp_path,
            fixture=_small_fixture(),
        )

    assert elsewhere.read_bytes() == b"do-not-touch"


def test_materializer_rejects_fixture_self_root_before_creating_target(
    tmp_path: Path,
) -> None:
    fixture = _small_fixture()
    fixture["payload"] = "drifted-after-seal"

    with pytest.raises(ValueError, match="自哈希"):
        capture.materialize_corpus_fixture_v1(
            repository_root=tmp_path,
            fixture=fixture,
        )

    assert not (tmp_path / "tests/fixtures/v3m0_b7_schema_lab_corpus.json").exists()


def test_materializer_fsyncs_before_create_only_atomic_publish(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[tuple[str, object]] = []
    original_fsync = os.fsync
    original_link = os.link

    def fsync(file_descriptor: int) -> None:
        events.append(("fsync", file_descriptor))
        original_fsync(file_descriptor)

    def link(source, target, **kwargs) -> None:
        events.append(("link", (Path(source), Path(target))))
        original_link(source, target, **kwargs)

    monkeypatch.setattr(capture.os, "fsync", fsync)
    monkeypatch.setattr(capture.os, "link", link)

    capture.materialize_corpus_fixture_v1(
        repository_root=tmp_path,
        fixture=_small_fixture(),
    )

    link_index = next(index for index, event in enumerate(events) if event[0] == "link")
    assert any(event[0] == "fsync" for event in events[:link_index])
    source, target = events[link_index][1]
    assert source.parent == target.parent
    assert target == tmp_path / "tests/fixtures/v3m0_b7_schema_lab_corpus.json"
    assert sum(event[0] == "fsync" for event in events[link_index + 1 :]) >= 1


def test_cli_emits_only_one_canonical_summary_line(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    fixture = _small_fixture()
    monkeypatch.setattr(
        capture,
        "build_corpus_fixture_v2",
        lambda **_kwargs: (fixture, {"identity": True}, {"probe": True}),
    )
    validation_calls: list[dict[str, object]] = []

    def validate(**kwargs):
        validation_calls.append(kwargs)
        return kwargs["fixture"]

    monkeypatch.setattr(
        capture,
        "validate_corpus_fixture_for_materialization_v1",
        validate,
    )

    assert (
        capture.main(
            [
                "--repository-root",
                str(tmp_path),
                "--python-invocation-path",
                sys.executable,
            ]
        )
        == 0
    )

    stdout = capsysbinary.readouterr().out
    assert len(validation_calls) == 1
    assert validation_calls[0]["fixture"] is fixture
    assert validation_calls[0]["python_identity_observation"] == {"identity": True}
    assert validation_calls[0]["python_probe_result"] == {"probe": True}
    expected = capture.render_materialization_summary_v1(
        capture.materialize_corpus_fixture_v1(
            repository_root=tmp_path,
            fixture=fixture,
        )
    )
    assert stdout == expected
    assert stdout.endswith(b"\n") and b"\n" not in stdout[:-1]
    parsed = _core_summary_load(stdout[:-1])
    assert tuple(parsed) == (
        "fixture_raw_sha256",
        "fixture_sha",
        "mutation_count",
    )


def _core_summary_load(raw_bytes: bytes) -> dict[str, object]:
    parsed = capture._core.strict_json_loads_v1(raw_bytes)
    assert capture._core.canonical_json_bytes_v1(parsed) == raw_bytes
    return parsed
