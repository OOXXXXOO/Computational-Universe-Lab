"""Explicit fp64 array adapter for frozen ordered local-shear programs."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import math
from numbers import Complex
from typing import Callable, Tuple

import numpy as np


_LOCAL_OPERATION = "local_canonical_shear"
_NEUTRAL_OPERATION = "neutral_identity"
_BACKENDS = ("numpy", "jax", "jax-cuda")


class BackendUnavailableError(RuntimeError):
    """The explicitly requested array engine cannot satisfy the contract."""


class CudaUnavailableError(BackendUnavailableError):
    """No NVIDIA CUDA device can be proven for the requested engine."""


@dataclass(frozen=True)
class LocalShearStep:
    """One inert, index-bound primitive in an ordered local program."""

    operation_id: str
    source_index: int
    destination_index: int
    offset: Tuple[int, ...]
    coefficient: complex

    def __post_init__(self) -> None:
        if self.operation_id not in (_LOCAL_OPERATION, _NEUTRAL_OPERATION):
            raise ValueError("operation_id is not an allowed local operation")
        _nonnegative_int(self.source_index, "source_index")
        _nonnegative_int(self.destination_index, "destination_index")
        if type(self.offset) is not tuple or not self.offset:
            raise TypeError("offset must be a non-empty tuple")
        for axis, coordinate in enumerate(self.offset):
            if type(coordinate) is not int:
                raise TypeError(f"offset[{axis}] must be an integer")
        if not isinstance(self.coefficient, Complex):
            raise TypeError("coefficient must be a complex scalar")
        coefficient = complex(self.coefficient)
        if not math.isfinite(coefficient.real) or not math.isfinite(
            coefficient.imag
        ):
            raise ValueError("coefficient must be finite")
        object.__setattr__(self, "coefficient", coefficient)
        if self.operation_id == _LOCAL_OPERATION:
            if self.source_index == self.destination_index:
                raise ValueError("local shear channels must differ")
            if coefficient == 0.0j:
                raise ValueError("local shear coefficient must be non-zero")
        elif coefficient != 0.0j or any(self.offset):
            raise ValueError(
                "neutral identity requires zero coefficient and zero offset"
            )


@dataclass(frozen=True)
class LocalShearProgram:
    """Inert dimensions plus primitives in their frozen execution order."""

    channel_count: int
    spatial_ndim: int
    steps: Tuple[LocalShearStep, ...]

    def __post_init__(self) -> None:
        _positive_int(self.channel_count, "channel_count")
        _positive_int(self.spatial_ndim, "spatial_ndim")
        if type(self.steps) is not tuple or not self.steps:
            raise TypeError("steps must be a non-empty tuple")
        for index, step in enumerate(self.steps):
            if type(step) is not LocalShearStep:
                raise TypeError(f"steps[{index}] must be a LocalShearStep")
            if len(step.offset) != self.spatial_ndim:
                raise ValueError(
                    f"steps[{index}].offset does not match spatial_ndim"
                )
            if step.source_index >= self.channel_count:
                raise ValueError(f"steps[{index}].source_index is out of range")
            if step.destination_index >= self.channel_count:
                raise ValueError(
                    f"steps[{index}].destination_index is out of range"
                )


@dataclass(frozen=True)
class BackendPreflight:
    """Read-only facts established before a runner is constructed."""

    backend: str
    engine: str
    x64_enabled: bool
    complex_dtype: str
    device_platforms: Tuple[str, ...]
    cuda_devices: Tuple[str, ...]


def _positive_int(value: object, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _backend_name(backend: object) -> str:
    if type(backend) is not str:
        raise TypeError("backend must be a string")
    if backend not in _BACKENDS:
        raise ValueError(
            "backend must be one of 'numpy', 'jax', or 'jax-cuda'"
        )
    return backend


def _is_cuda_device(device: object) -> bool:
    platform = str(getattr(device, "platform", "")).lower()
    kind = str(getattr(device, "device_kind", "")).lower()
    client = getattr(device, "client", None)
    platform_version = str(
        getattr(client, "platform_version", "")
    ).lower()
    return platform in {"cuda", "gpu"} and (
        "nvidia" in kind or "cuda" in platform_version
    )


def _load_jax(require_cuda: bool):
    try:
        jax = importlib.import_module("jax")
        jax.config.update("jax_enable_x64", True)
        jnp = importlib.import_module("jax.numpy")
        probe = jnp.asarray((0.0j,), dtype=jnp.complex128)
        devices = tuple(jax.devices())
    except (ImportError, ModuleNotFoundError) as exc:
        raise BackendUnavailableError(
            "the explicit JAX backend is not installed"
        ) from exc
    except Exception as exc:
        raise BackendUnavailableError(
            "the explicit JAX backend failed its fp64 probe"
        ) from exc
    if not bool(jax.config.x64_enabled):
        raise BackendUnavailableError("JAX x64 mode could not be enabled")
    if np.dtype(probe.dtype) != np.dtype(np.complex128):
        raise BackendUnavailableError("JAX complex128 probe was not preserved")
    cuda_devices = tuple(device for device in devices if _is_cuda_device(device))
    if require_cuda and not cuda_devices:
        raise CudaUnavailableError(
            "an NVIDIA CUDA device could not be proven for jax-cuda"
        )
    return jax, jnp, devices, cuda_devices


def preflight_backend(backend: str) -> BackendPreflight:
    """Establish dtype and device facts for one explicit backend."""

    selected = _backend_name(backend)
    if selected == "numpy":
        probe = np.asarray((0.0j,), dtype=np.complex128)
        if probe.dtype != np.dtype(np.complex128):
            raise BackendUnavailableError(
                "NumPy complex128 probe was not preserved"
            )
        return BackendPreflight(
            backend=selected,
            engine="numpy",
            x64_enabled=True,
            complex_dtype=probe.dtype.name,
            device_platforms=("cpu",),
            cuda_devices=(),
        )
    _, _, devices, cuda_devices = _load_jax(
        require_cuda=selected == "jax-cuda"
    )
    return BackendPreflight(
        backend=selected,
        engine="jax",
        x64_enabled=True,
        complex_dtype=np.dtype(np.complex128).name,
        device_platforms=tuple(
            sorted({str(getattr(device, "platform", "unknown")) for device in devices})
        ),
        cuda_devices=tuple(str(device) for device in cuda_devices),
    )


def _validate_state(state: object, program: LocalShearProgram) -> None:
    if not hasattr(state, "dtype") or not hasattr(state, "shape"):
        raise TypeError("state must be an array")
    try:
        dtype = np.dtype(state.dtype)  # type: ignore[attr-defined]
        shape = tuple(int(length) for length in state.shape)  # type: ignore[attr-defined]
    except (TypeError, ValueError) as exc:
        raise TypeError("state must expose a concrete dtype and shape") from exc
    if dtype != np.dtype(np.complex128):
        raise TypeError("state dtype must be complex128")
    expected_rank = program.spatial_ndim + 2
    if len(shape) != expected_rank:
        raise ValueError("state rank does not match program")
    if shape[0] <= 0 or any(length <= 0 for length in shape[2:]):
        raise ValueError("state batch and spatial axes must be positive")
    if shape[1] != program.channel_count:
        raise ValueError("state channel axis does not match program")


def _array_step(program: LocalShearProgram, state, array_module):
    result = array_module.array(state, dtype=array_module.complex128, copy=True)
    for step in program.steps:
        if step.operation_id == _NEUTRAL_OPERATION:
            continue
        source = result[:, step.source_index, ...]
        for axis, coordinate in enumerate(step.offset):
            source = array_module.roll(
                source,
                shift=-coordinate,
                axis=axis + 1,
            )
        channels = [
            result[:, channel_index, ...]
            for channel_index in range(program.channel_count)
        ]
        coefficient = array_module.asarray(
            step.coefficient,
            dtype=array_module.complex128,
        )
        channels[step.destination_index] = (
            channels[step.destination_index] + coefficient * source
        )
        result = array_module.stack(channels, axis=1)
    return result


def make_batched_local_shear_step(
    program: LocalShearProgram,
    *,
    backend: str,
) -> Callable[[object], object]:
    """Build a pure batched step for ``(batch, channel, *spatial)`` arrays."""

    if type(program) is not LocalShearProgram:
        raise TypeError("program must be a LocalShearProgram")
    selected = _backend_name(backend)
    preflight_backend(selected)
    if selected == "numpy":

        def numpy_step(state: object) -> np.ndarray:
            if type(state) is not np.ndarray:
                raise TypeError("state must be a NumPy ndarray")
            _validate_state(state, program)
            return _array_step(program, state, np)

        return numpy_step

    jax, jnp, _, cuda_devices = _load_jax(
        require_cuda=selected == "jax-cuda"
    )

    def jax_kernel(state):
        return _array_step(program, state, jnp)

    target_device = cuda_devices[0] if cuda_devices else None
    if target_device is None:
        compiled = jax.jit(jax_kernel)
    else:
        compiled = jax.jit(jax_kernel, device=target_device)

    def jax_step(state: object):
        _validate_state(state, program)
        device_state = jnp.asarray(state, dtype=jnp.complex128)
        if target_device is not None:
            device_state = jax.device_put(device_state, target_device)
        return compiled(device_state)

    return jax_step


__all__ = [
    "BackendPreflight",
    "BackendUnavailableError",
    "CudaUnavailableError",
    "LocalShearProgram",
    "LocalShearStep",
    "make_batched_local_shear_step",
    "preflight_backend",
]
