from __future__ import annotations

import ast
import base64
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import subprocess

import pytest

from rulespace_v3.parent_signing_audit_v1 import (
    _MANDATORY_STATUS_TRANSFORMS_BY_PATH,
    _PARENT_V3_SIGNING_LITERALS_PATH,
    _audit_repository_signing_bundle,
    _audit_exact_document_transform,
    _audit_signing_literals_transform,
    _issue_private_parent_signing_audit,
    _make_private_audit_registry,
    _parent_review_signed_statement_bytes,
    _parse_reviewer_registry_source,
    _parse_raw_diff_tree_z,
    _replay_git_tree_diff,
    _run_bounded_process,
    _require_private_parent_signing_audit,
    _snapshot_clean_head,
    _single_parent_commit,
    _signing_tree_diff_digest,
    _verify_review_receipt_signature,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3 import parent_candidate_v3 as candidate_contracts
from rulespace_v3 import parent_freeze_v3_contracts as signing_contracts
from rulespace_v3 import parent_signing_audit_v1 as signing_audit_module


SHA1_A = "a" * 40
SHA1_B = "b" * 40
SHA256_A = "a" * 64
SHA256_B = "b" * 64


def _raw_diff_record(
    path: str,
    *,
    old_mode: str = "100644",
    new_mode: str = "100644",
    old_oid: str = SHA1_A,
    new_oid: str = SHA1_B,
    status: str = "M",
) -> bytes:
    return (
        f":{old_mode} {new_mode} {old_oid} {new_oid} {status}".encode("ascii")
        + b"\x00"
        + path.encode("utf-8")
        + b"\x00"
    )


def test_raw_diff_parser_accepts_only_canonical_nonrename_records() -> None:
    raw = _raw_diff_record("a.txt") + _raw_diff_record(
        "z.txt",
        old_mode="000000",
        old_oid="0" * 40,
        status="A",
    )

    entries = _parse_raw_diff_tree_z(raw)

    assert tuple(item.relative_path for item in entries) == ("a.txt", "z.txt")
    assert entries[1].old_mode is None
    assert entries[1].old_git_blob_oid is None
    assert _signing_tree_diff_digest(entries) == (
        "bcb7a410144c1bf1e8078c61758a475679cf18448e036aca89ffa0b2e114dcad"
    )


@pytest.mark.parametrize(
    "raw",
    (
        _raw_diff_record("z.txt") + _raw_diff_record("a.txt"),
        _raw_diff_record("../escape"),
        _raw_diff_record("a.txt", status="R100") + b"old.txt\x00",
        _raw_diff_record("a.txt", old_mode="120000"),
        _raw_diff_record("a.txt")[:-1],
        _raw_diff_record("a.txt") + _raw_diff_record("a.txt"),
    ),
)
def test_raw_diff_parser_rejects_order_path_status_mode_and_framing_drift(
    raw: bytes,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        _parse_raw_diff_tree_z(raw)


def test_document_transform_is_one_exact_byte_replacement() -> None:
    path, (draft, signed) = next(iter(_MANDATORY_STATUS_TRANSFORMS_BY_PATH.items()))
    old = f"header\n{draft}\nbody DRAFT is explanatory\n".encode()
    new = f"header\n{signed}\nbody DRAFT is explanatory\n".encode()

    _audit_exact_document_transform(path, old, new)

    with pytest.raises(ValueError):
        _audit_exact_document_transform(path, old, new + b"extra")
    with pytest.raises(ValueError):
        _audit_exact_document_transform(path, old.replace(b"header", b"HEADER"), new)
    with pytest.raises(ValueError):
        _audit_exact_document_transform(path, old + (draft + "\n").encode(), new)


def test_all_real_draft_documents_admit_only_the_header_transform() -> None:
    repository = Path(__file__).parents[1]
    for relative_path, (draft, signed) in _MANDATORY_STATUS_TRANSFORMS_BY_PATH.items():
        preparation = (repository / relative_path).read_bytes()
        signing = preparation.replace(draft.encode("utf-8"), signed.encode("utf-8"), 1)

        _audit_exact_document_transform(relative_path, preparation, signing)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda raw, draft: b"\xef\xbb\xbf" + raw,
        lambda raw, draft: raw[:-1] + b"\r\n",
        lambda raw, draft: raw.replace(
            draft.encode("utf-8"), b"> " + draft.encode("utf-8"), 1
        ),
        lambda raw, draft: raw + (" " + draft + "\n").encode("utf-8"),
        lambda raw, draft: raw + b"\xff\n",
    ),
)
def test_document_transform_rejects_noncanonical_or_alternate_headers(mutation) -> None:
    path, (draft, signed) = next(iter(_MANDATORY_STATUS_TRANSFORMS_BY_PATH.items()))
    preparation = f"{draft}\nbody\n".encode("utf-8")
    mutated = mutation(preparation, draft)
    signing = mutated.replace(draft.encode("utf-8"), signed.encode("utf-8"), 1)

    with pytest.raises(ValueError):
        _audit_exact_document_transform(path, mutated, signing)


