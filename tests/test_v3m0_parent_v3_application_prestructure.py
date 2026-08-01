"""Strict RED contracts for the Parent-v3 application-prestructure owner."""

from __future__ import annotations

import ast
import copy
from dataclasses import fields, replace
import gc
import inspect
from pathlib import Path
from types import SimpleNamespace
import weakref

import numpy as np
import pytest

import test_v3m0_transition_authority_v3 as support


REPO_ROOT = Path(__file__).resolve().parents[1]
C19_STATE_SCHEMA_ID = "v3m0.c19-real-canonical-state.v2"
C19_CHANNEL_ORDER = tuple(
    channel for pair in range(10) for channel in (f"q{pair}", f"p{pair}")
)
C19_CHANNEL_PAIRS = tuple(
    (C19_CHANNEL_ORDER[index], C19_CHANNEL_ORDER[index + 1])
    for index in range(0, len(C19_CHANNEL_ORDER), 2)
)


def _module():
    import rulespace_v3.parent_v3_application_prestructure as facade

    return facade


def _fixture(monkeypatch: pytest.MonkeyPatch, *, root: str = "a"):
    from rulespace_v3.application_materialization_v3 import (
        ApplicationMaterializationV3Failure,
    )

    facade = _module()
    parent_sha = root * 64
    parent = support._FakeParentV3(parent_sha)
    actual_kernel, matched_kernel = support._kernel_pair()
    actual_body = support._FakeFactoryBody(
        factory_sha="1" * 64,
        target_spec_sha="8" * 64,
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        state_shape=(20, 8),
        spatial_ndim=1,
        dt=0.125,
        boundary_manifest_id="periodic-v1",
    )
    matched_body = copy.deepcopy(actual_body)
    object.__setattr__(matched_body, "factory_sha", "2" * 64)
    kernels = {"actual": actual_kernel, "matched_ablated": matched_kernel}
    supports = {
        "actual": ((-1,), (0,), (1,)),
        "matched_ablated": ((0,), (1,)),
    }

    def fresh_factory(role: str):
        body = actual_body if role == "actual" else matched_body
        return support._FakeLiveFactory(
            copy.deepcopy(body),
            role,
            kernels[role],
            supports[role],
        )

    actual_binding = support._binding(
        parent_sha=parent_sha,
        role="actual",
        factory=actual_body,
        stencil_support=supports["actual"],
    )
    matched_binding = support._binding(
        parent_sha=parent_sha,
        role="matched_ablated",
        factory=matched_body,
        stencil_support=supports["matched_ablated"],
    )
    response = support._FakeResponseContract("5" * 64)
    scenario = support._FakeScenarioAuthority(response, "4" * 64)
    application = support._FakeApplicationAuthority(
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        state_shape=(20, 8),
        spatial_shape=(8,),
        target_spec_sha="8" * 64,
        application_authority_sha="3" * 64,
    )
    basis = support._FakeBasisContract(
        state_schema_id=C19_STATE_SCHEMA_ID,
        channel_order=C19_CHANNEL_ORDER,
        state_shape=(20, 8),
        spatial_shape=(8,),
        basis_contract_sha="6" * 64,
    )
    pair = support._FakePairSnapshot(
        actual_factory=actual_body,
        matched_ablated_factory=matched_body,
        actual_factory_sha=actual_body.factory_sha,
        matched_ablated_factory_sha=matched_body.factory_sha,
        snapshot_sha="7" * 64,
    )
    body = support._FakeMaterializationBody(
        materialization_schema_version=("v3m0.application-scenario-materialization.v3"),
        permit=support._FakePermit(
            parent_sha,
            support._FakeCalibration(
                parent_sha,
                tuple(support._FakeCalibrationReplayRef(parent_sha) for _ in range(3)),
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
    materialization = support._FakeVerifiedMaterializationV3(parent, body)
    calls = SimpleNamespace(materialization=[], views=[], factories=[])

    def require_materialization(observed_parent, observed_materialization):
        calls.materialization.append((observed_parent, observed_materialization))
        if type(observed_parent) is not support._FakeParentV3:
            raise TypeError("exact live Parent-v3 required")
        if observed_parent is not parent:
            raise ApplicationMaterializationV3Failure(
                "CROSS_PARENT_ROOT",
                "Parent identity differs from the bound fixture",
            )
        if type(observed_materialization) is not (
            support._FakeVerifiedMaterializationV3
        ):
            raise TypeError("exact live B2 materialization required")
        if observed_materialization is not materialization:
            raise ApplicationMaterializationV3Failure(
                "PERMIT_INVALID",
                "equal-copy or foreign materialization is not live",
            )
        if observed_materialization.parent is not observed_parent:
            raise ApplicationMaterializationV3Failure(
                "CROSS_PARENT_ROOT",
                "materialization belongs to another Parent identity",
            )
        observed_body = observed_materialization.materialization
        if observed_body != body:
            raise ApplicationMaterializationV3Failure(
                "PERMIT_INVALID",
                "materialization body drifted",
            )
        actual = fresh_factory("actual")
        matched = fresh_factory("matched_ablated")
        calls.factories.append((actual, matched))
        view = SimpleNamespace(
            materialization=copy.deepcopy(observed_body),
            actual_factory=actual,
            matched_ablated_factory=matched,
        )
        calls.views.append(view)
        return view

    def reverify_factory(factory):
        if type(factory) is not support._FakeLiveFactory:
            raise TypeError("exact live B2 child factory required")
        return SimpleNamespace(
            factory=copy.deepcopy(factory.factory),
            role=factory.role,
        )

    def materialization_payload(value):
        if type(value) is not support._FakeMaterializationBody:
            raise TypeError("exact fake B2 materialization body required")
        return support._body_payload(value, "materialization_sha")

    def binding_payload(value):
        if type(value) is not support._FakeFactoryBinding:
            raise TypeError("exact fake B2 branch binding required")
        return support._body_payload(value, "binding_sha")

    monkeypatch.setattr(
        facade,
        "ApplicationMaterializationV3Failure",
        ApplicationMaterializationV3Failure,
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "ApplicationScenarioMaterializationV3",
        support._FakeMaterializationBody,
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "FactoryBranchBindingV3",
        support._FakeFactoryBinding,
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "VerifiedV3M0ApplicationScenarioMaterializationV3",
        support._FakeVerifiedMaterializationV3,
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "VerifiedFactory",
        support._FakeLiveFactory,
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        require_materialization,
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "_reverify_verified_factory",
        reverify_factory,
        raising=False,
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
    owner_payload = facade._make_parent_v3_application_prestructure_payload_api(
        facade._parent_v3_application_prestructure_payload_impl,
        body_type=facade.ParentV3ApplicationPrestructure,
        record_validator=facade._exact_record,
        binding_payload_builder=binding_payload,
        tensor_payload_builder=facade.frozen_tensor_payload,
        nested_wire_builder=facade._wire_tree,
    )
    graph = facade._make_parent_v3_application_prestructure_graph(
        facade._ISSUANCE_TOKEN
    )
    return SimpleNamespace(
        facade=facade,
        graph=graph,
        parent=parent,
        materialization=materialization,
        materialization_body=body,
        actual_body=actual_body,
        matched_body=matched_body,
        actual_binding=actual_binding,
        matched_binding=matched_binding,
        calls=calls,
        owner_payload=owner_payload,
    )


def _assert_rejected(callable_):
    with pytest.raises((AttributeError, RuntimeError, TypeError, ValueError)):
        callable_()


def _direct_rulespace_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            imported.add(f"rulespace_v3.{node.module}")
        elif isinstance(node, ast.Import):
            imported.update(
                alias.name
                for alias in node.names
                if alias.name.startswith("rulespace_v3.")
            )
    return imported


def test_owner_exact_record_private_api_and_surface() -> None:
    facade = _module()

    assert [item.name for item in fields(facade.ParentV3ApplicationPrestructure)] == [
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
    assert [
        item.name
        for item in fields(facade._VerifiedParentV3ApplicationPrestructureView)
    ] == [
        "prestructure",
        "parent",
        "materialization",
        "factory",
        "factory_binding",
    ]
    assert tuple(
        inspect.signature(facade._issue_parent_v3_application_prestructure).parameters
    ) == ("parent", "materialization", "factory_role")
    assert tuple(
        inspect.signature(facade._verify_parent_v3_application_prestructure).parameters
    ) == ("prestructure", "parent", "materialization")
    assert tuple(
        inspect.signature(
            facade._reverify_verified_parent_v3_application_prestructure
        ).parameters
    ) == ("prestructure",)
    assert tuple(
        inspect.signature(facade.parent_v3_application_prestructure_payload).parameters
    ) == ("prestructure",)
    assert isinstance(
        facade.VerifiedParentV3ApplicationPrestructure.prestructure,
        property,
    )
    assert tuple(facade.__all__) == (
        "ParentV3ApplicationPrestructure",
        "parent_v3_application_prestructure_payload",
    )
    assert not {
        "VerifiedParentV3ApplicationPrestructure",
        "_issue_parent_v3_application_prestructure",
        "_verify_parent_v3_application_prestructure",
        "_reverify_verified_parent_v3_application_prestructure",
    } & set(facade.__all__)
    with pytest.raises(TypeError):
        facade.VerifiedParentV3ApplicationPrestructure()


@pytest.mark.parametrize("factory_role", ("actual", "matched_ablated"))
def test_owner_issues_and_raw_verifies_exact_full_b2_branch(
    monkeypatch: pytest.MonkeyPatch,
    factory_role: str,
) -> None:
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.factory import frozen_tensor_array

    fixture = _fixture(monkeypatch)
    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        factory_role,
    )
    with pytest.raises(AttributeError):
        capability.prestructure = object()
    assert weakref.ref(capability)() is capability
    raw = capability.prestructure
    expected_binding = (
        fixture.actual_binding if factory_role == "actual" else fixture.matched_binding
    )

    assert type(capability) is (fixture.facade.VerifiedParentV3ApplicationPrestructure)
    assert type(raw) is fixture.facade.ParentV3ApplicationPrestructure
    assert raw.prestructure_schema_version == (
        "v3m0.parent-v3-application-prestructure.v1"
    )
    assert raw.parent_freeze_v3_sha == "a" * 64
    assert raw.permit_sha == "b" * 64
    assert raw.materialization_sha == "9" * 64
    assert raw.current_application_authority_v3_sha == "3" * 64
    assert raw.current_scenario_authority_v3_sha == "4" * 64
    assert raw.current_scenario_response_contract_v3_sha == "5" * 64
    assert raw.factory_binding == expected_binding
    assert raw.factory_sha == expected_binding.factory.factory_sha
    assert raw.factory_role == factory_role
    assert raw.ablation_pair_snapshot == (
        fixture.materialization_body.ablation_pair_snapshot
    )
    assert raw.basis_contract == fixture.materialization_body.basis_contract
    assert raw.evidence_lane == "synthetic-classical"
    assert raw.target_spec_sha == "8" * 64
    assert raw.state_schema_id == C19_STATE_SCHEMA_ID
    assert raw.channel_order == C19_CHANNEL_ORDER
    assert raw.canonical_channel_pairs == C19_CHANNEL_PAIRS
    assert raw.fourier_adjoint_convention_id == "minus-k-transpose-v1"
    assert raw.reality_convention_id == "real-kernel-positive-zero-v1"
    np.testing.assert_array_equal(
        frozen_tensor_array(raw.structure_form),
        support._canonical_block_j(),
    )
    assert raw.prestructure_authority_sha == canonical_sha(fixture.owner_payload(raw))

    issued_view = fixture.graph.reverify(capability)
    assert issued_view.prestructure == raw
    assert issued_view.parent is fixture.parent
    assert issued_view.materialization is fixture.materialization
    assert issued_view.factory_binding == expected_binding
    assert issued_view.factory.factory == expected_binding.factory
    assert issued_view.factory.role == factory_role

    replayed = fixture.graph.verify(
        raw,
        fixture.parent,
        fixture.materialization,
    )
    assert replayed is not capability
    assert replayed.prestructure == raw
    replayed_view = fixture.graph.reverify(replayed)
    assert replayed_view.parent is fixture.parent
    assert replayed_view.materialization is fixture.materialization
    assert replayed_view.prestructure == raw
    assert all(
        parent is fixture.parent and materialization is fixture.materialization
        for parent, materialization in fixture.calls.materialization
    )


def test_owner_accepts_fresh_b2_children_by_body_binding_role_and_sha_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch)
    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    first = fixture.graph.reverify(capability)
    second = fixture.graph.reverify(capability)
    raw_verified = fixture.graph.verify(
        capability.prestructure,
        fixture.parent,
        fixture.materialization,
    )
    third = fixture.graph.reverify(raw_verified)

    assert first.factory is not second.factory
    assert second.factory is not third.factory
    assert first.factory.factory == second.factory.factory == third.factory.factory
    assert first.factory.factory == fixture.actual_binding.factory
    assert first.factory_binding == second.factory_binding == third.factory_binding
    assert first.factory_binding == fixture.actual_binding
    assert first.factory.role == second.factory.role == third.factory.role == "actual"
    assert first.factory.factory.factory_sha == fixture.actual_body.factory_sha
    assert first.parent is second.parent is third.parent is fixture.parent
    assert (
        first.materialization
        is second.materialization
        is third.materialization
        is fixture.materialization
    )
    assert first.prestructure == second.prestructure == capability.prestructure
    assert len({id(pair[0]) for pair in fixture.calls.factories}) > 1


def test_owner_rejects_raw_identity_forged_dead_cross_graph_and_cross_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch)
    capability = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    raw = capability.prestructure

    _assert_rejected(
        lambda: fixture.graph.verify(
            raw,
            copy.copy(fixture.parent),
            fixture.materialization,
        )
    )
    equal_copy = support._FakeVerifiedMaterializationV3(
        fixture.parent,
        fixture.materialization_body,
    )
    _assert_rejected(lambda: fixture.graph.verify(raw, fixture.parent, equal_copy))
    _assert_rejected(lambda: fixture.graph.verify(raw))

    forged = object.__new__(fixture.facade.VerifiedParentV3ApplicationPrestructure)
    _assert_rejected(lambda: fixture.graph.reverify(forged))
    other_graph = fixture.facade._make_parent_v3_application_prestructure_graph(
        fixture.facade._ISSUANCE_TOKEN
    )
    _assert_rejected(lambda: other_graph.reverify(capability))

    seal_tampered = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "matched_ablated",
    )
    object.__setattr__(
        seal_tampered,
        "_VerifiedParentV3ApplicationPrestructure__authority_seal",
        "0" * 64,
    )
    _assert_rejected(lambda: fixture.graph.reverify(seal_tampered))

    body_tampered = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "matched_ablated",
    )
    hostile_live_body = copy.deepcopy(body_tampered.prestructure)
    object.__setattr__(hostile_live_body, "target_spec_sha", "f" * 64)
    object.__setattr__(
        body_tampered,
        "_VerifiedParentV3ApplicationPrestructure__prestructure",
        hostile_live_body,
    )
    _assert_rejected(lambda: fixture.graph.reverify(body_tampered))

    hostile = copy.deepcopy(raw)
    object.__setattr__(hostile, "target_spec_sha", "f" * 64)
    object.__setattr__(hostile, "prestructure_authority_sha", "0" * 64)
    try:
        hostile_sha = canonical_sha(fixture.owner_payload(hostile))
    except (TypeError, ValueError):
        pass
    else:
        object.__setattr__(hostile, "prestructure_authority_sha", hostile_sha)
        _assert_rejected(
            lambda: fixture.graph.verify(
                hostile,
                fixture.parent,
                fixture.materialization,
            )
        )

    doomed = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "matched_ablated",
    )
    reference = weakref.ref(doomed)
    del doomed
    gc.collect()
    assert reference() is None


