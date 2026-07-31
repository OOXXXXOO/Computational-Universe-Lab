from __future__ import annotations

import dataclasses
import math
import unittest

import numpy as np

import tests.test_v3m0_window_thresholds as window_test_helpers
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.causal import (
    CausalNumericalThresholds,
    compute_causal_spectrum,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    PrimitiveInterface,
    apply_factory_step,
    build_basis_manifest,
    build_factory_from_trace,
    factory_support_offsets,
    freeze_complex_tensor,
    frozen_tensor_array,
)
from rulespace_v3.interference_mode_preflight import (
    CANDIDATE_FEJER_ORDERS,
    INTERFERENCE_MODE_PREFLIGHT_STATE,
    INTERFERENCE_MODE_SCENARIO_IDS,
    PREFLIGHT_MOMENTA,
    build_interference_mode_preflight_artifact,
    build_interference_mode_preflight_trace_and_operators,
    interference_mode_preflight_artifact_payload,
    interference_mode_preflight_symbol,
    verify_interference_mode_preflight_artifact,
)
from rulespace_v3.parent_freeze import (
    build_v3m0_parent_freeze_candidate,
)
from rulespace_v3.response import (
    _extract_projector_candidates,
    compute_fejer_filtered_response,
)
from rulespace_v3.trace import MechanismKind


THRESHOLDS = CausalNumericalThresholds(
    absolute_signal_threshold=1.0e-3,
    raw_noise_floor=1.0e-12,
    relative_gap_min=1.0e3,
    survival_threshold=0.5,
    survival_ambiguity_half_width=0.1,
)


def _plane_wave(vector: np.ndarray, *, length: int, momentum: float) -> np.ndarray:
    sites = np.arange(length, dtype=np.float64)
    return (vector[:, None] * np.exp(1.0j * momentum * sites)[None, :]).astype(
        np.complex128
    )


