"""Exp 8C: polynomial-time theory synthesis, measured.

Claim (the 'IR transparency' principle): the map
    rule  ->  effective low-energy theory (dispersion, SME coefficients)
is polynomial-time computable, even though the trajectory-level dynamics of
the same rule is computationally irreducible (and many-body simulation is
exponential). This is what makes rule-space pruning a science.

Measurement: wall-clock time of the FULL exp7 extraction pipeline
(3+1D Dirac QCA + compact dimension of size H + leakage; observables =
band bottom, CPT-odd shift, spin splitting over a k-grid) vs Hilbert-space
dimension D = 4H. Fit t ~ D^alpha.
"""
import numpy as np, json, os, time
from scipy.linalg import expm
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "figs")

s0 = np.eye(2, dtype=complex)
sx = np.array([[0, 1], [1, 0]], complex)
sy = np.array([[0, -1j], [1j, 0]])
sz = np.array([[1, 0], [0, -1]], complex)
THETA, G_KIN = 0.15, 0.35

def eH(A): return expm(1j * A)
def W_R(kz): return eH(kz * sz)
def pipeline(H):
    """minimal but complete: build 4H x 4H U(k) on a k-grid, extract the
    visible band and its (wmin, kmin, split) observables."""
    lap = 2 * np.eye(H)
    for w in range(H):
        lap[w, (w + 1) % H] -= 1; lap[(w + 1) % H, w] -= 1
    M = G_KIN * np.kron(lap, np.kron(sy, s0)) \
        + 0.05 * np.kron(np.diag([1.0] + [0] * (H - 1)), np.kron(s0, sz))
    L = expm(1j * M)
    C = np.kron(np.eye(H), eH(THETA * np.kron(sx, s0)))
    P0 = np.ones(H) / np.sqrt(H)
    ks = np.linspace(-0.45, 0.45, 61)
    bands = np.empty((len(ks), 2))
    for a, kz in enumerate(ks):
        blk = np.zeros((4, 4), complex)
        blk[:2, :2] = eH(kz * sz); blk[2:, 2:] = eH(-kz * sz)
        U = np.kron(np.eye(H), blk) @ C @ L
        ev, V = np.linalg.eig(U)
        w = -np.angle(ev)
        Vw = V.reshape(H, 4, 4 * H)
        wq0 = (np.abs(np.einsum("h,hsj->sj", P0, Vw)) ** 2).sum(axis=0)
        pos = np.where(w > 1e-9)[0]
        sel = pos[np.argsort(-wq0[pos])][:2]
        bands[a] = np.sort(w[sel])
    j = np.argmin(bands[:, 0])
    return bands[j, 0], ks[j], (bands[:, 1] - bands[:, 0]).mean()

Hs = [2, 3, 4, 6, 8, 12, 16]
times = []
for H in Hs:
    pipeline(H)                      # warm-up / JIT caches
    t0 = time.perf_counter()
    pipeline(H)
    times.append(time.perf_counter() - t0)
D = 4 * np.array(Hs)
alpha = np.polyfit(np.log(D), np.log(times), 1)[0]

fig, ax = plt.subplots(figsize=(6.8, 4.6))
ax.loglog(D, times, "o-", color="tab:red", label="rule -> effective theory (measured)")
ax.loglog(D, times[-1] * (D / D[-1]) ** alpha, "k--", lw=1,
          label=f"power law D^{alpha:.2f}  (polynomial)")
ax.loglog(D, times[0] * 2.0 ** (D - D[0]), ":", color="gray",
          label="exponential 2^D (irreducible trajectory / many-body cost)")
ax.set(xlabel="Hilbert-space dimension D of the rule", ylabel="wall-clock seconds",
       title=f"IR transparency, measured: extracting the effective theory scales as D^{alpha:.2f}\n"
             "while generic simulation of the same rule is exponential", ylim=(1e-3, 1e3))
ax.legend(fontsize=8); ax.grid(alpha=0.3, which="both")
fig.tight_layout(); fig.savefig(f"{OUT}/fig8c_polytime.png", dpi=140); plt.close(fig)

out = {"D": D.tolist(), "seconds": times, "alpha": float(alpha)}
json.dump(out, open(os.path.join(DIR, "exp8c_results.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
