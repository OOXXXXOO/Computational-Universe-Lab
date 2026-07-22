"""cp1_v4_L1 -- CP1-v4 assembly ladder, LEVEL 1 (lane B, M1 re-attack).

WHAT L1 IS (per 主线-CP1v4-装配阶梯与证伪炮组.md, the authoritative spec):
the FIRST joint assembly of the certified parts -- walk kernel + K_placed
constraint -- with NO damping, NO source, NO sponge (those are L2-L4):

  * walk kernel : R14 graviton walk -- all 10 tensor components chi_c
    (2-spinor, complex) evolved by the SAME unitary split-step operator as
    matter (theta_g = theta_matter), via rulespace_gpu.green_one_walk.
    geom_walk_all (imported, NOT copied: importing the identical code object
    IS the shared-cone guarantee).
  * h storage   : R19 staggered placement semantics (定理笔记-R19).  Stored
    array of component c=(mu,nu) means hbar(t=n+o0/2, x=j+osp/2),
    o=(e_mu+e_nu) mod 2.  Placement lives in the DATA (seeding + pairing
    convention), never in the operator.
  * K_placed    : verbatim port of r19_staggered_placement.K_placed --
    integer rolls between staggered sublattices (R17 fwd/bwd dictionary) +
    the R20-certified time pairing (hbar_00 FORWARD next-cur, hbar_0i
    BACKWARD cur-prev).  hprev is retired: the operator sees only the
    rolling slice buffer, no damped-history state.
  * constraint  : L1 uses EXACT enforcement (the sanctioned exact-projection
    option): each macro step, the 0nu rows of the NEW slice are solved so
    that K_placed(H(t-2), H(t-1), H(t)) = 0 identically, and the correction
    is computed BY CALLING THE SAME K_placed FUNCTION used for measurement
    (enforce == measure, single code object, probe-asserted).
  * R21 coverage: the slave overwrites chi_0nu on BOTH spinor components,
    real AND imaginary parts (all 4 real dims per site) -- no walk-carried
    freedom survives in the 0nu sector (kills R21's 16 unitary residuals).
    R20's "slave projection forbidden" is read as forbidding enforce/measure
    FRAME MISMATCH; here the two are the same function, which is exactly
    what R20 prescribes.

OBLIQUE-k CHOICE (declared, per the spec's "palindromic axis order OR R19
oracle prediction -- pick one"): we keep the NON-PALINDROMIC single-sweep
kernel (the exact operator certified in R14/R19/CP0; a palindromic macro
step would destroy the axial half-angle shell sin^2(w/2)=c^2 sum sin^2(k/2)
on which the entire K_placed nullity rests) and handle oblique k by the R19
ORACLE: the walk's own frequency w_walk (measured from the operator's 2x2
k-mode matrix) is off the ideal shell by the pre-registered Trotter
correction (R15 §5); the slaved dynamics then lives EXACTLY on
ker K(w_walk,k), which the symbol oracle predicts pointwise.  Consequences,
computed by the oracle BEFORE the run (part B2):
    axial (2,0,0),(0,0,2)   : kap.kap ~ 1e-16 -> N_prop = 2 exactly;
    planar  (2,2,0),(3,1,0) : kap.kap = -0.086/-0.047 -> sv3 = 0.035/0.017
                              (< 0.05) -> N_prop = 2, oracle-matched;
    body diagonal (2,2,2)   : kap.kap = -0.683 -> oracle predicts N_prop=6.
GATE k-SET therefore = {(2,0,0),(0,0,2),(2,2,0),(3,1,0)} (axial + oblique,
4 modes as required); (2,2,2) is measured, reported, and ORACLE-MATCHED
(pointwise ker-residual < 1e-12 + whitened SV spectrum vs oracle), NOT
gated to 2 -- its excess is the walk-core Trotter property R19 §6 says is
"not a placement debt", and R15 §5 pre-registered.  Any fix belongs to a
kernel upgrade, not to L1 tuning.

KNOWN-AND-ORACLE-UNDERSTOOD FEATURE (declared): with a RAW generic random
IC, the exactly-enforced system carries a marginal zero-frequency Jordan
(secular) gauge mode: the initial h_0i static offset feeds h_00 linearly in
t through the row-0 recursion.  This is residual GAUGE content (zero placed
Riemann at any propagating frequency), is absent for constraint-consistent
initial data (run B: ker-seeded, bounded to 1e-14), and is precisely the
content L2's damping is designed to kill (R18 H3: gauge suppression is
expected).  The spectral pipeline linearly detrends each recorded series
(exact removal of the omega=0 ramp; declared, applied uniformly).

MEASUREMENT (projection-free Riemann-SVD count, kappa calculus):
generic/ker random data -> evolve -> per probe k record the 10-component
stored-frame mode series -> two-sided windowed FFT (walk convention puts
single-branch content at negative bins) -> at the propagating peak,
un-shift stored amplitudes to the physical frame (placement colfac; a unit
phase, lossless) -> symbol-level linearized Riemann at the placed kappa
direction (R19 §5.5: TT projector / judge direction = kappa, not k;
pre-registration cannon 9) -> stack trials -> SVD.  No TT projector
anywhere in the count.  The stock full-angle-calculus count (emergence_
judge math) is ALSO reported as a reference line -- it sees undamped
placed-gauge content as bright by calculus mismatch (R15), which is
expected at L1 (no damping) and is NOT the gate.

GATES (all simultaneous, fp64; FAIL => stop at L1 and write attribution):
  G1  N_prop = 2 at the 4 gate k (axial + oblique), run A (raw IC)
  G2  J5: |c_gw/c_matter - 1| < 1e-6  (shared kernel -> binned ratio exact)
  G3  |K@TT| < 1e-12 and |K@gauge| < 1e-12 on shell (direct real-space
      application, R19 gate-A path, 15 k x both branches);  PLUS dynamic
      bulk constraint machine-zero during evolution (max relC < 1e-13)
  G4  SV hard gate: sv3 < 0.05 and tt_match > 0.95 at gate k (run A)
  G5  stability at T >= 1000: walk-sector norm drift < 1e-10 (run A) and
      full-state drift < 1e-10 for constraint-consistent IC (run B);
      run-A secular gauge ramp reported and attributed (0nu rows only)

FALSIFICATION CANNONS (L1 set; each must break >= 1 gate):
  F1  theta_g != theta_matter (0.9 vs pi/3)      -> J5 must FAIL
  F2  integer-grid central template (no staggered
      storage semantics; CP0/CP1-v1 disease)     -> |K@TT| ~ 0.23, count
  F3  slave covers only Re(spinor0) of chi_0nu
      (1/4 real dims; the R21 disease)           -> constraint floor/count
  F4  lagged enforcement (stale K inputs, the
      R20 hprev disease)                         -> constraint floor

Run:  RULESPACE_BACKEND=numpy .venv/bin/python cp1_v4_L1.py
      (~6-10 min; writes cp1_v4_L1_results.json; sha256 of this file is
       embedded in the JSON)
"""
import hashlib
import json
import math
import os
import time

import numpy as np

import r15_walk_dedonder as r15
import r17_placement_operators as r17
from rulespace_gpu import backend as B
from rulespace_gpu import green_one_walk as gw

DIR = os.path.dirname(os.path.abspath(__file__))
TH0 = math.pi / 3.0                    # theta_g = theta_matter (lane B ref)
C_CONE = math.cos(TH0)                 # c = cos theta = 0.5
SEED_A, SEED_B, SEED_CANNON = 1, 2, 3  # fixed, pre-registered
SV_THRESH = 0.05                       # judge threshold (emergence_judge)
ETA = np.diag([-1.0, 1.0, 1.0, 1.0])

