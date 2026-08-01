from __future__ import annotations

import numpy as np
import pytest


class TestC19RefreezeV2RuntimeConstruction:
    def test_zero_argument_candidate_replays_real_fifty_slot_factories(self) -> None:
        from rulespace_v3.c19_refreeze_v2 import (
            C19_AUTHORITY_STATE_V2,
            C19_CHANNEL_ORDER_V2,
            C19RefreezeV2Candidate,
            build_c19_refreeze_v2_candidate,
            verify_c19_refreeze_v2_candidate,
        )
        from rulespace_v3.factory import NEUTRAL_IDENTITY_ID, frozen_tensor_array
        from rulespace_v3.trace import MechanismKind

        candidate = build_c19_refreeze_v2_candidate()

        assert type(candidate) is C19RefreezeV2Candidate
        assert candidate.authority_state == C19_AUTHORITY_STATE_V2
        assert candidate.channel_order == C19_CHANNEL_ORDER_V2
        assert candidate.spatial_shape == (8,)

        runtime = candidate.runtime_construction
        assert runtime.state_shape == (20, 8)
        assert runtime.actual_active_step_count == 50
        assert runtime.matched_active_step_count == 30
        assert runtime.actual_layer_slot_count == 50
        assert runtime.matched_layer_slot_count == 50
        assert runtime.actual_primitive_count == 50
        assert runtime.matched_primitive_count == 50
        assert len(runtime.construction_trace.primitives) == 50
        assert (
            sum(
                primitive.kind is MechanismKind.TARGET_CONDITIONED
                for primitive in runtime.construction_trace.primitives
            )
            == 20
        )

        actual = runtime.actual_factory
        matched = runtime.matched_factory
        assert actual.factory_role == "actual"
        assert matched.factory_role == "matched_ablated"
        assert actual.state_shape == matched.state_shape == (20, 8)
        assert actual.layer_slot_ids == matched.layer_slot_ids
        assert len(actual.layer_slot_ids) == len(actual.primitives) == 50
        assert len(matched.layer_slot_ids) == len(matched.primitives) == 50
        assert all(
            item.operation_id == "local_canonical_shear" for item in actual.primitives
        )
        neutrals = tuple(
            item
            for item in matched.primitives
            if item.operation_id == "neutral_identity"
        )
        assert len(neutrals) == 20
        assert all(item.neutral_identity_id == NEUTRAL_IDENTITY_ID for item in neutrals)
        assert len(runtime.ablation_manifest.replacements) == 20
        assert tuple(
            item.layer_slot_id for item in runtime.ablation_manifest.replacements
        ) == tuple(item.layer_slot_id for item in neutrals)
        assert (
            runtime.actual_support_offsets == runtime.matched_support_offsets == ((0,),)
        )

        j2 = np.asarray(((0.0, -1.0), (1.0, 0.0)), dtype=np.complex128)
        j20 = np.zeros((20, 20), dtype=np.complex128)
        for pair in range(10):
            j20[2 * pair : 2 * pair + 2, 2 * pair : 2 * pair + 2] = j2
        kernels = (
            runtime.actual_apply_factory_step_kernel,
            runtime.matched_apply_factory_step_kernel,
            runtime.actual_independent_replay_kernel,
            runtime.matched_independent_replay_kernel,
        )
        assert all(
            frozen_tensor_array(kernel).tobytes() == j20.tobytes() for kernel in kernels
        )

        assert verify_c19_refreeze_v2_candidate(candidate) == candidate

    def test_exact_claim_ceiling_forbids_causal_anchor_and_family_use(self) -> None:
        from rulespace_v3.c19_refreeze_v2 import (
            build_c19_refreeze_v2_candidate,
            c19_refreeze_v2_candidate_payload,
        )

        candidate = build_c19_refreeze_v2_candidate()
        assert candidate.claim_ceiling == "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY"
        assert candidate.causal_contrast_role == "NULL_INTERVENTION_INVARIANCE_CONTROL"
        assert candidate.physical_anchor_eligibility == "INELIGIBLE"
        assert candidate.family_eligibility == "INELIGIBLE"
        assert candidate.design_source_sha == (
            "c79dd64067c5b01cbff7629c85b82e73c03e9960096566147ca31d3ce666051b"
        )
        assert candidate.design_freeze_commit_sha == (
            "87a60dc50b025a360b4aad1e280837b32681bb85"
        )
        payload = c19_refreeze_v2_candidate_payload(candidate)
        assert payload["claim_ceiling"] == "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY"
        assert payload["causal_contrast_role"] == (
            "NULL_INTERVENTION_INVARIANCE_CONTROL"
        )
        assert payload["physical_anchor_eligibility"] == "INELIGIBLE"
        assert payload["family_eligibility"] == "INELIGIBLE"


