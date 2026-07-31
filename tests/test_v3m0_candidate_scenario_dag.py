"""Adversarial tests for all inert C05--C19 success-scenario DAGs."""

from __future__ import annotations

import math
import struct
import unittest
from dataclasses import replace

import numpy as np

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import frozen_tensor_array


PREFLIGHT_SCENARIOS = (
    "v3m0.synthetic-control.c07.v1.scenario.constructive.v1",
    "v3m0.synthetic-control.c07.v1.scenario.destructive.v1",
    "v3m0.synthetic-control.c08.v1.scenario.rank-missing.v1",
    "v3m0.synthetic-control.c10.v1.scenario.extra-mode.v1",
    "v3m0.synthetic-control.c12.v1.scenario.ir-normalization.v1",
)

EXPECTED_SCENARIOS = (
    "v3m0.synthetic-control.c05.v1.scenario.phase.v1",
    "v3m0.synthetic-control.c05.v1.scenario.gain.v1",
    "v3m0.synthetic-control.c06.v1.scenario.nonscale-mixing.v1",
    *PREFLIGHT_SCENARIOS[:2],
    PREFLIGHT_SCENARIOS[2],
    "v3m0.synthetic-control.c09.v1.scenario.gauge-dressing.v1",
    PREFLIGHT_SCENARIOS[3],
    "v3m0.synthetic-control.c11.v1.scenario.signal.v1",
    PREFLIGHT_SCENARIOS[4],
    "v3m0.synthetic-control.c15.v1.scenario.full-h.v1",
    "v3m0.synthetic-control.c15.v1.scenario.low-rank-tt.v1",
    "v3m0.synthetic-control.c15.v1.scenario.tt.v1",
    "v3m0.synthetic-control.c15.v1.scenario.tt-plus-row.v1",
    "v3m0.synthetic-control.c16.v1.scenario.coverage-low.v1",
    "v3m0.synthetic-control.c16.v1.scenario.coverage-high.v1",
    "v3m0.synthetic-control.c17.v1.scenario.quotient-gauge.v1",
    "v3m0.synthetic-control.c18.v1.scenario.independent-unary.v1",
    "v3m0.synthetic-control.c19.v1.scenario.observer-collapse.v1",
)

LIVE_RECIPE_SCENARIOS = tuple(
    scenario_id
    for scenario_id in EXPECTED_SCENARIOS
    if scenario_id not in PREFLIGHT_SCENARIOS
)


def _fp64_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _resign_operation(operation, **changes):
    from rulespace_v3.candidate_scenario_dag import (
        candidate_dag_operation_payload,
    )

    provisional = replace(operation, operation_sha="0" * 64, **changes)
    return replace(
        provisional,
        operation_sha=canonical_sha(candidate_dag_operation_payload(provisional)),
    )


def _resign_dag(dag, **changes):
    from rulespace_v3.candidate_scenario_dag import candidate_scenario_dag_payload

    provisional = replace(dag, dag_sha="0" * 64, **changes)
    return replace(
        provisional,
        dag_sha=canonical_sha(candidate_scenario_dag_payload(provisional)),
    )


def _resign_contract(contract, **changes):
    from rulespace_v3.candidate_scenario_dag import (
        compiled_candidate_scenario_contract_payload,
    )

    provisional = replace(contract, contract_sha="0" * 64, **changes)
    return replace(
        provisional,
        contract_sha=canonical_sha(
            compiled_candidate_scenario_contract_payload(provisional)
        ),
    )


def _parameter(operation, name: str):
    matches = tuple(item for item in operation.parameters if item.name == name)
    if len(matches) != 1:
        raise AssertionError(f"expected one parameter named {name!r}")
    return matches[0]


def _replace_parameter(operation, name: str, replacement):
    return _resign_operation(
        operation,
        parameters=tuple(
            replacement if item.name == name else item for item in operation.parameters
        ),
    )


def _step_physics(step) -> tuple[object, ...]:
    return (
        step.step_id,
        step.source_channel,
        step.destination_channel,
        step.offset,
        _fp64_bits(step.coefficient),
        step.target_conditioned,
    )


