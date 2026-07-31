"""Pre-shell Task 11 window-calibration protocol authority.

The protocol is frozen from the live three-control registry and the matching
C01--C03 parent application specs before any transition-derived shell exists.
Raw records remain serialization wires; only the live opaque wrapper is an
authority for downstream response construction.
"""

from __future__ import annotations

import math
import re
import threading
import weakref
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Callable, Literal

from .evidence import canonical_sha
from .grids import (
    BRIDGE_GRID_MAX_POINT_COUNT,
    RESPONSE_GRID_MAX_POINT_COUNT,
    BridgeKGridManifest,
    DirectionManifest,
    DirectionPathClosure,
    ResponseKGridManifest,
    _preflight_general_evidence_value,
    _preflight_spatial_dimension,
    _preflight_vector_dimension,
    bridge_grid_payload,
    build_application_bridge_grid_manifest,
    build_response_grid_manifest,
    response_grid_payload,
    verify_application_bridge_grid_manifest,
    verify_response_grid_manifest,
)
from .factory import _reverify_verified_factory
from .parent_freeze import (
    EXPECTED_SHELL_RANK_SOURCE_ID,
    V3M0SyntheticControlApplicationSpec,
    _reverify_verified_parent_freeze,
)
from .registry import (
    CONTROL_ORDER,
    ControlRegistryEntry,
    VerifiedControlRegistry,
    _reverify_verified_control_registry,
)
from .thresholds import (
    GENERAL_EVIDENCE_BODY_BYTES_MAX,
    OVERLAP_MARGIN_MIN,
    PHASE_GRID_PROTOCOL_ID,
    PHASE_SEPARATION_PROTOCOL_ID,
    SHELL_LOOP_RESIDUAL_MAX,
    SHELL_PARTICIPATION_MIN,
    SHELL_PROJECTOR_RESIDUAL_MAX,
    SOURCE_TRIAL_GENERATION_ID,
    T_CANDIDATES,
    preflight_source_bridge_work,
    verify_window_protocol_thresholds,
)


WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION = (
    "v3m0.window-calibration-protocol.v1"
)
_CONTROL_APPLICATION_CASE_IDS = (
    "C01_BLIND_HOLDOUT_FULL",
    "C02_CONDITIONED_ZERO",
    "C03_EQUAL_RANK_DIRECT_SUM",
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()


def _text(
    value: object,
    field: str,
    *,
    _type=type,
    _str_type=str,
    _type_error=TypeError,
    _value_error=ValueError,
) -> str:
    if _type(value) is not _str_type:
        raise _type_error(f"{field} must be a string")
    if not value.strip():
        raise _value_error(f"{field} must be non-empty")
    return value


def _sha(
    value: object,
    field: str,
    *,
    _text_validator=_text,
    _sha_pattern=_LOWER_SHA,
    _value_error=ValueError,
) -> str:
    result = _text_validator(value, field)
    if _sha_pattern.fullmatch(result) is None:
        raise _value_error(f"{field} must be a lowercase SHA-256")
    return result


def _positive_int(
    value: object,
    field: str,
    *,
    _type=type,
    _int_type=int,
    _type_error=TypeError,
    _value_error=ValueError,
) -> int:
    if _type(value) is not _int_type:
        raise _type_error(f"{field} must be an int")
    if value <= 0:
        raise _value_error(f"{field} must be positive")
    return value


def _index(
    value: object,
    field: str,
    *,
    ndim: int,
    _type=type,
    _tuple_type=tuple,
    _len=len,
    _enumerate=enumerate,
    _int_type=int,
    _list_type=list,
    _type_error=TypeError,
    _value_error=ValueError,
) -> tuple[int, ...]:
    if _type(value) is not _tuple_type or _len(value) != ndim:
        raise _value_error(f"{field} dimension mismatch")
    result: list[int] = _list_type()
    for axis, item in _enumerate(value):
        if _type(item) is not _int_type:
            raise _type_error(f"{field}[{axis}] must be an int")
        result.append(item)
    return _tuple_type(result)


def _phase_bands(
    value: object,
    field: str,
    *,
    _type=type,
    _tuple_type=tuple,
    _len=len,
    _enumerate=enumerate,
    _float_type=float,
    _list_type=list,
    _isfinite=math.isfinite,
    _pi=math.pi,
    _sorted=sorted,
    _set_type=set,
    _type_error=TypeError,
    _value_error=ValueError,
) -> tuple[tuple[float, float], ...]:
    if _type(value) is not _tuple_type or not value:
        raise _value_error(f"{field} must be a non-empty tuple")
    bands: list[tuple[float, float]] = _list_type()
    for index, band in _enumerate(value):
        if _type(band) is not _tuple_type or _len(band) != 2:
            raise _type_error(f"{field}[{index}] must be a pair")
        lower, upper = band
        if _type(lower) is not _float_type or _type(upper) is not _float_type:
            raise _type_error(f"{field}[{index}] endpoints must be floats")
        if not _isfinite(lower) or not _isfinite(upper):
            raise _value_error(f"{field}[{index}] endpoints must be finite")
        if not -_pi <= lower < upper <= _pi:
            raise _value_error(
                f"{field}[{index}] must be an ordered principal-phase band"
            )
        bands.append((lower, upper))
    result = _tuple_type(bands)
    if result != _tuple_type(_sorted(_set_type(result))):
        raise _value_error(f"{field} must be unique and canonical")
    return result


def _require_exact_record_fields(
    record: object,
    record_type: type[object],
    field: str,
) -> None:
    if type(record) is not record_type:
        raise TypeError(f"{field} has the wrong record type")
    expected = frozenset(record_type.__dataclass_fields__)
    try:
        observed = frozenset(vars(record))
    except TypeError as exc:
        raise TypeError(f"{field} has no strict record body") from exc
    if observed != expected:
        raise ValueError(
            f"{field} fields are not exact: "
            f"missing={sorted(expected - observed)!r}, "
            f"unknown={sorted(observed - expected)!r}"
        )


def _bounded_tuple(
    value: object,
    field: str,
    cap: int,
) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if len(value) > cap:
        raise ValueError(f"{field} exceeds point cap")
    return value


def _response_grid_record(
    grid: ResponseKGridManifest,
) -> dict[str, object]:
    return {
        **response_grid_payload(grid),
        "response_grid_sha": grid.response_grid_sha,
    }


def _bridge_grid_record(
    grid: BridgeKGridManifest,
) -> dict[str, object]:
    return {
        **bridge_grid_payload(grid),
        "bridge_grid_sha": grid.bridge_grid_sha,
    }


@dataclass(frozen=True)
class ControlWindowProtocolEntry:
    control_id: Literal["full", "zero", "direct_sum"]
    control_registry_entry_sha: str
    response_grid: ResponseKGridManifest
    source_readout_bridge_grid: BridgeKGridManifest
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    expected_shell_rank: int
    expected_shell_rank_source_id: Literal[
        "parent-freeze-control-application-spec-v1"
    ]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    source_trial_generation_id: Literal["registry-source-identity-v1"]
    entry_sha: str

    def __post_init__(
        self,
        *,
        _control_order=tuple(CONTROL_ORDER),
        _sha_validator=_sha,
        _response_type=ResponseKGridManifest,
        _bridge_type=BridgeKGridManifest,
        _positive_integer=_positive_int,
        _index_validator=_index,
        _phase_validator=_phase_bands,
        _rank_source_id=EXPECTED_SHELL_RANK_SOURCE_ID,
        _trial_source_id=SOURCE_TRIAL_GENERATION_ID,
        _type=type,
        _tuple_type=tuple,
        _enumerate=enumerate,
        _sorted=sorted,
        _set_type=set,
        _any=any,
        _type_error=TypeError,
        _value_error=ValueError,
    ) -> None:
        if self.control_id not in _control_order:
            raise _value_error("control_id is outside the closed registry")
        _sha_validator(
            self.control_registry_entry_sha,
            "control_registry_entry_sha",
        )
        if _type(self.response_grid) is not _response_type:
            raise _type_error(
                "response_grid must be a ResponseKGridManifest"
            )
        if _type(self.source_readout_bridge_grid) is not _bridge_type:
            raise _type_error(
                "source_readout_bridge_grid must be a BridgeKGridManifest"
            )
        if (
            _type(self.source_readout_bridge_steps) is not _tuple_type
            or not self.source_readout_bridge_steps
        ):
            raise _value_error(
                "source_readout_bridge_steps must be a non-empty tuple"
            )
        steps = _tuple_type(
            _positive_integer(
                step,
                f"source_readout_bridge_steps[{index}]",
            )
            for index, step in _enumerate(
                self.source_readout_bridge_steps
            )
        )
        if steps != _tuple_type(_sorted(_set_type(steps))):
            raise _value_error(
                "source_readout_bridge_steps must be strictly ascending"
            )
        if steps[-1] > 16384 or not _any(step > 1 for step in steps):
            raise _value_error(
                "source_readout_bridge_steps must include t>1 through 16384"
            )
        reference = _index_validator(
            self.reference_reciprocal_index,
            "reference_reciprocal_index",
            ndim=self.response_grid.spatial_ndim,
        )
        if reference not in self.response_grid.reciprocal_indices:
            raise _value_error(
                "reference_reciprocal_index is absent from response_grid"
            )
        _positive_integer(self.expected_shell_rank, "expected_shell_rank")
        if self.expected_shell_rank_source_id != _rank_source_id:
            raise _value_error(
                "expected_shell_rank_source_id is not frozen"
            )
        _phase_validator(
            self.preregistered_phase_bands,
            "preregistered_phase_bands",
        )
        if self.source_trial_generation_id != _trial_source_id:
            raise _value_error("source_trial_generation_id is not frozen")
        _sha_validator(self.entry_sha, "entry_sha")


@dataclass(frozen=True)
class WindowCalibrationProtocol:
    protocol_schema_version: str
    control_registry_sha: str
    parent_freeze_sha: str
    t_candidates: tuple[int, ...]
    control_entries: tuple[ControlWindowProtocolEntry, ...]
    phase_grid_protocol_id: Literal["two-pi-over-16T-v1"]
    phase_separation_protocol_id: Literal["eight-pi-over-T-v1"]
    participation_min_required: float
    overlap_margin_required: float
    loop_residual_max: float
    projector_residual_max: float
    protocol_sha: str

    def __post_init__(
        self,
        *,
        _text_validator=_text,
        _sha_validator=_sha,
        _threshold_verifier=verify_window_protocol_thresholds,
        _entry_type=ControlWindowProtocolEntry,
        _type=type,
        _tuple_type=tuple,
        _all=all,
        _type_error=TypeError,
    ) -> None:
        _text_validator(
            self.protocol_schema_version,
            "protocol_schema_version",
        )
        _sha_validator(self.control_registry_sha, "control_registry_sha")
        _sha_validator(self.parent_freeze_sha, "parent_freeze_sha")
        if _type(self.t_candidates) is not _tuple_type:
            raise _type_error("t_candidates must be a tuple")
        if _type(self.control_entries) is not _tuple_type:
            raise _type_error("control_entries must be a tuple")
        if not _all(
            _type(item) is _entry_type
            for item in self.control_entries
        ):
            raise _type_error(
                "control_entries must contain exact protocol entry records"
            )
        _threshold_verifier(
            t_candidates=self.t_candidates,
            phase_grid_protocol_id=self.phase_grid_protocol_id,
            phase_separation_protocol_id=(
                self.phase_separation_protocol_id
            ),
            participation_min_required=self.participation_min_required,
            overlap_margin_required=self.overlap_margin_required,
            loop_residual_max=self.loop_residual_max,
            projector_residual_max=self.projector_residual_max,
        )
        _sha_validator(self.protocol_sha, "protocol_sha")


def control_window_protocol_entry_payload(
    entry: ControlWindowProtocolEntry,
) -> dict[str, object]:
    if type(entry) is not ControlWindowProtocolEntry:
        raise TypeError(
            "entry must be a ControlWindowProtocolEntry"
        )
    return {
        "control_id": entry.control_id,
        "control_registry_entry_sha": (
            entry.control_registry_entry_sha
        ),
        "response_grid": _response_grid_record(entry.response_grid),
        "source_readout_bridge_grid": _bridge_grid_record(
            entry.source_readout_bridge_grid
        ),
        "source_readout_bridge_steps": list(
            entry.source_readout_bridge_steps
        ),
        "reference_reciprocal_index": list(
            entry.reference_reciprocal_index
        ),
        "expected_shell_rank": entry.expected_shell_rank,
        "expected_shell_rank_source_id": (
            entry.expected_shell_rank_source_id
        ),
        "preregistered_phase_bands": [
            list(item) for item in entry.preregistered_phase_bands
        ],
        "source_trial_generation_id": entry.source_trial_generation_id,
    }


def _control_entry_record(
    entry: ControlWindowProtocolEntry,
) -> dict[str, object]:
    return {
        **control_window_protocol_entry_payload(entry),
        "entry_sha": entry.entry_sha,
    }


def window_calibration_protocol_payload(
    protocol: WindowCalibrationProtocol,
) -> dict[str, object]:
    if type(protocol) is not WindowCalibrationProtocol:
        raise TypeError("protocol must be a WindowCalibrationProtocol")
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "control_registry_sha": protocol.control_registry_sha,
        "parent_freeze_sha": protocol.parent_freeze_sha,
        "t_candidates": list(protocol.t_candidates),
        "control_entries": [
            _control_entry_record(item)
            for item in protocol.control_entries
        ],
        "phase_grid_protocol_id": protocol.phase_grid_protocol_id,
        "phase_separation_protocol_id": (
            protocol.phase_separation_protocol_id
        ),
        "participation_min_required": (
            protocol.participation_min_required
        ),
        "overlap_margin_required": protocol.overlap_margin_required,
        "loop_residual_max": protocol.loop_residual_max,
        "projector_residual_max": protocol.projector_residual_max,
    }


