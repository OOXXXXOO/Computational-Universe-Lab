"""Exp 6: leakage in the Dirac QCA -> predicted dispersion corrections
         -> confrontation with real Lorentz-violation bounds.

Model: Dirac QCA on a strip  x in Z (visible)  x  y in Z_H (compact hidden).
2-component spinor. One timestep:
    U(k) = X(k) . C(theta) . L
  X(k)     = diag(e^{ik}, e^{-ik})           spin-conditioned x-shift
  C(theta) = exp(i theta sigma_x)            mass coin
  L        = expm(i M),  M = g_kin * Lap_y (x) sigma_x   (KK kinetic term)
                        + g_d  * |y=0><y=0| (x) sigma_c  (leakage DEFECT,
                                             channel sigma_c in {x,z,tilt})

Predictions to test (the channel dictionary):
  sigma_x channel commutes with the mass coin -> pure mass renormalisation:
      each KK mode stays EXACTLY Dirac-shaped. Invisible to dispersion tests.
      But: applied to a massless "photon", it INDUCES A MASS -> photon-mass bound.
  sigma_z channel commutes with the shift -> per-mode momentum offset (k -> k+a):
      spin-dependent CPT-odd background, the SME b-coefficient analog
      -> clock/comagnetometer bounds (1e-33 GeV!).
  tilted channel -> both + genuine shape deformation (c_eff shift, k^3/k^4 terms)
      -> Delta-c bounds and (weakly) GRB time-of-flight.

Outputs: channel dictionary figure, KK band structure, coefficient-vs-g scaling,
exclusion regions in the (eps/l_Pl, g) plane from real experimental bounds.
"""
import numpy as np, json, os
from scipy.linalg import expm
from scipy.optimize import curve_fit
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "figs")
RES = os.path.join(DIR, "exp6_results.json")
results = {}

sx = np.array([[0, 1], [1, 0]], complex)
sy = np.array([[0, -1j], [1j, 0]])
sz = np.array([[1, 0], [0, -1]], complex)
I2 = np.eye(2, dtype=complex)

H, G_KIN = 8, 0.30
TH_E, TH_PH = 0.20, 0.0          # electron-analog mass angle; photon-analog = 0

def lap_y(H):
    L = 2 * np.eye(H)
    for y in range(H):
        L[y, (y + 1) % H] -= 1; L[(y + 1) % H, y] -= 1
    return L

def build_L(g_d, chan):
    M = G_KIN * np.kron(lap_y(H), sx)
    D = np.zeros((H, H)); D[0, 0] = 1.0
    sc = {"x": sx, "z": sz, "tilt": (sx + sz) / np.sqrt(2)}[chan]
    M = M + g_d * np.kron(D, sc)
    return expm(1j * M)

def bands(theta, g_d, chan, ks):
    """visible (q=0-dominant, omega>0) band + full spectrum"""
    Lop = build_L(g_d, chan)
    Cth = np.kron(np.eye(H), expm(1j * theta * sx))
    P0 = np.ones(H) / np.sqrt(H)                     # q=0 projector components
    w_vis = np.empty(len(ks)); allw = np.empty((len(ks), 2 * H))
    for a, k in enumerate(ks):
        Xk = np.kron(np.eye(H), np.diag([np.exp(1j * k), np.exp(-1j * k)]))
        U = Xk @ Cth @ Lop
        ev, V = np.linalg.eig(U)
        w = -np.angle(ev)
        allw[a] = np.sort(w)
        # weight of each eigenvector on the q=0 subspace
        Vy = V.reshape(H, 2, 2 * H)
        wq0 = np.abs(np.einsum("y,ysj->sj", P0, Vy)) ** 2
        wq0 = wq0.sum(axis=0)
        cand = np.where(w > 1e-9)[0]
        w_vis[a] = w[cand[np.argmax(wq0[cand])]]
    return w_vis, allw

def extract(theta, g_d, chan, kmax=0.5, npts=161):
    ks = np.linspace(-kmax, kmax, npts)
    w, _ = bands(theta, g_d, chan, ks)
    f = lambda k, m, c, a: np.sqrt(m * m + c * c * (k + a) ** 2)
    p0 = [max(theta, 1e-3), 1.0, 0.0]
    (m, c, a), _ = curve_fit(f, ks, w, p0=p0, maxfev=20000)
    m = abs(m); c = abs(c)
    resid = w - f(ks, m, c, a)
    B = np.vstack([np.ones_like(ks), ks, ks ** 2, ks ** 3, ks ** 4]).T
    coef, *_ = np.linalg.lstsq(B, resid, rcond=None)
    return {"m": m, "c": c, "a": a, "z3": coef[3], "z4": coef[4],
            "resid_rms": float(np.sqrt((resid ** 2).mean()))}

