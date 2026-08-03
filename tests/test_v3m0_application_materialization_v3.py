"""Strict RED contracts for Parent-v3 C19 scenario materialization."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, fields, replace
import inspect
from pathlib import Path
from types import SimpleNamespace
import weakref

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
C19_CONTROL_CASE_ID = "C19_FULL_POSITIVE_OBSERVER_COLLAPSE"
C19_APPLICATION_INSTANCE_ID = "v3m0.synthetic-control.c19.v2"
C19_SCENARIO_ID = "v3m0.synthetic-control.c19.v2.scenario.observer-collapse.v2"


@dataclass(frozen=True)
class _FakeCalibrationBody:
    calibration_v3_sha: str


@dataclass(frozen=True)
class _FakePermitBody:
    permit_schema_version: str
    parent_freeze_v3_sha: str
    calibration: _FakeCalibrationBody
    current_application_authority: object
    current_scenario_authority: object
    current_scenario_response_contract: object
    selected_fejer_order: int
    permit_scope_id: str
    permit_sha: str

    def __post_init__(self) -> None:
        if self.permit_schema_version != "v3m0.calibration-application-permit.v3":
            raise ValueError("fake permit schema drifted")
        if len(self.parent_freeze_v3_sha) != 64:
            raise ValueError("fake permit Parent-v3 root drifted")
        if type(self.calibration) is not _FakeCalibrationBody:
            raise TypeError("fake permit calibration type drifted")
        if self.current_application_authority.control_case_id != (C19_CONTROL_CASE_ID):
            raise ValueError("fake permit application drifted")
        if self.current_scenario_authority not in (
            self.current_application_authority.scenario_authorities
        ):
            raise ValueError("fake permit scenario is outside its application")
        if self.current_scenario_response_contract != (
            self.current_scenario_authority.response_contract
        ):
            raise ValueError("fake permit response is outside its scenario")
        if type(self.selected_fejer_order) is not int or self.selected_fejer_order <= 0:
            raise ValueError("fake permit Fejer order drifted")
        if self.permit_scope_id != ("v3m0-parent-v3-current-application-scenario-v1"):
            raise ValueError("fake permit scope drifted")
        if len(self.permit_sha) != 64:
            raise ValueError("fake permit SHA drifted")


class _FakeParentV3:
    def __init__(self, manifest: object) -> None:
        self.manifest = manifest


class _FakeVerifiedPermitV3:
    def __init__(self, parent: _FakeParentV3, permit: _FakePermitBody) -> None:
        self.parent = parent
        self._permit = permit
        resolver = lambda wrapper: copy.deepcopy(wrapper._permit)  # noqa: E731
        object.__setattr__(
            self,
            "_FakeVerifiedPermitV3__resolver",
            resolver,
        )
        _FAKE_PERMIT_RESOLVERS[self] = resolver

    @property
    def permit(self) -> _FakePermitBody:
        resolver = object.__getattribute__(
            self,
            "_FakeVerifiedPermitV3__resolver",
        )
        return resolver(self)


_FAKE_PERMIT_RESOLVERS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _module():
    import rulespace_v3.application_materialization_v3 as facade

    return facade


@pytest.fixture(scope="module")
def current_c19_application():
    from rulespace_v3.parent_v3_contracts import (
        build_c19_current_application_authority_v3,
    )

    return build_c19_current_application_authority_v3()


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    application: object,
    *,
    root: str = "a",
    force_factory_replay_failure: bool = False,
):
    facade = _module()
    parent_sha = root * 64
    scenario = application.scenario_authorities[0]
    permit_body = _FakePermitBody(
        permit_schema_version="v3m0.calibration-application-permit.v3",
        parent_freeze_v3_sha=parent_sha,
        calibration=_FakeCalibrationBody("e" * 64),
        current_application_authority=application,
        current_scenario_authority=scenario,
        current_scenario_response_contract=scenario.response_contract,
        selected_fejer_order=32,
        permit_scope_id="v3m0-parent-v3-current-application-scenario-v1",
        permit_sha=("b" if root != "b" else "c") * 64,
    )
    parent_manifest = SimpleNamespace(
        parent_freeze_v3_sha=parent_sha,
        reviewed_candidate_v3=SimpleNamespace(
            refrozen_current_application_authorities_v3=(application,),
        ),
    )
    parent = _FakeParentV3(parent_manifest)
    permit = _FakeVerifiedPermitV3(parent, permit_body)

    def require_parent(observed_parent):
        if type(observed_parent) is not _FakeParentV3:
            raise TypeError("exact live Parent-v3 required")
        return copy.deepcopy(observed_parent.manifest)

    def verify_permit(observed_parent, observed_permit):
        if type(observed_permit) is not _FakeVerifiedPermitV3:
            raise TypeError("exact live permit-v3 required")
        if observed_permit.parent is not observed_parent:
            raise ValueError("permit belongs to another Parent-v3 identity")
        resolver = object.__getattribute__(
            observed_permit,
            "_FakeVerifiedPermitV3__resolver",
        )
        if _FAKE_PERMIT_RESOLVERS.get(observed_permit) is not resolver:
            raise ValueError("permit resolver immutable guard drifted")
        return observed_permit

    def permit_payload(permit):
        if type(permit) is not _FakePermitBody:
            raise TypeError("exact fake raw permit required")
        permit.__post_init__()
        return {
            "permit_schema_version": permit.permit_schema_version,
            "parent_freeze_v3_sha": permit.parent_freeze_v3_sha,
            "calibration": {
                "calibration_v3_sha": permit.calibration.calibration_v3_sha,
            },
            "current_application_authority": {
                "application_authority_sha": (
                    permit.current_application_authority.application_authority_sha
                ),
            },
            "current_scenario_authority": {
                "scenario_authority_sha": (
                    permit.current_scenario_authority.scenario_authority_sha
                ),
            },
            "current_scenario_response_contract": {
                "response_contract_sha": (
                    permit.current_scenario_response_contract.response_contract_sha
                ),
            },
            "selected_fejer_order": permit.selected_fejer_order,
            "permit_scope_id": permit.permit_scope_id,
        }

    monkeypatch.setattr(facade, "VerifiedParentFreezeV3", _FakeParentV3)
    monkeypatch.setattr(facade, "require_current_parent_v3", require_parent)
    monkeypatch.setattr(
        facade,
        "VerifiedCalibrationApplicationPermitV3",
        _FakeVerifiedPermitV3,
    )
    monkeypatch.setattr(facade, "CalibrationApplicationPermitV3", _FakePermitBody)
    monkeypatch.setattr(
        facade,
        "calibration_application_permit_v3_payload",
        permit_payload,
    )
    monkeypatch.setattr(
        facade,
        "verify_calibration_application_permit_v3",
        verify_permit,
    )
    if force_factory_replay_failure:

        def reject_factory(*_args, **_kwargs):
            raise ValueError("forced factory replay failure")

        monkeypatch.setattr(facade, "verify_factory", reject_factory)
    graph = facade._make_application_materialization_v3_graph(facade._ISSUANCE_TOKEN)
    return SimpleNamespace(
        facade=facade,
        graph=graph,
        parent=parent,
        parent_manifest=parent_manifest,
        permit=permit,
        permit_body=permit_body,
        application=application,
        scenario=scenario,
    )


def test_b2_exact_records_public_api_and_no_raw_or_v2_adapter_surface() -> None:
    facade = _module()
    expected_failure_reasons = frozenset(
        (
            "PARENT_V3_UNAVAILABLE",
            "PERMIT_INVALID",
            "FACTORY_REPLAY_FAILED",
            "FACTORY_WIRE_DRIFT",
            "BRANCH_JOIN_FAILED",
            "CROSS_PARENT_ROOT",
        )
    )

    assert [item.name for item in fields(facade.FactoryBranchBindingV3)] == [
        "binding_schema_version",
        "parent_freeze_v3_sha",
        "permit_sha",
        "materialization_input_sha",
        "branch",
        "factory",
        "construction_trace",
        "layer_slot_ids",
        "support_offsets",
        "support_sha",
        "active_step_count",
        "layer_slot_count",
        "primitive_count",
        "neutral_identity_count",
        "binding_sha",
    ]
    assert [
        item.name for item in fields(facade.ApplicationScenarioMaterializationV3)
    ] == [
        "materialization_schema_version",
        "permit",
        "current_application_authority",
        "current_scenario_authority",
        "current_scenario_response_contract",
        "basis_contract",
        "construction_trace",
        "ablation_pair_snapshot",
        "actual_factory_binding",
        "matched_ablated_factory_binding",
        "materialization_sha",
    ]
    assert tuple(
        inspect.signature(facade.materialize_v3m0_application_scenario_v3).parameters
    ) == ("parent", "permit")
    assert tuple(
        inspect.signature(
            facade.verify_v3m0_application_scenario_materialization_v3
        ).parameters
    ) == ("parent", "permit", "materialization")
    # Derived owner-internal seam: B3's frozen DAG cannot import B1, so B2
    # must rejoin the caller Parent to its already permit-bound capability.
    # This is deliberately not a B0 public API or an exported surface.
    owner_seam = facade._require_v3m0_application_scenario_materialization_v3_for_parent
    assert tuple(inspect.signature(owner_seam).parameters) == (
        "parent",
        "materialization",
    )
    assert owner_seam.__name__ not in facade.__all__
    assert facade._FAILURE_REASON_IDS == expected_failure_reasons
    for reason_id in expected_failure_reasons:
        failure = facade.ApplicationMaterializationV3Failure(reason_id, "probe")
        assert failure.reason_id == reason_id
        assert failure.detail == "probe"
    with pytest.raises(ValueError, match="reason"):
        facade.ApplicationMaterializationV3Failure("UNFROZEN_REASON", "probe")
    for public_api in (
        facade.materialize_v3m0_application_scenario_v3,
        facade.verify_v3m0_application_scenario_materialization_v3,
    ):
        assert "_PRODUCTION_GRAPH" not in public_api.__code__.co_names
    assert not {
        "materialize_v3m0_application_scenario_v2",
        "materialize_raw_application_scenario_v3",
        "hydrate_application_scenario_materialization_v3",
        "materialize_actual_factory_v3",
        "materialize_matched_factory_v3",
    } & set(facade.__all__)


def test_b2_current_c19_materializes_one_atomic_live_factory_pair(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
) -> None:
    from rulespace_v3.factory import VerifiedFactory, _reverify_verified_factory

    fixture = _fixture(monkeypatch, current_c19_application)
    capability = fixture.graph.materialize(fixture.parent, fixture.permit)
    body = capability.materialization
    actual = _reverify_verified_factory(capability.actual_factory)
    matched = _reverify_verified_factory(capability.matched_ablated_factory)
    runtime = fixture.application.runtime_construction

    assert type(capability) is (
        fixture.facade.VerifiedV3M0ApplicationScenarioMaterializationV3
    )
    assert type(capability.actual_factory) is VerifiedFactory
    assert type(capability.matched_ablated_factory) is VerifiedFactory
    assert (
        fixture.graph.verify(
            fixture.parent,
            fixture.permit,
            capability,
        )
        is capability
    )

    assert body.permit == fixture.permit_body
    assert body.current_application_authority == fixture.application
    assert body.current_scenario_authority == fixture.scenario
    assert body.current_scenario_response_contract == (
        fixture.scenario.response_contract
    )
    assert body.basis_contract == fixture.scenario.response_contract.basis_contract
    assert body.basis_contract.common_source_tensor == (
        fixture.application.common_source_tensor
    )
    assert body.basis_contract.common_readout_tensor == (
        fixture.application.common_readout_tensor
    )
    assert body.construction_trace == runtime.construction_trace
    assert body.actual_factory_binding.branch == "actual"
    assert body.matched_ablated_factory_binding.branch == "matched_ablated"
    assert actual.factory == runtime.actual_factory
    assert matched.factory == runtime.matched_factory
    assert body.actual_factory_binding.factory == runtime.actual_factory
    assert body.matched_ablated_factory_binding.factory == runtime.matched_factory
    assert body.actual_factory_binding.construction_trace == runtime.construction_trace
    assert body.matched_ablated_factory_binding.construction_trace == (
        runtime.construction_trace
    )
    assert body.actual_factory_binding.layer_slot_ids == (
        runtime.actual_factory.layer_slot_ids
    )
    assert body.matched_ablated_factory_binding.layer_slot_ids == (
        runtime.matched_factory.layer_slot_ids
    )
    assert body.actual_factory_binding.support_offsets == (
        runtime.actual_support_offsets
    )
    assert body.matched_ablated_factory_binding.support_offsets == (
        runtime.matched_support_offsets
    )
    assert body.ablation_pair_snapshot.actual_factory == runtime.actual_factory
    assert body.ablation_pair_snapshot.ablated_factory == runtime.matched_factory
    assert body.ablation_pair_snapshot.ablation_manifest == runtime.ablation_manifest

    expected = (
        (body.actual_factory_binding, 50, 50, 50, 0),
        (body.matched_ablated_factory_binding, 50, 50, 30, 20),
    )
    for binding, slots, primitives, active, neutral in expected:
        assert len(binding.layer_slot_ids) == slots
        assert len(binding.factory.layer_slot_ids) == slots
        assert len(binding.factory.primitives) == primitives
        assert binding.layer_slot_count == slots
        assert binding.primitive_count == primitives
        assert binding.active_step_count == active
        assert binding.neutral_identity_count == neutral
        assert (
            sum(
                primitive.operation_id == "neutral_identity"
                for primitive in binding.factory.primitives
            )
            == neutral
        )
    assert body.actual_factory_binding.materialization_input_sha == (
        body.matched_ablated_factory_binding.materialization_input_sha
    )
    assert body.actual_factory_binding.permit_sha == fixture.permit_body.permit_sha
    assert body.matched_ablated_factory_binding.permit_sha == (
        fixture.permit_body.permit_sha
    )
    assert body.actual_factory_binding.parent_freeze_v3_sha == (
        fixture.parent_manifest.parent_freeze_v3_sha
    )
    assert body.matched_ablated_factory_binding.parent_freeze_v3_sha == (
        fixture.parent_manifest.parent_freeze_v3_sha
    )
    replacements = {
        item.layer_slot_id: item for item in runtime.ablation_manifest.replacements
    }
    assert len(replacements) == 20
    for slot_id, actual_primitive, matched_primitive in zip(
        runtime.actual_factory.layer_slot_ids,
        runtime.actual_factory.primitives,
        runtime.matched_factory.primitives,
    ):
        assert actual_primitive.layer_slot_id == slot_id
        assert matched_primitive.layer_slot_id == slot_id
        if slot_id in replacements:
            replacement = replacements[slot_id]
            assert actual_primitive.operation_id == "local_canonical_shear"
            assert matched_primitive.operation_id == "neutral_identity"
            assert matched_primitive.neutral_identity_id == (
                replacement.neutral_identity_id
            )
            assert matched_primitive.mechanism_id == actual_primitive.mechanism_id
        else:
            assert matched_primitive == actual_primitive


@pytest.mark.parametrize(
    ("attack", "failure_reason"),
    (
        ("four-channels", "FACTORY_WIRE_DRIFT"),
        ("delete-slot", "FACTORY_WIRE_DRIFT"),
        ("thirty-primitives", "FACTORY_WIRE_DRIFT"),
        ("swap-branches", "BRANCH_JOIN_FAILED"),
    ),
)
def test_b2_c19_wire_count_and_branch_mutations_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
    attack: str,
    failure_reason: str,
) -> None:
    application = copy.deepcopy(current_c19_application)
    runtime = application.runtime_construction
    if attack == "four-channels":
        object.__setattr__(application, "channel_order", application.channel_order[:4])
    elif attack == "delete-slot":
        actual = runtime.actual_factory
        object.__setattr__(actual, "layer_slot_ids", actual.layer_slot_ids[:-1])
    elif attack == "thirty-primitives":
        matched = runtime.matched_factory
        object.__setattr__(matched, "primitives", matched.primitives[:30])
    else:
        actual = runtime.actual_factory
        matched = runtime.matched_factory
        object.__setattr__(runtime, "actual_factory", matched)
        object.__setattr__(runtime, "matched_factory", actual)
    fixture = _fixture(monkeypatch, application)

    with pytest.raises(fixture.facade.ApplicationMaterializationV3Failure) as caught:
        fixture.graph.materialize(fixture.parent, fixture.permit)
    assert caught.value.reason_id == failure_reason


def test_b2_factory_replay_failure_is_typed(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
) -> None:
    fixture = _fixture(
        monkeypatch,
        current_c19_application,
        force_factory_replay_failure=True,
    )

    with pytest.raises(fixture.facade.ApplicationMaterializationV3Failure) as caught:
        fixture.graph.materialize(fixture.parent, fixture.permit)
    assert caught.value.reason_id == "FACTORY_REPLAY_FAILED"


def test_b2_upstream_permit_resolver_tamper_is_rejected_before_materialization(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
) -> None:
    fixture = _fixture(monkeypatch, current_c19_application)
    object.__setattr__(
        fixture.permit,
        "_FakeVerifiedPermitV3__resolver",
        lambda _wrapper: copy.deepcopy(fixture.permit_body),
    )

    with pytest.raises(fixture.facade.ApplicationMaterializationV3Failure) as caught:
        fixture.graph.materialize(fixture.parent, fixture.permit)
    assert caught.value.reason_id == "PERMIT_INVALID"


def test_b2_owner_view_retains_the_exact_live_permit_identity(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
) -> None:
    from rulespace_v3.factory import _reverify_verified_factory

    fixture = _fixture(monkeypatch, current_c19_application)
    capability = fixture.graph.materialize(fixture.parent, fixture.permit)

    view = fixture.graph.require_for_parent(fixture.parent, capability)

    assert view.permit is fixture.permit
    assert view.materialization == capability.materialization
    assert _reverify_verified_factory(view.actual_factory).factory == (
        _reverify_verified_factory(capability.actual_factory).factory
    )
    assert _reverify_verified_factory(view.matched_ablated_factory).factory == (
        _reverify_verified_factory(capability.matched_ablated_factory).factory
    )


def test_b2_raw_hydration_historical_parent_caller_factory_and_recipe_die(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
) -> None:
    fixture = _fixture(monkeypatch, current_c19_application)
    capability = fixture.graph.materialize(fixture.parent, fixture.permit)
    raw = capability.materialization

    with pytest.raises(
        fixture.facade.ApplicationMaterializationV3Failure
    ) as parent_failure:
        fixture.graph.materialize(object(), fixture.permit)
    assert parent_failure.value.reason_id == "PARENT_V3_UNAVAILABLE"
    forged_permit = object.__new__(_FakeVerifiedPermitV3)
    with pytest.raises(
        fixture.facade.ApplicationMaterializationV3Failure
    ) as permit_failure:
        fixture.graph.materialize(fixture.parent, forged_permit)
    assert permit_failure.value.reason_id == "PERMIT_INVALID"
    with pytest.raises((TypeError, ValueError)):
        fixture.graph.materialize(fixture.parent, fixture.permit_body)
    with pytest.raises(TypeError):
        fixture.facade.materialize_v3m0_application_scenario_v3(
            fixture.parent,
            fixture.permit,
            factory=object(),
        )
    with pytest.raises(TypeError):
        fixture.facade.materialize_v3m0_application_scenario_v3(
            fixture.parent,
            fixture.permit,
            recipe=object(),
        )
    with pytest.raises((TypeError, ValueError)):
        fixture.graph.verify(fixture.parent, fixture.permit, raw)
    forged = object.__new__(
        fixture.facade.VerifiedV3M0ApplicationScenarioMaterializationV3
    )
    with pytest.raises((TypeError, ValueError, AttributeError)):
        fixture.graph.verify(fixture.parent, fixture.permit, forged)


def test_b2_issued_body_and_child_factory_tampering_cannot_redirect_replay(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
) -> None:
    from rulespace_v3.factory import _reverify_verified_factory

    fixture = _fixture(monkeypatch, current_c19_application)
    wrapper_type = fixture.facade.VerifiedV3M0ApplicationScenarioMaterializationV3
    assert not any("resolver" in slot for slot in wrapper_type.__slots__)
    property_resolvers = tuple(
        descriptor.fget.__closure__[0].cell_contents
        for descriptor in (
            wrapper_type.materialization,
            wrapper_type.actual_factory,
            wrapper_type.matched_ablated_factory,
        )
    )
    assert all(callable(item) for item in property_resolvers)
    assert len({id(item) for item in property_resolvers}) == 1
    capability = fixture.graph.materialize(fixture.parent, fixture.permit)
    expected_body = copy.deepcopy(capability.materialization)

    detached = capability.materialization
    object.__setattr__(detached, "materialization_sha", "f" * 64)
    try:
        verified = fixture.graph.verify(
            fixture.parent,
            fixture.permit,
            capability,
        )
    except (TypeError, ValueError, RuntimeError):
        pass
    else:
        assert verified is capability
        assert capability.materialization == expected_body

    private_body_name = (
        "_VerifiedV3M0ApplicationScenarioMaterializationV3__materialization"
    )
    try:
        private_body = object.__getattribute__(capability, private_body_name)
    except AttributeError:
        private_body = None
    if private_body is not None:
        object.__setattr__(private_body, "materialization_sha", "e" * 64)
        with pytest.raises((TypeError, ValueError, RuntimeError)):
            fixture.graph.verify(
                fixture.parent,
                fixture.permit,
                capability,
            )

    capability = fixture.graph.materialize(fixture.parent, fixture.permit)
    child = capability.actual_factory
    object.__setattr__(child, "_VerifiedFactory__seal", object())
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        _reverify_verified_factory(child)
    try:
        fixture.graph.verify(fixture.parent, fixture.permit, capability)
    except (TypeError, ValueError, RuntimeError):
        pass
    else:
        fresh_child = _reverify_verified_factory(capability.actual_factory)
        assert fresh_child.factory == (
            fixture.application.runtime_construction.actual_factory
        )


def test_b2_instance_callable_cannot_redirect_any_capability_property(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
) -> None:
    from rulespace_v3.factory import _reverify_verified_factory

    fixture = _fixture(monkeypatch, current_c19_application)
    capability = fixture.graph.materialize(fixture.parent, fixture.permit)
    expected_body = copy.deepcopy(capability.materialization)
    resolver_name = "_VerifiedV3M0ApplicationScenarioMaterializationV3__resolver"
    forged = lambda _value: SimpleNamespace(  # noqa: E731
        materialization="FORGED-BODY",
        actual_factory="FORGED-ACTUAL",
        matched_ablated_factory="FORGED-MATCHED",
    )

    try:
        object.__setattr__(capability, resolver_name, forged)
    except AttributeError:
        pass
    else:
        with pytest.raises((TypeError, ValueError, RuntimeError)):
            fixture.graph.verify(fixture.parent, fixture.permit, capability)

    assert capability.materialization == expected_body
    assert _reverify_verified_factory(capability.actual_factory).factory == (
        fixture.application.runtime_construction.actual_factory
    )
    assert (
        _reverify_verified_factory(capability.matched_ablated_factory).factory
        == fixture.application.runtime_construction.matched_factory
    )


def test_b2_public_api_is_closed_over_callables_not_redirectable_global_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _module()
    closed_apis = (
        facade.materialize_v3m0_application_scenario_v3,
        facade.verify_v3m0_application_scenario_materialization_v3,
        facade._require_v3m0_application_scenario_materialization_v3_for_parent,
    )
    before = tuple(
        tuple(cell.cell_contents for cell in (function.__closure__ or ()))
        for function in closed_apis
    )
    before_identities = tuple(tuple(id(item) for item in cells) for cells in before)
    assert all(cells for cells in before)

    monkeypatch.setattr(
        facade,
        "_PRODUCTION_GRAPH",
        SimpleNamespace(
            materialize=lambda *_args, **_kwargs: "FORGED",
            verify=lambda *_args, **_kwargs: "FORGED",
        ),
        raising=False,
    )
    after = tuple(
        tuple(cell.cell_contents for cell in (function.__closure__ or ()))
        for function in closed_apis
    )
    after_identities = tuple(tuple(id(item) for item in cells) for cells in after)
    assert after_identities == before_identities
    assert all(
        "_PRODUCTION_GRAPH" not in function.__code__.co_names
        for function in closed_apis
    )


def test_b2_cross_parent_root_and_permit_identity_die(
    monkeypatch: pytest.MonkeyPatch,
    current_c19_application,
) -> None:
    fixture = _fixture(monkeypatch, current_c19_application, root="a")
    capability = fixture.graph.materialize(fixture.parent, fixture.permit)
    other_parent = _FakeParentV3(
        SimpleNamespace(
            parent_freeze_v3_sha="c" * 64,
            reviewed_candidate_v3=fixture.parent_manifest.reviewed_candidate_v3,
        )
    )
    other_permit = _FakeVerifiedPermitV3(
        other_parent,
        _FakePermitBody(
            permit_schema_version="v3m0.calibration-application-permit.v3",
            parent_freeze_v3_sha="c" * 64,
            calibration=_FakeCalibrationBody("e" * 64),
            current_application_authority=fixture.application,
            current_scenario_authority=fixture.scenario,
            current_scenario_response_contract=fixture.scenario.response_contract,
            selected_fejer_order=32,
            permit_scope_id="v3m0-parent-v3-current-application-scenario-v1",
            permit_sha="d" * 64,
        ),
    )
    cross_root_permit = _FakeVerifiedPermitV3(
        fixture.parent,
        replace(fixture.permit_body, parent_freeze_v3_sha="c" * 64),
    )

    with pytest.raises(
        fixture.facade.ApplicationMaterializationV3Failure
    ) as cross_verify:
        fixture.graph.verify(other_parent, other_permit, capability)
    assert cross_verify.value.reason_id == "CROSS_PARENT_ROOT"
    with pytest.raises(
        fixture.facade.ApplicationMaterializationV3Failure
    ) as wrong_permit:
        fixture.graph.verify(fixture.parent, other_permit, capability)
    assert wrong_permit.value.reason_id == "PERMIT_INVALID"
    with pytest.raises(
        fixture.facade.ApplicationMaterializationV3Failure
    ) as cross_materialize:
        fixture.graph.materialize(fixture.parent, cross_root_permit)
    assert cross_materialize.value.reason_id == "CROSS_PARENT_ROOT"
    with pytest.raises(
        fixture.facade.ApplicationMaterializationV3Failure
    ) as wrong_parent:
        fixture.graph.materialize(other_parent, fixture.permit)
    assert wrong_parent.value.reason_id == "PERMIT_INVALID"


def test_b2_production_module_imports_only_the_frozen_v6_dag() -> None:
    module_path = REPO_ROOT / "rulespace_v3/application_materialization_v3.py"
    assert module_path.is_file()
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            imported.add(f"rulespace_v3.{node.module}")
    assert imported == {
        "rulespace_v3.ablation",
        "rulespace_v3.application_authority_v3",
        "rulespace_v3.factory",
        "rulespace_v3.pair_snapshot",
        "rulespace_v3.parent_authority_v3",
        "rulespace_v3.trace",
    }
    assert not imported & {
        "rulespace_v3.application_authority_v2",
        "rulespace_v3.application_materialization_v2",
        "rulespace_v3.c19_refreeze_v2",
        "rulespace_v3.parent_authority",
        "rulespace_v3.parent_freeze",
        "rulespace_v3.parent_freeze_v2",
        "rulespace_v3.parent_v2_contracts",
        "rulespace_v3.parent_v3_contracts",
    }
