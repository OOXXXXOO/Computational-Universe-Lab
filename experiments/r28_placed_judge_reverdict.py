"""R28 -- 卡点⑦ 三分便宜检验: re-judge the projection-free dynamical DOF count
with the Riemann differential SWAPPED from ideal (momentum = k) to PLACED kappa
(the walk-shell half-angle symbols kappa_placed, VERBATIM the R27/R16 placed
differential).  Lane B, executing lane A's verdict-C order (小报告-R27).

WHAT IS SWAPPED, WHAT IS HELD FIXED.
    The ONLY change vs 卡点⑦ (r25_emergence_timeseries) is the Riemann kernel:
        ideal:   R built from spatial symbol  i*sin(k_j)  + central-diff time
                 (emergence_judge.riemann_series_k)        <- momentum = k
        placed:  R_{m a n b} = 1/2 (kap_m kap_n H_ab + kap_a kap_b H_mn
                                    - kap_m kap_b H_an - kap_a kap_n H_mb)
                 with kap = kappa_placed(k) = [2 sin(w/2)/c, 2 sin(k_i/2)]
                 -- the SAME placed half-angle momenta the R25/walk gauge modes
                 are built on (R15 T8/T9), VERBATIM R16.riemann_energy.
    Everything else is byte-identical to 卡点⑦: SAME real evolution U (frozen
    R25 step), SAME clean IC (unit-modulus spectral subspace), SAME SVD count
    pipeline (window / peak / prominence / SV_THRESH), SAME field convention
    (physical h fed directly, no trace reversal).  Reused READ-ONLY from
    r25_emergence_timeseries: unit_projectors, make_ic, evolve_record,
    _peak_and_svd (ideal baseline).  Nothing in the frozen inputs is modified.

FIDELITY CERTIFICATE (E0): riemann_series_k_placed on one slice reproduces
    R16.riemann_energy bit-for-bit (checked at build time, 0.0 diff all k).

THREE-WAY VERDICT (let the numbers decide, per lane A's order):
    -> 2 (all k incl. body-diagonal):  pure judge/shell mismatch; E1 directly
         supports; 卡点⑦ flips FAIL->PASS under the shell-consistent judge
         (claim ONLY "涌现A gate passes under a shell-consistent judge"; 卡点④
         joint-verification still undone).
    -> intermediate (e.g. static placed = 2 but evolved-T-steps = X):  judge
         fixed part of it; the walk EVOLUTION kernel also needs Wilson
         co-deformation (named medium cost, not a new construction).
    -> unchanged (still 4-5):  evolution truly generates gauge curvature; deep
         obstruction -> supports verdict B.

STATIC vs DYNAMIC (the E1 gap lane A could not close):
    (a) STATIC : placed judge on placed regular modes (symbol unit modes +
        explicit placed gauge/TT).  Must reproduce E1: gauge -> 0, TT -> 2.
    (b) DYNAMIC: placed judge on the REAL U evolved T steps from clean IC.
        Tests whether U KEEPS the placed gauge/TT subspace (E1's missing half).

POSITIVE CONTROLS (re-run after the kappa swap -- if these break the test is
    void, fix the judge first):
    * teeth (bare wave spin2, half-angle shell) through the placed kernel -> 6
      (kernel not rigged to output 2; it has teeth).
    * placed gauge -> 0 machine, placed TT -> O(1) (kernel kills gauge, sees TT).
    * synthetic placed-TT-only 2-DOF series through placed kernel -> 2 with a
      machine-zero cliff (placed Fierz-Pauli analog).
    * null_damped (genuine Fierz-Pauli, FULL-angle wide shell) under ITS OWN
      shell-matched judge (= the ideal central kernel) -> 2 with cliff, AND
      under the half-angle placed kernel (shell-MISMATCHED) -> inflated: the
      SAME mismatch mechanism, shown symmetrically.

HONEST RED LINES (AGENTS.md + 执行令): this is a judge-shell test only.  It does
    NOT declare M3 / emergence / the DOF axis closed.  If it flips PASS, the
    only claim is "涌现A gate passes under a shell-consistent judge"; 卡点④ is
    still open.  Negative / intermediate results delivered as-is.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/r28_placed_judge_reverdict.py
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

import r25_realspace_step as R                             # noqa: E402 frozen U
import r25_dynamic_symbol as D1                            # noqa: E402 symbol
import r25_emergence_timeseries as TS                      # noqa: E402 卡点⑦ pipeline (read-only)
from rulespace_gpu import emergence_judge as EJ            # noqa: E402 ideal kernel + controls
from r15_walk_dedonder import (kappa_placed, gauge_block,  # noqa: E402 placed shell
                               tt_basis, shell_omega, C_CONE, ETA, unpack, SYM)

OUT = os.path.join(ROOT, "data", "results", "r28_results.json")

N = TS.N                                                   # 16
SV_THRESH = TS.SV_THRESH                                   # 0.05 (shared口径)
W_MAX = TS.W_MAX                                           # pi/2
C2 = float(np.cos(np.pi / 3.0) ** 2)                       # 0.25 light cone
KSET = [(2, 0, 0), (0, 3, 0), (2, 2, 0), (2, 2, 2)]        # axial x2 / face / BODY
LABELS = {(2, 0, 0): "axial", (0, 3, 0): "axial",
          (2, 2, 0): "face-diagonal", (2, 2, 2): "body-diagonal"}
T_CLEAN = 320
TRIALS = 6
T_CTRL = 512
TRIALS_CTRL = 8
SEED = TS.SEED


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


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


# ===========================================================================
#  THE SWAP: placed-kappa Riemann kernel (verbatim R16/R27 placed differential,
#  lifted from a scalar energy to the 256-vector time series the SVD口径 needs).
#  Drop-in replacement for EJ.riemann_series_k -- returns the SAME (T-4, 256)
#  shape so the downstream window/peak/SVD pipeline is byte-identical.
# ===========================================================================
def riemann_series_k_placed(H44, kap):
    """H44 : (T,4,4) complex physical-h k-mode series (NO trace reversal, same
             convention as 卡点⑦'s riemann_series_k call).
       kap : real placed 4-momentum on the walk shell = kappa_placed(kvec).
       Placed linearized Riemann is ALGEBRAIC in kap (both time & space are
       placed half-angle symbols); edges trimmed [2:-2] to match the ideal
       kernel's output length."""
    k = np.real(np.asarray(kap))
    T = H44.shape[0]
    Rt = np.zeros((T, 4, 4, 4, 4), dtype=complex)
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    Rt[:, m, a, n, b] = 0.5 * (
                        k[m] * k[n] * H44[:, a, b] + k[a] * k[b] * H44[:, m, n]
                        - k[m] * k[b] * H44[:, a, n] - k[a] * k[n] * H44[:, m, b])
    return Rt[2:-2].reshape(T - 4, 256)


def _tr_flat(v10):
    """flat-ETA trace reversal (R16 convention) hbar-packed -> physical-h packed;
    exactly cancels the -eta(kap.xi) term of gauge_block (whose eta is flat)."""
    Hb = unpack(v10)
    trb = sum(ETA[m, m] * Hb[m, m] for m in range(4))
    H = Hb - 0.5 * ETA * trb
    return np.array([H[m, n] for (m, n) in SYM])


# ===========================================================================
#  peak+SVD count -- COPIED verbatim from TS._peak_and_svd, ONLY the kernel line
#  swapped (ideal riemann_series_k -> placed).  Same window/sel/peak/prominence/
#  SV_THRESH/n_raw -> "同一 SVD 计数口径".
# ===========================================================================
def _peak_and_svd_placed(series_k, kvec, kap):
    T = series_k.shape[0]
    T0 = T // 2
    Wn = T - T0
    win = np.hanning(Wn)
    freqs = 2 * np.pi * np.fft.fftfreq(Wn - 4)
    sel = (freqs > max(0.05, 4 * np.pi / (Wn - 4))) & (freqs <= W_MAX)
    trials = series_k.shape[1]
    rows_R, rows_raw, pow_spec = [], [], None
    for r in range(trials):
        H10 = series_k[T0:, r, :]
        Rf = riemann_series_k_placed(EJ.packed_to_44(H10), kap)   # <-- ONLY SWAP
        F = np.fft.fft(Rf * win[2:-2, None], axis=0)
        Praw = np.fft.fft(H10[2:-2] * win[2:-2, None], axis=0)
        P = np.sum(np.abs(F) ** 2, axis=1)
        pow_spec = P if pow_spec is None else pow_spec + P
        rows_R.append(F)
        rows_raw.append(Praw)
    total = float(pow_spec[sel].sum())
    if total < 1e-18:
        return {"n_prop": 0, "n_raw": 0, "w_peak": float("nan"),
                "sv": [], "sv_raw": [], "no_peak": True}
    pk = int(np.argmax(np.where(sel, pow_spec, 0)))
    w_pk = float(freqs[pk])
    edge = int(np.argmax(sel))
    prom = float(pow_spec[pk] / (pow_spec[edge] + 1e-300))
    if pk == edge or prom < 2.0:
        return {"n_prop": 0, "n_raw": 0, "w_peak": float("nan"),
                "sv": [], "sv_raw": [], "no_peak": True, "prominence": prom}
    M = np.array([r[pk] for r in rows_R])
    sv = np.linalg.svd(M, compute_uv=False)
    svn = (sv / (sv[0] + 1e-300)).tolist()
    n_prop = int(np.sum(np.array(svn) > SV_THRESH))
    Mr = np.array([r[pk] for r in rows_raw])
    svr = np.linalg.svd(Mr, compute_uv=False)
    svrn = (svr / (svr[0] + 1e-300)).tolist()
    n_raw = int(np.sum(np.array(svrn) > SV_THRESH))
    return {"n_prop": n_prop, "n_raw": n_raw, "w_peak": w_pk, "prominence": prom,
            "sv": [float(v) for v in svn[:8]],
            "sv_raw": [float(v) for v in svrn[:10]]}


# ===========================================================================
#  generic rule evolve+record (for the positive controls: teeth / null_damped)
# ===========================================================================
def evolve_rule_record(rule, kmodes, T, trials, seed=1):
    step, nlev, c2 = rule["step"], rule["n_levels"], float(rule["cg2"])
    rng = np.random.default_rng(seed)
    state = tuple(rng.standard_normal((trials, N, N, N, 10)) for _ in range(nlev))
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    phases = np.stack([np.exp(-1j * (2 * np.pi / N)
                              * (nv[0] * X + nv[1] * Y + nv[2] * Z)) / N ** 3
                       for nv in kmodes])
    rec = np.zeros((T, trials, len(kmodes), 10), complex)
    for t in range(T):
        state = step(state)
        rec[t] = np.einsum("kxyz,rxyzc->rkc", phases, state[0])
    return rec, c2


# ===========================================================================
#  STATIC symbol test with placed kernel (mirror TS.symbol_branches, placed).
# ===========================================================================
def placed_symbol_branches(kmodes, mu=R.MU, tr=False):
    """Placed per-branch curvature rank of the frozen symbol's 12 unit modes.
    tr=False: feed V[:10] as physical h directly (卡点⑦'s field convention).
    tr=True : first flat-ETA trace-reverse V[:10] (hbar->physical) -- sensitivity
              probe: if this drops the rank to 2, the residual was a trace-term
              convention slip; if it stays 4-5, the extra curvature is real."""
    out = []
    tt = np.arange(6)
    for nv in kmodes:
        kvec = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(kvec)
        M = D1.damped_map(kvec, mu)[0]
        eig, V = np.linalg.eig(M)
        units, mx, rr = D1.unit_census(eig)
        idx = np.where(np.abs(np.abs(eig) - 1.0) < 2e-9)[0]
        phases = np.angle(eig[idx])
        branches = []
        used = np.zeros(len(idx), bool)
        for a in range(len(idx)):
            if used[a]:
                continue
            grp = [b for b in range(len(idx)) if abs(phases[b] - phases[a]) < 1e-6]
            for b in grp:
                used[b] = True
            lam = eig[idx[grp[0]]]
            vecs = []
            for b in grp:
                H10 = V[:10, idx[b]]
                if tr:
                    H10 = _tr_flat(H10)
                H44 = EJ.packed_to_44(H10[None])[0]
                ser = H44[None] * (lam ** tt)[:, None, None]
                vecs.append(riemann_series_k_placed(ser, kap)[1])
            sv = np.linalg.svd(np.array(vecs), compute_uv=False)
            svn = (sv / (sv[0] + 1e-300)).tolist() if len(sv) else []
            rank = int(np.sum(np.array(svn) > SV_THRESH)) if svn else 0
            branches.append({"w": float(abs(phases[a])), "n_modes": len(grp),
                             "curvature_rank": rank,
                             "sv": [float(v) for v in svn[:6]]})
        branches.sort(key=lambda d: d["w"])
        dom = max(branches, key=lambda d: d["curvature_rank"])
        out.append({"nv": list(nv), "unit_modes": units,
                    "dominant_branch_curvature_rank": dom["curvature_rank"],
                    "branches": branches})
    return out


def placed_subspace_residual(kmodes, mu=R.MU):
    """For each k, how much of the 12 unit modes' PHYSICAL-h content lies OUTSIDE
    the placed gauge(4) + placed TT(2) subspace.  Large residual => the walk's
    real modes are NOT placed-gauge+TT => a shell-consistent judge legitimately
    sees >2 curvature DOF (this is why placing the judge does not reach 2)."""
    out = []
    for nv in kmodes:
        kvec = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(kvec)
        G = gauge_block(kap)
        TT = tt_basis(kap)
        basis = np.column_stack([_tr_flat(np.real(G[:, a])) for a in range(4)]
                                + [np.real(TT[:, i]) for i in range(2)])  # physical
        Q, _ = np.linalg.qr(basis)                       # (10, 6) ortho placed subspace
        M = D1.damped_map(kvec, mu)[0]
        eig, V = np.linalg.eig(M)
        idx = np.where(np.abs(np.abs(eig) - 1.0) < 2e-9)[0]
        U = V[:10, idx]                                  # (10, 12) unit-mode metric parts
        U = U / (np.linalg.norm(U, axis=0, keepdims=True) + 1e-300)
        proj = Q @ (Q.conj().T @ U)
        resid = np.linalg.norm(U - proj, axis=0)         # per-mode residual (0..1)
        out.append({"nv": list(nv), "n_unit": int(U.shape[1]),
                    "mean_residual_outside_placed_subspace": float(np.mean(resid)),
                    "max_residual": float(np.max(resid)),
                    "n_modes_resid_gt_0.3": int(np.sum(resid > 0.3))})
    return out


# ===========================================================================
#  main
# ===========================================================================
def main():
    t0 = time.time()
    payload = {
        "register": "R28-placed-judge-reverdict (卡点⑦ three-way cheap test)",
        "status": "RUNNING",
        "backend": EJ.B.NAME,
        "params": {"N": N, "kset": [list(k) for k in KSET], "T_clean": T_CLEAN,
                   "trials": TRIALS, "T_ctrl": T_CTRL, "trials_ctrl": TRIALS_CTRL,
                   "sv_thresh": SV_THRESH, "c2": C2, "mu": R.MU, "seed": SEED},
        "the_swap": "Riemann differential ideal(i sin k, central-diff time) -> "
                    "placed kappa_placed=[2 sin(w/2)/c, 2 sin(k_i/2)] (R16/R27 "
                    "verbatim); everything else byte-identical to 卡点⑦.",
        "frozen_inputs_sha256": {
            "r25_realspace_step.py": sha256_file(os.path.join(DIR, "r25_realspace_step.py")),
            "r25_dynamic_symbol.py": sha256_file(os.path.join(DIR, "r25_dynamic_symbol.py")),
            "r25_emergence_timeseries.py": sha256_file(os.path.join(DIR, "r25_emergence_timeseries.py")),
            "r15_walk_dedonder.py": sha256_file(os.path.join(DIR, "r15_walk_dedonder.py")),
            "r16_cp1_invitro.py": sha256_file(os.path.join(DIR, "r16_cp1_invitro.py")),
            "emergence_judge.py": sha256_file(os.path.join(ROOT, "rulespace_gpu", "emergence_judge.py")),
        },
    }
    write_json(payload)

    # -- E0 fidelity: placed kernel == R16.riemann_energy (bit-for-bit) -------
    from r16_cp1_invitro import riemann_energy
    e0 = []
    for nv in KSET:
        kvec = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(kvec)
        G = gauge_block(kap)
        for a in range(4):
            vec = np.real(G[:, a])
            e_ref = riemann_energy(kap, vec)
            Hphys = EJ.packed_to_44(_tr_flat(vec)[None])[0]
            e_mine = float(np.sum(np.abs(
                riemann_series_k_placed(np.repeat(Hphys[None], 5, 0), kap)[0]) ** 2))
            e0.append(abs(e_ref - e_mine))
    payload["E0_placed_kernel_matches_R16"] = {"max_abs_diff": float(max(e0)),
                                               "pass": bool(max(e0) < 1e-20)}
    print(f"[E0] placed kernel == R16.riemann_energy: max diff {max(e0):.1e} -> "
          f"{'PASS' if max(e0) < 1e-20 else 'FAIL'}")
    write_json(payload)

    # -- E1 static: placed judge on explicit placed gauge / TT modes ---------
    print("[E1] static: placed Riemann on placed gauge (->0) and TT (->O(1)) ...")
    e1 = {}
    worst_gauge = 0.0
    for nv in KSET:
        kvec = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(kvec)
        G = gauge_block(kap)
        TT = tt_basis(kap)
        g = [float(np.sum(np.abs(riemann_series_k_placed(
            np.repeat(EJ.packed_to_44(_tr_flat(np.real(G[:, a]))[None])[0][None], 5, 0),
            kap)[0]) ** 2)) for a in range(4)]
        tref = [float(np.sum(np.abs(riemann_series_k_placed(
            np.repeat(EJ.packed_to_44(np.real(TT[:, i])[
                None].reshape(1, 10))[0][None], 5, 0), kap)[0]) ** 2)) for i in range(2)]
        worst_gauge = max(worst_gauge, max(g))
        e1[str(nv)] = {"placed_gauge_R2": g, "placed_tt_R2": tref}
    payload["E1_static_placed"] = {"per_k": e1, "worst_placed_gauge": worst_gauge,
                                   "pass": bool(worst_gauge < 1e-20)}
    print(f"    worst placed gauge R^2 = {worst_gauge:.1e} "
          f"({'machine-zero, E1 reconfirmed' if worst_gauge < 1e-20 else 'NONZERO!'})")
    write_json(payload)

    # -- STATIC symbol test: per-branch curvature rank, ideal vs placed -------
    print("[S] static symbol per-branch curvature rank (ideal vs placed) ...")
    sym_ideal = TS.symbol_branches(KSET)
    sym_placed = placed_symbol_branches(KSET, tr=False)
    sym_placed_tr = placed_symbol_branches(KSET, tr=True)
    resid = placed_subspace_residual(KSET)
    static_ideal = [e["dominant_branch_curvature_rank"] for e in sym_ideal]
    static_placed = [e["dominant_branch_curvature_rank"] for e in sym_placed]
    static_placed_tr = [e["dominant_branch_curvature_rank"] for e in sym_placed_tr]
    payload["static_symbol"] = {"ideal_dominant_rank": static_ideal,
                                "placed_dominant_rank": static_placed,
                                "placed_dominant_rank_traceReversed": static_placed_tr,
                                "placed_subspace_residual": resid,
                                "ideal_branches": sym_ideal,
                                "placed_branches": sym_placed}
    for nv, si, sp, spt, rr in zip(KSET, static_ideal, static_placed,
                                   static_placed_tr, resid):
        print(f"    k={nv}  static ideal={si} -> placed={sp} (TR-probe={spt})"
              f"  mean-resid-outside-placed-subspace="
              f"{rr['mean_residual_outside_placed_subspace']:.3f}")
    write_json(payload)

    # -- clean IC + REAL U evolution (identical to 卡点⑦) --------------------
    print("[U] building unit-modulus spectral projectors + clean IC (识 卡点⑦) ...")
    proj = TS.unit_projectors(N)
    h_c, pi_c, dark0 = TS.make_ic(N, TRIALS, SEED, proj=proj)
    print(f"    clean IC |K x|/rms = {dark0:.2e}   ({time.time()-t0:.1f}s)")
    print(f"[U] evolving REAL frozen R25 step (T={T_CLEAN}, trials={TRIALS}) ...")
    rec, mon = TS.evolve_record(h_c, pi_c, T_CLEAN, KSET)
    dark_max = max(d for _, d in mon["dark_curve"])
    payload["dynamic_run"] = {"clean_ic_dark_t0": dark0, "dark_max": dark_max,
                              "rms_growth": mon["rms_growth"], "stable": mon["stable"]}
    print(f"    constraint darkness stayed <= {dark_max:.2e}; rms growth "
          f"{mon['rms_growth']:.3f}   ({time.time()-t0:.1f}s)")
    write_json(payload)

    # -- DYNAMIC count on the SAME rec: ideal baseline vs placed reverdict ----
    print("[D] dynamic count on the SAME rec -- ideal baseline vs PLACED swap:")
    per_k = []
    for ki, nv in enumerate(KSET):
        kvec = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(kvec)
        ideal = TS._peak_and_svd(rec[:, :, ki, :], kvec)
        placed = _peak_and_svd_placed(rec[:, :, ki, :], kvec, kap)
        row = {"nv": list(nv), "label": LABELS[nv],
               "ideal_n_prop": ideal["n_prop"], "ideal_sv": ideal.get("sv", []),
               "placed_n_prop": placed["n_prop"], "placed_sv": placed.get("sv", []),
               "n_raw": ideal.get("n_raw"), "w_peak": placed.get("w_peak"),
               "w_shell": float(shell_omega(kvec))}
        per_k.append(row)
        print(f"    k={nv} [{LABELS[nv]:>13}]  ideal N_prop={ideal['n_prop']}"
              f"  ->  PLACED N_prop={placed['n_prop']}   "
              f"placed_sv={['%.1e' % s for s in placed.get('sv', [])[:5]]}")
    payload["dynamic_run"]["per_k"] = per_k
    dyn_ideal = [r["ideal_n_prop"] for r in per_k]
    dyn_placed = [r["placed_n_prop"] for r in per_k]
    payload["dynamic_run"]["ideal_seq"] = dyn_ideal
    payload["dynamic_run"]["placed_seq"] = dyn_placed
    write_json(payload)

    # -- POSITIVE CONTROLS (after the kappa swap) ----------------------------
    print("[PC] positive controls after the kappa swap ...")
    controls = {}

    # PC1 teeth: bare wave spin2 (half-angle shell) through PLACED kernel -> 6
    rec_t, c2_t = evolve_rule_record(EJ.make_rule_spin2(cg2=C2), KSET, T_CTRL,
                                     TRIALS_CTRL, seed=1)
    teeth_placed = []
    for ki, nv in enumerate(KSET):
        kvec = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(kvec)
        series = EJ.trace_reverse_c(rec_t[:, :, ki, :], c2_t)   # (T, trials, 10) physical h
        res = _peak_and_svd_placed(series, kvec, kap)
        teeth_placed.append(res["n_prop"])
    controls["teeth_bare_wave_placed"] = {"n_prop": teeth_placed,
                                          "expect": ">2 (has teeth, ~6)"}
    print(f"    teeth (spin2, placed kernel) N_prop = {teeth_placed}  (expect ~6)")
    write_json({**payload, "controls_partial": controls})

    # PC2 synthetic placed 2-DOF (TT-only) series -> placed kernel -> 2 cliff
    fp = []
    rng = np.random.default_rng(7)
    for nv in KSET:
        kvec = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(kvec)
        TT = tt_basis(kap)
        Gm = gauge_block(kap)
        w = shell_omega(kvec)
        tvec = np.arange(T_CTRL)
        series = np.zeros((T_CTRL, TRIALS_CTRL, 10), complex)
        for r in range(TRIALS_CTRL):
            ctt = TT @ (rng.standard_normal(2) + 1j * rng.standard_normal(2))
            cg = Gm @ (rng.standard_normal(4) + 1j * rng.standard_normal(4))
            phys = _tr_flat(ctt + cg)                          # TT + gauge, physical
            # +i w t: np.fft.fft puts e^{+i w t} content at the +w bin, which is
            # the (positive) band the peak selector scans (same as the ideal
            # judge's TT reference, emergence_judge line ~522).
            series[:, r, :] = phys[None, :] * np.exp(1j * w * tvec)[:, None]
        res = _peak_and_svd_placed(series, kvec, kap)
        fp.append({"nv": list(nv), "n_prop": res["n_prop"], "sv": res.get("sv", [])})
    controls["synthetic_placed_TT_plus_gauge"] = {
        "per_k": fp, "n_prop": [e["n_prop"] for e in fp],
        "expect": "2 with machine-zero cliff (gauge annihilated, TT seen)"}
    print(f"    synthetic placed TT+gauge (placed kernel) N_prop = "
          f"{[e['n_prop'] for e in fp]}  (expect 2, cliff)")
    write_json({**payload, "controls_partial": controls})

    # PC3 null_damped: ITS OWN shell-matched judge (ideal central) -> 2 cliff
    print("    null_damped under ideal(=its shell-matched) kernel via EJ.judge_dof ...")
    nd = EJ.judge_dof(EJ.make_rule_null_damped(cg2=C2, kappa=0.5), N=N,
                      T=T_CTRL, trials=TRIALS_CTRL, kmodes=tuple(KSET))
    nd_ideal = nd["n_prop_all"]
    nd_sv = [e.get("sv", [])[:6] for e in nd["per_k"]]
    controls["null_damped_ideal_shellmatched"] = {"n_prop": nd_ideal, "sv": nd_sv,
                                                  "expect": "2 with cliff"}
    print(f"    null_damped (ideal shell-matched) N_prop = {nd_ideal}  (expect 2 cliff)")
    # PC3b null_damped under the half-angle PLACED kernel (shell-MISMATCH) -> inflate
    rec_nd, c2_nd = evolve_rule_record(EJ.make_rule_null_damped(cg2=C2, kappa=0.5),
                                       KSET, T_CTRL, TRIALS_CTRL, seed=1)
    nd_placed = []
    for ki, nv in enumerate(KSET):
        kvec = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(kvec)
        series = EJ.trace_reverse_c(rec_nd[:, :, ki, :], c2_nd)
        nd_placed.append(_peak_and_svd_placed(series, kvec, kap)["n_prop"])
    controls["null_damped_halfangle_placed_MISMATCH"] = {
        "n_prop": nd_placed,
        "note": "half-angle placed kernel is shell-MISMATCHED to the full-angle "
                "null_damped rule -> misreads (>2): the SAME mechanism, shown "
                "symmetrically."}
    print(f"    null_damped (half-angle placed, MISMATCH) N_prop = {nd_placed}  "
          f"(shows mismatch inflates even a genuine 2-DOF rule)")
    payload["controls"] = controls
    write_json(payload)

    # -- verdict -------------------------------------------------------------
    teeth_ok = all(n > 2 for n in teeth_placed)
    fp_ok = all(e["n_prop"] == 2 for e in fp)
    nd_ok = all(n == 2 for n in nd_ideal)
    gauge_seen0 = payload["E1_static_placed"]["pass"]
    pc_pass = bool(teeth_ok and fp_ok and nd_ok and gauge_seen0
                   and payload["E0_placed_kernel_matches_R16"]["pass"])

    static_all2 = all(n <= 2 for n in static_placed)
    dyn_all2 = all(n <= 2 for n in dyn_placed)
    dyn_max = max(dyn_placed)

    if not pc_pass:
        verdict_tag = "VOID"
        verdict = ("正控 FAIL: the kappa swap blinded the judge (teeth_ok=%s "
                   "fp_ok=%s nd_ok=%s gauge0=%s E0=%s). Test invalid; fix judge "
                   "first." % (teeth_ok, fp_ok, nd_ok, gauge_seen0,
                               payload["E0_placed_kernel_matches_R16"]["pass"]))
    elif dyn_all2 and static_all2:
        verdict_tag = "->2 (pure judge/shell mismatch)"
        verdict = ("PLACED dynamical N_prop = %s = 2 at ALL k incl. body-diagonal "
                   "(2,2,2). Static placed = %s = 2. E1 directly supported: 卡点⑦'s "
                   "4-5 was a judge/shell mismatch (ideal momentum k vs walk placed "
                   "kappa). Under the shell-consistent judge the 涌现A DOF gate PASSES. "
                   "CLAIM ONLY '涌现A gate passes under shell-consistent judge'; 卡点④ "
                   "joint-verification STILL UNDONE; NO M3 / no emergence / no DOF-axis "
                   "closure." % (dyn_placed, static_placed))
    elif static_all2 and not dyn_all2:
        verdict_tag = "->intermediate (evolution needs Wilson co-deformation)"
        verdict = ("STATIC placed = %s = 2 (judge fixed) but DYNAMIC placed = %s "
                   "(max %d) after T=%d steps: the real U does NOT fully preserve "
                   "the placed gauge/TT subspace -- the walk EVOLUTION kernel also "
                   "needs Wilson co-deformation (named medium cost, not a new "
                   "construction). Localizes U's placed-subspace breakage rate."
                   % (static_placed, dyn_placed, dyn_max, T_CLEAN))
    else:
        verdict_tag = "->unchanged (deep, supports verdict B)"
        verdict = ("PLACED dynamical N_prop = %s (still >2, incl. body-diagonal); "
                   "static placed = %s. Even the shell-consistent judge sees >2 "
                   "propagating placed curvature DOF: the evolution TRULY generates "
                   "gauge curvature -> deep obstruction, supports verdict B (named "
                   "open)." % (dyn_placed, static_placed))

    payload["monotone_chain"] = {
        "naive_ideal_all_gauge_misread": 6,
        "R25_wilson_ideal_kappa7": [4, 4, 5, 5],
        "R28_ideal_on_this_rec": dyn_ideal,
        "R28_placed_static": static_placed,
        "R28_placed_dynamic": dyn_placed,
        "note": "naive 6 -> R25/ideal 4-5 -> shell-consistent placed: static %s / "
                "dynamic %s" % (static_placed, dyn_placed)}
    payload["positive_controls_pass"] = pc_pass
    payload["verdict_tag"] = verdict_tag
    payload["verdict"] = verdict
    payload["scope_boundary"] = (
        "Judge-shell test only (卡点⑦ three-way). NO M3 / no emergence / no DOF-axis "
        "closure. If ->2, claim ONLY '涌现A gate passes under shell-consistent judge'; "
        "卡点④ still open. Clean IC (unit-modulus spectral subspace) is the declared "
        "premise, same as 卡点⑦.")
    payload["status"] = "PASS" if (pc_pass and dyn_all2 and static_all2) else "FAIL"
    payload["source_sha256"] = sha256_file(__file__)
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = sha256_bytes(fh.read())
    payload["results_sha256"] = jsha
    write_json(payload)

    print("=" * 74)
    print(f"positive controls pass: {pc_pass}")
    print(f"STATIC placed  N_prop = {static_placed}")
    print(f"DYNAMIC placed N_prop = {dyn_placed}   (ideal baseline {dyn_ideal})")
    print(f"VERDICT [{verdict_tag}]")
    print(verdict)
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
