"""Path A — non-relativistic self-gravity: the Schrodinger-Newton soliton.

R7 showed a RELATIVISTIC Dirac packet disperses faster than gravity can bind
it. The fix (and the honest dynamical version of the dilution-law prediction):
NON-RELATIVISTIC (cold) matter. The 3D Schrodinger-Newton system

    i dpsi/dt = -(1/2m) Lap psi + V psi,     Lap V = g |psi|^2   (g>0 attractive)

is known to have stable self-gravitating solitons in 3D (and to collapse above
a critical mass). This is the cleanest test that self-gravity BINDS matter in
3+1D dynamically -- the positive result the relativistic walk couldn't give.

Split-step (Strang): kinetic in Fourier, potential in real space, Poisson via
FFT. All FFT/elementwise -> GPU-native.

Verdict per coupling g:
    width w(t) grows       -> unbound (kinetic wins)
    w(t) oscillates/steady -> SOLITON (self-gravity binds it)  [d>=3 only]
    w(t) collapses to grid -> supercritical collapse

The soliton width OSCILLATES, so the endpoint w[-1] is not a robust measure;
verdicts and summaries use steady_width() = median of the second half of w(t).

Mass-radius / dilution hook: mass is fixed here by wavefunction normalization,
so the accessible relation is soliton RADIUS (steady_width) vs coupling g. The
--scan BOUND table (g -> steady_width) is that radius-vs-g curve; across ndim it
probes the dilution law r^-(d-2) (expect d=3 binds, d=1 does not).

Run large on your GPU:
  RULESPACE_BACKEND=mlx python -m rulespace_gpu.pathA_sn_soliton --L 128 --T 4000
  RULESPACE_BACKEND=mlx python -m rulespace_gpu.pathA_sn_soliton --scan --glist "1,2,5,10,20"
"""
import argparse, time, json, os
import numpy as np
from . import backend as B
xp = B.xp


def _kgrids(L, ndim):
    k1 = 2 * np.pi * np.fft.fftfreq(L)
    ks = np.meshgrid(*([k1] * ndim), indexing="ij")
    k2 = sum(k ** 2 for k in ks)
    return B.asarray(k2)


def rms_width(rho, L, ndim):
    tot = B.fscalar(xp.sum(rho))
    w2 = 0.0
    for ax in range(ndim):
        idx = np.arange(L); dims = [1] * ndim; dims[ax] = L
        idr = B.asarray(idx.reshape(dims))
        z = xp.sum(rho * xp.exp(2j * np.pi * idr / L)) / tot
        R = B.fscalar(xp.abs(z))
        w2 += (L / (2 * np.pi)) ** 2 * max(-2 * np.log(max(R, 1e-9)), 0.0)
    return float(np.sqrt(w2 / ndim))


