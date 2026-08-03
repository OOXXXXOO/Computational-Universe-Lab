"""Root contracts for the additive B7 v9.2.1 mechanical erratum.

The tests materialize v9.1, then v9.2, then v9.2.1 without importing or
executing the schema lab.  They cannot issue D0, a scientific status, or a GPU
permit.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
V91_REGISTRY_PATH = REPO_ROOT / "docsv3" / "v3-机器合同-B7-v9.1-registry.json"
V92_OVERLAY_PATH = REPO_ROOT / "docsv3" / "v3-机器合同-B7-v9.2-overlay.json"
V921_OVERLAY_PATH = REPO_ROOT / "docsv3" / "v3-机器合同-B7-v9.2.1-overlay.json"
V921_ERRATUM_PATH = (
    REPO_ROOT / "docsv3" / "v3-勘误-B7-v9.2.1-reviewer合同机械闭合-2026-08-03.md"
)
V92_ROOT_TEST_PATH = REPO_ROOT / "tests" / "test_v3m0_b7_v92_contracts.py"
COMPARE_SOURCE_PATH = REPO_ROOT / "experiments" / "v3m0_b7_schema_lab" / "compare.py"

V91_REGISTRY_RAW_SHA256 = (
    "222cd47e95de63eaedee41f6ca4b207a0eccceb7a77089aed43a480a77f69d72"
)
V92_OVERLAY_RAW_SHA256 = (
    "b7a0d0a1a319ccb4ee56804a8e994bcf3bb90b138284f14841c87be594705b5f"
)
V921_OVERLAY_RAW_SHA256 = (
    "1231ee2e6c1b6f2eef86d1906990cb425128a643f4981b3552541d2ec0c689b6"
)

FRESH_PROCESS_V1 = "fresh-python-s-immutable-E-export-canonical-stdout-v1"
FRESH_PROCESS_V2 = "fresh-python-s-immutable-E-venv-invocation-v2"

V921_OPERATION_TARGETS = (
    "/lab_contract/exact_records/B7LabReviewerReceiptV1",
    (
        "/lab_contract/reviewer_child_static_scan_contract/"
        "lab_authored_import_contract/common"
    ),
    (
        "/lab_contract/reviewer_child_static_scan_contract/"
        "lab_authored_external_call_allowlist"
    ),
    (
        "/lab_contract/reviewer_child_static_scan_contract/"
        "lab_authored_import_contract/compare_outer_runner_only"
    ),
    "/lab_contract/reviewer_replay_materialization_contract",
    "/lab_contract/reviewer_executable_source_origin_contract",
)

V921_PRIOR_ORDERED_DIGESTS = {
    V921_OPERATION_TARGETS[0]: (
        "0bf7f327313d74da4caa36b113487e845c52862cf356e9d86e6ab8bf9b213e6d"
    ),
    V921_OPERATION_TARGETS[1]: (
        "1a1cc3bc75342f8a1d480f16b3caae9d5c809053561654e82663eb8fee8e355f"
    ),
    V921_OPERATION_TARGETS[2]: (
        "667c04cf6ed162a3164d2ba28ab36e4c071e7e2d59c083b40491fc9e53930b2e"
    ),
    V921_OPERATION_TARGETS[3]: (
        "fe6fa8cf83e620e52e7b1167050e63d39280b3e3c74fcc94d03faa113748dd87"
    ),
    V921_OPERATION_TARGETS[4]: (
        "4650f8d88b8ab577f7c1dee4ce057c1afdc3088d98e711eaf8189eb0aad53d6c"
    ),
    V921_OPERATION_TARGETS[5]: (
        "903a913925aa46c15879d4b6c4d82127db7985c414e7008750210f97b6840a2e"
    ),
}

COMMON_EXTERNAL_IMPORTS_V921 = [
    "__future__",
    "ast",
    "base64",
    "binascii",
    "copy",
    "dataclasses",
    "difflib",
    "enum",
    "hashlib",
    "json",
    "math",
    "numpy",
    "pathlib",
    "re",
    "struct",
    "typing",
]

V92_OUTER_ROOTS = [
    "precheck_python_invocation_identity_v2",
    "recheck_python_invocation_identity_v2",
    "run_python_environment_import_probe_v2",
    "capture_environment_manifest_v2",
    "run_frozen_reviewer_process_v2",
]

V92_OUTER_HELPER_CLOSURE = [
    "_require_lower_hex_v1",
    "build_sanitized_reviewer_environment_v1",
    "recheck_frozen_python_executable_identity_v1",
    "_require_normalized_absolute_path_v2",
    "_stable_regular_file_observation_v2",
    "_resolve_python_invocation_chain_v2",
    "_nearest_pyvenv_cfg_v2",
    "_python_environment_probe_report_is_well_typed_v2",
    "_empty_process_observation_v1",
    "_process_observation_v1",
    "_validate_bounded_process_configuration_v1",
    "run_bounded_reviewer_process_v1",
    "experiments.v3m0_b7_schema_lab.common.canonical_json_bytes_v1",
    "experiments.v3m0_b7_schema_lab.common.canonical_sha_v1",
    "experiments.v3m0_b7_schema_lab.common.strict_json_loads_v1",
    "experiments.v3m0_b7_schema_lab.common.validate_environment_manifest_v2",
    "experiments.v3m0_b7_schema_lab.common.validate_exact_lab_record_v1",
]

ENVIRONMENT_RUNTIME_PRODUCER_SYMBOL = (
    "experiments.v3m0_b7_schema_lab.compare.capture_environment_manifest_v2"
)
ENVIRONMENT_OBSERVATION_JOIN_SYMBOL = (
    "experiments.v3m0_b7_schema_lab.common.validate_environment_manifest_v2"
)
ENVIRONMENT_OWNERSHIP_RULE = (
    "compare-runtime-producer-captures-invocation-chain-target-same-fd-"
    "environment_sha-self-root-and-import-probe-observations;common-observation-"
    "join-only-validates-detached-bodies-and-caller-supplied-observation-"
    "evidence-and-must-not-read-files-environment-or-clock-or-spawn-a-process"
)

CHILD_FORBIDDEN_OUTER_REACHABILITY = [
    "precheck_python_invocation_identity_v2",
    "recheck_python_invocation_identity_v2",
    "run_bounded_reviewer_process_v1",
    "run_python_environment_import_probe_v2",
    "capture_environment_manifest_v2",
    "run_frozen_reviewer_process_v2",
]


def _reachable_compare_symbols(
    root_symbols: list[str] | tuple[str, ...],
) -> tuple[list[str], set[str], set[str]]:
    tree = ast.parse(COMPARE_SOURCE_PATH.read_text(encoding="utf-8"))
    definitions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    definition_names = [node.name for node in definitions]
    assert len(definition_names) == len(set(definition_names))
    by_name = {node.name: node for node in definitions}
    assert all(definition_names.count(root) == 1 for root in root_symbols)

    reachable = set(root_symbols)
    common_calls: set[str] = set()
    pending = list(root_symbols)
    while pending:
        owner = pending.pop(0)
        for call in ast.walk(by_name[owner]):
            if not isinstance(call, ast.Call):
                continue
            callable_node = call.func
            if isinstance(callable_node, ast.Name) and callable_node.id in by_name:
                if callable_node.id not in reachable:
                    reachable.add(callable_node.id)
                    pending.append(callable_node.id)
            elif (
                isinstance(callable_node, ast.Attribute)
                and isinstance(callable_node.value, ast.Name)
                and callable_node.value.id == "_common"
            ):
                common_calls.add(
                    f"experiments.v3m0_b7_schema_lab.common.{callable_node.attr}"
                )
    return definition_names, reachable, common_calls


def _actual_outer_helper_closure() -> list[str]:
    definition_names, reachable, common_calls = _reachable_compare_symbols(
        V92_OUTER_ROOTS
    )
    local_helpers = [
        name
        for name in definition_names
        if name in reachable and name not in V92_OUTER_ROOTS
    ]
    return local_helpers + sorted(common_calls)


def _v92_helpers() -> ModuleType:
    specification = importlib.util.spec_from_file_location(
        "_v3m0_b7_v92_contract_helpers",
        V92_ROOT_TEST_PATH,
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _load_prior_effective() -> tuple[ModuleType, dict[str, object]]:
    helpers = _v92_helpers()
    base = helpers._load_raw_rooted(V91_REGISTRY_PATH, V91_REGISTRY_RAW_SHA256)
    overlay = helpers._load_raw_rooted(V92_OVERLAY_PATH, V92_OVERLAY_RAW_SHA256)
    assert overlay["base_contract"]["raw_sha256"] == V91_REGISTRY_RAW_SHA256
    return helpers, helpers._materialize_v92(base, overlay)


def _load_v921_overlay(helpers: ModuleType) -> dict[str, object]:
    return helpers._load_raw_rooted(V921_OVERLAY_PATH, V921_OVERLAY_RAW_SHA256)


def _materialize_v921(
    helpers: ModuleType,
    prior: dict[str, object],
    overlay: dict[str, object],
) -> dict[str, object]:
    effective = copy.deepcopy(prior)
    algorithm = overlay["overlay_algorithm"]
    assert algorithm["algorithm"] == (
        "VERIFY_V91_RAW_APPLY_V92_THEN_VERIFY_V92_RAW_APPLY_ORDERED_V921"
    )
    assert algorithm["unlisted_prior_effective_mutation_allowed"] is False
    operations = algorithm["ordered_operations"]
    assert tuple(operation["json_pointer"] for operation in operations) == (
        V921_OPERATION_TARGETS
    )
    for operation in operations:
        assert set(operation) == {
            "json_pointer",
            "operation",
            "expected_prior_value_ordered_sha256",
            "replacement_ref",
        }
        pointer = operation["json_pointer"]
        assert operation["operation"] == "PATCH_EXACT_ORDERED_SHA256"
        assert (
            operation["expected_prior_value_ordered_sha256"]
            == (V921_PRIOR_ORDERED_DIGESTS[pointer])
        )
        parent, leaf = helpers._json_pointer_parent(effective, pointer)
        prior_value = parent[leaf]
        assert (
            helpers._ordered_digest(prior_value)
            == (operation["expected_prior_value_ordered_sha256"])
        )
        patch = helpers._resolve_overlay_ref(overlay, operation["replacement_ref"])
        parent[leaf] = helpers._apply_exact_patch(prior_value, patch)
    return effective


def _load_effective() -> tuple[dict[str, object], dict[str, object]]:
    helpers, prior = _load_prior_effective()
    overlay = _load_v921_overlay(helpers)
    return overlay, _materialize_v921(helpers, prior, overlay)


def _assert_closed_v921(overlay: dict[str, object]) -> None:
    helpers, prior = _load_prior_effective()
    effective = _materialize_v921(helpers, prior, overlay)
    lab = effective["lab_contract"]
    receipt = lab["exact_records"]["B7LabReviewerReceiptV1"]
    assert receipt["field_specs"][26] == {
        "name": "fresh_process_protocol_id",
        "wire_type": f"Literal[{FRESH_PROCESS_V2}]",
        "presence": "required",
        "nested_record": None,
    }
    common_import = lab["reviewer_child_static_scan_contract"][
        "lab_authored_import_contract"
    ]["common"]
    assert common_import["allowed_external_import_modules_exact"] == (
        COMMON_EXTERNAL_IMPORTS_V921
    )
    outer = lab["reviewer_child_static_scan_contract"]["lab_authored_import_contract"][
        "compare_outer_runner_only"
    ]
    assert outer["v92_outer_root_symbols_exact"] == V92_OUTER_ROOTS
    assert outer["v92_outer_static_helper_closure_exact"] == (V92_OUTER_HELPER_CLOSURE)
    assert outer["v92_outer_static_helper_closure_exact"] == (
        _actual_outer_helper_closure()
    )
    assert outer["reviewer_child_forbidden_reachable_symbols_exact"] == (
        CHILD_FORBIDDEN_OUTER_REACHABILITY
    )
    assert outer["environment_runtime_producer_symbol"] == (
        ENVIRONMENT_RUNTIME_PRODUCER_SYMBOL
    )
    assert outer["environment_observation_join_symbol"] == (
        ENVIRONMENT_OBSERVATION_JOIN_SYMBOL
    )
    assert outer["environment_ownership_rule"] == ENVIRONMENT_OWNERSHIP_RULE
    ordered = overlay["ordered_materialization_contract"]
    assert ordered["input_role_order"] == [
        "BASE_V91",
        "OVERLAY_V92",
        "OVERLAY_V921",
    ]
    export = lab["reviewer_replay_materialization_contract"]["immutable_source_export"]
    assert (
        str(V921_OVERLAY_PATH.relative_to(REPO_ROOT)) in (export["included_path_order"])
    )
    assert export["required_input_paths"]["registry_overlay_v921"] == str(
        V921_OVERLAY_PATH.relative_to(REPO_ROOT)
    )
    origins = lab["reviewer_executable_source_origin_contract"][
        "common_origin_exact_blob_paths"
    ]
    assert str(V921_OVERLAY_PATH.relative_to(REPO_ROOT)) in origins
    assert overlay["physical_contract_preservation"]["gpu_unlock_effect"] == "NONE"


def test_v921_raw_roots_and_ordered_three_layer_materialization() -> None:
    assert hashlib.sha256(V91_REGISTRY_PATH.read_bytes()).hexdigest() == (
        V91_REGISTRY_RAW_SHA256
    )
    assert hashlib.sha256(V92_OVERLAY_PATH.read_bytes()).hexdigest() == (
        V92_OVERLAY_RAW_SHA256
    )
    raw = V921_OVERLAY_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == V921_OVERLAY_RAW_SHA256
    assert raw.endswith(b"\n") and not raw.startswith(b"\xef\xbb\xbf")

    helpers, prior = _load_prior_effective()
    strictly_parsed = helpers._strict_json_loads(raw)
    duplicate_key_attack = raw.replace(
        b'{\n  "registry_schema_version":',
        (
            b'{\n  "registry_schema_version": "duplicate-key-attack",\n'
            b'  "registry_schema_version":'
        ),
        1,
    )
    assert duplicate_key_attack != raw
    with pytest.raises(ValueError, match="duplicate JSON key"):
        helpers._strict_json_loads(duplicate_key_attack)

    prior_snapshot = copy.deepcopy(prior)
    overlay = _load_v921_overlay(helpers)
    assert strictly_parsed == overlay
    assert list(overlay) == [
        "registry_schema_version",
        "base_contract_chain",
        "overlay_algorithm",
        "record_replacements",
        "contract_replacements",
        "ordered_materialization_contract",
        "source_closure_additions",
        "activation_contract",
        "physical_contract_preservation",
    ]
    assert overlay["registry_schema_version"] == (
        "experimental.v3m0.b7.v9.2.1-machine-contract-overlay.v1"
    )
    assert overlay["base_contract_chain"] == [
        {
            "layer_ordinal": 0,
            "role": "BASE_V91",
            "path": "docsv3/v3-机器合同-B7-v9.1-registry.json",
            "registry_schema_version": (
                "experimental.v3m0.b7.v9.1-machine-contract-registry.v1"
            ),
            "raw_sha256": V91_REGISTRY_RAW_SHA256,
        },
        {
            "layer_ordinal": 1,
            "role": "OVERLAY_V92",
            "path": "docsv3/v3-机器合同-B7-v9.2-overlay.json",
            "registry_schema_version": (
                "experimental.v3m0.b7.v9.2-machine-contract-overlay.v1"
            ),
            "raw_sha256": V92_OVERLAY_RAW_SHA256,
        },
    ]
    _materialize_v921(helpers, prior, overlay)
    assert prior == prior_snapshot

    ordered = overlay["ordered_materialization_contract"]
    assert ordered["input_role_order"] == [
        "BASE_V91",
        "OVERLAY_V92",
        "OVERLAY_V921",
    ]
    assert ordered["v921_raw_sha_source"] == (
        "root-test-literal-and-signed-Chinese-erratum"
    )
    assert ordered["mutation_rule"] == (
        "all-three-input-byte-streams-remain-immutable-and-each-overlay-applies-"
        "only-after-every-prior-layer-raw-root-and-ordered-operation-validates"
    )
    assert list(ordered).count("mutation_rule") == 1
    embedded = overlay["contract_replacements"][
        "reviewer_replay_materialization_contract"
    ]["relative_patches"][2]["replacement_value"]
    assert "mutation_rule" not in embedded


def test_v921_receipt_literal_exactly_joins_v92_protocol_registry() -> None:
    _overlay, effective = _load_effective()
    lab = effective["lab_contract"]
    field = lab["exact_records"]["B7LabReviewerReceiptV1"]["field_specs"][26]
    assert field["name"] == "fresh_process_protocol_id"
    assert field["wire_type"] == f"Literal[{FRESH_PROCESS_V2}]"
    assert FRESH_PROCESS_V1 not in field["wire_type"]
    assert all(
        protocol["fresh_process_protocol_id"] == FRESH_PROCESS_V2
        for protocol in lab["reviewer_protocol_registry"]
    )


def test_v921_common_difflib_and_outer_child_import_scopes_are_closed() -> None:
    _overlay, effective = _load_effective()
    lab = effective["lab_contract"]
    imports = lab["reviewer_child_static_scan_contract"]["lab_authored_import_contract"]
    assert imports["common"]["allowed_external_import_modules_exact"] == (
        COMMON_EXTERNAL_IMPORTS_V921
    )
    assert (
        imports["common"]["allowed_external_import_modules_exact"].count("difflib") == 1
    )
    assert lab["metric_algorithm"]["b8_consumer_changed_loc"]["diff"] == (
        "difflib.unified_diff-fromfile-skeleton-tofile-route-n-0-lineterm-empty"
    )
    calls = lab["reviewer_child_static_scan_contract"][
        "lab_authored_external_call_allowlist"
    ]
    assert calls["allowed_external_calls_exact"].count("difflib.unified_diff") == 1
    assert (
        calls["allowed_immutable_value_method_calls_exact"].count("str.splitlines") == 1
    )

    outer = imports["compare_outer_runner_only"]
    assert outer["v92_outer_root_symbols_exact"] == V92_OUTER_ROOTS
    assert outer["v92_outer_static_helper_closure_exact"] == (V92_OUTER_HELPER_CLOSURE)
    assert outer["v92_outer_static_helper_closure_exact"] == (
        _actual_outer_helper_closure()
    )
    assert outer["reviewer_child_forbidden_reachable_symbols_exact"] == (
        CHILD_FORBIDDEN_OUTER_REACHABILITY
    )
    assert "fixed-point" in outer["v92_outer_closure_rule"]
    assert "any-edge-reject" in outer["reviewer_child_exclusion_rule"]
    assert (
        "run_python_environment_import_probe_v2"
        in (outer["reviewer_child_exclusion_rule"])
    )
    assert outer["environment_runtime_producer_symbol"] == (
        ENVIRONMENT_RUNTIME_PRODUCER_SYMBOL
    )
    assert outer["environment_observation_join_symbol"] == (
        ENVIRONMENT_OBSERVATION_JOIN_SYMBOL
    )
    assert outer["environment_ownership_rule"] == ENVIRONMENT_OWNERSHIP_RULE


def test_v921_reviewer_export_origin_and_required_inputs_include_overlay() -> None:
    overlay, effective = _load_effective()
    lab = effective["lab_contract"]
    relative_overlay = str(V921_OVERLAY_PATH.relative_to(REPO_ROOT))
    export = lab["reviewer_replay_materialization_contract"]["immutable_source_export"]
    assert export["included_path_order"][2:5] == [
        "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "docsv3/v3-机器合同-B7-v9.2-overlay.json",
        relative_overlay,
    ]
    assert export["required_input_paths"] == {
        "d0": "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json",
        "d1": "data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json",
        "registry_base": "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "registry_overlay": "docsv3/v3-机器合同-B7-v9.2-overlay.json",
        "corpus": "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
        "registry_overlay_v921": relative_overlay,
    }
    assert export["machine_contract_materialization"] == {
        "overlay_input_path": relative_overlay,
        "ordered_contract_json_pointer": "/ordered_materialization_contract",
        "required_input_role_order": [
            "BASE_V91",
            "OVERLAY_V92",
            "OVERLAY_V921",
        ],
        "resolution_rule": (
            "strict-parse-overlay-with-duplicate-key-rejection-then-resolve-the-"
            "exact-ordered_contract_json_pointer-and-apply-that-contract-without-"
            "copying-or-reordering-fields"
        ),
    }
    helpers = _v92_helpers()
    assert (
        helpers._json_pointer(
            overlay,
            export["machine_contract_materialization"]["ordered_contract_json_pointer"],
        )
        == overlay["ordered_materialization_contract"]
    )
    origins = lab["reviewer_executable_source_origin_contract"][
        "common_origin_exact_blob_paths"
    ]
    assert origins[:3] == [
        "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "docsv3/v3-机器合同-B7-v9.2-overlay.json",
        relative_overlay,
    ]
    additions = overlay["source_closure_additions"]
    assert relative_overlay in additions
    assert str(V921_ERRATUM_PATH.relative_to(REPO_ROOT)) in additions
    assert str(Path(__file__).resolve().relative_to(REPO_ROOT)) in additions


def test_v921_is_contract_only_and_preserves_physics_and_locks() -> None:
    overlay, _effective = _load_effective()
    assert overlay["activation_contract"] == {
        "effective_scope": "B7-reviewer-contract-mechanical-closure-only",
        "activation_point": "before-first-v3m0-b7-schema-lab-D0-artifact",
        "v91_files_modified": False,
        "v92_files_modified": False,
        "contract_only": True,
        "d0_unlocked": False,
        "d1_unlocked": False,
        "production_unlocked": False,
        "gpu_unlocked": False,
    }
    assert overlay["physical_contract_preservation"] == {
        "physical_object_changed": False,
        "thresholds_changed": False,
        "route_order_changed": False,
        "seven_cases_changed": False,
        "gate_or_metric_order_changed": False,
        "d1_selected_fejer_order_changed": False,
        "scientific_status_effect": "NONE-CONTRACT-ERRATUM-ONLY",
        "d0_unlock_effect": "NONE",
        "gpu_unlock_effect": "NONE",
    }


@pytest.mark.parametrize(
    "attack_id",
    (
        "restore-receipt-v1",
        "remove-difflib",
        "remove-unified-diff-call",
        "remove-splitlines-method",
        "allow-child-probe",
        "swap-environment-ownership",
        "omit-v921-export",
        "reorder-materialization",
        "claim-gpu-unlock",
        "wrong-prior-digest",
    ),
)
def test_v921_contract_attacks_fail_closed(attack_id: str) -> None:
    helpers, _prior = _load_prior_effective()
    overlay = _load_v921_overlay(helpers)
    attacked = copy.deepcopy(overlay)
    if attack_id == "restore-receipt-v1":
        attacked["record_replacements"]["B7LabReviewerReceiptV1"]["relative_patches"][
            0
        ]["replacement_value"] = f"Literal[{FRESH_PROCESS_V1}]"
    elif attack_id == "remove-difflib":
        attacked["contract_replacements"]["common_import_contract"]["relative_patches"][
            0
        ]["replacement_value"].remove("difflib")
    elif attack_id == "remove-unified-diff-call":
        attacked["contract_replacements"]["external_call_allowlist"][
            "relative_patches"
        ][0]["replacement_value"].remove("difflib.unified_diff")
    elif attack_id == "remove-splitlines-method":
        attacked["contract_replacements"]["external_call_allowlist"][
            "relative_patches"
        ][1]["replacement_value"].remove("str.splitlines")
    elif attack_id == "allow-child-probe":
        attacked["contract_replacements"]["compare_outer_runner_only"][
            "relative_patches"
        ][3]["replacement_value"].remove("run_python_environment_import_probe_v2")
    elif attack_id == "swap-environment-ownership":
        attacked["contract_replacements"]["compare_outer_runner_only"][
            "relative_patches"
        ][6][
            "replacement_value"
        ] = "experiments.v3m0_b7_schema_lab.common.validate_environment_manifest_v2"
    elif attack_id == "omit-v921-export":
        attacked["contract_replacements"]["reviewer_replay_materialization_contract"][
            "relative_patches"
        ][0]["replacement_value"].remove("docsv3/v3-机器合同-B7-v9.2.1-overlay.json")
    elif attack_id == "reorder-materialization":
        attacked["ordered_materialization_contract"]["input_role_order"][1:] = [
            "OVERLAY_V921",
            "OVERLAY_V92",
        ]
    elif attack_id == "claim-gpu-unlock":
        attacked["physical_contract_preservation"]["gpu_unlock_effect"] = "UNLOCK"
    else:
        attacked["overlay_algorithm"]["ordered_operations"][0][
            "expected_prior_value_ordered_sha256"
        ] = "f" * 64
    with pytest.raises((AssertionError, KeyError, ValueError)):
        _assert_closed_v921(attacked)


def test_signed_chinese_v921_erratum_binds_roots_and_denies_unlock() -> None:
    text = V921_ERRATUM_PATH.read_text(encoding="utf-8")
    assert text.startswith("# v3 机器合同勘误：B7 v9.2.1")
    assert V91_REGISTRY_RAW_SHA256 in text
    assert V92_OVERLAY_RAW_SHA256 in text
    assert V921_OVERLAY_RAW_SHA256 in text
    assert "PI 签发" in text
    assert "fresh_process_protocol_id" in text
    assert "difflib.unified_diff" in text
    assert "str.splitlines" in text
    assert "run_python_environment_import_probe_v2" in text
    assert "base v9.1 → overlay v9.2 → overlay v9.2.1" in text
    assert "未解锁 D0、D1、production 或 GPU" in text
