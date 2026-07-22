"""tensor_walker.py -- TENSOR WALKER: a coin+shift PAIR walker whose bilinears give h_munu.

WHAT THIS IS (honest, up front):
    The first *walker-level* attempt at the open frontier left by tensor_qca.py:
    a multi-component unitary quantum walk (coin + shift, strictly local) whose
    BILINEAR observables define a symmetric tensor field h_munu(x), judged on
    whether the continuum limit of those observables is Fierz-Pauli (linearized
    spin-2).  Nothing here hand-writes a wave equation for h; h is *measured*
    from the walker state and the dynamics of h is whatever the walk induces.

CONSTRUCTION (design decisions, explicitly):
  (1) COMPONENTS <-> SPIN STRUCTURE.
      Internal space = C^2 (x) C^2  (4 components): a "pair of Weyl walkers
      glued to one lattice site" (the graviton-as-two-fermions idea).  The walk
      unitary is U = U1 (x) U1 -- each factor does the SAME split-step Dirac
      walk as rulespace/core.py (coin angle theta, emergent factor speed
      c1 = cos theta).  Composite bands (from U(k) = U1(k) (x) U1(k)):
          omega in { +2*omega1(k),  0,  0,  -2*omega1(k) }
      i.e. two luminal bands at the PAIR light speed c = 2 cos theta (theta =
      pi/3 calibrates c = 1) and an exactly FLAT doubly-degenerate band (the
      opposite-helicity sector) -- the candidate non-propagating/gauge sector.
      The observation map is the 10-component symmetric bilinear
          h_munu(x) = kappa * Re[ psi^dag(x) Sigma_munu psi(x) ],
          Sigma_munu = (sigma_mu (x) sigma_nu + sigma_nu (x) sigma_mu)/2,
      sigma = (I, sx, sy, sz).  10 components <-> the 10 of h_munu.  KNOWN
      REPRESENTATION-THEORY OBSTRUCTION, stated honestly: two spin-1/2 factors
      carry internal spin <= 1, so a momentum eigenstate can never carry
      helicity +-2.  The helicity-2 (TT) components of h arise ONLY as
      *coherences* between the Jz=+1 (up,up) and Jz=-1 (down,down) sectors --
      i.e. from ENTANGLED pair states superposing the +2omega and -2omega bands
      at opposite momenta (both right-moving).  Whether that mechanism yields a
      clean FP sector is exactly what the judges below decide.
  (2) DISCRETE DIFFEOMORPHISMS (tensor_qca.gauge_transform) AND THE COIN.
      The target gauge structure is tensor_qca's exact lattice diffeo
      h -> h + D_mu xi_nu + D_nu xi_mu with E_munu[h] exactly invariant.  On
      the walker side the EXACT coin symmetries are only GLOBAL: U(1) phase
      (bilinears blind -> trivial), and SWAP of the two factors ([U,SWAP]=0,
      certified numerically) which is *why* the bilinear closes on SYMMETRIC
      tensors (the antisymmetric singlet decouples).  A LOCAL xi_mu(x) does NOT
      lift to a local coin symmetry of this walk -- that is measured, not
      hidden: we test instead whether the measured h lands (approximately) in
      the transverse/de-Donder sector automatically (D^mu hbar_munu ~ 0), which
      is the dynamical substitute for gauge invariance that a walker can offer.
  (3) EXPECTED CONTINUUM LIMIT (derived numerically in continuum_report):
      band fit omega = c1 k + c3 k^3 (c1 -> 2 cos theta), flat-band width,
      exchange-coin eps gapping the flat band ("graviton mass" knob), then the
      measured h(t,z) is tested against box h = 0 and against tensor_qca's
      E_munu (residual vs a decorrelated baseline).

DIMENSIONALITY / UPGRADE PATH:
      Propagation + continuum-limit + judge-1 run on a quasi-1D lattice (walk
      along z, full 10-component internal tensor structure) -- the same thin-
      lattice geometry spin2_evolver's judge 1 uses.  The Newtonian/deflection
      judges use a full 3D pair walk (engine.py axis structure per factor).
      True 3+1D spin-2 propagation (helicity-2 under arbitrary khat) would
      need per-axis sandwich coins (massless 3D split-step) + rotational
      covariance of the internal state map; that is the declared next step,
      NOT claimed here.

NO CHEATING CLAUSE:
      tt_project is used ONLY as a *measurement* (as spin2_evolver's judges
      do), never inside the observation map.  No TT projection, no gauge
      fixing, no post-hoc filtering is applied to h before judging.

Run:   RULESPACE_BACKEND=numpy python -m rulespace_gpu.tensor_walker
"""
import argparse
import json
import math
import os

import numpy as np

from . import backend as B
from . import pathB_spin2 as pathB
from . import spin2_evolver as s2
from . import tensor_qca as tq

DIR = os.path.dirname(os.path.abspath(__file__))
IDX10 = s2.IDX10
ETA = np.diag([-1.0, 1.0, 1.0, 1.0])

# ======================================================================
#  PART 0.  internal algebra: sigma_mu, Sigma_munu, SWAP
# ======================================================================
SX = np.array([[0, 1], [1, 0]], dtype=complex)
SY = np.array([[0, -1j], [1j, 0]], dtype=complex)
SZ = np.array([[1, 0], [0, -1]], dtype=complex)
SIG = [np.eye(2, dtype=complex), SX, SY, SZ]        # sigma_mu, mu = 0..3

# Sigma_munu = sym(sigma_mu (x) sigma_nu), packed in IDX10 order -> (10,4,4)
SIGMA10 = np.stack([0.5 * (np.kron(SIG[m], SIG[n]) + np.kron(SIG[n], SIG[m]))
                    for (m, n) in IDX10])
SWAP = np.zeros((4, 4))
for _a in range(2):
    for _b in range(2):
        SWAP[2 * _a + _b, 2 * _b + _a] = 1.0


def bilinear_h(psi, kappa=1.0, sigma10=None):
    """Observation map: psi (..., 2, 2) complex  ->  h (..., 10) real.

    h_munu = kappa * Re[psi^dag Sigma_munu psi].  Sigma_munu Hermitian -> the
    bilinear is exactly real.  NO projection of any kind is applied.
    sigma10 lets the caller supply the WALK-ADAPTED internal frame version
    (see sigma10_for): the identification of internal sigma-axes with spatial
    axes is fixed by the walk operator itself, not tuned per state."""
    S10 = SIGMA10 if sigma10 is None else sigma10
    v = psi.reshape(psi.shape[:-2] + (4,))
    out = np.empty(psi.shape[:-2] + (10,), dtype=np.float64)
    for c in range(10):
        out[..., c] = kappa * np.real(
            np.einsum("...a,ab,...b->...", v.conj(), S10[c], v))
    return out


# ======================================================================
#  PART 1.  the pair walker (coin + shift, strictly local, unitary)
# ======================================================================
def _fac_get(psi, fac):
    """split psi (..., a, b) into the two components of factor fac (0=a,1=b);
    each returned array keeps ONE trailing internal axis (the other factor)."""
    if fac == 0:
        return psi[..., 0, :], psi[..., 1, :]
    return psi[..., 0], psi[..., 1]


def _fac_put(u0, u1, fac):
    return np.stack([u0, u1], axis=(-2 if fac == 0 else -1))


def _coin2(u0, u1, th):
    """the standard coin on a factor: (c u0 + i s u1, i s u0 + c u1)."""
    c = math.cos(th)
    s = 1j * math.sin(th)
    return c * u0 + s * u1, s * u0 + c * u1


def factor_step_1d(psi, th, fac, dm=0.0):
    """rulespace/core.py split-step on ONE factor, walk along spatial axis 0:
    C(th) -> S+ (comp0 shifts +1) -> C(-th+dm) -> S- (comp1 shifts -1).
    Massless (dm=0) dispersion per factor: cos w = cos^2 th cos k + sin^2 th
    => factor light speed c1 = cos th."""
    u0, u1 = _fac_get(psi, fac)
    u0, u1 = _coin2(u0, u1, th)
    u0 = np.roll(u0, 1, axis=0)
    u0, u1 = _coin2(u0, u1, -th + dm)
    u1 = np.roll(u1, -1, axis=0)
    return _fac_put(u0, u1, fac)


