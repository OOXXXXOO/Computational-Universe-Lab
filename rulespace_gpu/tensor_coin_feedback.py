"""tensor_coin_feedback -- MATTER -> GEOMETRY TENSOR CLOSED LOOP.

WHAT THIS IS (honest, up front):
    The tensor promotion of engine.py's scalar theta-feedback loop, i.e. the
    step (b) that tensor_walker.py's diagnosis demanded:

        scalar loop (engine.py):  walker rho/T00  --kappa-->  dynamical theta
                                  theta           --coin--->  walker
        tensor loop (this file):  walker BILINEAR T_munu(x)  --(-16 pi G)-->
                                  dynamical tensor coin field hbar_munu
                                  (leapfrog  box hbar = -16 pi G T, harmonic
                                  gauge, = spin2_evolver / tensor_qca update)
                                  h_munu --tensor coin--->  walker per-axis
                                  light speeds c_i(x) = c0 (1 + (h_00+h_ii)/2).

    The point: a FREE local unitary walk provably has no gapless k^-2 response,
    so the Newtonian / constraint sector of Fierz-Pauli CANNOT be a bilinear of
    a free field (tensor_walker judge-2 diagnosis).  Here the bilinears are the
    SOURCE (T_munu), not the field, and the 1/r sector lives in the sourced
    tensor field -- exactly as in linearized GR.

CONSTRUCTION (three pieces, precisely):

  (1) MATTER: a 4-component DIRAC "tensor-coin" walker on a 3D torus
      (chirality doubling is FORCED: a 2-component walker in 3D has no mass
      gap -- no 4th anticommuting Pauli -- and the Newtonian source must be a
      quasi-static massive blob).  One macro step per chirality = three axis
      sandwiches (the core.py 1D split-step, conjugated into per-axis frames),
      chir- mirrored (k -> -k), then the mass coin exp(i dm tau_x):
          U = C4(dm) . [ M_z M_y M_x  (+)  M_z M_y M_x |mirror ] ,
          M_a = Weff_a^dag [ Sm C(-th_a) Sp C(th_a) ] Weff_a ,
          Weff_a = A(th0)^dag W_a,  A = exp(i th0/2 sigma_x).
      Exactly unitary.  MEASURED PROPERTIES: pure-axis dispersion is EXACTLY
      the 1D one per axis (cos w = cos^2 th_a cos k_a + sin^2 th_a) => local
      light speed c_a = cos th_a(x) independently per axis -- three coin
      angles = the diagonal of a spatial metric; small-k isotropy 1.002
      (the A-frame correction is what makes the three axis generators
      orthogonal -- without it the cone is 22% anisotropic); mass gap exact,
      vg(k=0) = 0.004.  DECLARED DEFECTS (measured): Trotter cross terms give
      the massive bands O(k) group speeds in MIXED directions (the gap does
      not suppress velocity off-axis), so a blob melts at ~0.1-0.2 cells/step;
      and the light-cone skews O(k) off-axis.  Both are the same sequential-
      splitting disease and bound the closed-loop horizon.

  (2) T_munu FROM BILINEARS (the observation map, lower indices, signature
      eta_c = diag(-c^2,1,1,1), lattice units):
          T_munu = -1/2 Im[ (Sig_mu psi)^dag (D_nu psi)
                            + (Sig_nu psi)^dag (D_mu psi) ],
          Sig_0 = 1,   Sig_i = -(1/c_i) tau_z sigma_i ,   D = central diffs
          (D_0 uses psi(t-1), psi(t+1) -- the engine.T00 convention).
      Plane-wave targets: T_00 = sin(w) rho, T_0i = -sin(k_i) rho,
      T_ij = sym[sin(k_i) vg_j]/c^2 rho; the -(1/c_i) weight in Sig_i is
      REQUIRED for the eta_c divergence
          R_nu = -(1/c^2) D_0 T_0nu + D_j T_jnu
      to close.  MEASURED: exact on pure-axis modes (5e-12), 1.5% residual
      quasi-1D, but 10-150% component errors for MIXED-direction modes (the
      walk's true energy-momentum current is substep-quasi-local, not this
      on-site bilinear; the |k|-even eigenframe tilt makes the error
      non-analytic, so NO local polynomial counterterm can fix it -- measured,
      a naive counterterm makes it worse).  The walk DOES possess an exact
      local conservation law: the substep-telescoped bond current closes the
      rho continuity equation to 3e-18 (rho_current_certificate) -- deriving
      the analogous exact T_munu is precisely tensor_walker's step (a).
      Conservation matters because box hbar = -16 pi G T propagates
      D^mu T_munu directly into the de-Donder constraint.

  (3) GEOMETRY + FEEDBACK: hbar_munu (packed 10) evolves with the repo's
      leapfrog (tensor_qca.qca_step: 2h - h_prev + cg2 (Lap h + src) - gamma
      dh), src = -16 pi G (T - <T>) (neutralizing torus background, the same
      Jeans swindle every torus-Poisson judge in the repo uses).  Feedback:
      trace-reverse hbar -> physical h; per-axis coin fields
          c_i(x) = clip( cos(th0) [1 + (h_00 + h_ii)/2] ),  th_i = arccos c_i.
      This is the tensor coin: h_00 + h_ii is exactly the combination the
      photon index n = 1 - (h_00+h_ii)/2 of judge-3 (Eddington) says a wave
      moving along axis i must feel.  NOT implemented (declared): coupling of
      h_0i (frame dragging) and off-diagonal h_ij into the coin -- those need
      the 16-component chirality-doubled walker (step0/a, another agent); the
      interface point is theta_fields() below.

JUDGES (thresholds fixed a priori, no tuning):
    CONSTRUCTION  unitarity < 1e-12, per-axis c_a = cos th_a to < 1e-3,
                  small-k isotropy < 2%.
    CONS          eta_c-divergence residual of T (normalized like
                  tensor_walker.dedonder_residual): free packet < 0.10 and
                  >= 5x below a decorrelated baseline; inhomogeneous-theta
                  residual reported (it is the gravitational force density,
                  physical, not a bug).
    J2 NEWTON (the main target): static massive walker blob, T_munu measured
                  from bilinears, hbar relaxed (gamma-damped leapfrog) ->
                  hbar_00/phi = 4, h_00/phi = 2 (cv < 0.05), 1/r tail corr
                  > 0.99, Poisson residual < 5e-3, Eddington ratio 2 +- 0.05
                  from the SAME evolved h, and the closed 回授 test: a test
                  packet is DEFLECTED TOWARD the blob by the tensor coin.
    J1/J3 (emergence_judge, projection-free): does the matter coupling break
                  the propagating/gauge sector?  Measured on the bare leapfrog
                  (known N_prop = 6) and on the null-damped positive control
                  (known N_prop = 2), each with and without the live walker
                  source + feedback.
    LOOP          full co-evolution (live source, feedback on): stability,
                  exact walker norm, bounded field, well forms on the blob,
                  causal front, energy-exchange bookkeeping.

Run:   RULESPACE_BACKEND=numpy python -m rulespace_gpu.tensor_coin_feedback
"""
import argparse
import json
import math
import os

import numpy as np

from . import backend as B
from . import emergence_judge as ej
from . import pathB_spin2 as pathB
from . import spin2_evolver as s2
from . import tensor_qca as tq

DIR = os.path.dirname(os.path.abspath(__file__))
IDX10 = s2.IDX10
PK = ej.PK
PK00, PKXX, PKYY, PKZZ = PK[(0, 0)], PK[(1, 1)], PK[(2, 2)], PK[(3, 3)]

TH_MIN, TH_MAX = 0.08, 1.25                      # core.py coin clip range
C_MIN, C_MAX = math.cos(TH_MAX), math.cos(TH_MIN)
SIXTEEN_PI = 16.0 * math.pi

_R2 = math.sqrt(0.5)
WX = np.array([[1.0, 1.0], [1.0, -1.0]]) * _R2            # W sx W^dag = sz
WY = np.array([[1.0, -1.0j], [1.0, 1.0j]]) * _R2          # W sy W^dag = sz
SX = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)


# ======================================================================
#  PART 1.  the tensor-coin DIRAC walker (strictly local, exactly unitary)
#
#  Two constructions facts, both MEASURED (they were found the hard way and
#  are certified below, not assumed):
#    * the 1D sandwich's small-k generator is cos(th) * nhat(th).sigma with
#      nhat(th) = (0, -sin th, cos th) -- NOT sigma_z.  The axis frames must
#      therefore include the correction A(th0) = exp(i th0/2 sigma_x) that
#      rotates nhat(th0) -> zhat, or the three axis generators are not
#      orthogonal and the light cone is anisotropic (measured: 22% at th0 =
#      0.45 without the correction, < 1% with it).  A is fixed at the
#      reference th0; feedback deviations dtheta tilt the generators by
#      O(dtheta) -- declared, not hidden.
#    * a 2-component walker in 3D has NO mass gap (no 4th anticommuting
#      Pauli): any "mass coin" is a momentum shift and a k=0 packet still
#      moves at c.  A quasi-static massive blob -- the Newtonian source --
#      requires CHIRALITY DOUBLING: 4 components, the second chirality runs
#      the mirrored walk (all shifts reversed = k -> -k), and the mass coin
#      exp(i dm tau_x) mixes chiralities.  tau_x anticommutes with every
#      velocity generator tau_z sigma_a  =>  omega = sqrt(dm^2 + c^2 k^2),
#      group velocity 0 at k = 0.  (This is the same chirality doubling the
#      tensor_walker Dirac-pair probe validated, used here for MATTER only.)
# ======================================================================
def _coin(psi, th):
    """sigma_x coin with local angle th on a 2-component last axis."""
    c, s = np.cos(th), np.sin(th)
    p0, p1 = psi[..., 0], psi[..., 1]
    return np.stack([c * p0 + 1j * s * p1, 1j * s * p0 + c * p1], axis=-1)


