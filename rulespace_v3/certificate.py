"""Recursive Task-10 dynamics certificates and typed certification outcomes.

The raw records in this module are inert, self-hashed evidence bodies.  Live
authority is carried only by module-issued opaque wrappers.  Certificate
verification remeasures the full-state transition and replays every full-state
bridge case; hashes are bindings, never substitutes for those executions.
"""

from __future__ import annotations

import hashlib  # noqa: F401  # Compatibility probe; hashing is closure-captured.
import functools
import inspect
import json  # noqa: F401  # Compatibility probe; hashing is closure-captured.
import math
import re
import threading
import types
import weakref
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from typing import Callable, Optional

from . import laurent as _laurent
from . import spectral as _spectral
from .bridge import (
    BRIDGE_TOLERANCE,
    BridgeAudit,
    FullStateBridgeSpec,
    audit_full_state_bridge,
    bridge_audit_payload,
    build_full_state_bridge_spec,
    full_state_bridge_spec_payload,
    verify_full_state_bridge_audit,
    verify_full_state_bridge_spec,
)
from .contracts import BlockStatus, UndefinedReason
from .dynamics import (
    MeasuredTransition,
    VerifiedTransition,
    _reverify_verified_transition,
    measure_transition,
    measured_transition_payload,
    verify_measured_transition,
)
from .evidence import _EXACT_JSON_SHA256
from .factory import (
    VerifiedFactory,
    _reverify_verified_factory,
)
from .fp64_protocol import (
    Fp64EnclosureProtocol,
    build_fp64_enclosure_protocol,
    fp64_enclosure_protocol_payload,
    verify_fp64_enclosure_protocol,
)
from .grids import (
    DynamicsKGridManifest,
    verify_dynamics_grid_manifest,
)
from .instability import (
    InstabilityGrowthCounterWitness,
    certify_instability_growth_counter_witness,
    instability_growth_counter_witness_payload,
    verify_instability_growth_counter_witness,
)
from .laurent import (
    LaurentResidualCertificate,
    laurent_residual_payload,
    verify_laurent_residual_certificate,
)
from .metric import (
    StabilityMetricWitness,
    build_stability_metric_witness,
    stability_metric_witness_payload,
    verify_stability_metric_witness,
)
from .prestructure import (
    PrestructureAuthority,
    VerifiedPrestructureAuthority,
    _reverify_verified_prestructure_authority,
    prestructure_authority_payload,
)
from .runtime import (
    RUNTIME_MAX_SOURCE_FILES,
    RuntimeEvidenceManifest,
    runtime_evidence_manifest_payload,
    verify_runtime_evidence_manifest,
)
from .replay_scope import (
    _cached_replay_is_valid,
    _record_successful_replay,
    _scoped_replay_context,
)
from .spectral import (
    NORMALIZED_METRIC_RESIDUAL_GATE,
    SPECTRAL_MAX_COLUMN_RAW_BYTES,
    NormalizedMetricResidualAudit,
    PowerDriftAudit,
    SpectralMarginCoverage,
    SpectralPointEnclosureColumnarSidecar,
    build_power_drift_audit,
    build_spectral_margin_coverage,
    certify_normalized_metric_residual_audit,
    normalized_metric_residual_audit_payload,
    power_drift_audit_payload,
    spectral_margin_coverage_payload,
    verify_normalized_metric_residual_audit,
    verify_power_drift_audit,
    verify_spectral_margin_coverage,
)
from .structure import (
    RealityCertificate,
    StructureManifest,
    build_structure_manifest,
    certify_reality,
    reality_certificate_payload,
    structure_manifest_payload,
    verify_reality_certificate,
    verify_structure_manifest,
)


CERTIFICATE_SCHEMA_VERSION = "v3m0.dynamics-certificate.v1"
CERTIFICATION_ATTEMPT_SCHEMA_VERSION = "v3m0.dynamics-certification-attempt.v1"
CERTIFICATION_OUTCOME_SCHEMA_VERSION = "v3m0.dynamics-certification-outcome.v1"
STRUCTURE_RAW_RESIDUAL_GATE = 1.0e-12
POWER_DRIFT_GATE = 1.0e-8
CERTIFICATE_MAX_BRIDGE_CASES = 6_144
CERTIFICATE_MAX_TEXT_BYTES = 16_384
CERTIFICATE_MAX_CANONICAL_BODY_BYTES = 268_435_456
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()
_VALIDATED_TOKEN = object()
_ZERO_SHA = "0" * 64


def _snapshot_exact_wire(
    value: object,
) -> object:
    """Clone a validated inert wire without invoking frozen-slot setters."""

    memo: dict[int, object] = {}
    active: set[int] = set()

    def snapshot(item: object) -> object:
        if item is None or type(item) in (bool, int, float, str, bytes):
            return item
        if isinstance(item, Enum):
            return item
        identity = id(item)
        if identity in active:
            raise ValueError("authority snapshot wire must be acyclic")
        cached = memo.get(identity)
        if cached is not None:
            return cached
        active.add(identity)
        try:
            if type(item) is tuple:
                clone = tuple(snapshot(child) for child in item)
                memo[identity] = clone
                return clone
            if type(item) is list:
                clone_list: list[object] = []
                memo[identity] = clone_list
                clone_list.extend(snapshot(child) for child in item)
                return clone_list
            if type(item) is dict:
                clone_dict: dict[object, object] = {}
                memo[identity] = clone_dict
                for key, child in item.items():
                    clone_dict[snapshot(key)] = snapshot(child)
                return clone_dict
            if is_dataclass(item) and not isinstance(item, type):
                clone_record = object.__new__(type(item))
                memo[identity] = clone_record
                for field in fields(item):
                    object.__setattr__(
                        clone_record,
                        field.name,
                        snapshot(getattr(item, field.name)),
                    )
                return clone_record
        finally:
            active.remove(identity)
        raise TypeError(
            "authority snapshot encountered a non-wire value "
            f"{type(item).__name__}"
        )

    return snapshot(value)


def _make_bounded_canonical_sha(
    *,
    _exact_sha=_EXACT_JSON_SHA256,
    _type=type,
    _dict_type=dict,
    _int_type=int,
    _type_error=TypeError,
):
    def bounded_canonical_sha(
        payload: dict[str, object],
        *,
        maximum_bytes: int = CERTIFICATE_MAX_CANONICAL_BODY_BYTES,
    ) -> str:
        if _type(payload) is not _dict_type:
            raise _type_error("canonical payload must be an exact dict")
        if _type(maximum_bytes) is not _int_type or maximum_bytes <= 0:
            raise _type_error("maximum_bytes must be a positive int")
        return _exact_sha(payload, maximum_bytes=maximum_bytes)

    return bounded_canonical_sha


_bounded_canonical_sha = _make_bounded_canonical_sha()


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _bounded_text(value: object, field: str) -> str:
    result = _text(value, field)
    if len(result.encode("utf-8")) > CERTIFICATE_MAX_TEXT_BYTES:
        raise ValueError(f"{field} exceeds its text resource cap")
    return result


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _exact_type(value: object, expected: type, field: str) -> object:
    if type(value) is not expected:
        raise TypeError(f"{field} must be an exact {expected.__name__}")
    return value


def _require_exact_record_fields(
    value: object,
    expected: type,
    field: str,
) -> None:
    _exact_type(value, expected, field)
    instance_fields = getattr(value, "__dict__", None)
    if type(instance_fields) is not dict:
        raise ValueError(f"{field} has no exact record field map")
    expected_fields = frozenset(item.name for item in fields(expected))
    if frozenset(instance_fields) != expected_fields:
        raise ValueError(f"{field} contains unknown or missing fields")
    _require_recursive_exact_record_fields(value, field)


def _require_recursive_exact_record_fields(
    root: object,
    field: str,
) -> None:
    pending: list[tuple[object, str]] = [(root, field)]
    seen: set[int] = set()
    while pending:
        value, path = pending.pop()
        if is_dataclass(value) and not isinstance(value, type):
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            record_type = type(value)
            dataclass_bases = tuple(
                base for base in record_type.__mro__[1:] if is_dataclass(base)
            )
            if dataclass_bases:
                raise TypeError(f"{path} has an unregistered dataclass subtype")
            expected_names = frozenset(item.name for item in fields(record_type))
            instance_fields = getattr(value, "__dict__", None)
            if instance_fields is not None:
                if (
                    type(instance_fields) is not dict
                    or frozenset(instance_fields) != expected_names
                ):
                    raise ValueError(f"{path} contains unknown or missing fields")
            for item in fields(record_type):
                pending.append((getattr(value, item.name), f"{path}.{item.name}"))
            continue
        if type(value) in (tuple, list):
            for index, item in enumerate(value):
                pending.append((item, f"{path}[{index}]"))
            continue
        if type(value) is dict:
            for key, item in value.items():
                pending.append((item, f"{path}[{key!r}]"))


def _status_payload(status: BlockStatus) -> dict[str, object]:
    _exact_type(status, BlockStatus, "status")
    return {
        "defined": status.defined,
        "reason": None if status.reason is None else status.reason.value,
    }


def _record(payload: dict[str, object], sha_field: str, sha: str) -> dict[str, object]:
    return {**payload, sha_field: sha}


