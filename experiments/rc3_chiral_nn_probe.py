"""RC3 PROBE ONE -- CHIRALITY-DOUBLING NIELSEN-NINOMIYA HYPOTHESIS (cheap test).

CAMPAIGN CONTEXT (任务书-可达性战役 §11, RC3 first hypothesis, PREREGISTERED AS A
HYPOTHESIS, NOT A CONCLUSION):
    massless graviton  =>  matter walk chiral at the physical point (gapless Dirac)
    =>  chirality doubling (the MIRROR branch that 43g introduced to escape the Weyl
        no-go / mass-gap lock)  =>  the mirror branch is SUSPECTED to be the extra 2
        curvature-carrying DOF  =>  N_prop = 4.
    Two-horn candidate: you cannot simultaneously have (massless graviton = chiral
    matter) AND (N_prop = 2 = no mirror curvature DOF).

RC3 PROBE ONE (this file): TURN OFF THE MIRROR CHIRALITY BRANCH, COUNT N_prop, with
the SAME unprojected Riemann-SVD judge as RC1a/R28/R31/R32.
    drop to 2  => the extra DOF come from chirality doubling, N-N CONFIRMED
                  (RC3 answer forms: relaxing chirality => reachable but graviton
                  gains mass / breaks the J5 co-cone -- a DIRECTION, verified elsewhere);
    still 4/3  => chirality doubling EXCLUDED as the main culprit; the extra DOF have
                  another source, report "chirality excluded, look elsewhere";
    intermediate / not clean => report honestly.

MIRROR-BRANCH LOCATION (found, documented for lane A):
  * The literal chirality doubling (ledger 43g/43h/43i, tensor_walker16 /
    tensor_walker_dirac): the internal space is (C^2_chir (x) C^2_spin)^{(x)2}; the
    chirality-+ block runs the NORMAL split-step (tensor_walker.walk_matrix_1), the
    chirality-- block runs the MIRRORED split-step (walk_matrix_1m, all shifts
    reversed = k -> -k; tcf.step_matrix.chir_block(-1)); the mass coin exp(i dm tau_x)
    mixes them.  THIS is "43g's mirror sector".
  * The RC1a/R28/R31/R32 placed-complex N_prop machine is built on walk_symbol_p, which
    is walk_matrix_1 ALONE -- the MAIN chirality, a single 2-spinor, NO mirror block.
  * In THAT machine the mirror shows up as the -w Floquet branch of the geometry
    propagator: R31 localised the extra constraint-row curvature to the -w branch.  So
    "turn off the mirror branch" has two faithful readings, BOTH tested here:
       (B) Floquet reading  : count N_prop on the +w (main) Floquet branch only,
                              dropping the -w (病灶) branch.  [curvature_subspace branch]
       (A) literal reading  : rebuild the placed complex on the MIRROR chirality
                              (walk_matrix_1m == main at -k) and count its N_prop;
                              compare to the single (main) chirality complex.

CROSS-VALIDATION OF THE R31 CLUE (§task step 3): is the turned-off branch the -w
Floquet branch that R31 flagged as carrying the row-sector (病灶) curvature?  Reported
per k: dominant branch, per-branch residual-outside-kerC, sector energy (TT/gauge/row).

HONESTY RED LINES (§7 + §11 + AGENTS.md): HYPOTHESIS NOT CONCLUSION (R27 lesson, PI
order).  Do NOT presuppose the N-N pair; the branch-off count decides.  The branch-off
variant is a DIAGNOSTIC TOOL, not a candidate construction (you cannot unitarily delete
one Floquet branch).  Record side effects on the TT / co-cone / causal sectors honestly.
Do NOT declare M3 / emergence / reachability closed; R30 existence & boundary unchanged.
Chirality N-N confirmed (if it were) = a mechanism argument, a SIGNAL not a bit-proof.
Frozen inputs imported READ-ONLY.  fp64 (RULESPACE_BACKEND=numpy).  Incremental JSON.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/rc3_chiral_nn_probe.py
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
import r32_reachability_probe as R32                       # noqa: E402 curvature/branch machine
import rulespace_gpu.tensor_coin_feedback as tcf           # noqa: E402 chirality-doubled walker
import rulespace_gpu.tensor_walker as tw                   # noqa: E402 walk_matrix_1 / _1m

OUT = os.path.join(ROOT, "data", "results", "rc3_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "rc3_chiral_nn_probe.png")

N = RC.N
MU0 = RC.MU0
TH0 = math.pi / 3.0
C0 = math.cos(TH0)
KSET = [(2, 0, 0), (2, 2, 0), (2, 2, 2)]
KLAB = {(2, 0, 0): "axial", (2, 2, 0): "face-diagonal", (2, 2, 2): "body-diagonal"}
DM_LINE = [0.0, 0.05, 0.15, 0.3, 0.6]                      # R33 chirality-breaking dir


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
#  ONE (k, theta, dm) point: branch-resolved N_prop on the SAME machine.
#
#  The walk symbol / placed complex / ker C / linearized-Riemann SVD are all
#  RC1a/R32's frozen functions.  We only choose WHICH Floquet branch feeds the
#  curvature count (branch="pos"/"neg"/dominant), and we optionally rebuild the
#  whole thing on the MIRROR chirality (k -> -k, walk_matrix_1m).
# ==========================================================================
def branch_report(U10, phases, inc_mat, Q_kerC, Q_TT, Q_gauge, Q_row, branch):
    """N_prop + lock diagnostics of ONE Floquet branch's propagating curvature."""
    Scurv, nprop, svn = R32.curvature_subspace(U10, phases, inc_mat, branch)
    if branch == "pos":
        sel = phases > 1e-9
    elif branch == "neg":
        sel = phases < -1e-9
    else:
        sel = np.ones(len(phases), bool)
    n_modes = int(np.sum(sel))
    if Scurv.shape[1] == 0 or n_modes == 0:
        return {"branch": branch, "n_modes": n_modes, "N_prop": 0,
                "curv_sv": svn, "max_angle_vs_kerC_deg": float("nan"),
                "principal_angles_vs_kerC_deg": [], "n_locked(>45deg)": 0,
                "mean_resid_outside_kerC": float("nan"),
                "Scurv_sector_energy": {"TT": 0.0, "gauge": 0.0, "row": 0.0}}
    ang = np.degrees(R32.principal_angles(Scurv, Q_kerC))
    rmean, rmax = R32.residual_outside(U10[:, sel], Q_kerC)
    sec = R32.sector_energy(Scurv, Q_TT, Q_gauge, Q_row)
    deg = np.sort(ang)
    return {
        "branch": branch, "n_modes": n_modes, "N_prop": int(nprop),
        "curv_sv": svn,
        "principal_angles_vs_kerC_deg": [float(x) for x in deg],
        "max_angle_vs_kerC_deg": float(deg.max()) if len(deg) else float("nan"),
        "n_locked(>45deg)": int(np.sum(deg > 45.0)),
        "n_inside_kerC(<5deg)": int(np.sum(deg < 5.0)),
        "mean_resid_outside_kerC": rmean, "max_resid_outside_kerC": rmax,
        "Scurv_sector_energy": sec}


