"""Quotient-geometry kernels and the fail-closed Task-14 authority boundary.

The numerical kernel is private: callers cannot supply matrices or thresholds
to the scientific evaluator.  Public evaluation accepts only a live
``VerifiedResponseBlock`` and a live geometry-threshold calibration.  The
current Task-12 response-block schema does not yet carry the frozen kernel,
quotient, metric, and target representatives required by the Task-14 formula,
so authority issuance and public evaluation deliberately fail closed until
those exact upstream fields are frozen.
"""

from __future__ import annotations

import copy
import hashlib
import math
import struct
import threading
import weakref
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

from .blocks import (
    ResponseBlock,
    VerifiedResponseBlock,
    _reverify_verified_response_block,
    response_block_payload,
)
from .calibration_authority import (
    CalibrationApplicationPermit,
    VerifiedCalibrationApplicationPermit,
    _preflight_tree,
    _reverify_verified_calibration_application_permit,
    calibration_application_permit_payload,
)
from .evidence import canonical_sha
from .parent_freeze import (
    ParentFreezeManifest,
    V3M0SyntheticControlApplicationSpec,
    parent_freeze_manifest_payload,
    synthetic_control_application_spec_payload,
)
from .linalg import (
    LINALG_ARITHMETIC_WORK_CAP,
    LINALG_ENTRY_CAP,
    _canonical_columns_work,
    _metric_whitener_work,
    canonical_orthonormal_columns,
    hermitian_positive_whitener,
)


GEOMETRY_HERMITIAN_TOLERANCE = 1e-12
GEOMETRY_COVERAGE_THRESHOLD_INSTANCE_AUDIT_SCHEMA_VERSION = (
    "v3m0.geometry-coverage-threshold-instance-audit.v1"
)
GEOMETRY_COVERAGE_THRESHOLD_CONTROL_EVIDENCE_SCHEMA_VERSION = (
    "v3m0.geometry-coverage-threshold-control-evidence.v1"
)
GEOMETRY_COVERAGE_THRESHOLD_CALIBRATION_SCHEMA_VERSION = (
    "v3m0.geometry-coverage-threshold-calibration.v1"
)
GEOMETRY_THRESHOLD = 0.05
GEOMETRY_AMBIGUITY_HALF_WIDTH = 0.01
COVERAGE_THRESHOLD = 0.5
COVERAGE_AMBIGUITY_HALF_WIDTH = 0.1
GEOMETRY_THRESHOLD_CONTROL_CASE_IDS = (
    "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
    "C16_COVERAGE_025_075",
    "C17_QUOTIENT_GAUGE_COVERAGE",
)
GEOMETRY_AUTHORITY_REQUIRED_TASK12_FIELDS = (
    "kernel_basis",
    "physical_quotient_map",
    "physical_quotient_metric",
    "target_physical_representatives",
)
DEGENERATE_ROTATION_SEEDS = (
    "v3m0-degrot-0",
    "v3m0-degrot-1",
    "v3m0-degrot-2",
)
DEGENERATE_ROTATION_DRIFT_MAX = 1e-12
_ISSUANCE_TOKEN = object()


@dataclass(frozen=True)
class GeometryNumericalThresholds:
    """Numeric view copied from verified response and geometry calibrations."""

    signal_threshold: float
    geometry_threshold: float
    geometry_ambiguity_half_width: float
    coverage_threshold: float
    coverage_ambiguity_half_width: float

    def __post_init__(self) -> None:
        for field in (
            "signal_threshold",
            "geometry_threshold",
            "geometry_ambiguity_half_width",
            "coverage_threshold",
            "coverage_ambiguity_half_width",
        ):
            value = getattr(self, field)
            if type(value) is not float or not math.isfinite(value):
                raise TypeError(f"{field} must be an exact finite float")
        if self.signal_threshold <= 0.0:
            raise ValueError("signal_threshold must be positive")
        for prefix in ("geometry", "coverage"):
            threshold = getattr(self, f"{prefix}_threshold")
            half_width = getattr(self, f"{prefix}_ambiguity_half_width")
            if not 0.0 < threshold < 1.0:
                raise ValueError(f"{prefix}_threshold must lie inside (0,1)")
            if half_width <= 0.0:
                raise ValueError(f"{prefix} ambiguity half-width must be positive")
            if threshold - half_width < 0.0 or threshold + half_width > 1.0:
                raise ValueError(f"{prefix} ambiguity band must lie inside [0,1]")


@dataclass(frozen=True)
class GeometrySpectrum:
    g_spectrum: tuple[float, ...]
    c_spectrum: tuple[float, ...]
    n_response: Optional[int]
    n_curv: int
    max_g: float
    rms_g: float
    frobenius_leakage: float
    delta_geom_dof: Optional[float]
    delta_geom_energy: float
    n_cover: Optional[int]
    coverage_phys: Optional[float]
    rank_deficit: Optional[int]
    geometry_ambiguous: bool
    coverage_ambiguous: bool
    response_orthogonality_residual: float
    k_cover_hermitian_residual: float


@dataclass(frozen=True)
class GeometryRotationRow:
    seed: str
    g_spectrum_drift: float
    c_spectrum_drift: float
    coordinate_drift: Optional[float]
    projector_drift: float
    row_drift_max: Optional[float]


@dataclass(frozen=True)
class GeometryRotationAudit:
    rows: tuple[GeometryRotationRow, ...]
    degenerate_rotation_drift_max: Optional[float]
    passed: bool


def _matrix_header(
    value: object,
    field: str,
    *,
    square: bool = False,
) -> np.ndarray:
    if type(value) is not np.ndarray:
        raise TypeError(f"{field} must be an exact numpy.ndarray")
    if value.ndim != 2 or value.shape[0] <= 0 or value.shape[1] <= 0:
        raise ValueError(f"{field} must be a non-empty matrix")
    if square and value.shape[0] != value.shape[1]:
        raise ValueError(f"{field} must be square")
    if value.shape[0] * value.shape[1] > LINALG_ENTRY_CAP:
        raise ValueError(f"{field} exceeds the matrix resource cap")
    if value.dtype != np.dtype(np.complex128):
        raise TypeError(f"{field} must have complex128 dtype")
    return value


