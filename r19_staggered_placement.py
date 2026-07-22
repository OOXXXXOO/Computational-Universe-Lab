"""r19_staggered_placement -- the STAGGERED-h construction: component_phase
moved from k-space into REAL-SPACE STORAGE, closing the R15/R17 placement gap
(小报告-R15放置算子缺口 / 小报告-R17实空间放置缺口) at certificate level.

THE GAP (three lane-B rounds hit it).  R17 certified the placed de-Donder
symbol kappa_placed = (2 sin(w/2)/c, 2 sin(k_i/2)) at OPERATOR level, but the
factor that puts TT inside ker K is the COMPONENT PHASE e^{i k.o/2},
o = e_mu + e_nu -- the field's own half-cell placement.  Every real-space
implementation so far stored h_munu at INTEGER points (h = Re chi on the
integer grid) and tried to recover the phase with stencil choices
(central/forward/backward, "one-line fwd/bwd branch").  All provably fail:
integer rolls cannot synthesize e^{+-ik/2}; |K@TT| = 0.29, dim(ker/gauge) = 5/6.

THE CONSTRUCTION (this file).  Placement is a STORAGE SEMANTICS, not a stencil:

    stored array of component c = (mu,nu), integer index (n, j):
        H_c[n, j]  :=  hbar_munu( t = n + o_c[0]/2 ,  x = j + o_c,sp/2 )
    with o_c = (e_mu + e_nu) mod 2  (0/1 half-step flags; diagonal components
    have o = 2 e_mu = whole-cell shift = trivially integer -- absorbed by
    sublattice relabeling; spatial off-diagonal = face centers; 0i = half TIME
    step, realized by leapfrog slice semantics, NO interpolation).

    K_placed (integer rolls between the staggered sublattices + the pairing
    convention -- this is the entire operator):
        row C_nu lives at  x + e_nu,sp/2  (and t = n+1/2 for nu = 0):
        spatial mu:  component (mu,nu):  backward roll  f - S_+ f   if
                     o[mu] = 1,  forward  S_- f - f  otherwise (R17 dictionary);
        time  mu=0:  component (0,nu):   slices (cur - prev)  if o[0] = 1
                     (the 0i fields live at half times, so cur-prev is CENTERED
                     at integer time n), slices (next - cur) for nu = 0
                     (h_00 is integer-time, so next-cur is centered at n+1/2).
    NO phase ever appears in the operator: for a field stored AT its own
    staggered points, plain integer rolls between the sublattices realize the
    half-cell-centered difference exactly.  The e^{i k.o/2} of R17 is where the
    plane-wave VALUES of the staggered samples carry it -- i.e., in the data,
    which is what "placement is a construction, not a read-out template" means.

WHY THIS IS DISTINGUISHABLE FROM THE KNOWN NEGATIVE CONTROLS
    * staggered_geometry.py literal Yee (M1, N_prop=5): staggered only the 0nu
      row in TIME and kept full-angle central spatial stencils -> mixed
      half/full-angle symbol, kappa.kappa != 0 on shell (neg control B below).
    * cp1v2/v3 (lane B): correct fwd/bwd dictionary but INTEGER storage (no
      component placement) -> |K@TT| = 0.29 (neg control C below).
    * plain central template (CP0/CP1-v1): neg control A below.

CERTIFICATES (all single-k, on-shell, fp64)
    0  k-space oracle: re-run the R17 certified operator matrix on 120+ random
       3D k: |K@TT|, |K@gauge| ~ 1e-16, rank 4, dim(ker/gauge) = 2.
    1  real-space == oracle: assemble K_placed's action on unit staggered
       plane waves (both +w and -w branches), project at the target points ->
       matrix identical to the R17 oracle to machine precision, and the output
       field is EXACTLY a single plane wave (off-mode residual ~ 1e-16).
    A  HARD GATE: |K_placed @ TT| < 1e-12 and |K_placed @ gauge| < 1e-12
       (gauge on shell), measured by direct real-space application; plus the
       REAL-FIELD version (h = Re of the staggered wave) -- K_placed has real
       coefficients, so annihilation survives Re (the +-k pair is jointly
       staggered-consistent).
    B  HARD GATE: dim(ker K_placed / gauge) = 2, rank 4 (r15/r17 counting
       machinery on the real-space-assembled matrix), all test k, both branches.
    NEG (must FAIL): (a) integer central template |K@TT| >~ 0.1, dim != 2;
       (b) literal Yee (time-staggered 0nu + central spatial) wrong dim /
       |K@TT| != 0; (c) dictionary stencils WITHOUT staggered storage (the
       as-built cp1v2) |K@TT| ~ 0.3.
    5  dynamic smoke (16^3, R14 walk kernel, no damping): seed on-shell
       staggered TT / gauge / generic; evolve; measure K_placed every step.
       TT: constraint stays at machine zero (ALL k -- transversality does not
       need the shell).  gauge: machine zero on AXIS k (walk shell exact);
       oblique k floor = |kappa.kappa|(w_walk) = the pre-registered Trotter
       shell correction of the non-palindromic 3D walk (R15 §5), NOT a
       placement failure -- reported, not gated.  generic: O(1) (teeth).

Run:  RULESPACE_BACKEND=numpy .venv/bin/python r19_staggered_placement.py
      (~1-2 min; writes r19_results.json)
"""
import json
import math
import os

