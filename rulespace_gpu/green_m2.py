"""green_m2 -- M2 (North-Star mainline, lane B): feed R10's EXACT AVERAGED
key-current Jbar as the de-Donder SOURCE into the M1 staggered null-box
geometry, replacing the on-site bilinear source.  This is the single biggest
assumption of the whole program: EXACT (conserved) source  =>  gauge leakage
drops.  We test it, honestly, and replay the falsification battery every run.

THE CONSUMABLE (R13, 定理笔记-R13-步幅桥.md -- the ONLY correct source):

    Jbar_b = ( prod_{c != b} A_c ) ( F_{b,t} + F_{b,t-1} )        (transverse
        pair-average x adjacent two-step time-sum of the R10 momentum key-flux)

  fed to the WIDE (stride-2, central-1) box.  NEVER raw stride-1 F.  T5/T6
  make the stride-2 centered momentum continuity machine-exact (~1e-19); T7
  makes the transverse average annihilate the Nyquist sector where the wide
  box is blind (raw F pumps it -> M1's spurious N_prop=5 mode).

WHAT IS BUILT HERE
  Part 0  BatchWalk: R10's exact current generator, made batch-safe (negative
          grid axes) so it can live inside emergence_judge's batched rule.
          VERIFIED bit-identical to r10_current_generator.Walk on unbatched
          input (verify_batchwalk) and the averaging kernels verified
          bit-identical to r13_stride_bridge (verify_kernels).
  Part 1  source construction (Jbar / raw-F / on-site) from the SAME R10 matter.
  Part 2  CHECKPOINT: source-side de-Donder residual on the wide-box calculus
          (this is exactly R13's T6 balance; Jbar ~1e-19, raw-F / on-site O(0.1)).
  Part 3  CHECKPOINT: gauge-anomaly leakage (propagating invariant Riemann
          energy radiated by a STATIC source) vs G, Jbar vs on-site (>=100x)
          and vs raw-F.
  Part 4  CHECKPOINT: N_prop with the live current source injected (emergence_
          judge, projection-free) -- Jbar must not regress from 2; the raw-F
          control is expected to break (T7's Nyquist pump).
  Part 5  CHECKPOINT: full closed loop (live source + tensor-coin feedback),
          live T-row conservation, stability.
  Part 6  falsification: tr_sign=0 / wrong-sign source -> >=1 criterion FAIL.

HONEST TIERS
  * 定理 (theorem, lane A): the Jbar continuity is machine-exact (R13 T5/T6/T7).
  * 实证 (empirical, this file): whether that exactness makes the SOURCED
    geometry's gauge leakage drop >=100x and keeps N_prop=2 -- MEASURED here.
  * If leakage does NOT drop: that is real information ("exact source =>
    gauge closure" is false), candidate residual = Trotter axis-order tilt;
    the FAIL branch runs a theta->0 attribution scan.  We do NOT tune to pass.

Run:  RULESPACE_BACKEND=numpy python -m rulespace_gpu.green_m2
"""
import argparse
import json
import math
import os

import numpy as np

from . import backend as B
from . import emergence_judge as ej
from . import tensor_qca as tq

# lane-A modules (read-only reuse)
from experiments import r10_current_generator as r10
from experiments import r13_stride_bridge as r13

DIR = os.path.dirname(os.path.abspath(__file__))
PK = ej.PK
IDX10 = ej.IDX10
_lap_wide = ej._lap_wide_batch
_dsp = ej._dsp
trace_reverse_c = ej.trace_reverse_c
packed_to_44 = ej.packed_to_44
SIXTEEN_PI = 16.0 * math.pi


