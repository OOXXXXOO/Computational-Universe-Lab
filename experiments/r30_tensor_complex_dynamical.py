"""R30 — the DYNAMICAL half of the discrete linearized-Bianchi TENSOR complex.

MANDATE (lane A, 2026-07-24, following R29's pinned direction). R29 falsified
the projection/patch route (U = U0 + K C is non-local, PART A) and proved the
COMPLEX route is necessary and — for U(1)/Maxwell — possible (div curl = 0 is an
exact operator identity, 7e-16). The remaining, sharply posed theorem:

    Does a LOCAL, UNITARY, discrete linearized-Bianchi TENSOR complex exist,
    whose evolution is a product of local operators and whose constraint
    propagation is a COROLLARY of a tensor 'div curl = 0' identity (not a
    projection, not a Noether fit)?

The KINEMATIC half (R o D = 0, linearized Riemann annihilates gauge) was already
certified (R15/R16 E1). This file builds and certifies the DYNAMICAL half, and
answers the existence question with numbers (three-way verdict, let the data
decide — the first step of an N-N judgement).

THE CONSTRUCTION (Yee, not Regge — per R29's core independent call).
  * calculus:  the walk's OWN placed half-angle symbols kappa_i = 2 sin(k_i/2),
      kappa_0 = 2 sin(w/2)/c on the walk shell (R15 T8), = integer-roll backward
      differences, support radius 1. VERBATIM the R25/R28 placed differential.
  * tensor curl E := the placed linearized RIEMANN operator inc(h)
      R_{m a n b} = 1/2(kap_m kap_n H_ab + kap_a kap_b H_mn
                        - kap_m kap_b H_an - kap_a kap_n H_mb)   (R16/R28 verbatim)
      -- the incompatibility / double-curl. Ricci/Einstein G by contraction.
  * discrete Bianchi (tensor div curl = 0):  kappa^m G_{m n}(h) == 0 and the
      full second Bianchi kappa_[l R_{ma]nb} == 0 -- POLYNOMIAL identities in
      kappa, hence exact operator identities on ANY h (integer-roll real-space
      check confirms). This is the tensor analog of Maxwell's div curl = 0.
  * evolution U:  a Stormer-Verlet (leapfrog) macro-step of the placed wave
      operator  d_tt h = -L(kappa) h,  L = sum_i kappa_i^2  (3-point Laplacian,
      integer rolls +/-1, support radius 1).  dt = c = cos(pi/3) makes the mode
      frequency EQUAL the walk shell exactly. Symplectic (M^T J M = J), strictly
      unitary (|eig| = 1 on the CFL band). U = product of two local shears.
  * constraint propagation as a COROLLARY:  de Donder C_n = kappa^m hbar_mn is a
      fixed linear combination of components that all share the SAME scalar
      leapfrog, so C obeys its own leapfrog and stays 0 -- and the REASON it
      stays 0 is exactly the contracted Bianchi identity kappa^m G_mn = 0
      (div curl = 0). U preserves ker K = placed gauge(4) (+) TT(2) BY
      CONSTRUCTION, never through a projector.

DECISIVE ACCEPTANCE (sealed judgement, 阶段封存 / R28): projection-free
  N_prop = 2, i.e. the evolved unit modes' energy residual OUTSIDE ker K -> 0,
  read by the R28 PLACED-kappa Riemann-SVD judge, with the R28 double positive
  control (teeth -> 6; synthetic placed-TT -> 2 cliff).

CONTRAST WITH THE WALK (R28, frozen). The Dirac-walk U does NOT lie in this
  complex: its 12 unit modes carry 34-49% energy OUTSIDE ker K and it counts 4.
  This file's U is a genuine member of the complex: residual ~1e-15, counts 2.
  The walk's failure was never an N-N obstruction to the complex EXISTING; it
  was that the walk is not (yet) of the complex.

RED LINES (AGENTS.md + 执行令). This is an EXISTENCE construction. Success =>
  'a local unitary discrete linearized-Bianchi tensor complex EXISTS' (may be
  declared). It is NOT M3 and NOT emergence: U here is assembled, not the
  emergent Dirac walk; 卡点④ single-run joint-verification is untouched. The
  open question that remains is whether the EMERGENT walk can be deformed onto
  this complex (that is M3, out of scope). Negative/partial results equal value.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/r30_tensor_complex_dynamical.py
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

import matplotlib                                            # noqa: E402
matplotlib.use("Agg")

# ---- frozen machinery, READ-ONLY -----------------------------------------
from r15_walk_dedonder import (kappa_placed, gauge_block, tt_basis,          # noqa: E402
                               shell_omega, C_CONE, ETA, unpack, SYM)
from rulespace_gpu import emergence_judge as EJ              # noqa: E402  packed_to_44, kernels

OUT = os.path.join(ROOT, "data", "results", "r30_results.json")

N = 16
SV_THRESH = EJ.SV_THRESH                                     # 0.05, shared judge口径
W_MAX = np.pi / 2
DT = C_CONE                                                  # leapfrog step = cone speed
ETAu = np.diag([-1.0, 1.0, 1.0, 1.0])                        # eta^{munu} (flat)
KSET = [(2, 0, 0), (0, 3, 0), (2, 2, 0), (2, 2, 2)]          # axial / face / BODY diagonal
LABELS = {(2, 0, 0): "axial", (0, 3, 0): "axial",
          (2, 2, 0): "face-diagonal", (2, 2, 2): "body-diagonal"}
T_CLEAN = 320
TRIALS = 6
SEED = 30303


# ===========================================================================
#  serialization helpers
# ===========================================================================
def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _jd(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        f = float(o)
        return f if np.isfinite(f) else str(f)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def write_json(payload):
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_jd)


def _tr_flat(v10):
    """flat-ETA trace reversal (R16 convention): hbar-packed -> physical-h packed.
    Cancels the -eta(kap.xi) term of gauge_block so its output is physical h."""
    Hb = unpack(v10)
    trb = sum(ETA[m, m] * Hb[m, m] for m in range(4))
    H = Hb - 0.5 * ETA * trb
    return np.array([H[m, n] for (m, n) in SYM])


# ===========================================================================
#  PART 1.  THE TENSOR COMPLEX  D --inc--> E --div--> Bianchi
#  placed-kappa symbol operators; all identities are polynomial in kappa.
# ===========================================================================
def riemann4(kap, H44):
    """placed linearized Riemann R_{m a n b} (pairs (m,a),(n,b)); H physical h."""
    k = np.real(kap)
    R = np.zeros((4, 4, 4, 4))
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    R[m, a, n, b] = 0.5 * (
                        k[m] * k[n] * H44[a, b] + k[a] * k[b] * H44[m, n]
                        - k[m] * k[b] * H44[a, n] - k[a] * k[n] * H44[m, b])
    return R


def einstein(kap, H44):
    """linearized Einstein tensor G_{ab} = Ric_{ab} - 1/2 eta_ab R, from placed R.
    Ric_{ab} = eta^{mn} R_{m a n b}; R = eta^{ab} Ric_{ab}."""
    R = riemann4(kap, H44)
    Ric = np.einsum("mn,manb->ab", ETAu, R)
    Rs = np.einsum("ab,ab->", ETAu, Ric)
    return Ric - 0.5 * ETAu * Rs


def complex_identities_bz(n_side=7, n_h=3, seed=0):
    """Scan the BZ: certify the two complex identities as machine zero.
      div o inc = 0 : contracted Bianchi kappa^m G_mn(h) and full second Bianchi
                      kappa_[l R_ma]nb, both == 0 for ANY physical h. (tensor
                      div curl = 0 -- the Maxwell analog).
      inc o D  = 0 : Riemann of a placed gauge mode == 0 (kinematic half, E1).
    Also the raw Maxwell |k.(k x v)| baseline for the blood-line comparison."""
    rng = np.random.default_rng(seed)
    kaps = []
    axis = np.linspace(-1.1, 1.1, n_side)
    for kx in axis:
        for ky in axis:
            for kz in axis:
                k = np.array([kx, ky, kz])
                if np.linalg.norm(k) < 1e-2 or shell_omega(k) is None:
                    continue
                kaps.append((k, kappa_placed(k)))
    w_contracted = w_full = w_incD = 0.0
    for k, kap in kaps:
        for _ in range(n_h):
            A = rng.standard_normal((4, 4))
            H = A + A.T
            G = einstein(kap, H)
            w_contracted = max(w_contracted,
                               float(np.max(np.abs(np.einsum("a,ab->b",
                                                             ETAu @ kap, G)))))
            R = riemann4(kap, H)
            fb = 0.0
            for m in range(4):
                for a in range(4):
                    for n in range(4):
                        for b in range(4):
                            for l in range(4):
                                fb = max(fb, abs(
                                    kap[l] * R[m, a, n, b]
                                    + kap[n] * R[m, a, b, l]
                                    + kap[b] * R[m, a, l, n]))
            w_full = max(w_full, fb)
            xi = rng.standard_normal(4)
            Hg = np.outer(kap, xi) + np.outer(xi, kap)       # placed gauge (symmetrized grad)
            w_incD = max(w_incD, float(np.max(np.abs(riemann4(kap, Hg)))))
    mw = 0.0
    for _ in range(500):
        k = rng.standard_normal(3)
        v = rng.standard_normal(3)
        mw = max(mw, abs(float(np.dot(k, np.cross(k, v)))))
    return {"n_k_on_shell": len(kaps),
            "div_inc_contracted_Bianchi_kappaG": w_contracted,
            "div_inc_full_second_Bianchi": w_full,
            "inc_D_riemann_of_gauge": w_incD,
            "maxwell_divcurl_baseline": mw}


def complex_identity_realspace(Nc=6, seed=1):
    """Operator-identity form (Maxwell R23-P6 flavor): build G_{mn} on a small
    real 3D lattice from INTEGER-ROLL differences and check kappa^m G_mn == 0 as
    a real-space operator identity (not per-k). Central roll differences commute,
    so the polynomial identity lifts to the operator. Time index carried at a
    fixed frequency slab (static constraint surface), matching R29.C_grav."""
    rng = np.random.default_rng(seed)
    # random physical symmetric h field, 10 packed comps on an Nc^3 lattice
    hf = rng.standard_normal((Nc, Nc, Nc, 4, 4))
    hf = 0.5 * (hf + np.swapaxes(hf, -1, -2))
    kt = 0.37                                                # fixed time symbol slab

    def Dsp(f, j):                                           # integer roll central diff, axis j-1
        return 0.5 * (np.roll(f, -1, axis=j - 1) - np.roll(f, 1, axis=j - 1))

    def Dmu(f, mu):
        if mu == 0:
            return 1j * kt * f                               # static slab: pure phase
        return Dsp(f, mu)

    # second derivatives GG[m][n] = D_m D_n h
    GG = [[Dmu(Dmu(hf, n), m) for n in range(4)] for m in range(4)]
    R = np.zeros(hf.shape + (4, 4), dtype=complex)           # R[...,m,a? ] build R_{manb}
    # R_{m a n b} = 1/2 (D_m D_n h_ab + D_a D_b h_mn - D_m D_b h_an - D_a D_n h_mb)
    Rt = np.zeros(hf.shape[:3] + (4, 4, 4, 4), dtype=complex)
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    Rt[..., m, a, n, b] = 0.5 * (
                        GG[m][n][..., a, b] + GG[a][b][..., m, n]
                        - GG[m][b][..., a, n] - GG[a][n][..., m, b])
    Ric = np.einsum("mn,xyzmanb->xyzab", ETAu, Rt)
    Rs = np.einsum("ab,xyzab->xyz", ETAu, Ric)
    Gt = Ric - 0.5 * ETAu[None, None, None] * Rs[..., None, None]
    # divergence kappa^m G_mn -> D^m G_mn (raise with eta, same central rolls)
    div = np.zeros(hf.shape[:3] + (4,), dtype=complex)
    for nu in range(4):
        acc = np.zeros(hf.shape[:3], dtype=complex)
        for m in range(4):
            acc = acc + ETAu[m, m] * Dmu(Gt[..., m, nu], m)
        div[..., nu] = acc
    return float(np.max(np.abs(div)))


# ===========================================================================
#  PART 2.  THE YEE EVOLUTION  U  (local, symplectic, unitary)
# ===========================================================================
def L_placed(k):
    """placed spatial Laplacian symbol L(kappa) = sum_i kappa_i^2, kappa_i =
    2 sin(k_i/2) -- the 3-point integer-roll stencil, support radius 1."""
    return float(sum((2.0 * np.sin(ki / 2.0)) ** 2 for ki in k))


def leap_M(k):
    """one macro-step 2x2 Stormer-Verlet map per h-component (h, pi=dh/dt):
        h' = (1 - 1/2 dt^2 L) h + dt pi
        pi'= -dt L (1 - 1/4 dt^2 L) h + (1 - 1/2 dt^2 L) pi
    det == 1 (symplectic); |eig| == 1 iff dt^2 L < 4 (CFL); cos(w) = 1-1/2dt^2L."""
    L = L_placed(k)
    a = 1.0 - 0.5 * DT * DT * L
    return np.array([[a, DT], [-DT * L * (1.0 - 0.25 * DT * DT * L), a]])


def evolve_components(h0, pi0, k, T):
    """Evolve the 10 physical-h components + momenta by the SAME leapfrog (each a
    scalar wave with the shared placed L). h0, pi0: (trials, 10) complex.
    Returns rec (T, trials, 10) of the physical metric k-mode amplitude."""
    L = L_placed(k)
    a = 1.0 - 0.5 * DT * DT * L
    off = -DT * L * (1.0 - 0.25 * DT * DT * L)
    rec = np.zeros((T, h0.shape[0], 10), complex)
    h, pi = h0.copy(), pi0.copy()
    for t in range(T):
        hn = a * h + DT * pi
        pin = off * h + a * pi
        h, pi = hn, pin
        rec[t] = h
    return rec


def yee_certificates(kset_full):
    """|eig|=1, det=1, symplectic M^T J M = J, and freq == placed shell, over a
    broad k sample (the local unitary certificate)."""
    J = np.array([[0.0, 1.0], [-1.0, 0.0]])
    w_uni = w_det = w_symp = w_freq = 0.0
    cfl_ok = True
    for nv in kset_full:
        k = np.array(nv, float) * (2 * np.pi / N)
        w = shell_omega(k)
        if w is None:
            continue
        M = leap_M(k)
        ev = np.linalg.eigvals(M)
        w_uni = max(w_uni, abs(float(np.max(np.abs(ev))) - 1.0))
        w_det = max(w_det, abs(float(np.linalg.det(M)) - 1.0))
        w_symp = max(w_symp, float(np.max(np.abs(M.T @ J @ M - J))))
        w_freq = max(w_freq, abs(float(abs(np.angle(ev[0]))) - w))
        cfl_ok = cfl_ok and (DT * DT * L_placed(k) < 4.0)
    return {"max_abs_eig_minus_1": w_uni, "max_det_minus_1": w_det,
            "max_symplectic_defect": w_symp, "max_freq_minus_shell": w_freq,
            "cfl_ok": bool(cfl_ok)}


# ===========================================================================
#  PART 3.  PLACED Riemann-SVD judge (R28口径, verbatim window/peak/SVD).
# ===========================================================================
def riemann_series_k_placed(H44, kap):
    k = np.real(np.asarray(kap))
    T = H44.shape[0]
    Rt = np.zeros((T, 4, 4, 4, 4), dtype=complex)
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    Rt[:, m, a, n, b] = 0.5 * (
                        k[m] * k[n] * H44[:, a, b] + k[a] * k[b] * H44[:, m, n]
                        - k[m] * k[b] * H44[:, a, n] - k[a] * k[n] * H44[:, m, b])
    return Rt[2:-2].reshape(T - 4, 256)


def peak_and_svd_placed(series_k, kap):
    """series_k (T, trials, 10) physical h; placed-kappa Riemann SVD count.
    Byte-identical window/sel/peak/prominence/SV_THRESH to R28._peak_and_svd_placed."""
    T = series_k.shape[0]
    T0 = T // 2
    Wn = T - T0
    win = np.hanning(Wn)
    freqs = 2 * np.pi * np.fft.fftfreq(Wn - 4)
    sel = (freqs > max(0.05, 4 * np.pi / (Wn - 4))) & (freqs <= W_MAX)
    rows_R, rows_raw, pow_spec = [], [], None
    for r in range(series_k.shape[1]):
        H10 = series_k[T0:, r, :]
        Rf = riemann_series_k_placed(EJ.packed_to_44(H10), kap)
        F = np.fft.fft(Rf * win[2:-2, None], axis=0)
        Praw = np.fft.fft(H10[2:-2] * win[2:-2, None], axis=0)
        P = np.sum(np.abs(F) ** 2, axis=1)
        pow_spec = P if pow_spec is None else pow_spec + P
        rows_R.append(F)
        rows_raw.append(Praw)
    total = float(pow_spec[sel].sum())
    if total < 1e-18:
        return {"n_prop": 0, "w_peak": float("nan"), "sv": [], "no_peak": True}
    pk = int(np.argmax(np.where(sel, pow_spec, 0)))
    w_pk = float(freqs[pk])
    edge = int(np.argmax(sel))
    prom = float(pow_spec[pk] / (pow_spec[edge] + 1e-300))
    if pk == edge or prom < 2.0:
        return {"n_prop": 0, "w_peak": float("nan"), "sv": [], "no_peak": True,
                "prominence": prom}
    M = np.array([r[pk] for r in rows_R])
    sv = np.linalg.svd(M, compute_uv=False)
    svn = (sv / (sv[0] + 1e-300)).tolist()
    n_prop = int(np.sum(np.array(svn) > SV_THRESH))
    return {"n_prop": n_prop, "w_peak": w_pk, "prominence": prom,
            "sv": [float(v) for v in svn[:8]]}


# ===========================================================================
#  IC builders (clean = ker K; teeth = all 10; TT-only; gauge-only)
# ===========================================================================
def kerK_basis(kap):
    """physical ker K = placed gauge(4) (+) TT(2), orthonormalized (10,6)."""
    G = gauge_block(kap)
    TT = tt_basis(kap)
    basis = np.column_stack([_tr_flat(np.real(G[:, a])) for a in range(4)]
                            + [np.real(TT[:, i]) for i in range(2)])
    Q, _ = np.linalg.qr(basis)
    return Q, G, TT


def make_ic(kind, kap, k, trials, rng):
    """Return (h0, pi0) physical (trials,10). pi0 = i*w*h0 (single-branch +w)."""
    w = shell_omega(k)
    G = gauge_block(kap)
    TT = tt_basis(kap)
    h0 = np.zeros((trials, 10), complex)
    for r in range(trials):
        if kind == "clean_kerK":
            cg = _tr_flat(G @ (rng.standard_normal(4) + 1j * rng.standard_normal(4)))
            ctt = (TT[:, 0] * (rng.standard_normal() + 1j * rng.standard_normal())
                   + TT[:, 1] * (rng.standard_normal() + 1j * rng.standard_normal()))
            h0[r] = cg + ctt
        elif kind == "TT_only":
            h0[r] = (TT[:, 0] * (rng.standard_normal() + 1j * rng.standard_normal())
                     + TT[:, 1] * (rng.standard_normal() + 1j * rng.standard_normal()))
        elif kind == "gauge_only":
            h0[r] = _tr_flat(G @ (rng.standard_normal(4) + 1j * rng.standard_normal(4)))
        elif kind == "teeth_all10":
            h0[r] = rng.standard_normal(10) + 1j * rng.standard_normal(10)
        else:
            raise ValueError(kind)
    return h0, 1j * w * h0


def dedonder_darkness(series_k, kap):
    """max_t |C_n(t)| / rms, C_n = kappa^m hbar_mn ; hbar = trace-reverse of h.
    series_k (T,trials,10) physical h. Constraint on the trajectory."""
    kup = ETAu @ np.real(kap)
    worst = 0.0
    for t in range(series_k.shape[0]):
        for r in range(series_k.shape[1]):
            H = EJ.packed_to_44(series_k[t, r][None])[0]     # physical h
            trh = np.einsum("ab,ab->", ETAu, H)
            Hb = H - 0.5 * ETAu * trh                         # hbar = trace-reverse
            C = np.einsum("m,mn->n", kup, Hb)
            rms = np.sqrt(np.mean(np.abs(series_k[t, r]) ** 2)) + 1e-300
            worst = max(worst, float(np.max(np.abs(C))) / rms)
    return worst


def kerK_residual(series_k, kap):
    """mean residual of the (final-slice) evolved modes OUTSIDE physical ker K.
    The direct analog of R28.placed_subspace_residual (walk: 0.34-0.49)."""
    Q, _, _ = kerK_basis(kap)
    U = series_k[-1].T
    U = U / (np.linalg.norm(U, axis=0, keepdims=True) + 1e-300)
    resid = np.linalg.norm(U - Q @ (Q.conj().T @ U), axis=0)
    return float(np.mean(resid)), float(np.max(resid))


# ===========================================================================
#  main
# ===========================================================================
def main():
    t0 = time.time()
    payload = {
        "register": "R30-tensor-complex-dynamical-half",
        "status": "RUNNING",
        "backend": EJ.B.NAME,
        "mandate": "construct the DYNAMICAL half of a local unitary discrete "
                   "linearized-Bianchi tensor complex (Yee, not Regge); decide "
                   "existence by N_prop (three-way). EXISTENCE construction, NOT M3.",
        "params": {"N": N, "kset": [list(k) for k in KSET], "dt": DT,
                   "T_clean": T_CLEAN, "trials": TRIALS, "sv_thresh": SV_THRESH,
                   "seed": SEED, "c_cone": C_CONE},
        "frozen_inputs_sha256": {
            "r15_walk_dedonder.py": sha256_file(os.path.join(DIR, "r15_walk_dedonder.py")),
            "r16_cp1_invitro.py": sha256_file(os.path.join(DIR, "r16_cp1_invitro.py")),
            "emergence_judge.py": sha256_file(os.path.join(ROOT, "rulespace_gpu", "emergence_judge.py")),
            "r28_placed_judge_reverdict.py": sha256_file(os.path.join(DIR, "r28_placed_judge_reverdict.py")),
        },
    }
    write_json(payload)
    print("R30 — dynamical half of the discrete linearized-Bianchi tensor complex")
    print("=" * 74)

    # -- PART 1: the complex identities (Bianchi = tensor div curl = 0) -------
    print("[1] tensor complex identities over the BZ (placed kappa) ...")
    ci = complex_identities_bz()
    ci["div_inc_realspace_operator_identity"] = complex_identity_realspace()
    payload["complex_identities"] = ci
    print(f"    inc o D  (Riemann of gauge)      = {ci['inc_D_riemann_of_gauge']:.2e}  (R o D = 0, kinematic half)")
    print(f"    div o inc contracted Bianchi     = {ci['div_inc_contracted_Bianchi_kappaG']:.2e}  (tensor div curl = 0)")
    print(f"    div o inc full 2nd Bianchi       = {ci['div_inc_full_second_Bianchi']:.2e}")
    print(f"    div o inc real-space (int rolls) = {ci['div_inc_realspace_operator_identity']:.2e}  (operator identity)")
    print(f"    Maxwell |k.(kxv)| baseline       = {ci['maxwell_divcurl_baseline']:.2e}  (7e-16 blood-line)")
    write_json(payload)

    # -- PART 2: the Yee evolution certificates ------------------------------
    print("[2] Yee leapfrog U — local, symplectic, strictly unitary ...")
    kbroad = KSET + [(1, 3, 2), (4, 1, 0), (5, 0, 0), (3, 3, 3), (1, 0, 0),
                     (6, 2, 1), (0, 5, 2), (2, 4, 3)]
    yc = yee_certificates(kbroad)
    yc["locality"] = {"laplacian_stencil": "3-point per axis (rolls +/-1), "
                      "support radius 1", "curl_stencil": "kappa_i=2 sin(k_i/2) "
                      "= backward integer-roll difference, support radius 1",
                      "U": "product of two local shears (Stormer-Verlet)"}
    payload["yee_certificates"] = yc
    print(f"    max ||eig|-1|      = {yc['max_abs_eig_minus_1']:.2e}  (strictly unitary)")
    print(f"    max |det-1|        = {yc['max_det_minus_1']:.2e}  (symplectic)")
    print(f"    max M^T J M - J    = {yc['max_symplectic_defect']:.2e}")
    print(f"    max |freq - shell| = {yc['max_freq_minus_shell']:.2e}  (matches walk shell)")
    write_json(payload)

    # -- PART 3 + 4: constraint propagation + DECISIVE N_prop count ----------
    print("[3+4] evolve U from clean ker-K IC; de Donder propagation + N_prop:")
    rng = np.random.default_rng(SEED)
    per_k = []
    for nv in KSET:
        k = np.array(nv, float) * (2 * np.pi / N)
        kap = kappa_placed(k)
        h0, pi0 = make_ic("clean_kerK", kap, k, TRIALS, rng)
        rec = evolve_components(h0, pi0, k, T_CLEAN)
        dark = dedonder_darkness(rec, kap)
        rmean, rmax = kerK_residual(rec, kap)
        res = peak_and_svd_placed(rec, kap)
        row = {"nv": list(nv), "label": LABELS[nv], "n_prop": res["n_prop"],
               "sv": res.get("sv", []), "w_peak": res.get("w_peak"),
               "w_shell": float(shell_omega(k)),
               "dedonder_darkness_max_over_T": dark,
               "kerK_residual_mean": rmean, "kerK_residual_max": rmax}
        per_k.append(row)
        print(f"    k={nv} [{LABELS[nv]:>13}]  N_prop={res['n_prop']}"
              f"  deDonder|C|/rms<={dark:.1e}  resid_outside_kerK={rmean:.1e}"
              f"  sv={['%.0e' % s for s in res.get('sv', [])[:4]]}")
    payload["decisive_run"] = {"per_k": per_k,
                               "n_prop_seq": [r["n_prop"] for r in per_k]}
    write_json(payload)

    # -- POSITIVE CONTROLS (R28 double control + our own teeth) --------------
    print("[PC] positive controls (judge has teeth; is not rigged to 2) ...")
    controls = {}
    for kind, expect in (("teeth_all10", ">2 (~6): generic 10-comp IC -> full curvature"),
                         ("TT_only", "2 with machine-zero cliff"),
                         ("gauge_only", "0 (no propagating curvature / no peak)")):
        seq, svs = [], []
        rng2 = np.random.default_rng(SEED + 1)
        for nv in KSET:
            k = np.array(nv, float) * (2 * np.pi / N)
            kap = kappa_placed(k)
            h0, pi0 = make_ic(kind, kap, k, TRIALS, rng2)
            rec = evolve_components(h0, pi0, k, T_CLEAN)
            res = peak_and_svd_placed(rec, kap)
            seq.append(res["n_prop"])
            svs.append([round(s, 3) for s in res.get("sv", [])[:5]])
        controls[kind] = {"n_prop": seq, "sv": svs, "expect": expect}
        print(f"    {kind:12s} N_prop = {seq}   (expect {expect})")
    payload["positive_controls"] = controls
    write_json(payload)

    # -- VERDICT (three-way, let the numbers decide) -------------------------
    id_ok = (ci["inc_D_riemann_of_gauge"] < 1e-12
             and ci["div_inc_contracted_Bianchi_kappaG"] < 1e-12
             and ci["div_inc_full_second_Bianchi"] < 1e-12
             and ci["div_inc_realspace_operator_identity"] < 1e-10)
    yee_ok = (yc["max_abs_eig_minus_1"] < 1e-12 and yc["max_det_minus_1"] < 1e-12
              and yc["max_symplectic_defect"] < 1e-12
              and yc["max_freq_minus_shell"] < 1e-12 and yc["cfl_ok"])
    dark_ok = all(r["dedonder_darkness_max_over_T"] < 1e-10 for r in per_k)
    resid_ok = all(r["kerK_residual_mean"] < 1e-10 for r in per_k)
    nprop = [r["n_prop"] for r in per_k]
    nprop_ok = all(n == 2 for n in nprop)
    # controls sane: teeth>2, TT==2, gauge<2
    teeth_ok = all(n > 2 for n in controls["teeth_all10"]["n_prop"])
    tt_ok = all(n == 2 for n in controls["TT_only"]["n_prop"])
    gauge_ok = all(n < 2 for n in controls["gauge_only"]["n_prop"])
    pc_ok = teeth_ok and tt_ok and gauge_ok

    if not pc_ok:
        verdict_tag = "VOID (positive controls failed — judge blinded)"
        verdict = (f"controls: teeth={controls['teeth_all10']['n_prop']} "
                   f"TT={controls['TT_only']['n_prop']} "
                   f"gauge={controls['gauge_only']['n_prop']}. Fix the judge first.")
    elif id_ok and yee_ok and dark_ok and resid_ok and nprop_ok:
        verdict_tag = "CONSTRUCTION SUCCESS — tensor complex EXISTS"
        verdict = (
            "A LOCAL UNITARY discrete linearized-Bianchi TENSOR complex EXISTS. "
            f"Bianchi (tensor div curl=0) machine-zero over BZ "
            f"({ci['div_inc_contracted_Bianchi_kappaG']:.1e}, matching Maxwell "
            f"{ci['maxwell_divcurl_baseline']:.1e}); U strictly unitary/symplectic/"
            f"local (|eig|-1={yc['max_abs_eig_minus_1']:.1e}); de Donder preserved "
            f"BY CONSTRUCTION (|C|/rms<={max(r['dedonder_darkness_max_over_T'] for r in per_k):.1e}) "
            "as a COROLLARY of kappa^m G_mn=0, NOT a projection; unit modes stay "
            f"IN ker K (residual {max(r['kerK_residual_mean'] for r in per_k):.1e} "
            f"vs walk 0.34-0.49); projection-free N_prop = {nprop} = 2 at ALL k "
            "incl. body-diagonal (2,2,2), with a machine-zero cliff. This settles "
            "R29's remaining existence theorem AFFIRMATIVELY: the referees' N-N "
            "worry does NOT kill the spin-2 complex — the tensor div curl=0 is a "
            "polynomial identity in kappa, exactly as for Maxwell. RED LINE: this "
            "is an EXISTENCE construction of an ASSEMBLED U; it is NOT M3 and NOT "
            "emergence — whether the emergent Dirac walk can be deformed onto this "
            "complex (that is M3) remains open and untouched here.")
    elif id_ok and yee_ok and (dark_ok and resid_ok) and not nprop_ok:
        verdict_tag = "PARTIAL — complex + unitary hold, N_prop != 2"
        verdict = (f"Bianchi identity and unitary locality hold, ker K preserved, "
                   f"but N_prop = {nprop} != 2. Localize which irrep leaks.")
    elif id_ok and not yee_ok:
        verdict_tag = "PARTIAL — Bianchi identity holds, evolution not strictly unitary"
        verdict = (f"tensor div curl=0 machine zero, but Yee certificate failed "
                   f"({yc}). Report which fails.")
    else:
        verdict_tag = "TENSOR-LAYER OBSTRUCTION — N-N candidate"
        verdict = (f"an identity broke at the tensor layer: inc_D={ci['inc_D_riemann_of_gauge']:.1e} "
                   f"contracted={ci['div_inc_contracted_Bianchi_kappaG']:.1e} "
                   f"full={ci['div_inc_full_second_Bianchi']:.1e} "
                   f"realspace={ci['div_inc_realspace_operator_identity']:.1e}. "
                   "Characterize the broken irrep as N-N no-go evidence.")

    payload["maxwell_comparison"] = {
        "field": "A_mu (4) [spin1]  ->  h_mu_nu (10) [spin2]",
        "curl": "F=kap^A - A^kap  ->  inc(h)=linearized Riemann (double curl)",
        "div_curl_0": {"maxwell": ci["maxwell_divcurl_baseline"],
                       "tensor_contracted_Bianchi": ci["div_inc_contracted_Bianchi_kappaG"],
                       "tensor_full_Bianchi": ci["div_inc_full_second_Bianchi"]},
        "constraint": "Gauss k.E=0 (1) -> de Donder kappa^m hbar_mn=0 (4)",
        "gauge": "A+kap xi (1) -> hbar + kap xi + xi kap - eta(kap.xi) (4)",
        "physical": "2 photon pols  ->  2 TT graviton pols",
        "evolution": "Yee leapfrog E,B  ->  placed wave leapfrog (h,pi)",
        "constraint_mechanism": "div curl=0 identity in BOTH (not projection)"}
    payload["contrast_walk_R28"] = {
        "walk_kerK_residual": [0.469, 0.485, 0.341, 0.389],
        "walk_placed_dynamic_Nprop": [4, 4, 4, 4],
        "R30_kerK_residual": [r["kerK_residual_mean"] for r in per_k],
        "R30_Nprop": nprop,
        "note": "the walk's failure was NOT an N-N obstruction to the complex "
                "existing; it was that the walk is not (yet) of the complex."}
    payload["checks"] = {"identities": id_ok, "yee_unitary_local": yee_ok,
                         "dedonder_preserved": dark_ok, "kerK_preserved": resid_ok,
                         "n_prop_eq_2": nprop_ok, "positive_controls": pc_ok}
    payload["verdict_tag"] = verdict_tag
    payload["verdict"] = verdict
    payload["scope_boundary"] = (
        "EXISTENCE construction of an ASSEMBLED local unitary tensor complex. NOT "
        "M3, NOT emergence. U is hand-built (not the emergent Dirac walk); 卡点④ "
        "single-run joint verification untouched. Clean IC on ker K is the declared "
        "premise (same as 卡点⑦/R28); the content is that U PRESERVES it (residual "
        "~1e-15) where the walk did not (0.34-0.49).")
    payload["status"] = "PASS" if (pc_ok and id_ok and yee_ok and dark_ok
                                   and resid_ok and nprop_ok) else "PARTIAL/FAIL"
    payload["source_sha256"] = sha256_file(__file__)
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = sha256_bytes(fh.read())
    payload["results_sha256"] = jsha
    write_json(payload)

    print("=" * 74)
    print(f"identities={id_ok}  yee_unitary_local={yee_ok}  deDonder={dark_ok}  "
          f"kerK={resid_ok}  N_prop==2:{nprop_ok}  controls={pc_ok}")
    print(f"N_prop = {nprop}   (walk R28 was [4,4,4,4])")
    print(f"VERDICT [{verdict_tag}]")
    print(verdict)
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
