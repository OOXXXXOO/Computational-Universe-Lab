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
C_SP_NORMALIZATION = 0.5
DECLARED_COMPOSITION_RADIUS = 4
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
        mismatch = state.zeta - C_SP_NORMALIZATION * constraint_spatial(state.h)
        force_h = force_h - (
            kappa_c
            * C_SP_NORMALIZATION
            * constraint_spatial_adjoint(mismatch)
        )
        force_zeta = force_zeta + kappa_c * mismatch
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


def _response_radius(
    fields: tuple[np.ndarray, ...],
    center: int,
    relative_threshold: float = 1e-13,
) -> int:
    magnitude = np.maximum.reduce(
        [np.max(np.abs(field), axis=0) for field in fields]
    )
    peak = float(magnitude.max())
    if peak == 0.0:
        return 0
    active = np.argwhere(magnitude > relative_threshold * peak)
    L = magnitude.shape[0]
    radius = 0
    for coordinate in active:
        distances = []
        for value in coordinate:
            raw = abs(int(value) - center)
            distances.append(min(raw, L - raw))
        radius = max(radius, max(distances))
    return radius


def measure_support_radii(
    L_values: tuple[int, ...] = (17, 21),
) -> dict[str, object]:
    """Measure one-step Chebyshev support without using a Fourier transform."""

    probes: list[dict[str, object]] = []
    per_L: dict[str, int] = {}
    for L in L_values:
        center = L // 2
        radii: list[int] = []
        for q, kappa_c in ((0, 0.0), (0, 0.08), (4, 0.0), (4, 0.08)):
            for input_field, channels in (
                ("h", 10),
                ("p_h", 10),
                ("zeta", 4),
                ("p_zeta", 4),
            ):
                state = LocalFamilyState.zeros(L)
                target = getattr(state, input_field)
                target[:, center, center, center] = (
                    np.arange(1, channels + 1) * (1.0 + 0.173j)
                )
                stepped = realspace_step_factory(q, kappa_c)(state)
                radius = _response_radius(
                    (stepped.h, stepped.p_h, stepped.zeta, stepped.p_zeta),
                    center,
                )
                radii.append(radius)
                probes.append(
                    {
                        "L": L,
                        "q": q,
                        "kappa_c": kappa_c,
                        "input_field": input_field,
                        "radius": radius,
                    }
                )
        per_L[str(L)] = max(radii)
    unique = set(per_L.values())
    return {
        "per_L": per_L,
        "max_radius": max(per_L.values()),
        "independent_of_L": len(unique) == 1,
        "relative_threshold": 1e-13,
        "probes": probes,
    }


def _relative_adjoint_residual(
    lhs: complex,
    rhs: complex,
) -> float:
    return float(abs(lhs - rhs) / max(abs(lhs), abs(rhs), 1e-300))


def adjoint_certificate(L: int = 7, seed: int = 19) -> dict[str, object]:
    """Measure all adjoint pairs used by the potential kick."""

    rng = np.random.default_rng(seed)
    h1 = rng.normal(size=(10, L, L, L)) + 1j * rng.normal(
        size=(10, L, L, L)
    )
    h2 = rng.normal(size=(10, L, L, L)) + 1j * rng.normal(
        size=(10, L, L, L)
    )
    zeta = rng.normal(size=(4, L, L, L)) + 1j * rng.normal(
        size=(4, L, L, L)
    )

    constraint_residual = _relative_adjoint_residual(
        np.vdot(constraint_spatial(h1), zeta),
        np.vdot(h1, constraint_spatial_adjoint(zeta)),
    )
    walk_residual = _relative_adjoint_residual(
        np.vdot(apply_walk_stiffness(h1), h2),
        np.vdot(h1, apply_walk_stiffness(h2)),
    )
    r30_residual = _relative_adjoint_residual(
        np.vdot(apply_r30_stiffness(h1), h2),
        np.vdot(h1, apply_r30_stiffness(h2)),
    )
    return {
        "L": L,
        "seed": seed,
        "constraint_adjoint_residual": constraint_residual,
        "walk_stiffness_adjoint_residual": walk_residual,
        "r30_stiffness_adjoint_residual": r30_residual,
        "pass": max(constraint_residual, walk_residual, r30_residual) < 1e-13,
    }


K_CERT = (
    (0.0, 0.0, 0.0),
    (2.0 * math.pi / 32.0, 0.0, 0.0),
    (2.0 * math.pi / 32.0, 2.0 * math.pi / 32.0, 0.0),
    (
        2.0 * math.pi / 32.0,
        2.0 * math.pi / 32.0,
        2.0 * math.pi / 32.0,
    ),
    (math.pi / 2.0, 0.0, 0.0),
    (math.pi / 2.0, math.pi / 2.0, 0.0),
    (math.pi / 2.0, math.pi / 2.0, math.pi / 2.0),
    (math.pi, math.pi, math.pi),
)


def _constraint_symbol(k: np.ndarray) -> np.ndarray:
    differences = np.exp(1j * k) - 1.0
    return np.einsum("nai,i->na", C_SP_COEFF, differences)


