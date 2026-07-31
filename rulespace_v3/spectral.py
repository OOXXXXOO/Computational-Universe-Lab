"""Exact-zero spectral coverage and downstream stability audits for V3-M0.

This module implements the closed synthetic constant-kernel lane only.  It
still emits the complete singleton spectral body required by Task 10:
Root64-derived torus fill, one origin point, fourteen strict big-endian fp64
hard columns, and full protocol/grid bindings.  Laurent evidence is consumed
only by the normalized-residual issuer, never by spectral coverage.
"""

from __future__ import annotations

import base64
import json
import math
import re
import struct
import threading
import weakref
from dataclasses import dataclass, fields, replace
from fractions import Fraction
from typing import Callable, Literal, Optional

import numpy as np

from .dynamics import (
    VerifiedTransition,
    _reverify_verified_transition,
    measured_transition_payload,
)
from .evidence import canonical_sha
from .factory import frozen_tensor_array
from .fp64 import (
    MINIMUM_NORMAL,
    POWER_DRIFT_MACRO_STEP,
    POWER_DRIFT_METHOD_ID,
    POWER_DRIFT_SQUARING_COUNT,
    build_complex_dot_roundoff_bound,
    compute_power_drift_bounds,
    directed_add_upper,
    directed_div_lower,
    directed_div_upper,
    directed_mul_lower,
    directed_mul_upper,
    directed_sub_lower,
    frobenius_sqrt_upper,
    require_hard_scalar,
    require_semantic_zero,
)
from .fp64_protocol import (
    FP64_PROTOCOL_SCHEMA_VERSION,
    Fp64EnclosureProtocol,
    fp64_enclosure_protocol_payload,
    verify_fp64_enclosure_protocol,
)
from .grids import (
    DYNAMICS_GRID_SCHEMA_VERSION,
    DynamicsKGridManifest,
    build_dynamics_grid_manifest,
    dynamics_grid_payload,
    verify_dynamics_grid_manifest,
)
from .root64 import (
    DYADIC_EXPONENT,
    MACHIN_IDENTITY_ID,
    REMAINDER_METHOD_ID,
    ROOT_DENOMINATOR,
    TABLE_ID,
    TABLE_SCHEMA_VERSION,
    Fp64RootIntervalEntry,
    Fp64RootOfUnityIntervalTable,
)
from .laurent import (
    LaurentResidualCertificate,
    laurent_residual_payload,
    verify_laurent_residual_certificate,
)
from .metric import (
    StabilityMetricWitness,
    stability_metric_witness_payload,
    verify_stability_metric_witness,
)
from .structure import build_structure_manifest


SPECTRAL_SIDECAR_SCHEMA_VERSION = "v3m0.spectral-point-sidecar.v1"
SPECTRAL_COVERAGE_SCHEMA_VERSION = "v3m0.spectral-margin-coverage.v1"
NORMALIZED_AUDIT_SCHEMA_VERSION = "v3m0.normalized-metric-residual-audit.v1"
POWER_DRIFT_AUDIT_SCHEMA_VERSION = "v3m0.power-drift-audit.v1"
COLUMN_DATA_SCHEMA_VERSION = "v3m0.spectral-column-data.v1"
CANDIDATE_ALGORITHM_ID: Literal[
    "scalar-gauss-jordan-hermitian-cholesky-v1"
] = "scalar-gauss-jordan-hermitian-cholesky-v1"
COLUMN_ENCODING_ID: Literal[
    "strict-base64-big-endian-f64-columns-v1"
] = "strict-base64-big-endian-f64-columns-v1"
ROUNDING_METHOD_ID: Literal[
    "fp64-operation-count-nextafter-columnar-v1"
] = "fp64-operation-count-nextafter-columnar-v1"
TORUS_DOMAIN_ID: Literal[
    "minus-pi-pi-periodic-v1"
] = "minus-pi-pi-periodic-v1"
DISTANCE_CONVENTION_ID: Literal[
    "principal-linf-torus-v1"
] = "principal-linf-torus-v1"
DIVISION_METHOD_ID: Literal[
    "fp64-nextafter-outward-division-v1"
] = "fp64-nextafter-outward-division-v1"

SPECTRAL_MAX_GRID_POINTS = 262_144
SPECTRAL_MAX_CUBIC_WORK = 2_000_000_000
SPECTRAL_MAX_COLUMN_RAW_BYTES = 67_108_864
SPECTRAL_MAX_CANONICAL_BODY_BYTES = 100_663_296
SPECTRAL_HARD_COLUMN_COUNT = 14
SPECTRAL_AVAILABLE_COLUMN_COUNT = 18
SPECTRAL_M_SIGMA_MIN_GATE = 1.0e-8
SPECTRAL_G_LAMBDA_MIN_GATE = 1.0e-12
SPECTRAL_CONDITION_MAX = 1.0e8
NORMALIZED_METRIC_RESIDUAL_GATE = 1.0e-12

RAW_COLUMN_NAMES = (
    "raw_m_sigma_min_b64",
    "raw_m_sigma_max_b64",
    "raw_g_lambda_min_b64",
    "raw_g_lambda_max_b64",
)
HARD_COLUMN_NAMES = (
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
)

_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()


