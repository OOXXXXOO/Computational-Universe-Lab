"""Context-local reuse of already validated opaque capability proofs.

The cache lifetime is one explicitly opened top-level operation.  Entries
retain capability identity and authority proof metadata, never a caller raw
wire or a verifier result.  A module-specific cheap validator still runs on
every hit so in-place mutation of an exposed body remains fail-closed.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Iterator, Mapping, Optional


_SHA_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class _ReplayKey:
    namespace: str
    wrapper_type: type
    wrapper_identity: int


@dataclass(frozen=True)
class _ReplayEntry:
    wrapper: object
    token: object
    exposed_body_identities: tuple[int, ...]
    seal: str
    authority: object
    authority_digest: str


@dataclass(frozen=True)
class _ReplayScopeState:
    owner_thread_identity: int
    entries: Mapping[_ReplayKey, _ReplayEntry]
    hits: Mapping[str, int]
    misses: Mapping[str, int]
    full_records: Mapping[str, int]


@dataclass(frozen=True)
class _ReplayScopeStatistics:
    entry_count: int
    hits: tuple[tuple[str, int], ...]
    misses: tuple[tuple[str, int], ...]
    full_records: tuple[tuple[str, int], ...]


_ACTIVE_REPLAY_SCOPE: ContextVar[Optional[_ReplayScopeState]] = ContextVar(
    "v3m0_active_replay_scope",
    default=None,
)


def _frozen_mapping(values: Mapping) -> Mapping:
    return MappingProxyType(dict(values))


def _empty_state(owner_thread_identity: int) -> _ReplayScopeState:
    empty = MappingProxyType({})
    return _ReplayScopeState(
        owner_thread_identity=owner_thread_identity,
        entries=empty,
        hits=empty,
        misses=empty,
        full_records=empty,
    )


def _require_sha(value: str, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != _SHA_LENGTH
        or any(character not in _HEX_DIGITS for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _proof_key_and_body_identities(
    *,
    namespace: str,
    wrapper: object,
    expected_type: type,
    exposed_bodies: tuple[object, ...],
    seal: str,
    authority: object,
    authority_digest: str,
) -> tuple[_ReplayKey, tuple[int, ...]]:
    if type(namespace) is not str or not namespace or len(namespace) > 256:
        raise ValueError("replay namespace must be nonempty bounded text")
    if not isinstance(expected_type, type):
        raise TypeError("expected_type must be a type")
    if type(wrapper) is not expected_type:
        raise TypeError("replay wrapper has the wrong exact type")
    if type(exposed_bodies) is not tuple or not exposed_bodies:
        raise TypeError("exposed_bodies must be a nonempty exact tuple")
    if authority is None:
        raise TypeError("authority must be present")
    _require_sha(seal, "seal")
    _require_sha(authority_digest, "authority_digest")
    return (
        _ReplayKey(namespace, expected_type, id(wrapper)),
        tuple(id(body) for body in exposed_bodies),
    )


def _owned_state() -> Optional[_ReplayScopeState]:
    state = _ACTIVE_REPLAY_SCOPE.get()
    if state is None:
        return None
    if type(state) is not _ReplayScopeState:
        raise RuntimeError("active replay scope has the wrong exact state type")
    if state.owner_thread_identity != threading.get_ident():
        raise RuntimeError("active replay scope belongs to another owner thread")
    return state


def _increment(
    values: Mapping[str, int],
    namespace: str,
) -> Mapping[str, int]:
    updated = dict(values)
    updated[namespace] = updated.get(namespace, 0) + 1
    return _frozen_mapping(updated)


@contextmanager
def _scoped_replay_context() -> Iterator[None]:
    """Open one replay-proof scope or reuse a same-thread outer scope."""

    current = _ACTIVE_REPLAY_SCOPE.get()
    owner = threading.get_ident()
    if current is not None and current.owner_thread_identity == owner:
        yield
        return
    token = _ACTIVE_REPLAY_SCOPE.set(_empty_state(owner))
    try:
        yield
    finally:
        _ACTIVE_REPLAY_SCOPE.reset(token)


def _cached_replay_is_valid(
    *,
    namespace: str,
    wrapper: object,
    expected_type: type,
    token: object,
    exposed_bodies: tuple[object, ...],
    seal: str,
    authority: object,
    authority_digest: str,
    cheap_validator: Callable[[], None],
) -> bool:
    """Return true only for a guarded proof hit in the active scope."""

    key, body_identities = _proof_key_and_body_identities(
        namespace=namespace,
        wrapper=wrapper,
        expected_type=expected_type,
        exposed_bodies=exposed_bodies,
        seal=seal,
        authority=authority,
        authority_digest=authority_digest,
    )
    if not callable(cheap_validator):
        raise TypeError("cheap_validator must be callable")
    state = _owned_state()
    if state is None:
        return False
    entry = state.entries.get(key)
    if entry is None:
        _ACTIVE_REPLAY_SCOPE.set(
            _ReplayScopeState(
                owner_thread_identity=state.owner_thread_identity,
                entries=state.entries,
                hits=state.hits,
                misses=_increment(state.misses, namespace),
                full_records=state.full_records,
            )
        )
        return False
    if (
        entry.wrapper is not wrapper
        or type(entry.wrapper) is not expected_type
        or entry.token is not token
        or entry.exposed_body_identities != body_identities
        or entry.seal != seal
        or entry.authority is not authority
        or entry.authority_digest != authority_digest
    ):
        raise ValueError("cached replay proof guard mismatch")
    validation_result = cheap_validator()
    if validation_result is not None:
        raise TypeError("cheap_validator must return None")
    latest = _owned_state()
    if latest is None or latest.entries.get(key) is not entry:
        raise RuntimeError("active replay proof changed during hit validation")
    _ACTIVE_REPLAY_SCOPE.set(
        _ReplayScopeState(
            owner_thread_identity=latest.owner_thread_identity,
            entries=latest.entries,
            hits=_increment(latest.hits, namespace),
            misses=latest.misses,
            full_records=latest.full_records,
        )
    )
    return True


def _record_successful_replay(
    *,
    namespace: str,
    wrapper: object,
    expected_type: type,
    token: object,
    exposed_bodies: tuple[object, ...],
    seal: str,
    authority: object,
    authority_digest: str,
) -> None:
    """Record one completed full validation without retaining its result."""

    key, body_identities = _proof_key_and_body_identities(
        namespace=namespace,
        wrapper=wrapper,
        expected_type=expected_type,
        exposed_bodies=exposed_bodies,
        seal=seal,
        authority=authority,
        authority_digest=authority_digest,
    )
    state = _owned_state()
    if state is None:
        return
    if key in state.entries:
        raise RuntimeError("successful replay proof was already recorded")
    entries = dict(state.entries)
    entries[key] = _ReplayEntry(
        wrapper=wrapper,
        token=token,
        exposed_body_identities=body_identities,
        seal=seal,
        authority=authority,
        authority_digest=authority_digest,
    )
    _ACTIVE_REPLAY_SCOPE.set(
        _ReplayScopeState(
            owner_thread_identity=state.owner_thread_identity,
            entries=_frozen_mapping(entries),
            hits=state.hits,
            misses=state.misses,
            full_records=_increment(state.full_records, namespace),
        )
    )


def _replay_scope_statistics() -> _ReplayScopeStatistics:
    """Return immutable diagnostics for tests and performance audits."""

    state = _owned_state()
    if state is None:
        raise RuntimeError("statistics require an active replay scope")
    return _ReplayScopeStatistics(
        entry_count=len(state.entries),
        hits=tuple(sorted(state.hits.items())),
        misses=tuple(sorted(state.misses.items())),
        full_records=tuple(sorted(state.full_records.items())),
    )


__all__: tuple[str, ...] = ()