def _materialize_matrix(value: np.ndarray, field: str) -> np.ndarray:
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{field} must be finite")
    return np.array(value, dtype=np.complex128, copy=True, order="C")


def _matrix(
    value: object,
    field: str,
    *,
    square: bool = False,
) -> np.ndarray:
    return _materialize_matrix(
        _matrix_header(value, field, square=square),
        field,
    )


def _geometry_arithmetic_work(
    response: np.ndarray,
    kernel: np.ndarray,
    quotient: np.ndarray,
    metric: np.ndarray,
    targets: np.ndarray,
) -> int:
    response_rank_cap = min(response.shape)
    kernel_rank_cap = min(kernel.shape)
    mapped_response_rank_cap = min(quotient.shape[0], response.shape[1])
    target_rank_cap = min(quotient.shape[0], targets.shape[1])
    return (
        _metric_whitener_work(metric.shape[0])
        + response.shape[0] * response.shape[1] ** 2
        + response.shape[1] ** 3
        + _canonical_columns_work(*kernel.shape)
        + 2 * response.shape[0] * kernel_rank_cap * response.shape[1]
        + response.shape[0] * response.shape[1] * response_rank_cap
        + quotient.shape[0] ** 2 * quotient.shape[1]
        + quotient.shape[0] * quotient.shape[1] * response.shape[1]
        + _canonical_columns_work(
            quotient.shape[0],
            response.shape[1],
        )
        + quotient.shape[0] * quotient.shape[1] * targets.shape[1]
        + _canonical_columns_work(
            quotient.shape[0],
            targets.shape[1],
        )
        + quotient.shape[0] * mapped_response_rank_cap * target_rank_cap
        + mapped_response_rank_cap * target_rank_cap**2
        + 2 * target_rank_cap**3
    )


def _canonical_unit_interval_array(values: np.ndarray, field: str) -> np.ndarray:
    if not bool(np.all(np.isfinite(values))) or bool(
        np.any(values < -GEOMETRY_HERMITIAN_TOLERANCE)
        or np.any(values > 1.0 + GEOMETRY_HERMITIAN_TOLERANCE)
    ):
        raise ValueError(f"{field} lies outside [0,1]")
    return np.clip(values, 0.0, 1.0).astype(np.float64, copy=False)


def _compute_geometry_spectrum_from_matrices(
    s_curv: np.ndarray,
    kernel_basis: np.ndarray,
    physical_quotient_map: np.ndarray,
    physical_quotient_metric: np.ndarray,
    target_physical_representatives: np.ndarray,
    *,
    thresholds: GeometryNumericalThresholds,
) -> GeometrySpectrum:
    """Measure constraint leakage and target coverage in the frozen quotient."""

    response_view = _matrix_header(s_curv, "s_curv")
    kernel_view = _matrix_header(kernel_basis, "kernel_basis")
    quotient_view = _matrix_header(
        physical_quotient_map,
        "physical_quotient_map",
    )
    metric_view = _matrix_header(
        physical_quotient_metric,
        "physical_quotient_metric",
        square=True,
    )
    targets_view = _matrix_header(
        target_physical_representatives,
        "target_physical_representatives",
    )
    ambient_dimension = response_view.shape[0]
    if response_view.shape[1] > ambient_dimension:
        raise ValueError("s_curv has more columns than its observer dimension")
    if kernel_view.shape[0] != ambient_dimension:
        raise ValueError("kernel_basis observer dimension mismatch")
    if quotient_view.shape[1] != ambient_dimension:
        raise ValueError("physical_quotient_map source dimension mismatch")
    if metric_view.shape[0] != quotient_view.shape[0]:
        raise ValueError("physical_quotient_metric dimension mismatch")
    if targets_view.shape[0] != ambient_dimension:
        raise ValueError("target representative observer dimension mismatch")
    if type(thresholds) is not GeometryNumericalThresholds:
        raise TypeError("thresholds must be exact calibrated numerical values")

    arithmetic_work = _geometry_arithmetic_work(
        response_view,
        kernel_view,
        quotient_view,
        metric_view,
        targets_view,
    )
    if arithmetic_work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError("geometry calculation exceeds the arithmetic work cap")

    response = _materialize_matrix(response_view, "s_curv")
    kernel = _materialize_matrix(kernel_view, "kernel_basis")
    quotient = _materialize_matrix(
        quotient_view,
        "physical_quotient_map",
    )
    metric = _materialize_matrix(
        metric_view,
        "physical_quotient_metric",
    )
    targets = _materialize_matrix(
        targets_view,
        "target_physical_representatives",
    )

    # Metric validation is deliberately first among decompositions.
    whitening = hermitian_positive_whitener(metric)
    response_orthogonality_residual = float(
        np.linalg.norm(
            response.conj().T @ response
            - np.eye(response.shape[1], dtype=np.complex128),
            ord=2,
        )
    )
    if (
        not math.isfinite(response_orthogonality_residual)
        or response_orthogonality_residual > GEOMETRY_HERMITIAN_TOLERANCE
    ):
        raise ValueError("s_curv exceeds the orthogonality residual tolerance")
    kernel_orth = canonical_orthonormal_columns(
        kernel,
        absolute_threshold=thresholds.signal_threshold,
        expected_rank=kernel.shape[1],
    )

    residual = response - kernel_orth @ (kernel_orth.conj().T @ response)
    g_values = _canonical_unit_interval_array(
        np.linalg.svd(
            residual,
            compute_uv=False,
            full_matrices=False,
        ),
        "geometry singular value",
    )
    if len(g_values) != response.shape[1]:
        raise ValueError("geometry spectrum lost an explicit response direction")
    geometry_ambiguous = bool(
        np.any(
            np.abs(g_values - thresholds.geometry_threshold)
            < thresholds.geometry_ambiguity_half_width
        )
    )
    delta_geom_dof = (
        None
        if geometry_ambiguous
        else float(
            np.count_nonzero(g_values >= thresholds.geometry_threshold) / len(g_values)
        )
    )
    delta_geom_energy = float(math.sqrt(float(np.mean(g_values**2))))

    whitened_quotient = whitening.sqrt_metric @ quotient
    mapped_response = whitened_quotient @ response
    s_phys = canonical_orthonormal_columns(
        mapped_response,
        absolute_threshold=thresholds.signal_threshold,
    )
    mapped_targets = whitened_quotient @ targets
    target_basis = canonical_orthonormal_columns(
        mapped_targets,
        absolute_threshold=thresholds.signal_threshold,
        expected_rank=targets.shape[1],
    )
    if s_phys.shape[1] == 0:
        k_cover = np.zeros(
            (target_basis.shape[1], target_basis.shape[1]),
            dtype=np.complex128,
        )
    else:
        target_overlap = s_phys.conj().T @ target_basis
        k_cover = target_overlap.conj().T @ target_overlap
    k_cover_hermitian_residual = float(
        np.linalg.norm(k_cover - k_cover.conj().T, ord=2)
    )
    if (
        not math.isfinite(k_cover_hermitian_residual)
        or k_cover_hermitian_residual > GEOMETRY_HERMITIAN_TOLERANCE
    ):
        raise ValueError("K_cover exceeds the Hermitian residual tolerance")
    c_values = _canonical_unit_interval_array(
        np.linalg.eigvalsh(k_cover),
        "coverage eigenvalue",
    )
    coverage_ambiguous = bool(
        np.any(
            np.abs(c_values - thresholds.coverage_threshold)
            < thresholds.coverage_ambiguity_half_width
        )
    )
    if coverage_ambiguous:
        n_cover = None
        coverage_phys = None
        rank_deficit = None
    else:
        n_cover = int(np.count_nonzero(c_values >= thresholds.coverage_threshold))
        coverage_phys = float(n_cover / len(c_values))
        rank_deficit = int(len(c_values) - n_cover)

    return GeometrySpectrum(
        g_spectrum=tuple(float(value) for value in g_values),
        c_spectrum=tuple(float(value) for value in c_values),
        n_response=None,
        n_curv=response.shape[1],
        max_g=float(np.max(g_values)),
        rms_g=delta_geom_energy,
        frobenius_leakage=float(np.linalg.norm(residual, ord="fro")),
        delta_geom_dof=delta_geom_dof,
        delta_geom_energy=delta_geom_energy,
        n_cover=n_cover,
        coverage_phys=coverage_phys,
        rank_deficit=rank_deficit,
        geometry_ambiguous=geometry_ambiguous,
        coverage_ambiguous=coverage_ambiguous,
        response_orthogonality_residual=response_orthogonality_residual,
        k_cover_hermitian_residual=k_cover_hermitian_residual,
    )