# ---------------- (a) channel dictionary ----------------
ks = np.linspace(-np.pi / 2, np.pi / 2, 301)
base, _ = bands(TH_E, 0.0, "x", ks)
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), sharey=True)
gd_show = 0.35
for ax, chan, ttl in [(axes[0], "x", "sigma_x leak: mass renormalisation\n(Lorentz shape EXACTLY preserved)"),
                      (axes[1], "z", "sigma_z leak: CPT-odd momentum shift\n(band minimum moves off k=0)"),
                      (axes[2], "tilt", "tilted leak: both + shape deformation")]:
    w, _ = bands(TH_E, gd_show, chan, ks)
    ax.plot(ks, base, "k--", lw=1.2, label="g_d=0 baseline")
    ax.plot(ks, w, color="tab:red", lw=1.6, label=f"g_d={gd_show}")
    e = extract(TH_E, gd_show, chan)
    ax.set(title=ttl + f"\nm={e['m']:.4f} a={e['a']:.4f} c={e['c']:.5f}", xlabel="k")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    results[f"dict_{chan}"] = {k: float(v) for k, v in e.items()}
axes[0].set_ylabel("omega(k) of visible band")
fig.suptitle("The leakage-channel dictionary: the ALGEBRA of the leak operator decides which Lorentz-violation it generates", fontsize=11)
fig.tight_layout(); fig.savefig(f"{OUT}/fig6a_channel_dictionary.png", dpi=140); plt.close(fig)

# ---------------- (b) KK band structure ----------------
ks2 = np.linspace(-np.pi, np.pi, 401)
_, allw0 = bands(TH_E, 0.0, "x", ks2)
_, allwD = bands(TH_E, 0.4, "tilt", ks2)
fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5), sharey=True)
for ax, aw, ttl in [(axes[0], allw0, "g_d=0: clean Kaluza-Klein tower\nm_n = theta + 2 g_kin (1-cos q_n)"),
                    (axes[1], allwD, "g_d=0.4 tilted defect: modes mix,\nvisible band inherits corrections")]:
    for j in range(2 * H):
        ax.plot(ks2, aw[:, j], lw=0.7, color="tab:blue", alpha=0.7)
    ax.set(title=ttl, xlabel="k", ylim=(-np.pi, np.pi)); ax.grid(alpha=0.3)
axes[0].set_ylabel("omega")
fig.suptitle("A compact hidden dimension seen from 1D: the KK tower of the Dirac QCA strip (H=8)")
fig.tight_layout(); fig.savefig(f"{OUT}/fig6b_kk_tower.png", dpi=140); plt.close(fig)

# ---------------- (c) coefficient scaling vs g_d ----------------
gds = np.geomspace(2e-3, 0.4, 10)
scal = {}
for chan in ["x", "z", "tilt"]:
    for theta, tag in [(TH_E, "e"), (TH_PH, "ph")]:
        rows = []
        for gd in gds:
            e = extract(theta, gd, chan)
            rows.append(e)
        scal[f"{chan}_{tag}"] = rows

def series(chan, tag, key, ref0):
    return np.array([abs(r[key] - ref0) for r in scal[f"{chan}_{tag}"]])

ref_e = extract(TH_E, 0.0, "x"); ref_ph = extract(TH_PH, 0.0, "x")
results["baseline_e"] = {k: float(v) for k, v in ref_e.items()}
results["baseline_ph"] = {k: float(v) for k, v in ref_ph.items()}

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))
panels = [
    ("z", "e", "a", 0.0, "CPT-odd shift |a| (sigma_z leak, electron)", "SME b-type"),
    ("x", "ph", "m", 0.0, "induced photon mass m (sigma_x leak, theta=0)", "photon-mass bound"),
    ("tilt", "e", "c", ref_e["c"], "|Delta c| speed shift (tilted leak)", "Delta-c bounds"),
]
slopes = {}
for ax, (chan, tag, key, r0, ttl, sub) in zip(axes, panels):
    ys = series(chan, tag, key, r0)
    good = (ys > 1e-12) & (np.arange(len(ys)) < 6)     # perturbative window
    sl = np.polyfit(np.log(gds[good]), np.log(ys[good]), 1)[0]
    slopes[f"{chan}_{tag}_{key}"] = float(sl)
    ax.loglog(gds, ys, "o-", color="tab:red")
    ax.set(xlabel="leakage g_d", title=f"{ttl}\nlog-log slope = {sl:.2f}  ({sub})")
    ax.grid(alpha=0.3, which="both")