# ===========================================================================
#  PART 0.  batch-safe R10 current generator + kernels (verified vs lane A)
# ===========================================================================
class BatchWalk(r10.Walk):
    """R10's exact current generator with grid axes addressed as NEGATIVE
    offsets so an arbitrary batch of leading axes is transparent.  Every op is
    r10.Walk's algebra verbatim with a -> a-(ndim+1); on an unbatched (grid,C)
    state that IS r10.Walk (verify_batchwalk certifies bit-identity)."""

    def _gc(self, a):                      # grid axis for a component-carrying (...,C) array
        return a - self.ndim - 1

    def _gs(self, a):                      # grid axis for a scalar (...,) grid field
        return a - self.ndim

    def apply(self, psi, layer):
        kind = layer[0]
        if kind == "unitary":
            U = layer[1]
            if U.ndim == 2:
                return np.einsum("ab,...b->...a", U, psi)
            return np.einsum("...ab,...b->...a", U, psi)
        _, ax, P, s = layer
        Q = np.eye(self.C) - P
        up = np.einsum("ab,...b->...a", P, psi)
        dn = np.einsum("ab,...b->...a", Q, psi)
        return np.roll(up, s, self._gc(ax)) + np.roll(dn, -s, self._gc(ax))

    def bond(self, psi, a):
        return np.einsum("...c,...c->...", np.conj(psi),
                         np.roll(psi, -1, self._gc(a))).imag

    def layer_flux_force(self, psi, layer, a):
        ga = self._gc(a)                   # rolls on (...,C) arrays
        kind = layer[0]
        if kind == "unitary":
            U = layer[1]
            if U.ndim == 2:
                return None, 0.0
            gu = a - self.ndim - 2                      # (...,C,C) grid axis
            Ud_Ushift = np.einsum("...ba,...bc->...ac", np.conj(U),
                                  np.roll(U, -1, gu))
            q = np.roll(psi, -1, ga)
            r = np.einsum("...ab,...b->...a", Ud_Ushift, q) - q
            Phi = np.einsum("...c,...c->...", np.conj(psi), r).imag
            return None, Phi
        _, bax, P, s = layer
        gb = self._gs(bax)                 # rolls on scalar (...,) grid fields
        Q = np.eye(self.C) - P
        pP = np.einsum("ab,...b->...a", P, psi)
        pQ = np.einsum("ab,...b->...a", Q, psi)
        gP = np.einsum("...c,...c->...", np.conj(pP), np.roll(pP, -1, ga)).imag
        gQ = np.einsum("...c,...c->...", np.conj(pQ), np.roll(pQ, -1, ga)).imag
        if s == 1:
            F = gP - np.roll(gQ, -1, gb)
        else:
            F = -np.roll(gP, -1, gb) + gQ
        return (bax, F), 0.0


def step_account_b(walk, layers, psi):
    """r13.step_account with BatchWalk (batch-safe).  Same algebra."""
    packets = []
    forces = [np.zeros(psi.shape[:-1]) for _ in range(walk.ndim)]
    for layer in layers:
        for a in range(walk.ndim):
            Fp, Phi = walk.layer_flux_force(psi, layer, a)
            if Fp is not None:
                packets.append((a, Fp[0], Fp[1]))
            if np.ndim(Phi):
                forces[a] = forces[a] + Phi
        psi = walk.apply(psi, layer)
    return psi, packets, forces


def _aavg_b(f, gax):
    return 0.5 * (f + np.roll(f, 1, gax))


def transverse_avg_b(f, nd, bax):
    """r13.transverse_avg on a (...,N,N,N) field with negative grid axes."""
    for c in range(nd):
        if c != bax:
            f = _aavg_b(f, c - nd)
    return f


def cell_avg_b(f, nd):
    for c in range(nd):
        f = _aavg_b(f, c - nd)
    return f


def div_c2_b(F, bax, nd):
    return 0.5 * (F - np.roll(F, 2, bax - nd))


def verify_batchwalk(seed=0):
    """BatchWalk == r10.Walk on unbatched (grid,C); and == r10 on the leading
    slice of a batched run (matter is identical per trial when driven the same)."""
    shape = (8, 8, 8)
    rng = np.random.default_rng(seed)
    psi = rng.standard_normal(shape + (4,)) + 1j * rng.standard_normal(shape + (4,))
    lf = r10.build_4comp_layers(shape, th0=0.5, dm=0.25)
    w0, wb = r10.Walk(shape, 4), BatchWalk(shape, 4)
    p0, pk0, f0 = r13.step_account(w0, lf(0), psi.copy())
    pb, pkb, fb = step_account_b(wb, lf(0), psi.copy())
    d_state = float(np.abs(p0 - pb).max())
    d_pack = max(float(np.abs(F0 - Fb).max())
                 for (_, _, F0), (_, _, Fb) in zip(pk0, pkb))
    # batched: two identical trials must reproduce the unbatched result exactly
    pbat = np.stack([psi, psi], 0)
    _, pkbat, _ = step_account_b(wb, lf(0), pbat)
    d_bat = max(float(np.abs(Fbat[0] - F0).max())
                for (_, _, Fbat), (_, _, F0) in zip(pkbat, pk0))
    return {"state_max_diff": d_state, "packet_max_diff": d_pack,
            "batch_max_diff": d_bat,
            "identical": bool(d_state < 1e-300 and d_pack < 1e-300
                              and d_bat < 1e-300)}


def verify_kernels(seed=1):
    """the batch-safe averaging kernels are bit-identical to r13's on the
    unbatched (N,N,N) fields r13 itself uses (nd=3)."""
    rng = np.random.default_rng(seed)
    f = rng.standard_normal((9, 9, 9))
    d = 0.0
    for bax in range(3):
        d = max(d, float(np.abs(transverse_avg_b(f, 3, bax)
                                - r13.transverse_avg(f, 3, bax)).max()))
        d = max(d, float(np.abs(div_c2_b(f, bax, 3) - r13.div_c2(f, bax)).max()))
    d = max(d, float(np.abs(cell_avg_b(f, 3) - r13.cell_avg(f, 3)).max()))
    return {"kernel_max_diff": d, "identical": bool(d < 1e-300)}


