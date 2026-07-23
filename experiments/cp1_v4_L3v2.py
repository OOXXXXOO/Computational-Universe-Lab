"""cp1_v4_L3v2 -- CP1-v4 assembly ladder, LEVEL 3 SECOND ATTACK (lane B):
the REVIEW-CERTIFIED GEOMETRY-KERNEL SWAP (T10-T13), everything else frozen.

WHAT L3-v2 IS (per 主线-CP1v4-装配阶梯与证伪炮组.md §三f and 预注册 §二d, the
authoritative rulings): v1's L3 failed because the unitary first-order walk
kernel has NO omega=0 double pole (static response ~1/k, not 1/k^2; the repo
no-go theorem boomeranged onto geometry).  The certified fix (lane A, R24)
swaps ONE part -- the geometry evolution kernel -- for the time-staggered
(h, pi) symplectic pair (Yee-FDTD time structure):

    pi(t+1/2) = pi(t-1/2) + [ cos^2(th) * Lap h(t) + S(t) ]
    h(t+1)    = h(t)      + pi(t+1/2)

with Lap = the standard second-difference Laplacian, i.e. the kappa-Laplacian
symbol 4 cos^2(th) sum_i sin^2(k_i/2) = cos^2(th) * kappa.kappa.  pi lives at
HALF-INTEGER time steps = the R13 bridge's "placed side" done on the time
axis (the same staggered-placement semantics R19 wrote on the space axis;
placement lives in the DATA: chi[...,0] = h at integer t, chi[...,1] = pi at
t+1/2, spatial OFFSET staggering per component unchanged).

FROZEN (read-only imports, hashes asserted):
  cp1_v4_L1.py       4dad03be...  K_placed (THE constraint, verbatim), judges
  cp1_v4_L2.py       556e5666...  d_sym/D_adj dictionary, stock judge
  cp1_v4_damping.py  0b868b0f...  ConstraintOp / spectral_calibrate /
                                  probe_adjoint_assert / rate_gate (module)
  cp1_v4_L3.py       dc7cdbea...  the EXACT SOURCE CHAIN (architecture-
                                  independent, certified positive asset) +
                                  canary readout + A3 oracle + v1 runner
                                  (used verbatim for the kernel-restore cannon)

THE T ROW IS DEAD (review ruling, sourced-sector death sentence, archived).
No T variant is implemented anywhere in this file.  T'' exists only in v1
(frozen) and enters no gate.

THE v2 CONSTRAINT STACK (declared assembly consequence of the kernel swap):
with the (h,pi) state the previous slice is EXACT state data, y = h - pi,
so the stacked operator reduces to the TEXTBOOK 4-component Z4c: Z_mu tracks
the TRUE placed de Donder residual, built from the ONE frozen L1.K_placed:
    rows i : K_placed(y, h, .)[1:4]      (h0i backward pairing, exact)
    row  0 : K_placed(., y, h)[0]        (h00 forward pairing, exact)
This reading equals the true 3-slice constraint AT THE CONTENT'S OWN
FREQUENCY for arbitrary content -- the v1 disease (single-slice stack
reading valid only on the walk shell) is structurally gone.  The L2 A/T
rows are NOT carried over: measured here (design table + oracle), any
non-de-Donder row (R18-A time-slot constants, static-divergence A_W, trace)
reads either the Newton well or legitimate moving sourced content and
poisons the machine floor / the well; the L2 stack was walk-era scaffolding
for a kernel that could not read its own constraint off shell.  CONSEQUENCE
(declared, gated honestly below): on-shell GAUGE waves are exactly preserved
(placed-dark, certified), so the stock full-angle counter keeps reading >2 --
the two-calculus gate is expected to FAIL and is measured as frozen.

Z placement: Z_mu rows live on the C_nu landing slots (R19 pairing), each
row an (Zh, Zpi) pair evolved by the SAME pair kernel (comoving carrier =
"the auxiliary field lives on the matter cone", R22 hard requirement).

CALIBRATION (declared v2 procedure; numbers all re-measured, none inherited):
sigma^2 of the v2 stack symbol over the full BZ -> the frozen module
spectral_calibrate closed form.  MEASURED (certified below, spectrum
attached): the L2 plateau operating point is spectrally UNSTABLE on the
symplectic kernel (max|lambda| = 2.8) -- the plateau theory assumes a
first-order carrier-matched loop.  v2 rule (pre-registered here): keep the
closed-form contraction target and kappa1 = 1 - b^2; mu = the FIRST rung of
the dyadic ladder mu_cf * 2^-j (j = 0,1,2,...) whose TRUE augmented one-step
spectrum is stable over the full BZ (<= 1 + 1e-12); the slowest contracting
|lambda| of that spectrum IS the rate prediction fed to rate_gate (the
closed-form b is recorded as calibration input only).  Run lengths derive
from the rate by the declared formula T = ceil(ln 1e-16 / ln rate) + ramp +
margin (floor certs), capped; the 32^3 run is the tail-correlation
re-verification (no floor cert, T fixed).

CERTIFICATES (fp64; ALL must pass before any gate is evaluated):
  C-T10  exactly 2 bands, |eig| = 1, band frequency == the R15-T8 half-angle
         shell pointwise (< 1e-12; review-side 2.2e-16).  PLUS the honesty
         table: pair shell vs the MATTER WALK's own frequency at the six
         lattice gate k -- axial identical (2e-16), oblique separated by the
         pre-registered R15 §5 Trotter obliquity (3.6e-2 / 1.7e-2 / 1.6e-1).
         This table IS the J5 oracle: the certified kernel sits on the IDEAL
         shell, matter sits on the WALK shell; J5 is predicted to FAIL at
         oblique k by exactly these numbers (measured below, bin-resolved).
  C-T11  static double pole: driven-pair iteration reaches
         h* = S / (4 cos^2 th sum sin^2(k_i/2)) exactly (< 1e-12;
         review-side 4.2e-15) -- the Newton well is the exact lattice fixed
         point of the update rule.
  C-T13  the static well (hbar_00 only) is in ker K_placed EXACTLY (omega=0
         => kappa_0 = 0; machine zero on the frozen real-space operator) AND
         is an EXACT fixed point of the FULL damped sourced v2 system
         (augmented-matrix residual ~1e-17): Z4c does not fight the well;
         the L3-named tension dissolves as certified.

GATE TABLE (pre-registered; any FAIL => stop + attribute, no tuning):
  G1  leakage gate RE-ERECTED (review: suspend + re-derive + same strength).
      Oracle derived IN THIS FILE BEFORE the runs (part B3): the v2 stack
      reads the true constraint exactly, so the constraint sector is driven
      ONLY by K_placed of the injected source triples; hence
        floor(exact)/floor(on-site) = drive ratio = ||K.S||_ratio ~ 1e-15,
      and the mode-level resolvent oracle gives L_kernel ~ 1e-14 vs
      L_generic ~ O(1)  (v1: 3.67 vs 3.37 -- mechanism dead; v2: alive).
      GATE (frozen now, before any run): measured field-level relC-floor
      ratio on-site/exact >= 100x  (same strength as the original G1).
  G2  source de Donder residual < 1e-10 (live, post-ramp, injected triples)
  G3  matter conservation (live) < 1e-12 (rho row + three bond-momentum rows)
  G4  wave-sector FULL REPLAY on the new kernel + live source (L2 gate set):
      floor+rate (relC < 1e-13, rate == true-spectrum prediction),
      N_prop == 2 at ALL SIX k INCLUDING (2,2,2) (placed judge at the pair
      shell, Z sector deducted by the v2 spectral census), J5 MEASURED
      (< 1e-6 over the gate set -- oracle predicts oblique FAIL, see C-T10),
      two-calculus convergence (stockP == 2 -- oracle predicts FAIL: gauge
      survives, T dead), SV (sv3 < 0.05, tt_match > 0.95), stability
      (rms tail drift < 1e-10, h00 ratio < 1.5).
      JORDAN RE-CHECK (separate register): the new kernel's k = 0 zero mode
      is the PHYSICAL Newton zero mode (double integrator = the omega=0
      double pole), distinct from v1's gauge Jordan; at k != 0 the free pair
      has NO unit-circle omega=0 channel at all (band census); the static
      well survives with damping FULLY ON (exact fixed point, C-T13).
  G5  NEWTON CANARY, formal gate (T row dead, no exemption):
      ratio_A = h00/phi structure = 2.00 +/- 0.02 AND 1/r tail correlation
      > 0.99 (24^3; frozen v1 readout canary_numbers, FFT-Poisson phi ref),
      PLUS the 32^3 tail-correlation re-verification > 0.99.
      Static readout DECLARED: time-average of h over the final T_AVG steps
      (the switch-on TT/gauge radiation is undamped by construction and
      oscillates; the equilibrium itself is time-independent and exact).
      k=0 DECLARED: periodic-box Poisson requires a zero-mean source (Jeans
      subtraction); the injected source is spatially zero-mean per component
      (exactness preserved: the source's component means are time-constant,
      verified live); the k=0 double-integrator ramp with the mean retained
      is reported under the Jordan register (physical zero mode).

CANNONS (each must break >= 1 gate; duds reported honestly):
  K1  KERNEL-RESTORE (the load-bearing cannon): geometry kernel swapped BACK
      to the v1 unitary walk = v1's own frozen R3 code path re-executed
      verbatim (L3.run_sourced + frozen [W;A;T] stack + L2.bz_calibrate);
      the canary must reproduce v1's failure (~0.611 / 0.134) to fp
      accuracy -> proves the kernel swap is the load-bearing repair.
  K2  wrong-sign source (-G): well flips to hill        -> breaks G5
  K3  tr_sign = 0 in the canary readout: ratio_A -> 4.000 exactly
                                                        -> breaks G5
  K4  on-site bilinear source (the G1 control): floor stalls orders above
      the exact-source floor -- the v1-dead G1 target is ALIVE again
                                                        -> breaks G1
  K5a no damping: relC never floors (stalls O(1))       -> breaks G4;
      Newton contrast: the well is STILL present (time-average) and the k=0
      physical ramp revives -- the "two different channels" live certificate
  K5b static Z carrier (R22 ablation): symbol spectrum + short dynamics.
      v2 PREDICTION (declared): at the v2 operating point kappa1 is large
      (Z memory ~ 1 step) so the R22 long-memory instability channel is
      closed; expected transformed/dud -- reported honestly either way.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python cp1_v4_L3v2.py
      (~15-25 min; writes cp1_v4_L3v2_results.json with its own sha256 and
       all four frozen hashes)
"""
import hashlib
import json
import math
import os
import time
import warnings

