"""emergence_judge -- a PROJECTION-FREE emergence criterion for lattice spin-2.

WHY THIS EXISTS (the frontier, per HANDOFF #43c/#43d):
    spin2_evolver and tensor_qca both "pass three judges", but their 2 degrees
    of freedom are selected by a TT PROJECTOR AT MEASUREMENT TIME.  A hand-built
    componentwise wave equation for 10 components passes exactly the same bar.
    The harness therefore cannot distinguish "correct hand discretization of
    linearized GR" from "spin-2 genuinely emerging from the rule's dynamics".
    This module is the sharper criterion: it never applies a TT projection, and
    it demands that the RULE ITSELF dynamically eliminates the non-physical
    modes.  Both existing candidates are expected to FAIL it -- that is the
    point -- and it gives the future tensor walker an explicit pass line.

DESIGN (and why it cannot be gamed):

  Judge A -- projection-free propagating-DOF count N_prop(k).
    Excite fully generic random initial data (trace + longitudinal + gauge +
    constraint-violating content, all 10 components).  Evolve.  For selected
    lattice wavevectors k, record the 10-component complex mode amplitude time
    series.  Compute the DISCRETE LINEARIZED RIEMANN TENSOR series
        R_{mu alpha nu beta}
          = 1/2 (D_al D_nu h_{mu be} + D_mu D_be h_{al nu}
                 - D_al D_be h_{mu nu} - D_mu D_nu h_{al be})
    from commuting central differences (time: central difference of the
    series; space: exact symbol i sin k_j).  KEY FACTS:
      * Riemann is EXACTLY invariant under the discrete diffeomorphism
        h -> h + D_mu xi_nu + D_nu xi_mu for ARBITRARY xi(t,x) series
        (machine-precision certificate below; same commuting-D mechanism as
        tensor_qca.einstein_lin).  Pure-gauge content can NEVER be counted.
      * Riemann (not Ricci!) is the right invariant energy: vacuum GR waves
        have Ricci = 0 but Riemann != 0, so a true Fierz-Pauli rule would
        score N_prop = 0 under a Ricci-based count, and 2 under Riemann.
    Fourier the windowed late-time Riemann series, locate the propagating
    spectral peak, stack the peak-bin Riemann amplitude vectors of many random
    trials, and count independent polarizations by SVD numerical rank.  No
    projector anywhere: the rank is whatever curvature the rule actually
    propagates.
      * componentwise wave eq (spin2/tensor_qca vacuum rule):  N_prop = 6
        (10 components minus the 4-dim exact-gauge kernel of Riemann).
      * frozen rule: no propagating curvature at all -> N_prop = 0.
      * genuine Fierz-Pauli dynamics: N_prop = 2.
    Pass additionally requires a common light-cone speed across k directions
    (linear isotropic dispersion) and bounded field norms (stability).

  Judge B -- dynamical gauge suppression (uses tensor_qca.gauge_transform).
    Inject PURE GAUGE initial data h = D xi + D xi (static generic xi, built
    with tensor_qca.gauge_transform on a 4D block; trace-reversed into the
    evolved field).  Its invariant curvature is EXACTLY zero at t=0.  Track:
      (i)  the de Donder constraint energy |C|^2(t),
             C_nu = -(1/c^2) D_0 hbar_{0 nu} + D_j hbar_{j nu}
           (judge-side monitor, central differences, metric eta_c with the
           rule's light speed c);
      (ii) the gauge-invariant Riemann energy E_R(t) of the full lattice --
           the "gauge anomaly": a rule that respects the gauge structure keeps
           E_R ~ 0 forever; a hand-built componentwise wave rule CONVERTS
           pure-gauge data into physical curvature (measured: ~36% of the
           energy a generic IC of the same spectrum would carry);
      (iii) TT survival: a physical standing wave must NOT be damped.
    Pass = constraint decays (>=1e3 x) + gauge->physical conversion < 5%
    + TT survives.

  What honest residual gauge looks like: gauge modes compatible with the
  light cone (box xi = 0) can propagate forever in real GR too -- they carry
  exactly zero invariant energy, and Judge A/B are blind to them BY
  CONSTRUCTION (Riemann kernel).  The judges only require that gauge content
  never carries or creates invariant energy, which is the physically correct
  demand -- stronger and cleaner than demanding all gauge modes decay.

THE POSITIVE CONTROL (existence proof that the bar is passable), found by a
symbol-level analysis documented in the module (make_rule_null_damped):
    naive "leapfrog + de Donder constraint damping" is NOT enough: on the
    lattice the leapfrog box has HALF-ANGLE symbol sin^2(w/2) = c^2 sum
    sin^2(k_j/2), while the gauge structure / Riemann judge is built from
    full-angle central-difference symbols sin.  The constraint-satisfying
    on-shell subspace {C=0} of the leapfrog is then NOT TT + gauge: it keeps
    4 extra curvature-carrying polarizations, so constraint damping steadily
    damps C (measured rate -0.001/step) yet N_prop stays 5-6 -- the surviving
    top-2 directions do approach TT (tt_match ~ 0.98) but 3-4 extra carriers
    persist above threshold.  The fix needs BOTH:
      (1) a NULL-COMPATIBLE evolution operator: box built from the SAME
          commuting central differences as the gauge structure,
          box_c = eta_c^{mu nu} D_mu D_nu (a 4-level / wide-stencil update),
          so the dispersion sin^2 w = c^2 sum sin^2 k_j makes the on-shell
          symbol vector exactly eta_c-null, and {C=0} = TT + gauge EXACTLY;
      (2) constraint damping with NO TIME LAG: the kappa*C feedback on the
          hbar_{0 nu} components must use the same central time difference as
          C itself, which requires an (algebraically explicit) implicit solve;
          a one-step lag leaves the slaved 0nu response off the constraint
          surface and N_prop stays 6 (measured).
    With both ingredients: N_prop = 2 at every k (singular-value gap ~ 1e-6),
    constraint decays ~1e-31, gauge->physical conversion ~ 1e-29 (machine
    zero: the rule repairs pure-gauge data into a zero-energy pure-gauge
    trajectory instead of radiating it), TT untouched.  This "minimal
    emergence fix" is still hand-built -- but it PROVES the criterion is
    passable by a local rule and pins down exactly what structure the tensor
    walker must realize: one commuting difference calculus shared by the
    evolution operator, the constraint, and the gauge symmetry.

HONEST LIMITS:
    * The judge assumes a linear (or linearized / small-amplitude) rule and
      translation invariance; walkers should be probed in their linear regime.
    * The wide-stencil control has lattice doubler branches (pi - w); the
      judge restricts the spectral search to the continuum band w <= pi/2 and
      would report doublers as a light-cone violation if they dominated.
    * Judge A's SVD rank is w.r.t. thresholds SV_THRESH; all singular values
      are reported so no verdict hides behind a cutoff.

Run:   RULESPACE_BACKEND=numpy python -m rulespace_gpu.emergence_judge
"""
import argparse
import json
import os

