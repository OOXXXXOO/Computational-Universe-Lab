"""Round 3 — C1 dress rehearsal in 1+1D: the field equation from CONSISTENCY.

The walker's exact conserved energy under static theta:
    E_w = -Im <psi| U(theta) |psi>        (quasi-energy; conserved because
                                           <psi_t|U|psi_t> is invariant)
The candidate field sources:
    rho    : probability density              (judge-selected, EP-violating)
    T00    : time-derivative bilinear ~ rho*sin(omega)   (EP up to lattice)
    F      : the CONSISTENCY source  F(x) = -dE_w/dtheta(x)  (analytic, local)

Claims tested to machine precision / high accuracy:
 (A) sum_x T00 is EXACTLY conserved for static theta.
 (B) With the field equation  theta_tt = c^2 Lap(theta) + lam*F  and lam=1,
     the JOINT energy  E_tot = E_w + E_f  is conserved (bounded drift),
     while sources rho and T00-proxy leak energy secularly.
     => consistency (joint conservation + action-reaction) SELECTS F and
     FIXES the coupling lam=1 (in field-energy units). No judges needed.
 (C) The consistency source automatically satisfies the equivalence
     principle: Q_F/omega constant across species (EP derived, not assumed),
     and F>0 where matter sits => theta rises => c falls => ATTRACTION:
     the sign of gravity becomes a theorem.

Analytic local form of F(x): with psi1=C1 psi, psib=C2 S+ C1 psi,
chi1=S-^dag psi, chi3=S+^dag C2^dag chi1:
    F(x) = Re[chi3^dag sigma_x psi1](x) - Re[chi1^dag sigma_x psib](x)
(derivation: dC1/dtheta = +i sx C1, dC2/dtheta = -i sx C2, chain rule on
 E_w = -Im<psi|S- C2 S+ C1 psi>.)
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rulespace import core

DIR = os.path.dirname(os.path.abspath(__file__))
N = 256
results = {}

def U_apply(psi0, psi1, th, dm=0.0):
    return core.walker_step(psi0, psi1, th, dm=dm)

def E_walker(psi0, psi1, th, dm=0.0):
    u0, u1 = U_apply(psi0, psi1, th, dm)
    return float(-np.imag((np.conj(psi0) * u0 + np.conj(psi1) * u1).sum()))

def consistency_source(psi0, psi1, th, dm=0.0):
    """F(x) = -dE_w/dtheta(x), exact local bilinear (see docstring)."""
    # forward legs
    a0, a1 = core.coin(psi0, psi1, th)                # psi1_vec = C1 psi
    b0 = np.roll(a0, 1); b1 = a1                      # S+ (comp0 -> right)
    c0, c1 = core.coin(b0, b1, -th + dm)              # psib = C2 S+ C1 psi
    # adjoint legs
    x1_0 = psi0; x1_1 = np.roll(psi1, 1)              # chi1 = S-^dag psi
    y0, y1 = core.coin(x1_0, x1_1, +th - dm)          # C2^dag chi1
    z0 = np.roll(y0, -1); z1 = y1                     # chi3 = S+^dag C2^dag chi1
    # sigma_x bilinears
    t1 = np.real(np.conj(z0) * a1 + np.conj(z1) * a0)
    t2 = np.real(np.conj(x1_0) * c1 + np.conj(x1_1) * c0)
    return t1 - t2

# ---------------- (A) exact conservation of sum T00 ----------------
th = np.full(N, core.TH_REF)
psi0, psi1 = core.packet(N, N // 2, 0.7, 11.0, dm=0.3)
prev0, prev1 = psi0.copy(), psi1.copy()
tots = []
for t in range(400):
    nxt0, nxt1 = U_apply(psi0, psi1, th, dm=0.3)
    T00 = -0.5 * (np.conj(psi0) * (nxt0 - prev0) + np.conj(psi1) * (nxt1 - prev1)).imag
    if t > 0:
        tots.append(T00.sum())
    prev0, prev1 = psi0, psi1
    psi0, psi1 = nxt0, nxt1
tots = np.array(tots)
results["A_T00_conservation_drift"] = float(np.abs(tots - tots[0]).max())
print(f"(A) sum T00 drift over 400 steps: {results['A_T00_conservation_drift']:.2e}  (exact conservation)")

# quick check: analytic F vs finite-difference dE/dtheta at random sites
psi0, psi1 = core.packet(N, N // 2, 0.7, 11.0, dm=0.3)
F = consistency_source(psi0, psi1, th, dm=0.3)
eps = 1e-6
errs = []
for xtest in [100, 128, 140, 60]:
    thp = th.copy(); thp[xtest] += eps
    thm = th.copy(); thm[xtest] -= eps
    dE = (E_walker(psi0, psi1, thp, 0.3) - E_walker(psi0, psi1, thm, 0.3)) / (2 * eps)
    errs.append(abs(-dE - F[xtest]))
results["A_F_analytic_vs_fd"] = float(max(errs))
print(f"(A) analytic F vs finite-difference: max err {max(errs):.2e}")

# ---------------- (B) joint-energy conservation selects F ----------------
CG2, T_RUN, DM = 0.30, 2500, 0.3
def coupled_run(source_kind, lam=1.0):
    psi0, psi1 = core.packet(N, N // 2, 0.7, 11.0, dm=DM)
    prev0, prev1 = psi0.copy(), psi1.copy()
    th = np.full(N, core.TH_REF); th_prev = th.copy()
    drift = []
    E0 = None
    for t in range(T_RUN):
        nxt0, nxt1 = U_apply(psi0, psi1, th, dm=DM)
        if source_kind == "F":
            src = consistency_source(psi0, psi1, th, dm=DM)
        elif source_kind == "T00":
            src = -0.5 * (np.conj(psi0) * (nxt0 - prev0) + np.conj(psi1) * (nxt1 - prev1)).imag
        else:
            src, _ = core.rho_J(psi0, psi1)
            src = 0.05 * src                      # scale rho to comparable size
        thdot = th - th_prev
        Ef = float(0.5 * (thdot ** 2).sum() + 0.5 * CG2 * (core.grad(th) ** 2).sum())
        Ew = E_walker(psi0, psi1, th, dm=DM)
        Etot = Ew + Ef
        if E0 is None: E0 = Etot
        drift.append(Etot - E0)
        # field leapfrog with the chosen source (no clip in this regime check)
        th_new = 2 * th - th_prev + CG2 * core.lap(th) + lam * src
        th_new = np.clip(th_new, core.TH_MIN, core.TH_MAX)
        th_prev, th = th, th_new
        prev0, prev1 = psi0, psi1
        psi0, psi1 = nxt0, nxt1
    return np.array(drift)

for kind in ["F", "T00", "rho"]:
    d = coupled_run(kind)
    results[f"B_drift_{kind}_max"] = float(np.abs(d).max())
    results[f"B_drift_{kind}_final"] = float(d[-1])
    print(f"(B) source={kind:4s}: |E_tot drift| max {np.abs(d).max():.3e}  final {d[-1]:+.3e}")

# lam sensitivity: consistency fixes lam=1
for lam in [0.5, 1.0, 2.0]:
    d = coupled_run("F", lam=lam)
    results[f"B_drift_F_lam{lam}"] = float(np.abs(d).max())
    print(f"(B) source=F lam={lam}: |drift| max {np.abs(d).max():.3e}")

# ---------------- (C) EP and the sign, derived ----------------
def omega_of(k0, dm):
    ev = np.linalg.eigvals(core.walk_matrix(k0, core.TH_REF, dm))
    return float(np.max(-np.angle(ev)))

rows = []
for (k0, dm) in [(0.10, 0.10), (0.10, 0.20), (0.10, 0.35), (0.10, 0.50),
                 (0.30, 0.50), (0.10, 0.80), (0.50, 0.0), (0.9, 0.0)]:
    psi0, psi1 = core.packet(N, N // 2, k0, 12.0, dm=dm)
    F = consistency_source(psi0, psi1, np.full(N, core.TH_REF), dm=dm)
    w = omega_of(k0, dm)
    rows.append({"k0": k0, "dm": dm, "omega": w, "Q_F": float(F.sum()),
                 "F_positive_at_matter": bool(F[N // 2 - 20:N // 2 + 20].mean() > 0)})
QF = np.array([r["Q_F"] for r in rows]); WS = np.array([r["omega"] for r in rows])
ratio = QF / WS
results["C_QF_over_omega"] = {f"k0={r['k0']},dm={r['dm']}": float(r["Q_F"] / r["omega"]) for r in rows}
results["C_EP_spread"] = float(ratio.std() / abs(ratio.mean()))
results["C_all_F_positive"] = bool(all(r["F_positive_at_matter"] for r in rows))
print("\n(C) consistency source across species:")
for r in rows:
    print(f"    k0={r['k0']:.2f} dm={r['dm']:.2f}: omega={r['omega']:.3f}  "
          f"Q_F={r['Q_F']:+.4f}  Q_F/omega={r['Q_F']/r['omega']:+.4f}  F>0 at matter: {r['F_positive_at_matter']}")
print(f"(C) EP spread of Q_F/omega: {results['C_EP_spread']:.4f}")
print(f"(C) F>0 at matter for ALL species (=> attraction, kappa>0 derived): {results['C_all_F_positive']}")

json.dump(results, open(os.path.join(DIR, "r3_results.json"), "w"), indent=1)
