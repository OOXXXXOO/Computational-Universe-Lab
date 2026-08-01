"""Isolated, authority-neutral local preflight for a 10D C19 refreeze.

This module is deliberately disconnected from Parent, thresholds, response
authority, and issuance.  It only constructs and checks a candidate local
program suitable for a later, separately reviewed refreeze.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, replace
import math
import struct
from typing import Literal

import numpy as np

from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
    verify_frozen_tensor,
)
from .frozen_call_graph import freeze_rulespace_call_graph


C19_LOCAL_REFREEZE_PREFLIGHT_SCHEMA_VERSION = (
    "v3m0.c19-local-refreeze-preflight.v1"
)
C19_AUTHORITY_STATE = "ISOLATED_LOCAL_PREFLIGHT_NOT_ISSUED"
C19_CHANNEL_ORDER = tuple(
    channel
    for pair in range(10)
    for channel in (f"q{pair}", f"p{pair}")
)
C19_TARGET_TOOTH = 2.0**-14
C19_LOCAL_SHEAR_STEP_SCHEMA_VERSION = "v3m0.c19-local-shear-step.v1"


@dataclass(frozen=True)
class C19LocalShearStep:
    """One on-site real canonical shear in the isolated C19 program."""

    step_schema_version: str
    step_id: str
    source_channel: str
    destination_channel: str
    offset: tuple[int, ...]
    coefficient: float
    target_conditioned: bool
    step_sha: str


@dataclass(frozen=True)
class C19LocalRefreezePreflight:
    """Construction-only preflight; this record carries no authority."""

    preflight_schema_version: str
    authority_state: str
    channel_order: tuple[str, ...]
    spatial_ndim: int
    primitive_support_radius: int
    matched_steps: tuple[C19LocalShearStep, ...]
    actual_steps: tuple[C19LocalShearStep, ...]
    matched_program_digest: str
    actual_program_digest: str
    matched_branch_digest: str
    actual_branch_digest: str
    matched_executed_kernel: FrozenComplexTensor
    actual_executed_kernel: FrozenComplexTensor
    matched_unitarity_residual: float
    matched_symplectic_residual: float
    matched_reality_residual: float
    actual_unitarity_residual: float
    actual_symplectic_residual: float
    actual_reality_residual: float
    source_b_plus: FrozenComplexTensor
    readout_b_plus_adjoint: FrozenComplexTensor
    source_isometry_residual: float
    readout_coisometry_residual: float
    response_torus_denominator: int
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    bridge_reciprocal_indices: tuple[tuple[int, ...], ...]
    bridge_steps: tuple[int, ...]
    incidence_operator: FrozenComplexTensor
    tt_basis: FrozenComplexTensor
    gauge_basis: FrozenComplexTensor
    row_basis: FrozenComplexTensor
    ker_c_projector: FrozenComplexTensor
    curvature_frame: FrozenComplexTensor
    principal_sine_squared_kernel: FrozenComplexTensor
    principal_spectrum: tuple[float, ...]
    preflight_sha: str


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _exact_text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _exact_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an exact integer")
    return value


def _exact_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an exact fp64 float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _exact_int_tuple(value: object, field: str) -> tuple[int, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    return tuple(
        _exact_int(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    )


def _exact_index_tuple(
    value: object,
    field: str,
) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    result = tuple(
        _exact_int_tuple(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    )
    if any(len(item) != 1 for item in result):
        raise ValueError(f"{field} must contain one-dimensional indices")
    return result


def _sha(value: object, field: str) -> str:
    result = _exact_text(value, field)
    if len(result) != 64 or any(
        character not in "0123456789abcdef" for character in result
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _validate_preflight_wire_types(
    preflight: C19LocalRefreezePreflight,
) -> None:
    _exact_text(preflight.preflight_schema_version, "preflight_schema_version")
    _exact_text(preflight.authority_state, "authority_state")
    if type(preflight.channel_order) is not tuple:
        raise TypeError("channel_order must be an exact tuple")
    for index, channel in enumerate(preflight.channel_order):
        _exact_text(channel, f"channel_order[{index}]")
    _exact_int(preflight.spatial_ndim, "spatial_ndim")
    _exact_int(preflight.primitive_support_radius, "primitive_support_radius")
    for field in (
        "matched_program_digest",
        "actual_program_digest",
        "matched_branch_digest",
        "actual_branch_digest",
        "preflight_sha",
    ):
        _sha(getattr(preflight, field), field)
    for field in (
        "matched_unitarity_residual",
        "matched_symplectic_residual",
        "matched_reality_residual",
        "actual_unitarity_residual",
        "actual_symplectic_residual",
        "actual_reality_residual",
        "source_isometry_residual",
        "readout_coisometry_residual",
    ):
        _exact_float(getattr(preflight, field), field)
    _exact_int(
        preflight.response_torus_denominator,
        "response_torus_denominator",
    )
    _exact_index_tuple(
        preflight.response_reciprocal_indices,
        "response_reciprocal_indices",
    )
    _exact_index_tuple(
        preflight.bridge_reciprocal_indices,
        "bridge_reciprocal_indices",
    )
    _exact_int_tuple(preflight.bridge_steps, "bridge_steps")
    if type(preflight.principal_spectrum) is not tuple:
        raise TypeError("principal_spectrum must be an exact tuple")
    for index, value in enumerate(preflight.principal_spectrum):
        _exact_float(value, f"principal_spectrum[{index}]")


def c19_local_shear_step_payload(
    step: C19LocalShearStep,
) -> dict[str, object]:
    """Return the hash body of one isolated C19 local shear."""

    _exact_record(step, C19LocalShearStep, "C19 local shear step")
    return {
        "step_schema_version": step.step_schema_version,
        "step_id": step.step_id,
        "source_channel": step.source_channel,
        "destination_channel": step.destination_channel,
        "offset": list(step.offset),
        "coefficient": step.coefficient,
        "target_conditioned": step.target_conditioned,
    }


def _step_record(step: C19LocalShearStep) -> dict[str, object]:
    return {
        **c19_local_shear_step_payload(step),
        "step_sha": step.step_sha,
    }


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


def c19_local_refreeze_preflight_payload(
    preflight: C19LocalRefreezePreflight,
) -> dict[str, object]:
    """Return every construction field except the record's own SHA."""

    _exact_record(
        preflight,
        C19LocalRefreezePreflight,
        "C19 local refreeze preflight",
    )
    return {
        "preflight_schema_version": preflight.preflight_schema_version,
        "authority_state": preflight.authority_state,
        "channel_order": list(preflight.channel_order),
        "spatial_ndim": preflight.spatial_ndim,
        "primitive_support_radius": preflight.primitive_support_radius,
        "matched_steps": [_step_record(step) for step in preflight.matched_steps],
        "actual_steps": [_step_record(step) for step in preflight.actual_steps],
        "matched_program_digest": preflight.matched_program_digest,
        "actual_program_digest": preflight.actual_program_digest,
        "matched_branch_digest": preflight.matched_branch_digest,
        "actual_branch_digest": preflight.actual_branch_digest,
        "matched_executed_kernel": _tensor_record(
            preflight.matched_executed_kernel
        ),
        "actual_executed_kernel": _tensor_record(
            preflight.actual_executed_kernel
        ),
        "matched_unitarity_residual": preflight.matched_unitarity_residual,
        "matched_symplectic_residual": preflight.matched_symplectic_residual,
        "matched_reality_residual": preflight.matched_reality_residual,
        "actual_unitarity_residual": preflight.actual_unitarity_residual,
        "actual_symplectic_residual": preflight.actual_symplectic_residual,
        "actual_reality_residual": preflight.actual_reality_residual,
        "source_b_plus": _tensor_record(preflight.source_b_plus),
        "readout_b_plus_adjoint": _tensor_record(
            preflight.readout_b_plus_adjoint
        ),
        "source_isometry_residual": preflight.source_isometry_residual,
        "readout_coisometry_residual": preflight.readout_coisometry_residual,
        "response_torus_denominator": preflight.response_torus_denominator,
        "response_reciprocal_indices": [
            list(item) for item in preflight.response_reciprocal_indices
        ],
        "bridge_reciprocal_indices": [
            list(item) for item in preflight.bridge_reciprocal_indices
        ],
        "bridge_steps": list(preflight.bridge_steps),
        "incidence_operator": _tensor_record(preflight.incidence_operator),
        "tt_basis": _tensor_record(preflight.tt_basis),
        "gauge_basis": _tensor_record(preflight.gauge_basis),
        "row_basis": _tensor_record(preflight.row_basis),
        "ker_c_projector": _tensor_record(preflight.ker_c_projector),
        "curvature_frame": _tensor_record(preflight.curvature_frame),
        "principal_sine_squared_kernel": _tensor_record(
            preflight.principal_sine_squared_kernel
        ),
        "principal_spectrum": list(preflight.principal_spectrum),
    }


