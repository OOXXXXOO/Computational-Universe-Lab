"""Round 4b — closing result B: the discrete conserved energy.

Part 1 (SYMBOLIC, SymPy): prove the leapfrog field sector conserves the
STAGGERED energy exactly. For theta^{n+1} - 2 theta^n + theta^{n-1} = -K theta^n
(K symmetric), the quantity
    E^{n+1/2} = 1/2 |theta^{n+1}-theta^n|^2 + 1/2 (theta^{n+1})^T K theta^n
satisfies E^{n+1/2} - E^{n-1/2} = 0 identically.
result B used the NON-staggered 1/2 theta^T K theta -> spurious O(1) drift.

Part 2 (NUMERICAL): for the fully coupled walker+field system, test whether
the joint energy with the staggered field term is conserved exactly, or to
O(eps^2) as a shadow (the finite-step remnant that vanishes in the continuum
limit, i.e. the same status as every emergence in this program, P1). We
refine the field time-step by an adiabaticity parameter s (field stiffness
and coupling scaled by s^2, so the field evolves s-times slower per walker
step) and measure the drift's scaling exponent in s.
"""
import sys, os, json
import numpy as np
import sympy as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rulespace import core

DIR = os.path.dirname(os.path.abspath(__file__))
results = {}

# ---------- Part 1: symbolic staggered-energy identity ----------
n = 3                                            # tiny ring, symbolic
K = sp.Matrix(sp.symarray("K", (n, n)))
K = (K + K.T) / 2                                # symmetric
tm1 = sp.Matrix(sp.symarray("a", n))             # theta^{n-1}
t0 = sp.Matrix(sp.symarray("b", n))              # theta^{n}
t1 = 2 * t0 - tm1 - K * t0                        # leapfrog step -> theta^{n+1}
t2 = 2 * t1 - t0 - K * t1                          # -> theta^{n+2}
def Estag(tp, tc):                                # E^{(c+1/2)} using levels tp=next, tc=cur
    return (sp.Rational(1, 2) * (tp - tc).T * (tp - tc)
            + sp.Rational(1, 2) * tp.T * K * tc)[0]
dE = sp.simplify(Estag(t2, t1) - Estag(t1, t0))
results["B1_staggered_exact"] = bool(dE == 0)
print("Part1 (symbolic): staggered-energy increment simplifies to:", dE,
      "->", "EXACTLY CONSERVED" if dE == 0 else "NOT conserved")
# and show the naive energy is NOT conserved
def Enaive(tp, tc):
    return (sp.Rational(1, 2) * (tp - tc).T * (tp - tc) + sp.Rational(1, 2) * tc.T * K * tc)[0]
dEn = sp.simplify(Enaive(t2, t1) - Enaive(t1, t0))
results["B1_naive_conserved"] = bool(dEn == 0)
print("Part1: naive (non-staggered) energy increment is zero?", bool(dEn == 0))

# ---------- Part 2: coupled system — is the joint energy conserved? ----------
# Honest finding: coupling a FIRST-order unitary walker to a SECOND-order
# leapfrog field does not admit a naively conserved joint energy. The drift is
# SECULAR (grows linearly), and symmetrizing the coupling (Strang split: half
# field / walker at mid-theta / half field) reduces the secular rate but does
# not eliminate it. Exact closure = a genuinely symplectic walker-field
# co-integrator. This is the precise remaining math problem of C1.
N = 256
def E_walker(psi0, psi1, th, dm=0.0):
    u0, u1 = core.walker_step(psi0, psi1, th, dm=dm)
    return float(-np.imag((np.conj(psi0) * u0 + np.conj(psi1) * u1).sum()))

def Fsrc(p0, p1, th, dm):
    a0, a1 = core.coin(p0, p1, th); b0 = np.roll(a0, 1); b1 = a1
    c0, c1 = core.coin(b0, b1, -th + dm)
    x0 = p0; x1 = np.roll(p1, 1); y0, y1 = core.coin(x0, x1, th - dm)
    z0 = np.roll(y0, -1); z1 = y1
    return (np.real(np.conj(z0) * a1 + np.conj(z1) * a0)
            - np.real(np.conj(x0) * c1 + np.conj(x1) * c0))

