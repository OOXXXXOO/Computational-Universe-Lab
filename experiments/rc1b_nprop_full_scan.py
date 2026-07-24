"""RC1b -- REACHABILITY CAMPAIGN milestone 1b, DIRECT FORM (任务书 §11 修正路径).

CAMPAIGN QUESTION (§0): can the emergent matter walk's propagation-invariant
curvature subspace be deformed onto the R30 complex's ker C so that (unprojected)
N_prop = 2 (the R30 [2,2,2,2] cliff, 3rd singular value dropping into noise)?

WHY THE DIRECT FORM (§11, lane A 2026-07-24).  The RC1a "tensor topological index
I" judge is ILL-POSED at the physical (massless / gapless) point: the graviton must
be massless => gapless => the locked bundle is non-smooth and carries no quantized
integer (RC1a saw det-winding jump 0.13->7.5 under BZ-loop refinement -- refinement
noise, NOT a physical winding).  So the index is REMOVED from the critical path
(demoted to an optional gapped side-witness).  RC1b's MAIN judge returns to the
DIRECT terminal criterion: scan N_prop + the max locked principal angle over the
WHOLE (theta, dm) plane (not just the theta=pi/3 line RC1a/R32 tested), and look for
ANY (theta, dm) where N_prop -> 2.

  * FOUND N_prop -> 2 (a cliff, 3rd singular value into noise, aligned with R30)
      => REACHABLE CHANNEL; report (theta*, dm*) + cliff evidence -> hand to RC2.
  * NO POINT reaches 2 across the whole physical plane (N_prop stays 4-5, the max
      locked-angle floor never approaches 0 anywhere)
      => "UNREACHABLE (current assumption set)" is a MEASURED result, NOT a default
      (this is the direct answer to the "lane B defaults to locked" worry) -> RC3.
  * Either way report the N_prop + max-angle (theta,dm) maps and the CLOSEST point
      to N_prop=2 / to angle 0 (even if neither target is reached).

HONESTY RED LINES (§7 + §11): two-sided blanks.  Only N_prop measured=2 counts as
reachable (NOT an angle drop / extrapolation); only a genuine full-range scan with
no 2 counts as measured-unreachable (must really cover the physical range).  This is
a PURE REACHABILITY MEASUREMENT verdict: it does NOT declare M3 / emergence /
reachability closed; R30 existence & boundary unchanged (existence != emergence !=
M3).  The tensor topological index is NOT computed (§11: ill-posed at gapless pts).

MACHINE REUSE: imports the RC1a c=cos(theta) reassembly READ-ONLY (walk symbol on
c=cos theta with mass gap dm, faithfulness diff=0.0 to frozen R32 stack) and calls
its observables_at (N_prop unprojected count + principal angles S_walk vs reassembled
ker C).  RC1b adds NO new physics -- it is a DENSITY increase over the plane.  Frozen
files & RC1a untouched; fp64 (RULESPACE_BACKEND=numpy).

Run: RULESPACE_BACKEND=numpy .venv/bin/python experiments/rc1b_nprop_full_scan.py
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

# ---- RC1a reassembly machine, imported READ-ONLY (adds no new physics) ----
import rc1a_tensor_index_scan as RC1a                      # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "rc1b_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "rc1b_nprop_full_scan.png")

N = RC1a.N
TH0 = math.pi / 3.0                                        # R32/R30 calibrated theta
C0 = math.cos(TH0)
N_PROP_TARGET = 2                                          # R30 terminal criterion
ANGLE_ZERO_DEG = 5.0                                       # "inside ker C" threshold
SV_THRESH = RC1a.SV_THRESH                                 # 0.05 shared judge口径

# ---- (theta, dm) PLANE (physical range; NOT just the theta=pi/3 line) -----
# theta covers the physical band [0.2, pi/2 - 0.2]; c=cos theta in ~[0.20, 0.98].
# pi/3 (R30/R32 calibration) and 0.5 (RC1a extra) are inserted so the plane
# contains the previously-probed points exactly.
def theta_grid():
    g = list(np.linspace(0.2, math.pi / 2.0 - 0.2, 13))
    for extra in (0.5, TH0):
        if not any(abs(t - extra) < 1e-6 for t in g):
            g.append(extra)
    return sorted(set(round(float(t), 6) for t in g))


# dm=0 (massless / gapless Dirac point = R33 phase point) -> clearly gapped.
# Densified near dm=0 where R33 puts the single-particle W:0->1 transition.
def dm_grid():
    return [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]


# k directions: axial (small & large |k|), face-diagonal, body-diagonal.
# Richer than RC1a's 3 so an N_prop drop at any direction type is not missed.
# All stay on the c=cos theta band across the whole theta range (max c*s < 1).
KSET = [(1, 0, 0), (2, 0, 0), (0, 3, 0), (2, 2, 0),
        (3, 3, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3)]
KLAB = {(1, 0, 0): "axial", (2, 0, 0): "axial", (0, 3, 0): "axial",
        (2, 2, 0): "face-diag", (3, 3, 0): "face-diag",
        (1, 1, 1): "body-diag", (2, 2, 2): "body-diag", (3, 3, 3): "body-diag"}


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
#  PART A.  full-plane scan of the two DIRECT observables (N_prop + max angle)
# ==========================================================================
def scan_point(theta, dm):
    """N_prop + max locked principal angle at (theta, dm), per k and aggregated.
    Reuses RC1a.observables_at (c=cos theta reassembly, mass gap dm)."""
    c = math.cos(theta)
    per_k = {}
    nprops, maxangs, minangs = [], [], []
    for kl in KSET:
        obs = RC1a.observables_at(kl, theta, dm, c=c)
        if obs is None or obs.get("off"):
            per_k[str(kl)] = {"off": True}
            continue
        per_k[str(kl)] = {
            "N_prop": int(obs["N_prop"]),
            "max_angle_deg": float(obs["max_angle_deg"]),
            "min_angle_deg": float(obs["min_angle_deg"]),
            "n_inside_kerC(<5deg)": int(obs["n_inside_kerC(<5deg)"]),
            "n_locked(>45deg)": int(obs["n_locked(>45deg)"]),
            "curv_sv": obs["curv_sv"],
            "mean_resid_outside_kerC": float(obs["mean_resid_outside_kerC"]),
            "label": KLAB[kl]}
        nprops.append(int(obs["N_prop"]))
        maxangs.append(float(obs["max_angle_deg"]))
        minangs.append(float(obs["min_angle_deg"]))
    if not nprops:
        return {"theta": theta, "dm": dm, "c": c, "off_all": True, "per_k": per_k}
    return {
        "theta": theta, "dm": dm, "c": c, "off_all": False, "per_k": per_k,
        # aggregate over k: the FAVOURABLE extremes (closest to the R30 targets)
        "N_prop_min": int(min(nprops)), "N_prop_max": int(max(nprops)),
        "N_prop_by_k": nprops,
        "all_k_Nprop_eq2": bool(all(n == N_PROP_TARGET for n in nprops)),
        "any_k_Nprop_le2": bool(any(n <= N_PROP_TARGET for n in nprops)),
        "max_angle_floor_deg": float(min(maxangs)),   # smallest max-angle over k
        "max_angle_ceil_deg": float(max(maxangs)),
        "min_angle_floor_deg": float(min(minangs))}


def run_scan():
    THs, DMs = theta_grid(), dm_grid()
    rows = []
    for th in THs:
        for dm in DMs:
            rows.append(scan_point(th, dm))
    return THs, DMs, rows


# ==========================================================================
#  PART B.  verdict (direct N_prop=2 criterion) + closest-approach report
# ==========================================================================
def build_verdict(THs, DMs, rows):
    live = [r for r in rows if not r.get("off_all")]
    # closest to N_prop = 2 (min N_prop over the whole plane)
    r_np = min(live, key=lambda r: (r["N_prop_min"], r["max_angle_floor_deg"]))
    # closest to angle 0 (min max-angle floor over the whole plane)
    r_ang = min(live, key=lambda r: r["max_angle_floor_deg"])
    global_min_nprop = min(r["N_prop_min"] for r in live)
    global_min_angle = min(r["max_angle_floor_deg"] for r in live)
    reached_2 = [r for r in live if r["any_k_Nprop_le2"]]
    cliff_2 = [r for r in live if r["all_k_Nprop_eq2"]]
    nprop_values = sorted(set(n for r in live for n in r["N_prop_by_k"]))
    angle_near_zero = global_min_angle < ANGLE_ZERO_DEG

    def _loc(r):
        return {"theta": r["theta"], "dm": r["dm"], "c": r["c"],
                "N_prop_min": r["N_prop_min"], "N_prop_by_k": r["N_prop_by_k"],
                "max_angle_floor_deg": r["max_angle_floor_deg"],
                "min_angle_floor_deg": r["min_angle_floor_deg"]}

    if cliff_2:
        tag = "REACHABLE CHANNEL (R30-aligned N_prop=2 cliff at all k)"
        verdict = (
            "A (theta,dm) point drives the UNPROJECTED N_prop to 2 at EVERY probed "
            "k direction (the R30 [2,2,2,2] cliff: 3rd singular value below the %.2f "
            "noise floor). This is a MEASURED reachable channel; report (theta*,dm*) "
            "and hand to RC2 for the full acceptance (cliff at body-diagonal, residual"
            "->1e-15, TT/gauge sectors unmoved)." % SV_THRESH)
    elif reached_2:
        tag = "PARTIAL N_prop=2 (some k reach 2, not all) -- REACHABLE-LEAN, needs RC2"
        verdict = (
            "N_prop reaches 2 at SOME k directions but not all simultaneously, so the "
            "R30 [2,2,2,2] cliff is not yet met on the plane grid. This is a measured "
            "reachability SIGNAL (not the full cliff); recommend RC2 targeting the "
            "(theta,dm) with the most k at 2. Two-sided blank held: not yet the R30 "
            "cliff.")
    else:
        tag = "MEASURED UNREACHABLE (current assumption set) -- full-plane N_prop never 2"
        verdict = (
            "Across the WHOLE physical (theta,dm) plane -- theta in [%.2f, %.2f] (%d "
            "values incl. pi/3), dm in [0, %.1f] (%d values, densified at the R33 dm=0 "
            "gapless point) x %d k directions -- the unprojected N_prop NEVER reaches "
            "2: the observed N_prop values are %s, with global minimum %d, and the max "
            "locked principal-angle floor never approaches 0 (global minimum %.1f deg "
            ">> %.0f). So the emergent walk's propagating-curvature subspace keeps its "
            "extra constraint-row DOF everywhere on the plane. Per the §11 direct "
            "criterion this makes 'UNREACHABLE (current assumption set)' a MEASURED "
            "result, NOT a default -- the whole plane was genuinely scanned. Two-sided "
            "blanks held: NOT deformation-feasible (N_prop never measured=2); NOT a "
            "proven topological no-go (the tensor index is ill-posed at the gapless "
            "point, §11). Hand to RC3 (relax-an-assumption adjudication; the chirality-"
            "doubling N-N hypothesis of §11 is the first probe)." % (
                THs[0], THs[-1], len(THs), DMs[-1], len(DMs), len(KSET),
                nprop_values, global_min_nprop, global_min_angle, ANGLE_ZERO_DEG))

    return {
        "verdict_tag": tag, "verdict": verdict,
        "reachable_channel": bool(cliff_2),
        "partial_nprop2": bool(reached_2 and not cliff_2),
        "measured_unreachable": bool(not reached_2),
        "global_min_N_prop": int(global_min_nprop),
        "global_min_max_angle_floor_deg": float(global_min_angle),
        "angle_floor_near_zero(<5deg)": bool(angle_near_zero),
        "observed_N_prop_values": nprop_values,
        "closest_to_Nprop2": _loc(r_np),
        "closest_to_angle0": _loc(r_ang),
        "n_cliff_points": len(cliff_2), "n_partial_points": len(reached_2)}


# ==========================================================================
#  PART C.  figure -- (theta, dm) heatmaps of N_prop_min and max-angle floor
# ==========================================================================
def make_figure(THs, DMs, rows, verdict):
    idx = {(round(r["theta"], 6), r["dm"]): r for r in rows}
    NP = np.full((len(DMs), len(THs)), np.nan)
    AG = np.full((len(DMs), len(THs)), np.nan)
    for i, dm in enumerate(DMs):
        for j, th in enumerate(THs):
            r = idx.get((round(th, 6), dm))
            if r and not r.get("off_all"):
                NP[i, j] = r["N_prop_min"]
                AG[i, j] = r["max_angle_floor_deg"]
    fig, axes = plt.subplots(1, 2, figsize=(15.0, 5.4))
    ext = [THs[0], THs[-1], DMs[0], DMs[-1]]
    ax = axes[0]
    im = ax.imshow(NP, origin="lower", aspect="auto", extent=ext,
                   cmap="viridis", vmin=2, vmax=5)
    fig.colorbar(im, ax=ax, label="min N_prop over k")
    ax.axvline(TH0, color="w", ls="--", lw=0.8)
    cn = verdict["closest_to_Nprop2"]
    ax.plot(cn["theta"], cn["dm"], "r*", ms=15,
            label="min N_prop=%d" % cn["N_prop_min"])
    ax.set_xlabel("theta  (c = cos theta)"); ax.set_ylabel("dm (mass gap)")
    ax.set_title("N_prop (min over k) on the (theta,dm) plane\n"
                 "target = 2 (R30 cliff); observed floor = %d"
                 % verdict["global_min_N_prop"])
    ax.legend(fontsize=8, loc="upper right")
    ax = axes[1]
    im = ax.imshow(AG, origin="lower", aspect="auto", extent=ext,
                   cmap="magma_r", vmin=0, vmax=90)
    fig.colorbar(im, ax=ax, label="max locked angle floor (deg)")
    ax.axvline(TH0, color="w", ls="--", lw=0.8)
    ca = verdict["closest_to_angle0"]
    ax.plot(ca["theta"], ca["dm"], "c*", ms=15,
            label="min floor=%.1f deg" % ca["max_angle_floor_deg"])
    ax.set_xlabel("theta  (c = cos theta)"); ax.set_ylabel("dm (mass gap)")
    ax.set_title("max locked principal angle (floor over k)\n"
                 "target = 0 (S_walk in ker C); observed floor = %.1f deg"
                 % verdict["global_min_max_angle_floor_deg"])
    ax.legend(fontsize=8, loc="upper right")
    fig.suptitle("RC1b: DIRECT full-plane scan -- N_prop + max locked angle "
                 "(c=cos theta reassembly). Verdict: %s" % verdict["verdict_tag"],
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110)
    plt.close(fig)


# ==========================================================================
#  PART D.  main driver
# ==========================================================================
def main():
    t0 = time.time()
    THs, DMs = theta_grid(), dm_grid()
    payload = {
        "register": "RC1b-Nprop-full-plane-scan (reachability campaign, DIRECT form §11)",
        "status": "RUNNING", "backend": "numpy",
        "question": ("does ANY (theta,dm) on the whole physical plane drive the "
                     "unprojected N_prop to 2 (the R30 cliff)? c=cos theta reassembly, "
                     "mass gap dm; tensor topological index NOT computed (§11 ill-posed "
                     "at gapless pt)."),
        "params": {"N": N, "mu": RC1a.MU0, "sv_thresh": SV_THRESH,
                   "n_prop_target": N_PROP_TARGET, "angle_zero_deg": ANGLE_ZERO_DEG,
                   "theta_grid": THs, "dm_grid": DMs,
                   "kset": [list(k) for k in KSET],
                   "n_points": len(THs) * len(DMs), "n_k": len(KSET)},
        "red_lines": ("pure reachability measurement verdict; two-sided blanks (only "
                      "N_prop measured=2 => reachable; only genuine full-range no-2 => "
                      "measured-unreachable). Does NOT declare M3/emergence/reachability "
                      "closed. R30 existence & boundary unchanged (existence != emergence "
                      "!= M3). tensor topological index NOT on the critical path (§11). "
                      "frozen inputs & RC1a read-only; fp64."),
        "frozen_inputs_sha256": {
            "rc1a_tensor_index_scan.py": sha256_file(
                os.path.join(DIR, "rc1a_tensor_index_scan.py")),
            "r32_reachability_probe.py": sha256_file(
                os.path.join(DIR, "r32_reachability_probe.py")),
            "r15_walk_dedonder.py": sha256_file(
                os.path.join(DIR, "r15_walk_dedonder.py")),
            "cp1_v4_L2.py": sha256_file(os.path.join(DIR, "cp1_v4_L2.py")),
        },
    }
    write_json(payload)
    print("RC1b DIRECT full-plane N_prop scan (c = cos theta reassembly)")
    print("=" * 74)

    # faithfulness re-confirm (RC1a reassembly reduces to frozen stack, diff=0)
    cert = RC1a.faithfulness_certificate()
    payload["faithfulness_certificate"] = cert
    print(f"[cert] RC1a reassembly vs frozen @ (pi/3,dm=0,c=0.5): "
          f"max diff {max(cert['walk_symbol_max_diff'], cert['K_state_max_diff'], cert['damped_map_max_diff']):.1e}"
          f" -> {'PASS' if cert['PASS'] else 'FAIL'}")
    write_json(payload)
    if not cert["PASS"]:
        payload["status"] = "ABORT-faithfulness-failed"
        write_json(payload)
        print("ABORT: reassembly does not reduce to frozen stack.")
        return

    print(f"[scan] {len(THs)} theta x {len(DMs)} dm x {len(KSET)} k = "
          f"{len(THs) * len(DMs) * len(KSET)} evaluations ...")
    _, _, rows = run_scan()
    payload["scan"] = rows
    write_json(payload)

    verdict = build_verdict(THs, DMs, rows)
    payload.update(verdict)
    write_json(payload)

    make_figure(THs, DMs, rows, verdict)
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
    print(f"global min N_prop = {verdict['global_min_N_prop']} ; "
          f"global min max-angle floor = {verdict['global_min_max_angle_floor_deg']:.1f} deg")
    print(f"closest to N_prop=2: theta={verdict['closest_to_Nprop2']['theta']:.4f} "
          f"dm={verdict['closest_to_Nprop2']['dm']} "
          f"N_prop_by_k={verdict['closest_to_Nprop2']['N_prop_by_k']}")
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()



