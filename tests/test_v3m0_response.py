from __future__ import annotations

import copy
import dataclasses
import dis
import functools
import inspect
import math
import unittest
from fractions import Fraction
from types import SimpleNamespace
from unittest import mock

import numpy as np

import rulespace_v3.factory as factory_module
import rulespace_v3.response as response_module
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor
from rulespace_v3.contracts import BlockStatus
from rulespace_v3.certificate import (
    DynamicsCertificate,
    VerifiedDynamicsCertificate,
)
from rulespace_v3.dynamics import VerifiedTransition, measure_transition
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.registry import build_closed_control_registry
from rulespace_v3.runtime import (
    RuntimeEvidenceManifest,
    issue_runtime_evidence_manifest,
)
from rulespace_v3.response import (
    ENDPOINT_REFERENCE_ATTEMPT_SCHEMA_VERSION,
    ENDPOINT_REFERENCE_OUTCOME_SCHEMA_VERSION,
    ENDPOINT_REFERENCE_SCHEMA_VERSION,
    ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION,
    ENDPOINT_SHELL_ATTEMPT_SCHEMA_VERSION,
    ENDPOINT_SHELL_OUTCOME_SCHEMA_VERSION,
    ENDPOINT_SHELL_SCHEMA_VERSION,
    ENDPOINT_SHELL_SPEC_SCHEMA_VERSION,
    PAIRED_RESPONSE_ATTEMPT_SCHEMA_VERSION,
    PAIRED_RESPONSE_OUTCOME_SCHEMA_VERSION,
    PAIRED_RESPONSE_SCHEMA_VERSION,
    RESPONSE_RUN_SPEC_SCHEMA_VERSION,
    SOURCE_FRAME_COVERAGE_SCHEMA_VERSION,
    SOURCE_READOUT_BRIDGE_SCHEMA_VERSION,
    SOURCE_READOUT_RESPONSE_SCHEMA_VERSION,
    EndpointReferenceAttemptAudit,
    EndpointReferenceFailure,
    EndpointReferenceOutcome,
    EndpointReferenceProjector,
    EndpointReferenceSpec,
    EndpointShellAttemptAudit,
    EndpointShellFailure,
    EndpointShellManifest,
    EndpointShellOutcome,
    EndpointShellSpec,
    PairedFilteredResponse,
    PairedResponseAttemptAudit,
    PairedResponseFailure,
    PairedResponseOutcome,
    ResponseRunSpec,
    ShellCandidatePointAttempt,
    ShellPointAudit,
    SourceFrameCoverageCertificate,
    SourceReadoutBranchAttemptAudit,
    SourceReadoutBridgeAudit,
    SourceReadoutBridgeMatrixAudit,
    SourceReadoutResponse,
    VerifiedEndpointReferenceOutcome,
    VerifiedEndpointShellOutcome,
    VerifiedPairedResponseOutcome,
    _build_endpoint_reference_outcome_from_matrices,
    _build_endpoint_shell_outcome_from_matrices,
    _build_source_readout_bridge_audit_from_differences,
    _build_source_readout_response_from_values,
    _plane_wave,
    _readback_plane_wave,
    _measure_source_readout_bridge,
    build_endpoint_reference,
    build_endpoint_shell,
    build_endpoint_shell_spec,
    build_paired_filtered_response,
    build_response_run_spec,
    build_source_frame_coverage_certificate,
    _extract_projector_candidates,
    compute_fejer_filtered_response,
    endpoint_reference_attempt_audit_payload,
    endpoint_reference_outcome_payload,
    endpoint_reference_projector_payload,
    endpoint_reference_spec_payload,
    endpoint_shell_manifest_payload,
    endpoint_shell_outcome_payload,
    endpoint_shell_spec_payload,
    source_frame_coverage_payload,
    source_readout_branch_attempt_audit_payload,
    source_readout_bridge_audit_payload,
    source_readout_response_payload,
    verify_endpoint_reference_outcome,
    verify_endpoint_shell_outcome,
    verify_paired_filtered_response,
    verify_source_frame_coverage_certificate,
    verify_source_readout_bridge_audit_body,
    response_run_spec_payload,
    verify_response_run_spec,
)
from rulespace_v3.thresholds import (
    BRIDGE_TOLERANCE,
    phase_grid_step,
    phase_separation_min,
)
from rulespace_v3.window import (
    build_control_window_protocol_entries,
    build_window_calibration_protocol,
)
from tests.test_v3m0_window_thresholds import _window_controls


