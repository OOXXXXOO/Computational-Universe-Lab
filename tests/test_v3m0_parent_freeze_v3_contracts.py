from __future__ import annotations

import base64
from dataclasses import fields, replace
import hashlib
import importlib
import json
from pathlib import Path
import subprocess

import pytest

from rulespace_v3.evidence import canonical_sha


ROOT = Path(__file__).resolve().parents[1]


def _contracts():
    return importlib.import_module("rulespace_v3.parent_freeze_v3_contracts")


def _signed_source_ref(
    contracts,
    index: int = 0,
    *,
    preparation_commit_sha: str = "1" * 40,
    signing_commit_sha: str = "2" * 40,
):
    path, role, scope = contracts.PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS[index]
    provisional = contracts.SignedSourceRefV2(
        source_ref_schema_version=contracts.SIGNED_SOURCE_REF_V2_SCHEMA_VERSION,
        source_role=role,
        source_scope=scope,
        relative_path=path,
        raw_sha256=f"{index + 1:x}" * 64,
        preparation_commit_sha=preparation_commit_sha,
        signing_commit_sha=signing_commit_sha,
        source_ref_sha="0" * 64,
    )
    return replace(
        provisional,
        source_ref_sha=canonical_sha(
            contracts.signed_source_ref_v2_payload(provisional)
        ),
    )


def _signature_armor() -> str:
    encoded = base64.b64encode(b"SSHSIG" + b"\x00" * 64).decode("ascii")
    lines = [encoded[index : index + 70] for index in range(0, len(encoded), 70)]
    return (
        "-----BEGIN SSH SIGNATURE-----\n"
        + "\n".join(lines)
        + "\n-----END SSH SIGNATURE-----\n"
    )


def _review_receipt(contracts, role_index: int = 0, *, candidate_v3=None):
    candidate = importlib.import_module("rulespace_v3.parent_candidate_v3")
    if candidate_v3 is None:
        preparation_commit_sha = "1" * 40
        reviewed_candidate_sha = "2" * 64
        closure = (("alpha.py", "a" * 64), ("测量.md", "b" * 64))
    else:
        preparation_commit_sha = candidate_v3.preparation_commit_sha
        reviewed_candidate_sha = candidate_v3.candidate_sha
        closure = tuple(
            (path, raw_sha) for path, _mode, raw_sha in candidate_v3.source_closure
        )
    closure_sha = canonical_sha(candidate.reviewed_path_closure_v1_payload(closure))
    key_digest = hashlib.sha256(f"reviewer-{role_index}".encode("ascii")).digest()
    key_id = "SHA256:" + base64.b64encode(key_digest).decode("ascii").rstrip("=")
    provisional = contracts.ParentReviewReceiptV1(
        receipt_schema_version=contracts.PARENT_REVIEW_RECEIPT_V1_SCHEMA_VERSION,
        review_role=contracts.PARENT_V3_REVIEW_ROLES[role_index],
        reviewer_id=f"reviewer-{role_index + 1}",
        reviewer_key_id=key_id,
        signature_algorithm=contracts.PARENT_V3_REVIEW_SIGNATURE_ALGORITHM,
        preparation_commit_sha=preparation_commit_sha,
        reviewed_candidate_sha=reviewed_candidate_sha,
        reviewed_path_closure=closure,
        reviewed_path_closure_sha=closure_sha,
        verdict="PASS",
        signed_statement_sha="0" * 64,
        signature_armor=_signature_armor(),
        receipt_sha="0" * 64,
    )
    with_statement = replace(
        provisional,
        signed_statement_sha=canonical_sha(
            contracts.parent_review_receipt_v1_signed_statement_payload(provisional)
        ),
    )
    return replace(
        with_statement,
        receipt_sha=canonical_sha(
            contracts.parent_review_receipt_v1_payload(with_statement)
        ),
    )