def _factory_pair(artifact, target, *, length: int):
    interface = PrimitiveInterface(
        interface_id=f"interface.interference-mode.{artifact.scenario_kind}.L{length}.v1",
        state_schema_id=artifact.state_schema_id,
        spatial_ndim=artifact.spatial_ndim,
        channel_order=artifact.channel_order,
        dtype="complex128",
        backend="numpy",
    )
    trace, operators = build_interference_mode_preflight_trace_and_operators(
        artifact,
        target_spec_id=target.target_spec_id,
        interface=interface,
    )
    source = build_basis_manifest(
        role="source",
        state_schema_id=interface.state_schema_id,
        channel_order=interface.channel_order,
        vectors=frozen_tensor_array(artifact.source_injection).T,
    )
    readout = build_basis_manifest(
        role="readout",
        state_schema_id=interface.state_schema_id,
        channel_order=interface.channel_order,
        vectors=frozen_tensor_array(artifact.readout).conj(),
    )
    actual = build_factory_from_trace(
        trace,
        target,
        factory_id=f"factory.interference-mode.{artifact.scenario_kind}.L{length}.v1",
        interface=interface,
        state_shape=(len(artifact.channel_order), length),
        dt=0.25,
        target_blind_parameters=(("interference-mode-preflight", 1.0),),
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


class InterferenceModePreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = build_v3m0_parent_freeze_candidate()
        cls.artifacts = {
            scenario_id: build_interference_mode_preflight_artifact(
                cls.candidate,
                scenario_id,
            )
            for scenario_id in INTERFERENCE_MODE_SCENARIO_IDS
        }
        cls.target = window_test_helpers._window_controls((8,))[0].target

    def test_inert_artifacts_consume_exact_candidate_scenarios_and_selectors(
        self,
    ) -> None:
        expected = {
            "constructive": ((1.0,), 0.0, 0.0, 1, "CANDIDATE_RANK_UNCHANGED"),
            "destructive": ((0.0,), 1.0, 1.0, 1, "CANDIDATE_RANK_UNCHANGED"),
            "rank_missing": (
                (0.0, 1.0),
                0.0,
                0.5,
                2,
                "REQUIRES_PARENT_RANK_REFREEZE_1_TO_2",
            ),
            "extra_mode": ((0.0,), 1.0, None, 1, "CANDIDATE_RANK_UNCHANGED"),
        }
        expected_shapes = {
            "constructive": ((4, 1), (1, 4), (0,)),
            "destructive": ((4, 1), (2, 4), (0,)),
            "rank_missing": ((4, 2), (2, 4), (0, 1)),
            "extra_mode": ((4, 2), (2, 4), (0,)),
        }
        expected_source_readout = {
            "constructive": (
                np.asarray(((1.0,), (0.0,), (0.0,), (0.0,)), dtype=np.complex128),
                np.asarray(((0.0, 1.0, 0.0, 0.0),), dtype=np.complex128),
            ),
            "destructive": (
                np.asarray(
                    ((0.5,), (0.0,), (math.sqrt(3.0) / 2.0,), (0.0,)),
                    dtype=np.complex128,
                ),
                np.asarray(
                    ((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
                    dtype=np.complex128,
                ),
            ),
            "rank_missing": (
                np.asarray(
                    ((1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (0.0, 0.0)),
                    dtype=np.complex128,
                ),
                np.asarray(
                    ((0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
                    dtype=np.complex128,
                ),
            ),
            "extra_mode": (
                np.asarray(
                    ((0.0, 1.0), (0.0, 0.0), (1.0, 0.0), (0.0, 0.0)),
                    dtype=np.complex128,
                ),
                np.asarray(
                    ((0.0, 0.0, 0.0, 1.0), (0.0, 1.0, 0.0, 0.0)),
                    dtype=np.complex128,
                ),
            ),
        }
        candidate_scenarios = {
            scenario.scenario_execution_spec.scenario_id: scenario
            for application in self.candidate.application_candidates
            for scenario in application.scenario_candidates
        }
        for artifact in self.artifacts.values():
            with self.subTest(kind=artifact.scenario_kind):
                self.assertIs(
                    verify_interference_mode_preflight_artifact(
                        artifact,
                        self.candidate,
                    ),
                    artifact,
                )
                self.assertEqual(
                    artifact.construction_state,
                    INTERFERENCE_MODE_PREFLIGHT_STATE,
                )
                prediction = expected[artifact.scenario_kind]
                self.assertEqual(artifact.expected_survival_spectrum, prediction[0])
                self.assertEqual(artifact.expected_chi_extra, prediction[1])
                self.assertEqual(artifact.expected_d_proc_sq, prediction[2])
                self.assertEqual(artifact.expected_actual_shell_rank, prediction[3])
                self.assertEqual(artifact.candidate_rank_disposition, prediction[4])
                self.assertEqual(
                    artifact.candidate_selector_disposition,
                    "REQUIRES_PARENT_SELECTOR_REFREEZE",
                )
                self.assertEqual(
                    artifact.source_readout_role,
                    "PROPOSED_PARENT_SELECTOR",
                )
                self.assertFalse(hasattr(artifact, "selector_sha"))
                self.assertEqual(
                    artifact.based_on_candidate_selector_sha,
                    candidate_scenarios[
                        artifact.scenario_id
                    ].selector_spec.selector_sha,
                )
                source_shape, readout_shape, sector = expected_shapes[
                    artifact.scenario_kind
                ]
                self.assertEqual(
                    frozen_tensor_array(artifact.source_injection).shape,
                    source_shape,
                )
                self.assertEqual(
                    frozen_tensor_array(artifact.readout).shape,
                    readout_shape,
                )
                self.assertEqual(artifact.actual_sector_source_columns, sector)
                self.assertEqual(artifact.expected_matched_shell_rank, 1)
                frozen_source, frozen_readout = expected_source_readout[
                    artifact.scenario_kind
                ]
                candidate_source = frozen_tensor_array(
                    artifact.candidate_source_injection
                )
                candidate_readout = frozen_tensor_array(
                    artifact.candidate_readout_coisometry
                )
                proposed_source_selection = frozen_tensor_array(
                    artifact.proposed_source_selection
                )
                proposed_readout_selection = frozen_tensor_array(
                    artifact.proposed_readout_selection
                )
                np.testing.assert_array_equal(
                    candidate_source,
                    np.eye(4, dtype=np.complex128),
                )
                np.testing.assert_array_equal(
                    candidate_readout,
                    np.eye(4, dtype=np.complex128),
                )
                np.testing.assert_array_equal(
                    frozen_tensor_array(artifact.source_injection),
                    frozen_source,
                )
                np.testing.assert_array_equal(
                    frozen_tensor_array(artifact.readout),
                    frozen_readout,
                )
                np.testing.assert_array_equal(
                    frozen_tensor_array(artifact.source_injection),
                    candidate_source @ proposed_source_selection,
                )
                np.testing.assert_array_equal(
                    frozen_tensor_array(artifact.readout),
                    proposed_readout_selection @ candidate_readout,
                )
                self.assertNotEqual(
                    candidate_source.shape,
                    frozen_tensor_array(artifact.source_injection).shape,
                )
                self.assertNotEqual(
                    candidate_readout.shape,
                    frozen_tensor_array(artifact.readout).shape,
                )
                self.assertEqual(
                    artifact.parent_candidate_sha, self.candidate.candidate_sha
                )
                self.assertFalse(
                    any(
                        hasattr(artifact, field)
                        for field in (
                            "parent_freeze",
                            "permit",
                            "response_block",
                            "evidence",
                            "passed",
                            "scientific_status",
                        )
                    )
                )
        constructive = next(
            item
            for item in self.artifacts.values()
            if item.scenario_kind == "constructive"
        )
        self.assertEqual(constructive.constructive_delta, math.pi / 8192.0)
        rank_missing = next(
            item
            for item in self.artifacts.values()
            if item.scenario_kind == "rank_missing"
        )
        self.assertEqual(rank_missing.candidate_expected_actual_shell_rank, 1)
        self.assertEqual(rank_missing.expected_actual_shell_rank, 2)

    def test_self_hash_unknown_field_resign_and_splice_attacks_are_red(self) -> None:
        artifact = self.artifacts[INTERFERENCE_MODE_SCENARIO_IDS[0]]
        with self.assertRaisesRegex(ValueError, "SHA"):
            verify_interference_mode_preflight_artifact(
                dataclasses.replace(artifact, preflight_sha="0" * 64),
                self.candidate,
            )

        unknown = build_interference_mode_preflight_artifact(
            self.candidate,
            INTERFERENCE_MODE_SCENARIO_IDS[0],
        )
        object.__setattr__(unknown, "caller_unknown", "forged")
        with self.assertRaisesRegex(ValueError, "unknown|missing"):
            verify_interference_mode_preflight_artifact(unknown, self.candidate)

        nested = build_interference_mode_preflight_artifact(
            self.candidate,
            INTERFERENCE_MODE_SCENARIO_IDS[0],
        )
        object.__setattr__(nested.actual_steps[0], "caller_unknown", "forged")
        with self.assertRaisesRegex(ValueError, "unknown|missing"):
            verify_interference_mode_preflight_artifact(nested, self.candidate)

        resigned_body = dataclasses.replace(artifact, expected_chi_extra=0.25)
        resigned = dataclasses.replace(
            resigned_body,
            preflight_sha=canonical_sha(
                interference_mode_preflight_artifact_payload(resigned_body)
            ),
        )
        with self.assertRaisesRegex(ValueError, "canonical|prediction"):
            verify_interference_mode_preflight_artifact(resigned, self.candidate)

        disposition_body = dataclasses.replace(artifact)
        object.__setattr__(
            disposition_body,
            "candidate_selector_disposition",
            "SELECTOR_ALREADY_APPROVED",
        )
        object.__setattr__(
            disposition_body,
            "preflight_sha",
            canonical_sha(
                interference_mode_preflight_artifact_payload(disposition_body)
            ),
        )
        with self.assertRaisesRegex(ValueError, "selector|disposition|authority"):
            verify_interference_mode_preflight_artifact(
                disposition_body,
                self.candidate,
            )

        role_body = dataclasses.replace(artifact)
        object.__setattr__(
            role_body,
            "source_readout_role",
            "CURRENT_PARENT_SELECTOR",
        )
        object.__setattr__(
            role_body,
            "preflight_sha",
            canonical_sha(interference_mode_preflight_artifact_payload(role_body)),
        )
        with self.assertRaisesRegex(ValueError, "source|readout|role|authority"):
            verify_interference_mode_preflight_artifact(role_body, self.candidate)

        hostile_source_values = -frozen_tensor_array(artifact.source_injection)
        source_body = dataclasses.replace(
            artifact,
            source_injection=freeze_complex_tensor(hostile_source_values),
        )
        source_resigned = dataclasses.replace(
            source_body,
            preflight_sha=canonical_sha(
                interference_mode_preflight_artifact_payload(source_body)
            ),
        )
        with self.assertRaisesRegex(ValueError, "source|mechanical|canonical"):
            verify_interference_mode_preflight_artifact(
                source_resigned,
                self.candidate,
            )

        other = self.artifacts[INTERFERENCE_MODE_SCENARIO_IDS[1]]
        spliced_body = dataclasses.replace(artifact, scenario_sha=other.scenario_sha)
        spliced = dataclasses.replace(
            spliced_body,
            preflight_sha=canonical_sha(
                interference_mode_preflight_artifact_payload(spliced_body)
            ),
        )
        with self.assertRaisesRegex(ValueError, "scenario|canonical"):
            verify_interference_mode_preflight_artifact(spliced, self.candidate)

        hostile_candidate = dataclasses.replace(
            self.candidate,
            candidate_sha="0" * 64,
        )
        with self.assertRaisesRegex(ValueError, "candidate|SHA"):
            verify_interference_mode_preflight_artifact(
                artifact,
                hostile_candidate,
            )

    def test_matched_program_only_deletes_conditioned_scalar_shear_slots(self) -> None:
        expected_conditioned = {
            "constructive": 3,
            "destructive": 12,
            "rank_missing": 3,
            "extra_mode": 12,
        }
        for artifact in self.artifacts.values():
            trace, pair = _factory_pair(artifact, self.target, length=8)
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
            with self.subTest(kind=artifact.scenario_kind):
                self.assertEqual(
                    len(conditioned),
                    expected_conditioned[artifact.scenario_kind],
                )
                self.assertEqual(len(blind), 9)
                self.assertEqual(len(pair.manifest.replacements), len(conditioned))
                self.assertEqual(
                    artifact.matched_ablated_steps,
                    tuple(
                        step
                        for step in artifact.actual_steps
                        if not step.target_conditioned
                    ),
                )
                self.assertTrue(
                    all(step.offset == (0,) for step in artifact.actual_steps)
                )
                self.assertTrue(
                    all(
                        step.coefficient in (-1.0, 1.0)
                        for step in artifact.actual_steps
                        if "constructive.rotation" not in step.step_id
                    )
                )

    def test_compiled_transitions_match_the_frozen_analytic_matrices(self) -> None:
        j_block = np.asarray(((0.0, -1.0), (1.0, 0.0)), dtype=np.complex128)
        negative_identity = -np.eye(2, dtype=np.complex128)

        def direct_sum(left: np.ndarray, right: np.ndarray) -> np.ndarray:
            result = np.zeros((4, 4), dtype=np.complex128)
            result[:2, :2] = left
            result[2:, 2:] = right
            return result

        expected = {
            "constructive": (
                direct_sum(j_block, negative_identity),
                direct_sum(
                    np.asarray(
                        (
                            (
                                math.cos(math.pi / 2.0 - math.pi / 8192.0),
                                -math.sin(math.pi / 2.0 - math.pi / 8192.0),
                            ),
                            (
                                math.sin(math.pi / 2.0 - math.pi / 8192.0),
                                math.cos(math.pi / 2.0 - math.pi / 8192.0),
                            ),
                        ),
                        dtype=np.complex128,
                    ),
                    negative_identity,
                ),
            ),
            "destructive": (
                direct_sum(negative_identity, j_block),
                direct_sum(j_block, negative_identity),
            ),
            "rank_missing": (
                direct_sum(j_block, j_block),
                direct_sum(j_block, negative_identity),
            ),
            "extra_mode": (
                direct_sum(negative_identity, j_block),
                direct_sum(j_block, negative_identity),
            ),
        }
        for artifact in self.artifacts.values():
            actual_expected, matched_expected = expected[artifact.scenario_kind]
            with self.subTest(kind=artifact.scenario_kind):
                np.testing.assert_allclose(
                    interference_mode_preflight_symbol(
                        artifact,
                        math.pi / 4.0,
                        "actual",
                    ),
                    actual_expected,
                    rtol=0.0,
                    atol=5.0e-16,
                )
                np.testing.assert_allclose(
                    interference_mode_preflight_symbol(
                        artifact,
                        math.pi / 4.0,
                        "matched_ablated",
                    ),
                    matched_expected,
                    rtol=0.0,
                    atol=5.0e-16,
                )

        destructive = next(
            item
            for item in self.artifacts.values()
            if item.scenario_kind == "destructive"
        )
        (candidate,) = _extract_projector_candidates(
            interference_mode_preflight_symbol(
                destructive,
                math.pi / 4.0,
                "actual",
            ),
            np.eye(4, dtype=np.complex128),
            (destructive.reference_phase_band,),
            256,
            frozen_tensor_array(destructive.source_injection),
            frozen_tensor_array(destructive.readout),
        )
        self.assertEqual(candidate.rank, 1)
        self.assertAlmostEqual(candidate.participation, 3.0 / 8.0, places=14)

    def test_realspace_factory_bridge_is_local_unitary_symplectic_and_real(
        self,
    ) -> None:
        identity = np.eye(4, dtype=np.complex128)
        vector = np.asarray(
            (1.0, 2.0j, -0.5, 0.25j),
            dtype=np.complex128,
        )
        for artifact in self.artifacts.values():
            canonical = frozen_tensor_array(artifact.canonical_structure)
            for length in (8, 16):
                _, pair = _factory_pair(artifact, self.target, length=length)
                self.assertEqual(factory_support_offsets(pair.actual, 1), ((0,),))
                self.assertEqual(factory_support_offsets(pair.actual, 8), ((0,),))
                self.assertEqual(factory_support_offsets(pair.ablated, 8), ((0,),))
                for branch, factory in (
                    ("actual", pair.actual),
                    ("matched_ablated", pair.ablated),
                ):
                    for momentum in PREFLIGHT_MOMENTA:
                        symbol = interference_mode_preflight_symbol(
                            artifact,
                            momentum,
                            branch,
                        )
                        opposite = interference_mode_preflight_symbol(
                            artifact,
                            -momentum,
                            branch,
                        )
                        state = _plane_wave(
                            vector,
                            length=length,
                            momentum=momentum,
                        )
                        observed = apply_factory_step(factory, state)[:, 0]
                        with self.subTest(
                            kind=artifact.scenario_kind,
                            length=length,
                            branch=branch,
                            momentum=momentum,
                        ):
                            bridge_residual = float(
                                np.linalg.norm(observed - symbol @ vector, 2)
                            )
                            self.assertLessEqual(bridge_residual, 1.0e-12)
                            self.assertLessEqual(
                                float(
                                    np.linalg.norm(
                                        symbol.conj().T @ symbol - identity, 2
                                    )
                                ),
                                1.0e-12,
                            )
                            self.assertLessEqual(
                                float(
                                    np.linalg.norm(
                                        opposite.T @ canonical @ symbol - canonical, 2
                                    )
                                ),
                                1.0e-12,
                            )
                            self.assertLessEqual(
                                float(np.linalg.norm(opposite - symbol.conj(), 2)),
                                1.0e-12,
                            )

    def test_all_frozen_orders_and_momenta_reproduce_rank_and_causal_predictions(
        self,
    ) -> None:
        metric = np.eye(4, dtype=np.complex128)
        endpoint_norms = {
            "constructive": (
                (0.7043553929, 0.7070204750),
                (0.5335735096, 0.7049728868),
            ),
            "destructive": ((0.6099896636, 0.6122976923), (0.3521776965, 0.3535102375)),
        }
        observed_norms: dict[str, tuple[list[float], list[float]]] = {
            "constructive": ([], []),
            "destructive": ([], []),
        }
        expected_ablated_ranks = {
            "constructive": (1, 1),
            "destructive": (1, 1),
            "rank_missing": (1, 1),
            "extra_mode": (0, 1),
        }
        for artifact in self.artifacts.values():
            source = frozen_tensor_array(artifact.source_injection)
            readout = frozen_tensor_array(artifact.readout)
            sector = artifact.actual_sector_source_columns
            symbols = {
                branch: tuple(
                    interference_mode_preflight_symbol(
                        artifact,
                        momentum,
                        branch,
                    )
                    for momentum in PREFLIGHT_MOMENTA
                )
                for branch in ("actual", "matched_ablated")
            }
            for order in CANDIDATE_FEJER_ORDERS:
                actual_responses = []
                matched_responses = []
                for momentum_index, _momentum in enumerate(PREFLIGHT_MOMENTA):
                    actual_responses.append(
                        compute_fejer_filtered_response(
                            symbols["actual"][momentum_index],
                            metric,
                            artifact.reference_phase,
                            order,
                            source,
                            readout,
                        )
                    )
                    matched_responses.append(
                        compute_fejer_filtered_response(
                            symbols["matched_ablated"][momentum_index],
                            metric,
                            artifact.reference_phase,
                            order,
                            source,
                            readout,
                        )
                    )
                actual = np.vstack(actual_responses).astype(np.complex128)
                matched = np.vstack(matched_responses).astype(np.complex128)
                actual_on_sector = actual[:, sector]
                matched_on_sector = matched[:, sector]
                spectrum = compute_causal_spectrum(
                    actual_on_sector,
                    matched_on_sector,
                    matched,
                    thresholds=THRESHOLDS,
                )
                with self.subTest(kind=artifact.scenario_kind, order=order):
                    self.assertEqual(spectrum.actual_rank, len(sector))
                    expected_sector_rank, expected_full_rank = expected_ablated_ranks[
                        artifact.scenario_kind
                    ]
                    self.assertEqual(spectrum.ablated_rank, expected_sector_rank)
                    self.assertEqual(spectrum.ablated_all_rank, expected_full_rank)
                    np.testing.assert_allclose(
                        spectrum.survival_spectrum,
                        artifact.expected_survival_spectrum,
                        rtol=0.0,
                        atol=1.0e-12,
                    )
                    self.assertAlmostEqual(
                        spectrum.chi_extra,
                        artifact.expected_chi_extra,
                        places=12,
                    )
                    self.assertEqual(
                        spectrum.d_proc_sq,
                        artifact.expected_d_proc_sq,
                    )
                    self.assertEqual(
                        int(
                            np.count_nonzero(
                                np.linalg.svd(actual, compute_uv=False) >= 1.0e-3
                            )
                        ),
                        artifact.expected_actual_shell_rank,
                    )
                    self.assertEqual(
                        int(
                            np.count_nonzero(
                                np.linalg.svd(matched, compute_uv=False) >= 1.0e-3
                            )
                        ),
                        artifact.expected_matched_shell_rank,
                    )
                if artifact.scenario_kind in observed_norms:
                    observed_norms[artifact.scenario_kind][0].append(
                        float(np.linalg.norm(actual, ord="fro"))
                    )
                    observed_norms[artifact.scenario_kind][1].append(
                        float(np.linalg.norm(matched, ord="fro"))
                    )

        for kind, (actual_values, matched_values) in observed_norms.items():
            actual_expected, matched_expected = endpoint_norms[kind]
            self.assertAlmostEqual(min(actual_values), actual_expected[0], places=9)
            self.assertAlmostEqual(max(actual_values), actual_expected[1], places=9)
            self.assertAlmostEqual(min(matched_values), matched_expected[0], places=9)
            self.assertAlmostEqual(max(matched_values), matched_expected[1], places=9)


if __name__ == "__main__":
    unittest.main()
