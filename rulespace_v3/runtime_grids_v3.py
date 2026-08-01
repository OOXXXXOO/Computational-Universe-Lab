"""Parent-v3 bridge and dynamics runtime-grid authorities."""

from __future__ import annotations

import copy
import re
from struct import pack as _pack_binary
import threading
import weakref
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass, replace
from enum import Enum
from types import SimpleNamespace
from typing import NamedTuple

from .application_materialization_v3 import (
    ApplicationMaterializationV3Failure,
    ApplicationScenarioMaterializationV3,
    FactoryBranchBindingV3,
    VerifiedV3M0ApplicationScenarioMaterializationV3,
    _require_v3m0_application_scenario_materialization_v3_for_parent,
    application_scenario_materialization_v3_payload,
    factory_branch_binding_v3_payload,
)
from .grids import (
    BridgeKGridManifest,
    DirectionManifest,
    DirectionPathClosure,
    DynamicsKGridManifest,
    ResponseKGridManifest,
    bridge_grid_payload,
    build_bridge_grid_manifest,
    build_dynamics_grid_manifest,
    canonical_sha,
    dynamics_grid_payload,
    verify_bridge_grid_manifest,
    verify_dynamics_grid_manifest,
)
from .metric_support_authority_v1 import (
    MetricSignedSupportAttestationV1,
    MetricSupportAuthorityV1Failure,
    VerifiedMetricSignedSupportAttestationV1,
    _reverify_verified_metric_signed_support_attestation_v1,
    metric_signed_support_attestation_v1_payload,
)
from .transition_authority_v3 import (
    TransitionAuthorityV3,
    TransitionAuthorityV3Failure,
    VerifiedTransitionAuthorityV3,
    _reverify_verified_transition_authority_v3,
    transition_authority_v3_payload,
)


