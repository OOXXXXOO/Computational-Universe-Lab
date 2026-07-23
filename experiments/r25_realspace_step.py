"""R25-E1: full real-space time-step and adjoint bridge for the R25
auxiliary-Wilson dynamic-symbol candidate (pre-M3 obstacle #1).

State layout (28 = 14+14 per chiral sector):
  h  = 10 packed normal-metric components (r15.SYM order 00,0x,0y,0z,
       xx,xy,xz,yy,yz,zz) + 4 auxiliary Wilson fields, integer time slice;
  pi = the leapfrog momentum on the half-integer time slice.
Spatial placement follows the R19 staggered *storage semantics* (component
(mu,nu) samples live at x+(e_mu+e_nu)/2 mod 1): staggering never enters the
evolution operator, which is placement-transparent -- every operator below is
a pure function of integer rolls (geom_walk_all axis sandwiches and
nearest-neighbour cosine stencils).  The R25 complex is built from the walk
Bloch scalars (a, b_i, r), not from fwd/bwd difference dictionaries, so no
placement phase appears anywhere; C1 certifies the identification against the
Laurent symbol that carries the whole R25 certificate chain.

One macro step (the R25-D1 candidate, mu from the frozen JSON):
  x -> F (I - mu K_state^dag K_state) x,
  F: h' = (1-a_W) h + pi,  pi' = -a_W h + pi,     a_W = 2 - tr U + r^2,
  K_state = [K0 + (1-a_W) K1, K1]  (8x28), K(z)=K0+z K1 the augmented
  auxiliary-Wilson constraint with z h_t replaced by the free proposal.
The adjoint bridge K_state^dag is exact (R20 discipline: enforce==measure,
probe-asserted).  All scalar building blocks (a, b_i from the SU(2) walk,
q/r Wilson) are Hermitian convolutions, so the adjoint is the conjugate
coefficient table over the same integer-roll monomials.

Mirror/reality pairing (R25 chiral complex stencil): the ordered-xyz sector
evolves with this step; the mirror sector evolves with the conjugated step
step_minus = conj . step . conj; h_minus = conj(h_plus) is preserved exactly
and the physical field is (h_plus + conj(h_plus))/2.

Interfaces left open for the next obstacles:
  step(..., drive=...)   -- source slot: drive enters the pi update, the h
                            update and the K_state proposal (obstacle #3);
  step(..., precond=...) -- pluggable local-stencil preconditioner acting on
                            the 8 constraint fields between K and K^dag
                            (obstacle #2; must itself be a local stencil).

Certificates C1-C5 are declared in main(); PASS means exactly those checks.
Run:  .venv/bin/python r25_realspace_step.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (DIR, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import sympy as sp                                    # noqa: E402
import matplotlib                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402

import cp1_v4_L2 as L2                                # noqa: E402
import cp1_v4_L3 as L3                                # noqa: E402
import r25_auxiliary_wilson_complex as R25W           # noqa: E402
import r25_dynamic_symbol as D1                       # noqa: E402
import r25_static_newton as R25N                      # noqa: E402
from rulespace_gpu import green_one_walk as gw        # noqa: E402


OUT = os.path.join(ROOT, "data", "results", "r25_realspace_step_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "r25_realspace_step.png")
NF = 14
NS = 2 * NF
TH = L2.TH
CC = sp.Rational(1, 2)          # == L2.C == 0.5 exactly (binary float)
SYMC = [(m, n) for m in range(4) for n in range(m, 4)]
KUV = np.array([-1.714143895700328, 0.0, -1.714143895700328])
SEED = 250731

with open(os.path.join(ROOT, "data", "results",
                       "r25_dynamic_symbol_results.json")) as _fh:
    _d1 = json.load(_fh)
MU = float(_d1["chosen"]["mu"])
D1_FULLBZ = _d1["full_BZ"]


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _json_default(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(f"not serializable: {type(o)}")


# ===========================================================================
#  PART A. symbolic coefficient tables (built once; z eliminated affinely)
# ===========================================================================
A_S, B1_S, B2_S, B3_S, R_S, Z_S = sp.symbols("a b1 b2 b3 r z")
VARS = (A_S, B1_S, B2_S, B3_S, R_S)
BV_S = (B1_S, B2_S, B3_S)
ETA_S = sp.diag(-1, 1, 1, 1)


def _unpack_s(v):
    H = sp.zeros(4, 4)
    for x, (m, n) in zip(v, SYMC):
        H[m, n] = H[n, m] = x
    return H


def build_symbolic():
    """Mirror of r25_auxiliary_wilson_complex.augmented_maps_at_z over the
    commuting scalars (a, b_i, r, z).  Certified against the frozen numeric
    constructors in oracle_bridge() -- any divergence fails C1 immediately."""
    kap = sp.Matrix([(Z_S - A_S) / CC, sp.I * B1_S / CC,
                     sp.I * B2_S / CC, sp.I * B3_S / CC])
    kup = ETA_S * kap
    G = sp.zeros(10, 4)
    for al in range(4):
        xi = sp.zeros(4, 1)
        xi[al] = 1
        M = kap * xi.T + xi * kap.T
        for c, (m, n) in enumerate(SYMC):
            G[c, al] = M[m, n]
    C = sp.zeros(4, 10)
    for j in range(10):
        v = [0] * 10
        v[j] = 1
        H = _unpack_s(v)
        trh = sum(ETA_S[m, m] * H[m, m] for m in range(4))
        bar = H - ETA_S * trh / 2
        for nu in range(4):
            C[nu, j] = sum(kup[m] * bar[m, nu] for m in range(4))
    Hs = sp.zeros(4, 10)
    for row, (i, j, hij, h0i, h0j) in enumerate(
            ((0, 1, 5, 1, 2), (0, 2, 6, 1, 3), (1, 2, 8, 2, 3))):
        Hs[row, hij] = 1 + A_S
        Hs[row, h0i] = sp.Rational(3, 4) * sp.I * BV_S[j]
        Hs[row, h0j] = sp.Rational(3, 4) * sp.I * BV_S[i]
    Hs[3, 0] = -3
    Hs[3, 4] = Hs[3, 7] = Hs[3, 9] = 1
    s = R_S / CC
    Cp = sp.Matrix.hstack(C, -Z_S * s * sp.eye(4))
    Dp = sp.Matrix.hstack(s * Hs, -(Hs * G))
    Kp = sp.Matrix.vstack(Cp, Dp)
    K0 = Kp.subs(Z_S, 0)
    K1 = sp.expand(Kp.subs(Z_S, 1) - K0)
    aw = 2 - 2 * A_S + R_S ** 2
    Kh = sp.expand(K0 + (1 - aw) * K1)
    return {"Kh": Kh, "Kpi": K1, "K1": K1}


def coeff_table(M):
    """8x14 sympy matrix -> {monomial exponent tuple: complex (8,14) array}."""
    rows, cols = M.shape
    tab = {}
    for i in range(rows):
        for j in range(cols):
            e = sp.expand(M[i, j])
            if e == 0:
                continue
            p = sp.Poly(e, *VARS)
            for mono, coef in zip(p.monoms(), p.coeffs()):
                if mono not in tab:
                    tab[mono] = np.zeros((rows, cols), complex)
                tab[mono][i, j] += complex(coef)
    return tab


_TABLES = None


def tables():
    global _TABLES
    if _TABLES is None:
        sym = build_symbolic()
        _TABLES = {name: coeff_table(m) for name, m in sym.items()}
        _TABLES["maxdeg_K"] = max(sum(m) for t in
                                  (_TABLES["Kh"], _TABLES["Kpi"])
                                  for m in t)
    return _TABLES


def eval_table(tab, k):
    """Numeric matrix of a coefficient table at momentum k (oracle bridge)."""
    U, tr, r, _ = R25W.walk_data(k)
    a = tr / 2
    b = [complex(1j * np.trace(s @ U) / 2) for s in R25W.PAULI_NUM]
    vals = (a, b[0], b[1], b[2], r)
    out = None
    for mono, A in tab.items():
        f = 1.0 + 0j
        for v, p in zip(vals, mono):
            f *= v ** p
        out = A * f if out is None else out + A * f
    return out


# ===========================================================================
#  PART B. real-space primitives (pure functions, integer rolls only)
# ===========================================================================
def walk_mult(f):
    """f (..., N,N,N) complex -> (a f, b1 f, b2 f, b3 f) via the frozen
    matter macro-walk entries (exactly r25_static_newton's a/b actions)."""
    q0 = np.zeros(f.shape + (2,), complex)
    q1 = np.zeros(f.shape + (2,), complex)
    q0[..., 0] = f
    q1[..., 1] = f
    u0 = gw.geom_walk_all(q0, TH, TH, TH, TH)
    u1 = gw.geom_walk_all(q1, TH, TH, TH, TH)
    u00, u10 = u0[..., 0], u0[..., 1]
    u01, u11 = u1[..., 0], u1[..., 1]
    return (0.5 * (u00 + u11), 0.5j * (u10 + u01),
            0.5 * (u10 - u01), 0.5j * (u00 - u11))


def q_op(f):
    """Wilson scalar q = (1/3) sum_i sin^2(k_i/2), radius one."""
    out = 0.5 * f
    for ax in (-3, -2, -1):
        out = out - (np.roll(f, 1, axis=ax) + np.roll(f, -1, axis=ax)) / 12.0
    return out


def r_op(f):
    return 0.5 * q_op(f)


def aw_op(f):
    """Wilson stiffness a_W = 2 - tr U + r^2, radius two."""
    af = walk_mult(f)[0]
    return 2.0 * f - 2.0 * af + r_op(r_op(f))


class MonoCache:
    """Shared-DAG application of scalar monomials a^p b^q r^u to a field."""

    def __init__(self, base):
        self.c = {(0, 0, 0, 0, 0): base}
        self.w = {}

    def get(self, m):
        m = tuple(m)
        if m in self.c:
            return self.c[m]
        i = next((i for i in range(4) if m[i] > 0), None)
        if i is None:
            p = m[:4] + (m[4] - 1,)
            arr = r_op(self.get(p))
        else:
            p = tuple(m[j] - (1 if j == i else 0) for j in range(5))
            if p not in self.w:
                self.w[p] = walk_mult(self.get(p))
            arr = self.w[p][i]
        self.c[m] = arr
        return arr


def _apply_fwd(tab, cache):
    out = None
    for m, A in tab.items():
        val = np.einsum("rc,c...->r...", A, cache.get(m))
        out = val if out is None else out + val
    return out


def _apply_adj(tab, cache):
    out = None
    for m, A in tab.items():
        val = np.einsum("rc,r...->c...", A.conj(), cache.get(m))
        out = val if out is None else out + val
    return out


def K_apply(h, pi, drive=None):
    """K_state x: (14,...),(14,...) -> (8,...); drive feeds the proposal."""
    T = tables()
    out = _apply_fwd(T["Kh"], MonoCache(h)) \
        + _apply_fwd(T["Kpi"], MonoCache(pi))
    if drive is not None:
        out = out + _apply_fwd(T["K1"], MonoCache(drive))
    return out


def K_adjoint(y):
    """Exact adjoint of K_apply's homogeneous part: (8,...) -> (14,...)x2."""
    T = tables()
    cache = MonoCache(y)
    return _apply_adj(T["Kh"], cache), _apply_adj(T["Kpi"], cache)


def step(h, pi, drive=None, precond=None, mu=MU):
    """One macro step F (I - mu K^dag P K), source-aware.  Pure function."""
    if mu:
        Kx = K_apply(h, pi, drive)
        if precond is not None:
            Kx = precond(Kx)
        dh, dpi = K_adjoint(Kx)
        h = h - mu * dh
        pi = pi - mu * dpi
    awh = aw_op(h)
    pin = pi - awh
    if drive is not None:
        pin = pin + drive
    return h + pin, pin


def step_minus(h, pi, **kw):
    """Mirror/conjugate sector step (reality pairing partner)."""
    hn, pin = step(np.conjugate(h), np.conjugate(pi), **kw)
    return np.conjugate(hn), np.conjugate(pin)


def adjoint_probe(N=6, trials=4, seed=SEED):
    """R20 discipline: enforce == measure.  <K x, y> vs <x, K^dag y>."""
    rng = np.random.default_rng(seed)
    worst = 0.0
    for _ in range(trials):
        h = rng.normal(size=(NF, N, N, N)) + 1j * rng.normal(size=(NF, N, N, N))
        pi = rng.normal(size=(NF, N, N, N)) + 1j * rng.normal(size=(NF, N, N, N))
        y = rng.normal(size=(8, N, N, N)) + 1j * rng.normal(size=(8, N, N, N))
        Kx = K_apply(h, pi)
        dh, dpi = K_adjoint(y)
        lhs = np.vdot(Kx, y)
        rhs = np.vdot(h, dh) + np.vdot(pi, dpi)
        worst = max(worst, abs(lhs - rhs) / max(abs(lhs), 1e-300))
    return worst


# ===========================================================================
#  PART C. certificates
# ===========================================================================
def batched_step(X, mu=MU, chunk=7):
    """X (28, B, N,N,N) -> stepped, chunked over the batch axis."""
    outs = []
    for lo in range(0, X.shape[1], chunk):
        h = X[:NF, lo:lo + chunk]
        pi = X[NF:, lo:lo + chunk]
        hn, pin = step(h, pi, mu=mu)
        outs.append(np.concatenate([hn, pin], axis=0))
    return np.concatenate(outs, axis=1)


def plane(kv, N):
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    return np.exp(1j * (kv[0] * X + kv[1] * Y + kv[2] * Z))


def cert_C1(N=16):
    """Symbol == real space on unit plane waves, all 28 sector components."""
    nvecs = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0), (2, 2, 2),
             (1, 1, 1), (8, 8, 3), (5, 7, 2), (1, 3, 5)]
    # oracle bridge at random k: symbolic tables vs frozen K_state
    rng = np.random.default_rng(SEED)
    T = tables()
    kworst = 0.0
    for _ in range(64):
        k = rng.uniform(-np.pi, np.pi, 3)
        mine = np.hstack([eval_table(T["Kh"], k), eval_table(T["Kpi"], k)])
        kworst = max(kworst, float(np.max(np.abs(mine - D1.K_state(k)))))
    rows, worst, offworst = [], 0.0, 0.0
    for nv in nvecs:
        k = 2 * np.pi * np.array(nv, float) / N
        ph = plane(k, N)
        X = np.zeros((NS, NS, N, N, N), complex)
        for j in range(NS):
            X[j, j] = ph
        Y = batched_step(X)
        amp = np.einsum("ijxyz,xyz->ij", Y, np.conj(ph)) / N ** 3
        off = float(np.max(np.abs(Y - amp[..., None, None, None] * ph)))
        Msym = D1.damped_map(k, MU)[0]
        diff = float(np.max(np.abs(amp - Msym)))
        rows.append({"index": list(nv), "max_abs_diff": diff,
                     "off_mode_leak": off})
        worst = max(worst, diff)
        offworst = max(offworst, off)
    return {"table_vs_frozen_K_state": kworst, "points": rows,
            "worst_diff": worst, "worst_off_mode": offworst}


