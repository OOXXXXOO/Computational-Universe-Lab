"""Deterministic metric-aware linear algebra for the V3-M0 instrument.

The public routines in this module are numerical kernels, not evidence
authorities.  They reject non-Hermitian or non-positive metrics before any
whitening and require an explicit quotient map when the original observer
space contains metric-null directions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np


LINALG_ENTRY_CAP = 16_777_216
LINALG_ARITHMETIC_WORK_CAP = 2_000_000_000
DEFAULT_HERMITIAN_TOLERANCE = 1e-12
DEFAULT_ORTHOGONALITY_TOLERANCE = 1e-12


def _matrix_header(
    value: object,
    field: str,
    *,
    square: bool = False,
) -> np.ndarray:
    if type(value) is not np.ndarray:
        raise TypeError(f"{field} must be an exact numpy.ndarray")
    if value.ndim != 2:
        raise ValueError(f"{field} must be a matrix")
    rows, columns = value.shape
    if rows <= 0 or columns <= 0:
        raise ValueError(f"{field} must be non-empty")
    if square and rows != columns:
        raise ValueError(f"{field} must be square")
    if rows * columns > LINALG_ENTRY_CAP:
        raise ValueError(f"{field} exceeds the matrix resource cap")
    if value.dtype not in (np.dtype(np.float64), np.dtype(np.complex128)):
        raise TypeError(f"{field} must have float64 or complex128 dtype")
    return value


def _materialize_matrix(value: np.ndarray, field: str) -> np.ndarray:
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{field} must contain only finite values")
    return np.asarray(value, dtype=np.complex128)


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


def _nonnegative_finite(value: object, field: str) -> float:
    if type(value) not in (float, int):
        raise TypeError(f"{field} must be a real scalar")
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return result


def _spectral_norm(value: np.ndarray) -> float:
    if value.size == 0:
        return 0.0
    if not bool(np.all(np.isfinite(value))):
        return math.inf
    return float(np.linalg.norm(value, ord=2))


def _require_work_within_cap(work: int, field: str) -> None:
    if work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError(f"{field} exceeds the arithmetic work cap")


def _metric_whitener_work(dimension: int) -> int:
    # Hermitian spectral audit, eigendecomposition, two eigenvector/diagonal
    # reconstructions, and two product-plus-spectral residual audits.
    return 10 * dimension**3


def _canonical_columns_work(rows: int, columns: int) -> int:
    rank_cap = min(rows, columns)
    # SVD + two-pass coordinate Gram-Schmidt + accepted matvecs +
    # Gram/projector residual GEMMs and their spectral decompositions.
    return rows * columns * rank_cap + 12 * rows * rank_cap**2 + 3 * rank_cap**3


@dataclass(frozen=True)
class MetricWhitening:
    """Audited positive-metric square root pair.

    Array properties return fresh owning copies so callers cannot mutate the
    snapshot retained by this value.
    """

    _sqrt_metric: np.ndarray
    _inverse_sqrt_metric: np.ndarray
    minimum_eigenvalue: float
    hermitian_residual: float
    reconstruction_residual: float
    inverse_residual: float

    def __post_init__(self) -> None:
        sqrt_metric = np.array(
            self._sqrt_metric,
            dtype=np.complex128,
            copy=True,
            order="C",
        )
        inverse = np.array(
            self._inverse_sqrt_metric,
            dtype=np.complex128,
            copy=True,
            order="C",
        )
        sqrt_metric.setflags(write=False)
        inverse.setflags(write=False)
        object.__setattr__(self, "_sqrt_metric", sqrt_metric)
        object.__setattr__(self, "_inverse_sqrt_metric", inverse)

    @property
    def sqrt_metric(self) -> np.ndarray:
        return np.array(self._sqrt_metric, copy=True, order="C")

    @property
    def inverse_sqrt_metric(self) -> np.ndarray:
        return np.array(self._inverse_sqrt_metric, copy=True, order="C")


@dataclass(frozen=True)
class QuotientWhitenedBasis:
    """Canonical Euclidean basis after an explicit metric quotient."""

    _whitened_basis: np.ndarray
    quotient_rank: int
    orthogonality_residual: float
    metric_minimum_eigenvalue: float

    def __post_init__(self) -> None:
        basis = np.array(
            self._whitened_basis,
            dtype=np.complex128,
            copy=True,
            order="C",
        )
        basis.setflags(write=False)
        object.__setattr__(self, "_whitened_basis", basis)

    @property
    def whitened_basis(self) -> np.ndarray:
        return np.array(self._whitened_basis, copy=True, order="C")


def hermitian_positive_whitener(
    metric: np.ndarray,
    *,
    hermitian_tolerance: float = DEFAULT_HERMITIAN_TOLERANCE,
    minimum_positive_eigenvalue: float = 0.0,
) -> MetricWhitening:
    """Build ``W`` and ``W⁻¹`` with ``W†W=metric`` after hard audits."""

    tolerance = _nonnegative_finite(
        hermitian_tolerance,
        "hermitian_tolerance",
    )
    minimum_positive = _nonnegative_finite(
        minimum_positive_eigenvalue,
        "minimum_positive_eigenvalue",
    )
    values_view = _matrix_header(metric, "metric", square=True)
    _require_work_within_cap(
        _metric_whitener_work(values_view.shape[0]),
        "metric eigendecomposition",
    )
    values = _materialize_matrix(values_view, "metric")
    hermitian_residual = _spectral_norm(values - values.conj().T)
    if hermitian_residual > tolerance:
        raise ValueError("metric exceeds the Hermitian residual tolerance")

    eigenvalues, eigenvectors = np.linalg.eigh(values)
    if not bool(np.all(np.isfinite(eigenvalues)) and np.all(np.isfinite(eigenvectors))):
        raise ValueError("metric eigendecomposition left the finite range")
    minimum_eigenvalue = float(eigenvalues[0])
    if minimum_eigenvalue <= minimum_positive:
        raise ValueError("metric is not strictly positive definite")

    roots = np.sqrt(eigenvalues)
    inverse_roots = 1.0 / roots
    if not bool(np.all(np.isfinite(roots)) and np.all(np.isfinite(inverse_roots))):
        raise ValueError("metric whitening factors left the finite range")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        sqrt_metric = (eigenvectors @ np.diag(roots) @ eigenvectors.conj().T).astype(
            np.complex128, copy=False
        )
        inverse_sqrt = (
            eigenvectors @ np.diag(inverse_roots) @ eigenvectors.conj().T
        ).astype(np.complex128, copy=False)
    if not bool(np.all(np.isfinite(sqrt_metric)) and np.all(np.isfinite(inverse_sqrt))):
        raise ValueError("metric whitening matrices left the finite range")
    identity = np.eye(values.shape[0], dtype=np.complex128)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        reconstruction_residual = _spectral_norm(
            sqrt_metric.conj().T @ sqrt_metric - values
        )
        inverse_residual = _spectral_norm(inverse_sqrt @ sqrt_metric - identity)
    if (
        not np.isfinite(reconstruction_residual)
        or not np.isfinite(inverse_residual)
        or reconstruction_residual > tolerance
        or inverse_residual > tolerance
    ):
        raise ValueError("metric whitening residual exceeds tolerance")
    return MetricWhitening(
        _sqrt_metric=sqrt_metric,
        _inverse_sqrt_metric=inverse_sqrt,
        minimum_eigenvalue=minimum_eigenvalue,
        hermitian_residual=hermitian_residual,
        reconstruction_residual=reconstruction_residual,
        inverse_residual=inverse_residual,
    )


def _canonical_phase(vector: np.ndarray) -> np.ndarray:
    pivot = int(np.argmax(np.abs(vector)))
    magnitude = float(abs(vector[pivot]))
    if magnitude == 0.0:
        return vector
    return vector * np.conjugate(vector[pivot]) / magnitude


def canonical_orthonormal_columns(
    columns: np.ndarray,
    *,
    absolute_threshold: float,
    expected_rank: Optional[int] = None,
    orthogonality_tolerance: float = DEFAULT_ORTHOGONALITY_TOLERANCE,
) -> np.ndarray:
    """Return a deterministic basis of a thresholded column space.

    The SVD determines only the projector.  A lexicographic projected-axis
    Gram-Schmidt pass then fixes a canonical basis, so internal rotations of
    the input columns do not change the returned coordinates.
    """

    threshold = _nonnegative_finite(
        absolute_threshold,
        "absolute_threshold",
    )
    if threshold == 0.0:
        raise ValueError("absolute_threshold must be strictly positive")
    tolerance = _nonnegative_finite(
        orthogonality_tolerance,
        "orthogonality_tolerance",
    )
    values_view = _matrix_header(columns, "columns")
    _require_work_within_cap(
        _canonical_columns_work(*values_view.shape),
        "column-space decomposition",
    )
    if expected_rank is not None:
        if type(expected_rank) is not int or expected_rank < 0:
            raise ValueError("expected_rank must be a nonnegative exact int")
        if expected_rank > min(values_view.shape):
            raise ValueError("expected_rank exceeds the matrix dimensions")

    values = _materialize_matrix(values_view, "columns")
    left, singular_values, _ = np.linalg.svd(
        values,
        full_matrices=False,
    )
    if not bool(np.all(np.isfinite(left)) and np.all(np.isfinite(singular_values))):
        raise ValueError("column-space decomposition left the finite range")
    numerical_floor = (
        np.finfo(np.float64).eps * max(values.shape) * float(singular_values[0]) * 64.0
    )
    if numerical_floor > threshold and bool(
        np.any((singular_values >= threshold) & (singular_values < numerical_floor))
    ):
        raise ValueError("numerical rank is unresolved above the absolute threshold")
    effective_threshold = max(threshold, numerical_floor)
    rank = int(np.count_nonzero(singular_values >= effective_threshold))
    if expected_rank is not None and rank != expected_rank:
        raise ValueError("thresholded column rank differs from expected_rank")
    if rank == 0:
        return np.zeros((values.shape[0], 0), dtype=np.complex128)

    selected = left[:, :rank]
    basis: list[np.ndarray] = []
    coordinate_basis: list[np.ndarray] = []
    axis_threshold = np.finfo(np.float64).eps * max(values.shape) * 64.0
    for axis in range(values.shape[0]):
        # Gram-Schmidt in the rank-dimensional SVD coordinates.  This avoids
        # one ambient-length matrix-vector product for every rejected axis.
        coefficients = np.array(
            np.conjugate(selected[axis, :]),
            dtype=np.complex128,
            copy=True,
        )
        for _ in range(2):
            for prior in coordinate_basis:
                coefficients -= prior * np.vdot(prior, coefficients)
        norm = float(np.linalg.norm(coefficients))
        if norm <= axis_threshold:
            continue
        coefficients /= norm
        candidate = selected @ coefficients
        canonical = _canonical_phase(candidate)
        phase_inner = complex(np.vdot(candidate, canonical))
        if abs(phase_inner) == 0.0:
            raise ValueError("canonical phase construction lost a basis vector")
        phase = phase_inner / abs(phase_inner)
        coordinate_basis.append(coefficients * phase)
        basis.append(canonical)
        if len(basis) == rank:
            break
    if len(basis) != rank:
        raise ValueError("canonical basis construction lost thresholded rank")
    result = np.column_stack(basis).astype(np.complex128, copy=False)
    identity = np.eye(rank, dtype=np.complex128)
    orthogonality_residual = _spectral_norm(result.conj().T @ result - identity)
    projector_residual = _spectral_norm(
        selected - result @ (result.conj().T @ selected)
    )
    if orthogonality_residual > tolerance or projector_residual > tolerance:
        raise ValueError("canonical basis residual exceeds tolerance")
    return np.array(result, copy=True, order="C")


def whiten_quotient_columns(
    columns: np.ndarray,
    quotient_map: np.ndarray,
    quotient_metric: np.ndarray,
    *,
    absolute_threshold: float,
    expected_rank: Optional[int] = None,
) -> QuotientWhitenedBasis:
    """Remove metric-null directions through a frozen quotient, then whiten."""

    values_view = _matrix_header(columns, "columns")
    quotient_view = _matrix_header(quotient_map, "quotient_map")
    if quotient_view.shape[1] != values_view.shape[0]:
        raise ValueError("quotient_map source dimension mismatch")
    metric_view = _matrix_header(
        quotient_metric,
        "quotient_metric",
        square=True,
    )
    if metric_view.shape[0] != quotient_view.shape[0]:
        raise ValueError("quotient_metric dimension mismatch")
    whitened_rank_cap = min(
        quotient_view.shape[0],
        values_view.shape[1],
    )
    _require_work_within_cap(
        _metric_whitener_work(metric_view.shape[0])
        + quotient_view.shape[0] ** 2 * quotient_view.shape[1]
        + quotient_view.shape[0] * quotient_view.shape[1] * values_view.shape[1]
        + _canonical_columns_work(
            quotient_view.shape[0],
            values_view.shape[1],
        )
        + quotient_view.shape[0] * whitened_rank_cap**2
        + whitened_rank_cap**3,
        "quotient whitening",
    )
    values = _materialize_matrix(values_view, "columns")
    quotient = _materialize_matrix(quotient_view, "quotient_map")
    metric_values = _materialize_matrix(metric_view, "quotient_metric")
    whitening = hermitian_positive_whitener(metric_values)
    whitened = whitening._sqrt_metric @ quotient @ values
    basis = canonical_orthonormal_columns(
        whitened,
        absolute_threshold=absolute_threshold,
        expected_rank=expected_rank,
    )
    identity = np.eye(basis.shape[1], dtype=np.complex128)
    residual = _spectral_norm(basis.conj().T @ basis - identity)
    return QuotientWhitenedBasis(
        _whitened_basis=basis,
        quotient_rank=basis.shape[1],
        orthogonality_residual=residual,
        metric_minimum_eigenvalue=whitening.minimum_eigenvalue,
    )


__all__ = [
    "DEFAULT_HERMITIAN_TOLERANCE",
    "DEFAULT_ORTHOGONALITY_TOLERANCE",
    "LINALG_ARITHMETIC_WORK_CAP",
    "LINALG_ENTRY_CAP",
    "MetricWhitening",
    "QuotientWhitenedBasis",
    "canonical_orthonormal_columns",
    "hermitian_positive_whitener",
    "whiten_quotient_columns",
]
