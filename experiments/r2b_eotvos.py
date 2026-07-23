"""Round 2, Exp 2.2 — the Eotvos test: a second SPECIES enters the courtroom.

The v4 survivors passed universality across massless states (momentum, width,
amplitude). Now add a MASSIVE walker (dm=0.5). Its energy-per-probability
ratio differs from the massless species, so a field sourced by PROBABILITY
density rho cannot respond universally to both species unless energy and
probability happen to be proportional.

Prediction: most survivors fail; the fitted source coupling b2 for the
massive state should differ from the massless one by roughly the
energy-per-probability ratio — demonstrating that the equivalence principle
demands the source be T00 (energy), not rho. This is how the stress-energy
tensor gets SELECTED, not assumed.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rulespace import core
from rulespace.judges import _fit_reduced

DIR = os.path.dirname(os.path.abspath(__file__))
recs = [json.loads(l) for l in open(os.path.join(DIR, "campaigns/c1b_v4.jsonl"))]
surv = [r for r in recs if r["stage"] == 6]
print("v4 survivors:", len(surv))

STATES = [dict(k0=0.8, sig=10.0),                       # massless A
          dict(k0=1.4, sig=22.0, x0=85),                # massless B
          dict(k0=0.8, sig=10.0, amp=0.55),             # massless, lower energy
          dict(k0=0.5, sig=14.0, dm=0.5)]               # MASSIVE species

out_rows = []
n_pass = 0
for r in surv:
    a = np.array(r["a"])
    bs, r2s, okrun = [], [], True
    for skw in STATES:
        out = core.run_coupled(a, N=256, T=600, **skw)
        if out is None:
            okrun = False; break
        b, r2 = _fit_reduced(out)
        bs.append(b); r2s.append(r2)
    if not okrun:
        continue
    bs = np.array(bs)
    scale = np.abs(bs).mean(axis=0) + 1e-12
    d = float(np.max(np.abs(bs - bs.mean(axis=0)) / scale))
    passed = (d < 0.10) and (min(r2s) > 0.90)
    n_pass += passed
    # ratio of fitted source coupling: massive vs massless-A
    ratio = float(bs[3, 1] / bs[0, 1]) if abs(bs[0, 1]) > 1e-15 else np.nan
    out_rows.append({"a": r["a"], "univ4": d, "pass": bool(passed),
                     "b2_ratio_massive_over_massless": ratio,
                     "r2_min": float(min(r2s))})

ratios = np.array([o["b2_ratio_massive_over_massless"] for o in out_rows
                   if np.isfinite(o["b2_ratio_massive_over_massless"])])
# energy-per-probability of the two species (homogeneous background, exact)
def energy_per_prob(k0, dm):
    ev = np.linalg.eigvals(core.walk_matrix(k0, core.TH_REF, dm))
    w = -np.angle(ev)
    return float(np.max(w))
E_ml = energy_per_prob(0.8, 0.0)
E_mv = energy_per_prob(0.5, 0.5)
res = {"n_survivors_v4": len(surv), "n_pass_eotvos": int(n_pass),
       "kill_fraction": float(1 - n_pass / max(len(surv), 1)),
       "b2_ratio_median": float(np.median(ratios)) if len(ratios) else None,
       "b2_ratio_iqr": [float(np.percentile(ratios, 25)), float(np.percentile(ratios, 75))] if len(ratios) else None,
       "energy_per_prob_massless": E_ml, "energy_per_prob_massive": E_mv,
       "energy_ratio_prediction": E_mv / E_ml,
       "rows": out_rows}
json.dump(res, open(os.path.join(DIR, "r2b_results.json"), "w"), indent=1)
print(f"Eotvos verdict: {n_pass}/{len(surv)} survive the second species "
      f"(kill fraction {100*res['kill_fraction']:.0f}%)")
if len(ratios):
    print(f"fitted b2(massive)/b2(massless): median {np.median(ratios):.3f}  "
          f"IQR [{np.percentile(ratios,25):.3f}, {np.percentile(ratios,75):.3f}]")
print(f"species omega: massless {E_ml:.3f}, massive {E_mv:.3f}, ratio {E_mv/E_ml:.3f}")
