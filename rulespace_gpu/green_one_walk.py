"""green_one_walk -- M2'-CP0 (lane B): the R14 GRAVITON-WALK geometry kernel.

DECISIVE SINGLE-POINT CHECK (not a full M3 assembly).  Question: does letting
GEOMETRY propagate by the SAME split-step walk operator as matter (R14) remove
the "wide-box vs light-cone" obstruction that lane B confirmed structural
(小报告-J5宽盒vs光锥)?  The obstruction: with the stride-2 WIDE null box, a
LIGHT-CONE graviton (c_gw -> c_matter) requires sub-cycling, which WAKES the
stride-2 doubler -> N_prop = 5-6 (wrong DOF).  Correct DOF (N_prop = 2) only
survives with a SLOW graviton (c_gw = 0.5 c_matter).  Two cones = EP breaking.

R14 ESCAPE (spec: 定理笔记-R14-引力子行走核.md, certified 1D in
r14_graviton_walk_kernel.py):  a one-step UNITARY stride-1 split-step operator
has EXACTLY 2 bands on the whole BZ -- no mirror/doubler sector to wake.  Let
each of the 10 tensor components c carry a 2-spinor chi_c evolved by the
matter walk U_walk(theta_g), theta_g = theta_matter:

    chi_c(t+1) = U_walk(theta_g) chi_c(t)      (CP0: source eps = 0)
    hbar_c     = Re(chi_c[..., 0])             (the packed-10 field the judge reads)

Then c_gw == c_matter BY CONSTRUCTION (identical operator, identical
dispersion, identical lattice artifacts -- R14 C1), and the geometry sector is
doubler-free (R14 C2).

CONSTRAINT / non-TT sector (R14 four.3): the 10 free walks alone carry
N_prop = 6 (10 - 4 gauge); the non-physical non-TT curvature carriers must be
removed by de-Donder constraint damping DONE IN THE WALK's OWN CALCULUS -- NOT
a full-angle E_munu constraint surface (that mismatch is 43f's N_prop=5 root).
Here: lag-free de-Donder slaving of the hbar_{0nu} rows using the walk light
speed c = cos(theta_g); TT lives entirely in the spatial hbar_{ij} rows and is
never touched.  This mirrors ej.make_rule_null_damped's positive-control
damping, but with the WALK (not the wide box) as the propagator.

HONEST INTERPRETATION NOTE (declared, not hidden): R14 four.3 specifies
"diagonal (1-gamma) per-step, no-lag, in the walk frame" but does NOT pin the
exact algebra of the walk-calculus de-Donder on the complex chi field -- R14
five explicitly defers "10-component assembly + emergence judge" to M2'/M3
experiment.  The construction below is THIS agent's realization: (a) walk all
10 chi components, (b) lag-free de-Donder solve on the 0nu rows using the
walk's light speed, (c) fold the corrected 0nu value back into Re(chi_0nu).
Whether that realization suffices for N_prop=2 is exactly what CP0 measures --
so a stuck N_prop is a reportable negative result, not a bug to tune away.

Run:  RULESPACE_BACKEND=numpy python -m rulespace_gpu.green_one_walk
      -> green_one_walk_cp0_results.json
"""
import argparse
import json
import math
import os

import numpy as np

from . import backend as B
from . import emergence_judge as ej
from . import tensor_coin_feedback as tcf

DIR = os.path.dirname(os.path.abspath(__file__))
PK = ej.PK
IDX10 = ej.IDX10
_dsp = ej._dsp                       # central spatial diff, axis j-4 (full-angle)
_lap_wide = ej._lap_wide_batch

# 0nu rows (non-TT constraint sector, slaved) vs spatial rows (carry TT, free).
NU0_ROWS = [PK[(0, nu)] for nu in range(4)]          # 00,01,02,03
SPATIAL_ROWS = [PK[(i, j)] for i in (1, 2, 3) for j in range(i, 4)]  # 11..33


# ==========================================================================
#  PART 1.  the geometry walk: 10 tensor components, each a 2-spinor,
#           evolved by the MATTER split-step walk (tcf), theta_g = theta_matter
# ==========================================================================
def geom_walk_all(chi, thx, thy, thz, th0):
    """one macro walk step on chi shaped (10, ..., Nx, Ny, Nz, 2) complex.
    Reuses the matter per-axis sandwich (tcf._axis_sandwich, orient=1) so the
    dispersion is bit-identical to the matter walker's massless branch.
    Axis map: after chi[...,0] drops the spinor, spatial axes are (-3,-2,-1)."""
    Wx, Wy, Wz = tcf.axis_frames(th0)
    chi = tcf._axis_sandwich(chi, thx, -3, Wx, orient=1)
    chi = tcf._axis_sandwich(chi, thy, -2, Wy, orient=1)
    chi = tcf._axis_sandwich(chi, thz, -1, Wz, orient=1)
    return chi


