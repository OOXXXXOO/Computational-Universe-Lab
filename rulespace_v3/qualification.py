"""Certificate-backed ablation qualification authority.

This is the sole integration boundary allowed to consume both the Task-9
matched construction and a Task-10 verified dynamics certificate.  Raw
records remain inert serialization bodies; only the live opaque wrapper may
be consumed by response construction.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import math
import re
import threading
import types
import weakref
from dataclasses import dataclass, replace
from typing import Callable, Optional

from .ablation import (
    DYNAMICS_REPORT_SCHEMA_VERSION,
    AblationConstructionOutcome,
    AblationDynamicsReport,
    AblationManifest,
    AblationReplacement,
    _verify_construction_outcome,
    dynamics_report_payload,
)
from .certificate import (
    VerifiedDynamicsCertificate,
    _reverify_verified_dynamics_certificate,
)
from .contracts import BlockStatus, UndefinedReason
from .dynamics import MeasuredTransition
from .evidence import canonical_sha
from .factory import (
    BasisManifest,
    LinearRealspaceFactory,
    Primitive,
    PrimitiveInterface,
)
from .pair_snapshot import (
    AblationPairSnapshot,
    _pair_snapshot,
    ablation_pair_snapshot_payload,
)
from .prestructure import (
    _reverify_verified_prestructure_authority,
)


QUALIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "v3m0.certificate-backed-qualification-evidence.v1"
)
QUALIFICATION_OUTCOME_SCHEMA_VERSION = (
    "v3m0.certificate-backed-qualification-outcome.v1"
)
QUALIFICATION_AUTHORITY_SCHEMA_VERSION = (
    "v3m0.verified-certificate-backed-qualification.v1"
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()
_QUALIFICATION_WIRE_FIELD_NAMES: dict[type, tuple[str, ...]] = {}


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _status_payload(status: BlockStatus) -> dict[str, object]:
    if type(status) is not BlockStatus:
        raise TypeError("status must be an exact BlockStatus")
    return {
        "defined": status.defined,
        "reason": None if status.reason is None else status.reason.value,
    }


def _require_recursive_exact_fields(
    value: object,
    field: str,
    seen: Optional[set[int]] = None,
) -> None:
    visited = set() if seen is None else seen
    identity = id(value)
    if identity in visited:
        return
    record_type = type(value)
    field_names = _QUALIFICATION_WIRE_FIELD_NAMES.get(record_type)
    if field_names is not None:
        visited.add(identity)
        expected = frozenset(field_names)
        actual = frozenset(object.__getattribute__(value, "__dict__"))
        if actual != expected:
            raise ValueError(
                f"{field} record fields differ; "
                f"unknown={sorted(actual - expected)}, "
                f"missing={sorted(expected - actual)}"
            )
        for name in field_names:
            _require_recursive_exact_fields(
                object.__getattribute__(value, name),
                f"{field}.{name}",
                visited,
            )
        return
    if hasattr(record_type, "__dataclass_fields__"):
        raise TypeError(f"{field} has an unregistered record type")
    if record_type is UndefinedReason:
        return
    if type(value) in (tuple, list):
        visited.add(identity)
        for index, item in enumerate(value):
            _require_recursive_exact_fields(
                item,
                f"{field}[{index}]",
                visited,
            )
    elif type(value) is dict:
        visited.add(identity)
        for key, item in value.items():
            _require_recursive_exact_fields(
                item,
                f"{field}[{key!r}]",
                visited,
            )


def _snapshot_record(snapshot: AblationPairSnapshot) -> dict[str, object]:
    return {
        **ablation_pair_snapshot_payload(snapshot),
        "snapshot_sha": snapshot.snapshot_sha,
    }


def _report_record(report: AblationDynamicsReport) -> dict[str, object]:
    return {
        **dynamics_report_payload(report),
        "report_sha": report.report_sha,
    }


@dataclass(frozen=True)
class CertificateBackedQualificationEvidence:
    evidence_schema_version: str
    construction_status: BlockStatus
    pair_snapshot: AblationPairSnapshot
    dynamics_report: AblationDynamicsReport
    verified_certificate_sha: str
    evidence_sha: str

    def __post_init__(self) -> None:
        _text(self.evidence_schema_version, "evidence_schema_version")
        if type(self.construction_status) is not BlockStatus:
            raise TypeError("construction_status must be a BlockStatus")
        if not self.construction_status.defined:
            raise ValueError("qualification evidence requires defined status")
        if type(self.pair_snapshot) is not AblationPairSnapshot:
            raise TypeError("pair_snapshot has the wrong exact type")
        if type(self.dynamics_report) is not AblationDynamicsReport:
            raise TypeError("dynamics_report has the wrong exact type")
        _sha(self.verified_certificate_sha, "verified_certificate_sha")
        _sha(self.evidence_sha, "evidence_sha")


@dataclass(frozen=True)
class CertificateBackedQualificationOutcome:
    status: BlockStatus
    evidence: Optional[CertificateBackedQualificationEvidence]
    outcome_sha: str

    def __post_init__(self) -> None:
        if type(self.status) is not BlockStatus:
            raise TypeError("status must be an exact BlockStatus")
        if self.status.defined != (self.evidence is not None):
            raise ValueError("qualification is defined iff evidence is present")
        if not self.status.defined:
            raise ValueError("certificate-backed qualification is a success capability")
        if type(self.evidence) is not CertificateBackedQualificationEvidence:
            raise TypeError("evidence has the wrong exact type")
        _sha(self.outcome_sha, "outcome_sha")


_QUALIFICATION_WIRE_FIELD_NAMES.update(
    {
        record_type: tuple(record_type.__dataclass_fields__)
        for record_type in (
            CertificateBackedQualificationOutcome,
            CertificateBackedQualificationEvidence,
            BlockStatus,
            AblationPairSnapshot,
            AblationDynamicsReport,
            LinearRealspaceFactory,
            PrimitiveInterface,
            BasisManifest,
            Primitive,
            AblationManifest,
            AblationReplacement,
        )
    }
)


def certificate_backed_qualification_evidence_payload(
    evidence: CertificateBackedQualificationEvidence,
) -> dict[str, object]:
    if type(evidence) is not CertificateBackedQualificationEvidence:
        raise TypeError("evidence must be CertificateBackedQualificationEvidence")
    _require_recursive_exact_fields(evidence, "evidence")
    evidence.__post_init__()
    return {
        "evidence_schema_version": evidence.evidence_schema_version,
        "construction_status": _status_payload(evidence.construction_status),
        "pair_snapshot": _snapshot_record(evidence.pair_snapshot),
        "dynamics_report": _report_record(evidence.dynamics_report),
        "verified_certificate_sha": evidence.verified_certificate_sha,
    }


def certificate_backed_qualification_outcome_payload(
    outcome: CertificateBackedQualificationOutcome,
) -> dict[str, object]:
    if type(outcome) is not CertificateBackedQualificationOutcome:
        raise TypeError("outcome must be CertificateBackedQualificationOutcome")
    _require_recursive_exact_fields(outcome, "outcome")
    outcome.__post_init__()
    return {
        "status": _status_payload(outcome.status),
        "evidence": (
            None
            if outcome.evidence is None
            else {
                **certificate_backed_qualification_evidence_payload(outcome.evidence),
                "evidence_sha": outcome.evidence.evidence_sha,
            }
        ),
    }


def _expected_qualification_outcome(
    construction: AblationConstructionOutcome,
    certificate: VerifiedDynamicsCertificate,
    *,
    _verify_construction: Callable[
        [AblationConstructionOutcome],
        AblationConstructionOutcome,
    ] = _verify_construction_outcome,
    _snapshot_builder: Callable[..., tuple] = _pair_snapshot,
    _certificate_reverify: Callable = _reverify_verified_dynamics_certificate,
    _authority_reverify: Callable = (_reverify_verified_prestructure_authority),
    _canonical: Callable[[object], str] = canonical_sha,
) -> CertificateBackedQualificationOutcome:
    verified_construction = _verify_construction(construction)
    if not verified_construction.status.defined or verified_construction.pair is None:
        raise ValueError(
            "certificate-backed qualification requires a defined construction"
        )
    snapshot, actual_factory, ablated_factory = _snapshot_builder(verified_construction)
    del actual_factory
    certificate_record = _certificate_reverify(certificate)
    authority_view = _authority_reverify(certificate_record.authority)
    if certificate_record.factory is not ablated_factory:
        raise ValueError(
            "qualification requires the construction's ablated certificate"
        )
    if authority_view.factory is not ablated_factory:
        raise ValueError("certificate prestructure is not ablated-factory bound")
    if authority_view.construction is not verified_construction:
        raise ValueError("certificate prestructure is not bound to this construction")
    raw_certificate = certificate_record.certificate
    if raw_certificate.prestructure_authority.factory_role != "matched_ablated":
        raise ValueError("qualification certificate has the wrong factory role")
    if raw_certificate.prestructure_authority.ablation_pair_snapshot != snapshot:
        raise ValueError("certificate pair snapshot differs from live construction")
    certificate_sha = raw_certificate.certificate_sha
    report_provisional = AblationDynamicsReport(
        report_schema_version=DYNAMICS_REPORT_SCHEMA_VERSION,
        factory_sha=snapshot.ablated_factory.factory_sha,
        state_schema_matches=True,
        reversible=True,
        stable=True,
        certificate_sha=certificate_sha,
        report_sha="0" * 64,
    )
    report = replace(
        report_provisional,
        report_sha=_canonical(dynamics_report_payload(report_provisional)),
    )
    evidence_provisional = CertificateBackedQualificationEvidence(
        evidence_schema_version=QUALIFICATION_EVIDENCE_SCHEMA_VERSION,
        construction_status=verified_construction.status,
        pair_snapshot=snapshot,
        dynamics_report=report,
        verified_certificate_sha=certificate_sha,
        evidence_sha="0" * 64,
    )
    evidence = replace(
        evidence_provisional,
        evidence_sha=_canonical(
            certificate_backed_qualification_evidence_payload(evidence_provisional)
        ),
    )
    outcome_provisional = CertificateBackedQualificationOutcome(
        status=BlockStatus(True, None),
        evidence=evidence,
        outcome_sha="0" * 64,
    )
    return replace(
        outcome_provisional,
        outcome_sha=_canonical(
            certificate_backed_qualification_outcome_payload(outcome_provisional)
        ),
    )


def _validate_raw_outcome(
    outcome: CertificateBackedQualificationOutcome,
    *,
    _canonical: Callable[[object], str] = canonical_sha,
) -> None:
    if type(outcome) is not CertificateBackedQualificationOutcome:
        raise TypeError("outcome must be CertificateBackedQualificationOutcome")
    _require_recursive_exact_fields(outcome, "outcome")
    outcome.__post_init__()
    assert outcome.evidence is not None
    outcome.evidence.__post_init__()
    outcome.evidence.pair_snapshot.__post_init__()
    outcome.evidence.dynamics_report.__post_init__()
    if (
        outcome.evidence.evidence_schema_version
        != QUALIFICATION_EVIDENCE_SCHEMA_VERSION
    ):
        raise ValueError("unexpected qualification evidence schema")
    if outcome.evidence.evidence_sha != _canonical(
        certificate_backed_qualification_evidence_payload(outcome.evidence)
    ):
        raise ValueError("qualification evidence SHA mismatch")
    if outcome.outcome_sha != _canonical(
        certificate_backed_qualification_outcome_payload(outcome)
    ):
        raise ValueError("qualification outcome SHA mismatch")


def _qualification_seal(
    outcome: CertificateBackedQualificationOutcome,
    *,
    _canonical: Callable[[object], str] = canonical_sha,
) -> str:
    return _canonical(
        {
            "authority_schema_version": (QUALIFICATION_AUTHORITY_SCHEMA_VERSION),
            "outcome": {
                **certificate_backed_qualification_outcome_payload(outcome),
                "outcome_sha": outcome.outcome_sha,
            },
        }
    )


class VerifiedCertificateBackedQualification:
    """Opaque live success authority consumed by paired response."""

    __slots__ = ("__outcome", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        outcome: CertificateBackedQualificationOutcome,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("VerifiedCertificateBackedQualification is module-issued")
        object.__setattr__(
            self,
            "_VerifiedCertificateBackedQualification__outcome",
            outcome,
        )
        object.__setattr__(
            self,
            "_VerifiedCertificateBackedQualification__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedCertificateBackedQualification__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedCertificateBackedQualification is immutable")

    @property
    def outcome(self) -> CertificateBackedQualificationOutcome:
        """Return the frozen raw outcome through the installed live verifier."""

        return _reverify_verified_certificate_backed_qualification(self).outcome


@dataclass(frozen=True)
class _VerifiedQualificationView:
    outcome: CertificateBackedQualificationOutcome
    construction: AblationConstructionOutcome
    certificate: VerifiedDynamicsCertificate


@dataclass(frozen=True)
class _QualificationAuthority:
    outcome: CertificateBackedQualificationOutcome
    construction: AblationConstructionOutcome
    certificate: VerifiedDynamicsCertificate
    seal: str


def _make_qualification_authority(
    *,
    _wrapper_type: type = VerifiedCertificateBackedQualification,
    _view_type: type = _VerifiedQualificationView,
    _authority_type: type = _QualificationAuthority,
    _certificate_type: type = VerifiedDynamicsCertificate,
    _construction_type: type = AblationConstructionOutcome,
    _evidence_type: type = CertificateBackedQualificationEvidence,
    _outcome_type: type = CertificateBackedQualificationOutcome,
    _snapshot_type: type = AblationPairSnapshot,
    _report_type: type = AblationDynamicsReport,
    _status_type: type = BlockStatus,
    _factory_type: type = LinearRealspaceFactory,
    _interface_type: type = PrimitiveInterface,
    _basis_type: type = BasisManifest,
    _primitive_type: type = Primitive,
    _manifest_type: type = AblationManifest,
    _replacement_type: type = AblationReplacement,
    _undefined_reason_type: type = UndefinedReason,
    _token: object = _ISSUANCE_TOKEN,
    _evidence_schema: str = QUALIFICATION_EVIDENCE_SCHEMA_VERSION,
    _authority_schema: str = QUALIFICATION_AUTHORITY_SCHEMA_VERSION,
    _report_schema: str = DYNAMICS_REPORT_SCHEMA_VERSION,
    _verify_construction: Callable = _verify_construction_outcome,
    _snapshot_builder: Callable = _pair_snapshot,
    _certificate_reverify: Callable = _reverify_verified_dynamics_certificate,
    _prestructure_reverify: Callable = _reverify_verified_prestructure_authority,
    _snapshot_payload: Callable = ablation_pair_snapshot_payload,
    _report_payload: Callable = dynamics_report_payload,
    _isfinite: Callable = math.isfinite,
    _sha256: Callable = hashlib.sha256,
    _rlock: Callable = threading.RLock,
    _weakref_ref: Callable = weakref.ref,
    _type: Callable = type,
    _id: Callable = id,
    _len: Callable = len,
    _ord: Callable = ord,
    _enumerate: Callable = enumerate,
    _range: Callable = range,
    _reversed: Callable = reversed,
    _zip: Callable = zip,
    _sorted: Callable = sorted,
    _set: Callable = set,
    _frozenset: Callable = frozenset,
    _object: type = object,
    _str: type = str,
    _bool: type = bool,
    _int: type = int,
    _float: type = float,
    _tuple: type = tuple,
    _list: type = list,
    _dict: type = dict,
    _repr: Callable = repr,
    _type_error: type[Exception] = TypeError,
    _value_error: type[Exception] = ValueError,
    _attribute_error: type[Exception] = AttributeError,
) -> tuple[Callable, Callable]:
    text_bytes_max = 16_384
    body_bytes_max = 268_435_456
    depth_max = 128
    record_types = (
        _outcome_type,
        _evidence_type,
        _status_type,
        _snapshot_type,
        _report_type,
        _factory_type,
        _interface_type,
        _basis_type,
        _primitive_type,
        _manifest_type,
        _replacement_type,
    )
    record_field_names = {
        record_type: _tuple(record_type.__dataclass_fields__)
        for record_type in record_types
    }

    def text_bytes(value: str, field: str) -> int:
        total = 0
        for character in value:
            codepoint = _ord(character)
            if 0xD800 <= codepoint <= 0xDFFF:
                raise _value_error(f"{field} is not valid UTF-8 text")
            if codepoint <= 0x7F:
                total += 1
            elif codepoint <= 0x7FF:
                total += 2
            elif codepoint <= 0xFFFF:
                total += 3
            else:
                total += 4
            if total > text_bytes_max:
                raise _value_error(f"{field} text exceeds the resource cap")
        return total

    def preflight(value: object, field: str) -> None:
        total = 0
        active: set[int] = _set()
        pending: list[tuple[object, int, bool, str]] = [(value, 0, False, field)]
        while pending:
            current, depth, leaving, path = pending.pop()
            identity = _id(current)
            if leaving:
                active.remove(identity)
                continue
            if depth > depth_max:
                raise _value_error(f"{path} exceeds the nesting resource cap")
            total += 32
            if current is None or _type(current) is _bool:
                pass
            elif _type(current) is _str:
                total += text_bytes(current, path)
            elif _type(current) is _int:
                bits = current.bit_length()
                total += 4 + (bits * 30_103) // 100_000
            elif _type(current) is _float:
                if not _isfinite(current):
                    raise _value_error(f"{path} must be finite")
                total += 32
            elif _type(current) is _undefined_reason_type:
                pending.append(
                    (
                        _object.__getattribute__(current, "_value_"),
                        depth + 1,
                        False,
                        path,
                    )
                )
            elif _type(current) in record_field_names:
                if identity in active:
                    raise _value_error(f"{path} contains a cyclic record")
                names = record_field_names[_type(current)]
                actual_names = _frozenset(_object.__getattribute__(current, "__dict__"))
                expected_names = _frozenset(names)
                if actual_names != expected_names:
                    raise _value_error(f"{path} record fields differ")
                total += 8 * _len(names)
                if total + 32 * _len(names) > body_bytes_max:
                    raise _value_error(f"{field} body exceeds the resource cap")
                active.add(identity)
                pending.append((current, depth, True, path))
                for name in _reversed(names):
                    pending.append(
                        (
                            _object.__getattribute__(current, name),
                            depth + 1,
                            False,
                            f"{path}.{name}",
                        )
                    )
            elif _type(current) in (_tuple, _list):
                if identity in active:
                    raise _value_error(f"{path} contains a cyclic array")
                total += 4 * _len(current)
                if total + 32 * _len(current) > body_bytes_max:
                    raise _value_error(f"{field} body exceeds the resource cap")
                active.add(identity)
                pending.append((current, depth, True, path))
                for index in _range(_len(current) - 1, -1, -1):
                    pending.append(
                        (
                            current[index],
                            depth + 1,
                            False,
                            f"{path}[{index}]",
                        )
                    )
            elif _type(current) is _dict:
                if identity in active:
                    raise _value_error(f"{path} contains a cyclic mapping")
                total += 8 * _len(current)
                if total + 64 * _len(current) > body_bytes_max:
                    raise _value_error(f"{field} body exceeds the resource cap")
                active.add(identity)
                pending.append((current, depth, True, path))
                for index, key in _enumerate(_reversed(current)):
                    item = current[key]
                    pending.append(
                        (
                            item,
                            depth + 1,
                            False,
                            f"{path}.value[{index}]",
                        )
                    )
                    pending.append(
                        (
                            key,
                            depth + 1,
                            False,
                            f"{path}.key[{index}]",
                        )
                    )
            else:
                record_name = _type(current).__name__
                raise _type_error(f"{path} contains unsupported type {record_name}")
            if total > body_bytes_max:
                raise _value_error(f"{field} body exceeds the resource cap")

    def require_exact(value: object, field: str, seen: set[int]) -> None:
        identity = _id(value)
        if identity in seen:
            return
        value_type = _type(value)
        if value_type in record_field_names:
            seen.add(identity)
            names = record_field_names[value_type]
            expected_names = _frozenset(names)
            actual_names = _frozenset(_object.__getattribute__(value, "__dict__"))
            if actual_names != expected_names:
                raise _value_error(
                    f"{field} record fields differ; "
                    f"unknown={_sorted(actual_names - expected_names)}, "
                    f"missing={_sorted(expected_names - actual_names)}"
                )
            for name in names:
                require_exact(
                    _object.__getattribute__(value, name),
                    f"{field}.{name}",
                    seen,
                )
        elif value_type is _undefined_reason_type:
            return
        elif _type(value) in (_tuple, _list):
            seen.add(identity)
            for index, item in _enumerate(value):
                require_exact(item, f"{field}[{index}]", seen)
        elif _type(value) is _dict:
            seen.add(identity)
            for key, item in value.items():
                require_exact(key, f"{field}.key", seen)
                require_exact(item, f"{field}[{key!r}]", seen)
        elif value is not None and value_type not in (_str, _bool, _int, _float):
            raise _type_error(f"{field} has an unsupported exact type")

    def require_parallel_exact(
        actual: object,
        expected: object,
        field: str,
        seen: set[tuple[int, int]],
    ) -> None:
        pair = (_id(actual), _id(expected))
        if pair in seen:
            return
        seen.add(pair)
        if _type(actual) is not _type(expected):
            raise _type_error(f"{field} has the wrong exact type")
        expected_type = _type(expected)
        if expected_type in record_field_names:
            names = record_field_names[expected_type]
            expected_names = _frozenset(names)
            actual_names = _frozenset(_object.__getattribute__(actual, "__dict__"))
            if actual_names != expected_names:
                raise _value_error(f"{field} record fields differ")
            for name in names:
                require_parallel_exact(
                    _object.__getattribute__(actual, name),
                    _object.__getattribute__(expected, name),
                    f"{field}.{name}",
                    seen,
                )
        elif _type(expected) in (_tuple, _list):
            if _len(actual) != _len(expected):
                raise _value_error(f"{field} length differs")
            for index, (actual_item, expected_item) in _enumerate(
                _zip(actual, expected)
            ):
                require_parallel_exact(
                    actual_item,
                    expected_item,
                    f"{field}[{index}]",
                    seen,
                )
        elif _type(expected) is _dict:
            if _tuple(actual) != _tuple(expected):
                raise _value_error(f"{field} mapping keys differ")
            for key in expected:
                require_parallel_exact(
                    actual[key],
                    expected[key],
                    f"{field}[{key!r}]",
                    seen,
                )

    json_escapes = {
        '"': '\\"',
        "\\": "\\\\",
        "\b": "\\b",
        "\f": "\\f",
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }

    def encode_string(value: str, path: str) -> str:
        text_bytes(value, path)
        pieces: list[str] = ['"']
        for character in value:
            escaped = json_escapes.get(character)
            if escaped is not None:
                pieces.append(escaped)
                continue
            codepoint = _ord(character)
            if codepoint < 0x20:
                pieces.append(f"\\u{codepoint:04x}")
            else:
                pieces.append(character)
        pieces.append('"')
        return "".join(pieces)

    def encode_chunks(
        value: object,
        path: str,
        active: set[int],
    ):
        value_type = _type(value)
        if value is None:
            yield "null"
            return
        if value_type is _bool:
            yield "true" if value else "false"
            return
        if value_type is _int:
            yield _str(value)
            return
        if value_type is _float:
            if not _isfinite(value):
                raise _value_error(f"{path} must contain finite numbers")
            yield _repr(value)
            return
        if value_type is _str:
            yield encode_string(value, path)
            return
        identity = _id(value)
        if value_type in (_list, _tuple):
            if identity in active:
                raise _value_error(f"{path} contains a cyclic array")
            active.add(identity)
            try:
                yield "["
                for index, item in _enumerate(value):
                    if index:
                        yield ","
                    yield from encode_chunks(
                        item,
                        f"{path}[{index}]",
                        active,
                    )
                yield "]"
            finally:
                active.remove(identity)
            return
        if value_type is _dict:
            if identity in active:
                raise _value_error(f"{path} contains a cyclic mapping")
            active.add(identity)
            try:
                yield "{"
                keys = _sorted(value)
                for index, key in _enumerate(keys):
                    if _type(key) is not _str:
                        raise _type_error(f"{path} mapping key must be a str")
                    if index:
                        yield ","
                    yield encode_string(key, f"{path}.key[{index}]")
                    yield ":"
                    yield from encode_chunks(
                        value[key],
                        f"{path}.{key}",
                        active,
                    )
                yield "}"
            finally:
                active.remove(identity)
            return
        raise _type_error(f"{path} contains non-JSON type {value_type.__name__}")

    def canonical(payload: dict[str, object]) -> str:
        if _type(payload) is not _dict:
            raise _type_error("canonical payload must be an exact dict")
        digest = _sha256()
        total = 0
        for chunk in encode_chunks(payload, "$", _set()):
            encoded = chunk.encode("utf-8")
            total += _len(encoded)
            if total > body_bytes_max:
                raise _value_error("canonical body exceeds the resource cap")
            digest.update(encoded)
        return digest.hexdigest()

    def structural_copy(value: object) -> object:
        value_type = _type(value)
        if (
            value is None
            or value_type in (_str, _bool, _int, _float)
            or value_type is _undefined_reason_type
        ):
            return value
        if value_type in record_field_names:
            clone = _object.__new__(value_type)
            for name in record_field_names[value_type]:
                _object.__setattr__(
                    clone,
                    name,
                    structural_copy(_object.__getattribute__(value, name)),
                )
            return clone
        if value_type is _tuple:
            return _tuple(structural_copy(item) for item in value)
        if value_type is _list:
            return [structural_copy(item) for item in value]
        if value_type is _dict:
            return {
                structural_copy(key): structural_copy(item)
                for key, item in value.items()
            }
        raise _type_error("structural copy encountered an unsupported type")

    def make_record(record_type: type, values: dict[str, object]) -> object:
        names = record_field_names.get(record_type)
        if names is None or _frozenset(values) != _frozenset(names):
            raise _value_error("record construction fields differ")
        result = _object.__new__(record_type)
        for name in names:
            _object.__setattr__(result, name, values[name])
        return result

    def structural_replace(value: object, changes: dict[str, object]) -> object:
        value_type = _type(value)
        names = record_field_names.get(value_type)
        if names is None or not _set(changes).issubset(names):
            raise _value_error("record replacement fields differ")
        values = {
            name: (
                changes[name]
                if name in changes
                else _object.__getattribute__(value, name)
            )
            for name in names
        }
        return make_record(value_type, values)

    def status_payload(status: BlockStatus) -> dict[str, object]:
        if _type(status) is not _status_type:
            raise _type_error("status must be an exact BlockStatus")
        return {
            "defined": status.defined,
            "reason": None if status.reason is None else status.reason.value,
        }

    def snapshot_record(snapshot: AblationPairSnapshot) -> dict[str, object]:
        return {
            **_snapshot_payload(snapshot),
            "snapshot_sha": snapshot.snapshot_sha,
        }

    def report_record(report: AblationDynamicsReport) -> dict[str, object]:
        return {
            **_report_payload(report),
            "report_sha": report.report_sha,
        }

    def evidence_payload(
        evidence: CertificateBackedQualificationEvidence,
    ) -> dict[str, object]:
        return {
            "evidence_schema_version": evidence.evidence_schema_version,
            "construction_status": status_payload(evidence.construction_status),
            "pair_snapshot": snapshot_record(evidence.pair_snapshot),
            "dynamics_report": report_record(evidence.dynamics_report),
            "verified_certificate_sha": evidence.verified_certificate_sha,
        }

    def outcome_payload(
        outcome: CertificateBackedQualificationOutcome,
    ) -> dict[str, object]:
        return {
            "status": status_payload(outcome.status),
            "evidence": (
                None
                if outcome.evidence is None
                else {
                    **evidence_payload(outcome.evidence),
                    "evidence_sha": outcome.evidence.evidence_sha,
                }
            ),
        }

    def validate(outcome: CertificateBackedQualificationOutcome) -> None:
        if _type(outcome) is not _outcome_type:
            raise _type_error("outcome must be CertificateBackedQualificationOutcome")
        require_exact(outcome, "outcome", _set())
        evidence = outcome.evidence
        if (
            _type(outcome.status) is not _status_type
            or not outcome.status.defined
            or outcome.status.reason is not None
            or _type(evidence) is not _evidence_type
        ):
            raise _value_error("qualification outcome presence is invalid")
        if (
            evidence.evidence_schema_version != _evidence_schema
            or _type(evidence.construction_status) is not _status_type
            or evidence.construction_status != outcome.status
            or _type(evidence.pair_snapshot) is not _snapshot_type
            or _type(evidence.dynamics_report) is not _report_type
        ):
            raise _value_error("qualification evidence schema is invalid")
        if evidence.evidence_sha != canonical(
            evidence_payload(evidence)
        ) or outcome.outcome_sha != canonical(outcome_payload(outcome)):
            raise _value_error("qualification self SHA mismatch")

    def expected(
        construction: AblationConstructionOutcome,
        certificate: VerifiedDynamicsCertificate,
    ) -> CertificateBackedQualificationOutcome:
        if _type(construction) is not _construction_type:
            raise _type_error("construction must be an AblationConstructionOutcome")
        if _type(certificate) is not _certificate_type:
            raise _type_error("certificate must be a VerifiedDynamicsCertificate")
        verified_construction = _verify_construction(construction)
        if (
            verified_construction is not construction
            or not verified_construction.status.defined
            or verified_construction.pair is None
        ):
            raise _value_error(
                "certificate-backed qualification requires a defined construction"
            )
        snapshot, actual_factory, ablated_factory = _snapshot_builder(
            verified_construction
        )
        del actual_factory
        preflight(snapshot, "pair_snapshot")
        certificate_record = _certificate_reverify(certificate)
        try:
            private_certificate = _object.__getattribute__(
                certificate,
                "_VerifiedDynamicsCertificate__certificate",
            )
        except _attribute_error as exc:
            raise _value_error("certificate authority is incomplete") from exc
        if (
            certificate_record.certificate != private_certificate
            or certificate_record.factory is not ablated_factory
        ):
            raise _value_error("qualification certificate live view is inconsistent")
        authority_view = _prestructure_reverify(certificate_record.authority)
        raw_certificate = private_certificate
        if (
            authority_view.authority != raw_certificate.prestructure_authority
            or authority_view.factory is not ablated_factory
            or authority_view.construction is not verified_construction
        ):
            raise _value_error("certificate prestructure is not construction-bound")
        if (
            raw_certificate.prestructure_authority.factory_role != "matched_ablated"
            or raw_certificate.prestructure_authority.ablation_pair_snapshot != snapshot
        ):
            raise _value_error(
                "certificate pair snapshot differs from live construction"
            )
        certificate_sha = raw_certificate.certificate_sha
        report_provisional = make_record(
            _report_type,
            {
                "report_schema_version": _report_schema,
                "factory_sha": snapshot.ablated_factory.factory_sha,
                "state_schema_matches": True,
                "reversible": True,
                "stable": True,
                "certificate_sha": certificate_sha,
                "report_sha": "0" * 64,
            },
        )
        report = structural_replace(
            report_provisional,
            {"report_sha": canonical(report_record(report_provisional))},
        )
        evidence_provisional = make_record(
            _evidence_type,
            {
                "evidence_schema_version": _evidence_schema,
                "construction_status": verified_construction.status,
                "pair_snapshot": snapshot,
                "dynamics_report": report,
                "verified_certificate_sha": certificate_sha,
                "evidence_sha": "0" * 64,
            },
        )
        preflight(evidence_provisional, "qualification_evidence")
        evidence = structural_replace(
            evidence_provisional,
            {"evidence_sha": canonical(evidence_payload(evidence_provisional))},
        )
        defined_status = make_record(
            _status_type,
            {
                "defined": True,
                "reason": None,
            },
        )
        outcome_provisional = make_record(
            _outcome_type,
            {
                "status": defined_status,
                "evidence": evidence,
                "outcome_sha": "0" * 64,
            },
        )
        preflight(outcome_provisional, "qualification_outcome")
        return structural_replace(
            outcome_provisional,
            {"outcome_sha": canonical(outcome_payload(outcome_provisional))},
        )

    def seal(outcome: CertificateBackedQualificationOutcome) -> str:
        return canonical(
            {
                "authority_schema_version": _authority_schema,
                "outcome": {
                    **outcome_payload(outcome),
                    "outcome_sha": outcome.outcome_sha,
                },
            }
        )

    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedCertificateBackedQualification],
            _QualificationAuthority,
        ],
    ] = {}
    lock = _rlock()

    def issue(
        construction: AblationConstructionOutcome,
        certificate: VerifiedDynamicsCertificate,
        raw: Optional[CertificateBackedQualificationOutcome] = None,
    ) -> VerifiedCertificateBackedQualification:
        if raw is not None:
            if _type(raw) is not _outcome_type:
                raise _type_error(
                    "raw outcome must be CertificateBackedQualificationOutcome"
                )
            preflight(raw, "qualification_outcome")
            require_exact(raw, "qualification_outcome", _set())
            validate(raw)
        expected_outcome = expected(construction, certificate)
        if raw is not None:
            require_parallel_exact(
                raw,
                expected_outcome,
                "qualification_outcome",
                _set(),
            )
            if raw != expected_outcome:
                raise _value_error("raw qualification differs from live reconstruction")
        authority_outcome = structural_copy(expected_outcome)
        exposed_outcome = structural_copy(expected_outcome)
        authority_seal = seal(authority_outcome)
        wrapper = _wrapper_type(
            _token,
            exposed_outcome,
            authority_seal,
        )
        identity = _id(wrapper)
        authority = _authority_type(
            outcome=authority_outcome,
            construction=construction,
            certificate=certificate,
            seal=authority_seal,
        )

        def remove(
            reference: weakref.ReferenceType[VerifiedCertificateBackedQualification],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = _weakref_ref(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        return wrapper

    def reverify(
        wrapper: VerifiedCertificateBackedQualification,
    ) -> _VerifiedQualificationView:
        if _type(wrapper) is not _wrapper_type:
            raise _type_error(
                "qualification consumer requires a module-issued capability"
            )
        with lock:
            current = live.get(_id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise _value_error("qualification identity is not live")
            authority = current[1]
        try:
            token = _object.__getattribute__(
                wrapper,
                "_VerifiedCertificateBackedQualification__token",
            )
            raw = _object.__getattribute__(
                wrapper,
                "_VerifiedCertificateBackedQualification__outcome",
            )
            raw_seal = _object.__getattribute__(
                wrapper,
                "_VerifiedCertificateBackedQualification__seal",
            )
        except _attribute_error as exc:
            raise _value_error("qualification authority is incomplete") from exc
        if token is not _token:
            raise _value_error("qualification authority token mismatch")
        preflight(raw, "qualification_outcome")
        validate(raw)
        expected_outcome = expected(
            authority.construction,
            authority.certificate,
        )
        expected_seal = seal(expected_outcome)
        if (
            raw != authority.outcome
            or authority.outcome != expected_outcome
            or raw_seal != authority.seal
            or raw_seal != expected_seal
        ):
            raise _value_error("qualification immutable seal mismatch")
        return _view_type(
            outcome=structural_copy(authority.outcome),
            construction=authority.construction,
            certificate=authority.certificate,
        )

    return issue, reverify


def _freeze_qualification_call_graph(
    root: Callable,
    *,
    _partial_type=functools.partial,
) -> object:
    """Clone every reachable project function into private globals."""

    function_memo: dict[int, Callable] = {}
    module_memo: dict[tuple[int, tuple[str, ...]], object] = {}

    def referenced_code_names(code: types.CodeType) -> tuple[str, ...]:
        names = list(code.co_names)
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                names.extend(referenced_code_names(constant))
        return tuple(dict.fromkeys(names))

    def freeze_value(
        value: object,
        referenced_names: tuple[str, ...] = (),
    ) -> object:
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if type(value) is _partial_type:
            keywords = value.keywords or {}
            return _partial_type(
                freeze_value(value.func),
                *(freeze_value(item) for item in value.args),
                **{key: freeze_value(item) for key, item in keywords.items()},
            )
        if inspect.ismodule(value):
            module_values = vars(value)
            key = (id(value), referenced_names)
            cached_module = module_memo.get(key)
            if cached_module is not None:
                return cached_module
            proxy = types.SimpleNamespace()
            module_memo[key] = proxy
            for name in referenced_names:
                if name in module_values:
                    setattr(
                        proxy,
                        name,
                        freeze_value(
                            module_values[name],
                            referenced_names,
                        ),
                    )
            return proxy
        if type(value) is tuple:
            return tuple(freeze_value(item) for item in value)
        if type(value) is list:
            return [freeze_value(item) for item in value]
        if type(value) is dict:
            return {key: freeze_value(item) for key, item in value.items()}
        return value

    def freeze_closure_value(value: object) -> object:
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if type(value) is _partial_type:
            return freeze_value(value)
        if type(value) is tuple:
            return tuple(freeze_closure_value(item) for item in value)
        return value

    def make_cell(value: object) -> object:
        def read_cell() -> object:
            return value

        return read_cell.__closure__[0]

    def freeze_function(function: Callable) -> Callable:
        cached = function_memo.get(id(function))
        if cached is not None:
            return cached
        source_globals = function.__globals__
        builtins_body = source_globals.get("__builtins__", {})
        private_builtins = (
            dict(builtins_body)
            if type(builtins_body) is dict
            else dict(vars(builtins_body))
        )
        private_globals: dict[str, object] = {
            "__builtins__": private_builtins,
            "__name__": source_globals.get("__name__", __name__),
            "__package__": source_globals.get("__package__", __package__),
        }
        source_closure = function.__closure__
        private_cells = (
            None
            if source_closure is None
            else tuple(make_cell(None) for _ in source_closure)
        )
        clone = types.FunctionType(
            function.__code__,
            private_globals,
            function.__name__,
            None,
            private_cells,
        )
        function_memo[id(function)] = clone
        if source_closure is not None:
            assert private_cells is not None
            for private_cell, source_cell in zip(
                private_cells,
                source_closure,
            ):
                private_cell.cell_contents = freeze_closure_value(
                    source_cell.cell_contents
                )
        referenced_names = referenced_code_names(function.__code__)
        for name in referenced_names:
            if name in source_globals:
                private_globals[name] = freeze_value(
                    source_globals[name],
                    referenced_names,
                )
        clone.__defaults__ = (
            None
            if function.__defaults__ is None
            else tuple(freeze_value(item) for item in function.__defaults__)
        )
        clone.__kwdefaults__ = (
            None
            if function.__kwdefaults__ is None
            else {
                key: freeze_value(item) for key, item in function.__kwdefaults__.items()
            }
        )
        return clone

    return functools.partial(freeze_function(root))


_closed_make_qualification_authority = _freeze_qualification_call_graph(
    _make_qualification_authority
)
(
    _issue_verified_certificate_backed_qualification,
    _reverify_verified_certificate_backed_qualification,
) = _closed_make_qualification_authority()


def _install_frozen_outcome_property(
    reverify: Callable[
        [VerifiedCertificateBackedQualification],
        _VerifiedQualificationView,
    ],
) -> None:
    def outcome(
        wrapper: VerifiedCertificateBackedQualification,
    ) -> CertificateBackedQualificationOutcome:
        return reverify(wrapper).outcome

    VerifiedCertificateBackedQualification.outcome = property(outcome)


_install_frozen_outcome_property(_reverify_verified_certificate_backed_qualification)


def _make_public_qualification_boundaries(
    issue: Callable[..., VerifiedCertificateBackedQualification],
) -> tuple[Callable, Callable]:
    def qualify_ablation_from_certificate(
        construction: AblationConstructionOutcome,
        ablated_certificate: VerifiedDynamicsCertificate,
    ) -> VerifiedCertificateBackedQualification:
        """Issue only from the exact matched-ablated live certificate."""

        return issue(
            construction,
            ablated_certificate,
        )

    def verify_qualified_ablation_from_certificate(
        outcome: CertificateBackedQualificationOutcome,
        construction: AblationConstructionOutcome,
        ablated_certificate: VerifiedDynamicsCertificate,
    ) -> VerifiedCertificateBackedQualification:
        """Hydrate a raw outcome by replaying construction and certificate."""

        return issue(
            construction,
            ablated_certificate,
            raw=outcome,
        )

    return (
        qualify_ablation_from_certificate,
        verify_qualified_ablation_from_certificate,
    )


(
    qualify_ablation_from_certificate,
    verify_qualified_ablation_from_certificate,
) = _make_public_qualification_boundaries(
    _issue_verified_certificate_backed_qualification
)


def dependency_boundary() -> tuple[str, str, str]:
    """Expose the reviewed one-way integration modules for DAG tests."""

    return (
        AblationConstructionOutcome.__module__,
        MeasuredTransition.__module__,
        VerifiedDynamicsCertificate.__module__,
    )


__all__ = [
    "QUALIFICATION_AUTHORITY_SCHEMA_VERSION",
    "QUALIFICATION_EVIDENCE_SCHEMA_VERSION",
    "QUALIFICATION_OUTCOME_SCHEMA_VERSION",
    "CertificateBackedQualificationEvidence",
    "CertificateBackedQualificationOutcome",
    "VerifiedCertificateBackedQualification",
    "certificate_backed_qualification_evidence_payload",
    "certificate_backed_qualification_outcome_payload",
    "dependency_boundary",
    "qualify_ablation_from_certificate",
    "verify_qualified_ablation_from_certificate",
]
