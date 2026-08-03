"""V3-M0 immutable contracts and profile-aware evidence primitives."""

__all__ = (
    "FINAL_RESULT_EVIDENCE_FIELDS",
    "BlockStatus",
    "EvidenceEnvelope",
    "RequiredBlockReport",
    "UndefinedReason",
    "canonical_sha",
    "evaluate_required_blocks",
    "validate_evidence_envelope",
    "validate_evidence_fields",
)


def __getattr__(name):
    if name == "FINAL_RESULT_EVIDENCE_FIELDS":
        from .evidence import FINAL_RESULT_EVIDENCE_FIELDS

        return FINAL_RESULT_EVIDENCE_FIELDS
    if name == "BlockStatus":
        from .contracts import BlockStatus

        return BlockStatus
    if name == "EvidenceEnvelope":
        from .evidence import EvidenceEnvelope

        return EvidenceEnvelope
    if name == "RequiredBlockReport":
        from .contracts import RequiredBlockReport

        return RequiredBlockReport
    if name == "UndefinedReason":
        from .contracts import UndefinedReason

        return UndefinedReason
    if name == "canonical_sha":
        from .evidence import canonical_sha

        return canonical_sha
    if name == "evaluate_required_blocks":
        from .contracts import evaluate_required_blocks

        return evaluate_required_blocks
    if name == "validate_evidence_envelope":
        from .evidence import validate_evidence_envelope

        return validate_evidence_envelope
    if name == "validate_evidence_fields":
        from .evidence import validate_evidence_fields

        return validate_evidence_fields
    raise AttributeError(name)