def chi_to_hbar(chi):
    """chi (10, ..., Nx,Ny,Nz, 2) -> packed hbar (..., Nx,Ny,Nz, 10) = Re chi[...,0]."""
    return np.moveaxis(np.real(chi[..., 0]), 0, -1)


def seed_chi(h0):
    """generic random packed hbar (..., 10) -> chi with Re(chi_c[0]) = h0_c,
    Im and spinor-1 component zero (the walk immediately mixes them)."""
    chi = np.zeros((10,) + h0.shape[:-1] + (2,), dtype=complex)
    chi[..., 0] = np.moveaxis(h0, -1, 0)
    return chi


# ==========================================================================
#  PART 2.  the CP0 rule (emergence_judge-compatible): walk + walk-frame
#           de-Donder damping of the non-TT 0nu rows.  CP0: no source.
# ==========================================================================
def make_walk_geom_rule(th0=math.pi / 3.0, gamma=0.5, damping=True,
                        c_metric_th=None, wide_box_constraint=False,
                        cg2_box=None):
    """R14 graviton-walk geometry as a judge rule.

    th0            : the walk coin angle theta_g (= theta_matter).  c = cos th0.
    gamma          : de-Donder damping strength (the (1-gamma) knob; kappa).
    damping        : if False, pure 10x walk (expected N_prop = 6 control).
    c_metric_th    : light speed used in the de-Donder metric = cos(c_metric_th).
                     Default None -> = th0 (SHARED cone -> matches walk shell).
                     Falsification: set != th0 to feed a WRONG-angle constraint.
    wide_box_constraint : FALSIFICATION -- replace the walk-frame de-Donder with
                     a full-angle wide-box (stride-2) de-Donder surface applied
                     to the walk field (R14's forbidden 'full-angle constraint
                     with half-angle evolution' -> expected N_prop back to 5/6).
    """
    c2 = math.cos(th0) ** 2
    c2m = c2 if c_metric_th is None else math.cos(c_metric_th) ** 2
    fac = 1.0 / (1.0 + gamma / (2.0 * c2m))
    cache = {"last": None, "chi": None, "hbar_prev": None}

    def step(state):
        h = state[0]
        if cache["last"] is not h:
            cache["chi"] = seed_chi(h)
            cache["hbar_prev"] = chi_to_hbar(cache["chi"])
        chi = cache["chi"]
        chi = geom_walk_all(chi, th0, th0, th0, th0)
        hbar = chi_to_hbar(chi)                        # tentative new-time field

        if damping:
            hbar_prev = cache["hbar_prev"]
            if wide_box_constraint:
                # FALSIFICATION: full-angle wide-box de-Donder (stride-2 spatial
                # div) applied to the walk field -- the calculus MISMATCH R14
                # forbids.  Slaves 0nu with the stride-2 wide operator.
                for nu in range(4):
                    c0 = PK[(0, nu)]
                    S = np.zeros(hbar.shape[:-1])
                    for j in (1, 2, 3):
                        ax = j - 4
                        S = S + 0.5 * (np.roll(hbar[..., PK[(j, nu)]], -2, ax)
                                       - np.roll(hbar[..., PK[(j, nu)]], 2, ax))
                    hbar[..., c0] = fac * (hbar[..., c0]
                                          + gamma * (hbar_prev[..., c0] / (2 * c2m) + S))
            else:
                # walk-frame lag-free de-Donder on the 0nu rows (shared c metric).
                # C_nu = -(1/c^2) D0 hbar_0nu + D_j hbar_jnu ; slave hbar_0nu so
                # the update relaxes toward C_nu = 0 with strength gamma.
                for nu in range(4):
                    c0 = PK[(0, nu)]
                    S = np.zeros(hbar.shape[:-1])
                    for j in (1, 2, 3):
                        S = S + _dsp(hbar[..., PK[(j, nu)]], j)
                    hbar[..., c0] = fac * (hbar[..., c0]
                                          + gamma * (hbar_prev[..., c0] / (2 * c2m) + S))
            # fold the corrected 0nu rows back into Re(chi_0nu[0]); keep the
            # walk's momentum (imag + spinor-1) so propagation continues.
            for c0 in NU0_ROWS:
                chi[c0, ..., 0] = hbar[..., c0] + 1j * np.imag(chi[c0, ..., 0])
            cache["hbar_prev"] = hbar

        cache["chi"] = chi
        out = (hbar, cache["hbar_prev"] if cache["hbar_prev"] is not None else hbar)
        cache["last"] = out[0]
        return out

    tag = "walk-geom(R14)"
    if not damping:
        tag = "walk-geom NO-damp (10x free walk, expect Nprop=6)"
    elif wide_box_constraint:
        tag = "walk-geom + WIDE-BOX full-angle constraint (falsify)"
    elif c_metric_th is not None:
        tag = f"walk-geom theta_g!=theta_matter (falsify, c_metric={c_metric_th:.3f})"
    return {"name": tag, "n_levels": 2, "cg2": c2, "step": step}