def _resign_review_receipt(
    contracts,
    receipt,
    *,
    reviewer_id: str | None = None,
    reviewed_candidate_sha: str | None = None,
    reviewed_path_closure: tuple[tuple[str, str], ...] | None = None,
):
    candidate = importlib.import_module("rulespace_v3.parent_candidate_v3")
    closure = (
        receipt.reviewed_path_closure
        if reviewed_path_closure is None
        else reviewed_path_closure
    )
    provisional = replace(
        receipt,
        reviewer_id=receipt.reviewer_id if reviewer_id is None else reviewer_id,
        reviewed_candidate_sha=(
            receipt.reviewed_candidate_sha
            if reviewed_candidate_sha is None
            else reviewed_candidate_sha
        ),
        reviewed_path_closure=closure,
        reviewed_path_closure_sha=canonical_sha(
            candidate.reviewed_path_closure_v1_payload(closure)
        ),
        signed_statement_sha="0" * 64,
        receipt_sha="0" * 64,
    )
    with_statement = replace(
        provisional,
        signed_statement_sha=canonical_sha(
            contracts.parent_review_receipt_v1_signed_statement_payload(provisional)
        ),
    )
    return replace(
        with_statement,
        receipt_sha=canonical_sha(
            contracts.parent_review_receipt_v1_payload(with_statement)
        ),
    )


def _receipt_json_bytes_unchecked(contracts, receipt) -> bytes:
    payload = {
        **contracts.parent_review_receipt_v1_payload(receipt),
        "receipt_sha": receipt.receipt_sha,
    }
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


def _manifest_payload_unchecked(contracts, manifest) -> dict[str, object]:
    candidate = importlib.import_module("rulespace_v3.parent_candidate_v3")
    reviewed = manifest.reviewed_candidate_v3
    return {
        "parent_freeze_schema_version": manifest.parent_freeze_schema_version,
        "authority_state": manifest.authority_state,
        "program_id": manifest.program_id,
        "preparation_commit_sha": manifest.preparation_commit_sha,
        "signing_commit_sha": manifest.signing_commit_sha,
        "reviewed_candidate_v3": {
            **candidate.parent_freeze_candidate_v3_manifest_payload(reviewed),
            "candidate_sha": reviewed.candidate_sha,
        },
        "signed_source_refs": contracts.signed_source_refs_v2_root_payload(
            manifest.signed_source_refs
        )["entries"],
        "review_receipts": [
            {
                **contracts.parent_review_receipt_v1_payload(receipt),
                "receipt_sha": receipt.receipt_sha,
            }
            for receipt in manifest.review_receipts
        ],
        "signing_audit": {
            **contracts.parent_signing_audit_v1_payload(manifest.signing_audit),
            "audit_sha": manifest.signing_audit.audit_sha,
        },
        "current_application_registry_sha": (manifest.current_application_registry_sha),
    }


def _signing_audit(contracts, candidate_v3, references, receipts, signing_sha):
    refs_root = canonical_sha(contracts.signed_source_refs_v2_root_payload(references))
    provisional = contracts.ParentSigningAuditV1(
        audit_schema_version=contracts.PARENT_SIGNING_AUDIT_V1_SCHEMA_VERSION,
        preparation_commit_sha=candidate_v3.preparation_commit_sha,
        signing_commit_sha=signing_sha,
        review_receipt_shas=tuple(item.receipt_sha for item in receipts),
        diff_digest="3" * 64,
        diff_allowlist_id=contracts.PARENT_V3_SIGNING_DIFF_ALLOWLIST_ID,
        signed_source_refs_root_sha=refs_root,
        reviewed_candidate_sha=candidate_v3.candidate_sha,
        reviewed_path_closure_sha=receipts[0].reviewed_path_closure_sha,
        source_closure_sha=candidate_v3.source_closure_sha,
        audit_sha="0" * 64,
    )
    return replace(
        provisional,
        audit_sha=canonical_sha(contracts.parent_signing_audit_v1_payload(provisional)),
    )