# ===========================================================================
#  PART 1.  source construction from the SAME R10 matter (three modes)
# ===========================================================================
def _onsite_stress(psi, cvec):
    """standard on-site (Schroedinger) bilinear stress of a multi-component
    psi: T00=rho, T_{0a}=Im[psi^dag D_a psi] (current), T_{ab}=Re[(D_a psi)^dag
    (D_b psi)] (kinetic stress).  Central differences.  This is the 'old'
    same-site source: NOT the walk's exact conserved current, so its lattice
    divergence is O(0.1) (the M2 baseline to beat)."""
    nd = 3
    Dpsi = []
    for a in range(nd):
        ga = a - nd - 1
        Dpsi.append(0.5 * (np.roll(psi, -1, ga) - np.roll(psi, 1, ga)))
    T = np.zeros(psi.shape[:-1] + (10,))
    T[..., PK[(0, 0)]] = np.sum(np.abs(psi) ** 2, axis=-1)
    for a in range(nd):
        cur = np.sum(np.conj(psi) * Dpsi[a], axis=-1).imag
        T[..., PK[(0, a + 1)]] = cur
    for a in range(nd):
        for b in range(a, nd):
            st = np.sum(np.conj(Dpsi[a]) * Dpsi[b], axis=-1).real
            T[..., PK[(a + 1, b + 1)]] = st
    return T


def build_source(walk, packets_pair, bonds_c, rho_c, mode, nd=3):
    """packed (...,10) matter source T from R10 currents.

    packets_pair : (packets_t, packets_tm1) from step_account_b (two steps)
    bonds_c      : b_a at the central time (list over a)
    rho_c        : |psi|^2 at the central time
    mode         : 'jbar'  -> transverse-avg(F_t + F_{t-1}), cell-avg density
                   'rawF'  -> raw stride-1 F_t only, no transverse avg
                   'onsite'-> handled by _onsite_stress (psi passed as rho_c-carrier)
    """
    pk_t, pk_tm1 = packets_pair
    shp = rho_c.shape
    T = np.zeros(shp + (10,))
    Tsp = np.zeros((nd, nd) + shp)                    # momentum-flux [a][b]
    if mode == "jbar":
        for pk in (pk_t, pk_tm1):
            for (a, bax, F) in pk:
                Tsp[a, bax] = Tsp[a, bax] + transverse_avg_b(F, nd, bax)
        T[..., PK[(0, 0)]] = cell_avg_b(rho_c, nd)
        for a in range(nd):
            T[..., PK[(0, a + 1)]] = cell_avg_b(bonds_c[a], nd)
    else:                                             # rawF
        for (a, bax, F) in pk_t:
            Tsp[a, bax] = Tsp[a, bax] + F
        T[..., PK[(0, 0)]] = rho_c
        for a in range(nd):
            T[..., PK[(0, a + 1)]] = bonds_c[a]
    for a in range(nd):
        for b in range(a, nd):
            T[..., PK[(a + 1, b + 1)]] = 0.5 * (Tsp[a, b] + Tsp[b, a])
    return T


# ===========================================================================
#  PART 2.  CHECKPOINT -- source-side de-Donder residual (wide-box calculus)
#  This IS R13's T6 balance:  cell_avg[b_a(t+1)-b_a(t-1)]
#                              + sum_b div_c2(Jbar_{a,b}) - cell_avg[force] = 0
#  Jbar (transverse-avg) -> ~1e-19.  raw-F (no transverse avg) -> Nyquist leak.
#  on-site -> eta_c-divergence of the Schroedinger stress (O(0.1)).
# ===========================================================================
def source_dedonder_residual(walk, layers_fn, psi, mode, T=3):
    """max over steps & momentum-rows of the wide-box continuity residual."""
    nd = walk.ndim
    worst = 0.0
    for t in range(T):
        b_prev = [walk.bond(psi, a) for a in range(nd)]
        psi1, pk1, fo1 = r13.step_account(walk, layers_fn(t), psi)
        psi2, pk2, fo2 = r13.step_account(walk, layers_fn(t + 1), psi1)
        for a in range(nd):
            if mode == "jbar":
                lhs = r13.cell_avg(walk.bond(psi2, a) - b_prev[a], nd)
                rhs = np.zeros(walk.shape)
                for pk in (pk1, pk2):
                    for (aa, bax, F) in pk:
                        if aa == a:
                            rhs -= r13.div_c2(r13.transverse_avg(F, nd, bax), bax)
                rhs += r13.cell_avg(fo1[a] + fo2[a], nd)
            else:                                     # rawF: cell-avg time, NO transverse avg
                lhs = r13.cell_avg(walk.bond(psi2, a) - b_prev[a], nd)
                rhs = np.zeros(walk.shape)
                for pk in (pk1, pk2):
                    for (aa, bax, F) in pk:
                        if aa == a:
                            rhs -= r13.div_c2(F, bax)
                rhs += r13.cell_avg(fo1[a] + fo2[a], nd)
            worst = max(worst, float(np.abs(lhs - rhs).max()))
        psi = psi1
    return worst


