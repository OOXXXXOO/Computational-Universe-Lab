"""Parent-v3 full-state transition authority for the current C19 branch pair."""

from __future__ import annotations

import copy
import re
import threading
import weakref
from dataclasses import dataclass, fields as dataclass_fields, replace
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
from .dynamics import (
    FrozenComplexTensor,
    MeasuredTransition,
    _MeasuredTransitionSupportFailure,
    _assert_positive_bit_zero,
    _assert_no_wrap,
    _canonical_transition_support,
    _measure_bound_realspace_transition,
    _outside_support_mask,
    frozen_tensor_array,
    measured_transition_payload,
    transition_support_payload,
)
from .evidence import canonical_sha
from .parent_v3_application_prestructure import (
    ParentV3ApplicationPrestructure,
    VerifiedParentV3ApplicationPrestructure,
    _issue_parent_v3_application_prestructure,
    _reverify_verified_parent_v3_application_prestructure,
    _verify_parent_v3_application_prestructure,
    parent_v3_application_prestructure_payload,
)


TRANSITION_AUTHORITY_V3_SCHEMA_VERSION = "v3m0.transition-authority.v3"
_FAILURE_REASON_IDS = frozenset(
    (
        "MATERIALIZATION_INVALID",
        "PRESTRUCTURE_INVALID",
        "EXECUTOR_FAILED",
        "TRANSITION_MEASUREMENT_FAILED",
        "SUPPORT_INVALID",
        "BRANCH_JOIN_FAILED",
        "CROSS_PARENT_ROOT",
    )
)
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


def _make_transition_failure_initializer(reason_ids, text_validator, base_error):
    def __init__(self, reason_id: str, detail: str) -> None:
        if reason_id not in reason_ids:
            raise base_error("transition-authority-v3 reason is not frozen")
        self.reason_id = reason_id
        self.detail = text_validator(detail, "transition-authority-v3 detail")
        base_error.__init__(self, f"{reason_id}: {detail}")

    return __init__


class TransitionAuthorityV3Failure(ValueError):
    """Typed fail-closed result at the Parent-v3 transition boundary."""

    __init__ = _make_transition_failure_initializer(
        _FAILURE_REASON_IDS,
        _text,
        ValueError,
    )


@dataclass(frozen=True)
class TransitionAuthorityV3:
    transition_authority_schema_version: str
    materialization: ApplicationScenarioMaterializationV3
    factory_binding: FactoryBranchBindingV3
    prestructure_authority: ParentV3ApplicationPrestructure
    measured_transition: MeasuredTransition
    transition_authority_sha: str

    def __post_init__(
        self,
        *,
        _schema=TRANSITION_AUTHORITY_V3_SCHEMA_VERSION,
        _sha_validator=_sha,
    ) -> None:
        if self.transition_authority_schema_version != _schema:
            raise ValueError("transition authority schema drifted")
        _sha_validator(self.transition_authority_sha, "transition_authority_sha")


def _transition_authority_v3_payload_impl(
    transition: object,
    *,
    body_type: type,
    record_validator,
    materialization_payload_builder,
    binding_payload_builder,
    prestructure_payload_builder,
    measured_payload_builder,
) -> dict[str, object]:
    record_validator(transition, body_type, "transition authority v3")
    materialization = transition.materialization
    binding = transition.factory_binding
    prestructure = transition.prestructure_authority
    measured = transition.measured_transition
    return {
        "transition_authority_schema_version": (
            transition.transition_authority_schema_version
        ),
        "materialization": {
            **materialization_payload_builder(materialization),
            "materialization_sha": materialization.materialization_sha,
        },
        "factory_binding": {
            **binding_payload_builder(binding),
            "binding_sha": binding.binding_sha,
        },
        "prestructure_authority": {
            **prestructure_payload_builder(prestructure),
            "prestructure_authority_sha": prestructure.prestructure_authority_sha,
        },
        "measured_transition": {
            **measured_payload_builder(measured),
            "transition_sha": measured.transition_sha,
        },
    }


