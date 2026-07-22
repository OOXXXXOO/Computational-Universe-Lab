"""R13 — the stride bridge: averaged R10 currents live EXACTLY on the
stride-2 centered (T3 / wide-box) calculus, and the averaging maps
annihilate precisely the Nyquist sector where that calculus is blind.

CONTEXT (M1 finding, lane B): emergence needs the wide-box geometry
(central-1 differences, stride-2 physical step); R10's exact matter
currents are stride-1 (Yee). Literal half-grid injection -> N_prop = 5.
Diagnosis here: the obstruction is RAW vs AVERAGED, not stride-1 vs
stride-2. Three algebraic facts close it:

  T5 (time bridge)    b(t+1) - b(t-1) = -div[F_t + F_{t-1}] + (Phi_t + Phi_{t-1})
                      exact by telescoping two R10 forward balances.
  T6 (space bridge)   with A_c f = (f + roll(f,1,c))/2 (pair average) and the
                      cell average  Abar = A_0 A_1 A_2:
                          A_b o div^-_b = div^c2_b ,   div^c2_b F = (F - roll(F,2,b))/2
                      so applying Abar to the (time-bridged) balance gives the
                      EXACT stride-2 centered continuity on T3 staggered points:
                          Abar[b(t+1)-b(t-1)] = - sum_b div^c2_b( Jbar_b ) + Abar Phibar
                      with Jbar_b = (prod_{c != b} A_c)(F_b,t + F_b,t-1)  -- the
                      CONSUMABLE OBJECT for M2: feed the wide box with Jbar,
                      never with raw F.
  T7 (Nyquist annihilation)  symbol of A_b is cos(k_b/2) e^{-i k_b/2}: zero
                      exactly at k_b = pi, which is exactly where the
                      central-1 symbol i sin(k_b) is blind. Raw F carries
                      Nyquist content -> pumps the box's blind sector (lane
                      B's N_prop = 5 mode); Abar kills it identically.

Certificates (fp64, palindromic 3D walks from r10, force active):
  A  T5 time bridge, 2-comp theta-field walk        (machine zero)
  B  T6 full space-time bridge, same walk           (machine zero)
  C  T6 on the 4-comp Dirac pair w/ chirality mass  (machine zero)
  D  T7 Nyquist: A_b ((-1)^{x_b} g) == 0            (machine zero)
     + symbol scan: blind set of sin(k) == zero set of cos(k/2) on (0, pi]

Run:  python r13_stride_bridge.py    (seconds; writes r13_results.json)
"""
import json
import os

import numpy as np

from r10_current_generator import (Walk, build_2comp_layers,
                                   build_4comp_layers)

DIR = os.path.dirname(os.path.abspath(__file__))
RES = {}


# ------------------------------------------------------------ step account
def step_account(walk, layers, psi):
    """apply one full step; collect flux packets (a, bax, F) and forces."""
    packets = []
    forces = [np.zeros(walk.shape) for _ in range(walk.ndim)]
    for layer in layers:
        for a in range(walk.ndim):
            Fp, Phi = walk.layer_flux_force(psi, layer, a)
            if Fp is not None:
                packets.append((a, Fp[0], Fp[1]))
            if np.ndim(Phi):
                forces[a] += Phi
        psi = walk.apply(psi, layer)
    return psi, packets, forces


def Aavg(f, ax):
    return 0.5 * (f + np.roll(f, 1, ax))


def cell_avg(f, nd):
    for c in range(nd):
        f = Aavg(f, c)
    return f


def transverse_avg(f, nd, bax):
    for c in range(nd):
        if c != bax:
            f = Aavg(f, c)
    return f


def div_c2(F, ax):
    return 0.5 * (F - np.roll(F, 2, ax))


# ------------------------------------------------------------ certificates
def certify_time_bridge(walk, layers_fn, psi, T, label):
    """T5: b(t+1)-b(t-1) + div[F_t+F_{t-1}] - [Phi_t+Phi_{t-1}] == 0."""
    worst = 0.0
    psi_m, pk_m, fo_m = None, None, None
    for t in range(T):
        b_prev = [walk.bond(psi, a) for a in range(walk.ndim)]
        psi1, pk1, fo1 = step_account(walk, layers_fn(t), psi)
        psi2, pk2, fo2 = step_account(walk, layers_fn(t + 1), psi1)
        for a in range(walk.ndim):
            div = np.zeros(walk.shape)
            for pk in (pk1, pk2):
                for (aa, bax, F) in pk:
                    if aa == a:
                        div += F - np.roll(F, 1, bax)
            resid = (walk.bond(psi2, a) - b_prev[a] + div
                     - (fo1[a] + fo2[a]))
            worst = max(worst, float(np.abs(resid).max()))
        psi = psi1
    print(f"[{label}] T5 time bridge: max residual = {worst:.2e}")
    RES[label] = worst
    return worst


