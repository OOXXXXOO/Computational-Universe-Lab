"""R20 — in-vitro term-by-term alignment of the R18 prescriptions, and the
ATTRIBUTION MATRIX for the 6e-4 constraint floor (lane B, P2/R20).

SCOPE (per 小报告-R18 + main-loop discipline): single k, ON-SHELL initial
data, symbol-space dynamics that is EXACT for the linear assembly (R16's
in-vitro theorem), plus a 16^3 roll-vs-symbol bridge gate so every operator
here is certified identical to the roll code green_one uses.  NO full
assembly -- if all prescriptions align here and green_one still floors,
that verdict goes back to the main line.

THE RIG.  State = packed hbar amplitude in C^10 at one on-shell (w,k),
integer-storage (Yee-phased) frame, walk = exact on-shell phase e^{+iw}
(the R16 linearization).  One macro step, faithful to green_one_walk_cp1v2:

    walk:      h <- e^{iw} h  (+ co-rotating source s, source arms)
    measure:   C = A h_new + Bm h_cur          (4 rows)
    enforce:   h_new <- h_new - gamma E^dag C  (gradient step)

with the three axes of the attribution matrix realized as:

  ORDER / time placement  (suspicion 1 "walk re-injects each step")
    certified : time slots realized HISTORY-FREE with the per-OFFSET
                stencil ((0,0) forward, (0,nu) backward) -- the operator
                the r17 self-check gate certifies; kernel = Yee-phased
                TT (+) gauge exactly.  (v3's (W-I) realization.)
    v2        : uniform backward macro-step difference -(1/c)(h - hprev)
                with hprev = the previous DAMPED field -- green_one_cp1v2's
                actual code path.  Two known defects, both quantified here:
                (a) the (0,0) component gets a backward stencil where the
                certified operator wants forward (|dK| = (4/c) sin^2(w/2));
                (b) once damping perturbs the state off pure-phase
                evolution, hprev != e^{-iw} h and the slot de-tunes (lag).

  APERTURE  (suspicion 2 "measure != enforce")
    same         : E is THE SAME MATRIX OBJECT as A; both are probed out of
                   the same closure and ||K_meas - K_enf|| = 0 is asserted.
    naive        : E = single-flavor forward spatial stencils (no OFFSET
                   book-keeping), the R17 negative control.
    spatial_only : E = dict spatial rows, time slots dropped (R18 H4's
                   asymmetric enforcement).
    slave        : exact 0nu-row projection onto the v2 meter's surface
                   (green_one mode="slave"), measured with the certified
                   meter -- the "exact projection does not reduce measured
                   C" probe.

  SOURCE  (suspicion 3 "J-bar not de-Donder compatible")
    none / compat (s projected into the certified kernel, K s ~ 1e-16)
    / incompat (generic s, K s = O(|s|)); co-rotating so the floor is a
    clean steady state; amplitude scan checks floor ∝ ||K s||.

Every cell reports: floor of the violation content ||(1-P_ker) h||, floor
of the certified meter ||K_cert h||, floor of the cell's own meter, spectral
radius of the exact one-step map (probed), TT retention, gauge retention,
tt_match and the 3rd singular value of the gauge-quotiented final states
(the two HARD GATES from R18: sv3 < 0.05 AND tt_match > 0.95, plus
C -> < 1e-12 within 400 steps).

PRESCRIPTION 1 (gamma) is validated on the v2/J flavor whose sigma^2 the
R18 numbers were derived from: BZ scan must reproduce sigma^2 in
[3.01, 27.20]; then single gamma* = 0.0662 vs the 3-stage Chebyshev
[0.2159, 0.0662, 0.0391] are RUN as dynamics and the measured per-3-step
contraction is compared with the no-lag theory (0.513 vs 0.247) and with
the exact lag-including spectral radius computed here.

Run:  .venv/bin/python r20_invitro_alignment.py   (minutes; r20_results.json)
"""
import json
import math
import os

import numpy as np

import r15_walk_dedonder as r15
import r17_placement_operators as r17

DIR = os.path.dirname(os.path.abspath(__file__))
C = r15.C_CONE                                   # cos(pi/3) = 0.5
ETA = r15.ETA
SYM = r15.SYM                                    # 10 packed (m<=n) indices
PK = {}
for i, (m, n) in enumerate(SYM):
    PK[(m, n)] = i
    PK[(n, m)] = i
OFFSET = [r17.offset(a, b) for (a, b) in SYM]    # Yee half-step flags (4,)
NU0 = [PK[(0, nu)] for nu in range(4)]

GAMMA_STAR = 0.0662
CHEB = [0.21586100457072394, 0.06619830797164757, 0.03909358877115305]


# ==========================================================================
#  operators (integer-storage frame, raw roll symbols -- what the code does)
# ==========================================================================
def stencil(kd, bw):
    """symbol of the one-step difference on e^{i k x}:
    forward (e^{ik}-1), backward (1-e^{-ik})."""
    return (1.0 - np.exp(-1j * kd)) if bw else (np.exp(1j * kd) - 1.0)


def K_spatial(k3, naive=False):
    """(4,10) spatial part of C_nu = sum_mu eta^{mumu} D_mu hbar_munu.
    dict flavor: fwd/bwd per OFFSET (R17); naive: forward everywhere."""
    K = np.zeros((4, 10), complex)
    for comp, (a, b) in enumerate(SYM):
        pairs = ((a, b),) if a == b else ((a, b), (b, a))
        for mu, nu in pairs:
            if mu == 0:
                continue
            bw = bool(OFFSET[comp][mu]) and not naive
            K[nu, comp] += ETA[mu, mu] * stencil(k3[mu - 1], bw)
    return K


