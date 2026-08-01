"""Parent-v3 C19 prestructure authority derived from one live B2 branch."""

from __future__ import annotations

import copy
import re
import threading
import weakref
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass, replace
from enum import Enum
from types import SimpleNamespace
from typing import Literal, NamedTuple

import numpy as np

from .application_materialization_v3 import (
    ApplicationMaterializationV3Failure,
    ApplicationScenarioMaterializationV3,
    FactoryBranchBindingV3,
    VerifiedV3M0ApplicationScenarioMaterializationV3,
    _require_v3m0_application_scenario_materialization_v3_for_parent,
    application_scenario_materialization_v3_payload,
    factory_branch_binding_v3_payload,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    VerifiedFactory,
    _reverify_verified_factory,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
)


PARENT_V3_APPLICATION_PRESTRUCTURE_SCHEMA_VERSION = (
    "v3m0.parent-v3-application-prestructure.v1"
)
_C19_STATE_SCHEMA_ID = "v3m0.c19-real-canonical-state.v2"
_C19_CHANNEL_ORDER = tuple(
    channel for pair in range(10) for channel in (f"q{pair}", f"p{pair}")
)
_C19_CHANNEL_PAIRS = tuple(
    (_C19_CHANNEL_ORDER[index], _C19_CHANNEL_ORDER[index + 1])
    for index in range(0, len(_C19_CHANNEL_ORDER), 2)
)
_C19_STATE_SHAPE = (20, 8)
_C19_SPATIAL_SHAPE = (8,)
_EVIDENCE_LANE = "synthetic-classical"
_FOURIER_ADJOINT_CONVENTION_ID = "minus-k-transpose-v1"
_REALITY_CONVENTION_ID = "real-kernel-positive-zero-v1"
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()
_PROPERTY_BINDING_TOKEN = object()


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise TypeError(f"{field} must be an exact non-empty string")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _exact_record(
    value: object,
    record_type: type,
    field: str,
    *,
    _fields_builder=dataclass_fields,
) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in _fields_builder(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _wire_tree(
    value: object,
    *,
    _enum_type=Enum,
    _is_dataclass=is_dataclass,
    _fields_builder=dataclass_fields,
    _namespace_type=SimpleNamespace,
    _vars_builder=vars,
    _frozenset_builder=frozenset,
) -> object:
    def walk(current: object) -> object:
        if current is None or type(current) in (str, bool, int, float):
            return current
        if isinstance(current, _enum_type):
            return walk(current.value)
        if _is_dataclass(current):
            declared = tuple(_fields_builder(current))
            declared_names = _frozenset_builder(item.name for item in declared)
            if _frozenset_builder(_vars_builder(current)) != declared_names:
                raise ValueError("nested prestructure dataclass fields drifted")
            return {item.name: walk(getattr(current, item.name)) for item in declared}
        if isinstance(current, _namespace_type):
            return {key: walk(item) for key, item in vars(current).items()}
        if type(current) in (tuple, list):
            return [walk(item) for item in current]
        if type(current) is dict:
            return {key: walk(item) for key, item in current.items()}
        raise TypeError(f"nested prestructure wire contains {type(current).__name__}")

    return walk(value)


def _require_exact_recursive_wire(
    candidate: object,
    expected: object,
    *,
    _type=type,
    _isinstance=isinstance,
    _enum_type=Enum,
    _is_dataclass=is_dataclass,
    _fields_builder=dataclass_fields,
    _namespace_type=SimpleNamespace,
    _vars_builder=vars,
    _frozenset_builder=frozenset,
) -> None:
    def walk(current: object, reference: object) -> None:
        if _type(current) is not _type(reference):
            raise TypeError("recursive prestructure wire type drifted")
        if current is None or _type(current) in (str, bool, int, float, complex):
            return
        if _isinstance(current, _enum_type):
            return
        if _is_dataclass(current):
            fields = tuple(_fields_builder(reference))
            names = _frozenset_builder(item.name for item in fields)
            if (
                _frozenset_builder(_vars_builder(current)) != names
                or _frozenset_builder(_vars_builder(reference)) != names
            ):
                raise ValueError("recursive prestructure dataclass fields drifted")
            for item in fields:
                walk(
                    getattr(current, item.name),
                    getattr(reference, item.name),
                )
            return
        if _isinstance(current, _namespace_type):
            current_vars = _vars_builder(current)
            reference_vars = _vars_builder(reference)
            if tuple(current_vars) != tuple(reference_vars):
                raise ValueError("recursive prestructure namespace fields drifted")
            for key in current_vars:
                walk(current_vars[key], reference_vars[key])
            return
        if _type(current) in (tuple, list):
            if len(current) != len(reference):
                raise ValueError("recursive prestructure sequence length drifted")
            for current_item, reference_item in zip(current, reference):
                walk(current_item, reference_item)
            return
        if _type(current) is dict:
            if tuple(current) != tuple(reference):
                raise ValueError("recursive prestructure mapping keys drifted")
            for key in current:
                walk(current[key], reference[key])

    walk(candidate, expected)


@dataclass(frozen=True)
class ParentV3ApplicationPrestructure:
    prestructure_schema_version: str
    parent_freeze_v3_sha: str
    permit_sha: str
    materialization_sha: str
    current_application_authority_v3_sha: str
    current_scenario_authority_v3_sha: str
    current_scenario_response_contract_v3_sha: str
    factory_binding: FactoryBranchBindingV3
    factory_sha: str
    factory_role: Literal["actual", "matched_ablated"]
    ablation_pair_snapshot: object
    basis_contract: object
    evidence_lane: Literal["synthetic-classical"]
    target_spec_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    canonical_channel_pairs: tuple[tuple[str, str], ...]
    fourier_adjoint_convention_id: Literal["minus-k-transpose-v1"]
    structure_form: FrozenComplexTensor
    reality_convention_id: Literal["real-kernel-positive-zero-v1"]
    prestructure_authority_sha: str

    def __post_init__(
        self,
        *,
        _schema=PARENT_V3_APPLICATION_PRESTRUCTURE_SCHEMA_VERSION,
        _sha_validator=_sha,
        _state_schema=_C19_STATE_SCHEMA_ID,
        _channel_order=_C19_CHANNEL_ORDER,
        _channel_pairs=_C19_CHANNEL_PAIRS,
        _evidence_lane=_EVIDENCE_LANE,
        _fourier=_FOURIER_ADJOINT_CONVENTION_ID,
        _reality=_REALITY_CONVENTION_ID,
        _tensor_type=FrozenComplexTensor,
    ) -> None:
        if self.prestructure_schema_version != _schema:
            raise ValueError("Parent-v3 prestructure schema drifted")
        for name in (
            "parent_freeze_v3_sha",
            "permit_sha",
            "materialization_sha",
            "current_application_authority_v3_sha",
            "current_scenario_authority_v3_sha",
            "current_scenario_response_contract_v3_sha",
            "factory_sha",
            "target_spec_sha",
            "prestructure_authority_sha",
        ):
            _sha_validator(getattr(self, name), name)
        if self.factory_role not in ("actual", "matched_ablated"):
            raise ValueError("factory_role is not frozen")
        if self.evidence_lane != _evidence_lane:
            raise ValueError("evidence_lane is not frozen")
        if self.state_schema_id != _state_schema:
            raise ValueError("state_schema_id is not exact current C19")
        if self.channel_order != _channel_order:
            raise ValueError("channel_order is not exact current C19")
        if self.canonical_channel_pairs != _channel_pairs:
            raise ValueError("canonical_channel_pairs drifted")
        if self.fourier_adjoint_convention_id != _fourier:
            raise ValueError("Fourier adjoint convention drifted")
        if type(self.structure_form) is not _tensor_type:
            raise TypeError("structure_form must be an exact frozen tensor")
        if self.structure_form.shape != (20, 20):
            raise ValueError("structure_form must be exact 20x20 block-J")
        if self.reality_convention_id != _reality:
            raise ValueError("reality convention drifted")


def _parent_v3_application_prestructure_payload_impl(
    prestructure: object,
    *,
    body_type: type,
    record_validator,
    binding_payload_builder,
    tensor_payload_builder,
    nested_wire_builder,
) -> dict[str, object]:
    record_validator(prestructure, body_type, "Parent-v3 application prestructure")
    binding = prestructure.factory_binding
    structure = prestructure.structure_form
    return {
        "prestructure_schema_version": prestructure.prestructure_schema_version,
        "parent_freeze_v3_sha": prestructure.parent_freeze_v3_sha,
        "permit_sha": prestructure.permit_sha,
        "materialization_sha": prestructure.materialization_sha,
        "current_application_authority_v3_sha": (
            prestructure.current_application_authority_v3_sha
        ),
        "current_scenario_authority_v3_sha": (
            prestructure.current_scenario_authority_v3_sha
        ),
        "current_scenario_response_contract_v3_sha": (
            prestructure.current_scenario_response_contract_v3_sha
        ),
        "factory_binding": {
            **binding_payload_builder(binding),
            "binding_sha": binding.binding_sha,
        },
        "factory_sha": prestructure.factory_sha,
        "factory_role": prestructure.factory_role,
        "ablation_pair_snapshot": nested_wire_builder(
            prestructure.ablation_pair_snapshot
        ),
        "basis_contract": nested_wire_builder(prestructure.basis_contract),
        "evidence_lane": prestructure.evidence_lane,
        "target_spec_sha": prestructure.target_spec_sha,
        "state_schema_id": prestructure.state_schema_id,
        "channel_order": list(prestructure.channel_order),
        "canonical_channel_pairs": [
            list(pair) for pair in prestructure.canonical_channel_pairs
        ],
        "fourier_adjoint_convention_id": (prestructure.fourier_adjoint_convention_id),
        "structure_form": {
            **tensor_payload_builder(structure),
            "tensor_sha": structure.tensor_sha,
        },
        "reality_convention_id": prestructure.reality_convention_id,
    }


def _make_parent_v3_application_prestructure_payload_api(
    payload_impl,
    *,
    body_type,
    record_validator,
    binding_payload_builder,
    tensor_payload_builder,
    nested_wire_builder,
):
    def parent_v3_application_prestructure_payload(
        prestructure,
    ) -> dict[str, object]:
        return payload_impl(
            prestructure,
            body_type=body_type,
            record_validator=record_validator,
            binding_payload_builder=binding_payload_builder,
            tensor_payload_builder=tensor_payload_builder,
            nested_wire_builder=nested_wire_builder,
        )

    return parent_v3_application_prestructure_payload


parent_v3_application_prestructure_payload = (
    _make_parent_v3_application_prestructure_payload_api(
        _parent_v3_application_prestructure_payload_impl,
        body_type=ParentV3ApplicationPrestructure,
        record_validator=_exact_record,
        binding_payload_builder=factory_branch_binding_v3_payload,
        tensor_payload_builder=frozen_tensor_payload,
        nested_wire_builder=_wire_tree,
    )
)


@dataclass(frozen=True)
class _VerifiedParentV3ApplicationPrestructureView:
    prestructure: ParentV3ApplicationPrestructure
    parent: object
    materialization: VerifiedV3M0ApplicationScenarioMaterializationV3
    factory: VerifiedFactory
    factory_binding: FactoryBranchBindingV3


@dataclass(frozen=True)
class _ParentV3ApplicationPrestructureAuthority:
    prestructure: ParentV3ApplicationPrestructure
    parent: object
    materialization: object
    factory: object
    factory_binding: object
    authority_seal: str


class VerifiedParentV3ApplicationPrestructure:
    """Owner-internal live capability for one exact Parent-v3 B2 branch."""

    __slots__ = ("__prestructure", "__authority_seal", "__weakref__")

    def __init__(self) -> None:
        raise TypeError("Parent-v3 prestructure is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("Parent-v3 prestructure is immutable")


def _make_property_dispatcher(
    binding_token: object,
    *,
    _weak_reference=weakref.ref,
    _id=id,
):
    bindings: dict[int, tuple[weakref.ReferenceType[object], object]] = {}
    lock = threading.RLock()

    def require_binding(value, expected_resolver=None):
        with lock:
            current = bindings.get(_id(value))
            if current is None or current[0]() is not value:
                raise ValueError("prestructure property identity is not live")
            resolver = current[1]
        if expected_resolver is not None and resolver is not expected_resolver:
            raise ValueError("prestructure property resolver drifted")
        return resolver

    def resolve(value):
        return require_binding(value)(value)

    def bind(value, resolver, *, token):
        if token is not binding_token:
            raise TypeError("prestructure property binding token mismatch")
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
                raise RuntimeError("prestructure property identity collision")
            bindings[identity] = (reference, resolver)

    return resolve, bind, require_binding


(
    _resolve_prestructure_property,
    _bind_prestructure_property,
    _require_prestructure_property_binding,
) = _make_property_dispatcher(_PROPERTY_BINDING_TOKEN)


def _make_prestructure_property(resolver):
    def prestructure(value):
        return resolver(value).prestructure

    return property(prestructure)


VerifiedParentV3ApplicationPrestructure.prestructure = _make_prestructure_property(
    _resolve_prestructure_property
)


class _ParentV3ApplicationPrestructureGraph(NamedTuple):
    issue: object
    verify: object
    reverify: object


def _make_block_j(
    *,
    _zeros=np.zeros,
    _dtype=np.complex128,
) -> np.ndarray:
    result = _zeros((20, 20), dtype=_dtype)
    for index in range(0, 20, 2):
        result[index, index + 1] = 1.0 + 0.0j
        result[index + 1, index] = -1.0 + 0.0j
    return result


def _make_parent_v3_application_prestructure_graph(
    issuance_token: object,
) -> _ParentV3ApplicationPrestructureGraph:
    if issuance_token is not _ISSUANCE_TOKEN:
        raise TypeError("Parent-v3 prestructure graph token mismatch")

    materialization_failure_type = ApplicationMaterializationV3Failure
    materialization_type = ApplicationScenarioMaterializationV3
    binding_type = FactoryBranchBindingV3
    verified_materialization_type = VerifiedV3M0ApplicationScenarioMaterializationV3
    verified_factory_type = VerifiedFactory
    materialization_requirer = (
        _require_v3m0_application_scenario_materialization_v3_for_parent
    )
    factory_reverifier = _reverify_verified_factory
    materialization_payload_builder = application_scenario_materialization_v3_payload
    binding_payload_builder = factory_branch_binding_v3_payload
    sha_builder = canonical_sha
    tensor_freezer = freeze_complex_tensor
    tensor_array_builder = frozen_tensor_array
    tensor_payload_builder = frozen_tensor_payload
    body_type = ParentV3ApplicationPrestructure
    wrapper_type = VerifiedParentV3ApplicationPrestructure
    view_type = _VerifiedParentV3ApplicationPrestructureView
    authority_type = _ParentV3ApplicationPrestructureAuthority
    schema_version = PARENT_V3_APPLICATION_PRESTRUCTURE_SCHEMA_VERSION
    exact_record_validator = _exact_record
    body_payload_impl = _parent_v3_application_prestructure_payload_impl
    recursive_wire_guard = _require_exact_recursive_wire
    nested_wire_builder = _wire_tree
    block_j_builder = _make_block_j
    arrays_equal = np.array_equal
    clone = copy.deepcopy
    replace_fn = replace
    type_fn = type
    id_fn = id
    weak_reference = weakref.ref
    property_binder = _bind_prestructure_property
    property_binding_guard = _require_prestructure_property_binding
    property_binding_token = _PROPERTY_BINDING_TOKEN
    c19_state_schema = _C19_STATE_SCHEMA_ID
    c19_channels = _C19_CHANNEL_ORDER
    c19_pairs = _C19_CHANNEL_PAIRS
    c19_state_shape = _C19_STATE_SHAPE
    c19_spatial_shape = _C19_SPATIAL_SHAPE
    evidence_lane = _EVIDENCE_LANE
    fourier_convention = _FOURIER_ADJOINT_CONVENTION_ID
    reality_convention = _REALITY_CONVENTION_ID
    registry: dict[int, tuple[object, object]] = {}
    lock = threading.RLock()

    def body_payload(body):
        return body_payload_impl(
            body,
            body_type=body_type,
            record_validator=exact_record_validator,
            binding_payload_builder=binding_payload_builder,
            tensor_payload_builder=tensor_payload_builder,
            nested_wire_builder=nested_wire_builder,
        )

    def require_materialization(parent, materialization):
        if type_fn(materialization) is not verified_materialization_type:
            raise TypeError("prestructure requires exact live B2 materialization")
        try:
            view = materialization_requirer(parent, materialization)
        except materialization_failure_type:
            raise
        if type_fn(view.materialization) is not materialization_type:
            raise TypeError("B2 owner seam returned the wrong raw body")
        materialization_payload_builder(view.materialization)
        return view

    def derive(parent, materialization, factory_role):
        if factory_role not in ("actual", "matched_ablated"):
            raise ValueError("prestructure factory role is not frozen")
        view = require_materialization(parent, materialization)
        raw = view.materialization
        if factory_role == "actual":
            factory = view.actual_factory
            binding = raw.actual_factory_binding
        else:
            factory = view.matched_ablated_factory
            binding = raw.matched_ablated_factory_binding
        if type_fn(factory) is not verified_factory_type:
            raise TypeError("B2 returned the wrong live factory type")
        if type_fn(binding) is not binding_type:
            raise TypeError("B2 returned the wrong branch binding type")
        binding_payload_builder(binding)
        factory_view = factory_reverifier(factory)
        factory_body = factory_view.factory
        application = raw.current_application_authority
        scenario = raw.current_scenario_authority
        response = raw.current_scenario_response_contract
        basis = raw.basis_contract
        actual_binding = raw.actual_factory_binding
        matched_binding = raw.matched_ablated_factory_binding
        parent_sha = raw.permit.parent_freeze_v3_sha
        if scenario.response_contract != response:
            raise ValueError("scenario response differs from materialization response")
        if (
            binding.branch != factory_role
            or factory_view.role != factory_role
            or binding.factory != factory_body
            or binding.factory.factory_sha != factory_body.factory_sha
        ):
            raise ValueError("selected factory branch does not rejoin B2")
        if (
            actual_binding.parent_freeze_v3_sha != matched_binding.parent_freeze_v3_sha
            or actual_binding.parent_freeze_v3_sha != parent_sha
            or binding.permit_sha != raw.permit.permit_sha
            or actual_binding.permit_sha != matched_binding.permit_sha
            or actual_binding.materialization_input_sha
            != matched_binding.materialization_input_sha
        ):
            raise ValueError("B2 branch lineage roots drifted")
        if (
            application.state_schema_id != c19_state_schema
            or application.channel_order != c19_channels
            or application.state_shape != c19_state_shape
            or application.spatial_shape != c19_spatial_shape
            or factory_body.state_schema_id != c19_state_schema
            or factory_body.channel_order != c19_channels
            or factory_body.state_shape != c19_state_shape
            or factory_body.spatial_ndim != 1
            or factory_body.target_spec_sha != application.target_spec_sha
        ):
            raise ValueError("B2 branch is not exact current C19 full state")
        if (
            getattr(basis, "state_schema_id", None) != c19_state_schema
            or getattr(basis, "channel_order", None) != c19_channels
        ):
            raise ValueError("C19 basis contract drifted")
        if hasattr(basis, "state_shape") and basis.state_shape != c19_state_shape:
            raise ValueError("C19 basis state shape drifted")
        if hasattr(basis, "spatial_shape") and basis.spatial_shape != c19_spatial_shape:
            raise ValueError("C19 basis spatial shape drifted")
        structure = tensor_freezer(block_j_builder())
        provisional = body_type(
            prestructure_schema_version=schema_version,
            parent_freeze_v3_sha=parent_sha,
            permit_sha=raw.permit.permit_sha,
            materialization_sha=raw.materialization_sha,
            current_application_authority_v3_sha=(
                application.application_authority_sha
            ),
            current_scenario_authority_v3_sha=scenario.scenario_authority_sha,
            current_scenario_response_contract_v3_sha=(response.response_contract_sha),
            factory_binding=clone(binding),
            factory_sha=factory_body.factory_sha,
            factory_role=factory_role,
            ablation_pair_snapshot=clone(raw.ablation_pair_snapshot),
            basis_contract=clone(basis),
            evidence_lane=evidence_lane,
            target_spec_sha=factory_body.target_spec_sha,
            state_schema_id=factory_body.state_schema_id,
            channel_order=tuple(factory_body.channel_order),
            canonical_channel_pairs=c19_pairs,
            fourier_adjoint_convention_id=fourier_convention,
            structure_form=structure,
            reality_convention_id=reality_convention,
            prestructure_authority_sha="0" * 64,
        )
        body = replace_fn(
            provisional,
            prestructure_authority_sha=sha_builder(body_payload(provisional)),
        )
        return body, factory, binding

    def authority_seal(body):
        return sha_builder(
            {
                "authority_kind": "parent-v3-application-prestructure-live-v1",
                "prestructure_authority_sha": body.prestructure_authority_sha,
                "parent_freeze_v3_sha": body.parent_freeze_v3_sha,
                "factory_sha": body.factory_sha,
                "factory_role": body.factory_role,
            }
        )

    def shallow(value):
        if type_fn(value) is not wrapper_type:
            raise TypeError("value must be an exact live Parent-v3 prestructure")
        with lock:
            current = registry.get(id_fn(value))
            if current is None or current[0]() is not value:
                raise ValueError("Parent-v3 prestructure identity is not live")
            authority = current[1]
        try:
            private_body = object.__getattribute__(
                value,
                "_VerifiedParentV3ApplicationPrestructure__prestructure",
            )
            private_seal = object.__getattribute__(
                value,
                "_VerifiedParentV3ApplicationPrestructure__authority_seal",
            )
        except AttributeError as exc:
            raise ValueError("Parent-v3 prestructure capability is incomplete") from exc
        if (
            private_body != authority.prestructure
            or private_seal != authority.authority_seal
            or private_seal != authority_seal(authority.prestructure)
        ):
            raise ValueError("Parent-v3 prestructure immutable guard drifted")
        property_binding_guard(value, property_view)
        return authority

    def property_view(value):
        authority = shallow(value)
        return view_type(
            prestructure=clone(authority.prestructure),
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
            "_VerifiedParentV3ApplicationPrestructure__prestructure",
            clone(body),
        )
        object.__setattr__(
            wrapper,
            "_VerifiedParentV3ApplicationPrestructure__authority_seal",
            seal,
        )
        authority = authority_type(
            prestructure=clone(body),
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

        reference = weak_reference(wrapper, remove_stale)
        with lock:
            current = registry.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("Parent-v3 prestructure identity collision")
            registry[identity] = (reference, authority)
        property_binder(wrapper, property_view, token=property_binding_token)
        return wrapper

    def issue(parent, materialization, factory_role):
        body, factory, binding = derive(parent, materialization, factory_role)
        return register(body, parent, materialization, factory, binding)

    def verify(prestructure, parent, materialization):
        if type_fn(prestructure) is not body_type:
            raise TypeError("prestructure must be an exact raw Parent-v3 body")
        prestructure.__post_init__()
        if prestructure.prestructure_authority_sha != sha_builder(
            body_payload(prestructure)
        ):
            raise ValueError("prestructure SHA does not match complete body")
        expected, factory, binding = derive(
            parent,
            materialization,
            prestructure.factory_role,
        )
        recursive_wire_guard(prestructure, expected)
        if prestructure != expected:
            raise ValueError("prestructure differs from live B2 derivation")
        return register(expected, parent, materialization, factory, binding)

    def reverify(prestructure):
        authority = shallow(prestructure)
        expected, factory, binding = derive(
            authority.parent,
            authority.materialization,
            authority.prestructure.factory_role,
        )
        factory_view = factory_reverifier(factory)
        stored_factory_view = factory_reverifier(authority.factory)
        if (
            expected != authority.prestructure
            or binding != authority.factory_binding
            or factory_view.factory != stored_factory_view.factory
            or factory_view.role != stored_factory_view.role
        ):
            raise ValueError("Parent-v3 prestructure live replay drifted")
        if not arrays_equal(
            tensor_array_builder(expected.structure_form),
            block_j_builder(),
        ):
            raise ValueError("Parent-v3 prestructure block-J drifted")
        return view_type(
            prestructure=clone(authority.prestructure),
            parent=authority.parent,
            materialization=authority.materialization,
            factory=factory,
            factory_binding=clone(authority.factory_binding),
        )

    return _ParentV3ApplicationPrestructureGraph(issue, verify, reverify)


_PRODUCTION_GRAPH = _make_parent_v3_application_prestructure_graph(_ISSUANCE_TOKEN)


def _make_private_apis(issue_fn, verify_fn, reverify_fn):
    def _issue_parent_v3_application_prestructure(
        parent,
        materialization,
        factory_role,
    ):
        return issue_fn(parent, materialization, factory_role)

    def _verify_parent_v3_application_prestructure(
        prestructure,
        parent,
        materialization,
    ):
        return verify_fn(prestructure, parent, materialization)

    def _reverify_verified_parent_v3_application_prestructure(prestructure):
        return reverify_fn(prestructure)

    return (
        _issue_parent_v3_application_prestructure,
        _verify_parent_v3_application_prestructure,
        _reverify_verified_parent_v3_application_prestructure,
    )


(
    _issue_parent_v3_application_prestructure,
    _verify_parent_v3_application_prestructure,
    _reverify_verified_parent_v3_application_prestructure,
) = _make_private_apis(
    _PRODUCTION_GRAPH.issue,
    _PRODUCTION_GRAPH.verify,
    _PRODUCTION_GRAPH.reverify,
)


__all__ = (
    "ParentV3ApplicationPrestructure",
    "parent_v3_application_prestructure_payload",
)
