"""tier2_gw — HIGH-FIDELITY graviton group-velocity gate for the tensor campaign
tier-2 gate (TENSOR_CAMPAIGN_INTERFACE.md receipt clause #3).

WHY THIS EXISTS (honest framing):
    tier-1's `gw_speed` (tensor_batch) is a wave-PACKET-CENTROID speed ratio,
    normalized to a cg2=1 reference so the leading lattice-dispersion systematic
    cancels.  Its residual scatter is a few percent -- a MEASUREMENT FLOOR.  Reusing
    it at a 1e-2 gate is therefore *noise selection*, not physics: whatever survives
    the 1e-2 cut on that column survives because of centroid-tracking noise, not
    because its graviton actually moves at the matter speed.

    This module replaces that placeholder with the physically meaningful quantity
    the receipt asked for:

        c_gw  = graviton GROUP velocity dw/dk, measured by the SPECTRAL method
                (per-k dispersion peak; the same measurement family emergence_judge
                 uses on the null-box control, ~0.991), NOT a packet centroid.
        c_mat = walker MATTER speed (empirical: tensor_walker16 v_env/c = 0.993).
        gw_ratio = c_gw / c_mat,      gate:  |gw_ratio - 1| < 1e-2.

    At the physical light-cone rule (cg2=1) the graviton and the matter walker live
    on the SAME sub-cycled lattice, so their shared O(k^2) dispersion cancels in the
    ratio -> gw_ratio ~ 1.  A slow graviton (small cg2) has c_gw ~ sqrt(cg2) << c_mat
    -> ratio far from 1 -> culled.  THIS is the GW170817 constraint with teeth.

METHOD (spectral group velocity, projection-free, no SVD):
    * 1D plane-symmetric reduction along z (graviton TT propagation is 1D): the same
      componentwise leapfrog + sub-cycling as tier-1 (tensor_batch._step_wave1d), so
      the graviton measured here IS the graviton tier-1 screens (shared discretization
      -- the tier-1/tier-2 calibration decision, INTERFACE.md 2026-07-20).
    * Excite the physical TT (+) polarization with a DETERMINISTIC superposition of a
      few pure spatial modes k_j (no RNG -> bit-identical every run -> exact resume).
    * Evolve; each step, project the TT field onto each k_j (spatial DFT row) to get
      the complex mode amplitude time series a_j(t).
    * Per k_j: time-FFT |a_j(t)|, locate the dispersion peak with PARABOLIC sub-bin
      interpolation -> w(k_j) to ~1e-3 rad/step (a spectral line position, far sharper
      than a moving centroid).
    * c_gw = dw/dk = slope of a least-squares line through {(k_j, w_j)} -> the GROUP
      velocity in the probe band (physical cells/step, sub-cycling undone).

    Cost: ONE 1D evolution per rule (Nz x T, all k_j projected in the same pass),
    batched over the rule axis.  No 3D lattice, no Riemann tensor, no SVD, no gauge
    judge -> ~2-3 orders cheaper than a full judge_emergence call.  Per-survivor
    feasible (see COST at bottom of module / __main__).

ANALYTIC CROSS-CHECK (proxy, closed form, essentially free):
    The sub-cycled leapfrog dispersion is exactly
        sin(w_sim/2) = sqrt(cg2/4) sin(k/2),   w_phys = w_sim / SUB
        v_g(k) = dw_phys/dk = sqrt(cg2) cos(k/2) / sqrt(1 - (cg2/4) sin^2(k/2)).
    `analytic_group_velocity` returns it.  The measured c_gw agrees with it to the
    spectral-line precision (reported by __main__); for the LINEAR campaign rules the
    analytic form is a legitimate cheap fallback, but we gate on the MEASURED value so
    the criterion stays empirical (a nonlinear / walker rule could depart from it).

HONEST LABEL:  the c_gw measurement is EMPIRICAL (spectral group velocity of the
    evolved rule).  c_matter = 0.993 is an EMPIRICAL constant imported from the walker
    sector (tensor_walker16, v_env/c) -- it is NOT re-measured per rule (the walker is a
    fixed 16-component construction, not parametrized by the campaign's (cg2,gamma,...);
    re-running it per survivor would be prohibitive and pointless).  So the gate is
    empirical-c_gw / empirical-constant-c_matter.  Not a theorem.
"""
import argparse
import json
import os

import numpy as np

from . import backend as B
from .tensor_batch import SUB, SUB2, TT_PLUS, _step_wave1d, _step_wave1d_j

DIR = os.path.dirname(os.path.abspath(__file__))

# --- empirical matter speed (walker sector) --------------------------------
# tensor_walker16 dirac-pair probe: TT energy fraction 0.987, v_env/c = 0.993.
# This is the "matter" leg of the GW170817-style ratio.  Empirical import.
C_MATTER_WALKER = 0.993
TIER2_GW_TOL = 1e-2

