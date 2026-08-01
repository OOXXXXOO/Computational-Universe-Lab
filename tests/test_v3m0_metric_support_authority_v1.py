"""Strict RED contracts for the Parent-v3 C19 metric-support authority."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, fields, replace
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
C19_SPATIAL_SHAPE = (8,)
FAILURE_REASON_IDS = (
    "MATERIALIZATION_INVALID",
    "FACTORY_DEAD",
    "METRIC_PROTOCOL_DRIFT",
    "METRIC_REPLAY_FAILED",
    "SUPPORT_INVALID",
    "BRANCH_JOIN_FAILED",
    "CROSS_PARENT_ROOT",
)


@dataclass(frozen=True)
class _FakeFactoryBody:
    factory_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    state_shape: tuple[int, ...]
    spatial_ndim: int


class _FakeLiveFactory:
    def __init__(self, factory: _FakeFactoryBody, role: str) -> None:
        self.factory = factory
        self.role = role


@dataclass(frozen=True)
class _FakeFactoryBinding:
    parent_freeze_v3_sha: str
    branch: str
    factory: _FakeFactoryBody
    binding_sha: str


@dataclass(frozen=True)
class _FakeResponseContract:
    metric_support_derivation: object
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
        self._materialization = materialization
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


def _module():
    import rulespace_v3.metric_support_authority_v1 as facade

    return facade


@pytest.fixture(scope="module")
def exact_metric_protocol():
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.factory import freeze_complex_tensor
    from rulespace_v3.metric import metric_support_payload
    from rulespace_v3.parent_v3_contracts import (
        METRIC_SUPPORT_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION,
        MetricSupportDerivationProtocolV1,
        metric_support_derivation_protocol_v1_payload,
    )

    support = ((0,),)
    provisional = MetricSupportDerivationProtocolV1(
        protocol_schema_version=(METRIC_SUPPORT_DERIVATION_PROTOCOL_V1_SCHEMA_VERSION),
        metric_kind="constant-state-v1",
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        spatial_shape=C19_SPATIAL_SHAPE,
        spatial_ndim=1,
        state_metric=freeze_complex_tensor(
            np.eye(len(C19_CHANNEL_ORDER), dtype=np.complex128)
        ),
        normalization_id="trace-at-zero-equals-state-dim-v1",
        support_derivation_id="constant-kernel-origin-only-v1",
        metric_support_offsets=support,
        metric_support_sha=canonical_sha(metric_support_payload(support)),
        caller_supplied_support_allowed=False,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            metric_support_derivation_protocol_v1_payload(provisional)
        ),
    )


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    protocol: object,
    *,
    root: str = "a",
    fresh_factories: bool = False,
):
    from rulespace_v3.application_materialization_v3 import (
        ApplicationMaterializationV3Failure,
    )
    from rulespace_v3.metric import metric_support_payload as real_support_payload

    facade = _module()
    parent_sha = root * 64
    actual_body = _FakeFactoryBody(
        factory_sha="b" * 64,
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        state_shape=(20, 8),
        spatial_ndim=1,
    )
    matched_body = replace(actual_body, factory_sha="c" * 64)
    actual_factory = _FakeLiveFactory(actual_body, "actual")
    matched_factory = _FakeLiveFactory(matched_body, "matched_ablated")
    response = _FakeResponseContract(protocol, "d" * 64)
    scenario = _FakeScenarioAuthority(response, "e" * 64)
    application = _FakeApplicationAuthority(
        C19_STATE_SCHEMA_ID,
        C19_CHANNEL_ORDER,
        C19_SPATIAL_SHAPE,
        "f" * 64,
    )
    actual_binding = _FakeFactoryBinding(
        parent_sha,
        "actual",
        actual_body,
        "1" * 64,
    )
    matched_binding = _FakeFactoryBinding(
        parent_sha,
        "matched_ablated",
        matched_body,
        "2" * 64,
    )
    body = _FakeMaterializationBody(
        current_application_authority=application,
        current_scenario_authority=scenario,
        current_scenario_response_contract=response,
        actual_factory_binding=actual_binding,
        matched_ablated_factory_binding=matched_binding,
        materialization_sha="3" * 64,
    )
    parent = _FakeParentV3(parent_sha)
    materialization = _FakeVerifiedMaterializationV3(
        parent,
        body,
        actual_factory,
        matched_factory,
    )
    calls = SimpleNamespace(
        materialization=[],
        protocol=[],
        support=[],
        resolved_factories=[],
    )
    mode = {"value": None}

    def require_materialization(observed_parent, observed_materialization):
        calls.materialization.append((observed_parent, observed_materialization))
        selected_mode = mode["value"]
        if selected_mode == "materialization":
            raise ApplicationMaterializationV3Failure(
                "PERMIT_INVALID",
                "forced materialization failure",
            )
        if selected_mode == "factory":
            raise ApplicationMaterializationV3Failure(
                "FACTORY_REPLAY_FAILED",
                "forced dead factory",
            )
        if selected_mode == "cross_root":
            raise ApplicationMaterializationV3Failure(
                "CROSS_PARENT_ROOT",
                "forced Parent root mismatch",
            )
        if type(observed_parent) is not _FakeParentV3:
            raise TypeError("exact live Parent-v3 required")
        if type(observed_materialization) is not _FakeVerifiedMaterializationV3:
            raise TypeError("exact live B2 materialization required")
        if observed_materialization.parent is not observed_parent:
            raise ValueError("materialization belongs to another live Parent")
        try:
            materialization_body = observed_materialization.materialization
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            raise ApplicationMaterializationV3Failure(
                "PERMIT_INVALID",
                "materialization property resolver drifted",
            ) from exc
        resolved_actual = (
            _FakeLiveFactory(actual_body, "actual")
            if fresh_factories
            else actual_factory
        )
        resolved_matched = (
            _FakeLiveFactory(matched_body, "matched_ablated")
            if fresh_factories
            else matched_factory
        )
        calls.resolved_factories.append((resolved_actual, resolved_matched))
        return SimpleNamespace(
            materialization=materialization_body,
            actual_factory=resolved_actual,
            matched_ablated_factory=resolved_matched,
        )

    def verify_protocol(observed):
        calls.protocol.append(observed)
        if mode["value"] == "protocol":
            raise ValueError("forced metric protocol drift")
        if type(observed) is not type(protocol) or observed != protocol:
            raise ValueError("metric protocol differs from frozen C19 body")
        return observed

    def support_payload(offsets):
        calls.support.append(offsets)
        if mode["value"] == "metric_replay":
            raise RuntimeError("forced metric replay failure")
        return real_support_payload(offsets)

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
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        require_materialization,
    )
    monkeypatch.setattr(
        facade,
        "verify_metric_support_derivation_protocol_v1",
        verify_protocol,
    )
    monkeypatch.setattr(facade, "metric_support_payload", support_payload)
    graph = facade._make_metric_support_authority_v1_graph(facade._ISSUANCE_TOKEN)
    return SimpleNamespace(
        facade=facade,
        graph=graph,
        parent=parent,
        materialization=materialization,
        body=body,
        actual_factory=actual_factory,
        matched_factory=matched_factory,
        protocol=protocol,
        calls=calls,
        mode=mode,
    )


def _raw_attestation_payload(attestation: object) -> dict[str, object]:
    return {
        "attestation_schema_version": attestation.attestation_schema_version,
        "parent_freeze_v3_sha": attestation.parent_freeze_v3_sha,
        "current_application_authority_v3_sha": (
            attestation.current_application_authority_v3_sha
        ),
        "current_scenario_authority_v3_sha": (
            attestation.current_scenario_authority_v3_sha
        ),
        "response_contract_v3_sha": attestation.response_contract_v3_sha,
        "metric_support_protocol_sha": attestation.metric_support_protocol_sha,
        "application_scenario_materialization_v3_sha": (
            attestation.application_scenario_materialization_v3_sha
        ),
        "factory_sha": attestation.factory_sha,
        "factory_role": attestation.factory_role,
        "state_schema_id": attestation.state_schema_id,
        "channel_order": list(attestation.channel_order),
        "spatial_shape": list(attestation.spatial_shape),
        "metric_kind": attestation.metric_kind,
        "metric_support_offsets": [
            list(offset) for offset in attestation.metric_support_offsets
        ],
        "metric_support_sha": attestation.metric_support_sha,
    }


def _tamper_and_resign(attestation, **changes):
    from rulespace_v3.evidence import canonical_sha

    result = copy.deepcopy(attestation)
    for name, value in changes.items():
        object.__setattr__(result, name, value)
    object.__setattr__(
        result,
        "attestation_sha",
        canonical_sha(_raw_attestation_payload(result)),
    )
    return result


def _closure_reachable_objects(function: object) -> tuple[object, ...]:
    """Return callable closure objects without consulting module globals."""

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


def test_b4_exact_record_api_names_failure_vocabulary_and_public_surface() -> None:
    facade = _module()

    assert [item.name for item in fields(facade.MetricSignedSupportAttestationV1)] == [
        "attestation_schema_version",
        "parent_freeze_v3_sha",
        "current_application_authority_v3_sha",
        "current_scenario_authority_v3_sha",
        "response_contract_v3_sha",
        "metric_support_protocol_sha",
        "application_scenario_materialization_v3_sha",
        "factory_sha",
        "factory_role",
        "state_schema_id",
        "channel_order",
        "spatial_shape",
        "metric_kind",
        "metric_support_offsets",
        "metric_support_sha",
        "attestation_sha",
    ]
    assert tuple(
        inspect.signature(
            facade.issue_c19_metric_signed_support_attestation_v1
        ).parameters
    ) == ("parent", "materialization", "factory_role")
    assert tuple(
        inspect.signature(
            facade.verify_c19_metric_signed_support_attestation_v1
        ).parameters
    ) == ("attestation", "parent", "materialization")
    assert tuple(
        inspect.signature(
            facade.metric_signed_support_attestation_v1_payload
        ).parameters
    ) == ("attestation",)
    assert facade._FAILURE_REASON_IDS == frozenset(FAILURE_REASON_IDS)
    for reason_id in FAILURE_REASON_IDS:
        failure = facade.MetricSupportAuthorityV1Failure(reason_id, "probe")
        assert failure.reason_id == reason_id
        assert failure.detail == "probe"
    with pytest.raises(ValueError, match="reason"):
        facade.MetricSupportAuthorityV1Failure("CALLER_SUPPORT_ACCEPTED", "probe")

    required = {
        "MetricSupportAuthorityV1Failure",
        "MetricSignedSupportAttestationV1",
        "VerifiedMetricSignedSupportAttestationV1",
        "issue_c19_metric_signed_support_attestation_v1",
        "metric_signed_support_attestation_v1_payload",
        "verify_c19_metric_signed_support_attestation_v1",
    }
    assert len(tuple(facade.__all__)) == len(required)
    assert set(facade.__all__) == required
    assert (
        "_reverify_verified_metric_signed_support_attestation_v1" not in facade.__all__
    )


def test_b4_captures_and_executes_the_exact_production_b2_owner_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rulespace_v3.application_materialization_v3 as b2

    facade = _module()
    owner_seam = b2._require_v3m0_application_scenario_materialization_v3_for_parent
    assert facade._require_v3m0_application_scenario_materialization_v3_for_parent is (
        owner_seam
    )
    assert owner_seam in _closure_reachable_objects(
        facade.issue_c19_metric_signed_support_attestation_v1
    )

    calls: list[tuple[object, object]] = []

    def counted_owner_seam(parent, materialization):
        calls.append((parent, materialization))
        return owner_seam(parent, materialization)

    monkeypatch.setattr(
        facade,
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        counted_owner_seam,
    )
    graph = facade._make_metric_support_authority_v1_graph(facade._ISSUANCE_TOKEN)
    raw_parent = object()
    raw_materialization = object()
    with pytest.raises(facade.MetricSupportAuthorityV1Failure) as caught:
        graph.issue(raw_parent, raw_materialization, "actual")
    assert caught.value.reason_id == "MATERIALIZATION_INVALID"
    assert calls == [(raw_parent, raw_materialization)]


def test_b4_exact_protocol_is_i20_origin_singleton_and_never_caller_derived(
    exact_metric_protocol,
) -> None:
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.factory import frozen_tensor_array
    from rulespace_v3.metric import metric_support_payload

    protocol = exact_metric_protocol
    assert protocol.state_schema_id == C19_STATE_SCHEMA_ID
    assert protocol.channel_order == C19_CHANNEL_ORDER
    assert protocol.spatial_shape == C19_SPATIAL_SHAPE
    assert protocol.spatial_ndim == 1
    assert protocol.metric_kind == "constant-state-v1"
    assert np.array_equal(
        frozen_tensor_array(protocol.state_metric),
        np.eye(20, dtype=np.complex128),
    )
    assert protocol.normalization_id == "trace-at-zero-equals-state-dim-v1"
    assert protocol.support_derivation_id == "constant-kernel-origin-only-v1"
    assert protocol.metric_support_offsets == ((0,),)
    assert protocol.metric_support_sha == canonical_sha(metric_support_payload(((0,),)))
    assert protocol.caller_supplied_support_allowed is False


@pytest.mark.parametrize(
    ("role", "factory_sha"),
    (("actual", "b" * 64), ("matched_ablated", "c" * 64)),
)
def test_b4_issues_and_raw_verifies_exact_same_branch_attestation_from_live_lineage(
    monkeypatch: pytest.MonkeyPatch,
    exact_metric_protocol,
    role: str,
    factory_sha: str,
) -> None:
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.metric import metric_support_payload

    fixture = _fixture(monkeypatch, exact_metric_protocol)
    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        role,
    )
    body = capability.attestation

    assert type(capability) is fixture.facade.VerifiedMetricSignedSupportAttestationV1
    assert type(body) is fixture.facade.MetricSignedSupportAttestationV1
    assert body.attestation_schema_version == (
        "v3m0.metric-signed-support-attestation.v1"
    )
    assert body.parent_freeze_v3_sha == "a" * 64
    assert body.current_application_authority_v3_sha == "f" * 64
    assert body.current_scenario_authority_v3_sha == "e" * 64
    assert body.response_contract_v3_sha == "d" * 64
    assert body.metric_support_protocol_sha == exact_metric_protocol.protocol_sha
    assert body.application_scenario_materialization_v3_sha == "3" * 64
    assert body.factory_sha == factory_sha
    assert body.factory_role == role
    assert body.state_schema_id == C19_STATE_SCHEMA_ID
    assert body.channel_order == C19_CHANNEL_ORDER
    assert body.spatial_shape == C19_SPATIAL_SHAPE
    assert body.metric_kind == "constant-state-v1"
    assert body.metric_support_offsets == ((0,),)
    assert body.metric_support_sha == canonical_sha(metric_support_payload(((0,),)))
    assert body.attestation_sha == canonical_sha(
        fixture.facade.metric_signed_support_attestation_v1_payload(body)
    )
    assert fixture.calls.materialization == [(fixture.parent, fixture.materialization)]
    assert fixture.calls.protocol == [exact_metric_protocol]
    assert fixture.calls.support == [((0,),)]

    replayed = fixture.graph.verify(
        body,
        fixture.parent,
        fixture.materialization,
    )
    assert type(replayed) is fixture.facade.VerifiedMetricSignedSupportAttestationV1
    assert replayed.attestation == body
    assert len(fixture.calls.materialization) == 2
    assert len(fixture.calls.protocol) == 2
    assert len(fixture.calls.support) == 2


@pytest.mark.parametrize(
    ("mode", "reason_id"),
    (
        ("materialization", "MATERIALIZATION_INVALID"),
        ("factory", "FACTORY_DEAD"),
        ("protocol", "METRIC_PROTOCOL_DRIFT"),
        ("metric_replay", "METRIC_REPLAY_FAILED"),
        ("cross_root", "CROSS_PARENT_ROOT"),
    ),
)
def test_b4_routes_upstream_and_replay_failures_to_exact_reason_ids(
    monkeypatch: pytest.MonkeyPatch,
    exact_metric_protocol,
    mode: str,
    reason_id: str,
) -> None:
    fixture = _fixture(monkeypatch, exact_metric_protocol)
    fixture.mode["value"] = mode
    with pytest.raises(fixture.facade.MetricSupportAuthorityV1Failure) as caught:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
    assert caught.value.reason_id == reason_id


def test_b4_routes_self_resigned_support_and_branch_splices_to_exact_reasons(
    monkeypatch: pytest.MonkeyPatch,
    exact_metric_protocol,
) -> None:
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.metric import metric_support_payload

    fixture = _fixture(monkeypatch, exact_metric_protocol)
    issued = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).attestation

    hostile_support = _tamper_and_resign(
        issued,
        metric_support_offsets=((1,),),
        metric_support_sha=canonical_sha(metric_support_payload(((1,),))),
    )
    with pytest.raises(fixture.facade.MetricSupportAuthorityV1Failure) as support:
        fixture.graph.verify(
            hostile_support,
            fixture.parent,
            fixture.materialization,
        )
    assert support.value.reason_id == "SUPPORT_INVALID"

    role_only_splice = _tamper_and_resign(
        issued,
        factory_role="matched_ablated",
    )
    with pytest.raises(fixture.facade.MetricSupportAuthorityV1Failure) as branch:
        fixture.graph.verify(
            role_only_splice,
            fixture.parent,
            fixture.materialization,
        )
    assert branch.value.reason_id == "BRANCH_JOIN_FAILED"

    factory_only_splice = _tamper_and_resign(
        issued,
        factory_sha="c" * 64,
    )
    with pytest.raises(fixture.facade.MetricSupportAuthorityV1Failure) as branch:
        fixture.graph.verify(
            factory_only_splice,
            fixture.parent,
            fixture.materialization,
        )
    assert branch.value.reason_id == "BRANCH_JOIN_FAILED"

    matched = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "matched_ablated",
    ).attestation
    verified_matched = fixture.graph.verify(
        matched,
        fixture.parent,
        fixture.materialization,
    )
    assert verified_matched.attestation == matched
    assert matched.factory_role == "matched_ablated"
    assert matched.factory_sha == "c" * 64

    hostile_root = _tamper_and_resign(
        issued,
        parent_freeze_v3_sha="9" * 64,
    )
    with pytest.raises(fixture.facade.MetricSupportAuthorityV1Failure) as root:
        fixture.graph.verify(
            hostile_root,
            fixture.parent,
            fixture.materialization,
        )
    assert root.value.reason_id == "CROSS_PARENT_ROOT"


def test_b4_bare_attestation_sha_invalid_role_and_upstream_resolver_tamper_route_exactly(
    monkeypatch: pytest.MonkeyPatch,
    exact_metric_protocol,
) -> None:
    fixture = _fixture(monkeypatch, exact_metric_protocol)
    issued = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).attestation

    bare_sha_tamper = copy.deepcopy(issued)
    object.__setattr__(bare_sha_tamper, "attestation_sha", "9" * 64)
    with pytest.raises(fixture.facade.MetricSupportAuthorityV1Failure) as replay:
        fixture.graph.verify(
            bare_sha_tamper,
            fixture.parent,
            fixture.materialization,
        )
    assert replay.value.reason_id == "METRIC_REPLAY_FAILED"

    with pytest.raises(fixture.facade.MetricSupportAuthorityV1Failure) as role:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "control",
        )
    assert role.value.reason_id == "BRANCH_JOIN_FAILED"

    object.__setattr__(
        fixture.materialization,
        "_FakeVerifiedMaterializationV3__resolver",
        lambda _wrapper: fixture.body,
    )
    with pytest.raises(fixture.facade.MetricSupportAuthorityV1Failure) as upstream:
        fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "actual",
        )
    assert upstream.value.reason_id == "MATERIALIZATION_INVALID"


def test_b4_rejects_raw_old_and_all_caller_metric_support_grid_sha_surfaces(
    monkeypatch: pytest.MonkeyPatch,
    exact_metric_protocol,
) -> None:
    from rulespace_v3.metric import MetricOriginManifest, StabilityMetricWitness
    from rulespace_v3.prestructure import VerifiedPrestructureAuthority

    fixture = _fixture(monkeypatch, exact_metric_protocol)
    facade = fixture.facade
    issuer = facade.issue_c19_metric_signed_support_attestation_v1
    verifier = facade.verify_c19_metric_signed_support_attestation_v1

    with pytest.raises((TypeError, facade.MetricSupportAuthorityV1Failure)):
        fixture.graph.issue(object(), fixture.materialization, "actual")
    with pytest.raises((TypeError, facade.MetricSupportAuthorityV1Failure)):
        fixture.graph.issue(fixture.parent, fixture.body, "actual")
    with pytest.raises((TypeError, facade.MetricSupportAuthorityV1Failure)):
        fixture.graph.issue(fixture.parent, {}, "actual")
    with pytest.raises((TypeError, facade.MetricSupportAuthorityV1Failure)):
        fixture.graph.issue(
            fixture.parent,
            object.__new__(VerifiedPrestructureAuthority),
            "actual",
        )
    with pytest.raises((TypeError, facade.MetricSupportAuthorityV1Failure)):
        fixture.graph.issue(
            fixture.parent,
            object.__new__(StabilityMetricWitness),
            "actual",
        )
    with pytest.raises((TypeError, facade.MetricSupportAuthorityV1Failure)):
        fixture.graph.issue(
            fixture.parent,
            object.__new__(MetricOriginManifest),
            "actual",
        )

    forbidden_kwargs = (
        "factory",
        "support",
        "support_offsets",
        "grid",
        "points",
        "metric",
        "metric_body",
        "metric_sha",
        "support_sha",
        "protocol_sha",
        "witness",
        "attestation",
    )
    for keyword in forbidden_kwargs:
        with pytest.raises(TypeError):
            issuer(
                fixture.parent,
                fixture.materialization,
                "actual",
                **{keyword: object()},
            )
    issued = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).attestation
    for keyword in forbidden_kwargs:
        with pytest.raises(TypeError):
            verifier(
                issued,
                fixture.parent,
                fixture.materialization,
                **{keyword: object()},
            )
    with pytest.raises(TypeError):
        verifier(issued)
    with pytest.raises((TypeError, facade.MetricSupportAuthorityV1Failure)):
        verifier({}, fixture.parent, fixture.materialization)


def test_b4_opaque_registry_rejects_forged_dead_tampered_and_global_redirects(
    monkeypatch: pytest.MonkeyPatch,
    exact_metric_protocol,
) -> None:
    fixture = _fixture(monkeypatch, exact_metric_protocol)
    facade = fixture.facade
    wrapper_type = facade.VerifiedMetricSignedSupportAttestationV1
    assert tuple(wrapper_type.__slots__) == (
        "__attestation",
        "__authority_seal",
        "__weakref__",
    )
    assert isinstance(wrapper_type.attestation, property)
    property_closure = tuple(
        cell.cell_contents for cell in (wrapper_type.attestation.fget.__closure__ or ())
    )
    assert facade._resolve_metric_support_property in property_closure
    captured_property_resolver = facade._resolve_metric_support_property

    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    assert not hasattr(capability, "__dict__")
    view = fixture.graph.reverify(capability)
    assert view.attestation == capability.attestation
    assert view.parent is fixture.parent
    assert view.materialization is fixture.materialization
    assert view.factory is fixture.actual_factory
    assert view.factory_binding == fixture.body.actual_factory_binding

    forged = object.__new__(facade.VerifiedMetricSignedSupportAttestationV1)
    with pytest.raises((TypeError, ValueError)):
        fixture.graph.reverify(forged)

    other_graph = facade._make_metric_support_authority_v1_graph(facade._ISSUANCE_TOKEN)
    with pytest.raises((TypeError, ValueError)):
        other_graph.reverify(capability)

    hostile_body = _tamper_and_resign(
        capability.attestation,
        factory_sha="9" * 64,
    )
    object.__setattr__(
        capability,
        "_VerifiedMetricSignedSupportAttestationV1__attestation",
        hostile_body,
    )
    with pytest.raises((TypeError, ValueError)):
        fixture.graph.reverify(capability)

    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    expected_body = copy.deepcopy(capability.attestation)
    forged_resolver = lambda _wrapper: SimpleNamespace(  # noqa: E731
        attestation="FORGED-ATTESTATION"
    )
    try:
        object.__setattr__(
            capability,
            "_VerifiedMetricSignedSupportAttestationV1__resolver",
            forged_resolver,
        )
    except AttributeError:
        pass
    else:
        with pytest.raises((TypeError, ValueError, RuntimeError)):
            fixture.graph.reverify(capability)
    assert capability.attestation == expected_body

    # Dependencies are captured when the graph is made; rebinding facade
    # globals afterward cannot redirect this authority graph.
    stable_fixture = _fixture(monkeypatch, exact_metric_protocol)

    def redirected(*_args, **_kwargs):
        raise AssertionError("redirected global was consulted")

    monkeypatch.setattr(
        facade,
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        redirected,
    )
    monkeypatch.setattr(
        facade,
        "verify_metric_support_derivation_protocol_v1",
        redirected,
    )
    monkeypatch.setattr(facade, "metric_support_payload", redirected)
    monkeypatch.setattr(facade, "_resolve_metric_support_property", redirected)
    stable = stable_fixture.graph.issue(
        stable_fixture.parent,
        stable_fixture.materialization,
        "actual",
    )
    assert stable.attestation.factory_role == "actual"
    assert capability.attestation == expected_body
    assert captured_property_resolver in tuple(
        cell.cell_contents for cell in (wrapper_type.attestation.fget.__closure__ or ())
    )


def test_b4_reverify_accepts_fresh_live_b2_child_with_the_same_exact_branch_body(
    monkeypatch: pytest.MonkeyPatch,
    exact_metric_protocol,
) -> None:
    """B2 replay deliberately remints child factory wrappers on every join."""

    fixture = _fixture(
        monkeypatch,
        exact_metric_protocol,
        fresh_factories=True,
    )
    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )

    first = fixture.graph.reverify(capability)
    second = fixture.graph.reverify(capability)

    issued_factory = fixture.calls.resolved_factories[0][0]
    assert first.factory is not issued_factory
    assert second.factory is not first.factory
    assert first.factory.factory == issued_factory.factory
    assert second.factory.factory == issued_factory.factory
    assert first.factory_binding == second.factory_binding
    assert first.attestation == second.attestation == capability.attestation


def test_b4_public_api_closures_ignore_global_graph_dependency_and_resolver_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _module()
    issuer = facade.issue_c19_metric_signed_support_attestation_v1
    verifier = facade.verify_c19_metric_signed_support_attestation_v1
    production_graph = facade._PRODUCTION_GRAPH
    assert production_graph.issue in tuple(
        cell.cell_contents for cell in (issuer.__closure__ or ())
    )
    assert production_graph.verify in tuple(
        cell.cell_contents for cell in (verifier.__closure__ or ())
    )
    before = tuple(
        tuple(id(cell.cell_contents) for cell in (function.__closure__ or ()))
        for function in (issuer, verifier)
    )
    assert all(values for values in before)

    def redirected(*_args, **_kwargs):
        raise AssertionError("redirected global was consulted")

    monkeypatch.setattr(
        facade,
        "_PRODUCTION_GRAPH",
        SimpleNamespace(issue=redirected, verify=redirected, reverify=redirected),
    )
    for name in (
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        "verify_metric_support_derivation_protocol_v1",
        "metric_support_payload",
        "_resolve_metric_support_property",
    ):
        monkeypatch.setattr(facade, name, redirected)

    after = tuple(
        tuple(id(cell.cell_contents) for cell in (function.__closure__ or ()))
        for function in (issuer, verifier)
    )
    assert after == before
    assert all(
        "_PRODUCTION_GRAPH" not in function.__code__.co_names
        for function in (issuer, verifier)
    )
    with pytest.raises(facade.MetricSupportAuthorityV1Failure) as issued:
        issuer(object(), object(), "actual")
    assert issued.value.reason_id == "MATERIALIZATION_INVALID"
    with pytest.raises((TypeError, ValueError)):
        verifier(object(), object(), object())


def test_b4_existing_graph_ignores_its_own_record_payload_and_literal_globals(
    monkeypatch: pytest.MonkeyPatch,
    exact_metric_protocol,
) -> None:
    fixture = _fixture(monkeypatch, exact_metric_protocol)
    facade = fixture.facade
    graph = fixture.graph
    capability = graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    raw = capability.attestation
    expected_view_type = facade._VerifiedMetricSupportAttestationV1View
    expected_failure_type = facade.MetricSupportAuthorityV1Failure

    def redirected(*_args, **_kwargs):
        raise AssertionError("redirected metric-support owner global was consulted")

    for name in (
        "metric_signed_support_attestation_v1_payload",
        "_VerifiedMetricSupportAttestationV1View",
        "_MetricSupportAuthorityRecordV1",
        "MetricSupportAuthorityV1Failure",
    ):
        monkeypatch.setattr(facade, name, redirected)
    monkeypatch.setattr(facade, "weakref", SimpleNamespace(ref=redirected))
    monkeypatch.setattr(facade, "id", redirected, raising=False)
    monkeypatch.setattr(facade, "_PROPERTY_BINDING_TOKEN", object())
    monkeypatch.setattr(facade, "_C19_STATE_SCHEMA_ID", "redirected-state")
    monkeypatch.setattr(facade, "_C19_CHANNEL_ORDER", ("redirected-channel",))
    monkeypatch.setattr(facade, "_C19_SPATIAL_SHAPE", (999,))
    monkeypatch.setattr(facade, "_C19_METRIC_KIND", "redirected-metric")
    monkeypatch.setattr(facade, "_C19_METRIC_SUPPORT", ((999,),))

    replayed = graph.verify(raw, fixture.parent, fixture.materialization)
    view = graph.reverify(replayed)
    assert type(view) is expected_view_type
    assert view.attestation == raw
    assert view.factory_binding == fixture.body.actual_factory_binding

    fixture.mode["value"] = "protocol"
    with pytest.raises(expected_failure_type) as caught:
        graph.issue(fixture.parent, fixture.materialization, "actual")
    assert caught.value.reason_id == "METRIC_PROTOCOL_DRIFT"


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


def test_b4_static_import_dag_is_the_exact_three_edges() -> None:
    module_path = REPO_ROOT / "rulespace_v3" / "metric_support_authority_v1.py"
    assert module_path.is_file()
    assert _direct_rulespace_imports(module_path) == {
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.parent_v3_contracts",
        "rulespace_v3.metric",
    }
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    b2_imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and (
            (node.level == 1 and node.module == "application_materialization_v3")
            or node.module == "rulespace_v3.application_materialization_v3"
        )
        for alias in node.names
    }
    assert (
        "_require_v3m0_application_scenario_materialization_v3_for_parent"
        in b2_imported_names
    )