def _preflight_entries(
    entries: tuple[ControlWindowProtocolEntry, ...],
) -> tuple[ControlWindowProtocolEntry, ...]:
    if type(entries) is not tuple:
        raise TypeError("control_entries must be a tuple")
    if len(entries) != len(CONTROL_ORDER):
        raise ValueError("control_entries must contain exactly three controls")
    for entry in entries:
        _require_exact_record_fields(
            entry,
            ControlWindowProtocolEntry,
            "control window entry",
        )
        response = entry.response_grid
        bridge = entry.source_readout_bridge_grid
        _require_exact_record_fields(
            response,
            ResponseKGridManifest,
            "response grid",
        )
        _bounded_tuple(
            response.reciprocal_indices,
            "response grid",
            RESPONSE_GRID_MAX_POINT_COUNT,
        )
        direction = response.direction_manifest
        _require_exact_record_fields(
            direction,
            DirectionManifest,
            "response direction manifest",
        )
        for field, label in (
            ("direction_ids", "response directions"),
            ("primitive_directions", "response directions"),
            ("path_ids", "response direction paths"),
            ("ordered_paths", "response direction paths"),
            ("closure_path_pairs", "response closures"),
        ):
            _bounded_tuple(
                getattr(direction, field),
                label,
                RESPONSE_GRID_MAX_POINT_COUNT,
            )
        total_path_points = 0
        for path in direction.ordered_paths:
            if type(path) is not tuple:
                raise TypeError(
                    "response ordered_paths entries must be tuples"
                )
            total_path_points += len(path)
            if total_path_points > RESPONSE_GRID_MAX_POINT_COUNT:
                raise ValueError(
                    "response direction paths exceed point cap"
                )
        for closure in direction.closure_path_pairs:
            _require_exact_record_fields(
                closure,
                DirectionPathClosure,
                "response direction closure",
            )
        _require_exact_record_fields(
            bridge,
            BridgeKGridManifest,
            "source/readout bridge grid",
        )
        _bounded_tuple(
            bridge.reciprocal_indices,
            "source/readout bridge grid",
            BRIDGE_GRID_MAX_POINT_COUNT,
        )
        _bounded_tuple(
            entry.source_readout_bridge_steps,
            "source/readout bridge steps",
            16_384,
        )
        _bounded_tuple(
            entry.preregistered_phase_bands,
            "phase bands",
            RESPONSE_GRID_MAX_POINT_COUNT,
        )
        response.__post_init__()
        direction.__post_init__()
        for closure in direction.closure_path_pairs:
            closure.__post_init__()
        bridge.__post_init__()
        entry.__post_init__()
    return entries


def _control_applications(
    registry_view: object,
) -> tuple[V3M0SyntheticControlApplicationSpec, ...]:
    parent = _reverify_verified_parent_freeze(registry_view.parent)
    applications = parent.synthetic_control_application_specs[
        : len(CONTROL_ORDER)
    ]
    if (
        tuple(item.control_case_id for item in applications)
        != _CONTROL_APPLICATION_CASE_IDS
    ):
        raise ValueError(
            "parent C01-C03 application order is not the frozen mapping"
        )
    if len(applications) != len(CONTROL_ORDER):
        raise ValueError("parent does not contain all window controls")
    return applications


def _expected_control_entries(
    registry_view: object,
) -> tuple[ControlWindowProtocolEntry, ...]:
    registry = registry_view.registry
    applications = _control_applications(registry_view)
    entries: list[ControlWindowProtocolEntry] = []
    if len(registry_view.controls) != len(CONTROL_ORDER):
        raise ValueError("live registry control snapshots are incomplete")
    for control_id, registry_entry, control, application in zip(
        CONTROL_ORDER,
        registry.entries,
        registry_view.controls,
        applications,
    ):
        if type(registry_entry) is not ControlRegistryEntry:
            raise TypeError("registry entry has the wrong record type")
        if registry_entry.control_id != control_id:
            raise ValueError("registry entries are not in the closed order")
        grid = application.grid_protocol
        response_grid = build_response_grid_manifest(application)
        bridge_grid = build_application_bridge_grid_manifest(application)
        factory = _reverify_verified_factory(control.factory).factory
        factory_spatial_shape = tuple(factory.state_shape[1:])
        if (
            grid.spatial_shape != factory_spatial_shape
            or bridge_grid.spatial_shape != factory_spatial_shape
            or response_grid.torus_denominators
            != factory_spatial_shape
        ):
            raise ValueError(
                "registry factory spatial shape does not match "
                "the parent application grid"
            )
        source_dimension = len(registry_entry.source_basis.vectors_wire)
        preflight_source_bridge_work(
            n_k=len(bridge_grid.reciprocal_indices),
            n_trial=source_dimension,
            steps=grid.bridge_steps,
        )
        provisional = ControlWindowProtocolEntry(
            control_id=control_id,  # type: ignore[arg-type]
            control_registry_entry_sha=registry_entry.entry_sha,
            response_grid=response_grid,
            source_readout_bridge_grid=bridge_grid,
            source_readout_bridge_steps=grid.bridge_steps,
            reference_reciprocal_index=(
                grid.reference_reciprocal_index
            ),
            expected_shell_rank=grid.expected_shell_rank,
            expected_shell_rank_source_id=(
                grid.expected_shell_rank_source_id
            ),
            preregistered_phase_bands=(
                grid.preregistered_phase_bands
            ),
            source_trial_generation_id=SOURCE_TRIAL_GENERATION_ID,
            entry_sha="0" * 64,
        )
        entries.append(
            replace(
                provisional,
                entry_sha=canonical_sha(
                    control_window_protocol_entry_payload(provisional)
                ),
            )
        )
    return tuple(entries)


def _legacy_build_control_window_protocol_entries(
    registry: VerifiedControlRegistry,
) -> tuple[ControlWindowProtocolEntry, ...]:
    """Derive the three exact entry bodies from live registry + parent."""

    view = _reverify_verified_control_registry(registry)
    return _expected_control_entries(view)


def _expected_protocol(
    registry_view: object,
    control_entries: tuple[ControlWindowProtocolEntry, ...],
) -> WindowCalibrationProtocol:
    supplied = _preflight_entries(control_entries)
    expected_entries = _expected_control_entries(registry_view)
    if supplied != expected_entries:
        raise ValueError(
            "control_entries do not match live registry/application bodies"
        )
    registry = registry_view.registry
    provisional = WindowCalibrationProtocol(
        protocol_schema_version=WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION,
        control_registry_sha=registry.registry_sha,
        parent_freeze_sha=registry.parent_freeze_sha,
        t_candidates=T_CANDIDATES,
        control_entries=expected_entries,
        phase_grid_protocol_id=PHASE_GRID_PROTOCOL_ID,
        phase_separation_protocol_id=PHASE_SEPARATION_PROTOCOL_ID,
        participation_min_required=SHELL_PARTICIPATION_MIN,
        overlap_margin_required=OVERLAP_MARGIN_MIN,
        loop_residual_max=SHELL_LOOP_RESIDUAL_MAX,
        projector_residual_max=SHELL_PROJECTOR_RESIDUAL_MAX,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            window_calibration_protocol_payload(provisional)
        ),
    )