import numpy as np

import r15_walk_dedonder as r15
import r17_placement_operators as r17

DIR = os.path.dirname(os.path.abspath(__file__))
C_CONE = r15.C_CONE                     # cos(pi/3) = 0.5 (lane B's theta)
ETA = r15.ETA
SYM = r15.SYM                           # packed order 00,01,02,03,11,...,33
PKC = {}
for _i, (_m, _n) in enumerate(SYM):
    PKC[(_m, _n)] = _i
    PKC[(_n, _m)] = _i

# offset flags o_c = (e_mu + e_nu) mod 2, one row per packed component
OFFSET = np.array([r17.offset(m, n) for (m, n) in SYM])          # (10, 4)
OFF_ZERO = np.zeros_like(OFFSET)                                 # integer storage
OFF_YEE = np.zeros_like(OFFSET)                                  # literal-Yee ctrl:
for _nu in range(4):                                             # 0nu rows on the
    OFF_YEE[PKC[(0, _nu)], 0] = 1                                # half TIME grid only


# ===========================================================================
#  staggered storage: seeding + the real-space placed operator
# ===========================================================================
def plane(kv, N):
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    return np.exp(1j * (kv[0] * X + kv[1] * Y + kv[2] * Z))


def colfac(k4, offsets):
    """value phase of the staggered SAMPLES of a plane wave: e^{i k4.o/2}."""
    return np.array([np.exp(0.5j * float(np.dot(k4, offsets[c])))
                     for c in range(10)])


def seed_slices(a10, k4, N, offsets, nsl=3, base=None):
    """staggered-STORED plane wave: slice n, comp c value =
       a_c * exp(i(w (n + o0/2) + k.(x + osp/2))).
    The arrays are plain integer-indexed; the staggering is in what the
    samples MEAN (and hence in their values)."""
    w, kv = k4[0], k4[1:]
    if base is None:
        base = plane(kv, N)
    cf = colfac(k4, offsets)
    return [np.stack([a10[c] * cf[c] * np.exp(1j * w * n) * base
                      for c in range(10)]) for n in range(nsl)]


def D_dict(f, mu, comp, offsets=OFFSET):
    """R17 dictionary spatial difference by integer roll between sublattices."""
    ax = mu - 1
    if offsets[comp][mu]:
        return f - np.roll(f, 1, axis=ax)          # backward  f(x)-f(x-e)
    return np.roll(f, -1, axis=ax) - f             # forward   f(x+e)-f(x)


