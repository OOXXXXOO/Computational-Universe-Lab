"""rulespace_gpu.campaign — batched rule-space search on the device.

Evaluates MANY coupling vectors at once (batch axis 0) so a GPU can screen
thousands of candidate field-rules per second. This is the GPU-scaled core of
the judge funnel (rulespace/judges.py on CPU).

Batched model (1+1D, the screening dimension): for each rule a in the batch,
  theta_{t+1} = 2 theta_t - theta_{t-1} + sum_i a_i O_i(theta, rho)
with the same 6-operator library as the CPU campaign. The walker (rho source)
rides along on each ring. Returns per-rule stability + matter-response scores.
"""
import numpy as np
from . import backend as B
from rulespace import core as _core   # CPU reference (packet + walker convention)
xp = B.xp

TH_MIN, TH_MAX, TH_REF = 0.08, 1.25, 0.45
PAR_NAMES = ["Lap", "(grad)^2", "rho", "J", "th-ref", "damp"]


def _lap1(f):   return B.roll(f, 1, 1) + B.roll(f, -1, 1) - 2.0 * f
def _grad1(f):  return 0.5 * (B.roll(f, -1, 1) - B.roll(f, 1, 1))


def _coin(x0, x1, t):
    c = xp.cos(t); s = 1j * xp.sin(t); return c * x0 + s * x1, s * x0 + c * x1


def _wstep(x0, x1, t, dmv):
    """One split-step walker tick, batched over axis 0.

    EXACT mirror of rulespace.core.walker_step (coin(th); shift p0 right;
    coin(-th+dm); shift p1 left) so the GPU funnel screens the SAME walker
    unitary the CPU judges evolve. (An earlier version used engine.py's
    Hadamard-conjugated shift, a *different* walk with different dispersion:
    rho trajectories diverged from run_coupled's and ~13% of the "lawful" set
    failed the CPU J4 judge on re-check.)  dmv is a device scalar (mass gap).
    """
    x0, x1 = _coin(x0, x1, t)
    x0 = B.roll(x0, 1, 1)
    x0, x1 = _coin(x0, x1, dmv - t)
    x1 = B.roll(x1, -1, 1)
    return x0, x1


_EPS = 1e-9
VAR_MIN = 1e-13    # min per-sample var(theta_tt) for a REAL-dynamics J4 fit (see _fit_reduced)


def _step_lean(th, thp, p0, p1, sat, a0, a1, a2, a3, a4, a5, dmv):
    """Single J1 step (field + walker + saturation), no Gram accumulation.

    Loop-carried state in/out: (th, thp, p0, p1, sat). Pure -> B.jit-able.
    Returns the state advanced one tick, in the same order.
    """
    Bn = th.shape[0]
    rho = B.real(p0) ** 2 + B.imag(p0) ** 2 + B.real(p1) ** 2 + B.imag(p1) ** 2
    rho_c = rho - xp.reshape(xp.mean(rho, 1), (Bn, 1))
    force = (a0 * _lap1(th) + a1 * _grad1(th) ** 2 + a2 * rho_c
             + a3 * (B.real(p0) ** 2 + B.imag(p0) ** 2 - B.real(p1) ** 2 - B.imag(p1) ** 2)
             + a4 * (th - TH_REF) + a5 * (th - thp))
    nxt = 2.0 * th - thp + force
    clipped = xp.clip(nxt, TH_MIN, TH_MAX)
    sat = sat + xp.mean(1.0 * (xp.abs(clipped - nxt) > 1e-12), 1)
    p0, p1 = _wstep(p0, p1, clipped, dmv)              # advance walker with NEW theta
    return clipped, th, p0, p1, sat                    # (th, thp, p0, p1, sat)


