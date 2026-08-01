"""Fast tests for the non-authoritative Task-11 raw replay artifact."""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.thresholds import T_CANDIDATES


SHA0 = "0" * 64
SHA1 = "1" * 64
SHA2 = "2" * 64
SHA3 = "3" * 64
SHA4 = "4" * 64
SHA5 = "5" * 64
SHA6 = "6" * 64
SHA7 = "7" * 64
SHA8 = "8" * 64
SHA9 = "9" * 64
SHAA = "a" * 64
SHAB = "b" * 64
SHAC = "c" * 64
SHAD = "d" * 64
SHAE = "e" * 64
SHAF = "f" * 64
_CONTROL_CASES = (
    ("C01_BLIND_HOLDOUT_FULL", "full"),
    ("C02_CONDITIONED_ZERO", "zero"),
    ("C03_EQUAL_RANK_DIRECT_SUM", "direct_sum"),
)


def _attempt(order: int, suffix: str, entry_sha: str) -> dict[str, object]:
    reference_body = {
        "status": {"defined": True, "reason": None},
        "failure": None,
        "reference_spec": {},
        "attempt_audit": {},
        "reference": {},
    }
    reference = {
        **reference_body,
        "outcome_sha": canonical_sha(reference_body),
    }
    shell_manifest = {"shell_manifest_sha": canonical_sha({})}
    shell_body = {
        "status": {"defined": True, "reason": None},
        "failure": None,
        "reference_outcome": copy.deepcopy(reference),
        "attempt_audit": {},
        "shell": shell_manifest,
    }
    shell_outcome = {**shell_body, "outcome_sha": canonical_sha(shell_body)}
    paired_response = {"pair_sha": canonical_sha({})}
    paired_body = {
        "status": {"defined": True, "reason": None},
        "failure": None,
        "attempt_audit": {},
        "paired_response": paired_response,
    }
    paired_outcome = {**paired_body, "outcome_sha": canonical_sha(paired_body)}
    audit_body = {
        "attempt_schema_version": "v3m0.candidate-attempt-audit.v1",
        "control_registry_entry_sha": entry_sha,
        "fejer_order": order,
        "reference_outcome": reference,
        "shell_outcome": shell_outcome,
        "paired_response_outcome": paired_outcome,
    }
    attempt_audit = {**audit_body, "attempt_sha": canonical_sha(audit_body)}
    outcome_body = {
        "status": {"defined": True, "reason": None},
        "failure": None,
        "run_spec": {
            "fejer_order": order,
            "control_registry_entry_sha": entry_sha,
            "spec_sha": (suffix * 64)[:64],
        },
        "attempt_audit": attempt_audit,
    }
    return {**outcome_body, "outcome_sha": canonical_sha(outcome_body)}


def _branch_spectrum(branch: str) -> dict[str, object]:
    body = {
        "branch": branch,
        "declared_rank": 1,
        "spectrum_shape": [1, 1],
        "spectrum_order_id": "k-major-singular-descending-v1",
        "raw_spectrum": [1.0],
        "active_min": 1.0,
        "inactive_max": None,
    }
    return {**body, "branch_sha": canonical_sha(body)}


def _spectrum(
    kind: str,
    *,
    order: int,
    entry_sha: str,
    declaration_sha: str,
    run_spec_sha: str,
    paired_response_sha: str,
) -> dict[str, object]:
    body = {
        "readout_kind": kind,
        "control_registry_entry_sha": entry_sha,
        "expected_rank_declaration_sha": declaration_sha,
        "fejer_order": order,
        "run_spec_sha": run_spec_sha,
        "paired_response_sha": paired_response_sha,
        "actual": _branch_spectrum("actual"),
        "ablated": _branch_spectrum("matched_ablated"),
        "actual_bridge_operator_error_upper": 1.0e-14,
        "ablated_bridge_operator_error_upper": 1.0e-14,
    }
    return {**body, "audit_sha": canonical_sha(body)}