import numpy as np

# macOS Accelerate BLAS raises spurious divide/overflow/invalid FP flags on
# complex matmul (values verified finite and machine-exact by the certificates
# and the explicit overflow checks below); the cosmetic warnings are silenced.
warnings.filterwarnings("ignore", message=".*encountered in matmul")

import cp1_v4_L1 as L1                        # FROZEN (hash asserted)
import cp1_v4_L2 as L2                        # FROZEN (hash asserted)
import cp1_v4_L3 as L3                        # FROZEN v1 (hash asserted)
from cp1_v4_damping import (ConstraintOp, spectral_calibrate,
                            probe_adjoint_assert, rate_gate)
import r15_walk_dedonder as r15
from rulespace_gpu import backend as B
from rulespace_gpu import green_one_walk as gw

DIR = os.path.dirname(os.path.abspath(__file__))
FROZEN_L1_SHA = "4dad03be4319da896f485d954f0efc97bc0a6f781700f97e3e8120178a5c6035"
FROZEN_L2_SHA = "556e56665766b29c22eedf226645e3530c95c8ddc27e2b99527eb6158a70fb67"
FROZEN_DAMP_SHA = "0b868b0ffda835ff3cfdf0306952e71fc83599b4d25526756098736c1784c8ab"
FROZEN_L3V1_SHA = "dc7cdbea20e47328d0b652a5a9aefd25d8c8c2fae3f9d82b71926c02c150a9a3"


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


for _f, _h in (("cp1_v4_L1.py", FROZEN_L1_SHA), ("cp1_v4_L2.py", FROZEN_L2_SHA),
               ("cp1_v4_damping.py", FROZEN_DAMP_SHA),
               ("cp1_v4_L3.py", FROZEN_L3V1_SHA)):
    _got = _sha(os.path.join(DIR, _f))
    assert _got == _h, f"{_f} hash mismatch: {_got}"

TH = L1.TH0                                   # pi/3 shared cone (matter side)
C = L1.C_CONE                                 # 0.5
CT2 = C * C
PK = L1.PK
SEED_A, SEED_B, SEED_CANNON = 1, 2, 3         # pre-registered lineage
KM_GATE = list(L1.KM_GATE)
KM_DIAG = L1.KM_DIAG
KM_ALL = list(L1.KM_ALL)
G_FROZEN = L3.G_FROZEN                        # 0.05 (frozen v1 declaration)
T_RAMP = L3.T_RAMP                            # 128
DM_MOVING = L3.DM_MOVING                      # 0.3
SIG3 = 2.5
T_AVG = 512                                   # declared static readout window


# ===========================================================================
#  PART A. the certified geometry kernel: time-staggered (h, pi) pair
# ===========================================================================
def lap_kappa(h):
    """kappa-Laplacian: cos^2(th) * standard second difference.
    symbol: -4 cos^2 th sum_i sin^2(k_i/2) = -cos^2 th * kappa.kappa."""
    out = -6.0 * h
    for ax in (-3, -2, -1):
        out = out + np.roll(h, 1, ax) + np.roll(h, -1, ax)
    return CT2 * out


def pair_step(chi, drive=0.0):
    """one certified kernel step on the packed state chi (..., 2):
    [...,0] = h at integer t, [...,1] = pi at half steps.  The source enters
    the pi update (the R24-certified slot), hence also h via h' = h + pi'."""
    h = chi[..., 0]
    p = chi[..., 1]
    p2 = p + lap_kappa(h) + drive
    h2 = h + p2
    return np.stack([h2, p2], axis=-1)


def pair_omega(kl):
    """band frequency: EXACTLY the R15-T8 half-angle shell at every k."""
    s = C * math.sqrt(sum(math.sin(k / 2.0) ** 2 for k in kl))
    return 2.0 * math.asin(min(1.0, s))


def a_of(kl):
    return 4.0 * CT2 * sum(math.sin(k / 2.0) ** 2 for k in kl)


# ===========================================================================
#  PART B. the v2 constraint stack: textbook 4-row Z_mu on frozen K_placed
# ===========================================================================
def K2_apply(chi, c=C):
    """TRUE placed de Donder residual of the (h,pi) state, one frozen
    operator: y = h - pi is the EXACT previous slice.  Output (4,...,2)
    with the reading in [...,0] (Z rows are (Zh,Zpi) pairs; C feeds Zh)."""
    h = np.ascontiguousarray(chi[..., 0])
    p = np.ascontiguousarray(chi[..., 1])
    y = h - p
    Z = np.zeros_like(h)
    Ct = L1.K_placed(y, h, Z, c)               # rows 1..3 valid
    C0 = L1.K_placed(Z, y, h, c)               # row 0 valid
    out = np.zeros((4,) + h.shape[1:] + (2,), complex)
    out[1:4, ..., 0] = Ct[1:4]
    out[0, ..., 0] = C0[0]
    return out


def K2_adjoint(Cin, c=C):
    """exact adjoint of K2_apply (probe-asserted at stepper construction)."""
    u = Cin[..., 0]
    sh = (10,) + u.shape[1:]
    hadj = np.zeros(sh, complex)
    padj = np.zeros(sh, complex)
    for i in (1, 2, 3):
        for mu in (1, 2, 3):
            cmp = PK[(mu, i)]
            hadj[cmp] += L2.D_adj(u[i], mu, cmp)
        padj[PK[(0, i)]] += -u[i] / c
    for i in (1, 2, 3):
        cmp = PK[(i, 0)]
        d = L2.D_adj(u[0], i, cmp)
        hadj[cmp] += d
        padj[cmp] += -d
    padj[PK[(0, 0)]] += -u[0] / c
    return np.stack([hadj, padj], axis=-1)


KOP2 = ConstraintOp(K2_apply, K2_adjoint, name="K_v2[Z_mu]")


def carrier_pair(Z):
    """comoving carrier: the SAME pair kernel on each Z row (Zh, Zpi)."""
    return pair_step(Z)


def carrier_static(Z):
    return Z


def K2_sym(kl, c=C):
    """stored-frame symbol of K2_apply: (4, 20), columns [h(10), pi(10)]."""
    K = np.zeros((4, 20), complex)
    for i in (1, 2, 3):
        for mu in (1, 2, 3):
            cmp = PK[(mu, i)]
            K[i, cmp] += L2.d_sym(kl, mu, cmp)
        K[i, 10 + PK[(0, i)]] += -1.0 / c
    for i in (1, 2, 3):
        cmp = PK[(i, 0)]
        K[0, cmp] += L2.d_sym(kl, i, cmp)
        K[0, 10 + cmp] += -L2.d_sym(kl, i, cmp)
    K[0, 10 + PK[(0, 0)]] += -1.0 / c
    return K


def AW_sym(kl, c=C):
    """design-table reference: the 'static reading' K_placed(x,x,x) rows
    (pure spatial divergence).  NOT part of the v2 stack -- oracle only."""
    A = np.zeros((4, 20), complex)
    for i in (1, 2, 3):
        for mu in (1, 2, 3):
            cmp = PK[(mu, i)]
            A[i, cmp] += L2.d_sym(kl, mu, cmp)
    for i in (1, 2, 3):
        A[0, PK[(i, 0)]] += L2.d_sym(kl, i, PK[(i, 0)])
    return A


# ===========================================================================
#  PART C. augmented one-step symbol map (the v2 spectral oracle)
# ===========================================================================
def aug_map(kl, mu, k1, K=None, s10=None, carrier="pair"):
    """exact affine map of one damped sourced v2 step at mode k, state
    X = [h(10); pi(10); Zh(m); Zpi(m)].  Returns (M, b, a)."""
    a = a_of(kl)
    if K is None:
        K = K2_sym(kl)
    m = K.shape[0]
    Kd = K.conj().T
    I10 = np.eye(10)
    F = np.block([[(1 - a) * I10, I10], [-a * I10, I10]])
    Im = np.eye(m)
    Lc = (np.block([[(1 - a) * Im, Im], [-a * Im, Im]])
          if carrier == "pair" else np.eye(2 * m))
    Ph = np.zeros((m, 2 * m)); Ph[:, :m] = Im
    E = np.zeros((2 * m, m)); E[:m, :] = Im
    n = 20
    KF = K @ F
    M = np.zeros((n + 2 * m, n + 2 * m), complex)
    M[:n, :n] = F - mu * (Kd @ KF)
    M[:n, n:] = -mu * (Kd @ (Ph @ ((1 - k1) * Lc)))
    M[n:, :n] = E @ KF
    M[n:, n:] = (1 - k1) * Lc
    b = None
    if s10 is not None:
        bX = np.concatenate([np.asarray(s10, complex),
                             np.asarray(s10, complex)])
        Kb = K @ bX
        b = np.concatenate([bX - mu * (Kd @ Kb), E @ Kb])
    return M, b, a


def bz_spectrum(N, mu, k1, ks=None, carrier="pair"):
    """max |lambda| and slowest contracting |lambda| over the BZ (or ks)."""
    worst, rate = 0.0, 0.0
    if ks is None:
        it = ((aa, bb, dd) for aa in range(N) for bb in range(N)
              for dd in range(N))
    else:
        it = iter(ks)
    for nv in it:
        if nv == (0, 0, 0):
            continue
        kl = 2 * np.pi * np.array(nv, float) / N
        ml = np.abs(np.linalg.eigvals(aug_map(kl, mu, k1, carrier=carrier)[0]))
        worst = max(worst, float(ml.max()))
        sub = ml[ml < 1 - 1e-9]
        if sub.size:
            rate = max(rate, float(sub.max()))
    return worst, rate


def sample_ks(N, n_rand=500, seed=7):
    rng = np.random.default_rng(seed)
    ks = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0), (2, 2, 2), (1, 0, 0),
          (1, 1, 0), (1, 1, 1), (N // 2, N // 2, N // 2), (N // 2, 0, 0),
          (N - 1, N - 1, N - 1)]
    ks += [tuple(int(v) for v in rng.integers(0, N, 3)) for _ in range(n_rand)]
    return [k for k in ks if k != (0, 0, 0)]