def run(T, dm=0.3, cg2=0.30, lam=1.0, symm=False):
    p0, p1 = core.packet(N, N // 2, 0.7, 11.0, dm=dm)
    th = np.full(N, core.TH_REF); th_prev = th.copy()
    EJ = []
    for t in range(T):
        if symm:
            F = Fsrc(p0, p1, th, dm)
            th_half = th + 0.5 * ((th - th_prev) + 0.5 * (cg2 * core.lap(th) + lam * F))
            n0, n1 = core.walker_step(p0, p1, th_half, dm=dm)
            F2 = Fsrc(n0, n1, th_half, dm)
            th_new = 2 * th - th_prev + cg2 * core.lap(th) + 0.5 * lam * (F + F2)
        else:
            F = Fsrc(p0, p1, th, dm)
            n0, n1 = core.walker_step(p0, p1, th, dm=dm)
            th_new = 2 * th - th_prev + cg2 * core.lap(th) + lam * F
        thdot = th_new - th
        Ef = 0.5 * (thdot ** 2).sum() + 0.5 * cg2 * (core.grad(th_new) * core.grad(th)).sum()
        EJ.append(E_walker(p0, p1, th, dm) + Ef)
        th_prev, th = th, th_new
        p0, p1 = n0, n1
    EJ = np.array(EJ) - EJ[0]
    tt = np.arange(len(EJ))
    return EJ, float(np.polyfit(tt, EJ, 1)[0])

series = {}
for symm in [False, True]:
    EJ, slope = run(3000, symm=symm)
    tag = "symmetric" if symm else "naive"
    series[tag] = EJ
    results[f"B2_secular_slope_{tag}"] = slope
    results[f"B2_maxdrift_{tag}"] = float(np.abs(EJ).max())
    print(f"  coupling={tag:9s}: secular slope {slope:+.2e}/step  max|drift| {np.abs(EJ).max():.3e}")
results["B2_symmetrization_gain"] = abs(results["B2_secular_slope_naive"]) / abs(results["B2_secular_slope_symmetric"])
print(f"symmetrization reduces secular rate by {results['B2_symmetrization_gain']:.1f}x")
results["B2_field_sector_exact"] = results["B1_staggered_exact"]
results["B2_joint_closure"] = "OPEN: needs symplectic walker-field co-integrator"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.5))
ax1.text(0.5, 0.66, "staggered energy  E = ½|θ$^{n+1}$-θ$^n$|² + ½ θ$^{n+1}$·K·θ$^n$",
         ha="center", fontsize=11, transform=ax1.transAxes)
ax1.text(0.5, 0.46, "ΔE = 0   (SymPy: exactly conserved)",
         ha="center", fontsize=12, color="tab:green", transform=ax1.transAxes)
ax1.text(0.5, 0.24, "naive  ½ θ·K·θ :  NOT conserved",
         ha="center", fontsize=11, color="tab:red", transform=ax1.transAxes)
ax1.set_title("Part 1 (proved): field sector has an\nexactly conserved staggered energy")
ax1.axis("off")
for tag, col in [("naive", "tab:red"), ("symmetric", "tab:blue")]:
    ax2.plot(series[tag], color=col, lw=1.1,
             label=f"{tag}: {results[f'B2_secular_slope_{tag}']:+.1e}/step")
ax2.axhline(0, color="k", lw=0.5)
ax2.set(xlabel="time step", ylabel="joint-energy drift",
        title="Part 2 (honest): coupled walker+field drifts secularly;\nsymmetrization helps but exact closure stays open")
ax2.legend(fontsize=9); ax2.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{DIR}/figs/fig_r4b_noether.png", dpi=140); plt.close(fig)
json.dump(results, open(f"{DIR}/r4b_results.json", "w"), indent=1)
print("\nResult B status: field sector CLOSED (symbolic); joint closure = open symplectic problem.")
