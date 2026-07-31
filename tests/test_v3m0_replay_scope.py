from __future__ import annotations

import contextvars
import copy
import gc
import threading
import unittest
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, fields
from unittest import mock

import rulespace_v3.replay_scope as replay_scope
from rulespace_v3.replay_scope import (
    _ReplayEntry,
    _cached_replay_is_valid,
    _record_successful_replay,
    _replay_scope_statistics,
    _scoped_replay_context,
)


_TOKEN = object()
_SEAL = "a" * 64
_NAMESPACE = "tests.mini-authority"


@dataclass(frozen=True)
class _Leaf:
    value: int


@dataclass(frozen=True)
class _Body:
    leaf: _Leaf


@dataclass(frozen=True)
class _AuthorityRecord:
    snapshot: _Body
    seal: str


class _Wrapper:
    __slots__ = ("__weakref__", "_token", "_body", "_seal")

    def __init__(self, token: object, body: _Body, seal: str) -> None:
        self._token = token
        self._body = body
        self._seal = seal


class _HostileWrapper(_Wrapper):
    pass


class _MiniAuthority:
    def __init__(
        self,
        *,
        cache_lookup=_cached_replay_is_valid,
        cache_record=_record_successful_replay,
    ) -> None:
        self.full_validation_count = 0
        self.fail_full_validation = False
        self._cache_lookup = cache_lookup
        self._cache_record = cache_record
        self._live: dict[
            int,
            tuple[weakref.ReferenceType[_Wrapper], _AuthorityRecord],
        ] = {}
        self._lock = threading.RLock()

    def _remove(
        self,
        identity: int,
        reference: weakref.ReferenceType[_Wrapper],
    ) -> None:
        with self._lock:
            current = self._live.get(identity)
            if current is not None and current[0] is reference:
                del self._live[identity]

    def issue(self, value: int = 1) -> _Wrapper:
        exposed = _Body(_Leaf(value))
        snapshot = copy.deepcopy(exposed)
        wrapper = _Wrapper(_TOKEN, exposed, _SEAL)
        identity = id(wrapper)
        reference = weakref.ref(
            wrapper,
            lambda ref, key=identity: self._remove(key, ref),
        )
        with self._lock:
            self._live[identity] = (
                reference,
                _AuthorityRecord(snapshot=snapshot, seal=_SEAL),
            )
        return wrapper

    def replace_authority_record(self, wrapper: _Wrapper) -> None:
        with self._lock:
            reference, record = self._live[id(wrapper)]
            self._live[id(wrapper)] = (
                reference,
                _AuthorityRecord(
                    snapshot=copy.deepcopy(record.snapshot),
                    seal=record.seal,
                ),
            )

    def mutate_authority_digest(self, wrapper: _Wrapper) -> None:
        with self._lock:
            _, record = self._live[id(wrapper)]
            object.__setattr__(record, "seal", "c" * 64)

    def mutate_authority_snapshot(self, wrapper: _Wrapper) -> None:
        with self._lock:
            _, record = self._live[id(wrapper)]
            object.__setattr__(record.snapshot.leaf, "value", 2)

    def reverify(self, wrapper: _Wrapper) -> _Body:
        if type(wrapper) is not _Wrapper:
            raise TypeError("mini authority requires the exact wrapper type")
        with self._lock:
            current = self._live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError("mini wrapper identity is not live")
            authority = current[1]
        try:
            token = object.__getattribute__(wrapper, "_token")
            body = object.__getattribute__(wrapper, "_body")
            seal = object.__getattribute__(wrapper, "_seal")
        except AttributeError as exc:
            raise ValueError("mini wrapper body is incomplete") from exc

        def cheap_validator() -> None:
            if type(body) is not _Body or type(body.leaf) is not _Leaf:
                raise TypeError("mini exposed body has the wrong exact type")
            if body != authority.snapshot:
                raise ValueError("mini exposed body differs from authority snapshot")
            if seal != authority.seal:
                raise ValueError("mini exposed seal differs from authority seal")

        proof = {
            "namespace": _NAMESPACE,
            "wrapper": wrapper,
            "expected_type": _Wrapper,
            "token": token,
            "exposed_bodies": (body,),
            "seal": seal,
            "authority": authority,
            "authority_digest": authority.seal,
        }
        if self._cache_lookup(
            **proof,
            cheap_validator=cheap_validator,
        ):
            return copy.deepcopy(authority.snapshot)

        self.full_validation_count += 1
        if self.fail_full_validation:
            raise RuntimeError("injected full-validation failure")
        if token is not _TOKEN:
            raise ValueError("mini issuance token mismatch")
        cheap_validator()
        self._cache_record(**proof)
        return copy.deepcopy(authority.snapshot)