def _signing_literal_source(
    *,
    preparation: str = "None",
    candidate: str = "None",
    closure: str = "None",
    sources: str = "()",
    receipts: str = "()",
) -> bytes:
    return (
        "from __future__ import annotations\n\n"
        f"PARENT_V3_PREPARATION_COMMIT_SHA: str | None = {preparation}\n"
        f"PARENT_V3_REVIEWED_CANDIDATE_SHA256: str | None = {candidate}\n"
        f"PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256: str | None = {closure}\n"
        "PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH: "
        f"tuple[tuple[str, str], ...] = {sources}\n"
        "PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE: "
        f"tuple[tuple[str, str], ...] = {receipts}\n"
    ).encode()


def test_signing_literal_transform_freezes_values_and_all_other_bytes() -> None:
    source_items = tuple(
        (path, hashlib.sha256(path.encode()).hexdigest())
        for path in _MANDATORY_STATUS_TRANSFORMS_BY_PATH
    )
    receipt_items = (
        ("MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW", SHA256_A),
        ("AUTHORITY_AND_BOUNDARY_REVIEW", SHA256_B),
    )
    old = _signing_literal_source()
    new = _signing_literal_source(
        preparation=repr(SHA1_A),
        candidate=repr(SHA256_A),
        closure=repr(SHA256_B),
        sources=repr(source_items),
        receipts=repr(receipt_items),
    )

    observed = _audit_signing_literals_transform(
        old,
        new,
        preparation_commit_sha=SHA1_A,
        reviewed_candidate_sha=SHA256_A,
        reviewed_path_closure_sha=SHA256_B,
        signed_source_sha256_by_path=source_items,
        review_receipt_sha256_by_role=receipt_items,
    )

    assert observed["PARENT_V3_PREPARATION_COMMIT_SHA"] == SHA1_A
    assert ast.parse(new.decode())


@pytest.mark.parametrize(
    "mutation",
    (
        lambda raw: raw.replace(b"from __future__", b"# drift\nfrom __future__"),
        lambda raw: raw.replace(b"str | None", b"str", 1),
        lambda raw: raw.replace(
            b"PARENT_V3_PREPARATION_COMMIT_SHA",
            b"PARENT_V3_PREPARATION_COMMIT",
            1,
        ),
        lambda raw: raw + b"EXTRA = 1\n",
        lambda raw: raw + b"open('/tmp/side-effect', 'w').write('bad')\n",
        lambda raw: raw.replace(b"\n", b"\r\n"),
    ),
)
def test_signing_literal_transform_rejects_ast_or_non_rhs_drift(mutation) -> None:
    source_items = tuple(
        (path, SHA256_A) for path in _MANDATORY_STATUS_TRANSFORMS_BY_PATH
    )
    receipt_items = (
        ("MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW", SHA256_A),
        ("AUTHORITY_AND_BOUNDARY_REVIEW", SHA256_B),
    )
    old = _signing_literal_source()
    valid_new = _signing_literal_source(
        preparation=repr(SHA1_A),
        candidate=repr(SHA256_A),
        closure=repr(SHA256_B),
        sources=repr(source_items),
        receipts=repr(receipt_items),
    )

    with pytest.raises((TypeError, ValueError, SyntaxError)):
        _audit_signing_literals_transform(
            old,
            mutation(valid_new),
            preparation_commit_sha=SHA1_A,
            reviewed_candidate_sha=SHA256_A,
            reviewed_path_closure_sha=SHA256_B,
            signed_source_sha256_by_path=source_items,
            review_receipt_sha256_by_role=receipt_items,
        )


def test_signing_literal_transform_rejects_unchanged_side_effect_code() -> None:
    source_items = tuple(
        (path, SHA256_A) for path in _MANDATORY_STATUS_TRANSFORMS_BY_PATH
    )
    receipt_items = (
        ("MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW", SHA256_A),
        ("AUTHORITY_AND_BOUNDARY_REVIEW", SHA256_B),
    )
    old = _signing_literal_source() + b"open('/tmp/a4-side-effect', 'w')\n"
    new = (
        _signing_literal_source(
            preparation=repr(SHA1_A),
            candidate=repr(SHA256_A),
            closure=repr(SHA256_B),
            sources=repr(source_items),
            receipts=repr(receipt_items),
        )
        + b"open('/tmp/a4-side-effect', 'w')\n"
    )

    with pytest.raises(ValueError, match="statement shape"):
        _audit_signing_literals_transform(
            old,
            new,
            preparation_commit_sha=SHA1_A,
            reviewed_candidate_sha=SHA256_A,
            reviewed_path_closure_sha=SHA256_B,
            signed_source_sha256_by_path=source_items,
            review_receipt_sha256_by_role=receipt_items,
        )


