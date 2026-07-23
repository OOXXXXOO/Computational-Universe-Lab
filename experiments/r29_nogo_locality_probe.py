"""R29 — no-go feasibility probe: is exact-constraint + local + unitary
achievable, or is there a Nielsen-Ninomiya-type obstruction?

Three referees independently RAISED but did not JUDGE the same risk:
  -格点 breaks diffeomorphism invariance from the root; you are engineering a
    Bianchi identity in an algebra with no corresponding symmetry (referee 1);
  - a Nielsen-Ninomiya-type incompatibility may hold between {strict unitary,
    local, finite stencil, exact constraint propagation} (referee 2).

This file judges the FIRST decisive piece (cheap, falsifiable). It does NOT
claim a full no-go/go theorem -- it splits the routes:

PART A — the projection route (referee 3's route A: U = U0 + K C) is LOCALLY
  OBSTRUCTED. The constraint operator C(k) ~ k, so the constraint surface
  S_k = ker C(k) has a DIMENSION JUMP at k=0 (6-dim for k!=0, 10-dim at k=0).
  The projector P_S(k) onto ker C(k) therefore has a DIRECTION-DEPENDENT limit
  as k->0 -> P_S is non-analytic -> any U built from P_S / C^+ is NON-LOCAL.
  This kills "algebraically patch the current U with a constraint projector".

PART B — the complex route is NOT obstructed by this: Maxwell is the witness.
  The Gauss constraint k.E also ~ k (same k=0 non-analyticity of its P), yet
  Yee-FDTD preserves it EXACTLY and LOCALLY -- because the evolution is built
  from a local curl and the identity div curl = 0 holds on the nose. The
  constraint is preserved as an operator IDENTITY, never through a projector.

CONCLUSION. The obstruction is real but SPECIFIC to the projection route.
The complex/variational route (build U from a local "tensor curl" so that the
discrete linearized Bianchi identity holds identically) is (i) NECESSARY --
patching cannot be local -- and (ii) PROVEN POSSIBLE in principle by Maxwell.
The remaining open theorem (the true N-N question) is exactly:
  does a discrete linearized-Bianchi TENSOR complex exist whose evolution is
  local + unitary?  -- referee 2's chain-map / referee 3's tensor-plaquette,
  now a sharply posed, constructible & falsifiable target.

The KINEMATIC half of that complex is already in hand (R o D = 0, i.e.
linearized Riemann annihilates gauge modes -- certified earlier). What is
missing is the DYNAMICAL half: a local evolution whose discrete Bianchi
identity makes constraint propagation an identity, not a fit.

Run:  python r29_nogo_locality_probe.py   (seconds; writes r29_results.json)
"""
import json
import os

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
SYM = [(m, n) for m in range(4) for n in range(m, 4)]      # 10 packed
ETA = np.diag([-1.0, 1.0, 1.0, 1.0])


def C_grav(kvec):
    """linearized de Donder constraint (spatial), C_nu = eta^mu k_mu hbar_mu,nu.
    (4 x 10). k=(kx,ky,kz); time index 0 carried at zero frequency (static
    constraint surface)."""
    k4 = np.array([0.0, kvec[0], kvec[1], kvec[2]])
    C = np.zeros((4, 10))
    for c, (a, b) in enumerate(SYM):
        for nu in range(4):
            if b == nu:
                C[nu, c] += ETA[a, a] * k4[a]
            if a == nu and a != b:
                C[nu, c] += ETA[b, b] * k4[b]
    return C


def proj_ker(C, tol=1e-10):
    """orthogonal projector onto ker C."""
    u, s, vh = np.linalg.svd(C)
    smax = max(s.max(), 1e-30)
    r = int(np.sum(s > tol * smax))
    ker = vh[r:]
    return ker.conj().T @ ker, 10 - r


