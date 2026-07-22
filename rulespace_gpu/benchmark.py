"""rulespace_gpu.benchmark — throughput of the coupled 3+1D dynamics.

Run:  RULESPACE_BACKEND=mlx python -m rulespace_gpu.benchmark
Reports cell-updates/second so you can size runs for your GPU.
"""
import time, numpy as np
from . import backend as B, engine, states
xp = B.xp


def bench(L, ndim=3, steps=40, dm=0.3):
    shape = (L,) * ndim
    th = states.uniform_theta(shape, 0.45)
    p0, p1 = states.packet(shape, (L // 2,) * ndim, (0.6,) + (0.0,) * (ndim - 1), 4.0, 0.45, dm)
    state = (p0, p1, p0, p1, th, th)
    params = dict(ndim=ndim, dm=dm, source="capstone", cg2=0.2, kappa=0.02,
                  th_min=0.08, th_max=1.25)
    step = engine.make_stepper(params)
    state = step(state); B.sync(*state)                # warm-up / compile
    t0 = time.perf_counter()
    for _ in range(steps):
        state = step(state)
    B.sync(*state)
    dt = time.perf_counter() - t0
    cells = L ** ndim
    return dt / steps, cells * steps / dt


if __name__ == "__main__":
    print(f"backend = {B.NAME}   device = {B.device_info()}\n")
    print(f"{'grid':>16} {'sec/step':>12} {'cell-updates/s':>16}")
    dims = {1: [4096, 65536], 2: [128, 256, 512], 3: [32, 48, 64, 96]}
    for ndim in (1, 2, 3):
        for L in dims[ndim]:
            try:
                sps, cups = bench(L, ndim)
                g = f"{L}" + ("" if ndim == 1 else f"^{ndim}")
                print(f"{g:>16} {sps*1e3:>10.2f}ms {cups:>16.2e}")
            except Exception as e:
                print(f"  {L}^{ndim}: {type(e).__name__} {e}")
