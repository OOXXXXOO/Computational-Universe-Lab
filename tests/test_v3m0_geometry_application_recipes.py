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
    C16_GEOMETRY_SCENARIO_IDS,
    C17_GEOMETRY_SCENARIO_IDS,
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

    def test_c17_both_branch_symbols_are_structural_and_endpoint_is_visible(
        self,
    ) -> None:
        recipe = self.recipes[C17_GEOMETRY_SCENARIO_IDS[0]]
        source = frozen_tensor_array(recipe.source_injection)
        readout = frozen_tensor_array(recipe.readout)
        for momentum in (math.pi / 4.0, math.pi / 2.0):
            for branch in ("actual", "matched_ablated"):
                with self.subTest(momentum=momentum, branch=branch):
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
                        np.linalg.norm(negative.T @ _J @ matrix - _J, ord=2),
                        1.0e-12,
                    )
                    self.assertLessEqual(
                        np.linalg.norm(negative - matrix.conj(), ord=2),
                        1.0e-12,
                    )
            for order in (256, 512, 1024, 2048, 4096, 8192):
                with self.subTest(momentum=momentum, order=order):
                    candidates = _extract_projector_candidates(
                        geometry_application_recipe_symbol(
                            recipe,
                            momentum,
                            "actual",
                        ),
                        np.eye(4, dtype=np.complex128),
                        recipe.reference_phase_bands,
                        order,
                        source,
                        readout,
                    )
                    self.assertEqual(len(candidates), 1)
                    self.assertEqual(candidates[0].rank, 2)
                    self.assertLessEqual(
                        abs(candidates[0].participation - 1.0),
                        1.0e-12,
                    )
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

    def test_c16_analytic_bundles_freeze_distinct_targets_before_response(
        self,
    ) -> None:
        builder = getattr(
            geometry_recipes,
            "build_c16_analytic_geometry_bundle",
            None,
        )
        verifier = getattr(
            geometry_recipes,
            "verify_c16_analytic_geometry_bundle",
            None,
        )
        self.assertTrue(callable(builder))
        self.assertTrue(callable(verifier))
        with patch(
            "rulespace_v3.geometry_application_recipes._finite_response",
            side_effect=AssertionError("finite response is forbidden"),
        ):
            bundles = tuple(
                builder(self.parent, scenario_id, 256)
                for scenario_id in C16_GEOMETRY_SCENARIO_IDS
            )
            for bundle in bundles:
                self.assertIs(verifier(self.parent, bundle), bundle)

        targets = tuple(
            frozen_tensor_array(bundle.target_physical_representatives)
            for bundle in bundles
        )
        self.assertFalse(np.array_equal(targets[0], targets[1]))
        for scenario_id, bundle in zip(C16_GEOMETRY_SCENARIO_IDS, bundles):
            recipe = self.recipes[scenario_id]
            self.assertEqual(bundle.scenario_id, scenario_id)
            self.assertEqual(bundle.scenario_sha, recipe.scenario_sha)
            self.assertEqual(bundle.scenario_recipe_sha, recipe.recipe_sha)
            self.assertEqual(
                bundle.integration_state,
                "PENDING_PARENT_REFREEZE_AND_LIVE_PERMIT_T_BINDING",
            )
            self.assertIsNone(bundle.undressed_response_representatives)
            self.assertIsNone(bundle.dressed_response_representatives)
            self.assertIsNone(bundle.gauge_basis)
            self.assertIsNone(bundle.gauge_amplitude)

    def test_c17_dressing_is_a_real_kernel_tensor_and_quotient_invariant(
        self,
    ) -> None:
        builder = getattr(
            geometry_recipes,
            "build_c17_analytic_geometry_bundle",
            None,
        )
        verifier = getattr(
            geometry_recipes,
            "verify_c17_analytic_geometry_bundle",
            None,
        )
        self.assertTrue(callable(builder))
        self.assertTrue(callable(verifier))
        with patch(
            "rulespace_v3.geometry_application_recipes._finite_response",
            side_effect=AssertionError("finite response is forbidden"),
        ):
            bundle = builder(self.parent, 256)
            self.assertIs(verifier(self.parent, bundle), bundle)

        recipe = self.recipes[C17_GEOMETRY_SCENARIO_IDS[0]]
        self.assertEqual(bundle.scenario_id, recipe.scenario_id)
        self.assertEqual(bundle.scenario_sha, recipe.scenario_sha)
        self.assertEqual(bundle.scenario_recipe_sha, recipe.recipe_sha)
        self.assertEqual(bundle.gauge_amplitude, 8.0)
        self.assertIsNotNone(bundle.undressed_response_representatives)
        self.assertIsNotNone(bundle.dressed_response_representatives)
        self.assertIsNotNone(bundle.gauge_basis)
        targets = frozen_tensor_array(bundle.target_physical_representatives)
        undressed = frozen_tensor_array(bundle.undressed_response_representatives)
        dressed = frozen_tensor_array(bundle.dressed_response_representatives)
        gauge = frozen_tensor_array(bundle.gauge_basis)
        kernel = frozen_tensor_array(bundle.kernel_basis)
        quotient = frozen_tensor_array(bundle.physical_quotient_map)
        np.testing.assert_allclose(
            dressed,
            (undressed + 8.0 * gauge) / math.sqrt(65.0),
            rtol=0.0,
            atol=1.0e-12,
        )
        np.testing.assert_allclose(
            kernel,
            np.column_stack((undressed, gauge)),
            rtol=0.0,
            atol=1.0e-12,
        )
        self.assertEqual(targets.shape, (8, 2))
        self.assertLessEqual(
            np.linalg.norm(undressed.conj().T @ gauge, ord=2),
            1.0e-12,
        )
        self.assertLessEqual(np.linalg.norm(quotient @ gauge, ord=2), 1.0e-12)
        physical_block = undressed.conj().T @ dressed
        graph = (gauge.conj().T @ dressed) @ np.linalg.inv(physical_block)
        np.testing.assert_allclose(
            np.linalg.svd(graph, compute_uv=False),
            (8.0, 8.0),
            rtol=0.0,
            atol=1.0e-12,
        )

    def test_c17_real_branches_carry_the_frozen_gauge_dressing(self) -> None:
        measure = getattr(
            geometry_recipes,
            "measure_c17_finite_response_preflight",
            None,
        )
        self.assertTrue(callable(measure))
        for order in (256, 512, 1024, 2048, 4096, 8192):
            bundle = geometry_recipes.build_c17_analytic_geometry_bundle(
                self.parent,
                order,
            )
            with patch(
                "rulespace_v3.geometry_application_recipes._finite_response",
                wraps=_finite_response,
            ) as finite_response:
                preflight = measure(self.parent, bundle)
            self.assertEqual(
                {call.args[1] for call in finite_response.call_args_list},
                {"actual", "matched_ablated"},
            )
            dressed = frozen_tensor_array(preflight.raw_dressed_response)
            undressed = frozen_tensor_array(
                preflight.raw_undressed_response
            )
            self.assertGreater(np.linalg.norm(dressed - undressed), 0.5)
            expected_undressed_slope = 8.0 / (order + 1.0)
            np.testing.assert_allclose(
                preflight.undressed_graph_singular_values,
                (expected_undressed_slope, expected_undressed_slope),
                rtol=0.0,
                atol=1.0e-12,
            )
            np.testing.assert_allclose(
                preflight.expected_undressed_graph_singular_values,
                (expected_undressed_slope, expected_undressed_slope),
                rtol=0.0,
                atol=0.0,
            )
            np.testing.assert_allclose(
                preflight.dressed_graph_singular_values,
                preflight.expected_dressed_graph_singular_values,
                rtol=0.0,
                atol=1.0e-12,
            )
            np.testing.assert_allclose(
                preflight.expected_dressed_graph_singular_values,
                (8.0, 8.0),
                rtol=0.0,
                atol=0.0,
            )
            expected_undressed_physical_sigma = 1.0 / math.sqrt(
                1.0 + expected_undressed_slope**2
            )
            np.testing.assert_allclose(
                preflight.undressed_physical_block_singular_values,
                (
                    expected_undressed_physical_sigma,
                    expected_undressed_physical_sigma,
                ),
                rtol=0.0,
                atol=1.0e-12,
            )
            np.testing.assert_allclose(
                preflight.expected_undressed_physical_block_singular_values,
                (
                    expected_undressed_physical_sigma,
                    expected_undressed_physical_sigma,
                ),
                rtol=0.0,
                atol=0.0,
            )
            expected_dressed_physical_sigma = 1.0 / math.sqrt(65.0)
            np.testing.assert_allclose(
                preflight.dressed_physical_block_singular_values,
                (
                    expected_dressed_physical_sigma,
                    expected_dressed_physical_sigma,
                ),
                rtol=0.0,
                atol=1.0e-12,
            )
            np.testing.assert_allclose(
                preflight.expected_dressed_physical_block_singular_values,
                (
                    expected_dressed_physical_sigma,
                    expected_dressed_physical_sigma,
                ),
                rtol=0.0,
                atol=0.0,
            )
            self.assertLessEqual(
                preflight.undressed_physical_block_prediction_residual,
                1.0e-12,
            )
            self.assertLessEqual(
                preflight.dressed_physical_block_prediction_residual,
                1.0e-12,
            )
            self.assertLessEqual(
                preflight.graph_prediction_residual,
                1.0e-12,
            )
            self.assertEqual(
                tuple(
                    "below" if value < 0.5 else "above"
                    for value in preflight.undressed_c_spectrum
                ),
                ("below", "above"),
            )
            np.testing.assert_allclose(
                preflight.undressed_c_spectrum,
                (0.25, 0.75),
                rtol=0.0,
                atol=1.0e-12,
            )
            np.testing.assert_allclose(
                preflight.dressed_c_spectrum,
                (0.25, 0.75),
                rtol=0.0,
                atol=1.0e-12,
            )
            self.assertEqual(
                tuple(
                    "below" if value < 0.5 else "above"
                    for value in preflight.dressed_c_spectrum
                ),
                ("below", "above"),
            )
            self.assertLessEqual(preflight.coverage_spectrum_drift, 1.0e-12)
            self.assertLessEqual(max(preflight.undressed_g_spectrum), 1.0e-12)
            self.assertLessEqual(max(preflight.dressed_g_spectrum), 1.0e-12)
            self.assertEqual(
                preflight.integration_state,
                "PENDING_PARENT_REFREEZE_AND_LIVE_PERMIT_T_BINDING",
            )

    def test_c16_real_fejer_coverage_has_frozen_sides_and_margin(
        self,
    ) -> None:
        thresholds = GeometryNumericalThresholds(
            signal_threshold=0.001,
            geometry_threshold=0.05,
            geometry_ambiguity_half_width=0.01,
            coverage_threshold=0.5,
            coverage_ambiguity_half_width=0.1,
        )

        def measure(
            recipe: object,
            bundle: object,
            targets: np.ndarray,
            expected_rank: int,
        ) -> tuple[float, ...]:
            response = _finite_response(recipe, "actual", order)
            left, singular_values, _ = np.linalg.svd(
                response,
                full_matrices=False,
            )
            active = singular_values > thresholds.signal_threshold
            self.assertEqual(int(np.count_nonzero(active)), expected_rank)
            result = _compute_geometry_spectrum_from_matrices(
                np.asarray(left[:, active], dtype=np.complex128),
                frozen_tensor_array(bundle.kernel_basis),
                frozen_tensor_array(bundle.physical_quotient_map),
                frozen_tensor_array(bundle.physical_quotient_metric),
                targets,
                thresholds=thresholds,
            )
            return result.c_spectrum

        for order in (256, 512, 1024, 2048, 4096, 8192):
            for scenario_id, expected_side in zip(
                C16_GEOMETRY_SCENARIO_IDS,
                ("below", "above"),
            ):
                with self.subTest(
                    order=order,
                    scenario_id=scenario_id,
                ):
                    bundle = geometry_recipes.build_c16_analytic_geometry_bundle(
                        self.parent,
                        scenario_id,
                        order,
                    )
                    spectrum = measure(
                        self.recipes[scenario_id],
                        bundle,
                        frozen_tensor_array(
                            bundle.target_physical_representatives
                        ),
                        1,
                    )
                    self.assertEqual(len(spectrum), 1)
                    self.assertEqual(
                        "below" if spectrum[0] < 0.5 else "above",
                        expected_side,
                    )
                    self.assertGreater(abs(spectrum[0] - 0.5), 0.1)
                    self.assertLessEqual(
                        abs(spectrum[0] - bundle.coverage_control),
                        5.0e-4,
                    )

    def test_geometry_recipe_and_bundle_reject_unknown_record_fields(
        self,
    ) -> None:
        recipe_verifier = geometry_recipes.verify_geometry_application_recipe
        recipe = build_geometry_application_recipe(
            self.parent,
            C16_GEOMETRY_SCENARIO_IDS[0],
        )
        object.__setattr__(recipe, "caller_unknown", "injected")
        with self.assertRaisesRegex(ValueError, "unknown|field|record"):
            recipe_verifier(self.parent, recipe)

        nested_recipe = build_geometry_application_recipe(
            self.parent,
            C16_GEOMETRY_SCENARIO_IDS[0],
        )
        object.__setattr__(
            nested_recipe.source_injection,
            "caller_unknown",
            "injected",
        )
        with self.assertRaisesRegex(ValueError, "unknown|field|record"):
            recipe_verifier(self.parent, nested_recipe)

        bundle_verifier = geometry_recipes.verify_c16_analytic_geometry_bundle
        bundle = geometry_recipes.build_c16_analytic_geometry_bundle(
            self.parent,
            C16_GEOMETRY_SCENARIO_IDS[0],
            256,
        )
        object.__setattr__(bundle, "caller_unknown", "injected")
        with self.assertRaisesRegex(ValueError, "unknown|field|record"):
            bundle_verifier(self.parent, bundle)

        nested_bundle = geometry_recipes.build_c16_analytic_geometry_bundle(
            self.parent,
            C16_GEOMETRY_SCENARIO_IDS[0],
            256,
        )
        object.__setattr__(
            nested_bundle.target_physical_representatives,
            "caller_unknown",
            "injected",
        )
        with self.assertRaisesRegex(ValueError, "unknown|field|record"):
            bundle_verifier(self.parent, nested_bundle)

        c15_verifier = geometry_recipes.verify_c15_analytic_geometry_bundle
        c15_bundle = geometry_recipes.build_c15_analytic_geometry_bundle(
            self.parent,
            256,
        )
        object.__setattr__(c15_bundle, "caller_unknown", "injected")
        with self.assertRaisesRegex(ValueError, "unknown|field|record"):
            c15_verifier(self.parent, c15_bundle)

        nested_c15 = geometry_recipes.build_c15_analytic_geometry_bundle(
            self.parent,
            256,
        )
        object.__setattr__(
            nested_c15.kernel_basis,
            "caller_unknown",
            "injected",
        )
        with self.assertRaisesRegex(ValueError, "unknown|field|record"):
            c15_verifier(self.parent, nested_c15)

    def test_geometry_raw_verifiers_reject_splices_and_resigned_bodies(
        self,
    ) -> None:
        def resign_recipe(recipe: object) -> object:
            provisional = replace(recipe, recipe_sha="0" * 64)
            return replace(
                provisional,
                recipe_sha=canonical_sha(
                    geometry_recipes.geometry_application_recipe_payload(
                        provisional
                    )
                ),
            )

        def resign_bundle(bundle: object) -> object:
            provisional = replace(bundle, bundle_sha="0" * 64)
            return replace(
                provisional,
                bundle_sha=canonical_sha(
                    geometry_recipes.geometry_scenario_operator_bundle_template_payload(
                        provisional
                    )
                ),
            )

        verifier = geometry_recipes.verify_geometry_application_recipe
        low = build_geometry_application_recipe(
            self.parent,
            C16_GEOMETRY_SCENARIO_IDS[0],
        )
        high = build_geometry_application_recipe(
            self.parent,
            C16_GEOMETRY_SCENARIO_IDS[1],
        )
        changed_source = frozen_tensor_array(low.source_injection)
        changed_source[0, 0] += 0.125
        resigned_tensor = resign_recipe(
            replace(
                low,
                source_injection=freeze_complex_tensor(changed_source),
            )
        )
        with self.assertRaisesRegex(ValueError, "differs from|live parent"):
            verifier(self.parent, resigned_tensor)

        control_splice = resign_recipe(
            replace(low, control_case_id="C17_QUOTIENT_GAUGE_COVERAGE")
        )
        with self.assertRaisesRegex(ValueError, "differs from|live parent"):
            verifier(self.parent, control_splice)

        scenario_splice = resign_recipe(
            replace(
                low,
                scenario_id=high.scenario_id,
                scenario_sha=high.scenario_sha,
            )
        )
        with self.assertRaisesRegex(ValueError, "differs from|live parent"):
            verifier(self.parent, scenario_splice)

        resigned_rule = resign_recipe(
            replace(low, construction_rule_id="caller-resigned-rule")
        )
        with self.assertRaisesRegex(ValueError, "differs from|live parent"):
            verifier(self.parent, resigned_rule)

        parent_splice = issue_v3m0_parent_freeze()
        object.__setattr__(
            parent_splice,
            "_VerifiedParentFreeze__manifest",
            replace(parent_splice.manifest, program_id="caller-parent-splice"),
        )
        with self.assertRaisesRegex(
            ValueError,
            "parent|freeze|authority|sha|program",
        ):
            verifier(parent_splice, low)

        low_bundle = geometry_recipes.build_c16_analytic_geometry_bundle(
            self.parent,
            C16_GEOMETRY_SCENARIO_IDS[0],
            256,
        )
        changed_target = frozen_tensor_array(
            low_bundle.target_physical_representatives
        )
        changed_target[0, 0] += 0.125
        resigned_bundle_tensor = resign_bundle(
            replace(
                low_bundle,
                target_physical_representatives=freeze_complex_tensor(
                    changed_target
                ),
            )
        )
        with self.assertRaisesRegex(
            ValueError,
            "differs from|live replay|target|semantics",
        ):
            geometry_recipes.verify_c16_analytic_geometry_bundle(
                self.parent,
                resigned_bundle_tensor,
            )

        c17_bundle = geometry_recipes.build_c17_analytic_geometry_bundle(
            self.parent,
            256,
        )
        resigned_amplitude = resign_bundle(
            replace(c17_bundle, gauge_amplitude=4.0)
        )
        with self.assertRaisesRegex(
            ValueError,
            "differs from|live replay|target|semantics",
        ):
            geometry_recipes.verify_c17_analytic_geometry_bundle(
                self.parent,
                resigned_amplitude,
            )

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

    def test_c17_preflight_rejects_unknown_and_resigned_measurements(self) -> None:
        bundle = geometry_recipes.build_c17_analytic_geometry_bundle(
            self.parent,
            256,
        )
        preflight = geometry_recipes.measure_c17_finite_response_preflight(
            self.parent,
            bundle,
        )
        verifier = geometry_recipes.verify_c17_finite_response_preflight

        unknown = replace(preflight)
        object.__setattr__(unknown, "caller_unknown", "injected")
        with self.assertRaisesRegex(ValueError, "unknown|field|record"):
            verifier(self.parent, bundle, unknown)

        changed_raw = frozen_tensor_array(preflight.raw_dressed_response)
        changed_raw[0, 0] += 0.125
        provisional = replace(
            preflight,
            raw_dressed_response=freeze_complex_tensor(changed_raw),
            preflight_sha="0" * 64,
        )
        resigned_raw = replace(
            provisional,
            preflight_sha=canonical_sha(
                geometry_recipes.c17_finite_response_preflight_payload(
                    provisional
                )
            ),
        )
        with self.assertRaisesRegex(ValueError, "differs from live replay"):
            verifier(self.parent, bundle, resigned_raw)

        provisional = replace(
            preflight,
            expected_dressed_graph_singular_values=(7.0, 7.0),
            preflight_sha="0" * 64,
        )
        resigned_prediction = replace(
            provisional,
            preflight_sha=canonical_sha(
                geometry_recipes.c17_finite_response_preflight_payload(
                    provisional
                )
            ),
        )
        with self.assertRaisesRegex(ValueError, "differs from live replay"):
            verifier(self.parent, bundle, resigned_prediction)

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

    def test_c17_factory_bridge_is_exact_for_both_branches_at_l8_l16(
        self,
    ) -> None:
        recipe = self.recipes[C17_GEOMETRY_SCENARIO_IDS[0]]
        target = _window_controls()[0].target
        vector = np.asarray(
            (0.3 + 0.8j, -0.7 + 0.2j, 1.1 - 0.4j, -0.2 - 0.6j),
            dtype=np.complex128,
        )
        observed_support = []
        for length, modes in ((8, (1, 2)), (16, (2, 4))):
            interface = PrimitiveInterface(
                interface_id=f"interface.test.c17.geometry.{length}.v1",
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
                factory_id=f"factory.test.c17.geometry.{length}.v1",
                interface=interface,
                state_shape=(4, length),
                dt=0.25,
                target_blind_parameters=(("c17-geometry-recipe-test", 1.0),),
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
                    expected = geometry_application_recipe_symbol(
                        recipe,
                        momentum,
                        branch,
                    ) @ vector
                    np.testing.assert_allclose(
                        observed,
                        expected,
                        rtol=0.0,
                        atol=2.0e-12,
                    )
        self.assertEqual(observed_support[0], observed_support[1])


if __name__ == "__main__":
    unittest.main()