class ResponseAuthorityStructuralCodecTests(unittest.TestCase):
    @staticmethod
    def _certificate_with_real_runtime() -> DynamicsCertificate:
        runtime = issue_runtime_evidence_manifest()
        certificate = object.__new__(DynamicsCertificate)
        for field in dataclasses.fields(DynamicsCertificate):
            object.__setattr__(
                certificate,
                field.name,
                runtime if field.name == "runtime" else field.name,
            )
        return certificate

    def test_digest_and_clone_traverse_real_slotted_certificate_runtime(
        self,
    ) -> None:
        certificate = self._certificate_with_real_runtime()
        self.assertIs(type(certificate.runtime), RuntimeEvidenceManifest)

        digest = response_module._authority_structural_digest(certificate)
        cloned = response_module._authority_structural_clone(certificate)

        self.assertRegex(digest, r"\A[0-9a-f]{64}\Z")
        self.assertIs(type(cloned), DynamicsCertificate)
        self.assertIs(type(cloned.runtime), RuntimeEvidenceManifest)
        self.assertEqual(cloned.runtime, certificate.runtime)
        self.assertIsNot(cloned.runtime, certificate.runtime)

        injected = self._certificate_with_real_runtime()
        object.__setattr__(injected, "caller_unknown", "forbidden")
        with self.assertRaisesRegex(ValueError, "unknown"):
            response_module._authority_structural_digest(injected)
        with self.assertRaisesRegex(ValueError, "unknown"):
            response_module._authority_structural_clone(injected)

        incomplete = self._certificate_with_real_runtime()
        object.__setattr__(
            incomplete,
            "runtime",
            object.__new__(RuntimeEvidenceManifest),
        )
        with self.assertRaisesRegex(ValueError, "missing"):
            response_module._authority_structural_digest(incomplete)
        with self.assertRaisesRegex(ValueError, "missing"):
            response_module._authority_structural_clone(incomplete)

    def test_structural_digest_retains_cycle_and_resource_caps(self) -> None:
        @dataclasses.dataclass(frozen=True)
        class RecursiveRecord:
            child: object

        cyclic = RecursiveRecord(None)
        object.__setattr__(cyclic, "child", cyclic)
        with self.assertRaisesRegex(ValueError, "cyclic"):
            response_module._authority_structural_digest(cyclic)
        with self.assertRaisesRegex(ValueError, "cyclic"):
            response_module._authority_structural_clone(cyclic)

        oversized_text = RecursiveRecord("x" * 16_385)
        with self.assertRaisesRegex(ValueError, "text exceeds resource cap"):
            response_module._authority_structural_digest(oversized_text)

    def test_authority_helper_partials_are_frozen_off_module_globals(
        self,
    ) -> None:
        pending: list[object] = [
            response_module._authority_structural_digest,
            response_module._authority_structural_clone,
        ]
        seen: set[int] = set()
        helpers = []
        while pending:
            value = pending.pop()
            if id(value) in seen:
                continue
            seen.add(id(value))
            if type(value) is functools.partial:
                pending.append(value.func)
                pending.extend(value.args)
                pending.extend((value.keywords or {}).values())
            elif inspect.isfunction(value):
                if value.__name__ in {
                    "_exact_dataclass_items",
                    "_preflight_response_evidence_body",
                }:
                    helpers.append(value)
                pending.extend(value.__defaults__ or ())
                pending.extend((value.__kwdefaults__ or {}).values())
                pending.extend(
                    cell.cell_contents for cell in (value.__closure__ or ())
                )
            elif type(value) in (tuple, list, frozenset):
                pending.extend(value)
            elif type(value) is dict:
                pending.extend(value.values())

        self.assertEqual(
            {helper.__name__ for helper in helpers},
            {
                "_exact_dataclass_items",
                "_preflight_response_evidence_body",
            },
        )
        self.assertTrue(
            all(
                helper.__globals__ is not vars(response_module)
                for helper in helpers
            )
        )

    def test_module_helper_redirect_cannot_bypass_unknown_or_text_cap(
        self,
    ) -> None:
        @dataclasses.dataclass(frozen=True)
        class PlainRecord:
            value: str

        injected = PlainRecord("safe")
        object.__setattr__(injected, "caller_unknown", "forbidden")
        oversized = PlainRecord("x" * 16_385)
        builtin_vars = vars

        def redirected_vars(value):
            if isinstance(value, type):
                return builtin_vars(value)
            fields = getattr(type(value), "__dataclass_fields__", {})
            return {
                name: object.__getattribute__(value, name)
                for name in fields
            }

        with (
            mock.patch.object(
                response_module,
                "vars",
                side_effect=redirected_vars,
                create=True,
            ),
            mock.patch.object(
                response_module,
                "_exact_dataclass_items",
                return_value=(),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "unknown"):
                response_module._authority_structural_digest(injected)
            with self.assertRaisesRegex(
                ValueError,
                "text exceeds resource cap",
            ):
                response_module._authority_structural_digest(oversized)


class ResponseRunSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
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

    def _spec(self, order: int = 256) -> ResponseRunSpec:
        protocol = self.protocol.protocol
        protocol_entry = protocol.control_entries[0]
        registry_entry = self.registry.registry.entries[0]
        source_count = len(registry_entry.source_basis.vectors_wire)
        provisional = ResponseRunSpec(
            run_spec_schema_version=RESPONSE_RUN_SPEC_SCHEMA_VERSION,
            run_spec_id=f"v3m0.response-run.full.T{order}.v1",
            window_protocol_sha=protocol.protocol_sha,
            control_registry_entry_sha=registry_entry.entry_sha,
            fejer_order=order,
            state_schema_id=registry_entry.source_basis.state_schema_id,
            channel_order=registry_entry.source_basis.channel_order,
            source_basis=registry_entry.source_basis,
            readout_basis=registry_entry.readout_basis,
            spatial_shape=(protocol_entry.source_readout_bridge_grid.spatial_shape),
            response_grid=protocol_entry.response_grid,
            source_readout_bridge_grid=(protocol_entry.source_readout_bridge_grid),
            source_readout_bridge_steps=(protocol_entry.source_readout_bridge_steps),
            source_trial_vectors=freeze_complex_tensor(
                np.eye(source_count, dtype=np.complex128)
            ),
            bridge_tolerance=BRIDGE_TOLERANCE,
            spec_sha="0" * 64,
        )
        return dataclasses.replace(
            provisional,
            spec_sha=canonical_sha(response_run_spec_payload(provisional)),
        )

    def test_strict_run_spec_hydrates_from_live_window_protocol(self):
        raw = self._spec()
        self.assertEqual(verify_response_run_spec(raw, self.protocol), raw)
        self.assertEqual(
            raw.spec_sha,
            canonical_sha(response_run_spec_payload(raw)),
        )
        self.assertEqual(
            tuple(response_run_spec_payload(raw)),
            tuple(ResponseRunSpec.__dataclass_fields__)[:-1],
        )

    def test_run_spec_rejects_resigned_nonidentity_trials_and_wrong_grid(self):
        raw = self._spec()
        bad_trials = dataclasses.replace(
            raw,
            source_trial_vectors=freeze_complex_tensor(
                np.zeros((1, 1), dtype=np.complex128)
            ),
            spec_sha="0" * 64,
        )
        bad_trials = dataclasses.replace(
            bad_trials,
            spec_sha=canonical_sha(response_run_spec_payload(bad_trials)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_response_run_spec(bad_trials, self.protocol)

        from rulespace_v3.grids import response_grid_payload

        changed_grid = dataclasses.replace(
            raw.response_grid,
            reciprocal_indices=((1,),),
            response_grid_sha="0" * 64,
        )
        changed_grid = dataclasses.replace(
            changed_grid,
            response_grid_sha=canonical_sha(response_grid_payload(changed_grid)),
        )
        wrong_grid = dataclasses.replace(
            raw,
            response_grid=changed_grid,
            spec_sha="0" * 64,
        )
        wrong_grid = dataclasses.replace(
            wrong_grid,
            spec_sha=canonical_sha(response_run_spec_payload(wrong_grid)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_response_run_spec(wrong_grid, self.protocol)

    def test_run_spec_rejects_unknown_fields_and_fake_protocol(self):
        raw = self._spec()
        object.__setattr__(raw, "caller_unknown", "forbidden")
        with self.assertRaises((TypeError, ValueError)):
            verify_response_run_spec(raw, self.protocol)

        from rulespace_v3.window import VerifiedWindowCalibrationProtocol

        fake = object.__new__(VerifiedWindowCalibrationProtocol)
        with self.assertRaises((TypeError, ValueError)):
            verify_response_run_spec(self._spec(), fake)


class FejerResponseTests(unittest.TestCase):
    def test_source_bridge_plane_wave_lift_and_readback_cover_full_volume(self):
        vector = np.asarray((1.25 - 0.5j, -0.75 + 0.25j), dtype=np.complex128)
        field = _plane_wave(vector, (3,), (8,))
        self.assertEqual(field.shape, (2, 8))
        self.assertTrue(
            np.allclose(
                _readback_plane_wave(field, (3,), (8,)),
                vector,
                atol=2.0e-15,
            )
        )

    def test_scalar_schur_path_computes_the_declared_matrix_polynomial(self):
        first_phase = 0.125
        second_phase = -0.75
        transition = np.diag(
            np.exp(1.0j * np.asarray((first_phase, second_phase)))
        ).astype(np.complex128)
        metric = np.eye(2, dtype=np.complex128)
        source = np.eye(2, dtype=np.complex128)
        readout = np.eye(2, dtype=np.complex128)
        order = 256

        with (
            mock.patch.object(
                np.linalg,
                "matrix_power",
                side_effect=AssertionError("matrix power is forbidden"),
            ),
            mock.patch.object(
                np.linalg,
                "eig",
                side_effect=AssertionError("eigenvector selection is forbidden"),
            ),
        ):
            observed = compute_fejer_filtered_response(
                transition,
                metric,
                first_phase,
                order,
                source,
                readout,
            )

        weights = np.asarray(
            tuple(1.0 - step / order for step in range(order)),
            dtype=np.float64,
        )
        expected_second = np.sum(
            weights * np.exp(1.0j * (second_phase - first_phase) * np.arange(order)),
            dtype=np.complex128,
        ) / np.sum(weights)
        expected = np.diag((1.0 + 0.0j, expected_second))
        self.assertTrue(np.allclose(observed, expected, atol=2.0e-13))

    def test_fejer_path_is_strict_about_dtype_shape_and_closed_order(self):
        identity = np.eye(2, dtype=np.complex128)
        for changed in (
            identity.astype(np.complex64),
            identity[:, :1],
        ):
            with self.subTest(shape=changed.shape, dtype=changed.dtype):
                with self.assertRaises((TypeError, ValueError)):
                    compute_fejer_filtered_response(
                        changed,
                        identity,
                        0.0,
                        256,
                        identity,
                        identity,
                    )
        with self.assertRaises((TypeError, ValueError)):
            compute_fejer_filtered_response(
                identity,
                identity,
                0.0,
                255,
                identity,
                identity,
            )

    def test_endpoint_candidate_extraction_uses_invariant_projectors(self):
        transition = np.diag(np.exp(1.0j * np.asarray((0.0, 1.0)))).astype(
            np.complex128
        )
        identity = np.eye(2, dtype=np.complex128)
        candidates = _extract_projector_candidates(
            transition,
            identity,
            ((-0.25, 0.25),),
            256,
            identity,
            identity,
        )
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.rank, 1)
        self.assertAlmostEqual(candidate.phase, 0.0)
        self.assertTrue(
            np.allclose(
                candidate.projector,
                np.diag((1.0, 0.0)),
                atol=1.0e-14,
            )
        )
        self.assertGreaterEqual(candidate.participation, 1.0 - 1.0e-14)
        self.assertLessEqual(candidate.hermitian_residual, 1.0e-14)
        self.assertLessEqual(candidate.idempotent_residual, 1.0e-14)
        self.assertLessEqual(candidate.g_invariance_residual, 1.0e-14)
        self.assertLessEqual(candidate.eigenphase_residual, 1.0e-14)
        self.assertIsNone(candidate.nearest_competitor_gap)
        self.assertIsNone(candidate.runner_up_overlap)

    def test_endpoint_candidate_extraction_keeps_nearby_clusters_competing(self):
        transition = np.diag(np.exp(1.0j * np.asarray((0.0, 0.01, 1.0)))).astype(
            np.complex128
        )
        identity = np.eye(3, dtype=np.complex128)
        candidates = _extract_projector_candidates(
            transition,
            identity,
            ((-0.25, 0.25),),
            256,
            identity,
            identity,
        )
        self.assertEqual(tuple(item.rank for item in candidates), (1, 1))
        self.assertTrue(
            all(item.nearest_competitor_gap is not None for item in candidates)
        )
        self.assertAlmostEqual(
            candidates[0].nearest_competitor_gap or 0.0,
            0.01,
            places=12,
        )


class ResponseContractSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
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

    def _raw_reference_outcome(self) -> EndpointReferenceOutcome:
        protocol = self.protocol.protocol
        protocol_entry = protocol.control_entries[0]
        registry_entry = self.registry.registry.entries[0]
        provisional_spec = EndpointReferenceSpec(
            reference_spec_schema_version=(ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION),
            window_protocol_sha=protocol.protocol_sha,
            control_registry_entry=registry_entry,
            actual_factory_sha=registry_entry.factory_sha,
            actual_transition_sha="a" * 64,
            actual_dynamics_certificate_sha="b" * 64,
            candidate_fejer_order=256,
            reference_reciprocal_index=(protocol_entry.reference_reciprocal_index),
            preregistered_phase_bands=(protocol_entry.preregistered_phase_bands),
            expected_shell_rank=protocol_entry.expected_shell_rank,
            expected_shell_rank_source_id=(
                protocol_entry.expected_shell_rank_source_id
            ),
            reference_spec_sha="0" * 64,
        )
        spec = dataclasses.replace(
            provisional_spec,
            reference_spec_sha=canonical_sha(
                endpoint_reference_spec_payload(provisional_spec)
            ),
        )
        provisional_reference = EndpointReferenceProjector(
            reference_schema_version=ENDPOINT_REFERENCE_SCHEMA_VERSION,
            control_registry_entry_sha=registry_entry.entry_sha,
            actual_transition_sha="a" * 64,
            actual_dynamics_certificate_sha="b" * 64,
            reference_reciprocal_index=(protocol_entry.reference_reciprocal_index),
            reference_phase=math.pi / 2.0,
            projector_coordinate_convention_id="g-whitened-state-v1",
            rank=1,
            projector=freeze_complex_tensor(np.diag((0.0, 1.0)).astype(np.complex128)),
            reference_sha="0" * 64,
        )
        reference = dataclasses.replace(
            provisional_reference,
            reference_sha=canonical_sha(
                endpoint_reference_projector_payload(provisional_reference)
            ),
        )
        provisional_attempt = EndpointReferenceAttemptAudit(
            attempt_schema_version=(ENDPOINT_REFERENCE_ATTEMPT_SCHEMA_VERSION),
            reference_spec=spec,
            candidate_phases=(math.pi / 2.0,),
            candidate_ranks=(1,),
            expected_shell_rank=1,
            expected_shell_rank_source_id=("parent-freeze-control-application-spec-v1"),
            candidate_participations=(1.0,),
            runner_up_overlaps=(None,),
            hermitian_residuals=(0.0,),
            idempotent_residuals=(0.0,),
            g_invariance_residuals=(0.0,),
            eigenphase_residuals=(0.0,),
            observed_competitor_gaps=(None,),
            attempt_sha="0" * 64,
        )
        attempt = dataclasses.replace(
            provisional_attempt,
            attempt_sha=canonical_sha(
                endpoint_reference_attempt_audit_payload(provisional_attempt)
            ),
        )
        provisional_outcome = EndpointReferenceOutcome(
            status=BlockStatus(True, None),
            failure=None,
            reference_spec=spec,
            attempt_audit=attempt,
            reference=reference,
            outcome_sha="0" * 64,
        )
        return dataclasses.replace(
            provisional_outcome,
            outcome_sha=canonical_sha(
                endpoint_reference_outcome_payload(provisional_outcome)
            ),
        )

    def _run_spec(self) -> ResponseRunSpec:
        protocol = self.protocol.protocol
        protocol_entry = protocol.control_entries[0]
        registry_entry = self.registry.registry.entries[0]
        source_count = len(registry_entry.source_basis.vectors_wire)
        provisional = ResponseRunSpec(
            run_spec_schema_version=RESPONSE_RUN_SPEC_SCHEMA_VERSION,
            run_spec_id="v3m0.response-run.full.T256.v1",
            window_protocol_sha=protocol.protocol_sha,
            control_registry_entry_sha=registry_entry.entry_sha,
            fejer_order=256,
            state_schema_id=registry_entry.source_basis.state_schema_id,
            channel_order=registry_entry.source_basis.channel_order,
            source_basis=registry_entry.source_basis,
            readout_basis=registry_entry.readout_basis,
            spatial_shape=(protocol_entry.source_readout_bridge_grid.spatial_shape),
            response_grid=protocol_entry.response_grid,
            source_readout_bridge_grid=(protocol_entry.source_readout_bridge_grid),
            source_readout_bridge_steps=(protocol_entry.source_readout_bridge_steps),
            source_trial_vectors=freeze_complex_tensor(
                np.eye(source_count, dtype=np.complex128)
            ),
            bridge_tolerance=BRIDGE_TOLERANCE,
            spec_sha="0" * 64,
        )
        return dataclasses.replace(
            provisional,
            spec_sha=canonical_sha(response_run_spec_payload(provisional)),
        )

    def test_reference_payloads_are_recursive_exact_wire_and_self_hashed(self):
        outcome = self._raw_reference_outcome()
        self.assertEqual(
            outcome.outcome_sha,
            canonical_sha(endpoint_reference_outcome_payload(outcome)),
        )
        self.assertEqual(
            tuple(endpoint_reference_spec_payload(outcome.reference_spec)),
            tuple(EndpointReferenceSpec.__dataclass_fields__)[:-1],
        )
        self.assertEqual(
            tuple(endpoint_reference_attempt_audit_payload(outcome.attempt_audit)),
            tuple(EndpointReferenceAttemptAudit.__dataclass_fields__)[:-1],
        )
        self.assertEqual(
            tuple(endpoint_reference_outcome_payload(outcome)),
            tuple(EndpointReferenceOutcome.__dataclass_fields__)[:-1],
        )
        self.assertIn(
            "control_registry_entry",
            endpoint_reference_spec_payload(outcome.reference_spec),
        )
        self.assertIn(
            "reference_spec",
            endpoint_reference_attempt_audit_payload(outcome.attempt_audit),
        )

    def test_reference_outcome_is_mechanically_built_from_full_projector_body(self):
        template = self._raw_reference_outcome()
        transition = np.diag(np.exp(1.0j * np.asarray((0.0, math.pi / 2.0)))).astype(
            np.complex128
        )
        identity = np.eye(2, dtype=np.complex128)
        outcome = _build_endpoint_reference_outcome_from_matrices(
            template.reference_spec,
            transition,
            identity,
            identity,
            identity,
        )
        self.assertTrue(outcome.status.defined)
        self.assertIsNone(outcome.failure)
        self.assertIsNotNone(outcome.reference)
        assert outcome.reference is not None
        self.assertEqual(outcome.reference.rank, 1)
        self.assertEqual(
            outcome.reference.projector_coordinate_convention_id,
            "g-whitened-state-v1",
        )
        self.assertEqual(
            outcome.reference.reference_sha,
            canonical_sha(endpoint_reference_projector_payload(outcome.reference)),
        )
        self.assertEqual(
            outcome.outcome_sha,
            canonical_sha(endpoint_reference_outcome_payload(outcome)),
        )

    def test_reference_public_builder_rejects_nonlive_transition_and_certificate(self):
        fake_transition = object.__new__(VerifiedTransition)
        fake_certificate = object.__new__(VerifiedDynamicsCertificate)
        with self.assertRaises((TypeError, ValueError)):
            build_endpoint_reference(
                self.registry,
                self.protocol,
                self.controls[0].factory,
                fake_transition,
                fake_certificate,
                "full",
                256,
            )

    def test_shell_outcome_continues_the_reference_projector_per_path(self):
        reference_outcome = self._raw_reference_outcome()
        assert reference_outcome.reference is not None
        protocol_entry = self.protocol.protocol.control_entries[0]
        provisional_spec = EndpointShellSpec(
            shell_spec_schema_version=ENDPOINT_SHELL_SPEC_SCHEMA_VERSION,
            window_protocol_sha=self.protocol.protocol.protocol_sha,
            control_registry_entry=(
                reference_outcome.reference_spec.control_registry_entry
            ),
            response_grid=protocol_entry.response_grid,
            preregistered_phase_bands=(protocol_entry.preregistered_phase_bands),
            candidate_fejer_order=256,
            endpoint_reference_projector=reference_outcome.reference,
            extraction_protocol_id="endpoint-single-node-reference-v1",
            shell_spec_sha="0" * 64,
        )
        shell_spec = dataclasses.replace(
            provisional_spec,
            shell_spec_sha=canonical_sha(endpoint_shell_spec_payload(provisional_spec)),
        )
        identity = np.eye(2, dtype=np.complex128)
        transition = np.diag(np.exp(1.0j * np.asarray((0.0, math.pi / 2.0)))).astype(
            np.complex128
        )
        points = tuple(
            (path_id, position, reciprocal_index)
            for path_id, path in zip(
                shell_spec.response_grid.direction_manifest.path_ids,
                shell_spec.response_grid.direction_manifest.ordered_paths,
            )
            for position, reciprocal_index in enumerate(path)
        )
        matrices = tuple(transition.copy() for _ in points)
        metrics = tuple(identity.copy() for _ in points)
        outcome = _build_endpoint_shell_outcome_from_matrices(
            reference_outcome,
            shell_spec,
            matrices,
            metrics,
            identity,
            identity,
            actual_factory_sha=shell_spec.control_registry_entry.factory_sha,
            actual_transition_sha="a" * 64,
            actual_dynamics_certificate_sha="b" * 64,
            dt=0.25,
        )
        self.assertTrue(outcome.status.defined)
        self.assertIsNone(outcome.failure)
        self.assertIsNotNone(outcome.shell)
        assert outcome.shell is not None
        self.assertEqual(len(outcome.shell.point_audits), len(points))
        self.assertTrue(
            all(
                item.reference_overlap >= 1.0 - 1.0e-14
                for item in outcome.shell.point_audits
            )
        )
        self.assertEqual(
            outcome.shell.shell_manifest_sha,
            canonical_sha(endpoint_shell_manifest_payload(outcome.shell)),
        )
        self.assertEqual(
            outcome.outcome_sha,
            canonical_sha(endpoint_shell_outcome_payload(outcome)),
        )

    def test_shell_spec_builder_requires_successful_live_reference_authority(self):
        fake = object.__new__(VerifiedEndpointReferenceOutcome)
        with self.assertRaises((TypeError, ValueError)):
            build_endpoint_shell_spec(self.protocol, fake)

    def test_nonidentity_source_frame_requires_replayable_full_rank_certificate(self):
        basis = self.registry.registry.entries[0].source_basis
        trials = freeze_complex_tensor(
            np.asarray(((2.0 + 0.0j,),), dtype=np.complex128)
        )
        certificate = build_source_frame_coverage_certificate(
            basis,
            trials,
        )
        self.assertEqual(certificate.frame_operator_lower, 4.0)
        self.assertEqual(certificate.canonical_dual_residual_upper, 0.0)
        self.assertEqual(
            verify_source_frame_coverage_certificate(
                certificate,
                basis,
                trials,
            ),
            certificate,
        )
        changed = dataclasses.replace(
            certificate,
            frame_operator_lower=3.0,
            certificate_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            certificate_sha=canonical_sha(source_frame_coverage_payload(changed)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_source_frame_coverage_certificate(
                changed,
                basis,
                trials,
            )

    def test_paired_builder_is_explicitly_fail_closed_without_qualification_authority(
        self,
    ):
        with self.assertRaisesRegex(
            (TypeError, ValueError, RuntimeError),
            "certificate-backed qualification",
        ):
            build_paired_filtered_response(
                self.registry,
                self.protocol,
                object(),
                object(),
                object(),
                object(),
                object(),
                object(),
                object(),
            )

    def test_run_spec_builder_rejects_nonlive_transition_and_certificate(self):
        with self.assertRaises((TypeError, ValueError)):
            build_response_run_spec(
                self.protocol,
                object.__new__(VerifiedTransition),
                object.__new__(VerifiedDynamicsCertificate),
                "full",
                256,
            )

    def test_run_spec_builder_reads_controls_from_verified_registry_view(self):
        factory = self.controls[0].factory
        factory_body = factory.factory
        raw_transition = SimpleNamespace(
            factory_sha=factory_body.factory_sha,
            state_schema_id=factory_body.state_schema_id,
            channel_order=factory_body.channel_order,
            spatial_shape=factory_body.state_shape[1:],
        )
        with (
            mock.patch.object(
                response_module,
                "_reverify_verified_transition",
                return_value=SimpleNamespace(
                    factory=factory,
                    transition=raw_transition,
                ),
            ),
            mock.patch.object(
                response_module,
                "_reverify_verified_dynamics_certificate",
                return_value=SimpleNamespace(
                    factory=factory,
                    certificate=SimpleNamespace(
                        transition=raw_transition,
                    ),
                ),
            ),
            mock.patch.object(
                response_module,
                "verify_response_run_spec",
                side_effect=lambda spec, _protocol: spec,
            ),
        ):
            spec = build_response_run_spec(
                self.protocol,
                object(),
                object(),
                "full",
                256,
            )

        self.assertEqual(
            spec.control_registry_entry_sha,
            self.registry.registry.entries[0].entry_sha,
        )
        self.assertEqual(spec.spatial_shape, factory_body.state_shape[1:])

    def test_bridge_audit_preserves_every_dimensional_difference_matrix(self):
        run_spec = verify_response_run_spec(
            self._run_spec(),
            self.protocol,
        )
        entry = self.registry.registry.entries[0]
        differences = tuple(
            (
                reciprocal_index,
                steps,
                np.zeros((1, 1), dtype=np.complex128),
            )
            for reciprocal_index in (
                run_spec.source_readout_bridge_grid.reciprocal_indices
            )
            for steps in run_spec.source_readout_bridge_steps
        )
        audit = _build_source_readout_bridge_audit_from_differences(
            branch="actual",
            factory_sha=entry.factory_sha,
            transition_sha="a" * 64,
            dynamics_certificate_sha="b" * 64,
            run_spec=run_spec,
            registry_entry=entry,
            differences=differences,
        )
        self.assertEqual(len(audit.matrix_audits), len(differences))
        self.assertEqual(audit.h_operator_error_max, 0.0)
        self.assertEqual(audit.curv_operator_error_max, 0.0)
        self.assertTrue(
            all(item.frame_coverage is None for item in audit.matrix_audits)
        )
        self.assertTrue(
            all(
                item.raw_difference_matrix.shape == (1, 1)
                for item in audit.matrix_audits
            )
        )
        self.assertEqual(
            audit.bridge_sha,
            canonical_sha(source_readout_bridge_audit_payload(audit)),
        )
        values = freeze_complex_tensor(
            np.zeros(
                (
                    len(run_spec.response_grid.reciprocal_indices),
                    1,
                    1,
                ),
                dtype=np.complex128,
            )
        )
        response = _build_source_readout_response_from_values(
            branch="actual",
            factory_sha=entry.factory_sha,
            transition_sha="a" * 64,
            dynamics_certificate_sha="b" * 64,
            run_spec=run_spec,
            shell_manifest_sha="c" * 64,
            bridge_audit=audit,
            values=values,
        )
        self.assertEqual(
            response.response_sha,
            canonical_sha(source_readout_response_payload(response)),
        )

    def test_repeated_executor_bridge_reconstructs_the_complete_source_domain(self):
        construction = matched_ablation(self.controls[0].factory)
        assert construction.pair is not None
        factory = construction.pair.actual
        authority = issue_synthetic_prestructure_authority(
            self.parent,
            self.registry,
            "full",
            construction,
            "actual",
        )
        transition = measure_transition(
            factory,
            authority,
        )
        run_spec = verify_response_run_spec(
            self._run_spec(),
            self.protocol,
        )
        audit = _measure_source_readout_bridge(
            branch="actual",
            factory=factory,
            transition=transition,
            dynamics_certificate_sha="b" * 64,
            run_spec=run_spec,
            registry_entry=self.registry.registry.entries[0],
        )
        self.assertEqual(
            len(audit.matrix_audits),
            len(run_spec.source_readout_bridge_grid.reciprocal_indices)
            * len(run_spec.source_readout_bridge_steps),
        )
        self.assertLessEqual(audit.h_operator_error_max, 1.0e-12)
        self.assertLessEqual(audit.curv_operator_error_max, 1.0e-12)

    def test_task11_response_records_have_the_frozen_exact_fields(self):
        expected = {
            ResponseRunSpec: (
                "run_spec_schema_version",
                "run_spec_id",
                "window_protocol_sha",
                "control_registry_entry_sha",
                "fejer_order",
                "state_schema_id",
                "channel_order",
                "source_basis",
                "readout_basis",
                "spatial_shape",
                "response_grid",
                "source_readout_bridge_grid",
                "source_readout_bridge_steps",
                "source_trial_vectors",
                "bridge_tolerance",
                "spec_sha",
            ),
            EndpointReferenceSpec: (
                "reference_spec_schema_version",
                "window_protocol_sha",
                "control_registry_entry",
                "actual_factory_sha",
                "actual_transition_sha",
                "actual_dynamics_certificate_sha",
                "candidate_fejer_order",
                "reference_reciprocal_index",
                "preregistered_phase_bands",
                "expected_shell_rank",
                "expected_shell_rank_source_id",
                "reference_spec_sha",
            ),
            EndpointReferenceProjector: (
                "reference_schema_version",
                "control_registry_entry_sha",
                "actual_transition_sha",
                "actual_dynamics_certificate_sha",
                "reference_reciprocal_index",
                "reference_phase",
                "projector_coordinate_convention_id",
                "rank",
                "projector",
                "reference_sha",
            ),
            EndpointReferenceAttemptAudit: (
                "attempt_schema_version",
                "reference_spec",
                "candidate_phases",
                "candidate_ranks",
                "expected_shell_rank",
                "expected_shell_rank_source_id",
                "candidate_participations",
                "runner_up_overlaps",
                "hermitian_residuals",
                "idempotent_residuals",
                "g_invariance_residuals",
                "eigenphase_residuals",
                "observed_competitor_gaps",
                "attempt_sha",
            ),
            EndpointReferenceOutcome: (
                "status",
                "failure",
                "reference_spec",
                "attempt_audit",
                "reference",
                "outcome_sha",
            ),
            EndpointShellSpec: (
                "shell_spec_schema_version",
                "window_protocol_sha",
                "control_registry_entry",
                "response_grid",
                "preregistered_phase_bands",
                "candidate_fejer_order",
                "endpoint_reference_projector",
                "extraction_protocol_id",
                "shell_spec_sha",
            ),
            ShellPointAudit: (
                "reciprocal_index",
                "momentum_path_id",
                "momentum_path_position",
                "shell_phase",
                "rank",
                "hermitian_residual",
                "idempotent_residual",
                "g_invariance_residual",
                "eigenphase_residual",
                "participation",
                "nearest_competitor_gap",
                "reference_overlap",
                "runner_up_overlap",
                "predecessor_overlap",
                "loop_residual",
            ),
            EndpointShellManifest: (
                "shell_schema_version",
                "actual_factory_sha",
                "actual_transition_sha",
                "actual_dynamics_certificate_sha",
                "shell_spec",
                "dt",
                "eigenphase_convention_id",
                "shell_phases",
                "shell_projectors",
                "point_audits",
                "hermitian_residual_max",
                "idempotent_residual_max",
                "g_invariance_residual_max",
                "eigenphase_residual_max",
                "participation_min",
                "nearest_competitor_gap_min",
                "reference_overlap_min",
                "runner_up_overlap_max",
                "predecessor_overlap_min",
                "overlap_margin_min",
                "loop_residual_max",
                "ambiguous",
                "shell_manifest_sha",
            ),
            ShellCandidatePointAttempt: (
                "reciprocal_index",
                "momentum_path_id",
                "momentum_path_position",
                "candidate_phases",
                "candidate_ranks",
                "candidate_participations",
                "candidate_reference_overlaps",
                "candidate_predecessor_overlaps",
            ),
            EndpointShellAttemptAudit: (
                "attempt_schema_version",
                "shell_spec",
                "point_attempts",
                "projector_residual_max",
                "loop_residual_max_observed",
                "attempt_sha",
            ),
            EndpointShellOutcome: (
                "status",
                "failure",
                "reference_outcome",
                "attempt_audit",
                "shell",
                "outcome_sha",
            ),
            SourceFrameCoverageCertificate: (
                "certificate_schema_version",
                "source_basis_sha",
                "trial_matrix",
                "frame_operator_lower",
                "canonical_dual_residual_upper",
                "certificate_sha",
            ),
            SourceReadoutBridgeMatrixAudit: (
                "reciprocal_index",
                "macro_steps",
                "raw_difference_matrix",
                "frame_coverage",
                "raw_frobenius_upper",
                "raw_operator_norm_upper",
                "h_whitened_operator_error_upper",
                "curv_whitened_operator_error_upper",
            ),
            SourceReadoutBridgeAudit: (
                "bridge_schema_version",
                "branch",
                "factory_sha",
                "transition_sha",
                "dynamics_certificate_sha",
                "run_spec_sha",
                "source_metric_whitener_sha",
                "readout_calibration_spec_sha",
                "matrix_audits",
                "h_operator_error_max",
                "curv_operator_error_max",
                "bridge_sha",
            ),
            SourceReadoutResponse: (
                "response_schema_version",
                "branch",
                "factory_sha",
                "transition_sha",
                "dynamics_certificate_sha",
                "source_basis",
                "readout_basis",
                "run_spec_sha",
                "shell_manifest_sha",
                "bridge_audit",
                "values",
                "response_sha",
            ),
            PairedFilteredResponse: (
                "pair_schema_version",
                "ablation_manifest_sha",
                "qualification_sha",
                "actual_dynamics_certificate",
                "ablated_dynamics_certificate",
                "actual",
                "ablated",
                "run_spec",
                "shell_manifest",
                "pair_sha",
            ),
            SourceReadoutBranchAttemptAudit: (
                "branch",
                "response_values",
                "bridge_audit",
                "failure",
                "attempt_sha",
            ),
            PairedResponseAttemptAudit: (
                "attempt_schema_version",
                "window_protocol",
                "qualification_sha",
                "actual_factory_sha",
                "ablated_factory_sha",
                "actual_transition",
                "ablated_transition",
                "actual_dynamics_certificate",
                "ablated_dynamics_certificate",
                "run_spec",
                "shell_outcome",
                "actual_branch_attempt",
                "ablated_branch_attempt",
                "first_failure",
                "attempt_sha",
            ),
            PairedResponseOutcome: (
                "status",
                "failure",
                "attempt_audit",
                "paired_response",
                "outcome_sha",
            ),
        }
        for record_type, field_names in expected.items():
            with self.subTest(record=record_type.__name__):
                self.assertEqual(
                    tuple(record_type.__dataclass_fields__),
                    field_names,
                )

    def test_schema_versions_and_failure_enums_are_closed(self):
        versions = (
            RESPONSE_RUN_SPEC_SCHEMA_VERSION,
            ENDPOINT_REFERENCE_SPEC_SCHEMA_VERSION,
            ENDPOINT_REFERENCE_SCHEMA_VERSION,
            ENDPOINT_REFERENCE_ATTEMPT_SCHEMA_VERSION,
            ENDPOINT_REFERENCE_OUTCOME_SCHEMA_VERSION,
            ENDPOINT_SHELL_SPEC_SCHEMA_VERSION,
            ENDPOINT_SHELL_SCHEMA_VERSION,
            ENDPOINT_SHELL_ATTEMPT_SCHEMA_VERSION,
            ENDPOINT_SHELL_OUTCOME_SCHEMA_VERSION,
            SOURCE_FRAME_COVERAGE_SCHEMA_VERSION,
            SOURCE_READOUT_BRIDGE_SCHEMA_VERSION,
            SOURCE_READOUT_RESPONSE_SCHEMA_VERSION,
            PAIRED_RESPONSE_SCHEMA_VERSION,
            PAIRED_RESPONSE_ATTEMPT_SCHEMA_VERSION,
            PAIRED_RESPONSE_OUTCOME_SCHEMA_VERSION,
        )
        self.assertTrue(all(item.startswith("v3m0.") for item in versions))
        self.assertEqual(
            tuple(item.value for item in EndpointReferenceFailure),
            (
                "phase_band_empty",
                "phase_band_nonunique",
                "rank_mismatch",
                "participation_failed",
                "runner_up_margin_failed",
                "projector_invalid",
            ),
        )
        self.assertEqual(
            tuple(item.value for item in EndpointShellFailure),
            (
                "phase_band_empty",
                "phase_separation_failed",
                "gap_failed",
                "participation_failed",
                "reference_ambiguous",
                "runner_up_margin",
                "loop_inconsistent",
                "projector_invalid",
            ),
        )
        self.assertEqual(
            tuple(item.value for item in PairedResponseFailure),
            (
                "qualification_invalid",
                "input_binding_invalid",
                "actual_response_failed",
                "ablated_response_failed",
                "actual_bridge_failed",
                "ablated_bridge_failed",
            ),
        )

    def test_opaque_outcome_types_are_not_publicly_constructible(self):
        for wrapper in (
            VerifiedEndpointReferenceOutcome,
            VerifiedEndpointShellOutcome,
            VerifiedPairedResponseOutcome,
        ):
            with self.subTest(wrapper=wrapper.__name__):
                with self.assertRaises(TypeError):
                    wrapper()  # type: ignore[call-arg]


class ResponseHardeningReviewTests(unittest.TestCase):
    """Adversarial regressions from the independent Task 11-B review."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
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

    def _raw_reference_outcome(self) -> EndpointReferenceOutcome:
        return ResponseContractSurfaceTests._raw_reference_outcome(self)

    def _run_spec(self) -> ResponseRunSpec:
        return ResponseContractSurfaceTests._run_spec(self)

    def _zero_bridge_audit(
        self,
    ) -> tuple[ResponseRunSpec, object, SourceReadoutBridgeAudit]:
        run_spec = verify_response_run_spec(
            self._run_spec(),
            self.protocol,
        )
        entry = self.registry.registry.entries[0]
        differences = tuple(
            (
                reciprocal_index,
                steps,
                np.zeros((1, 1), dtype=np.complex128),
            )
            for reciprocal_index in (
                run_spec.source_readout_bridge_grid.reciprocal_indices
            )
            for steps in run_spec.source_readout_bridge_steps
        )
        audit = _build_source_readout_bridge_audit_from_differences(
            branch="actual",
            factory_sha=entry.factory_sha,
            transition_sha="a" * 64,
            dynamics_certificate_sha="b" * 64,
            run_spec=run_spec,
            registry_entry=entry,
            differences=differences,
        )
        return run_spec, entry, audit

    def _shell_inputs(
        self,
    ) -> tuple[
        EndpointReferenceOutcome,
        EndpointShellSpec,
        tuple[np.ndarray, ...],
        tuple[np.ndarray, ...],
    ]:
        template = self._raw_reference_outcome()
        identity = np.eye(2, dtype=np.complex128)
        transition = np.diag(np.exp(1.0j * np.asarray((0.0, math.pi / 2.0)))).astype(
            np.complex128
        )
        reference = _build_endpoint_reference_outcome_from_matrices(
            template.reference_spec,
            transition,
            identity,
            identity,
            identity,
        )
        assert reference.reference is not None
        protocol_entry = self.protocol.protocol.control_entries[0]
        provisional = EndpointShellSpec(
            shell_spec_schema_version=ENDPOINT_SHELL_SPEC_SCHEMA_VERSION,
            window_protocol_sha=self.protocol.protocol.protocol_sha,
            control_registry_entry=reference.reference_spec.control_registry_entry,
            response_grid=protocol_entry.response_grid,
            preregistered_phase_bands=protocol_entry.preregistered_phase_bands,
            candidate_fejer_order=256,
            endpoint_reference_projector=reference.reference,
            extraction_protocol_id="endpoint-single-node-reference-v1",
            shell_spec_sha="0" * 64,
        )
        spec = dataclasses.replace(
            provisional,
            shell_spec_sha=canonical_sha(endpoint_shell_spec_payload(provisional)),
        )
        point_count = sum(
            len(path) for path in spec.response_grid.direction_manifest.ordered_paths
        )
        return (
            reference,
            spec,
            tuple(transition.copy() for _ in range(point_count)),
            tuple(identity.copy() for _ in range(point_count)),
        )

    @staticmethod
    def _candidate(
        phase: float,
        projector: np.ndarray,
        *,
        participation: float,
        gap: float | None,
        runner_up: float | None,
    ):
        return response_module._ProjectorCandidate(
            phase=phase,
            rank=1,
            projector=projector,
            participation=participation,
            runner_up_overlap=runner_up,
            hermitian_residual=0.0,
            idempotent_residual=0.0,
            g_invariance_residual=0.0,
            eigenphase_residual=0.0,
            nearest_competitor_gap=gap,
        )

    def test_authority_clone_ignores_stdlib_deepcopy_dispatch(self):
        template = self._raw_reference_outcome()

        def hostile_dispatch(*args, **kwargs):
            del args, kwargs
            raise AssertionError("shared deepcopy dispatch was consulted")

        with mock.patch.dict(
            copy._deepcopy_dispatch,
            {type(template): hostile_dispatch},
        ):
            observed = response_module._authority_structural_clone(template)
        self.assertEqual(observed, template)
        self.assertIsNot(observed, template)
        self.assertIsNot(observed.reference_spec, template.reference_spec)

    def test_reference_global_patch_and_five_objects_cannot_issue_live_outcome(
        self,
    ):
        raw = self._raw_reference_outcome()
        with mock.patch.object(
            response_module,
            "_expected_reference_outcome",
            return_value=raw,
        ):
            with self.assertRaises((TypeError, ValueError)):
                response_module.build_endpoint_reference(
                    object(),
                    object(),
                    object(),
                    object(),
                    object(),
                    "full",
                    256,
                )

    def test_public_authority_call_graph_has_no_module_global_loads(self):
        pending = [
            build_endpoint_reference,
            verify_endpoint_reference_outcome,
            build_endpoint_shell_spec,
            build_endpoint_shell,
            verify_endpoint_shell_outcome,
            build_paired_filtered_response,
            verify_paired_filtered_response,
            VerifiedEndpointReferenceOutcome.outcome.fget,
            VerifiedEndpointReferenceOutcome.reference.fget,
            VerifiedEndpointShellOutcome.outcome.fget,
            VerifiedEndpointShellOutcome.shell.fget,
            VerifiedPairedResponseOutcome.outcome.fget,
            VerifiedPairedResponseOutcome.paired_response.fget,
        ]
        seen: set[int] = set()
        offenders: list[tuple[str, str, object]] = []
        while pending:
            function = pending.pop()
            if function is None or id(function) in seen:
                continue
            seen.add(id(function))
            for instruction in dis.get_instructions(function):
                if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}:
                    offenders.append(
                        (
                            function.__qualname__,
                            instruction.opname,
                            instruction.argval,
                        )
                    )
            reachable: list[object] = []
            reachable.extend(function.__defaults__ or ())
            reachable.extend((function.__kwdefaults__ or {}).values())
            reachable.extend(
                cell.cell_contents for cell in (function.__closure__ or ())
            )
            while reachable:
                value = reachable.pop()
                if (
                    inspect.isfunction(value)
                    and value.__module__ == response_module.__name__
                ):
                    pending.append(value)
                elif type(value) in (tuple, list, frozenset):
                    reachable.extend(value)
                elif type(value) is dict:
                    reachable.extend(value.values())
        self.assertEqual(offenders, [])

    def test_frozen_paired_replay_captures_nested_stage_globals(self):
        frozen = response_module._freeze_response_call_graph(
            response_module._expected_paired_outcome
        ).func
        for name in (
            "_compute_source_readout_response_values",
            "_measure_source_readout_bridge",
        ):
            with self.subTest(name=name):
                self.assertIn(name, frozen.__globals__)
                self.assertIsNot(
                    frozen.__globals__[name],
                    getattr(response_module, name),
                )

    def test_frozen_graph_snapshots_cross_module_closures_partials_and_modules(
        self,
    ):
        frozen = response_module._freeze_response_call_graph(
            response_module._expected_reference_outcome
        ).func
        self.assertIsNot(
            frozen.__globals__["_reverify_verified_dynamics_certificate"],
            response_module._reverify_verified_dynamics_certificate,
        )
        self.assertIsInstance(frozen.__globals__["np"], SimpleNamespace)
        frozen_asarray = frozen.__globals__["np"].asarray
        with mock.patch.object(np, "asarray", autospec=True):
            self.assertIs(frozen.__globals__["np"].asarray, frozen_asarray)

        def dependency(value):
            return value

        dependency.__module__ = response_module.__name__
        bound = functools.partial(dependency, 7)

        def root():
            return bound()

        root.__module__ = response_module.__name__
        frozen_root = response_module._freeze_response_call_graph(root).func
        frozen_bound = frozen_root.__closure__[0].cell_contents
        self.assertIsInstance(frozen_bound, functools.partial)
        self.assertIsNot(frozen_bound, bound)
        self.assertIsNot(frozen_bound.func, dependency)
        self.assertEqual(frozen_root(), 7)

        closure_module = np

        def module_closure_root():
            return closure_module.asarray((1.0,))

        module_closure_root.__module__ = response_module.__name__
        frozen_module_closure = response_module._freeze_response_call_graph(
            module_closure_root
        ).func
        frozen_closure_proxy = frozen_module_closure.__closure__[0].cell_contents
        self.assertIsInstance(frozen_closure_proxy, SimpleNamespace)
        closure_asarray = frozen_closure_proxy.asarray
        with mock.patch.object(np, "asarray", autospec=True):
            self.assertIs(frozen_closure_proxy.asarray, closure_asarray)

        def module_default_root(module=np):
            return module.asarray((1.0,))

        module_default_root.__module__ = response_module.__name__
        frozen_module_default = response_module._freeze_response_call_graph(
            module_default_root
        ).func
        frozen_default_proxy = frozen_module_default.__defaults__[0]
        self.assertIsInstance(frozen_default_proxy, SimpleNamespace)
        default_asarray = frozen_default_proxy.asarray
        with mock.patch.object(np, "asarray", autospec=True):
            self.assertIs(frozen_default_proxy.asarray, default_asarray)

    def test_authority_maker_keeps_independent_snapshots_and_rejects_raw_unknowns(
        self,
    ):
        template = self._raw_reference_outcome()

        def expected(*_args):
            return copy.deepcopy(template)

        (
            build,
            _verify,
            issue,
            reverify,
            outcome_property,
            _reference_property,
        ) = response_module._make_closed_reference_authority(
            expected,
            response_module._preflight_reference_outcome_body,
            response_module._authority_structural_digest,
            response_module._authority_structural_seal,
        )
        wrapper = build(
            object(),
            object(),
            object(),
            object(),
            object(),
            "full",
            256,
        )
        first = outcome_property(wrapper)
        second = outcome_property(wrapper)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(
            first.reference_spec,
            second.reference_spec,
        )
        object.__setattr__(
            first.reference_spec,
            "caller_unknown",
            "local-copy-only",
        )
        self.assertEqual(outcome_property(wrapper), template)

        caller_raw = copy.deepcopy(template)
        hydrated = issue(
            object(),
            object(),
            object(),
            object(),
            object(),
            "full",
            256,
            caller_raw,
        )
        object.__setattr__(
            caller_raw.reference_spec,
            "caller_unknown",
            "caller-mutated-after-issuance",
        )
        self.assertEqual(outcome_property(hydrated), template)

        stored_raw = object.__getattribute__(
            wrapper,
            "_VerifiedEndpointReferenceOutcome__outcome",
        )
        object.__setattr__(
            stored_raw.reference_spec,
            "caller_unknown",
            "forbidden",
        )
        with self.assertRaises((TypeError, ValueError)):
            reverify(wrapper)

    def test_closed_paired_authority_replays_atomic_input_snapshot(self):
        template = self._raw_reference_outcome()
        inputs = tuple(object() for _ in range(9))

        def expected(*observed):
            self.assertEqual(
                tuple(id(item) for item in observed),
                tuple(id(item) for item in inputs),
            )
            return copy.deepcopy(template)

        def hydrate(raw, _registry, _protocol, _qualification):
            self.assertEqual(raw, template)
            return inputs

        (
            build,
            verify,
            _issue,
            reverify,
            outcome_property,
            _paired_property,
        ) = response_module._make_closed_paired_authority(
            expected,
            hydrate,
            lambda _raw: None,
            response_module._authority_structural_digest,
            response_module._authority_structural_seal,
        )
        wrapper = build(*inputs)
        self.assertEqual(outcome_property(wrapper), template)
        self.assertIsNot(outcome_property(wrapper), outcome_property(wrapper))
        hydrated = verify(
            copy.deepcopy(template),
            object(),
            object(),
            object(),
        )
        self.assertEqual(outcome_property(hydrated), template)

        stored = object.__getattribute__(
            wrapper,
            "_VerifiedPairedResponseOutcome__outcome",
        )
        object.__setattr__(
            stored.reference_spec,
            "caller_unknown",
            "forbidden",
        )
        with self.assertRaises((TypeError, ValueError)):
            reverify(wrapper)

    def test_paired_public_tail_is_live_and_caps_before_replay_or_hash(self):
        self.assertNotIn(
            "unavailable",
            build_paired_filtered_response.__qualname__,
        )
        oversized = object.__new__(PairedResponseOutcome)
        object.__setattr__(oversized, "status", "😀" * 5_000)
        object.__setattr__(oversized, "failure", None)
        object.__setattr__(oversized, "attempt_audit", None)
        object.__setattr__(oversized, "paired_response", None)
        object.__setattr__(oversized, "outcome_sha", "0" * 64)
        with (
            mock.patch.object(
                response_module,
                "canonical_sha",
                side_effect=AssertionError("HASH_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module,
                "_reverify_verified_certificate_backed_qualification",
                side_effect=AssertionError("QUALIFICATION_REPLAY_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module,
                "apply_factory_step",
                side_effect=AssertionError("EXECUTOR_RAN_FIRST"),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "resource cap"):
                verify_paired_filtered_response(
                    oversized,
                    object(),
                    object(),
                    object(),
                )

    def test_atomic_paired_stage_order_preserves_first_failure_evidence(self):
        run_spec, entry, actual_bridge = self._zero_bridge_audit()
        differences = tuple(
            (
                reciprocal_index,
                steps,
                np.zeros((1, 1), dtype=np.complex128),
            )
            for reciprocal_index in (
                run_spec.source_readout_bridge_grid.reciprocal_indices
            )
            for steps in run_spec.source_readout_bridge_steps
        )
        ablated_bridge = _build_source_readout_bridge_audit_from_differences(
            branch="matched_ablated",
            factory_sha=entry.factory_sha,
            transition_sha="a" * 64,
            dynamics_certificate_sha="b" * 64,
            run_spec=run_spec,
            registry_entry=entry,
            differences=differences,
        )
        values = freeze_complex_tensor(
            np.zeros(
                (
                    len(run_spec.response_grid.reciprocal_indices),
                    1,
                    1,
                ),
                dtype=np.complex128,
            )
        )
        cases = (
            (
                None,
                (
                    "actual_values",
                    "ablated_values",
                    "actual_bridge",
                    "ablated_bridge",
                ),
                None,
            ),
            (
                "actual_values",
                ("actual_values",),
                PairedResponseFailure.ACTUAL_RESPONSE_FAILED,
            ),
            (
                "actual_bridge",
                ("actual_values", "ablated_values", "actual_bridge"),
                PairedResponseFailure.ACTUAL_BRIDGE_FAILED,
            ),
            (
                "ablated_values",
                ("actual_values", "ablated_values"),
                PairedResponseFailure.ABLATED_RESPONSE_FAILED,
            ),
            (
                "ablated_bridge",
                (
                    "actual_values",
                    "ablated_values",
                    "actual_bridge",
                    "ablated_bridge",
                ),
                PairedResponseFailure.ABLATED_BRIDGE_FAILED,
            ),
        )
        for fail_at, expected_order, expected_failure in cases:
            with self.subTest(fail_at=fail_at):
                observed: list[str] = []

                def stage(name, result):
                    def run():
                        observed.append(name)
                        if fail_at == name:
                            raise ValueError(f"{name} failed")
                        return result

                    return run

                actual, ablated, failure = (
                    response_module._run_atomic_paired_branch_attempts(
                        actual_values_call=stage("actual_values", values),
                        actual_bridge_call=stage(
                            "actual_bridge",
                            actual_bridge,
                        ),
                        ablated_values_call=stage("ablated_values", values),
                        ablated_bridge_call=stage(
                            "ablated_bridge",
                            ablated_bridge,
                        ),
                    )
                )
                self.assertEqual(tuple(observed), expected_order)
                self.assertEqual(failure, expected_failure)
                self.assertIsNotNone(actual)
                assert actual is not None
                self.assertEqual(
                    actual.attempt_sha,
                    canonical_sha(source_readout_branch_attempt_audit_payload(actual)),
                )
                if expected_failure is PairedResponseFailure.ACTUAL_RESPONSE_FAILED:
                    self.assertIsNone(ablated)
                else:
                    self.assertIsNotNone(ablated)
                if fail_at == "ablated_values":
                    self.assertIsNotNone(actual.response_values)
                    self.assertIsNone(actual.bridge_audit)
                if fail_at == "actual_bridge":
                    self.assertIsNotNone(actual.response_values)
                    self.assertIsNone(actual.bridge_audit)
                    assert ablated is not None
                    self.assertIsNone(ablated.failure)
                    self.assertIsNotNone(ablated.response_values)
                    self.assertIsNone(ablated.bridge_audit)
                if fail_at == "ablated_bridge":
                    assert ablated is not None
                    self.assertIsNotNone(ablated.response_values)
                    self.assertIsNone(ablated.bridge_audit)

    def test_raw_hydration_replays_both_certificate_bodies(self):
        registry = object()
        protocol = object()
        qualification = object()
        actual_factory = object()
        ablated_factory = object()
        qualification_certificate = object()
        live_actual_transition = object()
        live_ablated_transition = object()
        live_actual_certificate = object()
        live_ablated_certificate = object()
        live_shell = object()
        raw_actual_certificate = object()
        raw_ablated_certificate = object()
        run_spec = SimpleNamespace(control_registry_entry_sha="entry-sha")
        reference_outcome = object()
        shell_outcome = SimpleNamespace(reference_outcome=reference_outcome)
        attempt = SimpleNamespace(
            run_spec=run_spec,
            actual_transition=object(),
            ablated_transition=object(),
            actual_dynamics_certificate=raw_actual_certificate,
            ablated_dynamics_certificate=raw_ablated_certificate,
            shell_outcome=shell_outcome,
        )
        outcome = SimpleNamespace(attempt_audit=attempt)
        construction = SimpleNamespace(
            pair=SimpleNamespace(
                actual=actual_factory,
                ablated=ablated_factory,
            )
        )
        qualification_view = SimpleNamespace(
            construction=construction,
            certificate=qualification_certificate,
        )
        registry_view = SimpleNamespace(
            parent=object(),
            registry=SimpleNamespace(
                entries=(
                    SimpleNamespace(
                        entry_sha="entry-sha",
                        control_id="full",
                    ),
                )
            ),
        )
        protocol_view = SimpleNamespace(registry=registry)

        with (
            mock.patch.object(
                response_module,
                "_preflight_paired_outcome_body",
            ),
            mock.patch.object(
                response_module,
                "_verify_paired_declared_hashes",
            ),
            mock.patch.object(
                response_module,
                "_reverify_verified_certificate_backed_qualification",
                return_value=qualification_view,
            ),
            mock.patch.object(
                response_module,
                "_reverify_verified_control_registry",
                return_value=registry_view,
            ),
            mock.patch.object(
                response_module,
                "_reverify_verified_window_calibration_protocol",
                return_value=protocol_view,
            ),
            mock.patch.object(
                response_module,
                "issue_synthetic_prestructure_authority",
                side_effect=(object(), object()),
            ),
            mock.patch.object(
                response_module,
                "verify_measured_transition",
                side_effect=(
                    live_actual_transition,
                    live_ablated_transition,
                ),
            ),
            mock.patch.object(
                response_module,
                "verify_dynamics_certificate",
                side_effect=(
                    live_actual_certificate,
                    live_ablated_certificate,
                ),
            ) as verify_certificate,
            mock.patch.object(
                response_module,
                "verify_endpoint_reference_outcome",
                return_value=object(),
            ),
            mock.patch.object(
                response_module,
                "verify_endpoint_shell_outcome",
                return_value=live_shell,
            ),
            mock.patch.object(
                response_module,
                "verify_response_run_spec",
                return_value=run_spec,
            ),
        ):
            hydrated = response_module._hydrate_paired_inputs_from_raw(
                outcome,
                registry,
                protocol,
                qualification,
            )

        self.assertIs(hydrated[4], live_ablated_transition)
        self.assertIs(hydrated[5], live_actual_certificate)
        self.assertIs(hydrated[6], live_ablated_certificate)
        self.assertIs(hydrated[8], live_shell)
        self.assertEqual(
            tuple(call.args[:2] for call in verify_certificate.call_args_list),
            (
                (raw_actual_certificate, actual_factory),
                (raw_ablated_certificate, ablated_factory),
            ),
        )

    def test_wrapper_properties_ignore_global_reverify_rebindings(self):
        fake_reference = object.__new__(VerifiedEndpointReferenceOutcome)
        fake_shell = object.__new__(VerifiedEndpointShellOutcome)
        fake_pair = object.__new__(VerifiedPairedResponseOutcome)
        patched = mock.Mock()
        patched.outcome = self._raw_reference_outcome()
        with (
            mock.patch.object(
                response_module,
                "_reverify_verified_endpoint_reference_outcome",
                return_value=patched,
            ),
            mock.patch.object(
                response_module,
                "_reverify_verified_endpoint_shell_outcome",
                return_value=patched,
            ),
            mock.patch.object(
                response_module,
                "_reverify_verified_paired_response_outcome",
                return_value=patched,
            ),
        ):
            for fake in (fake_reference, fake_shell, fake_pair):
                with self.subTest(wrapper=type(fake).__name__):
                    with self.assertRaises((TypeError, ValueError)):
                        _ = fake.outcome

    def test_source_frame_lower_is_not_above_high_precision_true_value(self):
        basis = self.registry.registry.entries[2].source_basis
        trials = freeze_complex_tensor(
            np.asarray(
                (
                    (1.0, 1.0),
                    (1.0, 1.010001500225033755),
                ),
                dtype=np.complex128,
            )
        )
        certificate = build_source_frame_coverage_certificate(
            basis,
            trials,
        )
        high_precision_true = Fraction("2.4882602544615136532e-05")
        self.assertLessEqual(
            Fraction.from_float(certificate.frame_operator_lower),
            high_precision_true,
        )

    def test_source_frame_rejects_unknown_field_on_exact_basis_before_issuance(
        self,
    ):
        basis = copy.deepcopy(self.registry.registry.entries[0].source_basis)
        source_count = len(basis.vectors_wire)
        trials = freeze_complex_tensor(np.eye(source_count, dtype=np.complex128))
        certificate = build_source_frame_coverage_certificate(
            basis,
            trials,
        )
        object.__setattr__(basis, "caller_unknown", "forbidden")
        for operation in (
            lambda: build_source_frame_coverage_certificate(basis, trials),
            lambda: verify_source_frame_coverage_certificate(
                certificate,
                basis,
                trials,
            ),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises((TypeError, ValueError)):
                    operation()

    def test_source_frame_rejects_basis_subclass_with_unknown_field(self):
        @dataclasses.dataclass(frozen=True)
        class ForgedBasis(response_module.BasisManifest):
            caller_unknown: str = "forbidden"

        basis = self.registry.registry.entries[0].source_basis
        forged = ForgedBasis(
            **{
                name: getattr(basis, name)
                for name in response_module.BasisManifest.__dataclass_fields__
            }
        )
        source_count = len(basis.vectors_wire)
        trials = freeze_complex_tensor(np.eye(source_count, dtype=np.complex128))
        certificate = build_source_frame_coverage_certificate(
            basis,
            trials,
        )
        for operation in (
            lambda: build_source_frame_coverage_certificate(forged, trials),
            lambda: verify_source_frame_coverage_certificate(
                certificate,
                forged,
                trials,
            ),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises((TypeError, ValueError)):
                    operation()

    def test_source_frame_cap_fails_before_hash_or_tensor_decode(self):
        basis = self.registry.registry.entries[0].source_basis
        source_count = len(basis.vectors_wire)
        trials = freeze_complex_tensor(np.eye(source_count, dtype=np.complex128))
        certificate = build_source_frame_coverage_certificate(
            basis,
            trials,
        )
        oversized = copy.deepcopy(trials)
        object.__setattr__(
            oversized,
            "shape",
            (source_count, 16_777_217),
        )
        oversized_certificate = copy.deepcopy(certificate)
        object.__setattr__(
            oversized_certificate.trial_matrix,
            "shape",
            (source_count, 16_777_217),
        )
        for operation in (
            lambda: build_source_frame_coverage_certificate(
                basis,
                oversized,
            ),
            lambda: verify_source_frame_coverage_certificate(
                certificate,
                basis,
                oversized,
            ),
            lambda: verify_source_frame_coverage_certificate(
                oversized_certificate,
                basis,
                trials,
            ),
        ):
            with self.subTest(operation=operation):
                with (
                    mock.patch.object(
                        response_module,
                        "canonical_sha",
                        side_effect=AssertionError("RESPONSE_HASH_RAN_FIRST"),
                    ),
                    mock.patch.object(
                        factory_module,
                        "canonical_sha",
                        side_effect=AssertionError("TENSOR_HASH_RAN_FIRST"),
                    ),
                    mock.patch.object(
                        response_module,
                        "frozen_tensor_array",
                        side_effect=AssertionError("TENSOR_DECODE_RAN_FIRST"),
                    ),
                ):
                    with self.assertRaises(ValueError):
                        operation()

    def test_bridge_cardinality_cap_fails_before_hash_or_tensor_decode(self):
        run_spec, entry, audit = self._zero_bridge_audit()
        oversized = dataclasses.replace(
            audit,
            matrix_audits=audit.matrix_audits + (audit.matrix_audits[0],),
        )
        with (
            mock.patch.object(
                response_module,
                "canonical_sha",
                side_effect=AssertionError("HASH_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module,
                "frozen_tensor_array",
                side_effect=AssertionError("TENSOR_DECODE_RAN_FIRST"),
            ),
        ):
            with self.assertRaises(ValueError):
                verify_source_readout_bridge_audit_body(
                    oversized,
                    run_spec,
                    entry,
                )

    def test_response_value_shape_fails_before_tensor_verification(self):
        run_spec, entry, audit = self._zero_bridge_audit()
        wrong_values = freeze_complex_tensor(np.zeros((2, 2), dtype=np.complex128))
        with mock.patch.object(
            response_module,
            "verify_frozen_tensor",
            side_effect=AssertionError("TENSOR_VERIFY_RAN_FIRST"),
        ):
            with self.assertRaises(ValueError):
                _build_source_readout_response_from_values(
                    branch="actual",
                    factory_sha=entry.factory_sha,
                    transition_sha="a" * 64,
                    dynamics_certificate_sha="b" * 64,
                    run_spec=run_spec,
                    shell_manifest_sha="c" * 64,
                    bridge_audit=audit,
                    values=wrong_values,
                )

    def test_difference_shapes_fail_before_whitener_decode_or_output_allocation(
        self,
    ):
        run_spec = verify_response_run_spec(
            self._run_spec(),
            self.protocol,
        )
        entry = self.registry.registry.entries[0]
        differences = [
            (
                reciprocal_index,
                steps,
                np.zeros((1, 1), dtype=np.complex128),
            )
            for reciprocal_index in (
                run_spec.source_readout_bridge_grid.reciprocal_indices
            )
            for steps in run_spec.source_readout_bridge_steps
        ]
        reciprocal_index, steps, _raw = differences[0]
        differences[0] = (
            reciprocal_index,
            steps,
            np.zeros((2, 1), dtype=np.complex128),
        )
        with (
            mock.patch.object(
                response_module,
                "frozen_tensor_array",
                side_effect=AssertionError("WHITENER_DECODE_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module,
                "freeze_complex_tensor",
                side_effect=AssertionError("OUTPUT_ALLOCATION_RAN_FIRST"),
            ),
        ):
            with self.assertRaises(ValueError):
                _build_source_readout_bridge_audit_from_differences(
                    branch="actual",
                    factory_sha=entry.factory_sha,
                    transition_sha="a" * 64,
                    dynamics_certificate_sha="b" * 64,
                    run_spec=run_spec,
                    registry_entry=entry,
                    differences=tuple(differences),
                )

    def test_executor_bridge_work_cap_fails_before_replay_hash_or_allocation(self):
        run_spec = copy.deepcopy(self._run_spec())
        object.__setattr__(
            run_spec,
            "source_readout_bridge_steps",
            (2, 16_384),
        )
        with (
            mock.patch.object(
                response_module,
                "canonical_sha",
                side_effect=AssertionError("HASH_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module,
                "_reverify_verified_factory",
                side_effect=AssertionError("FACTORY_REPLAY_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module,
                "apply_factory_step",
                side_effect=AssertionError("EXECUTOR_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module.np,
                "zeros",
                side_effect=AssertionError("NP_ALLOCATION_RAN_FIRST"),
            ),
        ):
            with self.assertRaises(ValueError):
                _measure_source_readout_bridge(
                    branch="actual",
                    factory=object(),
                    transition=object(),
                    dynamics_certificate_sha="b" * 64,
                    run_spec=run_spec,
                    registry_entry=self.registry.registry.entries[0],
                )

    def test_response_grid_cap_fails_before_transition_schur_or_np_allocation(
        self,
    ):
        run_spec = copy.deepcopy(self._run_spec())
        first_index = run_spec.response_grid.reciprocal_indices[0]
        object.__setattr__(
            run_spec.response_grid,
            "reciprocal_indices",
            (first_index,) * 262_145,
        )
        with (
            mock.patch.object(
                response_module,
                "_reverify_verified_transition",
                side_effect=AssertionError("TRANSITION_REPLAY_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module,
                "compute_fejer_filtered_response",
                side_effect=AssertionError("SCHUR_RAN_FIRST"),
            ),
            mock.patch.object(
                response_module.np,
                "empty",
                side_effect=AssertionError("NP_ALLOCATION_RAN_FIRST"),
            ),
        ):
            with self.assertRaises(ValueError):
                response_module._compute_source_readout_response_values(
                    "actual",
                    object(),
                    object(),
                    run_spec,
                    object(),
                )

    def test_phase_grid_collision_and_resolved_candidates_differ(self):
        template = self._raw_reference_outcome()
        identity = np.eye(2, dtype=np.complex128)
        source = np.asarray(((1.0,), (0.0,)), dtype=np.complex128)
        readout = source.conj().T.copy()
        grid_step = phase_grid_step(256)

        collided = _build_endpoint_reference_outcome_from_matrices(
            template.reference_spec,
            np.diag(
                np.exp(
                    1.0j
                    * np.asarray(
                        (
                            math.pi / 2.0,
                            math.pi / 2.0 + 0.5 * grid_step,
                        )
                    )
                )
            ).astype(np.complex128),
            identity,
            source,
            readout,
        )
        resolved = _build_endpoint_reference_outcome_from_matrices(
            template.reference_spec,
            np.diag(
                np.exp(
                    1.0j
                    * np.asarray(
                        (
                            math.pi / 2.0,
                            math.pi / 2.0 + 2.0 * grid_step,
                        )
                    )
                )
            ).astype(np.complex128),
            identity,
            source,
            readout,
        )
        self.assertEqual(
            collided.failure,
            EndpointReferenceFailure.PHASE_BAND_NONUNIQUE,
        )
        self.assertNotEqual(
            resolved.failure,
            EndpointReferenceFailure.PHASE_BAND_NONUNIQUE,
        )

    def test_reference_runner_up_margin_is_reachable_with_two_candidates(self):
        template = self._raw_reference_outcome()
        identity = np.eye(2, dtype=np.complex128)
        gap = 2.0 * phase_grid_step(256)
        transition = np.diag(
            np.exp(
                1.0j
                * np.asarray(
                    (math.pi / 2.0, math.pi / 2.0 + gap),
                )
            )
        ).astype(np.complex128)
        outcome = _build_endpoint_reference_outcome_from_matrices(
            template.reference_spec,
            transition,
            identity,
            identity,
            identity,
        )
        self.assertEqual(
            outcome.failure,
            EndpointReferenceFailure.RUNNER_UP_MARGIN_FAILED,
        )

    def test_shell_phase_grid_collision_has_distinct_typed_failure(self):
        reference, spec, matrices, metrics = self._shell_inputs()
        grid_step = phase_grid_step(spec.candidate_fejer_order)
        transition = np.diag(
            np.exp(
                1.0j
                * np.asarray(
                    (math.pi / 2.0 + 0.5 * grid_step, math.pi / 2.0),
                )
            )
        ).astype(np.complex128)
        matrices = tuple(
            transition.copy()
            for _ in matrices
        )
        outcome = _build_endpoint_shell_outcome_from_matrices(
            reference,
            spec,
            matrices,
            metrics,
            np.eye(2, dtype=np.complex128),
            np.eye(2, dtype=np.complex128),
            actual_factory_sha=spec.control_registry_entry.factory_sha,
            actual_transition_sha="a" * 64,
            actual_dynamics_certificate_sha="b" * 64,
            dt=0.25,
        )
        self.assertEqual(
            outcome.failure,
            EndpointShellFailure.PHASE_SEPARATION_FAILED,
        )

    def test_shell_nearest_gap_failure_has_its_own_producer(self):
        reference, spec, matrices, metrics = self._shell_inputs()
        gap = 2.0 * phase_grid_step(spec.candidate_fejer_order)
        self.assertLess(gap, phase_separation_min(spec.candidate_fejer_order))
        transition = np.diag(
            np.exp(
                1.0j
                * np.asarray(
                    (math.pi / 2.0 + gap, math.pi / 2.0),
                )
            )
        ).astype(np.complex128)
        matrices = tuple(
            transition.copy()
            for _ in matrices
        )
        outcome = _build_endpoint_shell_outcome_from_matrices(
            reference,
            spec,
            matrices,
            metrics,
            np.eye(2, dtype=np.complex128),
            np.eye(2, dtype=np.complex128),
            actual_factory_sha=spec.control_registry_entry.factory_sha,
            actual_transition_sha="a" * 64,
            actual_dynamics_certificate_sha="b" * 64,
            dt=0.25,
        )
        self.assertEqual(
            outcome.failure,
            EndpointShellFailure.GAP_FAILED,
        )

    def test_recursive_exact_wire_rejects_direction_and_registry_unknowns(self):
        run_spec = copy.deepcopy(self._run_spec())
        object.__setattr__(
            run_spec.response_grid.direction_manifest,
            "caller_unknown",
            "forbidden",
        )
        with self.assertRaises((TypeError, ValueError)):
            response_run_spec_payload(run_spec)

        outcome = copy.deepcopy(self._raw_reference_outcome())
        entry = outcome.reference_spec.control_registry_entry
        object.__setattr__(
            entry.source_basis,
            "caller_unknown",
            "forbidden",
        )
        with self.assertRaises((TypeError, ValueError)):
            endpoint_reference_spec_payload(outcome.reference_spec)

        outcome = copy.deepcopy(self._raw_reference_outcome())
        tensor = outcome.reference_spec.control_registry_entry.readout_calibration_spec.source_metric_whitener
        object.__setattr__(tensor, "caller_unknown", "forbidden")
        with self.assertRaises((TypeError, ValueError)):
            endpoint_reference_spec_payload(outcome.reference_spec)


if __name__ == "__main__":
    unittest.main()