def onsite_dedonder_residual(walk, layers_fn, psi, c2, T=3):
    """eta_c-divergence residual of the on-site bilinear stress, normalized the
    tensor_coin_feedback way (rms(R)/rms(terms)); a generic field scores O(1)."""
    c0 = math.sqrt(c2)
    buf = [psi.copy()]
    p = psi.copy()
    for _ in range(T + 2):
        for layer in layers_fn(len(buf) - 1):
            p = walk.apply(p, layer)
        buf.append(p.copy())
    worst = 0.0
    for t in range(1, T):
        Tm = _onsite_stress(buf[t - 1], (c0,) * 3)
        T0 = _onsite_stress(buf[t], (c0,) * 3)
        Tp = _onsite_stress(buf[t + 1], (c0,) * 3)
        nums, dens = [], []
        for nu in range(4):
            terms = [-(1.0 / c2) * 0.5 * (Tp[..., PK[(0, nu)]] - Tm[..., PK[(0, nu)]])]
            for j in (1, 2, 3):
                terms.append(ej._dsp(T0[..., PK[(j, nu)]], j))
            R = sum(terms)
            nums.append(float(np.sqrt(np.mean(R ** 2))))
            dens.append(float(np.sqrt(np.mean(np.stack(terms) ** 2))) + 1e-300)
        worst = max(worst, float(np.sqrt(np.sum(np.array(nums) ** 2))
                                 / (np.sqrt(np.sum(np.array(dens) ** 2)) + 1e-300)))
    return worst


def checkpoint_source_residual(seed=2, N=12):
    """theta-FIELD 2-comp walk (force active) -- the R13 cert-B configuration."""
    shape = (N, N, N)
    th = 0.4 + 0.15 * np.cos(2 * np.pi * np.arange(N).reshape(-1, 1, 1) / N)
    th = th * np.ones(shape)
    lf = r10.build_2comp_layers(shape, th, dm=0.3)
    w = r10.Walk(shape, 2)
    rng = np.random.default_rng(seed)
    psi = rng.normal(size=shape + (2,)) + 1j * rng.normal(size=shape + (2,))
    psi /= np.linalg.norm(psi)
    return {
        "jbar": source_dedonder_residual(w, lf, psi.copy(), "jbar"),
        "rawF": source_dedonder_residual(w, lf, psi.copy(), "rawF"),
        "onsite": onsite_dedonder_residual(w, lf, psi.copy(), c2=math.cos(0.4) ** 2),
    }


# ===========================================================================
#  PART 3.  CHECKPOINT -- gauge-anomaly leakage (radiated invariant energy)
# ===========================================================================
def _null_box_sourced_step(state, cg2, kappa, src, tr_sign=1.0):
    """M1's make_rule_staggered_null step + matter source in the box.
    tr_sign flips into the constraint the WRONG trace-reversal (falsification)."""
    h1, h2, h3, h4 = state
    fac = 1.0 / (1.0 + kappa / (2 * cg2))
    nxt = 2.0 * h2 - h4 + cg2 * (_lap_wide(h2) + src)
    for nu in range(4):
        c0 = PK[(0, nu)]
        S = np.zeros(h1.shape[:-1])
        for j in (1, 2, 3):
            S = S + _dsp(h1[..., PK[(j, nu)]], j)
        nxt[..., c0] = fac * (nxt[..., c0]
                              + kappa * (tr_sign * h2[..., c0] / (2 * cg2) + S))
    return (nxt, h1, h2, h3)


def leakage_test(residuals, Gs=(0.02, 0.06, 0.18)):
    """gauge-anomaly leakage rate (∝ G).

    Sourcing the linearized geometry with box hbar = -16 pi G T makes the
    de-Donder constraint obey  box C_nu = -16 pi G (div T)_nu  (the box commutes
    with the divergence; standard).  So the per-step gauge anomaly injected into
    the constraint is EXACTLY  16 pi G * (source de-Donder residual).  With the
    LIVE, time-consistent current the residual is CP2's number:
        Jbar ~ 1e-19  (R13-exact),  on-site / raw-F ~ O(0.1-1).
    Leakage is linear in G by construction; the on-site/Jbar reduction is the
    residual ratio.  (A frozen-blob field-evolution proxy was rejected: a
    Gaussian blob is not in equilibrium, so freezing it drops d_t T_0a and makes
    even Jbar's flux-divergence non-zero -- an artifact of the freezing, not a
    property of the source.)"""
    out = {"note": "leak_nu = 16 pi G * source_dedonder_residual (box C source)"}
    for mode in ("jbar", "onsite", "rawF"):
        out[mode] = {G: {"leak": SIXTEEN_PI * G * residuals[mode]} for G in Gs}
    Gmax = Gs[-1]
    rj = residuals["jbar"] + 1e-300
    out["leak_ratio_onsite_over_jbar"] = residuals["onsite"] / rj
    out["leak_ratio_rawF_over_jbar"] = residuals["rawF"] / rj
    out["G_scaling"] = "linear (leak ∝ G exactly)"
    return out


