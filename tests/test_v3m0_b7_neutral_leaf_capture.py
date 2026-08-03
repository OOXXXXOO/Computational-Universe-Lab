"""Tests for the common-owned B7 neutral-leaf capture scheduler."""

from __future__ import annotations

import copy
import inspect

import pytest

from experiments.v3m0_b7_schema_lab import common


def _leaf_inputs() -> dict[str, object]:
    return {
        "reference_spec": {"reference_spec_sha": "1" * 64},
        "shell_spec_template": {
            "endpoint_reference_projector": None,
            "shell_spec_sha": "2" * 64,
        },
        "reference_transition_matrix": "reference-transition",
        "reference_metric_matrix": "reference-metric",
        "ordered_shell_transition_matrices": ("shell-transition",),
        "ordered_shell_metric_matrices": ("shell-metric",),
        "source_injection_matrix": "source-injection",
        "readout_matrix": "readout",
        "ordered_actual_transition_matrices": ("actual-transition",),
        "ordered_actual_metric_matrices": ("actual-metric",),
        "ordered_matched_ablated_transition_matrices": ("matched-transition",),
        "ordered_matched_ablated_metric_matrices": ("matched-metric",),
        "ordered_actual_raw_differences": (((0,), 2, "actual-difference"),),
        "ordered_matched_ablated_raw_differences": (((0,), 2, "matched-difference"),),
    }


def _graph() -> dict[str, object]:
    def branch(prefix: str) -> list[dict[str, object]]:
        return [
            {
                "component_id": f"{prefix}_transition_outcome",
                "complete_body": {
                    "factory_binding": {"factory": {"factory_sha": prefix[0] * 64}},
                    "measured_transition": {
                        "transition_sha": prefix[-1] * 64,
                        "dt": 0.25,
                    },
                },
            },
            {
                "component_id": f"{prefix}_certificate_outcome",
                "complete_body": {
                    "status": {"defined": True, "reason": None},
                    "failure": None,
                    "certificate": {"certificate_sha": "c" * 64},
                },
            },
        ]

    return {
        "graph_sha": "g" * 64,
        "ordered_component_bodies": [
            *branch("actual"),
            *branch("matched_ablated"),
        ],
    }


def _run_spec() -> dict[str, object]:
    return {
        "run_spec_sha": "r" * 64,
        "response_grid": {"grid": "response"},
        "selected_fejer_order": 256,
        "source_basis": {"role": "source"},
        "readout_basis": {"role": "readout"},
        "source_readout_bridge_grid": {"grid": "bridge"},
        "source_readout_bridge_steps": [2],
        "source_trial_vectors": {"trials": "identity"},
        "current_readout_calibration_spec": {"calibration": "current"},
    }


def _install_upstream_spies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(common, "validate_synthetic_graph_manifest_v1", lambda raw: raw)
    monkeypatch.setattr(common, "validate_provenance_fixture_v1", lambda raw: raw)
    monkeypatch.setattr(
        common,
        "validate_response_run_spec_fixture_v1",
        lambda raw, _provenance, _graph: raw,
    )
    monkeypatch.setattr(
        common,
        "validate_normalized_transcript_v1",
        lambda raw, **_kwargs: raw,
    )
    monkeypatch.setattr(
        common,
        "validate_source_readout_response_raw_v1",
        lambda raw, *_args: raw,
    )


def _install_leaf_spies(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
) -> None:
    def reference(*_args):
        calls.append("reference")
        return {
            "status": {"defined": True, "reason": None},
            "failure": None,
            "reference": {"reference_sha": "e" * 64},
            "outcome_sha": "f" * 64,
        }

    def shell(*_args):
        calls.append("shell")
        return {
            "status": {"defined": True, "reason": None},
            "failure": None,
            "shell": {
                "shell_manifest_sha": "s" * 64,
                "shell_phases": [1.0],
            },
            "outcome_sha": "h" * 64,
        }

    def values(branch, *_args):
        calls.append(f"{branch}_response_values")
        if branch not in ("actual", "matched_ablated"):
            raise ValueError("branch is not closed")
        return {"tensor_sha": branch[0] * 64}

    def bridge(branch, *_args):
        calls.append(f"{branch}_bridge")
        if branch not in ("actual", "matched_ablated"):
            raise ValueError("branch is not closed")
        return {"bridge_sha": branch[0] * 64}

    def assemble(actual_values, matched_values, actual_bridge, matched_bridge, failure):
        calls.append("assemble")
        actual = {
            "branch": "actual",
            "response_values": actual_values,
            "bridge_audit": actual_bridge,
            "failure": failure
            if failure in ("actual_response_failed", "actual_bridge_failed")
            else None,
            "attempt_sha": "a" * 64,
        }
        matched = None
        if matched_values is not None or failure in (
            "matched_ablated_response_failed",
            "matched_ablated_bridge_failed",
        ):
            matched = {
                "branch": "matched_ablated",
                "response_values": matched_values,
                "bridge_audit": matched_bridge,
                "failure": failure
                if failure and failure.startswith("matched")
                else None,
                "attempt_sha": "m" * 64,
            }
        return actual, matched, failure

    monkeypatch.setattr(
        common._pure_core, "_select_endpoint_reference_from_raw", reference
    )
    monkeypatch.setattr(common._pure_core, "_track_endpoint_shell_from_raw", shell)
    monkeypatch.setattr(
        common._pure_core,
        "_build_fejer_branch_response_values_from_raw",
        values,
    )
    monkeypatch.setattr(
        common._pure_core, "_audit_source_readout_bridge_from_raw", bridge
    )
    monkeypatch.setattr(
        common._pure_core,
        "_assemble_atomic_paired_response_attempt_from_raw",
        assemble,
    )


