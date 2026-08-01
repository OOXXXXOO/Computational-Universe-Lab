from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
from dataclasses import fields as dataclass_fields, replace
from pathlib import Path

import numpy as np
import pytest

from rulespace_v3 import parent_v3_contracts as contracts
from rulespace_v3.c19_refreeze_v2 import (
    BRIDGE_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION,
    C19_APPLICATION_INSTANCE_ID_V2,
    C19_BASIS_CONTRACT_V2_SCHEMA_VERSION,
    C19_CAUSAL_CONTRAST_ROLE_V2,
    C19_CLAIM_CEILING_V2,
    C19_CONTROL_CASE_ID_V2,
    C19_DESIGN_FREEZE_COMMIT_SHA_V2,
    C19_DESIGN_SOURCE_PATH_V2,
    C19_DESIGN_SOURCE_SHA_V2,
    C19_FAMILY_ELIGIBILITY_V2,
    C19_OBSERVER_GEOMETRY_BUNDLE_V1_SCHEMA_VERSION,
    C19_PHYSICAL_ANCHOR_ELIGIBILITY_V2,
    C19_SCENARIO_ID_V2,
    C19_STATE_SCHEMA_ID_V2,
    DYNAMICS_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION,
    build_c19_refreeze_v2_candidate,
    c19_basis_contract_v2_payload,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    build_basis_manifest,
    factory_payload,
    freeze_complex_tensor,
    frozen_tensor_array,
)
from rulespace_v3.grids import RESPONSE_GRID_SCHEMA_VERSION
from rulespace_v3.parent_v2_contracts import CurrentApplicationAuthorityV2


def test_parent_v3_contract_module_exists() -> None:
    assert importlib.util.find_spec("rulespace_v3.parent_v3_contracts") is not None


def test_parent_v3_raw_contract_api_is_present() -> None:
    expected = {
        "CurrentApplicationAuthorityV3",
        "CurrentScenarioAuthorityV3",
        "CurrentScenarioResponseContractV3",
        "MetricSupportDerivationProtocolV1",
        "build_c19_current_application_authority_v3",
        "current_application_authority_v3_payload",
        "current_scenario_authority_v3_payload",
        "current_scenario_response_contract_v3_payload",
        "metric_support_derivation_protocol_v1_payload",
        "verify_metric_support_derivation_protocol_v1",
        "verify_current_application_authority_v3",
    }
    assert expected <= set(vars(contracts))


@pytest.fixture(scope="module")
def authority():
    return contracts.build_c19_current_application_authority_v3()


def _resign_response(response, **changes):
    provisional = replace(
        response,
        response_contract_sha="0" * 64,
        **changes,
    )
    return replace(
        provisional,
        response_contract_sha=canonical_sha(
            contracts.current_scenario_response_contract_v3_payload(provisional)
        ),
    )


def _resign_scenario(scenario, **changes):
    provisional = replace(
        scenario,
        scenario_authority_sha="0" * 64,
        **changes,
    )
    return replace(
        provisional,
        scenario_authority_sha=canonical_sha(
            contracts.current_scenario_authority_v3_payload(provisional)
        ),
    )


def _resign_application(application, **changes):
    provisional = replace(
        application,
        application_authority_sha="0" * 64,
        **changes,
    )
    return replace(
        provisional,
        application_authority_sha=canonical_sha(
            contracts.current_application_authority_v3_payload(provisional)
        ),
    )


def test_zero_argument_builder_replays_the_only_provisional_c19_body(authority) -> None:
    assert not inspect.signature(
        contracts.build_c19_current_application_authority_v3
    ).parameters
    assert type(authority) is contracts.CurrentApplicationAuthorityV3
    assert contracts.verify_current_application_authority_v3(authority) is authority
    assert authority.application_authority_schema_version == (
        "v3m0.current-application-authority.v3"
    )
    assert authority.authority_state == "PROVISIONAL_NOT_ISSUED"
    assert authority.source_disposition == "C19_REFREEZE_V2_REVIEWED"
    assert authority.control_case_id == C19_CONTROL_CASE_ID_V2
    assert authority.application_instance_id == C19_APPLICATION_INSTANCE_ID_V2
    assert authority.claim_ceiling == C19_CLAIM_CEILING_V2
    assert authority.causal_contrast_role == C19_CAUSAL_CONTRAST_ROLE_V2
    assert authority.physical_anchor_eligibility == C19_PHYSICAL_ANCHOR_ELIGIBILITY_V2
    assert authority.family_eligibility == C19_FAMILY_ELIGIBILITY_V2
    assert authority.design_source_path == C19_DESIGN_SOURCE_PATH_V2
    assert authority.design_source_sha == C19_DESIGN_SOURCE_SHA_V2
    assert authority.design_freeze_commit_sha == C19_DESIGN_FREEZE_COMMIT_SHA_V2
    assert authority.application_authority_sha == canonical_sha(
        contracts.current_application_authority_v3_payload(authority)
    )


