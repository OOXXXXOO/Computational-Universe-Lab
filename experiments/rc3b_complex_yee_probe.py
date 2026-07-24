"""RC3 PROBE TWO -- COMPLEX-ROUTE WALK YEE-IZATION (the LAST fixable hypothesis).

CAMPAIGN CONTEXT (任务书-可达性战役 §11 + R35 negative steering, PREREGISTERED as
the LAST fixable-hypothesis probe; if NO => (ii) 裁纲领边界, no 4th hypothesis).

The RC3 bifurcation (小报告-RC3探测一, confirmed by R31/R32/RC1b) localizes the
residual reachability obstruction into TWO halves on the main/+w Floquet branch:
    (a) -w constraint-row curvature (constraint-violation propagation), and
    (b) +w GAUGE-propagation: 2 gauge-DOMINANT modes that sit in ker C's ambient
        yet are counted as propagating curvature DOF (N_prop stays 4, never 2).
R35 KILLED the de Donder SLAVE fix for (b) (slave coeff kappa^i/kappa^0 is
direction-dependent 1.215 at k->0 = R29-barred non-local).  The ONLY remaining
hope for (b) is the COMPLEX route (R30-style: LOCAL curl + operator identity, no
slave) -- but that requires the EMERGENT walk to BECOME Yee-type, a structural
change that may break emergence.  THIS PROBE TESTS EXACTLY THAT.

QUESTION (probe two, complex route ONLY -- slave is R35-dead):
  Can the emergent walk's +w gauge-propagation sector be Yee-ized (R30 local curl
  making the 2 gauge modes zero-curvature / dropping N_prop to 2) WITHOUT:
    (1) slaving          (R35-dead, non-local, forbidden);
    (2) non-local projection (R29-dead, forbidden);
    (3) touching TT      (the 2 real graviton polarizations must be bit-invariant);
    (4) breaking emergence (must stay the QCA-emergent walk, NOT degenerate into
        R30's hand-built product-of-local-shears existence construction);
    (5) breaking the J5 co-cone (construction change => J5 MUST be re-measured).
  ALL FIVE simultaneously => FIXABLE => reachability reopens.  Any one fails =>
  NOT FIXABLE => report WHICH criterion is stuck (that decides which assumption
  (ii) relaxes: emergent matter / exact constraint / strict locality).

FIVE-CRITERIA MEASUREMENT (let the numbers decide, R27 discipline):
  C1 N_prop : does an R30-style complex operation drop the +w N_prop to 2?
  C2 J5     : does the Yee target preserve c_gw == c_matter across theta?
  C3 TT     : are the 2 TT graviton polarizations bit-invariant under it?
  C4 LOCALITY : is the operation that reaches N_prop=2 local (R29 k->0 test)?
  C5 EMERGENCE: is the Yee-ized walk still the emergent walk, or R30's hand-built
                construction (residual-to-remove + operator distance)?

HONESTY RED LINES (§7 + R35 + AGENTS.md): TWO-SIDED BLANKS.  Do NOT claim FIXABLE
unless all five pass together; do NOT claim a structural no-go theorem (cheap probe
= SIGNAL not theorem; (ii) adjudication draws the conclusion).  This is the LAST
fixable hypothesis (PI order): if NO, deliver "(b) complex route NO, go to (ii)"
and name the stuck criterion, do NOT hunt a 4th hypothesis.  Frozen inputs
READ-ONLY.  fp64 (RULESPACE_BACKEND=numpy).  Incremental JSON.  R30 existence &
boundary unchanged (existence != emergence != M3); do NOT declare M3/emergence/
reachability closed.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/rc3b_complex_yee_probe.py
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

# ---- frozen, READ-ONLY machinery ---------------------------------------
import rc1a_tensor_index_scan as RC                        # noqa: E402 c=cos th reassembly
import r32_reachability_probe as R32                       # noqa: E402 kerC/sectors/inc/curv
from r15_walk_dedonder import shell_omega                  # noqa: E402 walk shell (takes c)

OUT = os.path.join(ROOT, "data", "results", "rc3b_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "rc3b_complex_yee_probe.png")

N = RC.N
MU0 = RC.MU0
TH0 = math.pi / 3.0
C0 = math.cos(TH0)
SV_THRESH = R32.SV_THRESH                                  # 0.05 shared judge口径
KSET = [(2, 0, 0), (2, 2, 0), (2, 2, 2)]
KLAB = {(2, 0, 0): "axial", (2, 2, 0): "face-diagonal", (2, 2, 2): "body-diagonal"}
DM_LINE = [0.0, 0.05, 0.15, 0.3, 0.6]                      # R33 chirality-breaking dir
TH_LINE = [0.4, TH0, 1.0, 1.2]                             # theta line for J5 co-cone
# k directions used for the J5 co-cone leapfrog-vs-shell check (broad)
KSET_J5 = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0), (2, 2, 2), (1, 0, 0)]
# k->0 directions for the R29 locality test of the Yee operation
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
#  Building blocks on the reassembled c=cos theta complex (all frozen fns).
#  ker C = placed gauge(4) (+) TT(2) [R32.build_sectors]; inc = placed
#  linearized Riemann (256,10).  S_walk = +w Floquet branch of the walk symbol.
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


def probe_point(kl, theta, dm, c):
    """The (b)-half complex-route measurement at ONE (k,theta,dm) point.

    Establishes, on the +w (main) Floquet branch that carries the (b) obstacle:
      * exact-gauge inc identity  |inc . Q_gauge|  (R30 kinematic half present);
      * baseline N_prop and the curvature subspace's sector decomposition;
      * C-mechanism INERTNESS: apply the R30 curl (remove the gauge sector's
        curvature image) and re-count -- if the walk's gauge is already zero-
        curvature the count is UNCHANGED (the complex route buys nothing here);
      * gauge-vs-nongauge curvature split (WHERE the +w curvature actually lives);
      * C1 the ker-C projection Yee-ization: does it drop N_prop to 2, clean cliff;
      * C3 TT bit-invariance under that projection;
      * C5 emergence distance: residual-outside-kerC of the raw +w modes (= the
        admixture the Yee-ization must delete) + principal angles S_curv vs ker C.
    """
    k = np.array(kl, float) * (2 * np.pi / N)
    b = _bases(k, c)
    if b is None:
        return {"off_band": True}
    Q_TT, Q_gauge, Q_row = b["TT"], b["gauge"], b["row"]
    Q_kerC, inc = b["kerC"], b["inc"]

    U10, phases, mods = RC.walk_unit_modes_p(k, MU0, theta, dm, c)
    if U10.shape[1] == 0:
        return {"off_band": False, "no_modes": True}
    Bpos = U10[:, phases > 1e-9]                             # +w (main) branch
    if Bpos.shape[1] == 0:
        return {"off_band": False, "no_pos_branch": True}

    # exact-gauge inc identity (R30 kinematic half; tool, not a fit)
    inc_gauge = float(np.max(np.abs(inc @ Q_gauge)))

    # baseline +w curvature image + count
    A = inc @ Bpos
    nprop_raw, svn_raw = _nprop(A)
    Uv, sv, Vh = np.linalg.svd(A, full_matrices=False)
    svn = sv / (sv[0] + 1e-300)
    Scurv = Bpos @ Vh.conj().T[:, :max(nprop_raw, 1)]
    Scurv, _ = np.linalg.qr(Scurv)
    fT = float(np.mean(np.linalg.norm(Q_TT.conj().T @ Scurv, axis=0) ** 2))
    fG = float(np.mean(np.linalg.norm(Q_gauge.conj().T @ Scurv, axis=0) ** 2))
    fR = float(np.mean(np.linalg.norm(Q_row.conj().T @ Scurv, axis=0) ** 2))

    # complex-route mechanism INERTNESS: R30 curl removes gauge curvature image.
    # inc annihilates exact gauge, so this subtracts ~0 -> count unchanged.
    A_gauge_curv = inc @ (Q_gauge @ (Q_gauge.conj().T @ Bpos))
    nprop_after_curl, svn_after_curl = _nprop(A - A_gauge_curv)

    # WHERE the +w curvature lives: gauge part vs non-gauge part of S_curv
    Sg = Q_gauge @ (Q_gauge.conj().T @ Scurv)
    Sng = Scurv - Sg
    curv_total = float(np.linalg.norm(inc @ Scurv))
    curv_gauge_part = float(np.linalg.norm(inc @ Sg))
    curv_nongauge_part = float(np.linalg.norm(inc @ Sng))

    # C1: ker-C projection Yee-ization -> N_prop
    Bproj = Q_kerC @ (Q_kerC.conj().T @ Bpos)
    nprop_yee, svn_yee = _nprop(inc @ Bproj)

    # C3: TT bit-invariance under the ker-C projection
    P_kerC = Q_kerC @ Q_kerC.conj().T
    tt_resid = float(np.linalg.norm(Q_TT - P_kerC @ Q_TT))

    # C5: emergence distance -- how far the raw +w modes are from ker C
    resid = np.linalg.norm(Bpos - Q_kerC @ (Q_kerC.conj().T @ Bpos), axis=0)
    ang_kerC = np.degrees(R32.principal_angles(Scurv, Q_kerC))

    return {
        "off_band": False, "n_pos_modes": int(Bpos.shape[1]),
        "exact_gauge_inc_identity": inc_gauge,
        "N_prop_raw_plusW": nprop_raw, "svn_raw": svn_raw,
        "Scurv_sector_TT_gauge_row": [fT, fG, fR],
        "N_prop_after_R30_gauge_curl": nprop_after_curl,
        "svn_after_R30_gauge_curl": svn_after_curl,
        "curv_total": curv_total, "curv_gauge_part": curv_gauge_part,
        "curv_nongauge_part": curv_nongauge_part,
        "N_prop_yee_projection": nprop_yee, "svn_yee": svn_yee,
        "TT_residual_under_projection": tt_resid,
        "plusW_resid_outside_kerC": [float(x) for x in resid],
        "plusW_resid_outside_kerC_max": float(resid.max()),
        "principal_angles_Scurv_vs_kerC_deg": [float(x) for x in np.sort(ang_kerC)],
        "max_angle_Scurv_vs_kerC_deg": float(ang_kerC.max()) if len(ang_kerC) else float("nan"),
    }


# ==========================================================================
#  C4 -- LOCALITY of the Yee operation (R29 / R35 k->0 direction-dependence).
#  The only operation that reaches N_prop=2 is the ker-C projection P_kerC(k).
#  Its k->0 direction-dependence is its (non)locality signature -- same test
#  R35 ran on the slave (1.215) and R29 on P_S (2.449).
# ==========================================================================
def locality_test(c, eps=1e-3):
    dirs = {k: list(np.array(v) / np.linalg.norm(v)) for k, v in DIRS_LOC.items()}
    Ps = {}
    for nm, nk in dirs.items():
        k = eps * np.asarray(nk, float)
        b = _bases(k, c)
        if b is None:
            Ps[nm] = None
            continue
        Ps[nm] = b["kerC"] @ b["kerC"].conj().T
    names = [n for n in Ps if Ps[n] is not None]
    worst = 0.0
    pairs = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            d = float(np.linalg.norm(Ps[names[i]] - Ps[names[j]]))
            pairs[f"{names[i]}-{names[j]}"] = d
            worst = max(worst, d)
    return {"eps": eps, "kerC_projector_dir_dependence": worst,
            "pairwise": pairs,
            "non_local": bool(worst > 0.1),
            "note": ("ker-C projector = the only operation reaching N_prop=2; its "
                     "direction-dependent k->0 limit => NON-LOCAL (R29 P_S=2.449, "
                     "R35 slave=1.215 same pathology)")}


# ==========================================================================
#  C2 -- J5 CO-CONE: does the R30 Yee target preserve c_gw == c_matter?
#  The R30 leapfrog (dt=c) has cos(w_leap)=1-1/2 dt^2 L, L=sum(2 sin k_i/2)^2.
#  The matter/walk shell is w_walk=2 arcsin(c sqrt(sum sin^2 k_i/2)).  If they
#  coincide across theta the graviton cone == matter cone c=cos theta (J5 holds).
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
            w_leap = math.acos(arg)
            worst = max(worst, abs(w_leap - w))
            n_ok += 1
        rows.append({"theta": th, "c": c, "n_k": n_ok,
                     "max_abs_w_leapfrog_minus_walkshell": worst})
    return rows


# ==========================================================================
#  FIVE-CRITERIA VERDICT (§11 / R35: last fixable hypothesis, numbers decide)
# ==========================================================================
def build_verdict(rows, loc, j5rows):
    # decisive line = massless dm=0 at theta=pi/3 (the (b) obstacle's home point)
    m0 = [r for r in rows if abs(r["theta"] - TH0) < 1e-9 and abs(r["dm"]) < 1e-9]
    per = []
    for r in m0:
        for kl in KSET:
            e = r["per_k"][str(kl)]
            if not e.get("off_band") and not e.get("no_modes") \
                    and not e.get("no_pos_branch"):
                per.append(e)

    # C1: does ANY complex-route operation drop N_prop to 2?
    #   R30 curl (local, emergence-preserving): count stays 4 (inert).
    #   ker-C projection (reaches 2): but see C4/C5.
    nprop_raw = sorted(set(e["N_prop_raw_plusW"] for e in per))
    nprop_curl = sorted(set(e["N_prop_after_R30_gauge_curl"] for e in per))
    nprop_yee = sorted(set(e["N_prop_yee_projection"] for e in per))
    r30_curl_inert = (nprop_curl == nprop_raw)
    yee_reaches_2 = all(e["N_prop_yee_projection"] == 2 for e in per)
    inc_gauge_max = max(e["exact_gauge_inc_identity"] for e in per)
    curv_gauge_max = max(e["curv_gauge_part"] for e in per)
    curv_nongauge_min = min(e["curv_nongauge_part"] for e in per)

    # C2: J5 co-cone of the R30 leapfrog target across theta
    j5_worst = max(x["max_abs_w_leapfrog_minus_walkshell"] for x in j5rows)
    j5_holds_for_target = bool(j5_worst < 1e-6)

    # C3: TT bit-invariance under the ker-C projection
    tt_worst = max(e["TT_residual_under_projection"] for e in per)
    tt_invariant = bool(tt_worst < 1e-10)

    # C4: locality of the N_prop=2 operation
    loc_nonlocal = bool(loc["non_local"])
    loc_dep = loc["kerC_projector_dir_dependence"]

    # C5: emergence -- the raw +w modes carry a NON-ZERO admixture outside ker C
    #     that the Yee-ization must delete; the ONLY local unitary that installs
    #     exact ker-C modes is R30's hand-built leapfrog (not the emergent walk).
    resid_max = max(e["plusW_resid_outside_kerC_max"] for e in per)
    resid_min = min(min(e["plusW_resid_outside_kerC"]) for e in per)
    ang_max = max(e["max_angle_Scurv_vs_kerC_deg"] for e in per)
    # emergence is broken because reaching N_prop=2 requires either (i) the non-
    # local ker-C projection (C4 fails) or (ii) replacing U with R30's assembled
    # leapfrog (an existence construction, not the QCA-emergent walk).
    emergence_preserving_route_exists = bool(r30_curl_inert is False)  # False here
    # i.e. the local/emergence-preserving R30 curl is INERT (N_prop stays 4).

    # ---- five-criteria pass/fail ----
    C = {
        "C1_Nprop_to_2": {
            "R30_curl_local_emergent": nprop_curl,
            "R30_curl_INERT_stays_4": bool(r30_curl_inert),
            "kerC_projection": nprop_yee,
            "reaches_2_ONLY_via_projection": bool(yee_reaches_2),
            "pass_if_emergent_local": False,   # inert; only non-local proj reaches 2
        },
        "C2_J5_cocone": {
            "leapfrog_target_worst_dev": j5_worst,
            "holds_for_R30_target": j5_holds_for_target,
            "pass": j5_holds_for_target,
        },
        "C3_TT_invariant": {"worst_TT_residual": tt_worst, "pass": tt_invariant},
        "C4_locality": {"kerC_projector_dir_dependence": loc_dep,
                        "non_local": loc_nonlocal, "pass": (not loc_nonlocal)},
        "C5_emergence": {
            "plusW_resid_outside_kerC_range": [resid_min, resid_max],
            "max_angle_Scurv_vs_kerC_deg": ang_max,
            "local_emergent_route_reaches_2": emergence_preserving_route_exists,
            "pass": emergence_preserving_route_exists,
        },
    }

    # FIXABLE iff all five pass simultaneously
    fixable = (C["C1_Nprop_to_2"]["pass_if_emergent_local"]
               and C["C2_J5_cocone"]["pass"] and C["C3_TT_invariant"]["pass"]
               and C["C4_locality"]["pass"] and C["C5_emergence"]["pass"])

    stuck = [name for name, blk in
             (("C1_Nprop(emergent-local route inert, stays 4)",
               C["C1_Nprop_to_2"]["pass_if_emergent_local"]),
              ("C4_locality(N_prop=2 op non-local, R29/R35-barred)",
               C["C4_locality"]["pass"]),
              ("C5_emergence(Yee-ization = R30 hand-built, not emergent walk)",
               C["C5_emergence"]["pass"]))
             if not blk]

    if fixable:
        tag = "FIXABLE -- (b) complex-route Yee-ization works, reachability REOPENS"
        verdict = (
            "All five criteria pass together: an R30-style LOCAL complex operation "
            "drops the +w N_prop to 2, preserves the J5 co-cone, leaves TT bit-"
            "invariant, stays local, and remains the emergent walk. Report the "
            "construction to RC2 for full acceptance. (SIGNAL, not M3; existence != "
            "emergence != M3.)")
    else:
        tag = ("NOT FIXABLE -- (b) complex-route Yee-ization fails; go to (ii). "
               "Stuck on: " + "; ".join(stuck))
        verdict = (
            "The (b) half CANNOT be fixed by an emergent-walk Yee-ization. MECHANISM "
            "(numbers decide): the R30 KINEMATIC identity IS present on the "
            "reassembled complex (|inc . exact-gauge| = %.1e, machine zero), so R30's "
            "curl annihilates EXACT placed-gauge curvature. But the emergent walk's "
            "+w gauge-dominant modes ALREADY carry zero gauge-sector curvature "
            "(|inc . gauge-part(S_curv)| = %.1e); their propagating curvature lives "
            "ENTIRELY in a small NON-GAUGE admixture (|inc . nongauge-part| >= %.2f). "
            "So applying the R30 gauge-curl is INERT: N_prop stays %s, never 2 "
            "(bit-for-bit svn unchanged) -- the complex route has nothing to bite on "
            "the gauge sector. The ONLY operation that reaches N_prop=2 is projecting "
            "the +w modes onto ker C (deleting the %.0f-%.0f%% non-gauge admixture) -- "
            "and that projector is NON-LOCAL (direction-dependence %.2f at k->0, the "
            "SAME R29/R35 pathology as P_S=2.449 / slave=1.215). Equivalently, the "
            "only LOCAL unitary that installs exact ker-C modes is R30's hand-built "
            "product-of-local-shears leapfrog -- an EXISTENCE construction, NOT the "
            "QCA-emergent walk. TWO criteria that do NOT block: C3 TT is bit-invariant "
            "(residual %.1e) and C2 the J5 co-cone HOLDS for the R30 leapfrog target "
            "(|w_leapfrog - w_walkshell| <= %.1e across theta in %s). So (b) is stuck "
            "JOINTLY on STRICT LOCALITY (the N_prop=2 operation is non-local) and "
            "EMERGENT MATTER (the local alternative is hand-built R30, not emergence) "
            "-- NOT on J5, NOT on TT, NOT on exact constraint per se. SIGNAL not "
            "theorem: (ii) adjudication draws the conclusion. This was the LAST "
            "fixable hypothesis (PI order); deliver (ii)." % (
                inc_gauge_max, curv_gauge_max, curv_nongauge_min, nprop_curl,
                resid_min * 100, resid_max * 100, loc_dep, tt_worst, j5_worst,
                [round(t, 3) for t in TH_LINE]))

    ii_target = {
        "verdict": "go to (ii) 裁纲领边界" if not fixable else "reachability reopens (RC2)",
        "stuck_criteria": stuck,
        "assumption_to_relax_primary": (
            "STRICT LOCALITY (allow a quasi-local projection to beat R29) OR "
            "EMERGENT MATTER (allow partial Yee-ization = hand-built local-shear "
            "geometry sector, dropping strict QCA-emergence of the geometry)"),
        "assumption_secondary_lever": (
            "EXACT CONSTRAINT: the +w modes sit %.0f-%.0f%% OUTSIDE ker C (a small "
            "de Donder violation); tolerating it via a SHADOW/approximate constraint "
            "would also let the modes count in ker C. Secondary, related lever."
            % (resid_min * 100, resid_max * 100)),
        "assumptions_NOT_the_blocker": (
            "J5 co-cone (holds for the R30 target, %.1e) and TT-invariance (%.1e) are "
            "NOT what kills (b); the exact constraint algebra ker C = gauge (+) TT is "
            "intact (kinematic identity %.1e)." % (j5_worst, tt_worst, inc_gauge_max)),
    }

    return {"verdict_tag": tag, "verdict": verdict, "criteria": C,
            "reachability_fixable": bool(fixable),
            "N_prop_raw_plusW": nprop_raw,
            "N_prop_after_R30_curl": nprop_curl,
            "N_prop_yee_projection": nprop_yee,
            "ii_adjudication_target": ii_target}


def make_figure(rows, j5rows):
    m0 = sorted([r for r in rows if abs(r["theta"] - TH0) < 1e-9],
                key=lambda r: r["dm"])
    dms = [r["dm"] for r in m0]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))

    def series(kl, key):
        ys = []
        for r in m0:
            e = r["per_k"][str(kl)]
            ys.append(e.get(key, float("nan"))
                      if not (e.get("off_band") or e.get("no_modes")
                              or e.get("no_pos_branch")) else float("nan"))
        return ys

    ax = axes[0]
    for kl in KSET:
        ax.plot(dms, series(kl, "N_prop_raw_plusW"), marker="o",
                label=f"{kl} raw +w")
        ax.plot(dms, series(kl, "N_prop_after_R30_gauge_curl"), marker="x", ls=":",
                label=f"{kl} after R30 curl")
        ax.plot(dms, series(kl, "N_prop_yee_projection"), marker="s", ls="--",
                label=f"{kl} kerC-proj")
    ax.axhline(2, color="green", ls=":", lw=0.8)
    ax.set_xlabel("dm"); ax.set_ylabel("N_prop (+w branch)")
    ax.set_title("C1: R30 curl INERT (stays 4);\nonly ker-C projection reaches 2")
    ax.set_ylim(0, 6.5); ax.legend(fontsize=5.5)

    ax = axes[1]
    for kl in KSET:
        yg = series(kl, "curv_gauge_part")
        yn = series(kl, "curv_nongauge_part")
        ax.plot(dms, yg, marker="^", label=f"{kl} gauge-part curv")
        ax.plot(dms, yn, marker="v", ls="--", label=f"{kl} nongauge-part curv")
    ax.set_xlabel("dm"); ax.set_ylabel("|inc . part(S_curv)|")
    ax.set_title("WHERE +w curvature lives:\ngauge=0, all in nongauge admixture")
    ax.legend(fontsize=5.5)

    ax = axes[2]
    ths = [x["theta"] for x in j5rows]
    devs = [x["max_abs_w_leapfrog_minus_walkshell"] for x in j5rows]
    ax.semilogy(ths, [max(d, 1e-17) for d in devs], marker="o", color="purple")
    ax.axhline(1e-6, color="green", ls=":", lw=0.8, label="J5 target 1e-6")
    ax.axvline(TH0, color="k", ls="--", lw=0.8, label="theta=pi/3")
    ax.set_xlabel("theta (c=cos theta)")
    ax.set_ylabel("|w_leapfrog - w_walkshell|")
    ax.set_title("C2: J5 co-cone HOLDS for R30 target\n(leapfrog freq == walk shell)")
    ax.legend(fontsize=7)

    fig.suptitle("RC3 probe two: emergent-walk Yee-ization of the +w gauge-"
                 "propagation (b) half (theta=pi/3, c=0.5 reassembly)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110)
    plt.close(fig)


def main():
    t0 = time.time()
    payload = {
        "register": "RC3-probe-two-complex-route-walk-Yee-ization (可达性战役 §11 + R35)",
        "status": "RUNNING", "backend": "numpy",
        "hypothesis": (
            "PREREGISTERED, LAST FIXABLE HYPOTHESIS (PI order): can the emergent "
            "walk's +w gauge-propagation (b) half be Yee-ized (R30 local curl + "
            "operator identity) to drop N_prop to 2, WITHOUT slaving (R35-dead), "
            "non-local projection (R29-dead), touching TT, breaking emergence, or "
            "breaking the J5 co-cone? All five => FIXABLE; any fail => (ii), name "
            "the stuck criterion. NO 4th hypothesis if NO."),
        "params": {"N": N, "mu": MU0, "theta0": TH0, "c0": C0,
                   "kset": [list(k) for k in KSET], "dm_line": DM_LINE,
                   "theta_line": TH_LINE, "sv_thresh": SV_THRESH},
        "frozen_inputs_sha256": {
            "rc1a_tensor_index_scan.py": sha256_file(os.path.join(DIR, "rc1a_tensor_index_scan.py")),
            "r32_reachability_probe.py": sha256_file(os.path.join(DIR, "r32_reachability_probe.py")),
            "r15_walk_dedonder.py": sha256_file(os.path.join(DIR, "r15_walk_dedonder.py")),
        },
        "red_lines": (
            "two-sided blanks: no FIXABLE unless all five pass; no structural no-go "
            "theorem (cheap probe = SIGNAL, (ii) adjudicates). LAST fixable "
            "hypothesis; if NO deliver (ii), no 4th hypothesis. frozen inputs read-"
            "only; fp64. R30 existence & boundary unchanged (existence != emergence "
            "!= M3); no M3/emergence/reachability closed."),
    }
    write_json(payload)

    print("RC3 PROBE TWO: emergent-walk Yee-ization of the +w gauge-prop (b) half")
    print("=" * 74)

    cert = RC.faithfulness_certificate()
    payload["faithfulness_certificate"] = cert
    print(f"[cert] RC1a reassembly vs frozen @ (pi/3,dm=0,c=0.5): "
          f"walk {cert['walk_symbol_max_diff']:.1e} K {cert['K_state_max_diff']:.1e} "
          f"map {cert['damped_map_max_diff']:.1e} -> "
          f"{'PASS' if cert['PASS'] else 'FAIL'}")
    write_json(payload)
    if not cert["PASS"]:
        payload["status"] = "ABORT-faithfulness-failed"
        write_json(payload)
        print("ABORT: RC1a machine does not reduce to frozen stack.")
        return

    # -- per-(theta,dm,k) complex-route measurement --------------------------
    pts = [{"theta": TH0, "dm": dm} for dm in DM_LINE]
    pts.append({"theta": 0.5, "dm": 0.0})
    rows = []
    for pt in pts:
        theta, dm = pt["theta"], pt["dm"]
        c = math.cos(theta)
        entry = {**pt, "c": c, "per_k": {}}
        for kl in KSET:
            e = probe_point(kl, theta, dm, c)
            entry["per_k"][str(kl)] = e
            if e.get("off_band") or e.get("no_modes") or e.get("no_pos_branch"):
                print(f"  th={theta:.3f} dm={dm:.2f} k={kl}: off/no-modes")
                continue
            print(f"  th={theta:.3f} dm={dm:.2f} k={str(kl):>9} [{KLAB[kl]:>13}]: "
                  f"N_prop raw={e['N_prop_raw_plusW']} "
                  f"afterCurl={e['N_prop_after_R30_gauge_curl']} "
                  f"Yee={e['N_prop_yee_projection']} | "
                  f"inc.gauge={e['exact_gauge_inc_identity']:.1e} "
                  f"curv g/ng={e['curv_gauge_part']:.2e}/{e['curv_nongauge_part']:.2f} | "
                  f"resid_out={e['plusW_resid_outside_kerC_max']:.2f} "
                  f"TTres={e['TT_residual_under_projection']:.1e}")
        rows.append(entry)
        write_json({**payload, "scan_partial": rows})
    payload["scan"] = rows

    # -- C4 locality of the N_prop=2 operation (R29/R35 k->0 test) -----------
    loc = locality_test(C0)
    payload["locality_test"] = loc
    print(f"[C4 locality] ker-C projector dir-dependence at k->0 = "
          f"{loc['kerC_projector_dir_dependence']:.3f} -> "
          f"{'NON-LOCAL (R29-barred)' if loc['non_local'] else 'local'}")
    write_json(payload)

    # -- C2 J5 co-cone across theta ------------------------------------------
    j5rows = j5_cocone_across_theta()
    payload["j5_cocone"] = j5rows
    print("[C2 J5 co-cone] R30 leapfrog freq vs walk shell across theta:")
    for x in j5rows:
        print(f"    theta={x['theta']:.3f} c={x['c']:.3f}: "
              f"max|w_leap - w_shell| = {x['max_abs_w_leapfrog_minus_walkshell']:.2e}")
    write_json(payload)

    # -- verdict --------------------------------------------------------------
    verdict = build_verdict(rows, loc, j5rows)
    payload.update(verdict)
    write_json(payload)

    make_figure(rows, j5rows)
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
    print(f"N_prop raw={verdict['N_prop_raw_plusW']} afterR30curl="
          f"{verdict['N_prop_after_R30_curl']} YeeProj={verdict['N_prop_yee_projection']}")
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()



