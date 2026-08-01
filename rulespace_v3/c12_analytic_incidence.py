"""Standalone, authority-neutral analytic C12 incidence certificate.

The issued C12 construction preflight is byte-frozen by Parent-v2.  This
module therefore proves the centered-incidence identity and its IR limit
without modifying, wrapping, or re-exporting that frozen source file.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace

import numpy as np
import sympy as sp

from .c12_incidence_preflight import (
    C12_INCIDENCE_FAMILY_ID,
    C12_INCIDENCE_POINT_SCHEMA_VERSION,
    C12_NORMALIZER_FORMULA_ID,
    C12_RESPONSE_RECIPROCAL_INDICES,
    C12_RESPONSE_TORUS_DENOMINATOR,
    C12IncidencePointWire,
    c12_incidence_point_wire_payload,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    freeze_complex_tensor,
    verify_frozen_tensor,
)
from .frozen_call_graph import freeze_rulespace_call_graph


C12_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION = (
    "v3m0.c12-analytic-incidence-certificate.v1"
)
C12_NORMALIZER_DERIVATION_ID = (
    "2-exp(+ik)-exp(-ik)-centered-second-difference-v1"
)
C12_IR_LIMIT_FORMULA_ID = (
    "lim-k-to-zero-nu-inc-over-k-squared-equals-one-v1"
)
C12_IR_CONCLUSION = "POSITIVE_SECOND_ORDER_UNIT_CONTINUUM_LIMIT"
C12_POSITIVITY_DOMAIN_ID = (
    "one-dimensional-minus-pi-open-pi-closed-excluding-zero-v1"
)
C12_ABSOLUTE_SIGNAL_THRESHOLD_AUTHORITY_REF = (
    "WindowThresholdSelection.curv_tau_sig"
)
C12_RAW_BRIDGE_NOISE_EVIDENCE_REF = (
    "SourceReadoutBridgeAudit.curv_operator_error_max"
)
C12_RAW_NOISE_ABSOLUTE_THRESHOLD_AUTHORITY_REF = (
    "rulespace_v3.thresholds.BRIDGE_TOLERANCE"
)
C12_RELATIVE_GAP_THRESHOLD_AUTHORITY_REF = (
    "rulespace_v3.thresholds.RAW_GAP_MIN"
)

_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_POINT_FIELD_NAMES = (
    "point_schema_version",
    "incidence_family_id",
    "normalizer_formula_id",
    "torus_denominator",
    "reciprocal_index",
    "momentum",
    "root_of_unity_order",
    "root_of_unity_power",
    "exact_nu_expression",
    "nu_minimal_polynomial_coefficients",
    "nu_value",
    "stencil_symbol_residual",
    "incidence_operator",
    "normalized_incidence_operator",
    "application_stage",
    "point_sha",
)


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _finite(value: object, field: str) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise TypeError(f"{field} must be an exact finite fp64 value")
    return value


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    try:
        observed = frozenset(vars(value))
    except TypeError as exc:
        raise TypeError(f"{field} has no exact record body") from exc
    expected = frozenset(record_type.__dataclass_fields__)
    if observed != expected:
        raise ValueError(f"{field} contains missing or unknown fields")


@dataclass(frozen=True)
class C12AnalyticIncidenceCertificate:
    """Exact analytic certificate; it carries no finite-response authority."""

    certificate_schema_version: str
    incidence_family_id: str
    normalizer_formula_id: str
    normalizer_derivation_id: str
    stencil_offsets: tuple[tuple[int, ...], ...]
    stencil_coefficients: tuple[int, ...]
    first_brillouin_domain_id: str
    positivity_domain_id: str
    ir_limit_formula_id: str
    ir_limit_order: int
    ir_limit_value: float
    ir_conclusion: str
    positivity_certified: bool
    absolute_signal_threshold_authority_ref: str
    raw_bridge_noise_evidence_ref: str
    raw_noise_absolute_threshold_authority_ref: str
    relative_gap_threshold_authority_ref: str
    point_wires: tuple[C12IncidencePointWire, ...]
    certificate_sha: str

    def __post_init__(self) -> None:
        if (
            self.certificate_schema_version
            != C12_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION
        ):
            raise ValueError("C12 analytic incidence certificate schema drifted")
        for field in (
            "incidence_family_id",
            "normalizer_formula_id",
            "normalizer_derivation_id",
            "first_brillouin_domain_id",
            "positivity_domain_id",
            "ir_limit_formula_id",
            "ir_conclusion",
            "absolute_signal_threshold_authority_ref",
            "raw_bridge_noise_evidence_ref",
            "raw_noise_absolute_threshold_authority_ref",
            "relative_gap_threshold_authority_ref",
        ):
            _text(getattr(self, field), field)
        if (
            type(self.stencil_offsets) is not tuple
            or not all(
                type(offset) is tuple
                and all(type(value) is int for value in offset)
                for offset in self.stencil_offsets
            )
        ):
            raise TypeError("stencil_offsets must contain exact integer tuples")
        if type(self.stencil_coefficients) is not tuple or not all(
            type(value) is int for value in self.stencil_coefficients
        ):
            raise TypeError("stencil_coefficients must be exact integers")
        if type(self.ir_limit_order) is not int:
            raise TypeError("ir_limit_order must be an exact integer")
        _finite(self.ir_limit_value, "ir_limit_value")
        if type(self.positivity_certified) is not bool:
            raise TypeError("positivity_certified must be an exact bool")
        if type(self.point_wires) is not tuple or not all(
            type(point) is C12IncidencePointWire for point in self.point_wires
        ):
            raise TypeError("point_wires have the wrong strict type")
        _sha(self.certificate_sha, "certificate_sha")


# Preserve the legacy class object and method byte-for-byte.  The local frozen
# callable closes its globals without mutating the shared legacy class.
_LEGACY_POINT_POST_INIT = C12IncidencePointWire.__post_init__
C12AnalyticIncidenceCertificate.__post_init__ = freeze_rulespace_call_graph(
    C12AnalyticIncidenceCertificate.__post_init__
)


def _point_record(point: C12IncidencePointWire) -> dict[str, object]:
    return {
        **c12_incidence_point_wire_payload(point),
        "point_sha": point.point_sha,
    }


def c12_analytic_incidence_certificate_payload(
    certificate: C12AnalyticIncidenceCertificate,
) -> dict[str, object]:
    """Return the complete hash body of an analytic-only C12 certificate."""

    _exact_record(
        certificate,
        C12AnalyticIncidenceCertificate,
        "C12 analytic incidence certificate",
    )
    return {
        "certificate_schema_version": certificate.certificate_schema_version,
        "incidence_family_id": certificate.incidence_family_id,
        "normalizer_formula_id": certificate.normalizer_formula_id,
        "normalizer_derivation_id": certificate.normalizer_derivation_id,
        "stencil_offsets": [list(item) for item in certificate.stencil_offsets],
        "stencil_coefficients": list(certificate.stencil_coefficients),
        "first_brillouin_domain_id": certificate.first_brillouin_domain_id,
        "positivity_domain_id": certificate.positivity_domain_id,
        "ir_limit_formula_id": certificate.ir_limit_formula_id,
        "ir_limit_order": certificate.ir_limit_order,
        "ir_limit_value": certificate.ir_limit_value,
        "ir_conclusion": certificate.ir_conclusion,
        "positivity_certified": certificate.positivity_certified,
        "absolute_signal_threshold_authority_ref": (
            certificate.absolute_signal_threshold_authority_ref
        ),
        "raw_bridge_noise_evidence_ref": (
            certificate.raw_bridge_noise_evidence_ref
        ),
        "raw_noise_absolute_threshold_authority_ref": (
            certificate.raw_noise_absolute_threshold_authority_ref
        ),
        "relative_gap_threshold_authority_ref": (
            certificate.relative_gap_threshold_authority_ref
        ),
        "point_wires": [_point_record(point) for point in certificate.point_wires],
    }


def _new_legacy_point(body: dict[str, object]) -> C12IncidencePointWire:
    if frozenset(body) != frozenset(_POINT_FIELD_NAMES):
        raise ValueError("analytic incidence point body is incomplete")
    point = object.__new__(C12IncidencePointWire)
    for field in _POINT_FIELD_NAMES:
        object.__setattr__(point, field, body[field])
    _LEGACY_POINT_POST_INIT(point)
    return point


def _build_analytic_incidence_point_body(
    reciprocal_index: tuple[int, ...],
) -> dict[str, object]:
    if reciprocal_index not in C12_RESPONSE_RECIPROCAL_INDICES:
        raise ValueError("C12 analytic incidence point is not preregistered")
    mode = reciprocal_index[0]
    exact_nu = sp.simplify(4 * sp.sin(sp.pi * mode / 8) ** 2)
    variable = sp.Symbol("nu")
    coefficients = tuple(
        int(value)
        for value in sp.Poly(
            sp.minpoly(exact_nu, variable),
            variable,
        ).all_coeffs()
    )
    nu_value = 2.0 - math.sqrt(2.0) if mode == 1 else 2.0
    momentum = 2.0 * math.pi * mode / C12_RESPONSE_TORUS_DENOMINATOR
    stencil_symbol = sum(
        coefficient * np.exp(1.0j * momentum * offset)
        for offset, coefficient in ((-1, -1), (0, 2), (1, -1))
    )
    incidence = nu_value * np.eye(4, dtype=np.complex128)
    normalized = incidence / nu_value
    return {
        "point_schema_version": C12_INCIDENCE_POINT_SCHEMA_VERSION,
        "incidence_family_id": C12_INCIDENCE_FAMILY_ID,
        "normalizer_formula_id": C12_NORMALIZER_FORMULA_ID,
        "torus_denominator": C12_RESPONSE_TORUS_DENOMINATOR,
        "reciprocal_index": reciprocal_index,
        "momentum": float(momentum),
        "root_of_unity_order": C12_RESPONSE_TORUS_DENOMINATOR,
        "root_of_unity_power": mode,
        "exact_nu_expression": str(exact_nu),
        "nu_minimal_polynomial_coefficients": coefficients,
        "nu_value": float(nu_value),
        "stencil_symbol_residual": float(abs(stencil_symbol - nu_value)),
        "incidence_operator": freeze_complex_tensor(incidence),
        "normalized_incidence_operator": freeze_complex_tensor(normalized),
        "application_stage": "POST_RESPONSE_READOUT_ONLY",
        "point_sha": "0" * 64,
    }


def _make_analytic_incidence_point(
    reciprocal_index: tuple[int, ...],
) -> C12IncidencePointWire:
    body = _build_analytic_incidence_point_body(reciprocal_index)
    provisional = _new_legacy_point(body)
    body["point_sha"] = canonical_sha(
        c12_incidence_point_wire_payload(provisional)
    )
    return _new_legacy_point(body)


def _verify_analytic_incidence_point(
    point: C12IncidencePointWire,
) -> C12IncidencePointWire:
    _exact_record(point, C12IncidencePointWire, "C12 analytic incidence point")
    _LEGACY_POINT_POST_INIT(point)
    if point.reciprocal_index not in C12_RESPONSE_RECIPROCAL_INDICES:
        raise ValueError("C12 analytic incidence point is not preregistered")
    for tensor in (point.incidence_operator, point.normalized_incidence_operator):
        _exact_record(tensor, FrozenComplexTensor, "C12 incidence tensor")
        verify_frozen_tensor(tensor)
    payload = c12_incidence_point_wire_payload(point)
    if point.point_sha != canonical_sha(payload):
        raise ValueError("C12 analytic incidence point SHA does not match its body")
    expected = _make_analytic_incidence_point(point.reciprocal_index)
    if point != expected:
        raise ValueError("C12 analytic incidence point differs from exact replay")
    return point


def _build_analytic_incidence_point(
    reciprocal_index: tuple[int, ...],
) -> C12IncidencePointWire:
    return _verify_analytic_incidence_point(
        _make_analytic_incidence_point(reciprocal_index)
    )


def _make_c12_analytic_incidence_certificate(
) -> C12AnalyticIncidenceCertificate:
    momentum = sp.Symbol("k", real=True)
    normalizer = 4 * sp.sin(momentum / 2) ** 2
    centered_symbol = 2 - sp.exp(sp.I * momentum) - sp.exp(-sp.I * momentum)
    if sp.simplify(centered_symbol - normalizer) != 0:
        raise AssertionError("centered stencil did not reproduce nu_inc")
    first_brillouin_domain = sp.Interval.Lopen(-sp.pi, sp.pi)
    if sp.ask(sp.Q.nonnegative(normalizer)) is not True:
        raise AssertionError("nu_inc is not nonnegative on the real line")
    zero_set = sp.solveset(
        sp.Eq(normalizer, 0),
        momentum,
        domain=first_brillouin_domain,
    )
    if zero_set != sp.FiniteSet(0):
        raise AssertionError("nu_inc zero set in the first BZ is not {0}")
    if sp.simplify(normalizer.subs(momentum, 0)) != 0:
        raise AssertionError("nu_inc must vanish at zero momentum")
    ir_limit = sp.simplify(sp.limit(normalizer / momentum**2, momentum, 0))
    if ir_limit != 1:
        raise AssertionError("centered incidence did not produce the exact IR limit")
    point_wires = tuple(
        _build_analytic_incidence_point(index)
        for index in C12_RESPONSE_RECIPROCAL_INDICES
    )
    if any(
        point.momentum == 0.0
        or not -math.pi < point.momentum <= math.pi
        or point.nu_value <= 0.0
        for point in point_wires
    ):
        raise AssertionError("frozen C12 points are outside the positive domain")
    provisional = C12AnalyticIncidenceCertificate(
        certificate_schema_version=(
            C12_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION
        ),
        incidence_family_id=C12_INCIDENCE_FAMILY_ID,
        normalizer_formula_id=C12_NORMALIZER_FORMULA_ID,
        normalizer_derivation_id=C12_NORMALIZER_DERIVATION_ID,
        stencil_offsets=((-1,), (0,), (1,)),
        stencil_coefficients=(-1, 2, -1),
        first_brillouin_domain_id=(
            "one-dimensional-minus-pi-open-pi-closed-v1"
        ),
        positivity_domain_id=C12_POSITIVITY_DOMAIN_ID,
        ir_limit_formula_id=C12_IR_LIMIT_FORMULA_ID,
        ir_limit_order=2,
        ir_limit_value=1.0,
        ir_conclusion=C12_IR_CONCLUSION,
        positivity_certified=True,
        absolute_signal_threshold_authority_ref=(
            C12_ABSOLUTE_SIGNAL_THRESHOLD_AUTHORITY_REF
        ),
        raw_bridge_noise_evidence_ref=C12_RAW_BRIDGE_NOISE_EVIDENCE_REF,
        raw_noise_absolute_threshold_authority_ref=(
            C12_RAW_NOISE_ABSOLUTE_THRESHOLD_AUTHORITY_REF
        ),
        relative_gap_threshold_authority_ref=(
            C12_RELATIVE_GAP_THRESHOLD_AUTHORITY_REF
        ),
        point_wires=point_wires,
        certificate_sha="0" * 64,
    )
    return replace(
        provisional,
        certificate_sha=canonical_sha(
            c12_analytic_incidence_certificate_payload(provisional)
        ),
    )


def _verify_c12_analytic_incidence_certificate_body(
    certificate: C12AnalyticIncidenceCertificate,
) -> C12AnalyticIncidenceCertificate:
    _exact_record(
        certificate,
        C12AnalyticIncidenceCertificate,
        "C12 analytic incidence certificate",
    )
    certificate.__post_init__()
    observed_payload = c12_analytic_incidence_certificate_payload(certificate)
    if certificate.certificate_sha != canonical_sha(observed_payload):
        raise ValueError(
            "C12 analytic incidence certificate SHA does not match its body"
        )
    for point in certificate.point_wires:
        _verify_analytic_incidence_point(point)
    expected = _make_c12_analytic_incidence_certificate()
    expected_payload = c12_analytic_incidence_certificate_payload(expected)
    if (
        observed_payload != expected_payload
        or certificate.certificate_sha != expected.certificate_sha
    ):
        raise ValueError(
            "C12 analytic incidence certificate differs from exact replay"
        )
    return certificate


def _raw_build_c12_analytic_incidence_certificate(
) -> C12AnalyticIncidenceCertificate:
    """Build the repository-closed analytic C12 incidence certificate."""

    certificate = _make_c12_analytic_incidence_certificate()
    return _verify_c12_analytic_incidence_certificate_body(certificate)


def _raw_verify_c12_analytic_incidence_certificate(
    certificate: C12AnalyticIncidenceCertificate,
) -> C12AnalyticIncidenceCertificate:
    """Verify an analytic C12 certificate against repository-owned replay."""

    return _verify_c12_analytic_incidence_certificate_body(certificate)


build_c12_analytic_incidence_certificate = freeze_rulespace_call_graph(
    _raw_build_c12_analytic_incidence_certificate
)
verify_c12_analytic_incidence_certificate = freeze_rulespace_call_graph(
    _raw_verify_c12_analytic_incidence_certificate
)
del (
    _raw_build_c12_analytic_incidence_certificate,
    _raw_verify_c12_analytic_incidence_certificate,
)


__all__ = [
    "C12_ABSOLUTE_SIGNAL_THRESHOLD_AUTHORITY_REF",
    "C12_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION",
    "C12_IR_CONCLUSION",
    "C12_IR_LIMIT_FORMULA_ID",
    "C12_NORMALIZER_DERIVATION_ID",
    "C12_POSITIVITY_DOMAIN_ID",
    "C12_RAW_BRIDGE_NOISE_EVIDENCE_REF",
    "C12_RAW_NOISE_ABSOLUTE_THRESHOLD_AUTHORITY_REF",
    "C12_RELATIVE_GAP_THRESHOLD_AUTHORITY_REF",
    "C12AnalyticIncidenceCertificate",
    "build_c12_analytic_incidence_certificate",
    "c12_analytic_incidence_certificate_payload",
    "verify_c12_analytic_incidence_certificate",
]
