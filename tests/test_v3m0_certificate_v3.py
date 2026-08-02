"""Strict B6 contracts for the Parent-v3 dynamics certificate authority."""

from __future__ import annotations

import ast
import builtins
import copy
from dataclasses import dataclass, fields, replace
import functools
import gc
import inspect
from types import FunctionType, SimpleNamespace
from pathlib import Path
import sys
import threading
from typing import get_type_hints

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _recursive_container_reader_template():
    return _FREEZER_TEST_CARRIER, _FREEZER_TEST_REGISTRY  # noqa: F821


@dataclass(frozen=True)
class _ParentBody:
    parent_freeze_v3_sha: str


class _Parent:
    def __init__(self, body: _ParentBody) -> None:
        self.body = body


class HostileValueError(ValueError):
    def __init__(self, calls: list[str]) -> None:
        super().__init__("untrusted exception detail")
        self._calls = calls

    def __str__(self) -> str:
        self._calls.append("hostile.__str__")
        raise RuntimeError("hostile exception formatting escaped")


@dataclass(frozen=True)
class _FactoryBody:
    factory_sha: str


class _Factory:
    def __init__(self, body: _FactoryBody, role: str) -> None:
        self.factory = body
        self.role = role


@dataclass(frozen=True)
class _Binding:
    parent_freeze_v3_sha: str
    branch: str
    factory: _FactoryBody
    binding_sha: str


@dataclass(frozen=True)
class _Permit:
    parent_freeze_v3_sha: str


@dataclass(frozen=True)
class _MetricProtocol:
    protocol_sha: str
    state_metric: str


@dataclass(frozen=True)
class _Response:
    metric_support_derivation: _MetricProtocol


@dataclass(frozen=True)
class _MaterializationBody:
    permit: _Permit
    current_scenario_response_contract: _Response
    actual_factory_binding: _Binding
    matched_ablated_factory_binding: _Binding
    materialization_sha: str


class _Materialization:
    pass


@dataclass(frozen=True)
class _PrestructureBody:
    parent_freeze_v3_sha: str
    materialization_sha: str
    factory_binding: _Binding
    factory_sha: str
    structure_form: str
    target_spec_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    canonical_channel_pairs: tuple[tuple[str, str], ...]
    prestructure_authority_sha: str


class _Prestructure:
    def __init__(self, body: _PrestructureBody) -> None:
        self.prestructure = body


@dataclass(frozen=True)
class _Measured:
    parent_freeze_sha: str
    prestructure_authority_sha: str
    factory_sha: str
    factory_role: str
    transition_sha: str


@dataclass(frozen=True)
class _TransitionBody:
    materialization: _MaterializationBody
    factory_binding: _Binding
    prestructure_authority: _PrestructureBody
    measured_transition: _Measured
    transition_authority_sha: str


class _Transition:
    pass


@dataclass(frozen=True)
class _MetricBody:
    parent_freeze_v3_sha: str
    application_scenario_materialization_v3_sha: str
    metric_support_protocol_sha: str
    metric_support_offsets: tuple[tuple[int, ...], ...]
    factory_sha: str
    attestation_sha: str


class _MetricAttestation:
    pass


@dataclass(frozen=True)
class _BridgeGridBody:
    materialization: _MaterializationBody
    factory_binding: _Binding
    bridge_grid: str
    grid_authority_sha: str


class _BridgeGrid:
    pass


@dataclass(frozen=True)
class _DynamicsGridBody:
    transition_authority: _TransitionBody
    metric_support_attestation: _MetricBody
    dynamics_grid: str
    grid_authority_sha: str


class _DynamicsGrid:
    pass


@dataclass(frozen=True)
class _Structure:
    structure_manifest_sha: str


@dataclass(frozen=True)
class _Reality:
    reality_certificate_sha: str


@dataclass(frozen=True)
class _MetricOrigin:
    derivation_or_preregistration_sha: str


@dataclass(frozen=True)
class _StabilityMetric:
    metric_origin: _MetricOrigin
    witness_sha: str


@dataclass(frozen=True)
class _Protocol:
    protocol_sha: str


@dataclass(frozen=True)
class _Residual:
    residual_kind: str
    raw_global_momentum_supremum_bound: float
    residual_sha: str


@dataclass(frozen=True)
class _Spectral:
    coverage_sha: str


@dataclass(frozen=True)
class _Normalized:
    normalized_metric_residual_upper: float
    audit_sha: str


@dataclass(frozen=True)
class _BridgeSpec:
    bridge_spec_sha: str


@dataclass(frozen=True)
class _BridgeAudit:
    normalized_max: float
    bridge_sha: str


@dataclass(frozen=True)
class _Power:
    drift_upper: float
    audit_sha: str


@dataclass(frozen=True)
class _Runtime:
    runtime_manifest_sha: str


@dataclass(frozen=True)
class _JordanWitness:
    witness_sha: str