# ==========================================================================
#  PART 3.  c_matter reference: the walk's OWN dispersion (same operator).
#  Measured by evolving a single-component plane wave with geom_walk_all and
#  reading the Re(chi[0]) phase frequency -> c_matter(k) = w_walk(k)/k_chord.
#  Since geometry uses the identical walk, this is c_matter for the ratio.
# ==========================================================================
def walk_omega(kvec, th0, N=16, T=512):
    """positive quasi-energy of the geometry/matter walk at lattice kvec, from a
    direct plane-wave evolution.  CRUCIAL: replicate judge_dof's EXACT spectral
    pipeline (second half T0=T//2, window length W-4, freq grid fftfreq(W-4)) so
    the raw-walk peak and the geometry Riemann peak land on the SAME FFT bin --
    otherwise the shared cone (ratio == 1 by construction) is masked by a ~2.5%
    binning artifact against the tight 1e-2 J5 bar."""
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    ph = np.exp(1j * (kvec[0] * X + kvec[1] * Y + kvec[2] * Z))
    chi = np.zeros((1, N, N, N, 2), dtype=complex)
    chi[0, ..., 0] = ph
    proj = np.conj(ph) / N ** 3
    rec = np.empty(T, dtype=complex)
    for t in range(T):
        chi = geom_walk_all(chi, th0, th0, th0, th0)
        rec[t] = np.sum(proj * chi[0, ..., 0])
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    seg = rec[T0:] * win
    seg = seg[2:-2]                                    # match riemann_series trim
    freqs = 2 * np.pi * np.fft.fftfreq(W - 4)
    sel = (freqs > max(0.05, 4 * np.pi / (W - 4))) & (freqs <= np.pi / 2)
    P = np.abs(np.fft.fft(seg)) ** 2
    w = abs(float(freqs[int(np.argmax(np.where(sel, P, 0.0)))]))
    return w


def kchord(kvec):
    return float(np.sqrt(sum(4.0 * np.sin(k / 2.0) ** 2 for k in kvec)))


def c_matter_table(th0, kmodes, N=16, T=512):
    out = {}
    for m in kmodes:
        kv = np.array(m, float) * (2 * np.pi / N)
        w = walk_omega(kv, th0, N=N, T=T)
        out[str(tuple(m))] = {"w_walk": w, "k_chord": kchord(kv),
                              "c_matter": w / (kchord(kv) + 1e-30)}
    return out