def _step(
    step_id: str,
    source_channel: str,
    destination_channel: str,
    coefficient: float,
    *,
    target_conditioned: bool,
) -> C19LocalShearStep:
    provisional = C19LocalShearStep(
        step_schema_version=C19_LOCAL_SHEAR_STEP_SCHEMA_VERSION,
        step_id=step_id,
        source_channel=source_channel,
        destination_channel=destination_channel,
        offset=(0,),
        coefficient=float(coefficient),
        target_conditioned=target_conditioned,
        step_sha="0" * 64,
    )
    return replace(
        provisional,
        step_sha=canonical_sha(c19_local_shear_step_payload(provisional)),
    )


def _pair_steps(pair: int) -> tuple[C19LocalShearStep, ...]:
    q_channel = f"q{pair}"
    p_channel = f"p{pair}"
    prefix = f"pair.{pair:02d}"
    return (
        _step(
            f"{prefix}.quarter.lower.0",
            q_channel,
            p_channel,
            1.0,
            target_conditioned=False,
        ),
        _step(
            f"{prefix}.quarter.upper",
            p_channel,
            q_channel,
            -1.0,
            target_conditioned=False,
        ),
        _step(
            f"{prefix}.quarter.lower.1",
            q_channel,
            p_channel,
            1.0,
            target_conditioned=False,
        ),
        _step(
            f"{prefix}.conditioned.inverse.0",
            q_channel,
            p_channel,
            C19_TARGET_TOOTH,
            target_conditioned=True,
        ),
        _step(
            f"{prefix}.conditioned.inverse.1",
            q_channel,
            p_channel,
            -C19_TARGET_TOOTH,
            target_conditioned=True,
        ),
    )