def K_placed(Hp, Hc, Hn, c=C_CONE, offsets=OFFSET):
    """the real-space placed de-Donder operator on staggered storage.
    rows: C_0 at (t = n+1/2, x integer); C_i at (t = n, x + e_i/2).
    Time pairing convention: half-time components (0i) difference (cur - prev)
    [centered at integer n]; integer-time h_00 difference (next - cur)
    [centered at n+1/2].  Integer rolls + pairing -- no phases, no interp."""
    C = np.zeros((4,) + Hc.shape[1:], complex)
    for nu in range(4):
        acc = np.zeros(Hc.shape[1:], complex)
        for mu in (1, 2, 3):
            comp = PKC[(mu, nu)]
            acc = acc + D_dict(Hc[comp], mu, comp, offsets)
        c0 = PKC[(0, nu)]
        dt = (Hc[c0] - Hp[c0]) if offsets[c0][0] else (Hn[c0] - Hc[c0])
        C[nu] = acc - dt / c                       # eta^00 = -1, time /c
    return C


# ---- negative-control operators (each with its own storage semantics) -----
def K_central(Hp, Hc, Hn, c=C_CONE):
    """NEG (a): integer-grid central template (CP0/CP1-v1 disease)."""
    C = np.zeros((4,) + Hc.shape[1:], complex)
    for nu in range(4):
        acc = np.zeros(Hc.shape[1:], complex)
        for mu in (1, 2, 3):
            f = Hc[PKC[(mu, nu)]]
            acc = acc + 0.5 * (np.roll(f, -1, axis=mu - 1)
                               - np.roll(f, 1, axis=mu - 1))
        c0 = PKC[(0, nu)]
        C[nu] = acc - 0.5 * (Hn[c0] - Hp[c0]) / c
    return C


def K_yee_literal(Hp, Hc, Hn, c=C_CONE):
    """NEG (b): literal-Yee a la staggered_geometry.make_rule_compact_yee --
    0nu rows on the half TIME grid (stride-1 explicit time diff) but spatial
    stencils stay full-angle central, components NOT spatially placed."""
    C = np.zeros((4,) + Hc.shape[1:], complex)
    for nu in range(4):
        acc = np.zeros(Hc.shape[1:], complex)
        for mu in (1, 2, 3):
            f = Hc[PKC[(mu, nu)]]
            acc = acc + 0.5 * (np.roll(f, -1, axis=mu - 1)
                               - np.roll(f, 1, axis=mu - 1))
        c0 = PKC[(0, nu)]
        C[nu] = acc - (Hc[c0] - Hp[c0]) / c        # stride-1 on half-time row
    return C


def K_nophase(Hp, Hc, Hn, c=C_CONE):
    """NEG (c): the as-built cp1v2 -- R17 fwd/bwd dictionary stencils but
    INTEGER storage (call with unstaggered-seeded slices) and macro-step
    backward time difference on every row."""
    C = np.zeros((4,) + Hc.shape[1:], complex)
    for nu in range(4):
        acc = np.zeros(Hc.shape[1:], complex)
        for mu in (1, 2, 3):
            comp = PKC[(mu, nu)]
            acc = acc + D_dict(Hc[comp], mu, comp, OFFSET)   # dict stencils
        c0 = PKC[(0, nu)]
        C[nu] = acc - (Hc[c0] - Hp[c0]) / c
    return C