def run(L=64, ndim=3, T=1500, g=None, m=1.0, sig=6.0, dt=0.1, measure=25):
    k2 = _kgrids(L, ndim)
    kin = xp.exp(-1j * (k2 / (2 * m)) * dt)
    k2_np = B.to_np(k2); k2safe = np.where(k2_np > 1e-12, k2_np, 1.0)
    poisson = B.asarray(np.where(k2_np > 1e-12, -1.0 / k2safe, 0.0))  # V_k = -g rho_k / k^2

    gr = np.meshgrid(*[np.arange(L)] * ndim, indexing="ij")
    r2 = sum(((gr[i] - L // 2)) ** 2 for i in range(ndim))
    psi = B.asarray(np.exp(-r2 / (4 * sig ** 2)).astype(complex))
    psi = psi / xp.sqrt(xp.sum(xp.abs(psi) ** 2))

    def potential(ps):
        rho = xp.abs(ps) ** 2
        rho = rho - xp.mean(rho)                       # neutralising background
        return g * B.real(B.ifftn(poisson * B.fftn(rho)))

    ws, ts = [], []
    for t in range(T):
        if t % measure == 0:
            ws.append(rms_width(xp.abs(psi) ** 2, L, ndim)); ts.append(t)
        V = potential(psi)
        psi = xp.exp(-1j * V * dt / 2) * psi
        psi = B.ifftn(kin * B.fftn(psi))
        V = potential(psi)
        psi = xp.exp(-1j * V * dt / 2) * psi
    return np.array(ts), np.array(ws)


def steady_width(ws):
    """Robust steady width: median of the second half of the trajectory.

    The soliton width oscillates, so the endpoint ws[-1] is polluted by the
    oscillation phase and is not a monotone/robust measure. The median of the
    second half of ws averages over the oscillation for a stable radius."""
    ws = np.asarray(ws)
    return float(np.median(ws[len(ws) // 2:]))


def classify(ws, w_free):
    """classify relative to the g=0 free-dispersal baseline steady width w_free."""
    ws = np.asarray(ws)
    w0, w_steady, wmin = ws[0], steady_width(ws), ws.min()
    if wmin < 0.35 * w0:
        return "COLLAPSE (supercritical)"
    if w_steady < 0.75 * w_free:
        return "BOUND (self-gravity holds it)"
    return "unbound (disperses ~ free)"


def powerlaw_fit(gs, radii):
    """Least-squares fit radius = A * g^p on log-log axes.

    Returns (p, A, r2). Used for the soliton radius-vs-coupling scaling over a
    clean, monotone bound range (caller selects the range to avoid the
    supercritical high-g mess)."""
    gs = np.asarray(gs, float); radii = np.asarray(radii, float)
    x, y = np.log(gs), np.log(radii)
    p, b = np.polyfit(x, y, 1)
    yhat = p * x + b
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(p), float(np.exp(b)), float(r2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=64)
    ap.add_argument("--ndim", type=int, default=3)
    ap.add_argument("--T", type=int, default=1500)
    ap.add_argument("--scan", action="store_true", help="sweep g to find the binding threshold")
    ap.add_argument("--glist", type=str, default=None,
                    help='comma-separated g values for --scan, e.g. "1,2,5,10,20" '
                         "(low-g fine scan to locate the critical coupling)")
    ap.add_argument("--out", type=str, default="pathA_results.json",
                    help="output json filename (relative to repo root) for --scan")
    ap.add_argument("--fitlo", type=float, default=None,
                    help="lower g for the radius~g^p power-law fit (clean bound range)")
    ap.add_argument("--fithi", type=float, default=None,
                    help="upper g for the radius~g^p power-law fit (cut before supercritical mess)")
    a = ap.parse_args()
    print(f"backend = {B.NAME}   device = {B.device_info()}   {a.L}^{a.ndim} x {a.T}\n")
    if a.scan:
        if a.glist is not None:
            glist = [float(x) for x in a.glist.split(",") if x.strip() != ""]
        else:
            glist = [20.0, 60.0, 150.0, 400.0, 1000.0]
        out = {"ndim": a.ndim, "L": a.L, "T": a.T}
        ts_free, w_free_arr = run(L=a.L, ndim=a.ndim, T=a.T, g=0.0)
        w_free = steady_width(w_free_arr)
        out["free"] = {"ts": ts_free.tolist(), "ws": w_free_arr.tolist(),
                       "steady_width": w_free}
        print(f"free (g=0) baseline: w {w_free_arr[0]:.1f} -> steady {w_free:.1f}\n")
        print(f"{'g':>8}  {'w0':>6}  {'steady':>7}  {'wmin':>6}  verdict")
        results = {}
        for g in glist:
            if g == 0.0:
                ts, ws = ts_free, w_free_arr        # reuse the baseline run
            else:
                ts, ws = run(L=a.L, ndim=a.ndim, T=a.T, g=g)
            t0 = time.perf_counter()
            wsw = steady_width(ws)
            wmin = float(ws.min())
            v = classify(ws, w_free)
            results[g] = {"ts": ts.tolist(), "ws": ws.tolist(),
                          "steady_width": wsw, "wmin": wmin, "verdict": v}
            print(f"{g:8.0f}  {ws[0]:6.1f}  {wsw:7.1f}  {wmin:6.1f}  {v}"
                  f"   ({time.perf_counter()-t0:.1f}s)")
        out["scan"] = {str(g): r for g, r in results.items()}

        # mass-radius / dilution hook: soliton radius (steady_width) vs g
        bound = [(g, r["steady_width"]) for g, r in results.items()
                 if r["verdict"].startswith("BOUND")]
        out["mass_radius"] = [{"g": g, "steady_width": w} for g, w in bound]
        print(f"\nmass-radius (BOUND: mass fixed by norm, radius vs coupling):")
        if bound:
            print(f"{'g':>8}  {'radius (steady_width)':>22}")
            for g, w in sorted(bound):
                print(f"{g:8.0f}  {w:22.2f}")
        else:
            print("  (no BOUND cases in this scan)")

        # optional radius ~ g^p power-law fit over a user-chosen clean bound range
        if a.fitlo is not None and a.fithi is not None:
            fitpts = sorted((g, r["steady_width"]) for g, r in results.items()
                            if a.fitlo <= g <= a.fithi)
            if len(fitpts) >= 2:
                gs_f = [g for g, _ in fitpts]; rr_f = [w for _, w in fitpts]
                p, A, r2 = powerlaw_fit(gs_f, rr_f)
                out["powerlaw_fit"] = {"glo": a.fitlo, "ghi": a.fithi,
                                       "gs": gs_f, "radii": rr_f,
                                       "p": p, "A": A, "r2": r2}
                print(f"\nradius ~ g^p fit over g in [{a.fitlo},{a.fithi}] "
                      f"({len(fitpts)} pts):")
                print(f"  p = {p:.3f}   A = {A:.3f}   R^2 = {r2:.4f}")
            else:
                print(f"\n(fit range [{a.fitlo},{a.fithi}] has <2 points; skipped)")

        json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", a.out), "w"))
    else:
        ts, ws = run(L=a.L, ndim=a.ndim, T=a.T, g=150.0)
        _, wf = run(L=a.L, ndim=a.ndim, T=a.T, g=0.0)
        print("width trajectory:", [round(w, 1) for w in ws[::4]])
        print("verdict:", classify(ws, steady_width(wf)))
