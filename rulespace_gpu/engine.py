"""rulespace_gpu.engine — the compute core, device-agnostic.

A 2-spinor Dirac/Weyl walk in 1, 2 or 3 spatial dimensions with a LOCAL coin
field theta(x) (emergent light speed c = cos theta) and an optional mass gap
dm, coupled to a dynamical scalar field theta via the leapfrog rule
    theta_{t+1} = 2 theta_t - theta_{t-1} + cg2 * Lap(theta) + kappa * source
with source in {rho, T00, capstone tan(theta)*T00}.

Everything here is PURE (no in-place mutation) so it JIT-compiles under jax/mlx.
"""
from . import backend as B
xp = B.xp
import math

INV2 = 1.0 / math.sqrt(2.0)


# ---------------- walker ----------------
def coin(p0, p1, th):
    c = xp.cos(th); s = 1j * xp.sin(th)
    return c * p0 + s * p1, s * p0 + c * p1

def _axis_x(p0, p1):
    up = INV2 * (p0 + p1); dn = INV2 * (p0 - p1)
    up = B.roll(up, 1, 0); dn = B.roll(dn, -1, 0)
    return INV2 * (up + dn), INV2 * (up - dn)

def _axis_y(p0, p1):
    up = INV2 * (p0 - 1j * p1); dn = INV2 * (p0 + 1j * p1)
    up = B.roll(up, 1, 1); dn = B.roll(dn, -1, 1)
    return INV2 * (up + dn), INV2 * (1j * up - 1j * dn)

def _axis_z(p0, p1):
    return B.roll(p0, 1, 2), B.roll(p1, -1, 2)

def walk_step(p0, p1, th, dm, ndim):
    """one full split-step in ndim spatial dimensions."""
    p0, p1 = _axis_x(p0, p1); p0, p1 = coin(p0, p1, th)
    if ndim >= 2:
        p0, p1 = _axis_y(p0, p1); p0, p1 = coin(p0, p1, th)
    if ndim >= 3:
        p0, p1 = _axis_z(p0, p1); p0, p1 = coin(p0, p1, th)
    if dm != 0.0:
        p0, p1 = coin(p0, p1, dm + 0.0 * th)      # broadcast mass gap
    return p0, p1


# ---------------- densities ----------------
def rho(p0, p1):
    return B.real(p0) ** 2 + B.imag(p0) ** 2 + B.real(p1) ** 2 + B.imag(p1) ** 2

def T00(p_prev, p_cur, p_next):
    """energy density = -1/2 Im[psi_t^dag (psi_{t+1}-psi_{t-1})] (species-blind)."""
    (a0, a1), (c0, c1) = p_prev, p_next
    b0, b1 = p_cur
    d0 = c0 - a0; d1 = c1 - a1
    return -0.5 * B.imag(B.conj(b0) * d0 + B.conj(b1) * d1)


# ---------------- field ----------------
def laplacian(f, ndim):
    out = -2.0 * ndim * f
    for ax in range(ndim):
        out = out + B.roll(f, 1, ax) + B.roll(f, -1, ax)
    return out

def field_step(th, th_prev, source, cg2, kappa, th_min, th_max, ndim):
    nxt = 2.0 * th - th_prev + cg2 * laplacian(th, ndim) + kappa * source
    return xp.clip(nxt, th_min, th_max)


# ---------------- coupled driver (one macro-step) ----------------
def coupled_step(state, params):
    """state = (p0,p1, p0_prev,p1_prev, th, th_prev); params = dict.
    Source = 'capstone' tan(theta)*T00 (massless-exact, r6a) / 'T00' / 'rho'.
    Pure function -> jit-able."""
    p0, p1, pp0, pp1, th, thp = state
    ndim = params["ndim"]; dm = params["dm"]
    n0, n1 = walk_step(p0, p1, th, dm, ndim)
    if params["source"] == "T00":
        src = T00((pp0, pp1), (p0, p1), (n0, n1))
    elif params["source"] == "capstone":
        src = xp.tan(th) * T00((pp0, pp1), (p0, p1), (n0, n1))
    else:
        src = rho(p0, p1)
    th_new = field_step(th, thp, src, params["cg2"], params["kappa"],
                        params["th_min"], params["th_max"], ndim)
    return (n0, n1, p0, p1, th_new, th)


def make_stepper(params):
    """returns a (possibly jit-compiled) one-macro-step function."""
    def step(state):
        return coupled_step(state, params)
    return B.jit(step) if hasattr(B, "jit") else step