def symbol_of_potential(
    q: int,
    kappa_c: float,
    k: tuple[float, float, float] | np.ndarray,
) -> np.ndarray:
    """Offline 14×14 potential symbol; never used by the real-space step."""

    k_array = np.asarray(k, dtype=float)
    r25 = _frozen_mod("r25_auxiliary_wilson_complex")
    _, _, _, a_walk = r25.walk_data(k_array)
    a_r30 = float(
        C_CONE
        * C_CONE
        * sum(
            (2.0 * math.sin(float(value) / 2.0)) ** 2
            for value in k_array
        )
    )
    a_q = float(a_walk + (q / 4.0) * (a_r30 - a_walk))
    constraint = _constraint_symbol(k_array)
    potential = np.zeros((14, 14), dtype=complex)
    potential[:10, :10] = a_q * np.eye(10)
    potential[10:, 10:] = a_r30 * np.eye(4)
    normalized_constraint = C_SP_NORMALIZATION * constraint
    potential[:10, :10] += (
        kappa_c * normalized_constraint.conj().T @ normalized_constraint
    )
    potential[:10, 10:] = -kappa_c * normalized_constraint.conj().T
    potential[10:, :10] = -kappa_c * normalized_constraint
    potential[10:, 10:] += kappa_c * np.eye(4)
    return potential


def _verlet_symbol(potential: np.ndarray, dt: float) -> np.ndarray:
    if not np.isfinite(potential).all() or not math.isfinite(dt):
        raise FloatingPointError("non-finite input to Verlet symbol")
    dimension = potential.shape[0]
    identity = np.eye(dimension, dtype=complex)
    zero = np.zeros_like(identity)
    kick = np.block(
        [
            [identity, zero],
            [-0.5 * dt * potential, identity],
        ]
    )
    drift = np.block(
        [
            [identity, dt * identity],
            [zero, identity],
        ]
    )
    # Accelerate BLAS on macOS can inherit stale floating-point status flags
    # from imported legacy modules.  Inputs/outputs are checked explicitly;
    # suppress only those spurious status warnings around the finite matmul.
    with np.errstate(all="ignore"):
        macro = kick @ drift @ kick
    if not np.isfinite(macro).all():
        raise FloatingPointError("non-finite Verlet symbol")
    return macro


def _real_representation(matrix: np.ndarray) -> np.ndarray:
    return np.block(
        [
            [matrix.real, -matrix.imag],
            [matrix.imag, matrix.real],
        ]
    )


def _real_symplectic_defect(matrix: np.ndarray) -> float:
    complex_dimension = matrix.shape[0] // 2
    identity = np.eye(complex_dimension)
    zero = np.zeros_like(identity)
    canonical = np.block([[zero, identity], [-identity, zero]])
    canonical_real = np.block(
        [
            [canonical, np.zeros_like(canonical)],
            [np.zeros_like(canonical), canonical],
        ]
    )
    real_matrix = _real_representation(matrix)
    with np.errstate(all="ignore"):
        defect = real_matrix.T @ canonical_real @ real_matrix - canonical_real
    if not np.isfinite(defect).all():
        raise FloatingPointError("non-finite symplectic defect")
    return float(np.max(np.abs(defect)))


