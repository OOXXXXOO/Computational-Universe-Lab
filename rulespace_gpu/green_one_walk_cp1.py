"""green_one_walk_cp1 -- M2'-CP1 (lane B): add R15's Yee-staggered de-Donder to
the R14 graviton-walk kernel and MEASURE whether the DOF half closes (N_prop=2)
while keeping CP0's light-cone half (c_gw == c_matter).

DECISIVE SINGLE-POINT CHECK (not full M3 assembly).  CP0 established the light
cone half is green (walk propagator: c_gw == c_matter exactly, doubler-free) but
the DOF half stuck at N_prop=[5,6,5,5] with a CENTRAL-difference de-Donder that
slaves the 4 hbar_{0nu} rows.  R15 (定理笔记-R15-walk交错去唐纳.md, certified
symbolically in r15_walk_dedonder.py) says: on the WALK shell
    sin^2(w/2) = c^2 sum_i sin^2(k_i/2)
the de-Donder surface {C=0} equals TT (+) gauge if and only if the constraint
symbol vector kappa is exactly eta_c-NULL, which happens iff the 10 components
are Yee-placed at x + (e_mu + e_nu)/2 so the forward-difference symbols become
the PURE half-angle
    kappa_0 = 2 sin(w/2)/c ,  kappa_i = 2 sin(k_i/2)   (kappa . kappa = 0 exact).

CENTRAL kicks give |kappa.kappa| ~ 0.035 (dim ker/gauge = 6), naive FORWARD
kicks give ~0.52 (dim = 6) -- BOTH negative controls (r15).  Only the *placed*
(half-phase absorbed) kappa gives dim(ker/gauge)=2.

WHAT THIS FILE MEASURES (honest scope):
  1. baseline central de-Donder (CP0 reproduction, all 4 rows)  -> N_prop
  2. naive forward-difference de-Donder (no half-cell placement) -> N_prop
  These are the two REAL-SPACE first-difference stencils realizable on the
  integer array.  For EACH, an r15 symbol self-check reports the constraint's
  |kappa.kappa| on the walk shell and dim(ker C / gauge) at the actual test k --
  the theory arbiter, computed with r15_walk_dedonder (read-only import).
  3. FALSIFICATION theta_g != theta_matter -> J5 must FAIL (inherits CP0).
  4. FALSIFICATION / k-vs-kappa: recount N_prop with a kappa-direction Riemann
     kernel (local, does NOT touch emergence_judge.judge_dof) and compare to the
     stock (k-direction) count, to test R15 four.6's warning that using k not
     kappa mis-judges at large k.

HONEST NOTE (declared): a pure half-angle symbol kappa_i = 2 sin(k_i/2) is NOT a
real-space first-difference stencil on an integer lattice (that needs a genuine
half-cell staggered grid -- the placement).  So the two stencils here are
r15's negative controls by construction; this driver measures HOW FAR each is
from N_prop=2 and localizes the obstruction, it does not itself synthesize the
placement.  Whether the walk's own substep midpoints can realize the placement
is the open design question surfaced to the main loop.

Run:  RULESPACE_BACKEND=numpy python -m rulespace_gpu.green_one_walk_cp1
      -> green_one_walk_cp1_results.json
"""
import argparse
import importlib.util
import json
import math
import os

import numpy as np

from . import backend as B
from . import emergence_judge as ej
from . import green_one_walk as gw

DIR = os.path.dirname(os.path.abspath(__file__))
PK = ej.PK
IDX10 = ej.IDX10
NU0_ROWS = gw.NU0_ROWS

# ---- r15 symbol certificate (READ-ONLY import of the repo-root module) -------
_r15_path = os.path.join(DIR, "..", "experiments", "r15_walk_dedonder.py")
_spec = importlib.util.spec_from_file_location("r15_walk_dedonder", _r15_path)
r15 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r15)


# ==========================================================================
#  spatial difference calculi (the ONLY realizable real-space first diffs)
# ==========================================================================
def _diff_central(f, j):
    ax = j - 4
    return 0.5 * (np.roll(f, -1, ax) - np.roll(f, 1, ax))    # symbol i sin k


def _diff_forward(f, j):
    ax = j - 4
    return np.roll(f, -1, ax) - f                            # symbol e^{ik}-1