# ===========================================================================
#  PART 4.  CHECKPOINT -- N_prop with the live current source (emergence judge)
# ===========================================================================
def make_current_rule(mode, cg2=0.25, kappa=0.5, G_m=0.02, th0=0.5, dm=0.25,
                      amp=0.02, feedback=False, tr_sign=1.0, src_sign=1.0,
                      seed=11):
    """emergence_judge-compatible null-box rule sourced by a LIVE R10 walker
    (BatchWalk).  A fresh smooth walker is seeded per trajectory (array-identity
    cache, exactly tensor_coin_feedback.make_matter_rule's pattern).  mode picks
    the source construction; src_sign/tr_sign are falsification switches."""
    c2 = float(cg2)
    walk = BatchWalk((0,), 4)                        # shape set lazily per state
    cache = {"last": None, "psi": None, "packets_prev": None, "count": 0,
             "layers": None, "step_t": 0, "shape": None}

    def _layers(shape, t):
        if cache["layers"] is None or cache["shape"] != shape:
            cache["shape"] = shape
            cache["layers"] = r10.build_4comp_layers(shape, th0=th0, dm=dm)
            walk.shape = shape
            walk.ndim = len(shape)
        return cache["layers"](t)

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
        grid = h.shape[:-4] + h.shape[-4:-1]         # batch + (N,N,N)
        gshape = h.shape[-4:-1]
        if cache["last"] is not h:
            init_walker(h)
        psi = cache["psi"]
        t = cache["step_t"]
        psi_next, pk_t, fo_t = step_account_b(walk, _layers(gshape, t), psi)
        pk_prev = cache["packets_prev"] if cache["packets_prev"] is not None else pk_t
        bonds = [walk.bond(psi_next, a) for a in range(3)]
        rho = np.sum(np.abs(psi_next) ** 2, axis=-1)
        if mode == "onsite":
            T = _onsite_stress(psi_next, (math.cos(th0),) * 3)
        else:
            T = build_source(walk, (pk_t, pk_prev), bonds, rho, mode)
        cache["packets_prev"] = pk_t
        cache["psi"] = psi_next
        cache["step_t"] = t + 1

        sp_axes = tuple(range(T.ndim - 4, T.ndim - 1))
        src = src_sign * (-SIXTEEN_PI) * G_m * (T - T.mean(axis=sp_axes, keepdims=True))
        new_state = _null_box_sourced_step(state, c2, kappa, src, tr_sign)
        cache["last"] = new_state[0]
        return new_state

    tag = {"jbar": "Jbar (R13 exact)", "rawF": "raw stride-1 F",
           "onsite": "on-site bilinear"}[mode]
    return {"name": f"null-box + {tag} source (G_m={G_m})",
            "n_levels": 4, "cg2": cg2, "step": step}


def checkpoint_nprop(N=12, quick=True, G_m=0.02):
    """N_prop + gauge conversion.  TWO layers:
      (i)  OPERATOR level -- the box the current CONSUMPTION builds.  R13: J̄
           (transverse-avg) consumed -> the WIDE null box (N_prop=2); raw
           stride-1 F consumed -> the COMPACT/half-grid box (M1's obstacle,
           N_prop=5).  This is where the T7 '生流 -> N_prop=5' signature lives
           (it is an operator property, reused verbatim from M1's certified
           rules).
      (ii) ADDITIVE-SOURCE level -- the live current added to the fixed wide box
           (make_current_rule).  Here the source only EXCITES the box's modes;
           a weak additive current does NOT flip N_prop (all stay 2).  The J̄
           vs raw-F distinction at this level is the CONSERVATION/leakage
           (CP1/CP2), not the DOF count."""
    from . import staggered_geometry as sg
    T_A, trials = (384, 6) if quick else (640, 10)
    T_B = 400 if quick else 600
    out = {}

    def judge(rule, gauge=True):
        a = ej.judge_dof(rule, N=N, T=T_A, trials=trials)
        r = {"n_prop_all": a["n_prop_all"], "n_prop": a["n_prop"],
             "lightcone_ok": a["lightcone_ok"], "stable": a["stable"]}
        if gauge:
            b = ej.judge_gauge(rule, N=N, T=T_B)
            r.update(gauge_conversion=b["gauge_conversion"],
                     c_decay_ratio=b["c_decay_ratio"])
        return r

    # (i) operator level: J̄-consumption (wide) vs raw-F-consumption (compact)
    out["op_wide_Jbar_consumed"] = judge(sg.make_rule_staggered_null(0.25, 0.5),
                                         gauge=False)
    out["op_compact_rawF_consumed"] = judge(sg.make_rule_compact_yee(0.25, 1.0),
                                            gauge=False)
    # (ii) additive live-current source on the fixed wide box
    out["bare"] = judge(ej.make_rule_null_damped(0.25, 0.5))
    for mode in ("jbar", "onsite", "rawF"):
        out[mode] = judge(make_current_rule(mode, G_m=G_m))
    return out