def _step_fit(th, thp, p0, p1, sat, Sll, Sls, Sss, Sly, Ssy, Sy, Syy, nn,
              a0, a1, a2, a3, a4, a5, dmv, fit_flag):
    """Single step that ALSO accumulates the reduced-fit Gram sums.

    fit_flag is a device scalar (1.0 for 1<=t<=T-2, else 0.0) so the compiled
    graph is built once and gates accumulation without a Python branch.
    Loop-carried state: (th, thp, p0, p1, sat, Sll..nn). Pure -> B.jit-able.
    """
    Bn = th.shape[0]
    rho = B.real(p0) ** 2 + B.imag(p0) ** 2 + B.real(p1) ** 2 + B.imag(p1) ** 2
    J = B.real(p0) ** 2 + B.imag(p0) ** 2 - B.real(p1) ** 2 - B.imag(p1) ** 2
    rho_c = rho - xp.reshape(xp.mean(rho, 1), (Bn, 1))
    lapth = _lap1(th)
    force = (a0 * lapth + a1 * _grad1(th) ** 2 + a2 * rho_c + a3 * J
             + a4 * (th - TH_REF) + a5 * (th - thp))
    nxt = 2.0 * th - thp + force
    clipped = xp.clip(nxt, TH_MIN, TH_MAX)
    sat = sat + xp.mean(1.0 * (xp.abs(clipped - nxt) > 1e-12), 1)
    # observer's reduced law: y = th_tt = b1*Lap(th) + b2*(rho-mean)
    y = clipped - 2.0 * th + thp                       # th[t+1]-2th[t]+th[t-1]
    src = rho_c                                        # rho[t]-mean(rho[t])
    m = (1.0 * (clipped > TH_MIN + _EPS)) * (1.0 * (clipped < TH_MAX - _EPS))
    Sll = Sll + fit_flag * xp.sum(m * lapth * lapth, 1)
    Sls = Sls + fit_flag * xp.sum(m * lapth * src, 1)
    Sss = Sss + fit_flag * xp.sum(m * src * src, 1)
    Sly = Sly + fit_flag * xp.sum(m * lapth * y, 1)
    Ssy = Ssy + fit_flag * xp.sum(m * src * y, 1)
    Sy = Sy + fit_flag * xp.sum(m * y, 1)
    Syy = Syy + fit_flag * xp.sum(m * y * y, 1)
    nn = nn + fit_flag * xp.sum(m, 1)
    p0, p1 = _wstep(p0, p1, clipped, dmv)              # advance walker with NEW theta
    return clipped, th, p0, p1, sat, Sll, Sls, Sss, Sly, Ssy, Sy, Syy, nn


def _twin_step(th, thp, a0, a1, a4, a5):
    """Single matter-free twin step (rho/J source == 0). Pure -> B.jit-able."""
    force = (a0 * _lap1(th) + a1 * _grad1(th) ** 2
             + a4 * (th - TH_REF) + a5 * (th - thp))
    nxt = 2.0 * th - thp + force
    clipped = xp.clip(nxt, TH_MIN, TH_MAX)
    return clipped, th                                 # (th, thp)


# compiled once at import: B.jit == mx.compile on MLX, jax.jit on jax, identity on numpy
_step_lean_jit = B.jit(_step_lean)
_step_fit_jit = B.jit(_step_fit)
_twin_step_jit = B.jit(_twin_step)


def _evolve(a_cols, Bn, N, T, k0, sig, amp, center, dm,
            want_snap=False, want_fit=False, jit=True):
    """One batched walker+coin-field trajectory (Bn rules in parallel).

    Mirrors rulespace.core.run_coupled's ordering: record (th_t, rho_t) then
    step the field, then advance the walker with the NEW theta.

    The per-step body is a pure function (_step_lean / _step_fit); when jit is
    True it is compiled once (B.jit) and called in the Python time loop. The
    loop-carried accumulators (sat, snapshot, Gram sums) are threaded through
    the compiled calls, so they stay exact across the compiled loop.

    Returns dict with per-rule (Bn,) arrays:
      sat, var                          (J1 stability)
      snap  = theta at time T//4        (if want_snap; for J3)
      Gram sums Sll,Sls,Sss,Sly,Ssy,Sy,Syy,nn   (if want_fit; for J4 reduced fit)
    """
    a0, a1, a2, a3, a4, a5 = a_cols
    # host-side packet from the CPU reference (rulespace.core.packet), so the
    # initial branch spinor matches the walker unitary _wstep now implements.
    p0h, p1h = _core.packet(N, center, k0, sig, dm=dm)
    p0 = xp.broadcast_to(xp.reshape(B.asarray(p0h), (1, N)), (Bn, N)) * amp
    p1 = xp.broadcast_to(xp.reshape(B.asarray(p1h), (1, N)), (Bn, N)) * amp
    p0 = p0 + 0.0j; p1 = p1 + 0.0j
    th = xp.full((Bn, N), TH_REF); thp = th
    dmv = B.asarray(np.array(float(dm)))               # device scalar (mass gap)

    sat = xp.zeros((Bn,))
    snap = th
    snap_t = T // 4

    if want_fit:
        z = xp.zeros((Bn,))
        Sll = z; Sls = z; Sss = z; Sly = z; Ssy = z; Sy = z; Syy = z; nn = z
        step = _step_fit_jit if jit else _step_fit
        one = B.asarray(np.array(1.0)); zero = B.asarray(np.array(0.0))
        carry = (th, thp, p0, p1, sat, Sll, Sls, Sss, Sly, Ssy, Sy, Syy, nn)
        for t in range(T):
            if want_snap and t == snap_t:
                snap = carry[0]                        # theta at time T//4
            flag = one if (1 <= t <= T - 2) else zero
            carry = step(*carry, a0, a1, a2, a3, a4, a5, dmv, flag)
        (th, thp, p0, p1, sat, Sll, Sls, Sss, Sly, Ssy, Sy, Syy, nn) = carry
    else:
        step = _step_lean_jit if jit else _step_lean
        carry = (th, thp, p0, p1, sat)
        for t in range(T):
            if want_snap and t == snap_t:
                snap = carry[0]                        # theta at time T//4
            carry = step(*carry, a0, a1, a2, a3, a4, a5, dmv)
        (th, thp, p0, p1, sat) = carry

    out = {"sat": sat, "var": xp.var(th, 1)}
    if want_snap:
        out["snap"] = snap
    if want_fit:
        out.update(Sll=Sll, Sls=Sls, Sss=Sss, Sly=Sly, Ssy=Ssy, Sy=Sy, Syy=Syy, nn=nn)
    return out


