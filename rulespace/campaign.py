"""rulespace.campaign — sweep runner with the judge funnel, JSONL storage."""
import numpy as np, json, os, time
from . import core, judges

def sample_coupling(rng):
    """sparse physics-shaped prior over coupling vectors"""
    a = np.zeros(core.NPAR)
    # geometric stiffness: usually on, positive, <=1 for causality hope
    if rng.random() < 0.9:
        a[0] = 10 ** rng.uniform(-2.5, -0.1)
    if rng.random() < 0.4:
        a[1] = np.sign(rng.random() - 0.5) * 10 ** rng.uniform(-3.5, -0.8)
    # matter couplings
    if rng.random() < 0.85:
        a[2] = np.sign(rng.random() - 0.3) * 10 ** rng.uniform(-3, -0.5)
    if rng.random() < 0.35:
        a[3] = np.sign(rng.random() - 0.5) * 10 ** rng.uniform(-3.5, -1)
    # restoring (negative = stable well) and damping (negative)
    if rng.random() < 0.7:
        a[4] = -(10 ** rng.uniform(-4, -1.3))
    if rng.random() < 0.6:
        a[5] = -(10 ** rng.uniform(-3, -1))
    return a

def evaluate(a, quick=False):
    rec = {"a": a.tolist()}
    out = core.run_coupled(a)
    ok1, m1 = judges.j1_stability(out); rec.update(m1); rec["J1"] = ok1
    if not ok1: rec["stage"] = 1; return rec
    ok5, m5 = judges.j5_sign(out); rec.update(m5); rec["J5"] = ok5
    ok3, m3 = judges.j3_response(a, out); rec.update(m3); rec["J3"] = ok3
    if not ok3: rec["stage"] = 3; return rec
    ok2, m2 = judges.j2_causality(a); rec.update(m2); rec["J2"] = ok2
    if not ok2: rec["stage"] = 2; return rec
    ok4, m4 = judges.j4_universality(a); rec.update(m4); rec["J4"] = ok4
    rec["stage"] = 6 if ok4 else 4
    return rec

def sweep(n, seed, path, budget_s=38.0):
    rng = np.random.default_rng(seed)
    t0 = time.time()
    done = 0
    with open(path, "a") as f:
        for i in range(n):
            if time.time() - t0 > budget_s:
                break
            a = sample_coupling(rng)
            rec = evaluate(a)
            rec["seed"] = int(seed); rec["idx"] = int(i)
            f.write(json.dumps(rec, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
            done += 1
    return done
