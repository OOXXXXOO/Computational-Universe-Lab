"""Parent-v3 C19 application/scenario materialization authority.

The records in this module are inert evidence wires.  Runtime consumers receive
only a live capability issued after the current Parent-v3 permit has been
replayed and the frozen C19 actual/matched factories have been reconstructed as
one atomic matched-ablation pair.
"""

from __future__ import annotations

import copy
import re
import threading
import weakref
from collections.abc import Callable
from dataclasses import dataclass, fields as dataclass_fields, replace
from typing import Literal

from .ablation import matched_ablation
from .application_authority_v3 import (
    CalibrationApplicationPermitV3,
    CurrentApplicationAuthorityV3,
    CurrentScenarioAuthorityV3,
    CurrentScenarioResponseContractV3,
    VerifiedCalibrationApplicationPermitV3,
    calibration_application_permit_v3_payload,
    current_application_authority_v3_payload,
    current_scenario_authority_v3_payload,
    current_scenario_response_contract_v3_payload,
    verify_calibration_application_permit_v3,
)
from .factory import (
    LinearRealspaceFactory,
    VerifiedFactory,
    _reverify_verified_factory,
    factory_payload,
    factory_support_offsets,
    verify_factory,
)
from .pair_snapshot import (
    AblationPairSnapshot,
    _pair_snapshot,
    ablation_pair_snapshot_payload,
)
from .parent_authority_v3 import VerifiedParentFreezeV3, require_current_parent_v3
from .trace import (
    ConstructionTrace,
    canonical_sha,
    construction_trace_payload,
    verify_construction_trace,
)


FACTORY_BRANCH_BINDING_V3_SCHEMA_VERSION = "v3m0.factory-branch-binding.v3"
FACTORY_BRANCH_SUPPORT_V3_SCHEMA_VERSION = "v3m0.factory-branch-support.v3"
MATERIALIZATION_INPUT_V3_SCHEMA_VERSION = "v3m0.materialization-input.v3"
APPLICATION_SCENARIO_MATERIALIZATION_V3_SCHEMA_VERSION = (
    "v3m0.application-scenario-materialization.v3"
)
C19_CONTROL_CASE_ID = "C19_FULL_POSITIVE_OBSERVER_COLLAPSE"
C19_APPLICATION_INSTANCE_ID = "v3m0.synthetic-control.c19.v2"
C19_SCENARIO_ID = "v3m0.synthetic-control.c19.v2.scenario.observer-collapse.v2"

