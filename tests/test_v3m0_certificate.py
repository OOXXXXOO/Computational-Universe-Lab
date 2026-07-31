from __future__ import annotations

import dataclasses
import contextlib
import functools
import inspect
import sys
import types
import unittest
from unittest import mock

import numpy as np

import rulespace_v3.certificate as certificate_module
import rulespace_v3.spectral as spectral_module
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.bridge import (
    audit_full_state_bridge,
    bridge_audit_payload,
    build_full_state_bridge_spec,
)
from rulespace_v3.certificate import (
    DynamicsCertificationFailure,
    VerifiedDynamicsCertificate,
    VerifiedDynamicsCertificationOutcome,
    _reverify_verified_dynamics_certificate,
    _reverify_verified_dynamics_certification_outcome,
    certify_transition_dynamics,
    dynamics_certificate_payload,
    verify_dynamics_certificate,
    verify_dynamics_certification_outcome,
)
from rulespace_v3.contracts import UndefinedReason
from rulespace_v3.dynamics import (
    measure_transition,
    measured_transition_payload,
    transition_kernel_array,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor
from rulespace_v3.grids import build_dynamics_grid_manifest
from rulespace_v3.instability import (
    _build_instability_growth_counter_witness_from_raw,
)
from rulespace_v3.metric import build_stability_metric_witness
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.registry import build_closed_control_registry
from rulespace_v3.replay_scope import (
    _replay_scope_statistics,
    _scoped_replay_context,
)
from rulespace_v3.runtime import (
    RUNTIME_MAX_SOURCE_FILES,
    issue_runtime_evidence_manifest,
)
from rulespace_v3.spectral import (
    POWER_DRIFT_AUDIT_SCHEMA_VERSION,
    PowerDriftAudit,
    power_drift_audit_payload,
)
from rulespace_v3.structure import (
    StructureManifest,
    build_structure_manifest,
    reality_certificate_payload,
)
from tests.test_v3m0_dynamics import _quarter_turn_controls


class CertificateSpectralDispatchBindingTests(unittest.TestCase):
    def test_build_and_hydrate_core_bind_only_generic_spectral_dispatch(self):
        build_names = set(
            certificate_module._certify_transition_dynamics_core.__code__.co_names
        )
        replay_names = set(
            certificate_module._verify_failure_evidence.__code__.co_names
        )
        hydrate_names = set(certificate_module._validate_certificate.__code__.co_names)
        spectral_verify_names = set(
            spectral_module.verify_spectral_margin_coverage.__code__.co_names
        )

        self.assertIn("build_spectral_margin_coverage", build_names)
        self.assertIn("build_spectral_margin_coverage", replay_names)
        self.assertIn("verify_spectral_margin_coverage", hydrate_names)
        self.assertIn(
            "build_spectral_margin_coverage",
            spectral_verify_names,
        )
        self.assertNotIn(
            "build_exact_zero_spectral_margin_coverage",
            build_names | replay_names | hydrate_names | spectral_verify_names,
        )

    def test_all_top_level_certificate_operations_open_public_replay_scopes(self):
        self.assertIn(
            "_scoped_replay_context",
            certificate_module.certify_transition_dynamics.func.__code__.co_names,
        )
        self.assertIn(
            "_scoped_replay_context",
            certificate_module.verify_dynamics_certificate.func.__code__.co_names,
        )
        self.assertIn(
            "_scoped_replay_context",
            certificate_module.verify_dynamics_certification_outcome.func.__code__.co_names,
        )


class DynamicsCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        cls.construction = matched_ablation(cls.controls[0].factory)
        assert cls.construction.pair is not None
        cls.factory = cls.construction.pair.actual
        cls.authority = issue_synthetic_prestructure_authority(
            cls.parent,
            cls.registry,
            "full",
            cls.construction,
            "actual",
        )
        cls.transition = measure_transition(cls.factory, cls.authority)
        cls.structure = build_structure_manifest(
            cls.factory,
            cls.authority,
        )
        cls.metric = build_stability_metric_witness(
            cls.factory,
            cls.authority,
            cls.structure,
        )
        cls.bridge_spec = build_full_state_bridge_spec(
            cls.factory,
            cls.authority,
        )
        cls.grid = build_dynamics_grid_manifest(
            cls.transition.transition.support_offsets,
            cls.metric.metric_support_offsets,
        )
        cls.runtime = issue_runtime_evidence_manifest()
        cls.result = certify_transition_dynamics(
            cls.factory,
            cls.transition,
            cls.authority,
            cls.structure,
            cls.metric,
            cls.bridge_spec,
            cls.grid,
            cls.runtime,
        )

    def _certify(self, *, core: bool = False):
        issuer = (
            certificate_module._certify_transition_dynamics_core
            if core
            else certify_transition_dynamics
        )
        return issuer(
            self.factory,
            self.transition,
            self.authority,
            self.structure,
            self.metric,
            self.bridge_spec,
            self.grid,
            self.runtime,
        )

    def _call_with_captured_public_scope(self, operation, *args):
        root = operation.func
        private_globals = root.__globals__
        original_context = private_globals["_scoped_replay_context"]
        observed = []

        @contextlib.contextmanager
        def observing_context():
            with original_context():
                yield
                observed.append(_replay_scope_statistics())

        private_globals["_scoped_replay_context"] = observing_context
        try:
            result = operation(*args)
        finally:
            private_globals["_scoped_replay_context"] = original_context
        self.assertEqual(len(observed), 1)
        return result, observed[0]

    def test_build_and_outcome_hydrate_reuse_one_top_level_scope(self):
        built, build_statistics = self._call_with_captured_public_scope(
            certify_transition_dynamics,
            self.factory,
            self.transition,
            self.authority,
            self.structure,
            self.metric,
            self.bridge_spec,
            self.grid,
            self.runtime,
        )
        self.assertTrue(built.outcome.status.defined)
        hydrated, hydrate_statistics = self._call_with_captured_public_scope(
            verify_dynamics_certification_outcome,
            built.outcome,
            self.factory,
            self.authority,
        )
        self.assertTrue(hydrated.outcome.status.defined)

        certificate_namespace = (
            "rulespace_v3.certificate.VerifiedDynamicsCertificate"
        )
        outcome_namespace = (
            "rulespace_v3.certificate."
            "VerifiedDynamicsCertificationOutcome"
        )
        for statistics in (build_statistics, hydrate_statistics):
            full_records = dict(statistics.full_records)
            hits = dict(statistics.hits)
            self.assertEqual(full_records.get(certificate_namespace), 1)
            self.assertEqual(full_records.get(outcome_namespace), 1)
            self.assertGreaterEqual(hits.get(certificate_namespace, 0), 1)

    def _jordan_witness(self):
        raw = self.transition.transition
        kernel = np.zeros_like(transition_kernel_array(self.transition))
        kernel[:, :, 0] = np.asarray(
            [[1.0, 1.0], [0.0, 1.0]],
            dtype=np.complex128,
        )
        changed = dataclasses.replace(
            raw,
            kernel=freeze_complex_tensor(kernel),
            transition_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            transition_sha=canonical_sha(measured_transition_payload(changed)),
        )
        witness = _build_instability_growth_counter_witness_from_raw(changed)
        assert witness is not None
        return witness

    def test_success_recursively_binds_all_evidence_and_hydrates_capabilities(self):
        result = self.result
        self.assertIs(type(result), VerifiedDynamicsCertificationOutcome)
        self.assertTrue(result.outcome.status.defined)
        self.assertIsNone(result.outcome.failure)
        self.assertIsNotNone(result.outcome.certificate)
        self.assertIs(type(result.certificate), VerifiedDynamicsCertificate)
        assert result.certificate is not None
        certificate = result.certificate.certificate
        self.assertEqual(
            certificate.certificate_sha,
            canonical_sha(dynamics_certificate_payload(certificate)),
        )
        self.assertEqual(
            certificate.transition.transition_sha,
            self.transition.transition.transition_sha,
        )
        self.assertEqual(
            certificate.prestructure_authority.authority_sha,
            self.authority.authority.authority_sha,
        )
        self.assertLessEqual(
            certificate.structure_residual.raw_global_momentum_supremum_bound,
            1.0e-12,
        )
        self.assertLessEqual(
            certificate.normalized_metric_residual.normalized_metric_residual_upper,
            1.0e-12,
        )
        self.assertLessEqual(
            certificate.full_state_bridge_audit.normalized_max,
            1.0e-12,
        )
        self.assertLessEqual(certificate.power_drift.drift_upper, 1.0e-8)

        hydrated = verify_dynamics_certificate(
            certificate,
            self.factory,
            self.authority,
        )
        self.assertIs(type(hydrated), VerifiedDynamicsCertificate)
        verified_outcome = verify_dynamics_certification_outcome(
            result.outcome,
            self.factory,
            self.authority,
        )
        self.assertIs(
            type(verified_outcome),
            VerifiedDynamicsCertificationOutcome,
        )
        self.assertIsNotNone(verified_outcome.certificate)

    def test_certificate_hit_revalidates_factory_and_prestructure_dependencies(self):
        certificate = self.result.certificate
        assert certificate is not None
        namespace = (
            "rulespace_v3.certificate.VerifiedDynamicsCertificate"
        )
        factory_primitive = self.factory.factory.primitives[0]
        prestructure_snapshot = self.authority.authority.ablation_pair_snapshot
        cases = (
            (
                "factory",
                factory_primitive,
                "coefficient_wire",
                (
                    factory_primitive.coefficient_wire[0] + 1.0,
                    factory_primitive.coefficient_wire[1],
                ),
            ),
            (
                "prestructure",
                prestructure_snapshot,
                "snapshot_sha",
                "f" * 64,
            ),
        )
        with _scoped_replay_context():
            certificate_module._reverify_verified_dynamics_certificate_core(
                certificate
            )
            for label, target, field, changed in cases:
                with self.subTest(dependency=label):
                    original = getattr(target, field)
                    hits_before = dict(_replay_scope_statistics().hits).get(
                        namespace,
                        0,
                    )
                    try:
                        object.__setattr__(target, field, changed)
                        with self.assertRaises((TypeError, ValueError)):
                            certificate_module._reverify_verified_dynamics_certificate_core(
                                certificate
                            )
                    finally:
                        object.__setattr__(target, field, original)
                    hits_after = dict(_replay_scope_statistics().hits).get(
                        namespace,
                        0,
                    )
                    self.assertEqual(hits_after, hits_before)
            outcome_namespace = (
                "rulespace_v3.certificate."
                "VerifiedDynamicsCertificationOutcome"
            )
            child_body = object.__getattribute__(
                certificate,
                "_VerifiedDynamicsCertificate__certificate",
            )
            outcome_body = dataclasses.replace(
                self.result.outcome,
                certificate=dataclasses.replace(child_body),
            )
            outcome = (
                certificate_module._issue_verified_dynamics_certification_outcome(
                    outcome_body,
                    certificate,
                    self.factory,
                    self.authority,
                )
            )
            outcome_hits_before = dict(_replay_scope_statistics().hits).get(
                outcome_namespace,
                0,
            )
            original = child_body.certificate_sha
            try:
                object.__setattr__(child_body, "certificate_sha", "f" * 64)
                with self.assertRaises((TypeError, ValueError)):
                    certificate_module._reverify_verified_dynamics_certification_outcome_core(
                        outcome
                    )
            finally:
                object.__setattr__(child_body, "certificate_sha", original)
            outcome_hits_after = dict(_replay_scope_statistics().hits).get(
                outcome_namespace,
                0,
            )
            self.assertEqual(outcome_hits_after, outcome_hits_before)

    def test_success_hydrate_dispatches_through_generic_spectral_builder(self):
        assert self.result.certificate is not None
        certificate = self.result.certificate.certificate
        with (
            certificate_module._scoped_replay_context(),
            mock.patch.object(
                spectral_module,
                "build_spectral_margin_coverage",
                wraps=spectral_module.build_spectral_margin_coverage,
            ) as dispatch,
        ):
            hydrated = certificate_module._verify_dynamics_certificate_core(
                certificate,
                self.factory,
                self.authority,
            )
        self.assertIs(type(hydrated), VerifiedDynamicsCertificate)
        dispatch.assert_called_once()

    def test_raw_failure_hydrator_rejects_false_prestructure_failure(self):
        attempt = certificate_module._attempt(
            factory_sha=self.factory.factory.factory_sha,
            authority_sha=self.authority.authority.authority_sha,
            transition_sha=None,
            failure=DynamicsCertificationFailure.PRESTRUCTURE_INVALID,
            reality=None,
            structure_residual=None,
            metric_residual=None,
            spectral_margins=None,
            normalized_metric_residual=None,
            full_state_bridge_audit=None,
            power_drift=None,
            instability_counter_witness=None,
        )
        forged = certificate_module._raw_outcome(
            failure=DynamicsCertificationFailure.PRESTRUCTURE_INVALID,
            attempt=attempt,
            certificate=None,
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_certification_outcome(
                forged,
                self.factory,
                self.authority,
            )

    def test_raw_failure_hydrator_rejects_false_reality_violation(self):
        attempt = certificate_module._attempt(
            factory_sha=self.factory.factory.factory_sha,
            authority_sha=self.authority.authority.authority_sha,
            transition_sha=self.transition.transition.transition_sha,
            failure=DynamicsCertificationFailure.REALITY_INVALID,
            reality=None,
            structure_residual=None,
            metric_residual=None,
            spectral_margins=None,
            normalized_metric_residual=None,
            full_state_bridge_audit=None,
            power_drift=None,
            instability_counter_witness=None,
        )
        forged = certificate_module._raw_outcome(
            failure=DynamicsCertificationFailure.REALITY_INVALID,
            attempt=attempt,
            certificate=None,
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_certification_outcome(
                forged,
                self.factory,
                self.authority,
            )

    def test_raw_failure_hydrator_rejects_false_bridge_failure(self):
        successful = self.result.outcome.attempt_audit
        attempt = certificate_module._attempt(
            factory_sha=successful.factory_sha,
            authority_sha=successful.prestructure_authority_sha,
            transition_sha=successful.transition_sha,
            failure=DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED,
            reality=successful.reality,
            structure_residual=successful.structure_residual,
            metric_residual=successful.metric_residual,
            spectral_margins=successful.spectral_margins,
            normalized_metric_residual=(successful.normalized_metric_residual),
            full_state_bridge_audit=None,
            power_drift=None,
            instability_counter_witness=None,
        )
        forged = certificate_module._raw_outcome(
            failure=DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED,
            attempt=attempt,
            certificate=None,
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_certification_outcome(
                forged,
                self.factory,
                self.authority,
            )

    def test_raw_failure_hydrator_rejects_false_power_failure(self):
        successful = self.result.outcome.attempt_audit
        attempt = certificate_module._attempt(
            factory_sha=successful.factory_sha,
            authority_sha=successful.prestructure_authority_sha,
            transition_sha=successful.transition_sha,
            failure=DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED,
            reality=successful.reality,
            structure_residual=successful.structure_residual,
            metric_residual=successful.metric_residual,
            spectral_margins=successful.spectral_margins,
            normalized_metric_residual=(successful.normalized_metric_residual),
            full_state_bridge_audit=(successful.full_state_bridge_audit),
            power_drift=None,
            instability_counter_witness=None,
        )
        forged = certificate_module._raw_outcome(
            failure=DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED,
            attempt=attempt,
            certificate=None,
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_certification_outcome(
                forged,
                self.factory,
                self.authority,
            )

    def test_raw_failure_hydrator_replays_each_unresolved_stage(self):
        successful = self.result.outcome.attempt_audit
        cases = (
            (
                DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED,
                None,
                None,
                None,
                None,
            ),
            (
                DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED,
                None,
                None,
                None,
                None,
            ),
            (
                DynamicsCertificationFailure.METRIC_RAW_UNRESOLVED,
                successful.structure_residual,
                None,
                None,
                None,
            ),
            (
                DynamicsCertificationFailure.SPECTRAL_COVERAGE_UNRESOLVED,
                successful.structure_residual,
                successful.metric_residual,
                None,
                None,
            ),
            (
                DynamicsCertificationFailure.NORMALIZED_METRIC_UNRESOLVED,
                successful.structure_residual,
                successful.metric_residual,
                successful.spectral_margins,
                None,
            ),
        )
        for (
            failure,
            structure_residual,
            metric_residual,
            spectral_margins,
            normalized_metric_residual,
        ) in cases:
            with self.subTest(failure=failure):
                attempt = certificate_module._attempt(
                    factory_sha=successful.factory_sha,
                    authority_sha=successful.prestructure_authority_sha,
                    transition_sha=successful.transition_sha,
                    failure=failure,
                    reality=successful.reality,
                    structure_residual=structure_residual,
                    metric_residual=metric_residual,
                    spectral_margins=spectral_margins,
                    normalized_metric_residual=(normalized_metric_residual),
                    full_state_bridge_audit=None,
                    power_drift=None,
                    instability_counter_witness=None,
                )
                forged = certificate_module._raw_outcome(
                    failure=failure,
                    attempt=attempt,
                    certificate=None,
                )
                with self.assertRaises((TypeError, ValueError)):
                    verify_dynamics_certification_outcome(
                        forged,
                        self.factory,
                        self.authority,
                    )

    def test_outer_resign_cannot_hide_nested_tampering_or_unknown_fields(self):
        assert self.result.certificate is not None
        certificate = self.result.certificate.certificate
        assert certificate.reality is not None
        changed_reality = dataclasses.replace(
            certificate.reality,
            factory_coefficient_count=(
                certificate.reality.factory_coefficient_count + 1
            ),
            reality_certificate_sha="0" * 64,
        )
        changed_reality = dataclasses.replace(
            changed_reality,
            reality_certificate_sha=canonical_sha(
                reality_certificate_payload(changed_reality)
            ),
        )
        changed = dataclasses.replace(
            certificate,
            reality=changed_reality,
            certificate_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            certificate_sha=canonical_sha(dynamics_certificate_payload(changed)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_certificate(
                changed,
                self.factory,
                self.authority,
            )

        @dataclasses.dataclass(frozen=True)
        class UnknownStructure(StructureManifest):
            unknown_field: str = "forbidden"

        forged_structure = UnknownStructure(
            **{
                field.name: getattr(certificate.structure, field.name)
                for field in dataclasses.fields(StructureManifest)
            }
        )
        unknown = object.__new__(type(certificate))
        for field in dataclasses.fields(certificate):
            object.__setattr__(
                unknown,
                field.name,
                getattr(certificate, field.name),
            )
        object.__setattr__(unknown, "structure", forged_structure)
        with self.assertRaises((TypeError, ValueError)):
            dynamics_certificate_payload(unknown)
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_certificate(
                unknown,
                self.factory,
                self.authority,
            )

    def test_frozen_verifier_ignores_external_executor_rebinding(self):
        assert self.result.certificate is not None
        certificate = self.result.certificate.certificate
        with mock.patch(
            "rulespace_v3.dynamics.apply_factory_step",
            side_effect=ValueError("executor changed"),
        ):
            verified = verify_dynamics_certificate(
                certificate,
                self.factory,
                self.authority,
            )
            self.assertIs(type(verified), VerifiedDynamicsCertificate)

        with mock.patch(
            "rulespace_v3.bridge.apply_factory_step",
            side_effect=ValueError("bridge executor changed"),
        ):
            verified = verify_dynamics_certificate(
                certificate,
                self.factory,
                self.authority,
            )
            self.assertIs(type(verified), VerifiedDynamicsCertificate)

    def test_opaque_wrappers_reject_fakes_slot_copy_and_slot_mutation(self):
        assert self.result.certificate is not None
        verified = verify_dynamics_certificate(
            self.result.certificate.certificate,
            self.factory,
            self.authority,
        )
        fake = object.__new__(VerifiedDynamicsCertificate)
        with self.assertRaises((TypeError, ValueError)):
            _reverify_verified_dynamics_certificate(fake)

        copied = object.__new__(VerifiedDynamicsCertificate)
        for field in ("__certificate", "__token", "__seal"):
            mangled = f"_VerifiedDynamicsCertificate{field}"
            object.__setattr__(
                copied,
                mangled,
                object.__getattribute__(verified, mangled),
            )
        with self.assertRaises((TypeError, ValueError)):
            _reverify_verified_dynamics_certificate(copied)

        object.__setattr__(
            verified,
            "_VerifiedDynamicsCertificate__certificate",
            dataclasses.replace(
                verified.certificate,
                certificate_sha="f" * 64,
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            _reverify_verified_dynamics_certificate(verified)

        fake_outcome = object.__new__(VerifiedDynamicsCertificationOutcome)
        with self.assertRaises((TypeError, ValueError)):
            _reverify_verified_dynamics_certification_outcome(fake_outcome)

    def test_resource_attack_is_rejected_before_canonical_serialization(self):
        assert self.result.certificate is not None
        certificate = self.result.certificate.certificate
        forged_runtime = object.__new__(type(certificate.runtime))
        for field in dataclasses.fields(certificate.runtime):
            object.__setattr__(
                forged_runtime,
                field.name,
                getattr(certificate.runtime, field.name),
            )
        object.__setattr__(
            forged_runtime,
            "source_closure",
            tuple(
                ("rulespace_v3/runtime.py", "0" * 64)
                for _ in range(RUNTIME_MAX_SOURCE_FILES + 1)
            ),
        )
        forged = object.__new__(type(certificate))
        for field in dataclasses.fields(certificate):
            object.__setattr__(
                forged,
                field.name,
                getattr(certificate, field.name),
            )
        object.__setattr__(forged, "runtime", forged_runtime)
        with mock.patch(
            "rulespace_v3.certificate._bounded_canonical_sha",
            side_effect=AssertionError("hashing ran before resource preflight"),
        ) as sha:
            with self.assertRaises((TypeError, ValueError)):
                certificate_module._verify_dynamics_certificate_core(
                    forged,
                    self.factory,
                    self.authority,
                )
        sha.assert_not_called()

    def test_failure_order_reality_then_resource_then_jordan_then_metric(self):
        with (
            mock.patch(
                "rulespace_v3.certificate.certify_reality",
                side_effect=ValueError("reality mismatch"),
            ),
            mock.patch(
                "rulespace_v3.certificate._preflight_laurent_resources",
                side_effect=AssertionError("resource stage ran"),
            ) as later,
        ):
            outcome = self._certify(core=True).outcome
        self.assertEqual(
            outcome.failure,
            DynamicsCertificationFailure.REALITY_INVALID,
        )
        self.assertEqual(outcome.status.reason, UndefinedReason.REALITY_VIOLATION)
        later.assert_not_called()

        with (
            mock.patch(
                "rulespace_v3.certificate._preflight_laurent_resources",
                side_effect=ValueError("resource cap"),
            ),
            mock.patch(
                "rulespace_v3.certificate.certify_instability_growth_counter_witness",
                side_effect=AssertionError("Jordan stage ran"),
            ) as jordan,
        ):
            outcome = self._certify(core=True).outcome
        self.assertEqual(
            outcome.failure,
            DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED,
        )
        self.assertEqual(
            outcome.status.reason,
            UndefinedReason.LAURENT_RESOURCE_EXCEEDED,
        )
        jordan.assert_not_called()

        witness = self._jordan_witness()
        with (
            mock.patch(
                "rulespace_v3.certificate.certify_instability_growth_counter_witness",
                return_value=witness,
            ),
            mock.patch(
                "rulespace_v3.certificate.verify_instability_growth_counter_witness",
                return_value=witness,
            ),
            mock.patch(
                "rulespace_v3.certificate._build_laurent_residual",
                side_effect=AssertionError("Laurent stage ran"),
            ) as metric,
        ):
            outcome = self._certify(core=True).outcome
        self.assertEqual(
            outcome.failure,
            DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS,
        )
        self.assertEqual(outcome.status.reason, UndefinedReason.UNSTABLE)
        self.assertEqual(
            outcome.attempt_audit.instability_counter_witness,
            witness,
        )
        metric.assert_not_called()

    def test_ordinary_evidence_insufficiency_is_unresolved_not_unstable(self):
        with (
            certificate_module._scoped_replay_context(),
            mock.patch(
                "rulespace_v3.certificate.build_spectral_margin_coverage",
                side_effect=ValueError("candidate inverse unresolved"),
            ),
        ):
            outcome = self._certify(core=True).outcome
        self.assertEqual(
            outcome.failure,
            DynamicsCertificationFailure.SPECTRAL_COVERAGE_UNRESOLVED,
        )
        self.assertEqual(
            outcome.status.reason,
            UndefinedReason.STABILITY_UNRESOLVED,
        )
        self.assertIsNone(outcome.attempt_audit.instability_counter_witness)
        self.assertIsNone(outcome.certificate)

    def test_bridge_and_power_gates_return_their_frozen_typed_failures(self):
        audit = audit_full_state_bridge(
            self.transition,
            self.factory,
            self.authority,
            self.bridge_spec,
        )
        bridge_failure = dataclasses.replace(
            audit,
            normalized_max=2.0e-12,
            bridge_sha="0" * 64,
        )
        bridge_failure = dataclasses.replace(
            bridge_failure,
            bridge_sha=canonical_sha(bridge_audit_payload(bridge_failure)),
        )
        with mock.patch(
            "rulespace_v3.certificate.audit_full_state_bridge",
            return_value=bridge_failure,
        ):
            outcome = self._certify(core=True).outcome
        self.assertEqual(
            outcome.failure,
            DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED,
        )
        self.assertEqual(
            outcome.status.reason,
            UndefinedReason.DYNAMICS_BRIDGE_FAILED,
        )

        power_failure = PowerDriftAudit(
            audit_schema_version=POWER_DRIFT_AUDIT_SCHEMA_VERSION,
            normalized_metric_residual_audit_sha="a" * 64,
            macro_step=16_384,
            nonzero_delta_squaring_count=14,
            executed_squaring_count=14,
            identity_branch=False,
            method_id="t16384-directed-repeated-squaring-v1",
            delta_upper=1.0e-12,
            one_minus_delta_lower=0.9999999999999998,
            one_plus_delta_upper=1.0000000000000002,
            growth_upper=2.0e-8,
            contraction_upper=2.0e-8,
            drift_upper=2.0e-8,
            audit_sha="0" * 64,
        )
        power_failure = dataclasses.replace(
            power_failure,
            audit_sha=canonical_sha(power_drift_audit_payload(power_failure)),
        )
        with mock.patch(
            "rulespace_v3.certificate.build_power_drift_audit",
            return_value=power_failure,
        ):
            outcome = self._certify(core=True).outcome
        self.assertEqual(
            outcome.failure,
            DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED,
        )
        self.assertEqual(
            outcome.status.reason,
            UndefinedReason.STABILITY_UNRESOLVED,
        )


class DynamicsCertificateRawSchemaTests(unittest.TestCase):
    @staticmethod
    def _attempt_with_reality(reality):
        return certificate_module.DynamicsCertificationAttemptAudit(
            attempt_schema_version=(
                certificate_module.CERTIFICATION_ATTEMPT_SCHEMA_VERSION
            ),
            factory_sha="a" * 64,
            transition_sha="b" * 64,
            prestructure_authority_sha="c" * 64,
            first_failure=(DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED),
            reality=reality,
            structure_residual=None,
            metric_residual=None,
            spectral_margins=None,
            normalized_metric_residual=None,
            full_state_bridge_audit=None,
            power_drift=None,
            instability_counter_witness=None,
            attempt_sha="d" * 64,
        )

    def test_raw_attempt_rejects_unknown_in_memory_fields(self):
        attempt = certificate_module.DynamicsCertificationAttemptAudit(
            attempt_schema_version=(
                certificate_module.CERTIFICATION_ATTEMPT_SCHEMA_VERSION
            ),
            factory_sha="a" * 64,
            transition_sha=None,
            prestructure_authority_sha="b" * 64,
            first_failure=(DynamicsCertificationFailure.PRESTRUCTURE_INVALID),
            reality=None,
            structure_residual=None,
            metric_residual=None,
            spectral_margins=None,
            normalized_metric_residual=None,
            full_state_bridge_audit=None,
            power_drift=None,
            instability_counter_witness=None,
            attempt_sha="c" * 64,
        )
        object.__setattr__(
            attempt,
            "unknown_in_memory_field",
            "not-hashed",
        )
        with self.assertRaises((TypeError, ValueError)):
            certificate_module.dynamics_certification_attempt_audit_payload(attempt)

    def test_raw_attempt_rejects_unknown_nested_evidence_fields(self):
        reality = certificate_module.RealityCertificate(
            reality_schema_version="v3m0.reality.v1",
            factory_sha="a" * 64,
            transition_sha="b" * 64,
            structure_manifest_sha="c" * 64,
            factory_coefficient_count=1,
            transition_entry_count=1,
            imaginary_bit_pattern_id="all-positive-zero-f64-v1",
            implied_fourier_identity_id=("m-minus-k-equals-conj-m-k-v1"),
            reality_certificate_sha="d" * 64,
        )
        object.__setattr__(
            reality,
            "unknown_nested_field",
            "not-hashed",
        )
        attempt = self._attempt_with_reality(reality)
        with self.assertRaises((TypeError, ValueError)):
            certificate_module.dynamics_certification_attempt_audit_payload(attempt)

    def test_raw_attempt_rejects_oversized_text_before_hashing(self):
        with self.assertRaises((TypeError, ValueError)):
            certificate_module.DynamicsCertificationAttemptAudit(
                attempt_schema_version="x" * 16_385,
                factory_sha="a" * 64,
                transition_sha=None,
                prestructure_authority_sha="b" * 64,
                first_failure=(DynamicsCertificationFailure.PRESTRUCTURE_INVALID),
                reality=None,
                structure_residual=None,
                metric_residual=None,
                spectral_margins=None,
                normalized_metric_residual=None,
                full_state_bridge_audit=None,
                power_drift=None,
                instability_counter_witness=None,
                attempt_sha="c" * 64,
            )

    def test_complete_body_hash_is_streamed_under_a_hard_cap(self):
        bounded_hash = getattr(
            certificate_module,
            "_bounded_canonical_sha",
            None,
        )
        self.assertIsNotNone(bounded_hash)
        with mock.patch.object(
            certificate_module.hashlib,
            "sha256",
            side_effect=AssertionError("digest began before complete cap"),
        ) as digest:
            with self.assertRaises(ValueError):
                bounded_hash(
                    {"payload": "x" * 128},
                    maximum_bytes=32,
                )
        digest.assert_not_called()

    def test_bounded_codec_ignores_shared_json_and_hashlib_rebinding(self):
        bounded_hash = certificate_module._bounded_canonical_sha
        payload = {
            "control": "\x00μ😀",
            "values": [True, None, -0.0, 5e-324],
        }
        expected = canonical_sha(payload)
        with (
            mock.patch.object(
                certificate_module.json,
                "JSONEncoder",
                side_effect=AssertionError("shared JSON encoder was consulted"),
            ),
            mock.patch.object(
                certificate_module.hashlib,
                "sha256",
                side_effect=AssertionError("shared hashlib module was consulted"),
            ),
        ):
            self.assertEqual(bounded_hash(payload), expected)

    def test_runtime_preflight_precedes_any_factory_or_transition_stage(self):
        events = []
        core = getattr(
            certificate_module,
            "_certify_transition_dynamics_core",
            certificate_module.certify_transition_dynamics,
        )

        def verify_runtime(manifest):
            events.append("runtime")
            return manifest

        def reject_factory(factory):
            del factory
            events.append("factory")
            raise ValueError("stop after ordering probe")

        with (
            mock.patch.object(
                certificate_module,
                "verify_runtime_evidence_manifest",
                side_effect=verify_runtime,
            ),
            mock.patch.object(
                certificate_module,
                "_reverify_verified_factory",
                side_effect=reject_factory,
            ),
        ):
            with self.assertRaises((TypeError, ValueError)):
                core(
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    object(),
                )
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[:2], ["runtime", "factory"])
        self.assertTrue(all(event == "factory" for event in events[1:]))

    def test_failed_opaque_issuer_requires_live_context(self):
        attempt = certificate_module._attempt(
            factory_sha="0" * 64,
            authority_sha="0" * 64,
            transition_sha=None,
            failure=DynamicsCertificationFailure.PRESTRUCTURE_INVALID,
            reality=None,
            structure_residual=None,
            metric_residual=None,
            spectral_margins=None,
            normalized_metric_residual=None,
            full_state_bridge_audit=None,
            power_drift=None,
            instability_counter_witness=None,
        )
        outcome = certificate_module._raw_outcome(
            failure=DynamicsCertificationFailure.PRESTRUCTURE_INVALID,
            attempt=attempt,
            certificate=None,
        )
        with self.assertRaises((TypeError, ValueError)):
            certificate_module._issue_verified_dynamics_certification_outcome(
                outcome,
                None,
                object(),
                object(),
            )

    def test_public_certificate_authority_rejects_semantic_rebind(self):
        with (
            mock.patch.object(
                certificate_module,
                "_validate_certificate",
                return_value=None,
            ),
            mock.patch.object(
                certificate_module,
                "_certificate_seal",
                return_value="0" * 64,
            ),
        ):
            with self.assertRaises((TypeError, ValueError, RuntimeError)):
                verify_dynamics_certificate(
                    object(),
                    None,
                    None,
                )

    def test_public_authorities_close_the_transitive_project_function_graph(self):
        roots = (
            certificate_module.certify_transition_dynamics,
            certificate_module.verify_dynamics_certificate,
            certificate_module.verify_dynamics_certification_outcome,
            certificate_module._reverify_verified_dynamics_certificate,
            certificate_module._reverify_verified_dynamics_certification_outcome,
        )
        pending = list(roots)
        seen = set()
        while pending:
            value = pending.pop()
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            if isinstance(value, functools.partial):
                pending.extend((value.func, value.args, value.keywords))
                continue
            if inspect.isfunction(value):
                if value.__module__.startswith("rulespace_v3."):
                    self.assertIsNot(
                        value.__globals__,
                        vars(sys.modules[value.__module__]),
                    )
                    code_pending = [value.__code__]
                    names = set()
                    while code_pending:
                        code = code_pending.pop()
                        names.update(code.co_names)
                        code_pending.extend(
                            constant
                            for constant in code.co_consts
                            if isinstance(constant, types.CodeType)
                        )
                    pending.extend(
                        value.__globals__[name]
                        for name in names
                        if name in value.__globals__
                    )
                    if value.__closure__ is not None:
                        pending.extend(cell.cell_contents for cell in value.__closure__)
                continue
            if inspect.ismodule(value):
                self.assertFalse(value.__name__.startswith("rulespace_v3."))
                continue
            if isinstance(value, types.SimpleNamespace):
                pending.extend(vars(value).values())
                continue
            if type(value) in (tuple, list):
                pending.extend(value)
                continue
            if type(value) is dict:
                pending.extend(value.values())


if __name__ == "__main__":
    unittest.main()