# ===========================================================================
#  projection / assembly machinery
# ===========================================================================
def project_rows(Crows, k4, N, n_cur=1, base=None, staggered_target=True):
    """extract the plane-wave amplitude of each constraint row, referred to the
    row's own target point, and the worst off-mode residual (must be ~0:
    a shift-invariant operator maps a plane wave to a plane wave)."""
    w, kv = k4[0], k4[1:]
    if base is None:
        base = plane(kv, N)
    pb = np.conj(base) / base.size
    amps = np.zeros(4, complex)
    off = 0.0
    for nu in range(4):
        if staggered_target:
            tp = (np.exp(1j * w * (n_cur + 0.5)) if nu == 0
                  else np.exp(1j * (w * n_cur + 0.5 * kv[nu - 1])))
        else:
            tp = np.exp(1j * w * n_cur)
        a = np.sum(pb * Crows[nu]) / tp
        amps[nu] = a
        off = max(off, float(np.abs(Crows[nu] - a * tp * base).max()))
    return amps, off


def assemble_K(applyK, k4, N, seed_offsets, staggered_target=True):
    """probe the real-space operator with the 10 unit staggered plane waves and
    project -> the (4,10) matrix it realizes on PHYSICAL amplitudes."""
    base = plane(k4[1:], N)
    K = np.zeros((4, 10), complex)
    offmax = 0.0
    for c in range(10):
        a = np.zeros(10)
        a[c] = 1.0
        Hs = seed_slices(a, k4, N, seed_offsets, 3, base)
        amps, off = project_rows(applyK(Hs[0], Hs[1], Hs[2]), k4, N, 1, base,
                                 staggered_target)
        K[:, c] = amps
        offmax = max(offmax, off)
    return K, offmax


def apply_norm(applyK, a10, k4, N, seed_offsets, base=None):
    """max |K field| for a unit-norm amplitude vector, direct real-space."""
    a = a10 / (np.linalg.norm(a10) + 1e-300)
    Hs = seed_slices(a, k4, N, seed_offsets, 3, base)
    return float(np.abs(applyK(Hs[0], Hs[1], Hs[2])).max())


def kset_lattice(N=16):
    """commensurate test wavevectors (axis / planar / oblique / generic)."""
    nvecs = [(2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2), (3, 1, 0),
             (1, 2, 3), (4, 1, 1), (2, -2, 1), (3, 0, 2), (1, 1, 1),
             (5, 2, 1), (2, 3, -1), (4, 4, 2), (6, 1, 0), (1, -3, 2)]
    out = []
    for nv in nvecs:
        k = np.array(nv, float) * (2 * np.pi / N)
        if r15.shell_omega(k) is not None and np.linalg.norm(k) > 0.05:
            out.append((nv, k))
    return out


def branch_k4(k, sign):
    """on-shell 4-frequency, +w (R17 convention) or -w (walk convention),
    with the matching kappa vector (kappa_0 flips sign with the branch)."""
    w = r15.shell_omega(k)
    kap = r15.kappa_placed(k).astype(float)
    if sign < 0:
        kap = kap.copy()
        kap[0] = -kap[0]
    return np.array([sign * w, k[0], k[1], k[2]]), kap


# ===========================================================================
#  PART 0: k-space oracle (R17 re-certification)
# ===========================================================================
def part0_oracle():
    rng = np.random.default_rng(0)
    ks = [np.array([0.5, 0.0, 0.0]), np.array([0.35, 0.35, 0.35]),
          np.array([0.7, 0.2, -0.4])]
    ks += [rng.uniform(-1.1, 1.1, 3) for _ in range(120)]
    ks = [k for k in ks if r15.shell_omega(k) is not None
          and np.linalg.norm(k) > 1e-2]
    worst_tt, worst_g, worst_dtt = 0.0, 0.0, 0.0
    ranks, dims = set(), set()
    for k in ks:
        k4, kap = branch_k4(k, +1)
        C = r17.constraint_matrix_op(k4) / 1j
        TT = r15.tt_basis(kap)
        TTn = TT / np.linalg.norm(TT, axis=0, keepdims=True)
        worst_tt = max(worst_tt, float(np.abs(C @ TTn).max()))
        cg, rank, dimq, dtt = r17.analyze_C(C, kap)
        worst_g = max(worst_g, cg)
        ranks.add(rank)
        dims.add(dimq)
        if dimq == 2:
            worst_dtt = max(worst_dtt, dtt)
    ok = (worst_tt < 1e-12 and worst_g < 1e-12 and ranks == {4}
          and dims == {2} and worst_dtt < 1e-6)
    return {"n_k": len(ks), "worst_KTT": worst_tt, "worst_Kgauge": worst_g,
            "ranks": sorted(ranks), "dims_ker_over_gauge": sorted(dims),
            "worst_dist_TT": worst_dtt, "PASS": bool(ok)}


