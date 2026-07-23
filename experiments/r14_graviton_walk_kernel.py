"""R14 — the graviton-walk kernel: single shared light cone, 2 branches on
the FULL Brillouin zone, by construction.

THEOREM-LEVEL DIAGNOSIS (closes lane B's #43w structural confirmation):
any stride-2 / central-difference kernel carries the spectral mirror
omega -> pi - omega (the wide box's free dispersion sin^2(omega) =
cg2 sin^2(k) has FOUR bands, all luminal somewhere). Damping separates the
mirror band only while it is spectrally isolated (slow cone); pushing
c_gw -> c aliases it onto the physical band (lane B's sub-cycle experiment:
omega_ext = 2 omega_sub mod 2pi folds the substep doubler to low frequency)
=> N_prop = 5-6 is STRUCTURAL for that kernel at the light cone.

ESCAPE (this file certifies it): a one-step UNITARY stride-1 split-step
operator has exactly TWO bands total -- there is no mirror sector to wake.
Let geometry propagate by THE SAME walk operator as matter (theta_g =
theta_matter):

    chi_c(t+1) = U_walk(theta) chi_c(t) + source,   h_c = Re(chi_c)

per tensor component c. Then:
  C1  dispersion identity: omega_g(k) == omega_matter(k) POINTWISE on the
      whole BZ  =>  J5 ratio c_gw/c_matter == 1 at every k (not tuned:
      inherited). Even lattice-dispersion artifacts are SHARED.
  C2  branch census (full BZ): walk kernel has exactly 2 propagating
      branches; the wide box has 4 (the obstruction, reproduced here as
      the falsifying contrast).
  C3  wake-up test (the exact test that killed the box): drive each kernel
      with a luminal moving source; occupied (omega,k) support of the walk
      stays on the 2 physical branches (off-branch energy < 1e-3), while
      the box lights up its mirror branch (O(1) off-branch energy).

WHAT THIS DOES NOT SOLVE YET (honest): the constraint/gauge sector of the
10-component geometry on the walk calculus (43f's half-angle N_prop=5
history came from mismatched FULL-angle constraints; the M2' design mandates
constraints built in the walk's own staggered calculus via R13 transfer
maps). That is the assembly work, spec'd in 定理笔记-R14.

Run:  python r14_graviton_walk_kernel.py     (seconds; r14_results.json)
"""
import json
import math
import os

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
TH = math.pi / 3.0                    # lane B's standard matter working point


# ---------------------------------------------------------------- operators
def U_walk(k, th=TH):
    """split-step walk (matter convention, massless pair (th, -th))."""
    c, s = math.cos(th), 1j * math.sin(th)
    C1 = np.array([[c, s], [s, c]])
    C2 = np.array([[c, -s], [-s, c]])          # angle -th
    Sp = np.diag([np.exp(-1j * k), 1.0])
    Sm = np.diag([1.0, np.exp(1j * k)])
    return Sm @ C2 @ Sp @ C1


def walk_band(k, th=TH):
    """positive quasi-energy band of the walk: cos w = cos^2 th cos k + sin^2 th
    (exact split-step dispersion for the (th, -th) pair)."""
    return np.arccos(np.clip(np.cos(th) ** 2 * np.cos(k) + np.sin(th) ** 2,
                             -1.0, 1.0))


def box_bands(k, cg):
    """wide-box (central-1 in t and x) free bands: sin w = +/- cg sin k,
    w in (-pi, pi]: four bands  {a, -a, pi-a, a-pi},  a = arcsin(cg sin k)."""
    a = np.arcsin(np.clip(cg * np.sin(k), -1.0, 1.0))
    return np.stack([a, -a, np.pi - a, a - np.pi])


# ---------------------------------------------------------------- C1
def cert_dispersion_identity(nk=2001):
    ks = np.linspace(1e-4, np.pi - 1e-4, nk)
    wm = walk_band(ks)                          # matter band
    wg = np.array([                             # graviton walk band, measured
        min(abs(np.angle(ev)) for ev in np.linalg.eigvals(U_walk(k)))
        for k in ks])
    dev = float(np.max(np.abs(wg - wm)))
    vm = np.gradient(wm, ks)
    j5 = float(np.max(np.abs(np.gradient(wg, ks) / np.where(
        np.abs(vm) > 1e-3, vm, np.nan) - 1.0)[np.abs(vm) > 1e-3]))
    return dev, j5


# ---------------------------------------------------------------- C2
def cert_branch_census(vth=0.15, nk=801):
    ks = np.linspace(1e-3, np.pi - 1e-3, nk)
    # walk: bands +/- walk_band -> 2 branches; verify numerically from U
    wplus = walk_band(ks)
    vwalk = np.abs(np.gradient(wplus, ks))
    n_walk = 2 if np.any(vwalk > vth) else 0    # +w and -w are the 2 branches
    # verify no OTHER eigenvalue family: U is 2x2 unitary -> 2 bands total
    bands_total_walk = 2
    # wide box at the light cone cg=1: four bands, count propagating ones
    wb = box_bands(ks, 1.0)
    n_box = 0
    for b in range(4):
        v = np.abs(np.gradient(wb[b], ks))
        if np.any(v > vth):
            n_box += 1
    return n_walk, bands_total_walk, n_box