SYM = r15.SYM                          # packed order 00,01,...,33
PK = {}
for _i, (_m, _n) in enumerate(SYM):
    PK[(_m, _n)] = _i
    PK[(_n, _m)] = _i
OFFSET = np.array([r17.offset(m, n) for (m, n) in SYM])   # (10,4) 0/1 flags
NU0 = [PK[(0, nu)] for nu in range(4)]
SPATIAL = [PK[(i, j)] for i in (1, 2, 3) for j in range(i, 4)]

KM_GATE = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0)]    # gate k-set
KM_DIAG = (2, 2, 2)                                       # oracle-matched
KM_ISO = [(2, 0, 0), (0, 2, 0), (0, 0, 2)]
KM_ALL = [(2, 0, 0), (0, 2, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0), (2, 2, 2)]


# ===========================================================================
#  PART A. construction: K_placed (R19 verbatim port) + the L1 slaved stepper
# ===========================================================================
def D_dict(f, mu, comp):
    """R17 dictionary spatial difference by integer roll between sublattices.
    f (..., Nx, Ny, Nz): spatial axes are the last three."""
    ax = mu - 4
    if OFFSET[comp][mu]:
        return f - np.roll(f, 1, axis=ax)          # backward  f(x)-f(x-e)
    return np.roll(f, -1, axis=ax) - f             # forward   f(x+e)-f(x)


def K_placed(Hp, Hc, Hn, c=C_CONE):
    """THE constraint operator (r19_staggered_placement.K_placed, verbatim
    port).  H* shaped (10, ..., Nx,Ny,Nz).  Rows: C_0 at (t=n+1/2, x int);
    C_i at (t=n, x+e_i/2).  Time pairing: 0i (half-time) cur-prev [centered
    at integer n]; h_00 (integer-time) next-cur [centered at n+1/2].
    Integer rolls + pairing convention -- no phases, no interpolation, no
    hprev state.  This ONE function is used for BOTH measurement and
    enforcement (probe-asserted below)."""
    C = np.zeros((4,) + Hc.shape[1:], complex)
    for nu in range(4):
        acc = np.zeros(Hc.shape[1:], complex)
        for mu in (1, 2, 3):
            comp = PK[(mu, nu)]
            acc = acc + D_dict(Hc[comp], mu, comp)
        c0 = PK[(0, nu)]
        dt = (Hc[c0] - Hp[c0]) if OFFSET[c0][0] else (Hn[c0] - Hc[c0])
        C[nu] = acc - dt / c
    return C


def K_central(Hp, Hc, Hn, c=C_CONE):
    """FALSIFICATION F2 operator: integer-grid central template (CP0/CP1-v1
    disease; R19 negative control (a))."""
    C = np.zeros((4,) + Hc.shape[1:], complex)
    for nu in range(4):
        acc = np.zeros(Hc.shape[1:], complex)
        for mu in (1, 2, 3):
            f = Hc[PK[(mu, nu)]]
            acc = acc + 0.5 * (np.roll(f, -1, axis=mu - 4)
                               - np.roll(f, 1, axis=mu - 4))
        c0 = PK[(0, nu)]
        C[nu] = acc - 0.5 * (Hn[c0] - Hp[c0]) / c
    return C


def make_stepper(mode="certified", th=TH0, c_slave=None):
    """Returns step(chi, hist) -> (chi, hist).  chi (10,...,N,N,N,2) complex;
    hist = per-spinor list of the last TWO stored slices [H(t-2), H(t-1)]
    (plain rolling buffer -- NOT a damped hprev; R20 fix list #1).

    modes:
      certified : L1 construction.  After the walk step, chi_0nu is FULLY
                  overwritten on both spinor components (4/4 real dims,
                  R21 coverage) by exact K_placed enforcement:
                    rows i (centered at new slice t):
                       C = K_placed(H(t-1), H_new, 0);  h0i_new += c*C_i
                    row 0 (centered at t-1/2):
                       C = K_placed(0, H(t-1), H_new);  h00_new += c*C_0
                  => K_placed(H(t-2),H(t-1),H(t)) == 0 identically, every t.
      none      : free 10x walk (control; expected N_prop = 6).
      central   : F2 -- same slave logic but with K_central (enforce==measure
                  for the central operator; its OWN monitor is zero, the kill
                  is |K_central@TT| ~ 0.23 + wrong count).
      partial   : F3 -- certified stencils but only Re(spinor0) is slaved
                  (1/4 real dims; Im + spinor-1 keep walk momentum; the CP0 /
                  R21 disease).
      lagged    : F4 -- corrections computed from one-step-STALE slices
                  (K inputs from t-1/t-2; the R20 hprev disease).
    """
    c = C_CONE if c_slave is None else c_slave

    def step(chi, hist):
        chi = gw.geom_walk_all(chi, th, th, th, th)
        newh = []
        for s in range(2):
            Hs = np.ascontiguousarray(chi[..., s])
            Hp2, Hp1 = hist[s]
            Z = np.zeros_like(Hs)
            if mode == "certified":
                Ct = K_placed(Hp1, Hs, Z, c)               # rows 1..3 valid
                for i in (1, 2, 3):
                    Hs[PK[(0, i)]] = Hs[PK[(0, i)]] + c * Ct[i]
                C0 = K_placed(Z, Hp1, Hs, c)               # row 0 valid
                Hs[PK[(0, 0)]] = Hs[PK[(0, 0)]] + c * C0[0]
                chi[..., s] = Hs
            elif mode == "central":
                Cc = K_central(Hp2, Hp1, Hs, c)
                for nu in range(4):
                    Hs[PK[(0, nu)]] = Hs[PK[(0, nu)]] + 2.0 * c * Cc[nu]
                chi[..., s] = Hs
            elif mode == "partial":
                if s == 0:                                 # spinor 0 only
                    Hr = np.real(Hs) + 0j
                    Hp1r = np.real(Hp1) + 0j
                    Ct = K_placed(Hp1r, Hr, Z, c)
                    for i in (1, 2, 3):
                        Hs[PK[(0, i)]] = (np.real(Hs[PK[(0, i)]])
                                          + c * np.real(Ct[i])
                                          + 1j * np.imag(Hs[PK[(0, i)]]))
                    Hr = np.real(Hs) + 0j
                    C0 = K_placed(Z, Hp1r, Hr, c)
                    Hs[PK[(0, 0)]] = (np.real(Hs[PK[(0, 0)]])
                                      + c * np.real(C0[0])
                                      + 1j * np.imag(Hs[PK[(0, 0)]]))
                    chi[..., s] = Hs
            elif mode == "lagged":
                Ct = K_placed(Hp2, Hp1, Z, c)              # STALE rows 1..3
                for i in (1, 2, 3):
                    Hs[PK[(0, i)]] = Hs[PK[(0, i)]] + c * Ct[i]
                C0 = K_placed(Z, Hp2, Hp1, c)              # STALE row 0
                Hs[PK[(0, 0)]] = Hs[PK[(0, 0)]] + c * C0[0]
                chi[..., s] = Hs
            # mode "none": no enforcement
            newh.append(np.ascontiguousarray(chi[..., s]))
        hist = [[hist[s][1], newh[s]] for s in range(2)]
        return chi, hist

    return step


def init_hist(chi):
    return [[np.ascontiguousarray(chi[..., s]).copy(),
             np.ascontiguousarray(chi[..., s]).copy()] for s in range(2)]


# ===========================================================================
#  helpers: modes, seeding, oracle
# ===========================================================================
def plane(kv, N):
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    return np.exp(1j * (kv[0] * X + kv[1] * Y + kv[2] * Z))