def delta_response(N, mu=MU):
    """Columns of the step operator on a delta: the exact finite stencil."""
    X = np.zeros((NS, NS, N, N, N), complex)
    for j in range(NS):
        X[j, j, 0, 0, 0] = 1.0
    return batched_step(X, mu=mu)      # [out_comp, in_comp, x, y, z]


def cert_C2(N=16):
    """Full-BZ spectrum of the real-space step operator (via FFT of the
    delta response, exact by translation invariance)."""
    G = delta_response(N)
    Mk = np.fft.fftn(G, axes=(2, 3, 4))
    unitsets, worst, rate = set(), 0.0, 0.0
    worst_idx = None
    rate_idx = None
    moduli_map = np.zeros((N, N, N))
    for idx in np.ndindex(N, N, N):
        M = Mk[:, :, idx[0], idx[1], idx[2]]
        eig = np.linalg.eigvals(M)
        if idx == (0, 0, 0):
            zero_units, zero_max, _ = D1.unit_census(eig)
            continue
        units, mx, rr = D1.unit_census(eig)
        unitsets.add(units)
        if mx > worst:
            worst, worst_idx = mx, idx
        if rr > rate:
            rate, rate_idx = rr, idx
        moduli_map[idx] = rr
    return {"N": N, "unit_counts": sorted(unitsets), "max_modulus": worst,
            "worst_index": list(worst_idx),
            "slowest_contracting": rate,
            "slowest_index": list(rate_idx),
            "k0_unit_count": zero_units, "k0_max_modulus": zero_max,
            "symbol_reference": D1_FULLBZ}, moduli_map