# ===========================================================================
#  PART 1 + HARD GATES A/B: real space
# ===========================================================================
def parts_1_A_B(N=16):
    ks = kset_lattice(N)
    out = {"N": N, "n_k": len(ks), "branches": [+1, -1]}
    max_dev, max_off = 0.0, 0.0
    worst_tt, worst_g, worst_dtt = 0.0, 0.0, 0.0
    ranks, dims = set(), set()
    for nv, k in ks:
        base = plane(k, N)
        for sign in (+1, -1):
            k4, kap = branch_k4(k, sign)
            # -- Part 1: real-space assembly == k-space oracle ---------------
            Kreal, off = assemble_K(lambda a, b, c: K_placed(a, b, c),
                                    k4, N, OFFSET)
            Korl = r17.constraint_matrix_op(k4)
            max_dev = max(max_dev, float(np.abs(Kreal - Korl).max()))
            max_off = max(max_off, off)
            # -- Gate A: direct application to on-shell TT / gauge -----------
            TT = r15.tt_basis(kap)
            G = r15.gauge_block(kap)
            for p in range(2):
                worst_tt = max(worst_tt, apply_norm(K_placed, TT[:, p],
                                                    k4, N, OFFSET, base))
            for p in range(4):
                worst_g = max(worst_g, apply_norm(K_placed, G[:, p],
                                                  k4, N, OFFSET, base))
            # -- Gate B: counting machinery on the REAL-SPACE matrix ---------
            cg, rank, dimq, dtt = r17.analyze_C(Kreal / 1j, kap)
            ranks.add(rank)
            dims.add(dimq)
            if dimq == 2:
                worst_dtt = max(worst_dtt, dtt)

    # -- Gate A': REAL-VALUED field (h = Re of the staggered wave) ----------
    nv, k = ks[2]                                   # (2,2,0): planar, generic-ish
    k4, kap = branch_k4(k, +1)
    base = plane(k, N)
    real_worst = 0.0
    TT = r15.tt_basis(kap)
    G = r15.gauge_block(kap)
    for v in [TT[:, 0], TT[:, 1], G[:, 1], G[:, 2]]:
        a = v / (np.linalg.norm(v) + 1e-300)
        Hs = [np.real(s) for s in seed_slices(a, k4, N, OFFSET, 3, base)]
        real_worst = max(real_worst,
                         float(np.abs(K_placed(Hs[0], Hs[1], Hs[2])).max()))

    out["part1_symbol_match"] = {"max_dev_vs_oracle": max_dev,
                                 "max_offmode_residual": max_off,
                                 "PASS": bool(max_dev < 1e-12 and max_off < 1e-12)}
    out["gateA"] = {"worst_KTT": worst_tt, "worst_Kgauge": worst_g,
                    "realfield_worst": real_worst,
                    "PASS": bool(worst_tt < 1e-12 and worst_g < 1e-12
                                 and real_worst < 1e-12)}
    out["gateB"] = {"ranks": sorted(ranks), "dims_ker_over_gauge": sorted(dims),
                    "worst_dist_TT": worst_dtt,
                    "PASS": bool(ranks == {4} and dims == {2}
                                 and worst_dtt < 1e-6)}
    return out


