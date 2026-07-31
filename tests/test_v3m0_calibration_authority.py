from __future__ import annotations

import dataclasses
import unittest
from dataclasses import dataclass
from unittest import mock

import numpy as np

import rulespace_v3.calibration_authority as authority_module
import rulespace_v3.dynamics as dynamics_module
import rulespace_v3.prestructure as prestructure_module
from rulespace_v3.dynamics import (
    _transition_symbol_from_raw,
    measure_transition,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    _reverify_verified_factory,
    frozen_tensor_array,
)
from rulespace_v3.grids import (
    build_application_bridge_grid_manifest,
    build_response_grid_manifest,
)
from rulespace_v3.metric import build_stability_metric_witness
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.registry import (
    ControlReadoutCalibrationSpec,
    build_closed_control_registry,
    readout_calibration_spec_payload,
)
from rulespace_v3.window import (
    build_control_window_protocol_entries,
    build_window_calibration_protocol,
)
from rulespace_v3.structure import build_structure_manifest
from tests.test_v3m0_window_thresholds import _window_controls

from rulespace_v3.calibration_authority import (
    CalibrationApplicationPermit,
    ResponseBlockAttemptOutcome,
    SelectedControlEvidenceRef,
    V3M0ScenarioConstruction,
    VerifiedCalibrationApplicationPermit,
    VerifiedResponseBlockAttemptOutcome,
    VerifiedV3M0ScenarioConstruction,
    V3M0ApplicationResponseRunSpec,
    WindowCalibrationOutcome,
    WindowThresholdCalibrationManifest,
    WindowThresholdSelection,
    build_c04_canonical_angle_recipe,
    build_v3m0_application_response_run_spec,
    c04_canonical_angle_recipe_symbol,
    calibration_application_permit_payload,
    issue_v3m0_calibration_application_permit,
    issue_v3m0_application_prestructure_authority,
    issue_v3m0_response_block_attempt,
    materialize_v3m0_scenario_construction,
    response_block_attempt_outcome_payload,
    reverify_verified_response_block_attempt_outcome,
    v3m0_scenario_construction_payload,
    verify_calibration_application_permit,
    verify_response_block_attempt_outcome,
    verify_v3m0_application_response_run_spec,
    verify_v3m0_scenario_construction,
    verify_window_threshold_calibration,
    window_calibration_outcome_payload,
    window_threshold_calibration_manifest_payload,
    window_threshold_selection_payload,
)


@dataclass(frozen=True)
class _CandidateAudit:
    fejer_order: int

    def __deepcopy__(self, memo):
        del memo
        raise AssertionError("authority cloning dispatched to __deepcopy__")


class CalibrationApplicationPermitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
        cls.parent_manifest = cls.parent.manifest
        cls.controls = _window_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        entries = build_control_window_protocol_entries(cls.registry)
        cls.protocol = build_window_calibration_protocol(
            cls.registry,
            entries,
        )

    def _empty_candidate_outcome(self) -> WindowCalibrationOutcome:
        refs = tuple(
            SelectedControlEvidenceRef(
                control_id=entry.control_id,
                control_registry_entry_sha=entry.entry_sha,
                expected_rank_declaration_sha=(str(index + 1) * 64)[-64:],
                run_spec_sha=(str(index + 2) * 64)[-64:],
                paired_response_sha=(str(index + 3) * 64)[-64:],
                shell_manifest_sha=(str(index + 4) * 64)[-64:],
                comparison_2t_run_spec_sha=(str(index + 5) * 64)[-64:],
                comparison_2t_response_sha=(str(index + 6) * 64)[-64:],
                comparison_2t_shell_manifest_sha=(str(index + 7) * 64)[-64:],
            )
            for index, entry in enumerate(self.registry.registry.entries)
        )
        provisional_selection = WindowThresholdSelection(
            selected_fejer_order=256,
            h_scale_ref=1.0,
            h_noise_ref=1.0e-6,
            h_signal_min=1.0,
            h_tau_sig=1.0e-3,
            curv_scale_ref=1.0,
            curv_noise_ref=1.0e-6,
            curv_signal_min=1.0,
            curv_tau_sig=1.0e-3,
            selected_evidence_refs=refs,
            selection_sha="0" * 64,
        )
        selection = dataclasses.replace(
            provisional_selection,
            selection_sha=canonical_sha(
                window_threshold_selection_payload(provisional_selection)
            ),
        )
        provisional_manifest = WindowThresholdCalibrationManifest(
            calibration_schema_version=(
                "v3m0.window-threshold-calibration-manifest.v1"
            ),
            control_registry=self.registry.registry,
            window_protocol=self.protocol.protocol,
            candidate_audits=(),
            calibration_manifest_sha="0" * 64,
        )
        manifest = dataclasses.replace(
            provisional_manifest,
            calibration_manifest_sha=canonical_sha(
                window_threshold_calibration_manifest_payload(provisional_manifest)
            ),
        )
        from rulespace_v3.contracts import BlockStatus

        provisional_outcome = WindowCalibrationOutcome(
            status=BlockStatus(True, None),
            manifest=manifest,
            selection=selection,
            outcome_sha="0" * 64,
        )
        return dataclasses.replace(
            provisional_outcome,
            outcome_sha=canonical_sha(
                window_calibration_outcome_payload(provisional_outcome)
            ),
        )

    def _successful_calibration(self):
        cached = getattr(type(self), "_cached_calibration", None)
        if cached is not None:
            return cached
        empty = self._empty_candidate_outcome()
        provisional_manifest = dataclasses.replace(
            empty.manifest,
            candidate_audits=tuple(
                _CandidateAudit(fejer_order=order)
                for order in authority_module.T_CANDIDATES
            ),
            calibration_manifest_sha="0" * 64,
        )
        manifest = dataclasses.replace(
            provisional_manifest,
            calibration_manifest_sha=canonical_sha(
                window_threshold_calibration_manifest_payload(provisional_manifest)
            ),
        )
        provisional_outcome = dataclasses.replace(
            empty,
            manifest=manifest,
            outcome_sha="0" * 64,
        )
        outcome = dataclasses.replace(
            provisional_outcome,
            outcome_sha=canonical_sha(
                window_calibration_outcome_payload(provisional_outcome)
            ),
        )
        result = verify_window_threshold_calibration(
            outcome,
            self.registry,
            self.protocol,
        )
        type(self)._cached_calibration = result
        return result

    def _application_permit(self, ordinal: int = 4):
        calibration = self._successful_calibration()
        spec = self.parent_manifest.synthetic_control_application_specs[ordinal - 1]
        permit = issue_v3m0_calibration_application_permit(
            self.parent,
            calibration,
            spec.application_instance_id,
        )
        return calibration, spec, permit

    @staticmethod
    def _scenario_id(spec, index: int = 0) -> str:
        return spec.scenario_execution_specs[index].scenario_id

    def test_fake_calibration_or_parent_cannot_issue_permit(self) -> None:
        instance_id = self.parent_manifest.synthetic_control_application_specs[
            3
        ].application_instance_id
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_calibration_application_permit(
                self.parent,
                object(),
                instance_id,
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_calibration_application_permit(
                object(),
                object(),
                instance_id,
            )

    def test_calibration_authority_rejects_missing_six_candidate_audits(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "six|candidate"):
            verify_window_threshold_calibration(
                self._empty_candidate_outcome(),
                self.registry,
                self.protocol,
            )

    def test_raw_self_hashed_permit_is_not_a_live_capability(self) -> None:
        self.assertEqual(
            tuple(CalibrationApplicationPermit.__dataclass_fields__),
            (
                "permit_schema_version",
                "scope",
                "parent_freeze",
                "application_spec",
                "calibration_manifest",
                "selection",
                "selected_fejer_order",
                "window_protocol",
                "response_grid",
                "source_readout_bridge_grid",
                "source_readout_bridge_steps",
                "reference_reciprocal_index",
                "preregistered_phase_bands",
                "expected_shell_rank",
                "expected_shell_rank_source_id",
                "source_basis",
                "readout_basis",
                "readout_calibration_spec",
                "permit_sha",
            ),
        )
        forbidden = {
            "paired_response",
            "control_evidence",
            "transition",
            "certificate",
            "physical_adapter",
        }
        self.assertTrue(
            forbidden.isdisjoint(CalibrationApplicationPermit.__dataclass_fields__)
        )
        raw = object.__new__(CalibrationApplicationPermit)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            calibration_application_permit_payload(raw)
        fake = object.__new__(VerifiedCalibrationApplicationPermit)
        with self.assertRaises((TypeError, ValueError)):
            fake.permit

    def test_application_grids_and_readout_spec_are_uniquely_derived(self) -> None:
        spec = self.parent_manifest.synthetic_control_application_specs[3]
        response = build_response_grid_manifest(spec)
        bridge = build_application_bridge_grid_manifest(spec)
        protocol = spec.readout_protocol
        provisional = ControlReadoutCalibrationSpec(
            spec_schema_version=("v3m0.control-readout-calibration-spec.v1"),
            source_metric_whitener=protocol.source_metric_whitener,
            h_metric_whitener=protocol.h_metric_whitener,
            curvature_incidence_operator=(protocol.curvature_incidence_operator),
            curvature_metric_whitener=(protocol.curvature_metric_whitener),
            curvature_normalizer_id=protocol.curvature_normalizer_id,
            spec_sha="0" * 64,
        )
        derived = dataclasses.replace(
            provisional,
            spec_sha=canonical_sha(readout_calibration_spec_payload(provisional)),
        )
        self.assertEqual(
            response.reciprocal_indices,
            spec.grid_protocol.response_reciprocal_indices,
        )
        self.assertEqual(
            bridge.reciprocal_indices,
            spec.grid_protocol.bridge_reciprocal_indices,
        )
        self.assertEqual(
            derived.source_metric_whitener,
            protocol.source_metric_whitener,
        )

    def test_application_run_spec_has_no_caller_metric_or_operator_fields(
        self,
    ) -> None:
        self.assertEqual(
            tuple(V3M0ApplicationResponseRunSpec.__dataclass_fields__),
            (
                "run_spec_schema_version",
                "permit_sha",
                "application_spec_sha",
                "fejer_order",
                "source_basis",
                "readout_basis",
                "response_grid",
                "source_readout_bridge_grid",
                "source_readout_bridge_steps",
                "source_trial_vectors",
                "bridge_tolerance",
                "run_spec_sha",
            ),
        )
        forbidden = {
            "source_metric",
            "physical_h_metric",
            "curvature_operator",
            "paired_response",
            "control_evidence",
        }
        self.assertTrue(
            forbidden.isdisjoint(V3M0ApplicationResponseRunSpec.__dataclass_fields__)
        )

    def test_run_spec_and_permit_verifiers_reject_object_new_wrappers(
        self,
    ) -> None:
        fake = object.__new__(VerifiedCalibrationApplicationPermit)
        with self.assertRaises((TypeError, ValueError)):
            build_v3m0_application_response_run_spec(fake)
        raw_run = object.__new__(V3M0ApplicationResponseRunSpec)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            verify_v3m0_application_response_run_spec(raw_run, fake)
        raw_permit = object.__new__(CalibrationApplicationPermit)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            verify_calibration_application_permit(
                raw_permit,
                self.parent,
                object(),
            )

    def test_oversized_raw_permit_caps_before_hash_or_upstream_replay(
        self,
    ) -> None:
        raw = object.__new__(CalibrationApplicationPermit)
        for field in CalibrationApplicationPermit.__dataclass_fields__:
            object.__setattr__(raw, field, None)
        object.__setattr__(raw, "permit_schema_version", "v1")
        object.__setattr__(raw, "scope", "x" * 20_000)
        with (
            mock.patch.object(
                authority_module,
                "canonical_sha",
                side_effect=AssertionError("hash ran first"),
            ),
            mock.patch.object(
                authority_module,
                "_reverify_verified_parent_freeze",
                side_effect=AssertionError("parent replay ran first"),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "resource cap"):
                verify_calibration_application_permit(
                    raw,
                    object(),
                    object(),
                )

    def test_application_construction_schema_is_snapshot_only(self) -> None:
        self.assertEqual(
            tuple(V3M0ScenarioConstruction.__dataclass_fields__),
            (
                "construction_schema_version",
                "permit",
                "scenario_spec",
                "operation_evaluations",
                "operation_effect_digests",
                "recipe_id",
                "recipe_derivation_source_id",
                "recipe_parameter_reads",
                "recipe_sha",
                "construction_status",
                "ablation_pair_snapshot",
                "interface_sha",
                "source_basis_sha",
                "readout_basis_sha",
                "response_grid_sha",
                "bridge_grid_sha",
                "run_spec_sha",
                "actual_effect_digest",
                "ablated_effect_digest",
                "actual_factory_sha",
                "ablated_factory_sha",
                "ablation_manifest_sha",
                "ablation_construction_sha",
                "construction_sha",
            ),
        )
        self.assertNotIn(
            "live_construction",
            V3M0ScenarioConstruction.__dataclass_fields__,
        )
        fake = object.__new__(VerifiedV3M0ScenarioConstruction)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            _ = fake.construction

    def test_closed_dag_materializes_unique_local_matched_pair(self) -> None:
        _, spec, permit = self._application_permit()
        scenario_id = self._scenario_id(spec)
        construction = materialize_v3m0_scenario_construction(
            permit,
            scenario_id,
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )
        raw = construction_view.construction
        actual = _reverify_verified_factory(construction_view.actual)
        ablated = _reverify_verified_factory(construction_view.ablated)

        self.assertTrue(raw.construction_status.defined)
        self.assertEqual(raw.permit, permit.permit)
        self.assertEqual(raw.actual_factory_sha, actual.factory.factory_sha)
        self.assertEqual(raw.ablated_factory_sha, ablated.factory.factory_sha)
        self.assertNotEqual(raw.actual_factory_sha, raw.ablated_factory_sha)
        self.assertEqual(actual.factory.channel_order, ("q0", "p0", "q1", "p1"))
        self.assertEqual(actual.factory.state_shape, (4, 8))
        self.assertEqual(ablated.factory.state_shape, actual.factory.state_shape)
        self.assertEqual(
            {primitive.offset for primitive in actual.factory.primitives},
            {(-1,), (0,), (1,)},
        )
        self.assertEqual(
            {
                offset
                for primitive in actual.factory.primitives
                for offset in primitive.support_offsets
            },
            {(-1,), (0,), (1,)},
        )
        self.assertEqual(len(actual.factory.primitives), 57)
        self.assertEqual(
            len(raw.ablation_pair_snapshot.ablation_manifest.replacements),
            12,
        )
        self.assertNotEqual(raw.actual_effect_digest, raw.ablated_effect_digest)
        provenance_ids = {node.provenance_id for node in actual.trace.provenance_nodes}
        self.assertTrue(
            {operation.operation_instance_id for operation in spec.operations}.issubset(
                provenance_ids
            )
        )

        hydrated = verify_v3m0_scenario_construction(
            raw,
            permit,
            scenario_id,
        )
        self.assertIs(type(hydrated), VerifiedV3M0ScenarioConstruction)
        self.assertEqual(
            raw.construction_sha,
            canonical_sha(v3m0_scenario_construction_payload(raw)),
        )

    def test_application_authorities_run_real_fp64_unitary_symplectic_steps(
        self,
    ) -> None:
        _, spec, permit = self._application_permit()
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )
        identity = np.eye(4, dtype=np.complex128)
        symplectic_form = np.kron(
            np.eye(2, dtype=np.complex128),
            np.asarray(
                ((0.0, 1.0), (-1.0, 0.0)),
                dtype=np.complex128,
            ),
        )
        recipe = build_c04_canonical_angle_recipe()

        for role, factory in (
            ("actual", construction_view.actual),
            ("matched_ablated", construction_view.ablated),
        ):
            prestructure = issue_v3m0_application_prestructure_authority(
                permit,
                construction,
                role,
            )
            transition = measure_transition(factory, prestructure)
            raw_transition = transition.transition
            if role == "actual":
                injected_provisional = dataclasses.replace(
                    raw_transition,
                    dt=raw_transition.dt + 1.0,
                    transition_sha="0" * 64,
                )
                injected_raw = dataclasses.replace(
                    injected_provisional,
                    transition_sha=canonical_sha(
                        dynamics_module.measured_transition_payload(
                            injected_provisional
                        )
                    ),
                )
                injected = dynamics_module._register_measured_transition(
                    injected_raw,
                    factory,
                    prestructure,
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "immutable seal mismatch",
                ):
                    dynamics_module._reverify_verified_transition(injected)
                with self.assertRaisesRegex(
                    ValueError,
                    "immutable seal mismatch",
                ):
                    dynamics_module.transition_symbol(
                        injected,
                        np.asarray((0.0,), dtype=np.float64),
                    )
            self.assertLessEqual(
                max(abs(offset[0]) for offset in raw_transition.support_offsets),
                2,
            )
            self.assertEqual(
                prestructure.authority.authority_kind,
                "synthetic-application-v1",
            )
            self.assertEqual(
                prestructure.authority.synthetic_application_permit_sha,
                permit.permit.permit_sha,
            )
            self.assertEqual(
                prestructure.authority.synthetic_application_scenario_spec,
                construction_view.construction.scenario_spec,
            )
            for momentum in (np.pi / 4.0, np.pi / 2.0):
                matrix = _transition_symbol_from_raw(
                    raw_transition,
                    np.asarray((momentum,), dtype=np.float64),
                )
                opposite = _transition_symbol_from_raw(
                    raw_transition,
                    np.asarray((-momentum,), dtype=np.float64),
                )
                np.testing.assert_allclose(
                    matrix,
                    c04_canonical_angle_recipe_symbol(
                        recipe,
                        float(momentum),
                        role,
                    ),
                    rtol=0.0,
                    atol=1.0e-12,
                )
                self.assertLessEqual(
                    float(
                        np.linalg.norm(
                            matrix.conj().T @ matrix - identity,
                            ord=2,
                        )
                    ),
                    1.0e-12,
                )
                self.assertLessEqual(
                    float(
                        np.linalg.norm(
                            opposite.T @ symplectic_form @ matrix - symplectic_form,
                            ord=2,
                        )
                    ),
                    1.0e-12,
                )
                np.testing.assert_allclose(
                    opposite,
                    matrix.conj(),
                    rtol=0.0,
                    atol=1.0e-12,
                )

    def test_application_authority_mechanically_derives_j_and_identity_metric(
        self,
    ) -> None:
        _, spec, permit = self._application_permit()
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )
        expected_j = np.kron(
            np.eye(2, dtype=np.complex128),
            np.asarray(
                ((0.0, 1.0), (-1.0, 0.0)),
                dtype=np.complex128,
            ),
        )
        for role, factory in (
            ("actual", construction_view.actual),
            ("matched_ablated", construction_view.ablated),
        ):
            authority = issue_v3m0_application_prestructure_authority(
                permit,
                construction,
                role,
            )
            structure = build_structure_manifest(factory, authority)
            metric = build_stability_metric_witness(
                factory,
                authority,
                structure,
            )
            np.testing.assert_array_equal(
                frozen_tensor_array(structure.structure_form),
                expected_j,
            )
            np.testing.assert_array_equal(
                frozen_tensor_array(metric.metric_kernel)[0],
                np.eye(4, dtype=np.complex128),
            )
            self.assertEqual(
                metric.metric_origin.derivation_or_preregistration_sha,
                permit.permit.application_spec.application_spec_sha,
            )

    def test_construction_rejects_cross_permit_and_unissued_wrapper(self) -> None:
        _, spec, first_permit = self._application_permit(4)
        _, _, same_body_other_permit = self._application_permit(4)
        _, _, wrong_case_permit = self._application_permit(5)
        scenario_id = self._scenario_id(spec)
        first = materialize_v3m0_scenario_construction(
            first_permit,
            scenario_id,
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_v3m0_scenario_construction(
                first.construction,
                wrong_case_permit,
                scenario_id,
            )
        fake = object.__new__(VerifiedV3M0ScenarioConstruction)
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                first_permit,
                fake,
                "actual",
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                same_body_other_permit,
                first,
                "actual",
            )

    def test_application_role_authority_requires_live_permit_and_construction(
        self,
    ) -> None:
        _, spec, permit = self._application_permit(4)
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        construction_view = authority_module._reverify_verified_scenario_construction(
            construction
        )

        authority = issue_v3m0_application_prestructure_authority(
            permit,
            construction,
            "actual",
        )
        self.assertEqual(
            authority.authority.synthetic_application_permit_sha,
            permit.permit.permit_sha,
        )
        self.assertEqual(
            authority.authority.synthetic_scenario_construction_sha,
            construction_view.construction.construction_sha,
        )

        with self.assertRaises((TypeError, ValueError)):
            prestructure_module._issue_synthetic_application_prestructure_authority(
                self.parent,
                spec,
                "f" * 64,
                construction_view.outcome,
                "actual",
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                object(),
                construction,
                "actual",
            )
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                permit,
                object(),
                "actual",
            )

        _, _, other_permit = self._application_permit(5)
        with self.assertRaises((TypeError, ValueError)):
            issue_v3m0_application_prestructure_authority(
                other_permit,
                construction,
                "actual",
            )

    def test_operation_parameters_change_scenario_effect_digest(self) -> None:
        _, spec, permit = self._application_permit(4)
        construction = materialize_v3m0_scenario_construction(
            permit,
            self._scenario_id(spec),
        )
        raw = authority_module._reverify_verified_scenario_construction(
            construction
        ).construction
        self.assertEqual(len(raw.operation_effect_digests), 3)
        self.assertEqual(
            len({digest for _, digest in raw.operation_effect_digests}),
            3,
        )
        self.assertNotEqual(raw.actual_effect_digest, raw.ablated_effect_digest)
        self.assertNotEqual(
            raw.ablation_pair_snapshot.actual_factory.runtime_operator_sha,
            raw.ablation_pair_snapshot.ablated_factory.runtime_operator_sha,
        )

    def test_expected_typed_terminations_are_replayed_and_never_issue_downstream(
        self,
    ) -> None:
        self.assertEqual(
            tuple(ResponseBlockAttemptOutcome.__dataclass_fields__),
            (
                "attempt_schema_version",
                "application_spec",
                "scenario_spec",
                "permit",
                "terminal_stage",
                "status",
                "raw_singular_values",
                "activation_labels",
                "precursor_evidence_sha",
                "downstream_capability_issued",
                "outcome_sha",
            ),
        )
        expected = {
            11: (
                ("activation", "response_null", (0.0,), ("null",)),
                ("activation", "response_grey", (0.5,), ("grey",)),
            ),
            13: (
                ("activation", "response_null", (0.0, 0.0), ("null", "null")),
            ),
            14: (
                (
                    "endpoint_shell",
                    "endpoint_shell_ambiguous",
                    (1.0,),
                    ("signal",),
                ),
                ("activation", "response_null", (0.0,), ("null",)),
                ("trace", "trace_unclassified", (), ()),
                ("stability", "unstable", (), ()),
            ),
        }
        first_attempt = None
        first_permit = None
        first_scenario_id = None
        for ordinal, expected_scenarios in expected.items():
            _, spec, permit = self._application_permit(ordinal)
            for scenario, (
                terminal_stage,
                reason_value,
                singular_values,
                activation_labels,
            ) in zip(spec.scenario_execution_specs, expected_scenarios):
                attempt = issue_v3m0_response_block_attempt(
                    permit,
                    scenario.scenario_id,
                )
                self.assertIs(type(attempt), VerifiedResponseBlockAttemptOutcome)
                raw = reverify_verified_response_block_attempt_outcome(attempt)
                self.assertEqual(raw.application_spec, spec)
                self.assertEqual(raw.scenario_spec, scenario)
                self.assertEqual(raw.permit, permit.permit)
                self.assertEqual(raw.terminal_stage, terminal_stage)
                self.assertFalse(raw.status.defined)
                self.assertEqual(raw.status.reason.value, reason_value)
                self.assertEqual(raw.raw_singular_values, singular_values)
                self.assertEqual(raw.activation_labels, activation_labels)
                self.assertIs(raw.downstream_capability_issued, False)
                self.assertEqual(
                    raw.outcome_sha,
                    canonical_sha(response_block_attempt_outcome_payload(raw)),
                )
                hydrated = verify_response_block_attempt_outcome(
                    raw,
                    permit,
                    scenario.scenario_id,
                )
                self.assertIs(
                    type(hydrated),
                    VerifiedResponseBlockAttemptOutcome,
                )
                if first_attempt is None:
                    first_attempt = attempt
                    first_permit = permit
                    first_scenario_id = scenario.scenario_id

        self.assertIsNotNone(first_attempt)
        self.assertIsNotNone(first_permit)
        self.assertIsNotNone(first_scenario_id)
        fake = object.__new__(VerifiedResponseBlockAttemptOutcome)
        with self.assertRaises((TypeError, ValueError, AttributeError)):
            reverify_verified_response_block_attempt_outcome(fake)
        _, _, wrong_permit = self._application_permit(12)
        with self.assertRaises((TypeError, ValueError)):
            verify_response_block_attempt_outcome(
                reverify_verified_response_block_attempt_outcome(first_attempt),
                wrong_permit,
                first_scenario_id,
            )


if __name__ == "__main__":
    unittest.main()
