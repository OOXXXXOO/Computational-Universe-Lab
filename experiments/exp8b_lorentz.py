"""Exp 8B (supersedes exp8 part B): the Lorentz force from Peierls phases,
measured two ways.

(1) RIGOROUS semiclassics: integrate kdot = B (v x z), xdot = v(k) using the
    EXACT lattice dispersion of the alternating-order 2D Dirac walk.
    Continuum Lorentz force predicts a circle of radius r = p/(qB).
(2) FULL QUANTUM wavepacket: k-space cyclotron rotation of <k_y>(t).
    Landau-gauge canonical k_x stays exactly conserved; kinetic momentum
    rotates at omega_c = qB/E (relativistic cyclotron frequency).
    Packet dispersion damps the oscillation (computable artifact), the
    frequency survives.
"""
import numpy as np, json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "figs")
RES = os.path.join(DIR, "exp8_results.json")
results = json.load(open(RES)) if os.path.exists(RES) else {}
inv = 1 / np.sqrt(2)

def U2pair(kx, ky, th):
    ch, sh = np.cos(th), np.sin(th)
    Sx = np.array([[np.cos(kx), -1j * np.sin(kx)], [-1j * np.sin(kx), np.cos(kx)]])
    Sy = np.array([[np.cos(ky), -np.sin(ky)], [np.sin(ky), np.cos(ky)]])
    C = np.diag([ch + 1j * sh, ch - 1j * sh])
    return (C @ Sx @ Sy) @ (C @ Sy @ Sx)

def w1(kx, ky, th):
    ev = np.linalg.eigvals(U2pair(kx, ky, th))
    return np.max(-np.angle(ev)) / 2

# ---------- (1) semiclassics with exact lattice dispersion ----------
TH, K0, B1 = 0.10, 0.30, 0.003
dk = 1e-5
def grad(kx, ky):
    return ((w1(kx + dk, ky, TH) - w1(kx - dk, ky, TH)) / (2 * dk),
            (w1(kx, ky + dk, TH) - w1(kx, ky - dk, TH)) / (2 * dk))
kx, ky, x, y = K0, 0.0, 0.0, 0.0
tr = []
for t in range(2300):
    vx, vy = grad(kx, ky)
    tr.append((x, y))
    x += vx; y += vy
    kx += B1 * vy; ky += -B1 * vx
tr = np.array(tr)
A_ = np.c_[2 * tr[:, 0], 2 * tr[:, 1], np.ones(len(tr))]
b_ = tr[:, 0] ** 2 + tr[:, 1] ** 2
sol, *_ = np.linalg.lstsq(A_, b_, rcond=None)
cx, cy = sol[0], sol[1]; r_semi = float(np.sqrt(sol[2] + cx ** 2 + cy ** 2))
r_cont = K0 / B1
results["B_semiclassical_radius"] = r_semi
results["B_continuum_r_p_over_qB"] = r_cont
results["B_lattice_correction_pct"] = 100 * (r_semi - r_cont) / r_cont

# ---------- (2) quantum packet: k-space cyclotron ----------
L = 256
kg = 2 * np.pi * np.fft.fftfreq(L)
KXG, KYG = np.meshgrid(kg, kg, indexing="ij")
xx = np.arange(L) - L // 2
X, Y = np.meshgrid(xx, xx, indexing="ij")

