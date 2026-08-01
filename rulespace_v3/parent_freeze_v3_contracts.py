"""Pure raw contracts for Parent-v3 review and signing records.

These frozen records carry no issuer token and cannot create a Parent-v3
capability.  Git replay and the P-to-S allowlist audit live in later layers.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import re
from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Literal, TYPE_CHECKING

from .evidence import canonical_sha

if TYPE_CHECKING:
    from .parent_candidate_v3 import ParentFreezeCandidateV3Manifest


SIGNED_SOURCE_REF_V2_SCHEMA_VERSION = "v3m0.signed-source-ref.v2"
SIGNED_SOURCE_REFS_V2_ROOT_SCHEMA_VERSION = "v3m0.signed-source-ref-tuple.v1"
PARENT_REVIEW_RECEIPT_V1_SCHEMA_VERSION = "v3m0.parent-review-receipt.v1"
PARENT_SIGNING_AUDIT_V1_SCHEMA_VERSION = "v3m0.parent-signing-audit.v1"
PARENT_FREEZE_V3_SCHEMA_VERSION = "v3m0.parent-freeze.v3"
PARENT_V3_AUTHORITY_STATE = "CURRENT_PARENT_V3_ISSUED"
PARENT_V3_PROGRAM_ID = "projective-rule-space-v3m0-v3"
PARENT_V3_SIGNING_DIFF_ALLOWLIST_ID = "parent-v3-signing-diff-v1"
PARENT_V3_REVIEW_SIGNATURE_ALGORITHM = "openssh-ed25519-v1"
PARENT_V3_REVIEW_SIGNATURE_NAMESPACE = "culab-parent-v3-review-v1"
PARENT_REVIEW_RECEIPT_MAX_BYTES = 4 << 20
PARENT_REVIEW_RECEIPT_MAX_DEPTH = 128
PARENT_REVIEW_RECEIPT_MAX_ARRAY_ITEMS = 4096
PARENT_REVIEW_RECEIPT_MAX_STRING_BYTES = 1 << 20

PARENT_V3_REVIEW_ROLES = (
    "MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW",
    "AUTHORITY_AND_BOUNDARY_REVIEW",
)
PARENT_V3_REVIEW_RECEIPT_PATHS_BY_ROLE = (
    (
        PARENT_V3_REVIEW_ROLES[0],
        "data/results/v3m0_parent_v3_review_mathematics.json",
    ),
    (
        PARENT_V3_REVIEW_ROLES[1],
        "data/results/v3m0_parent_v3_review_authority.json",
    ),
)

PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS = (
    (
        "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md",
        "SIGNED_INCREMENTAL_ERRATUM",
        "C05_C18_SCENARIO_RESPONSE_GEOMETRY",
    ),
    (
        "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md",
        "SIGNED_CONSTRUCTION_ERRATUM",
        "C19_REAL20_REFREEZE_V2",
    ),
    (
        "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md",
        "SIGNED_ISSUANCE_PROTOCOL",
        "PARENT_V3_P_EPOCH_SIGNING",
    ),
    (
        "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md",
        "SIGNED_RUNTIME_AUTHORITY_PROTOCOL",
        "C19_METRIC_SUPPORT_AUTHORITY_V1",
    ),
)

_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_GIT_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_OPENSSH_SHA256_FINGERPRINT = re.compile(r"SHA256:[A-Za-z0-9+/]{43}\Z")
_SSH_SIGNATURE_BEGIN = "-----BEGIN SSH SIGNATURE-----"
_SSH_SIGNATURE_END = "-----END SSH SIGNATURE-----"


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _require_exact_wire_tree(
    value: object,
    field: str,
    *,
    active: set[int] | None = None,
    depth: int = 1,
) -> None:
    if depth > PARENT_REVIEW_RECEIPT_MAX_DEPTH:
        raise ValueError("Parent review receipt exceeds the recursion cap")
    if active is None:
        active = set()
    if is_dataclass(value) and not isinstance(value, type):
        identity = id(value)
        if identity in active:
            raise ValueError(f"{field} contains a recursive dataclass cycle")
        active.add(identity)
        try:
            record_type = type(value)
            _exact_record(value, record_type, field)
            for item in dataclass_fields(record_type):
                _require_exact_wire_tree(
                    getattr(value, item.name),
                    f"{field}.{item.name}",
                    active=active,
                    depth=depth + 1,
                )
        finally:
            active.remove(identity)
        return
    if type(value) in (tuple, list):
        if len(value) > PARENT_REVIEW_RECEIPT_MAX_ARRAY_ITEMS:
            raise ValueError("Parent review receipt array exceeds the item cap")
        identity = id(value)
        if identity in active:
            raise ValueError(f"{field} contains a recursive container cycle")
        active.add(identity)
        try:
            for index, item in enumerate(value):
                _require_exact_wire_tree(
                    item,
                    f"{field}[{index}]",
                    active=active,
                    depth=depth + 1,
                )
        finally:
            active.remove(identity)
        return
    if type(value) is dict:
        identity = id(value)
        if identity in active:
            raise ValueError(f"{field} contains a recursive mapping cycle")
        active.add(identity)
        try:
            for key, item in value.items():
                _require_exact_wire_tree(
                    key,
                    f"{field}.key",
                    active=active,
                    depth=depth + 1,
                )
                _require_exact_wire_tree(
                    item,
                    f"{field}[{key!r}]",
                    active=active,
                    depth=depth + 1,
                )
        finally:
            active.remove(identity)
        return
    if isinstance(value, Enum):
        return
    if type(value) is str:
        if len(value.encode("utf-8")) > PARENT_REVIEW_RECEIPT_MAX_STRING_BYTES:
            raise ValueError("Parent review receipt string exceeds the 1 MiB cap")
        return
    if value is None or type(value) in (int, float, bool):
        return
    raise TypeError(
        f"{field} contains a non-exact wire value of type {type(value).__name__}"
    )


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha256(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA256.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _git_sha1(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_GIT_SHA1.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase Git SHA-1")
    return result


def _relative_path(value: object, field: str) -> str:
    result = _text(value, field)
    if "\x00" in result or "\\" in result:
        raise ValueError(f"{field} must be a canonical repository-relative path")
    path = PurePosixPath(result)
    if (
        path.is_absolute()
        or path.as_posix() != result
        or "." in path.parts
        or ".." in path.parts
    ):
        raise ValueError(f"{field} must be a canonical repository-relative path")
    return result


def _reviewed_path_closure(
    value: object,
) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple or not value:
        raise TypeError("reviewed_path_closure must be a non-empty exact tuple")
    result: list[tuple[str, str]] = []
    paths: list[str] = []
    for index, entry in enumerate(value):
        if type(entry) is not tuple or len(entry) != 2:
            raise TypeError(
                f"reviewed_path_closure[{index}] must be an exact path/SHA pair"
            )
        path = _relative_path(
            entry[0],
            f"reviewed_path_closure[{index}].relative_path",
        )
        raw_sha = _sha256(
            entry[1],
            f"reviewed_path_closure[{index}].raw_sha256",
        )
        paths.append(path)
        result.append((path, raw_sha))
    if tuple(paths) != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
        raise ValueError("reviewed_path_closure is not in UTF-8 path order")
    if len(paths) != len(set(paths)):
        raise ValueError("reviewed_path_closure contains duplicate paths")
    return tuple(result)


def _reviewed_path_closure_root_sha(
    reviewed_path_closure: tuple[tuple[str, str], ...],
) -> str:
    from .parent_candidate_v3 import reviewed_path_closure_v1_payload

    return canonical_sha(reviewed_path_closure_v1_payload(reviewed_path_closure))


def openssh_ed25519_public_key_wire(public_key_text: str) -> bytes:
    """Decode the one canonical ``ssh-ed25519 <base64>`` public-key line."""

    text = _text(public_key_text, "OpenSSH Ed25519 public key")
    if text != text.strip() or "\n" in text or "\r" in text:
        raise ValueError("OpenSSH Ed25519 public key has surrounding whitespace")
    parts = text.split(" ")
    if len(parts) != 2 or parts[0] != "ssh-ed25519" or not parts[1]:
        raise ValueError("OpenSSH Ed25519 public key is not one canonical line")
    encoded = parts[1]
    try:
        wire = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("OpenSSH Ed25519 public key is not strict base64") from exc
    if base64.b64encode(wire).decode("ascii") != encoded:
        raise ValueError("OpenSSH Ed25519 public key base64 is not canonical")
    if len(wire) != 51:
        raise ValueError("OpenSSH Ed25519 wire blob has the wrong size")
    algorithm_size = int.from_bytes(wire[:4], "big")
    algorithm_end = 4 + algorithm_size
    if algorithm_size != 11 or wire[4:algorithm_end] != b"ssh-ed25519":
        raise ValueError("OpenSSH Ed25519 wire algorithm drifted")
    if algorithm_end + 4 > len(wire):
        raise ValueError("OpenSSH Ed25519 wire key length is missing")
    key_size = int.from_bytes(wire[algorithm_end : algorithm_end + 4], "big")
    key_start = algorithm_end + 4
    if key_size != 32 or key_start + key_size != len(wire):
        raise ValueError("OpenSSH Ed25519 wire key is not exactly 32 bytes")
    return wire


def openssh_sha256_fingerprint(public_key_text: str) -> str:
    """Return the canonical OpenSSH SHA-256 fingerprint of the wire blob."""

    wire = openssh_ed25519_public_key_wire(public_key_text)
    encoded = base64.b64encode(hashlib.sha256(wire).digest()).decode("ascii")
    return "SHA256:" + encoded.rstrip("=")


def _fingerprint(value: object, field: str) -> str:
    result = _text(value, field)
    if _OPENSSH_SHA256_FINGERPRINT.fullmatch(result) is None:
        raise ValueError(f"{field} is not a canonical OpenSSH SHA-256 fingerprint")
    encoded = result.removeprefix("SHA256:")
    try:
        digest = base64.b64decode(encoded + "=", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field} is not a canonical OpenSSH fingerprint") from exc
    if (
        len(digest) != 32
        or base64.b64encode(digest).decode("ascii").rstrip("=") != encoded
    ):
        raise ValueError(f"{field} is not a canonical OpenSSH fingerprint")
    return result


def verify_parent_v3_reviewer_key_registry(
    registry: tuple[tuple[str, str, str, str], ...],
) -> tuple[tuple[str, str, str, str], ...]:
    """Validate either the explicit pre-P empty state or the complete C1 registry."""

    if type(registry) is not tuple:
        raise TypeError("reviewer registry must be an exact tuple")
    if not registry:
        return registry
    if len(registry) != len(PARENT_V3_REVIEW_ROLES):
        raise ValueError("reviewer registry must contain both frozen roles")
    reviewer_ids: list[str] = []
    key_ids: list[str] = []
    public_wires: list[bytes] = []
    for index, entry in enumerate(registry):
        if type(entry) is not tuple or len(entry) != 4:
            raise TypeError(
                f"reviewer registry[{index}] must be an exact four-string tuple"
            )
        role, reviewer_id, key_id, public_key_text = entry
        if type(role) is not str or role != PARENT_V3_REVIEW_ROLES[index]:
            raise ValueError("reviewer registry role order drifted")
        identity = _text(reviewer_id, f"reviewer registry[{index}].reviewer_id")
        if identity != identity.strip():
            raise ValueError("reviewer registry identity is not canonical")
        fingerprint = _fingerprint(
            key_id,
            f"reviewer registry[{index}].reviewer_key_id",
        )
        wire = openssh_ed25519_public_key_wire(public_key_text)
        if fingerprint != openssh_sha256_fingerprint(public_key_text):
            raise ValueError("reviewer registry fingerprint does not match its key")
        reviewer_ids.append(identity)
        key_ids.append(fingerprint)
        public_wires.append(wire)
    if len(set(reviewer_ids)) != len(reviewer_ids):
        raise ValueError("reviewer registry contains a duplicate identity")
    if len(set(key_ids)) != len(key_ids) or len(set(public_wires)) != len(public_wires):
        raise ValueError("reviewer registry contains a duplicate key")
    return registry


def _validate_signature_armor(value: object) -> str:
    armor = _text(value, "signature_armor")
    try:
        armor.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("signature_armor must be exact ASCII") from exc
    if "\r" in armor or not armor.endswith("\n"):
        raise ValueError("signature_armor must use canonical LF framing")
    lines = armor.split("\n")
    if (
        len(lines) < 4
        or lines[0] != _SSH_SIGNATURE_BEGIN
        or lines[-2] != _SSH_SIGNATURE_END
        or lines[-1] != ""
    ):
        raise ValueError("signature_armor has the wrong OpenSSH framing")
    encoded_lines = lines[1:-2]
    if (
        not encoded_lines
        or any(not line or len(line) > 70 for line in encoded_lines)
        or any(len(line) != 70 for line in encoded_lines[:-1])
    ):
        raise ValueError("signature_armor has non-canonical base64 wrapping")
    encoded = "".join(encoded_lines)
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("signature_armor is not strict base64") from exc
    if (
        not decoded.startswith(b"SSHSIG")
        or base64.b64encode(decoded).decode("ascii") != encoded
    ):
        raise ValueError("signature_armor is not a canonical SSHSIG blob")
    return armor


@dataclass(frozen=True)
class SignedSourceRefV2:
    source_ref_schema_version: str
    source_role: str
    source_scope: str
    relative_path: str
    raw_sha256: str
    preparation_commit_sha: str
    signing_commit_sha: str
    source_ref_sha: str

    def __post_init__(self) -> None:
        if self.source_ref_schema_version != SIGNED_SOURCE_REF_V2_SCHEMA_VERSION:
            raise ValueError("signed source-ref schema drifted")
        relative_path = _relative_path(self.relative_path, "relative_path")
        expected = {
            item[0]: item[1:] for item in PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS
        }
        if expected.get(relative_path) != (self.source_role, self.source_scope):
            raise ValueError("signed source-ref role/scope/path drifted")
        _sha256(self.raw_sha256, "raw_sha256")
        _git_sha1(self.preparation_commit_sha, "preparation_commit_sha")
        _git_sha1(self.signing_commit_sha, "signing_commit_sha")
        _sha256(self.source_ref_sha, "source_ref_sha")


def signed_source_ref_v2_payload(
    reference: SignedSourceRefV2,
) -> dict[str, object]:
    _exact_record(reference, SignedSourceRefV2, "signed source ref")
    reference.__post_init__()
    return {
        "source_ref_schema_version": reference.source_ref_schema_version,
        "source_role": reference.source_role,
        "source_scope": reference.source_scope,
        "relative_path": reference.relative_path,
        "raw_sha256": reference.raw_sha256,
        "preparation_commit_sha": reference.preparation_commit_sha,
        "signing_commit_sha": reference.signing_commit_sha,
    }


def verify_signed_source_ref_v2(
    reference: SignedSourceRefV2,
) -> SignedSourceRefV2:
    _exact_record(reference, SignedSourceRefV2, "signed source ref")
    reference.__post_init__()
    if reference.source_ref_sha != canonical_sha(
        signed_source_ref_v2_payload(reference)
    ):
        raise ValueError("signed source-ref SHA does not match its body")
    return reference


def verify_signed_source_refs_v2(
    references: tuple[SignedSourceRefV2, ...],
) -> tuple[SignedSourceRefV2, ...]:
    if type(references) is not tuple:
        raise TypeError("signed_source_refs must be an exact tuple")
    if len(references) != len(PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS):
        raise ValueError("signed_source_refs must contain all mandatory sources")
    for index, reference in enumerate(references):
        if type(reference) is not SignedSourceRefV2:
            raise TypeError(f"signed_source_refs[{index}] is not exact")
        verify_signed_source_ref_v2(reference)
    observed = tuple(
        (item.relative_path, item.source_role, item.source_scope) for item in references
    )
    if observed != PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS:
        raise ValueError("signed_source_refs order or role/scope mapping drifted")
    return references


def signed_source_refs_v2_root_payload(
    references: tuple[SignedSourceRefV2, ...],
) -> dict[str, object]:
    verified = verify_signed_source_refs_v2(references)
    return {
        "signed_source_refs_schema_version": (
            SIGNED_SOURCE_REFS_V2_ROOT_SCHEMA_VERSION
        ),
        "entries": [
            {
                **signed_source_ref_v2_payload(reference),
                "source_ref_sha": reference.source_ref_sha,
            }
            for reference in verified
        ],
    }


@dataclass(frozen=True)
class ParentReviewReceiptV1:
    receipt_schema_version: str
    review_role: str
    reviewer_id: str
    reviewer_key_id: str
    signature_algorithm: str
    preparation_commit_sha: str
    reviewed_candidate_sha: str
    reviewed_path_closure: tuple[tuple[str, str], ...]
    reviewed_path_closure_sha: str
    verdict: str
    signed_statement_sha: str
    signature_armor: str
    receipt_sha: str

    def __post_init__(self) -> None:
        if self.receipt_schema_version != PARENT_REVIEW_RECEIPT_V1_SCHEMA_VERSION:
            raise ValueError("Parent review-receipt schema drifted")
        if self.review_role not in PARENT_V3_REVIEW_ROLES:
            raise ValueError("Parent review role is not frozen")
        reviewer_id = _text(self.reviewer_id, "reviewer_id")
        if reviewer_id != reviewer_id.strip():
            raise ValueError("reviewer_id is not canonical")
        _fingerprint(self.reviewer_key_id, "reviewer_key_id")
        if self.signature_algorithm != PARENT_V3_REVIEW_SIGNATURE_ALGORITHM:
            raise ValueError("Parent review signature algorithm drifted")
        _git_sha1(self.preparation_commit_sha, "preparation_commit_sha")
        _sha256(self.reviewed_candidate_sha, "reviewed_candidate_sha")
        _reviewed_path_closure(self.reviewed_path_closure)
        _sha256(
            self.reviewed_path_closure_sha,
            "reviewed_path_closure_sha",
        )
        if self.verdict != "PASS":
            raise ValueError("Parent review verdict must be PASS")
        _sha256(self.signed_statement_sha, "signed_statement_sha")
        _validate_signature_armor(self.signature_armor)
        _sha256(self.receipt_sha, "receipt_sha")


def parent_review_receipt_v1_signed_statement_payload(
    receipt: ParentReviewReceiptV1,
) -> dict[str, object]:
    """Canonical bytes signed by the reviewer's Ed25519 key."""

    _exact_record(receipt, ParentReviewReceiptV1, "Parent review receipt")
    receipt.__post_init__()
    closure = _reviewed_path_closure(receipt.reviewed_path_closure)
    return {
        "receipt_schema_version": receipt.receipt_schema_version,
        "review_role": receipt.review_role,
        "reviewer_id": receipt.reviewer_id,
        "reviewer_key_id": receipt.reviewer_key_id,
        "signature_algorithm": receipt.signature_algorithm,
        "preparation_commit_sha": receipt.preparation_commit_sha,
        "reviewed_candidate_sha": receipt.reviewed_candidate_sha,
        "reviewed_path_closure": [list(item) for item in closure],
        "reviewed_path_closure_sha": receipt.reviewed_path_closure_sha,
        "verdict": receipt.verdict,
    }