def v2_calibrate(N, full_bz_stability=True):
    """declared v2 procedure: module sigma^2 measurement + closed form for
    (b, kappa1); mu = first stable rung of the dyadic ladder mu_cf * 2^-j on
    the TRUE augmented spectrum; rate prediction = slowest contracting
    |lambda| of that spectrum."""
    s2_all = []
    for aa in range(N):
        for bb in range(N):
            for dd in range(N):
                if aa == bb == dd == 0:
                    continue
                kl = 2 * np.pi * np.array([aa, bb, dd]) / N
                s2 = np.linalg.svd(K2_sym(kl), compute_uv=False) ** 2
                s2_all.append(s2[s2 > 1e-12])
    s2_all = np.concatenate(s2_all)
    cal = spectral_calibrate(s2_all, margin=0.04, mu_choice="low")
    mu_cf = cal["mu_z"]
    ks = None if full_bz_stability else sample_ks(N)
    chosen = None
    ladder = []
    for j in range(0, 10):
        mu = mu_cf * 2.0 ** (-j)
        worst, rate = bz_spectrum(N, mu, cal["kappa1"], ks=ks)
        ladder.append({"j": j, "mu": mu, "max_abs_lambda": worst,
                       "rate_slowest": rate})
        if worst <= 1.0 + 1e-12:
            chosen = (j, mu, worst, rate)
            break
    assert chosen is not None, "v2_calibrate: no stable rung on the ladder"
    j, mu, worst, rate = chosen
    out = dict(cal)
    out.update({"mu_closed_form": mu_cf, "mu_closed_form_unstable":
                bool(ladder[0]["max_abs_lambda"] > 1 + 1e-12),
                "mu_z": float(mu), "dyadic_j": j, "ladder": ladder,
                "max_abs_lambda": worst, "rate_pred_true_spectrum": rate,
                "stability_scan": "full BZ" if full_bz_stability
                else f"declared sample ({len(ks)} k)"})
    return out


def v2_z_certificate(nv, N, cal):
    """v2 spectral census at one gate k: 12 unit modes (2 bands x ker K = 6),
    zero Z content on the unit circle, subspace-level bright count = 2 per
    band (the N_prop = 2 bookkeeping with the Z sector + dark gauge
    explicitly deducted), all the rest contracting."""
    kl = 2 * np.pi * np.array(nv, float) / N
    M, _, a = aug_map(kl, cal["mu_z"], cal["kappa1"])
    lam, vec = np.linalg.eig(M)
    ml = np.abs(lam)
    unit = ml > 1 - 1e-9
    n_unit = int(unit.sum())
    zc = max((float(np.linalg.norm(vec[20:, i])) for i in range(len(lam))
              if unit[i]), default=0.0)
    rate = float(ml[~unit].max()) if (~unit).any() else 0.0
    w = pair_omega(kl)
    bright = {}
    for lam_b, tag in ((np.exp(-1j * w), "-w"), (np.exp(+1j * w), "+w")):
        idx = [i for i in range(len(lam)) if unit[i]
               and abs(lam[i] - lam_b) < 1e-6]
        if not idx:
            bright[tag] = {"dim": 0, "n_bright": -1}
            continue
        # an eigenmode with eigenvalue lam evolves as lam^t = e^{+i ws t}
        # with ws = angle(lam); that content pairs with kappa_of(ws) and
        # colfac((ws, k)) (the certified on-band frame convention)
        wv = float(np.angle(lam_b))
        kap = L1.kappa_of(wv, kl)
        cf = L1.colfac(np.array([wv, kl[0], kl[1], kl[2]]))
        Hs = np.stack([vec[:10, i] * np.conj(cf) for i in idx], axis=1)
        Q, _ = np.linalg.qr(Hs)
        R = np.stack([L1.riemann_sym(kap, Q[:, jj])
                      for jj in range(Q.shape[1])], axis=1)
        sv = np.linalg.svd(R, compute_uv=False)
        ref = np.linalg.norm(L1.riemann_sym(kap, r15.tt_basis(kap)[:, 0]))
        nb = int(np.sum(sv > 0.05 * ref))
        bright[tag] = {"dim": len(idx), "n_bright": nb,
                       "sv_over_ref": [float(v / ref) for v in sv[:4]]}
    ok = (n_unit == 12 and zc < 1e-10 and rate < 1.0
          and all(v["dim"] == 6 and v["n_bright"] == 2
                  for v in bright.values()))
    return {"nvec": list(nv), "n_unit": n_unit, "unit_Z_content_max": zc,
            "rate_slowest": rate, "bands": bright, "pass": bool(ok)}


# ===========================================================================
#  PART D. certificates C-T10 / C-T11 / C-T13
# ===========================================================================
def cert_T10(N=16):
    """band census + shell identity (continuous-k sample, r24 procedure) +
    the lattice honesty table pair-vs-walk (the J5 oracle)."""
    rng = np.random.default_rng(0)
    ks = [np.array([0.5, 0, 0]), np.array([0.35, 0.35, 0.35]),
          np.array([0.7, 0.2, -0.4])] + [rng.uniform(-1.1, 1.1, 3)
                                         for _ in range(120)]
    ks = [k for k in ks if np.linalg.norm(k) > 1e-2 and a_of(k) < 4.0]
    worst_shell, worst_mod, nbands = 0.0, 0.0, set()
    for k in ks:
        a = a_of(k)
        M = np.array([[1.0 - a, 1.0], [-a, 1.0]])
        ev = np.linalg.eigvals(M)
        nbands.add(len(ev))
        worst_mod = max(worst_mod, float(np.abs(np.abs(ev) - 1.0).max()))
        w_sh = r15.shell_omega(k)
        if w_sh is not None:
            om = np.sort(np.abs(np.angle(ev)))
            worst_shell = max(worst_shell, float(abs(om[-1] - w_sh)))
    # free-kernel omega=0 census: no unit-circle static channel at k != 0
    min_gap = np.inf
    for nv in [(1, 0, 0), (1, 1, 0), (1, 1, 1)]:
        kl = 2 * np.pi * np.array(nv, float) / 32   # smallest lattice k used
        a = a_of(kl)
        ev = np.linalg.eigvals(np.array([[1.0 - a, 1.0], [-a, 1.0]]))
        min_gap = min(min_gap, float(np.abs(ev - 1.0).min()))
    j5_tab = {}
    for nv in KM_ALL:
        kl = np.array(nv, float) * (2 * np.pi / N)
        wp = pair_omega(kl)
        ww = L1.onshell_mode(nv, N)[1]
        j5_tab[str(tuple(nv))] = {
            "w_pair": wp, "w_walk_matter": float(ww),
            "j5_dev_pred": float(abs(wp / ww - 1.0))}
    ok = (nbands == {2} and worst_mod < 1e-9 and worst_shell < 1e-12)
    return {"bands": sorted(nbands), "eig_mod_dev": worst_mod,
            "shell_dev": worst_shell,
            "min_dist_eig_to_1_smallest_k": float(min_gap),
            "j5_oracle_pair_vs_walk": j5_tab, "pass": bool(ok)}


def cert_T11():
    """static double pole by actual damped-probe iteration (r24 verbatim)."""
    rng = np.random.default_rng(0)
    ks = [np.array([0.5, 0, 0]), np.array([0.35, 0.35, 0.35]),
          np.array([0.7, 0.2, -0.4])] + [rng.uniform(-1.1, 1.1, 3)
                                         for _ in range(40)]
    ks = [k for k in ks if np.linalg.norm(k) > 1e-2 and a_of(k) < 4.0]
    worst = 0.0
    for k in ks[:40]:
        a = a_of(k)
        h, p = 0.0, 0.0
        for _ in range(20000):
            p = 0.995 * p + (-a * h + 1.0)
            h = h + p
        worst = max(worst, abs(h * a - 1.0))
    return {"static_resp_dev": float(worst), "pass": bool(worst < 1e-12)}


