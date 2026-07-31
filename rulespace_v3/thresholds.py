"""Frozen Task 11 window and signal-line thresholds.

This module contains no transition, shell, or family input.  It provides the
pre-registered constants and pure arithmetic gates that later verified
response evidence must replay; it does not issue a calibration capability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple


class _ThresholdAuthority(NamedTuple):
    t_candidates: tuple[int, ...]
    fejer_orders: tuple[int, ...]
    phase_grid_protocol_id: str
    phase_separation_protocol_id: str
    source_trial_generation_id: str
    pi: float
    shell_participation_min: float
    overlap_margin_min: float
    shell_projector_residual_max: float
    shell_loop_residual_max: float
    projector_t2t_max: float
    signal_noise_ratio_min: float
    raw_gap_min: float
    bridge_tolerance: float
    eps_fp64: float
    source_bridge_work_max: int
    shell_projector_entries_max: int
    fejer_work_max: int
    general_evidence_body_bytes_max: int


_FROZEN_THRESHOLDS = _ThresholdAuthority(
    t_candidates=(256, 512, 1024, 2048, 4096, 8192),
    fejer_orders=(256, 512, 1024, 2048, 4096, 8192, 16384),
    phase_grid_protocol_id="two-pi-over-16T-v1",
    phase_separation_protocol_id="eight-pi-over-T-v1",
    source_trial_generation_id="registry-source-identity-v1",
    pi=math.pi,
    shell_participation_min=0.25,
    overlap_margin_min=0.2,
    shell_projector_residual_max=1.0e-12,
    shell_loop_residual_max=1.0e-10,
    projector_t2t_max=1.0e-10,
    signal_noise_ratio_min=1.0e3,
    raw_gap_min=1.0e3,
    bridge_tolerance=1.0e-12,
    eps_fp64=2.0**-52,
    source_bridge_work_max=32_768,
    shell_projector_entries_max=16_777_216,
    fejer_work_max=2_000_000_000,
    general_evidence_body_bytes_max=256 * 1024 * 1024,
)

T_CANDIDATES = _FROZEN_THRESHOLDS.t_candidates
FEJER_ORDERS = _FROZEN_THRESHOLDS.fejer_orders

PHASE_GRID_PROTOCOL_ID = _FROZEN_THRESHOLDS.phase_grid_protocol_id
PHASE_SEPARATION_PROTOCOL_ID = (
    _FROZEN_THRESHOLDS.phase_separation_protocol_id
)
SOURCE_TRIAL_GENERATION_ID = (
    _FROZEN_THRESHOLDS.source_trial_generation_id
)

SHELL_PARTICIPATION_MIN = _FROZEN_THRESHOLDS.shell_participation_min
OVERLAP_MARGIN_MIN = _FROZEN_THRESHOLDS.overlap_margin_min
SHELL_PROJECTOR_RESIDUAL_MAX = (
    _FROZEN_THRESHOLDS.shell_projector_residual_max
)
SHELL_LOOP_RESIDUAL_MAX = _FROZEN_THRESHOLDS.shell_loop_residual_max
PROJECTOR_T2T_MAX = _FROZEN_THRESHOLDS.projector_t2t_max
SIGNAL_NOISE_RATIO_MIN = _FROZEN_THRESHOLDS.signal_noise_ratio_min
RAW_GAP_MIN = _FROZEN_THRESHOLDS.raw_gap_min
BRIDGE_TOLERANCE = _FROZEN_THRESHOLDS.bridge_tolerance
EPS_FP64 = _FROZEN_THRESHOLDS.eps_fp64

SOURCE_BRIDGE_WORK_MAX = _FROZEN_THRESHOLDS.source_bridge_work_max
SHELL_PROJECTOR_ENTRIES_MAX = (
    _FROZEN_THRESHOLDS.shell_projector_entries_max
)
FEJER_WORK_MAX = _FROZEN_THRESHOLDS.fejer_work_max
GENERAL_EVIDENCE_BODY_BYTES_MAX = (
    _FROZEN_THRESHOLDS.general_evidence_body_bytes_max
)


def _positive_int(
    value: object,
    field: str,
    *,
    _type=type,
    _int_type=int,
    _type_error=TypeError,
    _value_error=ValueError,
) -> int:
    if _type(value) is not _int_type:
        raise _type_error(f"{field} must be an int")
    if value <= 0:
        raise _value_error(f"{field} must be positive")
    return value


def _closed_order(
    value: object,
    field: str,
    fejer_orders: tuple[int, ...],
    *,
    _type=type,
    _int_type=int,
    _type_error=TypeError,
    _value_error=ValueError,
) -> int:
    if _type(value) is not _int_type:
        raise _type_error(f"{field} must be an int")
    if value <= 0:
        raise _value_error(f"{field} must be positive")
    order = value
    if order not in fejer_orders:
        raise _value_error(
            f"{field} must be a preregistered candidate or the 16384 2T check"
        )
    return order


def _make_scalar_validators(
    isfinite,
    *,
    type_fn=type,
    float_type=float,
    type_error=TypeError,
    value_error=ValueError,
):
    def finite_nonnegative_float(value: object, field: str) -> float:
        if type_fn(value) is not float_type:
            raise type_error(f"{field} must be a float")
        if not isfinite(value):
            raise value_error(f"{field} must be finite")
        if value < 0.0:
            raise value_error(f"{field} must be non-negative")
        return value

    def finite_positive_float(value: object, field: str) -> float:
        result = finite_nonnegative_float(value, field)
        if result <= 0.0:
            raise value_error(f"{field} must be positive")
        return result

    return finite_nonnegative_float, finite_positive_float


(
    _finite_nonnegative_float,
    _finite_positive_float,
) = _make_scalar_validators(math.isfinite)


def _make_phase_formulas(
    authority: _ThresholdAuthority,
    closed_order,
):
    def phase_grid_step(order: int) -> float:
        """Return the frozen eigenphase spacing ``2π/(16T)``."""

        verified = closed_order(
            order,
            "order",
            authority.fejer_orders,
        )
        return 2.0 * authority.pi / (16 * verified)

    def phase_separation_min(order: int) -> float:
        """Return the frozen nearest-competitor minimum ``8π/T``."""

        verified = closed_order(
            order,
            "order",
            authority.fejer_orders,
        )
        return 8.0 * authority.pi / verified

    return phase_grid_step, phase_separation_min


phase_grid_step, phase_separation_min = _make_phase_formulas(
    _FROZEN_THRESHOLDS,
    _closed_order,
)


def _make_protocol_and_comparison_gates(
    authority: _ThresholdAuthority,
    frozen_phase_separation_min,
    closed_order,
    finite_nonnegative_float,
    *,
    type_fn=type,
    tuple_type=tuple,
    str_type=str,
    value_error=ValueError,
):
    def verify_window_protocol_thresholds(
        *,
        t_candidates: tuple[int, ...],
        phase_grid_protocol_id: str,
        phase_separation_protocol_id: str,
        participation_min_required: float,
        overlap_margin_required: float,
        loop_residual_max: float,
        projector_residual_max: float,
    ) -> None:
        """Reject any re-signing of the preregistered constants."""

        if (
            type_fn(t_candidates) is not tuple_type
            or t_candidates != authority.t_candidates
        ):
            raise value_error(
                "t_candidates is not the frozen ascending table"
            )
        if (
            type_fn(phase_grid_protocol_id) is not str_type
            or phase_grid_protocol_id != authority.phase_grid_protocol_id
        ):
            raise value_error("phase_grid_protocol_id is not frozen")
        if (
            type_fn(phase_separation_protocol_id) is not str_type
            or phase_separation_protocol_id
            != authority.phase_separation_protocol_id
        ):
            raise value_error(
                "phase_separation_protocol_id is not frozen"
            )
        fields = (
            (
                participation_min_required,
                authority.shell_participation_min,
                "participation_min_required",
            ),
            (
                overlap_margin_required,
                authority.overlap_margin_min,
                "overlap_margin_required",
            ),
            (
                loop_residual_max,
                authority.shell_loop_residual_max,
                "loop_residual_max",
            ),
            (
                projector_residual_max,
                authority.shell_projector_residual_max,
                "projector_residual_max",
            ),
        )
        for observed, expected, field in fields:
            finite_nonnegative_float(observed, field)
            if observed != expected:
                raise value_error(
                    f"{field} is not the frozen threshold"
                )

    def verify_window_comparison_gates(
        *,
        order: int,
        phase_separation: float,
        overlap_margin: float,
        projector_t2t_distance: float,
    ) -> bool:
        """Apply the inclusive phase/overlap/projector hard gates."""

        verified_order = closed_order(
            order,
            "order",
            authority.fejer_orders,
        )
        if verified_order not in authority.t_candidates:
            raise value_error(
                "comparison base order must be a T candidate"
            )
        separation = finite_nonnegative_float(
            phase_separation,
            "phase_separation",
        )
        overlap = finite_nonnegative_float(
            overlap_margin,
            "overlap_margin",
        )
        distance = finite_nonnegative_float(
            projector_t2t_distance,
            "projector_t2t_distance",
        )
        return (
            separation
            >= frozen_phase_separation_min(verified_order)
            and overlap >= authority.overlap_margin_min
            and distance <= authority.projector_t2t_max
        )

    return (
        verify_window_protocol_thresholds,
        verify_window_comparison_gates,
    )


(
    verify_window_protocol_thresholds,
    verify_window_comparison_gates,
) = _make_protocol_and_comparison_gates(
    _FROZEN_THRESHOLDS,
    phase_separation_min,
    _closed_order,
    _finite_nonnegative_float,
)


@dataclass(frozen=True)
class SignalThresholdValues:
    """Unsigned arithmetic output; not a calibration authority."""

    scale_ref: float
    null_max: float | None
    bridge_operator_error_max: float
    noise_ref: float
    signal_min: float
    tau_sig: float
    signal_noise_ratio: float
    raw_relative_gap: float
    absolute_signal_gate_passed: bool
    relative_gap_gate_passed: bool


def _make_signal_and_resource_api(
    authority: _ThresholdAuthority,
    result_type: type[SignalThresholdValues],
    positive_int,
    finite_nonnegative_float,
    finite_positive_float,
    closed_order,
    *,
    max_fn=max,
    min_fn=min,
    any_fn=any,
    sqrt_fn=math.sqrt,
    isfinite_fn=math.isfinite,
    type_fn=type,
    tuple_type=tuple,
    enumerate_fn=enumerate,
    sorted_fn=sorted,
    set_type=set,
    value_error=ValueError,
):
    def compute_signal_threshold_values(
        *,
        scale_ref: float,
        null_max: float | None,
        bridge_operator_error_max: float,
        signal_min: float,
        raw_relative_gap: float,
    ) -> SignalThresholdValues:
        """Replay the signal line from already verified control evidence."""

        scale = finite_positive_float(scale_ref, "scale_ref")
        null = (
            None
            if null_max is None
            else finite_nonnegative_float(null_max, "null_max")
        )
        bridge = finite_nonnegative_float(
            bridge_operator_error_max,
            "bridge_operator_error_max",
        )
        signal = finite_positive_float(signal_min, "signal_min")
        gap = finite_nonnegative_float(
            raw_relative_gap,
            "raw_relative_gap",
        )
        noise = max_fn(
            0.0 if null is None else null,
            bridge,
            authority.eps_fp64 * scale,
        )
        if not isfinite_fn(noise) or noise <= 0.0:
            raise value_error(
                "noise_ref is not positive and representable in fp64"
            )
        tau = (
            noise
            if noise == signal
            else sqrt_fn(noise) * sqrt_fn(signal)
        )
        ratio = signal / noise
        lower = min_fn(noise, signal)
        upper = max_fn(noise, signal)
        if (
            not isfinite_fn(tau)
            or tau <= 0.0
            or not lower <= tau <= upper
        ):
            raise value_error(
                "tau_sig is outside the finite positive fp64 range"
            )
        if not isfinite_fn(ratio) or ratio <= 0.0:
            raise value_error(
                "signal_noise_ratio is outside the finite positive fp64 range"
            )
        return result_type(
            scale_ref=scale,
            null_max=null,
            bridge_operator_error_max=bridge,
            noise_ref=noise,
            signal_min=signal,
            tau_sig=tau,
            signal_noise_ratio=ratio,
            raw_relative_gap=gap,
            absolute_signal_gate_passed=(
                ratio >= authority.signal_noise_ratio_min
            ),
            relative_gap_gate_passed=gap >= authority.raw_gap_min,
        )

    def preflight_source_bridge_work(
        *,
        n_k: int,
        n_trial: int,
        steps: tuple[int, ...],
    ) -> int:
        """Check ``n_k * n_trial * max(steps)`` before allocation."""

        count_k = positive_int(n_k, "n_k")
        trials = positive_int(n_trial, "n_trial")
        if type_fn(steps) is not tuple_type or not steps:
            raise value_error("steps must be a non-empty tuple")
        checked = tuple_type(
            positive_int(step, f"steps[{index}]")
            for index, step in enumerate_fn(steps)
        )
        if checked != tuple_type(sorted_fn(set_type(checked))):
            raise value_error(
                "steps must be unique and strictly ascending"
            )
        if checked[-1] > 16384:
            raise value_error("steps exceed the frozen maximum")
        if not any_fn(step > 1 for step in checked):
            raise value_error("steps must include at least one t > 1")
        work = count_k * trials * checked[-1]
        if work > authority.source_bridge_work_max:
            raise value_error(
                "source bridge work exceeds the frozen cap"
            )
        return work

    def preflight_shell_projector_entries(
        *,
        n_k: int,
        n_state: int,
    ) -> int:
        """Check the complete ``n_k * n_state²`` projector body."""

        count_k = positive_int(n_k, "n_k")
        state = positive_int(n_state, "n_state")
        entries = count_k * state * state
        if entries > authority.shell_projector_entries_max:
            raise value_error(
                "shell projector entries exceed the frozen cap"
            )
        return entries

    def preflight_fejer_work(
        *,
        n_k: int,
        n_state: int,
        order: int,
    ) -> int:
        """Check ``n_k * (n_state³ + T*n_state)`` before work."""

        count_k = positive_int(n_k, "n_k")
        state = positive_int(n_state, "n_state")
        verified_order = closed_order(
            order,
            "order",
            authority.fejer_orders,
        )
        work = count_k * (state**3 + verified_order * state)
        if work > authority.fejer_work_max:
            raise value_error("Fejer work exceeds the frozen cap")
        return work

    def preflight_general_evidence_body(byte_count: int) -> int:
        """Check the 256 MiB evidence cap before encoding."""

        count = positive_int(byte_count, "byte_count")
        if count > authority.general_evidence_body_bytes_max:
            raise value_error(
                "general evidence body exceeds the frozen cap"
            )
        return count

    return (
        compute_signal_threshold_values,
        preflight_source_bridge_work,
        preflight_shell_projector_entries,
        preflight_fejer_work,
        preflight_general_evidence_body,
    )


(
    compute_signal_threshold_values,
    preflight_source_bridge_work,
    preflight_shell_projector_entries,
    preflight_fejer_work,
    preflight_general_evidence_body,
) = _make_signal_and_resource_api(
    _FROZEN_THRESHOLDS,
    SignalThresholdValues,
    _positive_int,
    _finite_nonnegative_float,
    _finite_positive_float,
    _closed_order,
)


__all__ = [
    "BRIDGE_TOLERANCE",
    "EPS_FP64",
    "FEJER_ORDERS",
    "FEJER_WORK_MAX",
    "GENERAL_EVIDENCE_BODY_BYTES_MAX",
    "OVERLAP_MARGIN_MIN",
    "PHASE_GRID_PROTOCOL_ID",
    "PHASE_SEPARATION_PROTOCOL_ID",
    "PROJECTOR_T2T_MAX",
    "RAW_GAP_MIN",
    "SHELL_LOOP_RESIDUAL_MAX",
    "SHELL_PARTICIPATION_MIN",
    "SHELL_PROJECTOR_ENTRIES_MAX",
    "SHELL_PROJECTOR_RESIDUAL_MAX",
    "SIGNAL_NOISE_RATIO_MIN",
    "SOURCE_BRIDGE_WORK_MAX",
    "SOURCE_TRIAL_GENERATION_ID",
    "SignalThresholdValues",
    "T_CANDIDATES",
    "compute_signal_threshold_values",
    "phase_grid_step",
    "phase_separation_min",
    "preflight_fejer_work",
    "preflight_general_evidence_body",
    "preflight_shell_projector_entries",
    "preflight_source_bridge_work",
    "verify_window_comparison_gates",
    "verify_window_protocol_thresholds",
]
