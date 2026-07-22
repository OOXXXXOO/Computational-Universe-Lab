"""R8 — R7 root-cause fix: the CONFORMAL 3D walker (attraction-sign-correct).

Autopsy result (see 追溯-R7根因.md): R7's heavy species was REPELLED by the
theta-up wells its own capstone source dug — a source/response sign mismatch:
  * engine.walk_step applies coin(+theta) after EVERY axis (no cancellation)
    -> a trivial additive theta-potential enters the rest phase; for heavy
    species the branch makes theta-up regions repulsive.
  * the capstone source tan(theta)*T00 was derived for the 1D CONFORMAL family
    where rest energy ~ cos(theta) (theta-up = genuine well).

Fix: the conformal 3D walk. Kinetic coins alternate +theta/-theta across axes
(additive part cancels at k=0); mass coin = dm*cos(theta)/cos(theta_ref)
(rest energy redshifts like the local light speed -> theta-up attracts ALL
matter, coupling O(1), matching the capstone source: action=reaction).

Modes:
  --autopsy   drift test near a frozen bump: undressed vs conformal (sign check)
  --scan      self-binding scan with the conformal walker (the R7 rematch)

GPU:  RULESPACE_BACKEND=mlx python -m rulespace_gpu.r8_conformal_selfbind --scan --L 96 --T 3000
"""
import argparse, json, os, math
import numpy as np
from . import backend as B, engine, states
xp = B.xp

TH_REF = 0.45
COS_REF = math.cos(TH_REF)
INV2 = 1.0 / math.sqrt(2.0)


def walk_step_conformal(p0, p1, th, dm, ndim=3):
    """kinetic coins alternate sign across axes (rest-phase cancellation);
    conformal mass coin dm*cos(th)/cos(th_ref)."""
    p0, p1 = engine._axis_x(p0, p1); p0, p1 = engine.coin(p0, p1, th)
    if ndim >= 2:
        p0, p1 = engine._axis_y(p0, p1); p0, p1 = engine.coin(p0, p1, -th)
    if ndim >= 3:
        p0, p1 = engine._axis_z(p0, p1); p0, p1 = engine.coin(p0, p1, th)
    total_kin = th if ndim == 1 else (0.0 * th if ndim == 2 else th)
    # cancel the residual kinetic rest-phase, then conformal mass rotation
    p0, p1 = engine.coin(p0, p1, -total_kin + dm * xp.cos(th) / COS_REF)
    return p0, p1


def _conformal_mode_U(kvec, th, dm):
    """2x2 mode operator of walk_step_conformal on a tiny grid (host)."""
    L = 6; ax = np.arange(L)
    g = np.meshgrid(ax, ax, ax, indexing="ij")
    ph = np.exp(1j * sum(kvec[i] * g[i] for i in range(3)))
    thf = B.asarray(np.full((L, L, L), th))
    U = np.zeros((2, 2), complex)
    for j, (b0, b1) in enumerate([(ph, 0 * ph), (0 * ph, ph)]):
        o0, o1 = walk_step_conformal(B.asarray(b0.astype(complex)),
                                     B.asarray(b1.astype(complex)), thf, dm)
        o0 = B.to_np(o0); o1 = B.to_np(o1)
        U[0, j] = o0[1, 1, 1] / ph[1, 1, 1]; U[1, j] = o1[1, 1, 1] / ph[1, 1, 1]
    return U