def _make_transition_authority_v3_payload_api(
    payload_impl,
    *,
    body_type,
    record_validator,
    materialization_payload_builder,
    binding_payload_builder,
    prestructure_payload_builder,
    measured_payload_builder,
):
    def transition_authority_v3_payload(transition) -> dict[str, object]:
        return payload_impl(
            transition,
            body_type=body_type,
            record_validator=record_validator,
            materialization_payload_builder=materialization_payload_builder,
            binding_payload_builder=binding_payload_builder,
            prestructure_payload_builder=prestructure_payload_builder,
            measured_payload_builder=measured_payload_builder,
        )

    return transition_authority_v3_payload


transition_authority_v3_payload = _make_transition_authority_v3_payload_api(
    _transition_authority_v3_payload_impl,
    body_type=TransitionAuthorityV3,
    record_validator=_exact_record,
    materialization_payload_builder=application_scenario_materialization_v3_payload,
    binding_payload_builder=factory_branch_binding_v3_payload,
    prestructure_payload_builder=parent_v3_application_prestructure_payload,
    measured_payload_builder=measured_transition_payload,
)


@dataclass(frozen=True)
class _VerifiedTransitionAuthorityV3View:
    transition_authority: TransitionAuthorityV3
    parent: object
    materialization: VerifiedV3M0ApplicationScenarioMaterializationV3
    factory: object
    prestructure: VerifiedParentV3ApplicationPrestructure


@dataclass(frozen=True)
class _TransitionAuthorityV3Record:
    transition_authority: TransitionAuthorityV3
    parent: object
    materialization: object
    factory: object
    prestructure: object
    authority_seal: str