def _fake_graph():
    import rulespace_v3.certificate_v3 as facade
    from rulespace_v3.evidence import canonical_sha

    parent_body = _ParentBody("a" * 64)
    parent = _Parent(parent_body)
    actual_body = _FactoryBody("b" * 64)
    matched_body = _FactoryBody("c" * 64)
    actual_binding = _Binding("a" * 64, "actual", actual_body, "d" * 64)
    matched_binding = _Binding(
        "a" * 64,
        "matched_ablated",
        matched_body,
        "e" * 64,
    )
    protocol = _MetricProtocol("f" * 64, "I20")
    materialization_body = _MaterializationBody(
        _Permit("a" * 64),
        _Response(protocol),
        actual_binding,
        matched_binding,
        "1" * 64,
    )
    materialization = _Materialization()
    prestructure_body = _PrestructureBody(
        "a" * 64,
        materialization_body.materialization_sha,
        actual_binding,
        actual_body.factory_sha,
        "J20",
        "2" * 64,
        "state.v2",
        ("q", "p"),
        (("q", "p"),),
        "3" * 64,
    )
    prestructure = _Prestructure(prestructure_body)
    measured = _Measured(
        "a" * 64,
        prestructure_body.prestructure_authority_sha,
        actual_body.factory_sha,
        "actual",
        "4" * 64,
    )
    transition_body = _TransitionBody(
        materialization_body,
        actual_binding,
        prestructure_body,
        measured,
        "5" * 64,
    )
    transition = _Transition()
    metric_body = _MetricBody(
        "a" * 64,
        materialization_body.materialization_sha,
        protocol.protocol_sha,
        ((0,),),
        actual_body.factory_sha,
        "6" * 64,
    )
    metric = _MetricAttestation()
    bridge_body = _BridgeGridBody(
        materialization_body,
        actual_binding,
        "bridge-grid",
        "7" * 64,
    )
    bridge_grid = _BridgeGrid()
    dynamics_body = _DynamicsGridBody(
        transition_body,
        metric_body,
        "dynamics-grid",
        "8" * 64,
    )
    dynamics_grid = _DynamicsGrid()

    factories = {
        "materialization": _Factory(copy.deepcopy(actual_body), "actual"),
        "transition": _Factory(copy.deepcopy(actual_body), "actual"),
        "metric": _Factory(copy.deepcopy(actual_body), "actual"),
        "bridge": _Factory(copy.deepcopy(actual_body), "actual"),
    }
    calls: list[str] = []
    mode = {"value": None}

    def parent_reader(value):
        calls.append("parent")
        if mode["value"] == "parent":
            raise ValueError("forced dead Parent")
        if mode["value"] == "parent.empty":
            raise ValueError()
        if mode["value"] == "parent.hostile":
            raise HostileValueError(calls)
        if type(value) is not _Parent:
            raise TypeError("exact Parent required")
        return copy.deepcopy(value.body)

    def materialization_requirer(observed_parent, value):
        calls.append("materialization")
        if mode["value"] == "materialization":
            raise ValueError("forced dead materialization")
        if observed_parent is not parent or value is not materialization:
            raise ValueError("materialization live identity differs")
        return SimpleNamespace(
            materialization=copy.deepcopy(materialization_body),
            actual_factory=factories["materialization"],
            matched_ablated_factory=_Factory(matched_body, "matched_ablated"),
        )

    def transition_reverifier(value):
        calls.append("transition")
        if mode["value"] == "transition":
            raise ValueError("forced dead transition")
        if value is not transition:
            raise TypeError("exact transition required")
        return SimpleNamespace(
            transition_authority=copy.deepcopy(transition_body),
            parent=parent,
            materialization=materialization,
            factory=factories["transition"],
            prestructure=prestructure,
        )

    def metric_reverifier(value):
        calls.append("metric_attestation")
        if mode["value"] == "metric_attestation":
            raise ValueError("forced dead metric")
        return SimpleNamespace(
            attestation=copy.deepcopy(metric_body),
            parent=(object() if mode["value"] == "cross_join" else parent),
            materialization=materialization,
            factory=factories["metric"],
            factory_binding=copy.deepcopy(actual_binding),
        )

    def bridge_reverifier(value):
        calls.append("bridge_grid")
        if mode["value"] == "bridge_grid":
            raise ValueError("forced dead bridge grid")
        return SimpleNamespace(
            grid_authority=copy.deepcopy(bridge_body),
            parent=parent,
            materialization=materialization,
            factory=factories["bridge"],
            factory_binding=copy.deepcopy(actual_binding),
        )

    def dynamics_reverifier(value):
        calls.append("dynamics_grid")
        if mode["value"] == "dynamics_grid":
            raise ValueError("forced dead dynamics grid")
        return SimpleNamespace(
            grid_authority=copy.deepcopy(dynamics_body),
            parent=parent,
            transition=transition,
            metric_attestation=metric,
        )

    def structure_builder(*args, **kwargs):
        del args, kwargs
        calls.append("reality.structure")
        if mode["value"] == "reality":
            raise ValueError("forced reality failure")
        return _Structure("9" * 64)

    def reality_builder(*args):
        del args
        calls.append("reality")
        return _Reality("0" * 64)

    def metric_builder(*args, **kwargs):
        del args, kwargs
        calls.append("metric")
        metric_call_count = calls.count("metric")
        if mode["value"] == "metric.prebuild" and metric_call_count == 1:
            raise ValueError("forced metric dependency preconstruction failure")
        if mode["value"] == "metric.builder" and metric_call_count == 2:
            raise ValueError("forced metric reconstruction failure")
        if mode["value"] == "metric.origin" and metric_call_count == 2:
            return _StabilityMetric(_MetricOrigin("e" * 64), "1" * 64)
        if mode["value"] == "metric.mismatch" and metric_call_count == 2:
            return _StabilityMetric(_MetricOrigin(protocol.protocol_sha), "e" * 64)
        return _StabilityMetric(_MetricOrigin(protocol.protocol_sha), "1" * 64)

    def laurent_preflight(*args):
        del args
        calls.append("laurent")
        if mode["value"] == "laurent":
            raise ValueError("forced Laurent cap")

    def instability_builder(*args):
        del args
        calls.append("jordan")
        return _JordanWitness("2" * 64) if mode["value"] == "jordan" else None

    def instability_verifier(value):
        calls.append("jordan.verify")
        return value

    def protocol_builder():
        calls.append("fp64.build")
        return _Protocol("3" * 64)

    def protocol_verifier(value):
        calls.append("fp64.verify")
        return value

    def residual_builder(*args, kind, **kwargs):
        del args, kwargs
        calls.append(kind)
        if mode["value"] == kind:
            raise ValueError(f"forced {kind} failure")
        upper = 2.0e-12 if mode["value"] == f"{kind}.gate" else 0.0
        return _Residual(kind, upper, ("4" if kind[0] == "c" else "5") * 64)

    def spectral_builder(*args, **kwargs):
        del args, kwargs
        calls.append("spectral")
        if mode["value"] == "spectral":
            raise ValueError("forced spectral failure")
        return _Spectral("6" * 64)

    def normalized_builder(*args):
        del args
        calls.append("normalized")
        if mode["value"] == "normalized":
            raise ValueError("forced normalized failure")
        upper = 2.0e-12 if mode["value"] == "normalized.gate" else 0.0
        return _Normalized(upper, "7" * 64)

    def bridge_spec_builder(*args, **kwargs):
        del args, kwargs
        calls.append("bridge.spec")
        return _BridgeSpec("8" * 64)

    def bridge_audit_builder(*args):
        del args
        calls.append("bridge.audit")
        if mode["value"] == "bridge":
            raise ValueError("forced bridge execution failure")
        upper = 2.0e-12 if mode["value"] == "bridge.gate" else 0.0
        return _BridgeAudit(upper, "9" * 64)

    def power_builder(*args):
        del args
        calls.append("power")
        if mode["value"] == "power":
            raise ValueError("forced power failure")
        upper = 2.0e-8 if mode["value"] == "power.gate" else 0.0
        return _Power(upper, "a" * 64)

    def runtime_issuer():
        calls.append("runtime.issue")
        if mode["value"] == "runtime.issue":
            raise RuntimeError("forced runtime authority failure")
        return _Runtime("b" * 64)

    def runtime_verifier(value):
        calls.append("runtime.verify")
        if mode["value"] == "runtime_drift":
            raise ValueError("forced historical runtime drift")
        return value

    deps = facade._CertificateV3Dependencies(
        parent_type=_Parent,
        materialization_type=_Materialization,
        transition_type=_Transition,
        measured_transition_type=_Measured,
        metric_attestation_type=_MetricAttestation,
        bridge_grid_type=_BridgeGrid,
        dynamics_grid_type=_DynamicsGrid,
        parent_reader=parent_reader,
        materialization_requirer=materialization_requirer,
        transition_reverifier=transition_reverifier,
        metric_reverifier=metric_reverifier,
        bridge_grid_reverifier=bridge_reverifier,
        dynamics_grid_reverifier=dynamics_reverifier,
        factory_body_reader=lambda value: value.factory,
        factory_role_reader=lambda value: value.role,
        structure_builder=structure_builder,
        reality_builder=reality_builder,
        metric_builder=metric_builder,
        laurent_preflight=laurent_preflight,
        instability_builder=instability_builder,
        instability_verifier=instability_verifier,
        protocol_builder=protocol_builder,
        protocol_verifier=protocol_verifier,
        residual_builder=residual_builder,
        spectral_builder=spectral_builder,
        normalized_builder=normalized_builder,
        bridge_spec_builder=bridge_spec_builder,
        bridge_audit_builder=bridge_audit_builder,
        power_builder=power_builder,
        runtime_issuer=runtime_issuer,
        runtime_verifier=runtime_verifier,
        sha_builder=canonical_sha,
        clone=copy.deepcopy,
    )
    graph = facade._make_certificate_v3_graph(facade._ISSUANCE_TOKEN, deps)
    inputs = (
        parent,
        materialization,
        transition,
        metric,
        bridge_grid,
        dynamics_grid,
    )
    return facade, graph, inputs, calls, mode


