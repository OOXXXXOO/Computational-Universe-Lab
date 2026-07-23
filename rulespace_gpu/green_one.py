"""green_one -- M3 (North-Star mainline, lane B): 全绿一号 assembly.

ONE construction, ONE run: assemble ALL five parts and drive the full
pre-registered M3 checkpoint table + the falsification battery.  Honest to the
charter: pre-registered bars only tighten; the battery is replayed every run;
no tuning to pass; single-criterion misses get at most ONE calibration round.

THE CONSTRUCTION (plan §一, the unique target):
  (1) MATTER  : 4-component Dirac-pair walker (chirality-doubled, R10 op
                language) -- the EXACT momentum-key-flux generator.
  (2) GEOMETRY: tensor coin field hbar_munu on the T3 SHARED central-1 calculus
                -- wide null box eta_c^{mn} D_m D_n + lag-free (no-lag) de-Donder
                constraint damping (M1).
  (3) SOURCE  : geometry source = R10 EXACT averaged key-current Jbar
                (transverse-avg x two-step time-sum), NOT the on-site bilinear
                (M2, the leakage ~1e-18 win).
  (4) SINK    : outgoing-wave sponge at the box edge; certificates in the BULK
                (fills M2's un-sinked field-energy growth).
  (5) FEEDBACK: trace-reversed h steers the walker's per-axis coin every step
                (theta_fields: c_i = cos th0 (1 + (h00+h_ii)/2)).  CLOSED LOOP
                -- M2 left this open; M3 turns it on.  R10's generator theorem
                guarantees the momentum balance Db_a + divF = Phi stays
                machine-exact even with an x-dependent (fed-back) coin, so the
                feedback force is booked, not leaked.

WHAT IS REUSED (never modified -- lane A / other agents' files):
  green_m2   : BatchWalk, step_account_b, build_source, source residual /
               leakage, live-row conservation (M2, 4/4).
  staggered_geometry : sponge cert, null-box controls, T3 calculus (M1).
  tensor_coin_feedback : theta_fields (h->coin), judge_newton (h00/phi=2,
               1/r tail, Eddington Born, deflection), _sponge_field.
  emergence_judge : judge_dof (N_prop, projection-free Riemann-SVD),
               judge_gauge (C decay, gauge->physical conversion).
  tier2_gw   : J5 spectral graviton group velocity.
  r10 / r13  : exact current generator + stride bridge (Jbar consumable).

HONEST TIERS (report keeps these separate):
  定理  : the R10/R13 momentum balance (machine-exact, ~1e-19) -- a theorem.
  实证  : N_prop=2, gauge suppression, Newton factor 2, Eddington 2, endurance
          stability -- MEASURED positive results of THIS construction.
  代理  : J5 uses c_matter=0.993 (imported walker constant) and the tier-2
          compact-leapfrog graviton at the rule's cg2 -- a proxy comparison.
  工程  : sponge, batching, caches.
  NOT   : non-linear GR (perihelion/strong field), quantum gravity, "world is
          a CA".  These are written dead; the report must not imply them.

Run:  RULESPACE_BACKEND=numpy python -m rulespace_gpu.green_one   [--full]
"""
import argparse
import json
import math
import os

import numpy as np

from . import backend as B
from . import emergence_judge as ej
from . import green_m2 as gm2
from . import spin2_evolver as s2
from . import staggered_geometry as sg
from . import tensor_coin_feedback as tcf
from . import tensor_qca as tq
from . import tier2_gw as t2

from experiments import r10_current_generator as r10
from experiments import r13_stride_bridge as r13

DIR = os.path.dirname(os.path.abspath(__file__))
PK = ej.PK
_lap_wide = ej._lap_wide_batch
_dsp = ej._dsp
SIXTEEN_PI = 16.0 * math.pi

# ---- pre-registered M3 bars (only tighten; never relax) -------------------
J1_DRIFT = 1e-10          # walker norm drift @ T=2000
NPROP_TARGET = 2
CDECAY_ORDERS = 6.0       # >= 6 orders (ratio <= 1e-6)
CONVERT_PASS = 1e-3       # gauge->physical conversion
ANOMALY_PASS = 1e-10      # gauge-anomaly leakage (16 pi G * source residual)
NEWTON_TOL = 0.02         # h00/phi = 2.00 +- 0.02
INVR_CORR = 0.99          # 1/r tail correlation
EDD_TOL = 0.02            # Eddington = 2.00 +- 0.02
CONS_PASS = 1e-12         # T-row residual in bulk
J5_TOL = 1e-2             # |c_gw/c_matter - 1|
ISO_PASS = 0.06           # axis c spread (non-blocking)


# ===========================================================================
#  PART A.  the fed-back 4-component Dirac-pair walker layer builder
#  Mirrors r10.build_4comp_layers EXACTLY when th_fields = [th0,th0,th0], so the
#  R10 exact-current property is preserved; per-axis FIELD coins add the
#  feedback (an x-dependent unitary -> R10's exact force term Phi, booked).
# ===========================================================================
_H2X, _H2Y = r10.had(kind="x"), r10.had(kind="y")


