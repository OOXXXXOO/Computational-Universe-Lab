"""photon_control.py -- cannon #10, the MEASURED half (lane B, post-L2).

WHAT THIS IS (per 主线-CP1v4-装配阶梯与证伪炮组.md §三b/三e and
预注册-CP1v4 cannon 10): the POSITIVE CONTROL of the emergence-judge
machinery on a system whose physics is KNOWN TRUE -- standard Yee FDTD
vacuum electromagnetism -- plus two KNOWN-SICK variants the judge must
reject.  R23 delivered the symbol-layer half (6/6); this file is the
lattice-dynamics half.

CORRESPONDENCE (the "EM Riemann-SVD", method-isomorphic to cp1_v4_L1):

    gravity (cp1_v4)                      EM (this file)
    ------------------------------------  ------------------------------------
    field h_bar_munu, 10 comps, gauge-    potential A_mu, 4 comps, gauge-
      variant                               variant
    invariant = linearized Riemann        invariant = F_munu, i.e. (E, B),
      (needs shell for gauge nullity)       6 comps (gauge nullity is an
                                            ALGEBRAIC identity -- R23 P3)
    staggered R17/R19 placement           Yee 1966 placement: E on edges
                                            (x + e_i/2, integer t), B on faces
                                            (x + (e_j+e_k)/2, half t)  [R23 P6:
                                            our dictionary degenerates to Yee]
    de Donder constraint K_placed (4)     Gauss div E = 0, div B = 0 (2)
    judge: record 10-comp k-mode series   judge: record 6-comp (E,B) k-mode
      -> build Riemann at the peak          series -> the series ALREADY IS the
      -> stack trials -> SVD rank           invariant (Yee stores F directly:
                                            "store the components right and the
                                            constraint is automatic", R19 SS1)
      -> stack trials -> SVD rank
    N_prop target: 2 (TT)                 N_prop target: 2 (transverse pols)
    c_gw vs c_matter (J5)                 c_photon vs Yee analytic dispersion
    SV gate sv3 < 0.05, tt_match > 0.95   SV gate sv3 < 0.05, transverse match
                                            > 0.95 (vs exact stepper eigenmodes,
                                            themselves certified Gauss-null)

Because Yee evolves F itself, the "build the invariant from the field"
step of the gravity pipeline is the IDENTITY here.  That is not a
weakening: it is the lattice-dynamics face of R23 P3 (F annihilates gauge
modes identically, off shell included) -- spin 1's gauge structure is one
level shallower than spin 2's, and the pipeline inherits that for free.

POSITIVE GATES (Yee-EM, ALL must PASS):
  P1  N_prop(EM) = 2 at every probe k (multi-line total; sv3 < 0.05)
  P2  dispersion: operator-level w_op == Yee analytic w(k) to machine;
      measured spectral peak |w_meas - w_yee| < 1 FFT bin at every probe
      k (axial + planar + body-diagonal + Nyquist); small-k |c-1| equals
      the analytic Yee dispersion correction pointwise (|c_meas - c_yee|
      < 2e-2 relative, with c_yee - 1 tabulated as the correction)
  P3  isotropy: axis-permutation c identical (spread < 1e-3)
  P4  constraints: generic IC -> div E, div B DRIFT from initial value
      machine zero (Yee identity div o curl == 0); solenoidal-projected
      IC -> div E, div B themselves machine zero for all t
  P5  stability: rms bounded; discrete Yee energy invariant
      H = |E|^2 + B(-)·B(+) drift reported
  P6  SV-style gate: transverse (photon) match of the top-2 SVD space
      > 0.95 against the exact one-step eigenmodes; those eigenmodes are
      independently certified transverse: lattice div applied to them is
      machine zero, and their frequency equals the analytic formula

SENSITIVITY CONTROLS (each must FAIL >= 1 gate; the judge's teeth):
  S1  Proca mass term m != 0 (lattice Proca on the same Yee complex, with
      the algebraic nu=0 equation A0 = -div E / m^2; see make_step_proca):
      all three polarizations sit exactly on the massive shell
      sin^2(w DT/2) = (DT/2)^2 (k_chord^2 + m^2) -> the judge must read
      N_prop = 3, a mass gap m_eff^2 = m^2 pointwise, and a broken c gate.
  S2  BAD PLACEMENT (constraint structure removed): all E, B components
      collocated at integer nodes, central differences in both curls --
      the CP0/CP1-v1 disease transplanted to EM (R19 negative control
      family).  Expect wrong dispersion pointwise (fails the analytic
      对拍 at every k) and a FROZEN Nyquist photon: at k = (pi,0,0) the
      central symbol sin(pi) = 0 kills propagation -> N_prop = 0 there
      (spurious-mode / miscount kill), while true Yee propagates it.

Discipline: fp64, fixed seeds, minutes-scale, numpy backend only.
cp1_v4 L2 results are CITED READ-ONLY for the 4-column verdict table;
nothing gravitational is re-run here.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python photon_control.py
      (writes photon_control_results.json; sha256 of this file embedded)
"""
import hashlib
import json
import math
import os
import time

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
N = 16
DT = 0.5                                # Courant: DT*sqrt(3) = 0.87 < ... CFL
T_MAIN = 1024
TRIALS = 8
SEED_TRUE, SEED_SOL, SEED_PROCA, SEED_BAD = 7, 8, 9, 10
SV_THRESH = 0.05                        # same judge threshold as cp1_v4/emergence_judge
M_PROCA = 0.4

