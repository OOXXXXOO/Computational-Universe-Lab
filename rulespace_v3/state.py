"""Pure V3-M0 terminal-state resolution.

The Task 17 orchestrator is responsible for obtaining every boolean and
required-block report from opaque verified capabilities.  This module only
freezes the fail-closed ordering and the unique window-reason mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .contracts import RequiredBlockReport, UndefinedReason


class V3M0State(str, Enum):
    HALT_FORMAL = "HALT-V3M0-FORMAL"
    HALT_CONTROL = "HALT-V3M0-CONTROL"
    HALT_IDENTIFIABILITY = "HALT-V3M0-IDENTIFIABILITY"
    HALT_WINDOW = "HALT-V3M0-WINDOW"
    READY_V3_M1_ANCHOR_CERTIFICATION = "READY-V3-M1-ANCHOR-CERTIFICATION"


@dataclass(frozen=True)
class V3M0StateDecision:
    state: V3M0State
    undefined: tuple[tuple[str, UndefinedReason], ...]

    def __post_init__(self) -> None:
        if type(self.state) is not V3M0State:
            raise TypeError("state must be a V3M0State")
        if type(self.undefined) is not tuple:
            raise TypeError("undefined must be a tuple")
        for entry in self.undefined:
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError("undefined entries must be exact pairs")
            block_id, reason = entry
            if type(block_id) is not str or not block_id:
                raise ValueError("undefined block IDs must be non-empty strings")
            if type(reason) is not UndefinedReason:
                raise TypeError("undefined reasons must be exact enum values")
        if self.ready and self.undefined:
            raise ValueError("ready state cannot retain undefined blocks")

    @property
    def ready(self) -> bool:
        return self.state is V3M0State.READY_V3_M1_ANCHOR_CERTIFICATION

    @property
    def first_undefined(self) -> Optional[tuple[str, UndefinedReason]]:
        return self.undefined[0] if self.undefined else None


def _exact_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{field} must be an exact bool")
    return value


def resolve_v3m0_state(
    *,
    formal_all_pass: bool,
    exact_all_pass: bool,
    identifiability_all_pass: bool,
    required_blocks: RequiredBlockReport,
    all_block_success_artifacts_verified: bool,
    all_required_controls_pass: bool,
    representation_invariants_pass: bool,
    all_expected_terminations_verified: bool,
    all_analysis_controls_verified: bool,
    no_unexpected_downstream_capability: bool,
    no_physical_anchor_run: bool,
) -> V3M0StateDecision:
    """Resolve the V3-M0 state without weakening or relabelling failures."""

    formal = _exact_bool(formal_all_pass, "formal_all_pass")
    exact = _exact_bool(exact_all_pass, "exact_all_pass")
    identifiable = _exact_bool(
        identifiability_all_pass,
        "identifiability_all_pass",
    )
    controls = _exact_bool(
        all_required_controls_pass,
        "all_required_controls_pass",
    )
    block_artifacts = _exact_bool(
        all_block_success_artifacts_verified,
        "all_block_success_artifacts_verified",
    )
    invariants = _exact_bool(
        representation_invariants_pass,
        "representation_invariants_pass",
    )
    terminations = _exact_bool(
        all_expected_terminations_verified,
        "all_expected_terminations_verified",
    )
    analysis_controls = _exact_bool(
        all_analysis_controls_verified,
        "all_analysis_controls_verified",
    )
    downstream_clean = _exact_bool(
        no_unexpected_downstream_capability,
        "no_unexpected_downstream_capability",
    )
    scope_clean = _exact_bool(
        no_physical_anchor_run,
        "no_physical_anchor_run",
    )
    if type(required_blocks) is not RequiredBlockReport:
        raise TypeError("required_blocks must be an exact RequiredBlockReport")
    undefined = required_blocks.undefined

    if not formal or not exact:
        state = V3M0State.HALT_FORMAL
    elif not identifiable:
        state = V3M0State.HALT_IDENTIFIABILITY
    elif undefined:
        state = (
            V3M0State.HALT_WINDOW
            if undefined[0][1] is UndefinedReason.WINDOW_UNRESOLVED
            else V3M0State.HALT_CONTROL
        )
    elif (
        not block_artifacts
        or not controls
        or not invariants
        or not terminations
        or not analysis_controls
        or not downstream_clean
        or not scope_clean
    ):
        state = V3M0State.HALT_CONTROL
    else:
        state = V3M0State.READY_V3_M1_ANCHOR_CERTIFICATION
    return V3M0StateDecision(state=state, undefined=undefined)


__all__ = [
    "V3M0State",
    "V3M0StateDecision",
    "resolve_v3m0_state",
]
