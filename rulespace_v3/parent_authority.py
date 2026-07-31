"""Unique live-identity facade for the current V3-M0 Parent-v2.

There is deliberately no raw-manifest hydration or caller-supplied promotion
path.  The only issuer is zero-argument and delegates to the repository-closed
builder, which currently fails closed until every success scenario and the
atomic signed-source inputs are complete.
"""

from __future__ import annotations

import copy
import threading
import weakref
from dataclasses import dataclass, fields as dataclass_fields
from typing import Callable

from .evidence import canonical_sha
from .parent_freeze_v2 import _build_closed_parent_v2_manifest
from .parent_v2_contracts import (
    CurrentApplicationAuthorityV2,
    CurrentScenarioAuthorityV2,
    CurrentScenarioResponseContractV2,
    ParentFreezeV2Manifest,
    current_application_authority_v2_payload,
    current_scenario_authority_v2_payload,
    current_scenario_response_contract_v2_payload,
    parent_freeze_v2_manifest_payload,
)


_ISSUANCE_TOKEN = object()


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    observed = frozenset(vars(value))
    if expected != observed:
        raise ValueError(f"{field} contains unknown or missing fields")


def _validate_closed_manifest(manifest: ParentFreezeV2Manifest) -> ParentFreezeV2Manifest:
    _exact_record(manifest, ParentFreezeV2Manifest, "Parent-v2 manifest")
    manifest.__post_init__()
    observed_scenarios: list[str] = []
    for application in manifest.current_application_authorities:
        _exact_record(
            application,
            CurrentApplicationAuthorityV2,
            "current application authority",
        )
        application.__post_init__()
        if application.application_authority_sha != canonical_sha(
            current_application_authority_v2_payload(application)
        ):
            raise ValueError("current application authority SHA drifted")
        for scenario in application.scenario_authorities:
            _exact_record(
                scenario,
                CurrentScenarioAuthorityV2,
                "current scenario authority",
            )
            scenario.__post_init__()
            response = scenario.response_contract
            _exact_record(
                response,
                CurrentScenarioResponseContractV2,
                "current response contract",
            )
            response.__post_init__()
            if response.response_contract_sha != canonical_sha(
                current_scenario_response_contract_v2_payload(response)
            ):
                raise ValueError("current response contract SHA drifted")
            if scenario.scenario_authority_sha != canonical_sha(
                current_scenario_authority_v2_payload(scenario)
            ):
                raise ValueError("current scenario authority SHA drifted")
            observed_scenarios.append(scenario.scenario_id)
    if tuple(observed_scenarios) != manifest.block_success_scenario_ids:
        raise ValueError("Parent-v2 applications do not enumerate every success scenario")
    if manifest.parent_freeze_v2_sha != canonical_sha(
        parent_freeze_v2_manifest_payload(manifest)
    ):
        raise ValueError("Parent-v2 root SHA does not match its exact body")
    canonical = _build_closed_parent_v2_manifest()
    if manifest != canonical:
        raise ValueError("Parent-v2 body differs from the repository-closed replay")
    return copy.deepcopy(manifest)


class VerifiedParentFreezeV2:
    """Opaque live capability for the sole current Parent-v2 body."""

    __slots__ = ("__manifest", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        manifest: ParentFreezeV2Manifest,
        seal: str,
        *,
        _issuance_token=_ISSUANCE_TOKEN,
        _setattr=object.__setattr__,
    ) -> None:
        if token is not _issuance_token:
            raise TypeError("VerifiedParentFreezeV2 can only be issued internally")
        _setattr(
            self,
            "_VerifiedParentFreezeV2__manifest",
            copy.deepcopy(manifest),
        )
        _setattr(self, "_VerifiedParentFreezeV2__token", token)
        _setattr(self, "_VerifiedParentFreezeV2__seal", seal)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedParentFreezeV2 is immutable")

    @property
    def manifest(self) -> ParentFreezeV2Manifest:
        return require_current_parent(self)


@dataclass(frozen=True)
class _ParentV2AuthorityRecord:
    manifest: ParentFreezeV2Manifest
    fingerprint: str