def _diff_backward(f, j):
    ax = j - 4
    return f - np.roll(f, 1, ax)                             # symbol 1-e^{-ik}


CALCULI = {"central": _diff_central, "forward": _diff_forward,
           "backward": _diff_backward}

# map each real-space calculus to its r15 symbol-certificate kappa fn
R15_KAPPA = {"central": r15.kappa_central,     # sin(w)/c, sin(k_i)   -> null 0.035
             "forward": r15.kappa_unplaced,    # forward w/o placement -> null 0.52
             "backward": r15.kappa_unplaced,   # backward: same |symbol| structure
             "placed": r15.kappa_placed}       # IDEAL (half-cell): null ~ 0


# ==========================================================================
#  CP1 rule: walk geometry + configurable de-Donder, ALL 4 rows slaved
# ==========================================================================
def make_walk_geom_rule_cp1(th0=math.pi / 3.0, gamma=0.5, calculus="forward",
                            time_mode="halfangle", c_metric_th=None):
    """R14 graviton-walk geometry + R15-style de-Donder damping.

    calculus   : spatial difference used in the constraint ("central"=CP0,
                 "forward"/"backward"=naive placed attempts).
    time_mode  : "central" (CP0, h(t+1)-h(t-1) symbol sin w) or "halfangle"
                 (forward h(t+1)-h(t) symbol 2 sin(w/2)).
    All 4 hbar_{0nu} rows are slaved by the 4 constraints C_nu = 0.
    """
    c2 = math.cos(th0) ** 2
    c2m = c2 if c_metric_th is None else math.cos(c_metric_th) ** 2
    diff = CALCULI[calculus]
    if time_mode == "central":
        fac = 1.0 / (1.0 + gamma / (2.0 * c2m))
        tfac = 2.0                       # h_prev/(2 c^2)
    else:                                # halfangle forward time
        fac = 1.0 / (1.0 + gamma / c2m)
        tfac = 1.0                       # h_time_prev/(c^2)
    cache = {"last": None, "chi": None, "h0_prev": None}

    def step(state):
        h = state[0]
        if cache["last"] is not h:
            cache["chi"] = gw.seed_chi(h)
            cache["h0_prev"] = gw.chi_to_hbar(cache["chi"])
        chi = cache["chi"]
        chi = gw.geom_walk_all(chi, th0, th0, th0, th0)
        hbar = gw.chi_to_hbar(chi)                        # tentative new field
        h0_prev = cache["h0_prev"]
        for nu in range(4):
            c0 = PK[(0, nu)]
            S = np.zeros(hbar.shape[:-1])
            for j in (1, 2, 3):
                S = S + diff(hbar[..., PK[(j, nu)]], j)
            hbar[..., c0] = fac * (hbar[..., c0]
                                   + gamma * (h0_prev[..., c0] / (tfac * c2m) + S))
        for c0 in NU0_ROWS:
            chi[c0, ..., 0] = hbar[..., c0] + 1j * np.imag(chi[c0, ..., 0])
        cache["h0_prev"] = hbar
        cache["chi"] = chi
        out = (hbar, h0_prev)
        cache["last"] = out[0]
        return out

    tag = f"walk-geom CP1 de-Donder[{calculus}/{time_mode}] all-4-rows"
    return {"name": tag, "n_levels": 2, "cg2": c2, "step": step}


# ==========================================================================
#  r15 SYMBOL SELF-CHECK: the theory arbiter for each calculus
# ==========================================================================
def symbol_selfcheck(calculus, kmodes, N=16):
    """For each test k, report the constraint symbol's |kappa.kappa| on the walk
    shell and dim(ker C / gauge), computed with r15 (read-only).  This predicts
    N_prop: dim(ker/gauge)=2 <=> N_prop can be 2; =6 <=> gauge NOT quotiented."""
    kfn = R15_KAPPA[calculus]
    rows = []
    for m in kmodes:
        k = np.array(m, float) * (2 * np.pi / N)
        kap = kfn(k)
        if kap is None:
            rows.append({"k": list(m), "on_shell": False})
            continue
        null, cg, rank, dker, dimq, dtt = r15.analyze(kap)
        rows.append({"k": list(m), "on_shell": True,
                     "kappa_dot_kappa": float(null), "rank_C": int(rank),
                     "dim_ker_over_gauge": int(dimq)})
    return rows


