"""rulespace_gpu.backend — one array API, four devices.

Pick the backend with the env var RULESPACE_BACKEND:
    mlx    -> Apple Silicon GPU        (pip install mlx)          [macOS M-series]
    jax    -> CUDA / Metal / CPU       (pip install "jax[cuda12]" or jax-metal)
    numpy  -> CPU reference            (always available)
    auto   -> first of mlx, jax, numpy that imports   (default)

All three expose a nearly-identical NumPy-like API; this shim smooths over the
few differences (conj/real/imag/angle names, lazy-eval sync, host transfer) so
the physics code (engine.py) is written once and runs on any device.
"""
import os
import numpy as _np

_WANT = os.environ.get("RULESPACE_BACKEND", "auto").lower()


def _load(name):
    if name == "numpy":
        import numpy as m; return m, "numpy"
    if name == "jax":
        import jax  # noqa
        import jax.numpy as m
        from jax import config
        config.update("jax_enable_x64", True)   # physics wants float64/complex128
        return m, "jax"
    if name == "mlx":
        import mlx.core as m; return m, "mlx"
    raise ValueError(f"unknown backend {name!r}")


if _WANT == "auto":
    for _cand in ("mlx", "jax", "numpy"):
        try:
            xp, NAME = _load(_cand); break
        except Exception:
            continue
else:
    xp, NAME = _load(_WANT)

# complex/float dtypes per backend
if NAME == "mlx":
    CIN, FIN = xp.complex64, xp.float32       # MLX is fp32-native
else:
    CIN, FIN = xp.complex128, xp.float64


# ---- wrappers over the few divergent ops ----
def asarray(a, dtype=None):
    return xp.array(_np.asarray(a)) if NAME == "mlx" else xp.asarray(a, dtype=dtype)

def conj(x):
    return xp.conjugate(x) if NAME == "mlx" else xp.conj(x)

def real(x): return xp.real(x)
def imag(x): return xp.imag(x)

def angle(x):
    return xp.arctan2(imag(x), real(x))       # uniform: avoids missing xp.angle

def roll(x, shift, axis):
    return xp.roll(x, shift, axis)          # positional: MLX roll is positional-only

def fftn(x):  return xp.fft.fftn(x)
def ifftn(x): return xp.fft.ifftn(x)

def fftfreq(n):
    return asarray(_np.fft.fftfreq(n))        # static; build on host, transfer once

def to_np(x):
    if NAME == "mlx":
        xp.eval(x); return _np.array(x)
    return _np.asarray(x)

def sync(*arrs):
    """force lazy backends to finish (for timing / before host reads)."""
    if NAME == "mlx":
        xp.eval(*arrs)
    elif NAME == "jax":
        for a in arrs:
            a.block_until_ready()

def fscalar(x):
    return float(to_np(x))

def device_info():
    if NAME == "jax":
        import jax; return str(jax.devices())
    if NAME == "mlx":
        return "mlx:" + str(xp.default_device())
    return "cpu:numpy"

def jit(fn):
    """compile a pure step function on the current backend (no-op on numpy)."""
    if NAME == "jax":
        import jax; return jax.jit(fn)
    if NAME == "mlx":
        return xp.compile(fn)
    return fn
