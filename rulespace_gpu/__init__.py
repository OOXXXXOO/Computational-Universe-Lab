"""Device adapters for the Projective Rule-Space Program.

Legacy modules remain available through the original package attributes, but
are imported only when requested.  This keeps isolated adapters free from the
legacy environment-selected backend during import.
"""

from importlib import import_module


__all__ = ["backend", "engine", "states", "observables"]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__():
    return sorted((*globals(), *__all__))
