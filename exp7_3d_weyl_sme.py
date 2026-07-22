"""Exp 7: 3+1D Weyl/Dirac QCA + compact 4th dimension + leakage
         -> numerical extraction of SME coefficients, channel-resolved.

Construction:
  3D Weyl walk (right-handed):  W_R(k) = e^{i kz sz} e^{i ky sy} e^{i kx sx}
  Left-handed partner:          W_L(k) = W_R(-k) form  (e^{-i kz sz} ...)
  Dirac pairing (4-comp, chirality space tau):
      U0(k) = C(theta) . diag(W_R, W_L),   C(theta) = exp(i theta tau_x (x) I)
  Compact 4th dimension w (H sites, periodic):
      L = expm(i M),
      M = g_kin * Lap_w (x) (tau_y (x) I)     KK kinetic (anticommutes with
                                              alpha_i and beta -> true KK tower
                                              m_n^2 = theta^2 + (g_kin l_n)^2)
        + g_d * |w=0><w=0| (x) GAMMA          leakage defect, channel GAMMA

Channel dictionary to test (chiral structure decides the SME coefficient):
  GAMMA = tau_0 (x) sigma_z  chirally SYMMETRIC spin leak
        -> for L-chirality momentum enters as -k.sigma, so a same-sign sigma_z
           term is a spin-coupled background: SME b_z type. OBSERVABLE:
           lifts spin degeneracy of the bands. Comagnetometer kills it.
  GAMMA = tau_z (x) sigma_z  chirally ANTI-symmetric spin leak
        -> equivalent to a uniform momentum shift k_z -> k_z + a for both
           chiralities: SME a_z type. Removable by field redefinition:
           bands translate rigidly, NO splitting. Physically invisible
           (for a single species without gravity).
  GAMMA = tau_x (x) I        mass-coin channel -> mass renormalisation.
  GAMMA = tau_0 (x) I        scalar phase -> a_0 (overall energy offset).

Observables extracted per channel from exact eigenphases of the 4H x 4H
unitary U(k) along the k_z axis:
  dm  : shift of the band bottom energy  omega_min
  da  : shift of the band bottom POSITION in k_z (rigid translation)
  db  : half the spin splitting at fixed k_z (degeneracy lift)
  da0 : uniform energy offset at the band bottom (after dm removal via k=0 pair)
Plus the baseline: intrinsic anisotropy of the pure 3D walk (the fermionic
analog of Mlodinow-Brun's photon-sector anisotropy).
"""
import numpy as np, json, os
from scipy.linalg import expm
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "figs")
RES = os.path.join(DIR, "exp7_results.json")
results = {}

s0 = np.eye(2, dtype=complex)
sx = np.array([[0, 1], [1, 0]], complex)
sy = np.array([[0, -1j], [1j, 0]])
sz = np.array([[1, 0], [0, -1]], complex)

def eH(A):  # exp(iA) for Hermitian A
    return expm(1j * A)

def W_R(kx, ky, kz):
    return eH(kz * sz) @ eH(ky * sy) @ eH(kx * sx)

def W_L(kx, ky, kz):
    return eH(-kz * sz) @ eH(-ky * sy) @ eH(-kx * sx)

def kron4(t, s):
    return np.kron(t, s)

TAU0, TAUX, TAUY, TAUZ = s0, sx, sy, sz
THETA, H, G_KIN = 0.15, 4, 0.35

def lap_w(H):
    L = 2 * np.eye(H)
    for w in range(H):
        L[w, (w + 1) % H] -= 1; L[(w + 1) % H, w] -= 1
    return L

CHANNELS = {
    "b-type  tau0(x)sz (chiral-symmetric)": kron4(TAU0, sz),
    "a-type  tauz(x)sz (chiral-antisym)":   kron4(TAUZ, sz),
    "mass    taux(x)I":                     kron4(TAUX, s0),
    "a0      tau0(x)I":                     kron4(TAU0, s0),
}

