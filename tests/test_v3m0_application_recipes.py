from __future__ import annotations

import dataclasses
import inspect
import math
import unittest

import numpy as np

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    PrimitiveInterface,
    PrimitiveOperatorWire,
    apply_factory_step,
    build_basis_manifest,
    build_factory_from_trace,
    frozen_tensor_array,
)
from rulespace_v3.parent_freeze import (
    SyntheticApplicationOperation,
    TaggedScalarWire,
    application_scenario_execution_spec_payload,
    issue_v3m0_parent_freeze,
    synthetic_application_operation_payload,
)
from rulespace_v3.application_recipes import (
    APPLICATION_C05_TEMPLATE_SCENARIO_IDS,
    APPLICATION_RECIPE_SCENARIO_IDS,
    ApplicationC05FejerTemplate,
    ApplicationRecipeArtifact,
    _c05_phase_offset_for_order,
    _causal_fejer_scalar,
    _evaluate_operation_values,
    application_recipe_symbol,
    build_c05_fejer_recipe_template,
    build_application_recipe,
    build_application_recipe_trace_and_operators,
    verify_c05_fejer_recipe_template,
    verify_application_recipe,
)
from rulespace_v3.response import compute_fejer_filtered_response
from rulespace_v3.trace import MechanismKind
from tests.test_v3m0_window_thresholds import _window_controls


C05_TEMPLATE_SCENARIOS = (
    "v3m0.synthetic-control.c05.v1.scenario.phase.v1",
    "v3m0.synthetic-control.c05.v1.scenario.gain.v1",
)

EXPECTED_SCENARIOS = (
    "v3m0.synthetic-control.c06.v1.scenario.nonscale-mixing.v1",
    "v3m0.synthetic-control.c07.v1.scenario.interference.v1",
    "v3m0.synthetic-control.c08.v1.scenario.rank-missing.v1",
    "v3m0.synthetic-control.c09.v1.scenario.gauge-dressing.v1",
    "v3m0.synthetic-control.c10.v1.scenario.extra-mode.v1",
    "v3m0.synthetic-control.c11.v1.scenario.signal.v1",
    "v3m0.synthetic-control.c12.v1.scenario.ir-normalization.v1",
)

ALL_SCENARIOS = C05_TEMPLATE_SCENARIOS + EXPECTED_SCENARIOS


def _evaluation_values(
    record: ApplicationC05FejerTemplate | ApplicationRecipeArtifact,
) -> dict[str, np.ndarray]:
    return {
        item.operation.operation_instance_id.rsplit(".", maxsplit=1)[
            -1
        ]: frozen_tensor_array(item.effect_tensor)
        for item in record.operation_evaluations
    }


def _replace_parameter(
    operation: SyntheticApplicationOperation,
    name: str,
    replacement: TaggedScalarWire,
) -> SyntheticApplicationOperation:
    changed = dataclasses.replace(
        operation,
        parameters=tuple(
            (key, replacement if key == name else value)
            for key, value in operation.parameters
        ),
        operation_sha="0" * 64,
    )
    return dataclasses.replace(
        changed,
        operation_sha=canonical_sha(synthetic_application_operation_payload(changed)),
    )


def _integer_wire(value: int) -> TaggedScalarWire:
    return TaggedScalarWire(
        value_kind="integer",
        fp64_bits_value=None,
        integer_value=value,
        text_value=None,
        complex128_bits_value=None,
    )


def _text_wire(value: str) -> TaggedScalarWire:
    return TaggedScalarWire(
        value_kind="text",
        fp64_bits_value=None,
        integer_value=None,
        text_value=value,
        complex128_bits_value=None,
    )


def _apply_steps_on_plane_wave(
    recipe: ApplicationRecipeArtifact,
    *,
    branch: str,
    length: int,
    mode: int,
    vector: np.ndarray,
) -> np.ndarray:
    momentum = 2.0 * math.pi * mode / length
    sites = np.arange(length, dtype=np.float64)
    state = vector[:, None] * np.exp(1.0j * momentum * sites)[None, :]
    steps = recipe.actual_steps if branch == "actual" else recipe.matched_ablated_steps
    channel_index = {
        channel: index for index, channel in enumerate(recipe.channel_order)
    }
    for step in steps:
        updated = state.copy()
        source = channel_index[step.source_channel]
        destination = channel_index[step.destination_channel]
        updated[destination] += step.coefficient * np.roll(
            state[source],
            shift=-step.offset[0],
        )
        state = updated
    return state[:, 0]


