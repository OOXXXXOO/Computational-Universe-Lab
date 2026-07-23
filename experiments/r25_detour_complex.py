"""R25-B2/C0: a strictly local walk-compatible spin-2 detour symbol.

The exact Floquet matrix F=z_t I-U is decomposed in the Pauli basis,

    F = kappa_0 I + sum_i kappa_i sigma_i.

Its determinant is the walk characteristic polynomial and therefore
kappa.eta.kappa=-P_walk (eta=-+++).  Substituting these *scalar Laurent*
components into the ordinary Killing--Einstein--Bianchi algebra yields a
finite-stencil detour complex with the exact full walk characteristic shell.

This file proves the polynomial identities and measures the generic on-shell
cohomology.  It does not yet realize damping/source dynamics in real space.
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
import r25_walk_dedonder_complex as R25B1


DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "r25_detour_results.json")
ETA = np.diag([-1.0, 1.0, 1.0, 1.0])
SYM = r15.SYM
I = sp.I
zx, zy, zz, zt = R25A.zx, R25A.zy, R25A.zz, R25A.zt


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def floquet_kappa_exact(U):
    tr_u = sp.simplify(sp.trace(U))
    a = tr_u / 2
    b = R25B1.bloch_vector(U)
    return sp.Matrix([zt - a, I * b[0], I * b[1], I * b[2]])


def ir_jacobian(kap):
    """Jacobian with columns (omega,kx,ky,kz), zt=e^-i omega."""
    variables = (zt, zx, zy, zz)
    factors = (-I * zt, I * zx, I * zy, I * zz)
    J = sp.Matrix(4, 4, lambda row, col: sp.diff(kap[row], variables[col])
                  * factors[col])
    return J.subs({zt: 1, zx: 1, zy: 1, zz: 1}).applyfunc(sp.simplify)


def pack_matrix(H):
    return np.array([H[m, n] for m, n in SYM], complex)


def unpack_vector(v):
    H = np.zeros((4, 4), complex)
    for x, (m, n) in zip(v, SYM):
        H[m, n] = H[n, m] = x
    return H


def gauge_matrix(kap):
    G = np.zeros((10, 4), complex)
    for alpha in range(4):
        xi = np.zeros(4, complex)
        xi[alpha] = 1
        G[:, alpha] = pack_matrix(np.outer(kap, xi) + np.outer(xi, kap))
    return G


def dedonder_matrix(kap):
    """C_nu=kappa^mu(h_munu-eta_munu h/2), for ordinary h."""
    C = np.zeros((4, 10), complex)
    kup = ETA @ kap
    for j in range(10):
        h = np.zeros(10, complex); h[j] = 1
        H = unpack_vector(h)
        trh = np.sum(ETA * H)
        bar = H - 0.5 * ETA * trh
        C[:, j] = kup @ bar
    return C


def einstein_matrix(kap):
    """Twice-linearized Einstein symbol, normalization irrelevant.

    E=q hbar-kappa_mu C_nu-kappa_nu C_mu+eta_mu_nu kappa^a C_a.
    It obeys E G=0 and kappa^mu E_mu_nu=0 identically.
    """
    C = dedonder_matrix(kap)
    q = kap @ ETA @ kap
    E = np.zeros((10, 10), complex)
    kup = ETA @ kap
    for j in range(10):
        H = unpack_vector(np.eye(10, dtype=complex)[:, j])
        trh = np.sum(ETA * H)
        bar = H - 0.5 * ETA * trh
        cv = C[:, j]
        EH = (q * bar - np.outer(kap, cv) - np.outer(cv, kap)
              + ETA * (kup @ cv))
        E[:, j] = pack_matrix(EH)
    return E


def bianchi_matrix(kap):
    B = np.zeros((4, 10), complex)
    kup = ETA @ kap
    for j in range(10):
        H = unpack_vector(np.eye(10, dtype=complex)[:, j])
        B[:, j] = kup @ H
    return B


def generic_identity_census():
    rng = np.random.default_rng(250726)
    worst = {"CG_minus_qI": 0.0, "EG": 0.0, "BE": 0.0}
    for _ in range(64):
        kap = rng.normal(size=4) + 1j * rng.normal(size=4)
        q = kap @ ETA @ kap
        G, C = gauge_matrix(kap), dedonder_matrix(kap)
        E, B = einstein_matrix(kap), bianchi_matrix(kap)
        worst["CG_minus_qI"] = max(worst["CG_minus_qI"],
                                    float(np.max(np.abs(C @ G - q*np.eye(4)))))
        worst["EG"] = max(worst["EG"], float(np.max(np.abs(E @ G))))
        worst["BE"] = max(worst["BE"], float(np.max(np.abs(B @ E))))
    return worst


def numeric_floquet_kappa(k, branch):
    U = L2.walk_symbol(np.asarray(k, float))
    vals = np.linalg.eigvals(U)
    # branch + selects positive omega with eigenvalue exp(-i omega).
    phases = -np.angle(vals)
    target = np.argmax(phases) if branch == 1 else np.argmin(phases)
    lam = vals[target]
    a = np.trace(U) / 2
    b = np.array([1j * np.trace(np.array(s.tolist(), complex) @ U) / 2
                  for s in R25B1.SIGMA])
    return np.concatenate([[lam-a], 1j*b]) / L2.C


def subspace_quotient_dim(E, G, tol=1e-8):
    se = np.linalg.svd(E, compute_uv=False)
    rank_e = int(np.sum(se > tol * max(se[0], 1.0)))
    _, _, vh = np.linalg.svd(E)
    ker = vh[rank_e:].conj().T
    qg, _ = np.linalg.qr(G)
    rem = ker - qg @ (qg.conj().T @ ker)
    sr = np.linalg.svd(rem, compute_uv=False)
    dim = int(np.sum(sr > tol))
    return rank_e, ker.shape[1], dim


def main():
    U, _ = R25A.walk_symbol_exact()
    kap = floquet_kappa_exact(U)
    P = sp.expand(zt**2-sp.trace(U)*zt+1)
    q = sp.expand(-(kap[0]**2) + sum(kap[j]**2 for j in range(1, 4)))
    q_residual = sp.simplify(q + P)
    J = ir_jacobian(kap)
    generic = generic_identity_census()

    rng = np.random.default_rng(250727)
    kset = [np.array([0.3, 0, 0]), np.array([0.4, 0.4, 0]),
            np.array([0.4, 0.4, 0.4]), np.array([0.7, 0.2, -0.5])]
    kset += [rng.uniform(-2.8, 2.8, 3) for _ in range(1024)]
    ranks_g, ranks_c, ranks_e, dims = set(), set(), set(), set()
    worst = {"q_on_shell": 0.0, "CG": 0.0, "EG": 0.0, "BE": 0.0}
    for branch in (-1, 1):
        for k in kset:
            kv = numeric_floquet_kappa(k, branch)
            qv = kv @ ETA @ kv
            G, C = gauge_matrix(kv), dedonder_matrix(kv)
            E, B = einstein_matrix(kv), bianchi_matrix(kv)
            ranks_g.add(np.linalg.matrix_rank(G, tol=1e-9))
            ranks_c.add(np.linalg.matrix_rank(C, tol=1e-9))
            re, _, dim = subspace_quotient_dim(E, G)
            ranks_e.add(re); dims.add(dim)
            worst["q_on_shell"] = max(worst["q_on_shell"], abs(qv))
            worst["CG"] = max(worst["CG"], float(np.max(np.abs(C@G))))
            worst["EG"] = max(worst["EG"], float(np.max(np.abs(E@G))))
            worst["BE"] = max(worst["BE"], float(np.max(np.abs(B@E))))

    checks = {
        "kappa_square_equals_minus_P_exact": q_residual == 0,
        "IR_is_common_i_times_physical_covector": J == sp.diag(-I, I/2, I/2, I/2),
        "generic_CG_identity_numeric": generic["CG_minus_qI"] < 1e-12,
        "generic_EG_identity_numeric": generic["EG"] < 1e-11,
        "generic_BE_identity_numeric": generic["BE"] < 1e-11,
        "on_shell_rank_G_four": ranks_g == {4},
        "on_shell_rank_C_four": ranks_c == {4},
        "on_shell_rank_E_four": ranks_e == {4},
        "on_shell_detour_cohomology_two": dims == {2},
        "on_shell_residuals_lt_1e-11": max(worst.values()) < 1e-11,
    }
    result = {
        "register": "R25-B2-C0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_sha256": sha256(__file__),
        "construction": {
            "F": "z_t I_2-U_walk = kappa_0 I+sum kappa_i sigma_i",
            "kappa": [str(x) for x in kap],
            "exact_characteristic_identity": "kappa.eta.kappa=-det(F)=-P_walk",
            "IR_jacobian_columns_omega_kxyz": str(J),
            "maps": "R^4 --Killing G--> R^10 --Einstein E--> R^10 --Bianchi B--> R^4",
            "locality": "all entries Laurent-polynomial; kappa radius (time,space)=(1,1), E radius <=(2,2)",
        },
        "generic_off_shell_identity_census": generic,
        "on_shell_census": {
            "points_per_branch": len(kset),
            "rank_G": sorted(int(x) for x in ranks_g),
            "rank_C": sorted(int(x) for x in ranks_c),
            "rank_E": sorted(int(x) for x in ranks_e),
            "dim_kerE_mod_imG": sorted(int(x) for x in dims),
            "worst": {k: float(v) for k, v in worst.items()},
        },
        "scope_boundary": "Symbol-level detour complex passed. Remaining: exact symbolic curvature compatibility/free resolution, real-space placement/adjoint realization, damping, source/Newton and full-BZ exceptional-ideal audit.",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print("R25-B2/C0 walk-compatible Killing--Einstein--Bianchi detour")
    print("status:", result["status"])
    print("IR Jacobian:", J)
    print("ranks G/C/E:", sorted(ranks_g), sorted(ranks_c), sorted(ranks_e),
          "cohomology:", sorted(dims))
    print("worst on-shell residual:", f"{max(worst.values()):.3e}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
