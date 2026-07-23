"""R25-D1: local time-domain symbol and direct constraint damping census.

K(z,k) is affine in z.  Replacing z h_t by the free proposed h_{t+1}
turns it into an 8x28 local operator on the staggered (h,pi) state.  The
one-step candidate M=F-mu K_state^*K_state is tested over the full 16^3 BZ.
This is a symbol oracle for the eventual real-space stencil, not an FFT
projector: every entry is a finite Laurent polynomial.
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import warnings

import r25_auxiliary_wilson_complex as W


DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "r25_dynamic_symbol_results.json")
NFIELD = 14
warnings.filterwarnings("ignore", message=".*encountered in matmul")


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def free_pair(a):
    I = np.eye(NFIELD)
    return np.block([[(1-a)*I, I], [-a*I, I]]).astype(complex)


def K_affine(k):
    K0 = W.augmented_maps_at_z(k, 0.0)[1]
    K1 = W.augmented_maps_at_z(k, 1.0)[1]-K0
    return K0, K1


def K_state(k):
    _, _, _, a = W.walk_data(k)
    K0, K1 = K_affine(k)
    return np.hstack([K0+(1-a)*K1, K1])


def damped_map(k, mu):
    _, _, _, a = W.walk_data(k)
    F = free_pair(a)
    K = K_state(k)
    # Contract the constraint covectors before the symplectic free step.  The
    # reversed ordering F-mu Q injects energy into the oscillator and is the
    # registered negative control; F(I-mu Q) is stable below the local CFL.
    return F@(np.eye(2*NFIELD)-mu*(K.conj().T@K)), F, K


def unit_census(eigs, tol=2e-9):
    mod = np.abs(eigs)
    return int(np.sum(np.abs(mod-1) < tol)), float(mod.max()), \
        float(mod[mod < 1-tol].max()) if np.any(mod < 1-tol) else 0.0


def scan_mu(ks):
    rows = []
    for mu in np.logspace(-5, -2.7, 17):
        worst, rate = 0.0, 0.0
        unitsets = set()
        for k in ks:
            eig = np.linalg.eigvals(damped_map(k, mu)[0])
            units, mx, rr = unit_census(eig)
            unitsets.add(units); worst=max(worst, mx); rate=max(rate, rr)
        rows.append({"mu": float(mu), "max_modulus": worst,
                     "slowest_contracting": rate,
                     "unit_counts": sorted(unitsets)})
    viable = [r for r in rows if r["max_modulus"] <= 1+1e-10
              and r["unit_counts"] == [12]]
    return rows, (max(viable, key=lambda r: r["mu"]) if viable else None)


def main():
    # Preflight: affine-z identity and exact darkness of both on-shell
    # physical/gauge constraint kernels.
    rng = np.random.default_rng(250729)
    affine_worst = 0.0
    dark_worst = 0.0
    for _ in range(128):
        k = rng.uniform(-np.pi, np.pi, 3)
        z = rng.normal()+1j*rng.normal()
        K0, K1 = K_affine(k)
        Kz = W.augmented_maps_at_z(k, z)[1]
        affine_worst=max(affine_worst, float(np.max(np.abs(Kz-K0-z*K1))))
        for branch in (-1, 1):
            zp, _, _ = W.geometry_root(k, branch)
            G = W.augmented_maps_at_z(k, zp)[0]
            p = (1-1/zp)*G
            Xg = np.vstack([G, p])  # 28x4
            dark_worst=max(dark_worst,
                           float(np.max(np.abs(K_state(k)@Xg))))

    # Candidate selection on a broad deterministic set, final certification
    # on every nonzero point of the 16^3 BZ.
    gate = [2*np.pi*np.array(v, float)/32 for v in
            ((2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0),
             (2, 2, 2), (1, 1, 1))]
    sample = gate+[rng.uniform(-np.pi, np.pi, 3) for _ in range(256)]
    scan, chosen = scan_mu(sample)

    full = {"N": 16, "max_modulus": None, "slowest_contracting": None,
            "unit_counts": [], "worst_index": None}
    if chosen is not None:
        mu = chosen["mu"]
        worst, rate, unitsets, wi = 0.0, 0.0, set(), None
        for idx in np.ndindex(16, 16, 16):
            if idx == (0, 0, 0):
                continue
            k = 2*np.pi*np.array(idx, float)/16
            units, mx, rr = unit_census(np.linalg.eigvals(damped_map(k, mu)[0]))
            unitsets.add(units); rate=max(rate, rr)
            if mx>worst: worst, wi=mx, idx
        full.update({"max_modulus": worst, "slowest_contracting": rate,
                     "unit_counts": sorted(unitsets),
                     "worst_index": list(wi)})

    checks = {
        "K_is_affine_in_time_shift": affine_worst < 1e-12,
        "on_shell_gauge_columns_dark_in_state_operator": dark_worst < 1e-11,
        "stable_mu_exists_with_twelve_unit_modes": chosen is not None,
        "full_16BZ_stable": chosen is not None and full["max_modulus"] <= 1+1e-10,
        "full_16BZ_unit_count_twelve": chosen is not None and full["unit_counts"] == [12],
    }
    result = {"register": "R25-D1-dynamic-symbol",
              "status": "PASS" if all(checks.values()) else "FAIL",
              "checks": checks, "source_sha256": sha256(__file__),
              "affine_z_residual": affine_worst,
              "gauge_state_dark_residual": dark_worst,
              "mu_scan": scan, "chosen": chosen, "full_BZ": full,
              "interpretation": "12 unit eigenmodes = two Floquet branches times (4 gauge + 2 physical); curvature quotient is two polarizations per frequency sign.",
              "scope_boundary": "Direct K^*K damping symbol only; rate quality, sourced static fixed point and real-space adjoint bridge remain."}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print("R25-D1 local dynamic-symbol damping")
    print("status:", result["status"])
    print("affine/dark residual:", affine_worst, dark_worst)
    print("chosen:", chosen)
    print("full BZ:", full)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