def test_application_recursively_carries_the_real_20_channel_construction(
    authority,
) -> None:
    runtime = authority.runtime_construction
    assert authority.state_schema_id == C19_STATE_SCHEMA_ID_V2
    assert authority.state_shape == (20, 8)
    assert authority.spatial_shape == (8,)
    assert authority.spatial_ndim == 1
    assert len(authority.channel_order) == 20
    assert frozen_tensor_array(authority.common_source_tensor).tobytes() == (
        np.eye(20, dtype=np.complex128).tobytes()
    )
    assert frozen_tensor_array(authority.common_readout_tensor).tobytes() == (
        np.eye(20, dtype=np.complex128).tobytes()
    )
    assert authority.common_source_basis.role == "source"
    assert authority.common_readout_basis.role == "readout"
    assert runtime.state_shape == (20, 8)
    assert authority.runtime_construction_sha == runtime.construction_sha
    assert authority.basis_contract_sha == (
        authority.scenario_authorities[
            0
        ].response_contract.basis_contract.basis_contract_sha
    )
    assert authority.operation_dag_sha == runtime.construction_trace.trace_sha
    assert authority.target_spec_sha == runtime.frozen_target.target_spec_sha
    assert authority.actual_factory_sha == runtime.actual_factory.factory_sha
    assert authority.matched_factory_sha == runtime.matched_factory.factory_sha
    assert authority.ablation_manifest_sha == runtime.ablation_manifest.manifest_sha
    assert authority.actual_slot_program_sha == runtime.actual_slot_program_sha
    assert authority.matched_slot_program_sha == runtime.matched_slot_program_sha
    assert authority.actual_active_effect_digest == runtime.actual_active_effect_digest
    assert (
        authority.matched_active_effect_digest == runtime.matched_active_effect_digest
    )


def test_application_registry_keeps_both_50_slot_programs_and_20_neutrals(
    authority,
) -> None:
    assert (
        authority.actual_active_step_count,
        authority.matched_active_step_count,
        authority.actual_layer_slot_count,
        authority.matched_layer_slot_count,
        authority.actual_primitive_count,
        authority.matched_primitive_count,
        authority.matched_neutral_identity_count,
    ) == (50, 30, 50, 50, 50, 50, 20)
    registry = authority.operation_registry
    assert type(registry) is tuple
    assert len(registry) == 100
    assert tuple(row[0] for row in registry[:50]) == ("actual",) * 50
    assert tuple(row[0] for row in registry[50:]) == ("matched_ablated",) * 50
    assert tuple(row[1] for row in registry[:50]) == tuple(range(50))
    assert tuple(row[1] for row in registry[50:]) == tuple(range(50))
    assert sum(row[3].operation_id == "neutral_identity" for row in registry) == 20
    assert sum(row[3].operation_id == "local_canonical_shear" for row in registry) == 80
    assert len(authority.runtime_construction.ablation_manifest.replacements) == 20
    assert len(authority.operation_registry_sha) == 64