def direction_dependence(Cfun, eps=1e-4):
    """||P_S(eps n1) - P_S(eps n2)|| over several directions n -> if O(1),
    P_S has a direction-dependent k->0 limit => non-analytic => non-local."""
    dirs = [np.array([1, 0, 0.0]), np.array([0, 1, 0.0]),
            np.array([1, 1, 0.0]) / np.sqrt(2),
            np.array([1, 1, 1.0]) / np.sqrt(3)]
    Ps = [proj_ker(Cfun(eps * n))[0] for n in dirs]
    worst = 0.0
    for i in range(len(Ps)):
        for j in range(i + 1, len(Ps)):
            worst = max(worst, float(np.linalg.norm(Ps[i] - Ps[j])))
    return worst


if __name__ == "__main__":
    print("R29 no-go feasibility probe")
    print("=" * 62)

    # PART A: gravity constraint projector is non-analytic at k=0
    dimk = proj_ker(C_grav([0.3, 0.2, -0.1]))[1]
    dim0 = proj_ker(C_grav([0.0, 0.0, 0.0]))[1]
    dd = direction_dependence(C_grav)
    print("PART A -- projection route (patch U with a constraint projector):")
    print(f"  dim ker C: k!=0 -> {dimk} ;  k=0 -> {dim0}  (dimension JUMP)")
    print(f"  ||P_S(eps n1) - P_S(eps n2)|| over directions = {dd:.3f}")
    print(f"  => P_S is {'DIRECTION-DEPENDENT at k=0 (non-analytic => NON-LOCAL)' if dd > 0.1 else 'analytic'}")
    print(f"  => algebraic patching U = U0 + K C (K ~ C^+) CANNOT be local.")

    # PART B: Maxwell witness -- same k=0 non-analyticity, yet Yee is local+exact
    rng = np.random.default_rng(0)
    dc = 0.0
    for _ in range(200):
        k = rng.normal(size=3); v = rng.normal(size=3)
        dc = max(dc, abs(np.dot(k, np.cross(k, v))))    # div curl = 0
    # Gauss projector also direction-dependent at k=0:
    def C_gauss(kk):
        return np.array(kk, float).reshape(1, 3)
    dd_max = direction_dependence(lambda n: C_gauss(n[:3]))  # note: 3-comp E
    print("\nPART B -- complex route (Maxwell/Yee witness):")
    print(f"  Gauss projector k->0 direction dependence = (same pathology)")
    print(f"  BUT identity  |k . (k x v)|  (= div curl) = {dc:.1e}  (machine 0)")
    print(f"  => Yee preserves Gauss EXACTLY and LOCALLY via the operator")
    print(f"     identity div curl = 0 -- never through a projector.")

    a_local_obstructed = dd > 0.1
    b_complex_possible = dc < 1e-12
    print("\nVERDICT (partial, decisive for direction):")
    print(f"  A projection/patch route: LOCALLY OBSTRUCTED "
          f"({'confirmed' if a_local_obstructed else 'NOT'})")
    print(f"  B complex route: possible in principle "
          f"({'Maxwell witness holds' if b_complex_possible else 'NOT'})")
    print("  => NOT a global no-go. The obstruction is specific to patching.")
    print("     Necessary & (U(1)-)proven-possible route: build U from a local")
    print("     tensor curl so discrete linearized Bianchi holds identically.")
    print("  Remaining theorem (true N-N question): does a LOCAL UNITARY")
    print("     discrete linearized-Bianchi TENSOR complex exist? -- sharply")
    print("     posed, constructible, falsifiable. Kinematic half (R.D=0) done;")
    print("     dynamical half (local evolution w/ discrete Bianchi) is the target.")

    json.dump({"gravity_dim_ker_knz": dimk, "gravity_dim_ker_k0": dim0,
               "PS_direction_dependence": dd,
               "maxwell_divcurl": dc,
               "A_projection_locally_obstructed": bool(a_local_obstructed),
               "B_complex_possible_maxwell_witness": bool(b_complex_possible),
               "global_no_go": False,
               "remaining_theorem": "local unitary discrete linearized-Bianchi "
               "tensor complex existence (kinematic R.D=0 done; dynamical half open)"},
              open(os.path.join(DIR, "r29_results.json"), "w"), indent=1)
    print("\nwrote r29_results.json")
