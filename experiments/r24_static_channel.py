"""R24 — the omega=0 channel: staggered (h,pi) symplectic pair = the geometry
kernel that keeps the walk shell AND has the Newtonian double pole.

LANE B's L3 WALL (verified logic): a UNITARY first-order kernel has static
response ~ 1/omega ~ 1/k, not 1/k^2 -- "free local unitary walk has no
gapless k^-2 response" boomerangs on geometry. The T-row canary fired as
pre-registered, but the deeper root is the kernel's missing omega=0 double
pole. Meanwhile the wave sector is intact (N_prop=2 incl. diagonal, J5=0).

HONEST SELF-CORRECTION OF R14 (T12). R14 argued "2 bands on the full BZ =>
unitary stride-1 split-step". That over-narrowed: the essential property was
{exactly 2 bands} + {shared half-angle shell}. Unitarity is SUFFICIENT, not
necessary. The time-STAGGERED first-order pair (Yee-FDTD's time structure,
= velocity-Verlet / leapfrog on (h, pi) with pi at half steps)

    pi(t+1/2) = pi(t-1/2) + [ cos^2(th) * Lap_half h(t) + S ]
    h(t+1)    = h(t)      + pi(t+1/2)

with Lap_half = the half-angle staggered Laplacian (symbol -4 sum sin^2(k_i/2))
is the SECOND member of the admissible class, and the one with statics:

  T10 (band census + shell identity): the pair has EXACTLY 2 bands, on
      sin^2(omega/2) = cos^2(th) sum_i sin^2(k_i/2)  -- THE SAME walk shell
      (R15 T8 verbatim) => kappa_placed, R17/R19 placement, Z4c, and the
      J5 dispersion identity with matter all carry over UNCHANGED.
      No mirror band: staggered forward differences, not stride-2 central.
  T11 (static double pole): driven steady state
      h* = S / (4 cos^2 th * sum_i sin^2(k_i/2))  -- exact lattice 1/k^2;
      the Newton well is the EXACT lattice fixed point of the update.
  T13 (well in ker K): the static well (hbar_00 only) satisfies the placed
      de Donder EXACTLY (omega=0 => kappa_0=0 kills the time row; no 0i/ij
      components kills the rest) => Z4c does not fight the well: the L3
      named tension ("Z4c kills Jordan" vs "well needs omega=0") dissolves
      -- the tension was a symptom of the WRONG static shape (1/k), not a
      structural incompatibility.

Run:  python r24_static_channel.py    (seconds; writes r24_results.json)
"""
import json
import math
import os

import numpy as np

from r15_walk_dedonder import (C_CONE, ETA, SYM, shell_omega, kappa_placed,
                               constraint_matrix)

DIR = os.path.dirname(os.path.abspath(__file__))
TH = math.pi / 3.0
CT2 = math.cos(TH) ** 2


def lam_half(k):
    """half-angle staggered (-Laplacian) symbol: 4 sum sin^2(k_i/2)."""
    return 4.0 * sum(math.sin(ki / 2.0) ** 2 for ki in k)


def pair_bands(k):
    """quasi-frequencies of the free staggered pair at k: the one-step map
    M = [[1 - a, 1], [-a, 1]] acting on (h, pi_half), a = CT2*lam_half."""
    a = CT2 * lam_half(k)
    M = np.array([[1.0 - a, 1.0], [-a, 1.0]])
    ev = np.linalg.eigvals(M)
    return np.sort(-np.angle(ev)), ev


if __name__ == "__main__":
    print("R24 omega=0 channel: staggered (h,pi) pair on the walk shell")
    print("=" * 68)
    rng = np.random.default_rng(0)
    ks = [np.array([0.5, 0, 0]), np.array([0.35, 0.35, 0.35]),
          np.array([0.7, 0.2, -0.4])] + [rng.uniform(-1.1, 1.1, 3)
                                         for _ in range(120)]
    ks = [k for k in ks if np.linalg.norm(k) > 1e-2
          and CT2 * lam_half(k) < 4.0]          # pair CFL: a < 4

    # T10: 2 bands, on the walk shell, |eigenvalues| = 1 (marginal-stable)
    worst_shell, worst_mod, nbands = 0.0, 0.0, set()
    for k in ks:
        om, ev = pair_bands(k)
        nbands.add(len(ev))
        worst_mod = max(worst_mod, abs(abs(ev[0]) - 1), abs(abs(ev[1]) - 1))
        w_walk = shell_omega(k)
        if w_walk is not None:
            worst_shell = max(worst_shell, abs(abs(om[-1]) - w_walk))
    print(f"T10 band census/shell : bands = {sorted(nbands)}   "
          f"|eig|-1 max = {worst_mod:.2e}   |omega_pair - omega_walk| max = "
          f"{worst_shell:.2e}  (SAME shell => J5/kappa/R17/R19 unchanged)")

    # T11: static response by ACTUAL ITERATION of the driven pair
    worst_resp = 0.0
    for k in ks[:40]:
        a = CT2 * lam_half(k)
        S = 1.0
        h, p = 0.0, 0.0
        # damped pair iteration to reach the fixed point (tiny friction on pi
        # only for convergence of the probe; fixed point is friction-free)
        for t in range(20000):
            p = 0.995 * p + (-a * h + S)
            h = h + p
        worst_resp = max(worst_resp, abs(h * a / S - 1.0))
    print(f"T11 static double pole: | h* * (CT2 lam) / S - 1 | max = "
          f"{worst_resp:.2e}   (exact lattice 1/k^2 -> Newton ratio 2 "
          f"recoverable at L3-v2)")

    # T13: the static well is in ker K_placed exactly
    worst_kw = 0.0
    for k in ks[:60]:
        kap = kappa_placed(k)
        if kap is None:
            continue
        kap0 = kap.copy(); kap0[0] = 0.0        # omega = 0: kappa_0 = 0
        K = constraint_matrix(kap0)
        well = np.zeros(10); well[0] = 1.0      # hbar_00 only (packed SYM[0])
        worst_kw = max(worst_kw, float(np.abs(K @ well).max()))
    print(f"T13 well in ker K     : |K(omega=0) @ well| max = {worst_kw:.2e}"
          f"   (Z4c does not fight the well; L3 tension dissolves)")

    ok = (nbands == {2} and worst_mod < 1e-9 and worst_shell < 1e-9
          and worst_resp < 1e-3 and worst_kw < 1e-14)
    print(f"\nR24: {'ALL PASS -- L3-v2 kernel spec certified' if ok else 'CHECK'}")
    print("L3-v2 swap: geometry evolution walk-U -> staggered (h,pi) pair;")
    print("EVERYTHING else frozen (kappa_placed constraints, Z4c, R19 storage,")
    print("source chain -- lane B certified it architecture-independent).")
    json.dump({"bands": sorted(nbands), "eig_mod_dev": worst_mod,
               "shell_dev": worst_shell, "static_resp_dev": worst_resp,
               "well_kerK": worst_kw, "all_pass": bool(ok)},
              open(os.path.join(DIR, "r24_results.json"), "w"), indent=1)
    print("wrote r24_results.json")
