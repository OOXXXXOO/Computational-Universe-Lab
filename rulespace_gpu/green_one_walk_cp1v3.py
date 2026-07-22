"""green_one_walk_cp1v3 -- M2'-CP1 (lane B), R18 focused-debug edition.

SCOPE OF THIS ROUND (per 小报告-R18 + main-loop directive): SINGLE-k, ON-SHELL
initial data, term-by-term alignment of the 3D real-space damping against the
R16 in-vitro oracle.  NOT the full generic-IC assembly (that is the next round,
gated on this alignment passing review).

WHAT CP1-v2 GOT WRONG (diagnosed this round, with data -- see the report):
  * The certified symbol operator (cp_v2._my_K_symbol, macrostep ON-SHELL time
    phase) already reproduces in-vitro EXACTLY at the amplitude level: the gate
    passes (dim ker/gauge = 2) AND e^{-iw}(I-gamma K'K) drives C -> 5e-16 with
    TT retention 1.0.  So the THEORY/OPERATOR is sound.
  * The v2 GRID dynamics floored (|C|^2 ~ 6e-4) because its TIME term used the
    MACROSTEP DIFFERENCE of two stored fields  hbar(t) - hprev(t)  with hprev =
    the PREVIOUS DAMPED field.  Once damping perturbs the mode off pure-phase
    evolution, hprev != e^{+iw} hbar, so the difference no longer realizes the
    on-shell symbol (1 - e^{-iw}); gauge then leaves ker K and the constraint
    re-injects each walk step -> a FLOOR, not a rate problem (R18 H1).
  * v2's fold-back wrote only Re(chi[...,0]) and kept the stale Im/spinor-1,
    so the walker was internally inconsistent -- a second, smaller re-injection.

THE FIX (v3):
  (1) TIME term realized by the WALK OPERATOR ITSELF, locally and history-free:
        D_0 hbar_{0nu}  <-  ( (W chi)[...,0] - chi[...,0] )_{0nu}
      whose per-mode symbol is exactly (e^{-iw}-1) = -(1 - e^{-iw}).  This is
      the split-step's own action as the t+1/2 time derivative (R16 key #1 /
      R17 sec.time), with NO lagged history and NO per-mode 1/cos.
  (2) The constraint operator K acts on the FULL complex walker chi (both spinor
      slots), and K^dag is its EXACT adjoint.  Because the geom-walk is unitary,
      W^dag = geom_walk_inv (verified |W^-1 W - I| ~ 3e-15); the time-term
      adjoint is realized by geom_walk_inv acting on a slot-0 0nu-seeded field,
      feeding BOTH slots -- so the whole walker is damped consistently (the v2
      fold-back inconsistency is gone by construction).  enforce == measure is
      then EXACT: <K chi, Y> = <chi, K^dag Y> to 1e-14.
  Damping step:  chi <- chi - gamma K^dag (K chi).  ker K = TT (+) gauge in the
  Yee frame, so TT is never touched (retention 1.0) and gauge is annihilated by
  the Riemann judge -> the damping fixed point carries Riemann only on TT.

GAMMA: the full-chi walk operator is STIFFER than R18's constant-1/c Jacobian
  estimate (the extra spinor slot adds stiffness), so its empirical stability
  ceiling is ~0.05 (body-diagonal modes blow up above it), NOT 0.0735.  We use
  gamma = 0.045 (<= 0.0735 gate, stable on every resolvable mode).  Small-|k|
  axial modes have small sigma^2_min (~0.24, same stiffness the in-vitro K has
  at small k -- r18 stiffness 256) and therefore converge slowly; body/face
  modes reach machine floor by T~2000.  This is declared calibration inside the
  stability domain, not a fit.

Run:  RULESPACE_BACKEND=numpy python -m rulespace_gpu.green_one_walk_cp1v3
      -> green_one_walk_cp1v3_results.json
"""
import argparse
import json
import math
import os