def _axis_sandwich(psi, th, ax3, W, orient=1, flux=None):
    """core.py split-step along one axis in the axis basis W (2-comp fields).
    ax3 in {-3,-2,-1}: spatial axis of the component-sliced arrays.
    orient=-1 runs the MIRRORED walk (all shifts reversed, i.e. k -> -k).

    flux: optional dict {"B": array} accumulating the EXACT bond current of
    this substep (probability crossing bond (x, x+e_a) in the + direction);
    shifts are the only transport, coins are on-site, so
        rho_{t+1} - rho_t + sum_a [B_a(x) - B_a(x - e_a)] = 0   EXACTLY."""
    if W is not None:
        psi = psi @ W.T                          # q = W psi
    psi = _coin(psi, th)
    if flux is not None:
        a2 = np.abs(psi[..., 0]) ** 2
        flux["B"] = flux["B"] + (a2 if orient == 1 else -np.roll(a2, -1, ax3))
    p0 = np.roll(psi[..., 0], orient, axis=ax3)
    psi = np.stack([p0, psi[..., 1]], axis=-1)
    psi = _coin(psi, -th)
    if flux is not None:
        b2 = np.abs(psi[..., 1]) ** 2
        flux["B"] = flux["B"] + (-np.roll(b2, -1, ax3) if orient == 1 else b2)
    p1 = np.roll(psi[..., 1], -orient, axis=ax3)
    psi = np.stack([psi[..., 0], p1], axis=-1)
    if W is not None:
        psi = psi @ W.conj()                     # psi = W^dag q
    return psi


_FRAME_CACHE = {}


def axis_frames(th0):
    """effective 2x2 frames W_a = A(th0)^dag W_a0 per axis, such that the
    net axis-a generator is cos(th) sigma_a at th = th0 (see header)."""
    key = round(float(th0), 12)
    if key not in _FRAME_CACHE:
        c, s = math.cos(th0 / 2), math.sin(th0 / 2)
        A = np.array([[c, 1j * s], [1j * s, c]])     # exp(i th0/2 sigma_x)
        Ad = A.conj().T
        _FRAME_CACHE[key] = (Ad @ WX, Ad @ WY, Ad)
    return _FRAME_CACHE[key]


def walker_step(psi, thx, thy, thz, dm=0.0, th0=0.45, want_flux=False):
    """one full macro step of the 4-component Dirac tensor-coin walker.

    psi (..., Nx, Ny, Nz, 4), components = (chir+, spin0/1, chir-, spin0/1);
    th_a scalar or (...,Nx,Ny,Nz) field.  chir+ walks normally, chir- walks
    mirrored; mass coin exp(i dm tau_x) mixes the chiralities.
    want_flux=True additionally returns the EXACT per-axis bond currents
    (Bx,By,Bz) satisfying the discrete continuity equation to machine
    precision (substep telescoping -- the walk's exact conserved rho-current)."""
    Wx, Wy, Wz = axis_frames(th0)
    pc = [psi[..., :2], psi[..., 2:]]
    fx = [{"B": 0.0}, {"B": 0.0}, {"B": 0.0}] if want_flux else [None] * 3
    for o, orient in ((0, 1), (1, -1)):
        p = pc[o]
        p = _axis_sandwich(p, thx, -3, Wx, orient, fx[0])
        p = _axis_sandwich(p, thy, -2, Wy, orient, fx[1])
        p = _axis_sandwich(p, thz, -1, Wz, orient, fx[2])
        pc[o] = p
    if dm != 0.0:
        c, s = math.cos(dm), 1j * math.sin(dm)
        out = np.concatenate([c * pc[0] + s * pc[1],
                              s * pc[0] + c * pc[1]], axis=-1)
    else:
        out = np.concatenate(pc, axis=-1)
    if want_flux:
        return out, tuple(f["B"] for f in fx)
    return out


def _coin_mat(th):
    c, s = math.cos(th), 1j * math.sin(th)
    return np.array([[c, s], [s, c]])


def step_matrix(kvec, ths, dm=0.0, th0=0.45):
    """exact one-step 4x4 operator at momentum kvec, uniform angles ths."""
    frames = axis_frames(th0)

    def chir_block(sign):
        U = np.eye(2, dtype=complex)
        for a, W in enumerate(frames):
            Sp = np.diag([np.exp(-1j * sign * kvec[a]), 1.0])
            Sm = np.diag([1.0, np.exp(1j * sign * kvec[a])])
            M = W.conj().T @ (Sm @ _coin_mat(-ths[a]) @ Sp
                              @ _coin_mat(ths[a])) @ W
            U = M @ U
        return U
    U4 = np.zeros((4, 4), dtype=complex)
    U4[:2, :2] = chir_block(+1)
    U4[2:, 2:] = chir_block(-1)
    if dm != 0.0:
        c, s = math.cos(dm), 1j * math.sin(dm)
        M4 = np.block([[c * np.eye(2), s * np.eye(2)],
                       [s * np.eye(2), c * np.eye(2)]])
        U4 = M4 @ U4
    return U4


def branch_state(kvec, ths, dm=0.0, axis=0, dk=1e-4, th0=0.45):
    """internal eigen-spinor (C^4) on the band with the largest group velocity
    along `axis` at momentum kvec (numerical, continuity-matched)."""
    def bands(kv):
        ev, V = np.linalg.eig(step_matrix(kv, ths, dm, th0))
        return -np.angle(ev), V
    w, V = bands(kvec)
    kp = list(kvec); kp[axis] += dk
    km = list(kvec); km[axis] -= dk
    wp, _ = bands(kp)
    wm, _ = bands(km)
    best = None
    for j in range(4):
        vg = (wp[np.argmin(np.abs(np.angle(np.exp(1j * (wp - w[j])))))]
              - wm[np.argmin(np.abs(np.angle(np.exp(1j * (wm - w[j])))))]) / (2 * dk)
        if best is None or vg > best[0]:
            v = V[:, j]
            v = v * np.exp(-1j * np.angle(v[np.argmax(np.abs(v))]))
            best = (vg, v / np.linalg.norm(v))
    return best[1]


# positive-energy k=0 internal state of the massive walker:
# eigenvector of tau_x (x) I with tau_x = -1  ->  U(0) chi = e^{-i dm} chi.
CHI_BLOB = np.array([1.0, 0.0, -1.0, 0.0]) / math.sqrt(2.0)


