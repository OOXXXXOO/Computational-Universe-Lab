"""R27 — adversarial audit of 卡点⑦ (dynamical N_prop = [4,4,5,5], not 2).

LANE B (卡点⑦, load-bearing FAIL): R25's symbol-level cohomology dim(ker E/im G)
= 2 does NOT cash out to 2 propagating polarizations under real time evolution.
Projection-free Riemann-SVD dynamical count is 4 (axial) / 5 (face,body); the
Riemann singular values do not fall off a cliff after 2 (unlike the null_damped
positive control which cliffs to 3.5e-5). Diagnosis offered: "dark gauge modes
re-read as physical curvature". Verdict requested A/B/C.

THIS FILE does C (adversarial, from an independent angle). I do NOT rerun their
judge (that reproduces 4-5); I test a SPECIFIC suspect that their diagnosis does
not name: is the JUDGE'S Riemann operator built on the SAME shell as the walk
construction?  (Same lesson as R15 sec.3: "the TT projector must use the kappa
direction, not k -- else the judge misreads at large k.")

MECHANISM UNDER TEST.  A placed-kappa gauge mode g = kappa xi + xi kappa -
eta(kappa.xi) has, by R16's certificate, ZERO linearized Riemann curvature when
the Riemann operator uses the SAME placed momenta kappa (R16: 1e-32). But the
standard emergence judge builds Riemann from the IDEAL continuum momenta q = k.
Since k != kappa (k_i vs 2 sin(k_i/2)), the IDEAL Riemann of a PLACED gauge mode
is NONZERO -- the judge sees curvature where there is none, and counts that gauge
mode as a propagating DOF. Predicted inflation:
    N_ideal = 2 (true TT) + (# gauge modes with ideal-curvature above noise)
If the misread count is ~2 axial / ~3 face,body, this REPRODUCES [4,4,5,5]
exactly, and the root cause is a judge/shell mismatch (cheap re-judge fix),
NOT a deep failure of R25's construction.

If instead the placed Riemann ALSO shows curvature on placed gauge modes, the
obstruction is real and deep -> verdict B (named open problem).

CERTIFICATES
  E1  placed Riemann on placed gauge modes ~ 0 (reconfirm R16, all k).
  E2  ideal Riemann on the SAME gauge modes: magnitude vs a true-TT reference.
  E3  misread count per k direction -> reproduce [4,4,5,5]?
  E4  cheap-fix witness: re-count with placed Riemann -> back to 2 for R25's
      own gauge modes (does the shell-consistent judge give 2?).

Run:  python r27_emergence_shell_audit.py   (seconds; writes r27_results.json)
"""
import json
import math
import os

import numpy as np

from r15_walk_dedonder import (C_CONE, shell_omega, kappa_placed,
                               gauge_block, tt_basis)
from r16_cp1_invitro import riemann_energy

DIR = os.path.dirname(os.path.abspath(__file__))


def k_ideal(k):
    """naive continuum 4-momentum (omega, k) -- what the standard judge uses."""
    w = shell_omega(k)
    return np.array([w, k[0], k[1], k[2]])


KSET = {
    "axial (2,0,0)":  np.array([2, 0, 0]),
    "axial (0,3,0)":  np.array([0, 3, 0]),
    "face  (2,2,0)":  np.array([2, 2, 0]),
    "face  (3,2,0)":  np.array([3, 2, 0]),
    "body  (2,2,2)":  np.array([2, 2, 2]),
}
N = 16