import numpy as np

from . import backend as B
from . import emergence_judge as ej
from . import green_one_walk as gw
from . import green_one_walk_cp1v2 as cp2
from . import tensor_coin_feedback as tcf

DIR = os.path.dirname(os.path.abspath(__file__))
IDX10 = ej.IDX10
PK = ej.PK
OFFSET = cp2.OFFSET
r15 = cp2.r15
r16 = cp2._load("r16_cp1_invitro")

TH0 = math.pi / 3.0
NU0 = [PK[(0, nu)] for nu in range(4)]


# ==========================================================================
#  Inverse geom-walk = exact adjoint of the (unitary) forward walk
# ==========================================================================
def _axis_sandwich_inv(psi, th, ax3, W, orient=1):
    """exact inverse of tcf._axis_sandwich (undo each step in reverse)."""
    if W is not None:
        psi = psi @ np.linalg.inv(W.conj())
    p1 = np.roll(psi[..., 1], orient, axis=ax3)
    psi = np.stack([psi[..., 0], p1], axis=-1)
    psi = tcf._coin(psi, th)
    p0 = np.roll(psi[..., 0], -orient, axis=ax3)
    psi = np.stack([p0, psi[..., 1]], axis=-1)
    psi = tcf._coin(psi, -th)
    if W is not None:
        psi = psi @ np.linalg.inv(W.T)
    return psi


def geom_walk_inv(chi, th0=TH0):
    Wx, Wy, Wz = tcf.axis_frames(th0)
    chi = _axis_sandwich_inv(chi, th0, -1, Wz, 1)
    chi = _axis_sandwich_inv(chi, th0, -2, Wy, 1)
    chi = _axis_sandwich_inv(chi, th0, -3, Wx, 1)
    return chi


def _packed(chi_slot):                  # (10,...,2? no) (10,N,N,N)->(N,N,N,10)
    return np.moveaxis(chi_slot, 0, -1)


# ==========================================================================
#  K: full walker chi -> constraint C (4 per site);  exact adjoint K^dag
#  spatial: R17 fwd/bwd dictionary on the slot-0 field;
#  time   : (W - I) via the walk operator (on-shell (e^{-iw}-1) symbol);  /c.
# ==========================================================================
def K_op(chi, c=math.cos(TH0), th0=TH0):
    f0 = _packed(chi[..., 0])
    wf0 = _packed(gw.geom_walk_all(chi.copy(), th0, th0, th0, th0)[..., 0])
    Cf = np.zeros(f0.shape[:-1] + (4,), dtype=complex)
    for nu in range(4):
        acc = np.zeros(f0.shape[:-1], dtype=complex)
        for mu in (1, 2, 3):
            comp = PK[(mu, nu)]
            acc = acc + cp2._dsp_dict(f0[..., comp], mu, comp, True)
        c0 = PK[(0, nu)]
        # time term eta^00 D_0 hbar_0nu = -(1/c)(I - W) hbar_0nu, symbol
        # -(1 - e^{-iw})/c -- MUST match _my_K_symbol exactly (which uses forward
        # difference e^{iw} - 1, equivalent to -(1 - e^{-iw})) or ker K != TT (+) gauge.
        # Implementation: compute (1/c)(f0 - Wf0) = -(1/c)(Wf0 - f0), i.e. backward diff.
        acc = acc - (1.0 / c) * (f0[..., c0] - wf0[..., c0])
        Cf[..., nu] = acc
    return Cf