def qca_ky(Bf, th, T, sample=4):
    ch, sh = np.cos(th), np.sin(th)
    env = np.exp(-((KXG - K0) ** 2 + KYG ** 2) * 18.0 ** 2) \
        * np.exp(-1j * (KXG + KYG) * (L // 2))
    ps0 = np.zeros((L, L), complex); ps1 = np.zeros((L, L), complex)
    for i, j in zip(*np.where(abs(env) > 1e-6)):
        ev, V = np.linalg.eig(U2pair(KXG[i, j], KYG[i, j], th))
        w = -np.angle(ev); bb = int(np.argmax(w))
        v = V[:, bb]; v = v * np.exp(-1j * np.angle(v[0]))
        ps0[i, j] = env[i, j] * v[0]; ps1[i, j] = env[i, j] * v[1]
    p0 = np.fft.ifftn(ps0); p1 = np.fft.ifftn(ps1)
    n = np.sqrt((abs(p0) ** 2 + abs(p1) ** 2).sum()); p0 /= n; p1 /= n
    pxp = np.exp(1j * (-Bf) * Y); pxm = np.conj(pxp)
    def sx_(a, b):
        up = inv * (a + b); dn = inv * (a - b)
        up = np.roll(up * pxp, 1, axis=0); dn = np.roll(dn * pxm, -1, axis=0)
        return inv * (up + dn), inv * (up - dn)
    def sy_(a, b):
        up = inv * (a - 1j * b); dn = inv * (a + 1j * b)
        up = np.roll(up, 1, axis=1); dn = np.roll(dn, -1, axis=1)
        return inv * (up + dn), inv * (1j * up - 1j * dn)
    ts, kys = [], []
    for t in range(T):
        if t % sample == 0:
            f0 = np.fft.fftn(p0); f1 = np.fft.fftn(p1)
            pk = abs(f0) ** 2 + abs(f1) ** 2; pk /= pk.sum()
            ts.append(t); kys.append(float((pk * KYG).sum()))
        if t % 2 == 0:
            p0, p1 = sx_(p0, p1); p0, p1 = sy_(p0, p1)
        else:
            p0, p1 = sy_(p0, p1); p0, p1 = sx_(p0, p1)
        p0 = p0 * (ch + 1j * sh); p1 = p1 * (ch - 1j * sh)
    return np.array(ts), np.array(kys)

runs = {}
for Bf in [0.005, 0.010]:
    ts, kys = qca_ky(Bf, 0.0, 420)
    imin = int(np.argmin(kys))
    om = (np.pi / 2) / ts[imin]
    runs[Bf] = (ts, kys, om)
    results[f"B_qca_omega_B{Bf}"] = float(om)
    results[f"B_qca_omega_pred_B{Bf}"] = float(Bf / K0)

# ---------- figure ----------
fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))
axes[0].plot(tr[:, 0], tr[:, 1], color="tab:red", lw=1.4,
             label=f"semiclassics on EXACT lattice dispersion: r={r_semi:.1f}")
th_ = np.linspace(0, 2 * np.pi, 200)
axes[0].plot(cx + r_cont * np.cos(th_), cy + r_cont * np.sin(th_), "k--", lw=1.1,
             label=f"continuum Lorentz force: r=p/qB={r_cont:.0f}")
axes[0].set(xlabel="x", ylabel="y", title="Lorentz force emerges\n"
            f"(lattice correction: {results['B_lattice_correction_pct']:+.1f}%)")
axes[0].set_aspect("equal"); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
cols = {0.005: "tab:blue", 0.010: "tab:red"}
for Bf, (ts, kys, om) in runs.items():
    axes[1].plot(ts, kys, color=cols[Bf], lw=1.3,
                 label=f"QCA <k_y>(t), B={Bf}: w_c={om:.4f} (pred {Bf/K0:.4f})")
    axes[1].plot(ts, -K0 * np.sin((Bf / K0) * ts) * np.exp(-ts / 600), "--",
                 color=cols[Bf], lw=0.8, alpha=0.7)
axes[1].axhline(0, color="gray", lw=0.5)
axes[1].set(xlabel="time step", ylabel="<k_y>",
            title="Quantum packet: kinetic momentum rotates at the relativistic\n"
                  "cyclotron frequency w_c=qB/E (dashed: predicted, with damping envelope)")
axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
fig.suptitle("Gauge fields = position-dependent rule phases: F = qv x B is not put in, it comes out")
fig.tight_layout(); fig.savefig(f"{OUT}/fig8b_cyclotron.png", dpi=140); plt.close(fig)

json.dump(results, open(RES, "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in results.items() if k.startswith("B_")}, indent=1))
