"""rulespace.discover — sparse regression layer (STLSQ, SINDy-style).

Given a trajectory, find the sparsest equation
    theta_tt = sum_i  c_i * O_i(theta, matter)
that explains it. In sweep v1 this acts as a control loop (should re-identify
the injected couplings); its real role begins when the field dynamics is
selected by consistency conditions rather than injected by hand.
"""
import numpy as np
from . import core

def build_library(out, subsample=3):
    th, rho, J = out["theta"], out["rho"], out["J"]
    Xs, ys = [], []
    eps = 1e-9
    for t in range(1, len(th) - 1, subsample):
        ok = (th[t + 1] > core.TH_MIN + eps) & (th[t + 1] < core.TH_MAX - eps)
        if not ok.any(): continue
        terms = core.field_terms(th[t], th[t - 1], rho[t], J[t])
        Xs.append(terms.reshape(core.NPAR, -1).T[ok])
        ys.append((th[t + 1] - 2 * th[t] + th[t - 1])[ok])
    return np.vstack(Xs), np.concatenate(ys)

def stlsq(X, y, thresh_frac=0.05, iters=8):
    """sequential thresholded lstsq with CONTRIBUTION-scale thresholding:
    threshold |c_i| * rms(X_i), not raw |c_i| (columns have wildly different units)."""
    scale = np.sqrt((X ** 2).mean(axis=0)) + 1e-30
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    for _ in range(iters):
        contrib = np.abs(c) * scale
        thr = thresh_frac * contrib.max()
        small = contrib < thr
        c[small] = 0.0
        act = ~small
        if act.sum() == 0: break
        c[act], *_ = np.linalg.lstsq(X[:, act], y, rcond=None)
    pred = X @ c
    r2 = 1 - ((y - pred) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-30)
    return c, float(r2)

def discover(a, **runkw):
    out = core.run_coupled(a, **runkw)
    if out is None: return None
    X, y = build_library(out)
    c, r2 = stlsq(X, y)
    eq = " + ".join(f"{ci:+.4g}*{name}" for ci, name in zip(c, core.PAR_NAMES) if ci != 0)
    return {"coeffs": c.tolist(), "r2": r2, "equation": "theta_tt = " + (eq or "0"),
            "injected": list(a), "recovery_err": float(np.linalg.norm(c - a) / (np.linalg.norm(a) + 1e-12))}