class VerifiedWindowCalibrationProtocol:
    """Opaque live authority for the unique pre-shell window protocol."""

    __slots__ = ("__protocol", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        protocol: WindowCalibrationProtocol,
        seal: str,
        *,
        _issuance_token=_ISSUANCE_TOKEN,
        _object_setattr=object.__setattr__,
        _type_error=TypeError,
    ) -> None:
        if token is not _issuance_token:
            raise _type_error(
                "VerifiedWindowCalibrationProtocol is module-issued only"
            )
        _object_setattr(
            self,
            "_VerifiedWindowCalibrationProtocol__protocol",
            protocol,
        )
        _object_setattr(
            self,
            "_VerifiedWindowCalibrationProtocol__token",
            token,
        )
        _object_setattr(
            self,
            "_VerifiedWindowCalibrationProtocol__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError(
            "VerifiedWindowCalibrationProtocol is immutable"
        )

    @property
    def protocol(self) -> WindowCalibrationProtocol:
        return _reverify_verified_window_calibration_protocol(self).protocol


@dataclass(frozen=True)
class _VerifiedWindowProtocolView:
    protocol: WindowCalibrationProtocol
    registry: VerifiedControlRegistry


@dataclass(frozen=True)
class _WindowProtocolAuthority:
    protocol: WindowCalibrationProtocol
    protocol_snapshot: WindowCalibrationProtocol
    expected_protocol_snapshot: WindowCalibrationProtocol
    registry: VerifiedControlRegistry
    seal: str
    canonical_body_sha: str


def _protocol_seal(
    protocol: WindowCalibrationProtocol,
    registry: VerifiedControlRegistry,
) -> str:
    _require_exact_record_fields(
        protocol,
        WindowCalibrationProtocol,
        "window protocol",
    )
    _preflight_entries(protocol.control_entries)
    view = _reverify_verified_control_registry(registry)
    expected = _expected_protocol(view, protocol.control_entries)
    if protocol != expected:
        raise ValueError("protocol does not match closed reconstruction")
    return canonical_sha(
        {
            "authority_schema_version": (
                "v3m0.verified-window-calibration-protocol.v1"
            ),
            "protocol": {
                **window_calibration_protocol_payload(protocol),
                "protocol_sha": protocol.protocol_sha,
            },
            "control_registry_sha": view.registry.registry_sha,
            "parent_freeze_sha": view.registry.parent_freeze_sha,
        }
    )


def _make_window_protocol_authority(
    seal_protocol: Callable[
        [WindowCalibrationProtocol, VerifiedControlRegistry],
        str,
    ] = _protocol_seal,
    exact_fields: Callable[[object, type[object], str], None] = (
        _require_exact_record_fields
    ),
    preflight_entries: Callable[
        [tuple[ControlWindowProtocolEntry, ...]],
        tuple[ControlWindowProtocolEntry, ...],
    ] = _preflight_entries,
    clone_protocol: Callable[
        [WindowCalibrationProtocol],
        WindowCalibrationProtocol,
    ] = deepcopy,
    reverify_registry: Callable = _reverify_verified_control_registry,
    reverify_parent: Callable = _reverify_verified_parent_freeze,
    control_order: tuple[str, ...] = tuple(CONTROL_ORDER),
) -> tuple[
    Callable[
        [WindowCalibrationProtocol, VerifiedControlRegistry],
        VerifiedWindowCalibrationProtocol,
    ],
    Callable[
        [VerifiedWindowCalibrationProtocol],
        _VerifiedWindowProtocolView,
    ],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedWindowCalibrationProtocol],
            _WindowProtocolAuthority,
        ],
    ] = {}
    lock = threading.RLock()

    def issue(
        protocol: WindowCalibrationProtocol,
        registry: VerifiedControlRegistry,
    ) -> VerifiedWindowCalibrationProtocol:
        exact_fields(
            protocol,
            WindowCalibrationProtocol,
            "window protocol",
        )
        preflight_entries(protocol.control_entries)
        protocol_snapshot = clone_protocol(protocol)
        seal = seal_protocol(protocol_snapshot, registry)
        wrapper = VerifiedWindowCalibrationProtocol(
            _ISSUANCE_TOKEN,
            protocol,
            seal,
        )
        identity = id(wrapper)
        authority = _WindowProtocolAuthority(
            protocol=protocol,
            protocol_snapshot=protocol_snapshot,
            registry=registry,
            seal=seal,
        )

        def remove(
            reference: weakref.ReferenceType[
                VerifiedWindowCalibrationProtocol
            ],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        return wrapper

    def reverify(
        wrapper: VerifiedWindowCalibrationProtocol,
    ) -> _VerifiedWindowProtocolView:
        if type(wrapper) is not VerifiedWindowCalibrationProtocol:
            raise TypeError(
                "runtime requires a module-issued "
                "VerifiedWindowCalibrationProtocol"
            )
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError(
                    "VerifiedWindowCalibrationProtocol identity is not live"
                )
            authority = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedWindowCalibrationProtocol__token",
            )
            raw = object.__getattribute__(
                wrapper,
                "_VerifiedWindowCalibrationProtocol__protocol",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedWindowCalibrationProtocol__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "VerifiedWindowCalibrationProtocol record is incomplete"
            ) from exc
        if token is not _ISSUANCE_TOKEN:
            raise ValueError(
                "VerifiedWindowCalibrationProtocol token mismatch"
            )
        exact_fields(
            raw,
            WindowCalibrationProtocol,
            "window protocol",
        )
        preflight_entries(raw.control_entries)
        if (
            raw is not authority.protocol
            or raw != authority.protocol_snapshot
            or seal != authority.seal
        ):
            raise ValueError(
                "VerifiedWindowCalibrationProtocol seal mismatch"
            )
        registry_view = reverify_registry(authority.registry)
        parent = reverify_parent(registry_view.parent)
        if (
            registry_view.registry.registry_sha
            != authority.protocol_snapshot.control_registry_sha
            or parent.parent_freeze_sha
            != authority.protocol_snapshot.parent_freeze_sha
            or tuple(
                entry.control_id
                for entry in authority.protocol_snapshot.control_entries
            )
            != control_order
            or tuple(
                entry.entry_sha
                for entry in registry_view.registry.entries
            )
            != tuple(
                entry.control_registry_entry_sha
                for entry in authority.protocol_snapshot.control_entries
            )
        ):
            raise ValueError(
                "VerifiedWindowCalibrationProtocol live source mismatch"
            )
        return _VerifiedWindowProtocolView(
            protocol=authority.protocol,
            registry=authority.registry,
        )

    return issue, reverify


(
    _issue_verified_window_calibration_protocol,
    _reverify_verified_window_calibration_protocol,
) = _make_window_protocol_authority()


