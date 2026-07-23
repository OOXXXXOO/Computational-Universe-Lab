"""Animation 1: HOW we judge emergence — the continuum-limit protocol, live.
Left: lattice dispersion converging onto the Dirac curve as eps -> 0.
Right: the JUDGE — error vs eps accumulating on log-log axes; verdict = slope 2.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
m = 1.0
p = np.linspace(-2, 2, 300)
eps_list = np.geomspace(0.6, 0.008, 46)
cont = np.sqrt(m ** 2 + p ** 2)

errs = []
for eps in eps_list:
    w = np.arccos(np.clip(np.cos(m * eps) * np.cos(p * eps), -1, 1)) / eps
    errs.append(np.max(np.abs(w - cont)))
errs = np.array(errs)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.4))
ax1.plot(p, cont, "k--", lw=1.6, label="Dirac  $\\omega=\\sqrt{m^2+p^2}$")
lat_line, = ax1.plot([], [], color="tab:red", lw=1.8, label="lattice  $\\omega_\\varepsilon(p)$")
ax1.set(xlabel="physical momentum p", ylabel="energy", ylim=(0.9, 2.6),
        title="the phenomenon: dispersion approaching relativity")
ax1.legend(fontsize=9, loc="upper center")
ax1.grid(alpha=0.3)
txt1 = ax1.text(0.03, 0.95, "", transform=ax1.transAxes, fontsize=10, va="top")

ax2.set(xscale="log", yscale="log", xlabel="lattice spacing $\\varepsilon$",
        ylabel="max dispersion error", xlim=(6e-3, 0.8), ylim=(1e-5, 0.3),
        title="the JUDGE: error $\\sim\\varepsilon^2$ ?")
ax2.grid(alpha=0.3, which="both")
pts, = ax2.plot([], [], "o", color="tab:red", ms=5)
ref, = ax2.plot([], [], "k--", lw=1)
txt2 = ax2.text(0.03, 0.08, "", transform=ax2.transAxes, fontsize=11, va="bottom")

def update(f):
    eps = eps_list[f]
    w = np.arccos(np.clip(np.cos(m * eps) * np.cos(p * eps), -1, 1)) / eps
    lat_line.set_data(p, w)
    txt1.set_text(f"$\\varepsilon$ = {eps:.3f}")
    pts.set_data(eps_list[: f + 1], errs[: f + 1])
    if f >= 4:
        sl = np.polyfit(np.log(eps_list[: f + 1]), np.log(errs[: f + 1]), 1)[0]
        ref.set_data(eps_list[: f + 1], errs[f] * (eps_list[: f + 1] / eps_list[f]) ** 2)
        verdict = "PASS: continuum limit exists" if abs(sl - 2) < 0.1 else "measuring..."
        txt2.set_text(f"measured order = {sl:.3f}\n{verdict}")
    return lat_line, pts, ref, txt1, txt2

ani = FuncAnimation(fig, update, frames=len(eps_list), blit=True)
fig.suptitle("Emergence protocol I: convergence-order test (Dirac equation from the QCA)", fontsize=11)
fig.tight_layout()
ani.save(f"{OUT}/anim1_convergence.gif", writer="pillow", fps=8)
print("anim1 done")