def _transition_record(value: MeasuredTransition) -> dict[str, object]:
    return _record(
        measured_transition_payload(value),
        "transition_sha",
        value.transition_sha,
    )


def _prestructure_record(value: PrestructureAuthority) -> dict[str, object]:
    return _record(
        prestructure_authority_payload(value),
        "authority_sha",
        value.authority_sha,
    )


def _structure_record(value: StructureManifest) -> dict[str, object]:
    return _record(
        structure_manifest_payload(value),
        "structure_manifest_sha",
        value.structure_manifest_sha,
    )


def _reality_record(value: RealityCertificate) -> dict[str, object]:
    return _record(
        reality_certificate_payload(value),
        "reality_certificate_sha",
        value.reality_certificate_sha,
    )


def _metric_record(value: StabilityMetricWitness) -> dict[str, object]:
    return _record(
        stability_metric_witness_payload(value),
        "witness_sha",
        value.witness_sha,
    )


def _protocol_record(value: Fp64EnclosureProtocol) -> dict[str, object]:
    return _record(
        fp64_enclosure_protocol_payload(value),
        "protocol_sha",
        value.protocol_sha,
    )


def _bridge_spec_record(value: FullStateBridgeSpec) -> dict[str, object]:
    return _record(
        full_state_bridge_spec_payload(value),
        "bridge_spec_sha",
        value.bridge_spec_sha,
    )


def _bridge_audit_record(value: BridgeAudit) -> dict[str, object]:
    return _record(
        bridge_audit_payload(value),
        "bridge_sha",
        value.bridge_sha,
    )


def _residual_record(value: LaurentResidualCertificate) -> dict[str, object]:
    return _record(
        laurent_residual_payload(value),
        "residual_sha",
        value.residual_sha,
    )


def _spectral_record(value: SpectralMarginCoverage) -> dict[str, object]:
    return _record(
        spectral_margin_coverage_payload(value),
        "coverage_sha",
        value.coverage_sha,
    )


def _normalized_record(value: NormalizedMetricResidualAudit) -> dict[str, object]:
    return _record(
        normalized_metric_residual_audit_payload(value),
        "audit_sha",
        value.audit_sha,
    )


def _power_record(value: PowerDriftAudit) -> dict[str, object]:
    return _record(
        power_drift_audit_payload(value),
        "audit_sha",
        value.audit_sha,
    )


def _runtime_record(value: RuntimeEvidenceManifest) -> dict[str, object]:
    return _record(
        runtime_evidence_manifest_payload(value),
        "runtime_manifest_sha",
        value.runtime_manifest_sha,
    )


def _instability_record(
    value: InstabilityGrowthCounterWitness,
) -> dict[str, object]:
    return _record(
        instability_growth_counter_witness_payload(value),
        "witness_sha",
        value.witness_sha,
    )


class DynamicsCertificationFailure(str, Enum):
    PRESTRUCTURE_INVALID = "prestructure_invalid"
    TRANSITION_INVALID = "transition_invalid"
    REALITY_INVALID = "reality_invalid"
    LAURENT_RESOURCE_EXCEEDED = "laurent_resource_exceeded"
    STRUCTURE_RAW_UNRESOLVED = "structure_raw_unresolved"
    METRIC_RAW_UNRESOLVED = "metric_raw_unresolved"
    SPECTRAL_COVERAGE_UNRESOLVED = "spectral_coverage_unresolved"
    NORMALIZED_METRIC_UNRESOLVED = "normalized_metric_unresolved"
    FULL_STATE_BRIDGE_FAILED = "full_state_bridge_failed"
    POWER_DRIFT_UNRESOLVED = "power_drift_unresolved"
    CERTIFIED_INSTABILITY_COUNTERWITNESS = "certified_instability_counterwitness"


@dataclass(frozen=True)
class DynamicsCertificate:
    certificate_schema_version: str
    transition: MeasuredTransition
    prestructure_authority: PrestructureAuthority
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

    def __post_init__(self) -> None:
        _bounded_text(
            self.certificate_schema_version,
            "certificate_schema_version",
        )
        _preflight_certificate_shape(self)
        _sha(self.certificate_sha, "certificate_sha")


@dataclass(frozen=True)
class DynamicsCertificationAttemptAudit:
    attempt_schema_version: str
    factory_sha: str
    transition_sha: Optional[str]
    prestructure_authority_sha: str
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

    def __post_init__(self) -> None:
        _bounded_text(
            self.attempt_schema_version,
            "attempt_schema_version",
        )
        _sha(self.factory_sha, "factory_sha")
        if self.transition_sha is not None:
            _sha(self.transition_sha, "transition_sha")
        _sha(
            self.prestructure_authority_sha,
            "prestructure_authority_sha",
        )
        if (
            self.first_failure is not None
            and type(self.first_failure) is not DynamicsCertificationFailure
        ):
            raise TypeError(
                "first_failure must be a DynamicsCertificationFailure or None"
            )
        for field, expected in (
            ("reality", RealityCertificate),
            ("structure_residual", LaurentResidualCertificate),
            ("metric_residual", LaurentResidualCertificate),
            ("spectral_margins", SpectralMarginCoverage),
            ("normalized_metric_residual", NormalizedMetricResidualAudit),
            ("full_state_bridge_audit", BridgeAudit),
            ("power_drift", PowerDriftAudit),
            (
                "instability_counter_witness",
                InstabilityGrowthCounterWitness,
            ),
        ):
            value = getattr(self, field)
            if value is not None:
                _exact_type(value, expected, field)
        _sha(self.attempt_sha, "attempt_sha")


@dataclass(frozen=True)
class DynamicsCertificationOutcome:
    status: BlockStatus
    failure: Optional[DynamicsCertificationFailure]
    attempt_audit: DynamicsCertificationAttemptAudit
    certificate: Optional[DynamicsCertificate]
    outcome_sha: str

    def __post_init__(self) -> None:
        _exact_type(self.status, BlockStatus, "status")
        if (
            self.failure is not None
            and type(self.failure) is not DynamicsCertificationFailure
        ):
            raise TypeError("failure must be a DynamicsCertificationFailure or None")
        _exact_type(
            self.attempt_audit,
            DynamicsCertificationAttemptAudit,
            "attempt_audit",
        )
        if self.certificate is not None:
            _exact_type(
                self.certificate,
                DynamicsCertificate,
                "certificate",
            )
        _sha(self.outcome_sha, "outcome_sha")