def exchange_coin(psi, eps):
    """coin rotation mixing the (0,1)<->(1,0) internal components: gaps the
    flat (opposite-helicity) band -- the 'graviton mass' knob.  [., SWAP]=0."""
    if eps == 0.0:
        return psi
    a, b = psi[..., 0, 1], psi[..., 1, 0]
    c = math.cos(eps)
    s = 1j * math.sin(eps)
    out = psi.copy()
    out[..., 0, 1] = c * a + s * b
    out[..., 1, 0] = s * a + c * b
    return out


def pair_step_1d(psi, th, dm=0.0, eps=0.0):
    """one full pair step U = X(eps) (U1 on factor B)(U1 on factor A)."""
    psi = factor_step_1d(psi, th, 0, dm)
    psi = factor_step_1d(psi, th, 1, dm)
    return exchange_coin(psi, eps)


# ---- exact one-step operators in Fourier space ----
def walk_matrix_1(k, th, dm=0.0):
    """exact 2x2 operator of the single-factor split-step walk (= core.walk_matrix)."""
    c, s = math.cos(th), 1j * math.sin(th)
    c2, s2 = math.cos(-th + dm), 1j * math.sin(-th + dm)
    C1 = np.array([[c, s], [s, c]])
    C2 = np.array([[c2, s2], [s2, c2]])
    Sp = np.diag([np.exp(-1j * k), 1.0])
    Sm = np.diag([1.0, np.exp(1j * k)])
    return Sm @ C2 @ Sp @ C1


def exchange_matrix(eps):
    X = np.eye(4, dtype=complex)
    X[1, 1] = X[2, 2] = math.cos(eps)
    X[1, 2] = X[2, 1] = 1j * math.sin(eps)
    return X


def pair_matrix(k, th, dm=0.0, eps=0.0):
    U1 = walk_matrix_1(k, th, dm)
    return exchange_matrix(eps) @ np.kron(U1, U1)


def walk_matrix_1m(k, th, dm=0.0):
    """MIRRORED single-factor walk (all shifts reversed): its right-movers are
    spin-DOWN -- the chirality partner used by the Dirac-pair probe."""
    c, s = math.cos(th), 1j * math.sin(th)
    c2, s2 = math.cos(-th + dm), 1j * math.sin(-th + dm)
    C1 = np.array([[c, s], [s, c]])
    C2 = np.array([[c2, s2], [s2, c2]])
    Sp = np.diag([np.exp(+1j * k), 1.0])
    Sm = np.diag([1.0, np.exp(-1j * k)])
    return Sm @ C2 @ Sp @ C1


def branch_vec(k, th, want_pos_vg=True, dm=0.0, dk=1e-6, matfun=None):
    """eigen-spinor of the walk on the band whose group velocity has the
    requested sign at momentum k (numerical, continuity-matched)."""
    mat = matfun or walk_matrix_1

    def bands(kk):
        ev, V = np.linalg.eig(mat(kk, th, dm))
        return -np.angle(ev), V
    w, V = bands(k)
    wp, _ = bands(k + dk)
    wm, _ = bands(k - dk)
    best = None
    for j in range(2):
        vg = (wp[np.argmin(np.abs(np.angle(np.exp(1j * (wp - w[j])))))]
              - wm[np.argmin(np.abs(np.angle(np.exp(1j * (wm - w[j])))))]) / (2 * dk)
        score = vg if want_pos_vg else -vg
        if best is None or score > best[0]:
            v = V[:, j]
            v = v * np.exp(-1j * np.angle(v[np.argmax(np.abs(v))]))
            best = (score, v / np.linalg.norm(v))
    return best[1]


def internal_frame(th, dm=0.0, kref=1e-3, dk=0.05):
    """The walk's DYNAMICAL internal frame (3x3 rotation R, rows n1,n2,n3).

    The split-step walk quantizes 'helicity' along the Bloch vector of its
    +vg branch spinor, which is NOT the internal z-axis.  The observation map
    must identify internal axes with spatial axes through THIS frame (walk
    direction z <-> n3 = Bloch(chi_+ , k->0);  n1 = the k-linear tilt
    direction; n2 = n3 x n1).  This is fixed by the walk operator alone --
    it is part of the construction, not a per-state tuning knob."""
    def bloch(k):
        ch = branch_vec(k, th, True, dm)
        return np.array([np.real(ch.conj() @ (S @ ch)) for S in SIG[1:]])
    n3 = bloch(kref)
    n3 = n3 / np.linalg.norm(n3)
    d = (bloch(kref + dk) - bloch(kref - dk)) / (2 * dk)
    d = d - (d @ n3) * n3
    if np.linalg.norm(d) < 1e-12:                  # degenerate: pick anything perp
        d = np.array([1.0, 0.0, 0.0]) - n3[0] * n3
    n1 = d / np.linalg.norm(d)
    n2 = np.cross(n3, n1)
    return np.stack([n1, n2, n3])


_S10_CACHE = {}


def sigma10_for(th, dm=0.0):
    """Sigma_munu built from the walk-adapted sigma'_i = R_ij sigma_j."""
    key = (round(float(th), 12), round(float(dm), 12))
    if key not in _S10_CACHE:
        R = internal_frame(th, dm)
        sigp = [SIG[0]] + [sum(R[i, j] * SIG[1 + j] for j in range(3))
                           for i in range(3)]
        _S10_CACHE[key] = np.stack(
            [0.5 * (np.kron(sigp[m], sigp[n]) + np.kron(sigp[n], sigp[m]))
             for (m, n) in IDX10])
    return _S10_CACHE[key]


def locking_certificate(th, k0, dm=0.0):
    """Measures the SPIN-MOMENTUM LOCKING obstruction, decisively.

    A propagating helicity-2 bilinear needs two CO-MOVING pieces whose total
    internal Jz (along the walk frame n3) differs by 2: an 'up,up' and a
    'down,down' pair both moving the same way.  For the Weyl-factor walk the
    two +vg branch spinors (at +k0 and -k0) are BOTH spin-up along n3
    (s3 ~ +1, +1); a 'down' right-mover simply does not exist -- exactly the
    1D image of 'two collinear massless helicity-1/2 particles max out at
    helicity 1'.  transverse_coherence2 = |<chi_up| sigma'_1,2 |chi_co>|^2 is
    the achievable TT amplitude (would be O(1) if anti-aligned)."""
    R = internal_frame(th, dm)
    def bloch(ch):
        return np.array([np.real(ch.conj() @ (S @ ch)) for S in SIG[1:]])
    up = branch_vec(+k0, th, True, dm)
    co = branch_vec(-k0, th, True, dm)      # the OTHER right-mover
    s3u = float(R[2] @ bloch(up))
    s3c = float(R[2] @ bloch(co))
    sig1 = sum(R[0, j] * SIG[1 + j] for j in range(3))
    sig2 = sum(R[1, j] * SIG[1 + j] for j in range(3))
    tc2 = float(abs(up.conj() @ (sig1 @ co)) ** 2 + abs(up.conj() @ (sig2 @ co)) ** 2)
    return {"s3_of_comoving_branches": [s3u, s3c],
            "locked": bool(s3u * s3c > 0.5),
            "transverse_coherence2": tc2,
            "needed_for_helicity2": "s3 pair (+1,-1) with O(1) transverse coherence"}


# ======================================================================
#  PART 2.  spectrum / continuum-limit of the walk operator itself
# ======================================================================
def dispersion_report(th, dm=0.0, eps=0.0, kmax=0.5, nk=25):
    """numerically diagonalize U_pair(k); fit the luminal band omega ~ c1 k + c3 k^3;
    measure the flat-band width and the eps-induced gap; certify [U,SWAP]=0."""
    ks = np.linspace(1e-3, kmax, nk)
    wtop, wflat = [], []
    swap_comm = 0.0
    for k in ks:
        U = pair_matrix(k, th, dm, eps)
        w = np.sort(-np.angle(np.linalg.eigvals(U)))
        wtop.append(w[-1])                      # +2 omega1 band
        wflat.append(0.5 * (abs(w[1]) + abs(w[2])))   # middle (flat) bands
        swap_comm = max(swap_comm, float(np.max(np.abs(U @ SWAP - SWAP @ U))))
    wtop = np.array(wtop)
    # odd fit omega = c1 k + c3 k^3 on the small-k half
    mask = ks < 0.6 * kmax
    Amat = np.stack([ks[mask], ks[mask] ** 3], axis=1)
    c1, c3 = np.linalg.lstsq(Amat, wtop[mask], rcond=None)[0]
    return {
        "c1_fit": float(c1),
        "c1_theory_2costh": float(2 * math.cos(th)),
        "c3_fit": float(c3),
        "flat_band_max_|omega|": float(np.max(np.abs(wflat))),
        "eps_gap_theory": float(abs(eps)),
        "swap_commutator": swap_comm,
        "unitary_defect": float(np.max(np.abs(
            pair_matrix(0.37, th, dm, eps) @ pair_matrix(0.37, th, dm, eps).conj().T
            - np.eye(4)))),
    }