def test_response_contract_is_complete_pre_response_and_has_no_live_grid_artifact(
    authority,
) -> None:
    scenario = authority.scenario_authorities[0]
    response = scenario.response_contract
    assert type(scenario) is contracts.CurrentScenarioAuthorityV3
    assert type(response) is contracts.CurrentScenarioResponseContractV3
    assert response.response_contract_schema_version == (
        "v3m0.current-scenario-response-contract.v3"
    )
    assert response.contract_state == "PROVISIONAL_NOT_ISSUED"
    assert response.runtime_artifact_state == (
        "DYNAMICS_AND_BRIDGE_NOT_DERIVED_PRE_RESPONSE"
    )
    assert response.measurement_state == "NOT_EVALUATED_PRE_RESPONSE"
    assert response.uses_global_fft_projection is False
    assert response.uses_per_k_time_step_projector is False
    assert response.basis_contract.basis_contract_schema_version == (
        C19_BASIS_CONTRACT_V2_SCHEMA_VERSION
    )
    assert response.dynamics_grid_derivation.protocol_schema_version == (
        DYNAMICS_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION
    )
    metric = response.metric_support_derivation
    assert type(metric) is contracts.MetricSupportDerivationProtocolV1
    assert metric.protocol_schema_version == (
        "v3m0.metric-support-derivation-protocol.v1"
    )
    assert metric.metric_kind == "constant-state-v1"
    assert metric.state_schema_id == C19_STATE_SCHEMA_ID_V2
    assert metric.channel_order == authority.channel_order
    assert metric.spatial_shape == (8,)
    assert metric.spatial_ndim == 1
    assert metric.state_metric == response.geometry_bundle.state_metric
    assert metric.normalization_id == "trace-at-zero-equals-state-dim-v1"
    assert metric.support_derivation_id == "constant-kernel-origin-only-v1"
    assert metric.metric_support_offsets == ((0,),)
    assert metric.metric_support_sha == canonical_sha(
        {
            "support_schema_version": "v3m0.metric-support.v1",
            "support_offsets": [[0]],
        }
    )
    assert metric.caller_supplied_support_allowed is False
    assert metric.protocol_sha == canonical_sha(
        contracts.metric_support_derivation_protocol_v1_payload(metric)
    )
    assert response.response_grid.grid_schema_version == RESPONSE_GRID_SCHEMA_VERSION
    assert response.response_grid.torus_denominators == (8,)
    assert response.response_grid.reciprocal_indices == ((1,),)
    assert response.response_reference_reciprocal_index == (1,)
    assert response.bridge_grid_derivation.protocol_schema_version == (
        BRIDGE_K_GRID_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION
    )
    assert response.geometry_bundle.geometry_bundle_schema_version == (
        C19_OBSERVER_GEOMETRY_BUNDLE_V1_SCHEMA_VERSION
    )
    assert response.geometry_bundle.state_dim == 20
    assert response.expected_actual_shell_rank == 10
    assert response.expected_matched_shell_rank == 10
    assert response.response_contract_sha == canonical_sha(
        contracts.current_scenario_response_contract_v3_payload(response)
    )
    forbidden_fields = {
        "dynamics_grid_manifest",
        "dynamics_grid_manifest_sha",
        "bridge_grid_manifest",
        "bridge_grid_manifest_sha",
        "metric_signed_support_attestation",
        "metric_signed_support_attestation_sha",
        "parent_freeze_v3_sha",
        "verdict",
    }
    assert not forbidden_fields.intersection(
        field.name for field in dataclass_fields(type(response))
    )


def test_metric_support_protocol_has_an_independent_canonical_verifier(
    authority,
) -> None:
    metric = authority.scenario_authorities[
        0
    ].response_contract.metric_support_derivation
    assert contracts.verify_metric_support_derivation_protocol_v1(metric) is metric

    class MetricSubclass(type(metric)):
        pass

    subclass = object.__new__(MetricSubclass)
    for name, value in vars(metric).items():
        object.__setattr__(subclass, name, value)
    with pytest.raises(TypeError):
        contracts.verify_metric_support_derivation_protocol_v1(subclass)

    future = copy.deepcopy(metric)
    object.__setattr__(future, "parent_freeze_v3_sha", "a" * 64)
    with pytest.raises(ValueError):
        contracts.verify_metric_support_derivation_protocol_v1(future)


def test_payloads_reject_non_exact_metric_and_response_container_types(
    authority,
) -> None:
    class TupleSubclass(tuple):
        pass

    response = authority.scenario_authorities[0].response_contract
    metric = response.metric_support_derivation
    with pytest.raises(TypeError):
        contracts.metric_support_derivation_protocol_v1_payload(
            replace(metric, channel_order=TupleSubclass(metric.channel_order))
        )
    with pytest.raises(TypeError):
        contracts.metric_support_derivation_protocol_v1_payload(
            replace(
                metric,
                metric_support_offsets=TupleSubclass(metric.metric_support_offsets),
            )
        )
    with pytest.raises(TypeError):
        contracts.metric_support_derivation_protocol_v1_payload(
            replace(metric, metric_support_offsets=((False,),))
        )
    with pytest.raises(TypeError):
        contracts.current_scenario_response_contract_v3_payload(
            replace(
                response,
                response_reference_reciprocal_index=TupleSubclass((1,)),
            )
        )


