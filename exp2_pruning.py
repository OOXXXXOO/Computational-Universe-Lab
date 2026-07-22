"""Exp 2: constraint pruning of rule space.

(a) Classical side: all 256 elementary CA. Constraint = reversibility
    (information conservation, the classical shadow of unitarity).
    Known result: only 6 survive and all are trivial -> classical local 1D
    reversible dynamics carries no interesting physics -> forces quantum rules.

(b) Quantum side: split-step QCA family U(k) = S- C(t2) S+ C(t1),
    dispersion cos w(k) = cos t1 cos t2 cos k - sin t1 sin t2.
    Prune parameter plane (t1,t2) by low-energy Lorentz deviation:
    fit w ~ sqrt(m^2 + c^2 k^2) near k=0, measure max residual for |k|<K.
    Survivors = thin manifold (the Dirac family).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json, os

OUT = os.path.join(os.path.dirname(__file__), "figs")
os.makedirs(OUT, exist_ok=True)
results = {}

# ---------- (a) classical: reversibility prunes 256 -> 6 trivial ----------
def rule_table(r):
    return np.array([(r >> i) & 1 for i in range(8)], dtype=np.uint8)

def is_reversible(r):
    """exact test on all cyclic configurations up to length L: injective global map"""
    tab = rule_table(r)
    for L in range(3, 11):
        seen = {}
        for cfg in range(2 ** L):
            bits = np.array([(cfg >> i) & 1 for i in range(L)], dtype=np.uint8)
            idx = (np.roll(bits, 1) << 2) | (bits << 1) | np.roll(bits, -1)
            out = tuple(tab[idx])
            if out in seen:
                return False
            seen[out] = cfg
    return True

rev = [r for r in range(256) if is_reversible(r)]
results["exp2_reversible_rules"] = rev

grid = np.zeros((16, 16))
for r in range(256):
    grid[r // 16, r % 16] = 1 if r in rev else 0
fig, ax = plt.subplots(figsize=(6.2, 5.8))
ax.imshow(grid, cmap="Greys", vmin=-0.15, vmax=1.6)
for r in rev:
    ax.text(r % 16, r // 16, str(r), ha="center", va="center", fontsize=7, color="darkred")
ax.set(title=f"256 elementary CA, reversibility prune -> {len(rev)} survive\n"
             "(all trivial: identity / shift / complement)",
       xlabel="rule mod 16", ylabel="rule // 16")
fig.tight_layout(); fig.savefig(f"{OUT}/fig2a_classical_prune.png", dpi=140); plt.close(fig)

# what dynamics do survivors have? classify
names = {204: "identity", 51: "NOT", 170: "shift left", 240: "shift right",
         85: "shift+NOT", 15: "shift+NOT"}
results["exp2_survivor_types"] = {str(r): names.get(r, "?") for r in rev}

# ---------- (b) quantum: Lorentz prune of split-step plane ----------
K = 0.6                      # low-energy window (lattice units)
k = np.linspace(-K, K, 121)
n = 241
t1s = np.linspace(-np.pi / 2, np.pi / 2, n)
t2s = np.linspace(-np.pi / 2, np.pi / 2, n)
T1, T2 = np.meshgrid(t1s, t2s)

def lorentz_residual(t1, t2):
    cw = np.cos(t1) * np.cos(t2) * np.cos(k) - np.sin(t1) * np.sin(t2)
    if np.any(np.abs(cw) > 1 - 1e-12):
        return np.nan                      # gapless-degenerate / band edge in window
    w = np.arccos(cw)
    m = w[len(k) // 2]
    # effective c^2 from curvature at k=0
    c2 = (w[len(k) // 2 + 1] ** 2 - m ** 2) / (k[len(k) // 2 + 1] ** 2)
    if c2 <= 0:
        return np.nan
    fit = np.sqrt(m ** 2 + c2 * k ** 2)
    return np.max(np.abs(w - fit)) / K     # normalized anharmonicity

R = np.zeros_like(T1)
for i in range(n):
    for j in range(n):
        R[i, j] = lorentz_residual(T1[i, j], T2[i, j])

tol = 1e-4
survive = (R < tol)
frac = survive.sum() / np.isfinite(R).sum()
results["exp2_lorentz_tol"] = tol
results["exp2_surviving_fraction"] = float(frac)

fig, ax = plt.subplots(figsize=(6.6, 5.6))
im = ax.imshow(np.log10(R), origin="lower", cmap="viridis",
               extent=[-np.pi / 2, np.pi / 2, -np.pi / 2, np.pi / 2], aspect="auto")
ax.contour(T1, T2, R, levels=[tol], colors="red", linewidths=1.4)
ax.plot(t1s, -t1s, "w--", lw=1, label="massless line t2=-t1 (Weyl)")
ax.set(xlabel="theta1", ylabel="theta2",
       title=f"Split-step QCA plane: log10 Lorentz deviation (|k|<{K})\n"
             f"red contour = tolerance {tol}; surviving fraction = {frac:.3f}")
fig.colorbar(im, ax=ax, label="log10 max residual / K")
ax.legend(loc="upper right", fontsize=8)
fig.tight_layout(); fig.savefig(f"{OUT}/fig2b_quantum_prune.png", dpi=140); plt.close(fig)

# survival fraction vs tolerance (how sharp is the knife)
tols = np.geomspace(1e-5, 1e-1, 17)
fracs = [(R < t).sum() / np.isfinite(R).sum() for t in tols]
fig, ax = plt.subplots(figsize=(6.0, 4.2))
ax.loglog(tols, fracs, "o-")
ax.set(xlabel="Lorentz-violation tolerance", ylabel="surviving fraction of rule plane",
       title="Experimental precision directly shrinks viable rule space")
ax.grid(True, which="both", alpha=0.3)
fig.tight_layout(); fig.savefig(f"{OUT}/fig2c_tolerance.png", dpi=140); plt.close(fig)
results["exp2_frac_vs_tol"] = {f"{t:.1e}": float(f) for t, f in zip(tols, fracs)}

print(json.dumps(results, indent=1))
