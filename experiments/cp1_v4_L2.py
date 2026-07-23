"""cp1_v4_L2 -- CP1-v4 assembly ladder, LEVEL 2 (lane B): + Z4c damping.

WHAT L2 IS (per 主线-CP1v4-装配阶梯与证伪炮组.md §三c, the authoritative spec):
the frozen L1 construction (walk kernel + K_placed staggered constraint,
cp1_v4_L1.py, sha256 4dad03be... -- asserted at import, file NOT modified)
with the exact 0nu slave REPLACED by Z4c constraint damping from the
pre-written module cp1_v4_damping.py (used verbatim: z4c_step/
make_z4c_stepper/ConstraintOp/spectral_calibrate/z_sector_certificate/
placement_gate/rate_gate).  No source, no sponge (L3-L4).

CONSTRUCTION (all constraint stencils are FROZEN L1 code objects):

  * walk    : gw.geom_walk_all, theta_g = theta_matter = pi/3 (same import
              as L1 -- shared-cone guarantee unchanged).
  * damping : module z4c_step, comoving carrier = THE SAME walk kernel
              applied to the auxiliary Z field (R22 hard requirement /
              falsification cannon "static carrier").
  * Kop     : ONE ConstraintOp (enforce == measure single instance,
              probe-asserted at stepper construction) stacking three blocks,
              each row built by CALLING the frozen L1 functions:

      block W (rows 0-3, "true constraint, W-realized time stencils"):
        the L1 slave's own centering with the previous slice realized by the
        walk itself (R20 fix #1: "D0 via the walk, per-OFFSET stencils;
        hbar_00 forward, hbar_0i backward"); y = W^dag x:
          rows i : K_placed(y, x, .)[1:4]     (h0i backward, centered at x)
          row  0 : K_placed(., y, x)[0]       (h00 forward, centered at t-1/2)
        On a walk branch e^{-iw} this block equals the FULL 3-slice placed
        constraint symbol at the walk's own frequency (bridge-checked to
        1e-13): its kernel is exactly L1's oracle kernel ker K(w_walk,k).
      block A (rows 4-7, "static Jacobian, R18 real-space calculus"):
          K_placed(0, x, 0)  -- the as-assembled analog of R18's jacobian_C
        (time slots -> constant 1/c).  This is the operator family the whole
        R16/R18/R20/R22 damping line was calibrated on; gauge is NOT in its
        kernel (R18 H3: gauge suppression EXPECTED, declared, not DOF loss).
      block T (row 8, "trace gauge-fixing row", DECLARED assembly choice):
          tr_eta hbar = -h00 + h11 + h22 + h33   (algebraic, local, all four
        diagonal components live on the SAME integer sublattice -- zero
        placement risk; |tr@TT| = 0 identically).

  WHY THE STACK (design theorem, verified in pre-flight and part B below):
  no SINGLE de-Donder-derived operator can pass the L2 gate table.
    - damping with block W alone: fixed set = ker K(w_walk) = TT + gauge;
      on-shell gauge waves survive -> stock count stays 5-6 -> G5 fails.
    - damping with block A alone: fixed set = ker A != ker K; surviving
      content violates the TRUE constraint -> relC never floors -> G1 fails.
    - blocks W+A: fixed set = ker W  ^ ker A = TT + one residual
      transverse-trace mode; that mode is PURE placed-gauge (lstsq residual
      vs the gauge block ~ 5e-16, placed-Riemann dark ~ 7e-16) but is bright
      to any full-angle reading -> stock gives 3 at oblique k -> G5 fails.
    - the residual mode is transverse: EVERY de-Donder row (divergence type)
      is blind to it.  Killing it requires one explicit gauge-fixing row --
      block T (the lattice analog of completing harmonic gauge to TT gauge;
      in NR language: the gauge sector is fixed separately from constraint
      damping).  With W+A+T the fixed set is EXACTLY TT at every k (kernel
      principal angles vs TT = 1 to machine precision, incl. (2,2,2)).
  DECLARED CONSEQUENCE (deviation from L1 handoff expectation 8.4): the
  damping fixed set is SMALLER than ker K, so the oblique/body-diagonal
  Trotter excess (in ker K but not in ker A) is damped away: (2,2,2) is
  predicted N_prop = 2 in the damped assembly.  Reported as data (no gate;
  M3 card unchanged).

CALIBRATION (no numbers inherited from R22/self-test -- re-derived from the
as-assembled operator): per (k, branch) the stepper block-diagonalizes
exactly (spatial rolls are spinor-diagonal, W-terms are branch-diagonal,
carrier = same walk), so the module theory applies verbatim with
K = K_branch(k, e^{-iw}).  sigma^2 collected over the FULL 16^3 BZ x both
branches -> spectral_calibrate (margin 4%, mu at plateau low end for
stiffness headroom, R22 §4) -> (mu_z, kappa1, rho) reported + plateau.

MEASUREMENT: L1's own frozen pipelines (count_at_k = placed-kappa judge;
stock_count_at_k = stock reference).  G5 operationalization (DECLARED here,
before the gates are evaluated):
  the gate compares the two CALCULI (placed half-angle vs stock full-angle
  ej machinery).  The stock reference function reads Re() of the raw STORED
  series without the colfac un-shift; on staggered storage at oblique k that
  reading splits even a PURE TT wave into >2 directions (synthetic pure-TT
  certificate, part D: stock-verbatim on noise-free TT data gives 3 at
  (2,2,0), 4 at (2,2,2)).  G5 is therefore evaluated on the stock CALCULUS
  applied to the physically-read series (colfac un-shift = unit phase,
  lossless -- R19 §5.5 "readout on the physical amplitude side"), with the
  verbatim-stock numbers ALSO reported and their oblique excess certified
  as the pure-TT reading artifact.  At axial k the two readings coincide
  and both must give 2.

GATES (all simultaneous, fp64; FAIL => stop at L2, attribution matrix):
  G1  raw-IC relC -> machine floor; measured rate == spectral prediction
      (tail-rate calculus distinguishes floor from slow decay, R20 fix 5)
  G2  TT preserved: damped evolution keeps TT amplitude = 1 (< 1e-10 drift;
      structural protection expected at 1e-14: |K_stack@TT| = 0)
  G3  gauge suppression recorded and EXPECTED (R18 H3 reading; gauge decay
      rate == spectral prediction; not counted as DOF loss)
  G4  N_prop = 2 (placed-kappa judge) at the 4 gate k, Z sector explicitly
      deducted via z_sector_certificate (unit modes = dim ker K, zero Z
      content on the unit circle, Z radius = sqrt(1-kappa1))
  G5  two-calculus convergence (promoted formal gate; see above)
  G6  Jordan mode killed: h00 secular ramp gone (raw IC); spectral pipeline
      WITHOUT the linear detrend gives identical counts (detrend removable)
  G7  stability: T >= 1024, matter-sector tail norm drift < 1e-10, Z -> 0

FALSIFICATION CANNONS (each must break >= 1 gate):
  C1  no damping (module off, L1 exact slave restored = L1 run-A config):
      Jordan mode MUST revive (h00 ramp returns)          -> breaks G6
  C2  static Z carrier (R22 ablation; most-unstable k from the full-BZ
      spectral scan, module red line)                     -> breaks G7/G1
  C3  lagged damping (Z fed with the PREVIOUS step's C -- R20 hprev disease;
      hand-injected: the module API cannot express it)    -> breaks G1
  C4  L1-F2 regression: integer-grid central template (damping must NOT
      rescue the placement disease)                       -> breaks G2/G4
  C0  count teeth: free walk, damping off -> N_prop = 6 reference

Run:  RULESPACE_BACKEND=numpy .venv/bin/python cp1_v4_L2.py
      (~15-25 min; writes cp1_v4_L2_results.json with sha256 of this file,
       of the frozen cp1_v4_L1.py and of cp1_v4_damping.py)
"""
import hashlib
import json
import math
import os
import time

import numpy as np

import cp1_v4_L1 as L1                       # FROZEN (hash asserted below)
from cp1_v4_damping import (ConstraintOp, make_z4c_stepper, spectral_calibrate,
                            z_sector_certificate, z4c_block_moduli,
                            placement_gate, rate_gate, probe_adjoint_assert)
import r15_walk_dedonder as r15
from rulespace_gpu import backend as B
from rulespace_gpu import green_one_walk as gw
from rulespace_gpu import emergence_judge as ej
from rulespace_gpu import tensor_coin_feedback as tcf

DIR = os.path.dirname(os.path.abspath(__file__))
FROZEN_L1_SHA = "4dad03be4319da896f485d954f0efc97bc0a6f781700f97e3e8120178a5c6035"


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


