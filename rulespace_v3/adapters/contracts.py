"""Pure, fail-closed handoff contracts for historical V3-M1 adapters.

This module intentionally does not import or execute any historical physics
module.  An :class:`AdapterContract` records the source and schema boundary
that V3-M1 must later certify.  It is not a dynamics certificate, a parent
freeze, a calibration permit, or scientific evidence.

``AdapterCommitmentReceipt`` is likewise only the raw Git receipt wire frozen
by Task 10.  Its self-hash establishes content identity, not wall-clock
priority or external anchoring.  V3-M0 exports no authority issuer for it.
"""

from __future__ import annotations

import builtins
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path, PurePosixPath
import re
from typing import Literal, NamedTuple


ADAPTER_COMMITMENT_RECEIPT_SCHEMA_VERSION = "v3m1.adapter-commitment-receipt.v1"
ADAPTER_ONE_STEP_CERTIFICATE_SCHEMA_VERSION = (
    "v3m1.adapter-one-step-kernel-equivalence-certificate.v1"
)
ADAPTER_MULTISTEP_CERTIFICATE_SCHEMA_VERSION = (
    "v3m1.adapter-multistep-response-equivalence-certificate.v1"
)
ADAPTER_CONTRACT_WIRE_SCHEMA_VERSION = "v3m0.adapter-contract-wire.v1"

ADAPTER_IDS = ("R23", "R30", "R25")
ADAPTER_CONTRACT_MAX_ROOTS = 64
ADAPTER_CONTRACT_MAX_PROVENANCE_ANCESTRY = 256
ADAPTER_CONTRACT_MAX_BLOB_ENTRIES = 256
ADAPTER_CONTRACT_MAX_ANCESTRY_COMMITS = 1_024
ADAPTER_CONTRACT_MAX_TEXT_BYTES = 4_096
ADAPTER_CONTRACT_MAX_WIRE_BYTES = 65_536
ADAPTER_CONTRACT_MAX_SOURCE_BYTES = 4_194_304

_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_GIT_OBJECT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_ADAPTER_CONTRACT_FIELDS = (
    "adapter_id",
    "target_spec_id",
    "frozen_source_sha",
    "state_schema_id",
    "source_manifest_id",
    "readout_manifest_id",
    "target_conditioned_roots",
    "target_blind_roots",
    "one_step_certificate_schema",
    "multistep_certificate_schema",
    "commitment_receipt_schema",
    "certification_state",
)
_ADAPTER_CONTRACT_WIRE_FIELDS = (
    *_ADAPTER_CONTRACT_FIELDS,
    "adapter_contract_sha",
)
_RECEIPT_FIELDS = (
    "receipt_schema_version",
    "repository_identity",
    "commit_sha",
    "committed_blob_shas",
    "clean_source_tree_sha",
    "required_ancestor_commit_sha",
    "ancestry_path",
    "external_anchor_id",
    "receipt_sha",
)
_RECEIPT_PAYLOAD_FIELDS = _RECEIPT_FIELDS[:-1]


def _make_canonical_json_primitives(
    *,
    _sha256=hashlib.sha256,
    _type=type,
    _str=str,
    _bool=bool,
    _int=int,
    _list=list,
    _tuple=tuple,
    _dict=dict,
    _sorted=sorted,
    _ord=ord,
):
    escapes = {
        '"': '\\"',
        "\\": "\\\\",
        "\b": "\\b",
        "\f": "\\f",
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }

    def encode_string(value: str) -> str:
        pieces = ['"']
        for character in value:
            escaped = escapes.get(character)
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

    def encode_value(value: object) -> str:
        if value is None:
            return "null"
        if _type(value) is _bool:
            return "true" if value else "false"
        if _type(value) is _int:
            return _str(value)
        if _type(value) is _str:
            return encode_string(value)
        if _type(value) in (_list, _tuple):
            return "[" + ",".join(encode_value(item) for item in value) + "]"
        if _type(value) is _dict:
            for key in value:
                if _type(key) is not _str:
                    raise TypeError("adapter canonical mapping keys must be strings")
            return (
                "{"
                + ",".join(
                    f"{encode_string(key)}:{encode_value(value[key])}"
                    for key in _sorted(value)
                )
                + "}"
            )
        raise TypeError(
            "adapter canonical JSON contains unsupported value type "
            f"{_type(value).__name__}"
        )

    def encode_bytes(value: object) -> bytes:
        return encode_value(value).encode("utf-8")

    def sha(payload: object) -> str:
        if _type(payload) is not _dict:
            raise TypeError("adapter hash payload must be a plain dict")
        return _sha256(encode_bytes(payload)).hexdigest()

    return encode_bytes, sha


_CANONICAL_JSON_BYTES, _CANONICAL_SHA = _make_canonical_json_primitives()


def canonical_sha(payload: dict[str, object]) -> str:
    """Public compatibility surface; security-sensitive paths use a frozen hash."""

    return _CANONICAL_SHA(payload)


