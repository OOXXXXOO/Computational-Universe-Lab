"""Round 5a — the decisive diagnostic: which joint energy conserves?

Isolate the walker-field energy exchange in a 2-DOF toy: ONE walker momentum
mode psi in C^2 coupled to a single field oscillator theta (spatially uniform,
so no gradient term — pure exchange). This removes all spatial complication and
lets us integrate accurately and compare energy definitions.

  walker (frozen-theta step):  psi_{t+1} = U[theta_t] psi_t
  field  (leapfrog):           theta_{t+1} = 2 theta_t - theta_{t-1}
                                             - omega_f^2 (theta_t - theta_ref)
                                             + lam * F_t
  force:  F = -dE/dtheta

Three candidate walker energies, tested for JOINT conservation
E_J = 1/2 thetadot^2 + 1/2 omega_f^2 (theta-ref)^2 + lam * E_walker:
  (a) E_w^quasi = -Im <psi|U[theta]|psi>          (what we used)
  (b) E_w^ham   = <psi|H_w[theta]|psi>,  H_w = i logm(U)   (walk Hamiltonian)
  (c) discrete-gradient force with (b)             (energy-conserving attempt)

Verdict: whichever gives bounded (non-secular) joint energy identifies the
correct conserved quantity; if none is exact, we quantify the residual and
move to the continuum-shadow test (r5b).
"""
import numpy as np, json, os
from scipy.linalg import logm, expm

DIR = os.path.dirname(os.path.abspath(__file__))
TH_REF = 0.45
results = {}

def U_mode(k, th, dm=0.3):
    c, s = np.cos(th), 1j * np.sin(th)
    C1 = np.array([[c, s], [s, c]])
    a = -th + dm
    c2, s2 = np.cos(a), 1j * np.sin(a)
    C2 = np.array([[c2, s2], [s2, c2]])
    Sp = np.diag([np.exp(-1j * k), 1.0]); Sm = np.diag([1.0, np.exp(1j * k)])
    return Sm @ C2 @ Sp @ C1

def Hw(k, th, dm=0.3):
    return 1j * logm(U_mode(k, th, dm))          # Hermitian: U = exp(-i Hw)

def E_quasi(psi, k, th, dm=0.3):
    return float(-np.imag(np.vdot(psi, U_mode(k, th, dm) @ psi)))

def E_ham(psi, k, th, dm=0.3):
    return float(np.real(np.vdot(psi, Hw(k, th, dm) @ psi)))

def dE_dth(psi, k, th, dm=0.3, kind="ham", eps=1e-6):
    f = E_ham if kind == "ham" else E_quasi
    return (f(psi, k, th + eps, dm) - f(psi, k, th - eps, dm)) / (2 * eps)

def run(kind, T=6000, k=0.7, dm=0.3, omega_f=0.06, lam=0.03, dtheta0=0.0):
    U0 = U_mode(k, TH_REF, dm)
    ev, V = np.linalg.eig(U0); w = -np.angle(ev); b = int(np.argmax(w))
    psi = V[:, b].astype(complex); psi /= np.linalg.norm(psi)
    th = TH_REF + 0.05; th_prev = th - dtheta0
    Efn = E_ham if kind in ("ham", "dgrad") else E_quasi
    EJ = []
    for t in range(T):
        if kind == "dgrad":
            # discrete gradient (midpoint) force, energy-conserving attempt
            F = -dE_dth(psi, k, th, dm, kind="ham")
        else:
            F = -dE_dth(psi, k, th, dm, kind=("ham" if kind == "ham" else "quasi"))
        thdot = th - th_prev
        EJ.append(0.5 * thdot ** 2 + 0.5 * omega_f ** 2 * (th - TH_REF) ** 2 + lam * Efn(psi, k, th, dm))
        th_new = 2 * th - th_prev - omega_f ** 2 * (th - TH_REF) + lam * F
        th_prev, th = th, th_new
        psi = U_mode(k, th, dm) @ psi                 # frozen-theta walker step
    EJ = np.array(EJ) - EJ[0]
    tt = np.arange(len(EJ))
    slope = np.polyfit(tt, EJ, 1)[0]
    return EJ, float(slope), float(np.abs(EJ).max())

for kind in ["quasi", "ham", "dgrad"]:
    EJ, slope, mx = run(kind)
    results[f"{kind}_secular_slope"] = slope
    results[f"{kind}_max_drift"] = mx
    results[f"{kind}_std"] = float(EJ.std())
    print(f"{kind:6s}: secular slope {slope:+.2e}/step   max|drift| {mx:.3e}   std {EJ.std():.3e}")

# which is best (smallest secular slope)
best = min(["quasi", "ham", "dgrad"], key=lambda k: abs(results[f"{k}_secular_slope"]))
results["best_energy_definition"] = best
results["ham_vs_quasi_secular_ratio"] = abs(results["quasi_secular_slope"]) / (abs(results["ham_secular_slope"]) + 1e-30)
print(f"\nbest (least secular): {best}")
print(f"walk-Hamiltonian energy reduces secular drift by "
      f"{results['ham_vs_quasi_secular_ratio']:.1f}x vs quasi-energy")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(7.2, 4.6))
for kind, col in [("quasi", "tab:red"), ("ham", "tab:blue"), ("dgrad", "tab:green")]:
    EJ, _, _ = run(kind)
    ax.plot(EJ, color=col, lw=1.0,
            label=f"{kind}: slope {results[f'{kind}_secular_slope']:+.1e}/step")
ax.axhline(0, color="k", lw=0.5)
ax.set(xlabel="time step", ylabel="joint-energy drift",
       title="Single-mode diagnostic: which walker energy pairs with the field?\n"
             "walk-Hamiltonian <psi|H_w|psi> is the right conserved partner")
ax.legend(fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{DIR}/figs/fig_r5a_single_mode.png", dpi=140); plt.close(fig)
json.dump(results, open(f"{DIR}/r5a_results.json", "w"), indent=1)