def _aggregate(
    kind: str,
    order: int,
    *,
    per_control: list[dict[str, object]],
    gates_passed: bool = False,
) -> dict[str, object]:
    scale = float(order)
    body = {
        "readout_kind": kind,
        "per_control": copy.deepcopy(per_control),
        "scale_ref": scale,
        "null_max": scale / 1000.0,
        "bridge_operator_error_max": 1.0e-14,
        "noise_ref": scale / 500.0,
        "signal_min": scale / 2.0,
        "tau_sig": scale / 100.0,
        "signal_noise_ratio": 250.0,
        "raw_relative_gap": 500.0,
        "absolute_signal_gate_passed": True,
        "relative_gap_gate_passed": gates_passed,
    }
    return {**body, "aggregate_sha": canonical_sha(body)}


def _selection_for_candidate(candidate: dict[str, object]) -> dict[str, object]:
    aggregates = {
        item["readout_kind"]: item for item in candidate["readout_aggregate_audits"]
    }
    references = []
    for control in candidate["control_audits"]:
        candidate_t = control["candidate_t"]
        comparison_2t = control["comparison_2t"]
        references.append(
            {
                "control_id": control["control_registry_entry"]["control_id"],
                "control_registry_entry_sha": control["control_registry_entry"][
                    "entry_sha"
                ],
                "expected_rank_declaration_sha": control["expected_rank_declaration"][
                    "declaration_sha"
                ],
                "run_spec_sha": candidate_t["run_spec"]["spec_sha"],
                "paired_response_sha": candidate_t["attempt_audit"][
                    "paired_response_outcome"
                ]["paired_response"]["pair_sha"],
                "shell_manifest_sha": candidate_t["attempt_audit"]["shell_outcome"][
                    "shell"
                ]["shell_manifest_sha"],
                "comparison_2t_run_spec_sha": comparison_2t["run_spec"]["spec_sha"],
                "comparison_2t_response_sha": comparison_2t["attempt_audit"][
                    "paired_response_outcome"
                ]["paired_response"]["pair_sha"],
                "comparison_2t_shell_manifest_sha": comparison_2t["attempt_audit"][
                    "shell_outcome"
                ]["shell"]["shell_manifest_sha"],
            }
        )
    provisional = {
        "selected_fejer_order": candidate["fejer_order"],
        "h_scale_ref": aggregates["h"]["scale_ref"],
        "h_noise_ref": aggregates["h"]["noise_ref"],
        "h_signal_min": aggregates["h"]["signal_min"],
        "h_tau_sig": aggregates["h"]["tau_sig"],
        "curv_scale_ref": aggregates["curv"]["scale_ref"],
        "curv_noise_ref": aggregates["curv"]["noise_ref"],
        "curv_signal_min": aggregates["curv"]["signal_min"],
        "curv_tau_sig": aggregates["curv"]["tau_sig"],
        "selected_evidence_refs": references,
    }
    return {**provisional, "selection_sha": canonical_sha(provisional)}


@lru_cache(maxsize=1)
def _real_root_wire_snapshot() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    str,
    tuple[str, ...],
]:
    """Cold-build exact domain roots; no hand-authored self-consistent roots."""

    from rulespace_v3.current_window_replay import (
        _build_current_window_calibration_protocol_v2_body,
        current_window_calibration_protocol_v2_payload,
    )
    from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
    from rulespace_v3.parent_freeze_v2 import (
        _build_reviewed_unchanged_scenario_authorities,
    )
    from rulespace_v3.registry import closed_control_registry_payload
    from rulespace_v3.task8_control_replay import (
        _build_current_control_registry_v2_body,
        _replay_current_task8_control_roots,
        current_control_registry_v2_payload,
    )
    from rulespace_v3.window import window_calibration_protocol_payload

    parent = issue_v3m0_parent_freeze()
    authorities = tuple(
        item
        for item in _build_reviewed_unchanged_scenario_authorities()
        if item.control_case_id.startswith(("C01_", "C02_", "C03_"))
    )
    replay = _replay_current_task8_control_roots(parent, authorities)
    current_registry_record = _build_current_control_registry_v2_body(
        SHAA,
        replay,
    )
    current_window_record = _build_current_window_calibration_protocol_v2_body(
        current_registry_record,
        replay,
    )
    legacy_registry_record = replay.legacy_registry.registry
    legacy_window_record = current_window_record.legacy_window_protocol
    legacy_registry = {
        **closed_control_registry_payload(legacy_registry_record),
        "registry_sha": legacy_registry_record.registry_sha,
    }
    legacy_window = {
        **window_calibration_protocol_payload(legacy_window_record),
        "protocol_sha": legacy_window_record.protocol_sha,
    }
    current_registry = {
        **current_control_registry_v2_payload(current_registry_record),
        "registry_sha": current_registry_record.registry_sha,
    }
    current_window = {
        **current_window_calibration_protocol_v2_payload(current_window_record),
        "protocol_sha": current_window_record.protocol_sha,
    }
    return (
        legacy_registry,
        legacy_window,
        current_registry,
        current_window,
        parent.manifest.parent_freeze_sha,
        tuple(item.scenario_authority_sha for item in authorities),
    )