def test_certificate_v3_public_wire_and_api_surface_is_frozen() -> None:
    import rulespace_v3.certificate_v3 as facade

    assert tuple(item.name for item in fields(facade.DynamicsCertificateV3)) == (
        "certificate_schema_version",
        "parent_freeze_v3",
        "materialization",
        "transition_authority",
        "metric_attestation",
        "bridge_grid_authority",
        "dynamics_grid_authority",
        "prestructure_authority",
        "structure",
        "reality",
        "stability_metric",
        "fp64_enclosure_protocol",
        "full_state_bridge_spec",
        "full_state_bridge_audit",
        "structure_residual",
        "metric_residual",
        "spectral_margins",
        "normalized_metric_residual",
        "power_drift",
        "runtime",
        "certificate_sha",
    )
    assert tuple(
        item.name for item in fields(facade.DynamicsCertificationAttemptAuditV3)
    ) == (
        "attempt_schema_version",
        "parent_freeze_v3_sha",
        "materialization_sha",
        "transition_authority_sha",
        "metric_attestation_sha",
        "bridge_grid_authority_sha",
        "dynamics_grid_authority_sha",
        "first_failure",
        "reality",
        "structure_residual",
        "metric_residual",
        "spectral_margins",
        "normalized_metric_residual",
        "full_state_bridge_audit",
        "power_drift",
        "instability_counter_witness",
        "attempt_sha",
    )
    assert tuple(
        item.name for item in fields(facade.DynamicsCertificationOutcomeV3)
    ) == (
        "status",
        "failure",
        "attempt_audit",
        "certificate",
        "outcome_sha",
    )

    from rulespace_v3.parent_freeze_v3_contracts import ParentFreezeV3Manifest

    assert get_type_hints(facade.DynamicsCertificateV3)["parent_freeze_v3"] is (
        ParentFreezeV3Manifest
    )

    public_parameters = {
        "certify_transition_dynamics_v3": (
            "parent",
            "materialization",
            "transition",
            "metric_attestation",
            "bridge_grid",
            "dynamics_grid",
        ),
        "verify_dynamics_certificate_v3": (
            "certificate",
            "parent",
            "materialization",
            "transition",
            "metric_attestation",
            "bridge_grid",
            "dynamics_grid",
        ),
        "verify_dynamics_certification_outcome_v3": (
            "outcome",
            "parent",
            "materialization",
            "transition",
            "metric_attestation",
            "bridge_grid",
            "dynamics_grid",
        ),
        "require_dynamics_certificate_v3": ("outcome",),
    }
    for name, parameters in public_parameters.items():
        assert tuple(inspect.signature(getattr(facade, name)).parameters) == parameters

    assert get_type_hints(facade.certify_transition_dynamics_v3)["return"] is (
        facade.VerifiedDynamicsCertificationOutcomeV3
    )
    assert get_type_hints(facade.verify_dynamics_certificate_v3)["return"] is (
        facade.VerifiedDynamicsCertificateV3
    )
    assert (
        get_type_hints(facade.verify_dynamics_certification_outcome_v3)["return"]
        is facade.VerifiedDynamicsCertificationOutcomeV3
    )
    assert get_type_hints(facade.require_dynamics_certificate_v3)["return"] is (
        facade.VerifiedDynamicsCertificateV3
    )

    assert {
        "DynamicsCertificateV3",
        "DynamicsCertificationAttemptAuditV3",
        "DynamicsCertificationFailure",
        "DynamicsCertificationOutcomeV3",
        "DynamicsCertificationUpstreamJoinFailure",
        "VerifiedDynamicsCertificateV3",
        "VerifiedDynamicsCertificationOutcomeV3",
        *public_parameters,
    } <= set(facade.__all__)


