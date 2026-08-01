from __future__ import annotations

from dataclasses import dataclass
import unittest
from unittest import mock

import rulespace_v3.certificate as certificate_module
import rulespace_v3.dynamics as dynamics_module
import rulespace_v3.factory as factory_module
import rulespace_v3.prestructure as prestructure_module
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.registry import build_closed_control_registry
from rulespace_v3.replay_scope import (
    _replay_scope_statistics,
    _scoped_replay_context,
)
from rulespace_v3.runtime import (
    RUNTIME_EVALUATOR_ID,
    RUNTIME_SCHEMA_VERSION,
    RuntimeEvidenceManifest,
)
from tests.test_v3m0_dynamics import _quarter_turn_controls


_SEAL = "a" * 64


@dataclass(frozen=True)
class _Leaf:
    value: int


@dataclass(frozen=True)
class _TransitionBinding:
    factory_sha: str
    factory_role: str
    prestructure_authority_sha: str


@dataclass(frozen=True)
class _CertificateDependencyBody:
    leaf: _Leaf
    prestructure_authority: object
    transition: _TransitionBinding


@dataclass(frozen=True)
class _FrozenSlotsWire:
    __slots__ = ("value",)

    value: object


@dataclass(frozen=True)
class _AliasedWire:
    left: _FrozenSlotsWire
    right: _FrozenSlotsWire


class _IntSubclass(int):
    pass


class ExactWireSnapshotTests(unittest.TestCase):
    def test_frozen_slots_runtime_manifest_is_cloned_with_exact_type(self):
        manifest = RuntimeEvidenceManifest(
            runtime_schema_version=RUNTIME_SCHEMA_VERSION,
            evaluator_id=RUNTIME_EVALUATOR_ID,
            source_closure=(("rulespace_v3/runtime.py", "a" * 64),),
            python_version="3.9.0",
            numpy_version="2.0.0",
            scipy_version="1.13.0",
            blas_config_sha="b" * 64,
            lapack_config_sha="c" * 64,
            platform_id="test-platform",
            runtime_manifest_sha="d" * 64,
        )
        clone = certificate_module._snapshot_exact_wire(manifest)
        self.assertIs(type(clone), RuntimeEvidenceManifest)
        self.assertEqual(clone, manifest)
        self.assertIsNot(clone, manifest)

    def test_alias_is_preserved_but_snapshot_is_independent(self):
        shared = _FrozenSlotsWire(1)
        wire = _AliasedWire(shared, shared)
        clone = certificate_module._snapshot_exact_wire(wire)
        self.assertIs(type(clone), _AliasedWire)
        self.assertIs(clone.left, clone.right)
        self.assertIsNot(clone.left, shared)
        object.__setattr__(shared, "value", 2)
        self.assertEqual(clone.left.value, 1)

    def test_cycle_unknown_object_and_scalar_subclass_are_rejected(self):
        cycle = _FrozenSlotsWire(None)
        object.__setattr__(cycle, "value", cycle)
        with self.assertRaisesRegex(ValueError, "acyclic"):
            certificate_module._snapshot_exact_wire(cycle)
        with self.assertRaisesRegex(TypeError, "non-wire"):
            certificate_module._snapshot_exact_wire(object())
        with self.assertRaisesRegex(TypeError, "non-wire"):
            certificate_module._snapshot_exact_wire(_IntSubclass(1))


class CertificateScopedReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(cls.controls, cls.parent)
        cls.construction = matched_ablation(cls.controls[0].factory)
        assert cls.construction.pair is not None
        cls.factory = cls.construction.pair.actual
        cls.authority = (
            prestructure_module.issue_synthetic_prestructure_authority(
                cls.parent,
                cls.registry,
                "full",
                cls.construction,
                "actual",
            )
        )

    def _issue(self) -> tuple[object, _CertificateDependencyBody]:
        body = _CertificateDependencyBody(
            leaf=_Leaf(1),
            prestructure_authority=certificate_module._snapshot_exact_wire(
                self.authority.authority
            ),
            transition=_TransitionBinding(
                factory_sha=self.factory.factory.factory_sha,
                factory_role="actual",
                prestructure_authority_sha=(
                    self.authority.authority.authority_sha
                ),
            ),
        )
        with (
            mock.patch.object(certificate_module, "_validate_certificate"),
            mock.patch.object(
                certificate_module,
                "_certificate_seal",
                return_value=_SEAL,
            ),
        ):
            wrapper = certificate_module._issue_verified_dynamics_certificate(
                certificate_module._VALIDATED_TOKEN,
                body,
                self.factory,
                self.authority,
            )
        return wrapper, body

    def test_validated_issuance_records_proof_for_immediate_reverify(self):
        body = _CertificateDependencyBody(
            leaf=_Leaf(1),
            prestructure_authority=certificate_module._snapshot_exact_wire(
                self.authority.authority
            ),
            transition=_TransitionBinding(
                factory_sha=self.factory.factory.factory_sha,
                factory_role="actual",
                prestructure_authority_sha=(
                    self.authority.authority.authority_sha
                ),
            ),
        )
        with (
            mock.patch.object(
                certificate_module,
                "_validate_certificate",
            ) as full_validate,
            mock.patch.object(
                certificate_module,
                "_certificate_seal",
                return_value=_SEAL,
            ),
            _scoped_replay_context(),
        ):
            wrapper = certificate_module._issue_verified_dynamics_certificate(
                certificate_module._VALIDATED_TOKEN,
                body,
                self.factory,
                self.authority,
            )
            certificate_module._reverify_verified_dynamics_certificate_core(
                wrapper
            )
            statistics = _replay_scope_statistics()

        full_validate.assert_called_once()
        self.assertEqual(
            dict(statistics.full_records)[
                "rulespace_v3.certificate.VerifiedDynamicsCertificate"
            ],
            1,
        )
        self.assertEqual(
            dict(statistics.hits)[
                "rulespace_v3.certificate.VerifiedDynamicsCertificate"
            ],
            1,
        )

    def test_same_scope_runs_full_certificate_validation_once(self):
        wrapper, _body = self._issue()
        with (
            mock.patch.object(
                certificate_module,
                "_validate_certificate",
            ) as full_validate,
            mock.patch.object(
                certificate_module,
                "_certificate_seal",
                return_value=_SEAL,
            ),
            _scoped_replay_context(),
        ):
            first = certificate_module._reverify_verified_dynamics_certificate_core(
                wrapper
            )
            second = certificate_module._reverify_verified_dynamics_certificate_core(
                wrapper
            )
            statistics = _replay_scope_statistics()

        self.assertEqual(first, second)
        full_validate.assert_called_once()
        self.assertEqual(
            dict(statistics.full_records)[
                "rulespace_v3.certificate.VerifiedDynamicsCertificate"
            ],
            1,
        )
        self.assertEqual(
            dict(statistics.hits)[
                "rulespace_v3.certificate.VerifiedDynamicsCertificate"
            ],
            1,
        )

    def test_in_place_deep_mutation_is_rejected_on_certificate_hit(self):
        wrapper, body = self._issue()
        with (
            mock.patch.object(
                certificate_module,
                "_validate_certificate",
            ),
            mock.patch.object(
                certificate_module,
                "_certificate_seal",
                return_value=_SEAL,
            ),
            _scoped_replay_context(),
        ):
            certificate_module._reverify_verified_dynamics_certificate_core(
                wrapper
            )
            object.__setattr__(body.leaf, "value", 2)
            with self.assertRaises(ValueError):
                certificate_module._reverify_verified_dynamics_certificate_core(
                    wrapper
                )


class AuthorityScopedReplayIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(cls.controls, cls.parent)
        cls.construction = matched_ablation(cls.controls[0].factory)
        assert cls.construction.pair is not None
        cls.factory = cls.construction.pair.actual
        cls.authority = (
            prestructure_module.issue_synthetic_prestructure_authority(
                cls.parent,
                cls.registry,
                "full",
                cls.construction,
                "actual",
            )
        )
        cls.transition = dynamics_module.measure_transition(
            cls.factory,
            cls.authority,
        )

    def _assert_hit_revalidates_mutated_dependency(
        self,
        *,
        namespace,
        reverify,
        wrapper,
        target,
        field,
        changed,
    ):
        original = getattr(target, field)
        try:
            with _scoped_replay_context():
                reverify(wrapper)
                hits_before = dict(_replay_scope_statistics().hits).get(
                    namespace,
                    0,
                )
                object.__setattr__(target, field, changed)
                with self.assertRaises((TypeError, ValueError)):
                    reverify(wrapper)
                hits_after = dict(_replay_scope_statistics().hits).get(
                    namespace,
                    0,
                )
        finally:
            object.__setattr__(target, field, original)
        self.assertEqual(hits_after, hits_before)

    def test_factory_prestructure_and_transition_replay_once_per_scope(self):
        with _scoped_replay_context():
            for _index in range(2):
                factory_module._reverify_verified_factory(self.factory)
                prestructure_module._reverify_verified_prestructure_authority(
                    self.authority
                )
                dynamics_module._reverify_verified_transition(self.transition)
            statistics = _replay_scope_statistics()

        expected = (
            "rulespace_v3.dynamics.VerifiedTransition",
            "rulespace_v3.factory.VerifiedFactory",
            "rulespace_v3.parent_freeze.VerifiedParentFreeze",
            "rulespace_v3.prestructure.VerifiedPrestructureAuthority",
            "rulespace_v3.registry.VerifiedControlRegistry",
        )
        self.assertEqual(
            tuple(namespace for namespace, count in statistics.full_records if count),
            expected,
        )
        self.assertEqual(
            tuple(namespace for namespace, count in statistics.hits if count),
            expected,
        )
        full_records = dict(statistics.full_records)
        misses = dict(statistics.misses)
        hits = dict(statistics.hits)
        self.assertEqual(full_records, misses)
        self.assertEqual(
            full_records["rulespace_v3.dynamics.VerifiedTransition"],
            1,
        )
        self.assertEqual(
            full_records[
                "rulespace_v3.prestructure.VerifiedPrestructureAuthority"
            ],
            1,
        )
        self.assertGreaterEqual(
            full_records["rulespace_v3.factory.VerifiedFactory"],
            1,
        )
        self.assertTrue(all(count >= 1 for count in hits.values()))

    def test_in_place_prestructure_mutation_is_rejected_on_hit(self):
        body = self.authority.authority
        snapshot = body.ablation_pair_snapshot
        original = snapshot.snapshot_sha
        try:
            with _scoped_replay_context():
                prestructure_module._reverify_verified_prestructure_authority(
                    self.authority
                )
                object.__setattr__(snapshot, "snapshot_sha", "f" * 64)
                with self.assertRaises(ValueError):
                    prestructure_module._reverify_verified_prestructure_authority(
                        self.authority
                    )
        finally:
            object.__setattr__(snapshot, "snapshot_sha", original)

    def test_in_place_factory_mutation_is_rejected_on_hit(self):
        primitive = self.factory.factory.primitives[0]
        original = primitive.coefficient_wire
        changed = (original[0] + 1.0, original[1])
        try:
            with _scoped_replay_context():
                factory_module._reverify_verified_factory(self.factory)
                object.__setattr__(primitive, "coefficient_wire", changed)
                with self.assertRaises(ValueError):
                    factory_module._reverify_verified_factory(self.factory)
        finally:
            object.__setattr__(primitive, "coefficient_wire", original)

    def test_in_place_transition_mutation_is_rejected_on_hit(self):
        kernel = self.transition.transition.kernel
        original = kernel.values_wire
        changed = ((original[0][0] + 1.0, original[0][1]),) + original[1:]
        try:
            with _scoped_replay_context():
                dynamics_module._reverify_verified_transition(self.transition)
                object.__setattr__(kernel, "values_wire", changed)
                with self.assertRaises(ValueError):
                    dynamics_module._reverify_verified_transition(
                        self.transition
                    )
        finally:
            object.__setattr__(kernel, "values_wire", original)

    def test_transition_hit_revalidates_factory_and_prestructure_dependencies(self):
        namespace = "rulespace_v3.dynamics.VerifiedTransition"
        primitive = self.factory.factory.primitives[0]
        prestructure_snapshot = self.authority.authority.ablation_pair_snapshot
        cases = (
            (
                "factory",
                primitive,
                "coefficient_wire",
                (
                    primitive.coefficient_wire[0] + 1.0,
                    primitive.coefficient_wire[1],
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
            dynamics_module._reverify_verified_transition(self.transition)
            for label, target, field, changed in cases:
                with self.subTest(dependency=label):
                    original = getattr(target, field)
                    try:
                        hits_before = dict(_replay_scope_statistics().hits).get(
                            namespace,
                            0,
                        )
                        object.__setattr__(target, field, changed)
                        with self.assertRaises((TypeError, ValueError)):
                            dynamics_module._reverify_verified_transition(
                                self.transition
                            )
                    finally:
                        object.__setattr__(target, field, original)
                    hits_after = dict(_replay_scope_statistics().hits).get(
                        namespace,
                        0,
                    )
                    self.assertEqual(hits_after, hits_before)

    def test_prestructure_registry_hit_revalidates_all_direct_dependencies(self):
        namespace = (
            "rulespace_v3.prestructure.VerifiedPrestructureAuthority"
        )
        parent_manifest = object.__getattribute__(
            self.parent,
            "_VerifiedParentFreeze__manifest",
        )
        registry_body = object.__getattribute__(
            self.registry,
            "_VerifiedControlRegistry__registry",
        )
        assert self.construction.pair is not None
        construction_manifest = self.construction.pair.manifest
        factory_primitive = self.factory.factory.primitives[0]
        cases = (
            (
                "parent",
                parent_manifest,
                "parent_freeze_sha",
                "f" * 64,
            ),
            (
                "registry",
                registry_body,
                "registry_sha",
                "f" * 64,
            ),
            (
                "construction-outcome",
                construction_manifest,
                "manifest_sha",
                "f" * 64,
            ),
            (
                "selected-factory",
                factory_primitive,
                "coefficient_wire",
                (
                    factory_primitive.coefficient_wire[0] + 1.0,
                    factory_primitive.coefficient_wire[1],
                ),
            ),
        )
        for label, target, field, changed in cases:
            with self.subTest(dependency=label):
                self._assert_hit_revalidates_mutated_dependency(
                    namespace=namespace,
                    reverify=(
                        prestructure_module._reverify_verified_prestructure_authority
                    ),
                    wrapper=self.authority,
                    target=target,
                    field=field,
                    changed=changed,
                )

    def test_failure_outcome_hit_revalidates_factory_and_prestructure(self):
        failure = certificate_module.DynamicsCertificationFailure.PRESTRUCTURE_INVALID
        attempt = certificate_module._attempt(
            factory_sha=self.factory.factory.factory_sha,
            authority_sha=self.authority.authority.authority_sha,
            transition_sha=None,
            failure=failure,
            reality=None,
            structure_residual=None,
            metric_residual=None,
            spectral_margins=None,
            normalized_metric_residual=None,
            full_state_bridge_audit=None,
            power_drift=None,
            instability_counter_witness=None,
        )
        raw = certificate_module._raw_outcome(
            failure=failure,
            attempt=attempt,
            certificate=None,
        )
        namespace = (
            "rulespace_v3.certificate."
            "VerifiedDynamicsCertificationOutcome"
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
        with mock.patch.object(
            certificate_module,
            "_verify_failure_evidence",
        ):
            outcome = (
                certificate_module._issue_verified_dynamics_certification_outcome(
                    raw,
                    None,
                    self.factory,
                    self.authority,
                )
            )
            with _scoped_replay_context():
                certificate_module._reverify_verified_dynamics_certification_outcome_core(
                    outcome
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
                                certificate_module._reverify_verified_dynamics_certification_outcome_core(
                                    outcome
                                )
                        finally:
                            object.__setattr__(target, field, original)
                        hits_after = dict(_replay_scope_statistics().hits).get(
                            namespace,
                            0,
                        )
                        self.assertEqual(hits_after, hits_before)

    def test_certificate_hit_revalidates_actual_factory_and_prestructure(self):
        body = _CertificateDependencyBody(
            leaf=_Leaf(1),
            prestructure_authority=certificate_module._snapshot_exact_wire(
                self.authority.authority
            ),
            transition=_TransitionBinding(
                factory_sha=self.factory.factory.factory_sha,
                factory_role="actual",
                prestructure_authority_sha=(
                    self.authority.authority.authority_sha
                ),
            ),
        )

        def validate(_body, factory, authority):
            factory_module._reverify_verified_factory(factory)
            prestructure_module._reverify_verified_prestructure_authority(
                authority
            )

        with (
            mock.patch.object(
                certificate_module,
                "_validate_certificate",
                side_effect=validate,
            ),
            mock.patch.object(
                certificate_module,
                "_certificate_seal",
                return_value=_SEAL,
            ),
        ):
            certificate = (
                certificate_module._issue_verified_dynamics_certificate(
                    certificate_module._VALIDATED_TOKEN,
                    body,
                    self.factory,
                    self.authority,
                )
            )
            namespace = (
                "rulespace_v3.certificate.VerifiedDynamicsCertificate"
            )
            factory_primitive = self.factory.factory.primitives[0]
            prestructure_snapshot = (
                self.authority.authority.ablation_pair_snapshot
            )
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


if __name__ == "__main__":
    unittest.main()
