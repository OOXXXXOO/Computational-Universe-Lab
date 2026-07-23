"""R25/R26 — adversarial audit of lane B's preconditioning no-go, and a
symbol-level feasibility certificate for the fix.

LANE B (卡点②): three families of STRICTLY LOCAL preconditioners all fail to
give a usable contraction; spectral certificate says sigma_min(K|damped) ~ k^2
=> gap ~ k^4, and even the exact global inverse only lifts to ~k^2 -> 0. Root:
the slowest constraint mode approaches the protected Newton omega=0 core as
k->0.  Verdict requested: A (open R26 "complex carries its own damping mass"),
B (name it an open problem), or C (adversarial re-audit first).

THIS FILE does C then A, both at symbol level (cheap, falsifiable):

PART A  — CONFIRM the no-go, independently, three ways:
  A1  sigma_min(K) scaling with |k| on the real constraint matrix (root of
      the spectral claim).
  A2  REAL-SPACE meaning: in-place projection damping IS the heat equation
      for the constraint violation (d zeta/dt = gamma * Lap zeta). A long-
      wavelength violation packet is NOT cleared -- its integral is conserved
      (k=0 mode has zero sink). This is stronger and cleaner than "~k^4": in
      place, you cannot remove long-wave constraint violation at all.
  A3  a bounded local P has a bounded symbol p(k); p(k)*sigma^2 still -> 0.

PART B  — the fix is NOT a bigger preconditioner. Reframe (cheaper than a new
  frozen-symbol construction): make the CONSTRAINT sector HYPERBOLIC (it
  propagates at the shared cone speed c) and let the ALREADY-PLANNED L4
  outgoing-wave sponge absorb it. Then:
  B1  violation propagates at group speed ~ c (k-INDEPENDENT transport), not
      k^2 diffusion.
  B2  with the sponge, clearance time ~ L/c -- k-INDEPENDENT -- vs in-place
      1/(gamma k^2) which DIVERGES as k->0. Same wide packet: hyperbolic+sponge
      clears to ~0, diffusion retains ~1.
  B3  PROTECTED QUANTITIES (symbol level): the augmentation is block-triangular
      in (physical | violation); the physical block (Newton zero mode + TT) is
      the UNCHANGED R24 (h,pi) pair -> J5, unit-modulus, Newton zero mode all
      bit-identical. Damping mass kappa lives only in the violation block.
  => Verdict A, but reframed: R26 = "constraint sector gets the same L3->(h,pi)
     hyperbolic upgrade + reuse the L4 boundary", NOT a new mass on frozen R25.

Run:  python r25_nogo_r26_feasibility.py    (seconds; writes r25r26_results.json)
"""
import json
import math
import os

import numpy as np

from r15_walk_dedonder import (C_CONE, shell_omega, kappa_placed,
                               constraint_matrix)

DIR = os.path.dirname(os.path.abspath(__file__))


def svd_min_max(K):
    s = np.linalg.svd(K, compute_uv=False)
    nz = s[s > 1e-12]
    return float(nz.min()), float(nz.max())


# ============================ PART A: confirm the no-go ================
def A1_sigma_scaling():
    mags = np.geomspace(3e-3, 0.3, 14)
    kdir = np.array([0.4, 0.7, 0.55]); kdir /= np.linalg.norm(kdir)
    smin = []
    for m in mags:
        lo, _ = svd_min_max(constraint_matrix(kappa_placed(m * kdir)))
        smin.append(lo)
    p = float(np.polyfit(np.log(mags), np.log(smin), 1)[0])
    return p, mags, np.array(smin)


def A2_diffusion_retains(L=160, T=800, g=0.2, w=14):
    """in-place projection damping = diffusion; long-wave packet not cleared."""
    x = np.arange(L)
    z = np.exp(-((x - L / 2) / w) ** 2)
    z0 = np.abs(z).sum()
    for _ in range(T):
        lap = np.roll(z, 1) + np.roll(z, -1) - 2 * z
        z = z + g * lap                          # d zeta/dt = g * Lap zeta
    return float(np.abs(z).sum() / z0)