_FAILURE_REASON_IDS = frozenset(
    (
        "PARENT_V3_UNAVAILABLE",
        "PERMIT_INVALID",
        "FACTORY_REPLAY_FAILED",
        "FACTORY_WIRE_DRIFT",
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


def _support(
    value: object,
    field: str,
    *,
    ndim: int,
) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty exact tuple")
    result: list[tuple[int, ...]] = []
    for index, offset in enumerate(value):
        if type(offset) is not tuple or len(offset) != ndim:
            raise ValueError(f"{field}[{index}] has the wrong dimension")
        if not all(type(component) is int for component in offset):
            raise TypeError(f"{field}[{index}] must contain exact ints")
        result.append(offset)
    answer = tuple(result)
    if answer != tuple(sorted(set(answer))):
        raise ValueError(f"{field} must be sorted and unique")
    return answer


class ApplicationMaterializationV3Failure(ValueError):
    """Typed fail-closed result at the Parent-v3 materialization boundary."""

    def __init__(self, reason_id: str, detail: str) -> None:
        if reason_id not in _FAILURE_REASON_IDS:
            raise ValueError("application-materialization-v3 reason is not frozen")
        self.reason_id = reason_id
        self.detail = _text(detail, "application-materialization-v3 detail")
        super().__init__(f"{reason_id}: {detail}")


@dataclass(frozen=True)
class FactoryBranchBindingV3:
    binding_schema_version: str
    parent_freeze_v3_sha: str
    permit_sha: str
    materialization_input_sha: str
    branch: Literal["actual", "matched_ablated"]
    factory: LinearRealspaceFactory
    construction_trace: ConstructionTrace
    layer_slot_ids: tuple[str, ...]
    support_offsets: tuple[tuple[int, ...], ...]
    support_sha: str
    active_step_count: int
    layer_slot_count: int
    primitive_count: int
    neutral_identity_count: int
    binding_sha: str

    def __post_init__(self) -> None:
        if self.binding_schema_version != FACTORY_BRANCH_BINDING_V3_SCHEMA_VERSION:
            raise ValueError("factory branch-binding-v3 schema drifted")
        for field in (
            "parent_freeze_v3_sha",
            "permit_sha",
            "materialization_input_sha",
            "support_sha",
            "binding_sha",
        ):
            _sha(getattr(self, field), field)
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("factory branch is not frozen")
        if type(self.factory) is not LinearRealspaceFactory:
            raise TypeError("factory has the wrong exact type")
        if type(self.construction_trace) is not ConstructionTrace:
            raise TypeError("construction_trace has the wrong exact type")
        if type(self.layer_slot_ids) is not tuple or len(self.layer_slot_ids) != 50:
            raise ValueError("layer_slot_ids must be the exact 50-slot tuple")
        if not all(type(item) is str and item for item in self.layer_slot_ids):
            raise TypeError("layer_slot_ids must contain exact non-empty strings")
        if len(set(self.layer_slot_ids)) != 50:
            raise ValueError("layer_slot_ids must be unique")
        _support(
            self.support_offsets,
            "support_offsets",
            ndim=self.factory.spatial_ndim,
        )
        for field in (
            "active_step_count",
            "layer_slot_count",
            "primitive_count",
            "neutral_identity_count",
        ):
            if type(getattr(self, field)) is not int:
                raise TypeError(f"{field} must be an exact int")
        expected = (50, 50, 50, 0) if self.branch == "actual" else (30, 50, 50, 20)
        observed = (
            self.active_step_count,
            self.layer_slot_count,
            self.primitive_count,
            self.neutral_identity_count,
        )
        if observed != expected:
            raise ValueError("factory branch literal counts drifted")


@dataclass(frozen=True)
class ApplicationScenarioMaterializationV3:
    materialization_schema_version: str
    permit: CalibrationApplicationPermitV3
    current_application_authority: CurrentApplicationAuthorityV3
    current_scenario_authority: CurrentScenarioAuthorityV3
    current_scenario_response_contract: CurrentScenarioResponseContractV3
    basis_contract: object
    construction_trace: ConstructionTrace
    ablation_pair_snapshot: AblationPairSnapshot
    actual_factory_binding: FactoryBranchBindingV3
    matched_ablated_factory_binding: FactoryBranchBindingV3
    materialization_sha: str

    def __post_init__(self) -> None:
        if self.materialization_schema_version != (
            APPLICATION_SCENARIO_MATERIALIZATION_V3_SCHEMA_VERSION
        ):
            raise ValueError("application scenario materialization-v3 schema drifted")
        if type(self.permit) is not CalibrationApplicationPermitV3:
            raise TypeError("permit has the wrong exact type")
        if (
            type(self.current_application_authority)
            is not CurrentApplicationAuthorityV3
        ):
            raise TypeError("current application authority has the wrong exact type")
        if type(self.current_scenario_authority) is not CurrentScenarioAuthorityV3:
            raise TypeError("current scenario authority has the wrong exact type")
        if (
            type(self.current_scenario_response_contract)
            is not CurrentScenarioResponseContractV3
        ):
            raise TypeError("current scenario response has the wrong exact type")
        if type(self.basis_contract) is not type(
            self.current_scenario_response_contract.basis_contract
        ):
            raise TypeError("basis contract has the wrong exact type")
        if type(self.construction_trace) is not ConstructionTrace:
            raise TypeError("construction_trace has the wrong exact type")
        if type(self.ablation_pair_snapshot) is not AblationPairSnapshot:
            raise TypeError("ablation_pair_snapshot has the wrong exact type")
        if type(self.actual_factory_binding) is not FactoryBranchBindingV3:
            raise TypeError("actual_factory_binding has the wrong exact type")
        if type(self.matched_ablated_factory_binding) is not FactoryBranchBindingV3:
            raise TypeError("matched factory binding has the wrong exact type")
        _sha(self.materialization_sha, "materialization_sha")


def factory_branch_support_v3_payload(
    branch: Literal["actual", "matched_ablated"],
    factory_sha: str,
    support_offsets: tuple[tuple[int, ...], ...],
) -> dict[str, object]:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("factory support branch is not frozen")
    _sha(factory_sha, "factory_sha")
    if type(support_offsets) is not tuple or not support_offsets:
        raise ValueError("support_offsets must be a non-empty exact tuple")
    return {
        "support_schema_version": FACTORY_BRANCH_SUPPORT_V3_SCHEMA_VERSION,
        "branch": branch,
        "factory_sha": factory_sha,
        "support_offsets": [list(item) for item in support_offsets],
    }


def _factory_record(
    factory: LinearRealspaceFactory,
    factory_payload_builder: Callable[[LinearRealspaceFactory], dict[str, object]],
) -> dict[str, object]:
    return {**factory_payload_builder(factory), "factory_sha": factory.factory_sha}


def _factory_branch_binding_v3_payload_impl(
    binding: FactoryBranchBindingV3,
    *,
    factory_payload_builder: Callable[[LinearRealspaceFactory], dict[str, object]],
    trace_payload_builder: Callable[[ConstructionTrace], dict[str, object]],
) -> dict[str, object]:
    _exact_record(binding, FactoryBranchBindingV3, "factory branch binding v3")
    return {
        "binding_schema_version": binding.binding_schema_version,
        "parent_freeze_v3_sha": binding.parent_freeze_v3_sha,
        "permit_sha": binding.permit_sha,
        "materialization_input_sha": binding.materialization_input_sha,
        "branch": binding.branch,
        "factory": _factory_record(binding.factory, factory_payload_builder),
        "construction_trace": trace_payload_builder(binding.construction_trace),
        "layer_slot_ids": list(binding.layer_slot_ids),
        "support_offsets": [list(item) for item in binding.support_offsets],
        "support_sha": binding.support_sha,
        "active_step_count": binding.active_step_count,
        "layer_slot_count": binding.layer_slot_count,
        "primitive_count": binding.primitive_count,
        "neutral_identity_count": binding.neutral_identity_count,
    }


def factory_branch_binding_v3_payload(
    binding: FactoryBranchBindingV3,
) -> dict[str, object]:
    return _factory_branch_binding_v3_payload_impl(
        binding,
        factory_payload_builder=factory_payload,
        trace_payload_builder=construction_trace_payload,
    )


def _permit_record(
    permit: CalibrationApplicationPermitV3,
    permit_payload_builder: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    return {**permit_payload_builder(permit), "permit_sha": permit.permit_sha}


def _application_record(
    application: CurrentApplicationAuthorityV3,
    payload_builder: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    return {
        **payload_builder(application),
        "application_authority_sha": application.application_authority_sha,
    }


def _scenario_record(
    scenario: CurrentScenarioAuthorityV3,
    payload_builder: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    return {
        **payload_builder(scenario),
        "scenario_authority_sha": scenario.scenario_authority_sha,
    }


def _response_record(
    response: CurrentScenarioResponseContractV3,
    payload_builder: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    return {
        **payload_builder(response),
        "response_contract_sha": response.response_contract_sha,
    }


def _basis_record(
    response: CurrentScenarioResponseContractV3,
    basis: object,
    payload_builder: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    """Serialize the direct basis field, not a convenient sibling copy."""

    shadow = replace(response, basis_contract=basis)
    payload = payload_builder(shadow)
    result = payload.get("basis_contract")
    if type(result) is not dict:
        raise TypeError("response payload omitted the exact basis contract")
    return result


def _snapshot_record(
    snapshot: AblationPairSnapshot,
    payload_builder: Callable[[AblationPairSnapshot], dict[str, object]],
) -> dict[str, object]:
    return {**payload_builder(snapshot), "snapshot_sha": snapshot.snapshot_sha}


def _application_scenario_materialization_v3_payload_impl(
    materialization: ApplicationScenarioMaterializationV3,
    *,
    permit_payload_builder: Callable[[object], dict[str, object]],
    application_payload_builder: Callable[[object], dict[str, object]],
    scenario_payload_builder: Callable[[object], dict[str, object]],
    response_payload_builder: Callable[[object], dict[str, object]],
    trace_payload_builder: Callable[[ConstructionTrace], dict[str, object]],
    snapshot_payload_builder: Callable[[AblationPairSnapshot], dict[str, object]],
    binding_payload_builder: Callable[[FactoryBranchBindingV3], dict[str, object]],
) -> dict[str, object]:
    _exact_record(
        materialization,
        ApplicationScenarioMaterializationV3,
        "application scenario materialization v3",
    )
    response_record = _response_record(
        materialization.current_scenario_response_contract,
        response_payload_builder,
    )
    return {
        "materialization_schema_version": materialization.materialization_schema_version,
        "permit": _permit_record(materialization.permit, permit_payload_builder),
        "current_application_authority": _application_record(
            materialization.current_application_authority,
            application_payload_builder,
        ),
        "current_scenario_authority": _scenario_record(
            materialization.current_scenario_authority,
            scenario_payload_builder,
        ),
        "current_scenario_response_contract": response_record,
        "basis_contract": _basis_record(
            materialization.current_scenario_response_contract,
            materialization.basis_contract,
            response_payload_builder,
        ),
        "construction_trace": trace_payload_builder(materialization.construction_trace),
        "ablation_pair_snapshot": _snapshot_record(
            materialization.ablation_pair_snapshot,
            snapshot_payload_builder,
        ),
        "actual_factory_binding": {
            **binding_payload_builder(materialization.actual_factory_binding),
            "binding_sha": materialization.actual_factory_binding.binding_sha,
        },
        "matched_ablated_factory_binding": {
            **binding_payload_builder(materialization.matched_ablated_factory_binding),
            "binding_sha": (
                materialization.matched_ablated_factory_binding.binding_sha
            ),
        },
    }


def application_scenario_materialization_v3_payload(
    materialization: ApplicationScenarioMaterializationV3,
) -> dict[str, object]:
    return _application_scenario_materialization_v3_payload_impl(
        materialization,
        permit_payload_builder=calibration_application_permit_v3_payload,
        application_payload_builder=current_application_authority_v3_payload,
        scenario_payload_builder=current_scenario_authority_v3_payload,
        response_payload_builder=current_scenario_response_contract_v3_payload,
        trace_payload_builder=construction_trace_payload,
        snapshot_payload_builder=ablation_pair_snapshot_payload,
        binding_payload_builder=factory_branch_binding_v3_payload,
    )


@dataclass(frozen=True)
class _MaterializationReplayV3:
    materialization: ApplicationScenarioMaterializationV3
    actual_factory: VerifiedFactory
    matched_ablated_factory: VerifiedFactory


@dataclass(frozen=True)
class _VerifiedApplicationMaterializationViewV3:
    materialization: ApplicationScenarioMaterializationV3
    actual_factory: VerifiedFactory
    matched_ablated_factory: VerifiedFactory
    permit: object


@dataclass(frozen=True)
class _MaterializationAuthorityV3:
    parent: object
    permit: object
    parent_freeze_v3_sha: str
    permit_sha: str
    materialization: ApplicationScenarioMaterializationV3
    actual_factory: VerifiedFactory
    matched_ablated_factory: VerifiedFactory
    authority_seal: str


class VerifiedV3M0ApplicationScenarioMaterializationV3:
    """Opaque live Parent-v3 materialization capability."""

    __slots__ = (
        "__materialization",
        "__actual_factory",
        "__matched_ablated_factory",
        "__authority_seal",
        "__weakref__",
    )

    def __init__(self) -> None:
        raise TypeError("application materialization-v3 is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("application materialization-v3 is immutable")


def _make_materialization_property_dispatcher(binding_token: object):
    """Keep property callables outside attacker-writable wrapper slots."""

    bindings: dict[int, tuple[object, Callable[[object], object]]] = {}
    lock = threading.RLock()

    def require_binding(value: object, expected_resolver=None):
        with lock:
            current = bindings.get(id(value))
            if current is None or current[0]() is not value:
                raise ValueError("materialization-v3 property identity is not live")
            resolver = current[1]
        if expected_resolver is not None and resolver is not expected_resolver:
            raise ValueError("materialization-v3 property resolver identity drifted")
        return resolver

    def resolve(value: object):
        return require_binding(value)(value)

    def bind(value: object, resolver, *, token: object):
        if token is not binding_token:
            raise TypeError("materialization-v3 property binding token mismatch")
        if not callable(resolver):
            raise TypeError("materialization-v3 property resolver must be callable")
        identity = id(value)

        def remove_stale(reference, wrapper_id=identity):
            with lock:
                observed = bindings.get(wrapper_id)
                if observed is not None and observed[0] is reference:
                    del bindings[wrapper_id]

        reference = weakref.ref(value, remove_stale)
        with lock:
            existing = bindings.get(identity)
            if existing is not None and existing[0]() is not None:
                raise RuntimeError("materialization-v3 property identity collision")
            bindings[identity] = (reference, resolver)

    return resolve, bind, require_binding


(
    _resolve_materialization_property,
    _bind_materialization_properties,
    _require_materialization_property_binding,
) = _make_materialization_property_dispatcher(_PROPERTY_BINDING_TOKEN)


def _make_closed_materialization_properties(resolver):
    def materialization(self):
        return resolver(self).materialization

    def actual_factory(self):
        return resolver(self).actual_factory

    def matched_ablated_factory(self):
        return resolver(self).matched_ablated_factory

    return (
        property(materialization),
        property(actual_factory),
        property(matched_ablated_factory),
    )


(
    VerifiedV3M0ApplicationScenarioMaterializationV3.materialization,
    VerifiedV3M0ApplicationScenarioMaterializationV3.actual_factory,
    VerifiedV3M0ApplicationScenarioMaterializationV3.matched_ablated_factory,
) = _make_closed_materialization_properties(_resolve_materialization_property)
del _make_closed_materialization_properties


@dataclass(frozen=True)
class _ApplicationMaterializationV3Graph:
    materialize: Callable[
        [object, object], VerifiedV3M0ApplicationScenarioMaterializationV3
    ]
    verify: Callable[
        [object, object, object],
        VerifiedV3M0ApplicationScenarioMaterializationV3,
    ]
    require_for_parent: Callable[
        [object, object],
        _VerifiedApplicationMaterializationViewV3,
    ]


def _make_application_materialization_v3_graph(
    issuance_token: object,
) -> _ApplicationMaterializationV3Graph:
    """Close one materialization graph over the exact six-edge dependency DAG."""

    if issuance_token is not _ISSUANCE_TOKEN:
        raise TypeError("application-materialization-v3 graph token mismatch")

    parent_type = VerifiedParentFreezeV3
    parent_reverifier = require_current_parent_v3
    permit_type = VerifiedCalibrationApplicationPermitV3
    permit_wire_type = CalibrationApplicationPermitV3
    permit_reverifier = verify_calibration_application_permit_v3
    permit_payload_builder = calibration_application_permit_v3_payload
    application_payload_builder = current_application_authority_v3_payload
    scenario_payload_builder = current_scenario_authority_v3_payload
    response_payload_builder = current_scenario_response_contract_v3_payload
    trace_verifier = verify_construction_trace
    trace_payload_builder = construction_trace_payload
    actual_factory_verifier = verify_factory
    live_factory_reverifier = _reverify_verified_factory
    support_builder = factory_support_offsets
    ablation_builder = matched_ablation
    pair_snapshotter = _pair_snapshot
    snapshot_payload_builder = ablation_pair_snapshot_payload
    sha_builder = canonical_sha
    clone = copy.deepcopy
    replace_fn = replace
    type_fn = type
    id_fn = id
    weak_reference = weakref.ref
    lock_builder = threading.RLock
    property_binder = _bind_materialization_properties
    property_binding_guard = _require_materialization_property_binding
    property_binding_token = _PROPERTY_BINDING_TOKEN
    wrapper_type = VerifiedV3M0ApplicationScenarioMaterializationV3
    binding_type = FactoryBranchBindingV3
    body_type = ApplicationScenarioMaterializationV3
    view_type = _VerifiedApplicationMaterializationViewV3
    authority_type = _MaterializationAuthorityV3
    registry: dict[int, tuple[object, _MaterializationAuthorityV3]] = {}
    lock = lock_builder()

    def fail(reason_id: str, detail: str, cause: BaseException | None = None):
        failure = ApplicationMaterializationV3Failure(reason_id, detail)
        if cause is None:
            raise failure
        raise failure from cause

    def support_payload(branch, factory_sha_value, offsets):
        if branch not in ("actual", "matched_ablated"):
            raise ValueError("factory support branch is not frozen")
        _sha(factory_sha_value, "factory_sha")
        if type_fn(offsets) is not tuple or not offsets:
            raise ValueError("support_offsets must be a non-empty exact tuple")
        return {
            "support_schema_version": FACTORY_BRANCH_SUPPORT_V3_SCHEMA_VERSION,
            "branch": branch,
            "factory_sha": factory_sha_value,
            "support_offsets": [list(item) for item in offsets],
        }

    def binding_payload(binding):
        return _factory_branch_binding_v3_payload_impl(
            binding,
            factory_payload_builder=factory_payload,
            trace_payload_builder=trace_payload_builder,
        )

    def body_payload(body):
        return _application_scenario_materialization_v3_payload_impl(
            body,
            permit_payload_builder=permit_payload_builder,
            application_payload_builder=application_payload_builder,
            scenario_payload_builder=scenario_payload_builder,
            response_payload_builder=response_payload_builder,
            trace_payload_builder=trace_payload_builder,
            snapshot_payload_builder=snapshot_payload_builder,
            binding_payload_builder=binding_payload,
        )

    def require_upstream(parent, permit):
        try:
            if type_fn(parent) is not parent_type:
                raise TypeError("materialization requires exact live Parent-v3")
            manifest = parent_reverifier(parent)
            parent_sha = _sha(
                manifest.parent_freeze_v3_sha,
                "parent_freeze_v3_sha",
            )
        except ApplicationMaterializationV3Failure:
            raise
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            fail("PARENT_V3_UNAVAILABLE", str(exc), exc)
        try:
            if type_fn(permit) is not permit_type:
                raise TypeError("materialization requires exact live permit-v3")
            verified_permit = permit_reverifier(parent, permit)
            if verified_permit is not permit:
                raise ValueError("permit reverifier changed live identity")
            permit_body = permit.permit
            if type_fn(permit_body) is not permit_wire_type:
                raise TypeError("permit body has the wrong exact type")
            permit_payload_builder(permit_body)
        except ApplicationMaterializationV3Failure:
            raise
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            fail("PERMIT_INVALID", str(exc), exc)
        if permit_body.parent_freeze_v3_sha != parent_sha:
            fail(
                "CROSS_PARENT_ROOT",
                "permit Parent-v3 root differs from the live Parent-v3",
            )
        return manifest, permit_body

    def resolve_current_application(manifest, permit_body):
        try:
            registry_values = manifest.reviewed_candidate_v3.refrozen_current_application_authorities_v3
            if type_fn(registry_values) is not tuple:
                raise TypeError("Parent-v3 current V3 registry is not an exact tuple")
            requested = permit_body.current_application_authority
            matches = tuple(
                item
                for item in registry_values
                if item.control_case_id == requested.control_case_id
                and item.application_instance_id == requested.application_instance_id
                and item.application_authority_sha
                == requested.application_authority_sha
            )
            if len(matches) != 1 or matches[0] != requested:
                raise ValueError("permit application is absent from current Parent-v3")
            application = matches[0]
            scenario = permit_body.current_scenario_authority
            response = permit_body.current_scenario_response_contract
            if (
                type_fn(application.scenario_authorities) is not tuple
                or len(application.scenario_authorities) != 1
                or application.scenario_authorities[0] != scenario
                or scenario.response_contract != response
            ):
                raise ValueError("permit scenario/response is outside the application")
            application_payload_builder(application)
            scenario_payload_builder(scenario)
            response_payload_builder(response)
            return application, scenario, response
        except ApplicationMaterializationV3Failure:
            raise
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            fail("PERMIT_INVALID", str(exc), exc)

    def require_frozen_c19_wire(application, scenario, response):
        try:
            runtime = application.runtime_construction
            actual = runtime.actual_factory
            matched = runtime.matched_factory
            if (
                actual.factory_role != "actual"
                or matched.factory_role != "matched_ablated"
            ):
                fail("BRANCH_JOIN_FAILED", "C19 factory branch roles are swapped")
            if (
                application.control_case_id != C19_CONTROL_CASE_ID
                or application.application_instance_id != C19_APPLICATION_INSTANCE_ID
                or scenario.control_case_id != C19_CONTROL_CASE_ID
                or scenario.application_instance_id != C19_APPLICATION_INSTANCE_ID
                or scenario.scenario_id != C19_SCENARIO_ID
                or response.control_case_id != C19_CONTROL_CASE_ID
                or response.application_instance_id != C19_APPLICATION_INSTANCE_ID
                or response.scenario_id != C19_SCENARIO_ID
            ):
                fail("FACTORY_WIRE_DRIFT", "materialization is not exact current C19")
            expected_counts = (50, 30, 50, 50, 50, 50, 20)
            runtime_counts = (
                runtime.actual_active_step_count,
                runtime.matched_active_step_count,
                runtime.actual_layer_slot_count,
                runtime.matched_layer_slot_count,
                runtime.actual_primitive_count,
                runtime.matched_primitive_count,
                len(runtime.ablation_manifest.replacements),
            )
            application_counts = (
                application.actual_active_step_count,
                application.matched_active_step_count,
                application.actual_layer_slot_count,
                application.matched_layer_slot_count,
                application.actual_primitive_count,
                application.matched_primitive_count,
                application.matched_neutral_identity_count,
            )
            if (
                runtime_counts != expected_counts
                or application_counts != expected_counts
            ):
                fail("FACTORY_WIRE_DRIFT", "C19 frozen literal counts drifted")
            if (
                type_fn(application.channel_order) is not tuple
                or len(application.channel_order) != 20
                or application.state_shape[0] != 20
                or actual.channel_order != application.channel_order
                or matched.channel_order != application.channel_order
                or actual.state_shape != application.state_shape
                or matched.state_shape != application.state_shape
                or actual.state_schema_id != application.state_schema_id
                or matched.state_schema_id != application.state_schema_id
            ):
                fail("FACTORY_WIRE_DRIFT", "C19 state/channel wire drifted")
            if (
                type_fn(actual.layer_slot_ids) is not tuple
                or type_fn(matched.layer_slot_ids) is not tuple
                or type_fn(actual.primitives) is not tuple
                or type_fn(matched.primitives) is not tuple
                or len(actual.layer_slot_ids) != 50
                or len(matched.layer_slot_ids) != 50
                or len(actual.primitives) != 50
                or len(matched.primitives) != 50
                or len(runtime.construction_trace.primitives) != 50
            ):
                fail("FACTORY_WIRE_DRIFT", "C19 50-slot factory wire drifted")
            actual_active = sum(
                primitive.operation_id != "neutral_identity"
                for primitive in actual.primitives
            )
            actual_neutral = sum(
                primitive.operation_id == "neutral_identity"
                for primitive in actual.primitives
            )
            matched_active = sum(
                primitive.operation_id != "neutral_identity"
                for primitive in matched.primitives
            )
            matched_neutral = sum(
                primitive.operation_id == "neutral_identity"
                for primitive in matched.primitives
            )
            if (actual_active, actual_neutral, matched_active, matched_neutral) != (
                50,
                0,
                30,
                20,
            ):
                fail("FACTORY_WIRE_DRIFT", "C19 active/neutral program drifted")
            basis = response.basis_contract
            if (
                basis != scenario.response_contract.basis_contract
                or basis.common_source_tensor != application.common_source_tensor
                or basis.common_readout_tensor != application.common_readout_tensor
                or basis.common_source_basis != application.common_source_basis
                or basis.common_readout_basis != application.common_readout_basis
                or basis.basis_contract_sha != application.basis_contract_sha
                or runtime.construction_sha != application.runtime_construction_sha
                or runtime.construction_sha != scenario.source_runtime_construction_sha
                or runtime.construction_sha != response.runtime_construction_sha
                or actual.factory_sha != application.actual_factory_sha
                or matched.factory_sha != application.matched_factory_sha
                or actual.factory_sha != response.actual_factory_sha
                or matched.factory_sha != response.matched_factory_sha
                or runtime.ablation_manifest.manifest_sha
                != application.ablation_manifest_sha
                or runtime.construction_trace.trace_sha != actual.construction_trace_sha
                or runtime.construction_trace.trace_sha
                != matched.construction_trace_sha
                or response.uses_global_fft_projection is not False
                or response.uses_per_k_time_step_projector is not False
            ):
                fail("FACTORY_WIRE_DRIFT", "C19 recursive body join drifted")
            return runtime, basis
        except ApplicationMaterializationV3Failure:
            raise
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            fail("FACTORY_WIRE_DRIFT", str(exc), exc)

    def materialization_input_payload(
        parent_sha,
        permit_body,
        application,
        scenario,
        response,
        trace,
        snapshot,
    ):
        response_record = _response_record(response, response_payload_builder)
        return {
            "materialization_input_schema_version": (
                MATERIALIZATION_INPUT_V3_SCHEMA_VERSION
            ),
            "parent_freeze_v3_sha": parent_sha,
            "permit": _permit_record(permit_body, permit_payload_builder),
            "current_application_authority_sha": application.application_authority_sha,
            "current_scenario_authority_sha": scenario.scenario_authority_sha,
            "current_scenario_response_contract_sha": response.response_contract_sha,
            "basis_contract": clone(response_record["basis_contract"]),
            "construction_trace": trace_payload_builder(trace),
            "ablation_pair_snapshot": _snapshot_record(
                snapshot,
                snapshot_payload_builder,
            ),
        }

    def make_binding(
        *,
        parent_sha,
        permit_sha,
        materialization_input_sha,
        branch,
        factory_wrapper,
        trace,
    ):
        view = live_factory_reverifier(factory_wrapper)
        factory_body = view.factory
        offsets = support_builder(factory_wrapper, 1)
        _support(offsets, "derived factory support", ndim=factory_body.spatial_ndim)
        support_sha = sha_builder(
            support_payload(branch, factory_body.factory_sha, offsets)
        )
        active = sum(
            primitive.operation_id != "neutral_identity"
            for primitive in factory_body.primitives
        )
        neutral = sum(
            primitive.operation_id == "neutral_identity"
            for primitive in factory_body.primitives
        )
        provisional = binding_type(
            binding_schema_version=FACTORY_BRANCH_BINDING_V3_SCHEMA_VERSION,
            parent_freeze_v3_sha=parent_sha,
            permit_sha=permit_sha,
            materialization_input_sha=materialization_input_sha,
            branch=branch,
            factory=clone(factory_body),
            construction_trace=clone(trace),
            layer_slot_ids=tuple(factory_body.layer_slot_ids),
            support_offsets=tuple(offsets),
            support_sha=support_sha,
            active_step_count=active,
            layer_slot_count=len(factory_body.layer_slot_ids),
            primitive_count=len(factory_body.primitives),
            neutral_identity_count=neutral,
            binding_sha="0" * 64,
        )
        return replace_fn(
            provisional,
            binding_sha=sha_builder(binding_payload(provisional)),
        )

    def verify_binding(binding, expected_wrapper, branch, materialization_input_sha):
        try:
            _exact_record(binding, binding_type, f"{branch} binding")
            binding.__post_init__()
            view = live_factory_reverifier(expected_wrapper)
            expected_support = support_builder(expected_wrapper, 1)
            if binding.binding_sha != sha_builder(binding_payload(binding)):
                raise ValueError("binding SHA does not match its full body")
            if binding.support_sha != sha_builder(
                support_payload(branch, view.factory.factory_sha, expected_support)
            ):
                raise ValueError("support SHA does not match exact support wire")
            if (
                binding.branch != branch
                or binding.materialization_input_sha != materialization_input_sha
                or binding.factory != view.factory
                or binding.construction_trace != view.trace
                or binding.layer_slot_ids != view.factory.layer_slot_ids
                or binding.support_offsets != expected_support
            ):
                raise ValueError("factory binding differs from live branch replay")
            return binding
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            fail("FACTORY_WIRE_DRIFT", str(exc), exc)

    def replay(parent, permit):
        manifest, permit_body = require_upstream(parent, permit)
        application, scenario, response = resolve_current_application(
            manifest,
            permit_body,
        )
        runtime, basis = require_frozen_c19_wire(application, scenario, response)
        try:
            trace = trace_verifier(runtime.construction_trace)
            initial_actual = actual_factory_verifier(
                runtime.actual_factory,
                trace,
                runtime.frozen_target,
            )
        except (AttributeError, IndexError, RuntimeError, TypeError, ValueError) as exc:
            fail("FACTORY_REPLAY_FAILED", str(exc), exc)
        try:
            outcome = ablation_builder(initial_actual)
            snapshot, actual, matched = pair_snapshotter(outcome)
            actual_view = live_factory_reverifier(actual)
            matched_view = live_factory_reverifier(matched)
        except (AttributeError, IndexError, RuntimeError, TypeError, ValueError) as exc:
            fail("FACTORY_REPLAY_FAILED", str(exc), exc)
        if actual_view.role != "actual" or matched_view.role != "matched_ablated":
            fail("BRANCH_JOIN_FAILED", "replayed factory pair roles drifted")
        if (
            actual_view.factory != runtime.actual_factory
            or matched_view.factory != runtime.matched_factory
            or actual_view.trace != trace
            or matched_view.trace != trace
            or snapshot.actual_factory != runtime.actual_factory
            or snapshot.ablated_factory != runtime.matched_factory
            or snapshot.ablation_manifest != runtime.ablation_manifest
        ):
            fail("BRANCH_JOIN_FAILED", "replayed pair differs from frozen C19 pair")
        try:
            actual_support = support_builder(actual, 1)
            matched_support = support_builder(matched, 1)
        except (AttributeError, IndexError, RuntimeError, TypeError, ValueError) as exc:
            fail("FACTORY_REPLAY_FAILED", str(exc), exc)
        if (
            actual_support != runtime.actual_support_offsets
            or matched_support != runtime.matched_support_offsets
        ):
            fail("FACTORY_WIRE_DRIFT", "frozen support differs from live factory")
        parent_sha = manifest.parent_freeze_v3_sha
        input_sha = sha_builder(
            materialization_input_payload(
                parent_sha,
                permit_body,
                application,
                scenario,
                response,
                trace,
                snapshot,
            )
        )
        actual_binding = make_binding(
            parent_sha=parent_sha,
            permit_sha=permit_body.permit_sha,
            materialization_input_sha=input_sha,
            branch="actual",
            factory_wrapper=actual,
            trace=trace,
        )
        matched_binding = make_binding(
            parent_sha=parent_sha,
            permit_sha=permit_body.permit_sha,
            materialization_input_sha=input_sha,
            branch="matched_ablated",
            factory_wrapper=matched,
            trace=trace,
        )
        provisional = body_type(
            materialization_schema_version=(
                APPLICATION_SCENARIO_MATERIALIZATION_V3_SCHEMA_VERSION
            ),
            permit=clone(permit_body),
            current_application_authority=clone(application),
            current_scenario_authority=clone(scenario),
            current_scenario_response_contract=clone(response),
            basis_contract=clone(basis),
            construction_trace=clone(trace),
            ablation_pair_snapshot=clone(snapshot),
            actual_factory_binding=actual_binding,
            matched_ablated_factory_binding=matched_binding,
            materialization_sha="0" * 64,
        )
        body = replace_fn(
            provisional,
            materialization_sha=sha_builder(body_payload(provisional)),
        )
        verify_binding(actual_binding, actual, "actual", input_sha)
        verify_binding(matched_binding, matched, "matched_ablated", input_sha)
        if body.materialization_sha != sha_builder(body_payload(body)):
            fail("BRANCH_JOIN_FAILED", "materialization SHA replay drifted")
        return _MaterializationReplayV3(body, actual, matched)

    def authority_seal(replay_value):
        return sha_builder(
            {
                "authority_kind": "v3m0-application-materialization-live-v3",
                "materialization_sha": replay_value.materialization.materialization_sha,
                "actual_factory_sha": (
                    replay_value.materialization.actual_factory_binding.factory.factory_sha
                ),
                "matched_ablated_factory_sha": (
                    replay_value.materialization.matched_ablated_factory_binding.factory.factory_sha
                ),
            }
        )

    def require_registered(value):
        if type_fn(value) is not wrapper_type:
            raise TypeError("value must be an exact live materialization-v3")
        with lock:
            current = registry.get(id_fn(value))
            if current is None or current[0]() is not value:
                raise ValueError("materialization-v3 identity is not live")
            authority = current[1]
        try:
            private_body = object.__getattribute__(
                value,
                "_VerifiedV3M0ApplicationScenarioMaterializationV3__materialization",
            )
            private_actual = object.__getattribute__(
                value,
                "_VerifiedV3M0ApplicationScenarioMaterializationV3__actual_factory",
            )
            private_matched = object.__getattribute__(
                value,
                "_VerifiedV3M0ApplicationScenarioMaterializationV3"
                "__matched_ablated_factory",
            )
            private_seal = object.__getattribute__(
                value,
                "_VerifiedV3M0ApplicationScenarioMaterializationV3__authority_seal",
            )
        except AttributeError as exc:
            raise ValueError("materialization-v3 wrapper is incomplete") from exc
        if (
            private_body != authority.materialization
            or private_actual is not authority.actual_factory
            or private_matched is not authority.matched_ablated_factory
            or private_seal != authority.authority_seal
        ):
            raise ValueError("materialization-v3 immutable guard drifted")
        property_binding_guard(value, property_view)
        actual_view = live_factory_reverifier(private_actual)
        matched_view = live_factory_reverifier(private_matched)
        if (
            actual_view.factory
            != authority.materialization.actual_factory_binding.factory
            or matched_view.factory
            != authority.materialization.matched_ablated_factory_binding.factory
        ):
            raise ValueError("materialization-v3 child factory body drifted")
        return authority

    def property_view(value):
        authority = require_registered(value)
        return view_type(
            materialization=clone(authority.materialization),
            actual_factory=authority.actual_factory,
            matched_ablated_factory=authority.matched_ablated_factory,
            permit=authority.permit,
        )

    def issue(parent, permit, replay_value):
        seal = authority_seal(replay_value)
        wrapper = object.__new__(wrapper_type)
        object.__setattr__(
            wrapper,
            "_VerifiedV3M0ApplicationScenarioMaterializationV3__materialization",
            clone(replay_value.materialization),
        )
        object.__setattr__(
            wrapper,
            "_VerifiedV3M0ApplicationScenarioMaterializationV3__actual_factory",
            replay_value.actual_factory,
        )
        object.__setattr__(
            wrapper,
            "_VerifiedV3M0ApplicationScenarioMaterializationV3"
            "__matched_ablated_factory",
            replay_value.matched_ablated_factory,
        )
        object.__setattr__(
            wrapper,
            "_VerifiedV3M0ApplicationScenarioMaterializationV3__authority_seal",
            seal,
        )
        authority = authority_type(
            parent=parent,
            permit=permit,
            parent_freeze_v3_sha=(
                replay_value.materialization.permit.parent_freeze_v3_sha
            ),
            permit_sha=replay_value.materialization.permit.permit_sha,
            materialization=clone(replay_value.materialization),
            actual_factory=replay_value.actual_factory,
            matched_ablated_factory=replay_value.matched_ablated_factory,
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
            existing = registry.get(identity)
            if existing is not None and existing[0]() is not None:
                raise RuntimeError("materialization-v3 live identity collision")
            registry[identity] = (reference, authority)
        try:
            property_binder(
                wrapper,
                property_view,
                token=property_binding_token,
            )
        except BaseException:
            with lock:
                observed = registry.get(identity)
                if observed is not None and observed[0] is reference:
                    del registry[identity]
            raise
        return wrapper

    def materialize(parent, permit):
        return issue(parent, permit, replay(parent, permit))

    def recursively_verify(parent, permit, value):
        manifest, permit_body = require_upstream(parent, permit)
        authority = require_registered(value)
        if authority.parent_freeze_v3_sha != manifest.parent_freeze_v3_sha:
            fail(
                "CROSS_PARENT_ROOT", "materialization belongs to another Parent-v3 root"
            )
        if authority.parent is not parent or authority.permit is not permit:
            fail("PERMIT_INVALID", "materialization belongs to another permit identity")
        if authority.permit_sha != permit_body.permit_sha:
            fail("PERMIT_INVALID", "materialization permit SHA drifted")
        expected = replay(parent, permit)
        if expected.materialization != authority.materialization:
            fail("BRANCH_JOIN_FAILED", "closed materialization replay changed")
        expected_actual = live_factory_reverifier(expected.actual_factory)
        expected_matched = live_factory_reverifier(expected.matched_ablated_factory)
        authority_actual = live_factory_reverifier(authority.actual_factory)
        authority_matched = live_factory_reverifier(authority.matched_ablated_factory)
        if (
            expected_actual.factory != authority_actual.factory
            or expected_matched.factory != authority_matched.factory
        ):
            fail("BRANCH_JOIN_FAILED", "closed factory pair replay changed")
        return value

    def require_for_parent(parent, value):
        authority = require_registered(value)
        try:
            if type_fn(parent) is not parent_type:
                raise TypeError("owner seam requires exact live Parent-v3")
            manifest = parent_reverifier(parent)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            fail("PARENT_V3_UNAVAILABLE", str(exc), exc)
        if authority.parent_freeze_v3_sha != manifest.parent_freeze_v3_sha:
            fail(
                "CROSS_PARENT_ROOT", "materialization belongs to another Parent-v3 root"
            )
        if authority.parent is not parent:
            fail(
                "CROSS_PARENT_ROOT",
                "materialization belongs to another Parent identity",
            )
        recursively_verify(parent, authority.permit, value)
        refreshed = replay(parent, authority.permit)
        return view_type(
            materialization=clone(refreshed.materialization),
            actual_factory=refreshed.actual_factory,
            matched_ablated_factory=refreshed.matched_ablated_factory,
            permit=authority.permit,
        )

    return _ApplicationMaterializationV3Graph(
        materialize=materialize,
        verify=recursively_verify,
        require_for_parent=require_for_parent,
    )


def _make_public_application_materialization_v3_api(graph):
    """Close public APIs over the production graph exactly once."""

    materializer = graph.materialize
    verifier = graph.verify
    owner_reverifier = graph.require_for_parent

    def materialize_v3m0_application_scenario_v3(parent, permit):
        return materializer(parent, permit)

    def verify_v3m0_application_scenario_materialization_v3(
        parent,
        permit,
        materialization,
    ):
        return verifier(parent, permit, materialization)

    def require_for_parent(parent, materialization):
        return owner_reverifier(parent, materialization)

    require_for_parent.__name__ = (
        "_require_v3m0_application_scenario_materialization_v3_for_parent"
    )
    return (
        materialize_v3m0_application_scenario_v3,
        verify_v3m0_application_scenario_materialization_v3,
        require_for_parent,
    )


_PRODUCTION_GRAPH = _make_application_materialization_v3_graph(_ISSUANCE_TOKEN)
(
    materialize_v3m0_application_scenario_v3,
    verify_v3m0_application_scenario_materialization_v3,
    _require_v3m0_application_scenario_materialization_v3_for_parent,
) = _make_public_application_materialization_v3_api(_PRODUCTION_GRAPH)


__all__ = (
    "APPLICATION_SCENARIO_MATERIALIZATION_V3_SCHEMA_VERSION",
    "ApplicationMaterializationV3Failure",
    "ApplicationScenarioMaterializationV3",
    "FACTORY_BRANCH_BINDING_V3_SCHEMA_VERSION",
    "FACTORY_BRANCH_SUPPORT_V3_SCHEMA_VERSION",
    "FactoryBranchBindingV3",
    "MATERIALIZATION_INPUT_V3_SCHEMA_VERSION",
    "VerifiedV3M0ApplicationScenarioMaterializationV3",
    "application_scenario_materialization_v3_payload",
    "factory_branch_binding_v3_payload",
    "factory_branch_support_v3_payload",
    "materialize_v3m0_application_scenario_v3",
    "verify_v3m0_application_scenario_materialization_v3",
)
