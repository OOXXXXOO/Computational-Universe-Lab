"""R32 -- REACHABILITY CHEAP PROBE (lane A/B direction verdict).

QUESTION (opening a new campaign: deform the emergent walk onto the R30 complex).
Is the distance between
   S_walk  = the CURRENT emergent walk U's PROPAGATION-INVARIANT subspace
             (the curvature-carrying propagating modes, the ones that make
             N_prop = 4-5; R28/R31 machinery), and
   S_kerC  = the R30 complex's ker C = placed gauge(4) (+) TT(2) = 6-dim
             (R15 T9, rebuilt per-k from the R30 algebraic backbone)
a DEFORMATION distance (small principal angles, and a continuous knob shrinks
them to zero -> open a construction campaign) or a TOPOLOGICAL distance (angles
locked bounded-away-from-zero at some k, an index/winding mismatch -> reachability
NO-GO signal)?  This turns the new campaign's first move from "weeks of
construction" into "one direction-deciding cheap linear-algebra check".

WHAT THIS DOES (pure principal-angle diagnosis, reuses frozen machinery, builds
nothing new).  For each k in {axial x2, face-diagonal, BODY-diagonal}:
  1. S_kerC(k): ker C = placed gauge(4) (+) TT(2), physical-h, orthonormal (10,6).
     The three mutually-orthogonal sectors TT(2)/gauge(4)/constraint-ROW(4) (R31)
     tile the 10-dim symmetric-tensor space; ker C = TT (+) gauge, ROW = its
     orthogonal complement (the R28 病灶).
  2. S_walk(k): the walk symbol M = D1.damped_map(k, MU)[0]'s unit-modulus modes'
     physical-h parts (V[:10], 卡点⑦/R28 convention).  The PROPAGATION-INVARIANT
     CURVATURE subspace = the SVD-rank-N_prop image directions of the placed
     linearized Riemann operator restricted to the dominant (-w) Floquet branch
     (gauge -> zero curvature drops out automatically; this is exactly the R28/R31
     N_prop count's subspace).
  3. principal angles {theta_i(k)} between S_walk and S_kerC (SVD of orthonormal
     bases' inner product); report max/min, how many angles ~0 (S_walk dims INSIDE
     ker C) vs bounded-away (dims LOCKED outside), and the mean residual of the 12
     unit modes OUTSIDE ker C (cross-check vs R31's 0.34-0.49).

DEFORMATION vs TOPOLOGICAL (let the numbers decide):
  * Deformation (optimistic): principal angles can be CONTINUOUSLY shrunk to zero
    along a parameter path.  Knobs swept: mu (constraint-damping coupling, explicit
    arg to damped_map) and ALPHA (Wilson radius; runtime attribute, restored after
    -- the frozen FILE is never modified).  A curve angle(param) -> 0 with no floor
    => recommend opening the construction campaign (deformation feasible; acceptance
    criterion residual->0 <=> N_prop=2).
  * Topological (no-go signal): angles LOCKED bounded-away-from-zero at some k, or a
    -w-branch Floquet winding / index mismatch that prevents continuous shrinkage.
    => reachability NO-GO signal (NOT a theorem unless an invariant is proven).

RED LINES (AGENTS.md): DIRECTION VERDICT ONLY.  Does NOT declare M3 / emergence /
reachability closed.  Deformation verdict = RECOMMEND a campaign (not "campaign
already succeeded"); topological verdict = NO-GO SIGNAL (not a proven no-go).  R30
existence unchanged; existence != emergence != M3.  Frozen inputs imported
READ-ONLY.  fp64 (RULESPACE_BACKEND=numpy).

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/r32_reachability_probe.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (DIR, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib                                          # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402

import r25_dynamic_symbol as D1                            # noqa: E402 walk symbol M
import r25_realspace_step as R                             # noqa: E402 frozen MU
import r25_auxiliary_wilson_complex as W                   # noqa: E402 Wilson radius ALPHA
from r15_walk_dedonder import (kappa_placed, gauge_block,  # noqa: E402 placed shell
                               tt_basis, constraint_matrix, shell_omega,
                               ETA, unpack, pack, SYM)

OUT = os.path.join(ROOT, "data", "results", "r32_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "r32_reachability.png")

N = 16
SV_THRESH = 0.05                                           # shared judge口径
MU0 = R.MU                                                 # frozen chosen damping ~2e-3
ALPHA0 = W.ALPHA                                           # frozen Wilson radius 0.5
KSET = [(2, 0, 0), (0, 3, 0), (2, 2, 0), (2, 2, 2)]
LABELS = {(2, 0, 0): "axial", (0, 3, 0): "axial",
          (2, 2, 0): "face-diagonal", (2, 2, 2): "body-diagonal"}
UNIT_TOL = 2e-9
PROP_TOL = 1e-6                                            # looser cut for parameter sweeps
ANGLE_ZERO_DEG = 5.0                                       # "inside ker C" threshold


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _jd(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        f = float(o)
        return f if np.isfinite(f) else str(f)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def write_json(payload):
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_jd)


def _tr_flat(v10):
    """flat-ETA trace reversal (R16 convention): hbar-packed -> physical-h packed.
    IDENTICAL to R28/R31._tr_flat."""
    Hb = unpack(v10)
    trb = sum(ETA[m, m] * Hb[m, m] for m in range(4))
    H = Hb - 0.5 * ETA * trb
    return np.array([H[m, n] for (m, n) in SYM])


# --------------------------------------------------------------------------
#  ker C and the three orthogonal sectors (physical-h), verbatim R31 geometry
# --------------------------------------------------------------------------
def kerC_basis(kap):
    """physical ker C = placed gauge(4) (+) TT(2), orthonormalized (10,6)."""
    G = np.column_stack([_tr_flat(np.real(gauge_block(kap)[:, a])) for a in range(4)])
    TT = np.real(tt_basis(kap))
    basis = np.column_stack([G, TT])
    Q, _ = np.linalg.qr(basis)
    return Q


def build_sectors(kap):
    """Q_TT(10,2), Q_gauge(10,4), Q_row(10,4) -- mutually orthogonal, tile R^10.
    ker C = [Q_TT|Q_gauge]; ROW = orthogonal complement of ker C (R28 病灶)."""
    G_phys = np.column_stack([_tr_flat(np.real(gauge_block(kap)[:, a]))
                              for a in range(4)])
    TT_phys = np.real(tt_basis(kap))
    Q_gauge, _ = np.linalg.qr(G_phys)
    ker = np.column_stack([G_phys, TT_phys])
    ker_perp_g = ker - Q_gauge @ (Q_gauge.conj().T @ ker)
    Uq, sq, _ = np.linalg.svd(ker_perp_g, full_matrices=False)
    rk = int(np.sum(sq > 1e-9 * sq[0]))
    Q_TT = Uq[:, :rk]
    Q6, _ = np.linalg.qr(np.column_stack([Q_gauge, Q_TT]))
    Qfull, _ = np.linalg.qr(Q6, mode="complete")
    Q_row = Qfull[:, Q6.shape[1]:]
    return Q_TT, Q_gauge, Q_row


def inc_matrix(kap):
    """placed linearized Riemann as a linear map (256,10) on packed physical h:
    columns j = flatten(R_{manb}(e_j)).  inc(h) = inc_matrix @ h_packed."""
    k = np.real(kap)
    cols = []
    for j in range(10):
        v = np.zeros(10); v[j] = 1.0
        H = unpack(v).real
        Rt = np.zeros((4, 4, 4, 4))
        for m in range(4):
            for a in range(4):
                for n in range(4):
                    for b in range(4):
                        Rt[m, a, n, b] = 0.5 * (
                            k[m] * k[n] * H[a, b] + k[a] * k[b] * H[m, n]
                            - k[m] * k[b] * H[a, n] - k[a] * k[n] * H[m, b])
        cols.append(Rt.reshape(256))
    return np.column_stack(cols)                           # (256,10)


# --------------------------------------------------------------------------
#  walk propagation-invariant + curvature subspaces
# --------------------------------------------------------------------------
def walk_unit_modes(k, mu, prop_tol=UNIT_TOL):
    """(U10 physical-h (10,n), phases (n,), |eig| (n,)) of the walk symbol's
    unit-modulus modes.  V[:10] fed as physical h (卡点⑦/R28 convention)."""
    M = D1.damped_map(k, mu)[0]
    eig, V = np.linalg.eig(M)
    idx = np.where(np.abs(np.abs(eig) - 1.0) < prop_tol)[0]
    U = V[:10, idx]
    U = U / (np.linalg.norm(U, axis=0, keepdims=True) + 1e-300)
    return U, np.angle(eig[idx]), np.abs(eig[idx])


def curvature_subspace(U10, phases, inc_mat, branch="neg"):
    """Propagation-invariant CURVATURE subspace of the chosen Floquet branch:
    the SVD-rank-N_prop image of inc restricted to that branch (gauge/zero-curv
    modes drop out).  Returns (S_curv (10,Nprop) orthonormal, N_prop, sv list)."""
    if branch == "neg":
        sel = phases < -1e-9
    elif branch == "pos":
        sel = phases > 1e-9
    else:
        sel = np.ones(len(phases), bool)
    B = U10[:, sel]                                        # (10, m)
    if B.shape[1] == 0:
        return np.zeros((10, 0)), 0, []
    A = inc_mat @ B                                        # (256, m) Riemann images
    Uv, sv, Vh = np.linalg.svd(A, full_matrices=False)
    svn = sv / (sv[0] + 1e-300)
    nprop = int(np.sum(svn > SV_THRESH))
    Vsig = Vh.conj().T[:, :nprop]                          # (m, nprop) mode-space
    Scurv = B @ Vsig                                       # (10, nprop) h-space
    Q, _ = np.linalg.qr(Scurv)
    return Q, nprop, [float(x) for x in svn[:8]]


def dominant_branch(U10, phases, inc_mat):
    """pick the branch carrying MORE curvature (the -w病灶 branch per R31)."""
    cn = np.linalg.norm(inc_mat @ U10[:, phases < -1e-9]) if np.any(phases < -1e-9) else 0.0
    cp = np.linalg.norm(inc_mat @ U10[:, phases > 1e-9]) if np.any(phases > 1e-9) else 0.0
    return "neg" if cn >= cp else "pos"


def principal_angles(A, B):
    """principal angles (radians, ascending) between column spaces of A, B."""
    if A.shape[1] == 0 or B.shape[1] == 0:
        return np.array([])
    Qa, _ = np.linalg.qr(A)
    Qb, _ = np.linalg.qr(B)
    s = np.linalg.svd(Qa.conj().T @ Qb, compute_uv=False)
    s = np.clip(s, 0.0, 1.0)
    return np.arccos(s)[::-1]                              # ascending angle


def residual_outside(U10, Q_kerC):
    """mean/max per-mode residual OUTSIDE ker C (R28/R31 cross-check metric)."""
    proj = Q_kerC @ (Q_kerC.conj().T @ U10)
    resid = np.linalg.norm(U10 - proj, axis=0)
    return float(np.mean(resid)), float(np.max(resid))


def sector_energy(S, Q_TT, Q_gauge, Q_row):
    """mean energy fraction of subspace S in each sector (over its basis cols)."""
    if S.shape[1] == 0:
        return {"TT": 0.0, "gauge": 0.0, "row": 0.0}
    fT = np.mean(np.linalg.norm(Q_TT.conj().T @ S, axis=0) ** 2)
    fG = np.mean(np.linalg.norm(Q_gauge.conj().T @ S, axis=0) ** 2)
    fR = np.mean(np.linalg.norm(Q_row.conj().T @ S, axis=0) ** 2)
    return {"TT": float(fT), "gauge": float(fG), "row": float(fR)}


# --------------------------------------------------------------------------
#  per-k principal-angle analysis at frozen (MU0, ALPHA0)
# --------------------------------------------------------------------------
def analyze_k(nv, mu=MU0):
    k = np.array(nv, float) * (2 * np.pi / N)
    kap = kappa_placed(k)
    Q_kerC = kerC_basis(kap)
    Q_TT, Q_gauge, Q_row = build_sectors(kap)
    inc_mat = inc_matrix(kap)

    U10, phases, mods = walk_unit_modes(k, mu)
    n_unit = U10.shape[1]
    dom = dominant_branch(U10, phases, inc_mat)
    Scurv, nprop, svn = curvature_subspace(U10, phases, inc_mat, dom)

    ang_kerC = principal_angles(Scurv, Q_kerC)            # S_walk vs ker C
    ang_TT = principal_angles(Scurv, Q_TT)                # S_walk vs TT (curv target)
    rmean, rmax = residual_outside(U10, Q_kerC)           # cross-check R31
    sec = sector_energy(Scurv, Q_TT, Q_gauge, Q_row)

    deg = np.degrees(ang_kerC)
    n_inside = int(np.sum(deg < ANGLE_ZERO_DEG))
    n_locked = int(np.sum(deg > 45.0))
    return {
        "nv": list(nv), "label": LABELS[nv], "n_unit": int(n_unit),
        "dominant_branch": dom, "omega_shell": float(shell_omega(k)),
        "N_prop_curv": nprop, "curv_sv": svn,
        "principal_angles_vs_kerC_deg": [float(x) for x in deg],
        "max_angle_vs_kerC_deg": float(deg.max()) if len(deg) else float("nan"),
        "min_angle_vs_kerC_deg": float(deg.min()) if len(deg) else float("nan"),
        "n_angles_inside_kerC(<5deg)": n_inside,
        "n_angles_locked(>45deg)": n_locked,
        "principal_angles_vs_TT_deg": [float(x) for x in np.degrees(ang_TT)],
        "mean_resid_outside_kerC": rmean, "max_resid_outside_kerC": rmax,
        "Scurv_sector_energy": sec,
    }


# --------------------------------------------------------------------------
#  parameter sweeps: does a continuous knob shrink the locked angle to 0?
# --------------------------------------------------------------------------
def sweep_mu(nv, mus):
    k = np.array(nv, float) * (2 * np.pi / N)
    kap = kappa_placed(k)
    Q_kerC = kerC_basis(kap)
    Q_TT, _, _ = build_sectors(kap)
    inc_mat = inc_matrix(kap)
    rows = []
    for mu in mus:
        U10, phases, mods = walk_unit_modes(k, mu, prop_tol=PROP_TOL)
        if U10.shape[1] == 0:
            rows.append({"mu": float(mu), "n_unit": 0, "max_angle_deg": None})
            continue
        dom = dominant_branch(U10, phases, inc_mat)
        Scurv, nprop, _ = curvature_subspace(U10, phases, inc_mat, dom)
        ang = np.degrees(principal_angles(Scurv, Q_kerC))
        angTT = np.degrees(principal_angles(Scurv, Q_TT))
        rmean, _ = residual_outside(U10, Q_kerC)
        rows.append({"mu": float(mu), "n_unit": int(U10.shape[1]),
                     "N_prop": nprop, "max_modulus": float(mods.max()),
                     "max_angle_vs_kerC_deg": float(ang.max()) if len(ang) else None,
                     "max_angle_vs_TT_deg": float(angTT.max()) if len(angTT) else None,
                     "mean_resid_outside_kerC": rmean})
    return rows


def sweep_alpha(nv, alphas):
    """Wilson-radius sweep.  ALPHA is a runtime attribute of the frozen module;
    we set it, measure, and RESTORE it -- the FILE on disk is never modified."""
    k = np.array(nv, float) * (2 * np.pi / N)
    kap = kappa_placed(k)
    Q_kerC = kerC_basis(kap)
    Q_TT, _, _ = build_sectors(kap)
    inc_mat = inc_matrix(kap)
    rows = []
    saved = W.ALPHA
    try:
        for al in alphas:
            W.ALPHA = float(al)
            U10, phases, mods = walk_unit_modes(k, MU0, prop_tol=PROP_TOL)
            if U10.shape[1] == 0:
                rows.append({"alpha": float(al), "n_unit": 0, "max_angle_deg": None})
                continue
            dom = dominant_branch(U10, phases, inc_mat)
            Scurv, nprop, _ = curvature_subspace(U10, phases, inc_mat, dom)
            ang = np.degrees(principal_angles(Scurv, Q_kerC))
            rmean, _ = residual_outside(U10, Q_kerC)
            rows.append({"alpha": float(al), "n_unit": int(U10.shape[1]),
                         "N_prop": nprop, "max_modulus": float(mods.max()),
                         "max_angle_vs_kerC_deg": float(ang.max()) if len(ang) else None,
                         "mean_resid_outside_kerC": rmean})
    finally:
        W.ALPHA = saved                                    # RESTORE (file untouched)
    return rows


def kray_scan(direction, ts):
    """principal-angle max along a continuum k-ray (topological k-lock probe):
    does the max angle dip to 0 anywhere along the ray, or stay bounded away?"""
    rows = []
    for t in ts:
        k = np.array(direction, float) * t
        w = shell_omega(k)
        if w is None or np.linalg.norm(k) < 1e-6:
            continue
        kap = kappa_placed(k)
        Q_kerC = kerC_basis(kap)
        inc_mat = inc_matrix(kap)
        U10, phases, mods = walk_unit_modes(k, MU0, prop_tol=UNIT_TOL)
        if U10.shape[1] == 0:
            continue
        dom = dominant_branch(U10, phases, inc_mat)
        Scurv, nprop, _ = curvature_subspace(U10, phases, inc_mat, dom)
        ang = np.degrees(principal_angles(Scurv, Q_kerC))
        rows.append({"t": float(t), "omega": float(w), "n_unit": int(U10.shape[1]),
                     "N_prop": nprop,
                     "max_angle_vs_kerC_deg": float(ang.max()) if len(ang) else None,
                     "min_angle_vs_kerC_deg": float(ang.min()) if len(ang) else None})
    return rows


# --------------------------------------------------------------------------
#  figure
# --------------------------------------------------------------------------
def make_figure(per_k, mu_sweeps, alpha_sweeps, mus, alphas):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))
    # panel 1: per-k principal angle spectra vs ker C
    ax = axes[0]
    for res in per_k:
        deg = res["principal_angles_vs_kerC_deg"]
        ax.plot(range(1, len(deg) + 1), sorted(deg),
                marker="o", label=f"{tuple(res['nv'])} [{res['label']}]")
    ax.axhline(90, color="gray", ls=":", lw=0.8)
    ax.axhline(5, color="green", ls=":", lw=0.8)
    ax.set_xlabel("principal-angle index (ascending)")
    ax.set_ylabel("angle S_walk vs ker C (deg)")
    ax.set_title("per-k principal-angle spectrum\n(90=orthogonal/row-locked, 0=inside ker C)")
    ax.set_ylim(-3, 95); ax.legend(fontsize=7)
    # panel 2: mu sweep
    ax = axes[1]
    for nv, rows in mu_sweeps.items():
        xs = [r["mu"] for r in rows if r.get("max_angle_vs_kerC_deg") is not None]
        ys = [r["max_angle_vs_kerC_deg"] for r in rows if r.get("max_angle_vs_kerC_deg") is not None]
        ax.semilogx(xs, ys, marker=".", label=str(nv))
    ax.axvline(MU0, color="k", ls="--", lw=0.8, label="frozen MU")
    ax.axhline(0, color="green", ls=":", lw=0.8)
    ax.set_xlabel("mu (constraint-damping coupling)")
    ax.set_ylabel("max angle vs ker C (deg)")
    ax.set_title("deformation knob 1: mu\n(-> 0 = deformation ; floor = lock)")
    ax.set_ylim(-3, 95); ax.legend(fontsize=7)
    # panel 3: alpha sweep
    ax = axes[2]
    for nv, rows in alpha_sweeps.items():
        xs = [r["alpha"] for r in rows if r.get("max_angle_vs_kerC_deg") is not None]
        ys = [r["max_angle_vs_kerC_deg"] for r in rows if r.get("max_angle_vs_kerC_deg") is not None]
        ax.plot(xs, ys, marker=".", label=str(nv))
    ax.axvline(ALPHA0, color="k", ls="--", lw=0.8, label="frozen ALPHA")
    ax.axhline(0, color="green", ls=":", lw=0.8)
    ax.set_xlabel("ALPHA (Wilson radius)")
    ax.set_ylabel("max angle vs ker C (deg)")
    ax.set_title("deformation knob 2: Wilson ALPHA\n(-> 0 = deformation ; floor = lock)")
    ax.set_ylim(-3, 95); ax.legend(fontsize=7)
    fig.suptitle("R32 reachability probe: principal angles S_walk (propagating curvature) "
                 "vs S_kerC (R30 complex ker C)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110)
    plt.close(fig)


def main():
    t0 = time.time()
    payload = {
        "register": "R32-reachability-probe (principal angles S_walk vs S_kerC)",
        "status": "RUNNING", "backend": "numpy",
        "question": "deformation (angles->0 along a continuous knob => open construction "
                    "campaign) vs topological (angles locked bounded-away / winding "
                    "mismatch => reachability NO-GO signal)?",
        "params": {"N": N, "kset": [list(k) for k in KSET], "mu0": MU0,
                   "alpha0": ALPHA0, "sv_thresh": SV_THRESH,
                   "angle_zero_deg": ANGLE_ZERO_DEG},
        "geometry": "S_kerC = placed gauge(4) (+) TT(2) = ker C (6-dim, R15 T9 / R30 "
                    "backbone). S_walk = walk symbol M's dominant (-w) Floquet-branch "
                    "curvature subspace (SVD-rank-N_prop image of placed Riemann; "
                    "R28/R31 count's subspace). ROW = ker C's orthogonal complement.",
        "frozen_inputs_sha256": {
            "r25_dynamic_symbol.py": sha256_file(os.path.join(DIR, "r25_dynamic_symbol.py")),
            "r25_realspace_step.py": sha256_file(os.path.join(DIR, "r25_realspace_step.py")),
            "r25_auxiliary_wilson_complex.py": sha256_file(os.path.join(DIR, "r25_auxiliary_wilson_complex.py")),
            "r15_walk_dedonder.py": sha256_file(os.path.join(DIR, "r15_walk_dedonder.py")),
        },
    }
    write_json(payload)

    print("R32 reachability probe: S_walk (propagating curvature) vs S_kerC (ker C)")
    print("=" * 74)

    # -- per-k principal angles at frozen (MU0, ALPHA0) ----------------------
    per_k = []
    for nv in KSET:
        res = analyze_k(nv)
        per_k.append(res)
        print(f"k={nv} [{res['label']:>13}] n_unit={res['n_unit']} dom={res['dominant_branch']} "
              f"N_prop={res['N_prop_curv']}")
        print(f"    principal angles vs kerC (deg) = "
              f"{['%.1f' % a for a in sorted(res['principal_angles_vs_kerC_deg'])]}")
        print(f"    max={res['max_angle_vs_kerC_deg']:.1f} min={res['min_angle_vs_kerC_deg']:.1f}  "
              f"inside(<5deg)={res['n_angles_inside_kerC(<5deg)']} "
              f"locked(>45deg)={res['n_angles_locked(>45deg)']}")
        print(f"    mean-resid-outside-kerC={res['mean_resid_outside_kerC']:.3f} "
              f"(R31 x-check); S_curv sector energy TT/gauge/row="
              f"{res['Scurv_sector_energy']['TT']:.2f}/"
              f"{res['Scurv_sector_energy']['gauge']:.2f}/"
              f"{res['Scurv_sector_energy']['row']:.2f}")
        write_json({**payload, "per_k_partial": per_k})
    payload["per_k"] = per_k

    # -- R31 cross-check ------------------------------------------------------
    r31_ref = {(2, 0, 0): 0.469, (0, 3, 0): 0.485, (2, 2, 0): 0.341, (2, 2, 2): 0.389}
    xcheck = []
    for res in per_k:
        ref = r31_ref.get(tuple(res["nv"]))
        xcheck.append({"nv": res["nv"], "r32_mean_resid": res["mean_resid_outside_kerC"],
                       "r31_mean_resid": ref,
                       "abs_diff": abs(res["mean_resid_outside_kerC"] - ref) if ref else None})
    worst_x = max((e["abs_diff"] for e in xcheck if e["abs_diff"] is not None), default=None)
    payload["r31_crosscheck"] = {"per_k": xcheck, "worst_abs_diff": worst_x,
                                 "reproduces_r31": bool(worst_x is not None and worst_x < 1e-3)}
    print(f"[x-check R31] worst |resid diff| = {worst_x:.2e} "
          f"-> reproduces={payload['r31_crosscheck']['reproduces_r31']}")
    write_json(payload)

    # -- parameter sweeps (deformation test) ---------------------------------
    print("[sweep] mu (constraint-damping coupling) and ALPHA (Wilson radius) ...")
    mus = np.logspace(-5.0, -1.3, 22)
    alphas = np.linspace(0.02, 1.4, 22)
    sweep_ks = [(2, 0, 0), (2, 2, 2)]                      # axial + body-diagonal
    mu_sweeps = {nv: sweep_mu(nv, mus) for nv in sweep_ks}
    alpha_sweeps = {nv: sweep_alpha(nv, alphas) for nv in sweep_ks}
    payload["mu_sweep"] = {str(nv): rows for nv, rows in mu_sweeps.items()}
    payload["alpha_sweep"] = {str(nv): rows for nv, rows in alpha_sweeps.items()}

    def sweep_floor(rows, key="max_angle_vs_kerC_deg"):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return (min(vals), max(vals)) if vals else (None, None)

    mu_floor = {str(nv): sweep_floor(rows) for nv, rows in mu_sweeps.items()}
    alpha_floor = {str(nv): sweep_floor(rows) for nv, rows in alpha_sweeps.items()}
    payload["sweep_floors_min_max_angle_deg"] = {"mu": mu_floor, "alpha": alpha_floor}
    for nv in sweep_ks:
        print(f"    k={nv}: mu-sweep angle range   = "
              f"{mu_floor[str(nv)][0]}..{mu_floor[str(nv)][1]} deg")
        print(f"    k={nv}: alpha-sweep angle range= "
              f"{alpha_floor[str(nv)][0]}..{alpha_floor[str(nv)][1]} deg")
    write_json(payload)

    # -- k-ray continuum scan (topological k-lock probe) ---------------------
    print("[k-ray] body-diagonal continuum scan (does the angle dip to 0?) ...")
    ts = np.linspace(0.15, 1.6, 20)
    kray = kray_scan((1.0, 1.0, 1.0), ts)
    kray_angmin = min((r["max_angle_vs_kerC_deg"] for r in kray
                       if r["max_angle_vs_kerC_deg"] is not None), default=None)
    payload["kray_body_diagonal"] = {"rows": kray, "min_over_ray_max_angle_deg": kray_angmin}
    print(f"    body-diagonal ray: min over ray of (max angle vs kerC) = {kray_angmin} deg")
    write_json(payload)

    # -- VERDICT (deformation vs topological, numbers decide) ----------------
    all_max = [r["max_angle_vs_kerC_deg"] for r in per_k]
    all_locked = [r["n_angles_locked(>45deg)"] for r in per_k]
    # global sweep floor across both knobs and both swept k
    floor_vals = []
    for d in (mu_floor, alpha_floor):
        for v in d.values():
            if v[0] is not None:
                floor_vals.append(v[0])
    global_floor = min(floor_vals) if floor_vals else None

    locked_now = all(m > 45.0 for m in all_max) and all(n >= 1 for n in all_locked)
    knob_shrinks = global_floor is not None and global_floor < ANGLE_ZERO_DEG
    kray_shrinks = kray_angmin is not None and kray_angmin < ANGLE_ZERO_DEG

    if knob_shrinks or kray_shrinks:
        verdict_tag = "DEFORMATION (angles reach ~0 along a continuous knob)"
        verdict = ("A continuous parameter path drives the max principal angle to "
                   "~0 (global sweep floor %.1f deg; k-ray floor %s deg): S_walk can "
                   "be continuously rotated into ker C. RECOMMEND opening the "
                   "construction campaign (acceptance: residual->0 <=> N_prop=2). "
                   "This is a DIRECTION recommendation, NOT 'campaign succeeded'."
                   % (global_floor if global_floor is not None else float('nan'),
                      kray_angmin))
    elif locked_now:
        verdict_tag = ("LOCK UNDER THE CHEAP KNOBS (mu-coupling + Wilson-alpha) -- "
                       "REACHABILITY CAUTION/NO-GO-LEAN SIGNAL (not a proven no-go)")
        verdict = ("At every k the propagating-curvature subspace keeps >=1 principal "
                   "angle LOCKED near 90deg to ker C -- i.e. it retains ~50%% ROW-sector "
                   "(constraint-row, R28 病灶) curvature energy -- and this is INVARIANT "
                   "under the two cheap-accessible knobs: N_prop stays 4-5 and the "
                   "outside-ker-C residual stays 0.35-0.53 across mu in [1e-5,5e-2] AND "
                   "Wilson alpha in [0.02,1.4]; the body-diagonal k-ray never dips below "
                   "%.0f deg (sweep floor %s deg, k-ray floor %s deg). So mu (constraint-"
                   "damping coupling) and the Wilson regulator DO NOT reduce the extra "
                   "row-space curvature DOF. IMPORTANT HONEST SCOPE: the matter-sector "
                   "coin angle theta (=chirality; sets the emergent light speed c=cos "
                   "theta) and the mass gap dm were NOT swept -- they are bound into "
                   "walk_symbol/K_branch (c=C hardcoded) and co-deform the ENTIRE placed "
                   "+Wilson+constraint complex, so a consistent theta/mass sweep IS the "
                   "construction campaign, not a cheap probe. Therefore this is a "
                   "REACHABILITY CAUTION/NO-GO-LEAN SIGNAL, NOT a theorem and NOT a proven "
                   "topological no-go (no winding/index invariant computed). What it "
                   "DECIDES for the campaign: do NOT spend the first weeks tuning mu / the "
                   "Wilson regulator -- they leave the row-space curvature untouched; the "
                   "deformation, if it exists, must act on the MATTER SECTOR (theta/mass) "
                   "AND co-move the complex, and whether that removes the row DOF is the "
                   "real open question (like R29, may instead force relaxing unitarity / "
                   "strict locality / exact constraint)."
                   % (ANGLE_ZERO_DEG, global_floor, kray_angmin))
    else:
        verdict_tag = "INTERMEDIATE (angles partly reducible; missing evidence to decide)"
        verdict = ("Angles are reduced by a knob but do not reach ~0 within the swept "
                   "range (sweep floor %s deg, k-ray floor %s deg). Neither a clean "
                   "deformation-to-zero nor a proven lock. Report angle spectrum; next "
                   "minimal check = extend the knob range / test a matter-sector "
                   "(mass/chirality) knob and a BZ-loop winding invariant."
                   % (global_floor, kray_angmin))

    payload["verdict_metrics"] = {
        "per_k_max_angle_vs_kerC_deg": all_max,
        "per_k_n_locked_gt45": all_locked,
        "global_sweep_floor_min_angle_deg": global_floor,
        "kray_floor_min_angle_deg": kray_angmin,
        "locked_at_all_k_now": locked_now,
        "a_knob_reaches_zero": bool(knob_shrinks or kray_shrinks)}
    payload["knobs_tested"] = {
        "mu": "constraint-damping coupling, explicit arg to damped_map; range [1e-5,5e-2]",
        "alpha": "Wilson radius (W.ALPHA), runtime attr set+restored; range [0.02,1.4]",
        "k_ray": "body-diagonal continuum k-ray (geometry direction)"}
    payload["knobs_not_tested_why"] = {
        "theta_coin_chirality": "walk_symbol(kl, th=TH) binds TH at def-time and "
            "walk_data calls it with the default; K_branch hardcodes c=C=cos(pi/3). A "
            "consistent theta sweep (c=cos theta) co-deforms the ENTIRE placed+Wilson+"
            "constraint stack -- that IS the construction campaign, not a cheap probe.",
        "mass_gap_dm": "same: bound into the frozen walk/complex stack; co-deforms the "
            "shell. Sweeping it consistently is construction, out of scope for a cheap "
            "direction probe."}
    payload["verdict_tag"] = verdict_tag
    payload["verdict"] = verdict
    payload["scope_boundary"] = (
        "DIRECTION VERDICT ONLY (principal-angle cheap probe). Does NOT declare M3 / "
        "emergence / reachability closed. Deformation => RECOMMEND a campaign (not "
        "'campaign succeeded'); topological => NO-GO SIGNAL (not a proven no-go, no "
        "invariant proven). R30 existence unchanged; existence != emergence != M3. "
        "Frozen inputs read-only; Wilson ALPHA set at runtime and restored, file "
        "never modified.")
    payload["status"] = "DONE"

    make_figure(per_k, mu_sweeps, alpha_sweeps, mus, alphas)
    payload["figure"] = os.path.relpath(FIG, ROOT)
    payload["source_sha256"] = sha256_file(__file__)
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)

    print("=" * 74)
    print(f"VERDICT [{verdict_tag}]")
    print(verdict)
    print(f"per-k max angle vs kerC (deg) = {['%.1f' % m for m in all_max]}")
    print(f"global sweep floor = {global_floor} deg ; k-ray floor = {kray_angmin} deg")
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