def _preflight_sidecar(sidecar: object) -> None:
    _exact_type(
        sidecar,
        SpectralPointEnclosureColumnarSidecar,
        "spectral_margins.point_enclosures",
    )
    point_count = sidecar.point_count
    if type(point_count) is not int or not 0 < point_count <= 262_144:
        raise ValueError("spectral sidecar point count exceeds resource cap")
    maximum_encoded = 4 * ((SPECTRAL_MAX_COLUMN_RAW_BYTES + 2) // 3)
    for field in (
        "raw_m_sigma_min_b64",
        "raw_m_sigma_max_b64",
        "raw_g_lambda_min_b64",
        "raw_g_lambda_max_b64",
        "transition_symbol_error_upper_b64",
        "metric_symbol_error_upper_b64",
        "transition_frobenius_upper_b64",
        "inverse_frobenius_upper_b64",
        "inverse_residual_frobenius_upper_b64",
        "m_sigma_min_lower_b64",
        "m_sigma_max_upper_b64",
        "metric_frobenius_upper_b64",
        "cholesky_factorization_residual_frobenius_upper_b64",
        "cholesky_inverse_frobenius_upper_b64",
        "cholesky_inverse_residual_frobenius_upper_b64",
        "ell_lower_b64",
        "g_lambda_min_lower_b64",
        "g_lambda_max_upper_b64",
    ):
        value = getattr(sidecar, field)
        if value is None:
            continue
        if type(value) is not str:
            raise TypeError(f"{field} must be a string or None")
        if len(value) > maximum_encoded:
            raise ValueError(f"{field} exceeds its encoded resource cap")
    if (
        type(sidecar.raw_byte_count) is not int
        or sidecar.raw_byte_count < 0
        or sidecar.raw_byte_count > SPECTRAL_MAX_COLUMN_RAW_BYTES
    ):
        raise ValueError("spectral raw byte count exceeds resource cap")


def _preflight_certificate_shape(certificate: object) -> None:
    _require_exact_record_fields(
        certificate,
        DynamicsCertificate,
        "certificate",
    )
    for field, expected in (
        ("transition", MeasuredTransition),
        ("prestructure_authority", PrestructureAuthority),
        ("structure", StructureManifest),
        ("stability_metric", StabilityMetricWitness),
        ("fp64_enclosure_protocol", Fp64EnclosureProtocol),
        ("full_state_bridge_spec", FullStateBridgeSpec),
        ("full_state_bridge_audit", BridgeAudit),
        ("structure_residual", LaurentResidualCertificate),
        ("metric_residual", LaurentResidualCertificate),
        ("spectral_margins", SpectralMarginCoverage),
        ("normalized_metric_residual", NormalizedMetricResidualAudit),
        ("power_drift", PowerDriftAudit),
        ("runtime", RuntimeEvidenceManifest),
    ):
        _exact_type(getattr(certificate, field), expected, field)
    if certificate.reality is not None:
        _exact_type(certificate.reality, RealityCertificate, "reality")
    if type(certificate.full_state_bridge_audit.cases) is not tuple:
        raise TypeError("full_state_bridge_audit.cases must be a tuple")
    if len(certificate.full_state_bridge_audit.cases) > CERTIFICATE_MAX_BRIDGE_CASES:
        raise ValueError("bridge audit case count exceeds certificate cap")
    if type(certificate.runtime.source_closure) is not tuple:
        raise TypeError("runtime.source_closure must be a tuple")
    if len(certificate.runtime.source_closure) > RUNTIME_MAX_SOURCE_FILES:
        raise ValueError("runtime source closure exceeds certificate cap")
    _spectral._preflight_root64_protocol(certificate.fp64_enclosure_protocol)
    _laurent._preflight_raw_laurent_cardinality(certificate.structure_residual)
    _laurent._preflight_raw_laurent_cardinality(certificate.metric_residual)
    transition_entries = math.prod(certificate.transition.kernel.shape)
    if (
        type(certificate.transition.kernel.values_wire) is not tuple
        or len(certificate.transition.kernel.values_wire) != transition_entries
        or transition_entries > 16_777_216
    ):
        raise ValueError("transition kernel exceeds certificate cap")
    metric_entries = math.prod(certificate.stability_metric.metric_kernel.shape)
    if (
        type(certificate.stability_metric.metric_kernel.values_wire) is not tuple
        or len(certificate.stability_metric.metric_kernel.values_wire) != metric_entries
        or metric_entries > 16_777_216
    ):
        raise ValueError("metric kernel exceeds certificate cap")
    _preflight_sidecar(certificate.spectral_margins.point_enclosures)


def dynamics_certificate_payload(
    certificate: DynamicsCertificate,
) -> dict[str, object]:
    _preflight_certificate_shape(certificate)
    return {
        "certificate_schema_version": (certificate.certificate_schema_version),
        "transition": _transition_record(certificate.transition),
        "prestructure_authority": _prestructure_record(
            certificate.prestructure_authority
        ),
        "structure": _structure_record(certificate.structure),
        "reality": (
            None
            if certificate.reality is None
            else _reality_record(certificate.reality)
        ),
        "stability_metric": _metric_record(certificate.stability_metric),
        "fp64_enclosure_protocol": _protocol_record(
            certificate.fp64_enclosure_protocol
        ),
        "full_state_bridge_spec": _bridge_spec_record(
            certificate.full_state_bridge_spec
        ),
        "full_state_bridge_audit": _bridge_audit_record(
            certificate.full_state_bridge_audit
        ),
        "structure_residual": _residual_record(certificate.structure_residual),
        "metric_residual": _residual_record(certificate.metric_residual),
        "spectral_margins": _spectral_record(certificate.spectral_margins),
        "normalized_metric_residual": _normalized_record(
            certificate.normalized_metric_residual
        ),
        "power_drift": _power_record(certificate.power_drift),
        "runtime": _runtime_record(certificate.runtime),
    }


def dynamics_certification_attempt_audit_payload(
    audit: DynamicsCertificationAttemptAudit,
) -> dict[str, object]:
    _require_exact_record_fields(
        audit,
        DynamicsCertificationAttemptAudit,
        "attempt_audit",
    )
    audit.__post_init__()
    return {
        "attempt_schema_version": audit.attempt_schema_version,
        "factory_sha": audit.factory_sha,
        "transition_sha": audit.transition_sha,
        "prestructure_authority_sha": (audit.prestructure_authority_sha),
        "first_failure": (
            None if audit.first_failure is None else audit.first_failure.value
        ),
        "reality": (None if audit.reality is None else _reality_record(audit.reality)),
        "structure_residual": (
            None
            if audit.structure_residual is None
            else _residual_record(audit.structure_residual)
        ),
        "metric_residual": (
            None
            if audit.metric_residual is None
            else _residual_record(audit.metric_residual)
        ),
        "spectral_margins": (
            None
            if audit.spectral_margins is None
            else _spectral_record(audit.spectral_margins)
        ),
        "normalized_metric_residual": (
            None
            if audit.normalized_metric_residual is None
            else _normalized_record(audit.normalized_metric_residual)
        ),
        "full_state_bridge_audit": (
            None
            if audit.full_state_bridge_audit is None
            else _bridge_audit_record(audit.full_state_bridge_audit)
        ),
        "power_drift": (
            None if audit.power_drift is None else _power_record(audit.power_drift)
        ),
        "instability_counter_witness": (
            None
            if audit.instability_counter_witness is None
            else _instability_record(audit.instability_counter_witness)
        ),
    }


def _certificate_record(value: DynamicsCertificate) -> dict[str, object]:
    return _record(
        dynamics_certificate_payload(value),
        "certificate_sha",
        value.certificate_sha,
    )


def dynamics_certification_outcome_payload(
    outcome: DynamicsCertificationOutcome,
) -> dict[str, object]:
    _require_exact_record_fields(
        outcome,
        DynamicsCertificationOutcome,
        "outcome",
    )
    return {
        "outcome_schema_version": CERTIFICATION_OUTCOME_SCHEMA_VERSION,
        "status": _status_payload(outcome.status),
        "failure": (None if outcome.failure is None else outcome.failure.value),
        "attempt_audit": _record(
            dynamics_certification_attempt_audit_payload(outcome.attempt_audit),
            "attempt_sha",
            outcome.attempt_audit.attempt_sha,
        ),
        "certificate": (
            None
            if outcome.certificate is None
            else _certificate_record(outcome.certificate)
        ),
    }


_FAILURE_REASONS = {
    DynamicsCertificationFailure.PRESTRUCTURE_INVALID: (
        UndefinedReason.PRESTRUCTURE_INVALID
    ),
    DynamicsCertificationFailure.TRANSITION_INVALID: (
        UndefinedReason.MANIFEST_MISMATCH
    ),
    DynamicsCertificationFailure.REALITY_INVALID: (UndefinedReason.REALITY_VIOLATION),
    DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED: (
        UndefinedReason.LAURENT_RESOURCE_EXCEEDED
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
    DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS: (
        UndefinedReason.UNSTABLE
    ),
}


def _verify_attempt_sha(
    audit: DynamicsCertificationAttemptAudit,
) -> None:
    if audit.attempt_schema_version != CERTIFICATION_ATTEMPT_SCHEMA_VERSION:
        raise ValueError("unexpected certification attempt schema")
    if audit.attempt_sha != _bounded_canonical_sha(
        dynamics_certification_attempt_audit_payload(audit)
    ):
        raise ValueError("attempt_sha does not match complete body")


def _validate_outcome_presence(
    outcome: DynamicsCertificationOutcome,
) -> None:
    outcome.__post_init__()
    _verify_attempt_sha(outcome.attempt_audit)
    if outcome.outcome_sha != _bounded_canonical_sha(
        dynamics_certification_outcome_payload(outcome)
    ):
        raise ValueError("outcome_sha does not match complete body")
    audit = outcome.attempt_audit
    if audit.first_failure is not outcome.failure:
        raise ValueError("attempt first_failure and outcome failure differ")
    success = outcome.failure is None
    if outcome.status.defined is not success:
        raise ValueError("status.defined and failure presence differ")
    if success:
        if outcome.status.reason is not None or outcome.certificate is None:
            raise ValueError("successful outcome lacks raw certificate")
        if audit.transition_sha is None:
            raise ValueError("successful attempt lacks transition SHA")
        for field in (
            "structure_residual",
            "metric_residual",
            "spectral_margins",
            "normalized_metric_residual",
            "full_state_bridge_audit",
            "power_drift",
        ):
            if getattr(audit, field) is None:
                raise ValueError(f"successful attempt lacks {field}")
        quantum = outcome.certificate.structure.evidence_lane == "quantum"
        if quantum != (audit.reality is None):
            raise ValueError(
                "reality presence does not match certificate evidence lane"
            )
        if audit.instability_counter_witness is not None:
            raise ValueError("successful attempt cannot contain instability")
        return
    if outcome.certificate is not None:
        raise ValueError("failed outcome must not contain a certificate")
    expected_reason = _FAILURE_REASONS[outcome.failure]
    if outcome.status.reason is not expected_reason:
        raise ValueError("failure and BlockStatus reason are inconsistent")
    has_counter = audit.instability_counter_witness is not None
    is_counter = (
        outcome.failure
        is DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS
    )
    if has_counter is not is_counter:
        raise ValueError("instability witness presence does not match counter-failure")
    ordered = (
        "reality",
        "structure_residual",
        "metric_residual",
        "spectral_margins",
        "normalized_metric_residual",
        "full_state_bridge_audit",
        "power_drift",
    )
    failure_stage = {
        DynamicsCertificationFailure.PRESTRUCTURE_INVALID: -2,
        DynamicsCertificationFailure.TRANSITION_INVALID: -1,
        DynamicsCertificationFailure.REALITY_INVALID: 0,
        DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED: 1,
        DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS: 1,
        DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED: 1,
        DynamicsCertificationFailure.METRIC_RAW_UNRESOLVED: 2,
        DynamicsCertificationFailure.SPECTRAL_COVERAGE_UNRESOLVED: 3,
        DynamicsCertificationFailure.NORMALIZED_METRIC_UNRESOLVED: 4,
        DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED: 5,
        DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED: 6,
    }[outcome.failure]
    for index, field in enumerate(ordered):
        if index > failure_stage and getattr(audit, field) is not None:
            raise ValueError(f"unreached attempt stage {field} is populated")
    if failure_stage < 0 and audit.transition_sha is not None:
        raise ValueError("pre-transition failure contains transition SHA")
    if failure_stage >= 1 and audit.reality is None:
        raise ValueError("post-reality failure lacks reality evidence")
    if failure_stage >= 2 and audit.structure_residual is None:
        raise ValueError("post-structure failure lacks structure evidence")
    if failure_stage >= 3 and audit.metric_residual is None:
        raise ValueError("post-metric failure lacks metric evidence")
    if failure_stage >= 4 and audit.spectral_margins is None:
        raise ValueError("post-spectral failure lacks spectral evidence")
    if failure_stage >= 5 and audit.normalized_metric_residual is None:
        raise ValueError("post-normalized failure lacks normalized evidence")
    if failure_stage >= 6 and audit.full_state_bridge_audit is None:
        raise ValueError("post-bridge failure lacks bridge evidence")


class VerifiedDynamicsCertificate:
    """Opaque live capability for a fully replayed dynamics certificate."""

    __slots__ = ("__certificate", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        certificate: DynamicsCertificate,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("VerifiedDynamicsCertificate is module-issued")
        object.__setattr__(
            self,
            "_VerifiedDynamicsCertificate__certificate",
            certificate,
        )
        object.__setattr__(
            self,
            "_VerifiedDynamicsCertificate__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedDynamicsCertificate__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedDynamicsCertificate is immutable")

    @property
    def certificate(self) -> DynamicsCertificate:
        return self.__certificate


@dataclass(frozen=True)
class _VerifiedCertificateRecord:
    certificate: DynamicsCertificate
    factory: VerifiedFactory
    authority: VerifiedPrestructureAuthority
    seal: str


def _certificate_seal(certificate: DynamicsCertificate) -> str:
    return _bounded_canonical_sha(
        {
            "verified_certificate_schema_version": (
                "v3m0.verified-dynamics-certificate.v1"
            ),
            "certificate": _certificate_record(certificate),
        }
    )


def _validate_certificate(
    certificate: DynamicsCertificate,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> None:
    _preflight_certificate_shape(certificate)
    if certificate.certificate_schema_version != CERTIFICATE_SCHEMA_VERSION:
        raise ValueError("unexpected dynamics certificate schema")
    if certificate.certificate_sha != _bounded_canonical_sha(
        dynamics_certificate_payload(certificate)
    ):
        raise ValueError("certificate_sha does not match complete body")
    verify_runtime_evidence_manifest(certificate.runtime)
    factory_view = _reverify_verified_factory(factory)
    authority_view = _reverify_verified_prestructure_authority(authority)
    if factory is not authority_view.factory:
        raise ValueError("certificate factory is not authority-bound")
    if certificate.prestructure_authority != authority_view.authority:
        raise ValueError("certificate prestructure body differs from authority")
    if certificate.prestructure_authority.authority_sha != _bounded_canonical_sha(
        prestructure_authority_payload(certificate.prestructure_authority)
    ):
        raise ValueError("embedded prestructure authority SHA is invalid")
    if certificate.transition.factory_sha != factory_view.factory.factory_sha:
        raise ValueError("embedded transition factory binding mismatch")
    transition = verify_measured_transition(
        certificate.transition,
        factory,
        authority,
    )
    structure = verify_structure_manifest(
        certificate.structure,
        factory,
        authority,
    )
    if structure.evidence_lane == "quantum":
        if certificate.reality is not None:
            raise ValueError("quantum certificate cannot contain reality")
    else:
        if certificate.reality is None:
            raise ValueError("classical certificate lacks reality evidence")
        verify_reality_certificate(
            certificate.reality,
            factory,
            transition,
            structure,
        )
    metric = verify_stability_metric_witness(
        certificate.stability_metric,
        factory,
        authority,
        structure,
    )
    protocol = verify_fp64_enclosure_protocol(certificate.fp64_enclosure_protocol)
    structure_residual = verify_laurent_residual_certificate(
        certificate.structure_residual,
        transition,
        structure,
        metric,
        protocol,
    )
    if structure_residual.residual_kind != "canonical-structure":
        raise ValueError("structure residual has the wrong kind")
    if (
        structure_residual.raw_global_momentum_supremum_bound
        > STRUCTURE_RAW_RESIDUAL_GATE
    ):
        raise ValueError("structure residual exceeds its hard upper gate")
    metric_residual = verify_laurent_residual_certificate(
        certificate.metric_residual,
        transition,
        structure,
        metric,
        protocol,
    )
    if metric_residual.residual_kind != "stability-metric":
        raise ValueError("metric residual has the wrong kind")
    spectral = verify_spectral_margin_coverage(
        certificate.spectral_margins,
        transition,
        metric,
    )
    if spectral.fp64_enclosure_protocol != protocol:
        raise ValueError("spectral and certificate protocols differ")
    normalized = verify_normalized_metric_residual_audit(
        certificate.normalized_metric_residual,
        metric_residual,
        spectral,
        transition,
        metric,
    )
    if (
        normalized.audit.normalized_metric_residual_upper
        > NORMALIZED_METRIC_RESIDUAL_GATE
    ):
        raise ValueError("normalized metric residual exceeds hard gate")
    spec = verify_full_state_bridge_spec(
        certificate.full_state_bridge_spec,
        factory,
        authority,
    )
    bridge = verify_full_state_bridge_audit(
        certificate.full_state_bridge_audit,
        transition,
        factory,
        authority,
        spec,
    )
    if bridge.normalized_max > BRIDGE_TOLERANCE:
        raise ValueError("full-state bridge exceeds hard tolerance")
    power = verify_power_drift_audit(
        certificate.power_drift,
        normalized,
    )
    if power.drift_upper > POWER_DRIFT_GATE:
        raise ValueError("power drift exceeds hard gate")


def _make_certificate_authority(
    cached_replay_is_valid: Callable[..., bool] = _cached_replay_is_valid,
    record_successful_replay: Callable[..., None] = _record_successful_replay,
    factory_reverifier: Callable[..., object] = _reverify_verified_factory,
    prestructure_reverifier: Callable[..., object] = (
        _reverify_verified_prestructure_authority
    ),
) -> tuple[
    Callable[..., VerifiedDynamicsCertificate],
    Callable[
        [VerifiedDynamicsCertificate],
        _VerifiedCertificateRecord,
    ],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedDynamicsCertificate],
            _VerifiedCertificateRecord,
        ],
    ] = {}
    lock = threading.RLock()

    def issue(
        token: object,
        certificate: DynamicsCertificate,
        factory: VerifiedFactory,
        authority: VerifiedPrestructureAuthority,
    ) -> VerifiedDynamicsCertificate:
        if token is not _VALIDATED_TOKEN:
            raise TypeError("certificate issuance requires validation")
        _validate_certificate(
            certificate,
            factory,
            authority,
        )
        seal = _certificate_seal(certificate)
        record = _VerifiedCertificateRecord(
            certificate=_snapshot_exact_wire(certificate),
            factory=factory,
            authority=authority,
            seal=seal,
        )
        wrapper = VerifiedDynamicsCertificate(
            _ISSUANCE_TOKEN,
            certificate,
            seal,
        )
        identity = id(wrapper)

        def remove(
            reference: weakref.ReferenceType[VerifiedDynamicsCertificate],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (reference, record)
        record_successful_replay(
            namespace="rulespace_v3.certificate.VerifiedDynamicsCertificate",
            wrapper=wrapper,
            expected_type=VerifiedDynamicsCertificate,
            token=_ISSUANCE_TOKEN,
            exposed_bodies=(certificate,),
            seal=seal,
            authority=record,
            authority_digest=record.seal,
        )
        return wrapper

    def reverify(
        wrapper: VerifiedDynamicsCertificate,
    ) -> _VerifiedCertificateRecord:
        if type(wrapper) is not VerifiedDynamicsCertificate:
            raise TypeError("certificate consumer requires a module-issued capability")
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError("VerifiedDynamicsCertificate identity is not live")
            record = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedDynamicsCertificate__token",
            )
            certificate = object.__getattribute__(
                wrapper,
                "_VerifiedDynamicsCertificate__certificate",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedDynamicsCertificate__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "VerifiedDynamicsCertificate record is incomplete"
            ) from exc
        namespace = "rulespace_v3.certificate.VerifiedDynamicsCertificate"

        def cheap_validator() -> None:
            try:
                body_mismatch = certificate != record.certificate
            except (AttributeError, IndexError, TypeError) as exc:
                raise ValueError(
                    "VerifiedDynamicsCertificate exposed body is malformed"
                ) from exc
            if body_mismatch or seal != record.seal:
                raise ValueError(
                    "VerifiedDynamicsCertificate cached immutable guard mismatch"
                )
            factory_view = factory_reverifier(record.factory)
            authority_view = prestructure_reverifier(record.authority)
            if (
                record.factory is not authority_view.factory
                or certificate.prestructure_authority
                != authority_view.authority
                or certificate.transition.factory_sha
                != factory_view.factory.factory_sha
                or certificate.transition.factory_role != factory_view.role
                or certificate.transition.prestructure_authority_sha
                != authority_view.authority.authority_sha
            ):
                raise ValueError(
                    "VerifiedDynamicsCertificate cached dependency binding "
                    "mismatch"
                )

        if cached_replay_is_valid(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=VerifiedDynamicsCertificate,
            token=token,
            exposed_bodies=(certificate,),
            seal=seal,
            authority=record,
            authority_digest=record.seal,
            cheap_validator=cheap_validator,
        ):
            return record
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("VerifiedDynamicsCertificate token mismatch")
        _validate_certificate(
            certificate,
            record.factory,
            record.authority,
        )
        expected_seal = _certificate_seal(certificate)
        if (
            certificate != record.certificate
            or seal != record.seal
            or seal != expected_seal
        ):
            raise ValueError("VerifiedDynamicsCertificate immutable seal mismatch")
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=VerifiedDynamicsCertificate,
            token=token,
            exposed_bodies=(certificate,),
            seal=seal,
            authority=record,
            authority_digest=record.seal,
        )
        return record

    return issue, reverify


(
    _issue_verified_dynamics_certificate,
    _reverify_verified_dynamics_certificate,
) = _make_certificate_authority()


class VerifiedDynamicsCertificationOutcome:
    """Opaque outcome; only a successful seal contains a certificate token."""

    __slots__ = ("__outcome", "__certificate", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        outcome: DynamicsCertificationOutcome,
        certificate: Optional[VerifiedDynamicsCertificate],
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("VerifiedDynamicsCertificationOutcome is module-issued")
        object.__setattr__(
            self,
            "_VerifiedDynamicsCertificationOutcome__outcome",
            outcome,
        )
        object.__setattr__(
            self,
            "_VerifiedDynamicsCertificationOutcome__certificate",
            certificate,
        )
        object.__setattr__(
            self,
            "_VerifiedDynamicsCertificationOutcome__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedDynamicsCertificationOutcome__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedDynamicsCertificationOutcome is immutable")

    @property
    def outcome(self) -> DynamicsCertificationOutcome:
        return self.__outcome

    @property
    def certificate(self) -> Optional[VerifiedDynamicsCertificate]:
        return self.__certificate


@dataclass(frozen=True)
class _VerifiedOutcomeRecord:
    outcome: DynamicsCertificationOutcome
    certificate: Optional[VerifiedDynamicsCertificate]
    factory: VerifiedFactory
    authority: VerifiedPrestructureAuthority
    seal: str


def _outcome_seal(outcome: DynamicsCertificationOutcome) -> str:
    return _bounded_canonical_sha(
        {
            "verified_outcome_schema_version": (
                "v3m0.verified-dynamics-certification-outcome.v1"
            ),
            "outcome": _record(
                dynamics_certification_outcome_payload(outcome),
                "outcome_sha",
                outcome.outcome_sha,
            ),
        }
    )


def _make_outcome_authority(
    cached_replay_is_valid: Callable[..., bool] = _cached_replay_is_valid,
    record_successful_replay: Callable[..., None] = _record_successful_replay,
    certificate_reverifier: Callable[..., object] = (
        _reverify_verified_dynamics_certificate
    ),
    factory_reverifier: Callable[..., object] = _reverify_verified_factory,
    prestructure_reverifier: Callable[..., object] = (
        _reverify_verified_prestructure_authority
    ),
) -> tuple[
    Callable[
        [
            DynamicsCertificationOutcome,
            Optional[VerifiedDynamicsCertificate],
            VerifiedFactory,
            VerifiedPrestructureAuthority,
        ],
        VerifiedDynamicsCertificationOutcome,
    ],
    Callable[
        [VerifiedDynamicsCertificationOutcome],
        _VerifiedOutcomeRecord,
    ],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedDynamicsCertificationOutcome],
            _VerifiedOutcomeRecord,
        ],
    ] = {}
    lock = threading.RLock()

    def issue(
        outcome: DynamicsCertificationOutcome,
        certificate: Optional[VerifiedDynamicsCertificate],
        factory: VerifiedFactory,
        authority: VerifiedPrestructureAuthority,
    ) -> VerifiedDynamicsCertificationOutcome:
        _validate_outcome_presence(outcome)
        if outcome.status.defined:
            if certificate is None:
                raise ValueError("successful outcome lacks opaque certificate")
            certificate_record = _reverify_verified_dynamics_certificate(certificate)
            if outcome.certificate != certificate_record.certificate:
                raise ValueError("raw and opaque certificate views differ")
            if (
                certificate_record.factory is not factory
                or certificate_record.authority is not authority
            ):
                raise ValueError("outcome context differs from certificate context")
        elif certificate is not None:
            raise ValueError("failed outcome cannot carry opaque certificate")
        else:
            _verify_failure_evidence(
                outcome,
                factory,
                authority,
            )
        seal = _outcome_seal(outcome)
        record = _VerifiedOutcomeRecord(
            outcome=_snapshot_exact_wire(outcome),
            certificate=certificate,
            factory=factory,
            authority=authority,
            seal=seal,
        )
        wrapper = VerifiedDynamicsCertificationOutcome(
            _ISSUANCE_TOKEN,
            outcome,
            certificate,
            seal,
        )
        identity = id(wrapper)

        def remove(
            reference: weakref.ReferenceType[VerifiedDynamicsCertificationOutcome],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (reference, record)
        exposed_bodies = (
            (outcome,)
            if certificate is None
            else (outcome, certificate)
        )
        record_successful_replay(
            namespace=(
                "rulespace_v3.certificate."
                "VerifiedDynamicsCertificationOutcome"
            ),
            wrapper=wrapper,
            expected_type=VerifiedDynamicsCertificationOutcome,
            token=_ISSUANCE_TOKEN,
            exposed_bodies=exposed_bodies,
            seal=seal,
            authority=record,
            authority_digest=record.seal,
        )
        return wrapper

    def reverify(
        wrapper: VerifiedDynamicsCertificationOutcome,
    ) -> _VerifiedOutcomeRecord:
        if type(wrapper) is not VerifiedDynamicsCertificationOutcome:
            raise TypeError("outcome consumer requires a module-issued capability")
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError(
                    "VerifiedDynamicsCertificationOutcome identity is not live"
                )
            record = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedDynamicsCertificationOutcome__token",
            )
            outcome = object.__getattribute__(
                wrapper,
                "_VerifiedDynamicsCertificationOutcome__outcome",
            )
            certificate = object.__getattribute__(
                wrapper,
                "_VerifiedDynamicsCertificationOutcome__certificate",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedDynamicsCertificationOutcome__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "VerifiedDynamicsCertificationOutcome record is incomplete"
            ) from exc
        namespace = (
            "rulespace_v3.certificate.VerifiedDynamicsCertificationOutcome"
        )

        def cheap_validator() -> None:
            try:
                body_mismatch = outcome != record.outcome
            except (AttributeError, IndexError, TypeError) as exc:
                raise ValueError(
                    "VerifiedDynamicsCertificationOutcome exposed body is malformed"
                ) from exc
            if (
                body_mismatch
                or certificate is not record.certificate
                or seal != record.seal
            ):
                raise ValueError(
                    "VerifiedDynamicsCertificationOutcome cached immutable "
                    "guard mismatch"
                )
            if certificate is not None:
                certificate_record = certificate_reverifier(certificate)
                if (
                    outcome.certificate != certificate_record.certificate
                    or certificate_record.factory is not record.factory
                    or certificate_record.authority is not record.authority
                ):
                    raise ValueError(
                        "VerifiedDynamicsCertificationOutcome cached "
                        "certificate binding mismatch"
                    )
            else:
                factory_view = factory_reverifier(record.factory)
                authority_view = prestructure_reverifier(record.authority)
                if (
                    record.factory is not authority_view.factory
                    or outcome.attempt_audit.factory_sha
                    not in (_ZERO_SHA, factory_view.factory.factory_sha)
                    or outcome.attempt_audit.prestructure_authority_sha
                    not in (_ZERO_SHA, authority_view.authority.authority_sha)
                ):
                    raise ValueError(
                        "VerifiedDynamicsCertificationOutcome cached failure "
                        "context mismatch"
                    )

        exposed_bodies = (
            (outcome,)
            if certificate is None
            else (outcome, certificate)
        )
        if cached_replay_is_valid(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=VerifiedDynamicsCertificationOutcome,
            token=token,
            exposed_bodies=exposed_bodies,
            seal=seal,
            authority=record,
            authority_digest=record.seal,
            cheap_validator=cheap_validator,
        ):
            return record
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("VerifiedDynamicsCertificationOutcome token mismatch")
        _validate_outcome_presence(outcome)
        if certificate is not None:
            certificate_record = _reverify_verified_dynamics_certificate(certificate)
            if outcome.certificate != certificate_record.certificate:
                raise ValueError("outcome certificate authority mismatch")
            if (
                certificate_record.factory is not record.factory
                or certificate_record.authority is not record.authority
            ):
                raise ValueError("outcome live context mismatch")
        else:
            _verify_failure_evidence(
                outcome,
                record.factory,
                record.authority,
            )
        expected_seal = _outcome_seal(outcome)
        if (
            outcome != record.outcome
            or certificate is not record.certificate
            or seal != record.seal
            or seal != expected_seal
        ):
            raise ValueError(
                "VerifiedDynamicsCertificationOutcome immutable seal mismatch"
            )
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=VerifiedDynamicsCertificationOutcome,
            token=token,
            exposed_bodies=exposed_bodies,
            seal=seal,
            authority=record,
            authority_digest=record.seal,
        )
        return record

    return issue, reverify


