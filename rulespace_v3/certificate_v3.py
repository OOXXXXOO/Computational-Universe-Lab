"""Parent-v3 full-state dynamics certification.

The public boundary consumes six live Parent-v3 authorities.  Raw records are
inert, recursively embedded evidence; only wrappers minted by the graph below
carry live authority.  Upstream capability failures are typed raises before
any attempt/outcome record or registry entry is created.  Scientific judge
failures, by contrast, produce a self-hashed first-failure outcome.
"""

from __future__ import annotations

import copy
import functools
import inspect
import re
import threading
import types
import weakref
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from enum import Enum
from typing import Callable, NamedTuple, Optional

from . import runtime as _runtime
from .application_materialization_v3 import (
    ApplicationScenarioMaterializationV3,
    VerifiedParentFreezeV3,
    VerifiedV3M0ApplicationScenarioMaterializationV3,
    _require_v3m0_application_scenario_materialization_v3_for_parent,
)
from .bridge import (
    BRIDGE_TOLERANCE,
    BridgeAudit,
    FullStateBridgeSpec,
    _audit_full_state_bridge_from_raw,
    _build_bound_full_state_bridge_spec,
)
from .certificate import (
    POWER_DRIFT_GATE,
    STRUCTURE_RAW_RESIDUAL_GATE,
    BlockStatus,
    DynamicsCertificationFailure,
    UndefinedReason,
)
from .dynamics import MeasuredTransition
from .fp64_protocol import (
    Fp64EnclosureProtocol,
    build_fp64_enclosure_protocol,
    verify_fp64_enclosure_protocol,
)
from .instability import (
    InstabilityGrowthCounterWitness,
    _build_instability_growth_counter_witness_from_raw,
    verify_instability_growth_counter_witness_arithmetic,
)
from .laurent import (
    LaurentResidualCertificate,
    _build_laurent_residual_from_raw,
    _preflight_laurent_resources_from_raw,
)
from .metric import (
    StabilityMetricWitness,
    _build_bound_synthetic_identity_metric,
)
from .metric_support_authority_v1 import (
    MetricSignedSupportAttestationV1,
    VerifiedMetricSignedSupportAttestationV1,
    _reverify_verified_metric_signed_support_attestation_v1,
)
from .parent_v3_application_prestructure import ParentV3ApplicationPrestructure
from .parent_freeze_v3_contracts import ParentFreezeV3Manifest
from .runtime import RuntimeEvidenceManifest
from .runtime_grids_v3 import (
    BridgeGridAuthorityV3,
    DynamicsGridAuthorityV3,
    VerifiedBridgeGridAuthorityV3,
    VerifiedDynamicsGridAuthorityV3,
    _reverify_verified_bridge_grid_authority_v3,
    _reverify_verified_dynamics_grid_authority_v3,
)
from .spectral import (
    NORMALIZED_METRIC_RESIDUAL_GATE,
    NormalizedMetricResidualAudit,
    PowerDriftAudit,
    SpectralMarginCoverage,
    _build_normalized_metric_residual_audit_from_raw,
    _build_power_drift_audit_from_raw,
    _build_spectral_margin_coverage_from_raw,
)
from .structure import (
    RealityCertificate,
    StructureManifest,
    _build_bound_synthetic_structure_manifest,
    _build_reality_certificate_from_raw,
    canonical_sha,
)
from .transition_authority_v3 import (
    TransitionAuthorityV3,
    VerifiedTransitionAuthorityV3,
    _reverify_verified_transition_authority_v3,
)


CERTIFICATE_V3_SCHEMA_VERSION = "v3m0.dynamics-certificate.v3"
CERTIFICATION_ATTEMPT_V3_SCHEMA_VERSION = "v3m0.dynamics-certification-attempt.v3"
_ZERO_SHA = "0" * 64
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()
_PROPERTY_BINDING_TOKEN = object()

