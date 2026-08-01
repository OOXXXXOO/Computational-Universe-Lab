from __future__ import annotations

import dataclasses
import dis
import unittest
from unittest import mock

import rulespace_v3.parent_freeze as parent_freeze
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.parent_freeze import (
    _reverify_verified_parent_freeze,
    issue_v3m0_parent_freeze,
    parent_freeze_manifest_payload,
    synthetic_application_operation_payload,
    synthetic_control_application_spec_payload,
)
from rulespace_v3.replay_scope import (
    _replay_scope_statistics,
    _scoped_replay_context,
)


_NAMESPACE = "rulespace_v3.parent_freeze.VerifiedParentFreeze"
_MANIFEST_SLOT = "_VerifiedParentFreeze__manifest"
_TOKEN_SLOT = "_VerifiedParentFreeze__token"
_SEAL_SLOT = "_VerifiedParentFreeze__seal"


class _TupleSubclass(tuple):
    pass


class _ListSubclass(list):
    pass


class _DictSubclass(dict):
    pass


class _TextSubclass(str):
    pass


def _raw_manifest(wrapper):
    return object.__getattribute__(wrapper, _MANIFEST_SLOT)


def _closure_cell(function, name):
    cells = dict(zip(function.__code__.co_freevars, function.__closure__ or ()))
    return cells[name].cell_contents


def _live_registry(function=_reverify_verified_parent_freeze):
    return _closure_cell(function, "registry")


def _resigned_deep_change(manifest):
    spec = manifest.synthetic_control_application_specs[0]
    operation = spec.operations[0]
    changed_operation = dataclasses.replace(
        operation,
        operation_instance_id=f"{operation.operation_instance_id}.tampered",
    )
    changed_operation = dataclasses.replace(
        changed_operation,
        operation_sha=canonical_sha(
            synthetic_application_operation_payload(changed_operation)
        ),
    )
    changed_spec = dataclasses.replace(
        spec,
        operations=(changed_operation, *spec.operations[1:]),
    )
    changed_spec = dataclasses.replace(
        changed_spec,
        application_spec_sha=canonical_sha(
            synthetic_control_application_spec_payload(changed_spec)
        ),
    )
    changed_manifest = dataclasses.replace(
        manifest,
        synthetic_control_application_specs=(
            changed_spec,
            *manifest.synthetic_control_application_specs[1:],
        ),
    )
    return dataclasses.replace(
        changed_manifest,
        parent_freeze_sha=canonical_sha(
            parent_freeze_manifest_payload(changed_manifest)
        ),
    )