def build_U(kx, ky, kz, g_d, Gamma):
    D = np.zeros((4, 4), complex)   # Dirac 4x4 walk block
    D[:2, :2] = W_R(kx, ky, kz); D[2:, 2:] = W_L(kx, ky, kz)
    C = eH(THETA * kron4(TAUX, s0))
    M = G_KIN * np.kron(lap_w(H), kron4(TAUY, s0))
    Dw = np.zeros((H, H)); Dw[0, 0] = 1.0
    M = M + g_d * np.kron(Dw, Gamma)
    L = expm(1j * M)
    U4 = C @ D                         # 4x4, k-dependent
    return np.kron(np.eye(H), U4) @ L  # 4H x 4H

P0w = np.ones(H) / np.sqrt(H)          # q=0 projector in w

def visible_bands(kz_arr, g_d, Gamma, nbands=2):
    """the two lowest positive bands dominated by the q=0 KK mode, along k_z"""
    out = np.empty((len(kz_arr), nbands))
    for i, kz in enumerate(kz_arr):
        U = build_U(0.0, 0.0, kz, g_d, Gamma)
        ev, V = np.linalg.eig(U)
        w = -np.angle(ev)
        Vw = V.reshape(H, 4, 4 * H)
        wq0 = (np.abs(np.einsum("h,hsj->sj", P0w, Vw)) ** 2).sum(axis=0)
        pos = np.where(w > 1e-9)[0]
        sel = pos[np.argsort(-wq0[pos])][: nbands]
        out[i] = np.sort(w[sel])
    return out

def observables(g_d, Gamma, kz_probe=0.25):
    kz = np.linspace(-0.45, 0.45, 121)
    b = visible_bands(kz, g_d, Gamma)
    lower = b[:, 0]
    j = np.argmin(lower)
    # quadratic interpolation of the band bottom
    if 0 < j < len(kz) - 1:
        x0, x1, x2 = kz[j - 1: j + 2]; y0, y1, y2 = lower[j - 1: j + 2]
        d = (y0 - 2 * y1 + y2)
        kmin = x1 - 0.5 * (y2 - y0) / d * (x1 - x0) if abs(d) > 1e-14 else x1
        wmin = y1 - 0.125 * (y2 - y0) ** 2 / d if abs(d) > 1e-14 else y1
    else:
        kmin, wmin = kz[j], lower[j]
    jp = np.argmin(np.abs(kz - kz_probe))
    split = b[jp, 1] - b[jp, 0]
    return {"kmin": kmin, "wmin": wmin, "split": split}

# ---------------- baseline ----------------
base = observables(0.0, CHANNELS["mass    taux(x)I"])
results["baseline"] = {k: float(v) for k, v in base.items()}
# KK tower masses check
kz0 = np.array([0.0])
U = build_U(0, 0, 0, 0.0, CHANNELS["mass    taux(x)I"])
w_all = np.sort(np.abs(-np.angle(np.linalg.eigvals(U))))
lam = np.linalg.eigvalsh(lap_w(H))
kk_pred = np.sort(np.sqrt(THETA ** 2 + (G_KIN * lam) ** 2))
results["kk_masses_measured"] = [float(x) for x in np.unique(np.round(w_all, 6))[:4]]
results["kk_masses_predicted"] = [float(x) for x in np.unique(np.round(kk_pred, 6))]

# ---------------- channel scan ----------------
gds = np.geomspace(3e-3, 0.15, 7)
chan_data = {}
for name, Gamma in CHANNELS.items():
    rows = [observables(g, Gamma) for g in gds]
    dm = np.array([abs(r["wmin"] - base["wmin"]) for r in rows])
    da = np.array([abs(r["kmin"] - base["kmin"]) for r in rows])
    db = np.array([abs(r["split"] - base["split"]) / 2 for r in rows])
    chan_data[name] = {"dm": dm, "da": da, "db": db}
    def slope_alpha(y):
        good = y > 1e-9
        if good.sum() < 3: return 0.0, 0.0
        sl = np.polyfit(np.log(gds[good]), np.log(y[good]), 1)[0]
        return float(sl), float(y[0] / gds[0])
    results[f"chan::{name}"] = {
        "dm_slope_alpha": slope_alpha(dm), "da_slope_alpha": slope_alpha(da),
        "db_slope_alpha": slope_alpha(db),
        "dm0": float(dm[0]), "da0": float(da[0]), "db0": float(db[0]), "g0": float(gds[0])}