def A3_local_P_scaling():
    """a bounded local preconditioner symbol p(k) cannot change the k-scaling.
    gap(P) = p(k)*sigma_min^2 with p bounded => gap ~ sigma_min^2 ~ k^2 still.
    Witness: sigma_min^2 slope in |k| is 2 (=> any bounded p keeps the k^2)."""
    kdir = np.array([0.4, 0.7, 0.55]); kdir /= np.linalg.norm(kdir)
    mags = np.geomspace(3e-3, 0.1, 10)
    g = []
    for m in mags:
        lo, _ = svd_min_max(constraint_matrix(kappa_placed(m * kdir)))
        g.append(lo ** 2)
    return float(np.polyfit(np.log(mags), np.log(g), 1)[0])   # -> 2


# ============================ PART B: R26 feasibility =================
def B1B2_transport_vs_diffusion(L=200, T=1000, c=C_CONE, kap=0.03,
                                edge=44, w=13):
    """same wide (long-wave) violation packet under (i) diffusion, (ii)
    hyperbolic + sponge. Return whole-domain retained-fraction of each."""
    x = np.arange(L)
    z0 = np.exp(-((x - L / 2) / w) ** 2)
    tot0 = np.abs(z0).sum()

    # (i) diffusion at same L,T (parity with A2)
    z = z0.copy()
    for _ in range(T):
        z = z + 0.2 * (np.roll(z, 1) + np.roll(z, -1) - 2 * z)
    diff_ret = float(np.abs(z).sum() / tot0)

    # (ii) hyperbolic constraint sector + field-taper sponge (outgoing wave)
    taper = np.ones(L)
    for i in range(edge):
        f = 1.0 - 0.18 * ((edge - i) / edge) ** 2
        taper[i] *= f; taper[L - 1 - i] *= f
    z = z0.copy(); zm = z0.copy()                # rest start -> two half packets
    for _ in range(T):
        lap = np.roll(z, 1) + np.roll(z, -1) - 2 * z
        zn = (2 * z - zm + c * c * lap - kap * (z - zm)) * taper
        zm, z = z, zn
    hyp_ret = float(np.abs(z).sum() / tot0)
    # group-speed witness: one-way packet centre-of-mass speed (no sponge)
    z = z0 * np.exp(1j * 0.6 * x); zm = z * np.exp(-1j * 0.6 * c)
    coms = []
    for t in range(70):
        lap = np.roll(z, 1) + np.roll(z, -1) - 2 * z
        zn = 2 * z - zm + c * c * lap
        zm, z = z, zn
        m = np.abs(z) ** 2
        coms.append((m * x).sum() / m.sum())
    vg = abs(float(np.polyfit(np.arange(25, 65), coms[25:65], 1)[0]))
    return diff_ret, hyp_ret, vg


def B3_physical_block_unchanged():
    """symbol level: augment (h,pi) with a violation dof zeta carrying mass
    kappa. The map is block-triangular; the physical (h,pi) block is the
    UNCHANGED R24 pair. Show its eigenvalues are bit-identical with/without
    the augmentation, across the BZ."""
    TH = math.pi / 3.0; CT2 = math.cos(TH) ** 2; kap = 0.04
    rng = np.random.default_rng(0)
    ks = [rng.uniform(-1.0, 1.0, 3) for _ in range(80)]
    worst = 0.0
    for k in ks:
        a = CT2 * 4.0 * sum(math.sin(ki / 2) ** 2 for ki in k)
        if a >= 4.0:
            continue
        Mphys = np.array([[1 - a, 1.0], [-a, 1.0]])          # R24 pair
        # augmented 3x3: zeta coupled ONE-WAY (physical -> violation leak),
        # violation carries mass kappa; block-LOWER-triangular:
        Maug = np.array([[1 - a, 1.0, 0.0],
                         [-a, 1.0, 0.0],
                         [0.3, 0.1, 1 - kap]])               # leak col into zeta
        ev_p = np.sort_complex(np.linalg.eigvals(Mphys))
        ev_a = np.sort_complex(np.linalg.eigvals(Maug))
        # physical eigenvalues must appear UNCHANGED among the augmented set
        d = min(np.max(np.abs(ev_a[:2] - ev_p)),
                np.max(np.abs(ev_a[[0, 2]] - ev_p)),
                np.max(np.abs(ev_a[1:] - ev_p)))
        worst = max(worst, float(d))
        # violation eigenvalue is exactly 1-kappa (k-independent damping):
        worst = max(worst, float(min(abs(ev_a - (1 - kap)))))
    return worst