def test_scenario_binds_candidate_runtime_basis_and_response_roots(authority) -> None:
    scenario = authority.scenario_authorities[0]
    response = scenario.response_contract
    assert len(authority.scenario_authorities) == 1
    assert scenario.scenario_authority_schema_version == (
        "v3m0.current-scenario-authority.v3"
    )
    assert scenario.authority_state == "PROVISIONAL_NOT_ISSUED"
    assert scenario.source_disposition == "C19_REFREEZE_V2_REVIEWED"
    assert scenario.control_case_id == authority.control_case_id
    assert scenario.application_instance_id == authority.application_instance_id
    assert scenario.scenario_id == C19_SCENARIO_ID_V2 == response.scenario_id
    assert scenario.source_candidate_sha == authority.source_candidate_sha
    assert (
        scenario.source_runtime_construction_sha == authority.runtime_construction_sha
    )
    assert scenario.source_basis_contract_sha == authority.basis_contract_sha
    assert response.runtime_construction_sha == authority.runtime_construction_sha
    assert response.actual_factory_sha == authority.actual_factory_sha
    assert response.matched_factory_sha == authority.matched_factory_sha
    assert response.operation_dag_sha == authority.operation_dag_sha
    assert scenario.scenario_authority_sha == canonical_sha(
        contracts.current_scenario_authority_v3_payload(scenario)
    )


def test_grid_root_hashes_all_three_distinct_complete_grid_bodies(authority) -> None:
    response = authority.scenario_authorities[0].response_contract
    assert type(response.dynamics_grid_derivation) is not type(response.response_grid)
    assert type(response.bridge_grid_derivation) is not type(response.response_grid)
    assert type(response.dynamics_grid_derivation) is not type(
        response.bridge_grid_derivation
    )
    assert len(authority.grid_protocol_root_sha) == 64
    assert authority.grid_protocol_root_sha not in {
        response.dynamics_grid_derivation.protocol_sha,
        response.response_grid.response_grid_sha,
        response.bridge_grid_derivation.protocol_sha,
    }


def test_dependency_closure_is_explicitly_provisional_and_replays_live_raw_bytes(
    authority,
) -> None:
    expected_paths = (
        "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md",
        "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md",
        "rulespace_v3/ablation.py",
        "rulespace_v3/c19_refreeze_v2.py",
        "rulespace_v3/evidence.py",
        "rulespace_v3/factory.py",
        "rulespace_v3/grids.py",
        "rulespace_v3/metric.py",
        "rulespace_v3/parent_v3_contracts.py",
        "rulespace_v3/trace.py",
    )
    assert authority.construction_dependency_closure_state == (
        "PROVISIONAL_CONSTRUCTION_DEPENDENCIES_NOT_SIGNED"
    )
    assert tuple(path for path, _ in authority.construction_dependency_closure) == (
        expected_paths
    )
    assert "rulespace_v3/parent_v3_contracts.py" in expected_paths
    repository = Path(__file__).resolve().parents[1]
    for relative_path, observed_sha in authority.construction_dependency_closure:
        assert (
            observed_sha
            == hashlib.sha256((repository / relative_path).read_bytes()).hexdigest()
        )
    assert len(authority.construction_dependency_closure_sha) == 64


def test_raw_module_has_no_issuer_hydrator_promoter_or_verified_capability() -> None:
    public = set(getattr(contracts, "__all__", ()))
    assert public
    assert not any(
        token in name.lower()
        for name in public
        for token in ("issue", "hydrate", "promote")
    )
    assert not any(name.startswith("Verified") for name in public)
    assert not {
        "ParentFreezeV3Manifest",
        "VerifiedParentFreezeV3",
        "issue_v3m0_parent_freeze_v3",
    }.intersection(vars(contracts))


def test_v2_historical_dict_and_subclass_cannot_impersonate_v3(authority) -> None:
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(
            build_c19_refreeze_v2_candidate()
        )
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(
            object.__new__(CurrentApplicationAuthorityV2)
        )
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(
            contracts.current_application_authority_v3_payload(authority)
        )

    class ApplicationSubclass(type(authority)):
        pass

    subclass = object.__new__(ApplicationSubclass)
    for name, value in vars(authority).items():
        object.__setattr__(subclass, name, value)
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(subclass)


def test_unknown_missing_and_outer_root_fields_fail_closed(authority) -> None:
    unknown = copy.deepcopy(authority)
    object.__setattr__(unknown, "caller_verdict", "PASS")
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(unknown)

    missing = copy.deepcopy(authority)
    object.__delattr__(missing, "grid_protocol_root_sha")
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(missing)

    outer = copy.deepcopy(authority)
    geometry = outer.scenario_authorities[0].response_contract.geometry_bundle
    object.__setattr__(geometry, "parent_freeze_v3_sha", "a" * 64)
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(outer)