_UPSTREAM_REASON_IDS = frozenset(
    (
        "PARENT_INVALID",
        "MATERIALIZATION_INVALID",
        "PRESTRUCTURE_INVALID",
        "TRANSITION_INVALID",
        "METRIC_ATTESTATION_INVALID",
        "BRIDGE_GRID_INVALID",
        "DYNAMICS_GRID_INVALID",
        "CROSS_AUTHORITY_JOIN",
    )
)
_ISSUABLE_FAILURES = frozenset(
    (
        DynamicsCertificationFailure.REALITY_INVALID,
        DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED,
        DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS,
        DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED,
        DynamicsCertificationFailure.METRIC_RAW_UNRESOLVED,
        DynamicsCertificationFailure.SPECTRAL_COVERAGE_UNRESOLVED,
        DynamicsCertificationFailure.NORMALIZED_METRIC_UNRESOLVED,
        DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED,
        DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED,
    )
)
_FAILURE_REASONS = {
    DynamicsCertificationFailure.REALITY_INVALID: (UndefinedReason.REALITY_VIOLATION),
    DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED: (
        UndefinedReason.LAURENT_RESOURCE_EXCEEDED
    ),
    DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS: (
        UndefinedReason.UNSTABLE
    ),
    DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED: (
        UndefinedReason.STRUCTURE_UNRESOLVED
    ),
    DynamicsCertificationFailure.METRIC_RAW_UNRESOLVED: (
        UndefinedReason.STABILITY_UNRESOLVED
    ),
    DynamicsCertificationFailure.SPECTRAL_COVERAGE_UNRESOLVED: (
        UndefinedReason.STABILITY_UNRESOLVED
    ),
    DynamicsCertificationFailure.NORMALIZED_METRIC_UNRESOLVED: (
        UndefinedReason.STABILITY_UNRESOLVED
    ),
    DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED: (
        UndefinedReason.DYNAMICS_BRIDGE_FAILED
    ),
    DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED: (
        UndefinedReason.STABILITY_UNRESOLVED
    ),
}


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
    _type=type,
    _fields_builder=dataclass_fields,
) -> None:
    if _type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in _fields_builder(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _wire_tree(
    value: object,
    *,
    _is_dataclass=is_dataclass,
    _fields_builder=dataclass_fields,
    _enum_type=Enum,
    _type=type,
) -> object:
    """Return a canonical plain-wire tree, preserving every nested self hash."""

    def walk(item: object) -> object:
        if item is None or _type(item) in (bool, int, float, str):
            return item
        if isinstance(item, _enum_type):
            return item.value
        if _is_dataclass(item) and not isinstance(item, _type):
            return {
                field.name: walk(getattr(item, field.name))
                for field in _fields_builder(item)
            }
        if _type(item) is tuple or _type(item) is list:
            return [walk(child) for child in item]
        if _type(item) is dict:
            if not all(_type(key) is str for key in item):
                raise TypeError("canonical evidence mappings require string keys")
            return {key: walk(child) for key, child in item.items()}
        raise TypeError(
            f"certificate evidence contains a non-wire {_type(item).__name__}"
        )

    return walk(value)


def _snapshot(value: object) -> object:
    return copy.deepcopy(value)


def _record_payload(
    value: object,
    record_type: type,
    self_hash: str,
    *,
    _record_validator=_exact_record,
    _fields_builder=dataclass_fields,
    _wire_builder=_wire_tree,
) -> dict[str, object]:
    _record_validator(value, record_type, record_type.__name__)
    result = {
        item.name: _wire_builder(getattr(value, item.name))
        for item in _fields_builder(record_type)
        if item.name != self_hash
    }
    return result


class DynamicsCertificationUpstreamJoinFailure(ValueError):
    """Typed failure before any B6 evidence artifact can be constructed."""

    def __init__(self, reason_id: str, detail: str) -> None:
        if reason_id not in _UPSTREAM_REASON_IDS:
            raise ValueError("B6 upstream-join reason is not frozen")
        self.reason_id = reason_id
        self.detail = _text(detail, "B6 upstream-join detail")
        super().__init__(f"{reason_id}: {detail}")


@dataclass(frozen=True)
class DynamicsCertificateV3:
    certificate_schema_version: str
    parent_freeze_v3: ParentFreezeV3Manifest
    materialization: ApplicationScenarioMaterializationV3
    transition_authority: TransitionAuthorityV3
    metric_attestation: MetricSignedSupportAttestationV1
    bridge_grid_authority: BridgeGridAuthorityV3
    dynamics_grid_authority: DynamicsGridAuthorityV3
    prestructure_authority: ParentV3ApplicationPrestructure
    structure: StructureManifest
    reality: Optional[RealityCertificate]
    stability_metric: StabilityMetricWitness
    fp64_enclosure_protocol: Fp64EnclosureProtocol
    full_state_bridge_spec: FullStateBridgeSpec
    full_state_bridge_audit: BridgeAudit
    structure_residual: LaurentResidualCertificate
    metric_residual: LaurentResidualCertificate
    spectral_margins: SpectralMarginCoverage
    normalized_metric_residual: NormalizedMetricResidualAudit
    power_drift: PowerDriftAudit
    runtime: RuntimeEvidenceManifest
    certificate_sha: str

    def __post_init__(
        self,
        *,
        _schema=CERTIFICATE_V3_SCHEMA_VERSION,
        _sha_validator=_sha,
    ) -> None:
        if self.certificate_schema_version != _schema:
            raise ValueError("unexpected dynamics-certificate-v3 schema")
        _sha_validator(self.certificate_sha, "certificate_sha")


@dataclass(frozen=True)
class DynamicsCertificationAttemptAuditV3:
    attempt_schema_version: str
    parent_freeze_v3_sha: str
    materialization_sha: str
    transition_authority_sha: str
    metric_attestation_sha: str
    bridge_grid_authority_sha: str
    dynamics_grid_authority_sha: str
    first_failure: Optional[DynamicsCertificationFailure]
    reality: Optional[RealityCertificate]
    structure_residual: Optional[LaurentResidualCertificate]
    metric_residual: Optional[LaurentResidualCertificate]
    spectral_margins: Optional[SpectralMarginCoverage]
    normalized_metric_residual: Optional[NormalizedMetricResidualAudit]
    full_state_bridge_audit: Optional[BridgeAudit]
    power_drift: Optional[PowerDriftAudit]
    instability_counter_witness: Optional[InstabilityGrowthCounterWitness]
    attempt_sha: str

    def __post_init__(
        self,
        *,
        _schema=CERTIFICATION_ATTEMPT_V3_SCHEMA_VERSION,
        _sha_validator=_sha,
        _failure_type=DynamicsCertificationFailure,
        _type=type,
    ) -> None:
        if self.attempt_schema_version != _schema:
            raise ValueError("unexpected dynamics-certification-attempt-v3 schema")
        for name in (
            "parent_freeze_v3_sha",
            "materialization_sha",
            "transition_authority_sha",
            "metric_attestation_sha",
            "bridge_grid_authority_sha",
            "dynamics_grid_authority_sha",
            "attempt_sha",
        ):
            _sha_validator(getattr(self, name), name)
        if self.first_failure is not None and (
            _type(self.first_failure) is not _failure_type
        ):
            raise TypeError(
                "first_failure must be a DynamicsCertificationFailure or None"
            )


@dataclass(frozen=True)
class DynamicsCertificationOutcomeV3:
    status: BlockStatus
    failure: Optional[DynamicsCertificationFailure]
    attempt_audit: DynamicsCertificationAttemptAuditV3
    certificate: Optional[DynamicsCertificateV3]
    outcome_sha: str

    def __post_init__(
        self,
        *,
        _status_type=BlockStatus,
        _failure_type=DynamicsCertificationFailure,
        _attempt_type=DynamicsCertificationAttemptAuditV3,
        _certificate_type=DynamicsCertificateV3,
        _sha_validator=_sha,
        _type=type,
    ) -> None:
        if _type(self.status) is not _status_type:
            raise TypeError("status must be an exact BlockStatus")
        if self.failure is not None and _type(self.failure) is not _failure_type:
            raise TypeError("failure must be a DynamicsCertificationFailure or None")
        if _type(self.attempt_audit) is not _attempt_type:
            raise TypeError("attempt_audit has the wrong exact type")
        if self.certificate is not None and (
            _type(self.certificate) is not _certificate_type
        ):
            raise TypeError("certificate has the wrong exact type")
        _sha_validator(self.outcome_sha, "outcome_sha")


def dynamics_certificate_v3_payload(
    certificate: DynamicsCertificateV3,
    *,
    _record_builder=_record_payload,
    _record_type=DynamicsCertificateV3,
) -> dict[str, object]:
    return _record_builder(
        certificate,
        _record_type,
        "certificate_sha",
    )


def dynamics_certification_attempt_audit_v3_payload(
    audit: DynamicsCertificationAttemptAuditV3,
    *,
    _record_builder=_record_payload,
    _record_type=DynamicsCertificationAttemptAuditV3,
) -> dict[str, object]:
    return _record_builder(
        audit,
        _record_type,
        "attempt_sha",
    )


def dynamics_certification_outcome_v3_payload(
    outcome: DynamicsCertificationOutcomeV3,
    *,
    _record_builder=_record_payload,
    _record_type=DynamicsCertificationOutcomeV3,
) -> dict[str, object]:
    return _record_builder(
        outcome,
        _record_type,
        "outcome_sha",
    )


class VerifiedDynamicsCertificateV3:
    """Opaque capability for one recursively replayed V3 certificate."""

    __slots__ = (
        "__certificate",
        "__originating_outcome",
        "__token",
        "__seal",
        "__weakref__",
    )

    def __init__(self) -> None:
        raise TypeError("VerifiedDynamicsCertificateV3 is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedDynamicsCertificateV3 is immutable")


class VerifiedDynamicsCertificationOutcomeV3:
    """Opaque outcome retaining its exact optional certificate capability."""

    __slots__ = (
        "__outcome",
        "__certificate",
        "__token",
        "__seal",
        "__weakref__",
    )

    def __init__(self) -> None:
        raise TypeError("VerifiedDynamicsCertificationOutcomeV3 is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedDynamicsCertificationOutcomeV3 is immutable")


def _make_property_dispatcher(binding_token: object):
    bindings: dict[int, tuple[weakref.ReferenceType[object], object]] = {}
    lock = threading.RLock()

    def require(value: object, expected_resolver=None):
        with lock:
            current = bindings.get(id(value))
            if current is None or current[0]() is not value:
                raise ValueError("certificate-v3 property identity is not live")
            resolver = current[1]
        if expected_resolver is not None and resolver is not expected_resolver:
            raise ValueError("certificate-v3 property resolver identity drifted")
        return resolver

    def resolve(value: object):
        return require(value)(value)

    def bind(value: object, resolver, *, token: object) -> None:
        if token is not binding_token:
            raise TypeError("certificate-v3 property token mismatch")
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
                raise RuntimeError("certificate-v3 property identity collision")
            bindings[identity] = (reference, resolver)

    return resolve, bind, require


(
    _resolve_certificate_property,
    _bind_certificate_property,
    _require_certificate_property_binding,
) = _make_property_dispatcher(_PROPERTY_BINDING_TOKEN)
(
    _resolve_outcome_property,
    _bind_outcome_property,
    _require_outcome_property_binding,
) = _make_property_dispatcher(_PROPERTY_BINDING_TOKEN)


def _make_wrapper_properties(certificate_resolver, outcome_resolver):
    def certificate_body(value):
        return certificate_resolver(value).certificate

    def outcome_body(value):
        return outcome_resolver(value).outcome

    def outcome_certificate(value):
        return outcome_resolver(value).certificate

    return (
        property(certificate_body),
        property(outcome_body),
        property(outcome_certificate),
    )


(
    VerifiedDynamicsCertificateV3.certificate,
    VerifiedDynamicsCertificationOutcomeV3.outcome,
    VerifiedDynamicsCertificationOutcomeV3.certificate,
) = _make_wrapper_properties(
    _resolve_certificate_property,
    _resolve_outcome_property,
)
del _make_wrapper_properties


@dataclass(frozen=True)
class _VerifiedDynamicsCertificateV3View:
    certificate: DynamicsCertificateV3
    originating_outcome: VerifiedDynamicsCertificationOutcomeV3
    parent: object
    materialization: object
    prestructure: object
    transition: object
    metric_attestation: object
    bridge_grid: object
    dynamics_grid: object


@dataclass(frozen=True)
class _VerifiedDynamicsCertificationOutcomeV3View:
    outcome: DynamicsCertificationOutcomeV3
    certificate: Optional[VerifiedDynamicsCertificateV3]
    parent: object
    materialization: object
    prestructure: object
    transition: object
    metric_attestation: object
    bridge_grid: object
    dynamics_grid: object


@dataclass(frozen=True)
class _CertificateV3Dependencies:
    parent_type: type
    materialization_type: type
    transition_type: type
    measured_transition_type: type
    metric_attestation_type: type
    bridge_grid_type: type
    dynamics_grid_type: type
    parent_reader: Callable[[object], object]
    materialization_requirer: Callable[[object, object], object]
    transition_reverifier: Callable[[object], object]
    metric_reverifier: Callable[[object], object]
    bridge_grid_reverifier: Callable[[object], object]
    dynamics_grid_reverifier: Callable[[object], object]
    factory_body_reader: Callable[[object], object]
    factory_role_reader: Callable[[object], str]
    structure_builder: Callable[..., object]
    reality_builder: Callable[..., object]
    metric_builder: Callable[..., object]
    laurent_preflight: Callable[..., None]
    instability_builder: Callable[..., object]
    instability_verifier: Callable[..., object]
    protocol_builder: Callable[[], object]
    protocol_verifier: Callable[[object], object]
    residual_builder: Callable[..., object]
    spectral_builder: Callable[..., object]
    normalized_builder: Callable[..., object]
    bridge_spec_builder: Callable[..., object]
    bridge_audit_builder: Callable[..., object]
    power_builder: Callable[..., object]
    runtime_issuer: Callable[[], object]
    runtime_verifier: Callable[[object], object]
    sha_builder: Callable[[dict[str, object]], str]
    clone: Callable[[object], object]


@dataclass(frozen=True)
class _JoinedCertificateV3Inputs:
    parent_body: object
    materialization_body: object
    transition_body: object
    metric_body: object
    bridge_grid_body: object
    dynamics_grid_body: object
    prestructure_body: object
    factory: object
    parent: object
    materialization: object
    prestructure: object
    transition: object
    metric_attestation: object
    bridge_grid: object
    dynamics_grid: object


@dataclass(frozen=True)
class _PipelineResultV3:
    outcome: DynamicsCertificationOutcomeV3
    certificate: Optional[DynamicsCertificateV3]


@dataclass(frozen=True)
class _OutcomeAuthorityRecordV3:
    outcome: DynamicsCertificationOutcomeV3
    certificate: Optional[weakref.ReferenceType[VerifiedDynamicsCertificateV3]]
    joined: _JoinedCertificateV3Inputs
    seal: str


@dataclass(frozen=True)
class _CertificateAuthorityRecordV3:
    certificate: DynamicsCertificateV3
    originating_outcome: weakref.ReferenceType[VerifiedDynamicsCertificationOutcomeV3]
    joined: _JoinedCertificateV3Inputs
    seal: str


class _CertificateV3Graph(NamedTuple):
    certify: Callable[..., VerifiedDynamicsCertificationOutcomeV3]
    verify_certificate: Callable[..., VerifiedDynamicsCertificateV3]
    verify_outcome: Callable[..., VerifiedDynamicsCertificationOutcomeV3]
    require_certificate: Callable[..., VerifiedDynamicsCertificateV3]
    reverify_certificate: Callable[..., _VerifiedDynamicsCertificateV3View]
    reverify_outcome: Callable[..., _VerifiedDynamicsCertificationOutcomeV3View]
    authority_counts: Callable[[], tuple[int, int]]


def _make_exact_record_constructor(
    record_type: type,
    *,
    _fields_builder=dataclass_fields,
    _object_type=object,
    _type=type,
):
    """Capture one exact dataclass constructor without dynamic method lookup."""

    field_names = tuple(item.name for item in _fields_builder(record_type))
    post_init = record_type.__post_init__

    def construct(**values):
        if tuple(values) != field_names:
            raise TypeError(f"{record_type.__name__} constructor fields drifted")
        result = _object_type.__new__(record_type)
        for name in field_names:
            _object_type.__setattr__(result, name, values[name])
        if _type(result) is not record_type:
            raise TypeError("exact record construction changed class identity")
        post_init(result)
        return result

    return construct


def _validate_attempt(
    audit: DynamicsCertificationAttemptAuditV3,
    *,
    _record_validator=_exact_record,
    _record_type=DynamicsCertificationAttemptAuditV3,
    _sha_builder=canonical_sha,
    _payload_builder=dynamics_certification_attempt_audit_v3_payload,
    _issuable_failures=_ISSUABLE_FAILURES,
    _failure_type=DynamicsCertificationFailure,
    _post_init=DynamicsCertificationAttemptAuditV3.__post_init__,
) -> None:
    _record_validator(audit, _record_type, "attempt audit v3")
    _post_init(audit)
    if audit.attempt_sha != _sha_builder(_payload_builder(audit)):
        raise ValueError("attempt_sha does not match complete body")
    failure = audit.first_failure
    if failure is None:
        required = (
            audit.reality,
            audit.structure_residual,
            audit.metric_residual,
            audit.spectral_margins,
            audit.normalized_metric_residual,
            audit.full_state_bridge_audit,
            audit.power_drift,
        )
        if any(item is None for item in required):
            raise ValueError("successful attempt lacks completed evidence")
        if audit.instability_counter_witness is not None:
            raise ValueError("successful attempt cannot carry instability witness")
        return
    if failure not in _issuable_failures:
        raise ValueError("upstream-only failure cannot appear in an outcome")
    evidence = (
        audit.reality,
        audit.structure_residual,
        audit.metric_residual,
        audit.spectral_margins,
        audit.normalized_metric_residual,
        audit.full_state_bridge_audit,
        audit.power_drift,
    )
    if failure is _failure_type.REALITY_INVALID:
        if any(item is not None for item in evidence):
            raise ValueError("reality failure cannot contain later evidence")
    elif failure in (
        _failure_type.LAURENT_RESOURCE_EXCEEDED,
        _failure_type.CERTIFIED_INSTABILITY_COUNTERWITNESS,
    ):
        if evidence[0] is None:
            raise ValueError("attempt evidence is not a completed prefix")
        if any(item is not None for item in evidence[1:]):
            raise ValueError("attempt contains evidence after first failure")
    else:
        current_evidence_index = {
            _failure_type.STRUCTURE_RAW_UNRESOLVED: 1,
            _failure_type.METRIC_RAW_UNRESOLVED: 2,
            _failure_type.SPECTRAL_COVERAGE_UNRESOLVED: 3,
            _failure_type.NORMALIZED_METRIC_UNRESOLVED: 4,
            _failure_type.FULL_STATE_BRIDGE_FAILED: 5,
            _failure_type.POWER_DRIFT_UNRESOLVED: 6,
        }[failure]
        if any(item is None for item in evidence[:current_evidence_index]):
            raise ValueError("attempt evidence is not a completed prefix")
        if any(item is not None for item in evidence[current_evidence_index + 1 :]):
            raise ValueError("attempt contains evidence after first failure")
    is_jordan = failure is _failure_type.CERTIFIED_INSTABILITY_COUNTERWITNESS
    if (audit.instability_counter_witness is not None) != is_jordan:
        raise ValueError("instability witness presence does not match first failure")


def _validate_outcome(
    outcome: DynamicsCertificationOutcomeV3,
    *,
    _record_validator=_exact_record,
    _record_type=DynamicsCertificationOutcomeV3,
    _attempt_validator=_validate_attempt,
    _failure_reasons=_FAILURE_REASONS,
    _sha_builder=canonical_sha,
    _payload_builder=dynamics_certification_outcome_v3_payload,
    _post_init=DynamicsCertificationOutcomeV3.__post_init__,
) -> None:
    _record_validator(outcome, _record_type, "outcome v3")
    _post_init(outcome)
    _attempt_validator(outcome.attempt_audit)
    if outcome.failure is not outcome.attempt_audit.first_failure:
        raise ValueError("outcome failure differs from attempt first failure")
    success = outcome.failure is None
    if outcome.status.defined != success:
        raise ValueError("outcome status does not match failure presence")
    if (outcome.certificate is not None) != success:
        raise ValueError("outcome certificate presence does not match success")
    expected_reason = None if success else _failure_reasons[outcome.failure]
    if outcome.status.reason is not expected_reason:
        raise ValueError("outcome reason does not match first failure")
    if outcome.outcome_sha != _sha_builder(_payload_builder(outcome)):
        raise ValueError("outcome_sha does not match complete body")


def _validate_certificate(
    certificate: DynamicsCertificateV3,
    *,
    _record_validator=_exact_record,
    _record_type=DynamicsCertificateV3,
    _sha_builder=canonical_sha,
    _payload_builder=dynamics_certificate_v3_payload,
    _structure_gate=STRUCTURE_RAW_RESIDUAL_GATE,
    _normalized_gate=NORMALIZED_METRIC_RESIDUAL_GATE,
    _bridge_gate=BRIDGE_TOLERANCE,
    _power_gate=POWER_DRIFT_GATE,
    _post_init=DynamicsCertificateV3.__post_init__,
) -> None:
    _record_validator(certificate, _record_type, "certificate v3")
    _post_init(certificate)
    if certificate.certificate_sha != _sha_builder(_payload_builder(certificate)):
        raise ValueError("certificate_sha does not match complete body")
    if (
        certificate.structure_residual.raw_global_momentum_supremum_bound
        > _structure_gate
    ):
        raise ValueError("certificate structure residual exceeds its hard gate")
    if (
        certificate.normalized_metric_residual.normalized_metric_residual_upper
        > _normalized_gate
    ):
        raise ValueError("certificate normalized metric residual exceeds its gate")
    if certificate.full_state_bridge_audit.normalized_max > _bridge_gate:
        raise ValueError("certificate full-state bridge exceeds its hard gate")
    if certificate.power_drift.drift_upper > _power_gate:
        raise ValueError("certificate power drift exceeds its hard gate")


def _make_certificate_v3_graph(
    issuance_token: object,
    dependencies: _CertificateV3Dependencies,
) -> _CertificateV3Graph:
    """Build one closed B6 authority graph over injectable owner seams."""

    if issuance_token is not _ISSUANCE_TOKEN:
        raise TypeError("certificate-v3 graph issuance token mismatch")
    if type(dependencies) is not _CertificateV3Dependencies:
        raise TypeError("certificate-v3 dependencies have the wrong exact type")

    parent_type = dependencies.parent_type
    materialization_type = dependencies.materialization_type
    transition_type = dependencies.transition_type
    measured_transition_type = dependencies.measured_transition_type
    metric_attestation_type = dependencies.metric_attestation_type
    bridge_grid_type = dependencies.bridge_grid_type
    dynamics_grid_type = dependencies.dynamics_grid_type
    parent_reader = dependencies.parent_reader
    materialization_requirer = dependencies.materialization_requirer
    transition_reverifier = dependencies.transition_reverifier
    metric_reverifier = dependencies.metric_reverifier
    bridge_grid_reverifier = dependencies.bridge_grid_reverifier
    dynamics_grid_reverifier = dependencies.dynamics_grid_reverifier
    factory_body_reader = dependencies.factory_body_reader
    factory_role_reader = dependencies.factory_role_reader
    structure_builder = dependencies.structure_builder
    reality_builder = dependencies.reality_builder
    metric_builder = dependencies.metric_builder
    laurent_preflight = dependencies.laurent_preflight
    instability_builder = dependencies.instability_builder
    instability_verifier = dependencies.instability_verifier
    protocol_builder = dependencies.protocol_builder
    protocol_verifier = dependencies.protocol_verifier
    residual_builder = dependencies.residual_builder
    spectral_builder = dependencies.spectral_builder
    normalized_builder = dependencies.normalized_builder
    bridge_spec_builder = dependencies.bridge_spec_builder
    bridge_audit_builder = dependencies.bridge_audit_builder
    power_builder = dependencies.power_builder
    runtime_issuer = dependencies.runtime_issuer
    runtime_verifier = dependencies.runtime_verifier
    sha_builder = dependencies.sha_builder
    clone = dependencies.clone
    type_fn = type
    type_name_reader = type.__getattribute__
    id_fn = id
    weak_reference = weakref.ref
    lock = threading.RLock()
    outcome_registry: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedDynamicsCertificationOutcomeV3],
            _OutcomeAuthorityRecordV3,
        ],
    ] = {}
    certificate_registry: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedDynamicsCertificateV3],
            _CertificateAuthorityRecordV3,
        ],
    ] = {}
    outcome_wrapper_type = VerifiedDynamicsCertificationOutcomeV3
    certificate_wrapper_type = VerifiedDynamicsCertificateV3
    certificate_body_type = DynamicsCertificateV3
    attempt_body_type = DynamicsCertificationAttemptAuditV3
    outcome_body_type = DynamicsCertificationOutcomeV3
    joined_inputs_type = _JoinedCertificateV3Inputs
    pipeline_result_type = _PipelineResultV3
    outcome_record_type = _OutcomeAuthorityRecordV3
    certificate_record_type = _CertificateAuthorityRecordV3
    outcome_view_type = _VerifiedDynamicsCertificationOutcomeV3View
    certificate_view_type = _VerifiedDynamicsCertificateV3View
    failure_type = DynamicsCertificationFailure
    attempt_constructor = _make_exact_record_constructor(attempt_body_type)
    outcome_constructor = _make_exact_record_constructor(outcome_body_type)
    certificate_constructor = _make_exact_record_constructor(certificate_body_type)
    block_status_constructor = _make_exact_record_constructor(BlockStatus)
    bind_outcome_property = _bind_outcome_property
    bind_certificate_property = _bind_certificate_property
    require_outcome_property_binding = _require_outcome_property_binding
    require_certificate_property_binding = _require_certificate_property_binding
    property_token = _PROPERTY_BINDING_TOKEN
    issuance_marker = _ISSUANCE_TOKEN
    snapshot = clone
    exact_record_validator = _exact_record
    attempt_validator = _validate_attempt
    outcome_validator = _validate_outcome
    certificate_validator = _validate_certificate
    certificate_payload_builder = dynamics_certificate_v3_payload
    attempt_payload_builder = dynamics_certification_attempt_audit_v3_payload
    outcome_payload_builder = dynamics_certification_outcome_v3_payload
    failure_reasons = dict(_FAILURE_REASONS)
    zero_sha = _ZERO_SHA
    certificate_schema = CERTIFICATE_V3_SCHEMA_VERSION
    attempt_schema = CERTIFICATION_ATTEMPT_V3_SCHEMA_VERSION
    structure_gate = STRUCTURE_RAW_RESIDUAL_GATE
    normalized_gate = NORMALIZED_METRIC_RESIDUAL_GATE
    bridge_gate = BRIDGE_TOLERANCE
    power_gate = POWER_DRIFT_GATE
    upstream_failure_type = DynamicsCertificationUpstreamJoinFailure
    science_errors = (AttributeError, RuntimeError, TypeError, ValueError)

    def trusted_type_name(value: object) -> str:
        try:
            observed = type_name_reader(type_fn(value), "__name__")
        except Exception:
            return "upstream exception"
        if type_fn(observed) is str and observed.strip():
            return observed.strip()
        return "upstream exception"

    def upstream_fail(reason_id: str, detail: object, cause=None):
        if cause is not None:
            detail_text = trusted_type_name(cause)
        elif type_fn(detail) is str and detail.strip():
            detail_text = detail
        else:
            detail_text = trusted_type_name(detail)
        failure = upstream_failure_type(reason_id, detail_text)
        if cause is None:
            raise failure
        raise failure from cause

    def call_upstream(reason_id: str, operation, *args):
        try:
            return operation(*args)
        except upstream_failure_type:
            raise
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            upstream_fail(reason_id, exc, exc)

    def wrapper_factory_body(factory):
        return factory_body_reader(factory)

    def wrapper_factory_role(factory):
        return factory_role_reader(factory)

    def atomic_join(
        parent,
        materialization,
        transition,
        metric_attestation,
        bridge_grid,
        dynamics_grid,
    ):
        if type_fn(parent) is not parent_type:
            upstream_fail("PARENT_INVALID", "exact live Parent-v3 is required")
        parent_body = call_upstream("PARENT_INVALID", parent_reader, parent)
        if type_fn(materialization) is not materialization_type:
            upstream_fail(
                "MATERIALIZATION_INVALID",
                "exact live B2 materialization is required",
            )
        materialization_view = call_upstream(
            "MATERIALIZATION_INVALID",
            materialization_requirer,
            parent,
            materialization,
        )
        if type_fn(transition) is not transition_type:
            upstream_fail(
                "TRANSITION_INVALID",
                "exact live TransitionAuthorityV3 is required",
            )
        try:
            transition_view = transition_reverifier(transition)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            reason = (
                "PRESTRUCTURE_INVALID"
                if getattr(exc, "reason_id", None) == "PRESTRUCTURE_INVALID"
                else "TRANSITION_INVALID"
            )
            upstream_fail(reason, exc, exc)
        if type_fn(metric_attestation) is not metric_attestation_type:
            upstream_fail(
                "METRIC_ATTESTATION_INVALID",
                "exact live metric attestation is required",
            )
        metric_view = call_upstream(
            "METRIC_ATTESTATION_INVALID",
            metric_reverifier,
            metric_attestation,
        )
        if type_fn(bridge_grid) is not bridge_grid_type:
            upstream_fail(
                "BRIDGE_GRID_INVALID",
                "exact live bridge-grid authority is required",
            )
        bridge_view = call_upstream(
            "BRIDGE_GRID_INVALID",
            bridge_grid_reverifier,
            bridge_grid,
        )
        if type_fn(dynamics_grid) is not dynamics_grid_type:
            upstream_fail(
                "DYNAMICS_GRID_INVALID",
                "exact live dynamics-grid authority is required",
            )
        dynamics_view = call_upstream(
            "DYNAMICS_GRID_INVALID",
            dynamics_grid_reverifier,
            dynamics_grid,
        )

        try:
            materialization_body = materialization_view.materialization
            transition_body = transition_view.transition_authority
            metric_body = metric_view.attestation
            bridge_grid_body = bridge_view.grid_authority
            dynamics_grid_body = dynamics_view.grid_authority
            live_prestructure = transition_view.prestructure
            prestructure_body = live_prestructure.prestructure
            measured = transition_body.measured_transition
            if type_fn(measured) is not measured_transition_type:
                raise ValueError("measured transition has the wrong exact type")
            role = measured.factory_role
            if role == "actual":
                materialization_factory = materialization_view.actual_factory
                materialization_binding = materialization_body.actual_factory_binding
            elif role == "matched_ablated":
                materialization_factory = materialization_view.matched_ablated_factory
                materialization_binding = (
                    materialization_body.matched_ablated_factory_binding
                )
            else:
                raise ValueError("transition factory role is not frozen")
            transition_factory = transition_view.factory
            factories = (
                materialization_factory,
                transition_factory,
                metric_view.factory,
                bridge_view.factory,
            )
            factory_bodies = tuple(wrapper_factory_body(item) for item in factories)
            factory_roles = tuple(wrapper_factory_role(item) for item in factories)
            if any(item != factory_bodies[0] for item in factory_bodies[1:]):
                raise ValueError("fresh factory wrappers do not expose equal bodies")
            if factory_roles != (role, role, role, role):
                raise ValueError("factory wrapper roles differ across authorities")
            bindings = (
                materialization_binding,
                transition_body.factory_binding,
                prestructure_body.factory_binding,
                metric_view.factory_binding,
                bridge_view.factory_binding,
            )
            if any(item != bindings[0] for item in bindings[1:]):
                raise ValueError("factory bindings differ across authorities")
            if materialization_binding.factory != factory_bodies[0]:
                raise ValueError("factory binding body differs from live factory")
            if materialization_binding.branch != role:
                raise ValueError("factory binding role differs from transition")
            if (
                transition_view.parent is not parent
                or metric_view.parent is not parent
                or bridge_view.parent is not parent
                or dynamics_view.parent is not parent
            ):
                raise ValueError("live Parent identity differs across authorities")
            if (
                transition_view.materialization is not materialization
                or metric_view.materialization is not materialization
                or bridge_view.materialization is not materialization
            ):
                raise ValueError("live materialization identity differs")
            if (
                dynamics_view.transition is not transition
                or dynamics_view.metric_attestation is not metric_attestation
            ):
                raise ValueError("dynamics-grid live authority identity differs")
            if transition_body.materialization != materialization_body:
                raise ValueError("transition materialization body differs")
            if bridge_grid_body.materialization != materialization_body:
                raise ValueError("bridge-grid materialization body differs")
            if (
                transition_body.prestructure_authority != prestructure_body
                or measured.prestructure_authority_sha
                != prestructure_body.prestructure_authority_sha
            ):
                raise ValueError("transition prestructure body differs")
            if (
                dynamics_grid_body.transition_authority != transition_body
                or dynamics_grid_body.metric_support_attestation != metric_body
            ):
                raise ValueError("dynamics-grid recursive inputs differ")
            response = materialization_body.current_scenario_response_contract
            metric_protocol = response.metric_support_derivation
            if metric_body.metric_support_protocol_sha != metric_protocol.protocol_sha:
                raise ValueError("metric protocol origin binding differs")
            parent_sha = parent_body.parent_freeze_v3_sha
            if (
                materialization_body.permit.parent_freeze_v3_sha != parent_sha
                or prestructure_body.parent_freeze_v3_sha != parent_sha
                or measured.parent_freeze_sha != parent_sha
                or metric_body.parent_freeze_v3_sha != parent_sha
                or materialization_binding.parent_freeze_v3_sha != parent_sha
            ):
                raise ValueError("recursive Parent-v3 roots differ")
            if (
                prestructure_body.materialization_sha
                != materialization_body.materialization_sha
                or metric_body.application_scenario_materialization_v3_sha
                != materialization_body.materialization_sha
            ):
                raise ValueError("recursive materialization roots differ")
            if (
                measured.factory_sha != factory_bodies[0].factory_sha
                or prestructure_body.factory_sha != factory_bodies[0].factory_sha
                or metric_body.factory_sha != factory_bodies[0].factory_sha
            ):
                raise ValueError("recursive factory roots differ")
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            upstream_fail("CROSS_AUTHORITY_JOIN", exc, exc)

        return joined_inputs_type(
            parent_body=clone(parent_body),
            materialization_body=clone(materialization_body),
            transition_body=clone(transition_body),
            metric_body=clone(metric_body),
            bridge_grid_body=clone(bridge_grid_body),
            dynamics_grid_body=clone(dynamics_grid_body),
            prestructure_body=clone(prestructure_body),
            factory=transition_factory,
            parent=parent,
            materialization=materialization,
            prestructure=live_prestructure,
            transition=transition,
            metric_attestation=metric_attestation,
            bridge_grid=bridge_grid,
            dynamics_grid=dynamics_grid,
        )

    def make_attempt(
        joined,
        *,
        failure,
        reality=None,
        structure_residual=None,
        metric_residual=None,
        spectral_margins=None,
        normalized_metric_residual=None,
        full_state_bridge_audit=None,
        power_drift=None,
        instability_counter_witness=None,
    ):
        provisional = attempt_constructor(
            attempt_schema_version=attempt_schema,
            parent_freeze_v3_sha=joined.parent_body.parent_freeze_v3_sha,
            materialization_sha=joined.materialization_body.materialization_sha,
            transition_authority_sha=(joined.transition_body.transition_authority_sha),
            metric_attestation_sha=joined.metric_body.attestation_sha,
            bridge_grid_authority_sha=(joined.bridge_grid_body.grid_authority_sha),
            dynamics_grid_authority_sha=(joined.dynamics_grid_body.grid_authority_sha),
            first_failure=failure,
            reality=clone(reality),
            structure_residual=clone(structure_residual),
            metric_residual=clone(metric_residual),
            spectral_margins=clone(spectral_margins),
            normalized_metric_residual=clone(normalized_metric_residual),
            full_state_bridge_audit=clone(full_state_bridge_audit),
            power_drift=clone(power_drift),
            instability_counter_witness=clone(instability_counter_witness),
            attempt_sha=zero_sha,
        )
        result = attempt_constructor(
            attempt_schema_version=provisional.attempt_schema_version,
            parent_freeze_v3_sha=provisional.parent_freeze_v3_sha,
            materialization_sha=provisional.materialization_sha,
            transition_authority_sha=provisional.transition_authority_sha,
            metric_attestation_sha=provisional.metric_attestation_sha,
            bridge_grid_authority_sha=provisional.bridge_grid_authority_sha,
            dynamics_grid_authority_sha=provisional.dynamics_grid_authority_sha,
            first_failure=provisional.first_failure,
            reality=provisional.reality,
            structure_residual=provisional.structure_residual,
            metric_residual=provisional.metric_residual,
            spectral_margins=provisional.spectral_margins,
            normalized_metric_residual=provisional.normalized_metric_residual,
            full_state_bridge_audit=provisional.full_state_bridge_audit,
            power_drift=provisional.power_drift,
            instability_counter_witness=provisional.instability_counter_witness,
            attempt_sha=sha_builder(attempt_payload_builder(provisional)),
        )
        attempt_validator(result)
        return result

    def make_outcome(failure, attempt, certificate):
        provisional = outcome_constructor(
            status=(
                block_status_constructor(defined=True, reason=None)
                if failure is None
                else block_status_constructor(
                    defined=False,
                    reason=failure_reasons[failure],
                )
            ),
            failure=failure,
            attempt_audit=attempt,
            certificate=clone(certificate),
            outcome_sha=zero_sha,
        )
        result = outcome_constructor(
            status=provisional.status,
            failure=provisional.failure,
            attempt_audit=provisional.attempt_audit,
            certificate=provisional.certificate,
            outcome_sha=sha_builder(outcome_payload_builder(provisional)),
        )
        outcome_validator(result)
        return result

    def failed(joined, failure, **evidence):
        attempt = make_attempt(joined, failure=failure, **evidence)
        outcome = make_outcome(failure, attempt, None)
        return pipeline_result_type(outcome, None)

    def run_pipeline(joined):
        prestructure = joined.prestructure_body
        transition = joined.transition_body.measured_transition
        factory = joined.factory
        # Runtime provenance is an evaluator precondition, not a scientific
        # judge.  Complete it before any attempt/outcome can be constructed;
        # the exact same manifest is embedded if the pipeline succeeds.
        runtime = runtime_verifier(runtime_issuer())
        try:
            structure = structure_builder(
                prestructure.structure_form,
                target_spec_sha=prestructure.target_spec_sha,
                state_schema_id=prestructure.state_schema_id,
                channel_order=prestructure.channel_order,
                canonical_channel_pairs=(prestructure.canonical_channel_pairs),
                prestructure_authority_sha=(prestructure.prestructure_authority_sha),
            )
            reality = reality_builder(factory, transition, structure)
        except science_errors:
            return failed(
                joined,
                failure_type.REALITY_INVALID,
            )

        metric_protocol = joined.materialization_body.current_scenario_response_contract.metric_support_derivation

        def reconstruct_metric():
            return metric_builder(
                factory,
                structure,
                metric_protocol.state_metric,
                parent_freeze_sha=joined.parent_body.parent_freeze_v3_sha,
                prestructure_authority_sha=(prestructure.prestructure_authority_sha),
                derivation_or_preregistration_sha=(
                    joined.metric_body.metric_support_protocol_sha
                ),
                metric_support_offsets=(joined.metric_body.metric_support_offsets),
            )

        # The canonical-structure core has a frozen exact-metric argument even
        # though that judge does not use G.  Preconstruct G once solely to make
        # the Laurent resource/structure prefix evaluable.  A failure here
        # cannot honestly mint METRIC_RAW_UNRESOLVED because no real structure
        # residual exists yet, so it is evaluator infrastructure failure.
        try:
            dependency_metric = reconstruct_metric()
            if (
                dependency_metric.metric_origin.derivation_or_preregistration_sha
                != joined.metric_body.metric_support_protocol_sha
            ):
                raise ValueError("metric origin does not bind the B4 protocol")
        except science_errors as exc:
            raise RuntimeError(
                "metric dependency preconstruction failed before judge prefix"
            ) from exc

        try:
            laurent_preflight(transition, dependency_metric)
        except science_errors:
            return failed(
                joined,
                failure_type.LAURENT_RESOURCE_EXCEEDED,
                reality=reality,
            )

        witness = instability_builder(transition)
        if witness is not None:
            try:
                verified_witness = instability_verifier(witness)
            except science_errors as exc:
                raise RuntimeError(
                    "exact-Jordan arithmetic infrastructure failed"
                ) from exc
            return failed(
                joined,
                failure_type.CERTIFIED_INSTABILITY_COUNTERWITNESS,
                reality=reality,
                instability_counter_witness=verified_witness,
            )

        protocol = protocol_verifier(protocol_builder())
        try:
            structure_residual = residual_builder(
                transition,
                structure,
                dependency_metric,
                protocol,
                kind="canonical-structure",
            )
        except science_errors:
            return failed(
                joined,
                failure_type.STRUCTURE_RAW_UNRESOLVED,
                reality=reality,
            )
        if structure_residual.raw_global_momentum_supremum_bound > structure_gate:
            return failed(
                joined,
                failure_type.STRUCTURE_RAW_UNRESOLVED,
                reality=reality,
                structure_residual=structure_residual,
            )

        # Reconstruct from the identical frozen joined inputs at the actual
        # metric judge.  This is a second call to the same owner-neutral core,
        # never a copied algorithm or caller seam.  Exception, origin drift,
        # or non-identical reconstruction is the typed metric first failure.
        try:
            metric = reconstruct_metric()
            if (
                metric.metric_origin.derivation_or_preregistration_sha
                != joined.metric_body.metric_support_protocol_sha
                or metric != dependency_metric
            ):
                raise ValueError("metric reconstruction differs from dependency")
        except science_errors:
            return failed(
                joined,
                failure_type.METRIC_RAW_UNRESOLVED,
                reality=reality,
                structure_residual=structure_residual,
            )

        try:
            metric_residual = residual_builder(
                transition,
                structure,
                metric,
                protocol,
                kind="stability-metric",
            )
        except science_errors:
            return failed(
                joined,
                failure_type.METRIC_RAW_UNRESOLVED,
                reality=reality,
                structure_residual=structure_residual,
            )

        try:
            spectral = spectral_builder(
                transition,
                metric,
                protocol,
                dynamics_grid=(joined.dynamics_grid_body.dynamics_grid),
            )
        except science_errors:
            return failed(
                joined,
                failure_type.SPECTRAL_COVERAGE_UNRESOLVED,
                reality=reality,
                structure_residual=structure_residual,
                metric_residual=metric_residual,
            )

        try:
            normalized = normalized_builder(metric_residual, spectral)
        except science_errors:
            return failed(
                joined,
                failure_type.NORMALIZED_METRIC_UNRESOLVED,
                reality=reality,
                structure_residual=structure_residual,
                metric_residual=metric_residual,
                spectral_margins=spectral,
            )
        if normalized.normalized_metric_residual_upper > normalized_gate:
            return failed(
                joined,
                failure_type.NORMALIZED_METRIC_UNRESOLVED,
                reality=reality,
                structure_residual=structure_residual,
                metric_residual=metric_residual,
                spectral_margins=spectral,
                normalized_metric_residual=normalized,
            )

        try:
            bridge_spec = bridge_spec_builder(
                factory,
                joined.bridge_grid_body.bridge_grid,
                parent_freeze_sha=joined.parent_body.parent_freeze_v3_sha,
                prestructure_authority_sha=(prestructure.prestructure_authority_sha),
            )
            bridge = bridge_audit_builder(transition, factory, bridge_spec)
        except science_errors:
            return failed(
                joined,
                failure_type.FULL_STATE_BRIDGE_FAILED,
                reality=reality,
                structure_residual=structure_residual,
                metric_residual=metric_residual,
                spectral_margins=spectral,
                normalized_metric_residual=normalized,
            )
        if bridge.normalized_max > bridge_gate:
            return failed(
                joined,
                failure_type.FULL_STATE_BRIDGE_FAILED,
                reality=reality,
                structure_residual=structure_residual,
                metric_residual=metric_residual,
                spectral_margins=spectral,
                normalized_metric_residual=normalized,
                full_state_bridge_audit=bridge,
            )

        try:
            power = power_builder(normalized)
        except science_errors:
            return failed(
                joined,
                failure_type.POWER_DRIFT_UNRESOLVED,
                reality=reality,
                structure_residual=structure_residual,
                metric_residual=metric_residual,
                spectral_margins=spectral,
                normalized_metric_residual=normalized,
                full_state_bridge_audit=bridge,
            )
        if power.drift_upper > power_gate:
            return failed(
                joined,
                failure_type.POWER_DRIFT_UNRESOLVED,
                reality=reality,
                structure_residual=structure_residual,
                metric_residual=metric_residual,
                spectral_margins=spectral,
                normalized_metric_residual=normalized,
                full_state_bridge_audit=bridge,
                power_drift=power,
            )

        provisional = certificate_constructor(
            certificate_schema_version=certificate_schema,
            parent_freeze_v3=clone(joined.parent_body),
            materialization=clone(joined.materialization_body),
            transition_authority=clone(joined.transition_body),
            metric_attestation=clone(joined.metric_body),
            bridge_grid_authority=clone(joined.bridge_grid_body),
            dynamics_grid_authority=clone(joined.dynamics_grid_body),
            prestructure_authority=clone(joined.prestructure_body),
            structure=clone(structure),
            reality=clone(reality),
            stability_metric=clone(metric),
            fp64_enclosure_protocol=clone(protocol),
            full_state_bridge_spec=clone(bridge_spec),
            full_state_bridge_audit=clone(bridge),
            structure_residual=clone(structure_residual),
            metric_residual=clone(metric_residual),
            spectral_margins=clone(spectral),
            normalized_metric_residual=clone(normalized),
            power_drift=clone(power),
            runtime=clone(runtime),
            certificate_sha=zero_sha,
        )
        certificate = certificate_constructor(
            certificate_schema_version=provisional.certificate_schema_version,
            parent_freeze_v3=provisional.parent_freeze_v3,
            materialization=provisional.materialization,
            transition_authority=provisional.transition_authority,
            metric_attestation=provisional.metric_attestation,
            bridge_grid_authority=provisional.bridge_grid_authority,
            dynamics_grid_authority=provisional.dynamics_grid_authority,
            prestructure_authority=provisional.prestructure_authority,
            structure=provisional.structure,
            reality=provisional.reality,
            stability_metric=provisional.stability_metric,
            fp64_enclosure_protocol=provisional.fp64_enclosure_protocol,
            full_state_bridge_spec=provisional.full_state_bridge_spec,
            full_state_bridge_audit=provisional.full_state_bridge_audit,
            structure_residual=provisional.structure_residual,
            metric_residual=provisional.metric_residual,
            spectral_margins=provisional.spectral_margins,
            normalized_metric_residual=provisional.normalized_metric_residual,
            power_drift=provisional.power_drift,
            runtime=provisional.runtime,
            certificate_sha=sha_builder(certificate_payload_builder(provisional)),
        )
        certificate_validator(certificate)
        attempt = make_attempt(
            joined,
            failure=None,
            reality=reality,
            structure_residual=structure_residual,
            metric_residual=metric_residual,
            spectral_margins=spectral,
            normalized_metric_residual=normalized,
            full_state_bridge_audit=bridge,
            power_drift=power,
        )
        outcome = make_outcome(None, attempt, certificate)
        return pipeline_result_type(outcome, certificate)

    def live_roots(joined):
        return (
            id_fn(joined.parent),
            id_fn(joined.materialization),
            id_fn(joined.prestructure),
            id_fn(joined.transition),
            id_fn(joined.metric_attestation),
            id_fn(joined.bridge_grid),
            id_fn(joined.dynamics_grid),
        )

    def authority_seal(kind: str, body_sha: str, joined):
        return sha_builder(
            {
                "authority_kind": kind,
                "body_sha": body_sha,
                "live_upstream_ids": list(live_roots(joined)),
            }
        )

    def make_wrapper(wrapper_type, fields):
        wrapper = object.__new__(wrapper_type)
        for name, value in fields:
            object.__setattr__(wrapper, name, value)
        return wrapper

    def register(result, joined):
        outcome_validator(result.outcome)
        if result.certificate is not None:
            certificate_validator(result.certificate)
            if result.outcome.certificate != result.certificate:
                raise ValueError("outcome and pipeline certificate bodies differ")
        outcome_seal = authority_seal(
            "v3m0.verified-dynamics-certification-outcome.v3",
            result.outcome.outcome_sha,
            joined,
        )
        certificate_seal = (
            None
            if result.certificate is None
            else authority_seal(
                "v3m0.verified-dynamics-certificate.v3",
                result.certificate.certificate_sha,
                joined,
            )
        )
        verified_certificate = (
            None
            if result.certificate is None
            else make_wrapper(
                certificate_wrapper_type,
                (
                    (
                        "_VerifiedDynamicsCertificateV3__certificate",
                        snapshot(result.certificate),
                    ),
                    ("_VerifiedDynamicsCertificateV3__token", issuance_marker),
                    ("_VerifiedDynamicsCertificateV3__seal", certificate_seal),
                ),
            )
        )
        verified_outcome = make_wrapper(
            outcome_wrapper_type,
            (
                (
                    "_VerifiedDynamicsCertificationOutcomeV3__outcome",
                    snapshot(result.outcome),
                ),
                (
                    "_VerifiedDynamicsCertificationOutcomeV3__certificate",
                    verified_certificate,
                ),
                (
                    "_VerifiedDynamicsCertificationOutcomeV3__token",
                    issuance_marker,
                ),
                (
                    "_VerifiedDynamicsCertificationOutcomeV3__seal",
                    outcome_seal,
                ),
            ),
        )
        if verified_certificate is not None:
            object.__setattr__(
                verified_certificate,
                "_VerifiedDynamicsCertificateV3__originating_outcome",
                verified_outcome,
            )
        outcome_identity = id_fn(verified_outcome)
        certificate_identity = (
            None if verified_certificate is None else id_fn(verified_certificate)
        )

        def remove_outcome(reference, wrapper_id=outcome_identity):
            with lock:
                observed = outcome_registry.get(wrapper_id)
                if observed is not None and observed[0] is reference:
                    del outcome_registry[wrapper_id]

        outcome_reference = weak_reference(verified_outcome, remove_outcome)
        if verified_certificate is not None:
            assert certificate_identity is not None

            def remove_certificate(reference, wrapper_id=certificate_identity):
                with lock:
                    observed = certificate_registry.get(wrapper_id)
                    if observed is not None and observed[0] is reference:
                        del certificate_registry[wrapper_id]

            certificate_reference = weak_reference(
                verified_certificate,
                remove_certificate,
            )
        else:
            certificate_reference = None
        outcome_record = outcome_record_type(
            snapshot(result.outcome),
            certificate_reference,
            joined,
            outcome_seal,
        )
        certificate_record = (
            None
            if verified_certificate is None
            else certificate_record_type(
                snapshot(result.certificate),
                outcome_reference,
                joined,
                certificate_seal,
            )
        )
        with lock:
            if outcome_identity in outcome_registry or (
                certificate_identity is not None
                and certificate_identity in certificate_registry
            ):
                raise RuntimeError("certificate-v3 live identity collision")
            outcome_registry[outcome_identity] = (
                outcome_reference,
                outcome_record,
            )
            if verified_certificate is not None:
                assert certificate_identity is not None
                assert certificate_reference is not None
                assert certificate_record is not None
                certificate_registry[certificate_identity] = (
                    certificate_reference,
                    certificate_record,
                )
        try:
            bind_outcome_property(
                verified_outcome,
                reverify_outcome,
                token=property_token,
            )
            if verified_certificate is not None:
                bind_certificate_property(
                    verified_certificate,
                    reverify_certificate,
                    token=property_token,
                )
        except Exception:
            with lock:
                outcome_registry.pop(outcome_identity, None)
                if certificate_identity is not None:
                    certificate_registry.pop(certificate_identity, None)
            raise
        return verified_outcome

    def rejoin_record(joined):
        refreshed = atomic_join(
            joined.parent,
            joined.materialization,
            joined.transition,
            joined.metric_attestation,
            joined.bridge_grid,
            joined.dynamics_grid,
        )
        for name in (
            "parent",
            "materialization",
            "prestructure",
            "transition",
            "metric_attestation",
            "bridge_grid",
            "dynamics_grid",
        ):
            if getattr(refreshed, name) is not getattr(joined, name):
                raise ValueError(f"certificate-v3 live {name} identity drifted")
        return refreshed

    def shallow_outcome(value):
        if type_fn(value) is not outcome_wrapper_type:
            raise TypeError("exact live certification-outcome-v3 is required")
        require_outcome_property_binding(value, reverify_outcome)
        with lock:
            current = outcome_registry.get(id_fn(value))
            if current is None or current[0]() is not value:
                raise ValueError("certification-outcome-v3 identity is not live")
            record = current[1]
        try:
            token = object.__getattribute__(
                value,
                "_VerifiedDynamicsCertificationOutcomeV3__token",
            )
            raw = object.__getattribute__(
                value,
                "_VerifiedDynamicsCertificationOutcomeV3__outcome",
            )
            certificate = object.__getattribute__(
                value,
                "_VerifiedDynamicsCertificationOutcomeV3__certificate",
            )
            seal = object.__getattribute__(
                value,
                "_VerifiedDynamicsCertificationOutcomeV3__seal",
            )
        except AttributeError as exc:
            raise ValueError("certification-outcome-v3 wrapper is incomplete") from exc
        expected_certificate = (
            None if record.certificate is None else record.certificate()
        )
        if (
            token is not issuance_marker
            or raw != record.outcome
            or certificate is not expected_certificate
            or seal != record.seal
        ):
            raise ValueError("certification-outcome-v3 wrapper drifted")
        outcome_validator(raw)
        if seal != authority_seal(
            "v3m0.verified-dynamics-certification-outcome.v3",
            raw.outcome_sha,
            record.joined,
        ):
            raise ValueError("certification-outcome-v3 seal drifted")
        rejoin_record(record.joined)
        return record

    def shallow_certificate(value):
        if type_fn(value) is not certificate_wrapper_type:
            raise TypeError("exact live dynamics-certificate-v3 is required")
        require_certificate_property_binding(value, reverify_certificate)
        with lock:
            current = certificate_registry.get(id_fn(value))
            if current is None or current[0]() is not value:
                raise ValueError("dynamics-certificate-v3 identity is not live")
            record = current[1]
        try:
            token = object.__getattribute__(
                value,
                "_VerifiedDynamicsCertificateV3__token",
            )
            raw = object.__getattribute__(
                value,
                "_VerifiedDynamicsCertificateV3__certificate",
            )
            originating_outcome = object.__getattribute__(
                value,
                "_VerifiedDynamicsCertificateV3__originating_outcome",
            )
            seal = object.__getattribute__(
                value,
                "_VerifiedDynamicsCertificateV3__seal",
            )
        except AttributeError as exc:
            raise ValueError("dynamics-certificate-v3 wrapper is incomplete") from exc
        expected_outcome = record.originating_outcome()
        if (
            token is not issuance_marker
            or raw != record.certificate
            or originating_outcome is not expected_outcome
            or seal != record.seal
        ):
            raise ValueError("dynamics-certificate-v3 wrapper drifted")
        certificate_validator(raw)
        if seal != authority_seal(
            "v3m0.verified-dynamics-certificate.v3",
            raw.certificate_sha,
            record.joined,
        ):
            raise ValueError("dynamics-certificate-v3 seal drifted")
        protocol_verifier(raw.fp64_enclosure_protocol)
        runtime_verifier(raw.runtime)
        rejoin_record(record.joined)
        return record

    def reverify_outcome(value):
        record = shallow_outcome(value)
        certificate = None if record.certificate is None else record.certificate()
        if certificate is not None:
            shallow_certificate(certificate)
            with lock:
                certificate_entry = certificate_registry.get(id_fn(certificate))
            if (
                certificate_entry is None
                or certificate_entry[0]() is not certificate
                or certificate_entry[1].originating_outcome() is not value
                or certificate_entry[1].certificate != record.outcome.certificate
            ):
                raise ValueError("outcome/certificate live lineage drifted")
        return outcome_view_type(
            outcome=snapshot(record.outcome),
            certificate=certificate,
            parent=record.joined.parent,
            materialization=record.joined.materialization,
            prestructure=record.joined.prestructure,
            transition=record.joined.transition,
            metric_attestation=record.joined.metric_attestation,
            bridge_grid=record.joined.bridge_grid,
            dynamics_grid=record.joined.dynamics_grid,
        )

    def reverify_certificate(value):
        record = shallow_certificate(value)
        originating_outcome = record.originating_outcome()
        if originating_outcome is None:
            raise ValueError("originating outcome identity is not live")
        with lock:
            outcome_entry = outcome_registry.get(id_fn(originating_outcome))
        if (
            outcome_entry is None
            or outcome_entry[0]() is not originating_outcome
            or outcome_entry[1].certificate is None
            or outcome_entry[1].certificate() is not value
            or outcome_entry[1].outcome.certificate != record.certificate
        ):
            raise ValueError("certificate/originating-outcome lineage drifted")
        return certificate_view_type(
            certificate=snapshot(record.certificate),
            originating_outcome=originating_outcome,
            parent=record.joined.parent,
            materialization=record.joined.materialization,
            prestructure=record.joined.prestructure,
            transition=record.joined.transition,
            metric_attestation=record.joined.metric_attestation,
            bridge_grid=record.joined.bridge_grid,
            dynamics_grid=record.joined.dynamics_grid,
        )

    def certify(
        parent,
        materialization,
        transition,
        metric_attestation,
        bridge_grid,
        dynamics_grid,
    ):
        joined = atomic_join(
            parent,
            materialization,
            transition,
            metric_attestation,
            bridge_grid,
            dynamics_grid,
        )
        return register(run_pipeline(joined), joined)

    def verify_certificate(
        certificate,
        parent,
        materialization,
        transition,
        metric_attestation,
        bridge_grid,
        dynamics_grid,
    ):
        joined = atomic_join(
            parent,
            materialization,
            transition,
            metric_attestation,
            bridge_grid,
            dynamics_grid,
        )
        exact_record_validator(
            certificate,
            certificate_body_type,
            "certificate v3",
        )
        certificate_validator(certificate)
        expected = run_pipeline(joined)
        if expected.certificate is None:
            raise ValueError("live replay does not produce a successful certificate")
        if certificate != expected.certificate:
            raise ValueError("certificate differs from complete live replay")
        verified_outcome = register(expected, joined)
        result = verified_outcome.certificate
        if result is None:
            raise AssertionError("successful replay lost its certificate capability")
        return result

    def verify_outcome(
        outcome,
        parent,
        materialization,
        transition,
        metric_attestation,
        bridge_grid,
        dynamics_grid,
    ):
        joined = atomic_join(
            parent,
            materialization,
            transition,
            metric_attestation,
            bridge_grid,
            dynamics_grid,
        )
        exact_record_validator(
            outcome,
            outcome_body_type,
            "outcome v3",
        )
        outcome_validator(outcome)
        expected = run_pipeline(joined)
        if outcome != expected.outcome:
            raise ValueError("outcome differs from complete live replay")
        return register(expected, joined)

    def require_certificate(outcome):
        view = reverify_outcome(outcome)
        if not view.outcome.status.defined or view.certificate is None:
            raise ValueError("successful dynamics certificate is required")
        certificate_view = reverify_certificate(view.certificate)
        if certificate_view.originating_outcome is not outcome:
            raise ValueError("certificate does not originate from this outcome")
        return view.certificate

    def authority_counts():
        with lock:
            return len(outcome_registry), len(certificate_registry)

    return _freeze_certificate_v3_graph(
        _CertificateV3Graph(
            certify,
            verify_certificate,
            verify_outcome,
            require_certificate,
            reverify_certificate,
            reverify_outcome,
            authority_counts,
        )
    )