def _twin(a_cols, Bn, N, Thalf, jit=True):
    """matter-free twin: same coin-field rule but rho/J source forced to zero.
    Mirrors judges.j3_response's twin loop. Returns theta after Thalf steps."""
    a0, a1, _a2, _a3, a4, a5 = a_cols
    th = xp.full((Bn, N), TH_REF); thp = th
    step = _twin_step_jit if jit else _twin_step
    for _t in range(Thalf):
        th, thp = step(th, thp, a0, a1, a4, a5)
    return th


def _fit_reduced(s):
    """Closed-form 2-parameter LSQ per rule from accumulated Gram sums.
    Returns (b1, b2, r2) as (Bn,) device arrays. Mirrors judges._fit_reduced."""
    Sll, Sls, Sss = s["Sll"], s["Sls"], s["Sss"]
    Sly, Ssy = s["Sly"], s["Ssy"]
    Sy, Syy, nn = s["Sy"], s["Syy"], s["nn"]
    det = Sll * Sss - Sls * Sls
    # det==0 => rank-deficient (e.g. Lap column identically zero for a constant
    # field). Substitute det_safe=1 so b->0 there; residual is then unmodeled and
    # R^2 follows naturally, matching numpy.lstsq's minimum-norm behavior.
    det_safe = xp.where(xp.abs(det) < 1e-30, xp.ones_like(det), det)
    b1 = (Sss * Sly - Sls * Ssy) / det_safe
    b2 = (Sll * Ssy - Sls * Sly) / det_safe
    ss_res = Syy - 2.0 * (b1 * Sly + b2 * Ssy) + (b1 * b1 * Sll + 2.0 * b1 * b2 * Sls + b2 * b2 * Sss)
    nn_safe = xp.where(nn < 0.5, xp.ones_like(nn), nn)
    ss_tot = Syy - Sy * Sy / nn_safe
    r2 = 1.0 - ss_res / xp.maximum(ss_tot, 1e-30)
    # Fail two degenerate cases (mirrors judges._fit_reduced's VAR_MIN guard):
    #  * nn==0: no unsaturated samples at all;
    #  * var(y) = SS_tot/nn below VAR_MIN: a numerically frozen theta_tt would
    #    give SS_tot ~ 0 -> R^2=1, b=0, dispersion 0 -- a degenerate J4 auto-
    #    pass for rules with no real field dynamics. VAR_MIN sits ~2 decades
    #    above the fp32 rounding floor of y (~1e-15) and ~2 decades below the
    #    weakest genuine lawful dynamics observed (var(y) ~ 9e-12).
    have = (nn > 0.5) & (ss_tot > VAR_MIN * nn_safe)
    b1 = xp.where(have, b1, xp.zeros_like(b1))
    b2 = xp.where(have, b2, xp.zeros_like(b2))
    r2 = xp.where(have, r2, -1.0 + xp.zeros_like(r2))
    return b1, b2, r2