import numpy as np

from . import backend as B
from . import tensor_qca as tq
from . import spin2_evolver as s2

DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# conventions: lattice units dt = dx = 1, light speed c = sqrt(cg2) (< 1 by
# CFL).  Minkowski metric in these units: eta_c = diag(-c^2, 1, 1, 1).
# packing of the 10 symmetric components: reuse the repo-wide order.
# ---------------------------------------------------------------------------
IDX10 = s2.IDX10
PK = {}
for _i, (_m, _n) in enumerate(IDX10):
    PK[(_m, _n)] = _i
    PK[(_n, _m)] = _i

# fixed judge thresholds (set from the measured gaps; every number is also
# reported raw so the thresholds can be audited):
SV_THRESH = 0.05          # bare rule: sv6 ~ 0.07-0.3 vs sv7 ~ 1e-6 ; control: sv2 ~ 0.55 vs sv3 ~ 1e-6
LIGHTCONE_TOL = 0.15      # max relative spread of w_pk/|k| across probe k
C_DECAY_PASS = 1e-3       # constraint energy must drop by >= 1000x
CONVERSION_PASS = 0.05    # gauge->physical invariant-energy conversion < 5%
TT_SURVIVAL_MIN = 0.5     # physical standing wave must keep >= 50% Riemann energy
STABLE_GROWTH_MAX = 1e5   # rms growth bound (Jordan modes give ~T linear growth)


def eta_c(c2):
    return np.diag([-float(c2), 1.0, 1.0, 1.0])


def eta_c_inv(c2):
    return np.diag([-1.0 / float(c2), 1.0, 1.0, 1.0])


def _dsp(f, j, ):
    """central spatial derivative along spatial axis j in {1,2,3} of a field
    whose LAST four axes before any trailing ones are (N,N,N)[,comp]... here we
    always call it on (..., N, N, N) scalars, so axis = j - 4."""
    ax = j - 4
    return 0.5 * (np.roll(f, -1, ax) - np.roll(f, 1, ax))


def trace_reverse_c(hb, c2):
    """packed (...,10):  h_munu = hbar_munu - 1/2 eta_c_munu tr_c(hbar).
    tr_c uses eta_c^{ab} = diag(-1/c^2,1,1,1).  Involution in 4D."""
    tr = (-(1.0 / c2) * hb[..., PK[(0, 0)]] + hb[..., PK[(1, 1)]]
          + hb[..., PK[(2, 2)]] + hb[..., PK[(3, 3)]])
    EC = eta_c(c2)
    out = hb.copy()
    for kpk, (m, n) in enumerate(IDX10):
        out[..., kpk] = hb[..., kpk] - 0.5 * EC[m, n] * tr
    return out


def packed_to_44(hp):
    """(...,10) -> (...,4,4) symmetric."""
    out = np.zeros(hp.shape[:-1] + (4, 4), dtype=hp.dtype)
    for kpk, (m, n) in enumerate(IDX10):
        out[..., m, n] = hp[..., kpk]
        out[..., n, m] = hp[..., kpk]
    return out


# ===========================================================================
#  PART 1.  the gauge-invariant measurement kernel: discrete linearized
#           RIEMANN tensor from commuting central differences.
#           (metric-free formula; exactly annihilates D xi + D xi.)
# ===========================================================================
def riemann_series_k(H44, kvec):
    """Riemann time series of one spatial Fourier mode.

    H44 : (T,4,4) complex -- the k-mode amplitude of the PHYSICAL h_munu
          (i.e. trace-reverse the evolved hbar first).
    kvec: wavevector (radians/cell).  Spatial D_j -> exact symbol i sin(k_j);
          time D_0 -> central difference of the series (unit dt).
    Returns (T-4, 256) flattened R_{mu al nu be}(t) (edges trimmed).
    """
    s = [None, 1j * np.sin(kvec[0]), 1j * np.sin(kvec[1]), 1j * np.sin(kvec[2])]

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