KM_ALL = [(2, 0, 0), (0, 2, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0), (2, 2, 2),
          (8, 0, 0)]                    # axial x3 + planar + oblique + body-diag + Nyquist
KM_SMALLK = KM_ALL[:6]                  # light-cone / |c-1| gate subset (declared)
KM_ISO = [(2, 0, 0), (0, 2, 0), (0, 0, 2)]

# Yee placement offsets (units of half cells), physical-frame un-shift is
# exp(-i k.off) at record time (unit phase, lossless -- cp1_v4 colfac).
OFF_E = np.array([[0.5, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 0.5]])
OFF_B = np.array([[0.0, 0.5, 0.5], [0.5, 0.0, 0.5], [0.5, 0.5, 0.0]])
OFF6 = np.vstack([OFF_E, OFF_B])
OFF6_ZERO = np.zeros_like(OFF6)         # bad-placement storage semantics


# ===========================================================================
#  PART A. the systems (pure fp64 update rules; spatial axes = last three)
# ===========================================================================
def _dp(f, ax):
    """forward difference f(x+e)-f(x)."""
    return np.roll(f, -1, axis=ax) - f


def _dm(f, ax):
    """backward difference f(x)-f(x-e)."""
    return f - np.roll(f, 1, axis=ax)


def _dc(f, ax):
    """central difference (the bad-placement calculus)."""
    return 0.5 * (np.roll(f, -1, axis=ax) - np.roll(f, 1, axis=ax))


def curl(F, d):
    """(curl F) with difference operator d; F shape (3, ..., N, N, N)."""
    ax = (-3, -2, -1)
    return np.stack([d(F[2], ax[1]) - d(F[1], ax[2]),
                     d(F[0], ax[2]) - d(F[2], ax[0]),
                     d(F[1], ax[0]) - d(F[0], ax[1])])


def div(F, d):
    return d(F[0], -3) + d(F[1], -2) + d(F[2], -1)


def step_yee(state):
    """state = (E^n, B^{n-1/2}) -> (E^{n+1}, B^{n+1/2}).  Standard Yee:
    curl_fwd for the B update (E on edges -> circulation on faces),
    curl_bwd for the E update.  div_bwd(curl_bwd) == 0 and
    div_fwd(curl_fwd) == 0 are exact lattice identities."""
    E, B = state
    B = B - DT * curl(E, _dp)
    E = E + DT * curl(B, _dm)
    return (E, B)


def make_step_proca(m):
    """S1: lattice Proca (massive photon), placement-faithful.

    First-order Proca system with E = -dA/dt - grad A0 and the ALGEBRAIC
    nu=0 field equation A0 = -div E / m^2 (Proca has no gauge freedom; A0
    is a dependent variable).  On the Yee complex: A_i on E-edges at half
    times, A0 at nodes:
        A0^n      = -div_bwd(E^n) / m^2
        A^{n+1/2} = A^{n-1/2} - DT (E^n + grad_fwd A0^n)
        B^{n+1/2} = B^{n-1/2} - DT curl_fwd E^n
        E^{n+1}   = E^n + DT (curl_bwd B^{n+1/2} + m^2 A^{n+1/2})
    (sign check: transverse d2A/dt2 = -curl B - m^2 A = lap A - m^2 A ->
    w^2 = k^2 + m^2; longitudinal picks up the same via the A0 term.)
    In the half-angle calculus ALL three polarizations sit exactly on
    sin^2(w DT/2) = (DT/2)^2 (k_chord^2 + m^2): one massive line, rank 3."""
    m2 = m * m

    def step(state):
        E, B, A = state
        A0 = -div(E, _dm) / m2
        gA0 = np.stack([_dp(A0, -3), _dp(A0, -2), _dp(A0, -1)])
        A = A - DT * (E + gA0)
        B = B - DT * curl(E, _dp)
        E = E + DT * (curl(B, _dm) + m2 * A)
        return (E, B, A)
    return step


def step_bad(state):
    """S2: bad placement -- all components at integer nodes, central
    differences in both curls (leapfrog time kept).  The Yee constraint
    STRUCTURE (staggered complex) is gone; dispersion symbol degrades from
    2 sin(k/2) (half-angle chord) to sin(k) (full angle) -> wrong speed at
    every k and a frozen Nyquist mode (sin(pi) = 0)."""
    E, B = state
    B = B - DT * curl(E, _dc)
    E = E + DT * curl(B, _dc)
    return (E, B)


# ===========================================================================
#  PART B. analytic references (the 对拍 targets)
# ===========================================================================
def kvec_of(nv):
    return np.array(nv, float) * (2.0 * np.pi / N)


def k_chord(kl):
    return float(np.sqrt(sum(4.0 * math.sin(k / 2.0) ** 2 for k in kl)))


def yee_omega(kl, dt=DT):
    """exact Yee vacuum dispersion: sin^2(w dt/2) = dt^2 sum_j sin^2(k_j/2)."""
    s = math.sqrt(sum(math.sin(k / 2.0) ** 2 for k in kl))
    return (2.0 / dt) * math.asin(dt * s)


def central_omega(kl, dt=DT):
    """the bad-placement scheme's OWN dispersion: sin(w dt/2) = (dt/2)|sin k|."""
    s = math.sqrt(sum(math.sin(k) ** 2 for k in kl))
    return (2.0 / dt) * math.asin(dt * s / 2.0)


def plane(kl):
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    return np.exp(1j * (kl[0] * X + kl[1] * Y + kl[2] * Z))