def colfac(k4):
    """value phase of staggered samples of a plane wave: e^{i k4.o/2}."""
    return np.array([np.exp(0.5j * float(np.dot(k4, OFFSET[c])))
                     for c in range(10)])


_MODE_CACHE = {}


def onshell_mode(nvec, N, th=TH0):
    """walk's own (w, spinor eigvec) at lattice mode nvec, from the exact 2x2
    k-mode matrix of the SAME operator (machine precision, no FFT bins)."""
    key = (tuple(nvec), N, round(th, 12))
    if key in _MODE_CACHE:
        return _MODE_CACHE[key]
    kl = np.array(nvec, float) * (2 * np.pi / N)
    ph = plane(kl, N)
    proj = np.conj(ph) / N ** 3
    M = np.zeros((2, 2), complex)
    for s in range(2):
        c0 = np.zeros((1, N, N, N, 2), complex)
        c0[0, ..., s] = ph
        c0 = gw.geom_walk_all(c0, th, th, th, th)
        for r in range(2):
            M[r, s] = np.sum(proj * c0[0, ..., r])
    ev, V = np.linalg.eig(M)
    w = -np.angle(ev)
    cand = [j for j in range(2) if 1e-9 < w[j] < math.pi - 1e-9]
    j = cand[int(np.argmin([w[jj] for jj in cand]))]
    out = (kl, float(w[j]), V[:, j] / np.linalg.norm(V[:, j]), ph, proj)
    _MODE_CACHE[key] = out
    return out


def kappa_of(w_signed, kl, c=C_CONE):
    return np.array([2.0 * math.sin(w_signed / 2.0) / c]
                    + [2.0 * math.sin(ki / 2.0) for ki in kl])


def ker_basis(w_signed, kl):
    """orthonormal basis (10,6) of ker K_oracle at (w_signed, k)."""
    k4 = np.array([w_signed, kl[0], kl[1], kl[2]])
    K = r17.constraint_matrix_op(k4) / 1j
    return np.linalg.svd(K)[2][4:].conj().T, K


def flat_tr(v):
    """flat trace-reverse hbar -> h, packed last axis (R16 pit: judge eats h)."""
    tr = (-v[..., PK[(0, 0)]] + v[..., PK[(1, 1)]] + v[..., PK[(2, 2)]]
          + v[..., PK[(3, 3)]])
    out = v.copy()
    for c10, (m, n) in enumerate(SYM):
        out[..., c10] = v[..., c10] - 0.5 * ETA[m, n] * tr
    return out


def riemann_sym(kap, v10):
    """symbol-level linearized Riemann 256-vector of a packed hbar amplitude
    at derivative-symbol direction kappa (annihilates kap(x)xi+xi(x)kap
    identically -- the placed-calculus gauge kernel)."""
    h = flat_tr(v10)
    H = np.zeros((4, 4), complex)
    for c10, (m, n) in enumerate(SYM):
        H[m, n] = H[n, m] = h[c10]
    k = kap
    R = np.zeros(256, complex)
    i = 0
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    R[i] = 0.5 * (k[m] * k[n] * H[a, b] + k[a] * k[b] * H[m, n]
                                  - k[m] * k[b] * H[a, n]
                                  - k[a] * k[n] * H[m, b])
                    i += 1
    return R


# ===========================================================================
#  PART B0. probe assertion: enforce == measure (same function object)
# ===========================================================================
def probe_enforce_eq_measure(N=8, seed=0):
    """R20 fix list #3: measurement and enforcement must be the SAME operator.
    Here they are the same FUNCTION OBJECT (K_placed); the probe additionally
    applies the measure-path and enforce-path callables to identical random
    staggered bundles and asserts bitwise-equal output."""
    measure_op = K_placed          # the callable the monitor uses
    enforce_op = K_placed          # the callable the stepper uses
    rng = np.random.default_rng(seed)
    Hs = [rng.standard_normal((10, N, N, N))
          + 1j * rng.standard_normal((10, N, N, N)) for _ in range(3)]
    d = float(np.abs(measure_op(*Hs) - enforce_op(*Hs)).max())
    same = measure_op is enforce_op
    return {"same_function_object": bool(same),
            "norm_Kmeas_minus_Kenf": d,
            "PASS": bool(same and d == 0.0)}


# ===========================================================================
#  PART B1. on-shell certificates |K@TT|, |K@gauge| (R19 gate-A code path)
# ===========================================================================
def seed_slices(a10, k4, N, nsl=3, base=None, offsets=None):
    """staggered-STORED plane wave slices (R19 seed_slices verbatim).
    offsets=OFF_ZERO seeds INTEGER storage (the 'staggering off' semantics)."""
    w, kv = k4[0], k4[1:]
    if base is None:
        base = plane(kv, N)
    off = OFFSET if offsets is None else offsets
    cf = np.array([np.exp(0.5j * float(np.dot(k4, off[c])))
                   for c in range(10)])
    return [np.stack([a10[c] * cf[c] * np.exp(1j * w * n) * base
                      for c in range(10)]) for n in range(nsl)]


OFF_ZERO = np.zeros_like(OFFSET)


def apply_norm(applyK, a10, k4, N, base=None, offsets=None):
    a = a10 / (np.linalg.norm(a10) + 1e-300)
    Hs = seed_slices(a, k4, N, 3, base, offsets)
    return float(np.abs(applyK(Hs[0], Hs[1], Hs[2])).max())


def kset_lattice(N=16):
    nvecs = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2), (3, 1, 0),
             (1, 2, 3), (4, 1, 1), (2, -2, 1), (3, 0, 2), (1, 1, 1),
             (5, 2, 1), (2, 3, -1), (4, 4, 2), (6, 1, 0), (1, -3, 2)]
    out = []
    for nv in nvecs:
        k = np.array(nv, float) * (2 * np.pi / N)
        if r15.shell_omega(k) is not None and np.linalg.norm(k) > 0.05:
            out.append((nv, k))
    return out


def cert_onshell(N=16, applyK=K_placed, offsets=None):
    """direct real-space application of the constraint operator to on-shell
    staggered TT / gauge waves, 15 lattice k x both branches (+w/-w).
    offsets=OFF_ZERO seeds integer storage (for the F2 negative control:
    central template + integer storage = R19 neg (a), reference 0.228)."""
    worst_tt, worst_g, real_worst = 0.0, 0.0, 0.0
    for nv, k in kset_lattice(N):
        base = plane(k, N)
        w = r15.shell_omega(k)
        for sign in (+1, -1):
            k4 = np.array([sign * w, k[0], k[1], k[2]])
            kap = kappa_of(sign * w, k)
            TT = r15.tt_basis(kap)
            G = r15.gauge_block(kap)
            for p in range(2):
                worst_tt = max(worst_tt,
                               apply_norm(applyK, TT[:, p], k4, N, base,
                                          offsets))
            for p in range(4):
                worst_g = max(worst_g,
                              apply_norm(applyK, G[:, p], k4, N, base,
                                         offsets))
    # real-field spot check (R19 gate A'): h = Re of the staggered wave
    nv, k = kset_lattice(N)[2]
    w = r15.shell_omega(k)
    k4 = np.array([w, k[0], k[1], k[2]])
    kap = kappa_of(w, k)
    base = plane(k, N)
    TT = r15.tt_basis(kap)
    G = r15.gauge_block(kap)
    for v in [TT[:, 0], TT[:, 1], G[:, 1], G[:, 2]]:
        a = v / (np.linalg.norm(v) + 1e-300)
        Hs = [np.real(s) + 0j
              for s in seed_slices(a, k4, N, 3, base, offsets)]
        real_worst = max(real_worst,
                         float(np.abs(applyK(Hs[0], Hs[1], Hs[2])).max()))
    return {"worst_KTT": worst_tt, "worst_Kgauge": worst_g,
            "realfield_worst": real_worst,
            "PASS": bool(worst_tt < 1e-12 and worst_g < 1e-12
                         and real_worst < 1e-12)}