def test_owner_rejects_unknown_and_subclassed_recursive_wires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch)

    for nested_field in ("ablation_pair_snapshot", "basis_contract"):
        raw = fixture.graph.issue(
            fixture.parent,
            fixture.materialization,
            "actual",
        ).prestructure
        object.__setattr__(
            getattr(raw, nested_field),
            "unknown_recursive_field",
            "forged",
        )
        _assert_rejected(
            lambda raw=raw: fixture.graph.verify(
                raw,
                fixture.parent,
                fixture.materialization,
            )
        )

    def hostile_subclass(value):
        class Hostile(type(value)):
            def __eq__(self, other):
                del other
                return True

            def __ne__(self, other):
                del other
                return False

        return Hostile(
            **{
                item.name: copy.deepcopy(getattr(value, item.name))
                for item in fields(value)
            }
        )

    raw = fixture.graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    ).prestructure
    hostile_pair = hostile_subclass(raw.ablation_pair_snapshot)
    hostile_basis = hostile_subclass(raw.basis_contract)
    hostile_factory = hostile_subclass(raw.ablation_pair_snapshot.actual_factory)
    nested_factory_pair = replace(
        raw.ablation_pair_snapshot,
        actual_factory=hostile_factory,
    )
    for changes in (
        {"ablation_pair_snapshot": hostile_pair},
        {"basis_contract": hostile_basis},
        {"ablation_pair_snapshot": nested_factory_pair},
    ):
        provisional = replace(
            raw,
            **changes,
            prestructure_authority_sha="0" * 64,
        )
        resigned = replace(
            provisional,
            prestructure_authority_sha=canonical_sha(
                fixture.owner_payload(provisional)
            ),
        )
        _assert_rejected(
            lambda resigned=resigned: fixture.graph.verify(
                resigned,
                fixture.parent,
                fixture.materialization,
            )
        )


