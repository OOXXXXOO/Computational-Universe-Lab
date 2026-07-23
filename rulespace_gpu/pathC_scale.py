"""Path C — GPU-scale rule-space search: the survival manifold at 10^5 rules.

The CPU campaign (rulespace/campaign.py) screened ~800 rules in ~40s. On GPU
the batched sweep (campaign.sweep) evaluates thousands of rules in parallel;
this driver runs 10^4-10^5 rules in batches and characterises the survival
manifold with real statistics: which operator-space directions survive the
stability judge, and the shape of the surviving region.

Run large on your GPU:
  RULESPACE_BACKEND=mlx python -m rulespace_gpu.pathC_scale --n 100000
"""
import argparse, time, json, os
import numpy as np
from . import backend as B
from .campaign import sweep, random_couplings, PAR_NAMES


def run(n_total, batch=4096, N=256, T=400, seed0=0, full=False, jit=True):
    """Default (full=False): fast J1-only survival scan, unchanged behavior.
    full=True: also tally J3/J4/lawful survivors from the fuller funnel and
    collect the lawful couplings (for the equivalence-principle manifold report).

    Returns (surv, all_stable) when full=False (backward-compatible), else
    (surv, all_stable, funnel, lawful) where `lawful` is the (M,6) array of
    couplings that passed J1&J3&J4. `jit` compiles the batched time loop (B.jit;
    no-op on numpy)."""
    surv_a, all_stable = [], 0
    lawf_a = [] if full else None
    funnel = {"J3": 0, "J4": 0, "lawful": 0} if full else None
    n_done = 0
    while n_done < n_total:
        bs = min(batch, n_total - n_done)
        cpl = random_couplings(bs, seed=seed0 + n_done)
        res = sweep(cpl, N=N, T=T, full=full, jit=jit)
        mask = res["stable"]
        all_stable += int(mask.sum())
        surv_a.append(cpl[mask])
        if full:
            funnel["J3"] += int((mask & res["J3"]).sum())
            funnel["J4"] += int((mask & res["J3"] & res["J4"]).sum())
            funnel["lawful"] += int(res["lawful"].sum())
            lawf_a.append(cpl[res["lawful"]])
        n_done += bs
    surv = np.concatenate(surv_a) if surv_a else np.zeros((0, 6))
    if not full:
        return surv, all_stable
    lawful = np.concatenate(lawf_a) if lawf_a else np.zeros((0, 6))
    return surv, all_stable, funnel, lawful


def manifold_report(surv, n_total):
    rep = {"n_total": n_total, "n_survivors": len(surv),
           "survival_rate": len(surv) / n_total}
    terms = {}
    for i, nm in enumerate(PAR_NAMES):
        col = surv[:, i]
        active = np.abs(col) > 0
        terms[nm] = {"active_pct": float(100 * active.mean()) if len(surv) else 0.0,
                     "median_abs": float(np.median(np.abs(col[active]))) if active.any() else 0.0,
                     "frac_positive": float((col[active] > 0).mean()) if active.any() else 0.0}
    rep["terms"] = terms
    return rep


def _print_manifold(rep):
    print(f"{'operator':>12}  {'active%':>8}  {'median|a|':>10}  {'positive%':>10}")
    for nm, s in rep["terms"].items():
        print(f"{nm:>12}  {s['active_pct']:>7.1f}%  {s['median_abs']:>10.4f}  {100*s['frac_positive']:>9.0f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--batch", type=int, default=4096)
    ap.add_argument("--T", type=int, default=400)
    ap.add_argument("--full", action="store_true",
                    help="also run the J3/J4 funnel and report lawful survivors")
    ap.add_argument("--no-jit", dest="jit", action="store_false",
                    help="disable the compiled time loop (reference path)")
    a = ap.parse_args()
    print(f"backend = {B.NAME}   device = {B.device_info()}   jit={a.jit}   screening {a.n} rules\n")
    t0 = time.perf_counter()
    _res = run(a.n, batch=a.batch, T=a.T, full=a.full, jit=a.jit)
    if a.full:
        surv, nstable, funnel, lawful = _res
    else:
        surv, nstable = _res; funnel = None; lawful = None
    dt = time.perf_counter() - t0
    rep = manifold_report(surv, a.n)
    print(f"screened {a.n} rules in {dt:.1f}s  ({a.n/dt:.0f} rules/s)")
    print(f"stable survivors: {rep['n_survivors']}/{a.n} ({100*rep['survival_rate']:.1f}%)")
    if funnel is not None:
        print(f"J1&J3 survivors : {funnel['J3']}/{a.n}   "
              f"lawful (J1&J3&J4): {funnel['lawful']}/{a.n}")
        rep["funnel"] = funnel
    print("\n-- STABLE (J1) manifold --")
    _print_manifold(rep)
    rep["seconds"] = dt

    if a.full:
        # equivalence-principle-passing subset: how lawful rules differ from stable ones
        lawrep = manifold_report(lawful, a.n)
        lawrep["seconds"] = dt
        lawrep["funnel"] = funnel
        lawrep["breakdown"] = {
            "n_total": a.n,
            "J1_stable": rep["n_survivors"],
            "J1_and_J3": funnel["J3"],
            "lawful_J1_J3_J4": funnel["lawful"],
            "J1_stable_pct": 100 * rep["survival_rate"],
            "J1_and_J3_pct": 100 * funnel["J3"] / a.n,
            "lawful_pct": 100 * funnel["lawful"] / a.n,
        }
        print(f"\n-- LAWFUL (J1&J3&J4) manifold  [{len(lawful)} rules] --")
        _print_manifold(lawrep)
        out = os.path.join(os.path.dirname(__file__), "..", "data", "results", "pathC_lawful_results.json")
        json.dump({"stable_manifold": rep, "lawful_manifold": lawrep,
                   "breakdown": lawrep["breakdown"]},
                  open(out, "w"), indent=1)
        print(f"\nwrote {out}")
    else:
        json.dump(rep, open(os.path.join(os.path.dirname(__file__), "..", "data", "results", "pathC_results.json"), "w"), indent=1)
