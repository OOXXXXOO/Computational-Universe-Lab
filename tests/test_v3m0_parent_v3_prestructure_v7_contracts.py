"""Static v7 delta contracts for Parent-v3 prestructure and B3/B6 joins.

The tests parse only the design erratum and existing source text.  They do not
import any future B3/B6 production module and cannot mint a capability.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-prestructure-production-chain-v7-2026-08-02.md"
)
BASE_CONTRACT_PATH = (
    REPO_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md"
)
BEGIN_MARKER = "<!-- BEGIN V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->"
END_MARKER = "<!-- END V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->"
BASE_BEGIN_MARKER = "<!-- BEGIN V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->"
BASE_END_MARKER = "<!-- END V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->"
BASE_CONTRACT_RAW_SHA256 = (
    "fd654e76ea143503916b45e1eec6456eab3f014e1e8ba02b826f6c62bb42e91f"
)
EXPECTED_REGISTRY_GOLDEN_SHA256 = (
    "a3a506a5b3ddbf245332fe3dc28f848af3db02f24e31cfd1d2b6f43e46d437e3"
)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _registry_source() -> str:
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    assert text.count(BEGIN_MARKER) == 1
    assert text.count(END_MARKER) == 1
    payload = text.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("\n```")
    return payload.removeprefix("```json\n").removesuffix("\n```")


def _load_registry() -> dict[str, object]:
    value = json.loads(
        _registry_source(),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {value}")
        ),
    )
    assert type(value) is dict
    return value


def _load_base_registry() -> dict[str, object]:
    text = BASE_CONTRACT_PATH.read_text(encoding="utf-8")
    assert text.count(BASE_BEGIN_MARKER) == 1
    assert text.count(BASE_END_MARKER) == 1
    payload = text.split(BASE_BEGIN_MARKER, 1)[1].split(BASE_END_MARKER, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("\n```")
    value = json.loads(
        payload.removeprefix("```json\n").removesuffix("\n```"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    assert type(value) is dict
    return value


def _freeze_ordered_json(value: object) -> object:
    if type(value) is dict:
        return tuple((key, _freeze_ordered_json(item)) for key, item in value.items())
    if type(value) is list:
        return tuple(_freeze_ordered_json(item) for item in value)
    return value


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def _apply_effective_merge(
    base: dict[str, object], merge: dict[str, object]
) -> dict[str, object]:
    effective = copy.deepcopy(base)
    for override in merge["json_pointer_overrides"]:
        assert set(override) == {
            "json_pointer",
            "operation",
            "expected_v6_value",
            "replacement_value",
        }
        assert override["operation"] == "REPLACE_EXACT"
        parent, leaf = _json_pointer_parent(effective, override["json_pointer"])
        assert parent[leaf] == override["expected_v6_value"]
        parent[leaf] = copy.deepcopy(override["replacement_value"])
    return effective


def _field_names(record: dict[str, object]) -> list[str]:
    return [field["name"] for field in record["field_specs"]]


def _field(record: dict[str, object], name: str) -> dict[str, object]:
    return next(field for field in record["field_specs"] if field["name"] == name)


def _assert_exact_field_specs(record: dict[str, object]) -> None:
    assert set(record) == {
        "operation",
        "schema_id",
        "canonical_owner",
        "field_specs",
        "record_invariants",
    }
    assert record["operation"] in {"ADD_V7_RECORD", "REPLACE_V6_RECORD"}
    assert type(record["field_specs"]) is list and record["field_specs"]
    assert type(record["record_invariants"]) is list
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
        }
        names.append(spec["name"])
        assert spec["presence"] in {"required", "required-nullable"}
        assert type(spec["literal_domain"]) is list
        assert type(spec["constraints"]) is list
        cardinality = spec["tuple_cardinality"]
        if cardinality is not None:
            assert set(cardinality) == {"kind", "value"}
            assert cardinality["kind"] in {
                "exact",
                "nonempty",
                "derived",
                "bounded",
            }
    assert len(names) == len(set(names))


def _class_fields(path: Path, class_name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.ClassDef) and item.name == class_name
    )
    return [
        item.target.id
        for item in node.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    ]


def _function_parameters(path: Path, function_name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        item
        for item in tree.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == function_name
    )
    return tuple(
        argument.arg
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
    )


def _module_all(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    )
    value = ast.literal_eval(assignment.value)
    assert type(value) is list and all(type(item) is str for item in value)
    return tuple(value)


def test_v7_registry_is_strict_design_only_delta_over_immutable_v6() -> None:
    registry = _load_registry()

    assert registry["registry_schema_version"] == (
        "v3m0.parent-v3-prestructure-production-chain-delta.v7"
    )
    assert registry["document_authority"] == "DESIGN_ONLY_NO_AUTHORITY"
    assert registry["production_status"] == "EXPECTED-MISSING_AT_V7_FREEZE"
    assert registry["issued_statuses"] == []
    assert registry["threshold_values"] == {}
    assert registry["threshold_policy"] == ("REFERENCE_EXISTING_FROZEN_VALUES_ONLY")
    assert list(registry) == [
        "registry_schema_version",
        "document_authority",
        "production_status",
        "issued_statuses",
        "threshold_values",
        "threshold_policy",
        "base_contract",
        "effective_merge",
        "record_catalog_delta",
        "dynamics_certificate_v3_field_replacement",
        "private_capabilities",
        "private_apis",
        "public_api_freeze",
        "dynamics_shared_core",
        "legacy_transition_registry_policy",
        "owner_neutral_judge_cores",
        "b6_upstream_private_views",
        "fresh_b2_child_semantics",
        "b6_upstream_atomic_precondition",
        "runtime_v3_private_authority",
        "legacy_delegation_and_regression_locks",
        "task_delta",
        "typed_failure_routing",
        "b6_typed_failure_routing",
        "attack_matrix",
        "b6_attack_matrix",
        "import_dag_delta",
        "legacy_immutability",
    ]

    base = registry["base_contract"]
    assert base == {
        "path": (
            "docsv3/v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md"
        ),
        "registry_schema_version": ("v3m0.parent-v3-downstream-contract-registry.v6"),
        "raw_sha256": BASE_CONTRACT_RAW_SHA256,
        "mutation_allowed": False,
        "delta_scope": [
            "Parent-v3 application prestructure ownership",
            "B3 transition measurement seam and recursive wire",
            "B6 prestructure field and live authority joins",
            "B3/B6 import DAG correction",
            "B6 owner-neutral judge seams and legacy delegation locks",
            "B4/B5 private live views and fresh B2 child semantics",
            "parallel private V3 runtime authority",
            "B6 upstream atomic precondition and effective outcome failure order",
        ],
    }
    assert hashlib.sha256(BASE_CONTRACT_PATH.read_bytes()).hexdigest() == (
        BASE_CONTRACT_RAW_SHA256
    )


def test_v7_effective_merge_exactly_replaces_only_the_two_b6_conflicts() -> None:
    registry = _load_registry()
    old_failures = [
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
    effective_failures = [
        "reality_invalid",
        "laurent_resource_exceeded",
        "certified_instability_counterwitness",
        "structure_raw_unresolved",
        "metric_raw_unresolved",
        "spectral_coverage_unresolved",
        "normalized_metric_unresolved",
        "full_state_bridge_failed",
        "power_drift_unresolved",
    ]
    old_invariant = "failure order is exactly DynamicsCertificationFailure enum order"
    effective_invariant = (
        "DynamicsCertificationFailure declaration order is wire compatibility "
        "only; prestructure_invalid and transition_invalid are nonissuable "
        "upstream typed raises, while issuable outcome first-failure execution "
        "follows the v7 failure contract"
    )
    merge = registry["effective_merge"]
    assert merge == {
        "algorithm": (
            "COPY_V6_THEN_APPLY_EXACT_JSON_POINTER_REPLACEMENTS_THEN_ADD_V7_DELTA"
        ),
        "unlisted_v6_mutation_allowed": False,
        "v7_delta_additions_apply_after_overrides": True,
        "json_pointer_overrides": [
            {
                "json_pointer": "/tasks/B6/invariants/0",
                "operation": "REPLACE_EXACT",
                "expected_v6_value": old_invariant,
                "replacement_value": effective_invariant,
            },
            {
                "json_pointer": "/tasks/B6/typed_failures",
                "operation": "REPLACE_EXACT",
                "expected_v6_value": old_failures,
                "replacement_value": effective_failures,
            },
        ],
    }

    base = _load_base_registry()
    effective = _apply_effective_merge(base, merge)
    assert effective["tasks"]["B6"]["invariants"][0] == effective_invariant
    assert effective["tasks"]["B6"]["typed_failures"] == effective_failures

    restored = copy.deepcopy(effective)
    for override in merge["json_pointer_overrides"]:
        parent, leaf = _json_pointer_parent(restored, override["json_pointer"])
        parent[leaf] = copy.deepcopy(override["expected_v6_value"])
    assert restored == base
    assert (
        effective["enum_catalog"]["DynamicsCertificationFailure"]
        == (base["enum_catalog"]["DynamicsCertificationFailure"])
    )


def test_v7_registry_has_independent_full_ordered_json_golden() -> None:
    registry = _load_registry()
    golden = _canonical_digest(_freeze_ordered_json(registry))
    assert golden == EXPECTED_REGISTRY_GOLDEN_SHA256

    hostile = copy.deepcopy(registry)
    hostile["dynamics_shared_core"]["semantics"][0] = "accept caller supplied projector"
    assert _canonical_digest(_freeze_ordered_json(hostile)) != golden


def test_parent_v3_application_prestructure_is_full_exact_owner_record() -> None:
    registry = _load_registry()
    catalog = registry["record_catalog_delta"]
    assert list(catalog) == [
        "ParentV3ApplicationPrestructure",
        "TransitionAuthorityV3",
    ]
    for record in catalog.values():
        _assert_exact_field_specs(record)

    record = catalog["ParentV3ApplicationPrestructure"]
    assert record["operation"] == "ADD_V7_RECORD"
    assert record["schema_id"] == ("v3m0.parent-v3-application-prestructure.v1")
    assert record["canonical_owner"] == (
        "rulespace_v3.parent_v3_application_prestructure"
    )
    assert _field_names(record) == [
        "prestructure_schema_version",
        "parent_freeze_v3_sha",
        "permit_sha",
        "materialization_sha",
        "current_application_authority_v3_sha",
        "current_scenario_authority_v3_sha",
        "current_scenario_response_contract_v3_sha",
        "factory_binding",
        "factory_sha",
        "factory_role",
        "ablation_pair_snapshot",
        "basis_contract",
        "evidence_lane",
        "target_spec_sha",
        "state_schema_id",
        "channel_order",
        "canonical_channel_pairs",
        "fourier_adjoint_convention_id",
        "structure_form",
        "reality_convention_id",
        "prestructure_authority_sha",
    ]
    assert _field(record, "prestructure_schema_version")["literal_domain"] == [
        "v3m0.parent-v3-application-prestructure.v1"
    ]
    assert _field(record, "factory_role")["literal_domain"] == [
        "actual",
        "matched_ablated",
    ]
    assert _field(record, "evidence_lane")["literal_domain"] == ["synthetic-classical"]
    assert _field(record, "fourier_adjoint_convention_id")["literal_domain"] == [
        "minus-k-transpose-v1"
    ]
    assert _field(record, "reality_convention_id")["literal_domain"] == [
        "real-kernel-positive-zero-v1"
    ]

    nested = {
        "factory_binding": "FactoryBranchBindingV3",
        "ablation_pair_snapshot": "AblationPairSnapshot",
        "basis_contract": "C19BasisContractV2",
        "structure_form": "FrozenComplexTensor",
    }
    for field_name, nested_record in nested.items():
        spec = _field(record, field_name)
        assert spec["nested_record"] == nested_record
        assert "full recursive raw body" in spec["constraints"]
    assert _field(record, "channel_order")["tuple_cardinality"] == {
        "kind": "exact",
        "value": 20,
    }
    assert _field(record, "canonical_channel_pairs")["tuple_cardinality"] == {
        "kind": "exact",
        "value": 10,
    }
    assert record["record_invariants"] == [
        "issued only from one exact live Parent-v3 plus one exact live B2 materialization and one frozen factory role",
        "all Parent, permit, materialization, application, scenario, response, branch and factory roots rejoin exactly",
        "factory_binding is the full selected B2 branch body and its branch/factory/root equal the direct fields",
        "ablation_pair_snapshot and basis_contract are the exact full bodies already nested in the same materialization",
        "state schema is v3m0.c19-real-canonical-state.v2; channel_order is exact q0,p0 through q9,p9 and spatial shape remains (8,) in the bound factory",
        "canonical_channel_pairs are the ten adjacent q/p pairs and structure_form is the exact derived 20x20 canonical block-J",
        "no caller supplies a prestructure body, structure form, basis, pair snapshot, factory or SHA",
        "prestructure_authority_sha is SHA-256 of the complete canonical body excluding only itself",
    ]


def test_transition_authority_v3_now_recursively_carries_prestructure() -> None:
    registry = _load_registry()
    record = registry["record_catalog_delta"]["TransitionAuthorityV3"]

    assert record["operation"] == "REPLACE_V6_RECORD"
    assert record["schema_id"] == "v3m0.transition-authority.v3"
    assert record["canonical_owner"] == "rulespace_v3.transition_authority_v3"
    assert _field_names(record) == [
        "transition_authority_schema_version",
        "materialization",
        "factory_binding",
        "prestructure_authority",
        "measured_transition",
        "transition_authority_sha",
    ]
    prestructure = _field(record, "prestructure_authority")
    assert prestructure["wire_type"] == "ParentV3ApplicationPrestructure"
    assert prestructure["nested_record"] == "ParentV3ApplicationPrestructure"
    assert prestructure["constraints"] == ["full recursive raw body"]
    assert record["record_invariants"] == [
        "materialization, factory_binding and prestructure_authority are full recursive raw bodies from one live B2 branch",
        "measured_transition.prestructure_authority_sha equals prestructure_authority.prestructure_authority_sha exactly",
        "factory binding branch/factory/root equals prestructure and measured transition branch/factory/root",
        "verification reconstructs the prestructure and remeasures every full-state impulse; self hashes alone never hydrate authority",
    ]


def test_private_prestructure_capability_and_views_are_exact_and_not_public() -> None:
    registry = _load_registry()
    capabilities = registry["private_capabilities"]
    assert list(capabilities) == [
        "VerifiedParentV3ApplicationPrestructure",
        "VerifiedTransitionAuthorityV3",
    ]
    assert capabilities["VerifiedParentV3ApplicationPrestructure"] == {
        "canonical_owner": "rulespace_v3.parent_v3_application_prestructure",
        "raw_body": "ParentV3ApplicationPrestructure",
        "constructibility": "owner-token-only-live-identity-registry",
        "exported_publicly": False,
        "required_b2_owner_seam": (
            "rulespace_v3.application_materialization_v3."
            "_require_v3m0_application_scenario_materialization_v3_for_parent"
        ),
        "raw_verification_policy": (
            "raw body is comparison evidence only; exact live Parent-v3 and "
            "materialization are mandatory and the B2 owner seam is replayed "
            "before owner registration"
        ),
        "private_view": {
            "name": "_VerifiedParentV3ApplicationPrestructureView",
            "fields": [
                {
                    "name": "prestructure",
                    "wire_type": "ParentV3ApplicationPrestructure",
                },
                {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
                {
                    "name": "materialization",
                    "wire_type": ("VerifiedV3M0ApplicationScenarioMaterializationV3"),
                },
                {"name": "factory", "wire_type": "VerifiedFactory"},
                {
                    "name": "factory_binding",
                    "wire_type": "FactoryBranchBindingV3",
                },
            ],
        },
    }
    assert capabilities["VerifiedTransitionAuthorityV3"] == {
        "canonical_owner": "rulespace_v3.transition_authority_v3",
        "raw_body": "TransitionAuthorityV3",
        "constructibility": "owner-token-only-live-identity-registry",
        "exported_publicly": True,
        "required_prestructure_reverifier": (
            "rulespace_v3.parent_v3_application_prestructure."
            "_reverify_verified_parent_v3_application_prestructure"
        ),
        "private_view": {
            "name": "_VerifiedTransitionAuthorityV3View",
            "fields": [
                {
                    "name": "transition_authority",
                    "wire_type": "TransitionAuthorityV3",
                },
                {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
                {
                    "name": "materialization",
                    "wire_type": ("VerifiedV3M0ApplicationScenarioMaterializationV3"),
                },
                {"name": "factory", "wire_type": "VerifiedFactory"},
                {
                    "name": "prestructure",
                    "wire_type": "VerifiedParentV3ApplicationPrestructure",
                },
            ],
        },
    }

    assert registry["private_apis"] == [
        {
            "owner": "rulespace_v3.parent_v3_application_prestructure",
            "name": "_issue_parent_v3_application_prestructure",
            "args": [
                {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
                {
                    "name": "materialization",
                    "wire_type": ("VerifiedV3M0ApplicationScenarioMaterializationV3"),
                },
                {
                    "name": "factory_role",
                    "wire_type": "Literal[actual,matched_ablated]",
                },
            ],
            "returns": "VerifiedParentV3ApplicationPrestructure",
            "raw_hydration_allowed": False,
        },
        {
            "owner": "rulespace_v3.parent_v3_application_prestructure",
            "name": "_verify_parent_v3_application_prestructure",
            "args": [
                {
                    "name": "prestructure",
                    "wire_type": "ParentV3ApplicationPrestructure",
                },
                {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
                {
                    "name": "materialization",
                    "wire_type": ("VerifiedV3M0ApplicationScenarioMaterializationV3"),
                },
            ],
            "returns": "VerifiedParentV3ApplicationPrestructure",
            "raw_hydration_allowed": False,
        },
        {
            "owner": "rulespace_v3.parent_v3_application_prestructure",
            "name": "_reverify_verified_parent_v3_application_prestructure",
            "args": [
                {
                    "name": "prestructure",
                    "wire_type": "VerifiedParentV3ApplicationPrestructure",
                }
            ],
            "returns": "_VerifiedParentV3ApplicationPrestructureView",
            "raw_hydration_allowed": False,
        },
        {
            "owner": "rulespace_v3.transition_authority_v3",
            "name": "_reverify_verified_transition_authority_v3",
            "args": [
                {
                    "name": "transition",
                    "wire_type": "VerifiedTransitionAuthorityV3",
                }
            ],
            "returns": "_VerifiedTransitionAuthorityV3View",
            "raw_hydration_allowed": False,
        },
    ]


def test_b3_file_boundary_public_api_and_shared_dynamics_core_are_exact() -> None:
    registry = _load_registry()
    b3 = registry["task_delta"]["B3"]

    assert b3["file_boundary"] == {
        "create": [
            "rulespace_v3/parent_v3_application_prestructure.py",
            "tests/test_v3m0_parent_v3_application_prestructure.py",
            "rulespace_v3/transition_authority_v3.py",
            "tests/test_v3m0_transition_authority_v3.py",
        ],
        "modify": [
            "rulespace_v3/dynamics.py",
            "tests/test_v3m0_dynamics.py",
        ],
    }
    assert b3["owned_records"] == [
        "ParentV3ApplicationPrestructure",
        "MeasuredTransition",
        "TransitionAuthorityV3",
    ]
    assert b3["public_opaque_wrappers"] == ["VerifiedTransitionAuthorityV3"]
    assert b3["owner_internal_opaque_wrappers"] == [
        "VerifiedParentV3ApplicationPrestructure"
    ]
    assert b3["public_apis"] == registry["public_api_freeze"]["B3"]
    assert [api["name"] for api in b3["public_apis"]] == [
        "issue_transition_authority_v3",
        "verify_transition_authority_v3",
        "verify_transition_pair_v3",
    ]
    assert all(api["raw_hydration_allowed"] is False for api in b3["public_apis"])

    core = registry["dynamics_shared_core"]
    assert core["owner"] == "rulespace_v3.dynamics"
    assert core["name"] == "_measure_bound_realspace_transition"
    assert core["visibility"] == "owner-internal"
    assert core["signature"] == {
        "args": [
            {"name": "factory", "wire_type": "VerifiedFactory"},
            {"name": "parent_freeze_sha", "wire_type": "sha256"},
            {"name": "prestructure_authority_sha", "wire_type": "sha256"},
        ],
        "keyword_only_after": "factory",
        "returns": "MeasuredTransition",
    }
    assert core["delegates"] == [
        "rulespace_v3.dynamics._remeasure_transition",
        "rulespace_v3.transition_authority_v3 B3 measurement route",
    ]
    assert core["semantics"] == [
        "reverify the exact live VerifiedFactory and derive role/state/channel/shape/dt/boundary from its immutable body",
        "derive canonical signed support from factory_support_offsets(factory,1), enforce no wrap, sorted uniqueness and bit-exact +0.0 outside support",
        "rerun one periodic real-space unit impulse for every full state channel at the canonical origin",
        "freeze the complete (n_state,n_state,*spatial_shape) complex128 kernel and macro_steps=1",
        "accept no caller kernel, support, state schema, channel order, spatial shape, dt, boundary, basis, grid, FFT, per-k projector or analytic substitute",
    ]
    assert core["legacy_delegate_order"] == (
        "legacy _remeasure_transition first performs its unchanged "
        "VerifiedFactory/VerifiedPrestructureAuthority join, then delegates once"
    )
    assert core["v3_delegate_order"] == (
        "B3 first reverifies Parent-v3/B2/new prestructure branch join, then "
        "delegates once"
    )


def test_b6_field_replacement_preserves_same_full_live_prestructure() -> None:
    registry = _load_registry()
    replacement = registry["dynamics_certificate_v3_field_replacement"]
    assert replacement == {
        "record": "DynamicsCertificateV3",
        "field": "prestructure_authority",
        "operation": "REPLACE_V6_FIELD_TYPE",
        "old_wire_type": "PrestructureAuthority",
        "old_nested_record": "PrestructureAuthority",
        "new_wire_type": "ParentV3ApplicationPrestructure",
        "new_nested_record": "ParentV3ApplicationPrestructure",
        "presence": "required",
        "constraints": [
            "full recursive raw body",
            "exactly equals transition_authority.prestructure_authority",
            "obtained from the same live VerifiedParentV3ApplicationPrestructure stored by VerifiedTransitionAuthorityV3",
            "B6 must not reconstruct, adapt or independently hash a prestructure",
        ],
    }
    b6 = registry["task_delta"]["B6"]
    assert b6["record_field_replacements"] == [
        "DynamicsCertificateV3.prestructure_authority: PrestructureAuthority -> ParentV3ApplicationPrestructure"
    ]
    assert b6["consume_private_api"] == (
        "rulespace_v3.transition_authority_v3."
        "_reverify_verified_transition_authority_v3"
    )
    assert b6["consume_private_view_field"] == "prestructure"
    assert b6["same_live_parent_materialization_prestructure_identity_required"] is True
    assert b6["factory_wrapper_identity_required"] is False
    assert b6["copy_or_rederive_algorithm_allowed"] is False
    assert b6["legacy_opaque_use_allowed"] is False
    assert b6["caller_runtime_allowed"] is False
    assert b6["metric_origin_binding"] == (
        "MetricOriginManifest.derivation_or_preregistration_sha == "
        "MetricSignedSupportAttestationV1.metric_support_protocol_sha"
    )
    assert b6["file_boundary"] == {
        "create": [
            "rulespace_v3/certificate_v3.py",
            "tests/test_v3m0_certificate_v3.py",
        ],
        "modify": [
            "rulespace_v3/structure.py",
            "tests/test_v3m0_structure.py",
            "rulespace_v3/metric.py",
            "tests/test_v3m0_metric.py",
            "rulespace_v3/bridge.py",
            "tests/test_v3m0_bridge.py",
            "rulespace_v3/laurent.py",
            "tests/test_v3m0_laurent.py",
            "rulespace_v3/spectral.py",
            "tests/test_v3m0_spectral.py",
            "tests/test_v3m0_spectral_nonzero.py",
            "rulespace_v3/runtime.py",
            "tests/test_v3m0_runtime.py",
            "rulespace_v3/certificate.py",
            "tests/test_v3m0_certificate.py",
        ],
    }
    assert b6["consume_private_apis"] == [
        "rulespace_v3.transition_authority_v3._reverify_verified_transition_authority_v3",
        "rulespace_v3.metric_support_authority_v1._reverify_verified_metric_signed_support_attestation_v1",
        "rulespace_v3.runtime_grids_v3._reverify_verified_bridge_grid_authority_v3",
        "rulespace_v3.runtime_grids_v3._reverify_verified_dynamics_grid_authority_v3",
        "rulespace_v3.runtime._issue_runtime_evidence_manifest_v3",
        "rulespace_v3.runtime._verify_runtime_evidence_manifest_v3",
    ]
    assert b6["owner_neutral_core_names"] == [
        "_build_bound_synthetic_structure_manifest",
        "_build_reality_certificate_from_raw",
        "_build_bound_synthetic_identity_metric",
        "_build_bound_full_state_bridge_spec",
        "_audit_full_state_bridge_from_raw",
        "_preflight_laurent_resources_from_raw",
        "_build_laurent_residual_from_raw",
        "_build_spectral_margin_coverage_from_raw",
        "_build_normalized_metric_residual_audit_from_raw",
        "_build_power_drift_audit_from_raw",
    ]
    assert b6["exact_joins"] == [
        "certificate.prestructure_authority == certificate.transition_authority.prestructure_authority",
        "certificate.prestructure_authority.prestructure_authority_sha == certificate.transition_authority.measured_transition.prestructure_authority_sha",
        "live transition view prestructure raw body == certificate.prestructure_authority",
        "Parent/materialization/prestructure capability identities agree; fresh factory wrappers may differ but exact factory bodies, bindings, roles and SHAs agree",
        "metric attestation, bridge grid and dynamics grid live views share the same Parent/materialization/branch identities",
        "bridge spec grid equals the live BridgeGridAuthorityV3.bridge_grid body",
        "spectral qualification and diagnostic grids equal the live DynamicsGridAuthorityV3.dynamics_grid body",
    ]


def test_v7_forbids_legacy_transition_registry_and_freezes_neutral_cores() -> None:
    registry = _load_registry()
    assert registry["legacy_transition_registry_policy"] == {
        "decision": ("FORBID_V3_REGISTRATION_IN_LEGACY_VERIFIED_TRANSITION_REGISTRY"),
        "legacy_registry_record": ("rulespace_v3.dynamics._TransitionAuthority"),
        "legacy_prestructure_type": "VerifiedPrestructureAuthority",
        "generalized_union_or_callback_registry_allowed": False,
        "required_v3_route": (
            "B3 owns VerifiedTransitionAuthorityV3; B6 consumes its raw "
            "MeasuredTransition only after the V3 private reverifier succeeds"
        ),
        "reasons": [
            "legacy registration and replay are identity-bound to VerifiedPrestructureAuthority",
            "legacy structure, metric, Laurent, spectral and normalized replay dereference the legacy prestructure",
            "sharing numerical cores must not broaden the authority accepted by VerifiedTransition",
        ],
    }

    catalog = registry["owner_neutral_judge_cores"]
    assert catalog["policy"] == {
        "visibility": "private-not-in-__all__",
        "authority_precondition": (
            "legacy callers complete their old live joins and B6 completes all "
            "V3 live joins before entering a neutral core"
        ),
        "candidate_verification": (
            "reconstruct the expected raw record from live-derived inputs and "
            "require exact record equality; never trust a self-hash alone"
        ),
        "caller_raw_entry_allowed": False,
        "algorithm_copy_allowed": False,
        "forbidden_owner_imports": [
            "rulespace_v3.parent_v3_application_prestructure",
            "rulespace_v3.transition_authority_v3",
            "rulespace_v3.certificate_v3",
        ],
    }
    cores = catalog["cores"]
    assert [(item["owner"], item["name"]) for item in cores] == [
        (
            "rulespace_v3.structure",
            "_build_bound_synthetic_structure_manifest",
        ),
        (
            "rulespace_v3.structure",
            "_build_reality_certificate_from_raw",
        ),
        (
            "rulespace_v3.metric",
            "_build_bound_synthetic_identity_metric",
        ),
        (
            "rulespace_v3.bridge",
            "_build_bound_full_state_bridge_spec",
        ),
        (
            "rulespace_v3.bridge",
            "_audit_full_state_bridge_from_raw",
        ),
        (
            "rulespace_v3.laurent",
            "_preflight_laurent_resources_from_raw",
        ),
        (
            "rulespace_v3.laurent",
            "_build_laurent_residual_from_raw",
        ),
        (
            "rulespace_v3.spectral",
            "_build_spectral_margin_coverage_from_raw",
        ),
        (
            "rulespace_v3.spectral",
            "_build_normalized_metric_residual_audit_from_raw",
        ),
        (
            "rulespace_v3.spectral",
            "_build_power_drift_audit_from_raw",
        ),
    ]
    expected_signatures = {
        "_build_bound_synthetic_structure_manifest": (
            ("structure_form", "FrozenComplexTensor"),
            ("target_spec_sha", "sha256"),
            ("state_schema_id", "str"),
            ("channel_order", "tuple[str,...]"),
            (
                "canonical_channel_pairs",
                "tuple[tuple[str,str],...]",
            ),
            ("prestructure_authority_sha", "sha256"),
            "structure_form",
            "StructureManifest",
        ),
        "_build_reality_certificate_from_raw": (
            ("factory", "VerifiedFactory"),
            ("transition", "MeasuredTransition"),
            ("structure", "StructureManifest"),
            None,
            "RealityCertificate",
        ),
        "_build_bound_synthetic_identity_metric": (
            ("factory", "VerifiedFactory"),
            ("structure", "StructureManifest"),
            ("state_metric", "FrozenComplexTensor"),
            ("parent_freeze_sha", "sha256"),
            ("prestructure_authority_sha", "sha256"),
            ("derivation_or_preregistration_sha", "sha256"),
            (
                "metric_support_offsets",
                "tuple[tuple[int,...],...]",
            ),
            "state_metric",
            "StabilityMetricWitness",
        ),
        "_build_bound_full_state_bridge_spec": (
            ("factory", "VerifiedFactory"),
            ("bridge_grid", "BridgeKGridManifest"),
            ("parent_freeze_sha", "sha256"),
            ("prestructure_authority_sha", "sha256"),
            "bridge_grid",
            "FullStateBridgeSpec",
        ),
        "_audit_full_state_bridge_from_raw": (
            ("transition", "MeasuredTransition"),
            ("factory", "VerifiedFactory"),
            ("spec", "FullStateBridgeSpec"),
            None,
            "BridgeAudit",
        ),
        "_preflight_laurent_resources_from_raw": (
            ("transition", "MeasuredTransition"),
            ("stability_metric", "StabilityMetricWitness"),
            None,
            "None",
        ),
        "_build_laurent_residual_from_raw": (
            ("transition", "MeasuredTransition"),
            ("structure", "StructureManifest"),
            ("metric", "StabilityMetricWitness"),
            ("protocol", "Fp64EnclosureProtocol"),
            (
                "kind",
                "Literal[canonical-structure,stability-metric]",
            ),
            "protocol",
            "LaurentResidualCertificate",
        ),
        "_build_spectral_margin_coverage_from_raw": (
            ("transition", "MeasuredTransition"),
            ("stability_metric", "StabilityMetricWitness"),
            ("fp64_protocol", "Fp64EnclosureProtocol"),
            ("dynamics_grid", "DynamicsKGridManifest"),
            "fp64_protocol",
            "SpectralMarginCoverage",
        ),
        "_build_normalized_metric_residual_audit_from_raw": (
            ("metric_residual", "LaurentResidualCertificate"),
            ("spectral_margins", "SpectralMarginCoverage"),
            None,
            "NormalizedMetricResidualAudit",
        ),
        "_build_power_drift_audit_from_raw": (
            ("normalized", "NormalizedMetricResidualAudit"),
            None,
            "PowerDriftAudit",
        ),
    }
    for core in cores:
        signature = core["signature"]
        flattened = tuple(
            (argument["name"], argument["wire_type"]) for argument in signature["args"]
        ) + (
            signature["keyword_only_after"],
            signature["returns"],
        )
        assert flattened == expected_signatures[core["name"]]
        assert core["visibility"] == "private-not-in-__all__"
        assert core["legacy_delegate"]
        assert core["b6_consumer"] == "rulespace_v3.certificate_v3"
        assert not any(
            forbidden in json.dumps(core)
            for forbidden in (
                'VerifiedTransition"',
                "VerifiedPrestructureAuthority",
            )
        )

    assert catalog["already_owner_neutral_reuse"] == [
        {
            "owner": "rulespace_v3.dynamics",
            "name": "_transition_symbol_from_raw",
            "consumed_by": ["rulespace_v3.bridge"],
        },
        {
            "owner": "rulespace_v3.instability",
            "name": "_build_instability_growth_counter_witness_from_raw",
            "consumed_by": ["rulespace_v3.certificate_v3"],
        },
        {
            "owner": "rulespace_v3.instability",
            "name": "verify_instability_growth_counter_witness_arithmetic",
            "consumed_by": ["rulespace_v3.certificate_v3"],
        },
        {
            "owner": "rulespace_v3.fp64_protocol",
            "name": "build_fp64_enclosure_protocol",
            "consumed_by": ["rulespace_v3.certificate_v3"],
        },
        {
            "owner": "rulespace_v3.fp64_protocol",
            "name": "verify_fp64_enclosure_protocol",
            "consumed_by": ["rulespace_v3.certificate_v3"],
        },
        {
            "owner": "rulespace_v3.fp64",
            "name": "compute_power_drift_bounds",
            "consumed_by": ["rulespace_v3.spectral"],
        },
    ]


def test_fresh_b2_children_and_b6_upstream_precondition_are_closed() -> None:
    registry = _load_registry()
    assert registry["fresh_b2_child_semantics"] == {
        "b2_owner_seam": (
            "rulespace_v3.application_materialization_v3."
            "_require_v3m0_application_scenario_materialization_v3_for_parent"
        ),
        "replay_may_remint_factory_wrapper": True,
        "factory_wrapper_identity_comparison_allowed": False,
        "required_factory_equivalence": [
            "exact VerifiedFactory.factory raw body equality",
            "exact FactoryBranchBindingV3 equality",
            "exact branch role and factory SHA equality",
        ],
        "same_live_identity_scope": [
            "VerifiedParentFreezeV3",
            "VerifiedV3M0ApplicationScenarioMaterializationV3",
            "VerifiedParentV3ApplicationPrestructure",
        ],
        "operation_contracts": [
            "issue_transition_authority_v3 saves the B2 owner-seam child and compares only frozen factory equivalence",
            "verify_transition_authority_v3 replays B2, saves the fresh child and compares only frozen factory equivalence",
            "_reverify_verified_transition_authority_v3 returns the fresh child and preserves live Parent/materialization/prestructure identity",
            "verify_transition_pair_v3 permits distinct fresh factory wrappers while requiring exact body/binding/role/SHA joins",
            "all three B6 public APIs permit distinct fresh factory wrappers while requiring exact body/binding/role/SHA joins",
        ],
    }

    precondition = registry["b6_upstream_atomic_precondition"]
    assert precondition == {
        "position": "BEFORE_ATTEMPT_AUDIT_OR_OUTCOME_CONSTRUCTION",
        "scope": "INPUT_CAPABILITY_VALIDITY_AND_CROSS_AUTHORITY_JOIN_ONLY",
        "applies_to": [
            "certify_transition_dynamics_v3",
            "verify_dynamics_certificate_v3",
            "verify_dynamics_certification_outcome_v3",
        ],
        "required_live_authorities": [
            "VerifiedParentFreezeV3",
            "VerifiedV3M0ApplicationScenarioMaterializationV3",
            "VerifiedTransitionAuthorityV3",
            "VerifiedMetricSignedSupportAttestationV1",
            "VerifiedBridgeGridAuthorityV3",
            "VerifiedDynamicsGridAuthorityV3",
        ],
        "attempt_sha_fields_populated_only_after_join": [
            "parent_freeze_v3_sha",
            "materialization_sha",
            "transition_authority_sha",
            "metric_attestation_sha",
            "bridge_grid_authority_sha",
            "dynamics_grid_authority_sha",
        ],
        "typed_exception": {
            "name": "DynamicsCertificationUpstreamJoinFailure",
            "reason_id_field": "reason_id",
            "detail_field": "detail",
            "reason_id_domain": [
                "PARENT_INVALID",
                "MATERIALIZATION_INVALID",
                "PRESTRUCTURE_INVALID",
                "TRANSITION_INVALID",
                "METRIC_ATTESTATION_INVALID",
                "BRIDGE_GRID_INVALID",
                "DYNAMICS_GRID_INVALID",
                "CROSS_AUTHORITY_JOIN",
            ],
            "exported_in___all__": True,
        },
        "atomic_join_rules": [
            "reverify all six live upstream authorities before reading roots into an attempt audit",
            "reverify the nested Parent-v3 application prestructure through the transition private view",
            "join Parent/materialization/prestructure by live identity and factory branches by exact body/binding/role/SHA equivalence",
            "any invalid, dead, forged, tampered or cross-authority input raises one typed upstream join failure",
        ],
        "valid_join_does_not_prejudge_derived_scientific_evidence": True,
        "derived_judge_failures_after_valid_join": [
            "metric_raw_unresolved",
            "spectral_coverage_unresolved",
            "full_state_bridge_failed",
        ],
        "no_artifact_on_failure": [
            "DynamicsCertificationAttemptAuditV3",
            "DynamicsCertificationOutcomeV3",
            "DynamicsCertificateV3",
            "VerifiedDynamicsCertificationOutcomeV3",
            "VerifiedDynamicsCertificateV3",
        ],
        "opaque_registry_side_effect_allowed": False,
        "wire_only_nonissuable_failure_enum_values": [
            "prestructure_invalid",
            "transition_invalid",
        ],
        "issuable_outcome_failure_enum_values": [
            "reality_invalid",
            "laurent_resource_exceeded",
            "certified_instability_counterwitness",
            "structure_raw_unresolved",
            "metric_raw_unresolved",
            "spectral_coverage_unresolved",
            "normalized_metric_unresolved",
            "full_state_bridge_failed",
            "power_drift_unresolved",
        ],
        "enum_catalog_mutation_allowed": False,
    }

    base = _load_base_registry()
    attempt_fields = _field_names(
        base["record_catalog"]["DynamicsCertificationAttemptAuditV3"]
    )
    assert all(
        field in attempt_fields
        for field in precondition["attempt_sha_fields_populated_only_after_join"]
    )
    assert "attempt_sha" in attempt_fields
    assert (
        "attempt_sha"
        not in precondition["attempt_sha_fields_populated_only_after_join"]
    )
    base_enum = base["enum_catalog"]["DynamicsCertificationFailure"]
    assert set(precondition["wire_only_nonissuable_failure_enum_values"]) < set(
        base_enum
    )
    assert set(precondition["wire_only_nonissuable_failure_enum_values"]) | set(
        precondition["issuable_outcome_failure_enum_values"]
    ) == set(base_enum)


def test_b6_private_views_and_runtime_authority_are_closed() -> None:
    registry = _load_registry()
    assert registry["b6_upstream_private_views"] == [
        {
            "owner": "rulespace_v3.transition_authority_v3",
            "name": "_reverify_verified_transition_authority_v3",
            "input": "VerifiedTransitionAuthorityV3",
            "returns": "_VerifiedTransitionAuthorityV3View",
            "required_fields": [
                "transition_authority",
                "parent",
                "materialization",
                "factory",
                "prestructure",
            ],
            "exported_in___all__": False,
        },
        {
            "owner": "rulespace_v3.metric_support_authority_v1",
            "name": ("_reverify_verified_metric_signed_support_attestation_v1"),
            "input": "VerifiedMetricSignedSupportAttestationV1",
            "returns": "_VerifiedMetricSupportAttestationV1View",
            "required_fields": [
                "attestation",
                "parent",
                "materialization",
                "factory",
                "factory_binding",
            ],
            "exported_in___all__": False,
        },
        {
            "owner": "rulespace_v3.runtime_grids_v3",
            "name": "_reverify_verified_bridge_grid_authority_v3",
            "input": "VerifiedBridgeGridAuthorityV3",
            "returns": "_VerifiedBridgeGridAuthorityV3View",
            "required_fields": [
                "grid_authority",
                "parent",
                "materialization",
                "factory",
                "factory_binding",
            ],
            "exported_in___all__": False,
        },
        {
            "owner": "rulespace_v3.runtime_grids_v3",
            "name": "_reverify_verified_dynamics_grid_authority_v3",
            "input": "VerifiedDynamicsGridAuthorityV3",
            "returns": "_VerifiedDynamicsGridAuthorityV3View",
            "required_fields": [
                "grid_authority",
                "parent",
                "transition",
                "metric_attestation",
            ],
            "exported_in___all__": False,
        },
    ]

    runtime = registry["runtime_v3_private_authority"]
    assert runtime["owner"] == "rulespace_v3.runtime"
    assert runtime["raw_record"] == "RuntimeEvidenceManifest"
    assert runtime["raw_record_schema"] == ("v3m0.runtime-evidence-manifest.v1")
    assert runtime["authority_symbol"] == "_V3_RUNTIME_AUTHORITY"
    assert runtime["evaluator_id"] == (
        "rulespace-v3m0-parent-v3-certificate-closure-v1"
    )
    assert runtime["fresh_process_import_roots"] == ["rulespace_v3.certificate_v3"]
    assert runtime["transitive_loaded_module_inventory"] is True
    assert runtime["caller_import_roots_allowed"] is False
    assert runtime["caller_runtime_manifest_allowed"] is False
    assert runtime["private_apis_exported_in___all__"] is False
    assert runtime["private_apis"] == [
        {
            "name": "_runtime_evidence_manifest_v3_payload",
            "args": [{"name": "manifest", "wire_type": "RuntimeEvidenceManifest"}],
            "returns": "dict[str,object]",
        },
        {
            "name": "_issue_runtime_evidence_manifest_v3",
            "args": [],
            "returns": "RuntimeEvidenceManifest",
        },
        {
            "name": "_verify_runtime_evidence_manifest_v3",
            "args": [{"name": "manifest", "wire_type": "RuntimeEvidenceManifest"}],
            "returns": "RuntimeEvidenceManifest",
        },
    ]
    assert runtime["legacy_public_authority_unchanged"] == {
        "evaluator_id": "rulespace-v3m0-certificate-closure-v1",
        "public_apis": [
            "runtime_evidence_manifest_payload",
            "issue_runtime_evidence_manifest",
            "verify_runtime_evidence_manifest",
        ],
        "import_roots": [
            "rulespace_v3.bridge",
            "rulespace_v3.certificate",
            "rulespace_v3.dynamics",
            "rulespace_v3.fp64_protocol",
            "rulespace_v3.grids",
            "rulespace_v3.instability",
            "rulespace_v3.laurent",
            "rulespace_v3.metric",
            "rulespace_v3.parent_freeze",
            "rulespace_v3.prestructure",
            "rulespace_v3.qualification",
            "rulespace_v3.registry",
            "rulespace_v3.runtime",
            "rulespace_v3.spectral",
            "rulespace_v3.structure",
        ],
        "wire_evaluator_roots_inventory_and_hash_algorithm_bit_identity_required": True,
        "same_source_snapshot_manifest_determinism_required": True,
        "historical_manifest_value_persistence_across_source_edits": False,
        "historical_manifest_after_source_edit": ("MUST_FAIL_FRESH_REVERIFICATION"),
    }


def test_v7_freezes_legacy_delegation_and_b6_failure_attack_contracts() -> None:
    registry = _load_registry()
    locks = registry["legacy_delegation_and_regression_locks"]
    assert locks["global_invariants"] == [
        "legacy public signatures, __all__, exact authority types and wire schemas do not change",
        "every legacy wrapper completes its original live authority join before one neutral-core call",
        "legacy reconstructed raw records and every recursive SHA remain byte-identical",
        "neutral cores are closure-captured or otherwise protected from public-global redirect",
        "V3 code never mints or accepts legacy VerifiedTransition or VerifiedPrestructureAuthority",
    ]
    assert locks["delegation_map"] == [
        {
            "owner": "rulespace_v3.dynamics",
            "legacy_functions": ["_remeasure_transition"],
            "neutral_cores": ["_measure_bound_realspace_transition"],
        },
        {
            "owner": "rulespace_v3.structure",
            "legacy_functions": ["_expected_structure", "_expected_reality"],
            "neutral_cores": [
                "_build_bound_synthetic_structure_manifest",
                "_build_reality_certificate_from_raw",
            ],
        },
        {
            "owner": "rulespace_v3.metric",
            "legacy_functions": ["_expected_metric"],
            "neutral_cores": ["_build_bound_synthetic_identity_metric"],
        },
        {
            "owner": "rulespace_v3.bridge",
            "legacy_functions": ["_expected_spec", "_expected_audit"],
            "neutral_cores": [
                "_build_bound_full_state_bridge_spec",
                "_audit_full_state_bridge_from_raw",
            ],
        },
        {
            "owner": "rulespace_v3.laurent",
            "legacy_functions": ["_build_residual"],
            "neutral_cores": ["_build_laurent_residual_from_raw"],
        },
        {
            "owner": "rulespace_v3.certificate",
            "legacy_functions": ["_preflight_laurent_resources"],
            "neutral_cores": ["_preflight_laurent_resources_from_raw"],
        },
        {
            "owner": "rulespace_v3.spectral",
            "legacy_functions": [
                "_expected_exact_zero_coverage",
                "_expected_nonzero_coverage",
                "_expected_normalized_audit",
                "_expected_power_drift_audit",
            ],
            "neutral_cores": [
                "_build_spectral_margin_coverage_from_raw",
                "_build_normalized_metric_residual_audit_from_raw",
                "_build_power_drift_audit_from_raw",
            ],
        },
    ]
    assert locks["required_tests"] == [
        "legacy output record and SHA golden equality before versus after extraction",
        "legacy public signature and __all__ snapshot",
        "old live join happens before the neutral core and the core is called exactly once",
        "forged/dead/tampered old opaque rejection remains unchanged",
        "post-freeze global redirect cannot bypass a captured authority or neutral core",
        "legacy runtime wire, evaluator, roots, inventory rules and hash algorithm stay bit-identical",
        "the same source snapshot reproduces the same manifest; any source edit invalidates the historical manifest",
    ]

    routing = registry["b6_typed_failure_routing"]
    assert [item["failure"] for item in routing] == [
        "prestructure_invalid",
        "transition_invalid",
        "reality_invalid",
        "laurent_resource_exceeded",
        "certified_instability_counterwitness",
        "structure_raw_unresolved",
        "metric_raw_unresolved",
        "spectral_coverage_unresolved",
        "normalized_metric_unresolved",
        "full_state_bridge_failed",
        "power_drift_unresolved",
    ]
    assert [item["execution_index"] for item in routing[:2]] == [None, None]
    assert [item["execution_index"] for item in routing[2:]] == list(range(9))
    base_enum = _load_base_registry()["enum_catalog"]["DynamicsCertificationFailure"]
    assert [item["enum_declaration_index"] for item in routing] == [
        base_enum.index(item["failure"]) for item in routing
    ]
    assert [
        item["failure"]
        for item in sorted(routing, key=lambda item: item["enum_declaration_index"])
    ] == base_enum
    assert [item["route_kind"] for item in routing[:2]] == [
        "UPSTREAM_PRECONDITION_TYPED_RAISE_NO_OUTCOME",
        "UPSTREAM_PRECONDITION_TYPED_RAISE_NO_OUTCOME",
    ]
    assert [item["outcome_issuable"] for item in routing[:2]] == [False, False]
    assert [item["typed_exception_reason_id"] for item in routing[:2]] == [
        "PRESTRUCTURE_INVALID",
        "TRANSITION_INVALID",
    ]
    assert all(item["route_kind"] == "OUTCOME_FIRST_FAILURE" for item in routing[2:])
    assert all(item["outcome_issuable"] is True for item in routing[2:])
    assert all(item["judge_owner"] for item in routing)
    assert all(item["required_attack_classes"] for item in routing)
    instability = routing[4]
    assert instability["evidence"] == "InstabilityGrowthCounterWitness"
    assert instability["status_semantics"] == "UNSTABLE"
    assert instability["exact_profile_only"] == ("exact-zero-offset-jordan-2x2-v1")
    assert registry["task_delta"]["B6"]["failure_contract"] == {
        "enum_values_and_declaration_order_unchanged": True,
        "wire_only_nonissuable_values": [
            "prestructure_invalid",
            "transition_invalid",
        ],
        "execution_order": [item["failure"] for item in routing[2:]],
        "v6_ambiguity_resolution": (
            "the enum declaration order is a wire/API freeze; upstream join "
            "failures raise before outcome construction, and issuable "
            "first-failure execution keeps the Jordan check after Laurent "
            "preflight and before structure/metric judges"
        ),
        "runtime_or_fp64_infrastructure_failure": (
            "raise without issuing a scientific outcome or certificate"
        ),
    }
    assert registry["b6_attack_matrix"] == [
        "legacy VerifiedFactory, VerifiedPrestructureAuthority, VerifiedTransition or VerifiedNormalizedMetricResidualAudit",
        "caller raw prestructure, transition, structure, metric, grid, fp64, bridge, Laurent, spectral, normalized, power or runtime body",
        "raw/dead/forged/equal-copy/tampered Parent-v3, materialization, transition, metric or grid capability",
        "cross-parent, cross-materialization, cross-branch, role swap, duplicate branch or half-pair splice",
        "self-resigned nested Parent, prestructure, transition, attestation, grid or evidence body",
        "bridge and dynamics grid swap, caller points, or grid body differing from its live authority",
        "metric protocol, I20 body, origin support, protocol SHA or metric-origin binding drift",
        "legacy transition-registry injection, union registration or replay-callback substitution",
        "analytic, FFT, reduced-state, per-k projector or caller kernel substitute",
        "old normalized opaque injection or duplicated Laurent, spectral, normalized or power algorithm",
        "V3 runtime evaluator id, import roots, transitive source closure, environment or manifest SHA drift",
        "success/failure XOR violation, non-prefix attempt evidence or evidence from an unreached stage",
        "non-Jordan, approximate-Jordan, wrong-support or self-resigned instability witness",
        "public-function global redirect, private-view bypass or owner-registry bypass",
    ]


def test_typed_failure_routes_and_hostile_inputs_are_closed() -> None:
    registry = _load_registry()
    assert registry["task_delta"]["B3"]["typed_failures"] == [
        "MATERIALIZATION_INVALID",
        "PRESTRUCTURE_INVALID",
        "EXECUTOR_FAILED",
        "TRANSITION_MEASUREMENT_FAILED",
        "SUPPORT_INVALID",
        "BRANCH_JOIN_FAILED",
        "CROSS_PARENT_ROOT",
    ]
    assert registry["typed_failure_routing"] == [
        {
            "reason_id": "MATERIALIZATION_INVALID",
            "required_attack_classes": [
                "raw/dead/forged/equal-copy materialization",
                "materialization replay failure",
            ],
        },
        {
            "reason_id": "PRESTRUCTURE_INVALID",
            "required_attack_classes": [
                "raw/dead/forged/tampered new prestructure",
                "pair/basis/block-J/self-hash drift",
            ],
        },
        {
            "reason_id": "EXECUTOR_FAILED",
            "required_attack_classes": [
                "factory executor exception",
                "executor dtype/shape/non-finite drift",
            ],
        },
        {
            "reason_id": "TRANSITION_MEASUREMENT_FAILED",
            "required_attack_classes": [
                "kernel or transition self-hash tamper",
                "raw transition differs from fresh full-state remeasurement",
            ],
        },
        {
            "reason_id": "SUPPORT_INVALID",
            "required_attack_classes": [
                "support sort/uniqueness/sign/no-wrap drift",
                "non-positive-zero coefficient outside declared support",
            ],
        },
        {
            "reason_id": "BRANCH_JOIN_FAILED",
            "required_attack_classes": [
                "factory role/SHA/binding/prestructure/transition mismatch",
                "actual-matched swap, duplicate or cross-pair splice",
            ],
        },
        {
            "reason_id": "CROSS_PARENT_ROOT",
            "required_attack_classes": [
                "different live Parent-v3 identity",
                "parent root splice anywhere in recursive bodies",
            ],
        },
    ]
    assert registry["attack_matrix"] == [
        "legacy VerifiedPrestructureAuthority and PrestructureAuthority v1",
        "legacy VerifiedTransition and naked MeasuredTransition",
        "historical Parent-v1/v2 or current raw Parent-v3",
        "raw/forged/dead/equal-copy B2 materialization",
        "raw/forged/dead/tampered ParentV3ApplicationPrestructure",
        "caller factory, pair snapshot, basis, structure form or any SHA",
        "caller kernel, support, state/grid/dt/boundary/macro-step",
        "analytic, FFT, reduced-state or per-k projector measurement",
        "self-resigned recursive body mutation",
        "actual/matched swap, duplicate, half-pair or cross-pair splice",
        "cross-parent identity or root splice",
        "forged/dead/tampered VerifiedTransitionAuthorityV3",
        "public-function global redirect or owner-registry bypass",
    ]


def test_v1_wires_and_public_dynamics_prestructure_apis_are_immutable() -> None:
    registry = _load_registry()
    legacy = registry["legacy_immutability"]
    assert legacy == {
        "prestructure_v1_record_schema": "v3m0.prestructure-authority.v1",
        "prestructure_v1_record_fields": [
            "authority_schema_version",
            "authority_kind",
            "parent_freeze",
            "factory_sha",
            "factory_role",
            "ablation_pair_snapshot",
            "ablation_manifest_sha",
            "ablation_construction_sha",
            "synthetic_registry",
            "synthetic_registry_entry_sha",
            "synthetic_preregistration",
            "synthetic_application_spec",
            "synthetic_application_scenario_spec",
            "synthetic_application_permit_sha",
            "synthetic_scenario_construction_sha",
            "adapter_preregistration",
            "authority_sha",
        ],
        "measured_transition_schema": "v3m0.measured-transition.v1",
        "measured_transition_fields": [
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
        ],
        "dynamics_public_signatures": [
            "measure_transition(factory,authority)",
            "verify_measured_transition(transition,factory,authority)",
            "transition_kernel_array(transition)",
            "transition_symbol(transition,momentum)",
        ],
        "prestructure_public_issuers_unchanged": [
            "issue_synthetic_prestructure_authority",
            "verify_synthetic_prestructure_authority",
            "issue_v3m0_application_prestructure_authority",
        ],
        "legacy_wire_mutation_allowed": False,
        "legacy_public_api_mutation_allowed": False,
        "new_private_core_exported_in_dynamics_all": False,
    }

    prestructure_path = REPO_ROOT / "rulespace_v3" / "prestructure.py"
    dynamics_path = REPO_ROOT / "rulespace_v3" / "dynamics.py"
    assert (
        _class_fields(prestructure_path, "PrestructureAuthority")
        == (legacy["prestructure_v1_record_fields"])
    )
    assert (
        _class_fields(dynamics_path, "MeasuredTransition")
        == (legacy["measured_transition_fields"])
    )
    assert _function_parameters(dynamics_path, "measure_transition") == (
        "factory",
        "authority",
    )
    assert _function_parameters(dynamics_path, "verify_measured_transition") == (
        "transition",
        "factory",
        "authority",
    )
    assert _function_parameters(dynamics_path, "transition_kernel_array") == (
        "transition",
    )
    assert _function_parameters(dynamics_path, "transition_symbol") == (
        "transition",
        "momentum",
    )
    dynamics_all = _module_all(dynamics_path)
    prestructure_all = _module_all(prestructure_path)
    assert "_measure_bound_realspace_transition" not in dynamics_all
    assert set(legacy["prestructure_public_issuers_unchanged"]) <= set(prestructure_all)


def test_v7_import_dag_delta_is_exact_acyclic_and_drops_legacy_adapter_edge() -> None:
    registry = _load_registry()
    delta = registry["import_dag_delta"]
    assert delta["nodes"] == {
        "rulespace_v3.parent_v3_application_prestructure": [
            "rulespace_v3.application_materialization_v3",
            "rulespace_v3.evidence",
            "rulespace_v3.factory",
        ],
        "rulespace_v3.transition_authority_v3": [
            "rulespace_v3.application_materialization_v3",
            "rulespace_v3.dynamics",
            "rulespace_v3.evidence",
            "rulespace_v3.parent_v3_application_prestructure",
        ],
        "rulespace_v3.certificate_v3": [
            "rulespace_v3.application_materialization_v3",
            "rulespace_v3.transition_authority_v3",
            "rulespace_v3.parent_v3_application_prestructure",
            "rulespace_v3.metric_support_authority_v1",
            "rulespace_v3.runtime_grids_v3",
            "rulespace_v3.certificate",
            "rulespace_v3.dynamics",
            "rulespace_v3.structure",
            "rulespace_v3.metric",
            "rulespace_v3.bridge",
            "rulespace_v3.instability",
            "rulespace_v3.laurent",
            "rulespace_v3.spectral",
            "rulespace_v3.fp64_protocol",
            "rulespace_v3.runtime",
        ],
    }
    assert delta["external_or_preexisting_leaves"] == [
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.bridge",
        "rulespace_v3.certificate",
        "rulespace_v3.dynamics",
        "rulespace_v3.evidence",
        "rulespace_v3.factory",
        "rulespace_v3.fp64_protocol",
        "rulespace_v3.instability",
        "rulespace_v3.laurent",
        "rulespace_v3.metric",
        "rulespace_v3.metric_support_authority_v1",
        "rulespace_v3.runtime",
        "rulespace_v3.runtime_grids_v3",
        "rulespace_v3.spectral",
        "rulespace_v3.structure",
    ]
    assert delta["forbidden_edges"] == [
        [
            "rulespace_v3.parent_v3_application_prestructure",
            "rulespace_v3.prestructure",
        ],
        [
            "rulespace_v3.transition_authority_v3",
            "rulespace_v3.prestructure",
        ],
        [
            "rulespace_v3.transition_authority_v3",
            "rulespace_v3.parent_authority_v3",
        ],
        [
            "rulespace_v3.certificate_v3",
            "rulespace_v3.prestructure",
        ],
        [
            "rulespace_v3.parent_v3_application_prestructure",
            "rulespace_v3.transition_authority_v3",
        ],
    ]
    assert delta["fresh_process_probe_edges"] == [
        [
            "rulespace_v3.runtime._V3_RUNTIME_AUTHORITY",
            "rulespace_v3.certificate_v3",
        ]
    ]
    assert delta["fresh_process_probe_edge_policy"] == (
        "SUBPROCESS_IMPORT_ROOT_NOT_A_STATIC_PARENT_IMPORT_EDGE"
    )
    assert delta["cycle_policy"] == "STRICT_DIRECT_DAG_NO_TRANSITIVE_BACK_EDGE"

    nodes = delta["nodes"]
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise AssertionError(f"v7 import cycle at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dependency in nodes.get(node, []):
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for module_name in nodes:
        visit(module_name)
    for source, target in delta["forbidden_edges"]:
        assert target not in nodes.get(source, [])

    # Prove the delta in its real context, not only as an isolated subgraph:
    # replace the two v6 nodes, add the new owner, and traverse the complete
    # immutable v6 graph including runtime-grids and downstream consumers.
    base = _load_base_registry()
    baseline = base["import_dag"]
    assert set(nodes) == {
        "rulespace_v3.parent_v3_application_prestructure",
        "rulespace_v3.transition_authority_v3",
        "rulespace_v3.certificate_v3",
    }
    assert (
        "rulespace_v3.prestructure" in baseline["rulespace_v3.transition_authority_v3"]
    )
    assert "rulespace_v3.parent_v3_application_prestructure" not in baseline
    assert (
        "rulespace_v3.parent_v3_application_prestructure"
        not in baseline["rulespace_v3.certificate_v3"]
    )
    combined = copy.deepcopy(baseline)
    combined.update(copy.deepcopy(nodes))
    assert all(
        combined[module_name] == dependencies
        for module_name, dependencies in baseline.items()
        if module_name not in nodes
    )
    for module_name, dependencies in nodes.items():
        assert combined[module_name] == dependencies
    assert (
        "rulespace_v3.prestructure"
        not in combined["rulespace_v3.transition_authority_v3"]
    )
    known = (
        set(combined)
        | set(base["import_dag_external_leaves"])
        | set(delta["external_or_preexisting_leaves"])
    )
    assert all(
        dependency in known
        for dependencies in combined.values()
        for dependency in dependencies
    )
    combined_visiting: set[str] = set()
    combined_visited: set[str] = set()

    def visit_combined(node: str) -> None:
        if node in combined_visiting:
            raise AssertionError(f"combined v6+v7 import cycle at {node}")
        if node in combined_visited:
            return
        combined_visiting.add(node)
        for dependency in combined.get(node, []):
            visit_combined(dependency)
        combined_visiting.remove(node)
        combined_visited.add(node)

    for module_name in combined:
        visit_combined(module_name)


def test_strict_json_loader_rejects_duplicate_keys_and_nonfinite_constants() -> None:
    source = _registry_source()
    assert json.loads(source, object_pairs_hook=_reject_duplicate_keys)

    duplicate = source.replace(
        '{\n  "registry_schema_version":',
        '{\n  "registry_schema_version": "forged",\n  "registry_schema_version":',
        1,
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        json.loads(duplicate, object_pairs_hook=_reject_duplicate_keys)

    nonfinite = source.replace(
        '"threshold_values": {}',
        '"threshold_values": {"forged": NaN}',
        1,
    )
    with pytest.raises(ValueError, match="non-finite JSON constant"):
        json.loads(
            nonfinite,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant: {value}")
            ),
        )


def test_static_v7_contract_test_imports_no_future_production_module() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    assert not any(
        name.startswith(
            (
                "rulespace_v3.parent_v3_application_prestructure",
                "rulespace_v3.transition_authority_v3",
                "rulespace_v3.certificate_v3",
            )
        )
        for name in imported
    )