def _freeze_certificate_v3_graph(graph: _CertificateV3Graph) -> _CertificateV3Graph:
    """Clone the transitive project call graph while retaining live state.

    Functions and private builtins are snapshotted, including cross-owner
    project functions reached through closures, defaults, globals, modules, or
    partials.  Exact classes, locks, weak registries, and capability registries
    deliberately retain identity.
    """

    function_memo: dict[int, Callable] = {}
    partial_memo: dict[int, object] = {}
    partial_freezing: set[int] = set()
    module_memo: dict[tuple[int, tuple[str, ...]], object] = {}
    container_function_memo: dict[int, bool] = {}
    container_scanning: set[int] = set()
    frozen_container_memo: dict[int, object] = {}
    container_freezing: set[int] = set()

    def referenced_code_names(code: types.CodeType) -> tuple[str, ...]:
        names = list(code.co_names)
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                names.extend(referenced_code_names(constant))
        return tuple(dict.fromkeys(names))

    def make_cell(value: object):
        def read_cell():
            return value

        return read_cell.__closure__[0]

    def container_children(value: object):
        if isinstance(value, functools.partial):
            yield value.func
            yield from value.args
            yield from (value.keywords or {}).values()
        elif type(value) is dict:
            for key, item in value.items():
                yield key
                yield item
        elif type(value) is tuple or type(value) is list:
            yield from value

    def contains_project_function(value: object):
        if inspect.isfunction(value):
            return value.__module__.startswith("rulespace_v3.")
        if not (
            isinstance(value, functools.partial) or type(value) in (tuple, list, dict)
        ):
            return False
        identity = id(value)
        cached = container_function_memo.get(identity)
        if cached is not None:
            return cached
        if identity in container_scanning:
            return None
        container_scanning.add(identity)
        unresolved_cycle = False
        try:
            for child in container_children(value):
                observed = contains_project_function(child)
                if observed is True:
                    container_function_memo[identity] = True
                    return True
                if observed is None:
                    unresolved_cycle = True
        finally:
            container_scanning.remove(identity)
        if unresolved_cycle:
            return None
        container_function_memo[identity] = False
        return False

    def is_live_registry_name(name: Optional[str]) -> bool:
        if name is None:
            return False
        normalized = name.lstrip("_")
        return normalized in (
            "registry",
            "bindings",
            "records",
            "authorities",
        ) or normalized.endswith(("_registry", "_bindings", "_records", "_authorities"))

    def freeze_container(
        value: object,
        referenced_names: tuple[str, ...],
        state_name: Optional[str],
    ):
        # Named authority registries are live state, not code, and always keep
        # identity.  Other containers are copied only when they recursively
        # transport a project function into the private graph.  Both scans and
        # copies are cycle-safe for recursive list/dict structures.
        if is_live_registry_name(state_name):
            return value
        if contains_project_function(value) is not True:
            return value
        identity = id(value)
        cached = frozen_container_memo.get(identity)
        if cached is not None:
            return cached
        if identity in container_freezing:
            if type(value) is tuple:
                raise ValueError(
                    "transitive freezer cannot represent an immutable container cycle"
                )
            raise RuntimeError("mutable container cycle lacks its shared memo entry")
        container_freezing.add(identity)
        try:
            if type(value) is list:
                result: object = []
                frozen_container_memo[identity] = result
                result.extend(freeze_value(item, referenced_names) for item in value)
                return result
            if type(value) is dict:
                result = {}
                frozen_container_memo[identity] = result
                for key, item in value.items():
                    result[freeze_value(key, referenced_names)] = freeze_value(
                        item,
                        referenced_names,
                    )
                return result
            result = tuple(freeze_value(item, referenced_names) for item in value)
            frozen_container_memo[identity] = result
            return result
        finally:
            container_freezing.remove(identity)

    def freeze_value(
        value: object,
        referenced_names: tuple[str, ...] = (),
        state_name: Optional[str] = None,
    ):
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if isinstance(value, functools.partial):
            cached_partial = partial_memo.get(id(value))
            if cached_partial is not None:
                return cached_partial
            if id(value) in partial_freezing:
                raise ValueError(
                    "transitive freezer cannot represent a positional partial cycle"
                )
            partial_freezing.add(id(value))
            try:
                frozen_function = freeze_value(value.func, referenced_names)
                frozen_arguments = tuple(
                    freeze_value(item, referenced_names) for item in value.args
                )
                frozen = functools.partial(
                    frozen_function,
                    *frozen_arguments,
                )
                partial_memo[id(value)] = frozen
                frozen.keywords.update(
                    {
                        key: freeze_value(item, referenced_names)
                        for key, item in (value.keywords or {}).items()
                    }
                )
                return frozen
            except Exception:
                partial_memo.pop(id(value), None)
                raise
            finally:
                partial_freezing.remove(id(value))
        if inspect.ismodule(value) and value.__name__.startswith("rulespace_v3."):
            key = (id(value), referenced_names)
            cached_module = module_memo.get(key)
            if cached_module is not None:
                return cached_module
            proxy = types.SimpleNamespace()
            module_memo[key] = proxy
            module_values = vars(value)
            for name in referenced_names:
                if name in module_values:
                    setattr(
                        proxy,
                        name,
                        freeze_value(
                            module_values[name],
                            referenced_names,
                            name,
                        ),
                    )
            return proxy
        if type(value) in (tuple, list, dict):
            return freeze_container(value, referenced_names, state_name)
        return value

    def freeze_closure_value(
        value: object,
        state_name: str,
        referenced_names: tuple[str, ...],
    ):
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if isinstance(value, functools.partial):
            return freeze_value(value, referenced_names, state_name)
        if inspect.ismodule(value) and value.__name__.startswith("rulespace_v3."):
            return freeze_value(value, referenced_names, state_name)
        if type(value) in (tuple, list, dict):
            return freeze_container(value, referenced_names, state_name)
        return value

    def freeze_function(function: Callable) -> Callable:
        cached = function_memo.get(id(function))
        if cached is not None:
            return cached
        source_globals = function.__globals__
        builtins_body = source_globals.get("__builtins__", {})
        private_builtins = (
            dict(builtins_body)
            if type(builtins_body) is dict
            else dict(vars(builtins_body))
        )
        private_globals: dict[str, object] = {
            "__builtins__": private_builtins,
            "__name__": source_globals.get("__name__", __name__),
            "__package__": source_globals.get("__package__", __package__),
        }
        source_closure = function.__closure__
        private_cells = (
            None
            if source_closure is None
            else tuple(make_cell(None) for _ in source_closure)
        )
        clone = types.FunctionType(
            function.__code__,
            private_globals,
            function.__name__,
            None,
            private_cells,
        )
        function_memo[id(function)] = clone
        names = referenced_code_names(function.__code__)
        if source_closure is not None:
            assert private_cells is not None
            for name, private_cell, source_cell in zip(
                function.__code__.co_freevars,
                private_cells,
                source_closure,
            ):
                private_cell.cell_contents = freeze_closure_value(
                    source_cell.cell_contents,
                    name,
                    names,
                )
        for name in names:
            if name in source_globals:
                private_globals[name] = freeze_value(
                    source_globals[name],
                    names,
                    name,
                )
        clone.__defaults__ = (
            None
            if function.__defaults__ is None
            else tuple(freeze_value(item) for item in function.__defaults__)
        )
        clone.__kwdefaults__ = (
            None
            if function.__kwdefaults__ is None
            else {
                key: freeze_value(item) for key, item in function.__kwdefaults__.items()
            }
        )
        clone.__annotations__ = dict(function.__annotations__)
        clone.__dict__.update(function.__dict__)
        clone.__doc__ = function.__doc__
        clone.__module__ = function.__module__
        clone.__qualname__ = function.__qualname__
        return clone

    return _CertificateV3Graph(*(freeze_function(function) for function in graph))


