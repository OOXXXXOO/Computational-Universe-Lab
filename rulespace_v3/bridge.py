"""Deterministic full-state realspace/Fourier bridge instrumentation."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Literal

import numpy as np

from .dynamics import (
    VerifiedTransition,
    _reverify_verified_transition,
    transition_symbol,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    VerifiedFactory,
    _reverify_verified_factory,
    apply_factory_step,
    factory_support_offsets,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
)
from .fp64 import frobenius_sqrt_upper
from .grids import (
    BridgeKGridManifest,
    bridge_grid_payload,
    build_bridge_grid_manifest,
    verify_bridge_grid_manifest,
)
from .prestructure import (
    VerifiedPrestructureAuthority,
    _reverify_verified_prestructure_authority,
)


BRIDGE_SPEC_SCHEMA_VERSION = "v3m0.full-state-bridge-spec.v1"
BRIDGE_AUDIT_SCHEMA_VERSION = "v3m0.full-state-bridge-audit.v1"
BRIDGE_KIND: Literal["full-state"] = "full-state"
BRIDGE_MACRO_STEPS = (1, 2, 4)
BRIDGE_TOLERANCE = 1e-12
TRIAL_GENERATION_ID: Literal["canonical-or-sha256-dense-v1"] = (
    "canonical-or-sha256-dense-v1"
)
TRIAL_DOMAIN_SEPARATOR: Literal["v3m0-full-state-bridge-trials-v1"] = (
    "v3m0-full-state-bridge-trials-v1"
)
TRIAL_GRAM_GATE_METHOD_ID: Literal["outward-frobenius-dominates-spectral-v1"] = (
    "outward-frobenius-dominates-spectral-v1"
)
BRIDGE_MAX_K_POINTS = 64
BRIDGE_MAX_COMPLEX_ENTRIES = 16_777_216
BRIDGE_MAX_EXECUTOR_WORK = 2_000_000_000
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _finite_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


def _grid_record(grid: BridgeKGridManifest) -> dict[str, object]:
    return {
        **bridge_grid_payload(grid),
        "bridge_grid_sha": grid.bridge_grid_sha,
    }


@dataclass(frozen=True)
class FullStateBridgeSpec:
    bridge_spec_schema_version: str
    factory_sha: str
    parent_freeze_sha: str
    prestructure_authority_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    bridge_grid: BridgeKGridManifest
    macro_steps: tuple[int, ...]
    state_trial_vectors: FrozenComplexTensor
    trial_generation_id: Literal["canonical-or-sha256-dense-v1"]
    trial_seed_sha: str
    trial_domain_separator: Literal["v3m0-full-state-bridge-trials-v1"]
    trial_gram_frobenius_upper: float
    trial_gram_gate_method_id: Literal["outward-frobenius-dominates-spectral-v1"]
    bridge_tolerance: float
    bridge_spec_sha: str

    def __post_init__(self) -> None:
        _text(
            self.bridge_spec_schema_version,
            "bridge_spec_schema_version",
        )
        for field in (
            "factory_sha",
            "parent_freeze_sha",
            "prestructure_authority_sha",
            "trial_seed_sha",
            "bridge_spec_sha",
        ):
            _sha(getattr(self, field), field)
        _text(self.state_schema_id, "state_schema_id")
        if type(self.channel_order) is not tuple or not self.channel_order:
            raise ValueError("channel_order must be a non-empty tuple")
        if len(set(self.channel_order)) != len(self.channel_order):
            raise ValueError("channel_order contains duplicates")
        if type(self.spatial_shape) is not tuple or not self.spatial_shape:
            raise ValueError("spatial_shape must be a non-empty tuple")
        for index, item in enumerate(self.spatial_shape):
            _positive_int(item, f"spatial_shape[{index}]")
        if not isinstance(self.bridge_grid, BridgeKGridManifest):
            raise TypeError("bridge_grid has the wrong strict grid type")
        if self.macro_steps != BRIDGE_MACRO_STEPS:
            raise ValueError("bridge macro_steps are not frozen")
        if not isinstance(self.state_trial_vectors, FrozenComplexTensor):
            raise TypeError("state_trial_vectors must be a FrozenComplexTensor")
        if self.trial_generation_id != TRIAL_GENERATION_ID:
            raise ValueError("trial_generation_id is not frozen")
        if self.trial_domain_separator != TRIAL_DOMAIN_SEPARATOR:
            raise ValueError("trial_domain_separator is not frozen")
        gram = _finite_float(
            self.trial_gram_frobenius_upper,
            "trial_gram_frobenius_upper",
        )
        if gram < 0.0 or gram > BRIDGE_TOLERANCE:
            raise ValueError("trial Gram bound exceeds the frozen gate")
        if self.trial_gram_gate_method_id != TRIAL_GRAM_GATE_METHOD_ID:
            raise ValueError("trial Gram gate method is not frozen")
        tolerance = _finite_float(
            self.bridge_tolerance,
            "bridge_tolerance",
        )
        if tolerance != BRIDGE_TOLERANCE:
            raise ValueError("bridge_tolerance is not frozen")


@dataclass(frozen=True)
class BridgeCaseAudit:
    reciprocal_index: tuple[int, ...]
    macro_steps: int
    trial_index: int
    raw_abs_residual: float
    scale: float
    normalized_residual: float

    def __post_init__(self) -> None:
        if type(self.reciprocal_index) is not tuple:
            raise TypeError("reciprocal_index must be a tuple")
        for index, item in enumerate(self.reciprocal_index):
            if type(item) is not int or item < 0:
                raise ValueError(
                    f"reciprocal_index[{index}] must be a non-negative int"
                )
        _positive_int(self.macro_steps, "macro_steps")
        if type(self.trial_index) is not int or self.trial_index < 0:
            raise ValueError("trial_index must be a non-negative int")
        raw = _finite_float(self.raw_abs_residual, "raw_abs_residual")
        scale = _finite_float(self.scale, "scale")
        normalized = _finite_float(
            self.normalized_residual,
            "normalized_residual",
        )
        if raw < 0.0 or scale < 1.0 or normalized < 0.0:
            raise ValueError("bridge residual wires are outside their domain")


@dataclass(frozen=True)
class BridgeAudit:
    bridge_schema_version: str
    bridge_kind: Literal["full-state"]
    factory_sha: str
    transition_sha: str
    bridge_spec_sha: str
    cases: tuple[BridgeCaseAudit, ...]
    raw_abs_max: float
    normalized_max: float
    bridge_sha: str

    def __post_init__(self) -> None:
        _text(self.bridge_schema_version, "bridge_schema_version")
        if self.bridge_kind != BRIDGE_KIND:
            raise ValueError("bridge_kind is not full-state")
        for field in (
            "factory_sha",
            "transition_sha",
            "bridge_spec_sha",
            "bridge_sha",
        ):
            _sha(getattr(self, field), field)
        if type(self.cases) is not tuple or not self.cases:
            raise ValueError("cases must be a non-empty tuple")
        if not all(isinstance(item, BridgeCaseAudit) for item in self.cases):
            raise TypeError("cases must contain BridgeCaseAudit records")
        raw = _finite_float(self.raw_abs_max, "raw_abs_max")
        normalized = _finite_float(self.normalized_max, "normalized_max")
        if raw < 0.0 or normalized < 0.0:
            raise ValueError("bridge maxima must be non-negative")


def full_state_bridge_spec_payload(
    spec: FullStateBridgeSpec,
) -> dict[str, object]:
    if not isinstance(spec, FullStateBridgeSpec):
        raise TypeError("spec must be a FullStateBridgeSpec")
    return {
        "bridge_spec_schema_version": spec.bridge_spec_schema_version,
        "factory_sha": spec.factory_sha,
        "parent_freeze_sha": spec.parent_freeze_sha,
        "prestructure_authority_sha": spec.prestructure_authority_sha,
        "state_schema_id": spec.state_schema_id,
        "channel_order": list(spec.channel_order),
        "spatial_shape": list(spec.spatial_shape),
        "bridge_grid": _grid_record(spec.bridge_grid),
        "macro_steps": list(spec.macro_steps),
        "state_trial_vectors": _tensor_record(spec.state_trial_vectors),
        "trial_generation_id": spec.trial_generation_id,
        "trial_seed_sha": spec.trial_seed_sha,
        "trial_domain_separator": spec.trial_domain_separator,
        "trial_gram_frobenius_upper": (spec.trial_gram_frobenius_upper),
        "trial_gram_gate_method_id": spec.trial_gram_gate_method_id,
        "bridge_tolerance": spec.bridge_tolerance,
    }


def _case_payload(case: BridgeCaseAudit) -> dict[str, object]:
    if not isinstance(case, BridgeCaseAudit):
        raise TypeError("case must be a BridgeCaseAudit")
    return {
        "reciprocal_index": list(case.reciprocal_index),
        "macro_steps": case.macro_steps,
        "trial_index": case.trial_index,
        "raw_abs_residual": case.raw_abs_residual,
        "scale": case.scale,
        "normalized_residual": case.normalized_residual,
    }


def bridge_audit_payload(audit: BridgeAudit) -> dict[str, object]:
    if not isinstance(audit, BridgeAudit):
        raise TypeError("audit must be a BridgeAudit")
    return {
        "bridge_schema_version": audit.bridge_schema_version,
        "bridge_kind": audit.bridge_kind,
        "factory_sha": audit.factory_sha,
        "transition_sha": audit.transition_sha,
        "bridge_spec_sha": audit.bridge_spec_sha,
        "cases": [_case_payload(item) for item in audit.cases],
        "raw_abs_max": audit.raw_abs_max,
        "normalized_max": audit.normalized_max,
    }


def _bind_factory_authority(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> tuple[object, object]:
    factory_view = _reverify_verified_factory(factory)
    authority_view = _reverify_verified_prestructure_authority(authority)
    if factory is not authority_view.factory:
        raise ValueError("bridge factory is not authority-bound")
    if factory_view.factory.factory_sha != authority_view.authority.factory_sha:
        raise ValueError("bridge factory SHA mismatch")
    return factory_view, authority_view


def _signed_support(
    factory: VerifiedFactory,
) -> tuple[tuple[int, ...], ...]:
    stencil = factory_support_offsets(factory, 1)
    return tuple(
        sorted({tuple(-coordinate for coordinate in offset) for offset in stencil})
    )


def _trial_seed(
    factory_sha: str,
    parent_freeze_sha: str,
) -> str:
    return canonical_sha(
        {
            "trial_seed_schema_version": "v3m0.bridge-trial-seed.v1",
            "factory_sha": factory_sha,
            "parent_freeze_sha": parent_freeze_sha,
            "domain_separator": TRIAL_DOMAIN_SEPARATOR,
        }
    )


def _odd_dyadic_component(
    seed: bytes,
    counter: int,
    *,
    _sha256=hashlib.sha256,
    _domain_bytes=TRIAL_DOMAIN_SEPARATOR.encode("ascii"),
    _int_from_bytes=int.from_bytes,
    _float=float,
    _ldexp=math.ldexp,
) -> float:
    digest = _sha256(
        seed + _domain_bytes + counter.to_bytes(8, "big", signed=False)
    ).digest()
    word = _int_from_bytes(digest[:8], "big", signed=False)
    sign = -1.0 if (word >> 63) else 1.0
    odd = (word & ((1 << 52) - 1)) | 1
    return _ldexp(sign * _float(odd), -51)


def _dense_seed_matrix(state_count: int, seed_sha: str) -> np.ndarray:
    seed = bytes.fromhex(seed_sha)
    result = np.empty((state_count, 32), dtype=np.complex128)
    counter = 0
    for row in range(state_count):
        for column in range(32):
            real = _odd_dyadic_component(seed, counter)
            counter += 1
            imaginary = _odd_dyadic_component(seed, counter)
            counter += 1
            result[row, column] = complex(real, imaginary)
    return result


def _scalar_householder_thin_q(matrix: np.ndarray) -> np.ndarray:
    if type(matrix) is not np.ndarray:
        raise TypeError("matrix must be a NumPy ndarray")
    if matrix.dtype != np.dtype(np.complex128):
        raise TypeError("matrix dtype must be complex128")
    row_count, column_count = matrix.shape
    if row_count < column_count or column_count != 32:
        raise ValueError("dense bridge seed must have shape (n>=32,32)")
    transformed = matrix.copy()
    reflectors: list[tuple[int, np.ndarray, float]] = []
    for column in range(column_count):
        vector = transformed[column:, column].copy()
        norm_squared = 0.0
        for value in vector:
            norm_squared += float(value.real) * float(value.real) + float(
                value.imag
            ) * float(value.imag)
        norm = math.sqrt(norm_squared)
        if norm == 0.0:
            raise ValueError("SHA256 dense seed lost full column rank")
        first = complex(vector[0])
        first_abs = abs(first)
        phase = (first / first_abs) if first_abs != 0.0 else (1.0 + 0.0j)
        alpha = -phase * norm
        vector[0] -= alpha
        denominator = 0.0
        for value in vector:
            denominator += float(value.real) * float(value.real) + float(
                value.imag
            ) * float(value.imag)
        if denominator == 0.0:
            raise ValueError("Householder reflector is singular")
        beta = 2.0 / denominator
        for target_column in range(column, column_count):
            inner = 0.0 + 0.0j
            for row, value in enumerate(vector):
                inner += (
                    value.conjugate()
                    * transformed[
                        column + row,
                        target_column,
                    ]
                )
            factor = beta * inner
            for row, value in enumerate(vector):
                transformed[column + row, target_column] -= value * factor
        reflectors.append((column, vector, beta))

    q_columns = np.zeros(
        (row_count, column_count),
        dtype=np.complex128,
    )
    for index in range(column_count):
        q_columns[index, index] = 1.0 + 0.0j
    for column, vector, beta in reversed(reflectors):
        for target_column in range(column_count):
            inner = 0.0 + 0.0j
            for row, value in enumerate(vector):
                inner += (
                    value.conjugate()
                    * q_columns[
                        column + row,
                        target_column,
                    ]
                )
            factor = beta * inner
            for row, value in enumerate(vector):
                q_columns[column + row, target_column] -= value * factor

    for column in range(column_count):
        first_row = next(
            (row for row in range(row_count) if q_columns[row, column] != 0.0),
            None,
        )
        if first_row is None:
            raise ValueError("Householder Q contains an empty column")
        first = complex(q_columns[first_row, column])
        multiplier = (first / abs(first)).conjugate()
        for row in range(row_count):
            q_columns[row, column] *= multiplier
        q_columns[first_row, column] = complex(
            abs(q_columns[first_row, column]),
            0.0,
        )
    return q_columns


def _exact_trial_gram_upper(trials: np.ndarray) -> float:
    row_count, state_count = trials.shape
    total = Fraction(0, 1)
    for first in range(row_count):
        for second in range(row_count):
            real = Fraction(0, 1)
            imaginary = Fraction(0, 1)
            for state in range(state_count):
                left = complex(trials[first, state])
                right = complex(trials[second, state])
                left_real = Fraction.from_float(float(left.real))
                left_imag = Fraction.from_float(float(left.imag))
                right_real = Fraction.from_float(float(right.real))
                right_imag = Fraction.from_float(float(right.imag))
                real += left_real * right_real + left_imag * right_imag
                imaginary += left_imag * right_real - left_real * right_imag
            if first == second:
                real -= 1
            total += real * real + imaginary * imaginary
    return frobenius_sqrt_upper(total)


def generate_bridge_trial_vectors(
    state_count: int,
    trial_seed_sha: str,
) -> tuple[FrozenComplexTensor, float]:
    """Generate identity or deterministic scalar-Householder trial rows."""

    count = _positive_int(state_count, "state_count")
    _sha(trial_seed_sha, "trial_seed_sha")
    if count <= 32:
        values = np.eye(count, dtype=np.complex128)
        return freeze_complex_tensor(values), 0.0
    seed_matrix = _dense_seed_matrix(count, trial_seed_sha)
    q_columns = _scalar_householder_thin_q(seed_matrix)
    trials = np.ascontiguousarray(q_columns.conjugate().T)
    upper = _exact_trial_gram_upper(trials)
    if upper > BRIDGE_TOLERANCE:
        raise ValueError("dense bridge trial Gram gate failed")
    return freeze_complex_tensor(trials), upper


def _preflight(
    *,
    k_count: int,
    trial_count: int,
    state_count: int,
    spatial_shape: tuple[int, ...],
    primitive_count: int,
) -> None:
    if k_count > BRIDGE_MAX_K_POINTS:
        raise ValueError("bridge k-point cap exceeded")
    if trial_count * state_count > BRIDGE_MAX_COMPLEX_ENTRIES:
        raise ValueError("bridge trial tensor entry cap exceeded")
    volume = math.prod(spatial_shape)
    work = k_count * trial_count * max(BRIDGE_MACRO_STEPS) * volume * primitive_count
    if work > BRIDGE_MAX_EXECUTOR_WORK:
        raise ValueError("bridge executor work cap exceeded")


def _expected_spec(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> FullStateBridgeSpec:
    factory_view, authority_view = _bind_factory_authority(
        factory,
        authority,
    )
    payload = factory_view.factory
    signed_support = _signed_support(factory)
    grid = build_bridge_grid_manifest(
        payload.state_shape[1:],
        signed_support,
    )
    state_count = len(payload.channel_order)
    trial_count = min(state_count, 32)
    _preflight(
        k_count=len(grid.reciprocal_indices),
        trial_count=trial_count,
        state_count=state_count,
        spatial_shape=payload.state_shape[1:],
        primitive_count=len(payload.primitives),
    )
    parent_sha = authority_view.authority.parent_freeze.parent_freeze_sha
    trial_seed_sha = _trial_seed(
        payload.factory_sha,
        parent_sha,
    )
    trials, gram_upper = generate_bridge_trial_vectors(
        state_count,
        trial_seed_sha,
    )
    provisional = FullStateBridgeSpec(
        bridge_spec_schema_version=BRIDGE_SPEC_SCHEMA_VERSION,
        factory_sha=payload.factory_sha,
        parent_freeze_sha=parent_sha,
        prestructure_authority_sha=(authority_view.authority.authority_sha),
        state_schema_id=payload.state_schema_id,
        channel_order=payload.channel_order,
        spatial_shape=payload.state_shape[1:],
        bridge_grid=grid,
        macro_steps=BRIDGE_MACRO_STEPS,
        state_trial_vectors=trials,
        trial_generation_id=TRIAL_GENERATION_ID,
        trial_seed_sha=trial_seed_sha,
        trial_domain_separator=TRIAL_DOMAIN_SEPARATOR,
        trial_gram_frobenius_upper=gram_upper,
        trial_gram_gate_method_id=TRIAL_GRAM_GATE_METHOD_ID,
        bridge_tolerance=BRIDGE_TOLERANCE,
        bridge_spec_sha="0" * 64,
    )
    return replace(
        provisional,
        bridge_spec_sha=canonical_sha(full_state_bridge_spec_payload(provisional)),
    )


def build_full_state_bridge_spec(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> FullStateBridgeSpec:
    """Build the unique support/grid/trial bridge spec."""

    return _expected_spec(factory, authority)


def verify_full_state_bridge_spec(
    spec: FullStateBridgeSpec,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> FullStateBridgeSpec:
    if type(spec) is not FullStateBridgeSpec:
        raise TypeError("spec must be a FullStateBridgeSpec")
    if spec.bridge_spec_schema_version != BRIDGE_SPEC_SCHEMA_VERSION:
        raise ValueError("unexpected bridge spec schema")
    if spec.bridge_spec_sha != canonical_sha(full_state_bridge_spec_payload(spec)):
        raise ValueError("bridge_spec_sha does not match complete body")
    verify_bridge_grid_manifest(
        spec.bridge_grid,
        spec.spatial_shape,
        _signed_support(factory),
    )
    expected = _expected_spec(factory, authority)
    if spec.bridge_spec_sha != expected.bridge_spec_sha:
        raise ValueError("bridge spec is not the unique reconstruction")
    return spec


def _plane_wave(
    vector: np.ndarray,
    reciprocal_index: tuple[int, ...],
    spatial_shape: tuple[int, ...],
) -> np.ndarray:
    volume = math.prod(spatial_shape)
    phase = np.ones(spatial_shape, dtype=np.complex128)
    for axis, (index, length) in enumerate(zip(reciprocal_index, spatial_shape)):
        axis_argument = (
            2.0
            * np.pi
            * float(index)
            / float(length)
            * np.arange(length, dtype=np.float64)
        )
        axis_phase = np.exp(np.complex128(1.0j) * axis_argument)
        reshape = [1] * len(spatial_shape)
        reshape[axis] = length
        phase *= axis_phase.reshape(tuple(reshape))
    normalization = np.float64(1.0 / math.sqrt(volume))
    return (
        vector.reshape((vector.shape[0],) + (1,) * len(spatial_shape))
        * phase
        * normalization
    ).astype(np.complex128, copy=False)


def _readback_plane_wave(
    field: np.ndarray,
    reciprocal_index: tuple[int, ...],
    spatial_shape: tuple[int, ...],
) -> np.ndarray:
    """Independent exp(-ikx)/sqrt(V) C-order full-volume readback."""

    if field.shape[1:] != spatial_shape:
        raise ValueError("readback field spatial shape mismatch")
    phase = np.ones(spatial_shape, dtype=np.complex128)
    for axis, (index, length) in enumerate(zip(reciprocal_index, spatial_shape)):
        axis_argument = (
            -2.0
            * np.pi
            * float(index)
            / float(length)
            * np.arange(length, dtype=np.float64)
        )
        axis_phase = np.exp(np.complex128(1.0j) * axis_argument)
        reshape = [1] * len(spatial_shape)
        reshape[axis] = length
        phase *= axis_phase.reshape(tuple(reshape))
    normalization = np.float64(1.0 / math.sqrt(math.prod(spatial_shape)))
    result = np.zeros(field.shape[0], dtype=np.complex128)
    for channel in range(field.shape[0]):
        result[channel] = (
            np.sum(field[channel] * phase, dtype=np.complex128) * normalization
        )
    return result


def _expected_audit(
    transition: VerifiedTransition,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    spec: FullStateBridgeSpec,
) -> BridgeAudit:
    verified_spec = verify_full_state_bridge_spec(
        spec,
        factory,
        authority,
    )
    transition_authority = _reverify_verified_transition(transition)
    if (
        transition_authority.factory is not factory
        or transition_authority.prestructure is not authority
    ):
        raise ValueError("transition is not bound to bridge inputs")
    raw_transition = transition_authority.transition
    if raw_transition.factory_sha != verified_spec.factory_sha:
        raise ValueError("transition factory SHA does not match bridge spec")
    if raw_transition.transition_sha != transition.transition.transition_sha:
        raise ValueError("transition authority mismatch")
    trials = frozen_tensor_array(verified_spec.state_trial_vectors)
    cases: list[BridgeCaseAudit] = []
    for reciprocal_index in verified_spec.bridge_grid.reciprocal_indices:
        momentum = np.asarray(
            tuple(
                2.0 * np.pi * float(index) / float(length)
                for index, length in zip(
                    reciprocal_index,
                    verified_spec.spatial_shape,
                )
            ),
            dtype=np.float64,
        )
        symbol = transition_symbol(transition, momentum)
        for steps in verified_spec.macro_steps:
            for trial_index, vector in enumerate(trials):
                initial = _plane_wave(
                    vector,
                    reciprocal_index,
                    verified_spec.spatial_shape,
                )
                initial_readback = _readback_plane_wave(
                    initial,
                    reciprocal_index,
                    verified_spec.spatial_shape,
                )
                initial_readback_error = float(
                    np.linalg.norm(initial_readback - vector)
                )
                if initial_readback_error > verified_spec.bridge_tolerance:
                    raise ValueError("bridge lift/readback convention is inconsistent")
                executor = initial.copy()
                for _ in range(steps):
                    executor = apply_factory_step(factory, executor)
                symbolic_vector = vector.copy()
                for _ in range(steps):
                    symbolic_vector = symbol @ symbolic_vector
                symbolic = _plane_wave(
                    symbolic_vector,
                    reciprocal_index,
                    verified_spec.spatial_shape,
                )
                raw = float(
                    np.linalg.norm((executor - symbolic).reshape(-1, order="C"))
                )
                executor_norm = float(np.linalg.norm(executor.reshape(-1, order="C")))
                symbolic_norm = float(np.linalg.norm(symbolic.reshape(-1, order="C")))
                scale = float(max(1.0, executor_norm, symbolic_norm))
                normalized = float(raw / scale)
                readback = _readback_plane_wave(
                    executor,
                    reciprocal_index,
                    verified_spec.spatial_shape,
                )
                readback_raw = float(np.linalg.norm(readback - symbolic_vector))
                readback_scale = float(
                    max(
                        1.0,
                        np.linalg.norm(readback),
                        np.linalg.norm(symbolic_vector),
                    )
                )
                if readback_raw / readback_scale > max(
                    normalized, verified_spec.bridge_tolerance
                ):
                    raise ValueError("bridge executor readback disagrees with symbol")
                cases.append(
                    BridgeCaseAudit(
                        reciprocal_index=reciprocal_index,
                        macro_steps=steps,
                        trial_index=trial_index,
                        raw_abs_residual=raw,
                        scale=scale,
                        normalized_residual=normalized,
                    )
                )
    raw_max = float(max(item.raw_abs_residual for item in cases))
    normalized_max = float(max(item.normalized_residual for item in cases))
    provisional = BridgeAudit(
        bridge_schema_version=BRIDGE_AUDIT_SCHEMA_VERSION,
        bridge_kind=BRIDGE_KIND,
        factory_sha=verified_spec.factory_sha,
        transition_sha=raw_transition.transition_sha,
        bridge_spec_sha=verified_spec.bridge_spec_sha,
        cases=tuple(cases),
        raw_abs_max=raw_max,
        normalized_max=normalized_max,
        bridge_sha="0" * 64,
    )
    return replace(
        provisional,
        bridge_sha=canonical_sha(bridge_audit_payload(provisional)),
    )


def audit_full_state_bridge(
    transition: VerifiedTransition,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    spec: FullStateBridgeSpec,
) -> BridgeAudit:
    """Run every frozen ``grid × steps × trials`` realspace bridge case."""

    return _expected_audit(transition, factory, authority, spec)


def verify_full_state_bridge_audit(
    audit: BridgeAudit,
    transition: VerifiedTransition,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    spec: FullStateBridgeSpec,
) -> BridgeAudit:
    if type(audit) is not BridgeAudit:
        raise TypeError("audit must be a BridgeAudit")
    if audit.bridge_schema_version != BRIDGE_AUDIT_SCHEMA_VERSION:
        raise ValueError("unexpected bridge audit schema")
    if audit.bridge_sha != canonical_sha(bridge_audit_payload(audit)):
        raise ValueError("bridge_sha does not match complete body")
    expected = _expected_audit(
        transition,
        factory,
        authority,
        spec,
    )
    if audit.bridge_sha != expected.bridge_sha:
        raise ValueError("bridge audit does not match executor replay")
    return audit


__all__ = [
    "BRIDGE_AUDIT_SCHEMA_VERSION",
    "BRIDGE_KIND",
    "BRIDGE_MACRO_STEPS",
    "BRIDGE_SPEC_SCHEMA_VERSION",
    "BRIDGE_TOLERANCE",
    "TRIAL_DOMAIN_SEPARATOR",
    "TRIAL_GENERATION_ID",
    "TRIAL_GRAM_GATE_METHOD_ID",
    "BridgeAudit",
    "BridgeCaseAudit",
    "FullStateBridgeSpec",
    "audit_full_state_bridge",
    "bridge_audit_payload",
    "build_full_state_bridge_spec",
    "full_state_bridge_spec_payload",
    "generate_bridge_trial_vectors",
    "verify_full_state_bridge_audit",
    "verify_full_state_bridge_spec",
]
