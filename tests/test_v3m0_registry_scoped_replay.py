from __future__ import annotations

import dataclasses
from contextvars import copy_context
import threading
import unittest

import rulespace_v3.registry as registry_module
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.replay_scope import (
    _replay_scope_statistics,
    _scoped_replay_context,
)
from tests.test_v3m0_dynamics import _quarter_turn_controls


_FACTORY_NAMESPACE = "rulespace_v3.factory.VerifiedFactory"
_PARENT_NAMESPACE = "rulespace_v3.parent_freeze.VerifiedParentFreeze"
_REGISTRY_NAMESPACE = "rulespace_v3.registry.VerifiedControlRegistry"


class _IntSubclass(int):
    pass


def _count(statistics, field: str, namespace: str) -> int:
    return dict(getattr(statistics, field)).get(namespace, 0)


def _closure_cell(function, name):
    cells = dict(zip(function.__code__.co_freevars, function.__closure__ or ()))
    return cells[name].cell_contents


class RegistryScopedReplayCardinalityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.source_registry = registry_module.build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        cls.raw_registry = cls.source_registry.registry

    def _counted_authority(self):
        seal_calls = []

        def counted_seal(raw, controls, parent):
            seal_calls.append(raw)
            return registry_module._registry_seal(raw, controls, parent)

        issue, reverify = registry_module._make_registry_authority(
            seal_builder=counted_seal,
        )
        wrapper = issue(self.raw_registry, self.controls, self.parent)
        seal_calls.clear()
        return seal_calls, wrapper, reverify

    def test_same_scope_runs_full_registry_seal_once(self):
        seal_calls, wrapper, reverify = self._counted_authority()

        with _scoped_replay_context():
            first = reverify(wrapper)
            second = reverify(wrapper)
            statistics = _replay_scope_statistics()

        self.assertEqual(first, second)
        self.assertEqual(len(seal_calls), 1)
        self.assertEqual(_count(statistics, "full_records", _REGISTRY_NAMESPACE), 1)
        self.assertEqual(_count(statistics, "hits", _REGISTRY_NAMESPACE), 1)

    def test_same_scope_hit_replays_each_factory_and_parent_once(self):
        _seal_calls, wrapper, reverify = self._counted_authority()

        with _scoped_replay_context():
            reverify(wrapper)
            before = _replay_scope_statistics()
            reverify(wrapper)
            after = _replay_scope_statistics()

        self.assertEqual(
            _count(after, "hits", _FACTORY_NAMESPACE)
            - _count(before, "hits", _FACTORY_NAMESPACE),
            3,
        )
        self.assertEqual(
            _count(after, "hits", _PARENT_NAMESPACE)
            - _count(before, "hits", _PARENT_NAMESPACE),
            1,
        )

    def test_fresh_scopes_do_not_share_registry_proofs(self):
        seal_calls, wrapper, reverify = self._counted_authority()

        observed = []
        for _index in range(2):
            with _scoped_replay_context():
                reverify(wrapper)
                reverify(wrapper)
                observed.append(_replay_scope_statistics())

        self.assertEqual(len(seal_calls), 2)
        for statistics in observed:
            self.assertEqual(
                _count(statistics, "full_records", _REGISTRY_NAMESPACE),
                1,
            )
            self.assertEqual(_count(statistics, "hits", _REGISTRY_NAMESPACE), 1)

    def test_issue_records_only_a_successful_full_proof(self):
        seal_calls = []

        def counted_seal(raw, controls, parent):
            seal_calls.append(raw)
            return registry_module._registry_seal(raw, controls, parent)

        issue, reverify = registry_module._make_registry_authority(
            seal_builder=counted_seal,
        )
        with _scoped_replay_context():
            wrapper = issue(self.raw_registry, self.controls, self.parent)
            reverify(wrapper)
            statistics = _replay_scope_statistics()

        self.assertEqual(len(seal_calls), 1)
        self.assertEqual(_count(statistics, "full_records", _REGISTRY_NAMESPACE), 1)
        self.assertEqual(_count(statistics, "hits", _REGISTRY_NAMESPACE), 1)

        def reject_snapshots(_controls, _parent):
            raise ValueError("dependency snapshots rejected")

        rejected_issue, _rejected_reverify = (
            registry_module._make_registry_authority(
                dependency_snapshot_builder=reject_snapshots,
            )
        )
        with _scoped_replay_context():
            with self.assertRaisesRegex(ValueError, "snapshots rejected"):
                rejected_issue(self.raw_registry, self.controls, self.parent)
            rejected_statistics = _replay_scope_statistics()

        self.assertEqual(
            _count(rejected_statistics, "full_records", _REGISTRY_NAMESPACE),
            0,
        )

    def test_failed_weakref_registration_does_not_record_proof(self):
        def reject_weakref(_wrapper, _callback):
            raise RuntimeError("weakref registration rejected")

        issue, _reverify = registry_module._make_registry_authority(
            weak_reference=reject_weakref,
        )
        with _scoped_replay_context():
            with self.assertRaisesRegex(RuntimeError, "weakref registration rejected"):
                issue(self.raw_registry, self.controls, self.parent)
            statistics = _replay_scope_statistics()

        self.assertEqual(_count(statistics, "full_records", _REGISTRY_NAMESPACE), 0)

    def test_copied_scope_cannot_cross_thread_owner(self):
        _seal_calls, wrapper, reverify = self._counted_authority()
        observed = []

        with _scoped_replay_context():
            reverify(wrapper)
            copied = copy_context()

            def run():
                try:
                    copied.run(reverify, wrapper)
                except BaseException as exc:  # pragma: no branch - test capture
                    observed.append(exc)

            thread = threading.Thread(target=run)
            thread.start()
            thread.join()

        self.assertEqual(len(observed), 1)
        self.assertIs(type(observed[0]), RuntimeError)
        self.assertIn("another owner thread", str(observed[0]))


class RegistryScopedReplayGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        source = registry_module.build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        cls.raw_registry = source.registry
        cls.alternate_controls = _quarter_turn_controls()

    def _issue(self):
        issue, reverify = registry_module._make_registry_authority()
        return (
            issue(self.raw_registry, self.controls, self.parent),
            reverify,
        )

    def test_preissue_bundle_schema_and_unknown_field_are_rejected(self):
        control = self.controls[0]
        original_schema = control.control_schema_version
        try:
            object.__setattr__(
                control,
                "control_schema_version",
                "v3m0.synthetic-control-bundle.forged",
            )
            with self.assertRaises((TypeError, ValueError)):
                registry_module.build_closed_control_registry(
                    self.controls,
                    self.parent,
                )
        finally:
            object.__setattr__(
                control,
                "control_schema_version",
                original_schema,
            )

        try:
            object.__setattr__(control, "caller_unknown", "forbidden")
            with self.assertRaises((TypeError, ValueError)):
                registry_module.build_closed_control_registry(
                    self.controls,
                    self.parent,
                )
        finally:
            object.__delattr__(control, "caller_unknown")

    def test_views_and_property_return_isolated_registry_clones(self):
        wrapper, reverify = self._issue()
        first = reverify(wrapper)
        second = reverify(wrapper)
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedControlRegistry__registry",
        )
        self.assertIsNot(first.registry, second.registry)
        self.assertIsNot(first.registry, raw)
        original_sha = first.registry.registry_sha
        object.__setattr__(first.registry, "registry_sha", "f" * 64)
        third = reverify(wrapper)
        self.assertEqual(third.registry.registry_sha, original_sha)

        public_wrapper = registry_module.build_closed_control_registry(
            self.controls,
            self.parent,
        )
        public_first = public_wrapper.registry
        public_second = public_wrapper.registry
        public_raw = object.__getattribute__(
            public_wrapper,
            "_VerifiedControlRegistry__registry",
        )
        self.assertIsNot(public_first, public_second)
        self.assertIsNot(public_first, public_raw)
        object.__setattr__(public_first, "registry_sha", "e" * 64)
        self.assertEqual(public_wrapper.registry.registry_sha, original_sha)

    def test_coordinated_live_and_snapshot_schema_tamper_is_rejected(self):
        wrapper, reverify = self._issue()
        live = _closure_cell(reverify, "live")
        authority = live[id(wrapper)][1]
        control = self.controls[0]
        snapshot = authority.control_snapshots[0]
        original_control_schema = control.control_schema_version
        original_snapshot_schema = snapshot.control_schema_version
        original_fingerprint = authority.replay_fingerprint

        with _scoped_replay_context():
            reverify(wrapper)
            object.__setattr__(control, "control_schema_version", "forged-schema")
            object.__setattr__(snapshot, "control_schema_version", "forged-schema")
            object.__setattr__(
                authority,
                "replay_fingerprint",
                registry_module._registry_replay_fingerprint(
                    authority.registry_snapshot,
                    authority.control_snapshots,
                    authority.parent,
                    authority.parent_snapshot,
                    authority.seal,
                ),
            )
            try:
                with self.assertRaises((TypeError, ValueError)):
                    reverify(wrapper)
            finally:
                object.__setattr__(
                    control,
                    "control_schema_version",
                    original_control_schema,
                )
                object.__setattr__(
                    snapshot,
                    "control_schema_version",
                    original_snapshot_schema,
                )
                object.__setattr__(
                    authority,
                    "replay_fingerprint",
                    original_fingerprint,
                )

    def _assert_warm_hit_rejects(self, mutate, restore):
        wrapper, reverify = self._issue()
        try:
            with _scoped_replay_context():
                reverify(wrapper)
                hits_before = _count(
                    _replay_scope_statistics(),
                    "hits",
                    _REGISTRY_NAMESPACE,
                )
                mutate(wrapper)
                with self.assertRaises((TypeError, ValueError)):
                    reverify(wrapper)
                hits_after = _count(
                    _replay_scope_statistics(),
                    "hits",
                    _REGISTRY_NAMESPACE,
                )
        finally:
            restore(wrapper)
        self.assertEqual(hits_after, hits_before)

    def test_raw_registry_body_and_identity_replacement_are_rejected(self):
        slot = "_VerifiedControlRegistry__registry"
        for label, replacement in (
            (
                "body",
                lambda raw: dataclasses.replace(raw, registry_sha="f" * 64),
            ),
            (
                "identity",
                lambda raw: dataclasses.replace(raw),
            ),
        ):
            with self.subTest(label=label):
                original = []

                def mutate(wrapper):
                    raw = object.__getattribute__(wrapper, slot)
                    original.append(raw)
                    object.__setattr__(wrapper, slot, replacement(raw))

                def restore(wrapper):
                    if original:
                        object.__setattr__(wrapper, slot, original[0])

                self._assert_warm_hit_rejects(mutate, restore)

    def test_control_target_trace_source_and_rank_replacement_are_rejected(self):
        control = self.controls[0]
        attacks = (
            ("target", "target", lambda value: dataclasses.replace(value)),
            (
                "trace",
                "construction_trace",
                lambda value: dataclasses.replace(value),
            ),
            (
                "source",
                "source_basis",
                lambda value: dataclasses.replace(value),
            ),
            ("rank", "expected_actual_rank", lambda value: value + 1),
            (
                "rank-type",
                "expected_actual_rank",
                lambda value: _IntSubclass(value),
            ),
        )
        for label, field, replacement in attacks:
            with self.subTest(label=label):
                original = getattr(control, field)

                def mutate(_wrapper, field=field, replacement=replacement):
                    object.__setattr__(
                        control,
                        field,
                        replacement(original),
                    )

                def restore(_wrapper, field=field):
                    object.__setattr__(control, field, original)

                self._assert_warm_hit_rejects(mutate, restore)

    def test_factory_private_body_mutation_is_rejected(self):
        factory = self.controls[0].factory
        raw_factory = object.__getattribute__(factory, "_VerifiedFactory__factory")
        primitive = raw_factory.primitives[0]
        original = primitive.coefficient_wire

        def mutate(_wrapper):
            object.__setattr__(
                primitive,
                "coefficient_wire",
                (original[0] + 1.0, original[1]),
            )

        def restore(_wrapper):
            object.__setattr__(primitive, "coefficient_wire", original)

        self._assert_warm_hit_rejects(mutate, restore)

    def test_equivalent_factory_identity_replacement_is_rejected(self):
        control = self.controls[0]
        original = control.factory
        replacement = self.alternate_controls[0].factory
        self.assertEqual(original.factory, replacement.factory)
        self.assertIsNot(original, replacement)

        def mutate(_wrapper):
            object.__setattr__(control, "factory", replacement)

        def restore(_wrapper):
            object.__setattr__(control, "factory", original)

        self._assert_warm_hit_rejects(mutate, restore)

    def test_parent_private_manifest_mutation_is_rejected(self):
        manifest = object.__getattribute__(
            self.parent,
            "_VerifiedParentFreeze__manifest",
        )
        original = manifest.parent_freeze_sha

        def mutate(_wrapper):
            object.__setattr__(manifest, "parent_freeze_sha", "f" * 64)

        def restore(_wrapper):
            object.__setattr__(manifest, "parent_freeze_sha", original)

        self._assert_warm_hit_rejects(mutate, restore)


if __name__ == "__main__":
    unittest.main()