def test_signing_audit_module_has_no_public_authority_constructor() -> None:
    module_path = Path(__file__).parents[1] / "rulespace_v3/parent_signing_audit_v1.py"
    module = ast.parse(module_path.read_text(encoding="utf-8"))
    public_functions = {
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert public_functions == set()
    assert _PARENT_V3_SIGNING_LITERALS_PATH == (
        "rulespace_v3/parent_signing_literals_v1.py"
    )


def _reviewer_registry_source(value: str, *, extra: str = "") -> bytes:
    return (
        '"""registry"""\n'
        "from __future__ import annotations\n\n"
        "PARENT_V3_TRUSTED_REVIEWER_KEYS_V1: "
        f"tuple[tuple[str, str, str, str], ...] = {value}\n\n"
        '__all__ = ["PARENT_V3_TRUSTED_REVIEWER_KEYS_V1"]\n'
        f"{extra}"
    ).encode()


def test_reviewer_registry_is_parsed_as_one_inert_exact_literal(monkeypatch) -> None:
    expected = (
        ("role-a", "alice", "key-a", "ssh-ed25519 AAAA"),
        ("role-b", "bob", "key-b", "ssh-ed25519 BBBB"),
    )
    monkeypatch.setattr(
        "rulespace_v3.parent_signing_audit_v1.verify_parent_v3_reviewer_key_registry",
        lambda value: (
            value if value == expected else (_ for _ in ()).throw(ValueError())
        ),
    )

    assert (
        _parse_reviewer_registry_source(_reviewer_registry_source(repr(expected)))
        == expected
    )


@pytest.mark.parametrize(
    "raw",
    (
        _reviewer_registry_source("build_registry()"),
        _reviewer_registry_source("()", extra="SIDE_EFFECT = 1\n"),
        _reviewer_registry_source("()") + b"\r\n",
        _reviewer_registry_source(
            "()", extra="PARENT_V3_TRUSTED_REVIEWER_KEYS_V1 = ()\n"
        ),
    ),
)
def test_reviewer_registry_parser_rejects_code_or_source_shape_drift(
    raw: bytes,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        _parse_reviewer_registry_source(raw)


def test_inert_python_parsers_reject_oversized_sources() -> None:
    oversized = _signing_literal_source() + b"#" * (1 << 20)
    with pytest.raises(ValueError, match="1 MiB"):
        _parse_reviewer_registry_source(oversized)
    with pytest.raises(ValueError, match="1 MiB"):
        from rulespace_v3.parent_signing_audit_v1 import _parse_signing_literal_module

        _parse_signing_literal_module(oversized)


def test_bounded_process_kills_at_first_stream_byte_over_cap(tmp_path: Path) -> None:
    marker = tmp_path / "should-not-exist"
    code = (
        "import pathlib,sys,time;"
        "sys.stdout.buffer.write(b'x'*65537);sys.stdout.buffer.flush();"
        "time.sleep(.2);"
        f"pathlib.Path({os.fspath(marker)!r}).write_text('escaped')"
    )

    with pytest.raises(ValueError, match="stream limit"):
        _run_bounded_process(
            (os.fspath(Path(os.__file__).parents[2] / "bin/python3"), "-c", code),
            cwd=tmp_path,
            environment={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
            input_bytes=b"",
            maximum_stdout_bytes=65536,
            maximum_stderr_bytes=65536,
            timeout_seconds=5,
        )
    assert not marker.exists()


def _git(repository: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LC_ALL": "C",
            "LANG": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", "-A")
    _git(
        repository,
        "-c",
        "user.name=Signing Audit Test",
        "-c",
        "user.email=signing-audit@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD").decode().strip()


def test_git_replay_rebuilds_raw_diff_from_immutable_tree_blobs(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "alpha.txt").write_bytes(b"alpha\n")
    preparation = _commit(repository, "P")
    (repository / "alpha.txt").write_bytes(b"ALPHA\n")
    (repository / "zeta.txt").write_bytes(b"zeta\n")
    signing = _commit(repository, "S")

    assert _snapshot_clean_head(repository) == signing
    assert _single_parent_commit(repository, signing) == preparation
    entries = _replay_git_tree_diff(repository, preparation, signing)

    assert tuple(item.relative_path for item in entries) == (
        "alpha.txt",
        "zeta.txt",
    )
    assert entries[0].old_blob_sha256 == hashlib.sha256(b"alpha\n").hexdigest()
    assert entries[0].new_blob_sha256 == hashlib.sha256(b"ALPHA\n").hexdigest()
    assert entries[1].old_blob_sha256 is None
    assert entries[1].new_blob_sha256 == hashlib.sha256(b"zeta\n").hexdigest()

    (repository / "untracked.txt").write_bytes(b"dirty")
    with pytest.raises(ValueError, match="clean"):
        _snapshot_clean_head(repository)


def test_clean_snapshot_disables_repository_local_fsmonitor_hook(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "tracked").write_bytes(b"tracked\n")
    signing = _commit(repository, "clean")
    hook = tmp_path / "fsmonitor-hook"
    sentinel = tmp_path / "fsmonitor-hook.ran"
    hook.write_text('#!/bin/sh\n: > "$0.ran"\nexit 0\n', encoding="utf-8")
    hook.chmod(0o755)
    _git(repository, "config", "core.fsmonitor", os.fspath(hook))

    _git(repository, "status", "--porcelain=v1")
    assert sentinel.exists(), "fixture must prove that ordinary Git executes the hook"
    sentinel.unlink()

    assert _snapshot_clean_head(repository) == signing
    assert not sentinel.exists()


def test_clean_snapshot_binds_the_explicit_root_against_core_worktree_redirect(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    alternate = tmp_path / "alternate-worktree"
    repository.mkdir()
    alternate.mkdir()
    _git(repository, "init", "-q")
    (repository / "tracked").write_bytes(b"signed\n")
    signing = _commit(repository, "S")
    (alternate / "tracked").write_bytes(b"signed\n")
    _git(repository, "config", "core.worktree", os.fspath(alternate))

    # Prove the hostile fixture: ordinary Git silently audits the alternate tree.
    assert _git(repository, "status", "--porcelain=v1") == b""
    (repository / "tracked").write_bytes(b"dirty\n")
    (repository / "untracked").write_bytes(b"untracked\n")

    with pytest.raises(ValueError, match="clean"):
        _snapshot_clean_head(repository)
    assert _git(repository, "rev-parse", "HEAD").decode("ascii").strip() == signing


@pytest.mark.parametrize("index_flag", ("--assume-unchanged", "--skip-worktree"))
def test_clean_snapshot_rejects_index_flags_that_hide_tracked_drift(
    tmp_path: Path,
    index_flag: str,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    tracked = repository / "tracked"
    tracked.write_bytes(b"signed\n")
    _commit(repository, "S")
    _git(repository, "update-index", index_flag, "tracked")
    tracked.write_bytes(b"dirty but hidden\n")

    assert _git(repository, "status", "--porcelain=v1") == b""
    with pytest.raises(ValueError, match="index contains hidden"):
        _snapshot_clean_head(repository)


@pytest.mark.parametrize("boundary", ("head", "status", "cat-file"))
@pytest.mark.parametrize("attack", ("dirty", "head-drift"))
def test_clean_snapshot_rejects_persistent_drift_after_internal_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    attack: str,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "tracked").write_bytes(b"tracked\n")
    _commit(repository, "S")
    real_git_command = signing_audit_module._git_command
    injected = False

    def command_boundary(arguments: tuple[str, ...]) -> str | None:
        if arguments[:3] == ("rev-parse", "--verify", "HEAD"):
            return "head"
        if "status" in arguments:
            return "status"
        if arguments[:2] == ("cat-file", "-t"):
            return "cat-file"
        return None

    def inject_after_command(root: Path, *arguments: str):
        nonlocal injected
        completed = real_git_command(root, *arguments)
        if not injected and command_boundary(arguments) == boundary:
            injected = True
            if attack == "dirty":
                (repository / "persistent-untracked").write_bytes(b"dirty\n")
            else:
                (repository / "new-clean-head").write_bytes(b"new HEAD\n")
                _commit(repository, "persistent clean HEAD drift")
        return completed

    monkeypatch.setattr(
        signing_audit_module,
        "_git_command",
        inject_after_command,
    )
    with pytest.raises(ValueError, match="clean|changed"):
        _snapshot_clean_head(repository)
    assert injected is True


def test_tree_blob_lookup_treats_git_pathspec_magic_as_a_literal_name(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    literal_name = ":(glob)*"
    (repository / literal_name).write_bytes(b"literal pathspec bytes\n")
    (repository / "ordinary").write_bytes(b"ordinary\n")
    commit = _commit(repository, "literal pathspec")

    blob = signing_audit_module._read_tree_blob(repository, commit, literal_name)

    assert blob is not None
    assert blob.raw == b"literal pathspec bytes\n"


def test_a4_git_commands_delegate_to_the_frozen_executable_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = {}

    def bounded(command, **keywords):
        observed["command"] = command
        observed.update(keywords)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(
        signing_audit_module,
        "_run_identity_bounded_process",
        bounded,
    )

    completed = signing_audit_module._git_command(tmp_path, "status")

    assert completed.returncode == 0
    assert observed["command"][0] == (
        signing_audit_module._TRUSTED_GIT_EXECUTABLE_REALPATH
    )
    assert observed["executable_identity"] is (
        signing_audit_module._TRUSTED_GIT_EXECUTABLE_IDENTITY
    )
    assert observed["env"]["GIT_LITERAL_PATHSPECS"] == "1"
    assert observed["env"]["GIT_WORK_TREE"] == os.fspath(tmp_path.resolve(strict=True))
    assert observed["max_stdout_bytes"] == 8 << 20
    assert observed["max_stderr_bytes"] == 1 << 20


def test_single_parent_gate_rejects_root_and_merge_commits(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "base").write_bytes(b"base")
    root = _commit(repository, "root")
    with pytest.raises(ValueError, match="single parent"):
        _single_parent_commit(repository, root)

    _git(repository, "checkout", "-q", "-b", "side")
    (repository / "side").write_bytes(b"side")
    _commit(repository, "side")
    _git(repository, "checkout", "-q", "-b", "main", root)
    (repository / "main").write_bytes(b"main")
    _commit(repository, "main")
    _git(
        repository,
        "-c",
        "user.name=Signing Audit Test",
        "-c",
        "user.email=signing-audit@example.invalid",
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "merge",
        "side",
    )
    merge = _git(repository, "rev-parse", "HEAD").decode().strip()
    with pytest.raises(ValueError, match="single parent"):
        _single_parent_commit(repository, merge)


def _armor_stub() -> str:
    encoded = base64.b64encode(b"SSHSIG" + b"\x00" * 64).decode("ascii")
    lines = [encoded[index : index + 70] for index in range(0, len(encoded), 70)]
    return (
        "-----BEGIN SSH SIGNATURE-----\n"
        + "\n".join(lines)
        + "\n-----END SSH SIGNATURE-----\n"
    )


def _real_signed_receipt(tmp_path: Path):
    private_key = tmp_path / "reviewer_ed25519"
    subprocess.run(
        (
            "/usr/bin/ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "",
            "-f",
            os.fspath(private_key),
        ),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    public_fields = private_key.with_suffix(".pub").read_text().strip().split()
    public_key = " ".join(public_fields[:2])
    key_id = signing_contracts.openssh_sha256_fingerprint(public_key)
    closure = (("alpha.py", SHA256_A),)
    closure_sha = canonical_sha(
        candidate_contracts.reviewed_path_closure_v1_payload(closure)
    )
    provisional = signing_contracts.ParentReviewReceiptV1(
        receipt_schema_version=(
            signing_contracts.PARENT_REVIEW_RECEIPT_V1_SCHEMA_VERSION
        ),
        review_role=signing_contracts.PARENT_V3_REVIEW_ROLES[0],
        reviewer_id="reviewer-math",
        reviewer_key_id=key_id,
        signature_algorithm=(signing_contracts.PARENT_V3_REVIEW_SIGNATURE_ALGORITHM),
        preparation_commit_sha=SHA1_A,
        reviewed_candidate_sha=SHA256_A,
        reviewed_path_closure=closure,
        reviewed_path_closure_sha=closure_sha,
        verdict="PASS",
        signed_statement_sha="0" * 64,
        signature_armor=_armor_stub(),
        receipt_sha="0" * 64,
    )
    statement_bound = replace(
        provisional,
        signed_statement_sha=canonical_sha(
            signing_contracts.parent_review_receipt_v1_signed_statement_payload(
                provisional
            )
        ),
    )
    statement = _parent_review_signed_statement_bytes(statement_bound)
    signed = subprocess.run(
        (
            "/usr/bin/ssh-keygen",
            "-Y",
            "sign",
            "-f",
            os.fspath(private_key),
            "-n",
            signing_contracts.PARENT_V3_REVIEW_SIGNATURE_NAMESPACE,
        ),
        input=statement,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    with_signature = replace(
        statement_bound,
        signature_armor=signed.stdout.decode("ascii"),
    )
    receipt = replace(
        with_signature,
        receipt_sha=canonical_sha(
            signing_contracts.parent_review_receipt_v1_payload(with_signature)
        ),
    )
    registry_entry = (
        receipt.review_role,
        receipt.reviewer_id,
        receipt.reviewer_key_id,
        public_key,
    )
    return receipt, registry_entry, private_key


def test_real_openssh_ed25519_receipt_signature_is_replayed(tmp_path: Path) -> None:
    receipt, registry_entry, private_key = _real_signed_receipt(tmp_path)

    assert _verify_review_receipt_signature(receipt, registry_entry) is receipt

    wrong_statement_signature = subprocess.run(
        (
            "/usr/bin/ssh-keygen",
            "-Y",
            "sign",
            "-f",
            os.fspath(private_key),
            "-n",
            signing_contracts.PARENT_V3_REVIEW_SIGNATURE_NAMESPACE,
        ),
        input=b"wrong statement",
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.decode("ascii")
    bad_body = replace(
        receipt,
        signature_armor=wrong_statement_signature,
        receipt_sha="0" * 64,
    )
    bad_receipt = replace(
        bad_body,
        receipt_sha=canonical_sha(
            signing_contracts.parent_review_receipt_v1_payload(bad_body)
        ),
    )
    with pytest.raises(ValueError, match="signature"):
        _verify_review_receipt_signature(bad_receipt, registry_entry)


def test_signature_replay_binds_role_identity_key_and_fingerprint(
    tmp_path: Path,
) -> None:
    receipt, registry_entry, _private_key = _real_signed_receipt(tmp_path)
    for index, replacement_value in enumerate(
        (
            signing_contracts.PARENT_V3_REVIEW_ROLES[1],
            "other-reviewer",
            "SHA256:" + "A" * 43,
        )
    ):
        altered = list(registry_entry)
        altered[index] = replacement_value
        with pytest.raises(ValueError):
            _verify_review_receipt_signature(receipt, tuple(altered))


def test_private_audit_capability_rejects_constructor_forgery_mutation_and_death() -> (
    None
):
    issuer, require, wrapper_type = _make_private_audit_registry(
        validator=lambda value: dict(value),
        seal_builder=lambda value: hashlib.sha256(
            repr(sorted(value.items())).encode()
        ).hexdigest(),
    )
    raw = {"audit": SHA256_A}
    capability = issuer(raw)

    assert require(capability) == raw
    raw["audit"] = SHA256_B
    assert require(capability) != raw
    with pytest.raises(TypeError):
        wrapper_type(object(), {"audit": SHA256_A}, SHA256_A)
    forged = object.__new__(wrapper_type)
    with pytest.raises(ValueError, match="registry"):
        require(forged)
    object.__setattr__(capability, "_VerifiedParentSigningAuditV1__seal", SHA256_B)
    with pytest.raises(ValueError, match="seal"):
        require(capability)


@pytest.fixture(scope="module")
def real_candidate_template():
    """Build the expensive legacy/V2/V3 semantic body once for central A4 tests."""

    repository = Path(__file__).parents[1]
    preparation = (
        _git(
            repository,
            "rev-list",
            "--no-merges",
            "-n",
            "1",
            "HEAD",
        )
        .decode("ascii")
        .strip()
    )
    return candidate_contracts._replay_v3m0_parent_freeze_candidate_v3_at_preparation_commit(
        preparation
    )


def _generate_reviewer_key(directory: Path, ordinal: int) -> tuple[Path, str, str]:
    private_key = directory / f"reviewer-{ordinal}"
    subprocess.run(
        (
            "/usr/bin/ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "",
            "-f",
            os.fspath(private_key),
        ),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    public_fields = private_key.with_suffix(".pub").read_text().strip().split()
    public_key = " ".join(public_fields[:2])
    return (
        private_key,
        public_key,
        signing_contracts.openssh_sha256_fingerprint(public_key),
    )


def _signed_candidate_receipt(
    *,
    candidate,
    role: str,
    reviewer_id: str,
    reviewer_key_id: str,
    private_key: Path,
):
    reviewed_closure = tuple(
        (path, raw_sha) for path, _mode, raw_sha in candidate.source_closure
    )
    reviewed_closure_sha = canonical_sha(
        candidate_contracts.reviewed_path_closure_v1_payload(reviewed_closure)
    )
    provisional = signing_contracts.ParentReviewReceiptV1(
        receipt_schema_version=signing_contracts.PARENT_REVIEW_RECEIPT_V1_SCHEMA_VERSION,
        review_role=role,
        reviewer_id=reviewer_id,
        reviewer_key_id=reviewer_key_id,
        signature_algorithm=signing_contracts.PARENT_V3_REVIEW_SIGNATURE_ALGORITHM,
        preparation_commit_sha=candidate.preparation_commit_sha,
        reviewed_candidate_sha=candidate.candidate_sha,
        reviewed_path_closure=reviewed_closure,
        reviewed_path_closure_sha=reviewed_closure_sha,
        verdict="PASS",
        signed_statement_sha="0" * 64,
        signature_armor=_armor_stub(),
        receipt_sha="0" * 64,
    )
    statement_bound = replace(
        provisional,
        signed_statement_sha=canonical_sha(
            signing_contracts.parent_review_receipt_v1_signed_statement_payload(
                provisional
            )
        ),
    )
    signed = subprocess.run(
        (
            "/usr/bin/ssh-keygen",
            "-Y",
            "sign",
            "-f",
            os.fspath(private_key),
            "-n",
            signing_contracts.PARENT_V3_REVIEW_SIGNATURE_NAMESPACE,
        ),
        input=_parent_review_signed_statement_bytes(statement_bound),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    with_signature = replace(
        statement_bound,
        signature_armor=signed.stdout.decode("ascii"),
    )
    return replace(
        with_signature,
        receipt_sha=canonical_sha(
            signing_contracts.parent_review_receipt_v1_payload(with_signature)
        ),
    )


def _rehash_candidate_for_preparation(template, repository: Path, preparation: str):
    closure_paths = (
        *tuple(_MANDATORY_STATUS_TRANSFORMS_BY_PATH),
        _PARENT_V3_SIGNING_LITERALS_PATH,
        signing_audit_module._PARENT_V3_REVIEWER_REGISTRY_PATH,
    )
    closure = []
    for relative_path in sorted(closure_paths, key=lambda item: item.encode("utf-8")):
        blob = signing_audit_module._read_tree_blob(
            repository,
            preparation,
            relative_path,
        )
        assert blob is not None
        closure.append((relative_path, blob.mode, hashlib.sha256(blob.raw).hexdigest()))
    closure_tuple = tuple(closure)
    provisional = replace(
        template,
        preparation_commit_sha=preparation,
        source_closure=closure_tuple,
        source_closure_sha="0" * 64,
        candidate_sha="0" * 64,
    )
    rooted = replace(
        provisional,
        source_closure_sha=canonical_sha(
            candidate_contracts.parent_v3_source_closure_v1_payload(
                preparation,
                closure_tuple,
            )
        ),
    )
    candidate = replace(
        rooted,
        candidate_sha=canonical_sha(
            candidate_contracts.parent_freeze_candidate_v3_manifest_payload(rooted)
        ),
    )
    candidate_contracts._verify_parent_candidate_v3_roots_and_registry(candidate)
    return candidate


def _build_real_signing_repository(
    root: Path,
    template,
    *,
    attack: str = "valid",
):
    repository = root / "repo"
    key_directory = root / "keys"
    repository.mkdir(parents=True)
    key_directory.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "core.autocrlf", "false")
    _git(repository, "config", "core.filemode", "true")

    key_rows = []
    private_keys = []
    for ordinal, role in enumerate(signing_contracts.PARENT_V3_REVIEW_ROLES):
        private_key, public_key, key_id = _generate_reviewer_key(key_directory, ordinal)
        reviewer_id = f"independent-reviewer-{ordinal}"
        key_rows.append((role, reviewer_id, key_id, public_key))
        private_keys.append(private_key)

    def write(relative_path: str, raw: bytes) -> None:
        destination = repository / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)

    for index, (relative_path, (draft, _signed)) in enumerate(
        _MANDATORY_STATUS_TRANSFORMS_BY_PATH.items()
    ):
        body = f"# Signed source {index}\n\n{draft}\n\nbody\n"
        if "Parent-v3-P-epoch" in relative_path:
            body += f"\n```text\n{draft}\n```\n"
        write(relative_path, body.encode("utf-8"))
    write(_PARENT_V3_SIGNING_LITERALS_PATH, _signing_literal_source())
    write(
        signing_audit_module._PARENT_V3_REVIEWER_REGISTRY_PATH,
        _reviewer_registry_source(repr(tuple(key_rows))),
    )
    if attack == "receipt-in-p":
        _role, receipt_path = signing_contracts.PARENT_V3_REVIEW_RECEIPT_PATHS_BY_ROLE[
            0
        ]
        write(receipt_path, b"P must not contain a receipt\n")
    preparation = _commit(repository, "P")
    candidate = _rehash_candidate_for_preparation(
        template,
        repository,
        preparation,
    )
    if attack == "wrong-parent":
        write("intermediate.txt", b"changes the direct parent\n")
        _commit(repository, "intermediate")

    receipts = tuple(
        _signed_candidate_receipt(
            candidate=candidate,
            role=role,
            reviewer_id=key_rows[index][1],
            reviewer_key_id=key_rows[index][2],
            private_key=private_keys[index],
        )
        for index, role in enumerate(signing_contracts.PARENT_V3_REVIEW_ROLES)
    )
    for relative_path, (draft, signed) in _MANDATORY_STATUS_TRANSFORMS_BY_PATH.items():
        preparation_raw = (repository / relative_path).read_bytes()
        write(
            relative_path,
            preparation_raw.replace(draft.encode("utf-8"), signed.encode("utf-8"), 1),
        )
    for receipt, (_role, relative_path) in zip(
        receipts,
        signing_contracts.PARENT_V3_REVIEW_RECEIPT_PATHS_BY_ROLE,
    ):
        write(
            relative_path,
            signing_contracts.parent_review_receipt_v1_canonical_json_bytes(receipt),
        )
    signed_source_items = tuple(
        (
            relative_path,
            hashlib.sha256((repository / relative_path).read_bytes()).hexdigest(),
        )
        for relative_path in _MANDATORY_STATUS_TRANSFORMS_BY_PATH
    )
    receipt_items = tuple(
        (receipt.review_role, receipt.receipt_sha) for receipt in receipts
    )
    write(
        _PARENT_V3_SIGNING_LITERALS_PATH,
        _signing_literal_source(
            preparation=repr(preparation),
            candidate=repr(candidate.candidate_sha),
            closure=repr(receipts[0].reviewed_path_closure_sha),
            sources=repr(signed_source_items),
            receipts=repr(receipt_items),
        ),
    )

    if attack == "missing":
        (_role, missing_path) = (
            signing_contracts.PARENT_V3_REVIEW_RECEIPT_PATHS_BY_ROLE[1]
        )
        (repository / missing_path).unlink()
    elif attack == "extra":
        write("unexpected-signing-change.txt", b"not allowlisted\n")

    signing = _commit(repository, "S")
    if attack == "dirty":
        write("untracked-after-S", b"dirty\n")
    return repository, candidate, preparation, signing


def _run_central_signing_audit(repository: Path, candidate):
    def verify_semantics(value):
        candidate_contracts._verify_parent_candidate_v3_roots_and_registry(value)
        return value

    return _audit_repository_signing_bundle(
        repository,
        candidate_replayer=lambda _preparation: candidate,
        candidate_verifier=verify_semantics,
    )


def test_central_repository_audit_replays_real_signed_bundle_and_capability(
    tmp_path: Path,
    real_candidate_template,
) -> None:
    repository, candidate, preparation, signing = _build_real_signing_repository(
        tmp_path,
        real_candidate_template,
    )

    bundle = _run_central_signing_audit(repository, candidate)
    capability = _issue_private_parent_signing_audit(bundle)
    replayed = _require_private_parent_signing_audit(capability)

    assert replayed == bundle
    assert bundle.reviewed_candidate_v3 is candidate
    assert bundle.signing_audit.preparation_commit_sha == preparation
    assert bundle.signing_audit.signing_commit_sha == signing
    assert len(bundle.review_receipts) == 2
    assert len(bundle.signed_source_refs) == 4
    assert len(bundle.protected_signing_tree) == 8


@pytest.mark.parametrize(
    "attack",
    ("missing", "extra", "receipt-in-p", "wrong-parent", "dirty"),
)
def test_central_repository_audit_rejects_epoch_and_worktree_attacks(
    tmp_path: Path,
    real_candidate_template,
    attack: str,
) -> None:
    repository, candidate, _preparation, _signing = _build_real_signing_repository(
        tmp_path,
        real_candidate_template,
        attack=attack,
    )

    with pytest.raises(ValueError):
        _run_central_signing_audit(repository, candidate)


def test_central_repository_audit_rejects_final_snapshot_drift(
    tmp_path: Path,
    real_candidate_template,
    monkeypatch,
) -> None:
    repository, candidate, preparation, signing = _build_real_signing_repository(
        tmp_path,
        real_candidate_template,
    )
    calls = 0

    def drifting_snapshot(root: Path) -> str:
        nonlocal calls
        calls += 1
        assert root == repository.resolve(strict=True)
        return signing if calls == 1 else preparation

    monkeypatch.setattr(
        signing_audit_module,
        "_snapshot_clean_head",
        drifting_snapshot,
    )
    with pytest.raises(ValueError, match="changed during"):
        _run_central_signing_audit(repository, candidate)
    assert calls == 2
