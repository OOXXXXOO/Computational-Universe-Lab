"""Animation 3: relativistic dynamics emerging under a constant force.
Left: the wavepacket |psi(x,t)|^2 accelerating.
Right: measured velocity building up against the special-relativity curve
v = k/sqrt(m^2+k^2) and the speed of light — the packet KNOWS relativity.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
N, TH, E0, K0 = 3072, 0.35, 0.0015, 0.10
T_STEPS, SNAP = 1400, 20
x = np.arange(N) - N // 4
c, s = np.cos(TH), np.sin(TH)

w0 = np.arccos(np.cos(TH) * np.cos(K0))
nr, ni = np.cos(w0) - c * np.cos(K0), -np.sin(w0) + c * np.sin(K0)
dr, di = s * np.sin(K0), s * np.cos(K0)
dd = dr * dr + di * di
br, bi = (nr * dr + ni * di) / dd, (ni * dr - nr * di) / dd
an = 1 / np.sqrt(1 + br * br + bi * bi)
sig = 55.0
g = np.exp(-x ** 2 / (4 * sig ** 2)) * np.exp(1j * K0 * x)
psi0 = an * g; psi1 = an * (br + 1j * bi) * g
nrm = np.sqrt((abs(psi0) ** 2 + abs(psi1) ** 2).sum()); psi0 /= nrm; psi1 /= nrm

phase = np.exp(1j * E0 * x)
snaps, xs = [], []
for t in range(T_STEPS):
    prob = abs(psi0) ** 2 + abs(psi1) ** 2
    xs.append(float((prob * x).sum()))
    if t % SNAP == 0:
        snaps.append(prob.copy())
    a = c * psi0 + 1j * s * psi1
    b = 1j * s * psi0 + c * psi1
    psi0 = np.roll(a, 1) * phase
    psi1 = np.roll(b, -1) * phase
xs = np.array(xs); v_meas = np.gradient(xs)
tt = np.arange(T_STEPS)
k_t = K0 + E0 * tt
v_rel = k_t / np.sqrt(TH ** 2 + k_t ** 2)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.3))
line, = ax1.plot([], [], color="tab:red", lw=1.2)
ax1.set(xlim=(x[0], x[-1]), ylim=(0, max(snaps[0]) * 1.15),
        xlabel="x (lattice sites)", ylabel="$|\\psi|^2$",
        title="constant force via rule phase $e^{iEx}$: packet accelerates")
txt1 = ax1.text(0.02, 0.93, "", transform=ax1.transAxes, fontsize=10)
ax1.grid(alpha=0.3)

ax2.plot(tt, v_rel, "k--", lw=1.4, label="special relativity $v=k/\\sqrt{m^2+k^2}$")
ax2.axhline(1.0, color="gray", ls=":", lw=1.2, label="speed of light $c$")
vline, = ax2.plot([], [], color="tab:red", lw=1.6, label="measured $\\langle v\\rangle(t)$")
dot, = ax2.plot([], [], "o", color="tab:red", ms=6)
ax2.set(xlim=(0, T_STEPS), ylim=(0, 1.1), xlabel="time step", ylabel="velocity",
        title="the packet obeys relativity it was never told about")
ax2.legend(fontsize=8, loc="lower right"); ax2.grid(alpha=0.3)
txt2 = ax2.text(0.02, 0.9, "", transform=ax2.transAxes, fontsize=10)

def update(f):
    t = f * SNAP
    line.set_data(x, snaps[f])
    txt1.set_text(f"t = {t}")
    vline.set_data(tt[:t], v_meas[:t])
    if t > 0:
        dot.set_data([t - 1], [v_meas[t - 1]])
        err = abs(v_meas[max(0, t - 50):t] - v_rel[max(0, t - 50):t]).mean()
        gam = 1 / np.sqrt(max(1 - v_meas[t - 1] ** 2, 1e-6))
        txt2.set_text(f"v = {v_meas[t-1]:.3f}   $\\gamma$ = {gam:.2f}\n|v - v_rel| = {err:.4f}")
    return line, vline, dot, txt1, txt2

ani = FuncAnimation(fig, update, frames=len(snaps), blit=True)
fig.suptitle("Emergence III: special-relativistic dynamics from a discrete rule (nothing relativistic was put in)", fontsize=10)
fig.tight_layout()
ani.save(f"{OUT}/anim3_saturation.gif", writer="pillow", fps=10)
print("anim3 done")
