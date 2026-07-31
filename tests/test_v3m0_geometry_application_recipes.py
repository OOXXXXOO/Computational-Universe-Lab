from __future__ import annotations

import math
from dataclasses import replace
import unittest
from unittest.mock import patch

import numpy as np
import rulespace_v3.geometry_application_recipes as geometry_recipes

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.factory import (
    PrimitiveInterface,
    apply_factory_step,
    build_basis_manifest,
    build_factory_from_trace,
    factory_support_offsets,
    freeze_complex_tensor,
    frozen_tensor_array,
)
from rulespace_v3.geometry import (
    GeometryNumericalThresholds,
    _compute_geometry_spectrum_from_matrices,
)
from rulespace_v3.geometry_application_recipes import (
    C15_GEOMETRY_SCENARIO_IDS,
    GEOMETRY_APPLICATION_SCENARIO_IDS,
    C15_EXPECTED_SPECTRA,
    _build_c15_preflight_bundle,
    _finite_response,
    build_geometry_application_recipe,
    build_geometry_recipe_trace_and_operators,
    geometry_application_recipe_symbol,
    geometry_operator_bundle_template_payload,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.response import (
    _extract_projector_candidates,
    compute_fejer_filtered_response,
)
from rulespace_v3.trace import MechanismKind
from tests.test_v3m0_window_thresholds import _window_controls


_J = np.asarray(
    (
        (0.0, 1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
        (0.0, 0.0, -1.0, 0.0),
    ),
    dtype=np.complex128,
)


class GeometryApplicationRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
        cls.recipes = {
            scenario_id: build_geometry_application_recipe(
                cls.parent,
                scenario_id,
            )
            for scenario_id in GEOMETRY_APPLICATION_SCENARIO_IDS
        }

    def test_registry_binds_all_c15_c19_success_scenarios_and_exact_dag(self) -> None:
        self.assertEqual(len(GEOMETRY_APPLICATION_SCENARIO_IDS), 9)
        manifest_scenarios = {
            scenario.scenario_id: (application, scenario)
            for application in self.parent.manifest.synthetic_control_application_specs
            if application.control_case_id.startswith(
                ("C15_", "C16_", "C17_", "C18_", "C19_")
            )
            for scenario in application.scenario_execution_specs
        }
        self.assertEqual(set(self.recipes), set(manifest_scenarios))
        for scenario_id, recipe in self.recipes.items():
            with self.subTest(scenario_id=scenario_id):
                application, scenario = manifest_scenarios[scenario_id]
                self.assertEqual(recipe.application_spec_sha, application.application_spec_sha)
                self.assertEqual(recipe.scenario_sha, scenario.scenario_sha)
                self.assertEqual(recipe.recipe_id, scenario.execution_recipe_id)
                self.assertEqual(recipe.channel_order, ("q0", "p0", "q1", "p1"))
                self.assertEqual(recipe.primitive_support_radius, 1)
                self.assertEqual(recipe.expected_shell_rank, 2)
                self.assertEqual(
                    recipe.integration_state,
                    "PENDING_PARENT_REFREEZE_AND_LIVE_PERMIT_T_BINDING",
                )
                self.assertTrue(recipe.actual_steps)
                self.assertEqual(
                    recipe.matched_ablated_steps,
                    tuple(
                        step
                        for step in recipe.actual_steps
                        if not step.target_conditioned
                    ),
                )
                self.assertTrue(
                    any(step.target_conditioned for step in recipe.actual_steps)
                )
                self.assertTrue(
                    all(abs(step.offset[0]) <= 1 for step in recipe.actual_steps)
                )
                self.assertNotEqual(
                    recipe.actual_effect_digest,
                    recipe.matched_ablated_effect_digest,
                )

    def test_c15_symbols_have_rank_two_shell_and_fp64_structure(self) -> None:
        for scenario_id in C15_GEOMETRY_SCENARIO_IDS:
            recipe = self.recipes[scenario_id]
            source = frozen_tensor_array(recipe.source_injection)
            readout = frozen_tensor_array(recipe.readout)
            for branch in ("actual", "matched_ablated"):
                for momentum in (math.pi / 4.0, math.pi / 2.0):
                    with self.subTest(
                        scenario_id=scenario_id,
                        branch=branch,
                        momentum=momentum,
                    ):
                        matrix = geometry_application_recipe_symbol(
                            recipe,
                            momentum,
                            branch,
                        )
                        negative = geometry_application_recipe_symbol(
                            recipe,
                            -momentum,
                            branch,
                        )
                        self.assertLessEqual(
                            np.linalg.norm(
                                matrix.conj().T @ matrix - np.eye(4),
                                ord=2,
                            ),
                            1.0e-12,
                        )
                        self.assertLessEqual(
                            np.linalg.norm(
                                negative.T @ _J @ matrix - _J,
                                ord=2,
                            ),
                            1.0e-12,
                        )
                        self.assertLessEqual(
                            np.linalg.norm(negative - matrix.conj(), ord=2),
                            1.0e-12,
                        )
                        candidates = _extract_projector_candidates(
                            matrix,
                            np.eye(4, dtype=np.complex128),
                            recipe.reference_phase_bands,
                            256,
                            source,
                            readout,
                        )
                        self.assertEqual(len(candidates), 1)
                        self.assertEqual(candidates[0].rank, 2)
                        self.assertGreater(candidates[0].participation, 0.25)
                        self.assertLessEqual(
                            max(
                                candidates[0].hermitian_residual,
                                candidates[0].idempotent_residual,
                                candidates[0].g_invariance_residual,
                                candidates[0].eigenphase_residual,
                            ),
                            1.0e-12,
                        )

    def test_c15_finite_fejer_responses_reproduce_semantic_geometry(self) -> None:
        thresholds = GeometryNumericalThresholds(
            signal_threshold=0.001,
            geometry_threshold=0.05,
            geometry_ambiguity_half_width=0.01,
            coverage_threshold=0.5,
            coverage_ambiguity_half_width=0.1,
        )
        for order in (256, 512, 1024, 2048, 4096, 8192):
            bundle, response_by_scenario = _build_c15_preflight_bundle(
                self.parent,
                order,
            )
            kernel = frozen_tensor_array(bundle.kernel_basis)
            quotient = frozen_tensor_array(bundle.physical_quotient_map)
            metric = frozen_tensor_array(bundle.physical_quotient_metric)
            targets = frozen_tensor_array(bundle.target_physical_representatives)
            for scenario_id in C15_GEOMETRY_SCENARIO_IDS:
                with self.subTest(order=order, scenario_id=scenario_id):
                    response = response_by_scenario[scenario_id]
                    singular_values = np.linalg.svd(response, compute_uv=False)
                    self.assertEqual(
                        np.count_nonzero(singular_values > 0.001),
                        response.shape[1],
                    )
                    left, _, _ = np.linalg.svd(response, full_matrices=False)
                    s_curv = np.asarray(
                        left[:, : response.shape[1]],
                        dtype=np.complex128,
                    )
                    result = _compute_geometry_spectrum_from_matrices(
                        s_curv,
                        kernel,
                        quotient,
                        metric,
                        targets,
                        thresholds=thresholds,
                    )
                    expected_g, expected_c = C15_EXPECTED_SPECTRA[scenario_id]
                    np.testing.assert_allclose(
                        result.g_spectrum,
                        expected_g,
                        rtol=0.0,
                        atol=2.0e-12,
                    )
                    np.testing.assert_allclose(
                        result.c_spectrum,
                        expected_c,
                        rtol=0.0,
                        atol=2.0e-12,
                    )

    def test_c15_analytic_bundle_build_does_not_read_finite_response(self) -> None:
        builder = getattr(
            geometry_recipes,
            "build_c15_analytic_geometry_bundle",
            None,
        )
        verifier = getattr(
            geometry_recipes,
            "verify_c15_analytic_geometry_bundle",
            None,
        )
        self.assertTrue(callable(builder))
        self.assertTrue(callable(verifier))
        with patch(
            "rulespace_v3.geometry_application_recipes._finite_response",
            side_effect=AssertionError("finite response is forbidden"),
        ):
            bundle = builder(self.parent, 256)
            verified = verifier(
                self.parent,
                bundle,
            )
        self.assertIs(verified, bundle)
        self.assertEqual(
            bundle.construction_rule_id,
            "c15-analytic-shell-semantic-bundle-v1",
        )

    def test_c15_analytic_bundle_measures_finite_t_sides_with_margin(self) -> None:
        builder = getattr(
            geometry_recipes,
            "build_c15_analytic_geometry_bundle",
            None,
        )
        self.assertTrue(callable(builder))
        expected_ranks = dict(
            zip(C15_GEOMETRY_SCENARIO_IDS, (4, 1, 2, 3))
        )
        expected_g_sides = {
            C15_GEOMETRY_SCENARIO_IDS[0]: ("above", "below", "below", "below"),
            C15_GEOMETRY_SCENARIO_IDS[1]: ("below",),
            C15_GEOMETRY_SCENARIO_IDS[2]: ("below", "below"),
            C15_GEOMETRY_SCENARIO_IDS[3]: ("above", "below", "below"),
        }
        expected_c_sides = {
            C15_GEOMETRY_SCENARIO_IDS[0]: ("above", "above"),
            C15_GEOMETRY_SCENARIO_IDS[1]: ("below", "above"),
            C15_GEOMETRY_SCENARIO_IDS[2]: ("above", "above"),
            C15_GEOMETRY_SCENARIO_IDS[3]: ("above", "above"),
        }
        thresholds = GeometryNumericalThresholds(
            signal_threshold=0.001,
            geometry_threshold=0.05,
            geometry_ambiguity_half_width=0.01,
            coverage_threshold=0.5,
            coverage_ambiguity_half_width=0.1,
        )

        def side(value: float, threshold: float, half_width: float) -> str:
            if abs(value - threshold) < half_width:
                return "grey"
            return "below" if value < threshold else "above"

        for order in (256, 512, 1024, 2048, 4096, 8192):
            bundle = builder(self.parent, order)
            kernel = frozen_tensor_array(bundle.kernel_basis)
            quotient = frozen_tensor_array(bundle.physical_quotient_map)
            metric = frozen_tensor_array(bundle.physical_quotient_metric)
            targets = frozen_tensor_array(bundle.target_physical_representatives)
            for scenario_id in C15_GEOMETRY_SCENARIO_IDS:
                with self.subTest(order=order, scenario_id=scenario_id):
                    response = _finite_response(
                        self.recipes[scenario_id],
                        "actual",
                        order,
                    )
                    left, singular_values, _ = np.linalg.svd(
                        response,
                        full_matrices=False,
                    )
                    active = singular_values > thresholds.signal_threshold
                    self.assertEqual(
                        int(np.count_nonzero(active)),
                        expected_ranks[scenario_id],
                    )
                    result = _compute_geometry_spectrum_from_matrices(
                        np.asarray(left[:, active], dtype=np.complex128),
                        kernel,
                        quotient,
                        metric,
                        targets,
                        thresholds=thresholds,
                    )
                    self.assertEqual(
                        tuple(
                            side(
                                value,
                                thresholds.geometry_threshold,
                                thresholds.geometry_ambiguity_half_width,
                            )
                            for value in result.g_spectrum
                        ),
                        expected_g_sides[scenario_id],
                    )
                    self.assertEqual(
                        tuple(
                            side(
                                value,
                                thresholds.coverage_threshold,
                                thresholds.coverage_ambiguity_half_width,
                            )
                            for value in result.c_spectrum
                        ),
                        expected_c_sides[scenario_id],
                    )
                    self.assertGreater(
                        min(
                            abs(value - thresholds.geometry_threshold)
                            for value in result.g_spectrum
                        ),
                        thresholds.geometry_ambiguity_half_width,
                    )
                    self.assertGreater(
                        min(
                            abs(value - thresholds.coverage_threshold)
                            for value in result.c_spectrum
                        ),
                        thresholds.coverage_ambiguity_half_width,
                    )

    def test_c15_analytic_bundle_rejects_resigned_tensor_and_scenario_splice(
        self,
    ) -> None:
        builder = getattr(
            geometry_recipes,
            "build_c15_analytic_geometry_bundle",
            None,
        )
        verifier = getattr(
            geometry_recipes,
            "verify_c15_analytic_geometry_bundle",
            None,
        )
        self.assertTrue(callable(builder))
        self.assertTrue(callable(verifier))
        bundle = builder(self.parent, 256)
        changed_kernel = frozen_tensor_array(bundle.kernel_basis)
        changed_kernel[0, 0] += 0.125
        tampered_tensor = replace(
            bundle,
            kernel_basis=freeze_complex_tensor(changed_kernel),
            bundle_sha="0" * 64,
        )
        tampered_tensor = replace(
            tampered_tensor,
            bundle_sha=canonical_sha(
                geometry_operator_bundle_template_payload(tampered_tensor)
            ),
        )
        with self.assertRaisesRegex(ValueError, "differs from|analytic"):
            verifier(self.parent, tampered_tensor)

        spliced = replace(
            bundle,
            scenario_recipe_shas=tuple(reversed(bundle.scenario_recipe_shas)),
            bundle_sha="0" * 64,
        )
        spliced = replace(
            spliced,
            bundle_sha=canonical_sha(
                geometry_operator_bundle_template_payload(spliced)
            ),
        )
        with self.assertRaisesRegex(ValueError, "differs from|analytic"):
            verifier(self.parent, spliced)

    def test_actual_and_matched_ablated_are_resolved_at_finite_order(self) -> None:
        for scenario_id in C15_GEOMETRY_SCENARIO_IDS:
            recipe = self.recipes[scenario_id]
            source = frozen_tensor_array(recipe.source_injection)
            readout = frozen_tensor_array(recipe.readout)
            actual_blocks = []
            ablated_blocks = []
            for momentum in (math.pi / 4.0, math.pi / 2.0):
                actual_matrix = geometry_application_recipe_symbol(
                    recipe,
                    momentum,
                    "actual",
                )
                actual_phase = _extract_projector_candidates(
                    actual_matrix,
                    np.eye(4, dtype=np.complex128),
                    recipe.reference_phase_bands,
                    256,
                    source,
                    readout,
                )[0].phase
                for branch, destination in (
                    ("actual", actual_blocks),
                    ("matched_ablated", ablated_blocks),
                ):
                    destination.append(
                        compute_fejer_filtered_response(
                            geometry_application_recipe_symbol(
                                recipe,
                                momentum,
                                branch,
                            ),
                            np.eye(4, dtype=np.complex128),
                            actual_phase,
                            256,
                            source,
                            readout,
                        )
                    )
            actual = np.vstack(actual_blocks)
            ablated = np.vstack(ablated_blocks)
            self.assertGreater(np.linalg.norm(actual - ablated, ord=2), 0.02)

    def test_c15_factory_bridge_is_exact_and_support_is_length_independent(
        self,
    ) -> None:
        recipe = self.recipes[C15_GEOMETRY_SCENARIO_IDS[0]]
        target = _window_controls()[0].target
        vector = np.asarray(
            (1.0 + 0.25j, -0.5 + 0.1j, 0.2 - 0.7j, 0.9 + 0.3j),
            dtype=np.complex128,
        )
        observed_support = []
        for length, modes in ((8, (1, 2)), (16, (2, 4))):
            interface = PrimitiveInterface(
                interface_id=f"interface.test.geometry.{length}.v1",
                state_schema_id=recipe.state_schema_id,
                spatial_ndim=1,
                channel_order=recipe.channel_order,
                dtype="complex128",
                backend="numpy",
            )
            trace, operators = build_geometry_recipe_trace_and_operators(
                self.parent,
                recipe,
                target_spec_id=target.target_spec_id,
                interface=interface,
            )
            self.assertTrue(all(item.depends_on == () for item in trace.primitives))
            self.assertEqual(
                tuple(item.kind for item in trace.primitives),
                tuple(
                    (
                        MechanismKind.TARGET_CONDITIONED
                        if step.target_conditioned
                        else MechanismKind.TARGET_BLIND
                    )
                    for step in recipe.actual_steps
                ),
            )
            identity = np.eye(4, dtype=np.complex128)
            source = build_basis_manifest(
                role="source",
                state_schema_id=interface.state_schema_id,
                channel_order=interface.channel_order,
                vectors=identity,
            )
            readout = build_basis_manifest(
                role="readout",
                state_schema_id=interface.state_schema_id,
                channel_order=interface.channel_order,
                vectors=identity,
            )
            actual = build_factory_from_trace(
                trace,
                target,
                factory_id=f"factory.test.geometry.{length}.v1",
                interface=interface,
                state_shape=(4, length),
                dt=0.25,
                target_blind_parameters=(("geometry-recipe-test", 1.0),),
                layer_slot_ids=tuple(item.layer_slot_id for item in operators),
                operator_payload=operators,
                source_manifest_id=source.manifest_id,
                readout_basis=readout,
                boundary_manifest_id="periodic-v1",
            )
            outcome = matched_ablation(actual)
            self.assertTrue(outcome.status.defined)
            self.assertIsNotNone(outcome.pair)
            pair = outcome.pair
            observed_support.append(factory_support_offsets(pair.actual, 1))
            for mode in modes:
                momentum = 2.0 * math.pi * mode / length
                sites = np.arange(length, dtype=np.float64)
                state = (
                    vector[:, None]
                    * np.exp(1.0j * momentum * sites)[None, :]
                ).astype(np.complex128)
                for branch, factory in (
                    ("actual", pair.actual),
                    ("matched_ablated", pair.ablated),
                ):
                    observed = apply_factory_step(factory, state)[:, 0]
                    expected = (
                        geometry_application_recipe_symbol(
                            recipe,
                            momentum,
                            branch,
                        )
                        @ vector
                    )
                    np.testing.assert_allclose(
                        observed,
                        expected,
                        rtol=0.0,
                        atol=2.0e-12,
                    )
        self.assertEqual(observed_support[0], observed_support[1])


if __name__ == "__main__":
    unittest.main()