class CandidateScenarioDagTests(unittest.TestCase):
    """Only DAG-derived, pre-response contracts may leave this module."""

    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            CANDIDATE_DAG_SCENARIO_IDS,
            build_all_candidate_scenario_dags,
        )

        from rulespace_v3.parent_freeze import build_v3m0_parent_freeze_candidate

        cls.candidate_v1 = build_v3m0_parent_freeze_candidate()
        scenarios = {
            scenario.scenario_execution_spec.scenario_id: scenario
            for application in cls.candidate_v1.application_candidates
            for scenario in application.scenario_candidates
        }
        cls.selector_bindings = tuple(
            (scenario_id, scenarios[scenario_id].selector_spec.selector_sha)
            for scenario_id in EXPECTED_SCENARIOS
        )
        cls.dags = build_all_candidate_scenario_dags(cls.selector_bindings)
        cls.dag_by_scenario = {item.scenario_id: item for item in cls.dags}
        if tuple(CANDIDATE_DAG_SCENARIO_IDS) != EXPECTED_SCENARIOS:
            raise AssertionError("candidate scenario registry drifted")

    def test_all_nineteen_canonical_dags_have_exact_three_node_closure(self) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            verify_candidate_scenario_dag,
        )

        self.assertEqual(
            tuple(item.scenario_id for item in self.dags),
            EXPECTED_SCENARIOS,
        )
        for dag in self.dags:
            with self.subTest(scenario_id=dag.scenario_id):
                self.assertIs(verify_candidate_scenario_dag(dag), dag)
                self.assertEqual(
                    dag.construction_state,
                    "PROPOSED_PARENT_DAG_EXTRACT_ONLY",
                )
                self.assertEqual(len(dag.operations), 3)
                transition, selector, contract = dag.operations
                self.assertEqual(transition.input_operation_ids, ())
                self.assertEqual(selector.input_operation_ids, ())
                self.assertEqual(
                    contract.input_operation_ids,
                    (transition.operation_id, selector.operation_id),
                )
                self.assertEqual(dag.output_operation_ids, (contract.operation_id,))
                self.assertEqual(
                    len({item.operation_sha for item in dag.operations}), 3
                )

    def test_reviewed_five_contracts_remain_fully_extracted(self) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            candidate_shear_step_signature_payload,
            extract_candidate_scenario_contract,
            verify_compiled_candidate_scenario_contract,
        )

        expected = {
            PREFLIGHT_SCENARIOS[0]: {
                "support": 0,
                "sector": (0,),
                "ranks": (1, 1, 1, 1),
                "survival": (1.0,),
                "chi": 0.0,
                "dproc_state": "defined-v1",
                "dproc": 0.0,
                "shapes": ((4, 1), (1, 4)),
            },
            PREFLIGHT_SCENARIOS[1]: {
                "support": 0,
                "sector": (0,),
                "ranks": (1, 1, 1, 1),
                "survival": (0.0,),
                "chi": 1.0,
                "dproc_state": "defined-v1",
                "dproc": 1.0,
                "shapes": ((4, 1), (2, 4)),
            },
            PREFLIGHT_SCENARIOS[2]: {
                "support": 0,
                "sector": (0, 1),
                "ranks": (2, 1, 1, 1),
                "survival": (0.0, 1.0),
                "chi": 0.0,
                "dproc_state": "defined-v1",
                "dproc": 0.5,
                "shapes": ((4, 2), (2, 4)),
            },
            PREFLIGHT_SCENARIOS[3]: {
                "support": 0,
                "sector": (0,),
                "ranks": (1, 1, 0, 1),
                "survival": (0.0,),
                "chi": 1.0,
                "dproc_state": "undefined-v1",
                "dproc": None,
                "shapes": ((4, 2), (2, 4)),
            },
            PREFLIGHT_SCENARIOS[4]: {
                "support": 1,
                "sector": (0, 1),
                "ranks": (2, 2, 2, 2),
                "survival": (),
                "chi": 0.0,
                "dproc_state": "undefined-v1",
                "dproc": None,
                "shapes": ((4, 2), (4, 4)),
            },
        }
        for scenario_id in PREFLIGHT_SCENARIOS:
            dag = self.dag_by_scenario[scenario_id]
            with self.subTest(scenario_id=dag.scenario_id):
                contract = extract_candidate_scenario_contract(dag)
                self.assertIs(
                    verify_compiled_candidate_scenario_contract(dag, contract),
                    contract,
                )
                target = expected[dag.scenario_id]
                self.assertEqual(
                    contract.construction_state,
                    "PROPOSED_PARENT_DAG_EXTRACT_ONLY",
                )
                self.assertEqual(contract.dag_sha, dag.dag_sha)
                self.assertEqual(
                    contract.based_on_candidate_selector_sha,
                    dag.based_on_candidate_selector_sha,
                )
                self.assertEqual(contract.primitive_support_radius, target["support"])
                self.assertFalse(contract.uses_global_fft_projection)
                self.assertFalse(contract.uses_per_k_time_step_projector)
                self.assertEqual(
                    contract.actual_sector_source_columns,
                    target["sector"],
                )
                self.assertEqual(
                    (
                        contract.expected_actual_shell_rank,
                        contract.expected_matched_shell_rank,
                        contract.expected_matched_actual_sector_rank,
                        contract.expected_matched_full_source_rank,
                    ),
                    target["ranks"],
                )
                self.assertEqual(
                    contract.expected_survival_spectrum,
                    target["survival"],
                )
                self.assertEqual(contract.expected_chi_extra, target["chi"])
                self.assertEqual(
                    contract.expected_d_proc_state,
                    target["dproc_state"],
                )
                self.assertEqual(contract.expected_d_proc_sq, target["dproc"])
                self.assertEqual(
                    contract.proposed_source_selection.shape,
                    target["shapes"][0],
                )
                self.assertEqual(
                    contract.proposed_readout_selection.shape,
                    target["shapes"][1],
                )
                self.assertEqual(
                    contract.matched_ablated_step_signatures,
                    tuple(
                        step
                        for step in contract.actual_step_signatures
                        if not step.target_conditioned
                    ),
                )
                self.assertTrue(contract.actual_step_signatures)
                self.assertLessEqual(
                    max(
                        abs(step.offset[0]) for step in contract.actual_step_signatures
                    ),
                    target["support"],
                )
                self.assertRegex(contract.actual_program_sha, r"[0-9a-f]{64}\Z")
                self.assertRegex(
                    contract.matched_ablated_program_sha,
                    r"[0-9a-f]{64}\Z",
                )
                for signature in contract.actual_step_signatures:
                    self.assertEqual(
                        signature.signature_sha,
                        canonical_sha(
                            candidate_shear_step_signature_payload(signature)
                        ),
                    )

                consumed = dict(contract.consumed_parameter_names)
                self.assertEqual(
                    set(consumed),
                    {operation.operation_id for operation in dag.operations},
                )
                for operation in dag.operations:
                    self.assertEqual(
                        consumed[operation.operation_id],
                        tuple(item.name for item in operation.parameters),
                    )

    def test_selector_matrices_are_the_exact_closed_constructions(self) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            extract_candidate_scenario_contract,
        )

        root_two = math.sqrt(2.0)
        half_root_two = 1.0 / (2.0 * root_two)
        c12_frame = np.asarray(
            (
                (1.0 / root_two, 0.0, 1.0 / root_two, 0.0),
                (
                    -1.0j * half_root_two,
                    -0.5 + 1.0j * half_root_two,
                    1.0j * half_root_two,
                    0.5 - 1.0j * half_root_two,
                ),
                (0.0, 1.0 / root_two, 0.0, 1.0 / root_two),
                (
                    0.5 + 1.0j * half_root_two,
                    1.0j * half_root_two,
                    -0.5 - 1.0j * half_root_two,
                    -1.0j * half_root_two,
                ),
            ),
            dtype=np.complex128,
        )
        expected = {
            PREFLIGHT_SCENARIOS[0]: (
                np.asarray(((1.0,), (0.0,), (0.0,), (0.0,))),
                np.asarray(((0.0, 1.0, 0.0, 0.0),)),
            ),
            PREFLIGHT_SCENARIOS[1]: (
                np.asarray(((0.5,), (0.0,), (math.sqrt(3.0) / 2.0,), (0.0,))),
                np.asarray(((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))),
            ),
            PREFLIGHT_SCENARIOS[2]: (
                np.asarray(((1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (0.0, 0.0))),
                np.asarray(((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))),
            ),
            PREFLIGHT_SCENARIOS[3]: (
                np.asarray(((0.0, 1.0), (0.0, 0.0), (1.0, 0.0), (0.0, 0.0))),
                np.asarray(((0.0, 0.0, 0.0, 1.0), (0.0, 1.0, 0.0, 0.0))),
            ),
            PREFLIGHT_SCENARIOS[4]: (
                c12_frame[:, :2],
                np.eye(4, dtype=np.complex128),
            ),
        }
        for scenario_id in PREFLIGHT_SCENARIOS:
            dag = self.dag_by_scenario[scenario_id]
            with self.subTest(scenario_id=dag.scenario_id):
                contract = extract_candidate_scenario_contract(dag)
                source, readout = expected[dag.scenario_id]
                np.testing.assert_array_equal(
                    frozen_tensor_array(contract.proposed_source_selection),
                    source,
                )
                np.testing.assert_array_equal(
                    frozen_tensor_array(contract.proposed_readout_selection),
                    readout,
                )

    def test_c12_cyclotomic_incidence_and_closed_threshold_refs(self) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            candidate_incidence_point_contract_payload,
            extract_candidate_scenario_contract,
        )

        contract = extract_candidate_scenario_contract(
            self.dag_by_scenario[PREFLIGHT_SCENARIOS[4]]
        )
        self.assertEqual(
            contract.incidence_family_id,
            "synthetic-lattice-laplacian-incidence-v1",
        )
        self.assertEqual(
            contract.incidence_normalizer_formula_id,
            "nu-inc-4-sum-sin2-half-v1",
        )
        self.assertEqual(
            contract.incidence_application_stage,
            "POST_RESPONSE_READOUT_ONLY",
        )
        self.assertEqual(contract.incidence_stencil_offsets, ((-1,), (0,), (1,)))
        self.assertEqual(contract.incidence_stencil_coefficients, (-1, 2, -1))
        self.assertEqual(contract.ir_limit_order, 2)
        self.assertEqual(
            contract.ir_limit_formula_id,
            "lim-k-to-zero-nu-inc-over-k-squared-equals-one-v1",
        )
        self.assertEqual(contract.response_torus_denominator, 8)
        self.assertEqual(contract.response_reciprocal_indices, ((1,), (2,)))
        self.assertEqual(
            contract.absolute_signal_threshold_authority_ref,
            "WindowThresholdSelection.curv_tau_sig",
        )
        self.assertEqual(
            contract.raw_bridge_noise_evidence_ref,
            "SourceReadoutBridgeAudit.curv_operator_error_max",
        )
        self.assertEqual(
            contract.raw_noise_absolute_threshold_authority_ref,
            "rulespace_v3.thresholds.BRIDGE_TOLERANCE",
        )
        self.assertEqual(
            contract.relative_gap_threshold_authority_ref,
            "rulespace_v3.thresholds.RAW_GAP_MIN",
        )
        first, second = contract.incidence_points
        for point in contract.incidence_points:
            self.assertEqual(
                point.point_sha,
                canonical_sha(candidate_incidence_point_contract_payload(point)),
            )
        self.assertEqual(first.reciprocal_index, (1,))
        self.assertEqual(first.exact_nu_expression, "2 - sqrt(2)")
        self.assertEqual(first.nu_minimal_polynomial_coefficients, (1, -4, 2))
        self.assertEqual(_fp64_bits(first.nu_value), 0x3FE2BEC333018866)
        self.assertEqual(second.reciprocal_index, (2,))
        self.assertEqual(second.exact_nu_expression, "2")
        self.assertEqual(second.nu_minimal_polynomial_coefficients, (1, -2))
        self.assertEqual(_fp64_bits(second.nu_value), 0x4000000000000000)

    def test_preflight_steps_selectors_and_c12_points_are_reproduced(self) -> None:
        from rulespace_v3.c12_incidence_preflight import (
            build_c12_incidence_preflight,
        )
        from rulespace_v3.candidate_scenario_dag import (
            build_candidate_scenario_dag,
            extract_candidate_scenario_contract,
        )
        from rulespace_v3.interference_mode_preflight import (
            INTERFERENCE_MODE_SCENARIO_IDS,
            build_interference_mode_preflight_artifact,
        )
        from rulespace_v3.parent_freeze import build_v3m0_parent_freeze_candidate

        candidate = build_v3m0_parent_freeze_candidate()
        scenarios = {
            scenario.scenario_execution_spec.scenario_id: scenario
            for application in candidate.application_candidates
            for scenario in application.scenario_candidates
        }
        for scenario_id in INTERFERENCE_MODE_SCENARIO_IDS:
            with self.subTest(scenario_id=scenario_id):
                selector_sha = scenarios[scenario_id].selector_spec.selector_sha
                contract = extract_candidate_scenario_contract(
                    build_candidate_scenario_dag(
                        scenario_id,
                        based_on_candidate_selector_sha=selector_sha,
                    )
                )
                preflight = build_interference_mode_preflight_artifact(
                    candidate,
                    scenario_id,
                )
                self.assertEqual(
                    tuple(map(_step_physics, contract.actual_step_signatures)),
                    tuple(map(_step_physics, preflight.actual_steps)),
                )
                self.assertEqual(
                    tuple(
                        map(
                            _step_physics,
                            contract.matched_ablated_step_signatures,
                        )
                    ),
                    tuple(map(_step_physics, preflight.matched_ablated_steps)),
                )
                np.testing.assert_array_equal(
                    frozen_tensor_array(contract.proposed_source_selection),
                    frozen_tensor_array(preflight.proposed_source_selection),
                )
                np.testing.assert_array_equal(
                    frozen_tensor_array(contract.proposed_readout_selection),
                    frozen_tensor_array(preflight.proposed_readout_selection),
                )

        scenario_id = PREFLIGHT_SCENARIOS[4]
        c12_preflight = build_c12_incidence_preflight(candidate)
        selector_sha = scenarios[scenario_id].selector_spec.selector_sha
        c12_contract = extract_candidate_scenario_contract(
            build_candidate_scenario_dag(
                scenario_id,
                based_on_candidate_selector_sha=selector_sha,
            )
        )
        self.assertEqual(
            tuple(map(_step_physics, c12_contract.actual_step_signatures)),
            tuple(map(_step_physics, c12_preflight.recipe.actual_steps)),
        )
        self.assertEqual(
            tuple(
                map(
                    _step_physics,
                    c12_contract.matched_ablated_step_signatures,
                )
            ),
            tuple(map(_step_physics, c12_preflight.recipe.matched_ablated_steps)),
        )
        np.testing.assert_array_equal(
            frozen_tensor_array(c12_contract.proposed_source_selection),
            frozen_tensor_array(
                c12_preflight.recipe.proposed_selector_spec.source_selector
            ),
        )
        np.testing.assert_array_equal(
            frozen_tensor_array(c12_contract.proposed_readout_selection),
            frozen_tensor_array(
                c12_preflight.recipe.proposed_selector_spec.readout_selector
            ),
        )
        self.assertEqual(
            tuple(
                (
                    point.reciprocal_index,
                    _fp64_bits(point.momentum),
                    point.exact_nu_expression,
                    point.nu_minimal_polynomial_coefficients,
                    _fp64_bits(point.nu_value),
                )
                for point in c12_contract.incidence_points
            ),
            tuple(
                (
                    point.reciprocal_index,
                    _fp64_bits(point.momentum),
                    point.exact_nu_expression,
                    point.nu_minimal_polynomial_coefficients,
                    _fp64_bits(point.nu_value),
                )
                for point in c12_preflight.ir_certificate.point_wires
            ),
        )

    def test_all_nineteen_contracts_bind_live_program_effect_selector_and_context(
        self,
    ) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            extract_candidate_scenario_contract,
        )
        from rulespace_v3.parent_freeze import build_v3m0_parent_freeze_candidate

        candidate = build_v3m0_parent_freeze_candidate()
        scenario_by_id = {
            scenario.scenario_execution_spec.scenario_id: scenario
            for application in candidate.application_candidates
            for scenario in application.scenario_candidates
        }
        for scenario_id in EXPECTED_SCENARIOS:
            with self.subTest(scenario_id=scenario_id):
                contract = extract_candidate_scenario_contract(
                    self.dag_by_scenario[scenario_id]
                )
                source_scenario = scenario_by_id[scenario_id]
                if scenario_id in LIVE_RECIPE_SCENARIOS:
                    self.assertEqual(
                        contract.proposed_source_selection.tensor_sha,
                        source_scenario.selector_spec.source_selector.tensor_sha,
                    )
                    self.assertEqual(
                        contract.proposed_readout_selection.tensor_sha,
                        source_scenario.selector_spec.readout_selector.tensor_sha,
                    )
                self.assertRegex(contract.construction_recipe_sha, r"[0-9a-f]{64}\Z")
                self.assertRegex(
                    contract.construction_operation_dag_sha,
                    r"[0-9a-f]{64}\Z",
                )
                self.assertTrue(contract.construction_rule_id)
                self.assertTrue(contract.construction_family_id)
                self.assertRegex(contract.actual_effect_digest, r"[0-9a-f]{64}\Z")
                self.assertRegex(
                    contract.matched_ablated_effect_digest,
                    r"[0-9a-f]{64}\Z",
                )
                self.assertEqual(
                    contract.response_torus_denominators,
                    source_scenario.response_template.response_torus_denominators,
                )
                self.assertEqual(
                    contract.response_reciprocal_indices,
                    source_scenario.response_template.response_reciprocal_indices,
                )
                self.assertEqual(
                    contract.source_readout_bridge_reciprocal_indices,
                    source_scenario.response_template.source_readout_bridge_reciprocal_indices,
                )
                self.assertEqual(
                    contract.source_readout_bridge_steps,
                    source_scenario.response_template.source_readout_bridge_steps,
                )
                self.assertEqual(
                    contract.reference_reciprocal_index,
                    source_scenario.response_template.reference_reciprocal_index,
                )
                self.assertEqual(
                    contract.preregistered_phase_bands,
                    source_scenario.response_template.preregistered_phase_bands,
                )
                np.testing.assert_array_equal(
                    frozen_tensor_array(contract.source_trial_vectors),
                    np.eye(contract.proposed_source_selection.shape[1], dtype=np.complex128),
                )

                if scenario_id.startswith(
                    (
                        "v3m0.synthetic-control.c15.",
                        "v3m0.synthetic-control.c16.",
                        "v3m0.synthetic-control.c17.",
                        "v3m0.synthetic-control.c18.",
                        "v3m0.synthetic-control.c19.",
                    )
                ):
                    self.assertIsNotNone(contract.geometry_operation_dag_sha)
                    self.assertTrue(contract.geometry_semantic_sector_names)
                    self.assertEqual(
                        contract.geometry_bundle_derivation_id,
                        source_scenario.response_template.geometry_bundle_derivation_id,
                    )
                else:
                    self.assertIsNone(contract.geometry_operation_dag_sha)
                    self.assertEqual(contract.geometry_semantic_sector_names, ())

    def test_live_root_and_evidence_accessors_replay_after_object_pollution(
        self,
    ) -> None:
        from rulespace_v3 import candidate_scenario_dag as dag_module

        scenario_id = (
            "v3m0.synthetic-control.c18.v1.scenario.independent-unary.v1"
        )
        candidate, _, scenarios = dag_module._live_candidate_roots()
        original_candidate_sha = candidate.candidate_sha
        source = scenarios[scenario_id][1]
        evidence = dag_module._live_construction_evidence(
            scenario_id,
            source.selector_spec.selector_sha,
        )
        cached_snapshot = dag_module._live_construction_evidence_bytes(
            scenario_id,
            source.selector_spec.selector_sha,
        )
        self.assertIs(type(cached_snapshot), bytes)
        original_matched_rank = evidence.expected_matched_shell_rank
        try:
            object.__setattr__(candidate, "candidate_sha", "f" * 64)
            object.__setattr__(evidence, "expected_matched_shell_rank", 1)
            replayed_candidate, _, replayed_scenarios = (
                dag_module._live_candidate_roots()
            )
            replayed_source = replayed_scenarios[scenario_id][1]
            replayed_evidence = dag_module._live_construction_evidence(
                scenario_id,
                replayed_source.selector_spec.selector_sha,
            )
            self.assertIsNot(replayed_candidate, candidate)
            self.assertIsNot(replayed_evidence, evidence)
            self.assertEqual(replayed_candidate.candidate_sha, original_candidate_sha)
            self.assertEqual(replayed_evidence.expected_matched_shell_rank, 2)
        finally:
            object.__setattr__(candidate, "candidate_sha", original_candidate_sha)
            object.__setattr__(
                evidence,
                "expected_matched_shell_rank",
                original_matched_rank,
            )

    def test_parameter_kind_and_value_attacks_fail_after_full_resign(self) -> None:
        from rulespace_v3.candidate_scenario_dag import verify_candidate_scenario_dag

        dag = self.dag_by_scenario[PREFLIGHT_SCENARIOS[0]]
        transition = dag.operations[0]
        delta = _parameter(transition, "delta-radians")
        attacks = (
            replace(
                delta,
                value_kind="integer",
                integer_value=1,
                fp64_bits_value=None,
            ),
            replace(
                delta,
                fp64_bits_value=delta.fp64_bits_value + 1,
            ),
        )
        for replacement in attacks:
            with self.subTest(replacement=replacement):
                attacked_operation = _replace_parameter(
                    transition,
                    "delta-radians",
                    replacement,
                )
                attacked_dag = _resign_dag(
                    dag,
                    operations=(attacked_operation, *dag.operations[1:]),
                )
                with self.assertRaises(ValueError):
                    verify_candidate_scenario_dag(attacked_dag)

    def test_operation_splice_and_dead_node_attacks_fail_after_resign(self) -> None:
        from rulespace_v3.candidate_scenario_dag import verify_candidate_scenario_dag

        constructive = self.dag_by_scenario[PREFLIGHT_SCENARIOS[0]]
        destructive = self.dag_by_scenario[PREFLIGHT_SCENARIOS[1]]
        constructive_selector = constructive.operations[1]
        foreign_selector = _resign_operation(
            destructive.operations[1],
            operation_id=constructive_selector.operation_id,
        )
        spliced = _resign_dag(
            constructive,
            operations=(
                constructive.operations[0],
                foreign_selector,
                constructive.operations[2],
            ),
        )
        with self.assertRaises(ValueError):
            verify_candidate_scenario_dag(spliced)

        dead = _resign_operation(
            constructive_selector,
            operation_id=f"{constructive_selector.operation_id}.dead",
        )
        dead_node_dag = _resign_dag(
            constructive,
            operations=(*constructive.operations, dead),
        )
        with self.assertRaises(ValueError):
            verify_candidate_scenario_dag(dead_node_dag)

    def test_unused_parameter_attack_fails_after_full_resign(self) -> None:
        from rulespace_v3.candidate_scenario_dag import verify_candidate_scenario_dag

        dag = self.dag_by_scenario[PREFLIGHT_SCENARIOS[0]]
        transition = dag.operations[0]
        unused = replace(
            transition.parameters[0],
            name="unused-output-bypass",
        )
        attacked_operation = _resign_operation(
            transition,
            parameters=tuple(
                sorted((*transition.parameters, unused), key=lambda x: x.name)
            ),
        )
        attacked = _resign_dag(
            dag,
            operations=(attacked_operation, *dag.operations[1:]),
        )
        with self.assertRaisesRegex(ValueError, "canonical|unconsumed|differ"):
            verify_candidate_scenario_dag(attacked)

    def test_c12_naive_sine_nu_one_ulp_attack_fails_after_full_resign(self) -> None:
        from rulespace_v3.candidate_scenario_dag import verify_candidate_scenario_dag

        dag = self.dag_by_scenario[PREFLIGHT_SCENARIOS[4]]
        incidence = dag.operations[2]
        exact = _parameter(incidence, "mode-0-nu")
        naive_bits = _fp64_bits(4.0 * math.sin(math.pi / 8.0) ** 2)
        self.assertEqual(exact.fp64_bits_value, 0x3FE2BEC333018866)
        self.assertEqual(naive_bits, exact.fp64_bits_value + 1)
        attacked_parameter = replace(exact, fp64_bits_value=naive_bits)
        attacked_operation = _replace_parameter(
            incidence,
            "mode-0-nu",
            attacked_parameter,
        )
        attacked = _resign_dag(
            dag,
            operations=(*dag.operations[:2], attacked_operation),
        )
        with self.assertRaises(ValueError):
            verify_candidate_scenario_dag(attacked)

    def test_compiled_contract_attack_fails_even_when_contract_is_resigned(
        self,
    ) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            extract_candidate_scenario_contract,
            verify_compiled_candidate_scenario_contract,
        )

        dag = self.dag_by_scenario[PREFLIGHT_SCENARIOS[1]]
        contract = extract_candidate_scenario_contract(dag)
        attacked = _resign_contract(contract, expected_chi_extra=0.0)
        with self.assertRaisesRegex(ValueError, "extraction|differs|canonical"):
            verify_compiled_candidate_scenario_contract(dag, attacked)

    def test_parameter_names_cannot_smuggle_measured_or_runtime_outcomes(self) -> None:
        from rulespace_v3.candidate_scenario_dag import (
            extract_candidate_scenario_contract,
        )

        for dag in self.dags:
            contract = extract_candidate_scenario_contract(dag)
            names = " ".join(
                parameter.name.lower()
                for operation in dag.operations
                for parameter in operation.parameters
            )
            serialized = f"{names} {contract!r}".lower()
            for forbidden in (
                "measured-",
                "selected-fejer",
                "singular-value",
                "sv-margin",
                "finite-t",
                "observed-",
            ):
                self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
