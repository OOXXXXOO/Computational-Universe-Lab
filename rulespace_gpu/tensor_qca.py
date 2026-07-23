"""tensor_qca.py -- a FIRST candidate TENSOR-QCA rule + honest verdict.

WHAT THIS IS (be honest, up front):
    A concrete, local, cellular update ("tensor-QCA") that evolves the 10
    symmetric components of the metric perturbation h_munu on a 3D spatial
    lattice with a leapfrog time step, whose continuum limit is LINEARIZED
    TENSOR GRAVITY (Fierz-Pauli).  It is the structural generalization of the
    scalar theta-field CA rule in engine.py (theta -> h_munu, scalar coin ->
    tensor coin), and it is judged on the SAME fixed acceptance bar as
    spin2_evolver (reusing that module's measurement helpers).

    The one genuinely NEW ingredient over spin2_evolver -- and the ingredient
    HANDOFF_03 step 2 explicitly calls for -- is a DISCRETE ANALOGUE OF
    LINEARIZED DIFFEOMORPHISM INVARIANCE:

        h_munu(x) -> h_munu(x) + D_mu xi_nu(x) + D_nu xi_mu(x)

    built from *commuting* lattice difference operators D_mu.  spin2_evolver has
    NO gauge transformation at all -- it picks harmonic gauge by hand and evolves
    box h-bar = 0.  Here the linearized Einstein/Ricci operator E_munu[h] is
    constructed from commuting second-difference stencils, so it is EXACTLY
    diffeomorphism-invariant on the lattice (verified to machine precision), and
    pure-gauge configurations h = D xi + D xi are EXACT null modes of E_munu.
    That is the discrete mechanism that "projects out" the longitudinal / trace
    modes: they carry no discrete curvature, hence no gauge-invariant energy,
    hence exactly 2 physical (TT) DOF propagate.

HONEST SCOPE / WHAT THIS IS NOT:
    - The *evolution* used for the three dynamical judges is still a leapfrog on
      the trace-reversed field in harmonic gauge (box h-bar = -16 pi G T).  That
      is the same operator class as spin2_evolver.  The NEW content is (i) the
      explicit lattice diffeomorphism operator and its exact-invariance
      certificate, (ii) gauge modes shown to be exact null modes of the discrete
      Einstein tensor (the operator-level reason for 2 DOF), (iii) a genuinely
      *dynamical* (evolved-to-fixed-point) Newtonian + lensing test that
      exercises the source coupling and trace reversal of the rule, not a static
      FFT solve, and (iv) the runner plug-in interface evaluate_tensor_rule().
    - It is STILL NOT a multi-component *walker* (a Dirac-style tensor coin)
      whose continuum limit is Fierz-Pauli.  That walker realization remains the
      open frontier; see the diagnosis printed by __main__ and the report.

Run:   RULESPACE_BACKEND=numpy python -m rulespace_gpu.tensor_qca
"""
import argparse
import json
import os

import numpy as np

from . import backend as B
from . import pathB_spin2 as pathB
from . import spin2_evolver as s2   # reuse the FIXED harness helpers & thresholds

DIR = os.path.dirname(os.path.abspath(__file__))

# spacetime: 0=t,1=x,2=y,3=z ; signature (-+++).
ETA = np.diag([-1.0, 1.0, 1.0, 1.0])
IDX10 = s2.IDX10           # packing order of the 10 symmetric components
SPATIAL = s2.SPATIAL


# ======================================================================
#  PART 1.  discrete diffeomorphism structure (the NEW ingredient)
#           built on a small 4D spacetime block so D_0 is a real derivative.
# ======================================================================
def _D(f, mu):
    """Central lattice derivative along spacetime axis mu (0=t,1=x,2=y,3=z).

    (D_mu f)(x) = [f(x+e_mu) - f(x-e_mu)] / 2.   Unit spacing.  Central
    differences on a regular lattice COMMUTE: D_mu D_nu = D_nu D_mu exactly.
    That commutativity is the whole ballgame -- it is what makes the discrete
    Einstein operator below exactly diffeomorphism-invariant.
    """
    return 0.5 * (np.roll(f, -1, axis=mu) - np.roll(f, 1, axis=mu))


