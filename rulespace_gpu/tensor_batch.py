"""tensor_batch — BATCHED screening evaluator for tensor (spin-2) rules.

Engineering item #2 of the 3+1D search migration: `evaluate_tensor_rule` is a
serial reference implementation; this module is its GPU-batched SCREENING
counterpart, designed to drop into campaign_runner as the sweep payload.

TWO-TIER ARCHITECTURE (mirrors the scalar campaign's honest pipeline):
  tier 1 (THIS FILE)  fast batched proxies over a batch axis Bn:
     S1  TT propagation: plane-symmetric reduction along z -> fields
         (Bn, Nz, 10); measure TT packet speed + polarization leakage
         (TT retention) + gauge-mode growth under each rule.
     S2  Newton: batched 3D relaxation to the static well; h00/phi ratio
         against the FFT Poisson reference (computed once).
     S3  deflection: Born integral on each rule's relaxed slice -> Eddington
         ratio (tensor/scalar would be 2; here we output h-based deflection
         per unit phi, judged against 2).
     J5  GW-speed judge: |c_TT(measured)/c_matter - 1| < delta  -- the
         GW170817 constraint as a first-class column from day one.
  tier 2 (existing, serial, unchanged): survivors -> full tensor_qca judges
         + emergence_judge A/B.  Screening never replaces the full verdict.

Rule parameters mirror tensor_qca.PARAM_NAMES = [cg2, gamma, G, tr_sign, sigma]:
  cg2     wave stiffness (c_TT^2)
  gamma   lag-free constraint/damping strength
  G       source coupling (fact2/3)
  tr_sign trace-reverse sign in the OBSERVATION map (the falsification knob:
          wrong sign must break Newton=2 and deflection=2)
  sigma   source width

Backend rules obeyed: python-float scalars only, positional axis args,
pure step functions (B.jit-able), per-rule coefficients as device arrays
broadcast over the batch axis.

Run (self-test): RULESPACE_BACKEND=numpy python -m rulespace_gpu.tensor_batch
"""
import json
import math
import os

import numpy as np

from . import backend as B

xp = B.xp
DIR = os.path.dirname(os.path.abspath(__file__))

# packed symmetric-tensor layout (10 components), matching spin2/tensor_qca
IDX10 = [(0, 0), (0, 1), (0, 2), (0, 3),
         (1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)]
PK = {p: i for i, p in enumerate(IDX10)}
SPAT_DIAG = [PK[(1, 1)], PK[(2, 2)], PK[(3, 3)]]
TT_PLUS = (PK[(1, 1)], PK[(2, 2)])            # xx - yy for z-propagation
TT_CROSS = PK[(1, 2)]                          # xy
GAUGE_Z = [PK[(0, 3)], PK[(3, 3)], PK[(0, 0)]]  # longitudinal/trace family


def _lap1(f):
    return B.roll(f, 1, 1) + B.roll(f, -1, 1) - 2.0 * f


def _step_wave1d(h, hp, cg2, gamma, dampmask):
    """batched leapfrog on (Bn, Nz, 10); CONSTRAINT damping acts only on the
    non-TT components (dampmask: (1,1,10) with 0 on TT, 1 elsewhere) — the
    emergence-judge structure: the rule kills gauge modes, never physical TT."""
    nxt = 2.0 * h - hp + cg2 * _lap1(h) - gamma * dampmask * (h - hp)
    return nxt, h


_step_wave1d_j = B.jit(_step_wave1d)

# --- dt SUB-CYCLING -----------------------------------------------------
# naive 3D leapfrog is CFL-stable only for cg2 <= 1/3, which would lock the
# physical target cg2 = 1 (tensor_qca's light cone) OUT of the screen. We
# evolve with dt' = dt/2  =>  cg2_sim = cg2/4, gamma_sim = gamma/2, and
# rescale measured speeds by 2. Screenable range becomes cg2 <= 4/3.
SUB = 0.5
SUB2 = 0.25
CFL3D_PHYS = 4.0 / 3.0   # physical-cg2 stability bound after sub-cycling