def time_mats(omega, order):
    """time slots of the meter as C = (Ksp + At) h_new + Bm h_cur.
    certified: history-free per-OFFSET stencil ((0,0) fwd, (0,nu) bwd) --
               exactly the operator the r17 self-check gate certifies;
    v2       : uniform backward macro-step difference with the STORED
               previous damped field (green_one_walk_cp1v2._constraint_C)."""
    At = np.zeros((4, 10), complex)
    Bm = np.zeros((4, 10), complex)
    for nu in range(4):
        comp = PK[(0, nu)]
        if order == "certified":
            bw = bool(OFFSET[comp][0])
            At[nu, comp] = ETA[0, 0] * stencil(omega, bw) / C
        elif order == "v2":
            At[nu, comp] = ETA[0, 0] * (1.0 / C)
            Bm[nu, comp] = -ETA[0, 0] * (1.0 / C)
        else:
            raise ValueError(order)
    return At, Bm


def frame(k3):
    """on-shell frame data at k: certified kernel = Yee-phased TT (+) gauge."""
    w = r15.shell_omega(k3)
    k4 = np.array([w, k3[0], k3[1], k3[2]])
    kap = r15.kappa_placed(k3)
    colfac = np.array([np.exp(0.5j * float(k4 @ OFFSET[c10]))
                       for c10 in range(10)])
    TTb = colfac[:, None] * r15.tt_basis(kap)          # (10,2) Yee frame
    Gb = colfac[:, None] * r15.gauge_block(kap)        # (10,4) Yee frame
    KerB = np.concatenate([TTb, Gb], axis=1)
    Qker, _ = np.linalg.qr(KerB)
    Qg, _ = np.linalg.qr(Gb)
    ttq = TTb - Qg @ (Qg.conj().T @ TTb)
    Qtt, _ = np.linalg.qr(ttq)                         # TT rep in gauge-complement
    Kcert = K_spatial(k3) + time_mats(w, "certified")[0]
    return {"k3": np.asarray(k3, float), "w": w, "k4": k4, "kap": kap,
            "colfac": colfac, "TTb": TTb, "Gb": Gb, "KerB": KerB,
            "Qker": Qker, "Qg": Qg, "Qtt": Qtt, "Kcert": Kcert}


# ==========================================================================
#  gates
# ==========================================================================
def gate_G0_kernel(F):
    """certified operator annihilates the Yee-phased TT (+) gauge, and has
    rank 4 (so the damped complement is exactly the 4 violation directions);
    the v2 meter does NOT annihilate it -- the leak is quantified."""
    Kc = F["Kcert"]
    res_ker = float(np.abs(Kc @ F["KerB"]).max())
    res_tt = float(np.abs(Kc @ F["TTb"]).max())
    sv = np.linalg.svd(Kc, compute_uv=False)
    # v2 effective on-trajectory meter: A h + Bm h_prev with h_prev = e^{-iw} h
    At, Bm = time_mats(F["w"], "v2")
    Kv2_eff = K_spatial(F["k3"]) + At + np.exp(-1j * F["w"]) * Bm
    leak_g = float(np.abs(Kv2_eff @ F["Gb"]).max())
    leak_tt = float(np.abs(Kv2_eff @ F["TTb"]).max())
    dk00 = float(abs((Kv2_eff - Kc)[0, PK[(0, 0)]]))
    return {"res_kernel": res_ker, "res_TT": res_tt,
            "rank": int((sv > 1e-10 * sv[0]).sum()),
            "v2_eff_gauge_leak": leak_g, "v2_eff_TT_leak": leak_tt,
            "v2_dK00_pred_4c_sin2": float(4.0 / C * math.sin(F["w"] / 2) ** 2),
            "v2_dK00_meas": dk00,
            "PASS": bool(res_ker < 1e-12 and res_tt < 1e-12
                         and leak_g > 1e-3 and leak_tt < 1e-12)}


def gate_G1_rolls(k3, N=16, seed=5):
    """bridge gate: the roll code (green_one's _dsp_dict logic, complex) on a
    16^3 plane wave == the symbol matrices used by this rig, to 1e-12."""
    rng = np.random.default_rng(seed)
    amp = rng.standard_normal(10) + 1j * rng.standard_normal(10)
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    ph = np.exp(1j * (k3[0] * X + k3[1] * Y + k3[2] * Z))

    def dsp(f, mu, comp, use_dict=True):
        ax = mu - 4
        bw = bool(OFFSET[comp][mu]) if use_dict else False
        if bw:
            return f - np.roll(f, 1, ax)
        return np.roll(f, -1, ax) - f

    err = 0.0
    for flavor, naive in (("dict", False), ("naive", True)):
        Ks = K_spatial(k3, naive=naive)
        for nu in range(4):
            acc = np.zeros((N, N, N), complex)
            for j in (1, 2, 3):
                comp = PK[(j, nu)]
                acc = acc + ETA[j, j] * dsp(amp[comp] * ph, j, comp,
                                            use_dict=not naive)
            want = (Ks @ amp)[nu] * ph
            err = max(err, float(np.abs(acc - want).max()))
    return {"max_err": err, "PASS": bool(err < 1e-12)}


# ==========================================================================
#  one cell of the attribution matrix
# ==========================================================================
def build_ops(F, order, enforce):
    A = K_spatial(F["k3"]) + time_mats(F["w"], order)[0]
    Bm = time_mats(F["w"], order)[1]
    if enforce == "same":
        E = A                                    # SAME object: one code path
    elif enforce == "naive":
        E = K_spatial(F["k3"], naive=True) + time_mats(F["w"], order)[0]
    elif enforce == "spatial_only":
        E = K_spatial(F["k3"])                   # time slots dropped (R18 H4)
    elif enforce == "slave":
        E = None                                 # handled in the step
    else:
        raise ValueError(enforce)
    return A, Bm, E