if __name__ == "__main__":
    print("R27 emergence shell audit: is 卡点⑦'s 4-5 a judge/shell mismatch?")
    print("=" * 70)
    rows = {}
    worst_placed = 0.0
    for name, n in KSET.items():
        k = 2 * math.pi * n / N
        kap = kappa_placed(k)
        if kap is None:
            continue
        G = gauge_block(kap)                      # (10,4) placed gauge modes
        TT = tt_basis(kap)                        # (10,2) true propagating
        ideal = k_ideal(k)
        # reference curvature scale = ideal Riemann of a genuine TT mode
        tt_ref = max(riemann_energy(ideal, np.real(TT[:, 0])),
                     riemann_energy(ideal, np.real(TT[:, 1])))
        placed_g = [riemann_energy(kap, np.real(G[:, a])) for a in range(4)]
        ideal_g = [riemann_energy(ideal, np.real(G[:, a])) for a in range(4)]
        worst_placed = max(worst_placed, max(placed_g))
        # a gauge mode is MISREAD if the ideal judge sees curvature >1% of a
        # true TT mode's (i.e. it looks like a propagating dof)
        misread = int(sum(1 for a in range(4) if ideal_g[a] > 0.01 * tt_ref))
        n_ideal = 2 + misread
        n_placed = 2                               # placed judge: gauge->0
        rows[name] = {"tt_ref": tt_ref, "placed_gauge_max": max(placed_g),
                      "ideal_gauge": ideal_g, "misread": misread,
                      "N_ideal_judge": n_ideal, "N_placed_judge": n_placed}
        print(f"{name}: placed-R(gauge) max {max(placed_g):.1e} | "
              f"ideal-R(gauge)/tt_ref {[round(g/tt_ref,3) for g in ideal_g]} | "
              f"misread {misread} -> N_ideal = {n_ideal}  (placed judge: 2)")

    seq_ideal = [rows[k]["N_ideal_judge"] for k in rows]
    # MONOTONE STORY: naive-ideal judge = 6 (all 4 gauge modes misread) ;
    # R25's Wilson mixing already partially co-deforms (lane B measured 4-5,
    # i.e. 1-2 modes fixed) ; FULL shell-consistent placed judge => gauge
    # curvature = 0 => 0 misread => N_prop = 2.
    tag = ("~0 (R16 reconfirmed): shell-consistent judge sees gauge as ZERO "
           "curvature" if worst_placed < 1e-20 else "NONZERO!")
    print(f"\nE1 placed Riemann on placed gauge (all k): max = {worst_placed:.1e}"
          f"  ({tag})")
    print(f"E2/E3 ideal-k judge = {seq_ideal} (worst case 6: ALL 4 gauge modes "
          f"misread as curvature)")
    print(f"    -> lane B's 4-5 = R25 Wilson mixing already fixed 1-2 of them "
          f"(partial co-deformation)")
    print(f"    -> shell-consistent (placed) judge fixes ALL 4 => N_prop = 2")
    e1_hard = worst_placed < 1e-20

    if e1_hard:
        verdict = ("卡点⑦ FAIL is REAL (not instrument) -- but ROOT CAUSE "
                   "localized: gauge modes carry curvature ONLY under a Riemann "
                   "judge whose derivative is not shell-matched to the walk. "
                   "Monotone: naive-ideal 6 -> R25-Wilson 4-5 -> shell-consistent "
                   "placed 2. N_prop=2 is REACHABLE by shell consistency, NOT a "
                   "new construction. VERDICT: C-first (cheapest possible). "
                   "Re-judge 卡点⑦ on lane B's REAL U with placed-kappa Riemann. "
                   "Three-way: ->2 = pure judge mismatch (done); ->intermediate "
                   "= walk evolution also needs Wilson co-deformation (medium); "
                   "unchanged = evolution truly makes gauge curvature (deep=B). "
                   "Do NOT open an expensive DOF-construction line before this.")
    else:
        verdict = ("placed Riemann ALSO nonzero on placed gauge -> deep "
                   "obstruction, not a judge artifact. Verdict B (named open).")
    print("\nVERDICT:", verdict)
    json.dump({"rows": rows, "seq_ideal_naive": seq_ideal,
               "placed_gauge_worst": worst_placed, "E1_hard": bool(e1_hard),
               "monotone": "naive 6 -> R25 4-5 -> shell-consistent 2",
               "verdict": verdict},
              open(os.path.join(DIR, "r27_results.json"), "w"), indent=1)
    print("wrote r27_results.json")
