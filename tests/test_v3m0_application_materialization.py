from __future__ import annotations

import dataclasses
import math
import unittest

import numpy as np

import rulespace_v3.application_materialization as materialization_module
import tests.test_v3m0_calibration_authority as calibration_authority_tests
from rulespace_v3.application_materialization import (
    ApplicationScenarioMaterialization,
    VerifiedV3M0ApplicationScenarioMaterialization,
    _reverify_verified_application_scenario_materialization,
    application_scenario_materialization_payload,
    materialize_v3m0_application_scenario,
    verify_v3m0_application_scenario_materialization,
)
from rulespace_v3.application_recipes import (
    APPLICATION_RECIPE_SCENARIO_IDS,
    _causal_fejer_scalar,
    _gain_phase_offset,
    application_recipe_symbol,
)
from rulespace_v3.calibration_authority import (
    issue_v3m0_calibration_application_permit,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import apply_factory_step
from rulespace_v3.response import compute_fejer_filtered_response
from rulespace_v3.trace import MechanismKind


SUCCESS_SCENARIOS = (
    *APPLICATION_RECIPE_SCENARIO_IDS,
)


def _plane_wave(
    vector: np.ndarray,
    length: int,
    mode: int,
) -> np.ndarray:
    momentum = 2.0 * math.pi * mode / length
    sites = np.arange(length, dtype=np.float64)
    return (
        vector[:, None] * np.exp(1.0j * momentum * sites)[None, :]
    ).astype(np.complex128)


class C05FiniteTResponseDiagnostics(unittest.TestCase):
    @staticmethod
    def _projector_transition(theta: float) -> np.ndarray:
        vector = np.asarray(
            (math.cos(theta), math.sin(theta)),
            dtype=np.complex128,
        )
        projector = np.outer(vector, vector.conj())
        return (1.0j * (2.0 * projector - np.eye(2))).astype(
            np.complex128
        )

    @classmethod
    def _cross_response(cls, theta: float, order: int) -> complex:
        response = compute_fejer_filtered_response(
            cls._projector_transition(theta),
            np.eye(2, dtype=np.complex128),
            math.pi / 2.0,
            order,
            np.asarray(((0.0,), (1.0,)), dtype=np.complex128),
            np.asarray(((1.0, 0.0),), dtype=np.complex128),
        )
        return complex(response[0, 0])

    def test_old_phase_offset_identity_contract_is_a_finite_t_no_go(
        self,
    ) -> None:
        for order in (256, 512, 1024, 2048, 4096, 8192):
            with self.subTest(order=order, scenario="phase"):
                phase_response = _causal_fejer_scalar(
                    math.pi / order,
                    order,
                )
                self.assertGreater(abs(phase_response + 1.0), 1.5)
                self.assertGreater(abs(abs(phase_response) - 1.0), 0.24)
            with self.subTest(order=order, scenario="gain"):
                offset = _gain_phase_offset(2.0, order)
                gain_response = _causal_fejer_scalar(offset, order)
                self.assertLess(abs(abs(gain_response) - 0.5), 3.0e-14)
                self.assertGreater(abs(gain_response - 0.5), 0.65)

    def test_equal_spectrum_projector_orientation_has_exact_finite_t_ratios(
        self,
    ) -> None:
        for order in (256, 512, 1024, 2048, 4096, 8192):
            with self.subTest(order=order, scenario="phase"):
                actual = self._cross_response(math.pi / 4.0, order)
                ablated = self._cross_response(-math.pi / 4.0, order)
                self.assertLessEqual(abs(actual + ablated), 1.0e-12)
                self.assertGreater(abs(actual), 0.49)
            with self.subTest(order=order, scenario="gain"):
                actual = self._cross_response(math.pi / 4.0, order)
                ablated = self._cross_response(math.pi / 12.0, order)
                self.assertLessEqual(abs(actual - 2.0 * ablated), 1.0e-12)
                self.assertGreater(abs(ablated), 0.24)
            for theta in (
                -math.pi / 4.0,
                math.pi / 12.0,
                math.pi / 4.0,
            ):
                phases = np.sort(
                    np.angle(np.linalg.eigvals(self._projector_transition(theta)))
                )
                np.testing.assert_allclose(
                    phases,
                    np.asarray((-math.pi / 2.0, math.pi / 2.0)),
                    rtol=0.0,
                    atol=2.0e-15,
                )


class ApplicationScenarioMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        helper_type = (
            calibration_authority_tests.CalibrationApplicationPermitTests
        )
        helper_type.setUpClass()
        helper = helper_type()
        cls.parent = helper.parent
        cls.calibration = helper._successful_calibration()
        applications = {
            item.control_case_id: item
            for item in cls.parent.manifest.synthetic_control_application_specs
        }
        cls.permits = {}
        for case_id in (
            "C04_CANONICAL_ANGLE_025_075",
            "C05_PHASE_AND_SCALAR_GAIN",
            "C06_INTERNAL_NONSCALE_MIXING",
            "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
            "C08_RANK_R_MISSING_MODES",
            "C09_PURE_GAUGE_DRESSING",
            "C10_FULL_SOURCE_EXTRA_MODE",
            "C11_NULL_GREY_SIGNAL_AMPLITUDE",
            "C12_NU_INC_IR_NORMALIZATION",
        ):
            cls.permits[case_id] = issue_v3m0_calibration_application_permit(
                cls.parent,
                cls.calibration,
                applications[case_id].application_instance_id,
            )
        cls.by_scenario = {}
        for scenario_id in SUCCESS_SCENARIOS:
            application = next(
                item
                for item in applications.values()
                if any(
                    scenario.scenario_id == scenario_id
                    for scenario in item.scenario_execution_specs
                )
            )
            permit = cls.permits[application.control_case_id]
            wrapper = materialize_v3m0_application_scenario(
                permit,
                scenario_id,
            )
            authority = materialization_module._MATERIALIZATION_LIVE[id(wrapper)][
                1
            ]
            cls.by_scenario[scenario_id] = (
                permit,
                wrapper,
                authority.snapshot,
                authority.actual,
                authority.ablated,
            )

    def test_all_c06_c12_success_scenarios_bind_full_live_chain(self) -> None:
        for scenario_id, (
            permit,
            wrapper,
            raw,
            actual,
            ablated,
        ) in self.by_scenario.items():
            with self.subTest(scenario_id=scenario_id):
                self.assertIsInstance(
                    wrapper,
                    VerifiedV3M0ApplicationScenarioMaterialization,
                )
                self.assertIsInstance(raw, ApplicationScenarioMaterialization)
                self.assertEqual(raw.permit, permit.permit)
                self.assertEqual(raw.scenario_spec.scenario_id, scenario_id)
                self.assertEqual(
                    raw.scenario_sha,
                    raw.scenario_spec.scenario_sha,
                )
                self.assertEqual(raw.run_spec.permit_sha, raw.permit.permit_sha)
                self.assertEqual(raw.run_spec.scenario_id, scenario_id)
                self.assertEqual(
                    raw.run_spec.scenario_sha,
                    raw.scenario_spec.scenario_sha,
                )
                self.assertEqual(
                    raw.selected_fejer_order,
                    raw.permit.selected_fejer_order,
                )
                self.assertEqual(
                    raw.run_spec.fejer_order,
                    raw.selected_fejer_order,
                )
                self.assertEqual(
                    raw.run_spec.source_basis,
                    raw.permit.source_basis,
                )
                self.assertEqual(
                    raw.run_spec.readout_basis,
                    raw.permit.readout_basis,
                )
                self.assertEqual(
                    actual.factory.source_manifest_id,
                    raw.run_spec.source_basis.manifest_id,
                )
                self.assertEqual(
                    ablated.factory.source_manifest_id,
                    raw.run_spec.source_basis.manifest_id,
                )
                self.assertEqual(
                    actual.factory.readout_basis,
                    raw.run_spec.readout_basis,
                )
                self.assertEqual(
                    ablated.factory.readout_basis,
                    raw.run_spec.readout_basis,
                )
                self.assertEqual(
                    len(raw.ablation_pair_snapshot.ablation_manifest.replacements),
                    sum(
                        primitive.kind is MechanismKind.TARGET_CONDITIONED
                        for primitive in raw.construction_trace.primitives
                    ),
                )
                self.assertTrue(
                    all(
                        primitive.depends_on == ()
                        for primitive in raw.construction_trace.primitives
                    )
                )
                self.assertNotEqual(
                    raw.actual_effect_digest,
                    raw.matched_ablated_effect_digest,
                )
                self.assertNotIn(
                    "source_action",
                    raw.run_spec.__dataclass_fields__,
                )
                self.assertNotIn(
                    "source_action",
                    raw.application_recipe.__dataclass_fields__,
                )

    def test_real_executor_matches_bound_recipe_symbols(self) -> None:
        vector = np.asarray(
            (1.0 + 0.25j, -0.5 + 0.1j, 0.2 - 0.7j, 0.9 + 0.3j),
            dtype=np.complex128,
        )
        for scenario_id, (_, _, raw, actual, ablated) in self.by_scenario.items():
            length = actual.factory.state_shape[1]
            for mode in (1, 2, 3):
                with self.subTest(scenario_id=scenario_id, mode=mode):
                    momentum = 2.0 * math.pi * mode / length
                    state = _plane_wave(vector, length, mode)
                    expected_actual = application_recipe_symbol(
                        raw.application_recipe,
                        momentum,
                        "actual",
                    )
                    expected_ablated = application_recipe_symbol(
                        raw.application_recipe,
                        momentum,
                        "matched_ablated",
                    )
                    np.testing.assert_allclose(
                        apply_factory_step(actual, state)[:, 0],
                        expected_actual @ vector,
                        rtol=0.0,
                        atol=2.0e-12,
                    )
                    np.testing.assert_allclose(
                        apply_factory_step(ablated, state)[:, 0],
                        expected_ablated @ vector,
                        rtol=0.0,
                        atol=2.0e-12,
                    )

    def test_hydration_and_authority_attacks_fail_closed(self) -> None:
        scenario_id = APPLICATION_RECIPE_SCENARIO_IDS[0]
        permit, _, raw, _, _ = self.by_scenario[scenario_id]
        hydrated = verify_v3m0_application_scenario_materialization(
            raw,
            permit,
            scenario_id,
        )
        self.assertIsInstance(
            hydrated,
            VerifiedV3M0ApplicationScenarioMaterialization,
        )

        first_operator = dataclasses.replace(
            raw.operator_payload[0],
            layer_slot_id=raw.operator_payload[0].layer_slot_id + ".tampered",
        )
        provisional = dataclasses.replace(
            raw,
            operator_payload=(first_operator, *raw.operator_payload[1:]),
            materialization_sha="0" * 64,
        )
        resigned = dataclasses.replace(
            provisional,
            materialization_sha=canonical_sha(
                application_scenario_materialization_payload(provisional)
            ),
        )
        with self.assertRaisesRegex(ValueError, "closed replay|differs"):
            verify_v3m0_application_scenario_materialization(
                resigned,
                permit,
                scenario_id,
            )

        other_permit = self.permits[
            "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE"
        ]
        with self.assertRaises((TypeError, ValueError)):
            verify_v3m0_application_scenario_materialization(
                raw,
                other_permit,
                scenario_id,
            )

        first_id, second_id = APPLICATION_RECIPE_SCENARIO_IDS[:2]
        first_permit, _, first_raw, _, _ = self.by_scenario[first_id]
        with self.assertRaisesRegex(ValueError, "differs|scenario"):
            verify_v3m0_application_scenario_materialization(
                first_raw,
                first_permit,
                second_id,
            )

        forged = object.__new__(
            VerifiedV3M0ApplicationScenarioMaterialization
        )
        with self.assertRaises((TypeError, ValueError)):
            _reverify_verified_application_scenario_materialization(forged)

        disposable = verify_v3m0_application_scenario_materialization(
            raw,
            permit,
            scenario_id,
        )
        exposed = object.__getattribute__(
            disposable,
            "_VerifiedV3M0ApplicationScenarioMaterialization__materialization",
        )
        object.__setattr__(exposed, "interface_sha", "e" * 64)
        with self.assertRaisesRegex(ValueError, "seal|immutable|replay"):
            _reverify_verified_application_scenario_materialization(
                disposable
            )

    def test_scope_rejects_c04_c05_and_typed_c11_scenarios(self) -> None:
        c04_permit = self.permits["C04_CANONICAL_ANGLE_025_075"]
        c04_scenario = c04_permit.permit.application_spec.scenario_execution_specs[
            0
        ]
        with self.assertRaisesRegex(ValueError, "C06-C12|outside"):
            materialize_v3m0_application_scenario(
                c04_permit,
                c04_scenario.scenario_id,
            )

        c05_permit = self.permits["C05_PHASE_AND_SCALAR_GAIN"]
        for scenario in c05_permit.permit.application_spec.scenario_execution_specs:
            with self.subTest(scenario=scenario.scenario_id):
                with self.assertRaisesRegex(ValueError, "C06-C12|outside"):
                    materialize_v3m0_application_scenario(
                        c05_permit,
                        scenario.scenario_id,
                    )

        c11_permit = self.permits["C11_NULL_GREY_SIGNAL_AMPLITUDE"]
        for scenario in c11_permit.permit.application_spec.scenario_execution_specs[
            :2
        ]:
            with self.subTest(scenario=scenario.scenario_id):
                with self.assertRaisesRegex(ValueError, "BLOCK_SUCCESS|outside"):
                    materialize_v3m0_application_scenario(
                        c11_permit,
                        scenario.scenario_id,
                    )

        with self.assertRaises((TypeError, ValueError)):
            materialize_v3m0_application_scenario(  # type: ignore[arg-type]
                c11_permit.permit,
                APPLICATION_RECIPE_SCENARIO_IDS[-2],
            )


if __name__ == "__main__":
    unittest.main()
