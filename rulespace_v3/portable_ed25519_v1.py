"""Portable canonical-JSON and OpenSSH Ed25519 verification primitives.

This lower leaf owns no campaign or Parent authority.  It accepts explicit
bytes only and is shared by the generic campaign-stage owner.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import tempfile
import time

from .evidence import canonical_sha


_SSH_SIGNATURE_BEGIN_V1 = "-----BEGIN SSH SIGNATURE-----"
_SSH_SIGNATURE_END_V1 = "-----END SSH SIGNATURE-----"
_SSH_SIGNATURE_MAGIC_AND_VERSION_V1 = b"SSHSIG\x00\x00\x00\x01"
_MAX_SIGNATURE_ARMOR_BYTES_V1 = 1 << 20
_SSH_KEYGEN_EXECUTABLE_V1 = "/usr/bin/ssh-keygen"
_SSH_VERIFY_PRINCIPAL_V1 = "computational-universe-lab-portable-ed25519-v1"
_SSH_VERIFY_TIMEOUT_SECONDS_V1 = 30.0
_SSH_VERIFY_STREAM_LIMIT_V1 = 65536
_SSH_VERIFY_ENVIRONMENT_V1 = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
}


def _exact_json_value_v1(
    value: object,
    *,
    path: str,
    active_containers: set[int],
) -> object:
    value_type = type(value)
    if value is None or value_type in (str, bool, int):
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a nonfinite float")
        return value
    if value_type is dict:
        identity = id(value)
        if identity in active_containers:
            raise ValueError(f"{path} contains a cyclic object")
        active_containers.add(identity)
        try:
            normalized: dict[str, object] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise TypeError(f"{path} contains a non-string object key")
                normalized[key] = _exact_json_value_v1(
                    item,
                    path=f"{path}.{key}",
                    active_containers=active_containers,
                )
            return normalized
        finally:
            active_containers.remove(identity)
    if value_type in (list, tuple):
        identity = id(value)
        if identity in active_containers:
            raise ValueError(f"{path} contains a cyclic array")
        active_containers.add(identity)
        try:
            return [
                _exact_json_value_v1(
                    item,
                    path=f"{path}[{index}]",
                    active_containers=active_containers,
                )
                for index, item in enumerate(value)
            ]
        finally:
            active_containers.remove(identity)
    raise TypeError(f"{path} contains non-JSON type {value_type.__name__}")


def _make_canonical_statement_codec_v1(
    *,
    _normalizer=_exact_json_value_v1,
    _canonical_sha=canonical_sha,
    _json_dumps=json.dumps,
    _sha256=hashlib.sha256,
):
    def canonical_statement_bytes_v1(payload: dict[str, object]) -> bytes:
        """Encode one exact JSON object using the repository canonical wire."""

        if type(payload) is not dict:
            raise TypeError("canonical statement payload must be an exact dict")
        normalized = _normalizer(payload, path="$", active_containers=set())
        assert type(normalized) is dict
        expected_sha = _canonical_sha(normalized)
        try:
            encoded = _json_dumps(
                normalized,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            raise ValueError("canonical statement is not exact UTF-8 JSON") from exc
        if _sha256(encoded).hexdigest() != expected_sha:
            raise ValueError("canonical statement codec differs from evidence hashing")
        return encoded

    return canonical_statement_bytes_v1


canonical_statement_bytes_v1 = _make_canonical_statement_codec_v1()


def _make_openssh_ed25519_public_key_decoder_v1(
    *,
    _b64decode=base64.b64decode,
    _b64encode=base64.b64encode,
):
    def openssh_ed25519_public_key_wire_v1(public_key_text: str) -> bytes:
        """Decode one canonical ``ssh-ed25519 <base64>`` public-key line."""

        if type(public_key_text) is not str:
            raise TypeError("OpenSSH Ed25519 public key must be an exact str")
        if (
            not public_key_text
            or public_key_text != public_key_text.strip()
            or "\n" in public_key_text
            or "\r" in public_key_text
        ):
            raise ValueError("OpenSSH Ed25519 public key has noncanonical whitespace")
        parts = public_key_text.split(" ")
        if len(parts) != 2 or parts[0] != "ssh-ed25519" or not parts[1]:
            raise ValueError("OpenSSH Ed25519 public key is not one canonical line")
        encoded = parts[1]
        try:
            wire = _b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("OpenSSH Ed25519 public key is not strict base64") from exc
        if _b64encode(wire).decode("ascii") != encoded:
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

    return openssh_ed25519_public_key_wire_v1


openssh_ed25519_public_key_wire_v1 = _make_openssh_ed25519_public_key_decoder_v1()


def _make_openssh_sha256_fingerprint_v1(
    *,
    _key_decoder=openssh_ed25519_public_key_wire_v1,
    _b64encode=base64.b64encode,
    _sha256=hashlib.sha256,
):
    def openssh_sha256_fingerprint_v1(public_key_text: str) -> str:
        """Return the canonical OpenSSH SHA-256 fingerprint for one Ed25519 key."""

        wire = _key_decoder(public_key_text)
        encoded = _b64encode(_sha256(wire).digest()).decode("ascii")
        return "SHA256:" + encoded.rstrip("=")

    return openssh_sha256_fingerprint_v1


openssh_sha256_fingerprint_v1 = _make_openssh_sha256_fingerprint_v1()


def _make_openssh_signature_armor_decoder_v1(
    *,
    _b64decode=base64.b64decode,
    _b64encode=base64.b64encode,
):
    def decode_openssh_signature_armor_v1(signature_armor: str) -> bytes:
        """Strictly decode one canonical OpenSSH SSHSIG armor body."""

        if type(signature_armor) is not str:
            raise TypeError("OpenSSH signature armor must be an exact str")
        try:
            raw_armor = signature_armor.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("OpenSSH signature armor must be exact ASCII") from exc
        if not raw_armor or len(raw_armor) > _MAX_SIGNATURE_ARMOR_BYTES_V1:
            raise ValueError("OpenSSH signature armor size is outside its hard cap")
        if "\r" in signature_armor or not signature_armor.endswith("\n"):
            raise ValueError("OpenSSH signature armor must use canonical LF framing")
        lines = signature_armor.split("\n")
        if (
            len(lines) < 4
            or lines[0] != _SSH_SIGNATURE_BEGIN_V1
            or lines[-2] != _SSH_SIGNATURE_END_V1
            or lines[-1] != ""
        ):
            raise ValueError("OpenSSH signature armor framing drifted")
        encoded_lines = lines[1:-2]
        if (
            not encoded_lines
            or any(not line or len(line) > 70 for line in encoded_lines)
            or any(len(line) != 70 for line in encoded_lines[:-1])
        ):
            raise ValueError("OpenSSH signature armor base64 wrapping drifted")
        encoded = "".join(encoded_lines)
        try:
            decoded = _b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("OpenSSH signature armor is not strict base64") from exc
        if _b64encode(decoded).decode("ascii") != encoded:
            raise ValueError("OpenSSH signature armor base64 is not canonical")
        if not decoded.startswith(_SSH_SIGNATURE_MAGIC_AND_VERSION_V1):
            raise ValueError("OpenSSH signature armor is not an SSHSIG v1 blob")
        return decoded

    return decode_openssh_signature_armor_v1


decode_openssh_signature_armor_v1 = _make_openssh_signature_armor_decoder_v1()


def _ssh_keygen_identity_v1(
    executable: str,
    *,
    _lstat=os.lstat,
) -> tuple[int, ...]:
    try:
        metadata = _lstat(executable)
    except OSError as exc:
        raise ValueError("literal trusted ssh-keygen is unavailable") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_mode & 0o022
        or metadata.st_mode & 0o111 == 0
        or metadata.st_size <= 0
    ):
        raise ValueError("literal trusted ssh-keygen identity or mode drifted")
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _stop_process_group_v1(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=1.0)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("trusted ssh-keygen process group could not be stopped") from exc


def _run_bounded_ssh_keygen_verify_v1(
    *,
    executable: str,
    principal: str,
    directory: Path,
    allowed_signers_path: Path,
    signature_path: Path,
    namespace: str,
    statement_bytes: bytes,
    _popen=subprocess.Popen,
    _stop_process_group=_stop_process_group_v1,
    _timeout_seconds=_SSH_VERIFY_TIMEOUT_SECONDS_V1,
    _stream_limit=_SSH_VERIFY_STREAM_LIMIT_V1,
    _environment=tuple(_SSH_VERIFY_ENVIRONMENT_V1.items()),
) -> subprocess.CompletedProcess[bytes]:
    command = (
        executable,
        "-Y",
        "verify",
        "-f",
        os.fspath(allowed_signers_path),
        "-I",
        principal,
        "-n",
        namespace,
        "-s",
        os.fspath(signature_path),
    )
    try:
        process = _popen(
            command,
            cwd=directory,
            shell=False,
            env=dict(_environment),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise ValueError("literal trusted ssh-keygen could not start") from exc
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    output = {"stdout": bytearray(), "stderr": bytearray()}
    input_offset = 0
    deadline = time.monotonic() + _timeout_seconds
    try:
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        os.set_blocking(process.stdin.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _stop_process_group(process)
                raise ValueError("literal trusted ssh-keygen timed out")
            events = selector.select(min(remaining, 0.1))
            if not events:
                continue
            for key, _mask in events:
                name = key.data
                stream = key.fileobj
                if name == "stdin":
                    try:
                        count = os.write(
                            stream.fileno(),
                            statement_bytes[input_offset : input_offset + 65536],
                        )
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        count = 0
                    input_offset += count
                    if count == 0 or input_offset == len(statement_bytes):
                        selector.unregister(stream)
                        stream.close()
                    continue
                try:
                    chunk = os.read(stream.fileno(), 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    continue
                room = _stream_limit + 1 - len(output[name])
                output[name].extend(chunk[: max(room, 0)])
                if len(output[name]) > _stream_limit:
                    _stop_process_group(process)
                    raise ValueError(
                        f"literal trusted ssh-keygen {name} exceeded its hard cap"
                    )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _stop_process_group(process)
            raise ValueError("literal trusted ssh-keygen timed out")
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _stop_process_group(process)
            raise ValueError("literal trusted ssh-keygen timed out") from exc
        return subprocess.CompletedProcess(
            args=command,
            returncode=returncode,
            stdout=bytes(output["stdout"]),
            stderr=bytes(output["stderr"]),
        )
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            stream.close()
        if not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            _stop_process_group(process)


def _make_openssh_ed25519_verifier_v1(
    *,
    _executable=_SSH_KEYGEN_EXECUTABLE_V1,
    _principal=_SSH_VERIFY_PRINCIPAL_V1,
    _key_decoder=openssh_ed25519_public_key_wire_v1,
    _armor_decoder=decode_openssh_signature_armor_v1,
    _identity=_ssh_keygen_identity_v1,
    _runner=_run_bounded_ssh_keygen_verify_v1,
    _temporary_directory=tempfile.TemporaryDirectory,
):
    """Capture every executable dependency behind the no-override public API."""

    def verify_openssh_ed25519_signature_v1(
        *,
        public_key_text: str,
        signature_armor: str,
        namespace: str,
        statement_bytes: bytes,
    ) -> None:
        """Verify one detached Ed25519 SSHSIG over exact caller-supplied bytes."""

        _key_decoder(public_key_text)
        _armor_decoder(signature_armor)
        if (
            type(namespace) is not str
            or not namespace
            or "\x00" in namespace
            or "\n" in namespace
            or "\r" in namespace
        ):
            raise ValueError(
                "OpenSSH signature namespace is not one exact nonempty string"
            )
        try:
            namespace.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("OpenSSH signature namespace is not exact UTF-8") from exc
        if type(statement_bytes) is not bytes:
            raise TypeError("OpenSSH signed statement must be exact bytes")
        executable_identity = _identity(_executable)
        with _temporary_directory(prefix="culab-portable-ed25519-") as raw_dir:
            directory = Path(raw_dir).resolve(strict=True)
            allowed_signers = directory / "allowed_signers"
            signature = directory / "statement.sig"
            try:
                allowed_signers.write_bytes(
                    (f"{_principal} {public_key_text}\n").encode("ascii")
                )
                signature.write_bytes(signature_armor.encode("ascii"))
            except (OSError, UnicodeEncodeError) as exc:
                raise ValueError(
                    "portable signature verification inputs could not be staged"
                ) from exc
            allowed_signers.chmod(0o600)
            signature.chmod(0o600)
            completed = _runner(
                executable=_executable,
                principal=_principal,
                directory=directory,
                allowed_signers_path=allowed_signers,
                signature_path=signature,
                namespace=namespace,
                statement_bytes=statement_bytes,
            )
        if _identity(_executable) != executable_identity:
            raise ValueError("literal trusted ssh-keygen changed during verification")
        if completed.returncode < 0:
            raise ValueError("literal trusted ssh-keygen terminated by signal")
        if completed.returncode != 0:
            raise ValueError("OpenSSH Ed25519 signature is invalid")

    return verify_openssh_ed25519_signature_v1


verify_openssh_ed25519_signature_v1 = _make_openssh_ed25519_verifier_v1()


__all__ = (
    "canonical_statement_bytes_v1",
    "decode_openssh_signature_armor_v1",
    "openssh_ed25519_public_key_wire_v1",
    "openssh_sha256_fingerprint_v1",
    "verify_openssh_ed25519_signature_v1",
)
