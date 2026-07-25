"""R37 -- (c)-HALF RESIDUAL SCALING AUDIT (preregistered; lane B, 2026-07-26).

AUTHORITY: docs/preregistration/裁定-可达性战役收束-R3验证预注册.md, "(c) 半补丁"
(PI-signed 2026-07-26) + docs/status/行动计划-2026-07-26-可达性收束三半验证与条件分支.md
(stage 0/1).  QUESTION: RC3ii's R3 pricing delta = 12-18% resid-outside-kerC of the
+w propagating modes is a FIXED 16^3 READING.  Is it an O(1) constant, or a
finite-size quantity that vanishes as the lattice grows?  This scaling fact sets
the STRENGTH of the boundary statement in the seal document ((b) already FAILED
in R36 -> seal branch is decided; (c) decides between the two sub-forms:
C-FAIL = structural-unreachability signal UPGRADED (O(1) constant cost);
C-PASS = boundary statement must note "residual vanishes in the limit language;
unreachability died of counting + stability deadlock, not of the residual itself").

MACHINE (frozen, READ-ONLY, same computation path as rc3ii candidate_R3):
  resid_outside_kerC per +w mode column =
      || b - Q_kerC (Q_kerC^H b) ||   for each unit column b of Bpos,
  where Bpos = walk_unit_modes_p(k, MU0, TH0, dm=0, C0) columns with phase > 1e-9
  (RC1a reassembled emergent walk, physical-h block, unit-normalized) and
  Q_kerC = qr([Q_gauge | Q_TT]) from R32.build_sectors(kappa_placed_p(k, C0))
  -- IDENTICAL code path to rc3ii._bases/_plus_modes + candidate_R3's resid.
  The machine is SPECTRAL in continuous k; the lattice enters ONLY through the
  sampling k = (2*pi/L) * n * dir.  Hence the scaling audit = sampling the same
  frozen resid(k) at the k resolvable by each lattice.  fp64 (numpy backend).

PREREGISTERED PROTOCOL (all details fixed HERE, BEFORE the run; not adjustable):
  * Lattices L in {16, 24, 32, 48}.  48^3 memory estimate: the (c) path holds no
    L^3 array (per-k 28x28 eig + fixed (256,10) inc); RSS ~ tens of MB -> FEASIBLE,
    included.  (Only rc3ii's R1 projector_field needed the full L^3 grid; unused here.)
  * Three rays: axial (1,0,0), face-diagonal (1,1,0), body-diagonal (1,1,1);
    samples n = 1..floor(L/8)  i.e. per-component k = 2*pi*n/L <= pi/4
    (FIT WINDOW, fixed a priori: wavelength >= 8 sites; the original 16^3 judge
    point k=(2,0,0) sits exactly at the window edge, everything smaller probes
    toward the continuum).  Context points pi/4 < comp <= pi/2 are RECORDED and
    plotted grey but NEVER fitted.
  * Per-k scalar observables (per unique k, deduped by exact ratio n/L):
      PRIMARY  : resid_max(k) = max over the +w mode columns  (this is what the
                 rc3ii delta prices: the worst residual that must be tolerated);
      SECONDARY: resid_mean(k), resid_min(k)  (robustness, reported, NOT deciding);
      LEAKAGE  : leak_mean(k) = mean(resid^2), leak_max(k) = max(resid^2).
  * k=0-NEIGHBOUR EXCLUSION: each lattice's n=1 sample is its k=0-neighbour cell;
    a pooled unique-k point enters the FIT only if it has at least one n>=2
    provenance.  Each lattice's minimum-|k| (n=1) RAW readings are reported
    verbatim for all three rays (预注册要求: 最小 |k|=2*pi/L 必测且同报原始读数).
  * DIRECTION-STRATIFIED FITS (no cross-direction averaging -- 车道A 复核点):
    per direction, on the fit set, two models of resid_max(|k|):
      M0 (constant) : resid = A0             (p=1 parameter)
      M1 (power law): resid = A + B*|k|^alpha, alpha grid (0.05..4.00 step 0.01)
                      with (A,B) linear least squares per alpha  (p=3)
    MODEL SELECTION CRITERION (chosen HERE, before running, per prereg): AIC,
      AIC = m*ln(RSS/m) + 2p;  winner = lower AIC;  DECISIVE iff |dAIC| >= 2.
    sigma_A: linearized covariance at the optimum, s^2 = RSS/(m-p),
      cov = s^2 * (J^T J)^-1 with J = [1, x^alpha, B*ln(x)*x^alpha].
  * PER-DIRECTION VERDICT (written BEFORE the run):
      PASS_d : M1 wins decisively (dAIC >= 2) AND alpha > 0 AND |A| <= 2*sigma_A
               ("A consistent with 0 within fit error");
      FAIL_d : the AIC-winning model's constant is O(1):
               |A_win| >= 0.05 AND |A_win| > 2*sigma_A_win
               (0.05 = SV_THRESH, the shared judge scale of this frozen stack);
      else   : ambiguous_d (report which direction and what is missing).
  * GLOBAL BRANCH (prereg, written dead):
      any FAIL_d            -> branch = "C-FAIL"   (structural signal upgraded);
      all three PASS_d      -> branch = "C-PASS"   (delta is finite-size, vanishes
                                                    in the limit language);
      otherwise             -> branch = "ambiguous" (name the direction + gap).

CERTIFICATES REQUIRED BEFORE ANY MEASUREMENT (abort otherwise):
  1. sha256 of the three frozen inputs == rc3ii recorded values, bit-for-bit;
  2. RC1a faithfulness certificate PASS (walk/K/map diff 0.0);
  3. 16^3 calibration: resid min/max at the three rc3ii judge k reproduce the
     rc3ii_results.json readings to <= 1e-12.

RED LINES: pure measurement -- NO existing gate or threshold is touched; (a)/(b)
halves are R36's, untouched; 卡点④ held; C-PASS does NOT flip (b)'s FAIL (the
seal direction is decided; this audit only sets the boundary-statement strength);
C-FAIL is a SIGNAL upgrade, not a theorem; two-sided blanks as always; frozen
inputs read-only; incremental JSON writes.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/r37_residual_scaling_audit.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
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

import matplotlib                                          # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402

# ---- frozen, READ-ONLY machinery (same stack as rc3ii) -------------------
import rc1a_tensor_index_scan as RC                        # noqa: E402
import r32_reachability_probe as R32                       # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "r37_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "r37_residual_scaling_audit.png")

MU0 = RC.MU0
TH0 = math.pi / 3.0
C0 = math.cos(TH0)
SV_THRESH = R32.SV_THRESH                                  # 0.05 shared judge scale

LATTICES = [16, 24, 32, 48]
DIRS = {"axial": (1, 0, 0), "face-diagonal": (1, 1, 0), "body-diagonal": (1, 1, 1)}
FIT_RATIO_MAX = Fraction(1, 8)                             # n/L <= 1/8 (comp <= pi/4)
CTX_RATIO_MAX = Fraction(1, 4)                             # context only, never fitted
ALPHA_GRID = np.arange(0.05, 4.001, 0.01)
DAIC_DECISIVE = 2.0
A_O1_THRESH = SV_THRESH                                    # 0.05 (= shared judge scale)

# rc3ii-recorded frozen-input hashes (bit-for-bit requirement) + 16^3 calibration
RC3II_HASHES = {
    "rc1a_tensor_index_scan.py":
        "ca57a32534c865542d5057eba0e578e7c3aee6e8ca36f779ab103fac6f2ab84f",
    "r32_reachability_probe.py":
        "f1ab9307ea2540a0e733ebf34f975a131790927553ded86a6e1134cd08227442",
    "r15_walk_dedonder.py":
        "ce10bc05c5caa487154a72a4169a1095930afe2afd2d84e4f49bba1041bb18cc",
}
RC3II_CALIB = {  # k(16^3 units) -> [resid_min, resid_max] from rc3ii_results.json
    (2, 0, 0): [0.11047839143772163, 0.1775137049625285],
    (2, 2, 0): [0.050845224845421755, 0.17966066843279108],
    (2, 2, 2): [0.052063126780119574, 0.11195071020524308],
}


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


# ---- rc3ii-identical computation path ------------------------------------
def kerC_basis(k, c):
    kap = RC.kappa_placed_p(k, c)
    if kap is None:
        return None
    Q_TT, Q_gauge, _ = R32.build_sectors(kap)
    Q, _ = np.linalg.qr(np.column_stack([Q_gauge, Q_TT]))   # (10,6) -- rc3ii._bases
    return Q


def resid_plus_modes(k, c):
    """rc3ii candidate_R3 resid path: per-column resid-outside-kerC of the +w
    branch.  Returns (resid array over +w columns, n_modes) or None off-band."""
    Q = kerC_basis(k, c)
    if Q is None:
        return None
    U10, phases, _ = RC.walk_unit_modes_p(k, MU0, TH0, 0.0, c)
    if U10.shape[1] == 0:
        return None
    Bpos = U10[:, phases > 1e-9]
    if Bpos.shape[1] == 0:
        return None
    resid = np.linalg.norm(Bpos - Q @ (Q.conj().T @ Bpos), axis=0)
    return resid


# ---- measurement -----------------------------------------------------------
def collect_direction(dname, dvec):
    """All unique sample points of a ray, pooled over lattices, deduped by exact
    ratio n/L.  Each point: ratio, |k|, readings, provenance, fit membership."""
    samples = {}                                            # Fraction -> dict
    for L in LATTICES:
        n_max = int(CTX_RATIO_MAX * L)                      # comp <= pi/2 context cap
        for n in range(1, n_max + 1):
            r = Fraction(n, L)
            if r > CTX_RATIO_MAX:
                continue
            if r in samples:
                samples[r]["provenance"].append([L, n])
                continue
            comp = 2.0 * math.pi * float(r)
            k = comp * np.array(dvec, float)
            resid = resid_plus_modes(k, C0)
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
        in_window = r <= FIT_RATIO_MAX
        has_n_ge2 = any(n >= 2 for _, n in s["provenance"])
        s["in_fit_window"] = bool(in_window)
        s["excluded_k0_neighbour"] = bool(in_window and not has_n_ge2)
        s["in_fit"] = bool(in_window and has_n_ge2 and not s.get("off_band"))
        out.append(s)
    return out


# ---- preregistered fits ----------------------------------------------------
def fit_constant(x, y):
    m = len(y)
    A0 = float(np.mean(y))
    rss = float(np.sum((y - A0) ** 2))
    aic = m * math.log(max(rss, 1e-300) / m) + 2 * 1
    sigA = float(np.std(y, ddof=1) / math.sqrt(m)) if m > 1 else float("inf")
    return {"model": "constant", "A": A0, "sigma_A": sigA, "RSS": rss,
            "AIC": aic, "m": m, "p": 1}


def fit_power(x, y):
    m = len(y)
    best = None
    for al in ALPHA_GRID:
        X = np.column_stack([np.ones(m), x ** al])
        coef, res, rank, _ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ coef
        rss = float(np.sum((y - pred) ** 2))
        if best is None or rss < best[0]:
            best = (rss, float(al), float(coef[0]), float(coef[1]))
    rss, al, A, B = best
    aic = m * math.log(max(rss, 1e-300) / m) + 2 * 3
    # linearized covariance at optimum
    J = np.column_stack([np.ones(m), x ** al, B * np.log(x) * (x ** al)])
    dof = max(m - 3, 1)
    s2 = rss / dof
    try:
        cov = s2 * np.linalg.inv(J.T @ J)
        sigA = float(math.sqrt(max(cov[0, 0], 0.0)))
        sigB = float(math.sqrt(max(cov[1, 1], 0.0)))
        sigAl = float(math.sqrt(max(cov[2, 2], 0.0)))
    except np.linalg.LinAlgError:
        sigA = sigB = sigAl = float("inf")
    return {"model": "power", "A": A, "sigma_A": sigA, "B": B, "sigma_B": sigB,
            "alpha": al, "sigma_alpha": sigAl, "RSS": rss, "AIC": aic,
            "m": m, "p": 3}


def judge_direction(dname, pts):
    fitpts = [s for s in pts if s["in_fit"]]
    x = np.array([s["kabs"] for s in fitpts])
    y = np.array([s["resid_max"] for s in fitpts])
    m0 = fit_constant(x, y)
    m1 = fit_power(x, y)
    daic = m0["AIC"] - m1["AIC"]                            # >0 => power better
    winner = m1 if m1["AIC"] < m0["AIC"] else m0
    decisive = bool(abs(daic) >= DAIC_DECISIVE)
    a_win = winner["A"]
    sig_win = winner["sigma_A"]
    pass_d = bool(winner is m1 and decisive and m1["alpha"] > 0.0
                  and abs(m1["A"]) <= 2.0 * m1["sigma_A"])
    fail_d = bool(abs(a_win) >= A_O1_THRESH and abs(a_win) > 2.0 * sig_win)
    verdict = "FAIL" if fail_d else ("PASS" if pass_d else "ambiguous")
    # secondary robustness fits (reported, never deciding)
    ymean = np.array([s["resid_mean"] for s in fitpts])
    sec = {"constant": fit_constant(x, ymean), "power": fit_power(x, ymean)}
    sec["dAIC_const_minus_power"] = sec["constant"]["AIC"] - sec["power"]["AIC"]
    return {
        "direction": dname,
        "n_fit_points": len(fitpts),
        "fit_kabs": [float(v) for v in x],
        "fit_resid_max": [float(v) for v in y],
        "constant_model": m0,
        "power_model": m1,
        "dAIC_const_minus_power": daic,
        "winner": winner["model"],
        "decisive": decisive,
        "PASS_d": pass_d,
        "FAIL_d": fail_d,
        "verdict": verdict,
        "secondary_resid_mean_fits": sec,
    }


def make_figure(data, judges):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8), sharey=True)
    mk = {16: "o", 24: "s", 32: "^", 48: "D"}
    col = {16: "#1f77b4", 24: "#ff7f0e", 32: "#2ca02c", 48: "#d62728"}
    for ax, (dname, pts) in zip(axes, data.items()):
        J = next(j for j in judges if j["direction"] == dname)
        seenL = set()
        for s in pts:
            if s.get("off_band"):
                continue
            L0, n0 = s["provenance"][0]
            if not s["in_fit_window"]:
                ax.plot(s["kabs"], s["resid_max"], ".", color="0.65", ms=6,
                        zorder=1)
                continue
            face = "none" if s["excluded_k0_neighbour"] else col[L0]
            lab = None
            if L0 not in seenL:
                seenL.add(L0)
                lab = "L=%d" % L0
            ax.plot(s["kabs"], s["resid_max"], mk[L0], mec=col[L0], mfc=face,
                    ms=7, label=lab, zorder=3)
        xs = np.linspace(min(s["kabs"] for s in pts if s["in_fit"]) * 0.3,
                         max(s["kabs"] for s in pts if s["in_fit"]) * 1.05, 200)
        m1 = J["power_model"]; m0 = J["constant_model"]
        ax.plot(xs, m1["A"] + m1["B"] * xs ** m1["alpha"], "-", color="0.2",
                lw=1.4, label="power A+B|k|^a", zorder=2)
        ax.axhline(m0["A"], color="0.5", ls="--", lw=1.0, label="constant A0")
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title("%s  [%s]\nA=%.4f±%.4f  B=%.3f  α=%.2f  ΔAIC=%.1f" % (
            dname, J["verdict"], m1["A"], m1["sigma_A"], m1["B"], m1["alpha"],
            J["dAIC_const_minus_power"]), fontsize=9)
        ax.set_xlabel("|k| (lattice rad)")
        ax.legend(fontsize=6.5, loc="upper left")
    axes[0].set_ylabel("resid-outside-kerC (max over +ω modes)")
    fig.suptitle("R37 (c)-half residual scaling audit: rc3ii +ω resid vs |k|, "
                 "lattices 16³/24³/32³/48³ pooled per ray (hollow = k=0-neighbour, "
                 "excluded from fit; grey = context outside preregistered window)",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110)
    plt.close(fig)


def main():
    t0 = time.time()
    payload = {
        "register": "R37 (c)-half residual scaling audit (预注册 (c) 半补丁, 行动计划阶段 1)",
        "status": "RUNNING", "backend": "numpy",
        "question": ("is the rc3ii R3 pricing delta=12-18% (+w resid-outside-kerC, "
                     "fixed 16^3) an O(1) constant or a finite-size quantity?"),
        "protocol": {
            "lattices": LATTICES,
            "rays": {k: list(v) for k, v in DIRS.items()},
            "fit_window": "per-component k = 2*pi*n/L <= pi/4 (n/L <= 1/8)",
            "context_window": "pi/4 < comp <= pi/2 recorded, never fitted",
            "primary_observable": "resid_max(k) = max over +w mode columns (rc3ii path)",
            "exclusion": "pooled point enters fit only with >=1 n>=2 provenance; "
                         "each lattice's n=1 raw reading reported verbatim",
            "models": "M0 resid=A0 (p=1) vs M1 resid=A+B|k|^alpha (p=3, alpha grid "
                      "0.05..4.00 step 0.01)",
            "criterion": "AIC = m*ln(RSS/m)+2p; winner=lower AIC; decisive |dAIC|>=2",
            "PASS_d": "M1 decisive AND alpha>0 AND |A|<=2 sigma_A",
            "FAIL_d": "|A_win|>=0.05 (=SV_THRESH) AND |A_win|>2 sigma_A_win",
            "branch": "any FAIL_d -> C-FAIL; all PASS_d -> C-PASS; else ambiguous",
        },
        "params": {"mu": MU0, "theta0": TH0, "c0": C0, "sv_thresh": SV_THRESH},
        "memory_note": ("48^3 feasible: (c)-path is per-k spectral (28x28 eig), "
                        "no L^3 array anywhere; included."),
        "red_lines": ("pure measurement; no gate/threshold touched; (a)(b) are R36's; "
                      "C-PASS does not flip (b) FAIL; C-FAIL is a signal upgrade not "
                      "a theorem; frozen inputs read-only; fp64; 卡点④ held."),
    }
    write_json(payload)

    print("R37 (c)-half residual scaling audit")
    print("=" * 74)

    # -- certificate 1: frozen-input hashes bit-for-bit vs rc3ii record
    hashes = {f: sha256_file(os.path.join(DIR, f)) for f in RC3II_HASHES}
    hash_ok = hashes == RC3II_HASHES
    payload["frozen_inputs_sha256"] = hashes
    payload["frozen_hash_match_rc3ii"] = bool(hash_ok)
    print("[cert1] frozen hashes vs rc3ii record: %s" % ("MATCH" if hash_ok else "MISMATCH"))
    write_json(payload)
    if not hash_ok:
        payload["status"] = "ABORT-frozen-hash-mismatch"
        write_json(payload)
        return

    # -- certificate 2: RC1a faithfulness
    cert = RC.faithfulness_certificate()
    payload["faithfulness_certificate"] = cert
    print("[cert2] RC1a faithfulness: walk %.1e K %.1e map %.1e -> %s" % (
        cert["walk_symbol_max_diff"], cert["K_state_max_diff"],
        cert["damped_map_max_diff"], "PASS" if cert["PASS"] else "FAIL"))
    write_json(payload)
    if not cert["PASS"]:
        payload["status"] = "ABORT-faithfulness-failed"
        write_json(payload)
        return

    # -- certificate 3: 16^3 calibration vs rc3ii readings
    calib = {}
    calib_ok = True
    for kl, (lo, hi) in RC3II_CALIB.items():
        k = np.array(kl, float) * (2 * np.pi / 16)
        resid = resid_plus_modes(k, C0)
        dlo = abs(float(resid.min()) - lo)
        dhi = abs(float(resid.max()) - hi)
        ok = bool(dlo <= 1e-12 and dhi <= 1e-12)
        calib_ok = calib_ok and ok
        calib[str(kl)] = {"resid_min": float(resid.min()),
                          "resid_max": float(resid.max()),
                          "diff_vs_rc3ii": [dlo, dhi], "ok": ok}
        print("[cert3] calib %s: diff (%.1e, %.1e) %s" % (kl, dlo, dhi,
                                                          "OK" if ok else "BAD"))
    payload["calibration_16cube_vs_rc3ii"] = calib
    write_json(payload)
    if not calib_ok:
        payload["status"] = "ABORT-calibration-mismatch"
        write_json(payload)
        return

    # -- measurement: three rays, pooled lattices
    data = {}
    for dname, dvec in DIRS.items():
        print("[scan] %s ray ..." % dname)
        data[dname] = collect_direction(dname, dvec)
    payload["ray_data"] = data
    write_json(payload)

    # -- per-lattice minimum-|k| raw readings (must-report)
    min_k_raw = {}
    for dname, pts in data.items():
        rows = {}
        for L in LATTICES:
            s = next(p for p in pts if [L, 1] in p["provenance"])
            rows["L=%d" % L] = {
                "kabs": s["kabs"], "resid_min": s.get("resid_min"),
                "resid_max": s.get("resid_max"), "resid_mean": s.get("resid_mean"),
                "leak_max": s.get("leak_max"), "leak_mean": s.get("leak_mean")}
        min_k_raw[dname] = rows
    payload["min_k_raw_readings"] = min_k_raw
    write_json(payload)
    print("[raw] minimum-|k| readings (resid_max):")
    for dname, rows in min_k_raw.items():
        print("    %s: %s" % (dname, "  ".join(
            "%s |k|=%.3f max=%.4f" % (Lk, v["kabs"], v["resid_max"])
            for Lk, v in rows.items())))

    # -- preregistered fits + branch
    judges = [judge_direction(d, pts) for d, pts in data.items()]
    payload["direction_fits"] = judges
    for J in judges:
        m1 = J["power_model"]
        print("[fit] %-14s m=%d  A=%.4f±%.4f  B=%.3f±%.3f  α=%.2f±%.2f  "
              "ΔAIC(const-pow)=%.1f  winner=%s  -> %s" % (
                  J["direction"], J["n_fit_points"], m1["A"], m1["sigma_A"],
                  m1["B"], m1["sigma_B"], m1["alpha"], m1["sigma_alpha"],
                  J["dAIC_const_minus_power"], J["winner"], J["verdict"]))
    write_json(payload)

    fails = [J["direction"] for J in judges if J["FAIL_d"]]
    passes = [J["direction"] for J in judges if J["PASS_d"]]
    ambig = [J["direction"] for J in judges if J["verdict"] == "ambiguous"]
    if fails:
        branch = "C-FAIL"
    elif len(passes) == len(judges):
        branch = "C-PASS"
    else:
        branch = "ambiguous"
    payload["branch"] = branch
    payload["branch_detail"] = {
        "PASS_directions": passes, "FAIL_directions": fails,
        "ambiguous_directions": ambig,
        "meaning": {
            "C-PASS": "delta=12-18% is a finite-size quantity; vanishes in the "
                      "limit language.  Does NOT flip R36's (b) FAIL: seal branch "
                      "stands; boundary statement must note the residual is not "
                      "the killer (counting + stability deadlock is).",
            "C-FAIL": "residual is an O(1) constant cost; structural-unreachability "
                      "signal UPGRADED (still a signal, not a theorem).",
            "ambiguous": "named direction(s) unresolved; report what is missing.",
        }[branch],
    }
    write_json(payload)

    make_figure(data, judges)
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
    print("BRANCH = %s   (PASS: %s | FAIL: %s | ambiguous: %s)" % (
        branch, passes, fails, ambig))
    print("source  sha256 = %s" % payload["source_sha256"])
    print("results sha256 = %s" % jsha)
    print("total %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
