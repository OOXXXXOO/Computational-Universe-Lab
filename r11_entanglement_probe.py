"""R11 — entanglement probe: Calabrese-Cardy central charge from the QCA.

PURPOSE (J6 pre-study). The program's next real-experiment shear after the
GW-speed judge is an ENTANGLEMENT judge: a lawful matter sector should carry
the entanglement structure of its continuum CFT. The cheapest sharp invariant
is the central charge c, extracted from ground-state block entropy via
Calabrese-Cardy (periodic chain, block length l):

    S(l) = (c/3) * ln[ (L/pi) * sin(pi*l/L) ] + c1

This file is the standalone prototype on the 1D split-step Dirac walk:

  * quasi-energy bands of U(k) = S(k) C(theta); mass = theta (gap 2*theta
    around omega = 0, exactly the program's standard dispersion
    cos(omega) = cos(theta) cos(k));
  * Dirac-sea ground state = fill all omega < 0 modes; EXACT free-fermion
    entanglement via the Peschel correlation-matrix method (no MC, no MPS);
  * certificates:
      C1  massless walk  -> c_fit ~= 1   (one Dirac cone at the Fermi level)
      C2  gapped walk    -> area law, c_fit ~= 0  (the judge has teeth)
      C3  crossover: c(theta) collapses 1 -> 0 as the gap opens, with the
          finite-size scale xi ~ 1/theta crossing L (honest: this is why a
          CAMPAIGN judge must fix L*theta_min, noted for J6).

HONEST TIERING (unchanged from the strategy answer): central charge via CC
scaling is the REACHABLE rung of the holography ladder (Yin-Xi-adjacent:
c is the same object that organizes AdS3/CFT2 partition functions). RT-toy
area laws on hyperbolic couplings = conceivable next. Exact microstate
counting / one-loop duality tests = NOT reachable by these numerics.

Method is exact and CPU-cheap (largest eigh is 2l x 2l <= 512): no GPU needed.
Run:  python r11_entanglement_probe.py        (~seconds, writes r11_results.json
      + figs/fig_r11_entanglement.png)
"""
import json
import os

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(DIR, "figs")


# ----------------------------------------------------------------------
# SPLIT-STEP walk (the program's standard family, core convention
# psi_{t+1} = S_- C2 S_+ C1):  U(k) = S_-(k) C(th2) S_+(k) C(th1)
#   S_+ = diag(e^{ik}, 1),  S_- = diag(1, e^{-ik})
# dispersion: cos(omega) = cos(th1)cos(th2)cos(k) - sin(th1)sin(th2)
#   gap at omega=0  ~ 2|th1+th2|   (the physical mass m = th1+th2)
#   gap at omega=pi ~ 2|th1-th2|   (kept OPEN to kill the pi-doubler)
#
# WHY split-step and not the single coin U=S C: quasi-energy is periodic, so
# filling omega<0 cuts the zone at BOTH omega=0 and omega=pi. The single-coin
# sea therefore has TWO Dirac cones and measures c = 2 (verified: 2.0005) --
# the pi-doubler is a Floquet/QCA artifact, and the split-step second angle
# is exactly the knob that gaps it away, leaving the single physical cone.
# ----------------------------------------------------------------------
TH2 = 0.5      # fixed second coin angle: pi-gap 2|m - 2*TH2| stays open


def walk_modes(L, m, th2=TH2):
    """Bloch modes of the split-step U(k), mass m = th1+th2 (th1 = m-th2).
    Returns ks, omegas (L,2), eigenvectors V (L,2,2)."""
    ks = 2.0 * np.pi * np.fft.fftfreq(L)
    th1 = m - th2

    def coin(t):
        return np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])

    C1, C2 = coin(th1), coin(th2)
    omegas = np.empty((L, 2))
    V = np.empty((L, 2, 2), complex)
    for j, k in enumerate(ks):
        Sp = np.diag([np.exp(1j * k), 1.0])
        Sm = np.diag([1.0, np.exp(-1j * k)])
        U = Sm @ C2 @ Sp @ C1
        ev, W = np.linalg.eig(U)
        om = -np.angle(ev)                      # U = e^{-i omega}
        order = np.argsort(om)
        omegas[j] = om[order]
        W = W[:, order]
        W /= np.linalg.norm(W, axis=0, keepdims=True)
        V[j] = W
    return ks, omegas, V


def sea_correlation_kernel(L, m):
    """C(x-y)_{ss'} for the Dirac-sea ground state (all omega<0 filled),
    via FFT of the occupied band projector. Returns (L,2,2) complex."""
    ks, om, V = walk_modes(L, m)
    Pk = np.zeros((L, 2, 2), complex)
    for j in range(L):
        for a in range(2):
            if om[j, a] < 0.0:
                v = V[j, :, a]
                Pk[j] += np.outer(v, v.conj())
    # C_{(x,s),(y,s')} = (1/L) sum_k e^{ik(x-y)} P_k[s,s']
    return np.fft.ifft(Pk, axis=0)              # kernel over d = x-y