class TestC19RefreezeV2BasisContract:
    def test_freezes_unique_i20_bplus_p_and_i10_wire(self) -> None:
        from rulespace_v3.c19_refreeze_v2 import (
            C19BasisContractV2,
            build_c19_refreeze_v2_candidate,
        )
        from rulespace_v3.factory import basis_manifest_array, frozen_tensor_array

        candidate = build_c19_refreeze_v2_candidate()
        basis = candidate.basis_contract

        assert type(basis) is C19BasisContractV2
        common_source = basis_manifest_array(basis.common_source_basis)
        common_readout = basis_manifest_array(basis.common_readout_basis)
        i20 = np.eye(20, dtype=np.complex128)
        assert common_source.tobytes() == i20.tobytes()
        assert common_readout.tobytes() == i20.tobytes()
        assert (
            frozen_tensor_array(basis.common_source_tensor).tobytes() == i20.tobytes()
        )
        assert (
            frozen_tensor_array(basis.common_readout_tensor).tobytes() == i20.tobytes()
        )

        b_plus = frozen_tensor_array(basis.source_selector_b_plus)
        readout = frozen_tensor_array(basis.readout_selector_p)
        injection = frozen_tensor_array(basis.source_injection)
        coisometry = frozen_tensor_array(basis.readout_coisometry)
        trials = frozen_tensor_array(basis.source_trial_vectors)
        assert b_plus.shape == (20, 10)
        assert readout.shape == (10, 20)
        assert readout.tobytes() == b_plus.conj().T.tobytes()
        assert injection.tobytes() == b_plus.tobytes()
        assert np.array_equal(coisometry, readout)
        assert trials.tobytes() == np.eye(10, dtype=np.complex128).tobytes()
        assert (
            basis_manifest_array(basis.scenario_source_basis).tobytes()
            == b_plus.T.tobytes()
        )
        assert (
            basis_manifest_array(basis.scenario_readout_basis).tobytes()
            == b_plus.T.tobytes()
        )

        j20 = frozen_tensor_array(
            candidate.runtime_construction.actual_apply_factory_step_kernel
        )
        source_gram = np.einsum("ai,aj->ij", b_plus.conj(), b_plus)
        readout_gram = np.einsum("ia,ja->ij", readout, readout.conj())
        j_source = np.einsum("ab,bi->ai", j20, b_plus)
        reduced = np.einsum("ia,aj->ij", readout, j_source)
        assert np.linalg.norm(source_gram - np.eye(10), ord=2) <= 1.0e-12
        assert np.linalg.norm(readout_gram - np.eye(10), ord=2) <= 1.0e-12
        assert np.linalg.norm(j_source - 1.0j * b_plus, ord=2) <= 1.0e-12
        assert np.linalg.norm(reduced - 1.0j * np.eye(10), ord=2) <= 1.0e-12
        assert np.linalg.matrix_rank(b_plus) == 10
        assert np.linalg.matrix_rank(readout) == 10
        assert np.linalg.matrix_rank(reduced) == 10
        assert basis.expected_actual_shell_rank == 10
        assert basis.expected_matched_shell_rank == 10