def Kdag_op(Cf, c=math.cos(TH0), th0=TH0, N=None):
    """exact adjoint of K_op; returns a full-walker-shaped correction.
    Batch-aware: Cf has shape (...spatial..., 4) with optional leading batch."""
    sh = Cf.shape[:-1]                                    # (...,N,N,N)  (+ batch)
    grad = np.zeros((10,) + sh + (2,), dtype=complex)
    g0 = np.zeros(sh + (10,), dtype=complex)              # feeds slot 0
    for comp, (a, b) in enumerate(IDX10):
        if a in (1, 2, 3):
            g0[..., comp] = g0[..., comp] + cp2._dsp_dict_adj(Cf[..., b], a, comp, True)
        if a != b and b in (1, 2, 3):
            g0[..., comp] = g0[..., comp] + cp2._dsp_dict_adj(Cf[..., a], b, comp, True)
    for nu in range(4):        # adjoint of -(1/c)(I - W): local -(1/c) part
        g0[..., PK[(0, nu)]] = g0[..., PK[(0, nu)]] - (1.0 / c) * Cf[..., nu]
    grad[..., 0] = np.moveaxis(g0, -1, 0)
    Z = np.zeros((10,) + sh + (2,), dtype=complex)        # +(1/c) W^dag part
    for nu in range(4):
        Z[PK[(0, nu)], ..., 0] = (1.0 / c) * Cf[..., nu]
    grad = grad + geom_walk_inv(Z, th0)                  # W^dag -> both slots
    return grad


def adjoint_residual(N=12, seed=3):
    """enforce == measure: |<K chi, Y> - <chi, K^dag Y>| (should be ~1e-14)."""
    rng = np.random.default_rng(seed)
    chi = (rng.standard_normal((10, N, N, N, 2))
           + 1j * rng.standard_normal((10, N, N, N, 2)))
    Y = rng.standard_normal((N, N, N, 4)) + 1j * rng.standard_normal((N, N, N, 4))
    lhs = np.vdot(Y, K_op(chi))
    rhs = np.vdot(Kdag_op(Y, N=N), chi)
    return float(abs(lhs - rhs)), float(abs(lhs))


# ==========================================================================
#  The v3 rule (for the NEXT round's assembly; here we mainly use the
#  single-k on-shell driver below).
# ==========================================================================
def make_rule_cp1v3(th0=TH0, gamma=0.045, damping=True, n_iter=1):
    c = math.cos(th0)
    cache = {"last": None, "chi": None}

    def step(state):
        h = state[0]
        if cache["last"] is not h:
            cache["chi"] = gw.seed_chi(h)
        chi = gw.geom_walk_all(cache["chi"], th0, th0, th0, th0)
        if damping:
            N = chi.shape[1]
            for _ in range(n_iter):
                chi = chi - gamma * Kdag_op(K_op(chi, c, th0), c, th0, N)
        hbar = gw.chi_to_hbar(chi)
        cache["chi"] = chi
        out = (hbar, hbar)
        cache["last"] = out[0]
        return out

    return {"name": f"walk-geom CP1v3 walk-time de-Donder gamma={gamma}",
            "n_levels": 2, "cg2": c * c, "step": step}


# ==========================================================================
#  ON-SHELL single-k harness (the deliverable of this round)
# ==========================================================================
def _klat(nvec, N):
    return np.array(nvec, float) * (2 * np.pi / N)


def _walk_2x2(kvec, N, th0=TH0):
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    ph = np.exp(1j * (kvec[0] * X + kvec[1] * Y + kvec[2] * Z))
    proj = np.conj(ph) / N ** 3
    M = np.zeros((2, 2), complex)
    for s in range(2):
        c0 = np.zeros((1, N, N, N, 2), complex)
        c0[0, ..., s] = ph
        c0 = gw.geom_walk_all(c0, th0, th0, th0, th0)
        for r in range(2):
            M[r, s] = np.sum(proj * c0[0, ..., r])
    return M


def _onshell_spinor(kvec, N, th0=TH0):
    """positive-energy eigen-spinor xi_+ and quasi-energy w of the walk at k."""
    M = _walk_2x2(kvec, N, th0)
    ev, V = np.linalg.eig(M)
    w = -np.angle(ev)
    cand = [j for j in range(2) if 1e-9 < w[j] < math.pi - 1e-9]
    j = cand[int(np.argmin([w[jj] for jj in cand]))]
    return float(w[j]), V[:, j] / np.linalg.norm(V[:, j])


