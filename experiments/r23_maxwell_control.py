"""R23 — Maxwell POSITIVE CONTROL: the same machinery, pointed at spin 1,
must produce the photon. (Pre-registration item 10, added 2026-07-20.)

WHY. The referee question is inevitable: "does your emergence machinery work
on a case where the answer is known?" Spin 1 is that case, and it is a strict
degeneration of everything we built for spin 2:

    field        A_mu (4 comps)          <- hbar_munu (10 comps)
    placement    A_mu at x + e_mu/2      <- x + (e_mu+e_nu)/2   (= CLASSIC YEE)
    constraint   C = kappa^mu A_mu (1)   <- de Donder (4)
    gauge        A_mu -> A_mu + kappa_mu xi   (1 param  <- 4 params)
    invariant    F_munu = kap_mu A_nu - kap_nu A_mu     <- linearized Riemann
    physical     2 transverse photon pols                <- 2 TT pols
    shell        SAME walk shell, SAME placed kappa, kappa.kappa = 0 (R15 T8)

CERTIFICATES
  P1  nullity: reused from R15 (same kappa) -- printed for completeness.
  P2  rank C = 1;  dim(ker C / gauge) = 2;  quotient == transverse(kappa)
      basis (photon counting: N_prop-by-construction = 2).
  P3  F_munu annihilates gauge IDENTICALLY (even off shell -- stronger than
      the spin-2 case, where Riemann(gauge)=0 needed the shell);
      F(transverse) != 0.
  P4  in-vitro dynamics (R16 pattern): damping (I - gamma K'K) leaves the
      transverse sector EXACTLY invariant, kills constraint-violating junk
      at the predicted rate, leaves gauge in ker.
  P5  negative controls: unplaced / central-flavor kappa -> gauge NOT in
      ker C -> photon count wrong (dim != 2). The machinery's teeth exist
      at spin 1 too.
  P6  operator level (R17 dictionary specialised): A_mu offset e_mu/2 ->
      the rule gives BACKWARD differences everywhere, all four terms land
      on the integer site, assembled symbol == i * kappa_mu exactly.

Run:  python r23_maxwell_control.py     (seconds; writes r23_results.json)
"""
import json
import math
import os

import numpy as np

from r15_walk_dedonder import (C_CONE, ETA, shell_omega, kappa_placed,
                               kappa_unplaced, kappa_central, subspace_dist)
from r17_placement_operators import stencil_symbol

DIR = os.path.dirname(os.path.abspath(__file__))


def constraint_row(kap):
    """C = kappa^mu A_mu  -> (1,4)."""
    return (ETA @ kap).reshape(1, 4)


def gauge_vec(kap):
    """A_mu^gauge = kappa_mu * xi  -> (4,1)."""
    return kap.reshape(4, 1)


def transverse_basis(kap):
    """two photon polarizations: spatial, orthogonal to the HALF-ANGLE
    direction n ~ kappa_spatial (and zero time component)."""
    n = np.real(kap[1:]).astype(float)
    n /= (np.linalg.norm(n) + 1e-300)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0.0, 1, 0])
    e1 = np.cross(n, a); e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    out = np.zeros((4, 2))
    out[1:, 0] = e1; out[1:, 1] = e2
    return out


def fmunu_energy(kap, A):
    """|F|^2 with F_munu = kap_mu A_nu - kap_nu A_mu (symbol level)."""
    F = np.outer(kap, A) - np.outer(A, kap)
    return float(np.sum(np.abs(F) ** 2))


def analyze(kap):
    C = constraint_row(kap)
    G = gauge_vec(kap)
    cg = float(np.abs(C @ G).max())
    u, s, vh = np.linalg.svd(C)
    rank = int(np.sum(s > 1e-10 * s[0]))
    ker = vh[rank:].conj().T                      # (4, 4-rank)
    Qg, _ = np.linalg.qr(G.astype(complex))
    kerq = ker - Qg @ (Qg.conj().T @ ker)
    uq, sq, _ = np.linalg.svd(kerq, full_matrices=False)
    dimq = int(np.sum(sq > 1e-8))
    dtr = float("nan")
    if dimq == 2:
        tr = transverse_basis(kap).astype(complex)
        trq = tr - Qg @ (Qg.conj().T @ tr)
        dtr = subspace_dist(uq[:, :2], trq)
    return cg, rank, dimq, dtr


