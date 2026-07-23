"""R12 — BTZ/thermal-CFT correspondence of the QCA Dirac sea.

THE LADDER (Yin-Xi-adjacent, honest rungs):
  R11  c extraction (CC log law)            -> DONE, c = 1 exact
  R11b factor bookkeeping (pre-reg c = 2)   -> DONE
  R12  THIS: black-hole-entropy SCALING toy -- the "conceivable" rung.

PHYSICS. Put the split-step walk's fermions at temperature 1/beta
(Fermi-Dirac filling of the quasi-energy bands). Thermal CFT predicts

    S(l) = (c/3) * ln[ (beta v / pi) * sinh(pi l / (beta v)) ] + c1'

which is EXACTLY the Ryu-Takayanagi geodesic length in the BTZ black-hole
geometry (planar horizon, temperature 1/beta): the log regime (l << beta*v)
is the vacuum AdS3 geodesic, the linear regime (l >> beta*v) is the geodesic
hugging the horizon, whose entropy density

    s_inf = dS/dl -> pi c / (3 beta v)

is the horizon-length law -- black-hole entropy SCALING (not microstate
counting; that stays out of reach and we say so).

So the sharp, falsifiable claims tested here, all exact free-fermion:
  B1  T->0 recovers R11's vacuum answer (c = 1);
  B2  at finite T the measured S(l) fits the sinh form with the SAME c = 1
      and a fitted thermal length beta_fit * v_fit == beta * v_group, where
      v_group = cos(TH2) is the walk's exact cone speed (analytic);
  B3  the large-l entropy density matches pi*c/(3*beta*v) to ~1%;
  B4  teeth: the GAPPED walk at the same T shows NO such scaling (entropy
      floor set by the gap, sinh fit collapses c toward 0).

Method: r11's Peschel machinery with the band projector replaced by the
thermal occupation  P_k = sum_a f(omega_a) v_a v_a^dag,  f = 1/(1+e^{b w}).
Ring L with l <= L/6 so finite-T finite-L torus corrections stay small
(honesty note: the exact torus answer needs modular sums we do not model).

Run:  python r12_btz_thermal.py     (~seconds; r12_results.json + fig)
"""
import json
import math
import os

import numpy as np

from r11_entanglement_probe import walk_modes, block_entropy, TH2

DIR = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(DIR, "figs")
V_CONE = math.cos(TH2)                    # exact cone speed of the walk


def _modes_ap(L, m):
    """walk modes on the ANTIPERIODIC (NS-sector) k grid k_n = 2pi(n+1/2)/L.
    Why: the periodic ring has an exact two-fold omega=0 mode at k=0; thermal
    filling half-occupies it (f=1/2), adding an l-DEPENDENT entropy
    contamination ~ (l/L)ln(L/l) that biased the vacuum fit to c=1.047.
    The NS grid gaps it away (~ 2pi v/2L) -- standard fermion-ring practice."""
    from r11_entanglement_probe import TH2 as th2
    ks = 2.0 * np.pi * (np.arange(L) + 0.5) / L
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
        om = -np.angle(ev)
        order = np.argsort(om)
        omegas[j] = om[order]
        W = W[:, order]
        W /= np.linalg.norm(W, axis=0, keepdims=True)
        V[j] = W
    return ks, omegas, V


def thermal_kernel(L, m, beta):
    """C(x-y) for the THERMAL state: Fermi-Dirac filling of the walk bands.
    NS-sector kernel: C(x-y) = (1/L) sum_k e^{ik(x-y)} P_k with half-integer k
    (the phase is handled exactly by an explicit transform)."""
    ks, om, V = _modes_ap(L, m)
    Pk = np.zeros((L, 2, 2), complex)
    for j in range(L):
        for a in range(2):
            f = 1.0 / (1.0 + np.exp(np.clip(beta * om[j, a], -700, 700)))
            v = V[j, :, a]
            Pk[j] += f * np.outer(v, v.conj())
    return ks, Pk


def thermal_entropy_profile(L, m, beta, ells):
    """NS-sector-safe: C(d+L) = -C(d) under antiperiodic k, so we assemble
    blocks with SIGNED separations d = x-y directly (r11's %L indexing would
    silently drop the sign)."""
    ks, Pk = thermal_kernel(L, m, beta)
    lmax = max(ells)
    ds = np.arange(-(lmax - 1), lmax)               # signed separations
    phase = np.exp(1j * np.outer(ks, ds))
    ker = np.einsum("kd,kab->dab", phase, Pk) / L   # ker[i] = C(ds[i])
    off = lmax - 1                                  # index of d = 0
    Cb = np.empty((2 * lmax, 2 * lmax), complex)
    for x in range(lmax):
        for y in range(lmax):
            Cb[2 * x:2 * x + 2, 2 * y:2 * y + 2] = ker[off + x - y]
    out = []
    for l in ells:
        nu = np.linalg.eigvalsh(Cb[: 2 * l, : 2 * l])
        nu = np.clip(nu.real, 1e-12, 1.0 - 1e-12)
        out.append(float(-np.sum(nu * np.log(nu) + (1 - nu) * np.log(1 - nu))))
    return np.array(out)