def _require_exact_record_fields(
    value: object,
    record_type: type,
    field: str,
) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} has the wrong exact type")
    expected = frozenset(item.name for item in fields(record_type))
    actual = frozenset(vars(value))
    if actual != expected:
        unknown = sorted(actual - expected)
        missing = sorted(expected - actual)
        raise ValueError(
            f"{field} record fields differ; "
            f"unknown={unknown}, missing={missing}"
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


def _wire_int(value: object, field: str, *, positive: bool = False) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if positive and value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _wire_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    return require_hard_scalar(value, field)


def _nonnegative_float(value: object, field: str) -> float:
    result = _wire_float(value, field)
    if result < 0.0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _positive_float(value: object, field: str) -> float:
    result = _wire_float(value, field)
    if result <= 0.0:
        raise ValueError(f"{field} must be positive")
    return result


def _float_tuple(
    value: object,
    field: str,
    *,
    length: int,
    positive: bool = False,
    nonnegative: bool = False,
) -> tuple[float, ...]:
    if type(value) is not tuple or len(value) != length:
        raise ValueError(f"{field} must have length {length}")
    result: list[float] = []
    for index, item in enumerate(value):
        if positive:
            checked = _positive_float(item, f"{field}[{index}]")
        elif nonnegative:
            checked = _nonnegative_float(item, f"{field}[{index}]")
        else:
            checked = _wire_float(item, f"{field}[{index}]")
        result.append(checked)
    return tuple(result)


def _protocol_record(protocol: Fp64EnclosureProtocol) -> dict[str, object]:
    return {
        **fp64_enclosure_protocol_payload(protocol),
        "protocol_sha": protocol.protocol_sha,
    }


def _grid_record(grid: DynamicsKGridManifest) -> dict[str, object]:
    return {
        **dynamics_grid_payload(grid),
        "dynamics_grid_sha": grid.dynamics_grid_sha,
    }


def _metric_record(witness: StabilityMetricWitness) -> dict[str, object]:
    return {
        **stability_metric_witness_payload(witness),
        "witness_sha": witness.witness_sha,
    }


def _residual_record(
    residual: LaurentResidualCertificate,
) -> dict[str, object]:
    return {
        **laurent_residual_payload(residual),
        "residual_sha": residual.residual_sha,
    }


@dataclass(frozen=True)
class SpectralPointEnclosureColumnarSidecar:
    sidecar_schema_version: str
    qualification_grid_sha: str
    point_count: int
    candidate_algorithm_id: Literal[
        "scalar-gauss-jordan-hermitian-cholesky-v1"
    ]
    encoding_id: Literal["strict-base64-big-endian-f64-columns-v1"]
    raw_diagnostic_status: Literal[
        "available-lapack-v1",
        "unavailable-v1",
    ]
    raw_diagnostic_unavailable_reason: Optional[str]
    raw_m_sigma_min_b64: Optional[str]
    raw_m_sigma_max_b64: Optional[str]
    raw_g_lambda_min_b64: Optional[str]
    raw_g_lambda_max_b64: Optional[str]
    transition_symbol_error_upper_b64: str
    metric_symbol_error_upper_b64: str
    transition_frobenius_upper_b64: str
    inverse_frobenius_upper_b64: str
    inverse_residual_frobenius_upper_b64: str
    m_sigma_min_lower_b64: str
    m_sigma_max_upper_b64: str
    metric_frobenius_upper_b64: str
    cholesky_factorization_residual_frobenius_upper_b64: str
    cholesky_inverse_frobenius_upper_b64: str
    cholesky_inverse_residual_frobenius_upper_b64: str
    ell_lower_b64: str
    g_lambda_min_lower_b64: str
    g_lambda_max_upper_b64: str
    raw_byte_count: int
    column_data_sha: str
    roundoff_enclosure_method_id: Literal[
        "fp64-operation-count-nextafter-columnar-v1"
    ]
    sidecar_sha: str

    def __post_init__(self) -> None:
        _text(self.sidecar_schema_version, "sidecar_schema_version")
        _sha(self.qualification_grid_sha, "qualification_grid_sha")
        points = _wire_int(self.point_count, "point_count", positive=True)
        if points > SPECTRAL_MAX_GRID_POINTS:
            raise ValueError("sidecar point count exceeds the spectral cap")
        if self.candidate_algorithm_id != CANDIDATE_ALGORITHM_ID:
            raise ValueError("candidate algorithm is not frozen")
        if self.encoding_id != COLUMN_ENCODING_ID:
            raise ValueError("column encoding is not frozen")
        if self.raw_diagnostic_status not in (
            "available-lapack-v1",
            "unavailable-v1",
        ):
            raise ValueError("raw diagnostic status is not closed")
        if self.raw_diagnostic_status == "unavailable-v1":
            _text(
                self.raw_diagnostic_unavailable_reason,
                "raw_diagnostic_unavailable_reason",
            )
            if any(getattr(self, name) is not None for name in RAW_COLUMN_NAMES):
                raise ValueError(
                    "unavailable diagnostics require all raw columns absent"
                )
            encoded_names = HARD_COLUMN_NAMES
        else:
            if self.raw_diagnostic_unavailable_reason is not None:
                raise ValueError(
                    "available diagnostics require no unavailable reason"
                )
            if any(getattr(self, name) is None for name in RAW_COLUMN_NAMES):
                raise ValueError(
                    "available diagnostics require all raw columns"
                )
            encoded_names = RAW_COLUMN_NAMES + HARD_COLUMN_NAMES
        expected_bytes = points * 8 * len(encoded_names)
        count = _wire_int(self.raw_byte_count, "raw_byte_count")
        if count != expected_bytes:
            raise ValueError("raw_byte_count does not match encoded columns")
        if count > SPECTRAL_MAX_COLUMN_RAW_BYTES:
            raise ValueError("columnar sidecar exceeds the raw-byte cap")
        for name in encoded_names:
            _decode_f64_column(getattr(self, name), points, name)
        _sha(self.column_data_sha, "column_data_sha")
        if self.roundoff_enclosure_method_id != ROUNDING_METHOD_ID:
            raise ValueError("roundoff enclosure method is not frozen")
        _sha(self.sidecar_sha, "sidecar_sha")


def spectral_point_sidecar_payload(
    sidecar: SpectralPointEnclosureColumnarSidecar,
) -> dict[str, object]:
    if not isinstance(sidecar, SpectralPointEnclosureColumnarSidecar):
        raise TypeError(
            "sidecar must be a SpectralPointEnclosureColumnarSidecar"
        )
    return {
        "sidecar_schema_version": sidecar.sidecar_schema_version,
        "qualification_grid_sha": sidecar.qualification_grid_sha,
        "point_count": sidecar.point_count,
        "candidate_algorithm_id": sidecar.candidate_algorithm_id,
        "encoding_id": sidecar.encoding_id,
        "raw_diagnostic_status": sidecar.raw_diagnostic_status,
        "raw_diagnostic_unavailable_reason": (
            sidecar.raw_diagnostic_unavailable_reason
        ),
        "raw_m_sigma_min_b64": sidecar.raw_m_sigma_min_b64,
        "raw_m_sigma_max_b64": sidecar.raw_m_sigma_max_b64,
        "raw_g_lambda_min_b64": sidecar.raw_g_lambda_min_b64,
        "raw_g_lambda_max_b64": sidecar.raw_g_lambda_max_b64,
        **{name: getattr(sidecar, name) for name in HARD_COLUMN_NAMES},
        "raw_byte_count": sidecar.raw_byte_count,
        "column_data_sha": sidecar.column_data_sha,
        "roundoff_enclosure_method_id": (
            sidecar.roundoff_enclosure_method_id
        ),
    }


def _sidecar_record(
    sidecar: SpectralPointEnclosureColumnarSidecar,
) -> dict[str, object]:
    return {
        **spectral_point_sidecar_payload(sidecar),
        "sidecar_sha": sidecar.sidecar_sha,
    }


@dataclass(frozen=True)
class SpectralMarginCoverage:
    coverage_schema_version: str
    transition_sha: str
    stability_metric_witness_sha: str
    fp64_enclosure_protocol: Fp64EnclosureProtocol
    qualification_grid: DynamicsKGridManifest
    spectral_diagnostic_grid: DynamicsKGridManifest
    torus_domain_id: Literal["minus-pi-pi-periodic-v1"]
    distance_convention_id: Literal["principal-linf-torus-v1"]
    fill_distance: float
    raw_diagnostic_status: Literal[
        "available-lapack-v1",
        "unavailable-v1",
    ]
    raw_diagnostic_unavailable_reason: Optional[str]
    raw_m_sigma_min: Optional[tuple[float, ...]]
    raw_m_sigma_max: Optional[tuple[float, ...]]
    raw_g_lambda_min: Optional[tuple[float, ...]]
    raw_g_lambda_max: Optional[tuple[float, ...]]
    point_enclosures: SpectralPointEnclosureColumnarSidecar
    grid_m_sigma_min_lower: tuple[float, ...]
    grid_m_sigma_max_upper: tuple[float, ...]
    grid_g_lambda_min_lower: tuple[float, ...]
    grid_g_lambda_max_upper: tuple[float, ...]
    m_sigma_min_axis_derivative_bounds: tuple[float, ...]
    m_sigma_max_axis_derivative_bounds: tuple[float, ...]
    g_lambda_min_axis_derivative_bounds: tuple[float, ...]
    g_lambda_max_axis_derivative_bounds: tuple[float, ...]
    m_sigma_min_coverage_increment: float
    m_sigma_max_coverage_increment: float
    g_lambda_min_coverage_increment: float
    g_lambda_max_coverage_increment: float
    covered_m_sigma_min_lower: float
    covered_m_sigma_max_upper: float
    covered_g_lambda_min_lower: float
    covered_g_lambda_max_upper: float
    covered_m_condition_number_upper: float
    covered_g_condition_number_upper: float
    spectral_radius_drift_diagnostic: Optional[float]
    coverage_sha: str

    def __post_init__(self) -> None:
        _text(self.coverage_schema_version, "coverage_schema_version")
        _sha(self.transition_sha, "transition_sha")
        _sha(
            self.stability_metric_witness_sha,
            "stability_metric_witness_sha",
        )
        if not isinstance(
            self.fp64_enclosure_protocol,
            Fp64EnclosureProtocol,
        ):
            raise TypeError("fp64_enclosure_protocol has the wrong type")
        if not isinstance(self.qualification_grid, DynamicsKGridManifest):
            raise TypeError("qualification_grid has the wrong type")
        if not isinstance(
            self.spectral_diagnostic_grid,
            DynamicsKGridManifest,
        ):
            raise TypeError("spectral_diagnostic_grid has the wrong type")
        if self.torus_domain_id != TORUS_DOMAIN_ID:
            raise ValueError("torus domain is not frozen")
        if self.distance_convention_id != DISTANCE_CONVENTION_ID:
            raise ValueError("distance convention is not frozen")
        _nonnegative_float(self.fill_distance, "fill_distance")
        if self.raw_diagnostic_status not in (
            "available-lapack-v1",
            "unavailable-v1",
        ):
            raise ValueError("raw diagnostic status is not closed")
        point_count = len(self.qualification_grid.reciprocal_indices)
        raw_arrays = (
            self.raw_m_sigma_min,
            self.raw_m_sigma_max,
            self.raw_g_lambda_min,
            self.raw_g_lambda_max,
        )
        if self.raw_diagnostic_status == "unavailable-v1":
            _text(
                self.raw_diagnostic_unavailable_reason,
                "raw_diagnostic_unavailable_reason",
            )
            if any(value is not None for value in raw_arrays):
                raise ValueError(
                    "unavailable diagnostics require all raw arrays absent"
                )
            if self.spectral_radius_drift_diagnostic is not None:
                raise ValueError(
                    "unavailable diagnostics require no radius diagnostic"
                )
        else:
            if self.raw_diagnostic_unavailable_reason is not None:
                raise ValueError(
                    "available diagnostics require no unavailable reason"
                )
            for index, value in enumerate(raw_arrays):
                _float_tuple(
                    value,
                    f"raw_diagnostic[{index}]",
                    length=point_count,
                )
            _nonnegative_float(
                self.spectral_radius_drift_diagnostic,
                "spectral_radius_drift_diagnostic",
            )
        if not isinstance(
            self.point_enclosures,
            SpectralPointEnclosureColumnarSidecar,
        ):
            raise TypeError("point_enclosures has the wrong type")
        if self.point_enclosures.point_count != point_count:
            raise ValueError("point enclosure count does not match grid")
        if (
            self.point_enclosures.qualification_grid_sha
            != self.qualification_grid.dynamics_grid_sha
        ):
            raise ValueError("point sidecar grid binding mismatch")
        if self.point_enclosures.raw_diagnostic_status != (
            self.raw_diagnostic_status
        ):
            raise ValueError("point and coverage diagnostic status differ")
        _float_tuple(
            self.grid_m_sigma_min_lower,
            "grid_m_sigma_min_lower",
            length=point_count,
            positive=True,
        )
        _float_tuple(
            self.grid_m_sigma_max_upper,
            "grid_m_sigma_max_upper",
            length=point_count,
            positive=True,
        )
        _float_tuple(
            self.grid_g_lambda_min_lower,
            "grid_g_lambda_min_lower",
            length=point_count,
            positive=True,
        )
        _float_tuple(
            self.grid_g_lambda_max_upper,
            "grid_g_lambda_max_upper",
            length=point_count,
            positive=True,
        )
        ndim = self.qualification_grid.spatial_ndim
        derivative_fields = (
            "m_sigma_min_axis_derivative_bounds",
            "m_sigma_max_axis_derivative_bounds",
            "g_lambda_min_axis_derivative_bounds",
            "g_lambda_max_axis_derivative_bounds",
        )
        for field in derivative_fields:
            _float_tuple(
                getattr(self, field),
                field,
                length=ndim,
                nonnegative=True,
            )
        increment_fields = (
            "m_sigma_min_coverage_increment",
            "m_sigma_max_coverage_increment",
            "g_lambda_min_coverage_increment",
            "g_lambda_max_coverage_increment",
        )
        for field in increment_fields:
            _nonnegative_float(getattr(self, field), field)
        for field in (
            "covered_m_sigma_min_lower",
            "covered_m_sigma_max_upper",
            "covered_g_lambda_min_lower",
            "covered_g_lambda_max_upper",
            "covered_m_condition_number_upper",
            "covered_g_condition_number_upper",
        ):
            _positive_float(getattr(self, field), field)
        if (
            self.qualification_grid.qualification_profile
            == "exact-offset-zero-v1"
        ):
            for field in derivative_fields:
                for index, value in enumerate(getattr(self, field)):
                    require_semantic_zero(value, f"{field}[{index}]")
            for field in increment_fields:
                require_semantic_zero(getattr(self, field), field)
            for field in (
                "transition_symbol_error_upper_b64",
                "metric_symbol_error_upper_b64",
            ):
                values = _decode_f64_column(
                    getattr(self.point_enclosures, field),
                    point_count,
                    field,
                )
                for index, value in enumerate(values):
                    require_semantic_zero(value, f"{field}[{index}]")
        _sha(self.coverage_sha, "coverage_sha")


def spectral_margin_coverage_payload(
    coverage: SpectralMarginCoverage,
) -> dict[str, object]:
    if not isinstance(coverage, SpectralMarginCoverage):
        raise TypeError("coverage must be a SpectralMarginCoverage")
    return {
        "coverage_schema_version": coverage.coverage_schema_version,
        "transition_sha": coverage.transition_sha,
        "stability_metric_witness_sha": (
            coverage.stability_metric_witness_sha
        ),
        "fp64_enclosure_protocol": _protocol_record(
            coverage.fp64_enclosure_protocol
        ),
        "qualification_grid": _grid_record(coverage.qualification_grid),
        "spectral_diagnostic_grid": _grid_record(
            coverage.spectral_diagnostic_grid
        ),
        "torus_domain_id": coverage.torus_domain_id,
        "distance_convention_id": coverage.distance_convention_id,
        "fill_distance": coverage.fill_distance,
        "raw_diagnostic_status": coverage.raw_diagnostic_status,
        "raw_diagnostic_unavailable_reason": (
            coverage.raw_diagnostic_unavailable_reason
        ),
        "raw_m_sigma_min": (
            None
            if coverage.raw_m_sigma_min is None
            else list(coverage.raw_m_sigma_min)
        ),
        "raw_m_sigma_max": (
            None
            if coverage.raw_m_sigma_max is None
            else list(coverage.raw_m_sigma_max)
        ),
        "raw_g_lambda_min": (
            None
            if coverage.raw_g_lambda_min is None
            else list(coverage.raw_g_lambda_min)
        ),
        "raw_g_lambda_max": (
            None
            if coverage.raw_g_lambda_max is None
            else list(coverage.raw_g_lambda_max)
        ),
        "point_enclosures": _sidecar_record(coverage.point_enclosures),
        "grid_m_sigma_min_lower": list(
            coverage.grid_m_sigma_min_lower
        ),
        "grid_m_sigma_max_upper": list(
            coverage.grid_m_sigma_max_upper
        ),
        "grid_g_lambda_min_lower": list(
            coverage.grid_g_lambda_min_lower
        ),
        "grid_g_lambda_max_upper": list(
            coverage.grid_g_lambda_max_upper
        ),
        "m_sigma_min_axis_derivative_bounds": list(
            coverage.m_sigma_min_axis_derivative_bounds
        ),
        "m_sigma_max_axis_derivative_bounds": list(
            coverage.m_sigma_max_axis_derivative_bounds
        ),
        "g_lambda_min_axis_derivative_bounds": list(
            coverage.g_lambda_min_axis_derivative_bounds
        ),
        "g_lambda_max_axis_derivative_bounds": list(
            coverage.g_lambda_max_axis_derivative_bounds
        ),
        "m_sigma_min_coverage_increment": (
            coverage.m_sigma_min_coverage_increment
        ),
        "m_sigma_max_coverage_increment": (
            coverage.m_sigma_max_coverage_increment
        ),
        "g_lambda_min_coverage_increment": (
            coverage.g_lambda_min_coverage_increment
        ),
        "g_lambda_max_coverage_increment": (
            coverage.g_lambda_max_coverage_increment
        ),
        "covered_m_sigma_min_lower": (
            coverage.covered_m_sigma_min_lower
        ),
        "covered_m_sigma_max_upper": (
            coverage.covered_m_sigma_max_upper
        ),
        "covered_g_lambda_min_lower": (
            coverage.covered_g_lambda_min_lower
        ),
        "covered_g_lambda_max_upper": (
            coverage.covered_g_lambda_max_upper
        ),
        "covered_m_condition_number_upper": (
            coverage.covered_m_condition_number_upper
        ),
        "covered_g_condition_number_upper": (
            coverage.covered_g_condition_number_upper
        ),
        "spectral_radius_drift_diagnostic": (
            coverage.spectral_radius_drift_diagnostic
        ),
    }


def _preflight_spectral_resources(
    *,
    point_count: int,
    n_state: int,
    encoded_column_count: int,
) -> None:
    points = _wire_int(point_count, "point_count", positive=True)
    state = _wire_int(n_state, "n_state", positive=True)
    columns = _wire_int(
        encoded_column_count,
        "encoded_column_count",
        positive=True,
    )
    if columns not in (
        SPECTRAL_HARD_COLUMN_COUNT,
        SPECTRAL_AVAILABLE_COLUMN_COUNT,
    ):
        raise ValueError("encoded column count is not a closed profile")
    if points > SPECTRAL_MAX_GRID_POINTS:
        raise ValueError("spectral grid point cap exceeded")
    if 3 * points * state**3 > SPECTRAL_MAX_CUBIC_WORK:
        raise ValueError("spectral cubic-work cap exceeded")
    if points * 8 * columns > SPECTRAL_MAX_COLUMN_RAW_BYTES:
        raise ValueError("spectral column raw-byte cap exceeded")


def _bounded_text(value: object, field: str) -> str:
    text = _text(value, field)
    limit = SPECTRAL_MAX_CANONICAL_BODY_BYTES
    if len(text) > limit:
        raise ValueError(f"{field} exceeds the spectral body cap")
    if len(text.encode("utf-8")) > limit:
        raise ValueError(f"{field} exceeds the spectral body cap")
    return text


def _bounded_root64_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if abs(value).bit_length() > 2 * DYADIC_EXPONENT + 16:
        raise ValueError(f"{field} exceeds the Root64 bigint cap")
    return value


def _preflight_root64_protocol(
    protocol: Fp64EnclosureProtocol,
) -> None:
    _require_exact_record_fields(
        protocol,
        Fp64EnclosureProtocol,
        "fp64_enclosure_protocol",
    )
    if protocol.protocol_schema_version != FP64_PROTOCOL_SCHEMA_VERSION:
        raise ValueError("unexpected fp64 protocol schema")
    table = protocol.root_interval_table
    _require_exact_record_fields(
        table,
        Fp64RootOfUnityIntervalTable,
        "root_interval_table",
    )
    if table.table_schema_version != TABLE_SCHEMA_VERSION:
        raise ValueError("unexpected Root64 table schema")
    if table.table_id != TABLE_ID:
        raise ValueError("unexpected Root64 table id")
    if table.denominator != ROOT_DENOMINATOR:
        raise ValueError("unexpected Root64 denominator")
    if table.dyadic_exponent != DYADIC_EXPONENT:
        raise ValueError("unexpected Root64 dyadic exponent")
    if table.taylor_precision_bits != DYADIC_EXPONENT:
        raise ValueError("unexpected Root64 Taylor precision")
    if table.machin_identity_id != MACHIN_IDENTITY_ID:
        raise ValueError("unexpected Root64 Machin identity")
    if table.remainder_method_id != REMAINDER_METHOD_ID:
        raise ValueError("unexpected Root64 remainder method")
    _bounded_root64_int(
        table.pi_lower_numerator,
        "root_interval_table.pi_lower_numerator",
    )
    _bounded_root64_int(
        table.pi_upper_numerator,
        "root_interval_table.pi_upper_numerator",
    )
    if type(table.entries) is not tuple:
        raise TypeError("Root64 entries must be a tuple")
    if len(table.entries) != ROOT_DENOMINATOR:
        raise ValueError("Root64 table must contain exactly 64 entries")
    for expected_index, entry in enumerate(table.entries):
        _require_exact_record_fields(
            entry,
            Fp64RootIntervalEntry,
            f"root_interval_table.entries[{expected_index}]",
        )
        for field in (
            "root_index",
            "dyadic_exponent",
            "real_lower_numerator",
            "real_upper_numerator",
            "imag_lower_numerator",
            "imag_upper_numerator",
            "real_center_f64_bits",
            "imag_center_f64_bits",
            "center_distance_squared_upper_numerator",
            "center_distance_squared_upper_power_of_two",
            "center_distance_upper_f64_bits",
        ):
            _bounded_root64_int(
                getattr(entry, field),
                f"root_interval_table.entries[{expected_index}].{field}",
            )
        if entry.root_index != expected_index:
            raise ValueError("Root64 entries are not canonically ordered")
        if entry.dyadic_exponent != DYADIC_EXPONENT:
            raise ValueError("Root64 entry dyadic exponent mismatch")
        if entry.center_distance_squared_upper_power_of_two != (
            -2 * DYADIC_EXPONENT
        ):
            raise ValueError("Root64 distance-square exponent mismatch")
        for field in (
            "real_center_f64_bits",
            "imag_center_f64_bits",
            "center_distance_upper_f64_bits",
        ):
            bits = getattr(entry, field)
            if not 0 <= bits <= 0xFFFFFFFFFFFFFFFF:
                raise ValueError(f"Root64 {field} is not an unsigned f64")
    _sha(table.table_sha, "root_interval_table.table_sha")
    _sha(protocol.protocol_sha, "fp64_enclosure_protocol.protocol_sha")
    protocol.__post_init__()


def _preflight_exact_zero_coverage_record(
    coverage: SpectralMarginCoverage,
    transition: VerifiedTransition,
) -> None:
    """Bound and type-check raw coverage before hashing or Root64 replay."""

    _require_exact_record_fields(
        coverage,
        SpectralMarginCoverage,
        "coverage",
    )
    if coverage.coverage_schema_version != SPECTRAL_COVERAGE_SCHEMA_VERSION:
        raise ValueError("unexpected spectral coverage schema")
    if type(transition) is not VerifiedTransition:
        raise TypeError("transition must be an exact VerifiedTransition")
    if type(coverage.fp64_enclosure_protocol) is not Fp64EnclosureProtocol:
        raise TypeError("fp64_enclosure_protocol has the wrong exact type")
    _preflight_root64_protocol(coverage.fp64_enclosure_protocol)
    if type(coverage.point_enclosures) is not (
        SpectralPointEnclosureColumnarSidecar
    ):
        raise TypeError("point_enclosures has the wrong exact type")
    try:
        raw_transition = transition.transition
    except (AttributeError, TypeError) as exc:
        raise TypeError("transition is not a live VerifiedTransition") from exc
    expected_ndim = len(raw_transition.spatial_shape)
    grids = (
        ("qualification_grid", coverage.qualification_grid),
        ("spectral_diagnostic_grid", coverage.spectral_diagnostic_grid),
    )
    for field, grid in grids:
        _require_exact_record_fields(
            grid,
            DynamicsKGridManifest,
            field,
        )
        if grid.grid_schema_version != DYNAMICS_GRID_SCHEMA_VERSION:
            raise ValueError(f"{field} has an unexpected schema")
        if grid.qualification_profile != "exact-offset-zero-v1":
            raise ValueError(
                f"{field} is outside the exact-zero coverage lane"
            )
        if type(grid.spatial_ndim) is not int:
            raise TypeError(f"{field}.spatial_ndim must be an int")
        if grid.spatial_ndim != expected_ndim:
            raise ValueError(f"{field} dimension does not match transition")
        if (
            type(grid.torus_denominators) is not tuple
            or len(grid.torus_denominators) != expected_ndim
        ):
            raise ValueError(f"{field} denominator cardinality mismatch")
        if (
            type(grid.reciprocal_indices) is not tuple
            or len(grid.reciprocal_indices) != 1
        ):
            raise ValueError(f"{field} must contain the origin singleton")
        origin = grid.reciprocal_indices[0]
        if type(origin) is not tuple or len(origin) != expected_ndim:
            raise ValueError(f"{field} origin dimension mismatch")

    sidecar = coverage.point_enclosures
    _require_exact_record_fields(
        sidecar,
        SpectralPointEnclosureColumnarSidecar,
        "point_enclosures",
    )
    if sidecar.sidecar_schema_version != SPECTRAL_SIDECAR_SCHEMA_VERSION:
        raise ValueError("unexpected spectral sidecar schema")
    if type(sidecar.point_count) is not int or sidecar.point_count != 1:
        raise ValueError("exact-zero sidecar point_count must equal one")
    if sidecar.point_count != len(
        coverage.qualification_grid.reciprocal_indices
    ):
        raise ValueError("sidecar point count does not match grid")
    if sidecar.raw_diagnostic_status == "available-lapack-v1":
        encoded_names = RAW_COLUMN_NAMES + HARD_COLUMN_NAMES
    elif sidecar.raw_diagnostic_status == "unavailable-v1":
        encoded_names = HARD_COLUMN_NAMES
        if any(getattr(sidecar, name) is not None for name in RAW_COLUMN_NAMES):
            raise ValueError(
                "unavailable diagnostics require all raw columns absent"
            )
    else:
        raise ValueError("sidecar raw diagnostic status is not closed")
    _preflight_spectral_resources(
        point_count=1,
        n_state=len(raw_transition.channel_order),
        encoded_column_count=len(encoded_names),
    )
    expected_encoded_length = 4 * ((sidecar.point_count * 8 + 2) // 3)
    for name in encoded_names:
        value = getattr(sidecar, name)
        if type(value) is not str:
            raise TypeError(f"{name} must be a string")
        if len(value) != expected_encoded_length:
            raise ValueError(f"{name} encoded length is not canonical")

    for owner, prefix in (
        (coverage, "coverage"),
        (sidecar, "point_enclosures"),
    ):
        reason = owner.raw_diagnostic_unavailable_reason
        if reason is not None:
            _bounded_text(
                reason,
                f"{prefix}.raw_diagnostic_unavailable_reason",
            )

    point_count = sidecar.point_count
    raw_arrays = (
        "raw_m_sigma_min",
        "raw_m_sigma_max",
        "raw_g_lambda_min",
        "raw_g_lambda_max",
    )
    for field in raw_arrays:
        value = getattr(coverage, field)
        if value is not None and (
            type(value) is not tuple or len(value) != point_count
        ):
            raise ValueError(f"{field} must be a canonical point tuple")
    for field in (
        "grid_m_sigma_min_lower",
        "grid_m_sigma_max_upper",
        "grid_g_lambda_min_lower",
        "grid_g_lambda_max_upper",
    ):
        value = getattr(coverage, field)
        if type(value) is not tuple or len(value) != point_count:
            raise ValueError(f"{field} must be a canonical point tuple")
    for field in (
        "m_sigma_min_axis_derivative_bounds",
        "m_sigma_max_axis_derivative_bounds",
        "g_lambda_min_axis_derivative_bounds",
        "g_lambda_max_axis_derivative_bounds",
    ):
        value = getattr(coverage, field)
        if type(value) is not tuple or len(value) != expected_ndim:
            raise ValueError(f"{field} must be a canonical axis tuple")

    # Raw objects can be made with object.__new__; rerun bounded constructors.
    for _, grid in grids:
        grid.__post_init__()
    sidecar.__post_init__()
    coverage.__post_init__()


def _require_coverage_body_within_cap(
    coverage: SpectralMarginCoverage,
) -> None:
    """Stream canonical JSON sizing without joining a giant byte string."""

    encoder = json.JSONEncoder(
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    total = 0
    for chunk in encoder.iterencode(
        spectral_margin_coverage_payload(coverage)
    ):
        total += len(chunk.encode("utf-8"))
        if total > SPECTRAL_MAX_CANONICAL_BODY_BYTES:
            raise ValueError("spectral canonical body exceeds the 96 MiB cap")


def _decode_f64_column(
    value: object,
    point_count: int,
    field: str,
) -> tuple[float, ...]:
    text = _text(value, field)
    expected_raw = point_count * 8
    expected_encoded = 4 * ((expected_raw + 2) // 3)
    if len(text) != expected_encoded:
        raise ValueError(f"{field} encoded length is not canonical")
    try:
        raw = base64.b64decode(text, validate=True)
    except Exception as exc:
        raise ValueError(f"{field} is not strict base64") from exc
    if len(raw) != expected_raw:
        raise ValueError(f"{field} decoded byte length mismatch")
    if base64.b64encode(raw).decode("ascii") != text:
        raise ValueError(f"{field} base64 spelling is not canonical")
    result = tuple(
        require_hard_scalar(item[0], f"{field}[{index}]")
        for index, item in enumerate(struct.iter_unpack(">d", raw))
    )
    if len(result) != point_count:
        raise ValueError(f"{field} decoded point count mismatch")
    return result


def _encode_f64_column(values: tuple[float, ...]) -> str:
    raw = b"".join(
        struct.pack(">d", require_hard_scalar(value, "column value"))
        for value in values
    )
    return base64.b64encode(raw).decode("ascii")


def _ordered_column_names(
    sidecar: SpectralPointEnclosureColumnarSidecar,
) -> tuple[str, ...]:
    if sidecar.raw_diagnostic_status == "available-lapack-v1":
        return RAW_COLUMN_NAMES + HARD_COLUMN_NAMES
    return HARD_COLUMN_NAMES


def _column_data_payload(
    sidecar: SpectralPointEnclosureColumnarSidecar,
) -> dict[str, object]:
    return {
        "column_data_schema_version": COLUMN_DATA_SCHEMA_VERSION,
        "ordered_columns": [
            [name, getattr(sidecar, name)]
            for name in _ordered_column_names(sidecar)
        ],
    }


def _verify_sidecar(
    sidecar: SpectralPointEnclosureColumnarSidecar,
) -> SpectralPointEnclosureColumnarSidecar:
    _require_exact_record_fields(
        sidecar,
        SpectralPointEnclosureColumnarSidecar,
        "sidecar",
    )
    if sidecar.sidecar_schema_version != SPECTRAL_SIDECAR_SCHEMA_VERSION:
        raise ValueError("unexpected spectral sidecar schema")
    if sidecar.column_data_sha != canonical_sha(
        _column_data_payload(sidecar)
    ):
        raise ValueError("column_data_sha does not match ordered columns")
    if sidecar.sidecar_sha != canonical_sha(
        spectral_point_sidecar_payload(sidecar)
    ):
        raise ValueError("sidecar_sha does not match complete body")
    return sidecar


def _fraction_upper_float(value: Fraction, field: str) -> float:
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    candidate = float(value)
    if not math.isfinite(candidate):
        raise ValueError(f"{field} exceeds finite fp64 range")
    if Fraction(*candidate.as_integer_ratio()) < value:
        candidate = math.nextafter(candidate, math.inf)
    return require_hard_scalar(candidate, field)


def _all_positive_zero_imaginary(values: np.ndarray) -> bool:
    array = np.asarray(values, dtype=np.complex128)
    imaginary = np.ascontiguousarray(array.imag, dtype=np.float64)
    return bool(np.all(imaginary.view(np.uint64) == 0))


def _require_signed_permutation(values: np.ndarray) -> None:
    matrix = np.asarray(values, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("constant transition must be square")
    if not _all_positive_zero_imaginary(matrix):
        raise ValueError(
            "exact-zero synthetic transition requires +0.0 imaginary bits"
        )
    real = matrix.real
    if not np.isin(real, np.asarray((-1.0, 0.0, 1.0))).all():
        raise ValueError(
            "exact-zero synthetic transition is not a signed permutation"
        )
    if not np.all(np.count_nonzero(real, axis=0) == 1):
        raise ValueError("signed permutation columns are not one-hot")
    if not np.all(np.count_nonzero(real, axis=1) == 1):
        raise ValueError("signed permutation rows are not one-hot")


def _require_identity_metric(values: np.ndarray, n_state: int) -> None:
    matrix = np.asarray(values, dtype=np.complex128)
    if matrix.shape != (n_state, n_state):
        raise ValueError("constant metric shape mismatch")
    if not _all_positive_zero_imaginary(matrix):
        raise ValueError(
            "exact-zero synthetic metric requires +0.0 imaginary bits"
        )
    if not np.array_equal(matrix.real, np.eye(n_state, dtype=np.float64)):
        raise ValueError("exact-zero synthetic metric must be identity")


def _scalar_gauss_jordan_inverse(values: np.ndarray) -> np.ndarray:
    """Fixed-order scalar Gauss–Jordan with deterministic partial pivoting."""

    matrix = np.asarray(values, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Gauss-Jordan input must be square")
    if not _all_positive_zero_imaginary(matrix):
        raise ValueError("this scalar candidate lane requires a real matrix")
    n_state = matrix.shape[0]
    left = [
        [float(matrix[row, column].real) for column in range(n_state)]
        for row in range(n_state)
    ]
    right = [
        [1.0 if row == column else +0.0 for column in range(n_state)]
        for row in range(n_state)
    ]
    for column in range(n_state):
        pivot_row = max(
            range(column, n_state),
            key=lambda row: (abs(left[row][column]), -row),
        )
        pivot = left[pivot_row][column]
        if pivot == 0.0:
            raise ValueError("transition candidate is singular")
        if pivot_row != column:
            left[column], left[pivot_row] = left[pivot_row], left[column]
            right[column], right[pivot_row] = (
                right[pivot_row],
                right[column],
            )
        pivot = left[column][column]
        for index in range(n_state):
            left[column][index] = left[column][index] / pivot
            right[column][index] = right[column][index] / pivot
        for row in range(n_state):
            if row == column:
                continue
            factor = left[row][column]
            for index in range(n_state):
                left[row][index] = (
                    left[row][index] - factor * left[column][index]
                )
                right[row][index] = (
                    right[row][index] - factor * right[column][index]
                )
    result = np.zeros((n_state, n_state), dtype=np.complex128)
    for row in range(n_state):
        for column in range(n_state):
            result[row, column] = complex(right[row][column], +0.0)
    return result


def _scalar_hermitian_cholesky(values: np.ndarray) -> np.ndarray:
    """Fixed-order scalar Cholesky for the closed exact identity lane."""

    matrix = np.asarray(values, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Cholesky input must be square")
    n_state = matrix.shape[0]
    _require_identity_metric(matrix, n_state)
    result = np.zeros((n_state, n_state), dtype=np.complex128)
    for row in range(n_state):
        for column in range(row + 1):
            accumulated = +0.0
            for inner in range(column):
                accumulated = (
                    accumulated
                    + float(result[row, inner].real)
                    * float(result[column, inner].real)
                )
            remainder = float(matrix[row, column].real) - accumulated
            if row == column:
                # The closed synthetic lane has an exact unit pivot, so no
                # libm square root or platform-dependent Cholesky is needed.
                if remainder != 1.0:
                    raise ValueError("identity Cholesky pivot is not exact one")
                result[row, column] = complex(1.0, +0.0)
            else:
                denominator = float(result[column, column].real)
                if denominator == 0.0:
                    raise ValueError("Cholesky diagonal is singular")
                result[row, column] = complex(
                    remainder / denominator,
                    +0.0,
                )
    return result


def _scalar_lower_triangular_inverse(values: np.ndarray) -> np.ndarray:
    """Invert a lower-triangular matrix by ordered forward substitution."""

    matrix = np.asarray(values, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("triangular inverse input must be square")
    if not _all_positive_zero_imaginary(matrix):
        raise ValueError("this triangular candidate lane requires real input")
    n_state = matrix.shape[0]
    result = np.zeros((n_state, n_state), dtype=np.complex128)
    for column in range(n_state):
        for row in range(n_state):
            if row < column:
                continue
            accumulated = +0.0
            for inner in range(row):
                accumulated = (
                    accumulated
                    + float(matrix[row, inner].real)
                    * float(result[inner, column].real)
                )
            target = 1.0 if row == column else +0.0
            diagonal = float(matrix[row, row].real)
            if diagonal == 0.0:
                raise ValueError("triangular inverse diagonal is singular")
            result[row, column] = complex(
                (target - accumulated) / diagonal,
                +0.0,
            )
    return result


def _spectral_hard_mul(left: float, right: float, field: str) -> float:
    first = require_hard_scalar(left, f"{field}.left")
    second = require_hard_scalar(right, f"{field}.right")
    return require_hard_scalar(first * second, field)


def _spectral_hard_add(left: float, right: float, field: str) -> float:
    first = require_hard_scalar(left, f"{field}.left")
    second = require_hard_scalar(right, f"{field}.right")
    return require_hard_scalar(first + second, field)


def _spectral_hard_sub(left: float, right: float, field: str) -> float:
    first = require_hard_scalar(left, f"{field}.left")
    second = require_hard_scalar(right, f"{field}.right")
    return require_hard_scalar(first - second, field)


def _spectral_ordered_complex_multiply(
    left: complex,
    right: complex,
) -> complex:
    left_real = require_hard_scalar(left.real, "multiply.left.real")
    left_imag = require_hard_scalar(left.imag, "multiply.left.imag")
    right_real = require_hard_scalar(right.real, "multiply.right.real")
    right_imag = require_hard_scalar(right.imag, "multiply.right.imag")
    real_first = _spectral_hard_mul(
        left_real,
        right_real,
        "multiply.real.first",
    )
    real_second = _spectral_hard_mul(
        left_imag,
        right_imag,
        "multiply.real.second",
    )
    imaginary_first = _spectral_hard_mul(
        left_real,
        right_imag,
        "multiply.imaginary.first",
    )
    imaginary_second = _spectral_hard_mul(
        left_imag,
        right_real,
        "multiply.imaginary.second",
    )
    return complex(
        _spectral_hard_sub(
            real_first,
            real_second,
            "multiply.real.subtract",
        ),
        _spectral_hard_add(
            imaginary_first,
            imaginary_second,
            "multiply.imaginary.add",
        ),
    )


def _spectral_ordered_complex_add(
    left: complex,
    right: complex,
) -> complex:
    return complex(
        _spectral_hard_add(left.real, right.real, "dot.real.add"),
        _spectral_hard_add(
            left.imag,
            right.imag,
            "dot.imaginary.add",
        ),
    )


def _spectral_ordered_complex_dot_values(
    left: tuple[complex, ...],
    right: tuple[complex, ...],
) -> tuple[complex, float, float]:
    """Execute q=4n-1 centers and directed real/imaginary abs sums."""

    if type(left) is not tuple or type(right) is not tuple:
        raise TypeError("dot operands must be tuples")
    if not left or len(left) != len(right):
        raise ValueError("dot operands must have equal positive length")
    center: complex | None = None
    real_absolute_sum = +0.0
    imaginary_absolute_sum = +0.0
    for left_value, right_value in zip(left, right):
        term = _spectral_ordered_complex_multiply(
            left_value,
            right_value,
        )
        center = (
            term
            if center is None
            else _spectral_ordered_complex_add(center, term)
        )
        factors = (
            ("real", abs(left_value.real), abs(right_value.real)),
            ("real", abs(left_value.imag), abs(right_value.imag)),
            ("imaginary", abs(left_value.real), abs(right_value.imag)),
            ("imaginary", abs(left_value.imag), abs(right_value.real)),
        )
        for component, first, second in factors:
            product = directed_mul_upper(first, second)
            if component == "real":
                real_absolute_sum = directed_add_upper(
                    real_absolute_sum,
                    product,
                )
            else:
                imaginary_absolute_sum = directed_add_upper(
                    imaginary_absolute_sum,
                    product,
                )
    if center is None:
        raise AssertionError("non-empty dot did not produce a center")
    return center, real_absolute_sum, imaginary_absolute_sum


def _require_scalar_product_identity(
    left: np.ndarray,
    right: np.ndarray,
    field: str,
) -> None:
    first = np.asarray(left, dtype=np.complex128)
    second = np.asarray(right, dtype=np.complex128)
    if (
        first.ndim != 2
        or second.ndim != 2
        or first.shape[0] != first.shape[1]
        or second.shape != first.shape
    ):
        raise ValueError(f"{field} matrix shapes do not match")
    n_state = first.shape[0]
    for row in range(n_state):
        for column in range(n_state):
            center, _, _ = _spectral_ordered_complex_dot_values(
                tuple(
                    complex(first[row, inner])
                    for inner in range(n_state)
                ),
                tuple(
                    complex(second[inner, column])
                    for inner in range(n_state)
                ),
            )
            expected = 1.0 if row == column else 0.0
            if center.real != expected or center.imag != 0.0:
                raise ValueError(f"{field} candidate product is not identity")


def _matrix_product_subtraction_roundoff_upper(
    left: np.ndarray,
    right: np.ndarray,
) -> float:
    """Bound ordered complex matmul plus subtraction from an exact target."""

    first = np.asarray(left, dtype=np.complex128)
    second = np.asarray(right, dtype=np.complex128)
    if (
        first.ndim != 2
        or second.ndim != 2
        or first.shape[1] != second.shape[0]
    ):
        raise ValueError("matrix product roundoff shapes do not align")
    dot_length = first.shape[1]
    subtraction_additive = Fraction(*MINIMUM_NORMAL.as_integer_ratio())
    sum_squares = Fraction(0)
    for row in range(first.shape[0]):
        for column in range(second.shape[1]):
            _, real_product_sum, imaginary_product_sum = (
                _spectral_ordered_complex_dot_values(
                    tuple(
                        complex(first[row, inner])
                        for inner in range(dot_length)
                    ),
                    tuple(
                        complex(second[inner, column])
                        for inner in range(dot_length)
                    ),
                )
            )
            real_bound = build_complex_dot_roundoff_bound(
                length=dot_length,
                absolute_product_sum=real_product_sum,
            ).roundoff_upper
            imaginary_bound = build_complex_dot_roundoff_bound(
                length=dot_length,
                absolute_product_sum=imaginary_product_sum,
            ).roundoff_upper
            real_fraction = (
                Fraction(*real_bound.as_integer_ratio())
                + subtraction_additive
            )
            imaginary_fraction = (
                Fraction(*imaginary_bound.as_integer_ratio())
                + subtraction_additive
            )
            sum_squares += (
                real_fraction * real_fraction
                + imaginary_fraction * imaginary_fraction
            )
    return frobenius_sqrt_upper(sum_squares)


def _build_unavailable_sidecar(
    *,
    grid: DynamicsKGridManifest,
    values: dict[str, float],
) -> SpectralPointEnclosureColumnarSidecar:
    columns = {
        name: _encode_f64_column((values[name],))
        for name in HARD_COLUMN_NAMES
    }
    provisional = SpectralPointEnclosureColumnarSidecar(
        sidecar_schema_version=SPECTRAL_SIDECAR_SCHEMA_VERSION,
        qualification_grid_sha=grid.dynamics_grid_sha,
        point_count=1,
        candidate_algorithm_id=CANDIDATE_ALGORITHM_ID,
        encoding_id=COLUMN_ENCODING_ID,
        raw_diagnostic_status="unavailable-v1",
        raw_diagnostic_unavailable_reason=(
            "not-required-exact-offset-zero-v1"
        ),
        raw_m_sigma_min_b64=None,
        raw_m_sigma_max_b64=None,
        raw_g_lambda_min_b64=None,
        raw_g_lambda_max_b64=None,
        **columns,
        raw_byte_count=SPECTRAL_HARD_COLUMN_COUNT * 8,
        column_data_sha="0" * 64,
        roundoff_enclosure_method_id=ROUNDING_METHOD_ID,
        sidecar_sha="0" * 64,
    )
    with_column_sha = replace(
        provisional,
        column_data_sha=canonical_sha(_column_data_payload(provisional)),
    )
    result = replace(
        with_column_sha,
        sidecar_sha=canonical_sha(
            spectral_point_sidecar_payload(with_column_sha)
        ),
    )
    return _verify_sidecar(result)


def _constant_transition_matrix(
    transition: VerifiedTransition,
) -> tuple[np.ndarray, int]:
    transition_view = _reverify_verified_transition(transition)
    raw = transition_view.transition
    zero = (0,) * len(raw.spatial_shape)
    if raw.support_offsets != (zero,):
        raise ValueError(
            "this coverage slice requires exact zero transition support"
        )
    kernel = frozen_tensor_array(raw.kernel)
    matrix = kernel[
        (slice(None), slice(None)) + (0,) * len(raw.spatial_shape)
    ].copy()
    return matrix, len(raw.channel_order)


def _constant_metric_matrix(
    witness: StabilityMetricWitness,
    ndim: int,
) -> np.ndarray:
    if witness.metric_support_offsets != ((0,) * ndim,):
        raise ValueError(
            "this coverage slice requires exact zero metric support"
        )
    values = frozen_tensor_array(witness.metric_kernel)
    if values.shape[0] != 1:
        raise ValueError("constant metric kernel must have one coefficient")
    return values[0].copy()


def _expected_exact_zero_coverage(
    transition: VerifiedTransition,
    stability_metric: StabilityMetricWitness,
    fp64_protocol: Fp64EnclosureProtocol,
) -> SpectralMarginCoverage:
    transition_view = _reverify_verified_transition(transition)
    structure = build_structure_manifest(
        transition_view.factory,
        transition_view.prestructure,
    )
    metric = verify_stability_metric_witness(
        stability_metric,
        transition_view.factory,
        transition_view.prestructure,
        structure,
    )
    protocol = verify_fp64_enclosure_protocol(fp64_protocol)
    raw_transition = transition_view.transition
    grid = build_dynamics_grid_manifest(
        raw_transition.support_offsets,
        metric.metric_support_offsets,
    )
    verify_dynamics_grid_manifest(
        grid,
        raw_transition.support_offsets,
        metric.metric_support_offsets,
    )
    if grid.qualification_profile != "exact-offset-zero-v1":
        raise ValueError("this builder only accepts exact-zero singleton grids")
    if grid.reciprocal_indices != ((0,) * grid.spatial_ndim,):
        raise ValueError("exact-zero grid is not the unique origin singleton")
    n_state = len(raw_transition.channel_order)
    _preflight_spectral_resources(
        point_count=1,
        n_state=n_state,
        encoded_column_count=SPECTRAL_HARD_COLUMN_COUNT,
    )

    transition_matrix, measured_state = _constant_transition_matrix(
        transition
    )
    if measured_state != n_state:
        raise ValueError("transition state dimension changed during replay")
    metric_matrix = _constant_metric_matrix(metric, grid.spatial_ndim)
    _require_signed_permutation(transition_matrix)
    _require_identity_metric(metric_matrix, n_state)

    inverse = _scalar_gauss_jordan_inverse(transition_matrix)
    cholesky = _scalar_hermitian_cholesky(metric_matrix)
    cholesky_inverse = _scalar_lower_triangular_inverse(cholesky)
    _require_scalar_product_identity(
        inverse,
        transition_matrix,
        "transition inverse",
    )
    _require_scalar_product_identity(
        cholesky,
        cholesky.conj().T,
        "metric Cholesky",
    )
    _require_scalar_product_identity(
        cholesky_inverse,
        cholesky,
        "Cholesky inverse",
    )
    inverse_residual = _matrix_product_subtraction_roundoff_upper(
        inverse,
        transition_matrix,
    )
    cholesky_residual = _matrix_product_subtraction_roundoff_upper(
        cholesky,
        cholesky.conj().T,
    )
    cholesky_inverse_residual = (
        _matrix_product_subtraction_roundoff_upper(
            cholesky_inverse,
            cholesky,
        )
    )
    frobenius = frobenius_sqrt_upper(Fraction(n_state, 1))
    zero = +0.0
    one_minus_error = directed_sub_lower(1.0, inverse_residual)
    m_sigma_min = directed_div_lower(one_minus_error, frobenius)
    m_sigma_max = directed_add_upper(frobenius, zero)
    if cholesky_inverse_residual >= 1.0:
        raise ValueError(
            "Cholesky inverse residual must be below one"
        )
    ell = directed_div_lower(
        directed_sub_lower(1.0, cholesky_inverse_residual),
        frobenius,
    )
    if ell <= 0.0:
        raise ValueError("Cholesky inverse lower must be positive")
    g_lambda_min = directed_sub_lower(
        directed_mul_lower(ell, ell),
        cholesky_residual,
    )
    g_lambda_max = directed_add_upper(frobenius, zero)
    if m_sigma_min <= 0.0 or g_lambda_min <= 0.0:
        raise ValueError("exact-zero hard lower bound is not positive")
    m_condition = directed_div_upper(m_sigma_max, m_sigma_min)
    g_condition = directed_div_upper(g_lambda_max, g_lambda_min)

    point_values = {
        "transition_symbol_error_upper_b64": zero,
        "metric_symbol_error_upper_b64": zero,
        "transition_frobenius_upper_b64": frobenius,
        "inverse_frobenius_upper_b64": frobenius,
        "inverse_residual_frobenius_upper_b64": inverse_residual,
        "m_sigma_min_lower_b64": m_sigma_min,
        "m_sigma_max_upper_b64": m_sigma_max,
        "metric_frobenius_upper_b64": frobenius,
        "cholesky_factorization_residual_frobenius_upper_b64": (
            cholesky_residual
        ),
        "cholesky_inverse_frobenius_upper_b64": frobenius,
        "cholesky_inverse_residual_frobenius_upper_b64": (
            cholesky_inverse_residual
        ),
        "ell_lower_b64": ell,
        "g_lambda_min_lower_b64": g_lambda_min,
        "g_lambda_max_upper_b64": g_lambda_max,
    }
    sidecar = _build_unavailable_sidecar(grid=grid, values=point_values)
    table = protocol.root_interval_table
    fill = _fraction_upper_float(
        Fraction(
            table.pi_upper_numerator,
            1 << table.dyadic_exponent,
        ),
        "fill_distance",
    )
    derivative_zero = (+0.0,) * grid.spatial_ndim
    provisional = SpectralMarginCoverage(
        coverage_schema_version=SPECTRAL_COVERAGE_SCHEMA_VERSION,
        transition_sha=raw_transition.transition_sha,
        stability_metric_witness_sha=metric.witness_sha,
        fp64_enclosure_protocol=protocol,
        qualification_grid=grid,
        spectral_diagnostic_grid=grid,
        torus_domain_id=TORUS_DOMAIN_ID,
        distance_convention_id=DISTANCE_CONVENTION_ID,
        fill_distance=fill,
        raw_diagnostic_status="unavailable-v1",
        raw_diagnostic_unavailable_reason=(
            "not-required-exact-offset-zero-v1"
        ),
        raw_m_sigma_min=None,
        raw_m_sigma_max=None,
        raw_g_lambda_min=None,
        raw_g_lambda_max=None,
        point_enclosures=sidecar,
        grid_m_sigma_min_lower=(m_sigma_min,),
        grid_m_sigma_max_upper=(m_sigma_max,),
        grid_g_lambda_min_lower=(g_lambda_min,),
        grid_g_lambda_max_upper=(g_lambda_max,),
        m_sigma_min_axis_derivative_bounds=derivative_zero,
        m_sigma_max_axis_derivative_bounds=derivative_zero,
        g_lambda_min_axis_derivative_bounds=derivative_zero,
        g_lambda_max_axis_derivative_bounds=derivative_zero,
        m_sigma_min_coverage_increment=+0.0,
        m_sigma_max_coverage_increment=+0.0,
        g_lambda_min_coverage_increment=+0.0,
        g_lambda_max_coverage_increment=+0.0,
        covered_m_sigma_min_lower=m_sigma_min,
        covered_m_sigma_max_upper=m_sigma_max,
        covered_g_lambda_min_lower=g_lambda_min,
        covered_g_lambda_max_upper=g_lambda_max,
        covered_m_condition_number_upper=m_condition,
        covered_g_condition_number_upper=g_condition,
        spectral_radius_drift_diagnostic=None,
        coverage_sha="0" * 64,
    )
    result = replace(
        provisional,
        coverage_sha=canonical_sha(
            spectral_margin_coverage_payload(provisional)
        ),
    )
    _require_coverage_body_within_cap(result)
    if result.covered_m_sigma_min_lower < SPECTRAL_M_SIGMA_MIN_GATE:
        raise ValueError("covered transition singular lower is unresolved")
    if result.covered_m_condition_number_upper > SPECTRAL_CONDITION_MAX:
        raise ValueError("covered transition condition upper is unresolved")
    if result.covered_g_lambda_min_lower < SPECTRAL_G_LAMBDA_MIN_GATE:
        raise ValueError("covered metric eigenvalue lower is unresolved")
    if result.covered_g_condition_number_upper > SPECTRAL_CONDITION_MAX:
        raise ValueError("covered metric condition upper is unresolved")
    return result


def build_exact_zero_spectral_margin_coverage(
    transition: VerifiedTransition,
    stability_metric: StabilityMetricWitness,
    fp64_protocol: Fp64EnclosureProtocol,
) -> SpectralMarginCoverage:
    """Build the complete exact-zero singleton coverage body.

    There is intentionally no Laurent residual argument: coverage proves only
    the four large-margin spectral quantities.
    """

    return _expected_exact_zero_coverage(
        transition,
        stability_metric,
        fp64_protocol,
    )


def verify_spectral_margin_coverage(
    coverage: SpectralMarginCoverage,
    transition: VerifiedTransition,
    stability_metric: StabilityMetricWitness,
) -> SpectralMarginCoverage:
    """Reconstruct exact-zero coverage from the live transition and metric."""

    if type(coverage) is not SpectralMarginCoverage:
        raise TypeError("coverage must be a SpectralMarginCoverage")
    _preflight_exact_zero_coverage_record(coverage, transition)
    _require_coverage_body_within_cap(coverage)
    if coverage.coverage_schema_version != SPECTRAL_COVERAGE_SCHEMA_VERSION:
        raise ValueError("unexpected spectral coverage schema")
    transition_view = _reverify_verified_transition(transition)
    structure = build_structure_manifest(
        transition_view.factory,
        transition_view.prestructure,
    )
    metric = verify_stability_metric_witness(
        stability_metric,
        transition_view.factory,
        transition_view.prestructure,
        structure,
    )
    for grid in (
        coverage.qualification_grid,
        coverage.spectral_diagnostic_grid,
    ):
        verify_dynamics_grid_manifest(
            grid,
            transition_view.transition.support_offsets,
            metric.metric_support_offsets,
        )
    verify_fp64_enclosure_protocol(coverage.fp64_enclosure_protocol)
    _verify_sidecar(coverage.point_enclosures)
    if coverage.coverage_sha != canonical_sha(
        spectral_margin_coverage_payload(coverage)
    ):
        raise ValueError("coverage_sha does not match complete body")
    expected = _expected_exact_zero_coverage(
        transition,
        metric,
        coverage.fp64_enclosure_protocol,
    )
    if coverage.coverage_sha != expected.coverage_sha:
        raise ValueError("spectral coverage does not match reconstruction")
    return coverage


@dataclass(frozen=True)
class NormalizedMetricResidualAudit:
    audit_schema_version: str
    metric_residual_sha: str
    spectral_margin_coverage_sha: str
    raw_metric_residual_upper: float
    covered_g_lambda_min_lower: float
    division_method_id: Literal[
        "fp64-nextafter-outward-division-v1"
    ]
    normalized_metric_residual_upper: float
    audit_sha: str

    def __post_init__(self) -> None:
        _text(self.audit_schema_version, "audit_schema_version")
        _sha(self.metric_residual_sha, "metric_residual_sha")
        _sha(
            self.spectral_margin_coverage_sha,
            "spectral_margin_coverage_sha",
        )
        _nonnegative_float(
            self.raw_metric_residual_upper,
            "raw_metric_residual_upper",
        )
        _positive_float(
            self.covered_g_lambda_min_lower,
            "covered_g_lambda_min_lower",
        )
        if self.division_method_id != DIVISION_METHOD_ID:
            raise ValueError("division method is not frozen")
        _nonnegative_float(
            self.normalized_metric_residual_upper,
            "normalized_metric_residual_upper",
        )
        _sha(self.audit_sha, "audit_sha")


def normalized_metric_residual_audit_payload(
    audit: NormalizedMetricResidualAudit,
) -> dict[str, object]:
    if not isinstance(audit, NormalizedMetricResidualAudit):
        raise TypeError(
            "audit must be a NormalizedMetricResidualAudit"
        )
    return {
        "audit_schema_version": audit.audit_schema_version,
        "metric_residual_sha": audit.metric_residual_sha,
        "spectral_margin_coverage_sha": (
            audit.spectral_margin_coverage_sha
        ),
        "raw_metric_residual_upper": audit.raw_metric_residual_upper,
        "covered_g_lambda_min_lower": (
            audit.covered_g_lambda_min_lower
        ),
        "division_method_id": audit.division_method_id,
        "normalized_metric_residual_upper": (
            audit.normalized_metric_residual_upper
        ),
    }


def _expected_normalized_audit(
    metric_residual: LaurentResidualCertificate,
    spectral_margins: SpectralMarginCoverage,
    transition: VerifiedTransition,
    stability_metric: StabilityMetricWitness,
) -> NormalizedMetricResidualAudit:
    transition_view = _reverify_verified_transition(transition)
    structure = build_structure_manifest(
        transition_view.factory,
        transition_view.prestructure,
    )
    metric = verify_stability_metric_witness(
        stability_metric,
        transition_view.factory,
        transition_view.prestructure,
        structure,
    )
    coverage = verify_spectral_margin_coverage(
        spectral_margins,
        transition,
        metric,
    )
    residual = verify_laurent_residual_certificate(
        metric_residual,
        transition,
        structure,
        metric,
        coverage.fp64_enclosure_protocol,
    )
    if residual.residual_kind != "stability-metric":
        raise ValueError(
            "normalized audit requires the metric Laurent residual"
        )
    if (
        residual.fp64_enclosure_protocol_sha
        != coverage.fp64_enclosure_protocol.protocol_sha
    ):
        raise ValueError("residual and coverage fp64 protocols differ")
    raw_upper = residual.raw_global_momentum_supremum_bound
    denominator = coverage.covered_g_lambda_min_lower
    normalized = directed_div_upper(raw_upper, denominator)
    if normalized > NORMALIZED_METRIC_RESIDUAL_GATE:
        raise ValueError(
            "normalized metric residual exceeds the 1e-12 hard gate"
        )
    provisional = NormalizedMetricResidualAudit(
        audit_schema_version=NORMALIZED_AUDIT_SCHEMA_VERSION,
        metric_residual_sha=residual.residual_sha,
        spectral_margin_coverage_sha=coverage.coverage_sha,
        raw_metric_residual_upper=raw_upper,
        covered_g_lambda_min_lower=denominator,
        division_method_id=DIVISION_METHOD_ID,
        normalized_metric_residual_upper=normalized,
        audit_sha="0" * 64,
    )
    return replace(
        provisional,
        audit_sha=canonical_sha(
            normalized_metric_residual_audit_payload(provisional)
        ),
    )


class VerifiedNormalizedMetricResidualAudit:
    """Opaque live capability backed by complete residual and coverage bodies."""

    __slots__ = ("__audit", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        audit: NormalizedMetricResidualAudit,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError(
                "VerifiedNormalizedMetricResidualAudit is module-issued"
            )
        object.__setattr__(
            self,
            "_VerifiedNormalizedMetricResidualAudit__audit",
            audit,
        )
        object.__setattr__(
            self,
            "_VerifiedNormalizedMetricResidualAudit__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedNormalizedMetricResidualAudit__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError(
            "VerifiedNormalizedMetricResidualAudit is immutable"
        )

    @property
    def audit(self) -> NormalizedMetricResidualAudit:
        return self.__audit


@dataclass(frozen=True)
class _NormalizedAuthority:
    audit: NormalizedMetricResidualAudit
    metric_residual: LaurentResidualCertificate
    coverage: SpectralMarginCoverage
    transition: VerifiedTransition
    stability_metric: StabilityMetricWitness
    seal: str


def _normalized_seal(
    audit: NormalizedMetricResidualAudit,
    metric_residual: LaurentResidualCertificate,
    coverage: SpectralMarginCoverage,
    transition: VerifiedTransition,
    stability_metric: StabilityMetricWitness,
) -> str:
    transition_view = _reverify_verified_transition(transition)
    return canonical_sha(
        {
            "verified_normalized_schema_version": (
                "v3m0.verified-normalized-metric-residual.v1"
            ),
            "audit": {
                **normalized_metric_residual_audit_payload(audit),
                "audit_sha": audit.audit_sha,
            },
            "metric_residual": _residual_record(metric_residual),
            "spectral_margins": {
                **spectral_margin_coverage_payload(coverage),
                "coverage_sha": coverage.coverage_sha,
            },
            "transition": {
                **measured_transition_payload(
                    transition_view.transition
                ),
                "transition_sha": (
                    transition_view.transition.transition_sha
                ),
            },
            "stability_metric": _metric_record(stability_metric),
        }
    )


def _make_normalized_authority() -> tuple[
    Callable[..., VerifiedNormalizedMetricResidualAudit],
    Callable[
        [VerifiedNormalizedMetricResidualAudit],
        _NormalizedAuthority,
    ],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedNormalizedMetricResidualAudit],
            _NormalizedAuthority,
        ],
    ] = {}
    lock = threading.RLock()

    def issue(
        audit: NormalizedMetricResidualAudit,
        metric_residual: LaurentResidualCertificate,
        coverage: SpectralMarginCoverage,
        transition: VerifiedTransition,
        stability_metric: StabilityMetricWitness,
    ) -> VerifiedNormalizedMetricResidualAudit:
        expected = _expected_normalized_audit(
            metric_residual,
            coverage,
            transition,
            stability_metric,
        )
        if type(audit) is not NormalizedMetricResidualAudit:
            raise TypeError("audit must be a NormalizedMetricResidualAudit")
        _require_exact_record_fields(
            audit,
            NormalizedMetricResidualAudit,
            "normalized audit",
        )
        audit.__post_init__()
        if audit.audit_sha != canonical_sha(
            normalized_metric_residual_audit_payload(audit)
        ):
            raise ValueError("audit_sha does not match complete body")
        if audit != expected:
            raise ValueError(
                "normalized audit does not match complete reconstruction"
            )
        authority_audit = replace(expected)
        exposed_audit = replace(expected)
        seal = _normalized_seal(
            authority_audit,
            metric_residual,
            coverage,
            transition,
            stability_metric,
        )
        authority = _NormalizedAuthority(
            audit=authority_audit,
            metric_residual=metric_residual,
            coverage=coverage,
            transition=transition,
            stability_metric=stability_metric,
            seal=seal,
        )
        wrapper = VerifiedNormalizedMetricResidualAudit(
            _ISSUANCE_TOKEN,
            exposed_audit,
            seal,
        )
        identity = id(wrapper)

        def remove(
            reference: weakref.ReferenceType[
                VerifiedNormalizedMetricResidualAudit
            ],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        return wrapper

    def reverify(
        wrapper: VerifiedNormalizedMetricResidualAudit,
    ) -> _NormalizedAuthority:
        if type(wrapper) is not VerifiedNormalizedMetricResidualAudit:
            raise TypeError(
                "power audit requires a module-issued normalized capability"
            )
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError(
                    "normalized metric residual identity is not live"
                )
            authority = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedNormalizedMetricResidualAudit__token",
            )
            audit = object.__getattribute__(
                wrapper,
                "_VerifiedNormalizedMetricResidualAudit__audit",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedNormalizedMetricResidualAudit__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "normalized metric residual authority is incomplete"
            ) from exc
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("normalized metric residual token mismatch")
        _require_exact_record_fields(
            audit,
            NormalizedMetricResidualAudit,
            "normalized audit",
        )
        audit.__post_init__()
        if audit.audit_sha != canonical_sha(
            normalized_metric_residual_audit_payload(audit)
        ):
            raise ValueError("normalized audit body changed after issuance")
        expected = _expected_normalized_audit(
            authority.metric_residual,
            authority.coverage,
            authority.transition,
            authority.stability_metric,
        )
        expected_seal = _normalized_seal(
            expected,
            authority.metric_residual,
            authority.coverage,
            authority.transition,
            authority.stability_metric,
        )
        if (
            audit != authority.audit
            or authority.audit != expected
            or seal != authority.seal
            or seal != expected_seal
        ):
            raise ValueError(
                "normalized metric residual immutable seal mismatch"
            )
        return authority

    return issue, reverify


(
    _issue_verified_normalized_audit,
    _reverify_verified_normalized_audit,
) = _make_normalized_authority()


def certify_normalized_metric_residual_audit(
    metric_residual: LaurentResidualCertificate,
    spectral_margins: SpectralMarginCoverage,
    transition: VerifiedTransition,
    stability_metric: StabilityMetricWitness,
) -> VerifiedNormalizedMetricResidualAudit:
    """Verify both full source bodies, then issue the normalized capability."""

    audit = _expected_normalized_audit(
        metric_residual,
        spectral_margins,
        transition,
        stability_metric,
    )
    return _issue_verified_normalized_audit(
        audit,
        metric_residual,
        spectral_margins,
        transition,
        stability_metric,
    )


def verify_normalized_metric_residual_audit(
    audit: NormalizedMetricResidualAudit,
    metric_residual: LaurentResidualCertificate,
    spectral_margins: SpectralMarginCoverage,
    transition: VerifiedTransition,
    stability_metric: StabilityMetricWitness,
) -> VerifiedNormalizedMetricResidualAudit:
    """Hydrate a raw normalized audit only after complete reconstruction."""

    if type(audit) is not NormalizedMetricResidualAudit:
        raise TypeError("audit must be a NormalizedMetricResidualAudit")
    _require_exact_record_fields(
        audit,
        NormalizedMetricResidualAudit,
        "normalized audit",
    )
    audit.__post_init__()
    if audit.audit_schema_version != NORMALIZED_AUDIT_SCHEMA_VERSION:
        raise ValueError("unexpected normalized audit schema")
    if audit.audit_sha != canonical_sha(
        normalized_metric_residual_audit_payload(audit)
    ):
        raise ValueError("audit_sha does not match complete body")
    expected = _expected_normalized_audit(
        metric_residual,
        spectral_margins,
        transition,
        stability_metric,
    )
    if audit.audit_sha != expected.audit_sha:
        raise ValueError(
            "normalized audit does not match complete source bodies"
        )
    return _issue_verified_normalized_audit(
        audit,
        metric_residual,
        spectral_margins,
        transition,
        stability_metric,
    )


@dataclass(frozen=True)
class PowerDriftAudit:
    audit_schema_version: str
    normalized_metric_residual_audit_sha: str
    macro_step: Literal[16384]
    nonzero_delta_squaring_count: Literal[14]
    executed_squaring_count: Literal[0, 14]
    identity_branch: bool
    method_id: Literal["t16384-directed-repeated-squaring-v1"]
    delta_upper: float
    one_minus_delta_lower: float
    one_plus_delta_upper: float
    growth_upper: float
    contraction_upper: float
    drift_upper: float
    audit_sha: str

    def __post_init__(self) -> None:
        _text(self.audit_schema_version, "audit_schema_version")
        _sha(
            self.normalized_metric_residual_audit_sha,
            "normalized_metric_residual_audit_sha",
        )
        if (
            _wire_int(self.macro_step, "macro_step")
            != POWER_DRIFT_MACRO_STEP
        ):
            raise ValueError("macro_step is not frozen")
        if (
            _wire_int(
                self.nonzero_delta_squaring_count,
                "nonzero_delta_squaring_count",
            )
            != POWER_DRIFT_SQUARING_COUNT
        ):
            raise ValueError("nonzero squaring count is not frozen")
        executed = _wire_int(
            self.executed_squaring_count,
            "executed_squaring_count",
        )
        if executed not in (0, POWER_DRIFT_SQUARING_COUNT):
            raise ValueError("executed squaring count is not closed")
        if type(self.identity_branch) is not bool:
            raise TypeError("identity_branch must be a bool")
        if self.method_id != POWER_DRIFT_METHOD_ID:
            raise ValueError("power drift method is not frozen")
        delta = _nonnegative_float(self.delta_upper, "delta_upper")
        for field in (
            "one_minus_delta_lower",
            "one_plus_delta_upper",
            "growth_upper",
            "contraction_upper",
            "drift_upper",
        ):
            _nonnegative_float(getattr(self, field), field)
        if self.identity_branch:
            if executed != 0:
                raise ValueError("identity branch must execute zero squarings")
            for field in (
                "delta_upper",
                "growth_upper",
                "contraction_upper",
                "drift_upper",
            ):
                require_semantic_zero(getattr(self, field), field)
            if (
                self.one_minus_delta_lower != 1.0
                or self.one_plus_delta_upper != 1.0
            ):
                raise ValueError("identity branch one±delta must equal one")
        else:
            if delta <= 0.0 or executed != POWER_DRIFT_SQUARING_COUNT:
                raise ValueError(
                    "nonzero branch requires positive delta and 14 squarings"
                )
        _sha(self.audit_sha, "audit_sha")


def power_drift_audit_payload(
    audit: PowerDriftAudit,
) -> dict[str, object]:
    if not isinstance(audit, PowerDriftAudit):
        raise TypeError("audit must be a PowerDriftAudit")
    return {
        "audit_schema_version": audit.audit_schema_version,
        "normalized_metric_residual_audit_sha": (
            audit.normalized_metric_residual_audit_sha
        ),
        "macro_step": audit.macro_step,
        "nonzero_delta_squaring_count": (
            audit.nonzero_delta_squaring_count
        ),
        "executed_squaring_count": audit.executed_squaring_count,
        "identity_branch": audit.identity_branch,
        "method_id": audit.method_id,
        "delta_upper": audit.delta_upper,
        "one_minus_delta_lower": audit.one_minus_delta_lower,
        "one_plus_delta_upper": audit.one_plus_delta_upper,
        "growth_upper": audit.growth_upper,
        "contraction_upper": audit.contraction_upper,
        "drift_upper": audit.drift_upper,
    }


def _expected_power_drift_audit(
    normalized: VerifiedNormalizedMetricResidualAudit,
) -> PowerDriftAudit:
    authority = _reverify_verified_normalized_audit(normalized)
    bounds = compute_power_drift_bounds(
        authority.audit.normalized_metric_residual_upper
    )
    provisional = PowerDriftAudit(
        audit_schema_version=POWER_DRIFT_AUDIT_SCHEMA_VERSION,
        normalized_metric_residual_audit_sha=authority.audit.audit_sha,
        macro_step=bounds.macro_step,
        nonzero_delta_squaring_count=(
            bounds.nonzero_delta_squaring_count
        ),
        executed_squaring_count=bounds.executed_squaring_count,
        identity_branch=bounds.identity_branch,
        method_id=bounds.method_id,
        delta_upper=bounds.delta_upper,
        one_minus_delta_lower=bounds.one_minus_delta_lower,
        one_plus_delta_upper=bounds.one_plus_delta_upper,
        growth_upper=bounds.growth_upper,
        contraction_upper=bounds.contraction_upper,
        drift_upper=bounds.drift_upper,
        audit_sha="0" * 64,
    )
    return replace(
        provisional,
        audit_sha=canonical_sha(power_drift_audit_payload(provisional)),
    )


def build_power_drift_audit(
    normalized: VerifiedNormalizedMetricResidualAudit,
) -> PowerDriftAudit:
    """Build power drift only from the live verified normalized authority."""

    return _expected_power_drift_audit(normalized)


def verify_power_drift_audit(
    audit: PowerDriftAudit,
    normalized: VerifiedNormalizedMetricResidualAudit,
) -> PowerDriftAudit:
    """Rebuild all fourteen directed squarings from normalized authority."""

    if type(audit) is not PowerDriftAudit:
        raise TypeError("audit must be a PowerDriftAudit")
    _require_exact_record_fields(
        audit,
        PowerDriftAudit,
        "power drift audit",
    )
    audit.__post_init__()
    if audit.audit_schema_version != POWER_DRIFT_AUDIT_SCHEMA_VERSION:
        raise ValueError("unexpected power drift audit schema")
    if audit.audit_sha != canonical_sha(power_drift_audit_payload(audit)):
        raise ValueError("power drift audit SHA does not match complete body")
    expected = _expected_power_drift_audit(normalized)
    if audit.audit_sha != expected.audit_sha:
        raise ValueError("power drift audit does not match reconstruction")
    return audit


__all__ = [
    "CANDIDATE_ALGORITHM_ID",
    "COLUMN_DATA_SCHEMA_VERSION",
    "COLUMN_ENCODING_ID",
    "DISTANCE_CONVENTION_ID",
    "DIVISION_METHOD_ID",
    "HARD_COLUMN_NAMES",
    "NORMALIZED_AUDIT_SCHEMA_VERSION",
    "NORMALIZED_METRIC_RESIDUAL_GATE",
    "POWER_DRIFT_AUDIT_SCHEMA_VERSION",
    "RAW_COLUMN_NAMES",
    "ROUNDING_METHOD_ID",
    "SPECTRAL_AVAILABLE_COLUMN_COUNT",
    "SPECTRAL_COVERAGE_SCHEMA_VERSION",
    "SPECTRAL_HARD_COLUMN_COUNT",
    "SPECTRAL_SIDECAR_SCHEMA_VERSION",
    "TORUS_DOMAIN_ID",
    "NormalizedMetricResidualAudit",
    "PowerDriftAudit",
    "SpectralMarginCoverage",
    "SpectralPointEnclosureColumnarSidecar",
    "VerifiedNormalizedMetricResidualAudit",
    "build_exact_zero_spectral_margin_coverage",
    "build_power_drift_audit",
    "certify_normalized_metric_residual_audit",
    "normalized_metric_residual_audit_payload",
    "power_drift_audit_payload",
    "spectral_margin_coverage_payload",
    "spectral_point_sidecar_payload",
    "verify_normalized_metric_residual_audit",
    "verify_power_drift_audit",
    "verify_spectral_margin_coverage",
]