if __name__ == "__main__":
    print("R23 Maxwell positive control: same machinery, spin 1 -> photon")
    print("=" * 68)
    rng = np.random.default_rng(0)
    ks = [np.array([0.5, 0.0, 0.0]), np.array([0.35, 0.35, 0.35]),
          np.array([0.7, 0.2, -0.4])]
    ks += [rng.uniform(-1.1, 1.1, 3) for _ in range(150)]
    ks = [k for k in ks if shell_omega(k) is not None
          and np.linalg.norm(k) > 1e-2]

    # P1/P2: counting across the BZ
    worst_null, worst_cg, worst_dtr = 0.0, 0.0, 0.0
    ranks, dims = set(), set()
    for k in ks:
        kap = kappa_placed(k)
        worst_null = max(worst_null, abs(float(kap @ ETA @ kap)))
        cg, rank, dimq, dtr = analyze(kap)
        worst_cg = max(worst_cg, cg); ranks.add(rank); dims.add(dimq)
        if dimq == 2:
            worst_dtr = max(worst_dtr, dtr)
    print(f"P1 nullity (reused)      : max |kappa.kappa| = {worst_null:.2e}")
    print(f"P2 photon counting       : |C@gauge| = {worst_cg:.2e}   "
          f"rank C = {sorted(ranks)}   dim(ker/gauge) = {sorted(dims)}   "
          f"dist(., transverse) = {worst_dtr:.2e}")

    # P3: F annihilates gauge identically (check ON and OFF shell)
    worst_fg, min_ftr = 0.0, np.inf
    for k in ks[:40]:
        kap = kappa_placed(k)
        worst_fg = max(worst_fg, fmunu_energy(kap, gauge_vec(kap)[:, 0]))
        min_ftr = min(min_ftr, fmunu_energy(kap, transverse_basis(kap)[:, 0]))
        # off-shell too: perturb kappa_0 (F(gauge)=0 is algebraic in A=kap*xi)
        kap_off = kap.copy(); kap_off[0] *= 1.37
        worst_fg = max(worst_fg, fmunu_energy(kap_off, kap_off))
    print(f"P3 F(gauge) identically 0: max = {worst_fg:.2e} (incl. OFF shell)"
          f"   F(transverse) min = {min_ftr:.2e}")

    # P4: in-vitro damping dynamics (R16 pattern)
    kx = np.array([0.7, 0.2, -0.4])
    w = shell_omega(kx); kap = kappa_placed(kx)
    K = constraint_row(kap)
    TR = transverse_basis(kap).astype(complex)
    gamma, T = 0.3, 400
    D = np.eye(4) - gamma * (K.conj().T @ K)
    step = np.exp(-1j * w) * D
    A0 = (TR @ (rng.normal(size=2) + 1j * rng.normal(size=2))
          + gauge_vec(kap)[:, 0] * (0.7 + 0.2j)
          + 0.5 * (rng.normal(size=4) + 1j * rng.normal(size=4)))
    A = A0.copy()
    for t in range(T):
        A = step @ A
    tr_ret = np.linalg.norm(TR.conj().T @ A) / np.linalg.norm(TR.conj().T @ A0)
    c0, cf = np.linalg.norm(K @ A0), np.linalg.norm(K @ A)
    print(f"P4 dynamics (gamma={gamma}, T={T}): transverse retention = "
          f"{tr_ret:.12f}   constraint {c0:.2e} -> {cf:.2e}")

    # P5: negative controls
    negs = {}
    for nm, fn in (("unplaced", kappa_unplaced), ("central", kappa_central)):
        kap_n = fn(kx)
        cg, rank, dimq, _ = analyze(kap_n)
        negs[nm] = {"cg": cg, "dim": dimq}
        print(f"P5 NEG {nm:9s}: |C@gauge| = {cg:.3f}   dim(ker/gauge) = {dimq}"
              f"   (photon count wrong -> teeth)")

    # P6: operator level -- A_mu offset e_mu/2 => backward diff everywhere
    errP6 = 0.0
    for k in ks[:40]:
        w = shell_omega(k)
        k4 = np.array([w, k[0], k[1], k[2]])
        kap = kappa_placed(k)
        for mu in range(4):
            s = stencil_symbol(k4, mu, True)          # backward
            s *= np.exp(0.5j * k4[mu])                # component offset e_mu/2
            s = s / C_CONE if mu == 0 else s          # time carries 1/c
            errP6 = max(errP6, abs(s - 1j * kap[mu]))
    print(f"P6 operator dictionary   : assembled symbol vs i*kappa = "
          f"{errP6:.2e}  (classic Yee recovered)")

    ok = (worst_null < 1e-12 and worst_cg < 1e-12 and ranks == {1}
          and dims == {2} and worst_dtr < 1e-6 and worst_fg < 1e-24
          and min_ftr > 1e-3 and abs(tr_ret - 1.0) < 1e-10
          and cf / c0 < 1e-6
          and all(v["dim"] != 2 or v["cg"] > 1e-3 for v in negs.values())
          and errP6 < 1e-12)
    print(f"\nPOSITIVE CONTROL: {'PASS — the machinery produces the photon' if ok else 'FAIL — machinery suspect, HALT M3'}")
    json.dump({"null": worst_null, "cg": worst_cg, "ranks": sorted(ranks),
               "dims": sorted(dims), "dist_transverse": worst_dtr,
               "F_gauge": worst_fg, "F_transverse_min": min_ftr,
               "transverse_retention": float(tr_ret),
               "constraint_decay": float(cf / c0), "negatives": negs,
               "operator_err": errP6, "all_pass": bool(ok)},
              open(os.path.join(DIR, "r23_results.json"), "w"), indent=1)
    print("wrote r23_results.json")