_l1sha = _sha(os.path.join(DIR, "cp1_v4_L1.py"))
assert _l1sha == FROZEN_L1_SHA, f"cp1_v4_L1.py hash mismatch: {_l1sha}"

TH = L1.TH0                                  # pi/3, shared cone
C = L1.C_CONE                                # 0.5
PK, OFFSET = L1.PK, L1.OFFSET
SEED_A, SEED_B, SEED_CANNON = 1, 2, 3        # L1 seeds reused (pre-registered)
SV_THRESH = L1.SV_THRESH
KM_GATE = list(L1.KM_GATE)                   # 4 gate k
KM_DIAG = L1.KM_DIAG                         # (2,2,2) reference column
KM_ALL = list(L1.KM_ALL)
KM_ISO = list(L1.KM_ISO)
T_MAIN = 1536
DIAG10 = [PK[(0, 0)], PK[(1, 1)], PK[(2, 2)], PK[(3, 3)]]
TRW = np.array([-1.0, 1.0, 1.0, 1.0])        # eta-trace weights on DIAG10


# ===========================================================================
#  PART A. construction: walk inverse + the stacked ConstraintOp
# ===========================================================================
def _axis_sandwich_inv(psi, th, ax3, W):
    """exact inverse of tcf._axis_sandwich (orient=1): unitary reversal."""
    psi = psi @ W.T
    p1 = np.roll(psi[..., 1], 1, axis=ax3)
    psi = np.stack([psi[..., 0], p1], axis=-1)
    psi = tcf._coin(psi, th)
    p0 = np.roll(psi[..., 0], -1, axis=ax3)
    psi = np.stack([p0, psi[..., 1]], axis=-1)
    psi = tcf._coin(psi, -th)
    psi = psi @ W.conj()
    return psi


def walk_fwd(chi, th=TH):
    return gw.geom_walk_all(chi, th, th, th, th)


def walk_inv(chi, th=TH):
    Wx, Wy, Wz = tcf.axis_frames(th)
    chi = _axis_sandwich_inv(chi, th, -1, Wz)
    chi = _axis_sandwich_inv(chi, th, -2, Wy)
    chi = _axis_sandwich_inv(chi, th, -3, Wx)
    return chi


def D_adj(g, mu, comp):
    """adjoint of the frozen L1.D_dict (integer-roll dictionary difference)."""
    ax = mu - 4
    if OFFSET[comp][mu]:
        return g - np.roll(g, -1, axis=ax)        # (backward diff)^dag
    return np.roll(g, 1, axis=ax) - g             # (forward diff)^dag


def K_apply(xx, c=C):
    """the stacked measurement: xx (10,...,N,N,N,2) -> C (9,...,N,N,N,2).
    Rows 0-3 = block W (frozen K_placed, L1 centering, prev slice = W^dag x);
    rows 4-7 = block A (frozen K_placed, zero history = static Jacobian);
    row  8   = block T (eta-trace, algebraic)."""
    y = walk_inv(xx)
    Cout = np.zeros((9,) + xx.shape[1:], complex)
    for s in range(2):
        xs = np.ascontiguousarray(xx[..., s])
        ys = np.ascontiguousarray(y[..., s])
        Z = np.zeros_like(xs)
        Cout[1:4, ..., s] = L1.K_placed(ys, xs, Z, c)[1:4]
        Cout[0, ..., s] = L1.K_placed(Z, ys, xs, c)[0]
        Cout[4:8, ..., s] = L1.K_placed(Z, xs, Z, c)
        Cout[8, ..., s] = (-xs[DIAG10[0]] + xs[DIAG10[1]] + xs[DIAG10[2]]
                           + xs[DIAG10[3]])
    return Cout


def K_adjoint(Cin, c=C):
    """exact adjoint of K_apply (probe-asserted by the damping module)."""
    sh = (10,) + Cin.shape[1:]
    out = np.zeros(sh, complex)
    wacc = np.zeros(sh, complex)                  # y-slot terms, walked once
    for s in range(2):
        u = Cin[0:4, ..., s]
        v = Cin[4:8, ..., s]
        w9 = Cin[8, ..., s]
        for i in (1, 2, 3):
            for mu in (1, 2, 3):
                cmp = PK[(mu, i)]
                out[cmp, ..., s] += D_adj(u[i], mu, cmp) + D_adj(v[i], mu, cmp)
            c0i = PK[(0, i)]
            out[c0i, ..., s] += -(u[i] + v[i]) / c
            wacc[c0i, ..., s] += u[i] / c
        c00 = PK[(0, 0)]
        out[c00, ..., s] += -u[0] / c + v[0] / c
        wacc[c00, ..., s] += u[0] / c
        for i in (1, 2, 3):
            cmp = PK[(i, 0)]
            wacc[cmp, ..., s] += D_adj(u[0], i, cmp)
            out[cmp, ..., s] += D_adj(v[0], i, cmp)
        for j, cmp in enumerate(DIAG10):
            out[cmp, ..., s] += TRW[j] * w9
    return out + walk_fwd(wacc)


KOP = ConstraintOp(K_apply, K_adjoint, name="K_stack[W;A;T]")


# --- F2/C4 flavor: integer-grid central template (frozen L1.K_central) -----
def Kc_apply(xx, c=C):
    y = walk_inv(xx)
    y2 = walk_inv(y)
    Cout = np.zeros((9,) + xx.shape[1:], complex)
    for s in range(2):
        xs = np.ascontiguousarray(xx[..., s])
        ys = np.ascontiguousarray(y[..., s])
        y2s = np.ascontiguousarray(y2[..., s])
        Z = np.zeros_like(xs)
        Cout[0:4, ..., s] = L1.K_central(y2s, ys, xs, c)
        Cout[4:8, ..., s] = L1.K_central(Z, xs, Z, c)
        Cout[8, ..., s] = (-xs[DIAG10[0]] + xs[DIAG10[1]] + xs[DIAG10[2]]
                           + xs[DIAG10[3]])
    return Cout


def _cent_adj(g, ax):
    return 0.5 * (np.roll(g, 1, axis=ax) - np.roll(g, -1, axis=ax))


def Kc_adjoint(Cin, c=C):
    sh = (10,) + Cin.shape[1:]
    out = np.zeros(sh, complex)
    wacc1 = np.zeros(sh, complex)                 # y-slot, walked once
    wacc2 = np.zeros(sh, complex)                 # y2-slot, walked twice
    for s in range(2):
        u = Cin[0:4, ..., s]
        v = Cin[4:8, ..., s]
        w9 = Cin[8, ..., s]
        for nu in range(4):
            c0 = PK[(0, nu)]
            out[c0, ..., s] += -0.5 * u[nu] / c
            wacc2[c0, ..., s] += 0.5 * u[nu] / c
            for mu in (1, 2, 3):
                cmp = PK[(mu, nu)]
                wacc1[cmp, ..., s] += _cent_adj(u[nu], mu - 4)
                out[cmp, ..., s] += _cent_adj(v[nu], mu - 4)
        for j, cmp in enumerate(DIAG10):
            out[cmp, ..., s] += TRW[j] * w9
    return out + walk_fwd(wacc1 + walk_fwd(wacc2))


KOP_CENTRAL = ConstraintOp(Kc_apply, Kc_adjoint, name="K_stack_central")


# ===========================================================================
#  PART B. symbols: walk 2x2, per-(k,branch) stacked matrix, BZ calibration
# ===========================================================================
def walk_symbol(kl, th=TH):
    Wx, Wy, Wz = tcf.axis_frames(th)
    U = np.eye(2, dtype=complex)
    for kc, W in ((kl[0], Wx), (kl[1], Wy), (kl[2], Wz)):
        D1 = np.diag([np.exp(-1j * kc), 1.0])
        D2 = np.diag([1.0, np.exp(1j * kc)])
        Uax = W.conj().T @ D2 @ tcf._coin_mat(-th) @ D1 @ tcf._coin_mat(th) @ W
        U = Uax @ U
    return U


def d_sym(kl, mu, comp):
    kc = kl[mu - 1]
    if OFFSET[comp][mu]:
        return 1.0 - np.exp(-1j * kc)
    return np.exp(1j * kc) - 1.0


