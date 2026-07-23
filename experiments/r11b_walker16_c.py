"""R11b — PRE-REGISTERED test: central charge of the tensor-walker matter factor.

Pre-registration (小报告-J6熵判据预研.md, 2026-07-20, BEFORE this run):
    the chirally-doubled Dirac factor of tensor_walker16 should measure
        c = 2   (one physical cone each for the normal + mirror walk)
    at the massless point dm = 0. Any measured deviation is a finding.

Objects (read-only import of lane B's tensor_walker; nothing is modified):
  * FACTOR (the matter fermion):  U4(k) = diag(U1(k), U1m(k)), 4 components.
    U1 = split-step walk with coins (th, -th+dm); mass knob dm.
    theta = pi/3 (lane B's standard working point, cone speed cos th = 1/2).
  * COMPOSITE (16 comp, U16 = U4 (x) U4): what makes the h_munu bilinears.
    Its quasi-energies are SUMS omega_a + omega_b -> an 8-fold flat band
    EXACTLY at omega = 0 (certified 5.6e-16 by lane B's dispersion16).
    A flat band pinned AT the Fermi level makes "fill omega<0" ill-defined
    -> we PROBE this honestly rather than fit a meaningless c.

Certificates:
  P1  factor, dm=0      : c = 2 (the pre-registered number)
  P2  decomposition     : U1 alone c = 1, U1m alone c = 1  (2 = 1+1)
  P3  teeth             : factor, dm=0.4 -> area law, c ~ 0
  P4  pi-doubler check  : U1's Brillouin scan has exactly ONE omega=0
                          crossing at th=pi/3 (no doubler: omega(pi)=pi-2th)
  P5  composite obstruction: count exact flat modes at omega=0 (expect 8/16)
                          -> J6 applicability boundary: judge FACTORS, not
                          the pair composite.

Method identical to r11 (exact Peschel), generalized to nc components.
Run: python r11b_walker16_c.py   (seconds, writes r11b_results.json)
"""
import json
import os
import sys

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
from rulespace_gpu import tensor_walker as tw          # READ-ONLY import
from r11_entanglement_probe import fit_central_charge

TH = np.pi / 3.0                                       # lane B working point


# ---------------------------------------------------------------- generic sea
def sea_kernel(L, Uk, nc):
    """correlation kernel (L, nc, nc) of the Dirac sea (omega<0 filled) for a
    Bloch one-step operator Uk(k) of an nc-component walk."""
    ks = 2.0 * np.pi * np.fft.fftfreq(L)
    Pk = np.zeros((L, nc, nc), complex)
    nzero = 0
    for j, k in enumerate(ks):
        U = Uk(k)
        ev, W = np.linalg.eig(U)
        om = -np.angle(ev)
        for a in range(nc):
            if om[a] < -1e-10:
                v = W[:, a] / np.linalg.norm(W[:, a])
                Pk[j] += np.outer(v, v.conj())
            elif abs(om[a]) <= 1e-10:
                nzero += 1
    return np.fft.ifft(Pk, axis=0), nzero


def block_entropy_nc(kernel, ells, nc):
    L = kernel.shape[0]
    lmax = max(ells)
    Cb = np.empty((nc * lmax, nc * lmax), complex)
    for x in range(lmax):
        for y in range(lmax):
            Cb[nc * x:nc * x + nc, nc * y:nc * y + nc] = kernel[(x - y) % L]
    out = []
    for l in ells:
        nu = np.linalg.eigvalsh(Cb[: nc * l, : nc * l])
        nu = np.clip(nu.real, 1e-12, 1.0 - 1e-12)
        out.append(float(-np.sum(nu * np.log(nu) + (1 - nu) * np.log(1 - nu))))
    return np.array(out)


