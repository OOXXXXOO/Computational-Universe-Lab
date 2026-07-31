from __future__ import annotations

import dataclasses
import math
import unittest

import numpy as np

import tests.test_v3m0_window_thresholds as window_test_helpers
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.c05_projector_recipe import (
    C05_PROJECTOR_RECIPE_STATE,
    build_c05_projector_orientation_recipe,
    build_c05_projector_recipe_trace_and_operators,
    c05_projector_orientation_recipe_symbol,
    derive_c05_projector_source_readout_from_public_identity,
    verify_c05_projector_orientation_recipe,
)
from rulespace_v3.factory import (
    PrimitiveInterface,
    apply_factory_step,
    basis_manifest_array,
    build_basis_manifest,
    build_factory_from_trace,
    factory_support_offsets,
    frozen_tensor_array,
)
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.response import (
    _extract_projector_candidates,
    compute_fejer_filtered_response,
)
from rulespace_v3.trace import MechanismKind


def _build_factory_pair(recipe, target, *, length: int):
    interface = PrimitiveInterface(
        interface_id=f"interface.c05-projector.{recipe.scenario_kind}.L{length}.v1",
        state_schema_id=recipe.state_schema_id,
        spatial_ndim=recipe.spatial_ndim,
        channel_order=recipe.channel_order,
        dtype="complex128",
        backend="numpy",
    )
    trace, operators = build_c05_projector_recipe_trace_and_operators(
        recipe,
        target_spec_id=target.target_spec_id,
        interface=interface,
    )
    source = build_basis_manifest(
        role="source",
        state_schema_id=interface.state_schema_id,
        channel_order=interface.channel_order,
        vectors=frozen_tensor_array(recipe.source_injection).T,
    )
    readout = build_basis_manifest(
        role="readout",
        state_schema_id=interface.state_schema_id,
        channel_order=interface.channel_order,
        # BasisManifest stores raw rows w; runtime execution uses P=conj(w).
        vectors=frozen_tensor_array(recipe.readout).conj(),
    )
    actual = build_factory_from_trace(
        trace,
        target,
        factory_id=f"factory.c05-projector.{recipe.scenario_kind}.L{length}.v1",
        interface=interface,
        state_shape=(len(recipe.channel_order), length),
        dt=0.25,
        target_blind_parameters=(("c05-projector-candidate", 1.0),),
        layer_slot_ids=tuple(item.layer_slot_id for item in operators),
        operator_payload=operators,
        source_manifest_id=source.manifest_id,
        readout_basis=readout,
        boundary_manifest_id="periodic-v1",
    )
    outcome = matched_ablation(actual)
    if not outcome.status.defined or outcome.pair is None:
        raise AssertionError(f"matched ablation failed: {outcome.status.reason}")
    return trace, outcome.pair


def _plane_wave(vector: np.ndarray, *, length: int, mode: int) -> np.ndarray:
    momentum = 2.0 * math.pi * mode / length
    sites = np.arange(length, dtype=np.float64)
    return (
        vector[:, None] * np.exp(1.0j * momentum * sites)[None, :]
    ).astype(np.complex128)


