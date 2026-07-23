"""Round 2, Exp 2.1(final) — sign axiom via Shapiro delay (test-particle limit).

Protocol:
 1. Freeze a heavy lump rho_ext; relax the field WITH damping (preparation
    only) to its static profile theta_s(x). No clipping allowed (checked).
 2. Send a massless probe across the well on the STATIC geometry
    (test-particle limit: probe does not back-react).
 3. Transit-time excess Dt vs flat background:
       kappa>0  => theta well up => c dips => Dt > 0  (LATE = attractive)
       kappa<0  => c bumps       => Dt < 0  (EARLY = repulsive)

Also records the discovered 1+1D structural fact: with a MOVING source and
no dissipation the field energy accumulates without bound (no geometric
dilution in 1D) — the reason self-binding needs a radiation sink here.
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

def relax_static(kappa, amp=0.003, w=10.0):
    rho_ext = amp * np.exp(-((x - N // 2) ** 2) / (2 * w ** 2))
    a_rel = np.array([0.30, 0, kappa, 0, 0, -0.10])
    th = np.full(N, core.TH_REF); th_prev = th.copy()
    clip = 0.0
    for t in range(5000):
        th_new, s = core.field_step(th, th_prev, rho_ext, np.zeros(N), a_rel)
        clip += s
        th_prev, th = th, th_new
    return th, clip / 5000

def transit_time(th_s, xs=88, xe=232, k0=0.9):
    """cumulative circular-mean position; arrival when pos crosses xe"""
    psi0, psi1 = core.packet(N, xs, k0, 9.0, dm=0.0)
    def com_phase(rho):
        return np.angle((rho * np.exp(2j * np.pi * x / N)).sum())
    rho, _ = core.rho_J(psi0, psi1)
    ph_prev = com_phase(rho)
    pos = xs
    for t in range(1, 420):
        psi0, psi1 = core.walker_step(psi0, psi1, th_s, dm=0.0)
        rho, _ = core.rho_J(psi0, psi1)
        ph = com_phase(rho)
        dph = np.angle(np.exp(1j * (ph - ph_prev)))       # unwrapped increment
        pos += dph * N / (2 * np.pi)
        ph_prev = ph
        if pos >= xe:
            return t
    return np.inf

th_flat = np.full(N, core.TH_REF)
t_base = transit_time(th_flat)
results["t_base"] = float(t_base)
profiles = {}
for kappa in [+0.05, -0.05]:
    th_s, clip = relax_static(kappa)
    assert clip < 1e-6, f"clipping during relaxation (kappa={kappa})"
    tt = transit_time(th_s)
    profiles[kappa] = th_s
    results[f"dt_kappa{kappa:+.2f}"] = float(tt - t_base)
    results[f"well_kappa{kappa:+.2f}"] = float(th_s[N // 2] - core.TH_REF)
    print(f"kappa={kappa:+.2f}: well {th_s[N//2]-core.TH_REF:+.4f}  transit {tt} vs {t_base}  Dt={tt-t_base:+.1f}")

ok = results["dt_kappa+0.05"] > 0 and results["dt_kappa-0.05"] < 0
results["sign_dictionary_confirmed"] = bool(ok)
json.dump(results, open(os.path.join(DIR, "r2a_results.json"), "w"), indent=1)
print("SHAPIRO SIGN DICTIONARY confirmed:", ok)

# ---- movie: probe crossing the attractive well, verdict = position lag ----
kappa = 0.05
th_s = profiles[kappa]
psi0, psi1 = core.packet(N, 88, 0.9, 9.0, dm=0.0)
psiF0, psiF1 = core.packet(N, 88, 0.9, 9.0, dm=0.0)     # flat-space twin
rec = Recorder()
posW = posF = 88.0
phW = phF = None
def cph(r): return np.angle((r * np.exp(2j * np.pi * x / N)).sum())
rW, _ = core.rho_J(psi0, psi1); phW = cph(rW)
rF, _ = core.rho_J(psiF0, psiF1); phF = cph(rF)
for t in range(300):
    rW, _ = core.rho_J(psi0, psi1)
    if t % 4 == 0:
        rec.record(t, theta=th_s, rho=rW, judges={"lag vs flat (sites)": posF - posW})
    psi0, psi1 = core.walker_step(psi0, psi1, th_s, dm=0.0)
    psiF0, psiF1 = core.walker_step(psiF0, psiF1, th_flat, dm=0.0)
    rW, _ = core.rho_J(psi0, psi1); rF, _ = core.rho_J(psiF0, psiF1)
    p = cph(rW); posW += np.angle(np.exp(1j * (p - phW))) * N / (2 * np.pi); phW = p
    p = cph(rF); posF += np.angle(np.exp(1j * (p - phF))) * N / (2 * np.pi); phF = p
rec.save(os.path.join(FIGS, "mov_r2a_shapiro.npz"))
rec.to_mp4(os.path.join(FIGS, "mov_r2a_shapiro.mp4"),
           title="SHAPIRO DELAY (kappa=+0.05): probe crossing the well falls behind its flat-space twin",
           fps=16)
print("movie saved")