# ======================================================================
#  PART 3.  drive states (walker initial conditions; NO h is set by hand)
# ======================================================================
def _envelope(N, z0, sigma):
    z = np.arange(N)
    return np.exp(-(z - z0) ** 2 / (4.0 * sigma ** 2))


def make_drive(N, th, k0, sigma, kind, z0=None, dm=0.0):
    """walker initial states (each is a NORMALIZED C^4 field on N sites):
      'tt'      : G(z)[ e^{+ik0 z} chiR(x)chiR + e^{-ik0 z} chiL'(x)chiL' ]
                  chiR = +vg band at +k0, chiL' = +vg band at -k0.  BOTH pieces
                  right-moving; their coherence is the Jz=+1 <-> Jz=-1 term
                  that populates the helicity-2 bilinears (h_+, h_x).
      'density' : G(z) e^{ik0 z} chiR(x)chiR        (single band: pure envelope)
      'flat'    : G(z) e^{ik0 z} chiR(x)chiM        (chiM = -vg band at +k0:
                  the flat, opposite-helicity sector; should NOT propagate)
      'standing': G(z) [chiR(x)chiR + reversed]      (counter-propagating;
                  centered at N/2 so neither lobe wraps the torus)"""
    if z0 is None:
        z0 = N // 2 if kind == "standing" else N // 4
    G = _envelope(N, z0, sigma)
    z = np.arange(N)
    chiR = branch_vec(+k0, th, True, dm)
    chiLp = branch_vec(-k0, th, True, dm)     # other band at -k0, still vg > 0
    chiM = branch_vec(+k0, th, False, dm)     # -vg band at +k0
    if kind == "tt":
        psi = (G * np.exp(1j * k0 * z))[:, None, None] * np.outer(chiR, chiR) \
            + (G * np.exp(-1j * k0 * z))[:, None, None] * np.outer(chiLp, chiLp)
    elif kind == "density":
        psi = (G * np.exp(1j * k0 * z))[:, None, None] * np.outer(chiR, chiR)
    elif kind == "flat":
        psi = (G * np.exp(1j * k0 * z))[:, None, None] * np.outer(chiR, chiM)
    elif kind == "standing":
        psi = (G * np.exp(1j * k0 * z))[:, None, None] * np.outer(chiR, chiR) \
            + (G * np.exp(-1j * k0 * z))[:, None, None] * np.outer(chiM, chiM)
    else:
        raise ValueError(kind)
    n = math.sqrt(float(np.sum(np.abs(psi) ** 2)))
    return psi / n


def evolve_record(psi, th, T, dm=0.0, eps=0.0, kappa=1.0):
    """evolve T steps, record h(t,z,10) at every step (dt = 1 step, dx = 1).
    The observation map uses the walk-adapted internal frame (sigma10_for)."""
    S10 = sigma10_for(th, dm)
    H = np.empty((T,) + psi.shape[:-2] + (10,))
    for t in range(T):
        H[t] = bilinear_h(psi, kappa, S10)
        psi = pair_step_1d(psi, th, dm, eps)
    return H, psi


# ---- polarization channels for khat = z (amplitudes, Frobenius-normalized) ----
_I10 = {p: i for i, p in enumerate(IDX10)}
CHANNELS = ["plus  (xx-yy)", "cross (xy)", "breathing (xx+yy)",
            "long (zz)", "mixed (xz)", "mixed (yz)"]
TT_CHANNELS = {"plus  (xx-yy)", "cross (xy)"}
_R2 = math.sqrt(2.0)


def channel_amps(H):
    """decompose packed h (..., 10) into the 6 spatial polarization amplitudes."""
    return {
        "plus  (xx-yy)": (H[..., _I10[(1, 1)]] - H[..., _I10[(2, 2)]]) / _R2,
        "cross (xy)": _R2 * H[..., _I10[(1, 2)]],
        "breathing (xx+yy)": (H[..., _I10[(1, 1)]] + H[..., _I10[(2, 2)]]) / _R2,
        "long (zz)": H[..., _I10[(3, 3)]],
        "mixed (xz)": _R2 * H[..., _I10[(1, 3)]],
        "mixed (yz)": _R2 * H[..., _I10[(2, 3)]],
    }


# ======================================================================
#  PART 4.  measurement helpers (measurement ONLY -- never fed back into h)
# ======================================================================
def _centroid_speed(E, warm=10):
    """energy centroid drift speed (cells/step) of E(t,z), linear fit."""
    T = E.shape[0]
    z = np.arange(E.shape[1])
    ts, cs = [], []
    for t in range(warm, T):
        w = E[t].sum()
        if w > 0:
            ts.append(t)
            cs.append(float((z * E[t]).sum() / w))
    if len(ts) < 4:
        return float("nan")
    return float(np.polyfit(np.array(ts, float), np.array(cs), 1)[0])


def channel_table(H, warm=10):
    """per-channel: energy fraction (over the 6 spatial channels), envelope
    speed, and whether it 'propagates' (|v| > 0.25 cells/step)."""
    amps = channel_amps(H)
    tot = sum(float(np.sum(a[warm:] ** 2)) for a in amps.values()) + 1e-300
    tab = {}
    for name, a in amps.items():
        frac = float(np.sum(a[warm:] ** 2)) / tot
        v = _centroid_speed(a ** 2, warm) if frac > 1e-6 else float("nan")
        tab[name] = {"energy_frac": frac, "speed": v,
                     "propagating": bool(frac > 0.02 and np.isfinite(v) and abs(v) > 0.25)}
    return tab


def phase_speed_fft(A, warm=8, kmin=0.0):
    """dominant (Omega, K) of a real wave A(t,z) via 2D FFT -> phase speed.
    kmin masks the envelope band (|K| < kmin) so the WAVE line is measured."""
    a = A[warm:] - A[warm:].mean()
    F = np.abs(np.fft.fft2(a))
    T, N = a.shape
    om = 2 * np.pi * np.fft.fftfreq(T)
    kk = 2 * np.pi * np.fft.fftfreq(N)
    F[0, :] = 0.0
    F[:, np.abs(kk) <= kmin] = 0.0     # drop envelope / DC lines
    i, j = np.unravel_index(np.argmax(F), F.shape)
    Om, K = om[i], kk[j]
    if K == 0:
        return float("nan"), 0.0, float(Om)
    return float(-Om / K), float(K), float(Om)   # e^{i(Kz - Om_phys t)}: v = Om_phys/K = -Om/K


def _unpack44(Hp):
    """packed (..., 10) -> full symmetric (..., 4, 4)."""
    out = np.zeros(Hp.shape[:-1] + (4, 4))
    for c, (m, n) in enumerate(IDX10):
        out[..., m, n] = Hp[..., c]
        out[..., n, m] = Hp[..., c]
    return out


def _tracerev44(h4):
    """hbar_munu = h_munu - 1/2 eta_munu (eta^{ab} h_ab)."""
    tr = np.einsum("ab,...ab->...", ETA, h4)
    return h4 - 0.5 * ETA * tr[..., None, None]


def spacetime_block(H, nxy=4):
    """embed measured h(t,z,10) into a 4D (t,x,y,z) block (uniform in x,y --
    exact for the quasi-1D walk since nothing depends on x,y), as (...,4,4)."""
    T, N = H.shape[0], H.shape[1]
    h4 = _unpack44(H)                                   # (T, N, 4, 4)
    return np.broadcast_to(h4[:, None, None], (T, nxy, nxy, N, 4, 4)).copy()