def colfac(kl, off6):
    """physical-frame un-shift phases exp(-i k.off) per component."""
    return np.exp(-1j * (off6 @ np.asarray(kl)))


# ===========================================================================
#  PART C. exact one-step 6x6 mode matrix (operator-level oracle, the same
#          methodology as cp1_v4_L1.onshell_mode) + its certificates
# ===========================================================================
def mode_matrix(kl, step, off6):
    """probe the ACTUAL stepper with unit single-component plane waves seeded
    at their declared placement; project back in the physical frame."""
    ph = plane(kl)
    proj = np.conj(ph) / N ** 3
    cf = colfac(kl, off6)
    M = np.zeros((6, 6), complex)
    for c in range(6):
        E = np.zeros((3, N, N, N), complex)
        B = np.zeros((3, N, N, N), complex)
        if c < 3:
            E[c] = ph / cf[c]           # stored sample carries e^{+i k.off}
        else:
            B[c - 3] = ph / cf[c]
        E2, B2 = step((E, B))
        amp = np.array([np.sum(proj * E2[j]) for j in range(3)]
                       + [np.sum(proj * B2[j]) for j in range(3)])
        M[:, c] = amp * cf
    return M


def yee_oracle(kl):
    """eigen-analysis of the true Yee mode matrix + certificates:
    (i) propagating eigenfrequency == analytic formula (machine);
    (ii) the propagating eigenmodes, re-seeded as lattice fields, have
         machine-zero lattice div E and div B (Gauss-transverse photons)."""
    M = mode_matrix(kl, step_yee, OFF6)
    lam, V = np.linalg.eig(M)
    ang = np.angle(lam)
    w_ref = yee_omega(kl)
    out = {"w_yee_analytic": w_ref}
    # unitarity of the propagating sector (symplectic leapfrog): |lam| = 1
    out["eig_absdev_max"] = float(np.abs(np.abs(lam) - 1.0).max())
    sel_p = np.where(np.abs(ang - w_ref * DT) < 1e-6)[0]
    sel_m = np.where(np.abs(ang + w_ref * DT) < 1e-6)[0]
    out["n_eig_plus"], out["n_eig_minus"] = len(sel_p), len(sel_m)
    out["w_op_vs_analytic"] = float(
        np.abs(np.abs(ang[sel_p]) / DT - w_ref).max()) \
        if len(sel_p) else float("nan")
    # Gauss certificate of the propagating eigenvectors (lattice-level)
    cf = colfac(kl, OFF6)
    ph = plane(kl)
    worst_div = 0.0
    for j in list(sel_p) + list(sel_m):
        v = V[:, j]
        E = np.stack([(v[c] / cf[c]) * ph for c in range(3)])
        B = np.stack([(v[c + 3] / cf[c + 3]) * ph for c in range(3)])
        dE = float(np.abs(div(E, _dm)).max()) / (np.abs(E).max() + 1e-300)
        dB = float(np.abs(div(B, _dp)).max()) / (np.abs(B).max() + 1e-300)
        worst_div = max(worst_div, dE, dB)
    out["eigmode_gauss_resid"] = worst_div
    out["V"], out["lam"] = V, lam
    out["PASS"] = bool(len(sel_p) == 2 and len(sel_m) == 2
                       and out["w_op_vs_analytic"] < 1e-12
                       and worst_div < 1e-12
                       and out["eig_absdev_max"] < 1e-12)
    return out


# ===========================================================================
#  PART D. the judge pipeline (variant-agnostic; identical for all columns)
# ===========================================================================
def seed_generic(nfield, seed):
    """fully generic raw random IC on every stored real component
    (judge-faithful: constraint-violating + longitudinal content included)."""
    rng = np.random.default_rng(seed)
    return tuple(rng.standard_normal((3, TRIALS, N, N, N)) for _ in range(nfield))


def solenoidal_project(F, kind):
    """FFT projection of stored E ('E', backward div) or B ('B', forward div)
    onto the lattice-solenoidal subspace, using the scheme's OWN div symbols
    d_j = 1 - e^{-ik_j} (E) / e^{ik_j} - 1 (B)."""
    k1 = 2.0 * np.pi * np.fft.fftfreq(N)
    KX, KY, KZ = np.meshgrid(k1, k1, k1, indexing="ij")
    if kind == "E":
        d = np.stack([1.0 - np.exp(-1j * KX), 1.0 - np.exp(-1j * KY),
                      1.0 - np.exp(-1j * KZ)])
    else:
        d = np.stack([np.exp(1j * KX) - 1.0, np.exp(1j * KY) - 1.0,
                      np.exp(1j * KZ) - 1.0])
    d2 = np.sum(np.abs(d) ** 2, axis=0)
    d2[d2 == 0] = 1.0
    Fh = np.fft.fftn(F, axes=(-3, -2, -1))
    dv = np.einsum("jxyz,jrxyz->rxyz", d, Fh)
    Fh = Fh - np.conj(d)[:, None] * (dv / d2)[None]
    return np.real(np.fft.ifftn(Fh, axes=(-3, -2, -1)))