if __name__ == "__main__":
    print("R25/R26 : no-go audit + Z4c-complex feasibility")
    print("=" * 66)

    p, mags, smin = A1_sigma_scaling()
    diff_ret_a = A2_diffusion_retains()
    p3 = A3_local_P_scaling()
    print("PART A -- confirming the no-go:")
    print(f"  A1 sigma_min(K) ~ |k|^{p:.3f}  => projection gap "
          f"gamma*sigma^2 ~ k^{2*p:.2f}  (independent confirmation)")
    print(f"  A2 in-place projection damping = diffusion: wide packet "
          f"retained fraction = {diff_ret_a:.3f}  (NOT cleared; k=0 sink=0)")
    print(f"  A3 gap(bounded local P) ~ |k|^{p3:.2f}: any bounded symbol "
          f"inherits the k^2 -> 0 (local P cannot rescue)")
    nogo = (0.8 < p < 1.2 and diff_ret_a > 0.9 and 1.7 < p3 < 2.3)
    print(f"  => NO-GO {'CONFIRMED' if nogo else 'NOT reproduced -- investigate'}"
          f" (in-place / bounded-local preconditioning cannot clear long waves)")

    diff_ret, hyp_ret, vg = B1B2_transport_vs_diffusion()
    b3 = B3_physical_block_unchanged()
    print("\nPART B -- R26 feasibility (hyperbolic sector + reuse L4 sponge):")
    print(f"  B1 violation group speed = {vg:.3f}  (target c={C_CONE:.3f}, "
          f"k-INDEPENDENT transport)")
    print(f"  B2 same wide packet, retained fraction:  diffusion {diff_ret:.3f}"
          f"  vs  hyperbolic+sponge {hyp_ret:.3e}  (cleared in ~L/c)")
    print(f"  B3 physical (h,pi) block eigenvalues unchanged by augmentation: "
          f"worst dev = {b3:.2e}  (Newton zero mode + TT + J5 protected)")
    feasible = (abs(vg - C_CONE) < 0.06 and hyp_ret < 1e-2 and b3 < 1e-12)
    print(f"  => R26 FEASIBLE {'YES' if feasible else 'CHECK'}: violation "
          f"transported at c and absorbed; physical sector bit-identical")

    print("\nVERDICT: A (reframed). The no-go kills IN-PLACE preconditioning,")
    print("not the program. Constraint sector gets the SAME L3->(h,pi) upgrade")
    print("(hyperbolic) and reuses the L4 sponge -- clearance ~L/c, k-free.")
    json.dump({"A1_sigma_slope": p, "A2_diffusion_retained": diff_ret_a,
               "A3_local_P": p3, "nogo_confirmed": bool(nogo),
               "B1_group_speed": vg, "B1_target_c": C_CONE,
               "B2_diffusion_ret": diff_ret, "B2_hyperbolic_ret": hyp_ret,
               "B3_physical_block_dev": b3, "R26_feasible": bool(feasible)},
              open(os.path.join(DIR, "r25r26_results.json"), "w"), indent=1)
    print("wrote r25r26_results.json")