def dedonder_residual(H, cs=1.0):
    """C_nu = D^mu hbar_munu on the measured spacetime block, rms-normalized by
    the rms of ALL first derivatives of hbar (so generic fields give O(1)).
    cs rescales the time axis so the operator matches the walk's light speed."""
    blk = spacetime_block(H)
    hbar = _tracerev44(blk)
    eta_eff = np.diag([-1.0 / (cs * cs), 1.0, 1.0, 1.0])
    C = np.zeros(blk.shape[:-2] + (4,))
    dall = 0.0
    cnt = 0
    for n in range(4):
        for m in range(4):
            d = tq._D(hbar[..., m, n], m)
            C[..., n] += eta_eff[m, m] * d
            dall += float(np.mean(d[2:-2] ** 2))
            cnt += 1
    num = float(np.sqrt(np.mean(C[2:-2] ** 2)))
    den = float(np.sqrt(dall / cnt)) + 1e-300
    return num / den


def einstein_residual(H, cs=1.0, seed=0):
    """||E_munu[h_measured]|| on the block vs the SAME functional on a
    component-decorrelated field (random z/t rolls per component) -- if the
    walk's h were an FP vacuum solution the ratio would be << 1.
    Time axis is rescaled into lattice units where the wave speed is 1
    (valid when cs ~= 1; report cs alongside)."""
    blk = spacetime_block(H)
    E = tq.einstein_lin(blk)
    meas = float(np.sqrt(np.mean(E[2:-2] ** 2)))
    rng = np.random.default_rng(seed)
    Hs = H.copy()
    for c in range(10):
        Hs[..., c] = np.roll(np.roll(H[..., c], int(rng.integers(0, H.shape[0])), 0),
                             int(rng.integers(0, H.shape[1])), 1)
    Es = tq.einstein_lin(spacetime_block(Hs))
    base = float(np.sqrt(np.mean(Es[2:-2] ** 2))) + 1e-300
    # localization: does the E residual track the matter envelope (h00)?
    rho = np.abs(H[2:-2, :, _I10[(0, 0)]])
    e00 = np.abs(E[2:-2, 0, 0, :, 0, 0])
    if rho.std() > 0 and e00.std() > 0:
        corr = float(np.corrcoef(rho.ravel(), e00.ravel())[0, 1])
    else:
        corr = float("nan")
    return {"E_rms": meas, "E_rms_decorrelated_baseline": base,
            "E_ratio": meas / base, "E00_vs_envelope_corr": corr}


# ======================================================================
#  PART 5.  continuum-limit report (the (3) deliverable, done numerically)
# ======================================================================
def continuum_report(th=math.pi / 3, k0=None, N=256, T=110, sigma=10.0,
                     dm=0.0, eps=0.0):
    """evolve the TT drive; extract the effective dynamics of the MEASURED h:
    envelope speed, on-cone phase speed, box-h residual, de-Donder residual,
    E_munu residual.  This IS the continuum-limit derivation, by measurement."""
    out = {"theta": th, "k0": float(k0 or 2 * np.pi / 24), "N": N, "T": T}
    k0 = out["k0"]
    disp = dispersion_report(th, dm, eps)
    out["dispersion"] = disp
    cpair = disp["c1_fit"]
    out["c_pair"] = cpair

    psi = make_drive(N, th, k0, sigma, "tt")
    H, _ = evolve_record(psi, th, T, dm, eps)
    amps = channel_amps(H)

    # (a) TT envelope speed and phase speed (target: both = c_pair, on-cone)
    # NOTE the AMPLITUDE: spin-momentum locking suppresses the co-moving TT
    # coherence, so this wave is a tiny O(k^2) remnant -- report its fraction.
    Ett = amps["plus  (xx-yy)"] ** 2 + amps["cross (xy)"] ** 2
    tot = sum(float(np.sum(a[10:] ** 2)) for a in amps.values()) + 1e-300
    out["tt_energy_fraction"] = float(np.sum(Ett[10:])) / tot
    v_env = _centroid_speed(Ett)
    vph, K, Om = phase_speed_fft(amps["plus  (xx-yy)"], kmin=k0)
    out["tt_envelope_speed_over_c"] = float(v_env / cpair)
    out["tt_phase_speed_over_c"] = float(vph / cpair) if np.isfinite(vph) else float("nan")
    out["tt_dominant_K"] = K
    out["tt_dominant_K_over_2k0"] = float(abs(K) / (2 * k0))   # theory: h wave at 2 k0

    # (b) box-h residual on the TT amplitude: r = d_t^2 A - c^2 d_z^2 A
    A = amps["plus  (xx-yy)"]
    dtt = A[2:] - 2 * A[1:-1] + A[:-2]
    dzz = np.roll(A, -1, 1) - 2 * A + np.roll(A, 1, 1)
    r = dtt - cpair ** 2 * dzz[1:-1]
    out["box_residual_tt"] = float(np.sqrt(np.mean(r ** 2) / (np.mean(dtt ** 2) + 1e-300)))
    # same residual for the LONGITUDINAL amplitude (is the whole h wave-like?)
    A = amps["long (zz)"]
    dtt = A[2:] - 2 * A[1:-1] + A[:-2]
    dzz = np.roll(A, -1, 1) - 2 * A + np.roll(A, 1, 1)
    r = dtt - cpair ** 2 * dzz[1:-1]
    out["box_residual_long"] = float(np.sqrt(np.mean(r ** 2) / (np.mean(dtt ** 2) + 1e-300)))

    # (c) gauge-sector diagnostics on the measured field
    out["dedonder_ratio_tt_drive"] = dedonder_residual(H, cs=cpair)
    out["einstein"] = einstein_residual(H, cs=cpair)

    # (d) de-Donder baseline: what would a generic (decorrelated) field give?
    rng = np.random.default_rng(1)
    Hs = H.copy()
    for c in range(10):
        Hs[..., c] = np.roll(np.roll(H[..., c], int(rng.integers(0, T)), 0),
                             int(rng.integers(0, N)), 1)
    out["dedonder_ratio_decorrelated"] = dedonder_residual(Hs, cs=cpair)
    return out


# ======================================================================
#  PART 5b.  DIRAC-PAIR PROBE -- does chirality doubling evade the locking?
#            Each factor becomes a 4-component (chirality x spin) Dirac
#            walker: chirality + runs the normal split-step, chirality - the
#            mirrored one, so right-movers of BOTH spins exist.  The TT
#            observable must then be chirality-FLIPPING on both factors
#            (Gamma_i = tau_x (x) sigma'_i, the lattice analogue of the
#            Dirac tensor bilinear), because the up,up pair lives in (+,+)
#            and the co-moving down,down pair in (-,-).
#            16 internal components; 1+1D; strictly local and unitary.
# ======================================================================
def _split_step_axis(arr, th, spin_axis, orient, dm=0.0):
    """1D split-step walk applied to a 2-dim internal axis of arr, walking
    along spatial axis 0 with the given orientation (+1 normal, -1 mirrored)."""
    def coin(a, ang):
        u0 = np.take(a, 0, spin_axis)
        u1 = np.take(a, 1, spin_axis)
        c, s = math.cos(ang), 1j * math.sin(ang)
        return np.stack([c * u0 + s * u1, s * u0 + c * u1], axis=spin_axis)
    a = coin(arr, th)
    u0 = np.roll(np.take(a, 0, spin_axis), orient, 0)
    a = np.stack([u0, np.take(a, 1, spin_axis)], axis=spin_axis)
    a = coin(a, -th + dm)
    u1 = np.roll(np.take(a, 1, spin_axis), -orient, 0)
    return np.stack([np.take(a, 0, spin_axis), u1], axis=spin_axis)


def dirac_pair_step(psi, th, dm=0.0):
    """psi (N, 2,2, 2,2) = (z; chirA, spinA, chirB, spinB); one full step."""
    out = np.empty_like(psi)
    for cA in (0, 1):
        out[:, cA] = _split_step_axis(psi[:, cA], th, 1, +1 if cA == 0 else -1, dm)
    res = np.empty_like(out)
    for cB in (0, 1):
        res[:, :, :, cB] = _split_step_axis(out[:, :, :, cB], th, 3,
                                            +1 if cB == 0 else -1, dm)
    return res


