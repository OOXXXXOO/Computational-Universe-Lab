"""V2M0 -- SIGMA-MACHINE CALIBRATION PIECE: >=64^3 SCALING AUDIT (lane B, 2026-07-26).

M0' DELIVERABLE 4.  AUTHORITY: docsv2/v2-任务书-M0-仪器迁移.md §5 (spec, verbatim)
+ docsv2/v2-裁定-D1D5-2026-07-26.md D3.  NATURE (措辞红线, fixed here forever):
this is an INSTRUMENT CALIBRATION of the v2 sigma machine, NOT a physics gate.
Whatever the numbers say, BOTH branches produce only WORDING-UPDATE SUGGESTIONS
for the scaling-evidence section (§五) of the v1 seal document
(docs/status/阶段封存-2026-07-26-...md) -- handed to lane A, append-only, no
history rewritten.  NO v1 verdict is changed (R37 branch stays "ambiguous" in its
own preregistered series; R36 (b) FAIL untouched); NO v2 physics gate is
triggered or filled.

GOAL: v1 left exactly one direction -- face-diagonal -- where a <=5% small floor
could not be excluded within <=48^3 (lane-A review: ~2%, 2.1-sigma marginal,
widened-window diagnostic).  The gap was the absence of FIT-ELIGIBLE points
(n>=2 provenance) at face-diagonal |k|<0.37.  Extend the lattice series to close
that gap and settle the leftover.

FROZEN PROTOCOL (R37 verbatim -- 一字不改): this script IMPORTS the frozen R37
script (hash-verified below) and calls ITS fit_constant / fit_power /
resid_plus_modes.  Window, exclusion, dedup, observables, models, AIC criterion
are therefore literally R37's code objects:
  * fit window: per-component k = 2*pi*n/L <= pi/4 (n/L <= 1/8); context
    pi/4 < comp <= pi/2 recorded, never fitted;
  * k=0-neighbour exclusion: pooled unique-k point (deduped by exact ratio n/L)
    enters the fit only with >=1 n>=2 provenance; every lattice's n=1 raw
    reading reported verbatim;
  * primary observable resid_max(k) (max over +w mode columns, rc3ii path);
    secondary resid_mean reported, never deciding;
  * M0 resid=A0 (p=1) vs M1 resid=A+B|k|^alpha (p=3, alpha grid 0.05..4.00
    step 0.01); AIC = m*ln(RSS/m)+2p, lower wins, decisive iff |dAIC| >= 2;
  * direction-stratified, no cross-direction averaging.
The ONLY change vs R37 is the lattice list -- which is exactly what D3 orders.

LATTICES (spec §5): 16/24/32/48/64 + 96 (96^3 INCLUDED: the machine is spectral,
lattice enters only through k-sampling; per-k path = 28x28 eig + fixed (256,10)
inc, no L^3 array anywhere; measured probe RSS ~90 MB, ~1 ms/point -> feasible).
New fit-eligible ratios vs R37: 1/48 (96:2 upgrades 48:1), 1/32 (64:2, 96:3
upgrade 32:1), 3/64, 5/96, 7/96, 5/64, 11/96, 7/64 -> m: 6 -> 14 per direction.
Face-diagonal |k|<0.37 coverage: |k|=0.185 (ratio 1/48) and 0.278 (1/32) --
the spec's required interval now holds fit-eligible points.

D3 ARCHIVAL RULES (written dead HERE, before the run; not adjustable after):
  * power-law wins iff dAIC(const-power) >= +2 (decisive);
  * zero-exclusion of the intercept ("排零") iff |A| <= 2*sigma_A;
  * scaling tier: alpha >= 1 -> "clean-scaling"; 0 < alpha < 1 -> "weak-scaling";
    tier archived only when the power law wins decisively; else "undecided".
ROBUSTNESS (lane-A review口径, 复核-车道A-R36R37三半验证-2026-07-26.md §4.2,
pre-committed): (i) leave-one-out over the new fit set (report A range + whether
zero-exclusion flips); (ii) widened-window diagnostic refit including the
excluded n=1 points (diagnostic only, NEVER deciding -- window rule is R37's).

CERTIFICATES REQUIRED BEFORE ANY NEW MEASUREMENT (abort otherwise):
  1. sha256 of the three rc3ii frozen inputs == rc3ii record, bit-for-bit;
  2. sha256 of r37_residual_scaling_audit.py == R37 report record, bit-for-bit;
  3. RC1a faithfulness certificate PASS (walk/K/map diff 0.0);
  4. 16^3 calibration vs rc3ii_results.json readings <= 1e-12 (R37 cert 3);
  5. old-series re-derivation: collector re-run on R37's lattices {16,24,32,48}
     must reproduce r37_results.json fit sets and (A, sigma_A, alpha, dAIC)
     bit-for-bit (diff == 0.0) -- proves the parametrized collector is the same
     machine before it is pointed at 64^3/96^3.

PRE-WRITTEN WORDING BRANCHES (both sides blank-filled by numbers only):
  Z  (face-diagonal power decisive AND |A|<=2 sigma_A, and same for the other
      two directions): suggest the seal §五-3 wording become "三方向截距均与 0
      一致(64^3/96^3 校准),幂律标度全向成立,v1 遗留的面斜小底了结";
  NZ (otherwise): suggest "面斜小底在 64^3/96^3 下仍存,量级更新为 A=... +/- ...".
Either way the seal main sentence (死于计数+稳定性死锁,不是残差本身) is NOT
touched -- it never depended on this calibration (seal §五-4).

RED LINES: frozen inputs read-only (hashes archived); fp64 numpy; single script
<< 30 min; incremental JSON writes; no git; no v1 file modified; no v2 gate
filled; criteria in this header not revised after the run.

Run: RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m0_sigma_calibration.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
import time
import warnings
from fractions import Fraction

import numpy as np

warnings.filterwarnings("ignore")  # k->0 basis degeneracy is the R29 singularity itself

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (DIR, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# ---- frozen, READ-ONLY machinery: the R37 script itself is the protocol ------
import r37_residual_scaling_audit as R37                     # noqa: E402
import rc1a_tensor_index_scan as RC                          # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m0_sigma_calibration.json")
R37_JSON = os.path.join(ROOT, "data", "results", "r37_results.json")

# frozen-protocol hash record (R37 report + rc3ii record)
R37_SCRIPT_SHA256 = "b847808c96ef8c64c72973d0e415db202497beb0236575d351a91c1fa9508df0"

LATTICES_V2 = [16, 24, 32, 48, 64, 96]                       # spec §5; 96^3 feasible
DIRS = dict(R37.DIRS)                                        # three rays, frozen
C0 = R37.C0
DAIC_DECISIVE = R37.DAIC_DECISIVE                            # 2.0 (D3 = R37 verbatim)
FACE_TARGET_KABS = 0.37                                      # spec: face-diag gap边界


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


# ---- collector: R37.collect_direction verbatim, lattice list parametrized ----
def collect_direction(dname, dvec, lattices):
    """Byte-level copy of R37.collect_direction with LATTICES as an argument.
    Faithfulness is certified below by bit-for-bit re-derivation of the R37
    series before any new lattice is touched (certificate 5)."""
    samples = {}                                             # Fraction -> dict
    for L in lattices:
        n_max = int(R37.CTX_RATIO_MAX * L)                   # comp <= pi/2 context cap
        for n in range(1, n_max + 1):
            r = Fraction(n, L)
            if r > R37.CTX_RATIO_MAX:
                continue
            if r in samples:
                samples[r]["provenance"].append([L, n])
                continue
            comp = 2.0 * math.pi * float(r)
            k = comp * np.array(dvec, float)
            resid = R37.resid_plus_modes(k, C0)
            if resid is None:
                samples[r] = {"ratio": [r.numerator, r.denominator],
                              "comp": comp, "kabs": comp * math.sqrt(sum(dvec)),
                              "off_band": True, "provenance": [[L, n]]}
                continue
            samples[r] = {
                "ratio": [r.numerator, r.denominator],
                "comp": comp,
                "kabs": comp * math.sqrt(float(np.dot(dvec, dvec))),
                "n_plus_modes": int(resid.size),
                "resid_all": sorted(float(x) for x in resid),
                "resid_min": float(resid.min()),
                "resid_max": float(resid.max()),
                "resid_mean": float(resid.mean()),
                "leak_max": float((resid ** 2).max()),
                "leak_mean": float((resid ** 2).mean()),
                "provenance": [[L, n]],
                "off_band": False,
            }
    out = []
    for r in sorted(samples):
        s = samples[r]
        in_window = r <= R37.FIT_RATIO_MAX
        has_n_ge2 = any(n >= 2 for _, n in s["provenance"])
        s["in_fit_window"] = bool(in_window)
        s["excluded_k0_neighbour"] = bool(in_window and not has_n_ge2)
        s["in_fit"] = bool(in_window and has_n_ge2 and not s.get("off_band"))
        out.append(s)
    return out


# ---- fits: literally R37's code objects -------------------------------------
def fit_pair(x, y):
    m0 = R37.fit_constant(x, y)
    m1 = R37.fit_power(x, y)
    daic = m0["AIC"] - m1["AIC"]                             # >0 => power better
    return m0, m1, daic


def d3_archive(m0, m1, daic):
    """D3 archival columns (header rules; calibration facts, not a gate)."""
    power_decisive = bool(daic >= DAIC_DECISIVE)
    zero_excl = bool(abs(m1["A"]) <= 2.0 * m1["sigma_A"])
    if power_decisive and m1["alpha"] >= 1.0:
        tier = "clean-scaling (alpha>=1)"
    elif power_decisive and 0.0 < m1["alpha"] < 1.0:
        tier = "weak-scaling (0<alpha<1)"
    else:
        tier = "undecided (power law not decisive)"
    return {"power_decisive_dAIC_ge_2": power_decisive,
            "dAIC_const_minus_power": daic,
            "intercept_zero_consistent_|A|<=2sigmaA": zero_excl,
            "d3_tier": tier}


def judge_direction_v2(dname, pts):
    fitpts = [s for s in pts if s["in_fit"]]
    x = np.array([s["kabs"] for s in fitpts])
    y = np.array([s["resid_max"] for s in fitpts])
    m0, m1, daic = fit_pair(x, y)
    arch = d3_archive(m0, m1, daic)
    # secondary robustness fits (reported, never deciding) -- R37 protocol
    ymean = np.array([s["resid_mean"] for s in fitpts])
    s0, s1, sdaic = fit_pair(x, ymean)
    # leave-one-out (lane-A口径)
    loo = []
    for i in range(len(x)):
        xi = np.delete(x, i); yi = np.delete(y, i)
        l0, l1, ldaic = fit_pair(xi, yi)
        loo.append({"dropped_kabs": float(x[i]), "A": l1["A"],
                    "sigma_A": l1["sigma_A"], "alpha": l1["alpha"],
                    "dAIC": ldaic,
                    "zero_consistent": bool(abs(l1["A"]) <= 2.0 * l1["sigma_A"])})
    # widened-window diagnostic: include the excluded n=1 in-window points
    wpts = [s for s in pts if s["in_fit_window"] and not s.get("off_band")]
    xw = np.array([s["kabs"] for s in wpts])
    yw = np.array([s["resid_max"] for s in wpts])
    w0, w1, wdaic = fit_pair(xw, yw)
    return {
        "direction": dname,
        "n_fit_points": len(fitpts),
        "fit_kabs": [float(v) for v in x],
        "fit_resid_max": [float(v) for v in y],
        "constant_model": m0,
        "power_model": m1,
        "d3_archive": arch,
        "secondary_resid_mean": {"power": s1, "dAIC_const_minus_power": sdaic},
        "loo": {"rows": loo,
                "A_range": [min(r["A"] for r in loo), max(r["A"] for r in loo)],
                "zero_consistent_all": bool(all(r["zero_consistent"] for r in loo)),
                "zero_consistent_any": bool(any(r["zero_consistent"] for r in loo))},
        "widened_window_diagnostic": {
            "note": "includes excluded n=1 points; window rule change => "
                    "diagnostic ONLY, never deciding (R37/lane-A discipline)",
            "n_points": len(wpts), "power": w1,
            "dAIC_const_minus_power": wdaic,
            "zero_consistent": bool(abs(w1["A"]) <= 2.0 * w1["sigma_A"])},
    }


def main():
    t0 = time.time()
    payload = {
        "register": "V2M0 sigma-machine calibration: >=64^3 scaling audit "
                    "(M0' deliverable 4, D3; INSTRUMENT CALIBRATION, not a physics gate)",
        "status": "RUNNING", "backend": "numpy", "fp": "fp64",
        "authority": ["docsv2/v2-任务书-M0-仪器迁移.md §5",
                      "docsv2/v2-裁定-D1D5-2026-07-26.md D3"],
        "protocol": "R37 verbatim (imported code objects of the hash-verified "
                    "frozen script); ONLY the lattice list is extended, as D3 orders",
        "lattices": LATTICES_V2,
        "lattice_96_note": "included: per-k spectral path (28x28 eig), no L^3 "
                           "array; probe ~1 ms/point, RSS < 0.1 GB",
        "d3_rules": {"power_decisive": "dAIC(const-power) >= 2",
                     "zero_exclusion": "|A| <= 2*sigma_A",
                     "tiers": "alpha>=1 clean-scaling; 0<alpha<1 weak-scaling"},
        "red_lines": "instrument calibration only; both branches -> wording "
                     "suggestions for seal §五 (append-only, via lane A); no v1 "
                     "verdict changed; no v2 physics gate triggered; frozen "
                     "inputs read-only; criteria not revised after run",
    }
    write_json(payload)

    print("V2M0 sigma calibration: >=64^3 scaling audit  (instrument calibration)")
    print("=" * 74)

    # -- certificate 1: rc3ii frozen-input hashes
    hashes = {f: sha256_file(os.path.join(DIR, f)) for f in R37.RC3II_HASHES}
    ok1 = hashes == R37.RC3II_HASHES
    # -- certificate 2: R37 script hash (the protocol itself)
    h37 = sha256_file(os.path.join(DIR, "r37_residual_scaling_audit.py"))
    ok2 = h37 == R37_SCRIPT_SHA256
    payload["frozen_inputs_sha256"] = dict(hashes,
                                           **{"r37_residual_scaling_audit.py": h37})
    payload["r37_results_json_sha256_as_found"] = sha256_file(R37_JSON)
    payload["frozen_hash_match"] = {"rc3ii_inputs": bool(ok1), "r37_script": bool(ok2)}
    print("[cert1] rc3ii frozen hashes: %s" % ("MATCH" if ok1 else "MISMATCH"))
    print("[cert2] r37 protocol script hash: %s" % ("MATCH" if ok2 else "MISMATCH"))
    write_json(payload)
    if not (ok1 and ok2):
        payload["status"] = "ABORT-frozen-hash-mismatch"
        write_json(payload)
        return

    # -- certificate 3: RC1a faithfulness
    cert = RC.faithfulness_certificate()
    payload["faithfulness_certificate"] = cert
    print("[cert3] RC1a faithfulness: walk %.1e K %.1e map %.1e -> %s" % (
        cert["walk_symbol_max_diff"], cert["K_state_max_diff"],
        cert["damped_map_max_diff"], "PASS" if cert["PASS"] else "FAIL"))
    write_json(payload)
    if not cert["PASS"]:
        payload["status"] = "ABORT-faithfulness-failed"
        write_json(payload)
        return

    # -- certificate 4: 16^3 calibration vs rc3ii readings (R37 cert 3 verbatim)
    calib = {}
    ok4 = True
    for kl, (lo, hi) in R37.RC3II_CALIB.items():
        k = np.array(kl, float) * (2 * np.pi / 16)
        resid = R37.resid_plus_modes(k, C0)
        dlo = abs(float(resid.min()) - lo)
        dhi = abs(float(resid.max()) - hi)
        ok = bool(dlo <= 1e-12 and dhi <= 1e-12)
        ok4 = ok4 and ok
        calib[str(kl)] = {"resid_min": float(resid.min()),
                          "resid_max": float(resid.max()),
                          "diff_vs_rc3ii": [dlo, dhi], "ok": ok}
    payload["calibration_16cube_vs_rc3ii"] = calib
    print("[cert4] 16^3 calibration vs rc3ii: %s" % ("OK 6/6" if ok4 else "BAD"))
    write_json(payload)
    if not ok4:
        payload["status"] = "ABORT-calibration-mismatch"
        write_json(payload)
        return

    # -- certificate 5: old-series re-derivation, bit-for-bit vs r37_results.json
    with open(R37_JSON, "r", encoding="utf-8") as fh:
        r37res = json.load(fh)
    old_fits = {J["direction"]: J for J in r37res["direction_fits"]}
    rederive = {}
    ok5 = True
    for dname, dvec in DIRS.items():
        pts = collect_direction(dname, dvec, R37.LATTICES)
        fitpts = [s for s in pts if s["in_fit"]]
        x = np.array([s["kabs"] for s in fitpts])
        y = np.array([s["resid_max"] for s in fitpts])
        m0, m1, daic = fit_pair(x, y)
        J = old_fits[dname]
        diffs = {
            "fit_kabs": float(np.max(np.abs(x - np.array(J["fit_kabs"])))),
            "fit_resid_max": float(np.max(np.abs(y - np.array(J["fit_resid_max"])))),
            "A": abs(m1["A"] - J["power_model"]["A"]),
            "sigma_A": abs(m1["sigma_A"] - J["power_model"]["sigma_A"]),
            "alpha": abs(m1["alpha"] - J["power_model"]["alpha"]),
            "dAIC": abs(daic - J["dAIC_const_minus_power"]),
        }
        ok_d = bool(all(v == 0.0 for v in diffs.values()))
        ok5 = ok5 and ok_d
        rederive[dname] = {"diffs": diffs, "ok": ok_d}
        print("[cert5] %-14s old-series re-derivation: %s (max diff %.1e)" % (
            dname, "BIT-FOR-BIT" if ok_d else "MISMATCH", max(diffs.values())))
    payload["old_series_rederivation"] = rederive
    write_json(payload)
    if not ok5:
        payload["status"] = "ABORT-old-series-rederivation-mismatch"
        write_json(payload)
        return

    # -- measurement: three rays, extended lattice series
    data = {}
    for dname, dvec in DIRS.items():
        print("[scan] %s ray (lattices %s) ..." % (dname, LATTICES_V2))
        data[dname] = collect_direction(dname, dvec, LATTICES_V2)
    payload["ray_data"] = data
    write_json(payload)

    # -- per-lattice minimum-|k| raw readings (must-report, extended to 64/96)
    min_k_raw = {}
    for dname, pts in data.items():
        rows = {}
        for L in LATTICES_V2:
            s = next(p for p in pts if [L, 1] in p["provenance"])
            rows["L=%d" % L] = {
                "kabs": s["kabs"], "n_plus_modes": s.get("n_plus_modes"),
                "resid_min": s.get("resid_min"), "resid_max": s.get("resid_max"),
                "resid_mean": s.get("resid_mean"),
                "leak_max": s.get("leak_max"), "leak_mean": s.get("leak_mean")}
        min_k_raw[dname] = rows
    payload["min_k_raw_readings"] = min_k_raw
    write_json(payload)
    print("[raw] minimum-|k| readings (resid_max):")
    for dname, rows in min_k_raw.items():
        print("    %s: %s" % (dname, "  ".join(
            "%s |k|=%.3f max=%.4f" % (Lk, v["kabs"], v["resid_max"])
            for Lk, v in rows.items())))

    # -- fits + D3 archive + robustness
    judges = [judge_direction_v2(d, pts) for d, pts in data.items()]
    payload["direction_fits_new"] = judges
    write_json(payload)

    # -- old-vs-new comparison table + face-diagonal coverage bookkeeping
    compare = {}
    for J in judges:
        d = J["direction"]
        Jo = old_fits[d]
        new_pts = [(k, r) for k, r in zip(J["fit_kabs"], J["fit_resid_max"])
                   if not any(abs(k - ko) == 0.0 for ko in Jo["fit_kabs"])]
        compare[d] = {
            "old_16_48": {"m": Jo["n_fit_points"],
                          "A": Jo["power_model"]["A"],
                          "sigma_A": Jo["power_model"]["sigma_A"],
                          "alpha": Jo["power_model"]["alpha"],
                          "dAIC": Jo["dAIC_const_minus_power"]},
            "new_16_96": {"m": J["n_fit_points"],
                          "A": J["power_model"]["A"],
                          "sigma_A": J["power_model"]["sigma_A"],
                          "alpha": J["power_model"]["alpha"],
                          "dAIC": J["d3_archive"]["dAIC_const_minus_power"]},
            "new_fit_points": [{"kabs": k, "resid_max": r} for k, r in new_pts],
            "d3_archive": J["d3_archive"],
        }
    face_cov = [p for p in compare["face-diagonal"]["new_fit_points"]
                if p["kabs"] < FACE_TARGET_KABS]
    compare["face_diagonal_coverage_below_0p37"] = face_cov
    payload["old_vs_new"] = compare
    write_json(payload)

    for J in judges:
        m1 = J["power_model"]
        a = J["d3_archive"]
        print("[fit] %-14s m=%d  A=%.4f±%.4f  B=%.3f  α=%.2f±%.2f  ΔAIC=%.1f  "
              "排零=%s  tier=%s" % (
                  J["direction"], J["n_fit_points"], m1["A"], m1["sigma_A"],
                  m1["B"], m1["alpha"], m1["sigma_alpha"],
                  a["dAIC_const_minus_power"],
                  a["intercept_zero_consistent_|A|<=2sigmaA"], a["d3_tier"]))
        print("      LOO A∈[%.4f, %.4f] zero-consistent all=%s | widened-window "
              "A=%.4f±%.4f zero=%s" % (
                  J["loo"]["A_range"][0], J["loo"]["A_range"][1],
                  J["loo"]["zero_consistent_all"],
                  J["widened_window_diagnostic"]["power"]["A"],
                  J["widened_window_diagnostic"]["power"]["sigma_A"],
                  J["widened_window_diagnostic"]["zero_consistent"]))

    # -- pre-written wording branches (header): pick by the numbers only
    face = next(J for J in judges if J["direction"] == "face-diagonal")
    fa = face["d3_archive"]
    all_zero = all(J["d3_archive"]["intercept_zero_consistent_|A|<=2sigmaA"]
                   and J["d3_archive"]["power_decisive_dAIC_ge_2"]
                   for J in judges)
    face_zero = bool(fa["power_decisive_dAIC_ge_2"]
                     and fa["intercept_zero_consistent_|A|<=2sigmaA"])
    if face_zero and all_zero:
        branch = "Z"
        suggestion = ("建议(交车道A,只加不改史): 封存文档 §五-3 追加——v2 M0' σ 机器"
                      "校准件(64³/96³, R37 协议逐字复用)在面斜 |k|<0.37 补入拟合合格点后,"
                      "三方向幂律均决定性胜出且截距均与 0 一致(|A|≤2σ_A);v1 遗留的"
                      "\"面斜是唯一不能在 ≤48³ 内排除 ≤5% 小底的方向\"就此了结。"
                      "R37 自身 ambiguous 落点按其预注册系列不改。")
    elif face_zero:
        branch = "Z-face-only"
        suggestion = ("建议(交车道A,只加不改史): 面斜方向小底在 64³/96³ 校准下排零成立"
                      "(|A|≤2σ_A),v1 遗留面斜小底了结;但其他方向截距状态见 d3_archive,"
                      "如实并注。R37 自身 ambiguous 落点按其预注册系列不改。")
    else:
        branch = "NZ"
        suggestion = ("建议(交车道A,只加不改史): 面斜小底在 64³/96³ 下仍存,量级更新为 "
                      "A=%.4f±%.4f;封存主句(死于计数+稳定性死锁,非残差本身)不受影响。"
                      % (face["power_model"]["A"], face["power_model"]["sigma_A"]))
    payload["calibration_branch"] = branch
    payload["face_small_floor_zero_excluded"] = face_zero
    payload["wording_update_suggestion"] = suggestion
    payload["nature_reminder"] = ("instrument calibration; NOT a physics gate; "
                                  "no v1 verdict changed; no v2 gate triggered")
    write_json(payload)

    payload["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    payload["status"] = "DONE"
    payload["source_sha256"] = sha256_file(__file__)
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha          # hash of the pre-field serialization
    write_json(payload)

    print("=" * 74)
    print("BRANCH = %s  face-small-floor zero-excluded = %s" % (branch, face_zero))
    print("source  sha256 = %s" % payload["source_sha256"])
    print("results sha256 = %s" % jsha)
    print("total %.1fs, peak RSS %.0f MB" % (time.time() - t0, payload["peak_rss_mb"]))


if __name__ == "__main__":
    main()