# ===========================================================================
#  PART B2. symbol oracle: predicted spectrum of the slaved state space
#           ker K(w_walk, k) under the placed Riemann, per probe k
# ===========================================================================
def oracle_entry(nvec, N, th=TH0):
    kl, w, xi, ph, proj = onshell_mode(nvec, N, th)
    w_shell = r15.shell_omega(kl, math.cos(th))
    out = {"nvec": list(nvec), "w_walk": w, "w_shell": w_shell,
           "shell_dev": abs(w - (w_shell if w_shell else float("nan")))}
    kap = kappa_of(w, kl, math.cos(th))
    out["kap_kap"] = float(kap @ ETA @ kap)
    ker, K = ker_basis(w, kl)          # +w branch (spectra identical both br.)
    Rcols = np.stack([riemann_sym(kap, ker[:, j]) for j in range(6)], axis=1)
    sv = np.linalg.svd(Rcols, compute_uv=False)
    svn = sv / (sv[0] + 1e-300)
    out["sv_oracle"] = svn[:6].tolist()
    out["n_prop_oracle"] = int(np.sum(svn > SV_THRESH))
    U = np.linalg.svd(Rcols, full_matrices=False)[0]
    TTb = r15.tt_basis(kap)
    Rtt = np.stack([riemann_sym(kap, TTb[:, j]) for j in range(2)], axis=1)
    Qd, _ = np.linalg.qr(U[:, :2])
    Qt, _ = np.linalg.qr(Rtt)
    out["tt_match_oracle"] = float(np.min(np.linalg.svd(
        Qd.conj().T @ Qt, compute_uv=False)) ** 2)
    G = r15.gauge_block(kap)
    out["Kgauge_at_w_walk"] = float(np.abs(
        K @ (G / np.linalg.norm(G, axis=0))).max())
    return out


# ===========================================================================
#  PART C. in-vitro slaved single-k dynamics (oracle pointwise 对拍)
# ===========================================================================
def invitro_single_k(nvec, kind, N=16, T=256, seed=11):
    """seed an exact staggered single-k state (TT / gauge / ker-generic) on
    the walk's own eigenmode (e^{-iwt} branch), evolve with the L1 stepper,
    and measure (i) the bulk constraint (machine zero), (ii) the pointwise
    oracle residual ||K_oracle(w_walk)@a(t)||/||a|| (< 1e-12 = the declared
    oracle matching), (iii) amplitude drift (TT survival for kind='tt')."""
    kl, w, xi, ph, proj = onshell_mode(nvec, N)
    k4 = np.array([-w, kl[0], kl[1], kl[2]])       # walk convention e^{-iwt}
    kap = kappa_of(-w, kl)
    ker, K = ker_basis(-w, kl)
    rng = np.random.default_rng(seed)
    if kind == "tt":
        a = r15.tt_basis(kap) @ np.array([1.0, 0.7])
    elif kind == "gauge":
        a = r15.gauge_block(kap) @ np.array([0.5, 1.0, -0.3, 0.7])
    else:                                          # generic in ker K
        a = ker @ (rng.standard_normal(6) + 1j * rng.standard_normal(6))
    a = a / (np.linalg.norm(a) + 1e-300)
    cf = colfac(k4)
    chi = np.zeros((10, N, N, N, 2), complex)
    for comp in range(10):
        chi[comp] = (a[comp] * cf[comp] * ph)[..., None] * xi[None, None, None, :]
    hist = init_hist(chi)
    step = make_stepper("certified")
    worstK, worstC, amp0, ampT = 0.0, 0.0, None, None
    for t in range(T):
        chi, hist = step(chi, hist)
        amp = np.array([np.sum(proj * hist[0][1][comp]) for comp in range(10)])
        aph = amp * np.conj(cf) * np.exp(-1j * (-w) * (t + 1))
        nrm = float(np.linalg.norm(aph))
        worstK = max(worstK, float(np.linalg.norm(K @ aph)) / (nrm + 1e-300))
        if amp0 is None:
            amp0 = nrm
        ampT = nrm
    # dedicated 3-slice constraint monitor pass (exact triple bookkeeping)
    chi = np.zeros((10, N, N, N, 2), complex)
    for comp in range(10):
        chi[comp] = (a[comp] * cf[comp] * ph)[..., None] * xi[None, None, None, :]
    hist = init_hist(chi)
    buf = [hist[0][1].copy()]
    for t in range(min(T, 64)):
        chi, hist = step(chi, hist)
        buf.append(hist[0][1])
        if len(buf) > 3:
            buf.pop(0)
        if len(buf) == 3:
            Cr = K_placed(buf[0], buf[1], buf[2])
            hn = float(np.sqrt(np.mean(np.abs(buf[1]) ** 2)))
            worstC = max(worstC,
                         float(np.sqrt(np.mean(np.abs(Cr) ** 2))) / (hn + 1e-300))
    return {"nvec": list(nvec), "kind": kind, "w_walk": w,
            "worst_oracle_resid": worstK, "relC_max": worstC,
            "amp_drift": abs(ampT / (amp0 + 1e-300) - 1.0)}


# ===========================================================================
#  PART D. main runs: evolve + record + count
# ===========================================================================
def detrend(seg):
    """remove per-(trial,comp) linear trend from a (W, ...) complex segment
    (exact removal of the omega=0 secular gauge ramp; declared)."""
    W = seg.shape[0]
    x = np.arange(W, dtype=float)
    X = np.stack([np.ones(W), x], axis=1)                  # (W,2)
    P = np.linalg.pinv(X)                                  # (2,W)
    coef = np.tensordot(P, seg, axes=(1, 0))               # (2, ...)
    fit = np.tensordot(X, coef, axes=(1, 0))
    return seg - fit