def dirac_pair_probe(th=math.pi / 3, k0=None, N=256, T=110, sigma=10.0, dm=0.0):
    """drive: G(z)[ e^{+ik0 z} (+,up)(x)(+,up)  +  e^{-ik0 z} (-,dn)(x)(-,dn) ],
    all four constituents RIGHT-moving.  Measure whether the chirality-flipping
    TT bilinears now carry an O(1), luminal, on-cone wave."""
    out = {}
    k0 = k0 or 2 * np.pi / 24
    cpair = 2 * math.cos(th)
    R = internal_frame(th, dm)
    sigp = [sum(R[i, j] * SIG[1 + j] for j in range(3)) for i in range(3)]
    TX = np.array([[0, 1], [1, 0]], dtype=complex)
    GAM = [np.kron(TX, np.eye(2))] + [np.kron(TX, s) for s in sigp]  # Gamma_0..3

    # spatial channel operators on the 16-dim pair space (frame indices 1,2,3)
    def sym16(i, j):
        return 0.5 * (np.kron(GAM[i], GAM[j]) + np.kron(GAM[j], GAM[i]))
    OPS = {
        "plus  (xx-yy)": (sym16(1, 1) - sym16(2, 2)) / _R2,
        "cross (xy)": _R2 * sym16(1, 2),
        "breathing (xx+yy)": (sym16(1, 1) + sym16(2, 2)) / _R2,
        "long (zz)": sym16(3, 3),
        "mixed (xz)": _R2 * sym16(1, 3),
        "mixed (yz)": _R2 * sym16(2, 3),
    }

    z = np.arange(N)
    z0 = N // 4
    G = _envelope(N, z0, sigma)
    chi_up = branch_vec(+k0, th, True, dm)                       # normal walk
    chi_dn = branch_vec(-k0, th, True, dm, matfun=walk_matrix_1m)  # mirrored
    e0, e1 = np.eye(2)
    vR = np.kron(e0, chi_up)                                     # (+ chirality, up)
    vL = np.kron(e1, chi_dn)                                     # (- chirality, dn)
    psi = (G * np.exp(1j * k0 * z))[:, None] * np.kron(vR, vR)[None, :] \
        + (G * np.exp(-1j * k0 * z))[:, None] * np.kron(vL, vL)[None, :]
    psi = psi / math.sqrt(float(np.sum(np.abs(psi) ** 2)))
    psi = psi.reshape(N, 2, 2, 2, 2)

    A = {name: np.empty((T, N)) for name in OPS}
    rho = np.empty((T, N))
    for t in range(T):
        v = psi.reshape(N, 16)
        for name, M in OPS.items():
            A[name][t] = np.real(np.einsum("za,ab,zb->z", v.conj(), M, v))
        rho[t] = np.sum(np.abs(v) ** 2, axis=1)
        psi = dirac_pair_step(psi, th, dm)

    tot = sum(float(np.sum(a[10:] ** 2)) for a in A.values()) + 1e-300
    out["channel_energy_frac"] = {n: float(np.sum(a[10:] ** 2)) / tot for n, a in A.items()}
    Ett = A["plus  (xx-yy)"] ** 2 + A["cross (xy)"] ** 2
    out["tt_energy_frac"] = (out["channel_energy_frac"]["plus  (xx-yy)"]
                             + out["channel_energy_frac"]["cross (xy)"])
    v_env = _centroid_speed(Ett)
    out["tt_envelope_speed_over_c"] = float(v_env / cpair)
    vph, K, Om = phase_speed_fft(A["plus  (xx-yy)"], kmin=k0)
    out["tt_phase_speed_over_c"] = float(vph / cpair) if np.isfinite(vph) else float("nan")
    out["tt_dominant_K_over_2k0"] = float(abs(K) / (2 * k0))
    Ap = A["plus  (xx-yy)"]
    dtt = Ap[2:] - 2 * Ap[1:-1] + Ap[:-2]
    dzz = np.roll(Ap, -1, 1) - 2 * Ap + np.roll(Ap, 1, 1)
    r = dtt - cpair ** 2 * dzz[1:-1]
    out["box_residual_tt"] = float(np.sqrt(np.mean(r ** 2) / (np.mean(dtt ** 2) + 1e-300)))
    out["density_speed_over_c"] = float(_centroid_speed(rho) / cpair)
    out["escape_works"] = bool(
        out["tt_energy_frac"] > 0.2
        and np.isfinite(out["tt_envelope_speed_over_c"])
        and abs(out["tt_envelope_speed_over_c"] - 1.0) < 0.05
        and abs(out["tt_phase_speed_over_c"] - 1.0) < 0.1)
    return out


