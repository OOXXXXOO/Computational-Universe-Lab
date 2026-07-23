"""Round 2, Exp 2.2(v3) — Eotvos via damped-apparatus wells, quasi-static species.

Lessons baked in:
  * 1+1D undamped sourced field grows ballistically (no geometric dilution)
    -> the measuring apparatus needs a stabilizer: damping term = the spring
    of the scale, NOT part of the candidate physics. Documented as apparatus.
  * discrete energy bilinear gives rho*sin(omega); sin(w)~w only at small w
    -> choose species in the small-omega regime; the residual is a lattice
    artifact vanishing in the continuum limit (measured below).

Species (both quasi-static, vg ~ 0.02):
  A: dm=0.20, k0=0.10  -> omega_A ~ 0.22
  B: dm=0.50, k0=0.10  -> omega_B ~ 0.51   (2.3x energy contrast)

Apparatus: theta_tt = 0.3 Lap(theta) + kappa*src - 0.1*thetadot, kappa=0.05.
Static well depth A_s at T=900 (assert: no clipping).
  q_s = A_s / omega_s ;  eta = 2|q_A - q_B|/(q_A + q_B)

Verdict table:
  src = rho:  predicted eta ~ 2|wB-wA|/(wA+wB) ~ 0.79  -> FAIL (>0.1)
  src = T00:  predicted eta ~ |d(sin w/w)| ~ 0.04     -> PASS (<0.1)
=> the equivalence principle SELECTS the energy density as the source.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rulespace import core

DIR = os.path.dirname(os.path.abspath(__file__))
N, TSTAR, KAPPA = 256, 900, 0.006
A_APP = np.array([0.30, 0, KAPPA, 0, 0, -0.10])

def omega_of(k0, dm):
    ev = np.linalg.eigvals(core.walk_matrix(k0, core.TH_REF, dm))
    return float(np.max(-np.angle(ev)))

SPECIES = {"A": dict(k0=0.10, dm=0.20, sig=12.0),
           "B": dict(k0=0.10, dm=0.50, sig=12.0)}
OMEGA = {s: omega_of(v["k0"], v["dm"]) for s, v in SPECIES.items()}

def well_depth(spec, source):
    k0, dm, sig = spec["k0"], spec["dm"], spec["sig"]
    psi0, psi1 = core.packet(N, N // 2, k0, sig, dm=dm)
    prev0, prev1 = psi0.copy(), psi1.copy()
    th = np.full(N, core.TH_REF); th_prev = th.copy()
    clip = 0.0
    for t in range(TSTAR):
        nxt0, nxt1 = core.walker_step(psi0, psi1, th, dm=dm)
        if source == "rho":
            src, _ = core.rho_J(psi0, psi1)
        else:
            d0 = nxt0 - prev0; d1 = nxt1 - prev1
            src = -0.5 * (np.conj(psi0) * d0 + np.conj(psi1) * d1).imag
        _, J = core.rho_J(psi0, psi1)
        th_new, s = core.field_step(th, th_prev, src, J, A_APP)
        clip += s
        th_prev, th = th, th_new
        prev0, prev1 = psi0, psi1
        psi0, psi1 = nxt0, nxt1
    assert clip / TSTAR < 1e-9, f"apparatus clipped ({source},{spec})"
    return float(np.max(np.abs(th - core.TH_REF)))

results = {"omega_A": OMEGA["A"], "omega_B": OMEGA["B"],
           "eta_pass_threshold": 0.10}
print(f"species energies: A {OMEGA['A']:.3f}  B {OMEGA['B']:.3f}  (contrast {OMEGA['B']/OMEGA['A']:.2f}x)")
for source in ["rho", "T00"]:
    q = {}
    for s, spec in SPECIES.items():
        A_s = well_depth(spec, source)
        q[s] = A_s / OMEGA[s]
        results[f"well_{source}_{s}"] = A_s
    eta = 2 * abs(q["A"] - q["B"]) / (q["A"] + q["B"])
    results[f"eta_{source}"] = float(eta)
    print(f"source={source:4s}: wells A={results[f'well_{source}_A']:.4f} "
          f"B={results[f'well_{source}_B']:.4f}  ->  eta = {eta:.3f}  "
          f"[{'PASS' if eta < 0.1 else 'FAIL'}]")

results["T00_selected"] = bool(results["eta_T00"] < 0.1 < results["eta_rho"])
# lattice-artifact check: eta_T00 should shrink as species get lighter (continuum)
SPECIES2 = {"A": dict(k0=0.07, dm=0.10, sig=14.0), "B": dict(k0=0.07, dm=0.25, sig=14.0)}
OM2 = {s: omega_of(v["k0"], v["dm"]) for s, v in SPECIES2.items()}
qq = {}
for s, spec in SPECIES2.items():
    qq[s] = well_depth(spec, "T00") / OM2[s]
results["eta_T00_lighter"] = float(2 * abs(qq["A"] - qq["B"]) / (qq["A"] + qq["B"]))
print(f"continuum-limit check: eta_T00 lighter species = {results['eta_T00_lighter']:.3f} "
      f"(should shrink toward 0)")
json.dump(results, open(os.path.join(DIR, "r2b_results.json"), "w"), indent=1)
print("EQUIVALENCE PRINCIPLE SELECTS T00:", results["T00_selected"])
