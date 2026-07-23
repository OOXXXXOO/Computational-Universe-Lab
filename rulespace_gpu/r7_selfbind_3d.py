"""R7 — self-binding in 3+1D: the dilution-law prediction, on GPU.

The geometric dilution law (r4a) predicts self-gravity can bind matter only
for d >= 3 (1D grows / 2D marginal / 3D localizes, finite self-energy).
This runs the LONG 3+1D coupled dynamics that was infeasible on CPU and tests
whether a matter blob virialises (bound) instead of dispersing (free).

Observable: RMS width w(t) of the matter, self-gravitating vs free.
  free            -> w grows (quantum dispersal)
  self-gravitating -> w stabilises / oscillates (a bound "star")

Run small here to tune; run LARGE on your GPU:
  RULESPACE_BACKEND=mlx python -m rulespace_gpu.r7_selfbind_3d --L 128 --T 4000 --save
"""
import argparse, time, json, os
import numpy as np
from . import backend as B, engine, states, observables
xp = B.xp


def rms_width(rho_arr, shape):
    """circular RMS radius of the matter distribution on the torus."""
    tot = B.fscalar(xp.sum(rho_arr))
    w2 = 0.0
    for ax in range(len(shape)):
        n = shape[ax]
        idx = B.asarray(np.arange(n))
        dims = [1] * len(shape); dims[ax] = n
        idr = xp.reshape(idx, dims)
        z = xp.sum(rho_arr * xp.exp(2j * np.pi * idr / n)) / tot
        R = B.fscalar(xp.abs(z))
        w2 += (n / (2 * np.pi)) ** 2 * max(-2 * np.log(max(R, 1e-9)), 0.0)
    return np.sqrt(w2 / len(shape))


def run(L=48, T=600, kappa=0.02, dm=0.6, k0=0.05, sig=5.0, cg2=0.25,
        measure_every=10, save=False, tag="mlx"):
    shape = (L,) * 3
    ctr = (L // 2,) * 3
    def make_state():
        p0, p1 = states.packet(shape, ctr, (k0, 0.0, 0.0), sig, 0.45, dm)
        th = states.uniform_theta(shape, 0.45)
        return (p0, p1, p0, p1, th, th)

    out = {}
    for mode, kap in (("free", 0.0), ("selfgrav", kappa)):
        params = dict(ndim=3, dm=dm, source="capstone", cg2=cg2, kappa=kap,
                      th_min=0.08, th_max=1.25)
        step = engine.make_stepper(params)
        state = make_state()
        ws, ts = [], []
        wells = []
        t0 = time.perf_counter()
        for t in range(T):
            if t % measure_every == 0:
                rho = engine.rho(state[0], state[1])
                ws.append(rms_width(rho, shape)); ts.append(t)
                wells.append(B.fscalar(xp.max(state[4])) - 0.45)
            state = step(state)
        B.sync(*state)
        dt = time.perf_counter() - t0
        out[mode] = {"t": ts, "width": ws, "well_depth": wells,
                     "sec_per_step": dt / T}
        print(f"  {mode:9s}: w {ws[0]:.1f} -> {ws[-1]:.1f}  "
              f"(x{ws[-1]/ws[0]:.2f})  well {wells[-1]:+.3f}  {1e3*dt/T:.2f} ms/step")
        if save and mode == "selfgrav":
            _save_field3d(state, shape, L, tag)

    wf, ws = out["free"]["width"][-1], out["selfgrav"]["width"][-1]
    out["binding_ratio"] = ws / wf
    out["bound"] = bool(ws < 0.75 * wf)
    print(f"\n  binding ratio w_selfgrav/w_free = {out['binding_ratio']:.2f}  "
          f"=> {'BOUND (self-gravity holds it)' if out['bound'] else 'not bound at these params'}")
    return out


def _save_field3d(state, shape, L, tag):
    """export matter cloud + geometry slices for 3d_gravity_well.html."""
    rho = B.to_np(engine.rho(state[0], state[1]))
    cloc = np.cos(B.to_np(state[4]))
    c = L // 2
    rho_n = rho / rho.max()
    pts = [[int(i), int(j), int(k), round(float(rho_n[i, j, k]), 3)]
           for i in range(L) for j in range(L) for k in range(L) if rho_n[i, j, k] > 0.06]
    data = {"G": L, "theta_ref": 0.45, "matter": pts,
            "slice_z": [[round(float(cloc[i, j, c]), 4) for j in range(L)] for i in range(L)],
            "slice_y": [[round(float(cloc[i, c, k]), 4) for k in range(L)] for i in range(L)],
            "slice_x": [[round(float(cloc[c, j, k]), 4) for k in range(L)] for j in range(L)],
            "c_min": float(cloc.min()), "c_max": float(cloc.max())}
    path = os.path.join(os.path.dirname(__file__), "..", "data", "results", f"r7_star_{tag}.json")
    json.dump(data, open(path, "w"))
    print(f"  saved 3D field ({len(pts)} matter pts) -> r7_star_{tag}.json "
          f"(load in 3d_gravity_well.html)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=48)
    ap.add_argument("--T", type=int, default=600)
    ap.add_argument("--kappa", type=float, default=0.02)
    ap.add_argument("--dm", type=float, default=0.6)
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    print(f"backend = {B.NAME}   device = {B.device_info()}   grid = {a.L}^3 x {a.T} steps\n")
    res = run(L=a.L, T=a.T, kappa=a.kappa, dm=a.dm, save=a.save, tag=B.NAME)
    json.dump({k: v for k, v in res.items() if k in ("binding_ratio", "bound")},
              open(os.path.join(os.path.dirname(__file__), "..", "data", "results", "r7_results.json"), "w"), indent=1)
