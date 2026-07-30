"""V3-M0 immutable contracts and profile-aware evidence primitives."""

from .contracts import (
    BlockStatus,
    RequiredBlockReport,
    UndefinedReason,
    evaluate_required_blocks,
)
from .evidence import (
    FINAL_RESULT_EVIDENCE_FIELDS,
    EvidenceEnvelope,
    canonical_sha,
    validate_evidence_envelope,
    validate_evidence_fields,
)

__all__ = [
    "FINAL_RESULT_EVIDENCE_FIELDS",
    "BlockStatus",
    "EvidenceEnvelope",
    "RequiredBlockReport",
    "UndefinedReason",
    "canonical_sha",
    "evaluate_required_blocks",
    "validate_evidence_envelope",
    "validate_evidence_fields",
]