(
    _issue_verified_dynamics_certification_outcome,
    _reverify_verified_dynamics_certification_outcome,
) = _make_outcome_authority()


def _attempt(
    *,
    factory_sha: str,
    authority_sha: str,
    transition_sha: Optional[str],
    failure: Optional[DynamicsCertificationFailure],
    reality: Optional[RealityCertificate],
    structure_residual: Optional[LaurentResidualCertificate],
    metric_residual: Optional[LaurentResidualCertificate],
    spectral_margins: Optional[SpectralMarginCoverage],
    normalized_metric_residual: Optional[NormalizedMetricResidualAudit],
    full_state_bridge_audit: Optional[BridgeAudit],
    power_drift: Optional[PowerDriftAudit],
    instability_counter_witness: Optional[InstabilityGrowthCounterWitness],
) -> DynamicsCertificationAttemptAudit:
    provisional = DynamicsCertificationAttemptAudit(
        attempt_schema_version=CERTIFICATION_ATTEMPT_SCHEMA_VERSION,
        factory_sha=factory_sha,
        transition_sha=transition_sha,
        prestructure_authority_sha=authority_sha,
        first_failure=failure,
        reality=reality,
        structure_residual=structure_residual,
        metric_residual=metric_residual,
        spectral_margins=spectral_margins,
        normalized_metric_residual=normalized_metric_residual,
        full_state_bridge_audit=full_state_bridge_audit,
        power_drift=power_drift,
        instability_counter_witness=instability_counter_witness,
        attempt_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        attempt_sha=_bounded_canonical_sha(
            dynamics_certification_attempt_audit_payload(provisional)
        ),
    )


