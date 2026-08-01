"""Repository-closed analytic certificate for identity incidence.

The response protocol carries only ``certificate_sha`` on each momentum
wire.  This module defines the complete body behind that digest so an exact
compiler can reconstruct it from the historical readout protocol instead of
accepting an arbitrary SHA-shaped string.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, replace
import re
import struct
from typing import Literal

from .evidence import canonical_sha


IDENTITY_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION = (
    "v3m0.identity-analytic-incidence-certificate.v1"
)
IDENTITY_INCIDENCE_FAMILY_ID = "identity-incidence-v1"
IDENTITY_NORMALIZER_FORMULA_ID = "identity-positive-normalizer-v1"
IDENTITY_NORMALIZER_DERIVATION_ID = "identity-incidence-derivation-v1"
IDENTITY_IR_LIMIT_FORMULA_ID = (
    "lim-k-to-0-identity-normalizer-equals-one-v1"
)
IDENTITY_IR_CONSTANT_CONCLUSION = (
    "POSITIVE_MOMENTUM_INDEPENDENT_UNIT_NORMALIZER"
)

_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _LOWER_SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


@dataclass(frozen=True)
class IdentityAnalyticIncidenceCertificate:
    """Proof wire for the momentum-independent positive identity normalizer."""

    certificate_schema_version: str
    incidence_family_id: Literal["identity-incidence-v1"]
    normalizer_formula_id: Literal["identity-positive-normalizer-v1"]
    normalizer_derivation_id: Literal["identity-incidence-derivation-v1"]
    historical_readout_protocol_sha: str
    ir_limit_formula_id: Literal[
        "lim-k-to-0-identity-normalizer-equals-one-v1"
    ]
    ir_normalizer_limit: float
    ir_constant_conclusion: Literal[
        "POSITIVE_MOMENTUM_INDEPENDENT_UNIT_NORMALIZER"
    ]
    certificate_sha: str

    def __post_init__(self) -> None:
        if (
            self.certificate_schema_version
            != IDENTITY_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION
        ):
            raise ValueError("identity incidence certificate schema drifted")
        if self.incidence_family_id != IDENTITY_INCIDENCE_FAMILY_ID:
            raise ValueError("identity incidence family drifted")
        if self.normalizer_formula_id != IDENTITY_NORMALIZER_FORMULA_ID:
            raise ValueError("identity normalizer formula drifted")
        if self.normalizer_derivation_id != IDENTITY_NORMALIZER_DERIVATION_ID:
            raise ValueError("identity normalizer derivation drifted")
        _sha(
            self.historical_readout_protocol_sha,
            "historical_readout_protocol_sha",
        )
        if self.ir_limit_formula_id != IDENTITY_IR_LIMIT_FORMULA_ID:
            raise ValueError("identity IR-limit formula drifted")
        if (
            type(self.ir_normalizer_limit) is not float
            or struct.pack(">d", self.ir_normalizer_limit)
            != struct.pack(">d", 1.0)
        ):
            raise ValueError("identity IR normalizer limit is not fp64 one")
        if self.ir_constant_conclusion != IDENTITY_IR_CONSTANT_CONCLUSION:
            raise ValueError("identity IR constant conclusion drifted")
        _sha(self.certificate_sha, "certificate_sha")


def identity_analytic_incidence_certificate_payload(
    certificate: IdentityAnalyticIncidenceCertificate,
) -> dict[str, object]:
    _exact_record(
        certificate,
        IdentityAnalyticIncidenceCertificate,
        "identity analytic incidence certificate",
    )
    return {
        "certificate_schema_version": certificate.certificate_schema_version,
        "incidence_family_id": certificate.incidence_family_id,
        "normalizer_formula_id": certificate.normalizer_formula_id,
        "normalizer_derivation_id": certificate.normalizer_derivation_id,
        "historical_readout_protocol_sha": (
            certificate.historical_readout_protocol_sha
        ),
        "ir_limit_formula_id": certificate.ir_limit_formula_id,
        "ir_normalizer_limit": certificate.ir_normalizer_limit,
        "ir_constant_conclusion": certificate.ir_constant_conclusion,
    }


def verify_identity_analytic_incidence_certificate(
    certificate: IdentityAnalyticIncidenceCertificate,
    *,
    sha_builder=canonical_sha,
) -> IdentityAnalyticIncidenceCertificate:
    _exact_record(
        certificate,
        IdentityAnalyticIncidenceCertificate,
        "identity analytic incidence certificate",
    )
    certificate.__post_init__()
    expected = sha_builder(
        identity_analytic_incidence_certificate_payload(certificate)
    )
    if certificate.certificate_sha != expected:
        raise ValueError("identity incidence certificate SHA does not match body")
    return certificate


def build_identity_analytic_incidence_certificate(
    historical_readout_protocol_sha: str,
    *,
    sha_builder=canonical_sha,
) -> IdentityAnalyticIncidenceCertificate:
    _sha(
        historical_readout_protocol_sha,
        "historical_readout_protocol_sha",
    )
    provisional = IdentityAnalyticIncidenceCertificate(
        certificate_schema_version=(
            IDENTITY_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION
        ),
        incidence_family_id=IDENTITY_INCIDENCE_FAMILY_ID,
        normalizer_formula_id=IDENTITY_NORMALIZER_FORMULA_ID,
        normalizer_derivation_id=IDENTITY_NORMALIZER_DERIVATION_ID,
        historical_readout_protocol_sha=historical_readout_protocol_sha,
        ir_limit_formula_id=IDENTITY_IR_LIMIT_FORMULA_ID,
        ir_normalizer_limit=1.0,
        ir_constant_conclusion=IDENTITY_IR_CONSTANT_CONCLUSION,
        certificate_sha="0" * 64,
    )
    return replace(
        provisional,
        certificate_sha=sha_builder(
            identity_analytic_incidence_certificate_payload(provisional)
        ),
    )


__all__ = [
    "IDENTITY_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION",
    "IDENTITY_INCIDENCE_FAMILY_ID",
    "IDENTITY_IR_CONSTANT_CONCLUSION",
    "IDENTITY_IR_LIMIT_FORMULA_ID",
    "IDENTITY_NORMALIZER_DERIVATION_ID",
    "IDENTITY_NORMALIZER_FORMULA_ID",
    "IdentityAnalyticIncidenceCertificate",
    "build_identity_analytic_incidence_certificate",
    "identity_analytic_incidence_certificate_payload",
    "verify_identity_analytic_incidence_certificate",
]