class ParentScopedReplayCardinalityTests(unittest.TestCase):
    def _counted_registry(self):
        calls = []

        def validator(manifest, *, require_closed_body):
            calls.append(manifest)
            return parent_freeze._validate_parent_freeze_manifest(
                manifest,
                require_closed_body=require_closed_body,
            )

        issue, reverify = parent_freeze._make_parent_freeze_registry(
            manifest_validator=validator,
        )
        return calls, issue, reverify

    def test_issue_records_full_proof_for_immediate_same_scope_hit(self):
        calls, issue, reverify = self._counted_registry()
        raw = parent_freeze._clone_parent_wire(
            parent_freeze._CLOSED_PARENT_FREEZE_SNAPSHOT
        )

        with _scoped_replay_context():
            wrapper = issue(raw)
            observed = reverify(wrapper)
            statistics = _replay_scope_statistics()

        self.assertEqual(observed, raw)
        self.assertEqual(len(calls), 1)
        self.assertEqual(dict(statistics.full_records)[_NAMESPACE], 1)
        self.assertEqual(dict(statistics.hits)[_NAMESPACE], 1)
        self.assertNotIn(_NAMESPACE, dict(statistics.misses))

    def test_same_scope_replay_has_one_full_miss_then_one_hit(self):
        calls, issue, reverify = self._counted_registry()
        wrapper = issue(parent_freeze._CLOSED_PARENT_FREEZE_SNAPSHOT)
        calls.clear()

        with _scoped_replay_context():
            first = reverify(wrapper)
            second = reverify(wrapper)
            statistics = _replay_scope_statistics()

        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertEqual(len(calls), 1)
        self.assertEqual(dict(statistics.misses)[_NAMESPACE], 1)
        self.assertEqual(dict(statistics.full_records)[_NAMESPACE], 1)
        self.assertEqual(dict(statistics.hits)[_NAMESPACE], 1)

    def test_fresh_scopes_do_not_share_parent_proofs(self):
        calls, issue, reverify = self._counted_registry()
        wrapper = issue(parent_freeze._CLOSED_PARENT_FREEZE_SNAPSHOT)
        calls.clear()

        observed_statistics = []
        for _index in range(2):
            with _scoped_replay_context():
                reverify(wrapper)
                reverify(wrapper)
                observed_statistics.append(_replay_scope_statistics())

        self.assertEqual(len(calls), 2)
        for statistics in observed_statistics:
            self.assertEqual(dict(statistics.misses)[_NAMESPACE], 1)
            self.assertEqual(dict(statistics.full_records)[_NAMESPACE], 1)
            self.assertEqual(dict(statistics.hits)[_NAMESPACE], 1)

    def test_failed_issue_does_not_record_a_replay_proof(self):
        def rejecting_weakref(_wrapper, _callback):
            raise RuntimeError("registration rejected")

        issue, _reverify = parent_freeze._make_parent_freeze_registry(
            weak_reference=rejecting_weakref,
        )
        with _scoped_replay_context():
            with self.assertRaisesRegex(RuntimeError, "registration rejected"):
                issue(parent_freeze._CLOSED_PARENT_FREEZE_SNAPSHOT)
            statistics = _replay_scope_statistics()

        self.assertEqual(statistics.entry_count, 0)
        self.assertEqual(dict(statistics.full_records), {})

    def test_failed_full_miss_does_not_record_a_replay_proof(self):
        calls = []

        def validator(manifest, *, require_closed_body):
            calls.append(manifest)
            if len(calls) > 1:
                raise ValueError("full replay rejected")
            return parent_freeze._validate_parent_freeze_manifest(
                manifest,
                require_closed_body=require_closed_body,
            )

        issue, reverify = parent_freeze._make_parent_freeze_registry(
            manifest_validator=validator,
        )
        wrapper = issue(parent_freeze._CLOSED_PARENT_FREEZE_SNAPSHOT)
        with _scoped_replay_context():
            with self.assertRaisesRegex(ValueError, "full replay rejected"):
                reverify(wrapper)
            statistics = _replay_scope_statistics()

        self.assertEqual(statistics.entry_count, 0)
        self.assertEqual(dict(statistics.misses)[_NAMESPACE], 1)
        self.assertEqual(dict(statistics.full_records), {})


