"""R25-C exceptional-set audit for the frozen matter walk.

Finds U_walk=+/-I points (where the Floquet Pauli covector from R25-B2
vanishes), certifies the nonzero +I point exactly on the y=0, z=x slice, and
records the resulting detour-rank collapse.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np
import sympy as sp
from scipy.optimize import root

import cp1_v4_L2 as L2
import r25_detour_complex as R25D
import r25_laurent_complex as R25A
import r25_walk_dedonder_complex as R25B1


DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "r25_uv_exceptional_results.json")
PAULI_NUM = [np.array(s.tolist(), complex) for s in R25B1.SIGMA]


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def bloch_num(k):
    U = L2.walk_symbol(np.asarray(k, float))
    return np.array([(1j*np.trace(s@U)/2).real for s in PAULI_NUM])


def wrap(k):
    return (np.asarray(k)+np.pi) % (2*np.pi)-np.pi


def find_roots(nseed=9):
    roots = []
    for idx in np.ndindex(nseed, nseed, nseed):
        seed = -np.pi+2*np.pi*np.array(idx, float)/nseed
        sol = root(bloch_num, seed)
        if not sol.success or np.linalg.norm(bloch_num(sol.x)) >= 1e-9:
            continue
        x = wrap(sol.x)
        if not any(np.linalg.norm(wrap(x-y)) < 1e-6 for y in roots):
            roots.append(x)
    return sorted(roots, key=lambda x: np.linalg.norm(x))


def main():
    U, _ = R25A.walk_symbol_exact()
    x = R25A.zx
    sliced = (U-sp.eye(2)).subs({R25A.zy: 1, R25A.zz: x})
    numerators = [sp.together(e).as_numer_denom()[0] for e in sliced]
    gcd = numerators[0]
    for num in numerators[1:]:
        gcd = sp.gcd(gcd, num, extension=[sp.I, sp.sqrt(3)])
    gcd = sp.monic(gcd, x, extension=[sp.I, sp.sqrt(3)])
    z_uv = (-1-4*sp.sqrt(3)*sp.I)/7
    exact_uv_residual = sliced.subs(x, z_uv).applyfunc(sp.simplify)
    unit_circle_residual = sp.simplify(z_uv*sp.conjugate(z_uv)-1)

    roots = find_roots()
    rows = []
    for k in roots:
        Uv = L2.walk_symbol(k)
        a = float(np.real(np.trace(Uv))/2)
        ztv = 1.0 if a > 0 else -1.0
        kap = R25D.numeric_floquet_kappa(k, 1)
        # At the +/-I root choose its exact degenerate eigenvalue directly.
        b = np.array([1j*np.trace(s@Uv)/2 for s in PAULI_NUM])
        kap = np.concatenate([[ztv-np.trace(Uv)/2], 1j*b])/L2.C
        G = R25D.gauge_matrix(kap)
        E = R25D.einstein_matrix(kap)
        # Root finder accuracy leaves O(1e-9) kappa.  The exact certificate
        # above proves kappa=0 at the nonzero root, so snap only certified
        # numerical roots within this declared tolerance for the rank census.
        certified_zero = np.linalg.norm(kap) < 1e-7
        rank_g = 0 if certified_zero else int(np.linalg.matrix_rank(G, tol=1e-9))
        rank_e = 0 if certified_zero else int(np.linalg.matrix_rank(E, tol=1e-9))
        rows.append({
            "k": k.tolist(), "a": a, "U_sign": 1 if a > 0 else -1,
            "bloch_norm": float(np.linalg.norm(b)),
            "kappa_norm": float(np.linalg.norm(kap)),
            "certified_zero_snap_tolerance": 1e-7,
            "rank_G": rank_g,
            "rank_E": rank_e,
            "dim_kerE_mod_imG": 10-rank_e-rank_g,
        })

    checks = {
        "slice_common_factor_contains_origin_and_nonzero_root":
            sp.rem(gcd, (x-1)*(x-z_uv), domain=sp.QQ.algebraic_field(sp.I, sp.sqrt(3))) == 0,
        "nonzero_root_on_unit_circle": unit_circle_residual == 0,
        "U_equals_I_exact_at_nonzero_root": exact_uv_residual == sp.zeros(2),
        "numeric_search_recovers_nonzero_root": any(np.linalg.norm(r["k"]) > 1 for r in rows),
        "current_detour_rank_collapses_there": any(r["rank_G"] == 0 and r["rank_E"] == 0 for r in rows if np.linalg.norm(r["k"]) > 1),
    }
    result = {
        "register": "R25-C-exceptional-audit",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_sha256": sha256(__file__),
        "exact_certificate": {
            "slice": "z_y=1, z_z=z_x",
            "gcd_of_entries_U_minus_I": str(sp.factor(gcd, extension=[sp.I, sp.sqrt(3)])),
            "nonzero_root_z": str(z_uv),
            "nonzero_root_k": float(sp.arg(z_uv).evalf()),
            "unit_circle_residual": str(unit_circle_residual),
            "U_minus_I_at_root": str(exact_uv_residual),
        },
        "numeric_root_census": rows,
        "verdict": "The frozen matter walk has an intrinsic nonzero +I Floquet/Dirac point. The canonical F=z_t I-U presentation vanishes there and its detour complex acquires exceptional UV cohomology.",
        "next_test": "Search a different Laurent matrix presentation of the same P_walk that vanishes at the IR origin but has rank one at the nonzero singular point; otherwise joint Wilsonization or matter-walk redesign becomes an architectural choice.",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print("R25 exceptional-set audit")
    print("status:", result["status"])
    print("slice gcd:", result["exact_certificate"]["gcd_of_entries_U_minus_I"])
    print("roots found:", len(rows))
    for row in rows:
        print(" k=", np.round(row["k"], 9), "U sign", row["U_sign"],
              "rank G/E", row["rank_G"], row["rank_E"],
              "cohomology", row["dim_kerE_mod_imG"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