def test_recursive_exact_closure_rejects_unknown_fields_and_tuple_subclasses(
    authority,
) -> None:
    class TupleSubclass(tuple):
        pass

    unknown_grid = copy.deepcopy(authority)
    response = unknown_grid.scenario_authorities[0].response_contract
    object.__setattr__(response.response_grid, "undeclared_live_grid", ((0,),))
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(unknown_grid)

    metric_support = copy.deepcopy(authority)
    metric = metric_support.scenario_authorities[
        0
    ].response_contract.metric_support_derivation
    object.__setattr__(
        metric,
        "metric_support_offsets",
        TupleSubclass(metric.metric_support_offsets),
    )
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(metric_support)

    metric_channels = copy.deepcopy(authority)
    metric = metric_channels.scenario_authorities[
        0
    ].response_contract.metric_support_derivation
    object.__setattr__(metric, "channel_order", TupleSubclass(metric.channel_order))
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(metric_channels)

    response_reference = copy.deepcopy(authority)
    response = response_reference.scenario_authorities[0].response_contract
    object.__setattr__(
        response,
        "response_reference_reciprocal_index",
        TupleSubclass(response.response_reference_reciprocal_index),
    )
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(response_reference)


def test_claim_measurement_and_id_upgrades_fail_even_when_every_outer_hash_is_resigned(
    authority,
) -> None:
    upgraded = _resign_application(authority, claim_ceiling="SCIENCE_PASS")
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(upgraded)

    scenario = authority.scenario_authorities[0]
    triggered_response = _resign_response(
        scenario.response_contract, measurement_state="PASS"
    )
    triggered_scenario = _resign_scenario(
        scenario,
        response_contract=triggered_response,
    )
    triggered = _resign_application(
        authority,
        scenario_authorities=(triggered_scenario,),
    )
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(triggered)

    spliced_response = _resign_response(
        scenario.response_contract,
        scenario_id="v3m0.synthetic-control.cross-splice",
    )
    spliced_scenario = _resign_scenario(
        scenario,
        scenario_id="v3m0.synthetic-control.cross-splice",
        response_contract=spliced_response,
    )
    spliced = _resign_application(
        authority,
        scenario_authorities=(spliced_scenario,),
    )
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(spliced)


def test_wrong_executable_p_rows_and_source_trials_fail_after_recursive_resigning(
    authority,
) -> None:
    scenario = authority.scenario_authorities[0]
    response = scenario.response_contract
    basis = response.basis_contract
    executable_p = frozen_tensor_array(basis.readout_selector_p)
    wrong_readout = build_basis_manifest(
        role="readout",
        state_schema_id=basis.state_schema_id,
        channel_order=basis.channel_order,
        vectors=executable_p,
    )
    provisional_basis = replace(
        basis,
        scenario_readout_basis=wrong_readout,
        source_trial_vectors=freeze_complex_tensor(
            2.0 * np.eye(10, dtype=np.complex128)
        ),
        basis_contract_sha="0" * 64,
    )
    bad_basis = replace(
        provisional_basis,
        basis_contract_sha=canonical_sha(
            c19_basis_contract_v2_payload(provisional_basis)
        ),
    )
    bad_response = _resign_response(response, basis_contract=bad_basis)
    bad_scenario = _resign_scenario(
        scenario,
        source_basis_contract_sha=bad_basis.basis_contract_sha,
        response_contract=bad_response,
    )
    bad = _resign_application(
        authority,
        basis_contract_sha=bad_basis.basis_contract_sha,
        scenario_authorities=(bad_scenario,),
    )
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(bad)