def gauge_transform(h4, xi):
    """Discrete linearized diffeomorphism  h_munu -> h_munu + D_mu xi_nu + D_nu xi_mu.

    h4 : (...,4,4) symmetric tensor field over a 4D spacetime block.
    xi : (...,4)   gauge 1-form field.
    Returns the transformed h4 (still symmetric by construction).
    """
    out = h4.copy()
    for m in range(4):
        for n in range(4):
            out[..., m, n] = out[..., m, n] + _D(xi[..., n], m) + _D(xi[..., m], n)
    return out


def einstein_lin(h4):
    """Discrete LINEARIZED RICCI tensor E_munu[h] on a 4D spacetime block.

        R_munu = 1/2 ( D^a D_mu h_{a nu} + D^a D_nu h_{a mu}
                       - D^a D_a h_{mu nu} - D_mu D_nu h )

    with D^a = eta^{ab} D_b and h = eta^{ab} h_{ab} (the trace).  Because every
    D commutes with every other D on the lattice, E_munu is EXACTLY invariant
    under gauge_transform (verified numerically in gauge_certificate).  In
    vacuum R_munu = 0 is the linearized Einstein equation; pure-gauge fields are
    exact null modes.
    """
    h4 = np.asarray(h4)
    trace = np.zeros(h4.shape[:-2])
    for a in range(4):
        for b in range(4):
            trace = trace + ETA[a, b] * h4[..., a, b]

    R = np.zeros_like(h4)
    for m in range(4):
        for n in range(4):
            # T1 = D^a D_mu h_{a n} ;  T2 = D^a D_nu h_{a m}
            T1 = np.zeros(h4.shape[:-2]); T2 = np.zeros(h4.shape[:-2])
            box = np.zeros(h4.shape[:-2])
            for a in range(4):
                for b in range(4):
                    eab = ETA[a, b]
                    if eab != 0.0:
                        T1 = T1 + eab * _D(_D(h4[..., a, n], m), b)
                        T2 = T2 + eab * _D(_D(h4[..., a, m], n), b)
                        box = box + eab * _D(_D(h4[..., m, n], b), a)
            T4 = _D(_D(trace, n), m)
            R[..., m, n] = 0.5 * (T1 + T2 - box - T4)
    return R


def gauge_certificate(N=8, seed=0):
    """Decisive numerical certificate of the discrete gauge structure.

    (a) EXACT diffeomorphism invariance:  max| E[h + D xi + D xi] - E[h] | == 0.
    (b) Pure gauge is an EXACT null mode:  max| E[D xi + D xi] |          == 0.
    Both to machine precision -> the discrete linearized Einstein operator has
    the Fierz-Pauli gauge symmetry built in, NOT imposed by a post-hoc projector.
    """
    rng = np.random.default_rng(seed)
    shape = (N, N, N, N)                         # (t,x,y,z) block
    # random symmetric tensor field
    h = rng.standard_normal(shape + (4, 4))
    h = 0.5 * (h + np.swapaxes(h, -1, -2))
    xi = rng.standard_normal(shape + (4,))

    R0 = einstein_lin(h)
    R1 = einstein_lin(gauge_transform(h, xi))
    inv_resid = float(np.max(np.abs(R1 - R0)))
    scale = float(np.max(np.abs(R0)) + 1e-300)

    pure_gauge = gauge_transform(np.zeros(shape + (4, 4)), xi)
    R_pg = einstein_lin(pure_gauge)
    null_resid = float(np.max(np.abs(R_pg)))
    pg_scale = float(np.max(np.abs(pure_gauge)) + 1e-300)

    return {
        "diffeo_invariance_residual": inv_resid,
        "diffeo_invariance_relative": inv_resid / scale,
        "pure_gauge_null_residual": null_resid,
        "pure_gauge_field_scale": pg_scale,
        "exact_gauge_invariance": bool(inv_resid < 1e-9 * (scale + 1)),
        "gauge_modes_are_null": bool(null_resid < 1e-9 * (pg_scale + 1)),
    }


# ======================================================================
#  PART 2.  the tensor-QCA evolution rule (the dynamical update).
#           leapfrog on the 10 trace-reversed components, harmonic gauge,
#           with OPTIONAL damping (Newtonian relaxation) and an OPTIONAL
#           experimental de-Donder constraint driver.
# ======================================================================
def _laplacian3d(h):
    return s2._laplacian3d(h)                     # reuse the harness 6-point stencil