def _text(
    value: object,
    field: str,
    _type=type,
    _str_type=str,
    _maximum_text_bytes: int = 4_096,
) -> str:
    if _type(value) is not _str_type:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    if len(value.encode("utf-8")) > _maximum_text_bytes:
        raise ValueError(f"{field} exceeds the text resource cap")
    return value


def _sha256(
    value: object,
    field: str,
    _text_validator=_text,
    _fullmatch=_LOWER_SHA256.fullmatch,
) -> str:
    text = _text_validator(value, field)
    if _fullmatch(text) is None:
        raise ValueError(f"{field} must be a 64-digit lowercase hexadecimal SHA-256")
    return text


def _git_object_sha(
    value: object,
    field: str,
    _text_validator=_text,
    _fullmatch=_LOWER_GIT_OBJECT_SHA.fullmatch,
) -> str:
    text = _text_validator(value, field)
    if _fullmatch(text) is None:
        raise ValueError(f"{field} must be a 40-digit lowercase Git object SHA")
    return text


def _relative_source_path(
    value: object,
    field: str,
    _text_validator=_text,
    _path_type=PurePosixPath,
) -> str:
    text = _text_validator(value, field)
    path = _path_type(text)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"{field} must be a canonical repository-relative path")
    if path.as_posix() != text:
        raise ValueError(f"{field} must use canonical POSIX separators")
    return text