def _capture(case_id: str, leaf_inputs: dict[str, object]) -> dict[str, object]:
    return common.capture_normalized_transcript_from_raw_v1(
        case_id=case_id,
        corpus_spec_sha="1" * 64,
        environment_manifest_sha="2" * 64,
        provenance_fixture={"provenance_fixture_sha": "p" * 64},
        response_run_spec_fixture=_run_spec(),
        synthetic_graph_manifest=_graph(),
        leaf_inputs=leaf_inputs,
    )


def test_common_harness_owns_all_success_leaf_calls_in_frozen_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _install_upstream_spies(monkeypatch)
    _install_leaf_spies(monkeypatch, calls)

    observed = _capture("success", _leaf_inputs())

    assert calls == [
        "reference",
        "shell",
        "actual_response_values",
        "matched_ablated_response_values",
        "actual_bridge",
        "matched_ablated_bridge",
        "assemble",
    ]
    assert observed["callback_trace"] == [
        "reference",
        "shell",
        "actual_response_values",
        "matched_ablated_response_values",
        "actual_bridge",
        "matched_ablated_bridge",
    ]
    assert [leaf["leaf_id"] for leaf in observed["ordered_leaf_digests"]] == observed[
        "callback_trace"
    ]
    assert observed["actual_completed_response"] is not None
    assert observed["matched_ablated_completed_response"] is not None


@pytest.mark.parametrize(
    ("case_id", "expected_calls"),
    (
        (
            "actual_response_values_failure",
            ["reference", "shell", "__injected_failure___response_values", "assemble"],
        ),
        (
            "matched_bridge_failure",
            [
                "reference",
                "shell",
                "actual_response_values",
                "matched_ablated_response_values",
                "actual_bridge",
                "__injected_failure___bridge",
                "assemble",
            ],
        ),
    ),
)
def test_common_harness_injects_exact_first_failure_and_stops_later_leaves(
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
    expected_calls: list[str],
) -> None:
    calls: list[str] = []
    _install_upstream_spies(monkeypatch)
    _install_leaf_spies(monkeypatch, calls)

    observed = _capture(case_id, _leaf_inputs())

    assert calls == expected_calls
    assert observed["terminal_tag"] == case_id
    assert observed["callback_trace"][-1] == common._case_contract_v1(case_id)[3]
    assert observed["actual_completed_response"] is None
    assert observed["matched_ablated_completed_response"] is None


def test_common_harness_rejects_nonexact_leaf_input_domain_before_any_leaf_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _install_upstream_spies(monkeypatch)
    _install_leaf_spies(monkeypatch, calls)
    leaf_inputs = _leaf_inputs()
    leaf_inputs["caller_leaf_provider"] = object()

    with pytest.raises(ValueError, match="fields or field order drifted"):
        _capture("success", leaf_inputs)

    assert calls == []


def test_injected_leaf_failure_helper_accepts_no_callback_or_provider() -> None:
    assert tuple(
        inspect.signature(common._capture_injected_leaf_failure_v1).parameters
    ) == ("leaves", "leaf_id", "call_args")


def test_common_harness_leaf_digest_binds_actual_matrix_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _install_upstream_spies(monkeypatch)
    _install_leaf_spies(monkeypatch, calls)
    first = _capture("success", _leaf_inputs())
    changed_inputs = copy.deepcopy(_leaf_inputs())
    changed_inputs["reference_transition_matrix"] = "changed-transition"
    second = _capture("success", changed_inputs)

    assert (
        first["ordered_leaf_digests"][0]["input_body_sha"]
        != second["ordered_leaf_digests"][0]["input_body_sha"]
    )