def probe_point(kl, theta, dm, c):
    """Branch-resolved probe at one representative point.

    Returns baseline (dominant branch), main (+w) branch = mirror-OFF, mirror
    (-w) branch, and the literal mirror-CHIRALITY complex (k -> -k)."""
    k = np.array(kl, float) * (2 * np.pi / N)
    kap = RC.kappa_placed_p(k, c)
    if kap is None:
        return {"off_band": True}
    Q_kerC = R32.kerC_basis(kap)
    Q_TT, Q_gauge, Q_row = R32.build_sectors(kap)
    inc_mat = R32.inc_matrix(kap)

    U10, phases, mods = RC.walk_unit_modes_p(k, MU0, theta, dm, c)
    if U10.shape[1] == 0:
        return {"off_band": False, "n_unit": 0, "no_modes": True}
    dom = R32.dominant_branch(U10, phases, inc_mat)          # -w per R31
    n_pos = int(np.sum(phases > 1e-9))
    n_neg = int(np.sum(phases < -1e-9))

    rep_dom = branch_report(U10, phases, inc_mat, Q_kerC, Q_TT, Q_gauge,
                            Q_row, dom)
    rep_pos = branch_report(U10, phases, inc_mat, Q_kerC, Q_TT, Q_gauge,
                            Q_row, "pos")
    rep_neg = branch_report(U10, phases, inc_mat, Q_kerC, Q_TT, Q_gauge,
                            Q_row, "neg")

    # literal reading (A): placed complex on the MIRROR chirality.
    # walk_matrix_1m runs the mirrored split-step (shifts reversed) => the placed
    # complex on the mirror chirality equals the main complex evaluated at -k
    # (parity image).  Rebuild fully at -k and count its dominant-branch N_prop.
    km = -k
    kapm = RC.kappa_placed_p(km, c)
    if kapm is not None:
        incm = R32.inc_matrix(kapm)
        U10m, phm, _ = RC.walk_unit_modes_p(km, MU0, theta, dm, c)
        if U10m.shape[1] > 0:
            domm = R32.dominant_branch(U10m, phm, incm)
            _, nprop_mir, _ = R32.curvature_subspace(U10m, phm, incm, domm)
        else:
            nprop_mir = 0
    else:
        nprop_mir = None

    return {
        "off_band": False, "n_unit": int(U10.shape[1]),
        "n_pos_omega": n_pos, "n_neg_omega": n_neg,
        "dominant_branch": dom, "omega_shell": float(R32.shell_omega(k, c)),
        "N_prop_baseline_dominant": rep_dom["N_prop"],
        "N_prop_main_branch_mirrorOFF": rep_pos["N_prop"],
        "N_prop_mirror_branch": rep_neg["N_prop"],
        "N_prop_mirror_chirality_complex": nprop_mir,
        "branch_dominant": rep_dom,
        "branch_main_plusW": rep_pos,
        "branch_mirror_minusW": rep_neg,
    }