class ScopedReplayContextTests(unittest.TestCase):
    def test_same_scope_runs_full_validation_once(self) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()
        with _scoped_replay_context():
            self.assertEqual(authority.reverify(wrapper), _Body(_Leaf(1)))
            self.assertEqual(authority.reverify(wrapper), _Body(_Leaf(1)))
        self.assertEqual(authority.full_validation_count, 1)

    def test_independent_scopes_each_run_full_validation_once(self) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()
        with _scoped_replay_context():
            authority.reverify(wrapper)
        with _scoped_replay_context():
            authority.reverify(wrapper)
        self.assertEqual(authority.full_validation_count, 2)

    def test_nested_scope_reuses_outer_proof(self) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()
        with _scoped_replay_context():
            authority.reverify(wrapper)
            with _scoped_replay_context():
                authority.reverify(wrapper)
            authority.reverify(wrapper)
            statistics = _replay_scope_statistics()
        self.assertEqual(authority.full_validation_count, 1)
        self.assertEqual(statistics.hits, ((_NAMESPACE, 2),))

    def test_exception_does_not_record_or_leak_scope(self) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()
        authority.fail_full_validation = True
        with self.assertRaisesRegex(
            RuntimeError,
            "injected full-validation failure",
        ):
            with _scoped_replay_context():
                authority.reverify(wrapper)
        authority.fail_full_validation = False
        with _scoped_replay_context():
            authority.reverify(wrapper)
            statistics = _replay_scope_statistics()
        self.assertEqual(authority.full_validation_count, 2)
        self.assertEqual(statistics.entry_count, 1)
        self.assertEqual(statistics.full_records, ((_NAMESPACE, 1),))
        with self.assertRaisesRegex(RuntimeError, "active replay scope"):
            _replay_scope_statistics()

    def test_wrong_exact_type_fake_and_expired_wrapper_are_rejected(
        self,
    ) -> None:
        authority = _MiniAuthority()
        hostile = _HostileWrapper(_TOKEN, _Body(_Leaf(1)), _SEAL)
        with self.assertRaisesRegex(TypeError, "exact wrapper type"):
            authority.reverify(hostile)
        fake = _Wrapper(_TOKEN, _Body(_Leaf(1)), _SEAL)
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            authority.reverify(fake)

        expired = authority.issue()
        expired_reference = weakref.ref(expired)
        del expired
        gc.collect()
        self.assertIsNone(expired_reference())
        replacement = _Wrapper(_TOKEN, _Body(_Leaf(1)), _SEAL)
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            authority.reverify(replacement)

    def test_token_body_seal_and_authority_identity_changes_are_rejected(
        self,
    ) -> None:
        mutators = {
            "token": lambda authority, wrapper: object.__setattr__(
                wrapper,
                "_token",
                object(),
            ),
            "body": lambda authority, wrapper: object.__setattr__(
                wrapper,
                "_body",
                copy.deepcopy(wrapper._body),
            ),
            "seal": lambda authority, wrapper: object.__setattr__(
                wrapper,
                "_seal",
                "b" * 64,
            ),
            "authority": lambda authority, wrapper: (
                authority.replace_authority_record(wrapper)
            ),
            "authority_digest": lambda authority, wrapper: (
                authority.mutate_authority_digest(wrapper)
            ),
            "authority_snapshot": lambda authority, wrapper: (
                authority.mutate_authority_snapshot(wrapper)
            ),
        }
        for name, mutate in mutators.items():
            with self.subTest(name=name):
                authority = _MiniAuthority()
                wrapper = authority.issue()
                with _scoped_replay_context():
                    authority.reverify(wrapper)
                    mutate(authority, wrapper)
                    with self.assertRaises(ValueError):
                        authority.reverify(wrapper)
                self.assertEqual(authority.full_validation_count, 1)

    def test_in_place_deep_scalar_mutation_is_rejected_on_cache_hit(
        self,
    ) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()
        original_body_identity = id(wrapper._body)
        with _scoped_replay_context():
            authority.reverify(wrapper)
            object.__setattr__(wrapper._body.leaf, "value", 2)
            self.assertEqual(id(wrapper._body), original_body_identity)
            with self.assertRaisesRegex(
                ValueError,
                "differs from authority snapshot",
            ):
                authority.reverify(wrapper)
        self.assertEqual(authority.full_validation_count, 1)

    def test_copied_context_cannot_reuse_proof_in_another_thread(
        self,
    ) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()
        with _scoped_replay_context():
            authority.reverify(wrapper)
            copied = contextvars.copy_context()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    copied.run,
                    authority.reverify,
                    wrapper,
                )
                with self.assertRaisesRegex(RuntimeError, "owner thread"):
                    future.result()
        self.assertEqual(authority.full_validation_count, 1)

    def test_public_scope_in_copied_thread_starts_independent_scope(
        self,
    ) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()

        def run_scoped() -> object:
            with _scoped_replay_context():
                authority.reverify(wrapper)
                return _replay_scope_statistics()

        with _scoped_replay_context():
            authority.reverify(wrapper)
            copied = contextvars.copy_context()
            with ThreadPoolExecutor(max_workers=1) as executor:
                child_statistics = executor.submit(
                    copied.run,
                    run_scoped,
                ).result()
            authority.reverify(wrapper)
            parent_statistics = _replay_scope_statistics()
        self.assertEqual(authority.full_validation_count, 2)
        self.assertEqual(child_statistics.full_records, ((_NAMESPACE, 1),))
        self.assertEqual(parent_statistics.full_records, ((_NAMESPACE, 1),))
        self.assertEqual(parent_statistics.hits, ((_NAMESPACE, 1),))

    def test_copied_context_uses_immutable_state_replacement(self) -> None:
        authority = _MiniAuthority()
        first = authority.issue(1)
        second = authority.issue(2)

        def add_second() -> object:
            authority.reverify(second)
            return _replay_scope_statistics()

        with _scoped_replay_context():
            authority.reverify(first)
            copied = contextvars.copy_context()
            child_statistics = copied.run(add_second)
            parent_statistics = _replay_scope_statistics()
        self.assertEqual(child_statistics.entry_count, 2)
        self.assertEqual(parent_statistics.entry_count, 1)
        self.assertEqual(authority.full_validation_count, 2)

    def test_scope_entry_has_no_raw_wire_or_cached_result_field(self) -> None:
        entry_fields = {field.name for field in fields(_ReplayEntry)}
        self.assertEqual(
            entry_fields,
            {
                "wrapper",
                "token",
                "exposed_body_identities",
                "seal",
                "authority",
                "authority_digest",
            },
        )
        self.assertTrue(
            entry_fields.isdisjoint(
                {"raw", "raw_wire", "body", "snapshot", "result"},
            )
        )

    def test_statistics_report_hits_misses_and_full_records(self) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()
        with _scoped_replay_context():
            authority.reverify(wrapper)
            authority.reverify(wrapper)
            statistics = _replay_scope_statistics()
        self.assertEqual(statistics.entry_count, 1)
        self.assertEqual(statistics.hits, ((_NAMESPACE, 1),))
        self.assertEqual(statistics.misses, ((_NAMESPACE, 1),))
        self.assertEqual(statistics.full_records, ((_NAMESPACE, 1),))

    def test_constructed_reverifier_keeps_captured_helpers(self) -> None:
        authority = _MiniAuthority()
        wrapper = authority.issue()
        with (
            mock.patch.object(
                replay_scope,
                "_cached_replay_is_valid",
                side_effect=AssertionError("module global cache lookup used"),
            ),
            mock.patch.object(
                replay_scope,
                "_record_successful_replay",
                side_effect=AssertionError("module global cache record used"),
            ),
            _scoped_replay_context(),
        ):
            authority.reverify(wrapper)
            authority.reverify(wrapper)
        self.assertEqual(authority.full_validation_count, 1)


if __name__ == "__main__":
    unittest.main()