def probe_measure_enforce(A, Bm, E, gamma):
    """prescription 2: extract K_meas and K_enf from the actual closures by
    unit-vector probing and diff them (the 'one-line diff gate')."""
    def meas(h_new, h_cur):
        return A @ h_new + Bm @ h_cur

    def enf(h, Cvec):
        return h - gamma * (E.conj().T @ Cvec)

    K_meas = np.stack([meas(np.eye(10)[j] + 0j, np.zeros(10)) for j in
                       range(10)], axis=1)
    KH_enf = np.stack([-(enf(np.zeros(10), np.eye(4)[nu] + 0j)) / gamma
                       for nu in range(4)], axis=1)   # columns = E^dag e_nu
    K_enf = KH_enf.conj().T
    return float(np.linalg.norm(K_meas - K_enf, 2)), (E is A)


def step_factory(F, order, enforce, gamma, gammas=None):
    """returns step(h, t, s) -> h_next (linear + source), green_one-faithful:
    walk -> measure -> enforce, hprev = the previous damped field."""
    A, Bm, E = build_ops(F, order, enforce)
    W = np.exp(1j * F["w"])
    Ksp = K_spatial(F["k3"])

    def gam(t):
        return gammas[t % len(gammas)] if gammas else gamma

    if enforce == "slave":
        def step(h, t, s):
            hw = W * h + (W ** (t + 1)) * s
            hn = hw.copy()
            for nu in range(4):                  # v2 sequential slave
                S = (Ksp @ hn)[nu]
                c0 = PK[(0, nu)]
                hn[c0] = h[c0] + C * S           # C_nu(v2 meter) = 0 exactly
            return hn, A @ hw + Bm @ h
        return step, A, Bm, E

    def step(h, t, s):
        hw = W * h + (W ** (t + 1)) * s
        Cm = A @ hw + Bm @ h
        hn = hw - gam(t) * (E.conj().T @ Cm)
        return hn, Cm
    return step, A, Bm, E


def make_source(F, kind, amp, rng):
    if kind == "none":
        return np.zeros(10, complex), 0.0
    raw = rng.standard_normal(10) + 1j * rng.standard_normal(10)
    if kind == "compat":
        s = F["Qker"] @ (F["Qker"].conj().T @ raw)
    elif kind == "incompat":
        s = raw
    else:
        raise ValueError(kind)
    s = amp * s / np.linalg.norm(s)
    return s, float(np.linalg.norm(F["Kcert"] @ s))


def rho_violation(M, meter):
    """spectral radius restricted to CONSTRAINT-CARRYING modes: max |lambda|
    over eigenvectors with nonzero dynamic-meter leak (kernel modes are
    marginal by construction and excluded by their zero leak)."""
    ev, evec = np.linalg.eig(M)
    rv, n_marg, leak_marg = 0.0, 0, 0.0
    for i in range(len(ev)):
        v = evec[:, i] / np.linalg.norm(evec[:, i])
        lk = float(np.linalg.norm(meter @ v))
        if lk > 1e-8:
            rv = max(rv, float(abs(ev[i])))
        if abs(ev[i]) > 1.0 - 1e-9:
            n_marg += 1
            leak_marg = max(leak_marg, lk)
    return rv, n_marg, leak_marg


def tail_rate(seq):
    """geometric per-step rate over the recorded tail (1.0 = stuck)."""
    if len(seq) < 10 or seq[0] < 1e-300:
        return float("nan")
    return float((seq[-1] / seq[0]) ** (1.0 / (len(seq) - 1)))