def trace_reverse_packed(v):
    """Packed 10-vector (or (10,...) field) trace reversal, eta=-+++."""
    tr = -v[0] + v[4] + v[7] + v[9]
    out = v.copy()
    out[0] = v[0] + 0.5 * tr
    out[4] = v[4] - 0.5 * tr
    out[7] = v[7] - 0.5 * tr
    out[9] = v[9] - 0.5 * tr
    return out


def cert_C3(N=24, sig=2.5, T=64):
    """Static Newton in real space + sourced fixed point of *this* step."""
    rho = R25N.gaussian_lump(N, sig)
    rho_zm = rho - rho.mean()
    hb, drive_hb, aw = R25N.static_field_local(rho_zm)
    hb_phys = 0.5 * (hb + np.conjugate(hb))
    cn = L3.canary_numbers(hb_phys.real, rho, sig)
    # normal-h equilibrium and 14-component augmented drive
    h_eq = np.concatenate([trace_reverse_packed(hb),
                           np.zeros((4, N, N, N), complex)])
    drive = np.concatenate([trace_reverse_packed(drive_hb),
                            np.zeros((4, N, N, N), complex)])
    scale = float(np.max(np.abs(drive)))
    # real-space stiffness stencil reproduces the FFT equilibrium
    bridge = float(np.max(np.abs(aw_op(h_eq) - drive)) / scale)
    # constraint darkness of the sourced equilibrium state
    dark = float(np.max(np.abs(K_apply(h_eq, np.zeros_like(h_eq),
                                       drive=drive))) / scale)
    # damped sourced step keeps the equilibrium fixed
    h, pi = h_eq.copy(), np.zeros_like(h_eq)
    href = float(np.max(np.abs(h_eq)))
    drift_trace = []
    for _ in range(T):
        h, pi = step(h, pi, drive=drive)
        drift_trace.append(float(np.max(np.abs(h - h_eq)) / href))
    return {"N": N, "sigma": sig, "canary": cn,
            "aw_stencil_vs_fft_equilibrium": bridge,
            "constraint_darkness_rel": dark,
            "fixed_point_T": T, "fixed_point_drift": drift_trace[-1],
            "fixed_point_drift_max": max(drift_trace),
            "reference": {"ratio_A_D0": 2.0, "tail_D0": 0.9994036640771159}}, \
        drift_trace