# fixed matter states for the equivalence-principle test (mirror judges.j4_universality)
def _j4_states(N):
    return [dict(k0=0.8, sig=10.0, amp=1.0, center=N // 2),
            dict(k0=1.4, sig=22.0, amp=1.0, center=N // 3),
            dict(k0=0.8, sig=10.0, amp=0.55, center=N // 2)]


def sweep(couplings, N=256, T=500, k0=0.8, sig=10.0, dm=0.0, seed=0, full=True,
          jit=True):
    """couplings: (Bn, 6) host array. Returns dict of per-rule score arrays.

    full=False  -> J1 only (fast; what pathC_scale's default scan uses).
    full=True   -> the fuller funnel: J1 stability + J3 response + J4 universality.
    jit=True    -> compile the batched time loop (B.jit; no-op on numpy). Set
                   False to run the un-compiled reference path (verification).
    """
    Bn = couplings.shape[0]
    a = B.asarray(np.asarray(couplings))                      # (Bn,6) device
    a_cols = tuple(xp.reshape(a[:, i], (Bn, 1)) for i in range(6))

    # ---- J1 stability + (if full) J3 snapshot, on the base matter state ----
    base = _evolve(a_cols, Bn, N, T, k0, sig, 1.0, N // 2, dm, want_snap=full, jit=jit)
    var = B.to_np(base["var"])
    satr = B.to_np(base["sat"]) / T
    stable = (satr < 0.01) & (var < 0.25)
    res = {"final_var": var, "saturation": satr, "stable": stable}
    if not full:
        return res

    # ---- J3 response: real field @ T//4 vs matter-free twin @ T//2 ----
    twin = _twin(a_cols, Bn, N, T // 2, jit=jit)
    matter_effect = B.to_np(xp.max(xp.abs(base["snap"] - twin), 1))
    J3 = matter_effect > 1e-4

    # ---- J4 universality: reduced 2-param law across >=3 matter states ----
    b1s, b2s, r2s = [], [], []
    for st in _j4_states(N):
        s = _evolve(a_cols, Bn, N, T, st["k0"], st["sig"], st["amp"], st["center"],
                    dm, want_fit=True, jit=jit)
        b1, b2, r2 = _fit_reduced(s)
        b1s.append(b1); b2s.append(b2); r2s.append(r2)

    def _disp(bs):
        mean = (bs[0] + bs[1] + bs[2]) / 3.0
        scale = (xp.abs(bs[0]) + xp.abs(bs[1]) + xp.abs(bs[2])) / 3.0 + 1e-12
        d = xp.abs(bs[0] - mean) / scale
        for k in (1, 2):
            d = xp.maximum(d, xp.abs(bs[k] - mean) / scale)
        return d
    d = xp.maximum(_disp(b1s), _disp(b2s))                    # coefficient dispersion
    r2min = xp.minimum(xp.minimum(r2s[0], r2s[1]), r2s[2])
    univ_dist = B.to_np(d)
    r2_reduced_min = B.to_np(r2min)
    J4 = (univ_dist < 0.10) & (r2_reduced_min > 0.90)

    res.update(matter_effect=matter_effect, J3=J3,
               univ_dist=univ_dist, r2_reduced_min=r2_reduced_min, J4=J4,
               lawful=stable & J3 & J4)
    return res


def random_couplings(n, seed=0):
    rng = np.random.default_rng(seed)
    a = np.zeros((n, 6))
    a[:, 0] = np.where(rng.random(n) < 0.9, 10 ** rng.uniform(-2.5, -0.1, n), 0)
    a[:, 2] = np.where(rng.random(n) < 0.85, np.sign(rng.random(n) - .3) * 10 ** rng.uniform(-3, -.5, n), 0)
    a[:, 4] = np.where(rng.random(n) < 0.7, -(10 ** rng.uniform(-4, -1.3, n)), 0)
    a[:, 5] = np.where(rng.random(n) < 0.6, -(10 ** rng.uniform(-3, -1, n)), 0)
    return a


if __name__ == "__main__":
    import time
    print(f"backend = {B.NAME}   device = {B.device_info()}")
    n = 512
    cpl = random_couplings(n)
    t0 = time.perf_counter()
    res = sweep(cpl, T=400, full=True)
    dt = time.perf_counter() - t0
    print(f"screened {n} rules x 400 steps (full funnel) in {dt:.2f}s  ({n/dt:.0f} rules/s)")
    s, s3 = res["stable"], res["stable"] & res["J3"]
    print(f"J1 stable        : {int(s.sum())}/{n} ({100*s.mean():.1f}%)")
    print(f"J1 & J3          : {int(s3.sum())}/{n} ({100*s3.mean():.1f}%)")
    print(f"full funnel lawful: {int(res['lawful'].sum())}/{n} ({100*res['lawful'].mean():.1f}%)")