def _emb4(U2, block):
    U = np.eye(4, dtype=complex)
    o = 0 if block == 0 else 2
    U[o:o + 2, o:o + 2] = U2
    return U


def _field_coin4(th):
    """(*grid,) angle field -> (*grid,4,4) coin on pairs (0,1),(2,3), r10 convention
    (coin_mat: diag cos, off-diag i sin).  Scalar th reproduces r10's coin exactly."""
    th = np.asarray(th, dtype=float)
    c = np.cos(th)
    s = 1j * np.sin(th)
    U = np.zeros(th.shape + (4, 4), dtype=complex)
    for (i, j) in ((0, 1), (2, 3)):
        U[..., i, i] = c
        U[..., i, j] = s
        U[..., j, i] = s
        U[..., j, j] = c
    return U


def build_4comp_layers_fb(shape, th_fields, dm):
    """R10 4-comp Dirac-pair layers with PER-AXIS coin FIELDS (feedback).
    th_fields: list of 3 arrays (grid-shaped, possibly batched leading dims)."""
    P = np.zeros((4, 4), dtype=complex)
    P[0, 0] = 1
    P[3, 3] = 1
    coin4 = [r10.Walk.unitary(_field_coin4(th_fields[a])) for a in range(3)]
    mass = r10.Walk.unitary(r10.coin_mat(dm, C=4, pair=(0, 2))
                            @ r10.coin_mat(dm, C=4, pair=(1, 3)))

    def layers_fn(t):
        order = (0, 1, 2) if t % 2 == 0 else (2, 1, 0)
        L = []
        for ax in order:
            if ax == 0:
                L += [r10.Walk.unitary(_emb4(_H2X, 0) @ _emb4(_H2X, 1))]
            elif ax == 1:
                L += [r10.Walk.unitary(_emb4(_H2Y, 0) @ _emb4(_H2Y, 1))]
            L.append(r10.Walk.shift(ax, P, +1))
            if ax == 0:
                L += [r10.Walk.unitary(_emb4(_H2X.conj().T, 0) @ _emb4(_H2X.conj().T, 1))]
            elif ax == 1:
                L += [r10.Walk.unitary(_emb4(_H2Y.conj().T, 0) @ _emb4(_H2Y.conj().T, 1))]
            L.append(coin4[ax])
        L.append(mass)
        return L
    return layers_fn


def verify_fb_reduces_to_r10(seed=0):
    """with a UNIFORM coin field (= th0 everywhere) the fed-back layers must be
    bit-identical to r10.build_4comp_layers (exactness of the M2 source is thus
    inherited by the feedback build)."""
    shape = (8, 8, 8)
    rng = np.random.default_rng(seed)
    psi = rng.standard_normal(shape + (4,)) + 1j * rng.standard_normal(shape + (4,))
    th0, dm = 0.5, 0.25
    lf0 = r10.build_4comp_layers(shape, th0, dm)
    ths = [th0 * np.ones(shape) for _ in range(3)]
    lf1 = build_4comp_layers_fb(shape, ths, dm)
    w = r10.Walk(shape, 4)
    p0, pk0, f0 = r13.step_account(w, lf0(0), psi.copy())
    p1, pk1, f1 = r13.step_account(w, lf1(0), psi.copy())
    d_state = float(np.abs(p0 - p1).max())
    d_pack = max(float(np.abs(F0 - F1).max())
                 for (_, _, F0), (_, _, F1) in zip(pk0, pk1)) if pk0 else 0.0
    return {"state_max_diff": d_state, "packet_max_diff": d_pack,
            "identical": bool(d_state < 1e-300 and d_pack < 1e-300)}


# ===========================================================================
#  PART B.  the geometry step (null box + no-lag de-Donder), all switches
# ===========================================================================
def _geom_step(state, cg2, kappa, src, tr_sign=1.0, damping=True, lag=False):
    """wide null box eta_c D D + lag-free de-Donder solve on hbar_{0nu}.
    Switches expose the falsification controls WITHOUT a separate code path:
      tr_sign=0 : drop the h(t-1)/2c^2 term (breaks constraint closure).
      damping=False : pure null box, no de-Donder solve (constraint free).
      lag=True : use a TIME-LAGGED constraint (off the constraint surface)."""
    h1, h2, h3, h4 = state
    c2 = float(cg2)
    nxt = 2.0 * h2 - h4 + c2 * (_lap_wide(h2) + src)
    if not damping:
        return (nxt, h1, h2, h3)
    fac = 1.0 / (1.0 + kappa / (2 * c2))
    for nu in range(4):
        c0 = PK[(0, nu)]
        if lag:
            C = -(1.0 / c2) * 0.5 * (h1[..., c0] - h3[..., c0])
            for j in (1, 2, 3):
                C = C + _dsp(h2[..., PK[(j, nu)]], j)
            nxt[..., c0] = nxt[..., c0] + kappa * c2 * C
        else:
            S = np.zeros(h1.shape[:-1])
            for j in (1, 2, 3):
                S = S + _dsp(h1[..., PK[(j, nu)]], j)
            nxt[..., c0] = fac * (nxt[..., c0]
                                  + kappa * (tr_sign * h2[..., c0] / (2 * c2) + S))
    return (nxt, h1, h2, h3)