# ===========================================================================
#  NEGATIVE CONTROLS (each must FAIL)
# ===========================================================================
def part_neg(N=16):
    ks = kset_lattice(N)
    ctrls = {
        "a_central_integer": (K_central, OFF_ZERO),
        "b_literal_yee": (K_yee_literal, OFF_YEE),
        "c_dict_no_placement": (K_nophase, OFF_ZERO),
    }
    out = {}
    for name, (op, soff) in ctrls.items():
        worst_tt, worst_g = 0.0, 0.0
        dims = set()
        for nv, k in ks:
            base = plane(k, N)
            k4, kap = branch_k4(k, +1)
            TT = r15.tt_basis(kap)
            G = r15.gauge_block(kap)
            for p in range(2):
                worst_tt = max(worst_tt, apply_norm(op, TT[:, p], k4, N,
                                                    soff, base))
            for p in range(4):
                worst_g = max(worst_g, apply_norm(op, G[:, p], k4, N,
                                                  soff, base))
            Kc, _ = assemble_K(op, k4, N, soff, staggered_target=False)
            _, _, dimq, _ = r17.analyze_C(Kc / 1j, kap)
            dims.add(dimq)
        fails = bool(worst_tt > 1e-6 or sorted(dims) != [2])
        out[name] = {"worst_KTT": worst_tt, "worst_Kgauge": worst_g,
                     "dims_ker_over_gauge": sorted(dims),
                     "FAILS_AS_REQUIRED": fails}
    out["teeth_PASS"] = bool(all(v["FAILS_AS_REQUIRED"] for v in out.values()
                                 if isinstance(v, dict)))
    return out