def run_cell(F, order, enforce, source, gamma=GAMMA_STAR, gammas=None,
             T=400, trials=12, src_amp=1e-3, seed=0, ic="mixed"):
    step, A, Bm, E = step_factory(F, order, enforce, gamma, gammas)
    Qker, Qg, Qtt, Kc = F["Qker"], F["Qg"], F["Qtt"], F["Kcert"]

    # exact one-step linear map (probed through the actual step closure)
    M = np.stack([step(np.eye(10)[j] + 0j, 0, np.zeros(10))[0]
                  for j in range(10)], axis=1)
    W = np.exp(1j * F["w"])
    meter = A * W + Bm                      # dynamic meter on pre-walk state
    rho_v, n_marg, leak = rho_violation(M, meter)
    rho = float(np.abs(np.linalg.eigvals(M)).max())
    # certified-C leak of the MARGINAL (never-damped) subspace
    ev, evec = np.linalg.eig(M)
    cert_leak = 0.0
    for i in np.where(np.abs(ev) > 1.0 - 1e-9)[0]:
        v = evec[:, i] / np.linalg.norm(evec[:, i])
        cert_leak = max(cert_leak, float(np.linalg.norm(Kc @ v)))

    fl_ref, fl_cert, fl_own, tt_ret, g_ret, tt_match = [], [], [], [], [], []
    rt_cert, rt_own = [], []
    finals_q = []
    for tr in range(trials):
        rng = np.random.default_rng(1000 * seed + tr)
        if ic == "mixed":
            h0 = (F["KerB"] @ (rng.standard_normal(6)
                               + 1j * rng.standard_normal(6))
                  + 0.5 * (rng.standard_normal(10)
                           + 1j * rng.standard_normal(10)))
        else:                                    # violation-only junk
            r = rng.standard_normal(10) + 1j * rng.standard_normal(10)
            h0 = r - Qker @ (Qker.conj().T @ r)
        h0 = h0 / np.linalg.norm(h0)
        s, ks = make_source(F, source, src_amp, rng)
        h = h0.copy()
        tail_ref, tail_cert, tail_own = [], [], []
        blew = False
        for t in range(T):
            h, Cm = step(h, t, s)
            if not np.isfinite(h).all() or np.linalg.norm(h) > 1e12:
                blew = True
                break
            if t >= T - 50:
                tail_ref.append(np.linalg.norm(h - Qker @ (Qker.conj().T @ h)))
                tail_cert.append(np.linalg.norm(Kc @ h))
                tail_own.append(np.linalg.norm(Cm))
        if blew:
            fl_ref.append(np.inf); fl_cert.append(np.inf); fl_own.append(np.inf)
            continue
        fl_ref.append(float(np.median(tail_ref)))
        fl_cert.append(float(np.median(tail_cert)))
        fl_own.append(float(np.median(tail_own)))
        rt_cert.append(tail_rate(tail_cert))
        rt_own.append(tail_rate(tail_own))
        tt0 = np.linalg.norm(Qtt.conj().T @ h0)
        ttf = np.linalg.norm(Qtt.conj().T @ h)
        tt_ret.append(float(ttf / (tt0 + 1e-300)))
        g_ret.append(float(np.linalg.norm(Qg.conj().T @ h)
                           / (np.linalg.norm(Qg.conj().T @ h0) + 1e-300)))
        hq = h - Qg @ (Qg.conj().T @ h)
        finals_q.append(hq)
        tt_match.append(float(np.linalg.norm(Qtt.conj().T @ hq)
                              / (np.linalg.norm(hq) + 1e-300)))
    out = {"order": order, "enforce": enforce, "source": source,
           "rho_step": rho, "rho_violation": rho_v, "n_marginal": n_marg,
           "marginal_cert_leak": cert_leak,
           "K_source_viol": ks if source != "none" else 0.0}
    if not np.isfinite(fl_ref).all() or len(finals_q) == 0:
        out.update({"floor_ref": float("inf"), "floor_cert": float("inf"),
                    "floor_own": float("inf"), "verdict": "BLOWUP",
                    "rate_cert": float("nan"), "rate_own": float("nan"),
                    "tt_retention": float("nan"), "gauge_retention": float("nan"),
                    "tt_match": float("nan"), "sv3_over_sv1": float("nan")})
        return out
    Mq = np.stack(finals_q)
    sv = np.linalg.svd(Mq, compute_uv=False)
    sv3 = float(sv[2] / (sv[0] + 1e-300)) if len(sv) > 2 else 0.0
    fr = float(np.median(fl_ref))
    rc = float(np.nanmedian(rt_cert))
    verdict = ("machine-floor" if fr < 1e-12 else
               "FLOOR" if (fr > 1e-8 and rc > 0.999) else
               "slow-decay" if fr > 1e-8 else "residual")
    out.update({"floor_ref": fr, "floor_cert": float(np.median(fl_cert)),
                "floor_own": float(np.median(fl_own)),
                "rate_cert": rc, "rate_own": float(np.nanmedian(rt_own)),
                "tt_retention": float(np.mean(tt_ret)),
                "gauge_retention": float(np.mean(g_ret)),
                "tt_match": float(np.mean(tt_match)),
                "sv3_over_sv1": sv3, "verdict": verdict})
    return out


# ==========================================================================
#  supplement: damp-BEFORE-walk (literal order flip, doubled state)
# ==========================================================================
def run_before_walk(F, source, gamma=GAMMA_STAR, T=400, trials=12,
                    src_amp=1e-3, seed=77):
    """measure C(h_t, hprev) -> damp -> THEN walk (the deliberate order-flip
    control of prescription 3), v2 meter, matched enforce."""
    A, Bm, E = build_ops(F, "v2", "same")
    W = np.exp(1j * F["w"])
    Qker, Kc = F["Qker"], F["Kcert"]
    fl_ref, fl_cert = [], []
    for tr in range(trials):
        rng = np.random.default_rng(1000 * seed + tr)
        h0 = (F["KerB"] @ (rng.standard_normal(6) + 1j * rng.standard_normal(6))
              + 0.5 * (rng.standard_normal(10) + 1j * rng.standard_normal(10)))
        h0 = h0 / np.linalg.norm(h0)
        s, _ = make_source(F, source, src_amp, rng)
        h, hprev = h0.copy(), np.conj(W) * h0     # on-shell history
        tail_ref, tail_cert = [], []
        for t in range(T):
            Cm = A @ h + Bm @ hprev
            hd = h - gamma * (E.conj().T @ Cm)
            hprev = hd
            h = W * hd + (W ** (t + 1)) * s
            if t >= T - 50:
                tail_ref.append(np.linalg.norm(h - Qker @ (Qker.conj().T @ h)))
                tail_cert.append(np.linalg.norm(Kc @ h))
        fl_ref.append(float(np.median(tail_ref)))
        fl_cert.append(float(np.median(tail_cert)))
    return {"source": source, "floor_ref": float(np.median(fl_ref)),
            "floor_cert": float(np.median(fl_cert))}


