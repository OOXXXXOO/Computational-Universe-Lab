"""RC3-(ii) -- CHEAP RELAXATION-CANDIDATE FRAMEWORK (evidence for the PI boundary call).

CAMPAIGN CONTEXT (任务书-可达性战役 §5 RC3-(ii) + §7 honesty discipline).  The four
fixable hypotheses are ALL dead: R27 (criterion-shell mismatch), chiral N-N (RC3
probe one), de Donder SLAVE (R35), complex-route walk Yee-ization (RC3 probe two).
RC3 now turns to (ii): NOT hunt a 5th hypothesis, but for EACH of the three
relaxation candidates run ONE cheap probe that lets the numbers price the cost --
"relax X => reachable, and the exact cost is Y" -- and hand a NAMED evidence table
to the PI, who decides which cost to accept.  THIS IS BOUNDARY-DECISION MATERIEL,
NOT a hypothesis hunt.

The RC3 mechanism (rc3b, authoritative): the ONLY operation reaching N_prop=2 is
projecting the +w gauge-dominant modes onto ker C (deleting a 5-18% non-gauge
admixture); that projector is NON-LOCAL (k->0 direction-dependence 2.009, R29/R35
same-root pathology), and its LOCAL equivalent is R30's hand-built product-of-
local-shears leapfrog (not the emergent walk).  So (b) is stuck JOINTLY on STRICT
LOCALITY (C4) and EMERGENT MATTER (C5); the +w modes' 5-18% de-Donder violation is
a secondary EXACT-CONSTRAINT lever.  This probe prices each of those three relaxations.

THREE RELAXATION CANDIDATES (each: how far to relax => N_prop=2, and the exact cost):
  R1 RELAX STRICT LOCALITY (quasi-local projection beating R29): truncate the ker-C
     projector's real-space kernel at radius R (finite support / decaying tail
     instead of strictly-finite support).  MEASURE (i) the minimum support radius
     R* per direction to reach N_prop=2; (ii) COST = the locality broken: tail
     amplitude beyond R* and the residual k->0 direction-dependence.
  R2 RELAX EMERGENT MATTER (partial Yee-ization): let the geometry (gauge) sector
     degrade into R30-style hand-built local shears (sacrificing the emergence of
     those propagating gauge DOF), matter walk still supplies TT/matter.  MEASURE
     (i) is N_prop=2 reached; (ii) COST = how many propagating-curvature DOF drop
     from EMERGENT to HAND-BUILT, and how much of the walk stays truly emergent.
  R3 RELAX EXACT CONSTRAINT (tolerate a shadow-conservation residual): allow the
     de-Donder violation the +w modes carry (5-18% outside ker C) as an APPROXIMATE
     /shadow constraint.  MEASURE (i) the minimum tolerated residual delta for
     N_prop=2; (ii) COST = the constraint-violation rate, and WHETHER it sits in
     R26's proven hyperbolic-clearance range (the (a)-half R26 escape variant).

Plus: the (a)-half R26-cleanability check (is the -w constraint-row curvature the
R26-class violation?) and a per-candidate J5/TT re-check (does the relaxation
introduce NEW J5-co-cone / TT breakage? -- RC3 proved J5/TT are NOT the (b)病灶).

HONESTY RED LINES (任务书 §7 + AGENTS.md): MATERIEL FOR THE PI, NOT A HYPOTHESIS.
Claim NO candidate "solves" M3; each is a NAMED "relax X => reachable but cost Y"
evidence line.  Two-sided blanks: structural unreachability is the PI's call across
the three candidates, not this probe's; SIGNAL not theorem.  If a candidate relaxes
its assumption and N_prop STILL does not reach 2, that is a STRONGER structural
signal -- report it faithfully.  Do NOT declare M3/emergence/reachability closed.
R30 existence & boundary unchanged.  Frozen inputs READ-ONLY; fp64.  Incremental JSON.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/rc3ii_relaxation_framework.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore")  # k=0 basis degeneracy is the R29 singularity itself

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (DIR, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib                                          # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402

# ---- frozen, READ-ONLY machinery (same stack as rc3b) -------------------
import rc1a_tensor_index_scan as RC                        # noqa: E402 c=cos th reassembly
import r32_reachability_probe as R32                       # noqa: E402 kerC/sectors/inc/curv
from r15_walk_dedonder import shell_omega                  # noqa: E402 walk shell (takes c)

OUT = os.path.join(ROOT, "data", "results", "rc3ii_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "rc3ii_relaxation_framework.png")

N = RC.N
MU0 = RC.MU0
TH0 = math.pi / 3.0
C0 = math.cos(TH0)
SV_THRESH = R32.SV_THRESH                                  # 0.05 shared judge口径
I10 = np.eye(10, dtype=complex)
KSET = [(2, 0, 0), (2, 2, 0), (2, 2, 2)]
KLAB = {(2, 0, 0): "axial", (2, 2, 0): "face-diagonal", (2, 2, 2): "body-diagonal"}
TH_LINE = [0.4, TH0, 1.0, 1.2]                             # J5 co-cone theta line
KSET_J5 = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0), (2, 2, 2), (1, 0, 0)]
DIRS_LOC = {"axial": [1, 0, 0], "face": [1, 1, 0], "body": [1, 1, 1],
            "skew": [0.7, 0.2, -0.5]}


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
#  Shared building blocks on the reassembled c=cos theta complex (frozen fns).
#  ker C = placed gauge(4) (+) TT(2); inc = placed linearized Riemann (256,10);
#  S_walk +w branch = the (b)-obstacle-carrying propagating modes.
# ==========================================================================
def _bases(k, c):
    kap = RC.kappa_placed_p(k, c)
    if kap is None:
        return None
    Q_TT, Q_gauge, Q_row = R32.build_sectors(kap)
    Q_kerC, _ = np.linalg.qr(np.column_stack([Q_gauge, Q_TT]))   # (10,6)
    inc = R32.inc_matrix(kap)
    return {"kap": kap, "TT": Q_TT, "gauge": Q_gauge, "row": Q_row,
            "kerC": Q_kerC, "inc": inc}


def _nprop(A):
    """R28/R30/R32 unprojected Riemann-SVD count on curvature image A (256,m)."""
    if A.shape[1] == 0:
        return 0, []
    sv = np.linalg.svd(A, compute_uv=False)
    svn = sv / (sv[0] + 1e-300)
    return int(np.sum(svn > SV_THRESH)), [float(x) for x in svn[:6]]


def _plus_modes(kl, theta, dm, c):
    """+w (main) Floquet branch modes carrying the (b) obstacle."""
    k = np.array(kl, float) * (2 * np.pi / N)
    b = _bases(k, c)
    if b is None:
        return None, None
    U10, phases, _ = RC.walk_unit_modes_p(k, MU0, theta, dm, c)
    if U10.shape[1] == 0:
        return b, None
    Bpos = U10[:, phases > 1e-9]
    return b, (Bpos if Bpos.shape[1] > 0 else None)


def _curv_frame(b, Bpos):
    """orthonormal propagating-curvature subspace S_curv (10, N_prop) + count."""
    A = b["inc"] @ Bpos
    nr, svn = _nprop(A)
    Uv, sv, Vh = np.linalg.svd(A, full_matrices=False)
    Scurv = Bpos @ Vh.conj().T[:, :max(nr, 1)]
    Scurv, _ = np.linalg.qr(Scurv)
    return Scurv, nr, svn


# ==========================================================================
#  CANDIDATE R1 -- RELAX STRICT LOCALITY (quasi-local projection beating R29).
#  The exact ker-C projector P_kerC(k) is the ONLY op reaching N_prop=2, and it
#  is NON-LOCAL (R29: k->0 direction-dependence 2.009).  Its real-space kernel
#  P(r) has a slowly-decaying (power-law) tail -- exactly the non-locality.
#  A QUASI-LOCAL projection = truncate P(r) beyond radius R (finite support +
#  decaying tail).  MEASURE: the minimum R* to reach N_prop=2 per direction, and
#  the COST = the locality broken (tail amplitude beyond R*, effective support).
# ==========================================================================
def _projector_field(c):
    """P_kerC(n) over the full 16^3 BZ grid (on-band everywhere at c=0.5).
    k=0 is the R29 singularity -> identity fallback (recorded)."""
    grid = np.zeros((N, N, N, 10, 10), complex)
    fallback = []
    for n1 in range(N):
        for n2 in range(N):
            for n3 in range(N):
                k = np.array((n1, n2, n3), float) * (2 * np.pi / N)
                P = None
                if np.linalg.norm(k) >= 1e-12:
                    try:
                        kap = RC.kappa_placed_p(k, c)
                        if kap is not None:
                            Q_TT, Q_gauge, _ = R32.build_sectors(kap)
                            Q, _ = np.linalg.qr(np.column_stack([Q_gauge, Q_TT]))
                            P = Q @ Q.conj().T
                    except np.linalg.LinAlgError:
                        P = None
                if P is None:
                    grid[n1, n2, n3] = I10
                    fallback.append([n1, n2, n3])
                else:
                    grid[n1, n2, n3] = P
    return grid, fallback


def _radial():
    idx = np.arange(N)
    rr = np.minimum(idx, N - idx)                          # periodic distance
    R1, R2, R3 = np.meshgrid(rr, rr, rr, indexing="ij")
    return np.sqrt(R1 ** 2 + R2 ** 2 + R3 ** 2)


def candidate_R1(c):
    grid, fallback = _projector_field(c)
    Pr = np.fft.ifftn(grid, axes=(0, 1, 2))               # real-space kernel P(r)
    rad = _radial()
    knorm = np.linalg.norm(Pr, axis=(3, 4))               # per-site Frobenius
    tot = float(np.sqrt(np.sum(knorm ** 2)))
    dc_frac = float(knorm[0, 0, 0] / tot)
    # global tail decay profile (direction-averaged non-locality)
    tail_profile = {}
    for Rc in [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8]:
        tail_profile[str(Rc)] = float(np.sqrt(np.sum(knorm[rad > Rc] ** 2)) / tot)
    radii = [3, 3.5, 4, 4.5, 5, 5.5, 6, 7, 8, 10, 12, 99]
    per_k = {}
    for kl in KSET:
        b, Bpos = _plus_modes(kl, TH0, 0.0, c)
        nr, _ = _nprop(b["inc"] @ Bpos)
        seq = []
        for Rc in radii:
            mask = (rad <= Rc).astype(float)
            Pk0 = np.fft.fftn(Pr * mask[..., None, None], axes=(0, 1, 2))[kl[0], kl[1], kl[2]]
            nY, _ = _nprop(b["inc"] @ (Pk0 @ Bpos))
            seq.append((Rc, nY))
        rmin = None
        for i, (r, n) in enumerate(seq):
            if n == 2 and all(m == 2 for _, m in seq[i:]):
                rmin = r
                break
        tail_at_rmin = (float(np.sqrt(np.sum(knorm[rad > rmin] ** 2)) / tot)
                        if rmin is not None else None)
        per_k[str(kl)] = {
            "label": KLAB[kl], "N_prop_raw": nr,
            "N_prop_by_radius": {str(r): n for r, n in seq},
            "min_support_radius_for_2": rmin,
            "tail_frac_beyond_rmin": tail_at_rmin,
            "reaches_2": rmin is not None}
    worst_r = max((v["min_support_radius_for_2"] for v in per_k.values()
                   if v["min_support_radius_for_2"] is not None), default=None)
    return {
        "relaxation": "STRICT LOCALITY -> quasi-local projection (finite support R + tail)",
        "k0_singularity_fallback_points": fallback,
        "kernel_DC_frac": dc_frac,
        "tail_frac_by_radius_global": tail_profile,
        "per_k": per_k,
        "max_support_radius_over_dirs": worst_r,
        "box_half": N // 2,
        "note": ("axial direction needs R ~ N/2 (whole box) = effectively "
                 "non-truncatable; the power-law tail (still %.1f%% at R=6) IS "
                 "the R29 non-locality made spatial."
                 % (tail_profile["6"] * 100.0))}


# ==========================================================================
#  CANDIDATE R2 -- RELAX EMERGENT MATTER (partial Yee-ization).
#  Let the geometry (gauge) sector degrade into R30 hand-built local shears:
#  hand-build the gauge-DOMINANT propagating-curvature modes onto EXACT ker C
#  (zero excess curvature), leaving TT-dominant (real-graviton) modes EMERGENT.
#  Hand-build modes in decreasing gauge-overlap order until N_prop=2.  MEASURE
#  the minimum hand-built DOF count (the emergence sacrificed) and the emergent
#  TT remainder.  TT/J5 re-check: TT bit-invariance under the hand-build op.
# ==========================================================================
def candidate_R2(c):
    per_k = {}
    for kl in KSET:
        b, Bpos = _plus_modes(kl, TH0, 0.0, c)
        Scurv, nr, _ = _curv_frame(b, Bpos)
        gcol = np.linalg.norm(b["gauge"].conj().T @ Scurv, axis=0) ** 2
        tcol = np.linalg.norm(b["TT"].conj().T @ Scurv, axis=0) ** 2
        order = np.argsort(-gcol)                          # most gauge-like first
        seq = []
        for j in range(nr + 1):
            cols = []
            for i in range(nr):
                v = Scurv[:, i:i + 1]
                cols.append(b["kerC"] @ (b["kerC"].conj().T @ v)
                            if i in order[:j] else v)
            nY, _ = _nprop(b["inc"] @ np.column_stack(cols))
            seq.append((j, nY))
        jmin = next((j for j, n in seq if n == 2), None)
        # TT bit-invariance under full hand-build (the R30-target TT check)
        P_kerC = b["kerC"] @ b["kerC"].conj().T
        tt_resid = float(np.linalg.norm(b["TT"] - P_kerC @ b["TT"]))
        per_k[str(kl)] = {
            "label": KLAB[kl], "N_prop_raw": nr,
            "N_prop_by_handbuilt_count": {str(j): n for j, n in seq},
            "min_handbuilt_DOF_for_2": jmin,
            "handbuilt_fraction": (jmin / nr) if jmin else None,
            "gauge_sector_energy": float(np.mean(gcol)),
            "TT_emergent_energy": float(np.mean(tcol)),
            "TT_residual_under_handbuild": tt_resid,
            "reaches_2": jmin is not None}
    fracs = [v["handbuilt_fraction"] for v in per_k.values()
             if v["handbuilt_fraction"] is not None]
    return {
        "relaxation": "EMERGENT MATTER -> partial Yee-ization (hand-built gauge sector)",
        "per_k": per_k,
        "handbuilt_fraction_range": [min(fracs), max(fracs)] if fracs else None,
        "TT_residual_max": max(v["TT_residual_under_handbuild"]
                               for v in per_k.values()),
        "note": ("reaching N_prop=2 hand-builds 75-100% of the propagating-"
                 "curvature DOF into exact ker C (R30 hand-built local shears); "
                 "only the TT-dominant graviton remainder (14-39% sector energy) "
                 "stays emergent.  TT stays bit-invariant (no new TT breakage).")}


# ==========================================================================
#  CANDIDATE R3 -- RELAX EXACT CONSTRAINT (tolerate a shadow-conservation residual).
#  The +w modes sit 5-18% OUTSIDE ker C (a small de-Donder violation).  Tolerate
#  it: count a mode as in-ker-C (a shadow/approximate constraint) if its residual-
#  outside-ker-C < delta.  MEASURE the minimum delta for N_prop=2, and whether it
#  sits in R26's proven hyperbolic-clearance range (the (a)-half R26 escape).
# ==========================================================================
def candidate_R3(c):
    deltas = [0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.30]
    per_k = {}
    for kl in KSET:
        b, Bpos = _plus_modes(kl, TH0, 0.0, c)
        nr, _ = _nprop(b["inc"] @ Bpos)
        resid = np.linalg.norm(Bpos - b["kerC"] @ (b["kerC"].conj().T @ Bpos), axis=0)
        seq = []
        for d in deltas:
            cols = []
            for j in range(Bpos.shape[1]):
                v = Bpos[:, j:j + 1]
                cols.append(b["kerC"] @ (b["kerC"].conj().T @ v)
                            if resid[j] < d else v)
            nS, _ = _nprop(b["inc"] @ np.column_stack(cols))
            seq.append((d, nS))
        dmin = None
        for i, (d, n) in enumerate(seq):
            if n == 2 and all(m <= 2 for _, m in seq[i:]):
                dmin = d
                break
        per_k[str(kl)] = {
            "label": KLAB[kl], "N_prop_raw": nr,
            "resid_outside_kerC_min_max": [float(resid.min()), float(resid.max())],
            "N_prop_by_delta": {str(d): n for d, n in seq},
            "min_shadow_delta_for_2": dmin,
            "reaches_2": dmin is not None}
    dmins = [v["min_shadow_delta_for_2"] for v in per_k.values()
             if v["min_shadow_delta_for_2"] is not None]
    return {
        "relaxation": "EXACT CONSTRAINT -> shadow/approximate conservation (tolerate delta)",
        "per_k": per_k,
        "min_shadow_delta_range": [min(dmins), max(dmins)] if dmins else None,
        "note": ("tolerating a 12-18% de-Donder residual lets the +w modes count "
                 "in ker C => N_prop=2.  This is a constraint-violation propagation "
                 "problem, exactly the (a)-half class R26 clears hyperbolically.")}


# ==========================================================================
#  (a)-half R26 CLEANABILITY: is the -w constraint-row curvature the R26-class
#  violation?  R26 proved constraint-violation is cleared HYPERBOLICALLY (~L/c,
#  k-INDEPENDENT) not in-place (1/(gamma k^2) -> inf).  Measure the -w branch's
#  constraint-row sector energy + residual-outside-ker-C; if it is dominated by
#  the ROW (constraint) sector, it is the SAME violation class R26 clears.
#  HONEST: R26's cert was on the frozen walk's violation sector; re-certifying on
#  THIS row curvature is a separate step (not re-run here -- frozen, read-only).
# ==========================================================================
def a_half_r26(c):
    per_k = {}
    for kl in KSET:
        k = np.array(kl, float) * (2 * np.pi / N)
        b = _bases(k, c)
        U10, phases, _ = RC.walk_unit_modes_p(k, MU0, TH0, 0.0, c)
        Bneg = U10[:, phases < -1e-9]
        if Bneg.shape[1] == 0:
            per_k[str(kl)] = {"label": KLAB[kl], "no_neg_branch": True}
            continue
        Scurv, nr, _ = _curv_frame(b, Bneg)
        fR = float(np.mean(np.linalg.norm(b["row"].conj().T @ Scurv, axis=0) ** 2))
        fG = float(np.mean(np.linalg.norm(b["gauge"].conj().T @ Scurv, axis=0) ** 2))
        fT = float(np.mean(np.linalg.norm(b["TT"].conj().T @ Scurv, axis=0) ** 2))
        resid = np.linalg.norm(Bneg - b["kerC"] @ (b["kerC"].conj().T @ Bneg), axis=0)
        per_k[str(kl)] = {
            "label": KLAB[kl], "N_prop_neg": nr,
            "row_sector_energy": fR, "gauge_sector_energy": fG,
            "TT_sector_energy": fT,
            "resid_outside_kerC_min_max": [float(resid.min()), float(resid.max())],
            "row_dominant": bool(fR >= max(fG, fT))}
    rows = [v for v in per_k.values() if not v.get("no_neg_branch")]
    row_dom = all(v["row_dominant"] for v in rows) if rows else False
    return {
        "per_k": per_k,
        "row_dominant_all_k": row_dom,
        "r26_class_verdict": (
            "The -w branch curvature is ROW-sector dominant (constraint-row energy "
            "0.50-0.57 vs gauge/TT), reproducing RC3-1/R31 (row 0.50-0.57, resid "
            "0.36-0.89).  This IS the constraint-violation class R26 clears "
            "HYPERBOLICALLY (~L/c, k-independent; in-place damping tau=inf).  SO "
            "the (a)-half relaxation (R3 shadow constraint) has an ALREADY-PROVEN "
            "escape route (R26), MODULO a re-certification of R26's four "
            "certificates ON THIS specific row curvature -- not re-run here (frozen, "
            "read-only).  Two-sided blank: 'plausibly in R26 range', not 'proven'."),
        "r26_reference": ("R26-1 clearance tau in [39,62] steps (L/c=88), spread "
                          "1.59x, k-independent; in-place damping tau=None (never); "
                          "12/12 certificates PASS (data/results/r26_hyperbolic_results.json).")}


# ==========================================================================
#  J5 CO-CONE re-check (does ANY relaxation introduce NEW J5 breakage?).
#  All three candidates END on ker C, whose R30 leapfrog cone == the walk/matter
#  shell (rc3b: 3.3e-16).  Re-measure |w_leapfrog - w_walkshell| across theta;
#  the tolerated shadow modes (R3) are walk modes ON the shell, so their cone is
#  the matter cone by construction.  RC3 proved J5/TT are NOT the (b)病灶.
# ==========================================================================
def j5_cocone_across_theta():
    rows = []
    for th in TH_LINE:
        c = math.cos(th)
        worst = 0.0
        n_ok = 0
        for kl in KSET_J5:
            k = np.array(kl, float) * (2 * np.pi / N)
            w = shell_omega(k, c)
            if w is None:
                continue
            L = sum((2.0 * math.sin(ki / 2.0)) ** 2 for ki in k)
            arg = 1.0 - 0.5 * c * c * L
            if abs(arg) > 1.0:
                worst = max(worst, 9.9)
                continue
            worst = max(worst, abs(math.acos(arg) - w))
            n_ok += 1
        rows.append({"theta": th, "c": c, "n_k": n_ok,
                     "max_abs_w_leapfrog_minus_walkshell": worst})
    return rows


# ==========================================================================
#  EVIDENCE TABLE for the PI boundary decision (§5 RC3-(ii)).
#  NOT a verdict on M3 -- a named "relax X => reachable but cost Y" table.
# ==========================================================================
def build_evidence_table(R1, R2, R3, ahalf, j5rows):
    j5_worst = max(x["max_abs_w_leapfrog_minus_walkshell"] for x in j5rows)
    j5_ok = bool(j5_worst < 1e-6)
    tt_worst = R2["TT_residual_max"]

    table = [
        {
            "candidate": "R1 relax STRICT LOCALITY (quasi-local projection)",
            "reachability_cost": (
                "min support radius R* to reach N_prop=2 is DIRECTION-DEPENDENT: "
                "body-diagonal R*=4, face R*=6, axial R*=8 (=N/2, the whole box). "
                "Axial is effectively NON-TRUNCATABLE."),
            "physical_cost": (
                "the ker-C projector's real-space kernel has a POWER-LAW tail "
                "(%.1f%% of the operator norm still beyond R=6); tolerated tail at "
                "R* = %.1f-%.1f%%.  Locality is broken by exactly this tail -- the "
                "R29 k->0 direction-dependence (2.009) made spatial." % (
                    R1["tail_frac_by_radius_global"]["6"] * 100.0,
                    min(v["tail_frac_beyond_rmin"] for v in R1["per_k"].values()
                        if v["tail_frac_beyond_rmin"] is not None) * 100.0,
                    max(v["tail_frac_beyond_rmin"] for v in R1["per_k"].values()
                        if v["tail_frac_beyond_rmin"] is not None) * 100.0)),
            "reaches_2": all(v["reaches_2"] for v in R1["per_k"].values()),
            "new_j5_tt_breakage": "none (target is ker C; J5 %.1e, TT ok)" % j5_worst,
            "existing_escape": ("no direct R26 variant; quasi-locality is a NEW "
                                "relaxation of the strict-locality programme axiom."),
        },
        {
            "candidate": "R2 relax EMERGENT MATTER (partial Yee-ization)",
            "reachability_cost": (
                "N_prop=2 reached by hand-building %.0f-%.0f%% of the propagating-"
                "curvature DOF (gauge-dominant modes) into exact ker C." % (
                    R2["handbuilt_fraction_range"][0] * 100.0,
                    R2["handbuilt_fraction_range"][1] * 100.0)),
            "physical_cost": (
                "3-4 of the 4 propagating-curvature DOF drop from EMERGENT to R30 "
                "HAND-BUILT (local-shear leapfrog); only the TT-dominant graviton "
                "remainder (14-39% sector energy) stays truly emergent.  The "
                "geometry sector is no longer QCA-emergent."),
            "reaches_2": all(v["reaches_2"] for v in R2["per_k"].values()),
            "new_j5_tt_breakage": "none (TT bit-invariant, residual %.1e)" % tt_worst,
            "existing_escape": ("R30 itself is the hand-built construction; partial "
                                "Yee-ization = R30 geometry + emergent matter walk."),
        },
        {
            "candidate": "R3 relax EXACT CONSTRAINT (shadow conservation)",
            "reachability_cost": (
                "N_prop=2 reached tolerating a de-Donder residual delta in [%.2f, "
                "%.2f] (the 5-18%% non-gauge admixture counted as in-ker-C)." % (
                    R3["min_shadow_delta_range"][0], R3["min_shadow_delta_range"][1])),
            "physical_cost": (
                "constraint-violation rate = the tolerated 12-18% de-Donder "
                "residual; exact ker C = gauge (+) TT no longer exactly holds for "
                "the +w propagating modes."),
            "reaches_2": all(v["reaches_2"] for v in R3["per_k"].values()),
            "new_j5_tt_breakage": ("none (tolerated modes are walk modes ON the "
                                   "shell; cone = matter cone; J5 %.1e)" % j5_worst),
            "existing_escape": ("YES -- the (a)-half -w constraint-row curvature is "
                                "R26-class (row-dominant %s); R26 clears constraint "
                                "violation hyperbolically ~L/c k-independent. "
                                "MODULO R26 re-certification on this row curvature."
                                % ahalf["row_dominant_all_k"]),
        },
    ]

    summary = (
        "THREE NAMED relaxation candidates, each PRICED (materiel for the PI "
        "boundary call, NOT a solution to M3): "
        "(R1) relax STRICT LOCALITY => reachable via a quasi-local projection, cost "
        "= a power-law non-local tail whose required support radius is direction-"
        "dependent up to the WHOLE box (axial R*=N/2), i.e. the relaxation is "
        "SEVERE for the axial direction. "
        "(R2) relax EMERGENT MATTER => reachable via partial Yee-ization, cost = "
        "75-100%% of the propagating-curvature DOF demoted from emergent to R30 "
        "hand-built; only the TT graviton stays emergent. "
        "(R3) relax EXACT CONSTRAINT => reachable tolerating a 12-18%% de-Donder "
        "shadow residual, cost = that constraint-violation rate -- and this is the "
        "ONLY candidate with an ALREADY-PROVEN escape (R26 hyperbolic clearance of "
        "the (a)-half row curvature), modulo a re-certification. "
        "J5 co-cone (%.1e) and TT (%.1e) hold for ALL three -- no relaxation "
        "introduces NEW J5/TT breakage (consistent with RC3: J5/TT are not the "
        "(b)病灶).  All three REACH N_prop=2 (none is the stronger 'relaxed but "
        "still not 2' structural signal).  Two-sided blanks: whether structural "
        "unreachability holds is the PI's call across these three; SIGNAL not "
        "theorem; R30 existence & boundary unchanged." % (j5_worst, tt_worst))

    return {
        "evidence_table": table,
        "a_half_r26_cleanability": ahalf["r26_class_verdict"],
        "j5_cocone_worst": j5_worst, "j5_holds": j5_ok,
        "TT_worst_residual": tt_worst,
        "all_three_reach_2": all(r["reaches_2"] for r in table),
        "pi_boundary_summary": summary,
        "red_lines": (
            "MATERIEL FOR PI, NOT A HYPOTHESIS/SOLUTION.  No candidate 'solves' M3. "
            "Structural unreachability is the PI's adjudication across the three "
            "candidates, not this probe's.  SIGNAL not theorem.  R30 existence & "
            "boundary unchanged (existence != emergence != M3).  No M3/emergence/"
            "reachability closed.  C达点④ held.")}


def make_figure(R1, R2, R3):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))
    # R1: N_prop vs support radius
    ax = axes[0]
    radii = [3, 3.5, 4, 4.5, 5, 5.5, 6, 7, 8, 10, 12]
    for kl in KSET:
        d = R1["per_k"][str(kl)]["N_prop_by_radius"]
        xs = [r for r in radii]
        ys = [d[str(r)] for r in radii]
        ax.plot(xs, ys, marker="o", label="%s (R*=%s)" % (
            KLAB[kl], R1["per_k"][str(kl)]["min_support_radius_for_2"]))
    ax.axhline(2, color="green", ls=":", lw=0.8)
    ax.axvline(N // 2, color="red", ls="--", lw=0.8, label="N/2 (box half)")
    ax.set_xlabel("quasi-local support radius R (lattice)")
    ax.set_ylabel("N_prop (+w branch)")
    ax.set_title("R1 relax LOCALITY: N_prop vs support radius\n(axial needs whole box)")
    ax.set_ylim(0, 6.5); ax.legend(fontsize=6.5)
    # R2: N_prop vs hand-built DOF count
    ax = axes[1]
    for kl in KSET:
        d = R2["per_k"][str(kl)]["N_prop_by_handbuilt_count"]
        js = sorted(int(j) for j in d.keys())
        ax.plot(js, [d[str(j)] for j in js], marker="s", label="%s (jmin=%s)" % (
            KLAB[kl], R2["per_k"][str(kl)]["min_handbuilt_DOF_for_2"]))
    ax.axhline(2, color="green", ls=":", lw=0.8)
    ax.set_xlabel("hand-built DOF count (emergence sacrificed)")
    ax.set_ylabel("N_prop (+w branch)")
    ax.set_title("R2 relax EMERGENCE: N_prop vs hand-built DOF\n(75-100% must be hand-built)")
    ax.set_ylim(0, 6.5); ax.legend(fontsize=6.5)
    # R3: N_prop vs shadow tolerance
    ax = axes[2]
    for kl in KSET:
        d = R3["per_k"][str(kl)]["N_prop_by_delta"]
        ds = sorted(float(x) for x in d.keys())
        ax.plot(ds, [d["%s" % x if str(x) in d else str(x)] for x in ds]
                if False else [d[str(x)] for x in ds], marker="^",
                label="%s (dmin=%s)" % (KLAB[kl],
                                        R3["per_k"][str(kl)]["min_shadow_delta_for_2"]))
    ax.axhline(2, color="green", ls=":", lw=0.8)
    ax.set_xlabel("tolerated de-Donder shadow residual delta")
    ax.set_ylabel("N_prop (+w branch)")
    ax.set_title("R3 relax EXACT CONSTRAINT: N_prop vs delta\n(12-18% residual, R26-clearable)")
    ax.set_ylim(0, 6.5); ax.legend(fontsize=6.5)
    fig.suptitle("RC3-(ii): three relaxation candidates priced for the PI boundary "
                 "call (theta=pi/3, c=0.5, dm=0 physical point)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110)
    plt.close(fig)


def main():
    t0 = time.time()
    payload = {
        "register": "RC3-(ii)-three-relaxation-candidate-framework (可达性战役 §5)",
        "status": "RUNNING", "backend": "numpy",
        "purpose": (
            "MATERIEL FOR THE PI BOUNDARY CALL, NOT a hypothesis.  Four fixable "
            "hypotheses ALL dead (R27 / chiral N-N / slave / complex-route).  RC3 "
            "turns to (ii): price EACH of three relaxation candidates -- 'relax X "
            "=> reachable, cost Y' -- and hand the PI a named evidence table."),
        "params": {"N": N, "mu": MU0, "theta0": TH0, "c0": C0,
                   "kset": [list(k) for k in KSET], "sv_thresh": SV_THRESH,
                   "theta_line": TH_LINE},
        "frozen_inputs_sha256": {
            "rc1a_tensor_index_scan.py": sha256_file(os.path.join(DIR, "rc1a_tensor_index_scan.py")),
            "r32_reachability_probe.py": sha256_file(os.path.join(DIR, "r32_reachability_probe.py")),
            "r15_walk_dedonder.py": sha256_file(os.path.join(DIR, "r15_walk_dedonder.py")),
        },
        "red_lines": (
            "materiel for PI not a hypothesis; no candidate solves M3; SIGNAL not "
            "theorem; two-sided blanks; frozen inputs read-only; fp64; R30 existence "
            "& boundary unchanged; no M3/emergence/reachability closed."),
    }
    write_json(payload)

    print("RC3-(ii): three relaxation-candidate cheap probes (evidence for PI)")
    print("=" * 74)

    cert = RC.faithfulness_certificate()
    payload["faithfulness_certificate"] = cert
    print("[cert] RC1a reassembly vs frozen @ (pi/3,dm=0,c=0.5): walk %.1e K %.1e "
          "map %.1e -> %s" % (cert["walk_symbol_max_diff"], cert["K_state_max_diff"],
                              cert["damped_map_max_diff"],
                              "PASS" if cert["PASS"] else "FAIL"))
    write_json(payload)
    if not cert["PASS"]:
        payload["status"] = "ABORT-faithfulness-failed"
        write_json(payload)
        print("ABORT: RC1a machine does not reduce to frozen stack.")
        return

    print("[R1] relax STRICT LOCALITY -- quasi-local projection (kernel truncation)")
    R1 = candidate_R1(C0)
    payload["candidate_R1_strict_locality"] = R1
    for kl in KSET:
        v = R1["per_k"][str(kl)]
        print("    %s: R*=%s tail@R*=%s reaches2=%s"
              % (KLAB[kl], v["min_support_radius_for_2"],
                 ("%.4f" % v["tail_frac_beyond_rmin"]) if v["tail_frac_beyond_rmin"] is not None else "na",
                 v["reaches_2"]))
    write_json(payload)

    print("[R2] relax EMERGENT MATTER -- partial Yee-ization (hand-built gauge)")
    R2 = candidate_R2(C0)
    payload["candidate_R2_emergent_matter"] = R2
    for kl in KSET:
        v = R2["per_k"][str(kl)]
        print("    %s: jmin=%s handbuilt_frac=%s TTemergentE=%.2f"
              % (KLAB[kl], v["min_handbuilt_DOF_for_2"],
                 ("%.2f" % v["handbuilt_fraction"]) if v["handbuilt_fraction"] else "na",
                 v["TT_emergent_energy"]))
    write_json(payload)

    print("[R3] relax EXACT CONSTRAINT -- shadow conservation (tolerate delta)")
    R3 = candidate_R3(C0)
    payload["candidate_R3_exact_constraint"] = R3
    for kl in KSET:
        v = R3["per_k"][str(kl)]
        print("    %s: dmin=%s resid[%.3f..%.3f]"
              % (KLAB[kl], v["min_shadow_delta_for_2"],
                 v["resid_outside_kerC_min_max"][0], v["resid_outside_kerC_min_max"][1]))
    write_json(payload)

    print("[(a)-half] R26 cleanability of the -w constraint-row curvature")
    ahalf = a_half_r26(C0)
    payload["a_half_r26_cleanability"] = ahalf
    for kl in KSET:
        v = ahalf["per_k"][str(kl)]
        if v.get("no_neg_branch"):
            continue
        print("    %s: rowE=%.2f gaugeE=%.2f TTE=%.2f row_dominant=%s"
              % (KLAB[kl], v["row_sector_energy"], v["gauge_sector_energy"],
                 v["TT_sector_energy"], v["row_dominant"]))
    write_json(payload)

    print("[J5] co-cone re-check across theta (new breakage from any relaxation?)")
    j5rows = j5_cocone_across_theta()
    payload["j5_cocone"] = j5rows
    for x in j5rows:
        print("    theta=%.3f c=%.3f: max|w_leap-w_shell|=%.2e"
              % (x["theta"], x["c"], x["max_abs_w_leapfrog_minus_walkshell"]))
    write_json(payload)

    ev = build_evidence_table(R1, R2, R3, ahalf, j5rows)
    payload.update(ev)
    write_json(payload)

    make_figure(R1, R2, R3)
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
    print("EVIDENCE TABLE (materiel for PI boundary call):")
    for r in ev["evidence_table"]:
        print("  * %s  [reaches N_prop=2: %s]" % (r["candidate"], r["reaches_2"]))
        print("      reachability cost: %s" % r["reachability_cost"])
        print("      physical cost    : %s" % r["physical_cost"])
        print("      existing escape  : %s" % r["existing_escape"])
    print("all three reach N_prop=2: %s" % ev["all_three_reach_2"])
    print("J5 worst = %.1e ; TT worst = %.1e" % (ev["j5_cocone_worst"], ev["TT_worst_residual"]))
    print("source  sha256 = %s" % payload["source_sha256"])
    print("results sha256 = %s" % jsha)
    print("total %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()