def evolve_record(state, step, kinfos, T, energy=False):
    """evolve; per step record the physical-frame 6-comp (E,B) mode amplitude
    at every probe k; monitor div drift, rms, optional Yee energy invariant."""
    nk = len(kinfos)
    projs = np.stack([np.conj(plane(ki["kl"])) / N ** 3 for ki in kinfos])
    cfs = np.stack([ki["cf"] for ki in kinfos])           # (nk, 6)
    rec = np.zeros((T, TRIALS, nk, 6), complex)
    divE0 = div(state[0], _dm).copy()
    divB0 = div(state[1], _dp).copy()
    sc_E = float(np.abs(state[0]).max()) + 1e-300
    dE_drift = dB_drift = 0.0
    rms0 = float(np.sqrt(np.mean(state[0] ** 2 + state[1] ** 2)))
    Hs = []
    for t in range(T):
        if energy:
            E_old, B_old = state[0], state[1]
        state = step(state)
        E, B = state[0], state[1]
        F6 = np.concatenate([E, B])                       # (6, TRIALS, N,N,N)
        rec[t] = np.einsum("kxyz,crxyz->rkc", projs, F6) * cfs[None]
        if energy:
            # exact Yee invariant  H^n = |E^n|^2 + B^{n-1/2}.B^{n+1/2}
            Hs.append(float(np.sum(E_old * E_old) + np.sum(B_old * B)))
        if t % 64 == 0 or t == T - 1:
            dE_drift = max(dE_drift,
                           float(np.abs(div(E, _dm) - divE0).max()) / sc_E)
            dB_drift = max(dB_drift,
                           float(np.abs(div(B, _dp) - divB0).max()) / sc_E)
    rms_end = float(np.sqrt(np.mean(state[0] ** 2 + state[1] ** 2)))
    mon = {"divE_drift_rel": dE_drift, "divB_drift_rel": dB_drift,
           "rms_first": rms0, "rms_last": rms_end,
           "rms_growth": rms_end / (rms0 + 1e-300),
           "stable": bool(np.isfinite(rms_end) and rms_end < 1e3 * rms0)}
    if energy and len(Hs) > 2:
        Hs = np.array(Hs)
        mon["yee_energy_drift_rel"] = float(
            np.abs(Hs - Hs[0]).max() / (abs(Hs[0]) + 1e-300))
    return rec, mon, state


def spectral_lines(rec_k, dt=DT, max_lines=3, rel_floor=1e-2):
    """multi-line spectral count for one probe k.  rec_k (T, trials, 6).
    Two-sided windowed FFT of the tail half; iteratively locate distinct
    |w| lines (mirror-masked); per line: parabolic-interpolated w, stacked
    peak-bin amplitude matrix -> SVD -> rank.  N_prop = sum of line ranks.
    Identical code path for every variant (the pipeline IS the judge)."""
    T = rec_k.shape[0]
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    F = np.fft.fft(rec_k[T0:] * win[:, None, None], axis=0)
    freqs = 2.0 * np.pi * np.fft.fftfreq(W) / dt
    df = 2.0 * np.pi / (W * dt)
    dc_cut = max(0.06, 6.0 * df)        # static content leaks ~6 bins (Hann)
    band = (np.abs(freqs) > dc_cut) & (np.abs(freqs) < 0.9 * np.pi / dt)
    # band-edge bins per sign side, for the prominence guard (a static
    # field's window skirt "peaks" at the first allowed bin -> NOT a
    # propagating line; same guard as emergence_judge)
    pos = np.where(band & (freqs > 0))[0]
    neg = np.where(band & (freqs < 0))[0]
    edge_p = pos[np.argmin(freqs[pos])] if len(pos) else -1
    edge_m = neg[np.argmax(freqs[neg])] if len(neg) else -1
    P = np.sum(np.abs(F) ** 2, axis=(1, 2))
    Pw = np.where(band, P, 0.0)
    total = float(Pw.sum())
    lines = []
    if total < 1e-16:
        return {"lines": [], "n_prop": 0, "no_peak": True,
                "inband_power": total, "bin_width": df}
    P0 = None
    rejected = []
    work = Pw.copy()
    for _ in range(2 * max_lines):
        if len(lines) >= max_lines:
            break
        pk = int(np.argmax(work))
        if work[pk] <= 0:
            break
        if P0 is not None and P[pk] < rel_floor * P0:
            break
        # prominence guard vs the band-edge (DC-skirt) bin on this side
        edge = edge_p if freqs[pk] > 0 else edge_m
        prominence = float(P[pk] / (P[edge] + 1e-300))
        if abs(pk - edge) <= 2 or prominence < 4.0:
            rejected.append({"w": float(abs(freqs[pk])),
                             "power": float(P[pk]),
                             "reason": "band-edge skirt, prominence %.2f"
                                       % prominence})
            wm = 6
            for b0 in (pk, int(np.argmin(np.abs(freqs + freqs[pk])))):
                lo, hi = max(0, b0 - wm), min(W, b0 + wm + 1)
                work[lo:hi] = 0.0
            continue
        if P0 is None:
            P0 = float(P[pk])
        # parabolic interpolation on log power (guarded at band edges)
        wl = float(freqs[pk])
        if 0 < pk < W - 1 and P[pk - 1] > 0 and P[pk + 1] > 0:
            l, c, r = np.log(P[pk - 1]), np.log(P[pk]), np.log(P[pk + 1])
            den = l - 2 * c + r
            delta = 0.5 * (l - r) / den if abs(den) > 1e-300 else 0.0
            delta = float(np.clip(delta, -0.5, 0.5))
            wl = float(freqs[pk] + delta * df * np.sign(freqs[1] - freqs[0]))
        A = F[pk]                                          # (trials, 6)
        sv = np.linalg.svd(A, compute_uv=False)
        svn = (sv / (sv[0] + 1e-300)).tolist()
        rank = int(np.sum(np.array(svn) > SV_THRESH))
        _, _, Vh = np.linalg.svd(A, full_matrices=False)
        lines.append({"w": abs(wl), "w_signed": wl, "bin": pk,
                      "power": float(P[pk]), "power_rel": float(P[pk] / P0),
                      "prominence": prominence,
                      "sv": [float(v) for v in svn[:6]], "rank": rank,
                      "sv3": float(svn[2]) if len(svn) > 2 else 0.0,
                      "Vh2": Vh[:2]})
        # mask this line and its mirror
        wm = 6
        for b0 in (pk, int(np.argmin(np.abs(freqs + freqs[pk])))):
            lo, hi = max(0, b0 - wm), min(W, b0 + wm + 1)
            work[lo:hi] = 0.0
    n_prop = int(sum(l["rank"] for l in lines))
    return {"lines": lines, "n_prop": n_prop, "no_peak": len(lines) == 0,
            "rejected": rejected, "inband_power": total, "bin_width": df}