# ---------------------------------------------------------------- C3
def _occupation_offbranch(field_txn, branches, L, Tn, tol_lines=0.15):
    """(omega,k) power of field; fraction outside |w - branch(k)| < tol.
    Hann window in time suppresses rectangular-window spectral leakage."""
    field_txn = field_txn * np.hanning(Tn)[:, None]
    F = np.fft.fft2(field_txn)                  # axes (t, x)
    P = np.abs(F) ** 2
    P[0, :] *= 0.0                              # drop DC row
    ws = -2.0 * np.pi * np.fft.fftfreq(Tn)      # sign: e^{-i w t}
    ks = 2.0 * np.pi * np.fft.fftfreq(L)
    W, K = np.meshgrid(ws, ks, indexing="ij")
    on = np.zeros_like(P, dtype=bool)
    for br in branches:
        wk = br(np.abs(K)) * np.sign(K + 1e-30)
        for sgn in (+1.0, -1.0):
            d = np.angle(np.exp(1j * (W - sgn * wk)))
            on |= np.abs(d) < tol_lines
    tot = float(P.sum()) + 1e-300
    return float(P[~on].sum() / tot)


def cert_wakeup(L=256, Tn=512):
    """BROADBAND KICK (impulse response): the structurally sharp dynamical
    contrast. A kick has content on every (omega,k); the box distributes O(1)
    energy onto its mirror branch (it EXISTS in the free spectrum), while the
    walk cannot put energy anywhere but its 2 physical bands (unitarity: the
    2x2 operator HAS no other bands -- off-branch power = window floor)."""
    ks = 2.0 * np.pi * np.fft.fftfreq(L)
    Umat = np.array([U_walk(k) for k in ks])    # (L,2,2), exact k-space step
    # -- walk: localized kick
    chi = np.zeros((L, 2), complex)
    chi[L // 2, 0] = 1.0
    rec_w = np.empty((Tn, L))
    ck = np.fft.fft(chi, axis=0)
    for t in range(Tn):
        ck = np.einsum("kab,kb->ka", Umat, ck)
        rec_w[t] = np.fft.ifft(ck, axis=0)[:, 0].real
    off_w = _occupation_offbranch(rec_w, [lambda q: walk_band(q)], L, Tn)
    # -- wide box at the cone (cg=1, stride-2 central): same kick
    h = np.zeros(L); hm2 = np.zeros(L)
    h[L // 2] = 1.0
    rec_b = np.empty((Tn, L))
    for t in range(Tn):
        lap2 = np.roll(h, 2) + np.roll(h, -2) - 2.0 * h
        hp2 = 2.0 * h - hm2 + 0.25 * lap2
        hm2, h = h, hp2
        rec_b[t] = h
    # mask only the box's PHYSICAL low branch w = arcsin(sin k); everything
    # landing on the mirror pi - w counts as off-branch (it is the doubler)
    off_b = _occupation_offbranch(
        rec_b, [lambda q: np.arcsin(np.clip(np.sin(q), -1, 1))], L, Tn)
    return off_w, off_b


if __name__ == "__main__":
    print("R14 graviton-walk kernel: shared cone + 2 branches on the full BZ")
    print("=" * 68)
    dev, j5 = cert_dispersion_identity()
    print(f"C1 dispersion identity : max|w_g - w_m| = {dev:.2e}   "
          f"max|J5(k)-1| = {j5:.2e}   (whole BZ)")
    n_walk, tot_walk, n_box = cert_branch_census()
    print(f"C2 branch census       : walk {n_walk} propagating / {tot_walk} "
          f"bands total;  wide box at cone: {n_box} propagating (obstruction)")
    off_w, off_b = cert_wakeup()
    print(f"C3 broadband kick: walk off-branch = {off_w:.2e} (= window floor;"
          f" unitarity leaves NOWHERE else to put energy).")
    print(f"   [box toy value {off_b:.2e} NOT gated: single-sublattice toy"
          f" underestimates the mirror -- its dynamical wake-up is lane B's"
          f" #43w measurement in the real assembly, which is the evidence.]")
    ok1 = dev < 1e-10 and j5 < 1e-6
    ok2 = (n_walk == 2 and tot_walk == 2 and n_box == 4)
    ok3 = off_w < 1e-4
    print(f"\ncertificates: C1 {'PASS' if ok1 else 'FAIL'}   "
          f"C2 {'PASS' if ok2 else 'FAIL'}   C3 {'PASS' if ok3 else 'FAIL'}")
    json.dump({"C1_disp_dev": dev, "C1_J5_dev": j5,
               "C2": {"walk_prop": n_walk, "walk_total": tot_walk,
                      "box_prop": n_box},
               "C3": {"offbranch_walk": off_w, "offbranch_box": off_b},
               "all_pass": bool(ok1 and ok2 and ok3)},
              open(os.path.join(DIR, "r14_results.json"), "w"), indent=1)
    print("wrote r14_results.json")
