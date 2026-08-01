"""Parent-v3 C19 metric signed-support authority.

The public attestation is inert evidence.  The opaque wrapper is issued only
after the exact live Parent-v3 materialization has been replayed through the
B2 owner seam and the frozen C19 identity-metric protocol has been verified.
"""

from __future__ import annotations

import copy
import re
import threading
import weakref
from dataclasses import dataclass, fields as dataclass_fields, replace
from typing import Literal, NamedTuple

from .application_materialization_v3 import (
    ApplicationMaterializationV3Failure,
    VerifiedV3M0ApplicationScenarioMaterializationV3,
    _require_v3m0_application_scenario_materialization_v3_for_parent,
)
from .metric import canonical_sha, metric_support_payload
from .parent_v3_contracts import (
    MetricSupportDerivationProtocolV1,
    verify_metric_support_derivation_protocol_v1,
)


METRIC_SIGNED_SUPPORT_ATTESTATION_V1_SCHEMA_VERSION = (
    "v3m0.metric-signed-support-attestation.v1"
)
_C19_STATE_SCHEMA_ID = "v3m0.c19-real-canonical-state.v2"
_C19_CHANNEL_ORDER = tuple(
    channel for pair in range(10) for channel in (f"q{pair}", f"p{pair}")
)
_C19_SPATIAL_SHAPE = (8,)
_C19_METRIC_KIND = "constant-state-v1"
_C19_METRIC_SUPPORT = ((0,),)
_FAILURE_REASON_IDS = frozenset(
    (
        "MATERIALIZATION_INVALID",
        "FACTORY_DEAD",
        "METRIC_PROTOCOL_DRIFT",
        "METRIC_REPLAY_FAILED",
        "SUPPORT_INVALID",
        "BRANCH_JOIN_FAILED",
        "CROSS_PARENT_ROOT",
    )
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()
_PROPERTY_BINDING_TOKEN = object()


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _channel_order(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise TypeError(f"{field} must be a non-empty exact tuple")
    if not all(type(item) is str and item for item in value):
        raise TypeError(f"{field} must contain exact non-empty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{field} must be unique")
    return value


def _shape(value: object, field: str) -> tuple[int, ...]:
    if type(value) is not tuple or not value:
        raise TypeError(f"{field} must be a non-empty exact tuple")
    if not all(type(item) is int and item > 0 for item in value):
        raise ValueError(f"{field} must contain exact positive ints")
    return value


def _support(value: object, field: str) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple or not value:
        raise TypeError(f"{field} must be a non-empty exact tuple")
    result: list[tuple[int, ...]] = []
    for index, offset in enumerate(value):
        if type(offset) is not tuple or not offset:
            raise TypeError(f"{field}[{index}] must be a non-empty exact tuple")
        if not all(type(component) is int for component in offset):
            raise TypeError(f"{field}[{index}] must contain exact ints")
        result.append(offset)
    answer = tuple(result)
    if answer != tuple(sorted(set(answer))):
        raise ValueError(f"{field} must be sorted and unique")
    return answer


class MetricSupportAuthorityV1Failure(ValueError):
    """Typed fail-closed result at the metric-support authority boundary."""

    def __init__(self, reason_id: str, detail: str) -> None:
        if reason_id not in _FAILURE_REASON_IDS:
            raise ValueError("metric-support-authority-v1 reason is not frozen")
        self.reason_id = reason_id
        self.detail = _text(detail, "metric-support-authority-v1 detail")
        super().__init__(f"{reason_id}: {detail}")


@dataclass(frozen=True)
class MetricSignedSupportAttestationV1:
    attestation_schema_version: str
    parent_freeze_v3_sha: str
    current_application_authority_v3_sha: str
    current_scenario_authority_v3_sha: str
    response_contract_v3_sha: str
    metric_support_protocol_sha: str
    application_scenario_materialization_v3_sha: str
    factory_sha: str
    factory_role: Literal["actual", "matched_ablated"]
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    metric_kind: Literal["constant-state-v1"]
    metric_support_offsets: tuple[tuple[int, ...], ...]
    metric_support_sha: str
    attestation_sha: str

    def __post_init__(self) -> None:
        if self.attestation_schema_version != (
            METRIC_SIGNED_SUPPORT_ATTESTATION_V1_SCHEMA_VERSION
        ):
            raise ValueError("metric support attestation schema drifted")
        for name in (
            "parent_freeze_v3_sha",
            "current_application_authority_v3_sha",
            "current_scenario_authority_v3_sha",
            "response_contract_v3_sha",
            "metric_support_protocol_sha",
            "application_scenario_materialization_v3_sha",
            "factory_sha",
            "metric_support_sha",
            "attestation_sha",
        ):
            _sha(getattr(self, name), name)
        if self.factory_role not in ("actual", "matched_ablated"):
            raise ValueError("factory_role is not frozen")
        _text(self.state_schema_id, "state_schema_id")
        _channel_order(self.channel_order, "channel_order")
        _shape(self.spatial_shape, "spatial_shape")
        if self.metric_kind != _C19_METRIC_KIND:
            raise ValueError("metric_kind is not frozen")
        _support(self.metric_support_offsets, "metric_support_offsets")


def metric_signed_support_attestation_v1_payload(
    attestation: MetricSignedSupportAttestationV1,
) -> dict[str, object]:
    _exact_record(
        attestation,
        MetricSignedSupportAttestationV1,
        "metric signed support attestation v1",
    )
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


@dataclass(frozen=True)
class _VerifiedMetricSupportAttestationV1View:
    attestation: MetricSignedSupportAttestationV1
    parent: object
    materialization: VerifiedV3M0ApplicationScenarioMaterializationV3
    factory: object
    factory_binding: object


@dataclass(frozen=True)
class _MetricSupportAuthorityRecordV1:
    attestation: MetricSignedSupportAttestationV1
    parent: object
    materialization: object
    factory: object
    factory_binding: object
    authority_seal: str


class VerifiedMetricSignedSupportAttestationV1:
    """Opaque live capability for one exact Parent-v3 C19 factory branch."""

    __slots__ = (
        "__attestation",
        "__authority_seal",
        "__weakref__",
    )

    def __init__(self) -> None:
        raise TypeError("metric support attestation is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("metric support attestation is immutable")


def _make_metric_support_property_dispatcher(binding_token: object):
    bindings: dict[int, tuple[weakref.ReferenceType[object], object]] = {}
    lock = threading.RLock()

    def require_binding(value: object, expected_resolver=None):
        with lock:
            current = bindings.get(id(value))
            if current is None or current[0]() is not value:
                raise ValueError("metric support property identity is not live")
            resolver = current[1]
        if expected_resolver is not None and resolver is not expected_resolver:
            raise ValueError("metric support property resolver identity drifted")
        return resolver

    def resolve(value: object):
        return require_binding(value)(value)

    def bind(value: object, resolver, *, token: object) -> None:
        if token is not binding_token:
            raise TypeError("metric support property binding token mismatch")
        if not callable(resolver):
            raise TypeError("metric support property resolver must be callable")
        identity = id(value)

        def remove_stale(reference, wrapper_id=identity):
            with lock:
                observed = bindings.get(wrapper_id)
                if observed is not None and observed[0] is reference:
                    del bindings[wrapper_id]

        reference = weakref.ref(value, remove_stale)
        with lock:
            current = bindings.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("metric support property identity collision")
            bindings[identity] = (reference, resolver)

    return resolve, bind, require_binding


(
    _resolve_metric_support_property,
    _bind_metric_support_property,
    _require_metric_support_property_binding,
) = _make_metric_support_property_dispatcher(_PROPERTY_BINDING_TOKEN)


def _make_attestation_property(resolver):
    def attestation(value: object):
        return resolver(value).attestation

    return property(attestation)


VerifiedMetricSignedSupportAttestationV1.attestation = _make_attestation_property(
    _resolve_metric_support_property
)


class _MetricSupportAuthorityGraphV1(NamedTuple):
    issue: object
    verify: object
    reverify: object


def _make_metric_support_authority_v1_graph(
    issuance_token: object,
) -> _MetricSupportAuthorityGraphV1:
    if issuance_token is not _ISSUANCE_TOKEN:
        raise TypeError("metric support graph issuance token mismatch")

    materialization_requirer = (
        _require_v3m0_application_scenario_materialization_v3_for_parent
    )
    protocol_verifier = verify_metric_support_derivation_protocol_v1
    support_payload_builder = metric_support_payload
    sha_builder = canonical_sha
    clone = copy.deepcopy
    replace_fn = replace
    type_fn = type
    id_fn = id
    wrapper_type = VerifiedMetricSignedSupportAttestationV1
    body_type = MetricSignedSupportAttestationV1
    bind_property = _bind_metric_support_property
    require_property_binding = _require_metric_support_property_binding
    registry: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedMetricSignedSupportAttestationV1],
            _MetricSupportAuthorityRecordV1,
        ],
    ] = {}
    lock = threading.RLock()

    def fail(reason_id: str, detail: str, cause: Exception | None = None):
        failure = MetricSupportAuthorityV1Failure(reason_id, detail)
        if cause is None:
            raise failure
        raise failure from cause

    def require_materialization(parent, materialization):
        try:
            return materialization_requirer(parent, materialization)
        except ApplicationMaterializationV3Failure as exc:
            if exc.reason_id == "CROSS_PARENT_ROOT":
                reason = "CROSS_PARENT_ROOT"
            elif exc.reason_id == "FACTORY_REPLAY_FAILED":
                reason = "FACTORY_DEAD"
            else:
                reason = "MATERIALIZATION_INVALID"
            fail(reason, exc.detail, exc)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("MATERIALIZATION_INVALID", str(exc), exc)

    def require_protocol(protocol: object) -> MetricSupportDerivationProtocolV1:
        try:
            return protocol_verifier(protocol)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("METRIC_PROTOCOL_DRIFT", str(exc), exc)

    def derive(parent, materialization, factory_role):
        if factory_role not in ("actual", "matched_ablated"):
            fail("BRANCH_JOIN_FAILED", "factory role is not frozen")
        view = require_materialization(parent, materialization)
        try:
            raw = view.materialization
            application = raw.current_application_authority
            scenario = raw.current_scenario_authority
            response = raw.current_scenario_response_contract
            if scenario.response_contract != response:
                fail(
                    "MATERIALIZATION_INVALID",
                    "scenario response differs from materialization response",
                )
            protocol = require_protocol(response.metric_support_derivation)
            if factory_role == "actual":
                factory = view.actual_factory
                binding = raw.actual_factory_binding
            else:
                factory = view.matched_ablated_factory
                binding = raw.matched_ablated_factory_binding
            factory_body = binding.factory
            if (
                binding.branch != factory_role
                or binding.parent_freeze_v3_sha
                != raw.actual_factory_binding.parent_freeze_v3_sha
                or raw.actual_factory_binding.parent_freeze_v3_sha
                != raw.matched_ablated_factory_binding.parent_freeze_v3_sha
            ):
                fail("BRANCH_JOIN_FAILED", "factory binding lineage drifted")
            if (
                factory_body.factory_sha
                not in (
                    raw.actual_factory_binding.factory.factory_sha,
                    raw.matched_ablated_factory_binding.factory.factory_sha,
                )
                or factory_body.state_schema_id != application.state_schema_id
                or factory_body.channel_order != application.channel_order
                or factory_body.state_shape[1:] != application.spatial_shape
            ):
                fail("BRANCH_JOIN_FAILED", "factory body differs from C19 branch")
            if (
                protocol.state_schema_id != application.state_schema_id
                or protocol.channel_order != application.channel_order
                or protocol.spatial_shape != application.spatial_shape
                or protocol.spatial_ndim != len(application.spatial_shape)
                or protocol.metric_kind != _C19_METRIC_KIND
                or protocol.metric_support_offsets != _C19_METRIC_SUPPORT
                or protocol.caller_supplied_support_allowed is not False
            ):
                fail("METRIC_PROTOCOL_DRIFT", "C19 metric protocol body drifted")
            if (
                protocol.state_schema_id != _C19_STATE_SCHEMA_ID
                or protocol.channel_order != _C19_CHANNEL_ORDER
                or protocol.spatial_shape != _C19_SPATIAL_SHAPE
            ):
                fail("METRIC_PROTOCOL_DRIFT", "metric protocol is not exact C19")
            support_payload = support_payload_builder(protocol.metric_support_offsets)
            expected_support_sha = sha_builder(support_payload)
            if protocol.metric_support_sha != expected_support_sha:
                fail("METRIC_PROTOCOL_DRIFT", "metric support SHA drifted")
            provisional = body_type(
                attestation_schema_version=(
                    METRIC_SIGNED_SUPPORT_ATTESTATION_V1_SCHEMA_VERSION
                ),
                parent_freeze_v3_sha=binding.parent_freeze_v3_sha,
                current_application_authority_v3_sha=(
                    application.application_authority_sha
                ),
                current_scenario_authority_v3_sha=(scenario.scenario_authority_sha),
                response_contract_v3_sha=response.response_contract_sha,
                metric_support_protocol_sha=protocol.protocol_sha,
                application_scenario_materialization_v3_sha=(raw.materialization_sha),
                factory_sha=factory_body.factory_sha,
                factory_role=factory_role,
                state_schema_id=protocol.state_schema_id,
                channel_order=tuple(protocol.channel_order),
                spatial_shape=tuple(protocol.spatial_shape),
                metric_kind=protocol.metric_kind,
                metric_support_offsets=tuple(protocol.metric_support_offsets),
                metric_support_sha=expected_support_sha,
                attestation_sha="0" * 64,
            )
            body = replace_fn(
                provisional,
                attestation_sha=sha_builder(
                    metric_signed_support_attestation_v1_payload(provisional)
                ),
            )
            return body, factory, binding
        except MetricSupportAuthorityV1Failure:
            raise
        except RuntimeError as exc:
            fail("METRIC_REPLAY_FAILED", str(exc), exc)
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            fail("MATERIALIZATION_INVALID", str(exc), exc)

    def authority_seal(body: MetricSignedSupportAttestationV1) -> str:
        return sha_builder(
            {
                "authority_kind": "v3m0-metric-signed-support-live-v1",
                "attestation_sha": body.attestation_sha,
                "parent_freeze_v3_sha": body.parent_freeze_v3_sha,
                "factory_sha": body.factory_sha,
                "factory_role": body.factory_role,
            }
        )

    def shallow(value) -> _MetricSupportAuthorityRecordV1:
        if type_fn(value) is not wrapper_type:
            raise TypeError("value must be an exact live metric support capability")
        with lock:
            current = registry.get(id_fn(value))
            if current is None or current[0]() is not value:
                raise ValueError("metric support capability identity is not live")
            authority = current[1]
        try:
            private_body = object.__getattribute__(
                value,
                "_VerifiedMetricSignedSupportAttestationV1__attestation",
            )
            private_seal = object.__getattribute__(
                value,
                "_VerifiedMetricSignedSupportAttestationV1__authority_seal",
            )
        except AttributeError as exc:
            raise ValueError("metric support capability is incomplete") from exc
        if (
            private_body != authority.attestation
            or private_seal != authority.authority_seal
            or private_seal != authority_seal(authority.attestation)
        ):
            raise ValueError("metric support capability immutable guard drifted")
        require_property_binding(value, property_view)
        return authority

    def property_view(value):
        authority = shallow(value)
        return _VerifiedMetricSupportAttestationV1View(
            attestation=clone(authority.attestation),
            parent=authority.parent,
            materialization=authority.materialization,
            factory=authority.factory,
            factory_binding=clone(authority.factory_binding),
        )

    def register(body, parent, materialization, factory, binding):
        seal = authority_seal(body)
        wrapper = object.__new__(wrapper_type)
        object.__setattr__(
            wrapper,
            "_VerifiedMetricSignedSupportAttestationV1__attestation",
            clone(body),
        )
        object.__setattr__(
            wrapper,
            "_VerifiedMetricSignedSupportAttestationV1__authority_seal",
            seal,
        )
        authority = _MetricSupportAuthorityRecordV1(
            attestation=clone(body),
            parent=parent,
            materialization=materialization,
            factory=factory,
            factory_binding=clone(binding),
            authority_seal=seal,
        )
        identity = id_fn(wrapper)

        def remove_stale(reference, wrapper_id=identity):
            with lock:
                observed = registry.get(wrapper_id)
                if observed is not None and observed[0] is reference:
                    del registry[wrapper_id]

        reference = weakref.ref(wrapper, remove_stale)
        with lock:
            current = registry.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("metric support capability identity collision")
            registry[identity] = (reference, authority)
        bind_property(
            wrapper,
            property_view,
            token=_PROPERTY_BINDING_TOKEN,
        )
        return wrapper

    def issue(parent, materialization, factory_role):
        body, factory, binding = derive(parent, materialization, factory_role)
        return register(body, parent, materialization, factory, binding)

    def verify(attestation, parent, materialization):
        if type_fn(attestation) is not body_type:
            raise TypeError("attestation must be an exact raw metric attestation")
        try:
            attestation.__post_init__()
            if attestation.attestation_sha != sha_builder(
                metric_signed_support_attestation_v1_payload(attestation)
            ):
                fail("METRIC_REPLAY_FAILED", "attestation SHA does not match body")
        except MetricSupportAuthorityV1Failure:
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            fail("METRIC_REPLAY_FAILED", str(exc), exc)
        expected, factory, binding = derive(
            parent,
            materialization,
            attestation.factory_role,
        )
        if attestation.parent_freeze_v3_sha != expected.parent_freeze_v3_sha:
            fail("CROSS_PARENT_ROOT", "attestation Parent-v3 root drifted")
        if (
            attestation.factory_role != expected.factory_role
            or attestation.factory_sha != expected.factory_sha
        ):
            fail("BRANCH_JOIN_FAILED", "attestation factory branch drifted")
        if (
            attestation.metric_kind != expected.metric_kind
            or attestation.metric_support_offsets != expected.metric_support_offsets
            or attestation.metric_support_sha != expected.metric_support_sha
        ):
            fail("SUPPORT_INVALID", "attestation metric support drifted")
        if (
            attestation.state_schema_id != expected.state_schema_id
            or attestation.channel_order != expected.channel_order
            or attestation.spatial_shape != expected.spatial_shape
            or attestation.metric_support_protocol_sha
            != expected.metric_support_protocol_sha
        ):
            fail("METRIC_PROTOCOL_DRIFT", "attestation metric protocol drifted")
        if attestation != expected:
            fail("MATERIALIZATION_INVALID", "attestation lineage body drifted")
        return register(expected, parent, materialization, factory, binding)

    def reverify(value):
        authority = shallow(value)
        expected, factory, binding = derive(
            authority.parent,
            authority.materialization,
            authority.attestation.factory_role,
        )
        if expected != authority.attestation or binding != authority.factory_binding:
            raise ValueError("metric support capability replay drifted")
        return _VerifiedMetricSupportAttestationV1View(
            attestation=clone(authority.attestation),
            parent=authority.parent,
            materialization=authority.materialization,
            factory=factory,
            factory_binding=clone(authority.factory_binding),
        )

    return _MetricSupportAuthorityGraphV1(issue, verify, reverify)