def _frozen_unitary(size: int, seed: str) -> np.ndarray:
    indices = np.arange(size, dtype=np.float64)
    fourier = np.exp(2.0j * math.pi * np.outer(indices, indices) / size) / math.sqrt(
        size
    )
    phases = []
    denominator = float(2**64)
    for index in range(size):
        digest = hashlib.sha256(f"{seed}:{index}".encode("ascii")).digest()
        angle = 2.0 * math.pi * int.from_bytes(digest[:8], "big") / denominator
        phases.append(complex(math.cos(angle), math.sin(angle)))
    return np.asarray(
        fourier * np.asarray(phases, dtype=np.complex128)[None, :],
        dtype=np.complex128,
    )


def _optional_drift(
    first: Optional[float],
    second: Optional[float],
) -> Optional[float]:
    if first is None or second is None:
        return 0.0 if first is None and second is None else None
    return abs(first - second)


def _audit_degenerate_rotations_from_matrices(
    s_curv: np.ndarray,
    kernel_basis: np.ndarray,
    physical_quotient_map: np.ndarray,
    physical_quotient_metric: np.ndarray,
    target_physical_representatives: np.ndarray,
    *,
    thresholds: GeometryNumericalThresholds,
) -> GeometryRotationAudit:
    """Apply the three frozen common unitary rotations and audit main outputs."""

    response_view = _matrix_header(s_curv, "s_curv")
    kernel_view = _matrix_header(kernel_basis, "kernel_basis")
    quotient_view = _matrix_header(
        physical_quotient_map,
        "physical_quotient_map",
    )
    metric_view = _matrix_header(
        physical_quotient_metric,
        "physical_quotient_metric",
        square=True,
    )
    targets_view = _matrix_header(
        target_physical_representatives,
        "target_physical_representatives",
    )
    if type(thresholds) is not GeometryNumericalThresholds:
        raise TypeError("thresholds must be exact calibrated numerical values")
    single_work = _geometry_arithmetic_work(
        response_view,
        kernel_view,
        quotient_view,
        metric_view,
        targets_view,
    )
    rotation_work = (
        3 * response_view.shape[0] * response_view.shape[1] ** 2
        + response_view.shape[0] * response_view.shape[1] * min(response_view.shape)
        + response_view.shape[1] ** 2
    )
    aggregate_work = (1 + len(DEGENERATE_ROTATION_SEEDS)) * single_work + len(
        DEGENERATE_ROTATION_SEEDS
    ) * rotation_work
    if aggregate_work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError(
            "geometry rotation audit aggregate calculation exceeds the arithmetic work cap"
        )

    response = _materialize_matrix(response_view, "s_curv")
    baseline = _compute_geometry_spectrum_from_matrices(
        response,
        kernel_view,
        quotient_view,
        metric_view,
        targets_view,
        thresholds=thresholds,
    )
    rows = []
    for seed in DEGENERATE_ROTATION_SEEDS:
        rotated_response = response @ _frozen_unitary(response.shape[1], seed)
        rotated = _compute_geometry_spectrum_from_matrices(
            rotated_response,
            kernel_view,
            quotient_view,
            metric_view,
            targets_view,
            thresholds=thresholds,
        )
        g_drift = max(
            abs(first - second)
            for first, second in zip(
                baseline.g_spectrum,
                rotated.g_spectrum,
            )
        )
        c_drift = max(
            abs(first - second)
            for first, second in zip(
                baseline.c_spectrum,
                rotated.c_spectrum,
            )
        )
        optional_coordinate_drifts = (
            _optional_drift(
                baseline.delta_geom_dof,
                rotated.delta_geom_dof,
            ),
            _optional_drift(
                baseline.coverage_phys,
                rotated.coverage_phys,
            ),
        )
        coordinate_drift = (
            None
            if any(value is None for value in optional_coordinate_drifts)
            or baseline.rank_deficit != rotated.rank_deficit
            else max(
                *(value for value in optional_coordinate_drifts if value is not None),
                abs(baseline.delta_geom_energy - rotated.delta_geom_energy),
            )
        )
        projector_drift = float(
            np.linalg.norm(
                response - rotated_response @ (rotated_response.conj().T @ response),
                ord=2,
            )
        )
        row_max = (
            None
            if coordinate_drift is None
            else max(
                g_drift,
                c_drift,
                coordinate_drift,
                projector_drift,
            )
        )
        rows.append(
            GeometryRotationRow(
                seed=seed,
                g_spectrum_drift=g_drift,
                c_spectrum_drift=c_drift,
                coordinate_drift=coordinate_drift,
                projector_drift=projector_drift,
                row_drift_max=row_max,
            )
        )
    frozen_rows = tuple(rows)
    maximum = (
        None
        if any(row.row_drift_max is None for row in frozen_rows)
        else max(
            row.row_drift_max for row in frozen_rows if row.row_drift_max is not None
        )
    )
    return GeometryRotationAudit(
        rows=frozen_rows,
        degenerate_rotation_drift_max=maximum,
        passed=bool(
            maximum is not None
            and math.isfinite(maximum)
            and maximum <= DEGENERATE_ROTATION_DRIFT_MAX
        ),
    )