# ===========================================================================
#  PART 5: dynamic smoke test on the R14 walk kernel (no damping)
# ===========================================================================
def part_smoke(N=16, T=160, th0=math.pi / 3.0):
    from rulespace_gpu import green_one_walk as gw
    c = math.cos(th0)

    def onshell_mode(nvec):
        kl = np.array(nvec, float) * (2 * np.pi / N)
        x = np.arange(N)
        X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
        ph = np.exp(1j * (kl[0] * X + kl[1] * Y + kl[2] * Z))
        proj = np.conj(ph) / N ** 3
        M = np.zeros((2, 2), complex)
        for s in range(2):
            c0 = np.zeros((1, N, N, N, 2), complex)
            c0[0, ..., s] = ph
            c0 = gw.geom_walk_all(c0, th0, th0, th0, th0)
            for r in range(2):
                M[r, s] = np.sum(proj * c0[0, ..., r])
        ev, V = np.linalg.eig(M)
        w = -np.angle(ev)
        cand = [j for j in range(2) if 1e-9 < w[j] < math.pi - 1e-9]
        j = cand[int(np.argmin([w[jj] for jj in cand]))]
        return kl, float(w[j]), V[:, j] / np.linalg.norm(V[:, j]), ph

    def run_seed(nvec, kind, seed=7):
        kl, w, xi, ph = onshell_mode(nvec)
        # walk convention e^{-i w t}: 4-frequency (-w, k), kappa_0 -> -kappa_0
        k4 = np.array([-w, kl[0], kl[1], kl[2]])
        kap = np.array([-2.0 * math.sin(w / 2.0) / c]
                       + [2.0 * math.sin(ki / 2.0) for ki in kl])
        TT = r15.tt_basis(kap)
        G = r15.gauge_block(kap)
        rng = np.random.default_rng(seed)
        if kind == "tt":
            a = TT @ np.array([1.0, 0.7])
        elif kind == "gauge":
            a = G @ np.array([0.5, 1.0, -0.3, 0.7])
        else:
            a = rng.normal(size=10) + 1j * rng.normal(size=10)
        a = a / (np.linalg.norm(a) + 1e-300)
        cf = colfac(k4, OFFSET)
        chi = np.zeros((10, N, N, N, 2), complex)
        for comp in range(10):
            chi[comp] = (a[comp] * cf[comp] * ph)[..., None] * xi[None, None, None, :]
        # quantitative floor prediction: the stored eigenmode is an exact plane
        # wave, so measured relC must equal the ORACLE symbol at the walk's own
        # (possibly off-shell-formula) k4 -- rms(C)/rms(H) with |xi_spinor|
        # common to numerator and denominator:
        #   relC_pred = sqrt(sum_nu |(K_oracle(k4) a)_nu|^2 / 4) / sqrt(|a|^2/10)
        Kw = r17.constraint_matrix_op(k4)
        relC_pred = float(np.sqrt(np.sum(np.abs(Kw @ a) ** 2) / 4.0)
                          / np.sqrt(np.sum(np.abs(a) ** 2) / 10.0))
        # rolling 3-slice buffer of STORED fields (chi spinor comp 0)
        rel = []
        Hbuf = [chi[..., 0].copy()]
        for t in range(T):
            chi = gw.geom_walk_all(chi, th0, th0, th0, th0)
            Hbuf.append(chi[..., 0].copy())
            if len(Hbuf) == 3:
                Cr = K_placed(Hbuf[0], Hbuf[1], Hbuf[2], c)
                hn = float(np.sqrt(np.mean(np.abs(Hbuf[1]) ** 2)))
                rel.append(float(np.sqrt(np.mean(np.abs(Cr) ** 2))) / (hn + 1e-300))
                Hbuf.pop(0)
        eta = np.diag([-1.0, 1.0, 1.0, 1.0])
        pred_dev = (float(abs(max(rel) - relC_pred))
                    if kind in ("tt", "gauge") else float("nan"))
        return {"w_walk": w, "w_shell": float(r15.shell_omega(kl)),
                "shell_dev": float(abs(w - r15.shell_omega(kl))),
                "kappa_null": float(abs(kap @ eta @ kap)),
                "relC_first": rel[0], "relC_max": max(rel),
                "relC_last": rel[-1],
                "relC_pred_oracle": relC_pred,
                "pred_dev": pred_dev,
                "drift": float(max(rel) - min(rel))}

    out = {"N": N, "T": T, "th0": th0, "modes": {}}
    for nvec in ((2, 0, 0), (2, 2, 2)):
        m = {}
        for kind in ("tt", "gauge", "generic"):
            m[kind] = run_seed(nvec, kind)
        out["modes"][str(nvec)] = m
    ax = out["modes"]["(2, 0, 0)"]
    ob = out["modes"]["(2, 2, 2)"]
    out["smoke_PASS"] = bool(
        ax["tt"]["relC_max"] < 1e-12 and ob["tt"]["relC_max"] < 1e-12
        and ax["gauge"]["relC_max"] < 1e-12
        and ax["generic"]["relC_max"] > 1e-3
        and ob["generic"]["relC_max"] > 1e-3
        and max(m[k]["pred_dev"] for m in out["modes"].values()
                for k in ("tt", "gauge")) < 1e-10)
    out["note_oblique_gauge"] = (
        "oblique gauge floor tracks |kappa.kappa|(w_walk) = the Trotter shell "
        "correction of the NON-PALINDROMIC 3D walk (R15 §5 reserved item; "
        "walk-core property, not a placement failure)")
    return out