def _read_parent_body(parent: object) -> object:
    return parent.manifest


def _read_factory_body(factory: object) -> object:
    return factory.factory


def _read_factory_role(factory: object) -> str:
    return factory.role


def _missing_runtime_v3_authority(*args, **kwargs):
    del args, kwargs
    raise RuntimeError("private Parent-v3 runtime authority is not installed")


_PRODUCTION_DEPENDENCIES = _CertificateV3Dependencies(
    parent_type=VerifiedParentFreezeV3,
    materialization_type=VerifiedV3M0ApplicationScenarioMaterializationV3,
    transition_type=VerifiedTransitionAuthorityV3,
    measured_transition_type=MeasuredTransition,
    metric_attestation_type=VerifiedMetricSignedSupportAttestationV1,
    bridge_grid_type=VerifiedBridgeGridAuthorityV3,
    dynamics_grid_type=VerifiedDynamicsGridAuthorityV3,
    parent_reader=_read_parent_body,
    materialization_requirer=(
        _require_v3m0_application_scenario_materialization_v3_for_parent
    ),
    transition_reverifier=_reverify_verified_transition_authority_v3,
    metric_reverifier=(_reverify_verified_metric_signed_support_attestation_v1),
    bridge_grid_reverifier=_reverify_verified_bridge_grid_authority_v3,
    dynamics_grid_reverifier=_reverify_verified_dynamics_grid_authority_v3,
    factory_body_reader=_read_factory_body,
    factory_role_reader=_read_factory_role,
    structure_builder=_build_bound_synthetic_structure_manifest,
    reality_builder=_build_reality_certificate_from_raw,
    metric_builder=_build_bound_synthetic_identity_metric,
    laurent_preflight=_preflight_laurent_resources_from_raw,
    instability_builder=_build_instability_growth_counter_witness_from_raw,
    instability_verifier=verify_instability_growth_counter_witness_arithmetic,
    protocol_builder=build_fp64_enclosure_protocol,
    protocol_verifier=verify_fp64_enclosure_protocol,
    residual_builder=_build_laurent_residual_from_raw,
    spectral_builder=_build_spectral_margin_coverage_from_raw,
    normalized_builder=_build_normalized_metric_residual_audit_from_raw,
    bridge_spec_builder=_build_bound_full_state_bridge_spec,
    bridge_audit_builder=_audit_full_state_bridge_from_raw,
    power_builder=_build_power_drift_audit_from_raw,
    runtime_issuer=getattr(
        _runtime,
        "_issue_runtime_evidence_manifest_v3",
        _missing_runtime_v3_authority,
    ),
    runtime_verifier=getattr(
        _runtime,
        "_verify_runtime_evidence_manifest_v3",
        _missing_runtime_v3_authority,
    ),
    sha_builder=canonical_sha,
    clone=copy.deepcopy,
)
_PRODUCTION_GRAPH = _make_certificate_v3_graph(
    _ISSUANCE_TOKEN,
    _PRODUCTION_DEPENDENCIES,
)