# ----------------------------------------------------------------------
# S1 + J5 : TT propagation, polarization retention, gauge growth, GW speed
# ----------------------------------------------------------------------
def screen_tt(params, Nz=128, T=140, c_matter=1.0, jit=True):
    """params: host (Bn,5). returns dict of (Bn,) arrays."""
    Bn = params.shape[0]
    cg2 = B.asarray((SUB2 * params[:, 0]).reshape(Bn, 1, 1))    # sub-cycled
    gam = B.asarray((SUB * params[:, 1]).reshape(Bn, 1, 1))
    z = np.arange(Nz)
    env = np.exp(-((z - Nz * 0.3) ** 2) / (2.0 * 6.0 ** 2)) * np.cos(0.5 * z)
    h0 = np.zeros((Bn, Nz, 10))
    h0[:, :, TT_PLUS[0]] = env                  # + polarization: hxx=-hyy
    h0[:, :, TT_PLUS[1]] = -env
    h0[:, :, TT_CROSS] = 0.3 * env              # some cross
    h0[:, :, GAUGE_Z[0]] = 0.2 * env            # seed a gauge-family component
    h = B.asarray(h0)
    hp = h
    dm_np = np.ones((1, 1, 10))
    for c in (TT_PLUS[0], TT_PLUS[1], TT_CROSS):
        dm_np[0, 0, c] = 0.0                     # never damp physical TT
    dampmask = B.asarray(dm_np)
    step = _step_wave1d_j if jit else _step_wave1d
    zc = B.asarray(z.reshape(1, Nz))

    def com_tt(hh):
        e = (hh[:, :, TT_PLUS[0]] - hh[:, :, TT_PLUS[1]]) ** 2 + hh[:, :, TT_CROSS] ** 2
        tot = xp.sum(e, 1) + 1e-30
        return xp.sum(e * zc, 1) / tot, tot

    c0, eTT0 = com_tt(h)
    g0 = xp.sum(h[:, :, GAUGE_Z[0]] ** 2, 1) + 1e-30
    for t in range(T):
        h, hp = step(h, hp, cg2, gam, dampmask)
    c1, eTT1 = com_tt(h)
    g1 = xp.sum(h[:, :, GAUGE_Z[0]] ** 2, 1)
    B.sync(h)
    speed = (B.to_np(c1) - B.to_np(c0)) / float(T) / SUB   # back to physical dt
    with np.errstate(all="ignore"):
        tt_ret = B.to_np(eTT1) / B.to_np(eTT0)
        gauge_growth = B.to_np(g1) / B.to_np(g0)
    # blow-up guard: non-finite or absurd energies = failed rule, not a number
    bad = ~np.isfinite(tt_ret) | (tt_ret > 1e3) | ~np.isfinite(speed)
    tt_ret = np.where(bad, 0.0, tt_ret)
    speed = np.where(bad, 0.0, speed)
    gauge_growth = np.where(~np.isfinite(gauge_growth), np.inf, gauge_growth)
    gw_dev = np.abs(np.abs(speed) / c_matter - 1.0)
    return {"tt_speed": np.abs(speed), "tt_retention": tt_ret,
            "gauge_growth": gauge_growth, "gw_dev": gw_dev, "blown": bad}


# ----------------------------------------------------------------------
# S2 + S3 : batched Newton relaxation + Born deflection
# ----------------------------------------------------------------------
def _lap3(f):
    out = -6.0 * f
    for ax in (1, 2, 3):
        out = out + B.roll(f, 1, ax) + B.roll(f, -1, ax)
    return out


def _step_newton(hb, hbp, cg2, gamma, src):
    nxt = 2.0 * hb - hbp + cg2 * _lap3(hb) - gamma * (hb - hbp) + src
    return nxt, hb


_step_newton_j = B.jit(_step_newton)


