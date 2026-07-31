"""Deterministic metric-aware linear algebra for the V3-M0 instrument.

The public routines in this module are numerical kernels, not evidence
authorities.  They reject non-Hermitian or non-positive metrics before any
whitening and require an explicit quotient map when the original observer
space contains metric-null directions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


LINALG_ENTRY_CAP = 16_777_216
LINALG_ARITHMETIC_WORK_CAP = 2_000_000_000
DEFAULT_HERMITIAN_TOLERANCE = 1e-12
DEFAULT_ORTHOGONALITY_TOLERANCE = 1e-12


def _matrix(
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
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{field} must contain only finite values")
    return np.asarray(value, dtype=np.complex128)


def _nonnegative_finite(value: object, field: str) -> float:
    if type(value) not in (float, int):
        raise TypeError(f"{field} must be a real scalar")
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return result


def _max_abs(value: np.ndarray) -> float:
    if value.size == 0:
        return 0.0
    return float(np.max(np.abs(value)))


def _require_work_within_cap(work: int, field: str) -> None:
    if work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError(f"{field} exceeds the arithmetic work cap")


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
    values = _matrix(metric, "metric", square=True)
    _require_work_within_cap(
        values.shape[0] ** 3,
        "metric eigendecomposition",
    )
    hermitian_residual = _max_abs(values - values.conj().T)
    if hermitian_residual > tolerance:
        raise ValueError("metric exceeds the Hermitian residual tolerance")

    eigenvalues, eigenvectors = np.linalg.eigh(values)
    minimum_eigenvalue = float(eigenvalues[0])
    if minimum_eigenvalue <= minimum_positive:
        raise ValueError("metric is not strictly positive definite")

    roots = np.sqrt(eigenvalues)
    inverse_roots = 1.0 / roots
    sqrt_metric = (eigenvectors @ np.diag(roots) @ eigenvectors.conj().T).astype(
        np.complex128, copy=False
    )
    inverse_sqrt = (
        eigenvectors @ np.diag(inverse_roots) @ eigenvectors.conj().T
    ).astype(np.complex128, copy=False)
    identity = np.eye(values.shape[0], dtype=np.complex128)
    reconstruction_residual = _max_abs(sqrt_metric.conj().T @ sqrt_metric - values)
    inverse_residual = _max_abs(inverse_sqrt @ sqrt_metric - identity)
    if reconstruction_residual > tolerance or inverse_residual > tolerance:
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
    values = _matrix(columns, "columns")
    _require_work_within_cap(
        values.shape[0] * values.shape[1] * min(values.shape),
        "column-space decomposition",
    )
    if expected_rank is not None:
        if type(expected_rank) is not int or expected_rank < 0:
            raise ValueError("expected_rank must be a nonnegative exact int")
        if expected_rank > min(values.shape):
            raise ValueError("expected_rank exceeds the matrix dimensions")

    left, singular_values, _ = np.linalg.svd(
        values,
        full_matrices=False,
    )
    rank = int(np.count_nonzero(singular_values >= threshold))
    if expected_rank is not None and rank != expected_rank:
        raise ValueError("thresholded column rank differs from expected_rank")
    if rank == 0:
        return np.zeros((values.shape[0], 0), dtype=np.complex128)

    selected = left[:, :rank]
    basis: list[np.ndarray] = []
    axis_threshold = np.finfo(np.float64).eps * max(values.shape) * 64.0
    for axis in range(values.shape[0]):
        # Apply the projector to one coordinate axis without materializing the
        # potentially enormous row_count × row_count projector.
        candidate = selected @ np.conjugate(selected[axis, :])
        for _ in range(2):
            for prior in basis:
                candidate -= prior * np.vdot(prior, candidate)
        norm = float(np.linalg.norm(candidate))
        if norm <= axis_threshold:
            continue
        basis.append(_canonical_phase(candidate / norm))
        if len(basis) == rank:
            break
    if len(basis) != rank:
        raise ValueError("canonical basis construction lost thresholded rank")
    result = np.column_stack(basis).astype(np.complex128, copy=False)
    identity = np.eye(rank, dtype=np.complex128)
    orthogonality_residual = _max_abs(result.conj().T @ result - identity)
    projector_residual = _max_abs(selected - result @ (result.conj().T @ selected))
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

    values = _matrix(columns, "columns")
    quotient = _matrix(quotient_map, "quotient_map")
    if quotient.shape[1] != values.shape[0]:
        raise ValueError("quotient_map source dimension mismatch")
    metric_values = _matrix(
        quotient_metric,
        "quotient_metric",
        square=True,
    )
    if metric_values.shape[0] != quotient.shape[0]:
        raise ValueError("quotient_metric dimension mismatch")
    _require_work_within_cap(
        quotient.shape[0] * quotient.shape[1] * values.shape[1]
        + quotient.shape[0] ** 2 * values.shape[1],
        "quotient whitening",
    )
    whitening = hermitian_positive_whitener(metric_values)
    whitened = whitening._sqrt_metric @ quotient @ values
    basis = canonical_orthonormal_columns(
        whitened,
        absolute_threshold=absolute_threshold,
        expected_rank=expected_rank,
    )
    identity = np.eye(basis.shape[1], dtype=np.complex128)
    residual = _max_abs(basis.conj().T @ basis - identity)
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
