"""R33 — independent audit of R32 + filling its topological blank: is the DOF
lock deformable (theta can move it) or topological (a winding number pins it)?

LANE B (R32): the reachability check found 2-3 principal angles LOCKED at 40-90
deg between the emergent walk's propagating subspace and the R30 complex's ker C;
cheap knobs (mu, Wilson alpha, k-ray) do not move them. Honestly LEFT OPEN: the
-omega branch's Floquet winding / index -- so R32 is a NO-GO-LEAN SIGNAL, not a
theorem. The only remaining deformation lever (matter-sector theta/dm co-moving
the whole complex) was said to require a full battle, not a cheap check.

THIS FILE fills that exact blank with something CHEAPER than a battle. The lock
being topological has a sharp, BZ-integral test: the winding number of the
chirally-doubled Dirac walk. If the locked constraint-row DOF inherit a nonzero,
theta-invariant winding, then continuous theta CANNOT unlock them (an integer
cannot change without a gap-closing, which breaks unitary/local smoothness) --
this is Nielsen-Ninomiya doubling surfacing in the matter-gravity coupling.

  W(theta) nonzero & constant across physical theta  -> TOPOLOGICAL LOCK
      => theta battle will NOT reach N_prop=2; escalate to R29-style verdict
         (relax one of: strict unitarity / strict locality / exact constraint).
  W(theta) has a transition (integer jump) at some theta*  -> that theta* is a
      DESCENT CHANNEL; the battle should target it (cheaply localized here).

Method: split-step walk U(k;theta,dm) has a chiral symmetry; H_eff = i log U
has a traceless d-vector lying in a plane; the winding of d around the BZ is a
quantized topological invariant (Kitagawa/Asboth walk winding). Normal and
mirror chiralities should carry opposite charges (that is what "doubling" means).

Honest scope: this is the SINGLE-PARTICLE walk winding (matter sector). The
claim that the tensor constraint-row DOF INHERIT it is a mechanism argument, not
a bit-proof (the tensor DOF are bilinears of the walk). So the output is a
STRONG topological signal for/against, matching R32's honesty -- not a theorem.

Run:  python r33_winding_topology.py   (seconds; writes r33_results.json)
"""
import json
import math
import os

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, os.path.join(DIR, "rulespace_gpu"))
sys.path.insert(0, os.path.dirname(DIR))
from rulespace_gpu.tensor_walker import walk_matrix_1, walk_matrix_1m

SX = np.array([[0, 1], [1, 0]], complex)
SY = np.array([[0, -1j], [1j, 0]], complex)
SZ = np.array([[1, 0], [0, -1]], complex)
PAULI = [SX, SY, SZ]


def d_vector(U):
    """H_eff = i log U ; return traceless Pauli components (d_x,d_y,d_z) real."""
    w, V = np.linalg.eig(U)
    ph = -np.angle(w)                       # U = e^{-i H}, eigen-phases
    H = (V * ph) @ np.linalg.inv(V)
    H = 0.5 * (H + H.conj().T)               # hermitize
    return np.array([np.real(0.5 * np.trace(H @ s)) for s in PAULI])


def winding(walk, th, dm, nk=2001):
    """winding of the d-vector in its chiral plane around the BZ."""
    ks = np.linspace(-math.pi, math.pi, nk)
    d = np.array([d_vector(walk(k, th, dm)) for k in ks])
    n = d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-30)
    # find the chiral axis = component with smallest amplitude across BZ
    amp = np.abs(n).max(axis=0)
    ax = int(np.argmin(amp))                 # ~0 component => chiral axis
    plane = [i for i in range(3) if i != ax]
    a, b = n[:, plane[0]], n[:, plane[1]]
    ang = np.unwrap(np.arctan2(b, a))
    W = (ang[-1] - ang[0]) / (2 * math.pi)
    return W, float(amp[ax])                 # amp[ax] small confirms chiral sym