def _execute_steps(
    steps: tuple[C19LocalShearStep, ...],
) -> np.ndarray:
    channel_index = {
        channel: index for index, channel in enumerate(C19_CHANNEL_ORDER)
    }
    matrix = np.eye(len(C19_CHANNEL_ORDER), dtype=np.complex128)
    for step in steps:
        source = channel_index[step.source_channel]
        destination = channel_index[step.destination_channel]
        matrix[destination] += step.coefficient * matrix[source]
    return matrix


def _program_digest(
    steps: tuple[C19LocalShearStep, ...],
) -> str:
    return canonical_sha(
        {
            "program_schema_version": "v3m0.c19-local-shear-program.v1",
            "steps": [
                {
                    **c19_local_shear_step_payload(step),
                    "step_sha": step.step_sha,
                }
                for step in steps
            ],
        }
    )


def _branch_digest(
    branch: Literal["actual", "matched_ablated"],
    program_digest: str,
    kernel_sha: str,
) -> str:
    return canonical_sha(
        {
            "branch_schema_version": "v3m0.c19-local-branch.v1",
            "branch": branch,
            "program_digest": program_digest,
            "executed_kernel_sha": kernel_sha,
        }
    )


def _kernel_residuals(matrix: np.ndarray) -> tuple[float, float, float]:
    identity = np.eye(len(C19_CHANNEL_ORDER), dtype=np.complex128)
    symplectic_form = np.kron(
        np.eye(10, dtype=np.complex128),
        np.asarray(((0.0, -1.0), (1.0, 0.0)), dtype=np.complex128),
    )
    # Accelerate can emit spurious IEEE warnings while returning the exact
    # zero product for these signed-permutation matrices.  The explicit
    # finite checks in the verifier (added below) remain the authority.
    with np.errstate(all="ignore"):
        return (
            float(np.linalg.norm(matrix.conj().T @ matrix - identity, ord=2)),
            float(
                np.linalg.norm(
                    matrix.T @ symplectic_form @ matrix - symplectic_form,
                    ord=2,
                )
            ),
            float(np.linalg.norm(matrix.conj() - matrix, ord=2)),
        )


