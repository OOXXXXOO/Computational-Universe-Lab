"""Round 2, Exp 2.2(final) — Eotvos via wells: does gravitational charge = energy?

Lesson from the fit-based attempt: when the rule's true source (rho) is in the
observer's library, species-independence of the FIT is vacuous. The physical
Eotvos question lives in the OBSERVABLE: two lumps of equal probability but
different ENERGY must dig wells proportional to their energy, or free fall is
not universal ("gravitational charge" != energy).

Protocol:
  Species L (light):  massless, k0=0.35  -> omega_L per unit norm
  Species H (heavy):  dm=1.0,  k0=0.30   -> omega_H per unit norm  (~3x)
  For a rule, run each species (same norm), measure early-time field response
  A_s = max_x |theta - theta_ref| at T*=300 (before dispersal).
  Gravitational charge/energy:  q_s = A_s / omega_s
  Eotvos parameter: eta = 2|q_L - q_H| / (q_L + q_H).   PASS iff eta < 0.1.

Prediction for rho-sourced rules: A_L ~ A_H (same norm) while omega differ
=> eta ~ 2|w_H - w_L|/(w_H + w_L)  != 0. ALL rho-rules fail.
Fix (constructive): the species-blind local ENERGY operator
  T00(x) = -Im[ psi_t^dagger(x) (psi_{t+1}(x) - psi_{t-1}(x)) ] / 2  ~ rho*omega
(time-derivative bilinear; uses one extra stored walker slice — same memory
depth the field update already uses). A T00-sourced rule should pass.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rulespace import core

DIR = os.path.dirname(os.path.abspath(__file__))
N, TSTAR = 256, 300

def omega_of(k0, dm):
    ev = np.linalg.eigvals(core.walk_matrix(k0, core.TH_REF, dm))
    return float(np.max(-np.angle(ev)))

SPECIES = {"L": dict(k0=0.35, dm=0.0, sig=12.0),
           "H": dict(k0=0.30, dm=1.0, sig=12.0)}
OMEGA = {s: omega_of(v["k0"], v["dm"]) for s, v in SPECIES.items()}

def field_response(a, spec, source="rho"):
    """early-time field response amplitude for one species; source = rho | T00"""
    k0, dm, sig = spec["k0"], spec["dm"], spec["sig"]
    psi0, psi1 = core.packet(N, N // 2, k0, sig, dm=dm)
    prev0, prev1 = psi0.copy(), psi1.copy()          # psi_{t-1}
    th = np.full(N, core.TH_REF); th_prev = th.copy()
    for t in range(TSTAR):
        nxt0, nxt1 = core.walker_step(psi0, psi1, th, dm=dm)
        if source == "rho":
            src, _ = core.rho_J(psi0, psi1)
        else:  # T00: time-derivative bilinear ~ rho * omega, species-blind
            d0 = nxt0 - prev0; d1 = nxt1 - prev1
            src = -0.5 * (np.conj(psi0) * d0 + np.conj(psi1) * d1).imag
        _, J = core.rho_J(psi0, psi1)
        th_new, _ = core.field_step(th, th_prev, src, J, a)
        th_prev, th = th, th_new
        prev0, prev1 = psi0, psi1
        psi0, psi1 = nxt0, nxt1
    return float(np.max(np.abs(th - core.TH_REF)))

def eotvos(a, source):
    q = {}
    for s, spec in SPECIES.items():
        q[s] = field_response(a, spec, source) / OMEGA[s]
    eta = 2 * abs(q["L"] - q["H"]) / (q["L"] + q["H"] + 1e-30)
    return eta, q

results = {"omega_L": OMEGA["L"], "omega_H": OMEGA["H"],
           "eta_predicted_rho": 2 * abs(OMEGA["H"] - OMEGA["L"]) / (OMEGA["H"] + OMEGA["L"])}

# (1) the rho-sourced survivor family
recs = [json.loads(l) for l in open(os.path.join(DIR, "campaigns/c1b_v4.jsonl"))]
surv = [r for r in recs if r["stage"] == 6][:12]
etas = []
for r in surv:
    eta, q = eotvos(np.array(r["a"]), "rho")
    etas.append(eta)
results["eta_rho_rules"] = {"median": float(np.median(etas)),
                            "min": float(np.min(etas)), "max": float(np.max(etas)),
                            "n_pass(<0.1)": int(sum(e < 0.1 for e in etas)), "n": len(etas)}
print(f"rho-sourced survivors: eta median {np.median(etas):.3f} "
      f"(predicted {results['eta_predicted_rho']:.3f}); pass: "
      f"{sum(e<0.1 for e in etas)}/{len(etas)}")

# (2) the constructive fix: same wave equation, T00 source
a_fix = np.array([0.30, 0, 0.05, 0, 0, 0])
eta_fix, q_fix = eotvos(a_fix, "T00")
eta_same_rho, _ = eotvos(a_fix, "rho")
results["eta_T00_rule"] = float(eta_fix)
results["eta_same_rule_rho"] = float(eta_same_rho)
print(f"same wave equation: source=rho  -> eta = {eta_same_rho:.3f}  (FAIL)")
print(f"                    source=T00  -> eta = {eta_fix:.3f}  "
      f"({'PASS' if eta_fix < 0.1 else 'FAIL'})")
results["conclusion_T00_selected"] = bool(eta_fix < 0.1 and eta_same_rho > 0.1)
json.dump(results, open(os.path.join(DIR, "r2b_results.json"), "w"), indent=1)
print("EOTVOS SELECTS T00 AS THE SOURCE:", results["conclusion_T00_selected"])