# ===========================================================================
#  PART C.  THE M3 CONSTRUCTION as an emergence_judge-compatible rule
#  null box + LIVE R10 exact Jbar source + h->coin feedback + sponge.
# ===========================================================================
def make_green_one_rule(mode="jbar", cg2=0.25, kappa=0.5, G_m=0.02, th0=0.5,
                        dm=0.25, amp=0.02, feedback=True, sponge_w=0,
                        sponge_max=0.4, tr_sign=1.0, src_sign=1.0, damping=True,
                        lag=False, seed=11):
    c2 = float(cg2)
    walk = gm2.BatchWalk((0,), 4)
    cache = {"last": None, "psi": None, "packets_prev": None, "count": 0,
             "step_t": 0, "gshape": None, "static_layers": None, "sp": None}

    def _static_layers(gshape):
        if cache["static_layers"] is None or cache["gshape"] != gshape:
            cache["gshape"] = gshape
            cache["static_layers"] = r10.build_4comp_layers(gshape, th0=th0, dm=dm)
            if sponge_w > 0:
                cache["sp"] = tcf._sponge_field(gshape[-1], sponge_w, sponge_max)
        return cache["static_layers"]

    def init_walker(h):
        rng = np.random.default_rng(seed + cache["count"])
        cache["count"] += 1
        shape = h.shape[:-1]
        p = (rng.standard_normal(shape + (4,))
             + 1j * rng.standard_normal(shape + (4,)))
        for _ in range(3):
            for ax in (-4, -3, -2):
                p = (np.roll(p, 1, ax) + np.roll(p, -1, ax) + 2 * p) / 4
        p *= amp / (np.sqrt(np.mean(np.abs(p) ** 2)) + 1e-300)
        cache["psi"] = p
        cache["packets_prev"] = None
        cache["step_t"] = 0

    def step(state):
        h = state[0]
        gshape = h.shape[-4:-1]
        walk.shape = gshape
        walk.ndim = len(gshape)
        _static_layers(gshape)
        if cache["last"] is not h:
            init_walker(h)
        psi = cache["psi"]
        t = cache["step_t"]
        if feedback:
            h_phys = tq.trace_reverse_packed(h)
            ths, _cs = tcf.theta_fields(h_phys, th0)     # 3 per-axis coin fields
            layers = build_4comp_layers_fb(gshape, ths, dm)(t)
        else:
            layers = cache["static_layers"](t)
        psi_next, pk_t, fo_t = gm2.step_account_b(walk, layers, psi)
        pk_prev = cache["packets_prev"] if cache["packets_prev"] is not None else pk_t
        bonds = [walk.bond(psi_next, a) for a in range(3)]
        rho = np.sum(np.abs(psi_next) ** 2, axis=-1)
        if mode == "onsite":
            T = gm2._onsite_stress(psi_next, (math.cos(th0),) * 3)
        else:
            T = gm2.build_source(walk, (pk_t, pk_prev), bonds, rho, mode)
        cache["packets_prev"] = pk_t
        cache["psi"] = psi_next
        cache["step_t"] = t + 1

        sp_axes = tuple(range(T.ndim - 4, T.ndim - 1))
        src = src_sign * (-SIXTEEN_PI) * G_m * (T - T.mean(axis=sp_axes, keepdims=True))
        new_state = _geom_step(state, c2, kappa, src, tr_sign, damping, lag)
        if cache["sp"] is not None:
            nxt0 = new_state[0] - cache["sp"][..., None] * (state[0] - state[1])
            new_state = (nxt0,) + new_state[1:]
        cache["last"] = new_state[0]
        return new_state

    fb = ",fb" if feedback else ""
    sk = f",sponge{sponge_w}" if sponge_w > 0 else ""
    return {"name": f"green-one null-box+{mode}+Jbar{fb}{sk} (G_m={G_m})",
            "n_levels": 4, "cg2": cg2, "step": step}


