"""Root contracts for the additive B7 v9.2 machine-contract erratum.

These tests validate immutable design bytes and mechanically materialize the
v9.2 lab overlay over the pinned v9.1 registry.  They do not import or execute
the schema lab and cannot issue a scientific status or a GPU permit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
V91_REGISTRY_PATH = REPO_ROOT / "docsv3" / "v3-机器合同-B7-v9.1-registry.json"
V92_OVERLAY_PATH = REPO_ROOT / "docsv3" / "v3-机器合同-B7-v9.2-overlay.json"
V92_ERRATUM_PATH = (
    REPO_ROOT / "docsv3" / "v3-勘误-B7-v9.2-corpus-环境与复放威胁边界-2026-08-03.md"
)

V91_REGISTRY_RAW_SHA256 = (
    "222cd47e95de63eaedee41f6ca4b207a0eccceb7a77089aed43a480a77f69d72"
)
V92_OVERLAY_RAW_SHA256 = (
    "b7a0d0a1a319ccb4ee56804a8e994bcf3bb90b138284f14841c87be594705b5f"
)
V91_PURE_REPLAY_PROJECTION_SHA256 = (
    "bafbaeb75e890715464c1fff6e6e0cbf1d4f56bb53a3817a9b2d12d2a3c27ff9"
)

ENVIRONMENT_V2_FIELDS = (
    "environment_schema_version",
    "python_implementation",
    "python_version",
    "python_invocation_path",
    "python_executable_realpath",
    "python_executable_raw_sha256",
    "python_invocation_identity_sha",
    "python_venv_prefix",
    "python_pyvenv_cfg_path",
    "python_pyvenv_cfg_raw_sha256",
    "numpy_version",
    "scipy_version",
    "platform_system",
    "platform_release",
    "platform_machine",
    "numpy_float64_dtype_str",
    "numpy_float64_itemsize",
    "byteorder",
    "python_hash_seed",
    "blas_thread_settings",
    "threadpool_info",
    "fresh_process_per_capture",
    "environment_sha",
)

CORPUS_V2_FIELDS = (
    "fixture_schema_version",
    "corpus_spec",
    "mutation_universe",
    "metric_spec",
    "environment_manifest",
    "synthetic_graph_manifest",
    "ordered_d0_transcripts",
    "fixture_sha",
)

OPERATION_TARGETS = (
    "/lab_contract/exact_records/B7LabEnvironmentManifestV2",
    "/lab_contract/exact_records/B7LabCorpusFixtureV2",
    "/lab_contract/exact_records/B7LabD0ComparisonV1",
    "/lab_contract/exact_records/B7LabD1ComparisonV1",
    "/lab_contract/validator_contracts/validators",
    "/lab_contract/validator_contracts/validators",
    "/lab_contract/corpus_fixture_contract",
    "/lab_contract/validator_contracts/validators/22",
    "/lab_contract/validator_contracts/validators/25",
    "/lab_contract/reviewer_protocol_registry",
    "/lab_contract/reviewer_replay_materialization_contract",
    "/lab_contract/reviewer_executable_source_origin_contract",
    "/lab_contract/reviewer_process_totalization_contract",
    "/lab_contract/reviewer_receipt_failure_contract",
    "/lab_contract/validator_contracts/validators/28",
    "/lab_contract/global_invariants",
)

REPLACEMENT_PRIOR_DIGESTS = {
    "/lab_contract/exact_records/B7LabD0ComparisonV1": (
        "5dd3f4782649907d20980e1228819b86f00a28cc85fc82c903262e10c185c1b1"
    ),
    "/lab_contract/exact_records/B7LabD1ComparisonV1": (
        "0f74ae348f1ef603b4d730b83ab9fb782c525f738482fff94448de0a58194e1b"
    ),
    "/lab_contract/corpus_fixture_contract": (
        "774115a3a67691f172e112cce45a973fe2b18375b5eb956dbcbab6817c47c0de"
    ),
    "/lab_contract/validator_contracts/validators/22": (
        "75e23c0a3ccd1890e52413d866be4ea8fa3ce9eb22f2efee7cb4b5d78603a56d"
    ),
    "/lab_contract/validator_contracts/validators/25": (
        "d86adc9b133430cc6994a3558eb7638445c0b7a62881d8a57d36cdc353dfe449"
    ),
    "/lab_contract/reviewer_protocol_registry": (
        "d3b586f89c7495cc30012924220f01d132132d1c1e4d2e085d03be60c4498c6d"
    ),
    "/lab_contract/reviewer_replay_materialization_contract": (
        "b9d40ef83f4ed39279e7969d273455403c8ba6442c8fa436ad7b55c02b9d3018"
    ),
    "/lab_contract/reviewer_executable_source_origin_contract": (
        "cb93d6840fbb159e0da25913412f6630231204af0da8743713ee5459e243e95c"
    ),
    "/lab_contract/reviewer_process_totalization_contract": (
        "1a3dfe12a15d57bf230e1e058c58558dd251b567338716ed5ef3adfc96ccfbae"
    ),
    "/lab_contract/reviewer_receipt_failure_contract": (
        "74273de381a6de70bc28e5f33c486fa9fb82d04239c3d93573e985fc2147a296"
    ),
    "/lab_contract/validator_contracts/validators/28": (
        "96fc06d06d6d2118e3a85c2bd39a57349039c5a045655ea306a003b8c4b6e953"
    ),
    "/lab_contract/global_invariants": (
        "8aec0e8b6b4130aa3317b0e9c13a9f47f9761204ee5d7bd5b50caf2770ce7dd9"
    ),
}


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
    assert not raw.startswith(b"\xef\xbb\xbf")
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


def _load_raw_rooted(path: Path, expected_sha256: str) -> dict[str, object]:
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_sha256
    return _strict_json_loads(raw)


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
    tokens = [
        token.replace("~1", "/").replace("~0", "~")
        for token in pointer.removeprefix("/").split("/")
    ]
    parent = document
    for token in tokens[:-1]:
        parent = parent[token] if type(parent) is dict else parent[int(token)]
    leaf: str | int = tokens[-1]
    if type(parent) is list:
        leaf = int(leaf)
    return parent, leaf


def _resolve_overlay_ref(overlay: dict[str, object], pointer: str) -> object:
    return copy.deepcopy(_json_pointer(overlay, pointer))


def _apply_exact_patch(prior: object, patch_contract: dict[str, object]) -> object:
    patched = copy.deepcopy(prior)
    assert set(patch_contract) == {"relative_patches", "result_ordered_sha256"}
    for patch in patch_contract["relative_patches"]:
        parent, leaf = _json_pointer_parent(patched, patch["relative_pointer"])
        if patch["operation"] == "REPLACE_EXACT":
            assert set(patch) == {
                "relative_pointer",
                "operation",
                "expected_prior_value",
                "replacement_value",
            }
            assert parent[leaf] == patch["expected_prior_value"]
            parent[leaf] = copy.deepcopy(patch["replacement_value"])
        else:
            assert patch["operation"] == "ADD_ABSENT"
            assert set(patch) == {
                "relative_pointer",
                "operation",
                "replacement_value",
            }
            assert type(parent) is dict and type(leaf) is str and leaf not in parent
            parent[leaf] = copy.deepcopy(patch["replacement_value"])
    assert _ordered_digest(patched) == patch_contract["result_ordered_sha256"]
    return patched


def _materialize_v92(
    base: dict[str, object], overlay: dict[str, object]
) -> dict[str, object]:
    effective = copy.deepcopy(base)
    algorithm = overlay["overlay_algorithm"]
    assert algorithm["algorithm"] == (
        "VERIFY_EXACT_V91_RAW_THEN_APPLY_ORDERED_V92_LAB_OVERLAY"
    )
    assert algorithm["unlisted_v91_mutation_allowed"] is False
    operations = algorithm["ordered_operations"]
    assert tuple(operation["json_pointer"] for operation in operations) == (
        OPERATION_TARGETS
    )

    for operation in operations:
        pointer = operation["json_pointer"]
        kind = operation["operation"]
        if kind == "ADD_ABSENT":
            assert set(operation) == {
                "json_pointer",
                "operation",
                "replacement_ref",
            }
            parent, leaf = _json_pointer_parent(effective, pointer)
            assert type(parent) is dict and type(leaf) is str and leaf not in parent
            parent[leaf] = _resolve_overlay_ref(overlay, operation["replacement_ref"])
        elif kind == "APPEND_EXACT_LENGTH":
            assert set(operation) == {
                "json_pointer",
                "operation",
                "expected_prior_length",
                "replacement_ref",
            }
            target = _json_pointer(effective, pointer)
            assert type(target) is list
            assert len(target) == operation["expected_prior_length"]
            target.append(_resolve_overlay_ref(overlay, operation["replacement_ref"]))
        else:
            assert kind in {
                "REPLACE_EXACT_ORDERED_SHA256",
                "PATCH_EXACT_ORDERED_SHA256",
            }
            assert set(operation) == {
                "json_pointer",
                "operation",
                "expected_prior_value_ordered_sha256",
                "replacement_ref",
            }
            assert (
                operation["expected_prior_value_ordered_sha256"]
                == REPLACEMENT_PRIOR_DIGESTS[pointer]
            )
            parent, leaf = _json_pointer_parent(effective, pointer)
            prior = parent[leaf]
            assert (
                _ordered_digest(prior)
                == operation["expected_prior_value_ordered_sha256"]
            )
            replacement = _resolve_overlay_ref(overlay, operation["replacement_ref"])
            if kind == "PATCH_EXACT_ORDERED_SHA256":
                replacement = _apply_exact_patch(prior, replacement)
            parent[leaf] = replacement
    return effective


def _field_names(record: dict[str, object]) -> tuple[str, ...]:
    return tuple(field["name"] for field in record["field_specs"])


def _validator(effective: dict[str, object], validator_id: str) -> dict[str, object]:
    return next(
        item
        for item in effective["lab_contract"]["validator_contracts"]["validators"]
        if item["validator_id"] == validator_id
    )


def _load_contracts() -> tuple[dict[str, object], dict[str, object]]:
    base = _load_raw_rooted(V91_REGISTRY_PATH, V91_REGISTRY_RAW_SHA256)
    overlay = _load_raw_rooted(V92_OVERLAY_PATH, V92_OVERLAY_RAW_SHA256)
    return overlay, _materialize_v92(base, overlay)


def _assert_closed_v92(overlay: dict[str, object]) -> None:
    base = _load_raw_rooted(V91_REGISTRY_PATH, V91_REGISTRY_RAW_SHA256)
    effective = _materialize_v92(base, overlay)
    lab = effective["lab_contract"]
    records = lab["exact_records"]
    assert _field_names(records["B7LabCorpusFixtureV2"]) == CORPUS_V2_FIELDS
    assert _field_names(records["B7LabEnvironmentManifestV2"]) == (
        ENVIRONMENT_V2_FIELDS
    )
    assert (
        lab["reviewer_replay_materialization_contract"]["python_invocation"][
            "placeholder"
        ]
        == "{FROZEN_PYTHON_INVOCATION_PATH}"
    )
    assert all(
        protocol["replay_command_argv_template"][0] == "{FROZEN_PYTHON_INVOCATION_PATH}"
        for protocol in lab["reviewer_protocol_registry"]
    )
    assert (
        lab["reviewer_process_totalization_contract"][
            "python_execution_binding_contract"
        ]["descriptor_bound_exec"]
        is False
    )
    assert (
        overlay["pure_core_projection_reuse_contract"]["canonical_sha256"]
        == V91_PURE_REPLAY_PROJECTION_SHA256
    )
    assert overlay["execution_dag_contract"]["ordered_edges"][2] == [
        "FREEZE_CORPUS_FIXTURE_V2",
        "RUN_D0",
    ]


def test_v92_overlay_raw_root_base_pin_and_ordered_materialization() -> None:
    base_raw = V91_REGISTRY_PATH.read_bytes()
    overlay_raw = V92_OVERLAY_PATH.read_bytes()
    assert hashlib.sha256(base_raw).hexdigest() == V91_REGISTRY_RAW_SHA256
    assert hashlib.sha256(overlay_raw).hexdigest() == V92_OVERLAY_RAW_SHA256
    assert overlay_raw.endswith(b"\n") and not overlay_raw.startswith(b"\xef\xbb\xbf")

    overlay = _strict_json_loads(overlay_raw)
    assert list(overlay) == [
        "registry_schema_version",
        "base_contract",
        "overlay_algorithm",
        "record_additions",
        "record_replacements",
        "validator_additions",
        "validator_replacements",
        "contract_replacements",
        "python_invocation_identity_contract",
        "execution_dag_contract",
        "pure_core_projection_reuse_contract",
        "static_scanner_reuse_contract",
        "source_closure_additions",
        "activation_contract",
        "physical_contract_preservation",
    ]
    assert overlay["registry_schema_version"] == (
        "experimental.v3m0.b7.v9.2-machine-contract-overlay.v1"
    )
    assert overlay["base_contract"] == {
        "path": "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "registry_schema_version": (
            "experimental.v3m0.b7.v9.1-machine-contract-registry.v1"
        ),
        "raw_sha256": V91_REGISTRY_RAW_SHA256,
    }
    base = _strict_json_loads(base_raw)
    snapshot = copy.deepcopy(base)
    effective = _materialize_v92(base, overlay)
    assert base == snapshot
    assert len(effective["lab_contract"]["validator_contracts"]["validators"]) == 34


def test_v92_records_bind_graph_and_invocation_identity_into_self_roots() -> None:
    _overlay, effective = _load_contracts()
    records = effective["lab_contract"]["exact_records"]
    environment = records["B7LabEnvironmentManifestV2"]
    corpus = records["B7LabCorpusFixtureV2"]

    assert environment["schema_id"] == ("experimental.v3m0.b7.environment-manifest.v2")
    assert _field_names(environment) == ENVIRONMENT_V2_FIELDS
    assert environment["field_specs"][-1] == {
        "name": "environment_sha",
        "wire_type": "sha256",
        "presence": "required",
        "nested_record": None,
    }
    assert any(
        "python_invocation_identity_sha" in invariant and "environment_sha" in invariant
        for invariant in environment["record_invariants"]
    )

    assert corpus["schema_id"] == "experimental.v3m0.b7.corpus-fixture.v2"
    assert _field_names(corpus) == CORPUS_V2_FIELDS
    assert corpus["field_specs"][4]["nested_record"] == ("B7LabEnvironmentManifestV2")
    assert corpus["field_specs"][5] == {
        "name": "synthetic_graph_manifest",
        "wire_type": "B7LabSyntheticGraphManifestV1",
        "presence": "required",
        "nested_record": "B7LabSyntheticGraphManifestV1",
    }
    assert corpus["record_invariants"] == [
        "validate_corpus_fixture_v2 must accept; fixture_sha equals project "
        "canonical_sha after removing only fixture_sha and therefore covers the "
        "complete environment and synthetic graph bodies"
    ]

    d0_environment = records["B7LabD0ComparisonV1"]["field_specs"][8]
    d1_environment = records["B7LabD1ComparisonV1"]["field_specs"][13]
    for field in (d0_environment, d1_environment):
        assert field["wire_type"] == "B7LabEnvironmentManifestV2"
        assert field["nested_record"] == "B7LabEnvironmentManifestV2"


def test_corpus_v2_validates_one_graph_before_all_seven_transcripts() -> None:
    _overlay, effective = _load_contracts()
    lab = effective["lab_contract"]
    corpus = lab["corpus_fixture_contract"]

    assert corpus["record"] == "B7LabCorpusFixtureV2"
    assert corpus["validator_id"] == "validate_corpus_fixture_v2"
    assert corpus["graph_validation_count_per_fixture"] == 1
    assert corpus["validation_order"] == [
        "strict-top-level-B7LabCorpusFixtureV2",
        "validate-corpus-spec",
        "validate-mutation-universe",
        "validate-metric-spec",
        "validate-environment-manifest-v2",
        "validate-synthetic-graph-manifest-v1-exactly-once",
        "validate-seven-transcripts-in-case-contract-order-against-that-graph",
        "validate-cross-roots-and-fixture-self-hash",
    ]
    assert corpus["transcript_graph_dependent_validator_calls"] == [
        "validate_response_run_spec_fixture_v1(transcript.response_run_spec_fixture,transcript.provenance_fixture,fixture.synthetic_graph_manifest)",
        "validate_source_readout_response_raw_v1(transcript.actual_completed_response,actual,transcript.response_run_spec_fixture,transcript.provenance_fixture,fixture.synthetic_graph_manifest)-iff-present",
        "validate_source_readout_response_raw_v1(transcript.matched_ablated_completed_response,matched_ablated,transcript.response_run_spec_fixture,transcript.provenance_fixture,fixture.synthetic_graph_manifest)-iff-present",
    ]
    corpus_validator = _validator(effective, "validate_corpus_fixture_v2")
    assert corpus_validator["implementation_symbol"] == "validate_corpus_fixture_v2"
    assert any(
        "graph-dependent" in condition and "all-seven" in condition
        for condition in corpus_validator["exact_conditions"]
    )

    d0_conditions = _validator(effective, "validate_d0_comparison_v1")[
        "exact_conditions"
    ]
    assert any("validate_corpus_fixture_v2" in item for item in d0_conditions)
    d1_conditions = _validator(effective, "validate_d1_comparison_v1")[
        "exact_conditions"
    ]
    assert any(
        "canonical-bytes-exactly-equal" in item
        and "fixture-synthetic-graph-manifest" in item
        for item in d1_conditions
    )


def test_environment_v2_separates_invocation_target_and_venv_identity() -> None:
    overlay, effective = _load_contracts()
    identity = overlay["python_invocation_identity_contract"]
    assert identity["max_symlink_hops"] == 40
    assert identity["invocation_path_rule"] == (
        "absolute-lexically-normalized-existing-path;symlink-allowed;used-as-argv0"
    )
    assert identity["resolved_target_rule"] == (
        "ordered-lstat-readlink-resolution-must-terminate-at-the-recorded-"
        "python_executable_realpath-regular-file"
    )
    assert identity["lstat_hop_field_order"] == [
        "hop_ordinal",
        "absolute_normalized_path",
        "lstat_device",
        "lstat_inode",
        "lstat_mode",
        "lstat_size",
        "lstat_mtime_ns",
        "lstat_ctime_ns",
        "symlink_target_or_null",
    ]
    assert identity["identity_projection_field_order"] == [
        "python_invocation_path",
        "ordered_lstat_hops",
        "python_executable_realpath",
        "python_executable_raw_sha256",
        "python_venv_prefix",
        "python_pyvenv_cfg_path",
        "python_pyvenv_cfg_raw_sha256",
    ]
    assert identity["nearest_pyvenv_cfg_rule"].startswith(
        "walk-lexical-ancestors-from-directory-of-python_invocation_path"
    )
    assert "same-open-file-descriptor" in identity["target_raw_sha_rule"]

    materialization = effective["lab_contract"][
        "reviewer_replay_materialization_contract"
    ]
    assert materialization["python_invocation"] == {
        "placeholder": "{FROZEN_PYTHON_INVOCATION_PATH}",
        "replacement_source": (
            "reviewed-D1-environment_manifest.python_invocation_path"
        ),
        "resolved_target_source": (
            "reviewed-D1-environment_manifest.python_executable_realpath"
        ),
        "required_target_raw_sha_source": (
            "reviewed-D1-environment_manifest.python_executable_raw_sha256"
        ),
        "required_invocation_identity_sha_source": (
            "reviewed-D1-environment_manifest.python_invocation_identity_sha"
        ),
        "argv0_rule": "use-normalized-invocation-path-never-resolved-target-realpath",
    }
    probe = materialization["python_environment_import_probe"]
    assert probe["argv_prefix_template"] == [
        "{FROZEN_PYTHON_INVOCATION_PATH}",
        "-s",
        "-c",
    ]
    assert probe["argv_final_item_source"] == "this-object.program_utf8"
    assert probe["argv_rule"] == (
        "exact-four-string-tuple-of-argv_prefix_template-followed-by-the-exact-"
        "program_utf8-field-value-no-other-placeholder-or-argument"
    )
    assert probe["required_imports"] == ["numpy", "scipy", "threadpoolctl"]
    assert probe["timeout_seconds"] == 30
    assert probe["stdout_hard_cap_bytes"] == 262144
    assert probe["stderr_hard_cap_bytes"] == 262144
    assert probe["result_join_rule"].endswith(
        "all-version-platform-dtype-byteorder-threadpool-and-venv-fields-equal-"
        "B7LabEnvironmentManifestV2"
    )

    for protocol in effective["lab_contract"]["reviewer_protocol_registry"]:
        argv = protocol["replay_command_argv_template"]
        assert argv[0] == "{FROZEN_PYTHON_INVOCATION_PATH}"
        assert "{FROZEN_PYTHON_EXECUTABLE}" not in argv


def test_reviewer_is_path_rechecked_but_makes_no_descriptor_bound_claim() -> None:
    _overlay, effective = _load_contracts()
    process = effective["lab_contract"]["reviewer_process_totalization_contract"]
    binding = process["python_execution_binding_contract"]

    assert binding["profile_id"] == "controlled-host-path-recheck-v1"
    assert binding["full_precheck_required"] is True
    assert binding["immediate_identity_recheck_required"] is True
    assert binding["popen_adjacency_rule"] == (
        "after-the-final-invocation-chain-target-pyvenv-and-environment-identity-"
        "recheck-returns-true-the-next-side-effecting-operation-is-Popen-with-"
        "argv0-equal-python_invocation_path"
    )
    assert binding["descriptor_bound_exec"] is False
    assert binding["strict_same_byte_adversarial_exec_claim_allowed"] is False
    assert "no-concurrent-path-mutation" in binding["controlled_host_assumption"]
    assert binding["macos_capability_observation"] == {
        "scope": "2026-08-03-current-development-host-observation-not-portable-kernel-law",
        "os_fexecve_available": False,
        "os_execveat_available": False,
        "dev_fd_python_exec_observation": "EACCES",
    }
    stronger = binding["stronger_security_deployment_prior"]
    assert stronger["required_only_for_adversarial_same-byte-claim"] is True
    assert stronger["current_B7_experiment_gate"] is False
    assert "separately-frozen-descriptor-bound-launcher" in stronger["requirement"]


def test_graph_corpus_d0_dag_and_reviewer_export_are_exact() -> None:
    overlay, effective = _load_contracts()
    dag = overlay["execution_dag_contract"]
    assert dag["node_order"] == [
        "VERIFY_V92_OVERLAY",
        "FREEZE_SYNTHETIC_GRAPH_MANIFEST",
        "FREEZE_ENVIRONMENT_MANIFEST_V2",
        "FREEZE_CORPUS_FIXTURE_V2",
        "RUN_D0",
        "RUN_D1_IF_D0_SURVIVORS",
        "COMMIT_E_IF_LAB_ARTIFACTS_VALIDATE",
        "MATERIALIZE_REVIEWER_EXPORT_IF_UNIQUE_D1",
        "RUN_TWO_REVIEWERS",
    ]
    assert dag["ordered_edges"][:4] == [
        ["VERIFY_V92_OVERLAY", "FREEZE_SYNTHETIC_GRAPH_MANIFEST"],
        ["FREEZE_SYNTHETIC_GRAPH_MANIFEST", "FREEZE_CORPUS_FIXTURE_V2"],
        ["FREEZE_CORPUS_FIXTURE_V2", "RUN_D0"],
        ["FREEZE_ENVIRONMENT_MANIFEST_V2", "FREEZE_CORPUS_FIXTURE_V2"],
    ]
    assert dag["d1_graph_rule"] == (
        "D1-must-reuse-canonical-bytes-identical-fixture-synthetic-graph-manifest;"
        "new-or-re-signed-graph-reject"
    )

    materialization = effective["lab_contract"][
        "reviewer_replay_materialization_contract"
    ]
    export = materialization["immutable_source_export"]
    assert export["included_path_order"][2:4] == [
        "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "docsv3/v3-机器合同-B7-v9.2-overlay.json",
    ]
    assert export["required_input_paths"] == {
        "d0": "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json",
        "d1": "data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json",
        "registry_base": "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "registry_overlay": "docsv3/v3-机器合同-B7-v9.2-overlay.json",
        "corpus": "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
    }
    source = effective["lab_contract"]["reviewer_executable_source_origin_contract"]
    assert source["common_origin_exact_blob_paths"][:2] == [
        "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "docsv3/v3-机器合同-B7-v9.2-overlay.json",
    ]


def test_pure_core_projection_and_physical_contract_are_unchanged() -> None:
    overlay, _effective = _load_contracts()
    base = _load_raw_rooted(V91_REGISTRY_PATH, V91_REGISTRY_RAW_SHA256)
    pure = base["lab_contract"]["pure_replay_core_contract"]
    projection_contract = overlay["pure_core_projection_reuse_contract"]
    projection = {
        field: _json_pointer(base, pointer)
        for field, pointer in zip(
            pure["registry_literal_projection"]["field_order"],
            pure["registry_literal_projection"]["source_pointers_in_field_order"],
        )
    }
    assert _canonical_sha(projection) == V91_PURE_REPLAY_PROJECTION_SHA256
    assert projection_contract == {
        "source_registry_path": "docsv3/v3-机器合同-B7-v9.1-registry.json",
        "source_registry_raw_sha256": V91_REGISTRY_RAW_SHA256,
        "source_pointer": "/lab_contract/pure_replay_core_contract/registry_literal_projection",
        "canonical_sha256": V91_PURE_REPLAY_PROJECTION_SHA256,
        "reuse_reason": (
            "v9.2 changes only common-layer corpus-environment-reviewer joins; all "
            "eight pure production-body validator semantics and literals remain v9.1"
        ),
        "v92_overlay_fields_enter_pure_projection": False,
        "core_literal_rewrite_required": False,
    }
    assert overlay["physical_contract_preservation"] == {
        "physical_object_changed": False,
        "thresholds_changed": False,
        "route_order_changed": False,
        "seven_cases_changed": False,
        "gate_or_metric_order_changed": False,
        "d1_selected_fejer_order_changed": False,
        "scientific_status_effect": "NONE-CONTRACT-ERRATUM-ONLY",
        "gpu_unlock_effect": "NONE",
    }


def test_static_scanner_bans_and_source_membership_schema_are_frozen() -> None:
    overlay, effective = _load_contracts()
    scanner = overlay["static_scanner_reuse_contract"]
    lab = effective["lab_contract"]
    metric_closure = lab["metric_algorithm"]["route_local_reachable_closure"]
    reviewer = lab["reviewer_child_static_scan_contract"]
    source = lab["reviewer_executable_source_origin_contract"]

    assert (
        scanner["route_forbidden_reachable_calls_exact"]
        == (metric_closure["forbidden_reachable_calls"])
        == ["eval", "exec", "compile", "__import__", "globals", "locals", "getattr"]
    )
    assert (
        scanner["reviewer_forbidden_exact_names_exact"]
        == reviewer["forbidden_exact_names"]
    )
    assert "__import__" in scanner["reviewer_forbidden_exact_names_exact"]
    assert "getattr" in scanner["reviewer_forbidden_exact_names_exact"]

    membership = scanner["source_closure_membership_record"]
    assert membership["schema_id"] == (
        "experimental.v3m0.b7.reviewer-source-closure-membership.v1"
    )
    assert [field["name"] for field in membership["field_specs"]] == source[
        "source_closure_root_record_field_order"
    ]
    assert membership["group_order"] == [
        "CORPUS_REPLAY",
        "METRIC_REPLAY",
        "A_FLAT",
        "B_PROGRESS",
        "C_UNION",
    ]
    assert membership["ordinal_rule"] == (
        "execution_ordinal-is-zero-based-contiguous-within-each-group-and-records-"
        "follow-group_order-then-static-executed-module-order"
    )
    assert membership["duplicate_rule"] == (
        "duplicate-group-ordinal-or-group-path-reject"
    )
    assert (
        scanner["expected_root_algorithm"]
        == source["expected_source_closure_root_algorithm"]
    )
    assert (
        scanner["observed_root_algorithm"]
        == source["observed_source_closure_root_algorithm"]
    )
    assert scanner["v92_algorithm_change"] == (
        "NONE-v9.2-overlay-enters-common-origin-exact-blob-set-but-not-the-"
        "executed-module-membership-sequence"
    )


@pytest.mark.parametrize(
    "attack_id",
    (
        "remove-corpus-graph",
        "launch-resolved-realpath",
        "claim-descriptor-bound",
        "rewrite-pure-projection",
        "skip-corpus-before-d0",
        "wrong-prior-digest",
    ),
)
def test_v92_contract_attacks_fail_closed(attack_id: str) -> None:
    overlay = _load_raw_rooted(V92_OVERLAY_PATH, V92_OVERLAY_RAW_SHA256)
    attacked = copy.deepcopy(overlay)
    if attack_id == "remove-corpus-graph":
        attacked["record_additions"]["B7LabCorpusFixtureV2"]["field_specs"].pop(5)
    elif attack_id == "launch-resolved-realpath":
        attacked["contract_replacements"]["reviewer_protocol_registry"][0][
            "replay_command_argv_template"
        ][0] = "{FROZEN_PYTHON_EXECUTABLE_REALPATH}"
    elif attack_id == "claim-descriptor-bound":
        attacked["contract_replacements"]["reviewer_process_totalization_contract"][
            "relative_patches"
        ][1]["replacement_value"]["descriptor_bound_exec"] = True
    elif attack_id == "rewrite-pure-projection":
        attacked["pure_core_projection_reuse_contract"]["canonical_sha256"] = "f" * 64
    elif attack_id == "skip-corpus-before-d0":
        attacked["execution_dag_contract"]["ordered_edges"][2] = [
            "FREEZE_SYNTHETIC_GRAPH_MANIFEST",
            "RUN_D0",
        ]
    else:
        attacked["overlay_algorithm"]["ordered_operations"][2][
            "expected_prior_value_ordered_sha256"
        ] = "e" * 64
    with pytest.raises((AssertionError, KeyError)):
        _assert_closed_v92(attacked)


def test_signed_chinese_erratum_binds_overlay_and_denies_premature_unlock() -> None:
    raw = V92_ERRATUM_PATH.read_bytes()
    text = raw.decode("utf-8")
    assert text.startswith("# v3 机器合同勘误：B7 v9.2")
    assert V91_REGISTRY_RAW_SHA256 in text
    assert V92_OVERLAY_RAW_SHA256 in text
    assert "PI 签发" in text
    assert "D0 corpus" in text and "synthetic graph" in text
    assert "invocation path" in text and "resolved target realpath" in text
    assert "不是 descriptor-bound 执行证明" in text
    assert "未解锁 D0、D1、production 或 GPU" in text
    overlay_source_paths = _load_raw_rooted(V92_OVERLAY_PATH, V92_OVERLAY_RAW_SHA256)[
        "source_closure_additions"
    ]
    assert overlay_source_paths
    assert str(V92_ERRATUM_PATH.relative_to(REPO_ROOT)) in overlay_source_paths