def riemann_energy_5slice(slices, c2):
    """Total Riemann^2 of the full lattice at the CENTER of 5 consecutive
    packed hbar slices [(N,N,N,10)] (newest last).  Time D_0 central on the
    stack; spatial D central rolls; field trace-reversed to physical h."""
    blk = np.stack([packed_to_44(trace_reverse_c(sl, c2)) for sl in slices])

    def D(f, mu):
        if mu == 0:
            out = np.zeros_like(f)
            out[1:-1] = 0.5 * (f[2:] - f[:-2])
            return out
        return 0.5 * (np.roll(f, -1, mu) - np.roll(f, 1, mu))

    G = [[D(D(blk, nu), mu)[2] for nu in range(4)] for mu in range(4)]
    tot = 0.0
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    R = 0.5 * (G[a][n][..., m, b] + G[m][b][..., a, n]
                               - G[a][b][..., m, n] - G[m][n][..., a, b])
                    tot += float(np.sum(R * R))
    return tot


def riemann_block_4d(h4):
    """Riemann of a (T,N,N,N,4,4) spacetime block using tensor_qca._D
    (periodic central differences on all four axes).  For certificates."""
    D = tq._D
    R = np.zeros(h4.shape[:-2] + (4, 4, 4, 4))
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    R[..., m, a, n, b] = 0.5 * (
                        D(D(h4[..., m, b], a), n) + D(D(h4[..., a, n], m), b)
                        - D(D(h4[..., m, n], a), b) - D(D(h4[..., a, b], m), n))
    return R


# ---------------------------------------------------------------------------
#  certificates: the judge's own validity proofs (machine precision)
# ---------------------------------------------------------------------------
def certificate_judge(N=8, T=32, seed=0):
    """(a) per-k Riemann kernel contains EVERY discrete pure-gauge series
        (arbitrary xi(t)):    max|R[D xi + D xi]| == 0  (machine).
    (b) full-block Riemann annihilates tensor_qca.gauge_transform output:
        max|R[gauge_transform(0, xi)]| == 0  (machine).
    (c) a TT plane wave DOES carry Riemann (the judge is not blind)."""
    rng = np.random.default_rng(seed)
    out = {}

    # (a) per-k series kernel
    kvec = np.array([2 * np.pi * 2 / 16, 0.0, 2 * np.pi / 16])
    s = [None, 1j * np.sin(kvec[0]), 1j * np.sin(kvec[1]), 1j * np.sin(kvec[2])]

    def D(f, mu):
        if mu == 0:
            o = np.zeros_like(f)
            o[1:-1] = 0.5 * (f[2:] - f[:-2])
            return o
        return s[mu] * f

    xi = rng.standard_normal((T, 4)) + 1j * rng.standard_normal((T, 4))
    H = np.zeros((T, 4, 4), dtype=complex)
    for m in range(4):
        for n in range(4):
            H[:, m, n] = D(xi[:, n], m) + D(xi[:, m], n)
    Rg = riemann_series_k(H, kvec)
    out["seriesk_gauge_null_resid"] = float(np.abs(Rg[2:-2]).max())
    out["seriesk_gauge_field_scale"] = float(np.abs(H).max())

    # (b) 4D block with tensor_qca.gauge_transform (the repo's own operator)
    shape = (N, N, N, N)
    xi4 = rng.standard_normal(shape + (4,))
    hpure = tq.gauge_transform(np.zeros(shape + (4, 4)), xi4)
    Rb = riemann_block_4d(hpure)
    out["block_gauge_null_resid"] = float(np.abs(Rb).max())
    out["block_gauge_field_scale"] = float(np.abs(hpure).max())

    # (c) TT plane wave is NOT in the kernel
    w = 0.4
    kz = kvec
    t = np.arange(T)
    Htt = np.zeros((T, 4, 4), dtype=complex)
    Htt[:, 1, 1] = np.exp(-1j * w * t)
    Htt[:, 2, 2] = -np.exp(-1j * w * t)
    Rtt = riemann_series_k(Htt, kz)
    out["tt_wave_riemann_scale"] = float(np.abs(Rtt[2:-2]).max())

    out["pass"] = bool(out["seriesk_gauge_null_resid"] < 1e-12
                       and out["block_gauge_null_resid"] < 1e-12
                       and out["tt_wave_riemann_scale"] > 1e-3)
    return out


# ===========================================================================
#  PART 2.  the rules under judgment.  A rule = dict with
#     name, n_levels, cg2, step(state)->state    state = tuple of packed
#  slices (batch..., N,N,N,10), newest FIRST.  Pure functions, fp64.
# ===========================================================================
def _lap3_batch(h):
    out = -6.0 * h
    for ax in (-4, -3, -2):
        out = out + np.roll(h, 1, ax) + np.roll(h, -1, ax)
    return out


def _lap_wide_batch(h):
    out = -6.0 * h
    for ax in (-4, -3, -2):
        out = out + np.roll(h, 2, ax) + np.roll(h, -2, ax)
    return out


def make_rule_spin2(cg2=0.25):
    """CANDIDATE 1: spin2_evolver's vacuum rule == componentwise leapfrog wave.
    This is ALSO the 'bare wave equation, no gauge structure' teeth control:
    10 independent wave equations.  Calls s2.leapfrog_step itself when the
    array layout allows (no batch axis), else the layout-safe equivalent."""
    def step(state):
        h, hp = state
        if h.ndim == 4:                       # (N,N,N,10): use the candidate's own code
            return (s2.leapfrog_step(h, hp, cg2), h)
        return (2.0 * h - hp + cg2 * _lap3_batch(h), h)
    return {"name": "spin2_evolver (leapfrog, harmonic gauge)",
            "n_levels": 2, "cg2": cg2, "step": step}