def test_slot_deletion_and_neutral_registry_drift_fail_after_self_resigning(
    authority,
) -> None:
    runtime = authority.runtime_construction
    active_matched = tuple(
        primitive
        for primitive in runtime.matched_factory.primitives
        if primitive.operation_id == "local_canonical_shear"
    )
    provisional_factory = replace(
        runtime.matched_factory,
        layer_slot_ids=tuple(item.layer_slot_id for item in active_matched),
        primitives=active_matched,
        factory_sha="0" * 64,
    )
    deleted_factory = replace(
        provisional_factory,
        factory_sha=canonical_sha(factory_payload(provisional_factory)),
    )
    deleted_runtime = replace(
        runtime,
        matched_factory=deleted_factory,
        matched_layer_slot_count=30,
        matched_primitive_count=30,
        construction_sha="0" * 64,
    )
    # The outer body is fully self-hashed, but its deleted runtime no longer
    # equals the closed C19 construction.
    deleted = _resign_application(
        authority,
        runtime_construction=deleted_runtime,
        matched_factory_sha=deleted_factory.factory_sha,
        matched_layer_slot_count=30,
        matched_primitive_count=30,
    )
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(deleted)

    registry = list(authority.operation_registry)
    first_neutral = next(
        index
        for index, row in enumerate(registry)
        if row[3].operation_id == "neutral_identity"
    )
    row = registry[first_neutral]
    registry[first_neutral] = (
        row[0],
        row[1],
        row[2],
        replace(row[3], neutral_identity_id="drift"),
    )
    drifted = _resign_application(
        authority,
        operation_registry=tuple(registry),
        operation_registry_sha="a" * 64,
    )
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(drifted)


def test_primitive_factory_resigning_cannot_bypass_closed_replay(authority) -> None:
    runtime = authority.runtime_construction
    primitives = list(runtime.actual_factory.primitives)
    primitives[0] = replace(primitives[0], coefficient_wire=(2.0, 0.0))
    provisional_factory = replace(
        runtime.actual_factory,
        primitives=tuple(primitives),
        factory_sha="0" * 64,
    )
    resigned_factory = replace(
        provisional_factory,
        factory_sha=canonical_sha(factory_payload(provisional_factory)),
    )
    provisional_runtime = replace(
        runtime,
        actual_factory=resigned_factory,
        construction_sha="0" * 64,
    )
    drifted = _resign_application(
        authority,
        runtime_construction=provisional_runtime,
        actual_factory_sha=resigned_factory.factory_sha,
    )
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(drifted)


def test_live_grid_injection_grid_swaps_and_legacy_geometry_fail_closed(
    authority,
) -> None:
    injected = copy.deepcopy(authority)
    response = injected.scenario_authorities[0].response_contract
    object.__setattr__(response, "dynamics_grid_manifest_sha", "a" * 64)
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(injected)

    swapped = copy.deepcopy(authority)
    response = swapped.scenario_authorities[0].response_contract
    object.__setattr__(
        response,
        "dynamics_grid_derivation",
        response.bridge_grid_derivation,
    )
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(swapped)

    legacy = copy.deepcopy(authority)
    object.__setattr__(
        legacy.scenario_authorities[0].response_contract,
        "geometry_bundle",
        {"state_dim": 4, "geometry_profile": "legacy-v3"},
    )
    with pytest.raises(TypeError):
        contracts.verify_current_application_authority_v3(legacy)


def test_metric_support_protocol_drift_and_future_authority_fail_closed(
    authority,
) -> None:
    raw = copy.deepcopy(authority)
    metric = raw.scenario_authorities[0].response_contract.metric_support_derivation
    object.__setattr__(metric, "parent_freeze_v3_sha", "a" * 64)
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(raw)

    scenario = authority.scenario_authorities[0]
    response = scenario.response_contract
    metric = response.metric_support_derivation
    bad_metric = replace(
        metric,
        metric_support_offsets=((1,),),
        metric_support_sha=canonical_sha(
            {
                "support_schema_version": "v3m0.metric-support.v1",
                "support_offsets": [[1]],
            }
        ),
        protocol_sha="0" * 64,
    )
    bad_metric = replace(
        bad_metric,
        protocol_sha=canonical_sha(
            contracts.metric_support_derivation_protocol_v1_payload(bad_metric)
        ),
    )
    bad_response = _resign_response(
        response,
        metric_support_derivation=bad_metric,
    )
    bad_scenario = _resign_scenario(scenario, response_contract=bad_response)
    bad = _resign_application(authority, scenario_authorities=(bad_scenario,))
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(bad)


def test_dependency_closure_drift_and_design_freeze_cross_splice_fail_resigned(
    authority,
) -> None:
    closure = list(authority.construction_dependency_closure)
    closure[0] = (closure[0][0], "a" * 64)
    drifted = _resign_application(
        authority,
        construction_dependency_closure=tuple(closure),
        construction_dependency_closure_sha="b" * 64,
    )
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(drifted)

    cross_spliced = _resign_application(
        authority,
        design_freeze_commit_sha="4" * 40,
    )
    with pytest.raises(ValueError):
        contracts.verify_current_application_authority_v3(cross_spliced)
