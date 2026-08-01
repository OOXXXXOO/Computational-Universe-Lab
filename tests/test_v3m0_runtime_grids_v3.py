"""Strict RED contracts for Parent-v3 runtime grid authorities."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, fields, is_dataclass, replace
import gc
import inspect
from pathlib import Path
from types import SimpleNamespace
import weakref

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
C19_STATE_SCHEMA_ID = "v3m0.c19-real-canonical-state.v2"
C19_CHANNEL_ORDER = tuple(
    channel for pair in range(10) for channel in (f"q{pair}", f"p{pair}")
)
C19_SPATIAL_SHAPE = (8,)
FAILURE_REASON_IDS = (
    "FACTORY_SUPPORT_INVALID",
    "TRANSITION_INVALID",
    "METRIC_ATTESTATION_INVALID",
    "BRANCH_JOIN_FAILED",
    "GRID_DERIVATION_FAILED",
    "CROSS_PARENT_ROOT",
)


@dataclass(frozen=True)
class _FakeFactoryBody:
    factory_sha: str
    factory_role: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    state_shape: tuple[int, ...]
    spatial_ndim: int


class _FakeLiveFactory:
    def __init__(self, factory: _FakeFactoryBody) -> None:
        self.factory = factory


@dataclass(frozen=True)
class _FakeFactoryBinding:
    parent_freeze_v3_sha: str
    branch: str
    factory: _FakeFactoryBody
    support_offsets: tuple[tuple[int, ...], ...]
    support_sha: str
    binding_sha: str


@dataclass(frozen=True)
class _FakeMetricSupportProtocol:
    protocol_sha: str
    metric_kind: str
    metric_support_offsets: tuple[tuple[int, ...], ...]
    metric_support_sha: str


@dataclass(frozen=True)
class _FakeResponseContract:
    dynamics_grid_derivation: object
    bridge_grid_derivation: object
    metric_support_derivation: _FakeMetricSupportProtocol
    response_grid: object
    response_contract_sha: str


@dataclass(frozen=True)
class _FakeScenarioAuthority:
    response_contract: _FakeResponseContract
    scenario_authority_sha: str


@dataclass(frozen=True)
class _FakeApplicationAuthority:
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    application_authority_sha: str


@dataclass(frozen=True)
class _FakeMaterializationBody:
    current_application_authority: _FakeApplicationAuthority
    current_scenario_authority: _FakeScenarioAuthority
    current_scenario_response_contract: _FakeResponseContract
    actual_factory_binding: _FakeFactoryBinding
    matched_ablated_factory_binding: _FakeFactoryBinding
    materialization_sha: str


class _FakeParentV3:
    def __init__(self, parent_freeze_v3_sha: str) -> None:
        self.manifest = SimpleNamespace(parent_freeze_v3_sha=parent_freeze_v3_sha)


class _FakeVerifiedMaterializationV3:
    def __init__(
        self,
        parent: _FakeParentV3,
        materialization: _FakeMaterializationBody,
        actual_factory: _FakeLiveFactory,
        matched_ablated_factory: _FakeLiveFactory,
    ) -> None:
        self.parent = parent
        self._materialization = copy.deepcopy(materialization)
        self.actual_factory = actual_factory
        self.matched_ablated_factory = matched_ablated_factory
        resolver = lambda wrapper: copy.deepcopy(wrapper._materialization)  # noqa: E731
        object.__setattr__(
            self,
            "_FakeVerifiedMaterializationV3__resolver",
            resolver,
        )
        _FAKE_MATERIALIZATION_RESOLVERS[self] = resolver

    @property
    def materialization(self) -> _FakeMaterializationBody:
        resolver = object.__getattribute__(
            self,
            "_FakeVerifiedMaterializationV3__resolver",
        )
        if _FAKE_MATERIALIZATION_RESOLVERS.get(self) is not resolver:
            raise ValueError("fake materialization resolver identity drifted")
        return resolver(self)


_FAKE_MATERIALIZATION_RESOLVERS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


@dataclass(frozen=True)
class _FakeMeasuredTransition:
    parent_freeze_sha: str
    factory_sha: str
    factory_role: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    support_offsets: tuple[tuple[int, ...], ...]
    support_sha: str
    transition_sha: str


@dataclass(frozen=True)
class _FakeTransitionAuthorityV3:
    materialization: _FakeMaterializationBody
    factory_binding: _FakeFactoryBinding
    measured_transition: _FakeMeasuredTransition
    transition_authority_sha: str


class _FakeVerifiedTransitionAuthorityV3:
    def __init__(
        self,
        parent: _FakeParentV3,
        materialization: _FakeVerifiedMaterializationV3,
        transition_authority: _FakeTransitionAuthorityV3,
        factory: _FakeLiveFactory,
    ) -> None:
        self.parent = parent
        self.materialization = materialization
        self._transition_authority = copy.deepcopy(transition_authority)
        self.factory = factory


@dataclass(frozen=True)
class _FakeMetricSignedSupportAttestationV1:
    attestation_schema_version: str
    parent_freeze_v3_sha: str
    current_application_authority_v3_sha: str
    current_scenario_authority_v3_sha: str
    response_contract_v3_sha: str
    metric_support_protocol_sha: str
    application_scenario_materialization_v3_sha: str
    factory_sha: str
    factory_role: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    metric_kind: str
    metric_support_offsets: tuple[tuple[int, ...], ...]
    metric_support_sha: str
    attestation_sha: str


class _FakeVerifiedMetricSignedSupportAttestationV1:
    def __init__(
        self,
        parent: _FakeParentV3,
        materialization: _FakeVerifiedMaterializationV3,
        attestation: _FakeMetricSignedSupportAttestationV1,
        factory: _FakeLiveFactory,
        factory_binding: _FakeFactoryBinding,
    ) -> None:
        self.parent = parent
        self.materialization = materialization
        self._attestation = copy.deepcopy(attestation)
        self.factory = factory
        self.factory_binding = factory_binding


def _module():
    import rulespace_v3.runtime_grids_v3 as facade

    return facade


@pytest.fixture(scope="module")
def c19_response_contract():
    from rulespace_v3.c19_refreeze_v2 import (
        _build_bridge_grid_derivation,
        _build_dynamics_grid_derivation,
        _build_response_grid,
    )

    return SimpleNamespace(
        dynamics_grid_derivation=_build_dynamics_grid_derivation(),
        bridge_grid_derivation=_build_bridge_grid_derivation(),
        response_grid=_build_response_grid(),
        response_contract_sha="c" * 64,
    )


def _wire_value(value: object) -> object:
    if is_dataclass(value):
        return {name: _wire_value(item) for name, item in vars(value).items()}
    if type(value) is tuple:
        return [_wire_value(item) for item in value]
    if type(value) is SimpleNamespace:
        return {name: _wire_value(item) for name, item in vars(value).items()}
    return value


def _payload_without_sha(value: object, sha_field: str) -> dict[str, object]:
    return {
        name: _wire_value(item)
        for name, item in vars(value).items()
        if name != sha_field
    }


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    response_contract: object,
    *,
    root: str = "a",
    fresh_children: bool = False,
):
    facade = _module()
    from rulespace_v3.application_materialization_v3 import (
        ApplicationMaterializationV3Failure,
    )
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.grids import (
        bridge_grid_payload as real_bridge_payload,
        build_bridge_grid_manifest as real_build_bridge,
        build_dynamics_grid_manifest as real_build_dynamics,
        dynamics_grid_payload as real_dynamics_payload,
        verify_bridge_grid_manifest as real_verify_bridge,
        verify_dynamics_grid_manifest as real_verify_dynamics,
    )
    from rulespace_v3.metric_support_authority_v1 import (
        MetricSupportAuthorityV1Failure,
    )
    from rulespace_v3.transition_authority_v3 import TransitionAuthorityV3Failure

    parent_sha = root * 64
    parent = _FakeParentV3(parent_sha)
    dynamics_protocol = response_contract.dynamics_grid_derivation
    bridge_protocol = response_contract.bridge_grid_derivation
    metric_protocol = _FakeMetricSupportProtocol(
        "c" * 64,
        "constant-state-v1",
        ((0,),),
        "d" * 64,
    )
    response = _FakeResponseContract(
        dynamics_protocol,
        bridge_protocol,
        metric_protocol,
        response_contract.response_grid,
        response_contract.response_contract_sha,
    )
    scenario = _FakeScenarioAuthority(response, "d" * 64)
    application = _FakeApplicationAuthority(
        C19_STATE_SCHEMA_ID,
        C19_CHANNEL_ORDER,
        C19_SPATIAL_SHAPE,
        "e" * 64,
    )
    actual_factory_body = _FakeFactoryBody(
        "1" * 64,
        "actual",
        C19_STATE_SCHEMA_ID,
        C19_CHANNEL_ORDER,
        (20, 8),
        1,
    )
    matched_factory_body = replace(
        actual_factory_body,
        factory_sha="2" * 64,
        factory_role="matched_ablated",
    )
    actual_factory = _FakeLiveFactory(actual_factory_body)
    matched_factory = _FakeLiveFactory(matched_factory_body)
    actual_binding = _FakeFactoryBinding(
        parent_sha,
        "actual",
        actual_factory_body,
        ((0,),),
        "3" * 64,
        "4" * 64,
    )
    matched_binding = _FakeFactoryBinding(
        parent_sha,
        "matched_ablated",
        matched_factory_body,
        ((0,),),
        "5" * 64,
        "6" * 64,
    )
    materialization_body = _FakeMaterializationBody(
        application,
        scenario,
        response,
        actual_binding,
        matched_binding,
        "7" * 64,
    )
    materialization = _FakeVerifiedMaterializationV3(
        parent,
        materialization_body,
        actual_factory,
        matched_factory,
    )

    def transition_body(
        role: str,
        binding: _FakeFactoryBinding,
    ) -> _FakeTransitionAuthorityV3:
        measured = _FakeMeasuredTransition(
            parent_sha,
            binding.factory.factory_sha,
            role,
            C19_STATE_SCHEMA_ID,
            C19_CHANNEL_ORDER,
            C19_SPATIAL_SHAPE,
            binding.support_offsets,
            binding.support_sha,
            ("8" if role == "actual" else "9") * 64,
        )
        return _FakeTransitionAuthorityV3(
            copy.deepcopy(materialization_body),
            binding,
            measured,
            ("a" if role == "actual" else "b") * 64,
        )

    actual_transition_body = transition_body("actual", actual_binding)
    matched_transition_body = transition_body("matched_ablated", matched_binding)
    actual_transition = _FakeVerifiedTransitionAuthorityV3(
        parent,
        materialization,
        actual_transition_body,
        actual_factory,
    )
    matched_transition = _FakeVerifiedTransitionAuthorityV3(
        parent,
        materialization,
        matched_transition_body,
        matched_factory,
    )

    def metric_body(
        role: str,
        binding: _FakeFactoryBinding,
    ) -> _FakeMetricSignedSupportAttestationV1:
        return _FakeMetricSignedSupportAttestationV1(
            "v3m0.metric-signed-support-attestation.v1",
            parent_sha,
            application.application_authority_sha,
            scenario.scenario_authority_sha,
            response.response_contract_sha,
            "c" * 64,
            materialization_body.materialization_sha,
            binding.factory.factory_sha,
            role,
            C19_STATE_SCHEMA_ID,
            C19_CHANNEL_ORDER,
            C19_SPATIAL_SHAPE,
            "constant-state-v1",
            ((0,),),
            "d" * 64,
            ("e" if role == "actual" else "f") * 64,
        )

    actual_metric_body = metric_body("actual", actual_binding)
    matched_metric_body = metric_body("matched_ablated", matched_binding)
    actual_metric = _FakeVerifiedMetricSignedSupportAttestationV1(
        parent,
        materialization,
        actual_metric_body,
        actual_factory,
        actual_binding,
    )
    matched_metric = _FakeVerifiedMetricSignedSupportAttestationV1(
        parent,
        materialization,
        matched_metric_body,
        matched_factory,
        matched_binding,
    )

    calls = SimpleNamespace(
        materialization=[],
        transition=[],
        metric=[],
        factory_children=[],
        bridge_build=[],
        bridge_verify=[],
        dynamics_build=[],
        dynamics_verify=[],
    )
    mode = {"value": None}

    def child_factory(
        canonical: _FakeLiveFactory,
    ) -> _FakeLiveFactory:
        if not fresh_children:
            return canonical
        child = _FakeLiveFactory(copy.deepcopy(canonical.factory))
        calls.factory_children.append((canonical, child))
        return child

    def require_materialization(observed_parent, observed_materialization):
        calls.materialization.append((observed_parent, observed_materialization))
        if mode["value"] == "factory_support":
            raise ApplicationMaterializationV3Failure(
                "FACTORY_WIRE_DRIFT",
                "forced factory support replay failure",
            )
        if mode["value"] == "cross_root":
            raise ApplicationMaterializationV3Failure(
                "CROSS_PARENT_ROOT",
                "forced cross-Parent materialization",
            )
        if type(observed_parent) is not _FakeParentV3:
            raise TypeError("exact live Parent-v3 required")
        if type(observed_materialization) is not _FakeVerifiedMaterializationV3:
            raise TypeError("exact live B2 materialization required")
        if observed_materialization.parent is not observed_parent:
            raise ApplicationMaterializationV3Failure(
                "CROSS_PARENT_ROOT",
                "materialization belongs to another live Parent",
            )
        body = observed_materialization.materialization
        return SimpleNamespace(
            parent=observed_parent,
            materialization=body,
            actual_factory=child_factory(actual_factory),
            matched_ablated_factory=child_factory(matched_factory),
        )

    def reverify_transition(observed):
        calls.transition.append(observed)
        if mode["value"] == "transition":
            raise TransitionAuthorityV3Failure(
                "TRANSITION_MEASUREMENT_FAILED",
                "forced transition replay failure",
            )
        if type(observed) is not _FakeVerifiedTransitionAuthorityV3:
            raise TypeError("exact live B3 transition required")
        role = observed._transition_authority.measured_transition.factory_role
        binding = actual_binding if role == "actual" else matched_binding
        return SimpleNamespace(
            transition_authority=copy.deepcopy(observed._transition_authority),
            parent=observed.parent,
            materialization=observed.materialization,
            factory=child_factory(observed.factory),
            factory_binding=binding,
        )

    def reverify_metric(observed):
        calls.metric.append(observed)
        if mode["value"] == "metric":
            raise MetricSupportAuthorityV1Failure(
                "METRIC_REPLAY_FAILED",
                "forced metric replay failure",
            )
        if type(observed) is not _FakeVerifiedMetricSignedSupportAttestationV1:
            raise TypeError("exact live B4 metric attestation required")
        return SimpleNamespace(
            attestation=copy.deepcopy(observed._attestation),
            parent=observed.parent,
            materialization=observed.materialization,
            factory=child_factory(observed.factory),
            factory_binding=observed.factory_binding,
        )

    def build_bridge(spatial_shape, signed_support):
        calls.bridge_build.append((spatial_shape, signed_support))
        if mode["value"] == "grid_bridge":
            raise ValueError("forced bridge grid derivation failure")
        return real_build_bridge(spatial_shape, signed_support)

    def verify_bridge(grid, spatial_shape, signed_support):
        calls.bridge_verify.append((grid, spatial_shape, signed_support))
        return real_verify_bridge(grid, spatial_shape, signed_support)

    def build_dynamics(transition_support, metric_support):
        calls.dynamics_build.append((transition_support, metric_support))
        if mode["value"] == "grid_dynamics":
            raise ValueError("forced dynamics grid derivation failure")
        return real_build_dynamics(transition_support, metric_support)

    def verify_dynamics(grid, transition_support, metric_support):
        calls.dynamics_verify.append((grid, transition_support, metric_support))
        return real_verify_dynamics(grid, transition_support, metric_support)

    def materialization_payload(value):
        return _payload_without_sha(value, "materialization_sha")

    def binding_payload(value):
        return _payload_without_sha(value, "binding_sha")

    def transition_payload(value):
        return _payload_without_sha(value, "transition_authority_sha")

    def metric_payload(value):
        return _payload_without_sha(value, "attestation_sha")

    monkeypatch.setattr(
        facade,
        "ApplicationMaterializationV3Failure",
        ApplicationMaterializationV3Failure,
    )
    monkeypatch.setattr(
        facade, "TransitionAuthorityV3Failure", TransitionAuthorityV3Failure
    )
    monkeypatch.setattr(
        facade,
        "MetricSupportAuthorityV1Failure",
        MetricSupportAuthorityV1Failure,
    )
    monkeypatch.setattr(
        facade,
        "VerifiedV3M0ApplicationScenarioMaterializationV3",
        _FakeVerifiedMaterializationV3,
    )
    monkeypatch.setattr(
        facade, "ApplicationScenarioMaterializationV3", _FakeMaterializationBody
    )
    monkeypatch.setattr(facade, "FactoryBranchBindingV3", _FakeFactoryBinding)
    monkeypatch.setattr(
        facade,
        "VerifiedTransitionAuthorityV3",
        _FakeVerifiedTransitionAuthorityV3,
    )
    monkeypatch.setattr(facade, "TransitionAuthorityV3", _FakeTransitionAuthorityV3)
    monkeypatch.setattr(
        facade,
        "VerifiedMetricSignedSupportAttestationV1",
        _FakeVerifiedMetricSignedSupportAttestationV1,
    )
    monkeypatch.setattr(
        facade,
        "MetricSignedSupportAttestationV1",
        _FakeMetricSignedSupportAttestationV1,
    )
    monkeypatch.setattr(
        facade,
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        require_materialization,
    )
    monkeypatch.setattr(
        facade,
        "_reverify_verified_transition_authority_v3",
        reverify_transition,
    )
    monkeypatch.setattr(
        facade,
        "_reverify_verified_metric_signed_support_attestation_v1",
        reverify_metric,
    )
    monkeypatch.setattr(
        facade,
        "application_scenario_materialization_v3_payload",
        materialization_payload,
    )
    monkeypatch.setattr(
        facade,
        "factory_branch_binding_v3_payload",
        binding_payload,
    )
    monkeypatch.setattr(
        facade,
        "transition_authority_v3_payload",
        transition_payload,
    )
    monkeypatch.setattr(
        facade,
        "metric_signed_support_attestation_v1_payload",
        metric_payload,
    )
    monkeypatch.setattr(facade, "canonical_sha", canonical_sha)
    monkeypatch.setattr(facade, "bridge_grid_payload", real_bridge_payload)
    monkeypatch.setattr(facade, "dynamics_grid_payload", real_dynamics_payload)
    monkeypatch.setattr(facade, "build_bridge_grid_manifest", build_bridge)
    monkeypatch.setattr(facade, "verify_bridge_grid_manifest", verify_bridge)
    monkeypatch.setattr(facade, "build_dynamics_grid_manifest", build_dynamics)
    monkeypatch.setattr(facade, "verify_dynamics_grid_manifest", verify_dynamics)

    bridge_payload = facade._make_bridge_grid_authority_v3_payload_api(
        facade._bridge_grid_authority_v3_payload_impl,
        body_type=facade.BridgeGridAuthorityV3,
        materialization_type=_FakeMaterializationBody,
        binding_type=_FakeFactoryBinding,
        record_validator=facade._exact_record,
        materialization_payload_builder=materialization_payload,
        binding_payload_builder=binding_payload,
        protocol_record_builder=facade._protocol_record,
        grid_payload_builder=real_bridge_payload,
    )
    dynamics_payload = facade._make_dynamics_grid_authority_v3_payload_api(
        facade._dynamics_grid_authority_v3_payload_impl,
        body_type=facade.DynamicsGridAuthorityV3,
        transition_type=_FakeTransitionAuthorityV3,
        metric_type=_FakeMetricSignedSupportAttestationV1,
        binding_type=_FakeFactoryBinding,
        record_validator=facade._exact_record,
        transition_payload_builder=transition_payload,
        metric_payload_builder=metric_payload,
        protocol_record_builder=facade._protocol_record,
        grid_payload_builder=real_dynamics_payload,
    )

    graph = facade._make_runtime_grids_v3_graph(facade._ISSUANCE_TOKEN)
    return SimpleNamespace(
        facade=facade,
        graph=graph,
        parent=parent,
        materialization=materialization,
        materialization_body=materialization_body,
        actual_factory=actual_factory,
        matched_factory=matched_factory,
        actual_binding=actual_binding,
        matched_binding=matched_binding,
        dynamics_protocol=dynamics_protocol,
        bridge_protocol=bridge_protocol,
        response_grid=response.response_grid,
        actual_transition=actual_transition,
        matched_transition=matched_transition,
        actual_transition_body=actual_transition_body,
        matched_transition_body=matched_transition_body,
        actual_metric=actual_metric,
        matched_metric=matched_metric,
        actual_metric_body=actual_metric_body,
        matched_metric_body=matched_metric_body,
        calls=calls,
        mode=mode,
        bridge_payload=bridge_payload,
        dynamics_payload=dynamics_payload,
    )


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


def test_b5_exact_seven_raw_records_three_apis_two_opaques_and_failures() -> None:
    import rulespace_v3.grids as grids
    import rulespace_v3.parent_freeze as parent_freeze

    facade = _module()
    assert facade.DirectionPathClosure is parent_freeze.DirectionPathClosure
    for name in (
        "DirectionManifest",
        "ResponseKGridManifest",
        "DynamicsKGridManifest",
        "BridgeKGridManifest",
    ):
        assert getattr(facade, name) is getattr(grids, name)

    assert [item.name for item in fields(facade.DirectionPathClosure)] == [
        "closure_id",
        "first_path_id",
        "first_path_position",
        "second_path_id",
        "second_path_position",
        "reciprocal_index",
    ]
    assert [item.name for item in fields(facade.DirectionManifest)] == [
        "direction_schema_version",
        "direction_ids",
        "primitive_directions",
        "path_ids",
        "ordered_paths",
        "closure_path_pairs",
        "direction_manifest_sha",
    ]
    assert [item.name for item in fields(facade.ResponseKGridManifest)] == [
        "grid_schema_version",
        "qualification_profile",
        "spatial_ndim",
        "torus_denominators",
        "reciprocal_indices",
        "direction_manifest",
        "response_grid_sha",
    ]
    assert [item.name for item in fields(facade.DynamicsKGridManifest)] == [
        "grid_schema_version",
        "qualification_profile",
        "spatial_ndim",
        "torus_denominators",
        "reciprocal_indices",
        "dynamics_grid_sha",
    ]
    assert [item.name for item in fields(facade.BridgeKGridManifest)] == [
        "grid_schema_version",
        "spatial_shape",
        "torus_denominators",
        "reciprocal_indices",
        "bridge_grid_sha",
    ]
    assert [item.name for item in fields(facade.BridgeGridAuthorityV3)] == [
        "grid_authority_schema_version",
        "materialization",
        "factory_binding",
        "derivation_protocol",
        "bridge_grid",
        "grid_authority_sha",
    ]
    assert [item.name for item in fields(facade.DynamicsGridAuthorityV3)] == [
        "grid_authority_schema_version",
        "transition_authority",
        "metric_support_attestation",
        "derivation_protocol",
        "dynamics_grid",
        "grid_authority_sha",
    ]
    assert tuple(
        inspect.signature(facade.derive_bridge_grid_authority_v3).parameters
    ) == ("parent", "materialization", "factory_role")
    assert tuple(
        inspect.signature(facade.derive_dynamics_grid_authority_v3).parameters
    ) == ("parent", "transition", "metric")
    assert tuple(
        inspect.signature(facade.verify_runtime_grid_authorities_v3).parameters
    ) == ("bridge_grid", "dynamics_grid")
    assert tuple(
        inspect.signature(facade._reverify_verified_bridge_grid_authority_v3).parameters
    ) == ("bridge_grid",)
    assert tuple(
        inspect.signature(
            facade._reverify_verified_dynamics_grid_authority_v3
        ).parameters
    ) == ("dynamics_grid",)
    assert [
        item.name for item in fields(facade._VerifiedBridgeGridAuthorityV3View)
    ] == [
        "grid_authority",
        "parent",
        "materialization",
        "factory",
        "factory_binding",
    ]
    assert [
        item.name for item in fields(facade._VerifiedDynamicsGridAuthorityV3View)
    ] == [
        "grid_authority",
        "parent",
        "transition",
        "metric_attestation",
    ]
    assert facade._FAILURE_REASON_IDS == frozenset(FAILURE_REASON_IDS)
    for reason_id in FAILURE_REASON_IDS:
        failure = facade.RuntimeGridAuthorityV3Failure(reason_id, "probe")
        assert failure.reason_id == reason_id
        assert failure.detail == "probe"
    with pytest.raises(ValueError, match="reason"):
        facade.RuntimeGridAuthorityV3Failure("CALLER_POINTS_ACCEPTED", "probe")

    required_surface = (
        "BridgeGridAuthorityV3",
        "BridgeKGridManifest",
        "DirectionManifest",
        "DirectionPathClosure",
        "DynamicsGridAuthorityV3",
        "DynamicsKGridManifest",
        "ResponseKGridManifest",
        "RuntimeGridAuthorityV3Failure",
        "VerifiedBridgeGridAuthorityV3",
        "VerifiedDynamicsGridAuthorityV3",
        "bridge_grid_authority_v3_payload",
        "derive_bridge_grid_authority_v3",
        "derive_dynamics_grid_authority_v3",
        "dynamics_grid_authority_v3_payload",
        "verify_runtime_grid_authorities_v3",
    )
    assert tuple(facade.__all__) == required_surface
    assert not {
        "_VerifiedBridgeGridAuthorityV3View",
        "_VerifiedDynamicsGridAuthorityV3View",
        "_reverify_verified_bridge_grid_authority_v3",
        "_reverify_verified_dynamics_grid_authority_v3",
    } & set(facade.__all__)


def test_b5_c19_response_and_zero_support_grids_are_exact_noninterchangeable_types(
    c19_response_contract,
) -> None:
    from rulespace_v3.grids import (
        BridgeKGridManifest,
        DynamicsKGridManifest,
        ResponseKGridManifest,
        build_bridge_grid_manifest,
        build_dynamics_grid_manifest,
    )

    facade = _module()
    response = c19_response_contract.response_grid
    dynamics = build_dynamics_grid_manifest(((0,),), ((0,),))
    bridge = build_bridge_grid_manifest(C19_SPATIAL_SHAPE, ((0,),))
    assert type(response) is ResponseKGridManifest
    assert type(dynamics) is DynamicsKGridManifest
    assert type(bridge) is BridgeKGridManifest
    assert len({type(response), type(dynamics), type(bridge)}) == 3

    assert response.grid_schema_version == "v3m0.response-k-grid.v1"
    assert response.qualification_profile == "directional-momentum-shell-path-v1"
    assert response.spatial_ndim == 1
    assert response.torus_denominators == (8,)
    assert response.reciprocal_indices == ((1,),)
    assert response.direction_manifest.direction_ids == ("positive-axis",)
    assert response.direction_manifest.primitive_directions == ((1,),)
    assert response.direction_manifest.path_ids == ("positive-axis-path",)
    assert response.direction_manifest.ordered_paths == (((1,),),)
    assert response.direction_manifest.closure_path_pairs == ()

    assert dynamics.grid_schema_version == "v3m0.dynamics-k-grid.v1"
    assert dynamics.qualification_profile == "exact-offset-zero-v1"
    assert dynamics.spatial_ndim == 1
    assert dynamics.torus_denominators == (1,)
    assert dynamics.reciprocal_indices == ((0,),)
    assert bridge.grid_schema_version == "v3m0.bridge-k-grid.v1"
    assert bridge.spatial_shape == (8,)
    assert bridge.torus_denominators == (8,)
    assert bridge.reciprocal_indices == ((0,),)
    assert facade.ResponseKGridManifest is ResponseKGridManifest
    assert facade.DynamicsKGridManifest is DynamicsKGridManifest
    assert facade.BridgeKGridManifest is BridgeKGridManifest


def test_b5_raw_grid_algorithms_retain_nonzero_support_fallbacks() -> None:
    from rulespace_v3.grids import (
        build_bridge_grid_manifest,
        build_dynamics_grid_manifest,
    )

    nonzero_support = ((-1,), (0,), (1,))
    dynamics = build_dynamics_grid_manifest(nonzero_support, ((0,),))
    bridge = build_bridge_grid_manifest(C19_SPATIAL_SHAPE, nonzero_support)

    assert dynamics.qualification_profile == "cartesian-full-64-v1"
    assert dynamics.torus_denominators == (64,)
    assert dynamics.reciprocal_indices == tuple((index,) for index in range(64))
    assert bridge.torus_denominators == (8,)
    assert bridge.reciprocal_indices == ((0,), (1,), (7,))


def test_b5_frozen_live_c19_has_origin_support_on_both_factory_roles() -> None:
    from rulespace_v3.parent_v3_contracts import (
        build_c19_current_application_authority_v3,
    )

    runtime = build_c19_current_application_authority_v3().runtime_construction
    assert runtime.actual_support_offsets == ((0,),)
    assert runtime.matched_support_offsets == ((0,),)


@pytest.mark.parametrize("attack_kind", ("str-subclass", "equality-spoof"))
def test_b5_bridge_role_requires_exact_frozen_literal(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    attack_kind: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    if attack_kind == "str-subclass":

        class StrAlias(str):
            pass

        hostile_role = StrAlias("actual")
    else:

        class EqualObject:
            def __eq__(self, other):
                return other == "actual"

            def __hash__(self):
                return hash("actual")

        hostile_role = EqualObject()

    with pytest.raises(fixture.facade.RuntimeGridAuthorityV3Failure) as caught:
        fixture.graph.derive_bridge(
            fixture.parent,
            fixture.materialization,
            hostile_role,
        )
    assert caught.value.reason_id == "BRANCH_JOIN_FAILED"


@pytest.mark.parametrize(
    ("role", "support", "expected_points"),
    (
        ("actual", ((0,),), ((0,),)),
        ("matched_ablated", ((0,),), ((0,),)),
    ),
)
def test_b5_bridge_is_uniquely_derived_from_live_b2_factory_support(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    role: str,
    support: tuple[tuple[int, ...], ...],
    expected_points: tuple[tuple[int, ...], ...],
) -> None:
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch, c19_response_contract)
    capability = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        role,
    )
    body = capability.bridge_grid_authority
    binding = fixture.actual_binding if role == "actual" else fixture.matched_binding
    assert type(capability) is fixture.facade.VerifiedBridgeGridAuthorityV3
    assert type(body) is fixture.facade.BridgeGridAuthorityV3
    assert body.grid_authority_schema_version == "v3m0.bridge-grid-authority.v3"
    assert body.materialization == fixture.materialization_body
    assert body.factory_binding == binding
    assert body.derivation_protocol == fixture.bridge_protocol
    assert type(body.bridge_grid) is fixture.facade.BridgeKGridManifest
    assert body.bridge_grid.spatial_shape == (8,)
    assert body.bridge_grid.torus_denominators == (8,)
    assert body.bridge_grid.reciprocal_indices == expected_points
    payload = fixture.bridge_payload(body)
    assert set(payload) == {
        "grid_authority_schema_version",
        "materialization",
        "factory_binding",
        "derivation_protocol",
        "bridge_grid",
    }
    assert payload["materialization"]["current_application_authority"]
    assert payload["materialization"]["materialization_sha"] == "7" * 64
    assert payload["factory_binding"]["support_offsets"] == [
        list(item) for item in support
    ]
    assert payload["factory_binding"]["binding_sha"] == binding.binding_sha
    assert payload["derivation_protocol"]["derivation_algorithm"] == (
        fixture.bridge_protocol.derivation_algorithm
    )
    assert payload["derivation_protocol"]["protocol_sha"] == (
        fixture.bridge_protocol.protocol_sha
    )
    assert payload["bridge_grid"]["reciprocal_indices"] == [
        list(item) for item in expected_points
    ]
    assert payload["bridge_grid"]["bridge_grid_sha"] == (
        body.bridge_grid.bridge_grid_sha
    )
    assert body.grid_authority_sha == canonical_sha(payload)
    assert fixture.calls.materialization == [(fixture.parent, fixture.materialization)]
    assert fixture.calls.bridge_build == [((8,), support)]
    assert fixture.calls.transition == []
    assert fixture.calls.metric == []
    assert fixture.calls.dynamics_build == []


@pytest.mark.parametrize(
    ("role", "profile", "denominators", "point_count"),
    (
        ("actual", "exact-offset-zero-v1", (1,), 1),
        ("matched_ablated", "exact-offset-zero-v1", (1,), 1),
    ),
)
def test_b5_dynamics_is_uniquely_derived_from_live_b3_and_b4_supports(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    role: str,
    profile: str,
    denominators: tuple[int, ...],
    point_count: int,
) -> None:
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch, c19_response_contract)
    transition = (
        fixture.actual_transition if role == "actual" else fixture.matched_transition
    )
    metric = fixture.actual_metric if role == "actual" else fixture.matched_metric
    transition_body = (
        fixture.actual_transition_body
        if role == "actual"
        else fixture.matched_transition_body
    )
    metric_body = (
        fixture.actual_metric_body if role == "actual" else fixture.matched_metric_body
    )
    capability = fixture.graph.derive_dynamics(
        fixture.parent,
        transition,
        metric,
    )
    body = capability.dynamics_grid_authority
    assert type(capability) is fixture.facade.VerifiedDynamicsGridAuthorityV3
    assert type(body) is fixture.facade.DynamicsGridAuthorityV3
    assert body.grid_authority_schema_version == "v3m0.dynamics-grid-authority.v3"
    assert body.transition_authority == transition_body
    assert body.metric_support_attestation == metric_body
    assert body.derivation_protocol == fixture.dynamics_protocol
    assert type(body.dynamics_grid) is fixture.facade.DynamicsKGridManifest
    assert body.dynamics_grid.qualification_profile == profile
    assert body.dynamics_grid.torus_denominators == denominators
    assert len(body.dynamics_grid.reciprocal_indices) == point_count
    assert body.dynamics_grid.reciprocal_indices[0] == (0,)
    payload = fixture.dynamics_payload(body)
    assert set(payload) == {
        "grid_authority_schema_version",
        "transition_authority",
        "metric_support_attestation",
        "derivation_protocol",
        "dynamics_grid",
    }
    assert payload["transition_authority"]["measured_transition"]
    assert payload["transition_authority"]["transition_authority_sha"] == (
        transition_body.transition_authority_sha
    )
    assert payload["metric_support_attestation"]["metric_support_offsets"] == [[0]]
    assert payload["metric_support_attestation"]["attestation_sha"] == (
        metric_body.attestation_sha
    )
    assert payload["derivation_protocol"]["derivation_algorithm"] == (
        fixture.dynamics_protocol.derivation_algorithm
    )
    assert payload["derivation_protocol"]["protocol_sha"] == (
        fixture.dynamics_protocol.protocol_sha
    )
    assert payload["dynamics_grid"]["dynamics_grid_sha"] == (
        body.dynamics_grid.dynamics_grid_sha
    )
    assert body.grid_authority_sha == canonical_sha(payload)
    assert fixture.calls.transition == [transition]
    assert fixture.calls.metric == [metric]
    assert fixture.calls.materialization == []
    assert fixture.calls.dynamics_build == [
        (
            transition_body.measured_transition.support_offsets,
            metric_body.metric_support_offsets,
        )
    ]
    assert fixture.calls.bridge_build == []


@pytest.mark.parametrize("role", ("actual", "matched_ablated"))
def test_b5_pair_reverification_replays_both_authorities_and_preserves_identity(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    role: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    transition = (
        fixture.actual_transition if role == "actual" else fixture.matched_transition
    )
    metric = fixture.actual_metric if role == "actual" else fixture.matched_metric
    bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        role,
    )
    dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        transition,
        metric,
    )
    before = (
        len(fixture.calls.materialization),
        len(fixture.calls.transition),
        len(fixture.calls.metric),
        len(fixture.calls.bridge_build),
        len(fixture.calls.dynamics_build),
    )
    verified_bridge, verified_dynamics = fixture.graph.verify_pair(
        bridge,
        dynamics,
    )
    assert verified_bridge is bridge
    assert verified_dynamics is dynamics
    after = (
        len(fixture.calls.materialization),
        len(fixture.calls.transition),
        len(fixture.calls.metric),
        len(fixture.calls.bridge_build),
        len(fixture.calls.dynamics_build),
    )
    assert tuple(end - start for start, end in zip(before, after)) == (1, 1, 1, 1, 1)


def test_b5_private_b6_views_replay_live_authorities_and_preserve_upstream_identity(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )
    bridge_body = bridge.bridge_grid_authority
    dynamics_body = dynamics.dynamics_grid_authority
    before = (
        len(fixture.calls.materialization),
        len(fixture.calls.transition),
        len(fixture.calls.metric),
        len(fixture.calls.bridge_build),
        len(fixture.calls.dynamics_build),
    )

    bridge_view = fixture.graph.reverify_bridge(bridge)
    dynamics_view = fixture.graph.reverify_dynamics(dynamics)

    assert type(bridge_view) is (fixture.facade._VerifiedBridgeGridAuthorityV3View)
    assert bridge_view.grid_authority == bridge_body
    assert bridge_view.grid_authority is not bridge_body
    assert bridge_view.parent is fixture.parent
    assert bridge_view.materialization is fixture.materialization
    assert bridge_view.factory is fixture.actual_factory
    assert bridge_view.factory_binding == fixture.actual_binding
    assert type(dynamics_view) is (fixture.facade._VerifiedDynamicsGridAuthorityV3View)
    assert dynamics_view.grid_authority == dynamics_body
    assert dynamics_view.grid_authority is not dynamics_body
    assert dynamics_view.parent is fixture.parent
    assert dynamics_view.transition is fixture.actual_transition
    assert dynamics_view.metric_attestation is fixture.actual_metric
    after = (
        len(fixture.calls.materialization),
        len(fixture.calls.transition),
        len(fixture.calls.metric),
        len(fixture.calls.bridge_build),
        len(fixture.calls.dynamics_build),
    )
    assert tuple(end - start for start, end in zip(before, after)) == (
        1,
        1,
        1,
        1,
        1,
    )


def test_b5_replay_joins_equivalent_fresh_child_factories_by_bound_body(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(
        monkeypatch,
        c19_response_contract,
        fresh_children=True,
    )
    bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )

    bridge_view = fixture.graph.reverify_bridge(bridge)
    dynamics_view = fixture.graph.reverify_dynamics(dynamics)
    assert bridge_view.parent is fixture.parent
    assert bridge_view.materialization is fixture.materialization
    assert bridge_view.factory is not fixture.actual_factory
    assert bridge_view.factory.factory == fixture.actual_factory.factory
    assert bridge_view.factory_binding == fixture.actual_binding
    assert dynamics_view.parent is fixture.parent
    assert dynamics_view.transition is fixture.actual_transition
    assert dynamics_view.metric_attestation is fixture.actual_metric

    verified_bridge, verified_dynamics = fixture.graph.verify_pair(
        bridge,
        dynamics,
    )
    assert verified_bridge is bridge
    assert verified_dynamics is dynamics
    assert len(fixture.calls.factory_children) >= 5
    assert all(
        child is not canonical and child.factory == canonical.factory
        for canonical, child in fixture.calls.factory_children
    )
    children = [child for _, child in fixture.calls.factory_children]
    assert len({id(child) for child in children}) == len(children)


@pytest.mark.parametrize(
    ("mode", "operation", "reason_id"),
    (
        ("factory_support", "bridge", "FACTORY_SUPPORT_INVALID"),
        ("transition", "dynamics", "TRANSITION_INVALID"),
        ("metric", "dynamics", "METRIC_ATTESTATION_INVALID"),
        ("grid_bridge", "bridge", "GRID_DERIVATION_FAILED"),
        ("grid_dynamics", "dynamics", "GRID_DERIVATION_FAILED"),
        ("cross_root", "bridge", "CROSS_PARENT_ROOT"),
    ),
)
def test_b5_routes_each_upstream_and_derivation_failure_exactly(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    mode: str,
    operation: str,
    reason_id: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    fixture.mode["value"] = mode
    with pytest.raises(fixture.facade.RuntimeGridAuthorityV3Failure) as caught:
        if operation == "bridge":
            fixture.graph.derive_bridge(
                fixture.parent,
                fixture.materialization,
                "actual",
            )
        else:
            fixture.graph.derive_dynamics(
                fixture.parent,
                fixture.actual_transition,
                fixture.actual_metric,
            )
    assert caught.value.reason_id == reason_id


def test_b5_cross_branch_pair_and_internal_lineage_splices_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    with pytest.raises(fixture.facade.RuntimeGridAuthorityV3Failure) as joined:
        fixture.graph.derive_dynamics(
            fixture.parent,
            fixture.actual_transition,
            fixture.matched_metric,
        )
    assert joined.value.reason_id == "BRANCH_JOIN_FAILED"

    actual_bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    matched_dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.matched_transition,
        fixture.matched_metric,
    )
    with pytest.raises(fixture.facade.RuntimeGridAuthorityV3Failure) as pair:
        fixture.graph.verify_pair(actual_bridge, matched_dynamics)
    assert pair.value.reason_id == "BRANCH_JOIN_FAILED"

    hostile_transition_body = copy.deepcopy(fixture.actual_transition_body)
    object.__setattr__(
        hostile_transition_body.measured_transition,
        "parent_freeze_sha",
        "9" * 64,
    )
    hostile_transition = _FakeVerifiedTransitionAuthorityV3(
        fixture.parent,
        fixture.materialization,
        hostile_transition_body,
        fixture.actual_factory,
    )
    with pytest.raises(fixture.facade.RuntimeGridAuthorityV3Failure) as root:
        fixture.graph.derive_dynamics(
            fixture.parent,
            hostile_transition,
            fixture.actual_metric,
        )
    assert root.value.reason_id == "CROSS_PARENT_ROOT"


def test_b5_same_role_materialization_factory_and_binding_splices_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)

    wrong_materialization = replace(
        fixture.actual_transition_body.materialization,
        materialization_sha="8" * 64,
    )
    wrong_transition_materialization = replace(
        fixture.actual_transition_body,
        materialization=wrong_materialization,
    )
    wrong_transition_factory = replace(
        fixture.actual_transition_body,
        measured_transition=replace(
            fixture.actual_transition_body.measured_transition,
            factory_sha="8" * 64,
        ),
    )
    wrong_transition_binding = replace(
        fixture.actual_transition_body,
        factory_binding=replace(
            fixture.actual_binding,
            binding_sha="8" * 64,
        ),
    )
    hostile_transitions = (
        wrong_transition_materialization,
        wrong_transition_factory,
        wrong_transition_binding,
    )
    for body in hostile_transitions:
        transition = _FakeVerifiedTransitionAuthorityV3(
            fixture.parent,
            fixture.materialization,
            body,
            fixture.actual_factory,
        )
        with pytest.raises(fixture.facade.RuntimeGridAuthorityV3Failure) as caught:
            fixture.graph.derive_dynamics(
                fixture.parent,
                transition,
                fixture.actual_metric,
            )
        assert caught.value.reason_id == "BRANCH_JOIN_FAILED"

    wrong_metric_materialization = replace(
        fixture.actual_metric_body,
        application_scenario_materialization_v3_sha="8" * 64,
    )
    wrong_metric_factory = replace(
        fixture.actual_metric_body,
        factory_sha="8" * 64,
    )
    wrong_metric_binding = replace(
        fixture.actual_binding,
        binding_sha="8" * 64,
    )
    hostile_metrics = (
        _FakeVerifiedMetricSignedSupportAttestationV1(
            fixture.parent,
            fixture.materialization,
            wrong_metric_materialization,
            fixture.actual_factory,
            fixture.actual_binding,
        ),
        _FakeVerifiedMetricSignedSupportAttestationV1(
            fixture.parent,
            fixture.materialization,
            wrong_metric_factory,
            fixture.actual_factory,
            fixture.actual_binding,
        ),
        _FakeVerifiedMetricSignedSupportAttestationV1(
            fixture.parent,
            fixture.materialization,
            fixture.actual_metric_body,
            fixture.actual_factory,
            wrong_metric_binding,
        ),
    )
    for metric in hostile_metrics:
        with pytest.raises(fixture.facade.RuntimeGridAuthorityV3Failure) as caught:
            fixture.graph.derive_dynamics(
                fixture.parent,
                fixture.actual_transition,
                metric,
            )
        assert caught.value.reason_id == "BRANCH_JOIN_FAILED"


def test_b5_pair_binds_exact_live_parent_and_materialization_identities(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )

    equal_raw_materialization = _FakeVerifiedMaterializationV3(
        fixture.parent,
        copy.deepcopy(fixture.materialization_body),
        fixture.actual_factory,
        fixture.matched_factory,
    )
    assert equal_raw_materialization is not fixture.materialization
    assert equal_raw_materialization.materialization == (
        fixture.materialization.materialization
    )
    other_transition = _FakeVerifiedTransitionAuthorityV3(
        fixture.parent,
        equal_raw_materialization,
        fixture.actual_transition_body,
        fixture.actual_factory,
    )
    other_metric = _FakeVerifiedMetricSignedSupportAttestationV1(
        fixture.parent,
        equal_raw_materialization,
        fixture.actual_metric_body,
        fixture.actual_factory,
        fixture.actual_binding,
    )
    other_dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        other_transition,
        other_metric,
    )
    with pytest.raises(
        fixture.facade.RuntimeGridAuthorityV3Failure
    ) as materialization_identity:
        fixture.graph.verify_pair(bridge, other_dynamics)
    assert materialization_identity.value.reason_id == "BRANCH_JOIN_FAILED"

    equal_root_parent = _FakeParentV3(fixture.parent.manifest.parent_freeze_v3_sha)
    equal_root_materialization = _FakeVerifiedMaterializationV3(
        equal_root_parent,
        copy.deepcopy(fixture.materialization_body),
        fixture.actual_factory,
        fixture.matched_factory,
    )
    equal_root_transition = _FakeVerifiedTransitionAuthorityV3(
        equal_root_parent,
        equal_root_materialization,
        fixture.actual_transition_body,
        fixture.actual_factory,
    )
    equal_root_metric = _FakeVerifiedMetricSignedSupportAttestationV1(
        equal_root_parent,
        equal_root_materialization,
        fixture.actual_metric_body,
        fixture.actual_factory,
        fixture.actual_binding,
    )
    equal_root_dynamics = fixture.graph.derive_dynamics(
        equal_root_parent,
        equal_root_transition,
        equal_root_metric,
    )
    with pytest.raises(fixture.facade.RuntimeGridAuthorityV3Failure) as parent_identity:
        fixture.graph.verify_pair(bridge, equal_root_dynamics)
    assert parent_identity.value.reason_id == "CROSS_PARENT_ROOT"


def test_b5_rejects_caller_grid_points_denominators_raw_and_legacy_opaques(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    from rulespace_v3.dynamics import VerifiedTransition
    from rulespace_v3.metric import StabilityMetricWitness
    from rulespace_v3.prestructure import VerifiedPrestructureAuthority

    fixture = _fixture(monkeypatch, c19_response_contract)
    facade = fixture.facade
    forbidden_kwargs = (
        "points",
        "reciprocal_indices",
        "grid",
        "grid_body",
        "grid_sha",
        "denominator",
        "denominators",
        "torus_denominators",
        "support",
        "support_offsets",
        "support_sha",
        "factory",
        "factory_sha",
        "protocol",
        "protocol_sha",
    )
    for keyword in forbidden_kwargs:
        with pytest.raises(TypeError):
            facade.derive_bridge_grid_authority_v3(
                fixture.parent,
                fixture.materialization,
                "actual",
                **{keyword: object()},
            )
        with pytest.raises(TypeError):
            facade.derive_dynamics_grid_authority_v3(
                fixture.parent,
                fixture.actual_transition,
                fixture.actual_metric,
                **{keyword: object()},
            )

    with pytest.raises(facade.RuntimeGridAuthorityV3Failure) as role:
        fixture.graph.derive_bridge(
            fixture.parent,
            fixture.materialization,
            "control",
        )
    assert role.value.reason_id == "BRANCH_JOIN_FAILED"
    for raw_or_old in (
        fixture.materialization_body,
        {},
        object.__new__(VerifiedPrestructureAuthority),
        object.__new__(VerifiedTransition),
        object.__new__(StabilityMetricWitness),
    ):
        with pytest.raises((TypeError, ValueError)):
            fixture.graph.derive_bridge(
                fixture.parent,
                raw_or_old,
                "actual",
            )
    for raw_or_old in (
        fixture.actual_transition_body,
        {},
        object.__new__(VerifiedPrestructureAuthority),
        object.__new__(VerifiedTransition),
    ):
        with pytest.raises((TypeError, ValueError)):
            fixture.graph.derive_dynamics(
                fixture.parent,
                raw_or_old,
                fixture.actual_metric,
            )
    for raw_or_old in (
        fixture.actual_metric_body,
        {},
        object.__new__(StabilityMetricWitness),
    ):
        with pytest.raises((TypeError, ValueError)):
            fixture.graph.derive_dynamics(
                fixture.parent,
                fixture.actual_transition,
                raw_or_old,
            )


def test_b5_raw_grid_types_and_authority_opaques_are_never_interchangeable(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )
    bridge_body = bridge.bridge_grid_authority
    dynamics_body = dynamics.dynamics_grid_authority

    for wrong_grid in (fixture.response_grid, dynamics_body.dynamics_grid):
        with pytest.raises((TypeError, ValueError)):
            replace(bridge_body, bridge_grid=wrong_grid)
    for wrong_grid in (fixture.response_grid, bridge_body.bridge_grid):
        with pytest.raises((TypeError, ValueError)):
            replace(dynamics_body, dynamics_grid=wrong_grid)
    for wrong_pair in (
        (dynamics, bridge),
        (bridge_body, dynamics),
        (bridge, dynamics_body),
        (fixture.response_grid, dynamics),
    ):
        with pytest.raises((TypeError, ValueError)):
            fixture.graph.verify_pair(*wrong_pair)


def _private_body(value: object, candidates: tuple[str, ...]) -> object | None:
    for name in candidates:
        try:
            return object.__getattribute__(value, name)
        except AttributeError:
            continue
    return None


def test_b5_opaque_registries_properties_and_resolvers_reject_forgery_and_tamper(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    facade = fixture.facade
    bridge_type = facade.VerifiedBridgeGridAuthorityV3
    dynamics_type = facade.VerifiedDynamicsGridAuthorityV3
    assert "__weakref__" in tuple(bridge_type.__slots__)
    assert "__weakref__" in tuple(dynamics_type.__slots__)
    assert not any("resolver" in slot for slot in bridge_type.__slots__)
    assert not any("resolver" in slot for slot in dynamics_type.__slots__)
    assert isinstance(bridge_type.bridge_grid_authority, property)
    assert isinstance(dynamics_type.dynamics_grid_authority, property)
    bridge_property_closure = tuple(
        cell.cell_contents
        for cell in (bridge_type.bridge_grid_authority.fget.__closure__ or ())
    )
    dynamics_property_closure = tuple(
        cell.cell_contents
        for cell in (dynamics_type.dynamics_grid_authority.fget.__closure__ or ())
    )
    bridge_property_resolvers = tuple(
        value for value in bridge_property_closure if callable(value)
    )
    dynamics_property_resolvers = tuple(
        value for value in dynamics_property_closure if callable(value)
    )
    assert len(bridge_property_resolvers) == 1
    assert len(dynamics_property_resolvers) == 1
    bridge_property_resolver = bridge_property_resolvers[0]
    dynamics_property_resolver = dynamics_property_resolvers[0]
    bridge_resolver_names = tuple(
        name
        for name, value in vars(facade).items()
        if value is bridge_property_resolver
    )
    dynamics_resolver_names = tuple(
        name
        for name, value in vars(facade).items()
        if value is dynamics_property_resolver
    )
    assert bridge_resolver_names
    assert dynamics_resolver_names

    bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )
    assert not hasattr(bridge, "__dict__")
    assert not hasattr(dynamics, "__dict__")
    expected_bridge = copy.deepcopy(bridge.bridge_grid_authority)
    expected_dynamics = copy.deepcopy(dynamics.dynamics_grid_authority)

    for wrapper_type, counterpart in (
        (bridge_type, dynamics),
        (dynamics_type, bridge),
    ):
        forged = object.__new__(wrapper_type)
        with pytest.raises((TypeError, ValueError, RuntimeError)):
            fixture.graph.verify_pair(
                forged if wrapper_type is bridge_type else counterpart,
                forged if wrapper_type is dynamics_type else counterpart,
            )
        with pytest.raises((TypeError, ValueError, RuntimeError)):
            if wrapper_type is bridge_type:
                fixture.graph.reverify_bridge(forged)
            else:
                fixture.graph.reverify_dynamics(forged)

    other_graph = facade._make_runtime_grids_v3_graph(facade._ISSUANCE_TOKEN)
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        other_graph.verify_pair(bridge, dynamics)
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        other_graph.reverify_bridge(bridge)
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        other_graph.reverify_dynamics(dynamics)

    temporary_bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dead_bridge = weakref.proxy(temporary_bridge)
    del temporary_bridge
    gc.collect()
    with pytest.raises((ReferenceError, TypeError, ValueError, RuntimeError)):
        fixture.graph.reverify_bridge(dead_bridge)
    temporary_dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )
    dead_dynamics = weakref.proxy(temporary_dynamics)
    del temporary_dynamics
    gc.collect()
    with pytest.raises((ReferenceError, TypeError, ValueError, RuntimeError)):
        fixture.graph.reverify_dynamics(dead_dynamics)

    detached_bridge = bridge.bridge_grid_authority
    object.__setattr__(detached_bridge, "grid_authority_sha", "9" * 64)
    detached_dynamics = dynamics.dynamics_grid_authority
    object.__setattr__(detached_dynamics, "grid_authority_sha", "8" * 64)
    assert bridge.bridge_grid_authority == expected_bridge
    assert dynamics.dynamics_grid_authority == expected_dynamics

    private_bridge = _private_body(
        bridge,
        (
            "_VerifiedBridgeGridAuthorityV3__grid_authority",
            "_VerifiedBridgeGridAuthorityV3__bridge_grid_authority",
        ),
    )
    if private_bridge is not None:
        object.__setattr__(private_bridge, "grid_authority_sha", "7" * 64)
        with pytest.raises((TypeError, ValueError, RuntimeError)):
            fixture.graph.verify_pair(bridge, dynamics)
        with pytest.raises((TypeError, ValueError, RuntimeError)):
            fixture.graph.reverify_bridge(bridge)

    private_dynamics = _private_body(
        dynamics,
        (
            "_VerifiedDynamicsGridAuthorityV3__grid_authority",
            "_VerifiedDynamicsGridAuthorityV3__dynamics_grid_authority",
        ),
    )
    if private_dynamics is not None:
        object.__setattr__(private_dynamics, "grid_authority_sha", "6" * 64)
        with pytest.raises((TypeError, ValueError, RuntimeError)):
            fixture.graph.reverify_dynamics(dynamics)

    bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )
    for wrapper, name in (
        (bridge, "_VerifiedBridgeGridAuthorityV3__resolver"),
        (dynamics, "_VerifiedDynamicsGridAuthorityV3__resolver"),
    ):
        try:
            object.__setattr__(wrapper, name, lambda _value: "FORGED")
        except AttributeError:
            pass
        else:
            with pytest.raises((TypeError, ValueError, RuntimeError)):
                fixture.graph.verify_pair(bridge, dynamics)

    def redirected(*_args, **_kwargs):
        raise AssertionError("redirected resolver was consulted")

    for name in (*bridge_resolver_names, *dynamics_resolver_names):
        monkeypatch.setattr(facade, name, redirected)
    assert bridge.bridge_grid_authority.grid_authority_sha != "FORGED"
    assert dynamics.dynamics_grid_authority.grid_authority_sha != "FORGED"
    bridge_view = fixture.graph.reverify_bridge(bridge)
    dynamics_view = fixture.graph.reverify_dynamics(dynamics)
    assert bridge_view.grid_authority == bridge.bridge_grid_authority
    assert dynamics_view.grid_authority == dynamics.dynamics_grid_authority
    verified = fixture.graph.verify_pair(bridge, dynamics)
    assert verified == (bridge, dynamics)


@pytest.mark.parametrize(
    ("authority_kind", "nested_field"),
    (
        ("bridge", None),
        ("bridge", "materialization"),
        ("bridge", "factory_binding"),
        ("bridge", "derivation_protocol"),
        ("bridge", "bridge_grid"),
        ("dynamics", None),
        ("dynamics", "transition_authority"),
        ("dynamics", "metric_support_attestation"),
        ("dynamics", "derivation_protocol"),
        ("dynamics", "dynamics_grid"),
    ),
)
def test_b5_opaque_private_bodies_reject_unknown_recursive_fields(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    authority_kind: str,
    nested_field: str | None,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    if authority_kind == "bridge":
        capability = fixture.graph.derive_bridge(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
        private_field = "_VerifiedBridgeGridAuthorityV3__grid_authority"
        reverify = fixture.graph.reverify_bridge
    else:
        capability = fixture.graph.derive_dynamics(
            fixture.parent,
            fixture.actual_transition,
            fixture.actual_metric,
        )
        private_field = "_VerifiedDynamicsGridAuthorityV3__grid_authority"
        reverify = fixture.graph.reverify_dynamics
    private_body = object.__getattribute__(capability, private_field)
    target = (
        private_body if nested_field is None else getattr(private_body, nested_field)
    )
    object.__setattr__(target, "unknown_recursive_field", "forged")

    with pytest.raises((TypeError, ValueError)):
        reverify(capability)


@pytest.mark.parametrize(
    ("authority_kind", "nested_field"),
    (
        ("bridge", None),
        ("bridge", "bridge_grid"),
        ("dynamics", None),
        ("dynamics", "dynamics_grid"),
    ),
)
def test_b5_opaque_private_bodies_reject_recursive_equality_spoof_subclasses(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    authority_kind: str,
    nested_field: str | None,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    if authority_kind == "bridge":
        capability = fixture.graph.derive_bridge(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
        private_field = "_VerifiedBridgeGridAuthorityV3__grid_authority"
        reverify = fixture.graph.reverify_bridge
    else:
        capability = fixture.graph.derive_dynamics(
            fixture.parent,
            fixture.actual_transition,
            fixture.actual_metric,
        )
        private_field = "_VerifiedDynamicsGridAuthorityV3__grid_authority"
        reverify = fixture.graph.reverify_dynamics
    private_body = object.__getattribute__(capability, private_field)
    target = (
        private_body if nested_field is None else getattr(private_body, nested_field)
    )

    class EqualitySpoof(type(target)):
        def __eq__(self, other):
            del other
            return True

        def __ne__(self, other):
            del other
            return False

    hostile = EqualitySpoof(
        **{
            item.name: copy.deepcopy(getattr(target, item.name))
            for item in fields(target)
        }
    )
    if nested_field is None:
        object.__setattr__(capability, private_field, hostile)
    else:
        object.__setattr__(private_body, nested_field, hostile)

    with pytest.raises((TypeError, ValueError)):
        reverify(capability)


@pytest.mark.parametrize(
    ("authority_kind", "mutation"),
    (
        ("bridge", "unknown-field"),
        ("bridge", "equality-subclass"),
        ("bridge", "value-drift"),
        ("dynamics", "unknown-field"),
        ("dynamics", "equality-subclass"),
        ("dynamics", "value-drift"),
    ),
)
def test_b5_public_payloads_reject_protocol_wire_aliases_and_unknown_fields(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    authority_kind: str,
    mutation: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    if authority_kind == "bridge":
        body = fixture.graph.derive_bridge(
            fixture.parent,
            fixture.materialization,
            "actual",
        ).bridge_grid_authority
        payload_builder = fixture.bridge_payload
    else:
        body = fixture.graph.derive_dynamics(
            fixture.parent,
            fixture.actual_transition,
            fixture.actual_metric,
        ).dynamics_grid_authority
        payload_builder = fixture.dynamics_payload
    protocol = body.derivation_protocol

    if mutation == "unknown-field":
        object.__setattr__(protocol, "unknown_protocol_field", "forged")
    elif mutation == "equality-subclass":

        class EqualitySpoof(type(protocol)):
            def __eq__(self, other):
                del other
                return True

            def __ne__(self, other):
                del other
                return False

        hostile = EqualitySpoof(
            **{
                item.name: copy.deepcopy(getattr(protocol, item.name))
                for item in fields(protocol)
            }
        )
        object.__setattr__(body, "derivation_protocol", hostile)
    else:
        object.__setattr__(protocol, "protocol_sha", "0" * 64)

    with pytest.raises((TypeError, ValueError)):
        payload_builder(body)


@pytest.mark.parametrize(
    ("authority_kind", "mutation"),
    (
        ("bridge", "unknown-field"),
        ("bridge", "equality-subclass"),
        ("bridge", "container-subclass"),
        ("dynamics", "unknown-field"),
        ("dynamics", "equality-subclass"),
        ("dynamics", "container-subclass"),
    ),
)
def test_b5_public_payloads_reject_grid_wire_aliases_and_unknown_fields(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    authority_kind: str,
    mutation: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    if authority_kind == "bridge":
        body = fixture.graph.derive_bridge(
            fixture.parent,
            fixture.materialization,
            "actual",
        ).bridge_grid_authority
        payload_builder = fixture.bridge_payload
        field = "bridge_grid"
    else:
        body = fixture.graph.derive_dynamics(
            fixture.parent,
            fixture.actual_transition,
            fixture.actual_metric,
        ).dynamics_grid_authority
        payload_builder = fixture.dynamics_payload
        field = "dynamics_grid"
    grid = getattr(body, field)

    if mutation == "unknown-field":
        object.__setattr__(grid, "unknown_grid_field", "forged")
    elif mutation == "equality-subclass":

        class EqualitySpoof(type(grid)):
            def __eq__(self, other):
                del other
                return True

            def __ne__(self, other):
                del other
                return False

        hostile = EqualitySpoof(
            **{
                item.name: copy.deepcopy(getattr(grid, item.name))
                for item in fields(grid)
            }
        )
        object.__setattr__(body, field, hostile)
    else:

        class TupleAlias(tuple):
            pass

        container_field = (
            "spatial_shape" if authority_kind == "bridge" else "torus_denominators"
        )
        object.__setattr__(
            grid,
            container_field,
            TupleAlias(getattr(grid, container_field)),
        )

    with pytest.raises((TypeError, ValueError)):
        payload_builder(body)


@pytest.mark.parametrize(
    "mutation",
    ("unknown-field", "equality-subclass", "container-subclass"),
)
def test_b5_bridge_payload_rejects_binding_aliases_against_materialization_root(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    mutation: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    body = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).bridge_grid_authority
    binding = body.factory_binding

    if mutation == "unknown-field":
        object.__setattr__(binding, "unknown_binding_field", "forged")
    elif mutation == "equality-subclass":

        class EqualitySpoof(type(binding)):
            def __eq__(self, other):
                del other
                return True

            def __ne__(self, other):
                del other
                return False

        object.__setattr__(
            body,
            "factory_binding",
            EqualitySpoof(
                **{
                    item.name: copy.deepcopy(getattr(binding, item.name))
                    for item in fields(binding)
                }
            ),
        )
    else:

        class TupleAlias(tuple):
            pass

        object.__setattr__(
            binding,
            "support_offsets",
            TupleAlias(binding.support_offsets),
        )

    with pytest.raises((TypeError, ValueError)):
        fixture.bridge_payload(body)


def test_b5_recursive_guard_distinguishes_ieee_signed_zero_bits() -> None:
    guard = _module()._require_exact_recursive_wire
    with pytest.raises(ValueError, match="leaf"):
        guard(+0.0, -0.0)
    with pytest.raises(ValueError, match="leaf"):
        guard(complex(+0.0, -0.0), complex(-0.0, -0.0))


def test_b5_recursive_guard_rejects_cycles_before_serialization() -> None:
    guard = _module()._require_exact_recursive_wire
    cyclic = SimpleNamespace()
    cyclic.loop = cyclic
    with pytest.raises(ValueError, match="cycle"):
        guard(cyclic, cyclic)


def test_b5_recursive_guard_rejects_mapping_key_scalar_subclasses() -> None:
    guard = _module()._require_exact_recursive_wire

    class StrAlias(str):
        pass

    hostile = {StrAlias("field"): 1}
    with pytest.raises(TypeError, match="unsupported"):
        guard(hostile, hostile)


def test_b5_recursive_guard_rejects_dataclass_subclasses_in_self_shape() -> None:
    guard = _module()._require_exact_recursive_wire

    class EqualitySpoof(_FakeMeasuredTransition):
        def __eq__(self, other):
            del other
            return True

    hostile = EqualitySpoof(
        "a" * 64,
        "b" * 64,
        "actual",
        C19_STATE_SCHEMA_ID,
        C19_CHANNEL_ORDER,
        C19_SPATIAL_SHAPE,
        ((0,),),
        "c" * 64,
        "d" * 64,
    )
    with pytest.raises(TypeError, match="dataclass subclass"):
        guard(hostile, hostile)


@pytest.mark.parametrize("authority_kind", ("bridge", "dynamics"))
def test_b5_public_payload_rejects_outer_scalar_wire_subclasses(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    authority_kind: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    if authority_kind == "bridge":
        body = fixture.graph.derive_bridge(
            fixture.parent,
            fixture.materialization,
            "actual",
        ).bridge_grid_authority
        payload_builder = fixture.bridge_payload
    else:
        body = fixture.graph.derive_dynamics(
            fixture.parent,
            fixture.actual_transition,
            fixture.actual_metric,
        ).dynamics_grid_authority
        payload_builder = fixture.dynamics_payload

    class StrAlias(str):
        pass

    object.__setattr__(
        body,
        "grid_authority_schema_version",
        StrAlias(body.grid_authority_schema_version),
    )
    with pytest.raises((TypeError, ValueError)):
        payload_builder(body)


@pytest.mark.parametrize(
    "splice_kind",
    ("cross-branch", "foreign-parent", "foreign-materialization"),
)
def test_b5_dynamics_payload_rejects_transition_metric_lineage_splices(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    splice_kind: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    body = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    ).dynamics_grid_authority
    if splice_kind == "cross-branch":
        hostile_metric = fixture.matched_metric_body
    elif splice_kind == "foreign-parent":
        hostile_metric = replace(
            fixture.actual_metric_body,
            parent_freeze_v3_sha="b" * 64,
            attestation_sha="1" * 64,
        )
    else:
        hostile_metric = replace(
            fixture.actual_metric_body,
            application_scenario_materialization_v3_sha="0" * 64,
            attestation_sha="1" * 64,
        )
    hostile = replace(
        body,
        metric_support_attestation=hostile_metric,
        grid_authority_sha="0" * 64,
    )

    with pytest.raises((TypeError, ValueError)):
        fixture.dynamics_payload(hostile)


def test_b5_fake_graph_captures_owner_seams_and_exact_call_counts(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)

    def redirected(*_args, **_kwargs):
        raise AssertionError("redirected dependency was consulted")

    for name in (
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        "_reverify_verified_transition_authority_v3",
        "_reverify_verified_metric_signed_support_attestation_v1",
        "build_bridge_grid_manifest",
        "build_dynamics_grid_manifest",
    ):
        monkeypatch.setattr(fixture.facade, name, redirected)
    bridge = fixture.graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dynamics = fixture.graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )
    assert bridge.bridge_grid_authority.factory_binding == fixture.actual_binding
    assert dynamics.dynamics_grid_authority.transition_authority == (
        fixture.actual_transition_body
    )
    assert len(fixture.calls.materialization) == 1
    assert len(fixture.calls.transition) == 1
    assert len(fixture.calls.metric) == 1
    assert len(fixture.calls.bridge_build) == 1
    assert len(fixture.calls.dynamics_build) == 1


def test_b5_existing_graph_captures_own_payload_record_view_failure_schema_and_registry_globals(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    facade = fixture.facade
    graph = fixture.graph
    graph_functions = (
        graph.derive_bridge,
        graph.derive_dynamics,
        graph.reverify_bridge,
        graph.reverify_dynamics,
        graph.verify_pair,
    )
    reachable = tuple(
        value
        for function in graph_functions
        for value in _closure_reachable_objects(function)
    )

    bridge_payload = facade._bridge_grid_authority_v3_payload_impl
    dynamics_payload = facade._dynamics_grid_authority_v3_payload_impl
    bridge_view_type = facade._VerifiedBridgeGridAuthorityV3View
    dynamics_view_type = facade._VerifiedDynamicsGridAuthorityV3View
    failure_type = facade.RuntimeGridAuthorityV3Failure
    expected_schemas = (
        "v3m0.bridge-grid-authority.v3",
        "v3m0.dynamics-grid-authority.v3",
    )
    record_bindings = tuple(
        (name, value)
        for name, value in vars(facade).items()
        if name.startswith("_")
        and "Record" in name
        and inspect.isclass(value)
        and any(captured is value for captured in reachable)
    )
    schema_bindings = tuple(
        name
        for name, value in vars(facade).items()
        if type(value) is str and value in expected_schemas
    )

    assert any(value is bridge_payload for value in reachable)
    assert any(value is dynamics_payload for value in reachable)
    assert len({id(value) for _, value in record_bindings}) == 2
    assert any(value is bridge_view_type for value in reachable)
    assert any(value is dynamics_view_type for value in reachable)
    assert any(value is failure_type for value in reachable)
    assert all(
        any(type(value) is str and value == schema for value in reachable)
        for schema in expected_schemas
    )
    assert all(
        any(vars(facade)[name] == schema for name in schema_bindings)
        for schema in expected_schemas
    )
    assert any(value is weakref.ref for value in reachable)
    assert any(value is id for value in reachable)

    def redirected(*_args, **_kwargs):
        raise AssertionError("redirected runtime-grid owner global was consulted")

    monkeypatch.setattr(facade, "bridge_grid_authority_v3_payload", redirected)
    monkeypatch.setattr(facade, "dynamics_grid_authority_v3_payload", redirected)
    for name in (
        "_wire_tree",
        "_protocol_record",
        "_protocol_record_impl",
        "_bridge_grid_authority_v3_payload_impl",
        "_dynamics_grid_authority_v3_payload_impl",
        "_exact_record",
        "dataclass_fields",
        "is_dataclass",
        "Enum",
        "SimpleNamespace",
        "application_scenario_materialization_v3_payload",
        "factory_branch_binding_v3_payload",
        "transition_authority_v3_payload",
        "metric_signed_support_attestation_v1_payload",
        "bridge_grid_payload",
        "dynamics_grid_payload",
    ):
        monkeypatch.setattr(facade, name, redirected)
    for name, _record_type in record_bindings:
        monkeypatch.setattr(facade, name, redirected)
    monkeypatch.setattr(
        facade,
        "_VerifiedBridgeGridAuthorityV3View",
        redirected,
    )
    monkeypatch.setattr(
        facade,
        "_VerifiedDynamicsGridAuthorityV3View",
        redirected,
    )
    monkeypatch.setattr(facade, "RuntimeGridAuthorityV3Failure", redirected)
    for name in schema_bindings:
        monkeypatch.setattr(facade, name, f"redirected-{name}")
    monkeypatch.setattr(facade, "weakref", SimpleNamespace(ref=redirected))
    monkeypatch.setattr(facade, "id", redirected, raising=False)

    bridge = graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dynamics = graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )
    assert (
        bridge.bridge_grid_authority.grid_authority_schema_version
        == (expected_schemas[0])
    )
    assert (
        dynamics.dynamics_grid_authority.grid_authority_schema_version
        == (expected_schemas[1])
    )
    bridge_view = graph.reverify_bridge(bridge)
    dynamics_view = graph.reverify_dynamics(dynamics)
    assert type(bridge_view) is bridge_view_type
    assert type(dynamics_view) is dynamics_view_type
    assert graph.verify_pair(bridge, dynamics) == (bridge, dynamics)

    with pytest.raises(failure_type) as caught:
        graph.derive_bridge(
            fixture.parent,
            fixture.materialization,
            "redirected-role",
        )
    assert caught.value.reason_id == "BRANCH_JOIN_FAILED"


@pytest.mark.parametrize(
    "builtin_name",
    (
        "type",
        "str",
        "bool",
        "int",
        "float",
        "complex",
        "isinstance",
        "vars",
        "getattr",
        "frozenset",
        "tuple",
        "list",
        "dict",
        "set",
        "len",
        "zip",
        "object",
        "AttributeError",
        "RuntimeError",
        "TypeError",
        "ValueError",
    ),
)
def test_b5_frozen_graph_payloads_properties_and_failures_ignore_builtin_redirects(
    monkeypatch: pytest.MonkeyPatch,
    c19_response_contract,
    builtin_name: str,
) -> None:
    fixture = _fixture(monkeypatch, c19_response_contract)
    facade = fixture.facade
    graph = fixture.graph
    bridge = graph.derive_bridge(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    dynamics = graph.derive_dynamics(
        fixture.parent,
        fixture.actual_transition,
        fixture.actual_metric,
    )
    bridge_body = bridge.bridge_grid_authority
    dynamics_body = dynamics.dynamics_grid_authority
    bridge_payload = fixture.bridge_payload(bridge_body)
    dynamics_payload = fixture.dynamics_payload(dynamics_body)
    recursive_wire_guard = facade._require_exact_recursive_wire
    nested_wire_builder = facade._wire_tree
    text_validator = facade._text
    failure_type = facade.RuntimeGridAuthorityV3Failure
    type_error = TypeError
    invalid_materialization = object()
    redirect_calls: list[str] = []

    def redirected(*_args, **_kwargs):
        redirect_calls.append(builtin_name)
        raise AssertionError(f"redirected builtin {builtin_name} was consulted")

    monkeypatch.setattr(facade, builtin_name, redirected, raising=False)

    assert bridge.bridge_grid_authority == bridge_body
    assert dynamics.dynamics_grid_authority == dynamics_body
    assert fixture.bridge_payload(bridge_body) == bridge_payload
    assert fixture.dynamics_payload(dynamics_body) == dynamics_payload
    assert graph.reverify_bridge(bridge).grid_authority == bridge_body
    assert graph.reverify_dynamics(dynamics).grid_authority == dynamics_body
    assert graph.verify_pair(bridge, dynamics) == (bridge, dynamics)
    recursive_wire_guard({"items": [1]}, {"items": [1]})
    assert nested_wire_builder({"items": [1]}) == {"items": [1]}
    assert text_validator("frozen", "probe") == "frozen"

    with pytest.raises(failure_type) as caught:
        graph.derive_bridge(
            fixture.parent,
            invalid_materialization,
            "actual",
        )
    assert caught.value.reason_id == "FACTORY_SUPPORT_INVALID"
    with pytest.raises(type_error, match="non-empty"):
        text_validator("", "probe")
    assert redirect_calls == []


def test_b5_production_public_closures_capture_exact_owner_seams_and_ignore_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _module()
    import rulespace_v3.application_materialization_v3 as b2
    import rulespace_v3.metric_support_authority_v1 as b4
    import rulespace_v3.transition_authority_v3 as b3

    b2_seam = b2._require_v3m0_application_scenario_materialization_v3_for_parent
    b3_seam = b3._reverify_verified_transition_authority_v3
    b4_seam = b4._reverify_verified_metric_signed_support_attestation_v1
    assert facade._require_v3m0_application_scenario_materialization_v3_for_parent is (
        b2_seam
    )
    assert facade._reverify_verified_transition_authority_v3 is b3_seam
    assert facade._reverify_verified_metric_signed_support_attestation_v1 is b4_seam

    bridge_api = facade.derive_bridge_grid_authority_v3
    dynamics_api = facade.derive_dynamics_grid_authority_v3
    pair_api = facade.verify_runtime_grid_authorities_v3
    bridge_payload_api = facade.bridge_grid_authority_v3_payload
    dynamics_payload_api = facade.dynamics_grid_authority_v3_payload
    bridge_reverify_api = facade._reverify_verified_bridge_grid_authority_v3
    dynamics_reverify_api = facade._reverify_verified_dynamics_grid_authority_v3
    production_graph = facade._PRODUCTION_GRAPH
    assert production_graph.derive_bridge in tuple(
        cell.cell_contents for cell in (bridge_api.__closure__ or ())
    )
    assert production_graph.derive_dynamics in tuple(
        cell.cell_contents for cell in (dynamics_api.__closure__ or ())
    )
    assert production_graph.verify_pair in tuple(
        cell.cell_contents for cell in (pair_api.__closure__ or ())
    )
    assert production_graph.reverify_bridge in tuple(
        cell.cell_contents for cell in (bridge_reverify_api.__closure__ or ())
    )
    assert production_graph.reverify_dynamics in tuple(
        cell.cell_contents for cell in (dynamics_reverify_api.__closure__ or ())
    )
    assert b2_seam in _closure_reachable_objects(bridge_api)
    assert b3_seam in _closure_reachable_objects(dynamics_api)
    assert b4_seam in _closure_reachable_objects(dynamics_api)
    assert facade._bridge_grid_authority_v3_payload_impl in (
        _closure_reachable_objects(bridge_payload_api)
    )
    assert facade._dynamics_grid_authority_v3_payload_impl in (
        _closure_reachable_objects(dynamics_payload_api)
    )
    before = tuple(
        tuple(id(cell.cell_contents) for cell in (function.__closure__ or ()))
        for function in (
            bridge_api,
            dynamics_api,
            pair_api,
            bridge_reverify_api,
            dynamics_reverify_api,
        )
    )

    def redirected(*_args, **_kwargs):
        raise AssertionError("redirected global was consulted")

    monkeypatch.setattr(
        facade,
        "_PRODUCTION_GRAPH",
        SimpleNamespace(
            derive_bridge=redirected,
            derive_dynamics=redirected,
            verify_pair=redirected,
            reverify_bridge=redirected,
            reverify_dynamics=redirected,
        ),
    )
    for name in (
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        "_reverify_verified_transition_authority_v3",
        "_reverify_verified_metric_signed_support_attestation_v1",
        "build_bridge_grid_manifest",
        "build_dynamics_grid_manifest",
        "_reverify_verified_bridge_grid_authority_v3",
        "_reverify_verified_dynamics_grid_authority_v3",
        "_bridge_grid_authority_v3_payload_impl",
        "_dynamics_grid_authority_v3_payload_impl",
        "application_scenario_materialization_v3_payload",
        "factory_branch_binding_v3_payload",
        "transition_authority_v3_payload",
        "metric_signed_support_attestation_v1_payload",
        "bridge_grid_payload",
        "dynamics_grid_payload",
        "_protocol_record",
        "_exact_record",
    ):
        monkeypatch.setattr(facade, name, redirected)
    for wrapper_type, property_name in (
        (facade.VerifiedBridgeGridAuthorityV3, "bridge_grid_authority"),
        (facade.VerifiedDynamicsGridAuthorityV3, "dynamics_grid_authority"),
    ):
        descriptor = getattr(wrapper_type, property_name)
        resolver = next(
            value
            for value in (
                cell.cell_contents for cell in (descriptor.fget.__closure__ or ())
            )
            if callable(value)
        )
        for name, value in tuple(vars(facade).items()):
            if value is resolver:
                monkeypatch.setattr(facade, name, redirected)
    after = tuple(
        tuple(id(cell.cell_contents) for cell in (function.__closure__ or ()))
        for function in (
            bridge_api,
            dynamics_api,
            pair_api,
            bridge_reverify_api,
            dynamics_reverify_api,
        )
    )
    assert after == before
    assert all(
        "_PRODUCTION_GRAPH" not in function.__code__.co_names
        for function in (
            bridge_api,
            dynamics_api,
            pair_api,
            bridge_reverify_api,
            dynamics_reverify_api,
        )
    )
    with pytest.raises(facade.RuntimeGridAuthorityV3Failure):
        bridge_api(object(), object(), "actual")
    with pytest.raises(facade.RuntimeGridAuthorityV3Failure):
        dynamics_api(object(), object(), object())
    with pytest.raises((TypeError, ValueError)):
        pair_api(object(), object())
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        bridge_reverify_api(object())
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        dynamics_reverify_api(object())
    with pytest.raises(TypeError):
        bridge_payload_api(object())
    with pytest.raises(TypeError):
        dynamics_payload_api(object())


def _direct_rulespace_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    package = "rulespace_v3"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name
                for alias in node.names
                if alias.name.startswith("rulespace_v3.")
            )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                prefix = package.split(".")
                base = ".".join(prefix[: len(prefix) - node.level + 1])
                resolved = ".".join(
                    value for value in (base, node.module or "") if value
                )
                if resolved.startswith("rulespace_v3."):
                    imported.add(resolved)
            elif node.module and node.module.startswith("rulespace_v3."):
                imported.add(node.module)
    return imported


def test_b5_static_import_dag_is_the_exact_four_edges_and_owner_seams() -> None:
    module_path = REPO_ROOT / "rulespace_v3" / "runtime_grids_v3.py"
    assert module_path.is_file()
    assert _direct_rulespace_imports(module_path) == {
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.transition_authority_v3",
        "rulespace_v3.metric_support_authority_v1",
        "rulespace_v3.grids",
    }
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports_by_module: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if node.level == 1:
            module = f"rulespace_v3.{module}"
        imports_by_module.setdefault(module, set()).update(
            alias.name for alias in node.names
        )
    assert (
        "_require_v3m0_application_scenario_materialization_v3_for_parent"
        in imports_by_module["rulespace_v3.application_materialization_v3"]
    )
    assert (
        "_reverify_verified_transition_authority_v3"
        in imports_by_module["rulespace_v3.transition_authority_v3"]
    )
    assert (
        "_reverify_verified_metric_signed_support_attestation_v1"
        in imports_by_module["rulespace_v3.metric_support_authority_v1"]
    )