def _positive_frequency_bridge() -> tuple[np.ndarray, np.ndarray]:
    source = np.zeros((20, 10), dtype=np.complex128)
    normalization = float(1.0 / math.sqrt(2.0))
    for pair in range(10):
        source[2 * pair, pair] = normalization
        source[2 * pair + 1, pair] = -1.0j * normalization
    return source, source.conj().T.copy()


def _bridge_residuals(
    source: np.ndarray,
    readout: np.ndarray,
) -> tuple[float, float]:
    identity = np.eye(10, dtype=np.complex128)
    with np.errstate(all="ignore"):
        return (
            float(np.linalg.norm(source.conj().T @ source - identity, ord=2)),
            float(
                np.linalg.norm(
                    readout @ readout.conj().T - identity,
                    ord=2,
                )
            ),
        )


def _observer_geometry() -> tuple[np.ndarray, ...]:
    ambient = np.eye(10, dtype=np.complex128)
    tt_basis = ambient[:, (0, 1)]
    gauge_basis = ambient[:, (2, 3, 4, 5)]
    row_basis = ambient[:, (6, 7, 8, 9)]
    incidence = ambient[(0, 1, 6, 7, 8, 9), :]
    ker_c_projector = np.zeros((10, 10), dtype=np.complex128)
    ker_c_projector[:6, :6] = np.eye(6, dtype=np.complex128)
    curvature_frame = incidence.conj().T.copy()
    with np.errstate(all="ignore"):
        principal = (
            np.eye(6, dtype=np.complex128)
            - curvature_frame.conj().T
            @ ker_c_projector
            @ curvature_frame
        )
    return (
        incidence,
        tt_basis,
        gauge_basis,
        row_basis,
        ker_c_projector,
        curvature_frame,
        principal,
    )


def _fp64_equal(left: float, right: float) -> bool:
    return (
        type(left) is float
        and type(right) is float
        and struct.pack(">d", left) == struct.pack(">d", right)
    )


def _canonical_j20() -> np.ndarray:
    result = np.zeros((20, 20), dtype=np.complex128)
    block = np.asarray(((0.0, -1.0), (1.0, 0.0)), dtype=np.complex128)
    for pair in range(10):
        start = 2 * pair
        result[start : start + 2, start : start + 2] = block
    return result


