"""Inert current-Parent envelope for the Task-11 window protocol.

The numerical window implementation remains the reviewed v1 engine, while
this exact v2 body binds that replay to the current C01--C03 scenario roots.
No function in this module promotes the raw body to an opaque capability.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, fields as dataclass_fields, replace
import re
import threading
import weakref

from .evidence import canonical_sha
from .task8_control_replay import (
    CurrentControlRegistryV2,
    CurrentTask8ControlReplay,
    VerifiedCurrentControlRegistryV2,
    _replay_current_control_registry_v2,
    current_control_registry_v2_payload,
    verify_current_control_registry_v2_body,
)
from .thresholds import T_CANDIDATES
from .window import (
    ControlWindowProtocolEntry,
    WindowCalibrationProtocol,
    build_control_window_protocol_entries,
    build_window_calibration_protocol,
    verify_window_calibration_protocol,
    window_calibration_protocol_payload,
)


CURRENT_WINDOW_CONTROL_BINDING_V2_SCHEMA_VERSION = (
    "v3m0.current-window-control-binding.v2"
)
CURRENT_WINDOW_CALIBRATION_PROTOCOL_V2_SCHEMA_VERSION = (
    "v3m0.current-window-calibration-protocol.v2"
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TASK8_CASES = (
    ("C01_BLIND_HOLDOUT_FULL", "full"),
    ("C02_CONDITIONED_ZERO", "zero"),
    ("C03_EQUAL_RANK_DIRECT_SUM", "direct_sum"),
)


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _LOWER_SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be a non-empty exact string")
    return value


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


@dataclass(frozen=True)
class CurrentWindowControlBindingV2:
    binding_schema_version: str
    parent_freeze_v2_sha: str
    control_case_id: str
    control_id: str
    current_registry_entry_sha: str
    scenario_authority_sha: str
    response_contract_sha: str
    legacy_window_entry_sha: str
    binding_sha: str

    def __post_init__(self) -> None:
        if (
            self.binding_schema_version
            != CURRENT_WINDOW_CONTROL_BINDING_V2_SCHEMA_VERSION
        ):
            raise ValueError("current window control-binding schema drifted")
        for field in ("control_case_id", "control_id"):
            _text(getattr(self, field), field)
        for field in (
            "parent_freeze_v2_sha",
            "current_registry_entry_sha",
            "scenario_authority_sha",
            "response_contract_sha",
            "legacy_window_entry_sha",
            "binding_sha",
        ):
            _sha(getattr(self, field), field)


def current_window_control_binding_v2_payload(
    binding: CurrentWindowControlBindingV2,
) -> dict[str, object]:
    _exact_record(binding, CurrentWindowControlBindingV2, "window control binding")
    return {
        "binding_schema_version": binding.binding_schema_version,
        "parent_freeze_v2_sha": binding.parent_freeze_v2_sha,
        "control_case_id": binding.control_case_id,
        "control_id": binding.control_id,
        "current_registry_entry_sha": binding.current_registry_entry_sha,
        "scenario_authority_sha": binding.scenario_authority_sha,
        "response_contract_sha": binding.response_contract_sha,
        "legacy_window_entry_sha": binding.legacy_window_entry_sha,
    }


@dataclass(frozen=True)
class CurrentWindowCalibrationProtocolV2:
    protocol_schema_version: str
    parent_freeze_v2_sha: str
    current_control_registry: CurrentControlRegistryV2
    legacy_window_protocol: WindowCalibrationProtocol
    t_candidates: tuple[int, ...]
    control_bindings: tuple[CurrentWindowControlBindingV2, ...]
    protocol_sha: str

    def __post_init__(self) -> None:
        if (
            self.protocol_schema_version
            != CURRENT_WINDOW_CALIBRATION_PROTOCOL_V2_SCHEMA_VERSION
        ):
            raise ValueError("current window protocol schema drifted")
        _sha(self.parent_freeze_v2_sha, "parent_freeze_v2_sha")
        _exact_record(
            self.current_control_registry,
            CurrentControlRegistryV2,
            "current_control_registry",
        )
        _exact_record(
            self.legacy_window_protocol,
            WindowCalibrationProtocol,
            "legacy_window_protocol",
        )
        if type(self.t_candidates) is not tuple or self.t_candidates != T_CANDIDATES:
            raise ValueError("current window candidate table is not frozen")
        if (
            type(self.control_bindings) is not tuple
            or len(self.control_bindings) != len(_TASK8_CASES)
            or not all(
                type(item) is CurrentWindowControlBindingV2
                for item in self.control_bindings
            )
        ):
            raise TypeError("current window bindings must be the exact three tuple")
        if tuple(item.control_case_id for item in self.control_bindings) != tuple(
            item[0] for item in _TASK8_CASES
        ):
            raise ValueError("current window bindings are not in C01-C03 order")
        if tuple(item.control_id for item in self.control_bindings) != tuple(
            item[1] for item in _TASK8_CASES
        ):
            raise ValueError("current window binding control IDs drifted")
        if (
            self.current_control_registry.parent_freeze_v2_sha
            != self.parent_freeze_v2_sha
            or any(
                item.parent_freeze_v2_sha != self.parent_freeze_v2_sha
                for item in self.control_bindings
            )
        ):
            raise ValueError("current window protocol is spliced across Parent-v2")
        _sha(self.protocol_sha, "protocol_sha")


def current_window_calibration_protocol_v2_payload(
    protocol: CurrentWindowCalibrationProtocolV2,
    *,
    _registry_payload=current_control_registry_v2_payload,
    _legacy_payload=window_calibration_protocol_payload,
    _binding_payload=current_window_control_binding_v2_payload,
) -> dict[str, object]:
    _exact_record(
        protocol,
        CurrentWindowCalibrationProtocolV2,
        "current window protocol",
    )
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "parent_freeze_v2_sha": protocol.parent_freeze_v2_sha,
        "current_control_registry": {
            **_registry_payload(
                protocol.current_control_registry
            ),
            "registry_sha": protocol.current_control_registry.registry_sha,
        },
        "legacy_window_protocol": {
            **_legacy_payload(
                protocol.legacy_window_protocol
            ),
            "protocol_sha": protocol.legacy_window_protocol.protocol_sha,
        },
        "t_candidates": list(protocol.t_candidates),
        "control_bindings": [
            {
                **_binding_payload(item),
                "binding_sha": item.binding_sha,
            }
            for item in protocol.control_bindings
        ],
    }


def _build_current_window_calibration_protocol_v2_body(
    current_registry: CurrentControlRegistryV2,
    replay: CurrentTask8ControlReplay,
    *,
    _registry_verifier=verify_current_control_registry_v2_body,
    _entry_builder=build_control_window_protocol_entries,
    _protocol_builder=build_window_calibration_protocol,
    _binding_payload=current_window_control_binding_v2_payload,
    _protocol_payload=current_window_calibration_protocol_v2_payload,
) -> CurrentWindowCalibrationProtocolV2:
    """Build the exact inert current window envelope from a fresh replay."""

    verified_registry = _registry_verifier(
        current_registry,
        current_registry.parent_freeze_v2_sha,
        replay,
    )
    legacy_entries = _entry_builder(
        replay.legacy_registry
    )
    legacy_capability = _protocol_builder(
        replay.legacy_registry,
        legacy_entries,
    )
    legacy_protocol = legacy_capability.protocol
    bindings: list[CurrentWindowControlBindingV2] = []
    for current_entry, legacy_entry in zip(
        verified_registry.entries,
        legacy_protocol.control_entries,
    ):
        if (
            type(legacy_entry) is not ControlWindowProtocolEntry
            or current_entry.control_id != legacy_entry.control_id
            or current_entry.legacy_registry_entry.entry_sha
            != legacy_entry.control_registry_entry_sha
        ):
            raise ValueError("current/legacy window control roots are spliced")
        provisional = CurrentWindowControlBindingV2(
            binding_schema_version=(
                CURRENT_WINDOW_CONTROL_BINDING_V2_SCHEMA_VERSION
            ),
            parent_freeze_v2_sha=verified_registry.parent_freeze_v2_sha,
            control_case_id=current_entry.control_case_id,
            control_id=current_entry.control_id,
            current_registry_entry_sha=current_entry.entry_sha,
            scenario_authority_sha=current_entry.scenario_authority_sha,
            response_contract_sha=current_entry.response_contract_sha,
            legacy_window_entry_sha=legacy_entry.entry_sha,
            binding_sha="0" * 64,
        )
        bindings.append(
            replace(
                provisional,
                binding_sha=canonical_sha(
                    _binding_payload(provisional)
                ),
            )
        )
    provisional_protocol = CurrentWindowCalibrationProtocolV2(
        protocol_schema_version=(
            CURRENT_WINDOW_CALIBRATION_PROTOCOL_V2_SCHEMA_VERSION
        ),
        parent_freeze_v2_sha=verified_registry.parent_freeze_v2_sha,
        current_control_registry=verified_registry,
        legacy_window_protocol=legacy_protocol,
        t_candidates=T_CANDIDATES,
        control_bindings=tuple(bindings),
        protocol_sha="0" * 64,
    )
    return replace(
        provisional_protocol,
        protocol_sha=canonical_sha(
            _protocol_payload(
                provisional_protocol
            )
        ),
    )


def verify_current_window_calibration_protocol_v2_body(
    protocol: CurrentWindowCalibrationProtocolV2,
    current_registry: CurrentControlRegistryV2,
    replay: CurrentTask8ControlReplay,
    *,
    _registry_verifier=verify_current_control_registry_v2_body,
    _legacy_verifier=verify_window_calibration_protocol,
    _binding_payload=current_window_control_binding_v2_payload,
    _protocol_payload=current_window_calibration_protocol_v2_payload,
    _builder=_build_current_window_calibration_protocol_v2_body,
) -> CurrentWindowCalibrationProtocolV2:
    """Validate the raw envelope against both current and numerical roots."""

    _exact_record(
        protocol,
        CurrentWindowCalibrationProtocolV2,
        "current window protocol",
    )
    protocol.__post_init__()
    _registry_verifier(
        protocol.current_control_registry,
        protocol.parent_freeze_v2_sha,
        replay,
    )
    verified_legacy = _legacy_verifier(
        protocol.legacy_window_protocol,
        replay.legacy_registry,
    ).protocol
    if verified_legacy != protocol.legacy_window_protocol:
        raise ValueError("legacy window protocol differs from live replay")
    for index, binding in enumerate(protocol.control_bindings):
        _exact_record(
            binding,
            CurrentWindowControlBindingV2,
            f"current window control binding[{index}]",
        )
        binding.__post_init__()
        if binding.binding_sha != canonical_sha(
            _binding_payload(binding)
        ):
            raise ValueError("current window control-binding SHA drifted")
    if protocol.protocol_sha != canonical_sha(
        _protocol_payload(protocol)
    ):
        raise ValueError("current window protocol SHA drifted")
    expected = _builder(
        current_registry,
        replay,
    )
    if protocol != expected:
        raise ValueError("current window protocol differs from fresh replay")
    return protocol


class VerifiedCurrentWindowCalibrationProtocolV2:
    """Opaque live current-window protocol capability."""

    __slots__ = ("_protocol_sha", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("current window protocol v2 is issuer-only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("current window protocol v2 is immutable")


@dataclass(frozen=True)
class _LiveCurrentWindowCalibrationProtocolV2:
    registry_capability: object
    protocol_sha: str


def _make_current_window_calibration_protocol_v2_api(
    *,
    registry_type: type,
    registry_replayer,
    body_builder=_build_current_window_calibration_protocol_v2_body,
    body_verifier=verify_current_window_calibration_protocol_v2_body,
    wrapper_type=VerifiedCurrentWindowCalibrationProtocolV2,
):
    """Freeze issuance and consumption over one live current registry."""

    registry: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedCurrentWindowCalibrationProtocolV2],
            _LiveCurrentWindowCalibrationProtocolV2,
        ],
    ] = {}
    lock = threading.RLock()

    def _replay(registry_capability):
        if type(registry_capability) is not registry_type:
            raise TypeError(
                "current window protocol requires an exact live current registry"
            )
        current_registry, task8_replay = registry_replayer(registry_capability)
        if type(current_registry) is not CurrentControlRegistryV2:
            raise TypeError("current window registry replay returned the wrong type")
        if type(task8_replay) is not CurrentTask8ControlReplay:
            raise TypeError("current window Task-8 replay returned the wrong type")
        protocol = body_builder(current_registry, task8_replay)
        return body_verifier(protocol, current_registry, task8_replay)

    def _live_record(value):
        if type(value) is not wrapper_type:
            raise TypeError(
                "current window consumer requires its exact opaque type"
            )
        with lock:
            current = registry.get(id(value))
            if current is None or current[0]() is not value:
                raise ValueError("current window protocol identity is not live")
            record = current[1]
        try:
            slot_sha = object.__getattribute__(value, "_protocol_sha")
        except AttributeError as exc:
            raise ValueError("current window protocol record is incomplete") from exc
        if slot_sha != record.protocol_sha:
            raise ValueError("current window protocol replay seal mismatch")
        return record

    def build_current_window_calibration_protocol_v2(
        registry_capability,
    ) -> VerifiedCurrentWindowCalibrationProtocolV2:
        protocol = _replay(registry_capability)
        wrapper = object.__new__(wrapper_type)
        object.__setattr__(wrapper, "_protocol_sha", protocol.protocol_sha)
        identity = id(wrapper)
        record = _LiveCurrentWindowCalibrationProtocolV2(
            registry_capability=registry_capability,
            protocol_sha=protocol.protocol_sha,
        )

        def remove_stale(
            reference: weakref.ReferenceType[
                VerifiedCurrentWindowCalibrationProtocolV2
            ],
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
                raise RuntimeError("live current window protocol identity collision")
            registry[identity] = (reference, record)
        return wrapper

    def require_current_window_calibration_protocol_v2(
        value: VerifiedCurrentWindowCalibrationProtocolV2,
    ) -> CurrentWindowCalibrationProtocolV2:
        record = _live_record(value)
        protocol = _replay(record.registry_capability)
        if protocol.protocol_sha != record.protocol_sha:
            raise ValueError("current window protocol replay seal mismatch")
        return copy.deepcopy(protocol)

    return (
        build_current_window_calibration_protocol_v2,
        require_current_window_calibration_protocol_v2,
    )


(
    build_current_window_calibration_protocol_v2,
    require_current_window_calibration_protocol_v2,
) = _make_current_window_calibration_protocol_v2_api(
    registry_type=VerifiedCurrentControlRegistryV2,
    registry_replayer=_replay_current_control_registry_v2,
)


def _current_window_protocol_property(
    self,
    _consumer=require_current_window_calibration_protocol_v2,
) -> CurrentWindowCalibrationProtocolV2:
    return _consumer(self)


VerifiedCurrentWindowCalibrationProtocolV2.protocol = property(
    _current_window_protocol_property
)
del _current_window_protocol_property


__all__ = [
    "CURRENT_WINDOW_CALIBRATION_PROTOCOL_V2_SCHEMA_VERSION",
    "CURRENT_WINDOW_CONTROL_BINDING_V2_SCHEMA_VERSION",
    "CurrentWindowCalibrationProtocolV2",
    "CurrentWindowControlBindingV2",
    "VerifiedCurrentWindowCalibrationProtocolV2",
    "build_current_window_calibration_protocol_v2",
    "current_window_calibration_protocol_v2_payload",
    "current_window_control_binding_v2_payload",
    "require_current_window_calibration_protocol_v2",
]