def transverse_match(line, oracle):
    """principal-angle overlap of the data's top-2 amplitude space with the
    exact stepper eigenmode pair on the peak's branch (photon reference)."""
    lam, V = oracle["lam"], oracle["V"]
    target = np.exp(1j * line["w_signed"] * DT)
    idx = np.argsort(np.abs(lam - target))[:2]
    # rows of A live in span{rows of Vh} (A = U S Vh): column basis = Vh.T
    Q1, _ = np.linalg.qr(line["Vh2"].T)
    Q2, _ = np.linalg.qr(V[:, idx])
    cosang = np.linalg.svd(Q1.conj().T @ Q2, compute_uv=False)
    return float(np.min(cosang) ** 2)


def judge(name, state, step, T=T_MAIN, off6=OFF6, energy=False,
          oracles=None):
    """the full judge for one system: evolve generic data, per-k multi-line
    count + dispersion 对拍 vs the TRUE Yee analytic line + SV/transverse
    gates + constraint monitors.  Returns the per-k table + monitor."""
    kinfos = [{"nv": nv, "kl": kvec_of(nv), "cf": colfac(kvec_of(nv), off6)}
              for nv in KM_ALL]
    rec, mon, _ = evolve_record(state, step, kinfos, T, energy=energy)
    per_k = {}
    for ki, nv in enumerate(KM_ALL):
        kl = kinfos[ki]["kl"]
        sp = spectral_lines(rec[:, :, ki, :])
        e = {"n_prop": sp["n_prop"], "no_peak": sp["no_peak"],
             "bin_width": sp["bin_width"],
             "w_yee": yee_omega(kl), "k_chord": k_chord(kl),
             "k_norm": float(np.linalg.norm(kl))}
        e["c_yee"] = e["w_yee"] / e["k_norm"]
        if sp["lines"]:
            main = sp["lines"][0]
            e["w_meas"] = main["w"]
            e["w_meas_vs_yee"] = abs(main["w"] - e["w_yee"])
            e["c_meas"] = main["w"] / e["k_norm"]
            e["sv3_main"] = main["sv3"]
            e["sv_main"] = main["sv"]
            if oracles is not None:
                e["transverse_match"] = transverse_match(main, oracles[nv])
            e["lines"] = [{k: v for k, v in l.items() if k != "Vh2"}
                          for l in sp["lines"]]
        per_k[str(nv)] = e
    return {"name": name, "monitor": mon, "per_k": per_k}


# ===========================================================================
#  PART E. gate evaluation
# ===========================================================================
def eval_positive_gates(res, oracles, res_sol):
    P = res["per_k"]
    g = {}
    g["P1_nprop2_all_k"] = bool(all(P[str(nv)]["n_prop"] == 2
                                    for nv in KM_ALL))
    g["P1_nprop_list"] = [P[str(nv)]["n_prop"] for nv in KM_ALL]
    g["P1_sv3_max"] = float(max(P[str(nv)].get("sv3_main", 1.0)
                                for nv in KM_ALL))
    g["P1_sv3_ok"] = bool(g["P1_sv3_max"] < SV_THRESH)

    wop = max(o["w_op_vs_analytic"] for o in oracles.values())
    g["P2_w_op_vs_analytic_max"] = float(wop)
    devs = [P[str(nv)].get("w_meas_vs_yee", np.inf) for nv in KM_ALL]
    binw = P[str(KM_ALL[0])]["bin_width"]
    g["P2_w_meas_vs_yee_max"] = float(max(devs))
    g["P2_bin_width"] = float(binw)
    cdev = [abs(P[str(nv)].get("c_meas", np.inf) / P[str(nv)]["c_yee"] - 1.0)
            for nv in KM_SMALLK]
    g["P2_c_vs_cyee_reldev_max"] = float(max(cdev))
    g["P2_dispersion_table"] = {
        str(nv): {"w_yee": P[str(nv)]["w_yee"],
                  "w_meas": P[str(nv)].get("w_meas"),
                  "c_yee": P[str(nv)]["c_yee"],
                  "c_meas": P[str(nv)].get("c_meas"),
                  "c_yee_minus_1": P[str(nv)]["c_yee"] - 1.0,
                  "c_meas_minus_1": (P[str(nv)].get("c_meas", np.nan) - 1.0)}
        for nv in KM_ALL}
    g["P2_ok"] = bool(wop < 1e-12 and max(devs) < binw
                      and max(cdev) < 2e-2)

    ciso = [P[str(nv)].get("c_meas", np.nan) for nv in KM_ISO]
    g["P3_iso_c"] = [float(v) for v in ciso]
    g["P3_iso_spread"] = float((max(ciso) - min(ciso))
                               / (np.mean(ciso) + 1e-300))
    g["P3_ok"] = bool(np.isfinite(g["P3_iso_spread"])
                      and g["P3_iso_spread"] < 1e-3)

    m = res["monitor"]
    g["P4_div_drift"] = {"divE": m["divE_drift_rel"],
                         "divB": m["divB_drift_rel"]}
    g["P4_sol_div_max"] = {"divE": res_sol["divE_max_rel"],
                           "divB": res_sol["divB_max_rel"]}
    g["P4_ok"] = bool(m["divE_drift_rel"] < 1e-12
                      and m["divB_drift_rel"] < 1e-12
                      and res_sol["divE_max_rel"] < 1e-12
                      and res_sol["divB_max_rel"] < 1e-12)

    g["P5_rms_growth"] = m["rms_growth"]
    g["P5_energy_drift"] = m.get("yee_energy_drift_rel")
    g["P5_ok"] = bool(m["stable"] and m["rms_growth"] < 10.0)

    tms = [P[str(nv)].get("transverse_match", 0.0) for nv in KM_ALL]
    g["P6_transverse_match_min"] = float(min(tms))
    g["P6_eig_gauss_resid_max"] = float(max(o["eigmode_gauss_resid"]
                                            for o in oracles.values()))
    g["P6_ok"] = bool(min(tms) > 0.95
                      and g["P6_eig_gauss_resid_max"] < 1e-12)

    g["ALL_PASS"] = bool(g["P1_nprop2_all_k"] and g["P1_sv3_ok"]
                         and g["P2_ok"] and g["P3_ok"] and g["P4_ok"]
                         and g["P5_ok"] and g["P6_ok"])
    return g


