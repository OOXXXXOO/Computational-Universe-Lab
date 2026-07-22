"""rulespace_gpu.observables — device-side measurements."""
import numpy as np
from . import backend as B
from . import engine
xp = B.xp


def total(x):
    return B.fscalar(xp.sum(x))

def com(rho_arr, axis, shape):
    """circular-mean center-of-mass along one axis (torus-safe)."""
    ax = B.asarray(np.arange(shape[axis]))
    n = shape[axis]
    dims = [1] * len(shape); dims[axis] = n
    axr = xp.reshape(ax, dims)
    z = xp.sum(rho_arr * xp.exp(2j * np.pi * axr / n))
    ang = B.fscalar(B.angle(z))
    return (ang / (2 * np.pi) * n) % n

def mean_k(p0, p1, axis, shape):
    """<k_axis> in Fourier space (impulse-clean observable)."""
    f0 = B.fftn(p0); f1 = B.fftn(p1)
    pk = B.real(f0) ** 2 + B.imag(f0) ** 2 + B.real(f1) ** 2 + B.imag(f1) ** 2
    kk = np.fft.fftfreq(shape[axis]) * 2 * np.pi
    dims = [1] * len(shape); dims[axis] = shape[axis]
    kr = B.asarray(kk.reshape(dims))
    num = B.fscalar(xp.sum(pk * kr)); den = B.fscalar(xp.sum(pk))
    return num / den


def poisson_solve(source, cg2, shape):
    """static field: cg2 * Lap theta = -source, on the torus (FFT, exact)."""
    S = B.fftn(source)
    lam = np.zeros(shape)
    for ax in range(len(shape)):
        k = 2 * np.pi * np.fft.fftfreq(shape[ax])
        dims = [1] * len(shape); dims[ax] = shape[ax]
        lam = lam + (2 - 2 * np.cos(k)).reshape(dims)
    lam = B.asarray(lam)
    denom = cg2 * lam
    Th = xp.where(denom > 1e-12, S / xp.where(denom > 1e-12, denom, 1.0), 0.0)
    return B.real(B.ifftn(Th))