def construction_certificate(th0=0.45, seed=0):
    """unitarity + per-axis c_a = cos th_a + isotropy + true mass gap."""
    out = {"th0": th0}
    rng = np.random.default_rng(seed)
    N = 12
    psi = (rng.standard_normal((N, N, N, 4)) + 1j * rng.standard_normal((N, N, N, 4)))
    n0 = float(np.sum(np.abs(psi) ** 2))
    ths = []
    for _ in range(3):
        f = rng.standard_normal((N, N, N))
        for _s in range(3):
            for ax in (0, 1, 2):
                f = (np.roll(f, 1, ax) + np.roll(f, -1, ax) + 2 * f) / 4
        ths.append(th0 + 0.15 * f / (np.abs(f).max() + 1e-300))
    for _ in range(50):
        psi = walker_step(psi, ths[0], ths[1], ths[2], dm=0.2, th0=th0)
    out["unitarity_drift"] = float(abs(np.sum(np.abs(psi) ** 2) / n0 - 1.0))

    # per-axis light speed with three DIFFERENT angles (the tensor property)
    angles = (0.40, 0.55, 0.70)
    k = 0.05
    speeds = []
    for a in range(3):
        kv = [0.0, 0.0, 0.0]; kv[a] = k
        w = float(np.max(-np.angle(np.linalg.eigvals(
            step_matrix(kv, angles, th0=th0)))))
        speeds.append(w / k)
    out["axis_speed_measured"] = speeds
    out["axis_speed_target_costh"] = [math.cos(a) for a in angles]
    out["axis_speed_max_err"] = float(max(abs(s - math.cos(a))
                                          for s, a in zip(speeds, angles)))
    # exact per-axis dispersion identity at finite k (not just small k)
    kbig = 0.7
    w = float(np.max(-np.angle(np.linalg.eigvals(
        step_matrix([kbig, 0, 0], angles, th0=th0)))))
    w_theory = math.acos(math.cos(angles[0]) ** 2 * math.cos(kbig)
                         + math.sin(angles[0]) ** 2)
    out["axis_dispersion_exact_err"] = float(abs(w - w_theory))

    # small-k isotropy at uniform th0 (needs the A(th0) frame correction)
    kv = np.array([1.0, 1.0, 1.0]) * (0.04 / math.sqrt(3.0))
    w = float(np.max(-np.angle(np.linalg.eigvals(
        step_matrix(kv, (th0,) * 3, th0=th0)))))
    out["isotropy_diag_speed_over_c"] = float(w / (0.04 * math.cos(th0)))

    # true mass gap: omega(0) = dm and group velocity 0 at k = 0
    dm = 0.8
    w0 = np.sort(np.abs(np.angle(np.linalg.eigvals(
        step_matrix([0, 0, 0], (th0,) * 3, dm, th0)))))
    out["mass_gap_err"] = float(abs(w0[0] - dm))
    dk = 0.02
    vgs = []
    for a in range(3):
        kv = [0.0, 0.0, 0.0]; kv[a] = dk
        wp = np.min(np.abs(np.angle(np.linalg.eigvals(
            step_matrix(kv, (th0,) * 3, dm, th0)))))
        vgs.append(abs(wp - w0[0]) / dk)
    out["massive_vg_at_k0"] = float(max(vgs))   # ~ c^2 k/dm = O(dk), small

    # DECLARED DEFECT (measured, no gate): in MIXED directions the massive
    # bands keep O(k) group speeds -- the mass coin gaps the frequency but the
    # Trotter cross terms defeat the velocity suppression, so a massive blob
    # melts at ~0.1-0.2 cells/step regardless of dm (limits the closed-loop
    # horizon; the pure-axis massive dispersion above IS properly flat).
    kmix = [0.1, 0.1, 0.1]
    w0m = -np.angle(np.linalg.eigvals(step_matrix(kmix, (th0,) * 3, dm, th0)))
    dk = 1e-5
    vmax = 0.0
    for j in range(4):
        vg = np.zeros(3)
        for a in range(3):
            kp = list(kmix); kp[a] += dk
            km = list(kmix); km[a] -= dk
            wp = -np.angle(np.linalg.eigvals(step_matrix(kp, (th0,) * 3, dm, th0)))
            wm = -np.angle(np.linalg.eigvals(step_matrix(km, (th0,) * 3, dm, th0)))
            vg[a] = (wp[np.argmin(np.abs(np.angle(np.exp(1j * (wp - w0m[j])))))]
                     - wm[np.argmin(np.abs(np.angle(np.exp(1j * (wm - w0m[j])))))]
                     ) / (2 * dk)
        vmax = max(vmax, float(np.linalg.norm(vg)))
    kn = float(np.linalg.norm(kmix))
    c0 = math.cos(th0)
    dirac_vg = c0 * c0 * kn / math.sqrt(dm * dm + (c0 * kn) ** 2)
    out["massive_vg_mixed_k_max"] = vmax
    out["massive_vg_mixed_over_dirac"] = float(vmax / dirac_vg)

    out["pass"] = bool(out["unitarity_drift"] < 1e-12
                       and out["axis_speed_max_err"] < 1e-3
                       and out["axis_dispersion_exact_err"] < 1e-9
                       and abs(out["isotropy_diag_speed_over_c"] - 1.0) < 0.02
                       and out["mass_gap_err"] < 1e-9
                       and out["massive_vg_at_k0"] < 0.05)
    return out


# ======================================================================
#  PART 2.  T_munu from bilinears + discrete conservation
# ======================================================================
def _velocity_apply(psi, i):
    """(tau_z (x) sigma_i) psi on the 4-component last axis: sigma_i on the
    spin index, sign flip on the mirrored (chir-) block -- these are exactly
    the walk's velocity generators (certified by construction_certificate)."""
    a0, a1, b0, b1 = psi[..., 0], psi[..., 1], psi[..., 2], psi[..., 3]
    if i == 1:
        return np.stack([a1, a0, -b1, -b0], axis=-1)
    if i == 2:
        return np.stack([-1j * a1, 1j * a0, 1j * b1, -1j * b0], axis=-1)
    return np.stack([a0, -a1, -b0, b1], axis=-1)


def stress_tensor(psi_prev, psi, psi_next, cvec):
    """T_munu(x), packed (...,10).  cvec = (c_x, c_y, c_z), scalars or fields.

    T_munu = -1/2 Im[(Sig_mu psi)^dag D_nu psi + (Sig_nu psi)^dag D_mu psi],
    Sig_0 = 1, Sig_i = -(1/c_i) tau_z sigma_i.  See module docstring for why."""
    D = [0.5 * (psi_next - psi_prev)]
    for ax4 in (-4, -3, -2):
        D.append(0.5 * (np.roll(psi, -1, ax4) - np.roll(psi, 1, ax4)))
    S = [psi]
    for i in (1, 2, 3):
        ci = cvec[i - 1]
        w = (-1.0 / ci) if np.isscalar(ci) else (-1.0 / ci)[..., None]
        S.append(w * _velocity_apply(psi, i))
    T = np.empty(psi.shape[:-1] + (10,))
    for c, (m, n) in enumerate(IDX10):
        z = np.sum(np.conj(S[m]) * D[n] + np.conj(S[n]) * D[m], axis=-1)
        T[..., c] = -0.5 * np.imag(z)
    return T


def _dsp3(f, j):
    """central spatial derivative of a (...,Nx,Ny,Nz) scalar, j in {1,2,3}."""
    ax = j - 4
    return 0.5 * (np.roll(f, -1, ax) - np.roll(f, 1, ax))


def divergence_residual(T_m, T_0, T_p, c2):
    """normalized eta_c divergence  R_nu = -(1/c^2) D_0 T_0nu + D_j T_jnu.

    Returns per-nu and overall rms(R)/rms(all first-derivative terms), the
    same normalization style as tensor_walker.dedonder_residual (a generic /
    decorrelated field scores O(1))."""
    ratios, nums, dens = [], [], []
    for nu in range(4):
        terms = [-(1.0 / c2) * 0.5 * (T_p[..., PK[(0, nu)]] - T_m[..., PK[(0, nu)]])]
        for j in (1, 2, 3):
            terms.append(_dsp3(T_0[..., PK[(j, nu)]], j))
        R = sum(terms)
        num = float(np.sqrt(np.mean(R ** 2)))
        den = float(np.sqrt(np.mean(np.stack(terms) ** 2))) + 1e-300
        ratios.append(num / den)
        nums.append(num)
        dens.append(den)
    overall = float(np.sqrt(np.sum(np.array(nums) ** 2))
                    / (np.sqrt(np.sum(np.array(dens) ** 2)) + 1e-300))
    return {"per_nu": [float(r) for r in ratios], "overall": overall}


def _gauss3(L, center, sig):
    g = np.meshgrid(*[np.arange(L)] * 3, indexing="ij")
    r2 = sum((g[i] - center[i]) ** 2 for i in range(3))
    return np.exp(-r2 / (4.0 * sig ** 2)), r2


def bilinear_mismatch_table(th0=0.45, L=24, nvecs=((2, 0, 0), (2, 1, 0),
                                                   (1, 1, 1), (2, 1, 1))):
    """THE precise diagnosis of why the bilinear T is not exactly conserved.

    For exact on-shell plane waves, compare every measured T component with
    the value a conserved tensor must take for that mode (T_00 = sin(w) rho,
    T_0i = -sin(k_i) rho, T_ij = sym[sin(k_i) vg_j]/c^2 rho).  Pure-axis
    modes are EXACT (ratio 1.000...); mixed-direction modes are off by
    O(10-100%) in the stress block: the split-step's sequential axis
    structure makes its true energy-momentum current quasi-local (substep-
    resolved), not the naive on-site sym(Sigma D) bilinear.  Returns the
    worst |ratio-1| per mode."""
    c0 = math.cos(th0)
    x = np.arange(L)
    out = {}
    for nvec in nvecs:
        k0 = tuple(2 * math.pi * n / L for n in nvec)
        ax = int(np.argmax(np.abs(np.asarray(k0))))
        chi = branch_state(list(k0), (th0,) * 3, 0.0, axis=ax, th0=th0)
        phase = np.exp(1j * (k0[0] * x[:, None, None] + k0[1] * x[None, :, None]
                             + k0[2] * x[None, None, :]))
        psi = phase[..., None] * chi / math.sqrt(L ** 3)
        p1 = walker_step(psi.copy(), th0, th0, th0, 0.0, th0)
        p2 = walker_step(p1.copy(), th0, th0, th0, 0.0, th0)
        Tm = stress_tensor(psi, p1, p2, (c0, c0, c0)).mean(axis=(0, 1, 2))
        ev = np.linalg.eigvals(step_matrix(list(k0), (th0,) * 3, 0.0, th0))
        w = -np.angle(ev)
        U = step_matrix(list(k0), (th0,) * 3, 0.0, th0)
        _, V = np.linalg.eig(U)
        j = int(np.argmax([abs(np.vdot(V[:, m], chi)) for m in range(4)]))
        om = float(w[j])
        dk = 1e-5
        vg = np.zeros(3)
        for a in range(3):
            kp = list(k0); kp[a] += dk
            km = list(k0); km[a] -= dk
            wp = -np.angle(np.linalg.eigvals(step_matrix(kp, (th0,) * 3, 0.0, th0)))
            wm = -np.angle(np.linalg.eigvals(step_matrix(km, (th0,) * 3, 0.0, th0)))
            vg[a] = (wp[np.argmin(np.abs(wp - om))]
                     - wm[np.argmin(np.abs(wm - om))]) / (2 * dk)
        rho = 1.0 / L ** 3
        ideal = {(0, 0): math.sin(om) * rho}
        for i in range(3):
            ideal[(0, i + 1)] = -math.sin(k0[i]) * rho
        for i in range(3):
            for jj in range(i, 3):
                ideal[(i + 1, jj + 1)] = 0.5 * (math.sin(k0[i]) * vg[jj]
                                                + math.sin(k0[jj]) * vg[i]) \
                    / (c0 * c0) * rho
        worst = 0.0
        for c, (m, n) in enumerate(IDX10):
            idl = ideal[(m, n)]
            scale = math.sin(om) * rho            # T00 scale
            if abs(idl) > 0.03 * scale:           # judge only O(1) components
                worst = max(worst, abs(Tm[c] / idl - 1.0))
        out[str(nvec)] = float(worst)
    return out


