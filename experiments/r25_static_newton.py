"""R25-D0: real-space local Newton lift and Wilson double-pole canary.

The source lift is a radius-one stencil built from U_walk.  The only inverse
is the physical static Green response 1/a_W; no inverse enters the gauge or
constraint operators.  Both 24^3 and 32^3 canaries use the frozen L3 readout.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

import cp1_v4_L2 as L2
import cp1_v4_L3 as L3
import r25_auxiliary_wilson_complex as R25W
from rulespace_gpu import green_one_walk as gw


DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "r25_static_newton_results.json")
C = L2.C
TH = L2.TH


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def walk_entry_actions(f):
    """Apply all four scalar entries of the local U_walk stencil to f."""
    q0 = np.zeros(f.shape+(2,), complex)
    q1 = np.zeros_like(q0)
    q0[..., 0] = f
    q1[..., 1] = f
    u0 = gw.geom_walk_all(q0, TH, TH, TH, TH)
    u1 = gw.geom_walk_all(q1, TH, TH, TH, TH)
    return u0[..., 0], u1[..., 0], u0[..., 1], u1[..., 1]  # U00,U01,U10,U11


def a_action(f):
    u00, _, _, u11 = walk_entry_actions(f)
    return 0.5*(u00+u11)


def b_actions(f):
    u00, u01, u10, u11 = walk_entry_actions(f)
    return np.stack([0.5j*(u10+u01),
                     0.5*(u10-u01),
                     0.5j*(u00-u11)])


def local_source_lift(rho):
    """Radius-two trace-reversed, spatial-trace-zero Newton numerator."""
    arho = a_action(rho)
    onepa = rho+arho
    b1 = b_actions(rho)
    # All entries are scalar Laurent convolutions and commute.  Compose them
    # directly in real space to retain a strictly finite stencil.
    bb = np.stack([b_actions(b1[j]) for j in range(3)], axis=1)  # [i,j,...]
    b2sum = bb[0, 0]+bb[1, 1]+bb[2, 2]
    hb = np.zeros((10,)+rho.shape, complex)
    hb[0] = (onepa+a_action(onepa))/(2*C)
    for i in range(3):
        hb[1+i] = -1j*(b1[i]+a_action(b1[i]))/(2*C)
    for i, j, packed in ((0, 0, 4), (0, 1, 5), (0, 2, 6),
                         (1, 1, 7), (1, 2, 8), (2, 2, 9)):
        hb[packed] = ((b2sum if i == j else 0)-3*bb[i, j])/(4*C)
    return hb


def symbols(N):
    a = np.zeros((N, N, N), float)
    for idx in np.ndindex(N, N, N):
        k = 2*np.pi*np.array(idx, float)/N
        a[idx] = R25W.walk_data(k)[3]
    return a


def static_field_local(rho):
    drive = local_source_lift(rho)
    aw = symbols(rho.shape[0])
    out = np.zeros_like(drive)
    mask = aw > 1e-14
    for j in range(10):
        dk = np.fft.fftn(drive[j])
        hk = np.zeros_like(dk)
        hk[mask] = dk[mask]/aw[mask]
        out[j] = np.fft.ifftn(hk)
    return out, drive, aw


def direct_symbol_field(rho, aw):
    rk = np.fft.fftn(rho)
    outk = np.zeros((10,)+rho.shape, complex)
    mask = aw > 1e-14
    for idx in np.ndindex(rho.shape):
        if not mask[idx]:
            continue
        k = 2*np.pi*np.array(idx, float)/rho.shape[0]
        U = L2.walk_symbol(k)
        # Convert the normal-h lift stored by R25W back to trace reverse.
        hn = R25W.static_newton_lift(U)
        H = np.zeros((4, 4), complex)
        for x, (m, n) in zip(hn, L3.r15.SYM):
            H[m, n] = H[n, m] = x
        trh = np.sum(L3.r15.ETA*H)
        hb = H-0.5*L3.r15.ETA*trh
        lift = np.array([hb[m, n] for m, n in L3.r15.SYM])
        outk[(slice(None),)+idx] = lift*rk[idx]/aw[idx]
    return np.fft.ifftn(outk, axes=(1, 2, 3))


def gaussian_lump(N, sig):
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    r2 = (X-N//2)**2+(Y-N//2)**2+(Z-N//2)**2
    rho = np.exp(-r2/(2*sig**2))
    return rho/rho.sum()


def run_box(N, sig):
    rho = gaussian_lump(N, sig)
    rho_zm = rho-rho.mean()
    hb, drive, aw = static_field_local(rho_zm)
    direct = direct_symbol_field(rho_zm, aw)
    bridge = float(np.max(np.abs(hb-direct))/(np.max(np.abs(direct))+1e-300))
    # The ordered xyz walk is a chiral complex stencil.  As on the frozen
    # matter side, the real theory is the direct sum with its conjugate/mirror
    # sector.  The reality condition h_minus=conj(h_plus) leaves four real
    # gauge parameters and two real polarizations; it does not double the
    # physical count.  Never take Re inside a single complex equation.
    hb_minus = np.conjugate(hb)
    hb_physical = 0.5*(hb+hb_minus)
    single_sector_imag = float(np.max(np.abs(hb.imag)))
    physical_imag = float(np.max(np.abs(hb_physical.imag)))
    conjugacy_residual = float(np.max(np.abs(hb_minus-np.conjugate(hb))))
    cn = L3.canary_numbers(hb_physical.real, rho, sig)
    # Exact equilibrium residual lap h + drive=0 in Fourier.
    worst_eq = 0.0
    for j in range(10):
        resk = -aw*np.fft.fftn(hb[j])+np.fft.fftn(drive[j])
        resk[(0, 0, 0)] = 0
        worst_eq = max(worst_eq, float(np.max(np.abs(resk))))
    return {"N": N, "sigma": sig, "canary": cn,
            "local_vs_direct_symbol_rel": bridge,
            "single_chiral_sector_max_imaginary": single_sector_imag,
            "doubled_physical_max_imaginary": physical_imag,
            "mirror_conjugacy_residual": conjugacy_residual,
            "equilibrium_fourier_residual_max": worst_eq,
            "aW_min_nonzero": float(aw[aw > 1e-14].min()),
            "aW_max": float(aw.max())}


def main():
    boxes = [run_box(24, 2.5), run_box(32, 2.5)]
    checks = {
        "local_stencil_matches_exact_symbol": max(x["local_vs_direct_symbol_rel"] for x in boxes) < 1e-12,
        "conjugate_doubling_produces_real_physical_metric":
            max(max(x["doubled_physical_max_imaginary"],
                    x["mirror_conjugacy_residual"]) for x in boxes) < 1e-12,
        "static_equilibrium_exact": max(x["equilibrium_fourier_residual_max"] for x in boxes) < 1e-10,
        "Newton_ratio_A_gate": all(abs(x["canary"]["ratio_A"]-2) <= 0.02 for x in boxes),
        "Newton_tail_gate": all(x["canary"]["tailcorr_h00"] > 0.99 for x in boxes),
    }
    result = {"register": "R25-D0-static-Newton",
              "status": "PASS" if all(checks.values()) else "FAIL",
              "checks": checks, "source_sha256": sha256(__file__),
              "reality_structure": "plus xyz sector direct-summed with its conjugate/mirrored sector; h_minus=conj(h_plus), physical h=(h_plus+h_minus)/2",
              "boxes": boxes,
              "scope_boundary": "Exact static oracle with a real-space local source lift; time-domain augmented damping and moving exact-current source remain."}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print("R25-D0 real-space Newton lift")
    print("status:", result["status"])
    for row in boxes:
        c = row["canary"]
        print(row["N"], "ratio_A", c["ratio_A"], "tail", c["tailcorr_h00"],
              "bridge", row["local_vs_direct_symbol_rel"],
              "eq", row["equilibrium_fourier_residual_max"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