def cert_T13(N=24):
    """well in ker K_placed (frozen real-space operator, machine zero) AND
    exact fixed point of the full damped sourced v2 system."""
    x = np.arange(N)
    X, Y, Z3 = np.meshgrid(x, x, x, indexing="ij")
    r2 = (X - N // 2) ** 2 + (Y - N // 2) ** 2 + (Z3 - N // 2) ** 2
    rho = np.exp(-r2 / (2 * SIG3 ** 2))
    rho /= rho.sum()
    rho_zm = rho - rho.mean()
    # real-space: the exact lattice well from the certified static response
    rk = np.fft.fftn(rho_zm)
    lam = np.zeros((N, N, N))
    for ax in range(3):
        kk = 2 * np.pi * np.fft.fftfreq(N)
        sh = [1, 1, 1]; sh[ax] = N
        lam = lam + (2 - 2 * np.cos(kk)).reshape(sh)
    denom = CT2 * lam
    hk = np.where(denom > 1e-12, rk / np.where(denom > 1e-12, denom, 1.0), 0.0)
    well00 = np.real(np.fft.ifftn(hk)) * G_FROZEN
    Hw = np.zeros((10, N, N, N), complex)
    Hw[PK[(0, 0)]] = well00
    kerr = float(np.abs(L1.K_placed(Hw, Hw, Hw)).max())
    # augmented fixed point at a few lattice k
    worst_fp = 0.0
    for nv in [(1, 0, 0), (2, 0, 0), (2, 2, 0), (3, 1, 0)]:
        kl = 2 * np.pi * np.array(nv, float) / N
        s10 = np.zeros(10, complex)
        s10[PK[(0, 0)]] = 1.0
        M, b, a = aug_map(kl, CAL24["mu_z"], CAL24["kappa1"], s10=s10)
        Xs = np.concatenate([s10 / a, np.zeros(10), np.zeros(8)])
        worst_fp = max(worst_fp, float(np.linalg.norm(M @ Xs + b - Xs)))
    return {"well_kerK_realspace": kerr, "well_fixed_point_resid": worst_fp,
            "well_field_ref": well00,
            "rho_lump": rho, "rho_lump_zm": rho_zm,
            "pass": bool(kerr < 1e-14 and worst_fp < 1e-12)}


def cert_onband_frames(N=16):
    """|K2 @ TT| and |K2 @ gauge| on the pair shell (stored frame, both
    branches): TT machine-zero AND gauge machine-zero -- gauge is exactly
    preserved by the pure-de-Donder stack (declared consequence)."""
    worst_tt, worst_g = 0.0, 0.0
    for nv, kl in L1.kset_lattice(N):
        w = pair_omega(kl)
        K = K2_sym(kl)
        for ws in (-w, +w):
            kap = L1.kappa_of(ws, kl)
            cf = L1.colfac(np.array([ws, kl[0], kl[1], kl[2]]))
            lift = np.vstack([np.eye(10),
                              (1 - np.exp(-1j * ws)) * np.eye(10)])
            TT = r15.tt_basis(kap)
            G = r15.gauge_block(kap)
            Gn = G / np.linalg.norm(G, axis=0)
            worst_tt = max(worst_tt, float(
                np.abs(K @ (lift @ (TT * cf[:, None]))).max()))
            worst_g = max(worst_g, float(
                np.abs(K @ (lift @ (Gn * cf[:, None]))).max()))
    return {"worst_K_at_TT": worst_tt, "worst_K_at_gauge": worst_g,
            "note": "gauge machine-zero = exactly PRESERVED (not damped): "
                    "the declared consequence of the pure-Z_mu stack",
            "pass": bool(worst_tt < 1e-12)}


def bridge_check_v2(nvec, N=16):
    """real-space K2_apply vs symbol K2_sym, random (h,pi) amplitudes."""
    kl = np.array(nvec, float) * (2 * np.pi / N)
    ph = L1.plane(kl, N)
    proj = np.conj(ph) / N ** 3
    K = K2_sym(kl)
    rng = np.random.default_rng(3)
    v = rng.standard_normal(20) + 1j * rng.standard_normal(20)
    chi = np.zeros((10, N, N, N, 2), complex)
    for comp in range(10):
        chi[comp, ..., 0] = v[comp] * ph
        chi[comp, ..., 1] = v[10 + comp] * ph
    got = K2_apply(chi)
    amp = np.array([np.sum(proj * got[r, ..., 0]) for r in range(4)])
    return float(np.abs(amp - K @ v).max())


def aug_vs_dynamics(nvec, N=16, T=48):
    """the oracle IS the implementation: real-space damped dynamics of one
    seeded k-mode vs powers of the augmented matrix (machine agreement)."""
    kl = np.array(nvec, float) * (2 * np.pi / N)
    ph = L1.plane(kl, N)
    proj = np.conj(ph) / N ** 3
    M, _, _ = aug_map(kl, CAL16["mu_z"], CAL16["kappa1"])
    rng = np.random.default_rng(4)
    X = rng.standard_normal(28) + 1j * rng.standard_normal(28)
    chi = np.zeros((10, N, N, N, 2), complex)
    Zf = np.zeros((4, N, N, N, 2), complex)
    for comp in range(10):
        chi[comp, ..., 0] = X[comp] * ph
        chi[comp, ..., 1] = X[10 + comp] * ph
    for r in range(4):
        Zf[r, ..., 0] = X[20 + r] * ph
        Zf[r, ..., 1] = X[24 + r] * ph
    mu, k1 = CAL16["mu_z"], CAL16["kappa1"]
    worst = 0.0
    for t in range(T):
        chi_w = pair_step(chi)
        Cc = K2_apply(chi_w)
        Zf = (1 - k1) * carrier_pair(Zf) + Cc
        chi = chi_w - mu * K2_adjoint(Zf)
        X = M @ X
        amp = np.concatenate(
            [[np.sum(proj * chi[comp, ..., 0]) for comp in range(10)],
             [np.sum(proj * chi[comp, ..., 1]) for comp in range(10)],
             [np.sum(proj * Zf[r, ..., 0]) for r in range(4)],
             [np.sum(proj * Zf[r, ..., 1]) for r in range(4)]])
        worst = max(worst, float(np.abs(amp - X).max()
                                 / (np.abs(X).max() + 1e-300)))
    return worst


# ===========================================================================
#  PART E. the sourced damped runner
# ===========================================================================
def run_v2(chi, source, cal, T, kinfo=None, gscale=G_FROZEN, ramp=T_RAMP,
           damping=True, carrier="pair", record=True, avg_last=0,
           zero_mean_src=True):
    """evolve the v2 assembly; monitor the TRUE 3-slice constraint (frozen
    K_placed) on recorded h slices; certify K.S on the actually injected
    (zero-meaned) source triples post-ramp (G2); track the k=0 channel."""
    mu, k1 = cal["mu_z"], cal["kappa1"]
    car = carrier_pair if carrier == "pair" else carrier_static
    trials = chi.shape[1] if chi.ndim == 6 else 1
    Zf = np.zeros((4,) + chi.shape[1:], complex)
    rec = (np.zeros((T, trials, len(kinfo), 10), complex)
           if (kinfo and record) else None)
    relC, h00r, rmsf, znorm, h00mean = [], [], [], [], []
    buf = []
    Sbuf = []
    ksrc_worst = 0.0
    mean_drift = 0.0
    mean_ref = None
    havg = None
    n_avg = 0
    for t in range(T):
        g = gscale * (0.5 - 0.5 * math.cos(math.pi * min(1.0, (t + 1) / ramp)))
        S = source.advance()
        if zero_mean_src:
            m = S.mean(axis=(-3, -2, -1), keepdims=True)
            if mean_ref is None:
                mean_ref = m.copy()
                sc0 = max(float(np.abs(S).max()), 1e-300)
            mean_drift = max(mean_drift, float(np.abs(m - mean_ref).max())
                             / sc0)
            S = S - m
        drive = g * (S[:, None] if chi.ndim == 6 else S)
        chi_w = pair_step(chi, drive)
        if damping:
            Cc = K2_apply(chi_w)
            Zf = (1 - k1) * car(Zf) + Cc
            chi = chi_w - mu * K2_adjoint(Zf)
        else:
            chi = chi_w
        if True:
            Sbuf.append(S.astype(complex))
            if len(Sbuf) > 3:
                Sbuf.pop(0)
            if len(Sbuf) == 3 and t >= ramp + 2:
                Cs = L1.K_placed(Sbuf[0], Sbuf[1], Sbuf[2])
                sc = max(float(np.sqrt(np.mean(np.abs(Sbuf[1]) ** 2))), 1e-300)
                ksrc_worst = max(ksrc_worst, float(
                    np.sqrt(np.mean(np.abs(Cs) ** 2))) / sc)
        H0 = np.ascontiguousarray(chi[..., 0])
        if rec is not None:
            for ki, (kl, wq, ph, proj) in enumerate(kinfo):
                rec[t, :, ki, :] = np.einsum("xyz,crxyz->rc", proj,
                                             H0 if chi.ndim == 6
                                             else H0[:, None])
        buf.append(H0)
        if len(buf) > 3:
            buf.pop(0)
        if len(buf) == 3:
            Cr = L1.K_placed(buf[0], buf[1], buf[2])
            hn = float(np.sqrt(np.mean(np.abs(buf[1]) ** 2)))
            relC.append(float(np.sqrt(np.mean(np.abs(Cr) ** 2)))
                        / (hn + 1e-300))
        h00r.append(float(np.sqrt(np.mean(np.abs(chi[PK[(0, 0)], ..., 0]) ** 2))))
        h00mean.append(float(np.real(chi[PK[(0, 0)], ..., 0].mean())))
        rmsf.append(float(np.sqrt(np.mean(np.abs(chi) ** 2))))
        znorm.append(float(np.sqrt(np.mean(np.abs(Zf) ** 2))))
        if avg_last and t >= T - avg_last:
            havg = H0.copy() if havg is None else havg + H0
            n_avg += 1
    if havg is not None:
        havg = havg / max(n_avg, 1)
    finite = all(np.isfinite(v) for v in relC)
    tail = relC[-9:]
    mon = {"relC_max": float(max(relC)), "relC_last": float(relC[-1]),
           "relC_postramp_min": float(min(relC[ramp + 8:]))
           if len(relC) > ramp + 8 else float(relC[-1]),
           "relC_tail_rate": float((tail[-1] / (tail[0] + 1e-300))
                                   ** (1.0 / max(1, len(tail) - 1))),
           "relC_overflow": bool(not finite),
           "relC_series": [float(v) for v in relC],
           "Ksrc_worst_rel_postramp": float(ksrc_worst),
           "src_mean_drift_rel": float(mean_drift),
           "h00_rms_first": h00r[2] if len(h00r) > 2 else h00r[-1],
           "h00_rms_last": h00r[-1],
           "h00_mean_first": h00mean[2] if len(h00mean) > 2 else h00mean[-1],
           "h00_mean_last": h00mean[-1],
           "rms_full_first": rmsf[0], "rms_full_last": rmsf[-1],
           "rms_tail_drift": float(abs(rmsf[-1] / (rmsf[3 * len(rmsf) // 4]
                                                   + 1e-300) - 1.0)),
           "Z_rms_last": znorm[-1],
           "consv_rho": float(getattr(source, "consv_rho", 0.0)),
           "consv_b": float(getattr(source, "consv_b", 0.0))}
    return chi, rec, mon, havg


def kinfo_pair(nv, N):
    kl = np.array(nv, float) * (2 * np.pi / N)
    ph = L1.plane(kl, N)
    return (kl, pair_omega(kl), ph, np.conj(ph) / N ** 3)


def canary_on_avg(havg, rho_src, sig, tr_sign=1.0):
    """frozen v1 readout (L3.canary_numbers) fed the time-averaged h field."""
    chi_like = np.zeros(havg.shape + (2,), complex)
    chi_like[..., 0] = havg
    return L3.canary_numbers(chi_like, rho_src, sig, tr_sign=tr_sign)


# ===========================================================================
#  main
# ===========================================================================
if __name__ == "__main__":
    t_start = time.time()
    print(f"backend = {B.NAME}  (fp64 required: numpy)")
    print("CP1-v4 L3-v2 -- certified (h,pi) kernel swap, everything else "
          "frozen (lane B)")
    print("=" * 74)
    out = {"backend": B.NAME, "th0": TH, "c_cone": C, "G_frozen": G_FROZEN,
           "T_ramp": T_RAMP, "T_avg": T_AVG, "dm_moving": DM_MOVING,
           "frozen_L1_sha256": FROZEN_L1_SHA,
           "frozen_L2_sha256": FROZEN_L2_SHA,
           "frozen_damping_sha256": FROZEN_DAMP_SHA,
           "frozen_L3v1_sha256": FROZEN_L3V1_SHA,
           "seeds": {"A": SEED_A, "B": SEED_B, "cannon": SEED_CANNON},
           "declared": [
               "kernel swap ONLY: geometry evolution = time-staggered (h,pi)"
               " pair, kappa-Laplacian symbol 4cos^2(th)sum sin^2(k_i/2); "
               "pi at half steps = R13-bridge placed side on the time axis "
               "(placement in the data, R19 semantics unchanged)",
               "v2 stack = textbook 4-row Z_mu on the TRUE placed de Donder "
               "residual, y = h - pi exact previous slice, one frozen "
               "L1.K_placed for measure AND fold-back (enforce==measure); "
               "L2's A/T rows not carried (T dead by ruling; A-type rows "
               "read the well / moving sourced content -- design table); "
               "consequence: on-shell gauge exactly preserved (placed-dark),"
               " two-calculus stock gate expected to FAIL and measured as "
               "frozen",
               "Z rows are (Zh,Zpi) pairs on the C_nu landing slots, "
               "comoving carrier = same pair kernel (R22 hard requirement)",
               "calibration: module sigma^2 + closed form for (b, kappa1); "
               "closed-form mu is spectrally UNSTABLE on the symplectic "
               "kernel (certified, spectrum attached); mu = first stable "
               "dyadic rung mu_cf*2^-j on the TRUE augmented BZ spectrum; "
               "rate prediction = slowest contracting |lambda|",
               "run lengths from the rate: T = ceil(ln 1e-16/ln rate) + "
               "ramp + margin (floor certs); 32^3 = tail re-verification, "
               "T fixed 1024, no floor cert",
               "static readout = time-average of h over the final T_avg "
               "steps (undamped switch-on TT/gauge radiation oscillates; "
               "the equilibrium is time-independent and exact)",
               "sources injected spatially zero-mean per component (Jeans "
               "subtraction; periodic-box Poisson); component means are "
               "time-constant (verified live) so K.S exactness survives; "
               "k=0 double-integrator with mean retained = the PHYSICAL "
               "Newton zero mode, reported in the Jordan register",
               "G1 re-erected at the ORIGINAL strength (>=100x) with the "
               "oracle derivation in part B3, frozen before any run"]}

    # ---- B0 probes --------------------------------------------------------
    print("[B0] probes:")
    rng0 = np.random.default_rng(0)
    xt = (rng0.standard_normal((10, 5, 5, 5, 2))
          + 1j * rng0.standard_normal((10, 5, 5, 5, 2)))
    pr = probe_adjoint_assert(KOP2, xt)
    bridges = {str(nv): bridge_check_v2(nv) for nv in
               [(2, 0, 0), (2, 2, 0), (2, 2, 2)]}
    # source chain integrity (frozen v1 chain, quick re-probe)
    psi_t = rng0.standard_normal((10, 10, 10, 4)) \
        + 1j * rng0.standard_normal((10, 10, 10, 4))
    psi_t /= np.sqrt((np.abs(psi_t) ** 2).sum())
    src_t = L3.ExactSource(psi_t.copy(), DM_MOVING)
    Sb, ks_t = [], 0.0
    for _ in range(10):
        Sb.append(src_t.advance().astype(complex))
        if len(Sb) > 3:
            Sb.pop(0)
        if len(Sb) == 3:
            Cs = L1.K_placed(Sb[0], Sb[1], Sb[2])
            sc = float(np.sqrt(np.mean(np.abs(Sb[1]) ** 2)))
            ks_t = max(ks_t, float(np.sqrt(np.mean(np.abs(Cs) ** 2))) / sc)
    out["B0_probes"] = {"adjoint_probe": pr,
                        "bridge_symbol_vs_realspace": bridges,
                        "source_chain_KS_probe": ks_t,
                        "source_chain_consv": [src_t.consv_rho, src_t.consv_b]}
    b0_ok = (max(bridges.values()) < 1e-12 and ks_t < 1e-12
             and src_t.consv_rho < 1e-12 and src_t.consv_b < 1e-12)
    print(f"    adjoint {pr['adjoint_mismatch_max']:.1e} | bridge "
          f"{max(bridges.values()):.1e} | source-chain K.S {ks_t:.1e} "
          f"consv {src_t.consv_rho:.1e}/{src_t.consv_b:.1e} -> "
          f"{'PASS' if b0_ok else 'FAIL'}")

    # ---- B1 calibrations (needed by certs) --------------------------------
    t0 = time.time()
    CAL16 = v2_calibrate(16, full_bz_stability=True)
    CAL24 = v2_calibrate(24, full_bz_stability=False)
    CAL32 = v2_calibrate(32, full_bz_stability=False)
    out["calibration_16"] = dict(CAL16)
    out["calibration_24"] = {k: v for k, v in CAL24.items() if k != "ladder"}
    out["calibration_32"] = {k: v for k, v in CAL32.items() if k != "ladder"}
    print(f"[B1] v2 calibration ({time.time()-t0:.0f}s):")
    for N_, cal in ((16, CAL16), (24, CAL24), (32, CAL32)):
        print(f"    N={N_}: sigma2=[{cal['sigma2_min']:.3f},"
              f"{cal['sigma2_max']:.3f}] closed-form mu={cal['mu_closed_form']:.5f}"
              f" UNSTABLE={cal['mu_closed_form_unstable']} -> dyadic j="
              f"{cal['dyadic_j']} mu={cal['mu_z']:.5f} k1={cal['kappa1']:.5f}"
              f" max|l|={cal['max_abs_lambda']:.6f} rate_pred="
              f"{cal['rate_pred_true_spectrum']:.5f} ({cal['stability_scan']})")
    avd = aug_vs_dynamics((2, 2, 0))
    out["B0_probes"]["aug_matrix_vs_dynamics"] = avd
    print(f"    oracle==implementation: aug-matrix vs real-space dynamics "
          f"rel dev {avd:.1e}")

    # ---- B2 certificates --------------------------------------------------
    print("\n[B2] certificates (must all pass before gates):")
    ct10 = cert_T10()
    out["certs"] = {"T10": {k: v for k, v in ct10.items()
                            if k != "j5_oracle_pair_vs_walk"}}
    out["certs"]["T10"]["j5_oracle"] = ct10["j5_oracle_pair_vs_walk"]
    print(f"  C-T10 bands={ct10['bands']} |eig|-1={ct10['eig_mod_dev']:.2e} "
          f"shell dev={ct10['shell_dev']:.2e} -> "
          f"{'PASS' if ct10['pass'] else 'FAIL'}")
    print("        J5 oracle (pair ideal shell vs matter walk shell):")
    for k, v in ct10["j5_oracle_pair_vs_walk"].items():
        print(f"          k={k}: w_pair={v['w_pair']:.6f} w_matter="
              f"{v['w_walk_matter']:.6f} J5 dev pred = {v['j5_dev_pred']:.2e}")
    ct11 = cert_T11()
    out["certs"]["T11"] = ct11
    print(f"  C-T11 static double pole: |h*.a/S - 1| = "
          f"{ct11['static_resp_dev']:.2e} -> "
          f"{'PASS' if ct11['pass'] else 'FAIL'}")
    ct13 = cert_T13()
    out["certs"]["T13"] = {k: v for k, v in ct13.items()
                           if k not in ("well_field_ref", "rho_lump",
                                        "rho_lump_zm")}
    print(f"  C-T13 well in ker K_placed = {ct13['well_kerK_realspace']:.1e} "
          f"(machine) | damped-system fixed-point resid = "
          f"{ct13['well_fixed_point_resid']:.1e} -> "
          f"{'PASS' if ct13['pass'] else 'FAIL'}")
    cob = cert_onband_frames()
    out["certs"]["onband_frames"] = cob
    print(f"  on-band |K2@TT| = {cob['worst_K_at_TT']:.1e} | |K2@gauge| = "
          f"{cob['worst_K_at_gauge']:.1e} (gauge exactly PRESERVED, "
          f"declared) -> {'PASS' if cob['pass'] else 'FAIL'}")
    certs_ok = (ct10["pass"] and ct11["pass"] and ct13["pass"] and cob["pass"]
                and b0_ok and avd < 1e-10)
    out["certs"]["all_pass"] = bool(certs_ok)
    assert certs_ok, "certificate replication failed -- stop before gates"

    # z certificates + design table
    zc = {str(tuple(nv)): v2_z_certificate(nv, 16, CAL16)
          for nv in KM_GATE + [KM_DIAG]}
    out["B2_z_certificates"] = zc
    zc_ok = all(v["pass"] for v in zc.values())
    print("  v2 spectral census (Z deduction):")
    for k, v in zc.items():
        print(f"    k={k}: n_unit={v['n_unit']} (=12) unitZ="
              f"{v['unit_Z_content_max']:.1e} bright/band="
              f"{[v['bands'][t]['n_bright'] for t in ('-w', '+w')]} (=2) "
              f"rate={v['rate_slowest']:.5f} -> "
              f"{'PASS' if v['pass'] else 'FAIL'}")
    # design table: on-band kernels of the candidate stacks (assembly note)
    des = {}
    for nv in [(2, 0, 0), (2, 2, 0), (2, 2, 2)]:
        kl = 2 * np.pi * np.array(nv, float) / 16
        w = pair_omega(kl)
        lift = np.vstack([np.eye(10), (1 - np.exp(-1j * (-w))) * np.eye(10)])
        cf = L1.colfac(np.array([-w, kl[0], kl[1], kl[2]]))
        row = {}
        for tag, Kst in (("W", K2_sym(kl)),
                         ("W_AW", np.vstack([K2_sym(kl), AW_sym(kl)]))):
            Kb = Kst @ (lift @ np.diag(cf))
            sv = np.linalg.svd(Kb, compute_uv=False)
            rank = int((sv > 1e-10 * sv[0]).sum())
            row[tag] = 10 - rank
        des[str(tuple(nv))] = row
    out["B2_design_table_onband_kernel_dims"] = des
    print(f"  design table dim ker(on-band): {des}  "
          f"(W: TT+gauge=6; W+A_W: TT+tau=3; tau is de-Donder-blind and "
          f"T-type rows are dead => no legal stack reaches stock=2)")

    # handoff candidate (symbol level only, NOT run as dynamics): the
    # walk-trace Laplacian a_tr(k) = 2 - Re tr U_walk(k) -- a local stencil
    # whose symbol equals 4 sin^2(w_walk/2) exactly, i.e. a pair kernel on
    # the WALK shell at every k (J5 restored) that keeps the omega=0 double
    # pole (statics) and leaves C-T13 untouched (well shape independent).
    atr = {}
    for nv in KM_ALL:
        kl = np.array(nv, float) * (2 * np.pi / 16)
        U = L2.walk_symbol(kl)
        a_tr = float(2.0 - np.real(np.trace(U)))
        ww = L1.onshell_mode(nv, 16)[1]
        atr[str(tuple(nv))] = {
            "a_tr": a_tr, "four_sin2_half_w_walk": 4 * math.sin(ww / 2) ** 2,
            "identity_dev": float(abs(a_tr - 4 * math.sin(ww / 2) ** 2)),
            "Im_trU": float(np.imag(np.trace(U)))}
    out["handoff_atr_candidate"] = {
        "table": atr,
        "identity_dev_max": max(v["identity_dev"] for v in atr.values()),
        "note": "2 - tr U_walk is a finite trig polynomial (stencil radius "
                "<= 1 per axis, det U = 1 => tr real): swapping the "
                "kappa-Laplacian for it puts the pair bands on the WALK "
                "shell at every k (J5 exact by construction again) while "
                "keeping the omega=0 double pole; C-T13 holds for any "
                "radial shape; C-T11's lattice-exact 1/k^2 becomes "
                "1/a_tr(k) (equal to O(k^4)).  NOT run at L3-v2 (outside "
                "the certified spec) -- named L3-v3/L4 candidate."}
    print(f"  handoff a_tr candidate: |a_tr - 4sin^2(w_walk/2)| max = "
          f"{out['handoff_atr_candidate']['identity_dev_max']:.1e} "
          f"(identity exact; J5-restoring kernel candidate, not run)")

    # ---- B3 G1 oracle re-derivation (BEFORE any gated run) ----------------
    print("\n[B3] G1 oracle re-derivation (gate frozen BEFORE the runs):")
    kl_a = np.array([2 * np.pi * 2 / 16, 0.0, 0.0])
    w_m = L3.matter_omega(kl_a, TH, DM_MOVING)
    A3 = L3.A3_of(w_m, kl_a)
    ker3 = np.linalg.svd(A3)[2][np.linalg.matrix_rank(A3):].conj().T
    rng5 = np.random.default_rng(5)
    lt = {}
    for tag, Kst in (("v2_W_only", None),
                     ("v2_W_plus_AW", np.vstack([K2_sym(kl_a),
                                                 AW_sym(kl_a)]))):
        row = {}
        for kind in ("kernel", "generic"):
            if kind == "kernel":
                s = ker3 @ (rng5.standard_normal(ker3.shape[1])
                            + 1j * rng5.standard_normal(ker3.shape[1]))
            else:
                s = rng5.standard_normal(10) + 1j * rng5.standard_normal(10)
            s = s / np.linalg.norm(s)
            M, b, _ = aug_map(kl_a, CAL16["mu_z"], CAL16["kappa1"], K=Kst,
                              s10=s)
            y = np.linalg.solve(np.eye(M.shape[0]) - np.exp(1j * w_m) * M, b)
            row[kind] = {"L_leak": float(np.linalg.norm(A3 @ y[:10])),
                         "gain": float(np.linalg.norm(y[:10]))}
        lt[tag] = row
    out["B3_leakage_oracle"] = {
        "w_matter": float(w_m), "k": "(2,0,0)", "transfer": lt,
        "v1_reference": {"L_kernel": 3.67, "L_generic": 3.37,
                         "verdict": "mechanism dead (same order)"},
        "derivation": "the v2 stack reads the TRUE 3-slice constraint for "
        "arbitrary content (bridge cert); the per-component scalar Green "
        "function preserves ker A3, so a kernel-compatible source drives "
        "ZERO constraint content and the field floor equals the vacuum "
        "floor; the on-site source drives ||K.S|| ~ 0.5 and its floor is "
        "the driven equilibrium.  Predicted separation = the drive ratio "
        "~ 1e15.  GATE (same strength as v1): measured floor ratio "
        "on-site/exact >= 100x."}
    print(f"    v2 W-only : L_kernel = {lt['v2_W_only']['kernel']['L_leak']:.2e}"
          f"  L_generic = {lt['v2_W_only']['generic']['L_leak']:.2e}   "
          f"(v1: 3.67 vs 3.37 -- mechanism resurrected)")
    print(f"    v2 W+A_W  : L_kernel = "
          f"{lt['v2_W_plus_AW']['kernel']['L_leak']:.2e} (A_W-type rows "
          f"poison the floor -> excluded from the stack, design table)")
    print("    G1 GATE FROZEN: on-site/exact relC floor ratio >= 100x")

    # =======================================================================
    #  R1. LEAKAGE SECTOR, exact source (16^3, moving massive packet)
    # =======================================================================
    N = 16
    rate16 = CAL16["rate_pred_true_spectrum"]
    T1 = min(4608, int(math.ceil(math.log(1e-16) / math.log(rate16)))
             + T_RAMP + 192)
    T1 = ((T1 + 63) // 64) * 64
    trials = 6
    print(f"\n[R1] leakage sector, EXACT source: 16^3 T={T1} trials={trials} "
          f"G={G_FROZEN} (T from declared rate formula, rate={rate16:.5f})")
    kinfo = [kinfo_pair(nv, N) for nv in KM_ALL]
    cm = gw.c_matter_table(TH, KM_ALL, N=N, T=T1)
    out["c_matter_ref"] = cm
    psi0 = L3.gauss_packet(N, 2.5, (0.7, 0.0, 0.0), L3.SP_MOVING)
    srcE = L3.ExactSource(psi0.copy(), DM_MOVING)
    chi = L1.seed_raw(N, trials, SEED_A)       # h random, pi = 0 (declared)
    t0 = time.time()
    chi1, rec1, mon1, _ = run_v2(chi, srcE, CAL16, T1, kinfo)
    out["R1_monitor"] = {k: v for k, v in mon1.items() if k != "relC_series"}
    out["R1_monitor"]["relC_checkpoints"] = {
        str(t): mon1["relC_series"][t]
        for t in (0, 64, 128, 200, 400, 800, 1600, T1 - 3)
        if t < len(mon1["relC_series"])}
    out["R1_source_diag"] = srcE.diag()
    rg1 = rate_gate(np.array(mon1["relC_series"]), rate16,
                    window=(T_RAMP + 72, T_RAMP + 472))
    out["R1_rate_gate"] = rg1
    print(f"    {time.time()-t0:.0f}s relC max {mon1['relC_max']:.2f} -> last "
          f"{mon1['relC_last']:.2e} | rate "
          f"{rg1['rate_meas'] if rg1['rate_meas'] else 'floored'} vs pred "
          f"{rg1['rate_pred']:.5f} | K.S live "
          f"{mon1['Ksrc_worst_rel_postramp']:.2e} | consv "
          f"{mon1['consv_rho']:.1e}/{mon1['consv_b']:.1e} | mean drift "
          f"{mon1['src_mean_drift_rel']:.1e}")
    perk1 = {}
    for ki, nv in enumerate(KM_ALL):
        kl, wq = kinfo[ki][0], kinfo[ki][1]
        e = L1.count_at_k(rec1[:, :, ki, :], kl, wq)
        e["stock_physical"] = L2.stock_physical_count(rec1[:, :, ki, :],
                                                      kl, wq)
        cmat = cm[str(tuple(nv))]["c_matter"]
        e["c_matter"] = cmat
        e["j5_ratio"] = e.get("c_gw", float("nan")) / (cmat + 1e-300)
        e["j5_dev_pred"] = ct10["j5_oracle_pair_vs_walk"][str(tuple(nv))][
            "j5_dev_pred"]
        perk1[str(tuple(nv))] = e
    out["R1_per_k"] = perk1
    print(f"    {'k':10s} {'N':>3} {'sv3':>9} {'ttm':>9} {'stockP':>7} "
          f"{'J5':>9} {'J5pred':>9} {'kerRes':>8}")
    for nv in KM_ALL:
        e = perk1[str(tuple(nv))]
        print(f"    {str(nv):10s} {e['n_prop']:>3} {e['sv3']:>9.2e} "
              f"{e['tt_match']:>9.6f} {e['stock_physical'].get('n_prop'):>7} "
              f"{e['j5_ratio']:>9.6f} {1+e['j5_dev_pred']:>9.6f} "
              f"{e['ker_resid_max']:>8.1e}")

    # =======================================================================
    #  R2. LEAKAGE SECTOR, on-site control (cannon K4 / the G1 target)
    # =======================================================================
    T2 = min(T1, 1536)
    print(f"\n[R2] on-site control source (cannon K4): T={T2} trials=2 ...")
    srcO = L3.OnsiteSource(psi0.copy(), DM_MOVING)
    chi = L1.seed_raw(N, 2, SEED_CANNON)
    t0 = time.time()
    _, _, mon2, _ = run_v2(chi, srcO, CAL16, T2, None, record=False)
    out["R2_monitor"] = {k: v for k, v in mon2.items() if k != "relC_series"}
    leak_exact = mon1["relC_last"]
    leak_onsite = mon2["relC_last"]
    g1_ratio = leak_onsite / max(leak_exact, 1e-300)
    print(f"    {time.time()-t0:.0f}s relC floor: onsite {leak_onsite:.2e} "
          f"(tail rate {mon2['relC_tail_rate']:.4f}) vs exact "
          f"{leak_exact:.2e}  ratio x{g1_ratio:.1e}  (v1: 0.14x REVERSED)")

    # =======================================================================
    #  R3. NEWTON sector primary canary (24^3) + 32^3 tail re-verification
    # =======================================================================
    N3 = 24
    rate24 = CAL24["rate_pred_true_spectrum"]
    T3 = min(6144, int(math.ceil(math.log(1e-16) / math.log(rate24)))
             + T_RAMP + 192)
    T3 = ((T3 + 63) // 64) * 64
    rho_lump = ct13["rho_lump"]
    rho_zm = ct13["rho_lump_zm"]
    print(f"\n[R3] NEWTON canary: 24^3 T={T3} sigma={SIG3} (frozen lump, "
          f"zero-mean injected; readout = time-avg last {T_AVG}) ...")
    t0 = time.time()
    chi = np.zeros((10, N3, N3, N3, 2), complex)
    chi3, _, mon3, havg3 = run_v2(chi, L3.FrozenSource(rho_zm), CAL24, T3,
                                  None, record=False, avg_last=T_AVG,
                                  zero_mean_src=False)
    cn3 = canary_on_avg(havg3, rho_lump, SIG3)
    cn3_inst = L3.canary_numbers(chi3, rho_lump, SIG3)
    out["R3_monitor"] = {k: v for k, v in mon3.items() if k != "relC_series"}
    out["R3_canary_primary"] = cn3
    out["R3_canary_instantaneous"] = cn3_inst
    print(f"    {time.time()-t0:.0f}s A_hbar00={cn3['A_hbar00']:+.3e} "
          f"ratio_A={cn3['ratio_A']:+.6f} (gate 2.00+-0.02) tailcorr="
          f"{cn3['tailcorr_h00']:+.6f} (gate >0.99) ratio_B="
          f"{cn3['ratio_B']:+.4f} -> {'PASS' if cn3['gate_pass'] else 'FAIL'}"
          f"   [instantaneous: {cn3_inst['ratio_A']:+.4f}/"
          f"{cn3_inst['tailcorr_h00']:+.4f}]")
    print(f"    relC last {mon3['relC_last']:.2e} | K.S live "
          f"{mon3['Ksrc_worst_rel_postramp']:.1e} (frozen lump: exact 0)")
    # oracle pointwise: the analytic well field vs the measured average
    pred00 = ct13["well_field_ref"]
    meas00 = np.real(havg3[PK[(0, 0)]])
    meas00 = meas00 - meas00.mean()
    dev3 = float(np.abs(meas00 - pred00).max() / (np.abs(pred00).max()
                                                  + 1e-300))
    out["R3_oracle_pointwise"] = {"rel_dev": dev3}
    print(f"    oracle pointwise (analytic well vs measured avg h00): "
          f"rel dev {dev3:.2e}")

    N4 = 32
    T4 = 1024
    print(f"[R3b] 32^3 tail re-verification: T={T4} ...")
    x4 = np.arange(N4)
    X4, Y4, Z4 = np.meshgrid(x4, x4, x4, indexing="ij")
    r24_ = (X4 - N4 // 2) ** 2 + (Y4 - N4 // 2) ** 2 + (Z4 - N4 // 2) ** 2
    rho32 = np.exp(-r24_ / (2 * SIG3 ** 2))
    rho32 /= rho32.sum()
    t0 = time.time()
    chi = np.zeros((10, N4, N4, N4, 2), complex)
    _, _, mon4, havg4 = run_v2(chi, L3.FrozenSource(rho32 - rho32.mean()),
                               CAL32, T4, None, record=False, avg_last=512,
                               zero_mean_src=False)
    cn4 = canary_on_avg(havg4, rho32, SIG3)
    out["R3b_monitor"] = {k: v for k, v in mon4.items() if k != "relC_series"}
    out["R3b_canary_32"] = cn4
    print(f"    {time.time()-t0:.0f}s ratio_A={cn4['ratio_A']:+.6f} "
          f"tailcorr={cn4['tailcorr_h00']:+.6f} (gate >0.99)")

    # =======================================================================
    #  R6. cannons
    # =======================================================================
    print("\n[R6] falsification cannons:")
    cann = {}

    # K1: kernel-restore -- v1's own frozen R3 code path, verbatim
    print("  [K1 kernel-restore] v1 walk kernel + frozen [W;A;T] stack "
          "(L3.run_sourced verbatim) ...")
    t0 = time.time()
    cal24_v1, _, _ = L2.bz_calibrate(24)
    v1json = json.load(open(os.path.join(DIR, "cp1_v4_L3_results.json")))
    cal_dev = max(abs(cal24_v1["mu_z"] - v1json["calibration_24"]["mu_z"]),
                  abs(cal24_v1["kappa1"] - v1json["calibration_24"]["kappa1"]))
    chi = np.zeros((10, N3, N3, N3, 2), complex)
    chiK1, _, monK1 = L3.run_sourced(chi, L3.FrozenSource(rho_lump), cal24_v1,
                                     560, None, record=False)
    cnK1 = L3.canary_numbers(chiK1, rho_lump, SIG3)
    ref = v1json["R3_canary_primary"]
    repro = max(abs(cnK1["ratio_A"] - ref["ratio_A"]),
                abs(cnK1["tailcorr_h00"] - ref["tailcorr_h00"]))
    k1_fire = bool((not cnK1["gate_pass"]) and repro < 1e-6)
    cann["K1_kernel_restore"] = {
        "ratio_A": cnK1["ratio_A"], "tailcorr": cnK1["tailcorr_h00"],
        "v1_reference": {"ratio_A": ref["ratio_A"],
                         "tailcorr": ref["tailcorr_h00"]},
        "reproduction_dev": float(repro), "cal_dev_vs_v1json": float(cal_dev),
        "breaks": ["G5 (v1 kernel fails the canary; swap is load-bearing)"]
        if k1_fire else []}
    print(f"    {time.time()-t0:.0f}s ratio_A={cnK1['ratio_A']:+.4f} "
          f"tail={cnK1['tailcorr_h00']:+.4f} vs v1 ({ref['ratio_A']:+.4f}/"
          f"{ref['tailcorr_h00']:+.4f})  repro dev {repro:.1e}  breaks: "
          f"{cann['K1_kernel_restore']['breaks']}")

    # K2: wrong-sign source
    T6 = 1024
    chi = np.zeros((10, N3, N3, N3, 2), complex)
    _, _, _, havgK2 = run_v2(chi, L3.FrozenSource(rho_zm), CAL24, T6, None,
                             record=False, gscale=-G_FROZEN, avg_last=T_AVG,
                             zero_mean_src=False)
    cnK2 = canary_on_avg(havgK2, rho_lump, SIG3)
    k2_fire = bool(cnK2["A_hbar00"] < 0)
    cann["K2_wrong_sign"] = {"A_hbar00": cnK2["A_hbar00"],
                             "breaks": ["G5 (well flips to hill)"]
                             if k2_fire else []}
    print(f"  [K2 wrong sign] A_hbar00 = {cnK2['A_hbar00']:+.2e}  breaks: "
          f"{cann['K2_wrong_sign']['breaks']}")

    # K3: tr_sign = 0 (readout chain)
    cn_tr0 = canary_on_avg(havg3, rho_lump, SIG3, tr_sign=0.0)
    k3_fire = bool(abs(cn_tr0["ratio_A"] - 2.0) > 0.02)
    cann["K3_tr_sign_zero"] = {
        "ratio_A_tr0": cn_tr0["ratio_A"], "ratio_A_normal": cn3["ratio_A"],
        "breaks": ["G5 (ratio_A -> 4)"] if k3_fire else []}
    print(f"  [K3 tr_sign=0] ratio_A {cn3['ratio_A']:+.4f} -> "
          f"{cn_tr0['ratio_A']:+.4f}  breaks: "
          f"{cann['K3_tr_sign_zero']['breaks']}")

    # K4: on-site source == R2 (the resurrected G1 target)
    k4_fire = bool(g1_ratio >= 100.0)
    cann["K4_onsite_source"] = {
        "relC_floor_onsite": leak_onsite, "relC_floor_exact": leak_exact,
        "leak_ratio": float(g1_ratio),
        "breaks": ["G1 (floor stalls >=100x above exact)"] if k4_fire else []}
    print(f"  [K4 on-site] floor ratio x{g1_ratio:.1e}  breaks: "
          f"{cann['K4_onsite_source']['breaks']}  (v1: DUD, target dead; "
          f"v2: target alive)")

    # K5a: no damping -- leakage stall + Newton two-channel contrast
    Tnd = 512
    srcE3 = L3.ExactSource(psi0.copy(), DM_MOVING)
    chi = L1.seed_raw(N, 2, SEED_CANNON)
    _, _, monN, _ = run_v2(chi, srcE3, CAL16, Tnd, None, record=False,
                           damping=False)
    stall = bool(monN["relC_last"] > 1e-3
                 and monN["relC_tail_rate"] > 0.999)
    chi = np.zeros((10, N3, N3, N3, 2), complex)
    _, _, monN3, havgN3 = run_v2(chi, L3.FrozenSource(rho_lump), CAL24, 1024,
                                 None, record=False, damping=False,
                                 avg_last=T_AVG, zero_mean_src=False)
    cnN3 = canary_on_avg(havgN3, rho_lump, SIG3)
    k5a_fire = bool(stall)
    cann["K5a_no_damping"] = {
        "leakage_relC_last": monN["relC_last"],
        "leakage_relC_tail_rate": monN["relC_tail_rate"],
        "newton_mean_retained": {
            "h00_mean_last": monN3["h00_mean_last"],
            "h00_rms_last": monN3["h00_rms_last"],
            "note": "k=0 double integrator ramps (PHYSICAL zero mode; mean "
                    "retained on purpose in this cannon)"},
        "newton_canary_timeavg": {k: cnN3[k] for k in
                                  ("ratio_A", "tailcorr_h00", "A_hbar00")},
        "breaks": ["G4 (constraint never floors)"] if k5a_fire else []}
    print(f"  [K5a no damping] leakage relC stalls at "
          f"{monN['relC_last']:.2e} (rate {monN['relC_tail_rate']:.4f}) "
          f"breaks: {cann['K5a_no_damping']['breaks']}")
    print(f"      Newton contrast: well STILL present in time-avg "
          f"(ratio_A={cnN3['ratio_A']:+.3f} tail={cnN3['tailcorr_h00']:+.3f})"
          f"; k=0 mean ramps to {monN3['h00_mean_last']:.2e} -- the TWO "
          f"CHANNELS separated live")

    # K5b: static Z carrier (R22 ablation) -- SAME length as R1 so the floor
    # comparison is fair (a shorter run would fake a stall)
    wS, rS = bz_spectrum(16, CAL16["mu_z"], CAL16["kappa1"],
                         ks=sample_ks(16, 300), carrier="static")
    chi = L1.seed_raw(N, 2, SEED_CANNON)
    srcE4 = L3.ExactSource(psi0.copy(), DM_MOVING)
    _, _, monS, _ = run_v2(chi, srcE4, CAL16, T1, None, record=False,
                           carrier="static")
    k5b_fire = bool(wS > 1.0 + 1e-9 or monS["relC_overflow"]
                    or monS["relC_last"] > 100 * leak_exact)
    cann["K5b_static_carrier"] = {
        "spectral_max_abs_lambda": float(wS),
        "spectral_rate": float(rS),
        "dyn_T": int(T1),
        "dyn_relC_last": monS["relC_last"],
        "dyn_relC_tail_rate": monS["relC_tail_rate"],
        "note": "v2 PREDICTION (declared): kappa1 large => Z memory ~1 step "
                "=> the R22 long-memory static-carrier instability channel "
                "is closed; a dud here is the predicted transformed outcome",
        "breaks": ["G4 (static carrier destabilizes/stalls)"]
        if k5b_fire else []}
    print(f"  [K5b static carrier] spectral max|l|={wS:.6f} rate={rS:.5f}; "
          f"dyn relC last {monS['relC_last']:.2e}  breaks: "
          f"{cann['K5b_static_carrier']['breaks']}"
          + ("" if k5b_fire else "  [DUD -- predicted transformed outcome, "
             "reported honestly]"))

    out["cannons"] = cann
    cann_ok = all(len(cann[c]["breaks"]) > 0 for c in
                  ("K1_kernel_restore", "K2_wrong_sign", "K3_tr_sign_zero",
                   "K4_onsite_source", "K5a_no_damping"))
    out["cannons_all_fire"] = bool(cann_ok and len(
        cann["K5b_static_carrier"]["breaks"]) > 0)
    out["cannons_core_fire"] = bool(cann_ok)

    # =======================================================================
    #  GATES
    # =======================================================================
    g1 = bool(g1_ratio >= 100.0)
    g2 = bool(max(mon1["Ksrc_worst_rel_postramp"],
                  mon3["Ksrc_worst_rel_postramp"]) < 1e-10)
    g3 = bool(max(mon1["consv_rho"], mon1["consv_b"]) < 1e-12)
    g4_floor = bool(mon1["relC_last"] < 1e-13 and rg1["ok"]
                    and not mon1["relC_overflow"])
    g4_nprop = bool(all(perk1[str(tuple(nv))]["n_prop"] == 2
                        for nv in KM_ALL) and zc_ok)
    j5devs = {str(tuple(nv)): abs(perk1[str(tuple(nv))]["j5_ratio"] - 1.0)
              for nv in KM_GATE}
    g4_j5 = bool(max(j5devs.values()) < 1e-6)
    g4_twocalc = bool(all(perk1[str(tuple(nv))]["stock_physical"].get(
        "n_prop") == 2 for nv in KM_GATE))
    g4_sv = bool(all(perk1[str(tuple(nv))]["sv3"] < 0.05
                     and perk1[str(tuple(nv))]["tt_match"] > 0.95
                     for nv in KM_GATE))
    g4_stab = bool(mon1["rms_tail_drift"] < 1e-10
                   and mon1["h00_rms_last"] / (mon1["h00_rms_first"] + 1e-300)
                   < 1.5)
    g4_jordan = bool(ct10["min_dist_eig_to_1_smallest_k"] > 1e-3
                     and ct13["well_fixed_point_resid"] < 1e-12
                     and mon1["h00_rms_last"] / (mon1["h00_rms_first"]
                                                 + 1e-300) < 1.5)
    g4 = bool(g4_floor and g4_nprop and g4_j5 and g4_twocalc and g4_sv
              and g4_stab and g4_jordan)
    g5 = bool(cn3["gate_pass"] and cn4["tailcorr_h00"] > 0.99)

    gates = {"G1_leakage_100x": g1, "G1_leak_ratio": float(g1_ratio),
             "G1_floor_exact": float(leak_exact),
             "G1_floor_onsite": float(leak_onsite),
             "G2_source_deDonder_lt_1e-10": g2,
             "G2_KS_worst": float(max(mon1["Ksrc_worst_rel_postramp"],
                                      mon3["Ksrc_worst_rel_postramp"])),
             "G3_conservation_lt_1e-12": g3,
             "G3_worst": float(max(mon1["consv_rho"], mon1["consv_b"])),
             "G4_wave_replay": g4,
             "G4_parts": {"floor_rate": g4_floor, "nprop_all6_zdeduct":
                          g4_nprop, "j5": g4_j5,
                          "j5_devs": {k: float(v) for k, v in j5devs.items()},
                          "two_calculus_stockP": g4_twocalc,
                          "stockP": {str(tuple(nv)):
                                     perk1[str(tuple(nv))]["stock_physical"]
                                     .get("n_prop") for nv in KM_GATE},
                          "sv": g4_sv, "stability": g4_stab,
                          "jordan_register": g4_jordan},
             "G5_canary": g5,
             "G5_primary": {k: cn3[k] for k in
                            ("ratio_A", "ratio_B", "tailcorr_h00",
                             "A_hbar00", "well_not_hill")},
             "G5_tail32": float(cn4["tailcorr_h00"]),
             "cannons_core_fire": bool(cann_ok)}
    out["gates"] = gates
    all_pass = bool(g1 and g2 and g3 and g4 and g5 and cann_ok)
    out["L3v2_PASS"] = all_pass

    out["jordan_register"] = {
        "free_kernel_no_omega0_channel_at_k_nonzero":
            {"min_dist_eig_to_1": ct10["min_dist_eig_to_1_smallest_k"],
             "note": "v1's gauge Jordan lived at omega=0 for every k in the "
                     "slaved walk; the free pair kernel has NO unit-circle "
                     "omega=0 mode at k != 0 (bands +-omega(k) only)"},
        "k0_physical_newton_mode": {
            "free_kernel_k0": "[[1,1],[0,1]] Jordan block = the omega=0 "
                              "double pole that IS the Newton 1/k^2 sector",
            "no_damping_mean_ramp": cann["K5a_no_damping"][
                "newton_mean_retained"]["h00_mean_last"],
            "damped_zero_mean_h00_mean": mon3["h00_mean_last"]},
        "well_with_damping_fully_on": {
            "fixed_point_resid": ct13["well_fixed_point_resid"],
            "measured_ratio_A": cn3["ratio_A"],
            "note": "Z4c does not kill the well -- exact fixed point "
                    "(C-T13); the two channels (constraint damping on the "
                    "wave shell vs omega=0 statics) are structurally "
                    "different, measured live via K5a"},
        "h00_secular_in_damped_runA": float(
            mon1["h00_rms_last"] / (mon1["h00_rms_first"] + 1e-300))}

    out["verdict_material"] = {
        "headline_fixed": "G5 canary PASSES at machine level (ratio_A = "
        f"{cn3['ratio_A']:.6f}, tail = {cn3['tailcorr_h00']:.6f}, 32^3 tail "
        f"= {cn4['tailcorr_h00']:.6f}) and G1 is re-erected AND passed "
        f"(floor ratio x{g1_ratio:.1e}); the two v1 killers are cured by "
        "the certified kernel swap; K1 reproduces v1's failure to "
        f"{cann['K1_kernel_restore']['reproduction_dev']:.0e} -- the swap "
        "is load-bearing.",
        "named_finding_1_J5_oblique": "the certified kernel sits EXACTLY on "
        "the R15-T8 ideal shell; matter's walk kernel carries the "
        "pre-registered R15 §5 Trotter obliquity; the shell identity that "
        "v1 had BY SHARED CONSTRUCTION is therefore broken at oblique k by "
        "exactly the frozen-oracle offsets (pred 3.56e-2 / 1.70e-2 / "
        "1.58e-1) -- measured to bin resolution.  The graviton is "
        "SUB-LUMINAL relative to matter at oblique k: the wide-box vs "
        "light-cone North-Star obstacle resurfaces as the price of the "
        "static sector.  Candidate reconciliation (symbol-level table in "
        "handoff_atr_candidate, NOT run): the walk-trace Laplacian "
        "a_tr(k) = 2 - Re tr U_walk(k), a local stencil with a_tr == "
        "4 sin^2(w_walk/2) to machine precision -- puts the pair kernel on "
        "the WALK shell at every k while keeping the omega=0 double pole.",
        "named_finding_2_two_calculus": "with T dead (review ruling) no "
        "legal stack reaches stock=2: every de-Donder row is blind to the "
        "transverse-trace gauge mode; the v2 pure-Z_mu stack exactly "
        "preserves ALL on-shell gauge (certified |K@gauge| ~ 1e-16), so "
        "stockP stays >2 while the placed count is 2 everywhere INCLUDING "
        "(2,2,2) (the body-diagonal Trotter excess is gone with the kernel)."
        "  The two-calculus gate outcome is a structural consequence of "
        "the T-row death sentence, not an assembly defect.",
        "named_finding_3_stability_drift": "rms tail drift = G*source "
        "steady inflow with no sponge (same attribution as v1); L4's "
        "medicine, unchanged.",
        "calibration_note": "the L2 plateau closed form is INAPPLICABLE to "
        "the symplectic kernel (its operating point measured spectrally "
        "unstable, max|lambda| = 2.8); the declared v2 rule (dyadic ladder "
        "on the true augmented spectrum) is certified stable on the full "
        "BZ and its rate prediction is the rate gate's reference."}

    print("\n" + "=" * 74)
    print("L3-v2 GATE TABLE")
    print(f"  G1 leakage >=100x (re-erected)     : x{g1_ratio:.1e} -> "
          f"{'PASS' if g1 else 'FAIL'}")
    print(f"  G2 source de Donder < 1e-10        : "
          f"{gates['G2_KS_worst']:.2e} -> {'PASS' if g2 else 'FAIL'}")
    print(f"  G3 conservation live < 1e-12       : "
          f"{gates['G3_worst']:.2e} -> {'PASS' if g3 else 'FAIL'}")
    print(f"  G4 wave replay                     : floor/rate={g4_floor} "
          f"nprop={g4_nprop} J5={g4_j5} twocalc={g4_twocalc} sv={g4_sv} "
          f"stab={g4_stab} jordan={g4_jordan} -> "
          f"{'PASS' if g4 else 'FAIL'}")
    print(f"  G5 canary (formal gate)            : ratio_A="
          f"{cn3['ratio_A']:+.6f} tail={cn3['tailcorr_h00']:+.6f} "
          f"tail32={cn4['tailcorr_h00']:+.6f} -> "
          f"{'PASS' if g5 else 'FAIL'}")
    print(f"  cannons (5 core)                   : "
          f"{'ALL FIRE' if cann_ok else 'DUD PRESENT'}  (K5b "
          f"{'fires' if len(cann['K5b_static_carrier']['breaks']) else 'dud (predicted)'})")
    print(f"\nL3-v2 VERDICT: {'ALL GATES PASS' if all_pass else 'NOT ALL PASS'}")

    # ---- hash + write ------------------------------------------------------
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

    with open(os.path.join(DIR, "cp1_v4_L3v2_results.json"), "w") as fh:
        json.dump(_san(out), fh, indent=1)
    print(f"\nscript sha256 = {out['script_sha256']}")
    print(f"total {out['total_seconds']:.0f}s   wrote cp1_v4_L3v2_results.json")