def _raw_outcome(
    *,
    failure: Optional[DynamicsCertificationFailure],
    attempt: DynamicsCertificationAttemptAudit,
    certificate: Optional[DynamicsCertificate],
) -> DynamicsCertificationOutcome:
    status = (
        BlockStatus(True, None)
        if failure is None
        else BlockStatus(False, _FAILURE_REASONS[failure])
    )
    provisional = DynamicsCertificationOutcome(
        status=status,
        failure=failure,
        attempt_audit=attempt,
        certificate=certificate,
        outcome_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        outcome_sha=_bounded_canonical_sha(
            dynamics_certification_outcome_payload(provisional)
        ),
    )


def _failed(
    *,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    factory_sha: str,
    authority_sha: str,
    transition_sha: Optional[str],
    failure: DynamicsCertificationFailure,
    reality: Optional[RealityCertificate] = None,
    structure_residual: Optional[LaurentResidualCertificate] = None,
    metric_residual: Optional[LaurentResidualCertificate] = None,
    spectral_margins: Optional[SpectralMarginCoverage] = None,
    normalized_metric_residual: Optional[NormalizedMetricResidualAudit] = None,
    full_state_bridge_audit: Optional[BridgeAudit] = None,
    power_drift: Optional[PowerDriftAudit] = None,
    instability_counter_witness: Optional[InstabilityGrowthCounterWitness] = None,
) -> VerifiedDynamicsCertificationOutcome:
    attempt = _attempt(
        factory_sha=factory_sha,
        authority_sha=authority_sha,
        transition_sha=transition_sha,
        failure=failure,
        reality=reality,
        structure_residual=structure_residual,
        metric_residual=metric_residual,
        spectral_margins=spectral_margins,
        normalized_metric_residual=normalized_metric_residual,
        full_state_bridge_audit=full_state_bridge_audit,
        power_drift=power_drift,
        instability_counter_witness=instability_counter_witness,
    )
    return _issue_verified_dynamics_certification_outcome(
        _raw_outcome(
            failure=failure,
            attempt=attempt,
            certificate=None,
        ),
        None,
        factory,
        authority,
    )