def test_certificate_v3_direct_import_dag_matches_v7_owner_contract() -> None:
    tree = ast.parse((REPO_ROOT / "rulespace_v3/certificate_v3.py").read_text())
    direct: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module is None:
                direct.update(f"rulespace_v3.{alias.name}" for alias in node.names)
            else:
                direct.add(f"rulespace_v3.{node.module}")

    assert {
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.transition_authority_v3",
        "rulespace_v3.parent_v3_application_prestructure",
        "rulespace_v3.metric_support_authority_v1",
        "rulespace_v3.runtime_grids_v3",
        "rulespace_v3.certificate",
        "rulespace_v3.dynamics",
        "rulespace_v3.structure",
        "rulespace_v3.metric",
        "rulespace_v3.bridge",
        "rulespace_v3.instability",
        "rulespace_v3.laurent",
        "rulespace_v3.spectral",
        "rulespace_v3.fp64_protocol",
        "rulespace_v3.runtime",
    } <= direct
    assert "rulespace_v3.prestructure" not in direct


def test_fake_live_graph_issues_recursive_success_and_preserves_v8_lineage() -> None:
    facade, graph, inputs, calls, _ = _fake_graph()

    verified = graph.certify(*inputs)

    assert type(verified) is facade.VerifiedDynamicsCertificationOutcomeV3
    assert verified.outcome.status.defined is True
    assert verified.outcome.failure is None
    certificate = graph.require_certificate(verified)
    assert type(certificate) is facade.VerifiedDynamicsCertificateV3
    assert certificate is verified.certificate
    certificate_view = graph.reverify_certificate(certificate)
    outcome_view = graph.reverify_outcome(verified)
    assert certificate_view.originating_outcome is verified
    assert outcome_view.certificate is certificate
    assert (
        outcome_view.outcome.certificate.prestructure_authority
        == outcome_view.outcome.certificate.transition_authority.prestructure_authority
    )
    assert outcome_view.parent is inputs[0]
    assert outcome_view.materialization is inputs[1]
    assert outcome_view.transition is inputs[2]
    assert outcome_view.metric_attestation is inputs[3]
    assert outcome_view.bridge_grid is inputs[4]
    assert outcome_view.dynamics_grid is inputs[5]
    assert calls[:6] == [
        "parent",
        "materialization",
        "transition",
        "metric_attestation",
        "bridge_grid",
        "dynamics_grid",
    ]
    metric_calls = tuple(
        index for index, value in enumerate(calls) if value == "metric"
    )
    assert len(metric_calls) == 2
    assert metric_calls[0] < calls.index("laurent")
    assert calls.index("canonical-structure") < metric_calls[1]


def test_runtime_authority_precedes_every_scientific_outcome() -> None:
    _, graph, inputs, calls, mode = _fake_graph()
    mode["value"] = "reality"

    verified = graph.certify(*inputs)

    assert verified.outcome.failure is not None
    assert calls.index("runtime.issue") < calls.index("reality.structure")
    assert calls.index("runtime.verify") < calls.index("reality.structure")


