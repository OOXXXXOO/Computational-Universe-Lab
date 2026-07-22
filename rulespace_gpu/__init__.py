"""rulespace_gpu — device-agnostic engine for the Projective Rule-Space Program.

    from rulespace_gpu import backend as B, engine, states, observables
    print(B.NAME, B.device_info())

Backend chosen by env var RULESPACE_BACKEND in {mlx, jax, numpy, auto}.
"""
from . import backend, engine, states, observables

__all__ = ["backend", "engine", "states", "observables"]
