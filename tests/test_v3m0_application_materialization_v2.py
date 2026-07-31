"""Exact-contract and fail-closed tests for scenario materialization v2."""

from __future__ import annotations

import copy
import inspect
from dataclasses import fields, replace
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np


class ApplicationMaterializationV2ContractTests(unittest.TestCase):
    def _c04_private_upstream(self):
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_freeze import (
            build_v3m0_parent_freeze_candidate,
            issue_v3m0_parent_freeze,
        )
        from rulespace_v3.parent_freeze_v2 import (
            _build_reviewed_unchanged_scenario_authorities,
        )
        from rulespace_v3.parent_v2_contracts import (
            CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION,
            CurrentApplicationAuthorityV2,
            current_application_authority_v2_payload,
        )

        historical = issue_v3m0_parent_freeze().manifest
        candidate = build_v3m0_parent_freeze_candidate()
        scenario = next(
            item
            for item in _build_reviewed_unchanged_scenario_authorities()
            if item.control_case_id == "C04_CANONICAL_ANGLE_025_075"
        )
        candidate_application = next(
            item
            for item in candidate.application_candidates
            if item.control_case_id == scenario.control_case_id
        )
        provisional = CurrentApplicationAuthorityV2(
            application_authority_schema_version=(
                CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION
            ),
            authority_state="CURRENT_REVIEWED_APPLICATION",
            control_case_id=scenario.control_case_id,
            application_instance_id=scenario.application_instance_id,
            based_on_application_spec_sha=scenario.based_on_application_spec_sha,
            source_candidate_v1_application_sha=(
                candidate_application.candidate_application_sha
            ),
            complete_scenario_execution_specs=tuple(
                item.scenario_execution_spec
                for item in candidate_application.scenario_candidates
            ),
            scenario_authorities=(scenario,),
            application_authority_sha="0" * 64,
        )
        application = replace(
            provisional,
            application_authority_sha=canonical_sha(
                current_application_authority_v2_payload(provisional)
            ),
        )
        parent_sha = "a" * 64
        parent_manifest = SimpleNamespace(
            parent_freeze_v2_sha=parent_sha,
            historical_parent_v1=historical,
            reviewed_candidate_v1=candidate,
            reviewed_candidate_v2=None,
            current_application_authorities=(application,),
        )
        permit = SimpleNamespace(
            parent_freeze_v2_sha=parent_sha,
            permit_sha="b" * 64,
            control_case_id=application.control_case_id,
            application_authority=application,
            scenario_authority_shas=(scenario.scenario_authority_sha,),
            selected_fejer_order=256,
        )
        return parent_manifest, permit, scenario

    def _c05_private_upstream(self):
        from rulespace_v3.c05_projector_recipe import (
            C05_PROJECTOR_RECIPE_STATE,
            build_c05_projector_orientation_recipe,
        )
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.parent_candidate_v2 import (
            PARENT_CANDIDATE_V2_BINDING_SCHEMA_VERSION,
            CandidateConstructionPreflightBinding,
            _build_scenario_refreeze,
            _C05_RECIPE_COMMIT_SHA,
            _C05_RECIPE_SOURCE_PATH,
            _C05_RECIPE_SOURCE_SHA,
            _finish_binding,
        )
        from rulespace_v3.parent_freeze import (
            build_v3m0_parent_freeze_candidate,
            issue_v3m0_parent_freeze,
        )
        from rulespace_v3.parent_freeze_v2 import (
            _build_response_contract_from_refreeze,
        )
        from rulespace_v3.parent_v2_contracts import (
            CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION,
            CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION,
            CurrentApplicationAuthorityV2,
            CurrentScenarioAuthorityV2,
            current_application_authority_v2_payload,
            current_scenario_authority_v2_payload,
        )

        historical = issue_v3m0_parent_freeze().manifest
        candidate = build_v3m0_parent_freeze_candidate()
        candidate_application = next(
            item
            for item in candidate.application_candidates
            if item.control_case_id == "C05_PHASE_AND_SCALAR_GAIN"
        )
        authorities = []
        refreezes = []
        for candidate_scenario in candidate_application.scenario_candidates:
            execution = candidate_scenario.scenario_execution_spec
            if execution.execution_lane != "BLOCK_SUCCESS":
                continue
            kind = "phase" if execution.scenario_id.endswith(".phase.v1") else "gain"
            recipe = build_c05_projector_orientation_recipe(kind)
            binding = _finish_binding(
                CandidateConstructionPreflightBinding(
                    binding_schema_version=(PARENT_CANDIDATE_V2_BINDING_SCHEMA_VERSION),
                    scenario_id=execution.scenario_id,
                    preflight_kind="C05_PROJECTOR_RECIPE",
                    source_path=_C05_RECIPE_SOURCE_PATH,
                    source_sha=_C05_RECIPE_SOURCE_SHA,
                    source_commit_sha=_C05_RECIPE_COMMIT_SHA,
                    candidate_v1_sha=candidate.candidate_sha,
                    candidate_application_sha=(
                        candidate_application.candidate_application_sha
                    ),
                    candidate_scenario_sha=(candidate_scenario.candidate_scenario_sha),
                    scenario_execution_spec_sha=execution.scenario_sha,
                    based_on_application_spec_sha=(
                        candidate_scenario.based_on_application_spec_sha
                    ),
                    preflight_state=C05_PROJECTOR_RECIPE_STATE,
                    preflight_artifact_sha=recipe.recipe_sha,
                    derivation_or_recipe_sha=recipe.recipe_sha,
                    binding_sha="0" * 64,
                )
            )
            refreeze = _build_scenario_refreeze(candidate, binding)
            response = _build_response_contract_from_refreeze(refreeze)
            provisional = CurrentScenarioAuthorityV2(
                scenario_authority_schema_version=(
                    CURRENT_SCENARIO_AUTHORITY_SCHEMA_VERSION
                ),
                authority_state="CURRENT_REVIEWED_SCENARIO",
                control_case_id=candidate_application.control_case_id,
                application_instance_id=(candidate_application.application_instance_id),
                based_on_application_spec_sha=(
                    candidate_application.based_on_application_spec_sha
                ),
                scenario_id=execution.scenario_id,
                scenario_execution_spec=execution,
                source_disposition="CANDIDATE_V2_REVIEWED_MODIFIED",
                source_candidate_v1_scenario_sha=(
                    candidate_scenario.candidate_scenario_sha
                ),
                source_candidate_v2_refreeze_sha=refreeze.scenario_refreeze_sha,
                response_contract=response,
                scenario_authority_sha="0" * 64,
            )
            authorities.append(
                replace(
                    provisional,
                    scenario_authority_sha=canonical_sha(
                        current_scenario_authority_v2_payload(provisional)
                    ),
                )
            )
            refreezes.append(refreeze)
        application_provisional = CurrentApplicationAuthorityV2(
            application_authority_schema_version=(
                CURRENT_APPLICATION_AUTHORITY_SCHEMA_VERSION
            ),
            authority_state="CURRENT_REVIEWED_APPLICATION",
            control_case_id=candidate_application.control_case_id,
            application_instance_id=candidate_application.application_instance_id,
            based_on_application_spec_sha=(
                candidate_application.based_on_application_spec_sha
            ),
            source_candidate_v1_application_sha=(
                candidate_application.candidate_application_sha
            ),
            complete_scenario_execution_specs=tuple(
                item.scenario_execution_spec
                for item in candidate_application.scenario_candidates
            ),
            scenario_authorities=tuple(authorities),
            application_authority_sha="0" * 64,
        )
        application = replace(
            application_provisional,
            application_authority_sha=canonical_sha(
                current_application_authority_v2_payload(application_provisional)
            ),
        )
        parent_sha = "d" * 64
        parent_manifest = SimpleNamespace(
            parent_freeze_v2_sha=parent_sha,
            historical_parent_v1=historical,
            reviewed_candidate_v1=candidate,
            reviewed_candidate_v2=SimpleNamespace(scenario_refreezes=tuple(refreezes)),
            current_application_authorities=(application,),
        )
        permit = SimpleNamespace(
            parent_freeze_v2_sha=parent_sha,
            permit_sha="e" * 64,
            control_case_id=application.control_case_id,
            application_authority=application,
            scenario_authority_shas=tuple(
                item.scenario_authority_sha for item in authorities
            ),
            selected_fejer_order=256,
        )
        return parent_manifest, permit, tuple(authorities)

    def _resign_step(self, value):
        from rulespace_v3.application_materialization_v2 import (
            scenario_local_shear_step_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, step_sha="0" * 64)
        return replace(
            provisional,
            step_sha=canonical_sha(scenario_local_shear_step_v2_payload(provisional)),
        )

    def _resign_effect(self, value):
        from rulespace_v3.application_materialization_v2 import (
            scenario_construction_effect_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(
            value,
            program_sha="0" * 64,
            effect_digest="0" * 64,
        )
        program_sha = canonical_sha(
            {
                "scenario_id": provisional.scenario_id,
                "branch": provisional.branch,
                "ordered_step_shas": [
                    item.step_sha for item in provisional.ordered_steps
                ],
            }
        )
        provisional = replace(provisional, program_sha=program_sha)
        return replace(
            provisional,
            effect_digest=canonical_sha(
                scenario_construction_effect_v2_payload(provisional)
            ),
        )

    def _resign_recipe(self, value):
        from rulespace_v3.application_materialization_v2 import (
            scenario_construction_recipe_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, recipe_sha="0" * 64)
        return replace(
            provisional,
            recipe_sha=canonical_sha(
                scenario_construction_recipe_v2_payload(provisional)
            ),
        )

    def _resign_trace(self, value):
        from rulespace_v3.application_materialization_v2 import (
            scenario_construction_trace_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, construction_trace_sha="0" * 64)
        return replace(
            provisional,
            construction_trace_sha=canonical_sha(
                scenario_construction_trace_v2_payload(provisional)
            ),
        )

    def _resign_factory_binding(self, value):
        from rulespace_v3.application_materialization_v2 import (
            scenario_factory_binding_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, factory_binding_sha="0" * 64)
        return replace(
            provisional,
            factory_binding_sha=canonical_sha(
                scenario_factory_binding_v2_payload(provisional)
            ),
        )

    def _resign_materialization(self, value):
        from rulespace_v3.application_materialization_v2 import (
            application_scenario_materialization_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, materialization_v2_sha="0" * 64)
        return replace(
            provisional,
            materialization_v2_sha=canonical_sha(
                application_scenario_materialization_v2_payload(provisional)
            ),
        )

    def _body(self):
        from rulespace_v3.application_materialization_v2 import (
            APPLICATION_SCENARIO_MATERIALIZATION_V2_SCHEMA_VERSION,
            SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION,
            SCENARIO_CONSTRUCTION_RECIPE_V2_SCHEMA_VERSION,
            SCENARIO_CONSTRUCTION_TRACE_V2_SCHEMA_VERSION,
            SCENARIO_FACTORY_BINDING_V2_SCHEMA_VERSION,
            SCENARIO_LOCAL_SHEAR_STEP_V2_SCHEMA_VERSION,
            ApplicationScenarioMaterializationV2,
            ScenarioConstructionEffectV2,
            ScenarioConstructionRecipeV2,
            ScenarioConstructionTraceV2,
            ScenarioFactoryBindingV2,
            ScenarioLocalShearStepV2,
            scenario_selector_v2_sha,
        )
        from rulespace_v3.factory import (
            build_basis_manifest,
            freeze_complex_tensor,
        )

        scenario_id = "v3m0.calibration.c07.application.main.scenario.constructive.v2"
        scenario_sha = "1" * 64
        channels = ("q", "p")
        state_schema = "v3m0.test.state.v1"
        common_source = build_basis_manifest(
            role="source",
            state_schema_id=state_schema,
            channel_order=channels,
            vectors=np.eye(2, dtype=np.complex128),
        )
        common_readout = build_basis_manifest(
            role="readout",
            state_schema_id=state_schema,
            channel_order=channels,
            vectors=np.asarray(((1j, 0.0), (0.0, 1.0)), dtype=np.complex128),
        )
        source_selector = freeze_complex_tensor(
            np.asarray(((0.0,), (1.0,)), dtype=np.complex128)
        )
        readout_selector = freeze_complex_tensor(
            np.asarray(((1.0, 0.0),), dtype=np.complex128)
        )
        source_injection = freeze_complex_tensor(
            np.asarray(((0.0,), (1.0,)), dtype=np.complex128)
        )
        readout_coisometry = freeze_complex_tensor(
            np.asarray(((-1j, 0.0),), dtype=np.complex128)
        )
        scenario_source_basis = build_basis_manifest(
            role="source",
            state_schema_id=state_schema,
            channel_order=channels,
            vectors=np.asarray(((0.0, 1.0),), dtype=np.complex128),
        )
        scenario_readout_basis = build_basis_manifest(
            role="readout",
            state_schema_id=state_schema,
            channel_order=channels,
            vectors=np.asarray(((1j, 0.0),), dtype=np.complex128),
        )

        blind = ScenarioLocalShearStepV2(
            step_schema_version=SCENARIO_LOCAL_SHEAR_STEP_V2_SCHEMA_VERSION,
            scenario_id=scenario_id,
            step_id="blind-000",
            ordinal=0,
            source_channel="q",
            destination_channel="p",
            offset=(0,),
            coefficient_wire=(1.0, 0.0),
            target_conditioned=False,
            step_sha="0" * 64,
        )
        blind = self._resign_step(blind)
        conditioned = ScenarioLocalShearStepV2(
            step_schema_version=SCENARIO_LOCAL_SHEAR_STEP_V2_SCHEMA_VERSION,
            scenario_id=scenario_id,
            step_id="conditioned-001",
            ordinal=1,
            source_channel="p",
            destination_channel="q",
            offset=(1,),
            coefficient_wire=(0.5, 0.0),
            target_conditioned=True,
            step_sha="0" * 64,
        )
        conditioned = self._resign_step(conditioned)
        actual_effect = ScenarioConstructionEffectV2(
            effect_schema_version=SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION,
            branch="actual",
            scenario_id=scenario_id,
            scenario_sha=scenario_sha,
            construction_rule_id="c07-interference-local-shear-v2",
            construction_family_id="c07-interference-family-v2",
            ordered_steps=(blind, conditioned),
            program_sha="0" * 64,
            effect_digest="0" * 64,
        )
        actual_effect = self._resign_effect(actual_effect)
        matched_effect = ScenarioConstructionEffectV2(
            effect_schema_version=SCENARIO_CONSTRUCTION_EFFECT_V2_SCHEMA_VERSION,
            branch="matched_ablated",
            scenario_id=scenario_id,
            scenario_sha=scenario_sha,
            construction_rule_id="c07-interference-local-shear-v2",
            construction_family_id="c07-interference-family-v2",
            ordered_steps=(blind,),
            program_sha="0" * 64,
            effect_digest="0" * 64,
        )
        matched_effect = self._resign_effect(matched_effect)
        selector_sha = scenario_selector_v2_sha(
            source_selector,
            readout_selector,
        )
        recipe = ScenarioConstructionRecipeV2(
            recipe_schema_version=SCENARIO_CONSTRUCTION_RECIPE_V2_SCHEMA_VERSION,
            recipe_state="FORMAL_SCENARIO_AUTHORITY_DERIVED",
            formal_parent_v2_sha="2" * 64,
            permit_v2_sha="3" * 64,
            application_spec_sha="4" * 64,
            scenario_authority_sha="5" * 64,
            response_contract_sha="6" * 64,
            control_case_id="C07",
            application_instance_id="v3m0.calibration.c07.application.main.v2",
            scenario_id=scenario_id,
            scenario_sha=scenario_sha,
            selector_sha=selector_sha,
            operation_dag_sha="7" * 64,
            compiled_contract_sha="8" * 64,
            construction_rule_id="c07-interference-local-shear-v2",
            construction_family_id="c07-interference-family-v2",
            primitive_support_radius=1,
            uses_global_fft_projection=False,
            uses_per_k_time_step_projector=False,
            source_selector=source_selector,
            readout_selector=readout_selector,
            actual_effect=actual_effect,
            matched_ablated_effect=matched_effect,
            recipe_sha="0" * 64,
        )
        recipe = self._resign_recipe(recipe)
        trace = ScenarioConstructionTraceV2(
            trace_schema_version=SCENARIO_CONSTRUCTION_TRACE_V2_SCHEMA_VERSION,
            trace_state="FORMAL_RECIPE_REPLAYED_PRE_EVOLUTION",
            scenario_id=scenario_id,
            scenario_sha=scenario_sha,
            recipe_sha=recipe.recipe_sha,
            operation_dag_sha=recipe.operation_dag_sha,
            compiled_contract_sha=recipe.compiled_contract_sha,
            construction_rule_id=recipe.construction_rule_id,
            construction_family_id=recipe.construction_family_id,
            target_spec_id="v3m0.test.carrier.v1",
            target_spec_sha="9" * 64,
            interface_sha="a" * 64,
            state_schema_id=state_schema,
            channel_order=channels,
            state_shape=(2, 8),
            dt=0.125,
            target_blind_parameters=(("selected_fejer_order", 256.0),),
            boundary_manifest_id="periodic-v1",
            actual_step_shas=tuple(
                item.step_sha for item in actual_effect.ordered_steps
            ),
            matched_ablated_step_shas=tuple(
                item.step_sha for item in matched_effect.ordered_steps
            ),
            actual_program_sha=actual_effect.program_sha,
            matched_ablated_program_sha=matched_effect.program_sha,
            actual_effect_digest=actual_effect.effect_digest,
            matched_ablated_effect_digest=matched_effect.effect_digest,
            construction_trace_sha="0" * 64,
        )
        trace = self._resign_trace(trace)

        def binding(branch, effect, factory_sha, runtime_sha):
            value = ScenarioFactoryBindingV2(
                binding_schema_version=SCENARIO_FACTORY_BINDING_V2_SCHEMA_VERSION,
                branch=branch,
                scenario_id=scenario_id,
                scenario_sha=scenario_sha,
                recipe_sha=recipe.recipe_sha,
                construction_trace_sha=trace.construction_trace_sha,
                program_sha=effect.program_sha,
                effect_digest=effect.effect_digest,
                factory_sha=factory_sha,
                runtime_operator_sha=runtime_sha,
                interface_sha=trace.interface_sha,
                state_schema_id=state_schema,
                state_shape=(2, 8),
                source_manifest_id=scenario_source_basis.manifest_id,
                readout_manifest_id=scenario_readout_basis.manifest_id,
                factory_binding_sha="0" * 64,
            )
            return self._resign_factory_binding(value)

        actual_binding = binding(
            "actual",
            actual_effect,
            "b" * 64,
            "c" * 64,
        )
        matched_binding = binding(
            "matched_ablated",
            matched_effect,
            "d" * 64,
            "e" * 64,
        )
        body = ApplicationScenarioMaterializationV2(
            materialization_schema_version=(
                APPLICATION_SCENARIO_MATERIALIZATION_V2_SCHEMA_VERSION
            ),
            materialization_state="FORMAL_PARENT_V2_LIVE_MATERIALIZED",
            formal_parent_v2_sha=recipe.formal_parent_v2_sha,
            permit_v2_sha=recipe.permit_v2_sha,
            application_authority_sha="f" * 64,
            application_spec_sha=recipe.application_spec_sha,
            control_case_id=recipe.control_case_id,
            application_instance_id=recipe.application_instance_id,
            scenario_authority_sha=recipe.scenario_authority_sha,
            response_contract_sha=recipe.response_contract_sha,
            scenario_id=scenario_id,
            scenario_sha=scenario_sha,
            selected_fejer_order=256,
            common_source_basis=common_source,
            common_readout_basis=common_readout,
            scenario_recipe=recipe,
            scenario_source_injection=source_injection,
            scenario_readout_coisometry=readout_coisometry,
            scenario_source_basis=scenario_source_basis,
            scenario_readout_basis=scenario_readout_basis,
            construction_trace=trace,
            actual_factory_binding=actual_binding,
            matched_ablated_factory_binding=matched_binding,
            materialization_v2_sha="0" * 64,
        )
        return self._resign_materialization(body)

    def test_schema_and_public_surface_are_closed(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            ApplicationScenarioMaterializationV2,
            VerifiedV3M0ApplicationScenarioMaterializationV2,
            materialize_v3m0_application_scenario_v2,
            verify_v3m0_application_scenario_materialization_v2,
        )

        names = {item.name for item in fields(ApplicationScenarioMaterializationV2)}
        for required in (
            "formal_parent_v2_sha",
            "permit_v2_sha",
            "scenario_authority_sha",
            "response_contract_sha",
            "common_source_basis",
            "common_readout_basis",
            "scenario_recipe",
            "scenario_source_injection",
            "scenario_readout_coisometry",
            "scenario_source_basis",
            "scenario_readout_basis",
            "construction_trace",
            "actual_factory_binding",
            "matched_ablated_factory_binding",
            "materialization_v2_sha",
        ):
            self.assertIn(required, names)
        self.assertEqual(
            tuple(
                inspect.signature(materialize_v3m0_application_scenario_v2).parameters
            ),
            ("formal_parent_v2", "permit_v2", "scenario_id"),
        )
        self.assertEqual(
            tuple(
                inspect.signature(
                    verify_v3m0_application_scenario_materialization_v2
                ).parameters
            ),
            ("value",),
        )
        self.assertFalse(
            hasattr(VerifiedV3M0ApplicationScenarioMaterializationV2, "hydrate")
        )

    def test_delayed_permit_wiring_uses_v2_public_consumer(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            VerifiedCalibrationApplicationPermitV2,
        )
        from rulespace_v3.application_materialization_v2 import (
            _require_exact_live_upstream,
        )
        from rulespace_v3.parent_authority import VerifiedParentFreezeV2

        with self.assertRaisesRegex(ValueError, "live registry"):
            _require_exact_live_upstream(
                object.__new__(VerifiedParentFreezeV2),
                object.__new__(VerifiedCalibrationApplicationPermitV2),
            )

    def test_private_replayer_compiles_c04_to_the_live_matched_pair(self) -> None:
        import rulespace_v3.application_materialization_v2 as materialization_v2
        from rulespace_v3.factory import _reverify_verified_factory

        self.assertTrue(
            hasattr(materialization_v2, "_make_expected_live_materialization_v2"),
            "private dependency-injected exact replayer is not implemented",
        )
        _make_expected_live_materialization_v2 = (
            materialization_v2._make_expected_live_materialization_v2
        )

        parent_manifest, permit, scenario = self._c04_private_upstream()
        parent_token = object()
        permit_token = object()
        replayer = _make_expected_live_materialization_v2(
            lambda parent, live_permit: (
                (
                    parent_manifest,
                    permit,
                )
                if (parent, live_permit) == (parent_token, permit_token)
                else (_ for _ in ()).throw(ValueError("unexpected injected upstream"))
            )
        )

        replay = replayer(parent_token, permit_token, scenario.scenario_id)
        body = replay.materialization
        actual = _reverify_verified_factory(replay.actual_factory)
        matched = _reverify_verified_factory(replay.matched_ablated_factory)

        self.assertEqual(
            body.formal_parent_v2_sha, parent_manifest.parent_freeze_v2_sha
        )
        self.assertEqual(body.permit_v2_sha, permit.permit_sha)
        self.assertEqual(body.scenario_authority_sha, scenario.scenario_authority_sha)
        self.assertEqual(
            body.response_contract_sha,
            scenario.response_contract.response_contract_sha,
        )
        self.assertEqual(actual.role, "actual")
        self.assertEqual(matched.role, "matched_ablated")
        self.assertIs(replay.ablation_outcome.pair.actual, replay.actual_factory)
        self.assertIs(
            replay.ablation_outcome.pair.ablated,
            replay.matched_ablated_factory,
        )
        self.assertEqual(
            actual.factory.factory_sha,
            body.actual_factory_binding.factory_sha,
        )
        self.assertEqual(
            matched.factory.factory_sha,
            body.matched_ablated_factory_binding.factory_sha,
        )

    def test_private_replayer_rejects_parent_application_and_scenario_splices(
        self,
    ) -> None:
        from rulespace_v3.application_materialization_v2 import (
            _make_expected_live_materialization_v2,
        )

        parent_manifest, permit, scenario = self._c04_private_upstream()

        def replay_with(candidate_permit):
            return _make_expected_live_materialization_v2(
                lambda parent, live_permit: (parent_manifest, candidate_permit)
            )(object(), object(), scenario.scenario_id)

        with self.assertRaisesRegex(ValueError, "Parent-v2 roots"):
            replay_with(
                SimpleNamespace(
                    **{
                        **vars(permit),
                        "parent_freeze_v2_sha": "c" * 64,
                    }
                )
            )
        with self.assertRaisesRegex(ValueError, "permit-v2 body"):
            replay_with(
                SimpleNamespace(
                    **{
                        **vars(permit),
                        "control_case_id": "C99_HOSTILE_SPLICE",
                    }
                )
            )
        with self.assertRaisesRegex(ValueError, "BLOCK_SUCCESS scenario"):
            _make_expected_live_materialization_v2(
                lambda parent, live_permit: (parent_manifest, permit)
            )(object(), object(), "v3m0.hostile.cross-scenario")

        hostile_application = replace(
            permit.application_authority,
            application_authority_sha="f" * 64,
        )
        hostile_parent = SimpleNamespace(
            **{
                **vars(parent_manifest),
                "current_application_authorities": (hostile_application,),
            }
        )
        hostile_permit = SimpleNamespace(
            **{
                **vars(permit),
                "application_authority": hostile_application,
            }
        )
        with self.assertRaisesRegex(ValueError, "application-authority SHA"):
            _make_expected_live_materialization_v2(
                lambda parent, live_permit: (hostile_parent, hostile_permit)
            )(object(), object(), scenario.scenario_id)

    def test_private_replayer_compiles_reviewed_candidate_v2_recipe(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            _make_expected_live_materialization_v2,
        )

        parent_manifest, permit, authorities = self._c05_private_upstream()
        scenario = authorities[0]
        replay = _make_expected_live_materialization_v2(
            lambda parent, live_permit: (parent_manifest, permit)
        )(object(), object(), scenario.scenario_id)

        self.assertEqual(
            replay.materialization.scenario_id,
            scenario.scenario_id,
        )
        self.assertEqual(
            replay.materialization.scenario_recipe.operation_dag_sha,
            scenario.response_contract.operation_dag_sha,
        )
        self.assertIs(replay.ablation_outcome.pair.actual, replay.actual_factory)
        self.assertIs(
            replay.ablation_outcome.pair.ablated,
            replay.matched_ablated_factory,
        )

    def test_private_replayer_rejects_candidate_v2_refreeze_splices(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            _make_expected_live_materialization_v2,
        )

        parent_manifest, permit, authorities = self._c05_private_upstream()
        scenario = authorities[0]
        refreezes = parent_manifest.reviewed_candidate_v2.scenario_refreezes

        cross_scenario_parent = SimpleNamespace(
            **{
                **vars(parent_manifest),
                "reviewed_candidate_v2": SimpleNamespace(
                    scenario_refreezes=(refreezes[1],)
                ),
            }
        )
        with self.assertRaisesRegex(
            ValueError,
            "candidate-v2 scenario refreeze does not resolve",
        ):
            _make_expected_live_materialization_v2(
                lambda parent, live_permit: (
                    cross_scenario_parent,
                    permit,
                )
            )(object(), object(), scenario.scenario_id)

        drifted_refreeze = replace(
            refreezes[0],
            scenario_refreeze_sha="f" * 64,
        )
        hash_drift_parent = SimpleNamespace(
            **{
                **vars(parent_manifest),
                "reviewed_candidate_v2": SimpleNamespace(
                    scenario_refreezes=(drifted_refreeze, refreezes[1])
                ),
            }
        )
        with self.assertRaisesRegex(ValueError, "scenario-refreeze SHA"):
            _make_expected_live_materialization_v2(
                lambda parent, live_permit: (hash_drift_parent, permit)
            )(object(), object(), scenario.scenario_id)

    def test_public_api_captures_its_fail_closed_replayer(self) -> None:
        import rulespace_v3.application_materialization_v2 as materialization_v2

        with mock.patch.object(
            materialization_v2,
            "_expected_live_materialization_v2",
            side_effect=AssertionError("module-global rebind was consumed"),
        ) as rebound:
            with self.assertRaises(
                (
                    TypeError,
                    materialization_v2.ApplicationMaterializationV2UpstreamUnavailable,
                )
            ):
                materialization_v2.materialize_v3m0_application_scenario_v2(
                    object(),
                    object(),
                    "v3m0.synthetic-control.c04.v1.scenario.canonical-angle.v1",
                )
        rebound.assert_not_called()

    def test_exact_body_replays_scenario_selectors_and_factories(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            verify_application_scenario_materialization_v2_body,
        )

        body = self._body()
        self.assertIs(verify_application_scenario_materialization_v2_body(body), body)

    def test_case_basis_cannot_override_scenario_selector(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            verify_application_scenario_materialization_v2_body,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        body = self._body()
        hostile = replace(
            body,
            scenario_source_injection=freeze_complex_tensor(
                np.asarray(((1.0,), (0.0,)), dtype=np.complex128)
            ),
        )
        hostile = self._resign_materialization(hostile)
        with self.assertRaisesRegex(ValueError, "scenario_source_injection"):
            verify_application_scenario_materialization_v2_body(hostile)

        hostile = replace(
            body,
            scenario_source_basis=body.common_source_basis,
        )
        hostile = self._resign_materialization(hostile)
        with self.assertRaisesRegex(
            ValueError,
            "scenario source basis|forced common case basis",
        ):
            verify_application_scenario_materialization_v2_body(hostile)

    def test_resigned_recipe_and_effect_splices_fail(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            verify_application_scenario_materialization_v2_body,
        )

        body = self._body()
        hostile_effect = replace(
            body.scenario_recipe.actual_effect,
            scenario_sha="0" * 64,
        )
        hostile_effect = self._resign_effect(hostile_effect)
        hostile_recipe = self._resign_recipe(
            replace(body.scenario_recipe, actual_effect=hostile_effect)
        )
        hostile = self._resign_materialization(
            replace(body, scenario_recipe=hostile_recipe)
        )
        with self.assertRaisesRegex(ValueError, "effect.*spliced"):
            verify_application_scenario_materialization_v2_body(hostile)

        hostile_recipe = self._resign_recipe(
            replace(
                body.scenario_recipe,
                scenario_id="v3m0.hostile.scenario",
            )
        )
        hostile = self._resign_materialization(
            replace(body, scenario_recipe=hostile_recipe)
        )
        with self.assertRaisesRegex(ValueError, "recipe.*spliced"):
            verify_application_scenario_materialization_v2_body(hostile)

    def test_resigned_cross_scenario_factory_binding_fails(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            verify_application_scenario_materialization_v2_body,
        )

        body = self._body()
        hostile_binding = self._resign_factory_binding(
            replace(
                body.matched_ablated_factory_binding,
                scenario_id="v3m0.hostile.scenario",
            )
        )
        hostile = self._resign_materialization(
            replace(body, matched_ablated_factory_binding=hostile_binding)
        )
        with self.assertRaisesRegex(ValueError, "factory.*spliced"):
            verify_application_scenario_materialization_v2_body(hostile)

        hostile_binding = self._resign_factory_binding(
            replace(
                body.actual_factory_binding,
                effect_digest=body.matched_ablated_factory_binding.effect_digest,
            )
        )
        hostile = self._resign_materialization(
            replace(body, actual_factory_binding=hostile_binding)
        )
        with self.assertRaisesRegex(ValueError, "factory.*effect"):
            verify_application_scenario_materialization_v2_body(hostile)

    def test_matched_effect_is_mechanical_conditioned_deletion(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            verify_application_scenario_materialization_v2_body,
        )

        body = self._body()
        wrong_matched = self._resign_effect(
            replace(
                body.scenario_recipe.matched_ablated_effect,
                ordered_steps=body.scenario_recipe.actual_effect.ordered_steps,
            )
        )
        hostile_recipe = self._resign_recipe(
            replace(body.scenario_recipe, matched_ablated_effect=wrong_matched)
        )
        hostile = self._resign_materialization(
            replace(body, scenario_recipe=hostile_recipe)
        )
        with self.assertRaisesRegex(ValueError, "conditioned deletion"):
            verify_application_scenario_materialization_v2_body(hostile)

    def test_unknown_draft_raw_subclass_and_forged_wrapper_fail(self) -> None:
        from rulespace_v3.application_materialization_v2 import (
            ApplicationScenarioMaterializationV2,
            VerifiedV3M0ApplicationScenarioMaterializationV2,
            verify_application_scenario_materialization_v2_body,
            verify_v3m0_application_scenario_materialization_v2,
        )

        attacked = copy.deepcopy(self._body())
        object.__setattr__(attacked, "caller_basis_override", True)
        with self.assertRaisesRegex(ValueError, "unknown or missing"):
            verify_application_scenario_materialization_v2_body(attacked)
        with self.assertRaisesRegex(ValueError, "state"):
            replace(
                self._body(),
                materialization_state="DRAFT_SCENARIO_MATERIALIZATION",
            )

        class HostileBody(ApplicationScenarioMaterializationV2):
            pass

        with self.assertRaises(TypeError):
            verify_application_scenario_materialization_v2_body(
                object.__new__(HostileBody)
            )
        forged = object.__new__(VerifiedV3M0ApplicationScenarioMaterializationV2)
        with self.assertRaises(ValueError):
            verify_v3m0_application_scenario_materialization_v2(forged)

        class HostileWrapper(VerifiedV3M0ApplicationScenarioMaterializationV2):
            pass

        with self.assertRaises(TypeError):
            verify_v3m0_application_scenario_materialization_v2(
                object.__new__(HostileWrapper)
            )

    def test_v1_candidate_raw_and_caller_injection_never_issue(self) -> None:
        from rulespace_v3.application_materialization import (
            VerifiedV3M0ApplicationScenarioMaterialization,
        )
        from rulespace_v3.application_materialization_v2 import (
            materialize_v3m0_application_scenario_v2,
        )
        from rulespace_v3.calibration_authority import (
            VerifiedCalibrationApplicationPermit,
        )
        from rulespace_v3.parent_candidate_v2 import ParentFreezeCandidateV2Manifest
        from rulespace_v3.parent_freeze import VerifiedParentFreeze

        foreign_pairs = (
            (
                object.__new__(VerifiedParentFreeze),
                object.__new__(VerifiedCalibrationApplicationPermit),
            ),
            (object.__new__(ParentFreezeCandidateV2Manifest), self._body()),
            (
                self._body(),
                object.__new__(VerifiedV3M0ApplicationScenarioMaterialization),
            ),
        )
        for parent, permit in foreign_pairs:
            with self.subTest(
                parent=type(parent).__name__, permit=type(permit).__name__
            ):
                with self.assertRaises((TypeError, ValueError, RuntimeError)):
                    materialize_v3m0_application_scenario_v2(
                        parent,
                        permit,
                        self._body().scenario_id,
                    )
        with self.assertRaises(TypeError):
            materialize_v3m0_application_scenario_v2(
                object(),
                object(),
                "v3m0.hostile.scenario",
                source_selector=np.eye(2),
            )


if __name__ == "__main__":
    unittest.main()