def _legacy_root_wires() -> tuple[dict[str, object], dict[str, object]]:
    legacy_registry, legacy_window, *_ = _real_root_wire_snapshot()
    return copy.deepcopy(legacy_registry), copy.deepcopy(legacy_window)


def _current_root_wires() -> tuple[dict[str, object], dict[str, object]]:
    _, _, current_registry, current_window, _, _ = _real_root_wire_snapshot()
    return copy.deepcopy(current_registry), copy.deepcopy(current_window)


def _outcome_payload(*, resolved: bool = False) -> dict[str, object]:
    legacy_registry, legacy_window = _legacy_root_wires()
    candidates = []
    for order in T_CANDIDATES:
        selected = resolved and order == T_CANDIDATES[2]
        controls = []
        for index, control_id in enumerate(("full", "zero", "direct_sum")):
            entry_sha = legacy_registry["entries"][index]["entry_sha"]
            declaration_sha = (str(index + 7) * 64)[:64]
            candidate_t = _attempt(order, str(index + 1), entry_sha)
            comparison_2t = _attempt(2 * order, str(index + 4), entry_sha)

            def spectra(attempt, spectrum_order):
                pair_sha = attempt["attempt_audit"]["paired_response_outcome"][
                    "paired_response"
                ]["pair_sha"]
                return [
                    _spectrum(
                        kind,
                        order=spectrum_order,
                        entry_sha=entry_sha,
                        declaration_sha=declaration_sha,
                        run_spec_sha=attempt["run_spec"]["spec_sha"],
                        paired_response_sha=pair_sha,
                    )
                    for kind in ("h", "curv")
                ]

            controls.append(
                {
                    "control_registry_entry": {
                        **copy.deepcopy(legacy_registry["entries"][index]),
                    },
                    "expected_rank_declaration": {"declaration_sha": declaration_sha},
                    "candidate_t": candidate_t,
                    "comparison_2t": comparison_2t,
                    "phase_separation": float(order) / 10.0,
                    "overlap_margin": 0.25 + index / 100.0,
                    "projector_t2t_distance": 1.0e-13 * (index + 1),
                    "passed": True,
                    "audit_sha": SHA0,
                    "readout_spectrum_audits": spectra(candidate_t, order),
                    "comparison_2t_readout_spectrum_audits": spectra(
                        comparison_2t,
                        2 * order,
                    ),
                }
            )
            controls[-1]["audit_sha"] = canonical_sha(
                {
                    key: value
                    for key, value in controls[-1].items()
                    if key != "audit_sha"
                }
            )
        candidate_body = {
            "fejer_order": order,
            "control_audits": controls,
            "readout_aggregate_audits": [
                _aggregate(
                    kind,
                    order,
                    per_control=[
                        next(
                            item
                            for item in control["readout_spectrum_audits"]
                            if item["readout_kind"] == kind
                        )
                        for control in controls
                    ],
                    gates_passed=selected,
                )
                for kind in ("h", "curv")
            ],
            "passed": selected,
        }
        candidates.append(
            {**candidate_body, "audit_sha": canonical_sha(candidate_body)}
        )
    selection = None
    status = {"defined": False, "reason": "window_unresolved"}
    if resolved:
        selection = _selection_for_candidate(candidates[2])
        status = {"defined": True, "reason": None}
    manifest_body = {
        "calibration_schema_version": ("v3m0.window-threshold-calibration-manifest.v1"),
        "control_registry": legacy_registry,
        "window_protocol": legacy_window,
        "candidate_audits": candidates,
    }
    return {
        "status": status,
        "manifest": {
            **manifest_body,
            "calibration_manifest_sha": canonical_sha(manifest_body),
        },
        "selection": selection,
    }