def qca_step(h, h_prev, cg2, source=None, gamma=0.0):
    """One tensor-QCA macro step on all 10 components.

        h_{t+1} = 2 h_t - h_{t-1} + cg2*Lap(h_t) [+ cg2*source] [- gamma*(h_t-h_{t-1})]

    gamma=0 (vacuum) reduces EXACTLY to spin2_evolver.leapfrog_step (same
    operator class).  gamma>0 adds friction so a static source relaxes to the
    discrete Poisson fixed point Lap(h) = -source (used by the Newtonian judge).
    Pure function (python-float scalars, positional roll) -> MLX/JAX-safe.
    """
    nxt = 2.0 * h - h_prev + cg2 * _laplacian3d(h)
    if source is not None:
        nxt = nxt + cg2 * source
    if gamma != 0.0:
        nxt = nxt - gamma * (h - h_prev)
    return nxt


class TensorQCA(s2.Spin2Field):
    """The candidate rule as a field object (reuses Spin2Field's buffers &
    measurement accessors; overrides the update to be the tensor-QCA step)."""

    def __init__(self, shape, cg2=0.25, dt=0.5, dx=1.0, gamma=0.0):
        super().__init__(shape, cg2=cg2, dt=dt, dx=dx)
        self.gamma = float(gamma)

    def step(self, source=None):
        nxt = qca_step(self.h, self.h_prev, self.cg2, source, self.gamma)
        self.h_prev, self.h = self.h, nxt


# ---- discrete trace reversal (exercised by the Newtonian judge) ----
def trace_reverse_packed(h_packed, sign=1.0):
    """h_munu = h-bar_munu - 1/2 eta_munu h-bar,  applied to a (...,10) field.

    sign flips the trace-reversal term so a WRONG implementation can be swept and
    caught by the Newtonian judge (sign=1 is correct; sign=0 disables it -> h==h-bar).
    """
    hp = np.asarray(h_packed)
    # trace h-bar = eta^{ab} h-bar_{ab}
    hbar_tr = np.zeros(hp.shape[:-1])
    for (mu, nu) in IDX10:
        c = IDX10.index((mu, nu))
        w = ETA[mu, nu] * (1.0 if mu == nu else 2.0)   # off-diagonal counted twice
        hbar_tr = hbar_tr + w * hp[..., c]
    out = hp.copy()
    for k, (mu, nu) in enumerate(IDX10):
        out[..., k] = hp[..., k] - sign * 0.5 * ETA[mu, nu] * hbar_tr
    return out