BRIDGE_GRID_AUTHORITY_V3_SCHEMA_VERSION = "v3m0.bridge-grid-authority.v3"
DYNAMICS_GRID_AUTHORITY_V3_SCHEMA_VERSION = "v3m0.dynamics-grid-authority.v3"
_FAILURE_REASON_IDS = frozenset(
    (
        "FACTORY_SUPPORT_INVALID",
        "TRANSITION_INVALID",
        "METRIC_ATTESTATION_INVALID",
        "BRANCH_JOIN_FAILED",
        "GRID_DERIVATION_FAILED",
        "CROSS_PARENT_ROOT",
    )
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()
_BRIDGE_PROPERTY_TOKEN = object()
_DYNAMICS_PROPERTY_TOKEN = object()


def _text(
    value: object,
    field: str,
    *,
    _type=type,
    _str_type=str,
    _type_error=TypeError,
) -> str:
    if _type(value) is not _str_type or not value.strip():
        raise _type_error(f"{field} must be an exact non-empty string")
    return value


def _sha(
    value: object,
    field: str,
    *,
    _text_validator=_text,
    _lower_sha=_LOWER_SHA,
    _value_error=ValueError,
) -> str:
    result = _text_validator(value, field)
    if _lower_sha.fullmatch(result) is None:
        raise _value_error(f"{field} must be a lowercase SHA-256")
    return result


def _exact_record(
    value: object,
    record_type: type,
    field: str,
    *,
    _fields_builder=dataclass_fields,
    _type=type,
    _frozenset_builder=frozenset,
    _vars_builder=vars,
    _type_error=TypeError,
    _value_error=ValueError,
) -> None:
    if _type(value) is not record_type:
        raise _type_error(f"{field} must be an exact {record_type.__name__}")
    expected = _frozenset_builder(item.name for item in _fields_builder(record_type))
    if _frozenset_builder(_vars_builder(value)) != expected:
        raise _value_error(f"{field} contains unknown or missing fields")


def _wire_tree(
    value: object,
    *,
    _enum_type=Enum,
    _is_dataclass=is_dataclass,
    _fields_builder=dataclass_fields,
    _namespace_type=SimpleNamespace,
    _type=type,
    _isinstance=isinstance,
    _getattr=getattr,
    _vars_builder=vars,
    _tuple_type=tuple,
    _list_type=list,
    _dict_type=dict,
    _leaf_types=(str, bool, int, float),
    _type_error=TypeError,
) -> object:
    def walk(current: object) -> object:
        if current is None or _type(current) in _leaf_types:
            return current
        if _isinstance(current, _enum_type):
            return walk(current.value)
        if _is_dataclass(current):
            return {
                item.name: walk(_getattr(current, item.name))
                for item in _fields_builder(current)
            }
        if _isinstance(current, _namespace_type):
            return {key: walk(item) for key, item in _vars_builder(current).items()}
        if _type(current) in (_tuple_type, _list_type):
            return [walk(item) for item in current]
        if _type(current) is _dict_type:
            return {key: walk(item) for key, item in current.items()}
        raise _type_error(f"runtime-grid wire contains {_type(current).__name__}")

    return walk(value)


def _require_exact_recursive_wire(
    candidate: object,
    expected: object,
    *,
    _type=type,
    _id=id,
    _isinstance=isinstance,
    _enum_type=Enum,
    _is_dataclass=is_dataclass,
    _fields_builder=dataclass_fields,
    _namespace_type=SimpleNamespace,
    _vars_builder=vars,
    _frozenset_builder=frozenset,
    _getattr=getattr,
    _tuple_builder=tuple,
    _set_builder=set,
    _len=len,
    _zip=zip,
    _tuple_type=tuple,
    _list_type=list,
    _dict_type=dict,
    _object_type=object,
    _plain_leaf_types=(str, bool, int),
    _float_type=float,
    _complex_type=complex,
    _binary_pack=_pack_binary,
    _type_error=TypeError,
    _value_error=ValueError,
) -> None:
    active: set[tuple[int, int]] = _set_builder()

    def walk(current: object, reference: object) -> None:
        if _type(current) is not _type(reference):
            raise _type_error("recursive runtime-grid wire type drifted")
        if current is None:
            return
        current_type = _type(current)
        if current_type in _plain_leaf_types:
            if current != reference:
                raise _value_error("recursive runtime-grid leaf value drifted")
            return
        if current_type is _float_type:
            if _binary_pack("!d", current) != _binary_pack("!d", reference):
                raise _value_error("recursive runtime-grid leaf bits drifted")
            return
        if current_type is _complex_type:
            current_bits = _binary_pack("!dd", current.real, current.imag)
            reference_bits = _binary_pack("!dd", reference.real, reference.imag)
            if current_bits != reference_bits:
                raise _value_error("recursive runtime-grid leaf bits drifted")
            return
        if _isinstance(current, _enum_type):
            walk(current.value, reference.value)
            return
        identity_pair = (_id(current), _id(reference))
        if identity_pair in active:
            raise _value_error("recursive runtime-grid wire cycle detected")
        active.add(identity_pair)
        try:
            if _is_dataclass(current):
                if _type(current).__bases__ != (_object_type,):
                    raise _type_error(
                        "recursive runtime-grid dataclass subclass is forbidden"
                    )
                declared = _tuple_builder(_fields_builder(reference))
                names = _frozenset_builder(item.name for item in declared)
                if (
                    _frozenset_builder(_vars_builder(current)) != names
                    or _frozenset_builder(_vars_builder(reference)) != names
                ):
                    raise _value_error(
                        "recursive runtime-grid dataclass fields drifted"
                    )
                for item in declared:
                    walk(
                        _getattr(current, item.name),
                        _getattr(reference, item.name),
                    )
                return
            if _isinstance(current, _namespace_type):
                current_vars = _vars_builder(current)
                reference_vars = _vars_builder(reference)
                if _tuple_builder(current_vars) != _tuple_builder(reference_vars):
                    raise _value_error(
                        "recursive runtime-grid namespace fields drifted"
                    )
                for key in current_vars:
                    walk(current_vars[key], reference_vars[key])
                return
            if _type(current) in (_tuple_type, _list_type):
                if _len(current) != _len(reference):
                    raise _value_error("recursive runtime-grid sequence length drifted")
                for current_item, reference_item in _zip(current, reference):
                    walk(current_item, reference_item)
                return
            if _type(current) is _dict_type:
                current_keys = _tuple_builder(current)
                reference_keys = _tuple_builder(reference)
                if _len(current_keys) != _len(reference_keys):
                    raise _value_error("recursive runtime-grid mapping keys drifted")
                for current_key, reference_key in _zip(
                    current_keys,
                    reference_keys,
                ):
                    walk(current_key, reference_key)
                    walk(current[current_key], reference[reference_key])
                return
            raise _type_error(
                f"unsupported recursive runtime-grid wire {_type(current).__name__}"
            )
        finally:
            active.remove(identity_pair)

    walk(candidate, expected)


def _protocol_record_impl(
    protocol: object,
    *,
    dataclass_predicate,
    fields_builder,
    nested_wire_builder,
    _getattr=getattr,
    _vars_builder=vars,
    _tuple_builder=tuple,
    _frozenset_builder=frozenset,
    _attribute_error=AttributeError,
    _type_error=TypeError,
    _value_error=ValueError,
) -> dict[str, object]:
    if not dataclass_predicate(protocol):
        raise _type_error("grid derivation protocol must be a dataclass record")
    declared = _tuple_builder(fields_builder(protocol))
    declared_names = _frozenset_builder(item.name for item in declared)
    if _frozenset_builder(_vars_builder(protocol)) != declared_names:
        raise _value_error("grid derivation protocol fields drifted")
    try:
        protocol_sha = protocol.protocol_sha
    except _attribute_error as exc:
        raise _type_error("grid derivation protocol omitted protocol_sha") from exc
    body = {
        item.name: nested_wire_builder(_getattr(protocol, item.name))
        for item in declared
        if item.name != "protocol_sha"
    }
    return {**body, "protocol_sha": protocol_sha}


def _make_protocol_record_api(
    protocol_record_impl,
    *,
    dataclass_predicate,
    fields_builder,
    nested_wire_builder,
):
    def _protocol_record(protocol: object) -> dict[str, object]:
        return protocol_record_impl(
            protocol,
            dataclass_predicate=dataclass_predicate,
            fields_builder=fields_builder,
            nested_wire_builder=nested_wire_builder,
        )

    return _protocol_record


_protocol_record = _make_protocol_record_api(
    _protocol_record_impl,
    dataclass_predicate=is_dataclass,
    fields_builder=dataclass_fields,
    nested_wire_builder=_wire_tree,
)


def _make_runtime_grid_failure_initializer(reason_ids, text_validator, base_error):
    def __init__(self, reason_id: str, detail: str) -> None:
        if reason_id not in reason_ids:
            raise base_error("runtime-grid-authority-v3 reason is not frozen")
        self.reason_id = reason_id
        self.detail = text_validator(detail, "runtime-grid-authority-v3 detail")
        base_error.__init__(self, f"{reason_id}: {detail}")

    return __init__


class RuntimeGridAuthorityV3Failure(ValueError):
    """Typed fail-closed result at the Parent-v3 runtime-grid boundary."""

    __init__ = _make_runtime_grid_failure_initializer(
        _FAILURE_REASON_IDS,
        _text,
        ValueError,
    )


@dataclass(frozen=True)
class BridgeGridAuthorityV3:
    grid_authority_schema_version: str
    materialization: ApplicationScenarioMaterializationV3
    factory_binding: FactoryBranchBindingV3
    derivation_protocol: object
    bridge_grid: BridgeKGridManifest
    grid_authority_sha: str

    def __post_init__(
        self,
        *,
        _schema=BRIDGE_GRID_AUTHORITY_V3_SCHEMA_VERSION,
        _grid_type=BridgeKGridManifest,
        _sha_validator=_sha,
        _type=type,
        _type_error=TypeError,
        _value_error=ValueError,
    ) -> None:
        if self.grid_authority_schema_version != _schema:
            raise _value_error("bridge grid authority schema drifted")
        if _type(self.bridge_grid) is not _grid_type:
            raise _type_error("bridge_grid has the wrong exact grid type")
        _sha_validator(self.grid_authority_sha, "grid_authority_sha")


@dataclass(frozen=True)
class DynamicsGridAuthorityV3:
    grid_authority_schema_version: str
    transition_authority: TransitionAuthorityV3
    metric_support_attestation: MetricSignedSupportAttestationV1
    derivation_protocol: object
    dynamics_grid: DynamicsKGridManifest
    grid_authority_sha: str

    def __post_init__(
        self,
        *,
        _schema=DYNAMICS_GRID_AUTHORITY_V3_SCHEMA_VERSION,
        _grid_type=DynamicsKGridManifest,
        _sha_validator=_sha,
        _type=type,
        _type_error=TypeError,
        _value_error=ValueError,
    ) -> None:
        if self.grid_authority_schema_version != _schema:
            raise _value_error("dynamics grid authority schema drifted")
        if _type(self.dynamics_grid) is not _grid_type:
            raise _type_error("dynamics_grid has the wrong exact grid type")
        _sha_validator(self.grid_authority_sha, "grid_authority_sha")


def _bridge_grid_authority_v3_payload_impl(
    authority,
    *,
    body_type,
    record_validator,
    materialization_payload_builder,
    binding_payload_builder,
    protocol_record_builder,
    grid_payload_builder,
    _recursive_wire_guard=_require_exact_recursive_wire,
    _grid_verifier=verify_bridge_grid_manifest,
    _materialization_type=ApplicationScenarioMaterializationV3,
    _binding_type=FactoryBranchBindingV3,
    _value_error=ValueError,
) -> dict[str, object]:
    record_validator(authority, body_type, "bridge grid authority v3")
    _recursive_wire_guard(authority, authority)
    materialization = authority.materialization
    binding = authority.factory_binding
    protocol = authority.derivation_protocol
    grid = authority.bridge_grid
    record_validator(
        materialization,
        _materialization_type,
        "bridge materialization",
    )
    record_validator(binding, _binding_type, "bridge factory binding")
    _recursive_wire_guard(materialization, materialization)
    if binding.branch == "actual":
        expected_binding = materialization.actual_factory_binding
    elif binding.branch == "matched_ablated":
        expected_binding = materialization.matched_ablated_factory_binding
    else:
        raise _value_error("bridge factory binding role drifted")
    _recursive_wire_guard(binding, expected_binding)
    if binding != expected_binding:
        raise _value_error("bridge factory binding lineage drifted")
    expected_protocol = (
        materialization.current_scenario_response_contract.bridge_grid_derivation
    )
    _recursive_wire_guard(protocol, expected_protocol)
    if protocol != expected_protocol:
        raise _value_error("bridge derivation protocol lineage drifted")
    _grid_verifier(
        grid,
        materialization.current_application_authority.spatial_shape,
        binding.support_offsets,
    )
    return {
        "grid_authority_schema_version": authority.grid_authority_schema_version,
        "materialization": {
            **materialization_payload_builder(materialization),
            "materialization_sha": materialization.materialization_sha,
        },
        "factory_binding": {
            **binding_payload_builder(binding),
            "binding_sha": binding.binding_sha,
        },
        "derivation_protocol": protocol_record_builder(protocol),
        "bridge_grid": {
            **grid_payload_builder(grid),
            "bridge_grid_sha": grid.bridge_grid_sha,
        },
    }


def _make_bridge_grid_authority_v3_payload_api(
    payload_impl,
    *,
    body_type,
    materialization_type,
    binding_type,
    record_validator,
    materialization_payload_builder,
    binding_payload_builder,
    protocol_record_builder,
    grid_payload_builder,
):
    def bridge_grid_authority_v3_payload(authority) -> dict[str, object]:
        return payload_impl(
            authority,
            body_type=body_type,
            _materialization_type=materialization_type,
            _binding_type=binding_type,
            record_validator=record_validator,
            materialization_payload_builder=materialization_payload_builder,
            binding_payload_builder=binding_payload_builder,
            protocol_record_builder=protocol_record_builder,
            grid_payload_builder=grid_payload_builder,
        )

    return bridge_grid_authority_v3_payload


bridge_grid_authority_v3_payload = _make_bridge_grid_authority_v3_payload_api(
    _bridge_grid_authority_v3_payload_impl,
    body_type=BridgeGridAuthorityV3,
    materialization_type=ApplicationScenarioMaterializationV3,
    binding_type=FactoryBranchBindingV3,
    record_validator=_exact_record,
    materialization_payload_builder=application_scenario_materialization_v3_payload,
    binding_payload_builder=factory_branch_binding_v3_payload,
    protocol_record_builder=_protocol_record,
    grid_payload_builder=bridge_grid_payload,
)


def _dynamics_grid_authority_v3_payload_impl(
    authority,
    *,
    body_type,
    record_validator,
    transition_payload_builder,
    metric_payload_builder,
    protocol_record_builder,
    grid_payload_builder,
    _recursive_wire_guard=_require_exact_recursive_wire,
    _grid_verifier=verify_dynamics_grid_manifest,
    _transition_type=TransitionAuthorityV3,
    _metric_type=MetricSignedSupportAttestationV1,
    _binding_type=FactoryBranchBindingV3,
    _value_error=ValueError,
) -> dict[str, object]:
    record_validator(
        authority,
        body_type,
        "dynamics grid authority v3",
    )
    _recursive_wire_guard(authority, authority)
    transition = authority.transition_authority
    metric = authority.metric_support_attestation
    protocol = authority.derivation_protocol
    grid = authority.dynamics_grid
    record_validator(
        transition,
        _transition_type,
        "dynamics transition authority",
    )
    record_validator(metric, _metric_type, "dynamics metric attestation")
    _recursive_wire_guard(transition, transition)
    _recursive_wire_guard(metric, metric)
    binding = transition.factory_binding
    record_validator(binding, _binding_type, "dynamics factory binding")
    materialization = transition.materialization
    if binding.branch == "actual":
        expected_binding = materialization.actual_factory_binding
    elif binding.branch == "matched_ablated":
        expected_binding = materialization.matched_ablated_factory_binding
    else:
        raise _value_error("dynamics factory binding role drifted")
    _recursive_wire_guard(binding, expected_binding)
    if binding != expected_binding:
        raise _value_error("dynamics factory binding lineage drifted")
    measured = transition.measured_transition
    application = materialization.current_application_authority
    scenario = materialization.current_scenario_authority
    response = materialization.current_scenario_response_contract
    metric_protocol = response.metric_support_derivation
    if (
        measured.parent_freeze_sha != metric.parent_freeze_v3_sha
        or measured.parent_freeze_sha != binding.parent_freeze_v3_sha
        or measured.factory_sha != metric.factory_sha
        or measured.factory_sha != binding.factory.factory_sha
        or measured.factory_role != metric.factory_role
        or measured.factory_role != binding.branch
        or measured.state_schema_id != metric.state_schema_id
        or measured.state_schema_id != application.state_schema_id
        or measured.channel_order != metric.channel_order
        or measured.channel_order != application.channel_order
        or measured.spatial_shape != metric.spatial_shape
        or measured.spatial_shape != application.spatial_shape
        or metric.current_application_authority_v3_sha
        != application.application_authority_sha
        or metric.current_scenario_authority_v3_sha != scenario.scenario_authority_sha
        or metric.response_contract_v3_sha != response.response_contract_sha
        or metric.metric_support_protocol_sha != metric_protocol.protocol_sha
        or metric.application_scenario_materialization_v3_sha
        != materialization.materialization_sha
        or metric.metric_kind != metric_protocol.metric_kind
        or metric.metric_support_offsets != metric_protocol.metric_support_offsets
        or metric.metric_support_sha != metric_protocol.metric_support_sha
    ):
        raise _value_error("dynamics transition/metric lineage drifted")
    expected_protocol = (
        materialization.current_scenario_response_contract.dynamics_grid_derivation
    )
    _recursive_wire_guard(protocol, expected_protocol)
    if protocol != expected_protocol:
        raise _value_error("dynamics derivation protocol lineage drifted")
    _grid_verifier(
        grid,
        transition.measured_transition.support_offsets,
        metric.metric_support_offsets,
    )
    return {
        "grid_authority_schema_version": authority.grid_authority_schema_version,
        "transition_authority": {
            **transition_payload_builder(transition),
            "transition_authority_sha": transition.transition_authority_sha,
        },
        "metric_support_attestation": {
            **metric_payload_builder(metric),
            "attestation_sha": metric.attestation_sha,
        },
        "derivation_protocol": protocol_record_builder(protocol),
        "dynamics_grid": {
            **grid_payload_builder(grid),
            "dynamics_grid_sha": grid.dynamics_grid_sha,
        },
    }


def _make_dynamics_grid_authority_v3_payload_api(
    payload_impl,
    *,
    body_type,
    transition_type,
    metric_type,
    binding_type,
    record_validator,
    transition_payload_builder,
    metric_payload_builder,
    protocol_record_builder,
    grid_payload_builder,
):
    def dynamics_grid_authority_v3_payload(authority) -> dict[str, object]:
        return payload_impl(
            authority,
            body_type=body_type,
            _transition_type=transition_type,
            _metric_type=metric_type,
            _binding_type=binding_type,
            record_validator=record_validator,
            transition_payload_builder=transition_payload_builder,
            metric_payload_builder=metric_payload_builder,
            protocol_record_builder=protocol_record_builder,
            grid_payload_builder=grid_payload_builder,
        )

    return dynamics_grid_authority_v3_payload


dynamics_grid_authority_v3_payload = _make_dynamics_grid_authority_v3_payload_api(
    _dynamics_grid_authority_v3_payload_impl,
    body_type=DynamicsGridAuthorityV3,
    transition_type=TransitionAuthorityV3,
    metric_type=MetricSignedSupportAttestationV1,
    binding_type=FactoryBranchBindingV3,
    record_validator=_exact_record,
    transition_payload_builder=transition_authority_v3_payload,
    metric_payload_builder=metric_signed_support_attestation_v1_payload,
    protocol_record_builder=_protocol_record,
    grid_payload_builder=dynamics_grid_payload,
)


@dataclass(frozen=True)
class _VerifiedBridgeGridAuthorityV3View:
    grid_authority: BridgeGridAuthorityV3
    parent: object
    materialization: VerifiedV3M0ApplicationScenarioMaterializationV3
    factory: object
    factory_binding: FactoryBranchBindingV3


@dataclass(frozen=True)
class _VerifiedDynamicsGridAuthorityV3View:
    grid_authority: DynamicsGridAuthorityV3
    parent: object
    transition: VerifiedTransitionAuthorityV3
    metric_attestation: VerifiedMetricSignedSupportAttestationV1


@dataclass(frozen=True)
class _BridgeGridAuthorityRecordV3:
    grid_authority: BridgeGridAuthorityV3
    parent: object
    materialization: object
    factory: object
    factory_binding: object
    authority_seal: str


@dataclass(frozen=True)
class _DynamicsGridAuthorityRecordV3:
    grid_authority: DynamicsGridAuthorityV3
    parent: object
    materialization: object
    transition: object
    metric_attestation: object
    authority_seal: str


class VerifiedBridgeGridAuthorityV3:
    """Opaque live bridge-grid authority."""

    __slots__ = ("__grid_authority", "__authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("bridge grid authority is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("bridge grid authority is immutable")


class VerifiedDynamicsGridAuthorityV3:
    """Opaque live dynamics-grid authority."""

    __slots__ = ("__grid_authority", "__authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("dynamics grid authority is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("dynamics grid authority is immutable")


def _make_property_dispatcher(
    binding_token: object,
    *,
    _weak_reference=weakref.ref,
    _id=id,
    _value_error=ValueError,
    _type_error=TypeError,
    _runtime_error=RuntimeError,
):
    bindings: dict[int, tuple[weakref.ReferenceType[object], object]] = {}
    lock = threading.RLock()

    def require_binding(value, expected_resolver=None):
        with lock:
            current = bindings.get(_id(value))
            if current is None or current[0]() is not value:
                raise _value_error("runtime-grid property identity is not live")
            resolver = current[1]
        if expected_resolver is not None and resolver is not expected_resolver:
            raise _value_error("runtime-grid property resolver drifted")
        return resolver

    def resolve(value):
        return require_binding(value)(value)

    def bind(value, resolver, *, token):
        if token is not binding_token:
            raise _type_error("runtime-grid property token mismatch")
        identity = _id(value)

        def remove_stale(reference, wrapper_id=identity):
            with lock:
                observed = bindings.get(wrapper_id)
                if observed is not None and observed[0] is reference:
                    del bindings[wrapper_id]

        reference = _weak_reference(value, remove_stale)
        with lock:
            current = bindings.get(identity)
            if current is not None and current[0]() is not None:
                raise _runtime_error("runtime-grid property identity collision")
            bindings[identity] = (reference, resolver)

    return resolve, bind, require_binding


(
    _resolve_bridge_property,
    _bind_bridge_property,
    _require_bridge_property_binding,
) = _make_property_dispatcher(_BRIDGE_PROPERTY_TOKEN)
(
    _resolve_dynamics_property,
    _bind_dynamics_property,
    _require_dynamics_property_binding,
) = _make_property_dispatcher(_DYNAMICS_PROPERTY_TOKEN)


def _make_property(
    resolver,
    field: str,
    *,
    _getattr=getattr,
    _property_builder=property,
):
    def authority(value, _getattr_fn=_getattr, _field=field):
        return _getattr_fn(resolver(value), _field)

    return _property_builder(authority)


VerifiedBridgeGridAuthorityV3.bridge_grid_authority = _make_property(
    _resolve_bridge_property,
    "grid_authority",
)
VerifiedDynamicsGridAuthorityV3.dynamics_grid_authority = _make_property(
    _resolve_dynamics_property,
    "grid_authority",
)


class _RuntimeGridsV3Graph(NamedTuple):
    derive_bridge: object
    derive_dynamics: object
    verify_pair: object
    reverify_bridge: object
    reverify_dynamics: object


def _make_runtime_grids_v3_graph(issuance_token: object) -> _RuntimeGridsV3Graph:
    if issuance_token is not _ISSUANCE_TOKEN:
        raise TypeError("runtime-grids-v3 graph token mismatch")

    materialization_failure_type = ApplicationMaterializationV3Failure
    transition_failure_type = TransitionAuthorityV3Failure
    metric_failure_type = MetricSupportAuthorityV1Failure
    materialization_type = ApplicationScenarioMaterializationV3
    binding_type = FactoryBranchBindingV3
    verified_materialization_type = VerifiedV3M0ApplicationScenarioMaterializationV3
    transition_type = TransitionAuthorityV3
    verified_transition_type = VerifiedTransitionAuthorityV3
    metric_type = MetricSignedSupportAttestationV1
    verified_metric_type = VerifiedMetricSignedSupportAttestationV1
    materialization_requirer = (
        _require_v3m0_application_scenario_materialization_v3_for_parent
    )
    transition_reverifier = _reverify_verified_transition_authority_v3
    metric_reverifier = _reverify_verified_metric_signed_support_attestation_v1
    bridge_builder = build_bridge_grid_manifest
    bridge_verifier = verify_bridge_grid_manifest
    dynamics_builder = build_dynamics_grid_manifest
    dynamics_verifier = verify_dynamics_grid_manifest
    bridge_grid_type = BridgeKGridManifest
    dynamics_grid_type = DynamicsKGridManifest
    bridge_body_type = BridgeGridAuthorityV3
    dynamics_body_type = DynamicsGridAuthorityV3
    bridge_wrapper_type = VerifiedBridgeGridAuthorityV3
    dynamics_wrapper_type = VerifiedDynamicsGridAuthorityV3
    bridge_view_type = _VerifiedBridgeGridAuthorityV3View
    dynamics_view_type = _VerifiedDynamicsGridAuthorityV3View
    bridge_record_type = _BridgeGridAuthorityRecordV3
    dynamics_record_type = _DynamicsGridAuthorityRecordV3
    failure_type = RuntimeGridAuthorityV3Failure
    bridge_schema = BRIDGE_GRID_AUTHORITY_V3_SCHEMA_VERSION
    dynamics_schema = DYNAMICS_GRID_AUTHORITY_V3_SCHEMA_VERSION
    bridge_payload_impl = _bridge_grid_authority_v3_payload_impl
    dynamics_payload_impl = _dynamics_grid_authority_v3_payload_impl
    materialization_payload_builder = application_scenario_materialization_v3_payload
    binding_payload_builder = factory_branch_binding_v3_payload
    transition_payload_builder = transition_authority_v3_payload
    metric_payload_builder = metric_signed_support_attestation_v1_payload
    protocol_record_impl = _protocol_record_impl
    nested_wire_builder = _wire_tree
    dataclass_predicate = is_dataclass
    fields_builder = dataclass_fields
    exact_record_validator = _exact_record
    recursive_wire_guard = _require_exact_recursive_wire
    bridge_grid_payload_builder = bridge_grid_payload
    dynamics_grid_payload_builder = dynamics_grid_payload
    sha_builder = canonical_sha
    clone = copy.deepcopy
    replace_fn = replace
    type_fn = type
    id_fn = id
    getattr_fn = getattr
    len_fn = len
    str_fn = str
    str_type = str
    object_type = object
    attribute_error_type = AttributeError
    runtime_error_type = RuntimeError
    type_error_type = TypeError
    value_error_type = ValueError
    replay_error_types = (
        attribute_error_type,
        runtime_error_type,
        type_error_type,
        value_error_type,
    )
    weak_reference = weakref.ref
    bridge_property_binder = _bind_bridge_property
    bridge_property_guard = _require_bridge_property_binding
    bridge_property_token = _BRIDGE_PROPERTY_TOKEN
    dynamics_property_binder = _bind_dynamics_property
    dynamics_property_guard = _require_dynamics_property_binding
    dynamics_property_token = _DYNAMICS_PROPERTY_TOKEN
    bridge_registry: dict[int, tuple[object, object]] = {}
    dynamics_registry: dict[int, tuple[object, object]] = {}
    bridge_lock = threading.RLock()
    dynamics_lock = threading.RLock()

    def fail(reason_id: str, detail: str, cause: BaseException | None = None):
        failure = failure_type(reason_id, detail)
        if cause is None:
            raise failure
        raise failure from cause

    def protocol_record(body):
        return protocol_record_impl(
            body,
            dataclass_predicate=dataclass_predicate,
            fields_builder=fields_builder,
            nested_wire_builder=nested_wire_builder,
        )

    def bridge_payload(body):
        return bridge_payload_impl(
            body,
            body_type=bridge_body_type,
            _materialization_type=materialization_type,
            _binding_type=binding_type,
            record_validator=exact_record_validator,
            materialization_payload_builder=materialization_payload_builder,
            binding_payload_builder=binding_payload_builder,
            protocol_record_builder=protocol_record,
            grid_payload_builder=bridge_grid_payload_builder,
        )

    def dynamics_payload(body):
        return dynamics_payload_impl(
            body,
            body_type=dynamics_body_type,
            _transition_type=transition_type,
            _metric_type=metric_type,
            _binding_type=binding_type,
            record_validator=exact_record_validator,
            transition_payload_builder=transition_payload_builder,
            metric_payload_builder=metric_payload_builder,
            protocol_record_builder=protocol_record,
            grid_payload_builder=dynamics_grid_payload_builder,
        )

    def require_materialization(parent, materialization):
        try:
            if type_fn(materialization) is not verified_materialization_type:
                raise type_error_type(
                    "bridge grid requires exact live B2 materialization"
                )
            view = materialization_requirer(parent, materialization)
            if type_fn(view.materialization) is not materialization_type:
                raise type_error_type(
                    "B2 owner seam returned wrong materialization body"
                )
            materialization_payload_builder(view.materialization)
            return view
        except materialization_failure_type as exc:
            if exc.reason_id == "CROSS_PARENT_ROOT":
                reason = "CROSS_PARENT_ROOT"
            else:
                reason = "FACTORY_SUPPORT_INVALID"
            fail(reason, exc.detail, exc)
        except failure_type:
            raise
        except replay_error_types as exc:
            fail("FACTORY_SUPPORT_INVALID", str_fn(exc), exc)

    def require_transition(transition):
        try:
            if type_fn(transition) is not verified_transition_type:
                raise type_error_type("dynamics grid requires exact live B3 transition")
            view = transition_reverifier(transition)
            if type_fn(view.transition_authority) is not transition_type:
                raise type_error_type("B3 owner seam returned wrong transition body")
            transition_payload_builder(view.transition_authority)
            return view
        except transition_failure_type as exc:
            fail("TRANSITION_INVALID", exc.detail, exc)
        except failure_type:
            raise
        except replay_error_types as exc:
            fail("TRANSITION_INVALID", str_fn(exc), exc)

    def require_metric(metric):
        try:
            if type_fn(metric) is not verified_metric_type:
                raise type_error_type(
                    "dynamics grid requires exact live B4 attestation"
                )
            view = metric_reverifier(metric)
            if type_fn(view.attestation) is not metric_type:
                raise type_error_type("B4 owner seam returned wrong attestation body")
            metric_payload_builder(view.attestation)
            return view
        except metric_failure_type as exc:
            fail("METRIC_ATTESTATION_INVALID", exc.detail, exc)
        except failure_type:
            raise
        except replay_error_types as exc:
            fail("METRIC_ATTESTATION_INVALID", str_fn(exc), exc)

    def bridge_components(parent, materialization, factory_role):
        if type_fn(factory_role) is not str_type or factory_role not in (
            "actual",
            "matched_ablated",
        ):
            fail("BRANCH_JOIN_FAILED", "bridge factory role is not frozen")
        view = require_materialization(parent, materialization)
        raw = view.materialization
        if factory_role == "actual":
            factory = view.actual_factory
            binding = raw.actual_factory_binding
        else:
            factory = view.matched_ablated_factory
            binding = raw.matched_ablated_factory_binding
        if type_fn(binding) is not binding_type:
            fail("BRANCH_JOIN_FAILED", "bridge branch binding has wrong exact type")
        binding_payload_builder(binding)
        application = raw.current_application_authority
        scenario = raw.current_scenario_authority
        response = raw.current_scenario_response_contract
        protocol = response.bridge_grid_derivation
        protocol_record(protocol)
        factory_body = factory.factory
        parent_sha = binding.parent_freeze_v3_sha
        if scenario.response_contract != response:
            fail("BRANCH_JOIN_FAILED", "bridge response lineage drifted")
        if (
            binding.branch != factory_role
            or factory_body != binding.factory
            or factory_body.factory_sha != binding.factory.factory_sha
            or getattr_fn(factory_body, "factory_role", factory_role) != factory_role
            or factory_body.state_schema_id != application.state_schema_id
            or factory_body.channel_order != application.channel_order
            or factory_body.state_shape[1:] != application.spatial_shape
            or factory_body.spatial_ndim != len_fn(application.spatial_shape)
        ):
            fail("BRANCH_JOIN_FAILED", "bridge branch body drifted")
        if (
            raw.actual_factory_binding.parent_freeze_v3_sha
            != raw.matched_ablated_factory_binding.parent_freeze_v3_sha
            or parent_sha != raw.actual_factory_binding.parent_freeze_v3_sha
        ):
            fail("CROSS_PARENT_ROOT", "bridge Parent-v3 root drifted")
        if (
            getattr_fn(protocol, "spatial_shape", application.spatial_shape)
            != application.spatial_shape
            or getattr_fn(protocol, "caller_supplied_points_allowed", False)
            is not False
        ):
            fail("FACTORY_SUPPORT_INVALID", "bridge derivation protocol drifted")
        try:
            grid = bridge_builder(
                application.spatial_shape,
                binding.support_offsets,
            )
            if type_fn(grid) is not bridge_grid_type:
                raise type_error_type("bridge builder returned wrong exact grid type")
            bridge_verifier(
                grid,
                application.spatial_shape,
                binding.support_offsets,
            )
        except failure_type:
            raise
        except replay_error_types as exc:
            fail("GRID_DERIVATION_FAILED", str_fn(exc), exc)
        return view, factory, binding, protocol, grid

    def dynamics_components(parent, transition, metric):
        transition_view = require_transition(transition)
        metric_view = require_metric(metric)
        transition_body = transition_view.transition_authority
        measured = transition_body.measured_transition
        attestation = metric_view.attestation
        role = measured.factory_role
        if role not in ("actual", "matched_ablated"):
            fail("BRANCH_JOIN_FAILED", "dynamics transition role is not frozen")
        if transition_view.parent is not parent or metric_view.parent is not parent:
            fail("CROSS_PARENT_ROOT", "dynamics Parent identity drifted")
        if transition_view.materialization is not metric_view.materialization:
            fail("BRANCH_JOIN_FAILED", "dynamics materialization identity drifted")
        raw = transition_body.materialization
        if type_fn(raw) is not materialization_type:
            fail("BRANCH_JOIN_FAILED", "transition materialization body drifted")
        binding = transition_body.factory_binding
        if type_fn(binding) is not binding_type:
            fail("BRANCH_JOIN_FAILED", "transition binding has wrong exact type")
        response = raw.current_scenario_response_contract
        protocol = response.dynamics_grid_derivation
        protocol_record(protocol)
        transition_factory = transition_view.factory.factory
        metric_factory = metric_view.factory.factory
        metric_binding = metric_view.factory_binding
        if measured.parent_freeze_sha != attestation.parent_freeze_v3_sha:
            fail("CROSS_PARENT_ROOT", "dynamics evidence Parent root drifted")
        if measured.parent_freeze_sha != binding.parent_freeze_v3_sha:
            fail("CROSS_PARENT_ROOT", "transition recursive Parent root drifted")
        if (
            measured.factory_role != attestation.factory_role
            or binding.branch != role
            or metric_binding.branch != role
            or measured.factory_sha != attestation.factory_sha
            or measured.factory_sha != binding.factory.factory_sha
            or transition_factory != binding.factory
            or metric_factory != binding.factory
            or metric_binding != binding
        ):
            fail("BRANCH_JOIN_FAILED", "dynamics branch/factory join drifted")
        if (
            transition_body.materialization.materialization_sha
            != attestation.application_scenario_materialization_v3_sha
            or transition_body.materialization.materialization_sha
            != transition_view.materialization.materialization.materialization_sha
        ):
            fail("BRANCH_JOIN_FAILED", "dynamics materialization root drifted")
        if (
            measured.state_schema_id != attestation.state_schema_id
            or measured.channel_order != attestation.channel_order
            or measured.spatial_shape != attestation.spatial_shape
            or attestation.metric_kind != "constant-state-v1"
            or getattr_fn(protocol, "caller_supplied_points_allowed", False)
            is not False
        ):
            fail("BRANCH_JOIN_FAILED", "dynamics state/protocol join drifted")
        try:
            grid = dynamics_builder(
                measured.support_offsets,
                attestation.metric_support_offsets,
            )
            if type_fn(grid) is not dynamics_grid_type:
                raise type_error_type("dynamics builder returned wrong exact grid type")
            dynamics_verifier(
                grid,
                measured.support_offsets,
                attestation.metric_support_offsets,
            )
        except failure_type:
            raise
        except replay_error_types as exc:
            fail("GRID_DERIVATION_FAILED", str_fn(exc), exc)
        return (
            transition_view,
            metric_view,
            protocol,
            grid,
        )

    def bridge_seal(body):
        return sha_builder(
            {
                "authority_kind": "parent-v3-bridge-grid-live-v3",
                "grid_authority_sha": body.grid_authority_sha,
                "parent_freeze_v3_sha": body.factory_binding.parent_freeze_v3_sha,
                "factory_sha": body.factory_binding.factory.factory_sha,
                "factory_role": body.factory_binding.branch,
            }
        )

    def dynamics_seal(body):
        measured = body.transition_authority.measured_transition
        return sha_builder(
            {
                "authority_kind": "parent-v3-dynamics-grid-live-v3",
                "grid_authority_sha": body.grid_authority_sha,
                "parent_freeze_v3_sha": measured.parent_freeze_sha,
                "factory_sha": measured.factory_sha,
                "factory_role": measured.factory_role,
            }
        )

    def bridge_shallow(value):
        if type_fn(value) is not bridge_wrapper_type:
            raise type_error_type("value must be an exact live bridge-grid capability")
        with bridge_lock:
            current = bridge_registry.get(id_fn(value))
            if current is None or current[0]() is not value:
                raise value_error_type("bridge-grid capability identity is not live")
            authority = current[1]
        private_body = object_type.__getattribute__(
            value,
            "_VerifiedBridgeGridAuthorityV3__grid_authority",
        )
        private_seal = object_type.__getattribute__(
            value,
            "_VerifiedBridgeGridAuthorityV3__authority_seal",
        )
        recursive_wire_guard(private_body, authority.grid_authority)
        if (
            private_body != authority.grid_authority
            or private_seal != authority.authority_seal
            or private_seal != bridge_seal(authority.grid_authority)
        ):
            raise value_error_type("bridge-grid immutable guard drifted")
        bridge_property_guard(value, bridge_property_view)
        return authority

    def dynamics_shallow(value):
        if type_fn(value) is not dynamics_wrapper_type:
            raise type_error_type(
                "value must be an exact live dynamics-grid capability"
            )
        with dynamics_lock:
            current = dynamics_registry.get(id_fn(value))
            if current is None or current[0]() is not value:
                raise value_error_type("dynamics-grid capability identity is not live")
            authority = current[1]
        private_body = object_type.__getattribute__(
            value,
            "_VerifiedDynamicsGridAuthorityV3__grid_authority",
        )
        private_seal = object_type.__getattribute__(
            value,
            "_VerifiedDynamicsGridAuthorityV3__authority_seal",
        )
        recursive_wire_guard(private_body, authority.grid_authority)
        if (
            private_body != authority.grid_authority
            or private_seal != authority.authority_seal
            or private_seal != dynamics_seal(authority.grid_authority)
        ):
            raise value_error_type("dynamics-grid immutable guard drifted")
        dynamics_property_guard(value, dynamics_property_view)
        return authority

    def bridge_property_view(value):
        authority = bridge_shallow(value)
        return bridge_view_type(
            grid_authority=clone(authority.grid_authority),
            parent=authority.parent,
            materialization=authority.materialization,
            factory=authority.factory,
            factory_binding=clone(authority.factory_binding),
        )

    def dynamics_property_view(value):
        authority = dynamics_shallow(value)
        return dynamics_view_type(
            grid_authority=clone(authority.grid_authority),
            parent=authority.parent,
            transition=authority.transition,
            metric_attestation=authority.metric_attestation,
        )

    def register_bridge(body, parent, materialization, factory, binding):
        seal = bridge_seal(body)
        wrapper = object_type.__new__(bridge_wrapper_type)
        object_type.__setattr__(
            wrapper,
            "_VerifiedBridgeGridAuthorityV3__grid_authority",
            clone(body),
        )
        object_type.__setattr__(
            wrapper,
            "_VerifiedBridgeGridAuthorityV3__authority_seal",
            seal,
        )
        authority = bridge_record_type(
            clone(body),
            parent,
            materialization,
            factory,
            clone(binding),
            seal,
        )
        identity = id_fn(wrapper)

        def remove_stale(reference, wrapper_id=identity):
            with bridge_lock:
                observed = bridge_registry.get(wrapper_id)
                if observed is not None and observed[0] is reference:
                    del bridge_registry[wrapper_id]

        reference = weak_reference(wrapper, remove_stale)
        with bridge_lock:
            current = bridge_registry.get(identity)
            if current is not None and current[0]() is not None:
                raise runtime_error_type("bridge-grid identity collision")
            bridge_registry[identity] = (reference, authority)
        bridge_property_binder(
            wrapper,
            bridge_property_view,
            token=bridge_property_token,
        )
        return wrapper

    def register_dynamics(
        body,
        parent,
        materialization,
        transition,
        metric,
    ):
        seal = dynamics_seal(body)
        wrapper = object_type.__new__(dynamics_wrapper_type)
        object_type.__setattr__(
            wrapper,
            "_VerifiedDynamicsGridAuthorityV3__grid_authority",
            clone(body),
        )
        object_type.__setattr__(
            wrapper,
            "_VerifiedDynamicsGridAuthorityV3__authority_seal",
            seal,
        )
        authority = dynamics_record_type(
            clone(body),
            parent,
            materialization,
            transition,
            metric,
            seal,
        )
        identity = id_fn(wrapper)

        def remove_stale(reference, wrapper_id=identity):
            with dynamics_lock:
                observed = dynamics_registry.get(wrapper_id)
                if observed is not None and observed[0] is reference:
                    del dynamics_registry[wrapper_id]

        reference = weak_reference(wrapper, remove_stale)
        with dynamics_lock:
            current = dynamics_registry.get(identity)
            if current is not None and current[0]() is not None:
                raise runtime_error_type("dynamics-grid identity collision")
            dynamics_registry[identity] = (reference, authority)
        dynamics_property_binder(
            wrapper,
            dynamics_property_view,
            token=dynamics_property_token,
        )
        return wrapper

    def derive_bridge(parent, materialization, factory_role):
        view, factory, binding, protocol, grid = bridge_components(
            parent,
            materialization,
            factory_role,
        )
        provisional = bridge_body_type(
            bridge_schema,
            clone(view.materialization),
            clone(binding),
            clone(protocol),
            clone(grid),
            "0" * 64,
        )
        body = replace_fn(
            provisional,
            grid_authority_sha=sha_builder(bridge_payload(provisional)),
        )
        return register_bridge(
            body,
            parent,
            materialization,
            factory,
            binding,
        )

    def derive_dynamics(parent, transition, metric):
        transition_view, metric_view, protocol, grid = dynamics_components(
            parent,
            transition,
            metric,
        )
        provisional = dynamics_body_type(
            dynamics_schema,
            clone(transition_view.transition_authority),
            clone(metric_view.attestation),
            clone(protocol),
            clone(grid),
            "0" * 64,
        )
        body = replace_fn(
            provisional,
            grid_authority_sha=sha_builder(dynamics_payload(provisional)),
        )
        return register_dynamics(
            body,
            parent,
            transition_view.materialization,
            transition,
            metric,
        )

    def reverify_bridge(bridge_grid):
        authority = bridge_shallow(bridge_grid)
        view, factory, binding, protocol, grid = bridge_components(
            authority.parent,
            authority.materialization,
            authority.grid_authority.factory_binding.branch,
        )
        bridge_verifier(
            authority.grid_authority.bridge_grid,
            view.materialization.current_application_authority.spatial_shape,
            binding.support_offsets,
        )
        provisional = bridge_body_type(
            bridge_schema,
            clone(view.materialization),
            clone(binding),
            clone(protocol),
            clone(grid),
            "0" * 64,
        )
        expected = replace_fn(
            provisional,
            grid_authority_sha=sha_builder(bridge_payload(provisional)),
        )
        if expected != authority.grid_authority:
            raise value_error_type("bridge-grid capability replay drifted")
        return bridge_view_type(
            clone(authority.grid_authority),
            authority.parent,
            authority.materialization,
            factory,
            clone(binding),
        )

    def reverify_dynamics(dynamics_grid):
        authority = dynamics_shallow(dynamics_grid)
        transition_view, metric_view, protocol, grid = dynamics_components(
            authority.parent,
            authority.transition,
            authority.metric_attestation,
        )
        dynamics_verifier(
            authority.grid_authority.dynamics_grid,
            transition_view.transition_authority.measured_transition.support_offsets,
            metric_view.attestation.metric_support_offsets,
        )
        provisional = dynamics_body_type(
            dynamics_schema,
            clone(transition_view.transition_authority),
            clone(metric_view.attestation),
            clone(protocol),
            clone(grid),
            "0" * 64,
        )
        expected = replace_fn(
            provisional,
            grid_authority_sha=sha_builder(dynamics_payload(provisional)),
        )
        if expected != authority.grid_authority:
            raise value_error_type("dynamics-grid capability replay drifted")
        return dynamics_view_type(
            clone(authority.grid_authority),
            authority.parent,
            authority.transition,
            authority.metric_attestation,
        )

    def verify_pair(bridge_grid, dynamics_grid):
        if (
            type_fn(bridge_grid) is not bridge_wrapper_type
            or type_fn(dynamics_grid) is not dynamics_wrapper_type
        ):
            raise type_error_type("runtime grid pair requires exact live capabilities")
        try:
            bridge_view = reverify_bridge(bridge_grid)
            dynamics_view = reverify_dynamics(dynamics_grid)
        except failure_type:
            raise
        except replay_error_types as exc:
            fail("BRANCH_JOIN_FAILED", str_fn(exc), exc)
        dynamics_authority = dynamics_shallow(dynamics_grid)
        if bridge_view.parent is not dynamics_view.parent:
            fail("CROSS_PARENT_ROOT", "runtime grid pair Parent identity drifted")
        if bridge_view.materialization is not dynamics_authority.materialization:
            fail(
                "BRANCH_JOIN_FAILED",
                "runtime grid pair materialization identity drifted",
            )
        bridge_role = bridge_view.grid_authority.factory_binding.branch
        dynamics_role = dynamics_view.grid_authority.transition_authority.measured_transition.factory_role
        if bridge_role != dynamics_role:
            fail("BRANCH_JOIN_FAILED", "runtime grid pair roles differ")
        if (
            bridge_view.grid_authority.materialization
            != dynamics_view.grid_authority.transition_authority.materialization
            or bridge_view.grid_authority.factory_binding
            != dynamics_view.grid_authority.transition_authority.factory_binding
        ):
            fail("BRANCH_JOIN_FAILED", "runtime grid pair recursive roots drifted")
        return bridge_grid, dynamics_grid

    return _RuntimeGridsV3Graph(
        derive_bridge,
        derive_dynamics,
        verify_pair,
        reverify_bridge,
        reverify_dynamics,
    )


_PRODUCTION_GRAPH = _make_runtime_grids_v3_graph(_ISSUANCE_TOKEN)


def _make_public_apis(derive_bridge_fn, derive_dynamics_fn, verify_pair_fn):
    def derive_bridge_grid_authority_v3(parent, materialization, factory_role):
        return derive_bridge_fn(parent, materialization, factory_role)

    def derive_dynamics_grid_authority_v3(parent, transition, metric):
        return derive_dynamics_fn(parent, transition, metric)

    def verify_runtime_grid_authorities_v3(bridge_grid, dynamics_grid):
        return verify_pair_fn(bridge_grid, dynamics_grid)

    return (
        derive_bridge_grid_authority_v3,
        derive_dynamics_grid_authority_v3,
        verify_runtime_grid_authorities_v3,
    )


(
    derive_bridge_grid_authority_v3,
    derive_dynamics_grid_authority_v3,
    verify_runtime_grid_authorities_v3,
) = _make_public_apis(
    _PRODUCTION_GRAPH.derive_bridge,
    _PRODUCTION_GRAPH.derive_dynamics,
    _PRODUCTION_GRAPH.verify_pair,
)


def _make_private_reverifiers(bridge_reverify_fn, dynamics_reverify_fn):
    def _reverify_verified_bridge_grid_authority_v3(bridge_grid):
        return bridge_reverify_fn(bridge_grid)

    def _reverify_verified_dynamics_grid_authority_v3(dynamics_grid):
        return dynamics_reverify_fn(dynamics_grid)

    return (
        _reverify_verified_bridge_grid_authority_v3,
        _reverify_verified_dynamics_grid_authority_v3,
    )


(
    _reverify_verified_bridge_grid_authority_v3,
    _reverify_verified_dynamics_grid_authority_v3,
) = _make_private_reverifiers(
    _PRODUCTION_GRAPH.reverify_bridge,
    _PRODUCTION_GRAPH.reverify_dynamics,
)


__all__ = (
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
