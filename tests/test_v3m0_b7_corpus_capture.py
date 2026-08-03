"""End-to-end tests for the auditable B7 v9.2 frozen-corpus capture."""

from __future__ import annotations

from pathlib import Path
import sys

from experiments.v3m0_b7_schema_lab import common
from tools import v3m0_b7_capture_corpus as capture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


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
    manifest = provenance["permit_body"]["calibration"][
        "calibration_outcome"
    ]["manifest"]
    assert [
        entry["control_id"] for entry in manifest["control_registry"]["entries"]
    ] == ["full"]
    assert [
        entry["control_id"] for entry in manifest["window_protocol"][
            "control_entries"
        ]
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
        assert common.validate_normalized_transcript_v1(
            transcript,
            corpus_spec_sha=corpus_sha,
            environment_manifest_sha=environment_sha,
            graph_raw=bundle["graph"],
        ) == transcript
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

    assert common.validate_corpus_fixture_v2(
        fixture,
        common_bytes,
        compare_bytes,
        python_identity_observation=identity,
        python_probe_result=probe,
    ) == fixture
    assert fixture["mutation_universe"]["mutation_count"] == 11618
    assert len(fixture["ordered_d0_transcripts"]) == 7
    assert capture.render_fixture_bytes_v1(fixture).endswith(b"\n")