def parent_review_receipt_v1_payload(
    receipt: ParentReviewReceiptV1,
) -> dict[str, object]:
    """Canonical receipt body excluding only ``receipt_sha``."""

    statement = parent_review_receipt_v1_signed_statement_payload(receipt)
    return {
        **statement,
        "signed_statement_sha": receipt.signed_statement_sha,
        "signature_armor": receipt.signature_armor,
    }


def verify_parent_review_receipt_v1(
    receipt: ParentReviewReceiptV1,
) -> ParentReviewReceiptV1:
    _exact_record(receipt, ParentReviewReceiptV1, "Parent review receipt")
    _require_exact_wire_tree(receipt, "Parent review receipt")
    receipt.__post_init__()
    closure_root = _reviewed_path_closure_root_sha(receipt.reviewed_path_closure)
    if receipt.reviewed_path_closure_sha != closure_root:
        raise ValueError("reviewed path-closure SHA does not match its body")
    if receipt.signed_statement_sha != canonical_sha(
        parent_review_receipt_v1_signed_statement_payload(receipt)
    ):
        raise ValueError("signed-statement SHA does not match its body")
    if receipt.receipt_sha != canonical_sha(parent_review_receipt_v1_payload(receipt)):
        raise ValueError("review receipt SHA does not match its body")
    encoded = _canonical_json_line(
        _parent_review_receipt_v1_full_payload_unchecked(receipt)
    )
    if len(encoded) > PARENT_REVIEW_RECEIPT_MAX_BYTES:
        raise ValueError("Parent review receipt exceeds the 4 MiB cap")
    return receipt