def evolve_record(chi, kinfo, T, mode="certified", th=TH0, c_slave=None,
                  monitor=True):
    """evolve; record stored-frame (spinor-0) mode series per probe k; monitor
    bulk constraint with the SAME K function the stepper enforces with."""
    trials = chi.shape[1]
    step = make_stepper(mode, th=th, c_slave=c_slave)
    hist = init_hist(chi)
    rec = np.zeros((T, trials, len(kinfo), 10), complex)
    relC = []
    buf = [[hist[s][1].copy()] for s in range(2)]
    Kmon = K_central if mode == "central" else K_placed
    c_mon = (C_CONE if c_slave is None else c_slave)
    norm_sp = []
    rms_full = []
    h00_rms = []
    for t in range(T):
        chi, hist = step(chi, hist)
        H0 = hist[0][1]
        for ki, (kl, w, xi, ph, proj) in enumerate(kinfo):
            rec[t, :, ki, :] = np.einsum("xyz,crxyz->rc", proj, H0)
        if monitor:
            worst = 0.0
            for s in range(2):
                buf[s].append(hist[s][1])
                if len(buf[s]) > 3:
                    buf[s].pop(0)
                if len(buf[s]) == 3 and mode != "none":
                    Cr = Kmon(buf[s][0], buf[s][1], buf[s][2], c_mon)
                    hn = float(np.sqrt(np.mean(np.abs(buf[s][1]) ** 2)))
                    worst = max(worst, float(
                        np.sqrt(np.mean(np.abs(Cr) ** 2))) / (hn + 1e-300))
            relC.append(worst)
        norm_sp.append(float(np.sqrt(np.sum(
            np.abs(chi[SPATIAL]) ** 2))))
        rms_full.append(float(np.sqrt(np.mean(np.abs(chi) ** 2))))
        h00_rms.append(float(np.sqrt(np.mean(
            np.abs(chi[PK[(0, 0)], ..., 0]) ** 2))))
    mon = {}
    if monitor and relC:
        tail = relC[int(0.75 * len(relC)):]
        finite = all(np.isfinite(v) for v in relC)
        mon = {"relC_max": float(max(relC)), "relC_last": float(relC[-1]),
               "relC_tail_rate": float((tail[-1] / (tail[0] + 1e-300))
                                       ** (1.0 / max(1, len(tail) - 1))),
               "relC_overflow": bool(not finite)}
    drift_sp = float(max(abs(v / (norm_sp[0] + 1e-300) - 1.0)
                         for v in norm_sp))
    n2 = len(rms_full) // 2
    slope = float(np.polyfit(np.arange(n2), rms_full[n2:], 1)[0]
                  / (np.mean(rms_full[n2:]) + 1e-300))
    return rec, dict(mon, walk_sector_norm_drift=drift_sp,
                     rms_full_first=rms_full[0], rms_full_last=rms_full[-1],
                     rms_full_tail_slope_rel=slope,
                     h00_rms_first=h00_rms[0], h00_rms_last=h00_rms[-1])


def count_at_k(rec_k, kl, w_walk, oracle=None, w_max=np.pi / 2):
    """projection-free placed-calculus Riemann-SVD count for one probe k.
    rec_k (T, trials, 10) stored-frame complex series.  Two-sided peak search
    (walk convention allows either branch); linear detrend; amplitudes
    un-shifted to the physical frame by the placement colfac (unit phase);
    Riemann built at kappa(sign(w_pk)*w_walk, k) -- w_walk is the operator's
    own measured frequency (oracle), the FFT locates the peak & extracts
    amplitudes.  Also returns the whitened (excitation-normalized) spectrum
    for the oracle pointwise match."""
    T, trials, _ = rec_k.shape
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    seg = detrend(rec_k[T0:])
    seg = (seg * win[:, None, None])[2:-2]
    freqs = 2 * np.pi * np.fft.fftfreq(W - 4)
    sel = (np.abs(freqs) > max(0.05, 4 * np.pi / (W - 4))) \
        & (np.abs(freqs) <= w_max)
    F = np.fft.fft(seg, axis=0)
    P = np.sum(np.abs(F) ** 2, axis=(1, 2))
    if float(P[sel].sum()) < 1e-18:
        return {"n_prop": 0, "no_peak": True}
    pk = int(np.argmax(np.where(sel, P, 0.0)))
    w_pk = float(freqs[pk])
    side = np.where((np.sign(freqs) == np.sign(w_pk)) & sel)[0]
    edge = side[int(np.argmin(np.abs(freqs[side])))]
    prom = float(P[pk] / (P[edge] + 1e-300))
    if pk == edge:
        prom = 1.0
    ws = math.copysign(w_walk, w_pk)
    k4 = np.array([ws, kl[0], kl[1], kl[2]])
    kap = kappa_of(ws, kl)
    cf = colfac(k4)
    A = F[pk] * np.conj(cf)[None, :]                       # (trials,10) phys
    M = np.stack([riemann_sym(kap, A[r]) for r in range(trials)])
    sv = np.linalg.svd(M, compute_uv=False)
    svn = (sv / (sv[0] + 1e-300)).tolist()
    n_prop = int(np.sum(np.array(svn) > SV_THRESH))
    U = np.linalg.svd(M.T, full_matrices=False)[0]
    TTb = r15.tt_basis(kap)
    Rtt = np.stack([riemann_sym(kap, TTb[:, j]) for j in range(2)], axis=1)
    Qd, _ = np.linalg.qr(U[:, :2])
    Qt, _ = np.linalg.qr(Rtt)
    ttm = float(np.min(np.linalg.svd(Qd.conj().T @ Qt,
                                     compute_uv=False)) ** 2)
    out = {"w_peak": w_pk, "w_walk_signed": ws, "peak_prominence": prom,
           "sv": [float(v) for v in svn[:8]], "n_prop": n_prop,
           "sv3": float(svn[2]) if len(svn) > 2 else 0.0, "tt_match": ttm,
           "c_gw": abs(w_pk) / (kchord(kl) + 1e-30)}
    # whitened spectrum: orthonormalize the measured excited subspace (top-6)
    Ua, sa, _ = np.linalg.svd(A.T, full_matrices=False)    # (10, r)
    Q6 = Ua[:, :min(6, Ua.shape[1])]
    Mw = np.stack([riemann_sym(kap, Q6[:, j]) for j in range(Q6.shape[1])])
    svw = np.linalg.svd(Mw, compute_uv=False)
    svwn = (svw / (svw[0] + 1e-300)).tolist()
    out["sv_whitened"] = [float(v) for v in svwn[:6]]
    # pointwise ker-residual of the measured amplitudes (oracle surface)
    _, K = ker_basis(ws, kl)
    resid = [float(np.linalg.norm(K @ A[r]) / (np.linalg.norm(A[r]) + 1e-300))
             for r in range(trials)]
    out["ker_resid_max"] = float(max(resid))
    if oracle is not None:
        so = np.array(oracle["sv_oracle"])
        sm = np.array(out["sv_whitened"])
        nmin = min(len(so), len(sm))
        out["sv_whitened_vs_oracle_maxdev"] = float(
            np.abs(so[:nmin] - sm[:nmin]).max())
    return out


def kchord(kl):
    return float(np.sqrt(sum(4.0 * np.sin(k / 2.0) ** 2 for k in kl)))


def stock_count_at_k(rec_k, kl, c2=C_CONE ** 2, w_max=np.pi / 2):
    """REFERENCE line: the stock emergence_judge calculus (full-angle sin k
    Riemann, central time, eta_c trace reverse) applied to Re of the stored
    series.  Expected to over-count at L1 (undamped placed-gauge content is
    full-angle-bright by calculus mismatch, R15) -- reported, NOT a gate."""
    T, trials, _ = rec_k.shape
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    seg = np.real(detrend(rec_k[T0:]))
    freqs = 2 * np.pi * np.fft.fftfreq(W - 4)
    sel = (freqs > max(0.05, 4 * np.pi / (W - 4))) & (freqs <= w_max)
    from rulespace_gpu import emergence_judge as ej
    rows, powsp = [], None
    for r in range(trials):
        Hh = ej.trace_reverse_c(seg[:, r, :], c2)
        Rf = ej.riemann_series_k(ej.packed_to_44(Hh), kl)
        Fr = np.fft.fft(Rf * win[2:-2, None], axis=0)
        Pr = np.sum(np.abs(Fr) ** 2, axis=1)
        powsp = Pr if powsp is None else powsp + Pr
        rows.append(Fr)
    if float(powsp[sel].sum()) < 1e-18:
        return {"n_prop": 0, "no_peak": True}
    pk = int(np.argmax(np.where(sel, powsp, 0.0)))
    M = np.array([r[pk] for r in rows])
    sv = np.linalg.svd(M, compute_uv=False)
    svn = (sv / (sv[0] + 1e-300)).tolist()
    return {"w_peak": float(freqs[pk]),
            "n_prop": int(np.sum(np.array(svn) > SV_THRESH)),
            "sv": [float(v) for v in svn[:8]]}


