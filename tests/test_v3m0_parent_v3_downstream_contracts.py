"""Static B0 contracts for the Parent-v3 downstream production chain.

The B0 test parses the design erratum.  It deliberately does not import any
future B1--B10 production module and therefore cannot mint a capability.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md"
)
BEGIN_MARKER = "<!-- BEGIN V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->"
END_MARKER = "<!-- END V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->"

EXPECTED_RECORD_CATALOG_COUNT = 148
EXPECTED_API_COUNT = 37
# Independent golden digests.  They are replaced only when the B0 registry is
# deliberately re-frozen; neither value is read from the registry under test.
EXPECTED_RECORD_CATALOG_GOLDEN_SHA256 = (
    "88d832f52507481c8fc790bc0994494ace5e0dfcd43ecaa8f024a601e161513c"
)
EXPECTED_TASK_CONTRACT_GOLDEN_SHA256 = (
    "9ef1b9bf9715b7e3c935c1a0703b1835d3598b03f900339b8cf0911c47eabfe6"
)


def _load_registry() -> dict[str, object]:
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    assert text.count(BEGIN_MARKER) == 1
    assert text.count(END_MARKER) == 1
    payload = text.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("\n```")
    return json.loads(payload.removeprefix("```json\n").removesuffix("\n```"))


def _fields(registry: dict[str, object], record: str) -> list[str]:
    catalog = registry["record_catalog"]
    return [item["name"] for item in catalog[record]["field_specs"]]


def _field(registry: dict[str, object], record: str, name: str) -> dict[str, object]:
    catalog = registry["record_catalog"]
    return next(item for item in catalog[record]["field_specs"] if item["name"] == name)


def _api(registry: dict[str, object], task: str, name: str) -> dict[str, object]:
    return next(
        item for item in registry["tasks"][task]["apis"] if item["name"] == name
    )


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _freeze_ordered_json(value: object) -> object:
    # Dict insertion order and every nested value are part of the golden.  For
    # record_catalog this includes all field wire metadata and invariants; for
    # tasks it includes modules, ownership, complete APIs, semantics and failures.
    if isinstance(value, dict):
        return tuple((key, _freeze_ordered_json(item)) for key, item in value.items())
    if isinstance(value, list):
        return tuple(_freeze_ordered_json(item) for item in value)
    return value


def _record_catalog_golden_tuple(registry: dict[str, object]) -> object:
    return _freeze_ordered_json(registry["record_catalog"])


def _task_contract_golden_tuple(registry: dict[str, object]) -> object:
    return _freeze_ordered_json(registry["tasks"])


def _assert_contract_death(action) -> None:
    try:
        action()
    except AssertionError:
        return
    raise AssertionError("hostile contract mutation unexpectedly survived")


def test_independent_golden_pins_full_148_record_and_37_api_task_contracts() -> None:
    registry = _load_registry()
    records = _record_catalog_golden_tuple(registry)
    tasks = _task_contract_golden_tuple(registry)

    assert len(registry["record_catalog"]) == EXPECTED_RECORD_CATALOG_COUNT
    assert (
        sum(len(task["apis"]) for task in registry["tasks"].values())
        == EXPECTED_API_COUNT
    )
    assert _canonical_digest(records) == EXPECTED_RECORD_CATALOG_GOLDEN_SHA256
    assert _canonical_digest(tasks) == EXPECTED_TASK_CONTRACT_GOLDEN_SHA256

    hostile = copy.deepcopy(registry)
    first_record = next(iter(hostile["record_catalog"].values()))
    first_record["field_specs"][0]["wire_type"] = "FORGED"
    assert (
        _canonical_digest(_record_catalog_golden_tuple(hostile))
        != EXPECTED_RECORD_CATALOG_GOLDEN_SHA256
    )

    hostile = copy.deepcopy(registry)
    _api(hostile, "B10", "verify_v3m0_checkpoint_envelope_v1")["semantics"] = (
        "ACCEPT WITHOUT VERIFY"
    )
    assert (
        _canonical_digest(_task_contract_golden_tuple(hostile))
        != EXPECTED_TASK_CONTRACT_GOLDEN_SHA256
    )


def test_registry_is_design_only_v6_and_all_records_are_machine_typed() -> None:
    registry = _load_registry()

    assert registry["registry_schema_version"] == (
        "v3m0.parent-v3-downstream-contract-registry.v6"
    )
    assert registry["document_authority"] == "DESIGN_ONLY_NO_AUTHORITY"
    assert registry["production_status"] == "EXPECTED-MISSING_AT_B0_FREEZE"
    assert registry["issued_statuses"] == []
    assert registry["threshold_values"] == {}
    assert registry["threshold_policy"] == "REFERENCE_EXISTING_FROZEN_VALUES_ONLY"
    assert registry["branch_literals"] == ["actual", "matched_ablated"]
    assert list(registry["tasks"]) == [f"B{index}" for index in range(1, 11)]
    assert all(
        task["implementation_status"] == "EXPECTED-MISSING_AT_B0_FREEZE"
        for task in registry["tasks"].values()
    )

    catalog = registry["record_catalog"]
    assert len(catalog) == EXPECTED_RECORD_CATALOG_COUNT
    schema_ids: list[str] = []
    for name, record in catalog.items():
        assert set(record) == {
            "schema_id",
            "canonical_owner",
            "field_specs",
            "record_invariants",
        }, name
        schema_ids.append(record["schema_id"])
        assert record["canonical_owner"].startswith("rulespace_v3.")
        assert record["field_specs"]
        assert isinstance(record["record_invariants"], list)
        names: list[str] = []
        for spec in record["field_specs"]:
            assert set(spec) == {
                "name",
                "wire_type",
                "presence",
                "literal_domain",
                "tuple_cardinality",
                "nested_record",
                "constraints",
            }, (name, spec)
            names.append(spec["name"])
            assert spec["presence"] in {"required", "required-nullable"}
            assert isinstance(spec["literal_domain"], list)
            assert isinstance(spec["constraints"], list)
            if spec["tuple_cardinality"] is not None:
                assert set(spec["tuple_cardinality"]) == {"kind", "value"}
                assert spec["tuple_cardinality"]["kind"] in {
                    "exact",
                    "nonempty",
                    "derived",
                    "bounded",
                }
            nested = spec["nested_record"]
            if nested is not None:
                assert nested in catalog, (name, spec["name"], nested)
        assert len(names) == len(set(names)), name
    assert len(schema_ids) == len(set(schema_ids))

    all_owned = [
        record
        for task in registry["tasks"].values()
        for record in task["owned_records"]
    ]
    assert len(all_owned) == len(set(all_owned))
    assert set(all_owned) == set(catalog)

    for task in registry["tasks"].values():
        for api in task["apis"]:
            assert set(api) == {
                "name",
                "visibility",
                "args",
                "returns",
                "raw_hydration_allowed",
                "semantics",
            }
            assert api["visibility"] in {"public", "owner-internal"}
            assert api["raw_hydration_allowed"] is False
            assert api["args"] == [
                {"name": arg["name"], "wire_type": arg["wire_type"]}
                for arg in api["args"]
            ]


def test_b1_and_b2_freeze_recursive_parent_v3_bodies_and_c19_counts() -> None:
    registry = _load_registry()

    assert _fields(registry, "SelectedControlEvidenceRef") == [
        "control_id",
        "control_registry_entry_sha",
        "expected_rank_declaration_sha",
        "run_spec_sha",
        "paired_response_sha",
        "shell_manifest_sha",
        "comparison_2t_run_spec_sha",
        "comparison_2t_response_sha",
        "comparison_2t_shell_manifest_sha",
    ]

    assert _fields(registry, "WindowThresholdCalibrationV3") == [
        "calibration_v3_schema_version",
        "parent_freeze_v3_sha",
        "current_application_registry_sha",
        "current_application_registry_v3",
        "calibration_control_replay_refs",
        "calibration_outcome",
        "calibration_v3_sha",
    ]
    assert _fields(registry, "ParentV3CalibrationControlReplayRefV1") == [
        "replay_ref_schema_version",
        "parent_freeze_v3_sha",
        "current_application_registry_sha",
        "parent_v1_ordinal",
        "authority_tag",
        "control_case_id",
        "control_id",
        "application_authority_v2",
        "application_authority_v2_sha",
        "scenario_authority_v2",
        "scenario_authority_v2_sha",
        "response_contract_v2",
        "response_contract_v2_sha",
        "replay_ref_sha",
    ]
    exact_v2_leaf_fields = {
        "ScenarioBasisSelectorSpec": [
            "selector_schema_version",
            "scenario_id",
            "public_source_basis_manifest_id",
            "public_readout_basis_manifest_id",
            "source_selector_derivation_id",
            "readout_selector_derivation_id",
            "source_selector",
            "readout_selector",
            "source_injection",
            "readout_coisometry",
            "selector_sha",
        ],
        "CurrentScenarioResponseContractV2": [
            "response_contract_schema_version",
            "contract_state",
            "scenario_id",
            "selector_sha",
            "selector_spec",
            "source_trial_vectors",
            "response_torus_denominators",
            "response_reciprocal_indices",
            "source_readout_bridge_reciprocal_indices",
            "source_readout_bridge_steps",
            "reference_reciprocal_index",
            "preregistered_phase_bands",
            "operation_dag_sha",
            "compiled_contract_sha",
            "construction_rule_id",
            "construction_family_id",
            "expected_actual_shell_rank",
            "expected_matched_shell_rank",
            "actual_step_count",
            "matched_ablated_step_count",
            "actual_program_sha",
            "matched_ablated_program_sha",
            "preflight_derivation_or_recipe_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "response_template_sha",
            "prediction_profile_sha",
            "uses_global_fft_projection",
            "uses_per_k_time_step_projector",
            "response_contract_sha",
        ],
        "CurrentScenarioAuthorityV2": [
            "scenario_authority_schema_version",
            "authority_state",
            "control_case_id",
            "application_instance_id",
            "based_on_application_spec_sha",
            "scenario_id",
            "scenario_execution_spec",
            "source_disposition",
            "source_candidate_v1_scenario_sha",
            "source_candidate_v2_refreeze_sha",
            "response_contract",
            "scenario_authority_sha",
        ],
        "CurrentApplicationAuthorityV2": [
            "application_authority_schema_version",
            "authority_state",
            "control_case_id",
            "application_instance_id",
            "based_on_application_spec_sha",
            "source_candidate_v1_application_sha",
            "complete_scenario_execution_specs",
            "scenario_authorities",
            "application_authority_sha",
        ],
    }
    for record_name, field_names in exact_v2_leaf_fields.items():
        assert _fields(registry, record_name) == field_names
    selector_record = registry["record_catalog"]["ScenarioBasisSelectorSpec"]
    assert selector_record["schema_id"] == "v3m0.scenario-basis-selector.v1"
    assert selector_record["canonical_owner"] == "rulespace_v3.parent_freeze"
    for record_name, schema_id in (
        (
            "CurrentScenarioResponseContractV2",
            "v3m0.current-scenario-response-contract.v2",
        ),
        ("CurrentScenarioAuthorityV2", "v3m0.current-scenario-authority.v2"),
        (
            "CurrentApplicationAuthorityV2",
            "v3m0.current-application-authority.v2",
        ),
    ):
        record = registry["record_catalog"][record_name]
        assert record["schema_id"] == schema_id
        assert record["canonical_owner"] == "rulespace_v3.parent_v2_contracts"
    for field_name in (
        "source_selector",
        "readout_selector",
        "source_injection",
        "readout_coisometry",
    ):
        assert (
            _field(registry, "ScenarioBasisSelectorSpec", field_name)["nested_record"]
            == "FrozenComplexTensor"
        )
    assert (
        _field(
            registry,
            "CurrentScenarioResponseContractV2",
            "selector_spec",
        )["nested_record"]
        == "ScenarioBasisSelectorSpec"
    )
    assert (
        _field(
            registry,
            "CurrentScenarioResponseContractV2",
            "source_trial_vectors",
        )["nested_record"]
        == "FrozenComplexTensor"
    )
    assert (
        _field(
            registry,
            "CurrentScenarioAuthorityV2",
            "scenario_execution_spec",
        )["nested_record"]
        == "ApplicationScenarioExecutionSpec"
    )
    assert (
        _field(
            registry,
            "CurrentScenarioAuthorityV2",
            "response_contract",
        )["nested_record"]
        == "CurrentScenarioResponseContractV2"
    )
    assert (
        _field(
            registry,
            "CurrentApplicationAuthorityV2",
            "complete_scenario_execution_specs",
        )["nested_record"]
        == "ApplicationScenarioExecutionSpec"
    )
    assert (
        _field(
            registry,
            "CurrentApplicationAuthorityV2",
            "scenario_authorities",
        )["nested_record"]
        == "CurrentScenarioAuthorityV2"
    )
    for field_name, nested_record in (
        ("application_authority_v2", "CurrentApplicationAuthorityV2"),
        ("scenario_authority_v2", "CurrentScenarioAuthorityV2"),
        ("response_contract_v2", "CurrentScenarioResponseContractV2"),
    ):
        field = _field(
            registry,
            "ParentV3CalibrationControlReplayRefV1",
            field_name,
        )
        assert field["wire_type"] == nested_record
        assert field["nested_record"] == nested_record
    assert (
        _field(
            registry,
            "WindowThresholdCalibrationV3",
            "current_application_registry_v3",
        )["wire_type"]
        == "canonical-json-object"
    )
    assert (
        _field(
            registry,
            "WindowThresholdCalibrationV3",
            "calibration_control_replay_refs",
        )["nested_record"]
        == "ParentV3CalibrationControlReplayRefV1"
    )
    assert _field(
        registry,
        "WindowThresholdCalibrationV3",
        "calibration_control_replay_refs",
    )["tuple_cardinality"] == {"kind": "exact", "value": "3"}
    assert _field(
        registry,
        "ParentV3CalibrationControlReplayRefV1",
        "authority_tag",
    )["literal_domain"] == ["INHERITED_CURRENT_V2"]
    assert all(
        "parent_freeze_v2_sha" not in name
        for name in _fields(registry, "ParentV3CalibrationControlReplayRefV1")
    )
    calibration_invariants = registry["record_catalog"]["WindowThresholdCalibrationV3"][
        "record_invariants"
    ]
    assert any(
        "19 inherited V2" in item and "one refrozen V3" in item
        for item in calibration_invariants
    )
    assert any("old and replacement C19" in item for item in calibration_invariants)
    assert any(
        "historical Parent-v1" in item and "numerical witness" in item
        for item in calibration_invariants
    )
    assert (
        _field(registry, "WindowThresholdCalibrationV3", "calibration_outcome")[
            "nested_record"
        ]
        == "WindowCalibrationOutcome"
    )
    assert _fields(registry, "WindowCalibrationOutcome") == [
        "status",
        "manifest",
        "selection",
        "outcome_sha",
    ]
    assert (
        _field(registry, "WindowCalibrationOutcome", "manifest")["nested_record"]
        == "WindowThresholdCalibrationManifest"
    )
    assert (
        _field(registry, "WindowCalibrationOutcome", "selection")["nested_record"]
        == "WindowThresholdSelection"
    )

    assert _fields(registry, "CalibrationApplicationPermitV3") == [
        "permit_schema_version",
        "parent_freeze_v3_sha",
        "calibration",
        "current_application_authority",
        "current_scenario_authority",
        "current_scenario_response_contract",
        "selected_fejer_order",
        "permit_scope_id",
        "permit_sha",
    ]
    for field_name, nested in (
        ("calibration", "WindowThresholdCalibrationV3"),
        ("current_application_authority", "CurrentApplicationAuthorityV3"),
        ("current_scenario_authority", "CurrentScenarioAuthorityV3"),
        ("current_scenario_response_contract", "CurrentScenarioResponseContractV3"),
    ):
        assert (
            _field(registry, "CalibrationApplicationPermitV3", field_name)[
                "nested_record"
            ]
            == nested
        )

    assert _fields(registry, "ApplicationScenarioMaterializationV3") == [
        "materialization_schema_version",
        "permit",
        "current_application_authority",
        "current_scenario_authority",
        "current_scenario_response_contract",
        "basis_contract",
        "construction_trace",
        "ablation_pair_snapshot",
        "actual_factory_binding",
        "matched_ablated_factory_binding",
        "materialization_sha",
    ]
    assert (
        _field(registry, "ApplicationScenarioMaterializationV3", "permit")[
            "nested_record"
        ]
        == "CalibrationApplicationPermitV3"
    )
    assert (
        _field(
            registry, "ApplicationScenarioMaterializationV3", "ablation_pair_snapshot"
        )["nested_record"]
        == "AblationPairSnapshot"
    )
    assert (
        _field(
            registry, "ApplicationScenarioMaterializationV3", "actual_factory_binding"
        )["nested_record"]
        == "FactoryBranchBindingV3"
    )
    assert (
        _field(registry, "FactoryBranchBindingV3", "factory")["nested_record"]
        == "LinearRealspaceFactory"
    )

    assert registry["c19_freeze"] == {
        "control_case_id": "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
        "claim_ceiling": "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY",
        "causal_contrast_role": "NULL_INTERVENTION_INVARIANCE_CONTROL",
        "physical_anchor_eligibility": "INELIGIBLE",
        "family_eligibility": "INELIGIBLE",
        "state_schema_id": "v3m0.c19-real-canonical-state.v2",
        "channel_count": 20,
        "spatial_shape": [8],
        "actual_active_step_count": 50,
        "matched_active_step_count": 30,
        "actual_layer_slot_count": 50,
        "matched_layer_slot_count": 50,
        "actual_primitive_count": 50,
        "matched_primitive_count": 50,
        "matched_neutral_identity_count": 20,
        "source_selector": "B_plus",
        "readout_selector": "P",
        "state_metric": "I20",
        "source_trial_vectors": "I10",
    }


def test_b1_task11_owner_internal_helper_and_file_scope_are_exact() -> None:
    registry = _load_registry()
    b1 = registry["tasks"]["B1"]

    assert b1["modules"] == [
        "rulespace_v3.application_authority_v3",
        "rulespace_v3.task11_runner",
    ]
    assert b1["implementation_files"] == [
        {
            "action": "CREATE",
            "path": "rulespace_v3/application_authority_v3.py",
        },
        {
            "action": "CREATE",
            "path": "tests/test_v3m0_application_authority_v3.py",
        },
        {"action": "MODIFY", "path": "rulespace_v3/task11_runner.py"},
        {"action": "MODIFY", "path": "tests/test_v3m0_task11_runner.py"},
    ]
    helper = _api(
        registry,
        "B1",
        "_run_task11_window_calibration_from_task8_replay",
    )
    assert helper == {
        "name": "_run_task11_window_calibration_from_task8_replay",
        "visibility": "owner-internal",
        "args": [
            {
                "name": "historical_parent",
                "wire_type": "VerifiedParentFreeze",
            },
            {
                "name": "task8_replay",
                "wire_type": "CurrentTask8ControlReplay",
            },
        ],
        "returns": "WindowCalibrationOutcome",
        "raw_hydration_allowed": False,
        "semantics": (
            "accept only the exact historical Parent-v1 and exact "
            "CurrentTask8ControlReplay; internally rebuild the "
            "authority-neutral legacy registry/window, share the same "
            "six-order numerical core with the unchanged public V2 runner, "
            "and return a raw WindowCalibrationOutcome carrying no authority; "
            "no current_registry, current_window, or parent_freeze_v2_sha "
            "argument exists"
        ),
    }
    assert not {
        "current_registry",
        "current_window",
        "parent_freeze_v2_sha",
    } & {item["name"] for item in helper["args"]}


def test_b1_mixed_registry_v6_contract_mutations_die() -> None:
    registry = _load_registry()
    registry_field = _field(
        registry,
        "WindowThresholdCalibrationV3",
        "current_application_registry_v3",
    )
    assert registry_field == {
        "name": "current_application_registry_v3",
        "wire_type": "canonical-json-object",
        "presence": "required",
        "literal_domain": [],
        "tuple_cardinality": None,
        "nested_record": None,
        "constraints": [
            "exact full current_application_registry_v3_payload from the live Parent-v3 reviewed candidate",
            "exactly 20 entries with parent_v1_ordinal, authority_tag, and full V2-or-V3 application_authority body",
        ],
    }

    attacks = []

    hostile = copy.deepcopy(registry)
    hostile["record_catalog"]["WindowThresholdCalibrationV3"]["field_specs"] = [
        item
        for item in hostile["record_catalog"]["WindowThresholdCalibrationV3"][
            "field_specs"
        ]
        if item["name"] != "current_application_registry_v3"
    ]
    attacks.append(hostile)

    hostile = copy.deepcopy(registry)
    refs = hostile["record_catalog"]["WindowThresholdCalibrationV3"]["field_specs"]
    next(item for item in refs if item["name"] == "calibration_control_replay_refs")[
        "tuple_cardinality"
    ]["value"] = "2"
    attacks.append(hostile)

    hostile = copy.deepcopy(registry)
    ref_fields = hostile["record_catalog"]["ParentV3CalibrationControlReplayRefV1"][
        "field_specs"
    ]
    ref_fields.insert(
        2,
        {
            "name": "parent_freeze_v2_sha",
            "wire_type": "sha256",
            "presence": "required",
            "literal_domain": [],
            "tuple_cardinality": None,
            "nested_record": None,
            "constraints": ["invented legacy root"],
        },
    )
    attacks.append(hostile)

    hostile = copy.deepcopy(registry)
    tag = next(
        item
        for item in hostile["record_catalog"]["ParentV3CalibrationControlReplayRefV1"][
            "field_specs"
        ]
        if item["name"] == "authority_tag"
    )
    tag["literal_domain"] = ["REFROZEN_CURRENT_V3"]
    attacks.append(hostile)

    hostile = copy.deepcopy(registry)
    hostile["record_catalog"]["WindowThresholdCalibrationV3"]["record_invariants"] = [
        item
        for item in hostile["record_catalog"]["WindowThresholdCalibrationV3"][
            "record_invariants"
        ]
        if "old and replacement C19" not in item
    ]
    attacks.append(hostile)

    for field_name in (
        "application_authority_v2",
        "scenario_authority_v2",
        "response_contract_v2",
    ):
        hostile = copy.deepcopy(registry)
        field = _field(
            hostile,
            "ParentV3CalibrationControlReplayRefV1",
            field_name,
        )
        field["wire_type"] = "canonical-json-object"
        field["nested_record"] = None
        attacks.append(hostile)

    for attacked in attacks:
        assert (
            _canonical_digest(_record_catalog_golden_tuple(attacked))
            != EXPECTED_RECORD_CATALOG_GOLDEN_SHA256
        )

    task_attacks = []
    hostile = copy.deepcopy(registry)
    helper = _api(
        hostile,
        "B1",
        "_run_task11_window_calibration_from_task8_replay",
    )
    helper["args"].append(
        {"name": "current_registry", "wire_type": "CurrentControlRegistryV2"}
    )
    task_attacks.append(hostile)

    hostile = copy.deepcopy(registry)
    hostile["tasks"]["B1"]["modules"].remove("rulespace_v3.task11_runner")
    task_attacks.append(hostile)

    for attacked in task_attacks:
        assert (
            _canonical_digest(_task_contract_golden_tuple(attacked))
            != EXPECTED_TASK_CONTRACT_GOLDEN_SHA256
        )


def _assert_synthetic_schema_literals(registry: dict[str, object]) -> None:
    expected = {
        "SyntheticApplicationBasisProtocol": (
            "protocol_schema_version",
            "v3m0.synthetic-application-basis-protocol.wire.v1",
        ),
        "SyntheticApplicationGridProtocol": (
            "protocol_schema_version",
            "v3m0.synthetic-application-grid-protocol.wire.v1",
        ),
        "SyntheticApplicationReadoutProtocol": (
            "protocol_schema_version",
            "v3m0.synthetic-application-readout-protocol.wire.v1",
        ),
        "SyntheticApplicationProtocolConstants": (
            "constants_schema_version",
            "v3m0.synthetic-application-protocol-constants.wire.v1",
        ),
        "SyntheticApplicationOperation": (
            "operation_schema_version",
            "v3m0.synthetic-application-operation.wire.v1",
        ),
        "SyntheticApplicationPredictionProfile": (
            "prediction_schema_version",
            "v3m0.synthetic-application-prediction-profile.wire.v1",
        ),
    }
    for record_name, (field_name, schema_literal) in expected.items():
        version = _field(registry, record_name, field_name)
        assert version["wire_type"] == "str"
        assert version["literal_domain"] == [schema_literal]
        assert version["constraints"] == ["exact schema literal"]


def test_six_synthetic_version_literals_are_exact_and_hostile_mutations_die() -> None:
    registry = _load_registry()
    _assert_synthetic_schema_literals(registry)

    attacks = (
        ("literal_domain", []),
        ("literal_domain", ["v3m0.forged.v1"]),
        ("constraints", []),
        ("wire_type", "object"),
    )
    synthetic_records = (
        ("SyntheticApplicationBasisProtocol", "protocol_schema_version"),
        ("SyntheticApplicationGridProtocol", "protocol_schema_version"),
        ("SyntheticApplicationReadoutProtocol", "protocol_schema_version"),
        ("SyntheticApplicationProtocolConstants", "constants_schema_version"),
        ("SyntheticApplicationOperation", "operation_schema_version"),
        ("SyntheticApplicationPredictionProfile", "prediction_schema_version"),
    )
    for record_name, field_name in synthetic_records:
        for attacked_key, attacked_value in attacks:
            hostile = copy.deepcopy(registry)
            _field(hostile, record_name, field_name)[attacked_key] = attacked_value
            _assert_contract_death(
                lambda value=hostile: _assert_synthetic_schema_literals(value)
            )


def test_corrected_existing_record_owners_match_production_definitions() -> None:
    registry = _load_registry()
    assert registry["record_catalog"]["DirectionPathClosure"]["canonical_owner"] == (
        "rulespace_v3.parent_freeze"
    )
    assert (
        registry["record_catalog"]["InstabilityGrowthCounterWitness"]["canonical_owner"]
        == "rulespace_v3.instability"
    )
    assert (
        registry["record_catalog"]["ResponseBlockAttemptOutcome"]["canonical_owner"]
        == "rulespace_v3.calibration_authority"
    )


def test_b3_b6_freeze_transition_metric_grids_and_recursive_certificate() -> None:
    registry = _load_registry()

    b3_apis = registry["tasks"]["B3"]["apis"]
    assert [api["name"] for api in b3_apis] == [
        "issue_transition_authority_v3",
        "verify_transition_authority_v3",
        "verify_transition_pair_v3",
    ]
    assert b3_apis[0]["args"] == [
        {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
        {
            "name": "materialization",
            "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3",
        },
        {
            "name": "factory_role",
            "wire_type": "Literal[actual,matched_ablated]",
        },
    ]
    assert b3_apis[0]["returns"] == "VerifiedTransitionAuthorityV3"
    assert b3_apis[1]["args"] == [
        {"name": "transition", "wire_type": "TransitionAuthorityV3"},
        {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
        {
            "name": "materialization",
            "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3",
        },
    ]
    assert b3_apis[1]["returns"] == "VerifiedTransitionAuthorityV3"
    assert b3_apis[2]["args"] == [
        {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
        {
            "name": "materialization",
            "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3",
        },
        {
            "name": "actual_transition",
            "wire_type": "VerifiedTransitionAuthorityV3",
        },
        {
            "name": "matched_ablated_transition",
            "wire_type": "VerifiedTransitionAuthorityV3",
        },
    ]
    assert b3_apis[2]["returns"] == (
        "tuple[VerifiedTransitionAuthorityV3,VerifiedTransitionAuthorityV3]"
    )
    assert registry["tasks"]["B3"]["opaque_wrappers"] == [
        "VerifiedTransitionAuthorityV3"
    ]

    assert _fields(registry, "MeasuredTransition") == [
        "transition_schema_version",
        "parent_freeze_sha",
        "prestructure_authority_sha",
        "factory_sha",
        "factory_role",
        "state_schema_id",
        "channel_order",
        "spatial_shape",
        "dt",
        "boundary_manifest_id",
        "state_basis_convention_id",
        "kernel",
        "support_offsets",
        "support_sha",
        "macro_steps",
        "transition_sha",
    ]
    assert _field(registry, "MeasuredTransition", "factory_role")["literal_domain"] == [
        "actual",
        "matched_ablated",
    ]
    assert _field(registry, "MeasuredTransition", "boundary_manifest_id")[
        "literal_domain"
    ] == ["periodic-v1"]
    assert _field(registry, "MeasuredTransition", "state_basis_convention_id")[
        "literal_domain"
    ] == ["channel-identity-v1"]
    assert _field(registry, "MeasuredTransition", "macro_steps")["literal_domain"] == [
        1
    ]
    assert _fields(registry, "TransitionAuthorityV3") == [
        "transition_authority_schema_version",
        "materialization",
        "factory_binding",
        "measured_transition",
        "transition_authority_sha",
    ]
    for field_name, nested in (
        ("materialization", "ApplicationScenarioMaterializationV3"),
        ("factory_binding", "FactoryBranchBindingV3"),
        ("measured_transition", "MeasuredTransition"),
    ):
        assert (
            _field(registry, "TransitionAuthorityV3", field_name)["nested_record"]
            == nested
        )

    assert _fields(registry, "MetricSignedSupportAttestationV1") == [
        "attestation_schema_version",
        "parent_freeze_v3_sha",
        "current_application_authority_v3_sha",
        "current_scenario_authority_v3_sha",
        "response_contract_v3_sha",
        "metric_support_protocol_sha",
        "application_scenario_materialization_v3_sha",
        "factory_sha",
        "factory_role",
        "state_schema_id",
        "channel_order",
        "spatial_shape",
        "metric_kind",
        "metric_support_offsets",
        "metric_support_sha",
        "attestation_sha",
    ]
    metric_api = _api(registry, "B4", "issue_c19_metric_signed_support_attestation_v1")
    assert metric_api["args"] == [
        {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
        {
            "name": "materialization",
            "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3",
        },
        {
            "name": "factory_role",
            "wire_type": "Literal[actual,matched_ablated]",
        },
    ]
    assert metric_api["returns"] == "VerifiedMetricSignedSupportAttestationV1"

    assert _fields(registry, "ResponseKGridManifest") == [
        "grid_schema_version",
        "qualification_profile",
        "spatial_ndim",
        "torus_denominators",
        "reciprocal_indices",
        "direction_manifest",
        "response_grid_sha",
    ]
    assert _fields(registry, "DynamicsKGridManifest") == [
        "grid_schema_version",
        "qualification_profile",
        "spatial_ndim",
        "torus_denominators",
        "reciprocal_indices",
        "dynamics_grid_sha",
    ]
    assert _fields(registry, "BridgeKGridManifest") == [
        "grid_schema_version",
        "spatial_shape",
        "torus_denominators",
        "reciprocal_indices",
        "bridge_grid_sha",
    ]
    assert registry["grid_freeze"] == {
        "response": "directional-momentum-shell-path-v1; exact one C19 directional node",
        "dynamics_zero": "denominators=(1,); indices=((0,),); support=((0,),)",
        "bridge_zero": "denominators=(8,); indices=((0,),); support=((0,),)",
        "metric_support": "constant-state-v1; I20; offsets=((0,),)",
        "grids_are_not_interchangeable": True,
        "caller_supplied_points_allowed": False,
    }

    assert _fields(registry, "DynamicsCertificateV3") == [
        "certificate_schema_version",
        "parent_freeze_v3",
        "materialization",
        "transition_authority",
        "metric_attestation",
        "bridge_grid_authority",
        "dynamics_grid_authority",
        "prestructure_authority",
        "structure",
        "reality",
        "stability_metric",
        "fp64_enclosure_protocol",
        "full_state_bridge_spec",
        "full_state_bridge_audit",
        "structure_residual",
        "metric_residual",
        "spectral_margins",
        "normalized_metric_residual",
        "power_drift",
        "runtime",
        "certificate_sha",
    ]
    for name, nested in (
        ("parent_freeze_v3", "ParentFreezeV3Manifest"),
        ("materialization", "ApplicationScenarioMaterializationV3"),
        ("transition_authority", "TransitionAuthorityV3"),
        ("metric_attestation", "MetricSignedSupportAttestationV1"),
        ("bridge_grid_authority", "BridgeGridAuthorityV3"),
        ("dynamics_grid_authority", "DynamicsGridAuthorityV3"),
        ("prestructure_authority", "PrestructureAuthority"),
        ("structure", "StructureManifest"),
        ("reality", "RealityCertificate"),
        ("stability_metric", "StabilityMetricWitness"),
        ("fp64_enclosure_protocol", "Fp64EnclosureProtocol"),
        ("full_state_bridge_spec", "FullStateBridgeSpec"),
        ("full_state_bridge_audit", "BridgeAudit"),
        ("structure_residual", "LaurentResidualCertificate"),
        ("metric_residual", "LaurentResidualCertificate"),
        ("spectral_margins", "SpectralMarginCoverage"),
        ("normalized_metric_residual", "NormalizedMetricResidualAudit"),
        ("power_drift", "PowerDriftAudit"),
        ("runtime", "RuntimeEvidenceManifest"),
    ):
        assert (
            _field(registry, "DynamicsCertificateV3", name)["nested_record"] == nested
        )

    b6_apis = registry["tasks"]["B6"]["apis"]
    assert [api["name"] for api in b6_apis] == [
        "certify_transition_dynamics_v3",
        "verify_dynamics_certificate_v3",
        "verify_dynamics_certification_outcome_v3",
    ]
    upstream_args = [
        {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
        {
            "name": "materialization",
            "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3",
        },
        {
            "name": "transition",
            "wire_type": "VerifiedTransitionAuthorityV3",
        },
        {
            "name": "metric_attestation",
            "wire_type": "VerifiedMetricSignedSupportAttestationV1",
        },
        {
            "name": "bridge_grid",
            "wire_type": "VerifiedBridgeGridAuthorityV3",
        },
        {
            "name": "dynamics_grid",
            "wire_type": "VerifiedDynamicsGridAuthorityV3",
        },
    ]
    assert b6_apis[0]["args"] == upstream_args
    assert b6_apis[0]["returns"] == "VerifiedDynamicsCertificationOutcomeV3"
    assert b6_apis[1]["args"] == [
        {"name": "certificate", "wire_type": "DynamicsCertificateV3"},
        *upstream_args,
    ]
    assert b6_apis[1]["returns"] == "VerifiedDynamicsCertificateV3"
    assert b6_apis[2]["args"] == [
        {"name": "outcome", "wire_type": "DynamicsCertificationOutcomeV3"},
        *upstream_args,
    ]
    assert b6_apis[2]["returns"] == "VerifiedDynamicsCertificationOutcomeV3"
    assert registry["tasks"]["B6"]["opaque_wrappers"] == [
        "VerifiedDynamicsCertificationOutcomeV3",
        "VerifiedDynamicsCertificateV3",
    ]
    forbidden_api_wires = {
        "VerifiedFactory",
        "VerifiedTransition",
        "VerifiedPrestructureAuthority",
        "StructureManifest",
        "StabilityMetricWitness",
        "FullStateBridgeSpec",
        "DynamicsKGridManifest",
        "RuntimeEvidenceManifest",
    }
    for task_id in ("B3", "B6"):
        exposed = {
            arg["wire_type"]
            for api in registry["tasks"][task_id]["apis"]
            for arg in api["args"]
        }
        assert exposed.isdisjoint(forbidden_api_wires)

    assert registry["enum_catalog"]["DynamicsCertificationFailure"] == [
        "prestructure_invalid",
        "transition_invalid",
        "reality_invalid",
        "laurent_resource_exceeded",
        "structure_raw_unresolved",
        "metric_raw_unresolved",
        "spectral_coverage_unresolved",
        "normalized_metric_unresolved",
        "full_state_bridge_failed",
        "power_drift_unresolved",
        "certified_instability_counterwitness",
    ]
    assert (
        "success iff failure is null and certificate is non-null"
        in (
            registry["record_catalog"]["DynamicsCertificationOutcomeV3"][
                "record_invariants"
            ]
        )
    )
    assert (
        "failure iff failure is non-null and certificate is null"
        in (
            registry["record_catalog"]["DynamicsCertificationOutcomeV3"][
                "record_invariants"
            ]
        )
    )


def test_b7_restores_typed_reference_shell_pair_chain_without_half_pair() -> None:
    registry = _load_registry()

    assert _fields(registry, "ResponseRunSpec") == [
        "run_spec_schema_version",
        "run_spec_id",
        "window_protocol_sha",
        "control_registry_entry_sha",
        "fejer_order",
        "state_schema_id",
        "channel_order",
        "source_basis",
        "readout_basis",
        "spatial_shape",
        "response_grid",
        "source_readout_bridge_grid",
        "source_readout_bridge_steps",
        "source_trial_vectors",
        "bridge_tolerance",
        "spec_sha",
    ]
    assert _field(registry, "ResponseRunSpec", "source_readout_bridge_steps")[
        "constraints"
    ] == ["exact frozen WindowCalibrationProtocol value", "contains a value > 1"]
    assert _field(registry, "ResponseRunSpec", "source_trial_vectors")[
        "constraints"
    ] == [
        "full recursive raw body",
        "full I_nsource columns; C19 exact I10; no sampling or rank reduction",
    ]

    expected_layers = {
        "reference": [
            "EndpointReferenceSpec",
            "EndpointReferenceProjector",
            "EndpointReferenceAttemptAudit",
            "EndpointReferenceOutcome",
        ],
        "shell": [
            "EndpointShellSpec",
            "ShellPointAudit",
            "EndpointShellManifest",
            "ShellCandidatePointAttempt",
            "EndpointShellAttemptAudit",
            "EndpointShellOutcome",
        ],
        "paired": [
            "SourceReadoutBridgeMatrixAudit",
            "SourceReadoutBridgeAudit",
            "SourceReadoutResponse",
            "PairedFilteredResponse",
            "SourceReadoutBranchAttemptAudit",
            "PairedResponseAttemptAudit",
            "PairedResponseOutcome",
        ],
    }
    assert registry["response_chain"]["raw_layers"] == expected_layers
    assert registry["response_chain"]["opaque_outcomes"] == [
        "VerifiedEndpointReferenceOutcome",
        "VerifiedEndpointShellOutcome",
        "VerifiedPairedResponseOutcome",
    ]
    assert registry["response_chain"]["selection_branch"] == "actual"
    assert registry["response_chain"]["matched_reselection_allowed"] is False
    assert registry["response_chain"]["success_failure_xor"] is True
    assert registry["response_chain"]["half_pair_capability_allowed"] is False
    assert registry["enum_catalog"]["EndpointReferenceFailure"] == [
        "phase_band_empty",
        "phase_band_nonunique",
        "rank_mismatch",
        "participation_failed",
        "runner_up_margin_failed",
        "projector_invalid",
    ]
    assert registry["enum_catalog"]["EndpointShellFailure"] == [
        "phase_band_empty",
        "phase_separation_failed",
        "gap_failed",
        "participation_failed",
        "reference_ambiguous",
        "runner_up_margin",
        "loop_inconsistent",
        "projector_invalid",
    ]
    assert registry["enum_catalog"]["PairedResponseFailure"] == [
        "qualification_invalid",
        "input_binding_invalid",
        "actual_response_failed",
        "ablated_response_failed",
        "actual_bridge_failed",
        "ablated_bridge_failed",
    ]
    for outcome in (
        "EndpointReferenceOutcome",
        "EndpointShellOutcome",
        "PairedResponseOutcome",
    ):
        invariants = registry["record_catalog"][outcome]["record_invariants"]
        assert any("success iff" in item for item in invariants)
        assert any("failure iff" in item for item in invariants)


def test_b8_orders_evidence_blocks_and_geometry_and_freezes_c19_boundary() -> None:
    registry = _load_registry()
    dag = registry["import_dag"]

    evidence_fields = _fields(registry, "ClosedControlApplicationEvidenceV3")
    assert "paired_response_outcome" in evidence_fields
    assert not any(
        "block" in name or "geometry_evaluation" in name for name in evidence_fields
    )
    assert registry["record_catalog"]["ResponseBlock"]["canonical_owner"] == (
        "rulespace_v3.blocks"
    )
    assert (
        registry["record_catalog"]["C19ControlGeometryEvaluationV3"]["canonical_owner"]
        == "rulespace_v3.control_geometry_evaluation_v3"
    )
    assert "rulespace_v3.control_application_evidence_v3" in dag["rulespace_v3.blocks"]
    assert (
        "rulespace_v3.blocks" not in dag["rulespace_v3.control_application_evidence_v3"]
    )
    assert "rulespace_v3.blocks" in dag["rulespace_v3.control_geometry_evaluation_v3"]

    boundary = registry["c19_geometry_boundary"]
    assert boundary["claim_ceiling"] == "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY"
    assert boundary["causal_contrast_role"] == "NULL_INTERVENTION_INVARIANCE_CONTROL"
    assert boundary["physical_anchor_eligibility"] == "INELIGIBLE"
    assert boundary["family_eligibility"] == "INELIGIBLE"
    assert boundary["pre_response_state"] == "NOT_EVALUATED_PRE_RESPONSE"
    assert boundary["required_predicate_ids"] == [
        "complete-nonzero-gram-support-selection",
        "whitened-coisometry-or-incidence-range-preservation",
        "incidence-rank-six",
        "gauge-contained-in-incidence-kernel-dimension-four",
        "tt2-gauge4-row4-pairwise-orthogonal-complete-decomposition",
        "constraint-kernel-tt-plus-gauge-compatible-projector-and-metric",
        "actual-source-readout-share-endpoint-shell-and-finite-paired-response",
    ]
    assert boundary["evaluation_requires_verified_response_blocks"] is True
    assert boundary["eligible_for_physical_or_family_claim"] is False


def test_b9_replays_parent_v3_controls_and_freezes_typed_terminal_outputs() -> None:
    registry = _load_registry()
    execution = registry["v3m0_execution_freeze"]

    assert execution["parent_v3_replay_case_ids"] == [
        *(f"C{index:02d}" for index in range(1, 19)),
        "C20",
    ]
    assert execution["c19_route"] == "CurrentApplicationAuthorityV3 only"
    assert execution["v2_opaque_authority_allowed"] is False
    assert execution["denied_opaque_types"] == [
        "VerifiedParentFreeze",
        "VerifiedParentFreezeV2",
        "VerifiedWindowThresholdCalibration",
        "VerifiedCalibrationApplicationPermit",
        "VerifiedWindowThresholdCalibrationV2",
        "VerifiedCalibrationApplicationPermitV2",
        "VerifiedV3M0ApplicationScenarioMaterializationV2",
        "VerifiedApplicationScenarioResponseProtocolV2",
        "VerifiedApplicationPairedResponseOutcomeV2",
    ]
    assert execution["representation_invariant_ids"] == [
        *(f"I{index:02d}" for index in range(1, 10))
    ]
    assert execution["typed_termination_routes"] == [
        ["C11:null", "activation", "RESPONSE_NULL"],
        ["C11:grey", "activation", "RESPONSE_GREY"],
        ["C11:signal", "success", None],
        ["C13:both-zero", "activation", "RESPONSE_NULL"],
        ["C14:endpoint-ambiguous", "endpoint_shell", "ENDPOINT_SHELL_AMBIGUOUS"],
        ["C14:response-null", "activation", "RESPONSE_NULL"],
        ["C14:trace-unclassified", "trace", "TRACE_UNCLASSIFIED"],
        ["C14:unstable", "stability", "UNSTABLE"],
    ]
    assert execution["scenario_item_tags"] == [
        "BLOCK_SUCCESS",
        "EXPECTED_TYPED_TERMINATION",
        "ANALYSIS_CONTROL",
    ]
    assert (
        _field(registry, "ParentV3ScenarioReplayAuthorityV1", "application_spec")[
            "nested_record"
        ]
        == "V3M0SyntheticControlApplicationSpec"
    )
    assert (
        _field(registry, "ParentV3ScenarioReplayAuthorityV1", "scenario_specs")[
            "nested_record"
        ]
        == "ApplicationScenarioExecutionSpec"
    )
    assert _field(
        registry, "ResponseBlockAttemptOutcome", "downstream_capability_issued"
    )["literal_domain"] == [False]
    assert _field(registry, "DeterministicSeriesControlOutcome", "series_class")[
        "literal_domain"
    ] == ["clean-zero", "true-floor"]
    assert _field(registry, "DeterministicSeriesControlOutcome", "decision_rule")[
        "literal_domain"
    ] == ["D-M2-6"]

    assert registry["artifact_contracts"] == [
        {
            "order": 0,
            "relative_path": "data/results/v3m0_parent_v3.json",
            "artifact_kind": "PARENT_V3_FREEZE",
            "artifact_schema_id": "v3m0.parent-freeze.v3",
        },
        {
            "order": 1,
            "relative_path": "data/results/v3m0_controls_v3.json",
            "artifact_kind": "V3M0_CONTROLS_RESULT",
            "artifact_schema_id": "v3m0.controls-result.v3",
        },
        {
            "order": 2,
            "relative_path": "data/results/v3m0_response_v3.json",
            "artifact_kind": "V3M0_RESPONSE_RESULT",
            "artifact_schema_id": "v3m0.response-result.v3",
        },
        {
            "order": 3,
            "relative_path": "data/runtime/v3m0_state.json",
            "artifact_kind": "V3M0_STATE_DECISION",
            "artifact_schema_id": "v3m0.state-decision.v3",
        },
    ]


def test_b10_portable_root_is_recursive_signed_and_state_ceiling_is_exact() -> None:
    registry = _load_registry()

    assert _fields(registry, "PortableEnvelopeRootV1") == [
        "portable_root_schema_version",
        "stage_id",
        "stage_sequence",
        "previous_portable_envelope_sha",
        "typed_state_id",
        "next_stage_ceiling_id",
        "artifact_root_sha",
        "unsigned_statement_sha",
        "portable_envelope_sha",
    ]
    for record in ("CampaignStageOutputEnvelopeV1", "V3M0CheckpointEnvelopeV1"):
        assert _field(registry, record, "portable_root")["nested_record"] == (
            "PortableEnvelopeRootV1"
        )
    assert (
        _field(registry, "CampaignStageOutputEnvelopeV1", "stage_freeze")[
            "nested_record"
        ]
        == "CampaignStageFreezeV1"
    )
    assert (
        _field(registry, "CampaignStageOutputEnvelopeV1", "run_permit")["nested_record"]
        == "CampaignStageRunPermitV1"
    )
    assert (
        _field(registry, "V3M0CheckpointEnvelopeV1", "parent_freeze_v3")[
            "nested_record"
        ]
        == "ParentFreezeV3Manifest"
    )
    assert (
        _field(registry, "V3M0CheckpointEnvelopeV1", "run_outcome")["nested_record"]
        == "V3M0RunOutcomeV3"
    )

    freeze_fields = _fields(registry, "CampaignStageFreezeV1")
    for field in (
        "previous_envelope_sha",
        "taskbook_ref",
        "taskbook_body_utf8",
        "stage_manifest_ref",
        "stage_manifest_body",
        "stage_manifest_schema_id",
        "source_closure",
        "preparation_epoch_commit_sha",
        "signing_epoch_commit_sha",
        "reviewer_registry",
        "review_receipts",
        "strict_diff_audit",
    ):
        assert field in freeze_fields

    assert (
        _field(registry, "V3M0RunManifestV3", "artifact_contracts")["nested_record"]
        == "V3M0ArtifactContractV3"
    )
    assert (
        "PortableArtifactRef"
        not in _field(registry, "V3M0RunManifestV3", "artifact_contracts")["wire_type"]
    )

    assert registry["state_ceiling_map"] == {
        "HALT-V3M0-FORMAL": "STOP",
        "HALT-V3M0-CONTROL": "STOP",
        "HALT-V3M0-IDENTIFIABILITY": "STOP",
        "HALT-V3M0-WINDOW": "STOP",
        "READY-V3-M1-ANCHOR-CERTIFICATION": "V3-M1",
    }
    assert registry["portable_replay_semantics"] == (
        "portable verification is idempotent; duplicate consumption is rejected "
        "only by the next-stage issuer against its fixed previous envelope root"
    )
    assert "REPLAYED_ENVELOPE" not in registry["tasks"]["B10"]["typed_failures"]
    assert registry["tasks"]["B10"]["reviewer_primitives_owner"] == (
        "rulespace_v3.campaign_stage_authority_v1"
    )
    assert not any(
        dependency
        in {
            "rulespace_v3.parent_reviewer_keys_v1",
            "rulespace_v3.parent_signing_audit_v1",
        }
        for dependency in registry["import_dag"][
            "rulespace_v3.campaign_stage_authority_v1"
        ]
    )

    b10_apis = registry["tasks"]["B10"]["apis"]
    assert [api["name"] for api in b10_apis] == [
        "verify_campaign_stage_freeze_v1",
        "issue_campaign_stage_run_permit_v1",
        "verify_campaign_stage_output_envelope_v1",
        "issue_v3m0_checkpoint_envelope_v1",
        "verify_v3m0_checkpoint_envelope_v1",
    ]
    previous_input = (
        "Optional[Union[VerifiedCampaignStageOutputEnvelopeV1,"
        "CampaignStageOutputEnvelopeV1]]"
    )
    stage_input = "Union[VerifiedCampaignStageFreezeV1,CampaignStageFreezeV1]"
    permit_input = "Union[VerifiedCampaignStageRunPermitV1,CampaignStageRunPermitV1]"
    parent_input = "Union[VerifiedParentFreezeV3,ParentFreezeV3Manifest]"
    trust_anchor = "VerifiedCampaignCheckpointTrustAnchorV1"
    trust_anchor_arg = {"name": "trust_anchor", "wire_type": trust_anchor}
    source_bundle = "tuple[tuple[PortableSourceRefV1,bytes],...]"
    common_detached_args = [
        {"name": "taskbook_bytes", "wire_type": "bytes"},
        {"name": "stage_manifest_bytes", "wire_type": "bytes"},
        {"name": "source_bundle", "wire_type": source_bundle},
        {"name": "reviewer_key_source_bytes", "wire_type": "bytes"},
        {"name": "preparation_source_bytes", "wire_type": "bytes"},
        {"name": "signing_source_bytes", "wire_type": "bytes"},
    ]
    assert b10_apis[0]["args"] == [
        trust_anchor_arg,
        {"name": "freeze", "wire_type": "CampaignStageFreezeV1"},
        {"name": "previous_envelope_input", "wire_type": previous_input},
        *common_detached_args,
    ]
    assert b10_apis[1]["args"] == [
        trust_anchor_arg,
        {
            "name": "stage_freeze",
            "wire_type": "VerifiedCampaignStageFreezeV1",
        },
    ]
    assert b10_apis[2]["args"] == [
        trust_anchor_arg,
        {"name": "envelope", "wire_type": "CampaignStageOutputEnvelopeV1"},
        {"name": "stage_freeze_input", "wire_type": stage_input},
        {"name": "run_permit_input", "wire_type": permit_input},
        {"name": "previous_envelope_input", "wire_type": previous_input},
        *common_detached_args,
        {"name": "artifact_bundle", "wire_type": "tuple[bytes,...]"},
    ]
    assert b10_apis[3]["args"][0] == trust_anchor_arg
    assert b10_apis[4]["args"] == [
        trust_anchor_arg,
        {"name": "checkpoint", "wire_type": "V3M0CheckpointEnvelopeV1"},
        {"name": "stage_freeze_input", "wire_type": stage_input},
        {"name": "run_permit_input", "wire_type": permit_input},
        {"name": "parent_input", "wire_type": parent_input},
        {"name": "previous_envelope_input", "wire_type": previous_input},
        *common_detached_args,
        {
            "name": "old_s_source_bundle",
            "wire_type": "tuple[tuple[SignedSourceRefV2,bytes],...]",
        },
        {"name": "old_s_reviewer_key_source_bytes", "wire_type": "bytes"},
        {"name": "old_s_signing_literal_source_bytes", "wire_type": "bytes"},
        {
            "name": "artifact_bundle",
            "wire_type": "tuple[bytes,bytes,bytes,bytes]",
        },
    ]
    assert all(api["args"][0] == trust_anchor_arg for api in b10_apis)
    assert registry["tasks"]["B10"]["typed_failures"][0] == "TRUST_ANCHOR_INVALID"
    assert registry["tasks"]["B10"]["opaque_wrappers"][0] == trust_anchor

    assert registry["portable_trust_anchor_freeze"] == {
        "wrapper_type": "VerifiedCampaignCheckpointTrustAnchorV1",
        "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
        "provisioning": "OUT_OF_BAND_TRUST_STORE_ONLY",
        "public_issuer_exists": False,
        "raw_or_serialized_anchor_allowed": False,
        "caller_supplied_registry_or_key_bootstrap_allowed": False,
        "ordered_pins": [
            "anchor_profile_id",
            "stage_family_id",
            "trust_epoch_id",
            "trusted_checkpoint_or_genesis_sha",
            "trusted_previous_portable_envelope_sha",
            "campaign_reviewer_registry_sha",
            "campaign_reviewer_key_source_sha",
            "parent_reviewer_key_source_sha",
            "parent_signing_literal_source_sha",
        ],
        "verification_order": [
            "require exact live trust-anchor wrapper identity",
            "join stage family, trust epoch and pinned checkpoint/root",
            "join embedded campaign registry and key-source bytes to anchor pins",
            "join Parent old-S key/literal source bytes to anchor pins",
            "only then verify source closures, receipts and envelope signatures",
        ],
        "anchor_rotation": (
            "out-of-band only after separately authenticated checkpoint approval; "
            "never from envelope contents"
        ),
        "wrong_anchor_failure": "TRUST_ANCHOR_INVALID",
        "rekeyed_self_bootstrap_failure": "UNTRUSTED_REVIEWER_KEY",
    }

    assert registry["portable_verifier_freeze"] == {
        "detached_cross_machine_supported": True,
        "repository_or_git_state_required": False,
        "out_of_band_live_trust_anchor_required": True,
        "stage_freeze_input_types": [
            "VerifiedCampaignStageFreezeV1",
            "CampaignStageFreezeV1",
        ],
        "run_permit_input_types": [
            "VerifiedCampaignStageRunPermitV1",
            "CampaignStageRunPermitV1",
        ],
        "parent_input_types": [
            "VerifiedParentFreezeV3",
            "ParentFreezeV3Manifest",
        ],
        "source_bundle_entry": "(signed ref, exact raw bytes) in manifest order",
        "old_s_inputs": [
            "old_s_source_bundle",
            "old_s_reviewer_key_source_bytes",
            "old_s_signing_literal_source_bytes",
        ],
        "detached_positive_route": (
            "exact out-of-band live trust-anchor plus frozen stage/permit/Parent "
            "bodies and exact source, key, manifest, taskbook and artifact bytes "
            "verify without importing repository literals"
        ),
        "detached_death_cases": [
            "missing_trust_anchor",
            "wrong_trust_anchor",
            "caller_rekeyed_self_bootstrap",
            "missing_stage_freeze_body",
            "missing_run_permit_body",
            "missing_parent_body",
            "missing_source_bundle",
            "missing_reviewer_key_source_bytes",
            "missing_old_s_source_bundle",
            "missing_old_s_reviewer_key_source_bytes",
            "missing_old_s_signing_literal_source_bytes",
            "mutated_source_bytes",
            "mutated_key_bytes",
        ],
    }


def test_b10_detached_cross_machine_positive_and_death_contracts() -> None:
    trusted_anchor = object()
    required = {
        "trust_anchor",
        "stage_freeze_input",
        "run_permit_input",
        "parent_input",
        "taskbook_bytes",
        "stage_manifest_bytes",
        "source_bundle",
        "reviewer_key_source_bytes",
        "preparation_source_bytes",
        "signing_source_bytes",
        "old_s_source_bundle",
        "old_s_reviewer_key_source_bytes",
        "old_s_signing_literal_source_bytes",
        "artifact_bundle",
    }

    expected_scalar_bytes = {
        "taskbook_bytes": b"taskbook",
        "stage_manifest_bytes": b"manifest",
        "reviewer_key_source_bytes": b"campaign-keys",
        "preparation_source_bytes": b"P-source",
        "signing_source_bytes": b"S-source",
        "old_s_reviewer_key_source_bytes": b"old-S-reviewer-keys",
        "old_s_signing_literal_source_bytes": b"old-S-signing-literals",
    }
    expected_bundles = {
        "source_bundle": (("source-ref", b"source"),),
        "old_s_source_bundle": (("signed-source-ref", b"old-S-source"),),
        "artifact_bundle": (b"a", b"b", b"c", b"d"),
    }

    def detached_complete(values: dict[str, object]) -> bool:
        if set(values) != required:
            return False
        if values["trust_anchor"] is not trusted_anchor:
            return False
        body_types = {
            "stage_freeze_input": "CampaignStageFreezeV1",
            "run_permit_input": "CampaignStageRunPermitV1",
            "parent_input": "ParentFreezeV3Manifest",
        }
        if any(values[name] != expected for name, expected in body_types.items()):
            return False
        if any(
            values[name] != expected for name, expected in expected_scalar_bytes.items()
        ):
            return False
        return all(
            values[name] == expected for name, expected in expected_bundles.items()
        )

    detached = {
        "trust_anchor": trusted_anchor,
        "stage_freeze_input": "CampaignStageFreezeV1",
        "run_permit_input": "CampaignStageRunPermitV1",
        "parent_input": "ParentFreezeV3Manifest",
        **expected_scalar_bytes,
        **expected_bundles,
    }
    assert detached_complete(detached)
    for field_name in required:
        hostile = dict(detached)
        del hostile[field_name]
        assert not detached_complete(hostile)
    for field_name in (
        "source_bundle",
        "old_s_source_bundle",
        "artifact_bundle",
    ):
        hostile = dict(detached)
        hostile[field_name] = ()
        assert not detached_complete(hostile)
    for field_name in (
        "reviewer_key_source_bytes",
        "old_s_reviewer_key_source_bytes",
        "old_s_signing_literal_source_bytes",
    ):
        hostile = dict(detached)
        hostile[field_name] = b""
        assert not detached_complete(hostile)
    for field_name in expected_scalar_bytes:
        hostile = dict(detached)
        hostile[field_name] = expected_scalar_bytes[field_name] + b"-mutated"
        assert not detached_complete(hostile)
    hostile = dict(detached)
    hostile["source_bundle"] = (("source-ref", b"source-mutated"),)
    assert not detached_complete(hostile)
    hostile = dict(detached)
    hostile["old_s_source_bundle"] = (("signed-source-ref", b"old-S-source-mutated"),)
    assert not detached_complete(hostile)

    hostile = dict(detached)
    hostile["trust_anchor"] = object()
    assert not detached_complete(hostile)

    hostile = dict(detached)
    hostile["reviewer_key_source_bytes"] = b"caller-new-dual-keys"
    hostile["old_s_reviewer_key_source_bytes"] = b"caller-new-parent-keys"
    hostile["source_bundle"] = (("caller-source-ref", b"caller-resigned-source"),)
    hostile["old_s_source_bundle"] = (
        ("caller-old-s-ref", b"caller-resigned-old-s-source"),
    )
    assert not detached_complete(hostile)


def test_import_dag_is_complete_acyclic_and_respects_layering() -> None:
    registry = _load_registry()
    dag = registry["import_dag"]
    external_leaves = set(registry["import_dag_external_leaves"])
    assert tuple(registry["import_dag_external_leaves"]) == (
        "rulespace_v3.ablation",
        "rulespace_v3.bridge",
        "rulespace_v3.c19_refreeze_v2",
        "rulespace_v3.calibration_authority",
        "rulespace_v3.causal",
        "rulespace_v3.certificate",
        "rulespace_v3.contracts",
        "rulespace_v3.current_window_replay",
        "rulespace_v3.dynamics",
        "rulespace_v3.evidence",
        "rulespace_v3.factory",
        "rulespace_v3.fp64_protocol",
        "rulespace_v3.frozen_call_graph",
        "rulespace_v3.geometry",
        "rulespace_v3.geometry_protocol_v3",
        "rulespace_v3.grids",
        "rulespace_v3.laurent",
        "rulespace_v3.metric",
        "rulespace_v3.pair_snapshot",
        "rulespace_v3.parent_candidate_v2",
        "rulespace_v3.parent_freeze",
        "rulespace_v3.parent_freeze_v2",
        "rulespace_v3.parent_reviewer_keys_v1",
        "rulespace_v3.parent_signing_literals_v1",
        "rulespace_v3.parent_v2_contracts",
        "rulespace_v3.prestructure",
        "rulespace_v3.qualification",
        "rulespace_v3.registry",
        "rulespace_v3.replay_scope",
        "rulespace_v3.response",
        "rulespace_v3.runtime",
        "rulespace_v3.series_control",
        "rulespace_v3.sigma",
        "rulespace_v3.spectral",
        "rulespace_v3.structure",
        "rulespace_v3.task8_control_replay",
        "rulespace_v3.thresholds",
        "rulespace_v3.trace",
        "rulespace_v3.window",
    )
    assert set(dag).isdisjoint(external_leaves)
    assert all(
        dependency in dag or dependency in external_leaves
        for dependencies in dag.values()
        for dependency in dependencies
    )
    for module_name in external_leaves:
        assert (REPO_ROOT / (module_name.replace(".", "/") + ".py")).is_file()
    required_keys = {
        "rulespace_v3.parent_freeze_v3",
        "rulespace_v3.parent_authority_v3",
        "rulespace_v3.task11_runner",
        "rulespace_v3.application_authority_v3",
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.transition_authority_v3",
        "rulespace_v3.metric_support_authority_v1",
        "rulespace_v3.runtime_grids_v3",
        "rulespace_v3.certificate_v3",
        "rulespace_v3.application_response_v3",
        "rulespace_v3.control_application_evidence_v3",
        "rulespace_v3.blocks",
        "rulespace_v3.control_geometry_evaluation_v3",
        "rulespace_v3.runtime_v3",
        "rulespace_v3.campaign_stage_authority_v1",
        "rulespace_v3.checkpoint_envelope_v1",
        "rulespace_v3.state",
        "experiments.v3m0_preflight",
        "experiments.v3m0_controls",
    }
    assert required_keys <= set(dag)
    assert dag["rulespace_v3.application_authority_v3"] == [
        "rulespace_v3.parent_authority_v3",
        "rulespace_v3.parent_candidate_v3",
        "rulespace_v3.parent_v3_contracts",
        "rulespace_v3.calibration_authority",
        "rulespace_v3.parent_freeze",
        "rulespace_v3.task8_control_replay",
        "rulespace_v3.task11_runner",
    ]
    assert dag["rulespace_v3.task11_runner"] == [
        "rulespace_v3.ablation",
        "rulespace_v3.bridge",
        "rulespace_v3.calibration_authority",
        "rulespace_v3.certificate",
        "rulespace_v3.contracts",
        "rulespace_v3.current_window_replay",
        "rulespace_v3.dynamics",
        "rulespace_v3.evidence",
        "rulespace_v3.factory",
        "rulespace_v3.frozen_call_graph",
        "rulespace_v3.grids",
        "rulespace_v3.metric",
        "rulespace_v3.parent_freeze",
        "rulespace_v3.prestructure",
        "rulespace_v3.qualification",
        "rulespace_v3.registry",
        "rulespace_v3.replay_scope",
        "rulespace_v3.response",
        "rulespace_v3.runtime",
        "rulespace_v3.structure",
        "rulespace_v3.task8_control_replay",
        "rulespace_v3.thresholds",
        "rulespace_v3.window",
    ]

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module: str) -> None:
        if module in visiting:
            raise AssertionError(f"cycle at {module}")
        if module in visited:
            return
        visiting.add(module)
        for dependency in dag.get(module, []):
            visit(dependency)
        visiting.remove(module)
        visited.add(module)

    for module in dag:
        visit(module)

    assert "rulespace_v3.checkpoint_envelope_v1" not in dag["rulespace_v3.runtime_v3"]
    assert (
        "rulespace_v3.runtime_v3" not in dag["rulespace_v3.campaign_stage_authority_v1"]
    )
    assert not any(
        dependency.startswith(("experiments.", "rulespace_gpu."))
        for module, dependencies in dag.items()
        if module.startswith("rulespace_v3.")
        for dependency in dependencies
    )


def _direct_repo_local_imports(module_name: str) -> set[str]:
    module_path = REPO_ROOT / (module_name.replace(".", "/") + ".py")
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    package = module_name.rpartition(".")[0]
    imported: set[str] = set()

    class RuntimeImportVisitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If) -> None:
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                return
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            imported.update(
                alias.name
                for alias in node.names
                if alias.name.startswith("rulespace_v3")
            )

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.level:
                base = package.split(".")
                prefix = ".".join(base[: len(base) - node.level + 1])
                resolved = ".".join(
                    item for item in (prefix, node.module or "") if item
                )
                if resolved.startswith("rulespace_v3"):
                    imported.add(resolved)
            elif node.module and node.module.startswith("rulespace_v3"):
                imported.add(node.module)

    RuntimeImportVisitor().visit(tree)
    return imported


def test_import_dag_ast_and_fresh_imports_match_real_a5_edges() -> None:
    registry = _load_registry()
    dag = registry["import_dag"]
    pinned = registry["import_dag_ast_pinned_nodes"]
    assert pinned == [
        "rulespace_v3.parent_signing_audit_v1",
        "rulespace_v3.parent_freeze_v3",
        "rulespace_v3.parent_authority_v3",
        "rulespace_v3.task11_runner",
    ]
    for module_name in pinned:
        assert _direct_repo_local_imports(module_name) == set(dag[module_name])

        child = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import importlib,json,sys;"
                    "sys.path.insert(0,sys.argv[1]);"
                    "importlib.import_module(sys.argv[2]);"
                    "print(json.dumps(sorted(name for name in sys.modules "
                    "if name.startswith('rulespace_v3'))))"
                ),
                str(REPO_ROOT),
                module_name,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        freshly_loaded = set(json.loads(child.stdout))
        assert module_name in freshly_loaded
        assert set(dag[module_name]) <= freshly_loaded


def test_static_contract_test_imports_no_future_production_module() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
    assert not any(module.startswith("rulespace_v3") for module in imported_modules)