class TestC19RefreezeV2PreResponseGrids:
    def test_freezes_derivation_protocols_but_only_live_response_manifest(self) -> None:
        from dataclasses import fields

        from rulespace_v3.c19_refreeze_v2 import (
            BridgeKGridDerivationProtocolV1,
            DynamicsKGridDerivationProtocolV1,
            build_c19_refreeze_v2_candidate,
        )
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.grids import (
            ResponseKGridManifest,
            direction_manifest_payload,
            response_grid_payload,
        )

        candidate = build_c19_refreeze_v2_candidate()
        dynamics = candidate.dynamics_grid_derivation
        response = candidate.response_grid
        bridge = candidate.bridge_grid_derivation

        assert type(dynamics) is DynamicsKGridDerivationProtocolV1
        assert dynamics.branch_roles == ("actual", "matched_ablated")
        assert (
            dynamics.transition_support_source
            == "live-measured-transition-signed-support"
        )
        assert dynamics.metric_support_source == "live-verified-metric-signed-support"
        assert dynamics.exact_zero_qualification_profile == "exact-offset-zero-v1"
        assert dynamics.nonzero_fallback_profile == "cartesian-full-64-v1"
        assert dynamics.caller_supplied_points_allowed is False
        dynamics_fields = {item.name for item in fields(type(dynamics))}
        assert "dynamics_grid" not in dynamics_fields
        assert "dynamics_grid_sha" not in dynamics_fields

        assert type(response) is ResponseKGridManifest
        assert response.torus_denominators == (8,)
        assert response.reciprocal_indices == ((1,),)
        assert response.direction_manifest.direction_ids == ("positive-axis",)
        assert response.direction_manifest.primitive_directions == ((1,),)
        assert response.direction_manifest.path_ids == ("positive-axis-path",)
        assert response.direction_manifest.ordered_paths == (((1,),),)
        assert response.direction_manifest.closure_path_pairs == ()
        assert response.direction_manifest.direction_manifest_sha == canonical_sha(
            direction_manifest_payload(response.direction_manifest)
        )
        assert response.response_grid_sha == canonical_sha(
            response_grid_payload(response)
        )
        assert candidate.response_reference_reciprocal_index == (1,)

        assert type(bridge) is BridgeKGridDerivationProtocolV1
        assert bridge.branch_roles == ("actual", "matched_ablated")
        assert bridge.spatial_shape == (8,)
        assert bridge.support_source == "live-verified-factory-signed-support"
        assert bridge.derivation_algorithm == "support-active-axes-origin-plus-pm1-v1"
        assert bridge.bridge_steps == (1, 2, 4)
        assert bridge.caller_supplied_points_allowed is False
        bridge_fields = {item.name for item in fields(type(bridge))}
        assert "bridge_grid" not in bridge_fields
        assert "bridge_grid_sha" not in bridge_fields