def _build_executable_recipe_pair(
    parent,
    recipe: ApplicationRecipeArtifact,
    target,
    *,
    length: int,
):
    interface = PrimitiveInterface(
        interface_id=f"interface.test.{recipe.control_case_id}.{length}.v1",
        state_schema_id=recipe.state_schema_id,
        spatial_ndim=recipe.spatial_ndim,
        channel_order=recipe.channel_order,
        dtype="complex128",
        backend="numpy",
    )
    trace, operators = build_application_recipe_trace_and_operators(
        parent,
        recipe,
        target_spec_id=target.target_spec_id,
        interface=interface,
    )
    identity = np.eye(len(recipe.channel_order), dtype=np.complex128)
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
        factory_id=f"factory.test.{recipe.control_case_id}.{length}.v1",
        interface=interface,
        state_shape=(len(recipe.channel_order), length),
        dt=0.25,
        target_blind_parameters=(("application-recipe-test", 1.0),),
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


def _exact_shell_stack(
    recipe: ApplicationRecipeArtifact,
    branch: str,
) -> np.ndarray:
    blocks = []
    for momentum in (math.pi / 4.0, math.pi / 2.0):
        matrix = application_recipe_symbol(recipe, momentum, branch)
        values, vectors = np.linalg.eig(matrix)
        phases = np.angle(values)
        selected = np.flatnonzero(
            (phases >= recipe.reference_phase_band[0])
            & (phases <= recipe.reference_phase_band[1])
        )
        if len(selected) != 1:
            raise AssertionError("reference band lost its frozen rank")
        columns = vectors[:, selected]
        shell = columns @ np.linalg.inv(columns.conj().T @ columns) @ columns.conj().T
        blocks.append(shell)
    return np.concatenate(tuple(blocks), axis=0)


def _fejer_response_stack(
    recipe: ApplicationRecipeArtifact,
    branch: str,
) -> np.ndarray:
    blocks = []
    for momentum in (math.pi / 4.0, math.pi / 2.0):
        actual = application_recipe_symbol(recipe, momentum, "actual")
        actual_values = np.linalg.eigvals(actual)
        phases = np.angle(actual_values)
        selected = np.flatnonzero(
            (phases >= recipe.reference_phase_band[0])
            & (phases <= recipe.reference_phase_band[1])
        )
        if len(selected) != 1:
            raise AssertionError("actual reference band lost its frozen rank")
        transition = application_recipe_symbol(recipe, momentum, branch)
        blocks.append(
            compute_fejer_filtered_response(
                transition,
                np.eye(4, dtype=np.complex128),
                float(phases[selected[0]]),
                256,
                frozen_tensor_array(recipe.source_injection),
                frozen_tensor_array(recipe.readout),
            )
        )
    return np.concatenate(tuple(blocks), axis=0)


def _source_survival(actual: np.ndarray, ablated: np.ndarray) -> np.ndarray:
    _, actual_values, actual_right = np.linalg.svd(actual, full_matrices=False)
    _, ablated_values, ablated_right = np.linalg.svd(
        ablated,
        full_matrices=False,
    )
    actual_rank = int(np.count_nonzero(actual_values > 1.0e-12))
    ablated_rank = int(np.count_nonzero(ablated_values > 1.0e-12))
    actual_basis = actual_right.conj().T[:, :actual_rank]
    ablated_basis = ablated_right.conj().T[:, :ablated_rank]
    values = np.linalg.svd(
        ablated_basis.conj().T @ actual_basis,
        compute_uv=False,
    )
    result = np.zeros(actual_rank, dtype=np.float64)
    result[: len(values)] = values**2
    return np.sort(result)


def _output_survival(actual: np.ndarray, ablated: np.ndarray) -> np.ndarray:
    actual_left, actual_values, _ = np.linalg.svd(actual, full_matrices=False)
    ablated_left, ablated_values, _ = np.linalg.svd(
        ablated,
        full_matrices=False,
    )
    actual_rank = int(np.count_nonzero(actual_values > 1.0e-12))
    ablated_rank = int(np.count_nonzero(ablated_values > 1.0e-12))
    values = np.linalg.svd(
        ablated_left[:, :ablated_rank].conj().T @ actual_left[:, :actual_rank],
        compute_uv=False,
    )
    result = np.zeros(actual_rank, dtype=np.float64)
    result[: len(values)] = values**2
    return np.sort(result)


class ApplicationRecipeRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
        cls.target = _window_controls()[0].target
        cls.templates = {
            scenario_id: build_c05_fejer_recipe_template(
                cls.parent,
                scenario_id,
            )
            for scenario_id in C05_TEMPLATE_SCENARIOS
        }
        cls.recipes = {
            scenario_id: build_application_recipe(cls.parent, scenario_id)
            for scenario_id in EXPECTED_SCENARIOS
        }

    def test_registry_is_exact_and_excludes_typed_c11_lanes(self) -> None:
        self.assertEqual(
            APPLICATION_C05_TEMPLATE_SCENARIO_IDS,
            C05_TEMPLATE_SCENARIOS,
        )
        self.assertEqual(APPLICATION_RECIPE_SCENARIO_IDS, EXPECTED_SCENARIOS)
        self.assertNotIn(
            "v3m0.synthetic-control.c11.v1.scenario.null.v1",
            APPLICATION_RECIPE_SCENARIO_IDS,
        )
        self.assertNotIn(
            "v3m0.synthetic-control.c11.v1.scenario.grey.v1",
            APPLICATION_RECIPE_SCENARIO_IDS,
        )
        with self.assertRaisesRegex(ValueError, "BLOCK_SUCCESS"):
            build_application_recipe(
                self.parent,
                "v3m0.synthetic-control.c11.v1.scenario.grey.v1",
            )
        for scenario_id in C05_TEMPLATE_SCENARIOS:
            with self.subTest(scenario_id=scenario_id):
                with self.assertRaisesRegex(ValueError, "integration pending"):
                    build_application_recipe(self.parent, scenario_id)

    def test_every_recipe_binds_live_parent_dag_and_local_factory_inputs(self) -> None:
        applications = {
            item.control_case_id: item
            for item in self.parent.manifest.synthetic_control_application_specs
        }
        for scenario_id, recipe in self.recipes.items():
            with self.subTest(scenario_id=scenario_id):
                self.assertIs(verify_application_recipe(self.parent, recipe), recipe)
                self.assertEqual(recipe.scenario_id, scenario_id)
                self.assertEqual(recipe.channel_order, ("q0", "p0", "q1", "p1"))
                self.assertEqual(recipe.primitive_support_radius, 1)
                self.assertTrue(recipe.operation_evaluations)
                self.assertTrue(recipe.actual_steps)
                self.assertTrue(recipe.matched_ablated_steps)
                self.assertTrue(
                    any(step.target_conditioned for step in recipe.actual_steps)
                )
                self.assertTrue(
                    all(
                        not step.target_conditioned
                        for step in recipe.matched_ablated_steps
                    )
                )
                self.assertNotEqual(
                    recipe.actual_effect_digest,
                    recipe.matched_ablated_effect_digest,
                )
                self.assertTrue(
                    all(
                        abs(step.offset[0]) <= 1
                        and math.isfinite(step.coefficient)
                        and step.coefficient != 0.0
                        for step in recipe.actual_steps
                    )
                )

                application = applications[recipe.control_case_id]
                scenario = next(
                    item
                    for item in application.scenario_execution_specs
                    if item.scenario_id == scenario_id
                )
                self.assertEqual(
                    recipe.application_spec_sha, application.application_spec_sha
                )
                self.assertEqual(recipe.scenario_sha, scenario.scenario_sha)
                self.assertEqual(
                    canonical_sha(
                        application_scenario_execution_spec_payload(scenario)
                    ),
                    scenario.scenario_sha,
                )

                interface = PrimitiveInterface(
                    interface_id=f"interface.test.{recipe.control_case_id}.v1",
                    state_schema_id=recipe.state_schema_id,
                    spatial_ndim=1,
                    channel_order=recipe.channel_order,
                    dtype="complex128",
                    backend="numpy",
                )
                trace, operators = build_application_recipe_trace_and_operators(
                    self.parent,
                    recipe,
                    target_spec_id="target.synthetic.application-recipe.v1",
                    interface=interface,
                )
                self.assertEqual(len(trace.primitives), len(recipe.actual_steps))
                self.assertEqual(len(operators), len(recipe.actual_steps))
                self.assertTrue(
                    all(type(item) is PrimitiveOperatorWire for item in operators)
                )
                self.assertEqual(
                    tuple(item.offset for item in operators),
                    tuple(item.offset for item in recipe.actual_steps),
                )

    def test_trace_taint_and_matched_ablation_preserve_blind_right_factors(
        self,
    ) -> None:
        vector = np.asarray(
            (1.0 + 0.25j, -0.5 + 0.1j, 0.2 - 0.7j, 0.9 + 0.3j),
            dtype=np.complex128,
        )
        for scenario_id, recipe in self.recipes.items():
            for length, modes in ((8, (1, 2)), (12, (1, 3))):
                with self.subTest(
                    scenario_id=scenario_id,
                    length=length,
                ):
                    trace, pair = _build_executable_recipe_pair(
                        self.parent,
                        recipe,
                        self.target,
                        length=length,
                    )
                    conditioned_count = sum(
                        step.target_conditioned for step in recipe.actual_steps
                    )
                    self.assertEqual(
                        len(pair.manifest.replacements),
                        conditioned_count,
                    )
                    self.assertTrue(
                        all(item.depends_on == () for item in trace.primitives)
                    )
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
                    first_conditioned = next(
                        index
                        for index, step in enumerate(recipe.actual_steps)
                        if step.target_conditioned
                    )
                    blind_right_factors = tuple(
                        item.kind
                        for item, step in zip(
                            trace.primitives[first_conditioned + 1 :],
                            recipe.actual_steps[first_conditioned + 1 :],
                        )
                        if not step.target_conditioned
                    )
                    self.assertTrue(blind_right_factors)
                    self.assertTrue(
                        all(
                            kind is MechanismKind.TARGET_BLIND
                            for kind in blind_right_factors
                        )
                    )
                    for mode in modes:
                        momentum = 2.0 * math.pi * mode / length
                        sites = np.arange(length, dtype=np.float64)
                        state = (
                            vector[:, None]
                            * np.exp(1.0j * momentum * sites)[None, :]
                        ).astype(np.complex128)
                        actual = apply_factory_step(pair.actual, state)[:, 0]
                        ablated = apply_factory_step(pair.ablated, state)[:, 0]
                        np.testing.assert_allclose(
                            actual,
                            application_recipe_symbol(
                                recipe,
                                momentum,
                                "actual",
                            )
                            @ vector,
                            rtol=0.0,
                            atol=2.0e-12,
                        )
                        np.testing.assert_allclose(
                            ablated,
                            application_recipe_symbol(
                                recipe,
                                momentum,
                                "matched_ablated",
                            )
                            @ vector,
                            rtol=0.0,
                            atol=2.0e-12,
                        )

    def test_operation_dags_have_the_frozen_mechanical_effects(self) -> None:
        values = {
            scenario_id: _evaluation_values(record)
            for scenario_id, record in {
                **self.templates,
                **self.recipes,
            }.items()
        }
        np.testing.assert_allclose(
            values[ALL_SCENARIOS[0]]["01-phase-flip"],
            -np.eye(2),
            rtol=0.0,
            atol=2.0e-15,
        )
        np.testing.assert_array_equal(
            values[ALL_SCENARIOS[1]]["02-scalar-gain"],
            2.0 * np.eye(2),
        )
        np.testing.assert_array_equal(
            values[ALL_SCENARIOS[2]]["01-nonscalar-mix"],
            np.asarray(((2.0, 1.0), (0.0, 1.0))),
        )
        np.testing.assert_allclose(
            values[ALL_SCENARIOS[3]]["04-interference-combiner"],
            np.asarray(((1.0, -1.0), (1.0, 1.0))),
            rtol=0.0,
            atol=2.0e-15,
        )
        np.testing.assert_array_equal(
            values[ALL_SCENARIOS[4]]["01-rank-one-deletion"],
            np.diag((1.0, 0.0)),
        )
        np.testing.assert_array_equal(
            values[ALL_SCENARIOS[5]]["02-curvature-quotient"],
            np.eye(2),
        )
        self.assertGreater(
            float(
                np.linalg.norm(values[ALL_SCENARIOS[5]]["01-pure-gauge-dressing"][2])
            ),
            1.0,
        )
        np.testing.assert_array_equal(
            values[ALL_SCENARIOS[6]]["02-full-source-extra-readout"],
            np.asarray(((0.0, 0.0), (0.0, 1.0))),
        )
        np.testing.assert_array_equal(
            values[ALL_SCENARIOS[7]]["03-signal-amplitude"],
            np.ones((1, 1)),
        )
        np.testing.assert_array_equal(
            values[ALL_SCENARIOS[8]]["01-nu-inc-normalized"],
            np.asarray((2.0, 2.0)),
        )

    def test_numeric_parameters_change_effect_tensors_and_text_tamper_fails(
        self,
    ) -> None:
        applications = {
            item.control_case_id: item
            for item in self.parent.manifest.synthetic_control_application_specs
        }
        cases = (
            ("C05_PHASE_AND_SCALAR_GAIN", "01-phase-flip", "phase-radians"),
            ("C05_PHASE_AND_SCALAR_GAIN", "02-scalar-gain", "amplitude-scale"),
            ("C06_INTERNAL_NONSCALE_MIXING", "01-nonscalar-mix", "matrix-01"),
            (
                "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
                "04-interference-combiner",
                "combiner-01",
            ),
            ("C08_RANK_R_MISSING_MODES", "01-rank-one-deletion", "missing-rank"),
            ("C09_PURE_GAUGE_DRESSING", "01-pure-gauge-dressing", "gauge-amplitude"),
            (
                "C10_FULL_SOURCE_EXTRA_MODE",
                "01-ablated-orthogonal-mode",
                "new-source-axis",
            ),
            (
                "C11_NULL_GREY_SIGNAL_AMPLITUDE",
                "03-signal-amplitude",
                "amplitude-scale",
            ),
            (
                "C12_NU_INC_IR_NORMALIZATION",
                "01-nu-inc-normalized",
                "curvature-mode-count",
            ),
        )
        for control_id, suffix, parameter_name in cases:
            application = applications[control_id]
            operation = next(
                item
                for item in application.operations
                if item.operation_instance_id.endswith(suffix)
            )
            original_inputs = {
                "phase-rotation-v1": (np.eye(2, dtype=np.complex128),),
                "amplitude-rescale-v1": (
                    np.eye(
                        1 if control_id == "C11_NULL_GREY_SIGNAL_AMPLITUDE" else 2,
                        dtype=np.complex128,
                    ),
                ),
                "source-linear-mix-v1": (
                    np.eye(2, dtype=np.complex128)
                    if control_id != "C10_FULL_SOURCE_EXTRA_MODE"
                    else np.zeros((2, 1), dtype=np.complex128),
                ),
                "geometry-subspace-v1": (
                    np.eye(2, dtype=np.complex128)
                    if control_id != "C12_NU_INC_IR_NORMALIZATION"
                    else np.ones((2, 1), dtype=np.complex128),
                ),
                "canonical-shear-v1": (np.eye(2, dtype=np.complex128),),
            }[operation.operation_kind]
            original = _evaluate_operation_values(operation, original_inputs)
            wire = dict(operation.parameters)[parameter_name]
            if wire.value_kind == "integer":
                replacement = _integer_wire((wire.integer_value or 0) + 1)
            else:
                replacement = dataclasses.replace(
                    wire,
                    fp64_bits_value=4609434218613702656,
                )
            changed_operation = _replace_parameter(
                operation,
                parameter_name,
                replacement,
            )
            try:
                changed = _evaluate_operation_values(
                    changed_operation,
                    original_inputs,
                )
            except ValueError:
                continue
            with self.subTest(control_id=control_id, parameter=parameter_name):
                self.assertFalse(np.array_equal(original, changed))

        c09 = applications["C09_PURE_GAUGE_DRESSING"]
        gauge = next(
            item
            for item in c09.operations
            if item.operation_instance_id.endswith("01-pure-gauge-dressing")
        )
        hostile = _replace_parameter(
            gauge,
            "gauge-sector",
            _text_wire("physical-sector"),
        )
        with self.assertRaisesRegex(ValueError, "gauge sector"):
            _evaluate_operation_values(
                hostile,
                (np.eye(2, dtype=np.complex128),),
            )

    def test_symbols_are_executor_local_unitary_symplectic_and_l_independent(
        self,
    ) -> None:
        identity = np.eye(4, dtype=np.complex128)
        symplectic = np.asarray(
            (
                (0.0, 1.0, 0.0, 0.0),
                (-1.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
                (0.0, 0.0, -1.0, 0.0),
            ),
            dtype=np.complex128,
        )
        vector = np.asarray((1.0, 2.0j, -0.5, 0.25j), dtype=np.complex128)
        for scenario_id, recipe in self.recipes.items():
            for branch in ("actual", "matched_ablated"):
                for momentum in (math.pi / 4.0, math.pi / 2.0):
                    with self.subTest(
                        scenario_id=scenario_id,
                        branch=branch,
                        momentum=momentum,
                    ):
                        matrix = application_recipe_symbol(
                            recipe,
                            momentum,
                            branch,
                        )
                        opposite = application_recipe_symbol(
                            recipe,
                            -momentum,
                            branch,
                        )
                        self.assertLessEqual(
                            float(
                                np.linalg.norm(matrix.conj().T @ matrix - identity, 2)
                            ),
                            1.0e-12,
                        )
                        self.assertLessEqual(
                            float(
                                np.linalg.norm(
                                    opposite.T @ symplectic @ matrix - symplectic,
                                    2,
                                )
                            ),
                            1.0e-12,
                        )
                        self.assertLessEqual(
                            float(np.linalg.norm(opposite - matrix.conj(), 2)),
                            1.0e-12,
                        )
                        phases = np.angle(np.linalg.eigvals(matrix))
                        selected = (phases >= recipe.reference_phase_band[0]) & (
                            phases <= recipe.reference_phase_band[1]
                        )
                        self.assertEqual(int(np.count_nonzero(selected)), 1)

                expected = (
                    application_recipe_symbol(
                        recipe,
                        math.pi / 2.0,
                        branch,
                    )
                    @ vector
                )
                for length in (8, 12):
                    actual = _apply_steps_on_plane_wave(
                        recipe,
                        branch=branch,
                        length=length,
                        mode=length // 4,
                        vector=vector,
                    )
                    np.testing.assert_allclose(
                        actual,
                        expected,
                        rtol=0.0,
                        atol=5.0e-13,
                    )

    def test_c05_is_parent_bound_math_only_until_live_permit_materialization(
        self,
    ) -> None:
        phase = self.templates[C05_TEMPLATE_SCENARIOS[0]]
        gain = self.templates[C05_TEMPLATE_SCENARIOS[1]]
        self.assertIs(
            verify_c05_fejer_recipe_template(self.parent, phase),
            phase,
        )
        self.assertIs(
            verify_c05_fejer_recipe_template(self.parent, gain),
            gain,
        )
        self.assertEqual(
            phase.integration_state,
            "PENDING_LIVE_PERMIT_T_BINDING",
        )
        self.assertEqual(
            gain.integration_state,
            "PENDING_LIVE_PERMIT_T_BINDING",
        )
        np.testing.assert_array_equal(
            frozen_tensor_array(phase.source_injection),
            frozen_tensor_array(gain.source_injection),
        )
        np.testing.assert_array_equal(
            frozen_tensor_array(phase.readout),
            frozen_tensor_array(gain.readout),
        )
        self.assertAlmostEqual(phase.requested_value, math.pi, places=15)
        self.assertEqual(gain.requested_value, 2.0)
        for order in (256, 512, 1024, 2048, 4096, 8192):
            phase_offset = _c05_phase_offset_for_order(phase, order)
            gain_offset = _c05_phase_offset_for_order(gain, order)
            self.assertAlmostEqual(
                phase_offset,
                math.pi / float(order),
                places=15,
            )
            self.assertGreater(
                abs(np.angle(_causal_fejer_scalar(phase_offset, order))),
                0.5,
            )
            self.assertAlmostEqual(
                abs(_causal_fejer_scalar(gain_offset, order)),
                0.5,
                places=13,
            )
            self.assertGreater(gain_offset, phase_offset)
            self.assertLess(gain_offset, 1.0 / 8.0)

    def test_c06_source_survives_but_cross_k_map_is_strictly_nonscalar(
        self,
    ) -> None:
        recipe = self.recipes[EXPECTED_SCENARIOS[0]]
        actual = _fejer_response_stack(recipe, "actual")
        ablated = _fejer_response_stack(recipe, "matched_ablated")
        survival = _source_survival(actual, ablated)
        self.assertEqual(len(survival), actual.shape[1])
        np.testing.assert_allclose(
            survival,
            np.ones(actual.shape[1]),
            rtol=0.0,
            atol=2.0e-12,
        )
        inner = np.vdot(ablated, actual)
        congruence = abs(inner) ** 2 / (
            float(np.vdot(actual, actual).real) * float(np.vdot(ablated, ablated).real)
        )
        self.assertLess(congruence, 0.90)
        self.assertGreater(congruence, 0.70)
        self.assertAlmostEqual(
            float(np.linalg.norm(actual) / np.linalg.norm(ablated)),
            1.0,
            places=12,
        )
        self.assertAlmostEqual(float(np.angle(inner)), 0.0, places=12)

    def test_c07_c08_and_c10_freeze_rank_and_orthogonality_teeth(self) -> None:
        for scenario_id in (EXPECTED_SCENARIOS[1], EXPECTED_SCENARIOS[2]):
            recipe = self.recipes[scenario_id]
            np.testing.assert_allclose(
                _output_survival(
                    _exact_shell_stack(recipe, "actual"),
                    _exact_shell_stack(recipe, "matched_ablated"),
                ),
                np.asarray((0.0, 1.0)),
                rtol=0.0,
                atol=2.0e-12,
            )
        c10 = self.recipes[EXPECTED_SCENARIOS[4]]
        actual = application_recipe_symbol(c10, math.pi / 2.0, "actual")
        ablated = application_recipe_symbol(
            c10,
            math.pi / 2.0,
            "matched_ablated",
        )
        actual_values, actual_vectors = np.linalg.eig(actual)
        ablated_values, ablated_vectors = np.linalg.eig(ablated)
        actual_column = actual_vectors[
            :,
            np.flatnonzero(
                (np.angle(actual_values) >= c10.reference_phase_band[0])
                & (np.angle(actual_values) <= c10.reference_phase_band[1])
            ),
        ]
        ablated_column = ablated_vectors[
            :,
            np.flatnonzero(
                (np.angle(ablated_values) >= c10.reference_phase_band[0])
                & (np.angle(ablated_values) <= c10.reference_phase_band[1])
            ),
        ]
        self.assertLessEqual(
            float((abs(ablated_column.conj().T @ actual_column) ** 2).item()),
            2.0e-12,
        )

    def test_recipe_tamper_and_raw_parent_are_fail_closed(self) -> None:
        recipe = self.recipes[EXPECTED_SCENARIOS[0]]
        with self.assertRaises((TypeError, ValueError)):
            build_application_recipe(  # type: ignore[arg-type]
                self.parent.manifest,
                EXPECTED_SCENARIOS[0],
            )
        with self.assertRaisesRegex(ValueError, "recipe"):
            verify_application_recipe(
                self.parent,
                dataclasses.replace(recipe, recipe_sha="f" * 64),
            )
        changed_step = dataclasses.replace(
            recipe.actual_steps[0],
            coefficient=recipe.actual_steps[0].coefficient + 0.125,
        )
        hostile = dataclasses.replace(
            recipe,
            actual_steps=(changed_step,) + recipe.actual_steps[1:],
        )
        with self.assertRaisesRegex(ValueError, "recipe"):
            verify_application_recipe(self.parent, hostile)
        template = self.templates[C05_TEMPLATE_SCENARIOS[0]]
        with self.assertRaisesRegex(ValueError, "template"):
            verify_c05_fejer_recipe_template(
                self.parent,
                dataclasses.replace(template, template_sha="f" * 64),
            )

    def test_module_has_no_global_transform_or_per_momentum_projection_step(
        self,
    ) -> None:
        import rulespace_v3.application_recipes as module

        source = inspect.getsource(module).lower()
        self.assertNotIn("np.fft", source)
        self.assertNotIn("numpy.fft", source)
        self.assertNotIn("projector", source)
        self.assertNotIn("spatial_shape", inspect.getsource(build_application_recipe))


if __name__ == "__main__":
    unittest.main()