def make_rule_tensor_qca(cg2=0.25, gamma=0.0):
    """CANDIDATE 2: tensor_qca's evolution rule (its wave-judge configuration
    is gamma=0, which is operator-identical to spin2's leapfrog -- the module's
    new content is measurement-layer certificates, not dynamics)."""
    def step(state):
        h, hp = state
        if h.ndim == 4:
            return (tq.qca_step(h, hp, cg2, None, gamma), h)
        nxt = 2.0 * h - hp + cg2 * _lap3_batch(h)
        if gamma != 0.0:
            nxt = nxt - gamma * (h - hp)
        return (nxt, h)
    return {"name": f"tensor_qca (qca_step, gamma={gamma})",
            "n_levels": 2, "cg2": cg2, "step": step}


def make_rule_frozen(cg2=0.25):
    """TEETH CONTROL (trivial suppression): h(t+1) = h(t).  Freezes everything
    including physics -> must FAIL (N_prop = 0 != 2, constraint frozen)."""
    def step(state):
        return state
    return {"name": "frozen (h_next = h)", "n_levels": 2, "cg2": cg2, "step": step}


def make_rule_naive_damped(cg2=0.25, kappa=0.05):
    """DIAGNOSTIC CONTROL: leapfrog + de Donder constraint damping, the naive
    'minimal fix' suggested by HANDOFF #43d.  C_nu (backward time difference,
    eta_c metric) is fed back on the hbar_{0 nu} components:
        hbar_{0 nu} += kappa * C_nu.
    (This is the stable reduction of the Gundlach-type damping family
     k1*2n_(mu C_nu) + k3*n n C0 with k1=k3=-kappa: only 0nu rows survive.)
    MEASURED VERDICT: the constraint energy decays by ~30 orders, but
    N_prop stays 6: on the leapfrog mass shell (half-angle symbols) the
    constraint surface {C=0} is NOT TT+gauge, so 4 non-gauge curvature
    carriers survive.  Constraint damping alone is NOT the minimal fix."""
    c2 = float(cg2)

    def step(state):
        h, hp = state
        nxt = 2.0 * h - hp + c2 * _lap3_batch(h)
        for nu in range(4):
            c0 = PK[(0, nu)]
            C = -(1.0 / c2) * (h[..., c0] - hp[..., c0])
            for j in (1, 2, 3):
                C = C + _dsp(h[..., PK[(j, nu)]], j)
            nxt[..., c0] += kappa * C
        return (nxt, h)
    return {"name": f"leapfrog + naive de Donder damping (kappa={kappa})",
            "n_levels": 2, "cg2": cg2, "step": step}


def make_rule_null_damped(cg2=0.25, kappa=0.5):
    """POSITIVE CONTROL -- the 'minimal emergence fix' (see module docstring).

    (1) null-compatible box: box_c = eta_c^{mu nu} D_mu D_nu with the SAME
        central-1 differences as the gauge structure -> a 4-level update
        h(t+1) = 2h(t-1) - h(t-3) + c^2 * lap_wide(h(t-1))
        whose dispersion sin^2 w = c^2 sum_j sin^2 k_j puts on-shell modes on
        an exactly eta_c-NULL symbol vector, so {C=0} = TT + gauge exactly.
    (2) lag-free constraint damping (implicit in the diagonal 0nu block):
        C_nu(t) = -(1/c^2) [h(t+1)-h(t-1)]_{0nu}/2 + D_j h(t)_{j nu}
        h(t+1)_{0nu} = [bare + kappa (h(t-1)_{0nu}/(2 c^2) + D_j h(t)_{j nu})]
                        / (1 + kappa/(2 c^2))
        The slaved 0nu response then satisfies C = 0 EXACTLY (no lag term),
        for any kappa > 0.  TT is untouched exactly (its C vanishes
        identically), on-shell gauge modes survive as ZERO-ENERGY residual
        gauge (correct physics), constraint violators are damped.
    Known wart: wide stencils decouple lattice parities -> doubler branches
    at pi - w (declared in the docstring; judge probes the continuum band)."""
    c2 = float(cg2)
    fac = 1.0 / (1.0 + kappa / (2 * c2))

    def step(state):
        h1, h2, h3, h4 = state                    # t, t-1, t-2, t-3
        nxt = 2.0 * h2 - h4 + c2 * _lap_wide_batch(h2)
        for nu in range(4):
            c0 = PK[(0, nu)]
            S = np.zeros(h1.shape[:-1])
            for j in (1, 2, 3):
                S = S + _dsp(h1[..., PK[(j, nu)]], j)
            nxt[..., c0] = fac * (nxt[..., c0]
                                  + kappa * (h2[..., c0] / (2 * c2) + S))
        return (nxt, h1, h2, h3)
    return {"name": f"null-box + lag-free constraint damping (kappa={kappa})",
            "n_levels": 4, "cg2": cg2, "step": step}


