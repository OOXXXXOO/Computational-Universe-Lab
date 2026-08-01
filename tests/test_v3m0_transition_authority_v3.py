"""Strict RED contracts for the v7 Parent-v3 transition authority.

The tests deliberately keep B2, the new prestructure owner, and the dynamics
measurement seam as distinct authorities.  Synthetic fixtures replace only
those already-frozen boundaries; the transition owner itself is always the
production graph under test.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, fields, is_dataclass, replace
import inspect
from pathlib import Path
from types import SimpleNamespace
import weakref

import numpy as np
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
C19_STATE_SCHEMA_ID = "v3m0.c19-real-canonical-state.v2"
C19_CHANNEL_ORDER = tuple(
    channel for pair in range(10) for channel in (f"q{pair}", f"p{pair}")
)
C19_CHANNEL_PAIRS = tuple(
    (C19_CHANNEL_ORDER[index], C19_CHANNEL_ORDER[index + 1])
    for index in range(0, len(C19_CHANNEL_ORDER), 2)
)
C19_SPATIAL_SHAPE = (8,)
FAILURE_REASON_IDS = (
    "MATERIALIZATION_INVALID",
    "PRESTRUCTURE_INVALID",
    "EXECUTOR_FAILED",
    "TRANSITION_MEASUREMENT_FAILED",
    "SUPPORT_INVALID",
    "BRANCH_JOIN_FAILED",
    "CROSS_PARENT_ROOT",
)


@dataclass(frozen=True)
class _FakeFactoryBody:
    factory_sha: str
    target_spec_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    state_shape: tuple[int, ...]
    spatial_ndim: int
    dt: float
    boundary_manifest_id: str


class _FakeLiveFactory:
    __slots__ = ("factory", "role", "transition_kernel", "stencil_support")

    def __init__(
        self,
        factory: _FakeFactoryBody,
        role: str,
        transition_kernel: np.ndarray,
        stencil_support: tuple[tuple[int, ...], ...],
    ) -> None:
        self.factory = factory
        self.role = role
        self.transition_kernel = np.asarray(
            transition_kernel,
            dtype=np.complex128,
        ).copy()
        self.stencil_support = stencil_support


@dataclass(frozen=True)
class _FakeFactoryBinding:
    binding_schema_version: str
    parent_freeze_v3_sha: str
    permit_sha: str
    materialization_input_sha: str
    branch: str
    factory: _FakeFactoryBody
    construction_trace: object
    layer_slot_ids: tuple[str, ...]
    support_offsets: tuple[tuple[int, ...], ...]
    support_sha: str
    active_step_count: int
    layer_slot_count: int
    primitive_count: int
    neutral_identity_count: int
    binding_sha: str


@dataclass(frozen=True)
class _FakeCalibrationReplayRef:
    parent_freeze_v3_sha: str


@dataclass(frozen=True)
class _FakeCalibration:
    parent_freeze_v3_sha: str
    calibration_control_replay_refs: tuple[_FakeCalibrationReplayRef, ...]


@dataclass(frozen=True)
class _FakePermit:
    parent_freeze_v3_sha: str
    calibration: _FakeCalibration
    permit_sha: str


@dataclass(frozen=True)
class _FakeApplicationAuthority:
    state_schema_id: str
    channel_order: tuple[str, ...]
    state_shape: tuple[int, ...]
    spatial_shape: tuple[int, ...]
    target_spec_sha: str
    application_authority_sha: str


@dataclass(frozen=True)
class _FakeResponseContract:
    response_contract_sha: str


@dataclass(frozen=True)
class _FakeScenarioAuthority:
    response_contract: _FakeResponseContract
    scenario_authority_sha: str


@dataclass(frozen=True)
class _FakeBasisContract:
    state_schema_id: str
    channel_order: tuple[str, ...]
    state_shape: tuple[int, ...]
    spatial_shape: tuple[int, ...]
    basis_contract_sha: str


@dataclass(frozen=True)
class _FakePairSnapshot:
    actual_factory: _FakeFactoryBody
    matched_ablated_factory: _FakeFactoryBody
    actual_factory_sha: str
    matched_ablated_factory_sha: str
    snapshot_sha: str


@dataclass(frozen=True)
class _FakeMaterializationBody:
    materialization_schema_version: str
    permit: _FakePermit
    current_application_authority: _FakeApplicationAuthority
    current_scenario_authority: _FakeScenarioAuthority
    current_scenario_response_contract: _FakeResponseContract
    basis_contract: _FakeBasisContract
    construction_trace: object
    ablation_pair_snapshot: _FakePairSnapshot
    actual_factory_binding: _FakeFactoryBinding
    matched_ablated_factory_binding: _FakeFactoryBinding
    materialization_sha: str


class _FakeParentV3:
    __slots__ = ("manifest",)

    def __init__(self, parent_freeze_v3_sha: str) -> None:
        self.manifest = SimpleNamespace(
            parent_freeze_v3_sha=parent_freeze_v3_sha,
        )


class _FakeVerifiedMaterializationV3:
    __slots__ = ("parent", "_body")

    def __init__(
        self,
        parent: _FakeParentV3,
        body: _FakeMaterializationBody,
    ) -> None:
        self.parent = parent
        self._body = copy.deepcopy(body)

    @property
    def materialization(self) -> _FakeMaterializationBody:
        return copy.deepcopy(self._body)


@dataclass(frozen=True)
class _FakePrestructureBody:
    prestructure_schema_version: str
    parent_freeze_v3_sha: str
    permit_sha: str
    materialization_sha: str
    current_application_authority_v3_sha: str
    current_scenario_authority_v3_sha: str
    current_scenario_response_contract_v3_sha: str
    factory_binding: _FakeFactoryBinding
    factory_sha: str
    factory_role: str
    ablation_pair_snapshot: _FakePairSnapshot
    basis_contract: _FakeBasisContract
    evidence_lane: str
    target_spec_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    canonical_channel_pairs: tuple[tuple[str, str], ...]
    fourier_adjoint_convention_id: str
    structure_form: object
    reality_convention_id: str
    prestructure_authority_sha: str


class _FakeVerifiedPrestructure:
    __slots__ = ("__prestructure", "__weakref__")

    def __init__(self, body: _FakePrestructureBody) -> None:
        object.__setattr__(
            self,
            "_FakeVerifiedPrestructure__prestructure",
            copy.deepcopy(body),
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("fake prestructure capability is immutable")

    @property
    def prestructure(self) -> _FakePrestructureBody:
        return copy.deepcopy(
            object.__getattribute__(
                self,
                "_FakeVerifiedPrestructure__prestructure",
            )
        )


def _module():
    import rulespace_v3.transition_authority_v3 as facade

    return facade


def _canonical_block_j() -> np.ndarray:
    result = np.zeros((20, 20), dtype=np.complex128)
    for index in range(0, 20, 2):
        result[index, index + 1] = 1.0 + 0.0j
        result[index + 1, index] = -1.0 + 0.0j
    return result


def _kernel_pair() -> tuple[np.ndarray, np.ndarray]:
    actual = np.zeros((20, 20, 8), dtype=np.complex128)
    actual[:, :, 0] = np.eye(20, dtype=np.complex128)
    actual[1, 0, 1] = 0.125 + 0.0j
    actual[3, 2, 7] = -0.25 + 0.0j

    matched = np.zeros((20, 20, 8), dtype=np.complex128)
    matched[:, :, 0] = np.eye(20, dtype=np.complex128)
    matched[0, 1, 7] = -0.0625 + 0.0j
    return actual, matched


def _factory_step(factory: _FakeLiveFactory, state: np.ndarray) -> np.ndarray:
    if type(factory) is not _FakeLiveFactory:
        raise TypeError("executor requires the exact live B2 child factory")
    if type(state) is not np.ndarray or state.dtype != np.dtype(np.complex128):
        raise TypeError("executor state must be an exact complex128 ndarray")
    if state.shape != factory.factory.state_shape:
        raise ValueError("executor state shape drifted")
    if not np.isfinite(state).all():
        raise ValueError("executor state is non-finite")
    output = np.zeros_like(state)
    for source_position in range(state.shape[1]):
        source_vector = state[:, source_position]
        for displacement_index in range(state.shape[1]):
            destination = (source_position + displacement_index) % state.shape[1]
            output[:, destination] += (
                factory.transition_kernel[:, :, displacement_index] @ source_vector
            )
    return output


def _wire_tree(value: object) -> object:
    if is_dataclass(value):
        return {
            item.name: _wire_tree(getattr(value, item.name)) for item in fields(value)
        }
    if isinstance(value, SimpleNamespace):
        return {key: _wire_tree(item) for key, item in vars(value).items()}
    if type(value) is tuple:
        return [_wire_tree(item) for item in value]
    if type(value) is list:
        return [_wire_tree(item) for item in value]
    if type(value) is dict:
        return {key: _wire_tree(item) for key, item in value.items()}
    return value


def _body_payload(body: object, self_hash_field: str) -> dict[str, object]:
    if not is_dataclass(body):
        raise TypeError("fake payload requires a dataclass body")
    return {
        item.name: _wire_tree(getattr(body, item.name))
        for item in fields(body)
        if item.name != self_hash_field
    }


def _binding(
    *,
    parent_sha: str,
    role: str,
    factory: _FakeFactoryBody,
    stencil_support: tuple[tuple[int, ...], ...],
) -> _FakeFactoryBinding:
    from rulespace_v3.evidence import canonical_sha

    return _FakeFactoryBinding(
        binding_schema_version="v3m0.factory-branch-binding.v3",
        parent_freeze_v3_sha=parent_sha,
        permit_sha="b" * 64,
        materialization_input_sha="c" * 64,
        branch=role,
        factory=factory,
        construction_trace=SimpleNamespace(trace_sha="d" * 64),
        layer_slot_ids=tuple(f"slot.{index:02d}" for index in range(50)),
        support_offsets=stencil_support,
        support_sha=canonical_sha(
            {
                "branch": role,
                "support_offsets": [list(item) for item in stencil_support],
            }
        ),
        active_step_count=50 if role == "actual" else 30,
        layer_slot_count=50,
        primitive_count=50,
        neutral_identity_count=0 if role == "actual" else 20,
        binding_sha=("e" if role == "actual" else "f") * 64,
    )


def _assert_canonical_impulse_groups(
    calls: list[np.ndarray],
    factory: _FakeLiveFactory,
) -> None:
    assert calls
    assert len(calls) % len(C19_CHANNEL_ORDER) == 0
    for start in range(0, len(calls), len(C19_CHANNEL_ORDER)):
        group = calls[start : start + len(C19_CHANNEL_ORDER)]
        for source, observed in enumerate(group):
            expected = np.zeros(
                factory.factory.state_shape,
                dtype=np.complex128,
            )
            expected[(source, 0)] = 1.0 + 0.0j
            np.testing.assert_array_equal(observed, expected)


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    *,
    root: str = "a",
    fresh_factories: bool = False,
    measurement_attack: str | None = None,
    allow_secondary_materialization: bool = False,
):
    from rulespace_v3.application_materialization_v3 import (
        ApplicationMaterializationV3Failure,
    )
    from rulespace_v3.dynamics import (
        MeasuredTransition,
        freeze_complex_tensor,
        frozen_tensor_array,
        measured_transition_payload,
        transition_support_payload,
    )
    from rulespace_v3.evidence import canonical_sha

    facade = _module()
    parent_sha = root * 64
    parent = _FakeParentV3(parent_sha)
    actual_kernel, matched_kernel = _kernel_pair()
    actual_body = _FakeFactoryBody(
        factory_sha="1" * 64,
        target_spec_sha="8" * 64,
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        state_shape=(20, 8),
        spatial_ndim=1,
        dt=0.125,
        boundary_manifest_id="periodic-v1",
    )
    matched_body = replace(actual_body, factory_sha="2" * 64)
    kernels = {
        "actual": actual_kernel,
        "matched_ablated": matched_kernel,
    }
    stencil_supports = {
        "actual": ((-1,), (0,), (1,)),
        "matched_ablated": ((0,), (1,)),
    }

    def fresh_factory(role: str) -> _FakeLiveFactory:
        body = actual_body if role == "actual" else matched_body
        return _FakeLiveFactory(
            body,
            role,
            kernels[role],
            stencil_supports[role],
        )

    stable_factories = {
        "actual": fresh_factory("actual"),
        "matched_ablated": fresh_factory("matched_ablated"),
    }
    actual_binding = _binding(
        parent_sha=parent_sha,
        role="actual",
        factory=actual_body,
        stencil_support=stencil_supports["actual"],
    )
    matched_binding = _binding(
        parent_sha=parent_sha,
        role="matched_ablated",
        factory=matched_body,
        stencil_support=stencil_supports["matched_ablated"],
    )
    response = _FakeResponseContract("5" * 64)
    scenario = _FakeScenarioAuthority(response, "4" * 64)
    application = _FakeApplicationAuthority(
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        state_shape=(20, 8),
        spatial_shape=C19_SPATIAL_SHAPE,
        target_spec_sha="8" * 64,
        application_authority_sha="3" * 64,
    )
    basis = _FakeBasisContract(
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        state_shape=(20, 8),
        spatial_shape=C19_SPATIAL_SHAPE,
        basis_contract_sha="6" * 64,
    )
    pair = _FakePairSnapshot(
        actual_factory=actual_body,
        matched_ablated_factory=matched_body,
        actual_factory_sha=actual_body.factory_sha,
        matched_ablated_factory_sha=matched_body.factory_sha,
        snapshot_sha="7" * 64,
    )
    materialization_body = _FakeMaterializationBody(
        materialization_schema_version=("v3m0.application-scenario-materialization.v3"),
        permit=_FakePermit(
            parent_sha,
            _FakeCalibration(
                parent_sha,
                tuple(_FakeCalibrationReplayRef(parent_sha) for _ in range(3)),
            ),
            "b" * 64,
        ),
        current_application_authority=application,
        current_scenario_authority=scenario,
        current_scenario_response_contract=response,
        basis_contract=basis,
        construction_trace=SimpleNamespace(trace_sha="d" * 64),
        ablation_pair_snapshot=pair,
        actual_factory_binding=actual_binding,
        matched_ablated_factory_binding=matched_binding,
        materialization_sha="9" * 64,
    )
    materialization = _FakeVerifiedMaterializationV3(
        parent,
        materialization_body,
    )
    secondary_materialization = _FakeVerifiedMaterializationV3(
        parent,
        copy.deepcopy(materialization_body),
    )
    calls = SimpleNamespace(
        events=[],
        materialization=[],
        resolved_factories=[],
        prestructure_issued=[],
        prestructure_verified=[],
        prestructure_reverified=[],
        measurements=[],
        executor={"actual": [], "matched_ablated": []},
    )
    mode = {"value": None}

    def require_materialization(observed_parent, observed_materialization):
        calls.events.append("b2_owner_seam")
        calls.materialization.append((observed_parent, observed_materialization))
        if mode["value"] == "materialization":
            raise ApplicationMaterializationV3Failure(
                "PERMIT_INVALID",
                "forced B2 materialization replay failure",
            )
        if mode["value"] == "cross_parent":
            raise ApplicationMaterializationV3Failure(
                "CROSS_PARENT_ROOT",
                "forced B2 Parent root mismatch",
            )
        if type(observed_parent) is not _FakeParentV3:
            raise TypeError("exact live Parent-v3 required")
        if observed_parent is not parent:
            raise ApplicationMaterializationV3Failure(
                "CROSS_PARENT_ROOT",
                "Parent identity differs from the bound fixture",
            )
        if type(observed_materialization) is not _FakeVerifiedMaterializationV3:
            raise TypeError("exact live B2 materialization required")
        allowed_materializations = (
            (materialization, secondary_materialization)
            if allow_secondary_materialization
            else (materialization,)
        )
        if not any(
            observed_materialization is candidate
            for candidate in allowed_materializations
        ):
            raise ApplicationMaterializationV3Failure(
                "PERMIT_INVALID",
                "equal-copy or foreign materialization is not live",
            )
        if observed_materialization.parent is not observed_parent:
            raise ApplicationMaterializationV3Failure(
                "CROSS_PARENT_ROOT",
                "materialization belongs to another Parent identity",
            )
        body = observed_materialization.materialization
        if body != materialization_body:
            raise ApplicationMaterializationV3Failure(
                "PERMIT_INVALID",
                "materialization body drifted",
            )
        actual = (
            fresh_factory("actual") if fresh_factories else stable_factories["actual"]
        )
        matched = (
            fresh_factory("matched_ablated")
            if fresh_factories
            else stable_factories["matched_ablated"]
        )
        calls.resolved_factories.append((actual, matched))
        return SimpleNamespace(
            materialization=copy.deepcopy(body),
            actual_factory=actual,
            matched_ablated_factory=matched,
        )

    prestructure_registry: dict[int, tuple[object, object]] = {}

    def prestructure_payload(body):
        if type(body) is not _FakePrestructureBody:
            raise TypeError("exact fake Parent-v3 prestructure body required")
        return _body_payload(body, "prestructure_authority_sha")

    def build_prestructure(observed_parent, observed_materialization, role):
        if role not in ("actual", "matched_ablated"):
            raise ValueError("prestructure role is not frozen")
        view = require_materialization(observed_parent, observed_materialization)
        selected_factory = (
            view.actual_factory if role == "actual" else view.matched_ablated_factory
        )
        selected_binding = (
            view.materialization.actual_factory_binding
            if role == "actual"
            else view.materialization.matched_ablated_factory_binding
        )
        structure = freeze_complex_tensor(_canonical_block_j())
        provisional = _FakePrestructureBody(
            prestructure_schema_version=("v3m0.parent-v3-application-prestructure.v1"),
            parent_freeze_v3_sha=observed_parent.manifest.parent_freeze_v3_sha,
            permit_sha=view.materialization.permit.permit_sha,
            materialization_sha=view.materialization.materialization_sha,
            current_application_authority_v3_sha=(
                view.materialization.current_application_authority.application_authority_sha
            ),
            current_scenario_authority_v3_sha=(
                view.materialization.current_scenario_authority.scenario_authority_sha
            ),
            current_scenario_response_contract_v3_sha=(
                view.materialization.current_scenario_response_contract.response_contract_sha
            ),
            factory_binding=copy.deepcopy(selected_binding),
            factory_sha=selected_factory.factory.factory_sha,
            factory_role=role,
            ablation_pair_snapshot=copy.deepcopy(
                view.materialization.ablation_pair_snapshot
            ),
            basis_contract=copy.deepcopy(view.materialization.basis_contract),
            evidence_lane="synthetic-classical",
            target_spec_sha=selected_factory.factory.target_spec_sha,
            state_schema_id=selected_factory.factory.state_schema_id,
            channel_order=selected_factory.factory.channel_order,
            canonical_channel_pairs=C19_CHANNEL_PAIRS,
            fourier_adjoint_convention_id="minus-k-transpose-v1",
            structure_form=structure,
            reality_convention_id="real-kernel-positive-zero-v1",
            prestructure_authority_sha="0" * 64,
        )
        body = replace(
            provisional,
            prestructure_authority_sha=canonical_sha(prestructure_payload(provisional)),
        )
        return body, selected_factory, selected_binding

    def register_prestructure(
        body,
        observed_parent,
        observed_materialization,
        selected_factory,
        selected_binding,
    ):
        capability = _FakeVerifiedPrestructure(body)
        identity = id(capability)
        reference = weakref.ref(
            capability,
            lambda current, wrapper_id=identity: prestructure_registry.pop(
                wrapper_id,
                None,
            ),
        )
        prestructure_registry[identity] = (
            reference,
            SimpleNamespace(
                body=copy.deepcopy(body),
                parent=observed_parent,
                materialization=observed_materialization,
                factory=selected_factory,
                factory_binding=copy.deepcopy(selected_binding),
            ),
        )
        return capability

    def issue_prestructure(observed_parent, observed_materialization, role):
        calls.events.append("prestructure_issue")
        calls.prestructure_issued.append(
            (observed_parent, observed_materialization, role)
        )
        if mode["value"] == "prestructure":
            raise ValueError("forced Parent-v3 prestructure derivation failure")
        body, selected_factory, selected_binding = build_prestructure(
            observed_parent,
            observed_materialization,
            role,
        )
        return register_prestructure(
            body,
            observed_parent,
            observed_materialization,
            selected_factory,
            selected_binding,
        )

    def verify_prestructure(body, observed_parent, observed_materialization):
        calls.events.append("prestructure_verify")
        calls.prestructure_verified.append(
            (body, observed_parent, observed_materialization)
        )
        if mode["value"] == "prestructure":
            raise ValueError("forced Parent-v3 prestructure replay failure")
        if type(body) is not _FakePrestructureBody:
            raise TypeError("raw Parent-v3 prestructure has the wrong exact type")
        expected, selected_factory, selected_binding = build_prestructure(
            observed_parent,
            observed_materialization,
            body.factory_role,
        )
        if body != expected:
            raise ValueError("raw Parent-v3 prestructure differs from live derivation")
        return register_prestructure(
            body,
            observed_parent,
            observed_materialization,
            selected_factory,
            selected_binding,
        )

    def reverify_prestructure(capability):
        calls.events.append("prestructure_reverify")
        calls.prestructure_reverified.append(capability)
        if mode["value"] == "prestructure":
            raise ValueError("forced live Parent-v3 prestructure failure")
        if type(capability) is not _FakeVerifiedPrestructure:
            raise TypeError("exact live Parent-v3 prestructure required")
        current = prestructure_registry.get(id(capability))
        if current is None or current[0]() is not capability:
            raise ValueError("Parent-v3 prestructure identity is not live")
        authority = current[1]
        if capability.prestructure != authority.body:
            raise ValueError("Parent-v3 prestructure immutable body drifted")
        b2_view = require_materialization(
            authority.parent,
            authority.materialization,
        )
        selected_factory = (
            b2_view.actual_factory
            if authority.body.factory_role == "actual"
            else b2_view.matched_ablated_factory
        )
        selected_binding = (
            b2_view.materialization.actual_factory_binding
            if authority.body.factory_role == "actual"
            else b2_view.materialization.matched_ablated_factory_binding
        )
        if (
            selected_factory.factory != authority.factory.factory
            or selected_binding != authority.factory_binding
            or authority.body.factory_binding != selected_binding
        ):
            raise ValueError("Parent-v3 prestructure branch replay drifted")
        return SimpleNamespace(
            prestructure=copy.deepcopy(authority.body),
            parent=authority.parent,
            materialization=authority.materialization,
            factory=selected_factory,
            factory_binding=copy.deepcopy(selected_binding),
        )

    def measure_bound(
        factory,
        *,
        parent_freeze_sha,
        prestructure_authority_sha,
    ):
        calls.events.append("measure")
        calls.measurements.append(
            (factory, parent_freeze_sha, prestructure_authority_sha)
        )
        if mode["value"] == "executor":
            raise RuntimeError("forced real-space factory executor failure")
        if mode["value"] == "support_exception":
            raise facade._MeasuredTransitionSupportFailure(
                "forced real-space support validation failure"
            )
        if type(factory) is not _FakeLiveFactory:
            raise TypeError("measurement requires an exact live factory")
        payload = factory.factory
        support = tuple(
            sorted(
                {
                    tuple(-coordinate for coordinate in offset)
                    for offset in factory.stencil_support
                }
            )
        )
        kernel = np.zeros(
            (len(payload.channel_order), len(payload.channel_order), 8),
            dtype=np.complex128,
        )
        for source in range(len(payload.channel_order)):
            impulse = np.zeros(payload.state_shape, dtype=np.complex128)
            impulse[(source, 0)] = 1.0 + 0.0j
            calls.executor[factory.role].append(impulse.copy())
            output = _factory_step(factory, impulse)
            if output.dtype != np.dtype(np.complex128):
                raise TypeError("factory executor changed dtype")
            if output.shape != payload.state_shape:
                raise ValueError("factory executor changed shape")
            if not np.isfinite(output).all():
                raise ValueError("factory executor returned non-finite values")
            kernel[:, source, :] = output
        frozen = freeze_complex_tensor(kernel)
        support_sha = canonical_sha(
            transition_support_payload(
                support,
                C19_SPATIAL_SHAPE,
                C19_CHANNEL_ORDER,
                "channel-identity-v1",
            )
        )
        provisional = MeasuredTransition(
            transition_schema_version="v3m0.measured-transition.v1",
            parent_freeze_sha=parent_freeze_sha,
            prestructure_authority_sha=prestructure_authority_sha,
            factory_sha=payload.factory_sha,
            factory_role=factory.role,
            state_schema_id=C19_STATE_SCHEMA_ID,
            channel_order=C19_CHANNEL_ORDER,
            spatial_shape=C19_SPATIAL_SHAPE,
            dt=payload.dt,
            boundary_manifest_id=payload.boundary_manifest_id,
            state_basis_convention_id="channel-identity-v1",
            kernel=frozen,
            support_offsets=support,
            support_sha=support_sha,
            macro_steps=1,
            transition_sha="0" * 64,
        )
        result = replace(
            provisional,
            transition_sha=canonical_sha(measured_transition_payload(provisional)),
        )
        if measurement_attack is None:
            return result
        if measurement_attack == "unknown_field":
            object.__setattr__(result, "unknown_measured_field", "forged")
            return result
        if measurement_attack == "unknown_kernel_field":
            object.__setattr__(result.kernel, "unknown_kernel_field", "forged")
            return result
        if measurement_attack == "support_sha":
            attacked = replace(
                result,
                support_sha="d" * 64,
                transition_sha="0" * 64,
            )
        elif measurement_attack in ("no_wrap", "wrong_sign"):
            attacked_support = (
                ((0,), (4,)) if measurement_attack == "no_wrap" else ((0,), (1,))
            )
            attacked_kernel = frozen_tensor_array(result.kernel)
            attacked_kernel[:, :, 1:] = 0.0 + 0.0j
            attacked = replace(
                result,
                kernel=freeze_complex_tensor(attacked_kernel),
                support_offsets=attacked_support,
                support_sha=canonical_sha(
                    transition_support_payload(
                        attacked_support,
                        C19_SPATIAL_SHAPE,
                        C19_CHANNEL_ORDER,
                        "channel-identity-v1",
                    )
                ),
                transition_sha="0" * 64,
            )
        else:
            raise AssertionError("unknown hostile measurement attack")
        return replace(
            attacked,
            transition_sha=canonical_sha(measured_transition_payload(attacked)),
        )

    def materialization_payload(body):
        return _body_payload(body, "materialization_sha")

    def binding_payload(body):
        return _body_payload(body, "binding_sha")

    monkeypatch.setattr(
        facade,
        "ApplicationMaterializationV3Failure",
        ApplicationMaterializationV3Failure,
    )
    monkeypatch.setattr(
        facade,
        "VerifiedV3M0ApplicationScenarioMaterializationV3",
        _FakeVerifiedMaterializationV3,
    )
    monkeypatch.setattr(
        facade,
        "ApplicationScenarioMaterializationV3",
        _FakeMaterializationBody,
    )
    monkeypatch.setattr(facade, "FactoryBranchBindingV3", _FakeFactoryBinding)
    monkeypatch.setattr(
        facade,
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        require_materialization,
    )
    monkeypatch.setattr(
        facade,
        "ParentV3ApplicationPrestructure",
        _FakePrestructureBody,
    )
    monkeypatch.setattr(
        facade,
        "VerifiedParentV3ApplicationPrestructure",
        _FakeVerifiedPrestructure,
    )
    monkeypatch.setattr(
        facade,
        "_issue_parent_v3_application_prestructure",
        issue_prestructure,
    )
    monkeypatch.setattr(
        facade,
        "_verify_parent_v3_application_prestructure",
        verify_prestructure,
    )
    monkeypatch.setattr(
        facade,
        "_reverify_verified_parent_v3_application_prestructure",
        reverify_prestructure,
    )
    monkeypatch.setattr(
        facade,
        "parent_v3_application_prestructure_payload",
        prestructure_payload,
    )
    monkeypatch.setattr(
        facade,
        "application_scenario_materialization_v3_payload",
        materialization_payload,
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "factory_branch_binding_v3_payload",
        binding_payload,
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "_measure_bound_realspace_transition",
        measure_bound,
    )

    authority_payload = facade._make_transition_authority_v3_payload_api(
        facade._transition_authority_v3_payload_impl,
        body_type=facade.TransitionAuthorityV3,
        record_validator=facade._exact_record,
        materialization_payload_builder=materialization_payload,
        binding_payload_builder=binding_payload,
        prestructure_payload_builder=prestructure_payload,
        measured_payload_builder=measured_transition_payload,
    )

    def forbidden_legacy(*args, **kwargs):
        del args, kwargs
        raise AssertionError("B3 consulted a forbidden legacy/projected path")

    for name in (
        "measure_transition",
        "verify_measured_transition",
        "_register_measured_transition",
        "_issue_verified_transition",
        "transition_symbol",
        "_transition_symbol_from_raw",
        "fft",
        "fftn",
        "projector",
        "per_k_projector",
    ):
        monkeypatch.setattr(facade, name, forbidden_legacy, raising=False)

    graph = facade._make_transition_authority_v3_graph(facade._ISSUANCE_TOKEN)
    return SimpleNamespace(
        facade=facade,
        graph=graph,
        parent=parent,
        materialization=materialization,
        secondary_materialization=secondary_materialization,
        materialization_body=materialization_body,
        actual_factory=stable_factories["actual"],
        matched_factory=stable_factories["matched_ablated"],
        actual_kernel=actual_kernel,
        matched_kernel=matched_kernel,
        calls=calls,
        mode=mode,
        prestructure_payload=prestructure_payload,
        authority_payload=authority_payload,
    )


def _resign_transition(transition, **changes):
    from rulespace_v3.dynamics import measured_transition_payload
    from rulespace_v3.evidence import canonical_sha

    provisional = replace(
        transition,
        **changes,
        transition_sha="0" * 64,
    )
    return replace(
        provisional,
        transition_sha=canonical_sha(measured_transition_payload(provisional)),
    )


def _resign_authority(fixture, authority, **changes):
    from rulespace_v3.evidence import canonical_sha

    provisional = replace(
        authority,
        **changes,
        transition_authority_sha="0" * 64,
    )
    return replace(
        provisional,
        transition_authority_sha=canonical_sha(fixture.authority_payload(provisional)),
    )


def _assert_reason(caught: pytest.ExceptionInfo[BaseException], reason_id: str) -> None:
    assert getattr(caught.value, "reason_id", None) == reason_id
    assert type(getattr(caught.value, "detail", None)) is str
    assert caught.value.detail


def _closure_reachable_objects(function: object) -> tuple[object, ...]:
    pending = [function]
    visited: set[int] = set()
    found: list[object] = []
    while pending:
        current = pending.pop()
        if inspect.ismethod(current):
            current = current.__func__
        if not inspect.isfunction(current) or id(current) in visited:
            continue
        visited.add(id(current))
        for cell in current.__closure__ or ():
            value = cell.cell_contents
            found.append(value)
            if inspect.isfunction(value) or inspect.ismethod(value):
                pending.append(value)
    return tuple(found)


def _direct_rulespace_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name
                for alias in node.names
                if alias.name.startswith("rulespace_v3.")
            )
        elif isinstance(node, ast.ImportFrom):
            if node.level == 1 and node.module:
                imported.add(f"rulespace_v3.{node.module}")
            elif node.module and node.module.startswith("rulespace_v3."):
                imported.add(node.module)
    return imported


def _relative_imported_names(path: Path, module: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and (
            (node.level == 1 and node.module == module)
            or node.module == f"rulespace_v3.{module}"
        )
        for alias in node.names
    }


def test_b3_exact_v7_records_api_failure_vocabulary_and_surface() -> None:
    facade = _module()
    import rulespace_v3.parent_v3_application_prestructure as prestructure
    from rulespace_v3.dynamics import MeasuredTransition

    assert facade.MeasuredTransition is MeasuredTransition
    assert [
        item.name for item in fields(prestructure.ParentV3ApplicationPrestructure)
    ] == [
        "prestructure_schema_version",
        "parent_freeze_v3_sha",
        "permit_sha",
        "materialization_sha",
        "current_application_authority_v3_sha",
        "current_scenario_authority_v3_sha",
        "current_scenario_response_contract_v3_sha",
        "factory_binding",
        "factory_sha",
        "factory_role",
        "ablation_pair_snapshot",
        "basis_contract",
        "evidence_lane",
        "target_spec_sha",
        "state_schema_id",
        "channel_order",
        "canonical_channel_pairs",
        "fourier_adjoint_convention_id",
        "structure_form",
        "reality_convention_id",
        "prestructure_authority_sha",
    ]
    assert [item.name for item in fields(facade.TransitionAuthorityV3)] == [
        "transition_authority_schema_version",
        "materialization",
        "factory_binding",
        "prestructure_authority",
        "measured_transition",
        "transition_authority_sha",
    ]
    assert [
        item.name for item in fields(facade._VerifiedTransitionAuthorityV3View)
    ] == [
        "transition_authority",
        "parent",
        "materialization",
        "factory",
        "prestructure",
    ]
    assert tuple(
        inspect.signature(facade.issue_transition_authority_v3).parameters
    ) == (
        "parent",
        "materialization",
        "factory_role",
    )
    assert tuple(
        inspect.signature(facade.verify_transition_authority_v3).parameters
    ) == (
        "transition",
        "parent",
        "materialization",
    )
    assert tuple(inspect.signature(facade.verify_transition_pair_v3).parameters) == (
        "parent",
        "materialization",
        "actual_transition",
        "matched_ablated_transition",
    )
    assert tuple(
        inspect.signature(facade._reverify_verified_transition_authority_v3).parameters
    ) == ("transition",)
    assert facade._FAILURE_REASON_IDS == frozenset(FAILURE_REASON_IDS)
    for reason_id in FAILURE_REASON_IDS:
        failure = facade.TransitionAuthorityV3Failure(reason_id, "probe")
        assert failure.reason_id == reason_id
        assert failure.detail == "probe"
    with pytest.raises(ValueError, match="reason"):
        facade.TransitionAuthorityV3Failure("CALLER_KERNEL_ACCEPTED", "probe")

    required_public = (
        "TransitionAuthorityV3Failure",
        "TransitionAuthorityV3",
        "VerifiedTransitionAuthorityV3",
        "issue_transition_authority_v3",
        "transition_authority_v3_payload",
        "verify_transition_authority_v3",
        "verify_transition_pair_v3",
    )
    assert tuple(facade.__all__) == required_public
    assert not {
        "MeasuredTransition",
        "VerifiedParentV3ApplicationPrestructure",
        "_reverify_verified_transition_authority_v3",
        "VerifiedPrestructureAuthority",
        "VerifiedTransition",
        "measure_transition",
        "verify_measured_transition",
        "transition_symbol",
    } & set(facade.__all__)


def test_b3_captures_exact_b2_prestructure_and_dynamics_owner_seams() -> None:
    import rulespace_v3.application_materialization_v3 as b2
    import rulespace_v3.dynamics as dynamics
    import rulespace_v3.parent_v3_application_prestructure as prestructure

    facade = _module()
    assert facade._require_v3m0_application_scenario_materialization_v3_for_parent is (
        b2._require_v3m0_application_scenario_materialization_v3_for_parent
    )
    assert facade._issue_parent_v3_application_prestructure is (
        prestructure._issue_parent_v3_application_prestructure
    )
    assert facade._verify_parent_v3_application_prestructure is (
        prestructure._verify_parent_v3_application_prestructure
    )
    assert facade._reverify_verified_parent_v3_application_prestructure is (
        prestructure._reverify_verified_parent_v3_application_prestructure
    )
    assert facade._measure_bound_realspace_transition is (
        dynamics._measure_bound_realspace_transition
    )

    issuer_reachable = _closure_reachable_objects(facade.issue_transition_authority_v3)
    verifier_reachable = _closure_reachable_objects(
        facade.verify_transition_authority_v3
    )
    private_reachable = _closure_reachable_objects(
        facade._reverify_verified_transition_authority_v3
    )
    assert (
        b2._require_v3m0_application_scenario_materialization_v3_for_parent
        in issuer_reachable
    )
    assert prestructure._issue_parent_v3_application_prestructure in issuer_reachable
    assert prestructure._verify_parent_v3_application_prestructure in verifier_reachable
    assert dynamics._measure_bound_realspace_transition in issuer_reachable
    assert dynamics._measure_bound_realspace_transition in verifier_reachable
    assert (
        prestructure._reverify_verified_parent_v3_application_prestructure
        in private_reachable
    )


def test_b3_dynamics_shared_core_is_exact_private_realspace_full_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rulespace_v3.dynamics as dynamics
    from rulespace_v3.evidence import canonical_sha

    production_core = dynamics._measure_bound_realspace_transition
    signature = inspect.signature(production_core)
    assert tuple(signature.parameters) == (
        "factory",
        "parent_freeze_sha",
        "prestructure_authority_sha",
    )
    assert (
        signature.parameters["factory"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    )
    assert (
        signature.parameters["parent_freeze_sha"].kind is inspect.Parameter.KEYWORD_ONLY
    )
    assert (
        signature.parameters["prestructure_authority_sha"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
    assert "_measure_bound_realspace_transition" not in dynamics.__all__

    body = _FakeFactoryBody(
        factory_sha="1" * 64,
        target_spec_sha="8" * 64,
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        state_shape=(20, 8),
        spatial_ndim=1,
        dt=0.125,
        boundary_manifest_id="periodic-v1",
    )
    kernel, _ = _kernel_pair()
    factory = _FakeLiveFactory(
        body,
        "actual",
        kernel,
        ((-1,), (0,), (1,)),
    )
    impulses: list[np.ndarray] = []
    support_calls: list[tuple[object, int]] = []
    reverify_calls: list[object] = []

    def reverify(observed):
        reverify_calls.append(observed)
        if observed is not factory:
            raise ValueError("factory identity is not live")
        return SimpleNamespace(factory=body, role="actual")

    def support(observed, macro_steps):
        support_calls.append((observed, macro_steps))
        if observed is not factory or macro_steps != 1:
            raise ValueError("support derivation drifted")
        return factory.stencil_support

    def execute(observed, state):
        if observed is not factory:
            raise ValueError("executor factory identity drifted")
        impulses.append(state.copy())
        return _factory_step(factory, state)

    support_payload_builder = dynamics.transition_support_payload
    measured_payload_builder = dynamics.measured_transition_payload
    tensor_array_builder = dynamics.frozen_tensor_array
    core = dynamics._make_bound_realspace_transition_core(
        factory_reverifier=reverify,
        factory_support_builder=support,
        canonical_support_builder=dynamics._canonical_transition_support,
        no_wrap_validator=dynamics._assert_no_wrap,
        kernel_allocator=dynamics._allocate_transition_kernel,
        factory_executor=execute,
        outside_mask_builder=dynamics._outside_support_mask,
        positive_zero_validator=dynamics._assert_positive_bit_zero,
        tensor_freezer=dynamics.freeze_complex_tensor,
        sha_builder=canonical_sha,
        support_payload_builder=support_payload_builder,
        measured_type=dynamics.MeasuredTransition,
        measured_payload_builder=measured_payload_builder,
        replace_fn=replace,
        np_module=np,
        transition_schema=dynamics.TRANSITION_SCHEMA_VERSION,
        basis_convention=dynamics.STATE_BASIS_CONVENTION_ID,
        support_failure_type=dynamics._MeasuredTransitionSupportFailure,
    )

    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("shared core consulted FFT/projected/legacy dynamics")

    for name in (
        "fft",
        "fftn",
        "projector",
        "per_k_projector",
        "transition_symbol",
        "_transition_symbol_from_raw",
        "measure_transition",
        "verify_measured_transition",
        "_reverify_verified_factory",
        "factory_support_offsets",
        "apply_factory_step",
        "_assert_no_wrap",
        "_outside_support_mask",
        "_assert_positive_bit_zero",
        "_allocate_transition_kernel",
        "freeze_complex_tensor",
        "canonical_sha",
        "transition_support_payload",
        "measured_transition_payload",
    ):
        monkeypatch.setattr(dynamics, name, forbidden, raising=False)

    result = core(
        factory,
        parent_freeze_sha="a" * 64,
        prestructure_authority_sha="b" * 64,
    )
    assert reverify_calls == [factory]
    assert support_calls == [(factory, 1)]
    _assert_canonical_impulse_groups(impulses, factory)
    assert result.parent_freeze_sha == "a" * 64
    assert result.prestructure_authority_sha == "b" * 64
    assert result.state_schema_id == C19_STATE_SCHEMA_ID
    assert result.channel_order == C19_CHANNEL_ORDER
    assert result.spatial_shape == C19_SPATIAL_SHAPE
    assert result.kernel.shape == (20, 20, 8)
    assert result.support_offsets == ((-1,), (0,), (1,))
    assert result.support_sha == canonical_sha(
        support_payload_builder(
            result.support_offsets,
            C19_SPATIAL_SHAPE,
            C19_CHANNEL_ORDER,
            "channel-identity-v1",
        )
    )
    np.testing.assert_array_equal(
        tensor_array_builder(result.kernel),
        kernel,
    )
    assert result.transition_sha == canonical_sha(measured_payload_builder(result))

    # The same executor with an under-declared support must die; the core may
    # not silently truncate, project, or tolerate a nonzero coefficient.
    factory.stencil_support = ((0,),)
    with pytest.raises(
        dynamics._MeasuredTransitionSupportFailure, match="support|zero"
    ):
        core(
            factory,
            parent_freeze_sha="a" * 64,
            prestructure_authority_sha="b" * 64,
        )


@pytest.mark.parametrize("factory_role", ("actual", "matched_ablated"))
def test_b3_issues_and_raw_verifies_full_c19_transition_with_same_prestructure(
    monkeypatch: pytest.MonkeyPatch,
    factory_role: str,
) -> None:
    from rulespace_v3.dynamics import frozen_tensor_array, measured_transition_payload
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch)
    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        factory_role,
    )
    assert type(capability) is fixture.facade.VerifiedTransitionAuthorityV3
    raw = capability.transition_authority
    assert type(raw) is fixture.facade.TransitionAuthorityV3
    expected_binding = (
        fixture.materialization_body.actual_factory_binding
        if factory_role == "actual"
        else fixture.materialization_body.matched_ablated_factory_binding
    )
    expected_factory = (
        fixture.actual_factory if factory_role == "actual" else fixture.matched_factory
    )
    expected_kernel = (
        fixture.actual_kernel if factory_role == "actual" else fixture.matched_kernel
    )
    expected_support = tuple(
        sorted(
            {
                tuple(-coordinate for coordinate in offset)
                for offset in expected_factory.stencil_support
            }
        )
    )

    assert raw.transition_authority_schema_version == ("v3m0.transition-authority.v3")
    assert raw.materialization == fixture.materialization_body
    assert raw.factory_binding == expected_binding
    prestructure = raw.prestructure_authority
    assert type(prestructure) is _FakePrestructureBody
    assert prestructure.prestructure_schema_version == (
        "v3m0.parent-v3-application-prestructure.v1"
    )
    assert prestructure.parent_freeze_v3_sha == "a" * 64
    assert prestructure.materialization_sha == (
        fixture.materialization_body.materialization_sha
    )
    assert prestructure.factory_binding == expected_binding
    assert prestructure.factory_sha == expected_binding.factory.factory_sha
    assert prestructure.factory_role == factory_role
    assert prestructure.ablation_pair_snapshot == (
        fixture.materialization_body.ablation_pair_snapshot
    )
    assert prestructure.basis_contract == fixture.materialization_body.basis_contract
    assert prestructure.state_schema_id == C19_STATE_SCHEMA_ID
    assert prestructure.channel_order == C19_CHANNEL_ORDER
    assert prestructure.canonical_channel_pairs == C19_CHANNEL_PAIRS
    assert prestructure.structure_form.shape == (20, 20)
    np.testing.assert_array_equal(
        frozen_tensor_array(prestructure.structure_form),
        _canonical_block_j(),
    )
    assert prestructure.prestructure_authority_sha == canonical_sha(
        fixture.prestructure_payload(prestructure)
    )

    measured = raw.measured_transition
    assert measured.prestructure_authority_sha == (
        prestructure.prestructure_authority_sha
    )
    assert measured.parent_freeze_sha == prestructure.parent_freeze_v3_sha
    assert measured.factory_sha == prestructure.factory_sha
    assert measured.factory_role == factory_role
    assert measured.state_schema_id == C19_STATE_SCHEMA_ID
    assert measured.channel_order == C19_CHANNEL_ORDER
    assert measured.spatial_shape == C19_SPATIAL_SHAPE
    assert measured.kernel.shape == (20, 20, 8)
    assert measured.support_offsets == expected_support
    np.testing.assert_array_equal(
        frozen_tensor_array(measured.kernel),
        expected_kernel,
    )
    assert measured.transition_sha == canonical_sha(
        measured_transition_payload(measured)
    )
    assert raw.transition_authority_sha == canonical_sha(fixture.authority_payload(raw))

    transition_view = fixture.graph.reverify(capability)
    assert transition_view.transition_authority == raw
    assert transition_view.parent is fixture.parent
    assert transition_view.materialization is fixture.materialization
    assert transition_view.factory.factory == expected_factory.factory
    assert type(transition_view.prestructure) is _FakeVerifiedPrestructure
    assert transition_view.prestructure is fixture.calls.prestructure_reverified[0]
    assert transition_view.prestructure.prestructure == prestructure
    assert len(fixture.calls.prestructure_issued) == 1
    measure_index = fixture.calls.events.index("measure")
    assert fixture.calls.events.index("b2_owner_seam") < fixture.calls.events.index(
        "prestructure_issue"
    )
    assert fixture.calls.events.index("prestructure_issue") < measure_index
    assert fixture.calls.events.index("prestructure_reverify") < measure_index
    _assert_canonical_impulse_groups(
        fixture.calls.executor[factory_role],
        expected_factory,
    )
    other_role = "matched_ablated" if factory_role == "actual" else "actual"
    assert fixture.calls.executor[other_role] == []

    replayed = fixture.graph.verify(
        raw,
        fixture.parent,
        fixture.materialization,
    )
    assert type(replayed) is fixture.facade.VerifiedTransitionAuthorityV3
    assert replayed is not capability
    assert replayed.transition_authority == raw


def test_b3_reverify_accepts_fresh_b2_child_bodies_but_keeps_prestructure_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, fresh_factories=True)
    actual_capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    issued_prestructure = fixture.calls.prestructure_reverified[0]
    matched_capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "matched_ablated",
    )

    first = fixture.graph.reverify(actual_capability)
    second = fixture.graph.reverify(actual_capability)
    raw_verified = fixture.graph.verify(
        actual_capability.transition_authority,
        fixture.parent,
        fixture.materialization,
    )
    raw_view = fixture.graph.reverify(raw_verified)
    assert fixture.graph.verify_pair(
        fixture.parent,
        fixture.materialization,
        actual_capability,
        matched_capability,
    ) == (actual_capability, matched_capability)

    assert first.factory is not second.factory
    assert first.factory.factory == second.factory.factory
    assert first.factory.role == second.factory.role == "actual"
    assert first.prestructure is second.prestructure is issued_prestructure
    assert (
        first.prestructure.prestructure
        == actual_capability.transition_authority.prestructure_authority
    )
    assert raw_view.prestructure is not issued_prestructure
    assert raw_view.prestructure.prestructure == issued_prestructure.prestructure
    assert raw_view.factory.factory == first.factory.factory
    assert all(
        actual.factory == fixture.actual_factory.factory
        and matched.factory == fixture.matched_factory.factory
        for actual, matched in fixture.calls.resolved_factories
    )
    assert len({id(actual) for actual, _ in fixture.calls.resolved_factories}) > 1


@pytest.mark.parametrize(
    ("mode", "reason_id"),
    (
        ("materialization", "MATERIALIZATION_INVALID"),
        ("prestructure", "PRESTRUCTURE_INVALID"),
        ("executor", "EXECUTOR_FAILED"),
        ("support_exception", "SUPPORT_INVALID"),
        ("cross_parent", "CROSS_PARENT_ROOT"),
    ),
)
def test_b3_routes_upstream_and_executor_failures_to_exact_reason_ids(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    reason_id: str,
) -> None:
    fixture = _fixture(monkeypatch)
    fixture.mode["value"] = mode
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
    _assert_reason(caught, reason_id)


def test_b3_all_measurement_support_branch_and_prestructure_attacks_route_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3.dynamics import (
        freeze_complex_tensor,
        frozen_tensor_array,
        transition_support_payload,
    )
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch)
    issued = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).transition_authority

    hostile_kernel = frozen_tensor_array(issued.measured_transition.kernel)
    hostile_kernel[0, 0, 0] += 0.5 + 0.0j
    kernel_transition = _resign_transition(
        issued.measured_transition,
        kernel=freeze_complex_tensor(hostile_kernel),
    )
    kernel_authority = _resign_authority(
        fixture,
        issued,
        measured_transition=kernel_transition,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as measured:
        fixture.graph.verify(
            kernel_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(measured, "TRANSITION_MEASUREMENT_FAILED")

    support = ((0,),)
    support_transition = _resign_transition(
        issued.measured_transition,
        support_offsets=support,
        support_sha=canonical_sha(
            transition_support_payload(
                support,
                C19_SPATIAL_SHAPE,
                C19_CHANNEL_ORDER,
                "channel-identity-v1",
            )
        ),
    )
    support_authority = _resign_authority(
        fixture,
        issued,
        measured_transition=support_transition,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as invalid_support:
        fixture.graph.verify(
            support_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(invalid_support, "SUPPORT_INVALID")

    branch_transition = _resign_transition(
        issued.measured_transition,
        factory_role="matched_ablated",
    )
    branch_authority = _resign_authority(
        fixture,
        issued,
        measured_transition=branch_transition,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as branch:
        fixture.graph.verify(
            branch_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(branch, "BRANCH_JOIN_FAILED")

    wrong_structure = freeze_complex_tensor(np.eye(20, dtype=np.complex128))
    prestructure_provisional = replace(
        issued.prestructure_authority,
        structure_form=wrong_structure,
        prestructure_authority_sha="0" * 64,
    )
    hostile_prestructure = replace(
        prestructure_provisional,
        prestructure_authority_sha=canonical_sha(
            fixture.prestructure_payload(prestructure_provisional)
        ),
    )
    prestructure_transition = _resign_transition(
        issued.measured_transition,
        prestructure_authority_sha=(hostile_prestructure.prestructure_authority_sha),
    )
    prestructure_authority = _resign_authority(
        fixture,
        issued,
        prestructure_authority=hostile_prestructure,
        measured_transition=prestructure_transition,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as prestructure:
        fixture.graph.verify(
            prestructure_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(prestructure, "PRESTRUCTURE_INVALID")

    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as role:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "control",
        )
    _assert_reason(role, "BRANCH_JOIN_FAILED")


def test_b3_raw_verify_routes_recursive_roots_executor_and_outside_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3.dynamics import freeze_complex_tensor, frozen_tensor_array
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch)
    issued = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).transition_authority

    measured_root = _resign_transition(
        issued.measured_transition,
        parent_freeze_sha="d" * 64,
    )
    measured_root_authority = _resign_authority(
        fixture,
        issued,
        measured_transition=measured_root,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.verify(
            measured_root_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(caught, "CROSS_PARENT_ROOT")

    prestructure_root_provisional = replace(
        issued.prestructure_authority,
        parent_freeze_v3_sha="d" * 64,
        prestructure_authority_sha="0" * 64,
    )
    prestructure_root = replace(
        prestructure_root_provisional,
        prestructure_authority_sha=canonical_sha(
            fixture.prestructure_payload(prestructure_root_provisional)
        ),
    )
    prestructure_root_measured = _resign_transition(
        issued.measured_transition,
        prestructure_authority_sha=prestructure_root.prestructure_authority_sha,
    )
    prestructure_root_authority = _resign_authority(
        fixture,
        issued,
        prestructure_authority=prestructure_root,
        measured_transition=prestructure_root_measured,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.verify(
            prestructure_root_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(caught, "CROSS_PARENT_ROOT")

    hostile_permit = replace(
        issued.materialization.permit,
        parent_freeze_v3_sha="d" * 64,
    )
    hostile_materialization = replace(
        issued.materialization,
        permit=hostile_permit,
    )
    materialization_root_authority = _resign_authority(
        fixture,
        issued,
        materialization=hostile_materialization,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.verify(
            materialization_root_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(caught, "CROSS_PARENT_ROOT")

    hostile_calibration = replace(
        issued.materialization.permit.calibration,
        parent_freeze_v3_sha="d" * 64,
    )
    calibration_permit = replace(
        issued.materialization.permit,
        calibration=hostile_calibration,
    )
    calibration_materialization = replace(
        issued.materialization,
        permit=calibration_permit,
    )
    calibration_root_authority = _resign_authority(
        fixture,
        issued,
        materialization=calibration_materialization,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.verify(
            calibration_root_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(caught, "CROSS_PARENT_ROOT")

    for replay_index in range(3):
        refs = list(
            issued.materialization.permit.calibration.calibration_control_replay_refs
        )
        refs[replay_index] = replace(
            refs[replay_index],
            parent_freeze_v3_sha="d" * 64,
        )
        replay_calibration = replace(
            issued.materialization.permit.calibration,
            calibration_control_replay_refs=tuple(refs),
        )
        replay_permit = replace(
            issued.materialization.permit,
            calibration=replay_calibration,
        )
        replay_materialization = replace(
            issued.materialization,
            permit=replay_permit,
        )
        replay_root_authority = _resign_authority(
            fixture,
            issued,
            materialization=replay_materialization,
        )
        with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
            fixture.graph.verify(
                replay_root_authority,
                fixture.parent,
                fixture.materialization,
            )
        _assert_reason(caught, "CROSS_PARENT_ROOT")

    for binding_field in (
        "actual_factory_binding",
        "matched_ablated_factory_binding",
    ):
        nested_binding = replace(
            getattr(issued.materialization, binding_field),
            parent_freeze_v3_sha="d" * 64,
        )
        nested_materialization = replace(
            issued.materialization,
            **{binding_field: nested_binding},
        )
        nested_root_authority = _resign_authority(
            fixture,
            issued,
            materialization=nested_materialization,
        )
        with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
            fixture.graph.verify(
                nested_root_authority,
                fixture.parent,
                fixture.materialization,
            )
        _assert_reason(caught, "CROSS_PARENT_ROOT")

    hostile_binding = replace(
        issued.factory_binding,
        parent_freeze_v3_sha="d" * 64,
    )
    binding_root_authority = _resign_authority(
        fixture,
        issued,
        factory_binding=hostile_binding,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.verify(
            binding_root_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(caught, "CROSS_PARENT_ROOT")

    prestructure_binding = replace(
        issued.prestructure_authority.factory_binding,
        parent_freeze_v3_sha="d" * 64,
    )
    prestructure_binding_provisional = replace(
        issued.prestructure_authority,
        factory_binding=prestructure_binding,
        prestructure_authority_sha="0" * 64,
    )
    prestructure_binding_body = replace(
        prestructure_binding_provisional,
        prestructure_authority_sha=canonical_sha(
            fixture.prestructure_payload(prestructure_binding_provisional)
        ),
    )
    prestructure_binding_measured = _resign_transition(
        issued.measured_transition,
        prestructure_authority_sha=(
            prestructure_binding_body.prestructure_authority_sha
        ),
    )
    prestructure_binding_authority = _resign_authority(
        fixture,
        issued,
        prestructure_authority=prestructure_binding_body,
        measured_transition=prestructure_binding_measured,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.verify(
            prestructure_binding_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(caught, "CROSS_PARENT_ROOT")

    outside_kernel = frozen_tensor_array(issued.measured_transition.kernel)
    outside_kernel[0, 0, 3] = 1.0 + 0.0j
    outside_transition = _resign_transition(
        issued.measured_transition,
        kernel=freeze_complex_tensor(outside_kernel),
    )
    outside_authority = _resign_authority(
        fixture,
        issued,
        measured_transition=outside_transition,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.verify(
            outside_authority,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(caught, "SUPPORT_INVALID")

    fixture.actual_factory.transition_kernel[0, 0, 3] = 1.0 + 0.0j
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
    _assert_reason(caught, "SUPPORT_INVALID")
    fixture.actual_factory.transition_kernel[0, 0, 3] = 0.0 + 0.0j

    fixture.mode["value"] = "executor"
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.verify(
            issued,
            fixture.parent,
            fixture.materialization,
        )
    _assert_reason(caught, "EXECUTOR_FAILED")


def test_b3_raw_verify_rejects_measured_subclasses_and_unknown_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3.dynamics import MeasuredTransition, measured_transition_payload
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch)
    issued = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).transition_authority

    unknown = copy.deepcopy(issued.measured_transition)
    object.__setattr__(unknown, "unknown_measured_field", "forged")

    class HostileMeasuredTransition(MeasuredTransition):
        def __eq__(self, other):
            del other
            return True

        def __ne__(self, other):
            del other
            return False

    subclassed = HostileMeasuredTransition(**vars(issued.measured_transition))
    wrong_channel_wire = copy.deepcopy(issued.measured_transition)
    object.__setattr__(
        wrong_channel_wire,
        "channel_order",
        list(wrong_channel_wire.channel_order),
    )
    object.__setattr__(wrong_channel_wire, "transition_sha", "0" * 64)
    object.__setattr__(
        wrong_channel_wire,
        "transition_sha",
        canonical_sha(measured_transition_payload(wrong_channel_wire)),
    )
    unknown_kernel_wire = copy.deepcopy(issued.measured_transition)
    object.__setattr__(
        unknown_kernel_wire.kernel,
        "unknown_kernel_field",
        "forged",
    )

    for measured in (
        unknown,
        subclassed,
        wrong_channel_wire,
        unknown_kernel_wire,
    ):
        hostile = _resign_authority(
            fixture,
            issued,
            measured_transition=measured,
        )
        with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
            fixture.graph.verify(
                hostile,
                fixture.parent,
                fixture.materialization,
            )
        _assert_reason(caught, "TRANSITION_MEASUREMENT_FAILED")


@pytest.mark.parametrize(
    ("measurement_attack", "factory_role"),
    (
        ("support_sha", "actual"),
        ("no_wrap", "actual"),
        ("wrong_sign", "matched_ablated"),
    ),
)
def test_b3_issue_rejects_hostile_owner_core_support_records(
    monkeypatch: pytest.MonkeyPatch,
    measurement_attack: str,
    factory_role: str,
) -> None:
    fixture = _fixture(monkeypatch, measurement_attack=measurement_attack)
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            factory_role,
        )
    _assert_reason(caught, "SUPPORT_INVALID")


def test_b3_issue_rejects_owner_measurement_with_unknown_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, measurement_attack="unknown_field")
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
    _assert_reason(caught, "TRANSITION_MEASUREMENT_FAILED")


def test_b3_issue_rejects_owner_measurement_with_unknown_kernel_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, measurement_attack="unknown_kernel_field")
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
    _assert_reason(caught, "TRANSITION_MEASUREMENT_FAILED")


def test_b3_pair_is_atomic_ordered_and_bound_to_one_live_parent_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch)
    actual = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    matched = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "matched_ablated",
    )
    assert fixture.graph.verify_pair(
        fixture.parent,
        fixture.materialization,
        actual,
        matched,
    ) == (actual, matched)

    for hostile_pair in (
        (matched, actual),
        (actual, actual),
        (matched, matched),
    ):
        with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caught:
            fixture.graph.verify_pair(
                fixture.parent,
                fixture.materialization,
                *hostile_pair,
            )
        _assert_reason(caught, "BRANCH_JOIN_FAILED")

    for hostile_pair in (
        (actual.transition_authority, matched),
        (actual, matched.transition_authority),
    ):
        with pytest.raises((TypeError, fixture.facade.TransitionAuthorityV3Failure)):
            fixture.graph.verify_pair(
                fixture.parent,
                fixture.materialization,
                *hostile_pair,
            )

    equal_copy = _FakeVerifiedMaterializationV3(
        fixture.parent,
        fixture.materialization_body,
    )
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as materialization:
        fixture.graph.verify_pair(
            fixture.parent,
            equal_copy,
            actual,
            matched,
        )
    _assert_reason(materialization, "MATERIALIZATION_INVALID")

    equal_parent = _FakeParentV3(fixture.parent.manifest.parent_freeze_v3_sha)
    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as parent:
        fixture.graph.verify_pair(
            equal_parent,
            fixture.materialization,
            actual,
            matched,
        )
    _assert_reason(parent, "CROSS_PARENT_ROOT")


def test_b3_pair_rejects_cross_splice_between_two_live_materializations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, allow_secondary_materialization=True)
    primary_actual = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    secondary_actual = fixture.graph.issue(
        fixture.parent,
        fixture.secondary_materialization,
        "actual",
    )
    secondary_matched = fixture.graph.issue(
        fixture.parent,
        fixture.secondary_materialization,
        "matched_ablated",
    )

    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as splice:
        fixture.graph.verify_pair(
            fixture.parent,
            fixture.materialization,
            primary_actual,
            secondary_matched,
        )
    _assert_reason(splice, "BRANCH_JOIN_FAILED")

    with pytest.raises(fixture.facade.TransitionAuthorityV3Failure) as caller:
        fixture.graph.verify_pair(
            fixture.parent,
            fixture.materialization,
            secondary_actual,
            secondary_matched,
        )
    _assert_reason(caller, "MATERIALIZATION_INVALID")


def test_b3_rejects_raw_old_caller_fft_projector_and_registry_attacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3.dynamics import VerifiedTransition
    from rulespace_v3.factory import VerifiedFactory
    from rulespace_v3.prestructure import VerifiedPrestructureAuthority

    fixture = _fixture(monkeypatch)
    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    raw = capability.transition_authority
    old_factory = object.__new__(VerifiedFactory)
    old_prestructure = object.__new__(VerifiedPrestructureAuthority)
    old_transition = object.__new__(VerifiedTransition)

    for parent, materialization, role in (
        (object(), fixture.materialization, "actual"),
        (fixture.parent, fixture.materialization_body, "actual"),
        (fixture.parent, {}, "actual"),
        (fixture.parent, old_factory, "actual"),
        (fixture.parent, old_prestructure, "actual"),
    ):
        with pytest.raises((TypeError, fixture.facade.TransitionAuthorityV3Failure)):
            fixture.graph.issue(parent, materialization, role)

    for hostile in (
        old_transition,
        raw.measured_transition,
        raw.prestructure_authority,
        {},
    ):
        with pytest.raises((TypeError, fixture.facade.TransitionAuthorityV3Failure)):
            fixture.graph.verify(
                hostile,
                fixture.parent,
                fixture.materialization,
            )

    forged = object.__new__(fixture.facade.VerifiedTransitionAuthorityV3)
    with pytest.raises((TypeError, ValueError)):
        fixture.graph.reverify(forged)
    with pytest.raises((TypeError, ValueError)):
        fixture.graph.reverify(raw)
    other_graph = fixture.facade._make_transition_authority_v3_graph(
        fixture.facade._ISSUANCE_TOKEN
    )
    with pytest.raises((TypeError, ValueError)):
        other_graph.reverify(capability)

    tampered = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "matched_ablated",
    )
    object.__setattr__(
        tampered,
        "_VerifiedTransitionAuthorityV3__authority_seal",
        "0" * 64,
    )
    with pytest.raises((TypeError, ValueError)):
        fixture.graph.reverify(tampered)

    body_tampered = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "matched_ablated",
    )
    hostile_body = _resign_authority(
        fixture,
        body_tampered.transition_authority,
        factory_binding=fixture.materialization_body.actual_factory_binding,
    )
    object.__setattr__(
        body_tampered,
        "_VerifiedTransitionAuthorityV3__transition_authority",
        hostile_body,
    )
    with pytest.raises((TypeError, ValueError)):
        fixture.graph.reverify(body_tampered)

    forbidden_kwargs = (
        "factory",
        "prestructure",
        "prestructure_authority",
        "transition",
        "kernel",
        "support",
        "support_offsets",
        "state",
        "state_schema_id",
        "channel_order",
        "spatial_shape",
        "dt",
        "boundary",
        "macro_steps",
        "grid",
        "points",
        "fft",
        "fft_projector",
        "per_k_projector",
        "projector",
        "analytic_symbol",
        "registry",
        "replay_callback",
    )
    for keyword in forbidden_kwargs:
        with pytest.raises(TypeError):
            fixture.facade.issue_transition_authority_v3(
                fixture.parent,
                fixture.materialization,
                "actual",
                **{keyword: object()},
            )
        with pytest.raises(TypeError):
            fixture.facade.verify_transition_authority_v3(
                raw,
                fixture.parent,
                fixture.materialization,
                **{keyword: object()},
            )


def test_b3_graph_and_public_api_closures_resist_post_freeze_global_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch)
    baseline = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).transition_authority
    baseline_payload = fixture.authority_payload(baseline)

    def redirected(*args, **kwargs):
        del args, kwargs
        raise AssertionError("post-freeze module global redirect was consulted")

    for name in (
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        "_issue_parent_v3_application_prestructure",
        "_verify_parent_v3_application_prestructure",
        "_reverify_verified_parent_v3_application_prestructure",
        "_measure_bound_realspace_transition",
        "application_scenario_materialization_v3_payload",
        "factory_branch_binding_v3_payload",
        "parent_v3_application_prestructure_payload",
        "_transition_authority_v3_payload_impl",
        "dataclass_fields",
        "canonical_sha",
    ):
        monkeypatch.setattr(fixture.facade, name, redirected, raising=False)

    assert fixture.authority_payload(baseline) == baseline_payload
    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    assert fixture.graph.reverify(capability).transition_authority == (
        capability.transition_authority
    )

    facade = fixture.facade
    issuer = facade.issue_transition_authority_v3
    verifier = facade.verify_transition_authority_v3
    pair_verifier = facade.verify_transition_pair_v3
    production_graph = facade._PRODUCTION_GRAPH
    reachable = _closure_reachable_objects(issuer)
    assert production_graph.issue in reachable
    assert production_graph.verify in _closure_reachable_objects(verifier)
    assert production_graph.verify_pair in _closure_reachable_objects(pair_verifier)
    assert all(
        "_PRODUCTION_GRAPH" not in function.__code__.co_names
        for function in (issuer, verifier, pair_verifier)
    )
    monkeypatch.setattr(
        facade,
        "_PRODUCTION_GRAPH",
        SimpleNamespace(
            issue=redirected,
            verify=redirected,
            verify_pair=redirected,
            reverify=redirected,
        ),
    )
    with pytest.raises(facade.TransitionAuthorityV3Failure) as caught:
        issuer(object(), object(), "actual")
    assert caught.value.reason_id == "MATERIALIZATION_INVALID"


def test_b3_graph_captures_own_record_view_failure_schema_and_weakref_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch)
    facade = fixture.facade
    original_record = facade.TransitionAuthorityV3
    original_wrapper = facade.VerifiedTransitionAuthorityV3
    original_view = facade._VerifiedTransitionAuthorityV3View
    original_failure = facade.TransitionAuthorityV3Failure
    assert facade.TRANSITION_AUTHORITY_V3_SCHEMA_VERSION == (
        "v3m0.transition-authority.v3"
    )

    def redirected(*args, **kwargs):
        del args, kwargs
        raise AssertionError("post-freeze owner-global redirect was consulted")

    monkeypatch.setattr(facade, "TransitionAuthorityV3", redirected)
    monkeypatch.setattr(facade, "VerifiedTransitionAuthorityV3", redirected)
    monkeypatch.setattr(facade, "_VerifiedTransitionAuthorityV3View", redirected)
    monkeypatch.setattr(facade, "TransitionAuthorityV3Failure", redirected)
    monkeypatch.setattr(
        facade,
        "TRANSITION_AUTHORITY_V3_SCHEMA_VERSION",
        "redirected.schema",
    )
    monkeypatch.setattr(
        facade,
        "weakref",
        SimpleNamespace(ref=redirected),
    )

    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    assert type(capability) is original_wrapper
    assert type(capability.transition_authority) is original_record
    assert capability.transition_authority.transition_authority_schema_version == (
        "v3m0.transition-authority.v3"
    )
    view = fixture.graph.reverify(capability)
    assert type(view) is original_view

    fixture.mode["value"] = "executor"
    with pytest.raises(original_failure) as caught:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
    _assert_reason(caught, "EXECUTOR_FAILED")


def test_b3_static_import_dag_private_seams_and_no_legacy_projection_path() -> None:
    path = REPO_ROOT / "rulespace_v3" / "transition_authority_v3.py"
    assert path.is_file()
    assert _direct_rulespace_imports(path) == {
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.dynamics",
        "rulespace_v3.evidence",
        "rulespace_v3.parent_v3_application_prestructure",
    }
    assert {
        "ApplicationScenarioMaterializationV3",
        "FactoryBranchBindingV3",
        "VerifiedV3M0ApplicationScenarioMaterializationV3",
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
    } <= _relative_imported_names(path, "application_materialization_v3")
    assert {
        "MeasuredTransition",
        "_measure_bound_realspace_transition",
        "measured_transition_payload",
    } <= _relative_imported_names(path, "dynamics")
    assert {
        "ParentV3ApplicationPrestructure",
        "VerifiedParentV3ApplicationPrestructure",
        "_issue_parent_v3_application_prestructure",
        "_verify_parent_v3_application_prestructure",
        "_reverify_verified_parent_v3_application_prestructure",
        "parent_v3_application_prestructure_payload",
    } <= _relative_imported_names(path, "parent_v3_application_prestructure")

    tree = ast.parse(path.read_text(encoding="utf-8"))
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    assert not identifiers & {
        "VerifiedPrestructureAuthority",
        "VerifiedTransition",
        "_TransitionAuthority",
        "_issue_verified_transition",
        "_register_measured_transition",
        "measure_transition",
        "verify_measured_transition",
        "transition_symbol",
        "_transition_symbol_from_raw",
        "fft",
        "fftn",
        "ifftn",
        "projector",
        "per_k_projector",
    }


def test_b3_dynamics_static_core_and_legacy_delegation_match_v7() -> None:
    path = REPO_ROOT / "rulespace_v3" / "dynamics.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_make_bound_realspace_transition_core" in functions
    core_factory = functions["_make_bound_realspace_transition_core"]
    core = next(
        node
        for node in ast.walk(core_factory)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_measure_bound_realspace_transition"
    )
    assert [argument.arg for argument in core.args.args] == ["factory"]
    assert [argument.arg for argument in core.args.kwonlyargs] == [
        "parent_freeze_sha",
        "prestructure_authority_sha",
    ]
    assert core.args.vararg is None and core.args.kwarg is None
    core_identifiers = {
        node.id for node in ast.walk(core) if isinstance(node, ast.Name)
    } | {node.attr for node in ast.walk(core) if isinstance(node, ast.Attribute)}
    assert {
        "factory_reverifier",
        "factory_support_builder",
        "factory_executor",
        "canonical_support_builder",
        "no_wrap_validator",
        "outside_mask_builder",
        "positive_zero_validator",
    } <= core_identifiers
    assert not core_identifiers & {
        "VerifiedPrestructureAuthority",
        "_reverify_verified_prestructure_authority",
        "fft",
        "fftn",
        "ifftn",
        "projector",
        "per_k_projector",
        "transition_symbol",
        "_transition_symbol_from_raw",
    }

    assert "_make_remeasure_transition" in functions
    legacy_factory = functions["_make_remeasure_transition"]
    legacy = next(
        node
        for node in ast.walk(legacy_factory)
        if isinstance(node, ast.FunctionDef) and node.name == "_remeasure_transition"
    )
    legacy_calls = [
        node.func.id
        for node in ast.walk(legacy)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert legacy_calls.count("input_binder") == 1
    assert legacy_calls.count("measurement_core") == 1
    assert "_measure_bound_realspace_transition" not in ast.literal_eval(
        next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            )
        )
    )