results["slopes"] = slopes
results["alpha_a"] = float(series("z", "e", "a", 0)[0] / gds[0])          # a ~ alpha_a g
mg = series("x", "ph", "m", 0); results["alpha_m"] = float(mg[0] / gds[0])
dc = series("tilt", "e", "c", ref_e["c"])
results["alpha_c"] = float(dc[4] / gds[4] ** 2)     # Dc ~ alpha_c g^2, perturbative window
zt = np.array([abs(r["z3"]) for r in scal["tilt_ph"]])
results["zeta3_tilt_ph_max"] = float(zt.max())
results["resid_rms_max"] = float(max(r["resid_rms"] for v in scal.values() for r in v))
fig.suptitle("Scaling of induced Lorentz-violating coefficients with leakage strength")
fig.tight_layout(); fig.savefig(f"{OUT}/fig6c_scaling.png", dpi=140); plt.close(fig)

# ---------------- (d) exclusion plot with REAL bounds ----------------
E_PL_GeV = 1.22e19
BND_b_GeV = 1e-33                 # comagnetometer, SME b-type (order of magnitude)
BND_mph_GeV = 1e-27               # photon mass < 1e-18 eV = 1e-27 GeV
BND_dc = 1e-15                    # photon/electron speed difference
E_QG2 = 1.3e11                    # GeV, GRB 090510 quadratic bound

alpha_a, alpha_m, alpha_c = results["alpha_a"], results["alpha_m"], results["alpha_c"]
eps = np.geomspace(1, 1e10, 300)                 # lattice spacing in Planck lengths
E_lat = E_PL_GeV / eps                            # lattice energy scale in GeV

g_b = (BND_b_GeV / E_lat) / alpha_a               # exclude g > g_b   (sigma_z, matter)
g_m = (BND_mph_GeV / E_lat) / alpha_m             # exclude g > g_m   (sigma_x, photon)
g_c = np.full_like(eps, np.sqrt(BND_dc / alpha_c))# exclude g > g_c   (tilt, eps-indep)
# GRB quadratic: omega = ck(1 + eta2 k^2), eta2 ~ O(g^2) at most ->
# bound eta2 < (E_lat/E_QG2)^2; with eta2 ~ alpha_c g^2 (generous) :
g_grb = np.sqrt(np.minimum((E_lat / E_QG2) ** 2 / alpha_c, 1e6))

fig, ax = plt.subplots(figsize=(8.6, 5.6))
ax.fill_between(eps, g_b, 1, color="tab:red", alpha=0.35,
                label="EXCLUDED: comagnetometer b-type < 1e-33 GeV (sigma_z leak, matter)")
ax.fill_between(eps, g_m, 1, color="tab:orange", alpha=0.35,
                label="EXCLUDED: photon mass < 1e-18 eV (sigma_x leak, photon)")
ax.fill_between(eps, g_c, 1, color="tab:blue", alpha=0.25,
                label="EXCLUDED: |Delta c| < 1e-15 (tilted leak)")
ax.plot(eps, g_grb, "g--", lw=1.5,
        label="GRB090510 quadratic (E_QG2>1.3e11 GeV): bites only at eps >~ 1e8 l_Pl")
ax.set(xscale="log", yscale="log", xlim=(1, 1e10), ylim=(1e-60, 1),
       xlabel="lattice spacing  eps / l_Planck", ylabel="leakage coupling g_d",
       title="Real experiments pruning the toy rule space\n"
             "clocks cut ~30 orders of magnitude deeper than GRB time-of-flight")
ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.3, which="both")
fig.tight_layout(); fig.savefig(f"{OUT}/fig6d_exclusion.png", dpi=140); plt.close(fig)

# headline numbers at eps = l_Pl
results["g_max_at_planck"] = {
    "sigma_z_matter_comagnetometer": float(g_b[0]),
    "sigma_x_photon_mass": float(g_m[0]),
    "tilt_delta_c": float(g_c[0]),
    "grb_quadratic": float(g_grb[0])}
json.dump(results, open(RES, "w"), indent=1, default=float)
print(json.dumps(results["g_max_at_planck"], indent=1))
print("slopes:", json.dumps(slopes, indent=1))
print("alpha_a=%.4f alpha_m=%.4f alpha_c=%.4f zeta3max=%.2e resid=%.2e"
      % (alpha_a, alpha_m, alpha_c, results["zeta3_tilt_ph_max"], results["resid_rms_max"]))
