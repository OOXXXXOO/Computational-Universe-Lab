"""Round 6b — the full source->field->response loop in 3+1D:
gravitational deflection of a test packet passing a mass.

1. A heavy mass rho_M at the center sources a static 3D theta-well
   (FFT Poisson, the r4a machinery — dilution ~1/r, finite well).
2. A massless test packet is launched in +x with an impact parameter b in y.
3. Measure the transverse velocity <v_y> gained = deflection toward the mass.
   Sign (toward the mass) and scaling with impact parameter test that the
   emergent 3+1D geometry deflects matter attractively — the response half
   of the loop, in 3+1D.

Combined with r4d (T00 sources & conserves) and r6a (F=tan th * T00 (v/c)^2),
this closes the qualitative C1 loop in 3+1D: matter -> T00 -> theta-well ->
deflection of matter. (Quantitative GR comparison is out of scope: the toy is
SCALAR gravity, see report.)
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DIR = os.path.dirname(os.path.abspath(__file__))
TH = 0.45
inv = 1 / np.sqrt(2)
results = {}
L = 48
xg = np.arange(L)
X, Y, Z = np.meshgrid(xg, xg, xg, indexing="ij")
c0 = L // 2

def step3d(p0, p1, th):
    up = inv * (p0 + p1); dn = inv * (p0 - p1)
    up = np.roll(up, 1, 0); dn = np.roll(dn, -1, 0)
    p0, p1 = inv * (up + dn), inv * (up - dn)
    c, s = np.cos(th), 1j * np.sin(th); p0, p1 = c * p0 + s * p1, s * p0 + c * p1
    up = inv * (p0 - 1j * p1); dn = inv * (p0 + 1j * p1)
    up = np.roll(up, 1, 1); dn = np.roll(dn, -1, 1)
    p0, p1 = inv * (up + dn), inv * (1j * up - 1j * dn)
    c, s = np.cos(th), 1j * np.sin(th); p0, p1 = c * p0 + s * p1, s * p0 + c * p1
    p0 = np.roll(p0, 1, 2); p1 = np.roll(p1, -1, 2)
    return p0, p1

# static well from a central heavy mass (FFT Poisson)
rho_M = np.exp(-((X - c0) ** 2 + (Y - c0) ** 2 + (Z - c0) ** 2) / (2 * 3.5 ** 2))
src = rho_M - rho_M.mean()
ks = [2 * np.pi * np.fft.fftfreq(L)] * 3
K = np.meshgrid(*ks, indexing="ij")
lam = sum(2 - 2 * np.cos(k) for k in K)
S = np.fft.fftn(0.03 * src)
Th = np.zeros_like(S); nz = lam > 1e-12; Th[nz] = S[nz] / lam[nz]
theta_well = TH + np.real(np.fft.ifftn(Th))
results["well_depth"] = float(theta_well.max() - TH)
results["c_min"] = float(np.cos(theta_well.max()))
print(f"static well depth {results['well_depth']:.3f}, c_min {results['c_min']:.3f}")

def packet3d(x0, y0, z0, k0, sig=4.0):
    g = np.exp(-((X - x0) ** 2 + (Y - y0) ** 2 + (Z - z0) ** 2) / (2 * sig ** 2)) * np.exp(1j * k0 * X)
    p0 = g.astype(complex); p1 = 0.2 * g
    n = np.sqrt((abs(p0) ** 2 + abs(p1) ** 2).sum()); return p0 / n, p1 / n

kyg = 2 * np.pi * np.fft.fftfreq(L)
KY = kyg[np.newaxis, :, np.newaxis]
def mean_ky(p0, p1):
    f0 = np.fft.fftn(p0); f1 = np.fft.fftn(p1)
    pk = np.abs(f0) ** 2 + np.abs(f1) ** 2; pk /= pk.sum()
    return float((pk * KY).sum())

def run_deflect(b, th_field, k0=0.9, T=30):
    """launch moving +x at impact parameter b in y; measure transverse impulse d<k_y>"""
    p0, p1 = packet3d(8, c0 + b, c0, k0)
    ky0 = mean_ky(p0, p1)
    for t in range(T):
        p0, p1 = step3d(p0, p1, th_field)
    return float(mean_ky(p0, p1) - ky0)

th_flat = np.full((L, L, L), TH)
print("\nimpact parameter b -> transverse impulse d<k_y> (toward center mass => negative for b>0):")
rows = []
for b in [6, 9, 12, 16]:
    dk_mass = run_deflect(b, theta_well)
    dk_free = run_deflect(b, th_flat)
    imp = dk_mass - dk_free
    rows.append({"b": b, "impulse": imp, "dk_mass": dk_mass, "dk_free": dk_free})
    print(f"  b={b:+d}: impulse d<k_y> = {imp:+.5f}  (mass {dk_mass:+.5f}, free {dk_free:+.5f})")
attractive = all(r["impulse"] < 0 for r in rows)
falloff = all(abs(rows[i]["impulse"]) >= abs(rows[i + 1]["impulse"]) - 2e-4 for i in range(len(rows) - 1))
results["deflection"] = rows
results["attractive_3d"] = bool(attractive)
results["deflection_falls_with_b"] = bool(falloff)
print(f"\n3+1D attractive deflection (impulse toward mass for all b): {attractive}")
print(f"deflection weakens with impact parameter: {falloff}")
json.dump(results, open(f"{DIR}/r6b_results.json", "w"), indent=1)
