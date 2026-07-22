"""rulespace_gpu.verify — correctness tests reproducing the CPU-era results.

Run:  RULESPACE_BACKEND=mlx python -m rulespace_gpu.verify
Confirms the GPU engine matches the validated physics before you scale up.
"""
import numpy as np
from . import backend as B, engine, states, observables
xp = B.xp


def test_T00_conservation(ndim=3, L=32, T=60, dm=0.3):
    shape = (L,) * ndim
    th = states.uniform_theta(shape, 0.45)
    p0, p1 = states.packet(shape, (L // 2,) * ndim, (0.6,) + (0.0,) * (ndim - 1), 4.0, 0.45, dm)
    pp0, pp1 = p0, p1
    tots = []
    for t in range(T):
        n0, n1 = engine.walk_step(p0, p1, th, dm, ndim)
        if t > 1:
            tots.append(observables.total(engine.T00((pp0, pp1), (p0, p1), (n0, n1))))
        pp0, pp1 = p0, p1; p0, p1 = n0, n1
    drift = max(abs(t - tots[0]) for t in tots) / abs(tots[0])   # relative drift
    # fp64 backends conserve to ~1e-13 (README: 4.5e-14); MLX is fp32-native, where
    # the deterministic rounding floor of the 32^3 sums over 60 steps is ~1e-5.
    tol = 1e-9 if B.FIN == getattr(B.xp, "float64", None) else 5e-5
    return drift, drift < tol

def test_metric(L=600, T=180):
    """the emergent metric: a packet's local speed must equal c = cos(theta)
    on each plateau (the C1a instrument test — clean, convention-free)."""
    errs = []
    for th0 in (0.2, 0.6, 1.0):
        shape = (L,)
        th = states.uniform_theta(shape, th0)
        p0, p1 = states.packet(shape, (L // 4,), (0.8,), 12.0, th0, 0.0)
        c0 = observables.com(engine.rho(p0, p1), 0, shape)
        for _ in range(T):
            p0, p1 = engine.walk_step(p0, p1, th, 0.0, 1)
        c1 = observables.com(engine.rho(p0, p1), 0, shape)
        v = abs((c1 - c0 + L / 2) % L - L / 2) / T
        # exact group velocity of this walk's branch at k0=0.8
        _, w = states.branch_spinor(np.array([0.8]), th0, 0.0, 1)
        kk = np.array([0.8]); dk = 1e-4
        vg = (states.omega(kk + dk, th0, 0, 1) - states.omega(kk - dk, th0, 0, 1)) / (2 * dk)
        errs.append(abs(v - abs(vg)))
    return max(errs), max(errs) < 0.03

def test_light_cone(L=200, T=40):
    shape = (L,)
    th = states.uniform_theta(shape, 0.30)          # c = cos(0.3) ~ 0.955
    p0, p1 = states.packet(shape, (L // 2,), (0.7,), 8.0, 0.30, 0.0)
    c0 = observables.com(engine.rho(p0, p1), 0, shape)
    for _ in range(T):
        p0, p1 = engine.walk_step(p0, p1, th, 0.0, 1)
    c1 = observables.com(engine.rho(p0, p1), 0, shape)
    disp = (c1 - c0 + L / 2) % L - L / 2
    v = abs(disp) / T
    return v, v <= 1.0 + 1e-6


if __name__ == "__main__":
    print(f"backend = {B.NAME}   device = {B.device_info()}\n")
    d, ok1 = test_T00_conservation()
    print(f"[{'PASS' if ok1 else 'FAIL'}] 3+1D T00 conservation: drift = {d:.2e}")
    e, ok2 = test_metric()
    print(f"[{'PASS' if ok2 else 'FAIL'}] emergent metric (speed = cos theta): max err = {e:.4f}")
    v, ok3 = test_light_cone()
    print(f"[{'PASS' if ok3 else 'FAIL'}] causal light cone: packet speed = {v:.3f} <= 1")
    print("\nALL PASS" if (ok1 and ok2 and ok3) else "\nSOME FAILED")