def _canonical_string_tuple(
    value: object,
    field: str,
    *,
    maximum: int,
    _type=type,
    _tuple_type=tuple,
    _text_validator=_text,
    _sorted=sorted,
) -> tuple[str, ...]:
    if _type(value) is not _tuple_type:
        raise TypeError(f"{field} must be a tuple")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    if len(value) > maximum:
        raise ValueError(f"{field} exceeds its root resource cap maximum")
    result = _tuple_type(
        _text_validator(item, f"{field}[{index}]") for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise ValueError(f"{field} contains duplicate roots")
    if result != _tuple_type(_sorted(result)):
        raise ValueError(f"{field} must be in canonical sorted order")
    return result


def _require_exact_instance_fields(
    value: object,
    expected_type: type,
    expected_fields: tuple[str, ...],
    field: str,
    _type=type,
    _tuple_type=tuple,
    _hasattr=hasattr,
    _getattr=getattr,
) -> None:
    if _type(value) is not expected_type:
        raise TypeError(f"{field} must be an exact {expected_type.__name__}")
    if _hasattr(value, "__dict__"):
        raise ValueError(f"{field} has unknown or missing instance fields")
    slots = _getattr(expected_type, "__slots__", ())
    if _tuple_type(slots) != expected_fields:
        raise ValueError(f"{field} has unknown or missing record slots")
    for name in expected_fields:
        try:
            _getattr(value, name)
        except AttributeError as exc:
            raise ValueError(f"{field} is missing {name}") from exc


def _validate_adapter_contract_fields(
    contract: object,
    _text_validator=_text,
    _sha_validator=_sha256,
    _roots_validator=_canonical_string_tuple,
    _adapter_ids: tuple[str, ...] = ("R23", "R30", "R25"),
    _max_roots: int = 64,
    _getattr=getattr,
) -> None:
    adapter_id = _text_validator(_getattr(contract, "adapter_id"), "adapter_id")
    if adapter_id not in _adapter_ids:
        raise ValueError("adapter_id is outside the closed R23/R30/R25 registry")
    for field in (
        "target_spec_id",
        "state_schema_id",
        "source_manifest_id",
        "readout_manifest_id",
        "one_step_certificate_schema",
        "multistep_certificate_schema",
        "commitment_receipt_schema",
    ):
        _text_validator(_getattr(contract, field), field)
    _sha_validator(_getattr(contract, "frozen_source_sha"), "frozen_source_sha")
    conditioned = _roots_validator(
        _getattr(contract, "target_conditioned_roots"),
        "target_conditioned_roots",
        maximum=_max_roots,
    )
    blind = _roots_validator(
        _getattr(contract, "target_blind_roots"),
        "target_blind_roots",
        maximum=_max_roots,
    )
    if not set(conditioned).isdisjoint(blind):
        raise ValueError("target-conditioned and target-blind roots overlap")
    if _getattr(contract, "certification_state") != "PENDING_V3M1":
        raise ValueError("adapter certification_state must remain PENDING_V3M1")


@dataclass(frozen=True)
class AdapterContract:
    __slots__ = _ADAPTER_CONTRACT_FIELDS

    adapter_id: str
    target_spec_id: str
    frozen_source_sha: str
    state_schema_id: str
    source_manifest_id: str
    readout_manifest_id: str
    target_conditioned_roots: tuple[str, ...]
    target_blind_roots: tuple[str, ...]
    one_step_certificate_schema: str
    multistep_certificate_schema: str
    commitment_receipt_schema: str
    certification_state: Literal["PENDING_V3M1"]

    def __post_init__(
        self,
        _validator=_validate_adapter_contract_fields,
    ) -> None:
        _validator(self)


class _ExpectedAdapter(NamedTuple):
    adapter_id: str
    target_spec_id: str
    frozen_source_sha: str
    state_schema_id: str
    source_manifest_id: str
    readout_manifest_id: str
    target_conditioned_roots: tuple[str, ...]
    target_blind_roots: tuple[str, ...]
    one_step_certificate_schema: str
    multistep_certificate_schema: str
    commitment_receipt_schema: str
    certification_state: str
    source_path: str


_EXPECTED_ADAPTERS = (
    _ExpectedAdapter(
        adapter_id="R23",
        target_spec_id="spin1.maxwell.v1",
        frozen_source_sha=(
            "38ea5bbf5282209f720c754e1f5b17a802a5e7aae19197a3b030b440402e4263"
        ),
        state_schema_id="state.legacy.r23.yee-eb-staggered.v1",
        source_manifest_id="source.legacy.r23.full-eb.v1",
        readout_manifest_id="readout.legacy.r23.maxwell-field-strength.v1",
        target_conditioned_roots=tuple(
            sorted(
                (
                    "experiments/r17_placement_operators.py::placed-Yee-coefficients",
                    "experiments/r23_maxwell_control.py::Lorenz-constraint",
                    "experiments/v2m1_candidate.py::curl-assembly",
                    "experiments/v2m1_candidate.py::target-selector-DM11-A",
                )
            )
        ),
        target_blind_roots=tuple(
            sorted(
                (
                    "experiments/photon_control.py::integer-roll",
                    "experiments/photon_control.py::local-leapfrog",
                )
            )
        ),
        one_step_certificate_schema=(ADAPTER_ONE_STEP_CERTIFICATE_SCHEMA_VERSION),
        multistep_certificate_schema=(ADAPTER_MULTISTEP_CERTIFICATE_SCHEMA_VERSION),
        commitment_receipt_schema=(ADAPTER_COMMITMENT_RECEIPT_SCHEMA_VERSION),
        certification_state="PENDING_V3M1",
        source_path="experiments/photon_control.py",
    ),
    _ExpectedAdapter(
        adapter_id="R30",
        target_spec_id="spin2.linearized.v1",
        frozen_source_sha=(
            "eae6034d8403a93977988d0a56e80c8899b9ffe80fcacc4084fc0244b2d519a4"
        ),
        state_schema_id="state.legacy.r30.packed-h10-pi10.v1",
        source_manifest_id="source.legacy.r30.full-hpi.v1",
        readout_manifest_id="readout.legacy.r30.placed-riemann.v1",
        target_conditioned_roots=tuple(
            sorted(
                (
                    "experiments/r30_tensor_complex_dynamical.py::C",
                    "experiments/r30_tensor_complex_dynamical.py::TT-basis",
                    "experiments/r30_tensor_complex_dynamical.py::inc-Riemann",
                    "experiments/r30_tensor_complex_dynamical.py::kerC",
                    "experiments/r30_tensor_complex_dynamical.py::placed-coefficients",
                )
            )
        ),
        target_blind_roots=tuple(
            sorted(
                (
                    "experiments/r30_tensor_complex_dynamical.py::integer-roll",
                    "experiments/r30_tensor_complex_dynamical.py::local-canonical-leapfrog",
                )
            )
        ),
        one_step_certificate_schema=(ADAPTER_ONE_STEP_CERTIFICATE_SCHEMA_VERSION),
        multistep_certificate_schema=(ADAPTER_MULTISTEP_CERTIFICATE_SCHEMA_VERSION),
        commitment_receipt_schema=(ADAPTER_COMMITMENT_RECEIPT_SCHEMA_VERSION),
        certification_state="PENDING_V3M1",
        source_path="experiments/r30_tensor_complex_dynamical.py",
    ),
    _ExpectedAdapter(
        adapter_id="R25",
        target_spec_id="spin2.linearized.v1",
        frozen_source_sha=(
            "a66f6082e03c45b55687ad60859257e0993dc04f30185e212ff3e4bd62331445"
        ),
        state_schema_id="state.legacy.r25.chiral-h14-pi14.v1",
        source_manifest_id="source.legacy.r25.full-hpi.v1",
        readout_manifest_id="readout.legacy.r25.placed-riemann.v1",
        target_conditioned_roots=tuple(
            sorted(
                (
                    "experiments/r25_auxiliary_wilson_complex.py::Wilson-constraint",
                    "experiments/r25_realspace_step.py::de-Donder-constraint",
                    "experiments/r32_reachability_probe.py::target-repair",
                    "experiments/r32_reachability_probe.py::target-selector",
                )
            )
        ),
        target_blind_roots=tuple(
            sorted(
                (
                    "experiments/r25_realspace_step.py::integer-roll",
                    "rulespace_gpu/green_one_walk.py::frozen-matter-walk",
                )
            )
        ),
        one_step_certificate_schema=(ADAPTER_ONE_STEP_CERTIFICATE_SCHEMA_VERSION),
        multistep_certificate_schema=(ADAPTER_MULTISTEP_CERTIFICATE_SCHEMA_VERSION),
        commitment_receipt_schema=(ADAPTER_COMMITMENT_RECEIPT_SCHEMA_VERSION),
        certification_state="PENDING_V3M1",
        source_path="experiments/r25_realspace_step.py",
    ),
)

_MODULE_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_OPEN_BINARY = builtins.open
_SOURCE_SHA256 = hashlib.sha256


def _contract_from_expected(
    expected: _ExpectedAdapter,
    _record_type=AdapterContract,
    _fields: tuple[str, ...] = _ADAPTER_CONTRACT_FIELDS,
) -> AdapterContract:
    return _record_type(**{field: getattr(expected, field) for field in _fields})


def get_adapter_contract(
    adapter_id: str,
    _expected_adapters: tuple[_ExpectedAdapter, ...] = _EXPECTED_ADAPTERS,
    _text_validator=_text,
    _builder=_contract_from_expected,
) -> AdapterContract:
    """Return a fresh inert contract from the closed historical registry."""

    _text_validator(adapter_id, "adapter_id")
    matches = tuple(
        expected for expected in _expected_adapters if expected.adapter_id == adapter_id
    )
    if len(matches) != 1:
        raise ValueError("adapter_id is outside the closed R23/R30/R25 registry")
    return _builder(matches[0])


def all_adapter_contracts(
    _expected_adapters: tuple[_ExpectedAdapter, ...] = _EXPECTED_ADAPTERS,
    _builder=_contract_from_expected,
) -> tuple[AdapterContract, ...]:
    """Return all three contracts in their preregistered handoff order."""

    return tuple(_builder(item) for item in _expected_adapters)


def adapter_contract_payload(
    contract: AdapterContract,
    _require=_require_exact_instance_fields,
    _record_type=AdapterContract,
    _fields: tuple[str, ...] = _ADAPTER_CONTRACT_FIELDS,
    _validator=_validate_adapter_contract_fields,
    _list_type=list,
) -> dict[str, object]:
    """Return the exact self-hash body, excluding the derived SHA."""

    _require(
        contract,
        _record_type,
        _fields,
        "contract",
    )
    _validator(contract)
    return {
        "adapter_id": contract.adapter_id,
        "target_spec_id": contract.target_spec_id,
        "frozen_source_sha": contract.frozen_source_sha,
        "state_schema_id": contract.state_schema_id,
        "source_manifest_id": contract.source_manifest_id,
        "readout_manifest_id": contract.readout_manifest_id,
        "target_conditioned_roots": _list_type(contract.target_conditioned_roots),
        "target_blind_roots": _list_type(contract.target_blind_roots),
        "one_step_certificate_schema": contract.one_step_certificate_schema,
        "multistep_certificate_schema": (contract.multistep_certificate_schema),
        "commitment_receipt_schema": contract.commitment_receipt_schema,
        "certification_state": contract.certification_state,
    }


def adapter_contract_sha(
    contract: AdapterContract,
    _hash=_CANONICAL_SHA,
    _payload=adapter_contract_payload,
) -> str:
    """Hash the complete contract body without granting verification status."""

    return _hash(_payload(contract))


def adapter_source_path(
    contract: AdapterContract,
    _expected_adapters: tuple[_ExpectedAdapter, ...] = _EXPECTED_ADAPTERS,
    _require=_require_exact_instance_fields,
    _record_type=AdapterContract,
    _fields: tuple[str, ...] = _ADAPTER_CONTRACT_FIELDS,
) -> str:
    """Return the frozen legacy factory path without importing that factory."""

    _require(
        contract,
        _record_type,
        _fields,
        "contract",
    )
    matches = tuple(
        expected
        for expected in _expected_adapters
        if expected.adapter_id == contract.adapter_id
    )
    if len(matches) != 1:
        raise ValueError("adapter contract has no frozen source registry entry")
    return matches[0].source_path


def verify_adapter_source(
    contract: AdapterContract,
    _expected_adapters: tuple[_ExpectedAdapter, ...] = _EXPECTED_ADAPTERS,
    _repository_root: Path = _MODULE_REPOSITORY_ROOT,
    _open_binary=_OPEN_BINARY,
    _sha256_impl=_SOURCE_SHA256,
    _require=_require_exact_instance_fields,
    _record_type=AdapterContract,
    _fields: tuple[str, ...] = _ADAPTER_CONTRACT_FIELDS,
    _source_path=adapter_source_path,
    _path_validator=_relative_source_path,
    _path_stat=Path.stat,
    _path_is_file=Path.is_file,
    _max_source_bytes: int = 4_194_304,
) -> AdapterContract:
    """Verify only frozen source bytes; never import or execute legacy code."""

    _require(
        contract,
        _record_type,
        _fields,
        "contract",
    )
    path_text = _source_path(
        contract,
        _expected_adapters=_expected_adapters,
    )
    _path_validator(path_text, "source_path")
    path = _repository_root / path_text
    try:
        stat_result = _path_stat(path)
    except OSError as exc:
        raise ValueError("frozen adapter source is unavailable") from exc
    if not _path_is_file(path):
        raise ValueError("frozen adapter source is not a regular file")
    if stat_result.st_size > _max_source_bytes:
        raise ValueError("frozen adapter source exceeds the source resource cap")
    try:
        with _open_binary(path, "rb") as handle:
            body = handle.read(_max_source_bytes + 1)
    except OSError as exc:
        raise ValueError("frozen adapter source cannot be read") from exc
    if len(body) > _max_source_bytes:
        raise ValueError("frozen adapter source exceeds the source resource cap")
    if len(body) != stat_result.st_size:
        raise ValueError("frozen adapter source changed during verification")
    observed = _sha256_impl(body).hexdigest()
    if observed != contract.frozen_source_sha:
        raise ValueError("frozen adapter source SHA does not match the contract")
    return contract


def verify_adapter_contract(
    contract: AdapterContract,
    _expected_adapters: tuple[_ExpectedAdapter, ...] = _EXPECTED_ADAPTERS,
    _source_verifier=verify_adapter_source,
    _payload=adapter_contract_payload,
    _builder=_contract_from_expected,
) -> AdapterContract:
    """Verify a closed pending contract; return no opaque V3 authority."""

    payload = _payload(contract)
    matches = tuple(
        expected
        for expected in _expected_adapters
        if expected.adapter_id == contract.adapter_id
    )
    if len(matches) != 1:
        raise ValueError("adapter contract is outside the frozen registry")
    expected_payload = _payload(_builder(matches[0]))
    if payload != expected_payload:
        raise ValueError("adapter contract differs from the frozen canonical body")
    _source_verifier(
        contract,
        _expected_adapters=_expected_adapters,
    )
    return contract


def _wire_dict(
    wire: object,
    *,
    expected_fields: tuple[str, ...],
    field: str,
    _type=type,
    _dict_type=dict,
    _len=len,
    _set=set,
    _str_type=str,
) -> dict[str, object]:
    if _type(wire) is not _dict_type:
        raise TypeError(f"{field} must be a plain dict")
    if _len(wire) != _len(expected_fields) or _set(wire) != _set(expected_fields):
        raise ValueError(f"{field} has unknown or missing fields")
    for key in wire:
        if _type(key) is not _str_type:
            raise TypeError(f"{field} keys must be strings")
    return wire


def _wire_root_list(
    value: object,
    field: str,
    _type=type,
    _list_type=list,
    _tuple_type=tuple,
    _len=len,
    _text_validator=_text,
    _maximum_roots: int = 64,
) -> tuple[str, ...]:
    if _type(value) is not _list_type:
        raise TypeError(f"{field} must be a list on the wire")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    if _len(value) > _maximum_roots:
        raise ValueError(f"{field} exceeds its root resource cap maximum")
    result = _tuple_type(
        _text_validator(item, f"{field}[{index}]") for index, item in enumerate(value)
    )
    return result


def _wire_body_cap(
    payload: dict[str, object],
    field: str,
    _encoder=_CANONICAL_JSON_BYTES,
    _maximum_wire_bytes: int = 65_536,
) -> None:
    body = _encoder(payload)
    if len(body) > _maximum_wire_bytes:
        raise ValueError(f"{field} exceeds the serialized wire resource cap")


def adapter_contract_to_wire(
    contract: AdapterContract,
    _verifier=verify_adapter_contract,
    _hash=_CANONICAL_SHA,
    _payload=adapter_contract_payload,
    _body_cap=_wire_body_cap,
) -> dict[str, object]:
    """Serialize one verified pending contract to an exact self-hashed wire."""

    _verifier(contract)
    payload = _payload(contract)
    _body_cap(payload, "adapter contract")
    return {**payload, "adapter_contract_sha": _hash(payload)}


def adapter_contract_from_wire(
    wire: object,
    _hash=_CANONICAL_SHA,
    _verifier=verify_adapter_contract,
    _wire_parser=_wire_dict,
    _wire_fields: tuple[str, ...] = _ADAPTER_CONTRACT_WIRE_FIELDS,
    _root_parser=_wire_root_list,
    _sha_validator=_sha256,
    _record_type=AdapterContract,
    _payload=adapter_contract_payload,
    _body_cap=_wire_body_cap,
) -> AdapterContract:
    """Strictly decode and replay one complete contract wire."""

    body = _wire_parser(
        wire,
        expected_fields=_wire_fields,
        field="adapter contract wire",
    )
    conditioned = _root_parser(
        body["target_conditioned_roots"],
        "target_conditioned_roots",
    )
    blind = _root_parser(
        body["target_blind_roots"],
        "target_blind_roots",
    )
    claimed_sha = _sha_validator(
        body["adapter_contract_sha"],
        "adapter_contract_sha",
    )
    contract = _record_type(
        adapter_id=body["adapter_id"],
        target_spec_id=body["target_spec_id"],
        frozen_source_sha=body["frozen_source_sha"],
        state_schema_id=body["state_schema_id"],
        source_manifest_id=body["source_manifest_id"],
        readout_manifest_id=body["readout_manifest_id"],
        target_conditioned_roots=conditioned,
        target_blind_roots=blind,
        one_step_certificate_schema=body["one_step_certificate_schema"],
        multistep_certificate_schema=body["multistep_certificate_schema"],
        commitment_receipt_schema=body["commitment_receipt_schema"],
        certification_state=body["certification_state"],
    )
    payload = _payload(contract)
    _body_cap(payload, "adapter contract")
    if claimed_sha != _hash(payload):
        raise ValueError("adapter contract self-hash does not match its body")
    _verifier(contract)
    return contract


def _make_adapter_ancestry_classifier(
    *,
    verifier=verify_adapter_contract,
    maximum_ancestry: int = 256,
    text_validator=_text,
    isfinite=math.isfinite,
    type_of=type,
    tuple_type=tuple,
    string_type=str,
    integer_type=int,
    float_type=float,
    length=len,
    enumerate_items=enumerate,
    type_error=TypeError,
    value_error=ValueError,
):
    neutral_derivations = frozenset(("cache", "copy", "rename"))

    def classify_adapter_ancestry(
        contract: AdapterContract,
        ancestry: tuple[object, ...],
    ) -> Literal["target_conditioned", "target_blind", "unclassified"]:
        """Join provenance under module-frozen caps and validators."""

        if type_of(ancestry) is not tuple_type:
            raise type_error("ancestry must be a tuple")
        if not ancestry:
            raise value_error("ancestry must be non-empty")
        if length(ancestry) > maximum_ancestry:
            raise value_error("ancestry exceeds the provenance resource cap")

        verifier(contract)
        saw_conditioned = False
        saw_unclassified = False
        saw_blind = False
        for index, item in enumerate_items(ancestry):
            if type_of(item) is string_type:
                text_validator(item, f"ancestry[{index}]")
                if item in contract.target_conditioned_roots:
                    saw_conditioned = True
                elif item in contract.target_blind_roots:
                    saw_blind = True
                elif item in neutral_derivations:
                    continue
                elif item.startswith("literal:"):
                    saw_unclassified = True
                else:
                    raise value_error(
                        f"ancestry[{index}] is an unclassified caller root"
                    )
            elif type_of(item) is integer_type:
                saw_unclassified = True
            elif type_of(item) is float_type:
                if not isfinite(item):
                    raise value_error(f"ancestry[{index}] literal must be finite")
                saw_unclassified = True
            else:
                raise type_error(
                    f"ancestry[{index}] has an unsupported provenance type"
                )

        if saw_conditioned:
            return "target_conditioned"
        if saw_unclassified:
            return "unclassified"
        if saw_blind:
            return "target_blind"
        return "unclassified"

    return classify_adapter_ancestry


classify_adapter_ancestry = _make_adapter_ancestry_classifier()


def _validate_receipt_fields(
    receipt: object,
    _schema_version: str = "v3m1.adapter-commitment-receipt.v1",
    _text_validator=_text,
    _git_sha_validator=_git_object_sha,
    _source_path_validator=_relative_source_path,
    _sha_validator=_sha256,
    _type=type,
    _tuple_type=tuple,
    _len=len,
    _set=set,
    _sorted=sorted,
    _getattr=getattr,
    _max_blobs: int = 256,
    _max_ancestry: int = 1_024,
) -> None:
    if _getattr(receipt, "receipt_schema_version") != _schema_version:
        raise ValueError("receipt_schema_version is not the frozen schema")
    _text_validator(
        _getattr(receipt, "repository_identity"),
        "repository_identity",
    )
    commit_sha = _git_sha_validator(
        _getattr(receipt, "commit_sha"),
        "commit_sha",
    )
    committed_blobs = _getattr(receipt, "committed_blob_shas")
    if _type(committed_blobs) is not _tuple_type:
        raise TypeError("committed_blob_shas must be a tuple")
    if not committed_blobs:
        raise ValueError("committed_blob_shas must be non-empty")
    if _len(committed_blobs) > _max_blobs:
        raise ValueError("committed_blob_shas exceeds the blob resource cap")
    normalized_blobs = []
    for index, entry in enumerate(committed_blobs):
        if _type(entry) is not _tuple_type or _len(entry) != 2:
            raise TypeError(f"committed_blob_shas[{index}] must be a path/SHA tuple")
        path = _source_path_validator(
            entry[0],
            f"committed_blob_shas[{index}][0]",
        )
        blob_sha = _git_sha_validator(
            entry[1],
            f"committed_blob_shas[{index}][1]",
        )
        normalized_blobs.append((path, blob_sha))
    if _tuple_type(normalized_blobs) != _tuple_type(_sorted(normalized_blobs)):
        raise ValueError("committed_blob_shas must be in canonical path order")
    if _len(_set(path for path, _ in normalized_blobs)) != _len(normalized_blobs):
        raise ValueError("committed_blob_shas contains duplicate paths")
    _sha_validator(
        _getattr(receipt, "clean_source_tree_sha"),
        "clean_source_tree_sha",
    )
    ancestor = _git_sha_validator(
        _getattr(receipt, "required_ancestor_commit_sha"),
        "required_ancestor_commit_sha",
    )
    raw_ancestry = _getattr(receipt, "ancestry_path")
    if _type(raw_ancestry) is not _tuple_type:
        raise TypeError("ancestry_path must be a tuple")
    if not raw_ancestry:
        raise ValueError("ancestry_path must be non-empty")
    if _len(raw_ancestry) > _max_ancestry:
        raise ValueError("ancestry_path exceeds the ancestry resource cap")
    ancestry = _tuple_type(
        _git_sha_validator(value, f"ancestry_path[{index}]")
        for index, value in enumerate(raw_ancestry)
    )
    if _len(_set(ancestry)) != _len(ancestry):
        raise ValueError("ancestry_path contains a repeated commit")
    if ancestry[0] != ancestor:
        raise ValueError("ancestry_path must begin at required ancestor")
    if ancestry[-1] != commit_sha:
        raise ValueError("ancestry_path must end at commit_sha")
    _text_validator(
        _getattr(receipt, "external_anchor_id"),
        "external_anchor_id",
    )
    _sha_validator(_getattr(receipt, "receipt_sha"), "receipt_sha")


@dataclass(frozen=True)
class AdapterCommitmentReceipt:
    __slots__ = _RECEIPT_FIELDS

    receipt_schema_version: str
    repository_identity: str
    commit_sha: str
    committed_blob_shas: tuple[tuple[str, str], ...]
    clean_source_tree_sha: str
    required_ancestor_commit_sha: str
    ancestry_path: tuple[str, ...]
    external_anchor_id: str
    receipt_sha: str

    def __post_init__(
        self,
        _validator=_validate_receipt_fields,
    ) -> None:
        _validator(self)


def adapter_commitment_receipt_payload(
    receipt: AdapterCommitmentReceipt,
    _require=_require_exact_instance_fields,
    _record_type=AdapterCommitmentReceipt,
    _fields: tuple[str, ...] = _RECEIPT_FIELDS,
    _validator=_validate_receipt_fields,
    _list_type=list,
) -> dict[str, object]:
    """Return the exact raw receipt self-hash body."""

    _require(
        receipt,
        _record_type,
        _fields,
        "receipt",
    )
    _validator(receipt)
    return {
        "receipt_schema_version": receipt.receipt_schema_version,
        "repository_identity": receipt.repository_identity,
        "commit_sha": receipt.commit_sha,
        "committed_blob_shas": [
            _list_type((path, sha)) for path, sha in receipt.committed_blob_shas
        ],
        "clean_source_tree_sha": receipt.clean_source_tree_sha,
        "required_ancestor_commit_sha": (receipt.required_ancestor_commit_sha),
        "ancestry_path": _list_type(receipt.ancestry_path),
        "external_anchor_id": receipt.external_anchor_id,
    }


def adapter_commitment_receipt_sha(
    receipt: AdapterCommitmentReceipt,
    _hash=_CANONICAL_SHA,
    _payload=adapter_commitment_receipt_payload,
) -> str:
    """Hash a raw receipt body without validating its external anchor."""

    return _hash(_payload(receipt))


def validate_adapter_commitment_receipt(
    receipt: AdapterCommitmentReceipt,
    _hash=_CANONICAL_SHA,
    _payload=adapter_commitment_receipt_payload,
    _body_cap=_wire_body_cap,
) -> AdapterCommitmentReceipt:
    """Validate raw receipt shape and self-hash only; grant no authority."""

    payload = _payload(receipt)
    _body_cap(payload, "adapter commitment receipt")
    if receipt.receipt_sha != _hash(payload):
        raise ValueError("adapter commitment receipt self-hash mismatch")
    return receipt


def adapter_commitment_receipt_to_wire(
    receipt: AdapterCommitmentReceipt,
    _validator=validate_adapter_commitment_receipt,
    _payload=adapter_commitment_receipt_payload,
) -> dict[str, object]:
    """Serialize a self-consistent raw receipt, without external verification."""

    _validator(receipt)
    return {
        **_payload(receipt),
        "receipt_sha": receipt.receipt_sha,
    }


def _wire_blob_entries(
    value: object,
    _type=type,
    _list_type=list,
    _tuple_type=tuple,
    _len=len,
    _path_validator=_relative_source_path,
    _git_sha_validator=_git_object_sha,
    _maximum_blobs: int = 256,
) -> tuple[tuple[str, str], ...]:
    if _type(value) is not _list_type:
        raise TypeError("committed_blob_shas must be a list on the wire")
    if not value:
        raise ValueError("committed_blob_shas must be non-empty")
    if _len(value) > _maximum_blobs:
        raise ValueError("committed_blob_shas exceeds the blob resource cap")
    entries = []
    for index, entry in enumerate(value):
        if _type(entry) is not _list_type or _len(entry) != 2:
            raise TypeError(f"committed_blob_shas[{index}] must be a two-item list")
        entries.append(
            (
                _path_validator(
                    entry[0],
                    f"committed_blob_shas[{index}][0]",
                ),
                _git_sha_validator(
                    entry[1],
                    f"committed_blob_shas[{index}][1]",
                ),
            )
        )
    return _tuple_type(entries)


def _wire_ancestry(
    value: object,
    _type=type,
    _list_type=list,
    _tuple_type=tuple,
    _len=len,
    _git_sha_validator=_git_object_sha,
    _maximum_ancestry: int = 1_024,
) -> tuple[str, ...]:
    if _type(value) is not _list_type:
        raise TypeError("ancestry_path must be a list on the wire")
    if not value:
        raise ValueError("ancestry_path must be non-empty")
    if _len(value) > _maximum_ancestry:
        raise ValueError("ancestry_path exceeds the ancestry resource cap")
    return _tuple_type(
        _git_sha_validator(item, f"ancestry_path[{index}]")
        for index, item in enumerate(value)
    )


def adapter_commitment_receipt_from_wire(
    wire: object,
    _validator=validate_adapter_commitment_receipt,
    _wire_parser=_wire_dict,
    _wire_fields: tuple[str, ...] = _RECEIPT_FIELDS,
    _blob_parser=_wire_blob_entries,
    _ancestry_parser=_wire_ancestry,
    _record_type=AdapterCommitmentReceipt,
) -> AdapterCommitmentReceipt:
    """Strictly decode a raw receipt; do not interpret it as an anchor."""

    body = _wire_parser(
        wire,
        expected_fields=_wire_fields,
        field="adapter commitment receipt wire",
    )
    blobs = _blob_parser(body["committed_blob_shas"])
    ancestry = _ancestry_parser(body["ancestry_path"])
    receipt = _record_type(
        receipt_schema_version=body["receipt_schema_version"],
        repository_identity=body["repository_identity"],
        commit_sha=body["commit_sha"],
        committed_blob_shas=blobs,
        clean_source_tree_sha=body["clean_source_tree_sha"],
        required_ancestor_commit_sha=body["required_ancestor_commit_sha"],
        ancestry_path=ancestry,
        external_anchor_id=body["external_anchor_id"],
        receipt_sha=body["receipt_sha"],
    )
    _validator(receipt)
    return receipt


__all__ = [
    "ADAPTER_COMMITMENT_RECEIPT_SCHEMA_VERSION",
    "ADAPTER_CONTRACT_MAX_ANCESTRY_COMMITS",
    "ADAPTER_CONTRACT_MAX_BLOB_ENTRIES",
    "ADAPTER_CONTRACT_MAX_PROVENANCE_ANCESTRY",
    "ADAPTER_CONTRACT_MAX_ROOTS",
    "ADAPTER_CONTRACT_MAX_SOURCE_BYTES",
    "ADAPTER_CONTRACT_MAX_TEXT_BYTES",
    "ADAPTER_CONTRACT_MAX_WIRE_BYTES",
    "ADAPTER_CONTRACT_WIRE_SCHEMA_VERSION",
    "ADAPTER_IDS",
    "ADAPTER_MULTISTEP_CERTIFICATE_SCHEMA_VERSION",
    "ADAPTER_ONE_STEP_CERTIFICATE_SCHEMA_VERSION",
    "AdapterCommitmentReceipt",
    "AdapterContract",
    "adapter_commitment_receipt_from_wire",
    "adapter_commitment_receipt_payload",
    "adapter_commitment_receipt_sha",
    "adapter_commitment_receipt_to_wire",
    "adapter_contract_from_wire",
    "adapter_contract_payload",
    "adapter_contract_sha",
    "adapter_contract_to_wire",
    "adapter_source_path",
    "all_adapter_contracts",
    "canonical_sha",
    "classify_adapter_ancestry",
    "get_adapter_contract",
    "validate_adapter_commitment_receipt",
    "verify_adapter_contract",
    "verify_adapter_source",
]