def build_c19_local_refreeze_preflight() -> C19LocalRefreezePreflight:
    """Build the unique isolated 20-channel local construction preflight."""

    actual_steps = tuple(
        step for pair in range(10) for step in _pair_steps(pair)
    )
    matched_steps = tuple(
        step for step in actual_steps if not step.target_conditioned
    )
    matched_matrix = _execute_steps(matched_steps)
    actual_matrix = _execute_steps(actual_steps)
    matched_kernel = freeze_complex_tensor(matched_matrix)
    actual_kernel = freeze_complex_tensor(actual_matrix)
    matched_program_digest = _program_digest(matched_steps)
    actual_program_digest = _program_digest(actual_steps)
    matched_residuals = _kernel_residuals(matched_matrix)
    actual_residuals = _kernel_residuals(actual_matrix)
    source, readout = _positive_frequency_bridge()
    bridge_residuals = _bridge_residuals(source, readout)
    geometry = _observer_geometry()
    provisional = C19LocalRefreezePreflight(
        preflight_schema_version=(
            C19_LOCAL_REFREEZE_PREFLIGHT_SCHEMA_VERSION
        ),
        authority_state=C19_AUTHORITY_STATE,
        channel_order=C19_CHANNEL_ORDER,
        spatial_ndim=1,
        primitive_support_radius=0,
        matched_steps=matched_steps,
        actual_steps=actual_steps,
        matched_program_digest=matched_program_digest,
        actual_program_digest=actual_program_digest,
        matched_branch_digest=_branch_digest(
            "matched_ablated",
            matched_program_digest,
            matched_kernel.tensor_sha,
        ),
        actual_branch_digest=_branch_digest(
            "actual",
            actual_program_digest,
            actual_kernel.tensor_sha,
        ),
        matched_executed_kernel=matched_kernel,
        actual_executed_kernel=actual_kernel,
        matched_unitarity_residual=matched_residuals[0],
        matched_symplectic_residual=matched_residuals[1],
        matched_reality_residual=matched_residuals[2],
        actual_unitarity_residual=actual_residuals[0],
        actual_symplectic_residual=actual_residuals[1],
        actual_reality_residual=actual_residuals[2],
        source_b_plus=freeze_complex_tensor(source),
        readout_b_plus_adjoint=freeze_complex_tensor(readout),
        source_isometry_residual=bridge_residuals[0],
        readout_coisometry_residual=bridge_residuals[1],
        response_torus_denominator=8,
        response_reciprocal_indices=((1,),),
        bridge_reciprocal_indices=((0,), (1,), (7,)),
        bridge_steps=(1, 2, 4),
        incidence_operator=freeze_complex_tensor(geometry[0]),
        tt_basis=freeze_complex_tensor(geometry[1]),
        gauge_basis=freeze_complex_tensor(geometry[2]),
        row_basis=freeze_complex_tensor(geometry[3]),
        ker_c_projector=freeze_complex_tensor(geometry[4]),
        curvature_frame=freeze_complex_tensor(geometry[5]),
        principal_sine_squared_kernel=freeze_complex_tensor(geometry[6]),
        principal_spectrum=(0.0, 0.0, 1.0, 1.0, 1.0, 1.0),
        preflight_sha="0" * 64,
    )
    return replace(
        provisional,
        preflight_sha=canonical_sha(
            c19_local_refreeze_preflight_payload(provisional)
        ),
    )


