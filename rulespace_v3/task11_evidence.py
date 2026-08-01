"""Non-authoritative evidence envelope for the expensive Task-11 raw replay.

This module deliberately operates on the canonical JSON payload of a
``WindowCalibrationOutcome``.  Its SHA is an integrity checksum, not an
authority seal.  In particular, none of the builders below can issue a
current-Parent-v2 calibration capability or a scientific PASS/FAIL verdict.
"""

from __future__ import annotations

import json
import re
from typing import Mapping

from .calibration_authority import (
    WindowCalibrationOutcome,
    _validate_window_calibration,
    window_calibration_outcome_payload,
)
from .current_window_replay import (
    CURRENT_WINDOW_CALIBRATION_PROTOCOL_V2_SCHEMA_VERSION,
    CURRENT_WINDOW_CONTROL_BINDING_V2_SCHEMA_VERSION,
)
from .evidence import canonical_sha
from .frozen_call_graph import freeze_rulespace_call_graph
from .registry import CONTROL_ORDER, VerifiedControlRegistry
from .runtime import (
    RUNTIME_EVALUATOR_ID,
    RUNTIME_SCHEMA_VERSION,
    runtime_evidence_manifest_from_wire,
    runtime_evidence_manifest_to_wire,
)
from .task8_control_replay import (
    CURRENT_CONTROL_REGISTRY_ENTRY_V2_SCHEMA_VERSION,
    CURRENT_CONTROL_REGISTRY_V2_SCHEMA_VERSION,
)
from .window import VerifiedWindowCalibrationProtocol


TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION = "v3m0.task11-raw-replay-evidence.v2"
TASK11_RAW_REPLAY_AUTHORITY_STATE = (
    "RAW_HISTORICAL_PARENT_REPLAY_NO_CURRENT_V2_AUTHORITY"
)
TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT = "NOT_ISSUED"
TASK11_RAW_REPLAY_SCOPE = (
    "HISTORICAL_PARENT_V1_NUMERICAL_REPLAY_WITH_TEST_ONLY_V2_SHA_PLACEHOLDER"
)
TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA = "a" * 64
TASK11_RAW_REPLAY_CREATE_POLICY = "CREATE_ONLY"
TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM = (
    "DEFAULT_CLI_PRODUCER_CALLED_PRODUCTION_TASK11_VALIDATOR"
)
TASK11_RAW_REPLAY_PRODUCTION_VALIDATION_PROOF = "NOT_AVAILABLE_OFFLINE"
TASK11_RAW_REPLAY_OFFLINE_VERIFICATION_SCOPE = (
    "INTEGRITY_ONLY_NO_AUTHORITY_NO_PROOF_OF_CREATION"
)
_TEST_ONLY_CREATION_VALIDATION_CLAIM = (
    "TEST_ONLY_INJECTED_VALIDATOR_NO_PRODUCTION_CLAIM"
)
EXPECTED_RAW_SNAPSHOT_HISTORICAL_PARENT_V1_SHA = (
    "f57079846203b2cbcf86da7ebfb06c8d6bc55c5a2c16e2548e009d2a6ce607d9"
)
EXPECTED_RAW_SNAPSHOT_LEGACY_REGISTRY_SHA = (
    "e113e2f7cee75a7215eb758aea9e334f9513d068a0d9fb2fada3394cad5ba67a"
)
EXPECTED_RAW_SNAPSHOT_CURRENT_REGISTRY_SHA = (
    "d4785a26fe96e941b46ad38f00343ce5ef045cf2589b9918bb686f5840bab29d"
)
EXPECTED_RAW_SNAPSHOT_LEGACY_WINDOW_SHA = (
    "0aa23f01916d33855af560f17e3d22009cfb65586796b2ccc0db46db4c2fdaa9"
)
EXPECTED_RAW_SNAPSHOT_CURRENT_WINDOW_SHA = (
    "526e30d23bcbbac5ce40641563a7a411dbebaa070a7ef4a9cde98f5c5006946b"
)
EXPECTED_RAW_SNAPSHOT_SCENARIO_AUTHORITY_SHAS = (
    "349abbcbe276884fb0e872fb609418430ae29b09b33adfc9a19dee423fd4812b",
    "4a544d4f8c8191de9c411e253fda4c6668a2a60746d05bf7d91a8b3ffed1b0f2",
    "64507aa71ca1e2ac5d286dafa58fbd0b1c48b499aa53c242090dc50af5373e59",
)
TASK11_RAW_REPLAY_REPOSITORY_MEASUREMENT_SCOPE = (
    "CLAIMED_AT_RUN_AND_INTEGRITY_BOUND; OFFLINE_VERIFICATION_DOES_NOT_"
    "REMEASURE_HISTORICAL_GIT_OR_SOURCE_BYTES"
)
TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS = (
    "experiments/__init__.py",
    "experiments/r10_current_generator.py",
    "experiments/v3m0_task11_raw_replay.py",
    "rulespace_v3/application_recipes.py",
    "rulespace_v3/blocks.py",
    "rulespace_v3/c05_projector_recipe.py",
    "rulespace_v3/c12_incidence_preflight.py",
    "rulespace_v3/calibration_authority.py",
    "rulespace_v3/candidate_scenario_dag.py",
    "rulespace_v3/current_window_replay.py",
    "rulespace_v3/evidence.py",
    "rulespace_v3/frozen_call_graph.py",
    "rulespace_v3/geometry.py",
    "rulespace_v3/geometry_application_recipes.py",
    "rulespace_v3/interference_mode_preflight.py",
    "rulespace_v3/linalg.py",
    "rulespace_v3/parent_authority.py",
    "rulespace_v3/parent_candidate_v2.py",
    "rulespace_v3/parent_freeze.py",
    "rulespace_v3/parent_freeze_v2.py",
    "rulespace_v3/parent_v2_contracts.py",
    "rulespace_v3/registry.py",
    "rulespace_v3/replay_scope.py",
    "rulespace_v3/response.py",
    "rulespace_v3/runtime.py",
    "rulespace_v3/task11_evidence.py",
    "rulespace_v3/task11_runner.py",
    "rulespace_v3/task8_control_replay.py",
    "rulespace_v3/thresholds.py",
)
_ENGINEERING_SCOPE = "SIX_T_THREE_CONTROL_INDEPENDENT_2T_RAW_REPLAY"
_CLAIM_SCOPE = (
    "ENGINEERING_REPLAY_EVIDENCE_ONLY; NOT A TASK11-V2 AUTHORITY OR "
    "SCIENTIFIC PASS/FAIL"
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_GIT_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_EMPTY_BYTES_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
_CONTROL_CASES = (
    ("C01_BLIND_HOLDOUT_FULL", "full"),
    ("C02_CONDITIONED_ZERO", "zero"),
    ("C03_EQUAL_RANK_DIRECT_SUM", "direct_sum"),
)
_EVIDENCE_FIELDS = frozenset(
    (
        "evidence_schema_version",
        "authority_state",
        "scientific_verdict",
        "current_parent_v2_bound",
        "create_policy",
        "engineering_contract_scope",
        "claim_scope",
        "creation_validation_claim",
        "production_validation_proof",
        "offline_verification_scope",
        "provenance",
        "outcome",
        "outcome_sha",
        "evidence_sha",
    )
)
_PROVENANCE_FIELDS = frozenset(
    (
        "replay_scope",
        "historical_parent_v1_sha",
        "placeholder_parent_freeze_v2_sha",
        "legacy_registry_sha",
        "current_control_registry_sha",
        "legacy_window_protocol_sha",
        "current_window_protocol_sha",
        "current_control_registry",
        "current_window_protocol",
        "scenario_authority_shas",
        "git_head",
        "git_worktree_dirty",
        "git_status_porcelain_sha256",
        "source_files",
        "runtime_manifest",
        "repository_measurement_scope",
        "command",
    )
)
_RUNTIME_MANIFEST_FIELDS = frozenset(
    (
        "runtime_schema_version",
        "evaluator_id",
        "source_closure",
        "python_version",
        "numpy_version",
        "scipy_version",
        "blas_config_sha",
        "lapack_config_sha",
        "platform_id",
        "runtime_manifest_sha",
    )
)
_CURRENT_REGISTRY_FIELDS = frozenset(
    (
        "registry_schema_version",
        "parent_freeze_v2_sha",
        "historical_parent_v1_sha",
        "legacy_registry_sha",
        "entries",
        "registry_sha",
    )
)
_CURRENT_REGISTRY_ENTRY_FIELDS = frozenset(
    (
        "entry_schema_version",
        "parent_freeze_v2_sha",
        "control_case_id",
        "control_id",
        "scenario_id",
        "scenario_authority_sha",
        "response_contract_sha",
        "legacy_registry_entry",
        "actual_factory_sha",
        "matched_ablated_factory_sha",
        "actual_program_sha",
        "matched_ablated_program_sha",
        "actual_effect_digest",
        "matched_ablated_effect_digest",
        "actual_step_count",
        "matched_ablated_step_count",
        "expected_actual_shell_rank",
        "expected_matched_shell_rank",
        "entry_sha",
    )
)
_CURRENT_WINDOW_FIELDS = frozenset(
    (
        "protocol_schema_version",
        "parent_freeze_v2_sha",
        "current_control_registry",
        "legacy_window_protocol",
        "t_candidates",
        "control_bindings",
        "protocol_sha",
    )
)
_CURRENT_WINDOW_BINDING_FIELDS = frozenset(
    (
        "binding_schema_version",
        "parent_freeze_v2_sha",
        "control_case_id",
        "control_id",
        "current_registry_entry_sha",
        "scenario_authority_sha",
        "response_contract_sha",
        "legacy_window_entry_sha",
        "binding_sha",
    )
)


def _json_clone(value: object, field: str) -> object:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be finite plain JSON") from exc
    return json.loads(encoded)


def _plain_dict(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise TypeError(f"{field} must be a plain dict")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{field} keys must be exact strings")
    return value


def _plain_list(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise TypeError(f"{field} must be a plain list")
    return value


def _exact_fields(
    value: dict[str, object], expected: frozenset[str], field: str
) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{field} schema mismatch; "
            f"unknown={sorted(observed - expected)}, "
            f"missing={sorted(expected - observed)}"
        )


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _LOWER_SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be a non-empty exact string")
    return value


def _git_object_id(value: object, field: str) -> str:
    if type(value) is not str or _GIT_OBJECT_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase Git object ID")
    return value


def _mapping_value(value: dict[str, object], key: str, field: str) -> dict[str, object]:
    return _plain_dict(value.get(key), f"{field}.{key}")


def _validate_current_root_wires(provenance: dict[str, object]) -> None:
    placeholder = provenance["placeholder_parent_freeze_v2_sha"]
    scenarios = _plain_list(
        provenance["scenario_authority_shas"],
        "provenance.scenario_authority_shas",
    )
    registry = _plain_dict(
        provenance["current_control_registry"],
        "provenance.current_control_registry",
    )
    _exact_fields(
        registry,
        _CURRENT_REGISTRY_FIELDS,
        "provenance.current_control_registry",
    )
    if (
        registry["registry_schema_version"]
        != CURRENT_CONTROL_REGISTRY_V2_SCHEMA_VERSION
    ):
        raise ValueError("current registry schema is not frozen")
    if registry["parent_freeze_v2_sha"] != placeholder:
        raise ValueError("current registry is spliced to another Parent-v2")
    if registry["historical_parent_v1_sha"] != provenance["historical_parent_v1_sha"]:
        raise ValueError("current registry historical parent root drifted")
    if registry["legacy_registry_sha"] != provenance["legacy_registry_sha"]:
        raise ValueError("current registry legacy root drifted")
    if registry["registry_sha"] != provenance["current_control_registry_sha"]:
        raise ValueError("current registry declared SHA drifted")
    entries = _plain_list(
        registry["entries"],
        "provenance.current_control_registry.entries",
    )
    if len(entries) != len(_CONTROL_CASES):
        raise ValueError("current registry must retain C01-C03 exactly")
    verified_entries: list[dict[str, object]] = []
    for index, ((case_id, control_id), scenario_sha) in enumerate(
        zip(_CONTROL_CASES, scenarios)
    ):
        field = f"provenance.current_control_registry.entries[{index}]"
        entry = _plain_dict(entries[index], field)
        _exact_fields(entry, _CURRENT_REGISTRY_ENTRY_FIELDS, field)
        if (
            entry["entry_schema_version"]
            != CURRENT_CONTROL_REGISTRY_ENTRY_V2_SCHEMA_VERSION
        ):
            raise ValueError(f"{field} schema is not frozen")
        if entry["parent_freeze_v2_sha"] != placeholder:
            raise ValueError(f"{field} is spliced to another Parent-v2")
        if entry["control_case_id"] != case_id or entry["control_id"] != control_id:
            raise ValueError(f"{field} control root order drifted")
        _text(entry["scenario_id"], f"{field}.scenario_id")
        if entry["scenario_authority_sha"] != scenario_sha:
            raise ValueError(f"{field} scenario root drifted")
        for name in (
            "scenario_authority_sha",
            "response_contract_sha",
            "actual_factory_sha",
            "matched_ablated_factory_sha",
            "actual_program_sha",
            "matched_ablated_program_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "entry_sha",
        ):
            _sha(entry[name], f"{field}.{name}")
        legacy_entry = _plain_dict(
            entry["legacy_registry_entry"],
            f"{field}.legacy_registry_entry",
        )
        _sha(
            legacy_entry.get("entry_sha"),
            f"{field}.legacy_registry_entry.entry_sha",
        )
        for name in (
            "actual_step_count",
            "matched_ablated_step_count",
            "expected_actual_shell_rank",
            "expected_matched_shell_rank",
        ):
            value = entry[name]
            if type(value) is not int or value < 0:
                raise ValueError(f"{field}.{name} must be non-negative exact int")
        entry_body = {key: value for key, value in entry.items() if key != "entry_sha"}
        if canonical_sha(entry_body) != entry["entry_sha"]:
            raise ValueError(f"{field} entry SHA does not match its complete body")
        verified_entries.append(entry)
    registry_body = {
        key: value for key, value in registry.items() if key != "registry_sha"
    }
    if canonical_sha(registry_body) != registry["registry_sha"]:
        raise ValueError("current registry SHA does not match its complete body")

    window = _plain_dict(
        provenance["current_window_protocol"],
        "provenance.current_window_protocol",
    )
    _exact_fields(window, _CURRENT_WINDOW_FIELDS, "provenance.current_window_protocol")
    if (
        window["protocol_schema_version"]
        != CURRENT_WINDOW_CALIBRATION_PROTOCOL_V2_SCHEMA_VERSION
    ):
        raise ValueError("current window schema is not frozen")
    if window["parent_freeze_v2_sha"] != placeholder:
        raise ValueError("current window is spliced to another Parent-v2")
    if window["current_control_registry"] != registry:
        raise ValueError("current window embeds another current registry root")
    legacy_window = _plain_dict(
        window["legacy_window_protocol"],
        "provenance.current_window_protocol.legacy_window_protocol",
    )
    if legacy_window.get("protocol_sha") != provenance["legacy_window_protocol_sha"]:
        raise ValueError("current window legacy protocol root drifted")
    if window["protocol_sha"] != provenance["current_window_protocol_sha"]:
        raise ValueError("current window declared SHA drifted")
    legacy_entries = _plain_list(
        legacy_window.get("control_entries"),
        "provenance.current_window_protocol.legacy_window_protocol.control_entries",
    )
    bindings = _plain_list(
        window["control_bindings"],
        "provenance.current_window_protocol.control_bindings",
    )
    if len(legacy_entries) != len(_CONTROL_CASES) or len(bindings) != len(
        _CONTROL_CASES
    ):
        raise ValueError("current window must retain C01-C03 bindings exactly")
    for index, ((case_id, control_id), entry, legacy_entry) in enumerate(
        zip(_CONTROL_CASES, verified_entries, legacy_entries)
    ):
        field = f"provenance.current_window_protocol.control_bindings[{index}]"
        binding = _plain_dict(bindings[index], field)
        _exact_fields(binding, _CURRENT_WINDOW_BINDING_FIELDS, field)
        if (
            binding["binding_schema_version"]
            != CURRENT_WINDOW_CONTROL_BINDING_V2_SCHEMA_VERSION
        ):
            raise ValueError(f"{field} schema is not frozen")
        legacy_entry_body = _plain_dict(
            legacy_entry,
            (
                "provenance.current_window_protocol.legacy_window_protocol"
                f".control_entries[{index}]"
            ),
        )
        expected = {
            "parent_freeze_v2_sha": placeholder,
            "control_case_id": case_id,
            "control_id": control_id,
            "current_registry_entry_sha": entry["entry_sha"],
            "scenario_authority_sha": entry["scenario_authority_sha"],
            "response_contract_sha": entry["response_contract_sha"],
            "legacy_window_entry_sha": legacy_entry_body.get("entry_sha"),
        }
        for name, expected_value in expected.items():
            if binding[name] != expected_value:
                raise ValueError(f"{field}.{name} root drifted")
        for name in (
            "parent_freeze_v2_sha",
            "current_registry_entry_sha",
            "scenario_authority_sha",
            "response_contract_sha",
            "legacy_window_entry_sha",
            "binding_sha",
        ):
            _sha(binding[name], f"{field}.{name}")
        binding_body = {
            key: value for key, value in binding.items() if key != "binding_sha"
        }
        if canonical_sha(binding_body) != binding["binding_sha"]:
            raise ValueError(f"{field} binding SHA does not match its complete body")
    window_body = {key: value for key, value in window.items() if key != "protocol_sha"}
    if canonical_sha(window_body) != window["protocol_sha"]:
        raise ValueError("current window SHA does not match its complete body")


def _validate_outcome_root_links(
    outcome: dict[str, object],
    provenance: dict[str, object],
) -> None:
    manifest = _mapping_value(outcome, "manifest", "outcome")
    registry = _mapping_value(manifest, "control_registry", "outcome.manifest")
    protocol = _mapping_value(manifest, "window_protocol", "outcome.manifest")
    if registry.get("registry_sha") != provenance["legacy_registry_sha"]:
        raise ValueError("raw outcome registry SHA differs from provenance")
    if registry.get("parent_freeze_sha") != provenance["historical_parent_v1_sha"]:
        raise ValueError("raw outcome registry historical parent root drifted")
    if protocol.get("protocol_sha") != provenance["legacy_window_protocol_sha"]:
        raise ValueError("raw outcome window SHA differs from provenance")
    if protocol.get("parent_freeze_sha") != provenance["historical_parent_v1_sha"]:
        raise ValueError("raw outcome window historical parent root drifted")
    if protocol.get("control_registry_sha") != provenance["legacy_registry_sha"]:
        raise ValueError("raw outcome window registry root drifted")
    current_registry = _plain_dict(
        provenance["current_control_registry"],
        "provenance.current_control_registry",
    )
    legacy_entries = _plain_list(
        registry.get("entries"),
        "outcome.manifest.control_registry.entries",
    )
    current_entries = _plain_list(
        current_registry.get("entries"),
        "provenance.current_control_registry.entries",
    )
    if len(legacy_entries) != len(current_entries) or any(
        current["legacy_registry_entry"] != legacy
        for current, legacy in zip(current_entries, legacy_entries)
    ):
        raise ValueError("current registry is not linked to outcome legacy entries")
    current_window = _plain_dict(
        provenance["current_window_protocol"],
        "provenance.current_window_protocol",
    )
    if current_window.get("legacy_window_protocol") != protocol:
        raise ValueError("current window is not linked to outcome legacy protocol")


def _validated_provenance(value: object) -> dict[str, object]:
    cloned = _json_clone(value, "Task-11 raw replay provenance")
    provenance = _plain_dict(cloned, "Task-11 raw replay provenance")
    _exact_fields(provenance, _PROVENANCE_FIELDS, "Task-11 raw replay provenance")
    if provenance["replay_scope"] != TASK11_RAW_REPLAY_SCOPE:
        raise ValueError("raw replay scope is not frozen")
    if (
        provenance["repository_measurement_scope"]
        != TASK11_RAW_REPLAY_REPOSITORY_MEASUREMENT_SCOPE
    ):
        raise ValueError("repository measurement scope is not frozen")
    for name in (
        "historical_parent_v1_sha",
        "placeholder_parent_freeze_v2_sha",
        "legacy_registry_sha",
        "current_control_registry_sha",
        "legacy_window_protocol_sha",
        "current_window_protocol_sha",
    ):
        _sha(provenance[name], f"provenance.{name}")
    expected_snapshot_roots = {
        "historical_parent_v1_sha": (EXPECTED_RAW_SNAPSHOT_HISTORICAL_PARENT_V1_SHA),
        "legacy_registry_sha": EXPECTED_RAW_SNAPSHOT_LEGACY_REGISTRY_SHA,
        "current_control_registry_sha": (EXPECTED_RAW_SNAPSHOT_CURRENT_REGISTRY_SHA),
        "legacy_window_protocol_sha": EXPECTED_RAW_SNAPSHOT_LEGACY_WINDOW_SHA,
        "current_window_protocol_sha": EXPECTED_RAW_SNAPSHOT_CURRENT_WINDOW_SHA,
    }
    for name, expected in expected_snapshot_roots.items():
        if provenance[name] != expected:
            raise ValueError(f"provenance.{name} differs from exact raw snapshot root")
    _git_object_id(provenance["git_head"], "provenance.git_head")
    if (
        provenance["placeholder_parent_freeze_v2_sha"]
        != TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA
    ):
        raise ValueError("raw replay must disclose the exact Parent-v2 placeholder")
    git_worktree_dirty = provenance["git_worktree_dirty"]
    if type(git_worktree_dirty) is not bool:
        raise TypeError("provenance.git_worktree_dirty must be an exact bool")
    git_status_sha = _sha(
        provenance["git_status_porcelain_sha256"],
        "provenance.git_status_porcelain_sha256",
    )
    if git_worktree_dirty == (git_status_sha == _EMPTY_BYTES_SHA256):
        raise ValueError("provenance git dirty/status digest is contradictory")
    scenario_shas = _plain_list(
        provenance["scenario_authority_shas"],
        "provenance.scenario_authority_shas",
    )
    if len(scenario_shas) != len(CONTROL_ORDER):
        raise ValueError("provenance must retain three scenario authority SHAs")
    for index, value in enumerate(scenario_shas):
        _sha(value, f"provenance.scenario_authority_shas[{index}]")
    if tuple(scenario_shas) != EXPECTED_RAW_SNAPSHOT_SCENARIO_AUTHORITY_SHAS:
        raise ValueError("scenario authority SHAs differ from exact raw snapshot roots")
    _validate_current_root_wires(provenance)
    source_files = _plain_list(provenance["source_files"], "provenance.source_files")
    if not source_files:
        raise ValueError("provenance.source_files must be non-empty")
    paths = []
    source_sha_by_path: dict[str, str] = {}
    for index, item in enumerate(source_files):
        source = _plain_dict(item, f"provenance.source_files[{index}]")
        _exact_fields(
            source,
            frozenset(("relative_path", "sha256")),
            f"provenance.source_files[{index}]",
        )
        relative_path = _text(source["relative_path"], "source relative_path")
        paths.append(relative_path)
        source_sha_by_path[relative_path] = _sha(source["sha256"], "source sha256")
    if len(paths) != len(set(paths)):
        raise ValueError("provenance.source_files contains duplicate paths")
    if tuple(paths) != TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS:
        raise ValueError(
            "provenance.source_files is not the frozen Task-11 closure order"
        )
    runtime = _plain_dict(provenance["runtime_manifest"], "provenance.runtime_manifest")
    _exact_fields(
        runtime,
        _RUNTIME_MANIFEST_FIELDS,
        "provenance.runtime_manifest",
    )
    if runtime["runtime_schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise ValueError("runtime_schema_version is not frozen")
    if runtime["evaluator_id"] != RUNTIME_EVALUATOR_ID:
        raise ValueError("evaluator_id is not frozen")
    for name in (
        "python_version",
        "numpy_version",
        "scipy_version",
        "platform_id",
    ):
        _text(runtime[name], f"provenance.runtime_manifest.{name}")
    for name in (
        "blas_config_sha",
        "lapack_config_sha",
        "runtime_manifest_sha",
    ):
        _sha(runtime[name], f"provenance.runtime_manifest.{name}")
    closure = _plain_list(
        runtime["source_closure"],
        "provenance.runtime_manifest.source_closure",
    )
    if not closure:
        raise ValueError("runtime source closure must be non-empty")
    closure_paths = []
    runtime_sha_by_path: dict[str, str] = {}
    for index, item in enumerate(closure):
        entry = _plain_dict(
            item,
            f"provenance.runtime_manifest.source_closure[{index}]",
        )
        _exact_fields(
            entry,
            frozenset(("relative_path", "sha256")),
            f"provenance.runtime_manifest.source_closure[{index}]",
        )
        relative_path = _text(entry["relative_path"], "runtime source relative_path")
        closure_paths.append(relative_path)
        runtime_sha_by_path[relative_path] = _sha(
            entry["sha256"], "runtime source sha256"
        )
    if len(closure_paths) != len(set(closure_paths)):
        raise ValueError("runtime source closure contains duplicate paths")
    for relative_path in source_sha_by_path.keys() & runtime_sha_by_path.keys():
        if source_sha_by_path[relative_path] != runtime_sha_by_path[relative_path]:
            raise ValueError(
                f"direct/runtime source closure overlap SHA mismatch: {relative_path}"
            )
    runtime_body = {
        key: item for key, item in runtime.items() if key != "runtime_manifest_sha"
    }
    if canonical_sha(runtime_body) != runtime["runtime_manifest_sha"]:
        raise ValueError("runtime manifest SHA does not match its complete body")
    hydrated_runtime = runtime_evidence_manifest_from_wire(runtime)
    if runtime_evidence_manifest_to_wire(hydrated_runtime) != runtime:
        raise ValueError("runtime manifest differs from its strict wire codec")
    command = _plain_list(provenance["command"], "provenance.command")
    if not command:
        raise ValueError("provenance.command must be non-empty")
    for index, item in enumerate(command):
        _text(item, f"provenance.command[{index}]")
    return provenance


def _build_task11_raw_replay_integrity_payload(
    outcome_payload: Mapping[str, object],
    *,
    outcome_sha: str,
    provenance: Mapping[str, object],
    creation_validation_claim: str,
) -> dict[str, object]:
    """Assemble integrity bytes; this private helper proves no validation call."""

    outcome = _json_clone(outcome_payload, "Task-11 outcome payload")
    outcome_body = _plain_dict(outcome, "Task-11 outcome payload")
    observed_outcome_sha = _sha(outcome_sha, "outcome_sha")
    if canonical_sha(outcome_body) != observed_outcome_sha:
        raise ValueError("Task-11 raw outcome SHA does not match its complete body")
    if creation_validation_claim not in (
        TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM,
        _TEST_ONLY_CREATION_VALIDATION_CLAIM,
    ):
        raise ValueError("Task-11 creation validation claim is not frozen")
    provenance_body = _validated_provenance(provenance)
    _validate_outcome_root_links(outcome_body, provenance_body)

    body: dict[str, object] = {
        "evidence_schema_version": TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION,
        "authority_state": TASK11_RAW_REPLAY_AUTHORITY_STATE,
        "scientific_verdict": TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT,
        "current_parent_v2_bound": False,
        "create_policy": TASK11_RAW_REPLAY_CREATE_POLICY,
        "engineering_contract_scope": _ENGINEERING_SCOPE,
        "claim_scope": _CLAIM_SCOPE,
        "creation_validation_claim": creation_validation_claim,
        "production_validation_proof": (TASK11_RAW_REPLAY_PRODUCTION_VALIDATION_PROOF),
        "offline_verification_scope": TASK11_RAW_REPLAY_OFFLINE_VERIFICATION_SCOPE,
        "provenance": provenance_body,
        "outcome": outcome_body,
        "outcome_sha": observed_outcome_sha,
    }
    return {**body, "evidence_sha": canonical_sha(body)}


def _make_creation_builder(
    *,
    outcome_type: type,
    registry_type: type,
    protocol_type: type,
    validator,
    payload_encoder,
    creation_validation_claim: str,
):
    def build_task11_raw_replay_evidence_payload(
        outcome,
        registry,
        protocol,
        *,
        provenance: Mapping[str, object],
    ) -> dict[str, object]:
        if type(outcome) is not outcome_type:
            raise TypeError(
                "Task-11 creation requires the exact WindowCalibrationOutcome"
            )
        if type(registry) is not registry_type:
            raise TypeError("Task-11 creation requires the exact live registry")
        if type(protocol) is not protocol_type:
            raise TypeError("Task-11 creation requires the exact live protocol")

        # This call must precede serialization and every creation claim.
        validator(outcome, registry, protocol)
        outcome_payload = payload_encoder(outcome)
        if type(outcome_payload) is not dict:
            raise TypeError("Task-11 production encoder returned a non-dict payload")
        return _build_task11_raw_replay_integrity_payload(
            outcome_payload,
            outcome_sha=outcome.outcome_sha,
            provenance=provenance,
            creation_validation_claim=creation_validation_claim,
        )

    return build_task11_raw_replay_evidence_payload


def _make_task11_raw_replay_creation_builder(
    *,
    outcome_type: type,
    registry_type: type,
    protocol_type: type,
    validator,
    payload_encoder,
):
    """Return a test-only injected builder that cannot claim production validation."""

    return _make_creation_builder(
        outcome_type=outcome_type,
        registry_type=registry_type,
        protocol_type=protocol_type,
        validator=validator,
        payload_encoder=payload_encoder,
        creation_validation_claim=_TEST_ONLY_CREATION_VALIDATION_CLAIM,
    )


def verify_task11_raw_replay_evidence_payload(
    evidence_payload: Mapping[str, object],
) -> dict[str, object]:
    """Verify integrity only, with no authority or proof of creation validation.

    A fully re-signed, semantically invalid JSON document can pass this offline
    verifier.  Only the default creation path can call the captured production
    Task-11 validator before serialization; that call is not provable offline.
    """

    cloned = _json_clone(evidence_payload, "Task-11 raw replay evidence")
    evidence = _plain_dict(cloned, "Task-11 raw replay evidence")
    _exact_fields(evidence, _EVIDENCE_FIELDS, "Task-11 raw replay evidence")
    expected_constants = {
        "evidence_schema_version": TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION,
        "authority_state": TASK11_RAW_REPLAY_AUTHORITY_STATE,
        "scientific_verdict": TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT,
        "current_parent_v2_bound": False,
        "create_policy": TASK11_RAW_REPLAY_CREATE_POLICY,
        "engineering_contract_scope": _ENGINEERING_SCOPE,
        "claim_scope": _CLAIM_SCOPE,
        "creation_validation_claim": (TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM),
        "production_validation_proof": (TASK11_RAW_REPLAY_PRODUCTION_VALIDATION_PROOF),
        "offline_verification_scope": TASK11_RAW_REPLAY_OFFLINE_VERIFICATION_SCOPE,
    }
    for name, expected in expected_constants.items():
        if evidence[name] != expected or type(evidence[name]) is not type(expected):
            raise ValueError(f"Task-11 raw evidence {name} drifted")
    outcome = _plain_dict(evidence["outcome"], "evidence.outcome")
    outcome_sha = _sha(evidence["outcome_sha"], "evidence.outcome_sha")
    if canonical_sha(outcome) != outcome_sha:
        raise ValueError("Task-11 raw outcome SHA does not match its complete body")
    provenance = _validated_provenance(evidence["provenance"])
    _validate_outcome_root_links(outcome, provenance)
    evidence_sha = _sha(evidence["evidence_sha"], "evidence.evidence_sha")
    body = {key: value for key, value in evidence.items() if key != "evidence_sha"}
    if canonical_sha(body) != evidence_sha:
        raise ValueError("Task-11 raw evidence SHA does not match its complete body")
    return evidence


_raw_build_task11_raw_replay_evidence_payload = _make_creation_builder(
    outcome_type=WindowCalibrationOutcome,
    registry_type=VerifiedControlRegistry,
    protocol_type=VerifiedWindowCalibrationProtocol,
    validator=_validate_window_calibration,
    payload_encoder=window_calibration_outcome_payload,
    creation_validation_claim=TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM,
)
build_task11_raw_replay_evidence_payload = freeze_rulespace_call_graph(
    _raw_build_task11_raw_replay_evidence_payload
)
verify_task11_raw_replay_evidence_payload = freeze_rulespace_call_graph(
    verify_task11_raw_replay_evidence_payload
)


__all__ = [
    "EXPECTED_RAW_SNAPSHOT_CURRENT_REGISTRY_SHA",
    "EXPECTED_RAW_SNAPSHOT_CURRENT_WINDOW_SHA",
    "EXPECTED_RAW_SNAPSHOT_HISTORICAL_PARENT_V1_SHA",
    "EXPECTED_RAW_SNAPSHOT_LEGACY_REGISTRY_SHA",
    "EXPECTED_RAW_SNAPSHOT_LEGACY_WINDOW_SHA",
    "EXPECTED_RAW_SNAPSHOT_SCENARIO_AUTHORITY_SHAS",
    "TASK11_RAW_REPLAY_AUTHORITY_STATE",
    "TASK11_RAW_REPLAY_CREATE_POLICY",
    "TASK11_RAW_REPLAY_CREATION_VALIDATION_CLAIM",
    "TASK11_RAW_REPLAY_EVIDENCE_SCHEMA_VERSION",
    "TASK11_RAW_REPLAY_OFFLINE_VERIFICATION_SCOPE",
    "TASK11_RAW_REPLAY_PARENT_V2_PLACEHOLDER_SHA",
    "TASK11_RAW_REPLAY_PRODUCTION_VALIDATION_PROOF",
    "TASK11_RAW_REPLAY_REPOSITORY_MEASUREMENT_SCOPE",
    "TASK11_RAW_REPLAY_REQUIRED_SOURCE_PATHS",
    "TASK11_RAW_REPLAY_SCIENTIFIC_VERDICT",
    "TASK11_RAW_REPLAY_SCOPE",
    "build_task11_raw_replay_evidence_payload",
    "verify_task11_raw_replay_evidence_payload",
]