def screen_newton(params, L=24, T=400, jit=True):
    """batched hbar00 relaxation (scalar sector of the tensor: the 00 row),
    per-rule (cg2, gamma, G, tr_sign, sigma). Judges h00/phi -> 2 and the
    Born deflection per phi -> Eddington 2 with the correct trace-reverse."""
    Bn = params.shape[0]
    # sub-cycled operator; src is scaled by SUB2 too, so the static fixed
    # point  h = src/(cg2*lam)  keeps PHYSICAL amplitude (SUB2 cancels).
    cg2 = B.asarray((SUB2 * params[:, 0]).reshape(Bn, 1, 1, 1))
    gam = B.asarray((SUB * np.maximum(params[:, 1], 0.02)).reshape(Bn, 1, 1, 1))
    Gc = params[:, 2]
    trs = params[:, 3]
    sig = params[:, 4]
    x = np.arange(L)
    g3 = np.meshgrid(x, x, x, indexing="ij")
    r2 = sum((gg - L // 2) ** 2 for gg in g3)
    # per-rule source (width sigma), zero-mean
    src_np = np.empty((Bn, L, L, L))
    for i in range(Bn):                      # host-side init, once
        s = np.exp(-r2 / (2.0 * max(sig[i], 1.5) ** 2))
        s -= s.mean()
        src_np[i] = 16.0 * math.pi * Gc[i] * s
    src = B.asarray(SUB2 * src_np)
    hb = B.asarray(np.zeros((Bn, L, L, L)))
    hbp = hb
    step = _step_newton_j if jit else _step_newton
    for t in range(T):
        hb, hbp = step(hb, hbp, cg2, gam, src)
    B.sync(hb)
    hbar00 = B.to_np(hb)
    # lattice spectral operators (host): lam = eigenvalue of  -Laplacian  >= 0
    k1 = 2.0 * math.pi * np.fft.fftfreq(L)
    K = np.meshgrid(k1, k1, k1, indexing="ij")
    lam = sum(2.0 - 2.0 * np.cos(k) for k in K); lam[0, 0, 0] = 1.0
    conv_err = np.empty(Bn); h_ratio = np.empty(Bn); defl_ratio = np.empty(Bn)
    for i in range(Bn):
        if not np.isfinite(hbar00[i]).all() or np.abs(hbar00[i]).max() > 1e6:
            conv_err[i] = np.inf; h_ratio[i] = np.nan; defl_ratio[i] = np.nan
            continue
        # analytic fixed point of THIS rule's own operator:
        #   cg2 * Lap h + src = 0  ->  h_k = src_k / (cg2 * lam)
        sk = np.fft.fftn(src_np[i]); sk[0, 0, 0] = 0.0
        h_static = np.real(np.fft.ifftn(sk / (params[i, 0] * lam)))
        nrm = np.abs(h_static).max() + 1e-30
        conv_err[i] = float(np.abs(hbar00[i] - h_static).max() / nrm)
        # Newton reference:  Lap phi = 4 pi G s  ->  phi_k = -4 pi G s_k / lam
        s_only = src_np[i] / (16.0 * math.pi * max(Gc[i], 1e-12))
        pk = np.fft.fftn(4.0 * math.pi * max(Gc[i], 1e-12) * s_only); pk[0, 0, 0] = 0.0
        phi = np.real(np.fft.ifftn(-pk / lam))
        # observation map, tr_sign semantics ALIGNED WITH tensor_qca:
        #   tr_sign = 1  -> correct trace-reverse, h00 = hbar00/2
        #   tr_sign = 0  -> trace-reverse OMITTED (falsifier), h00 = hbar00
        # correct map gives cg2*h00/phi = -2 (GR: hbar00=-4phi at cg2=c^2=1);
        # the falsifier lands at -4 and must fail S2/S3.
        h00 = hbar00[i] * (0.5 if trs[i] > 0.5 else 1.0)
        m = np.abs(phi) > 0.25 * np.abs(phi).max()
        h_ratio[i] = params[i, 0] * np.median(h00[m] / phi[m]) if m.any() else np.nan
        # Born deflection: phi_h = -cg2*h00/2 (= phi for the correct map)
        c = L // 2
        phi_h = -params[i, 0] * 0.5 * h00[:, :, c]
        phi_s = phi[:, :, c]
        n_t = 1.0 - 2.0 * phi_h
        n_s = 1.0 - phi_s
        b = (c + max(int(2 * sig[i]), 3)) % L
        # WEAK-FIELD Born ratio (pathB lesson relearned): divide-by-n keeps a
        # finite-amplitude O(phi) correction that drifts with L (1.78@L20 ->
        # 1.63@L32 for the good rule). The linearized integrals make the
        # ratio amplitude- and box-independent: 2 iff phi_h == phi.
        at = -np.sum(np.gradient(n_t, axis=1)[:, b])
        asc = -np.sum(np.gradient(n_s, axis=1)[:, b])
        defl_ratio[i] = at / asc if abs(asc) > 1e-12 else np.nan
    return {"newton_conv": conv_err, "h00_over_phi": h_ratio,
            "deflection_ratio": defl_ratio}


# ----------------------------------------------------------------------
# the drop-in payload
# ----------------------------------------------------------------------
def evaluate_tensor_batch(params, c_matter=1.0, gw_delta=0.05,
                          quick=True, jit=True):
    """params: (Bn,5) host array. Returns per-rule screening columns +
    pass flags. This is TIER-1 ONLY: survivors must be re-judged by the
    full tensor_qca + emergence_judge (tier 2)."""
    params = np.asarray(params, float)
    tt = screen_tt(params, Nz=96 if quick else 192, T=120 if quick else 240,
                   c_matter=c_matter, jit=jit)
    nw = screen_newton(params, L=20 if quick else 32,
                       T=700 if quick else 1800, jit=jit)   # sub-cycled: 4x steps
    out = {}
    out.update(tt); out.update(nw)
    out["S1_tt"] = (tt["tt_retention"] > 0.5) & (tt["gauge_growth"] < 2.0)
    out["J5_gw"] = tt["gw_dev"] < gw_delta
    with np.errstate(all="ignore"):
        # correct trace-reverse map gives cg2*h00/phi = -2 (see screen_newton)
        out["S2_newton"] = ((np.abs(nw["h00_over_phi"] + 2.0) < 0.5)
                            & (nw["newton_conv"] < 0.15))
        out["S3_eddington"] = np.abs(nw["deflection_ratio"] - 2.0) < 0.35
    out["S2_newton"] &= np.isfinite(nw["h00_over_phi"])
    out["S3_eddington"] &= np.isfinite(nw["deflection_ratio"])
    out["screen_pass"] = out["S1_tt"] & out["S2_newton"] & out["S3_eddington"]
    out["screen_pass_gw"] = out["screen_pass"] & out["J5_gw"]
    return out


# ======================================================================
# CONTRACT ADAPTER  (TENSOR_CAMPAIGN_INTERFACE.md, interface (1), lane A)
# ======================================================================
PARAM_NAMES = ["cg2", "gamma", "G", "tr_sign", "sigma"]   # = tensor_qca's
GW_TOL = 0.05        # tier-1 J5 tolerance (measurement floor); tier-2 tightens

_REF_SPEED = {}      # per-process cache of the reference TT speed


def _tt_speed_ref(quick=True):
    """measured TT packet speed of the cg2=1 REFERENCE rule with the same
    protocol as every screened rule -> lattice-dispersion systematics cancel
    in the ratio, so gw_speed = tt_speed/ref ~= sqrt(cg2), target 1.0 at the
    light cone (tensor_qca's null-box cone = cg2 = 1)."""
    key = bool(quick)
    if key not in _REF_SPEED:
        p = np.array([[1.0, 0.02, 0.02, 1.0, 2.5]])
        r = screen_tt(p, Nz=96 if quick else 192, T=120 if quick else 240)
        _REF_SPEED[key] = float(r["tt_speed"][0])
    return _REF_SPEED[key]


def sample_tensor_prior(n, seed=0):
    """physics-shaped prior over PARAM_NAMES. cg2 range includes the physical
    light-cone target 1.0 (screenable thanks to sub-cycling, bound 4/3).
    tr_sign in {1, 0} per tensor_qca semantics (0 = broken trace-reverse)."""
    rng = np.random.default_rng(seed)
    p = np.zeros((n, 5))
    p[:, 0] = 10 ** rng.uniform(-1.0, 0.1, n)           # cg2 in [0.1, 1.26]
    p[:, 1] = 10 ** rng.uniform(-2.5, -0.8, n)          # gamma
    # G floor raised 1e-3 -> 1e-2 (tier-1/2 calibration, 2026-07-20): tier-2's
    # 1/r-correlation judge is SNR-limited and cannot certify wells below
    # ~1e-2; tier-1's ratio judges are scale-free and passed them anyway.
    p[:, 2] = 10 ** rng.uniform(-2.0, -0.7, n)          # G in [0.01, 0.2]
    p[:, 3] = np.where(rng.random(n) < 0.85, 1.0, 0.0)  # tr_sign falsifier arm
    p[:, 4] = rng.uniform(1.5, 3.5, n)                  # sigma
    return p


sample_tensor_rules = sample_tensor_prior               # back-compat alias


def screen_tensor_rules(params_batch, quick=True, c_matter_rel=1.0, jit=True):
    """CONTRACT interface (1): (Bn, 5) host array -> per-rule column dict.
    c_matter_rel: matter speed relative to the lattice light cone (harness
    may pass the walker sector's measured v/c, e.g. 0.993; default 1.0)."""
    P = np.atleast_2d(np.asarray(params_batch, dtype=float))
    ref = _tt_speed_ref(quick) * float(c_matter_rel)
    r = evaluate_tensor_batch(P, c_matter=ref, gw_delta=GW_TOL,
                              quick=quick, jit=jit)
    gw_speed = r["tt_speed"] / ref
    stable = (~r["blown"]) & np.isfinite(r["h00_over_phi"])
    tt_dof = np.where(r["S1_tt"], 2, 6).astype(int)     # cheap DOF proxy
    return {
        # ---- contract columns (harness depends on these names) ----
        "passes_screen": r["screen_pass_gw"],
        "stable": stable,
        "tt_dof": tt_dof,
        "gw_speed": gw_speed,
        "gw_speed_ok": np.abs(gw_speed - 1.0) < GW_TOL,
        "newton_proxy": -r["h00_over_phi"],             # target +2.0
        "emergence_proxy": tt_dof.astype(float),
        # ---- raw diagnostics (pass-through, harness may log) ----
        "tt_speed": r["tt_speed"], "tt_retention": r["tt_retention"],
        "gauge_growth": r["gauge_growth"], "newton_conv": r["newton_conv"],
        "deflection_ratio": r["deflection_ratio"],
        "S1_tt": r["S1_tt"], "S2_newton": r["S2_newton"],
        "S3_eddington": r["S3_eddington"], "J5_gw": r["J5_gw"],
    }


if __name__ == "__main__":
    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("TENSOR BATCH SCREEN (tier-1) contract self-test\n" + "=" * 64)
    # discrimination through the CONTRACT interface. The good probe is now
    # the PHYSICAL light-cone rule cg2 = 1 (screenable via sub-cycling);
    # tr_sign = 0 is tensor_qca's falsifier (trace-reverse omitted).
    probes = np.array([
        [1.00, 0.05, 0.02, 1.0, 2.5],    # good: light-cone rule, correct map
        [1.00, 0.05, 0.02, 0.0, 2.5],    # falsifier: no trace-reverse
        [0.25, 0.05, 0.02, 1.0, 2.5],    # slow graviton (c_g = c/2): J5 kills
        [2.00, 0.05, 0.02, 1.0, 2.5],    # beyond CFL 4/3: must blow & fail
    ])
    res = screen_tensor_rules(probes)
    rows = ["good", "no tr-reverse", "slow graviton", "CFL violator"]
    print(f"ref TT speed (cg2=1) = {_tt_speed_ref():.3f}\n")
    print(f"{'rule':>14} {'gw_spd':>7} {'newt':>6} {'defl':>6} {'dof':>4} "
          f"{'stab':>5} {'gwOK':>5} {'PASS':>5}")
    for i, r in enumerate(rows):
        print(f"{r:>14} {res['gw_speed'][i]:7.3f} {res['newton_proxy'][i]:6.3f} "
              f"{res['deflection_ratio'][i]:6.3f} {res['tt_dof'][i]:>4} "
              f"{str(res['stable'][i])[0]:>5} {str(res['gw_speed_ok'][i])[0]:>5} "
              f"{str(res['passes_screen'][i])[0]:>5}")
    ok = (bool(res["passes_screen"][0]) and not bool(res["S2_newton"][1])
          and not bool(res["gw_speed_ok"][2]) and not bool(res["stable"][3]))
    json.dump({k: v.tolist() for k, v in res.items()},
              open(os.path.join(DIR, "..", "data", "results", "tensor_batch_selftest.json"), "w"), indent=1)
    print("\nDISCRIMINATION:", "PASS (good passes; falsifier/slow-gw/CFL killed)"
          if ok else "CHECK — see table")
    # mini funnel over the shipped prior (the shape the campaign will see)
    pr = sample_tensor_prior(64, seed=0)
    f = screen_tensor_rules(pr)
    print(f"\nprior funnel (64): stable {int(f['stable'].sum())} | "
          f"S1 {int(f['S1_tt'].sum())} | S2 {int(f['S2_newton'].sum())} | "
          f"S3 {int(f['S3_eddington'].sum())} | gwOK {int(f['gw_speed_ok'].sum())} "
          f"| pass_screen {int(f['passes_screen'].sum())}")
