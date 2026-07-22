"""R17 — the placement-operator dictionary: how to realize kappa_placed with
INTEGER arrays and one-line difference templates (closes CP1's only blocker).

WHY CP1 FELL INTO THE NEGATIVE CONTROLS.  R15 said "arrays unchanged, pick the
read-out point by placement" -- too vague. Taken literally as a first-order
difference on the integer grid (central/forward/backward), you get exactly
R15's own negative controls (|kappa.kappa| = 0.064 / 0.65-2.35, dim = 6),
because kappa_i = 2 sin(k_i/2) is a HALF-frequency symbol: no integer-grid
stencil produces it in isolation.

THE ACTUAL DICTIONARY.  Keep integer storage, but BOOK-KEEP each component's
Yee offset and choose the stencil per (component, direction) so that the half
phases cancel in C_nu as a whole:

    hbar_{mu nu}  lives at   x + (e_mu + e_nu)/2       (offset vector o(mu,nu))
    C_nu = sum_mu eta^{mu mu} D^{(mu,nu)}_mu hbar_{mu nu}   lives at  x + e_nu/2

    stencil rule:  D_mu acting on a component whose offset HAS the half step
                   in direction mu  ->  BACKWARD difference  (f(x) - f(x-e_mu))
                   ...does NOT have it  ->  FORWARD difference (f(x+e_mu) - f(x))

Both choices move the read-out point by exactly -1/2 or +1/2 in direction mu,
i.e. each term lands on the SAME target point x + e_nu/2, and its symbol is
    (+-)(e^{+- i k_mu/2}) * (2i sin(k_mu/2)) * (offset phase of the component)
whose phases cancel identically, leaving the pure real symbol
    kappa_mu = 2 sin(k_mu / 2)   (and kappa_0 = 2 sin(omega/2)/c in time).

So: the array is integer-indexed; the OFFSET TABLE decides fwd-vs-bwd; nothing
is interpolated. This file certifies the dictionary at operator level.

CERTIFICATES
  A  template symbols: fwd/bwd extraction is machine-exact vs analytic.
  B  operator-level kappa: for every (mu,nu) component and every direction,
     the assembled symbol equals kappa_placed EXACTLY (phases cancel).
  C  R15 suite re-run with the OPERATOR-built constraint: ||C@gauge|| = 0,
     rank C = 4, dim(ker/gauge) = 2 -- on the same random 3D k set.
  D  negative control: ignore the offset table (use one flavor everywhere)
     -> reproduce lane B's measured failure numbers.

Run:  python r17_placement_operators.py     (seconds; r17_results.json)
"""
import json
import math
import os

import numpy as np

from r15_walk_dedonder import (C_CONE, ETA, SYM, shell_omega, kappa_placed,
                               gauge_block, tt_basis, subspace_dist)

DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- placement
def offset(mu, nu):
    """Yee offset o(mu,nu) in units of 1/2 lattice step, as a 4-vector of
    0/1 flags: component hbar_{mu nu} sits at x + (e_mu + e_nu)/2."""
    o = np.zeros(4, dtype=int)
    o[mu] += 1
    o[nu] += 1
    return o % 2                      # e_mu + e_mu = full step -> integer


def stencil_symbol(k4, direction, backward):
    """symbol of the one-step difference in `direction`:
       forward :  f(x+e) - f(x)     ->  e^{i k} - 1  = 2i sin(k/2) e^{ i k/2}
       backward:  f(x)   - f(x-e)   ->  1 - e^{-i k} = 2i sin(k/2) e^{-i k/2}"""
    kd = k4[direction]
    return (np.exp(1j * kd) - 1.0) if not backward else (1.0 - np.exp(-1j * kd))


def component_phase(k4, mu, nu):
    """phase of the component's own offset: e^{i k . o / 2}."""
    o = offset(mu, nu)
    return np.exp(0.5j * float(np.dot(k4, o)))


def target_phase(k4, nu):
    """the constraint C_nu lives at x + e_nu/2 -> phase e^{i k_nu/2}."""
    return np.exp(0.5j * k4[nu])


def operator_kappa(k4, mu, nu, c=C_CONE):
    """assembled symbol of D_mu acting on hbar_{mu nu}, referred to the
    target point x + e_nu/2. The dictionary rule picks the stencil.
    k4 = (omega, k_x, k_y, k_z); the time difference carries the 1/c of
    the cone (kappa_0 = 2 sin(omega/2)/c) -- keeping omega itself in k4 is
    also what makes the offset PHASES right (a w/c there is wrong on both
    counts; that slip is what made this file's first run fail C)."""
    backward = bool(offset(mu, nu)[mu])          # component has half step in mu
    s = stencil_symbol(k4, mu, backward)
    s = s * component_phase(k4, mu, nu) / target_phase(k4, nu)
    return s / c if mu == 0 else s


def constraint_matrix_op(k4):
    """(4,10) constraint built from the DICTIONARY templates (not from an
    assumed symbol vector)."""
    C = np.zeros((4, 10), dtype=complex)
    for c10, (a, b) in enumerate(SYM):
        for nu in range(4):
            # C_nu = sum_mu eta^{mu mu} D_mu hbar_{mu nu}; component (a,b)
            # contributes when it equals (mu,nu) in either index order
            if b == nu:
                C[nu, c10] += ETA[a, a] * operator_kappa(k4, a, nu)
            if a == nu and a != b:
                C[nu, c10] += ETA[b, b] * operator_kappa(k4, b, nu)
    return C