def rho_current_certificate(th0=0.45, seed=2, N=12, T=20):
    """EXACT local conservation exists: the substep-telescoped bond current
    closes the discrete continuity equation to machine precision, for a random
    state, inhomogeneous theta fields and dm != 0.  (Existence proof for the
    'exact quasi-local current' program -- step (a).)"""
    rng = np.random.default_rng(seed)
    psi = rng.standard_normal((N, N, N, 4)) + 1j * rng.standard_normal((N, N, N, 4))
    psi /= math.sqrt(float(np.sum(np.abs(psi) ** 2)))
    ths = []
    for _ in range(3):
        f = rng.standard_normal((N, N, N))
        for _s in range(3):
            for ax in (0, 1, 2):
                f = (np.roll(f, 1, ax) + np.roll(f, -1, ax) + 2 * f) / 4
        ths.append(np.clip(th0 + 0.2 * f / np.abs(f).max(), TH_MIN, TH_MAX))
    worst = 0.0
    for _ in range(T):
        rho0 = np.sum(np.abs(psi) ** 2, axis=-1)
        psi, (Bx, By, Bz) = walker_step(psi, ths[0], ths[1], ths[2],
                                        dm=0.35, th0=th0, want_flux=True)
        rho1 = np.sum(np.abs(psi) ** 2, axis=-1)
        div = (Bx - np.roll(Bx, 1, -3) + By - np.roll(By, 1, -2)
               + Bz - np.roll(Bz, 1, -1))
        worst = max(worst, float(np.max(np.abs(rho1 - rho0 + div))))
    return {"continuity_residual_max": worst,
            "exact": bool(worst < 1e-12)}