# ==========================================================================
#  kappa-direction Riemann recount (k-vs-kappa falsification; local, no
#  emergence_judge edit -> strictly backward compatible)
# ==========================================================================
def _riemann_series_k_dir(H44, kvec, sdir):
    """riemann_series_k but with spatial symbol i*sdir[j] instead of i*sin(k_j).
    sdir = k-direction (sin k_j) reproduces ej.riemann_series_k; sdir = kappa
    (2 sin(k_j/2)) is the half-angle direction R15 four.4 asks for."""
    s = [None, 1j * sdir[0], 1j * sdir[1], 1j * sdir[2]]

    def D(f, mu):
        if mu == 0:
            out = np.zeros_like(f)
            out[1:-1] = 0.5 * (f[2:] - f[:-2])
            return out
        return s[mu] * f

    T = H44.shape[0]
    G = [[D(D(H44, nu), mu) for nu in range(4)] for mu in range(4)]
    R = np.zeros((T, 4, 4, 4, 4), dtype=complex)
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    R[:, m, a, n, b] = 0.5 * (
                        G[a][n][:, m, b] + G[m][b][:, a, n]
                        - G[a][b][:, m, n] - G[m][n][:, a, b])
    return R[2:-2].reshape(T - 4, 256)


def recount_kappa(rule, kmodes, N=16, T=512, trials=8, seed=1):
    """Re-run judge_dof's counting pipeline but measure the Riemann-SVD rank with
    BOTH the stock k-direction kernel and the kappa (half-angle) kernel, to test
    whether the projection-free COUNT itself is sensitive to k-vs-kappa."""
    step, nlev, c2 = rule["step"], rule["n_levels"], float(rule["cg2"])
    rng = np.random.default_rng(seed)
    state = tuple(rng.standard_normal((trials, N, N, N, 10)) for _ in range(nlev))
    kvecs = [np.array(v, float) * (2 * np.pi / N) for v in kmodes]
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    phases = np.stack([np.exp(-1j * (k[0] * X + k[1] * Y + k[2] * Z)) / N ** 3
                       for k in kvecs])
    rec = np.zeros((T, trials, len(kvecs), 10), dtype=complex)
    for t in range(T):
        state = step(state)
        rec[t] = np.einsum("kxyz,rxyzc->rkc", phases, state[0])
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    freqs = 2 * np.pi * np.fft.fftfreq(W - 4)
    sel = (freqs > max(0.05, 4 * np.pi / (W - 4))) & (freqs <= np.pi / 2)
    out = []
    for ki, kvec in enumerate(kvecs):
        entry = {"k": list(kmodes[ki])}
        for name, sdir in (("k_dir", np.array([np.sin(kk) for kk in kvec])),
                           ("kappa_dir",
                            np.array([2 * np.sin(kk / 2) for kk in kvec]))):
            rows, pow_spec = [], None
            for r in range(trials):
                Hh = ej.trace_reverse_c(rec[T0:, r, ki, :], c2)
                Rf = _riemann_series_k_dir(ej.packed_to_44(Hh), kvec, sdir)
                F = np.fft.fft(Rf * win[2:-2, None], axis=0)
                P = np.sum(np.abs(F) ** 2, axis=1)
                pow_spec = P if pow_spec is None else pow_spec + P
                rows.append(F)
            if float(pow_spec[sel].sum()) < 1e-18:
                entry[name] = {"n_prop": 0}
                continue
            pk = int(np.argmax(np.where(sel, pow_spec, 0)))
            M = np.array([r[pk] for r in rows])
            _, sv, _ = np.linalg.svd(M, full_matrices=False)
            svn = (sv / (sv[0] + 1e-300)).tolist()
            entry[name] = {"n_prop": int(np.sum(np.array(svn) > ej.SV_THRESH)),
                           "sv": [float(v) for v in svn[:8]]}
        out.append(entry)
    return out