# ==========================================================================
#  supplement: v2 fold-back model (damp Re-slot only, Im-slot walks free)
# ==========================================================================
def run_foldback(F, order="certified", gamma=GAMMA_STAR, T=800, trials=8,
                 seed=88):
    """v2 folded hbar back into Re(chi) only; the walk then remixes the
    un-damped quadrature.  Model: two 10-vectors (a,b), walk = SO(2)
    rotation by w between them, matched damping applied to a ONLY (meter
    per `order`; for v2 the meter's hprev is the previous damped a).
    Question: floor or just a slower rate?"""
    A, Bm, E = build_ops(F, order, "same")
    w = F["w"]
    cw, sw = math.cos(w), math.sin(w)
    Qker, Kc = F["Qker"], F["Kcert"]
    fl_ref, fl_own, rates = [], [], []
    for tr in range(trials):
        rng = np.random.default_rng(1000 * seed + tr)
        r = rng.standard_normal(10) + 1j * rng.standard_normal(10)
        a = r - Qker @ (Qker.conj().T @ r)       # violation-only junk
        a = a / np.linalg.norm(a)
        b = np.zeros(10, complex)
        aprev = a.copy()
        hist, hown = [], []
        for t in range(T):
            an, b = cw * a - sw * b, sw * a + cw * b
            Cm = A @ an + Bm @ aprev
            an = an - gamma * (E.conj().T @ Cm)
            aprev, a = an, an
            hist.append(np.linalg.norm(a - Qker @ (Qker.conj().T @ a))
                        + np.linalg.norm(b - Qker @ (Qker.conj().T @ b)))
            hown.append(np.linalg.norm(Cm))
        fl_ref.append(float(np.median(hist[-50:])))
        fl_own.append(float(np.median(hown[-50:])))
        h10, h200 = hist[10], hist[200]
        rates.append((h200 / (h10 + 1e-300)) ** (1.0 / 190.0))
    return {"order": order, "floor_ref": float(np.median(fl_ref)),
            "floor_own": float(np.median(fl_own)),
            "rate_per_step": float(np.mean(rates))}


# ==========================================================================
#  supplement: uniform time stencil (v3's (I-W) realization) vs certificate
# ==========================================================================
def uniform_time_check(F):
    """the certificate demands PER-OFFSET time stencils (hbar_00 forward,
    hbar_0i backward).  ANY uniform single-flavor time slot -- including
    v3's uniform (I-W) -- leaks gauge out of the kernel.  Quantified here."""
    res = {}
    for tag, bwmap in (("uniform_forward", (False,) * 4),
                       ("uniform_backward", (True,) * 4),
                       ("per_offset_certified", (False, True, True, True))):
        K = K_spatial(F["k3"]).copy()
        for nu in range(4):
            comp = PK[(0, nu)]
            K[nu, comp] += ETA[0, 0] * stencil(F["w"], bwmap[nu]) / C
        res[tag] = {"leak_kernel": float(np.abs(K @ F["KerB"]).max()),
                    "leak_TT": float(np.abs(K @ F["TTb"]).max())}
    return res


# ==========================================================================
#  prescription 1: gamma window -- BZ scan + single vs Chebyshev dynamics
# ==========================================================================
def bz_scan_sigma2():
    """sigma^2 of the v2/J damping operator (dict spatial + const 1/c time
    slot) over the same BZ grid R18 used; must reproduce [3.01, 27.20]."""
    lo, hi = np.inf, 0.0
    k_lo = k_hi = None
    for a in range(8):
        for b in range(8):
            for d in range(8):
                k3 = 2 * np.pi * np.array([a, b, d]) / 16.0
                if np.linalg.norm(k3) < 1e-9:
                    continue
                A = K_spatial(k3) + time_mats(1.0, "v2")[0]  # At is w-free
                s2 = np.linalg.svd(A, compute_uv=False) ** 2
                s2 = s2[s2 > 1e-12]
                if s2.min() < lo:
                    lo, k_lo = float(s2.min()), k3
                if s2.max() > hi:
                    hi, k_hi = float(s2.max()), k3
    return lo, hi, k_lo, k_hi