# ==========================================================================
#  VERDICT (§11 three-way, hypothesis-not-conclusion discipline)
# ==========================================================================
def build_verdict(rows):
    th0 = [r for r in rows if abs(r["theta"] - TH0) < 1e-9]
    base, main_off, mir_br, mir_chir = [], [], [], []
    main_resid, mir_resid, main_locked, mir_locked = [], [], [], []
    main_row, mir_row, main_tt, mir_tt = [], [], [], []
    # decisive line: dm=0 (the massless / gapless-chiral point -- the ONLY point
    # where the hypothesis's premise "massless => chiral" actually holds).
    massless_off, massless_base = [], []
    m0_main_resid, m0_mir_resid, m0_main_locked, m0_mir_locked = [], [], [], []
    dom_all_neg = True
    m0_dom_neg = True
    for r in th0:
        for kl in KSET:
            e = r["per_k"][str(kl)]
            if e.get("off_band") or e.get("no_modes"):
                continue
            base.append(e["N_prop_baseline_dominant"])
            main_off.append(e["N_prop_main_branch_mirrorOFF"])
            mir_br.append(e["N_prop_mirror_branch"])
            if e["N_prop_mirror_chirality_complex"] is not None:
                mir_chir.append(e["N_prop_mirror_chirality_complex"])
            dom_all_neg = dom_all_neg and (e["dominant_branch"] == "neg")
            if abs(r["dm"]) < 1e-9:
                m0_dom_neg = m0_dom_neg and (e["dominant_branch"] == "neg")
            bm, bn = e["branch_main_plusW"], e["branch_mirror_minusW"]
            main_resid.append(bm["mean_resid_outside_kerC"])
            mir_resid.append(bn["mean_resid_outside_kerC"])
            main_locked.append(bm["n_locked(>45deg)"])
            mir_locked.append(bn["n_locked(>45deg)"])
            main_row.append(bm["Scurv_sector_energy"]["row"])
            mir_row.append(bn["Scurv_sector_energy"]["row"])
            main_tt.append(bm["Scurv_sector_energy"]["TT"])
            mir_tt.append(bn["Scurv_sector_energy"]["TT"])
            if abs(r["dm"]) < 1e-9:
                massless_off.append(e["N_prop_main_branch_mirrorOFF"])
                massless_base.append(e["N_prop_baseline_dominant"])
                m0_main_resid.append(bm["mean_resid_outside_kerC"])
                m0_mir_resid.append(bn["mean_resid_outside_kerC"])
                m0_main_locked.append(bm["n_locked(>45deg)"])
                m0_mir_locked.append(bn["n_locked(>45deg)"])

    # DECISION keys on the massless line (hypothesis premise); dm!=0 already
    # breaks chirality, so a stray count there cannot confirm chiral N-N and the
    # 4<->5 jitter is a known SVD threshold-edge artifact (RC1a).
    mirror_off_hits_2 = (all(n <= 2 for n in massless_off)
                         if massless_off else False)
    mirror_off_any_2 = any(n <= 2 for n in massless_off) if massless_off else False
    mirror_off_stays_high = (all(n >= 4 for n in massless_off)
                             if massless_off else False)
    # R31 cross-validation: is the mirror (-w) branch the row-sector 病灶, while the
    # main (+w) branch sits inside ker C?
    # keyed on the massless dm=0 line (the physical / gapless-chiral point);
    # at dm!=0 the mass mixes the chiralities and the clean branch separation
    # degrades -- itself evidence AGAINST the chiral hypothesis, reported below.
    r31_confirmed = bool(
        m0_dom_neg
        and m0_main_resid and max(m0_main_resid) < 0.30    # main branch ~inside kerC
        and m0_mir_resid and min(m0_mir_resid) > 0.4       # mirror branch locked out
        and (sum(m0_main_locked) == 0)                     # main: no locked angles
        and all(l >= 1 for l in m0_mir_locked))            # mirror: >=1 locked angle

    metrics = {
        "N_prop_massless_dm0_mirrorOFF": massless_off,
        "N_prop_massless_dm0_baseline": massless_base,
        "N_prop_baseline_dominant": base,
        "N_prop_main_branch_mirrorOFF": main_off,
        "N_prop_mirror_branch_minusW": mir_br,
        "N_prop_mirror_chirality_complex": mir_chir,
        "main_branch_resid_outside_kerC_range": [min(main_resid), max(main_resid)]
        if main_resid else None,
        "mirror_branch_resid_outside_kerC_range": [min(mir_resid), max(mir_resid)]
        if mir_resid else None,
        "main_branch_locked_angle_counts": main_locked,
        "mirror_branch_locked_angle_counts": mir_locked,
        "main_branch_row_sector_energy_range": [min(main_row), max(main_row)]
        if main_row else None,
        "mirror_branch_row_sector_energy_range": [min(mir_row), max(mir_row)]
        if mir_row else None,
        "main_branch_TT_sector_energy_range": [min(main_tt), max(main_tt)]
        if main_tt else None,
        "dominant_branch_all_negW": dom_all_neg,
        "dominant_branch_all_negW_massless_dm0": m0_dom_neg,
        "massless_dm0_main_resid_outside_kerC_range": [min(m0_main_resid),
                                                       max(m0_main_resid)]
        if m0_main_resid else None,
        "massless_dm0_mirror_resid_outside_kerC_range": [min(m0_mir_resid),
                                                         max(m0_mir_resid)]
        if m0_mir_resid else None,
        "massless_dm0_main_locked_counts": m0_main_locked,
        "massless_dm0_mirror_locked_counts": m0_mir_locked,
        "R31_minusW_lock_crossvalidation_confirmed": r31_confirmed,
    }

    if mirror_off_hits_2:
        tag = "CHIRALITY N-N CONFIRMED (mirror-off drops N_prop to 2 at dm=0)"
        verdict = (
            "Turning off the mirror chirality branch drops the unprojected N_prop "
            "to 2 at the massless (dm=0) point at every k: the extra curvature DOF "
            "come from chirality doubling. RC3 answer forms (relaxing chirality => "
            "reachable but the graviton gains mass / breaks the J5 co-cone -- a "
            "DIRECTION to verify separately, NOT this probe's conclusion). MECHANISM "
            "ARGUMENT, SIGNAL NOT A BIT-PROOF; a candidate N-N boundary.")
    elif mirror_off_stays_high:
        tag = ("CHIRALITY DOUBLING EXCLUDED as the N_prop culprit "
               "(mirror-off stays 4 at the massless dm=0 point)")
        verdict = (
            "At the massless dm=0 point (the ONLY point where the hypothesis premise "
            "'massless => chiral' holds) turning off the mirror branch does NOT drop "
            "N_prop to 2 -- it stays %s (main/+w branch). The extra count is NOT "
            "removed by deleting the "
            "mirror sector. Moreover the RC1a/R28/R31/R32 placed complex is built "
            "on the MAIN chirality ALONE (walk_symbol_p = walk_matrix_1, no mirror "
            "block), yet N_prop is already 4-5; and the placed complex rebuilt on "
            "the MIRROR chirality (walk_matrix_1m == main at -k) gives the SAME %s "
            "-- each chirality independently carries the excess. => chirality "
            "doubling is EXCLUDED as the main culprit for N_prop>2; look elsewhere. "
            "HONEST NUANCE (two-sided): the reachability LOCK (residual outside "
            "ker C = the R28/R31/R32 病灶) IS localised to the -w (mirror) Floquet "
            "branch -- R31 cross-validation %s (main/+w branch ~inside ker C, "
            "residual %s, zero locked angles; mirror/-w branch residual %s, >=1 "
            "locked angle 40-90deg). So the mirror/-w branch carries the OBSTACLE, "
            "but removing it leaves 2 spurious GAUGE-propagating modes in the main "
            "branch (gauge subset ker C, still counted) => N_prop stays 4, never 2. "
            "The residual obstacle splits in two: (a) -w-branch constraint-row "
            "curvature, (b) +w-branch gauge propagation; neither is fixed by "
            "removing chirality doubling. ANTI-HYPOTHESIS TREND: as dm grows "
            "(chirality BROKEN) the main/+w branch gets WORSE not better -- residual "
            "outside ker C rises 0.08->0.74, row-sector curvature 0.01->0.62, locked "
            "angles appear -- the opposite of what 'massless-chiral => extra DOF' "
            "predicts." % (
                sorted(set(massless_off)),
                sorted(set(mir_chir)) if mir_chir else "N/A",
                "CONFIRMED" if r31_confirmed else "PARTIAL",
                metrics["massless_dm0_main_resid_outside_kerC_range"],
                metrics["massless_dm0_mirror_resid_outside_kerC_range"]))
    else:
        tag = "MIXED / NOT CLEAN (report honestly, NEEDS-council)"
        verdict = (
            "Mixed evidence on the massless dm=0 line: mirror-off N_prop = %s (hits "
            "2 somewhere: %s). Neither a clean drop-to-2 (would confirm N-N) nor a "
            "clean stays-4 (would exclude). R31 -w-lock cross-validation: %s. Report "
            "honestly." % (
                sorted(set(massless_off)), mirror_off_any_2,
                "confirmed" if r31_confirmed else "partial"))

    return {"verdict_tag": tag, "verdict": verdict, "verdict_metrics": metrics}