# ===========================================================================
#  PART D.  ENDURANCE closed loop (J1) -- feedback + sponge, T=2000, bulk cert
# ===========================================================================
def endurance_loop(N=12, T=2000, cg2=0.25, kappa=0.5, G=0.03, th0=0.5, dm=0.25,
                   feedback=True, sponge_w=3, sponge_max=0.4, seed=5):
    """single-trajectory co-evolution: R10 4-comp matter <-> null-box geometry,
    LIVE Jbar source, h->coin feedback, sponge sink.  Measures walker norm drift
    (unitary => machine-floor), bulk field-energy stability (the real slow-escape
    guard), and the live R10 momentum balance INCLUDING the feedback force."""
    shape = (N, N, N)
    w = r10.Walk(shape, 4)
    psi = r10.gaussian_psi(shape, 4, k0=(0.0, 0.0, 0.0), sig=N / 6.0, seed=seed)
    state = tuple(np.zeros(shape + (10,)) for _ in range(4))
    sp = tcf._sponge_field(N, sponge_w, sponge_max) if sponge_w > 0 else None
    b0 = sponge_w + 2
    b1 = N - sponge_w - 2
    if b1 - b0 < 2:                       # tiny box: keep a non-empty interior
        b0, b1 = 1, N - 1
    bulk = (slice(b0, b1),) * 3
    packets_prev = None
    n0 = float(np.sum(np.abs(psi) ** 2))
    norms, fields = [], []
    worst_cons = 0.0
    blow = False
    warm = T // 5
    samp = max(1, (T - warm) // 12)
    for t in range(T):
        if feedback:
            h_phys = tq.trace_reverse_packed(state[0])
            ths, _cs = tcf.theta_fields(h_phys, th0)
            lf = build_4comp_layers_fb(shape, ths, dm)
        else:
            lf = r10.build_4comp_layers(shape, th0, dm)
        # live momentum balance (R10 theorem) on the current Jbar, bulk only.
        if t % 50 == 0:
            b_pre = [w.bond(psi, a) for a in range(3)]
            psi1, pk1, fo1 = r13.step_account(w, lf(t), psi)
            lf2 = (build_4comp_layers_fb(shape, ths, dm) if feedback
                   else r10.build_4comp_layers(shape, th0, dm))
            psi2, pk2, fo2 = r13.step_account(w, lf2(t + 1), psi1)
            for a in range(3):
                lhs = r13.cell_avg(w.bond(psi2, a) - b_pre[a], 3)
                rhs = np.zeros(shape)
                for pk in (pk1, pk2):
                    for (aa, bax, F) in pk:
                        if aa == a:
                            rhs -= r13.div_c2(r13.transverse_avg(F, 3, bax), bax)
                rhs += r13.cell_avg(fo1[a] + fo2[a], 3)
                worst_cons = max(worst_cons, float(np.abs((lhs - rhs)[bulk]).max()))
        else:
            psi1, pk1, fo1 = r13.step_account(w, lf(t), psi)
        # drive geometry with the live Jbar source, then sponge
        bonds = [w.bond(psi1, a) for a in range(3)]
        rho = np.sum(np.abs(psi1) ** 2, axis=-1)
        pk_prev = packets_prev if packets_prev is not None else pk1
        T_src = gm2.build_source(w, (pk1, pk_prev), bonds, rho, "jbar")
        src = -SIXTEEN_PI * G * (T_src - T_src.mean(axis=(0, 1, 2), keepdims=True))
        state = _geom_step(state, cg2, kappa, src)
        if sp is not None:
            nxt0 = state[0] - sp[..., None] * (state[1] - state[2])
            state = (nxt0,) + state[1:]
        if not np.all(np.isfinite(state[0])):
            blow = True
            break
        packets_prev = pk1
        psi = psi1
        if t >= warm and t % samp == 0:
            norms.append(float(np.sum(np.abs(psi) ** 2)))
            fields.append(float(np.sum(((state[0] - state[1]) ** 2)[bulk])))
    drift = float(abs(norms[-1] / norms[0] - 1.0)) if len(norms) > 1 else float("nan")
    growth = (float(fields[-1] / (fields[len(fields) // 2] + 1e-300))
              if len(fields) > 2 else float("nan"))
    return {"T": T, "walker_norm_drift": drift, "norm_final_over_start_full":
            float(np.sum(np.abs(psi) ** 2) / n0),
            "bulk_field_energy_growth_late": growth,
            "live_row_conservation_bulk_max": worst_cons,
            "stable": bool(not blow), "feedback": feedback, "sponge_w": sponge_w}


# ===========================================================================
#  PART E.  checkpoint drivers (each probes THE construction in its regime)
# ===========================================================================
def cp_emergence(N=12, quick=True, **kw):
    """涌现A (N_prop) + 涌现B (C decay, gauge->physical conversion) on the full
    fed-back construction."""
    T_A, trials = (384, 6) if quick else (640, 10)
    T_B = 400 if quick else 600
    rule = make_green_one_rule(feedback=True, **kw)
    a = ej.judge_dof(rule, N=N, T=T_A, trials=trials)
    b = ej.judge_gauge(rule, N=N, T=T_B)
    orders = float(np.log10(1.0 / (b["c_decay_ratio"] + 1e-300)))
    return {"n_prop_all": a["n_prop_all"], "n_prop": a["n_prop"],
            "lightcone_ok": bool(a["lightcone_ok"]), "stable_A": bool(a["stable"]),
            "speed_spread": a["speed_spread"], "per_k": a["per_k"],
            "c_decay_ratio": b["c_decay_ratio"], "c_decay_orders": orders,
            "c_decay_rate": b["c_decay_rate_per_step"],
            "gauge_conversion": b["gauge_conversion"], "stable_B": bool(b["stable"]),
            "tt_survival": b["tt_survival"]}


def cp_anomaly_conservation():
    """规范反常 (16 pi G * source de-Donder residual) + 守恒 (live R10 balance).
    Uses green_m2's certified source residual (Jbar ~1e-19)."""
    res = gm2.checkpoint_source_residual()
    lk = gm2.leakage_test(res)
    Gs = sorted(lk["jbar"].keys())
    leak = max(lk["jbar"][G]["leak"] for G in Gs)
    return {"source_residual_jbar": res["jbar"], "source_residual_onsite": res["onsite"],
            "gauge_anomaly_leak_max": leak,
            "leak_ratio_onsite_over_jbar": lk["leak_ratio_onsite_over_jbar"]}


def cp_newton(L=48):
    """牛顿 (h00/phi=2, 1/r tail) + 偏折 (Eddington Born).  tcf.judge_newton
    relaxes hbar under the STATIC measured source (trace-reverse geometry);
    the factor-2 is a trace-reversal property the shared operator inherits."""
    r = tcf.judge_newton(L=L)
    return {"h00_over_phi": r["h00_over_phi_median"], "h00_over_phi_cv": r["h00_over_phi_cv"],
            "hbar00_over_phi": r["hbar00_over_phi_median"],
            "invr_fit_corr": r["invr_fit_corr"], "poisson_residual": r["poisson_residual"],
            "eddington_ratio": r["eddington_ratio"],
            "deflection_toward_blob": bool(r["deflection_toward_blob"]),
            "deflection_dy": r["deflection_dy"],
            "tolman_3p_over_rho": r.get("trace_3p_over_rho")}


def cp_j5(cg2=0.25):
    """J5 |c_gw/c_matter - 1| < 1e-2 (spectral graviton group velocity, tier2_gw
    proxy).  ALSO reports the 3D wide-null-box CFL cap (cg2 <= 1/3 for stability,
    since sin^2 w = cg2 * sum_j sin^2 k_j <= 1 with max sum = 3): the emergence
    sector FORCES a slow graviton, structurally below the matter speed."""
    params = np.array([[cg2, 0.05, 0.02, 1.0, 2.5]])
    r = t2.tier2_gw(params)
    cfl_cg2 = 1.0 / 3.0
    kc = 2.0 * np.pi * float(np.mean(t2._PROBE_MODES)) / 192
    return {"cg2": cg2, "c_gw": float(r["gw_speed"][0]), "c_matter": t2.C_MATTER_WALKER,
            "gw_ratio": float(r["gw_ratio"][0]), "gw_analytic": float(r["gw_analytic"][0]),
            "cfl_max_cg2_3d_widebox": cfl_cg2,
            "c_gw_at_cfl_cap": float(t2.analytic_group_velocity(cfl_cg2, kc)),
            "gw_ratio_at_cfl_cap": float(t2.analytic_group_velocity(cfl_cg2, kc)
                                         / t2.C_MATTER_WALKER)}


def cp_isotropy(N=12, quick=True, **kw):
    """各向同性 (axis c spread, non-blocking) from judge_dof axis-aligned modes."""
    T_A, trials = (384, 6) if quick else (640, 10)
    rule = make_green_one_rule(feedback=True, **kw)
    a = ej.judge_dof(rule, N=N, T=T_A, trials=trials,
                     kmodes=((2, 0, 0), (0, 2, 0), (0, 0, 2)))
    vs = [e["v_meas"] for e in a["per_k"] if np.isfinite(e.get("v_meas", np.nan))]
    if len(vs) >= 2 and np.mean(vs) > 0:
        spread = float((max(vs) - min(vs)) / np.mean(vs))
    else:
        spread = float("nan")
    return {"axis_speeds": vs, "axis_c_spread": spread}


def wrong_sign_newton(L=44, sig=3.0, dm=1.5, th0=0.45, G=1.0, cg2=0.25, gamma=0.06,
                      T_avg=24, max_steps=4000, src_sign=-1.0):
    """judge_newton's static relaxation with the SOURCE sign flipped ONLY, while
    the phi reference keeps a FIXED (positive-G, attractive) sign.  Correct
    source: h00 = +2 phi (ratio +2, correlation +1).  Wrong source: h00 = -2 phi
    (ratio -2, correlation -1) -> the Newton criterion FAILS by 4 sigma.  This is
    the robust, clip-free teeth for the sign-blind 'wrong-sign source' control."""
    c0 = math.cos(th0)
    ctr = (L // 2,) * 3
    env, r2 = tcf._gauss3(L, ctr, sig)
    psi = env[..., None] * tcf.CHI_BLOB
    psi = psi / math.sqrt(float(np.sum(np.abs(psi) ** 2)))
    buf, p = [psi.copy()], psi.copy()
    for _ in range(T_avg + 1):
        p = tcf.walker_step(p, th0, th0, th0, dm, th0)
        buf.append(p.copy())
    Tacc = np.zeros((L, L, L, 10))
    for t in range(1, T_avg):
        Tacc += tcf.stress_tensor(buf[t - 1], buf[t], buf[t + 1], (c0, c0, c0))
    Tavg = Tacc / (T_avg - 1)
    T00 = Tavg[..., tcf.PK00]
    src = src_sign * (-tcf.SIXTEEN_PI) * G * (Tavg - Tavg.mean(axis=(0, 1, 2), keepdims=True))
    hb = np.zeros((L, L, L, 10))
    hbp = np.zeros((L, L, L, 10))
    for _ in range(max_steps):
        hb, hbp = tq.qca_step(hb, hbp, cg2, src, gamma), hb
    h00 = tq.trace_reverse_packed(hb)[..., tcf.PK00]
    rho_c = T00 - T00.mean()
    phi = s2._poisson_fft(rho_c, L, 4 * np.pi * abs(G))    # FIXED-sign attractive phi
    sl = (slice(None), ctr[1], ctr[2])
    phi_line = phi[sl]
    mask = np.abs(phi_line) > 0.05 * np.abs(phi_line).max()
    ratio = float(np.median((h00[sl] / phi_line)[mask]))
    corr = float(np.corrcoef((h00 - h00.mean()).ravel(), (2 * phi).ravel())[0, 1])
    return {"h00_over_phi": ratio, "h00_phi_corr": corr, "src_sign": src_sign}


# ===========================================================================
#  PART F.  falsification battery (each MUST fail >= 1 criterion)
# ===========================================================================
def falsification(N=12, quick=True):
    T_A, trials = (384, 6) if quick else (640, 10)
    T_B = 400 if quick else 600
    out = {}

    def emg(**kw):
        rule = make_green_one_rule(feedback=True, **kw)
        a = ej.judge_dof(rule, N=N, T=T_A, trials=trials)
        b = ej.judge_gauge(rule, N=N, T=T_B)
        return {"n_prop_all": a["n_prop_all"], "lightcone_ok": bool(a["lightcone_ok"]),
                "c_decay_ratio": float(b["c_decay_ratio"]),
                "gauge_conversion": float(b["gauge_conversion"]),
                "stable": bool(a["stable"] and b["stable"])}

    # tr_sign=0 : breaks the constraint closure -> gauge/DOF FAIL
    r = emg(tr_sign=0.0)
    r["fails"] = not (all(n == 2 for n in r["n_prop_all"])
                      and r["gauge_conversion"] < CONVERT_PASS
                      and r["c_decay_ratio"] < 1e-6)
    r["breaks"] = "N_prop / gauge suppression"
    out["tr_sign=0"] = r

    # no damping : no de-Donder solve -> constraint never decays -> FAIL
    r = emg(damping=False)
    r["fails"] = not (all(n == 2 for n in r["n_prop_all"])
                      and r["gauge_conversion"] < CONVERT_PASS
                      and r["c_decay_ratio"] < 1e-6)
    r["breaks"] = "C decay / gauge suppression"
    out["no_damping"] = r

    # lagged damping : off the constraint surface -> FAIL
    r = emg(lag=True)
    r["fails"] = not (all(n == 2 for n in r["n_prop_all"])
                      and r["gauge_conversion"] < CONVERT_PASS
                      and r["c_decay_ratio"] < 1e-6)
    r["breaks"] = "gauge suppression"
    out["lagged_damping"] = r

    # on-site source : source de-Donder residual O(1) -> gauge anomaly >> 1e-10
    res = gm2.checkpoint_source_residual()
    onsite_leak = SIXTEEN_PI * 0.18 * res["onsite"]
    out["onsite_source"] = {
        "source_residual": res["onsite"], "gauge_anomaly_leak": onsite_leak,
        "fails": bool(onsite_leak >= ANOMALY_PASS),
        "breaks": "gauge anomaly (< 1e-10)"}

    # wrong-sign source : h00 = -2 phi (repulsive) -> Newton ratio FAIL
    ws_bad = wrong_sign_newton(L=44, src_sign=-1.0)
    ws_ok = wrong_sign_newton(L=44, src_sign=+1.0)     # positive control (must be +2)
    out["wrong_sign_source"] = {
        "h00_over_phi_wrongsign": ws_bad["h00_over_phi"],
        "h00_phi_corr_wrongsign": ws_bad["h00_phi_corr"],
        "h00_over_phi_control": ws_ok["h00_over_phi"],
        "fails": bool(abs(ws_bad["h00_over_phi"] - 2.0) > NEWTON_TOL
                      and abs(ws_ok["h00_over_phi"] - 2.0) < 0.1),
        "breaks": "Newton ratio h00/phi (sign)"}

    out["battery_has_teeth"] = bool(all(out[k]["fails"] for k in
                                        ("tr_sign=0", "no_damping", "lagged_damping",
                                         "onsite_source", "wrong_sign_source")))
    return out


# ===========================================================================
#  driver
# ===========================================================================
def run_all(quick=True, endurance_T=2000, endurance_N=12, newton_L=48, cg2=0.25,
            g_m=0.02, g_m_calib=1e-3):
    out = {"backend": B.NAME, "cg2": cg2, "G_m": g_m}
    out["verify_fb"] = verify_fb_reduces_to_r10()
    esw = 3 if endurance_N >= 16 else 2
    out["j1_endurance"] = endurance_loop(N=endurance_N, T=endurance_T,
                                         cg2=cg2, feedback=True, sponge_w=esw)
    out["emergence"] = cp_emergence(quick=quick, cg2=cg2, sponge_w=0, G_m=g_m)
    out["anomaly_conservation"] = cp_anomaly_conservation()
    out["newton"] = cp_newton(L=newton_L)
    out["j5"] = cp_j5(cg2=cg2)
    out["isotropy"] = cp_isotropy(quick=quick, cg2=cg2, G_m=g_m)
    out["falsification"] = falsification(quick=quick)
    # ONE allowed calibration round (the linear-probe coupling G_m): if the
    # live-source injection floors emergence-B's C-decay below 6 orders, re-run
    # the emergence sector at a smaller G_m (the ONLY knob touched; Newton uses
    # its own static G, J5 its own cg2, conservation is the R10 theorem).
    em = out["emergence"]
    if em["c_decay_orders"] < CDECAY_ORDERS:
        out["calibration"] = {
            "reason": "emergence-B C-decay floored by live-source stride-1 "
                      "injection; lower the linear-probe coupling G_m",
            "G_m_calib": g_m_calib,
            "emergence": cp_emergence(quick=quick, cg2=cg2, sponge_w=0, G_m=g_m_calib)}
    return out


def _checktable(out):
    j1 = out["j1_endurance"]
    em = out["emergence"]
    ac = out["anomaly_conservation"]
    nw = out["newton"]
    j5 = out["j5"]
    iso = out["isotropy"]

    rows = []
    # J1
    c = j1["walker_norm_drift"] < J1_DRIFT and j1["stable"]
    rows.append(("J1 stability (walker norm drift @ T=%d)" % j1["T"],
                 f"{j1['walker_norm_drift']:.2e} (stable={j1['stable']})",
                 "< 1e-10", c, True))
    # 涌现A
    c = all(n == NPROP_TARGET for n in em["n_prop_all"]) and em["stable_A"]
    rows.append(("emergence-A: N_prop (proj-free, >=4 k)", str(em["n_prop_all"]),
                 "= 2 all k", c, True))
    # 涌现B
    c = em["c_decay_orders"] >= CDECAY_ORDERS and em["gauge_conversion"] < CONVERT_PASS
    rows.append(("emergence-B: C decay >=6 orders & convert<1e-3",
                 f"{em['c_decay_orders']:.1f} ord, conv={em['gauge_conversion']:.2e}",
                 ">=6 & <1e-3", c, True))
    # 规范反常
    c = ac["gauge_anomaly_leak_max"] < ANOMALY_PASS
    rows.append(("gauge anomaly (16piG * source residual)",
                 f"{ac['gauge_anomaly_leak_max']:.2e}", "< 1e-10", c, True))
    # 牛顿
    c = (abs(nw["h00_over_phi"] - 2.0) < NEWTON_TOL and nw["invr_fit_corr"] > INVR_CORR)
    rows.append(("Newton: h00/phi=2.00 & 1/r corr>0.99",
                 f"{nw['h00_over_phi']:.3f}, corr={nw['invr_fit_corr']:.3f}",
                 "2.00+-.02", c, True))
    # 偏折
    c = abs(nw["eddington_ratio"] - 2.0) < EDD_TOL and nw["deflection_toward_blob"]
    rows.append(("deflection: Eddington=2.00 (Born)",
                 f"{nw['eddington_ratio']:.3f} (toward={nw['deflection_toward_blob']})",
                 "2.00+-.02", c, True))
    # 守恒
    c = j1["live_row_conservation_bulk_max"] < CONS_PASS
    rows.append(("conservation: T-row residual (bulk)",
                 f"{j1['live_row_conservation_bulk_max']:.2e}", "< 1e-12", c, True))
    # J5
    c = abs(j5["gw_ratio"] - 1.0) < J5_TOL
    rows.append(("J5: |c_gw/c_matter - 1|",
                 f"{abs(j5['gw_ratio']-1.0):.3e} (cg2={j5['cg2']})", "< 1e-2", c, True))
    # 各向同性 (non-blocking)
    c = np.isfinite(iso["axis_c_spread"]) and iso["axis_c_spread"] < ISO_PASS
    rows.append(("isotropy: axis c spread (non-blocking)",
                 f"{iso['axis_c_spread']:.3f}" if np.isfinite(iso['axis_c_spread'])
                 else "nan", "< 6%", c, False))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "data", "results", "green_one_results.json"))
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="tiny fast sanity run")
    ap.add_argument("--cg2", type=float, default=0.25)
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING: backend = {B.NAME}; run RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("M3 -- 全绿一号: null-box + R10 exact Jbar source + h->coin feedback "
          "+ sponge, ONE construction\n")

    if args.smoke:
        out = run_all(quick=True, endurance_T=200, endurance_N=10, newton_L=32,
                      cg2=args.cg2)
    else:
        out = run_all(quick=not args.full, endurance_T=2000, endurance_N=16,
                      newton_L=56, cg2=args.cg2)

    vf = out["verify_fb"]
    print(f"[VERIFY] fed-back layers == r10 @ uniform coin: "
          f"state {vf['state_max_diff']:.1e} packet {vf['packet_max_diff']:.1e} "
          f"-> {'bit-identical' if vf['identical'] else 'MISMATCH'}\n")

    rows = _checktable(out)
    print("=" * 92)
    print("PRE-REGISTERED M3 CHECKPOINTS (fp64):")
    print(f"  {'criterion':52s} {'measured':22s} {'target':12s} PASS")
    blocking_pass = True
    for name, meas, tgt, ok, blocking in rows:
        tag = "PASS" if ok else "FAIL"
        if blocking and not ok:
            blocking_pass = False
        print(f"  {name:52s} {meas:22s} {tgt:12s} {tag}"
              + ("" if blocking else "  (non-blocking)"))
    print("-" * 92)
    nblock = sum(1 for *_, b in rows if b)
    npass = sum(1 for *_, ok, b in rows if b and ok)
    print(f"  M3 VERDICT: {npass}/{nblock} blocking checkpoints PASS -> "
          + ("ALL GREEN" if blocking_pass else "NOT all green (honest FAIL analysis below)"))

    # honest FAIL analysis: root causes + the one allowed calibration
    fails = [(name, meas) for name, meas, tgt, ok, blk in rows if blk and not ok]
    if fails:
        print("\n" + "-" * 92)
        print("HONEST FAIL ANALYSIS (root cause per missed pre-registered bar):")
        em = out["emergence"]
        j5 = out["j5"]
        for name, meas in fails:
            if name.startswith("emergence-B"):
                print(f"  * {name}: {meas}")
                print(f"      root cause: the LIVE wide-exact Jbar source injects a floor "
                      f"into the JUDGE's\n      stride-1 de-Donder monitor (Jbar is "
                      f"divergence-free on the stride-2 WIDE box,\n      not the monitor's "
                      f"stride-1 calculus) -- an M1/M2 stride-mismatch, NOT feedback.\n"
                      f"      conversion={em['gauge_conversion']:.2e} DOES pass < 1e-3; "
                      f"only C-decay orders miss.")
                if "calibration" in out:
                    cal = out["calibration"]["emergence"]
                    calok = (cal["c_decay_orders"] >= CDECAY_ORDERS
                             and cal["gauge_conversion"] < CONVERT_PASS
                             and all(n == 2 for n in cal["n_prop_all"]))
                    print(f"      [ONE calibration round] G_m -> "
                          f"{out['calibration']['G_m_calib']:.0e}: "
                          f"C-decay={cal['c_decay_orders']:.1f} ord, "
                          f"conv={cal['gauge_conversion']:.2e}, "
                          f"N_prop={cal['n_prop_all']} -> "
                          f"{'RECOVERS >=6 orders' if calok else 'still below bar'}")
            elif name.startswith("J5"):
                print(f"  * {name}: {meas}")
                print(f"      root cause: STRUCTURAL sector incompatibility.  The 3D wide "
                      f"null box is CFL-\n      capped at cg2 <= 1/3 "
                      f"(c_gw <= {j5['c_gw_at_cfl_cap']:.3f}, ratio "
                      f"{j5['gw_ratio_at_cfl_cap']:.3f}), so its graviton is\n      "
                      f"structurally sub-luminal vs matter (0.993).  NOT a calibration "
                      f"miss -> per the\n      plan this returns to M1/M2 (a light-cone "
                      f"graviton compatible with the wide-box\n      N_prop=2 count is a "
                      f"named open problem; the compact/half-angle box gives N_prop=5).")
            else:
                print(f"  * {name}: {meas} (see JSON)")

    print("\n" + "=" * 92)
    print("FALSIFICATION BATTERY (each MUST fail >= 1 criterion; replayed every run):")
    fb = out["falsification"]
    for k in ("tr_sign=0", "no_damping", "lagged_damping", "onsite_source",
              "wrong_sign_source"):
        r = fb[k]
        print(f"  {k:18s} breaks[{r['breaks']:28s}] -> "
              f"{'FAIL as required' if r['fails'] else 'UNEXPECTED PASS -- battery toothless!'}")
    print(f"  battery_has_teeth = {fb['battery_has_teeth']}")

    print("\nTIER: 定理(R10/R13 momentum balance ~1e-19) + 实证(N_prop=2, gauge "
          "suppression,\n  Newton factor 2, Eddington 2, endurance) + 代理(J5: "
          "c_matter=0.993 imported)\n  + 工程(sponge/batch).  NOT non-linear GR / "
          "QG / 'world is a CA'.")

    if blocking_pass and fb["battery_has_teeth"]:
        print("\n" + "=" * 92)
        print("FROZEN CANDIDATE (all pre-registered bars met, battery has teeth):")
        print(f"  construction : null-box(T3 central-1) + R10 exact Jbar source "
              f"+ h->coin feedback + sponge")
        print(f"  params       : cg2={out['cg2']}, kappa=0.5, G_m=0.02, th0=0.5, "
              f"dm=0.25, amp=0.02, sponge_w=3")
        print(f"  seeds        : walker seed=11 (judge) / 5 (endurance); "
              f"judge seeds fixed in emergence_judge")
        print(f"  reproduce    : RULESPACE_BACKEND=numpy python -m rulespace_gpu.green_one --full")

    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: (
            o.tolist() if isinstance(o, np.ndarray) else float(o)))
    print(f"\nwrote {os.path.abspath(args.json)}")