class TestC19RefreezeV2GeometryBundle:
    def test_freezes_ten_dimensional_conditional_geometry_without_outer_roots(
        self,
    ) -> None:
        from dataclasses import fields

        from rulespace_v3.c19_refreeze_v2 import (
            C19ObserverGeometryBundleV1,
            build_c19_refreeze_v2_candidate,
        )
        from rulespace_v3.factory import frozen_tensor_array

        candidate = build_c19_refreeze_v2_candidate()
        geometry = candidate.geometry_bundle

        assert type(geometry) is C19ObserverGeometryBundleV1
        assert (
            geometry.geometry_bundle_schema_version
            == "v3m0.c19-observer-geometry-bundle.v1"
        )
        assert geometry.kind == "C19_OBSERVER_COLLAPSE_CONDITIONS"
        assert geometry.claim_ceiling == "CONDITIONAL_PREREQUISITES_ONLY"
        assert geometry.evaluation_state == "NOT_EVALUATED_PRE_RESPONSE"
        assert (
            geometry.conditional_prediction_state
            == "CONDITIONAL_ANALYTIC_IDENTITY_ONLY"
        )
        assert (
            geometry.state_dim,
            geometry.ambient_h_dim,
            geometry.curvature_dim,
            geometry.tt_dim,
            geometry.gauge_dim,
            geometry.row_dim,
        ) == (20, 10, 6, 2, 4, 4)

        field_names = {item.name for item in fields(type(geometry))}
        forbidden = {
            "current_application_authority_v3_sha",
            "current_scenario_authority_v3_sha",
            "response_contract_v3_sha",
            "parent_freeze_v3_sha",
            "parent_candidate_v3_sha",
            "observed_residual",
            "scientific_verdict",
        }
        assert field_names.isdisjoint(forbidden)

        omega = frozen_tensor_array(geometry.omega_j20)
        b_plus = frozen_tensor_array(geometry.source_b_plus)
        readout = frozen_tensor_array(geometry.readout_p)
        tt = frozen_tensor_array(geometry.tt_basis)
        gauge = frozen_tensor_array(geometry.gauge_basis)
        row = frozen_tensor_array(geometry.row_basis)
        incidence = frozen_tensor_array(geometry.incidence_q)
        ker_c = frozen_tensor_array(geometry.ker_c_projector)
        curvature = frozen_tensor_array(geometry.curvature_frame)
        principal = frozen_tensor_array(geometry.conditional_principal_sine_squared)

        assert omega.shape == (20, 20)
        assert b_plus.shape == (20, 10)
        assert readout.shape == (10, 20)
        assert tt.shape == (10, 2)
        assert gauge.shape == (10, 4)
        assert row.shape == (10, 4)
        assert incidence.shape == (6, 10)
        assert ker_c.shape == (10, 10)
        assert curvature.shape == (10, 6)
        assert principal.shape == (6, 6)
        assert np.array_equal(omega.T, -omega)
        assert np.array_equal(np.einsum("ab,bc->ac", omega, omega), -np.eye(20))
        assert (
            np.linalg.norm(np.einsum("ab,bi->ai", omega, b_plus) - 1.0j * b_plus, ord=2)
            <= 1.0e-12
        )
        assert (
            np.linalg.norm(
                np.einsum("ia,aj->ij", readout, np.einsum("ab,bj->aj", omega, b_plus))
                - 1.0j * np.eye(10),
                ord=2,
            )
            <= 1.0e-12
        )
        complete = np.concatenate((tt, gauge, row), axis=1)
        assert np.array_equal(
            np.einsum("ai,aj->ij", complete.conj(), complete), np.eye(10)
        )
        assert np.array_equal(
            np.einsum("ia,ja->ij", incidence, incidence.conj()), np.eye(6)
        )
        assert np.array_equal(
            np.einsum("ia,aj->ij", incidence, gauge), np.zeros((6, 4))
        )
        assert np.array_equal(
            ker_c,
            np.einsum(
                "ai,bi->ab",
                complete[:, :6],
                complete[:, :6].conj(),
            ),
        )
        assert np.array_equal(curvature, incidence.conj().T)
        assert np.array_equal(principal, np.diag((0.0, 0.0, 1.0, 1.0, 1.0, 1.0)))
        assert geometry.conditional_principal_spectrum == (
            0.0,
            0.0,
            1.0,
            1.0,
            1.0,
            1.0,
        )

        identities = (
            (geometry.state_metric, 20),
            (geometry.state_whitener, 20),
            (geometry.source_metric, 10),
            (geometry.source_whitener, 10),
            (geometry.h_metric, 10),
            (geometry.h_whitener, 10),
            (geometry.curvature_metric, 6),
            (geometry.curvature_whitener, 6),
        )
        assert all(
            frozen_tensor_array(tensor).tobytes()
            == np.eye(dimension, dtype=np.complex128).tobytes()
            for tensor, dimension in identities
        )

        runtime = candidate.runtime_construction
        basis = candidate.basis_contract
        assert geometry.operation_dag_sha == runtime.construction_trace.trace_sha
        assert geometry.actual_slot_program_sha == runtime.actual_slot_program_sha
        assert geometry.matched_slot_program_sha == runtime.matched_slot_program_sha
        assert geometry.source_b_plus_sha == basis.source_selector_b_plus.tensor_sha
        assert geometry.readout_p_sha == basis.readout_selector_p.tensor_sha
        assert geometry.response_grid_sha == candidate.response_grid.response_grid_sha
        assert (
            geometry.dynamics_derivation_protocol_sha
            == candidate.dynamics_grid_derivation.protocol_sha
        )
        assert (
            geometry.bridge_derivation_protocol_sha
            == candidate.bridge_grid_derivation.protocol_sha
        )

    def test_strict_compiler_accepts_only_the_exact_conditional_v1_body(self) -> None:
        from dataclasses import replace

        from rulespace_v3.c19_refreeze import build_c19_local_refreeze_preflight
        from rulespace_v3.c19_refreeze_v2 import (
            C19ObserverGeometryBundleV1,
            build_c19_refreeze_v2_candidate,
            c19_observer_geometry_bundle_v1_payload,
            compile_c19_observer_geometry_bundle_v1,
        )
        from rulespace_v3.evidence import canonical_sha

        geometry = build_c19_refreeze_v2_candidate().geometry_bundle
        assert compile_c19_observer_geometry_bundle_v1(geometry) == geometry

        tampered = replace(
            geometry,
            evaluation_state="TRIGGERED",  # type: ignore[arg-type]
            geometry_bundle_sha="0" * 64,
        )
        tampered = replace(
            tampered,
            geometry_bundle_sha=canonical_sha(
                c19_observer_geometry_bundle_v1_payload(tampered)
            ),
        )
        with pytest.raises(ValueError):
            compile_c19_observer_geometry_bundle_v1(tampered)

        class GeometrySubclass(C19ObserverGeometryBundleV1):
            pass

        subclass = GeometrySubclass(**vars(geometry))
        with pytest.raises(TypeError):
            compile_c19_observer_geometry_bundle_v1(subclass)
        with pytest.raises(TypeError):
            compile_c19_observer_geometry_bundle_v1(  # type: ignore[arg-type]
                build_c19_local_refreeze_preflight()
            )


