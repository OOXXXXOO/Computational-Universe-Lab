"""R25-A: exact Laurent/Floquet symbol of the frozen CP1-v4 matter walk.

This is a symbolic certificate, not a fitted dispersion model.  It rebuilds
the three axis sandwiches used by green_one_walk.geom_walk_all over the exact
coefficient field Q(i, sqrt(2), sqrt(3)), expands the trace as a finite
Laurent polynomial, and records the first B0 (classical scalar-differential)
compatibility obstruction.

Run:
    .venv/bin/python r25_laurent_complex.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from collections import defaultdict

import numpy as np
import sympy as sp

import cp1_v4_L2 as L2


DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "r25_laurent_results.json")
I = sp.I
SQ2 = sp.sqrt(2)
SQ3 = sp.sqrt(3)
zx, zy, zz, zt = sp.symbols("z_x z_y z_z z_t", nonzero=True)


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def coin(sign=1):
    """C(sign*pi/3) = exp(i sign*pi/3 sigma_x)."""
    return sp.Matrix([[sp.Rational(1, 2), sign * I * SQ3 / 2],
                      [sign * I * SQ3 / 2, sp.Rational(1, 2)]])


def exact_frames():
    # A=exp(i*pi/6 sigma_x); implementation uses (A^dag W_x,
    # A^dag W_y, A^dag), with row-spinor convention already absorbed by the
    # authoritative momentum formula W^dag (...) W in L2.walk_symbol.
    A = sp.Matrix([[SQ3 / 2, I / 2], [I / 2, SQ3 / 2]])
    Ad = A.conjugate().T
    Wx0 = sp.Matrix([[1, 1], [1, -1]]) / SQ2
    Wy0 = sp.Matrix([[1, -I], [1, I]]) / SQ2
    return Ad * Wx0, Ad * Wy0, Ad


def axis_symbol(z, W):
    D1 = sp.diag(1 / z, 1)
    D2 = sp.diag(1, z)
    return sp.simplify(W.conjugate().T * D2 * coin(-1) * D1 * coin(+1) * W)


def walk_symbol_exact():
    Wx, Wy, Wz = exact_frames()
    Ux, Uy, Uz = (axis_symbol(zx, Wx), axis_symbol(zy, Wy),
                  axis_symbol(zz, Wz))
    return sp.simplify(Uz * Uy * Ux), (Ux, Uy, Uz)


def laurent_coefficients(expr, variables=(zx, zy, zz)):
    """Return exact exponent tuple -> coefficient for a Laurent polynomial."""
    expr = sp.expand(expr)
    out = defaultdict(lambda: sp.Integer(0))
    for term in sp.Add.make_args(expr):
        powers = term.as_powers_dict()
        exps = tuple(int(powers.get(v, 0)) for v in variables)
        coeff = term
        for v, e in zip(variables, exps):
            coeff /= v ** e
        out[exps] += sp.simplify(coeff)
    return {k: sp.simplify(v) for k, v in sorted(out.items()) if v != 0}


def eval_exact_matrix(M, kval):
    sub = {zx: np.exp(1j * kval[0]), zy: np.exp(1j * kval[1]),
           zz: np.exp(1j * kval[2])}
    return np.array(M.evalf(17, subs=sub).tolist(), dtype=complex)


def directional_series(expr, direction, order=7):
    e = sp.symbols("epsilon", real=True)
    sub = {zx: sp.exp(I * e * sp.Rational(direction[0])),
           zy: sp.exp(I * e * sp.Rational(direction[1])),
           zz: sp.exp(I * e * sp.Rational(direction[2]))}
    return sp.simplify(sp.series(expr.subs(sub), e, 0, order).removeO())


def laurent_star(expr):
    """Formal adjoint involution: conjugate coefficients and z_a -> z_a^-1."""
    out = sp.conjugate(expr)
    return sp.expand(out.xreplace({sp.conjugate(zx): 1 / zx,
                                   sp.conjugate(zy): 1 / zy,
                                   sp.conjugate(zz): 1 / zz,
                                   sp.conjugate(zt): 1 / zt}))


def matrix_star(M):
    return M.applyfunc(laurent_star).T


def ideal_b0_null():
    """R15 classical placed scalar-difference null polynomial.

    On Fourier modes, d0^2 is represented by (2-zt-zt^-1)/c^2 and each
    spatial placed square by (2-zi-zi^-1).  With c=1/2, q=0 is the ideal
    half-angle shell.  Sign is chosen so the IR term is -w^2/c^2+|k|^2.
    """
    return sp.expand(4 * (2 - zt - 1 / zt)
                     - sum(2 - z - 1 / z for z in (zx, zy, zz)))


def main():
    U, axes = walk_symbol_exact()
    tr_u = sp.simplify(sp.trace(U))
    det_u = sp.simplify(sp.det(U))
    atr = sp.expand(2 - tr_u)
    char = sp.expand(zt ** 2 - tr_u * zt + 1)
    char_recip = sp.simplify(char.subs(zt, 1 / zt) * zt ** 2 - char)

    rng = np.random.default_rng(250724)
    worst = 0.0
    for _ in range(32):
        k = rng.uniform(-math.pi, math.pi, 3)
        worst = max(worst, float(np.max(np.abs(eval_exact_matrix(U, k)
                                               - L2.walk_symbol(k)))))

    coeff = laurent_coefficients(atr)
    support = [list(e) for e in coeff]
    max_radius = max(max(abs(v) for v in e) for e in coeff)

    # The defining walk shell in reciprocal form is
    # f_walk = zt + zt^-1 - tr(U) = 0.  Compare it symbolically with B0's
    # classical placed null polynomial after normalizing the time term.
    f_walk = sp.expand(zt + 1 / zt - tr_u)
    q_b0 = ideal_b0_null()
    # q_b0 = -4 f_ideal.  If classical B0 shared the walk shell, q_b0 would
    # be a Laurent-unit multiple of f_walk; matching zt coefficients fixes
    # that unit to -4, so this residual is an exact obstruction certificate.
    b0_residual = sp.expand(q_b0 + 4 * f_walk)
    b0_coeff = laurent_coefficients(b0_residual)

    # The noncommuting walk itself supplies a finite matrix-valued spectral
    # factor.  This is the B1 seed: it uses the two walk-spinor channels
    # instead of pretending that the shell is a sum of three commuting scalar
    # placed derivatives.
    I2 = sp.eye(2)
    Dwalk = I2 - U
    spatial_factor_residual = (matrix_star(Dwalk) * Dwalk
                               - atr * I2).applyfunc(sp.simplify)
    F = zt * I2 - U
    adjF = sp.Matrix([[F[1, 1], -F[0, 1]], [-F[1, 0], F[0, 0]]])
    floquet_factor_residual = (adjF * F - char * I2).applyfunc(sp.simplify)

    dirs = [(1, 0, 0), (1, 1, 0), (1, 1, 1), (3, 1, -2)]
    series = {str(d): str(directional_series(atr, d)) for d in dirs}
    residual_series = {str(d): str(directional_series(b0_residual, d))
                       for d in dirs}

    # UV/foldback registry is diagnostic, not a proof of all zeroes: scan a
    # deterministic 64^3 BZ and report the smallest nonzero a_tr locations.
    uv = []
    N = 64
    for ix in range(N):
        for iy in range(N):
            for iz in range(N):
                if (ix, iy, iz) == (0, 0, 0):
                    continue
                k = 2 * np.pi * np.array([ix, iy, iz], float) / N
                val = float(2 - np.real(np.trace(L2.walk_symbol(k))))
                if len(uv) < 12 or val < uv[-1][0]:
                    uv.append((val, ix, iy, iz))
                    uv.sort()
                    uv = uv[:12]

    checks = {
        "exact_vs_implementation_lt_1e-12": worst < 1e-12,
        "det_U_identically_one": det_u == 1,
        "characteristic_reciprocal": char_recip == 0,
        "finite_radius_one_trace_support": max_radius == 1,
        "B0_classical_residual_nonzero": b0_residual != 0,
        "B1_walk_matrix_spectral_factor_exact": spatial_factor_residual == sp.zeros(2),
        "Floquet_matrix_factorization_exact": floquet_factor_residual == sp.zeros(2),
    }
    result = {
        "register": "R25-A",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_sha256": sha256(__file__),
        "frozen_symbol_source": "cp1_v4_L2.walk_symbol",
        "exact_vs_numeric_max_abs": worst,
        "det_U": str(det_u),
        "trace_U": str(tr_u),
        "P_zt": str(char),
        "a_tr": str(atr),
        "a_tr_support": support,
        "a_tr_support_size": len(coeff),
        "a_tr_max_coordinate_radius": max_radius,
        "a_tr_coefficients": {str(k): str(v) for k, v in coeff.items()},
        "a_tr_directional_IR_series": series,
        "B0": {
            "scope": "classical R15 symmetric-gradient with the original four scalar placed differences",
            "q_b0": str(q_b0),
            "normalization_argument": "zt coefficients force q_b0 = -4 f_walk if the two principal shell polynomials are associates",
            "exact_residual_q_b0_plus_4_f_walk": str(b0_residual),
            "residual_support_size": len(b0_coeff),
            "residual_coefficients": {str(k): str(v) for k, v in b0_coeff.items()},
            "directional_IR_series": residual_series,
            "verdict": "NO-GO for B0 only; B1/B2 general Laurent generators remain open",
        },
        "B1_seed": {
            "D_walk": "I_2 - U_walk",
            "spatial_identity": "D_walk^* D_walk = (2-tr U_walk) I_2",
            "spatial_residual": str(spatial_factor_residual),
            "F_walk": "z_t I_2 - U_walk",
            "floquet_identity": "adj(F_walk) F_walk = P(z_t,z) I_2",
            "floquet_residual": str(floquet_factor_residual),
            "interpretation": "strictly local 2-channel matrix-valued differential / matrix-factorization seed; not yet a rank-4 spin-2 gauge generator",
        },
        "uv_scan": {
            "N": N,
            "smallest_nonzero_a_tr": [
                {"a_tr": v, "index": [ix, iy, iz]} for v, ix, iy, iz in uv
            ],
            "interpretation": "diagnostic registry, not an algebraic zero-set proof",
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print("R25-A exact Laurent/Floquet register")
    print("status:", result["status"])
    print("exact-vs-code max abs:", f"{worst:.3e}")
    print("det U:", det_u, "  a_tr support:", len(coeff),
          "radius:", max_radius)
    print("B0 residual support:", len(b0_coeff), "(nonzero = bounded no-go)")
    print("smallest scanned nonzero a_tr:", f"{uv[0][0]:.6e}",
          "at", uv[0][1:])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
