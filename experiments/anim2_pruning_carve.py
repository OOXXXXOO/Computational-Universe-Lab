"""Animation 2: experimental pruning carving rule space, live.
Split-step QCA plane (theta1, theta2); as the Lorentz-violation tolerance
tightens (= experiments improve), the surviving manifold is carved out.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
n, K, nk = 181, 0.6, 41
t = np.linspace(-np.pi / 2, np.pi / 2, n)
T1, T2 = np.meshgrid(t, t)
k = np.linspace(-K, K, nk)

# vectorized residual computation
A = (np.cos(T1) * np.cos(T2))[..., None]
B = (np.sin(T1) * np.sin(T2))[..., None]
cw = A * np.cos(k) - B
bad = np.any(np.abs(cw) > 1 - 1e-12, axis=-1)
w = np.arccos(np.clip(cw, -1, 1))
mid = nk // 2
m0 = w[..., mid]
c2 = (w[..., mid + 1] ** 2 - m0 ** 2) / (k[mid + 1] ** 2)
fit = np.sqrt(np.maximum(m0[..., None] ** 2 + c2[..., None] * k ** 2, 0))
R = np.max(np.abs(w - fit), axis=-1) / K
R[bad | (c2 <= 0)] = np.nan

tols = np.geomspace(1e-1, 1e-5, 48)
finite = np.isfinite(R)

fig, ax = plt.subplots(figsize=(7.2, 6.2))
base = ax.imshow(np.log10(np.where(finite, R, np.nan)), origin="lower", cmap="Greys",
                 extent=[-np.pi/2, np.pi/2, -np.pi/2, np.pi/2], alpha=0.55, aspect="auto")
mask_img = ax.imshow(np.zeros((n, n, 4)), origin="lower",
                     extent=[-np.pi/2, np.pi/2, -np.pi/2, np.pi/2], aspect="auto")
ax.plot(t, -t, "b--", lw=1, label="massless Weyl line $\\theta_2=-\\theta_1$")
ax.set(xlabel="$\\theta_1$", ylabel="$\\theta_2$")
ax.legend(loc="upper right", fontsize=9)
txt = ax.text(0.02, 0.02, "", transform=ax.transAxes, fontsize=12,
              va="bottom", color="darkred",
              bbox=dict(fc="white", alpha=0.85, ec="none"))

def update(f):
    tol = tols[f]
    surv = (R < tol) & finite
    rgba = np.zeros((n, n, 4))
    rgba[surv] = [0.95, 0.15, 0.15, 0.95]
    mask_img.set_data(rgba)
    frac = surv.sum() / finite.sum()
    txt.set_text(f"experimental precision: {tol:.1e}\n"
                 f"surviving rules: {100*frac:.2f}%")
    return mask_img, txt

ani = FuncAnimation(fig, update, frames=len(tols), blit=True)
ax.set_title("Emergence protocol II: pruning — every order of magnitude of experimental\n"
             "precision carves rule space down to the relativistic manifold", fontsize=10)
fig.tight_layout()
ani.save(f"{OUT}/anim2_pruning.gif", writer="pillow", fps=8)
print("anim2 done")
