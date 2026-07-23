"""Round 4c — 2+1D self-binding: does a matter lump hold itself together?

2D Dirac walk (2-spinor) with local coin angle theta(x,y):
  x half-step: rotate to sigma_x basis, shift +/-x, rotate back
  y half-step: rotate to sigma_y basis, shift +/-y
  mass coin:   e^{i theta sigma_z}    ->  local light speed c = cos theta
Dynamical field:  theta_tt = cg2 * Lap2D(theta) + kappa * rho   (kappa>0 attractive)

Test: width w(t) of a lump, COUPLED (self-gravity on) vs FREE (kappa=0).
In 2D the dilution is marginal (log), so expect SLOWED dispersal / partial
binding rather than full virialization — the honest 2D prediction; full
binding is the 3D story (r4a self-energy is finite only for d>=3).
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rulespace import core
import subprocess, tempfile, shutil
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = os.path.dirname(os.path.abspath(__file__))
L, T = 128, 900
inv = 1 / np.sqrt(2)
xg = np.arange(L)
X, Y = np.meshgrid(xg, xg, indexing="ij")

def lap2(f):
    return (np.roll(f, 1, 0) + np.roll(f, -1, 0) + np.roll(f, 1, 1) + np.roll(f, -1, 1) - 4 * f)

def step2d(p0, p1, th):
    ch, sh = np.cos(th), np.sin(th)
    # x: sigma_x basis
    up = inv * (p0 + p1); dn = inv * (p0 - p1)
    up = np.roll(up, 1, 0); dn = np.roll(dn, -1, 0)
    p0, p1 = inv * (up + dn), inv * (up - dn)
    # y: sigma_y basis
    up = inv * (p0 - 1j * p1); dn = inv * (p0 + 1j * p1)
    up = np.roll(up, 1, 1); dn = np.roll(dn, -1, 1)
    p0, p1 = inv * (up + dn), inv * (1j * up - 1j * dn)
    # mass coin (sigma_z)
    return p0 * (ch + 1j * sh), p1 * (ch - 1j * sh)

def gauss_lump(x0, y0, sig, k0=0.0):
    r2 = (X - x0) ** 2 + (Y - y0) ** 2
    g = np.exp(-r2 / (2 * sig ** 2)).astype(complex)
    p0 = g; p1 = 0.3 * g
    n = np.sqrt((abs(p0) ** 2 + abs(p1) ** 2).sum())
    return p0 / n, p1 / n

def circ_width(rho):
    zx = (rho * np.exp(2j * np.pi * X / L)).sum(); zy = (rho * np.exp(2j * np.pi * Y / L)).sum()
    Rx, Ry = abs(zx) / rho.sum(), abs(zy) / rho.sum()
    wx = L / (2 * np.pi) * np.sqrt(max(-2 * np.log(max(Rx, 1e-9)), 0))
    wy = L / (2 * np.pi) * np.sqrt(max(-2 * np.log(max(Ry, 1e-9)), 0))
    return 0.5 * (wx + wy)

def run(kappa, cg2=0.4, record=False):
    p0, p1 = gauss_lump(L // 2, L // 2, 6.0)
    th = np.full((L, L), core.TH_REF); th_prev = th.copy()
    ws, frames = [], []
    for t in range(T):
        rho = np.abs(p0) ** 2 + np.abs(p1) ** 2
        ws.append(circ_width(rho))
        if record and t % 12 == 0:
            frames.append((rho.copy(), np.cos(th).copy(), ws[-1]))
        th_new = 2 * th - th_prev + cg2 * lap2(th) + kappa * rho * L * L
        th_new = np.clip(th_new, core.TH_MIN, core.TH_MAX)
        th_prev, th = th, th_new
        p0, p1 = step2d(p0, p1, th)
    return np.array(ws), frames

wf, _ = run(0.0)
wc, frames = run(0.0002, record=True)
res = {"width_free_final": float(wf[-1]), "width_coupled_final": float(wc[-1]),
       "width_free_growth": float(wf[-1] / wf[0]), "width_coupled_growth": float(wc[-1] / wc[0]),
       "binding_ratio": float(wc[-1] / wf[-1])}
json.dump(res, open(f"{DIR}/r4c_results.json", "w"), indent=1)
print(json.dumps(res, indent=1))

# summary figure
fig, ax = plt.subplots(figsize=(6.8, 4.6))
ax.plot(wf, color="gray", lw=1.6, label=f"FREE (no self-gravity): x{wf[-1]/wf[0]:.1f}")
ax.plot(wc, color="tab:blue", lw=1.6, label=f"SELF-GRAVITATING: x{wc[-1]/wc[0]:.1f}")
ax.set(xlabel="time step", ylabel="lump width",
       title=f"2+1D self-binding: self-gravity slows dispersal to {100*wc[-1]/wf[-1]:.0f}% of free\n"
             "(2D is marginal; full binding is the 3D story — see r4a)")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{DIR}/figs/fig_r4c_selfbind.png", dpi=140); plt.close(fig)

# 2D MP4: matter density + geometry contours + width verdict
tmp = tempfile.mkdtemp()
wmin = min(f[2] for f in frames)
for i, (rho, c, w) in enumerate(frames):
    fig = plt.figure(figsize=(9.4, 5.0))
    g = fig.add_gridspec(1, 2, width_ratios=[1.3, 1])
    axm = fig.add_subplot(g[0]); axj = fig.add_subplot(g[1])
    axm.imshow(rho.T, origin="lower", cmap="magma", vmax=np.percentile(rho, 99.6))
    axm.contour(c.T, levels=6, colors="cyan", linewidths=0.5, alpha=0.7)
    axm.set(title="MATTER (magma) + GEOMETRY c(x,y) (cyan)", xticks=[], yticks=[])
    axj.plot(wc[:i * 12 + 1], color="tab:blue", lw=1.4)
    axj.plot(wf[:i * 12 + 1], color="gray", lw=1.0, ls="--")
    axj.set(xlim=(0, T), ylim=(0, max(wf.max(), wc.max()) * 1.05),
            title=f"VERDICT: width now {w:.1f}  (free dashed)", xlabel="t", ylabel="width")
    axj.grid(alpha=0.3)
    fig.suptitle("Emergence of self-gravity in 2+1D: a lump curving its own geometry", fontsize=11)
    fig.set_size_inches(9.4, 5.0)
    fig.savefig(f"{tmp}/f{i:04d}.png", dpi=96); plt.close(fig)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "14",
                "-i", f"{tmp}/f%04d.png", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "24", f"{DIR}/figs/mov_r4c_selfbind_2d.mp4"], check=True)
shutil.rmtree(tmp)
print("2D self-binding movie saved")