# ===========================================================================
#  PART 3.  JUDGE A -- projection-free propagating-DOF count
# ===========================================================================
def judge_dof(rule, N=16, T=800, trials=12, seed=1,
              kmodes=((2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2)),
              w_max=np.pi / 2):
    """Returns per-k N_prop + light-cone diagnostics.  NO TT projector."""
    step, nlev, c2 = rule["step"], rule["n_levels"], float(rule["cg2"])
    c = np.sqrt(c2)
    rng = np.random.default_rng(seed)
    state = tuple(rng.standard_normal((trials, N, N, N, 10)) for _ in range(nlev))
    rms0 = float(np.sqrt(np.mean(state[0] ** 2)))

    kvecs = [np.array(v, float) * (2 * np.pi / N) for v in kmodes]
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    phases = np.stack([np.exp(-1j * (k[0] * X + k[1] * Y + k[2] * Z)) / N ** 3
                       for k in kvecs])

    rec = np.zeros((T, trials, len(kvecs), 10), dtype=complex)
    for t in range(T):
        state = step(state)
        rec[t] = np.einsum("kxyz,rxyzc->rkc", phases, state[0])

    rms_end = float(np.sqrt(np.mean(state[0] ** 2)))
    stable = bool(np.isfinite(rms_end) and rms_end < STABLE_GROWTH_MAX * (rms0 + 1e-30))

    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    freqs = 2 * np.pi * np.fft.fftfreq(W - 4)
    # exclude the near-DC band (static / non-propagating content leaks there
    # through the window skirt; probe modes sit at c|k| ~ 0.38-0.66 >> 0.05)
    sel = (freqs > max(0.05, 4 * np.pi / (W - 4))) & (freqs <= w_max)

    per_k = []
    for ki, kvec in enumerate(kvecs):
        rows, pow_spec = [], None
        for r in range(trials):
            Hh = trace_reverse_c(rec[T0:, r, ki, :], c2)   # physical h
            Rf = riemann_series_k(packed_to_44(Hh), kvec)
            F = np.fft.fft(Rf * win[2:-2, None], axis=0)
            P = np.sum(np.abs(F) ** 2, axis=1)
            pow_spec = P if pow_spec is None else pow_spec + P
            rows.append(F)
        total_pow = float(pow_spec[sel].sum())
        kchord = float(np.sqrt(sum(4 * np.sin(k / 2) ** 2 for k in kvec)))
        entry = {"k": [float(v) for v in kvec], "k_chord": kchord,
                 "riemann_power": total_pow}
        if not stable or total_pow < 1e-18:
            entry.update({"n_prop": 0, "w_peak": float("nan"),
                          "v_meas": float("nan"), "sv": [], "tt_match": 0.0})
            per_k.append(entry)
            continue
        pk = int(np.argmax(np.where(sel, pow_spec, 0)))
        w_pk = float(freqs[pk])
        # peak PROMINENCE: a genuine propagating line must dominate the
        # band-edge leakage floor (a static field's Riemann leaks through the
        # window skirt and "peaks" at the first allowed bin -> not propagation)
        edge = int(np.argmax(sel))                          # first allowed bin
        prominence = float(pow_spec[pk] / (pow_spec[edge] + 1e-300))
        if pk == edge or prominence < 2.0:
            entry.update({"n_prop": 0, "w_peak": float("nan"),
                          "v_meas": float("nan"), "sv": [], "tt_match": 0.0,
                          "no_propagating_peak": True})
            per_k.append(entry)
            continue
        M = np.array([r[pk] for r in rows])                # (trials, 256), +w branch
        U, sv, Vh = np.linalg.svd(M, full_matrices=False)
        svn = (sv / (sv[0] + 1e-300)).tolist()
        n_prop = int(np.sum(np.array(svn) > SV_THRESH))

        # a-posteriori identification only (NOT part of the count): overlap of
        # the surviving 2-dim polarization space with analytic TT plane waves.
        tt_match = 0.0
        if n_prop >= 1:
            shat = np.array([np.sin(k) for k in kvec])
            shat = shat / (np.linalg.norm(shat) + 1e-300)
            trial = np.array([1.0, 0.0, 0.0])
            if abs(np.dot(trial, shat)) > 0.9:
                trial = np.array([0.0, 1.0, 0.0])
            e1 = trial - np.dot(trial, shat) * shat
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(shat, e1)
            tvec = np.arange(W)
            refs = []
            for pol in (np.outer(e1, e1) - np.outer(e2, e2),
                        np.outer(e1, e2) + np.outer(e2, e1)):
                Href = np.zeros((W, 4, 4), dtype=complex)
                # +w_pk sign: np.fft.fft puts e^{+i w t} content at the +w bin
                Href[:, 1:, 1:] = pol[None] * np.exp(1j * w_pk * tvec)[:, None, None]
                Fr = np.fft.fft(riemann_series_k(Href, kvec) * win[2:-2, None], axis=0)
                refs.append(Fr[pk])
            Q1, _ = np.linalg.qr(Vh[:2].conj().T)          # data top-2 space
            Q2, _ = np.linalg.qr(np.array(refs).conj().T)  # TT reference space
            cosang = np.linalg.svd(Q1.conj().T @ Q2, compute_uv=False)
            tt_match = float(np.min(cosang) ** 2)

        entry.update({"n_prop": n_prop, "w_peak": w_pk,
                      "v_meas": w_pk / kchord,             # cells/step
                      "sv": [float(v) for v in svn[:10]], "tt_match": tt_match,
                      "peak_prominence": prominence})
        per_k.append(entry)

    n_props = [e["n_prop"] for e in per_k]
    vs = [e["w_peak"] / e["k_chord"] for e in per_k if np.isfinite(e["w_peak"])]
    if len(vs) == len(per_k) and len(vs) > 0 and np.mean(vs) > 0.05:
        spread = float((max(vs) - min(vs)) / (np.mean(vs) + 1e-300))
        lightcone_ok = bool(spread < LIGHTCONE_TOL)
    else:
        spread = float("nan")
        lightcone_ok = False

    return {"per_k": per_k, "n_prop_all": n_props,
            "n_prop": int(max(n_props)) if n_props else 0,
            "speed_mean": float(np.mean(vs)) if vs else float("nan"),
            "speed_spread": spread, "lightcone_ok": lightcone_ok,
            "stable": stable, "rms_growth": rms_end / (rms0 + 1e-30),
            "pass": bool(stable and lightcone_ok and all(n == 2 for n in n_props))}