def test_runtime_infrastructure_failure_preempts_all_scientific_stages() -> None:
    _, graph, inputs, calls, mode = _fake_graph()
    mode["value"] = "runtime.issue"

    with pytest.raises(RuntimeError, match="runtime authority failure"):
        graph.certify(*inputs)

    assert graph.authority_counts() == (0, 0)
    assert not {
        "reality.structure",
        "reality",
        "metric",
        "laurent",
        "jordan",
        "canonical-structure",
        "stability-metric",
        "spectral",
        "normalized",
        "bridge.spec",
        "bridge.audit",
        "power",
    }.intersection(calls)


@pytest.mark.parametrize(
    "mode_value",
    ("metric.builder", "metric.origin", "metric.mismatch"),
)
def test_metric_reconstruction_failure_is_a_metric_raw_outcome_with_prefix(
    mode_value: str,
) -> None:
    facade, graph, inputs, calls, mode = _fake_graph()
    mode["value"] = mode_value

    verified = graph.certify(*inputs)
    audit = verified.outcome.attempt_audit

    assert verified.outcome.failure is (
        facade.DynamicsCertificationFailure.METRIC_RAW_UNRESOLVED
    )
    assert audit.reality is not None
    assert audit.structure_residual is not None
    assert audit.metric_residual is None
    metric_calls = tuple(
        index for index, value in enumerate(calls) if value == "metric"
    )
    assert len(metric_calls) == 2
    assert metric_calls[0] < calls.index("laurent")
    assert calls.index("laurent") < calls.index("jordan")
    assert calls.index("jordan") < calls.index("canonical-structure")
    assert calls.index("canonical-structure") < metric_calls[1]


def test_metric_dependency_preconstruction_failure_is_infrastructure() -> None:
    _, graph, inputs, calls, mode = _fake_graph()
    mode["value"] = "metric.prebuild"

    with pytest.raises(RuntimeError, match="metric dependency preconstruction"):
        graph.certify(*inputs)

    assert graph.authority_counts() == (0, 0)
    assert calls.count("metric") == 1
    assert "laurent" not in calls


def test_raw_success_outcome_and_certificate_replay_mint_fresh_joined_views() -> None:
    facade, graph, inputs, _, _ = _fake_graph()
    original = graph.certify(*inputs)
    raw_outcome = original.outcome
    raw_certificate = original.certificate.certificate

    replayed_outcome = graph.verify_outcome(raw_outcome, *inputs)
    replayed_certificate = graph.verify_certificate(raw_certificate, *inputs)

    assert replayed_outcome is not original
    assert replayed_outcome.outcome == raw_outcome
    assert graph.require_certificate(replayed_outcome).certificate == raw_certificate
    assert replayed_certificate.certificate == raw_certificate
    assert (
        graph.reverify_certificate(replayed_certificate).originating_outcome
        is not original
    )


@pytest.mark.parametrize(
    ("mode_value", "reason_id"),
    (
        ("parent", "PARENT_INVALID"),
        ("materialization", "MATERIALIZATION_INVALID"),
        ("transition", "TRANSITION_INVALID"),
        ("metric_attestation", "METRIC_ATTESTATION_INVALID"),
        ("bridge_grid", "BRIDGE_GRID_INVALID"),
        ("dynamics_grid", "DYNAMICS_GRID_INVALID"),
        ("cross_join", "CROSS_AUTHORITY_JOIN"),
    ),
)
def test_upstream_invalidity_is_a_typed_atomic_raise_without_artifact(
    mode_value: str,
    reason_id: str,
) -> None:
    facade, graph, inputs, calls, mode = _fake_graph()
    mode["value"] = mode_value

    with pytest.raises(facade.DynamicsCertificationUpstreamJoinFailure) as raised:
        graph.certify(*inputs)

    assert raised.value.reason_id == reason_id
    assert graph.authority_counts() == (0, 0)
    assert not {
        "reality.structure",
        "reality",
        "laurent",
        "jordan",
        "canonical-structure",
        "spectral",
        "bridge.audit",
        "power",
        "runtime.issue",
    }.intersection(calls)


def test_empty_upstream_exception_keeps_typed_reason_and_atomicity() -> None:
    facade, graph, inputs, _, mode = _fake_graph()
    mode["value"] = "parent.empty"

    with pytest.raises(facade.DynamicsCertificationUpstreamJoinFailure) as raised:
        graph.certify(*inputs)

    assert raised.value.reason_id == "PARENT_INVALID"
    assert raised.value.detail == "ValueError"
    assert type(raised.value.__cause__) is ValueError
    assert graph.authority_counts() == (0, 0)


def test_hostile_upstream_exception_formatting_cannot_escape_typed_failure() -> None:
    facade, graph, inputs, calls, mode = _fake_graph()
    mode["value"] = "parent.hostile"

    with pytest.raises(facade.DynamicsCertificationUpstreamJoinFailure) as raised:
        graph.certify(*inputs)

    assert raised.value.reason_id == "PARENT_INVALID"
    assert raised.value.detail == "HostileValueError"
    assert type(raised.value.__cause__) is HostileValueError
    assert "hostile.__str__" not in calls
    assert graph.authority_counts() == (0, 0)