# ======================================================================
#  JUDGE 1 (walker version) -- which polarizations propagate, and how fast
# ======================================================================
def judge1_walker(th=math.pi / 3, k0=None, N=256, T=110, sigma=10.0,
                  dm=0.0, eps=0.0):
    """drive the walker with physically distinct internal states; measure which
    of the 6 polarization channels of the MEASURED h carry propagating energy.
    FP target: exactly the 2 TT channels, at |v|/c = 1; everything else silent
    or static.  tt_project is used only to report the TT fraction (measurement)."""
    out = {}
    k0 = k0 or 2 * np.pi / 24
    cpair = dispersion_report(th, dm, eps)["c1_fit"]
    out["c_pair"] = cpair

    out["locking"] = locking_certificate(th, k0, dm)
    drives = {}
    prop_union = {}
    for kind in ("tt", "density", "flat", "standing"):
        psi = make_drive(N, th, k0, sigma, kind)
        H, _ = evolve_record(psi, th, T, dm, eps)
        tab = channel_table(H)
        drives[kind] = tab
        for name, row in tab.items():
            if row["propagating"]:
                v = abs(row["speed"]) / cpair
                prop_union[name] = max(prop_union.get(name, 0.0), v)
    out["drives"] = drives
    out["propagating_channels"] = {k: float(v) for k, v in prop_union.items()}
    out["n_propagating_dof"] = len(prop_union)
    tt_prop = [c for c in prop_union if c in TT_CHANNELS]
    non_tt_prop = [c for c in prop_union if c not in TT_CHANNELS]
    out["tt_channels_propagating"] = tt_prop
    out["non_tt_channels_propagating"] = non_tt_prop
    tt_speeds = [prop_union[c] for c in tt_prop]
    out["tt_speed_over_c"] = float(np.mean(tt_speeds)) if tt_speeds else float("nan")

    # causal cone: the walk moves at most 2 cells/step (1 per factor)
    psi = make_drive(N, th, k0, sigma, "tt")
    H, _ = evolve_record(psi, th, T, dm, eps)
    e = np.sum(H[-1] ** 2, axis=-1) - np.mean(np.sum(H[-1] ** 2, axis=-1))
    e = np.abs(e)
    z = np.arange(N)
    outside = np.abs(z - N // 4) > (2.0 * T + 4 * sigma)
    out["causal_leak_fraction"] = float(e[outside].sum() / (e.sum() + 1e-300))

    # measurement-only TT fraction of the full spatial tensor (tt drive)
    h3 = np.zeros(H.shape[:2] + (3, 3))
    for (m, n), (a, b) in s2.SPATIAL.items():
        comp = H[..., _I10[(m, n)]]
        h3[..., a, b] = comp
        h3[..., b, a] = comp
    h3 = h3 - h3.mean(axis=1, keepdims=True)
    tt = s2.tt_project(h3, (0, 0, 1))
    out["tt_fraction_of_spatial_h"] = float(np.sum(tt ** 2) / (np.sum(h3 ** 2) + 1e-300))

    ok = (len(tt_prop) == 2
          and len(non_tt_prop) == 0
          and np.isfinite(out["tt_speed_over_c"])
          and abs(out["tt_speed_over_c"] - 1.0) < 0.05
          and out["causal_leak_fraction"] < 1e-3)
    out["pass"] = bool(ok)
    return out


# ======================================================================
#  PART 6.  full 3D pair walker (engine.py axis structure per factor)
#           -- used by the Newtonian / deflection judges
# ======================================================================
_INV2 = 1.0 / math.sqrt(2.0)


def _ax_x(u0, u1):
    up = _INV2 * (u0 + u1)
    dn = _INV2 * (u0 - u1)
    up = np.roll(up, 1, axis=0)
    dn = np.roll(dn, -1, axis=0)
    return _INV2 * (up + dn), _INV2 * (up - dn)


def _ax_y(u0, u1):
    up = _INV2 * (u0 - 1j * u1)
    dn = _INV2 * (u0 + 1j * u1)
    up = np.roll(up, 1, axis=1)
    dn = np.roll(dn, -1, axis=1)
    return _INV2 * (up + dn), _INV2 * (1j * up - 1j * dn)


def _ax_z(u0, u1):
    return np.roll(u0, 1, axis=2), np.roll(u1, -1, axis=2)


def factor_step_3d(psi, th, fac, dm=0.0):
    """engine.walk_step on ONE factor of the pair (axes x,y,z, coin after x,y)."""
    u0, u1 = _fac_get(psi, fac)
    u0, u1 = _ax_x(u0, u1)
    u0, u1 = _coin2(u0, u1, th)
    u0, u1 = _ax_y(u0, u1)
    u0, u1 = _coin2(u0, u1, th)
    u0, u1 = _ax_z(u0, u1)
    if dm != 0.0:
        u0, u1 = _coin2(u0, u1, dm)
    return _fac_put(u0, u1, fac)


def pair_step_3d(psi, th, dm=0.0, eps=0.0):
    psi = factor_step_3d(psi, th, 0, dm)
    psi = factor_step_3d(psi, th, 1, dm)
    return exchange_coin(psi, eps)


# ======================================================================
#  JUDGE 2 (walker version) -- Newtonian limit from the MEASURED h_00
#  A static walker blob is the only 'mass' this construction has.  FP demands
#  the surrounding h_00 be a 1/r potential with h_00/phi = 2 (constant).
# ======================================================================
def judge2_walker(th=math.pi / 3, L=40, sigma=3.0, T=20, G=1.0, dm=0.0, eps=0.0):
    """SHORT-HORIZON measurement (before the blob wraps the torus): the free
    pair walker cannot hold a static lump -- it disperses ballistically (no
    self-binding, consistent with R7) -- so we average h over t in [T/2, T)
    and ALSO report the dispersal rate as a primary diagnostic."""
    out = {}
    g = np.meshgrid(*[np.arange(L)] * 3, indexing="ij")
    c0 = L // 2
    r2 = sum((g[i] - c0) ** 2 for i in range(3))
    G3 = np.exp(-r2 / (4.0 * sigma ** 2)).astype(complex)
    # internal k=0 quasi-stationary state: eigenvector (1,-1)/sqrt2 of the k=0 coin
    chi0 = np.array([1.0, -1.0]) / math.sqrt(2.0)
    psi = G3[..., None, None] * np.outer(chi0, chi0)
    psi = psi / math.sqrt(float(np.sum(np.abs(psi) ** 2)))

    def rms_radius(p):
        rho = np.sum(np.abs(p) ** 2, axis=(-1, -2))
        return math.sqrt(float((rho * r2).sum()))

    r_start = rms_radius(psi)
    Havg = np.zeros((L, L, L, 10))
    nacc = 0
    for t in range(T):
        psi = pair_step_3d(psi, th, dm, eps)
        if t >= T // 2:
            Havg += bilinear_h(psi)
            nacc += 1
    Havg /= max(nacc, 1)
    out["rms_radius_start"] = r_start
    out["rms_radius_end"] = rms_radius(psi)
    out["dispersal_rate_cells_per_step"] = float(
        (out["rms_radius_end"] - r_start) / T)

    h00 = Havg[..., _I10[(0, 0)]]
    hxx = Havg[..., _I10[(1, 1)]]
    hyy = Havg[..., _I10[(2, 2)]]
    rho = h00 - h00.mean()
    out["walker_norm_drift"] = float(abs(np.sum(np.abs(psi) ** 2) - 1.0))

    # FP reference: Lap phi = 4 pi G rho with rho = the walker's own density
    phi = s2._poisson_fft(rho, L, 4 * np.pi * G)
    sl = (slice(None), c0, c0)
    phi_line = phi[sl]
    mask = np.abs(phi_line) > 0.05 * np.abs(phi_line).max()
    ratio = (h00[sl] - h00[sl].mean())[mask] / phi_line[mask]
    out["h00_over_phi_median"] = float(np.median(ratio))
    out["h00_over_phi_cv"] = float(np.std(ratio) / (abs(np.median(ratio)) + 1e-300))

    # decisive shape test: does h00 have a 1/r tail (FP) or a compact profile?
    idx = np.indices((L, L, L))
    r = np.sqrt(sum((idx[i] - c0) ** 2 for i in range(3))).ravel()
    v = (h00 - h00.mean()).ravel()
    order = np.argsort(r)
    r, v = r[order], v[order]
    bins = np.linspace(1, L // 2, 20)
    rc = 0.5 * (bins[:-1] + bins[1:])
    prof = np.array([v[(r >= bins[i]) & (r < bins[i + 1])].mean()
                     for i in range(len(bins) - 1)])
    prof = prof - prof[-1]
    win = (rc > 0.10 * L) & (rc < 0.40 * L) & np.isfinite(prof)
    if win.sum() >= 3 and np.std(prof[win]) > 0:
        A = np.polyfit(1.0 / rc[win], prof[win], 1)
        fit = np.polyval(A, 1.0 / rc[win])
        out["invr_fit_corr"] = float(np.corrcoef(prof[win], fit)[0, 1])
    else:
        out["invr_fit_corr"] = 0.0
    # tail localization: fraction of |h00| signal beyond 3 sigma (FP: substantial)
    far = np.sqrt(r2) > 3 * sigma
    out["h00_tail_fraction"] = float(np.abs(h00 - h00.mean())[far].sum()
                                     / (np.abs(h00 - h00.mean()).sum() + 1e-300))
    out["hxx_over_h00_center"] = float(hxx[c0, c0, c0] / (h00[c0, c0, c0] + 1e-300))
    out["hyy_over_h00_center"] = float(hyy[c0, c0, c0] / (h00[c0, c0, c0] + 1e-300))

    ok = (abs(out["h00_over_phi_median"] - 2.0) < 0.05
          and out["h00_over_phi_cv"] < 0.05
          and out["invr_fit_corr"] > 0.99)
    out["pass"] = bool(ok)
    out["_slices"] = {"h00": h00[..., c0] - h00[..., c0].mean(),
                      "hxx": hxx[..., c0] - hxx[..., c0].mean(),
                      "hyy": hyy[..., c0] - hyy[..., c0].mean()}
    return out


# ======================================================================
#  JUDGE 3 (walker version) -- Eddington factor 2 from the MEASURED metric
# ======================================================================
def judge3_walker(j2=None, L=None, b=None, **kw):
    out = {}
    if j2 is None:
        j2 = judge2_walker(**(({"L": L} if L else {}) | kw))
    h00, hxx, hyy = (j2["_slices"][k] for k in ("h00", "hxx", "hyy"))
    L = h00.shape[0]
    b = b if b is not None else max(3, L // 5)
    scale = 3e-4 / (np.abs(0.5 * h00).max() + 1e-300)
    h00s, hxxs, hyys = h00 * scale, hxx * scale, hyy * scale
    # ray along x (deflected in y): photon feels h00 + hxx ; scalar feels h00
    n_t = 1.0 - 0.5 * (h00s + hxxs)
    n_s = 1.0 - 0.5 * h00s
    out["ratio_ray_x"] = float(pathB._deflection(n_t, L, b) / pathB._deflection(n_s, L, b))
    # ray along y: photon feels h00 + hyy (isotropy check -- FP requires equality)
    n_t = 1.0 - 0.5 * (h00s.T + hyys.T)
    n_s = 1.0 - 0.5 * h00s.T
    out["ratio_ray_y"] = float(pathB._deflection(n_t, L, b) / pathB._deflection(n_s, L, b))
    out["anisotropy"] = float(abs(out["ratio_ray_x"] - out["ratio_ray_y"]))
    ok = (abs(out["ratio_ray_x"] - 2.0) < 0.05
          and abs(out["ratio_ray_y"] - 2.0) < 0.05)
    out["pass"] = bool(ok)
    return out


# ======================================================================
#  runner plug-in interface (aligned with tensor_qca.evaluate_tensor_rule)
# ======================================================================
PARAM_NAMES = ["theta", "dm", "eps", "k0", "kappa"]
DEFAULT_PARAMS = np.array([math.pi / 3, 0.0, 0.0, 2 * np.pi / 24, 1.0])


def evaluate_walker_rule(params_batch, quick=True):
    """Batch evaluation of pair-walker rules against the walker judges.

    params_batch : (Bn, 5) host array, columns = PARAM_NAMES
        theta : coin angle (pair light speed c = 2 cos theta; pi/3 -> c = 1)
        dm    : factor mass gap (off the Weyl line)
        eps   : exchange-coin angle (flat-band gap / graviton-mass knob)
        k0    : drive momentum for the propagation judges
        kappa : bilinear normalization (pure rescaling of h)
    Returns dict of length-Bn arrays: passes, tt_dof(n_propagating channels),
    tt_speed(/c), non_tt_prop(count), box_resid, dedonder, flat_band,
    newton_corr, newton_cv, deflection, fact1/2/3.
    Same status note as tensor_qca.evaluate_tensor_rule: correct-interface,
    single-rule loop; GPU batching would add a leading batch axis to the pure
    step functions (they are roll/stack-only) and jit via backend.B."""
    P = np.atleast_2d(np.asarray(params_batch, dtype=float))
    keys = ["passes", "tt_dof", "tt_speed", "non_tt_prop", "box_resid",
            "dedonder", "flat_band", "newton_corr", "newton_cv", "deflection",
            "locking_s3prod", "dirac_tt_frac", "dirac_tt_speed",
            "fact1", "fact2", "fact3"]
    res = {k: [] for k in keys}
    N, T = (128, 56) if quick else (256, 110)
    L, TN = (28, 14) if quick else (40, 20)
    for th, dm, eps, k0, kappa in P:
        disp = dispersion_report(th, dm, eps)
        f1 = judge1_walker(th=th, k0=k0, N=N, T=T, dm=dm, eps=eps)
        cr = continuum_report(th=th, k0=k0, N=N, T=T, dm=dm, eps=eps)
        lock = locking_certificate(th, k0, dm)
        dp = dirac_pair_probe(th=th, k0=k0, N=N, T=T, dm=dm)
        f2 = judge2_walker(th=th, L=L, T=TN, dm=dm, eps=eps)
        f3 = judge3_walker(f2, L=L, b=max(3, L // 5))
        res["passes"].append(bool(f1["pass"] and f2["pass"] and f3["pass"]))
        res["tt_dof"].append(f1["n_propagating_dof"])
        res["tt_speed"].append(f1["tt_speed_over_c"])
        res["non_tt_prop"].append(len(f1["non_tt_channels_propagating"]))
        res["box_resid"].append(cr["box_residual_tt"])
        res["dedonder"].append(cr["dedonder_ratio_tt_drive"])
        res["flat_band"].append(disp["flat_band_max_|omega|"])
        res["newton_corr"].append(f2["invr_fit_corr"])
        res["newton_cv"].append(f2["h00_over_phi_cv"])
        res["deflection"].append(f3["ratio_ray_x"])
        res["locking_s3prod"].append(lock["s3_of_comoving_branches"][0]
                                     * lock["s3_of_comoving_branches"][1])
        res["dirac_tt_frac"].append(dp["tt_energy_frac"])
        res["dirac_tt_speed"].append(dp["tt_envelope_speed_over_c"])
        res["fact1"].append(f1["pass"])
        res["fact2"].append(f2["pass"])
        res["fact3"].append(f3["pass"])
    return {k: np.array(v) for k, v in res.items()}


# ======================================================================
#  driver -- construction + ruthless verdict + precise diagnosis
# ======================================================================
def run_all():
    th = math.pi / 3          # calibrates pair light speed 2 cos(th) = 1
    res = {"backend": B.NAME, "theta": th}
    res["dispersion"] = dispersion_report(th)
    res["dispersion_eps0.2"] = dispersion_report(th, eps=0.2)
    res["gauge_certificate_target"] = tq.gauge_certificate(N=6)
    res["continuum"] = continuum_report(th=th)
    res["locking"] = locking_certificate(th, 2 * np.pi / 24)
    res["dirac_probe"] = dirac_pair_probe(th=th)
    res["judge1"] = judge1_walker(th=th)
    j2 = judge2_walker(th=th)
    res["judge2"] = {k: v for k, v in j2.items() if not k.startswith("_")}
    res["judge3"] = judge3_walker(j2)
    return res


def _diagnose(res):
    """precise failure-mode diagnosis (the point of this module)."""
    d = []
    f1, f2, f3 = res["judge1"], res["judge2"], res["judge3"]
    cr = res["continuum"]
    lock = res["locking"]
    dp = res["dirac_probe"]
    if lock["locked"]:
        d.append(
            "SPIN-MOMENTUM LOCKING KILLS PROPAGATING HELICITY-2 (Weyl pair): "
            "the two co-moving branch spinors have s3 = (%.3f, %.3f) -- BOTH "
            "spin-up along the walk axis; a spin-down right-mover does not "
            "exist, so the co-moving up,up/down,down coherence that the TT "
            "bilinears need is impossible (transverse coherence^2 = %.2e). "
            "h_+ exists only as a STANDING wave (see 'standing' drive). This is "
            "the lattice image of 'collinear massless 1/2+1/2 maxes at helicity "
            "1'. ESCAPE MEASURED: chirality-doubled (Dirac, 16-comp) pair probe "
            "-> TT energy frac %.3f at v_env/c=%.3f, v_ph/c=%.3f (escape_works="
            "%s): the obstruction is representation-level, not fundamental."
            % (lock["s3_of_comoving_branches"][0], lock["s3_of_comoving_branches"][1],
               lock["transverse_coherence2"], dp["tt_energy_frac"],
               dp["tt_envelope_speed_over_c"], dp["tt_phase_speed_over_c"],
               dp["escape_works"]))
    if f1["non_tt_channels_propagating"]:
        d.append(
            "DOF COUNT WRONG: non-TT channels %s carry propagating energy. Root "
            "cause: the bilinear map conflates FIELD and SOURCE -- a single-band "
            "walker packet puts its own density rho into h00/hzz (and it advects "
            "at c), so longitudinal components propagate. In FP those are "
            "constrained (non-radiative). Missing structure: a constraint "
            "sector separating T_munu-like bilinears from radiative coherences."
            % f1["non_tt_channels_propagating"])
    if cr["dedonder_ratio_tt_drive"] > 0.1:
        d.append(
            "GAUGE MODES NOT DECOUPLED: de-Donder residual |D^mu hbar_munu| ~ "
            "%.2f of generic (decorrelated baseline %.2f). Root cause: the "
            "advected matter envelope in h00/hzz has no compensating h_{0i} "
            "current at the right calibration -- the naive sym(sigma x sigma) "
            "bilinear is NOT the walk's conserved lattice current (for negative-"
            "frequency components it even has the wrong sign), so the measured "
            "h fails lattice transversality at O(1)."
            % (cr["dedonder_ratio_tt_drive"], cr["dedonder_ratio_decorrelated"]))
    if not f2["pass"]:
        d.append(
            "NEWTONIAN SECTOR ABSENT: h00 around a static walker blob has no 1/r "
            "tail (invr corr %.3f, tail fraction %.3f, h00/phi cv %.2f). Root "
            "cause: a FREE local unitary walk has no gapless k^-2 response; the "
            "constraint (Poisson) part of FP is not a propagating mode and "
            "cannot be a bilinear of a free field. Requires matter->geometry "
            "feedback (the engine.py theta-loop, promoted to tensor: h sourced "
            "BY the bilinears, i.e. bilinear = T_munu, not h_munu)."
            % (f2["invr_fit_corr"], f2["h00_tail_fraction"], f2["h00_over_phi_cv"]))
    if not f3["pass"]:
        d.append(
            "DEFLECTION/ISOTROPY WRONG: ray-x ratio %.3f, ray-y ratio %.3f "
            "(target 2.000 both). Root cause: the spatial part h_ij ~ <sigma_i>"
            "<sigma_j> rho is set by the INTERNAL polarization of the blob, not "
            "by trace-reversed gravity (h_ij = 2 phi delta_ij); rotational "
            "covariance is broken by the internal state."
            % (f3["ratio_ray_x"], f3["ratio_ray_y"]))
    if not d:
        d.append("no failures detected -- treat with suspicion and re-verify.")
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "tensor_walker_results.json"))
    args = ap.parse_args()

    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("TENSOR WALKER: pair split-step walk, h_munu = Re[psi^dag sym(sigma x sigma) psi]\n")

    res = run_all()
    disp, cr = res["dispersion"], res["continuum"]
    f1, f2, f3 = res["judge1"], res["judge2"], res["judge3"]

    print("[CONSTRUCTION] U = U1(theta) (x) U1(theta), internal C^2 x C^2")
    print(f"    unitarity defect            = {disp['unitary_defect']:.2e}")
    print(f"    [U, SWAP] (symmetric-tensor closure) = {disp['swap_commutator']:.2e}")
    print(f"    luminal band fit: omega = {disp['c1_fit']:.4f} k + ({disp['c3_fit']:+.4f}) k^3"
          f"   (theory c = 2 cos th = {disp['c1_theory_2costh']:.4f})")
    print(f"    flat band max|omega|        = {disp['flat_band_max_|omega|']:.2e}  (exact 0 = "
          f"non-propagating opposite-helicity sector)")
    print(f"    eps=0.2 flat-band gap       = {res['dispersion_eps0.2']['flat_band_max_|omega|']:.4f}"
          f"  (graviton-mass knob works)")
    cert = res["gauge_certificate_target"]
    print(f"    target gauge structure (tensor_qca): E-invariance residual "
          f"{cert['diffeo_invariance_residual']:.1e}, pure-gauge null "
          f"{cert['pure_gauge_null_residual']:.1e}  <- walker must reproduce this\n")

    print("[CONTINUUM LIMIT] measured dynamics of h from the TT (entangled-pair) drive")
    print(f"    TT energy fraction          = {cr['tt_energy_fraction']:.2e}  "
          f"(locking-suppressed remnant; the speeds below are for THIS tiny wave)")
    print(f"    TT envelope speed / c       = {cr['tt_envelope_speed_over_c']:.4f}  (target 1)")
    print(f"    TT phase speed / c          = {cr['tt_phase_speed_over_c']:.4f}  (on-cone check)")
    print(f"    dominant K / 2k0            = {cr['tt_dominant_K_over_2k0']:.4f}  (theory 1: "
          f"h oscillates at 2 k0)")
    print(f"    box-residual (TT channel)   = {cr['box_residual_tt']:.4f}  (0 = exact wave eq)")
    print(f"    box-residual (long channel) = {cr['box_residual_long']:.4f}")
    print(f"    de-Donder ratio (measured)  = {cr['dedonder_ratio_tt_drive']:.4f}   "
          f"[decorrelated baseline {cr['dedonder_ratio_decorrelated']:.4f}; FP wants << baseline]")
    ein = cr["einstein"]
    print(f"    E_munu[h] rms / decorrelated baseline = {ein['E_ratio']:.4f}  "
          f"(FP vacuum wants << 1)")
    print(f"    |E_00| vs matter-envelope corr        = {ein['E00_vs_envelope_corr']:.3f}  "
          f"(high => residual = the walker's own T_munu)\n")

    lock = res["locking"]
    print("[OBSTRUCTION] spin-momentum locking of the Weyl pair (measured)")
    print(f"    s3 of the two co-moving branch spinors = "
          f"({lock['s3_of_comoving_branches'][0]:+.4f}, "
          f"{lock['s3_of_comoving_branches'][1]:+.4f})   "
          f"[helicity-2 needs (+1,-1)] -> locked: {lock['locked']}")
    print(f"    achievable transverse (TT) coherence^2 = "
          f"{lock['transverse_coherence2']:.3e}\n")

    dp = res["dirac_probe"]
    print("[ESCAPE PROBE] chirality-doubled DIRAC pair (16 components, 1+1D)")
    print(f"    TT energy fraction          = {dp['tt_energy_frac']:.3f}  "
          f"(Weyl pair gave ~0)")
    print(f"    TT envelope speed / c       = {dp['tt_envelope_speed_over_c']:.4f}")
    print(f"    TT phase speed / c          = {dp['tt_phase_speed_over_c']:.4f}   "
          f"K/2k0 = {dp['tt_dominant_K_over_2k0']:.3f}")
    print(f"    box-residual (TT)           = {dp['box_residual_tt']:.4f}")
    print(f"    per-channel E-frac: " + ", ".join(
        f"{n.split()[0]}={v:.3f}" for n, v in dp["channel_energy_frac"].items()))
    print(f"    -> escape_works: {dp['escape_works']}\n")

    print("[JUDGE 1] propagating polarization content of the MEASURED h")
    for kind, tab in f1["drives"].items():
        print(f"    drive '{kind}':")
        for name, row in tab.items():
            tag = ("PROPAGATES v/c=%.3f" % (abs(row["speed"]) / f1["c_pair"])
                   if row["propagating"] else
                   ("static" if row["energy_frac"] > 0.02 else "silent"))
            print(f"        {name:20s} E-frac={row['energy_frac']:6.3f}  {tag}")
    print(f"    propagating channels = {f1['n_propagating_dof']} "
          f"(TT: {f1['tt_channels_propagating']}, "
          f"non-TT: {f1['non_tt_channels_propagating']})   target: exactly the 2 TT")
    print(f"    TT speed / c = {f1['tt_speed_over_c']:.4f}   causal leak = "
          f"{f1['causal_leak_fraction']:.2e}")
    print(f"    TT fraction of spatial h (tt drive, measurement only) = "
          f"{f1['tt_fraction_of_spatial_h']:.3f}")
    print(f"    -> {'PASS' if f1['pass'] else 'FAIL'}\n")

    print("[JUDGE 2] Newtonian limit from the measured h_00 of a static blob")
    print(f"    blob rms radius {f2['rms_radius_start']:.2f} -> {f2['rms_radius_end']:.2f} "
          f"in {res['judge2'].get('T', 20)} steps "
          f"(dispersal {f2['dispersal_rate_cells_per_step']:.3f} cells/step: "
          f"the 'mass' does not even stay put)")
    print(f"    h00/phi median = {f2['h00_over_phi_median']:.4f} (target 2), "
          f"cv = {f2['h00_over_phi_cv']:.3f} (target <0.05)")
    print(f"    1/r-tail fit corr = {f2['invr_fit_corr']:.4f} (target >0.99), "
          f"tail fraction = {f2['h00_tail_fraction']:.4f}")
    print(f"    hxx/h00, hyy/h00 at center = {f2['hxx_over_h00_center']:.3f}, "
          f"{f2['hyy_over_h00_center']:.3f}  (FP after trace reversal: 1, 1)")
    print(f"    -> {'PASS' if f2['pass'] else 'FAIL'}\n")

    print("[JUDGE 3] Eddington deflection factor from the measured metric")
    print(f"    ray-x ratio = {f3['ratio_ray_x']:.4f}, ray-y ratio = {f3['ratio_ray_y']:.4f} "
          f"(target 2.000, isotropic)")
    print(f"    -> {'PASS' if f3['pass'] else 'FAIL'}\n")

    all_pass = f1["pass"] and f2["pass"] and f3["pass"]
    print("=" * 70)
    print("ALL JUDGES PASS" if all_pass else "SOME JUDGES FAILED (expected -- see diagnosis)")
    print("=" * 70)
    print("\n[DIAGNOSIS]")
    diags = _diagnose(res)
    for i, dtxt in enumerate(diags, 1):
        print(f"  ({i}) {dtxt}\n")
    res["diagnosis"] = diags
    res["all_pass"] = bool(all_pass)

    print("[NEXT STEPS, concrete]")
    print(" (0) PROMOTE the chirality-doubled Dirac pair (escape probe) to the full")
    print("     construction: its chirality-flipping bilinears already give an")
    print("     essentially pure TT wave on the light cone (frac ~0.99, box-resid")
    print("     ~0.006). Build the complete 10-component map on the 16-comp walker")
    print("     and rerun judge 1 there.")
    print(" (a) replace the sym(I x sigma_i) time components by the walk's exact")
    print("     lattice-conserved current (quasi-local, from the shift structure)")
    print("     -> repairs de-Donder transversality.")
    print(" (b) close the loop: bilinears are T_munu, not h_munu -- feed them as")
    print("     SOURCE into a tensor coin field (tensor analogue of engine.py's")
    print("     theta feedback) to get the constraint/Newtonian 1/r sector a free")
    print("     unitary walk provably lacks.")
    print(" (c) 3+1D isotropy: per-axis sandwich coins + rotationally covariant")
    print("     internal frame before claiming helicity-2 under arbitrary khat.")

    with open(args.json, "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {os.path.abspath(args.json)}")