def _d1_wrapper_fixture() -> dict[str, object]:
    provenance = {
        "permit_body": {
            "calibration": {
                "calibration_outcome": {
                    "manifest": {
                        "control_registry": {"entries": [{"entry": "control"}]}
                    }
                }
            }
        }
    }
    run_spec = {
        "window_protocol_sha": "1" * 64,
        "selected_fejer_order": 256,
        "reference_reciprocal_index": [1],
        "preregistered_phase_bands": [[1.0, 2.0]],
        "expected_shell_rank": 1,
        "channel_order": ["x", "y"],
        "response_grid": {"grid": "response"},
        "source_readout_bridge_grid": {"reciprocal_indices": [[0], [1]]},
        "source_readout_bridge_steps": [2],
    }
    transcripts = [
        {
            "case_id": row[1],
            "provenance_fixture": copy.deepcopy(provenance),
            "response_run_spec_fixture": copy.deepcopy(run_spec),
        }
        for row in common._CASE_CONTRACTS_V1
    ]
    return {
        "corpus_spec": {"corpus_spec_sha": "2" * 64},
        "environment_manifest": {"environment_sha": "3" * 64},
        "synthetic_graph_manifest": {
            "selected_fejer_order": 256,
            "graph_sha": "4" * 64,
        },
        "ordered_d0_transcripts": transcripts,
    }


def test_d1_capture_wrapper_has_only_ordinal_and_validated_fixture_boundary() -> None:
    assert tuple(inspect.signature(common.capture_d1_transcript_set_v1).parameters) == (
        "capture_ordinal",
        "validated_corpus_fixture",
    )


def test_d1_capture_wrapper_reconstructs_all_seven_raw_inputs_inside_common(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _d1_wrapper_fixture()
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        common,
        "_validated_d0_fixture_source_domain_v1",
        lambda observed: (
            observed,
            [copy.deepcopy(observed["ordered_d0_transcripts"])],
        ),
    )
    monkeypatch.setattr(
        common,
        "validate_synthetic_graph_manifest_v1",
        lambda observed: copy.deepcopy(observed),
    )
    monkeypatch.setattr(
        common,
        "_validate_normalized_transcript_against_validated_graph_v1",
        lambda observed, **_kwargs: copy.deepcopy(observed),
    )
    monkeypatch.setattr(
        common,
        "_branch_lineage_v1",
        lambda _graph, branch: {
            "factory_sha": ("a" if branch == "actual" else "b") * 64,
            "transition_sha": ("c" if branch == "actual" else "d") * 64,
            "dynamics_certificate_sha": "e" * 64,
            "dt": 0.25,
        },
    )

    def capture(**kwargs):
        calls.append(kwargs)
        return {"case_id": kwargs["case_id"], "captured": True}

    monkeypatch.setattr(common, "capture_normalized_transcript_from_raw_v1", capture)

    observed = common.capture_d1_transcript_set_v1(
        capture_ordinal=2,
        validated_corpus_fixture=fixture,
    )

    assert [row["case_id"] for row in observed] == [
        row[1] for row in common._CASE_CONTRACTS_V1
    ]
    assert len(calls) == 7
    assert all("leaf_provider" not in call and "callback" not in call for call in calls)
    assert all(call["corpus_spec_sha"] == "2" * 64 for call in calls)
    assert all(call["environment_manifest_sha"] == "3" * 64 for call in calls)
    assert all(
        call["synthetic_graph_manifest"] == fixture["synthetic_graph_manifest"]
        for call in calls
    )
    first = calls[0]["leaf_inputs"]
    second = calls[1]["leaf_inputs"]
    success = calls[-1]["leaf_inputs"]
    assert first["reference_transition_matrix"].shape == (2, 2)
    assert first["reference_transition_matrix"].tolist() == [[1.0, 0.0], [0.0, 1.0]]
    assert second["ordered_shell_transition_matrices"][0].tolist() == [
        [1.0, 0.0],
        [0.0, 1.0],
    ]
    assert success["reference_transition_matrix"].tolist() == [
        [1j, 0j],
        [0j, 1 + 0j],
    ]


@pytest.mark.parametrize("capture_ordinal", (-1, 3, True, 1.0, "1"))
def test_d1_capture_wrapper_rejects_nonfrozen_ordinal_before_raw_leaf_call(
    monkeypatch: pytest.MonkeyPatch,
    capture_ordinal,
) -> None:
    calls = 0

    def forbidden(**_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("raw leaf scheduler entered")

    monkeypatch.setattr(common, "capture_normalized_transcript_from_raw_v1", forbidden)
    with pytest.raises((TypeError, ValueError)):
        common.capture_d1_transcript_set_v1(
            capture_ordinal=capture_ordinal,
            validated_corpus_fixture=_d1_wrapper_fixture(),
        )
    assert calls == 0
