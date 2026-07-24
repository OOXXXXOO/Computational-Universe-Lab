"""RC1a -- REACHABILITY CAMPAIGN, milestone 1a (cheap representative points).

CAMPAIGN QUESTION (preregistration 任务书-可达性战役 §0/§3/§10): can the emergent
matter walk's PROPAGATION-INVARIANT curvature subspace be deformed onto the R30
complex's ker C so that (unprojected) N_prop = 2?  RC1a is the FIRST, CHEAP step:
reassemble placed kappa + Wilson + ker C + the tensor walk ON c = cos(theta)
(UNLOCKING R32's hardcoded c = C = cos(pi/3)), evaluate THREE observables at a
few representative (theta, dm, k) points, and look -- cheaply -- for a descent /
zero-crossing SIGNAL along the dm direction (R33: dm carries topological content,
gapless dm=0 -> gapped dm!=0).  RC1b (dense scan) only if RC1a shows a signal.

THE THREE OBSERVABLES (per (theta, dm, k), on the reassembled c=cos theta complex):
  (1) theta_princ(k) : principal angles between S_walk (walk's propagating
      curvature subspace) and the REASSEMBLED ker C = placed gauge(4)(+)TT(2).
      This is the DEFORMATION distance (near = deformable).  Reuses the R32
      principal-angle machine, now measured after rebuilding the complex.
  (2) I(theta,dm)    : a TENSOR-level topological index of the LOCKED subspace
      (constraint-row curvature modes, ker-C-orthogonal, the R28 病灶) -- a
      Berry-phase winding of that bundle around a closed BZ loop.  This is the
      TOPOLOGICAL distance (locked or not).  TENSOR level, NOT single particle
      (R33 hard requirement: single-particle winding is ill-defined at the
      gapless massless point).  HONEST: if it does not converge to a clean
      integer, we REPORT "not cleanly converged" -- that decides the §3 branch.
  (3) N_prop(theta,dm): unprojected propagating-curvature count (confirm 4-5 or
      drop to 2).

RC1a VERDICT (cheap, §10): along dm, is there a zero-crossing of I / a clear drop
of the max locked principal angle?
  SIGNAL      -> recommend RC1b dense scan; report the signal location.
  NO SIGNAL   -> (N_prop stays 4-5, max locked angle floor does not drop, I a
                 clean nonzero integer) pin the integer invariance, call
                 TOPOLOGICAL-LOCK CANDIDATE, hand to lane A.
  AMBIGUOUS   -> (I not a clean integer / angle drops but N_prop does not) report
                 honestly, flag NEEDS-COUNCIL.

HONESTY RED LINES (§7): two-sided blanks.  Do NOT inflate the lock into a
topological theorem unless I is a clean nonzero integer invariant; do NOT claim
deformation feasible unless N_prop measured = 2.  Direction verdict only; R30
existence & boundary unchanged (existence != emergence != M3).  Frozen inputs
imported READ-ONLY; the c=cos theta reassembly is written HERE, the frozen files
are never modified.  fp64 (RULESPACE_BACKEND=numpy).

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/rc1a_tensor_index_scan.py
"""
from __future__ import annotations

import hashlib
import json
import math
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

# ---- frozen, READ-ONLY imports ------------------------------------------
import cp1_v4_L2 as L2                                     # noqa: E402 walk_symbol(k, th)
import r25_auxiliary_wilson_complex as R25W               # noqa: E402 wilson_r/aux/PAULI
import r25_detour_complex as R25D                          # noqa: E402 gauge/dedonder(kappa)
import r25_dynamic_symbol as D1                            # noqa: E402 frozen damped_map (x-check)
import r25_realspace_step as RS                            # noqa: E402 frozen MU
from r15_walk_dedonder import (kappa_placed, shell_omega,  # noqa: E402 placed shell (takes c)
                               gauge_block, tt_basis)
import r32_reachability_probe as R32                       # noqa: E402 reuse tensor-complex fns

