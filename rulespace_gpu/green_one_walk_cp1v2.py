"""green_one_walk_cp1v2 -- M2'-CP1 (lane B), R17 placement-operator edition.

WHAT CHANGED FROM CP1-v1.  CP1-v1 slaved the de-Donder constraint with an
INTEGER-grid first-difference template (central / forward / backward).  R15/R17
proved that is a negative control: kappa_i = 2 sin(k_i/2) is a HALF-frequency
symbol no single integer stencil realizes, so {C=0} keeps 3-4 extra curvature
carriers and N_prop stuck at 5-6.  CP1-v2 replaces the difference with the R17
PLACEMENT-OPERATOR DICTIONARY (定理笔记-R17 + r17_placement_operators.py):

  OFFSET[c][mu] = ((e_a + e_b)/2 mod 1)[mu]     for component c = (a,b)
  D_mu on component c :  backward  f(x) - f(x - e_mu)   if OFFSET[c][mu] == 1
                         forward   f(x + e_mu) - f(x)   if OFFSET[c][mu] == 0
  C_nu = sum_mu eta^{mu mu} D_mu hbar_{mu nu}   (ALL 4 rows, flat eta)
         time term (mu=0): eta^00 = -1, divided by c, D_0 = macrostep diff
         hbar_new - hbar_prev  (on the walk shell this ALREADY yields the pure
         half-angle kappa_0 = 2 sin(w/2)/c times the Yee time phase -- R16 key
         (1): the split-step's own macro-step difference is the t+1/2 field, no
         interpolation, no per-mode /cos).

DAMPING (R16 in vitro):  hbar <- hbar - gamma K^dag K hbar.  K = the R17
  constraint operator above; K^dag = reverse dictionary (spatial: adjoint rolls;
  time: local -1/c coefficient, lag-free).  ker K = TT (+) gauge, so physics is
  never damped; the 4 non-TT curvature carriers are.

  GAMMA CALIBRATION (one sanctioned round -- R16's gamma=0.3 is LATTICE-UNSTABLE,
  found this round).  R16 key (2) measured sigma^2_max ~ 2.2 at its three SMALL-k
  in-vitro modes and set gamma=0.3 (gamma sigma^2 ~ 0.66).  But the full 3D
  Brillouin zone reaches sigma^2_max ~ 28 at the corner k=(pi,pi,pi) (the linear
  damping operator, time coeff -1/c), so gamma=0.3 gives 1-gamma sigma^2 ~ -7.4
  (|.|>>1) -> BZ-corner modes blow up (measured: overflow, N_prop=0).  Stable
  domain: gamma sigma^2_max < 2 -> gamma < 0.071.  gamma = 0.05 is used:
  gamma sigma^2_max = 1.4 (< 2, stable) while the probe-mode constraint violators
  (sigma^2 in [3, 6.1]) damp as 0.85^t -> machine floor over T/2 steps.  This is
  the declared calibration, NOT a fit to pass (falsification cannons re-fired).

THE FRAME SUBTLETY THIS AGENT FOUND (declared, load-bearing).  On the integer
lattice the stored field carries a per-component Yee phase e^{i k.o(c)/2}: the
real-space constraint kernel is  diag(e^{i k.o/2}) * (TT (+) gauge)_placed.
Symbol check (r17_selfcheck_gate below, seconds): quotient the real-space kernel
by the UNSHIFTED placed gauge -> dim 5/6 (looks like the neg control); quotient
by the Yee-phased gauge diag(e^{i k.o/2}) gauge_placed -> dim 2 EXACTLY,
||C gauge|| ~ 1e-16.  So the DOF half closes in the Yee-consistent frame, and
the Riemann judge must read the staggered field in the SAME frame: a per-mode
UNIT-PHASE un-shift e^{-i k.o_sp/2} (NOT interpolation, NOT a /cos division --
lossless Fourier reading of a Yee-staggered field at its own sample points).

MEASUREMENT (3 ways, all reported, no projector anywhere):
  (A) stock ej.judge_dof         : sin(k) Riemann on the raw stored field
                                   (apples-to-apples with CP0/CP1-v1).
  (B) kappa Riemann, NO un-shift : 2 sin(k/2) direction, raw field.
  (C) kappa Riemann + Yee un-shift: the placement-consistent count.
The teeth are preserved: the no-damping 10x walk gives N_prop=6 under (C) too
(un-shift is a phase, it cannot lower SVD rank); only the constraint damping
takes 6 -> 2.

emergence_judge.py is NOT modified (strict backward-compat): the kappa /
Yee-aware Riemann lives here, local to lane B.

Run:  RULESPACE_BACKEND=numpy python -m rulespace_gpu.green_one_walk_cp1v2
      -> green_one_walk_cp1v2_results.json
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
IDX10 = ej.IDX10
PK = ej.PK

# ---- read-only import of the repo-root symbol modules (self-check gate) ------
def _load(name):
    p = os.path.join(DIR, "..", name + ".py")
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


r15 = _load("r15_walk_dedonder")
r17 = _load("r17_placement_operators")


# ==========================================================================
#  R17 PLACEMENT DICTIONARY (real-space)
# ==========================================================================
def _offset(comp):
    a, b = IDX10[comp]
    o = np.zeros(4, dtype=int)
    o[a] += 1
    o[b] += 1
    return o % 2                                # 0/1 half-step flags per dir


OFFSET = [_offset(c) for c in range(10)]        # OFFSET[comp][mu]


def _dsp_dict(f, mu, comp, use_dict=True):
    """D_mu on packed component `comp` (spatial mu in {1,2,3}).  R17 rule:
    backward if the component has a half step in direction mu, else forward.
    use_dict=False -> single flavor (forward) everywhere: the R17 negative
    control / falsification cannon (a)."""
    ax = mu - 4
    bw = bool(OFFSET[comp][mu]) if use_dict else False
    if bw:
        return f - np.roll(f, 1, ax)           # backward  f(x)-f(x-e)
    return np.roll(f, -1, ax) - f              # forward   f(x+e)-f(x)


def _dsp_dict_adj(g, mu, comp, use_dict=True):
    """adjoint of _dsp_dict along the SAME (mu,comp): F^dag = S_+ - I,
    B^dag = I - S_-  (reverse dictionary)."""
    ax = mu - 4
    bw = bool(OFFSET[comp][mu]) if use_dict else False
    if bw:
        return g - np.roll(g, -1, ax)          # B^dag = I - S_-
    return np.roll(g, 1, ax) - g               # F^dag = S_+ - I


def _constraint_C(hbar, hprev, c, use_dict=True):
    """C_nu = sum_mu eta^{mu mu} D_mu hbar_{mu nu}, all 4 rows (flat eta).
    time term mu=0: -(1/c)(hbar_new - hprev)_{0 nu}  (macrostep = t+1/2 diff)."""
    C = np.zeros(hbar.shape[:-1] + (4,))
    for nu in range(4):
        acc = np.zeros(hbar.shape[:-1])
        for mu in (1, 2, 3):                    # spatial, eta^{mu mu} = +1
            comp = PK[(mu, nu)]
            acc = acc + _dsp_dict(hbar[..., comp], mu, comp, use_dict)
        comp0 = PK[(0, nu)]                     # time, eta^00 = -1, /c
        acc = acc - (1.0 / c) * (hbar[..., comp0] - hprev[..., comp0])
        C[..., nu] = acc
    return C


def _KdagC(C, c, use_dict=True):
    """K^dag C -> packed (...,10).  Component (a,b) is term mu=a in row C_b and
    (a!=b) term mu=b in row C_a.  spatial term -> adjoint roll; time term
    (mu=0) -> local -(1/c) coefficient (lag-free, the only current-time part)."""
    grad = np.zeros(C.shape[:-1] + (10,))
    for comp, (a, b) in enumerate(IDX10):
        g = _term_adj(C[..., b], a, comp, c, use_dict)      # mu=a, row nu=b
        if a != b:
            g = g + _term_adj(C[..., a], b, comp, c, use_dict)  # mu=b, row nu=a
        grad[..., comp] = g
    return grad


def _term_adj(Cnu, mu, comp, c, use_dict):
    if mu == 0:                                # time: eta^00=-1, /c, local
        return -(1.0 / c) * Cnu
    return _dsp_dict_adj(Cnu, mu, comp, use_dict)          # spatial eta^{mm}=+1


# ==========================================================================
#  CP1-v2 rule: walk geometry + R17-dictionary (I - gamma K^dag K) damping
# ==========================================================================
def make_rule_cp1v2(th0=math.pi / 3.0, gamma=0.05, damping=True, use_dict=True,
                    c_metric_th=None, mode="soft", n_iter=1):
    """R14 graviton walk (c_gw = c_matter) + R17 placed de-Donder damping.

    use_dict=False   -> single-flavor (forward) de-Donder: falsification (a).
    c_metric_th      -> de-Donder metric light speed cos(c_metric_th); default
                        th0 (shared cone).  Wrong angle -> falsification metric.
    damping=False    -> pure 10x free walk (control, expect N_prop=6).
    mode="soft"      -> hbar -= gamma K^dag K hbar (R16 (I-gamma K^dag K)),
                        n_iter repeats per step (stable strengthening).
    mode="slave"     -> EXACT projection: solve C_nu=0 for the 0nu rows
                        (gamma -> inf limit, unconditionally stable).  This is
                        CP0/CP1's realization but now with the R17 dictionary --
                        the root-cause probe for "is the soft gamma just too weak
                        against the walk's per-step re-sourcing of constraint?".
    """
    c = math.cos(th0)
    c_dd = c if c_metric_th is None else math.cos(c_metric_th)
    cache = {"last": None, "chi": None, "hprev": None}

    def step(state):
        h = state[0]
        if cache["last"] is not h:
            cache["chi"] = gw.seed_chi(h)
            cache["hprev"] = gw.chi_to_hbar(cache["chi"])
        chi = gw.geom_walk_all(cache["chi"], th0, th0, th0, th0)
        hbar = gw.chi_to_hbar(chi)                          # tentative new field
        hprev = cache["hprev"]
        if damping and mode == "soft":
            for _ in range(n_iter):
                C = _constraint_C(hbar, hprev, c_dd, use_dict)
                hbar = hbar - gamma * _KdagC(C, c_dd, use_dict)
            for comp in range(10):                         # fold all 10 back
                chi[comp, ..., 0] = hbar[..., comp] + 1j * np.imag(chi[comp, ..., 0])
        elif damping and mode == "slave":
            # exact 0nu slave: C_nu = -(1/c)(hbar_0nu - hprev_0nu) + sum_j D_j hbar_jnu = 0
            for nu in range(4):
                S = np.zeros(hbar.shape[:-1])
                for j in (1, 2, 3):
                    comp = PK[(j, nu)]
                    S = S + _dsp_dict(hbar[..., comp], j, comp, use_dict)
                c0 = PK[(0, nu)]
                hbar[..., c0] = hprev[..., c0] + c_dd * S    # enforce C_nu = 0
            for nu in range(4):                            # fold only slaved rows
                c0 = PK[(0, nu)]
                chi[c0, ..., 0] = hbar[..., c0] + 1j * np.imag(chi[c0, ..., 0])
        cache["chi"] = chi
        cache["hprev"] = hbar
        out = (hbar, hprev)
        cache["last"] = out[0]
        return out

    tag = f"walk-geom CP1v2 R17-dict de-Donder [{mode}] gamma={gamma} n_iter={n_iter}"
    if not damping:
        tag = "walk-geom NO-damp (10x free walk, expect Nprop=6)"
    elif not use_dict:
        tag = "walk-geom SINGLE-FLAVOR de-Donder (falsify a, expect Nprop>2)"
    elif c_metric_th is not None:
        tag = f"walk-geom wrong-cone de-Donder (c_metric_th={c_metric_th})"
    return {"name": tag, "n_levels": 2, "cg2": c * c, "step": step}


def constraint_decay(rule, N=16, T=512, seed=2, c=None):
    """diagnostic: |C|^2 (R17-dict de-Donder, judge-side) at t=1 vs late, from a
    generic random IC.  Tells whether the damping actually drives C -> 0."""
    step, nlev = rule["step"], rule["n_levels"]
    cc = math.sqrt(float(rule["cg2"])) if c is None else c
    rng = np.random.default_rng(seed)
    state = tuple(rng.standard_normal((N, N, N, 10)) for _ in range(nlev))
    hprev = state[0].copy()
    c_hist = []
    for t in range(T):
        state = step(state)
        h = state[0]
        C = _constraint_C(h, hprev, cc, True)
        c_hist.append((t, float(np.mean(C ** 2))))
        hprev = h.copy()
    early = np.mean([v for t, v in c_hist if 1 <= t <= 5])
    late = np.mean([v for t, v in c_hist if t > 0.8 * T])
    return {"c2_early": float(early), "c2_late": float(late),
            "ratio": float(late / (early + 1e-300))}


# ==========================================================================
#  r17 SELF-CHECK GATE (symbol level, seconds) -- run BEFORE the 3D judge
# ==========================================================================
def _my_K_symbol(k4, c):
    """symbol matrix (4,10) of my real-space K_lin at k4=(w,kx,ky,kz)."""
    K = np.zeros((4, 10), complex)
    ETA = np.diag([-1.0, 1.0, 1.0, 1.0])
    for comp, (a, b) in enumerate(IDX10):
        def sym(mu):
            bw = bool(OFFSET[comp][mu])
            kd = k4[mu]
            s = (1 - np.exp(-1j * kd)) if bw else (np.exp(1j * kd) - 1)
            s = s * ETA[mu, mu]
            return s / c if mu == 0 else s
        K[b, comp] += sym(a)                    # term mu=a, row nu=b
        if a != b:
            K[a, comp] += sym(b)                # term mu=b, row nu=a
    return K


def r17_selfcheck_gate():
    """Confirm MY OFFSET table + fwd/bwd difference assemble kappa_placed
    (dim ker/gauge = 2) in the Yee frame, and that the single-flavor control
    does NOT.  Uses r15/r17 (read-only).  Returns the numbers for the report."""
    c = math.cos(math.pi / 3.0)
    rng = np.random.default_rng(0)
    ks = [np.array([0.5, 0.0, 0.0]), np.array([0.35, 0.35, 0.35]),
          np.array([0.7, 0.2, -0.4])]
    ks += [rng.uniform(-1.0, 1.0, 3) for _ in range(60)]
    ks = [k for k in ks if r15.shell_omega(k) is not None
          and np.linalg.norm(k) > 0.05]

    def quotient_dim(K, colfac, kap):
        Greal = colfac[:, None] * r15.gauge_block(kap)
        cg = float(np.abs(K @ Greal).max())
        u, s, vh = np.linalg.svd(K)
        rank = int(np.sum(s > 1e-10 * s[0]))
        ker = vh[rank:].conj().T
        Qg, _ = np.linalg.qr(Greal)
        kerq = ker - Qg @ (Qg.conj().T @ ker)
        _, sq, _ = np.linalg.svd(kerq, full_matrices=False)
        return rank, int(np.sum(sq > 1e-8)), cg

    dims_yee, dims_unshifted, worst_cg = set(), set(), 0.0
    for k in ks:
        w = r15.shell_omega(k)
        k4 = np.array([w, k[0], k[1], k[2]])
        kap = r15.kappa_placed(k)
        K = _my_K_symbol(k4, c) / 1j
        colfac = np.array([np.exp(0.5j * float(np.dot(k4, OFFSET[cc])))
                           for cc in range(10)])
        rank, dq, cg = quotient_dim(K, colfac, kap)
        dims_yee.add(dq)
        worst_cg = max(worst_cg, cg)
        _, dq0, _ = quotient_dim(K, np.ones(10), kap)       # unshifted gauge
        dims_unshifted.add(dq0)

    # single-flavor (no OFFSET) negative control, Yee frame
    dims_single = set()
    for k in ks:
        w = r15.shell_omega(k)
        k4 = np.array([w, k[0], k[1], k[2]])
        kap = r15.kappa_placed(k)
        Ksf = np.zeros((4, 10), complex)
        ETA = np.diag([-1.0, 1.0, 1.0, 1.0])
        for comp, (a, b) in enumerate(IDX10):
            def sym(mu):
                s = (np.exp(1j * k4[mu]) - 1) * ETA[mu, mu]
                return s / c if mu == 0 else s
            Ksf[b, comp] += sym(a)
            if a != b:
                Ksf[a, comp] += sym(b)
        colfac = np.array([np.exp(0.5j * float(np.dot(k4, OFFSET[cc])))
                           for cc in range(10)])
        _, dq, _ = quotient_dim(Ksf / 1j, colfac, kap)
        dims_single.add(dq)

    return {"n_k": len(ks),
            "dim_ker_over_gauge_YEE": sorted(dims_yee),
            "dim_ker_over_gauge_UNSHIFTED": sorted(dims_unshifted),
            "worst_C_gauge_YEE": worst_cg,
            "dim_single_flavor_YEE": sorted(dims_single),
            "GATE_PASS": bool(sorted(dims_yee) == [2] and worst_cg < 1e-10
                              and sorted(dims_single) != [2])}


# ==========================================================================
#  COUNT-FREE DIAGNOSTIC: Riemann-energy subspace decomposition
#  (the SVD N_prop count is a blunt threshold; this measures WHERE the
#   propagating curvature lives -- placed-TT vs the non-TT/non-gauge "rest".)
# ==========================================================================
def _riemann_energy_sym(kap, v10):
    """symbol-level |linearized Riemann|^2 of a packed-10 hbar amplitude v10
    at half-angle direction kap (flat trace-reverse to h first)."""
    h = _flat_trace_reverse(v10)
    H = np.zeros((4, 4), dtype=complex)
    for kpk, (m, n) in enumerate(IDX10):
        H[m, n] = H[n, m] = h[kpk]
    k = np.real(kap)
    R = 0.0
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    r = 0.5 * (k[m] * k[n] * H[a, b] + k[a] * k[b] * H[m, n]
                               - k[m] * k[b] * H[a, n] - k[a] * k[n] * H[m, b])
                    R += abs(r) ** 2
    return float(R)


def riemann_subspace_decomp(rule, kmodes, N=16, T=512, trials=8, seed=1):
    """At each probe k's propagating peak, decompose the recorded 10-vector
    (un-shifted to the placed frame) into placed-TT / placed-gauge / rest and
    report the Riemann-energy fraction in the non-TT/non-gauge REST -- the
    honest 'how far from 2 DOF' number, independent of any SVD threshold."""
    c = math.sqrt(float(rule["cg2"]))
    step, nlev = rule["step"], rule["n_levels"]
    rng = np.random.default_rng(seed)
    state = tuple(rng.standard_normal((trials, N, N, N, 10)) for _ in range(nlev))
    kvecs = [np.array(v, float) * (2 * np.pi / N) for v in kmodes]
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    ph = np.stack([np.exp(-1j * (k[0] * X + k[1] * Y + k[2] * Z)) / N ** 3
                   for k in kvecs])
    rec = np.zeros((T, trials, len(kvecs), 10), complex)
    for t in range(T):
        state = step(state)
        rec[t] = np.einsum("kxyz,rxyzc->rkc", ph, state[0])
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    freqs = 2 * np.pi * np.fft.fftfreq(W)
    sel = (freqs > 0.05) & (freqs <= np.pi / 2)
    out = []
    for ki, kv in enumerate(kvecs):
        seg = rec[T0:, :, ki, :] * win[:, None, None]
        F = np.fft.fft(seg, axis=0)
        P = np.sum(np.abs(F) ** 2, axis=(1, 2))
        pk = int(np.argmax(np.where(sel, P, 0)))
        wpk = abs(float(freqs[pk]))
        kap = np.array([2 * np.sin(wpk / 2) / c] + [2 * np.sin(kv[j] / 2)
                                                    for j in range(3)])
        k4 = np.array([wpk, *kv])
        colfac = np.array([np.exp(0.5j * float(np.dot(k4, OFFSET[cc])))
                           for cc in range(10)])
        TT = r15.tt_basis(kap)
        G = r15.gauge_block(kap)
        Qgt, _ = np.linalg.qr(np.concatenate([G, TT], axis=1))
        Qtt, _ = np.linalg.qr(TT)
        rE_tt = rE_rest = 0.0
        V = F[pk]
        for r in range(trials):
            v = V[r] * np.conj(colfac)                     # placed frame
            vtt = Qtt @ (Qtt.conj().T @ v)
            rest = v - Qgt @ (Qgt.conj().T @ v)
            rE_tt += _riemann_energy_sym(kap, vtt)
            rE_rest += _riemann_energy_sym(kap, rest)
        out.append({"k": list(kmodes[ki]), "w_peak": wpk,
                    "riem_TT": rE_tt, "riem_rest": rE_rest,
                    "rest_fraction": float(rE_rest / (rE_tt + rE_rest + 1e-300))})
    return out


# ==========================================================================
#  Yee-aware kappa-direction Riemann (local; emergence_judge untouched)
# ==========================================================================
def _flat_trace_reverse(hp):
    """h_munu = hbar_munu - 1/2 eta_munu tr_eta(hbar),  eta = diag(-1,1,1,1).
    (R16 known pit: Riemann eats h, the gauge/constraint block is hbar.)"""
    tr = (-hp[..., PK[(0, 0)]] + hp[..., PK[(1, 1)]]
          + hp[..., PK[(2, 2)]] + hp[..., PK[(3, 3)]])
    EF = np.diag([-1.0, 1.0, 1.0, 1.0])
    out = hp.copy()
    for kpk, (m, n) in enumerate(IDX10):
        out[..., kpk] = hp[..., kpk] - 0.5 * EF[m, n] * tr
    return out


def _riemann_series(H44, sdir):
    """linearized Riemann time series; spatial symbol i*sdir[j], central time."""
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


def _packed_to_44(hp):
    out = np.zeros(hp.shape[:-1] + (4, 4), dtype=hp.dtype)
    for kpk, (m, n) in enumerate(IDX10):
        out[..., m, n] = hp[..., kpk]
        out[..., n, m] = hp[..., kpk]
    return out


def recount_yee(rule, kmodes, N=16, T=512, trials=8, seed=1):
    """count N_prop with (B) kappa no-unshift and (C) kappa + Yee un-shift.
    Returns per-k dict with both counts, peak freq, and singular values."""
    step, nlev = rule["step"], rule["n_levels"]
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
        kchord = float(np.sqrt(sum(4 * np.sin(k / 2) ** 2 for k in kvec)))
        kappa_dir = np.array([2 * np.sin(k / 2) for k in kvec])
        # per-component spatial Yee un-shift phase (time offset handled by D_0)
        unshift = np.array([np.exp(-0.5j * float(np.dot(kvec, OFFSET[cc][1:])))
                            for cc in range(10)])
        entry = {"k": list(kmodes[ki]), "k_chord": kchord}
        for name, use_unshift in (("kappa_raw", False), ("kappa_yee", True)):
            rows, pow_spec = [], None
            for r in range(trials):
                hp = rec[T0:, r, ki, :].copy()
                if use_unshift:
                    hp = hp * unshift
                Hh = _flat_trace_reverse(hp)
                Rf = _riemann_series(_packed_to_44(Hh), kappa_dir)
                F = np.fft.fft(Rf * win[2:-2, None], axis=0)
                P = np.sum(np.abs(F) ** 2, axis=1)
                pow_spec = P if pow_spec is None else pow_spec + P
                rows.append(F)
            if float(pow_spec[sel].sum()) < 1e-18:
                entry[name] = {"n_prop": 0, "w_peak": float("nan"),
                               "c_gw": float("nan"), "sv": []}
                continue
            pk = int(np.argmax(np.where(sel, pow_spec, 0)))
            edge = int(np.argmax(sel))
            prom = float(pow_spec[pk] / (pow_spec[edge] + 1e-300))
            if pk == edge or prom < 2.0:
                entry[name] = {"n_prop": 0, "w_peak": float("nan"),
                               "c_gw": float("nan"), "sv": [], "no_peak": True}
                continue
            M = np.array([r[pk] for r in rows])
            _, sv, _ = np.linalg.svd(M, full_matrices=False)
            svn = (sv / (sv[0] + 1e-300)).tolist()
            w_pk = float(freqs[pk])
            entry[name] = {"n_prop": int(np.sum(np.array(svn) > ej.SV_THRESH)),
                           "w_peak": w_pk, "c_gw": w_pk / (kchord + 1e-30),
                           "sv": [float(v) for v in svn[:8]],
                           "peak_prominence": prom}
        out.append(entry)
    return out


# ==========================================================================
#  CP1-v2 driver
# ==========================================================================
def run_cp1v2(N=16, T=512, trials=8, th0=math.pi / 3.0, gamma=0.05):
    kmodes = ((2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2))
    iso_modes = ((2, 0, 0), (0, 2, 0), (0, 0, 2))
    c0 = math.cos(th0)
    out = {"backend": B.NAME, "th0": th0, "c_matter_costh": c0, "gamma": gamma,
           "N": N, "T": T, "trials": trials, "kmodes": [list(m) for m in kmodes],
           "cp1v1_reference": {"n_prop_all": [5, 5, 5, 5],
                               "note": "CP1-v1 forward-template = R17 neg control"}}

    # -- 0. r17 self-check GATE (must pass before the 3D judge) --------------
    out["r17_selfcheck_gate"] = r17_selfcheck_gate()

    # -- c_matter reference from the walk's own dispersion -------------------
    cm = gw.c_matter_table(th0, kmodes, N=N, T=T)
    out["c_matter_ref"] = cm

    # -- MAIN candidate: walk + R17-dict de-Donder ---------------------------
    rule = make_rule_cp1v2(th0=th0, gamma=gamma)
    a_stock = ej.judge_dof(rule, N=N, T=T, trials=trials, kmodes=kmodes)
    yee = recount_yee(rule, kmodes, N=N, T=T, trials=trials)
    a_iso = ej.judge_dof(rule, N=N, T=T, trials=trials, kmodes=iso_modes)
    yee_iso = recount_yee(rule, iso_modes, N=N, T=T, trials=trials)

    per_k = []
    for e_stock, ey, m in zip(a_stock["per_k"], yee, kmodes):
        cmat = cm[str(tuple(m))]["c_matter"]
        cgw = ey["kappa_yee"]["c_gw"]
        ratio = (cgw / cmat) if (np.isfinite(cgw) and cmat > 1e-9) else float("nan")
        per_k.append({
            "k": list(m),
            "n_prop_stock_sink": e_stock["n_prop"],
            "n_prop_kappa_raw": ey["kappa_raw"]["n_prop"],
            "n_prop_kappa_yee": ey["kappa_yee"]["n_prop"],
            "c_gw": cgw, "c_matter": cmat, "ratio": ratio,
            "sv_yee": ey["kappa_yee"].get("sv"),
            "w_peak_yee": ey["kappa_yee"].get("w_peak")})
    j5 = max((abs(p["ratio"] - 1.0) for p in per_k if np.isfinite(p["ratio"])),
             default=float("nan"))
    # isotropy from the Yee count peaks
    vs = [ey["kappa_yee"]["c_gw"] for ey in yee_iso
          if np.isfinite(ey["kappa_yee"]["c_gw"])]
    iso = (float((max(vs) - min(vs)) / (np.mean(vs) + 1e-30))
           if len(vs) >= 2 else float("nan"))
    nprop_yee = [p["n_prop_kappa_yee"] for p in per_k]
    out["main"] = {
        "per_k": per_k,
        "n_prop_stock_all": a_stock["n_prop_all"],
        "n_prop_kappa_raw_all": [p["n_prop_kappa_raw"] for p in per_k],
        "n_prop_kappa_yee_all": nprop_yee,
        "stable": bool(a_stock["stable"]), "rms_growth": a_stock["rms_growth"],
        "j5_max_dev": j5, "isotropy_spread": iso,
        "N_prop_yee_all_eq_2": bool(all(n == 2 for n in nprop_yee)),
        "J5_within_1e-2": bool(np.isfinite(j5) and j5 < 1e-2),
        "isotropy_within_6pct": bool(np.isfinite(iso) and iso < 0.06)}

    # -- FALSIFICATION (a): single-flavor de-Donder (no OFFSET) --------------
    rule_a = make_rule_cp1v2(th0=th0, gamma=gamma, use_dict=False)
    a_a = ej.judge_dof(rule_a, N=N, T=T, trials=trials, kmodes=kmodes)
    yee_a = recount_yee(rule_a, kmodes, N=N, T=T, trials=trials)
    npa = [ey["kappa_yee"]["n_prop"] for ey in yee_a]
    out["falsify_single_flavor"] = {
        "n_prop_stock_all": a_a["n_prop_all"],
        "n_prop_kappa_yee_all": npa,
        "NPROP_NOT_2": bool(not all(n == 2 for n in npa)),
        "note": "R17 neg control: drop OFFSET book-keeping -> dim 5/6, N_prop!=2"}

    # -- FALSIFICATION (b): theta_g != theta_matter (double cone -> J5 FAIL) --
    th_wrong = 0.9
    rule_b = make_rule_cp1v2(th0=th_wrong, gamma=gamma)
    yee_b = recount_yee(rule_b, kmodes, N=N, T=T, trials=trials)
    b_ratios = []
    for ey, m in zip(yee_b, kmodes):
        cmat = cm[str(tuple(m))]["c_matter"]           # matter ref at th0
        cgw = ey["kappa_yee"]["c_gw"]
        if np.isfinite(cgw) and cmat > 1e-9:
            b_ratios.append(cgw / cmat)
    b_dev = max((abs(r - 1.0) for r in b_ratios), default=float("nan"))
    out["falsify_double_cone"] = {
        "th_geom": th_wrong, "th_matter_ref": th0, "ratios": b_ratios,
        "j5_max_dev": b_dev,
        "J5_FAILS": bool(np.isfinite(b_dev) and b_dev > 1e-2),
        "note": "geom cone cos(0.9)=%.4f vs matter cos(pi/3)=%.4f"
                % (math.cos(th_wrong), c0)}

    # -- FALSIFICATION (c): k-direction vs kappa/Yee recount -----------------
    out["k_vs_kappa"] = {
        "stock_k_dir_all": a_stock["n_prop_all"],
        "kappa_raw_all": [p["n_prop_kappa_raw"] for p in per_k],
        "kappa_yee_all": nprop_yee,
        "note": "stock uses sin(k); Yee is the placement-consistent count"}

    # -- CONTROL: no-damping 10x free walk (teeth: Yee count must stay 6) -----
    rule_c = make_rule_cp1v2(th0=th0, gamma=gamma, damping=False)
    a_c = ej.judge_dof(rule_c, N=N, T=T, trials=trials, kmodes=kmodes)
    yee_c = recount_yee(rule_c, kmodes, N=N, T=T, trials=trials)
    out["control_no_damping"] = {
        "n_prop_stock_all": a_c["n_prop_all"],
        "n_prop_kappa_yee_all": [ey["kappa_yee"]["n_prop"] for ey in yee_c],
        "stable": bool(a_c["stable"]),
        "note": "un-shift is a phase -> cannot lower rank; must stay ~6"}

    return out


def _fmt(x):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "  nan  "
    return f"{x:8.4f}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(
        DIR, "..", "green_one_walk_cp1v2_results.json"))
    ap.add_argument("--N", type=int, default=16)
    ap.add_argument("--T", type=int, default=512)
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--gamma", type=float, default=0.05)
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING: backend={B.NAME}; run RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("M2'-CP1-v2 -- R17 placement-operator de-Donder on the R14 walk\n")

    out = run_cp1v2(N=args.N, T=args.T, trials=args.trials, gamma=args.gamma)
    th0 = out["th0"]
    print(f"theta_g = theta_matter = {th0:.6f}  (c = {out['c_matter_costh']:.4f})"
          f"   gamma = {out['gamma']}\n")

    g = out["r17_selfcheck_gate"]
    print("[r17 SELF-CHECK GATE]  (symbol level, before the 3D judge)")
    print(f"  my OFFSET+diff, dim(ker/gauge) in YEE frame      : "
          f"{g['dim_ker_over_gauge_YEE']}  (want [2])  ||C.gauge||={g['worst_C_gauge_YEE']:.1e}")
    print(f"  same, quotient by UNSHIFTED placed gauge         : "
          f"{g['dim_ker_over_gauge_UNSHIFTED']}  (looks like neg control -> the frame matters)")
    print(f"  single-flavor (no OFFSET) neg control, YEE frame : "
          f"{g['dim_single_flavor_YEE']}  (want !=2)")
    print(f"  -> GATE {'PASS' if g['GATE_PASS'] else 'FAIL'}\n")

    m = out["main"]
    print("[MAIN]  walk + R17-dict de-Donder (all numbers, no projector)")
    print(f"  {'k':12s} {'Nstock':>7} {'Nkap_raw':>9} {'Nkap_yee':>9} "
          f"{'c_gw':>9} {'c_matter':>9} {'ratio':>8}")
    for p in m["per_k"]:
        print(f"  {str(tuple(p['k'])):12s} {p['n_prop_stock_sink']:>7} "
              f"{p['n_prop_kappa_raw']:>9} {p['n_prop_kappa_yee']:>9} "
              f"{_fmt(p['c_gw'])} {_fmt(p['c_matter'])} {_fmt(p['ratio'])}")
    print(f"  N_prop(YEE) all = {m['n_prop_kappa_yee_all']}   stable={m['stable']} "
          f"(rms growth {m['rms_growth']:.2e})")
    print(f"  J5 max|r-1| = {m['j5_max_dev']:.3e}   isotropy = {m['isotropy_spread']:.4f}")
    print(f"  -> N_prop==2 all k (YEE): {m['N_prop_yee_all_eq_2']}   "
          f"J5<1e-2: {m['J5_within_1e-2']}   iso<6%: {m['isotropy_within_6pct']}\n")

    print("FALSIFICATION CANNON:")
    fa = out["falsify_single_flavor"]
    print(f"  [a] single-flavor (no OFFSET): N_prop(YEE)={fa['n_prop_kappa_yee_all']} "
          f"-> {'FAILS as required (!=2)' if fa['NPROP_NOT_2'] else 'STILL 2 (toothless!)'}")
    fb = out["falsify_double_cone"]
    print(f"  [b] theta_g!=theta_matter: {fb['note']}")
    print(f"      J5 max|r-1|={fb['j5_max_dev']:.3e} -> "
          f"{'J5 FAILS as required' if fb['J5_FAILS'] else 'DID NOT FAIL (toothless!)'}")
    kk = out["k_vs_kappa"]
    print(f"  [c] k-vs-kappa: stock(k)={kk['stock_k_dir_all']}  "
          f"kappa_raw={kk['kappa_raw_all']}  kappa_yee={kk['kappa_yee_all']}")
    cc = out["control_no_damping"]
    print(f"  [ctrl] no-damping 10x walk: N_prop(YEE)={cc['n_prop_kappa_yee_all']} "
          f"(must stay ~6 -- un-shift cannot fake the count)")

    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: (
            o.tolist() if isinstance(o, np.ndarray) else float(o)))
    print(f"\nwrote {os.path.abspath(args.json)}")