def K_branch(kl, lam, c=C):
    """stored-frame 9x10 stacked symbol on a walk branch (eigenvalue lam)."""
    lb = np.conj(lam)
    K = np.zeros((9, 10), complex)
    tf = (1.0 - lb) / c
    for i in (1, 2, 3):
        for mu in (1, 2, 3):
            K[i, PK[(mu, i)]] += d_sym(kl, mu, PK[(mu, i)])
            K[4 + i, PK[(mu, i)]] += d_sym(kl, mu, PK[(mu, i)])
        K[i, PK[(0, i)]] += -tf
        K[4 + i, PK[(0, i)]] += -1.0 / c
    for i in (1, 2, 3):
        K[0, PK[(i, 0)]] += lb * d_sym(kl, i, PK[(i, 0)])
        K[4, PK[(i, 0)]] += d_sym(kl, i, PK[(i, 0)])
    K[0, PK[(0, 0)]] += -tf
    K[4, PK[(0, 0)]] += 1.0 / c
    for j, cmp in enumerate(DIAG10):
        K[8, cmp] = TRW[j]
    return K


def bridge_check(nvec, N=16):
    """real-space K_apply vs symbol K_branch, both branches, all 10 comps."""
    klat = np.array(nvec, float) * (2 * np.pi / N)
    ev, V = np.linalg.eig(walk_symbol(klat))
    ph = L1.plane(klat, N)
    proj = np.conj(ph) / N ** 3
    worst = 0.0
    for b in range(2):
        xi = V[:, b] / np.linalg.norm(V[:, b])
        Kb = K_branch(klat, ev[b])
        for comp in range(10):
            xx = np.zeros((10, N, N, N, 2), complex)
            xx[comp] = ph[..., None] * xi[None, None, None, :]
            amp = np.einsum("xyz,rxyzs,s->r", proj, K_apply(xx), np.conj(xi))
            worst = max(worst, float(np.abs(amp - Kb[:, comp]).max()))
    return worst


def bz_calibrate(N=16, margin=0.04, mu_choice="low"):
    """sigma^2 over the FULL BZ x both branches of the as-assembled stack."""
    s2_all, om_all = [], []
    for a in range(N):
        for b in range(N):
            for d in range(N):
                if a == b == d == 0:
                    continue
                klat = 2 * np.pi * np.array([a, b, d]) / N
                for lam in np.linalg.eigvals(walk_symbol(klat)):
                    s2 = np.linalg.svd(K_branch(klat, lam),
                                       compute_uv=False) ** 2
                    s2 = s2[s2 > 1e-12]
                    s2_all.append(s2)
                    om_all.append(np.full(s2.size, -np.angle(lam)))
    s2_all = np.concatenate(s2_all)
    om_all = np.concatenate(om_all)
    cal = spectral_calibrate(s2_all, margin=margin, mu_choice=mu_choice)
    cal["rho_discrete_bz"] = float(
        z4c_block_moduli(cal["mu_z"], cal["kappa1"], s2_all).max())
    cal["rho_static_carrier_at_op"] = float(
        z4c_block_moduli(cal["mu_z"], cal["kappa1"], s2_all,
                         phase=om_all).max())
    return cal, s2_all, om_all


def kernel_certificate(nvec, N=16):
    """per gate k: dim ker(K_branch) == 2, ker == TT (principal angles),
    |K@TT| machine zero, t-trace purity (pure placed-gauge) certificate."""
    klat = np.array(nvec, float) * (2 * np.pi / N)
    kl4, wq, xi, ph, proj = L1.onshell_mode(nvec, N)
    out = {"nvec": list(nvec), "w_walk": float(wq)}
    k4 = np.array([-wq, klat[0], klat[1], klat[2]])
    kap = L1.kappa_of(-wq, klat)
    cf = L1.colfac(k4)
    Kb = K_branch(klat, np.exp(-1j * wq))
    s = np.linalg.svd(Kb, compute_uv=False)
    rank = int(np.sum(s > 1e-10 * s[0]))
    out["dim_ker"] = 10 - rank
    Vh = np.linalg.svd(Kb)[2]
    kerp = Vh[rank:].conj().T * np.conj(cf)[:, None]
    TTp = r15.tt_basis(kap)
    Qk, _ = np.linalg.qr(kerp)
    Qt, _ = np.linalg.qr(TTp)
    ang = np.linalg.svd(Qk.conj().T @ Qt, compute_uv=False)
    out["ker_vs_TT_principal_cos_min"] = float(ang.min()) if ang.size else 0.0
    out["K_at_TT"] = float(np.abs(Kb @ (TTp * cf[:, None])).max())
    G = r15.gauge_block(kap)
    out["K_at_gauge"] = float(np.abs(
        Kb @ ((G / np.linalg.norm(G, axis=0)) * cf[:, None])).max())
    # the direction the trace row ACTUALLY kills: 3rd kernel direction of
    # the [W;A] sub-stack (rows 0-7), orthogonalized against TT -- this is
    # the transverse-trace residual mode at THIS k (not a hardcoded rep).
    K8 = Kb[:8]
    s8 = np.linalg.svd(K8, compute_uv=False)
    rank8 = int(np.sum(s8 > 1e-10 * s8[0]))
    ker8p = np.linalg.svd(K8)[2][rank8:].conj().T * np.conj(cf)[:, None]
    Qt, _ = np.linalg.qr(TTp)
    Rm = ker8p - Qt @ (Qt.conj().T @ ker8p)
    sR, uR = np.linalg.svd(Rm, compute_uv=False), np.linalg.svd(Rm)[0]
    out["WA_substack_dim_ker"] = 10 - rank8
    out["ttrace_residual_dims"] = int(np.sum(sR > 1e-8))
    v = uR[:, 0]                                # the killed residual mode
    cg, *_ = np.linalg.lstsq(G, v, rcond=None)
    out["ttrace_gauge_purity_resid"] = float(np.linalg.norm(G @ cg - v))
    out["ttrace_placed_riemann"] = float(np.linalg.norm(
        L1.riemann_sym(kap, v)) / (np.linalg.norm(
            L1.riemann_sym(kap, TTp[:, 0])) + 1e-300))
    out["ttrace_eta_trace"] = float(abs(-v[PK[(0, 0)]] + v[PK[(1, 1)]]
                                        + v[PK[(2, 2)]] + v[PK[(3, 3)]]))
    return out


# ===========================================================================
#  PART C. steppers, drivers, measurement
# ===========================================================================
def make_L2_stepper(cal, Kop=KOP, carrier="walk", probe=True):
    car = walk_fwd if carrier == "walk" else (lambda z: z)
    probe_chi = None
    if probe:
        rngp = np.random.default_rng(99)
        probe_chi = (rngp.standard_normal((10, 6, 6, 6, 2))
                     + 1j * rngp.standard_normal((10, 6, 6, 6, 2)))
    return make_z4c_stepper(walk_fwd, car, Kop, cal["mu_z"], cal["kappa1"],
                            probe_chi=probe_chi)