@pytest.fixture(scope="module")
def candidate_v3_fixture():
    candidate = importlib.import_module("rulespace_v3.parent_candidate_v3")
    commit_sha = subprocess.run(
        ("git", "rev-list", "--no-merges", "-n", "1", "HEAD"),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    return candidate._replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit(
        commit_sha
    )


def test_slice_a3_1_exact_schemas_and_preparation_placeholders() -> None:
    contracts = _contracts()
    reviewer_keys = importlib.import_module("rulespace_v3.parent_reviewer_keys_v1")
    literals = importlib.import_module("rulespace_v3.parent_signing_literals_v1")

    assert tuple(item.name for item in fields(contracts.SignedSourceRefV2)) == (
        "source_ref_schema_version",
        "source_role",
        "source_scope",
        "relative_path",
        "raw_sha256",
        "preparation_commit_sha",
        "signing_commit_sha",
        "source_ref_sha",
    )
    assert tuple(item.name for item in fields(contracts.ParentReviewReceiptV1)) == (
        "receipt_schema_version",
        "review_role",
        "reviewer_id",
        "reviewer_key_id",
        "signature_algorithm",
        "preparation_commit_sha",
        "reviewed_candidate_sha",
        "reviewed_path_closure",
        "reviewed_path_closure_sha",
        "verdict",
        "signed_statement_sha",
        "signature_armor",
        "receipt_sha",
    )
    assert tuple(item.name for item in fields(contracts.ParentSigningAuditV1)) == (
        "audit_schema_version",
        "preparation_commit_sha",
        "signing_commit_sha",
        "review_receipt_shas",
        "diff_digest",
        "diff_allowlist_id",
        "signed_source_refs_root_sha",
        "reviewed_candidate_sha",
        "reviewed_path_closure_sha",
        "source_closure_sha",
        "audit_sha",
    )
    assert tuple(item.name for item in fields(contracts.ParentFreezeV3Manifest)) == (
        "parent_freeze_schema_version",
        "authority_state",
        "program_id",
        "preparation_commit_sha",
        "signing_commit_sha",
        "reviewed_candidate_v3",
        "signed_source_refs",
        "review_receipts",
        "signing_audit",
        "current_application_registry_sha",
        "parent_freeze_v3_sha",
    )
    assert all(
        record.__dataclass_params__.frozen is True
        for record in (
            contracts.SignedSourceRefV2,
            contracts.ParentReviewReceiptV1,
            contracts.ParentSigningAuditV1,
            contracts.ParentFreezeV3Manifest,
        )
    )
    assert reviewer_keys.PARENT_V3_TRUSTED_REVIEWER_KEYS_V1 == ()
    assert literals.PARENT_V3_PREPARATION_COMMIT_SHA is None
    assert literals.PARENT_V3_REVIEWED_CANDIDATE_SHA256 is None
    assert literals.PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256 is None
    assert literals.PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH == ()
    assert literals.PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE == ()
    assert (
        (ROOT / "rulespace_v3/parent_signing_literals_v1.py").read_bytes()
        == b"""\
from __future__ import annotations

PARENT_V3_PREPARATION_COMMIT_SHA: str | None = None
PARENT_V3_REVIEWED_CANDIDATE_SHA256: str | None = None
PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256: str | None = None
PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH: tuple[tuple[str, str], ...] = ()
PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE: tuple[tuple[str, str], ...] = ()
"""
    )


def test_slice_a3_1_signed_source_ref_is_exact_and_self_hashed() -> None:
    contracts = _contracts()
    reference = _signed_source_ref(contracts)

    assert contracts.verify_signed_source_ref_v2(reference) is reference
    assert contracts.signed_source_ref_v2_payload(reference) == {
        "source_ref_schema_version": contracts.SIGNED_SOURCE_REF_V2_SCHEMA_VERSION,
        "source_role": "SIGNED_INCREMENTAL_ERRATUM",
        "source_scope": "C05_C18_SCENARIO_RESPONSE_GEOMETRY",
        "relative_path": ("docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md"),
        "raw_sha256": "1" * 64,
        "preparation_commit_sha": "1" * 40,
        "signing_commit_sha": "2" * 40,
    }

    with pytest.raises(ValueError):
        contracts.verify_signed_source_ref_v2(
            replace(reference, source_ref_sha="f" * 64)
        )
    with pytest.raises(ValueError):
        replace(reference, preparation_commit_sha="a" * 64)
    with pytest.raises(ValueError):
        replace(reference, raw_sha256="a" * 40)

    class HostileRef(contracts.SignedSourceRefV2):
        pass

    with pytest.raises(TypeError):
        contracts.verify_signed_source_ref_v2(HostileRef(**vars(reference)))


def test_slice_a3_1_signed_source_tuple_has_one_frozen_order_and_root_owner() -> None:
    contracts = _contracts()
    references = tuple(
        _signed_source_ref(contracts, index)
        for index in range(len(contracts.PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS))
    )

    assert contracts.verify_signed_source_refs_v2(references) is references
    payload = contracts.signed_source_refs_v2_root_payload(references)
    assert payload["signed_source_refs_schema_version"] == (
        "v3m0.signed-source-ref-tuple.v1"
    )
    assert [entry["relative_path"] for entry in payload["entries"]] == [
        item[0] for item in contracts.PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS
    ]
    assert all("source_ref_sha" in entry for entry in payload["entries"])

    with pytest.raises(ValueError):
        contracts.verify_signed_source_refs_v2(tuple(reversed(references)))
    with pytest.raises(TypeError):
        contracts.verify_signed_source_refs_v2(tuple(vars(item) for item in references))

    class HostileTuple(tuple):
        pass

    with pytest.raises(TypeError):
        contracts.verify_signed_source_refs_v2(HostileTuple(references))


def test_slice_a3_2_openssh_ed25519_wire_and_fingerprint_match_ssh_keygen(
    tmp_path: Path,
) -> None:
    contracts = _contracts()
    public_key_text = (
        "ssh-ed25519 "
        "AAAAC3NzaC1lZDI1NTE5AAAAINdamAGCsQq31Uv+08lkBzoO4XLz2qYjJa8CGmj3B1Ea"
    )
    expected_fingerprint = "SHA256:bbXpuKG6zhzdmnxq256TlqzFBzRl2f6OOg722cYNbU8"

    wire = contracts.openssh_ed25519_public_key_wire(public_key_text)
    assert len(wire) == 51
    assert contracts.openssh_sha256_fingerprint(public_key_text) == (
        expected_fingerprint
    )
    public_key_path = tmp_path / "reviewer.pub"
    public_key_path.write_text(public_key_text + "\n", encoding="ascii")
    completed = subprocess.run(
        ("ssh-keygen", "-E", "sha256", "-lf", public_key_path),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert completed.stderr == ""
    assert completed.stdout.split()[1] == expected_fingerprint

    for attacked in (
        " " + public_key_text,
        public_key_text + " ",
        public_key_text + "\n",
        public_key_text + " comment",
        public_key_text.replace("ssh-ed25519", "ssh-rsa", 1),
        public_key_text[:-1] + "!",
    ):
        with pytest.raises((TypeError, ValueError)):
            contracts.openssh_ed25519_public_key_wire(attacked)

    decoded = base64.b64decode(public_key_text.split()[1])
    for attacked_wire in (
        decoded + b"x",
        b"\x00\x00\x00\x0a" + decoded[4:],
        decoded[:15] + b"\x00\x00\x00\x1f" + decoded[19:-1],
    ):
        attacked = "ssh-ed25519 " + base64.b64encode(attacked_wire).decode("ascii")
        with pytest.raises(ValueError):
            contracts.openssh_ed25519_public_key_wire(attacked)


def test_slice_a3_2_reviewer_registry_is_exact_or_explicitly_pre_p_empty() -> None:
    contracts = _contracts()
    public_key_text = (
        "ssh-ed25519 "
        "AAAAC3NzaC1lZDI1NTE5AAAAINdamAGCsQq31Uv+08lkBzoO4XLz2qYjJa8CGmj3B1Ea"
    )
    fingerprint = contracts.openssh_sha256_fingerprint(public_key_text)
    roles = contracts.PARENT_V3_REVIEW_ROLES
    complete = (
        (roles[0], "math-reviewer", fingerprint, public_key_text),
        (
            roles[1],
            "authority-reviewer",
            "SHA256:" + "A" * 43,
            public_key_text,
        ),
    )

    assert contracts.verify_parent_v3_reviewer_key_registry(()) == ()
    with pytest.raises(ValueError, match="fingerprint"):
        contracts.verify_parent_v3_reviewer_key_registry(complete)
    for attacked in (
        (complete[0], complete[0]),
        tuple(reversed(complete)),
        (complete[0],),
        [*complete],
    ):
        with pytest.raises((TypeError, ValueError)):
            contracts.verify_parent_v3_reviewer_key_registry(attacked)


def test_slice_a3_2_receipt_payloads_and_canonical_json_round_trip() -> None:
    contracts = _contracts()
    receipt = _review_receipt(contracts)

    assert contracts.verify_parent_review_receipt_v1(receipt) is receipt
    statement = contracts.parent_review_receipt_v1_signed_statement_payload(receipt)
    assert tuple(statement) == (
        "receipt_schema_version",
        "review_role",
        "reviewer_id",
        "reviewer_key_id",
        "signature_algorithm",
        "preparation_commit_sha",
        "reviewed_candidate_sha",
        "reviewed_path_closure",
        "reviewed_path_closure_sha",
        "verdict",
    )
    payload = contracts.parent_review_receipt_v1_payload(receipt)
    assert tuple(payload)[-2:] == ("signed_statement_sha", "signature_armor")
    assert payload["reviewed_path_closure"] == [
        ["alpha.py", "a" * 64],
        ["测量.md", "b" * 64],
    ]

    raw = contracts.parent_review_receipt_v1_canonical_json_bytes(receipt)
    expected = {**payload, "receipt_sha": receipt.receipt_sha}
    assert raw == (
        json.dumps(
            expected,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    assert contracts.parse_parent_review_receipt_v1_json(raw) == receipt

    for changes in (
        {"signed_statement_sha": "f" * 64},
        {"receipt_sha": "f" * 64},
        {"reviewed_path_closure": tuple(reversed(receipt.reviewed_path_closure))},
        {"reviewed_path_closure_sha": "f" * 64},
        {"verdict": "FAIL"},
        {"signature_algorithm": "ed25519"},
    ):
        with pytest.raises((TypeError, ValueError)):
            contracts.verify_parent_review_receipt_v1(replace(receipt, **changes))


def test_slice_a3_2_receipt_json_rejects_duplicate_noncanonical_and_oversized() -> None:
    contracts = _contracts()
    receipt = _review_receipt(contracts)
    raw = contracts.parent_review_receipt_v1_canonical_json_bytes(receipt)

    duplicate = raw.replace(
        b'{"preparation_commit_sha":',
        b'{"preparation_commit_sha":"' + b"1" * 40 + b'","preparation_commit_sha":',
        1,
    )
    for attacked in (
        duplicate,
        b"\xef\xbb\xbf" + raw,
        raw[:-1],
        raw[:-1] + b" \n",
        raw + b"\n",
        b"x" * (contracts.PARENT_REVIEW_RECEIPT_MAX_BYTES + 1),
    ):
        with pytest.raises((TypeError, ValueError)):
            contracts.parse_parent_review_receipt_v1_json(attacked)

    with pytest.raises(TypeError):
        contracts.parse_parent_review_receipt_v1_json(bytearray(raw))


def test_slice_a3_2_raw_and_json_receipts_reject_4097_closure_entries() -> None:
    contracts = _contracts()
    closure = tuple(
        (f"entry-{index:04d}.py", "a" * 64)
        for index in range(contracts.PARENT_REVIEW_RECEIPT_MAX_ARRAY_ITEMS + 1)
    )
    attacked = _resign_review_receipt(
        contracts,
        _review_receipt(contracts),
        reviewed_path_closure=closure,
    )
    raw = _receipt_json_bytes_unchecked(contracts, attacked)
    assert len(raw) < contracts.PARENT_REVIEW_RECEIPT_MAX_BYTES

    with pytest.raises(ValueError, match="array exceeds the item cap"):
        contracts.verify_parent_review_receipt_v1(attacked)
    with pytest.raises(ValueError, match="array exceeds the item cap"):
        contracts.parent_review_receipt_v1_canonical_json_bytes(attacked)
    with pytest.raises(ValueError, match="array exceeds the item cap"):
        contracts.parse_parent_review_receipt_v1_json(raw)


def test_slice_a3_2_raw_export_and_json_share_one_mib_string_boundary() -> None:
    contracts = _contracts()
    receipt = _review_receipt(contracts)
    at_limit = _resign_review_receipt(
        contracts,
        receipt,
        reviewer_id="r" * contracts.PARENT_REVIEW_RECEIPT_MAX_STRING_BYTES,
    )
    at_limit_raw = _receipt_json_bytes_unchecked(contracts, at_limit)

    assert contracts.verify_parent_review_receipt_v1(at_limit) is at_limit
    assert (
        contracts.parent_review_receipt_v1_canonical_json_bytes(at_limit)
        == at_limit_raw
    )
    assert contracts.parse_parent_review_receipt_v1_json(at_limit_raw) == at_limit

    over_limit = _resign_review_receipt(
        contracts,
        receipt,
        reviewer_id=("r" * (contracts.PARENT_REVIEW_RECEIPT_MAX_STRING_BYTES + 1)),
    )
    over_limit_raw = _receipt_json_bytes_unchecked(contracts, over_limit)
    for verifier in (
        contracts.verify_parent_review_receipt_v1,
        contracts.parent_review_receipt_v1_canonical_json_bytes,
    ):
        with pytest.raises(ValueError, match="string exceeds the 1 MiB cap"):
            verifier(over_limit)
    with pytest.raises(ValueError, match="string exceeds the 1 MiB cap"):
        contracts.parse_parent_review_receipt_v1_json(over_limit_raw)


def test_slice_a3_2_raw_and_json_walkers_share_depth_boundary() -> None:
    contracts = _contracts()
    raw_at_limit: object = "leaf"
    json_at_limit: object = "leaf"
    for _ in range(contracts.PARENT_REVIEW_RECEIPT_MAX_DEPTH - 1):
        raw_at_limit = (raw_at_limit,)
        json_at_limit = [json_at_limit]

    contracts._require_exact_wire_tree(raw_at_limit, "raw_at_limit")
    contracts._validate_json_resource_caps(json_at_limit)

    raw_over_limit = (raw_at_limit,)
    json_over_limit = [json_at_limit]
    with pytest.raises(ValueError, match="recursion cap"):
        contracts._require_exact_wire_tree(raw_over_limit, "raw_over_limit")
    with pytest.raises(ValueError, match="recursion cap"):
        contracts._validate_json_resource_caps(json_over_limit)


def test_slice_a3_2_raw_receipt_verifier_enforces_total_byte_cap() -> None:
    contracts = _contracts()
    one_mib = contracts.PARENT_REVIEW_RECEIPT_MAX_STRING_BYTES
    closure = tuple((letter * one_mib, "a" * 64) for letter in ("a", "b", "c"))
    attacked = _resign_review_receipt(
        contracts,
        _review_receipt(contracts),
        reviewer_id="r" * one_mib,
        reviewed_path_closure=closure,
    )
    raw = _receipt_json_bytes_unchecked(contracts, attacked)
    assert len(raw) > contracts.PARENT_REVIEW_RECEIPT_MAX_BYTES

    with pytest.raises(ValueError, match="4 MiB cap"):
        contracts.verify_parent_review_receipt_v1(attacked)
    with pytest.raises(ValueError, match="4 MiB cap"):
        contracts.parent_review_receipt_v1_canonical_json_bytes(attacked)
    with pytest.raises(ValueError, match="invalid size"):
        contracts.parse_parent_review_receipt_v1_json(raw)


def test_slice_a3_3_signing_audit_payload_is_exact_and_self_hashed() -> None:
    contracts = _contracts()
    provisional = contracts.ParentSigningAuditV1(
        audit_schema_version=contracts.PARENT_SIGNING_AUDIT_V1_SCHEMA_VERSION,
        preparation_commit_sha="1" * 40,
        signing_commit_sha="2" * 40,
        review_receipt_shas=("3" * 64, "4" * 64),
        diff_digest="5" * 64,
        diff_allowlist_id=contracts.PARENT_V3_SIGNING_DIFF_ALLOWLIST_ID,
        signed_source_refs_root_sha="6" * 64,
        reviewed_candidate_sha="7" * 64,
        reviewed_path_closure_sha="8" * 64,
        source_closure_sha="9" * 64,
        audit_sha="0" * 64,
    )
    audit = replace(
        provisional,
        audit_sha=canonical_sha(contracts.parent_signing_audit_v1_payload(provisional)),
    )

    assert contracts.verify_parent_signing_audit_v1(audit) is audit
    assert contracts.parent_signing_audit_v1_payload(audit) == {
        "audit_schema_version": "v3m0.parent-signing-audit.v1",
        "preparation_commit_sha": "1" * 40,
        "signing_commit_sha": "2" * 40,
        "review_receipt_shas": ["3" * 64, "4" * 64],
        "diff_digest": "5" * 64,
        "diff_allowlist_id": "parent-v3-signing-diff-v1",
        "signed_source_refs_root_sha": "6" * 64,
        "reviewed_candidate_sha": "7" * 64,
        "reviewed_path_closure_sha": "8" * 64,
        "source_closure_sha": "9" * 64,
    }
    for changes in (
        {"audit_sha": "f" * 64},
        {"diff_allowlist_id": "parent-v3-signing-diff-v2"},
        {"review_receipt_shas": tuple(reversed(audit.review_receipt_shas))},
        {"preparation_commit_sha": "1" * 64},
        {"diff_digest": "5" * 40},
    ):
        with pytest.raises((TypeError, ValueError)):
            contracts.verify_parent_signing_audit_v1(replace(audit, **changes))

    class HostileAudit(contracts.ParentSigningAuditV1):
        pass

    with pytest.raises(TypeError):
        contracts.verify_parent_signing_audit_v1(HostileAudit(**vars(audit)))


def test_slice_a3_3_receipt_pair_and_manifest_bind_all_canonical_roots(
    candidate_v3_fixture,
) -> None:
    contracts = _contracts()
    candidate_module = importlib.import_module("rulespace_v3.parent_candidate_v3")
    signing_sha = "f" * 40
    references = tuple(
        _signed_source_ref(
            contracts,
            index,
            preparation_commit_sha=candidate_v3_fixture.preparation_commit_sha,
            signing_commit_sha=signing_sha,
        )
        for index in range(len(contracts.PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS))
    )
    receipts = tuple(
        _review_receipt(contracts, index, candidate_v3=candidate_v3_fixture)
        for index in range(2)
    )
    assert (
        contracts.verify_parent_review_receipts_v1(
            receipts,
            candidate_v3_fixture,
        )
        is receipts
    )
    audit = _signing_audit(
        contracts,
        candidate_v3_fixture,
        references,
        receipts,
        signing_sha,
    )
    registry_sha = canonical_sha(
        candidate_module.current_application_registry_v3_payload(candidate_v3_fixture)
    )
    provisional = contracts.ParentFreezeV3Manifest(
        parent_freeze_schema_version=contracts.PARENT_FREEZE_V3_SCHEMA_VERSION,
        authority_state=contracts.PARENT_V3_AUTHORITY_STATE,
        program_id=contracts.PARENT_V3_PROGRAM_ID,
        preparation_commit_sha=candidate_v3_fixture.preparation_commit_sha,
        signing_commit_sha=signing_sha,
        reviewed_candidate_v3=candidate_v3_fixture,
        signed_source_refs=references,
        review_receipts=receipts,
        signing_audit=audit,
        current_application_registry_sha=registry_sha,
        parent_freeze_v3_sha="0" * 64,
    )
    manifest = replace(
        provisional,
        parent_freeze_v3_sha=canonical_sha(
            contracts.parent_freeze_v3_manifest_payload(provisional)
        ),
    )

    assert contracts.verify_parent_freeze_v3_manifest(manifest) is manifest
    payload = contracts.parent_freeze_v3_manifest_payload(manifest)
    assert payload["reviewed_candidate_v3"]["candidate_sha"] == (
        candidate_v3_fixture.candidate_sha
    )
    assert [item["source_ref_sha"] for item in payload["signed_source_refs"]] == [
        item.source_ref_sha for item in references
    ]
    assert [item["receipt_sha"] for item in payload["review_receipts"]] == [
        item.receipt_sha for item in receipts
    ]
    assert payload["signing_audit"]["audit_sha"] == audit.audit_sha
    assert payload["current_application_registry_sha"] == registry_sha
    assert not hasattr(contracts, "issue_v3m0_parent_freeze_v3")
    assert not hasattr(contracts, "VerifiedParentFreezeV3")

    for changes in (
        {"parent_freeze_v3_sha": "e" * 64},
        {"signed_source_refs": tuple(reversed(references))},
        {"review_receipts": tuple(reversed(receipts))},
        {"current_application_registry_sha": "e" * 64},
        {"preparation_commit_sha": "e" * 40},
        {"signing_commit_sha": "d" * 40},
    ):
        with pytest.raises((TypeError, ValueError)):
            contracts.verify_parent_freeze_v3_manifest(replace(manifest, **changes))

    class HostileManifest(contracts.ParentFreezeV3Manifest):
        pass

    with pytest.raises(TypeError):
        contracts.verify_parent_freeze_v3_manifest(HostileManifest(**vars(manifest)))


def test_slice_a3_3_recursive_resign_cannot_change_review_or_candidate_roots(
    candidate_v3_fixture,
) -> None:
    contracts = _contracts()
    signing_sha = "f" * 40
    references = tuple(
        _signed_source_ref(
            contracts,
            index,
            preparation_commit_sha=candidate_v3_fixture.preparation_commit_sha,
            signing_commit_sha=signing_sha,
        )
        for index in range(len(contracts.PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS))
    )
    receipts = tuple(
        _review_receipt(contracts, index, candidate_v3=candidate_v3_fixture)
        for index in range(2)
    )
    audit = _signing_audit(
        contracts,
        candidate_v3_fixture,
        references,
        receipts,
        signing_sha,
    )

    resigned_audit_body = replace(
        audit,
        review_receipt_shas=tuple(reversed(audit.review_receipt_shas)),
        audit_sha="0" * 64,
    )
    resigned_audit = replace(
        resigned_audit_body,
        audit_sha=canonical_sha(
            contracts.parent_signing_audit_v1_payload(resigned_audit_body)
        ),
    )
    with pytest.raises(ValueError):
        contracts.verify_parent_v3_signing_bundle(
            candidate_v3_fixture,
            references,
            receipts,
            resigned_audit,
        )

    candidate_module = importlib.import_module("rulespace_v3.parent_candidate_v3")
    resigned_candidate_body = replace(
        candidate_v3_fixture,
        source_closure_sha="e" * 64,
        candidate_sha="0" * 64,
    )
    resigned_candidate = replace(
        resigned_candidate_body,
        candidate_sha=canonical_sha(
            candidate_module.parent_freeze_candidate_v3_manifest_payload(
                resigned_candidate_body
            )
        ),
    )
    with pytest.raises(ValueError):
        contracts.verify_parent_review_receipts_v1(
            receipts,
            resigned_candidate,
        )


@pytest.mark.parametrize("attack_kind", ("reorder", "replace"))
def test_slice_a3_3_recursive_resign_cannot_change_success_lane_semantics(
    candidate_v3_fixture,
    monkeypatch: pytest.MonkeyPatch,
    attack_kind: str,
) -> None:
    contracts = _contracts()
    candidate_module = importlib.import_module("rulespace_v3.parent_candidate_v3")
    success_ids = candidate_v3_fixture.block_success_scenario_ids
    if attack_kind == "reorder":
        attacked_success_ids = (success_ids[1], success_ids[0], *success_ids[2:])
    else:
        attacked_success_ids = (
            "ATTACKER_REPLACEMENT_SUCCESS_LANE",
            *success_ids[1:],
        )
    candidate_body = replace(
        candidate_v3_fixture,
        block_success_scenario_ids=attacked_success_ids,
        candidate_sha="0" * 64,
    )
    attacked_candidate = replace(
        candidate_body,
        candidate_sha=canonical_sha(
            candidate_module.parent_freeze_candidate_v3_manifest_payload(candidate_body)
        ),
    )

    signing_sha = "f" * 40
    references = tuple(
        _signed_source_ref(
            contracts,
            index,
            preparation_commit_sha=attacked_candidate.preparation_commit_sha,
            signing_commit_sha=signing_sha,
        )
        for index in range(len(contracts.PARENT_V3_MANDATORY_SIGNED_SOURCE_SPECS))
    )
    receipts = tuple(
        _review_receipt(contracts, index, candidate_v3=attacked_candidate)
        for index in range(2)
    )
    audit = _signing_audit(
        contracts,
        attacked_candidate,
        references,
        receipts,
        signing_sha,
    )
    provisional = contracts.ParentFreezeV3Manifest(
        parent_freeze_schema_version=contracts.PARENT_FREEZE_V3_SCHEMA_VERSION,
        authority_state=contracts.PARENT_V3_AUTHORITY_STATE,
        program_id=contracts.PARENT_V3_PROGRAM_ID,
        preparation_commit_sha=attacked_candidate.preparation_commit_sha,
        signing_commit_sha=signing_sha,
        reviewed_candidate_v3=attacked_candidate,
        signed_source_refs=references,
        review_receipts=receipts,
        signing_audit=audit,
        current_application_registry_sha=canonical_sha(
            candidate_module.current_application_registry_v3_payload(attacked_candidate)
        ),
        parent_freeze_v3_sha="0" * 64,
    )
    recursively_resigned = replace(
        provisional,
        parent_freeze_v3_sha=canonical_sha(
            _manifest_payload_unchecked(contracts, provisional)
        ),
    )

    def _forbid_public_fresh_audit(_candidate):
        raise AssertionError("A3 must not invoke the public fresh-audit verifier")

    monkeypatch.setattr(
        candidate_module,
        "verify_parent_freeze_candidate_v3",
        _forbid_public_fresh_audit,
    )
    with pytest.raises(ValueError, match="block-success scenario IDs"):
        contracts.verify_parent_freeze_v3_manifest(recursively_resigned)