# ---------------- intrinsic anisotropy of the pure 3D Weyl walk ----------------
def omega_weyl(kvec):
    U = W_R(*kvec)
    return float(np.max(-np.angle(np.linalg.eigvals(U))))

k0s = np.geomspace(0.02, 0.6, 12)
dirs = {"100": np.array([1, 0, 0]), "110": np.array([1, 1, 0]) / np.sqrt(2),
        "111": np.array([1, 1, 1]) / np.sqrt(3)}
aniso = []
for k0 in k0s:
    ws = {d: omega_weyl(k0 * v) for d, v in dirs.items()}
    aniso.append((max(ws.values()) - min(ws.values())) / k0)   # Delta v between directions
aniso = np.array(aniso)
sl_an = np.polyfit(np.log(k0s), np.log(np.maximum(aniso, 1e-16)), 1)[0]
results["anisotropy_slope_in_k"] = float(sl_an)
results["anisotropy_coeff"] = float(aniso[0] / k0s[0] ** round(sl_an))

# ---------------- figures ----------------
kz = np.linspace(-0.45, 0.45, 121)
fig, axes = plt.subplots(1, 4, figsize=(16.4, 4.1), sharey=True)
gd_show = 0.12
for ax, (name, Gamma) in zip(axes, CHANNELS.items()):
    b0 = visible_bands(kz, 0.0, Gamma)
    b1 = visible_bands(kz, gd_show, Gamma)
    ax.plot(kz, b0[:, 0], "k--", lw=1); ax.plot(kz, b0[:, 1], "k--", lw=1, label="g=0")
    ax.plot(kz, b1[:, 0], color="tab:red", lw=1.5)
    ax.plot(kz, b1[:, 1], color="tab:orange", lw=1.5, label=f"g={gd_show}")
    ax.set(title=name.split("  ")[0] + "\n" + name.split("  ")[1], xlabel="k_z")
    ax.grid(alpha=0.3); ax.legend(fontsize=7)
axes[0].set_ylabel("omega (visible KK-0 bands, spin pair)")
fig.suptitle("3+1D channel dictionary: chiral structure of the leak decides the SME operator "
             "(b: spin splitting / a: rigid translation / mass: bottom lifts / a0: offset)", fontsize=11)
fig.tight_layout(); fig.savefig(f"{OUT}/fig7a_channels_3d.png", dpi=140); plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3))
mark = dict(zip(CHANNELS, ["o", "s", "^", "d"]))
for key, ttl, ax in [("db", "spin splitting  ->  SME b_z", axes[0]),
                     ("da", "band translation  ->  SME a_z", axes[1]),
                     ("dm", "bottom shift  ->  mass renorm.", axes[2])]:
    for name in CHANNELS:
        y = chan_data[name][key]
        ax.loglog(gds, np.maximum(y, 1e-12), mark[name] + "-", label=name.split("  ")[0], ms=4)
    ax.set(xlabel="leakage g_d", title=ttl); ax.grid(alpha=0.3, which="both")
    ax.set_ylim(1e-9, 1)
axes[0].legend(fontsize=8)
fig.suptitle("Channel-resolved SME coefficients vs leakage strength (4H x 4H exact eigenphases, H=4)")
fig.tight_layout(); fig.savefig(f"{OUT}/fig7b_sme_scaling.png", dpi=140); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.2, 4.4))
ax.loglog(k0s, aniso, "o-", color="tab:red")
ax.set(xlabel="|k| (lattice units)", ylabel="max directional velocity spread",
       title=f"Intrinsic anisotropy of the pure 3D Weyl walk: slope={sl_an:.2f}\n"
             "(fermionic analog of Mlodinow-Brun photon anisotropy; bounds eps itself)")
ax.grid(alpha=0.3, which="both")
fig.tight_layout(); fig.savefig(f"{OUT}/fig7c_anisotropy.png", dpi=140); plt.close(fig)

json.dump(results, open(RES, "w"), indent=1, default=float)
for k, v in results.items():
    if k.startswith("chan::"): print(k, json.dumps(v))
print("kk meas:", results["kk_masses_measured"], "pred:", results["kk_masses_predicted"])
print("aniso slope:", results["anisotropy_slope_in_k"], "coeff:", results["anisotropy_coeff"])
