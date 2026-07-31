"""Deterministic Task-8 control roots for the current Parent replay.

This module is an internal numerical/root adapter, not an authority issuer.
The public current-Parent entry point must first obtain the exact C01--C03
scenario authorities from a live :class:`VerifiedParentFreezeV2`; only then
may it call :func:`_replay_current_task8_control_roots`.

The legacy Parent capability below is retained as a numerical witness.  Every
current response contract is independently compared with the freshly rebuilt
controls, matched ablations, programs, effects, bases and grids, so merely
re-labelling a v1 SHA cannot satisfy this replay.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, fields as dataclass_fields, replace
import re
import threading
import weakref

import numpy as np

from .ablation import AblationConstructionOutcome, matched_ablation, verify_ablation_pair
from .controls import (
    SyntheticControlBundle,
    build_direct_sum_control,
    build_full_control,
    build_zero_control,
)
from .evidence import canonical_sha
from .factory import (
    PrimitiveInterface,
    PrimitiveOperatorWire,
    basis_manifest_array,
    build_basis_manifest,
    build_calibration_seed,
    freeze_complex_tensor,
    freeze_synthetic_target,
    frozen_tensor_array,
    measure_calibration_holdout,
    primitive_payload,
    primitive_sha,
)
from .frozen_call_graph import freeze_rulespace_call_graph
from .grids import (
    build_application_bridge_grid_manifest,
    build_response_grid_manifest,
)
from .parent_freeze import (
    VerifiedParentFreeze,
    _reverify_verified_parent_freeze,
    issue_v3m0_parent_freeze,
)
from .parent_v2_contracts import CurrentScenarioAuthorityV2
from .registry import (
    ControlRegistryEntry,
    VerifiedControlRegistry,
    build_closed_control_registry,
    control_registry_entry_payload,
)


_TASK8_CASES = (
    ("C01_BLIND_HOLDOUT_FULL", "full"),
    ("C02_CONDITIONED_ZERO", "zero"),
    ("C03_EQUAL_RANK_DIRECT_SUM", "direct_sum"),
)
CURRENT_CONTROL_REGISTRY_ENTRY_V2_SCHEMA_VERSION = (
    "v3m0.current-control-registry-entry.v2"
)
CURRENT_CONTROL_REGISTRY_V2_SCHEMA_VERSION = "v3m0.current-control-registry.v2"
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")


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
class CurrentControlRegistryEntryV2:
    entry_schema_version: str
    parent_freeze_v2_sha: str
    control_case_id: str
    control_id: str
    scenario_id: str
    scenario_authority_sha: str
    response_contract_sha: str
    legacy_registry_entry: ControlRegistryEntry
    actual_factory_sha: str
    matched_ablated_factory_sha: str
    actual_program_sha: str
    matched_ablated_program_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    actual_step_count: int
    matched_ablated_step_count: int
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int
    entry_sha: str

    def __post_init__(
        self,
        _schema=CURRENT_CONTROL_REGISTRY_ENTRY_V2_SCHEMA_VERSION,
        _sha_validator=_sha,
        _text_validator=_text,
        _record_validator=_exact_record,
        _legacy_type=ControlRegistryEntry,
        _getattr=getattr,
        _type=type,
        _int_type=int,
        _value_error=ValueError,
    ) -> None:
        if (
            self.entry_schema_version
            != _schema
        ):
            raise _value_error("current control registry-entry schema drifted")
        _sha_validator(self.parent_freeze_v2_sha, "parent_freeze_v2_sha")
        for field in ("control_case_id", "control_id", "scenario_id"):
            _text_validator(_getattr(self, field), field)
        for field in (
            "scenario_authority_sha",
            "response_contract_sha",
            "actual_factory_sha",
            "matched_ablated_factory_sha",
            "actual_program_sha",
            "matched_ablated_program_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "entry_sha",
        ):
            _sha_validator(_getattr(self, field), field)
        _record_validator(
            self.legacy_registry_entry,
            _legacy_type,
            "legacy_registry_entry",
        )
        self.legacy_registry_entry.__post_init__()
        for field in (
            "actual_step_count",
            "matched_ablated_step_count",
            "expected_actual_shell_rank",
            "expected_matched_shell_rank",
        ):
            value = _getattr(self, field)
            if _type(value) is not _int_type or value < 0:
                raise _value_error(
                    f"{field} must be a non-negative exact integer"
                )


def current_control_registry_entry_v2_payload(
    entry: CurrentControlRegistryEntryV2,
) -> dict[str, object]:
    _exact_record(entry, CurrentControlRegistryEntryV2, "current registry entry")
    return {
        "entry_schema_version": entry.entry_schema_version,
        "parent_freeze_v2_sha": entry.parent_freeze_v2_sha,
        "control_case_id": entry.control_case_id,
        "control_id": entry.control_id,
        "scenario_id": entry.scenario_id,
        "scenario_authority_sha": entry.scenario_authority_sha,
        "response_contract_sha": entry.response_contract_sha,
        "legacy_registry_entry": {
            **control_registry_entry_payload(entry.legacy_registry_entry),
            "entry_sha": entry.legacy_registry_entry.entry_sha,
        },
        "actual_factory_sha": entry.actual_factory_sha,
        "matched_ablated_factory_sha": entry.matched_ablated_factory_sha,
        "actual_program_sha": entry.actual_program_sha,
        "matched_ablated_program_sha": entry.matched_ablated_program_sha,
        "actual_effect_digest": entry.actual_effect_digest,
        "matched_ablated_effect_digest": entry.matched_ablated_effect_digest,
        "actual_step_count": entry.actual_step_count,
        "matched_ablated_step_count": entry.matched_ablated_step_count,
        "expected_actual_shell_rank": entry.expected_actual_shell_rank,
        "expected_matched_shell_rank": entry.expected_matched_shell_rank,
    }


@dataclass(frozen=True)
class CurrentControlRegistryV2:
    registry_schema_version: str
    parent_freeze_v2_sha: str
    historical_parent_v1_sha: str
    legacy_registry_sha: str
    entries: tuple[CurrentControlRegistryEntryV2, ...]
    registry_sha: str

    def __post_init__(
        self,
        _schema=CURRENT_CONTROL_REGISTRY_V2_SCHEMA_VERSION,
        _sha_validator=_sha,
        _cases=_TASK8_CASES,
        _entry_type=CurrentControlRegistryEntryV2,
        _getattr=getattr,
        _type=type,
        _tuple_type=tuple,
        _len=len,
        _all=all,
        _any=any,
        _type_error=TypeError,
        _value_error=ValueError,
    ) -> None:
        if self.registry_schema_version != _schema:
            raise _value_error("current control registry schema drifted")
        for field in (
            "parent_freeze_v2_sha",
            "historical_parent_v1_sha",
            "legacy_registry_sha",
            "registry_sha",
        ):
            _sha_validator(_getattr(self, field), field)
        if (
            _type(self.entries) is not _tuple_type
            or _len(self.entries) != _len(_cases)
            or not _all(_type(item) is _entry_type for item in self.entries)
        ):
            raise _type_error(
                "current registry entries must be the exact three-entry tuple"
            )
        if _tuple_type(item.control_case_id for item in self.entries) != _tuple_type(
            item[0] for item in _cases
        ):
            raise _value_error(
                "current registry entries are not in canonical C01-C03 order"
            )
        if _tuple_type(item.control_id for item in self.entries) != _tuple_type(
            item[1] for item in _cases
        ):
            raise _value_error("current registry control IDs are not canonical")
        if _any(
            item.parent_freeze_v2_sha != self.parent_freeze_v2_sha
            for item in self.entries
        ):
            raise _value_error(
                "current registry entry is spliced to another Parent-v2"
            )


def current_control_registry_v2_payload(
    registry: CurrentControlRegistryV2,
) -> dict[str, object]:
    _exact_record(registry, CurrentControlRegistryV2, "current control registry")
    return {
        "registry_schema_version": registry.registry_schema_version,
        "parent_freeze_v2_sha": registry.parent_freeze_v2_sha,
        "historical_parent_v1_sha": registry.historical_parent_v1_sha,
        "legacy_registry_sha": registry.legacy_registry_sha,
        "entries": [
            {
                **current_control_registry_entry_v2_payload(item),
                "entry_sha": item.entry_sha,
            }
            for item in registry.entries
        ],
    }


class CurrentControlRegistryV2Unavailable(RuntimeError):
    """The raw current registry exists, but its live Parent connector is locked."""


class VerifiedCurrentControlRegistryV2:
    """Opaque live registry whose body is replayed from the current Parent."""

    __slots__ = ("_registry_sha", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("current control registry v2 is issuer-only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("current control registry v2 is immutable")


@dataclass(frozen=True)
class CurrentTask8ControlCaseReplay:
    control_case_id: str
    control_id: str
    scenario_id: str
    scenario_authority_sha: str
    response_contract_sha: str
    legacy_registry_entry_sha: str
    actual_factory_sha: str
    matched_ablated_factory_sha: str
    actual_program_sha: str
    matched_ablated_program_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    actual_step_count: int
    matched_ablated_step_count: int
    expected_actual_shell_rank: int
    expected_matched_shell_rank: int


@dataclass(frozen=True)
class CurrentTask8ControlReplay:
    controls: tuple[SyntheticControlBundle, ...]
    legacy_registry: VerifiedControlRegistry
    matched_ablation_outcomes: tuple[AblationConstructionOutcome, ...]
    case_replays: tuple[CurrentTask8ControlCaseReplay, ...]


def _task8_program_sha(
    branch: str,
    steps: tuple[tuple[object, bool], ...],
) -> str:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("Task-8 program branch is not frozen")
    records: list[dict[str, object]] = []
    for primitive, target_conditioned in steps:
        if primitive.operation_id != "local_canonical_shear":
            raise ValueError("Task-8 program contains a non-shear primitive")
        records.append(
            {
                **primitive_payload(primitive),
                "primitive_sha": primitive_sha(primitive),
                "target_conditioned": target_conditioned,
            }
        )
    return canonical_sha(
        {
            "program_schema_version": (
                "v3m0.task8-channel-generic-local-shear-program.v1"
            ),
            "branch": branch,
            "steps": records,
        }
    )


def _task8_effect_digest(
    channel_order: tuple[str, ...],
    steps: tuple[tuple[object, bool], ...],
    branch: str,
) -> str:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("Task-8 effect branch is not frozen")
    channel_index = {channel: index for index, channel in enumerate(channel_order)}
    if len(channel_index) != len(channel_order):
        raise ValueError("Task-8 factory channel order repeats")
    spatial_ndim = len(steps[0][0].offset) if steps else 1
    zero = (0,) * spatial_ndim
    coefficients: dict[tuple[int, ...], np.ndarray] = {
        zero: np.eye(len(channel_order), dtype=np.complex128)
    }
    for primitive, _ in steps:
        source = channel_index[primitive.source_channel]
        destination = channel_index[primitive.destination_channel]
        coefficient = complex(*primitive.coefficient_wire)
        previous = {
            offset: np.asarray(matrix, dtype=np.complex128).copy()
            for offset, matrix in coefficients.items()
        }
        updated = {
            offset: np.asarray(matrix, dtype=np.complex128).copy()
            for offset, matrix in previous.items()
        }
        for offset, matrix in previous.items():
            shifted = tuple(
                left + right for left, right in zip(offset, primitive.offset)
            )
            contribution = np.zeros_like(matrix)
            contribution[destination] = coefficient * matrix[source]
            if shifted in updated:
                updated[shifted] += contribution
            else:
                updated[shifted] = contribution
        coefficients = updated
    support = tuple(sorted(coefficients))
    kernel = freeze_complex_tensor(
        np.stack(tuple(coefficients[offset] for offset in support), axis=0)
    )
    return canonical_sha(
        {
            "effect_schema_version": (
                "v3m0.task8-channel-generic-laurent-effect.v1"
            ),
            "branch": branch,
            "channel_order": list(channel_order),
            "support_offsets": [list(item) for item in support],
            "kernel_tensor_sha": kernel.tensor_sha,
        }
    )


def _build_task8_controls(
    parent: VerifiedParentFreeze,
) -> tuple[SyntheticControlBundle, ...]:
    manifest = _reverify_verified_parent_freeze(parent)
    applications = {
        item.control_case_id: item
        for item in manifest.synthetic_control_application_specs
    }
    c01 = applications[_TASK8_CASES[0][0]]
    spatial_shape = c01.grid_protocol.spatial_shape
    source = c01.basis_protocol.source_basis
    readout = c01.basis_protocol.readout_basis
    interface = PrimitiveInterface(
        interface_id="interface.synthetic.local-linear.v1",
        state_schema_id=source.state_schema_id,
        spatial_ndim=len(spatial_shape),
        channel_order=source.channel_order,
        dtype="complex128",
        backend="numpy",
    )
    holdout = build_basis_manifest(
        role="holdout_source",
        state_schema_id=source.state_schema_id,
        channel_order=source.channel_order,
        vectors=basis_manifest_array(source),
    )
    coefficients = (1.0, -1.0, 1.0)
    sources = (
        source.channel_order[0],
        source.channel_order[1],
        source.channel_order[0],
    )
    destinations = (
        source.channel_order[1],
        source.channel_order[0],
        source.channel_order[1],
    )
    operators = tuple(
        PrimitiveOperatorWire(
            mechanism_id=f"pair.000.shear.{layer}",
            production_id="local_canonical_shear",
            layer_slot_id=f"layer.000.{layer}",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=sources[layer],
            destination_channel=destinations[layer],
            offset=(0,) * interface.spatial_ndim,
            coefficient_wire=(coefficients[layer], 0.0),
        )
        for layer in range(3)
    )
    seed = build_calibration_seed(
        calibration_protocol_id="calibration.synthetic.v1",
        interface=interface,
        state_shape=(len(interface.channel_order), *spatial_shape),
        dt=0.25,
        target_blind_parameters=(("mass", 1.0),),
        source_basis=source,
        holdout_source_basis=holdout,
        readout_basis=readout,
        boundary_manifest_id="periodic-v1",
        operator_payload=operators,
    )
    observation = measure_calibration_holdout(seed)
    target = freeze_synthetic_target(seed, observation, "target.synthetic.v1")
    return (
        build_full_control(seed, observation, target),
        build_zero_control(1, target, spatial_shape, 0.25),
        build_direct_sum_control(1, target, spatial_shape, 0.25),
    )


def _verify_contract_against_replay(
    *,
    authority: CurrentScenarioAuthorityV2,
    parent_application,
    registry_entry,
    pair,
) -> CurrentTask8ControlCaseReplay:
    response = authority.response_contract
    actual_factory = pair.actual.factory
    conditioned = frozenset(
        item.mechanism_id for item in pair.manifest.replacements
    )
    actual_steps = tuple(
        (primitive, primitive.mechanism_id in conditioned)
        for primitive in actual_factory.primitives
    )
    matched_steps = tuple(item for item in actual_steps if not item[1])
    actual_program_sha = _task8_program_sha("actual", actual_steps)
    matched_program_sha = _task8_program_sha(
        "matched_ablated",
        matched_steps,
    )
    actual_effect_digest = _task8_effect_digest(
        actual_factory.channel_order,
        actual_steps,
        "actual",
    )
    matched_effect_digest = _task8_effect_digest(
        actual_factory.channel_order,
        matched_steps,
        "matched_ablated",
    )
    response_grid = build_response_grid_manifest(parent_application)
    bridge_grid = build_application_bridge_grid_manifest(parent_application)
    selector = response.selector_spec
    source_selector = frozen_tensor_array(selector.source_injection)
    readout_selector = frozen_tensor_array(selector.readout_coisometry)
    source_basis = basis_manifest_array(parent_application.basis_protocol.source_basis)
    readout_basis = basis_manifest_array(parent_application.basis_protocol.readout_basis)
    expected_trials = np.eye(source_basis.shape[0], dtype=np.complex128)
    observed_trials = frozen_tensor_array(response.source_trial_vectors)

    expected = (
        authority.source_disposition
        == "PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE"
        and authority.application_instance_id
        == parent_application.application_instance_id
        and authority.based_on_application_spec_sha
        == parent_application.application_spec_sha
        and authority.scenario_execution_spec
        in parent_application.scenario_execution_specs
        and registry_entry.source_basis
        == parent_application.basis_protocol.source_basis
        and registry_entry.readout_basis
        == parent_application.basis_protocol.readout_basis
        and actual_factory.factory_sha == registry_entry.factory_sha
        and pair.manifest.actual_factory_sha == registry_entry.factory_sha
        and response.selector_sha == selector.selector_sha
        and np.array_equal(source_selector, source_basis.T)
        and np.array_equal(readout_selector, readout_basis)
        and np.array_equal(observed_trials, expected_trials)
        and response.response_torus_denominators
        == response_grid.torus_denominators
        and response.response_reciprocal_indices
        == response_grid.reciprocal_indices
        and response.source_readout_bridge_reciprocal_indices
        == bridge_grid.reciprocal_indices
        and response.source_readout_bridge_steps
        == parent_application.grid_protocol.bridge_steps
        and response.reference_reciprocal_index
        == parent_application.grid_protocol.reference_reciprocal_index
        and response.preregistered_phase_bands
        == parent_application.grid_protocol.preregistered_phase_bands
        and response.expected_actual_shell_rank
        == registry_entry.expected_h_actual_rank
        and response.expected_matched_shell_rank
        == registry_entry.expected_h_ablated_rank
        and response.actual_step_count == len(actual_steps)
        and response.matched_ablated_step_count == len(matched_steps)
        and response.actual_program_sha == actual_program_sha
        and response.matched_ablated_program_sha == matched_program_sha
        and response.actual_effect_digest == actual_effect_digest
        and response.matched_ablated_effect_digest == matched_effect_digest
        and response.construction_family_id
        == "task8-channel-generic-local-canonical-shear-v1"
        and response.uses_global_fft_projection is False
        and response.uses_per_k_time_step_projector is False
    )
    if not expected:
        raise ValueError(
            f"{authority.control_case_id} current contract differs from fresh Task-8 replay"
        )
    return CurrentTask8ControlCaseReplay(
        control_case_id=authority.control_case_id,
        control_id=registry_entry.control_id,
        scenario_id=authority.scenario_id,
        scenario_authority_sha=authority.scenario_authority_sha,
        response_contract_sha=response.response_contract_sha,
        legacy_registry_entry_sha=registry_entry.entry_sha,
        actual_factory_sha=pair.actual.factory.factory_sha,
        matched_ablated_factory_sha=pair.ablated.factory.factory_sha,
        actual_program_sha=actual_program_sha,
        matched_ablated_program_sha=matched_program_sha,
        actual_effect_digest=actual_effect_digest,
        matched_ablated_effect_digest=matched_effect_digest,
        actual_step_count=len(actual_steps),
        matched_ablated_step_count=len(matched_steps),
        expected_actual_shell_rank=registry_entry.expected_h_actual_rank,
        expected_matched_shell_rank=registry_entry.expected_h_ablated_rank,
    )


def _replay_current_task8_control_roots(
    parent: VerifiedParentFreeze,
    current_scenario_authorities: tuple[CurrentScenarioAuthorityV2, ...],
) -> CurrentTask8ControlReplay:
    """Rebuild C01--C03 and compare them with exact reviewed current contracts."""

    if type(parent) is not VerifiedParentFreeze:
        raise TypeError("Task-8 replay requires the exact live historical Parent")
    if type(current_scenario_authorities) is not tuple or len(
        current_scenario_authorities
    ) != len(_TASK8_CASES):
        raise ValueError("Task-8 replay requires the canonical C01--C03 tuple")
    observed = tuple(
        item.control_case_id for item in current_scenario_authorities
    )
    expected_cases = tuple(item[0] for item in _TASK8_CASES)
    if observed != expected_cases:
        raise ValueError("Task-8 authority order is not canonical C01--C03")

    # The closed verifier is imported only at call time, allowing this helper
    # to be shared by parent_freeze_v2 without an import cycle.
    from .parent_freeze_v2 import verify_reviewed_unchanged_scenario_authority

    authorities = tuple(
        verify_reviewed_unchanged_scenario_authority(item)
        for item in current_scenario_authorities
    )
    parent_manifest = _reverify_verified_parent_freeze(parent)
    parent_applications = {
        item.control_case_id: item
        for item in parent_manifest.synthetic_control_application_specs
    }
    controls = _build_task8_controls(parent)
    registry = build_closed_control_registry(controls, parent)
    raw_registry = registry.registry
    outcomes: list[AblationConstructionOutcome] = []
    case_replays: list[CurrentTask8ControlCaseReplay] = []
    for authority, (case_id, control_id), control, entry in zip(
        authorities,
        _TASK8_CASES,
        controls,
        raw_registry.entries,
    ):
        if (
            authority.control_case_id != case_id
            or control.control_id != control_id
            or entry.control_id != control_id
        ):
            raise ValueError("Task-8 replay roots are cross-case spliced")
        outcome = matched_ablation(control.factory)
        if not outcome.status.defined or outcome.pair is None:
            raise ValueError("Task-8 matched ablation is unexpectedly undefined")
        pair = verify_ablation_pair(outcome.pair)
        case_replays.append(
            _verify_contract_against_replay(
                authority=authority,
                parent_application=parent_applications[case_id],
                registry_entry=entry,
                pair=pair,
            )
        )
        outcomes.append(outcome)
    return CurrentTask8ControlReplay(
        controls=controls,
        legacy_registry=registry,
        matched_ablation_outcomes=tuple(outcomes),
        case_replays=tuple(case_replays),
    )


def _build_current_control_registry_v2_body(
    parent_freeze_v2_sha: str,
    replay: CurrentTask8ControlReplay,
) -> CurrentControlRegistryV2:
    """Bind the fresh Task-8 replay to one current Parent-v2 root."""

    parent_sha = _sha(parent_freeze_v2_sha, "parent_freeze_v2_sha")
    if type(replay) is not CurrentTask8ControlReplay:
        raise TypeError("current registry requires an exact Task-8 replay")
    if (
        type(replay.case_replays) is not tuple
        or len(replay.case_replays) != len(_TASK8_CASES)
    ):
        raise ValueError("Task-8 replay does not contain the exact three cases")
    legacy = replay.legacy_registry.registry
    if len(legacy.entries) != len(_TASK8_CASES):
        raise ValueError("legacy Task-8 registry does not contain three entries")
    entries: list[CurrentControlRegistryEntryV2] = []
    for case, legacy_entry in zip(replay.case_replays, legacy.entries):
        if (
            case.control_id != legacy_entry.control_id
            or case.legacy_registry_entry_sha != legacy_entry.entry_sha
            or case.actual_factory_sha != legacy_entry.factory_sha
        ):
            raise ValueError("Task-8 case replay is spliced from its legacy entry")
        provisional = CurrentControlRegistryEntryV2(
            entry_schema_version=(
                CURRENT_CONTROL_REGISTRY_ENTRY_V2_SCHEMA_VERSION
            ),
            parent_freeze_v2_sha=parent_sha,
            control_case_id=case.control_case_id,
            control_id=case.control_id,
            scenario_id=case.scenario_id,
            scenario_authority_sha=case.scenario_authority_sha,
            response_contract_sha=case.response_contract_sha,
            legacy_registry_entry=legacy_entry,
            actual_factory_sha=case.actual_factory_sha,
            matched_ablated_factory_sha=case.matched_ablated_factory_sha,
            actual_program_sha=case.actual_program_sha,
            matched_ablated_program_sha=case.matched_ablated_program_sha,
            actual_effect_digest=case.actual_effect_digest,
            matched_ablated_effect_digest=case.matched_ablated_effect_digest,
            actual_step_count=case.actual_step_count,
            matched_ablated_step_count=case.matched_ablated_step_count,
            expected_actual_shell_rank=case.expected_actual_shell_rank,
            expected_matched_shell_rank=case.expected_matched_shell_rank,
            entry_sha="0" * 64,
        )
        entries.append(
            replace(
                provisional,
                entry_sha=canonical_sha(
                    current_control_registry_entry_v2_payload(provisional)
                ),
            )
        )
    provisional_registry = CurrentControlRegistryV2(
        registry_schema_version=CURRENT_CONTROL_REGISTRY_V2_SCHEMA_VERSION,
        parent_freeze_v2_sha=parent_sha,
        historical_parent_v1_sha=legacy.parent_freeze_sha,
        legacy_registry_sha=legacy.registry_sha,
        entries=tuple(entries),
        registry_sha="0" * 64,
    )
    return replace(
        provisional_registry,
        registry_sha=canonical_sha(
            current_control_registry_v2_payload(provisional_registry)
        ),
    )


def verify_current_control_registry_v2_body(
    registry: CurrentControlRegistryV2,
    parent_freeze_v2_sha: str,
    replay: CurrentTask8ControlReplay,
    *,
    _builder=_build_current_control_registry_v2_body,
) -> CurrentControlRegistryV2:
    """Validate an inert raw body; this function issues no capability."""

    _exact_record(registry, CurrentControlRegistryV2, "current control registry")
    registry.__post_init__()
    for index, entry in enumerate(registry.entries):
        _exact_record(
            entry,
            CurrentControlRegistryEntryV2,
            f"current control registry entry[{index}]",
        )
        entry.__post_init__()
        legacy_entry = entry.legacy_registry_entry
        if legacy_entry.entry_sha != canonical_sha(
            control_registry_entry_payload(legacy_entry)
        ):
            raise ValueError("legacy registry-entry SHA drifted")
        if entry.entry_sha != canonical_sha(
            current_control_registry_entry_v2_payload(entry)
        ):
            raise ValueError("current registry-entry SHA drifted")
    if registry.registry_sha != canonical_sha(
        current_control_registry_v2_payload(registry)
    ):
        raise ValueError("current control-registry SHA drifted")
    expected = _builder(
        parent_freeze_v2_sha,
        replay,
    )
    if registry != expected:
        raise ValueError("current control registry differs from fresh Task-8 replay")
    return registry


@dataclass(frozen=True)
class _LiveCurrentControlRegistryV2:
    parent_v2: object
    registry_sha: str


def _make_current_control_registry_v2_api(
    *,
    parent_type: type,
    parent_reverifier,
    replay_builder,
    body_builder=_build_current_control_registry_v2_body,
    body_verifier=verify_current_control_registry_v2_body,
    wrapper_type=VerifiedCurrentControlRegistryV2,
):
    """Freeze the sole issuer and consumer over the complete replay graph."""

    registry: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedCurrentControlRegistryV2],
            _LiveCurrentControlRegistryV2,
        ],
    ] = {}
    lock = threading.RLock()

    def _replay(parent_v2):
        if type(parent_v2) is not parent_type:
            raise TypeError("current registry requires an exact live current Parent")
        parent_manifest = parent_reverifier(parent_v2)
        parent_sha = _sha(
            parent_manifest.parent_freeze_v2_sha,
            "parent_freeze_v2_sha",
        )
        replay = replay_builder(parent_v2, parent_manifest)
        if type(replay) is not CurrentTask8ControlReplay:
            raise TypeError("current registry replay returned the wrong exact type")
        body = body_builder(parent_sha, replay)
        return body_verifier(body, parent_sha, replay), replay

    def _live_record(value):
        if type(value) is not wrapper_type:
            raise TypeError("current registry consumer requires its exact opaque type")
        with lock:
            current = registry.get(id(value))
            if current is None or current[0]() is not value:
                raise ValueError("current control-registry identity is not live")
            record = current[1]
        try:
            slot_sha = object.__getattribute__(value, "_registry_sha")
        except AttributeError as exc:
            raise ValueError("current control-registry record is incomplete") from exc
        if slot_sha != record.registry_sha:
            raise ValueError("current control-registry replay seal mismatch")
        return record

    def build_current_control_registry_v2(
        parent_v2,
    ) -> VerifiedCurrentControlRegistryV2:
        body, _ = _replay(parent_v2)
        wrapper = object.__new__(wrapper_type)
        object.__setattr__(wrapper, "_registry_sha", body.registry_sha)
        identity = id(wrapper)
        record = _LiveCurrentControlRegistryV2(
            parent_v2=parent_v2,
            registry_sha=body.registry_sha,
        )

        def remove_stale(
            reference: weakref.ReferenceType[VerifiedCurrentControlRegistryV2],
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
                raise RuntimeError("live current registry identity collision")
            registry[identity] = (reference, record)
        return wrapper

    def require_current_control_registry_v2(
        value: VerifiedCurrentControlRegistryV2,
    ) -> CurrentControlRegistryV2:
        record = _live_record(value)
        body, _ = _replay(record.parent_v2)
        if body.registry_sha != record.registry_sha:
            raise ValueError("current control-registry replay seal mismatch")
        return copy.deepcopy(body)

    def replay_current_control_registry_v2(
        value: VerifiedCurrentControlRegistryV2,
    ) -> tuple[CurrentControlRegistryV2, CurrentTask8ControlReplay]:
        """Private downstream bridge; return a fresh replay, never stored raw."""

        record = _live_record(value)
        body, replay = _replay(record.parent_v2)
        if body.registry_sha != record.registry_sha:
            raise ValueError("current control-registry replay seal mismatch")
        return copy.deepcopy(body), replay

    return (
        build_current_control_registry_v2,
        require_current_control_registry_v2,
        replay_current_control_registry_v2,
    )


def _make_current_parent_task8_replayer(
    *,
    historical_parent_issuer=issue_v3m0_parent_freeze,
    historical_parent_reverifier=_reverify_verified_parent_freeze,
    task8_replayer=_replay_current_task8_control_roots,
):
    """Capture the historical numerical witness and current authority selector."""

    def replay_current_parent_task8(parent_v2, parent_manifest):
        del parent_v2
        historical_parent = historical_parent_issuer()
        historical_manifest = historical_parent_reverifier(historical_parent)
        if historical_manifest != parent_manifest.historical_parent_v1:
            raise ValueError("current Parent historical numerical witness drifted")
        applications = {
            item.control_case_id: item
            for item in parent_manifest.current_application_authorities
        }
        if len(applications) != len(
            parent_manifest.current_application_authorities
        ):
            raise ValueError("current Parent application registry repeats a case")
        authorities = []
        for case_id, _ in _TASK8_CASES:
            application = applications.get(case_id)
            if application is None or len(application.scenario_authorities) != 1:
                raise ValueError(
                    "current Parent does not expose one Task-8 scenario authority"
                )
            authority = application.scenario_authorities[0]
            if authority.control_case_id != case_id:
                raise ValueError("current Parent Task-8 scenario is cross-case spliced")
            authorities.append(authority)
        return task8_replayer(historical_parent, tuple(authorities))

    return replay_current_parent_task8


_replay_current_parent_task8 = _make_current_parent_task8_replayer()

# Imported only after every local replay function exists.  This avoids an
# import cycle while still freezing the production Parent consumer into the
# closure returned below.
from .parent_authority import (  # noqa: E402
    VerifiedParentFreezeV2 as _VerifiedParentFreezeV2,
    require_current_parent as _require_current_parent,
)


(
    _raw_build_current_control_registry_v2,
    _raw_require_current_control_registry_v2,
    _raw_replay_current_control_registry_v2,
) = _make_current_control_registry_v2_api(
    parent_type=_VerifiedParentFreezeV2,
    parent_reverifier=_require_current_parent,
    replay_builder=_replay_current_parent_task8,
)


def _make_current_registry_property_binding():
    consumer_holder = []

    def current_registry_property(self):
        if len(consumer_holder) != 1:
            raise RuntimeError("current registry property is not bound exactly once")
        return consumer_holder[0](self)

    def bind(consumer):
        if consumer_holder:
            raise RuntimeError("current registry property is already bound")
        consumer_holder.append(consumer)

    return property(current_registry_property), bind


(
    _current_registry_property,
    _bind_current_registry_property,
) = _make_current_registry_property_binding()
VerifiedCurrentControlRegistryV2.registry = _current_registry_property
del _current_registry_property
del _make_current_registry_property_binding

build_current_control_registry_v2 = freeze_rulespace_call_graph(
    _raw_build_current_control_registry_v2
)
require_current_control_registry_v2 = freeze_rulespace_call_graph(
    _raw_require_current_control_registry_v2
)
_replay_current_control_registry_v2 = freeze_rulespace_call_graph(
    _raw_replay_current_control_registry_v2
)
del (
    _raw_build_current_control_registry_v2,
    _raw_require_current_control_registry_v2,
    _raw_replay_current_control_registry_v2,
)
_bind_current_registry_property(require_current_control_registry_v2)
del _bind_current_registry_property


__all__ = [
    "CURRENT_CONTROL_REGISTRY_ENTRY_V2_SCHEMA_VERSION",
    "CURRENT_CONTROL_REGISTRY_V2_SCHEMA_VERSION",
    "CurrentControlRegistryV2Unavailable",
    "CurrentControlRegistryEntryV2",
    "CurrentControlRegistryV2",
    "CurrentTask8ControlCaseReplay",
    "CurrentTask8ControlReplay",
    "VerifiedCurrentControlRegistryV2",
    "build_current_control_registry_v2",
    "current_control_registry_entry_v2_payload",
    "current_control_registry_v2_payload",
    "require_current_control_registry_v2",
]