def _seed(nvec, a10, xi, N):
    kl = _klat(nvec, N)
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    ph = np.exp(1j * (kl[0] * X + kl[1] * Y + kl[2] * Z))
    chi = np.zeros((10, N, N, N, 2), complex)
    for c in range(10):
        chi[c] = a10[c] * ph[..., None] * xi[None, None, None, :]
    return chi


def _amp(chi, nvec, N):
    kl = _klat(nvec, N)
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    proj = np.conj(np.exp(1j * (kl[0] * X + kl[1] * Y + kl[2] * Z))) / N ** 3
    return np.array([np.sum(proj * chi[c, ..., 0]) for c in range(10)])


def _riemann_vec(kap, a10):
    """linearized Riemann tensor (256-vector) of a placed amplitude a10
    (trace-reversed to physical h first; flat eta)."""
    hp = a10.astype(complex)
    tr = (-hp[PK[(0, 0)]] + hp[PK[(1, 1)]] + hp[PK[(2, 2)]] + hp[PK[(3, 3)]])
    EF = np.diag([-1.0, 1.0, 1.0, 1.0])
    h = hp.copy()
    for kpk, (m, n) in enumerate(IDX10):
        h[kpk] = hp[kpk] - 0.5 * EF[m, n] * tr
    H = np.zeros((4, 4), complex)
    for kpk, (m, n) in enumerate(IDX10):
        H[m, n] = H[n, m] = h[kpk]
    k = np.real(kap)
    R = np.zeros((4, 4, 4, 4), complex)
    for m in range(4):
        for a in range(4):
            for n in range(4):
                for b in range(4):
                    R[m, a, n, b] = 0.5 * (k[m] * k[n] * H[a, b] + k[a] * k[b] * H[m, n]
                                           - k[m] * k[b] * H[a, n] - k[a] * k[n] * H[m, b])
    return R.reshape(256)


def invitro_oracle(nvec, N, gamma, T, th0=TH0):
    """R16 in-vitro on-shell reference: a(t+1)=e^{-iw}(I-gamma K'K)a(t)."""
    kl = _klat(nvec, N)
    w = r15.shell_omega(kl)
    kap = r15.kappa_placed(kl)
    K = r15.constraint_matrix(kap)
    TT = r15.tt_basis(kap)
    G = r15.gauge_block(kap)
    D = np.eye(10) - gamma * (K.conj().T @ K)
    rng = np.random.default_rng(7)
    a = (TT @ (rng.normal(size=2) + 1j * rng.normal(size=2))
         + G @ (rng.normal(size=4) + 1j * rng.normal(size=4))
         + 0.5 * (rng.normal(size=10) + 1j * rng.normal(size=10)))
    c0 = np.linalg.norm(K @ a)
    tt0 = np.linalg.norm(TT.conj().T @ a)
    for _ in range(T):
        a = np.exp(-1j * w) * (D @ a)
    return {"C_ratio": float(np.linalg.norm(K @ a) / (c0 + 1e-300)),
            "C_final": float(np.linalg.norm(K @ a)),
            "TT_retention": float(np.linalg.norm(TT.conj().T @ a) / (tt0 + 1e-300))}


def _seed_batch(nvec, a10_batch, xi, N):
    """a10_batch (trials,10) -> chi (10, trials, N,N,N, 2)."""
    kl = _klat(nvec, N)
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    ph = np.exp(1j * (kl[0] * X + kl[1] * Y + kl[2] * Z))
    B_ = a10_batch.shape[0]
    chi = np.zeros((10, B_, N, N, N, 2), complex)
    for c in range(10):
        amp = a10_batch[:, c][:, None, None, None]        # (B,1,1,1)
        chi[c] = amp[..., None] * ph[None, ..., None] * xi[None, None, None, None, :]
    return chi