def leapfrog_energy(h, pi):
    """Exact quadratic invariant of the free step (A=a_W self-adjoint):
    Q = <pi,pi> + <h,A h> - Re<A h, pi>."""
    awh = aw_op(h)
    return float(np.vdot(pi, pi).real + np.vdot(h, awh).real
                 - np.vdot(awh, pi).real)


def cert_C4(N=16, T=2048, seed=SEED):
    """Stability sector is declared ZERO-MEAN, matching the dynamic-symbol
    certificate which excludes k=(0,0,0): at k=0 the free map is the exact
    defective Jordan pair [[1,1],[0,1]] (a_W(0)=0; the translation/Newton
    zero-mode carrier), so a constant-pi offset drifts linearly by
    construction -- registered below as the exact law h_t=h_0+t*pi_0, and
    excluded from dynamics by the same zero-mean discipline the source side
    already uses (rho_zm in D0/C3).  All convolutions preserve the k=0
    sector, so removing the mean at t=0 removes it for all t."""
    rng = np.random.default_rng(seed)
    h0 = rng.normal(size=(NF, N, N, N)) + 1j * rng.normal(size=(NF, N, N, N))
    pi0 = rng.normal(size=(NF, N, N, N)) + 1j * rng.normal(size=(NF, N, N, N))
    h0 -= h0.mean(axis=(-3, -2, -1), keepdims=True)
    pi0 -= pi0.mean(axis=(-3, -2, -1), keepdims=True)
    # registered zero-mode law (free map): constant fields obey h_t=h0+t*pi0
    hz = np.ones((NF, 4, 4, 4), complex)
    pz = 1j * np.ones((NF, 4, 4, 4), complex)
    hj, pj = hz.copy(), pz.copy()
    for _ in range(16):
        hj, pj = step(hj, pj, mu=0.0)
    k0_jordan = float(max(np.max(np.abs(hj - (hz + 16 * pz))),
                          np.max(np.abs(pj - pz))))
    # C4a: free step conserves the leapfrog energy to fp64 floor
    h, pi = h0.copy(), pi0.copy()
    Q0 = leapfrog_energy(h, pi)
    qdrift, qtrace = 0.0, []
    for t in range(T):
        h, pi = step(h, pi, mu=0.0)
        if t % 16 == 15:
            Q = leapfrog_energy(h, pi)
            qtrace.append(Q)
            qdrift = max(qdrift, abs(Q - Q0) / abs(Q0))
    # C4b: damped run bounded; ||Kx|| decay = contraction-rate baseline
    h, pi = h0.copy(), pi0.copy()
    norms, knorms = [], []
    for t in range(T):
        Kx = K_apply(h, pi)
        dh, dpi = K_adjoint(Kx)
        h1 = h - MU * dh
        pi1 = pi - MU * dpi
        awh = aw_op(h1)
        pi = pi1 - awh
        h = h1 + pi
        knorms.append(float(np.linalg.norm(Kx)))
        norms.append(float(np.sqrt(np.linalg.norm(h) ** 2
                                   + np.linalg.norm(pi) ** 2)))
    n0 = float(np.sqrt(np.linalg.norm(h0) ** 2 + np.linalg.norm(pi0) ** 2))
    blocks = [max(norms[i:i + 64]) for i in range(0, T, 64)]
    lat = np.log(np.array(blocks[len(blocks) // 2:]))
    slope = float(np.polyfit(np.arange(lat.size) * 64.0, lat, 1)[0])
    mean_ratio = float(np.mean(norms[T - 512:]) / np.mean(norms[:512]))
    rate_late = float((knorms[-1] / knorms[-513]) ** (1.0 / 512.0))
    # negative control: anti-damping must inject energy (instrument check)
    hn, pin = h0.copy(), pi0.copy()
    kn = []
    for t in range(256):
        Kx = K_apply(hn, pin)
        dh, dpi = K_adjoint(Kx)
        hn = hn + MU * dh
        pin = pin + MU * dpi
        awh = aw_op(hn)
        pin = pin - awh
        hn = hn + pin
        kn.append(float(np.linalg.norm(Kx)))
    return {"N": N, "T": T,
            "sector": "zero-mean (k=0 excluded, as in the symbol certificate)",
            "k0_jordan_law_residual": k0_jordan,
            "free_energy_drift": qdrift,
            "damped_max_over_initial": max(norms) / n0,
            "damped_final_over_initial": norms[-1] / n0,
            "damped_mean_last512_over_first512": mean_ratio,
            "damped_envelope_slope_per_step_diagnostic": slope,
            "measured_K_rate_last512": rate_late,
            "negative_control_antidamping_growth": kn[-1] / kn[0]}, \
        (qtrace, norms, knorms)


def cert_C5(mu=MU):
    """Second UV node kx=kz=-1.714...: evaluate the *real-space* stencil's
    Laurent symbol at the exact node and compare with the frozen oracle."""
    T = tables()
    maxdeg = T["maxdeg_K"]
    declared_radius = 2 * maxdeg + 2          # K^dag K + free-step radius
    N = 2 * declared_radius + 4
    G = delta_response(N)
    mag = np.max(np.abs(G), axis=(0, 1))
    coords = [np.minimum(np.arange(N), N - np.arange(N)) for _ in range(3)]
    Xr, Yr, Zr = np.meshgrid(*coords, indexing="ij")
    rad = np.maximum(np.maximum(Xr, Yr), Zr)
    thresh = 1e-14 * float(mag.max())
    measured_radius = int(rad[mag > thresh].max())
    xs = np.where(np.arange(N) <= N // 2, np.arange(N), np.arange(N) - N)
    Xs, Ys, Zs = np.meshgrid(xs, xs, xs, indexing="ij")
    phase = np.exp(-1j * (KUV[0] * Xs + KUV[1] * Ys + KUV[2] * Zs))
    Muv = np.einsum("ijxyz,xyz->ij", G, phase)
    Msym = D1.damped_map(KUV, mu)[0]
    diff = float(np.max(np.abs(Muv - Msym)))
    units, mx, rr = D1.unit_census(np.linalg.eigvals(Muv))
    # small neighbourhood scan of the real-space symbol around the node
    worst_nb = 0.0
    units_nb = set()
    for dx in (-0.04, 0.0, 0.04):
        for dz in (-0.04, 0.0, 0.04):
            k = KUV + np.array([dx, 0.0, dz])
            ph = np.exp(-1j * (k[0] * Xs + k[1] * Ys + k[2] * Zs))
            Mn = np.einsum("ijxyz,xyz->ij", G, ph)
            u, m, _ = D1.unit_census(np.linalg.eigvals(Mn))
            units_nb.add(u)
            worst_nb = max(worst_nb, m)
    _, _, r, aw = R25W.walk_data(KUV)
    return {"k_node": list(KUV), "a_W_at_node": aw, "wilson_r_at_node": r,
            "max_monomial_degree_K": int(maxdeg),
            "declared_radius": int(declared_radius),
            "measured_radius": measured_radius,
            "stencil_box_N": int(N),
            "stencil_vs_symbol_at_node": diff,
            "unit_modes_at_node": units, "max_modulus_at_node": mx,
            "slowest_contracting_at_node": rr,
            "neighbourhood_unit_counts": sorted(units_nb),
            "neighbourhood_max_modulus": worst_nb}


def cert_mirror(N=8, T=8, seed=SEED):
    """Reality pairing: mirror sector stays the exact conjugate partner."""
    rng = np.random.default_rng(seed)
    hp = rng.normal(size=(NF, N, N, N)) + 1j * rng.normal(size=(NF, N, N, N))
    pp = rng.normal(size=(NF, N, N, N)) + 1j * rng.normal(size=(NF, N, N, N))
    hm, pm = np.conjugate(hp), np.conjugate(pp)
    for _ in range(T):
        hp, pp = step(hp, pp)
        hm, pm = step_minus(hm, pm)
    pair = float(max(np.max(np.abs(hm - np.conjugate(hp))),
                     np.max(np.abs(pm - np.conjugate(pp)))))
    phys_imag = float(np.max(np.abs((hp + hm).imag))) / 2.0
    return {"T": T, "pairing_residual": pair,
            "physical_field_max_imag": phys_imag}


# ===========================================================================
#  PART D. main
# ===========================================================================
def main():
    t0 = time.time()
    T = tables()
    nmono = {k: len(T[k]) for k in ("Kh", "Kpi", "K1")}
    print("tables built:", nmono, "maxdeg", T["maxdeg_K"],
          f"({time.time()-t0:.1f}s)")

    probe = adjoint_probe()
    print("adjoint probe (R20):", probe)
    assert probe < 1e-13, "adjoint bridge inconsistent -- enforce != measure"

    c1 = cert_C1()
    print(f"C1 symbol==realspace: worst {c1['worst_diff']:.3e} "
          f"offmode {c1['worst_off_mode']:.3e} "
          f"tableK {c1['table_vs_frozen_K_state']:.3e} "
          f"({time.time()-t0:.1f}s)")

    c2, moduli_map = cert_C2()
    print(f"C2 spectrum 16^3: units {c2['unit_counts']} "
          f"max_mod {c2['max_modulus']:.16f} "
          f"rate {c2['slowest_contracting']:.16f} at {c2['slowest_index']} "
          f"({time.time()-t0:.1f}s)")

    c3, drift_trace = cert_C3()
    print(f"C3 Newton 24^3: ratio_A {c3['canary']['ratio_A']:.6f} "
          f"tail {c3['canary']['tailcorr_h00']:.6f} "
          f"bridge {c3['aw_stencil_vs_fft_equilibrium']:.3e} "
          f"dark {c3['constraint_darkness_rel']:.3e} "
          f"fp-drift {c3['fixed_point_drift']:.3e} ({time.time()-t0:.1f}s)")

    c4, traces = cert_C4()
    print(f"C4 stability: Qdrift {c4['free_energy_drift']:.3e} "
          f"max/init {c4['damped_max_over_initial']:.6f} "
          f"meanratio {c4['damped_mean_last512_over_first512']:.9f} "
          f"Krate {c4['measured_K_rate_last512']:.9f} "
          f"negctrl {c4['negative_control_antidamping_growth']:.3f} "
          f"({time.time()-t0:.1f}s)")

    c5 = cert_C5()
    print(f"C5 UV node: |M_stencil-M_sym| {c5['stencil_vs_symbol_at_node']:.3e} "
          f"units {c5['unit_modes_at_node']} "
          f"max_mod {c5['max_modulus_at_node']:.16f} "
          f"radius {c5['measured_radius']}<= {c5['declared_radius']} "
          f"({time.time()-t0:.1f}s)")

    mirror = cert_mirror()
    print("mirror pairing:", mirror)

    checks = {
        "C1_symbol_equals_realspace_lt_1e-12":
            c1["worst_diff"] < 1e-12 and c1["worst_off_mode"] < 1e-12
            and c1["table_vs_frozen_K_state"] < 1e-12,
        "C2_twelve_unit_modes_all_nonzero_k": c2["unit_counts"] == [12],
        "C2_spectral_radius_le_1p1e-14": c2["max_modulus"] <= 1 + 1e-14,
        "C2_rate_matches_symbol_1e-9":
            abs(c2["slowest_contracting"]
                - D1_FULLBZ["slowest_contracting"]) < 1e-9,
        "C3_ratio_A_2_pm_0p02": abs(c3["canary"]["ratio_A"] - 2.0) <= 0.02,
        "C3_tail_ge_0p999": c3["canary"]["tailcorr_h00"] >= 0.999,
        "C3_sourced_fixed_point_drift_lt_1e-9":
            c3["fixed_point_drift_max"] < 1e-9,
        "C3_constraint_darkness_lt_1e-11": c3["constraint_darkness_rel"] < 1e-11,
        # declared operationalization of "norm drift": the exact leapfrog
        # invariant of the free step must sit on the fp64 floor over T=2048;
        # spectral stability of the damped map is C2 (exact, full BZ), the
        # damped trajectory gate below checks boundedness/no secular growth.
        "C4_free_energy_drift_lt_1e-10": c4["free_energy_drift"] < 1e-10,
        "C4_k0_jordan_zero_mode_law_exact":
            c4["k0_jordan_law_residual"] < 1e-12,
        "C4_damped_bounded_no_secular_growth":
            c4["damped_max_over_initial"] < 1.5
            and c4["damped_mean_last512_over_first512"] < 1 + 1e-6,
        "C4_negative_control_grows": c4["negative_control_antidamping_growth"] > 1.0,
        "C5_stencil_symbol_match_lt_1e-11":
            c5["stencil_vs_symbol_at_node"] < 1e-11,
        "C5_node_stable_twelve_units":
            c5["unit_modes_at_node"] == 12
            and c5["max_modulus_at_node"] <= 1 + 1e-13,
        "C5_radius_within_declaration":
            c5["measured_radius"] <= c5["declared_radius"],
        "adjoint_probe_lt_1e-13": probe < 1e-13,
        "mirror_pairing_exact": mirror["pairing_residual"] == 0.0,
    }
    result = {
        "register": "R25-E1-realspace-step",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_sha256": sha256(__file__),
        "frozen_inputs_sha256": {
            "r25_dynamic_symbol.py": sha256(os.path.join(DIR, "r25_dynamic_symbol.py")),
            "r25_auxiliary_wilson_complex.py": sha256(os.path.join(DIR, "r25_auxiliary_wilson_complex.py")),
            "r25_static_newton.py": sha256(os.path.join(DIR, "r25_static_newton.py")),
            "cp1_v4_L2.py": sha256(os.path.join(DIR, "cp1_v4_L2.py")),
        },
        "mu": MU,
        "field_layout": {
            "state": "(h, pi) x 14 components: 10 packed normal h (r15.SYM) + 4 auxiliary Wilson",
            "time": "leapfrog: h integer slices, pi half-integer slices (dynamic-symbol staggering)",
            "space": "R19 staggered storage semantics (samples of (mu,nu) at x+(e_mu+e_nu)/2); operators are placement-transparent integer-roll stencils; the R25 Bloch-scalar complex carries no placement phase",
            "reality": "single chiral xyz sector; mirror sector = exact conjugate (step_minus); physical h = (h_plus + conj(h_plus))/2",
        },
        "operator_structure": {
            "monomial_counts": nmono,
            "max_monomial_degree_K": int(T["maxdeg_K"]),
            "step": "x -> F (I - mu K_state^dag P K_state) x + source",
            "primitives": "a, b_i (frozen matter macro-walk entries), q/r Wilson cosine stencil; all Hermitian scalar convolutions",
        },
        "adjoint_probe": probe,
        "C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5,
        "mirror": mirror,
        "contraction_rate_baseline": {
            "realspace_16BZ_slowest": c2["slowest_contracting"],
            "symbol_16BZ_slowest": D1_FULLBZ["slowest_contracting"],
            "timedomain_last512_rate": c4["measured_K_rate_last512"],
            "note": "obstacle #2 (rate ~0.9999994 too slow) is NOT solved here; these are the real-space baselines a preconditioner must beat",
        },
        "interfaces": {
            "preconditioner": "step(..., precond=P): P maps the 8 constraint fields locally (finite stencil) between K and K^dag; identity by default",
            "source": "step(..., drive=D): 14-component drive enters pi-update, h-update and the K_state proposal; static fixed point certified in C3; moving exact-current source is obstacle #3",
        },
        "scope_boundary": "Real-space step + adjoint bridge only (pre-M3 instrument). No M3 claim: DOF/J5 replay, moving source, dynamic Newton, Eddington, sponge/endurance and falsification battery all remain.",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2,
                  default=_json_default)

    # figure
    qtrace, norms, knorms = traces
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    im = ax[0, 0].imshow(moduli_map[:, :, c2["slowest_index"][2]],
                         origin="lower", cmap="viridis")
    ax[0, 0].set_title("slowest contracting modulus, kz-slice %d"
                       % c2["slowest_index"][2])
    fig.colorbar(im, ax=ax[0, 0])
    ax[0, 1].plot(16 * np.arange(1, len(qtrace) + 1),
                  np.abs(np.array(qtrace) / qtrace[0] - 1.0))
    ax[0, 1].set_yscale("log")
    ax[0, 1].set_title("free-step leapfrog energy |Q/Q0-1|")
    ax[1, 0].plot(norms, label="||x||")
    ax[1, 0].plot(knorms, label="||Kx||")
    ax[1, 0].set_yscale("log")
    ax[1, 0].legend()
    ax[1, 0].set_title("damped run T=2048 (16^3)")
    ax[1, 1].plot(drift_trace)
    ax[1, 1].set_yscale("log")
    ax[1, 1].set_title("C3 sourced fixed-point drift (24^3)")
    for a in ax.flat:
        a.set_xlabel("step")
    fig.tight_layout()
    fig.savefig(FIG, dpi=110)

    print("status:", result["status"])
    print("wrote", OUT)
    print("wrote", FIG)
    print("total %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