def _parent_review_receipt_v1_full_payload_unchecked(
    receipt: ParentReviewReceiptV1,
) -> dict[str, object]:
    return {
        **parent_review_receipt_v1_payload(receipt),
        "receipt_sha": receipt.receipt_sha,
    }


def _parent_review_receipt_v1_full_payload(
    receipt: ParentReviewReceiptV1,
) -> dict[str, object]:
    verified = verify_parent_review_receipt_v1(receipt)
    return _parent_review_receipt_v1_full_payload_unchecked(verified)


def _canonical_json_line(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def parent_review_receipt_v1_canonical_json_bytes(
    receipt: ParentReviewReceiptV1,
) -> bytes:
    payload = _parent_review_receipt_v1_full_payload(receipt)
    encoded = _canonical_json_line(payload)
    if len(encoded) > PARENT_REVIEW_RECEIPT_MAX_BYTES:
        raise ValueError("Parent review receipt exceeds the 4 MiB cap")
    return encoded


def _reject_duplicate_json_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise ValueError("Parent review receipt JSON has a non-string key")
        if key in result:
            raise ValueError("Parent review receipt JSON contains duplicate keys")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"Parent review receipt JSON contains {value}")


def _validate_json_resource_caps(
    value: object,
    *,
    depth: int = 1,
) -> None:
    if depth > PARENT_REVIEW_RECEIPT_MAX_DEPTH:
        raise ValueError("Parent review receipt exceeds the recursion cap")
    if type(value) is str:
        if len(value.encode("utf-8")) > PARENT_REVIEW_RECEIPT_MAX_STRING_BYTES:
            raise ValueError("Parent review receipt string exceeds the 1 MiB cap")
        return
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Parent review receipt contains a non-finite number")
        return
    if type(value) is list:
        if len(value) > PARENT_REVIEW_RECEIPT_MAX_ARRAY_ITEMS:
            raise ValueError("Parent review receipt array exceeds the item cap")
        for item in value:
            _validate_json_resource_caps(item, depth=depth + 1)
        return
    if type(value) is dict:
        for key, item in value.items():
            _validate_json_resource_caps(key, depth=depth + 1)
            _validate_json_resource_caps(item, depth=depth + 1)
        return
    raise TypeError("Parent review receipt JSON contains an unsupported value")