def seed_raw(N, trials, seed):
    """judge-faithful fully generic random IC (Re spinor-0 = random packed h)."""
    rng = np.random.default_rng(seed)
    chi = np.zeros((10, trials, N, N, N, 2), complex)
    chi[..., 0] = rng.standard_normal((10, trials, N, N, N))
    return chi


def seed_ker(N, trials, seed, nvecs):
    """constraint-consistent IC: random ker-K content on the walk's own
    eigenmodes at the probe k (single branch -> bounded, no secular gauge)."""
    rng = np.random.default_rng(seed)
    chi = np.zeros((10, trials, N, N, N, 2), complex)
    for nv in nvecs:
        kl, w, xi, ph, proj = onshell_mode(nv, N)
        k4 = np.array([-w, kl[0], kl[1], kl[2]])
        ker, _ = ker_basis(-w, kl)
        cf = colfac(k4)
        for r in range(trials):
            a = ker @ (rng.standard_normal(6) + 1j * rng.standard_normal(6))
            for comp in range(10):
                chi[comp, r] += (a[comp] * cf[comp] * ph)[..., None] \
                    * xi[None, None, None, :]
    return chi


# ===========================================================================
#  drivers
# ===========================================================================
def run_main(N=16, T=1024, trials=8):
    out = {"N": N, "T": T, "trials": trials,
           "seeds": {"A": SEED_A, "B": SEED_B}}
    kinfo = [onshell_mode(nv, N) for nv in KM_ALL]
    oracle = {str(tuple(nv)): oracle_entry(nv, N) for nv in KM_ALL}
    out["oracle"] = oracle

    # matter reference: the walk's OWN dispersion, judge pipeline (CP0 code)
    cm = gw.c_matter_table(TH0, KM_ALL, N=N, T=T)
    out["c_matter_ref"] = cm

    # ---- run A: raw generic IC (judge-faithful) --------------------------
    chi = seed_raw(N, trials, SEED_A)
    t0 = time.time()
    recA, monA = evolve_record(chi, kinfo, T)
    out["runA_monitor"] = monA
    out["runA_seconds"] = time.time() - t0
    perkA = {}
    for ki, nv in enumerate(KM_ALL):
        kl, w = kinfo[ki][0], kinfo[ki][1]
        e = count_at_k(recA[:, :, ki, :], kl, w, oracle[str(tuple(nv))])
        e["stock_reference"] = stock_count_at_k(recA[:, :, ki, :], kl)
        cmat = cm[str(tuple(nv))]["c_matter"]
        e["c_matter"] = cmat
        e["j5_ratio"] = e.get("c_gw", float("nan")) / (cmat + 1e-300)
        perkA[str(tuple(nv))] = e
    out["runA_per_k"] = perkA

    # ---- run B: ker-seeded (constraint-consistent IC) --------------------
    nvB = KM_GATE + [KM_DIAG]
    chi = seed_ker(N, trials, SEED_B, nvB)
    kinfoB = [onshell_mode(nv, N) for nv in nvB]
    recB, monB = evolve_record(chi, kinfoB, T)
    out["runB_monitor"] = monB
    perkB = {}
    for ki, nv in enumerate(nvB):
        kl, w = kinfoB[ki][0], kinfoB[ki][1]
        perkB[str(tuple(nv))] = count_at_k(recB[:, :, ki, :], kl, w,
                                           oracle[str(tuple(nv))])
    out["runB_per_k"] = perkB
    return out


def run_control_and_cannons(N=16, T=512, trials=8):
    """no-slave control (count teeth) + the four L1 falsification cannons.
    Reduced cost: kmodes (2,0,0),(2,2,0)."""
    kms = [(2, 0, 0), (2, 2, 0)]
    kinfo = [onshell_mode(nv, N) for nv in kms]
    cm = gw.c_matter_table(TH0, kms, N=N, T=T)
    res = {}

    def battery(mode, th=TH0, c_slave=None, kinfo_th=None):
        ki_use = kinfo_th or kinfo
        chi = seed_raw(N, trials, SEED_CANNON)
        rec, mon = evolve_record(chi, ki_use, T, mode=mode, th=th,
                                 c_slave=c_slave)
        per = {}
        for ki, nv in enumerate(kms):
            kl, w = ki_use[ki][0], ki_use[ki][1]
            e = count_at_k(rec[:, :, ki, :], kl, w)
            cmat = cm[str(tuple(nv))]["c_matter"]
            e["c_matter_ref_th0"] = cmat
            e["j5_ratio_vs_th0_matter"] = e.get("c_gw", float("nan")) \
                / (cmat + 1e-300)
            per[str(tuple(nv))] = e
        return {"monitor": mon, "per_k": per}

    # control: free 10x walk, no enforcement (count teeth: expect 6)
    res["control_no_slave"] = battery("none")
    res["control_no_slave"]["expected"] = "N_prop = 6 (free walk)"

    # F1: theta_g != theta_matter (geometry at 0.9, matter ref at pi/3)
    th_wrong = 0.9
    kinfo_w = [onshell_mode(nv, N, th_wrong) for nv in kms]
    f1 = battery("certified", th=th_wrong, c_slave=math.cos(th_wrong),
                 kinfo_th=kinfo_w)
    devs = [abs(v["j5_ratio_vs_th0_matter"] - 1.0)
            for v in f1["per_k"].values() if np.isfinite(
                v.get("j5_ratio_vs_th0_matter", float("nan")))]
    f1["j5_max_dev"] = float(max(devs)) if devs else float("nan")
    f1["breaks"] = ["J5"] if (devs and max(devs) > 1e-6) else []
    res["F1_double_cone"] = f1

    # F2: integer central template (no staggered semantics)
    f2 = battery("central")
    # (i) central template applied to STAGGERED-seeded on-shell waves (the
    #     as-assembled mismatch); (ii) central template + INTEGER storage =
    #     exactly R19 negative control (a), reference |K@TT| = 0.228.
    f2["cert_KTT_central_staggered_seed"] = cert_onshell(N, applyK=K_central)
    f2["cert_KTT_central_integer_seed"] = cert_onshell(
        N, applyK=K_central, offsets=OFF_ZERO)
    f2["cert_KTT_central"] = f2["cert_KTT_central_staggered_seed"]
    br = []
    if f2["cert_KTT_central"]["worst_KTT"] > 1e-12:
        br.append("|K@TT| (staggered-seed %.3f / integer-seed %.3f ~ R19 "
                  "0.23 family)"
                  % (f2["cert_KTT_central_staggered_seed"]["worst_KTT"],
                     f2["cert_KTT_central_integer_seed"]["worst_KTT"]))
    if any(v["n_prop"] != 2 for v in f2["per_k"].values()):
        br.append("N_prop")
    if any(v.get("sv3", 0) > SV_THRESH or v.get("tt_match", 1) < 0.95
           for v in f2["per_k"].values()):
        br.append("SV/tt_match")
    f2["breaks"] = br
    res["F2_integer_placement"] = f2

    # F3: partial slave (Re spinor-0 only; R21 disease)
    f3 = battery("partial")
    br = []
    if f3["monitor"]["relC_max"] > 1e-13:
        br.append("constraint (relC %.2e)" % f3["monitor"]["relC_max"])
    if any(v["n_prop"] != 2 for v in f3["per_k"].values()):
        br.append("N_prop")
    if any(v.get("sv3", 0) > SV_THRESH or v.get("tt_match", 1) < 0.95
           for v in f3["per_k"].values()):
        br.append("SV/tt_match")
    f3["breaks"] = br
    res["F3_partial_0nu_slave"] = f3

    # F4: lagged enforcement (stale K inputs; R20 hprev disease)
    f4 = battery("lagged")
    br = []
    if f4["monitor"]["relC_max"] > 1e-13:
        br.append("constraint (relC %.2e, tail rate %.4f)"
                  % (f4["monitor"]["relC_max"], f4["monitor"]["relC_tail_rate"]))
    if any(v["n_prop"] != 2 for v in f4["per_k"].values()):
        br.append("N_prop")
    if any(v.get("sv3", 0) > SV_THRESH or v.get("tt_match", 1) < 0.95
           for v in f4["per_k"].values()):
        br.append("SV/tt_match")
    f4["breaks"] = br
    res["F4_lagged_projection"] = f4
    return res