def eval_sick(res, expect_nprop=2):
    """apply the SAME gates to a sick variant; collect which gates break."""
    P = res["per_k"]
    breaks = []
    nprops = [P[str(nv)]["n_prop"] for nv in KM_ALL]
    if any(n != 2 for n in nprops):
        breaks.append("N_prop != 2 (%s)" % nprops)
    devs = [P[str(nv)].get("w_meas_vs_yee", np.inf) for nv in KM_ALL]
    binw = P[str(KM_ALL[0])]["bin_width"]
    if max(devs) > binw:
        breaks.append("dispersion 对拍 |w_meas - w_yee| = %.3f >> bin %.3f"
                      % (max(devs), binw))
    cdev = [abs(P[str(nv)].get("c_meas", np.inf) / P[str(nv)]["c_yee"] - 1.0)
            for nv in KM_SMALLK]
    if max(cdev) > 2e-2:
        breaks.append("|c_meas/c_yee - 1| = %.3f > 2e-2" % max(cdev))
    return {"nprops": nprops, "w_dev_max": float(max(devs)),
            "c_reldev_max": float(max(cdev)), "breaks": breaks,
            "FAILS_as_required": bool(len(breaks) > 0)}


# ===========================================================================
#  main
# ===========================================================================
if __name__ == "__main__":
    t_start = time.time()
    print("photon_control -- cannon #10 measured half: Yee-EM positive "
          "control of the emergence judge")
    print("=" * 74)
    out = {"N": N, "dt": DT, "T": T_MAIN, "trials": TRIALS,
           "sv_thresh": SV_THRESH, "m_proca": M_PROCA,
           "k_probes": [list(v) for v in KM_ALL],
           "seeds": {"true": SEED_TRUE, "sol": SEED_SOL,
                     "proca": SEED_PROCA, "bad": SEED_BAD}}

    # -- A. operator-level oracle + certificates ---------------------------
    print("[A] Yee mode-matrix oracle (operator == analytic, machine):")
    oracles = {}
    for nv in KM_ALL:
        o = yee_oracle(kvec_of(nv))
        oracles[nv] = o
        print("    k=%-9s w_yee=%.6f  |w_op-w_yee|=%.1e  eig|.|-1=%.1e  "
              "gauss(eigmode)=%.1e  n(+w)=%d -> %s"
              % (nv, o["w_yee_analytic"], o["w_op_vs_analytic"],
                 o["eig_absdev_max"], o["eigmode_gauss_resid"],
                 o["n_eig_plus"], "PASS" if o["PASS"] else "FAIL"))
    out["oracle"] = {str(nv): {k: v for k, v in o.items()
                               if k not in ("V", "lam")}
                     for nv, o in oracles.items()}
    oracle_pass = all(o["PASS"] for o in oracles.values())

    # -- B. TRUE Yee run (generic IC) --------------------------------------
    print("\n[B] TRUE Yee-EM, generic random IC, %d^3, T=%d, trials=%d ..."
          % (N, T_MAIN, TRIALS))
    st = seed_generic(2, SEED_TRUE)
    res_true = judge("yee_true", st, step_yee, energy=True, oracles=oracles)
    out["yee_true"] = res_true

    # -- B'. solenoidal-projected IC (constraint machine zero throughout) --
    E0, B0 = seed_generic(2, SEED_SOL)
    E0 = solenoidal_project(E0, "E")
    B0 = solenoidal_project(B0, "B")
    sc = float(np.abs(E0).max())
    dEm = dBm = 0.0
    stt = (E0, B0)
    for t in range(256):
        stt = step_yee(stt)
        if t % 32 == 0 or t == 255:
            dEm = max(dEm, float(np.abs(div(stt[0], _dm)).max()) / sc)
            dBm = max(dBm, float(np.abs(div(stt[1], _dp)).max()) / sc)
    res_sol = {"divE_max_rel": dEm, "divB_max_rel": dBm}
    out["yee_solenoidal"] = res_sol

    gates = eval_positive_gates(res_true, oracles, res_sol)
    out["positive_gates"] = gates
    P = res_true["per_k"]
    print("    %-10s %6s %9s %9s %10s %10s %9s %9s" %
          ("k", "N_prop", "w_meas", "w_yee", "c_meas-1", "c_yee-1",
           "sv3", "trans"))
    for nv in KM_ALL:
        e = P[str(nv)]
        print("    %-10s %6d %9.5f %9.5f %+10.5f %+10.5f %9.1e %9.6f"
              % (nv, e["n_prop"], e.get("w_meas", float("nan")), e["w_yee"],
                 e.get("c_meas", float("nan")) - 1.0, e["c_yee"] - 1.0,
                 e.get("sv3_main", float("nan")),
                 e.get("transverse_match", float("nan"))))
    m = res_true["monitor"]
    print("    div drift: E %.1e  B %.1e | solenoidal-IC div: E %.1e  B %.1e"
          % (m["divE_drift_rel"], m["divB_drift_rel"], dEm, dBm))
    print("    energy invariant drift %.1e   rms growth %.3f   iso spread %.1e"
          % (m.get("yee_energy_drift_rel", float("nan")),
             m["rms_growth"], gates["P3_iso_spread"]))
    for k in ("P1_nprop2_all_k", "P1_sv3_ok", "P2_ok", "P3_ok", "P4_ok",
              "P5_ok", "P6_ok"):
        print("    %-18s -> %s" % (k, "PASS" if gates[k] else "FAIL"))
    print("    POSITIVE CONTROL: %s"
          % ("ALL GATES PASS" if gates["ALL_PASS"] and oracle_pass
             else "NOT ALL PASS -- judge or scheme bug, report honestly"))

    # -- C. sick variant 1: Proca ------------------------------------------
    print("\n[C] SICK 1 -- Proca m=%.2f (same judge, same gates):" % M_PROCA)
    stp = seed_generic(3, SEED_PROCA)
    res_proca = judge("proca", stp, make_step_proca(M_PROCA))
    ver_p = eval_sick(res_proca)
    # mass-gap diagnostic: half-angle m_eff^2 = (2 sin(w dt/2)/dt)^2 - k_chord^2
    gap = {}
    for nv in KM_ALL:
        e = res_proca["per_k"][str(nv)]
        if "w_meas" in e:
            wh = 2.0 * math.sin(e["w_meas"] * DT / 2.0) / DT
            gap[str(nv)] = wh * wh - e["k_chord"] ** 2
    ver_p["m_eff2_per_k"] = gap
    ver_p["m2_true"] = M_PROCA ** 2
    out["proca"] = {"judge": res_proca, "verdict": ver_p}
    for nv in KM_ALL:
        e = res_proca["per_k"][str(nv)]
        lw = [round(l["w"], 3) for l in e.get("lines", [])]
        lr = [l["rank"] for l in e.get("lines", [])]
        print("    k=%-9s N_prop=%d  lines w=%s ranks=%s  m_eff^2=%.4f"
              % (nv, e["n_prop"], lw, lr,
                 gap.get(str(nv), float("nan"))))
    print("    breaks: %s" % ver_p["breaks"])
    print("    -> %s" % ("FAILS as required (judge has teeth)"
                         if ver_p["FAILS_as_required"]
                         else "DID NOT BREAK -- judge toothless!"))

    # -- D. sick variant 2: bad placement ----------------------------------
    print("\n[D] SICK 2 -- bad placement (collocated + central diff):")
    stb = seed_generic(2, SEED_BAD)
    res_bad = judge("bad_placement", stb, step_bad, off6=OFF6_ZERO)
    ver_b = eval_sick(res_bad)
    # its own theory line, to show the judge measured the sick scheme right
    own = {str(nv): {"w_central_own": central_omega(kvec_of(nv)),
                     "w_meas": res_bad["per_k"][str(nv)].get("w_meas")}
           for nv in KM_ALL}
    ver_b["own_dispersion_check"] = own
    nyq = res_bad["per_k"][str((8, 0, 0))]
    ver_b["nyquist_frozen"] = {"n_prop": nyq["n_prop"],
                               "no_peak": nyq["no_peak"],
                               "w_yee_would_be": nyq["w_yee"]}
    if nyq["n_prop"] == 0:
        ver_b["breaks"].append(
            "Nyquist photon FROZEN (spurious mode): N_prop=0, Yee "
            "propagates it at w=%.3f" % nyq["w_yee"])
    ver_b["FAILS_as_required"] = bool(len(ver_b["breaks"]) > 0)
    # honest note: the bad variant's OWN central-calculus div IS conserved
    # (central ops commute algebraically), so the kill is NOT a monitor-frame
    # trick -- it is wrong dispersion + frozen Nyquist; the structural (Yee)
    # Gauss drift is reported alongside as "constraint structure gone".
    stb2 = seed_generic(2, SEED_BAD)
    d0E, d0B = div(stb2[0], _dc), div(stb2[1], _dc)
    sc2 = float(np.abs(stb2[0]).max())
    ddE = ddB = 0.0
    for t in range(256):
        stb2 = step_bad(stb2)
        if t % 32 == 0 or t == 255:
            ddE = max(ddE, float(np.abs(div(stb2[0], _dc) - d0E).max()) / sc2)
            ddB = max(ddB, float(np.abs(div(stb2[1], _dc) - d0B).max()) / sc2)
    ver_b["own_central_div_drift"] = {"divE": ddE, "divB": ddB}
    out["bad_placement"] = {"judge": res_bad, "verdict": ver_b}
    for nv in KM_ALL:
        e = res_bad["per_k"][str(nv)]
        print("    k=%-9s N_prop=%d  w_meas=%s  w_yee=%.4f  w_own=%.4f"
              % (nv, e["n_prop"],
                 ("%.4f" % e["w_meas"]) if "w_meas" in e else "  --  ",
                 e["w_yee"], own[str(nv)]["w_central_own"]))
    print("    breaks: %s" % ver_b["breaks"])
    print("    own-calculus div drift (declared): E %.1e  B %.1e "
          "(conserved -- kill is not a monitor-frame trick); structural "
          "Yee-div drift: E %.1e  B %.1e (constraint structure gone)"
          % (ddE, ddB, res_bad["monitor"]["divE_drift_rel"],
             res_bad["monitor"]["divB_drift_rel"]))
    print("    -> %s" % ("FAILS as required (judge has teeth)"
                         if ver_b["FAILS_as_required"]
                         else "DID NOT BREAK -- judge toothless!"))

    # -- E. four-column verdict table (cp1_v4 L2 cited READ-ONLY) ----------
    print("\n[E] four-column cross table (same judge family):")
    cited = {}
    try:
        with open(os.path.join(DIR, "cp1_v4_L2_results.json")) as fh:
            L2 = json.load(fh)
        A = L2["runA_per_k"]
        cited = {
            "source": "cp1_v4_L2_results.json (read-only citation)",
            "script_sha256": L2.get("script_sha256"),
            "n_prop_all_k": [A[k]["n_prop"] for k in A],
            "sv3_max": max(A[k]["sv3"] for k in A),
            "tt_match_min": min(A[k]["tt_match"] for k in A),
            "j5_ratio_dev_max": max(abs(A[k]["j5_ratio"] - 1.0) for k in A),
            "relC_last": L2["runA_monitor"]["relC_last"],
            "L2_PASS": L2["L2_PASS"]}
    except Exception as ex:                                # honest fallback
        cited = {"error": "could not read cp1_v4_L2_results.json: %r" % ex}
    out["cited_cp1v4_L2"] = cited

    def _row(label, vals):
        print("    %-22s %-16s %-18s %-20s %-16s"
              % ((label,) + tuple(str(v) for v in vals)))

    _row("", ["Yee-EM (true)", "Proca (sick)", "bad-place (sick)",
              "cp1_v4 L2 (ours)"])
    _row("N_prop", [gates["P1_nprop_list"], ver_p["nprops"],
                    ver_b["nprops"],
                    cited.get("n_prop_all_k", "?")])
    _row("dispersion dev", ["%.1e" % gates["P2_w_meas_vs_yee_max"],
                            "%.2f" % ver_p["w_dev_max"],
                            "%.2f" % ver_b["w_dev_max"],
                            "J5 dev %.0e" % cited.get("j5_ratio_dev_max", -1)])
    _row("constraint", ["drift %.0e" % m["divE_drift_rel"],
                        "(not gated)", "(structure gone)",
                        "relC %.0e" % cited.get("relC_last", -1)])
    _row("sv3 / match", ["%.0e / %.4f" % (gates["P1_sv3_max"],
                                          gates["P6_transverse_match_min"]),
                         "-", "-",
                         "%.0e / %.4f" % (cited.get("sv3_max", -1),
                                          cited.get("tt_match_min", -1))])
    _row("verdict", ["PASS" if gates["ALL_PASS"] else "FAIL",
                     "REJECTED" if ver_p["FAILS_as_required"] else "passed?!",
                     "REJECTED" if ver_b["FAILS_as_required"] else "passed?!",
                     "PASS" if cited.get("L2_PASS") else "?"])

    ok = (gates["ALL_PASS"] and oracle_pass and ver_p["FAILS_as_required"]
          and ver_b["FAILS_as_required"])
    out["oracle_all_pass"] = bool(oracle_pass)
    out["CANNON10_MEASURED_PASS"] = bool(ok)
    print("\nCANNON #10 (measured half) VERDICT: %s"
          % ("PASS -- judge passes true physics, rejects both sick variants"
             if ok else "FAIL -- see gate table (report honestly)"))

    # -- hash + write -------------------------------------------------------
    with open(os.path.abspath(__file__), "rb") as fh:
        out["script_sha256"] = hashlib.sha256(fh.read()).hexdigest()
    out["total_seconds"] = time.time() - t_start

    def _san(o):
        if isinstance(o, dict):
            return {k: _san(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_san(v) for v in o]
        if isinstance(o, np.ndarray):
            return _san(o.tolist())
        if isinstance(o, (bool, np.bool_)):
            return bool(o)
        if isinstance(o, (float, np.floating)):
            f = float(o)
            return f if np.isfinite(f) else ("inf" if f > 0 else
                                             ("-inf" if f < 0 else "nan"))
        if isinstance(o, np.integer):
            return int(o)
        return o

    jpath = os.path.join(DIR, "photon_control_results.json")
    with open(jpath, "w") as fh:
        json.dump(_san(out), fh, indent=1)
    with open(jpath, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    print("script  sha256 = %s" % out["script_sha256"])
    print("results sha256 = %s" % jsha)
    print("total %.0fs   wrote photon_control_results.json" % out["total_seconds"])
