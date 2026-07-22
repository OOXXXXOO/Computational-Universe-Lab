"""R15 — the walk's OWN staggered de Donder: Yee placement + half-angle null
structure close the DOF half of the #43x obstruction.

LANE B's DIAGNOSIS (verified here, quantitatively): on the walk shell
    sin^2(omega/2) = c^2 * sum_i sin^2(k_i/2)          (half-angle shell)
slaving the 0-nu rows with ANY unplaced difference flavor cannot make
{C=0} = TT (+) gauge. Correct: the failure is a PHASE mismatch, and the cure
is field PLACEMENT, not flavor tuning.

T8 (Yee placement -> real symbols -> exact nullity)
    Place h_munu at x + (e_mu + e_nu)/2 (index 0 = half step in time; this is
    the gravitational Yee lattice). Then each forward difference delta_mu,
    read at the natural staggered point, has the PURE symbol
        kappa_0 = 2 sin(omega/2)/c,   kappa_i = 2 sin(k_i/2)
    (no stray e^{i k/2} phases -- they are absorbed by placement), and on the
    walk shell   kappa . kappa = -kappa_0^2 + sum kappa_i^2 = 0  EXACTLY.
    NOTE vs M1's "literal Yee -> N_prop=5": that was Yee-reconstructed
    STRIDE-1 CURRENTS fed to the WIDE BOX (calculus mismatch). Here the
    evolution itself is the walk -- half-angle native -- and Yee placement IS
    its own calculus. Same word, opposite role.

T9 (constraint surface = TT (+) gauge, verbatim continuum algebra)
    With C_nu = kappa^mu hbar_munu (de Donder in the placed calculus):
      * gauge modes  hbar = kappa (x) xi + xi (x) kappa - eta (kappa.xi)
        satisfy C = (kappa.kappa) xi = 0 ON SHELL, exactly;
      * rank C = 4 at generic k; ker C = 6-dim = gauge(4) (+) TT(2);
      * ker C / gauge  ==  TT built on the HALF-ANGLE direction
        n ~ (2 sin(k_i/2))  -- NOT on k_i. (Operational: the emergence
        judge's TT projector must use the kappa direction.)

NEGATIVE CONTROLS (explain [5,6,5,5] quantitatively)
    * unplaced forward flavor: symbols keep e^{+-i k/2} phases ->
      |kappa'.kappa'| = O(1) on shell -> gauge modes NOT in ker C';
    * central flavor (sin k, sin omega) on the walk shell: nullity fails
      except k -> 0 -> same verdict.
    In both, damping toward {C'=0} treats gauge as physical -> N_prop > 2.

Run:  python r15_walk_dedonder.py     (seconds; writes r15_results.json)
"""
import json
import math
import os

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
C_CONE = math.cos(math.pi / 3.0)      # walk cone speed at lane B's theta


ETA = np.diag([-1.0, 1.0, 1.0, 1.0])


def shell_omega(k, c=C_CONE):
    s = np.sqrt(sum(np.sin(ki / 2.0) ** 2 for ki in k))
    arg = c * s
    if arg > 1.0:
        return None                    # outside the walk band
    return 2.0 * math.asin(arg)


def kappa_placed(k, c=C_CONE):
    """T8: placed (real) half-angle symbols on the shell."""
    w = shell_omega(k, c)
    if w is None:
        return None
    return np.array([2.0 * math.sin(w / 2.0) / c] +
                    [2.0 * math.sin(ki / 2.0) for ki in k])


def kappa_unplaced(k, c=C_CONE):
    """negative control 1: forward differences WITHOUT Yee placement --
    complex symbols with surviving half-phases."""
    w = shell_omega(k, c)
    if w is None:
        return None
    k0 = (-2j) * math.sin(w / 2.0) * np.exp(-1j * w / 2.0) / c
    return np.array([k0] + [2j * math.sin(ki / 2.0) * np.exp(1j * ki / 2.0)
                            for ki in k])


def kappa_central(k, c=C_CONE):
    """negative control 2: central-1 symbols evaluated on the WALK shell."""
    w = shell_omega(k, c)
    if w is None:
        return None
    return np.array([math.sin(w) / c] + [math.sin(ki) for ki in k])


# ------------------------------------------------------------ linear algebra
SYM = [(m, n) for m in range(4) for n in range(m, 4)]     # 10 packed indices


def unpack(v10):
    H = np.zeros((4, 4), dtype=complex)
    for c10, (m, n) in enumerate(SYM):
        H[m, n] = H[n, m] = v10[c10]
    return H


def pack(H):
    return np.array([H[m, n] for (m, n) in SYM])


def constraint_matrix(kap):
    """C_nu = kappa^mu hbar_munu  -> (4, 10)."""
    kup = ETA @ kap                                       # kappa^mu
    C = np.zeros((4, 10), dtype=complex)
    for c10, (m, n) in enumerate(SYM):
        for nu in range(4):
            val = 0.0
            if n == nu:
                val += kup[m]
            if m == nu and m != n:
                val += kup[n]
            elif m == nu and m == n:
                pass                                       # already counted
            C[nu, c10] += val
        # note: for m==n the single term kup[m] delta_{n nu} suffices
    return C


def gauge_block(kap):
    """(10, 4): xi -> hbar_gauge = kap xi + xi kap - eta (kap.xi)."""
    G = np.zeros((10, 4), dtype=complex)
    for a in range(4):
        xi = np.zeros(4); xi[a] = 1.0
        kdotxi = float(xi @ ETA @ kap) if np.isrealobj(kap) else (xi @ ETA @ kap)
        H = np.outer(kap, xi) + np.outer(xi, kap) - ETA * kdotxi
        G[:, a] = pack(H)
    return G