def measure(L, Uk, nc, lmin=8):
    ells = list(range(lmin, L // 2 + 1, 2))
    ker, nzero = sea_kernel(L, Uk, nc)
    S = block_entropy_nc(ker, ells, nc)
    c, c1, r2 = fit_central_charge(L, ells, S)
    return {"c": c, "r2": r2, "zero_modes_total": nzero}


# ---------------------------------------------------------------- operators
def U_factor(k, dm=0.0):
    """4-comp chirally-doubled factor: normal + mirror split-step walk."""
    U = np.zeros((4, 4), complex)
    U[:2, :2] = tw.walk_matrix_1(k, TH, dm)
    U[2:, 2:] = tw.walk_matrix_1m(k, TH, dm)
    return U


def U_norm(k, dm=0.0):
    return tw.walk_matrix_1(k, TH, dm)


def U_mirr(k, dm=0.0):
    return tw.walk_matrix_1m(k, TH, dm)


# ---------------------------------------------------------------- run
if __name__ == "__main__":
    L = 192
    print("R11b pre-registered test: c of the tensor-walker matter factor")
    print("=" * 66)

    # P1: the pre-registered number
    m_f = measure(L, lambda k: U_factor(k, 0.0), 4)
    print(f"P1 factor dm=0    : c = {m_f['c']:.4f}   "
          f"(PRE-REGISTERED 2, r2 = {m_f['r2']:.6f})")

    # P2: decomposition 2 = 1 + 1
    m_n = measure(L, lambda k: U_norm(k, 0.0), 2)
    m_m = measure(L, lambda k: U_mirr(k, 0.0), 2)
    print(f"P2 decomposition  : normal c = {m_n['c']:.4f}, "
          f"mirror c = {m_m['c']:.4f}   (target 1 + 1)")

    # P3: teeth
    m_g = measure(L, lambda k: U_factor(k, 0.4), 4, lmin=24)
    print(f"P3 gapped dm=0.4  : c = {m_g['c']:.4f}   (target 0: area law)")

    # P4: single-cone certificate for U1 at th=pi/3 (no pi-doubler)
    ks = np.linspace(-np.pi, np.pi, 4001)
    om = np.array([min(abs(-np.angle(ev)) for ev in np.linalg.eigvals(U_norm(k)))
                   for k in ks])
    crossings = int(np.sum((om[:-1] < 0.02) & (om[1:] >= 0.02)))
    print(f"P4 cone count U1  : omega=0 touch regions = {crossings}  "
          f"(target 1; omega(pi) = pi-2th = {np.pi - 2 * TH:.3f} > 0)")

    # P5: composite flat-band obstruction (probe, not a fit)
    nflat = 0
    for k in (0.1, 0.3, 0.7, 1.2):
        Uf = U_factor(k, 0.0)
        U16 = np.kron(Uf, Uf)
        om16 = -np.angle(np.linalg.eigvals(U16))
        nflat = max(nflat, int(np.sum(np.abs(om16) < 1e-9)))
    print(f"P5 composite      : exact omega=0 modes = {nflat}/16 at generic k")
    print("   -> sea filling ill-defined at the Fermi level; J6 must judge")
    print("      matter FACTORS, never the pair composite (applicability rule)")

    ok1 = abs(m_f["c"] - 2.0) < 0.05
    ok2 = abs(m_n["c"] - 1.0) < 0.03 and abs(m_m["c"] - 1.0) < 0.03
    ok3 = abs(m_g["c"]) < 0.06
    ok4 = crossings == 1
    ok5 = nflat >= 6
    print(f"\ncertificates: P1 {'PASS' if ok1 else 'FAIL'}  "
          f"P2 {'PASS' if ok2 else 'FAIL'}  P3 {'PASS' if ok3 else 'FAIL'}  "
          f"P4 {'PASS' if ok4 else 'FAIL'}  P5 {'PASS' if ok5 else 'FAIL'}")
    verdict = ("PRE-REGISTRATION CONFIRMED: c = 2" if ok1 and ok2 else
               "DEVIATION FROM PRE-REGISTRATION -- that is a finding; investigate")
    print(verdict)

    json.dump({"L": L, "theta": TH,
               "factor_dm0": m_f, "normal": m_n, "mirror": m_m,
               "factor_dm0.4": m_g, "cone_crossings_U1": crossings,
               "composite_flat_modes": nflat,
               "certificates": {"P1": ok1, "P2": ok2, "P3": ok3,
                                "P4": ok4, "P5": ok5},
               "verdict": verdict},
              open(os.path.join(DIR, "r11b_results.json"), "w"), indent=1)
    print("wrote r11b_results.json")