@pytest.mark.parametrize(
    ("mode_value", "failure", "required_prefix"),
    (
        ("reality", "REALITY_INVALID", ()),
        ("laurent", "LAURENT_RESOURCE_EXCEEDED", ("reality",)),
        (
            "jordan",
            "CERTIFIED_INSTABILITY_COUNTERWITNESS",
            ("reality",),
        ),
        (
            "canonical-structure.gate",
            "STRUCTURE_RAW_UNRESOLVED",
            ("reality",),
        ),
        (
            "stability-metric",
            "METRIC_RAW_UNRESOLVED",
            ("reality", "structure_residual"),
        ),
        (
            "spectral",
            "SPECTRAL_COVERAGE_UNRESOLVED",
            ("reality", "structure_residual", "metric_residual"),
        ),
        (
            "normalized",
            "NORMALIZED_METRIC_UNRESOLVED",
            (
                "reality",
                "structure_residual",
                "metric_residual",
                "spectral_margins",
            ),
        ),
        (
            "bridge.gate",
            "FULL_STATE_BRIDGE_FAILED",
            (
                "reality",
                "structure_residual",
                "metric_residual",
                "spectral_margins",
                "normalized_metric_residual",
            ),
        ),
        (
            "power.gate",
            "POWER_DRIFT_UNRESOLVED",
            (
                "reality",
                "structure_residual",
                "metric_residual",
                "spectral_margins",
                "normalized_metric_residual",
                "full_state_bridge_audit",
            ),
        ),
    ),
)
def test_scientific_failures_follow_v7_effective_first_failure_order(
    mode_value: str,
    failure: str,
    required_prefix: tuple[str, ...],
) -> None:
    facade, graph, inputs, _, mode = _fake_graph()
    mode["value"] = mode_value

    verified = graph.certify(*inputs)
    raw = verified.outcome
    audit = raw.attempt_audit

    assert raw.status.defined is False
    assert raw.failure is getattr(facade.DynamicsCertificationFailure, failure)
    assert raw.certificate is None
    assert verified.certificate is None
    assert graph.authority_counts() == (1, 0)
    for field in required_prefix:
        assert getattr(audit, field) is not None
    if failure == "CERTIFIED_INSTABILITY_COUNTERWITNESS":
        assert audit.instability_counter_witness is not None
    else:
        assert audit.instability_counter_witness is None
    with pytest.raises(ValueError, match="successful dynamics certificate"):
        graph.require_certificate(verified)


def test_require_rejects_forged_dead_and_tampered_outcome_without_minting() -> None:
    facade, graph, inputs, _, _ = _fake_graph()
    verified = graph.certify(*inputs)
    counts = graph.authority_counts()
    forged = object.__new__(facade.VerifiedDynamicsCertificationOutcomeV3)

    with pytest.raises(ValueError):
        graph.require_certificate(forged)

    object.__setattr__(
        verified,
        "_VerifiedDynamicsCertificationOutcomeV3__seal",
        "f" * 64,
    )
    with pytest.raises(ValueError, match="drifted"):
        graph.require_certificate(verified)
    assert graph.authority_counts() == counts


def test_raw_outcome_tamper_is_rejected_after_live_join_without_registry_growth() -> (
    None
):
    _, graph, inputs, _, _ = _fake_graph()
    verified = graph.certify(*inputs)
    counts = graph.authority_counts()
    tampered = replace(verified.outcome, outcome_sha="f" * 64)

    with pytest.raises(ValueError, match="outcome_sha"):
        graph.verify_outcome(tampered, *inputs)

    assert graph.authority_counts() == counts


@pytest.mark.parametrize("mode_value", ("laurent", "jordan"))
def test_laurent_and_jordan_attempts_require_reality_prefix(
    mode_value: str,
) -> None:
    facade, graph, inputs, _, mode = _fake_graph()
    from rulespace_v3.evidence import canonical_sha

    mode["value"] = mode_value
    raw = graph.certify(*inputs).outcome
    provisional_attempt = replace(
        raw.attempt_audit,
        reality=None,
        attempt_sha="0" * 64,
    )
    bad_attempt = replace(
        provisional_attempt,
        attempt_sha=canonical_sha(
            facade.dynamics_certification_attempt_audit_v3_payload(provisional_attempt)
        ),
    )
    provisional_outcome = replace(
        raw,
        attempt_audit=bad_attempt,
        outcome_sha="0" * 64,
    )
    bad_outcome = replace(
        provisional_outcome,
        outcome_sha=canonical_sha(
            facade.dynamics_certification_outcome_v3_payload(provisional_outcome)
        ),
    )

    with pytest.raises(ValueError, match="completed prefix"):
        facade._validate_outcome(bad_outcome)


def test_require_freshly_reverifies_embedded_runtime_manifest() -> None:
    _, graph, inputs, _, mode = _fake_graph()
    verified = graph.certify(*inputs)
    mode["value"] = "runtime_drift"

    with pytest.raises(ValueError, match="historical runtime drift"):
        graph.require_certificate(verified)


def test_outcome_certificate_cycle_is_collectable_and_registry_entries_die() -> None:
    _, graph, inputs, _, _ = _fake_graph()
    verified = graph.certify(*inputs)
    certificate = graph.require_certificate(verified)
    assert graph.authority_counts() == (1, 1)

    del verified
    del certificate
    gc.collect()

    assert graph.authority_counts() == (0, 0)


def test_saved_graph_ignores_owner_global_record_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade, graph, inputs, _, _ = _fake_graph()
    saved_certify = graph.certify

    class _RedirectedCertificate:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs
            raise AssertionError("owner global redirect reached saved graph")

    monkeypatch.setattr(facade, "DynamicsCertificateV3", _RedirectedCertificate)

    verified = saved_certify(*inputs)
    assert verified.outcome.status.defined is True