# ==========================================================================
#  CP1 driver
# ==========================================================================
def _per_k(a, cm, kmodes):
    rows = []
    for e, m in zip(a["per_k"], kmodes):
        cmat = cm[str(tuple(m))]["c_matter"]
        cgw = e.get("v_meas", float("nan"))
        ratio = (cgw / cmat) if (np.isfinite(cgw) and cmat > 1e-9) else float("nan")
        rows.append({"k": list(m), "n_prop": e["n_prop"], "c_gw": cgw,
                     "c_matter": cmat, "ratio": ratio, "w_peak": e.get("w_peak"),
                     "sv": e.get("sv"), "tt_match": e.get("tt_match")})
    return rows


def run_cp1(N=16, T=512, trials=8, th0=math.pi / 3.0, gamma=0.5):
    kmodes = ((2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2))
    iso_modes = ((2, 0, 0), (0, 2, 0), (0, 0, 2))
    c0 = math.cos(th0)
    out = {"backend": B.NAME, "th0": th0, "c_matter_costh": c0, "gamma": gamma,
           "N": N, "T": T, "trials": trials, "kmodes": [list(m) for m in kmodes],
           "cp0_reference": {"n_prop_all": [5, 6, 5, 5], "note": "从 CP0 json"}}

    cm = gw.c_matter_table(th0, kmodes, N=N, T=T)
    out["c_matter_ref"] = cm

    # -- r15 symbol certificate for the three realizable calculi + the ideal ---
    out["r15_symbol_selfcheck"] = {
        cal: symbol_selfcheck(cal, kmodes, N=N)
        for cal in ("placed", "central", "forward")}

    # -- MAIN candidate calculi: central (=CP0) and forward (naive placed) -----
    out["candidates"] = {}
    for cal, tmode in (("central", "central"), ("forward", "halfangle")):
        rule = make_walk_geom_rule_cp1(th0=th0, gamma=gamma, calculus=cal,
                                       time_mode=tmode)
        a = ej.judge_dof(rule, N=N, T=T, trials=trials, kmodes=kmodes)
        per_k = _per_k(a, cm, kmodes)
        j5 = max((abs(p["ratio"] - 1.0) for p in per_k if np.isfinite(p["ratio"])),
                 default=float("nan"))
        a_iso = ej.judge_dof(rule, N=N, T=T, trials=trials, kmodes=iso_modes)
        vs = [e["v_meas"] for e in a_iso["per_k"]
              if np.isfinite(e.get("v_meas", np.nan))]
        iso = (float((max(vs) - min(vs)) / (np.mean(vs) + 1e-30))
               if len(vs) >= 2 else float("nan"))
        out["candidates"][cal] = {
            "time_mode": tmode, "n_prop_all": a["n_prop_all"],
            "stable": bool(a["stable"]), "rms_growth": a["rms_growth"],
            "j5_max_dev": j5, "isotropy_spread": iso, "per_k": per_k,
            "N_prop_all_eq_2": bool(all(n == 2 for n in a["n_prop_all"])),
            "J5_within_1e-2": bool(np.isfinite(j5) and j5 < 1e-2)}

    # -- FALSIFICATION 1: theta_g != theta_matter (double cone -> J5 FAIL) -----
    th_wrong = 0.9
    rule_f1 = make_walk_geom_rule_cp1(th0=th_wrong, gamma=gamma,
                                      calculus="forward", time_mode="halfangle")
    a_f1 = ej.judge_dof(rule_f1, N=N, T=T, trials=trials, kmodes=kmodes)
    f1_ratios = []
    for e, m in zip(a_f1["per_k"], kmodes):
        cmat = cm[str(tuple(m))]["c_matter"]           # matter ref at th0
        cgw = e.get("v_meas", float("nan"))
        if np.isfinite(cgw) and cmat > 1e-9:
            f1_ratios.append(cgw / cmat)
    f1_dev = max((abs(r - 1.0) for r in f1_ratios), default=float("nan"))
    out["falsify_double_cone"] = {
        "th_geom": th_wrong, "th_matter_ref": th0, "ratios": f1_ratios,
        "j5_max_dev": f1_dev,
        "J5_FAILS": bool(np.isfinite(f1_dev) and f1_dev > 1e-2),
        "note": "geometry cone cos(0.9)=%.4f vs matter cos(pi/3)=%.4f"
                % (math.cos(th_wrong), c0)}

    # -- FALSIFICATION 2 / k-vs-kappa: is the projection-free COUNT sensitive? --
    rule_fwd = make_walk_geom_rule_cp1(th0=th0, gamma=gamma, calculus="forward",
                                       time_mode="halfangle")
    out["k_vs_kappa_recount"] = recount_kappa(rule_fwd, kmodes, N=N, T=T,
                                              trials=trials)

    # -- CONTROL: no-damping 10x free walk (expect N_prop=6) -------------------
    rule_c = make_walk_geom_rule_cp1(th0=th0, gamma=0.0, calculus="central",
                                     time_mode="central")
    # gamma=0 disables damping via the fac/gamma multipliers -> pure 10x walk
    a_c = ej.judge_dof(rule_c, N=N, T=T, trials=trials, kmodes=kmodes)
    out["control_no_damping"] = {"n_prop_all": a_c["n_prop_all"],
                                 "stable": bool(a_c["stable"])}
    return out


