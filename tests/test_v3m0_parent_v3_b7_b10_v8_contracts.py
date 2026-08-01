"""Static v8 contracts for the Parent-v3 B7--B10 correction.

The tests parse design registries and already-existing legacy source only.  They
never import a future B7--B10 production owner and therefore cannot mint a
capability or issue a scientific status.
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
    / "v3-设计勘误-Parent-v3-B7至B10-production-chain-v8-2026-08-02.md"
)
V6_PATH = (
    REPO_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md"
)
V7_PATH = (
    REPO_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-prestructure-production-chain-v7-2026-08-02.md"
)
REPRESENTATION_PLAN_PATH = (
    REPO_ROOT / "docsv3" / "v3-实施计划-V3M0-双轴仪器迁移-2026-07-30.md"
)
BEGIN = "<!-- BEGIN V3M0_PARENT_V3_B7_B10_V8_REGISTRY -->"
END = "<!-- END V3M0_PARENT_V3_B7_B10_V8_REGISTRY -->"
V6_BEGIN = "<!-- BEGIN V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->"
V6_END = "<!-- END V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->"
V7_BEGIN = "<!-- BEGIN V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->"
V7_END = "<!-- END V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->"

V6_RAW_SHA256 = "fd654e76ea143503916b45e1eec6456eab3f014e1e8ba02b826f6c62bb42e91f"
V7_RAW_SHA256 = "a6b83b08b57bccf09fd78e95a1a63d2c0b49339cb29dbd6e6ff07cb19eb512f4"
V7_ORDERED_REGISTRY_SHA256 = (
    "a3a506a5b3ddbf245332fe3dc28f848af3db02f24e31cfd1d2b6f43e46d437e3"
)
REPRESENTATION_PLAN_RAW_SHA256 = (
    "32a9061bac1ac7bdfb0f0014de3dea55f8ca6113a806380906b594ff6a4b0f8f"
)
# Filled only after an intentional v8 registry freeze.
V8_ORDERED_REGISTRY_SHA256 = (
    "bb0e34718b371e10d8bd83cb2306905d5b0445480c3b9df7ebcc3f83f879c3a8"
)

PRIOR_REPLACEMENT_DIGESTS = {
    "/tasks/B7": "b396dc45bb86169acb6b151121cb348c5fa238fe84f029f533eead22d9bce889",
    "/tasks/B8": "6475b432586f5005db39aec5a9ffd3f6c0e9f5747bd9f3b52c88caad246366ea",
    "/tasks/B9": "2eb7d289814c18fe5995c93af737094701da02be5e25a591fbc4c78873c6ef5c",
    "/tasks/B10": "36e6a047871756ad1bf7914c7838a13f58406d1f2459e236120af29908711f0d",
    "/response_chain": "fa61d146dd1c109298d98e3c3288ff272ddfce97619f439f851ae926c459b6f9",
    "/v3m0_execution_freeze": "a70936651013fe540edf9b85ffa3aeef3d17f971a885b548862e3d3d16f25701",
    "/portable_trust_anchor_freeze": "5445833689c834a18b59b26028efe6c87126fd51e84742febc2d1f170b09ac82",
    "/portable_verifier_freeze": "6b7ad28f7d188776a8b5efe5b487da1b2e5c4c7714cd6cac61f483cd14d661bf",
    "/record_catalog/PairedFilteredResponse": "ed85b802e254f380ee0bdb9fa826f2d9492d530c9a321c418556fee35a456bef",
    "/record_catalog/PairedResponseAttemptAudit": "08fb7f525c12486915f3b27f19d5b637e33528085a9782116b26666b0a47caf3",
    "/record_catalog/ClosedControlApplicationEvidenceV3": "1e602171fe0411a3803721d20d927cad4d2d397bc6df08cb8cdc76a10ed0773f",
    "/record_catalog/ClosedControlApplicationEvidenceOutcomeV3": "d340e6947ca1ac7d50991309d5d433d2a201311d60a62f657f1621b953b654d7",
    "/record_catalog/GeometryPrerequisiteObservationV3": "84f9c52b146b4317abbbcf3eaac7ad025302b123638e1ba4c61ea17a8541dbd8",
    "/record_catalog/GeometryPrerequisiteEvaluationV3": "783f3de7edb634549e48da6b3a9e70a4073de39b73ab0821450094881614a3cd",
    "/record_catalog/C19ControlGeometryEvaluationV3": "3005839f8dd9321b96c39c9190432f5bb6573320d554c4b817218820d32aebf1",
    "/record_catalog/ResponseBlockAttemptOutcome": "7061014da440bde8c0026eebd5ae4884b3020fbfa8ca208ea34e2a3acccd5c47",
    "/record_catalog/ParentV3ScenarioReplayAuthorityV1": "d7c8aaa39f94728d4508db2b846df6b46aa4fa5bb45314b5a1b9c8719ac5fe91",
    "/record_catalog/ApplicationScenarioExecutionSpec/record_invariants/0": "f21cbe232196b45d425e438286dfce03cb510aa093aa33c2efc955e7631567af",
    "/record_catalog/V3M0ScenarioEvidenceItemV3": "017963c1e6b3cb9cc88fa2ffebc6ecc08573bdbe20e2fb3928ae0b0156d616d1",
    "/record_catalog/V3M0ControlsResultV3": "60c36659e6f00dec39c8093ec4bfdc43b5cd4eb4835bda95e7b23b42a5d4a801",
    "/record_catalog/V3M0ResponseResultV3": "2dc143ed9fd870a11108a46cdaa6646ac1eda65ff103692c891a6ab3f3249fd8",
    "/record_catalog/RepresentationInvariantOutcomeV3": "28ab702aa427a141b06893a6dee8ffd9f08c20502d6c8a590e7773d9af51d5db",
    "/record_catalog/V3M0InstrumentResultV3": "6a23c37916b845c2be0927bb2cc5dadaf38f6f003687bd4ac498a84dbc6b6139",
    "/record_catalog/V3M0RunOutcomeV3": "00b2634890efe0761444d13170a0fcc2b554976a76e066cada98d21b966698f8",
    "/record_catalog/V3M0RunManifestV3": "153c5f36842223e0bd11b7fe1248fb0f4b38242a61e5ac67f74c1cc7d9627b96",
    "/record_catalog/V3M0CheckpointEnvelopeV1": "63ccde047385f0339105137f7f5bccd6215e45066e3dc03f182e31af95065621",
}

SCENARIO_ORDER = (
    "v3m0.synthetic-control.c01.v1.scenario.holdout-span.v1",
    "v3m0.synthetic-control.c02.v1.scenario.conditioned-zero.v1",
    "v3m0.synthetic-control.c03.v1.scenario.equal-rank-direct-sum.v1",
    "v3m0.synthetic-control.c04.v1.scenario.canonical-angle.v1",
    "v3m0.synthetic-control.c05.v1.scenario.phase.v1",
    "v3m0.synthetic-control.c05.v1.scenario.gain.v1",
    "v3m0.synthetic-control.c06.v1.scenario.nonscale-mixing.v1",
    "v3m0.synthetic-control.c07.v1.scenario.interference.v1",
    "v3m0.synthetic-control.c08.v1.scenario.rank-missing.v1",
    "v3m0.synthetic-control.c09.v1.scenario.gauge-dressing.v1",
    "v3m0.synthetic-control.c10.v1.scenario.extra-mode.v1",
    "v3m0.synthetic-control.c11.v1.scenario.null.v1",
    "v3m0.synthetic-control.c11.v1.scenario.grey.v1",
    "v3m0.synthetic-control.c11.v1.scenario.signal.v1",
    "v3m0.synthetic-control.c12.v1.scenario.ir-normalization.v1",
    "v3m0.synthetic-control.c13.v1.scenario.both-zero.v1",
    "v3m0.synthetic-control.c14.v1.scenario.endpoint-ambiguous.v1",
    "v3m0.synthetic-control.c14.v1.scenario.response-null.v1",
    "v3m0.synthetic-control.c14.v1.scenario.trace-unclassified.v1",
    "v3m0.synthetic-control.c14.v1.scenario.unstable.v1",
    "v3m0.synthetic-control.c15.v1.scenario.full-h.v1",
    "v3m0.synthetic-control.c15.v1.scenario.low-rank-tt.v1",
    "v3m0.synthetic-control.c15.v1.scenario.tt.v1",
    "v3m0.synthetic-control.c15.v1.scenario.tt-plus-row.v1",
    "v3m0.synthetic-control.c16.v1.scenario.coverage-low.v1",
    "v3m0.synthetic-control.c16.v1.scenario.coverage-high.v1",
    "v3m0.synthetic-control.c17.v1.scenario.quotient-gauge.v1",
    "v3m0.synthetic-control.c18.v1.scenario.independent-unary.v1",
    "v3m0.synthetic-control.c19.v2.scenario.observer-collapse.v2",
    "v3m0.synthetic-control.c20.v1.scenario.clean-zero.v1",
    "v3m0.synthetic-control.c20.v1.scenario.true-floor.v1",
)

INVARIANT_IDS = (
    "I01_LAYER_SPLIT_MERGE",
    "I02_INSERT_S_SINV",
    "I03_COMMUTING_LAYER_REORDER",
    "I04_Q_LABEL_PERMUTATION",
    "I05_SOURCE_ISOMETRY",
    "I06_READOUT_ISOMETRY",
    "I07_PHASE_NONZERO_SCALAR",
    "I08_COVARIANT_CANONICAL_CHANGE",
    "I09_NO_WRAP_VOLUME_CHANGE",
)

CURRENT_C19_SCENARIO_ID = "v3m0.synthetic-control.c19.v2.scenario.observer-collapse.v2"

GEOMETRY_PREDICATE_IDS = (
    "complete-nonzero-gram-support-selection",
    "whitened-coisometry-or-incidence-range-preservation",
    "incidence-rank-six",
    "gauge-contained-in-incidence-kernel-dimension-four",
    "tt2-gauge4-row4-pairwise-orthogonal-complete-decomposition",
    "constraint-kernel-tt-plus-gauge-compatible-projector-and-metric",
    "actual-source-readout-share-endpoint-shell-and-finite-paired-response",
)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _registry_source(path: Path, begin: str, end: str) -> str:
    text = path.read_text(encoding="utf-8")
    assert text.count(begin) == 1
    assert text.count(end) == 1
    payload = text.split(begin, 1)[1].split(end, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("\n```")
    return payload.removeprefix("```json\n").removesuffix("\n```")


def _load(path: Path, begin: str, end: str) -> dict[str, object]:
    value = json.loads(
        _registry_source(path, begin, end),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {value}")
        ),
    )
    assert type(value) is dict
    return value


def _v8() -> dict[str, object]:
    return _load(CONTRACT_PATH, BEGIN, END)


def _v6() -> dict[str, object]:
    return _load(V6_PATH, V6_BEGIN, V6_END)


def _v7() -> dict[str, object]:
    return _load(V7_PATH, V7_BEGIN, V7_END)


def _freeze_ordered_json(value: object) -> object:
    if type(value) is dict:
        return tuple((key, _freeze_ordered_json(item)) for key, item in value.items())
    if type(value) is list:
        return tuple(_freeze_ordered_json(item) for item in value)
    return value


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _get(document: object, pointer: str) -> object:
    assert pointer.startswith("/")
    current = document
    for raw in pointer.removeprefix("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if type(current) is dict:
            current = current[token]
        else:
            assert type(current) is list
            current = current[int(token)]
    return current


def _apply_relative_patches(
    value: dict[str, object], patches: list[dict[str, object]]
) -> dict[str, object]:
    result = copy.deepcopy(value)
    for patch in patches:
        assert set(patch) == {
            "relative_pointer",
            "expected_prior_value",
            "replacement_value",
        }
        tokens = patch["relative_pointer"].removeprefix("/").split("/")
        parent: object = result
        for token in tokens[:-1]:
            parent = parent[int(token)] if type(parent) is list else parent[token]
        leaf = int(tokens[-1]) if type(parent) is list else tokens[-1]
        assert parent[leaf] == patch["expected_prior_value"]
        parent[leaf] = copy.deepcopy(patch["replacement_value"])
    return result


def _record(registry: dict[str, object], name: str) -> dict[str, object]:
    return registry["record_catalog_delta"][name]


def _field_names(record: dict[str, object]) -> list[str]:
    return [field["name"] for field in record["field_specs"]]


def _field(record: dict[str, object], name: str) -> dict[str, object]:
    return next(item for item in record["field_specs"] if item["name"] == name)


def _api(task: dict[str, object], name: str) -> dict[str, object]:
    return next(item for item in task["apis"] if item["name"] == name)


def _class_annotations(path: Path, name: str) -> list[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.ClassDef) and item.name == name
    )
    return [
        (item.target.id, ast.unparse(item.annotation))
        for item in node.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    ]


def _assert_acyclic(nodes: dict[str, list[str]], known_leaves: set[str]) -> None:
    assert all(
        dep in nodes or dep in known_leaves for deps in nodes.values() for dep in deps
    )
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node: str) -> None:
        if node in permanent:
            return
        assert node not in temporary, f"cycle at {node}"
        temporary.add(node)
        for dependency in nodes.get(node, []):
            if dependency in nodes:
                visit(dependency)
        temporary.remove(node)
        permanent.add(node)

    for node in nodes:
        visit(node)


def _assert_current_c19_v2_identity(registry: dict[str, object]) -> None:
    freeze = registry["v3m0_execution_freeze_delta"]
    identity = freeze["current_c19_identity"]
    scenario_id = freeze["scenario_order"][28]
    assert freeze["block_success_route_tags"] == [
        "INHERITED_PARENT_V3",
        "CURRENT_C19",
    ]
    assert scenario_id == identity["scenario_id"]
    assert scenario_id != identity["forbidden_legacy_scenario_id"]
    assert identity["application_instance_id"] == "v3m0.synthetic-control.c19.v2"
    assert registry["geometry_predicate_freeze"]["legacy_v1_scenario_allowed"] is False


def test_v8_registry_is_strict_design_only_delta_over_pinned_v6_v7() -> None:
    registry = _v8()

    assert hashlib.sha256(V6_PATH.read_bytes()).hexdigest() == V6_RAW_SHA256
    assert hashlib.sha256(V7_PATH.read_bytes()).hexdigest() == V7_RAW_SHA256
    assert _digest(_freeze_ordered_json(_v7())) == V7_ORDERED_REGISTRY_SHA256
    assert registry["registry_schema_version"] == (
        "v3m0.parent-v3-b7-b10-production-chain-delta.v8"
    )
    assert registry["document_authority"] == "DESIGN_ONLY_NO_AUTHORITY"
    assert registry["production_status"] == "EXPECTED-MISSING_AT_V8_FREEZE"
    assert registry["issued_statuses"] == []
    assert registry["threshold_values"] == {}
    assert registry["threshold_policy"] == "REFERENCE_EXISTING_FROZEN_VALUES_ONLY"
    assert registry["base_contracts"] == {
        "v6": {
            "path": V6_PATH.relative_to(REPO_ROOT).as_posix(),
            "registry_schema_version": "v3m0.parent-v3-downstream-contract-registry.v6",
            "raw_sha256": V6_RAW_SHA256,
        },
        "v7": {
            "path": V7_PATH.relative_to(REPO_ROOT).as_posix(),
            "registry_schema_version": (
                "v3m0.parent-v3-prestructure-production-chain-delta.v7"
            ),
            "raw_sha256": V7_RAW_SHA256,
            "ordered_registry_sha256": V7_ORDERED_REGISTRY_SHA256,
        },
    }
    assert list(registry) == [
        "registry_schema_version",
        "document_authority",
        "production_status",
        "issued_statuses",
        "threshold_values",
        "threshold_policy",
        "base_contracts",
        "effective_merge",
        "record_wire_schema",
        "enum_catalog_delta",
        "legacy_record_repairs",
        "record_catalog_delta",
        "b6_outcome_lineage_seam",
        "task_delta",
        "response_chain_delta",
        "geometry_predicate_freeze",
        "v3m0_execution_freeze_delta",
        "state_resolver_binding",
        "portable_trust_anchor_freeze_delta",
        "portable_verifier_freeze_delta",
        "neutral_core_and_legacy_locks",
        "import_dag_delta",
        "preservation_freeze",
        "attack_matrix",
        "implementation_order",
        "explicit_non_goals",
    ]


def test_v8_effective_operations_pin_every_replaced_prior_value() -> None:
    registry = _v8()
    base = _v6()
    merge = registry["effective_merge"]

    assert merge["algorithm"] == (
        "VERIFY_V6_AND_V7_THEN_MATERIALIZE_EFFECTIVE_V7_AND_APPLY_ORDERED_V8"
    )
    assert merge["unlisted_prior_mutation_allowed"] is False
    replacements = merge["replace_exact_sha256"]
    assert [item["json_pointer"] for item in replacements] == list(
        PRIOR_REPLACEMENT_DIGESTS
    )
    for item in replacements:
        assert set(item) == {
            "json_pointer",
            "operation",
            "expected_prior_value_sha256",
            "replacement_ref",
        }
        assert item["operation"] == "REPLACE_EXACT_SHA256"
        pointer = item["json_pointer"]
        assert item["expected_prior_value_sha256"] == PRIOR_REPLACEMENT_DIGESTS[pointer]
        assert (
            _digest(_freeze_ordered_json(_get(base, pointer)))
            == item["expected_prior_value_sha256"]
        )
        assert _get(registry, item["replacement_ref"])

    additions = merge["add_absent"]
    added_names = [item["json_pointer"].split("/")[-1] for item in additions]
    assert added_names == [
        name
        for name, record in registry["record_catalog_delta"].items()
        if record["operation"] == "ADD_ABSENT"
    ]
    prior_names = set(base["record_catalog"]) | set(_v7()["record_catalog_delta"])
    assert not prior_names.intersection(added_names)

    preserve = registry["preservation_freeze"]
    assert preserve["unchanged_v6_tasks"] == ["B1", "B2", "B3", "B4", "B5", "B6"]
    assert preserve["only_b6_addition"] == "b6_outcome_lineage_seam"
    for name in (
        "c19_freeze",
        "grid_freeze",
        "artifact_contracts",
        "state_ceiling_map",
    ):
        assert preserve[name] == base[name]


def test_v8_full_ordered_registry_golden_and_contract_schema_are_closed() -> None:
    registry = _v8()
    assert _digest(_freeze_ordered_json(registry)) == V8_ORDERED_REGISTRY_SHA256

    allowed = {"ADD_ABSENT", "REPLACE_EXACT_SHA256"}
    catalog = registry["record_catalog_delta"]
    effective_names = (
        set(_v6()["record_catalog"]) | set(_v7()["record_catalog_delta"]) | set(catalog)
    )
    schema_ids: set[str] = set()
    for name, record in catalog.items():
        assert set(record) == {
            "operation",
            "schema_id",
            "canonical_owner",
            "field_specs",
            "record_invariants",
        }, name
        assert record["operation"] in allowed
        assert record["schema_id"] not in schema_ids
        schema_ids.add(record["schema_id"])
        assert record["canonical_owner"].startswith("rulespace_v3.")
        assert record["field_specs"]
        assert record["record_invariants"]
        if record["operation"] == "ADD_ABSENT":
            first = record["field_specs"][0]
            assert first["name"].endswith("schema_version"), name
            assert first["wire_type"] == f"Literal[{record['schema_id']}]", name
        names: list[str] = []
        for field in record["field_specs"]:
            assert set(field) == {"name", "wire_type", "presence", "nested_record"}
            assert field["presence"] in {"required", "required-nullable"}
            names.append(field["name"])
            nested = field["nested_record"]
            assert nested is None or nested in effective_names, (name, field)
        assert len(names) == len(set(names)), name

    source = _registry_source(CONTRACT_PATH, BEGIN, END)
    for forbidden in ("TBD", "TODO", "or equivalent", "implementation-defined"):
        assert forbidden not in source

    hostile = copy.deepcopy(registry)
    hostile["portable_trust_anchor_freeze_delta"]["absolute_path"] += ".forged"
    assert _digest(_freeze_ordered_json(hostile)) != V8_ORDERED_REGISTRY_SHA256
    hostile = copy.deepcopy(registry)
    hostile["v3m0_execution_freeze_delta"]["scenario_order"].pop()
    assert _digest(_freeze_ordered_json(hostile)) != V8_ORDERED_REGISTRY_SHA256


def test_b7_parallel_v3_response_chain_preserves_legacy_wires() -> None:
    registry = _v8()
    repairs = registry["legacy_record_repairs"]
    response_source = REPO_ROOT / "rulespace_v3" / "response.py"
    legacy_expected = {
        "PairedFilteredResponse": [
            "pair_schema_version",
            "ablation_manifest_sha",
            "qualification_sha",
            "actual_dynamics_certificate",
            "ablated_dynamics_certificate",
            "actual",
            "ablated",
            "run_spec",
            "shell_manifest",
            "pair_sha",
        ],
        "PairedResponseAttemptAudit": [
            "attempt_schema_version",
            "window_protocol",
            "qualification_sha",
            "actual_factory_sha",
            "ablated_factory_sha",
            "actual_transition",
            "ablated_transition",
            "actual_dynamics_certificate",
            "ablated_dynamics_certificate",
            "run_spec",
            "shell_outcome",
            "actual_branch_attempt",
            "ablated_branch_attempt",
            "first_failure",
            "attempt_sha",
        ],
    }
    for name, expected_fields in legacy_expected.items():
        annotations = _class_annotations(response_source, name)
        assert [field for field, _ in annotations] == expected_fields
        assert repairs[name]["source_field_annotations"] == [
            {"name": field, "annotation": annotation}
            for field, annotation in annotations
        ]
        assert repairs[name]["operation"] == "RESTORE_EXACT_PRODUCTION_SOURCE"
        repaired = _apply_relative_patches(
            _v6()["record_catalog"][name], repairs[name]["record_patch"]
        )
        assert repaired["schema_id"] == repairs[name]["schema_id"]
        repaired_types = {
            field["name"]: field["wire_type"] for field in repaired["field_specs"]
        }
        assert repaired_types["actual_dynamics_certificate"] == "DynamicsCertificate"
        assert repaired_types["ablated_dynamics_certificate"] == "DynamicsCertificate"
    assert "DynamicsCertificateV3" not in json.dumps(
        [
            repairs["PairedFilteredResponse"]["source_field_annotations"],
            repairs["PairedResponseAttemptAudit"]["source_field_annotations"],
        ],
        sort_keys=True,
    )

    attempt_repair = repairs["ResponseBlockAttemptOutcome"]
    repaired_attempt = _apply_relative_patches(
        _v6()["record_catalog"]["ResponseBlockAttemptOutcome"],
        attempt_repair["record_patch"],
    )
    assert repaired_attempt["schema_id"] == "v3m0.response-block-attempt-outcome.v1"
    assert (
        next(
            field
            for field in repaired_attempt["field_specs"]
            if field["name"] == "permit"
        )["wire_type"]
        == "CalibrationApplicationPermit"
    )

    expected_v3 = {
        "ResponseRunSpecV3",
        "EndpointReferenceSpecV3",
        "EndpointReferenceProjectorV3",
        "EndpointReferenceAttemptAuditV3",
        "EndpointReferenceOutcomeV3",
        "EndpointShellSpecV3",
        "EndpointShellManifestV3",
        "EndpointShellAttemptAuditV3",
        "EndpointShellOutcomeV3",
        "PairedFilteredResponseV3",
        "PairedResponseAttemptAuditV3",
        "PairedResponseOutcomeV3",
    }
    assert expected_v3 <= set(registry["record_catalog_delta"])
    for name in expected_v3:
        record = _record(registry, name)
        assert record["canonical_owner"] == "rulespace_v3.application_response_v3"
        assert record["schema_id"].endswith(".v3")
        first = record["field_specs"][0]
        assert first["name"].endswith("schema_version")
        assert first["wire_type"] == f"Literal[{record['schema_id']}]"

    task = registry["task_delta"]["B7"]
    issuer = _api(task, "issue_v3m0_application_paired_response_v3")
    assert [arg["wire_type"] for arg in issuer["args"]] == [
        "VerifiedParentFreezeV3",
        "VerifiedV3M0ApplicationScenarioMaterializationV3",
        "VerifiedDynamicsCertificationOutcomeV3",
        "VerifiedDynamicsCertificationOutcomeV3",
    ]
    assert not {"run_spec", "reference", "shell", "grid", "thresholds"}.intersection(
        arg["name"] for arg in issuer["args"]
    )
    task_wire = json.dumps(task, sort_keys=True)
    assert "ControlRegistryEntry" not in task_wire
    assert "qualification_sha" not in task_wire
    assert "VerifiedDynamicsCertificateV3" not in json.dumps(issuer, sort_keys=True)
    assert registry["response_chain_delta"]["attempt_prefix"] == [
        "reference",
        "shell",
        "actual",
        "matched_ablated",
    ]
    assert registry["response_chain_delta"]["half_pair_capability_allowed"] is False
    assert task["private_view_fields"] == {
        "reference": [
            "outcome",
            "parent",
            "materialization",
            "permit",
            "actual_certification_outcome",
            "actual_certificate",
        ],
        "shell": [
            "outcome",
            "parent",
            "materialization",
            "permit",
            "actual_certification_outcome",
            "actual_certificate",
            "reference",
        ],
        "paired": [
            "outcome",
            "parent",
            "materialization",
            "permit",
            "actual_certification_outcome",
            "matched_ablated_certification_outcome",
            "actual_certificate",
            "matched_ablated_certificate",
            "reference",
            "shell",
        ],
    }


def test_b8_atomic_pair_and_seven_geometry_predicates_are_total() -> None:
    registry = _v8()
    task = registry["task_delta"]["B8"]
    api_names = [api["name"] for api in task["apis"]]
    assert "issue_verified_response_block_from_closed_evidence" not in api_names
    assert api_names == [
        "issue_closed_control_application_evidence_v3",
        "require_closed_control_application_evidence_v3",
        "issue_closed_response_block_pair_v3",
        "issue_inherited_response_block_pair_v3",
        "require_closed_response_block_pair_v3",
        "evaluate_c19_control_geometry_v3",
        "require_c19_control_geometry_evaluation_v3",
    ]
    assert task["atomic_mint_order"] == [
        "build_actual_raw",
        "build_matched_ablated_raw",
        "verify_both_raw",
        "mint_actual_wrapper",
        "mint_matched_ablated_wrapper",
        "mint_pair_outcome_wrapper",
    ]
    assert task["private_view_fields"] == {
        "closed_evidence": [
            "outcome",
            "evidence",
            "parent",
            "materialization",
            "actual_certification_outcome",
            "matched_ablated_certification_outcome",
            "paired_response",
        ],
        "block_pair": [
            "outcome",
            "authority_route",
            "authority_outcome",
            "actual_response_block",
            "matched_ablated_response_block",
        ],
        "geometry": [
            "outcome",
            "evaluation",
            "closed_evidence",
            "response_block_pair",
        ],
    }
    geometry = _api(task, "evaluate_c19_control_geometry_v3")
    assert [arg["wire_type"] for arg in geometry["args"]] == [
        "VerifiedClosedControlApplicationEvidenceV3",
        "VerifiedResponseBlockPairOutcomeV3",
    ]
    inherited_pair = _api(task, "issue_inherited_response_block_pair_v3")
    assert [arg["wire_type"] for arg in inherited_pair["args"]] == [
        "VerifiedParentV3InheritedResponseOutcomeV1"
    ]
    pair_attempt = _record(registry, "ResponseBlockPairAttemptV3")
    assert "closed_evidence_sha" not in _field_names(pair_attempt)
    assert _field(pair_attempt, "authority_route")["wire_type"] == (
        "Literal[CURRENT_C19,INHERITED_PARENT_V3]"
    )
    assert _field(pair_attempt, "authority_outcome_sha")["wire_type"] == "sha256"

    freeze = registry["geometry_predicate_freeze"]
    assert freeze["current_c19_identity_ref"] == (
        "/v3m0_execution_freeze_delta/current_c19_identity"
    )
    assert freeze["legacy_v1_scenario_allowed"] is False
    assert tuple(freeze["ordered_predicate_ids"]) == GEOMETRY_PREDICATE_IDS
    assert freeze["second_predicate_mode"] == "WHITENED_COISOMETRY_ONLY_FOR_C19"
    assert len(freeze["presence_matrix"]) == 7
    assert [item["predicate_id"] for item in freeze["presence_matrix"]] == list(
        GEOMETRY_PREDICATE_IDS
    )
    assert all(item["present_fields"] for item in freeze["presence_matrix"])
    assert len(freeze["formula_contracts"]) == 7
    assert all(item["threshold_source"] for item in freeze["formula_contracts"])

    evaluation = _record(registry, "GeometryPrerequisiteEvaluationV3")
    assert _field(evaluation, "status")["wire_type"] == "BlockStatus[evaluability]"
    assert _field(evaluation, "predicate_passed")["wire_type"] == "Optional[bool]"
    assert (
        "predicate_passed is null iff status is undefined"
        in evaluation["record_invariants"]
    )
    geometry_outcome = _record(registry, "C19ControlGeometryEvaluationOutcomeV3")
    assert _field(geometry_outcome, "status")["wire_type"] == (
        "BlockStatus[evaluability]"
    )
    assert (
        "status is defined and failure null iff evaluation exists and "
        "evaluation.all_evaluable is true; all_predicates_passed may then be true or "
        "false" in geometry_outcome["record_invariants"]
    )
    assert (
        "prerequisite_false"
        not in registry["enum_catalog_delta"]["C19ControlGeometryFailureV3"]
    )
    require_geometry = _api(task, "require_c19_control_geometry_evaluation_v3")
    assert require_geometry["semantics"] == (
        "return evaluation when all seven predicates are evaluable, retaining "
        "all_predicates_passed true or false"
    )
    assert "PREREQUISITE_FALSE" not in task["typed_failures"]
    pair = _record(registry, "ResponseBlockPairOutcomeV3")
    assert {
        "actual_response_block",
        "matched_ablated_response_block",
    } <= set(_field_names(pair))


def test_b9_scenario_union_counts_order_calibrations_and_invariants_are_exact() -> None:
    registry = _v8()
    freeze = registry["v3m0_execution_freeze_delta"]
    assert tuple(freeze["scenario_order"]) == SCENARIO_ORDER
    assert freeze["scenario_counts"] == {
        "total": 31,
        "block_success": 22,
        "inherited_block_success": 21,
        "current_c19_block_success": 1,
        "expected_typed_termination": 7,
        "analysis_control": 2,
    }
    assert freeze["successful_response_block_sha_count"] == 44
    assert freeze["window_calibration_count"] == 1
    assert tuple(freeze["representation_invariant_ids"]) == INVARIANT_IDS
    source_authority = freeze["representation_source_authority"]
    assert (
        hashlib.sha256(REPRESENTATION_PLAN_PATH.read_bytes()).hexdigest()
        == REPRESENTATION_PLAN_RAW_SHA256
    )
    assert source_authority == {
        "caller_source_allowed": False,
        "recipe_source_path": REPRESENTATION_PLAN_PATH.relative_to(
            REPO_ROOT
        ).as_posix(),
        "recipe_source_raw_sha256": REPRESENTATION_PLAN_RAW_SHA256,
        "recipe_source_section": "Task 17 / 9 项 representation invariants",
        "derivation": (
            "full invariant ID selects its frozen recipe; issuer derives baseline and "
            "transformed construction from the recursively verified live Parent"
        ),
    }
    assert freeze["typed_undefined_reason_wires"] == [
        "response_null",
        "response_grey",
        "endpoint_shell_ambiguous",
        "trace_unclassified",
        "unstable",
    ]

    data = json.loads(
        (REPO_ROOT / "data" / "results" / "v3m0_controls.json").read_text(
            encoding="utf-8"
        )
    )
    legacy_order = tuple(item["scenario_id"] for item in data["scenario_manifest"])
    assert legacy_order[:28] == SCENARIO_ORDER[:28]
    assert legacy_order[29:] == SCENARIO_ORDER[29:]
    assert legacy_order[28] == (
        "v3m0.synthetic-control.c19.v1.scenario.observer-collapse.v1"
    )
    assert SCENARIO_ORDER[28] == CURRENT_C19_SCENARIO_ID
    assert freeze["current_c19_identity"] == {
        "control_case_id": "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
        "application_instance_id": "v3m0.synthetic-control.c19.v2",
        "scenario_id": CURRENT_C19_SCENARIO_ID,
        "forbidden_legacy_scenario_id": (
            "v3m0.synthetic-control.c19.v1.scenario.observer-collapse.v1"
        ),
        "source_owner": "rulespace_v3.c19_refreeze_v2",
    }
    c19_source = (REPO_ROOT / "rulespace_v3" / "c19_refreeze_v2.py").read_text(
        encoding="utf-8"
    )
    assert f'C19_SCENARIO_ID_V2 = "{CURRENT_C19_SCENARIO_ID}"' in c19_source

    item = _record(registry, "V3M0ScenarioEvidenceItemV3")
    assert _field(item, "block_success")["wire_type"] == (
        "Optional[V3M0BlockSuccessOutcomeV3]"
    )
    assert "ClosedControlApplicationEvidenceV3" not in json.dumps(item, sort_keys=True)
    block_outcome = _record(registry, "V3M0BlockSuccessOutcomeV3")
    assert _field(block_outcome, "status")["wire_type"] == ("BlockStatus[evaluability]")
    assert _field(block_outcome, "actual_response_block_sha")["wire_type"] == (
        "Optional[sha256]"
    )
    assert _field(block_outcome, "current_c19")["wire_type"] == (
        "Optional[CurrentC19BlockSuccessOutcomeV3]"
    )
    current_attempt = _record(registry, "CurrentC19BlockSuccessAttemptV3")
    assert _field_names(current_attempt)[:10] == [
        "attempt_schema_version",
        "window_calibration",
        "permit",
        "materialization",
        "actual_certification_outcome",
        "matched_ablated_certification_outcome",
        "paired_response_outcome",
        "closed_evidence_outcome",
        "response_block_pair_outcome",
        "geometry_outcome",
    ]
    assert _field(current_attempt, "paired_response_outcome")["wire_type"] == (
        "Optional[PairedResponseOutcomeV3]"
    )
    assert registry["enum_catalog_delta"]["CurrentC19BlockSuccessFailureV3"][:2] == [
        "window_unresolved",
        "dynamics_certification_failed",
    ]
    assert (
        "geometry_evaluation_failed"
        not in registry["enum_catalog_delta"]["CurrentC19BlockSuccessFailureV3"]
    )
    assert "execute_current_c19_block_success_v3" in [
        api["name"] for api in registry["task_delta"]["B9"]["apis"]
    ]
    response_result = _record(registry, "V3M0ResponseResultV3")
    assert "verified_response_block_shas" not in _field_names(response_result)
    assert _field(response_result, "response_block_sha_pairs")["wire_type"] == (
        "tuple[tuple[Optional[sha256],Optional[sha256]];exact=22]"
    )
    assert _field(response_result, "c19_geometry_outcome")["wire_type"] == (
        "Optional[C19ControlGeometryEvaluationOutcomeV3]"
    )
    assert (
        "both members of each SHA pair are present iff the corresponding nested route "
        "attempt contains a successful atomic pair"
        in response_result["record_invariants"]
    )
    assert (
        "C19 geometry outcome is present iff the current-C19 prefix reached geometry "
        "evaluation" in response_result["record_invariants"]
    )
    replay = _record(registry, "ParentV3ScenarioReplayAuthorityV1")
    assert replay["canonical_owner"] == (
        "rulespace_v3.parent_v3_scenario_replay_authority_v1"
    )
    response_attempt = _record(registry, "ParentV3InheritedResponseAttemptV1")
    response_outcome = _record(registry, "ParentV3InheritedResponseOutcomeV1")
    assert response_attempt["canonical_owner"] == (
        "rulespace_v3.inherited_control_execution_v3"
    )
    assert response_outcome["canonical_owner"] == (
        "rulespace_v3.inherited_control_execution_v3"
    )
    assert _field(response_attempt, "window_calibration")["wire_type"] == (
        "WindowThresholdCalibrationV3"
    )
    lower_api = _api(
        registry["task_delta"]["B9"],
        "execute_parent_v3_inherited_response_v1",
    )
    assert lower_api["returns"] == "VerifiedParentV3InheritedResponseOutcomeV1"
    assert [arg["wire_type"] for arg in lower_api["args"]] == [
        "VerifiedParentFreezeV3",
        "VerifiedParentV3ScenarioReplayAuthorityV1",
        "str",
        "VerifiedWindowThresholdCalibrationV3",
    ]
    invariant_api = _api(
        registry["task_delta"]["B9"],
        "evaluate_representation_invariant_v3",
    )
    assert [arg["wire_type"] for arg in invariant_api["args"]] == [
        "VerifiedParentFreezeV3",
        "Literal[full-I01-I09-ids]",
    ]
    assert "source_block_success" not in [arg["name"] for arg in invariant_api["args"]]
    high_attempt = _record(registry, "InheritedBlockSuccessAttemptV3")
    assert high_attempt["canonical_owner"] == (
        "rulespace_v3.inherited_control_measurement_v3"
    )
    assert _field(high_attempt, "inherited_response_outcome")["wire_type"] == (
        "ParentV3InheritedResponseOutcomeV1"
    )
    assert _field(high_attempt, "response_block_pair_outcome")["wire_type"] == (
        "Optional[ResponseBlockPairOutcomeV3]"
    )
    assert not {
        "materialization",
        "response_binding",
        "reference",
        "shell",
        "paired_response",
        "actual_response_block",
        "matched_ablated_response_block",
    }.intersection(_field_names(high_attempt))
    prediction = _record(registry, "ControlPredictionOutcomeV3")
    assert (
        "prediction_mismatch"
        not in registry["enum_catalog_delta"]["ControlPredictionFailureV3"]
    )
    assert (
        "evaluable mismatch is retained as prediction_passed false, not encoded as "
        "failure or undefined" in prediction["record_invariants"]
    )
    inherited_evidence = _record(registry, "InheritedBlockSuccessEvidenceV3")
    inherited_outcome = _record(registry, "InheritedBlockSuccessOutcomeV3")
    assert (
        "prediction_mismatch"
        not in registry["enum_catalog_delta"]["InheritedBlockSuccessFailureV3"]
    )
    assert (
        "prediction_passed is retained exactly and may be true or false"
        in inherited_evidence["record_invariants"]
    )
    assert _field(inherited_outcome, "status")["wire_type"] == (
        "BlockStatus[evaluability]"
    )
    assert (
        "evidence is present and failure null iff status defined; evidence may retain "
        "prediction_passed false" in inherited_outcome["record_invariants"]
    )
    current_outcome = _record(registry, "CurrentC19BlockSuccessOutcomeV3")
    assert _field(current_outcome, "status")["wire_type"] == (
        "BlockStatus[evaluability]"
    )
    assert (
        "both block SHAs are present together iff attempt.response_block_pair_outcome "
        "contains a successful atomic pair, independent of later geometry evaluability "
        "or verdict" in current_outcome["record_invariants"]
    )
    assert (
        "both block SHAs are present together iff the selected nested route attempt "
        "contains a successful atomic pair" in block_outcome["record_invariants"]
    )
    assert registry["task_delta"]["B9"]["module_partition"] == {
        "rulespace_v3.inherited_control_execution_v3": [
            "ParentV3 inherited response prefix",
            "ParentV3 inherited response outcome capability",
            "expected typed termination prefix",
        ],
        "rulespace_v3.blocks": ["route-tagged atomic response-block pair capability"],
        "rulespace_v3.inherited_control_measurement_v3": [
            "survival/geometry calibrations",
            "causal/geometry/sigma observation",
            "prediction and inherited block-success outcome",
        ],
    }
    application_invariant = freeze["application_scenario_invariant_replacement"]
    assert application_invariant == (
        "BLOCK_SUCCESS requires expected_terminal_stage == success, "
        "expected_undefined_reason is null, and expected_artifact_type == "
        "VerifiedResponseBlock"
    )

    observation = _record(registry, "RepresentationInvariantObservationV3")
    assert "canonical-json-object" not in json.dumps(observation, sort_keys=True)
    outcome = _record(registry, "RepresentationInvariantOutcomeV3")
    assert _field(outcome, "passed")["wire_type"] == "Optional[bool]"
    assert _field(outcome, "baseline_block_success_outcome")["wire_type"] == (
        "V3M0BlockSuccessOutcomeV3"
    )
    assert _field(outcome, "transformed_block_success_outcome")["wire_type"] == (
        "Optional[V3M0BlockSuccessOutcomeV3]"
    )
    assert _field(outcome, "observation")["wire_type"] == (
        "Optional[RepresentationInvariantObservationV3]"
    )
    assert (
        "observation is present and passed is bool iff status evaluable; both are null "
        "iff status undefined" in outcome["record_invariants"]
    )


def test_current_c19_v1_identity_splice_is_rejected() -> None:
    registry = _v8()
    _assert_current_c19_v2_identity(registry)

    spliced = copy.deepcopy(registry)
    identity = spliced["v3m0_execution_freeze_delta"]["current_c19_identity"]
    spliced["v3m0_execution_freeze_delta"]["scenario_order"][28] = identity[
        "forbidden_legacy_scenario_id"
    ]
    with pytest.raises(AssertionError):
        _assert_current_c19_v2_identity(spliced)


def test_b1_window_unresolved_path_reaches_a_signable_halt_checkpoint() -> None:
    registry = _v8()
    current_attempt = _record(registry, "CurrentC19BlockSuccessAttemptV3")
    assert _field_names(current_attempt)[:3] == [
        "attempt_schema_version",
        "window_calibration",
        "permit",
    ]
    assert (
        "window calibration is always retained; unresolved selection leaves every later "
        "optional body null" in current_attempt["record_invariants"]
    )
    assert (
        "window_unresolved"
        in registry["enum_catalog_delta"]["CurrentC19BlockSuccessFailureV3"]
    )
    assert "HALT-V3M0-WINDOW" in registry["task_delta"]["B9"]["typed_failures"]
    run_outcome = _record(registry, "V3M0RunOutcomeV3")
    assert (
        "all 22 and all 7 typed outcomes remain present on HALT"
        in run_outcome["record_invariants"]
    )
    checkpoint = _record(registry, "V3M0CheckpointEnvelopeV1")
    assert (
        "HALT or READY state may be signed; checkpoint never itself issues next-stage "
        "authority" in checkpoint["record_invariants"]
    )
    assert (
        registry["portable_verifier_freeze_delta"]["halt_states_are_signable"] is True
    )
    assert (
        registry["preservation_freeze"]["state_ceiling_map"]["HALT-V3M0-WINDOW"]
        == "STOP"
    )


def test_b9_resolver_inputs_and_failure_capability_accounting_are_total() -> None:
    registry = _v8()
    result = _record(registry, "V3M0InstrumentResultV3")
    assert "all_block_success_artifacts_verified" in _field_names(result)
    resolver = registry["state_resolver_binding"]
    expected_booleans = {
        "formal_all_pass",
        "exact_all_pass",
        "identifiability_all_pass",
        "all_required_controls_pass",
        "all_block_success_artifacts_verified",
        "all_expected_terminations_verified",
        "all_analysis_controls_verified",
        "representation_invariants_pass",
        "no_unexpected_downstream_capability",
    }
    assert set(resolver["boolean_evidence_sources"]) == expected_booleans
    assert all(
        type(sources) is list and len(sources) == 1
        for sources in resolver["boolean_evidence_sources"].values()
    )
    assert resolver["required_block_report_count"] == 22
    assert resolver["required_block_report_includes_typed_terminations"] is False
    assert resolver["delegates_only_to"] == "rulespace_v3.state.resolve_v3m0_state"
    assert resolver["boolean_evidence_sources"]["identifiability_all_pass"] == [
        "22 recursively verified block-success materializations bind construction trace "
        "to the exact Parent scenario without relabel"
    ]
    assert resolver["boolean_evidence_sources"]["all_required_controls_pass"] == [
        "31 scenario evidence items in manifest order; evaluable false prediction or "
        "geometry is control false, never undefined"
    ]
    assert resolver["boolean_evidence_sources"][
        "all_block_success_artifacts_verified"
    ] == [
        "22 ordered optional SHA pairs; true iff all pairs contain exact actual/matched "
        "SHAs joined to their outcomes, yielding 44 total"
    ]
    assert resolver["typed_termination_capability_accounting"] == {
        "outcome_count": 7,
        "downstream_capability_issued_values": [
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        ],
        "issuer_registry_mint_count": 0,
    }


def test_b10_concrete_loader_statement_and_four_leaf_join_are_exact() -> None:
    registry = _v8()
    anchor = registry["portable_trust_anchor_freeze_delta"]
    assert anchor["loader_api"] == {
        "name": "load_campaign_checkpoint_trust_anchor_v1",
        "args": [],
        "returns": "VerifiedCampaignCheckpointTrustAnchorV1",
        "loader_is_issuer": False,
    }
    assert anchor["absolute_path"] == (
        "/etc/computational-universe-lab/trust/v3m0-campaign-checkpoint-anchor-v1.json"
    )
    assert anchor["open_flags"] == ["O_RDONLY", "O_CLOEXEC", "O_NOFOLLOW"]
    assert anchor["fstat_policy"] == {
        "regular_file": True,
        "uid": 0,
        "nlink": 1,
        "group_writable": False,
        "other_writable": False,
        "size_bytes_min": 1,
        "size_bytes_max": 65536,
    }
    assert anchor["parser"] == "STRICT_UTF8_JSON_DUPLICATE_AND_NONFINITE_REJECT"
    assert anchor["caller_path_or_environment_override_allowed"] is False
    assert anchor["position_previous_root_xor"] == {
        "GENESIS": "trusted_previous_portable_envelope_sha MUST be null",
        "CHECKPOINT": "trusted_previous_portable_envelope_sha MUST be sha256",
    }
    assert anchor["verification_order"][0] == "load_and_reverify_exact_live_anchor"
    assert (
        anchor["verification_order"][1] == "only_then_parse_attacker_controlled_bytes"
    )

    task = registry["task_delta"]["B10"]
    assert "CampaignStageFreezeReviewStatementV1" in registry["record_catalog_delta"]
    assert "DetachedInputBundleV1" not in json.dumps(task, sort_keys=True)
    prepare = _api(task, "prepare_v3m0_checkpoint_unsigned_statement_v1")
    assert prepare["returns"] == ("tuple[UnsignedPortableEnvelopeStatementV1,bytes]")
    final = _api(task, "issue_v3m0_checkpoint_envelope_v1")
    assert [arg["name"] for arg in final["args"]][-3:] == [
        "unsigned_statement",
        "unsigned_statement_bytes",
        "review_signatures",
    ]
    verifier = registry["portable_verifier_freeze_delta"]
    assert verifier["reviewer_constraints"] == {
        "signature_count": 2,
        "roles_distinct": True,
        "keys_distinct": True,
        "statement_bytes_exactly_equal": True,
    }
    assert verifier["halt_states_are_signable"] is True
    assert verifier["verification_is_idempotent"] is True
    assert verifier["duplicate_consumption_owned_by_next_stage_issuer"] is True

    artifacts = verifier["four_leaf_join"]
    assert [item["order"] for item in artifacts] == [0, 1, 2, 3]
    assert [item["artifact_contract"] for item in artifacts] == _v6()[
        "artifact_contracts"
    ]
    assert [item["exact_body"] for item in artifacts] == [
        "parent.manifest",
        "run.result.controls_result",
        "run.result.response_result",
        "run.result.state_decision",
    ]


def test_v8_combined_import_dag_is_complete_acyclic_and_layered() -> None:
    registry = _v8()
    v6 = _v6()
    v7 = _v7()
    dag_delta = registry["import_dag_delta"]
    expected_prior = dag_delta["replace_node_expected_prior_sha256"]
    assert set(expected_prior) == set(dag_delta["replace_nodes"])
    for owner, digest in expected_prior.items():
        assert _digest(_freeze_ordered_json(v6["import_dag"][owner])) == digest

    nodes = copy.deepcopy(v6["import_dag"])
    nodes.update(v7["import_dag_delta"]["nodes"])
    nodes.update(registry["import_dag_delta"]["replace_nodes"])
    nodes.update(registry["import_dag_delta"]["add_nodes"])
    leaves = set(v6["import_dag_external_leaves"])
    leaves.update(v7["import_dag_delta"]["external_or_preexisting_leaves"])
    leaves.update(registry["import_dag_delta"]["external_or_preexisting_leaves"])
    _assert_acyclic(nodes, leaves)

    for owner, dependency in registry["import_dag_delta"]["forbidden_edges"]:
        assert dependency not in nodes.get(owner, [])
    assert (
        "rulespace_v3.runtime_v3"
        not in nodes["rulespace_v3.parent_v3_scenario_replay_authority_v1"]
    )
    assert (
        "rulespace_v3.parent_authority_v3"
        not in nodes["rulespace_v3.campaign_stage_authority_v1"]
    )
    assert "rulespace_v3.inherited_control_execution_v3" in nodes["rulespace_v3.blocks"]
    assert (
        "rulespace_v3.blocks"
        not in nodes["rulespace_v3.inherited_control_execution_v3"]
    )
    assert {
        "rulespace_v3.inherited_control_execution_v3",
        "rulespace_v3.blocks",
    } <= set(nodes["rulespace_v3.inherited_control_measurement_v3"])
    assert (
        "rulespace_v3.inherited_control_measurement_v3"
        not in nodes["rulespace_v3.blocks"]
    )
    assert "rulespace_v3.application_response_v3" not in nodes.get(
        "rulespace_v3.response", []
    )
    assert registry["implementation_order"][2:5] == [
        "B9_REPLAY_AND_INHERITED_RESPONSE_LOWER_SLICE",
        "B8_CLOSED_EVIDENCE_ATOMIC_BLOCK_PAIR_AND_GEOMETRY",
        "B9_INHERITED_MEASUREMENT_INVARIANTS_AND_RUNTIME_UPPER_SLICE",
    ]


def test_static_v8_contract_test_imports_no_future_production_module() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden = {
        "rulespace_v3.application_response_v3",
        "rulespace_v3.control_application_evidence_v3",
        "rulespace_v3.control_geometry_evaluation_v3",
        "rulespace_v3.inherited_control_execution_v3",
        "rulespace_v3.inherited_control_measurement_v3",
        "rulespace_v3.parent_v3_scenario_replay_authority_v1",
        "rulespace_v3.representation_invariant_v3",
        "rulespace_v3.runtime_v3",
        "rulespace_v3.portable_ed25519_v1",
        "rulespace_v3.campaign_stage_authority_v1",
        "rulespace_v3.checkpoint_envelope_v1",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert not forbidden.intersection(imported)


def test_strict_v8_loader_rejects_duplicate_keys_and_nonfinite_constants() -> None:
    source = _registry_source(CONTRACT_PATH, BEGIN, END)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        json.loads(
            source.replace(
                '"document_authority": "DESIGN_ONLY_NO_AUTHORITY",',
                '"document_authority": "DESIGN_ONLY_NO_AUTHORITY",\n'
                '  "document_authority": "FORGED",',
                1,
            ),
            object_pairs_hook=_reject_duplicate_keys,
        )
    with pytest.raises(ValueError, match="non-finite"):
        json.loads(
            source.replace('"threshold_values": {},', '"threshold_values": NaN,', 1),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant: {value}")
            ),
        )
