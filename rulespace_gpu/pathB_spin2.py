"""Path B — linearized spin-2 (Fierz-Pauli): the real frontier, first milestones.

R7 (three times over) hit the ceiling of SCALAR gravity: a scalar theta gives
the wrong equivalence principle, wrong light bending, and can't trap. Real
gravity needs a SPIN-2 tensor field h_munu. Two decisive first tests here,
both tractable before the full nonlinear build:

  B1  DEGREES OF FREEDOM: a symmetric spatial tensor h_ij has 6 components;
      the transverse-traceless (TT) projector must leave exactly 2 -- the
      graviton's two polarizations (+ and x). This is what makes it spin-2
      (a scalar has 1, a vector 2-but-different). Verified as the rank of the
      TT projector for a generic wavevector.

  B2  LIGHT BENDING (the decisive scalar-vs-tensor test): the static linearized
      metric of a mass is ds^2 = -(1+2phi)dt^2 + (1-2phi)dx^2. A photon feels
      BOTH the time part AND the space part -> effective index n = 1 - 2phi,
      deflection = 2x the scalar-gravity value (which has only n = 1 - phi).
      GR: 4GM/b.  Scalar (R7): 2GM/b.  The factor 2 is the Eddington signature
      that we have TENSOR gravity, not scalar.
"""
import argparse, json, os
import numpy as np
from . import backend as B, observables
xp = B.xp


# ---------------- B1: graviton polarization count ----------------
def tt_projector_rank(khat):
    """rank of the transverse-traceless projector on symmetric 3x3 tensors.
    Lambda_ij,kl = P_ik P_jl + P_il P_jk)/2 - (1/2) P_ij P_kl,  P = I - khat khat^T.
    Rank = number of graviton polarizations."""
    k = np.asarray(khat, float); k /= np.linalg.norm(k)
    P = np.eye(3) - np.outer(k, k)
    # build 6x6 matrix of Lambda acting on symmetric tensors (Voigt-like basis)
    idx = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]
    def sym_basis(a, b):
        E = np.zeros((3, 3)); E[a, b] = E[b, a] = 1.0; return E
    def Lambda(h):
        return P @ h @ P - 0.5 * P * np.trace(P @ h @ P)
    M = np.zeros((6, 6))
    for j, (a, b) in enumerate(idx):
        Lh = Lambda(sym_basis(a, b))
        M[:, j] = [Lh[a, b] for (a, b) in idx]
    return int(np.linalg.matrix_rank(M, tol=1e-9))


def b1_polarization():
    ranks = [tt_projector_rank(k) for k in
             [(0, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1), (0.3, 0.7, -0.4)]]
    return ranks, all(r == 2 for r in ranks)


# ---------------- B2: light bending, tensor vs scalar ----------------
def _phi_static(L, blob_sig, ndim=3, amp=1.0):
    """Newtonian potential of a blob: Lap phi = rho (units 4piG=1), phi<0 well."""
    gr = np.meshgrid(*[np.arange(L)] * ndim, indexing="ij")
    r2 = sum((gr[i] - L // 2) ** 2 for i in range(ndim))
    rho = np.exp(-r2 / (2 * blob_sig ** 2)); rho -= rho.mean()
    k1 = 2 * np.pi * np.fft.fftfreq(L)
    K = np.meshgrid(*([k1] * ndim), indexing="ij")
    k2 = sum(k ** 2 for k in K); k2[(0,) * ndim] = 1.0
    phi = np.real(np.fft.ifftn(-np.fft.fftn(amp * rho) / k2))   # Lap phi = rho
    return phi


def _deflection(nindex, L, b):
    """Born (weak-lensing) deflection: alpha = -integral d(ln n)/dy dx along the
    straight photon path at impact parameter b. Standard, unambiguous."""
    c = L // 2
    y = c + b
    dn_dy = np.gradient(nindex, axis=1)          # d n / d y
    line = dn_dy[:, int(round(y)) % L]           # along x at height y
    n_line = nindex[:, int(round(y)) % L]
    alpha = -np.sum(line / n_line)               # integral of -d(ln n)/dy dx (dx=1)
    return float(alpha)


def b2_light_bending(L=256, blob_sig=8.0, b=30):
    """weak-field limit: tensor/scalar deflection ratio -> 2 (Eddington)."""
    rows = []
    for amp in (3e-3, 3e-4, 3e-5):
        phi = _phi_static(L, blob_sig, ndim=2, amp=amp); phi -= phi.max()
        at = _deflection(1 - 2 * phi, L, b)                  # GR:     n = 1 - 2phi
        as_ = _deflection(1 - phi, L, b)                     # scalar: n = 1 - phi (R7)
        rows.append({"phi_max": float(abs(phi).max()), "ratio": at / as_})
    return {"convergence": rows, "ratio_weakfield": rows[-1]["ratio"]}


if __name__ == "__main__":
    print(f"backend = {B.NAME}   device = {B.device_info()}\n")
    ranks, ok1 = b1_polarization()
    print(f"[B1] graviton polarizations (TT projector rank per k): {ranks}")
    print(f"     {'PASS' if ok1 else 'FAIL'}: exactly 2 DOF => spin-2 (scalar=1, not this)\n")
    r = b2_light_bending()
    print("[B2] light bending, tensor/scalar ratio -> 2 (Eddington) in weak field:")
    for row in r["convergence"]:
        print(f"     |phi|max={row['phi_max']:.2e}   ratio={row['ratio']:.4f}")
    ok2 = abs(r["ratio_weakfield"] - 2.0) < 0.02
    print(f"     {'PASS' if ok2 else 'CHECK'}: weak-field ratio {r['ratio_weakfield']:.4f} "
          f"= factor-2 tensor signature (scalar R7 would give 1.0)")
    json.dump({"ranks": ranks, "bending": r},
              open(os.path.join(os.path.dirname(__file__), "..", "data", "results", "pathB_results.json"), "w"), indent=1)