def test_production_graph_has_transitively_private_project_function_globals() -> None:
    from rulespace_v3 import certificate_v3 as facade

    pending = list(facade._PRODUCTION_GRAPH[:6])
    observed: set[int] = set()
    project_functions = []
    while pending:
        function = pending.pop()
        if not inspect.isfunction(function) or id(function) in observed:
            continue
        observed.add(id(function))
        if function.__module__.startswith("rulespace_v3."):
            project_functions.append(function)
        if function.__closure__ is not None:
            pending.extend(cell.cell_contents for cell in function.__closure__)
        if function.__defaults__ is not None:
            pending.extend(function.__defaults__)
        if function.__kwdefaults__ is not None:
            pending.extend(function.__kwdefaults__.values())

    assert project_functions
    for function in project_functions:
        assert function.__globals__["__builtins__"] is not builtins.__dict__


def test_production_graph_preserves_every_reachable_live_authority_registry() -> None:
    from rulespace_v3 import certificate_v3 as facade

    rlock_type = type(threading.RLock())

    def is_authority_state(name: str, value: object) -> bool:
        normalized = name.lstrip("_")
        registry_name = normalized in (
            "registry",
            "bindings",
            "records",
            "authorities",
        ) or normalized.endswith(("_registry", "_bindings", "_records", "_authorities"))
        lock_name = name == "lock" or name.endswith("_lock")
        return (registry_name and type(value) is dict) or (
            lock_name and type(value) is rlock_type
        )

    def reachable_functions(roots):
        pending = list(roots)
        observed: set[int] = set()
        while pending:
            value = pending.pop()
            if isinstance(value, functools.partial):
                pending.append(value.func)
                pending.extend(value.args)
                pending.extend((value.keywords or {}).values())
                continue
            if not inspect.isfunction(value) or id(value) in observed:
                continue
            observed.add(id(value))
            if not value.__module__.startswith("rulespace_v3."):
                continue
            yield value
            if value.__closure__ is not None:
                pending.extend(cell.cell_contents for cell in value.__closure__)
            if value.__defaults__ is not None:
                pending.extend(value.__defaults__)
            if value.__kwdefaults__ is not None:
                pending.extend(value.__kwdefaults__.values())
            for name in value.__code__.co_names:
                referenced = value.__globals__.get(name)
                if inspect.isfunction(referenced) or isinstance(
                    referenced,
                    functools.partial,
                ):
                    pending.append(referenced)

    def authority_state(functions):
        result: dict[tuple[object, str], set[int]] = {}
        objects: dict[int, object] = {}
        for function in functions:
            if function.__closure__ is not None:
                for name, cell in zip(
                    function.__code__.co_freevars,
                    function.__closure__,
                ):
                    value = cell.cell_contents
                    if is_authority_state(name, value):
                        result.setdefault((function.__code__, name), set()).add(
                            id(value)
                        )
                        objects[id(value)] = value
            owner_globals = vars(sys.modules[function.__module__])
            for name in function.__code__.co_names:
                if name not in function.__globals__ or name not in owner_globals:
                    continue
                value = function.__globals__[name]
                if is_authority_state(name, owner_globals[name]):
                    result.setdefault((function.__code__, name), set()).add(id(value))
                    objects[id(value)] = value
        return result, objects

    dependency_roots = tuple(
        getattr(facade._PRODUCTION_DEPENDENCIES, field.name)
        for field in fields(facade._CertificateV3Dependencies)
        if callable(getattr(facade._PRODUCTION_DEPENDENCIES, field.name))
    )
    live_state, live_objects = authority_state(reachable_functions(dependency_roots))
    frozen_state, frozen_objects = authority_state(
        reachable_functions(facade._PRODUCTION_GRAPH[:6])
    )

    assert live_state
    for key, live_identities in live_state.items():
        assert live_identities <= frozen_state.get(key, set()), key

    from rulespace_v3 import parent_authority_v3

    parent_code = parent_authority_v3._reverify_parent_v3.__code__
    parent_registry_key = (parent_code, "_registry")
    parent_lock_key = (parent_code, "_registry_lock")
    assert id(parent_authority_v3._registry) in frozen_state[parent_registry_key]
    assert id(parent_authority_v3._registry_lock) in frozen_state[parent_lock_key]

    marker = object()
    marker_key = -id(marker)
    with parent_authority_v3._registry_lock:
        parent_authority_v3._registry[marker_key] = marker
        try:
            assert parent_authority_v3._registry
            for identity in frozen_state[parent_registry_key]:
                assert frozen_objects[identity][marker_key] is marker
        finally:
            parent_authority_v3._registry.pop(marker_key, None)

    assert id(parent_authority_v3._registry) in live_objects


def test_transitive_freezer_selectively_handles_recursive_containers() -> None:
    from rulespace_v3 import certificate_v3 as facade

    private_globals = {
        "__builtins__": builtins.__dict__,
        "__name__": "rulespace_v3.certificate_v3",
    }
    reader = FunctionType(
        _recursive_container_reader_template.__code__,
        private_globals,
        "reader",
    )
    reader.__module__ = "rulespace_v3.certificate_v3"
    carrier: dict[str, object] = {}
    carrier["self"] = carrier
    carrier["reader"] = reader
    registry: dict[str, object] = {}
    registry["self"] = registry
    private_globals["_FREEZER_TEST_CARRIER"] = carrier
    private_globals["_FREEZER_TEST_REGISTRY"] = registry

    graph = facade._CertificateV3Graph(*(reader for _ in range(7)))
    frozen = facade._freeze_certificate_v3_graph(graph)
    frozen_carrier = frozen.certify.__globals__["_FREEZER_TEST_CARRIER"]

    assert frozen_carrier is not carrier
    assert frozen_carrier["self"] is frozen_carrier
    assert frozen_carrier["reader"] is frozen.certify
    assert frozen.certify.__globals__["_FREEZER_TEST_REGISTRY"] is registry
    assert registry["self"] is registry