def _verify_protocol_raw_body(
    protocol: WindowCalibrationProtocol,
    registry_view: object,
) -> WindowCalibrationProtocol:
    _require_exact_record_fields(
        protocol,
        WindowCalibrationProtocol,
        "window protocol",
    )
    _preflight_entries(protocol.control_entries)
    protocol.__post_init__()
    if (
        protocol.protocol_schema_version
        != WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION
    ):
        raise ValueError("unexpected window protocol schema")
    if tuple(WindowCalibrationProtocol.__dataclass_fields__) != (
        "protocol_schema_version",
        "control_registry_sha",
        "parent_freeze_sha",
        "t_candidates",
        "control_entries",
        "phase_grid_protocol_id",
        "phase_separation_protocol_id",
        "participation_min_required",
        "overlap_margin_required",
        "loop_residual_max",
        "projector_residual_max",
        "protocol_sha",
    ):
        raise RuntimeError("window protocol field registry is incomplete")
    if tuple(ControlWindowProtocolEntry.__dataclass_fields__) != (
        "control_id",
        "control_registry_entry_sha",
        "response_grid",
        "source_readout_bridge_grid",
        "source_readout_bridge_steps",
        "reference_reciprocal_index",
        "expected_shell_rank",
        "expected_shell_rank_source_id",
        "preregistered_phase_bands",
        "source_trial_generation_id",
        "entry_sha",
    ):
        raise RuntimeError(
            "control window entry field registry is incomplete"
        )
    for control_id, entry, application in zip(
        CONTROL_ORDER,
        protocol.control_entries,
        _control_applications(registry_view),
    ):
        if entry.control_id != control_id:
            raise ValueError(
                "control window entries are not in registry order"
            )
        verify_response_grid_manifest(entry.response_grid, application)
        verify_application_bridge_grid_manifest(
            entry.source_readout_bridge_grid,
            application,
        )
        if entry.entry_sha != canonical_sha(
            control_window_protocol_entry_payload(entry)
        ):
            raise ValueError("entry_sha does not match complete body")
    if protocol.protocol_sha != canonical_sha(
        window_calibration_protocol_payload(protocol)
    ):
        raise ValueError("protocol_sha does not match complete body")
    expected = _expected_protocol(
        registry_view,
        protocol.control_entries,
    )
    if protocol != expected:
        raise ValueError(
            "protocol is not the unique live registry/application freeze"
        )
    return protocol


def _legacy_build_window_calibration_protocol(
    registry: VerifiedControlRegistry,
    control_entries: tuple[ControlWindowProtocolEntry, ...],
) -> VerifiedWindowCalibrationProtocol:
    """Freeze the unique Task 11 protocol before any shell is measured."""

    entries = _preflight_entries(control_entries)
    view = _reverify_verified_control_registry(registry)
    protocol = _expected_protocol(view, entries)
    return _issue_verified_window_calibration_protocol(
        protocol,
        registry,
    )


def _legacy_verify_window_calibration_protocol(
    protocol: WindowCalibrationProtocol,
    registry: VerifiedControlRegistry,
) -> VerifiedWindowCalibrationProtocol:
    """Hydrate a raw protocol only by replaying the live closed registry."""

    _require_exact_record_fields(
        protocol,
        WindowCalibrationProtocol,
        "window protocol",
    )
    _preflight_entries(protocol.control_entries)
    view = _reverify_verified_control_registry(registry)
    verified = _verify_protocol_raw_body(protocol, view)
    return _issue_verified_window_calibration_protocol(
        verified,
        registry,
    )


