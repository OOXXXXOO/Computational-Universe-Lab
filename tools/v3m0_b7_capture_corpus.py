"""Auditable one-shot builder for the B7 v9.2 non-authority corpus.

This module deliberately lives outside the reviewer/runtime source closure.  It
materializes complete raw bodies from the frozen pure-core catalogs, then asks
the production-neutral validators to accept every join before anything may be
written as a fixture.  The graph is synthetic and never an authority object.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile

import numpy as np

from rulespace_v3 import b7_replay_core_v1 as _core


_SCHEMAS = _core._record_schemas_v1()
_FIXTURE_RELATIVE_PATH_V1 = Path("tests/fixtures/v3m0_b7_schema_lab_corpus.json")
_MATERIALIZATION_SUMMARY_FIELDS_V1 = (
    "fixture_raw_sha256",
    "fixture_sha",
    "mutation_count",
)


def _canonical_sha(value: object) -> str:
    return _core.canonical_sha_v1(value)


def _clone(value: object) -> object:
    return _core.strict_json_loads_v1(_core.canonical_json_bytes_v1(value))


def _seal(raw_body: dict[str, object], hash_field: str) -> dict[str, object]:
    raw_body[hash_field] = _canonical_sha(
        {name: value for name, value in raw_body.items() if name != hash_field}
    )
    return raw_body


def _split_top_level(value: str, delimiter: str) -> list[str]:
    result: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(value):
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
        elif character == delimiter and depth == 0:
            result.append(value[start:index])
            start = index + 1
    result.append(value[start:])
    return result


def _literal(token: str) -> object:
    if token == "true":
        return True
    if token == "false":
        return False
    if token.lstrip("-").isdigit():
        return int(token)
    return token


def _minimal_wire(
    wire_type: str,
    nested_record: str | None,
    active: tuple[str, ...],
) -> object:
    if wire_type.startswith("Optional["):
        return None
    if nested_record is not None and wire_type.startswith("tuple["):
        parts = _split_top_level(wire_type[6:-1], ";")
        count = 0
        for modifier in parts[1:]:
            if modifier.startswith("exact=") and modifier[6:].isdigit():
                count = int(modifier[6:])
            elif modifier == "nonempty":
                count = max(count, 1)
        return [_minimal_record(nested_record, active) for _ in range(count)]
    if nested_record is not None:
        nested = _minimal_record(nested_record, active)
        if nested_record == "FrozenComplexTensor":
            shape = [1]
            if wire_type.startswith("FrozenComplexTensor["):
                dimensions = wire_type.removeprefix("FrozenComplexTensor[")[:-1]
                shape = [int(item) for item in dimensions.split("x")]
            nested["shape"] = shape
            nested["values_wire"] = [
                [0.0, 0.0] for _ in range(math.prod(shape))
            ]
            _resign_tree("FrozenComplexTensor", nested)
        return nested
    if wire_type.startswith("Literal["):
        return _literal(_split_top_level(wire_type[8:-1], ",")[0])
    if wire_type == "sha256":
        return hashlib.sha256(b"b7-synthetic-capture-reference").hexdigest()
    if wire_type == "hex64":
        return "0000000000000000"
    if wire_type == "git-sha1":
        return hashlib.sha1(b"b7-synthetic-capture-commit").hexdigest()
    if wire_type in {"str", "base64-be-f64-column"}:
        return "b7-synthetic-capture"
    if wire_type == "UndefinedReason":
        return "response_null"
    if wire_type == "MechanismKind":
        return "target_blind"
    if wire_type == "ProvenanceOperation":
        return "derive"
    if wire_type == "bool":
        return False
    if wire_type == "int":
        return 1
    if wire_type in {"float", "float64"}:
        return 1.0
    if wire_type == "canonical-json-object":
        return {}
    if wire_type.startswith("tuple["):
        parts = _split_top_level(wire_type[6:-1], ";")
        item_expression = parts[0]
        count: int | None = None
        repeated_value: object | None = None
        for modifier in parts[1:]:
            if modifier.startswith("exact=") and modifier[6:].isdigit():
                count = int(modifier[6:])
            elif modifier == "exact=response-grid-size":
                count = 1
            elif modifier == "nonempty":
                count = max(count or 0, 1)
            elif modifier.startswith("value="):
                repeated_value = _literal(modifier[6:])
        item_types = _split_top_level(item_expression, ",")
        if item_types[-1] == "...":
            item_types = [item_types[0]] * (0 if count is None else count)
        elif len(item_types) == 1:
            item_types = [item_types[0]] * (1 if count is None else count)
        values = [_minimal_wire(item, None, active) for item in item_types]
        if repeated_value is not None:
            values = [repeated_value for _ in values]
        return values
    return "b7-synthetic-enum"


def _minimal_record(
    record_name: str,
    active: tuple[str, ...] = (),
) -> dict[str, object]:
    if record_name in active:
        raise ValueError(f"unbroken required record cycle at {record_name}")
    if record_name == "BlockStatus":
        return {"defined": False, "reason": "response_null"}
    hash_field, fields = _SCHEMAS[record_name]
    raw_body = {
        name: _minimal_wire(wire_type, nested, (*active, record_name))
        for name, wire_type, nested in fields
    }
    if record_name == "FrozenComplexTensor":
        raw_body["tensor_schema_version"] = "v3m0.frozen-complex-tensor.v1"
    elif record_name == "BasisManifest":
        raw_body["channel_order"] = ["q0"]
        raw_body["vectors_wire"] = [[[0.0, 0.0]]]
    if hash_field is not None:
        _seal(raw_body, hash_field)
    return raw_body


def _resign_tree(record_name: str, raw_body: dict[str, object]) -> None:
    hash_field, fields = _SCHEMAS[record_name]
    for name, _wire_type, nested in fields:
        value = raw_body[name]
        if nested is None or value is None:
            continue
        if type(value) is list:
            for item in value:
                if type(item) is not dict:
                    raise TypeError(f"{record_name}.{name} item is not a record")
                _resign_tree(nested, item)
        else:
            if type(value) is not dict:
                raise TypeError(f"{record_name}.{name} is not a record")
            _resign_tree(nested, value)
    if hash_field is not None:
        _seal(raw_body, hash_field)


def _tensor(shape: list[int]) -> dict[str, object]:
    return _seal(
        {
            "tensor_schema_version": "v3m0.frozen-complex-tensor.v1",
            "shape": shape,
            "values_wire": [[0.0, 0.0] for _ in range(math.prod(shape))],
            "tensor_sha": "",
        },
        "tensor_sha",
    )


def _matrix_tensor(rows: int, columns: int, diagonal_count: int) -> dict[str, object]:
    return _seal(
        {
            "tensor_schema_version": "v3m0.frozen-complex-tensor.v1",
            "shape": [rows, columns],
            "values_wire": [
                [1.0 if row == column and row < diagonal_count else 0.0, 0.0]
                for row in range(rows)
                for column in range(columns)
            ],
            "tensor_sha": "",
        },
        "tensor_sha",
    )


def _status(defined: bool) -> dict[str, object]:
    return {"defined": defined, "reason": None if defined else "response_null"}


def _build_synthetic_parent_body() -> dict[str, object]:
    parent = _minimal_record("ParentFreezeV3Manifest")
    candidate = parent["reviewed_candidate_v3"]
    audit = parent["signing_audit"]
    parent["parent_freeze_schema_version"] = "v3m0.parent-freeze.v3"
    parent["preparation_commit_sha"] = hashlib.sha1(
        b"b7-synthetic-parent-preparation"
    ).hexdigest()
    parent["signing_commit_sha"] = hashlib.sha1(
        b"b7-synthetic-parent-signing"
    ).hexdigest()
    candidate["candidate_schema_version"] = "v3m0.parent-freeze-candidate.v3"
    candidate["preparation_commit_sha"] = parent["preparation_commit_sha"]
    _resign_tree("ParentFreezeCandidateV3Manifest", candidate)

    source_specs = (
        (
            "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md",
            "SIGNED_INCREMENTAL_ERRATUM",
            "C05_C18_SCENARIO_RESPONSE_GEOMETRY",
        ),
        (
            "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md",
            "SIGNED_CONSTRUCTION_ERRATUM",
            "C19_REAL20_REFREEZE_V2",
        ),
        (
            "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md",
            "SIGNED_ISSUANCE_PROTOCOL",
            "PARENT_V3_P_EPOCH_SIGNING",
        ),
        (
            "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md",
            "SIGNED_RUNTIME_AUTHORITY_PROTOCOL",
            "C19_METRIC_SUPPORT_AUTHORITY_V1",
        ),
    )
    references: list[dict[str, object]] = []
    for index, (path, role, scope) in enumerate(source_specs):
        reference = _minimal_record("SignedSourceRefV2")
        reference.update(
            {
                "source_ref_schema_version": "v3m0.signed-source-ref.v2",
                "source_role": role,
                "source_scope": scope,
                "relative_path": path,
                "raw_sha256": hashlib.sha256(
                    f"b7-synthetic-source-{index}".encode()
                ).hexdigest(),
                "preparation_commit_sha": parent["preparation_commit_sha"],
                "signing_commit_sha": parent["signing_commit_sha"],
            }
        )
        _resign_tree("SignedSourceRefV2", reference)
        references.append(reference)
    parent["signed_source_refs"] = references

    closure = [["docsv3/b7-nonauthority-synthetic-fixture.md", "9" * 64]]
    closure_root = _canonical_sha(
        {
            "reviewed_path_closure_schema_version": (
                "v3m0.parent-reviewed-path-closure.v1"
            ),
            "entries": [
                {"relative_path": path, "raw_sha256": raw_sha}
                for path, raw_sha in closure
            ],
        }
    )
    signature_wire = b"SSHSIG" + bytes(range(64))
    signature_text = base64.b64encode(signature_wire).decode("ascii")
    signature_armor = (
        "-----BEGIN SSH SIGNATURE-----\n"
        + "\n".join(
            signature_text[index : index + 70]
            for index in range(0, len(signature_text), 70)
        )
        + "\n-----END SSH SIGNATURE-----\n"
    )
    receipts: list[dict[str, object]] = []
    for index, role in enumerate(
        (
            "MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW",
            "AUTHORITY_AND_BOUNDARY_REVIEW",
        )
    ):
        receipt = _minimal_record("ParentReviewReceiptV1")
        receipt.update(
            {
                "receipt_schema_version": "v3m0.parent-review-receipt.v1",
                "review_role": role,
                "reviewer_id": f"b7-synthetic-reviewer-{index}",
                "reviewer_key_id": "SHA256:"
                + base64.b64encode(bytes([index + 1]) * 32)
                .decode("ascii")
                .rstrip("="),
                "signature_algorithm": "openssh-ed25519-v1",
                "preparation_commit_sha": parent["preparation_commit_sha"],
                "reviewed_candidate_sha": candidate["candidate_sha"],
                "reviewed_path_closure": _clone(closure),
                "reviewed_path_closure_sha": closure_root,
                "verdict": "PASS",
                "signature_armor": signature_armor,
            }
        )
        statement_fields = (
            "receipt_schema_version",
            "review_role",
            "reviewer_id",
            "reviewer_key_id",
            "signature_algorithm",
            "preparation_commit_sha",
            "reviewed_candidate_sha",
            "reviewed_path_closure",
            "reviewed_path_closure_sha",
            "verdict",
        )
        receipt["signed_statement_sha"] = _canonical_sha(
            {name: receipt[name] for name in statement_fields}
        )
        _resign_tree("ParentReviewReceiptV1", receipt)
        receipts.append(receipt)
    parent["review_receipts"] = receipts

    audit.update(
        {
            "audit_schema_version": "v3m0.parent-signing-audit.v1",
            "preparation_commit_sha": parent["preparation_commit_sha"],
            "signing_commit_sha": parent["signing_commit_sha"],
            "diff_allowlist_id": "parent-v3-signing-diff-v1",
            "review_receipt_shas": [item["receipt_sha"] for item in receipts],
            "signed_source_refs_root_sha": _canonical_sha(
                {
                    "signed_source_refs_schema_version": (
                        "v3m0.signed-source-ref-tuple.v1"
                    ),
                    "entries": references,
                }
            ),
            "reviewed_candidate_sha": candidate["candidate_sha"],
            "reviewed_path_closure_sha": closure_root,
            "source_closure_sha": candidate["source_closure_sha"],
        }
    )
    _resign_tree("ParentSigningAuditV1", audit)
    _resign_tree("ParentFreezeV3Manifest", parent)
    return parent


def _build_base_provenance() -> dict[str, object]:
    parent = _build_synthetic_parent_body()
    permit = _minimal_record("CalibrationApplicationPermitV3")
    calibration = permit["calibration"]
    outcome = calibration["calibration_outcome"]
    selection = _minimal_record("WindowThresholdSelection")
    selection["selected_fejer_order"] = 256
    _resign_tree("WindowThresholdSelection", selection)
    outcome["status"] = _status(True)
    outcome["selection"] = selection
    _resign_tree("WindowCalibrationOutcome", outcome)
    permit["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
    permit["selected_fejer_order"] = 256
    contract = permit["current_scenario_response_contract"]
    response_grid = contract["response_grid"]
    response_grid["spatial_ndim"] = 1
    response_grid["torus_denominators"] = [8]
    response_grid["reciprocal_indices"] = [[1]]
    direction = response_grid["direction_manifest"]
    direction["direction_ids"] = ["d0"]
    direction["primitive_directions"] = [[1]]
    direction["path_ids"] = ["p0"]
    direction["ordered_paths"] = [[[1]]]
    direction["closure_path_pairs"] = []
    _resign_tree("DirectionManifest", direction)
    _resign_tree("ResponseKGridManifest", response_grid)
    contract["response_reference_reciprocal_index"] = [1]
    contract["preregistered_phase_bands"] = [
        [1.4457963267948966, 1.6957963267948966]
    ]
    contract["bridge_tolerance"] = 1e-12
    calibration_spec = contract["current_readout_calibration_spec"]
    calibration_spec["spec_schema_version"] = (
        "v3m0.current-readout-calibration-spec.v3"
    )
    calibration_spec["source_metric_whitener"] = _matrix_tensor(10, 10, 10)
    calibration_spec["h_metric_whitener"] = _matrix_tensor(10, 10, 10)
    calibration_spec["curvature_incidence_operator"] = _matrix_tensor(6, 10, 6)
    calibration_spec["curvature_metric_whitener"] = _matrix_tensor(6, 6, 6)
    normalizer = calibration_spec["curvature_normalizer_protocol"]
    normalizer["spatial_shape"] = [8]
    normalizer["response_grid_sha"] = response_grid["response_grid_sha"]
    normalizer["ordered_reciprocal_indices"] = [[1]]
    normalizer["ordered_momentum_values"] = [[math.pi / 4.0]]
    normalizer["ordered_momentum_fp64_bits"] = [["3fe921fb54442d18"]]
    normalizer["ordered_normalizer_values"] = [0.5857864376269049]
    normalizer["ordered_normalizer_fp64_bits"] = ["3fe2bec333018867"]
    _resign_tree("CurrentCurvatureNormalizerProtocolV1", normalizer)
    geometry = contract["geometry_bundle"]
    geometry["source_whitener"] = _clone(
        calibration_spec["source_metric_whitener"]
    )
    geometry["h_whitener"] = _clone(calibration_spec["h_metric_whitener"])
    geometry["incidence_q"] = _clone(
        calibration_spec["curvature_incidence_operator"]
    )
    geometry["curvature_whitener"] = _clone(
        calibration_spec["curvature_metric_whitener"]
    )
    _resign_tree("C19ObserverGeometryBundleV1", geometry)
    calibration_spec["geometry_bundle_sha"] = geometry["geometry_bundle_sha"]
    _resign_tree("CurrentReadoutCalibrationSpecV3", calibration_spec)
    _resign_tree("CurrentScenarioResponseContractV3", contract)
    _resign_tree("CalibrationApplicationPermitV3", permit)

    materialization = _minimal_record("ApplicationScenarioMaterializationV3")
    materialization["permit"] = _clone(permit)
    materialization["current_application_authority"] = _clone(
        permit["current_application_authority"]
    )
    materialization["current_scenario_authority"] = _clone(
        permit["current_scenario_authority"]
    )
    materialization["current_scenario_response_contract"] = _clone(contract)
    basis = materialization["basis_contract"]
    channels = [f"q{index}" for index in range(20)]
    basis["state_schema_id"] = "v3m0.c19-real-canonical-state.v2"
    basis["channel_order"] = channels
    for role, field in (
        ("source", "scenario_source_basis"),
        ("readout", "scenario_readout_basis"),
    ):
        basis_body = basis[field]
        basis_body["role"] = role
        basis_body["state_schema_id"] = basis["state_schema_id"]
        basis_body["channel_order"] = channels
        basis_body["vectors_wire"] = [
            [
                [1.0 if row == column else 0.0, 0.0]
                for column in range(len(channels))
            ]
            for row in range(10)
        ]
        _resign_tree("BasisManifest", basis_body)
    basis["source_injection"] = _matrix_tensor(20, 10, 10)
    basis["readout_coisometry"] = _matrix_tensor(10, 20, 10)
    basis["source_trial_vectors"] = _matrix_tensor(10, 10, 10)
    basis["expected_actual_shell_rank"] = 10
    basis["expected_matched_shell_rank"] = 10
    _resign_tree("C19BasisContractV2", basis)
    _resign_tree("ApplicationScenarioMaterializationV3", materialization)

    actual_bridge = _minimal_record("BridgeGridAuthorityV3")
    actual_bridge["materialization"] = _clone(materialization)
    actual_bridge["factory_binding"]["branch"] = "actual"
    _resign_tree("FactoryBranchBindingV3", actual_bridge["factory_binding"])
    bridge_grid = actual_bridge["bridge_grid"]
    bridge_grid["spatial_shape"] = [8]
    bridge_grid["torus_denominators"] = [8]
    bridge_grid["reciprocal_indices"] = [[0]]
    _resign_tree("BridgeKGridManifest", bridge_grid)
    _resign_tree("BridgeGridAuthorityV3", actual_bridge)

    matched_bridge = _clone(actual_bridge)
    matched_bridge["factory_binding"]["branch"] = "matched_ablated"
    _resign_tree("FactoryBranchBindingV3", matched_bridge["factory_binding"])
    _resign_tree("BridgeGridAuthorityV3", matched_bridge)
    fixture = {
        "provenance_fixture_schema_version": (
            "experimental.v3m0.b7.provenance-fixture.v1"
        ),
        "parent_freeze_v3_body": parent,
        "permit_body": permit,
        "materialization_body": materialization,
        "current_scenario_response_contract_v3_body": _clone(contract),
        "actual_bridge_grid_authority_body": actual_bridge,
        "matched_ablated_bridge_grid_authority_body": matched_bridge,
        "provenance_fixture_sha": "",
    }
    return _seal(fixture, "provenance_fixture_sha")


def _component_wrapper(
    component_id: str,
    complete_body: dict[str, object],
) -> dict[str, object]:
    contracts = json.loads(_core._B7_COMPONENT_CONTRACTS_JSON_V1)
    entry = next(item for item in contracts if item[0] == component_id)
    body_type, hash_field, lineage = entry[1], entry[3], entry[4]
    body = {
        "component_body_schema_version": (
            "experimental.v3m0.b7.synthetic-component-body.v1"
        ),
        "component_id": component_id,
        "body_type": body_type,
        "complete_body": complete_body,
        "body_raw_canonical_sha256": _canonical_sha(complete_body),
        "body_self_hash_field": hash_field,
        "body_self_hash_value": complete_body[hash_field],
        "lineage_parent_component_ids": lineage,
        "fejer_order": 256,
        "component_sha": "",
    }
    return _seal(body, "component_sha")


def _build_graph(provenance: dict[str, object]) -> dict[str, object]:
    parent = provenance["parent_freeze_v3_body"]
    permit = provenance["permit_body"]
    materialization = provenance["materialization_body"]
    actual_bridge = provenance["actual_bridge_grid_authority_body"]
    matched_bridge = provenance["matched_ablated_bridge_grid_authority_body"]
    selection = permit["calibration"]["calibration_outcome"]["selection"]

    actual_transition = _minimal_record("TransitionAuthorityV3")
    actual_transition["materialization"] = _clone(materialization)
    actual_transition["factory_binding"]["branch"] = "actual"
    _resign_tree("TransitionAuthorityV3", actual_transition)
    matched_transition = _clone(actual_transition)
    matched_transition["factory_binding"]["branch"] = "matched_ablated"
    _resign_tree("TransitionAuthorityV3", matched_transition)

    actual_metric = _minimal_record("MetricSignedSupportAttestationV1")
    actual_metric["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
    actual_metric["application_scenario_materialization_v3_sha"] = materialization[
        "materialization_sha"
    ]
    actual_metric["factory_role"] = "actual"
    _resign_tree("MetricSignedSupportAttestationV1", actual_metric)
    matched_metric = _clone(actual_metric)
    matched_metric["factory_role"] = "matched_ablated"
    _resign_tree("MetricSignedSupportAttestationV1", matched_metric)

    def certification(
        transition: dict[str, object],
        metric: dict[str, object],
        bridge: dict[str, object],
    ) -> dict[str, object]:
        certificate = _minimal_record("DynamicsCertificateV3")
        certificate["parent_freeze_v3"] = _clone(parent)
        certificate["materialization"] = _clone(materialization)
        certificate["transition_authority"] = _clone(transition)
        certificate["metric_attestation"] = _clone(metric)
        certificate["bridge_grid_authority"] = _clone(bridge)
        dynamics_grid = certificate["dynamics_grid_authority"]
        dynamics_grid["transition_authority"] = _clone(transition)
        dynamics_grid["metric_support_attestation"] = _clone(metric)
        _resign_tree("DynamicsGridAuthorityV3", dynamics_grid)
        bridge_spec = certificate["full_state_bridge_spec"]
        bridge_spec["bridge_grid"] = _clone(bridge["bridge_grid"])
        bridge_spec["macro_steps"] = [2]
        bridge_spec["bridge_tolerance"] = permit[
            "current_scenario_response_contract"
        ]["bridge_tolerance"]
        _resign_tree("FullStateBridgeSpec", bridge_spec)
        _resign_tree("DynamicsCertificateV3", certificate)
        outcome = _minimal_record("DynamicsCertificationOutcomeV3")
        attempt = outcome["attempt_audit"]
        attempt["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
        attempt["materialization_sha"] = materialization["materialization_sha"]
        attempt["transition_authority_sha"] = transition[
            "transition_authority_sha"
        ]
        attempt["metric_attestation_sha"] = metric["attestation_sha"]
        attempt["bridge_grid_authority_sha"] = bridge["grid_authority_sha"]
        attempt["first_failure"] = None
        _resign_tree("DynamicsCertificationAttemptAuditV3", attempt)
        outcome["status"] = _status(True)
        outcome["failure"] = None
        outcome["certificate"] = certificate
        _resign_tree("DynamicsCertificationOutcomeV3", outcome)
        return outcome

    complete_bodies = {
        "calibration_selection": selection,
        "permit": permit,
        "materialization": materialization,
        "actual_transition_outcome": actual_transition,
        "matched_ablated_transition_outcome": matched_transition,
        "actual_metric_authority": actual_metric,
        "matched_ablated_metric_authority": matched_metric,
        "actual_bridge_grid_authority": actual_bridge,
        "matched_ablated_bridge_grid_authority": matched_bridge,
        "actual_certificate_outcome": certification(
            actual_transition, actual_metric, actual_bridge
        ),
        "matched_ablated_certificate_outcome": certification(
            matched_transition, matched_metric, matched_bridge
        ),
    }
    contracts = json.loads(_core._B7_COMPONENT_CONTRACTS_JSON_V1)
    component_order = [item[0] for item in contracts]
    components = [
        _component_wrapper(component_id, complete_bodies[component_id])
        for component_id in component_order
    ]
    by_id = {item["component_id"]: item for item in components}
    root_entries = [
        {
            "component_id": item["component_id"],
            "body_self_hash_value": item["body_self_hash_value"],
        }
        for item in components
    ]
    bindings = [
        _seal(
            {
                "binding_schema_version": (
                    "experimental.v3m0.b7.t-bearer-binding.v1"
                ),
                "component_id": item["component_id"],
                "body_sha": item["body_self_hash_value"],
                "fejer_order": 256,
                "binding_sha": "",
            },
            "binding_sha",
        )
        for item in components
    ]
    field_by_component = {
        "calibration_selection": "calibration_selection_sha",
        "permit": "permit_sha",
        "materialization": "materialization_sha",
        "actual_transition_outcome": "actual_transition_outcome_sha",
        "matched_ablated_transition_outcome": (
            "matched_ablated_transition_outcome_sha"
        ),
        "actual_metric_authority": "actual_metric_authority_sha",
        "matched_ablated_metric_authority": "matched_ablated_metric_authority_sha",
        "actual_bridge_grid_authority": "actual_bridge_grid_authority_sha",
        "matched_ablated_bridge_grid_authority": (
            "matched_ablated_bridge_grid_authority_sha"
        ),
        "actual_certificate_outcome": "actual_certificate_outcome_sha",
        "matched_ablated_certificate_outcome": (
            "matched_ablated_certificate_outcome_sha"
        ),
    }
    graph = {
        "graph_manifest_schema_version": (
            "experimental.v3m0.b7.synthetic-graph-manifest.v1"
        ),
        "graph_profile_id": "v3m0-b7-d1-nonauthority-synthetic-private-graph-v1",
        "authority_state": "NON_AUTHORITY_SYNTHETIC",
        "parent_freeze_v3_body": _clone(parent),
        "parent_freeze_v3_sha": parent["parent_freeze_v3_sha"],
        "synthetic_graph_component_root_sha": _canonical_sha(root_entries),
        "selected_fejer_order": 256,
        "permit_fejer_order": 256,
        "materialization_fejer_order": 256,
        "ordered_component_bodies": components,
        "ordered_t_bearer_bindings": bindings,
        "graph_sha": "",
    }
    for component_id, field in field_by_component.items():
        graph[field] = by_id[component_id]["body_self_hash_value"]
    ordered_fields = (
        "graph_manifest_schema_version",
        "graph_profile_id",
        "authority_state",
        "parent_freeze_v3_body",
        "parent_freeze_v3_sha",
        "synthetic_graph_component_root_sha",
        "selected_fejer_order",
        "calibration_selection_sha",
        "permit_sha",
        "permit_fejer_order",
        "materialization_sha",
        "materialization_fejer_order",
        "actual_transition_outcome_sha",
        "matched_ablated_transition_outcome_sha",
        "actual_metric_authority_sha",
        "matched_ablated_metric_authority_sha",
        "actual_bridge_grid_authority_sha",
        "matched_ablated_bridge_grid_authority_sha",
        "actual_certificate_outcome_sha",
        "matched_ablated_certificate_outcome_sha",
        "ordered_component_bodies",
        "ordered_t_bearer_bindings",
        "graph_sha",
    )
    graph = {name: graph[name] for name in ordered_fields}
    return _seal(graph, "graph_sha")


def _component_body(graph: dict[str, object], component_id: str) -> dict[str, object]:
    return next(
        item["complete_body"]
        for item in graph["ordered_component_bodies"]
        if item["component_id"] == component_id
    )


def _build_run_spec(
    provenance: dict[str, object],
    graph: dict[str, object],
) -> dict[str, object]:
    spec = _minimal_record("ResponseRunSpecV3")
    parent = provenance["parent_freeze_v3_body"]
    permit = provenance["permit_body"]
    materialization = provenance["materialization_body"]
    contract = provenance["current_scenario_response_contract_v3_body"]
    actual_bridge = provenance["actual_bridge_grid_authority_body"]
    calibration = permit["calibration"]
    outcome = calibration["calibration_outcome"]
    selection = outcome["selection"]
    protocol = outcome["manifest"]["window_protocol"]
    basis = materialization["basis_contract"]
    spec.update(
        {
            "parent_freeze_v3_sha": parent["parent_freeze_v3_sha"],
            "permit_sha": permit["permit_sha"],
            "materialization_sha": materialization["materialization_sha"],
            "window_calibration_v3_sha": calibration["calibration_v3_sha"],
            "window_protocol_sha": protocol["protocol_sha"],
            "window_selection_sha": selection["selection_sha"],
            "current_scenario_response_contract_v3_sha": contract[
                "response_contract_sha"
            ],
            "application_instance_id": contract["application_instance_id"],
            "scenario_id": contract["scenario_id"],
            "scenario_sha": permit["current_scenario_authority"][
                "scenario_authority_sha"
            ],
            "selected_fejer_order": 256,
            "channel_order": list(basis["channel_order"]),
            "spatial_shape": [8],
            "source_basis": _clone(basis["scenario_source_basis"]),
            "readout_basis": _clone(basis["scenario_readout_basis"]),
            "source_injection_isometry": _clone(basis["source_injection"]),
            "readout_coisometry": _clone(basis["readout_coisometry"]),
            "response_grid": _clone(contract["response_grid"]),
            "source_readout_bridge_grid": _clone(actual_bridge["bridge_grid"]),
            "source_readout_bridge_steps": [2],
            "reference_reciprocal_index": list(
                contract["response_reference_reciprocal_index"]
            ),
            "preregistered_phase_bands": _clone(
                contract["preregistered_phase_bands"]
            ),
            "expected_shell_rank": 10,
            "source_trial_vectors": _clone(basis["source_trial_vectors"]),
            "bridge_tolerance": contract["bridge_tolerance"],
            "current_readout_calibration_spec": _clone(
                contract["current_readout_calibration_spec"]
            ),
            "actual_bridge_grid_authority_sha": graph[
                "actual_bridge_grid_authority_sha"
            ],
            "matched_ablated_bridge_grid_authority_sha": graph[
                "matched_ablated_bridge_grid_authority_sha"
            ],
        }
    )
    _resign_tree("ResponseRunSpecV3", spec)
    return spec


def _rebind_provenance_lineage(
    provenance: dict[str, object],
    graph: dict[str, object],
    run_spec: dict[str, object],
) -> dict[str, object]:
    permit = provenance["permit_body"]
    contract = permit["current_scenario_response_contract"]
    actual_transition = _component_body(graph, "actual_transition_outcome")
    matched_transition = _component_body(
        graph, "matched_ablated_transition_outcome"
    )
    actual_factory_sha = actual_transition["factory_binding"]["factory"][
        "factory_sha"
    ]
    matched_factory_sha = matched_transition["factory_binding"]["factory"][
        "factory_sha"
    ]
    contract["actual_factory_sha"] = actual_factory_sha
    contract["matched_factory_sha"] = matched_factory_sha
    _resign_tree("CurrentScenarioResponseContractV3", contract)

    calibration = permit["calibration"]
    manifest = calibration["calibration_outcome"]["manifest"]
    registry = manifest["control_registry"]
    entry = _minimal_record("ControlRegistryEntry")
    entry["control_id"] = "full"
    entry["factory_sha"] = actual_factory_sha
    entry["source_basis"] = _clone(run_spec["source_basis"])
    entry["readout_basis"] = _clone(run_spec["readout_basis"])
    entry["mode_count"] = 10
    entry["expected_h_actual_rank"] = 10
    entry["expected_h_ablated_rank"] = 10
    entry["expected_curv_actual_rank"] = 6
    entry["expected_curv_ablated_rank"] = 6
    entry["parent_freeze_sha"] = provenance["parent_freeze_v3_body"][
        "parent_freeze_v3_sha"
    ]
    _resign_tree("ControlRegistryEntry", entry)
    registry["entries"] = [entry]
    registry["parent_freeze_sha"] = entry["parent_freeze_sha"]
    _resign_tree("ClosedControlRegistry", registry)

    protocol = manifest["window_protocol"]
    protocol_entry = _minimal_record("ControlWindowProtocolEntry")
    protocol_entry.update(
        {
            "control_id": "full",
            "control_registry_entry_sha": entry["entry_sha"],
            "response_grid": _clone(run_spec["response_grid"]),
            "source_readout_bridge_grid": _clone(
                run_spec["source_readout_bridge_grid"]
            ),
            "source_readout_bridge_steps": list(
                run_spec["source_readout_bridge_steps"]
            ),
            "reference_reciprocal_index": list(
                run_spec["reference_reciprocal_index"]
            ),
            "expected_shell_rank": run_spec["expected_shell_rank"],
            "preregistered_phase_bands": _clone(
                run_spec["preregistered_phase_bands"]
            ),
        }
    )
    _resign_tree("ControlWindowProtocolEntry", protocol_entry)
    protocol["control_registry_sha"] = registry["registry_sha"]
    protocol["parent_freeze_sha"] = entry["parent_freeze_sha"]
    protocol["t_candidates"] = [256]
    protocol["control_entries"] = [protocol_entry]
    _resign_tree("WindowCalibrationProtocol", protocol)
    _resign_tree("WindowThresholdCalibrationManifest", manifest)
    _resign_tree("WindowCalibrationOutcome", calibration["calibration_outcome"])
    _resign_tree("WindowThresholdCalibrationV3", calibration)

    permit["current_scenario_authority"]["response_contract"] = _clone(contract)
    _resign_tree("CurrentScenarioAuthorityV3", permit["current_scenario_authority"])
    _resign_tree("CalibrationApplicationPermitV3", permit)
    materialization = provenance["materialization_body"]
    materialization["permit"] = _clone(permit)
    materialization["current_application_authority"] = _clone(
        permit["current_application_authority"]
    )
    materialization["current_scenario_authority"] = _clone(
        permit["current_scenario_authority"]
    )
    materialization["current_scenario_response_contract"] = _clone(contract)
    _resign_tree("ApplicationScenarioMaterializationV3", materialization)
    provenance["current_scenario_response_contract_v3_body"] = _clone(contract)
    for field in (
        "actual_bridge_grid_authority_body",
        "matched_ablated_bridge_grid_authority_body",
    ):
        provenance[field]["materialization"] = _clone(materialization)
        _resign_tree("BridgeGridAuthorityV3", provenance[field])
    return _seal(provenance, "provenance_fixture_sha")


def build_synthetic_graph_bundle_v1() -> dict[str, object]:
    """Build and fully validate one self-consistent non-authority B1--B6 graph."""

    from experiments.v3m0_b7_schema_lab import common

    provenance = _build_base_provenance()
    preliminary_graph = _build_graph(provenance)
    preliminary_run_spec = _build_run_spec(provenance, preliminary_graph)
    provenance = _rebind_provenance_lineage(
        provenance,
        preliminary_graph,
        preliminary_run_spec,
    )
    graph = _build_graph(provenance)
    run_spec = _build_run_spec(provenance, graph)
    common.validate_synthetic_graph_manifest_v1(graph)
    common.validate_provenance_fixture_v1(provenance)
    common.validate_response_run_spec_fixture_v1(run_spec, provenance, graph)
    return {
        "provenance": provenance,
        "graph": graph,
        "run_spec": run_spec,
    }


def _branch_lineage(
    graph: dict[str, object],
    branch: str,
) -> dict[str, object]:
    prefix = "actual" if branch == "actual" else "matched_ablated"
    transition = _component_body(graph, f"{prefix}_transition_outcome")
    certificate_outcome = _component_body(graph, f"{prefix}_certificate_outcome")
    return {
        "factory_sha": transition["factory_binding"]["factory"]["factory_sha"],
        "transition_sha": transition["measured_transition"]["transition_sha"],
        "dynamics_certificate_sha": certificate_outcome["certificate"][
            "certificate_sha"
        ],
        "dt": transition["measured_transition"]["dt"],
    }


_CAPTURE_CASES = (
    (
        "reference_failure",
        "reference_failure",
        ("reference",),
    ),
    (
        "shell_failure",
        "shell_failure",
        ("reference", "shell"),
    ),
    (
        "actual_response_values_failure",
        "actual_response_values_failure",
        ("reference", "shell", "actual_response_values"),
    ),
    (
        "matched_response_values_failure",
        "matched_response_values_failure",
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
        ),
    ),
    (
        "actual_bridge_failure",
        "actual_bridge_failure",
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
        ),
    ),
    (
        "matched_bridge_failure",
        "matched_bridge_failure",
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
            "matched_ablated_bridge",
        ),
    ),
    (
        "success",
        "success",
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
            "matched_ablated_bridge",
        ),
    ),
)


def _capture_reference_spec(bundle: dict[str, object]) -> dict[str, object]:
    provenance = bundle["provenance"]
    run_spec = bundle["run_spec"]
    control_entry = provenance["permit_body"]["calibration"][
        "calibration_outcome"
    ]["manifest"]["control_registry"]["entries"][0]
    actual = _branch_lineage(bundle["graph"], "actual")
    return _seal(
        {
            "reference_spec_schema_version": "v3m0.endpoint-reference-spec.v1",
            "window_protocol_sha": run_spec["window_protocol_sha"],
            "control_registry_entry": _clone(control_entry),
            "actual_factory_sha": actual["factory_sha"],
            "actual_transition_sha": actual["transition_sha"],
            "actual_dynamics_certificate_sha": actual[
                "dynamics_certificate_sha"
            ],
            "candidate_fejer_order": run_spec["selected_fejer_order"],
            "reference_reciprocal_index": _clone(
                run_spec["reference_reciprocal_index"]
            ),
            "preregistered_phase_bands": _clone(
                run_spec["preregistered_phase_bands"]
            ),
            "expected_shell_rank": run_spec["expected_shell_rank"],
            "expected_shell_rank_source_id": (
                "parent-freeze-control-application-spec-v1"
            ),
            "reference_spec_sha": "",
        },
        "reference_spec_sha",
    )


def _capture_shell_spec_template(bundle: dict[str, object]) -> dict[str, object]:
    provenance = bundle["provenance"]
    run_spec = bundle["run_spec"]
    control_entry = provenance["permit_body"]["calibration"][
        "calibration_outcome"
    ]["manifest"]["control_registry"]["entries"][0]
    return _seal(
        {
            "shell_spec_schema_version": "v3m0.endpoint-shell-spec.v1",
            "window_protocol_sha": run_spec["window_protocol_sha"],
            "control_registry_entry": _clone(control_entry),
            "response_grid": _clone(run_spec["response_grid"]),
            "preregistered_phase_bands": _clone(
                run_spec["preregistered_phase_bands"]
            ),
            "candidate_fejer_order": run_spec["selected_fejer_order"],
            "endpoint_reference_projector": None,
            "extraction_protocol_id": "endpoint-single-node-reference-v1",
            "shell_spec_sha": "",
        },
        "shell_spec_sha",
    )


def _capture_leaf_inputs(
    bundle: dict[str, object],
    case_id: str,
) -> dict[str, object]:
    run_spec = bundle["run_spec"]
    state_count = len(run_spec["channel_order"])
    shell_rank = run_spec["expected_shell_rank"]
    success_transition = np.diag(
        np.asarray(
            [1.0j] * shell_rank + [1.0 + 0.0j] * (state_count - shell_rank),
            dtype=np.complex128,
        )
    )
    failure_transition = np.eye(state_count, dtype=np.complex128)
    metric = np.eye(state_count, dtype=np.complex128)
    source_injection = np.zeros((state_count, shell_rank), dtype=np.complex128)
    source_injection[:shell_rank, :] = np.eye(shell_rank, dtype=np.complex128)
    readout = np.zeros((shell_rank, state_count), dtype=np.complex128)
    readout[:, :shell_rank] = np.eye(shell_rank, dtype=np.complex128)
    bridge_differences = tuple(
        (
            tuple(reciprocal_index),
            macro_steps,
            np.zeros((shell_rank, shell_rank), dtype=np.complex128),
        )
        for reciprocal_index in run_spec["source_readout_bridge_grid"][
            "reciprocal_indices"
        ]
        for macro_steps in run_spec["source_readout_bridge_steps"]
    )
    return {
        "reference_spec": _capture_reference_spec(bundle),
        "shell_spec_template": _capture_shell_spec_template(bundle),
        "reference_transition_matrix": (
            failure_transition
            if case_id == "reference_failure"
            else success_transition
        ),
        "reference_metric_matrix": metric,
        "ordered_shell_transition_matrices": (
            failure_transition if case_id == "shell_failure" else success_transition,
        ),
        "ordered_shell_metric_matrices": (metric,),
        "source_injection_matrix": source_injection,
        "readout_matrix": readout,
        "ordered_actual_transition_matrices": (success_transition,),
        "ordered_actual_metric_matrices": (metric,),
        "ordered_matched_ablated_transition_matrices": (success_transition,),
        "ordered_matched_ablated_metric_matrices": (metric,),
        "ordered_actual_raw_differences": bridge_differences,
        "ordered_matched_ablated_raw_differences": bridge_differences,
    }


def build_ordered_d0_transcripts_v1(
    bundle: dict[str, object],
    *,
    corpus_spec_sha: str,
    environment_manifest_sha: str,
) -> list[dict[str, object]]:
    """Capture the frozen seven-case scheduler against exactly one graph body."""

    from experiments.v3m0_b7_schema_lab import common

    transcripts = [
        common.capture_normalized_transcript_from_raw_v1(
            case_id=case_id,
            corpus_spec_sha=corpus_spec_sha,
            environment_manifest_sha=environment_manifest_sha,
            provenance_fixture=bundle["provenance"],
            response_run_spec_fixture=bundle["run_spec"],
            synthetic_graph_manifest=bundle["graph"],
            leaf_inputs=_capture_leaf_inputs(bundle, case_id),
        )
        for case_id, _terminal_tag, _trace in _CAPTURE_CASES
    ]
    return transcripts


def _build_metric_spec(
    common_source_bytes: bytes,
    compare_source_bytes: bytes,
) -> dict[str, object]:
    from experiments.v3m0_b7_schema_lab import common

    metric = {
        "metric_spec_schema_version": "experimental.v3m0.b7.metric-spec.v1",
        "metric_algorithm_id": "v3m0-b7-schema-metrics-v1",
        "metric_contract_sha": common._METRIC_CONTRACT_SHA_V1,
        "metric_order": list(common._METRIC_ORDER_V1),
        "evidence_pointer_order": list(common._EVIDENCE_POINTER_ORDER_V1),
        "invalid_presence_bit_width": 9,
        "reachable_closure_algorithm_id": (
            "python-ast-route-local-reachable-closure-v1"
        ),
        "branch_count_algorithm_id": "python-ast-branch-contribution-v1",
        "b8_diff_algorithm_id": "python-difflib-unified-n0-v1",
        "common_source_sha256": hashlib.sha256(common_source_bytes).hexdigest(),
        "compare_source_sha256": hashlib.sha256(compare_source_bytes).hexdigest(),
        "metric_spec_sha": "",
    }
    _seal(metric, "metric_spec_sha")
    common.validate_metric_spec_v1(
        metric,
        common_source_bytes,
        compare_source_bytes,
    )
    return metric


def _build_corpus_spec(metric_spec_sha: str) -> dict[str, object]:
    from experiments.v3m0_b7_schema_lab import common

    cases: list[dict[str, object]] = []
    for row in common._CASE_CONTRACTS_V1:
        (
            ordinal,
            case_id,
            terminal_tag,
            failure_stage,
            presence_bits,
            actual_failure,
            matched_failure,
            trace,
            leaf_ids,
        ) = row
        case = {
            "case_schema_version": "experimental.v3m0.b7.corpus-case.v1",
            "case_ordinal": ordinal,
            "case_id": case_id,
            "terminal_tag": terminal_tag,
            "injected_failure_stage": failure_stage,
            "presence_bits": presence_bits,
            "actual_attempt_failure": actual_failure,
            "matched_ablated_attempt_failure": matched_failure,
            "expected_callback_trace": list(trace),
            "expected_leaf_ids": list(leaf_ids),
            "case_sha": "",
        }
        _seal(case, "case_sha")
        common.validate_corpus_case_v1(case)
        cases.append(case)
    nested_rules: list[dict[str, object]] = []
    for pointer, body_kind, hash_field, nullable in (
        common._NESTED_BODY_RULE_PROJECTIONS_V1
    ):
        rule = {
            "rule_schema_version": "experimental.v3m0.b7.nested-body-rule.v1",
            "json_pointer": pointer,
            "body_kind": body_kind,
            "hash_field": hash_field,
            "nullable": nullable,
            "full_body_required": True,
            "rule_sha": "",
        }
        _seal(rule, "rule_sha")
        common.validate_nested_body_rule_v1(rule)
        nested_rules.append(rule)
    corpus = {
        "corpus_spec_schema_version": "experimental.v3m0.b7.corpus-spec.v1",
        "transcript_schema_version": (
            "experimental.v3m0.b7.normalized-transcript.v1"
        ),
        "canonical_json_profile_id": "canonical-json-sha256-v1",
        "scheduler_stage_order": list(common._SCHEDULER_STAGE_ORDER_V1),
        "presence_pointer_order": list(common._PRESENCE_POINTER_ORDER_V1),
        "terminal_tag_order": list(common._TERMINAL_TAG_ORDER_V1),
        "case_contract_sha": common._CASE_CONTRACT_SHA_V1,
        "ordered_case_specs": cases,
        "nested_body_rules": nested_rules,
        "mutation_algorithm_id": "v3m0-b7-exhaustive-mutation-v1",
        "mutation_class_order": list(common._MUTATION_CLASSES_V1),
        "mutation_operation_order": list(common._MUTATION_OPERATIONS_V1),
        "mutation_generation_contract_sha": (
            common._MUTATION_GENERATION_CONTRACT_SHA_V1
        ),
        "mutation_generation_rules": list(common._MUTATION_GENERATION_RULES_V1),
        "upstream_invalid_probe_rule": "M10_UPSTREAM_INVALID_ZERO_TRANSCRIPT",
        "metric_spec_sha": metric_spec_sha,
        "corpus_spec_sha": "",
    }
    _seal(corpus, "corpus_spec_sha")
    common.validate_corpus_spec_v1(corpus, metric_spec_sha)
    return corpus


def _build_mutation_universe(
    transcripts: list[dict[str, object]],
    corpus: dict[str, object],
    common_source_bytes: bytes,
) -> dict[str, object]:
    from experiments.v3m0_b7_schema_lab import common

    mutations = common.generate_ordered_mutations_v1(transcripts)
    universe = {
        "mutation_universe_schema_version": (
            "experimental.v3m0.b7.mutation-universe.v1"
        ),
        "corpus_spec_sha": corpus["corpus_spec_sha"],
        "mutation_generation_contract_sha": corpus[
            "mutation_generation_contract_sha"
        ],
        "generator_source_sha256": hashlib.sha256(common_source_bytes).hexdigest(),
        "ordered_mutations": mutations,
        "mutation_count": len(mutations),
        "mutation_universe_sha": "",
    }
    _seal(universe, "mutation_universe_sha")
    common.validate_mutation_universe_v1(
        universe,
        transcripts,
        corpus["corpus_spec_sha"],
        corpus["mutation_generation_contract_sha"],
        common_source_bytes,
    )
    return universe


def _observe_environment_manifest(
    python_invocation_path: str,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    from experiments.v3m0_b7_schema_lab import compare

    manifest = compare.capture_environment_manifest_v2(
        python_invocation_path=python_invocation_path
    )
    identity = compare.precheck_python_invocation_identity_v2(
        python_invocation_path=manifest["python_invocation_path"],
        recorded_realpath=manifest["python_executable_realpath"],
        recorded_raw_sha256=manifest["python_executable_raw_sha256"],
        recorded_venv_prefix=manifest["python_venv_prefix"],
        recorded_pyvenv_cfg_path=manifest["python_pyvenv_cfg_path"],
        recorded_pyvenv_cfg_raw_sha256=manifest[
            "python_pyvenv_cfg_raw_sha256"
        ],
    )
    probe = compare.run_python_environment_import_probe_v2(
        python_invocation_path=manifest["python_invocation_path"],
        python_identity_observation=identity,
    )
    return manifest, identity, probe


def build_corpus_fixture_v2(
    *,
    repository_root: Path,
    python_invocation_path: str,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Build the complete graph-bearing D0_FROZEN_CAPTURE fixture in memory."""

    root = Path(repository_root)
    common_source_bytes = (
        root / "experiments/v3m0_b7_schema_lab/common.py"
    ).read_bytes()
    compare_source_bytes = (
        root / "experiments/v3m0_b7_schema_lab/compare.py"
    ).read_bytes()
    metric = _build_metric_spec(common_source_bytes, compare_source_bytes)
    corpus = _build_corpus_spec(metric["metric_spec_sha"])
    environment, identity, probe = _observe_environment_manifest(
        python_invocation_path
    )
    bundle = build_synthetic_graph_bundle_v1()
    transcripts = build_ordered_d0_transcripts_v1(
        bundle,
        corpus_spec_sha=corpus["corpus_spec_sha"],
        environment_manifest_sha=environment["environment_sha"],
    )
    mutation_universe = _build_mutation_universe(
        transcripts,
        corpus,
        common_source_bytes,
    )
    fixture = {
        "fixture_schema_version": "experimental.v3m0.b7.corpus-fixture.v2",
        "corpus_spec": corpus,
        "mutation_universe": mutation_universe,
        "metric_spec": metric,
        "environment_manifest": environment,
        "synthetic_graph_manifest": bundle["graph"],
        "ordered_d0_transcripts": transcripts,
        "fixture_sha": "",
    }
    _seal(fixture, "fixture_sha")
    return fixture, identity, probe