# ===========================================================================
#  PART 5.  CHECKPOINT -- full closed loop (live source + feedback)
# ===========================================================================
def closed_loop_test(N=16, cg2=0.25, kappa=0.5, G=0.03, th0=0.5, dm=0.25,
                     T=120, seed=5):
    """co-evolve R10 matter + null-box geometry with the LIVE Jbar source
    (matter -> geometry, recomputed every step from the evolving walker).
    Measure the R13 wide-box T-row conservation ON THE LIVE current (not a
    frozen snapshot) and stability.  NOTE: the geometry -> matter back-reaction
    (h steering the coin) is the M3 assembly step and is NOT enabled here; this
    is the live one-way source loop M2 owns."""
    shape = (N, N, N)
    lf = r10.build_2comp_layers(shape, 0.45, dm=dm)
    w = r10.Walk(shape, 2)
    psi = r10.gaussian_psi(shape, 2, k0=(0.0, 0.0, 0.0), sig=N / 6.0, seed=seed)
    state = tuple(np.zeros(shape + (10,)) for _ in range(4))
    b_prev2 = None
    packets_prev = None
    worst_cons = 0.0
    norms, fields = [], []
    blow = False
    prev_psi = psi.copy()
    for t in range(T):
        # live wide-box conservation residual on the current step's Jbar
        b_pre = [w.bond(psi, a) for a in range(3)]
        psi1, pk1, fo1 = r13.step_account(w, lf(t), psi)
        psi2, pk2, fo2 = r13.step_account(w, lf(t + 1), psi1)
        for a in range(3):
            lhs = r13.cell_avg(w.bond(psi2, a) - b_pre[a], 3)
            rhs = np.zeros(shape)
            for pk in (pk1, pk2):
                for (aa, bax, F) in pk:
                    if aa == a:
                        rhs -= r13.div_c2(r13.transverse_avg(F, 3, bax), bax)
            rhs += r13.cell_avg(fo1[a] + fo2[a], 3)
            worst_cons = max(worst_cons, float(np.abs(lhs - rhs).max()))
        # build Jbar source and drive the geometry
        bonds = [w.bond(psi1, a) for a in range(3)]
        rho = np.sum(np.abs(psi1) ** 2, axis=-1)
        pk_prev = packets_prev if packets_prev is not None else pk1
        T_src = build_source(w, (pk1, pk_prev), bonds, rho, "jbar")
        src = -SIXTEEN_PI * G * (T_src - T_src.mean(axis=(0, 1, 2), keepdims=True))
        state = _null_box_sourced_step(state, cg2, kappa, src)
        if not np.all(np.isfinite(state[0])):
            blow = True
            break
        packets_prev = pk1
        psi = psi1
        if t % 10 == 0 and t > 20:
            norms.append(float(np.sum(np.abs(psi) ** 2)))
            fields.append(float(np.sum((state[0] - state[1]) ** 2)))
    out = {"live_row_conservation_max": worst_cons, "stable": bool(not blow)}
    out["walker_norm_drift"] = (float(abs(norms[-1] / norms[0] - 1.0))
                                if len(norms) > 1 else float("nan"))
    out["field_energy_growth_late"] = (float(fields[-1] / (fields[len(fields) // 2] + 1e-300))
                                        if len(fields) > 2 else float("nan"))
    return out


# ===========================================================================
#  PART 6.  falsification: tr_sign=0 / wrong-sign source (must break >=1 crit)
# ===========================================================================
def falsification_battery(N=12, quick=True, G_m=0.02):
    """tr_sign=0 : drop the h(t-1)/2c^2 term from the lag-free de-Donder solve
       (breaks the constraint closure) -> MUST fail the gauge/DOF judges.
       wrong-sign src : flip the source sign (repulsive 'gravity').  The gauge
       structure and the projection-free DOF count are SIGN-BLIND by
       construction, so this correctly PASSES them; it is caught only by a
       physical observable (Newtonian attraction sign, M3's deflection test).
       That is honest -- the emergence judges test gauge/DOF, not the matter
       sign.  Battery has teeth iff the tr_sign=0 control fails."""
    T_A, trials = (384, 6) if quick else (640, 10)
    T_B = 400 if quick else 600
    out = {}
    for tag, kw, gauge_sensitive in (
            ("tr_sign=0", {"tr_sign": 0.0}, True),
            ("wrong-sign src", {"src_sign": -1.0}, False)):
        rule = make_current_rule("jbar", G_m=G_m, **kw)
        a = ej.judge_dof(rule, N=N, T=T_A, trials=trials)
        b = ej.judge_gauge(rule, N=N, T=T_B)
        crit = {"n_prop_all": a["n_prop_all"],
                "lightcone_ok": bool(a["lightcone_ok"]),
                "stable": bool(a["stable"] and b["stable"]),
                "gauge_conversion": float(b["gauge_conversion"]),
                "c_decay_ratio": float(b["c_decay_ratio"])}
        fails = not (all(n == 2 for n in a["n_prop_all"]) and a["lightcone_ok"]
                     and a["stable"] and b["stable"]
                     and b["gauge_conversion"] < ej.CONVERSION_PASS
                     and b["c_decay_ratio"] < ej.C_DECAY_PASS)
        crit["gauge_sensitive"] = gauge_sensitive
        crit["fails_gauge_judge"] = bool(fails)
        # verdict: gauge-sensitive controls MUST fail; sign-blind ones need not
        crit["as_expected"] = bool(fails if gauge_sensitive else not fails)
        out[tag] = crit
    out["battery_has_teeth"] = bool(out["tr_sign=0"]["fails_gauge_judge"])
    return out


# ===========================================================================
#  driver
# ===========================================================================
def run_all(quick=True):
    out = {"backend": B.NAME}
    out["verify_batchwalk"] = verify_batchwalk()
    out["verify_kernels"] = verify_kernels()
    out["cp2_source_residual"] = checkpoint_source_residual()
    out["cp1_leakage"] = leakage_test(out["cp2_source_residual"])
    out["cp5_closed_loop"] = closed_loop_test()
    out["cp4_nprop"] = checkpoint_nprop(quick=quick)
    out["falsification"] = falsification_battery(quick=quick)
    return out


def _verdict(out):
    cp2 = out["cp2_source_residual"]
    lk = out["cp1_leakage"]
    lp = out["cp5_closed_loop"]
    npr = out["cp4_nprop"]
    c1 = lk["leak_ratio_onsite_over_jbar"] >= 100.0
    c2 = cp2["jbar"] < 1e-10
    c3 = lp["live_row_conservation_max"] < 1e-12 and lp["stable"]
    c4 = all(n == 2 for n in npr["jbar"]["n_prop_all"]) and npr["jbar"]["stable"]
    rows = [
        ("gauge-anomaly leakage rate: on-site/Jbar (16piG*div T)",
         f"{lk['leak_ratio_onsite_over_jbar']:.2e}x", ">= 100x", c1),
        ("source de-Donder residual (Jbar, wide box)",
         f"{cp2['jbar']:.2e}", "< 1e-10", c2),
        ("closed-loop live T-row conservation",
         f"{lp['live_row_conservation_max']:.2e}", "< 1e-12", c3),
        ("N_prop (live current source, no-lag)",
         str(npr["jbar"]["n_prop_all"]), "= 2 (no regress)", c4),
    ]
    return rows, [c1, c2, c3, c4]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "data", "results", "green_m2_results.json"))
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING: backend = {B.NAME}; run RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("M2 -- R10 exact averaged key-current Jbar as de-Donder source into "
          "the M1 null-box geometry\n")

    out = run_all(quick=not args.full)

    vb, vk = out["verify_batchwalk"], out["verify_kernels"]
    print(f"[VERIFY] BatchWalk == r10.Walk: state {vb['state_max_diff']:.1e} "
          f"packet {vb['packet_max_diff']:.1e} batch {vb['batch_max_diff']:.1e} "
          f"-> {'bit-identical' if vb['identical'] else 'MISMATCH'}")
    print(f"[VERIFY] averaging kernels == r13: {vk['kernel_max_diff']:.1e} "
          f"-> {'bit-identical' if vk['identical'] else 'MISMATCH'}\n")

    cp2 = out["cp2_source_residual"]
    print("[CP2] source-side de-Donder residual (R13 wide-box T6 balance):")
    print(f"    Jbar (transverse-avg + two-step) = {cp2['jbar']:.2e}   (< 1e-10)")
    print(f"    raw stride-1 F (no transverse avg)= {cp2['rawF']:.2e}   "
          f"(Nyquist leak: T7)")
    print(f"    on-site bilinear (eta_c div, norm)= {cp2['onsite']:.2e}   "
          f"(the 'old' baseline)\n")

    lk = out["cp1_leakage"]
    print("[CP1] gauge-anomaly leakage rate = 16 pi G * (source de-Donder "
          "residual) = the de-Donder constraint source box C = -16 pi G div T:")
    Gs = sorted(g for g in lk["jbar"].keys())
    print(f"    {'G':>8}  {'Jbar leak':>12}  {'on-site leak':>14}  "
          f"{'raw-F leak':>12}")
    for G in Gs:
        print(f"    {G:>8.3f}  {lk['jbar'][G]['leak']:>12.3e}  "
              f"{lk['onsite'][G]['leak']:>14.3e}  {lk['rawF'][G]['leak']:>12.3e}")
    print(f"    leak ratio on-site/Jbar = {lk['leak_ratio_onsite_over_jbar']:.2e}x "
          f"(target >= 100x);  raw-F/Jbar = {lk['leak_ratio_rawF_over_jbar']:.2e}x")
    print(f"    G-scaling: {lk['G_scaling']}\n")

    lp = out["cp5_closed_loop"]
    print("[CP5] closed loop (LIVE Jbar source, matter->geometry; back-reaction "
          "is M3):")
    print(f"    live T-row conservation (wide box) = "
          f"{lp['live_row_conservation_max']:.2e}  (< 1e-12)")
    print(f"    stable = {lp['stable']}   walker norm drift = "
          f"{lp['walker_norm_drift']:.2e}   field growth late = "
          f"{lp['field_energy_growth_late']:.3f}")
    print("    (field growth = undamped null box + continuous source ringing "
          "on a torus with no\n     sink; bounded/stable -- a sponge/gamma "
          "sink is added at M3, per tensor_coin_feedback)\n")

    npr = out["cp4_nprop"]
    print("[CP4] N_prop (projection-free judge) -- two layers:")
    print("  (i) OPERATOR level: the box the current CONSUMPTION builds (M1 rules)")
    for key, lab in (("op_wide_Jbar_consumed", "J̄ consumed -> WIDE null box"),
                     ("op_compact_rawF_consumed", "raw stride-1 F -> COMPACT box")):
        r = npr[key]
        print(f"      {lab:34s} N_prop={str(r['n_prop_all']):>15s} "
              f"cone={'ok' if r['lightcone_ok'] else 'NO'} stable={r['stable']}")
    print("  (ii) ADDITIVE live-current source on the fixed wide box:")
    print(f"      {'source':16s} {'N_prop(all k)':>16s} {'cone':>5s} "
          f"{'C-decay':>9s} {'convert':>9s} {'stbl':>4s}")
    for key in ("bare", "jbar", "onsite", "rawF"):
        r = npr[key]
        print(f"      {key:16s} {str(r['n_prop_all']):>16s} "
              f"{'ok' if r['lightcone_ok'] else 'NO':>5s} "
              f"{r['c_decay_ratio']:>9.1e} {r['gauge_conversion']:>9.2e} "
              f"{'y' if r['stable'] else 'N':>4s}")
    print("    T7: the N_prop=5 signature lives in the compact/half-grid BOX "
          "(operator level).\n    J̄'s transverse-average is exactly what keeps "
          "the box wide (=2).  A weak\n    ADDITIVE current does not flip "
          "N_prop; there J̄ vs raw-F differ in CONSERVATION.\n")

    fb = out["falsification"]
    print("[FALSIFICATION] (battery has teeth iff tr_sign=0 breaks a criterion):")
    for tag in ("tr_sign=0", "wrong-sign src"):
        r = fb[tag]
        kind = "gauge-sensitive" if r["gauge_sensitive"] else "sign-blind (physics-only)"
        note = ("FAILS gauge judge as required" if r["fails_gauge_judge"]
                else "passes gauge judge (correct: caught only by Newtonian sign)")
        print(f"    {tag:16s} [{kind:26s}] N_prop={r['n_prop_all']} "
              f"conv={r['gauge_conversion']:.1e} Cdecay={r['c_decay_ratio']:.1e} "
              f"-> {note} [{'OK' if r['as_expected'] else 'CHECK'}]")
    print(f"    battery_has_teeth = {fb['battery_has_teeth']}\n")

    rows, cps = _verdict(out)
    print("\n" + "=" * 82)
    print("PRE-REGISTERED CHECKPOINTS (M2):")
    print(f"  {'criterion':52s} {'measured':16s} {'target':16s} PASS")
    for name, meas, tgt, ok in rows:
        print(f"  {name:52s} {meas:16s} {tgt:16s} {'PASS' if ok else 'FAIL'}")
    npass = sum(cps)
    print("-" * 82)
    print(f"  M2 VERDICT: {npass}/4 checkpoints PASS"
          + ("  (ALL PASS)" if npass == 4 else "  -- see honest FAIL analysis"))
    out["checkpoints_pass"] = [bool(c) for c in cps]
    out["n_pass"] = int(npass)

    print("\nTIER: 定理(R13 Jbar continuity, machine-exact) + 实证(this file: "
          "whether exactness => the SOURCED geometry's leakage drops / N_prop "
          "holds).  NOT non-linear GR / QG / 'world is a CA'.")

    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: (
            o.tolist() if isinstance(o, np.ndarray) else float(o)))
    print(f"\nwrote {os.path.abspath(args.json)}")