# ==========================================================================
#  PART 4.  CP0 driver
# ==========================================================================
def run_cp0(N=16, T=512, trials=8, th0=math.pi / 3.0, gamma=0.5):
    kmodes = ((2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2))
    iso_modes = ((2, 0, 0), (0, 2, 0), (0, 0, 2))
    c0 = math.cos(th0)
    out = {"backend": B.NAME, "th0": th0, "c_matter_costh": c0, "gamma": gamma,
           "N": N, "T": T, "trials": trials, "kmodes": [list(m) for m in kmodes]}

    # -- c_matter reference from the SAME walk operator --------------------
    cm = c_matter_table(th0, kmodes, N=N, T=T)
    out["c_matter_ref"] = cm

    # -- MAIN: R14 walk geometry (walk + walk-frame de-Donder) -------------
    rule = make_walk_geom_rule(th0=th0, gamma=gamma)
    a = ej.judge_dof(rule, N=N, T=T, trials=trials, kmodes=kmodes)
    per_k = []
    for e, m in zip(a["per_k"], kmodes):
        key = str(tuple(m))
        cmat = cm[key]["c_matter"]
        cgw = e.get("v_meas", float("nan"))
        ratio = (cgw / cmat) if (np.isfinite(cgw) and cmat > 1e-9) else float("nan")
        per_k.append({"k": list(m), "n_prop": e["n_prop"], "c_gw": cgw,
                      "c_matter": cmat, "ratio": ratio,
                      "w_peak": e.get("w_peak"), "sv": e.get("sv"),
                      "tt_match": e.get("tt_match")})
    out["main"] = {"n_prop_all": a["n_prop_all"], "stable": bool(a["stable"]),
                   "lightcone_ok": bool(a["lightcone_ok"]),
                   "speed_spread": a["speed_spread"],
                   "rms_growth": a["rms_growth"], "per_k": per_k}
    j5_dev = max(abs(p["ratio"] - 1.0) for p in per_k
                 if np.isfinite(p["ratio"])) if per_k else float("nan")
    out["main"]["j5_max_dev"] = j5_dev

    # -- isotropy: axis-aligned c_gw spread --------------------------------
    a_iso = ej.judge_dof(rule, N=N, T=T, trials=trials, kmodes=iso_modes)
    vs = [e["v_meas"] for e in a_iso["per_k"] if np.isfinite(e.get("v_meas", np.nan))]
    iso_spread = (float((max(vs) - min(vs)) / (np.mean(vs) + 1e-30))
                  if len(vs) >= 2 else float("nan"))
    out["isotropy"] = {"axis_c_gw": vs, "spread": iso_spread,
                       "n_prop_all": a_iso["n_prop_all"]}

    # -- FALSIFICATION 1: theta_g != theta_matter (double cone) ------------
    #    geometry walks at th0 but the de-Donder metric uses a WRONG angle, and
    #    we score the ratio against a c_matter computed at a DIFFERENT angle.
    th_wrong = 0.9                        # c=cos(0.9)=0.6216 vs cos(pi/3)=0.5
    rule_f1 = make_walk_geom_rule(th0=th0, gamma=gamma, c_metric_th=th_wrong)
    a_f1 = ej.judge_dof(rule_f1, N=N, T=T, trials=trials, kmodes=kmodes)
    # J5 with a genuinely different matter cone: geometry at th_wrong, matter ref
    # at th0 -> ratio = cos(th_wrong)/cos(th0) != 1 (two cones).
    rule_f1b = make_walk_geom_rule(th0=th_wrong, gamma=gamma)
    a_f1b = ej.judge_dof(rule_f1b, N=N, T=T, trials=trials, kmodes=kmodes)
    f1_ratios = []
    for e, m in zip(a_f1b["per_k"], kmodes):
        cmat = cm[str(tuple(m))]["c_matter"]        # matter ref at th0
        cgw = e.get("v_meas", float("nan"))
        if np.isfinite(cgw) and cmat > 1e-9:
            f1_ratios.append(cgw / cmat)
    f1_j5dev = max(abs(r - 1.0) for r in f1_ratios) if f1_ratios else float("nan")
    out["falsify_double_cone"] = {
        "th_geom": th_wrong, "th_matter_ref": th0,
        "n_prop_all_wrongmetric": a_f1["n_prop_all"],
        "ratios_geom_th_wrong_vs_matter_th0": f1_ratios,
        "j5_max_dev": f1_j5dev,
        "J5_FAILS": bool(np.isfinite(f1_j5dev) and f1_j5dev > 1e-2),
        "note": "geometry cone cos(0.9)=%.4f vs matter cone cos(pi/3)=%.4f"
                % (math.cos(th_wrong), c0)}

    # -- FALSIFICATION 2: full-angle wide-box constraint on the walk -------
    rule_f2 = make_walk_geom_rule(th0=th0, gamma=gamma, wide_box_constraint=True)
    a_f2 = ej.judge_dof(rule_f2, N=N, T=T, trials=trials, kmodes=kmodes)
    out["falsify_widebox_constraint"] = {
        "n_prop_all": a_f2["n_prop_all"], "stable": bool(a_f2["stable"]),
        "NPROP_NOT_2": bool(not all(n == 2 for n in a_f2["n_prop_all"])),
        "note": "full-angle stride-2 de-Donder surface with half-angle walk"}

    # -- CONTROL: 10x free walk, no damping (expected N_prop = 6) -----------
    rule_c = make_walk_geom_rule(th0=th0, gamma=gamma, damping=False)
    a_c = ej.judge_dof(rule_c, N=N, T=T, trials=trials, kmodes=kmodes)
    out["control_no_damping"] = {"n_prop_all": a_c["n_prop_all"],
                                 "stable": bool(a_c["stable"])}

    # -- verdict summary (NOT a pass claim; numbers for independent review) --
    m = out["main"]
    out["cp0_summary"] = {
        "N_prop_all": m["n_prop_all"],
        "N_prop_all_eq_2": bool(all(n == 2 for n in m["n_prop_all"])),
        "j5_max_dev": m["j5_max_dev"],
        "J5_within_1e-2": bool(np.isfinite(m["j5_max_dev"]) and m["j5_max_dev"] < 1e-2),
        "stable": m["stable"],
        "isotropy_spread": iso_spread,
        "isotropy_within_6pct": bool(np.isfinite(iso_spread) and iso_spread < 0.06),
        "falsify_double_cone_J5_FAILS": out["falsify_double_cone"]["J5_FAILS"],
        "falsify_widebox_NPROP_NOT_2": out["falsify_widebox_constraint"]["NPROP_NOT_2"],
    }
    return out