def _parent_v2_seal(manifest: ParentFreezeV2Manifest) -> str:
    return canonical_sha(
        {
            "authority_kind": "v3m0-current-parent-live-identity-v2",
            "manifest": {
                **parent_freeze_v2_manifest_payload(manifest),
                "parent_freeze_v2_sha": manifest.parent_freeze_v2_sha,
            },
        }
    )


def _make_registry(
    *,
    validator=_validate_closed_manifest,
    seal_builder=_parent_v2_seal,
    wrapper_type=VerifiedParentFreezeV2,
    authority_type=_ParentV2AuthorityRecord,
    issuance_token=_ISSUANCE_TOKEN,
) -> tuple[
    Callable[[ParentFreezeV2Manifest], VerifiedParentFreezeV2],
    Callable[[VerifiedParentFreezeV2], ParentFreezeV2Manifest],
]:
    registry: dict[
        int,
        tuple[weakref.ReferenceType[VerifiedParentFreezeV2], _ParentV2AuthorityRecord],
    ] = {}
    lock = threading.RLock()

    def issue_closed(manifest: ParentFreezeV2Manifest) -> VerifiedParentFreezeV2:
        snapshot = validator(manifest)
        fingerprint = seal_builder(snapshot)
        wrapper = wrapper_type(issuance_token, snapshot, fingerprint)
        identity = id(wrapper)

        def remove_stale(
            reference: weakref.ReferenceType[VerifiedParentFreezeV2],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = registry.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del registry[wrapper_id]

        reference = weakref.ref(wrapper, remove_stale)
        with lock:
            current = registry.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("live VerifiedParentFreezeV2 identity collision")
            registry[identity] = (
                reference,
                authority_type(copy.deepcopy(snapshot), fingerprint),
            )
        return wrapper

    def reverify_live(wrapper: VerifiedParentFreezeV2) -> ParentFreezeV2Manifest:
        if type(wrapper) is not wrapper_type:
            raise TypeError(
                "current Parent consumer requires an exact VerifiedParentFreezeV2"
            )
        with lock:
            current = registry.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError(
                    "VerifiedParentFreezeV2 identity is absent from the live registry"
                )
            authority = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedParentFreezeV2__token",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedParentFreezeV2__seal",
            )
            manifest = object.__getattribute__(
                wrapper,
                "_VerifiedParentFreezeV2__manifest",
            )
        except AttributeError as exc:
            raise ValueError("VerifiedParentFreezeV2 record is incomplete") from exc
        if token is not issuance_token:
            raise ValueError("VerifiedParentFreezeV2 token mismatch")
        snapshot = validator(manifest)
        expected_seal = seal_builder(snapshot)
        if seal != expected_seal or seal != authority.fingerprint:
            raise ValueError("VerifiedParentFreezeV2 seal mismatch")
        if snapshot != authority.manifest:
            raise ValueError("VerifiedParentFreezeV2 manifest mismatch")
        return copy.deepcopy(authority.manifest)

    return issue_closed, reverify_live


_issue_closed_parent, _reverify_current_parent = _make_registry()


def _make_public_facade(
    *,
    closed_builder=_build_closed_parent_v2_manifest,
    issuer=_issue_closed_parent,
    reverifier=_reverify_current_parent,
):
    def issue_v3m0_parent_freeze_v2() -> VerifiedParentFreezeV2:
        """Issue the sole repository-closed current Parent, with no arguments."""

        return issuer(closed_builder())

    def require_current_parent(
        value: VerifiedParentFreezeV2,
    ) -> ParentFreezeV2Manifest:
        """Consume only a live module-issued exact v2 capability."""

        if type(value) is not VerifiedParentFreezeV2:
            raise TypeError(
                "current Parent consumer rejects v1, candidate, raw, and subclass values"
            )
        return reverifier(value)

    return issue_v3m0_parent_freeze_v2, require_current_parent


issue_v3m0_parent_freeze_v2, require_current_parent = _make_public_facade()


__all__ = [
    "VerifiedParentFreezeV2",
    "issue_v3m0_parent_freeze_v2",
    "require_current_parent",
]
