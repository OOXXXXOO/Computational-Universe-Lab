"""Round 2, Exp 2.1 — the sign axiom, robust observables.

Two-body drift is k^2-suppressed for coin-mass species, and late-time lump
positions are dispersal artifacts. The robust sign observables are:

(a) SELF-BINDING: a single massive lump digs its own well (kappa>0) and
    self-focuses (a star), or anti-digs (kappa<0) and melts faster than the
    free (kappa=0) baseline. Observable: lump width w(t).
(b) SHAPIRO DELAY: relax the field around a frozen heavy lump; send a
    massless probe through; transit-time excess Dt vs empty background.
    kappa>0 => c dips => Dt>0 (probe arrives LATE) — the 1D gravitational
    time-delay dictionary.

Both are standard GR signatures. sign(kappa) should flip both coherently.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rulespace import core
from rulespace.render import Recorder

DIR = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(DIR, "figs")
N = 320
x = np.arange(N)
results = {}

# ---------------- (a) self-binding ----------------
DM, K0, SIG, T = 0.45, 0.10, 7.0, 3000
def width_run(kappa, record_mp4=None, title=""):
    a = np.array([0.30, 0, kappa, 0, 0, 0])
    psi0, psi1 = core.packet(N, N // 2, K0, SIG, dm=DM)
    th = np.full(N, core.TH_REF); th_prev = th.copy()
    rec = Recorder() if record_mp4 else None
    ws = []
    for t in range(T):
        rho, J = core.rho_J(psi0, psi1)
        c = (rho * x).sum()
        w = np.sqrt(max((rho * (x - c) ** 2).sum(), 0))
        ws.append(w)
        if rec and t % 20 == 0:
            rec.record(t, theta=th, rho=rho, judges={"lump width": w})
        th_new, _ = core.field_step(th, th_prev, rho, J, a)
        th_prev, th = th, th_new
        psi0, psi1 = core.walker_step(psi0, psi1, th, dm=DM)
    if rec:
        rec.save(record_mp4.replace(".mp4", ".npz"))
        rec.to_mp4(record_mp4, title=title, fps=16)
    return np.array(ws)

curves = {}
for kappa in [+0.05, 0.0, -0.05]:
    curves[kappa] = width_run(
        kappa,
        record_mp4=os.path.join(FIGS, "mov_r2a_selfbind.mp4") if kappa > 0 else None,
        title="SELF-BINDING: kappa=+0.05 — matter digs its own well and holds itself (a star)")
    results[f"width_final_kappa{kappa:+.2f}"] = float(curves[kappa][-1])
    print(f"kappa={kappa:+.2f}: width {curves[kappa][0]:.1f} -> {curves[kappa][-1]:.1f}")

# ---------------- (b) Shapiro delay ----------------
def relax_static_field(kappa, amp=0.045, w=10.0):
    rho_ext = amp * np.exp(-((x - N // 2) ** 2) / (2 * w ** 2))
    a_relax = np.array([0.30, 0, kappa, 0, 0, -0.08])       # damping to settle
    th = np.full(N, core.TH_REF); th_prev = th.copy()
    for t in range(4000):
        th_new, _ = core.field_step(th, th_prev, rho_ext, np.zeros(N), a_relax)
        th_prev, th = th, th_new
    return th

def transit_time(th_static, xs=50, xe=270, k0=0.9):
    psi0, psi1 = core.packet(N, xs, k0, 9.0, dm=0.0)
    pos = xs
    for t in range(1, 500):
        psi0, psi1 = core.walker_step(psi0, psi1, th_static, dm=0.0)
        rho, _ = core.rho_J(psi0, psi1)
        d = (x - xs + N // 2) % N - N // 2
        pos = xs + (rho * d).sum()
        if pos >= xe:
            frac = (pos - xe)
            return t - frac / max(pos - (pos - 1), 1e-9) * 0 + t
    return np.inf

th_flat = np.full(N, core.TH_REF)
t_base = transit_time(th_flat)
for kappa in [+0.05, -0.05]:
    th_s = relax_static_field(kappa)
    tt = transit_time(th_s)
    results[f"shapiro_dt_kappa{kappa:+.2f}"] = float(tt - t_base)
    results[f"theta_well_depth_kappa{kappa:+.2f}"] = float(th_s[N // 2] - core.TH_REF)
    print(f"kappa={kappa:+.2f}: transit {tt} vs base {t_base}  ->  Dt = {tt - t_base}"
          f"   (well depth {th_s[N//2]-core.TH_REF:+.4f})")

ok = (results["shapiro_dt_kappa+0.05"] > 0 and results["shapiro_dt_kappa-0.05"] < 0
      and results["width_final_kappa+0.05"] < results["width_final_kappa+0.00"]
      < results["width_final_kappa-0.05"])
results["sign_dictionary_confirmed"] = bool(ok)
json.dump(results, open(os.path.join(DIR, "r2a_results.json"), "w"), indent=1)
print("SIGN DICTIONARY (self-binding + Shapiro coherent):", ok)

# summary figure
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.4))
for kappa, col in [(+0.05, "tab:blue"), (0.0, "gray"), (-0.05, "tab:red")]:
    ax1.plot(curves[kappa], color=col, lw=1.5, label=f"$\\kappa$={kappa:+.2f}")
ax1.set(xlabel="t", ylabel="lump width", title="self-binding: $\\kappa>0$ holds itself together\n$\\kappa<0$ melts faster than free")
ax1.legend(); ax1.grid(alpha=0.3)
ks = [+0.05, -0.05]
ax2.bar([0, 1], [results[f"shapiro_dt_kappa{k:+.2f}"] for k in ks],
        color=["tab:blue", "tab:red"], width=0.5)
ax2.set_xticks([0, 1]); ax2.set_xticklabels(["$\\kappa=+0.05$", "$\\kappa=-0.05$"])
ax2.axhline(0, color="k", lw=0.8)
ax2.set(ylabel="transit-time excess $\\Delta t$ (steps)",
        title="Shapiro delay through the lump's well:\nlate = attractive geometry")
fig.tight_layout(); fig.savefig(f"{FIGS}/fig_r2a_sign.png", dpi=140)
print("figure saved")