# ===========================================================================
#  PART 4.  JUDGE B -- dynamical gauge suppression + gauge anomaly + TT survival
# ===========================================================================
def _gauge_hbar_slice(N, c2, seed=3, smooth=4):
    """Pure-gauge initial slice built with tensor_qca.gauge_transform:
    static generic xi -> h = D xi + D xi (block) -> hbar = TR_c(h) (packed).
    Static xi is deliberately NOT harmonic: it carries constraint violation,
    i.e. it is gauge data a genuinely gauge-respecting rule must neutralize
    without creating invariant energy."""
    rng = np.random.default_rng(seed)
    xi = rng.standard_normal((4, N, N, N))
    for _ in range(smooth):
        for ax in (1, 2, 3):
            xi = (np.roll(xi, 1, ax) + np.roll(xi, -1, ax) + 2 * xi) / 4
    Tb = 8
    xib = np.moveaxis(np.broadcast_to(xi[None], (Tb, 4, N, N, N)).copy(), 1, -1)
    h4 = tq.gauge_transform(np.zeros((Tb, N, N, N, 4, 4)), xib)
    sl = h4[2]                                   # any interior slice (static)
    hp = np.zeros((N, N, N, 10))
    for kpk, (m, n) in enumerate(IDX10):
        hp[..., kpk] = sl[..., m, n]
    return trace_reverse_c(hp, c2)


def _generic_slice(N, rms, seed=99, smooth=4):
    """generic (non-gauge) smooth random tensor slice, spectrum-matched to the
    gauge IC (same smoothing), for normalizing the conversion ratio."""
    rng = np.random.default_rng(seed)
    f = rng.standard_normal((N, N, N, 10))
    for _ in range(smooth):
        for ax in (0, 1, 2):
            f = (np.roll(f, 1, ax) + np.roll(f, -1, ax) + 2 * f) / 4
    return f * (rms / (np.sqrt(np.mean(f ** 2)) + 1e-300))


def _c_monitor(hnext, h, hprev, c2):
    """judge-side de Donder monitor (central time difference, eta_c)."""
    C = np.zeros(h.shape[:-1] + (4,))
    for nu in range(4):
        c0 = PK[(0, nu)]
        C[..., nu] = -(1.0 / c2) * 0.5 * (hnext[..., c0] - hprev[..., c0])
        for j in (1, 2, 3):
            C[..., nu] += _dsp(h[..., PK[(j, nu)]], j)
    return C


def _run_energy(rule, ic_slice, T, sample_every=50):
    """evolve from a static IC; sample constraint energy + Riemann energy."""
    step, nlev, c2 = rule["step"], rule["n_levels"], float(rule["cg2"])
    state = tuple(ic_slice.copy() for _ in range(nlev))
    prevs = [ic_slice.copy(), ic_slice.copy()]
    hist_c, hist_e, buf = [], [], []
    for t in range(T):
        state = step(state)
        h = state[0]
        if t >= 1 and (t % 25 == 0 or t == 1):
            C = _c_monitor(h, prevs[0], prevs[1], c2)
            hist_c.append((t, float(np.mean(C ** 2))))
        buf.append(h.copy())
        if len(buf) > 5:
            buf.pop(0)
        if t % sample_every == 0 and len(buf) == 5:
            hist_e.append((t, riemann_energy_5slice(buf, c2)))
        prevs = [h.copy(), prevs[0]]
    return hist_c, hist_e, float(np.sqrt(np.mean(state[0] ** 2)))


def judge_gauge(rule, N=16, T=600, seed=3):
    """B1 constraint decay, B2 gauge->physical conversion, B3 TT survival."""
    c2 = float(rule["cg2"])
    g0 = _gauge_hbar_slice(N, c2, seed=seed)
    rms0 = float(np.sqrt(np.mean(g0 ** 2)))

    hist_c, hist_e, rms_end = _run_energy(rule, g0, T)
    stable = bool(np.isfinite(rms_end) and rms_end < STABLE_GROWTH_MAX * (rms0 + 1e-30))

    c_init = hist_c[0][1]
    c_final = hist_c[-1][1]
    c_ratio = c_final / (c_init + 1e-300)
    # decay rate of ln C^2 per step over the section above the numerical floor
    pts = [(t, cc) for t, cc in hist_c if cc > 1e-24 * (c_init + 1e-300)]
    if len(pts) >= 2:
        ts = np.array([p[0] for p in pts], float)
        ls = np.log(np.array([p[1] for p in pts]))
        rate = float(np.polyfit(ts, ls, 1)[0])
    else:
        rate = float("nan")

    # gauge anomaly: late-time invariant energy vs a spectrum-matched generic IC
    _, ref_e, _ = _run_energy(rule, _generic_slice(N, rms0), T)
    e_late = float(np.mean([e for t, e in hist_e if t > 0.7 * T]))
    ref_late = float(np.mean([e for t, e in ref_e if t > 0.7 * T]))
    conversion = e_late / (ref_late + 1e-300)

    # TT survival: standing TT wave (static start), Riemann energy early vs late
    kz = 2 * np.pi * 2 / N
    z = np.arange(N)
    tt = np.zeros((N, N, N, 10))
    tt[..., PK[(1, 1)]] = np.cos(kz * z)[None, None, :]
    tt[..., PK[(2, 2)]] = -np.cos(kz * z)[None, None, :]
    # sample densely: a standing wave's Riemann energy oscillates with period
    # 2 pi / w ~ 16 steps; sparse sampling would alias the early/late averages.
    _, tt_e, _ = _run_energy(rule, tt, T, sample_every=5)
    tt_early = float(np.mean([e for t, e in tt_e if t <= 0.2 * T]))
    tt_late = float(np.mean([e for t, e in tt_e if t > 0.8 * T]))
    tt_survival = tt_late / (tt_early + 1e-300)

    return {"c2_init": c_init, "c2_final": c_final, "c_decay_ratio": c_ratio,
            "c_decay_rate_per_step": rate,
            "c2_curve": [(int(t), float(cc)) for t, cc in hist_c],
            "riemann_from_gauge_curve": [(int(t), float(e)) for t, e in hist_e],
            "riemann_gauge_late": e_late, "riemann_generic_late": ref_late,
            "gauge_conversion": conversion,
            "tt_survival": tt_survival, "stable": stable,
            "pass": bool(stable and c_ratio < C_DECAY_PASS
                         and conversion < CONVERSION_PASS
                         and tt_survival > TT_SURVIVAL_MIN)}