def parse_parent_review_receipt_v1_json(
    raw: bytes,
) -> ParentReviewReceiptV1:
    """Parse one bounded, canonical, duplicate-free receipt JSON line."""

    if type(raw) is not bytes:
        raise TypeError("Parent review receipt file must be exact bytes")
    if not raw or len(raw) > PARENT_REVIEW_RECEIPT_MAX_BYTES:
        raise ValueError("Parent review receipt file has an invalid size")
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise ValueError("Parent review receipt must be exactly one JSON line")
    try:
        text = raw[:-1].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Parent review receipt is not strict UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("Parent review receipt contains a BOM")
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_pairs,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError("Parent review receipt is not strict JSON") from exc
    _validate_json_resource_caps(payload)
    if type(payload) is not dict:
        raise TypeError("Parent review receipt JSON must be an exact object")
    expected_fields = tuple(
        item.name for item in dataclass_fields(ParentReviewReceiptV1)
    )
    if set(payload) != set(expected_fields):
        raise ValueError("Parent review receipt JSON fields drifted")
    try:
        canonical = (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Parent review receipt is not canonical JSON") from exc
    if canonical != raw:
        raise ValueError("Parent review receipt JSON bytes are not canonical")
    closure_value = payload["reviewed_path_closure"]
    if type(closure_value) is not list:
        raise TypeError("reviewed_path_closure JSON value must be an array")
    closure_entries: list[tuple[str, str]] = []
    for index, entry in enumerate(closure_value):
        if type(entry) is not list or len(entry) != 2:
            raise TypeError(f"reviewed_path_closure[{index}] JSON value is not a pair")
        if any(type(item) is not str for item in entry):
            raise TypeError(
                f"reviewed_path_closure[{index}] must contain exact strings"
            )
        closure_entries.append((entry[0], entry[1]))
    hydrated = dict(payload)
    hydrated["reviewed_path_closure"] = tuple(closure_entries)
    try:
        receipt = ParentReviewReceiptV1(**hydrated)
    except (TypeError, ValueError) as exc:
        raise ValueError("Parent review receipt contract is invalid") from exc
    return verify_parent_review_receipt_v1(receipt)


def _validate_parent_candidate_v3(candidate: object) -> object:
    from .parent_candidate_v3 import (
        ParentFreezeCandidateV3Manifest,
        _verify_parent_candidate_v3_roots_and_registry,
        parent_freeze_candidate_v3_manifest_payload,
        parent_v3_source_closure_v1_payload,
    )

    _exact_record(candidate, ParentFreezeCandidateV3Manifest, "Parent-v3 candidate")
    _require_exact_wire_tree(candidate, "Parent-v3 candidate")
    candidate.__post_init__()
    _verify_parent_candidate_v3_roots_and_registry(candidate)
    expected_source_root = canonical_sha(
        parent_v3_source_closure_v1_payload(
            candidate.preparation_commit_sha,
            candidate.source_closure,
        )
    )
    if candidate.source_closure_sha != expected_source_root:
        raise ValueError("Parent-v3 candidate source-closure root drifted")
    if candidate.candidate_sha != canonical_sha(
        parent_freeze_candidate_v3_manifest_payload(candidate)
    ):
        raise ValueError("Parent-v3 candidate SHA does not match its body")
    return candidate


def verify_parent_review_receipts_v1(
    receipts: tuple[ParentReviewReceiptV1, ...],
    candidate: ParentFreezeCandidateV3Manifest,
) -> tuple[ParentReviewReceiptV1, ...]:
    """Bind both frozen roles to the exact projection of one P candidate."""

    reviewed_candidate = _validate_parent_candidate_v3(candidate)
    if type(receipts) is not tuple:
        raise TypeError("review_receipts must be an exact tuple")
    if len(receipts) != len(PARENT_V3_REVIEW_ROLES):
        raise ValueError("review_receipts must contain both frozen roles")
    for index, receipt in enumerate(receipts):
        if type(receipt) is not ParentReviewReceiptV1:
            raise TypeError(f"review_receipts[{index}] is not exact")
        verify_parent_review_receipt_v1(receipt)
        if receipt.review_role != PARENT_V3_REVIEW_ROLES[index]:
            raise ValueError("review_receipts role order drifted")
    expected_closure = tuple(
        (path, raw_sha) for path, _mode, raw_sha in reviewed_candidate.source_closure
    )
    expected_closure_root = _reviewed_path_closure_root_sha(expected_closure)
    for receipt in receipts:
        if receipt.preparation_commit_sha != reviewed_candidate.preparation_commit_sha:
            raise ValueError("review receipt preparation commit drifted")
        if receipt.reviewed_candidate_sha != reviewed_candidate.candidate_sha:
            raise ValueError("review receipt candidate root drifted")
        if receipt.reviewed_path_closure != expected_closure:
            raise ValueError(
                "review receipt path closure is not the candidate projection"
            )
        if receipt.reviewed_path_closure_sha != expected_closure_root:
            raise ValueError("review receipt path-closure root drifted")
    if len({item.reviewer_id for item in receipts}) != len(receipts):
        raise ValueError("review receipts reuse a reviewer identity")
    if len({item.reviewer_key_id for item in receipts}) != len(receipts):
        raise ValueError("review receipts reuse a reviewer key")
    if len({item.receipt_sha for item in receipts}) != len(receipts):
        raise ValueError("review receipts have duplicate roots")
    return receipts


@dataclass(frozen=True)
class ParentSigningAuditV1:
    audit_schema_version: str
    preparation_commit_sha: str
    signing_commit_sha: str
    review_receipt_shas: tuple[str, ...]
    diff_digest: str
    diff_allowlist_id: str
    signed_source_refs_root_sha: str
    reviewed_candidate_sha: str
    reviewed_path_closure_sha: str
    source_closure_sha: str
    audit_sha: str

    def __post_init__(self) -> None:
        if self.audit_schema_version != PARENT_SIGNING_AUDIT_V1_SCHEMA_VERSION:
            raise ValueError("Parent signing-audit schema drifted")
        preparation = _git_sha1(
            self.preparation_commit_sha,
            "preparation_commit_sha",
        )
        signing = _git_sha1(self.signing_commit_sha, "signing_commit_sha")
        if preparation == signing:
            raise ValueError("preparation and signing commits must differ")
        if type(self.review_receipt_shas) is not tuple or len(
            self.review_receipt_shas
        ) != len(PARENT_V3_REVIEW_ROLES):
            raise TypeError("review_receipt_shas must be the exact two-role tuple")
        for index, receipt_sha in enumerate(self.review_receipt_shas):
            _sha256(receipt_sha, f"review_receipt_shas[{index}]")
        if len(set(self.review_receipt_shas)) != len(self.review_receipt_shas):
            raise ValueError("review_receipt_shas contain duplicate roots")
        _sha256(self.diff_digest, "diff_digest")
        if self.diff_allowlist_id != PARENT_V3_SIGNING_DIFF_ALLOWLIST_ID:
            raise ValueError("Parent signing diff allowlist ID drifted")
        for field in (
            "signed_source_refs_root_sha",
            "reviewed_candidate_sha",
            "reviewed_path_closure_sha",
            "source_closure_sha",
            "audit_sha",
        ):
            _sha256(getattr(self, field), field)


def parent_signing_audit_v1_payload(
    audit: ParentSigningAuditV1,
) -> dict[str, object]:
    _exact_record(audit, ParentSigningAuditV1, "Parent signing audit")
    audit.__post_init__()
    return {
        "audit_schema_version": audit.audit_schema_version,
        "preparation_commit_sha": audit.preparation_commit_sha,
        "signing_commit_sha": audit.signing_commit_sha,
        "review_receipt_shas": list(audit.review_receipt_shas),
        "diff_digest": audit.diff_digest,
        "diff_allowlist_id": audit.diff_allowlist_id,
        "signed_source_refs_root_sha": audit.signed_source_refs_root_sha,
        "reviewed_candidate_sha": audit.reviewed_candidate_sha,
        "reviewed_path_closure_sha": audit.reviewed_path_closure_sha,
        "source_closure_sha": audit.source_closure_sha,
    }


def verify_parent_signing_audit_v1(
    audit: ParentSigningAuditV1,
) -> ParentSigningAuditV1:
    _exact_record(audit, ParentSigningAuditV1, "Parent signing audit")
    audit.__post_init__()
    if audit.audit_sha != canonical_sha(parent_signing_audit_v1_payload(audit)):
        raise ValueError("Parent signing-audit SHA does not match its body")
    return audit


def verify_parent_v3_signing_bundle(
    candidate: ParentFreezeCandidateV3Manifest,
    signed_source_refs: tuple[SignedSourceRefV2, ...],
    review_receipts: tuple[ParentReviewReceiptV1, ...],
    signing_audit: ParentSigningAuditV1,
) -> ParentSigningAuditV1:
    reviewed_candidate = _validate_parent_candidate_v3(candidate)
    references = verify_signed_source_refs_v2(signed_source_refs)
    receipts = verify_parent_review_receipts_v1(
        review_receipts,
        reviewed_candidate,
    )
    audit = verify_parent_signing_audit_v1(signing_audit)
    preparation_commits = {item.preparation_commit_sha for item in references}
    signing_commits = {item.signing_commit_sha for item in references}
    if preparation_commits != {reviewed_candidate.preparation_commit_sha}:
        raise ValueError("signed source refs do not bind the candidate P")
    if signing_commits != {audit.signing_commit_sha}:
        raise ValueError("signed source refs do not bind the audited S")
    if audit.preparation_commit_sha != reviewed_candidate.preparation_commit_sha:
        raise ValueError("signing audit preparation commit drifted")
    if audit.review_receipt_shas != tuple(item.receipt_sha for item in receipts):
        raise ValueError("signing audit receipt roots drifted")
    expected_refs_root = canonical_sha(signed_source_refs_v2_root_payload(references))
    if audit.signed_source_refs_root_sha != expected_refs_root:
        raise ValueError("signing audit signed-source root drifted")
    if audit.reviewed_candidate_sha != reviewed_candidate.candidate_sha:
        raise ValueError("signing audit candidate root drifted")
    if audit.reviewed_path_closure_sha != receipts[0].reviewed_path_closure_sha:
        raise ValueError("signing audit reviewed path root drifted")
    if audit.source_closure_sha != reviewed_candidate.source_closure_sha:
        raise ValueError("signing audit source-closure root drifted")
    return audit


@dataclass(frozen=True)
class ParentFreezeV3Manifest:
    parent_freeze_schema_version: str
    authority_state: Literal["CURRENT_PARENT_V3_ISSUED"]
    program_id: Literal["projective-rule-space-v3m0-v3"]
    preparation_commit_sha: str
    signing_commit_sha: str
    reviewed_candidate_v3: ParentFreezeCandidateV3Manifest
    signed_source_refs: tuple[SignedSourceRefV2, ...]
    review_receipts: tuple[ParentReviewReceiptV1, ...]
    signing_audit: ParentSigningAuditV1
    current_application_registry_sha: str
    parent_freeze_v3_sha: str

    def __post_init__(self) -> None:
        from .parent_candidate_v3 import ParentFreezeCandidateV3Manifest

        if self.parent_freeze_schema_version != PARENT_FREEZE_V3_SCHEMA_VERSION:
            raise ValueError("Parent-v3 manifest schema drifted")
        if self.authority_state != PARENT_V3_AUTHORITY_STATE:
            raise ValueError("Parent-v3 authority state drifted")
        if self.program_id != PARENT_V3_PROGRAM_ID:
            raise ValueError("Parent-v3 program ID drifted")
        preparation = _git_sha1(
            self.preparation_commit_sha,
            "preparation_commit_sha",
        )
        signing = _git_sha1(self.signing_commit_sha, "signing_commit_sha")
        if preparation == signing:
            raise ValueError("Parent-v3 P and S must differ")
        _exact_record(
            self.reviewed_candidate_v3,
            ParentFreezeCandidateV3Manifest,
            "reviewed_candidate_v3",
        )
        if type(self.signed_source_refs) is not tuple:
            raise TypeError("signed_source_refs must be an exact tuple")
        if not all(type(item) is SignedSourceRefV2 for item in self.signed_source_refs):
            raise TypeError("signed_source_refs contain a non-exact record")
        if type(self.review_receipts) is not tuple:
            raise TypeError("review_receipts must be an exact tuple")
        if not all(
            type(item) is ParentReviewReceiptV1 for item in self.review_receipts
        ):
            raise TypeError("review_receipts contain a non-exact record")
        _exact_record(
            self.signing_audit,
            ParentSigningAuditV1,
            "signing_audit",
        )
        _sha256(
            self.current_application_registry_sha,
            "current_application_registry_sha",
        )
        _sha256(self.parent_freeze_v3_sha, "parent_freeze_v3_sha")


def parent_freeze_v3_manifest_payload(
    manifest: ParentFreezeV3Manifest,
) -> dict[str, object]:
    """Canonical Parent-v3 body excluding only its outer self hash."""

    from .parent_candidate_v3 import parent_freeze_candidate_v3_manifest_payload

    _exact_record(manifest, ParentFreezeV3Manifest, "Parent-v3 manifest")
    manifest.__post_init__()
    _require_exact_wire_tree(manifest, "Parent-v3 manifest")
    candidate = _validate_parent_candidate_v3(manifest.reviewed_candidate_v3)
    verify_parent_v3_signing_bundle(
        candidate,
        manifest.signed_source_refs,
        manifest.review_receipts,
        manifest.signing_audit,
    )
    return {
        "parent_freeze_schema_version": manifest.parent_freeze_schema_version,
        "authority_state": manifest.authority_state,
        "program_id": manifest.program_id,
        "preparation_commit_sha": manifest.preparation_commit_sha,
        "signing_commit_sha": manifest.signing_commit_sha,
        "reviewed_candidate_v3": {
            **parent_freeze_candidate_v3_manifest_payload(candidate),
            "candidate_sha": candidate.candidate_sha,
        },
        "signed_source_refs": signed_source_refs_v2_root_payload(
            manifest.signed_source_refs
        )["entries"],
        "review_receipts": [
            _parent_review_receipt_v1_full_payload(receipt)
            for receipt in manifest.review_receipts
        ],
        "signing_audit": {
            **parent_signing_audit_v1_payload(manifest.signing_audit),
            "audit_sha": manifest.signing_audit.audit_sha,
        },
        "current_application_registry_sha": (manifest.current_application_registry_sha),
    }


def verify_parent_freeze_v3_manifest(
    manifest: ParentFreezeV3Manifest,
) -> ParentFreezeV3Manifest:
    """Verify raw linked roots without issuing an opaque capability."""

    from .parent_candidate_v3 import current_application_registry_v3_payload

    _exact_record(manifest, ParentFreezeV3Manifest, "Parent-v3 manifest")
    manifest.__post_init__()
    _require_exact_wire_tree(manifest, "Parent-v3 manifest")
    candidate = _validate_parent_candidate_v3(manifest.reviewed_candidate_v3)
    if manifest.preparation_commit_sha != candidate.preparation_commit_sha:
        raise ValueError("Parent-v3 preparation commit drifted from candidate")
    if manifest.signing_commit_sha != manifest.signing_audit.signing_commit_sha:
        raise ValueError("Parent-v3 signing commit drifted from audit")
    verify_parent_v3_signing_bundle(
        candidate,
        manifest.signed_source_refs,
        manifest.review_receipts,
        manifest.signing_audit,
    )
    expected_registry_root = canonical_sha(
        current_application_registry_v3_payload(candidate)
    )
    if manifest.current_application_registry_sha != expected_registry_root:
        raise ValueError("Parent-v3 current application-registry root drifted")
    if manifest.parent_freeze_v3_sha != canonical_sha(
        parent_freeze_v3_manifest_payload(manifest)
    ):
        raise ValueError("Parent-v3 manifest SHA does not match its body")
    return manifest


__all__ = [
    "PARENT_FREEZE_V3_SCHEMA_VERSION",
    "PARENT_REVIEW_RECEIPT_MAX_ARRAY_ITEMS",
    "PARENT_REVIEW_RECEIPT_MAX_BYTES",
    "PARENT_REVIEW_RECEIPT_MAX_DEPTH",
    "PARENT_REVIEW_RECEIPT_MAX_STRING_BYTES",
    "PARENT_REVIEW_RECEIPT_V1_SCHEMA_VERSION",
    "PARENT_SIGNING_AUDIT_V1_SCHEMA_VERSION",
    "PARENT_V3_AUTHORITY_STATE",
    "PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS",
    "PARENT_V3_PROGRAM_ID",
    "PARENT_V3_REVIEW_RECEIPT_PATHS_BY_ROLE",
    "PARENT_V3_REVIEW_ROLES",
    "PARENT_V3_REVIEW_SIGNATURE_ALGORITHM",
    "PARENT_V3_REVIEW_SIGNATURE_NAMESPACE",
    "PARENT_V3_SIGNING_DIFF_ALLOWLIST_ID",
    "SIGNED_SOURCE_REF_V2_SCHEMA_VERSION",
    "SIGNED_SOURCE_REFS_V2_ROOT_SCHEMA_VERSION",
    "ParentFreezeV3Manifest",
    "ParentReviewReceiptV1",
    "ParentSigningAuditV1",
    "SignedSourceRefV2",
    "openssh_ed25519_public_key_wire",
    "openssh_sha256_fingerprint",
    "parent_freeze_v3_manifest_payload",
    "parent_review_receipt_v1_canonical_json_bytes",
    "parent_review_receipt_v1_payload",
    "parent_review_receipt_v1_signed_statement_payload",
    "parent_signing_audit_v1_payload",
    "parse_parent_review_receipt_v1_json",
    "signed_source_ref_v2_payload",
    "signed_source_refs_v2_root_payload",
    "verify_parent_review_receipt_v1",
    "verify_parent_review_receipts_v1",
    "verify_parent_freeze_v3_manifest",
    "verify_parent_signing_audit_v1",
    "verify_parent_v3_reviewer_key_registry",
    "verify_parent_v3_signing_bundle",
    "verify_signed_source_ref_v2",
    "verify_signed_source_refs_v2",
]