def _provenance() -> dict[str, object]:
    from rulespace_v3.task11_evidence import (
        TASK11_RAW_REPLAY_REPOSITORY_MEASUREMENT_SCOPE,
        TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS,
        TASK11_RAW_REPLAY_SCOPE,
    )

    runtime_source_sha = hashlib.sha256(b"rulespace_v3/runtime.py").hexdigest()
    runtime_body = {
        "runtime_schema_version": "v3m0.runtime-evidence-manifest.v1",
        "evaluator_id": "rulespace-v3m0-certificate-closure-v1",
        "source_closure": [
            {
                "relative_path": "rulespace_v3/runtime.py",
                "sha256": runtime_source_sha,
            }
        ],
        "python_version": "3.11-test",
        "numpy_version": "2-test",
        "scipy_version": "1-test",
        "blas_config_sha": SHAB,
        "lapack_config_sha": SHAC,
        "platform_id": "test-platform",
    }
    runtime_manifest = {
        **runtime_body,
        "runtime_manifest_sha": canonical_sha(runtime_body),
    }
    legacy_registry, legacy_window = _legacy_root_wires()
    current_registry, current_window = _current_root_wires()
    _, _, _, _, historical_parent_sha, scenario_shas = _real_root_wire_snapshot()

    return {
        "replay_scope": TASK11_RAW_REPLAY_SCOPE,
        "historical_parent_v1_sha": historical_parent_sha,
        "placeholder_parent_freeze_v2_sha": SHAA,
        "legacy_registry_sha": legacy_registry["registry_sha"],
        "current_control_registry_sha": current_registry["registry_sha"],
        "legacy_window_protocol_sha": legacy_window["protocol_sha"],
        "current_window_protocol_sha": current_window["protocol_sha"],
        "current_control_registry": current_registry,
        "current_window_protocol": current_window,
        "scenario_authority_shas": list(scenario_shas),
        "git_head": "9" * 40,
        "git_worktree_dirty": False,
        "git_status_porcelain_sha256": hashlib.sha256(b"").hexdigest(),
        "source_files": [
            {
                "relative_path": relative_path,
                "sha256": hashlib.sha256(relative_path.encode()).hexdigest(),
            }
            for relative_path in TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS
        ],
        "runtime_manifest": runtime_manifest,
        "repository_measurement_scope": (
            TASK11_RAW_REPLAY_REPOSITORY_MEASUREMENT_SCOPE
        ),
        "command": ["python", "experiments/v3m0_task11_raw_replay.py"],
    }


