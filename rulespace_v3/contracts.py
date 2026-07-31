"""Frozen status contracts for V3-M0 evaluator blocks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class UndefinedReason(str, Enum):
    TRACE_UNCLASSIFIED = "trace_unclassified"
    ABLATION_NOT_REVERSIBLE = "ablation_not_reversible"
    STATE_SCHEMA_MISMATCH = "state_schema_mismatch"
    RESPONSE_NULL = "response_null"
    RESPONSE_GREY = "response_grey"
    RANK_GAP = "rank_gap"
    SHELL_TRACKING_AMBIGUOUS = "shell_tracking_ambiguous"
    UNSTABLE = "unstable"
    MANIFEST_MISMATCH = "manifest_mismatch"
    PRESTRUCTURE_INVALID = "prestructure_invalid"
    REALITY_VIOLATION = "reality_violation"
    LAURENT_RESOURCE_EXCEEDED = "laurent_resource_exceeded"
    STRUCTURE_UNRESOLVED = "structure_unresolved"
    DYNAMICS_BRIDGE_FAILED = "dynamics_bridge_failed"
    STABILITY_UNRESOLVED = "stability_unresolved"
    WINDOW_UNRESOLVED = "window_unresolved"
    ENDPOINT_SHELL_AMBIGUOUS = "endpoint_shell_ambiguous"
    PAIRED_RESPONSE_FAILED = "paired_response_failed"
    RESPONSE_BRIDGE_FAILED = "response_bridge_failed"


@dataclass(frozen=True)
class BlockStatus:
    """Whether a block is defined, with an exact reason when it is not."""

    defined: bool
    reason: Optional[UndefinedReason]

    def __post_init__(self) -> None:
        if type(self.defined) is not bool:
            raise TypeError("defined must be a bool")
        if self.reason is not None and not isinstance(self.reason, UndefinedReason):
            raise TypeError("reason must be an UndefinedReason or None")
        if self.defined != (self.reason is None):
            raise ValueError("defined must be true exactly when reason is None")


@dataclass(frozen=True)
class RequiredBlockReport:
    """All undefined required blocks plus their ordered summary status."""

    status: BlockStatus
    undefined: tuple[tuple[str, UndefinedReason], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, BlockStatus):
            raise TypeError("status must be a BlockStatus")
        if not isinstance(self.undefined, tuple):
            raise TypeError("undefined must be a tuple")

        seen: set[str] = set()
        for entry in self.undefined:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise TypeError("undefined entries must be (block_id, reason) tuples")
            block_id, reason = entry
            if not isinstance(block_id, str) or not block_id.strip():
                raise ValueError("undefined block IDs must be non-empty strings")
            if block_id in seen:
                raise ValueError(f"duplicate undefined block ID: {block_id}")
            if not isinstance(reason, UndefinedReason):
                raise TypeError("undefined reasons must be UndefinedReason values")
            seen.add(block_id)

        expected = (
            BlockStatus(False, self.undefined[0][1])
            if self.undefined
            else BlockStatus(True, None)
        )
        if self.status != expected:
            raise ValueError("status must summarize the first undefined block")


def evaluate_required_blocks(
    blocks: Mapping[str, BlockStatus],
    required_ids: Sequence[str],
) -> RequiredBlockReport:
    """Evaluate only preregistered blocks, preserving their declared order."""

    if not isinstance(blocks, Mapping):
        raise TypeError("blocks must be a mapping")

    block_snapshot: dict[str, BlockStatus] = {}
    for block_id, status in blocks.items():
        if not isinstance(block_id, str) or not block_id.strip():
            raise ValueError("block IDs must be non-empty strings")
        if not isinstance(status, BlockStatus):
            raise TypeError(f"block {block_id!r} must have a BlockStatus")
        if block_id in block_snapshot:
            raise ValueError(f"duplicate block ID in items snapshot: {block_id}")
        block_snapshot[block_id] = status

    if not isinstance(required_ids, Sequence) or isinstance(
        required_ids, (str, bytes, bytearray)
    ):
        raise TypeError("required_ids must be a sequence of block IDs")
    ordered_ids = tuple(required_ids)
    if not ordered_ids:
        raise ValueError("required_ids must not be empty")

    seen: set[str] = set()
    for block_id in ordered_ids:
        if not isinstance(block_id, str):
            raise TypeError("required block IDs must be strings")
        if not block_id.strip():
            raise ValueError("required block IDs must be non-empty strings")
        if block_id in seen:
            raise ValueError(f"duplicate required block ID: {block_id}")
        seen.add(block_id)

    missing = [
        block_id for block_id in ordered_ids if block_id not in block_snapshot
    ]
    if missing:
        raise ValueError(f"missing required blocks: {', '.join(missing)}")

    undefined_entries: list[tuple[str, UndefinedReason]] = []
    for block_id in ordered_ids:
        status = block_snapshot[block_id]
        if status.defined:
            continue
        reason = status.reason
        if reason is None:
            raise AssertionError("BlockStatus invariant lost its undefined reason")
        undefined_entries.append((block_id, reason))
    undefined = tuple(undefined_entries)

    return RequiredBlockReport(
        status=(
            BlockStatus(False, undefined[0][1])
            if undefined
            else BlockStatus(True, None)
        ),
        undefined=undefined,
    )
