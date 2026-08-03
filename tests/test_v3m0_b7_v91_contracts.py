"""Static contracts for the frozen B7 v9.1 machine registry.

These tests read design registries and existing source bytes only.  They do not
import the future schema lab or the pure replay core, and therefore cannot mint
an authority, execute a route, or issue a scientific status.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "docsv3" / "v3-机器合同-B7-v9.1-registry.json"
REGISTRY_RAW_SHA256 = "222cd47e95de63eaedee41f6ca4b207a0eccceb7a77089aed43a480a77f69d72"
PURE_REPLAY_PROJECTION_SHA256 = (
    "bafbaeb75e890715464c1fff6e6e0cbf1d4f56bb53a3817a9b2d12d2a3c27ff9"
)
GIT_HANDOFF_MECHANICAL_SHA256 = (
    "1fec7f8cdc26e7fef95706fb495d6b659ec32bad0d029ed0db6b9362d2a66845"
)
HALT_ARTIFACT_MATRIX_SHA256 = (
    "fd9872ddd1fe3ce91eedc5d93bc78805bef35bfa4a9857bbe9bb43fccc68da56"
)
REPLAY_REPORT_MECHANICAL_SHA256 = (
    "99064f0f2122e9e3a2499464fa084178aeef15caa503f175f9bad30fe2a4ecd1"
)

BASE_CONTRACTS = {
    "v6": {
        "path": "docsv3/v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md",
        "registry_schema_version": ("v3m0.parent-v3-downstream-contract-registry.v6"),
        "raw_sha256": (
            "fd654e76ea143503916b45e1eec6456eab3f014e1e8ba02b826f6c62bb42e91f"
        ),
        "ordered_registry_sha256": (
            "f7af99b8b1621c2afbe73ae5553aeb4044080f0ed6a408573e324ecc202fb256"
        ),
    },
    "v7": {
        "path": (
            "docsv3/v3-设计勘误-Parent-v3-prestructure-production-chain-v7-2026-08-02.md"
        ),
        "registry_schema_version": (
            "v3m0.parent-v3-prestructure-production-chain-delta.v7"
        ),
        "raw_sha256": (
            "a6b83b08b57bccf09fd78e95a1a63d2c0b49339cb29dbd6e6ff07cb19eb512f4"
        ),
        "ordered_registry_sha256": (
            "a3a506a5b3ddbf245332fe3dc28f848af3db02f24e31cfd1d2b6f43e46d437e3"
        ),
    },
    "v8": {
        "path": (
            "docsv3/v3-设计勘误-Parent-v3-B7至B10-production-chain-v8-2026-08-02.md"
        ),
        "registry_schema_version": ("v3m0.parent-v3-b7-b10-production-chain-delta.v8"),
        "raw_sha256": (
            "e55445b50c2a885b8cd4a2ab1e9e3066c9632445d6860b508ab56a422f66f3ae"
        ),
        "ordered_registry_sha256": (
            "bb0e34718b371e10d8bd83cb2306905d5b0445480c3b9df7ebcc3f83f879c3a8"
        ),
    },
    "v9": {
        "path": (
            "docsv3/v3-设计勘误-B7三路线并行对照与production收敛-v9-2026-08-03.md"
        ),
        "raw_sha256": (
            "1803dc0b9d400a7e2e1d7876f15c0da9c4743d9e16676ba0377e35eaa4c7a9e9"
        ),
    },
}

EMBEDDED_REGISTRY_MARKERS = {
    "v6": (
        "<!-- BEGIN V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->",
        "<!-- END V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->",
    ),
    "v7": (
        "<!-- BEGIN V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->",
        "<!-- END V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->",
    ),
    "v8": (
        "<!-- BEGIN V3M0_PARENT_V3_B7_B10_V8_REGISTRY -->",
        "<!-- END V3M0_PARENT_V3_B7_B10_V8_REGISTRY -->",
    ),
}

EXACT_RECORD_NAMES = (
    "B7LabEnvironmentManifestV1",
    "B7LabProvenanceFixtureV1",
    "B7LabBranchAttemptV1",
    "B7LeafDigestV1",
    "NormalizedB7ExecutionTranscriptV1",
    "B7LabCorpusCaseV1",
    "B7LabNestedBodyRuleV1",
    "B7LabCorpusSpecV1",
    "B7LabCorpusFixtureV1",
    "B7LabMutationV1",
    "B7LabMutationUniverseV1",
    "B7LabRouteManifestV1",
    "B7LabGateObservationV1",
    "B7LabGateOutcomeV1",
    "B7LabD0RouteResultV1",
    "B7LabD0ComparisonV1",
    "B7LabMetricSpecV1",
    "B7LabSyntheticComponentBodyV1",
    "B7LabTBearerBindingV1",
    "B7LabSyntheticGraphManifestV1",
    "B7LabMetricVectorV1",
    "B7LabCrossReplayCellV1",
    "B7LabD1RouteResultV1",
    "B7LabD1ComparisonV1",
    "B7LabReplayReportV1",
    "B7LabReviewerReceiptV1",
    "B7LabReviewHaltV1",
    "B7LabSelectionReviewV1",
    "B7ProductionHandoffReviewV1",
)

VALIDATOR_IDS = (
    "validate_d0_decision_payload_projection_v1",
    "validate_d1_decision_payload_projection_v1",
    "validate_corpus_fixture_v1",
    "validate_response_run_spec_fixture_v1",
    "validate_endpoint_reference_outcome_raw_v1",
    "validate_endpoint_shell_outcome_raw_v1",
    "validate_source_readout_response_raw_v1",
    "validate_route_static_surface_v1",
    "validate_synthetic_parent_freeze_v3_body_v1",
    "validate_synthetic_component_body_v1",
    "validate_gate_e01_v1",
    "validate_gate_e02_v1",
    "validate_gate_e03_v1",
    "validate_gate_e04_v1",
    "validate_gate_e05_v1",
    "validate_gate_e06_v1",
    "validate_gate_e07_v1",
    "validate_gate_e08_v1",
    "validate_provenance_fixture_v1",
    "validate_branch_attempt_v1",
    "validate_case_contract_v1",
    "validate_d0_route_result_v1",
    "validate_d0_comparison_v1",
    "validate_synthetic_graph_manifest_v1",
    "validate_d1_route_result_v1",
    "validate_d1_comparison_v1",
    "validate_reviewer_child_static_surface_v1",
    "validate_reviewer_executable_source_origin_v1",
    "validate_reviewer_receipt_v1",
    "validate_review_halt_v1",
    "validate_selection_review_v1",
    "validate_production_handoff_v1",
)

PURE_CORE_VALIDATOR_IDS = (
    "validate_response_run_spec_fixture_v1",
    "validate_endpoint_reference_outcome_raw_v1",
    "validate_endpoint_shell_outcome_raw_v1",
    "validate_source_readout_response_raw_v1",
    "validate_synthetic_parent_freeze_v3_body_v1",
    "validate_synthetic_component_body_v1",
    "validate_provenance_fixture_v1",
    "validate_branch_attempt_v1",
)

RECEIPT_FIELDS = (
    "receipt_schema_version",
    "reviewer_id",
    "reviewer_role",
    "review_protocol_id",
    "reviewed_lab_evidence_commit_sha",
    "review_environment_manifest_sha",
    "observed_review_environment_manifest_sha",
    "review_environment_precheck_passed",
    "reviewed_d0_result_raw_sha256",
    "reviewed_d0_result_sha",
    "reviewed_d0_decision_payload_sha",
    "reviewed_d1_result_raw_sha256",
    "reviewed_d1_result_sha",
    "reviewed_d1_decision_payload_sha",
    "reviewed_common_commit_sha",
    "reviewed_route_commit_shas",
    "reviewed_corpus_spec_sha",
    "reviewed_mutation_universe_sha",
    "reviewed_metric_spec_sha",
    "reviewed_compare_source_sha256",
    "reviewed_executable_source_closure_sha",
    "observed_executable_source_closure_sha",
    "executable_source_origin_precheck_passed",
    "replay_source_path",
    "replay_source_sha256",
    "replay_command_argv",
    "fresh_process_protocol_id",
    "replay_input_root_sha",
    "observed_report_reviewer_role",
    "observed_report_review_protocol_id",
    "observed_report_lab_evidence_commit_sha",
    "observed_report_replay_input_root_sha",
    "replay_output_root_sha",
    "replay_stdout_sha256",
    "replay_stderr_sha256",
    "replay_termination_kind",
    "replay_exit_code",
    "replay_signal_number",
    "replayed_d0_decision_payload_sha",
    "replayed_d1_decision_payload_sha",
    "observed_surviving_route_ids",
    "observed_provisional_winner_route_id",
    "verdict",
    "reason_codes",
    "receipt_sha",
)

REVIEW_REASON_CODES = (
    "REVIEW_ENVIRONMENT_MISMATCH",
    "REPLAY_SOURCE_MISMATCH",
    "REPLAY_EXECUTABLE_SOURCE_ORIGIN_MISMATCH",
    "REPLAY_INPUT_ROOT_MISMATCH",
    "REPLAY_PROCESS_PRECHECK_FAILED",
    "REPLAY_PROCESS_SPAWN_FAILED",
    "REPLAY_PROCESS_OUTPUT_LIMIT_EXCEEDED",
    "REPLAY_PROCESS_TIMED_OUT",
    "REPLAY_PROCESS_SIGNALED",
    "REPLAY_PROCESS_NONZERO",
    "REPLAY_PROCESS_CLEANUP_DEADLINE_EXCEEDED",
    "REPLAY_EXPORT_CLEANUP_FAILED",
    "REPLAY_STDOUT_NOT_CANONICAL_REPORT",
    "REPLAY_REPORT_IDENTITY_MISMATCH",
    "REPLAY_D0_DECISION_MISMATCH",
    "REPLAY_D1_DECISION_MISMATCH",
    "REPLAY_SURVIVOR_MISMATCH",
    "REPLAY_WINNER_MISMATCH",
)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def _strict_json_loads(raw: bytes) -> dict[str, object]:
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {value}")
        ),
        parse_float=_parse_finite_float,
    )
    assert type(value) is dict
    return value


def _load_frozen_registry() -> dict[str, object]:
    raw = REGISTRY_PATH.read_bytes()
    # The raw-byte identity gate deliberately precedes UTF-8 decoding and parse.
    assert hashlib.sha256(raw).hexdigest() == REGISTRY_RAW_SHA256
    return _strict_json_loads(raw)


def _load_embedded_registry(
    verified_raw: bytes, begin_marker: str, end_marker: str
) -> dict[str, object]:
    text = verified_raw.decode("utf-8")
    assert text.count(begin_marker) == 1
    assert text.count(end_marker) == 1
    block = text.split(begin_marker, 1)[1].split(end_marker, 1)[0].strip()
    assert block.startswith("```json\n") and block.endswith("\n```")
    return _strict_json_loads(
        block.removeprefix("```json\n").removesuffix("\n```").encode("utf-8")
    )


def _freeze_ordered_json(value: object) -> object:
    if type(value) is dict:
        return tuple((key, _freeze_ordered_json(item)) for key, item in value.items())
    if type(value) is list:
        return tuple(_freeze_ordered_json(item) for item in value)
    return value


def _ordered_digest(value: object) -> str:
    payload = json.dumps(
        _freeze_ordered_json(value),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_pointer(document: object, pointer: str) -> object:
    assert pointer.startswith("/")
    current = document
    for raw_token in pointer.removeprefix("/").split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if type(current) is dict:
            current = current[token]
        else:
            assert type(current) is list
            current = current[int(token)]
    return current


def _json_pointer_parent(
    document: object, pointer: str
) -> tuple[dict[str, object] | list[object], str | int]:
    assert pointer.startswith("/")
    tokens = [
        token.replace("~1", "/").replace("~0", "~")
        for token in pointer.removeprefix("/").split("/")
    ]
    assert tokens
    parent = document
    for token in tokens[:-1]:
        if type(parent) is dict:
            parent = parent[token]
        else:
            assert type(parent) is list
            parent = parent[int(token)]
    assert type(parent) in {dict, list}
    leaf: str | int = tokens[-1]
    if type(parent) is list:
        leaf = int(leaf)
    return parent, leaf


def _replace_pointer(document: object, pointer: str, replacement: object) -> None:
    parent, leaf = _json_pointer_parent(document, pointer)
    parent[leaf] = copy.deepcopy(replacement)


def _add_absent_pointer(document: object, pointer: str, replacement: object) -> None:
    parent, leaf = _json_pointer_parent(document, pointer)
    assert type(parent) is dict and type(leaf) is str
    assert leaf not in parent
    parent[leaf] = copy.deepcopy(replacement)


def _field_names(record: dict[str, object]) -> tuple[str, ...]:
    return tuple(field["name"] for field in record["field_specs"])


def _walk_strings(value: object) -> list[str]:
    if type(value) is str:
        return [value]
    if type(value) is list:
        return [item for child in value for item in _walk_strings(child)]
    if type(value) is dict:
        return [
            item
            for key, child in value.items()
            for item in (*_walk_strings(key), *_walk_strings(child))
        ]
    return []


def _record_body(record_delta: dict[str, object]) -> dict[str, object]:
    assert "operation" in record_delta
    return {key: value for key, value in record_delta.items() if key != "operation"}


def _load_verified_base_registries(
    registry: dict[str, object],
) -> dict[str, dict[str, object]]:
    loaded: dict[str, dict[str, object]] = {}
    for version, expected in BASE_CONTRACTS.items():
        assert registry["base_contracts"][version] == expected
        raw = (REPO_ROOT / expected["path"]).read_bytes()
        # This exact object is decoded and parsed below; the path is not read twice.
        assert hashlib.sha256(raw).hexdigest() == expected["raw_sha256"]
        if version not in EMBEDDED_REGISTRY_MARKERS:
            assert raw.decode("utf-8")
            continue
        begin, end = EMBEDDED_REGISTRY_MARKERS[version]
        base = _load_embedded_registry(raw, begin, end)
        assert base["registry_schema_version"] == expected["registry_schema_version"]
        assert _ordered_digest(base) == expected["ordered_registry_sha256"]
        loaded[version] = base
    assert tuple(loaded) == ("v6", "v7", "v8")
    return loaded


def _escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _diff_leaf_pointers(left: object, right: object, pointer: str = "") -> set[str]:
    if type(left) is not type(right):
        return {pointer or "/"}
    if type(left) is dict:
        differences: set[str] = set()
        for key in sorted(set(left) | set(right)):
            child = f"{pointer}/{_escape_pointer_token(key)}"
            if key not in left or key not in right:
                differences.add(child)
            else:
                differences.update(_diff_leaf_pointers(left[key], right[key], child))
        return differences
    if type(left) is list:
        if len(left) != len(right):
            return {pointer or "/"}
        differences = set()
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            differences.update(
                _diff_leaf_pointers(left_item, right_item, f"{pointer}/{index}")
            )
        return differences
    return set() if left == right else {pointer or "/"}


def _assert_mutation_closure(
    prior: dict[str, object],
    effective: dict[str, object],
    declared_roots: list[str],
) -> None:
    differences = _diff_leaf_pointers(prior, effective)
    assert differences
    assert len(declared_roots) == len(set(declared_roots))
    for difference in differences:
        assert any(
            difference == root or difference.startswith(f"{root}/")
            for root in declared_roots
        ), difference
    for root in declared_roots:
        assert any(
            difference == root or difference.startswith(f"{root}/")
            for difference in differences
        ), root


def _materialize_effective_v7(
    v6: dict[str, object], v7: dict[str, object]
) -> dict[str, object]:
    effective = copy.deepcopy(v6)
    merge = v7["effective_merge"]
    assert merge["algorithm"] == (
        "COPY_V6_THEN_APPLY_EXACT_JSON_POINTER_REPLACEMENTS_THEN_ADD_V7_DELTA"
    )
    assert merge["unlisted_v6_mutation_allowed"] is False
    assert merge["v7_delta_additions_apply_after_overrides"] is True
    declared_roots: list[str] = []

    for override in merge["json_pointer_overrides"]:
        assert set(override) == {
            "json_pointer",
            "operation",
            "expected_v6_value",
            "replacement_value",
        }
        assert override["operation"] == "REPLACE_EXACT"
        pointer = override["json_pointer"]
        assert _json_pointer(effective, pointer) == override["expected_v6_value"]
        _replace_pointer(effective, pointer, override["replacement_value"])
        declared_roots.append(pointer)

    for name, delta in v7["record_catalog_delta"].items():
        pointer = f"/record_catalog/{_escape_pointer_token(name)}"
        operation = delta["operation"]
        if operation == "ADD_V7_RECORD":
            _add_absent_pointer(effective, pointer, _record_body(delta))
        else:
            assert operation == "REPLACE_V6_RECORD"
            assert _json_pointer(effective, pointer)
            _replace_pointer(effective, pointer, _record_body(delta))
        declared_roots.append(pointer)

    field_replacement = v7["dynamics_certificate_v3_field_replacement"]
    assert field_replacement["operation"] == "REPLACE_V6_FIELD_TYPE"
    record = effective["record_catalog"][field_replacement["record"]]
    field_index, field = next(
        (index, field)
        for index, field in enumerate(record["field_specs"])
        if field["name"] == field_replacement["field"]
    )
    assert field["wire_type"] == field_replacement["old_wire_type"]
    assert field["nested_record"] == field_replacement["old_nested_record"]
    assert field["presence"] == field_replacement["presence"]
    field["wire_type"] = field_replacement["new_wire_type"]
    field["nested_record"] = field_replacement["new_nested_record"]
    field["constraints"] = copy.deepcopy(field_replacement["constraints"])
    declared_roots.append(
        f"/record_catalog/{field_replacement['record']}/field_specs/{field_index}"
    )

    assert len(merge["json_pointer_overrides"]) == 2
    assert len(v7["record_catalog_delta"]) == 2
    assert len(declared_roots) == 5
    _assert_mutation_closure(v6, effective, declared_roots)
    return effective


def _apply_relative_patches(
    prior: object, repair: dict[str, object]
) -> dict[str, object]:
    assert type(prior) is dict
    repaired = copy.deepcopy(prior)
    assert repair["operation"] == "RESTORE_EXACT_PRODUCTION_SOURCE"
    assert repair["legacy_byte_and_sha_compatibility_required"] is True
    for patch in repair["record_patch"]:
        assert set(patch) == {
            "relative_pointer",
            "expected_prior_value",
            "replacement_value",
        }
        parent, leaf = _json_pointer_parent(repaired, patch["relative_pointer"])
        assert parent[leaf] == patch["expected_prior_value"]
        parent[leaf] = copy.deepcopy(patch["replacement_value"])
    assert repaired["schema_id"] == repair["schema_id"]
    assert repaired["canonical_owner"] == repair["canonical_owner"]
    assert [field["name"] for field in repaired["field_specs"]] == [
        field["name"] for field in repair["source_field_annotations"]
    ]
    return repaired


def _resolve_v8_replacement(
    v8: dict[str, object], replacement_ref: str, prior: object
) -> object:
    replacement = _json_pointer(v8, replacement_ref)
    if replacement_ref.startswith("/legacy_record_repairs/"):
        assert type(replacement) is dict
        return _apply_relative_patches(prior, replacement)
    if type(replacement) is dict and "operation" in replacement:
        return _record_body(replacement)
    return copy.deepcopy(replacement)


def _materialize_effective_v8(
    effective_v7: dict[str, object], v8: dict[str, object]
) -> dict[str, object]:
    effective = copy.deepcopy(effective_v7)
    merge = v8["effective_merge"]
    assert merge["algorithm"] == (
        "VERIFY_V6_AND_V7_THEN_MATERIALIZE_EFFECTIVE_V7_AND_APPLY_ORDERED_V8"
    )
    assert merge["unlisted_prior_mutation_allowed"] is False
    assert merge["replacement_ref_resolution"] == (
        "task_delta and record_catalog_delta refs replace with the referenced object "
        "after stripping operation; legacy_record_repairs refs apply their ordered "
        "record_patch to the prior record and then require exact "
        "source_field_annotations"
    )
    replacements = merge["replace_exact_sha256"]
    additions = merge["add_absent"]
    assert len(replacements) == 26
    assert len(additions) == 40
    declared_roots: list[str] = []
    used_refs: list[str] = []

    for operation in replacements:
        assert set(operation) == {
            "json_pointer",
            "operation",
            "expected_prior_value_sha256",
            "replacement_ref",
        }
        assert operation["operation"] == "REPLACE_EXACT_SHA256"
        pointer = operation["json_pointer"]
        prior = _json_pointer(effective, pointer)
        assert _ordered_digest(prior) == operation["expected_prior_value_sha256"]
        replacement = _resolve_v8_replacement(v8, operation["replacement_ref"], prior)
        _replace_pointer(effective, pointer, replacement)
        declared_roots.append(pointer)
        used_refs.append(operation["replacement_ref"])

    for operation in additions:
        assert set(operation) == {"json_pointer", "operation", "replacement_ref"}
        assert operation["operation"] == "ADD_ABSENT"
        pointer = operation["json_pointer"]
        replacement = _resolve_v8_replacement(v8, operation["replacement_ref"], {})
        _add_absent_pointer(effective, pointer, replacement)
        declared_roots.append(pointer)
        used_refs.append(operation["replacement_ref"])

    assert {ref for ref in used_refs if ref.startswith("/task_delta/")} == {
        f"/task_delta/{task}" for task in v8["task_delta"]
    }
    assert {ref for ref in used_refs if ref.startswith("/record_catalog_delta/")} == {
        f"/record_catalog_delta/{name}" for name in v8["record_catalog_delta"]
    }
    assert {ref for ref in used_refs if ref.startswith("/legacy_record_repairs/")} == {
        f"/legacy_record_repairs/{name}" for name in v8["legacy_record_repairs"]
    }
    assert len(used_refs) == len(set(used_refs)) == 66
    _assert_mutation_closure(effective_v7, effective, declared_roots)
    return effective


def _materialize_effective_v91(
    registry: dict[str, object], bases: dict[str, dict[str, object]]
) -> dict[str, object]:
    effective_v7 = _materialize_effective_v7(bases["v6"], bases["v7"])
    effective_v8 = _materialize_effective_v8(effective_v7, bases["v8"])
    effective = copy.deepcopy(effective_v8)
    merge = registry["p0_effective_merge"]
    assert merge["unlisted_prior_mutation_allowed"] is False
    assert merge["replacement_ref_resolution"] == (
        "strip operation before installing the replacement record body"
    )
    replacements = merge["replace_exact_sha256"]
    additions = merge["add_absent"]
    assert len(replacements) == len(additions) == 2
    declared_roots: list[str] = []
    used_refs: list[str] = []

    for operation in replacements:
        assert set(operation) in (
            {
                "json_pointer",
                "operation",
                "expected_prior_value_sha256",
                "replacement_ref",
            },
            {
                "json_pointer",
                "operation",
                "expected_prior_value_sha256",
                "invalid_digest_with_v8_add_absent_metadata",
                "replacement_ref",
            },
        )
        assert operation["operation"] == "REPLACE_EXACT_SHA256"
        pointer = operation["json_pointer"]
        prior = _json_pointer(effective, pointer)
        assert _ordered_digest(prior) == operation["expected_prior_value_sha256"]
        source = _json_pointer(registry, operation["replacement_ref"])
        assert type(source) is dict and source["operation"] == operation["operation"]
        if "invalid_digest_with_v8_add_absent_metadata" in operation:
            name = operation["replacement_ref"].rsplit("/", 1)[1]
            assert (
                _ordered_digest(bases["v8"]["record_catalog_delta"][name])
                == (operation["invalid_digest_with_v8_add_absent_metadata"])
            )
        _replace_pointer(effective, pointer, _record_body(source))
        declared_roots.append(pointer)
        used_refs.append(operation["replacement_ref"])

    for operation in additions:
        assert set(operation) == {"json_pointer", "operation", "replacement_ref"}
        assert operation["operation"] == "ADD_ABSENT"
        source = _json_pointer(registry, operation["replacement_ref"])
        assert type(source) is dict and source["operation"] == operation["operation"]
        _add_absent_pointer(effective, operation["json_pointer"], _record_body(source))
        declared_roots.append(operation["json_pointer"])
        used_refs.append(operation["replacement_ref"])

    assert set(used_refs) == {
        f"/p0_record_catalog_delta/{name}"
        for name in registry["p0_record_catalog_delta"]
    }
    assert declared_roots == [
        "/record_catalog/CurrentScenarioResponseContractV3",
        "/record_catalog/ResponseRunSpecV3",
        "/record_catalog/CurrentCurvatureNormalizerProtocolV1",
        "/record_catalog/CurrentReadoutCalibrationSpecV3",
    ]
    assert [item["operation"] for item in merge["private_operations"]] == [
        "PRIVATE_VIEW_EXTEND",
        "PRIVATE_REFACTOR",
        "PURE_MODULE_ADD",
        "PRIVATE_DELEGATION_TO_PURE_CORE",
        "LAZY_EXPORT_IMPORT_PURITY_REFACTOR",
    ]
    _assert_mutation_closure(effective_v8, effective, declared_roots)
    return effective


def test_frozen_registry_is_loaded_only_after_raw_sha_verification() -> None:
    registry = _load_frozen_registry()

    assert list(registry) == [
        "registry_schema_version",
        "base_contracts",
        "p0_effective_merge",
        "p0_record_catalog_delta",
        "lab_contract",
    ]
    assert registry["registry_schema_version"] == (
        "experimental.v3m0.b7.v9.1-machine-contract-registry.v1"
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        _strict_json_loads(b'{"key":1,"key":2}')
    with pytest.raises(ValueError, match="non-finite JSON constant"):
        _strict_json_loads(b'{"key":NaN}')
    with pytest.raises(ValueError, match="non-finite JSON number"):
        _strict_json_loads(b'{"key":1e999}')
    with pytest.raises(ValueError, match="non-finite JSON number"):
        _strict_json_loads(b'{"key":-1e999}')
    with pytest.raises(UnicodeDecodeError):
        _strict_json_loads(b'{"key":"\xff"}')


def test_base_v6_through_v9_hashes_and_p0_overlay_are_exact() -> None:
    registry = _load_frozen_registry()
    assert registry["base_contracts"] == {
        **BASE_CONTRACTS,
        "effective_merge_algorithm": (
            "VERIFY_V6_V7_V8_THEN_MATERIALIZE_EFFECTIVE_V8_AND_APPLY_ORDERED_V91"
        ),
    }

    bases = _load_verified_base_registries(registry)
    effective = _materialize_effective_v91(registry, bases)
    delta_catalog = registry["p0_record_catalog_delta"]
    assert list(delta_catalog) == [
        "CurrentScenarioResponseContractV3",
        "CurrentCurvatureNormalizerProtocolV1",
        "CurrentReadoutCalibrationSpecV3",
        "ResponseRunSpecV3",
    ]
    for name, delta in delta_catalog.items():
        assert set(delta) == {
            "operation",
            "schema_id",
            "canonical_owner",
            "field_specs",
            "record_invariants",
        }
        for field in delta["field_specs"]:
            assert set(field) == {"name", "wire_type", "presence", "nested_record"}
            nested = field["nested_record"]
            assert nested is None or nested in effective["record_catalog"], (
                name,
                field["name"],
                nested,
            )


def test_complete_effective_registry_rejects_every_unlisted_mutation() -> None:
    registry = _load_frozen_registry()
    bases = _load_verified_base_registries(registry)
    effective = _materialize_effective_v91(registry, bases)
    assert effective["record_catalog"]["ResponseRunSpecV3"] == _record_body(
        registry["p0_record_catalog_delta"]["ResponseRunSpecV3"]
    )

    hostile_bases = copy.deepcopy(bases)
    hostile_bases["v8"]["record_catalog_delta"]["UnlistedRecord"] = copy.deepcopy(
        hostile_bases["v8"]["record_catalog_delta"]["ResponseRunSpecV3"]
    )
    with pytest.raises(AssertionError):
        _materialize_effective_v91(registry, hostile_bases)


def test_all_29_exact_records_are_typed_unique_and_reference_closed() -> None:
    records = _load_frozen_registry()["lab_contract"]["exact_records"]

    assert tuple(records) == EXACT_RECORD_NAMES
    assert len(records) == 29
    schema_ids: list[str] = []
    for name, record in records.items():
        assert set(record) == {
            "schema_id",
            "canonical_owner",
            "field_specs",
            "record_invariants",
        }, name
        assert record["canonical_owner"] in {
            "experiments.v3m0_b7_schema_lab.common",
            "experiments.v3m0_b7_schema_lab.compare",
        }
        schema_ids.append(record["schema_id"])
        assert type(record["field_specs"]) is list and record["field_specs"]
        assert type(record["record_invariants"]) is list and record["record_invariants"]
        field_names: list[str] = []
        for field in record["field_specs"]:
            assert set(field) == {"name", "wire_type", "presence", "nested_record"}
            assert field["presence"] in {"required", "required-nullable"}
            field_names.append(field["name"])
            nested = field["nested_record"]
            assert nested is None or nested in records, (name, field["name"], nested)
        assert len(field_names) == len(set(field_names)), name
    assert len(schema_ids) == len(set(schema_ids)) == 29


def test_all_32_validator_ids_resolve_and_pure_core_projection_is_frozen() -> None:
    registry = _load_frozen_registry()
    lab = registry["lab_contract"]
    contracts = lab["validator_contracts"]
    validators = contracts["validators"]

    assert tuple(item["validator_id"] for item in validators) == VALIDATOR_IDS
    assert len(validators) == 32
    assert all(
        set(item) == {"validator_id", "implementation_symbol", "exact_conditions"}
        and item["validator_id"] == item["implementation_symbol"]
        and type(item["exact_conditions"]) is list
        and item["exact_conditions"]
        for item in validators
    )
    validator_references = {
        match
        for text in _walk_strings(registry)
        for match in re.findall(r"validate_[a-z0-9_]+_v\d+", text)
    }
    assert validator_references == set(VALIDATOR_IDS)

    pure = lab["pure_replay_core_contract"]
    assert pure["module"] == "rulespace_v3.b7_replay_core_v1"
    assert pure["source_path"] == "rulespace_v3/b7_replay_core_v1.py"
    assert pure["allowed_repository_local_import_modules_exact"] == []
    assert tuple(contracts["pure_core_validator_ids"]) == PURE_CORE_VALIDATOR_IDS
    assert tuple(pure["exact_symbols"]["production_body_validator_symbols"]) == (
        PURE_CORE_VALIDATOR_IDS
    )

    frozen_projection = pure["registry_literal_projection"]
    expected_field_order = (
        "p0_record_catalog_delta",
        "canonical_json_algorithm",
        "scheduler_stage_order",
        "terminal_tag_order",
        "case_contracts",
        "normalized_nested_body_registry",
        "synthetic_component_registry",
        "synthetic_graph_contract",
        "exact_records",
    )
    expected_pointers = (
        "/p0_record_catalog_delta",
        "/lab_contract/canonical_json_algorithm",
        "/lab_contract/scheduler_stage_order",
        "/lab_contract/terminal_tag_order",
        "/lab_contract/case_contracts",
        "/lab_contract/normalized_nested_body_registry",
        "/lab_contract/synthetic_component_registry",
        "/lab_contract/synthetic_graph_contract",
        "/lab_contract/exact_records",
    )
    assert tuple(frozen_projection["field_order"]) == expected_field_order
    assert tuple(frozen_projection["source_pointers_in_field_order"]) == (
        expected_pointers
    )
    projection = {
        field: _json_pointer(registry, pointer)
        for field, pointer in zip(expected_field_order, expected_pointers)
    }
    assert _canonical_sha(projection) == PURE_REPLAY_PROJECTION_SHA256
    assert frozen_projection["canonical_sha256"] == PURE_REPLAY_PROJECTION_SHA256


def test_reviewer_receipt_has_45_fields_18_total_reject_reasons_and_identity_joins() -> (
    None
):
    lab = _load_frozen_registry()["lab_contract"]
    records = lab["exact_records"]
    receipt = records["B7LabReviewerReceiptV1"]

    assert _field_names(receipt) == RECEIPT_FIELDS
    assert len(RECEIPT_FIELDS) == 45
    failures = lab["reviewer_receipt_failure_contract"]
    assert tuple(failures["reason_code_order"]) == REVIEW_REASON_CODES
    assert len(REVIEW_REASON_CODES) == 18

    report_fields = (
        "replay_report_schema_version",
        "reviewer_role",
        "review_protocol_id",
        "lab_evidence_commit_sha",
        "replay_input_root_sha",
        "recomputed_d0_decision_payload_sha",
        "recomputed_d1_decision_payload_sha",
        "observed_surviving_route_ids",
        "observed_provisional_winner_route_id",
        "replay_output_root_sha",
        "replay_report_sha",
    )
    assert _field_names(records["B7LabReplayReportV1"]) == report_fields
    optional_report_receipt_fields = (
        "observed_report_reviewer_role",
        "observed_report_review_protocol_id",
        "observed_report_lab_evidence_commit_sha",
        "observed_report_replay_input_root_sha",
        "replay_output_root_sha",
        "replayed_d0_decision_payload_sha",
        "replayed_d1_decision_payload_sha",
        "observed_surviving_route_ids",
        "observed_provisional_winner_route_id",
    )
    assert RECEIPT_FIELDS[28:33] + RECEIPT_FIELDS[38:42] == (
        optional_report_receipt_fields
    )
    nullable = {
        field["name"]
        for field in receipt["field_specs"]
        if field["presence"] == "required-nullable"
    }
    assert set(optional_report_receipt_fields) <= nullable
    assert (
        "all-nine-optional-observed-report-fields" in failures["output_presence_rule"]
    )

    predicates = failures["reason_predicates"]
    assert set(predicates) == {
        "REVIEW_ENVIRONMENT_MISMATCH",
        "REPLAY_SOURCE_MISMATCH",
        "REPLAY_EXECUTABLE_SOURCE_ORIGIN_MISMATCH",
        "REPLAY_INPUT_ROOT_MISMATCH",
        "REPLAY_REPORT_IDENTITY_MISMATCH",
    }
    assert (
        "role-review-protocol-id-or-lab-evidence-commit-sha"
        in predicates["REPLAY_REPORT_IDENTITY_MISMATCH"]
    )
    assert (
        "child-reported-replay_input_root" in predicates["REPLAY_INPUT_ROOT_MISMATCH"]
    )
    assert failures["verdict_rule"].startswith("ACCEPT-iff-both-precheck")
    assert failures["verdict_rule"].endswith("otherwise-REJECT")
    assert failures["reason_rule"] == (
        "stable-filter-reason_code_order-by-fresh-recomputed-total-observation-and-"
        "process-failure-predicates-no-duplicate-no-unlisted-code"
    )

    receipt_validator = next(
        item
        for item in lab["validator_contracts"]["validators"]
        if item["validator_id"] == "validate_reviewer_receipt_v1"
    )
    joined_conditions = "\n".join(receipt_validator["exact_conditions"])
    for required in (
        "four-receipt-observed-report-identity-fields",
        "replay_input_root_sha",
        "fresh-process-spawn-timeout-signal-exit-and-cleanup-are-totalized",
        "reason_codes-are-the-exact-stable-recomputed-subset",
        "verdict-exactly-follows",
    ):
        assert required in joined_conditions


def test_reviewer_source_environment_argv_and_process_observations_are_total() -> None:
    lab = _load_frozen_registry()["lab_contract"]
    source = lab["reviewer_executable_source_origin_contract"]
    source_closure = source["python_module_execution_closure"]

    assert source["source_closure_expected_root_field"] == (
        "B7LabReviewerReceiptV1.reviewed_executable_source_closure_sha"
    )
    assert source["source_closure_observed_root_field"] == (
        "B7LabReviewerReceiptV1.observed_executable_source_closure_sha"
    )
    assert source["source_closure_passed_field"] == (
        "B7LabReviewerReceiptV1.executable_source_origin_precheck_passed"
    )
    assert source_closure["executed_rulespace_v3_paths_exact"] == [
        "rulespace_v3/__init__.py",
        "rulespace_v3/b7_replay_core_v1.py",
    ]
    assert source["common_origin_exact_subtrees"] == ["rulespace_v3"]
    assert source["common_origin_exact_blob_paths"] == [
        "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "experiments/v3m0_b7_schema_lab/__init__.py",
        "experiments/v3m0_b7_schema_lab/common.py",
        "experiments/v3m0_b7_schema_lab/compare.py",
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
    ]
    assert "reviewed-root-always-recomputes" in source["total_observation_rule"]
    assert "observed-root-is-nonnull-iff" in source["total_observation_rule"]
    assert (
        "passed-iff-observed-root-equals-reviewed-root"
        in source["total_observation_rule"]
    )
    assert "do-not-spawn" in source["pre_spawn_rule"]
    assert "REPLAY_EXECUTABLE_SOURCE_ORIGIN_MISMATCH" in source["pre_spawn_rule"]

    materialization = lab["reviewer_replay_materialization_contract"]
    python_executable = materialization["python_executable"]
    assert python_executable == {
        "placeholder": "{FROZEN_PYTHON_EXECUTABLE}",
        "replacement_source": (
            "reviewed-D1-environment_manifest.python_executable_realpath"
        ),
        "required_raw_sha_source": (
            "reviewed-D1-environment_manifest.python_executable_raw_sha256"
        ),
        "materialization": (
            "os.path.realpath-must-equal-recorded-realpath;regular-file;executable;"
            "raw-sha-equal;subprocess-shell-false"
        ),
    }
    expected_review_environment = {
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "LANG": "C",
        "LC_ALL": "C",
    }
    assert materialization["sanitized_environment"] == {
        "clear_all_caller_environment_first": True,
        "literal_values": expected_review_environment,
    }
    environment_rule = lab["reviewer_receipt_failure_contract"][
        "environment_observation_rule"
    ]
    assert "observed_review_environment_manifest_sha-is-null-iff" in environment_rule
    assert "review_environment_precheck_passed-iff" in environment_rule

    protocols = lab["reviewer_protocol_registry"]
    assert [item["reviewer_role"] for item in protocols] == [
        "CORPUS_REPLAY",
        "METRIC_REPLAY",
    ]
    placeholders = (
        "{FROZEN_PYTHON_EXECUTABLE}",
        "{E}",
        "{EXECUTABLE_SOURCE_CLOSURE_SHA}",
    )
    for protocol in protocols:
        argv = protocol["replay_command_argv_template"]
        assert all(argv.count(placeholder) == 1 for placeholder in placeholders)
        assert sum(item.startswith("{") and item.endswith("}") for item in argv) == 3
        assert argv[1:5] == [
            "-s",
            "-m",
            "experiments.v3m0_b7_schema_lab.compare",
            "review-corpus"
            if protocol["reviewer_role"] == "CORPUS_REPLAY"
            else "review-metric",
        ]
        assert argv[-3:] == [
            "--reviewed-executable-source-closure-sha",
            "{EXECUTABLE_SOURCE_CLOSURE_SHA}",
            "--emit-replay-report",
        ]
    assert materialization["argv_rule"].startswith(
        "replace-exactly-the-three-declared-placeholder-kinds"
    )
    assert materialization["executable_source_closure"]["materialization"].endswith(
        "transported-to-child-only-by-this-literal-argv-pair"
    )

    process = lab["reviewer_process_totalization_contract"]
    assert process["termination_kind_order"] == [
        "EXITED",
        "SIGNALED",
        "PRECHECK_FAILED",
        "SPAWN_FAILED",
        "OUTPUT_LIMIT_EXCEEDED",
        "TIMED_OUT",
    ]
    assert process["timeout_seconds"] == 1800
    assert process["stdout_hard_cap_bytes"] == 1048576
    assert process["stderr_hard_cap_bytes"] == 1048576
    assert process["io_chunk_bytes"] == 65536
    assert (
        "never-call-communicate-or-unbounded-read-or-drain"
        in process["bounded_io_protocol"]
    )
    assert "do-not-create-child" in process["precheck_failure_protocol"]
    assert process["success_termination_rule"] == (
        "ACCEPT-requires-termination-kind-EXITED-and-replay_exit_code-zero-and-"
        "null-signal"
    )
    process_mapping = process["termination_reason_predicate_mapping"]
    assert list(process_mapping) == [
        "PRECHECK_FAILED",
        "SPAWN_FAILED",
        "OUTPUT_LIMIT_EXCEEDED",
        "TIMED_OUT",
        "SIGNALED",
        "EXITED_NONZERO",
        "EXITED_ZERO",
    ]
    for reason in REVIEW_REASON_CODES[4:10]:
        assert reason in "\n".join(process_mapping.values())


def test_terminal_git_guards_cover_selection_lab_halt_and_review_halt() -> None:
    lab = _load_frozen_registry()["lab_contract"]
    git_contract = lab["git_object_handoff_contract"]
    reachability = git_contract["evidence_commit_reachability"]

    assert git_contract["evidence_commit_symbol"] == "E"
    assert git_contract["selection_commit_symbol"] == "S"
    assert git_contract["review_halt_commit_symbol"] == "H"
    assert reachability["common_is_ancestor_of_each_route_commit"] is True
    assert reachability["each_route_commit_is_ancestor_of_E"] is True
    assert reachability["route_commit_oids_are_distinct"] is True
    assert reachability["E_tree_common_subtrees"] == ["rulespace_v3"]
    assert reachability["E_tree_common_paths"] == [
        "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "experiments/v3m0_b7_schema_lab/__init__.py",
        "experiments/v3m0_b7_schema_lab/common.py",
        "experiments/v3m0_b7_schema_lab/compare.py",
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
    ]
    assert reachability["garbage_collection_reachability"] == (
        "selection-tag-to-S-to-E-or-review-halt-tag-to-H-to-E-or-lab-halt-tag-"
        "direct-to-E-retains-all-common-and-route-ancestor-objects"
    )

    expected_common_guards = [
        "objects-info-alternates-path-must-be-absent",
        "info-grafts-path-must-be-absent",
        "replace-ref-namespace-is-ignored-by-global-option",
        "E-cat-file-type-equals-commit",
        "common-and-all-three-route-oids-cat-file-type-equals-commit-and-"
        "satisfy-evidence_commit_reachability",
        "all-object-reads-use-trusted_git_executable_protocol-sanitized_environment-"
        "and-git_global_argv_prefix",
    ]
    expected_inheritance = {
        "UNIQUE_SELECTION": "common_repository_guards-plus-repository_guards",
        "D0_OR_D1_TYPED_LAB_HALT": (
            "common_repository_guards-plus-lab_halt_repository_guards"
        ),
        "REPLAY_OR_REVIEW_FAILURE": (
            "common_repository_guards-plus-review_halt_repository_guards"
        ),
    }
    expected_selection_guards = [
        "all-common_repository_guards-pass-with-S-required",
        "S-cat-file-type-equals-commit",
        "tag-ref-resolves-to-full-tag-object-oid",
        "tag-object-cat-file-type-equals-tag",
        "raw-S-commit-has-exactly-one-parent-line-equal-E",
        "diff-tree-raw-z-no-renames-E-S-equals-S_tree_delta_exact",
    ]
    expected_lab_halt_guards = [
        "all-common_repository_guards-pass-with-S-absent-and-E-"
        "evidence_commit_reachability-recomputed",
        "E-cat-file-type-equals-commit-and-satisfies-evidence_commit_reachability-"
        "using-D0-as-the-always-present-root-source",
        "E-colon-d0-path-is-mode-100644-blob-and-raw-SHA-strict-body-self-hash-"
        "decision-projection-and-D0-state-recompute",
        "if-D0-has-no-survivor-then-E-colon-d1-path-is-absent",
        "if-D0-has-survivors-then-E-colon-d1-path-is-mode-100644-valid-blob-with-"
        "no-survivor-or-metric-tie-and-all-D0-D1-joins-recompute",
        "E-colon-selection-and-review-halt-paths-are-absent-and-production-handoff-"
        "report-is-absent",
        "lab-halt-tag-ref-resolves-to-full-tag-object-oid-with-type-tag-header-"
        "object-E-header-type-commit-exact-tag-name-and-peeled-target-E",
        "selection-and-review-halt-tag-refs-are-absent-for-this-E-terminal",
    ]
    expected_review_halt_guards = [
        "all-common_repository_guards-pass-with-S-absent-and-E-"
        "evidence_commit_reachability-recomputed",
        "E-and-H-cat-file-type-equals-commit",
        "raw-H-commit-has-exactly-one-parent-line-equal-E",
        "diff-tree-raw-z-no-renames-E-H-equals-H_tree_delta_exact",
        "halt-tag-ref-resolves-to-full-tag-object-oid",
        "halt-tag-object-cat-file-type-equals-tag-and-peeled-target-equals-H",
        "H-colon-review_halt-path-is-mode-100644-blob-and-strict-body-validates-"
        "validate_review_halt_v1",
        "S-selection-tag-and-production-handoff-are-absent-for-this-E-terminal",
    ]
    assert git_contract["common_repository_guards"] == expected_common_guards
    assert git_contract["terminal_repository_guard_inheritance"] == (
        expected_inheritance
    )
    assert git_contract["repository_guards"] == expected_selection_guards
    assert git_contract["lab_halt_repository_guards"] == expected_lab_halt_guards
    assert git_contract["review_halt_repository_guards"] == (
        expected_review_halt_guards
    )

    expected_blob_read_protocol = {
        "tree_entry_command": "ls-tree-z-commit-double-dash-literal-path",
        "allowed_mode": "100644",
        "allowed_type": "blob",
        "blob_command": "cat-file-blob-commit-colon-literal-path",
        "raw_sha_before_parse": True,
        "strict_parse_after_raw_sha": True,
        "d0_and_d1_commit": "E",
        "selection_commit": "S",
        "review_halt_commit": "H",
        "worktree_or_caller_path_allowed": False,
    }
    expected_handoff_container = {
        "begin_marker": "<!-- BEGIN V3M0_B7_PRODUCTION_HANDOFF_V1 -->",
        "end_marker": "<!-- END V3M0_B7_PRODUCTION_HANDOFF_V1 -->",
        "machine_block_count": 1,
        "machine_block_language": "json",
        "strict_utf8_no_bom": True,
        "handoff_sha_domain": ("parsed-machine-record-after-removing-only-handoff_sha"),
        "markdown_blob_or-carrier-path-in-handoff_sha": False,
    }
    expected_self_hash_exclusions = {
        "d0_comparison.json": ["d0_result_sha"],
        "d1_comparison.json": ["d1_result_sha"],
        "selection_review.json": ["selection_review_sha"],
        "review_halt.json": ["review_halt_sha"],
        "production_handoff_review": ["handoff_sha"],
    }
    assert git_contract["blob_read_protocol"] == expected_blob_read_protocol
    assert git_contract["handoff_report_container"] == expected_handoff_container
    assert git_contract["self_hash_exclusions"] == expected_self_hash_exclusions
    assert git_contract["handoff_tag_target"] == "S"
    git_projection_fields = (
        "handoff_report_container",
        "blob_read_protocol",
        "self_hash_exclusions",
        "handoff_tag_target",
        "common_repository_guards",
        "terminal_repository_guard_inheritance",
        "repository_guards",
        "lab_halt_repository_guards",
        "review_halt_repository_guards",
    )
    git_projection = {field: git_contract[field] for field in git_projection_fields}
    assert _ordered_digest(git_projection) == GIT_HANDOFF_MECHANICAL_SHA256

    halt = lab["halt_emission_contract"]
    expected_halt = {
        "D0_NO_SURVIVOR": {
            "d0_comparison": "required",
            "d1_comparison": "absent",
            "selection_review": "absent",
            "review_halt": "absent",
            "production_handoff": "absent",
            "terminal_tag": "annotated-v3m0-b7-schema-lab-halt-v1-to-E",
        },
        "D1_NO_SURVIVOR_OR_METRIC_TIE": {
            "d0_comparison": "required",
            "d1_comparison": "required",
            "selection_review": "absent",
            "review_halt": "absent",
            "production_handoff": "absent",
            "terminal_tag": "annotated-v3m0-b7-schema-lab-halt-v1-to-E",
        },
        "REPLAY_OR_REVIEW_FAILURE": {
            "d0_comparison": "required",
            "d1_comparison": "required",
            "selection_review": "absent",
            "review_halt": (
                "required-in-H-single-parent-terminal-commit-and-annotated-halt-tag"
            ),
            "production_handoff": "absent",
            "terminal_tag": "annotated-v3m0-b7-schema-review-halt-v1-to-H",
        },
        "UNIQUE_SELECTION": {
            "d0_comparison": "required",
            "d1_comparison": "required",
            "selection_review": (
                "required-in-S-single-parent-release-commit-and-annotated-selection-tag"
            ),
            "review_halt": "absent",
            "production_handoff": "required-before-production-implementation",
            "terminal_tag": "annotated-v3m0-b7-schema-selection-v1-to-S",
        },
        "tracing_report_authority": (
            "optional-human-report-outside-result_paths-with-no-production-release-"
            "effect"
        ),
    }
    assert halt == expected_halt
    terminal_states = (
        "D0_NO_SURVIVOR",
        "D1_NO_SURVIVOR_OR_METRIC_TIE",
        "REPLAY_OR_REVIEW_FAILURE",
        "UNIQUE_SELECTION",
    )
    artifact_matrix = {state: halt[state] for state in terminal_states}
    assert _ordered_digest(artifact_matrix) == HALT_ARTIFACT_MATRIX_SHA256


def test_replay_report_output_root_self_hash_and_stdout_are_mechanically_frozen() -> (
    None
):
    lab = _load_frozen_registry()["lab_contract"]
    report = lab["exact_records"]["B7LabReplayReportV1"]
    expected_invariant = (
        "replay_output_root_sha equals canonical_sha of fields through "
        "observed_provisional_winner_route_id; replay_report_sha removes only itself; "
        "stdout is canonical JSON bytes plus one LF and contains no receipt fields"
    )
    expected_output_presence_rule = (
        "if-and-only-if-stdout-strict-decodes-as-valid-B7LabReplayReportV1-then-all-"
        "nine-optional-observed-report-fields-are-nonnull-and-exactly-equal-that-"
        "report;otherwise-all-nine-are-null"
    )
    expected_stdout_write_rule = (
        "exactly-one-terminal-sys.stdout.buffer.write-of-canonical-"
        "B7LabReplayReportV1-bytes-plus-one-LF-is-allowed-after-all-computation;"
        "all-other-print-or-stdout-stderr-write-calls-in-child-closure-reject"
    )
    expected_stream_hash_rule = (
        "for-normal-completion-hash-exact-complete-captured-stream;for-overflow-hash-"
        "exact-first-cap-bytes;for-timeout-or-signal-hash-exact-bounded-prefix-read-"
        "before-parent-fd-close;for-precheck-or-spawn-failure-hash-empty-bytes"
    )
    assert report["record_invariants"] == [expected_invariant]
    assert _field_names(report)[-3:] == (
        "observed_provisional_winner_route_id",
        "replay_output_root_sha",
        "replay_report_sha",
    )
    assert lab["reviewer_receipt_failure_contract"]["output_presence_rule"] == (
        expected_output_presence_rule
    )
    assert lab["reviewer_child_static_scan_contract"]["stdout_write_rule"] == (
        expected_stdout_write_rule
    )
    assert lab["reviewer_process_totalization_contract"]["stream_hash_rule"] == (
        expected_stream_hash_rule
    )
    receipt_validator = next(
        validator
        for validator in lab["validator_contracts"]["validators"]
        if validator["validator_id"] == "validate_reviewer_receipt_v1"
    )
    replay_projection = {
        "replay_report_record": report,
        "output_presence_rule": expected_output_presence_rule,
        "stdout_write_rule": expected_stdout_write_rule,
        "stream_hash_rule": expected_stream_hash_rule,
        "reviewer_receipt_exact_conditions": receipt_validator["exact_conditions"],
    }
    assert _ordered_digest(replay_projection) == REPLAY_REPORT_MECHANICAL_SHA256