class VerifiedTransitionAuthorityV3:
    """Opaque transition whose full-state impulses replay through B2."""

    __slots__ = (
        "__transition_authority",
        "__authority_seal",
        "__weakref__",
    )

    def __init__(self) -> None:
        raise TypeError("transition authority v3 is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("transition authority v3 is immutable")


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
                raise ValueError("transition property identity is not live")
            resolver = current[1]
        if expected_resolver is not None and resolver is not expected_resolver:
            raise ValueError("transition property resolver drifted")
        return resolver

    def resolve(value):
        return require_binding(value)(value)

    def bind(value, resolver, *, token):
        if token is not binding_token:
            raise TypeError("transition property binding token mismatch")
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
                raise RuntimeError("transition property identity collision")
            bindings[identity] = (reference, resolver)

    return resolve, bind, require_binding


(
    _resolve_transition_property,
    _bind_transition_property,
    _require_transition_property_binding,
) = _make_property_dispatcher(_PROPERTY_BINDING_TOKEN)


def _make_transition_property(resolver):
    def transition_authority(value):
        return resolver(value).transition_authority

    return property(transition_authority)


VerifiedTransitionAuthorityV3.transition_authority = _make_transition_property(
    _resolve_transition_property
)


class _TransitionAuthorityV3Graph(NamedTuple):
    issue: object
    verify: object
    verify_pair: object
    reverify: object


def _make_transition_authority_v3_graph(
    issuance_token: object,
) -> _TransitionAuthorityV3Graph:
    if issuance_token is not _ISSUANCE_TOKEN:
        raise TypeError("transition-authority-v3 graph token mismatch")

    materialization_failure_type = ApplicationMaterializationV3Failure
    materialization_type = ApplicationScenarioMaterializationV3
    binding_type = FactoryBranchBindingV3
    verified_materialization_type = VerifiedV3M0ApplicationScenarioMaterializationV3
    materialization_requirer = (
        _require_v3m0_application_scenario_materialization_v3_for_parent
    )
    prestructure_type = ParentV3ApplicationPrestructure
    verified_prestructure_type = VerifiedParentV3ApplicationPrestructure
    prestructure_issuer = _issue_parent_v3_application_prestructure
    prestructure_verifier = _verify_parent_v3_application_prestructure
    prestructure_reverifier = _reverify_verified_parent_v3_application_prestructure
    measurement_builder = _measure_bound_realspace_transition
    support_failure_type = _MeasuredTransitionSupportFailure
    measured_type = MeasuredTransition
    tensor_type = FrozenComplexTensor
    materialization_payload_builder = application_scenario_materialization_v3_payload
    binding_payload_builder = factory_branch_binding_v3_payload
    prestructure_payload_builder = parent_v3_application_prestructure_payload
    measured_payload_builder = measured_transition_payload
    sha_builder = canonical_sha
    body_type = TransitionAuthorityV3
    wrapper_type = VerifiedTransitionAuthorityV3
    view_type = _VerifiedTransitionAuthorityV3View
    authority_record_type = _TransitionAuthorityV3Record
    failure_type = TransitionAuthorityV3Failure
    schema_version = TRANSITION_AUTHORITY_V3_SCHEMA_VERSION
    exact_record_validator = _exact_record
    body_payload_impl = _transition_authority_v3_payload_impl
    support_mask_builder = _outside_support_mask
    positive_zero_validator = _assert_positive_bit_zero
    no_wrap_validator = _assert_no_wrap
    canonical_support_builder = _canonical_transition_support
    support_payload_builder = transition_support_payload
    tensor_array_builder = frozen_tensor_array
    clone = copy.deepcopy
    replace_fn = replace
    type_fn = type
    id_fn = id
    weak_reference = weakref.ref
    property_binder = _bind_transition_property
    property_binding_guard = _require_transition_property_binding
    property_binding_token = _PROPERTY_BINDING_TOKEN
    registry: dict[int, tuple[object, object]] = {}
    lock = threading.RLock()

    def fail(reason_id: str, detail: str, cause: BaseException | None = None):
        failure = failure_type(reason_id, detail)
        if cause is None:
            raise failure
        raise failure from cause

    def body_payload(body):
        return body_payload_impl(
            body,
            body_type=body_type,
            record_validator=exact_record_validator,
            materialization_payload_builder=materialization_payload_builder,
            binding_payload_builder=binding_payload_builder,
            prestructure_payload_builder=prestructure_payload_builder,
            measured_payload_builder=measured_payload_builder,
        )

    def require_materialization(parent, materialization):
        try:
            if type_fn(materialization) is not verified_materialization_type:
                raise TypeError("transition requires exact live B2 materialization")
            view = materialization_requirer(parent, materialization)
            if type_fn(view.materialization) is not materialization_type:
                raise TypeError("B2 owner seam returned the wrong raw body")
            materialization_payload_builder(view.materialization)
            return view
        except materialization_failure_type as exc:
            reason = (
                "CROSS_PARENT_ROOT"
                if exc.reason_id == "CROSS_PARENT_ROOT"
                else "MATERIALIZATION_INVALID"
            )
            fail(reason, exc.detail, exc)
        except failure_type:
            raise
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("MATERIALIZATION_INVALID", str(exc), exc)

    def require_prestructure_issue(parent, materialization, factory_role):
        try:
            result = prestructure_issuer(parent, materialization, factory_role)
            if type_fn(result) is not verified_prestructure_type:
                raise TypeError("prestructure issuer returned wrong capability type")
            return result
        except failure_type:
            raise
        except materialization_failure_type as exc:
            reason = (
                "CROSS_PARENT_ROOT"
                if exc.reason_id == "CROSS_PARENT_ROOT"
                else "MATERIALIZATION_INVALID"
            )
            fail(reason, exc.detail, exc)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("PRESTRUCTURE_INVALID", str(exc), exc)

    def require_prestructure_verify(raw, parent, materialization):
        try:
            if type_fn(raw) is not prestructure_type:
                raise TypeError("transition contains wrong prestructure body type")
            result = prestructure_verifier(raw, parent, materialization)
            if type_fn(result) is not verified_prestructure_type:
                raise TypeError("prestructure verifier returned wrong capability type")
            return result
        except failure_type:
            raise
        except materialization_failure_type as exc:
            reason = (
                "CROSS_PARENT_ROOT"
                if exc.reason_id == "CROSS_PARENT_ROOT"
                else "MATERIALIZATION_INVALID"
            )
            fail(reason, exc.detail, exc)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("PRESTRUCTURE_INVALID", str(exc), exc)

    def require_prestructure_view(prestructure, parent, materialization):
        try:
            view = prestructure_reverifier(prestructure)
            if view.parent is not parent:
                fail("CROSS_PARENT_ROOT", "prestructure belongs to another Parent")
            if view.materialization is not materialization:
                fail(
                    "MATERIALIZATION_INVALID",
                    "prestructure belongs to another materialization",
                )
            return view
        except failure_type:
            raise
        except materialization_failure_type as exc:
            reason = (
                "CROSS_PARENT_ROOT"
                if exc.reason_id == "CROSS_PARENT_ROOT"
                else "MATERIALIZATION_INVALID"
            )
            fail(reason, exc.detail, exc)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("PRESTRUCTURE_INVALID", str(exc), exc)

    def selected_branch(materialization_view, factory_role):
        raw = materialization_view.materialization
        if factory_role == "actual":
            return materialization_view.actual_factory, raw.actual_factory_binding
        if factory_role == "matched_ablated":
            return (
                materialization_view.matched_ablated_factory,
                raw.matched_ablated_factory_binding,
            )
        fail("BRANCH_JOIN_FAILED", "transition factory role is not frozen")

    def join_branch(materialization_view, prestructure_view, factory_role):
        current_factory, binding = selected_branch(
            materialization_view,
            factory_role,
        )
        if type_fn(binding) is not binding_type:
            fail("BRANCH_JOIN_FAILED", "B2 branch binding has wrong exact type")
        binding_payload_builder(binding)
        prestructure_body = prestructure_view.prestructure
        current_body = current_factory.factory
        prestructure_factory_body = prestructure_view.factory.factory
        if (
            prestructure_body.factory_role != factory_role
            or prestructure_body.factory_binding != binding
            or prestructure_body.factory_sha != binding.factory.factory_sha
            or binding.branch != factory_role
            or current_factory.role != factory_role
            or prestructure_view.factory.role != factory_role
            or current_body != binding.factory
            or prestructure_factory_body != binding.factory
            or current_body.factory_sha != prestructure_body.factory_sha
        ):
            fail("BRANCH_JOIN_FAILED", "transition branch lineage drifted")
        if (
            prestructure_body.parent_freeze_v3_sha != binding.parent_freeze_v3_sha
            or prestructure_body.materialization_sha
            != materialization_view.materialization.materialization_sha
        ):
            fail("CROSS_PARENT_ROOT", "transition branch Parent root drifted")
        return prestructure_view.factory, binding

    def measure(factory, prestructure_body):
        try:
            measured = measurement_builder(
                factory,
                parent_freeze_sha=prestructure_body.parent_freeze_v3_sha,
                prestructure_authority_sha=(
                    prestructure_body.prestructure_authority_sha
                ),
            )
        except failure_type:
            raise
        except support_failure_type as exc:
            fail("SUPPORT_INVALID", str(exc), exc)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("EXECUTOR_FAILED", str(exc), exc)
        try:
            if type_fn(measured) is not measured_type:
                raise TypeError("measurement returned the wrong exact record type")
            exact_record_validator(
                measured,
                measured_type,
                "measured transition",
            )
            exact_record_validator(
                measured.kernel,
                tensor_type,
                "measured transition kernel",
            )
            measured.__post_init__()
            if measured.transition_sha != sha_builder(
                measured_payload_builder(measured)
            ):
                raise ValueError("fresh measured transition SHA drifted")
            require_declared_support(
                measured,
                prestructure_body.factory_binding.support_offsets,
            )
            return measured
        except failure_type:
            raise
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("TRANSITION_MEASUREMENT_FAILED", str(exc), exc)

    def require_recursive_parent_roots(transition, materialization_view):
        expected_root = materialization_view.materialization.permit.parent_freeze_v3_sha
        try:
            observed_roots = (
                transition.materialization.permit.parent_freeze_v3_sha,
                transition.materialization.permit.calibration.parent_freeze_v3_sha,
                *(
                    ref.parent_freeze_v3_sha
                    for ref in transition.materialization.permit.calibration.calibration_control_replay_refs
                ),
                transition.materialization.actual_factory_binding.parent_freeze_v3_sha,
                transition.materialization.matched_ablated_factory_binding.parent_freeze_v3_sha,
                transition.factory_binding.parent_freeze_v3_sha,
                transition.prestructure_authority.parent_freeze_v3_sha,
                transition.prestructure_authority.factory_binding.parent_freeze_v3_sha,
                transition.measured_transition.parent_freeze_sha,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            fail("CROSS_PARENT_ROOT", str(exc), exc)
        if any(root != expected_root for root in observed_roots):
            fail("CROSS_PARENT_ROOT", "recursive transition Parent-v3 root drifted")

    def require_declared_support(measured, factory_support):
        try:
            expected_support = canonical_support_builder(factory_support)
            if measured.support_offsets != expected_support:
                raise ValueError("transition support sign differs from live B2 binding")
            no_wrap_validator(measured.spatial_shape, expected_support)
            expected_support_sha = sha_builder(
                support_payload_builder(
                    expected_support,
                    measured.spatial_shape,
                    measured.channel_order,
                    measured.state_basis_convention_id,
                )
            )
            if measured.support_sha != expected_support_sha:
                raise ValueError("transition support SHA drifted")
            outside = support_mask_builder(
                measured.spatial_shape,
                expected_support,
            )
            kernel = tensor_array_builder(measured.kernel)
            positive_zero_validator(kernel[:, :, outside])
        except (AttributeError, IndexError, RuntimeError, TypeError, ValueError) as exc:
            fail("SUPPORT_INVALID", str(exc), exc)

    def derive(
        parent,
        materialization,
        factory_role,
        raw_prestructure=None,
        materialization_view=None,
    ):
        if materialization_view is None:
            materialization_view = require_materialization(parent, materialization)
        if raw_prestructure is None:
            prestructure = require_prestructure_issue(
                parent,
                materialization,
                factory_role,
            )
        else:
            prestructure = require_prestructure_verify(
                raw_prestructure,
                parent,
                materialization,
            )
        prestructure_view = require_prestructure_view(
            prestructure,
            parent,
            materialization,
        )
        factory, binding = join_branch(
            materialization_view,
            prestructure_view,
            factory_role,
        )
        measured = measure(
            factory,
            prestructure_view.prestructure,
        )
        provisional = body_type(
            transition_authority_schema_version=schema_version,
            materialization=clone(materialization_view.materialization),
            factory_binding=clone(binding),
            prestructure_authority=clone(prestructure_view.prestructure),
            measured_transition=clone(measured),
            transition_authority_sha="0" * 64,
        )
        body = replace_fn(
            provisional,
            transition_authority_sha=sha_builder(body_payload(provisional)),
        )
        return body, factory, prestructure

    def authority_seal(body):
        return sha_builder(
            {
                "authority_kind": "parent-v3-transition-live-v3",
                "transition_authority_sha": body.transition_authority_sha,
                "parent_freeze_v3_sha": (
                    body.prestructure_authority.parent_freeze_v3_sha
                ),
                "factory_sha": body.prestructure_authority.factory_sha,
                "factory_role": body.prestructure_authority.factory_role,
            }
        )

    def shallow(value):
        if type_fn(value) is not wrapper_type:
            raise TypeError("value must be an exact live transition capability")
        with lock:
            current = registry.get(id_fn(value))
            if current is None or current[0]() is not value:
                raise ValueError("transition capability identity is not live")
            authority = current[1]
        try:
            private_body = object.__getattribute__(
                value,
                "_VerifiedTransitionAuthorityV3__transition_authority",
            )
            private_seal = object.__getattribute__(
                value,
                "_VerifiedTransitionAuthorityV3__authority_seal",
            )
        except AttributeError as exc:
            raise ValueError("transition capability is incomplete") from exc
        if (
            private_body != authority.transition_authority
            or private_seal != authority.authority_seal
            or private_seal != authority_seal(authority.transition_authority)
        ):
            raise ValueError("transition capability immutable guard drifted")
        property_binding_guard(value, property_view)
        return authority

    def property_view(value):
        authority = shallow(value)
        return view_type(
            transition_authority=clone(authority.transition_authority),
            parent=authority.parent,
            materialization=authority.materialization,
            factory=authority.factory,
            prestructure=authority.prestructure,
        )

    def register(body, parent, materialization, factory, prestructure):
        seal = authority_seal(body)
        wrapper = object.__new__(wrapper_type)
        object.__setattr__(
            wrapper,
            "_VerifiedTransitionAuthorityV3__transition_authority",
            clone(body),
        )
        object.__setattr__(
            wrapper,
            "_VerifiedTransitionAuthorityV3__authority_seal",
            seal,
        )
        authority = authority_record_type(
            transition_authority=clone(body),
            parent=parent,
            materialization=materialization,
            factory=factory,
            prestructure=prestructure,
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
                raise RuntimeError("transition capability identity collision")
            registry[identity] = (reference, authority)
        property_binder(wrapper, property_view, token=property_binding_token)
        return wrapper

    def issue(parent, materialization, factory_role):
        if factory_role not in ("actual", "matched_ablated"):
            fail("BRANCH_JOIN_FAILED", "transition factory role is not frozen")
        body, factory, prestructure = derive(
            parent,
            materialization,
            factory_role,
        )
        return register(body, parent, materialization, factory, prestructure)

    def verify(transition, parent, materialization):
        if type_fn(transition) is not body_type:
            raise TypeError("transition must be an exact raw authority body")
        try:
            transition.__post_init__()
            if transition.transition_authority_sha != sha_builder(
                body_payload(transition)
            ):
                fail(
                    "TRANSITION_MEASUREMENT_FAILED",
                    "transition authority SHA does not match complete body",
                )
        except failure_type:
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            fail("TRANSITION_MEASUREMENT_FAILED", str(exc), exc)
        try:
            exact_record_validator(
                transition.measured_transition,
                measured_type,
                "measured transition",
            )
            exact_record_validator(
                transition.measured_transition.kernel,
                tensor_type,
                "measured transition kernel",
            )
            transition.measured_transition.__post_init__()
        except (AttributeError, TypeError, ValueError) as exc:
            fail("TRANSITION_MEASUREMENT_FAILED", str(exc), exc)
        materialization_view = require_materialization(parent, materialization)
        require_recursive_parent_roots(transition, materialization_view)
        role = transition.prestructure_authority.factory_role
        expected, factory, prestructure = derive(
            parent,
            materialization,
            role,
            raw_prestructure=transition.prestructure_authority,
            materialization_view=materialization_view,
        )
        candidate_measured = transition.measured_transition
        expected_measured = expected.measured_transition
        if (
            transition.prestructure_authority.parent_freeze_v3_sha
            != expected.prestructure_authority.parent_freeze_v3_sha
        ):
            fail("CROSS_PARENT_ROOT", "transition Parent-v3 root drifted")
        if transition.materialization != expected.materialization:
            fail("MATERIALIZATION_INVALID", "transition materialization drifted")
        if (
            transition.factory_binding != expected.factory_binding
            or candidate_measured.factory_role != role
            or candidate_measured.factory_sha
            != transition.prestructure_authority.factory_sha
            or candidate_measured.prestructure_authority_sha
            != transition.prestructure_authority.prestructure_authority_sha
        ):
            fail("BRANCH_JOIN_FAILED", "transition branch join drifted")
        if (
            candidate_measured.support_offsets != expected_measured.support_offsets
            or candidate_measured.support_sha != expected_measured.support_sha
        ):
            fail("SUPPORT_INVALID", "transition support differs from live executor")
        require_declared_support(
            candidate_measured,
            expected.factory_binding.support_offsets,
        )
        if candidate_measured != expected_measured:
            fail(
                "TRANSITION_MEASUREMENT_FAILED",
                "transition differs from fresh full-state remeasurement",
            )
        if transition != expected:
            fail("BRANCH_JOIN_FAILED", "transition recursive lineage drifted")
        return register(expected, parent, materialization, factory, prestructure)

    def reverify(transition):
        authority = shallow(transition)
        materialization_view = require_materialization(
            authority.parent,
            authority.materialization,
        )
        prestructure_view = require_prestructure_view(
            authority.prestructure,
            authority.parent,
            authority.materialization,
        )
        role = authority.transition_authority.prestructure_authority.factory_role
        factory, binding = join_branch(
            materialization_view,
            prestructure_view,
            role,
        )
        measured = measure(
            factory,
            prestructure_view.prestructure,
        )
        provisional = body_type(
            transition_authority_schema_version=schema_version,
            materialization=clone(materialization_view.materialization),
            factory_binding=clone(binding),
            prestructure_authority=clone(prestructure_view.prestructure),
            measured_transition=clone(measured),
            transition_authority_sha="0" * 64,
        )
        expected = replace_fn(
            provisional,
            transition_authority_sha=sha_builder(body_payload(provisional)),
        )
        if expected != authority.transition_authority:
            raise ValueError("transition capability replay drifted")
        return view_type(
            transition_authority=clone(authority.transition_authority),
            parent=authority.parent,
            materialization=authority.materialization,
            factory=factory,
            prestructure=authority.prestructure,
        )

    def verify_pair(
        parent,
        materialization,
        actual_transition,
        matched_ablated_transition,
    ):
        require_materialization(parent, materialization)
        if (
            type_fn(actual_transition) is not wrapper_type
            or type_fn(matched_ablated_transition) is not wrapper_type
        ):
            raise TypeError("transition pair requires exact live capabilities")
        try:
            actual_view = reverify(actual_transition)
            matched_view = reverify(matched_ablated_transition)
        except failure_type:
            raise
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            fail("BRANCH_JOIN_FAILED", str(exc), exc)
        if actual_view.parent is not parent or matched_view.parent is not parent:
            fail("CROSS_PARENT_ROOT", "transition pair Parent identity drifted")
        if actual_view.materialization is not matched_view.materialization:
            fail(
                "BRANCH_JOIN_FAILED",
                "transition branches belong to different live materializations",
            )
        if (
            actual_view.materialization is not materialization
            or matched_view.materialization is not materialization
        ):
            fail(
                "MATERIALIZATION_INVALID",
                "transition pair materialization identity drifted",
            )
        actual_role = (
            actual_view.transition_authority.prestructure_authority.factory_role
        )
        matched_role = (
            matched_view.transition_authority.prestructure_authority.factory_role
        )
        if (
            actual_role != "actual"
            or matched_role != "matched_ablated"
            or actual_transition is matched_ablated_transition
        ):
            fail("BRANCH_JOIN_FAILED", "transition pair roles are not ordered")
        actual_raw = actual_view.transition_authority
        matched_raw = matched_view.transition_authority
        if (
            actual_raw.materialization != matched_raw.materialization
            or actual_raw.prestructure_authority.parent_freeze_v3_sha
            != matched_raw.prestructure_authority.parent_freeze_v3_sha
            or actual_raw.factory_binding.branch == matched_raw.factory_binding.branch
        ):
            fail("BRANCH_JOIN_FAILED", "transition pair lineage drifted")
        return actual_transition, matched_ablated_transition

    return _TransitionAuthorityV3Graph(issue, verify, verify_pair, reverify)


_PRODUCTION_GRAPH = _make_transition_authority_v3_graph(_ISSUANCE_TOKEN)


def _make_public_apis(issue_fn, verify_fn, verify_pair_fn):
    def issue_transition_authority_v3(parent, materialization, factory_role):
        return issue_fn(parent, materialization, factory_role)

    def verify_transition_authority_v3(transition, parent, materialization):
        return verify_fn(transition, parent, materialization)

    def verify_transition_pair_v3(
        parent,
        materialization,
        actual_transition,
        matched_ablated_transition,
    ):
        return verify_pair_fn(
            parent,
            materialization,
            actual_transition,
            matched_ablated_transition,
        )

    return (
        issue_transition_authority_v3,
        verify_transition_authority_v3,
        verify_transition_pair_v3,
    )


(
    issue_transition_authority_v3,
    verify_transition_authority_v3,
    verify_transition_pair_v3,
) = _make_public_apis(
    _PRODUCTION_GRAPH.issue,
    _PRODUCTION_GRAPH.verify,
    _PRODUCTION_GRAPH.verify_pair,
)


def _make_private_reverifier(reverify_fn):
    def _reverify_verified_transition_authority_v3(transition):
        return reverify_fn(transition)

    return _reverify_verified_transition_authority_v3


_reverify_verified_transition_authority_v3 = _make_private_reverifier(
    _PRODUCTION_GRAPH.reverify
)


__all__ = (
    "TransitionAuthorityV3Failure",
    "TransitionAuthorityV3",
    "VerifiedTransitionAuthorityV3",
    "issue_transition_authority_v3",
    "transition_authority_v3_payload",
    "verify_transition_authority_v3",
    "verify_transition_pair_v3",
)