def _fmt(x):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "  nan  "
    return f"{x:8.4f}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "data", "results",
                                                    "green_one_walk_cp0_results.json"))
    ap.add_argument("--N", type=int, default=16)
    ap.add_argument("--T", type=int, default=512)
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--gamma", type=float, default=0.5)
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING: backend = {B.NAME}; group velocity is precision-"
              f"sensitive.  Run RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("M2'-CP0 -- R14 graviton-walk geometry kernel (lane B, single-point)\n")

    out = run_cp0(N=args.N, T=args.T, trials=args.trials, gamma=args.gamma)

    th0 = out["th0"]
    print(f"theta_g = theta_matter = {th0:.6f}  (c = cos theta = "
          f"{out['c_matter_costh']:.4f})   gamma = {out['gamma']}\n")

    print("MAIN: R14 walk geometry (walk + walk-frame de-Donder on 0nu rows)")
    print(f"  {'k':12s} {'N_prop':>6} {'c_gw':>9} {'c_matter':>9} {'ratio':>8} "
          f"{'|r-1|':>9}")
    for p in out["main"]["per_k"]:
        r = p["ratio"]
        dev = abs(r - 1.0) if np.isfinite(r) else float("nan")
        print(f"  {str(tuple(p['k'])):12s} {p['n_prop']:>6} {_fmt(p['c_gw'])} "
              f"{_fmt(p['c_matter'])} {_fmt(r)} {_fmt(dev)}")
    m = out["main"]
    print(f"  N_prop_all = {m['n_prop_all']}   stable = {m['stable']}   "
          f"J5 max|r-1| = {m['j5_max_dev']:.3e}   rms_growth = {m['rms_growth']:.2e}")
    iso = out["isotropy"]
    print(f"  isotropy: axis c_gw = {[round(v,4) for v in iso['axis_c_gw']]}  "
          f"spread = {iso['spread']:.4f}  (N_prop {iso['n_prop_all']})\n")

    print("FALSIFICATION CANNON (each MUST fail):")
    fc = out["falsify_double_cone"]
    print(f"  [1] theta_g != theta_matter (double cone): {fc['note']}")
    print(f"      N_prop(wrong metric) = {fc['n_prop_all_wrongmetric']}  "
          f"J5 max|r-1| = {fc['j5_max_dev']:.3e}  -> "
          f"{'J5 FAILS as required' if fc['J5_FAILS'] else 'DID NOT FAIL (toothless!)'}")
    fw = out["falsify_widebox_constraint"]
    print(f"  [2] full-angle wide-box constraint on walk: "
          f"N_prop = {fw['n_prop_all']}  -> "
          f"{'N_prop != 2 as required' if fw['NPROP_NOT_2'] else 'STILL 2 (toothless!)'}")
    cc = out["control_no_damping"]
    print(f"  [ctrl] no damping (10x free walk): N_prop = {cc['n_prop_all']}  "
          f"(expected 6)\n")

    s = out["cp0_summary"]
    print("=" * 72)
    print("CP0 SUMMARY (measured numbers -- NOT a pass claim; for main-loop review)")
    print(f"  emergence-A  N_prop=2 all k : {s['N_prop_all']}  -> {s['N_prop_all_eq_2']}")
    print(f"  J5  |c_gw/c_matter-1|<1e-2  : {s['j5_max_dev']:.3e}  -> {s['J5_within_1e-2']}")
    print(f"  stable                       : {s['stable']}")
    print(f"  isotropy spread < 6%%        : {s['isotropy_spread']:.4f}  -> {s['isotropy_within_6pct']}")
    print(f"  falsify double-cone J5 FAILS : {s['falsify_double_cone_J5_FAILS']}")
    print(f"  falsify widebox N_prop != 2  : {s['falsify_widebox_NPROP_NOT_2']}")

    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: (
            o.tolist() if isinstance(o, np.ndarray) else float(o)))
    print(f"\nwrote {os.path.abspath(args.json)}")