def verify_c19_local_refreeze_preflight(
    preflight: C19LocalRefreezePreflight,
) -> C19LocalRefreezePreflight:
    """Replay the isolated record without issuing Parent or science authority."""

    _exact_record(
        preflight,
        C19LocalRefreezePreflight,
        "C19 local refreeze preflight",
    )
    _validate_preflight_wire_types(preflight)
    if (
        preflight.preflight_schema_version
        != C19_LOCAL_REFREEZE_PREFLIGHT_SCHEMA_VERSION
    ):
        raise ValueError("C19 local refreeze preflight schema drifted")
    if preflight.authority_state != C19_AUTHORITY_STATE:
        raise ValueError("C19 local preflight cannot claim issuance authority")
    if preflight.channel_order != C19_CHANNEL_ORDER:
        raise ValueError("C19 channel order is not the frozen 20-channel schema")
    if preflight.spatial_ndim != 1:
        raise ValueError("C19 spatial dimension is not frozen")
    if preflight.primitive_support_radius != 0:
        raise ValueError("C19 primitive support is not strictly on-site")

    for field in ("matched_steps", "actual_steps"):
        steps = getattr(preflight, field)
        if type(steps) is not tuple:
            raise TypeError(f"{field} must be an exact tuple")
        for step in steps:
            _exact_record(step, C19LocalShearStep, "C19 local shear step")
            _exact_text(step.step_schema_version, "step_schema_version")
            _exact_text(step.step_id, "step_id")
            _exact_text(step.source_channel, "source_channel")
            _exact_text(step.destination_channel, "destination_channel")
            _exact_int_tuple(step.offset, "offset")
            _exact_float(step.coefficient, "coefficient")
            if type(step.target_conditioned) is not bool:
                raise TypeError(
                    "C19 target-conditioned tag is not an exact bool"
                )
            _sha(step.step_sha, "step_sha")
            if step.step_sha != canonical_sha(
                c19_local_shear_step_payload(step)
            ):
                raise ValueError("C19 local shear step SHA does not replay")
            if step.step_schema_version != C19_LOCAL_SHEAR_STEP_SCHEMA_VERSION:
                raise ValueError("C19 local shear step schema drifted")
            if (
                step.source_channel not in C19_CHANNEL_ORDER
                or step.destination_channel not in C19_CHANNEL_ORDER
                or step.source_channel == step.destination_channel
            ):
                raise ValueError("C19 local shear channels are invalid")
            if step.offset != (0,):
                raise ValueError("C19 local shear offset is not on-site")

    expected_actual = tuple(
        step for pair in range(10) for step in _pair_steps(pair)
    )
    expected_matched = tuple(
        step for step in expected_actual if not step.target_conditioned
    )
    if preflight.actual_steps != expected_actual:
        raise ValueError("C19 inverse-tooth actual program differs from freeze")
    if preflight.matched_steps != expected_matched:
        raise ValueError("C19 matched quarter-turn program differs from freeze")
    if len(preflight.actual_steps) != 50 or len(preflight.matched_steps) != 30:
        raise ValueError("C19 local program step counts drifted")

    for field in (
        "matched_executed_kernel",
        "actual_executed_kernel",
        "source_b_plus",
        "readout_b_plus_adjoint",
        "incidence_operator",
        "tt_basis",
        "gauge_basis",
        "row_basis",
        "ker_c_projector",
        "curvature_frame",
        "principal_sine_squared_kernel",
    ):
        verify_frozen_tensor(getattr(preflight, field))

    expected_matched_program = _program_digest(preflight.matched_steps)
    expected_actual_program = _program_digest(preflight.actual_steps)
    if preflight.matched_program_digest != expected_matched_program:
        raise ValueError("C19 matched program digest does not replay")
    if preflight.actual_program_digest != expected_actual_program:
        raise ValueError("C19 actual program digest does not replay")
    if preflight.actual_program_digest == preflight.matched_program_digest:
        raise ValueError("C19 distinct programs have identical provenance digest")

    matched_matrix = _execute_steps(preflight.matched_steps)
    actual_matrix = _execute_steps(preflight.actual_steps)
    canonical_j20 = _canonical_j20()
    if matched_matrix.tobytes() != canonical_j20.tobytes():
        raise ValueError("C19 matched executed kernel is not bit-exact J20")
    if actual_matrix.tobytes() != canonical_j20.tobytes():
        raise ValueError("C19 actual executed kernel is not bit-exact J20")
    if actual_matrix.tobytes() != matched_matrix.tobytes():
        raise ValueError("C19 executed kernels are not branch-neutral")
    expected_matched_kernel = freeze_complex_tensor(matched_matrix)
    expected_actual_kernel = freeze_complex_tensor(actual_matrix)
    if preflight.matched_executed_kernel != expected_matched_kernel:
        raise ValueError("C19 matched stored kernel does not replay")
    if preflight.actual_executed_kernel != expected_actual_kernel:
        raise ValueError("C19 actual stored kernel does not replay")
    if (
        preflight.actual_executed_kernel.tensor_sha
        != preflight.matched_executed_kernel.tensor_sha
    ):
        raise ValueError("C19 branch-neutral kernel SHA differs across branches")

    expected_matched_branch = _branch_digest(
        "matched_ablated",
        expected_matched_program,
        expected_matched_kernel.tensor_sha,
    )
    expected_actual_branch = _branch_digest(
        "actual",
        expected_actual_program,
        expected_actual_kernel.tensor_sha,
    )
    if preflight.matched_branch_digest != expected_matched_branch:
        raise ValueError("C19 matched branch digest does not replay")
    if preflight.actual_branch_digest != expected_actual_branch:
        raise ValueError("C19 actual branch digest does not replay")
    if preflight.actual_branch_digest == preflight.matched_branch_digest:
        raise ValueError("C19 branch provenance digests are not distinct")

    matched_residuals = _kernel_residuals(matched_matrix)
    actual_residuals = _kernel_residuals(actual_matrix)
    residual_pairs = (
        (preflight.matched_unitarity_residual, matched_residuals[0]),
        (preflight.matched_symplectic_residual, matched_residuals[1]),
        (preflight.matched_reality_residual, matched_residuals[2]),
        (preflight.actual_unitarity_residual, actual_residuals[0]),
        (preflight.actual_symplectic_residual, actual_residuals[1]),
        (preflight.actual_reality_residual, actual_residuals[2]),
    )
    for observed, expected in residual_pairs:
        if not _fp64_equal(observed, expected):
            raise ValueError("C19 kernel residual does not replay")
        if not math.isfinite(observed) or observed > 1.0e-12:
            raise ValueError("C19 kernel residual exceeds fp64 preflight bound")

    expected_source, expected_readout = _positive_frequency_bridge()
    source = frozen_tensor_array(preflight.source_b_plus)
    readout = frozen_tensor_array(preflight.readout_b_plus_adjoint)
    if source.tobytes() != expected_source.tobytes() or source.shape != (20, 10):
        raise ValueError("C19 B+ source is not the frozen 20x10 isometry")
    if (
        readout.tobytes() != expected_readout.tobytes()
        or readout.shape != (10, 20)
        or readout.tobytes() != source.conj().T.tobytes()
    ):
        raise ValueError("C19 readout is not bit-exact B+ adjoint")
    bridge_residuals = _bridge_residuals(source, readout)
    for observed, expected in (
        (preflight.source_isometry_residual, bridge_residuals[0]),
        (preflight.readout_coisometry_residual, bridge_residuals[1]),
    ):
        if not _fp64_equal(observed, expected):
            raise ValueError("C19 source/readout residual does not replay")
        if not math.isfinite(observed) or observed > 1.0e-12:
            raise ValueError("C19 source/readout residual exceeds fp64 bound")

    if (
        preflight.response_torus_denominator != 8
        or preflight.response_reciprocal_indices != ((1,),)
    ):
        raise ValueError("C19 response must contain exactly the frozen single node")
    if preflight.bridge_reciprocal_indices != ((0,), (1,), (7,)):
        raise ValueError("C19 source/readout bridge nodes drifted")
    if preflight.bridge_steps != (1, 2, 4):
        raise ValueError("C19 source/readout bridge steps drifted")

    expected_geometry = _observer_geometry()
    geometry_fields = (
        "incidence_operator",
        "tt_basis",
        "gauge_basis",
        "row_basis",
        "ker_c_projector",
        "curvature_frame",
        "principal_sine_squared_kernel",
    )
    observed_geometry = tuple(
        frozen_tensor_array(getattr(preflight, field))
        for field in geometry_fields
    )
    if any(
        observed.tobytes() != expected.tobytes()
        for observed, expected in zip(observed_geometry, expected_geometry)
    ):
        raise ValueError("C19 ten-dimensional observer geometry drifted")
    incidence, tt_basis, gauge_basis, row_basis, ker_c, curvature, principal = (
        observed_geometry
    )
    with np.errstate(all="ignore"):
        complete = np.concatenate((tt_basis, gauge_basis, row_basis), axis=1)
        if np.linalg.matrix_rank(incidence) != 6:
            raise ValueError("C19 incidence rank is not six")
        if np.linalg.matrix_rank(gauge_basis) != 4:
            raise ValueError("C19 gauge dimension is not four")
        if not np.array_equal(incidence @ gauge_basis, np.zeros((6, 4))):
            raise ValueError("C19 Gauge is not killed by incidence")
        if not np.array_equal(complete.conj().T @ complete, np.eye(10)):
            raise ValueError("C19 TT/Gauge/Row sectors are not orthonormal complete")
        if not np.array_equal(
            ker_c,
            complete[:, :6] @ complete[:, :6].conj().T,
        ):
            raise ValueError("C19 ker C is not TT plus Gauge")
        if not np.array_equal(curvature, incidence.conj().T):
            raise ValueError("C19 curvature frame is not incidence adjoint range")
        replayed_principal = (
            np.eye(6, dtype=np.complex128)
            - curvature.conj().T @ ker_c @ curvature
        )
    if not np.array_equal(principal, replayed_principal):
        raise ValueError("C19 principal-sine kernel does not replay")
    spectrum = tuple(float(value) for value in np.linalg.eigvalsh(principal))
    expected_spectrum = (0.0, 0.0, 1.0, 1.0, 1.0, 1.0)
    if spectrum != expected_spectrum or preflight.principal_spectrum != spectrum:
        raise ValueError("C19 principal spectrum is not {0,0,1,1,1,1}")

    if preflight.preflight_sha != canonical_sha(
        c19_local_refreeze_preflight_payload(preflight)
    ):
        raise ValueError("C19 local refreeze preflight SHA does not replay")
    return preflight


