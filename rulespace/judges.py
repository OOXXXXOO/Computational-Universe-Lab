"""rulespace.judges — the law-likeness funnel.

J1 STABILITY   no NaN, clip saturation < 1%, field variance bounded
J2 CAUSALITY   a field perturbation spreads no faster than the walker cone
J3 RESPONSE    the field actually feels matter (twin run with no walker differs)
J4 UNIVERSALITY (equivalence-principle judge) the fitted matter->field response
               is the same for different walker states. THE law detector.
J5 SIGN        gravity-like orientation: energy concentration slows light
               (d theta / d rho > 0 => c = cos theta decreases where matter sits)
"""
import numpy as np
from . import core

def j1_stability(out):
    if out is None: return False, {"sat": 1.0}
    ok = (out["sat"] < 0.01) and (out["final_var"] < 0.25)
    return ok, {"sat": out["sat"], "final_var": out["final_var"]}

def j2_causality(a, N=192, T=150):
    base = core.run_coupled(a, N=N, T=T, kick=0.0, record_every=1)
    pert = core.run_coupled(a, N=N, T=T, kick=0.02, record_every=1)
    if base is None or pert is None: return False, {"v_front": np.inf}
    d = np.abs(pert["theta"] - base["theta"])
    thr = 1e-9
    x0 = N // 4
    def front(t):
        hit = np.where(d[t] > thr)[0]
        if not len(hit): return 0.0
        return float(np.max(np.minimum((hit - x0) % N, (x0 - hit) % N)))
    t1, t2 = 20, T - 1
    v = (front(t2) - front(t1)) / (t2 - t1)   # asymptotic front speed
    return v <= 1.05, {"v_front": float(v)}

def j3_response(a, out, N=256, T=600):
    """compare field trajectory against a matter-free twin"""
    th0 = core.np.full(N, core.TH_REF)
    th, th_prev = th0.copy(), th0.copy()
    zero = np.zeros(N)
    for t in range(T // 2):
        th_new, _ = core.field_step(th, th_prev, zero, zero, a)
        th_prev, th = th, th_new
    diff = float(np.abs(out["theta"][min(T // 4, len(out["theta"]) - 1)] - th).max())
    return diff > 1e-4, {"matter_effect": diff}

def _fit_response(out):
    """least-squares fit of theta_tt = b . terms  on the recorded trajectory"""
    th, rho, J = out["theta"], out["rho"], out["J"]
    T = len(th)
    rows_X, rows_y = [], []
    eps = 1e-9
    for t in range(1, T - 1):
        ok = (th[t + 1] > core.TH_MIN + eps) & (th[t + 1] < core.TH_MAX - eps)
        if not ok.any(): continue
        terms = core.field_terms(th[t], th[t - 1], rho[t], J[t])
        rows_X.append(terms.reshape(core.NPAR, -1).T[ok])
        rows_y.append((th[t + 1] - 2 * th[t] + th[t - 1])[ok])
    X = np.vstack(rows_X); y = np.concatenate(rows_y)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ b
    ss = 1 - ((y - pred) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-30)
    return b, float(ss)

VAR_MIN = 1e-13   # min per-sample var(theta_tt) for a REAL-dynamics reduced fit

def _fit_reduced(out):
    """the OBSERVER's model: theta_tt = b1*Lap(theta) + b2*(rho-mean).
    The observer does not know the microscopic rule; truncated terms leak
    into state-dependence of (b1,b2) — that is what universality tests.

    Degenerate-case guard: a numerically frozen theta_tt (var(y) ~ 0) would
    give SS_tot ~ 0 -> R^2 = 1 with b = 0, i.e. a J4 auto-pass for rules with
    no real field dynamics. Require var(y) > VAR_MIN (same constant as
    rulespace_gpu.campaign.VAR_MIN, keeping CPU and GPU verdicts aligned)."""
    th, rho = out["theta"], out["rho"]
    eps = 1e-9
    Xs, ys = [], []
    for t in range(1, len(th) - 1):
        ok = (th[t + 1] > core.TH_MIN + eps) & (th[t + 1] < core.TH_MAX - eps)
        if not ok.any(): continue
        X = np.stack([core.lap(th[t]), rho[t] - rho[t].mean()])
        Xs.append(X.reshape(2, -1).T[ok])
        ys.append((th[t + 1] - 2 * th[t] + th[t - 1])[ok])
    X = np.vstack(Xs); y = np.concatenate(ys)
    ss_tot = ((y - y.mean()) ** 2).sum()
    if ss_tot <= VAR_MIN * len(y):                # frozen field: no real dynamics
        return np.zeros(2), -1.0
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - ((y - X @ b) ** 2).sum() / max(ss_tot, 1e-30)
    return b, float(r2)

def j4_universality(a, N=256, T=600):
    """equivalence principle: the observer's REDUCED law (wave + universal
    source) must have state-independent coefficients across matter states
    differing in momentum, width and energy scale."""
    states = [dict(k0=0.8, sig=10.0), dict(k0=1.4, sig=22.0, x0=N // 3),
              dict(k0=0.8, sig=10.0, amp=0.55)]
    bs, r2s = [], []
    for skw in states:
        out = core.run_coupled(a, N=N, T=T, **skw)
        if out is None: return False, {"univ_dist": np.inf}
        b, r2 = _fit_reduced(out)
        bs.append(b); r2s.append(r2)
    bs = np.array(bs)
    scale = np.abs(bs).mean(axis=0) + 1e-12
    d = float(np.max(np.abs(bs - bs.mean(axis=0)) / scale))
    lawful = min(r2s) > 0.90                      # reduced law must actually FIT
    return (d < 0.10) and lawful, {"univ_dist": d, "r2_reduced_min": float(min(r2s)),
                                   "b_states": bs.tolist()}

def j5_sign(out):
    """corr(rho, theta-change): positive = matter slows light (gravity-like)"""
    th, rho = out["theta"], out["rho"]
    dth = th[-1] - th[0]
    rr = rho.mean(axis=0)
    c = np.corrcoef(rr - rr.mean(), dth - dth.mean())[0, 1]
    return bool(c > 0.1), {"grav_corr": float(c)}