def test_transitive_freezer_selectively_freezes_project_module_in_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3 import certificate_v3 as facade
    from rulespace_v3 import evidence

    def make_reader(owner):
        def reader(payload):
            return owner.canonical_sha(payload)

        return reader

    reader = make_reader(evidence)
    graph = facade._CertificateV3Graph(*(reader for _ in range(7)))
    frozen = facade._freeze_certificate_v3_graph(graph)
    payload = {"closure": "project-module"}
    expected = evidence.canonical_sha(payload)

    monkeypatch.setattr(evidence, "canonical_sha", lambda value: "REDIRECTED")

    assert frozen.certify(payload) == expected


def test_transitive_freezer_rejects_mixed_immutable_cycle_without_alias_leak() -> None:
    from rulespace_v3 import certificate_v3 as facade

    private_globals = {
        "__builtins__": builtins.__dict__,
        "__name__": "rulespace_v3.certificate_v3",
    }
    reader = FunctionType(
        _recursive_container_reader_template.__code__,
        private_globals,
        "reader",
    )
    reader.__module__ = "rulespace_v3.certificate_v3"
    recursive_list: list[object] = []
    recursive_tuple = (recursive_list, reader)
    recursive_list.append(recursive_tuple)
    registry: dict[str, object] = {}
    private_globals["_FREEZER_TEST_CARRIER"] = recursive_tuple
    private_globals["_FREEZER_TEST_REGISTRY"] = registry
    graph = facade._CertificateV3Graph(*(reader for _ in range(7)))

    with pytest.raises(ValueError, match="immutable container cycle"):
        facade._freeze_certificate_v3_graph(graph)

    alias_globals = {
        "__builtins__": builtins.__dict__,
        "__name__": "rulespace_v3.certificate_v3",
    }
    alias_reader = FunctionType(
        _recursive_container_reader_template.__code__,
        alias_globals,
        "alias_reader",
    )
    alias_reader.__module__ = "rulespace_v3.certificate_v3"
    shared = [alias_reader]
    alias_carrier = (shared, shared)
    alias_registry: dict[str, object] = {}
    alias_globals["_FREEZER_TEST_CARRIER"] = alias_carrier
    alias_globals["_FREEZER_TEST_REGISTRY"] = alias_registry
    alias_graph = facade._CertificateV3Graph(*(alias_reader for _ in range(7)))

    frozen = facade._freeze_certificate_v3_graph(alias_graph)
    frozen_carrier = frozen.certify.__globals__["_FREEZER_TEST_CARRIER"]
    assert frozen_carrier is not alias_carrier
    assert frozen_carrier[0] is frozen_carrier[1]
    assert frozen_carrier[0] is not shared
    assert frozen_carrier[0][0] is frozen.certify
    assert frozen.certify.__globals__["__builtins__"] is not builtins.__dict__
    assert frozen.certify.__globals__["_FREEZER_TEST_REGISTRY"] is alias_registry


def test_transitive_freezer_rebuilds_cyclic_partial_without_original_alias() -> None:
    from rulespace_v3 import certificate_v3 as facade

    private_globals = {
        "__builtins__": builtins.__dict__,
        "__name__": "rulespace_v3.certificate_v3",
    }
    reader = FunctionType(
        _recursive_container_reader_template.__code__,
        private_globals,
        "reader",
    )
    reader.__module__ = "rulespace_v3.certificate_v3"
    cyclic_partial = functools.partial(reader)
    cyclic_partial.keywords["self"] = cyclic_partial
    registry: dict[str, object] = {}
    private_globals["_FREEZER_TEST_CARRIER"] = cyclic_partial
    private_globals["_FREEZER_TEST_REGISTRY"] = registry
    graph = facade._CertificateV3Graph(*(reader for _ in range(7)))

    frozen = facade._freeze_certificate_v3_graph(graph)
    frozen_partial = frozen.certify.__globals__["_FREEZER_TEST_CARRIER"]

    assert frozen_partial is not cyclic_partial
    assert frozen_partial.keywords["self"] is frozen_partial
    assert frozen_partial.func is frozen.certify
    assert frozen_partial.func.__globals__["__builtins__"] is not builtins.__dict__
    assert frozen.certify.__globals__["_FREEZER_TEST_REGISTRY"] is registry


def test_saved_graph_ignores_exact_record_dynamic_method_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade, graph, inputs, _, _ = _fake_graph()
    saved_certify = graph.certify

    def redirected_post_init(self) -> None:
        del self
        raise AssertionError("dynamic exact-record method redirect reached graph")

    for record_type in (
        facade.DynamicsCertificationAttemptAuditV3,
        facade.DynamicsCertificationOutcomeV3,
        facade.DynamicsCertificateV3,
        facade.BlockStatus,
    ):
        monkeypatch.setattr(record_type, "__post_init__", redirected_post_init)

    verified = saved_certify(*inputs)
    assert verified.outcome.status.defined is True