def constraint_matrix_naive(k4, backward=False):
    """negative control: one flavor everywhere, no offset book-keeping."""
    C = np.zeros((4, 10), dtype=complex)
    for c10, (a, b) in enumerate(SYM):
        for nu in range(4):
            if b == nu:
                C[nu, c10] += ETA[a, a] * stencil_symbol(k4, a, backward)
            if a == nu and a != b:
                C[nu, c10] += ETA[b, b] * stencil_symbol(k4, b, backward)
    return C


def analyze_C(C, kap):
    G = gauge_block(kap)
    cg = float(np.abs(C @ G).max())
    u, s, vh = np.linalg.svd(C)
    rank = int(np.sum(s > 1e-10 * s[0]))
    ker = vh[rank:].conj().T
    Qg, _ = np.linalg.qr(G)
    kerq = ker - Qg @ (Qg.conj().T @ ker)
    uq, sq, _ = np.linalg.svd(kerq, full_matrices=False)
    dimq = int(np.sum(sq > 1e-8))
    dtt = float("nan")
    if dimq == 2:
        tt = tt_basis(kap)
        ttq = tt - Qg @ (Qg.conj().T @ tt)
        dtt = subspace_dist(uq[:, :2], ttq)
    return cg, rank, dimq, dtt


if __name__ == "__main__":
    print("R17 placement-operator dictionary (integer arrays + offset table)")
    print("=" * 70)
    rng = np.random.default_rng(0)
    ks = [np.array([0.5, 0.0, 0.0]), np.array([0.35, 0.35, 0.35]),
          np.array([0.7, 0.2, -0.4])]
    ks += [rng.uniform(-1.1, 1.1, 3) for _ in range(120)]
    ks = [k for k in ks if shell_omega(k) is not None
          and np.linalg.norm(k) > 1e-2]

    # A: template symbol extraction
    k4t = np.array([0.31, 0.7, 0.2, -0.4])
    errA = 0.0
    for d in range(4):
        for bw in (False, True):
            got = stencil_symbol(k4t, d, bw)
            want = (2j * math.sin(k4t[d] / 2)
                    * np.exp((-0.5j if bw else 0.5j) * k4t[d]))
            errA = max(errA, abs(got - want))
    print(f"A template symbols        : max error = {errA:.2e}")

    # B: operator kappa == kappa_placed, all components/directions
    errB = 0.0
    for k in ks:
        w = shell_omega(k)
        k4 = np.array([w, k[0], k[1], k[2]])
        kap = kappa_placed(k)
        for mu in range(4):
            for nu in range(4):
                got = operator_kappa(k4, mu, nu)
                want = 1j * kap[mu]          # pure real kappa, times i
                errB = max(errB, abs(got - want))
    print(f"B operator kappa == placed: max deviation = {errB:.2e}  "
          f"(all 16 (mu,nu), {len(ks)} k)")

    # C: R15 suite with operator-built C
    worst_cg, ranks, dims, worst_dtt = 0.0, set(), set(), 0.0
    for k in ks:
        w = shell_omega(k)
        k4 = np.array([w, k[0], k[1], k[2]])
        kap = kappa_placed(k)
        # operator C carries an overall factor i (symbols are 2i sin): the
        # constraint SURFACE is unchanged by that scalar; strip for comparison
        C = constraint_matrix_op(k4) / 1j
        cg, rank, dimq, dtt = analyze_C(C, kap)
        worst_cg = max(worst_cg, cg); ranks.add(rank); dims.add(dimq)
        if dimq == 2:
            worst_dtt = max(worst_dtt, dtt)
    print(f"C R15 suite (operator C)  : ||C@gauge|| = {worst_cg:.2e}   "
          f"rank = {sorted(ranks)}   dim(ker/gauge) = {sorted(dims)}   "
          f"dist(.,TT) = {worst_dtt:.2e}")

    # D: negative control -- no offset book-keeping
    kx = np.array([0.7, 0.2, -0.4])
    w = shell_omega(kx)
    k4 = np.array([w, kx[0], kx[1], kx[2]])
    kap = kappa_placed(kx)
    for nm, bw in (("forward-everywhere", False), ("backward-everywhere", True)):
        C = constraint_matrix_naive(k4, bw) / 1j
        cg, rank, dimq, _ = analyze_C(C, kap)
        print(f"D NEG {nm:20s}: ||C@gauge|| = {cg:.3f}  "
              f"dim(ker/gauge) = {dimq}   (lane B's measured failure mode)")

    okA = errA < 1e-13
    okB = errB < 1e-12
    okC = worst_cg < 1e-12 and ranks == {4} and dims == {2} and worst_dtt < 1e-6
    Cn = constraint_matrix_naive(k4, False) / 1j
    okD = analyze_C(Cn, kap)[2] != 2      # gauge NOT quotiented out
    print(f"\ncertificates: A {'PASS' if okA else 'FAIL'}  "
          f"B {'PASS' if okB else 'FAIL'}  C {'PASS' if okC else 'FAIL'}  "
          f"D teeth {'PASS' if okD else 'FAIL'}")
    json.dump({"errA": errA, "errB": errB, "worst_cg": worst_cg,
               "ranks": sorted(ranks), "dims": sorted(dims),
               "worst_dtt": worst_dtt,
               "all_pass": bool(okA and okB and okC and okD)},
              open(os.path.join(DIR, "r17_results.json"), "w"), indent=1)
    print("wrote r17_results.json")