class C05ProjectorOrientationRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.recipes = {
            kind: build_c05_projector_orientation_recipe(kind)
            for kind in ("phase", "gain")
        }
        cls.target = window_test_helpers._window_controls((8,))[0].target

    def test_record_is_raw_pending_construction_not_authority(self) -> None:
        for kind, recipe in self.recipes.items():
            with self.subTest(kind=kind):
                self.assertIs(
                    verify_c05_projector_orientation_recipe(recipe),
                    recipe,
                )
                self.assertEqual(
                    recipe.construction_state,
                    C05_PROJECTOR_RECIPE_STATE,
                )
                self.assertEqual(recipe.response_ratio_numerator_role, "matched_ablated")
                self.assertEqual(recipe.response_ratio_denominator_role, "actual")
                self.assertFalse(
                    any(
                        hasattr(recipe, field)
                        for field in (
                            "evidence",
                            "permit",
                            "passed",
                            "scientific_status",
                        )
                    )
                )
                public_identity = np.eye(4, dtype=np.complex128)
                source, readout = (
                    derive_c05_projector_source_readout_from_public_identity(
                        recipe,
                        public_identity,
                    )
                )
                np.testing.assert_array_equal(
                    source,
                    frozen_tensor_array(recipe.source_injection),
                )
                np.testing.assert_array_equal(
                    readout,
                    frozen_tensor_array(recipe.readout),
                )
                self.assertLessEqual(
                    float(
                        np.linalg.norm(
                            source.conj().T @ source
                            - np.eye(source.shape[1], dtype=np.complex128),
                            2,
                        )
                    ),
                    1.0e-12,
                )
                self.assertLessEqual(
                    float(
                        np.linalg.norm(
                            readout @ readout.conj().T
                            - np.eye(readout.shape[0], dtype=np.complex128),
                            2,
                        )
                    ),
                    1.0e-12,
                )
                hostile = dataclasses.replace(recipe, recipe_sha="0" * 64)
                with self.assertRaisesRegex(ValueError, "SHA"):
                    verify_c05_projector_orientation_recipe(hostile)

    def test_recipe_interface_matches_the_parent_common_basis_schema(self) -> None:
        parent = issue_v3m0_parent_freeze().manifest
        application = next(
            item
            for item in parent.synthetic_control_application_specs
            if item.control_case_id == "C05_PHASE_AND_SCALAR_GAIN"
        )
        source = application.basis_protocol.source_basis
        readout = application.basis_protocol.readout_basis
        self.assertEqual(source.state_schema_id, readout.state_schema_id)
        for recipe in self.recipes.values():
            self.assertEqual(recipe.state_schema_id, source.state_schema_id)
            self.assertEqual(recipe.channel_order, source.channel_order)
            self.assertEqual(recipe.channel_order, readout.channel_order)
            np.testing.assert_array_equal(
                basis_manifest_array(source),
                np.eye(4, dtype=np.complex128),
            )
            np.testing.assert_array_equal(
                basis_manifest_array(readout),
                np.eye(4, dtype=np.complex128),
            )

    def test_verifier_rejects_unknown_fields_at_every_record_layer(self) -> None:
        attacks = (
            lambda recipe: recipe,
            lambda recipe: recipe.actual_steps[0],
            lambda recipe: recipe.source_injection,
            lambda recipe: recipe.readout,
            lambda recipe: recipe.canonical_structure,
        )
        for index, select_target in enumerate(attacks):
            recipe = build_c05_projector_orientation_recipe("gain")
            object.__setattr__(
                select_target(recipe),
                "caller_unknown",
                "forged",
            )
            with self.subTest(attack=index):
                with self.assertRaisesRegex(ValueError, "unknown fields"):
                    verify_c05_projector_orientation_recipe(recipe)

    def test_ablation_deletes_only_six_conditioned_local_slots(self) -> None:
        for kind, recipe in self.recipes.items():
            trace, pair = _build_factory_pair(recipe, self.target, length=8)
            conditioned = tuple(
                item
                for item in trace.primitives
                if item.kind is MechanismKind.TARGET_CONDITIONED
            )
            blind = tuple(
                item
                for item in trace.primitives
                if item.kind is MechanismKind.TARGET_BLIND
            )
            with self.subTest(kind=kind):
                self.assertEqual(len(conditioned), 6)
                self.assertEqual(len(blind), 6)
                self.assertEqual(len(pair.manifest.replacements), 6)
                self.assertEqual(
                    {item.layer_slot_id for item in pair.manifest.replacements},
                    {
                        pair.actual.factory.layer_slot_ids[index]
                        for index, item in enumerate(trace.primitives)
                        if item.kind is MechanismKind.TARGET_CONDITIONED
                    },
                )
                self.assertEqual(
                    tuple(
                        step
                        for step in recipe.actual_steps
                        if not step.target_conditioned
                    ),
                    recipe.matched_ablated_steps,
                )

    def test_factory_symbol_locality_and_structural_residuals(self) -> None:
        identity = np.eye(4, dtype=np.complex128)
        canonical = frozen_tensor_array(
            self.recipes["phase"].canonical_structure
        )
        vector = np.asarray(
            (1.0, 2.0j, -0.5, 0.25j),
            dtype=np.complex128,
        )
        for kind, recipe in self.recipes.items():
            for length in (8, 16):
                _, pair = _build_factory_pair(recipe, self.target, length=length)
                self.assertEqual(factory_support_offsets(pair.actual, 1), ((0,),))
                self.assertEqual(factory_support_offsets(pair.actual, 8), ((0,),))
                self.assertEqual(factory_support_offsets(pair.ablated, 8), ((0,),))
                for branch, factory in (
                    ("actual", pair.actual),
                    ("matched_ablated", pair.ablated),
                ):
                    for mode in (1, 2):
                        momentum = 2.0 * math.pi * mode / length
                        symbol = c05_projector_orientation_recipe_symbol(
                            recipe,
                            momentum,
                            branch,
                        )
                        opposite = c05_projector_orientation_recipe_symbol(
                            recipe,
                            -momentum,
                            branch,
                        )
                        state = _plane_wave(vector, length=length, mode=mode)
                        observed = apply_factory_step(factory, state)[:, 0]
                        with self.subTest(
                            kind=kind,
                            length=length,
                            branch=branch,
                            mode=mode,
                        ):
                            np.testing.assert_allclose(
                                observed,
                                symbol @ vector,
                                rtol=0.0,
                                atol=2.0e-12,
                            )
                            self.assertLessEqual(
                                float(
                                    np.linalg.norm(
                                        symbol.conj().T @ symbol - identity,
                                        2,
                                    )
                                ),
                                1.0e-12,
                            )
                            self.assertLessEqual(
                                float(
                                    np.linalg.norm(
                                        opposite.T @ canonical @ symbol - canonical,
                                        2,
                                    )
                                ),
                                1.0e-12,
                            )
                            self.assertLessEqual(
                                float(np.linalg.norm(opposite - symbol.conj(), 2)),
                                1.0e-12,
                            )
                            phases = np.angle(np.linalg.eigvals(symbol))
                            selected = (
                                phases >= recipe.reference_phase_band[0]
                            ) & (
                                phases <= recipe.reference_phase_band[1]
                            )
                            self.assertEqual(
                                int(np.count_nonzero(selected)),
                                recipe.expected_shell_rank,
                            )

    def test_production_fejer_uses_y0_over_y1_for_every_candidate(self) -> None:
        metric = np.eye(4, dtype=np.complex128)
        for kind, recipe in self.recipes.items():
            source = frozen_tensor_array(recipe.source_injection)
            readout = frozen_tensor_array(recipe.readout)
            expected = recipe.expected_response_scalar_y0_over_y1
            for order in (256, 512, 1024, 2048, 4096, 8192):
                y0_matched_ablated = compute_fejer_filtered_response(
                    c05_projector_orientation_recipe_symbol(
                        recipe,
                        math.pi / 4.0,
                        "matched_ablated",
                    ),
                    metric,
                    recipe.reference_phase,
                    order,
                    source,
                    readout,
                )
                y1_actual = compute_fejer_filtered_response(
                    c05_projector_orientation_recipe_symbol(
                        recipe,
                        math.pi / 4.0,
                        "actual",
                    ),
                    metric,
                    recipe.reference_phase,
                    order,
                    source,
                    readout,
                )
                denominator = float(np.linalg.norm(y1_actual, 2))
                numerator = float(np.linalg.norm(y0_matched_ablated, 2))
                ratio = numerator / denominator
                with self.subTest(kind=kind, order=order):
                    self.assertGreater(denominator, 0.1)
                    self.assertLessEqual(
                        abs(ratio - abs(expected)),
                        1.0e-12,
                    )
                    self.assertLessEqual(
                        float(
                            np.linalg.norm(
                                y0_matched_ablated - expected * y1_actual,
                                2,
                            )
                        ),
                        1.0e-12,
                    )

    def test_actual_endpoint_candidate_has_positive_participation_margin(
        self,
    ) -> None:
        metric = np.eye(4, dtype=np.complex128)
        expected_participation = {
            "phase": 27.0 / 76.0,
            "gain": 23.0 / 76.0,
        }
        for kind, recipe in self.recipes.items():
            candidate, = _extract_projector_candidates(
                c05_projector_orientation_recipe_symbol(
                    recipe,
                    math.pi / 4.0,
                    "actual",
                ),
                metric,
                (recipe.reference_phase_band,),
                256,
                frozen_tensor_array(recipe.source_injection),
                frozen_tensor_array(recipe.readout),
            )
            with self.subTest(kind=kind):
                self.assertEqual(candidate.rank, recipe.expected_shell_rank)
                self.assertAlmostEqual(
                    candidate.participation,
                    expected_participation[kind],
                    places=14,
                )
                self.assertGreater(candidate.participation - 0.25, 0.05)


if __name__ == "__main__":
    unittest.main()