# ===========================================================================
#  driver
# ===========================================================================
if __name__ == "__main__":
    print("R19 staggered-h placement: component_phase moved into real-space storage")
    print("=" * 74)
    out = {}

    out["part0_oracle_kspace"] = p0 = part0_oracle()
    print(f"[0 ORACLE k-space]  {p0['n_k']} random 3D k:  "
          f"|K@TT| = {p0['worst_KTT']:.2e}  |K@gauge| = {p0['worst_Kgauge']:.2e}")
    print(f"    rank = {p0['ranks']}  dim(ker/gauge) = {p0['dims_ker_over_gauge']}"
          f"  dist(.,TT) = {p0['worst_dist_TT']:.2e}   "
          f"-> {'PASS' if p0['PASS'] else 'FAIL'}")

    pab = parts_1_A_B()
    out.update(pab)
    p1 = pab["part1_symbol_match"]
    print(f"\n[1 REAL == ORACLE]  {pab['n_k']} lattice k x both branches (+w/-w):")
    print(f"    max |K_real - K_oracle| = {p1['max_dev_vs_oracle']:.2e}   "
          f"off-mode residual = {p1['max_offmode_residual']:.2e}   "
          f"-> {'PASS' if p1['PASS'] else 'FAIL'}")
    gA = pab["gateA"]
    print(f"[A HARD GATE]  |K_placed@TT| = {gA['worst_KTT']:.2e}   "
          f"|K_placed@gauge| = {gA['worst_Kgauge']:.2e}  (on-shell)")
    print(f"    real-valued field (h = Re) worst = {gA['realfield_worst']:.2e}"
          f"   -> {'PASS' if gA['PASS'] else 'FAIL'}")
    gB = pab["gateB"]
    print(f"[B HARD GATE]  rank = {gB['ranks']}  dim(ker/gauge) = "
          f"{gB['dims_ker_over_gauge']}  dist(.,TT) = {gB['worst_dist_TT']:.2e}"
          f"   -> {'PASS' if gB['PASS'] else 'FAIL'}")

    out["neg_controls"] = ng = part_neg()
    print("\n[NEG CONTROLS]  (each must FAIL)")
    for name in ("a_central_integer", "b_literal_yee", "c_dict_no_placement"):
        v = ng[name]
        print(f"    {name:22s}: |K@TT| = {v['worst_KTT']:.3f}  "
              f"|K@gauge| = {v['worst_Kgauge']:.3f}  "
              f"dim(ker/gauge) = {v['dims_ker_over_gauge']}  -> "
              f"{'FAILS as required' if v['FAILS_AS_REQUIRED'] else 'UNEXPECTED PASS'}")
    print(f"    teeth -> {'PASS' if ng['teeth_PASS'] else 'FAIL'}")

    out["smoke"] = sm = part_smoke()
    print(f"\n[5 SMOKE]  R14 walk kernel, N={sm['N']}, T={sm['T']}, no damping:")
    for mk, m in sm["modes"].items():
        print(f"    k = {mk}:  w_walk = {m['tt']['w_walk']:.6f}  "
              f"|w-shell| = {m['tt']['shell_dev']:.2e}  "
              f"|kap.kap| = {m['tt']['kappa_null']:.2e}")
        for kind in ("tt", "gauge", "generic"):
            r = m[kind]
            extra = (f"  oracle-pred = {r['relC_pred_oracle']:.2e} "
                     f"(dev {r['pred_dev']:.1e})"
                     if kind in ("tt", "gauge") else "")
            print(f"      {kind:7s}: relC max = {r['relC_max']:.2e}  "
                  f"last = {r['relC_last']:.2e}  drift = {r['drift']:.2e}{extra}")
    print(f"    -> smoke {'PASS' if sm['smoke_PASS'] else 'FAIL'}  "
          f"({sm['note_oblique_gauge']})")

    out["all_pass"] = bool(p0["PASS"] and p1["PASS"] and gA["PASS"]
                           and gB["PASS"] and ng["teeth_PASS"]
                           and sm["smoke_PASS"])
    print("\n" + "=" * 74)
    print(f"R19 VERDICT: {'ALL PASS' if out['all_pass'] else 'NOT ALL PASS'}"
          "  (oracle + real==oracle + gates A/B + neg teeth + smoke)")

    with open(os.path.join(DIR, "r19_results.json"), "w") as fh:
        json.dump(out, fh, indent=1,
                  default=lambda o: (o.tolist() if isinstance(o, np.ndarray)
                                     else float(o)))
    print("wrote r19_results.json")