# ======================================================================
#  JUDGE 1 -- exactly 2 propagating TT polarizations at speed c
#             (mirrors spin2_evolver.fact1_two_polarizations, driven by the
#              tensor-QCA rule; reuses the harness's tt_project / thresholds)
# ======================================================================
def judge_fact1(Nz=192, cg2=0.25, dt=0.5, k0=None, sigma=9.0, T=120):
    out = {}
    # (1a) algebraic TT-projector rank (pure convention, reused verbatim)
    ks = [(0, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1), (0.3, 0.7, -0.4), (2, -1, 3)]
    ranks = [pathB.tt_projector_rank(k) for k in ks]
    out["tt_ranks"] = ranks
    out["tt_rank_all_2"] = all(r == 2 for r in ranks)

    Nx = Ny = 4
    shape = (Nx, Ny, Nz)
    zc = np.arange(Nz)
    z0 = Nz / 4.0
    if k0 is None:
        k0 = 2 * np.pi / 24.0
    # sub-cycle so cg2=1 clears even the quasi-1D CFL edge; the speed RATIO
    # (measured / c) is sub-cycle-invariant, so no unfolding is needed as long
    # as c, the packet seed, reach and normalization all use cg2_sim.
    cg2_sim = SUB2 * cg2
    c = (cg2_sim ** 0.5) * 1.0 / dt

    def broadcast(fz):
        return np.broadcast_to(fz.reshape(1, 1, Nz), shape).copy()

    # (1b) launch a +,x TT packet, measure propagation speed with the QCA rule
    F0 = s2._gaussian_wave(zc, z0, sigma, k0)
    Fprev = s2._gaussian_wave(zc + c * dt, z0, sigma, k0)
    fld = TensorQCA(shape, cg2=cg2_sim, dt=dt)
    fld.set_component(1, 1, broadcast(F0), broadcast(Fprev))
    fld.set_component(2, 2, broadcast(-F0), broadcast(-Fprev))
    fld.set_component(1, 2, broadcast(F0), broadcast(Fprev))

    def energy_z(field):
        v = field.velocity()
        vt = field.spatial_3x3(v)
        vtt = s2.tt_project(vt, (0, 0, 1))
        e = np.sum(vtt * vtt, axis=(-1, -2))
        return e.mean(axis=(0, 1))

    def centroid(ez):
        w = ez.sum()
        return float((zc * ez).sum() / w) if w > 0 else 0.0

    t_meas, c_meas = [], []
    warm = 20
    for t in range(T):
        fld.step()
        if t >= warm:
            t_meas.append(t); c_meas.append(centroid(energy_z(fld)))
    slope = np.polyfit(np.array(t_meas, float), np.array(c_meas), 1)[0]
    speed_phys = slope * (1.0 / dt)
    out["tt_packet_speed"] = float(speed_phys)
    out["tt_packet_speed_over_c"] = float(speed_phys / c)
    vg = np.cos(k0 / 2) / np.sqrt(1 - cg2_sim * np.sin(k0 / 2) ** 2)
    out["tt_speed_lattice_theory_over_c"] = float(vg)
    ez_final = energy_z(fld)
    reach = c * (T * dt) + 3 * sigma
    outside = np.abs(zc - z0) > reach
    out["causal_leak_fraction"] = float(ez_final[outside].sum() / (ez_final.sum() + 1e-30))

    # (1c) which spatial polarizations carry gauge-invariant (TT) energy, AND the
    # de-Donder constraint C = d^mu h-bar_{mu nu} that LABELS gauge vs physical.
    s2h = 2.0 ** -0.5
    pols = {
        "plus  (xx-yy)": [(1, 1, s2h), (2, 2, -s2h)],
        "cross (xy)":    [(1, 2, 1.0)],
        "breathing (xx+yy)": [(1, 1, s2h), (2, 2, s2h)],
        "long (zz)":     [(3, 3, 1.0)],
        "mixed (xz)":    [(1, 3, 1.0)],
        "mixed (yz)":    [(2, 3, 1.0)],
    }
    pol_fracs, pol_constraint = {}, {}
    for name, comps in pols.items():
        g = TensorQCA(shape, cg2=cg2_sim, dt=dt)
        for (mu, nu, amp) in comps:
            g.set_component(mu, nu, broadcast(amp * F0), broadcast(amp * Fprev))
        for _ in range(30):
            g.step()
        full = g.spatial_3x3()
        full = full - full.mean(axis=(0, 1, 2), keepdims=True)
        tt = s2.tt_project(full, (0, 0, 1))
        pol_fracs[name] = float(s2.frob2(tt) / (s2.frob2(full) + 1e-30))
        # de-Donder spatial constraint proxy for k=zhat: d_z h-bar_{z nu}
        hp = B.to_np(g.h)
        cnu = 0.0
        for nu in (1, 2, 3):
            key = (3, nu) if (3, nu) in IDX10 else (nu, 3)
            comp = hp[..., IDX10.index(key)]
            dz = 0.5 * (np.roll(comp, -1, 2) - np.roll(comp, 1, 2))
            cnu += float(np.sum(dz * dz))
        pol_constraint[name] = cnu
    out["polarization_tt_fraction"] = pol_fracs
    out["polarization_dedonder_C2"] = pol_constraint
    n_physical = sum(1 for f in pol_fracs.values() if f > 0.5)
    out["n_propagating_dof"] = n_physical

    ok = (out["tt_rank_all_2"] and n_physical == 2
          and abs(out["tt_packet_speed_over_c"] - 1.0) < 0.05
          and out["causal_leak_fraction"] < 1e-3)
    out["pass"] = bool(ok)
    return out


# ======================================================================
#  JUDGE 2 -- Newtonian limit h_00/phi -> 2, DYNAMICALLY (evolved to the
#             fixed point of the rule, NOT a static FFT solve).  This genuinely
#             exercises the rule's source coupling + discrete trace reversal.
# ======================================================================
# tier-2 sub-cycling (lane-A calibration, TENSOR_CAMPAIGN_INTERFACE.md):
# dt' = SUB dt lets physical cg2 up to (1/3)/SUB2 = 4/3 pass the 3D CFL, so the
# physical target cg2=1 is IN the search domain (tier-2 aligns UP to tier-1).
SUB, SUB2 = 0.5, 0.25          # SUB2 = SUB**2