def render_fixture_bytes_v1(fixture: dict[str, object]) -> bytes:
    """Render exact fixture bytes: project canonical JSON followed by one LF."""

    return _core.canonical_json_bytes_v1(fixture) + b"\n"


def validate_corpus_fixture_for_materialization_v1(
    *,
    repository_root: Path,
    fixture: dict[str, object],
    python_identity_observation: dict[str, object],
    python_probe_result: dict[str, object],
) -> dict[str, object]:
    """Run the full source/environment-bound fixture validator before writing."""

    from experiments.v3m0_b7_schema_lab import common

    root = Path(repository_root).resolve(strict=True)
    common_source_bytes = (
        root / "experiments/v3m0_b7_schema_lab/common.py"
    ).read_bytes()
    compare_source_bytes = (
        root / "experiments/v3m0_b7_schema_lab/compare.py"
    ).read_bytes()
    validated = common.validate_corpus_fixture_v2(
        fixture,
        common_source_bytes,
        compare_source_bytes,
        python_identity_observation=python_identity_observation,
        python_probe_result=python_probe_result,
    )
    if _core.canonical_json_bytes_v1(validated) != _core.canonical_json_bytes_v1(
        fixture
    ):
        raise ValueError("完整 fixture validator 替换了待物化对象")
    return validated


