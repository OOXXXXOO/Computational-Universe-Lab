"""R35 — probe-two pre-check: does the de Donder SLAVE row hit the R29 barrier?

RC3 (合流) precisely localized the residual obstruction into a dichotomy:
  (a) -omega constraint-row curvature (constraint violation propagating);
  (b) +omega GAUGE-propagation: 2 gauge modes IN ker C, yet counted as
      propagating DOF (their discrete curvature != 0 vs the R30 complex).
RC3 suggested probe-two: fix (b) via "exact constraint propagation / de Donder
slave rows" (align with 43x green_one_walk gap).

BEFORE lane B spends probe-two on the slave route, this file checks whether the
de Donder slave row is even LOCAL. The slave expresses the 0-nu (time) rows via
the spatial rows using the constraint C_nu = kappa^mu hbar_mu,nu = 0:

    kappa^0 hbar_{0 nu} + kappa^i hbar_{i nu} = 0
    => hbar_{0 nu} = -(kappa^i / kappa^0) hbar_{i nu}                (SLAVE)

The slave coefficient carries 1/kappa^0. At the PHYSICAL massless point the
graviton dispersion is omega = c|k| + ..., so kappa^0 = 2 sin(omega/2)/c ~ |k|
-> 0 as k -> 0. The ratio kappa^i/kappa^0 ~ k_i/|k| = n_i has a
DIRECTION-DEPENDENT k->0 limit -> non-analytic -> the slave is NON-LOCAL. This
is the SAME k=0 pathology R29 found for the constraint projector P_S (its
direction dependence was 2.449). So the slave route is R29-barred.

CONSEQUENCE for probe-two: do NOT spend it on de Donder slave rows -- that route
is non-local at the massless point (R29). The only remaining hope for (b) is the
COMPLEX route (R30-style: local curl + operator identity, no slave), but that
requires the walk to BE Yee-type, i.e. a structural change to the emergent walk
(breaks emergence). Probe-two should test THAT, not the slave.

Honest: this is R29 applied to the slave mechanism -- a corollary, not a new
theorem. Its value is steering probe-two off a dead route RC3 pointed at.

Run:  python r35_slave_locality.py   (seconds; writes r35_results.json)
"""
import json
import math
import os

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
C_CONE = math.cos(math.pi / 3.0)


def kappa_placed_massless(nk, eps):
    """placed kappa at wavevector eps*nk on the massless shell: omega=c|k|.
    returns (kappa0, kappa_spatial[3])."""
    k = eps * np.asarray(nk, float)
    kmag = np.linalg.norm(k)
    omega = 2.0 * math.asin(min(1.0, C_CONE * math.sin(kmag / 2.0)))  # shell
    kappa0 = 2.0 * math.sin(omega / 2.0) / C_CONE
    kap_i = np.array([2.0 * math.sin(ki / 2.0) for ki in k])
    return kappa0, kap_i


def slave_coeff(nk, eps):
    """slave coefficient vector kappa^i/kappa^0 (what multiplies h_iv to give
    h_0v). Divergence/direction-dependence at k->0 = non-locality."""
    kappa0, kap_i = kappa_placed_massless(nk, eps)
    return kap_i / (kappa0 + 1e-300), kappa0


if __name__ == "__main__":
    print("R35 de Donder slave locality (probe-two pre-check)")
    print("=" * 60)
    dirs = {"axial [1,0,0]": [1, 0, 0], "face [1,1,0]": [1, 1, 0],
            "body [1,1,1]": [1, 1, 1], "skew [0.7,0.2,-0.5]": [0.7, 0.2, -0.5]}
    # normalize directions
    dirs = {k: list(np.array(v) / np.linalg.norm(v)) for k, v in dirs.items()}

    eps = 1e-4
    print(f"slave coefficient kappa^i/kappa^0 as k->0 (eps={eps}):")
    coeffs = {}
    for name, nk in dirs.items():
        c, k0 = slave_coeff(nk, eps)
        coeffs[name] = c
        print(f"  {name:20s}: kappa^0={k0:.2e}  coeff={np.round(c,3)}  "
              f"|coeff|={np.linalg.norm(c):.3f}")

    # direction dependence of the k->0 limit
    cvals = list(coeffs.values())
    worst = 0.0
    for i in range(len(cvals)):
        for j in range(i + 1, len(cvals)):
            worst = max(worst, float(np.linalg.norm(cvals[i] - cvals[j])))
    print(f"\ndirection-dependence of slave coeff at k->0: {worst:.3f}")
    print(f"  (nonzero => non-analytic k=0 limit => slave is NON-LOCAL,")
    print(f"   same pathology as R29's projector P_S direction-dependence 2.449)")

    # also show kappa^0 -> 0 (the vanishing denominator)
    print("\nkappa^0 along the body diagonal as k->0 (the vanishing slave denom):")
    for e in [1e-1, 1e-2, 1e-3, 1e-4]:
        k0, _ = kappa_placed_massless([1, 1, 1], e)
        print(f"  eps={e:.0e}: kappa^0 = {k0:.3e}")

    barred = worst > 0.1
    print("\n" + "-" * 60)
    print(f"VERDICT: de Donder slave route is "
          f"{'R29-BARRED (non-local at massless point)' if barred else 'local?? recheck'}")
    print("  => probe-two should NOT use de Donder slave rows (RC3's suggested")
    print("     route is R29-dead). The only remaining hope for the +omega gauge-")
    print("     propagation half (b) is the COMPLEX route (R30-style local curl +")
    print("     operator identity, no slave) -- which requires the emergent walk")
    print("     to become Yee-type = a STRUCTURAL change (breaks emergence).")
    print("  => probe-two = test whether the walk can be made Yee-type WITHOUT")
    print("     breaking emergence/J5; NOT slave-row patching.")
    print("  Honest: corollary of R29, not a new theorem.")

    json.dump({"slave_coeff_by_dir": {k: v.tolist() for k, v in coeffs.items()},
               "direction_dependence": worst,
               "slave_r29_barred": bool(barred),
               "note": "de Donder slave non-local at massless point; probe-two "
               "should test Yee-type structural route, not slave rows"},
              open(os.path.join(DIR, "r35_results.json"), "w"), indent=1)
    print("\nwrote r35_results.json")