# ===========================================================================
#  PART 5.  batch interface (walker-compatible; mirrors evaluate_tensor_rule)
# ===========================================================================
PARAM_NAMES = ["rule_id", "cg2", "kappa"]
# rule_id: 0 spin2 | 1 tensor_qca | 2 frozen | 3 naive damped | 4 null-box damped
DEFAULT_PARAMS = np.array([[0.0, 0.25, 0.0],
                           [1.0, 0.25, 0.0],
                           [4.0, 0.25, 0.5]])


def _builtin_factory(row):
    rid = int(round(row[0]))
    cg2 = float(row[1])
    kappa = float(row[2])
    if rid == 0:
        return make_rule_spin2(cg2)
    if rid == 1:
        return make_rule_tensor_qca(cg2)
    if rid == 2:
        return make_rule_frozen(cg2)
    if rid == 3:
        return make_rule_naive_damped(cg2, kappa if kappa > 0 else 0.1)
    if rid == 4:
        return make_rule_null_damped(cg2, kappa if kappa > 0 else 0.5)
    raise ValueError(f"unknown rule_id {rid}")


def judge_emergence(params_batch=None, step_factory=None, quick=True, N=16):
    """Batch emergence judgment.  Style mirrors tensor_qca.evaluate_tensor_rule.

    params_batch : (Bn, 3) host array, columns = PARAM_NAMES, judged with the
                   builtin rules; OR pass step_factory(row)->rule-dict to judge
                   external rules (e.g. the tensor walker): rule-dict needs
                   {name, n_levels, cg2, step(state)->state}, state = tuple of
                   n_levels packed (batch...,N,N,N,10) slices, newest first,
                   pure fp64 functions.
    quick        : smaller T / fewer trials (judgment gaps are ~1e6, so quick
                   mode loses no discrimination).

    Returns dict of length-Bn arrays:
        n_prop          (int)   max over probe k of the projection-free count (target exactly 2)
        n_prop_min      (int)   min over probe k (must also be 2)
        lightcone_ok    (bool)  single linear dispersion across k directions
        speed           (float) measured propagation speed (cells/step)
        gauge_decay_ratio (float) constraint energy final/init (target << 1)
        gauge_decay_rate  (float) d ln|C|^2 / dt per step (negative = decays)
        gauge_conversion  (float) invariant energy created from pure-gauge IC,
                                normalized by a spectrum-matched generic IC
        tt_survival     (float) physical standing-wave Riemann energy retention
        stable          (bool)
        passes_A, passes_B, passes_emergence (bool)
    PASS LINE (for the tensor walker):  passes_emergence == True, i.e.
        n_prop == 2 at every probe k  AND  common light cone  AND
        gauge_decay_ratio < 1e-3  AND  gauge_conversion < 0.05  AND
        tt_survival > 0.5  AND  stable.
    """
    if params_batch is None:
        params_batch = DEFAULT_PARAMS
    P = np.atleast_2d(np.asarray(params_batch, dtype=float))
    factory = step_factory or _builtin_factory
    T_A, trials = (512, 8) if quick else (800, 12)
    T_B = 500 if quick else 600

    keys = ["n_prop", "n_prop_min", "lightcone_ok", "speed",
            "gauge_decay_ratio", "gauge_decay_rate", "gauge_conversion",
            "tt_survival", "stable", "passes_A", "passes_B", "passes_emergence"]
    res = {k: [] for k in keys}
    for row in P:
        rule = factory(row)
        a = judge_dof(rule, N=N, T=T_A, trials=trials)
        b = judge_gauge(rule, N=N, T=T_B)
        res["n_prop"].append(a["n_prop"])
        res["n_prop_min"].append(int(min(a["n_prop_all"])) if a["n_prop_all"] else 0)
        res["lightcone_ok"].append(a["lightcone_ok"])
        res["speed"].append(a["speed_mean"])
        res["gauge_decay_ratio"].append(b["c_decay_ratio"])
        res["gauge_decay_rate"].append(b["c_decay_rate_per_step"])
        res["gauge_conversion"].append(b["gauge_conversion"])
        res["tt_survival"].append(b["tt_survival"])
        res["stable"].append(a["stable"] and b["stable"])
        res["passes_A"].append(a["pass"])
        res["passes_B"].append(b["pass"])
        res["passes_emergence"].append(a["pass"] and b["pass"])
    return {k: np.array(v) for k, v in res.items()}


# ===========================================================================
#  driver
# ===========================================================================
def run_all(quick=False):
    out = {"backend": B.NAME, "judge_certificate": certificate_judge()}
    rules = [make_rule_spin2(),
             make_rule_tensor_qca(),
             make_rule_frozen(),
             make_rule_naive_damped(kappa=0.1),
             make_rule_null_damped(kappa=0.5)]
    T_A, trials = (512, 8) if quick else (800, 12)
    T_B = 500 if quick else 600
    verdicts = []
    for rule in rules:
        a = judge_dof(rule, T=T_A, trials=trials)
        bres = judge_gauge(rule, T=T_B)
        verdicts.append({"rule": rule["name"], "judge_A": a, "judge_B": bres,
                         "passes_emergence": bool(a["pass"] and bres["pass"])})
    out["verdicts"] = verdicts
    return out


