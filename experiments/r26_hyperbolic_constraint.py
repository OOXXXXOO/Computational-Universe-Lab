"""R26-E1: REAL-SPACE hyperbolicization of the constraint-violation sector.

Lane B second wave. This is the ONLY exit from obstacle #2's no-go: long-wave
constraint violation cannot be cleared IN PLACE (sigma_min(K) ~ k^2 => in-place
gap ~ k^4, and the slow mode limits to the protected Newton omega=0 core; even
the exact global inverse only lifts to k^2 -> 0; see 小报告-R25-预条件化收缩).
The fix (裁定 A, reframed): DO NOT clear the violation in place -- TRANSPORT it
out.  Give the constraint-violation field zeta its own auxiliary momentum pi_zeta
(a symplectic pair) sharing the geometry light cone c = cos(pi/3); the violation
then propagates at c (k-INDEPENDENT transport, not k^2 diffusion) and is absorbed
by the ALREADY-PLANNED L4 sponge (reused verbatim from tensor_coin_feedback
._sponge_field).  Blueprint = the L3->(h,pi) hyperbolic upgrade replicated at the
constraint layer.

FROZEN, READ-ONLY imports (not modified here):
  r25_realspace_step  -- frozen R25 physical step, K_apply/K_adjoint (adjoint
                         bridge), aw_op, MU.  The PHYSICAL (h,pi) block is left
                         bit-for-bit untouched.
  r25_dynamic_symbol  -- the ACTUAL covariantly-deformed K_state(k) (the real
                         Wilson-mixed constraint, NOT a clean ideal-shell K) and
                         damped_map(k,MU) = the frozen physical map; unit_census.
  r15_walk_dedonder   -- C_CONE = cos(pi/3) = 0.5, the shared cone speed.
  tensor_coin_feedback._sponge_field -- the L4/B4 sponge (reused, not rebuilt).

Four certificates (fp64, numpy):
  R26-1  clearance timescale ~ L/c and k-INDEPENDENT (incl. smallest nonzero
         k=(0,1,0), obstacle #2's pathology) + NEGATIVE CONTROL: hyperbolization
         OFF (pure in-place damping) must reproduce the no-go (long wave -> 1.000).
  R26-2  BOUNDARY 1 (the interaction warning): the PHYSICAL (h,pi) block spectrum
         on the ACTUAL K_state (the covariantly-deformed one) is bit-identical
         under the augmentation; Newton omega=0 zero mode + TT + J5 protected.
  R26-3  kappa stable window is k-INDEPENDENT.
  R26-4  sponge reflection coefficient < 1e-3 (outgoing-packet round-trip vs
         torus control) + bulk energy accounting.
Plus: adjoint bridge (enforce == measure) preserved for the leak injection.

Run:  .venv/bin/python experiments/r26_hyperbolic_constraint.py
Scope: real-space construction of the violation-clearance mechanism ONLY. This
does NOT close obstacle #2 (in-place no-go stays a registered fact); it does NOT
declare M3 or close any axis.  R26 (violation clearance) and L3-v3 (K co-
deformation) are ORTHOGONAL and must merge at obstacle #4's joint verification
(R26-2 already re-certifies on the co-deformed K, per the裁定 boundary).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (DIR, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import r25_realspace_step as RS          # FROZEN physical step + adjoint bridge
import r25_dynamic_symbol as D1          # ACTUAL K_state + frozen physical map
import r15_walk_dedonder as r15          # C_CONE
from rulespace_gpu import tensor_coin_feedback as tcf   # L4 sponge (reused)

OUT = os.path.join(ROOT, "data", "results", "r26_hyperbolic_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "r26_hyperbolic_constraint.png")

C_CONE = float(r15.C_CONE)               # 0.5, geometry light cone = cos(pi/3)
C2 = C_CONE * C_CONE                     # 0.25
MU = float(RS.MU)
NC = 8                                   # 8 constraint-violation channels (=K rows)
SEED = 260724

_RESULT = {"register": "R26-E1-hyperbolic-constraint-realspace"}


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _dump():
    _RESULT["source_sha256"] = sha256(__file__)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(_RESULT, fh, ensure_ascii=False, indent=2, default=float)


# ===========================================================================
#  PART A. real-space constraint-violation sector (pure, integer-roll, local)
#          Blueprint: the geometry leapfrog (aw stiffness) copied at the
#          constraint layer, sharing the cone speed c.
# ===========================================================================
def _neg_lap(f):
    """discrete -Laplacian, pure integer rolls, radius 1, self-adjoint:
    symbol = sum_i (2 - 2 cos k_i) = 4 sum_i sin^2(k_i/2)."""
    out = 6.0 * f if f.ndim >= 3 else 2.0 * f * f.ndim
    for ax in (-3, -2, -1):
        out = out - np.roll(f, 1, axis=ax) - np.roll(f, -1, axis=ax)
    return out


def stiffness(zeta):
    """S = c^2 * (-Lap) zeta -- gives the SHARED cone speed c (symbol c^2*|k|^2
    at small k; max symbol c^2*4*3 = 3 < 4 => leapfrog stable at every k)."""
    return C2 * _neg_lap(zeta)


def hyper_step(zeta, pzeta, kappa, sp=None, drive=None):
    """One leapfrog macro-step of the HYPERBOLIC constraint sector.  (zeta,pzeta)
    is a symplectic pair; kappa is the k-independent damping mass; sp is the L4
    sponge field (reused from tcf._sponge_field).  Pure function.
        pi_zeta' = (1-kappa) pi_zeta - S(zeta) [+ drive]
        zeta'    = zeta + pi_zeta'
        sponge   : zeta' -= sp * pi_zeta'   (L4 outgoing-wave absorber, verbatim
                   green_one pattern: subtract sp * outgoing-velocity), then keep
                   the symplectic pair consistent."""
    pzn = (1.0 - kappa) * pzeta - stiffness(zeta)
    if drive is not None:
        pzn = pzn + drive
    zn = zeta + pzn
    if sp is not None:
        zn = zn - sp * pzn                       # L4 sponge (reused)
        pzn = zn - zeta                           # keep leapfrog pair consistent
    return zn, pzn


def diffusion_step(zeta, gamma=0.08):
    """NEGATIVE CONTROL: hyperbolization OFF -> pure in-place damping = the heat
    equation for the violation (obstacle #2's in-place mechanism).  k=0 sink=0,
    so long waves are NOT cleared.  gamma <= 1/6 keeps the 3D scheme stable
    (max symbol of -Lap is 12)."""
    return zeta - gamma * _neg_lap(zeta)


# ===========================================================================
#  helpers: seeds, bulk norm
# ===========================================================================
def _carrier(shape, kvec):
    N = shape[-1]
    grids = np.meshgrid(*[np.arange(N)] * 3, indexing="ij")
    ph = sum(kvec[i] * grids[i] for i in range(3))
    return np.exp(1j * ph)


def _envelope(N, w, ctr=None):
    if ctr is None:
        ctr = N / 2.0
    x = np.arange(N)
    g = np.exp(-((x - ctr) / w) ** 2)
    return g[:, None, None] * g[None, :, None] * g[None, None, :]


def _seed(N, kvec, w):
    """8-channel violation packet: smooth envelope * carrier e^{i k.x}."""
    env = _envelope(N, w)
    z = (env * _carrier((N, N, N), kvec))[None] * np.ones((NC, 1, 1, 1))
    return z.astype(complex)


def _bulk_mass(z, pad):
    b = (slice(pad, -pad),) * 3
    return float(np.abs(z[(slice(None),) + b]).sum())


# ===========================================================================
#  R26-1. clearance timescale ~ L/c, k-INDEPENDENT + negative control
# ===========================================================================
def cert_R26_1(N=44, T=600, w=6.0, kappa=0.02, sp_w=10, sp_max=0.30, gamma=0.08):
    sp = tcf._sponge_field(N, sp_w, sp_max)
    pad = sp_w + 2
    thresh = 0.05                                     # "cleared" = <5% retained
    # k-list in units of 2pi/N; (0,1,0) is obstacle #2's smallest-nonzero病灶.
    kunits = [(0, 1, 0), (0, 2, 0), (1, 1, 0), (2, 2, 0), (2, 2, 2), (4, 4, 4)]
    rows = []
    for ku in kunits:
        kvec = 2 * np.pi * np.array(ku, float) / N
        z0 = _seed(N, kvec, w)
        m0 = _bulk_mass(z0, pad)
        # (i) HYPERBOLIC + sponge : transport out + absorb
        z, pz = z0.copy(), np.zeros_like(z0)
        tau_h, ret_h = None, None
        for t in range(1, T + 1):
            z, pz = hyper_step(z, pz, kappa, sp=sp)
            r = _bulk_mass(z, pad) / m0
            if tau_h is None and r < thresh:
                tau_h = t
            if t == T:
                ret_h = r
        # (ii) DIFFUSION (in-place, hyperbolization OFF) : the no-go mechanism.
        #      in-place clearance time ~ 1/(gamma k^2) DIVERGES as k->0.
        z = z0.copy()
        tau_d, ret_d = None, None
        for t in range(1, T + 1):
            z = diffusion_step(z, gamma)
            r = _bulk_mass(z, pad) / m0
            if tau_d is None and r < thresh:
                tau_d = t
            if t == T:
                ret_d = r
        rows.append({"k_units": list(ku),
                     "hyp_tau_clear": tau_h, "hyp_retained_T": ret_h,
                     "diff_tau_clear": tau_d, "diff_retained_T": ret_d})

    # group-speed witness (shared cone), registered B1 method: one-way traveling
    # packet COM speed along +y on a large box (single channel; the 8 channels
    # evolve diagonally).  zm = z0 exp(-i k c) is the previous leapfrog slice.
    Ng, kg, wg = 120, 0.6, 13.0
    xg = np.arange(Ng)
    envg = np.exp(-((xg - Ng / 2) / wg) ** 2)
    e3 = envg[None, :, None] * envg[:, None, None] * envg[None, None, :]
    z0 = (e3 * np.exp(1j * kg * xg)[None, :, None]).astype(complex)[None]
    zm = z0 * np.exp(-1j * kg * C_CONE)               # previous slice
    z, pz = z0.copy(), z0 - zm
    coms = []
    for t in range(70):
        z, pz = hyper_step(z, pz, kappa=0.0)          # no damping for clean COM
        m = np.abs(z[0]) ** 2
        my = m.sum(axis=(0, 2))
        coms.append(float((my * xg).sum() / my.sum()))
    vg = abs(float(np.polyfit(np.arange(25, 65), coms[25:65], 1)[0]))
    vg_predicted = (C_CONE * math.cos(kg / 2)
                    / math.sqrt(1 - C2 * math.sin(kg / 2) ** 2))

    # A2 no-go replica (registered signature): a REAL long-wave Gaussian under
    # in-place diffusion is EXACTLY conserved (k=0 sink=0) -> WHOLE-DOMAIN
    # retained ~ 1.000 (positivity + conservation); it is never cleared.
    env = _envelope(N, 12.0)[None] * np.ones((NC, 1, 1, 1))
    m0 = float(np.abs(env).sum())
    z = env.astype(complex).copy()
    for _ in range(T):
        z = diffusion_step(z, gamma)
    a2_diffusion_retained = float(np.abs(z).sum()) / m0

    tau_h_list = [r["hyp_tau_clear"] for r in rows if r["hyp_tau_clear"]]
    tau_h_spread = (max(tau_h_list) / min(tau_h_list)) if tau_h_list else None
    small = rows[0]                                    # k=(0,1,0), the病灶
    out = {
        "N": N, "T": T, "c": C_CONE, "L_over_c": N / C_CONE,
        "kappa": kappa, "gamma_diffusion": gamma,
        "sponge_w": sp_w, "sponge_max": sp_max,
        "per_k": rows,
        "hyp_tau_all_cleared": all(r["hyp_tau_clear"] is not None for r in rows),
        "hyp_tau_min": min(tau_h_list) if tau_h_list else None,
        "hyp_tau_max": max(tau_h_list) if tau_h_list else None,
        "hyp_tau_spread_ratio": tau_h_spread,
        "half_box_over_c_steps": (N / 2.0) / C_CONE,
        "smallest_k_hyp_tau": small["hyp_tau_clear"],
        "smallest_k_hyp_retained": small["hyp_retained_T"],
        "smallest_k_diffusion_tau": small["diff_tau_clear"],
        "smallest_k_diffusion_retained": small["diff_retained_T"],
        "group_speed_witness": vg, "group_speed_predicted": vg_predicted,
        "group_speed_target_c": C_CONE,
        "A2_real_gaussian_diffusion_retained": a2_diffusion_retained,
    }
    _RESULT["R26_1_clearance_timescale"] = out
    _dump()
    return out


# ===========================================================================
#  R26-2. BOUNDARY 1: physical (h,pi) block bit-identical on the ACTUAL K_state
# ===========================================================================
def _viol_block_symbol(kvec, kappa):
    """violation leapfrog symbol on (zeta,pzeta) at momentum k, 16x16 =
    2x2 leapfrog (x) I_8.  Order: [zeta(8), pzeta(8)]."""
    s = C2 * 4.0 * sum(math.sin(kvec[i] / 2) ** 2 for i in range(3))
    # pzeta' = (1-kappa)pzeta - s zeta ; zeta' = zeta + pzeta' = (1-s)zeta+(1-kappa)pzeta
    two = np.array([[1.0 - s, 1.0 - kappa],
                    [-s, 1.0 - kappa]])
    return np.kron(two, np.eye(NC)), s


def cert_R26_2(Nbz=12, kappa=0.02, leak=0.3):
    """Augment the ACTUAL frozen physical map (28x28, covariantly-deformed
    K_state) with the violation sector, coupled ONE-WAY (physical -> violation
    leak via the real K_state).  Block-LOWER-triangular => physical eigenvalues
    bit-identical.  Certified on the REAL K_state, not a clean K (the裁定
    boundary-1 requirement)."""
    rng = np.random.default_rng(SEED)
    ks = [(0, 1, 0), (0, 2, 0), (1, 1, 0), (2, 2, 2)]     # incl. smallest-k病灶
    ks = [2 * np.pi * np.array(k, float) / Nbz for k in ks]
    # add a BZ sweep
    for idx in np.ndindex(Nbz, Nbz, Nbz):
        if idx == (0, 0, 0):
            continue
        ks.append(2 * np.pi * np.array(idx, float) / Nbz)

    worst_phys = 0.0
    worst_idx = None
    unit_ok = True
    unit_phys_ref = None
    worst_viol_dev = 0.0
    n = 0
    for kvec in ks:
        Mphys = D1.damped_map(kvec, MU)[0]                 # 28x28 ACTUAL map
        Ks = D1.K_state(kvec)                               # 8x28 ACTUAL K_state
        Mviol, s = _viol_block_symbol(kvec, kappa)         # 16x16
        # leak: physical(28) -> pzeta(8) via the real K_state (into rows 8..15).
        Lk = np.zeros((16, 28), complex)
        Lk[NC:2 * NC, :] = leak * Ks
        Maug = np.zeros((44, 44), complex)
        Maug[:28, :28] = Mphys
        Maug[28:, 28:] = Mviol
        Maug[28:, :28] = Lk                                # lower-triangular
        ev_p = np.sort_complex(np.linalg.eigvals(Mphys))
        ev_a = np.sort_complex(np.linalg.eigvals(Maug))
        # the 28 physical eigenvalues must appear in the augmented spectrum
        used = np.zeros(44, bool)
        dmax = 0.0
        for lam in ev_p:
            d = np.abs(ev_a - lam) + (used * 1e9)
            j = int(np.argmin(d))
            used[j] = True
            dmax = max(dmax, float(d[j]))
        if dmax > worst_phys:
            worst_phys, worst_idx = dmax, [float(x) for x in kvec]
        # 12 unit modes preserved in the physical block
        up, _, _ = D1.unit_census(ev_p)
        if unit_phys_ref is None:
            unit_phys_ref = up
        unit_ok = unit_ok and (up == 12)
        # violation eigenvalues are the leapfrog ones (k-independent damping det)
        det = (1 - kappa)
        prod = abs(complex(np.prod(np.linalg.eigvals(Mviol)))) ** (1.0 / NC)
        worst_viol_dev = max(worst_viol_dev, abs(prod - det))
        n += 1
    out = {"Nbz": Nbz, "n_k": n, "kappa": kappa, "leak": leak,
           "physical_block_worst_dev": worst_phys,
           "physical_block_worst_k": worst_idx,
           "twelve_unit_modes_preserved": bool(unit_ok),
           "unit_count_physical": unit_phys_ref,
           "violation_det_matches_1_minus_kappa": worst_viol_dev,
           "structure": "block-lower-triangular (physical->violation one-way); "
                        "physical spectrum exactly the frozen covariantly-deformed map"}
    _RESULT["R26_2_physical_block_unchanged"] = out
    _dump()
    return out


# ===========================================================================
#  R26-3. kappa stable window is k-INDEPENDENT
# ===========================================================================
def cert_R26_3(Nbz=14):
    kappas = np.linspace(0.0, 2.2, 45)
    # k-sets: (a) smallest nonzero only, (b) full BZ
    small = [2 * np.pi * np.array((0, 1, 0), float) / Nbz]
    full = []
    for idx in np.ndindex(Nbz, Nbz, Nbz):
        if idx == (0, 0, 0):
            continue
        full.append(2 * np.pi * np.array(idx, float) / Nbz)

    def max_rho(kset, kap):
        r = 0.0
        for kvec in kset:
            M, _ = _viol_block_symbol(kvec, kap)
            r = max(r, float(np.max(np.abs(np.linalg.eigvals(M)))))
        return r

    rows = []
    for kap in kappas:
        rs = max_rho(small, kap)
        rf = max_rho(full, kap)
        rows.append({"kappa": float(kap), "max_rho_small_k": rs,
                     "max_rho_full_bz": rf})
    # A single kappa is stable across the ENTIRE BZ (a COMMON, k-independent
    # working window).  The full-BZ upper edge is the high-k CFL bound
    # (kappa <= 2 - s/2, s(k) the stiffness symbol) -- expected, and it is the
    # SAME bound seen from small k once s is large; what matters for beating the
    # no-go is that a common window exists and the CONTRACTION RATE in it is
    # k-independent.
    tol = 1e-9
    stable_full = [r["kappa"] for r in rows if r["max_rho_full_bz"] <= 1 + tol]
    stable_small = [r["kappa"] for r in rows if r["max_rho_small_k"] <= 1 + tol]
    win_full = (min(stable_full), max(stable_full)) if stable_full else (None, None)
    win_small = (min(stable_small), max(stable_small)) if stable_small else (None, None)
    common_window_nonempty = bool(stable_full)
    # contraction rate at a working kappa is sqrt(1-kappa) for underdamped modes,
    # IDENTICAL across k (the crux: in-place gives rate 1-O(k^4)->1 as k->0).
    kap_work = 0.02
    rates = []
    for kvec in [small[0]] + full[::37]:
        M, _ = _viol_block_symbol(kvec, kap_work)
        eig = np.linalg.eigvals(M)
        # slowest UNDERDAMPED (complex) mode = the transported violation
        comp = eig[np.abs(eig.imag) > 1e-9]
        if comp.size:
            rates.append(float(np.max(np.abs(comp))))
    rate_spread = (max(rates) - min(rates)) if rates else None
    out = {"Nbz": Nbz, "sweep": rows,
           "common_stable_window_full_bz": list(win_full),
           "stable_window_small_k_only": list(win_small),
           "common_window_nonempty": common_window_nonempty,
           "kappa_work": kap_work,
           "contraction_rate_sqrt_1_minus_kappa": math.sqrt(1 - kap_work),
           "underdamped_rate_spread_over_k": rate_spread,
           "rate_k_independent": rate_spread is not None and rate_spread < 1e-9,
           "note": "underdamped violation rate = sqrt(1-kappa), k-INDEPENDENT "
                   "(contrast obstacle #2 in-place rate 1-O(k^4) -> 1 as k->0). "
                   "full-BZ upper edge = high-k CFL bound kappa<=2-s/2, expected."}
    _RESULT["R26_3_kappa_window_k_independent"] = out
    _dump()
    return out


# ===========================================================================
#  R26-4. sponge reflection < 1e-3 + bulk energy accounting
# ===========================================================================
def cert_R26_4(N=80, sp_w=30, sp_max=0.25, w=4.0, nper=10.0):
    """Launch an outgoing violation packet toward the +y edge; compare the bulk
    energy that RETURNS after the packet has exited WITH the L4 sponge vs a torus
    (no-sponge) control that wraps the packet back.  Reflection R = returned-
    bulk-energy / incident.  Single channel: the 8 channels evolve diagonally, so
    a scalar proxy is exact per-channel."""
    sp = tcf._sponge_field(N, sp_w, sp_max)
    pad = sp_w + 3
    ky = 2 * np.pi * nper / N
    s_sym = C2 * (2 - 2 * math.cos(ky))
    omega = math.acos(max(-1.0, min(1.0, 1.0 - s_sym / 2.0)))
    x = np.arange(N)
    env = np.exp(-((x - N / 2) / w) ** 2)
    z0 = (env[None, :, None] * env[:, None, None] * env[None, None, :]
          ).astype(complex) * np.exp(1j * ky * x)[None, :, None]
    z0 = z0[None]                                          # (1,N,N,N)
    pz0 = (np.exp(-1j * omega) - 1.0) * z0                 # +y mover

    def bulk_energy(z):
        b = (slice(pad, -pad),) * 3
        return float((np.abs(z[(slice(None),) + b]) ** 2).sum())

    e_in = bulk_energy(z0)
    Tround = int(N / C_CONE) + 60                          # allow torus wrap-back
    exit_t = int((N / 2 + 2 * w) / C_CONE) + sp_w          # packet has left bulk

    # (i) with sponge: absorbed; measure any energy that RE-enters the bulk.
    z, pz = z0.copy(), pz0.copy()
    tr = []
    for t in range(1, Tround + 1):
        z, pz = hyper_step(z, pz, kappa=0.0, sp=sp)
        tr.append(bulk_energy(z))
    R_sponge = max(tr[exit_t:]) / e_in

    # (ii) torus control (no sponge): packet wraps and returns fully
    z, pz = z0.copy(), pz0.copy()
    trt = []
    for t in range(1, Tround + 1):
        z, pz = hyper_step(z, pz, kappa=0.0, sp=None)
        trt.append(bulk_energy(z))
    R_torus = max(trt[exit_t:]) / e_in

    out = {"N": N, "sponge_w": sp_w, "sponge_max": sp_max, "carrier_periods": nper,
           "round_trip_T": Tround, "exit_step": exit_t,
           "incident_bulk_energy": e_in,
           "reflection_coeff_sponge": R_sponge,
           "reflection_coeff_torus_control": R_torus,
           "absorbed_fraction": 1.0 - R_sponge,
           "reflection_lt_1e-3": R_sponge < 1e-3}
    _RESULT["R26_4_sponge_reflection"] = out
    _dump()
    return out


# ===========================================================================
#  adjoint bridge (enforce == measure) for the leak injection -- reuse frozen
# ===========================================================================
def cert_adjoint(N=6, trials=4):
    """The violation is sourced by the physical constraint K_apply(h,pi); its
    adjoint (measure) is the frozen K_adjoint.  R20 discipline preserved."""
    rng = np.random.default_rng(SEED)
    worst = 0.0
    for _ in range(trials):
        h = rng.normal(size=(RS.NF, N, N, N)) + 1j * rng.normal(size=(RS.NF, N, N, N))
        pi = rng.normal(size=(RS.NF, N, N, N)) + 1j * rng.normal(size=(RS.NF, N, N, N))
        y = rng.normal(size=(8, N, N, N)) + 1j * rng.normal(size=(8, N, N, N))
        Kx = RS.K_apply(h, pi)
        dh, dpi = RS.K_adjoint(y)
        lhs = np.vdot(Kx, y)
        rhs = np.vdot(h, dh) + np.vdot(pi, dpi)
        worst = max(worst, abs(lhs - rhs) / max(abs(lhs), 1e-300))
    out = {"enforce_equals_measure_residual": float(worst)}
    _RESULT["adjoint_bridge"] = out
    _dump()
    return out


def coupled_step(h, pi, zeta, pzeta, kappa, sp=None, leak=0.3, drive=None):
    """OBSTACLE #4 INTERFACE: one unified macro step.  Physical (h,pi) advances
    by the FROZEN R25 step (untouched); the physical constraint violation
    K_apply(h,pi) leaks into the hyperbolic violation sector, which transports it
    at c and lets the sponge absorb it.  Wire this into obstacle #4's joint loop;
    re-certify R26-2 on whatever K_state L3-v3 co-deformation produces."""
    hn, pin = RS.step(h, pi, drive=drive)                 # frozen, unchanged
    viol = RS.K_apply(h, pi)                              # measured violation
    zn, pzn = hyper_step(zeta, pzeta, kappa, sp=sp, drive=leak * viol)
    return hn, pin, zn, pzn


# ===========================================================================
def main():
    t0 = time.time()
    print("R26-E1 : real-space hyperbolic constraint sector")
    print("=" * 66)
    print(f"c={C_CONE}  MU={MU:.6e}  channels={NC}")

    adj = cert_adjoint()
    print(f"adjoint bridge (enforce==measure): {adj['enforce_equals_measure_residual']:.2e}"
          f"  ({time.time()-t0:.1f}s)")

    r1 = cert_R26_1()
    print(f"\nR26-1 clearance ~L/c, k-independent (L/c={r1['L_over_c']:.0f}):")
    for r in r1["per_k"]:
        print(f"  k={r['k_units']}: hyp tau={r['hyp_tau_clear']} ret={r['hyp_retained_T']:.2e}"
              f" | diff tau={r['diff_tau_clear']} ret={r['diff_retained_T']:.3f}")
    print(f"  hyp tau spread ratio={r1['hyp_tau_spread_ratio']:.2f}; smallest-k(病灶): "
          f"hyp tau={r1['smallest_k_hyp_tau']} vs diff tau={r1['smallest_k_diffusion_tau']}")
    print(f"  group speed={r1['group_speed_witness']:.3f} (pred {r1['group_speed_predicted']:.3f}, c={C_CONE})")
    print(f"  A2 no-go replica (real long-wave, diffusion): retained="
          f"{r1['A2_real_gaussian_diffusion_retained']:.4f}  ({time.time()-t0:.1f}s)")

    r2 = cert_R26_2()
    print(f"\nR26-2 physical block on ACTUAL K_state: worst dev={r2['physical_block_worst_dev']:.2e}"
          f" 12-unit-modes={r2['twelve_unit_modes_preserved']}  ({time.time()-t0:.1f}s)")

    r3 = cert_R26_3()
    print(f"\nR26-3 common stable window full-BZ={r3['common_stable_window_full_bz']} "
          f"nonempty={r3['common_window_nonempty']} rate k-indep={r3['rate_k_independent']}"
          f" (spread={r3['underdamped_rate_spread_over_k']:.2e})  ({time.time()-t0:.1f}s)")

    r4 = cert_R26_4()
    print(f"\nR26-4 sponge reflection={r4['reflection_coeff_sponge']:.2e} "
          f"(torus control={r4['reflection_coeff_torus_control']:.3f}) "
          f"absorbed={r4['absorbed_fraction']:.5f}  ({time.time()-t0:.1f}s)")

    checks = {
        "adjoint_enforce_equals_measure_lt_1e-13":
            adj["enforce_equals_measure_residual"] < 1e-13,
        "R26_1_hyp_all_k_cleared_finite_tau": r1["hyp_tau_all_cleared"],
        "R26_1_hyp_tau_bounded_spread_lt_3x":
            r1["hyp_tau_spread_ratio"] is not None and r1["hyp_tau_spread_ratio"] < 3.0,
        "R26_1_smallest_k_hyp_tau_le_3_L_over_c":
            r1["smallest_k_hyp_tau"] is not None
            and r1["smallest_k_hyp_tau"] <= 3.0 * r1["L_over_c"],
        "R26_1_negctrl_smallest_k_diffusion_NOT_cleared":
            r1["smallest_k_diffusion_tau"] is None,     # no-go reproduced
        "R26_1_negctrl_A2_diffusion_retains_long_wave":
            r1["A2_real_gaussian_diffusion_retained"] > 0.99,
        "R26_1_group_speed_near_c":
            abs(r1["group_speed_witness"] - C_CONE) < 0.08,
        "R26_2_physical_block_dev_lt_1e-13":
            r2["physical_block_worst_dev"] < 1e-13,
        "R26_2_twelve_unit_modes_preserved": r2["twelve_unit_modes_preserved"],
        "R26_3_common_window_nonempty": r3["common_window_nonempty"],
        "R26_3_underdamped_rate_k_independent": r3["rate_k_independent"],
        "R26_4_sponge_reflection_lt_1e-3": r4["reflection_coeff_sponge"] < 1e-3,
    }
    _RESULT["checks"] = checks
    _RESULT["status"] = "PASS" if all(checks.values()) else "FAIL"
    _RESULT["frozen_inputs_sha256"] = {
        "r25_realspace_step.py": sha256(os.path.join(DIR, "r25_realspace_step.py")),
        "r25_dynamic_symbol.py": sha256(os.path.join(DIR, "r25_dynamic_symbol.py")),
    }
    _RESULT["scope_boundary"] = (
        "Real-space construction of the violation-clearance mechanism ONLY. "
        "Does NOT close obstacle #2 (in-place no-go remains a registered fact); "
        "does NOT declare M3 or close any axis. R26 (violation clearance) and "
        "L3-v3 (K covariant deformation) are ORTHOGONAL; R26-2 re-certifies on "
        "the covariantly-deformed K, and the two axes merge at obstacle #4's "
        "joint verification.")
    _RESULT["obstacle4_interface"] = (
        "coupled_step(h,pi,zeta,pzeta,kappa,sp,leak): physical step FROZEN, "
        "physical constraint K_apply(h,pi) leaks into the hyperbolic violation "
        "sector; re-run cert_R26_2 on the co-deformed K_state at joint verify.")
    _dump()

    # figure
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 2, figsize=(11, 8))
        ku = [str(r["k_units"]) for r in r1["per_k"]]
        th = [r["hyp_tau_clear"] for r in r1["per_k"]]
        rd = [r["diff_retained_T"] for r in r1["per_k"]]
        ax[0, 0].bar(range(len(ku)), th, color="tab:green")
        ax[0, 0].axhline(r1["half_box_over_c_steps"], ls="--", color="k",
                         label="L/2c")
        ax[0, 0].set_xticks(range(len(ku)))
        ax[0, 0].set_xticklabels(ku, rotation=45, fontsize=7)
        ax[0, 0].set_title("R26-1 hyperbolic clearance time (k-independent ~L/c)")
        ax[0, 0].legend()
        ax[0, 1].bar(range(len(ku)), rd, color="tab:red")
        ax[0, 1].axhline(1.0, ls="--", color="k")
        ax[0, 1].set_xticks(range(len(ku)))
        ax[0, 1].set_xticklabels(ku, rotation=45, fontsize=7)
        ax[0, 1].set_title("negative control: in-place diffusion retained (->1 small k)")
        kap = [r["kappa"] for r in r3["sweep"]]
        ax[1, 0].plot(kap, [r["max_rho_full_bz"] for r in r3["sweep"]],
                      label="full BZ")
        ax[1, 0].plot(kap, [r["max_rho_small_k"] for r in r3["sweep"]], "--",
                      label="small k")
        ax[1, 0].axhline(1.0, ls=":", color="k")
        ax[1, 0].set_xlabel("kappa"); ax[1, 0].set_title("R26-3 stable window (k-indep)")
        ax[1, 0].legend()
        ax[1, 1].bar([0, 1], [r4["reflection_coeff_sponge"],
                              r4["reflection_coeff_torus_control"]],
                     color=["tab:green", "tab:gray"])
        ax[1, 1].set_yscale("log")
        ax[1, 1].axhline(1e-3, ls="--", color="k", label="1e-3")
        ax[1, 1].set_xticks([0, 1])
        ax[1, 1].set_xticklabels(["sponge", "torus"])
        ax[1, 1].set_title("R26-4 sponge reflection")
        ax[1, 1].legend()
        fig.tight_layout()
        fig.savefig(FIG, dpi=110)
        _RESULT["figure"] = FIG
        _dump()
        print("wrote", FIG)
    except Exception as e:
        print("figure skipped:", e)

    print("\nstatus:", _RESULT["status"])
    print("checks:", {k: v for k, v in checks.items() if not v} or "all PASS")
    print("wrote", OUT)
    print("total %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
