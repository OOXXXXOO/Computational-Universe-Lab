"""Pure causal-subspace survival kernels for the V3-M0 instrument.

The evidence-facing Task 13 authority is intentionally not defined here yet.
It must obtain these three response arrays from matched, verified response
blocks and obtain the survival threshold from its verified calibration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .linalg import (
    LINALG_ARITHMETIC_WORK_CAP,
    LINALG_ENTRY_CAP,
    _canonical_columns_work,
    canonical_orthonormal_columns,
)


CAUSAL_HERMITIAN_TOLERANCE = 1e-12


@dataclass(frozen=True)
class CausalNumericalThresholds:
    """Numeric view mechanically copied from verified Task 11/13 calibration."""

    absolute_signal_threshold: float
    raw_noise_floor: float
    relative_gap_min: float
    survival_threshold: float
    survival_ambiguity_half_width: float

    def __post_init__(self) -> None:
        for field in (
            "absolute_signal_threshold",
            "raw_noise_floor",
            "relative_gap_min",
            "survival_threshold",
            "survival_ambiguity_half_width",
        ):
            value = getattr(self, field)
            if type(value) is not float or not math.isfinite(value):
                raise TypeError(f"{field} must be an exact finite float")
        if self.absolute_signal_threshold <= 0.0:
            raise ValueError("absolute_signal_threshold must be positive")
        if self.raw_noise_floor < 0.0:
            raise ValueError("raw_noise_floor must be nonnegative")
        if self.relative_gap_min < 1.0:
            raise ValueError("relative_gap_min must be at least one")
        if not 0.0 < self.survival_threshold < 1.0:
            raise ValueError("survival_threshold must lie strictly inside (0,1)")
        if self.survival_ambiguity_half_width <= 0.0:
            raise ValueError("survival_ambiguity_half_width must be positive")
        if (
            self.survival_threshold - self.survival_ambiguity_half_width < 0.0
            or self.survival_threshold + self.survival_ambiguity_half_width > 1.0
        ):
            raise ValueError("survival ambiguity band must lie inside [0,1]")


@dataclass(frozen=True)
class CausalSpectrum:
    survival_spectrum: tuple[float, ...]
    epsilon_dof: Optional[float]
    epsilon_cont: float
    chi_extra: float
    kappa_map: Optional[float]
    d_proc_sq: Optional[float]
    gain_ratio: Optional[float]
    phase_shift: Optional[float]
    ambiguous: bool
    actual_rank: int
    ablated_rank: int
    ablated_all_rank: int
    k_surv_hermitian_residual: float


def _response_matrix_header(value: object, field: str) -> np.ndarray:
    if type(value) is not np.ndarray:
        raise TypeError(f"{field} must be an exact numpy.ndarray")
    if value.ndim != 2 or value.shape[0] <= 0 or value.shape[1] <= 0:
        raise ValueError(f"{field} must be a non-empty matrix")
    if value.shape[0] * value.shape[1] > LINALG_ENTRY_CAP:
        raise ValueError(f"{field} exceeds the matrix resource cap")
    if value.dtype != np.dtype(np.complex128):
        raise TypeError(f"{field} must have complex128 dtype")
    return value


def _materialize_response_matrix(value: np.ndarray, field: str) -> np.ndarray:
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{field} must be finite")
    return np.array(value, dtype=np.complex128, copy=True, order="C")


def _max_abs(value: np.ndarray) -> float:
    if value.size == 0:
        return 0.0
    return float(np.max(np.abs(value)))


def _basis_decomposition_work(values: np.ndarray) -> int:
    maximum_rank = min(values.shape)
    return values.shape[0] * values.shape[1] * maximum_rank + _canonical_columns_work(
        *values.shape
    )


def _canonical_unit_interval(value: float, field: str) -> float:
    result = float(value)
    if (
        not math.isfinite(result)
        or result < -CAUSAL_HERMITIAN_TOLERANCE
        or result > 1.0 + CAUSAL_HERMITIAN_TOLERANCE
    ):
        raise ValueError(f"{field} is outside the audited unit interval")
    return float(min(1.0, max(0.0, result)))


def _canonical_unit_interval_array(values: np.ndarray, field: str) -> np.ndarray:
    if not bool(np.all(np.isfinite(values))) or bool(
        np.any(values < -CAUSAL_HERMITIAN_TOLERANCE)
        or np.any(values > 1.0 + CAUSAL_HERMITIAN_TOLERANCE)
    ):
        raise ValueError(f"{field} lies outside the audited unit interval")
    return np.clip(values, 0.0, 1.0).astype(np.float64, copy=False)


def _active_basis(
    values: np.ndarray,
    thresholds: CausalNumericalThresholds,
    field: str,
) -> np.ndarray:
    work = _basis_decomposition_work(values)
    if work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError(f"{field} exceeds the arithmetic work cap")
    singular_values = np.linalg.svd(
        values,
        compute_uv=False,
        full_matrices=False,
    )
    if not bool(np.all(np.isfinite(singular_values))):
        raise ValueError(f"{field} singular values are non-finite")
    numerical_floor = (
        np.finfo(np.float64).eps * max(values.shape) * float(singular_values[0]) * 64.0
    )
    signal_line = max(
        thresholds.absolute_signal_threshold,
        thresholds.raw_noise_floor * thresholds.relative_gap_min,
    )
    if bool(
        np.any(
            (singular_values > thresholds.raw_noise_floor)
            & (singular_values < signal_line)
        )
    ):
        raise ValueError(f"{field} lies in the calibrated signal grey band")
    if numerical_floor > signal_line and bool(
        np.any((singular_values >= signal_line) & (singular_values < numerical_floor))
    ):
        raise ValueError(f"{field} numerical rank is unresolved above signal line")
    effective_threshold = float(max(signal_line, numerical_floor))
    rank = int(np.count_nonzero(singular_values >= effective_threshold))
    if 0 < rank < len(singular_values):
        inactive = max(
            float(singular_values[rank]),
            thresholds.raw_noise_floor,
        )
        relative_gap = (
            math.inf if inactive == 0.0 else float(singular_values[rank - 1]) / inactive
        )
        if relative_gap < thresholds.relative_gap_min:
            raise ValueError(f"{field} does not pass the relative rank gap")
    return canonical_orthonormal_columns(
        values,
        absolute_threshold=effective_threshold,
        expected_rank=rank,
    )


def _scaled_frobenius(value: np.ndarray) -> tuple[float, float]:
    scale = _max_abs(value)
    if scale == 0.0:
        return 0.0, 0.0
    scaled = value / scale
    norm_sq = float(np.sum(np.abs(scaled) ** 2))
    if not math.isfinite(norm_sq) or norm_sq <= 0.0:
        raise ValueError("scaled Frobenius norm left the finite range")
    return scale, norm_sq


def compute_causal_spectrum(
    actual_on_actual_sector: np.ndarray,
    ablated_on_actual_sector: np.ndarray,
    ablated_on_full_source: np.ndarray,
    *,
    thresholds: CausalNumericalThresholds,
) -> CausalSpectrum:
    """Measure matched-ablation survival in the actual curvature sector."""

    actual_view = _response_matrix_header(
        actual_on_actual_sector,
        "actual_on_actual_sector",
    )
    ablated_view = _response_matrix_header(
        ablated_on_actual_sector,
        "ablated_on_actual_sector",
    )
    ablated_all_view = _response_matrix_header(
        ablated_on_full_source,
        "ablated_on_full_source",
    )
    if ablated_view.shape != actual_view.shape:
        raise ValueError("matched response shape mismatch")
    if ablated_all_view.shape[0] != actual_view.shape[0]:
        raise ValueError("full-source response observer dimension mismatch")
    if type(thresholds) is not CausalNumericalThresholds:
        raise TypeError("thresholds must be exact calibrated numerical values")

    observer_dimension = actual_view.shape[0]
    actual_rank_cap = min(actual_view.shape)
    ablated_rank_cap = min(ablated_view.shape)
    ablated_all_rank_cap = min(ablated_all_view.shape)
    aggregate_work = (
        _basis_decomposition_work(actual_view)
        + _basis_decomposition_work(ablated_view)
        + _basis_decomposition_work(ablated_all_view)
        + observer_dimension * ablated_rank_cap * actual_rank_cap
        + ablated_rank_cap * actual_rank_cap**2
        + 2 * actual_rank_cap**3
        + observer_dimension * actual_rank_cap * ablated_all_rank_cap
        + observer_dimension * (2 * actual_view.shape[1] + ablated_all_view.shape[1])
    )
    if aggregate_work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError("causal aggregate calculation exceeds the arithmetic work cap")

    actual = _materialize_response_matrix(
        actual_view,
        "actual_on_actual_sector",
    )
    ablated = _materialize_response_matrix(
        ablated_view,
        "ablated_on_actual_sector",
    )
    ablated_all = _materialize_response_matrix(
        ablated_all_view,
        "ablated_on_full_source",
    )

    actual_basis = _active_basis(
        actual,
        thresholds,
        "actual response",
    )
    if actual_basis.shape[1] != actual.shape[1]:
        raise ValueError("actual response lost a preregistered curvature mode")
    ablated_basis = _active_basis(
        ablated,
        thresholds,
        "ablated response",
    )
    ablated_all_basis = _active_basis(
        ablated_all,
        thresholds,
        "full-source ablated response",
    )

    if ablated_basis.shape[1] == 0:
        k_surv = np.zeros(
            (actual_basis.shape[1], actual_basis.shape[1]),
            dtype=np.complex128,
        )
    else:
        overlap = ablated_basis.conj().T @ actual_basis
        k_surv = overlap.conj().T @ overlap
    hermitian_residual = float(np.linalg.norm(k_surv - k_surv.conj().T, ord=2))
    if (
        not math.isfinite(hermitian_residual)
        or hermitian_residual > CAUSAL_HERMITIAN_TOLERANCE
    ):
        raise ValueError("K_surv exceeds the Hermitian residual tolerance")

    survival = _canonical_unit_interval_array(
        np.linalg.eigvalsh(k_surv),
        "K_surv eigenvalue",
    )
    ambiguous = bool(
        np.any(
            np.abs(survival - thresholds.survival_threshold)
            < thresholds.survival_ambiguity_half_width
        )
    )
    epsilon_dof = (
        None
        if ambiguous
        else float(
            np.count_nonzero(survival >= thresholds.survival_threshold) / len(survival)
        )
    )
    epsilon_cont = _canonical_unit_interval(
        float(np.mean(survival)),
        "continuous survival",
    )

    if ablated_all_basis.shape[1] == 0:
        chi_extra = 0.0
    else:
        shared_weight = float(
            np.linalg.norm(
                actual_basis.conj().T @ ablated_all_basis,
                ord="fro",
            )
            ** 2
        )
        chi_extra = float(1.0 - shared_weight / ablated_all_basis.shape[1])
        chi_extra = _canonical_unit_interval(
            chi_extra,
            "full-source extra-mode fraction",
        )

    ablated_scale, ablated_norm_scaled = _scaled_frobenius(ablated)
    actual_scale, actual_norm_scaled = _scaled_frobenius(actual)
    if ablated_scale == 0.0:
        kappa_map = None
        d_proc_sq = None
        gain_ratio = None
        phase_shift = None
    else:
        ablated_scaled = ablated / ablated_scale
        actual_scaled = actual / actual_scale
        inner = complex(np.vdot(ablated_scaled, actual_scaled))
        kappa_map = _canonical_unit_interval(
            float(abs(inner) ** 2 / (ablated_norm_scaled * actual_norm_scaled)),
            "Procrustes overlap",
        )
        d_proc_sq = _canonical_unit_interval(
            float(1.0 - kappa_map),
            "Procrustes squared distance",
        )
        log_gain = (
            math.log(ablated_scale)
            - math.log(actual_scale)
            + 0.5 * (math.log(ablated_norm_scaled) - math.log(actual_norm_scaled))
        )
        if abs(log_gain) > math.log(np.finfo(np.float64).max):
            raise ValueError("Procrustes gain ratio left the finite range")
        gain_ratio = float(math.exp(log_gain))
        phase_shift = (
            None if abs(inner) == 0.0 else float(math.atan2(inner.imag, inner.real))
        )

    return CausalSpectrum(
        survival_spectrum=tuple(float(value) for value in survival),
        epsilon_dof=epsilon_dof,
        epsilon_cont=epsilon_cont,
        chi_extra=chi_extra,
        kappa_map=kappa_map,
        d_proc_sq=d_proc_sq,
        gain_ratio=gain_ratio,
        phase_shift=phase_shift,
        ambiguous=ambiguous,
        actual_rank=actual_basis.shape[1],
        ablated_rank=ablated_basis.shape[1],
        ablated_all_rank=ablated_all_basis.shape[1],
        k_surv_hermitian_residual=hermitian_residual,
    )


__all__ = [
    "CAUSAL_HERMITIAN_TOLERANCE",
    "CausalNumericalThresholds",
    "CausalSpectrum",
    "compute_causal_spectrum",
]
