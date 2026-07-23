"""R25-C1: auxiliary mapping-cone Wilson deformation of the walk complex.

Four auxiliary fields extend the physical 10-component tensor field while
the gauge parameter rank remains four.  For a local Wilson scalar r(z),

  G+ = [G; r I],             C+ = [C, -zt r I],
  C+ G+ = -(P_walk+zt r^2) I.

Four further exact syzygies D=[r H, -H G] remove the auxiliary quotient.
The common Wilson shell is P_W=P_walk+zt r^2, corresponding to stiffness
a_W=(2-tr U)+r^2.  No inverse or momentum projector occurs.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

import cp1_v4_L2 as L2
import r25_detour_complex as R25D
import r25_walk_dedonder_complex as R25B1


DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "r25_auxiliary_wilson_results.json")
ALPHA = 0.5
I4 = np.eye(4, dtype=complex)
PAULI_NUM = [np.array(s.tolist(), complex) for s in R25B1.SIGMA]


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def q_spatial(k):
    return sum(math.sin(float(x)/2)**2 for x in k)/3.0


def wilson_r(k):
    # Radius one, O(k^2); r^2 is radius two and O(k^4).  Alpha=1/2 is the
    # largest simple rational point with comfortable full-BZ a_W<4 margin.
    return ALPHA*q_spatial(k)


def walk_data(k):
    U = L2.walk_symbol(np.asarray(k, float))
    tr = float(np.real(np.trace(U)))
    r = wilson_r(k)
    aw = 2-tr+r*r
    return U, tr, r, aw


def auxiliary_selector(U):
    """Cubic-symmetric local selector, deliberately dark on the Newton lift.

    The first three rows relate spatial off-diagonals to h0i using the walk
    Bloch vector; the last is spatial_trace-3h00.  All four annihilate the
    trace-zero transverse Newton representative below.  They have radius one
    and remain independent of C+ at the old UV node.
    """
    a = np.trace(U)/2
    b = np.array([1j*np.trace(s@U)/2 for s in PAULI_NUM])
    H = np.zeros((4, 10), complex)
    # (spatial pair, packed hij, packed h0i, packed h0j)
    for row, (i, j, hij, h0i, h0j) in enumerate(
            ((0, 1, 5, 1, 2), (0, 2, 6, 1, 3), (1, 2, 8, 2, 3))):
        H[row, hij] = 1+a
        H[row, h0i] = 0.75j*b[j]
        H[row, h0j] = 0.75j*b[i]
    H[3, 0] = -3
    H[3, [4, 7, 9]] = 1
    return H


def static_newton_lift(U):
    """Local normal-metric representative in ker C(z_t=1).

    Its trace reverse has zero spatial trace:
      hbar00=(1+a)^2/(2c),
      hbar0i=-(1+a)i b_i/(2c),
      hbarij=[b^2 deltaij-3 b_i b_j]/(4c).
    Hence normal h00=hbar00/2 identically (the frozen canary ratio is exactly
    two), while the IR structure is h00=hii=2.  All entries have radius two.
    """
    a = np.trace(U)/2
    b = np.array([1j*np.trace(s@U)/2 for s in PAULI_NUM])
    hb = np.zeros((4, 4), complex)
    hb[0, 0] = (1+a)**2/(2*L2.C)
    hb[0, 1:] = hb[1:, 0] = -(1+a)*1j*b/(2*L2.C)
    hb[1:, 1:] = (np.eye(3)*(b@b)-3*np.outer(b, b))/(4*L2.C)
    trb = np.sum(R25D.ETA*hb)
    h = hb-0.5*R25D.ETA*trb
    return R25D.pack_matrix(h)


def geometry_root(k, branch):
    _, tr, r, aw = walk_data(k)
    arg = np.clip((tr-r*r)/2, -1.0, 1.0)
    omega = math.acos(arg)
    return np.exp(-1j*branch*omega), omega, aw


def base_kappa(U, z):
    a = np.trace(U)/2
    b = np.array([1j*np.trace(s@U)/2 for s in PAULI_NUM])
    return np.concatenate([[z-a], 1j*b])/L2.C


def augmented_maps_at_z(k, z):
    U, _, r, _ = walk_data(k)
    kap = base_kappa(U, z)
    G = R25D.gauge_matrix(kap)
    C = R25D.dedonder_matrix(kap)
    # kappa was normalized by c, hence C G=-P/c^2.  The auxiliary leg uses
    # the same normalization so C+G+=-P_W/c^2 exactly.
    s = r/L2.C
    Gp = np.vstack([G, s*I4])
    Cp = np.hstack([C, -z*s*I4])
    H = auxiliary_selector(U)
    Dp = np.hstack([s*H, -H@G])
    Kp = np.vstack([Cp, Dp])
    P0 = z*z-np.trace(U)*z+1
    Pw = P0+z*r*r
    return Gp, Kp, Cp, Dp, P0, Pw


def augmented_maps(k, branch):
    z, omega, _ = geometry_root(k, branch)
    return (*augmented_maps_at_z(k, z), omega)


def rank(A, tol=1e-9):
    s = np.linalg.svd(A, compute_uv=False)
    return int(np.sum(s > tol*max(float(s[0]), 1.0))) if s.size else 0


def main():
    # Full 64^3 BZ scalar stability/lift audit.
    N = 64
    amin_nonzero, amax = float("inf"), 0.0
    min_row = max_row = None
    for idx in np.ndindex(N, N, N):
        if idx == (0, 0, 0):
            continue
        k = 2*np.pi*np.array(idx, float)/N
        _, _, r, aw = walk_data(k)
        if aw < amin_nonzero:
            amin_nonzero, min_row = aw, (idx, r)
        if aw > amax:
            amax, max_row = aw, (idx, r)

    # Formal J5 set.
    gate = []
    for nv in ((2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0),
               (2, 2, 2), (1, 1, 1)):
        k = 2*np.pi*np.array(nv, float)/32
        wm = math.acos(np.clip(float(np.real(np.trace(L2.walk_symbol(k)))/2), -1, 1))
        _, wg, _ = geometry_root(k, 1)
        gate.append({"index": list(nv), "omega_matter": wm,
                     "omega_geometry": wg, "relative_J5": abs(wg/wm-1)})

    rng = np.random.default_rng(250728)
    kset = [np.array([0.3, 0, 0]), np.array([0.4, 0.4, 0]),
            np.array([0.4, 0.4, 0.4]),
            np.array([-1.714143896, 0, -1.714143896])]
    kset += [rng.uniform(-math.pi, math.pi, 3) for _ in range(2048)]
    ranks_g, ranks_k, cohom = set(), set(), set()
    worst = {"KG": 0.0, "CG_plus_PwI": 0.0, "Pw": 0.0}
    smallest_s8 = float("inf")
    for branch in (-1, 1):
        for k in kset:
            G, K, C, D, P0, Pw, _ = augmented_maps(k, branch)
            rg, rk = rank(G), rank(K)
            ranks_g.add(rg); ranks_k.add(rk)
            cohom.add(14-rk-rg)
            worst["KG"] = max(worst["KG"], float(np.max(np.abs(K@G))))
            worst["CG_plus_PwI"] = max(
                worst["CG_plus_PwI"], float(np.max(np.abs(C@G+Pw*I4/(L2.C**2)))))
            worst["Pw"] = max(worst["Pw"], float(abs(Pw)))
            sk = np.linalg.svd(K, compute_uv=False)
            smallest_s8 = min(smallest_s8, float(sk[7]))

    # Exact old UV point, evaluated without relying on the approximate k root.
    kuv = np.array([-1.714143895700328, 0.0, -1.714143895700328])
    uv_rows = []
    for branch in (-1, 1):
        G, K, _, _, _, Pw, omega = augmented_maps(kuv, branch)
        uv_rows.append({"branch": branch, "omega_geometry": omega,
                        "r": wilson_r(kuv), "Pw_abs": abs(Pw),
                        "rank_G": rank(G), "rank_K": rank(K),
                        "cohomology": 14-rank(K)-rank(G)})

    # Static sourced-sector certificate: a local Newton representative with
    # zero auxiliary field lies exactly in the full eight-row constraint
    # kernel at z_t=1.  Its source lift a_W*h_N is also finite-local.
    static_worst = {"K_newton": 0.0, "C_newton": 0.0,
                    "H_newton": 0.0}
    static_rows = []
    for k in kset:
        U, _, r, aw = walk_data(k)
        kap = base_kappa(U, 1.0)
        G0 = R25D.gauge_matrix(kap)
        C0 = R25D.dedonder_matrix(kap)
        s = r/L2.C
        H0 = auxiliary_selector(U)
        K0 = np.vstack([np.hstack([C0, -s*I4]),
                        np.hstack([s*H0, -H0@G0])])
        hn = static_newton_lift(U)
        xn = np.concatenate([hn, np.zeros(4)])
        static_worst["K_newton"] = max(static_worst["K_newton"],
                                        float(np.max(np.abs(K0@xn))))
        static_worst["C_newton"] = max(static_worst["C_newton"],
                                        float(np.max(np.abs(C0@hn))))
        static_worst["H_newton"] = max(static_worst["H_newton"],
                                        float(np.max(np.abs(H0@hn))))
    for nv in ((1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 2, 2)):
        k = 2*np.pi*np.array(nv, float)/32
        U, _, _, aw = walk_data(k)
        hn = static_newton_lift(U)
        static_rows.append({"index": list(nv), "a_W": aw,
                            "h00_numerator": float(np.real(hn[0])),
                            "hii_numerator": [float(np.real(hn[j])) for j in (4, 7, 9)],
                            "h00_over_hii": float(np.real(hn[0]/hn[4]))})

    checks = {
        "full_BZ_pair_stability_0_lt_a_lt_4": amin_nonzero > 0 and amax < 4,
        "formal_J5_lt_1e-2": max(x["relative_J5"] for x in gate) < 1e-2,
        "augmented_gauge_rank_four": ranks_g == {4},
        "augmented_constraint_rank_eight": ranks_k == {8},
        "on_shell_quotient_dimension_two": cohom == {2},
        "mapping_cone_identities_lt_1e-11": max(worst.values()) < 1e-11,
        "old_UV_node_lifted_with_two_cohomology": all(x["cohomology"] == 2 for x in uv_rows),
        "static_Newton_lift_exactly_constraint_dark": max(static_worst.values()) < 1e-11,
    }
    result = {
        "register": "R25-C1-auxiliary-Wilson",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_sha256": sha256(__file__),
        "construction": {
            "r": "(1/2) q, q=(1/3) sum_i sin^2(k_i/2)",
            "r_local_radius": 1,
            "wilson_stiffness": "a_W=2-tr(U_walk)+r^2",
            "wilson_local_radius": 2,
            "G_plus": "vertical_stack(G_walk, r I_4)",
            "C_plus": "horizontal_stack(C_walk, -z_t r I_4)",
            "D_plus": "horizontal_stack(r H, -H G_walk)",
            "H": "cubic-symmetric radius-one selector dark on the trace-zero Newton lift",
            "physical_gauge_rank": 4,
            "field_count_with_auxiliary": 14,
        },
        "full_BZ": {
            "N": N, "min_nonzero_a_W": amin_nonzero,
            "min_row": {"index": list(min_row[0]), "r": min_row[1]},
            "max_a_W": amax,
            "max_row": {"index": list(max_row[0]), "r": max_row[1]},
        },
        "formal_gate": gate,
        "on_shell_census": {
            "points_per_branch": len(kset), "rank_G_plus": sorted(ranks_g),
            "rank_K_plus": sorted(ranks_k), "quotient_dim": sorted(cohom),
            "worst_identity_residuals": worst,
            "smallest_eighth_singular_value_K": smallest_s8,
        },
        "old_UV_node": uv_rows,
        "static_Newton": {
            "normal_h_lift": "trace reverse: hbar00=(1+a)^2/(2c), hbar0i=-(1+a)i b_i/(2c), hbarij=(b^2 deltaij-3b_i b_j)/(4c); auxiliary=0",
            "source_lift": "drive h with h_N(z)*rho; equilibrium is h_N rho/a_W",
            "locality": "h_N radius 1; no division except the physical 1/a_W Green response",
            "worst": static_worst,
            "IR_normal_h_at_k0": [float(np.real(x)) for x in
                                    static_newton_lift(L2.walk_symbol(np.zeros(3)))],
            "gate_rows": static_rows,
        },
        "scope_boundary": "Constraint/gauge mapping cone passed. A local augmented Einstein/evolution operator and real-space damping/source realization remain to be constructed.",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print("R25-C1 auxiliary Wilson mapping-cone complex")
    print("status:", result["status"])
    print("full BZ a_W min/max:", amin_nonzero, amax)
    print("max formal J5:", max(x["relative_J5"] for x in gate))
    print("ranks G/K, quotient:", sorted(ranks_g), sorted(ranks_k), sorted(cohom))
    print("worst identity residual:", max(worst.values()))
    print("old UV rows:", uv_rows)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