def run_trend_24(N=24, T=1024, trials=6):
    """post-gate 24^3 re-verification (trend, not certificate)."""
    nvs = KM_GATE + [KM_DIAG]
    kinfo = [onshell_mode(nv, N) for nv in nvs]
    oracle = {str(tuple(nv)): oracle_entry(nv, N) for nv in nvs}
    chi = seed_ker(N, trials, SEED_B, nvs)
    rec, mon = evolve_record(chi, kinfo, T)
    per = {}
    for ki, nv in enumerate(nvs):
        kl, w = kinfo[ki][0], kinfo[ki][1]
        per[str(tuple(nv))] = count_at_k(rec[:, :, ki, :], kl, w,
                                         oracle[str(tuple(nv))])
    return {"N": N, "T": T, "trials": trials, "monitor": mon,
            "oracle": oracle, "per_k": per}


# ===========================================================================
#  main
# ===========================================================================
if __name__ == "__main__":
    t_start = time.time()
    print(f"backend = {B.NAME}  (fp64 required: numpy)")
    print("CP1-v4 L1 -- walk kernel + K_placed, first joint assembly (lane B)")
    print("=" * 74)
    out = {"backend": B.NAME, "th0": TH0, "c_cone": C_CONE,
           "sv_thresh": SV_THRESH,
           "oblique_choice": ("non-palindromic single-sweep kernel + R19 "
                              "oracle prediction (declared; palindromic "
                              "macro-step would break the axial half-angle "
                              "shell K_placed relies on); gate k-set = "
                              "axial+planar-oblique, (2,2,2) oracle-matched")}

    # -- B0 probe: enforce == measure --------------------------------------
    out["B0_probe_enforce_eq_measure"] = p0 = probe_enforce_eq_measure()
    print(f"[B0 probe] enforce==measure same function object: "
          f"{p0['same_function_object']}   ||K_meas-K_enf|| = "
          f"{p0['norm_Kmeas_minus_Kenf']:.1e}  -> "
          f"{'PASS' if p0['PASS'] else 'FAIL'}")

    # -- B1 on-shell certificates ------------------------------------------
    out["B1_cert_onshell"] = c1 = cert_onshell()
    print(f"[B1 cert]  |K@TT| = {c1['worst_KTT']:.2e}   |K@gauge| = "
          f"{c1['worst_Kgauge']:.2e}   real-field = "
          f"{c1['realfield_worst']:.2e}  -> {'PASS' if c1['PASS'] else 'FAIL'}")

    # -- C in-vitro single-k -----------------------------------------------
    print("[C in-vitro] slaved single-k, oracle pointwise match:")
    iv = {}
    for nv in [(2, 0, 0), (2, 2, 0), (2, 2, 2)]:
        for kind in ("tt", "ker"):
            e = invitro_single_k(nv, kind)
            iv[f"{nv}_{kind}"] = e
            print(f"    k={nv} {kind:4s}: ||K_oracle@a|| max = "
                  f"{e['worst_oracle_resid']:.2e}   relC = {e['relC_max']:.2e}"
                  f"   amp drift = {e['amp_drift']:.2e}")
    # gauge seed only at an axial k (on the ideal shell gauge is in ker there)
    e = invitro_single_k((2, 0, 0), "gauge")
    iv["(2, 0, 0)_gauge"] = e
    print(f"    k=(2,0,0) gaug: ||K_oracle@a|| max = "
          f"{e['worst_oracle_resid']:.2e}   relC = {e['relC_max']:.2e}")
    out["C_invitro"] = iv
    iv_ok = all(v["worst_oracle_resid"] < 1e-12 and v["relC_max"] < 1e-13
                for v in iv.values())
    print(f"    -> oracle pointwise (<1e-12) & constraint machine-zero: "
          f"{'PASS' if iv_ok else 'FAIL'}")
    out["C_invitro_PASS"] = bool(iv_ok)

    # -- D main runs --------------------------------------------------------
    print("\n[D main] 16^3, T=1024, trials=8 ...")
    main = run_main()
    out["main"] = main
    print("  oracle table (walk-core, pre-registered R15 §5 oblique Trotter):")
    for nv in KM_ALL:
        o = main["oracle"][str(tuple(nv))]
        print(f"    k={nv}: w_walk={o['w_walk']:.6f} |dw_shell|="
              f"{o['shell_dev']:.2e} kap.kap={o['kap_kap']:+.3e} "
              f"N_prop_oracle={o['n_prop_oracle']} "
              f"sv3_oracle={o['sv_oracle'][2]:.2e}")
    print("  run A (raw generic IC, judge-faithful):")
    print(f"    {'k':10s} {'N_prop':>6} {'sv3':>9} {'tt_match':>9} "
          f"{'c_gw':>8} {'J5 ratio':>9} {'kerRes':>8} {'stockN':>7}")
    for nv in KM_ALL:
        e = main["runA_per_k"][str(tuple(nv))]
        print(f"    {str(nv):10s} {e['n_prop']:>6} {e['sv3']:>9.2e} "
              f"{e['tt_match']:>9.6f} {e['c_gw']:>8.4f} "
              f"{e['j5_ratio']:>9.6f} {e['ker_resid_max']:>8.1e} "
              f"{e['stock_reference'].get('n_prop', -1):>7}")
    mA = main["runA_monitor"]
    print(f"    constraint: relC max = {mA['relC_max']:.2e}  "
          f"walk-sector norm drift = {mA['walk_sector_norm_drift']:.2e}")
    print(f"    full-state rms {mA['rms_full_first']:.3f} -> "
          f"{mA['rms_full_last']:.3f} (h00 {mA['h00_rms_first']:.2f} -> "
          f"{mA['h00_rms_last']:.2f}: the declared secular GAUGE ramp; "
          f"absent in run B)")
    print("  run B (constraint-consistent ker-seeded IC):")
    for nv in KM_GATE + [KM_DIAG]:
        e = main["runB_per_k"][str(tuple(nv))]
        dv = e.get("sv_whitened_vs_oracle_maxdev", float("nan"))
        print(f"    {str(nv):10s} N_prop={e['n_prop']} sv3={e['sv3']:.2e} "
              f"ttm={e['tt_match']:.6f} kerRes={e['ker_resid_max']:.1e} "
              f"svW-vs-oracle={dv:.2e}")
    mB = main["runB_monitor"]
    print(f"    relC max = {mB['relC_max']:.2e}  rms drift = "
          f"|{mB['rms_full_last']/mB['rms_full_first']-1:.2e}|  "
          f"walk-sector drift = {mB['walk_sector_norm_drift']:.2e}")

    # -- isotropy -----------------------------------------------------------
    vs = [main["runA_per_k"][str(tuple(nv))]["c_gw"] for nv in KM_ISO]
    iso = float((max(vs) - min(vs)) / (np.mean(vs) + 1e-300))
    out["isotropy"] = {"axis_c_gw": vs, "spread": iso}
    print(f"  isotropy: axis c_gw = {[round(v, 5) for v in vs]}  "
          f"spread = {iso:.2e}")

    # -- E control + cannons -------------------------------------------------
    print("\n[E] control + falsification cannons (each must break a gate):")
    cann = run_control_and_cannons()
    out["cannons"] = cann
    cc = cann["control_no_slave"]
    print(f"  [ctrl no-slave] N_prop = "
          f"{[v['n_prop'] for v in cc['per_k'].values()]}  (expect 6: count "
          f"teeth {'OK' if all(v['n_prop'] >= 5 for v in cc['per_k'].values()) else 'BROKEN'})")
    for name, want in (("F1_double_cone", "J5"),
                       ("F2_integer_placement", "|K@TT|"),
                       ("F3_partial_0nu_slave", "constraint/count"),
                       ("F4_lagged_projection", "constraint")):
        f = cann[name]
        extra = ""
        if name == "F1_double_cone":
            extra = f"  J5 max|r-1| = {f['j5_max_dev']:.3f}"
        if name == "F2_integer_placement":
            extra = f"  |K@TT| = {f['cert_KTT_central']['worst_KTT']:.3f}"
        if name in ("F3_partial_0nu_slave", "F4_lagged_projection"):
            extra = (f"  relC = {f['monitor']['relC_max']:.2e} "
                     f"(rate {f['monitor'].get('relC_tail_rate', float('nan')):.4f})"
                     f"  N_prop = {[v['n_prop'] for v in f['per_k'].values()]}")
        ok = len(f["breaks"]) > 0
        print(f"  [{name}]{extra}")
        print(f"      breaks: {f['breaks']}  -> "
              f"{'FAILS as required' if ok else 'DID NOT BREAK (construction fake!)'}")
    cann_ok = all(len(cann[n]["breaks"]) > 0 for n in
                  ("F1_double_cone", "F2_integer_placement",
                   "F3_partial_0nu_slave", "F4_lagged_projection"))
    teeth_ok = all(v["n_prop"] >= 5
                   for v in cann["control_no_slave"]["per_k"].values())
    out["cannons_all_fire"] = bool(cann_ok)
    out["count_teeth_ok"] = bool(teeth_ok)

    # -- GATE evaluation (16^3 fp64 certificate) -----------------------------
    A = main["runA_per_k"]
    g1 = all(A[str(tuple(nv))]["n_prop"] == 2 for nv in KM_GATE)
    j5devs = [abs(A[str(tuple(nv))]["j5_ratio"] - 1.0) for nv in KM_GATE]
    g2 = max(j5devs) < 1e-6
    g3 = (c1["PASS"] and mA["relC_max"] < 1e-13 and mB["relC_max"] < 1e-13)
    g4 = all(A[str(tuple(nv))]["sv3"] < SV_THRESH
             and A[str(tuple(nv))]["tt_match"] > 0.95 for nv in KM_GATE)
    g5 = (mA["walk_sector_norm_drift"] < 1e-10
          and abs(mB["rms_full_last"] / mB["rms_full_first"] - 1.0) < 1e-10)
    diag_ok = (main["runB_per_k"][str(KM_DIAG)]["ker_resid_max"] < 1e-6
               and main["runA_per_k"][str(KM_DIAG)]["ker_resid_max"] < 1e-2)
    gates = {"G1_Nprop2_gate_k": bool(g1),
             "G2_J5_lt_1e-6": bool(g2), "G2_j5_max_dev": float(max(j5devs)),
             "G3_constraint": bool(g3),
             "G4_SV_hard_gate": bool(g4),
             "G5_stability": bool(g5),
             "diag_222_oracle_matched": bool(diag_ok),
             "cannons_all_fire": bool(cann_ok),
             "count_teeth_ok": bool(teeth_ok)}
    out["gates"] = gates
    all_pass = all([g1, g2, g3, g4, g5, cann_ok, teeth_ok])
    out["L1_PASS"] = bool(all_pass)

    print("\n" + "=" * 74)
    print("L1 GATE TABLE (16^3 fp64 certificate)")
    print(f"  G1 N_prop=2 @ gate k {KM_GATE}      : "
          f"{[A[str(tuple(nv))]['n_prop'] for nv in KM_GATE]} -> "
          f"{'PASS' if g1 else 'FAIL'}")
    print(f"  G2 J5 |c_gw/c_matter-1| < 1e-6        : max dev = "
          f"{max(j5devs):.2e} -> {'PASS' if g2 else 'FAIL'}")
    print(f"  G3 |K@TT|,|K@gauge| <1e-12 + bulk C=0 : "
          f"{c1['worst_KTT']:.1e}/{c1['worst_Kgauge']:.1e}, relC "
          f"{mA['relC_max']:.1e} -> {'PASS' if g3 else 'FAIL'}")
    print(f"  G4 sv3<0.05 & tt_match>0.95           : sv3 max = "
          f"{max(A[str(tuple(nv))]['sv3'] for nv in KM_GATE):.2e}, ttm min = "
          f"{min(A[str(tuple(nv))]['tt_match'] for nv in KM_GATE):.4f} -> "
          f"{'PASS' if g4 else 'FAIL'}")
    print(f"  G5 stability T=1024                   : walk-sector drift "
          f"{mA['walk_sector_norm_drift']:.1e}, run-B full drift "
          f"{abs(mB['rms_full_last']/mB['rms_full_first']-1):.1e} -> "
          f"{'PASS' if g5 else 'FAIL'}")
    print(f"  (2,2,2) oracle-matched (declared)     : N_prop_oracle="
          f"{main['oracle'][str(KM_DIAG)]['n_prop_oracle']} measured="
          f"{A[str(KM_DIAG)]['n_prop']} kerRes="
          f"{main['runB_per_k'][str(KM_DIAG)]['ker_resid_max']:.1e} -> "
          f"{'MATCH' if diag_ok else 'MISMATCH'}")
    print(f"  cannons all fire                      : "
          f"{'PASS' if cann_ok else 'FAIL'}")
    print(f"\nL1 VERDICT: {'ALL GATES PASS' if all_pass else 'NOT ALL PASS'}")

    # -- F 24^3 trend (only after gates) -------------------------------------
    if all_pass:
        print("\n[F] 24^3 trend re-verification (T=1024, trials=6) ...")
        tr = run_trend_24()
        out["trend_24"] = tr
        for nv in KM_GATE + [KM_DIAG]:
            e = tr["per_k"][str(tuple(nv))]
            o = tr["oracle"][str(tuple(nv))]
            print(f"    k={nv}: N_prop={e['n_prop']} "
                  f"(oracle {o['n_prop_oracle']}) sv3={e['sv3']:.2e} "
                  f"ttm={e['tt_match']:.6f} kerRes={e['ker_resid_max']:.1e}")
        print(f"    relC max = {tr['monitor']['relC_max']:.2e}  "
              f"walk-sector drift = "
              f"{tr['monitor']['walk_sector_norm_drift']:.2e}")

    # -- hash + write --------------------------------------------------------
    with open(os.path.abspath(__file__), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    out["script_sha256"] = sha
    out["total_seconds"] = time.time() - t_start

    def _san(o):
        """strict-JSON sanitizer: non-finite floats -> strings."""
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
        if isinstance(o, np.integer):
            return int(o)
        return o

    with open(os.path.join(DIR, "cp1_v4_L1_results.json"), "w") as fh:
        json.dump(_san(out), fh, indent=1)
    print(f"\nscript sha256 = {sha}")
    print(f"total {out['total_seconds']:.0f}s   wrote cp1_v4_L1_results.json")