def block_entropy(kernel, ells):
    """Exact free-fermion block entropies via Peschel: eigenvalues nu of the
    block-restricted correlation matrix -> S = -sum nu ln nu + (1-nu)ln(1-nu)."""
    L = kernel.shape[0]
    out = []
    lmax = max(ells)
    # assemble the largest block once; sub-blocks are leading principal minors
    Cb = np.empty((2 * lmax, 2 * lmax), complex)
    for x in range(lmax):
        for y in range(lmax):
            Cb[2 * x:2 * x + 2, 2 * y:2 * y + 2] = kernel[(x - y) % L]
    for l in ells:
        nu = np.linalg.eigvalsh(Cb[: 2 * l, : 2 * l])
        nu = np.clip(nu.real, 1e-12, 1.0 - 1e-12)
        out.append(float(-np.sum(nu * np.log(nu) + (1 - nu) * np.log(1 - nu))))
    return np.array(out)


def fit_central_charge(L, ells, S):
    """least-squares fit S = (c/3)*x + c1 with x = ln[(L/pi) sin(pi l/L)]."""
    x = np.log((L / np.pi) * np.sin(np.pi * np.asarray(ells) / L))
    A = np.vstack([x / 3.0, np.ones_like(x)]).T
    (c, c1), res, *_ = np.linalg.lstsq(A, S, rcond=None)
    ss_tot = np.sum((S - S.mean()) ** 2)
    r2 = 1.0 - (res[0] / ss_tot if len(res) and ss_tot > 0 else 0.0)
    return float(c), float(c1), float(r2)


def measure_c(L, m, ells=None):
    if ells is None:
        # even blocks only (kills free-fermion parity oscillations), keep away
        # from the tiny-l lattice regime
        ells = [l for l in range(6, L // 2 + 1, 2)]
    ker = sea_correlation_kernel(L, m)
    S = block_entropy(ker, ells)
    c, c1, r2 = fit_central_charge(L, ells, S)
    return {"c": c, "c1": c1, "r2": r2, "ells": list(ells), "S": S.tolist()}


# ----------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(FIGS, exist_ok=True)
    L = 256
    print("R11 entanglement probe: Calabrese-Cardy c from the Dirac-sea QCA")
    print("=" * 68)

    # C1: massless point (m=0) -> ONE Dirac cone (pi-doubler gapped) -> c = 1
    m0 = measure_c(L, m=0.0)
    print(f"C1 massless  : c = {m0['c']:.4f}  (target 1, r2 = {m0['r2']:.6f})")

    # C2: gapped walk -> area law. fit on large blocks only (l >> xi ~ 1/m)
    mg = measure_c(L, m=0.6, ells=list(range(32, L // 2 + 1, 2)))
    print(f"C2 gapped 0.6: c = {mg['c']:.4f}  (target 0: area law -> teeth)")

    # C3: crossover c(m) -- the gap opens, c collapses 1 -> 0
    thetas = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.6]
    sweep = []
    for th in thetas:
        mm = measure_c(L, th, ells=list(range(16, L // 2 + 1, 2)))
        sweep.append(mm["c"])
    print("C3 crossover : mass  ", "  ".join(f"{t:5.2f}" for t in thetas))
    print("               c_fit ", "  ".join(f"{c:5.3f}" for c in sweep))

    ok1 = abs(m0["c"] - 1.0) < 0.03 and m0["r2"] > 0.999
    ok2 = abs(mg["c"]) < 0.05
    ok3 = sweep[0] > 0.97 and sweep[-1] < 0.05 and all(
        sweep[i] >= sweep[i + 1] - 0.02 for i in range(len(sweep) - 1))
    print(f"\ncertificates: C1 {'PASS' if ok1 else 'FAIL'}   "
          f"C2 {'PASS' if ok2 else 'FAIL'}   C3 {'PASS' if ok3 else 'FAIL'}")

    # figure: S(l) profiles + c(theta)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        x0 = np.log((L / np.pi) * np.sin(np.pi * np.array(m0["ells"]) / L))
        ax[0].plot(x0, m0["S"], "o", ms=3, label=f"massless (c={m0['c']:.3f})")
        ax[0].plot(x0, np.array(x0) * m0["c"] / 3 + m0["c1"], "-", lw=1)
        xg = np.log((L / np.pi) * np.sin(np.pi * np.array(mg["ells"]) / L))
        ax[0].plot(xg, mg["S"], "s", ms=3, label=f"gapped 0.6 (c={mg['c']:.3f})")
        ax[0].set_xlabel(r"$\ln[(L/\pi)\sin(\pi \ell/L)]$")
        ax[0].set_ylabel(r"$S(\ell)$")
        ax[0].legend(); ax[0].set_title("Calabrese-Cardy fit (L=256, exact)")
        ax[1].semilogx(np.array(thetas) + 1e-3, sweep, "o-")
        ax[1].axhline(1.0, ls=":", c="gray"); ax[1].axhline(0.0, ls=":", c="gray")
        ax[1].set_xlabel(r"$\theta$ (mass)"); ax[1].set_ylabel(r"$c_{\rm fit}$")
        ax[1].set_title(r"gap opens $\Rightarrow$ $c$ collapses ($\xi\sim1/\theta$ vs $L$)")
        fig.tight_layout()
        fig.savefig(os.path.join(FIGS, "fig_r11_entanglement.png"), dpi=140)
        print("wrote figs/fig_r11_entanglement.png")
    except Exception as e:                       # matplotlib optional
        print("figure skipped:", e)

    json.dump({"L": L, "massless": m0, "gapped": mg,
               "sweep": {"theta": thetas, "c": sweep},
               "certificates": {"C1": ok1, "C2": ok2, "C3": ok3}},
              open(os.path.join(DIR, "r11_results.json"), "w"), indent=1)
    print("wrote r11_results.json")