def execute_c19_constant_symbol(
    preflight: C19LocalRefreezePreflight,
    *,
    branch: Literal["actual", "matched_ablated"],
    reciprocal_index: tuple[int, ...],
    lattice_size: int,
) -> np.ndarray:
    """Execute the on-site symbol; momentum and lattice size are probes only."""

    if type(preflight) is not C19LocalRefreezePreflight:
        raise TypeError("preflight has the wrong strict type")
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("C19 execution branch is not frozen")
    if (
        type(reciprocal_index) is not tuple
        or len(reciprocal_index) != 1
        or type(reciprocal_index[0]) is not int
    ):
        raise TypeError("reciprocal_index must be one exact integer tuple")
    if type(lattice_size) is not int or lattice_size <= 0:
        raise ValueError("lattice_size must be a positive exact integer")
    steps = preflight.actual_steps if branch == "actual" else preflight.matched_steps
    return _execute_steps(steps)


_raw_build_c19_local_refreeze_preflight = build_c19_local_refreeze_preflight
_raw_verify_c19_local_refreeze_preflight = verify_c19_local_refreeze_preflight
build_c19_local_refreeze_preflight = freeze_rulespace_call_graph(
    _raw_build_c19_local_refreeze_preflight
)
verify_c19_local_refreeze_preflight = freeze_rulespace_call_graph(
    _raw_verify_c19_local_refreeze_preflight
)
del (
    _raw_build_c19_local_refreeze_preflight,
    _raw_verify_c19_local_refreeze_preflight,
)


__all__ = [
    "C19_AUTHORITY_STATE",
    "C19_CHANNEL_ORDER",
    "C19_LOCAL_REFREEZE_PREFLIGHT_SCHEMA_VERSION",
    "C19_LOCAL_SHEAR_STEP_SCHEMA_VERSION",
    "C19_TARGET_TOOTH",
    "C19LocalRefreezePreflight",
    "C19LocalShearStep",
    "build_c19_local_refreeze_preflight",
    "c19_local_refreeze_preflight_payload",
    "c19_local_shear_step_payload",
    "execute_c19_constant_symbol",
    "verify_c19_local_refreeze_preflight",
]