def _materialization_summary_v1(
    fixture: dict[str, object],
    fixture_raw_bytes: bytes,
) -> dict[str, object]:
    if type(fixture) is not dict:
        raise TypeError("fixture 必须是精确 JSON 对象")
    fixture_sha = fixture.get("fixture_sha")
    mutation_universe = fixture.get("mutation_universe")
    mutation_count = (
        mutation_universe.get("mutation_count")
        if type(mutation_universe) is dict
        else None
    )
    if (
        type(fixture_sha) is not str
        or len(fixture_sha) != 64
        or any(character not in "0123456789abcdef" for character in fixture_sha)
    ):
        raise ValueError("fixture_sha 不是小写 sha256")
    if type(mutation_count) is not int or mutation_count < 0:
        raise ValueError("mutation_count 必须是非负精确整数")
    expected_fixture_sha = _core.canonical_sha_v1(
        {name: value for name, value in fixture.items() if name != "fixture_sha"}
    )
    if fixture_sha != expected_fixture_sha:
        raise ValueError("fixture 自哈希与完整对象不一致")
    return {
        "fixture_raw_sha256": hashlib.sha256(fixture_raw_bytes).hexdigest(),
        "fixture_sha": fixture_sha,
        "mutation_count": mutation_count,
    }


def render_materialization_summary_v1(summary: dict[str, object]) -> bytes:
    """Render the only successful CLI stdout body as canonical JSON plus LF."""

    if (
        type(summary) is not dict
        or tuple(summary) != _MATERIALIZATION_SUMMARY_FIELDS_V1
    ):
        raise ValueError("物化摘要字段或顺序漂移")
    raw_sha = summary["fixture_raw_sha256"]
    fixture_sha = summary["fixture_sha"]
    mutation_count = summary["mutation_count"]
    for label, value in (
        ("fixture_raw_sha256", raw_sha),
        ("fixture_sha", fixture_sha),
    ):
        if (
            type(value) is not str
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError(f"{label} 不是小写 sha256")
    if type(mutation_count) is not int or mutation_count < 0:
        raise ValueError("mutation_count 必须是非负精确整数")
    return _core.canonical_json_bytes_v1(summary) + b"\n"


def _read_existing_target_v1(target: Path) -> bytes | None:
    try:
        initial = os.lstat(target)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(initial.st_mode):
        raise ValueError("固定 fixture 目标不得是符号链接")
    if not stat.S_ISREG(initial.st_mode):
        raise ValueError("固定 fixture 目标必须是普通文件")

    descriptor = None
    try:
        descriptor = os.open(
            target,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        before = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("固定 fixture 目标必须是普通文件")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1048576, remaining))
            if not chunk:
                raise ValueError("读取固定 fixture 时提前结束")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise ValueError("固定 fixture 在读取时增长")
        after = os.fstat(descriptor)
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if after_identity != before_identity:
            raise ValueError("固定 fixture 在读取时发生变化")
        return b"".join(chunks)
    except OSError as error:
        raise ValueError("固定 fixture 无法在禁止跟随链接时读取") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _fsync_directory_v1(directory: Path) -> None:
    descriptor = os.open(
        directory,
        os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY,
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_fixed_fixture_parent_v1(root: Path) -> Path:
    current = root
    for component in _FIXTURE_RELATIVE_PATH_V1.parts[:-1]:
        candidate = current / component
        try:
            observed = os.lstat(candidate)
        except FileNotFoundError:
            try:
                os.mkdir(candidate, 0o755)
            except FileExistsError:
                pass
            else:
                _fsync_directory_v1(current)
            observed = os.lstat(candidate)
        if stat.S_ISLNK(observed.st_mode):
            raise ValueError("固定 fixture 父目录不得经过符号链接")
        if not stat.S_ISDIR(observed.st_mode):
            raise ValueError("固定 fixture 父路径组件必须是目录")
        current = candidate
    return current


def materialize_corpus_fixture_v1(
    *,
    repository_root: Path,
    fixture: dict[str, object],
) -> dict[str, object]:
    """Create only the fixed corpus path; identical bytes are idempotent."""

    root = Path(repository_root).resolve(strict=True)
    fixture_raw_bytes = render_fixture_bytes_v1(fixture)
    summary = _materialization_summary_v1(fixture, fixture_raw_bytes)
    target_parent = _ensure_fixed_fixture_parent_v1(root)
    target = target_parent / _FIXTURE_RELATIVE_PATH_V1.name

    existing = _read_existing_target_v1(target)
    if existing is not None:
        if existing != fixture_raw_bytes:
            raise FileExistsError("固定 fixture 已存在且字节不同，拒绝覆盖")
        return summary

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=".v3m0-b7-corpus-",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    linked = False
    try:
        os.fchmod(file_descriptor, 0o444)
        view = memoryview(fixture_raw_bytes)
        written = 0
        while written < len(view):
            count = os.write(file_descriptor, view[written:])
            if count <= 0:
                raise OSError("临时 fixture 写入未取得进展")
            written += count
        os.fsync(file_descriptor)
        os.close(file_descriptor)
        file_descriptor = -1
        try:
            os.link(temporary, target, follow_symlinks=False)
            linked = True
        except FileExistsError:
            raced = _read_existing_target_v1(target)
            if raced != fixture_raw_bytes:
                raise FileExistsError(
                    "固定 fixture 在发布竞争中出现且字节不同，拒绝覆盖"
                ) from None
        if linked:
            _fsync_directory_v1(target.parent)
        os.unlink(temporary)
        _fsync_directory_v1(target.parent)
        if not linked:
            return summary
        published = _read_existing_target_v1(target)
        if published != fixture_raw_bytes:
            raise ValueError("固定 fixture 发布后字节校验失败")
        return summary
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _argument_parser_v1() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "构造并仅新建 tests/fixtures/v3m0_b7_schema_lab_corpus.json；"
            "同字节幂等，不同字节拒绝。"
        )
    )
    parser.add_argument(
        "--repository-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="仓库根目录；目标相对路径固定且不可覆盖指定。",
    )
    parser.add_argument(
        "--python-invocation-path",
        default=sys.executable,
        help="用于冻结环境身份的 Python venv 调用路径。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _argument_parser_v1().parse_args(argv)
    repository_root = Path(arguments.repository_root)
    fixture, identity, probe = build_corpus_fixture_v2(
        repository_root=repository_root,
        python_invocation_path=arguments.python_invocation_path,
    )
    fixture = validate_corpus_fixture_for_materialization_v1(
        repository_root=repository_root,
        fixture=fixture,
        python_identity_observation=identity,
        python_probe_result=probe,
    )
    summary = materialize_corpus_fixture_v1(
        repository_root=repository_root,
        fixture=fixture,
    )
    sys.stdout.buffer.write(render_materialization_summary_v1(summary))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
