"""Pure quotient-geometry kernels for the V3-M0 instrument.

The Task 14 evidence authority must source every matrix from a verified
response block and its frozen target specification.  This module contains only
the deterministic numerical calculation shared by that authority.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .linalg import (
    LINALG_ARITHMETIC_WORK_CAP,
    LINALG_ENTRY_CAP,
    _canonical_columns_work,
    _metric_whitener_work,
    canonical_orthonormal_columns,
    hermitian_positive_whitener,
)


GEOMETRY_HERMITIAN_TOLERANCE = 1e-12
DEGENERATE_ROTATION_SEEDS = (
    "v3m0-degrot-0",
    "v3m0-degrot-1",
    "v3m0-degrot-2",
)
DEGENERATE_ROTATION_DRIFT_MAX = 1e-12


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


def compute_geometry_spectrum(
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


def audit_degenerate_rotations(
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
    baseline = compute_geometry_spectrum(
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
        rotated = compute_geometry_spectrum(
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


__all__ = [
    "DEGENERATE_ROTATION_DRIFT_MAX",
    "DEGENERATE_ROTATION_SEEDS",
    "GEOMETRY_HERMITIAN_TOLERANCE",
    "GeometryNumericalThresholds",
    "GeometryRotationAudit",
    "GeometryRotationRow",
    "GeometrySpectrum",
    "audit_degenerate_rotations",
    "compute_geometry_spectrum",
]