GeometryThresholdSide = Literal["below", "grey", "above"]


class GeometryAuthorityUnavailableError(RuntimeError):
    """Task-14 authority cannot be issued from the current Task-12 schema."""


def _sha(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _exact_record(
    value: object,
    record_type: type,
    field: str,
) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    try:
        observed = frozenset(vars(value))
    except TypeError as exc:
        raise TypeError(f"{field} has no exact record body") from exc
    expected = frozenset(record_type.__dataclass_fields__)
    if observed != expected:
        raise ValueError(f"{field} contains missing or unknown fields")


def _finite_wire_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _unit_spectrum(
    values: object,
    field: str,
) -> tuple[float, ...]:
    if type(values) is not tuple or not values:
        raise ValueError(f"{field} must be a non-empty tuple")
    result = tuple(
        _finite_wire_float(value, f"{field}[{index}]")
        for index, value in enumerate(values)
    )
    if any(value < 0.0 or value > 1.0 for value in result):
        raise ValueError(f"{field} lies outside [0,1]")
    return result


def _side_labels(
    labels: object,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[GeometryThresholdSide, ...]:
    if type(labels) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    if not labels and not allow_empty:
        raise ValueError(f"{field} must be non-empty")
    if not all(
        type(label) is str and label in ("below", "grey", "above") for label in labels
    ):
        raise ValueError(f"{field} contains a non-frozen side label")
    return labels


def _signed_margins(
    values: object,
    field: str,
) -> tuple[float, ...]:
    if type(values) is not tuple or not values:
        raise ValueError(f"{field} must be a non-empty tuple")
    return tuple(
        _finite_wire_float(value, f"{field}[{index}]")
        for index, value in enumerate(values)
    )


def _measured_side(
    value: float,
    threshold: float,
    half_width: float,
) -> GeometryThresholdSide:
    margin = value - threshold
    if abs(margin) < half_width:
        return "grey"
    return "below" if margin < 0.0 else "above"


@dataclass(frozen=True)
class GeometryCoverageThresholdInstanceAudit:
    audit_schema_version: str
    application_spec: V3M0SyntheticControlApplicationSpec
    permit: CalibrationApplicationPermit
    response_block: ResponseBlock
    g_spectrum: tuple[float, ...]
    c_spectrum: tuple[float, ...]
    measured_geometry_side_labels: tuple[GeometryThresholdSide, ...]
    measured_coverage_side_labels: tuple[GeometryThresholdSide, ...]
    expected_geometry_side_labels: tuple[GeometryThresholdSide, ...]
    expected_coverage_side_labels: tuple[GeometryThresholdSide, ...]
    geometry_signed_threshold_margins: tuple[float, ...]
    coverage_signed_threshold_margins: tuple[float, ...]
    geometry_minimum_absolute_margin: float
    coverage_minimum_absolute_margin: float
    audit_sha: str

    def __post_init__(self) -> None:
        if type(self.audit_schema_version) is not str or self.audit_schema_version != (
            GEOMETRY_COVERAGE_THRESHOLD_INSTANCE_AUDIT_SCHEMA_VERSION
        ):
            raise ValueError("geometry threshold audit schema is not frozen")
        if type(self.application_spec) is not V3M0SyntheticControlApplicationSpec:
            raise TypeError("application_spec has the wrong strict type")
        if type(self.permit) is not CalibrationApplicationPermit:
            raise TypeError("permit has the wrong strict type")
        if type(self.response_block) is not ResponseBlock:
            raise TypeError("response_block has the wrong strict type")
        g_spectrum = _unit_spectrum(self.g_spectrum, "g_spectrum")
        c_spectrum = _unit_spectrum(self.c_spectrum, "c_spectrum")
        measured_geometry = _side_labels(
            self.measured_geometry_side_labels,
            "measured_geometry_side_labels",
        )
        measured_coverage = _side_labels(
            self.measured_coverage_side_labels,
            "measured_coverage_side_labels",
        )
        expected_geometry = _side_labels(
            self.expected_geometry_side_labels,
            "expected_geometry_side_labels",
            allow_empty=True,
        )
        expected_coverage = _side_labels(
            self.expected_coverage_side_labels,
            "expected_coverage_side_labels",
            allow_empty=True,
        )
        geometry_margins = _signed_margins(
            self.geometry_signed_threshold_margins,
            "geometry_signed_threshold_margins",
        )
        coverage_margins = _signed_margins(
            self.coverage_signed_threshold_margins,
            "coverage_signed_threshold_margins",
        )
        if (
            len(measured_geometry) != len(g_spectrum)
            or len(geometry_margins) != len(g_spectrum)
            or (expected_geometry and len(expected_geometry) != len(g_spectrum))
        ):
            raise ValueError("geometry threshold audit lengths do not agree")
        if (
            len(measured_coverage) != len(c_spectrum)
            or len(coverage_margins) != len(c_spectrum)
            or (expected_coverage and len(expected_coverage) != len(c_spectrum))
        ):
            raise ValueError("coverage threshold audit lengths do not agree")
        expected_measured_geometry = tuple(
            _measured_side(
                value,
                GEOMETRY_THRESHOLD,
                GEOMETRY_AMBIGUITY_HALF_WIDTH,
            )
            for value in g_spectrum
        )
        expected_measured_coverage = tuple(
            _measured_side(
                value,
                COVERAGE_THRESHOLD,
                COVERAGE_AMBIGUITY_HALF_WIDTH,
            )
            for value in c_spectrum
        )
        if measured_geometry != expected_measured_geometry:
            raise ValueError("measured geometry side labels were not recomputed")
        if measured_coverage != expected_measured_coverage:
            raise ValueError("measured coverage side labels were not recomputed")
        if geometry_margins != tuple(
            value - GEOMETRY_THRESHOLD for value in g_spectrum
        ):
            raise ValueError("geometry signed margins were not recomputed")
        if coverage_margins != tuple(
            value - COVERAGE_THRESHOLD for value in c_spectrum
        ):
            raise ValueError("coverage signed margins were not recomputed")
        geometry_minimum = _finite_wire_float(
            self.geometry_minimum_absolute_margin,
            "geometry_minimum_absolute_margin",
        )
        coverage_minimum = _finite_wire_float(
            self.coverage_minimum_absolute_margin,
            "coverage_minimum_absolute_margin",
        )
        if geometry_minimum < 0.0 or coverage_minimum < 0.0:
            raise ValueError("minimum absolute margins must be non-negative")
        if geometry_minimum != min(abs(value) for value in geometry_margins):
            raise ValueError("geometry minimum absolute margin was not recomputed")
        if coverage_minimum != min(abs(value) for value in coverage_margins):
            raise ValueError("coverage minimum absolute margin was not recomputed")
        _sha(self.audit_sha, "audit_sha")


def _application_spec_record(
    spec: V3M0SyntheticControlApplicationSpec,
) -> dict[str, object]:
    return {
        **synthetic_control_application_spec_payload(spec),
        "application_spec_sha": spec.application_spec_sha,
    }


def _permit_record(
    permit: CalibrationApplicationPermit,
) -> dict[str, object]:
    return {
        **calibration_application_permit_payload(permit),
        "permit_sha": permit.permit_sha,
    }


def _response_block_record(block: ResponseBlock) -> dict[str, object]:
    return {
        **response_block_payload(block),
        "block_sha": block.block_sha,
    }


def geometry_coverage_threshold_instance_audit_payload(
    audit: GeometryCoverageThresholdInstanceAudit,
) -> dict[str, object]:
    _exact_record(
        audit,
        GeometryCoverageThresholdInstanceAudit,
        "geometry threshold instance audit",
    )
    audit.__post_init__()
    _preflight_tree(audit, "geometry threshold instance audit")
    return {
        "audit_schema_version": audit.audit_schema_version,
        "application_spec": _application_spec_record(audit.application_spec),
        "permit": _permit_record(audit.permit),
        "response_block": _response_block_record(audit.response_block),
        "g_spectrum": list(audit.g_spectrum),
        "c_spectrum": list(audit.c_spectrum),
        "measured_geometry_side_labels": list(audit.measured_geometry_side_labels),
        "measured_coverage_side_labels": list(audit.measured_coverage_side_labels),
        "expected_geometry_side_labels": list(audit.expected_geometry_side_labels),
        "expected_coverage_side_labels": list(audit.expected_coverage_side_labels),
        "geometry_signed_threshold_margins": list(
            audit.geometry_signed_threshold_margins
        ),
        "coverage_signed_threshold_margins": list(
            audit.coverage_signed_threshold_margins
        ),
        "geometry_minimum_absolute_margin": (audit.geometry_minimum_absolute_margin),
        "coverage_minimum_absolute_margin": (audit.coverage_minimum_absolute_margin),
    }


@dataclass(frozen=True)
class GeometryCoverageThresholdControlEvidence:
    evidence_schema_version: str
    parent_freeze: ParentFreezeManifest
    instance_audits: tuple[GeometryCoverageThresholdInstanceAudit, ...]
    evidence_sha: str

    def __post_init__(self) -> None:
        if type(
            self.evidence_schema_version
        ) is not str or self.evidence_schema_version != (
            GEOMETRY_COVERAGE_THRESHOLD_CONTROL_EVIDENCE_SCHEMA_VERSION
        ):
            raise ValueError("geometry threshold evidence schema is not frozen")
        if type(self.parent_freeze) is not ParentFreezeManifest:
            raise TypeError("parent_freeze has the wrong strict type")
        if type(self.instance_audits) is not tuple or not self.instance_audits:
            raise ValueError("instance_audits must be a non-empty tuple")
        if not all(
            type(audit) is GeometryCoverageThresholdInstanceAudit
            for audit in self.instance_audits
        ):
            raise TypeError("instance_audits has the wrong strict type")
        _sha(self.evidence_sha, "evidence_sha")


def geometry_coverage_threshold_control_evidence_payload(
    evidence: GeometryCoverageThresholdControlEvidence,
) -> dict[str, object]:
    _exact_record(
        evidence,
        GeometryCoverageThresholdControlEvidence,
        "geometry threshold control evidence",
    )
    evidence.__post_init__()
    _preflight_tree(evidence, "geometry threshold control evidence")
    return {
        "evidence_schema_version": evidence.evidence_schema_version,
        "parent_freeze": {
            **parent_freeze_manifest_payload(evidence.parent_freeze),
            "parent_freeze_sha": evidence.parent_freeze.parent_freeze_sha,
        },
        "instance_audits": [
            {
                **geometry_coverage_threshold_instance_audit_payload(audit),
                "audit_sha": audit.audit_sha,
            }
            for audit in evidence.instance_audits
        ],
    }


@dataclass(frozen=True)
class GeometryCoverageThresholdCalibration:
    calibration_schema_version: str
    tau_geom: Literal[0.05]
    geom_ambiguity_half_width: Literal[0.01]
    tau_cover: Literal[0.5]
    cover_ambiguity_half_width: Literal[0.1]
    control_evidence: GeometryCoverageThresholdControlEvidence
    calibration_sha: str

    def __post_init__(self) -> None:
        if (
            type(self.calibration_schema_version) is not str
            or self.calibration_schema_version
            != GEOMETRY_COVERAGE_THRESHOLD_CALIBRATION_SCHEMA_VERSION
        ):
            raise ValueError("geometry threshold calibration schema is not frozen")
        if type(self.tau_geom) is not float or self.tau_geom != GEOMETRY_THRESHOLD:
            raise ValueError("tau_geom is not frozen")
        if (
            type(self.geom_ambiguity_half_width) is not float
            or self.geom_ambiguity_half_width != GEOMETRY_AMBIGUITY_HALF_WIDTH
        ):
            raise ValueError("geometry ambiguity half-width is not frozen")
        if type(self.tau_cover) is not float or self.tau_cover != COVERAGE_THRESHOLD:
            raise ValueError("tau_cover is not frozen")
        if (
            type(self.cover_ambiguity_half_width) is not float
            or self.cover_ambiguity_half_width != COVERAGE_AMBIGUITY_HALF_WIDTH
        ):
            raise ValueError("coverage ambiguity half-width is not frozen")
        if type(self.control_evidence) is not GeometryCoverageThresholdControlEvidence:
            raise TypeError("control_evidence has the wrong strict type")
        _sha(self.calibration_sha, "calibration_sha")


def geometry_coverage_threshold_calibration_payload(
    calibration: GeometryCoverageThresholdCalibration,
) -> dict[str, object]:
    _exact_record(
        calibration,
        GeometryCoverageThresholdCalibration,
        "geometry threshold calibration",
    )
    calibration.__post_init__()
    _preflight_tree(calibration, "geometry threshold calibration")
    return {
        "calibration_schema_version": calibration.calibration_schema_version,
        "tau_geom": calibration.tau_geom,
        "geom_ambiguity_half_width": (calibration.geom_ambiguity_half_width),
        "tau_cover": calibration.tau_cover,
        "cover_ambiguity_half_width": (calibration.cover_ambiguity_half_width),
        "control_evidence": {
            **geometry_coverage_threshold_control_evidence_payload(
                calibration.control_evidence
            ),
            "evidence_sha": calibration.control_evidence.evidence_sha,
        },
    }


def _wire_fp64(wire: object, field: str) -> float:
    if (
        getattr(wire, "value_kind", None) != "fp64-bits"
        or type(getattr(wire, "fp64_bits_value", None)) is not int
    ):
        raise ValueError(f"{field} must be a frozen fp64 prediction")
    bits = wire.fp64_bits_value
    assert bits is not None
    return struct.unpack(">d", bits.to_bytes(8, "big", signed=False))[0]


def _expected_threshold_labels(
    application: V3M0SyntheticControlApplicationSpec,
) -> tuple[
    tuple[GeometryThresholdSide, ...],
    tuple[GeometryThresholdSide, ...],
]:
    profile = application.expected_prediction_profile
    expected_geometry: list[GeometryThresholdSide] = []
    expected_coverage: list[GeometryThresholdSide] = []
    for name, wires in profile.expected_exact_values:
        if name.startswith("g-spectrum."):
            expected_geometry.extend(
                _measured_side(
                    _wire_fp64(wire, name),
                    GEOMETRY_THRESHOLD,
                    GEOMETRY_AMBIGUITY_HALF_WIDTH,
                )
                for wire in wires
            )
        elif name in ("coverage-spectrum", "coverage-after-dressing"):
            expected_coverage.extend(
                _measured_side(
                    _wire_fp64(wire, name),
                    COVERAGE_THRESHOLD,
                    COVERAGE_AMBIGUITY_HALF_WIDTH,
                )
                for wire in wires
            )
    return tuple(expected_geometry), tuple(expected_coverage)


def _validate_instance_audit(
    audit: GeometryCoverageThresholdInstanceAudit,
    parent_freeze: ParentFreezeManifest,
) -> None:
    payload = geometry_coverage_threshold_instance_audit_payload(audit)
    if audit.audit_sha != canonical_sha(payload):
        raise ValueError("geometry threshold instance audit self-hash mismatch")
    if audit.application_spec.application_spec_sha != canonical_sha(
        synthetic_control_application_spec_payload(audit.application_spec)
    ):
        raise ValueError("application_spec_sha does not match the full body")
    if audit.permit.permit_sha != canonical_sha(
        calibration_application_permit_payload(audit.permit)
    ):
        raise ValueError("permit_sha does not match the full body")
    if audit.response_block.block_sha != canonical_sha(
        response_block_payload(audit.response_block)
    ):
        raise ValueError("response block SHA does not match the full body")
    if audit.application_spec != audit.permit.application_spec:
        raise ValueError("audit application spec does not match its permit")
    if audit.permit.parent_freeze != parent_freeze:
        raise ValueError("audit permit does not bind the evidence parent")
    if audit.response_block.application_authority_sha != audit.permit.permit_sha:
        raise ValueError("response block does not bind the application permit")
    expected_geometry, expected_coverage = _expected_threshold_labels(
        audit.application_spec
    )
    if audit.expected_geometry_side_labels != expected_geometry:
        raise ValueError("expected geometry labels do not come from ParentFreeze")
    if audit.expected_coverage_side_labels != expected_coverage:
        raise ValueError("expected coverage labels do not come from ParentFreeze")


def _validate_calibration_body(
    calibration: GeometryCoverageThresholdCalibration,
) -> None:
    calibration_payload = geometry_coverage_threshold_calibration_payload(calibration)
    if calibration.calibration_sha != canonical_sha(calibration_payload):
        raise ValueError("geometry threshold calibration self-hash mismatch")
    evidence = calibration.control_evidence
    if evidence.parent_freeze.parent_freeze_sha != canonical_sha(
        parent_freeze_manifest_payload(evidence.parent_freeze)
    ):
        raise ValueError("ParentFreeze SHA does not match the full body")
    for audit in evidence.instance_audits:
        _validate_instance_audit(audit, evidence.parent_freeze)
    evidence_payload = geometry_coverage_threshold_control_evidence_payload(evidence)
    if evidence.evidence_sha != canonical_sha(evidence_payload):
        raise ValueError("geometry threshold evidence self-hash mismatch")
    observed_controls = {
        audit.application_spec.control_case_id for audit in evidence.instance_audits
    }
    if (
        len(evidence.instance_audits) != len(GEOMETRY_THRESHOLD_CONTROL_CASE_IDS)
        or len(observed_controls) != len(evidence.instance_audits)
        or observed_controls != set(GEOMETRY_THRESHOLD_CONTROL_CASE_IDS)
    ):
        raise ValueError("geometry threshold evidence must cover C15-C17")


@dataclass(frozen=True)
class _GeometryThresholdAuthority:
    calibration: GeometryCoverageThresholdCalibration
    blocks: tuple[VerifiedResponseBlock, ...]
    permits: tuple[VerifiedCalibrationApplicationPermit, ...]
    digest: str
    seal: str


@dataclass(frozen=True)
class _GeometryThresholdView:
    calibration: GeometryCoverageThresholdCalibration


class VerifiedGeometryCoverageThresholdCalibration:
    """Opaque capability issued only after full C15-C17 replay."""

    __slots__ = ("__calibration", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        calibration: GeometryCoverageThresholdCalibration,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError(
                "VerifiedGeometryCoverageThresholdCalibration is module-issued only"
            )
        object.__setattr__(
            self,
            "_VerifiedGeometryCoverageThresholdCalibration__calibration",
            calibration,
        )
        object.__setattr__(
            self,
            "_VerifiedGeometryCoverageThresholdCalibration__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedGeometryCoverageThresholdCalibration__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("geometry threshold calibration is immutable")

    @property
    def calibration(self) -> GeometryCoverageThresholdCalibration:
        return _reverify_verified_geometry_coverage_threshold_calibration(
            self
        ).calibration


_GEOMETRY_THRESHOLD_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedGeometryCoverageThresholdCalibration],
        _GeometryThresholdAuthority,
    ],
] = {}
_GEOMETRY_THRESHOLD_LOCK = threading.RLock()


def _validate_live_inputs(
    blocks: object,
    permits: object,
) -> tuple[
    tuple[VerifiedResponseBlock, ...],
    tuple[ResponseBlock, ...],
    tuple[VerifiedCalibrationApplicationPermit, ...],
    tuple[CalibrationApplicationPermit, ...],
]:
    if type(blocks) is not tuple:
        raise TypeError("blocks must be an exact tuple")
    if type(permits) is not tuple:
        raise TypeError("permits must be an exact tuple")
    if not blocks or not permits:
        raise ValueError("geometry threshold authority requires all C15-C17 controls")
    block_wrappers: list[VerifiedResponseBlock] = []
    block_bodies: list[ResponseBlock] = []
    for index, block in enumerate(blocks):
        if type(block) is not VerifiedResponseBlock:
            raise TypeError(f"blocks[{index}] must be a live VerifiedResponseBlock")
        block_wrappers.append(block)
        block_bodies.append(_reverify_verified_response_block(block).block)
    permit_wrappers: list[VerifiedCalibrationApplicationPermit] = []
    permit_bodies: list[CalibrationApplicationPermit] = []
    for index, permit in enumerate(permits):
        if type(permit) is not VerifiedCalibrationApplicationPermit:
            raise TypeError(
                f"permits[{index}] must be a live VerifiedCalibrationApplicationPermit"
            )
        permit_wrappers.append(permit)
        permit_bodies.append(
            _reverify_verified_calibration_application_permit(permit).permit
        )
    if len(permit_bodies) != len(GEOMETRY_THRESHOLD_CONTROL_CASE_IDS):
        raise ValueError("geometry threshold authority requires one permit per C15-C17")
    controls = tuple(
        permit.application_spec.control_case_id for permit in permit_bodies
    )
    if len(set(controls)) != len(controls) or set(controls) != set(
        GEOMETRY_THRESHOLD_CONTROL_CASE_IDS
    ):
        raise ValueError("geometry threshold permits must cover C15-C17 exactly")
    permit_by_sha = {permit.permit_sha: permit for permit in permit_bodies}
    if len(block_bodies) != len(permit_bodies):
        raise ValueError("geometry threshold authority requires one block per permit")
    block_authorities = tuple(block.application_authority_sha for block in block_bodies)
    if len(set(block_authorities)) != len(block_authorities) or set(
        block_authorities
    ) != set(permit_by_sha):
        raise ValueError("response block is not bound to a C15-C17 permit")
    parent_bodies = tuple(permit.parent_freeze for permit in permit_bodies)
    if any(parent != parent_bodies[0] for parent in parent_bodies[1:]):
        raise ValueError("C15-C17 permits do not share one ParentFreeze")
    calibration_bodies = tuple(permit.calibration_manifest for permit in permit_bodies)
    if any(
        calibration != calibration_bodies[0] for calibration in calibration_bodies[1:]
    ):
        raise ValueError("C15-C17 permits do not share one calibration")
    return (
        tuple(block_wrappers),
        tuple(block_bodies),
        tuple(permit_wrappers),
        tuple(permit_bodies),
    )


def _raise_missing_task12_geometry_contract(
    block_bodies: tuple[ResponseBlock, ...],
) -> None:
    missing: set[str] = set()
    for block in block_bodies:
        for field in GEOMETRY_AUTHORITY_REQUIRED_TASK12_FIELDS:
            if not hasattr(block, field) and not hasattr(block.operator_spec, field):
                missing.add(field)
    if missing:
        ordered = tuple(
            field
            for field in GEOMETRY_AUTHORITY_REQUIRED_TASK12_FIELDS
            if field in missing
        )
        raise GeometryAuthorityUnavailableError(
            "Task 12 response-block geometry contract is not frozen; "
            f"missing fields={ordered!r}"
        )
    raise GeometryAuthorityUnavailableError(
        "Task 12 geometry-target extraction authority is not frozen"
    )


def _expected_geometry_threshold_calibration(
    blocks: tuple[VerifiedResponseBlock, ...],
    permits: tuple[VerifiedCalibrationApplicationPermit, ...],
) -> GeometryCoverageThresholdCalibration:
    _, block_bodies, _, _ = _validate_live_inputs(blocks, permits)
    _raise_missing_task12_geometry_contract(block_bodies)


def _issue_geometry_threshold_calibration(
    calibration: GeometryCoverageThresholdCalibration,
    blocks: tuple[VerifiedResponseBlock, ...],
    permits: tuple[VerifiedCalibrationApplicationPermit, ...],
) -> VerifiedGeometryCoverageThresholdCalibration:
    expected = _expected_geometry_threshold_calibration(blocks, permits)
    if calibration != expected:
        raise ValueError(
            "geometry threshold calibration differs from the live C15-C17 replay"
        )
    _validate_calibration_body(calibration)
    digest = canonical_sha(geometry_coverage_threshold_calibration_payload(calibration))
    seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-geometry-coverage-threshold-calibration.v1"
            ),
            "calibration_sha": calibration.calibration_sha,
            "body_digest": digest,
        }
    )
    frozen = copy.deepcopy(calibration)
    wrapper = VerifiedGeometryCoverageThresholdCalibration(
        _ISSUANCE_TOKEN,
        copy.deepcopy(frozen),
        seal,
    )
    identity = id(wrapper)
    authority = _GeometryThresholdAuthority(
        calibration=frozen,
        blocks=blocks,
        permits=permits,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[VerifiedGeometryCoverageThresholdCalibration],
        wrapper_id: int = identity,
    ) -> None:
        with _GEOMETRY_THRESHOLD_LOCK:
            current = _GEOMETRY_THRESHOLD_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _GEOMETRY_THRESHOLD_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _GEOMETRY_THRESHOLD_LOCK:
        _GEOMETRY_THRESHOLD_LIVE[identity] = (reference, authority)
    return wrapper


