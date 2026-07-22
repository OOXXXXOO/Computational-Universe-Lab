"""rulespace.core — standardized machinery for inhomogeneous QCA campaigns.

Walker: massless split-step Dirac walk on the Weyl line with LOCAL coin angle
theta(x,t):   psi -> S_minus C(-theta) S_plus C(theta) psi.
Homogeneous dispersion: cos w = cos^2(th) cos k + sin^2(th)
  => local light speed  c(x) = cos theta(x).   (metric ds^2 = dt^2 - dx^2/c^2)

Coin field: second-order-in-time local update with coupling vector a:
  theta(t+1) = clip( 2 th - th_prev
                     + a0 * Lap(th)          geometric stiffness (wave term)
                     + a1 * (grad th)^2      nonlinear geometry
                     + a2 * (rho - rho_bar)  matter energy source
                     + a3 * J                matter momentum source
                     + a4 * (th - TH_REF)    restoring / "cosmological" term
                     + a5 * (th - th_prev)   damping (sign<0)
                   , TH_MIN, TH_MAX)

rho = |psi0|^2+|psi1|^2 (energy proxy), J = |psi0|^2-|psi1|^2 (momentum proxy).
"""
import numpy as np

TH_MIN, TH_MAX, TH_REF = 0.08, 1.25, 0.45
NPAR = 6
PAR_NAMES = ["Lap(th)", "(grad th)^2", "rho-mean", "J", "th-ref", "damping"]

# ---------------- walker ----------------
def coin(psi0, psi1, th):
    c, s = np.cos(th), 1j * np.sin(th)
    return c * psi0 + s * psi1, s * psi0 + c * psi1

def walker_step(psi0, psi1, th, dm=0.0):
    """dm > 0 takes the walker off the Weyl line: mass gap = dm (species knob)"""
    p0, p1 = coin(psi0, psi1, th)
    p0 = np.roll(p0, 1)                       # S_plus : comp0 -> right
    p0, p1 = coin(p0, p1, -th + dm)
    p1 = np.roll(p1, -1)                      # S_minus: comp1 -> left
    return p0, p1

def walk_matrix(k, th, dm=0.0):
    """exact one-step 2x2 operator of the homogeneous split-step walk"""
    c, s = np.cos(th), 1j * np.sin(th)
    c2, s2 = np.cos(-th + dm), 1j * np.sin(-th + dm)
    C1 = np.array([[c, s], [s, c]])
    C2 = np.array([[c2, s2], [s2, c2]])
    Sp = np.diag([np.exp(-1j * k), 1.0])
    Sm = np.diag([1.0, np.exp(1j * k)])
    return Sm @ C2 @ Sp @ C1

def branch_spinor(k0, th, dk=1e-5, dm=0.0):
    """eigen-spinor of the branch with POSITIVE group velocity at k0"""
    best = None
    ev, V = np.linalg.eig(walk_matrix(k0, th, dm))
    w = -np.angle(ev)
    for j in range(2):
        wp = -np.angle(np.linalg.eigvals(walk_matrix(k0 + dk, th, dm)))
        wm = -np.angle(np.linalg.eigvals(walk_matrix(k0 - dk, th, dm)))
        vg = (wp[np.argmin(np.abs(wp - w[j]))] - wm[np.argmin(np.abs(wm - w[j]))]) / (2 * dk)
        if best is None or vg > best[0]:
            v = V[:, j] * np.exp(-1j * np.angle(V[0, j] + 1e-30))
            best = (vg, v)
    return best[1]

def packet(N, x0, k0, sig, th=TH_REF, dm=0.0):
    """positive-velocity-branch packet on a homogeneous theta background."""
    x = np.arange(N)
    d = (x - x0 + N // 2) % N - N // 2           # centered torus distance
    g = np.exp(-d ** 2 / (4 * sig ** 2)) * np.exp(1j * k0 * x)
    sp = branch_spinor(k0, th, dm=dm)
    psi0, psi1 = sp[0] * g, sp[1] * g
    n = np.sqrt((abs(psi0) ** 2 + abs(psi1) ** 2).sum())
    return psi0 / n, psi1 / n

def rho_J(psi0, psi1):
    r = np.abs(psi0) ** 2 + np.abs(psi1) ** 2
    return r, np.abs(psi0) ** 2 - np.abs(psi1) ** 2

# ---------------- coin field ----------------
def lap(f):  return np.roll(f, 1) + np.roll(f, -1) - 2 * f
def grad(f): return 0.5 * (np.roll(f, -1) - np.roll(f, 1))

def field_terms(th, th_prev, rho, J):
    return np.stack([
        lap(th),
        grad(th) ** 2,
        rho - rho.mean(),
        J,
        th - TH_REF,
        th - th_prev,
    ])

def field_step(th, th_prev, rho, J, a):
    terms = field_terms(th, th_prev, rho, J)
    nxt = 2 * th - th_prev + np.tensordot(a, terms, axes=1)
    clipped = np.clip(nxt, TH_MIN, TH_MAX)
    sat = float((clipped != nxt).mean())
    return clipped, sat

# ---------------- coupled run ----------------
def run_coupled(a, N=256, T=600, k0=0.8, sig=10.0, x0=None, seed=0,
                record_every=1, kick=0.0, amp=1.0, dm=0.0, rho_ext=None):
    """evolve walker + dynamical coin field; returns trajectory data.
    dm: walker species mass. rho_ext: frozen external source (e.g. a heavy lump)."""
    rng = np.random.default_rng(seed)
    x0 = N // 2 if x0 is None else x0
    psi0, psi1 = packet(N, x0, k0, sig, dm=dm)
    psi0, psi1 = amp * psi0, amp * psi1          # energy-scale knob (universality test)
    th = np.full(N, TH_REF)
    if kick:
        th[N // 4] += kick                    # single-site delta: clean causal front
    th_prev = th.copy()
    sat_tot, ths, rhos, Js = 0.0, [], [], []
    for t in range(T):
        rho, J = rho_J(psi0, psi1)
        if rho_ext is not None:
            rho = rho + rho_ext
        if t % record_every == 0:
            ths.append(th.copy()); rhos.append(rho.copy()); Js.append(J.copy())
        th_new, sat = field_step(th, th_prev, rho, J, a)
        sat_tot += sat
        th_prev, th = th, th_new
        psi0, psi1 = walker_step(psi0, psi1, th, dm=dm)
        if not np.isfinite(th).all():
            return None
    return {"theta": np.array(ths), "rho": np.array(rhos), "J": np.array(Js),
            "sat": sat_tot / T, "final_var": float(np.var(th))}