def _amp_batch(chi, nvec, N):
    """+k amplitude per trial: chi (10,B,N,N,N,2) -> (B,10)."""
    kl = _klat(nvec, N)
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    proj = np.conj(np.exp(1j * (kl[0] * X + kl[1] * Y + kl[2] * Z))) / N ** 3
    return np.einsum("xyz,cbxyz->bc", proj, chi[..., 0])


def align_mode(nvec, N=16, gamma=0.045, T=2000, trials=8, th0=TH0):
    """single-k on-shell alignment of the v3 real-space damping vs in-vitro.
    All `trials` mixed on-shell ICs are damped in one BATCH; trial 0 is used
    for the C trajectory + TT-retention curve."""
    c = math.cos(th0)
    kl = _klat(nvec, N)
    w, xi = _onshell_spinor(kl, N, th0)
    kap = r15.kappa_placed(kl)
    TT = r15.tt_basis(kap)
    G = r15.gauge_block(kap)
    k4 = np.array([w, kl[0], kl[1], kl[2]])
    colfac = np.array([np.exp(0.5j * float(np.dot(k4, OFFSET[cc]))) for cc in range(10)])

    # Yee-frame seeds: physical modes live at colfac*(...), so colfac*TT is
    # exactly in ker(K_op) and is never damped.
    a_batch = np.zeros((trials, 10), complex)
    for r in range(trials):
        rr = np.random.default_rng(100 + r)
        a_batch[r] = colfac * (TT @ (rr.normal(size=2) + 1j * rr.normal(size=2))
                               + G @ (rr.normal(size=4) + 1j * rr.normal(size=4))
                               + 0.5 * (rr.normal(size=10) + 1j * rr.normal(size=10)))
    chi = _seed_batch(nvec, a_batch, xi, N)
    tt_of = lambda ch: np.linalg.norm(
        TT.conj().T @ (np.conj(colfac) * _amp_batch(ch, nvec, N)[0]))
    c_of = lambda ch: float(np.sqrt(np.mean(np.abs(K_op(ch, c, th0)[0]) ** 2)))
    c_norm0, tt0 = c_of(chi), tt_of(chi)
    rms0 = float(np.sqrt(np.mean(np.abs(chi[:, 0]) ** 2)))
    traj, c_min = [], np.inf
    for t in range(T):
        chi = gw.geom_walk_all(chi, th0, th0, th0, th0)
        chi = chi - gamma * Kdag_op(K_op(chi, c, th0), c, th0, N)
        if (t + 1) % max(1, T // 10) == 0 or t == T - 1:
            cc = c_of(chi)
            c_min = min(c_min, cc)
            traj.append((t + 1, cc))
    c_final = traj[-1][1]
    ttf = tt_of(chi)
    rms_final = float(np.sqrt(np.mean(np.abs(chi[:, 0]) ** 2)))

    a_pl = np.conj(colfac)[None, :] * _amp_batch(chi, nvec, N)     # (trials,10)
    Mr = np.array([_riemann_vec(kap, a_pl[r]) for r in range(trials)])
    tt_ref = [_riemann_vec(kap, TT[:, p]) for p in (0, 1)]
    sv = np.linalg.svd(Mr, compute_uv=False)
    svn = (sv / (sv[0] + 1e-300)).tolist()
    n_prop = int(np.sum(np.array(svn) > ej.SV_THRESH))
    _, _, Vh = np.linalg.svd(Mr, full_matrices=False)
    Q1, _ = np.linalg.qr(Vh[:2].conj().T)
    Q2, _ = np.linalg.qr(np.array(tt_ref).conj().T)
    cosang = np.linalg.svd(Q1.conj().T @ Q2, compute_uv=False)
    tt_match = float(np.min(cosang) ** 2)

    iv = invitro_oracle(nvec, N, min(gamma, 0.3), T, th0)
    return {
        "k": list(nvec), "w_walk": w, "w_shell": float(r15.shell_omega(kl)),
        "gamma": gamma, "T": T,
        "C_initial": c_norm0, "C_final": c_final, "C_min": float(c_min),
        "C_ratio": float(c_final / (c_norm0 + 1e-300)),
        "C_trajectory": [(int(t), float(v)) for t, v in traj],
        "TT_retention": float(ttf / (tt0 + 1e-300)),
        "rms_growth": float(rms_final / (rms0 + 1e-300)),
        "sv_spectrum": [float(v) for v in svn[:8]],
        "sv_third": float(svn[2]) if len(svn) > 2 else 0.0,
        "n_prop": n_prop, "tt_match": tt_match,
        "invitro": iv,
    }


def run_cp1v3(N=16, gamma=0.045, T=2000, trials=8, th0=TH0):
    out = {"backend": B.NAME, "th0": th0, "c": math.cos(th0),
           "gamma": gamma, "N": N, "T": T, "trials": trials,
           "scope": "single-k on-shell alignment vs R16 in-vitro (NOT full assembly)"}
    ares, ascale = adjoint_residual()
    out["enforce_eq_measure"] = {"abs_diff": ares, "scale": ascale,
                                 "rel": ares / (ascale + 1e-300),
                                 "PASS": bool(ares / (ascale + 1e-300) < 1e-10)}
    # verify inverse walk
    rng = np.random.default_rng(0)
    ck = (rng.standard_normal((10, N, N, N, 2))
          + 1j * rng.standard_normal((10, N, N, N, 2)))
    resid = float(np.abs(geom_walk_inv(gw.geom_walk_all(ck.copy(), th0, th0, th0, th0), th0)
                         - ck).max())
    out["inverse_walk_residual"] = resid
    out["gate"] = cp2.r17_selfcheck_gate()
    modes = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2)]
    out["modes"] = {}
    for m in modes:
        out["modes"][str(m)] = align_mode(m, N=N, gamma=gamma, T=T, trials=trials, th0=th0)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "green_one_walk_cp1v3_results.json"))
    ap.add_argument("--N", type=int, default=16)
    ap.add_argument("--T", type=int, default=2000)
    ap.add_argument("--gamma", type=float, default=0.045)
    ap.add_argument("--trials", type=int, default=8)
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING backend={B.NAME}; run RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend={B.NAME}  CP1-v3 single-k on-shell alignment\n")
    out = run_cp1v3(N=args.N, gamma=args.gamma, T=args.T, trials=args.trials)

    e = out["enforce_eq_measure"]
    print(f"enforce==measure  |<Kx,y>-<x,K'y>|={e['abs_diff']:.2e} rel={e['rel']:.2e}  "
          f"-> {'PASS' if e['PASS'] else 'FAIL'}")
    print(f"inverse-walk residual = {out['inverse_walk_residual']:.2e}")
    print(f"r17 gate: dim(ker/gauge)_YEE={out['gate']['dim_ker_over_gauge_YEE']} "
          f"GATE={'PASS' if out['gate']['GATE_PASS'] else 'FAIL'}\n")
    hdr = f"  {'k':11s} {'w':>7} {'C_init':>9} {'C_min':>9} {'C_final':>9} {'TTret':>8} {'3rdSV':>8} {'ttmatch':>8} {'Nprop':>5} {'IVfloor':>9}"
    print(hdr)
    for m, r in out["modes"].items():
        print(f"  {m:11s} {r['w_walk']:7.4f} {r['C_initial']:9.2e} {r['C_min']:9.2e} "
              f"{r['C_final']:9.2e} {r['TT_retention']:8.5f} {r['sv_third']:8.2e} "
              f"{r['tt_match']:8.5f} {r['n_prop']:5d} {r['invitro']['C_final']:9.2e}")

    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: (
            o.tolist() if isinstance(o, np.ndarray) else float(o)))
    print(f"\nwrote {os.path.abspath(args.json)}")