# probe wavevector band (integer modes n on an Nz lattice: k = 2*pi*n/Nz).  Kept in
# the small-k continuum band where the dispersion is smooth and the peak is a clean
# single line; group velocity = slope of w(k) across these modes.
_PROBE_MODES = (2, 3, 4, 5, 6)


def analytic_group_velocity(cg2, k):
    """closed-form physical group velocity of the sub-cycled leapfrog TT wave.
    v_g = sqrt(cg2) cos(k/2) / sqrt(1 - (cg2/4) sin^2(k/2)).  cells/step (physical)."""
    cg2 = np.asarray(cg2, float)
    s = np.sin(k / 2.0)
    return np.sqrt(cg2) * np.cos(k / 2.0) / np.sqrt(np.maximum(1.0 - (cg2 / 4.0) * s * s, 1e-30))


def _parabolic_peak(power, i):
    """sub-bin peak offset via 3-point parabolic interpolation around index i."""
    if i <= 0 or i >= len(power) - 1:
        return 0.0
    a, b, c = power[i - 1], power[i], power[i + 1]
    denom = a - 2.0 * b + c
    if abs(denom) < 1e-300:
        return 0.0
    return float(np.clip(0.5 * (a - c) / denom, -0.5, 0.5))


def measure_gw_speed(params, Nz=192, T=2048, jit=True, return_diag=False):
    """Spectral graviton GROUP velocity per rule.  params: host (Bn,5), columns
    = tensor_qca PARAM_NAMES [cg2,gamma,G,tr_sign,sigma] (only cg2,gamma used).
    Returns (Bn,) c_gw in physical cells/step (sub-cycling undone).  Deterministic."""
    params = np.atleast_2d(np.asarray(params, float))
    Bn = params.shape[0]
    cg2 = B.asarray((SUB2 * params[:, 0]).reshape(Bn, 1, 1))      # sub-cycled stiffness
    gam = B.asarray((SUB * params[:, 1]).reshape(Bn, 1, 1))

    z = np.arange(Nz)
    ks = np.array([2.0 * np.pi * n / Nz for n in _PROBE_MODES])    # probe wavevectors
    # deterministic TT(+) initial data: equal-amplitude superposition of the probe
    # modes (zero velocity -> standing waves; each k_j rings at its own w(k_j)).
    env = np.zeros(Nz)
    for k in ks:
        env += np.cos(k * z)
    h0 = np.zeros((Bn, Nz, 10))
    h0[:, :, TT_PLUS[0]] = env                                    # h_xx = +env
    h0[:, :, TT_PLUS[1]] = -env                                   # h_yy = -env  (TT +)
    h = B.asarray(h0)
    hp = h                                                        # zero initial velocity
    dm = B.asarray(np.zeros((1, 1, 10)))                          # never damp TT here
    step = _step_wave1d_j if jit else _step_wave1d

    # spatial DFT rows for the probe modes (project the TT scalar hxx-hyy each step)
    proj = np.exp(-1j * np.outer(ks, z)) / Nz                     # (nk, Nz)
    nk = len(ks)
    rec = np.zeros((T, Bn, nk), dtype=complex)
    for t in range(T):
        h, hp = step(h, hp, cg2, gam, dm)
        tt = B.to_np(h[:, :, TT_PLUS[0]] - h[:, :, TT_PLUS[1]])   # (Bn, Nz)
        rec[t] = tt.astype(complex) @ proj.T                      # (Bn, nk)
    B.sync(h)

    # per-rule, per-k spectral peak -> w(k); group velocity = slope dw/dk.
    # standing-wave modes -> full FFT, take the POSITIVE-frequency half only.
    fullfreq = 2.0 * np.pi * np.fft.fftfreq(T)                    # rad per SUB-step
    nh = T // 2
    freqs = fullfreq[:nh]                                         # >= 0 band
    dfreq = freqs[1] - freqs[0]
    c_gw = np.full(Bn, np.nan)
    w_meas = np.full((Bn, nk), np.nan)
    win = np.hanning(T)
    lo = 2                                                       # skip only DC + 1 bin
    #   (a slow graviton's w can be << k, so a light-speed-scaled DC guard would
    #    clip its low-k peaks and corrupt the dw/dk slope -- keep the guard tiny)
    for i in range(Bn):
        rmsend = np.sqrt(np.mean(np.abs(rec[:, i, :]) ** 2))
        if not np.isfinite(rmsend) or rmsend > 1e6 or rmsend < 1e-12:
            continue                                             # blown / dead rule
        wk = []
        for j in range(nk):
            F = np.abs(np.fft.fft(rec[:, i, j] * win))[:nh] ** 2
            F[:lo] = 0.0
            pk = int(np.argmax(F))
            w_sim = freqs[pk] + _parabolic_peak(F, pk) * dfreq
            wk.append(w_sim / SUB)                               # -> physical rad/step
        wk = np.array(wk)
        w_meas[i] = wk
        # group velocity: least-squares slope of w(k) across the probe band
        A = np.vstack([ks, np.ones_like(ks)]).T
        slope = np.linalg.lstsq(A, wk, rcond=None)[0][0]
        c_gw[i] = abs(slope)
    if return_diag:
        return {"c_gw": c_gw, "w_meas": w_meas, "ks": ks}
    return c_gw