def certify_t3_bridge(walk, layers_fn, psi, T, label):
    """T6: cell-averaged centered continuity with stride-2 divergences."""
    nd = walk.ndim
    worst = 0.0
    for t in range(T):
        b_prev = [walk.bond(psi, a) for a in range(nd)]
        psi1, pk1, fo1 = step_account(walk, layers_fn(t), psi)
        psi2, pk2, fo2 = step_account(walk, layers_fn(t + 1), psi1)
        for a in range(nd):
            lhs = cell_avg(walk.bond(psi2, a) - b_prev[a], nd)
            rhs = np.zeros(walk.shape)
            for pk in (pk1, pk2):
                for (aa, bax, F) in pk:
                    if aa == a:
                        rhs -= div_c2(transverse_avg(F, nd, bax), bax)
            rhs += cell_avg(fo1[a] + fo2[a], nd)
            worst = max(worst, float(np.abs(lhs - rhs).max()))
        psi = psi1
    print(f"[{label}] T6 T3-staggered centered continuity: "
          f"max residual = {worst:.2e}")
    RES[label] = worst
    return worst


def certify_nyquist(shape, label):
    """T7: A_b annihilates the Nyquist sector; blind-set duality of symbols."""
    rng = np.random.default_rng(3)
    g = rng.normal(size=(1,) + shape[1:])           # transverse profile only:
    x0 = np.arange(shape[0]).reshape(-1, 1, 1)      # pure Nyquist along axis 0
    f = ((-1.0) ** x0) * g
    ann = float(np.abs(Aavg(f, 0)).max())
    ks = np.linspace(1e-6, np.pi, 20001)
    blind_sin = np.abs(np.sin(ks)) < 1e-9          # central-1 blind set
    zero_avg = np.abs(np.cos(ks / 2.0)) < 1e-9     # averaging kernel zeros
    duality = bool(np.array_equal(np.where(blind_sin)[0],
                                  np.where(zero_avg)[0]))
    print(f"[{label}] T7 Nyquist annihilation: |A_b f_Nyq|_max = {ann:.2e}; "
          f"blind-set(sin k) == zero-set(cos k/2) on (0,pi]: {duality}")
    RES[label] = ann
    return ann, duality


if __name__ == "__main__":
    print("R13 stride bridge: averaged R10 currents on the T3/wide-box calculus")
    print("=" * 70)
    rng = np.random.default_rng(0)
    shape = (12, 12, 12)

    # 2-comp walk with a theta FIELD (force term active)
    th_field = 0.4 + 0.15 * np.cos(
        2 * np.pi * np.arange(12).reshape(-1, 1, 1) / 12.0)
    th_field = th_field * np.ones(shape)
    lf2 = build_2comp_layers(shape, th_field, dm=0.3)
    w2 = Walk(shape, 2)
    psi2 = rng.normal(size=shape + (2,)) + 1j * rng.normal(size=shape + (2,))
    psi2 /= np.linalg.norm(psi2)
    rA = certify_time_bridge(w2, lf2, psi2.copy(), 4, "A_2comp_theta_T5")
    rB = certify_t3_bridge(w2, lf2, psi2.copy(), 4, "B_2comp_theta_T6")

    # 4-comp Dirac pair with chirality-mixing mass coin
    lf4 = build_4comp_layers(shape, th0=0.5, dm=0.25)
    w4 = Walk(shape, 4)
    psi4 = rng.normal(size=shape + (4,)) + 1j * rng.normal(size=shape + (4,))
    psi4 /= np.linalg.norm(psi4)
    rC = certify_t3_bridge(w4, lf4, psi4.copy(), 4, "C_4comp_dirac_T6")

    rD, dual = certify_nyquist(shape, "D_nyquist")

    tol = 1e-14
    ok = (rA < tol and rB < tol and rC < tol and rD < tol and dual)
    print("\nR13:", "ALL CERTIFICATES PASS" if ok else "CHECK FAILURES ABOVE")
    print("M2 consumable: feed the wide box with Jbar_b = "
          "transverse-avg(F_b,t + F_b,t-1) -- NEVER raw stride-1 F.")
    json.dump({k: float(v) for k, v in RES.items()}
              | {"symbol_duality": bool(dual), "all_pass": bool(ok)},
              open(os.path.join(DIR, "r13_results.json"), "w"), indent=1)
    print("wrote r13_results.json")