class TestC19RefreezeV2Attacks:
    def test_slot_deletion_with_complete_self_resigning_still_fails_closed(
        self,
    ) -> None:
        from dataclasses import replace

        from rulespace_v3.ablation import ablation_manifest_payload
        from rulespace_v3.c19_refreeze_v2 import (
            build_c19_refreeze_v2_candidate,
            c19_observer_geometry_bundle_v1_payload,
            c19_refreeze_v2_candidate_payload,
            c19_runtime_construction_v2_payload,
            verify_c19_refreeze_v2_candidate,
        )
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.factory import factory_sha, runtime_operator_sha

        candidate = build_c19_refreeze_v2_candidate()
        runtime = candidate.runtime_construction
        matched = runtime.matched_factory
        active = tuple(
            item
            for item in matched.primitives
            if item.operation_id == "local_canonical_shear"
        )
        active_slots = tuple(item.layer_slot_id for item in active)
        shortened = replace(
            matched,
            layer_slot_ids=active_slots,
            primitives=active,
            runtime_operator_sha=runtime_operator_sha(active),
            factory_sha="0" * 64,
        )
        shortened = replace(shortened, factory_sha=factory_sha(shortened))
        resigned_manifest = replace(
            runtime.ablation_manifest,
            ablated_factory_sha=shortened.factory_sha,
            manifest_sha="0" * 64,
        )
        resigned_manifest = replace(
            resigned_manifest,
            manifest_sha=canonical_sha(ablation_manifest_payload(resigned_manifest)),
        )
        shortened_program_sha = canonical_sha(
            {
                "branch": shortened.factory_role,
                "layer_slot_ids": list(shortened.layer_slot_ids),
                "runtime_operator_sha": shortened.runtime_operator_sha,
                "primitive_operation_ids": [
                    item.operation_id for item in shortened.primitives
                ],
            }
        )
        resigned_runtime = replace(
            runtime,
            matched_factory=shortened,
            ablation_manifest=resigned_manifest,
            matched_layer_slot_count=30,
            matched_primitive_count=30,
            matched_slot_program_sha=shortened_program_sha,
            construction_sha="0" * 64,
        )
        resigned_runtime = replace(
            resigned_runtime,
            construction_sha=canonical_sha(
                c19_runtime_construction_v2_payload(resigned_runtime)
            ),
        )
        resigned_geometry = replace(
            candidate.geometry_bundle,
            matched_layer_slot_count=30,
            matched_slot_program_sha=shortened_program_sha,
            geometry_bundle_sha="0" * 64,
        )
        resigned_geometry = replace(
            resigned_geometry,
            geometry_bundle_sha=canonical_sha(
                c19_observer_geometry_bundle_v1_payload(resigned_geometry)
            ),
        )
        attack = replace(
            candidate,
            runtime_construction=resigned_runtime,
            geometry_bundle=resigned_geometry,
            candidate_sha="0" * 64,
        )
        attack = replace(
            attack,
            candidate_sha=canonical_sha(c19_refreeze_v2_candidate_payload(attack)),
        )

        with pytest.raises(ValueError):
            verify_c19_refreeze_v2_candidate(attack)

    def test_unknown_verdict_outer_roots_subclasses_and_v1_fail_closed(self) -> None:
        from rulespace_v3.c19_refreeze import build_c19_local_refreeze_preflight
        from rulespace_v3.c19_refreeze_v2 import (
            C19RefreezeV2Candidate,
            build_c19_refreeze_v2_candidate,
            verify_c19_refreeze_v2_candidate,
        )

        candidate = build_c19_refreeze_v2_candidate()

        class CandidateSubclass(C19RefreezeV2Candidate):
            pass

        with pytest.raises(TypeError):
            verify_c19_refreeze_v2_candidate(CandidateSubclass(**vars(candidate)))
        with pytest.raises(TypeError):
            verify_c19_refreeze_v2_candidate(  # type: ignore[arg-type]
                build_c19_local_refreeze_preflight()
            )

        for field, value in (
            ("scientific_verdict", "PASS"),
            ("parent_freeze_v3_sha", "a" * 64),
            ("parent_candidate_v3_sha", "b" * 64),
        ):
            attacked = build_c19_refreeze_v2_candidate()
            vars(attacked.geometry_bundle)[field] = value
            with pytest.raises(ValueError):
                verify_c19_refreeze_v2_candidate(attacked)

        unknown_top_level = build_c19_refreeze_v2_candidate()
        vars(unknown_top_level)["permit_sha"] = "c" * 64
        with pytest.raises(ValueError):
            verify_c19_refreeze_v2_candidate(unknown_top_level)

    def test_unknown_fields_in_nested_runtime_records_fail_closed(self) -> None:
        from rulespace_v3.c19_refreeze_v2 import (
            build_c19_refreeze_v2_candidate,
            verify_c19_refreeze_v2_candidate,
        )

        candidate = build_c19_refreeze_v2_candidate()
        runtime = candidate.runtime_construction
        nested_records = (
            runtime.construction_trace,
            runtime.construction_trace.primitives[0],
            runtime.frozen_target.observation,
            runtime.actual_factory.interface,
            runtime.actual_factory.primitives[0],
            runtime.ablation_manifest.replacements[0],
        )
        for record in nested_records:
            vars(record)["forged_nested_authority"] = "a" * 64
            with pytest.raises(ValueError):
                verify_c19_refreeze_v2_candidate(candidate)
            del vars(record)["forged_nested_authority"]

    def test_self_hash_tamper_and_live_grid_injection_fail_closed(self) -> None:
        from dataclasses import replace

        from rulespace_v3.c19_refreeze_v2 import (
            build_c19_refreeze_v2_candidate,
            verify_c19_refreeze_v2_candidate,
        )

        candidate = build_c19_refreeze_v2_candidate()
        with pytest.raises(ValueError):
            verify_c19_refreeze_v2_candidate(replace(candidate, candidate_sha="f" * 64))

        vars(candidate.dynamics_grid_derivation)["dynamics_grid_sha"] = "d" * 64
        with pytest.raises(ValueError):
            verify_c19_refreeze_v2_candidate(candidate)

    def test_three_grid_type_swaps_and_resigned_role_swaps_fail_closed(self) -> None:
        from dataclasses import replace

        from rulespace_v3.c19_refreeze_v2 import (
            bridge_k_grid_derivation_protocol_v1_payload,
            build_c19_refreeze_v2_candidate,
            c19_refreeze_v2_candidate_payload,
            dynamics_k_grid_derivation_protocol_v1_payload,
            verify_c19_refreeze_v2_candidate,
        )
        from rulespace_v3.evidence import canonical_sha

        candidate = build_c19_refreeze_v2_candidate()
        typed_swaps = (
            replace(
                candidate,
                dynamics_grid_derivation=candidate.response_grid,  # type: ignore[arg-type]
            ),
            replace(
                candidate,
                response_grid=candidate.bridge_grid_derivation,  # type: ignore[arg-type]
            ),
            replace(
                candidate,
                bridge_grid_derivation=candidate.dynamics_grid_derivation,  # type: ignore[arg-type]
            ),
        )
        for attack in typed_swaps:
            with pytest.raises(TypeError):
                verify_c19_refreeze_v2_candidate(attack)

        reversed_dynamics = replace(
            candidate.dynamics_grid_derivation,
            branch_roles=("matched_ablated", "actual"),
            protocol_sha="0" * 64,
        )
        reversed_dynamics = replace(
            reversed_dynamics,
            protocol_sha=canonical_sha(
                dynamics_k_grid_derivation_protocol_v1_payload(reversed_dynamics)
            ),
        )
        reversed_bridge = replace(
            candidate.bridge_grid_derivation,
            branch_roles=("matched_ablated", "actual"),
            protocol_sha="0" * 64,
        )
        reversed_bridge = replace(
            reversed_bridge,
            protocol_sha=canonical_sha(
                bridge_k_grid_derivation_protocol_v1_payload(reversed_bridge)
            ),
        )
        for field, drifted_protocol in (
            ("dynamics_grid_derivation", reversed_dynamics),
            ("bridge_grid_derivation", reversed_bridge),
        ):
            attack = replace(
                candidate,
                **{field: drifted_protocol},
                candidate_sha="0" * 64,
            )
            attack = replace(
                attack,
                candidate_sha=canonical_sha(c19_refreeze_v2_candidate_payload(attack)),
            )
            with pytest.raises(ValueError):
                verify_c19_refreeze_v2_candidate(attack)

    def test_executable_p_as_raw_scenario_readout_with_resigning_fails_closed(
        self,
    ) -> None:
        from dataclasses import replace

        from rulespace_v3.c19_refreeze_v2 import (
            build_c19_refreeze_v2_candidate,
            c19_basis_contract_v2_payload,
            c19_refreeze_v2_candidate_payload,
            verify_c19_refreeze_v2_candidate,
        )
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.factory import (
            build_basis_manifest,
            frozen_tensor_array,
        )

        candidate = build_c19_refreeze_v2_candidate()
        basis = candidate.basis_contract
        executable_p = frozen_tensor_array(basis.readout_selector_p)
        wrong_raw_readout = build_basis_manifest(
            role="readout",
            state_schema_id=basis.state_schema_id,
            channel_order=basis.channel_order,
            vectors=executable_p,
        )
        assert (
            wrong_raw_readout.vectors_wire != basis.scenario_readout_basis.vectors_wire
        )
        resigned_basis = replace(
            basis,
            scenario_readout_basis=wrong_raw_readout,
            basis_contract_sha="0" * 64,
        )
        resigned_basis = replace(
            resigned_basis,
            basis_contract_sha=canonical_sha(
                c19_basis_contract_v2_payload(resigned_basis)
            ),
        )
        attack = replace(
            candidate,
            basis_contract=resigned_basis,
            candidate_sha="0" * 64,
        )
        attack = replace(
            attack,
            candidate_sha=canonical_sha(c19_refreeze_v2_candidate_payload(attack)),
        )
        with pytest.raises(ValueError):
            verify_c19_refreeze_v2_candidate(attack)

    def test_resigned_claim_upgrade_fails_closed(self) -> None:
        from dataclasses import replace

        from rulespace_v3.c19_refreeze_v2 import (
            build_c19_refreeze_v2_candidate,
            c19_refreeze_v2_candidate_payload,
            verify_c19_refreeze_v2_candidate,
        )
        from rulespace_v3.evidence import canonical_sha

        candidate = build_c19_refreeze_v2_candidate()
        drifts = (
            {"claim_ceiling": "PHYSICAL_ANCHOR"},
            {"causal_contrast_role": "IDENTIFIABLE_CAUSAL_CONTRAST"},
            {"physical_anchor_eligibility": "ELIGIBLE"},
            {"family_eligibility": "ELIGIBLE"},
        )
        for drift in drifts:
            attack = replace(  # type: ignore[arg-type]
                candidate,
                **drift,
                candidate_sha="0" * 64,
            )
            attack = replace(
                attack,
                candidate_sha=canonical_sha(c19_refreeze_v2_candidate_payload(attack)),
            )
            with pytest.raises(ValueError):
                verify_c19_refreeze_v2_candidate(attack)

    def test_module_exposes_no_parent_permit_evidence_or_hydration_issuer(self) -> None:
        import rulespace_v3.c19_refreeze_v2 as module

        forbidden_fragments = ("parent", "permit", "evidence", "hydrate", "issue")
        public_names = tuple(name.lower() for name in module.__all__)
        assert all(
            fragment not in name
            for name in public_names
            for fragment in forbidden_fragments
        )
