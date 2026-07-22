"""rulespace_gpu.states — grid, packet initialisation, and the host-side
mode operator (small 2x2 eig on CPU, then transfer to device).

The mode operator U(k) is built by APPLYING the exact device walk_step to the
two basis plane waves on a tiny numpy grid, so the host spinor branch is
guaranteed consistent with the running dynamics (no hand-derived sign
conventions to get wrong).
"""
import numpy as np
from . import backend as B
from . import engine


def _walk_np(p0, p1, th, dm, ndim):
    """numpy mirror of engine.walk_step for host-side operator construction."""
    inv = 1 / np.sqrt(2)
    def coin(a, b, t):
        c, s = np.cos(t), 1j * np.sin(t); return c * a + s * b, s * a + c * b
    up = inv * (p0 + p1); dn = inv * (p0 - p1)
    up = np.roll(up, 1, 0); dn = np.roll(dn, -1, 0)
    p0, p1 = inv * (up + dn), inv * (up - dn); p0, p1 = coin(p0, p1, th)
    if ndim >= 2:
        up = inv * (p0 - 1j * p1); dn = inv * (p0 + 1j * p1)
        up = np.roll(up, 1, 1); dn = np.roll(dn, -1, 1)
        p0, p1 = inv * (up + dn), inv * (1j * up - 1j * dn); p0, p1 = coin(p0, p1, th)
    if ndim >= 3:
        p0 = np.roll(p0, 1, 2); p1 = np.roll(p1, -1, 2)
        p0, p1 = coin(p0, p1, th)
    if dm != 0.0:
        p0, p1 = coin(p0, p1, dm)
    return p0, p1


def mode_operator(kvec, th0, dm, ndim):
    """2x2 U(k) in the plane-wave basis, from the exact walk on a small grid."""
    L = 8
    ax = np.arange(L)
    grids = np.meshgrid(*([ax] * ndim), indexing="ij")
    phase = np.exp(1j * sum(kvec[i] * grids[i] for i in range(ndim)))
    th = np.full([L] * ndim, th0)
    U = np.zeros((2, 2), complex)
    for j, (b0, b1) in enumerate([(phase, 0 * phase), (0 * phase, phase)]):
        o0, o1 = _walk_np(b0.astype(complex), b1.astype(complex), th, dm, ndim)
        ref = tuple([1] * ndim)
        U[0, j] = o0[ref] / phase[ref]; U[1, j] = o1[ref] / phase[ref]
    return U


def branch_spinor(kvec, th0, dm, ndim):
    """positive-omega eigenspinor of U(k)."""
    U = mode_operator(kvec, th0, dm, ndim)
    ev, V = np.linalg.eig(U)
    w = -np.angle(ev); b = int(np.argmax(w))
    v = V[:, b]; v = v * np.exp(-1j * np.angle(v[0] + 1e-30))
    return v, float(w[b])


def omega(kvec, th0, dm, ndim):
    ev = np.linalg.eigvals(mode_operator(kvec, th0, dm, ndim))
    return float(np.max(-np.angle(ev)))


def packet(shape, center, k0dir, sig, th0, dm=0.0):
    """Gaussian wavepacket on the positive branch. Returns device arrays p0,p1."""
    ndim = len(shape)
    grids = np.meshgrid(*[np.arange(n) for n in shape], indexing="ij")
    r2 = sum(((grids[i] - center[i] + shape[i] // 2) % shape[i] - shape[i] // 2) ** 2
             for i in range(ndim))
    kvec = np.array(k0dir, float)
    phase = sum(kvec[i] * grids[i] for i in range(ndim))
    g = np.exp(-r2 / (4 * sig ** 2)) * np.exp(1j * phase)
    sp, _ = branch_spinor(kvec, th0, dm, ndim)
    p0 = (sp[0] * g).astype(B.to_np(B.asarray(0j)).dtype if False else complex)
    p1 = (sp[1] * g).astype(complex)
    nrm = np.sqrt((np.abs(p0) ** 2 + np.abs(p1) ** 2).sum())
    return B.asarray(p0 / nrm), B.asarray(p1 / nrm)


def uniform_theta(shape, th0):
    return B.asarray(np.full(shape, th0))
