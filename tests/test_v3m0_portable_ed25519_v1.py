"""Focused contracts for the generic B10 portable Ed25519 lower leaf."""

from __future__ import annotations

import ast
import base64
import hashlib
import inspect
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest


_GOLDEN_PUBLIC_KEY = (
    "ssh-ed25519 "
    "AAAAC3NzaC1lZDI1NTE5AAAAINdamAGCsQq31Uv+08lkBzoO4XLz2qYjJa8CGmj3B1Ea"
)
_GOLDEN_FINGERPRINT = "SHA256:bbXpuKG6zhzdmnxq256TlqzFBzRl2f6OOg722cYNbU8"
_TEST_NAMESPACE = "computational-universe-lab-portable-test-v1"


def _signed_statement_v1(
    tmp_path: Path,
    statement: bytes,
    *,
    namespace: str = _TEST_NAMESPACE,
) -> tuple[str, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
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
    public_key_text = " ".join(public_fields[:2])
    signed = subprocess.run(
        (
            "/usr/bin/ssh-keygen",
            "-Y",
            "sign",
            "-f",
            os.fspath(private_key),
            "-n",
            namespace,
        ),
        input=statement,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return public_key_text, signed.stdout.decode("ascii")


def test_public_key_codec_matches_the_frozen_parent_golden() -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    wire = portable.openssh_ed25519_public_key_wire_v1(_GOLDEN_PUBLIC_KEY)

    assert len(wire) == 51
    assert portable.openssh_sha256_fingerprint_v1(_GOLDEN_PUBLIC_KEY) == (
        _GOLDEN_FINGERPRINT
    )

    for attacked in (
        " " + _GOLDEN_PUBLIC_KEY,
        _GOLDEN_PUBLIC_KEY + " ",
        _GOLDEN_PUBLIC_KEY + "\n",
        _GOLDEN_PUBLIC_KEY + " comment",
        _GOLDEN_PUBLIC_KEY.replace("ssh-ed25519", "ssh-rsa", 1),
        _GOLDEN_PUBLIC_KEY[:-1] + "!",
    ):
        with pytest.raises((TypeError, ValueError)):
            portable.openssh_ed25519_public_key_wire_v1(attacked)

    decoded = base64.b64decode(_GOLDEN_PUBLIC_KEY.split()[1])
    for attacked_wire in (
        decoded + b"x",
        b"\x00\x00\x00\x0a" + decoded[4:],
        decoded[:15] + b"\x00\x00\x00\x1f" + decoded[19:-1],
    ):
        attacked = "ssh-ed25519 " + base64.b64encode(attacked_wire).decode("ascii")
        with pytest.raises(ValueError):
            portable.openssh_ed25519_public_key_wire_v1(attacked)


def test_canonical_statement_codec_matches_the_evidence_hash_contract() -> None:
    from rulespace_v3 import evidence
    from rulespace_v3 import portable_ed25519_v1 as portable

    statement = {
        "z": [True, None, -0.0],
        "a": {"unicode": "度量", "integer": 7},
    }
    expected = (
        b'{"a":{"integer":7,"unicode":"\xe5\xba\xa6\xe9\x87\x8f"},'
        b'"z":[true,null,-0.0]}'
    )

    observed = portable.canonical_statement_bytes_v1(statement)

    assert observed == expected
    assert hashlib.sha256(observed).hexdigest() == evidence.canonical_sha(statement)

    for hostile in (
        {"bad": float("nan")},
        {"bad": {1: "non-string-key"}},
        {"bad": b"not-json"},
    ):
        with pytest.raises((TypeError, ValueError)):
            portable.canonical_statement_bytes_v1(hostile)

    with pytest.raises(TypeError):
        portable.canonical_statement_bytes_v1([])  # type: ignore[arg-type]


def test_real_openssh_sshsig_verifies_exact_key_namespace_and_statement(
    tmp_path: Path,
) -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    statement = portable.canonical_statement_bytes_v1(
        {"protocol": "portable-test-v1", "root": "a" * 64}
    )
    public_key_text, signature_armor = _signed_statement_v1(tmp_path, statement)

    decoded = portable.decode_openssh_signature_armor_v1(signature_armor)
    assert decoded.startswith(b"SSHSIG\x00\x00\x00\x01")
    portable.verify_openssh_ed25519_signature_v1(
        public_key_text=public_key_text,
        signature_armor=signature_armor,
        namespace=_TEST_NAMESPACE,
        statement_bytes=statement,
    )

    wrong_key, _wrong_signature = _signed_statement_v1(
        tmp_path / "wrong-key",
        statement,
    )
    attacks = (
        {"public_key_text": wrong_key},
        {"namespace": _TEST_NAMESPACE + "-wrong"},
        {"statement_bytes": statement + b"\n"},
        {"signature_armor": signature_armor.replace("A", "B", 1)},
    )
    baseline = {
        "public_key_text": public_key_text,
        "signature_armor": signature_armor,
        "namespace": _TEST_NAMESPACE,
        "statement_bytes": statement,
    }
    for attack in attacks:
        with pytest.raises(ValueError):
            portable.verify_openssh_ed25519_signature_v1(
                **{**baseline, **attack}
            )


def test_signature_armor_rejects_noncanonical_framing(tmp_path: Path) -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    public_key_text, signature_armor = _signed_statement_v1(tmp_path, b"statement")
    assert public_key_text.startswith("ssh-ed25519 ")

    for attacked in (
        signature_armor.replace("\n", "\r\n"),
        signature_armor.removesuffix("\n"),
        " " + signature_armor,
        signature_armor + "\n",
        signature_armor.replace("-----BEGIN SSH SIGNATURE-----", "BEGIN"),
    ):
        with pytest.raises((TypeError, ValueError)):
            portable.decode_openssh_signature_armor_v1(attacked)


def test_public_verifier_cannot_be_redirected_from_literal_ssh_keygen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    statement = b"exact statement"
    public_key_text, signature_armor = _signed_statement_v1(tmp_path, statement)
    true_executable = Path("/usr/bin/true")
    if not true_executable.is_file():
        pytest.skip("platform has no literal /usr/bin/true attack fixture")
    monkeypatch.setattr(
        portable,
        "_SSH_KEYGEN_EXECUTABLE_V1",
        os.fspath(true_executable),
    )

    with pytest.raises(ValueError):
        portable.verify_openssh_ed25519_signature_v1(
            public_key_text=public_key_text,
            signature_armor=signature_armor,
            namespace=_TEST_NAMESPACE,
            statement_bytes=statement + b" attacked",
        )


def test_canonical_statement_codec_captures_its_exact_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    payload = {"must": "remain", "ordered": [1, 2, 3]}
    expected = b'{"must":"remain","ordered":[1,2,3]}'
    hostile = b"{}"
    monkeypatch.setattr(portable.json, "dumps", lambda *_args, **_kwargs: "{}")
    monkeypatch.setattr(
        portable,
        "canonical_sha",
        lambda _payload: hashlib.sha256(hostile).hexdigest(),
    )
    monkeypatch.setattr(portable.hashlib, "sha256", hashlib.sha256)

    assert portable.canonical_statement_bytes_v1(payload) == expected


def test_literal_ssh_keygen_identity_rejects_missing_or_unsafe_files() -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    with pytest.raises(ValueError, match="unavailable"):
        portable._ssh_keygen_identity_v1("/definitely/absent/ssh-keygen")

    safe = os.lstat("/usr/bin/ssh-keygen")
    base = {
        field: getattr(safe, field)
        for field in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_uid",
            "st_gid",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
    }
    for override in (
        {"st_uid": 1},
        {"st_mode": stat.S_IFREG | 0o775},
        {"st_mode": stat.S_IFLNK | 0o777},
        {"st_size": 0},
    ):
        attacked = SimpleNamespace(**{**base, **override})
        with pytest.raises(ValueError, match="identity|mode"):
            portable._ssh_keygen_identity_v1(
                "/usr/bin/ssh-keygen",
                _lstat=lambda _path, attacked=attacked: attacked,
            )


def test_bounded_verifier_process_rejects_timeout_and_output_overflow(
    tmp_path: Path,
) -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    allowed_signers = tmp_path / "allowed_signers"
    signature = tmp_path / "statement.sig"
    allowed_signers.write_bytes(b"unused\n")
    signature.write_bytes(b"unused\n")
    real_popen = subprocess.Popen

    def timeout_child(_command, **kwargs):
        return real_popen(
            (sys.executable, "-c", "import time; time.sleep(5)"),
            **kwargs,
        )

    with pytest.raises(ValueError, match="timed out"):
        portable._run_bounded_ssh_keygen_verify_v1(
            executable="/usr/bin/ssh-keygen",
            principal="test-principal",
            directory=tmp_path,
            allowed_signers_path=allowed_signers,
            signature_path=signature,
            namespace=_TEST_NAMESPACE,
            statement_bytes=b"statement",
            _popen=timeout_child,
            _timeout_seconds=0.05,
        )

    def output_child(_command, **kwargs):
        return real_popen(
            (
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(b'x' * 33); sys.stdout.flush()",
            ),
            **kwargs,
        )

    with pytest.raises(ValueError, match="stdout.*hard cap"):
        portable._run_bounded_ssh_keygen_verify_v1(
            executable="/usr/bin/ssh-keygen",
            principal="test-principal",
            directory=tmp_path,
            allowed_signers_path=allowed_signers,
            signature_path=signature,
            namespace=_TEST_NAMESPACE,
            statement_bytes=b"statement",
            _popen=output_child,
            _stream_limit=32,
        )


def test_verifier_factory_rejects_signal_failure_and_binary_identity_drift(
    tmp_path: Path,
) -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    statement = b"statement"
    public_key_text, signature_armor = _signed_statement_v1(tmp_path, statement)

    signaled = portable._make_openssh_ed25519_verifier_v1(
        _identity=lambda _path: (1,),
        _runner=lambda **_kwargs: subprocess.CompletedProcess((), -9, b"", b""),
    )
    with pytest.raises(ValueError, match="signal"):
        signaled(
            public_key_text=public_key_text,
            signature_armor=signature_armor,
            namespace=_TEST_NAMESPACE,
            statement_bytes=statement,
        )

    identities = iter(((1,), (2,)))
    drifted = portable._make_openssh_ed25519_verifier_v1(
        _identity=lambda _path: next(identities),
        _runner=lambda **_kwargs: subprocess.CompletedProcess((), 0, b"", b""),
    )
    with pytest.raises(ValueError, match="changed"):
        drifted(
            public_key_text=public_key_text,
            signature_armor=signature_armor,
            namespace=_TEST_NAMESPACE,
            statement_bytes=statement,
        )


def test_portable_leaf_has_no_parent_crypto_or_signing_surface() -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    source_path = Path(inspect.getsourcefile(portable) or "")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    relative_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 1
    }

    assert relative_imports == {"evidence"}
    assert portable.__all__ == (
        "canonical_statement_bytes_v1",
        "decode_openssh_signature_armor_v1",
        "openssh_ed25519_public_key_wire_v1",
        "openssh_sha256_fingerprint_v1",
        "verify_openssh_ed25519_signature_v1",
    )
    assert tuple(
        inspect.signature(
            portable.verify_openssh_ed25519_signature_v1
        ).parameters
    ) == (
        "public_key_text",
        "signature_armor",
        "namespace",
        "statement_bytes",
    )
    assert not any(
        name.startswith(("sign_", "issue_", "create_private", "generate_private"))
        for name in vars(portable)
    )


def test_parent_key_and_statement_fixtures_have_byte_exact_golden_parity(
    tmp_path: Path,
) -> None:
    from rulespace_v3 import parent_freeze_v3_contracts as parent
    from rulespace_v3 import portable_ed25519_v1 as portable

    _fixture_key, signature_armor = _signed_statement_v1(tmp_path, b"fixture")
    receipt = parent.ParentReviewReceiptV1(
        receipt_schema_version=parent.PARENT_REVIEW_RECEIPT_V1_SCHEMA_VERSION,
        review_role=parent.PARENT_V3_REVIEW_ROLES[0],
        reviewer_id="portable-golden-reviewer",
        reviewer_key_id=_GOLDEN_FINGERPRINT,
        signature_algorithm=parent.PARENT_V3_REVIEW_SIGNATURE_ALGORITHM,
        preparation_commit_sha="a" * 40,
        reviewed_candidate_sha="b" * 64,
        reviewed_path_closure=(("alpha.py", "c" * 64),),
        reviewed_path_closure_sha="d" * 64,
        verdict="PASS",
        signed_statement_sha="e" * 64,
        signature_armor=signature_armor,
        receipt_sha="f" * 64,
    )
    parent_payload = parent.parent_review_receipt_v1_signed_statement_payload(
        receipt
    )

    assert portable.openssh_ed25519_public_key_wire_v1(_GOLDEN_PUBLIC_KEY) == (
        parent.openssh_ed25519_public_key_wire(_GOLDEN_PUBLIC_KEY)
    )
    assert portable.openssh_sha256_fingerprint_v1(_GOLDEN_PUBLIC_KEY) == (
        parent.openssh_sha256_fingerprint(_GOLDEN_PUBLIC_KEY)
    )
    parent._validate_signature_armor(signature_armor)
    assert hashlib.sha256(
        portable.canonical_statement_bytes_v1(parent_payload)
    ).hexdigest() == parent.canonical_sha(parent_payload)


def test_key_and_armor_codecs_capture_their_exact_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rulespace_v3 import portable_ed25519_v1 as portable

    _key, signature_armor = _signed_statement_v1(tmp_path, b"fixture")
    expected_wire = portable.openssh_ed25519_public_key_wire_v1(_GOLDEN_PUBLIC_KEY)
    expected_signature = portable.decode_openssh_signature_armor_v1(signature_armor)
    monkeypatch.setattr(
        portable.base64,
        "b64decode",
        lambda *_args, **_kwargs: b"redirected",
    )

    assert portable.openssh_ed25519_public_key_wire_v1(_GOLDEN_PUBLIC_KEY) == (
        expected_wire
    )
    assert portable.openssh_sha256_fingerprint_v1(_GOLDEN_PUBLIC_KEY) == (
        _GOLDEN_FINGERPRINT
    )
    assert portable.decode_openssh_signature_armor_v1(signature_armor) == (
        expected_signature
    )