def _make_closed_window_api(
    *,
    protocol_type=WindowCalibrationProtocol,
    entry_type=ControlWindowProtocolEntry,
    verified_type=VerifiedWindowCalibrationProtocol,
    view_type=_VerifiedWindowProtocolView,
    authority_type=_WindowProtocolAuthority,
    registry_type=VerifiedControlRegistry,
    registry_entry_type=ControlRegistryEntry,
    response_type=ResponseKGridManifest,
    direction_type=DirectionManifest,
    closure_type=DirectionPathClosure,
    bridge_type=BridgeKGridManifest,
    application_type=V3M0SyntheticControlApplicationSpec,
    canonical_hash=canonical_sha,
    response_payload=response_grid_payload,
    bridge_payload=bridge_grid_payload,
    response_builder=build_response_grid_manifest,
    bridge_builder=build_application_bridge_grid_manifest,
    response_verifier=verify_response_grid_manifest,
    bridge_verifier=verify_application_bridge_grid_manifest,
    registry_reverifier=_reverify_verified_control_registry,
    parent_reverifier=_reverify_verified_parent_freeze,
    factory_reverifier=_reverify_verified_factory,
    source_work_preflight=preflight_source_bridge_work,
    threshold_verifier=verify_window_protocol_thresholds,
    body_preflight=_preflight_general_evidence_value,
    body_byte_cap=GENERAL_EVIDENCE_BODY_BYTES_MAX,
    spatial_preflight=_preflight_spatial_dimension,
    vector_preflight=_preflight_vector_dimension,
    clone=deepcopy,
    replace_record=replace,
    weak_reference=weakref.ref,
    lock_builder=threading.RLock,
    schema_version=WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION,
    authority_schema_version=(
        "v3m0.verified-window-calibration-protocol.v1"
    ),
    control_order=tuple(CONTROL_ORDER),
    application_case_ids=_CONTROL_APPLICATION_CASE_IDS,
    t_candidates=tuple(T_CANDIDATES),
    phase_grid_protocol_id=PHASE_GRID_PROTOCOL_ID,
    phase_separation_protocol_id=PHASE_SEPARATION_PROTOCOL_ID,
    participation_min=SHELL_PARTICIPATION_MIN,
    overlap_min=OVERLAP_MARGIN_MIN,
    loop_residual_max=SHELL_LOOP_RESIDUAL_MAX,
    projector_residual_max=SHELL_PROJECTOR_RESIDUAL_MAX,
    expected_rank_source_id=EXPECTED_SHELL_RANK_SOURCE_ID,
    source_trial_id=SOURCE_TRIAL_GENERATION_ID,
    response_point_cap=RESPONSE_GRID_MAX_POINT_COUNT,
    bridge_point_cap=BRIDGE_GRID_MAX_POINT_COUNT,
    issuance_token=_ISSUANCE_TOKEN,
    text_validator=_text,
    sha_validator=_sha,
    positive_integer=_positive_int,
    index_validator=_index,
    phase_validator=_phase_bands,
    type_fn=type,
    tuple_type=tuple,
    list_type=list,
    len_fn=len,
    zip_fn=zip,
    enumerate_fn=enumerate,
    getattr_fn=getattr,
    vars_fn=vars,
    frozenset_type=frozenset,
    sorted_fn=sorted,
    set_type=set,
    object_type=object,
    id_fn=id,
    weakref_type=weakref.ReferenceType,
    type_error=TypeError,
    value_error=ValueError,
    runtime_error=RuntimeError,
    attribute_error=AttributeError,
):
    protocol_fields = (
        "protocol_schema_version",
        "control_registry_sha",
        "parent_freeze_sha",
        "t_candidates",
        "control_entries",
        "phase_grid_protocol_id",
        "phase_separation_protocol_id",
        "participation_min_required",
        "overlap_margin_required",
        "loop_residual_max",
        "projector_residual_max",
        "protocol_sha",
    )
    entry_fields = (
        "control_id",
        "control_registry_entry_sha",
        "response_grid",
        "source_readout_bridge_grid",
        "source_readout_bridge_steps",
        "reference_reciprocal_index",
        "expected_shell_rank",
        "expected_shell_rank_source_id",
        "preregistered_phase_bands",
        "source_trial_generation_id",
        "entry_sha",
    )

    def exact_record_fields(record, record_type, field):
        if type_fn(record) is not record_type:
            raise type_error(f"{field} has the wrong record type")
        expected = frozenset_type(record_type.__dataclass_fields__)
        try:
            observed = frozenset_type(vars_fn(record))
        except type_error as exc:
            raise type_error(f"{field} has no strict record body") from exc
        if observed != expected:
            raise value_error(
                f"{field} fields are not exact: "
                f"missing={sorted_fn(expected - observed)!r}, "
                f"unknown={sorted_fn(observed - expected)!r}"
            )

    def bounded_tuple(value, field, cap):
        if type_fn(value) is not tuple_type:
            raise type_error(f"{field} must be a tuple")
        if len_fn(value) > cap:
            raise value_error(f"{field} exceeds point cap")
        return value

    def response_grid_record(grid):
        return {
            **response_payload(grid),
            "response_grid_sha": grid.response_grid_sha,
        }

    def bridge_grid_record(grid):
        return {
            **bridge_payload(grid),
            "bridge_grid_sha": grid.bridge_grid_sha,
        }

    def entry_payload(entry):
        if type_fn(entry) is not entry_type:
            raise type_error(
                "entry must be a ControlWindowProtocolEntry"
            )
        return {
            "control_id": entry.control_id,
            "control_registry_entry_sha": (
                entry.control_registry_entry_sha
            ),
            "response_grid": response_grid_record(entry.response_grid),
            "source_readout_bridge_grid": bridge_grid_record(
                entry.source_readout_bridge_grid
            ),
            "source_readout_bridge_steps": list_type(
                entry.source_readout_bridge_steps
            ),
            "reference_reciprocal_index": list_type(
                entry.reference_reciprocal_index
            ),
            "expected_shell_rank": entry.expected_shell_rank,
            "expected_shell_rank_source_id": (
                entry.expected_shell_rank_source_id
            ),
            "preregistered_phase_bands": [
                list_type(item)
                for item in entry.preregistered_phase_bands
            ],
            "source_trial_generation_id": (
                entry.source_trial_generation_id
            ),
        }

    def entry_record(entry):
        return {
            **entry_payload(entry),
            "entry_sha": entry.entry_sha,
        }

    def protocol_payload(protocol):
        if type_fn(protocol) is not protocol_type:
            raise type_error(
                "protocol must be a WindowCalibrationProtocol"
            )
        return {
            "protocol_schema_version": protocol.protocol_schema_version,
            "control_registry_sha": protocol.control_registry_sha,
            "parent_freeze_sha": protocol.parent_freeze_sha,
            "t_candidates": list_type(protocol.t_candidates),
            "control_entries": [
                entry_record(item)
                for item in protocol.control_entries
            ],
            "phase_grid_protocol_id": protocol.phase_grid_protocol_id,
            "phase_separation_protocol_id": (
                protocol.phase_separation_protocol_id
            ),
            "participation_min_required": (
                protocol.participation_min_required
            ),
            "overlap_margin_required": (
                protocol.overlap_margin_required
            ),
            "loop_residual_max": protocol.loop_residual_max,
            "projector_residual_max": (
                protocol.projector_residual_max
            ),
        }

    def preflight_entries(entries):
        if type_fn(entries) is not tuple_type:
            raise type_error("control_entries must be a tuple")
        if len_fn(entries) != len_fn(control_order):
            raise value_error(
                "control_entries must contain exactly three controls"
            )
        body_preflight(
            entries,
            "window control entries evidence",
            byte_cap=body_byte_cap,
        )
        for entry in entries:
            exact_record_fields(
                entry,
                entry_type,
                "control window entry",
            )
            response = entry.response_grid
            bridge = entry.source_readout_bridge_grid
            exact_record_fields(
                response,
                response_type,
                "response grid",
            )
            bounded_tuple(
                response.reciprocal_indices,
                "response grid",
                response_point_cap,
            )
            direction = response.direction_manifest
            exact_record_fields(
                direction,
                direction_type,
                "response direction manifest",
            )
            for field, label in (
                ("direction_ids", "response directions"),
                ("primitive_directions", "response directions"),
                ("path_ids", "response direction paths"),
                ("ordered_paths", "response direction paths"),
                ("closure_path_pairs", "response closures"),
            ):
                bounded_tuple(
                    getattr_fn(direction, field),
                    label,
                    response_point_cap,
                )
            total_path_points = 0
            for path in direction.ordered_paths:
                if type_fn(path) is not tuple_type:
                    raise type_error(
                        "response ordered_paths entries must be tuples"
                    )
                total_path_points += len_fn(path)
                if total_path_points > response_point_cap:
                    raise value_error(
                        "response direction paths exceed point cap"
                    )
            for closure in direction.closure_path_pairs:
                exact_record_fields(
                    closure,
                    closure_type,
                    "response direction closure",
                )
            exact_record_fields(
                bridge,
                bridge_type,
                "source/readout bridge grid",
            )
            bounded_tuple(
                bridge.reciprocal_indices,
                "source/readout bridge grid",
                bridge_point_cap,
            )
            bounded_tuple(
                entry.source_readout_bridge_steps,
                "source/readout bridge steps",
                16_384,
            )
            bounded_tuple(
                entry.preregistered_phase_bands,
                "phase bands",
                response_point_cap,
            )
            ndim = spatial_preflight(
                response.spatial_ndim,
                (response.torus_denominators,),
                "response grid",
            )
            for index, point in enumerate_fn(
                response.reciprocal_indices
            ):
                vector_preflight(
                    point,
                    ndim,
                    f"response grid point[{index}]",
                )
            for index, primitive in enumerate_fn(
                direction.primitive_directions
            ):
                vector_preflight(
                    primitive,
                    ndim,
                    f"response primitive direction[{index}]",
                )
            for path_index, path in enumerate_fn(
                direction.ordered_paths
            ):
                for point_index, point in enumerate_fn(path):
                    vector_preflight(
                        point,
                        ndim,
                        f"response path[{path_index}][{point_index}]",
                    )
            for index, closure in enumerate_fn(
                direction.closure_path_pairs
            ):
                vector_preflight(
                    closure.reciprocal_index,
                    ndim,
                    f"response closure[{index}]",
                )
            bridge_ndim = spatial_preflight(
                len_fn(bridge.spatial_shape)
                if type_fn(bridge.spatial_shape) is tuple_type
                else bridge.spatial_shape,
                (
                    bridge.spatial_shape,
                    bridge.torus_denominators,
                ),
                "source/readout bridge grid",
            )
            for index, point in enumerate_fn(
                bridge.reciprocal_indices
            ):
                vector_preflight(
                    point,
                    bridge_ndim,
                    f"source/readout bridge point[{index}]",
                )
            vector_preflight(
                entry.reference_reciprocal_index,
                ndim,
                "reference_reciprocal_index",
            )
            body_preflight(
                entry,
                "control window entry evidence",
                byte_cap=body_byte_cap,
            )
            response.__post_init__()
            direction.__post_init__()
            for closure in direction.closure_path_pairs:
                closure.__post_init__()
            bridge.__post_init__()
            entry.__post_init__()
        return entries

    def preflight_protocol(protocol):
        exact_record_fields(
            protocol,
            protocol_type,
            "window protocol",
        )
        body_preflight(
            protocol,
            "window protocol evidence",
            byte_cap=body_byte_cap,
        )
        preflight_entries(protocol.control_entries)
        protocol.__post_init__()
        if protocol.protocol_schema_version != schema_version:
            raise value_error("unexpected window protocol schema")
        if tuple_type(protocol_type.__dataclass_fields__) != protocol_fields:
            raise runtime_error(
                "window protocol field registry is incomplete"
            )
        if tuple_type(entry_type.__dataclass_fields__) != entry_fields:
            raise runtime_error(
                "control window entry field registry is incomplete"
            )
        threshold_verifier(
            t_candidates=protocol.t_candidates,
            phase_grid_protocol_id=protocol.phase_grid_protocol_id,
            phase_separation_protocol_id=(
                protocol.phase_separation_protocol_id
            ),
            participation_min_required=(
                protocol.participation_min_required
            ),
            overlap_margin_required=(
                protocol.overlap_margin_required
            ),
            loop_residual_max=protocol.loop_residual_max,
            projector_residual_max=protocol.projector_residual_max,
        )
        return protocol

    def control_applications(registry_view):
        parent = parent_reverifier(registry_view.parent)
        applications = parent.synthetic_control_application_specs[
            : len_fn(control_order)
        ]
        observed_ids = tuple_type(
            item.control_case_id for item in applications
        )
        if observed_ids != application_case_ids:
            raise value_error(
                "parent C01-C03 application order is not the frozen mapping"
            )
        if len_fn(applications) != len_fn(control_order):
            raise value_error(
                "parent does not contain all window controls"
            )
        for application in applications:
            if type_fn(application) is not application_type:
                raise type_error(
                    "parent application has the wrong record type"
                )
        return applications

    def expected_control_entries(registry_view):
        registry_record = registry_view.registry
        applications = control_applications(registry_view)
        entries = list_type()
        if len_fn(registry_view.controls) != len_fn(control_order):
            raise value_error(
                "live registry control snapshots are incomplete"
            )
        for (
            control_id,
            registry_entry,
            control,
            application,
        ) in zip_fn(
            control_order,
            registry_record.entries,
            registry_view.controls,
            applications,
        ):
            if type_fn(registry_entry) is not registry_entry_type:
                raise type_error(
                    "registry entry has the wrong record type"
                )
            if registry_entry.control_id != control_id:
                raise value_error(
                    "registry entries are not in the closed order"
                )
            grid = application.grid_protocol
            response_grid = response_builder(application)
            bridge_grid = bridge_builder(application)
            factory = factory_reverifier(control.factory).factory
            factory_spatial_shape = tuple_type(
                factory.state_shape[1:]
            )
            if (
                grid.spatial_shape != factory_spatial_shape
                or bridge_grid.spatial_shape != factory_spatial_shape
                or response_grid.torus_denominators
                != factory_spatial_shape
            ):
                raise value_error(
                    "registry factory spatial shape does not match "
                    "the parent application grid"
                )
            source_dimension = len_fn(
                registry_entry.source_basis.vectors_wire
            )
            source_work_preflight(
                n_k=len_fn(bridge_grid.reciprocal_indices),
                n_trial=source_dimension,
                steps=grid.bridge_steps,
            )
            provisional = entry_type(
                control_id=control_id,
                control_registry_entry_sha=registry_entry.entry_sha,
                response_grid=response_grid,
                source_readout_bridge_grid=bridge_grid,
                source_readout_bridge_steps=grid.bridge_steps,
                reference_reciprocal_index=(
                    grid.reference_reciprocal_index
                ),
                expected_shell_rank=grid.expected_shell_rank,
                expected_shell_rank_source_id=expected_rank_source_id,
                preregistered_phase_bands=(
                    grid.preregistered_phase_bands
                ),
                source_trial_generation_id=source_trial_id,
                entry_sha="0" * 64,
            )
            body_preflight(
                provisional,
                "control window entry evidence",
                byte_cap=body_byte_cap,
            )
            entries.append(
                replace_record(
                    provisional,
                    entry_sha=canonical_hash(
                        entry_payload(provisional)
                    ),
                )
            )
        answer = tuple_type(entries)
        preflight_entries(answer)
        return answer

    def expected_protocol(registry_view, control_entries):
        supplied = preflight_entries(control_entries)
        expected_entries = expected_control_entries(registry_view)
        if supplied != expected_entries:
            raise value_error(
                "control_entries do not match "
                "live registry/application bodies"
            )
        registry_record = registry_view.registry
        provisional = protocol_type(
            protocol_schema_version=schema_version,
            control_registry_sha=registry_record.registry_sha,
            parent_freeze_sha=registry_record.parent_freeze_sha,
            t_candidates=t_candidates,
            control_entries=expected_entries,
            phase_grid_protocol_id=phase_grid_protocol_id,
            phase_separation_protocol_id=(
                phase_separation_protocol_id
            ),
            participation_min_required=participation_min,
            overlap_margin_required=overlap_min,
            loop_residual_max=loop_residual_max,
            projector_residual_max=projector_residual_max,
            protocol_sha="0" * 64,
        )
        body_preflight(
            provisional,
            "window protocol evidence",
            byte_cap=body_byte_cap,
        )
        return replace_record(
            provisional,
            protocol_sha=canonical_hash(protocol_payload(provisional)),
        )

    def verify_raw_body(protocol, registry_view):
        preflight_protocol(protocol)
        applications = control_applications(registry_view)
        for control_id, entry, application in zip_fn(
            control_order,
            protocol.control_entries,
            applications,
        ):
            if entry.control_id != control_id:
                raise value_error(
                    "control window entries are not in registry order"
                )
            response_verifier(entry.response_grid, application)
            bridge_verifier(
                entry.source_readout_bridge_grid,
                application,
            )
            if entry.entry_sha != canonical_hash(
                entry_payload(entry)
            ):
                raise value_error(
                    "entry_sha does not match complete body"
                )
        if protocol.protocol_sha != canonical_hash(
            protocol_payload(protocol)
        ):
            raise value_error(
                "protocol_sha does not match complete body"
            )
        expected = expected_protocol(
            registry_view,
            protocol.control_entries,
        )
        if protocol != expected:
            raise value_error(
                "protocol is not the unique "
                "live registry/application freeze"
            )
        return protocol

    def protocol_seal(protocol, registry_view):
        verified = verify_raw_body(protocol, registry_view)
        body_preflight(
            (
                authority_schema_version,
                verified,
                registry_view.registry.registry_sha,
                registry_view.registry.parent_freeze_sha,
            ),
            "window authority evidence",
            byte_cap=body_byte_cap,
        )
        return canonical_hash(
            {
                "authority_schema_version": authority_schema_version,
                "protocol": {
                    **protocol_payload(verified),
                    "protocol_sha": verified.protocol_sha,
                },
                "control_registry_sha": (
                    registry_view.registry.registry_sha
                ),
                "parent_freeze_sha": (
                    registry_view.registry.parent_freeze_sha
                ),
            }
        )

    live = {}
    lock = lock_builder()

    def issue_with_view(protocol, registry, registry_view):
        verified = verify_raw_body(protocol, registry_view)
        reconstructed = expected_protocol(
            registry_view,
            verified.control_entries,
        )
        if verified != reconstructed:
            raise value_error(
                "protocol does not match closed reconstruction"
            )
        exposed = clone(verified)
        canonical_snapshot = clone(verified)
        expected_snapshot = clone(reconstructed)
        preflight_protocol(exposed)
        preflight_protocol(canonical_snapshot)
        preflight_protocol(expected_snapshot)
        canonical_body_sha = canonical_hash(
            protocol_payload(canonical_snapshot)
        )
        if (
            canonical_snapshot.protocol_sha != canonical_body_sha
            or expected_snapshot.protocol_sha != canonical_body_sha
        ):
            raise value_error(
                "window protocol canonical snapshot mismatch"
            )
        seal = protocol_seal(canonical_snapshot, registry_view)
        wrapper = verified_type(
            issuance_token,
            exposed,
            seal,
        )
        identity = id_fn(wrapper)
        authority = authority_type(
            protocol=exposed,
            protocol_snapshot=canonical_snapshot,
            expected_protocol_snapshot=expected_snapshot,
            registry=registry,
            seal=seal,
            canonical_body_sha=canonical_body_sha,
        )

        def remove(reference, wrapper_id=identity):
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weak_reference(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        return wrapper

    def reverify(wrapper):
        if type_fn(wrapper) is not verified_type:
            raise type_error(
                "runtime requires a module-issued "
                "VerifiedWindowCalibrationProtocol"
            )
        with lock:
            current = live.get(id_fn(wrapper))
            if current is None or current[0]() is not wrapper:
                raise value_error(
                    "VerifiedWindowCalibrationProtocol "
                    "identity is not live"
                )
            authority = current[1]
        try:
            token = object_type.__getattribute__(
                wrapper,
                "_VerifiedWindowCalibrationProtocol__token",
            )
            raw = object_type.__getattribute__(
                wrapper,
                "_VerifiedWindowCalibrationProtocol__protocol",
            )
            wrapper_seal = object_type.__getattribute__(
                wrapper,
                "_VerifiedWindowCalibrationProtocol__seal",
            )
        except attribute_error as exc:
            raise value_error(
                "VerifiedWindowCalibrationProtocol "
                "record is incomplete"
            ) from exc
        if token is not issuance_token:
            raise value_error(
                "VerifiedWindowCalibrationProtocol token mismatch"
            )
        preflight_protocol(raw)
        preflight_protocol(authority.protocol_snapshot)
        preflight_protocol(authority.expected_protocol_snapshot)
        if (
            raw is not authority.protocol
            or raw != authority.protocol_snapshot
            or raw != authority.expected_protocol_snapshot
        ):
            raise value_error(
                "VerifiedWindowCalibrationProtocol snapshot mismatch"
            )
        registry_view = registry_reverifier(authority.registry)
        verified_snapshot = verify_raw_body(
            authority.protocol_snapshot,
            registry_view,
        )
        expected_live = expected_protocol(
            registry_view,
            verified_snapshot.control_entries,
        )
        if (
            verified_snapshot != expected_live
            or authority.expected_protocol_snapshot != expected_live
            or raw != expected_live
        ):
            raise value_error(
                "VerifiedWindowCalibrationProtocol "
                "closed reconstruction mismatch"
            )
        raw_body_sha = canonical_hash(protocol_payload(raw))
        snapshot_body_sha = canonical_hash(
            protocol_payload(authority.protocol_snapshot)
        )
        expected_body_sha = canonical_hash(
            protocol_payload(authority.expected_protocol_snapshot)
        )
        if (
            raw_body_sha != authority.canonical_body_sha
            or snapshot_body_sha != authority.canonical_body_sha
            or expected_body_sha != authority.canonical_body_sha
            or raw.protocol_sha != authority.canonical_body_sha
            or authority.protocol_snapshot.protocol_sha
            != authority.canonical_body_sha
            or authority.expected_protocol_snapshot.protocol_sha
            != authority.canonical_body_sha
        ):
            raise value_error(
                "VerifiedWindowCalibrationProtocol "
                "canonical snapshot mismatch"
            )
        fresh_seal = protocol_seal(
            authority.protocol_snapshot,
            registry_view,
        )
        if (
            wrapper_seal != authority.seal
            or fresh_seal != authority.seal
        ):
            raise value_error(
                "VerifiedWindowCalibrationProtocol seal mismatch"
            )
        return view_type(
            protocol=raw,
            registry=authority.registry,
        )

    def build_control_entries(registry):
        if type_fn(registry) is not registry_type:
            raise type_error(
                "registry must be a VerifiedControlRegistry"
            )
        view = registry_reverifier(registry)
        return expected_control_entries(view)

    def build_protocol(registry, control_entries):
        preflight_entries(control_entries)
        if type_fn(registry) is not registry_type:
            raise type_error(
                "registry must be a VerifiedControlRegistry"
            )
        view = registry_reverifier(registry)
        protocol = expected_protocol(view, control_entries)
        return issue_with_view(protocol, registry, view)

    def verify_protocol(protocol, registry):
        preflight_protocol(protocol)
        if type_fn(registry) is not registry_type:
            raise type_error(
                "registry must be a VerifiedControlRegistry"
            )
        view = registry_reverifier(registry)
        verified = verify_raw_body(protocol, view)
        return issue_with_view(verified, registry, view)

    def issue_protocol(protocol, registry):
        preflight_protocol(protocol)
        if type_fn(registry) is not registry_type:
            raise type_error(
                "registry must be a VerifiedControlRegistry"
            )
        view = registry_reverifier(registry)
        verified = verify_raw_body(protocol, view)
        return issue_with_view(verified, registry, view)

    def protocol_property(wrapper):
        return reverify(wrapper).protocol

    return (
        build_control_entries,
        build_protocol,
        verify_protocol,
        issue_protocol,
        reverify,
        protocol_property,
    )


(
    build_control_window_protocol_entries,
    build_window_calibration_protocol,
    verify_window_calibration_protocol,
    _issue_verified_window_calibration_protocol,
    _reverify_verified_window_calibration_protocol,
    _closed_window_protocol_property,
) = _make_closed_window_api()

setattr(
    VerifiedWindowCalibrationProtocol,
    "protocol",
    property(_closed_window_protocol_property),
)


__all__ = [
    "WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION",
    "ControlWindowProtocolEntry",
    "VerifiedWindowCalibrationProtocol",
    "WindowCalibrationProtocol",
    "build_control_window_protocol_entries",
    "build_window_calibration_protocol",
    "control_window_protocol_entry_payload",
    "verify_window_calibration_protocol",
    "window_calibration_protocol_payload",
]