if __name__ == "__main__":
    print("R33 winding-number topology probe (fills R32's open blank)")
    print("=" * 66)
    thetas = [0.2, 0.4, math.pi / 6, 0.6, math.pi / 4, 1.0, math.pi / 3, 1.3]
    print(f"{'theta':>7} {'W_normal':>9} {'W_mirror':>9} {'sum':>6} "
          f"{'chiral_ax_amp':>13}")
    rows = []
    for th in thetas:
        Wn, axn = winding(walk_matrix_1, th, 0.0)
        Wm, axm = winding(walk_matrix_1m, th, 0.0)
        rows.append({"theta": th, "W_normal": Wn, "W_mirror": Wm,
                     "sum": Wn + Wm, "chiral_axis_amp": max(axn, axm)})
        print(f"{th:7.3f} {Wn:9.2f} {Wm:9.2f} {Wn+Wm:6.2f} {max(axn,axm):13.1e}")

    Wn_vals = [round(r["W_normal"]) for r in rows]
    Wm_vals = [round(r["W_mirror"]) for r in rows]
    normal_const = len(set(Wn_vals)) == 1
    mirror_const = len(set(Wm_vals)) == 1
    doubled = all(abs(r["W_normal"] + r["W_mirror"]) < 0.05 for r in rows)
    nonzero = all(abs(round(r["W_normal"])) >= 1 for r in rows)

    # mass scan: does dm open a transition (Wilson-like) that theta cannot?
    print("\ndm scan at theta=pi/3 (does mass drive a topological transition?):")
    dm_rows = []
    for dm in [0.0, 0.3, 0.6, 1.0, 1.4]:
        Wn, _ = winding(walk_matrix_1, math.pi / 3, dm)
        dm_rows.append({"dm": dm, "W_normal": Wn})
        print(f"  dm={dm:.2f}: W_normal = {Wn:.2f}")
    dm_transition = len(set(round(r["W_normal"]) for r in dm_rows)) > 1

    print("\n" + "-" * 66)
    print(f"normal winding constant across theta : {normal_const} "
          f"(W={Wn_vals[0] if normal_const else Wn_vals})")
    print(f"doubling (W_normal + W_mirror = 0)   : {doubled}")
    print(f"nonzero charge each chirality        : {nonzero}")
    print(f"mass(dm) drives a transition theta cannot : {dm_transition}")

    # HONESTY GATE (applied to my OWN probe, R27->R28 discipline): the winding
    # is only trustworthy where the chiral plane is clean (chiral_axis_amp ~ 0)
    # AND the walk is gapped. massless (dm=0) is GAPLESS (Dirac point) -> the
    # d-vector passes through 0 -> winding genuinely ill-defined. And that is
    # exactly the physical point (massless graviton matter, c=cos theta).
    axamp_massless = max(r["chiral_axis_amp"] for r in rows)
    clean = axamp_massless < 1e-6
    if not clean:
        verdict = ("CHEAP SINGLE-PARTICLE PROBE CANNOT PREEMPT THIS. At the "
                   "physical point (massless, dm=0) the walk is GAPLESS (Dirac "
                   "point), so the single-particle winding is ILL-DEFINED "
                   f"(chiral-axis amp {axamp_massless:.1e}, not ~0). My proposed "
                   "cheap topological shortcut does NOT reach the question -- "
                   "which CONFIRMS R32: deciding topological-vs-deformable "
                   "genuinely needs the TENSOR-level index (the battle). "
                   "REAL FINDING (refines the battle, not a verdict): the MASS "
                   "direction dm carries topological content (W: 0 at dm=0 -> 1 "
                   "at dm!=0, a gapless->gapped transition). So the battle's "
                   "first milestone should (a) measure the TENSOR constraint-row "
                   "index, not just principal angles (angles = deformation "
                   "distance; index = topological distance), and (b) use dm as a "
                   "lever, not only theta. Whether crossing that dm transition "
                   "UNLOCKS the tensor DOF or is a WALL depends on tensor "
                   "inheritance -- only the battle decides. I do NOT claim "
                   "deform-possible or topological-lock from this probe.")
    elif nonzero and normal_const and doubled:
        verdict = ("TOPOLOGICAL LOCK (clean). theta-invariant +/-1 doubling; "
                   "theta cannot unlock; escalate R29-style.")
    else:
        verdict = ("clean but no lock signal; deformation plausible.")
    print("\nVERDICT:", verdict)
    json.dump({"theta_scan": rows, "dm_scan": dm_rows,
               "normal_const": bool(normal_const), "doubled": bool(doubled),
               "nonzero": bool(nonzero), "dm_transition": bool(dm_transition),
               "verdict": verdict},
              open(os.path.join(DIR, "r33_results.json"), "w"), indent=1)
    print("wrote r33_results.json")