_PRODUCTION_GRAPH = _make_metric_support_authority_v1_graph(_ISSUANCE_TOKEN)


def _make_public_metric_support_apis(issue_fn, verify_fn):
    def issue_c19_metric_signed_support_attestation_v1(
        parent,
        materialization,
        factory_role,
    ):
        return issue_fn(parent, materialization, factory_role)

    def verify_c19_metric_signed_support_attestation_v1(
        attestation,
        parent,
        materialization,
    ):
        return verify_fn(attestation, parent, materialization)

    return (
        issue_c19_metric_signed_support_attestation_v1,
        verify_c19_metric_signed_support_attestation_v1,
    )


(
    issue_c19_metric_signed_support_attestation_v1,
    verify_c19_metric_signed_support_attestation_v1,
) = _make_public_metric_support_apis(
    _PRODUCTION_GRAPH.issue,
    _PRODUCTION_GRAPH.verify,
)


def _make_private_metric_support_reverifier(reverify_fn):
    def _reverify_verified_metric_signed_support_attestation_v1(value):
        return reverify_fn(value)

    return _reverify_verified_metric_signed_support_attestation_v1


_reverify_verified_metric_signed_support_attestation_v1 = (
    _make_private_metric_support_reverifier(_PRODUCTION_GRAPH.reverify)
)


__all__ = [
    "MetricSupportAuthorityV1Failure",
    "MetricSignedSupportAttestationV1",
    "VerifiedMetricSignedSupportAttestationV1",
    "issue_c19_metric_signed_support_attestation_v1",
    "metric_signed_support_attestation_v1_payload",
    "verify_c19_metric_signed_support_attestation_v1",
]