def _reverify_verified_geometry_coverage_threshold_calibration(
    wrapper: VerifiedGeometryCoverageThresholdCalibration,
) -> _GeometryThresholdView:
    if type(wrapper) is not VerifiedGeometryCoverageThresholdCalibration:
        raise TypeError(
            "consumer requires a live VerifiedGeometryCoverageThresholdCalibration"
        )
    with _GEOMETRY_THRESHOLD_LOCK:
        current = _GEOMETRY_THRESHOLD_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("geometry threshold calibration identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedGeometryCoverageThresholdCalibration__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedGeometryCoverageThresholdCalibration__calibration",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedGeometryCoverageThresholdCalibration__seal",
        )
    except AttributeError as exc:
        raise ValueError(
            "geometry threshold calibration authority is incomplete"
        ) from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("geometry threshold calibration token mismatch")
    expected = _expected_geometry_threshold_calibration(
        authority.blocks,
        authority.permits,
    )
    observed_digest = canonical_sha(
        geometry_coverage_threshold_calibration_payload(raw)
    )
    expected_digest = canonical_sha(
        geometry_coverage_threshold_calibration_payload(expected)
    )
    expected_seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-geometry-coverage-threshold-calibration.v1"
            ),
            "calibration_sha": expected.calibration_sha,
            "body_digest": expected_digest,
        }
    )
    if (
        raw != authority.calibration
        or expected != authority.calibration
        or observed_digest != authority.digest
        or expected_digest != authority.digest
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("geometry threshold calibration immutable seal mismatch")
    return _GeometryThresholdView(calibration=copy.deepcopy(expected))


def build_geometry_coverage_threshold_calibration(
    blocks: tuple[VerifiedResponseBlock, ...],
    permits: tuple[VerifiedCalibrationApplicationPermit, ...],
) -> VerifiedGeometryCoverageThresholdCalibration:
    """Replay C15-C17 and issue only when Task 12 exposes all frozen operators."""

    expected = _expected_geometry_threshold_calibration(blocks, permits)
    return _issue_geometry_threshold_calibration(expected, blocks, permits)


def verify_geometry_coverage_threshold_calibration(
    raw: GeometryCoverageThresholdCalibration,
    blocks: tuple[VerifiedResponseBlock, ...],
    permits: tuple[VerifiedCalibrationApplicationPermit, ...],
) -> VerifiedGeometryCoverageThresholdCalibration:
    """Hydrate only by full raw-body validation and C15-C17 replay."""

    _exact_record(
        raw,
        GeometryCoverageThresholdCalibration,
        "raw GeometryCoverageThresholdCalibration",
    )
    _validate_calibration_body(raw)
    expected = _expected_geometry_threshold_calibration(blocks, permits)
    if raw != expected:
        raise ValueError("raw geometry threshold calibration differs from replay")
    return _issue_geometry_threshold_calibration(expected, blocks, permits)


def compute_geometry(
    block: VerifiedResponseBlock,
    calibration: VerifiedGeometryCoverageThresholdCalibration,
) -> GeometrySpectrum:
    """Evaluate unary geometry from capabilities only; no caller matrices."""

    if type(block) is not VerifiedResponseBlock:
        raise TypeError("block must be a live VerifiedResponseBlock")
    block_body = _reverify_verified_response_block(block).block
    _reverify_verified_geometry_coverage_threshold_calibration(calibration)
    _raise_missing_task12_geometry_contract((block_body,))


__all__ = [
    "COVERAGE_AMBIGUITY_HALF_WIDTH",
    "COVERAGE_THRESHOLD",
    "DEGENERATE_ROTATION_DRIFT_MAX",
    "DEGENERATE_ROTATION_SEEDS",
    "GEOMETRY_AMBIGUITY_HALF_WIDTH",
    "GEOMETRY_AUTHORITY_REQUIRED_TASK12_FIELDS",
    "GEOMETRY_COVERAGE_THRESHOLD_CALIBRATION_SCHEMA_VERSION",
    "GEOMETRY_COVERAGE_THRESHOLD_CONTROL_EVIDENCE_SCHEMA_VERSION",
    "GEOMETRY_COVERAGE_THRESHOLD_INSTANCE_AUDIT_SCHEMA_VERSION",
    "GEOMETRY_HERMITIAN_TOLERANCE",
    "GEOMETRY_THRESHOLD",
    "GEOMETRY_THRESHOLD_CONTROL_CASE_IDS",
    "GeometryAuthorityUnavailableError",
    "GeometryCoverageThresholdCalibration",
    "GeometryCoverageThresholdControlEvidence",
    "GeometryCoverageThresholdInstanceAudit",
    "GeometryRotationAudit",
    "GeometryRotationRow",
    "GeometrySpectrum",
    "VerifiedGeometryCoverageThresholdCalibration",
    "build_geometry_coverage_threshold_calibration",
    "compute_geometry",
    "geometry_coverage_threshold_calibration_payload",
    "geometry_coverage_threshold_control_evidence_payload",
    "geometry_coverage_threshold_instance_audit_payload",
    "verify_geometry_coverage_threshold_calibration",
]