OUT = os.path.join(ROOT, "data", "results", "rc1a_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "rc1a_tensor_index.png")

N = 16
MU0 = RS.MU                                                # frozen constraint damping
NFIELD = 14
I4 = np.eye(4, dtype=complex)
I28 = np.eye(2 * NFIELD, dtype=complex)
SV_THRESH = R32.SV_THRESH                                 # 0.05 shared judge口径
UNIT_TOL = 2e-9
SZ = np.array([[1.0, 0.0], [0.0, -1.0]], complex)         # mass-coin generator

# representative k (one axial, one face-diagonal, one body-diagonal)
KSET = [(2, 0, 0), (2, 2, 0), (2, 2, 2)]
KLAB = {(2, 0, 0): "axial", (2, 2, 0): "face-diagonal", (2, 2, 2): "body-diagonal"}


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


# ==========================================================================
#  PART A.  c = cos(theta) REASSEMBLY of the walk propagator symbol.
#  Unlocks R32's hardcoded c = C = cos(pi/3).  theta sets the emergent speed
#  c = cos theta; dm is the mass-gap coin (dm=0 -> gapless Dirac point, dm!=0
#  -> gapped, exactly the R33 topological-content direction).
#  At (theta=pi/3, dm=0, c=0.5) every function below reduces BIT-FOR-BIT to the
#  frozen D1.damped_map -- asserted in the faithfulness certificate (PART D).
# ==========================================================================
_PAULI = R25W.PAULI_NUM                                    # [sx, sy, sz], frozen


def walk_symbol_p(kl, theta, dm):
    """L2.walk_symbol structure with (a) variable coin angle theta -> c=cos theta,
    (b) mass gap dm inserted in the second coin exactly as R33.walk_matrix_1
    (_coin_mat(-theta+dm)).  dm=0 => identical to L2.walk_symbol(kl, theta)."""
    import rulespace_gpu.tensor_coin_feedback as tcf
    Wx, Wy, Wz = tcf.axis_frames(theta)
    U = np.eye(2, dtype=complex)
    for kc, W in ((kl[0], Wx), (kl[1], Wy), (kl[2], Wz)):
        Da = np.diag([np.exp(-1j * kc), 1.0])
        Db = np.diag([1.0, np.exp(1j * kc)])
        Uax = (W.conj().T @ Db @ tcf._coin_mat(-theta + dm)
               @ Da @ tcf._coin_mat(theta) @ W)
        U = Uax @ U
    return U


def walk_data_p(kl, theta, dm):
    U = walk_symbol_p(np.asarray(kl, float), theta, dm)
    tr = float(np.real(np.trace(U)))
    r = R25W.wilson_r(kl)                                   # UV regulator, c-independent
    aw = 2.0 - tr + r * r
    return U, tr, r, aw


def base_kappa_p(U, z, c):
    a = np.trace(U) / 2
    b = np.array([1j * np.trace(s @ U) / 2 for s in _PAULI])
    return np.concatenate([[z - a], 1j * b]) / c


def augmented_K_p(kl, z, theta, dm, c):
    """8x14 augmented Wilson constraint at time-shift z (R25W.augmented_maps_at_z
    with c unlocked)."""
    U, _, r, _ = walk_data_p(kl, theta, dm)
    kap = base_kappa_p(U, z, c)
    G = R25D.gauge_matrix(kap)                             # (10,4)
    C = R25D.dedonder_matrix(kap)                          # (4,10)
    s = r / c
    Gp = np.vstack([G, s * I4])
    Cp = np.hstack([C, -z * s * I4])
    H = R25W.auxiliary_selector(U)
    Dp = np.hstack([s * H, -H @ G])
    return np.vstack([Cp, Dp]), G                          # Kp (8,14), G for reuse


def K_state_p(kl, theta, dm, c):
    _, _, _, aw = walk_data_p(kl, theta, dm)
    K0, _ = augmented_K_p(kl, 0.0, theta, dm, c)
    K1 = augmented_K_p(kl, 1.0, theta, dm, c)[0] - K0
    return np.hstack([K0 + (1.0 - aw) * K1, K1])           # (8,28)


def free_pair_p(aw):
    I = np.eye(NFIELD)
    return np.block([[(1 - aw) * I, I], [-aw * I, I]]).astype(complex)


def damped_map_p(kl, mu, theta, dm, c):
    """28x28 one-step walk propagator symbol on c=cos theta, mass dm.
    x -> F (I - mu K^dag K) x.  == D1.damped_map(k,mu)[0] at (pi/3,0,0.5)."""
    _, _, _, aw = walk_data_p(kl, theta, dm)
    F = free_pair_p(aw)
    K = K_state_p(kl, theta, dm, c)
    return F @ (I28 - mu * (K.conj().T @ K))


def kappa_placed_p(kl, c):
    """ker C is the R30 complex reassembled on the c=cos theta NULL shell
    (kappa.kappa=0, where ker C = gauge(4)(+)TT(2) holds -- R30 backbone).
    This is r15.kappa_placed with c unlocked; dm enters via the WALK (S_walk),
    NOT via the target complex.  Returns None outside the band."""
    return kappa_placed(np.asarray(kl, float), c)


# ==========================================================================
#  PART B.  the three observables at one (theta, dm, k).
#  ker C / sectors / inc_matrix come from R32 (pure fns of kap); the WALK
#  symbol is the c=cos theta / dm reassembly above.
# ==========================================================================
def walk_unit_modes_p(kl, mu, theta, dm, c, prop_tol=UNIT_TOL):
    """physical-h (10,n) unit-modulus modes of the reassembled walk symbol
    (mirror of R32.walk_unit_modes, but on damped_map_p)."""
    M = damped_map_p(kl, mu, theta, dm, c)
    eig, V = np.linalg.eig(M)
    idx = np.where(np.abs(np.abs(eig) - 1.0) < prop_tol)[0]
    U = V[:10, idx]
    U = U / (np.linalg.norm(U, axis=0, keepdims=True) + 1e-300)
    return U, np.angle(eig[idx]), np.abs(eig[idx])


def observables_at(kl, theta, dm, c, mu=MU0):
    """theta_princ(k), N_prop, and the raw material for I: locked frame + kerC.
    Returns None if this k is off the c=cos theta band."""
    k = np.array(kl, float) * (2 * np.pi / N)
    kapp = kappa_placed_p(k, c)
    if kapp is None:
        return None
    Q_kerC = R32.kerC_basis(kapp)
    Q_TT, Q_gauge, Q_row = R32.build_sectors(kapp)
    inc_mat = R32.inc_matrix(kapp)

    U10, phases, mods = walk_unit_modes_p(k, mu, theta, dm, c)
    if U10.shape[1] == 0:
        return {"n_unit": 0, "N_prop": 0, "off": True}
    dom = R32.dominant_branch(U10, phases, inc_mat)
    Scurv, nprop, svn = R32.curvature_subspace(U10, phases, inc_mat, dom)
    ang = np.degrees(R32.principal_angles(Scurv, Q_kerC))
    rmean, rmax = R32.residual_outside(U10, Q_kerC)
    sec = R32.sector_energy(Scurv, Q_TT, Q_gauge, Q_row)
    deg = np.sort(ang)
    return {
        "n_unit": int(U10.shape[1]), "dominant_branch": dom,
        "N_prop": int(nprop), "curv_sv": svn,
        "principal_angles_deg": [float(x) for x in deg],
        "max_angle_deg": float(deg.max()) if len(deg) else float("nan"),
        "min_angle_deg": float(deg.min()) if len(deg) else float("nan"),
        "n_inside_kerC(<5deg)": int(np.sum(deg < 5.0)),
        "n_locked(>45deg)": int(np.sum(deg > 45.0)),
        "mean_resid_outside_kerC": rmean, "max_resid_outside_kerC": rmax,
        "Scurv_sector_energy": sec, "off": False}


# ==========================================================================
#  PART C.  TENSOR TOPOLOGICAL INDEX I(theta, dm)  --  the major claim.
#
#  DEFINITION (for lane A independent audit):
#  * At each point k(phi) on a closed BZ loop around the representative k, build
#    the walk's PROPAGATING-CURVATURE subspace S_curv(k) (R32 machinery, on the
#    dominant Floquet branch) and the reassembled ker C(k).  This is a TENSOR
#    object (subspace of the 10-dim symmetric-tensor curvature space), NOT the
#    single-particle 2-spinor d-vector R33 showed is ill-defined at gapless pts.
#  * LOCKED BUNDLE L(k) = orthonormalized (I - P_kerC(k)) S_curv(k), keeping the
#    columns whose ker-C-orthogonal residual norm > BUNDLE_TOL.  This is exactly
#    the constraint-ROW curvature content (the R28/R31/R32 病灶): the part of the
#    propagating curvature that lives OUTSIDE ker C.  Its rank = n_locked.
#  * WILSON-LOOP / BERRY-PHASE INDEX.  Non-abelian Wilson loop around the loop:
#        W = prod_j  L_j^dag L_{j+1}      (L_nphi := L_0)
#    Berry phases {gamma_a} = -Im log(eig(W)); total Berry phase Gamma = sum_a.
#    Reported index I = Gamma / (2 pi).  (det-based winding, gauge-invariant.)
#  * INTEGER-NESS is NOT assumed.  We report |I - round(I)|, the loop-refinement
#    convergence (nphi = 24/48/96), and the BUNDLE GAP along the loop (min
#    principal angle of L vs ker C, and min gap of L vs TT).  A clean nonzero
#    integer invariant requires: (a) bundle gapped around the WHOLE loop (min
#    gap floored away from 0), (b) rank(L) constant, (c) I -> integer, stable
#    under refinement.  If any fails at the physical point we REPORT "index not
#    cleanly converged" (R33-consistent: the massless dm=0 point may be gapless
#    at the tensor level too).
# ==========================================================================
BUNDLE_TOL = 0.20          # ker-C-orthogonal residual to count a locked column
GAP_FLOOR_DEG = 5.0        # locked bundle must stay >this from ker C to be gapped


def _locked_frame(kl, theta, dm, c, mu=MU0):
    """orthonormal (10, n_locked) frame of the ker-C-orthogonal propagating
    curvature (the constraint-row curvature bundle) at one k."""
    k = np.array(kl, float) * (2 * np.pi / N)
    kapp = kappa_placed_p(k, c)
    if kapp is None:
        return None, None, None
    Q_kerC = R32.kerC_basis(kapp)
    Q_TT, _, _ = R32.build_sectors(kapp)
    inc_mat = R32.inc_matrix(kapp)
    U10, phases, _ = walk_unit_modes_p(k, mu, theta, dm, c)
    if U10.shape[1] == 0:
        return None, Q_kerC, Q_TT
    dom = R32.dominant_branch(U10, phases, inc_mat)
    Scurv, _, _ = R32.curvature_subspace(U10, phases, inc_mat, dom)
    if Scurv.shape[1] == 0:
        return np.zeros((10, 0)), Q_kerC, Q_TT
    perp = Scurv - Q_kerC @ (Q_kerC.conj().T @ Scurv)      # ker-C-orthogonal part
    Uu, sv, _ = np.linalg.svd(perp, full_matrices=False)
    keep = sv > BUNDLE_TOL
    return Uu[:, keep], Q_kerC, Q_TT


def _loop_points(kl, radius, nphi):
    """closed loop k_rep + radius*(cos phi e1 + sin phi e2) in lattice-k units,
    e1,e2 an orthonormal plane. Returns list of integer-free float nvecs."""
    base = np.array(kl, float)
    a = np.array([1.0, 0.0, 0.0]) if abs(base[0]) < 1e-9 or np.linalg.norm(base) < 1e-9 \
        else base / np.linalg.norm(base)
    ref = np.array([0.0, 0.0, 1.0])
    if abs(a @ ref) > 0.9:
        ref = np.array([0.0, 1.0, 0.0])
    e1 = ref - (ref @ a) * a
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    return [base + radius * (math.cos(p) * e1 + math.sin(p) * e2)
            for p in np.linspace(0.0, 2 * math.pi, nphi, endpoint=False)]


def tensor_index(kl, theta, dm, c, nphi=48, radius=0.6, mu=MU0):
    """Wilson-loop Berry-phase index of the LOCKED bundle around a BZ loop.
    Returns index, integer-ness, bundle-gap diagnostics, rank stability."""
    pts = _loop_points(kl, radius, nphi)
    frames, ranks, minang_kerC, minang_TT = [], [], [], []
    for nv in pts:
        k = np.array(nv, float) * (2 * np.pi / N)
        if shell_omega(k, c) is None or np.linalg.norm(k) < 1e-6:
            return {"defined": False, "reason": "loop leaves c=cos theta band",
                    "radius": radius, "nphi": nphi}
        L, Q_kerC, Q_TT = _locked_frame(nv, theta, dm, c, mu)
        if L is None or L.shape[1] == 0:
            return {"defined": False, "reason": "empty locked bundle on loop",
                    "radius": radius, "nphi": nphi}
        frames.append(L)
        ranks.append(L.shape[1])
        akc = np.degrees(R32.principal_angles(L, Q_kerC))   # locked vs ker C
        atl = np.degrees(R32.principal_angles(L, Q_TT))
        minang_kerC.append(float(akc.min()) if len(akc) else float("nan"))
        minang_TT.append(float(atl.min()) if len(atl) else float("nan"))
    rank_stable = len(set(ranks)) == 1
    gap_kerC = float(np.min(minang_kerC))                   # bundle-vs-kerC gap floor
    gap_TT = float(np.min(minang_TT))
    if not rank_stable:
        return {"defined": False, "reason": "locked-bundle rank not constant",
                "ranks_on_loop": sorted(set(ranks)), "radius": radius,
                "nphi": nphi, "bundle_gap_vs_kerC_deg": gap_kerC}
    # non-abelian Wilson loop (Berry phases) of the rank-constant bundle
    W = np.eye(frames[0].shape[1], dtype=complex)
    for j in range(len(frames)):
        M = frames[j].conj().T @ frames[(j + 1) % len(frames)]
        W = W @ M
    evals = np.linalg.eigvals(W)
    berry = np.angle(evals)                                 # per-eigenphase
    total = float(np.sum(berry))
    idx = total / (2 * math.pi)
    # det-winding (product of overlap dets, accumulated & unwrapped) --- robust
    logdet = 0.0
    for j in range(len(frames)):
        M = frames[j].conj().T @ frames[(j + 1) % len(frames)]
        logdet += np.angle(np.linalg.det(M))
    det_winding = float(logdet / (2 * math.pi))
    return {"defined": True, "rank": int(ranks[0]),
            "index_berry_over_2pi": idx,
            "index_det_winding": det_winding,
            "nearest_int": int(round(det_winding)),
            "int_dev": float(abs(det_winding - round(det_winding))),
            "berry_phases": [float(x) for x in np.sort(berry)],
            "bundle_gap_vs_kerC_deg": gap_kerC,
            "bundle_gap_vs_TT_deg": gap_TT,
            "gapped_around_loop": bool(gap_kerC > GAP_FLOOR_DEG),
            "radius": radius, "nphi": nphi}


# ==========================================================================
#  PART D.  faithfulness certificate + main driver
# ==========================================================================
TH0 = math.pi / 3.0
C0 = math.cos(TH0)                                          # 0.5 == L2.C


def faithfulness_certificate():
    """At (theta=pi/3, dm=0, c=cos pi/3=0.5) the reassembly MUST reduce to the
    frozen stack bit-for-bit: walk_symbol_p==L2.walk_symbol, K_state_p==D1.K_state,
    damped_map_p==D1.damped_map.  If not, RC1a is built on the wrong walk."""
    rng = np.random.default_rng(7)
    w_sym = w_kst = w_map = 0.0
    for _ in range(24):
        nv = rng.uniform(-3.0, 3.0, 3)
        w_sym = max(w_sym, float(np.abs(
            walk_symbol_p(nv, TH0, 0.0) - L2.walk_symbol(nv)).max()))
        w_kst = max(w_kst, float(np.abs(
            K_state_p(nv, TH0, 0.0, C0) - D1.K_state(nv)).max()))
        w_map = max(w_map, float(np.abs(
            damped_map_p(nv, MU0, TH0, 0.0, C0) - D1.damped_map(nv, MU0)[0]).max()))
    return {"walk_symbol_max_diff": w_sym, "K_state_max_diff": w_kst,
            "damped_map_max_diff": w_map,
            "PASS": bool(max(w_sym, w_kst, w_map) < 1e-11)}


def representative_points():
    """(theta, dm) representatives.  theta held at the calibrated pi/3 (c=0.5)
    so ker C & speed match R30/R32 exactly; dm scanned across the R33 phase
    point dm=0 (gapless) -> dm!=0 (gapped).  One extra theta (0.5, faster cone
    c=cos0.5) as a cheap theta-direction sanity check."""
    dm_line = [0.0, 0.05, 0.15, 0.3, 0.6]                   # R33 transition direction
    pts = [{"theta": TH0, "dm": dm, "tag": "th=pi/3 (c=0.5)"} for dm in dm_line]
    pts.append({"theta": 0.5, "dm": 0.0, "tag": "th=0.5 (c=%.3f)" % math.cos(0.5)})
    pts.append({"theta": 0.5, "dm": 0.3, "tag": "th=0.5 (c=%.3f)" % math.cos(0.5)})
    return pts


def build_verdict(rows, refine):
    """Cheap dm-direction signal verdict (§10 three-way)."""
    # gather, along the theta=pi/3 dm line, per-k: N_prop, max locked angle, I
    th0_rows = [r for r in rows if abs(r["theta"] - TH0) < 1e-9]
    th0_rows = sorted(th0_rows, key=lambda r: r["dm"])
    nprops, maxangs, idxs, intdevs, gaps = [], [], [], [], []
    for r in th0_rows:
        for kl in KSET:
            e = r["per_k"][str(kl)]
            obs, idx = e["observables"], e["index"]
            if obs and not obs.get("off"):
                nprops.append(obs["N_prop"])
                maxangs.append(obs["max_angle_deg"])
                if idx.get("defined"):
                    idxs.append(idx["index_det_winding"])
                    intdevs.append(idx["int_dev"])
                    gaps.append(idx["bundle_gap_vs_kerC_deg"])
    # dm-direction descent signal on the max locked principal angle
    # (per k, compare dm=0 vs largest dm)
    ang_drop = {}
    zero_cross = {}
    for kl in KSET:
        seq = [(r["dm"], r["per_k"][str(kl)]["observables"])
               for r in th0_rows
               if r["per_k"][str(kl)]["observables"]
               and not r["per_k"][str(kl)]["observables"].get("off")]
        if len(seq) >= 2:
            a0 = seq[0][1]["max_angle_deg"]
            amin = min(s[1]["max_angle_deg"] for s in seq)
            ang_drop[str(kl)] = {"dm0_max_angle": a0, "min_over_dm": amin,
                                 "drop_deg": a0 - amin}
        iseq = [(r["dm"], r["per_k"][str(kl)]["index"])
                for r in th0_rows
                if r["per_k"][str(kl)]["index"].get("defined")]
        if len(iseq) >= 2:
            ivals = [s[1]["index_det_winding"] for s in iseq]
            zero_cross[str(kl)] = {
                "I_by_dm": {f"{s[0]:.2f}": s[1]["index_det_winding"] for s in iseq},
                "crosses_zero": bool(min(ivals) < -0.4 and max(ivals) > 0.4)
                or bool(any(abs(v) < 0.25 for v in ivals)
                        and any(abs(v) > 0.75 for v in ivals)),
                "nearest_ints": [int(round(v)) for v in ivals],
                "int_changes": len(set(int(round(v)) for v in ivals)) > 1}

    # cheap thresholds
    ANG_DROP_SIGNAL = 15.0          # a "clear drop" in max locked angle (deg)
    REFINE_TOL = 0.25               # nphi-refinement spread to call I "converged"
    max_drop = max((d["drop_deg"] for d in ang_drop.values()), default=0.0)
    nprop_all_high = all(n >= 4 for n in nprops) if nprops else False
    nprop_hits_2 = any(n <= 2 for n in nprops)

    # -- index convergence FIRST: an integer-change is only a physical signal
    #    if the index itself is well-defined (converges under loop refinement).
    #    Non-convergent integer jumps are NUMERICAL noise (R33 discipline: the
    #    massless/tensor point may be gapless / the cheap bundle discontinuous),
    #    NOT a dm signal.  This gate prevents the R27 over-optimism trap.
    ref_defined = [r for r in refine if r.get("refine_spread") is not None
                   and np.isfinite(r.get("refine_spread", float("nan")))]
    max_refine_spread = (max(r["refine_spread"] for r in ref_defined)
                         if ref_defined else float("nan"))
    index_well_defined = bool(ref_defined) and max_refine_spread < REFINE_TOL
    # integer cleanliness (only meaningful if well-defined)
    clean_int = (index_well_defined and bool(intdevs) and max(intdevs) < 0.15
                 and all(g > GAP_FLOOR_DEG for g in gaps)
                 and all(abs(round(v)) >= 1 for v in idxs))
    ref_stable = index_well_defined
    # index-driven signal (gated on convergence)
    any_zero_cross = index_well_defined and any(
        z["crosses_zero"] or z["int_changes"] for z in zero_cross.values())

    signal = (max_drop > ANG_DROP_SIGNAL) or any_zero_cross or nprop_hits_2

    if signal:
        tag = "SIGNAL (dm direction shows a descent / index change)"
        verdict = (
            "Along dm, the reassembled c=cos theta complex shows a REACHABILITY "
            "SIGNAL: max locked principal angle drops by up to %.1f deg and/or the "
            "tensor index changes integer / crosses zero and/or N_prop reaches <=2 "
            "at some (theta,dm,k). RECOMMEND RC1b dense (theta,dm) scan targeting "
            "the signal location(s). This is a DIRECTION recommendation, NOT a "
            "proven deformation channel (N_prop measured=2 with residual->0 is the "
            "RC2 acceptance, not shown here)." % max_drop)
    elif nprop_all_high and max_drop <= ANG_DROP_SIGNAL and not nprop_hits_2:
        if clean_int and ref_stable:
            tag = ("TOPOLOGICAL-LOCK CANDIDATE (clean nonzero integer tensor index)")
            verdict = (
                "No dm-direction signal: across all representative (theta,dm,k) the "
                "unprojected N_prop stays 4-5, the max locked principal angle floor "
                "does not drop (max drop %.1f deg < %.0f), AND the tensor locked-"
                "bundle index is a CLEAN NONZERO INTEGER (max |I-round(I)| = %.3f, "
                "gapped around the loop, stable under nphi refinement spread %.3f). "
                "Call TOPOLOGICAL-LOCK CANDIDATE; hand the index definition to lane "
                "A for independent audit (R28/R30 adversarial standard). HONEST: "
                "tensor-DOF inheritance of the winding is a subspace-topology "
                "statement on the reassembled complex, audited by lane A before any "
                "no-go theorem claim." % (max_drop, ANG_DROP_SIGNAL, max(intdevs),
                                          max(r["refine_spread"] for r in ref_defined)))
        else:
            tag = ("NEEDS-COUNCIL (index not cleanly converged; no angle/N_prop signal)")
            verdict = (
                "No dm-direction angle/N_prop signal (N_prop stays 4-5 -- never 2, "
                "max locked-angle floor drop only %.1f deg), BUT the tensor index "
                "does NOT converge to a clean integer: under BZ-loop refinement "
                "(nphi 24/48/96) the det-winding jumps by up to %.1f (>> tol %.2f), "
                "so the locked constraint-row bundle is NOT a smooth gapped "
                "subbundle over the loop and carries NO clean quantized invariant. "
                "Per the honesty discipline (R33-consistent: the massless/tensor "
                "point is plausibly gapless at the bundle level too) this is "
                "INDEX NOT CLEANLY CONVERGED -> NEEDS-COUNCIL. Two-sided blanks "
                "held: NOT a topological lock (no clean integer), NOT deformation-"
                "feasible (N_prop never 2). The apparent integer 'jumps' along dm "
                "are refinement noise, not a physical zero-crossing." % (
                    max_drop, max_refine_spread, REFINE_TOL))
    else:
        tag = "NEEDS-COUNCIL (mixed / ambiguous)"
        verdict = (
            "Mixed evidence (angle drop %.1f deg, N_prop hits<=2: %s, zero-cross: "
            "%s, clean integer: %s). Neither a clean deformation signal nor a clean "
            "topological lock. Report honestly, flag NEEDS-COUNCIL." % (
                max_drop, nprop_hits_2, any_zero_cross, clean_int))

    return {
        "verdict_tag": tag, "verdict": verdict,
        "signal_metrics": {
            "max_locked_angle_drop_deg": max_drop,
            "angle_drop_by_k": ang_drop,
            "index_zero_crossing_by_k": zero_cross,
            "N_prop_values_th0_line": nprops,
            "N_prop_all_ge4": nprop_all_high, "N_prop_hits_2": nprop_hits_2,
            "index_clean_nonzero_integer": clean_int,
            "index_well_defined_converges": index_well_defined,
            "index_max_refine_spread": max_refine_spread,
            "index_refine_stable": ref_stable,
            "index_int_devs": intdevs, "index_values": idxs,
            "bundle_gaps_deg": gaps},
    }


def make_figure(rows):
    th0_rows = sorted([r for r in rows if abs(r["theta"] - TH0) < 1e-9],
                      key=lambda r: r["dm"])
    dms = [r["dm"] for r in th0_rows]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))
    ax = axes[0]
    for kl in KSET:
        ys = [r["per_k"][str(kl)]["observables"].get("max_angle_deg", float("nan"))
              if r["per_k"][str(kl)]["observables"] else float("nan")
              for r in th0_rows]
        ax.plot(dms, ys, marker="o", label=f"{kl} [{KLAB[kl]}]")
    ax.axhline(5, color="green", ls=":", lw=0.8)
    ax.set_xlabel("dm (mass gap)"); ax.set_ylabel("max locked principal angle (deg)")
    ax.set_title("obs1: max angle S_walk vs ker C\n(drop toward 0 = deformation signal)")
    ax.set_ylim(-3, 95); ax.legend(fontsize=7)
    ax = axes[1]
    for kl in KSET:
        ys = [r["per_k"][str(kl)]["observables"].get("N_prop", float("nan"))
              if r["per_k"][str(kl)]["observables"] else float("nan")
              for r in th0_rows]
        ax.plot(dms, ys, marker="s", label=str(kl))
    ax.axhline(2, color="green", ls=":", lw=0.8)
    ax.set_xlabel("dm"); ax.set_ylabel("N_prop (unprojected)")
    ax.set_title("obs3: N_prop\n(-> 2 = reachable count)")
    ax.set_ylim(0, 6.5); ax.legend(fontsize=7)
    ax = axes[2]
    for kl in KSET:
        ys = [r["per_k"][str(kl)]["index"].get("index_det_winding", float("nan"))
              if r["per_k"][str(kl)]["index"].get("defined") else float("nan")
              for r in th0_rows]
        ax.plot(dms, ys, marker="^", label=str(kl))
    ax.axhline(0, color="gray", ls=":", lw=0.8)
    ax.set_xlabel("dm"); ax.set_ylabel("tensor index I (det-winding / 2pi)")
    ax.set_title("obs2: tensor locked-bundle index\n(zero-cross / int change = signal)")
    ax.legend(fontsize=7)
    fig.suptitle("RC1a: three observables along the dm direction (theta=pi/3, c=0.5 "
                 "reassembly)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110)
    plt.close(fig)


def main():
    t0 = time.time()
    payload = {
        "register": "RC1a-tensor-index-representative (reachability campaign milestone 1a)",
        "status": "RUNNING", "backend": "numpy",
        "question": ("on c=cos theta reassembly, does the dm direction show a "
                     "zero-crossing of the tensor index I / a drop of the max "
                     "locked principal angle (a deformation channel signal)?"),
        "params": {"N": N, "mu": MU0, "kset": [list(k) for k in KSET],
                   "sv_thresh": SV_THRESH, "bundle_tol": BUNDLE_TOL,
                   "gap_floor_deg": GAP_FLOOR_DEG},
        "index_definition": (
            "Wilson-loop (non-abelian Berry-phase / det-winding) of the LOCKED "
            "bundle L(k) = orthonormalized (I-P_kerC) S_curv (constraint-row "
            "curvature, ker-C-orthogonal) around a closed BZ loop of radius "
            "0.6 (lattice-k) about the representative k. TENSOR level (subspace "
            "of the 10-dim symmetric-tensor curvature space), NOT single-particle. "
            "I = det-winding/2pi. Clean integer requires: bundle gapped around the "
            "whole loop, rank constant, I->integer stable under nphi refinement."),
        "frozen_inputs_sha256": {
            "cp1_v4_L2.py": sha256_file(os.path.join(DIR, "cp1_v4_L2.py")),
            "r25_auxiliary_wilson_complex.py": sha256_file(os.path.join(DIR, "r25_auxiliary_wilson_complex.py")),
            "r25_detour_complex.py": sha256_file(os.path.join(DIR, "r25_detour_complex.py")),
            "r25_dynamic_symbol.py": sha256_file(os.path.join(DIR, "r25_dynamic_symbol.py")),
            "r25_realspace_step.py": sha256_file(os.path.join(DIR, "r25_realspace_step.py")),
            "r15_walk_dedonder.py": sha256_file(os.path.join(DIR, "r15_walk_dedonder.py")),
            "r32_reachability_probe.py": sha256_file(os.path.join(DIR, "r32_reachability_probe.py")),
        },
        "red_lines": ("direction verdict only; two-sided blanks (no topological "
                      "theorem unless I clean nonzero integer; no deformation-"
                      "feasible unless N_prop measured=2). R30 existence & boundary "
                      "unchanged. frozen inputs read-only; c=cos theta reassembly "
                      "written here, frozen files untouched. fp64."),
    }
    write_json(payload)

    print("RC1a tensor-index representative scan (c = cos theta reassembly)")
    print("=" * 74)

    cert = faithfulness_certificate()
    payload["faithfulness_certificate"] = cert
    print(f"[cert] reassembly vs frozen @ (pi/3,dm=0,c=0.5): "
          f"walk {cert['walk_symbol_max_diff']:.1e} K {cert['K_state_max_diff']:.1e} "
          f"map {cert['damped_map_max_diff']:.1e} -> "
          f"{'PASS' if cert['PASS'] else 'FAIL'}")
    write_json(payload)
    if not cert["PASS"]:
        payload["status"] = "ABORT-faithfulness-failed"
        write_json(payload)
        print("ABORT: reassembly does not reduce to frozen stack; not proceeding.")
        return

    pts = representative_points()
    rows = []
    for pt in pts:
        theta, dm = pt["theta"], pt["dm"]
        c = math.cos(theta)
        entry = {**pt, "c": c, "per_k": {}}
        for kl in KSET:
            obs = observables_at(kl, theta, c=c, dm=dm)
            idx = tensor_index(kl, theta, dm, c) if obs and not obs.get("off") else \
                {"defined": False, "reason": "no observables"}
            entry["per_k"][str(kl)] = {"observables": obs, "index": idx}
            if obs and not obs.get("off"):
                iv = (f"{idx['index_det_winding']:+.3f}(int?{idx['int_dev']:.2f},"
                      f"gap{idx['bundle_gap_vs_kerC_deg']:.0f})") if idx.get("defined") \
                      else f"undef({idx.get('reason','')[:18]})"
                print(f"  theta={theta:.3f} dm={dm:.2f} k={kl} [{KLAB[kl]:>13}]: "
                      f"N_prop={obs['N_prop']} maxang={obs['max_angle_deg']:.1f} "
                      f"locked={obs['n_locked(>45deg)']} I={iv}")
            else:
                print(f"  theta={theta:.3f} dm={dm:.2f} k={kl}: off-band/no modes")
        rows.append(entry)
        write_json({**payload, "scan_partial": rows})
    payload["scan"] = rows

    # -- refinement of I at the physical point for integer-ness evidence -----
    print("[refine] tensor index nphi convergence at physical points ...")
    refine = []
    for pt in pts:
        theta, dm, c = pt["theta"], pt["dm"], math.cos(pt["theta"])
        for kl in KSET:
            base = tensor_index(kl, theta, dm, c, nphi=48)
            if not base.get("defined"):
                continue
            conv = {str(nn): tensor_index(kl, theta, dm, c, nphi=nn)
                    for nn in (24, 48, 96)}
            vals = [conv[str(nn)].get("index_det_winding") for nn in (24, 48, 96)
                    if conv[str(nn)].get("defined")]
            spread = float(max(vals) - min(vals)) if len(vals) > 1 else float("nan")
            refine.append({"theta": theta, "dm": dm, "k": list(kl),
                           "det_winding_by_nphi":
                               {nn: conv[str(nn)].get("index_det_winding")
                                for nn in (24, 48, 96)},
                           "refine_spread": spread,
                           "rank": base.get("rank"),
                           "gap_vs_kerC_deg": base.get("bundle_gap_vs_kerC_deg"),
                           "gapped": base.get("gapped_around_loop")})
    payload["index_refinement"] = refine
    write_json(payload)

    # -- dm-direction signal verdict (cheap) ---------------------------------
    verdict = build_verdict(rows, refine)
    payload.update(verdict)
    write_json(payload)

    make_figure(rows)
    payload["figure"] = os.path.relpath(FIG, ROOT)
    payload["status"] = "DONE"
    payload["source_sha256"] = sha256_file(__file__)
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)

    print("=" * 74)
    print(f"VERDICT [{verdict['verdict_tag']}]")
    print(verdict["verdict"])
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()



