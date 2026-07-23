"""Round 4d — real stress-energy T00 in 3+1D, conservation, conformal EP transfer.

3+1D Dirac-type walk, 2-spinor, three axis split-steps with local coin
angle theta (local light speed c=cos theta) + a mass gap dm (species knob):
  axis x: sigma_x basis, +/- shift, coin C(theta)
  axis y: sigma_y basis, +/- shift, coin C(theta)
  axis z: sigma_z basis, +/- shift, coin C(theta)
  mass:   extra coin e^{i dm sigma_x}
Real energy density (species-blind, two time slices):
  T00(r) = -1/2 Im[ psi_t^dagger (psi_{t+1} - psi_{t-1}) ](r)

Claims (all in 3+1D):
 (A) sum_r T00 conserved to machine precision under static theta.
 (B) T00 is LOCAL and positive-weighted where matter sits.
 (C) EQUIVALENCE PRINCIPLE TRANSFER: the gravitational charge Q = sum_r T00
     satisfies Q/omega = const across species (masses, momenta) — the
     conformal-coupling EP result of r3 survives into 3+1D. This is the
     transferability the whole program hinges on.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DIR = os.path.dirname(os.path.abspath(__file__))
TH = 0.45
inv = 1 / np.sqrt(2)
results = {}

def coin(p0, p1, ang):
    c, s = np.cos(ang), 1j * np.sin(ang)
    return c * p0 + s * p1, s * p0 + c * p1

def step3d(p0, p1, th, dm):
    # x (sigma_x)
    up = inv * (p0 + p1); dn = inv * (p0 - p1)
    up = np.roll(up, 1, 0); dn = np.roll(dn, -1, 0)
    p0, p1 = inv * (up + dn), inv * (up - dn)
    p0, p1 = coin(p0, p1, th)
    # y (sigma_y)
    up = inv * (p0 - 1j * p1); dn = inv * (p0 + 1j * p1)
    up = np.roll(up, 1, 1); dn = np.roll(dn, -1, 1)
    p0, p1 = inv * (up + dn), inv * (1j * up - 1j * dn)
    p0, p1 = coin(p0, p1, th)
    # z (sigma_z)
    p0 = np.roll(p0, 1, 2); p1 = np.roll(p1, -1, 2)
    p0, p1 = coin(p0, p1, th)
    # mass gap
    p0, p1 = coin(p0, p1, dm)
    return p0, p1

def U_k(kx, ky, kz, th, dm):
    """one-step 2x2 operator in a plane-wave sector (for exact omega)."""
    sx = np.array([[0, 1], [1, 0]], complex)
    sy = np.array([[0, -1j], [1j, 0]])
    sz = np.array([[1, 0], [0, -1]], complex)
    I = np.eye(2, dtype=complex)
    def C(a): return np.cos(a) * I + 1j * np.sin(a) * sx
    # x shift in sigma_x basis:
    Hx = np.array([[np.cos(kx), 1j * np.sin(kx)], [1j * np.sin(kx), np.cos(kx)]])  # e^{i kx sx}
    Hy = np.array([[np.cos(ky), np.sin(ky)], [-np.sin(ky), np.cos(ky)]])           # e^{i ky sy}
    Hz = np.diag([np.exp(1j * kz), np.exp(-1j * kz)])                              # e^{i kz sz}
    return C(dm) @ C(th) @ Hz @ C(th) @ Hy @ C(th) @ Hx

def omega_of(k0, dm, direction=(1, 0, 0)):
    d = np.array(direction) / np.linalg.norm(direction)
    kx, ky, kz = k0 * d
    ev = np.linalg.eigvals(U_k(kx, ky, kz, TH, dm))
    return float(np.max(-np.angle(ev)))

L = 40
xg = np.arange(L)
Xc, Yc, Zc = np.meshgrid(xg, xg, xg, indexing="ij")

def packet3d(k0, dm, sig=5.0, direction=(1, 0, 0)):
    d = np.array(direction) / np.linalg.norm(direction)
    r2 = (Xc - L // 2) ** 2 + (Yc - L // 2) ** 2 + (Zc - L // 2) ** 2
    phase = k0 * (d[0] * Xc + d[1] * Yc + d[2] * Zc)
    g = np.exp(-r2 / (2 * sig ** 2)) * np.exp(1j * phase)
    # spinor: use eigenvector of U_k at central k for the positive branch
    kk = k0 * d
    ev, V = np.linalg.eig(U_k(kk[0], kk[1], kk[2], TH, dm))
    w = -np.angle(ev); b = int(np.argmax(w))
    sp = V[:, b]
    p0 = sp[0] * g; p1 = sp[1] * g
    n = np.sqrt((abs(p0) ** 2 + abs(p1) ** 2).sum())
    return p0 / n, p1 / n

# ---------- (A) T00 conservation under static theta ----------
th = np.full((L, L, L), TH)
p0, p1 = packet3d(0.6, 0.3)
prev0, prev1 = p0.copy(), p1.copy()
tot = []
for t in range(120):
    n0, n1 = step3d(p0, p1, th, 0.3)
    T00 = -0.5 * (np.conj(p0) * (n0 - prev0) + np.conj(p1) * (n1 - prev1)).imag
    if t > 1:
        tot.append(float(T00.sum()))
    prev0, prev1 = p0, p1
    p0, p1 = n0, n1
tot = np.array(tot)
results["A_T00_conservation_drift_3d"] = float(np.abs(tot - tot[0]).max())
results["A_T00_mean"] = float(tot.mean())
print(f"(A) 3+1D sum T00 drift over 120 steps: {results['A_T00_conservation_drift_3d']:.2e}")

# ---------- (C) equivalence-principle transfer ----------
species = [(0.6, 0.0, (1, 0, 0)), (0.6, 0.3, (1, 0, 0)), (0.6, 0.6, (1, 0, 0)),
           (0.4, 0.3, (1, 1, 0)), (0.8, 0.0, (1, 1, 1)), (0.5, 0.5, (1, 0, 0))]
rows = []
for (k0, dm, direction) in species:
    p0, p1 = packet3d(k0, dm, direction=direction)
    prev0, prev1 = p0.copy(), p1.copy()
    # advance one step to define T00 at t=1
    n0, n1 = step3d(p0, p1, th, dm)
    Qsum = 0.0
    for t in range(30):
        nn0, nn1 = step3d(n0, n1, th, dm)
        T00 = -0.5 * (np.conj(n0) * (nn0 - prev0) + np.conj(n1) * (nn1 - prev1)).imag
        Qsum += T00.sum()
        prev0, prev1 = n0, n1
        n0, n1 = nn0, nn1
    Q = Qsum / 30
    w = omega_of(k0, dm, direction)
    rows.append({"k0": k0, "dm": dm, "dir": direction, "omega": w, "Q": float(Q.real),
                 "Q_over_omega": float(Q.real / w)})
ratio = np.array([r["Q_over_omega"] for r in rows])
results["C_EP_transfer_spread"] = float(ratio.std() / abs(ratio.mean()))
results["C_rows"] = rows
print("\n(C) equivalence-principle transfer to 3+1D:")
for r in rows:
    print(f"    k0={r['k0']} dm={r['dm']} dir={r['dir']}: omega={r['omega']:.3f}  "
          f"Q={r['Q']:+.4f}  Q/omega={r['Q_over_omega']:+.4f}")
print(f"(C) EP spread of Q/omega across 6 species: {results['C_EP_transfer_spread']:.4f}")
print(f"    (<0.1 => the equivalence principle survives into 3+1D)")

json.dump(results, open(f"{DIR}/r4d_results.json", "w"), indent=1)