def certify_local_family() -> dict[str, object]:
    """Measure H0 admission certificates on all 30 construction cells."""

    floquet = floquet_retune_table()
    adjoint = adjoint_certificate()
    support = measure_support_radii()
    per_cell: list[dict[str, object]] = []
    worst_symplectic = 0.0
    worst_hermitian = 0.0
    worst_modulus = 0.0
    worst_cfl = 0.0
    minimum_potential_eigenvalue = math.inf

    for q in Q_LEVELS:
        dt = float(floquet[q]["dt"])
        for kappa_c in KAPPA_C_LEVELS:
            cell_symplectic = 0.0
            cell_hermitian = 0.0
            cell_modulus = 0.0
            cell_cfl = 0.0
            cell_minimum_potential_eigenvalue = math.inf
            worst_k = None
            for k in K_CERT:
                potential = symbol_of_potential(q, kappa_c, k)
                hermitian = float(
                    np.max(np.abs(potential - potential.conj().T))
                )
                potential_eigenvalues = np.linalg.eigvalsh(potential)
                potential_minimum = float(potential_eigenvalues.min())
                cfl_number = dt * dt * float(potential_eigenvalues.max())
                macro = _verlet_symbol(potential, dt)
                symplectic = _real_symplectic_defect(macro)
                if any(abs(component) > 1e-15 for component in k):
                    eigenvalues = np.linalg.eigvals(macro)
                    modulus = float(
                        np.max(np.abs(np.abs(eigenvalues) - 1.0))
                    )
                else:
                    # The exact zero-stiffness modes are Jordan drifts.  A
                    # generic eigensolver splits their repeated λ=1 roots by
                    # O(sqrt(eps)); stability is instead certified by the
                    # Hermitian potential spectrum and the Verlet CFL bound.
                    modulus = 0.0
                cell_hermitian = max(cell_hermitian, hermitian)
                cell_symplectic = max(cell_symplectic, symplectic)
                cell_cfl = max(cell_cfl, cfl_number)
                cell_minimum_potential_eigenvalue = min(
                    cell_minimum_potential_eigenvalue,
                    potential_minimum,
                )
                if modulus > cell_modulus:
                    cell_modulus = modulus
                    worst_k = list(k)
            worst_symplectic = max(worst_symplectic, cell_symplectic)
            worst_hermitian = max(worst_hermitian, cell_hermitian)
            worst_modulus = max(worst_modulus, cell_modulus)
            worst_cfl = max(worst_cfl, cell_cfl)
            minimum_potential_eigenvalue = min(
                minimum_potential_eigenvalue,
                cell_minimum_potential_eigenvalue,
            )
            stable = (
                cell_minimum_potential_eigenvalue >= -2e-12
                and cell_cfl < 4.0
                and cell_modulus <= 1e-12
            )
            per_cell.append(
                {
                    "q": q,
                    "kappa_c": kappa_c,
                    "dt": dt,
                    "max_symplectic_defect_fp64": cell_symplectic,
                    "max_potential_hermitian_defect": cell_hermitian,
                    "max_abs_eig_modulus_minus_1": cell_modulus,
                    "minimum_potential_eigenvalue": (
                        cell_minimum_potential_eigenvalue
                    ),
                    "max_verlet_cfl_number": cell_cfl,
                    "worst_modulus_k": worst_k,
                    "stable": stable,
                }
            )

    stable_all = all(bool(row["stable"]) for row in per_cell)
    floquet_residual = max(
        float(row["frequency_residual"]) for row in floquet.values()
    )
    passed = (
        adjoint["pass"]
        and support["independent_of_L"]
        and int(support["max_radius"]) <= 6
        and worst_symplectic <= 1e-12
        and worst_hermitian <= 1e-12
        and worst_modulus <= 1e-12
        and minimum_potential_eigenvalue >= -2e-12
        and worst_cfl < 4.0
        and floquet_residual <= 1e-12
    )
    return {
        "_schema": "v2m3_local_family_certificate v1",
        "construction": "walk-to-R30 four-counter-shear family",
        "cells_checked": len(per_cell),
        "k_samples": [list(k) for k in K_CERT],
        "max_symplectic_defect_fp64": worst_symplectic,
        "max_potential_hermitian_defect": worst_hermitian,
        "max_abs_eig_modulus_minus_1": worst_modulus,
        "minimum_potential_eigenvalue": minimum_potential_eigenvalue,
        "max_verlet_cfl_number": worst_cfl,
        "zero_mode_policy": (
            "analytic Jordan drift; spectral modulus excluded at k=0"
        ),
        "max_floquet_frequency_residual": floquet_residual,
        "stable_all": stable_all,
        "adjoint": adjoint,
        "support": support,
        "floquet_retune": floquet,
        "per_cell": per_cell,
        "pass": bool(passed),
    }


def local_family_descriptor(
    certificate: dict[str, object],
) -> dict[str, object]:
    """Build the admission descriptor from measured construction evidence."""

    support = certificate["support"]
    error = max(
        float(certificate["max_symplectic_defect_fp64"]),
        float(certificate["max_abs_eig_modulus_minus_1"]),
    )
    return {
        "name": "M3-local-counter-shear-q-family-v1",
        "construction_kind": "strict_local_realspace",
        "realspace_step_factory": (
            "rulespace_v2.m3_local_family:realspace_step_factory"
        ),
        "support_radius": int(support["max_radius"]),
        "declared_composition_radius": DECLARED_COMPOSITION_RADIUS,
        "support_radius_independent_of_L": bool(support["independent_of_L"]),
        "unitarity_error_fp64": error,
        "same_state_space_all_q": True,
        "state_schema": ["h[10]", "p_h[10]", "zeta[4]", "p_zeta[4]"],
        "k_dependent_projection": False,
        "time_step_uses_fft": False,
        "explicit_local_shears": [
            "counter_1",
            "counter_2",
            "counter_3",
            "counter_4",
        ],
        "q_layer_counts": list(Q_LEVELS),
        "coordinates_are_measured": True,
        "floquet_retune_mode": "actual-floquet-shell",
        "constraint_penalty": (
            "0.5*kappa_c*||zeta-0.5*C_sp*h||^2"
        ),
        "construction_certificate_pass": bool(certificate["pass"]),
    }


__all__ = [
    "C_SP_NORMALIZATION",
    "C_SP_COEFF",
    "DECLARED_COMPOSITION_RADIUS",
    "K_CERT",
    "KAPPA_C_LEVELS",
    "LocalFamilyState",
    "LocalFamilyStep",
    "Q_LEVELS",
    "apply_counter_stiffness",
    "apply_r30_stiffness",
    "apply_walk_stiffness",
    "adjoint_certificate",
    "constraint_spatial",
    "constraint_spatial_adjoint",
    "certify_local_family",
    "floquet_retune_table",
    "local_family_descriptor",
    "measure_support_radii",
    "negative_laplacian",
    "realspace_step_factory",
    "symbol_of_potential",
]