def judge_fact2(L=40, sigma=3.5, G=1.0, cg2=0.25, dt=0.5, gamma=0.06,
                max_steps=6000, tol=1e-4, tr_sign=1.0):
    out = {}
    g = np.meshgrid(*[np.arange(L)] * 3, indexing="ij")
    c0 = L // 2
    r2 = sum((g[i] - c0) ** 2 for i in range(3))
    rho = np.exp(-r2 / (2 * sigma ** 2))
    rho = rho - rho.mean()                              # neutralizing torus background

    # --- evolve the QCA rule with a STATIC T_00 = rho source, damped to rest ---
    # box h-bar_00 = -16 pi G T_00  =>  d_t^2 h-bar_00 = Lap h-bar_00 - 16 pi G rho
    # leapfrog source slot is +cg2*source, so source = -16 pi G rho for the 00 comp.
    shape = (L, L, L)
    src = np.zeros(shape + (10,))
    src[..., IDX10.index((0, 0))] = -16 * np.pi * G * rho
    src_dev = B.asarray(src)

    # sub-cycle: cg2_sim<CFL carries the SUB2 factor; qca_step adds cg2*src, so
    # src stays PHYSICAL (also scaling src by SUB2 -> well 4x too low). gamma~dt.
    # Relaxation needs 1/SUB2 = 4x steps; fixed point Lap h = -src is physical, so
    # ALL h/phi thresholds below are unchanged (physical cg2 cancels).
    cg2_sim, gamma_sim = SUB2 * cg2, SUB * gamma
    cap = int(round(max_steps / SUB2))
    fld = TensorQCA(shape, cg2=cg2_sim, dt=dt, gamma=gamma_sim)
    resid_hist = []
    for it in range(cap):
        fld.step(source=src_dev)
        if (it + 1) % 200 == 0:
            hbar00 = B.to_np(fld.h)[..., IDX10.index((0, 0))]
            lap = B.to_np(_laplacian3d(fld.h))[..., IDX10.index((0, 0))]
            r = lap - 16 * np.pi * G * rho             # fixed point: Lap h-bar_00 = 16 pi G rho
            rr = float(np.sqrt(np.mean(r ** 2)) / (np.sqrt(np.mean((16*np.pi*G*rho) ** 2)) + 1e-30))
            resid_hist.append(rr)
            if rr < tol:
                break
    out["relax_steps"] = it + 1
    out["poisson_residual"] = resid_hist[-1] if resid_hist else float("nan")

    # --- read the EVOLVED trace-reversed field, apply the rule's trace reversal ---
    hbar_packed = B.to_np(fld.h)                        # (L,L,L,10) = evolved h-bar
    h_packed = trace_reverse_packed(hbar_packed, sign=tr_sign)   # -> physical h_munu
    hbar00 = hbar_packed[..., IDX10.index((0, 0))]
    h00 = h_packed[..., IDX10.index((0, 0))]
    hxx = h_packed[..., IDX10.index((1, 1))]           # spatial curvature from trace reversal

    # reference Newtonian potential: SAME 6-point discrete Laplacian fixed point
    phi = s2._poisson_fft(rho, L, 4 * np.pi * G)        # Lap phi = 4 pi G rho

    sl = tuple([slice(None)] + [c0, c0])
    phi_line = phi[sl]
    mask = np.abs(phi_line) > 0.05 * np.abs(phi_line).max()
    out["hbar00_over_phi"] = float(np.median((hbar00[sl] / phi_line)[mask]))     # -> 4
    out["h00_over_phi"] = float(np.median((h00[sl] / phi_line)[mask]))           # -> 2
    out["hxx_over_phi"] = float(np.median((hxx[sl] / phi_line)[mask]))           # -> 2 (space curv)

    # 3D 1/r dilution of the evolved potential (reuse spin2's diagnostic logic)
    idx = np.indices((L, L, L))
    r = np.sqrt(sum((idx[i] - c0) ** 2 for i in range(3))).ravel()
    v = (0.5 * hbar00 - (0.5 * hbar00).mean()).ravel()   # h00 ~ phi, evolved
    order = np.argsort(r); r, v = r[order], v[order]
    bins = np.linspace(1, L // 2, 30)
    rc = 0.5 * (bins[:-1] + bins[1:])
    prof = np.array([v[(r >= bins[i]) & (r < bins[i + 1])].mean() for i in range(len(bins) - 1)])
    prof = prof - prof[-1]
    win = (rc > 0.10 * L) & (rc < 0.40 * L) & np.isfinite(prof)
    if int(np.count_nonzero(win)) < 2:                     # 1/r window unresolved
        corr = 0.0            # (source too concentrated for this L) -> fail gracefully, don't crash
    else:
        A = np.polyfit(1.0 / rc[win], prof[win], 1)
        corr = float(np.corrcoef(prof[win], np.polyval(A, 1.0 / rc[win]))[0, 1])
    out["invr_fit_corr"] = corr

    ok = (abs(out["h00_over_phi"] - 2.0) < 0.02
          and abs(out["hbar00_over_phi"] - 4.0) < 0.02
          and abs(corr) > 0.99
          and out["poisson_residual"] < 5e-3)
    out["pass"] = bool(ok)
    # stash evolved slices for the deflection judge (tie fact3 to the SAME field)
    out["_slices"] = {"h00": h00[..., c0], "hxx": hxx[..., c0]}
    return out


# ======================================================================
#  JUDGE 3 -- light deflection factor 2 (Eddington), built from the SAME
#             evolved metric (h_00 time part + h_ij space part).  A wrong trace
#             reversal (no spatial curvature) would give ratio 1, not 2.
# ======================================================================
def judge_fact3(fact2_out=None, L=40, sigma=3.5, G=1.0, b=8):
    out = {}
    if fact2_out is None:
        fact2_out = judge_fact2(L=L, sigma=sigma, G=G)
    h00 = fact2_out["_slices"]["h00"]                   # (L,L) z-centre slice
    hxx = fact2_out["_slices"]["hxx"]

    # The Newtonian judge runs at O(1) source amplitude (fine for the linear,
    # amplitude-independent RATIO h_00/phi).  Light bending -> 2 is a WEAK-FIELD
    # limit (needs n ~ 1), so -- the field being exactly linear -- rescale the
    # evolved slices to a small well depth (matching pathB's weakest amp) and do
    # the same weak-field convergence sweep pathB does.
    rows = []
    for target in (3e-3, 3e-4, 3e-5):
        scale = target / (np.abs(0.5 * h00).max() + 1e-30)
        h00s, hxxs = h00 * scale, hxx * scale
        # photon index (propagation along x, deflected in y):
        #   n = 1 - 1/2 ( h_00 + h_xx )   [time part + space part along the ray]
        # scalar gravity feels only the time part:  n = 1 - 1/2 h_00.
        n_tensor = 1.0 - 0.5 * (h00s + hxxs)
        n_scalar = 1.0 - 0.5 * h00s
        at = pathB._deflection(n_tensor, L, b)
        as_ = pathB._deflection(n_scalar, L, b)
        rows.append({"well_depth": float(np.abs(0.5 * h00s).max()), "ratio": float(at / as_)})
    out["convergence"] = rows
    out["evolved_field_ratio"] = rows[-1]["ratio"]
    out["h00_contribution"] = float(np.min(0.5 * h00))
    out["hxx_contribution"] = float(np.min(0.5 * hxx))

    # cross-check against the FIXED harness convention (spin2/pathB), weak field
    pb = pathB.b2_light_bending()
    out["pathB_ratio"] = pb["ratio_weakfield"]

    out["pass"] = bool(abs(out["evolved_field_ratio"] - 2.0) < 0.05)
    return out


# ======================================================================
#  runner plug-in interface  (mirrors rulespace_gpu.campaign.sweep)
# ======================================================================
# parameter-vector columns for a batch row:
PARAM_NAMES = ["cg2", "gamma", "G", "tr_sign", "sigma"]
DEFAULT_PARAMS = np.array([0.25, 0.06, 1.0, 1.0, 3.5])


def evaluate_tensor_rule(params_batch, quick=True):
    """Batch evaluation of tensor-QCA rules against the fixed 3-judge harness.

    Mirrors campaign.sweep(couplings) -> dict of per-rule score arrays.

    params_batch : (Bn, 5) host array, columns = PARAM_NAMES
                   [cg2, gamma(Newton relax), G, tr_sign(trace-reversal), sigma].
    quick=True    : smaller lattices (fast single-rule dev; still fp64-exact).

    Returns dict of length-Bn arrays:
        passes        (bool)  -- all three judges pass
        tt_dof        (int)   -- number of propagating gauge-invariant DOF (target 2)
        tt_speed      (float) -- TT packet speed / c            (target 1)
        newton_ratio  (float) -- evolved h_00 / phi             (target 2)
        deflection    (float) -- evolved tensor/scalar bending  (target 2)
        gauge_resid   (float) -- discrete diffeomorphism-invariance residual (target 0)
        fact1/2/3     (bool)  -- per-judge pass flags
        poisson_resid (float) -- Newton relaxation convergence residual

    NOTE ON BATCHING (not yet GPU-batched):  this is a correct-interface,
    single-rule-in-a-loop reference.  To drop into campaign_runner it needs:
      * the leapfrog time loops (judge_fact1/2 evolution) rewritten with a
        leading batch axis and B.jit-compiled (as campaign._step_lean is), so
        all Bn rules share one compiled graph -- the judges are already pure and
        roll/clip-only, so this is mechanical;
      * the FFT reference phi and the small 4D gauge certificate stay on host
        (cheap, rule-independent -- compute once, broadcast);
      * fp64 (numpy) for the acceptance ratios; MLX fp32 only for coarse
        pre-screening of stability.
      * MLX GOTCHA #1 (high-risk when batching): the per-rule scalars pulled
        from `params_batch` (cg2, gamma, G, ...) are numpy float64. A
        numpy-scalar * MLX-array product (e.g. `ETA[a,b] * h_device`, `cg2 * lap`)
        silently coerces the whole expression back to a host ndarray. When
        porting to MLX, reshape those scalars to a (Bn,1,...) DEVICE array first,
        or wrap in float() only if truly scalar -- never leave a numpy scalar on
        the left of an MLX array.
    """
    P = np.atleast_2d(np.asarray(params_batch, dtype=float))
    Bn = P.shape[0]
    keys = ["passes", "tt_dof", "tt_speed", "newton_ratio", "deflection",
            "gauge_resid", "fact1", "fact2", "fact3", "poisson_resid"]
    res = {k: [] for k in keys}

    # gauge certificate is rule-independent -> compute once
    cert = gauge_certificate(N=6)
    gauge_ok = cert["exact_gauge_invariance"] and cert["gauge_modes_are_null"]

    for row in P:
        cg2, gamma, G, tr_sign, sigma = row
        Nz = 128 if quick else 192
        # Newton lattice stays at 40: the 1/r-dilution diagnostic's corr>0.99
        # threshold needs it (the physics RATIOS are exact even smaller).
        L = 40
        f1 = judge_fact1(Nz=Nz, cg2=cg2)
        f2 = judge_fact2(L=L, sigma=sigma, G=G, cg2=cg2, gamma=gamma, tr_sign=tr_sign)
        f3 = judge_fact3(f2, L=L, sigma=sigma, G=G)
        passes = f1["pass"] and f2["pass"] and f3["pass"] and gauge_ok
        res["passes"].append(passes)
        res["tt_dof"].append(f1["n_propagating_dof"])
        res["tt_speed"].append(f1["tt_packet_speed_over_c"])
        res["newton_ratio"].append(f2["h00_over_phi"])
        res["deflection"].append(f3["evolved_field_ratio"])
        res["gauge_resid"].append(cert["diffeo_invariance_residual"])
        res["fact1"].append(f1["pass"]); res["fact2"].append(f2["pass"]); res["fact3"].append(f3["pass"])
        res["poisson_resid"].append(f2["poisson_residual"])
    return {k: np.array(v) for k, v in res.items()}


# ======================================================================
#  driver
# ======================================================================
def run_all():
    cert = gauge_certificate(N=8)
    f1 = judge_fact1()
    f2 = judge_fact2()
    f3 = judge_fact3(f2)
    # drop the private slices before serializing
    f2_clean = {k: v for k, v in f2.items() if not k.startswith("_")}
    return {"backend": B.NAME, "gauge_certificate": cert,
            "judge1_two_polarizations": f1,
            "judge2_newtonian": f2_clean,
            "judge3_deflection": f3}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "data", "results", "tensor_qca_results.json"))
    args = ap.parse_args()

    print(f"backend = {B.NAME}   device = {B.device_info()}")
    print("TENSOR-QCA candidate: leapfrog on 10 h_munu comps + DISCRETE "
          "DIFFEOMORPHISM operator\n")

    res = run_all()
    cert = res["gauge_certificate"]
    f1, f2, f3 = res["judge1_two_polarizations"], res["judge2_newtonian"], res["judge3_deflection"]

    print("[GAUGE CERTIFICATE] discrete linearized diffeomorphism invariance")
    print(f"    max|E[h + D.xi + D.xi] - E[h]| = {cert['diffeo_invariance_residual']:.3e}  "
          f"(rel {cert['diffeo_invariance_relative']:.3e})  -> exact: {cert['exact_gauge_invariance']}")
    print(f"    max|E[pure gauge]|             = {cert['pure_gauge_null_residual']:.3e}  "
          f"-> gauge modes are null: {cert['gauge_modes_are_null']}")
    print("    (this is the discrete mechanism that leaves Fierz-Pauli's 2 DOF)\n")

    print("[JUDGE 1] two propagating TT polarizations at speed c")
    print(f"    TT-projector rank per k: {f1['tt_ranks']} -> all==2: {f1['tt_rank_all_2']}")
    print(f"    gauge-invariant DOF that propagate = {f1['n_propagating_dof']} (target 2)")
    for name, frac in f1["polarization_tt_fraction"].items():
        c2 = f1["polarization_dedonder_C2"][name]
        tag = "TT/physical" if frac > 0.5 else "gauge (no TT energy)"
        print(f"        {name:20s} TT-frac={frac:6.3f}  deDonder C^2={c2:9.3e}  {tag}")
    print(f"    TT packet speed v/c = {f1['tt_packet_speed_over_c']:.4f} "
          f"(lattice dispersion predicts {f1['tt_speed_lattice_theory_over_c']:.4f})")
    print(f"    causal leak = {f1['causal_leak_fraction']:.2e}")
    print(f"    -> {'PASS' if f1['pass'] else 'FAIL'}\n")

    print("[JUDGE 2] Newtonian limit (DYNAMICALLY evolved to the rule's fixed point)")
    print(f"    relax steps = {f2['relax_steps']}, Poisson residual = {f2['poisson_residual']:.2e}")
    print(f"    h-bar_00 / phi = {f2['hbar00_over_phi']:.4f} (target 4)")
    print(f"    h_00     / phi = {f2['h00_over_phi']:.4f} (target 2  <- trace reversal)")
    print(f"    h_xx     / phi = {f2['hxx_over_phi']:.4f} (target 2  <- space curvature)")
    print(f"    3D 1/r dilution fit corr = {f2['invr_fit_corr']:.4f}")
    print(f"    -> {'PASS' if f2['pass'] else 'FAIL'}\n")

    print("[JUDGE 3] light deflection factor 2 (Eddington), from the evolved metric")
    print(f"    evolved-field tensor/scalar ratio = {f3['evolved_field_ratio']:.4f} (target 2.000)")
    print(f"    (h00 well depth {f3['h00_contribution']:.3e}, hxx well depth {f3['hxx_contribution']:.3e})")
    print(f"    pathB fixed-harness cross-check ratio = {f3['pathB_ratio']:.4f}")
    print(f"    -> {'PASS' if f3['pass'] else 'FAIL'}\n")

    gauge_ok = cert["exact_gauge_invariance"] and cert["gauge_modes_are_null"]
    all_pass = f1["pass"] and f2["pass"] and f3["pass"] and gauge_ok
    print("=" * 66)
    print("ALL JUDGES PASS" if all_pass else "SOME JUDGES FAILED")
    print("=" * 66)
    print("\nHONEST SCOPE: the NEW content vs spin2_evolver is the exact discrete")
    print("diffeomorphism operator + gauge-null certificate (why 2 DOF, at the")
    print("operator level) and a dynamically-evolved Newtonian/lensing test. The")
    print("evolution itself is still a harmonic-gauge leapfrog, NOT a multi-")
    print("component WALKER with a tensor coin. That walker realization -- a")
    print("Dirac-style QCA whose continuum limit IS Fierz-Pauli -- remains OPEN.")

    res["all_pass"] = bool(all_pass)
    with open(args.json, "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {os.path.abspath(args.json)}")
