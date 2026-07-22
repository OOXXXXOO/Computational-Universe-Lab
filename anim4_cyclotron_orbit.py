"""Animation 4: the Lorentz force emerging — a QCA wavepacket in a uniform
magnetic field (Peierls phases) executes a cyclotron orbit.
Overlay: the semiclassical orbit predicted from the EXACT lattice dispersion,
and the continuum Lorentz-force circle r = p/qB.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
L, K0, B = 256, 0.30, 0.005
T, SNAP = 700, 14
inv = 1 / np.sqrt(2)

kg = 2 * np.pi * np.fft.fftfreq(L)
KXG, KYG = np.meshgrid(kg, kg, indexing="ij")
xx = np.arange(L) - L // 2
X, Y = np.meshgrid(xx, xx, indexing="ij")

def U2pair(kx, ky):
    Sx = np.array([[np.cos(kx), -1j * np.sin(kx)], [-1j * np.sin(kx), np.cos(kx)]])
    Sy = np.array([[np.cos(ky), -np.sin(ky)], [np.sin(ky), np.cos(ky)]])
    return (Sx @ Sy) @ (Sy @ Sx)          # massless

env = np.exp(-((KXG - K0) ** 2 + KYG ** 2) * 18.0 ** 2) * np.exp(-1j * (KXG + KYG) * (L // 2))
ps0 = np.zeros((L, L), complex); ps1 = np.zeros((L, L), complex)
for i, j in zip(*np.where(abs(env) > 1e-6)):
    ev, V = np.linalg.eig(U2pair(KXG[i, j], KYG[i, j]))
    w = -np.angle(ev); b = int(np.argmax(w))
    v = V[:, b]; v = v * np.exp(-1j * np.angle(v[0]))
    ps0[i, j] = env[i, j] * v[0]; ps1[i, j] = env[i, j] * v[1]
psi0 = np.fft.ifftn(ps0); psi1 = np.fft.ifftn(ps1)
n = np.sqrt((abs(psi0) ** 2 + abs(psi1) ** 2).sum()); psi0 /= n; psi1 /= n

pxp = np.exp(1j * (-B) * Y); pxm = np.conj(pxp)
def sx_(a, b):
    up = inv * (a + b); dn = inv * (a - b)
    up = np.roll(up * pxp, 1, axis=0); dn = np.roll(dn * pxm, -1, axis=0)
    return inv * (up + dn), inv * (up - dn)
def sy_(a, b):
    up = inv * (a - 1j * b); dn = inv * (a + 1j * b)
    up = np.roll(up, 1, axis=1); dn = np.roll(dn, -1, axis=1)
    return inv * (up + dn), inv * (1j * up - 1j * dn)

snaps, cms = [], []
for t in range(T):
    p = abs(psi0) ** 2 + abs(psi1) ** 2
    cms.append((float((p * X).sum()), float((p * Y).sum())))
    if t % SNAP == 0:
        snaps.append(p[::2, ::2].T.copy())      # transpose: imshow rows = y
    if t % 2 == 0:
        psi0, psi1 = sx_(psi0, psi1); psi0, psi1 = sy_(psi0, psi1)
    else:
        psi0, psi1 = sy_(psi0, psi1); psi0, psi1 = sx_(psi0, psi1)
cms = np.array(cms)

# semiclassical orbit with exact lattice dispersion (massless)
def w1(kx, ky):
    ev = np.linalg.eigvals(U2pair(kx, ky))
    return np.max(-np.angle(ev)) / 2
dk = 1e-5
kx, ky, sxp, syp = K0, 0.0, 0.0, 0.0
semi = []
for t in range(T):
    vx = (w1(kx + dk, ky) - w1(kx - dk, ky)) / (2 * dk)
    vy = (w1(kx, ky + dk) - w1(kx, ky - dk)) / (2 * dk)
    semi.append((sxp, syp))
    sxp += vx; syp += vy
    kx += B * vy; ky += -B * vx
semi = np.array(semi)
# align curvature sign of semiclassics with the quantum run
if abs(semi[120, 1] - cms[120, 1]) > abs(-semi[120, 1] - cms[120, 1]):
    semi[:, 1] *= -1
r_cont = K0 / B

fig, ax = plt.subplots(figsize=(6.6, 6.6))
im = ax.imshow(snaps[0], origin="lower", cmap="magma",
               extent=[xx[0], xx[-1], xx[0], xx[-1]],
               vmax=max(snaps[0].max(), 1e-9))
trace, = ax.plot([], [], color="cyan", lw=1.4, label="packet center $\\langle x\\rangle(t)$")
ax.plot(semi[:, 0], semi[:, 1], color="lime", lw=1.0, ls="--",
        label="semiclassics, exact lattice dispersion")
tha = np.linspace(0, 2 * np.pi, 200)
cy = np.sign(semi[120, 1]) * r_cont          # orbit center (0, +-r), start point at origin
ax.plot(r_cont * np.cos(tha), cy + r_cont * np.sin(tha), "w:", lw=1.2,
        label=f"continuum Lorentz force $r=p/qB={r_cont:.0f}$")
ax.set(xlim=(-110, 110), ylim=(-150, 70), xlabel="x", ylabel="y")
ax.legend(fontsize=8, loc="upper right")
txt = ax.text(0.02, 0.02, "", transform=ax.transAxes, color="white", fontsize=10, va="bottom")

def update(f):
    t = f * SNAP
    im.set_data(snaps[f]); im.set_clim(0, snaps[f].max())
    trace.set_data(cms[:t, 0], cms[:t, 1])
    txt.set_text(f"t = {t}   B = {B}   $\\omega_c^{{pred}}=qB/E$ = {B/K0:.4f}")
    return im, trace, txt

ani = FuncAnimation(fig, update, frames=len(snaps), blit=True)
ax.set_title("Emergence IV: Lorentz force $F=qv\\times B$ from position-dependent rule phases", fontsize=10)
fig.tight_layout()
ani.save(f"{OUT}/anim4_cyclotron.gif", writer="pillow", fps=9)
print("anim4 done, snaps:", len(snaps))