def tt_basis(kap):
    """2 TT modes transverse to the HALF-ANGLE spatial direction."""
    n = np.real(kap[1:]).astype(float)
    n = n / (np.linalg.norm(n) + 1e-300)
    # two unit vectors orthogonal to n
    a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(n, a); e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    plus = np.outer(e1, e1) - np.outer(e2, e2)
    cross = np.outer(e1, e2) + np.outer(e2, e1)
    out = np.zeros((10, 2), dtype=complex)
    for i, pol in enumerate((plus, cross)):
        H = np.zeros((4, 4), dtype=complex)
        H[1:, 1:] = pol
        out[:, i] = pack(H)
    return out


def subspace_dist(A, B):
    """max principal-angle sine between col spaces (0 = identical)."""
    Qa, _ = np.linalg.qr(A); Qb, _ = np.linalg.qr(B)
    s = np.linalg.svd(Qa.conj().T @ Qb, compute_uv=False)
    return float(np.sqrt(max(0.0, 1.0 - min(s) ** 2)))


def analyze(kap):
    """returns nullity |kap.kap|, ||C @ gauge||, rank C, dim ker, and
    distance( ker C  mod gauge , TT )."""
    null = abs(complex(kap @ ETA @ kap))
    C = constraint_matrix(kap)
    G = gauge_block(kap)
    cg = float(np.abs(C @ G).max())
    u, s, vh = np.linalg.svd(C)
    rank = int(np.sum(s > 1e-10 * s[0]))
    ker = vh[rank:].conj().T                              # (10, 10-rank)
    # quotient by gauge: project ker onto complement of gauge span
    Qg, _ = np.linalg.qr(G)
    kerq = ker - Qg @ (Qg.conj().T @ ker)
    uq, sq, _ = np.linalg.svd(kerq, full_matrices=False)
    dimq = int(np.sum(sq > 1e-8))
    phys = uq[:, :dimq]
    # compare IN THE QUOTIENT: project the TT representative onto the same
    # gauge-complement before measuring subspace distance (raw TT is a
    # different representative of the same classes).
    tt = tt_basis(kap)
    ttq = tt - Qg @ (Qg.conj().T @ tt)
    dtt = subspace_dist(phys, ttq) if dimq == 2 else float("nan")
    return null, cg, rank, ker.shape[1], dimq, dtt


if __name__ == "__main__":
    print("R15 walk staggered de Donder: Yee placement + half-angle nullity")
    print("=" * 68)
    rng = np.random.default_rng(0)
    kset = [np.array([0.3, 0.0, 0.0]), np.array([0.4, 0.4, 0.4]),
            np.array([0.7, 0.2, -0.5])]
    kset += [rng.uniform(-1.2, 1.2, 3) for _ in range(200)]
    kset = [k for k in kset if shell_omega(k) is not None
            and np.linalg.norm(k) > 1e-2]

    worst = {"null": 0.0, "cg": 0.0, "dtt": 0.0}
    ranks, dims = set(), set()
    for k in kset:
        kap = kappa_placed(k)
        null, cg, rank, dker, dimq, dtt = analyze(kap)
        worst["null"] = max(worst["null"], null)
        worst["cg"] = max(worst["cg"], cg)
        worst["dtt"] = max(worst["dtt"], dtt)
        ranks.add(rank); dims.add(dimq)
    print(f"T8/T9 PLACED half-angle ({len(kset)} k incl. random 3D):")
    print(f"   max |kappa.kappa| on shell      = {worst['null']:.2e}")
    print(f"   max ||C @ gauge||               = {worst['cg']:.2e}")
    print(f"   rank C = {sorted(ranks)}   dim(ker C / gauge) = {sorted(dims)}")
    print(f"   max dist(ker/gauge , TT(kappa)) = {worst['dtt']:.2e}")

    # negative controls at a representative generic k
    kx = np.array([0.7, 0.2, -0.5])
    for name, fn in (("unplaced forward", kappa_unplaced),
                     ("central flavor  ", kappa_central)):
        kap = fn(kx)
        null, cg, rank, dker, dimq, dtt = analyze(kap)
        print(f"NEG {name}: |kappa.kappa| = {null:.3f}   ||C@gauge|| = {cg:.3f}"
              f"   dim(ker/gauge) = {dimq}  (gauge NOT killed by C -> N_prop>2)")

    ok = (worst["null"] < 1e-12 and worst["cg"] < 1e-12
          and ranks == {4} and dims == {2} and worst["dtt"] < 1e-6)
    # negative controls: nullity must be VIOLATED (any nonzero = gauge leaks
    # through the constraint; its magnitude sets the leak rate -- the small
    # central-flavor value 0.035 is exactly why lane B saw a slow bleed to
    # N_prop 5-6 rather than a clean 6) and the quotient must not be 2.
    n1 = abs(complex(kappa_unplaced(kx) @ ETA @ kappa_unplaced(kx)))
    n2 = abs(complex(kappa_central(kx) @ ETA @ kappa_central(kx)))
    d1 = analyze(kappa_unplaced(kx))[4]
    d2 = analyze(kappa_central(kx))[4]
    teeth = n1 > 1e-6 and n2 > 1e-6 and d1 != 2 and d2 != 2
    print(f"\ncertificates: T8/T9 {'PASS' if ok else 'FAIL'}   "
          f"negative-control teeth {'PASS' if teeth else 'FAIL'}")
    json.dump({"worst": worst, "ranks": sorted(ranks), "dims": sorted(dims),
               "neg_unplaced_null": n1, "neg_central_null": n2,
               "all_pass": bool(ok and teeth)},
              open(os.path.join(DIR, "r15_results.json"), "w"), indent=1)
    print("wrote r15_results.json")
