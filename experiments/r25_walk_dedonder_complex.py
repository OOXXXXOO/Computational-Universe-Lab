"""R25-B1: exact on-shell walk-compatible de Donder/gauge complex.

Write the frozen SU(2) walk as U=a I-i b_j sigma_j.  Its Bloch vector b is a
radius-one Laurent vector containing all noncommuting/Trotter cross terms.
Together with the centered Floquet time symbol it defines

    kappa = ((zt^-1-zt)/(2i), b_x, b_y, b_z).

The norm kappa.eta.kappa is exactly divisible by the walk characteristic
polynomial, so the ordinary trace-reversed Killing/de Donder algebra becomes
an exact complex over the shell ring R/(P_walk), without any Green operator.

Run:
    .venv/bin/python r25_walk_dedonder_complex.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np
import sympy as sp

import cp1_v4_L2 as L2
import r15_walk_dedonder as r15
import r25_laurent_complex as R25A


DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "r25_walk_complex_results.json")
I = sp.I
zx, zy, zz, zt = R25A.zx, R25A.zy, R25A.zz, R25A.zt
SIGMA = (
    sp.Matrix([[0, 1], [1, 0]]),
    sp.Matrix([[0, -I], [I, 0]]),
    sp.Matrix([[1, 0], [0, -1]]),
)


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def bloch_vector(U):
    # U=aI-i b.sigma => b_j=(i/2) tr(sigma_j U).
    return sp.Matrix([sp.simplify(I * sp.trace(s * U) / 2) for s in SIGMA])


def ir_jacobian(b):
    vars_ = (zx, zy, zz)
    # z=e^{ik}: d/dk at zero = i z d/dz evaluated at z=1.
    return sp.Matrix(3, 3, lambda row, col: sp.simplify(
        I * vars_[col] * sp.diff(b[row], vars_[col]))) \
        .subs({zx: 1, zy: 1, zz: 1}).applyfunc(sp.simplify)


def generic_dedonder_identity():
    """Prove C(kappa) G(kappa)=(kappa.eta.kappa)I universally."""
    ks = sp.symbols("k0:4")
    kap = sp.Matrix(ks)
    eta = sp.diag(-1, 1, 1, 1)
    kup = eta * kap
    sym = r15.SYM
    C = sp.zeros(4, 10)
    G = sp.zeros(10, 4)
    for c10, (m, n) in enumerate(sym):
        for nu in range(4):
            if n == nu:
                C[nu, c10] += kup[m]
            if m == nu and m != n:
                C[nu, c10] += kup[n]
        for alpha in range(4):
            # trace-reversed gauge hbar_mn=k_m xi_n+k_n xi_m
            # -eta_mn (k.xi); xi has a lower component label here.
            G[c10, alpha] = (kap[m] * int(n == alpha)
                             + kap[n] * int(m == alpha)
                             - eta[m, n] * kup[alpha])
    q = (kap.T * eta * kap)[0]
    residual = (C * G - q * sp.eye(4)).applyfunc(sp.simplify)
    return residual


def numerical_kappa(k, branch=1):
    U = L2.walk_symbol(np.asarray(k, float))
    a = float(np.real(np.trace(U)) / 2)
    omega = math.acos(np.clip(a, -1.0, 1.0))
    b = np.array([1j * np.trace(np.array(s.tolist(), complex) @ U) / 2
                  for s in SIGMA], complex)
    # zt=e^{-i branch omega}; centered symbol is branch*sin(omega).
    return np.concatenate([[branch * math.sin(omega)], b.real]) / L2.C


def main():
    U, _ = R25A.walk_symbol_exact()
    tr_u = sp.simplify(sp.trace(U))
    a = tr_u / 2
    b = bloch_vector(U)
    t = (1 / zt - zt) / (2 * I)
    q = sp.expand(-t ** 2 + (b.T * b)[0])
    f_walk = sp.expand(zt + 1 / zt - tr_u)
    quotient = sp.expand((zt + 1 / zt + tr_u) / 4)
    factor_residual = sp.simplify(q - f_walk * quotient)
    su2_residual = sp.simplify(a ** 2 + (b.T * b)[0] - 1)
    star_residual = [sp.simplify(R25A.laurent_star(x) - x) for x in b]
    jac = ir_jacobian(b)
    universal_cg = generic_dedonder_identity()

    rng = np.random.default_rng(250725)
    kset = [np.array([0.3, 0.0, 0.0]), np.array([0.4, 0.4, 0.0]),
            np.array([0.4, 0.4, 0.4]), np.array([0.7, 0.2, -0.5])]
    kset += [rng.uniform(-2.5, 2.5, 3) for _ in range(512)]
    worst = {"null": 0.0, "cg": 0.0, "dtt": 0.0,
             "imag_b": 0.0}
    ranks, dims = set(), set()
    branch_rows = []
    for branch in (-1, 1):
        for k in kset:
            kap = numerical_kappa(k, branch)
            null, cg, rank, _, dimq, dtt = r15.analyze(kap)
            worst["null"] = max(worst["null"], null)
            worst["cg"] = max(worst["cg"], cg)
            worst["dtt"] = max(worst["dtt"], dtt)
            ranks.add(rank)
            dims.add(dimq)
        branch_rows.append({"branch": branch, "points": len(kset)})

    # Directly measure the imaginary leakage of b on the unit torus.
    for k in kset:
        Uv = L2.walk_symbol(k)
        bv = np.array([1j * np.trace(np.array(s.tolist(), complex) @ Uv) / 2
                       for s in SIGMA])
        worst["imag_b"] = max(worst["imag_b"], float(np.max(np.abs(bv.imag))))

    # L3-v3 gate momenta: compare exact walk-compatible nullity against the
    # old ideal placed kappa at the true walk frequency.
    gate = []
    N = 32
    for nv in ((2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0),
               (2, 2, 2), (1, 1, 1)):
        k = 2 * np.pi * np.array(nv, float) / N
        knew = numerical_kappa(k)
        Uv = L2.walk_symbol(k)
        omega = math.acos(np.clip(float(np.real(np.trace(Uv)) / 2), -1, 1))
        kold = np.array([2 * math.sin(omega / 2) / L2.C]
                        + [2 * math.sin(x / 2) for x in k])
        gate.append({
            "index": list(nv),
            "new_abs_kappa2": float(abs(knew @ r15.ETA @ knew)),
            "old_abs_kappa2": float(abs(kold @ r15.ETA @ kold)),
            "new_dim_kerC_mod_gauge": r15.analyze(knew)[4],
        })

    checks = {
        "SU2_bloch_identity_exact": su2_residual == 0,
        "bloch_components_star_real": star_residual == [0, 0, 0],
        "walk_null_polynomial_factor_exact": factor_residual == 0,
        "universal_CG_equals_qI": universal_cg == sp.zeros(4),
        "IR_jacobian_equals_cI": jac == sp.eye(3) / 2,
        "numeric_shell_null_lt_1e-12": worst["null"] < 1e-12,
        "numeric_CG_lt_1e-12": worst["cg"] < 1e-12,
        "rank_C_four": ranks == {4},
        "on_shell_dim_kerC_mod_gauge_two": dims == {2},
    }
    result = {
        "register": "R25-B1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_sha256": sha256(__file__),
        "construction": {
            "U_decomposition": "U=a I-i sum_j b_j sigma_j",
            "kappa": "((zt^-1-zt)/(2i), b_x, b_y, b_z) / c",
            "IR_b_jacobian": str(jac),
            "q_factorization": "kappa^2 (before common /c) = (zt+zt^-1-trU)(zt+zt^-1+trU)/4",
            "shell_ring": "R/(zt+zt^-1-trU), equivalently R/(P_walk)",
            "locality": "b_j have coordinate radius 1 because U_walk does",
        },
        "symbolic_residuals": {
            "a2_plus_b2_minus_1": str(su2_residual),
            "star_b_minus_b": [str(x) for x in star_residual],
            "q_minus_f_times_quotient": str(factor_residual),
            "C_G_minus_q_I": str(universal_cg),
        },
        "numeric_census": {
            "branches": branch_rows,
            "ranks_C": sorted(ranks),
            "dim_kerC_mod_gauge": sorted(dims),
            "worst": worst,
        },
        "L3v3_gate_comparison": gate,
        "scope_boundary": "This passes the on-shell de Donder/gauge complex. It does not yet construct the off-shell Einstein/detour operator, damping realization, or Newton source response.",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print("R25-B1 walk-compatible on-shell de Donder/gauge complex")
    print("status:", result["status"])
    print("IR db/dk:", jac)
    print("rank C:", sorted(ranks), "dim(ker C/gauge):", sorted(dims))
    print("worst null:", f"{worst['null']:.3e}",
          "worst C@G:", f"{worst['cg']:.3e}")
    print("old/new body-diagonal null:", gate[4]["old_abs_kappa2"],
          gate[4]["new_abs_kappa2"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