def _preflight_laurent_resources(
    transition: VerifiedTransition,
    stability_metric: StabilityMetricWitness,
) -> None:
    transition_view = _reverify_verified_transition(transition)
    _exact_type(
        stability_metric,
        StabilityMetricWitness,
        "stability_metric",
    )
    transition_support = transition_view.transition.support_offsets
    metric_support = stability_metric.metric_support_offsets
    if type(metric_support) is not tuple or not metric_support:
        raise ValueError("metric support is absent")
    n_state = len(transition_view.transition.channel_order)
    ndim = len(transition_view.transition.spatial_shape)
    zero_support = ((0,) * ndim,)
    left_support = tuple(
        sorted(
            tuple(-coordinate for coordinate in offset) for offset in transition_support
        )
    )
    _laurent._preflight_convolution_chain(
        left_support,
        zero_support,
        transition_support,
        n_state,
    )
    _laurent._preflight_convolution_chain(
        left_support,
        metric_support,
        transition_support,
        n_state,
    )


def _build_laurent_residual(
    kind: str,
    transition: VerifiedTransition,
    structure: StructureManifest,
    metric: StabilityMetricWitness,
    protocol: Fp64EnclosureProtocol,
) -> LaurentResidualCertificate:
    if kind not in ("canonical-structure", "stability-metric"):
        raise ValueError("Laurent residual kind is not closed")
    return _laurent._build_residual(
        kind=kind,
        transition=transition,
        structure=structure,
        metric=metric,
        protocol=protocol,
    )


def certify_transition_dynamics(
    factory: VerifiedFactory,
    transition: VerifiedTransition,
    prestructure_authority: VerifiedPrestructureAuthority,
    structure_manifest: StructureManifest,
    stability_metric: StabilityMetricWitness,
    full_state_bridge_spec: FullStateBridgeSpec,
    dynamics_grid: DynamicsKGridManifest,
    runtime_manifest: RuntimeEvidenceManifest,
) -> VerifiedDynamicsCertificationOutcome:
    """Run the frozen certification pipeline and preserve its first failure."""

    runtime = verify_runtime_evidence_manifest(runtime_manifest)
    factory_sha = _ZERO_SHA
    authority_sha = _ZERO_SHA
    try:
        factory_view = _reverify_verified_factory(factory)
        authority_view = _reverify_verified_prestructure_authority(
            prestructure_authority
        )
        if factory is not authority_view.factory:
            raise ValueError("factory is not authority-bound")
        factory_sha = factory_view.factory.factory_sha
        authority_sha = authority_view.authority.authority_sha
        structure = verify_structure_manifest(
            structure_manifest,
            factory,
            prestructure_authority,
        )
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=None,
            failure=DynamicsCertificationFailure.PRESTRUCTURE_INVALID,
        )

    try:
        transition_view = _reverify_verified_transition(transition)
        verified_transition = verify_measured_transition(
            transition_view.transition,
            factory,
            prestructure_authority,
        )
        transition_sha = verified_transition.transition.transition_sha
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=None,
            failure=DynamicsCertificationFailure.TRANSITION_INVALID,
        )

    try:
        reality = certify_reality(
            factory,
            verified_transition,
            structure,
        )
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=DynamicsCertificationFailure.REALITY_INVALID,
        )

    try:
        _preflight_laurent_resources(
            verified_transition,
            stability_metric,
        )
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED),
            reality=reality,
        )

    witness = certify_instability_growth_counter_witness(verified_transition)
    if witness is not None:
        witness = verify_instability_growth_counter_witness(
            witness,
            factory,
            prestructure_authority,
        )
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS),
            reality=reality,
            instability_counter_witness=witness,
        )

    protocol = build_fp64_enclosure_protocol()
    try:
        canonical_metric = build_stability_metric_witness(
            factory,
            prestructure_authority,
            structure,
        )
        structure_residual = _build_laurent_residual(
            "canonical-structure",
            verified_transition,
            structure,
            canonical_metric,
            protocol,
        )
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED),
            reality=reality,
        )
    if (
        structure_residual.raw_global_momentum_supremum_bound
        > STRUCTURE_RAW_RESIDUAL_GATE
    ):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED),
            reality=reality,
            structure_residual=structure_residual,
        )

    try:
        metric = verify_stability_metric_witness(
            stability_metric,
            factory,
            prestructure_authority,
            structure,
        )
        metric_residual = _build_laurent_residual(
            "stability-metric",
            verified_transition,
            structure,
            metric,
            protocol,
        )
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=DynamicsCertificationFailure.METRIC_RAW_UNRESOLVED,
            reality=reality,
            structure_residual=structure_residual,
        )

    try:
        grid = verify_dynamics_grid_manifest(
            dynamics_grid,
            verified_transition.transition.support_offsets,
            metric.metric_support_offsets,
        )
        spectral = build_spectral_margin_coverage(
            verified_transition,
            metric,
            protocol,
        )
        if spectral.qualification_grid != grid:
            raise ValueError("spectral coverage grid differs from input grid")
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.SPECTRAL_COVERAGE_UNRESOLVED),
            reality=reality,
            structure_residual=structure_residual,
            metric_residual=metric_residual,
        )

    try:
        normalized_capability = certify_normalized_metric_residual_audit(
            metric_residual,
            spectral,
            verified_transition,
            metric,
        )
        normalized = normalized_capability.audit
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.NORMALIZED_METRIC_UNRESOLVED),
            reality=reality,
            structure_residual=structure_residual,
            metric_residual=metric_residual,
            spectral_margins=spectral,
        )

    try:
        spec = verify_full_state_bridge_spec(
            full_state_bridge_spec,
            factory,
            prestructure_authority,
        )
        bridge = audit_full_state_bridge(
            verified_transition,
            factory,
            prestructure_authority,
            spec,
        )
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED),
            reality=reality,
            structure_residual=structure_residual,
            metric_residual=metric_residual,
            spectral_margins=spectral,
            normalized_metric_residual=normalized,
        )
    if bridge.normalized_max > BRIDGE_TOLERANCE:
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED),
            reality=reality,
            structure_residual=structure_residual,
            metric_residual=metric_residual,
            spectral_margins=spectral,
            normalized_metric_residual=normalized,
            full_state_bridge_audit=bridge,
        )

    try:
        power = build_power_drift_audit(normalized_capability)
    except (TypeError, ValueError):
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED),
            reality=reality,
            structure_residual=structure_residual,
            metric_residual=metric_residual,
            spectral_margins=spectral,
            normalized_metric_residual=normalized,
            full_state_bridge_audit=bridge,
        )
    if power.drift_upper > POWER_DRIFT_GATE:
        return _failed(
            factory=factory,
            authority=prestructure_authority,
            factory_sha=factory_sha,
            authority_sha=authority_sha,
            transition_sha=transition_sha,
            failure=(DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED),
            reality=reality,
            structure_residual=structure_residual,
            metric_residual=metric_residual,
            spectral_margins=spectral,
            normalized_metric_residual=normalized,
            full_state_bridge_audit=bridge,
            power_drift=power,
        )

    provisional = DynamicsCertificate(
        certificate_schema_version=CERTIFICATE_SCHEMA_VERSION,
        transition=verified_transition.transition,
        prestructure_authority=authority_view.authority,
        structure=structure,
        reality=reality,
        stability_metric=metric,
        fp64_enclosure_protocol=protocol,
        full_state_bridge_spec=spec,
        full_state_bridge_audit=bridge,
        structure_residual=structure_residual,
        metric_residual=metric_residual,
        spectral_margins=spectral,
        normalized_metric_residual=normalized,
        power_drift=power,
        runtime=runtime,
        certificate_sha=_ZERO_SHA,
    )
    certificate = replace(
        provisional,
        certificate_sha=_bounded_canonical_sha(
            dynamics_certificate_payload(provisional)
        ),
    )
    verified_certificate = _issue_verified_dynamics_certificate(
        _VALIDATED_TOKEN,
        certificate,
        factory,
        prestructure_authority,
    )
    attempt = _attempt(
        factory_sha=factory_sha,
        authority_sha=authority_sha,
        transition_sha=transition_sha,
        failure=None,
        reality=reality,
        structure_residual=structure_residual,
        metric_residual=metric_residual,
        spectral_margins=spectral,
        normalized_metric_residual=normalized,
        full_state_bridge_audit=bridge,
        power_drift=power,
        instability_counter_witness=None,
    )
    raw = _raw_outcome(
        failure=None,
        attempt=attempt,
        certificate=certificate,
    )
    return _issue_verified_dynamics_certification_outcome(
        raw,
        verified_certificate,
        factory,
        prestructure_authority,
    )