def fit_btz(ells, S, Lth_grid):
    """fit S = (c/3) ln[(Lth/pi) sinh(pi l/Lth)] + c1 by scanning the thermal
    length Lth (= beta*v) on a grid; inner fit is linear -> global lsq."""
    ells = np.asarray(ells, float)
    best = None
    for Lth in Lth_grid:
        x = np.log((Lth / np.pi) * np.sinh(np.pi * ells / Lth))
        A = np.vstack([x / 3.0, np.ones_like(x)]).T
        (c, c1), res, *_ = np.linalg.lstsq(A, S, rcond=None)
        r = float(res[0]) if len(res) else 0.0
        if best is None or r < best[0]:
            best = (r, float(c), float(c1), float(Lth))
    _, c, c1, Lth = best
    ss = np.sum((S - S.mean()) ** 2)
    r2 = 1.0 - best[0] / ss if ss > 0 else 1.0
    return c, c1, Lth, float(r2)


if __name__ == "__main__":
    os.makedirs(FIGS, exist_ok=True)
    L = 768
    ells = list(range(6, L // 6 + 1, 2))
    print("R12 BTZ/thermal-CFT correspondence of the QCA sea")
    print(f"(L={L}, cone speed v = cos({TH2}) = {V_CONE:.4f} analytic)")
    print("=" * 66)

    # B1: T->0 recovers vacuum c=1 (beta large; CC fit from r11 on same ells)
    from r11_entanglement_probe import fit_central_charge
    S0 = thermal_entropy_profile(L, 0.0, beta=4000.0, ells=ells)
    c0, _, r20 = fit_central_charge(L, ells, S0)
    print(f"B1 T->0      : c = {c0:.4f}  (vacuum CC fit, r2={r20:.6f})")

    # B2: finite temperatures -- sinh fit, c and thermal length certified
    betas = [40.0, 80.0, 160.0]
    b2rows, b2ok = [], True
    for beta in betas:
        S = thermal_entropy_profile(L, 0.0, beta, ells)
        grid = np.linspace(0.5 * beta * V_CONE, 1.6 * beta * V_CONE, 141)
        c, c1, Lth, r2 = fit_btz(ells, S, grid)
        vfit = Lth / beta
        row = {"beta": beta, "c": c, "Lth_fit": Lth, "v_fit": vfit, "r2": r2}
        b2rows.append(row)
        b2ok &= abs(c - 1.0) < 0.04 and abs(vfit / V_CONE - 1.0) < 0.04
        print(f"B2 beta={beta:5.0f} : c = {c:.4f}  v_fit = {vfit:.4f} "
              f"(target {V_CONE:.4f})  r2 = {r2:.6f}")

    # B3: horizon-entropy density  s_inf = pi c/(3 beta v)
    beta = 40.0
    lA, lB = L // 6 - 12, L // 6
    SA, SB = thermal_entropy_profile(L, 0.0, beta, [lA, lB])
    s_meas = (SB - SA) / (lB - lA)
    s_theo = np.pi * 1.0 / (3.0 * beta * V_CONE)
    print(f"B3 s_inf     : measured {s_meas:.6f}  vs  pi*c/(3*beta*v) = "
          f"{s_theo:.6f}   ratio = {s_meas / s_theo:.4f}")

    # B4: teeth -- gapped walk, same T, sinh fit must collapse
    Sg = thermal_entropy_profile(L, 0.55, beta, ells)
    grid = np.linspace(0.5 * beta * V_CONE, 1.6 * beta * V_CONE, 141)
    cg, _, _, _ = fit_btz(ells, Sg, grid)
    print(f"B4 gapped    : c_fit = {cg:.4f}  (gap 0.55 >> T: must be ~0)")

    ok1 = abs(c0 - 1.0) < 0.03
    ok3 = abs(s_meas / s_theo - 1.0) < 0.02
    ok4 = abs(cg) < 0.05
    print(f"\ncertificates: B1 {'PASS' if ok1 else 'FAIL'}  "
          f"B2 {'PASS' if b2ok else 'FAIL'}  B3 {'PASS' if ok3 else 'FAIL'}  "
          f"B4 {'PASS' if ok4 else 'FAIL'}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4.4))
        for beta, mk in zip(betas, "osd"):
            S = thermal_entropy_profile(L, 0.0, beta, ells)
            ax.plot(ells, S, mk, ms=3, label=f"beta={beta:.0f} (thermal)")
            Lth = beta * V_CONE
            ax.plot(ells, (1 / 3) * np.log((Lth / np.pi)
                    * np.sinh(np.pi * np.array(ells) / Lth))
                    + (S[0] - (1 / 3) * np.log((Lth / np.pi)
                       * np.sinh(np.pi * ells[0] / Lth))), "-", lw=1)
        ax.plot(ells, S0, "^", ms=3, c="k", label="T=0 (vacuum, log)")
        ax.set_xlabel(r"block $\ell$"); ax.set_ylabel(r"$S(\ell)$")
        ax.set_title("QCA sea: AdS$_3$ log $\\to$ BTZ horizon linear law "
                     "(lines = BTZ geodesic prediction)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(FIGS, "fig_r12_btz.png"), dpi=140)
        print("wrote figs/fig_r12_btz.png")
    except Exception as e:
        print("figure skipped:", e)

    json.dump({"L": L, "v_cone": V_CONE, "B1_c_vacuum": c0, "B2": b2rows,
               "B3": {"s_meas": float(s_meas), "s_theory": float(s_theo)},
               "B4_c_gapped": cg,
               "certificates": {"B1": bool(ok1), "B2": bool(b2ok),
                                "B3": bool(ok3), "B4": bool(ok4)}},
              open(os.path.join(DIR, "r12_results.json"), "w"), indent=1)
    print("wrote r12_results.json")