def _fmt(x):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "  nan  "
    return f"{x:8.4f}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(
        DIR, "..", "data", "results", "green_one_walk_cp1_results.json"))
    ap.add_argument("--N", type=int, default=16)
    ap.add_argument("--T", type=int, default=512)
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--gamma", type=float, default=0.5)
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING: backend={B.NAME}; run RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("M2'-CP1 -- R15 Yee-staggered de-Donder on the R14 walk kernel\n")

    out = run_cp1(N=args.N, T=args.T, trials=args.trials, gamma=args.gamma)
    th0 = out["th0"]
    print(f"theta_g = theta_matter = {th0:.6f}  (c = {out['c_matter_costh']:.4f})"
          f"   gamma = {out['gamma']}\n")

    print("[r15 SYMBOL SELF-CHECK]  dim(ker C/gauge)=2 <=> DOF half CAN close")
    print(f"  {'calculus':10s} {'k':12s} {'|kappa.kappa|':>14} {'dim(ker/gauge)':>15}")
    for cal in ("placed", "central", "forward"):
        for r in out["r15_symbol_selfcheck"][cal]:
            if not r.get("on_shell"):
                continue
            print(f"  {cal:10s} {str(tuple(r['k'])):12s} "
                  f"{r['kappa_dot_kappa']:>14.3e} {r['dim_ker_over_gauge']:>15d}")
    print("  (placed = IDEAL half-cell; central = CP0; forward = naive stencil)\n")

    for cal, c in out["candidates"].items():
        print(f"[CANDIDATE de-Donder = {cal} / time={c['time_mode']}]")
        print(f"  {'k':12s} {'N_prop':>6} {'c_gw':>9} {'c_matter':>9} {'ratio':>8}")
        for p in c["per_k"]:
            print(f"  {str(tuple(p['k'])):12s} {p['n_prop']:>6} "
                  f"{_fmt(p['c_gw'])} {_fmt(p['c_matter'])} {_fmt(p['ratio'])}")
        print(f"  N_prop_all={c['n_prop_all']}  stable={c['stable']}  "
              f"J5 max|r-1|={c['j5_max_dev']:.3e}  iso={c['isotropy_spread']:.4f}")
        print(f"  -> N_prop==2 all k: {c['N_prop_all_eq_2']}   "
              f"J5<1e-2: {c['J5_within_1e-2']}\n")

    print("FALSIFICATION CANNON:")
    fc = out["falsify_double_cone"]
    print(f"  [c] theta_g != theta_matter: {fc['note']}")
    print(f"      J5 max|r-1| = {fc['j5_max_dev']:.3e} -> "
          f"{'J5 FAILS as required' if fc['J5_FAILS'] else 'DID NOT FAIL (toothless!)'}")
    print("  [b] k-vs-kappa projection-free recount (does the COUNT change?):")
    for r in out["k_vs_kappa_recount"]:
        kd = r.get("k_dir", {}).get("n_prop")
        ka = r.get("kappa_dir", {}).get("n_prop")
        print(f"      k={tuple(r['k'])}: N_prop(k_dir)={kd}  N_prop(kappa_dir)={ka}")
    cc = out["control_no_damping"]
    print(f"  [ctrl] no-damping 10x walk: N_prop = {cc['n_prop_all']} (expect 6)")

    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: (
            o.tolist() if isinstance(o, np.ndarray) else float(o)))
    print(f"\nwrote {os.path.abspath(args.json)}")