class ParentScopedReplayExactGuardTests(unittest.TestCase):
    def _record(self):
        wrapper = issue_v3m0_parent_freeze()
        context = _scoped_replay_context()
        context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        _reverify_verified_parent_freeze(wrapper)
        return wrapper

    def test_nested_unknown_field_is_rejected_on_hit(self):
        wrapper = self._record()
        basis_protocol = (
            _raw_manifest(wrapper)
            .synthetic_control_application_specs[0]
            .basis_protocol
        )
        object.__setattr__(basis_protocol, "caller_unknown", "forbidden")

        with self.assertRaisesRegex((TypeError, ValueError), "field|wire|exact"):
            _reverify_verified_parent_freeze(wrapper)

    def test_container_and_scalar_subclasses_are_rejected_on_hit(self):
        mutations = (
            (
                "tuple",
                lambda raw: object.__setattr__(
                    raw,
                    "source_closure",
                    _TupleSubclass(raw.source_closure),
                ),
            ),
            (
                "list",
                lambda raw: object.__setattr__(
                    raw,
                    "source_closure",
                    _ListSubclass(raw.source_closure),
                ),
            ),
            (
                "dict",
                lambda raw: object.__setattr__(
                    raw,
                    "source_closure",
                    _DictSubclass(enumerate(raw.source_closure)),
                ),
            ),
            (
                "scalar",
                lambda raw: object.__setattr__(
                    raw,
                    "program_id",
                    _TextSubclass(raw.program_id),
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                wrapper = issue_v3m0_parent_freeze()
                with _scoped_replay_context():
                    _reverify_verified_parent_freeze(wrapper)
                    mutate(_raw_manifest(wrapper))
                    with self.assertRaisesRegex(
                        (TypeError, ValueError),
                        "wire|type|snapshot|mismatch",
                    ):
                        _reverify_verified_parent_freeze(wrapper)

    def test_deep_in_place_mutation_is_rejected_on_hit(self):
        wrapper = self._record()
        raw = _raw_manifest(wrapper)
        operation = raw.synthetic_control_application_specs[0].operations[0]
        object.__setattr__(
            operation,
            "operation_instance_id",
            f"{operation.operation_instance_id}.tampered",
        )

        with self.assertRaises(ValueError):
            _reverify_verified_parent_freeze(wrapper)

    def test_fully_resigned_deep_body_change_is_rejected_on_hit(self):
        wrapper = self._record()
        raw = _raw_manifest(wrapper)
        resigned = _resigned_deep_change(raw)
        object.__setattr__(
            raw,
            "synthetic_control_application_specs",
            resigned.synthetic_control_application_specs,
        )
        object.__setattr__(raw, "parent_freeze_sha", resigned.parent_freeze_sha)

        with self.assertRaises(ValueError):
            _reverify_verified_parent_freeze(wrapper)

    def test_body_token_and_seal_replacement_are_rejected_on_hit(self):
        mutations = (
            (
                "body",
                lambda wrapper: object.__setattr__(
                    wrapper,
                    _MANIFEST_SLOT,
                    parent_freeze._clone_parent_wire(_raw_manifest(wrapper)),
                ),
            ),
            (
                "token",
                lambda wrapper: object.__setattr__(wrapper, _TOKEN_SLOT, object()),
            ),
            (
                "seal",
                lambda wrapper: object.__setattr__(
                    wrapper,
                    _SEAL_SLOT,
                    "f" * 64,
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                wrapper = issue_v3m0_parent_freeze()
                with _scoped_replay_context():
                    _reverify_verified_parent_freeze(wrapper)
                    mutate(wrapper)
                    with self.assertRaises(ValueError):
                        _reverify_verified_parent_freeze(wrapper)

    def test_authority_record_replacement_and_tamper_are_rejected(self):
        mutations = (
            (
                "record replacement",
                lambda wrapper, registry, authority: registry.__setitem__(
                    id(wrapper),
                    (registry[id(wrapper)][0], dataclasses.replace(authority)),
                ),
            ),
            (
                "fingerprint",
                lambda _wrapper, _registry, authority: object.__setattr__(
                    authority,
                    "fingerprint",
                    "e" * 64,
                ),
            ),
            (
                "manifest",
                lambda _wrapper, _registry, authority: object.__setattr__(
                    authority.manifest,
                    "program_id",
                    "tampered-program",
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                wrapper = issue_v3m0_parent_freeze()
                registry = _live_registry()
                with _scoped_replay_context():
                    _reverify_verified_parent_freeze(wrapper)
                    authority = registry[id(wrapper)][1]
                    mutate(wrapper, registry, authority)
                    with self.assertRaises(ValueError):
                        _reverify_verified_parent_freeze(wrapper)

    def test_resigned_exposed_and_authority_bodies_cannot_replace_closed_binding(self):
        wrapper = issue_v3m0_parent_freeze()
        registry = _live_registry()
        with _scoped_replay_context():
            _reverify_verified_parent_freeze(wrapper)
            raw = _raw_manifest(wrapper)
            authority = registry[id(wrapper)][1]
            resigned = _resigned_deep_change(raw)
            for target in (raw, authority.manifest):
                object.__setattr__(
                    target,
                    "synthetic_control_application_specs",
                    parent_freeze._clone_parent_wire(
                        resigned.synthetic_control_application_specs
                    ),
                )
                object.__setattr__(
                    target,
                    "parent_freeze_sha",
                    resigned.parent_freeze_sha,
                )
            resigned_seal = parent_freeze._parent_freeze_seal(resigned)
            object.__setattr__(authority, "fingerprint", resigned_seal)
            object.__setattr__(wrapper, _SEAL_SLOT, resigned_seal)

            with self.assertRaises(ValueError):
                _reverify_verified_parent_freeze(wrapper)


class ParentScopedReplayIsolationTests(unittest.TestCase):
    def test_distinct_wrappers_have_distinct_proofs_and_cannot_switch_binding(self):
        first = issue_v3m0_parent_freeze()
        second = issue_v3m0_parent_freeze()
        registry = _live_registry()
        with _scoped_replay_context():
            _reverify_verified_parent_freeze(first)
            _reverify_verified_parent_freeze(second)
            _reverify_verified_parent_freeze(first)
            _reverify_verified_parent_freeze(second)
            statistics = _replay_scope_statistics()
            first_reference = registry[id(first)][0]
            second_authority = registry[id(second)][1]
            registry[id(first)] = (first_reference, second_authority)
            with self.assertRaises(ValueError):
                _reverify_verified_parent_freeze(first)

        self.assertEqual(statistics.entry_count, 2)
        self.assertEqual(dict(statistics.full_records)[_NAMESPACE], 2)
        self.assertEqual(dict(statistics.hits)[_NAMESPACE], 2)

    def test_returned_clone_mutation_does_not_poison_next_hit(self):
        wrapper = issue_v3m0_parent_freeze()
        with _scoped_replay_context():
            first = _reverify_verified_parent_freeze(wrapper)
            object.__setattr__(first, "program_id", "caller-mutated")
            second = _reverify_verified_parent_freeze(wrapper)

        self.assertEqual(second.program_id, parent_freeze.PROGRAM_ID)
        self.assertIsNot(first, second)
        self.assertIsNot(second, _raw_manifest(wrapper))

    def test_module_helper_rebinding_cannot_bypass_hit_guard(self):
        wrapper = issue_v3m0_parent_freeze()
        with _scoped_replay_context():
            _reverify_verified_parent_freeze(wrapper)
            raw = _raw_manifest(wrapper)
            object.__setattr__(raw, "program_id", "tampered-program")
            with (
                mock.patch.object(
                    parent_freeze,
                    "_clone_parent_wire",
                    return_value=parent_freeze._CLOSED_PARENT_FREEZE_SNAPSHOT,
                ),
                mock.patch.object(
                    parent_freeze,
                    "_validate_parent_freeze_manifest",
                    return_value=parent_freeze._CLOSED_PARENT_FREEZE_SNAPSHOT,
                ),
                mock.patch.object(
                    parent_freeze,
                    "_parent_freeze_seal",
                    return_value=object.__getattribute__(wrapper, _SEAL_SLOT),
                ),
            ):
                with self.assertRaises(ValueError):
                    _reverify_verified_parent_freeze(wrapper)

    def test_reverifier_retains_no_module_global_loads(self):
        offenders = [
            (instruction.opname, instruction.argval)
            for instruction in dis.get_instructions(
                _reverify_verified_parent_freeze
            )
            if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}
        ]
        self.assertEqual(offenders, [])

    def test_task11_style_registry_dependency_reuses_one_parent_full_proof(self):
        from rulespace_v3.registry import build_closed_control_registry
        from test_v3m0_dynamics import _quarter_turn_controls

        parent = issue_v3m0_parent_freeze()
        controls = _quarter_turn_controls()
        with _scoped_replay_context():
            _reverify_verified_parent_freeze(parent)
            build_closed_control_registry(controls, parent)
            _reverify_verified_parent_freeze(parent)
            statistics = _replay_scope_statistics()

        self.assertEqual(dict(statistics.full_records)[_NAMESPACE], 1)
        self.assertGreaterEqual(dict(statistics.hits)[_NAMESPACE], 2)


if __name__ == "__main__":
    unittest.main()