def contraction_run(F, gammas, order="v2", T=150, trials=8, seed=9):
    """measured per-3-step contraction of the own meter from junk IC, plus
    the EXACT violation-sector spectral radius of the 3-step product (the
    lag included), vs the no-lag theory max |prod(1 - gamma sigma^2)|."""
    g3 = (gammas * 3)[:3]
    step, A, Bm, E = step_factory(F, order, "same", gammas[0],
                                  gammas if len(gammas) > 1 else None)
    Qker = F["Qker"]
    W = np.exp(1j * F["w"])
    meter = A * W + Bm
    worst = 0.0
    for tr in range(trials):
        rng = np.random.default_rng(1000 * seed + tr)
        r = rng.standard_normal(10) + 1j * rng.standard_normal(10)
        h = r - Qker @ (Qker.conj().T @ r)
        h = h / np.linalg.norm(h)
        ns = []
        for t in range(T):
            h, Cm = step(h, t, np.zeros(10))
            ns.append(np.linalg.norm(Cm))
        ns = np.array(ns)
        # per-cycle factors after transient, before floor
        for m in range(3, min(40, T // 3 - 1)):
            if ns[3 * m] > 1e-13 and ns[3 * (m - 1)] > 1e-13:
                worst = max(worst, float(ns[3 * m] / ns[3 * (m - 1)]))
    # exact 3-step product, violation sector only (leak-based)
    Ms = []
    for g in g3:
        s2, A2, B2, E2 = step_factory(F, order, "same", g, None)
        Ms.append(np.stack([s2(np.eye(10)[j] + 0j, 0, np.zeros(10))[0]
                            for j in range(10)], axis=1))
    M3 = Ms[2] @ Ms[1] @ Ms[0]
    rho3, _, _ = rho_violation(M3, meter)
    # no-lag theory on this k's sigma^2 of the damping operator A
    s2v = np.linalg.svd(A, compute_uv=False) ** 2
    s2v = s2v[s2v > 1e-12]
    th = float(max(abs(np.prod([1 - g * s for g in g3])) for s in s2v))
    return {"measured_worst_cycle": worst, "exact_rho3": rho3,
            "theory_no_lag": th, "sigma2": [float(v) for v in sorted(s2v)]}


def bz_rho_scan(gamma, order, enforce, stride=1):
    """max violation-sector spectral radius of the one-macro-step map over
    the resolvable BZ (16^3 grid), + how much of the BZ is near-marginal
    (rho > 0.999: content there cannot decay within a few hundred steps)."""
    rmax, k_arg = 0.0, None
    n_tot = n_unstable = n_marg999 = 0
    for a in range(0, 8, stride):
        for b in range(0, 8, stride):
            for d in range(0, 8, stride):
                k3 = 2 * np.pi * np.array([a, b, d]) / 16.0
                if np.linalg.norm(k3) < 1e-9:
                    continue
                F = frame(k3)
                step, A, Bm, E = step_factory(F, order, enforce, gamma, None)
                M = np.stack([step(np.eye(10)[j] + 0j, 0, np.zeros(10))[0]
                              for j in range(10)], axis=1)
                meter = A * np.exp(1j * F["w"]) + Bm
                rv, _, _ = rho_violation(M, meter)
                n_tot += 1
                if rv > 1.0 + 1e-9:
                    n_unstable += 1
                if rv > 0.999:
                    n_marg999 += 1
                if rv > rmax:
                    rmax, k_arg = rv, [a, b, d]
    return {"gamma": gamma, "order": order, "enforce": enforce,
            "rho_max": rmax, "k_argmax_16ths": k_arg, "n_k": n_tot,
            "frac_unstable": n_unstable / n_tot,
            "frac_rho_gt_0.999": n_marg999 / n_tot}


def bz_scan_sigma2_certified():
    """sigma^2 range of the CERTIFIED (history-free on-shell) operator over
    the BZ -> its true gamma window and a matched Chebyshev triple."""
    lo, hi = np.inf, 0.0
    for a in range(8):
        for b in range(8):
            for d in range(8):
                k3 = 2 * np.pi * np.array([a, b, d]) / 16.0
                if np.linalg.norm(k3) < 1e-9:
                    continue
                w = r15.shell_omega(k3)
                A = K_spatial(k3) + time_mats(w, "certified")[0]
                s2 = np.linalg.svd(A, compute_uv=False) ** 2
                s2 = s2[s2 > 1e-12]
                lo, hi = min(lo, float(s2.min())), max(hi, float(s2.max()))
    cheb = [2.0 / (lo + hi - (hi - lo) * math.cos((2 * j + 1) * math.pi / 6))
            for j in range(3)]
    poly = max(abs(np.prod([1 - g * s for g in cheb]))
               for s in np.linspace(lo, hi, 4000))
    return {"sigma2": [lo, hi], "gamma_max": 2.0 / hi,
            "gamma_opt": 2.0 / (lo + hi), "chebyshev": cheb,
            "cheb_worst_factor": float(poly),
            "steps_to_1e-12_at_gamma_opt": float(
                math.log(1e-12) / math.log(abs(1 - (2.0 / (lo + hi)) * lo)))}


# ==========================================================================
#  driver
# ==========================================================================
def main():
    print("R20 in-vitro alignment & floor attribution (single k, on-shell)")
    print("=" * 72)
    k_main = 2 * np.pi * np.array([2.0, 1.0, -1.0]) / 16.0
    k_axis = 2 * np.pi * np.array([2.0, 0.0, 0.0]) / 16.0
    F_main, F_axis = frame(k_main), frame(k_axis)
    out = {"c": C, "gamma_star": GAMMA_STAR, "chebyshev": CHEB,
           "k_main": k_main.tolist(), "k_axis": k_axis.tolist(),
           "w_main": F_main["w"], "w_axis": F_axis["w"]}

    # ---- gates -----------------------------------------------------------
    g0 = gate_G0_kernel(F_main)
    g0x = gate_G0_kernel(F_axis)
    g1 = gate_G1_rolls(k_main)
    print(f"[G0 kernel certification] k_main: ||K_cert@(TT(+)gauge)|| = "
          f"{g0['res_kernel']:.2e}  rank={g0['rank']}  -> "
          f"{'PASS' if g0['PASS'] else 'FAIL'}")
    print(f"    v2 effective meter: gauge leak {g0['v2_eff_gauge_leak']:.3f} "
          f"TT leak {g0['v2_eff_TT_leak']:.1e}  "
          f"dK(0,0) meas {g0['v2_dK00_meas']:.3f} = (4/c)sin^2(w/2) pred "
          f"{g0['v2_dK00_pred_4c_sin2']:.3f}")
    print(f"[G1 roll-vs-symbol bridge] max err = {g1['max_err']:.2e}  -> "
          f"{'PASS' if g1['PASS'] else 'FAIL'}")
    A, Bm, E = build_ops(F_main, "certified", "same")
    d_same, same_obj = probe_measure_enforce(A, Bm, E, GAMMA_STAR)
    _, _, En = build_ops(F_main, "certified", "naive")
    d_naive, _ = probe_measure_enforce(A, Bm, En, GAMMA_STAR)
    _, _, Es = build_ops(F_main, "certified", "spatial_only")
    d_sp, _ = probe_measure_enforce(A, Bm, Es, GAMMA_STAR)
    print(f"[G2 measure==enforce diff gate] matched ||K_m-K_e|| = {d_same:.1e} "
          f"(same object: {same_obj});  naive mismatch = {d_naive:.3f};  "
          f"spatial-only mismatch = {d_sp:.3f}")
    assert d_same == 0.0 and same_obj
    out["gates"] = {"G0_main": g0, "G0_axis": g0x, "G1": g1,
                    "G2": {"matched": d_same, "naive": d_naive,
                           "spatial_only": d_sp}}

    # ---- prescription 1: gamma window ------------------------------------
    lo, hi, k_lo, k_hi = bz_scan_sigma2()
    print(f"\n[P1 gamma] BZ sigma^2(v2/J operator) = [{lo:.4f}, {hi:.4f}]   "
          f"(R18: [3.0124, 27.1999])")
    p1 = {"sigma2_bz": [lo, hi], "r18_reference": [3.0124, 27.1999],
          "runs": {}}
    for name, kv in (("k_sigma_min", k_lo), ("k_sigma_max", k_hi),
                     ("k_main", k_main)):
        Fk = frame(kv)
        row = {"k": np.asarray(kv).tolist()}
        for order in ("v2", "certified"):
            single = contraction_run(Fk, [GAMMA_STAR], order=order)
            cheb = contraction_run(Fk, CHEB, order=order)
            row[order] = {"single": single, "cheb": cheb}
            print(f"  {name:11s} [{order:9s}] single: meas "
                  f"{single['measured_worst_cycle']:.3f} exact "
                  f"{single['exact_rho3']:.3f} theory "
                  f"{single['theory_no_lag']:.3f}  |  cheb: meas "
                  f"{cheb['measured_worst_cycle']:.3f} exact "
                  f"{cheb['exact_rho3']:.3f} theory "
                  f"{cheb['theory_no_lag']:.3f}")
        p1["runs"][name] = row
    print("  R18 global worst (no lag): single 0.513  cheb 0.247   "
          "(v2 exact != theory -> the hprev LAG breaks the R16/R18 rate "
          "prediction; certified exact == theory)")
    out["prescription1"] = p1

    # ---- gamma stability over the BZ: the lag shrinks the window ---------
    print("\n[P1b BZ-wide stability, violation sector]  (rho_max over 511 k)")
    rho_rows = []
    for g in (0.03, 0.04, 0.05, GAMMA_STAR, 0.0735, 0.10, 0.15):
        r = bz_rho_scan(g, "v2", "same")
        rho_rows.append(r)
        print(f"  v2-lag matched      gamma={g:6.4f}: rho_max = "
              f"{r['rho_max']:.4f} @k={r['k_argmax_16ths']}  "
              f"unstable {100*r['frac_unstable']:.1f}%  rho>0.999 "
              f"{100*r['frac_rho_gt_0.999']:.1f}% of BZ")
    for g in (0.05, GAMMA_STAR):
        for enf in ("same", "naive"):
            r = bz_rho_scan(g, "certified", enf)
            rho_rows.append(r)
            print(f"  certified {enf:9s} gamma={g:6.4f}: rho_max = "
                  f"{r['rho_max']:.4f} @k={r['k_argmax_16ths']}  "
                  f"unstable {100*r['frac_unstable']:.1f}%  rho>0.999 "
                  f"{100*r['frac_rho_gt_0.999']:.1f}% of BZ")
    out["bz_stability"] = rho_rows

    cert_bz = bz_scan_sigma2_certified()
    print(f"\n[P1c certified-operator window] BZ sigma^2 = "
          f"[{cert_bz['sigma2'][0]:.4f}, {cert_bz['sigma2'][1]:.4f}]  ->  "
          f"gamma_max = {cert_bz['gamma_max']:.4f}, gamma_opt = "
          f"{cert_bz['gamma_opt']:.4f}  (lane B v3 empirical ceiling ~0.05)")
    print(f"    matched Chebyshev = [{cert_bz['chebyshev'][0]:.4f}, "
          f"{cert_bz['chebyshev'][1]:.4f}, {cert_bz['chebyshev'][2]:.4f}]  "
          f"worst cycle {cert_bz['cheb_worst_factor']:.3f};  slowest mode at "
          f"gamma_opt needs ~{cert_bz['steps_to_1e-12_at_gamma_opt']:.0f} "
          f"steps to 1e-12 (the 400-step gate is per-k, not global)")
    out["certified_window"] = cert_bz

    # ---- the attribution matrix ------------------------------------------
    print("\n[ATTRIBUTION MATRIX]  (k_main; floors on ||(1-P_ker)h||, "
          "state normalized to 1; T=400, gamma=0.0662)")
    hdr = (f"  {'order':10s} {'aperture':13s} {'source':9s} {'floor_ref':>10s} "
           f"{'floor_cert':>10s} {'floor_own':>10s} {'rt_own':>7s} "
           f"{'rho_v':>7s} {'ttret':>6s} {'ttmatch':>8s} {'sv3':>7s}  verdict")
    print(hdr)
    matrix = []
    for order in ("certified", "v2"):
        for enforce in ("same", "naive"):
            for source in ("compat", "incompat"):
                cell = run_cell(F_main, order, enforce, source, seed=3)
                cell["k"] = "k_main"
                matrix.append(cell)
    # source=none baselines (hard-gate cells)
    for order in ("certified", "v2"):
        for enforce in ("same", "naive"):
            cell = run_cell(F_main, order, enforce, "none", seed=3)
            cell["k"] = "k_main"
            matrix.append(cell)
    # axis-k replication of the 8 matrix cells
    for order in ("certified", "v2"):
        for enforce in ("same", "naive"):
            for source in ("compat", "incompat"):
                cell = run_cell(F_axis, order, enforce, source, seed=4)
                cell["k"] = "k_axis"
                matrix.append(cell)
    for cell in matrix:
        if cell["k"] != "k_main":
            continue
        print(f"  {cell['order']:10s} {cell['enforce']:13s} "
              f"{cell['source']:9s} {cell['floor_ref']:>10.2e} "
              f"{cell['floor_cert']:>10.2e} {cell['floor_own']:>10.2e} "
              f"{cell['rate_own']:>7.4f} {cell['rho_violation']:>7.4f} "
              f"{cell['tt_retention']:>6.3f} {cell['tt_match']:>8.4f} "
              f"{cell['sv3_over_sv1']:>7.1e}  {cell['verdict']}")
    out["matrix"] = matrix

    # ---- source scaling: floor ∝ ||K s|| ---------------------------------
    sc = []
    for amp in (1e-3, 1e-4, 1e-5):
        cell = run_cell(F_main, "certified", "same", "incompat",
                        src_amp=amp, seed=5)
        sc.append({"src_amp": amp, "K_source_viol": cell["K_source_viol"],
                   "floor_ref": cell["floor_ref"],
                   "floor_cert": cell["floor_cert"]})
    r10 = sc[0]["floor_ref"] / (sc[1]["floor_ref"] + 1e-300)
    print(f"\n[SOURCE SCALING] incompat floors at |s|=1e-3/1e-4/1e-5 : "
          f"{sc[0]['floor_ref']:.2e} / {sc[1]['floor_ref']:.2e} / "
          f"{sc[2]['floor_ref']:.2e}   (ratio per decade {r10:.2f} -> "
          f"floor ∝ ||K s|| {'CONFIRMED' if 8 < r10 < 12 else 'NOT LINEAR'})")
    out["source_scaling"] = sc

    # ---- supplements ------------------------------------------------------
    sup = {}
    sup["before_walk_none"] = run_before_walk(F_main, "none")
    sup["before_walk_incompat"] = run_before_walk(F_main, "incompat")
    print(f"\n[SUP damp-BEFORE-walk, v2 meter matched] no source floor_ref = "
          f"{sup['before_walk_none']['floor_ref']:.2e} ; incompat source = "
          f"{sup['before_walk_incompat']['floor_ref']:.2e}")
    sup["spatial_only"] = run_cell(F_main, "certified", "spatial_only",
                                   "none", seed=6)
    c = sup["spatial_only"]
    print(f"[SUP spatial-only adjoint (R18 H4)] rho = {c['rho_step']:.4f}  "
          f"floor_ref = {c['floor_ref']:.2e}  verdict = {c['verdict']}")
    sup["slave"] = run_cell(F_main, "v2", "slave", "none", seed=7)
    c = sup["slave"]
    print(f"[SUP exact slave projection, v2 surface] own-meter floor = "
          f"{c['floor_own']:.2e}  certified-meter floor = "
          f"{c['floor_cert']:.2e}  rho = {c['rho_step']:.4f}  "
          f"({c['verdict']})  <- measure!=enforce SURFACE mismatch probe")
    sup["uniform_time_main"] = uniform_time_check(F_main)
    sup["uniform_time_axis"] = uniform_time_check(F_axis)
    u = sup["uniform_time_main"]
    print(f"[SUP uniform time stencil (v3 (I-W) alert)] k_main gauge leak: "
          f"uniform fwd {u['uniform_forward']['leak_kernel']:.3f} / uniform "
          f"bwd {u['uniform_backward']['leak_kernel']:.3f} / per-OFFSET "
          f"{u['per_offset_certified']['leak_kernel']:.1e}  <- only the "
          f"per-OFFSET mixture is certified")
    sup["foldback_certified"] = run_foldback(F_main, "certified")
    sup["foldback_v2"] = run_foldback(F_main, "v2")
    for nm in ("foldback_certified", "foldback_v2"):
        c = sup[nm]
        print(f"[SUP fold-back Re-only damping, {c['order']:9s} meter] "
              f"floor_ref = {c['floor_ref']:.2e}  own-meter floor = "
              f"{c['floor_own']:.2e}  rate/step = {c['rate_per_step']:.4f}")
    out["supplements"] = sup

    # ---- hard gates (prescription 5) on the all-correct cell -------------
    ac = [m for m in matrix if m["k"] == "k_main" and m["order"] == "certified"
          and m["enforce"] == "same" and m["source"] == "none"][0]
    acc = [m for m in matrix if m["k"] == "k_main"
           and m["order"] == "certified" and m["enforce"] == "same"
           and m["source"] == "compat"][0]
    gates = {
        "C_to_machine_floor_lt_1e-12": bool(ac["floor_cert"] < 1e-12),
        "C_machine_floor_value": ac["floor_cert"],
        "sv3_lt_0.05": bool(ac["sv3_over_sv1"] < 0.05),
        "sv3_value": ac["sv3_over_sv1"],
        "tt_match_gt_0.95": bool(ac["tt_match"] > 0.95),
        "tt_match_value": ac["tt_match"],
        "compat_source_also_machine_floor": bool(acc["floor_cert"] < 1e-10),
        "ALL_PASS": bool(ac["floor_cert"] < 1e-12
                         and ac["sv3_over_sv1"] < 0.05
                         and ac["tt_match"] > 0.95)}
    print(f"\n[HARD GATES, all-correct cell] C floor {ac['floor_cert']:.2e} "
          f"(<1e-12: {gates['C_to_machine_floor_lt_1e-12']})  sv3 "
          f"{ac['sv3_over_sv1']:.1e} (<0.05: {gates['sv3_lt_0.05']})  "
          f"tt_match {ac['tt_match']:.4f} (>0.95: {gates['tt_match_gt_0.95']})"
          f"  -> {'ALL PASS' if gates['ALL_PASS'] else 'FAIL'}")
    out["hard_gates"] = gates

    with open(os.path.join(DIR, "r20_results.json"), "w") as fh:
        json.dump(out, fh, indent=1,
                  default=lambda o: (o.tolist() if isinstance(o, np.ndarray)
                                     else float(o)))
    print("\nwrote r20_results.json")
    return out


if __name__ == "__main__":
    main()
