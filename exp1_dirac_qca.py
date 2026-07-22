"""Exp 1: 1D Dirac Quantum Cellular Automaton (quantum walk) -> Dirac equation in continuum limit.

Model: psi(t+1) = S C psi(t), 2-component field on Z.
Coin (mass step): C = [[cos t, i sin t],[i sin t, cos t]]  (t = theta = m*eps)
Shift: component 0 moves +1, component 1 moves -1.
Exact dispersion: cos w(k) = cos(theta) cos(k).
Continuum limit (eps->0, theta=m*eps, k=p*eps): w/eps -> sqrt(m^2+p^2).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json, os

OUT = os.path.join(os.path.dirname(__file__), "figs")
os.makedirs(OUT, exist_ok=True)
results = {}

# ---------- (a) spacetime evolution ----------
N, T = 401, 190
theta = 0.35          # mass angle
k0 = 0.9              # packet momentum
sig = 12.0
x = np.arange(N) - N // 2
c, s = np.cos(theta), 1j * np.sin(theta)
# project packet onto the positive-group-velocity eigenspinor of U(k0)
Ck = np.array([[c, s], [s, c]])
Uk = np.diag([np.exp(-1j * k0), np.exp(1j * k0)]) @ Ck   # roll(+1) => e^{-ik}
ev, evec = np.linalg.eig(Uk)
w0_ = np.arccos(np.cos(theta) * np.cos(k0))
branch = np.argmin(np.abs(ev - np.exp(-1j * w0_)))       # e^{-iw} branch moves with +vg
spinor = evec[:, branch]
psi = np.zeros((2, N), complex)
g = np.exp(-x**2 / (4 * sig**2)) * np.exp(1j * k0 * x)
psi[0] = spinor[0] * g; psi[1] = spinor[1] * g
psi /= np.linalg.norm(psi)
prob = np.zeros((T, N))
for t in range(T):
    prob[t] = np.abs(psi[0])**2 + np.abs(psi[1])**2
    a = c * psi[0] + s * psi[1]
    b = s * psi[0] + c * psi[1]
    psi[0] = np.roll(a, 1)   # right mover
    psi[1] = np.roll(b, -1)  # left mover

# analytic group velocity: dw/dk = cos(theta) sin(k) / sin(w)
w0 = np.arccos(np.cos(theta) * np.cos(k0))
vg = np.cos(theta) * np.sin(k0) / np.sin(w0)
results["exp1_vg_analytic"] = vg
# measured velocity from <x>
xs = (prob * x).sum(axis=1)
vg_meas = np.polyfit(np.arange(T // 2, T), xs[T // 2:], 1)[0]
results["exp1_vg_measured"] = vg_meas

fig, ax = plt.subplots(figsize=(6.4, 4.6))
ax.imshow(prob, aspect="auto", origin="lower", cmap="magma",
          extent=[x[0], x[-1], 0, T], interpolation="nearest",
          vmax=np.percentile(prob, 99.5))
ax.plot([0, T], [0, T], color="cyan", lw=0.8, ls="--", label="light cone |v|=1")
ax.plot([0, -T], [0, T], color="cyan", lw=0.8, ls="--")
ax.plot([0, vg * T], [0, T], color="lime", lw=1.2, label=f"Dirac group velocity v={vg:.3f}")
ax.set(xlabel="lattice site x", ylabel="time step t",
       title=f"Dirac QCA wavepacket (mass angle={theta}, k0={k0})\nmeasured v={vg_meas:.3f}")
ax.set_xlim(x[0], x[-1]); ax.legend(loc="upper left", fontsize=8)
fig.tight_layout(); fig.savefig(f"{OUT}/fig1a_spacetime.png", dpi=140); plt.close(fig)

# ---------- (b) dispersion relations ----------
k = np.linspace(-np.pi, np.pi, 800)
fig, ax = plt.subplots(figsize=(6.4, 4.6))
for th, col in [(0.15, "tab:blue"), (0.5, "tab:orange"), (1.0, "tab:green")]:
    w = np.arccos(np.cos(th) * np.cos(k))
    ax.plot(k, w, color=col, lw=1.6, label=f"QCA  cos w = cos({th}) cos k")
    ax.plot(k, np.sqrt(th**2 + k**2), color=col, lw=1.0, ls="--")
ax.plot([], [], "k--", lw=1, label="continuum  w = sqrt(m^2+k^2)")
ax.set(xlabel="k (lattice units)", ylabel="w", title="QCA dispersion vs relativistic dispersion")
ax.legend(fontsize=8); fig.tight_layout()
fig.savefig(f"{OUT}/fig1b_dispersion.png", dpi=140); plt.close(fig)

# ---------- (c) convergence order ----------
m = 1.0
p = np.linspace(-2, 2, 401)          # physical momentum window
eps_list = np.geomspace(0.5, 0.005, 12)
errs = []
for eps in eps_list:
    w_lat = np.arccos(np.cos(m * eps) * np.cos(p * eps)) / eps
    errs.append(np.max(np.abs(w_lat - np.sqrt(m**2 + p**2))))
errs = np.array(errs)
slope = np.polyfit(np.log(eps_list), np.log(errs), 1)[0]
results["exp1_convergence_order"] = slope

fig, ax = plt.subplots(figsize=(6.0, 4.4))
ax.loglog(eps_list, errs, "o-", label="max |w_QCA/eps - sqrt(m^2+p^2)|, |p|<2")
ax.loglog(eps_list, errs[-1] * (eps_list / eps_list[-1])**2, "k--", lw=1, label="slope 2 reference")
ax.set(xlabel="lattice spacing eps", ylabel="dispersion error",
       title=f"Continuum-limit convergence: order = {slope:.3f}")
ax.legend(fontsize=9); ax.grid(True, which="both", alpha=0.3)
fig.tight_layout(); fig.savefig(f"{OUT}/fig1c_convergence.png", dpi=140); plt.close(fig)

print(json.dumps(results, indent=1))