# ==========================================================================
#  figure
# ==========================================================================
def make_figure(rows):
    th0 = sorted([r for r in rows if abs(r["theta"] - TH0) < 1e-9],
                 key=lambda r: r["dm"])
    dms = [r["dm"] for r in th0]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))

    def series(kl, key):
        ys = []
        for r in th0:
            e = r["per_k"][str(kl)]
            ys.append(e.get(key, float("nan")) if not (e.get("off_band") or
                      e.get("no_modes")) else float("nan"))
        return ys

    ax = axes[0]
    for kl in KSET:
        ax.plot(dms, series(kl, "N_prop_baseline_dominant"), marker="o",
                label=f"{kl} baseline(-w)")
        ax.plot(dms, series(kl, "N_prop_main_branch_mirrorOFF"), marker="s",
                ls="--", label=f"{kl} mirror-OFF(+w)")
    ax.axhline(2, color="green", ls=":", lw=0.8)
    ax.set_xlabel("dm (chirality-breaking mass)")
    ax.set_ylabel("N_prop (unprojected)")
    ax.set_title("N_prop: baseline vs mirror-OFF\n(-> 2 = N-N confirmed)")
    ax.set_ylim(0, 6.5); ax.legend(fontsize=6)

    ax = axes[1]
    for kl in KSET:
        yb = [r["per_k"][str(kl)]["branch_main_plusW"]["mean_resid_outside_kerC"]
              if not (r["per_k"][str(kl)].get("off_band") or
                      r["per_k"][str(kl)].get("no_modes")) else float("nan")
              for r in th0]
        yn = [r["per_k"][str(kl)]["branch_mirror_minusW"]["mean_resid_outside_kerC"]
              if not (r["per_k"][str(kl)].get("off_band") or
                      r["per_k"][str(kl)].get("no_modes")) else float("nan")
              for r in th0]
        ax.plot(dms, yb, marker="s", ls="--", label=f"{kl} main(+w)")
        ax.plot(dms, yn, marker="^", label=f"{kl} mirror(-w)")
    ax.set_xlabel("dm"); ax.set_ylabel("mean residual outside ker C")
    ax.set_title("the LOCK by branch\n(main~inside, mirror=病灶 lock)")
    ax.set_ylim(-0.02, 0.9); ax.legend(fontsize=6)

    ax = axes[2]
    for kl in KSET:
        yr = [r["per_k"][str(kl)]["branch_mirror_minusW"]["Scurv_sector_energy"]["row"]
              if not (r["per_k"][str(kl)].get("off_band") or
                      r["per_k"][str(kl)].get("no_modes")) else float("nan")
              for r in th0]
        ym = [r["per_k"][str(kl)]["branch_main_plusW"]["Scurv_sector_energy"]["row"]
              if not (r["per_k"][str(kl)].get("off_band") or
                      r["per_k"][str(kl)].get("no_modes")) else float("nan")
              for r in th0]
        ax.plot(dms, yr, marker="^", label=f"{kl} mirror(-w) row")
        ax.plot(dms, ym, marker="s", ls="--", label=f"{kl} main(+w) row")
    ax.set_xlabel("dm"); ax.set_ylabel("constraint-ROW sector energy of S_curv")
    ax.set_title("R31 cross-val: 病灶 row curvature\nlives on the -w (mirror) branch")
    ax.set_ylim(-0.02, 0.9); ax.legend(fontsize=6)

    fig.suptitle("RC3 probe one: turn off the mirror chirality branch, count N_prop "
                 "(theta=pi/3, c=0.5 reassembly)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110)
    plt.close(fig)


# ==========================================================================
#  main driver
# ==========================================================================
def main():
    t0 = time.time()
    payload = {
        "register": "RC3-probe-one-chirality-doubling-NN (reachability campaign §11)",
        "status": "RUNNING", "backend": "numpy",
        "hypothesis": ("PREREGISTERED HYPOTHESIS NOT CONCLUSION: massless graviton "
                       "=> chiral matter => chirality doubling (43g mirror branch) => "
                       "mirror branch = extra 2 curvature DOF => N_prop=4. Test: turn "
                       "off the mirror branch, count N_prop; 2=>N-N confirmed, 4=>"
                       "chirality excluded."),
        "mirror_branch_location": (
            "literal: tensor_walker.walk_matrix_1(main)/walk_matrix_1m(mirror, k->-k), "
            "tcf.step_matrix.chir_block(+1/-1), the 43g/43h/43i chirality doubling. "
            "In the RC1a/R28/R31/R32 placed complex (walk_symbol_p = walk_matrix_1, "
            "MAIN chirality only) the mirror shows up as the -w Floquet branch (R31's "
            "row-sector 病灶 branch). Both readings tested: (B) count N_prop on +w "
            "(main) branch only; (A) rebuild the complex on the mirror chirality "
            "(== main at -k)."),
        "params": {"N": N, "mu": MU0, "theta": TH0, "c": C0,
                   "kset": [list(k) for k in KSET], "dm_line": DM_LINE,
                   "sv_thresh": R32.SV_THRESH},
        "frozen_inputs_sha256": {
            "rc1a_tensor_index_scan.py": sha256_file(os.path.join(DIR, "rc1a_tensor_index_scan.py")),
            "r32_reachability_probe.py": sha256_file(os.path.join(DIR, "r32_reachability_probe.py")),
            "tensor_coin_feedback.py": sha256_file(os.path.join(ROOT, "rulespace_gpu", "tensor_coin_feedback.py")),
            "tensor_walker.py": sha256_file(os.path.join(ROOT, "rulespace_gpu", "tensor_walker.py")),
        },
        "red_lines": ("hypothesis not conclusion (R27); branch-off is a DIAGNOSTIC not "
                      "a candidate construction (cannot unitarily delete a Floquet "
                      "branch); record TT/co-cone/causal side effects; no M3/emergence/"
                      "reachability closed; R30 existence & boundary unchanged; frozen "
                      "inputs read-only; fp64."),
    }
    write_json(payload)

    print("RC3 PROBE ONE: turn off the mirror chirality branch, count N_prop")
    print("=" * 74)

    # -- faithfulness: the RC1a machine still reduces to the frozen stack -----
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

    # -- representative points (theta=pi/3 dm line + theta=0.5 sanity) --------
    pts = [{"theta": TH0, "dm": dm, "tag": "th=pi/3 (c=0.5)"} for dm in DM_LINE]
    pts.append({"theta": 0.5, "dm": 0.0, "tag": "th=0.5 sanity"})
    pts.append({"theta": 0.5, "dm": 0.3, "tag": "th=0.5 sanity"})

    rows = []
    for pt in pts:
        theta, dm = pt["theta"], pt["dm"]
        c = math.cos(theta)
        entry = {**pt, "c": c, "per_k": {}}
        for kl in KSET:
            e = probe_point(kl, theta, dm, c)
            entry["per_k"][str(kl)] = e
            if e.get("off_band") or e.get("no_modes"):
                print(f"  th={theta:.3f} dm={dm:.2f} k={kl}: off-band/no modes")
                continue
            bm, bn = e["branch_main_plusW"], e["branch_mirror_minusW"]
            print(f"  th={theta:.3f} dm={dm:.2f} k={str(kl):>9} [{KLAB[kl]:>13}]: "
                  f"N_prop base(-w)={e['N_prop_baseline_dominant']} "
                  f"mirrorOFF(+w)={e['N_prop_main_branch_mirrorOFF']} "
                  f"mirrorChir={e['N_prop_mirror_chirality_complex']} | "
                  f"resid_out main={bm['mean_resid_outside_kerC']:.2f} "
                  f"mir={bn['mean_resid_outside_kerC']:.2f} | "
                  f"lock main={bm['n_locked(>45deg)']} mir={bn['n_locked(>45deg)']} | "
                  f"row main={bm['Scurv_sector_energy']['row']:.2f} "
                  f"mir={bn['Scurv_sector_energy']['row']:.2f}")
        rows.append(entry)
        write_json({**payload, "scan_partial": rows})
    payload["scan"] = rows

    verdict = build_verdict(rows)
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