def verify_dynamics_certificate(
    certificate: DynamicsCertificate,
    factory: VerifiedFactory,
    prestructure_authority: VerifiedPrestructureAuthority,
) -> VerifiedDynamicsCertificate:
    """Hydrate only after complete recursive validation and executor replay."""

    return _issue_verified_dynamics_certificate(
        _VALIDATED_TOKEN,
        certificate,
        factory,
        prestructure_authority,
    )


def _verify_failure_evidence(
    outcome: DynamicsCertificationOutcome,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> None:
    """Replay the frozen first-failure pipeline from live authority context."""

    audit = outcome.attempt_audit
    failure = outcome.failure
    factory_view = _reverify_verified_factory(factory)
    authority_view = _reverify_verified_prestructure_authority(authority)
    if factory is not authority_view.factory:
        raise ValueError("outcome factory is not authority-bound")
    if failure is DynamicsCertificationFailure.PRESTRUCTURE_INVALID:
        raise ValueError(
            "a valid factory/authority pair cannot prove prestructure failure"
        )
    if audit.factory_sha not in (_ZERO_SHA, factory_view.factory.factory_sha):
        raise ValueError("attempt factory SHA mismatch")
    if audit.prestructure_authority_sha not in (
        _ZERO_SHA,
        authority_view.authority.authority_sha,
    ):
        raise ValueError("attempt authority SHA mismatch")

    structure = build_structure_manifest(factory, authority)
    try:
        transition = _failure_transition(factory, authority)
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.TRANSITION_INVALID:
            return
        raise ValueError("an earlier transition failure contradicts first_failure")
    if failure is DynamicsCertificationFailure.TRANSITION_INVALID:
        raise ValueError("canonical transition replay succeeds")
    if (
        audit.transition_sha is None
        or transition.transition.transition_sha != audit.transition_sha
    ):
        raise ValueError("attempt transition SHA differs from remeasurement")

    try:
        replayed_reality = certify_reality(
            factory,
            transition,
            structure,
        )
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.REALITY_INVALID:
            return
        raise ValueError("an earlier reality failure contradicts first_failure")
    if failure is DynamicsCertificationFailure.REALITY_INVALID:
        raise ValueError("replayed reality gate passes")
    if audit.reality is not None:
        verified_reality = verify_reality_certificate(
            audit.reality,
            factory,
            transition,
            structure,
        )
        if verified_reality != replayed_reality:
            raise ValueError("attempt reality evidence differs from replay")

    metric = build_stability_metric_witness(
        factory,
        authority,
        structure,
    )
    try:
        _preflight_laurent_resources(transition, metric)
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED:
            return
        raise ValueError(
            "an earlier Laurent resource failure contradicts first_failure"
        )
    if failure is DynamicsCertificationFailure.LAURENT_RESOURCE_EXCEEDED:
        raise ValueError("replayed Laurent resource preflight passes")

    witness = certify_instability_growth_counter_witness(transition)
    if witness is not None:
        replayed_witness = verify_instability_growth_counter_witness(
            witness,
            factory,
            authority,
        )
        if (
            failure
            is not DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS
        ):
            raise ValueError(
                "an earlier Jordan counterwitness contradicts first_failure"
            )
        if audit.instability_counter_witness != replayed_witness:
            raise ValueError("attempt Jordan witness differs from replay")
        return
    if failure is DynamicsCertificationFailure.CERTIFIED_INSTABILITY_COUNTERWITNESS:
        raise ValueError("claimed Jordan counterwitness is not reproducible")

    protocol = build_fp64_enclosure_protocol()
    try:
        replayed_structure = _build_laurent_residual(
            "canonical-structure",
            transition,
            structure,
            metric,
            protocol,
        )
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED:
            return
        raise ValueError(
            "an earlier structure enclosure failure contradicts first_failure"
        )
    structure_failed = (
        replayed_structure.raw_global_momentum_supremum_bound
        > STRUCTURE_RAW_RESIDUAL_GATE
    )
    if structure_failed:
        if failure is not DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED:
            raise ValueError(
                "an earlier structure hard-gate failure contradicts first_failure"
            )
        if (
            audit.structure_residual is not None
            and audit.structure_residual != replayed_structure
        ):
            raise ValueError("attempt structure evidence differs from replay")
        return
    if failure is DynamicsCertificationFailure.STRUCTURE_RAW_UNRESOLVED:
        raise ValueError("replayed structure residual passes")
    if audit.structure_residual != replayed_structure:
        raise ValueError("attempt structure evidence differs from replay")

    try:
        replayed_metric = _build_laurent_residual(
            "stability-metric",
            transition,
            structure,
            metric,
            protocol,
        )
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.METRIC_RAW_UNRESOLVED:
            return
        raise ValueError(
            "an earlier metric enclosure failure contradicts first_failure"
        )
    if failure is DynamicsCertificationFailure.METRIC_RAW_UNRESOLVED:
        raise ValueError("replayed metric residual construction passes")
    if audit.metric_residual != replayed_metric:
        raise ValueError("attempt metric evidence differs from replay")

    try:
        replayed_spectral = build_spectral_margin_coverage(
            transition,
            metric,
            protocol,
        )
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.SPECTRAL_COVERAGE_UNRESOLVED:
            return
        raise ValueError("an earlier spectral failure contradicts first_failure")
    if failure is DynamicsCertificationFailure.SPECTRAL_COVERAGE_UNRESOLVED:
        raise ValueError("replayed spectral coverage passes")
    if audit.spectral_margins != replayed_spectral:
        raise ValueError("attempt spectral evidence differs from replay")

    try:
        normalized_capability = certify_normalized_metric_residual_audit(
            replayed_metric,
            replayed_spectral,
            transition,
            metric,
        )
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.NORMALIZED_METRIC_UNRESOLVED:
            return
        raise ValueError(
            "an earlier normalized-metric failure contradicts first_failure"
        )
    replayed_normalized = normalized_capability.audit
    if failure is DynamicsCertificationFailure.NORMALIZED_METRIC_UNRESOLVED:
        raise ValueError("replayed normalized metric audit passes")
    if audit.normalized_metric_residual != replayed_normalized:
        raise ValueError("attempt normalized evidence differs from replay")

    spec = build_full_state_bridge_spec(factory, authority)
    try:
        replayed_bridge = audit_full_state_bridge(
            transition,
            factory,
            authority,
            spec,
        )
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED:
            return
        raise ValueError(
            "an earlier bridge execution failure contradicts first_failure"
        )
    bridge_failed = replayed_bridge.normalized_max > BRIDGE_TOLERANCE
    if bridge_failed:
        if failure is not DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED:
            raise ValueError(
                "an earlier bridge hard-gate failure contradicts first_failure"
            )
        if (
            audit.full_state_bridge_audit is not None
            and audit.full_state_bridge_audit != replayed_bridge
        ):
            raise ValueError("attempt bridge evidence differs from replay")
        return
    if failure is DynamicsCertificationFailure.FULL_STATE_BRIDGE_FAILED:
        raise ValueError("replayed full-state bridge passes")
    if audit.full_state_bridge_audit != replayed_bridge:
        raise ValueError("attempt bridge evidence differs from replay")

    try:
        replayed_power = build_power_drift_audit(normalized_capability)
    except (TypeError, ValueError):
        if failure is DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED:
            return
        raise ValueError("an earlier power audit failure contradicts first_failure")
    if replayed_power.drift_upper > POWER_DRIFT_GATE:
        if failure is not DynamicsCertificationFailure.POWER_DRIFT_UNRESOLVED:
            raise ValueError(
                "an earlier power hard-gate failure contradicts first_failure"
            )
        if audit.power_drift is not None and audit.power_drift != replayed_power:
            raise ValueError("attempt power evidence differs from replay")
        return
    raise ValueError("all replayed stages pass for the claimed failed outcome")


def _failure_transition(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> VerifiedTransition:
    return measure_transition(factory, authority)


def verify_dynamics_certification_outcome(
    outcome: DynamicsCertificationOutcome,
    factory: VerifiedFactory,
    prestructure_authority: VerifiedPrestructureAuthority,
) -> VerifiedDynamicsCertificationOutcome:
    """Hydrate a raw outcome; only a fully verified success gains capability."""

    _exact_type(outcome, DynamicsCertificationOutcome, "outcome")
    _validate_outcome_presence(outcome)
    if outcome.status.defined:
        if outcome.certificate is None:
            raise ValueError("successful raw outcome lacks certificate")
        verified = verify_dynamics_certificate(
            outcome.certificate,
            factory,
            prestructure_authority,
        )
        return _issue_verified_dynamics_certification_outcome(
            outcome,
            verified,
            factory,
            prestructure_authority,
        )
    _verify_failure_evidence(
        outcome,
        factory,
        prestructure_authority,
    )
    return _issue_verified_dynamics_certification_outcome(
        outcome,
        None,
        factory,
        prestructure_authority,
    )


def _freeze_certificate_call_graph(root: Callable) -> object:
    """Clone the reachable project call graph into private globals."""

    function_memo: dict[int, Callable] = {}
    module_memo: dict[tuple[int, tuple[str, ...]], object] = {}

    def referenced_code_names(code: types.CodeType) -> tuple[str, ...]:
        names = list(code.co_names)
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                names.extend(referenced_code_names(constant))
        return tuple(dict.fromkeys(names))

    def freeze_value(
        value: object,
        referenced_names: tuple[str, ...] = (),
    ) -> object:
        if inspect.isfunction(value) and (
            value.__module__ == __name__ or value.__module__.startswith("rulespace_v3.")
        ):
            return freeze_function(value)
        if inspect.ismodule(value):
            module_values = vars(value)
            key = (id(value), referenced_names)
            cached_module = module_memo.get(key)
            if cached_module is not None:
                return cached_module
            proxy = types.SimpleNamespace()
            module_memo[key] = proxy
            for name in referenced_names:
                if name in module_values:
                    setattr(
                        proxy,
                        name,
                        freeze_value(
                            module_values[name],
                            referenced_names,
                        ),
                    )
            return proxy
        if type(value) is tuple:
            return tuple(freeze_value(item) for item in value)
        if type(value) is list:
            return [freeze_value(item) for item in value]
        if type(value) is dict:
            return {key: freeze_value(item) for key, item in value.items()}
        return value

    def freeze_closure_value(value: object) -> object:
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if type(value) is tuple:
            return tuple(freeze_closure_value(item) for item in value)
        return value

    def make_cell(value: object) -> object:
        def read_cell() -> object:
            return value

        return read_cell.__closure__[0]

    def freeze_function(function: Callable) -> Callable:
        cached = function_memo.get(id(function))
        if cached is not None:
            return cached
        source_globals = function.__globals__
        builtins_body = source_globals.get("__builtins__", {})
        if type(builtins_body) is dict:
            private_builtins = dict(builtins_body)
        else:
            private_builtins = dict(vars(builtins_body))
        private_globals: dict[str, object] = {
            "__builtins__": private_builtins,
            "__name__": source_globals.get("__name__", __name__),
            "__package__": source_globals.get(
                "__package__",
                __package__,
            ),
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
        if source_closure is not None:
            assert private_cells is not None
            for private_cell, source_cell in zip(
                private_cells,
                source_closure,
            ):
                private_cell.cell_contents = freeze_closure_value(
                    source_cell.cell_contents
                )
        referenced_names = referenced_code_names(function.__code__)
        for name in referenced_names:
            if name in source_globals:
                private_globals[name] = freeze_value(
                    source_globals[name],
                    referenced_names,
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
        return clone

    return functools.partial(freeze_function(root))


_certify_transition_dynamics_core = certify_transition_dynamics
_verify_dynamics_certificate_core = verify_dynamics_certificate
_verify_dynamics_certification_outcome_core = verify_dynamics_certification_outcome
_reverify_verified_dynamics_certificate_core = _reverify_verified_dynamics_certificate
_reverify_verified_dynamics_certification_outcome_core = (
    _reverify_verified_dynamics_certification_outcome
)


def _certify_transition_dynamics_in_replay_scope(
    factory: VerifiedFactory,
    transition: VerifiedTransition,
    prestructure_authority: VerifiedPrestructureAuthority,
    structure_manifest: StructureManifest,
    stability_metric: StabilityMetricWitness,
    full_state_bridge_spec: FullStateBridgeSpec,
    dynamics_grid: DynamicsKGridManifest,
    runtime_manifest: RuntimeEvidenceManifest,
) -> VerifiedDynamicsCertificationOutcome:
    with _scoped_replay_context():
        return _certify_transition_dynamics_core(
            factory,
            transition,
            prestructure_authority,
            structure_manifest,
            stability_metric,
            full_state_bridge_spec,
            dynamics_grid,
            runtime_manifest,
        )


def _verify_dynamics_certificate_in_replay_scope(
    certificate: DynamicsCertificate,
    factory: VerifiedFactory,
    prestructure_authority: VerifiedPrestructureAuthority,
) -> VerifiedDynamicsCertificate:
    with _scoped_replay_context():
        return _verify_dynamics_certificate_core(
            certificate,
            factory,
            prestructure_authority,
        )


def _verify_dynamics_certification_outcome_in_replay_scope(
    outcome: DynamicsCertificationOutcome,
    factory: VerifiedFactory,
    prestructure_authority: VerifiedPrestructureAuthority,
) -> VerifiedDynamicsCertificationOutcome:
    with _scoped_replay_context():
        return _verify_dynamics_certification_outcome_core(
            outcome,
            factory,
            prestructure_authority,
        )


certify_transition_dynamics = _freeze_certificate_call_graph(
    _certify_transition_dynamics_in_replay_scope
)
verify_dynamics_certificate = _freeze_certificate_call_graph(
    _verify_dynamics_certificate_in_replay_scope
)
verify_dynamics_certification_outcome = _freeze_certificate_call_graph(
    _verify_dynamics_certification_outcome_in_replay_scope
)
_reverify_verified_dynamics_certificate = _freeze_certificate_call_graph(
    _reverify_verified_dynamics_certificate_core
)
_reverify_verified_dynamics_certification_outcome = _freeze_certificate_call_graph(
    _reverify_verified_dynamics_certification_outcome_core
)


__all__ = [
    "CERTIFICATE_SCHEMA_VERSION",
    "CERTIFICATION_ATTEMPT_SCHEMA_VERSION",
    "CERTIFICATION_OUTCOME_SCHEMA_VERSION",
    "POWER_DRIFT_GATE",
    "STRUCTURE_RAW_RESIDUAL_GATE",
    "DynamicsCertificate",
    "DynamicsCertificationAttemptAudit",
    "DynamicsCertificationFailure",
    "DynamicsCertificationOutcome",
    "VerifiedDynamicsCertificate",
    "VerifiedDynamicsCertificationOutcome",
    "certify_transition_dynamics",
    "dynamics_certificate_payload",
    "dynamics_certification_attempt_audit_payload",
    "dynamics_certification_outcome_payload",
    "verify_dynamics_certificate",
    "verify_dynamics_certification_outcome",
]
