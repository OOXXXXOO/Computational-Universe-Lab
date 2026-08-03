"""Static contracts for the frozen B7 v9.1 machine registry.

These tests read design registries and existing source bytes only.  They do not
import the future schema lab or the pure replay core, and therefore cannot mint
an authority, execute a route, or issue a scientific status.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "docsv3" / "v3-机器合同-B7-v9.1-registry.json"
REGISTRY_RAW_SHA256 = "222cd47e95de63eaedee41f6ca4b207a0eccceb7a77089aed43a480a77f69d72"
PURE_REPLAY_PROJECTION_SHA256 = (
    "bafbaeb75e890715464c1fff6e6e0cbf1d4f56bb53a3817a9b2d12d2a3c27ff9"
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


def _strict_json_loads(raw: bytes) -> dict[str, object]:
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {value}")
        ),
    )
    assert type(value) is dict
    return value


def _load_frozen_registry() -> dict[str, object]:
    raw = REGISTRY_PATH.read_bytes()
    # The raw-byte identity gate deliberately precedes UTF-8 decoding and parse.
    assert hashlib.sha256(raw).hexdigest() == REGISTRY_RAW_SHA256
    return _strict_json_loads(raw)


def _load_embedded_registry(
    path: Path, begin_marker: str, end_marker: str
) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
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

    loaded: dict[str, dict[str, object]] = {}
    for version, expected in BASE_CONTRACTS.items():
        path = REPO_ROOT / expected["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected["raw_sha256"]
        if version in EMBEDDED_REGISTRY_MARKERS:
            begin, end = EMBEDDED_REGISTRY_MARKERS[version]
            base = _load_embedded_registry(path, begin, end)
            loaded[version] = base
            assert (
                base["registry_schema_version"] == expected["registry_schema_version"]
            )
            assert _ordered_digest(base) == expected["ordered_registry_sha256"]

    catalog = dict(loaded["v6"]["record_catalog"])
    for name, delta in loaded["v7"]["record_catalog_delta"].items():
        if delta["operation"] == "ADD_V7_RECORD":
            assert name not in catalog
        else:
            assert delta["operation"] == "REPLACE_V6_RECORD"
            assert name in catalog
        catalog[name] = _record_body(delta)

    v8 = loaded["v8"]
    v8_replacements = {
        item["json_pointer"]: item
        for item in v8["effective_merge"]["replace_exact_sha256"]
        if item["json_pointer"].startswith("/record_catalog/")
    }
    for name, delta in v8["record_catalog_delta"].items():
        pointer = f"/record_catalog/{name}"
        if delta["operation"] == "ADD_ABSENT":
            assert name not in catalog
        else:
            assert delta["operation"] == "REPLACE_EXACT_SHA256"
            assert (
                _ordered_digest(catalog[name])
                == v8_replacements[pointer]["expected_prior_value_sha256"]
            )
        catalog[name] = _record_body(delta)

    merge = registry["p0_effective_merge"]
    assert merge["unlisted_prior_mutation_allowed"] is False
    assert merge["replacement_ref_resolution"] == (
        "strip operation before installing the replacement record body"
    )
    assert [item["json_pointer"] for item in merge["replace_exact_sha256"]] == [
        "/record_catalog/CurrentScenarioResponseContractV3",
        "/record_catalog/ResponseRunSpecV3",
    ]
    assert [item["json_pointer"] for item in merge["add_absent"]] == [
        "/record_catalog/CurrentCurvatureNormalizerProtocolV1",
        "/record_catalog/CurrentReadoutCalibrationSpecV3",
    ]

    delta_catalog = registry["p0_record_catalog_delta"]
    for item in merge["replace_exact_sha256"]:
        name = item["json_pointer"].rsplit("/", 1)[1]
        assert item["operation"] == "REPLACE_EXACT_SHA256"
        assert _ordered_digest(catalog[name]) == item["expected_prior_value_sha256"]
        assert _json_pointer(registry, item["replacement_ref"]) == delta_catalog[name]
        if "invalid_digest_with_v8_add_absent_metadata" in item:
            assert (
                _ordered_digest(v8["record_catalog_delta"][name])
                == item["invalid_digest_with_v8_add_absent_metadata"]
            )
        catalog[name] = _record_body(delta_catalog[name])
    for item in merge["add_absent"]:
        name = item["json_pointer"].rsplit("/", 1)[1]
        assert item["operation"] == "ADD_ABSENT"
        assert name not in catalog
        assert _json_pointer(registry, item["replacement_ref"]) == delta_catalog[name]
        catalog[name] = _record_body(delta_catalog[name])

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
            assert nested is None or nested in catalog, (name, field["name"], nested)


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

    tag_expectations = {
        "tag_contract": ("S", "v3m0-b7-schema-selection-v1"),
        "lab_halt_tag_contract": ("E", "v3m0-b7-schema-lab-halt-v1"),
        "review_halt_tag_contract": ("H", "v3m0-b7-schema-review-halt-v1"),
    }
    for name, (target, tag_name) in tag_expectations.items():
        tag = git_contract[name]
        assert tag["ref_object_type"] == "tag"
        assert tag["tag_header_object"] == target
        assert tag["tag_header_type"] == "commit"
        assert tag["tag_header_tag"] == tag_name
        assert tag["peeled_target"] == target
        assert tag["lightweight_tag_allowed"] is False

    assert git_contract["terminal_repository_guard_inheritance"] == {
        "UNIQUE_SELECTION": "common_repository_guards-plus-repository_guards",
        "D0_OR_D1_TYPED_LAB_HALT": (
            "common_repository_guards-plus-lab_halt_repository_guards"
        ),
        "REPLAY_OR_REVIEW_FAILURE": (
            "common_repository_guards-plus-review_halt_repository_guards"
        ),
    }
    assert any(
        "evidence_commit_reachability" in guard
        for guard in git_contract["common_repository_guards"]
    )
    assert any(
        "evidence_commit_reachability" in guard
        for guard in git_contract["lab_halt_repository_guards"]
    )
    assert any(
        "evidence_commit_reachability" in guard
        for guard in git_contract["review_halt_repository_guards"]
    )
    assert git_contract["commit_partition"][
        "terminal_children_mutually_exclusive"
    ].startswith("exactly-one-of-S-or-H")

    halt = lab["halt_emission_contract"]
    assert list(halt) == [
        "D0_NO_SURVIVOR",
        "D1_NO_SURVIVOR_OR_METRIC_TIE",
        "REPLAY_OR_REVIEW_FAILURE",
        "UNIQUE_SELECTION",
        "tracing_report_authority",
    ]
    assert halt["D0_NO_SURVIVOR"]["terminal_tag"].endswith("lab-halt-v1-to-E")
    assert halt["D1_NO_SURVIVOR_OR_METRIC_TIE"]["terminal_tag"].endswith(
        "lab-halt-v1-to-E"
    )
    assert halt["REPLAY_OR_REVIEW_FAILURE"]["terminal_tag"].endswith(
        "review-halt-v1-to-H"
    )
    assert halt["UNIQUE_SELECTION"]["terminal_tag"].endswith("selection-v1-to-S")