def _offline_integrity_fixture_claiming_default_producer(
    *,
    outcome: dict[str, object] | None = None,
    provenance: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build serialized test bytes; deliberately proves no production call."""

    from rulespace_v3.task11_evidence import (
        TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM,
        _build_task11_raw_replay_integrity_payload,
    )

    raw_outcome = _outcome_payload() if outcome is None else outcome
    raw_provenance = _provenance() if provenance is None else provenance
    return _build_task11_raw_replay_integrity_payload(
        raw_outcome,
        outcome_sha=canonical_sha(raw_outcome),
        provenance=raw_provenance,
        creation_validation_claim=TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM,
    )


class Task11RawReplayEvidenceTests(unittest.TestCase):
    def test_v2_creation_factory_requires_exact_records_and_validator_first(
        self,
    ) -> None:
        from rulespace_v3.task11_evidence import (
            TASK11_RAW_REPLAY_PRODUCTION_VALIDATION_PROOF,
            _TEST_ONLY_CREATION_VALIDATION_CLAIM,
            _make_task11_raw_replay_creation_builder,
            verify_task11_raw_replay_evidence_payload,
        )

        class FakeOutcome:
            __slots__ = ("attack", "outcome_sha", "payload")

            def __init__(self, payload, attack=None):
                self.payload = payload
                self.attack = attack
                self.outcome_sha = canonical_sha(payload)

        class FakeRegistry:
            __slots__ = ()

        class FakeProtocol:
            __slots__ = ()

        calls = []

        def validator(outcome, registry, protocol):
            calls.append(("validate", outcome.attack, registry, protocol))
            if outcome.attack is not None:
                raise ValueError(f"production validator rejected {outcome.attack}")

        def encoder(outcome):
            calls.append(("encode", outcome.attack))
            return copy.deepcopy(outcome.payload)

        builder = _make_task11_raw_replay_creation_builder(
            outcome_type=FakeOutcome,
            registry_type=FakeRegistry,
            protocol_type=FakeProtocol,
            validator=validator,
            payload_encoder=encoder,
        )
        registry = FakeRegistry()
        protocol = FakeProtocol()
        valid = FakeOutcome(_outcome_payload())
        evidence = builder(valid, registry, protocol, provenance=_provenance())
        self.assertEqual(
            calls[:2],
            [("validate", None, registry, protocol), ("encode", None)],
        )
        self.assertEqual(
            evidence["creation_validation_claim"],
            _TEST_ONLY_CREATION_VALIDATION_CLAIM,
        )
        self.assertEqual(
            evidence["production_validation_proof"],
            TASK11_RAW_REPLAY_PRODUCTION_VALIDATION_PROOF,
        )
        with self.assertRaisesRegex(ValueError, "creation_validation_claim"):
            verify_task11_raw_replay_evidence_payload(evidence)

        for attack in ("negative_aggregate", "outer_inner_failure", "spectrum"):
            calls.clear()
            with self.subTest(attack=attack):
                with self.assertRaisesRegex(ValueError, "production validator"):
                    builder(
                        FakeOutcome(_outcome_payload(), attack),
                        registry,
                        protocol,
                        provenance=_provenance(),
                    )
                self.assertEqual(calls[0][0], "validate")
                self.assertFalse(any(item[0] == "encode" for item in calls))

        with self.assertRaisesRegex(TypeError, "WindowCalibrationOutcome|outcome"):
            builder(_outcome_payload(), registry, protocol, provenance=_provenance())
        with self.assertRaisesRegex(TypeError, "registry"):
            builder(valid, object(), protocol, provenance=_provenance())
        with self.assertRaisesRegex(TypeError, "protocol"):
            builder(valid, registry, object(), provenance=_provenance())

    def test_provenance_requires_runtime_authority_order_git_digest_and_overlap(
        self,
    ) -> None:
        from rulespace_v3.runtime import RUNTIME_EVALUATOR_ID, RUNTIME_SCHEMA_VERSION
        from rulespace_v3.task11_evidence import (
            TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM,
            _build_task11_raw_replay_integrity_payload,
            verify_task11_raw_replay_evidence_payload,
        )

        baseline = _offline_integrity_fixture_claiming_default_producer()
        self.assertEqual(
            verify_task11_raw_replay_evidence_payload(baseline),
            baseline,
        )
        self.assertEqual(
            baseline["provenance"]["runtime_manifest"]["runtime_schema_version"],
            RUNTIME_SCHEMA_VERSION,
        )
        self.assertEqual(
            baseline["provenance"]["runtime_manifest"]["evaluator_id"],
            RUNTIME_EVALUATOR_ID,
        )

        def assemble(provenance):
            outcome = _outcome_payload()
            return _build_task11_raw_replay_integrity_payload(
                outcome,
                outcome_sha=canonical_sha(outcome),
                provenance=provenance,
                creation_validation_claim=(TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM),
            )

        wrong_runtime = _provenance()
        wrong_runtime["runtime_manifest"]["runtime_schema_version"] = (
            "v3m0.runtime-evidence.v1"
        )
        _rehash(wrong_runtime["runtime_manifest"], "runtime_manifest_sha")
        with self.assertRaisesRegex(ValueError, "runtime_schema_version"):
            assemble(wrong_runtime)

        reordered = _provenance()
        reordered["source_files"][0], reordered["source_files"][1] = (
            reordered["source_files"][1],
            reordered["source_files"][0],
        )
        with self.assertRaisesRegex(ValueError, "closure order"):
            assemble(reordered)

        overlap_splice = _provenance()
        overlap_splice["runtime_manifest"]["source_closure"][0]["sha256"] = SHAF
        _rehash(overlap_splice["runtime_manifest"], "runtime_manifest_sha")
        with self.assertRaisesRegex(ValueError, "overlap SHA mismatch"):
            assemble(overlap_splice)

        bad_git_digest = _provenance()
        bad_git_digest["git_status_porcelain_sha256"] = "not-a-sha"
        with self.assertRaisesRegex(ValueError, "git_status_porcelain_sha256"):
            assemble(bad_git_digest)

        contradictory_git_state = _provenance()
        contradictory_git_state["git_status_porcelain_sha256"] = SHAF
        with self.assertRaisesRegex(ValueError, "dirty/status digest"):
            assemble(contradictory_git_state)

    def test_required_source_paths_cover_the_fresh_import_replay_closure(
        self,
    ) -> None:
        from rulespace_v3.task11_evidence import (
            TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS,
        )

        expected_additional = {
            "experiments/__init__.py",
            "experiments/r10_current_generator.py",
            "rulespace_v3/application_recipes.py",
            "rulespace_v3/blocks.py",
            "rulespace_v3/c05_projector_recipe.py",
            "rulespace_v3/c12_incidence_preflight.py",
            "rulespace_v3/candidate_scenario_dag.py",
            "rulespace_v3/geometry.py",
            "rulespace_v3/geometry_application_recipes.py",
            "rulespace_v3/interference_mode_preflight.py",
            "rulespace_v3/linalg.py",
            "rulespace_v3/parent_authority.py",
            "rulespace_v3/parent_candidate_v2.py",
            "rulespace_v3/parent_v2_contracts.py",
        }
        self.assertLessEqual(
            expected_additional,
            set(TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS),
        )
        self.assertEqual(
            len(TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS),
            len(set(TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS)),
        )

    def test_current_and_historical_roots_reject_fully_resigned_splices(
        self,
    ) -> None:
        from rulespace_v3.task11_evidence import (
            verify_task11_raw_replay_evidence_payload,
        )

        evidence = _offline_integrity_fixture_claiming_default_producer()

        declared_only = copy.deepcopy(evidence)
        declared_only["provenance"]["current_control_registry_sha"] = SHAF
        _rehash(declared_only, "evidence_sha")

        scenario_splice = copy.deepcopy(evidence)
        provenance = scenario_splice["provenance"]
        provenance["scenario_authority_shas"][0] = SHAF
        current_registry = provenance["current_control_registry"]
        entry = current_registry["entries"][0]
        entry["scenario_authority_sha"] = SHAF
        _rehash(entry, "entry_sha")
        _rehash(current_registry, "registry_sha")
        provenance["current_control_registry_sha"] = current_registry["registry_sha"]
        current_window = provenance["current_window_protocol"]
        current_window["current_control_registry"] = copy.deepcopy(current_registry)
        binding = current_window["control_bindings"][0]
        binding["current_registry_entry_sha"] = entry["entry_sha"]
        binding["scenario_authority_sha"] = SHAF
        _rehash(binding, "binding_sha")
        _rehash(current_window, "protocol_sha")
        provenance["current_window_protocol_sha"] = current_window["protocol_sha"]
        _rehash(scenario_splice, "evidence_sha")

        outcome_splice = copy.deepcopy(evidence)
        outcome_splice["outcome"]["manifest"]["control_registry"]["registry_sha"] = SHAF
        _rehash(outcome_splice["outcome"]["manifest"], "calibration_manifest_sha")
        outcome_splice["outcome_sha"] = canonical_sha(outcome_splice["outcome"])
        _rehash(outcome_splice, "evidence_sha")

        for label, attacked in (
            ("declared current registry", declared_only),
            ("scenario full tree", scenario_splice),
            ("outcome/provenance link", outcome_splice),
        ):
            with self.subTest(attack=label):
                with self.assertRaisesRegex(
                    (TypeError, ValueError),
                    "root|registry|scenario|SHA|snapshot",
                ):
                    verify_task11_raw_replay_evidence_payload(attacked)

    def test_frozen_offline_verifier_ignores_rebound_status_labels(self) -> None:
        import rulespace_v3.task11_evidence as evidence_module

        verifier = evidence_module.verify_task11_raw_replay_evidence_payload
        valid = _offline_integrity_fixture_claiming_default_producer()
        rebound_labels = {
            "TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION": "forged.schema",
            "TASK11_RAW_REPLAY_AUTHORITY_STATE": "SCIENTIFIC_PASS",
            "TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT": "PASS",
            "TASK11_RAW_REPLAY_CREATE_POLICY": "OVERWRITE",
            "_ENGINEERING_SCOPE": "FORGED_ENGINEERING_SCOPE",
            "_CLAIM_SCOPE": "SCIENTIFIC_PASS",
        }
        with mock.patch.multiple(evidence_module, **rebound_labels):
            self.assertEqual(verifier(valid), valid)

        forged = copy.deepcopy(valid)
        key_map = {
            "TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION": "evidence_schema_version",
            "TASK11_RAW_REPLAY_AUTHORITY_STATE": "authority_state",
            "TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT": "scientific_verdict",
            "TASK11_RAW_REPLAY_CREATE_POLICY": "create_policy",
            "_ENGINEERING_SCOPE": "engineering_contract_scope",
            "_CLAIM_SCOPE": "claim_scope",
        }
        for source_name, forged_value in rebound_labels.items():
            forged[key_map[source_name]] = forged_value
        _rehash(forged, "evidence_sha")
        with mock.patch.multiple(evidence_module, **rebound_labels):
            with self.assertRaisesRegex(ValueError, "drifted"):
                verifier(forged)

    def test_offline_verifier_is_integrity_only_and_accepts_resigned_semantics(
        self,
    ) -> None:
        from rulespace_v3.task11_evidence import (
            TASK11_RAW_REPLAY_OFFLINE_VERIFICATION_SCOPE,
            TASK11_RAW_REPLAY_PRODUCTION_VALIDATION_PROOF,
            verify_task11_raw_replay_evidence_payload,
        )

        outcome = _outcome_payload(resolved=True)
        valid = _offline_integrity_fixture_claiming_default_producer(outcome=outcome)
        self.assertFalse(valid["current_parent_v2_bound"])
        self.assertEqual(valid["scientific_verdict"], "NOT_ISSUED")
        self.assertEqual(
            valid["offline_verification_scope"],
            TASK11_RAW_REPLAY_OFFLINE_VERIFICATION_SCOPE,
        )
        self.assertEqual(
            valid["production_validation_proof"],
            TASK11_RAW_REPLAY_PRODUCTION_VALIDATION_PROOF,
        )
        self.assertEqual(verify_task11_raw_replay_evidence_payload(valid), valid)

        unsigned_tamper = copy.deepcopy(valid)
        unsigned_tamper["outcome"]["status"]["defined"] = False
        with self.assertRaisesRegex(ValueError, "outcome SHA"):
            verify_task11_raw_replay_evidence_payload(unsigned_tamper)

        resigned_invalid = copy.deepcopy(valid)
        candidate = resigned_invalid["outcome"]["manifest"]["candidate_audits"][2]
        aggregate = candidate["readout_aggregate_audits"][0]
        aggregate["signal_min"] = -1.0
        _rehash(aggregate, "aggregate_sha")
        _rehash(candidate, "audit_sha")
        _rehash(resigned_invalid["outcome"]["manifest"], "calibration_manifest_sha")
        resigned_invalid["outcome_sha"] = canonical_sha(resigned_invalid["outcome"])
        _rehash(resigned_invalid, "evidence_sha")
        verified = verify_task11_raw_replay_evidence_payload(resigned_invalid)
        self.assertEqual(
            verified["outcome"]["manifest"]["candidate_audits"][2][
                "readout_aggregate_audits"
            ][0]["signal_min"],
            -1.0,
        )

    def test_integrity_assembler_rejects_wrong_sha_and_nonfinite_json(self) -> None:
        from rulespace_v3.task11_evidence import (
            TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM,
            _build_task11_raw_replay_integrity_payload,
        )

        outcome = _outcome_payload()
        with self.assertRaisesRegex(ValueError, "outcome SHA"):
            _build_task11_raw_replay_integrity_payload(
                outcome,
                outcome_sha=SHAF,
                provenance=_provenance(),
                creation_validation_claim=(TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM),
            )
        nonfinite = copy.deepcopy(outcome)
        nonfinite["manifest"]["candidate_audits"][0]["readout_aggregate_audits"][0][
            "signal_min"
        ] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite plain JSON"):
            _build_task11_raw_replay_integrity_payload(
                nonfinite,
                outcome_sha=canonical_sha(outcome),
                provenance=_provenance(),
                creation_validation_claim=(TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM),
            )

    def test_writer_is_atomic_create_only_and_keeps_existing_bytes(self) -> None:
        from experiments.v3m0_task11_raw_replay import (
            write_task11_raw_replay_evidence_create_only,
        )
        from rulespace_v3.task11_evidence import (
            verify_task11_raw_replay_evidence_payload,
        )

        evidence = _offline_integrity_fixture_claiming_default_producer()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "task11.json"
            write_task11_raw_replay_evidence_create_only(output, evidence)
            self.assertEqual(
                verify_task11_raw_replay_evidence_payload(
                    json.loads(output.read_text(encoding="utf-8"))
                ),
                evidence,
            )
            original = output.read_bytes()
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                write_task11_raw_replay_evidence_create_only(output, evidence)
            self.assertEqual(output.read_bytes(), original)

    def test_cli_has_no_public_execute_injection_and_preflights_create_only(
        self,
    ) -> None:
        import experiments.v3m0_task11_raw_replay as replay_module
        from rulespace_v3.task11_evidence import (
            build_task11_raw_replay_evidence_payload,
        )

        self.assertEqual(
            tuple(inspect.signature(replay_module.run_raw_replay).parameters),
            ("output", "command"),
        )
        self.assertEqual(
            tuple(
                inspect.signature(build_task11_raw_replay_evidence_payload).parameters
            ),
            ("outcome", "registry", "protocol", "provenance"),
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "already.json"
            output.write_text("existing", encoding="utf-8")
            with mock.patch.object(
                replay_module,
                "execute_raw_historical_replay",
            ) as execute:
                with self.assertRaisesRegex(FileExistsError, "already exists"):
                    replay_module.run_raw_replay(output)
                execute.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "existing")

    def test_source_provenance_hashes_exact_git_status_bytes(self) -> None:
        import experiments.v3m0_task11_raw_replay as replay_module

        status_bytes = b" M rulespace_v3/task11_evidence.py\\n?? scratch\\n"

        def git_output(*arguments):
            if arguments[0] == "status":
                return status_bytes
            if arguments == ("rev-parse", "HEAD"):
                return b"9" * 40 + b"\\n"
            raise AssertionError(arguments)

        with mock.patch.object(
            replay_module,
            "_git_output_bytes",
            side_effect=git_output,
        ):
            provenance = replay_module._source_provenance(("python", "task11.py"))
        self.assertTrue(provenance["git_worktree_dirty"])
        self.assertEqual(
            provenance["git_status_porcelain_sha256"],
            hashlib.sha256(status_bytes).hexdigest(),
        )
        self.assertEqual(
            tuple(item["relative_path"] for item in provenance["source_files"]),
            tuple(replay_module.TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS),
        )

    def test_long_replay_rejects_pre_post_repository_provenance_drift(
        self,
    ) -> None:
        from experiments.v3m0_task11_raw_replay import (
            _execute_with_stable_source_provenance,
        )

        stable_measurements = [
            {"source": "same", "git_status_porcelain_sha256": SHAA},
            {"source": "same", "git_status_porcelain_sha256": SHAA},
        ]
        seen = []
        result = _execute_with_stable_source_provenance(
            ("python", "task11.py"),
            lambda source: seen.append(source) or "raw-result",
            measure=lambda _command: stable_measurements.pop(0),
        )
        self.assertEqual(result, "raw-result")
        self.assertEqual(
            seen,
            [{"source": "same", "git_status_porcelain_sha256": SHAA}],
        )

        drifting_measurements = [
            {"source": "before", "git_status_porcelain_sha256": SHAA},
            {"source": "after", "git_status_porcelain_sha256": SHAB},
        ]
        with self.assertRaisesRegex(RuntimeError, "provenance drifted"):
            _execute_with_stable_source_provenance(
                ("python", "task11.py"),
                lambda _source: "raw-result",
                measure=lambda _command: drifting_measurements.pop(0),
            )


def _rehash(mapping: dict[str, object], hash_name: str) -> None:
    mapping[hash_name] = canonical_sha(
        {key: value for key, value in mapping.items() if key != hash_name}
    )


if __name__ == "__main__":
    unittest.main()