def evolve_record_L2(chi, kinfo, T, step, monitor=True):
    """evolve with the damped stepper; record stored-frame spinor-0 series;
    monitor the TRUE 3-slice constraint with the FROZEN K_placed on the
    actually recorded slices (independent of the stepper's internal meter)."""
    trials = chi.shape[1]
    Zf = np.zeros((9,) + chi.shape[1:], complex)
    rec = np.zeros((T, trials, len(kinfo), 10), complex)
    relC, h00r, rmsf, znorm = [], [], [], []
    buf = [[], []]
    for t in range(T):
        chi, Zf = step(chi, Zf)
        H0 = np.ascontiguousarray(chi[..., 0])
        for ki, (kl, wq, xi, ph, proj) in enumerate(kinfo):
            rec[t, :, ki, :] = np.einsum("xyz,crxyz->rc", proj, H0)
        if monitor:
            worst, measured = 0.0, False
            for s in range(2):
                buf[s].append(np.ascontiguousarray(chi[..., s]))
                if len(buf[s]) > 3:
                    buf[s].pop(0)
                if len(buf[s]) == 3:
                    Cr = L1.K_placed(buf[s][0], buf[s][1], buf[s][2])
                    hn = float(np.sqrt(np.mean(np.abs(buf[s][1]) ** 2)))
                    worst = max(worst, float(np.sqrt(
                        np.mean(np.abs(Cr) ** 2))) / (hn + 1e-300))
                    measured = True
            if measured:                       # no zero-padding before the
                relC.append(worst)             # first full slice triple
        h00r.append(float(np.sqrt(np.mean(np.abs(chi[PK[(0, 0)], ..., 0]) ** 2))))
        rmsf.append(float(np.sqrt(np.mean(np.abs(chi) ** 2))))
        znorm.append(float(np.sqrt(np.mean(np.abs(Zf) ** 2))))
    mon = {"h00_rms_first": h00r[2], "h00_rms_last": h00r[-1],
           "rms_full_first": rmsf[0], "rms_full_last": rmsf[-1],
           "rms_tail_drift": float(abs(rmsf[-1] / (rmsf[3 * len(rmsf) // 4]
                                                   + 1e-300) - 1.0)),
           "Z_rms_last": znorm[-1], "Z_rms_max": float(max(znorm))}
    if monitor and relC:
        finite = all(np.isfinite(v) for v in relC)
        tail = relC[-9:]
        mon.update({
            "relC_init": float(relC[0]), "relC_max": float(max(relC)),
            "relC_last": float(relC[-1]),
            "relC_tail_rate": float((tail[-1] / (tail[0] + 1e-300))
                                    ** (1.0 / max(1, len(tail) - 1))),
            "relC_overflow": bool(not finite),
            "relC_checkpoints": {str(t): float(relC[t])
                                 for t in (0, 20, 60, 100, 200, 400, 800,
                                           len(relC) - 1) if t < len(relC)}})
        mon["relC_series"] = [float(v) for v in relC]
    return rec, mon, chi


def stock_physical_count(rec_k, kl, w_walk, c2=C ** 2, w_max=np.pi / 2):
    """G5 operationalization: the STOCK calculus (ej.trace_reverse_c +
    ej.riemann_series_k, full-angle) applied to the physically-read series
    (colfac un-shift, a lossless unit phase).  Derived from the frozen
    L1.stock_count_at_k (sha256 4dad03be...), reading changed ONLY."""
    T, trials, _ = rec_k.shape
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    seg_c = L1.detrend(rec_k[T0:])
    segw = (seg_c * win[:, None, None])[2:-2]
    freqs = 2 * np.pi * np.fft.fftfreq(W - 4)
    sel2 = (np.abs(freqs) > max(0.05, 4 * np.pi / (W - 4))) \
        & (np.abs(freqs) <= w_max)
    F = np.fft.fft(segw, axis=0)
    P2 = np.sum(np.abs(F) ** 2, axis=(1, 2))
    if float(P2[sel2].sum()) < 1e-18:
        return {"n_prop": 0, "no_peak": True}
    pk = int(np.argmax(np.where(sel2, P2, 0.0)))
    ws = math.copysign(w_walk, freqs[pk])
    cf = L1.colfac(np.array([ws, kl[0], kl[1], kl[2]]))
    seg = np.real(seg_c * np.conj(cf)[None, None, :])
    sel = (freqs > max(0.05, 4 * np.pi / (W - 4))) & (freqs <= w_max)
    rows, powsp = [], None
    for r in range(trials):
        Hh = ej.trace_reverse_c(seg[:, r, :], c2)
        Rf = ej.riemann_series_k(ej.packed_to_44(Hh), kl)
        Fr = np.fft.fft(Rf * win[2:-2, None], axis=0)
        Pr = np.sum(np.abs(Fr) ** 2, axis=1)
        powsp = Pr if powsp is None else powsp + Pr
        rows.append(Fr)
    pk1 = int(np.argmax(np.where(sel, powsp, 0.0)))
    M = np.array([r[pk1] for r in rows])
    sv = np.linalg.svd(M, compute_uv=False)
    svn = (sv / (sv[0] + 1e-300)).tolist()
    return {"w_peak": float(freqs[pk1]),
            "n_prop": int(np.sum(np.array(svn) > SV_THRESH)),
            "sv": [float(v) for v in svn[:8]]}


def count_nodetrend(rec_k, kl, wq):
    """G6: L1.count_at_k with the declared linear detrend REMOVED at runtime
    (temporary rebind of the module global; cp1_v4_L1.py is not modified)."""
    orig = L1.detrend
    L1.detrend = lambda seg: seg
    try:
        e = L1.count_at_k(rec_k, kl, wq)
        st = L1.stock_count_at_k(rec_k, kl)
    finally:
        L1.detrend = orig
    return e, st


def tt_artifact_certificate(rec_k, kl, w_walk, T):
    """G5 certificate at oblique k: extract the two-branch peak amplitudes,
    project onto TT (physical frame; residual recorded), REBUILD a pure-TT
    synthetic stored series from the projections only, and compare the
    verbatim-stock SV spectrum with the measured one.  If they match, the
    verbatim-stock excess is generated entirely by TT content misread by
    the no-unshift Re() convention."""
    trials = rec_k.shape[1]
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    seg = (L1.detrend(rec_k[T0:]) * win[:, None, None])[2:-2]
    freqs = 2 * np.pi * np.fft.fftfreq(W - 4)
    sel = (np.abs(freqs) > max(0.05, 4 * np.pi / (W - 4))) \
        & (np.abs(freqs) <= np.pi / 2)
    F = np.fft.fft(seg, axis=0)
    P = np.sum(np.abs(F) ** 2, axis=(1, 2))
    pk = int(np.argmax(np.where(sel, P, 0.0)))
    mk = int(np.argmin(np.abs(freqs + freqs[pk])))
    rec_syn = np.zeros((T, trials, 10), complex)
    resid = 0.0
    for b in (pk, mk):
        ws = math.copysign(w_walk, freqs[b])
        k4 = np.array([ws, kl[0], kl[1], kl[2]])
        kap = L1.kappa_of(ws, kl)
        cf = L1.colfac(k4)
        TTp = r15.tt_basis(kap)
        for r in range(trials):
            aph = F[b, r, :] * np.conj(cf)
            coef, *_ = np.linalg.lstsq(TTp, aph, rcond=None)
            resid = max(resid, float(np.linalg.norm(TTp @ coef - aph)
                                     / (np.linalg.norm(aph) + 1e-300)))
            a_st = (TTp @ coef) * cf
            rec_syn[:, r, :] += a_st[None, :] * np.exp(
                1j * freqs[b] * np.arange(T))[:, None]
    st_syn = L1.stock_count_at_k(rec_syn, kl)
    st_meas = L1.stock_count_at_k(rec_k, kl)
    n_ok = st_syn.get("n_prop") == st_meas.get("n_prop")
    svs = np.array(st_syn.get("sv", [0.0] * 8)[:4])
    svm = np.array(st_meas.get("sv", [0.0] * 8)[:4])
    dv = float(np.abs(svs - svm).max())
    return {"tt_projection_resid_max": resid,
            "stock_verbatim_measured": st_meas, "stock_verbatim_ttsynth": st_syn,
            "sv_maxdev_synth_vs_measured": dv,
            "artifact_certified": bool(n_ok and dv < 0.05 and resid < 0.05)}


def seed_single_k(nvec, kind, N=16, seed=11):
    """exact staggered single-k state on the walk's own branch (L1 recipe)."""
    kl, wq, xi, ph, proj = L1.onshell_mode(nvec, N)
    k4 = np.array([-wq, kl[0], kl[1], kl[2]])
    kap = L1.kappa_of(-wq, kl)
    if kind == "tt":
        a = r15.tt_basis(kap) @ np.array([1.0, 0.7])
    elif kind == "gauge":
        a = r15.gauge_block(kap) @ np.array([0.5, 1.0, -0.3, 0.7])
    else:
        ker, _ = L1.ker_basis(-wq, kl)
        rng = np.random.default_rng(seed)
        a = ker @ (rng.standard_normal(6) + 1j * rng.standard_normal(6))
    a = a / (np.linalg.norm(a) + 1e-300)
    cf = L1.colfac(k4)
    chi = np.zeros((10, N, N, N, 2), complex)
    for comp in range(10):
        chi[comp] = (a[comp] * cf[comp] * ph)[..., None] * xi[None, None, None, :]
    return chi[:, None], (kl, wq, xi, ph, proj), cf


def single_k_amp_run(nvec, kind, cal, T=1024, N=16):
    """damped single-k dynamics: amplitude trajectory of the seeded content.
    For kind='gauge' the asymptote is NOT zero but the packed-orthogonal
    TT-projection plateau (R22 §3 reading: the row-space component is
    suppressed, the norm falls to the kernel-component plateau, predicted
    pointwise) -- ker(K_stack) = TT and the row space is orthogonal to it."""
    chi, (kl, wq, xi, ph, proj), cf = seed_single_k(nvec, kind, N)
    # predicted plateau: || P_TT seed || (physical frame; colfac is unitary)
    a_phys = np.einsum("xyz,cxyz->c", proj, chi[:, 0, ..., 0]) * np.conj(cf)
    kap = L1.kappa_of(-wq, kl)
    Qtt, _ = np.linalg.qr(r15.tt_basis(kap))
    plateau_pred = float(np.linalg.norm(Qtt.conj().T @ a_phys))
    step = make_L2_stepper(cal, probe=False)
    Zf = np.zeros((9,) + chi.shape[1:], complex)
    amps = []
    for t in range(T):
        chi, Zf = step(chi, Zf)
        amp = np.einsum("xyz,cxyz->c", proj, chi[:, 0, ..., 0])
        aph = amp * np.conj(cf) * np.exp(-1j * (-wq) * (t + 1))
        amps.append(float(np.linalg.norm(aph)))
    return {"nvec": list(nvec), "kind": kind, "amp_first": amps[0],
            "amp_last": amps[-1], "plateau_pred_PTT": plateau_pred,
            "plateau_dev": float(abs(amps[-1] - plateau_pred)),
            "amp_drift": float(abs(amps[-1] / (amps[0] + 1e-300) - 1.0)),
            "amp_checkpoints": {str(t): amps[t]
                                for t in (0, 50, 100, 200, 400, T - 1)
                                if t < T}}


# ===========================================================================
#  main
# ===========================================================================
if __name__ == "__main__":
    t_start = time.time()
    N = 16
    print(f"backend = {B.NAME}  (fp64 required: numpy)")
    print("CP1-v4 L2 -- frozen L1 construction + Z4c damping (lane B)")
    print("=" * 74)
    out = {"backend": B.NAME, "th0": TH, "c_cone": C, "sv_thresh": SV_THRESH,
           "frozen_L1_sha256": FROZEN_L1_SHA,
           "damping_module_sha256": _sha(os.path.join(DIR, "cp1_v4_damping.py")),
           "design": ("Z4c damping with stacked ConstraintOp [W;A;T]: "
                      "W = true placed constraint with W-realized per-OFFSET "
                      "time stencils (R20 fix 1); A = static Jacobian "
                      "(R18 real-space calculus, gauge suppression channel); "
                      "T = declared algebraic trace gauge-fixing row (kills "
                      "the residual transverse-trace mode, certified pure "
                      "placed-gauge).  Comoving Z carrier = same walk kernel. "
                      "Fixed set = TT exactly at every k (incl. (2,2,2))."),
           "declared_deviations": [
               "trace gauge-fixing row (block T) is an assembly-layer gauge "
               "choice beyond the R19 constraint dictionary; it annihilates "
               "TT identically and kills only a certified pure-gauge mode",
               "G5 evaluated on the stock CALCULUS with physical-frame "
               "reading (colfac un-shift); verbatim-stock also reported, "
               "its oblique excess certified as a pure-TT reading artifact",
               "damping fixed set is smaller than ker K: the (2,2,2) "
               "Trotter excess is damped away (deviation from L1 handoff "
               "8.4 expectation, reported as data)"]}

    # -- B0 probes ----------------------------------------------------------
    rng0 = np.random.default_rng(0)
    xt = (rng0.standard_normal((10, 4, 4, 4, 2))
          + 1j * rng0.standard_normal((10, 4, 4, 4, 2)))
    inv_err = float(np.abs(walk_inv(walk_fwd(xt)) - xt).max())
    pr = probe_adjoint_assert(KOP, xt)
    bridges = {str(nv): bridge_check(nv) for nv in
               [(2, 0, 0), (2, 2, 0), (2, 2, 2)]}
    out["B0_probes"] = {"walk_inverse_err": inv_err,
                        "adjoint_probe": pr, "bridge_symbol_vs_realspace": bridges}
    b0_ok = inv_err < 1e-13 and all(v < 1e-12 for v in bridges.values())
    print(f"[B0] walk-inverse {inv_err:.1e} | adjoint probe "
          f"{pr['adjoint_mismatch_max']:.1e} | bridge "
          f"{max(bridges.values()):.1e} -> {'PASS' if b0_ok else 'FAIL'}")

    # on-shell |K_stack@TT| over the L1 15-k certificate set, both branches
    worst_tt, worst_g = 0.0, 0.0
    for nv, kl in L1.kset_lattice(N):
        for lam in np.linalg.eigvals(walk_symbol(kl)):
            Kb = K_branch(kl, lam)
            ws = -float(np.angle(lam))
            kap = L1.kappa_of(ws, kl)
            cf = L1.colfac(np.array([ws, kl[0], kl[1], kl[2]]))
            pg = placement_gate(Kb, r15.tt_basis(kap) * cf[:, None],
                                (r15.gauge_block(kap)
                                 / np.linalg.norm(r15.gauge_block(kap), axis=0))
                                * cf[:, None], expect_gauge_zero=False)
            worst_tt = max(worst_tt, pg["K_at_TT"])
            worst_g = max(worst_g, pg["K_at_gauge"])
    out["B1_cert_onshell"] = {"worst_K_at_TT": worst_tt,
                              "worst_K_at_gauge_recorded": worst_g,
                              "expect_gauge_zero": False,
                              "PASS": bool(worst_tt < 1e-12)}
    print(f"[B1] 15k x 2 branches: |K_stack@TT| = {worst_tt:.2e} (<1e-12) | "
          f"|K_stack@gauge| = {worst_g:.3f} (recorded, R18-H3 suppression "
          f"channel) -> {'PASS' if worst_tt < 1e-12 else 'FAIL'}")

    # kernel certificates per gate k + diag
    kc = {str(tuple(nv)): kernel_certificate(nv) for nv in KM_GATE + [KM_DIAG]}
    out["B2_kernel_certificates"] = kc
    kc_ok = all(v["dim_ker"] == 2 and v["ker_vs_TT_principal_cos_min"] > 1 - 1e-10
                and v["K_at_TT"] < 1e-12 for v in kc.values())
    print("[B2] kernel certificates (branch -w):")
    for k, v in kc.items():
        print(f"    k={k}: dim ker={v['dim_ker']} ker==TT cos_min="
              f"{v['ker_vs_TT_principal_cos_min']:.12f} |K@TT|={v['K_at_TT']:.1e}"
              f" |K@gauge|={v['K_at_gauge']:.3f} t-trace gauge-purity resid="
              f"{v['ttrace_gauge_purity_resid']:.1e} placed-R(t-trace)="
              f"{v['ttrace_placed_riemann']:.1e}")
    print(f"    -> {'PASS' if kc_ok else 'FAIL'} (fixed set = TT exactly)")

    # -- B3 calibration ------------------------------------------------------
    t0 = time.time()
    cal, s2_all, om_all = bz_calibrate(N)
    out["calibration"] = {k: v for k, v in cal.items()}
    print(f"[B3] calibration (full 16^3 BZ x 2 branches, {time.time()-t0:.0f}s):")
    print(f"    sigma2 = [{cal['sigma2_min']:.4f}, {cal['sigma2_max']:.4f}]  "
          f"kappa_cond = {cal['kappa_cond']:.1f}  (n = {cal['n_sigma2']})")
    print(f"    mu_z = {cal['mu_z']:.5f}  kappa1 = {cal['kappa1']:.5f}  "
          f"rho_pred = {cal['rho_step_pred']:.4f}/step")
    print(f"    plateau mu in [{cal['mu_plateau'][0]:.5f}, "
          f"{cal['mu_plateau'][1]:.5f}] (mu_choice=low, margin 4%)  "
          f"stab max {cal['mu_stab_max']:.5f}  gamma_fallback "
          f"{cal['gamma_fallback']:.5f}")
    print(f"    discrete-BZ worst rho = {cal['rho_discrete_bz']:.4f} "
          f"(== rho_pred: plateau flatness)  static-carrier rho at op = "
          f"{cal['rho_static_carrier_at_op']:.4f} (>1)")

    # -- B4 Z-sector certificates (G4 deduction) -----------------------------
    zc = {}
    for nv in KM_GATE:
        klat = np.array(nv, float) * (2 * np.pi / N)
        kl4, wq, xi, ph, proj = L1.onshell_mode(nv, N)
        cert = {}
        for tag, lam, om in (("-w", np.exp(-1j * wq), wq),
                             ("+w", np.exp(1j * wq), -wq)):
            cert[tag] = z_sector_certificate(K_branch(klat, lam), om,
                                             cal["mu_z"], cal["kappa1"])
        zc[str(tuple(nv))] = cert
    out["B4_z_sector_certificates"] = zc
    zc_ok = all(c[t]["pass"] and c[t]["dim_kerK"] == 2
                for c in zc.values() for t in c)
    print("[B4] z_sector_certificate (Z deduction, both branches):")
    for k, c in zc.items():
        v = c["-w"]
        print(f"    k={k}: unit modes = {v['n_unit_modes']} (= dim ker = "
              f"{v['dim_kerK']}), unit-mode Z content = "
              f"{v['unit_mode_Z_component_max']:.1e}, Z radius = "
              f"{v['z_sector_radius']:.4f} (pred {v['z_sector_radius_pred']:.4f})"
              f" -> {'PASS' if v['pass'] else 'FAIL'}")

    # -- C in-vitro single-k: TT preservation + gauge suppression ------------
    print("[C] damped single-k in-vitro:")
    step_probe = make_L2_stepper(cal)          # probe assertion fires here
    out["C_probe_report"] = step_probe.probe_report
    tt_runs, gauge_runs = {}, {}
    for nv in KM_GATE + [KM_DIAG]:
        e = single_k_amp_run(nv, "tt", cal, T=1024)
        tt_runs[str(tuple(nv))] = e
        print(f"    TT    k={nv}: amp drift @T=1024 = {e['amp_drift']:.2e}")
    for nv in [(2, 0, 0), (2, 2, 0)]:
        e = single_k_amp_run(nv, "gauge", cal, T=600)
        gauge_runs[str(tuple(nv))] = e
        print(f"    gauge k={nv}: amp 1 -> {e['amp_last']:.2e} @T=600, "
              f"plateau pred |P_TT g| = {e['plateau_pred_PTT']:.2e}, dev = "
              f"{e['plateau_dev']:.2e} (suppressed to the kernel plateau; "
              f"R18 H3 / R22 §3 expected)")
    out["C_tt_preservation"] = tt_runs
    out["C_gauge_suppression"] = gauge_runs

    # -- D main runs ---------------------------------------------------------
    print(f"\n[D] run A: raw generic IC (judge-faithful), N=16 T={T_MAIN} "
          f"trials=8 seed {SEED_A} ...")
    kinfo = [L1.onshell_mode(nv, N) for nv in KM_ALL]
    cm = gw.c_matter_table(TH, KM_ALL, N=N, T=T_MAIN)
    out["c_matter_ref"] = cm
    chi = L1.seed_raw(N, 8, SEED_A)
    t0 = time.time()
    recA, monA, _ = evolve_record_L2(chi, kinfo, T_MAIN, step_probe)
    out["runA_monitor"] = monA
    out["runA_seconds"] = time.time() - t0
    rg = rate_gate(np.array(monA["relC_series"]), cal["rho_step_pred"],
                   window=(100, 400))
    out["runA_rate_gate"] = rg
    print(f"    {out['runA_seconds']:.0f}s  relC {monA['relC_init']:.2f} -> "
          f"{monA['relC_last']:.2e} (tail rate {monA['relC_tail_rate']:.4f}) | "
          f"decay rate {rg['rate_meas'] if rg['rate_meas'] else 'floored'}"
          f" vs pred {rg['rate_pred']:.4f}/step | h00 "
          f"{monA['h00_rms_first']:.3f} -> {monA['h00_rms_last']:.2e} | "
          f"Z {monA['Z_rms_last']:.1e}")
    perkA = {}
    for ki, nv in enumerate(KM_ALL):
        kl, wq = kinfo[ki][0], kinfo[ki][1]
        e = L1.count_at_k(recA[:, :, ki, :], kl, wq)
        e["stock_verbatim"] = L1.stock_count_at_k(recA[:, :, ki, :], kl)
        e["stock_physical"] = stock_physical_count(recA[:, :, ki, :], kl, wq)
        end, stnd = count_nodetrend(recA[:, :, ki, :], kl, wq)
        e["nodetrend"] = {"n_prop": end["n_prop"], "sv3": end["sv3"],
                          "tt_match": end["tt_match"],
                          "stock_n_prop": stnd.get("n_prop")}
        cmat = cm[str(tuple(nv))]["c_matter"]
        e["c_matter"] = cmat
        e["j5_ratio"] = e.get("c_gw", float("nan")) / (cmat + 1e-300)
        perkA[str(tuple(nv))] = e
    out["runA_per_k"] = perkA
    print(f"    {'k':10s} {'N':>3} {'sv3':>9} {'ttm':>9} {'stockV':>7} "
          f"{'stockP':>7} {'J5':>9} {'noDetr':>7}")
    for nv in KM_ALL:
        e = perkA[str(tuple(nv))]
        print(f"    {str(nv):10s} {e['n_prop']:>3} {e['sv3']:>9.2e} "
              f"{e['tt_match']:>9.6f} {e['stock_verbatim'].get('n_prop'):>7} "
              f"{e['stock_physical'].get('n_prop'):>7} {e['j5_ratio']:>9.6f} "
              f"{e['nodetrend']['n_prop']:>7}")

    # TT reading-artifact certificates at the oblique gate k
    arts = {}
    for nv in [(2, 2, 0), (3, 1, 0), KM_DIAG]:
        ki = KM_ALL.index(nv)
        kl, wq = kinfo[ki][0], kinfo[ki][1]
        arts[str(tuple(nv))] = tt_artifact_certificate(
            recA[:, :, ki, :], kl, wq, T_MAIN)
    out["G5_tt_artifact_certificates"] = arts
    for k, a in arts.items():
        print(f"    artifact cert k={k}: stock-verbatim measured N="
              f"{a['stock_verbatim_measured'].get('n_prop')} vs pure-TT synth N="
              f"{a['stock_verbatim_ttsynth'].get('n_prop')}, sv maxdev = "
              f"{a['sv_maxdev_synth_vs_measured']:.3f}, TT-proj resid = "
              f"{a['tt_projection_resid_max']:.2e} -> "
              f"{'CERTIFIED' if a['artifact_certified'] else 'NOT CERTIFIED'}")

    # isotropy
    vs = [perkA[str(tuple(nv))]["c_gw"] for nv in KM_ISO]
    out["isotropy"] = {"axis_c_gw": vs,
                       "spread": float((max(vs) - min(vs))
                                       / (np.mean(vs) + 1e-300))}

    print(f"\n[D] run B: constraint-consistent ker-seeded IC, T=1024 trials=6 "
          f"seed {SEED_B} ...")
    nvB = KM_GATE + [KM_DIAG]
    kinfoB = [L1.onshell_mode(nv, N) for nv in nvB]
    chi = L1.seed_ker(N, 6, SEED_B, nvB)
    recB, monB, _ = evolve_record_L2(chi, kinfoB, 1024, step_probe)
    out["runB_monitor"] = monB
    perkB = {}
    for ki, nv in enumerate(nvB):
        kl, wq = kinfoB[ki][0], kinfoB[ki][1]
        e = L1.count_at_k(recB[:, :, ki, :], kl, wq)
        e["stock_physical"] = stock_physical_count(recB[:, :, ki, :], kl, wq)
        perkB[str(tuple(nv))] = e
    out["runB_per_k"] = perkB
    print("    " + "  ".join(f"{nv}:N={perkB[str(tuple(nv))]['n_prop']}"
                             f"/ttm={perkB[str(tuple(nv))]['tt_match']:.4f}"
                             for nv in nvB))
    print(f"    relC {monB['relC_init']:.2e} -> {monB['relC_last']:.2e}  "
          f"tail drift {monB['rms_tail_drift']:.2e}")

    # -- E cannons -----------------------------------------------------------
    print("\n[E] falsification cannons:")
    cann = {}
    kms2 = [(2, 0, 0), (2, 2, 0)]
    kinfo2 = [L1.onshell_mode(nv, N) for nv in kms2]

    # C0 teeth: free walk (no slave, no damping) -> N = 6.  trials = 8:
    # the cross-trial SVD rank is capped by the trial count, so >= 6 trials
    # are required for the reference count to be able to show 6 at all.
    chi = L1.seed_raw(N, 8, SEED_CANNON)
    rec0, mon0 = L1.evolve_record(chi, kinfo2, 512, mode="none")
    teeth = {str(tuple(nv)): L1.count_at_k(rec0[:, :, ki, :], kinfo2[ki][0],
                                           kinfo2[ki][1])["n_prop"]
             for ki, nv in enumerate(kms2)}
    cann["C0_teeth_free_walk"] = {"n_prop": teeth,
                                  "expected": "6 (free walk)"}
    teeth_ok = all(v >= 5 for v in teeth.values())
    print(f"  [C0 teeth] free-walk N_prop = {teeth} (expect 6) "
          f"{'OK' if teeth_ok else 'BROKEN'}")

    # C1 no damping: module off, L1 exact slave restored (frozen stepper)
    chi = L1.seed_raw(N, 8, SEED_CANNON)
    rec1, mon1 = L1.evolve_record(chi, kinfo2, 512, mode="certified")
    ramp = mon1["h00_rms_last"] / (mon1["h00_rms_first"] + 1e-300)
    st1 = {str(tuple(nv)): L1.stock_count_at_k(rec1[:, :, ki, :],
                                               kinfo2[ki][0]).get("n_prop")
           for ki, nv in enumerate(kms2)}
    cann["C1_no_damping_L1_slave"] = {
        "monitor": {k: mon1[k] for k in ("relC_max", "h00_rms_first",
                                         "h00_rms_last")},
        "h00_growth_factor": float(ramp), "stock_n_prop": st1,
        "breaks": (["G6 (Jordan ramp revived)"] if ramp > 10 else [])
                  + (["G5 (stock stays >2)"] if any(v and v > 2
                                                    for v in st1.values()) else [])}
    print(f"  [C1 no-damping/L1-slave] h00 rms x{ramp:.0f} @T=512 "
          f"(L1 runA family; constraint stays {mon1['relC_max']:.1e}) "
          f"stock N = {st1}  breaks: {cann['C1_no_damping_L1_slave']['breaks']}")

    # C2 static carrier: most-unstable k from the spectral scan, dynamics
    kworst, rho_kw = None, 0.0
    for a in range(N):
        for bb in range(N):
            for d in range(N):
                if a == bb == d == 0:
                    continue
                klat = 2 * np.pi * np.array([a, bb, d]) / N
                for lam in np.linalg.eigvals(walk_symbol(klat)):
                    s2 = np.linalg.svd(K_branch(klat, lam),
                                       compute_uv=False) ** 2
                    s2 = s2[s2 > 1e-12]
                    r = float(z4c_block_moduli(
                        cal["mu_z"], cal["kappa1"], s2,
                        phase=np.full(s2.size, -np.angle(lam))).max())
                    if r > rho_kw:
                        rho_kw, kworst = r, (a, bb, d)
    # dynamics: broadband random IC (the 16^3 box resolves every BZ mode,
    # so it CONTAINS the spectrally-worst k found above; declared)
    chi = L1.seed_raw(N, 1, SEED_CANNON)
    step_st = make_L2_stepper(cal, carrier="static", probe=False)
    Zf = np.zeros((9,) + chi.shape[1:], complex)
    Cn = []
    for t in range(160):
        chi, Zf = step_st(chi, Zf)
        Cn.append(float(np.sqrt(np.mean(np.abs(K_apply(chi)) ** 2))))
    finite2 = all(np.isfinite(v) for v in Cn)
    growth = (Cn[-1] / (Cn[0] + 1e-300)) if finite2 else float("inf")
    cann["C2_static_carrier"] = {
        "rho_spectral_at_op": cal["rho_static_carrier_at_op"],
        "worst_k": list(kworst), "rho_at_worst_k": rho_kw,
        "C_growth_160_steps": (float(growth) if finite2 else "overflow"),
        "breaks": ["G1/G7 (unstable)"] if (not finite2 or growth > 10) else []}
    print(f"  [C2 static carrier] spectral rho = "
          f"{cal['rho_static_carrier_at_op']:.3f} (worst k={kworst} "
          f"rho={rho_kw:.3f}); dynamics: C grows x"
          f"{cann['C2_static_carrier']['C_growth_160_steps']} / 160 steps  "
          f"breaks: {cann['C2_static_carrier']['breaks']}")

    # C3 lagged damping (R20 hprev disease, hand-injected)
    chi = L1.seed_raw(N, 2, SEED_CANNON)
    Zf = np.zeros((9,) + chi.shape[1:], complex)
    Cprev = None
    relC3 = []
    buf3 = [[], []]
    for t in range(384):
        chi_w = walk_fwd(chi)
        Zc = walk_fwd(Zf)
        Cnow = K_apply(chi_w)
        Cuse = Cnow if Cprev is None else Cprev          # STALE drive
        Zf = (1.0 - cal["kappa1"]) * Zc + Cuse
        chi = chi_w - cal["mu_z"] * K_adjoint(Zf)
        Cprev = Cnow
        worst = 0.0
        for s in range(2):
            buf3[s].append(np.ascontiguousarray(chi[..., s]))
            if len(buf3[s]) > 3:
                buf3[s].pop(0)
            if len(buf3[s]) == 3:
                Cr = L1.K_placed(buf3[s][0], buf3[s][1], buf3[s][2])
                hn = float(np.sqrt(np.mean(np.abs(buf3[s][1]) ** 2)))
                worst = max(worst, float(np.sqrt(np.mean(np.abs(Cr) ** 2)))
                            / (hn + 1e-300))
        relC3.append(worst)
    finite3 = all(np.isfinite(v) for v in relC3)
    rate3 = ((relC3[-1] / (relC3[-9] + 1e-300)) ** (1 / 8)
             if finite3 else float("inf"))
    fail3 = (not finite3) or relC3[-1] > 1e-10 \
        or abs(rate3 - cal["rho_step_pred"]) > 0.03
    cann["C3_lagged_damping"] = {
        "relC_last": (float(relC3[-1]) if finite3 else "overflow"),
        "relC_overflow": bool(not finite3),
        "tail_rate": (float(rate3) if np.isfinite(rate3) else "inf"),
        "rate_pred": cal["rho_step_pred"],
        "breaks": ["G1 (rate/floor fails; R20 hprev disease)"] if fail3 else []}
    print(f"  [C3 lagged damping] relC last = "
          f"{cann['C3_lagged_damping']['relC_last']} tail rate = "
          f"{cann['C3_lagged_damping']['tail_rate']} vs pred "
          f"{cal['rho_step_pred']:.4f}  breaks: "
          f"{cann['C3_lagged_damping']['breaks']}")

    # C4 integer placement regression (L1-F2 + damping).  The central stack
    # keeps the SAME (mu,kappa1): the cannon tests whether damping rescues
    # the placement disease, not whether re-tuning could.  Its adjoint is
    # probe-asserted so the kill cannot be blamed on a broken fold-back.
    step_c = make_z4c_stepper(walk_fwd, walk_fwd, KOP_CENTRAL,
                              cal["mu_z"], cal["kappa1"], probe_chi=xt)
    ttc = {}
    for nv in kms2:
        chi, (kl, wq, xi, ph, proj), cf = seed_single_k(nv, "tt", N)
        Zf = np.zeros((9,) + chi.shape[1:], complex)
        a0, aT = None, None
        for t in range(400):
            chi, Zf = step_c(chi, Zf)
            amp = np.einsum("xyz,cxyz->c", proj, chi[:, 0, ..., 0])
            nrm = float(np.linalg.norm(amp))
            a0 = nrm if a0 is None else a0
            aT = nrm
        ttc[str(tuple(nv))] = {"tt_amp_first": a0, "tt_amp_last": aT,
                               "tt_amp_ratio": aT / (a0 + 1e-300)}
    chi = L1.seed_raw(N, 4, SEED_CANNON)
    rec4 = np.zeros((512, 4, len(kms2), 10), complex)
    Zf = np.zeros((9,) + chi.shape[1:], complex)
    for t in range(512):
        chi, Zf = step_c(chi, Zf)
        H0 = np.ascontiguousarray(chi[..., 0])
        for ki, (kl, wq, xi, ph, proj) in enumerate(kinfo2):
            rec4[t, :, ki, :] = np.einsum("xyz,crxyz->rc", proj, H0)
    per4 = {}
    for ki, nv in enumerate(kms2):
        kl, wq = kinfo2[ki][0], kinfo2[ki][1]
        per4[str(tuple(nv))] = L1.count_at_k(rec4[:, :, ki, :], kl, wq)
    br4 = []
    if any(v["tt_amp_ratio"] < 0.99 for v in ttc.values()):
        br4.append("G2 (TT damped by the mis-placed operator)")
    if any(v["n_prop"] != 2 or v.get("tt_match", 1) < 0.95
           for v in per4.values()):
        br4.append("G4 (count/tt_match)")
    cann["C4_integer_placement_regression"] = {
        "tt_amp": ttc,
        "per_k": {k: {"n_prop": v["n_prop"], "sv3": v.get("sv3"),
                      "tt_match": v.get("tt_match")} for k, v in per4.items()},
        "breaks": br4}
    print(f"  [C4 integer placement + damping] TT amp ratio @400 = "
          f"{ {k: round(v['tt_amp_ratio'], 4) for k, v in ttc.items()} }  "
          f"N_prop = { {k: v['n_prop'] for k, v in per4.items()} }  "
          f"breaks: {br4}")

    out["cannons"] = cann
    cann_ok = all(len(cann[c]["breaks"]) > 0 for c in
                  ("C1_no_damping_L1_slave", "C2_static_carrier",
                   "C3_lagged_damping", "C4_integer_placement_regression"))
    out["cannons_all_fire"] = bool(cann_ok)
    out["count_teeth_ok"] = bool(teeth_ok)

    # -- GATES ---------------------------------------------------------------
    A = perkA
    g1 = (monA["relC_last"] < 1e-13 and not monA["relC_overflow"]
          and rg["ok"])
    g2_worst = max(v["amp_drift"] for v in tt_runs.values())
    g2 = g2_worst < 1e-10
    g3_dev = max(v["plateau_dev"] for v in gauge_runs.values())
    g3 = g3_dev < 1e-6                # suppressed to the predicted plateau
    g4 = (all(A[str(tuple(nv))]["n_prop"] == 2 for nv in KM_GATE) and zc_ok)
    g5_phys = all(A[str(tuple(nv))]["stock_physical"].get("n_prop") == 2
                  for nv in KM_GATE)
    g5_axial = all(A[str(tuple(nv))]["stock_verbatim"].get("n_prop") == 2
                   for nv in [(2, 0, 0), (0, 0, 2)])
    g5_art = all(a["artifact_certified"] for k, a in arts.items()
                 if k in [str(tuple(nv)) for nv in KM_GATE])
    g5 = g5_phys and g5_axial and g5_art
    h00_ratio = monA["h00_rms_last"] / (monA["h00_rms_first"] + 1e-300)
    g6_ramp = h00_ratio < 1.5
    g6_detr = all(A[str(tuple(nv))]["nodetrend"]["n_prop"]
                  == A[str(tuple(nv))]["n_prop"]
                  and abs(A[str(tuple(nv))]["nodetrend"]["sv3"]
                          - A[str(tuple(nv))]["sv3"]) < 1e-3
                  for nv in KM_GATE)
    g6 = g6_ramp and g6_detr and len(cann["C1_no_damping_L1_slave"]["breaks"]) > 0
    g7 = (monA["rms_tail_drift"] < 1e-10 and monA["Z_rms_last"] < 1e-12
          and not monA["relC_overflow"] and monB["rms_tail_drift"] < 1e-10)
    gates = {"G1_constraint_floor": bool(g1),
             "G1_relC_last": monA["relC_last"],
             "G1_rate_meas_vs_pred": [rg["rate_meas"], rg["rate_pred"]],
             "G2_TT_preserved": bool(g2), "G2_worst_amp_drift": g2_worst,
             "G3_gauge_suppressed_expected": bool(g3),
             "G3_gauge_plateau_dev_max": g3_dev,
             "G3_gauge_final_amps": {k: v["amp_last"]
                                     for k, v in gauge_runs.items()},
             "G4_Nprop2_placed_zdeduct": bool(g4),
             "G5_two_calculus_converge": bool(g5),
             "G5_stock_physical_all2": bool(g5_phys),
             "G5_stock_verbatim_axial2": bool(g5_axial),
             "G5_oblique_artifact_certified": bool(g5_art),
             "G6_jordan_killed": bool(g6), "G6_h00_ratio": float(h00_ratio),
             "G6_detrend_removable": bool(g6_detr),
             "G7_stability": bool(g7),
             "diag_222_damped_to_2": bool(A[str(KM_DIAG)]["n_prop"] == 2),
             "cannons_all_fire": bool(cann_ok),
             "count_teeth_ok": bool(teeth_ok)}
    out["gates"] = gates
    all_pass = all([g1, g2, g3, g4, g5, g6, g7, cann_ok, teeth_ok])
    out["L2_PASS"] = bool(all_pass)

    print("\n" + "=" * 74)
    print("L2 GATE TABLE (16^3 fp64 certificate)")
    print(f"  G1 relC -> machine floor + rate == pred : "
          f"{monA['relC_last']:.1e}, rate {rg['rate_meas']} vs "
          f"{rg['rate_pred']:.4f}/step -> {'PASS' if g1 else 'FAIL'}")
    print(f"  G2 TT preserved (drift < 1e-10)         : worst "
          f"{g2_worst:.1e} -> {'PASS' if g2 else 'FAIL'}")
    print(f"  G3 gauge suppressed to pred plateau     : max |amp-pred| "
          f"{g3_dev:.1e} -> {'PASS' if g3 else 'FAIL'}")
    print(f"  G4 N_prop = 2 placed (Z deducted)       : "
          f"{[A[str(tuple(nv))]['n_prop'] for nv in KM_GATE]} + Z certs -> "
          f"{'PASS' if g4 else 'FAIL'}")
    print(f"  G5 two-calculus convergence             : stockP "
          f"{[A[str(tuple(nv))]['stock_physical'].get('n_prop') for nv in KM_GATE]}"
          f", axial stockV 2/2, artifacts certified -> "
          f"{'PASS' if g5 else 'FAIL'}")
    print(f"  G6 Jordan killed + detrend removable    : h00 ratio "
          f"{h00_ratio:.2e}, no-detrend identical -> "
          f"{'PASS' if g6 else 'FAIL'}")
    print(f"  G7 stability (T>=1024, Z -> 0)          : tail drift "
          f"{monA['rms_tail_drift']:.1e}, Z {monA['Z_rms_last']:.1e} -> "
          f"{'PASS' if g7 else 'FAIL'}")
    print(f"  (2,2,2) reference                       : N_prop = "
          f"{A[str(KM_DIAG)]['n_prop']} (L1 undamped: 6; damped fixed set = TT)")
    print(f"  cannons all fire                        : "
          f"{'PASS' if cann_ok else 'FAIL'}")
    print(f"\nL2 VERDICT: {'ALL GATES PASS' if all_pass else 'NOT ALL PASS'}")

    # -- F 24^3 re-verification (only after gates) ---------------------------
    if all_pass:
        print("\n[F] 24^3 re-verification (T=1536, trials=6, raw IC) ...")
        N24 = 24
        cal24, _, _ = bz_calibrate(N24)
        out["calibration_24"] = {k: v for k, v in cal24.items()}
        print(f"    cal24: sigma2=[{cal24['sigma2_min']:.4f},"
              f"{cal24['sigma2_max']:.4f}] mu={cal24['mu_z']:.5f} "
              f"k1={cal24['kappa1']:.5f} rho={cal24['rho_step_pred']:.4f}")
        kinfo24 = [L1.onshell_mode(nv, N24) for nv in KM_GATE + [KM_DIAG]]
        step24 = make_L2_stepper(cal24, probe=False)
        chi = L1.seed_raw(N24, 6, SEED_A)
        t0 = time.time()
        rec24, mon24, _ = evolve_record_L2(chi, kinfo24, 1536, step24)
        per24 = {}
        for ki, nv in enumerate(KM_GATE + [KM_DIAG]):
            kl, wq = kinfo24[ki][0], kinfo24[ki][1]
            e = L1.count_at_k(rec24[:, :, ki, :], kl, wq)
            e["stock_physical"] = stock_physical_count(rec24[:, :, ki, :],
                                                       kl, wq)
            per24[str(tuple(nv))] = e
        out["trend_24"] = {"N": N24, "T": 1536, "trials": 6,
                           "monitor": mon24, "per_k": per24}
        print(f"    {time.time()-t0:.0f}s relC -> {mon24['relC_last']:.2e} "
              f"h00 -> {mon24['h00_rms_last']:.1e} tail drift "
              f"{mon24['rms_tail_drift']:.1e}")
        for nv in KM_GATE + [KM_DIAG]:
            e = per24[str(tuple(nv))]
            print(f"    k={nv}: N={e['n_prop']} sv3={e['sv3']:.2e} "
                  f"ttm={e['tt_match']:.6f} stockP="
                  f"{e['stock_physical'].get('n_prop')}")

    # -- hash + write --------------------------------------------------------
    out["script_sha256"] = _sha(os.path.abspath(__file__))
    out["total_seconds"] = time.time() - t_start

    def _san(o):
        if isinstance(o, dict):
            return {k: _san(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_san(v) for v in o]
        if isinstance(o, np.ndarray):
            return _san(o.tolist())
        if isinstance(o, (float, np.floating)):
            f = float(o)
            return f if np.isfinite(f) else ("inf" if f > 0 else
                                             ("-inf" if f < 0 else "nan"))
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return o

    with open(os.path.join(DIR, "cp1_v4_L2_results.json"), "w") as fh:
        json.dump(_san(out), fh, indent=1)
    print(f"\nscript sha256 = {out['script_sha256']}")
    print(f"total {out['total_seconds']:.0f}s   wrote cp1_v4_L2_results.json")