def conformal_packet(shape, center, kvec, sig, dm):
    """packet on the POSITIVE-ENERGY branch of the CONFORMAL walk
    (states.packet uses the undressed mode operator -> wrong spinor here)."""
    U = _conformal_mode_U(list(kvec) + [0.0] * (3 - len(kvec)), TH_REF, dm)
    ev, V = np.linalg.eig(U)
    w = -np.angle(ev)
    b = int(np.argmax(w))                        # positive-energy branch (the WELL branch)
    sp = V[:, b]; sp = sp * np.exp(-1j * np.angle(sp[0] + 1e-30))
    grids = np.meshgrid(*[np.arange(n) for n in shape], indexing="ij")
    r2 = sum(((grids[i] - center[i] + shape[i] // 2) % shape[i] - shape[i] // 2) ** 2
             for i in range(3))
    phase = sum(kvec[i] * grids[i] for i in range(len(kvec)))
    g = np.exp(-r2 / (4 * sig ** 2)) * np.exp(1j * phase)
    p0 = sp[0] * g; p1 = sp[1] * g
    n = np.sqrt((np.abs(p0) ** 2 + np.abs(p1) ** 2).sum())
    return B.asarray(p0 / n), B.asarray(p1 / n)


def drift_test(dm, conformal, L=40, T=160, k0=0.05):
    """packet at center; frozen theta-bump 8 sites to +x; net x-drift vs flat."""
    shape = (L,) * 3; c = L // 2
    gr = np.meshgrid(*[np.arange(L)] * 3, indexing="ij")
    r2 = (gr[0] - (c + 8)) ** 2 + (gr[1] - c) ** 2 + (gr[2] - c) ** 2
    th_bump = B.asarray(0.45 + 0.30 * np.exp(-r2 / (2 * 4.0 ** 2)))
    th_flat = states.uniform_theta(shape, 0.45)
    x1d = np.arange(L)
    def one(th):
        if conformal:
            p0, p1 = conformal_packet(shape, (c, c, c), (k0, 0, 0), 5.0, dm)
        else:
            p0, p1 = states.packet(shape, (c, c, c), (k0, 0, 0), 5.0, TH_REF, dm)
        def xcom():
            r = B.to_np(engine.rho(p0, p1)); return (r * x1d[:, None, None]).sum() / r.sum()
        x0 = xcom()
        for _ in range(T):
            if conformal:
                p0, p1 = walk_step_conformal(p0, p1, th, dm)
            else:
                p0, p1 = engine.walk_step(p0, p1, th, dm, 3)
        return xcom() - x0
    return one(th_bump) - one(th_flat)


def selfbind_scan(L=64, T=1500, dm=2.0, sig=8.0, kappas=(0.0, 0.05, 0.2, 0.8)):
    """R7 rematch: coupled dynamics with the CONFORMAL walker + capstone source."""
    shape = (L,) * 3
    x1d = np.arange(L)
    def rms_width(rho):
        tot = B.fscalar(xp.sum(rho)); w2 = 0.0
        for ax in range(3):
            dims = [1, 1, 1]; dims[ax] = L
            idr = B.asarray(x1d.reshape(dims))
            z = xp.sum(rho * xp.exp(2j * np.pi * idr / L)) / tot
            R = B.fscalar(xp.abs(z))
            w2 += (L / (2 * np.pi)) ** 2 * max(-2 * np.log(max(R, 1e-9)), 0.0)
        return float(np.sqrt(w2 / 3))
    results = {}
    for kap in kappas:
        p0, p1 = conformal_packet(shape, (L // 2,) * 3, (0.02, 0, 0), sig, dm)
        pp0, pp1 = p0, p1
        th = states.uniform_theta(shape, TH_REF); thp = th
        ws = []
        for t in range(T):
            n0, n1 = walk_step_conformal(p0, p1, th, dm)
            if t % 100 == 0:
                ws.append(rms_width(engine.rho(p0, p1)))
            src = xp.tan(th) * engine.T00((pp0, pp1), (p0, p1), (n0, n1))
            th_new = engine.field_step(th, thp, src, 0.25, kap, 0.08, 1.25, 3)
            thp, th = th, th_new
            pp0, pp1 = p0, p1
            p0, p1 = n0, n1
        B.sync(th)
        well = B.fscalar(xp.max(th)) - TH_REF
        results[kap] = {"w": ws, "well": well}
        print(f"  kappa={kap:5.2f}: w {ws[0]:5.1f} -> {ws[-1]:5.1f}  (min {min(ws):5.1f})  well {well:+.3f}")
    wf = results[kappas[0]]["w"][-1]
    for kap in kappas[1:]:
        r = results[kap]["w"][-1] / wf
        print(f"  binding ratio kappa={kap}: {r:.2f}" + ("  <-- BOUND" if r < 0.75 else ""))
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--autopsy", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--L", type=int, default=64)
    ap.add_argument("--T", type=int, default=1500)
    ap.add_argument("--dm", type=float, default=2.0)
    a = ap.parse_args()
    print(f"backend = {B.NAME}   device = {B.device_info()}\n")
    if a.autopsy or not a.scan:
        print("SIGN AUTOPSY: net drift toward a frozen theta-up bump (+ = attracted)")
        for dm in (0.45, 2.0):
            du = drift_test(dm, conformal=False)
            dc = drift_test(dm, conformal=True)
            print(f"  dm={dm}: undressed(R7) {du:+.2f}   CONFORMAL {dc:+.2f}"
                  f"   -> {'FIXED: attraction restored' if dc > 0.3 > du or (dc > 0.3 and du < 0.3) else 'check'}")
    if a.scan:
        print("\nSELF-BINDING REMATCH (conformal walker, capstone source):")
        selfbind_scan(L=a.L, T=a.T, dm=a.dm)