def judge_conservation(L=32, th0=0.45, k0=(0.4, 0.25, 0.15), sig=5.0,
                       dm=0.0, T=12, seed=0):
    """discrete D^mu T_munu of a free walker packet (uniform theta), vs a
    decorrelated baseline; then with a frozen inhomogeneous theta field (the
    residual there = gravitational force density, physical)."""
    out = {"k0": list(k0), "th0": th0, "dm": dm}
    c0 = math.cos(th0)
    c2 = c0 * c0
    env, _ = _gauss3(L, (L // 2,) * 3, sig)
    x = np.arange(L)
    phase = np.exp(1j * (k0[0] * x[:, None, None] + k0[1] * x[None, :, None]
                         + k0[2] * x[None, None, :]))
    chi = branch_state(list(k0), (th0,) * 3, dm)
    psi = (env * phase)[..., None] * chi
    psi = psi / math.sqrt(float(np.sum(np.abs(psi) ** 2)))

    def run(th_fields, cvec):
        buf = [psi.copy()]
        p = psi.copy()
        for _ in range(T + 1):
            p = walker_step(p, th_fields[0], th_fields[1], th_fields[2], dm, th0)
            buf.append(p.copy())
        Ts = [stress_tensor(buf[t - 1], buf[t], buf[t + 1], cvec)
              for t in range(1, T)]
        mids = range(1, len(Ts) - 1)
        res = [divergence_residual(Ts[t - 1], Ts[t], Ts[t + 1], c2) for t in mids]
        overall = float(np.mean([r["overall"] for r in res]))
        per_nu = np.mean(np.array([r["per_nu"] for r in res]), axis=0)
        e_series = [float(np.sum(Tt[..., PK00])) for Tt in Ts]
        return overall, [float(v) for v in per_nu], Ts, e_series

    ov, per_nu, Ts, e_series = run((th0, th0, th0), (c0, c0, c0))
    out["residual_overall"] = ov
    out["residual_per_nu"] = per_nu
    out["global_T00_drift"] = float(abs(e_series[-1] - e_series[0])
                                    / (abs(e_series[0]) + 1e-300))

    # decorrelated baseline: roll each packed component randomly in space
    rng = np.random.default_rng(seed)
    Tsh = []
    for Tt in (Ts[3], Ts[4], Ts[5]):
        Tc = Tt.copy()
        rng2 = np.random.default_rng(7)          # same shuffle for all 3 times
        for c in range(10):
            sh = [int(rng2.integers(0, L)) for _ in range(3)]
            Tc[..., c] = np.roll(np.roll(np.roll(Tt[..., c], sh[0], 0),
                                         sh[1], 1), sh[2], 2)
        Tsh.append(Tc)
    out["residual_decorrelated"] = divergence_residual(*Tsh, c2)["overall"]

    # inhomogeneous theta (frozen smooth field): covariant-force residual
    f = rng.standard_normal((L, L, L))
    for _ in range(4):
        for ax in (0, 1, 2):
            f = (np.roll(f, 1, ax) + np.roll(f, -1, ax) + 2 * f) / 4
    dth = 0.05 * f / (np.sqrt(np.mean(f ** 2)) + 1e-300)
    thf = np.clip(th0 + dth, TH_MIN, TH_MAX)
    cf = np.cos(thf)
    ov_in, _, _, _ = run((thf, thf, thf), (cf, cf, cf))
    out["residual_inhomogeneous_theta"] = ov_in
    out["theta_perturbation_rms"] = 0.05

    # QUASI-1D control: carrier + envelope along one axis only -> the bilinear
    # IS (nearly) conserved when the walk is effectively one-dimensional.
    env1 = np.exp(-((x - L // 2) ** 2) / (4.0 * sig ** 2))
    envx = np.broadcast_to(env1.reshape(L, 1, 1), (L, L, L)).copy()
    kq = (abs(k0[0]) + 1e-9, 0.0, 0.0)
    chi1 = branch_state(list(kq), (th0,) * 3, dm, axis=0, th0=th0)
    psi_save = psi
    psi = (envx * np.exp(1j * kq[0] * x[:, None, None]))[..., None] * chi1
    psi = psi / math.sqrt(float(np.sum(np.abs(psi) ** 2)))
    ov1d, _, _, _ = run((th0, th0, th0), (c0, c0, c0))
    out["residual_quasi1d"] = ov1d
    psi = psi_save

    # exact conserved rho-current exists (machine precision) + the precise
    # component-level diagnosis of WHY the bilinear T fails in mixed directions
    out["rho_current"] = rho_current_certificate(th0)
    out["planewave_worst_mismatch"] = bilinear_mismatch_table(th0)

    out["pass"] = bool(out["residual_quasi1d"] < 0.05
                       and out["residual_overall"] < 0.10
                       and out["residual_decorrelated"] > 5 * out["residual_overall"]
                       and out["global_T00_drift"] < 1e-3
                       and out["rho_current"]["exact"])
    return out


# ======================================================================
#  PART 3.  geometry + feedback (the tensor coin)
# ======================================================================
def theta_fields(h_phys, th0):
    """physical (trace-reversed) packed h -> per-axis coin angle + speed fields.

    c_i(x) = clip( cos th0 * [1 + (h_00 + h_ii)/2] , cos TH_MAX, cos TH_MIN ).
    INTERFACE NOTE (step0/a merge): h_0i and off-diagonal h_ij do not enter --
    steering by them needs the 16-component chirality-doubled walker's larger
    coin group; this function is the single place they would plug in."""
    c0 = math.cos(th0)
    h00 = h_phys[..., PK00]
    cs, ths = [], []
    for ii in (PKXX, PKYY, PKZZ):
        c = np.clip(c0 * (1.0 + 0.5 * (h00 + h_phys[..., ii])), C_MIN, C_MAX)
        cs.append(c)
        ths.append(np.arccos(c))
    return ths, cs


def loop_step(state, params):
    """one closed-loop macro step (the tensor coupled_step).

    state = (psi_prev, psi, hbar, hbar_prev);  params: th0, dm, cg2, G, gamma.
    order (mirrors engine.coupled_step): geometry steers matter -> matter steps
    -> bilinear T at time t -> T sources geometry."""
    psi_prev, psi, hb, hbp = state
    h_phys = tq.trace_reverse_packed(hb)
    ths, cs = theta_fields(h_phys, params["th0"])
    psi_next = walker_step(psi, ths[0], ths[1], ths[2], params["dm"],
                           params["th0"])
    T = stress_tensor(psi_prev, psi, psi_next, cs)
    src = -SIXTEEN_PI * params["G"] * (T - T.mean(axis=(0, 1, 2), keepdims=True))
    hb_next = tq.qca_step(hb, hbp, params["cg2"], src, params["gamma"])
    sp = params.get("sponge")            # optional absorbing boundary layer (B4)
    if sp is not None:                   # extra edge friction: soaks outgoing radiation
        hb_next = hb_next - sp[..., None] * (hb - hbp)
    return (psi, psi_next, hb_next, hb), T


def _sponge_field(L, width, gmax):
    """absorbing boundary layer: gamma ramps 0 (interior) -> gmax (edge) over the
    outer `width` cells, quadratic. Lets outgoing waves dissipate at the box edge
    instead of wrapping the torus (B4: is well_poisson_corr=-0.48 a torus artifact?)."""
    if width <= 0:
        return None
    idx = np.arange(L)
    d1 = np.minimum(idx, L - 1 - idx)                       # distance to nearest edge
    ramp1 = np.clip((width - d1) / float(width), 0.0, 1.0) ** 2
    rx = ramp1[:, None, None]; ry = ramp1[None, :, None]; rz = ramp1[None, None, :]
    return gmax * np.maximum(np.maximum(rx, ry), rz)


# ======================================================================
#  JUDGE 2 -- NEWTONIAN SECTOR (the main target)
# ======================================================================
def judge_newton(L=56, sig=3.0, dm=1.5, th0=0.45, G=1.0, T_avg=24,
                 cg2=0.25, gamma=0.06, max_steps=6000, tol=5e-3,
                 steer_contrast=0.15, b_imp=8, T_steer=40, k_steer=0.6):
    """static massive walker blob -> measured T_munu -> relaxed hbar ->
    h00/phi = 2, 1/r tail, Eddington 2, and packet deflection TOWARD the blob."""
    out = {"L": L, "sigma": sig, "dm": dm, "th0": th0}
    c0 = math.cos(th0)
    ctr = (L // 2,) * 3
    env, r2 = _gauss3(L, ctr, sig)
    psi = env[..., None] * CHI_BLOB
    psi = psi / math.sqrt(float(np.sum(np.abs(psi) ** 2)))

    def rms_radius(p):
        rho = np.sum(np.abs(p) ** 2, axis=-1)
        return math.sqrt(float((rho * r2).sum()))

    out["blob_rms_radius_start"] = rms_radius(psi)
    # free evolution at uniform th0 (static limit: feedback off), averaging T
    buf = [psi.copy()]
    p = psi.copy()
    for _ in range(T_avg + 1):
        p = walker_step(p, th0, th0, th0, dm, th0)
        buf.append(p.copy())
    out["blob_rms_radius_end"] = rms_radius(p)
    Tacc = np.zeros((L, L, L, 10))
    for t in range(1, T_avg):
        Tacc += stress_tensor(buf[t - 1], buf[t], buf[t + 1], (c0, c0, c0))
    Tavg = Tacc / (T_avg - 1)
    T00 = Tavg[..., PK00]
    out["T00_total"] = float(T00.sum())
    out["T00_negative_fraction"] = float(np.abs(T00[T00 < 0]).sum()
                                         / (np.abs(T00).sum() + 1e-300))
    press = (np.abs(Tavg[..., PKXX]) + np.abs(Tavg[..., PKYY])
             + np.abs(Tavg[..., PKZZ])) / 3.0
    out["pressure_over_T00"] = float(press.sum() / (np.abs(T00).sum() + 1e-300))
    # SIGNED trace pressure: linearized GR predicts h00 = 2 phi_{rho+3p}
    # (Tolman), i.e. h00/phi_{rho} = 2 (1 + 3 pbar/rho).  Measured, then used
    # below to CHECK that any deviation of h00/phi from 2 is pressure physics.
    tr3p = float((Tavg[..., PKXX] + Tavg[..., PKYY] + Tavg[..., PKZZ]).sum()
                 / (T00.sum() + 1e-300))
    out["trace_3p_over_rho"] = tr3p

    # relax hbar under the STATIC measured source (r6b static limit, tensorized)
    src = -SIXTEEN_PI * G * (Tavg - Tavg.mean(axis=(0, 1, 2), keepdims=True))
    hb = np.zeros((L, L, L, 10))
    hbp = np.zeros((L, L, L, 10))
    rho_c = T00 - T00.mean()
    rhs_rms = float(np.sqrt(np.mean((SIXTEEN_PI * G * rho_c) ** 2))) + 1e-300
    resid = float("nan")
    for it in range(max_steps):
        nxt = tq.qca_step(hb, hbp, cg2, src, gamma)
        hbp, hb = hb, nxt
        if (it + 1) % 200 == 0:
            lap = s2._laplacian3d(hb)[..., PK00]
            resid = float(np.sqrt(np.mean((lap - SIXTEEN_PI * G * rho_c) ** 2))
                          / rhs_rms)
            if resid < tol:
                break
    out["relax_steps"] = it + 1
    out["poisson_residual"] = resid

    h_phys = tq.trace_reverse_packed(hb)
    hbar00 = hb[..., PK00]
    h00 = h_phys[..., PK00]
    hxx = h_phys[..., PKXX]

    phi = s2._poisson_fft(rho_c, L, 4 * np.pi * G)   # Lap phi = 4 pi G rho
    sl = (slice(None), ctr[1], ctr[2])
    phi_line = phi[sl]
    mask = np.abs(phi_line) > 0.05 * np.abs(phi_line).max()
    r_hb = (hbar00[sl] / phi_line)[mask]
    r_h = (h00[sl] / phi_line)[mask]
    out["hbar00_over_phi_median"] = float(np.median(r_hb))
    out["h00_over_phi_median"] = float(np.median(r_h))
    out["h00_over_phi_cv"] = float(np.std(r_h) / (abs(np.median(r_h)) + 1e-300))
    out["h00_over_phi_tolman_expected"] = 2.0 * (1.0 + tr3p)
    out["pressure_explains_deviation"] = bool(
        abs(out["h00_over_phi_median"] - out["h00_over_phi_tolman_expected"])
        < 0.5 * abs(out["h00_over_phi_median"] - 2.0) + 0.02)
    out["hxx_over_phi_median"] = float(np.median((hxx[sl] / phi_line)[mask]))

    # 1/r dilution of the EVOLVED potential
    idx = np.indices((L, L, L))
    r = np.sqrt(sum((idx[i] - ctr[i]) ** 2 for i in range(3))).ravel()
    v = (h00 - h00.mean()).ravel()
    order = np.argsort(r)
    r, v = r[order], v[order]
    bins = np.linspace(1, L // 2, 30)
    rc = 0.5 * (bins[:-1] + bins[1:])
    prof = np.array([v[(r >= bins[i]) & (r < bins[i + 1])].mean()
                     for i in range(len(bins) - 1)])
    prof = prof - prof[-1]
    win = (rc > 0.10 * L) & (rc < 0.40 * L) & np.isfinite(prof)
    A = np.polyfit(1.0 / rc[win], prof[win], 1)
    out["invr_fit_corr"] = float(np.corrcoef(
        prof[win], np.polyval(A, 1.0 / rc[win]))[0, 1])

    # Eddington factor from the SAME evolved h (weak-field rescale, tq pattern)
    h00_sl = h00[..., ctr[2]]
    hxx_sl = hxx[..., ctr[2]]
    scale = 3e-4 / (np.abs(0.5 * h00_sl).max() + 1e-300)
    n_t = 1.0 - 0.5 * (h00_sl + hxx_sl) * scale
    n_s = 1.0 - 0.5 * h00_sl * scale
    out["eddington_ratio"] = float(pathB._deflection(n_t, L, b_imp)
                                   / pathB._deflection(n_s, L, b_imp))

    # ---- 回授 (feedback) test: the tensor coin DEFLECTS matter toward the blob
    hsc = h_phys * (steer_contrast
                    / (np.abs(0.5 * (h00 + np.maximum(np.maximum(
                        h_phys[..., PKXX], h_phys[..., PKYY]),
                        h_phys[..., PKZZ]))).max() + 1e-300))
    ths, _cs = theta_fields(hsc, th0)
    out["steer_max_dtheta"] = float(max(np.abs(t - th0).max() for t in ths))
    x = np.arange(L)
    y0 = ctr[1] + b_imp
    dxt = ((x - 8 + L // 2) % L) - L // 2         # centered torus distance
    envp = np.exp(-((dxt[:, None, None]) ** 2
                    + (x[None, :, None] - y0) ** 2
                    + (x[None, None, :] - ctr[2]) ** 2) / (4.0 * 3.0 ** 2))
    chi = branch_state([k_steer, 0, 0], (th0,) * 3, 0.0)
    pk0 = (envp * np.exp(1j * k_steer * x[:, None, None]))[..., None] * chi
    pk0 = pk0 / math.sqrt(float(np.sum(np.abs(pk0) ** 2)))

    def ycen(p):
        rho = np.sum(np.abs(p) ** 2, axis=-1)
        return float((rho.sum(axis=(0, 2)) * x).sum() / rho.sum())

    pa, pb_ = pk0.copy(), pk0.copy()
    for _ in range(T_steer):
        pa = walker_step(pa, ths[0], ths[1], ths[2], 0.0, th0)  # feedback field
        pb_ = walker_step(pb_, th0, th0, th0, 0.0, th0)         # control
    out["deflection_dy"] = float(ycen(pa) - ycen(pb_))        # <0 = toward blob
    out["deflection_toward_blob"] = bool(out["deflection_dy"] < 0)

    ok = (abs(out["h00_over_phi_median"] - 2.0) < 0.05
          and out["h00_over_phi_cv"] < 0.05
          and abs(out["hbar00_over_phi_median"] - 4.0) < 0.10
          and out["invr_fit_corr"] > 0.99
          and out["poisson_residual"] < tol
          and abs(out["eddington_ratio"] - 2.0) < 0.05
          and out["deflection_toward_blob"]
          and abs(out["deflection_dy"]) > 0.05)
    out["pass"] = bool(ok)
    return out


def newton_massless_probe(L=48, sig=2.5, th0=0.45, **kw):
    """same pipeline, massless (radiation) blob -- diagnostic only, no gate:
    a relativistic source has pressure ~ rho/3, so h00/phi is NOT expected
    to be 2 (Tolman: effective source rho + 3p)."""
    r = judge_newton(L=L, sig=sig, dm=0.0, th0=th0, T_avg=16,
                     steer_contrast=0.15, **kw)
    return {"h00_over_phi_median": r["h00_over_phi_median"],
            "pressure_over_T00": r["pressure_over_T00"],
            "invr_fit_corr": r["invr_fit_corr"],
            "note": "radiation-like source; deviation from 2 is physics "
                    "(rho+3p), not failure"}


# ======================================================================
#  JUDGE LOOP -- full co-evolution (live source + live feedback)
# ======================================================================
def judge_closed_loop(L=36, sig=3.0, dm=1.5, th0=0.45, cg2=0.25, G=0.03,
                      gamma=0.05, T=200, causal_T=25, sponge_w=0, sponge_max=0.3):
    """full co-evolution.  gamma=0.02 is the torus stand-in for outgoing-wave
    boundary conditions (waves cannot escape a torus; without a sink the
    switch-on ringing never settles -- measured and reported via the secondary
    gamma=0 run, which is judged on stability only)."""
    out = {"L": L, "G": G, "gamma": gamma, "T": T}
    ctr = (L // 2,) * 3
    env, r2 = _gauss3(L, ctr, sig)
    psi = env[..., None] * CHI_BLOB
    psi = psi / math.sqrt(float(np.sum(np.abs(psi) ** 2)))
    params = {"th0": th0, "dm": dm, "cg2": cg2, "G": G, "gamma": gamma}
    sp = _sponge_field(L, sponge_w, sponge_max)
    if sp is not None:
        params["sponge"] = sp
    out["sponge_w"] = sponge_w
    state = (psi.copy(), psi.copy(), np.zeros((L, L, L, 10)),
             np.zeros((L, L, L, 10)))

    norms, e_w, e_f, h00min, times = [], [], [], [], []
    T_last = None
    warm = 20                                    # skip the D_0 warmup transient
    field_energy = lambda hb, hbp: float(
        np.sum((hb - hbp) ** 2) + cg2 * sum(
            np.sum((np.roll(hb, -1, ax) - hb) ** 2) for ax in (0, 1, 2)))
    blowup = False
    for t in range(T):
        state, Tst = loop_step(state, params)
        T_last = Tst
        if not np.all(np.isfinite(state[2])):
            blowup = True
            out["blowup_step"] = t
            break
        if (t % 10 == 0 and t >= warm) or t == T - 1:
            times.append(t)
            norms.append(float(np.sum(np.abs(state[1]) ** 2)))
            e_w.append(float(np.sum(Tst[..., PK00])))
            e_f.append(field_energy(state[2], state[3]))
            h00min.append(float(tq.trace_reverse_packed(state[2])[..., PK00].min()))
    out["stable"] = bool(not blowup)
    out["walker_norm_drift"] = float(abs(norms[-1] / norms[0] - 1.0)) if norms else float("nan")
    out["walker_energy_start_mid_end"] = ([e_w[0], e_w[len(e_w) // 2], e_w[-1]]
                                          if e_w else [])
    out["walker_energy_drift"] = (float(abs(e_w[-1] - e_w[0]) / (abs(e_w[0]) + 1e-300))
                                  if e_w else float("nan"))
    out["field_energy_series_head_tail"] = ([e_f[0], e_f[len(e_f) // 2], e_f[-1]]
                                            if e_f else [])
    out["field_energy_growth_late"] = (float(e_f[-1] / (e_f[len(e_f) // 2] + 1e-300))
                                       if e_f else float("nan"))
    out["h00_min_final"] = h00min[-1] if h00min else float("nan")

    if not blowup:
        h_phys = tq.trace_reverse_packed(state[2])
        h00 = h_phys[..., PK00]
        # well check: the live field must track the quasi-static Poisson
        # response to its OWN live source, h00 ~ 2 phi[T00_live]
        rho_live = T_last[..., PK00]
        phi_live = s2._poisson_fft(rho_live - rho_live.mean(), L, 4 * np.pi * G)
        out["well_poisson_corr"] = float(np.corrcoef(
            (h00 - h00.mean()).ravel(), (2 * phi_live).ravel())[0, 1])
        out["well_depth"] = float(h00.min())
        out["well_depth_over_2phimin"] = float(h00.min() / (2 * phi_live.min())
                                               ) if phi_live.min() < 0 else float("nan")
        # the loop's claim is 'the well sits on the LIVE matter': compare the
        # smoothed h00 minimum with the smoothed live-Poisson minimum (the
        # matter itself drifts/disperses -- that is the walker's own measured
        # deficiency, reported separately as blob_coherence below)
        def smin(f):
            fs = f.copy()
            for ax in (0, 1, 2):
                fs = (np.roll(fs, 1, ax) + np.roll(fs, -1, ax) + 2 * fs) / 4
            return np.unravel_index(np.argmin(fs), fs.shape)
        la = smin(h00)
        lb = smin(phi_live)
        doff = [min(abs(la[i] - lb[i]), L - abs(la[i] - lb[i])) for i in range(3)]
        out["well_vs_source_offset"] = float(np.sqrt(sum(d * d for d in doff)))
        rr0 = np.sqrt(r2)
        out["matter_frac_within_3sig_final"] = float(
            T_last[..., PK00][rr0 < 3 * sig].sum()
            / (T_last[..., PK00].sum() + 1e-300))

        # causality: fresh short run; the uniform neutralizing background
        # (k=0 Jeans swindle, carries no signal) is removed per component.
        st2 = (psi.copy(), psi.copy(), np.zeros((L, L, L, 10)),
               np.zeros((L, L, L, 10)))
        for _ in range(causal_T):
            st2, _T2 = loop_step(st2, params)
        # signal = spatial STRUCTURE.  The k=0 Jeans-swindle background gives
        # every far site the same uniform offset (bookkeeping, not signal), so
        # causality is judged on the variance: structure outside the cone.
        rr = np.sqrt(r2)
        reach = math.sqrt(cg2) * causal_T + 4 * sig
        outside = rr > reach
        num = den = 0.0
        for c in range(10):
            f = st2[2][..., c]
            num += float(np.sum((f[outside] - f[outside].mean()) ** 2))
            den += float(np.sum((f - f.mean()) ** 2))
        out["causal_reach"] = reach
        out["causal_leak_fraction"] = num / (den + 1e-300)

        # secondary: undamped (gamma=0) run -- stability only; the switch-on
        # ringing has no escape on a torus, so the well is noisy (reported).
        p0 = dict(params); p0["gamma"] = 0.0
        st0 = (psi.copy(), psi.copy(), np.zeros((L, L, L, 10)),
               np.zeros((L, L, L, 10)))
        ef0 = []
        g0_ok = True
        for t in range(T):
            st0, T0l = loop_step(st0, p0)
            if not np.all(np.isfinite(st0[2])):
                g0_ok = False
                break
            if t % 20 == 0 and t >= warm:
                ef0.append(field_energy(st0[2], st0[3]))
        out["gamma0_stable"] = bool(g0_ok)
        out["gamma0_field_growth_late"] = (float(ef0[-1] / (ef0[len(ef0) // 2] + 1e-300))
                                           if len(ef0) > 3 else float("nan"))
        if g0_ok:
            h00g0 = tq.trace_reverse_packed(st0[2])[..., PK00]
            rho0l = T0l[..., PK00]
            phi0 = s2._poisson_fft(rho0l - rho0l.mean(), L, 4 * np.pi * G)
            out["gamma0_well_poisson_corr"] = float(np.corrcoef(
                (h00g0 - h00g0.mean()).ravel(), (2 * phi0).ravel())[0, 1])
    else:
        out["well_poisson_corr"] = float("nan")
        out["well_vs_source_offset"] = float("nan")
        out["causal_leak_fraction"] = float("nan")
        out["gamma0_stable"] = False

    ok = (out["stable"]
          and out["walker_norm_drift"] < 1e-9
          and out["walker_energy_drift"] < 0.05
          and out["field_energy_growth_late"] < 3.0
          and out["well_poisson_corr"] > 0.9
          and out["well_vs_source_offset"] <= 3.0
          and out["causal_leak_fraction"] < 1e-3
          and out["gamma0_stable"]
          and out["gamma0_field_growth_late"] < 3.0)
    out["pass"] = bool(ok)
    return out


# ======================================================================
#  JUDGE 1/3 -- does the matter coupling break the emergent sector?
#  (rule dicts for emergence_judge: bare leapfrog / null-damped control,
#   each with and without the live walker source + feedback)
# ======================================================================
def make_matter_rule(base="spin2", cg2=0.25, kappa=0.5, G_m=0.01, th0=0.45,
                     amp=0.02, dm=0.3, feedback=True, seed=11):
    """emergence_judge-compatible rule with an INTERNAL live walker.

    The walker state lives in a closure; a new trajectory is detected by array
    identity (the judges always feed back exactly the array the rule returned).
    Walker ICs: smooth random psi with rms `amp` (linear regime: the matter
    source is a small perturbation on the judge's O(1) tensor ICs)."""
    c2 = float(cg2)
    fac = 1.0 / (1.0 + kappa / (2 * c2))
    n_levels = 2 if base == "spin2" else 4
    cache = {"last": None, "psi_prev": None, "psi": None, "count": 0}

    def init_walker(h):
        rng = np.random.default_rng(seed + cache["count"])
        cache["count"] += 1
        shape = h.shape[:-1] + (4,)
        p = rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
        for _ in range(3):
            for ax in (-4, -3, -2):
                p = (np.roll(p, 1, ax) + np.roll(p, -1, ax) + 2 * p) / 4
        p *= amp / (np.sqrt(np.mean(np.abs(p) ** 2)) + 1e-300)
        cache["psi_prev"] = p.copy()
        cache["psi"] = p

    def step(state):
        h = state[0]
        if cache["last"] is not h:
            init_walker(h)
        if feedback:
            ths, cs = theta_fields(tq.trace_reverse_packed(h), th0)
        else:
            ths, cs = (th0, th0, th0), (math.cos(th0),) * 3
        psi_next = walker_step(cache["psi"], ths[0], ths[1], ths[2], dm, th0)
        T = stress_tensor(cache["psi_prev"], cache["psi"], psi_next, cs)
        sp_axes = tuple(range(T.ndim - 4, T.ndim - 1))
        src = -SIXTEEN_PI * G_m * (T - T.mean(axis=sp_axes, keepdims=True))
        cache["psi_prev"], cache["psi"] = cache["psi"], psi_next

        if base == "spin2":
            nxt = 2.0 * h - state[1] + c2 * (ej._lap3_batch(h) + src)
            new_state = (nxt, h)
        else:                                     # null-box + lag-free damping
            h1, h2, h3, h4 = state
            nxt = 2.0 * h2 - h4 + c2 * (ej._lap_wide_batch(h2) + src)
            for nu in range(4):
                c0i = PK[(0, nu)]
                S = np.zeros(h1.shape[:-1])
                for j in (1, 2, 3):
                    S = S + ej._dsp(h1[..., PK[(j, nu)]], j)
                nxt[..., c0i] = fac * (nxt[..., c0i]
                                       + kappa * (h2[..., c0i] / (2 * c2) + S))
            new_state = (nxt, h1, h2, h3)
        cache["last"] = nxt
        return new_state

    tag = "+matter" if G_m != 0.0 else ""
    fb = ",fb" if (feedback and G_m != 0.0) else ""
    return {"name": f"{base}{tag}{fb} (G_m={G_m}, amp={amp})",
            "n_levels": n_levels, "cg2": cg2, "step": step}


def judge_propagation(N=16, quick=True, G_m=0.01, G_scale=1.0):
    """emergence_judge A+B on 4 configs; the matter question is the DELTA."""
    T_A, trials = (512, 8) if quick else (800, 12)
    T_B = 500 if quick else 600
    configs = [
        ("spin2 bare", make_matter_rule("spin2", G_m=0.0, feedback=False)),
        ("spin2 + matter", make_matter_rule("spin2", G_m=G_m, feedback=True)),
        ("null-damped bare", make_matter_rule("null", G_m=0.0, feedback=False)),
        ("null-damped + matter", make_matter_rule("null", G_m=G_m, feedback=True)),
    ]
    if G_scale != 1.0:
        configs.append(("null-damped + matter x%g" % G_scale,
                        make_matter_rule("null", G_m=G_m * G_scale, feedback=True)))
    rows = {}
    for name, rule in configs:
        a = ej.judge_dof(rule, N=N, T=T_A, trials=trials)
        bres = ej.judge_gauge(rule, N=N, T=T_B)
        rows[name] = {
            "n_prop_all": a["n_prop_all"], "n_prop": a["n_prop"],
            "lightcone_ok": a["lightcone_ok"], "speed": a["speed_mean"],
            "stable": a["stable"] and bres["stable"],
            "c_decay_ratio": bres["c_decay_ratio"],
            "gauge_conversion": bres["gauge_conversion"],
            "tt_survival": bres["tt_survival"],
            "passes_A": a["pass"], "passes_B": bres["pass"],
            "passes_emergence": bool(a["pass"] and bres["pass"]),
        }
    base_ok = rows["null-damped bare"]["passes_emergence"]
    with_m = rows["null-damped + matter"]
    out = {"configs": rows,
           "control_passes_without_matter": bool(base_ok),
           "control_passes_with_matter": bool(with_m["passes_emergence"]),
           "matter_C_floor_ratio": float(with_m["c_decay_ratio"]),
           "matter_gauge_conversion": float(with_m["gauge_conversion"])}
    out["pass"] = bool(base_ok and with_m["passes_emergence"]
                       and rows["spin2 + matter"]["n_prop"]
                       == rows["spin2 bare"]["n_prop"])
    return out


# ======================================================================
#  driver
# ======================================================================
def run_all(quick=False):
    res = {"backend": B.NAME}
    res["construction"] = construction_certificate()
    res["conservation"] = judge_conservation()
    res["newton"] = judge_newton()
    res["newton_massless_probe"] = newton_massless_probe()
    res["closed_loop"] = judge_closed_loop()
    res["propagation"] = judge_propagation(quick=True, G_scale=100.0)
    return res


def _diagnose(res):
    d = []
    cons, nw, lp, pr = (res["conservation"], res["newton"],
                        res["closed_loop"], res["propagation"])
    if not cons["pass"]:
        d.append("T_munu NOT LATTICE-CONSERVED at the required level: overall "
                 "residual %.3f (baseline %.3f). The bilinear D-current is not "
                 "the walk's exact conserved current; the mismatch feeds the "
                 "de-Donder constraint of the sourced field. Fix: derive the "
                 "exact quasi-local current from the shift structure (the same "
                 "step (a) tensor_walker prescribes for the 16-comp walker)."
                 % (cons["residual_overall"], cons["residual_decorrelated"]))
    if not nw["pass"]:
        d.append("NEWTONIAN SECTOR INCOMPLETE: h00/phi=%.3f (cv %.3f), "
                 "1/r corr %.3f, Poisson resid %.2e, Eddington %.3f, "
                 "deflection dy=%.3f. See raw numbers for which gate failed."
                 % (nw["h00_over_phi_median"], nw["h00_over_phi_cv"],
                    nw["invr_fit_corr"], nw["poisson_residual"],
                    nw["eddington_ratio"], nw["deflection_dy"]))
    else:
        d.append("NEWTONIAN SECTOR CLOSED (positive result): the walker's OWN "
                 "bilinear T_munu sources h00/phi=%.3f (target 2), 1/r corr "
                 "%.4f, Eddington %.3f, and the tensor coin deflects a test "
                 "packet toward the blob (dy=%.3f). The sector a free unitary "
                 "walk provably lacks is supplied by the feedback loop."
                 % (nw["h00_over_phi_median"], nw["invr_fit_corr"],
                    nw["eddington_ratio"], nw["deflection_dy"]))
    if not lp["pass"]:
        d.append("DYNAMIC CLOSED LOOP problem: stable=%s, norm drift %.1e, "
                 "field growth %.2f, well-vs-Poisson corr %.2f, causal leak "
                 "%.1e." % (lp["stable"], lp["walker_norm_drift"],
                            lp["field_energy_growth_late"],
                            lp["well_poisson_corr"],
                            lp["causal_leak_fraction"]))
    cfg = pr["configs"]
    if cfg["spin2 bare"]["n_prop"] != 2:
        d.append("PROPAGATING SECTOR STILL WRONG ON THE BARE LEAPFROG "
                 "(N_prop=%d, known): the feedback loop does not and cannot "
                 "fix the DOF count -- that needs the null-compatible operator "
                 "(emergence_judge positive control) or the 16-comp walker "
                 "(step0/a). Matter coupling changes N_prop by %+d."
                 % (cfg["spin2 bare"]["n_prop"],
                    cfg["spin2 + matter"]["n_prop"] - cfg["spin2 bare"]["n_prop"]))
    if pr["control_passes_without_matter"] and not pr["control_passes_with_matter"]:
        d.append("MATTER COUPLING BREAKS THE EMERGENT SECTOR: the null-damped "
                 "control passes alone but fails with the live T source "
                 "(C floor %.1e, conversion %.3f) -- the conservation residual "
                 "of the bilinear T is the likely culprit; see judge CONS."
                 % (pr["matter_C_floor_ratio"], pr["matter_gauge_conversion"]))
    if pr["control_passes_without_matter"] and pr["control_passes_with_matter"]:
        d.append("FEEDBACK IS COMPATIBLE WITH THE EMERGENT SECTOR: adding the "
                 "live walker source + tensor-coin feedback keeps the positive "
                 "control at N_prop=2 with constraint decay %.1e and gauge "
                 "conversion %.3f (thresholds 1e-3 / 0.05)."
                 % (pr["matter_C_floor_ratio"], pr["matter_gauge_conversion"]))
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "data", "results",
                                                   "tensor_coin_feedback_results.json"))
    args = ap.parse_args()

    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("TENSOR COIN FEEDBACK: bilinear T_munu -> box hbar = -16 pi G T -> "
          "per-axis coin c_i = cos th0 (1 + (h00+hii)/2)\n")

    res = run_all()

    cc = res["construction"]
    print("[CONSTRUCTION] tensor-coin walker (per-axis sandwich, axis bases)")
    print(f"    unitarity drift (50 steps, inhomogeneous theta) = "
          f"{cc['unitarity_drift']:.2e}")
    print(f"    per-axis speeds (th=0.40,0.55,0.70): measured "
          f"{[f'{v:.4f}' for v in cc['axis_speed_measured']]} vs cos(th) "
          f"{[f'{v:.4f}' for v in cc['axis_speed_target_costh']]}"
          f"  (max err {cc['axis_speed_max_err']:.1e})")
    print(f"    exact 1D dispersion identity err = "
          f"{cc['axis_dispersion_exact_err']:.1e}   diag-k isotropy = "
          f"{cc['isotropy_diag_speed_over_c']:.4f}")
    print(f"    -> {'PASS' if cc['pass'] else 'FAIL'}\n")

    cons = res["conservation"]
    print("[CONS] discrete conservation D^mu T_munu (eta_c divergence)")
    print(f"    quasi-1D packet residual = {cons['residual_quasi1d']:.4f}  "
          f"(gate < 0.05)")
    print(f"    3D packet residual       = {cons['residual_overall']:.4f}  "
          f"per-nu {[f'{v:.3f}' for v in cons['residual_per_nu']]}  (gate < 0.10)")
    print(f"    decorrelated baseline    = {cons['residual_decorrelated']:.4f}  "
          f"(generic field ~ O(1))")
    print(f"    global sum(T00) drift    = {cons['global_T00_drift']:.2e}")
    print(f"    inhomogeneous theta (rms 0.05): residual = "
          f"{cons['residual_inhomogeneous_theta']:.4f}  "
          f"(includes the covariant force density, physical)")
    print(f"    EXACT rho bond-current continuity residual = "
          f"{cons['rho_current']['continuity_residual_max']:.2e}  "
          f"(exact local conservation exists)")
    print(f"    plane-wave stress mismatch (worst |T/T_conserved - 1| per mode):")
    for nv, worst in cons["planewave_worst_mismatch"].items():
        print(f"        k ~ {nv:12s} : {worst:.3f}")
    print(f"    -> {'PASS' if cons['pass'] else 'FAIL'}\n")

    nw = res["newton"]
    print("[J2 NEWTON] static walker blob -> measured T_munu -> relaxed hbar")
    print(f"    blob rms radius {nw['blob_rms_radius_start']:.2f} -> "
          f"{nw['blob_rms_radius_end']:.2f} over averaging window; "
          f"pressure/T00 = {nw['pressure_over_T00']:.3f}, "
          f"T00<0 fraction = {nw['T00_negative_fraction']:.2e}")
    print(f"    relaxation: {nw['relax_steps']} steps, Poisson residual = "
          f"{nw['poisson_residual']:.2e}")
    print(f"    hbar00/phi = {nw['hbar00_over_phi_median']:.4f} (target 4)   "
          f"h00/phi = {nw['h00_over_phi_median']:.4f} (target 2, "
          f"cv {nw['h00_over_phi_cv']:.4f})   hxx/phi = "
          f"{nw['hxx_over_phi_median']:.4f} (target 2)")
    print(f"    Tolman check: 3p/rho = {nw['trace_3p_over_rho']:.4f} -> "
          f"expected h00/phi = {nw['h00_over_phi_tolman_expected']:.4f}; "
          f"pressure explains the residual deviation: "
          f"{nw['pressure_explains_deviation']}")
    print(f"    1/r tail fit corr = {nw['invr_fit_corr']:.4f} (target >0.99)")
    print(f"    Eddington ratio (same evolved h) = "
          f"{nw['eddington_ratio']:.4f} (target 2)")
    print(f"    回授 deflection: dy = {nw['deflection_dy']:+.3f} cells "
          f"(toward blob: {nw['deflection_toward_blob']}; "
          f"max|dtheta| = {nw['steer_max_dtheta']:.3f})")
    print(f"    -> {'PASS' if nw['pass'] else 'FAIL'}\n")

    nm = res["newton_massless_probe"]
    print("[J2b massless probe, no gate] radiation-like source: h00/phi = "
          f"{nm['h00_over_phi_median']:.3f}, pressure/T00 = "
          f"{nm['pressure_over_T00']:.3f}  ({nm['note']})\n")

    lp = res["closed_loop"]
    print("[LOOP] full co-evolution (live source + live feedback)")
    print(f"    stable = {lp['stable']}   walker norm drift = "
          f"{lp['walker_norm_drift']:.2e} (unitary: machine 0)")
    print(f"    walker energy drift (post-warmup) = "
          f"{lp['walker_energy_drift']:.2e}   field energy late growth = "
          f"{lp['field_energy_growth_late']:.3f}")
    print(f"    well: depth h00_min = {lp['h00_min_final']:.2e} "
          f"(= {lp.get('well_depth_over_2phimin', float('nan')):.2f} x "
          f"quasi-static 2phi), corr vs live Poisson = "
          f"{lp['well_poisson_corr']:.3f}, well-vs-source offset = "
          f"{lp['well_vs_source_offset']:.1f} cells")
    print(f"    matter still within 3 sigma of start at t=T: "
          f"{lp['matter_frac_within_3sig_final']:.2f}  "
          f"(walker mass-sector defect, see CONSTRUCTION)")
    print(f"    causal leak (fresh run, reach {lp.get('causal_reach', 0):.1f}) = "
          f"{lp['causal_leak_fraction']:.2e}")
    print(f"    -> {'PASS' if lp['pass'] else 'FAIL'}\n")

    pr = res["propagation"]
    print("[J1/J3 EMERGENCE] projection-free judges, with/without matter")
    hdr = f"    {'config':26s} {'N_prop':>6s} {'cone':>5s} {'C decay':>9s} " \
          f"{'convert':>8s} {'TTsurv':>7s} {'A':>3s} {'B':>3s}"
    print(hdr)
    for name, r in pr["configs"].items():
        print(f"    {name:26s} {r['n_prop']:>6d} "
              f"{'ok' if r['lightcone_ok'] else 'NO':>5s} "
              f"{r['c_decay_ratio']:>9.1e} {r['gauge_conversion']:>8.3f} "
              f"{r['tt_survival']:>7.2f} "
              f"{'P' if r['passes_A'] else 'F':>3s} "
              f"{'P' if r['passes_B'] else 'F':>3s}")
    print(f"    -> {'PASS' if pr['pass'] else 'FAIL'}  (gate: control keeps "
          f"emergence with matter; matter does not change bare N_prop)\n")

    table = [("CONSTRUCTION", cc["pass"]), ("T CONSERVATION", cons["pass"]),
             ("J2 NEWTON (main)", nw["pass"]), ("DYNAMIC LOOP", lp["pass"]),
             ("J1/J3 EMERGENCE+matter", pr["pass"])]
    print("=" * 70)
    for name, ok in table:
        print(f"  {name:30s} {'PASS' if ok else 'FAIL'}")
    all_pass = all(ok for _n, ok in table)
    print("=" * 70)
    print("ALL PASS" if all_pass else "SOME FAILED (see diagnosis)")

    print("\n[DIAGNOSIS]")
    diags = _diagnose(res)
    for i, t in enumerate(diags, 1):
        print(f"  ({i}) {t}\n")
    res["diagnosis"] = diags
    res["all_pass"] = bool(all_pass)

    print("[HONEST SCOPE]")
    print("  * The geometry update is the repo's hand-written leapfrog "
          "(spin2/tensor_qca);")
    print("    what is NEW here is the CLOSED LOOP: source = walker bilinear "
          "T_munu (not a")
    print("    hand-placed Gaussian) and h steers the walker's per-axis coin. "
          "The Newtonian")
    print("    1/r sector therefore now comes from measured matter, through "
          "feedback -- the")
    print("    static limit of the loop -- not from a free walk's bilinears "
          "(impossible).")
    print("  * Coin coupling implements h00 + diagonal h_ii only; h_0i and "
          "off-diagonal h_ij")
    print("    need the 16-component walker (step0/a agent). Interface: "
          "theta_fields().")

    with open(args.json, "w") as fh:
        json.dump(res, fh, indent=1, default=lambda o: (
            o.tolist() if isinstance(o, np.ndarray) else float(o)))
    print(f"\nwrote {os.path.abspath(args.json)}")