def _make_public_apis(graph: _CertificateV3Graph):
    certify_fn = graph.certify
    verify_certificate_fn = graph.verify_certificate
    verify_outcome_fn = graph.verify_outcome
    require_certificate_fn = graph.require_certificate
    reverify_certificate_fn = graph.reverify_certificate
    reverify_outcome_fn = graph.reverify_outcome

    def certify_transition_dynamics_v3(
        parent: VerifiedParentFreezeV3,
        materialization: VerifiedV3M0ApplicationScenarioMaterializationV3,
        transition: VerifiedTransitionAuthorityV3,
        metric_attestation: VerifiedMetricSignedSupportAttestationV1,
        bridge_grid: VerifiedBridgeGridAuthorityV3,
        dynamics_grid: VerifiedDynamicsGridAuthorityV3,
    ) -> VerifiedDynamicsCertificationOutcomeV3:
        return certify_fn(
            parent,
            materialization,
            transition,
            metric_attestation,
            bridge_grid,
            dynamics_grid,
        )

    def verify_dynamics_certificate_v3(
        certificate: DynamicsCertificateV3,
        parent: VerifiedParentFreezeV3,
        materialization: VerifiedV3M0ApplicationScenarioMaterializationV3,
        transition: VerifiedTransitionAuthorityV3,
        metric_attestation: VerifiedMetricSignedSupportAttestationV1,
        bridge_grid: VerifiedBridgeGridAuthorityV3,
        dynamics_grid: VerifiedDynamicsGridAuthorityV3,
    ) -> VerifiedDynamicsCertificateV3:
        return verify_certificate_fn(
            certificate,
            parent,
            materialization,
            transition,
            metric_attestation,
            bridge_grid,
            dynamics_grid,
        )

    def verify_dynamics_certification_outcome_v3(
        outcome: DynamicsCertificationOutcomeV3,
        parent: VerifiedParentFreezeV3,
        materialization: VerifiedV3M0ApplicationScenarioMaterializationV3,
        transition: VerifiedTransitionAuthorityV3,
        metric_attestation: VerifiedMetricSignedSupportAttestationV1,
        bridge_grid: VerifiedBridgeGridAuthorityV3,
        dynamics_grid: VerifiedDynamicsGridAuthorityV3,
    ) -> VerifiedDynamicsCertificationOutcomeV3:
        return verify_outcome_fn(
            outcome,
            parent,
            materialization,
            transition,
            metric_attestation,
            bridge_grid,
            dynamics_grid,
        )

    def require_dynamics_certificate_v3(
        outcome: VerifiedDynamicsCertificationOutcomeV3,
    ) -> VerifiedDynamicsCertificateV3:
        return require_certificate_fn(outcome)

    def _reverify_verified_dynamics_certificate_v3(certificate):
        return reverify_certificate_fn(certificate)

    def _reverify_verified_dynamics_certification_outcome_v3(outcome):
        return reverify_outcome_fn(outcome)

    return (
        certify_transition_dynamics_v3,
        verify_dynamics_certificate_v3,
        verify_dynamics_certification_outcome_v3,
        require_dynamics_certificate_v3,
        _reverify_verified_dynamics_certificate_v3,
        _reverify_verified_dynamics_certification_outcome_v3,
    )


(
    certify_transition_dynamics_v3,
    verify_dynamics_certificate_v3,
    verify_dynamics_certification_outcome_v3,
    require_dynamics_certificate_v3,
    _reverify_verified_dynamics_certificate_v3,
    _reverify_verified_dynamics_certification_outcome_v3,
) = _make_public_apis(_PRODUCTION_GRAPH)


__all__ = (
    "CERTIFICATE_V3_SCHEMA_VERSION",
    "CERTIFICATION_ATTEMPT_V3_SCHEMA_VERSION",
    "DynamicsCertificateV3",
    "DynamicsCertificationAttemptAuditV3",
    "DynamicsCertificationFailure",
    "DynamicsCertificationOutcomeV3",
    "DynamicsCertificationUpstreamJoinFailure",
    "VerifiedDynamicsCertificateV3",
    "VerifiedDynamicsCertificationOutcomeV3",
    "certify_transition_dynamics_v3",
    "dynamics_certificate_v3_payload",
    "dynamics_certification_attempt_audit_v3_payload",
    "dynamics_certification_outcome_v3_payload",
    "require_dynamics_certificate_v3",
    "verify_dynamics_certificate_v3",
    "verify_dynamics_certification_outcome_v3",
)
