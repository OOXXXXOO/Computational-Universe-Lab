"""Strict-local real-space family for M3′ Round 0 admission.

The production step contains only integer rolls and pointwise linear algebra.
Fourier symbols are used later by certificate functions, never by the step.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
import warnings

import numpy as np

from . import frozen


C_CONE = 0.5
Q_LEVELS = (0, 1, 2, 3, 4)
KAPPA_C_LEVELS = (0.0, 0.005, 0.01, 0.02, 0.04, 0.08)
PACKED_SYM = tuple((m, n) for m in range(4) for n in range(m, 4))
ETA = np.diag([-1.0, 1.0, 1.0, 1.0])


def _constraint_coefficients() -> np.ndarray:
    """Return B[nu, packed_component, spatial_axis] for C_sp."""

    coeff = np.zeros((4, 10, 3), dtype=float)
    for component, (m, n) in enumerate(PACKED_SYM):
        tensor = np.zeros((4, 4), dtype=float)
        tensor[m, n] = 1.0
        tensor[n, m] = 1.0
        trace = float(sum(ETA[a, a] * tensor[a, a] for a in range(4)))
        trace_reversed = tensor - 0.5 * ETA * trace
        for nu in range(4):
            for spatial_axis, i in enumerate((1, 2, 3)):
                coeff[nu, component, spatial_axis] = trace_reversed[i, nu]
    return coeff


C_SP_COEFF = _constraint_coefficients()


def _frozen_mod(name: str):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        return frozen.mod(name)


def negative_laplacian(field: np.ndarray) -> np.ndarray:
    """Nearest-neighbour -Δ with Chebyshev support radius one."""

    out = 6.0 * field
    for axis in (-3, -2, -1):
        out = out - np.roll(field, 1, axis=axis)
        out = out - np.roll(field, -1, axis=axis)
    return out


def apply_walk_stiffness(field: np.ndarray) -> np.ndarray:
    """Frozen R25 conservative walk stiffness, applied in real space."""

    return _frozen_mod("r25_realspace_step").aw_op(field)


def apply_r30_stiffness(field: np.ndarray) -> np.ndarray:
    """R30 placed-Yee stiffness c²(-Δ), with c=1/2."""

    return (C_CONE * C_CONE) * negative_laplacian(field)


def apply_counter_stiffness(field: np.ndarray, layer: int) -> np.ndarray:
    """One of four named quarter counter-kicks."""

    if layer not in range(4):
        raise ValueError(f"counter layer must be 0..3, got {layer!r}")
    return 0.25 * (
        apply_r30_stiffness(field) - apply_walk_stiffness(field)
    )


def _forward_difference(field: np.ndarray, spatial_axis: int) -> np.ndarray:
    axis = -3 + spatial_axis
    return np.roll(field, -1, axis=axis) - field


def _forward_difference_adjoint(
    field: np.ndarray, spatial_axis: int
) -> np.ndarray:
    axis = -3 + spatial_axis
    return np.roll(field, 1, axis=axis) - field


def constraint_spatial(h: np.ndarray) -> np.ndarray:
    """Placed spatial de-Donder row C_sp: packed h[10] -> zeta[4]."""

    if h.ndim != 4 or h.shape[0] != 10:
        raise ValueError("h must have shape (10, L, L, L)")
    out = np.zeros((4,) + h.shape[1:], dtype=h.dtype)
    for nu in range(4):
        for component in range(10):
            for spatial_axis in range(3):
                coefficient = C_SP_COEFF[nu, component, spatial_axis]
                if coefficient:
                    out[nu] += coefficient * _forward_difference(
                        h[component], spatial_axis
                    )
    return out


def constraint_spatial_adjoint(zeta: np.ndarray) -> np.ndarray:
    """Exact packed-field adjoint of :func:`constraint_spatial`."""

    if zeta.ndim != 4 or zeta.shape[0] != 4:
        raise ValueError("zeta must have shape (4, L, L, L)")
    out = np.zeros((10,) + zeta.shape[1:], dtype=zeta.dtype)
    for nu in range(4):
        for component in range(10):
            for spatial_axis in range(3):
                coefficient = C_SP_COEFF[nu, component, spatial_axis]
                if coefficient:
                    out[component] += coefficient * _forward_difference_adjoint(
                        zeta[nu], spatial_axis
                    )
    return out


@lru_cache(maxsize=1)
def floquet_retune_table() -> dict[int, dict[str, object]]:
    """Freeze dt_q from the actual q-stiffness at one walk-shell reference."""

    L_ref = 32
    k_units = np.array([1.0, 0.0, 0.0])
    k = k_units * (2.0 * math.pi / L_ref)
    r25 = _frozen_mod("r25_auxiliary_wilson_complex")
    r15 = _frozen_mod("r15_walk_dedonder")
    _, _, _, a_walk = r25.walk_data(k)
    a_r30 = float(
        C_CONE * C_CONE
        * sum((2.0 * math.sin(float(value) / 2.0)) ** 2 for value in k)
    )
    omega_target = float(r15.shell_omega(k, C_CONE))

    table: dict[int, dict[str, object]] = {}
    for q in Q_LEVELS:
        a_q = float(a_walk + (q / 4.0) * (a_r30 - a_walk))
        dt = math.sqrt(2.0 * (1.0 - math.cos(omega_target)) / a_q)
        argument = float(np.clip(1.0 - 0.5 * dt * dt * a_q, -1.0, 1.0))
        omega_measured = math.acos(argument)
        table[q] = {
            "dt": dt,
            "L_ref": L_ref,
            "k_units_ref": [1, 0, 0],
            "omega_target": omega_target,
            "omega_measured": omega_measured,
            "frequency_residual": abs(omega_measured - omega_target),
            "a_walk_ref": float(a_walk),
            "a_r30_ref": a_r30,
            "a_q_ref": a_q,
        }
    return table


@dataclass(frozen=True)
class LocalFamilyState:
    h: np.ndarray
    p_h: np.ndarray
    zeta: np.ndarray
    p_zeta: np.ndarray

    def __post_init__(self) -> None:
        fields = (self.h, self.p_h, self.zeta, self.p_zeta)
        expected_channels = (10, 10, 4, 4)
        spatial_shape = self.h.shape[1:] if self.h.ndim == 4 else ()
        if len(spatial_shape) != 3 or len(set(spatial_shape)) != 1:
            raise ValueError("state fields must live on one cubic 3D lattice")
        for field, channels in zip(fields, expected_channels):
            if field.ndim != 4 or field.shape != (channels,) + spatial_shape:
                raise ValueError("all state fields must share one lattice schema")

    @classmethod
    def zeros(
        cls, L: int, dtype: np.dtype = np.complex128
    ) -> "LocalFamilyState":
        if L < 3:
            raise ValueError("L must be at least 3")
        return cls(
            h=np.zeros((10, L, L, L), dtype=dtype),
            p_h=np.zeros((10, L, L, L), dtype=dtype),
            zeta=np.zeros((4, L, L, L), dtype=dtype),
            p_zeta=np.zeros((4, L, L, L), dtype=dtype),
        )

    @property
    def schema(self) -> tuple[tuple[int, ...], ...]:
        return tuple(
            field.shape
            for field in (self.h, self.p_h, self.zeta, self.p_zeta)
        )


def _half_potential_kick(
    state: LocalFamilyState,
    q: int,
    kappa_c: float,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    force_h = apply_walk_stiffness(state.h)
    for layer in range(q):
        force_h = force_h + apply_counter_stiffness(state.h, layer)
    force_zeta = apply_r30_stiffness(state.zeta)
    if kappa_c:
        force_h = force_h + kappa_c * constraint_spatial_adjoint(state.zeta)
        force_zeta = force_zeta + kappa_c * constraint_spatial(state.h)
    half_dt = 0.5 * dt
    return (
        state.p_h - half_dt * force_h,
        state.p_zeta - half_dt * force_zeta,
    )


@dataclass(frozen=True)
class LocalFamilyStep:
    q: int
    kappa_c: float
    dt: float

    def __post_init__(self) -> None:
        if self.q not in Q_LEVELS:
            raise ValueError(f"q must be one of {Q_LEVELS}")
        if self.kappa_c not in KAPPA_C_LEVELS:
            raise ValueError(f"kappa_c must be one of {KAPPA_C_LEVELS}")
        if not math.isfinite(self.dt) or self.dt <= 0:
            raise ValueError("dt must be finite and positive")

    def __call__(self, state: LocalFamilyState) -> LocalFamilyState:
        p_h, p_zeta = _half_potential_kick(
            state, self.q, self.kappa_c, self.dt
        )
        h = state.h + self.dt * p_h
        zeta = state.zeta + self.dt * p_zeta
        drifted = LocalFamilyState(h, p_h, zeta, p_zeta)
        p_h, p_zeta = _half_potential_kick(
            drifted, self.q, self.kappa_c, self.dt
        )
        return LocalFamilyState(h, p_h, zeta, p_zeta)


def realspace_step_factory(q: int, kappa_c: float) -> LocalFamilyStep:
    """Build one executable real-space macro-step; no k or FFT is accepted."""

    row = floquet_retune_table()[q]
    return LocalFamilyStep(q=q, kappa_c=kappa_c, dt=float(row["dt"]))


__all__ = [
    "C_SP_COEFF",
    "KAPPA_C_LEVELS",
    "LocalFamilyState",
    "LocalFamilyStep",
    "Q_LEVELS",
    "apply_counter_stiffness",
    "apply_r30_stiffness",
    "apply_walk_stiffness",
    "constraint_spatial",
    "constraint_spatial_adjoint",
    "floquet_retune_table",
    "negative_laplacian",
    "realspace_step_factory",
]