def _fmt(x, w=9, p=2):
    if isinstance(x, bool):
        return f"{'yes' if x else 'no':>{w}}"
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return f"{'-':>{w}}"
    return f"{x:>{w}.{p}e}" if (abs(x) < 1e-3 or abs(x) >= 1e4) and x != 0 else f"{x:>{w}.{p}f}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "emergence_results.json"))
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING: backend = {B.NAME}; the judge is precision-sensitive. "
              f"Run with RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("EMERGENCE JUDGE -- projection-free spin-2 DOF count + dynamical "
          "gauge suppression\n")

    res = run_all(quick=args.quick)

    cert = res["judge_certificate"]
    print("[JUDGE CERTIFICATE] (validity of the measurement kernel itself)")
    print(f"    per-k Riemann annihilates ANY discrete gauge series: "
          f"max|R| = {cert['seriesk_gauge_null_resid']:.3e} "
          f"(field scale {cert['seriesk_gauge_field_scale']:.2f})")
    print(f"    block Riemann annihilates tensor_qca.gauge_transform: "
          f"max|R| = {cert['block_gauge_null_resid']:.3e} "
          f"(field scale {cert['block_gauge_field_scale']:.2f})")
    print(f"    TT wave carries Riemann (judge not blind): "
          f"{cert['tt_wave_riemann_scale']:.3e}")
    print(f"    -> {'PASS' if cert['pass'] else 'FAIL'}\n")

    for v in res["verdicts"]:
        a, b = v["judge_A"], v["judge_B"]
        print("=" * 78)
        print(f"RULE: {v['rule']}")
        print("  [A] projection-free DOF count (target: N_prop = 2 at every k)")
        for e in a["per_k"]:
            sv = np.array(e["sv"])
            svs = " ".join(f"{s:.1e}" for s in sv[:6]) if len(sv) else "-"
            print(f"      k={tuple(round(q, 3) for q in e['k'])}  "
                  f"N_prop={e['n_prop']}  w_pk={e['w_peak']:.4f}  "
                  f"tt_match={e['tt_match']:.3f}  sv={svs}")
        print(f"      speed={a['speed_mean']:.4f} cells/step  "
              f"spread={a['speed_spread']:.3f}  lightcone_ok={a['lightcone_ok']}  "
              f"stable={a['stable']} (rms growth {a['rms_growth']:.1e})")
        print(f"      -> {'PASS' if a['pass'] else 'FAIL'}")
        print("  [B] gauge dynamics (pure-gauge IC via tensor_qca.gauge_transform)")
        print(f"      constraint |C|^2: init={b['c2_init']:.3e} "
              f"final={b['c2_final']:.3e} ratio={b['c_decay_ratio']:.3e} "
              f"rate={b['c_decay_rate_per_step']:+.4f}/step")
        curve = b["riemann_from_gauge_curve"]
        print(f"      invariant energy from GAUGE IC: "
              + "  ".join(f"t={t}:{e:.1e}" for t, e in curve[::max(1, len(curve)//4)]))
        print(f"      gauge->physical conversion = {b['gauge_conversion']:.3e} "
              f"(vs spectrum-matched generic IC {b['riemann_generic_late']:.2e})")
        print(f"      TT survival = {b['tt_survival']:.3f}")
        print(f"      -> {'PASS' if b['pass'] else 'FAIL'}")
        print(f"  EMERGENCE VERDICT: "
              f"{'PASS' if v['passes_emergence'] else 'FAIL'}")

    print("=" * 78)
    print("\nSUMMARY TABLE")
    hdr = (f"{'rule':44s} {'Nprop':>5} {'lcone':>6} {'C-decay':>9} "
           f"{'convert':>9} {'TTsurv':>7} {'A':>4} {'B':>4} {'EMERGE':>7}")
    print(hdr)
    print("-" * len(hdr))
    for v in res["verdicts"]:
        a, b = v["judge_A"], v["judge_B"]
        print(f"{v['rule'][:44]:44s} {a['n_prop']:>5d} "
              f"{'yes' if a['lightcone_ok'] else 'no':>6} "
              f"{b['c_decay_ratio']:>9.1e} {b['gauge_conversion']:>9.1e} "
              f"{b['tt_survival']:>7.2f} "
              f"{'ok' if a['pass'] else 'X':>4} {'ok' if b['pass'] else 'X':>4} "
              f"{'PASS' if v['passes_emergence'] else 'FAIL':>7}")

    teeth = [v for v in res["verdicts"] if "spin2" in v["rule"]]
    if teeth:
        n = teeth[0]["judge_A"]["n_prop"]
        print(f"\nTEETH CHECK: bare componentwise wave rule measures N_prop = {n} "
              f"(> 2: {'yes -- the judge has teeth' if n > 2 else 'NO -- JUDGE IS BROKEN'})")

    print("\nHONEST SCOPE: the judge never applies a TT projector; it counts the")
    print("independent polarizations that carry gauge-invariant RIEMANN energy on a")
    print("common light cone, from generic random data.  spin2_evolver and tensor_qca")
    print("FAIL it (N_prop=6, no gauge suppression, ~36% gauge->physical anomaly):")
    print("their '2 DOF' were projected, not dynamical.  Naive constraint damping")
    print("damps the constraint but NOT the extra curvature carriers (symbol")
    print("mismatch).  The null-box + lag-free damping control PASSES everything --")
    print("the pass line is achievable, and the required structure is now explicit:")
    print("one commuting discrete-derivative calculus shared by evolution operator,")
    print("constraint, and gauge symmetry.  That is the tensor walker's target.")

    with open(args.json, "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {os.path.abspath(args.json)}")
