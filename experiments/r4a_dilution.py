"""Round 4a — the geometric dilution law: why 3+1D is a phase transition.

Static field of a localized source obeys the lattice Poisson equation
    c^2 (lattice Laplacian) theta = -source,
solved EXACTLY in Fourier space (torus). Measure the radial profile
theta(r) - theta_infinity and its falloff.

Continuum Green's functions in d spatial dimensions:
    d=1:  theta ~ -|r|          (GROWS: no dilution)   -> self-energy diverges
    d=2:  theta ~ +log r        (marginal)
    d>=3: theta ~ -r^{-(d-2)}   (localized well)       -> self-binding possible

This single law explains (i) why the 1+1D star-formation failed (energy
accumulates), and (ii) predicts self-binding turns on at d>=3 (marginal at
d=2). It is the quantitative content of "the revolution waits for 3+1D".
Also compute the self-energy E_self = (1/2) integral source*theta: finite
iff d>=3.
"""
import numpy as np, json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = os.path.dirname(os.path.abspath(__file__))
results = {}

def solve_poisson(shape, src, c2=1.0):
    """c2 * Lap theta = -src  on a torus, zero-mode removed."""
    d = len(shape)
    ks = [2 * np.pi * np.fft.fftfreq(n) for n in shape]
    K = np.meshgrid(*ks, indexing="ij")
    lam = sum(2 - 2 * np.cos(k) for k in K)          # -lattice Laplacian eigenvalue >=0
    S = np.fft.fftn(src)
    denom = c2 * lam
    Th = np.zeros_like(S)
    nz = denom > 1e-12
    Th[nz] = S[nz] / denom[nz]                        # since -Lap = lam, c2*Lap th=-src -> c2 lam th = src
    Th[~nz] = 0.0
    return np.real(np.fft.ifftn(Th))

def radial_profile(theta, center):
    idx = np.indices(theta.shape)
    r = np.sqrt(sum((idx[i] - center[i]) ** 2 for i in range(theta.ndim)))
    r = r.ravel(); v = theta.ravel()
    order = np.argsort(r)
    r, v = r[order], v[order]
    # bin
    rmax = min(theta.shape) // 2
    bins = np.linspace(1, rmax, 40)
    prof = [v[(r >= bins[i]) & (r < bins[i + 1])].mean() for i in range(len(bins) - 1)]
    rc = 0.5 * (bins[:-1] + bins[1:])
    return rc, np.array(prof)

sizes = {1: (2048,), 2: (256, 256), 3: (64, 64, 64)}
blob = {1: 6.0, 2: 4.0, 3: 3.0}
fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
for d, ax in zip([1, 2, 3], axes):
    shape = sizes[d]
    center = tuple(n // 2 for n in shape)
    idx = np.indices(shape)
    r2 = sum((idx[i] - center[i]) ** 2 for i in range(d))
    src = np.exp(-r2 / (2 * blob[d] ** 2))
    src = src - src.mean()                           # remove zero mode (neutralizing bg)
    theta = solve_poisson(shape, src)
    if d == 1:
        x = np.arange(shape[0]) - center[0]
        prof_r = np.abs(x[center[0]:]); prof_v = theta[center[0]:]
        rc, prof = prof_r[3:shape[0] // 2], prof_v[3:shape[0] // 2]
    else:
        rc, prof = radial_profile(theta, center)
    prof = prof - prof[-1]                            # subtract far value
    # measure falloff: fit in the window r in [0.15,0.45]*L away from source & edge
    L = min(shape)
    win = (rc > 0.08 * L) & (rc < 0.4 * L) & np.isfinite(prof)
    depth0 = theta[center] - theta.mean()
    self_energy = float(0.5 * (src * theta).sum())
    results[f"d{d}_self_energy"] = self_energy
    results[f"d{d}_well_depth"] = float(depth0)
    # fit model per expected form
    if d == 1:
        p = np.polyfit(rc[win], prof[win], 1)
        results["d1_slope_linear"] = float(p[0])
        ax.plot(rc, prof, "o", ms=3, color="tab:red", label="lattice solution")
        ax.plot(rc[win], np.polyval(p, rc[win]), "k--", label=f"linear GROWTH, slope {p[0]:.3f}")
        ax.set_title(f"d=1: theta ~ -|r| (NO dilution)\nself-energy = {self_energy:.1f} (diverges with box)")
    elif d == 2:
        p = np.polyfit(np.log(rc[win]), prof[win], 1)
        results["d2_log_coeff"] = float(p[0])
        ax.semilogx(rc, prof, "o", ms=3, color="tab:orange", label="lattice solution")
        ax.semilogx(rc[win], np.polyval(p, np.log(rc[win])), "k--", label=f"log r, coeff {p[0]:.3f}")
        ax.set_title(f"d=2: theta ~ log r (marginal)\nself-energy = {self_energy:.2f}")
    else:
        pos = prof - prof.min() + 1e-6
        p = np.polyfit(np.log(rc[win]), np.log(np.abs(prof[win] - prof[win][-1]) + 1e-9), 1)
        # cleaner: fit theta ~ A r^-(d-2) = A/r
        A = np.polyfit(1.0 / rc[win], prof[win], 1)
        results["d3_power"] = float(p[0]); results["d3_invr_slope"] = float(A[0])
        ax.plot(rc, prof, "o", ms=3, color="tab:blue", label="lattice solution")
        rr = np.linspace(rc[win][0], rc[win][-1], 50)
        ax.plot(rr, A[0] / rr + A[1], "k--", label=f"~ 1/r fit (dilution!)")
        ax.set_title(f"d=3: theta ~ -1/r (localized well)\nself-energy = {self_energy:.3f} (FINITE)")
    ax.set(xlabel="r (lattice)", ylabel="theta(r) - theta_far"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

fig.suptitle("Geometric dilution law: a static source's field falls as r^-(d-2) — 1D grows, 2D marginal, 3D localizes", fontsize=12)
fig.tight_layout(); fig.savefig(f"{DIR}/figs/fig_r4a_dilution.png", dpi=140); plt.close(fig)

# self-energy vs box size: the divergence test (d=1) vs finiteness (d=3)
for d in [1, 3]:
    ses = []
    Ls = [64, 96, 128, 192, 256] if d == 1 else [24, 32, 40, 48, 56]
    for L in Ls:
        shape = (L,) * d
        center = tuple(n // 2 for n in shape)
        idx = np.indices(shape)
        r2 = sum((idx[i] - center[i]) ** 2 for i in range(d))
        src = np.exp(-r2 / (2 * blob[d] ** 2)); src = src - src.mean()
        th = solve_poisson(shape, src)
        ses.append(float(0.5 * (src * th).sum()))
    results[f"d{d}_selfE_vs_L"] = {str(L): s for L, s in zip(Ls, ses)}
    print(f"d={d} self-energy vs box L={Ls}: {[round(s,3) for s in ses]}")

json.dump(results, open(f"{DIR}/r4a_results.json", "w"), indent=1)
print(json.dumps({k: v for k, v in results.items() if "vs_L" not in k}, indent=1))