def test_owner_graph_and_private_apis_capture_their_own_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch)
    facade = fixture.facade
    graph = fixture.graph
    capability = graph.issue(
        fixture.parent,
        fixture.materialization,
        "actual",
    )
    raw = capability.prestructure
    baseline_payload = fixture.owner_payload(raw)
    expected_record_type = facade.ParentV3ApplicationPrestructure
    expected_wrapper_type = facade.VerifiedParentV3ApplicationPrestructure
    expected_view_type = facade._VerifiedParentV3ApplicationPrestructureView

    def redirected(*_args, **_kwargs):
        raise AssertionError("post-freeze owner global redirect was consulted")

    for name in (
        "ApplicationScenarioMaterializationV3",
        "FactoryBranchBindingV3",
        "VerifiedV3M0ApplicationScenarioMaterializationV3",
        "VerifiedFactory",
        "_require_v3m0_application_scenario_materialization_v3_for_parent",
        "_reverify_verified_factory",
        "application_scenario_materialization_v3_payload",
        "factory_branch_binding_v3_payload",
        "canonical_sha",
        "freeze_complex_tensor",
        "_wire_tree",
        "_parent_v3_application_prestructure_payload_impl",
        "dataclass_fields",
        "is_dataclass",
        "Enum",
        "SimpleNamespace",
        "ParentV3ApplicationPrestructure",
        "VerifiedParentV3ApplicationPrestructure",
        "_VerifiedParentV3ApplicationPrestructureView",
        "_ParentV3ApplicationPrestructureAuthority",
    ):
        monkeypatch.setattr(facade, name, redirected, raising=False)
    monkeypatch.setattr(
        facade,
        "PARENT_V3_APPLICATION_PRESTRUCTURE_SCHEMA_VERSION",
        "redirected-schema",
        raising=False,
    )
    monkeypatch.setattr(
        facade,
        "weakref",
        SimpleNamespace(ref=redirected),
        raising=False,
    )

    assert fixture.owner_payload(raw) == baseline_payload
    replayed = graph.verify(raw, fixture.parent, fixture.materialization)
    view = graph.reverify(replayed)
    assert type(replayed) is expected_wrapper_type
    assert type(view) is expected_view_type
    assert type(view.prestructure) is expected_record_type
    assert view.prestructure == raw

    production_graph = facade._PRODUCTION_GRAPH
    bindings = (
        (
            facade._issue_parent_v3_application_prestructure,
            production_graph.issue,
        ),
        (
            facade._verify_parent_v3_application_prestructure,
            production_graph.verify,
        ),
        (
            facade._reverify_verified_parent_v3_application_prestructure,
            production_graph.reverify,
        ),
    )
    for api, method in bindings:
        reachable = support._closure_reachable_objects(api)
        assert api == method or method in reachable
        if inspect.isfunction(api):
            assert "_PRODUCTION_GRAPH" not in api.__code__.co_names

    before = tuple(
        tuple(id(item) for item in support._closure_reachable_objects(api))
        for api, _method in bindings
    )

    monkeypatch.setattr(
        facade,
        "_PRODUCTION_GRAPH",
        SimpleNamespace(
            issue=redirected,
            verify=redirected,
            reverify=redirected,
        ),
    )
    after = tuple(
        tuple(id(item) for item in support._closure_reachable_objects(api))
        for api, _method in bindings
    )
    assert after == before


def test_owner_static_import_dag_has_no_legacy_or_transition_back_edge() -> None:
    path = REPO_ROOT / "rulespace_v3" / "parent_v3_application_prestructure.py"
    assert path.is_file()
    assert _direct_rulespace_imports(path) == {
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.evidence",
        "rulespace_v3.factory",
    }