def tier2_gw(params, c_matter=C_MATTER_WALKER, tol=TIER2_GW_TOL,
             Nz=192, T=2048, jit=True, with_analytic=True):
    """TIER-2 gw gate.  params: host (Bn,5) [cg2,gamma,G,tr_sign,sigma].
    Returns per-rule dict:
        gw_speed  (float) c_gw, measured graviton group velocity (cells/step)
        gw_ratio  (float) c_gw / c_matter
        gw_ok     (bool)  |gw_ratio - 1| < tol   <-- the tier-2 gate
        gw_analytic (float) closed-form c_gw at the band-center probe k (cross-check)
    Deterministic pure function of params (no RNG) -> exact resume."""
    params = np.atleast_2d(np.asarray(params, float))
    c_gw = measure_gw_speed(params, Nz=Nz, T=T, jit=jit)
    with np.errstate(all="ignore"):
        gw_ratio = c_gw / float(c_matter)
        gw_ok = np.isfinite(gw_ratio) & (np.abs(gw_ratio - 1.0) < tol)
    out = {"gw_speed": c_gw, "gw_ratio": gw_ratio, "gw_ok": gw_ok}
    if with_analytic:
        kc = 2.0 * np.pi * float(np.mean(_PROBE_MODES)) / Nz
        out["gw_analytic"] = analytic_group_velocity(params[:, 0], kc)
    return out


# ===========================================================================
#  self-test / cost report
# ===========================================================================
if __name__ == "__main__":
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "data", "results", "tier2_gw_selftest.json"))
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING backend={B.NAME}; group velocity is precision-sensitive, "
              f"run RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend = {B.NAME}   c_matter(walker) = {C_MATTER_WALKER}   tol = {TIER2_GW_TOL}")
    print("=" * 78)

    probes = np.array([
        [1.00, 0.05, 0.02, 1.0, 2.5],    # gold standard: light-cone rule
        [0.25, 0.05, 0.02, 1.0, 2.5],    # slow graviton (c_g ~ c/2): must be culled
        [0.81, 0.05, 0.02, 1.0, 2.5],    # mild slow graviton (c_g ~ 0.9): culled
        [0.98, 0.05, 0.02, 1.0, 2.5],    # near light-cone: borderline
    ])
    names = ["gold cg2=1", "slow cg2=0.25", "mild cg2=0.81", "near cg2=0.98"]
    t0 = time.time()
    r = tier2_gw(probes)
    dt = time.time() - t0
    diag = measure_gw_speed(probes, return_diag=True)
    print(f"{'rule':>16} {'c_gw':>8} {'analytic':>9} {'ratio':>8} {'ok':>4}")
    for i, nm in enumerate(names):
        print(f"{nm:>16} {r['gw_speed'][i]:8.4f} {r['gw_analytic'][i]:9.4f} "
              f"{r['gw_ratio'][i]:8.4f} {str(bool(r['gw_ok'][i]))[0]:>4}")
    print(f"\nper-k measured w(k) (gold): "
          + "  ".join(f"k={k:.3f}:w={w:.4f}" for k, w in zip(diag['ks'], diag['w_meas'][0])))
    disc = (bool(r["gw_ok"][0]) and not bool(r["gw_ok"][1]) and not bool(r["gw_ok"][2]))
    print(f"\nDISCRIMINATION: {'PASS (gold passes; slow gravitons culled)' if disc else 'CHECK'}")
    print(f"COST: {probes.shape[0]} rules in {dt:.3f}s ({1e3*dt/probes.shape[0]:.1f} ms/rule) "
          f"Nz=192 T=2048")
    json.dump({"c_matter": C_MATTER_WALKER, "tol": TIER2_GW_TOL,
               "names": names, "gw_speed": r["gw_speed"].tolist(),
               "gw_analytic": r["gw_analytic"].tolist(), "gw_ratio": r["gw_ratio"].tolist(),
               "gw_ok": [bool(x) for x in r["gw_ok"]], "ms_per_rule": 1e3 * dt / probes.shape[0]},
              open(args.json, "w"), indent=1)
    print(f"wrote {os.path.abspath(args.json)}")
