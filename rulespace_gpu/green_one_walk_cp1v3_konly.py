"""green_one_walk_cp1v3_konly -- k-space constraint damping using the certified
_my_K_symbol. The walk remains real-space; constraint measurement and damping are
applied in Fourier space using the symbol operator proven correct in the gates.
This isolates whether the R18-time-term-floor bug is purely the real-space K
implementation or requires a deeper rewrite of the time-difference integration.
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

DIR = os.path.dirname(os.path.abspath(__file__))
IDX10 = ej.IDX10
PK = ej.PK
OFFSET = cp2.OFFSET
r15 = cp2.r15

TH0 = math.pi / 3.0
C = math.cos(TH0)


def _klat(nvec, N):
    return np.array(nvec, float) * (2 * np.pi / N)


def _onshell_spinor(kvec, N, th0=TH0):
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
    return np.einsum("xyz,cxyz->c", proj, chi[..., 0])


def _riemann_vec(kap, a10):
    """Riemann 256-vector from a 10-vec in the hbar frame (h = hbar - eta tr/2)."""
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


def damp_konly(nvec, N, gamma, T, th0):
    """k-space constraint damping using certified _my_K_symbol."""
    kl = _klat(nvec, N)
    w, xi = _onshell_spinor(kl, N, th0)
    kap = r15.kappa_placed(kl)
    k4 = np.array([w, kl[0], kl[1], kl[2]])
    colfac = np.array([np.exp(0.5j * float(np.dot(k4, OFFSET[cc]))) for cc in range(10)])
    TT = r15.tt_basis(kap)
    G = r15.gauge_block(kap)
    # Yee-framed mixed seed
    rng = np.random.default_rng(1)
    a0 = colfac * (TT @ (rng.normal(size=2) + 1j * rng.normal(size=2))
                   + G @ (rng.normal(size=4) + 1j * rng.normal(size=4))
                   + 0.5 * (rng.normal(size=10) + 1j * rng.normal(size=10)))
    chi = _seed(nvec, a0, xi, N)
    # certified K symbol (4x10)
    Ksym = cp2._my_K_symbol(k4, C) / 1j
    D = np.eye(10) - gamma * (Ksym.conj().T @ Ksym)
    c_traj = []
    for t in range(T + 1):
        # measure C_norm in real space (for reporting)
        Cf = np.zeros((N, N, N, 4), complex)
        f0 = np.moveaxis(chi[..., 0], 0, -1)
        wf0 = np.moveaxis(gw.geom_walk_all(chi.copy(), th0, th0, th0, th0)[..., 0], 0, -1)
        for nu in range(4):
            acc = np.zeros((N, N, N), complex)
            for mu in (1, 2, 3):
                comp = PK[(mu, nu)]
                acc = acc + cp2._dsp_dict(f0[..., comp], mu, comp, True)
            c0 = PK[(0, nu)]
            acc = acc - (1.0 / C) * (f0[..., c0] - wf0[..., c0])
            Cf[..., nu] = acc
        c_norm = float(np.sqrt(np.mean(np.abs(Cf) ** 2)))
        c_traj.append((t, c_norm))
        # walk
        chi = gw.geom_walk_all(chi, th0, th0, th0, th0)
        # extract +k amplitude and damp in k-space with certified D
        a_k = np.conj(colfac) * _amp(chi, nvec, N)
        a_k = np.exp(-1j * w) * (D @ a_k)
        # rebuild chi from damped amplitude
        for c in range(10):
            chi[c, ..., 0] = (colfac[c] * a_k[c])[None, ...]
    # final TT retention and SV
    a_final = np.conj(colfac) * _amp(chi, nvec, N)
    tt0 = np.linalg.norm(TT.conj().T @ a0)
    ttf = np.linalg.norm(TT.conj().T @ a_final)
    tt_ret = float(ttf / (tt0 + 1e-300))
    # batch of trials for SV
    trials, rows = 8, []
    for r in range(trials):
        rr = np.random.default_rng(100 + r)
        ar = colfac * (TT @ (rr.normal(size=2) + 1j * rr.normal(size=2))
                       + G @ (rr.normal(size=4) + 1j * rr.normal(size=4))
                       + 0.5 * (rr.normal(size=10) + 1j * rr.normal(size=10)))
        chir = _seed(nvec, ar, xi, N)
        for t in range(T):
            chir = gw.geom_walk_all(chir, th0, th0, th0, th0)
            ak = np.conj(colfac) * _amp(chir, nvec, N)
            ak = np.exp(-1j * w) * (D @ ak)
            for c in range(10):
                chir[c, ..., 0] = (colfac[c] * ak[c])[None, ...]
        rows.append(_riemann_vec(kap, ak))
    Mr = np.array(rows)
    sv = np.linalg.svd(Mr, compute_uv=False)
    svn = (sv / (sv[0] + 1e-300)).tolist()
    n_prop = int(np.sum(np.array(svn) > ej.SV_THRESH))
    # tt_match
    _, _, Vh = np.linalg.svd(Mr, full_matrices=False)
    ttref = [_riemann_vec(kap, TT[:, p]) for p in (0, 1)]
    Q1, _ = np.linalg.qr(Vh[:2].conj().T)
    Q2, _ = np.linalg.qr(np.array(ttref).conj().T)
    tt_match = float(np.min(np.linalg.svd(Q1.conj().T @ Q2, compute_uv=False)) ** 2)

    return {
        "k": list(nvec), "w_walk": w, "w_shell": float(r15.shell_omega(kl)),
        "gamma": gamma, "T": T,
        "C_initial": c_traj[0][1], "C_final": c_traj[-1][1],
        "C_min": min(v for _, v in c_traj),
        "TT_retention": tt_ret,
        "sv_spectrum": [float(v) for v in svn[:8]],
        "sv_third": float(svn[2]) if len(svn) > 2 else 0.0,
        "n_prop": n_prop, "tt_match": tt_match,
    }


def run_cp1v3_konly(N=16, gamma=0.045, T=2000, trials=8, th0=TH0):
    out = {"backend": B.NAME, "th0": th0, "c": math.cos(th0),
           "gamma": gamma, "N": N, "T": T, "trials": trials,
           "scope": "k-space constraint damping using certified _my_K_symbol"}
    out["gate"] = cp2.r17_selfcheck_gate()
    modes = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2)]
    out["modes"] = {}
    for m in modes:
        out["modes"][str(m)] = damp_konly(m, N, gamma, T, th0)
    # invitro oracle for each mode
    for m in modes:
        kl = _klat(m, N); kap = r15.kappa_placed(kl)
        TT = r15.tt_basis(kap); G = r15.gauge_block(kap)
        w = r15.shell_omega(kl)
        K = r15.constraint_matrix(kap)
        rng = np.random.default_rng(7)
        a = (TT @ (rng.normal(size=2) + 1j * rng.normal(size=2))
             + G @ (rng.normal(size=4) + 1j * rng.normal(size=4))
             + 0.5 * (rng.normal(size=10) + 1j * rng.normal(size=10)))
        D = np.eye(10) - min(gamma, 0.3) * (K.conj().T @ K)
        for _ in range(T):
            a = np.exp(-1j * w) * (D @ a)
        out["modes"][str(m)]["invitro_C_final"] = float(np.linalg.norm(K @ a))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(DIR, "..", "green_one_walk_cp1v3_konly_results.json"))
    ap.add_argument("--N", type=int, default=16)
    ap.add_argument("--T", type=int, default=2000)
    ap.add_argument("--gamma", type=float, default=0.045)
    ap.add_argument("--trials", type=int, default=8)
    args = ap.parse_args()

    if B.NAME != "numpy":
        print(f"WARNING backend={B.NAME}; run RULESPACE_BACKEND=numpy (fp64).")
    print(f"backend={B.NAME}  CP1-v3_konly k-space constraint damping\n")
    out = run_cp1v3_konly(N=args.N, gamma=args.gamma, T=args.T, trials=args.trials)

    print(f"r17 gate: dim(ker/gauge)={out['gate']['dim_ker_over_gauge_YEE']} GATE={'PASS' if out['gate']['GATE_PASS'] else 'FAIL'}")
    hdr = f"  {'k':11s} {'C_init':>9} {'C_min':>9} {'C_final':>9} {'TTret':>8} {'3rdSV':>8} {'ttmatch':>8} {'Nprop':>5} {'IVfloor':>9}"
    print(hdr)
    for m, r in out["modes"].items():
        print(f"  {m:11s} {r['C_initial']:9.2e} {r['C_min']:9.2e} {r['C_final']:9.2e} "
              f"{r['TT_retention']:8.5f} {r['sv_third']:8.2e} {r['tt_match']:8.5f} {r['n_prop']:5d} {r.get('invitro_C_final', -1):.2e}")

    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: (
            o.tolist() if isinstance(o, np.ndarray) else float(o)))
    print(f"\nwrote {os.path.abspath(args.json)}")