"""Pure R37/D-M2-6 sigma fitting kernels for V3-M0.

This module deliberately contains no geometry authority issuer.  Task 15's
evidence boundary may call these deterministic kernels only after it has
obtained geometry samples from verified response blocks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np


ALPHA_GRID = tuple(float(value) for value in np.arange(0.05, 4.001, 0.01))
SIGMA_MAX_POINTS = 2_048
SIGMA_LSTSQ_CALL_CAP = 50_000
SIGMA_MAX_K = math.sqrt(3.0) * math.pi
SIGMA_MAX_GEOMETRY_SCALE = 1.0 + 1e-12
DM26_DELTA_AIC_MIN = 2.0
DM26_HIGH_ORDER_COLLAPSE = 5.0
DM26_HALF_WINDOW_COLLAPSE = 2.0
_RSS_FLOOR = 1e-300


@dataclass(frozen=True)
class ConstantFit:
    A: float
    sigma_A: float
    rss: float
    aic: float
    sample_count: int
    parameter_count: int = 1


@dataclass(frozen=True)
class PowerFit:
    A: float
    sigma_A: Optional[float]
    B: float
    sigma_B: Optional[float]
    alpha: float
    sigma_alpha: Optional[float]
    rss: float
    aic: float
    sample_count: int
    parameter_count: int = 3


@dataclass(frozen=True)
class HighOrderFit:
    A: float
    B: float
    C: float
    alpha: float
    rss: float
    aic: float
    sample_count: int
    parameter_count: int = 4


@dataclass(frozen=True)
class LeaveOneOutPowerFit:
    dropped_k: float
    fit: PowerFit


@dataclass(frozen=True)
class DM26Decision:
    power_full: PowerFit
    high_order: HighOrderFit
    delta_aic_power_minus_high: float
    high_order_aic_supported: bool
    high_order_intercept_collapsed: bool
    high_order_pollution: bool
    A_half: float
    alpha_half: float
    half_window_pollution: bool
    both_pollution: bool


@dataclass(frozen=True)
class DM26ControlAudit:
    control_id: str
    family: str
    expected_pollution: bool
    decision: DM26Decision
    matches_expected: bool


@dataclass(frozen=True)
class SigmaResult:
    geometry_manifest_id: str
    deterministic: bool
    model_winner: Literal["constant", "power"]
    constant_fit: ConstantFit
    power_fit: PowerFit
    high_order_fit: HighOrderFit
    A: float
    alpha: Optional[float]
    sigma_A: Optional[float]
    sigma_alpha: Optional[float]
    delta_aic: float
    loo: tuple[LeaveOneOutPowerFit, ...]
    fit_window: tuple[float, ...]
    expanded_window: Optional[tuple[float, ...]]
    direction: Literal["geometry-manifest-defined"]
    alpha_identifiable: bool
    zero_consistent: bool
    zero_test: Literal["dm26-double-test", "two-sigma"]
    dm26_decision: Optional[DM26Decision]
    dm26_controls: tuple[DM26ControlAudit, ...]


def _series(
    k_values: object,
    values: object,
    *,
    minimum_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    if type(k_values) is not np.ndarray or type(values) is not np.ndarray:
        raise TypeError("fit inputs must be exact numpy.ndarray values")
    if k_values.ndim != 1 or values.ndim != 1:
        raise ValueError("fit inputs must be one-dimensional")
    if k_values.dtype != np.dtype(np.float64) or values.dtype != np.dtype(np.float64):
        raise TypeError("fit inputs must have float64 dtype")
    if len(k_values) != len(values):
        raise ValueError("fit inputs must have equal length")
    if len(k_values) < minimum_points:
        raise ValueError(f"fit requires at least {minimum_points} observations")
    if len(k_values) > SIGMA_MAX_POINTS:
        raise ValueError("fit point count exceeds the resource cap")
    if not bool(np.all(np.isfinite(k_values))) or not bool(np.all(np.isfinite(values))):
        raise ValueError("fit inputs must be finite")
    if bool(np.any(k_values <= 0.0)):
        raise ValueError("k values must be strictly positive")
    if bool(np.any(k_values > SIGMA_MAX_K)):
        raise ValueError("k values exceed the frozen Brillouin-domain bound")
    if len(np.unique(k_values)) != len(k_values):
        raise ValueError("k values must be distinct")
    if bool(np.any(values < 0.0)):
        raise ValueError("geometry scale values must be nonnegative")
    if bool(np.any(values > SIGMA_MAX_GEOMETRY_SCALE)):
        raise ValueError("geometry scale values exceed the singular-value bound")
    return (
        np.array(k_values, dtype=np.float64, copy=True, order="C"),
        np.array(values, dtype=np.float64, copy=True, order="C"),
    )


def _aic(rss: float, sample_count: int, parameter_count: int) -> float:
    return float(
        sample_count * math.log(max(rss, _RSS_FLOOR) / sample_count)
        + 2 * parameter_count
    )


def fit_constant(k_values: np.ndarray, values: np.ndarray) -> ConstantFit:
    x, y = _series(k_values, values, minimum_points=4)
    del x
    sample_count = len(y)
    intercept = float(np.mean(y))
    rss = float(np.sum((y - intercept) ** 2))
    sigma = float(np.std(y, ddof=1) / math.sqrt(sample_count))
    return ConstantFit(
        A=intercept,
        sigma_A=sigma,
        rss=rss,
        aic=_aic(rss, sample_count, 1),
        sample_count=sample_count,
    )


def _fit_power(
    x: np.ndarray,
    y: np.ndarray,
) -> PowerFit:
    sample_count = len(y)
    best: Optional[tuple[float, float, float, float]] = None
    for alpha in ALPHA_GRID:
        design = np.column_stack((np.ones(sample_count), x**alpha))
        coefficients, _, _, _ = np.linalg.lstsq(
            design,
            y,
            rcond=None,
        )
        residual = y - design @ coefficients
        rss = float(np.sum(residual**2))
        if best is None or rss < best[0]:
            best = (
                rss,
                alpha,
                float(coefficients[0]),
                float(coefficients[1]),
            )
    assert best is not None
    rss, alpha, intercept, amplitude = best
    jacobian = np.column_stack(
        (
            np.ones(sample_count),
            x**alpha,
            amplitude * np.log(x) * (x**alpha),
        )
    )
    variance = rss / max(sample_count - 3, 1)
    try:
        covariance = variance * np.linalg.inv(jacobian.T @ jacobian)
        if not bool(np.all(np.isfinite(covariance))):
            raise np.linalg.LinAlgError("covariance is non-finite")
        diagonal = np.real(np.diag(covariance))
        if bool(np.any(diagonal < 0.0)):
            raise np.linalg.LinAlgError("covariance has a negative diagonal")
        sigma_A = float(math.sqrt(diagonal[0]))
        sigma_B = float(math.sqrt(diagonal[1]))
        sigma_alpha = float(math.sqrt(diagonal[2]))
    except np.linalg.LinAlgError:
        sigma_A = None
        sigma_B = None
        sigma_alpha = None
    return PowerFit(
        A=intercept,
        sigma_A=sigma_A,
        B=amplitude,
        sigma_B=sigma_B,
        alpha=alpha,
        sigma_alpha=sigma_alpha,
        rss=rss,
        aic=_aic(rss, sample_count, 3),
        sample_count=sample_count,
    )


def fit_power(k_values: np.ndarray, values: np.ndarray) -> PowerFit:
    x, y = _series(k_values, values, minimum_points=4)
    return _fit_power(x, y)


def _fit_high_order(
    x: np.ndarray,
    y: np.ndarray,
) -> HighOrderFit:
    sample_count = len(y)
    best: Optional[tuple[float, float, float, float, float]] = None
    for alpha in ALPHA_GRID:
        design = np.column_stack(
            (
                np.ones(sample_count),
                x**alpha,
                x ** (alpha + 2.0),
            )
        )
        coefficients, _, _, _ = np.linalg.lstsq(
            design,
            y,
            rcond=None,
        )
        residual = y - design @ coefficients
        rss = float(np.sum(residual**2))
        if best is None or rss < best[0]:
            best = (
                rss,
                alpha,
                float(coefficients[0]),
                float(coefficients[1]),
                float(coefficients[2]),
            )
    assert best is not None
    rss, alpha, intercept, amplitude, high_amplitude = best
    return HighOrderFit(
        A=intercept,
        B=amplitude,
        C=high_amplitude,
        alpha=alpha,
        rss=rss,
        aic=_aic(rss, sample_count, 4),
        sample_count=sample_count,
    )


def fit_high_order(
    k_values: np.ndarray,
    values: np.ndarray,
) -> HighOrderFit:
    x, y = _series(k_values, values, minimum_points=4)
    return _fit_high_order(x, y)


def leave_one_out_power(
    k_values: np.ndarray,
    values: np.ndarray,
) -> tuple[LeaveOneOutPowerFit, ...]:
    x, y = _series(k_values, values, minimum_points=4)
    if len(x) * len(ALPHA_GRID) > SIGMA_LSTSQ_CALL_CAP:
        raise ValueError("leave-one-out fit exceeds the arithmetic work cap")
    return tuple(
        LeaveOneOutPowerFit(
            dropped_k=float(x[index]),
            fit=_fit_power(
                np.delete(x, index),
                np.delete(y, index),
            ),
        )
        for index in range(len(x))
    )


def run_dm26(k_values: np.ndarray, values: np.ndarray) -> DM26Decision:
    x, y = _series(k_values, values, minimum_points=4)
    power = _fit_power(x, y)
    high = _fit_high_order(x, y)
    delta_aic = float(power.aic - high.aic)
    high_aic = bool(delta_aic >= DM26_DELTA_AIC_MIN)
    high_collapse = bool(abs(high.A) <= abs(power.A) / DM26_HIGH_ORDER_COLLAPSE)
    selected = np.argsort(x)[:3]
    half = _fit_power(x[selected], y[selected])
    half_collapse = bool(abs(half.A) <= abs(power.A) / DM26_HALF_WINDOW_COLLAPSE)
    return DM26Decision(
        power_full=power,
        high_order=high,
        delta_aic_power_minus_high=delta_aic,
        high_order_aic_supported=high_aic,
        high_order_intercept_collapsed=high_collapse,
        high_order_pollution=bool(high_aic and high_collapse),
        A_half=half.A,
        alpha_half=half.alpha,
        half_window_pollution=half_collapse,
        both_pollution=bool(high_aic and high_collapse and half_collapse),
    )


def dm26_controls() -> tuple[DM26ControlAudit, ...]:
    """Run the frozen eight-control teeth check before deterministic exclusion."""

    x = np.asarray(
        [2.0 * math.pi / size for size in (16, 24, 32, 48)],
        dtype=np.float64,
    )
    controls = (
        ("A1", "clean-zero", 0.0, 2.0, -0.05, +0.01, True),
        ("A2", "clean-zero", 0.0, 2.0, -0.02, -0.005, True),
        ("A3", "clean-zero", 0.0, 2.0, -0.10, +0.02, True),
        ("A4", "clean-zero", 0.0, 1.9, -0.05, +0.01, True),
        ("B1", "true-floor", -1.2e-4, 2.0, -0.05, +0.01, False),
        ("B2", "true-floor", +1.2e-4, 2.0, -0.05, +0.01, False),
        ("B3", "true-floor", -2.4e-4, 2.0, -0.02, -0.005, False),
        ("B4", "true-floor", -1.2e-4, 1.9, -0.05, +0.01, False),
    )
    output = []
    for (
        control_id,
        family,
        intercept,
        alpha,
        high_amplitude,
        tail_amplitude,
        expected,
    ) in controls:
        y = (
            intercept
            + 0.236 * x**alpha
            + high_amplitude * x ** (alpha + 2.0)
            + tail_amplitude * x ** (alpha + 4.0)
        ).astype(np.float64)
        decision = run_dm26(x, y)
        output.append(
            DM26ControlAudit(
                control_id=control_id,
                family=family,
                expected_pollution=expected,
                decision=decision,
                matches_expected=(decision.both_pollution is expected),
            )
        )
    return tuple(output)


def _geometry_manifest_id(value: object) -> str:
    if type(value) is not str:
        raise TypeError("geometry_manifest_id must be an exact string")
    if not value or len(value.encode("utf-8")) > 256:
        raise ValueError("geometry_manifest_id has invalid length")
    if any(character.isspace() or not character.isprintable() for character in value):
        raise ValueError("geometry_manifest_id must be a printable token")
    return value


def _power_fit_is_finite(fit: PowerFit) -> bool:
    if fit.sigma_A is None or fit.sigma_B is None or fit.sigma_alpha is None:
        return False
    return all(
        math.isfinite(value)
        for value in (
            fit.A,
            fit.sigma_A,
            fit.B,
            fit.sigma_B,
            fit.alpha,
            fit.sigma_alpha,
            fit.rss,
            fit.aic,
        )
    )


def fit_sigma(
    k_values: np.ndarray,
    g_max: np.ndarray,
    geometry_manifest_id: str,
    *,
    deterministic: bool,
) -> SigmaResult:
    """Fit the frozen constant/power models and the applicable zero test.

    This is the pure numerical layer.  The later geometry authority must bind
    ``geometry_manifest_id`` to verified response-block evidence before
    serialising this result.
    """

    manifest_id = _geometry_manifest_id(geometry_manifest_id)
    if type(deterministic) is not bool:
        raise TypeError("deterministic must be an exact bool")
    x, y = _series(k_values, g_max, minimum_points=4)
    # Main power/high-order (2), LOO power (n), and, on the
    # deterministic branch, nine DM26 runs × three fits each.
    fit_count = len(x) + 2 + (27 if deterministic else 0)
    if fit_count * len(ALPHA_GRID) > SIGMA_LSTSQ_CALL_CAP:
        raise ValueError("full sigma fit exceeds the arithmetic work cap")
    constant = fit_constant(x, y)
    power = _fit_power(x, y)
    high_order = _fit_high_order(x, y)
    loo = tuple(
        LeaveOneOutPowerFit(
            dropped_k=float(x[index]),
            fit=_fit_power(np.delete(x, index), np.delete(y, index)),
        )
        for index in range(len(x))
    )
    delta_aic = float(constant.aic - power.aic)
    power_wins = bool(power.aic < constant.aic)
    decisive_power = bool(delta_aic >= DM26_DELTA_AIC_MIN)
    saturated = bool(
        float(np.ptp(y))
        <= np.finfo(np.float64).eps * max(1.0, float(np.max(np.abs(y)))) * 64.0
    )
    loo_finite = all(_power_fit_is_finite(row.fit) for row in loo)
    grid_boundary = power.alpha in (ALPHA_GRID[0], ALPHA_GRID[-1])
    alpha_identifiable = bool(
        power_wins
        and decisive_power
        and not saturated
        and loo_finite
        and not grid_boundary
    )

    if power_wins:
        selected_A = power.A
        selected_sigma_A = power.sigma_A
    else:
        selected_A = constant.A
        selected_sigma_A = constant.sigma_A

    exact_zero = bool(np.all(y == 0.0))
    if deterministic:
        controls = dm26_controls()
        controls_have_teeth = all(row.matches_expected for row in controls)
        decision = run_dm26(x, y)
        zero_consistent = bool(
            controls_have_teeth and (exact_zero or decision.both_pollution)
        )
        zero_test: Literal["dm26-double-test", "two-sigma"] = "dm26-double-test"
    else:
        controls = ()
        decision = None
        zero_consistent = bool(
            selected_sigma_A is not None
            and math.isfinite(selected_sigma_A)
            and abs(selected_A) <= 2.0 * selected_sigma_A
        )
        zero_test = "two-sigma"

    return SigmaResult(
        geometry_manifest_id=manifest_id,
        deterministic=deterministic,
        model_winner="power" if power_wins else "constant",
        constant_fit=constant,
        power_fit=power,
        high_order_fit=high_order,
        A=selected_A,
        alpha=power.alpha if alpha_identifiable else None,
        sigma_A=selected_sigma_A,
        sigma_alpha=power.sigma_alpha if alpha_identifiable else None,
        delta_aic=delta_aic,
        loo=loo,
        fit_window=tuple(float(value) for value in x),
        expanded_window=None,
        direction="geometry-manifest-defined",
        alpha_identifiable=alpha_identifiable,
        zero_consistent=zero_consistent,
        zero_test=zero_test,
        dm26_decision=decision,
        dm26_controls=controls,
    )


__all__ = [
    "ALPHA_GRID",
    "DM26ControlAudit",
    "DM26Decision",
    "DM26_DELTA_AIC_MIN",
    "DM26_HALF_WINDOW_COLLAPSE",
    "DM26_HIGH_ORDER_COLLAPSE",
    "HighOrderFit",
    "LeaveOneOutPowerFit",
    "PowerFit",
    "SIGMA_MAX_POINTS",
    "SIGMA_LSTSQ_CALL_CAP",
    "SIGMA_MAX_GEOMETRY_SCALE",
    "SIGMA_MAX_K",
    "SigmaResult",
    "ConstantFit",
    "dm26_controls",
    "fit_constant",
    "fit_high_order",
    "fit_power",
    "fit_sigma",
    "leave_one_out_power",
    "run_dm26",
]
