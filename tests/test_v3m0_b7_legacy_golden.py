from __future__ import annotations

import dataclasses
import hashlib
import json
import struct
import subprocess
import typing
from enum import Enum
from fractions import Fraction
from pathlib import Path

from rulespace_v3.certificate import (
    DynamicsCertificate,
    dynamics_certificate_payload,
)
from rulespace_v3.dynamics import MeasuredTransition, measured_transition_payload
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import FrozenComplexTensor, frozen_tensor_payload
from rulespace_v3.response import (
    PAIRED_RESPONSE_SCHEMA_VERSION,
    EndpointShellOutcome,
    PairedFilteredResponse,
    PairedResponseFailure,
    PairedResponseOutcome,
    ResponseRunSpec,
    SourceReadoutBridgeAudit,
    _build_source_readout_response_from_values,
    endpoint_shell_outcome_payload,
    paired_filtered_response_payload,
    paired_response_outcome_payload,
    response_run_spec_payload,
    source_readout_bridge_audit_payload,
)
from rulespace_v3.window import (
    WindowCalibrationProtocol,
    window_calibration_protocol_payload,
)

import rulespace_v3.response as response_module


SOURCE_COMMIT_SHA = "18b0d4302658c376fcc237a56fc1dc28bf6dd95e"
RESPONSE_SOURCE_PATH = "rulespace_v3/response.py"
RESPONSE_SOURCE_RAW_SHA256 = (
    "d8670ba98a153eef660e22fcdca45fd56e68140445e1b17ef6f273d0ab7f9b89"
)
FIXTURE_RAW_SHA256 = "9dd2340c93abcda020434fc6e7ab41f4625a7cf4acbd722fc830986fd9622612"
FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "v3m0_b7_legacy_response_18b0d43.json"
)
CASE_ORDER = (
    "qualification_invalid",
    "input_binding_invalid",
    "actual_response_failed",
    "ablated_response_failed",
    "actual_bridge_failed",
    "ablated_bridge_failed",
    "success",
)
CASE_FIELD_ORDER = (
    "case_id",
    "expected_failure",
    "complete_input_wire",
    "complete_outcome_wire",
    "canonical_utf8_hex",
    "literal_sha256",
    "callback_trace",
    "presence",
    "fp64_bits",
    "negative_zero_paths",
    "ordered_leaf_digests",
)
_INPUT_RECORD_TYPES = {
    "window_protocol": WindowCalibrationProtocol,
    "actual_transition": MeasuredTransition,
    "ablated_transition": MeasuredTransition,
    "actual_dynamics_certificate": DynamicsCertificate,
    "ablated_dynamics_certificate": DynamicsCertificate,
    "run_spec": ResponseRunSpec,
    "shell_outcome": EndpointShellOutcome,
    "actual_response_values": FrozenComplexTensor,
    "ablated_response_values": FrozenComplexTensor,
    "actual_bridge_audit": SourceReadoutBridgeAudit,
    "ablated_bridge_audit": SourceReadoutBridgeAudit,
}
_FAIL_STAGE_BY_CASE = {
    "actual_response_failed": "actual_values",
    "ablated_response_failed": "ablated_values",
    "actual_bridge_failed": "actual_bridge",
    "ablated_bridge_failed": "ablated_bridge",
    "success": None,
}


def _trusted_git_object(path: str) -> bytes:
    completed = subprocess.run(
        [
            "/usr/bin/git",
            "--no-pager",
            "--no-replace-objects",
            "show",
            f"{SOURCE_COMMIT_SHA}:{path}",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _record(payload: dict[str, object], field: str, value: str) -> dict[str, object]:
    return {**payload, field: value}


def _tensor_wire(value: FrozenComplexTensor) -> dict[str, object]:
    return _record(frozen_tensor_payload(value), "tensor_sha", value.tensor_sha)


def _bridge_wire(value: SourceReadoutBridgeAudit) -> dict[str, object]:
    return _record(
        source_readout_bridge_audit_payload(value),
        "bridge_sha",
        value.bridge_sha,
    )


def complete_input_wire(
    *,
    injected_failure: typing.Optional[str],
    window_protocol: WindowCalibrationProtocol,
    qualification_sha: str,
    actual_factory_sha: str,
    ablated_factory_sha: str,
    actual_transition: MeasuredTransition,
    ablated_transition: MeasuredTransition,
    actual_dynamics_certificate: DynamicsCertificate,
    ablated_dynamics_certificate: DynamicsCertificate,
    run_spec: ResponseRunSpec,
    shell_outcome: EndpointShellOutcome,
    ablation_manifest_sha: str,
    actual_response_values: FrozenComplexTensor,
    ablated_response_values: FrozenComplexTensor,
    actual_bridge_audit: SourceReadoutBridgeAudit,
    ablated_bridge_audit: SourceReadoutBridgeAudit,
) -> dict[str, object]:
    """Return every inert input body consumed by the seven-case replay."""

    return {
        "injected_failure": injected_failure,
        "window_protocol": _record(
            window_calibration_protocol_payload(window_protocol),
            "protocol_sha",
            window_protocol.protocol_sha,
        ),
        "qualification_sha": qualification_sha,
        "actual_factory_sha": actual_factory_sha,
        "ablated_factory_sha": ablated_factory_sha,
        "actual_transition": _record(
            measured_transition_payload(actual_transition),
            "transition_sha",
            actual_transition.transition_sha,
        ),
        "ablated_transition": _record(
            measured_transition_payload(ablated_transition),
            "transition_sha",
            ablated_transition.transition_sha,
        ),
        "actual_dynamics_certificate": _record(
            dynamics_certificate_payload(actual_dynamics_certificate),
            "certificate_sha",
            actual_dynamics_certificate.certificate_sha,
        ),
        "ablated_dynamics_certificate": _record(
            dynamics_certificate_payload(ablated_dynamics_certificate),
            "certificate_sha",
            ablated_dynamics_certificate.certificate_sha,
        ),
        "run_spec": _record(
            response_run_spec_payload(run_spec),
            "spec_sha",
            run_spec.spec_sha,
        ),
        "shell_outcome": _record(
            endpoint_shell_outcome_payload(shell_outcome),
            "outcome_sha",
            shell_outcome.outcome_sha,
        ),
        "ablation_manifest_sha": ablation_manifest_sha,
        "actual_response_values": _tensor_wire(actual_response_values),
        "ablated_response_values": _tensor_wire(ablated_response_values),
        "actual_bridge_audit": _bridge_wire(actual_bridge_audit),
        "ablated_bridge_audit": _bridge_wire(ablated_bridge_audit),
    }


def _hydrate(annotation: object, wire: object) -> object:
    origin = typing.get_origin(annotation)
    arguments = typing.get_args(annotation)
    if origin is typing.Union:
        if wire is None and type(None) in arguments:
            return None
        candidates = tuple(item for item in arguments if item is not type(None))
        if len(candidates) != 1:
            raise TypeError(f"unsupported union annotation {annotation!r}")
        return _hydrate(candidates[0], wire)
    if origin is typing.Literal:
        if wire not in arguments:
            raise ValueError(f"wire literal {wire!r} is outside {arguments!r}")
        return wire
    if origin is tuple:
        if (
            arguments == (str, str)
            and type(wire) is dict
            and tuple(wire)
            == (
                "relative_path",
                "sha256",
            )
        ):
            return (wire["relative_path"], wire["sha256"])
        if type(wire) is not list:
            raise TypeError(
                f"tuple wire for {annotation!r} must be a list; got {wire!r}"
            )
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            return tuple(_hydrate(arguments[0], item) for item in wire)
        if len(arguments) != len(wire):
            raise ValueError("fixed tuple wire has the wrong length")
        return tuple(
            _hydrate(item_type, item) for item_type, item in zip(arguments, wire)
        )
    if origin is list:
        if type(wire) is not list or len(arguments) != 1:
            raise TypeError("list wire or annotation is invalid")
        return [_hydrate(arguments[0], item) for item in wire]
    if origin is dict:
        if type(wire) is not dict or len(arguments) != 2:
            raise TypeError("dict wire or annotation is invalid")
        return {
            _hydrate(arguments[0], key): _hydrate(arguments[1], value)
            for key, value in wire.items()
        }
    if annotation is typing.Any or annotation is object:
        return wire
    if annotation is Fraction:
        if (
            type(wire) is not list
            or len(wire) != 2
            or any(type(item) is not int for item in wire)
        ):
            raise TypeError("Fraction wire must be [int, int]")
        return Fraction(wire[0], wire[1])
    if annotation is bytes:
        if type(wire) is not str:
            raise TypeError("bytes wire must be hexadecimal text")
        return bytes.fromhex(wire)
    if annotation in (str, int, float, bool):
        if type(wire) is not annotation:
            raise TypeError(f"wire value is not an exact {annotation.__name__}")
        return wire
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(wire)
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        if type(wire) is not dict:
            raise TypeError(f"{annotation.__name__} wire must be an object")
        fields = dataclasses.fields(annotation)
        if tuple(wire) != tuple(item.name for item in fields):
            raise ValueError(f"{annotation.__name__} wire field order differs")
        hints = typing.get_type_hints(annotation)
        result = object.__new__(annotation)
        for field in fields:
            object.__setattr__(
                result,
                field.name,
                _hydrate(hints[field.name], wire[field.name]),
            )
        return result
    raise TypeError(f"unsupported hydration annotation {annotation!r}")


def hydrate_complete_input(wire: dict[str, object]) -> dict[str, object]:
    if type(wire) is not dict:
        raise TypeError("complete input wire must be an object")
    expected_fields = (
        "injected_failure",
        "window_protocol",
        "qualification_sha",
        "actual_factory_sha",
        "ablated_factory_sha",
        "actual_transition",
        "ablated_transition",
        "actual_dynamics_certificate",
        "ablated_dynamics_certificate",
        "run_spec",
        "shell_outcome",
        "ablation_manifest_sha",
        "actual_response_values",
        "ablated_response_values",
        "actual_bridge_audit",
        "ablated_bridge_audit",
    )
    if tuple(wire) != expected_fields:
        raise ValueError("complete input wire field order differs")
    result: dict[str, object] = {}
    for field, value in wire.items():
        expected = _INPUT_RECORD_TYPES.get(field)
        result[field] = value if expected is None else _hydrate(expected, value)
    return result


def _outcome_wire(outcome: PairedResponseOutcome) -> dict[str, object]:
    return _record(
        paired_response_outcome_payload(outcome),
        "outcome_sha",
        outcome.outcome_sha,
    )


def _leaf_input_body(name: str, inputs: dict[str, object]) -> dict[str, object]:
    transition_key = (
        "actual_transition" if name.startswith("actual") else "ablated_transition"
    )
    certificate_key = (
        "actual_dynamics_certificate"
        if name.startswith("actual")
        else "ablated_dynamics_certificate"
    )
    return {
        "leaf_id": name,
        "branch": "actual" if name.startswith("actual") else "matched_ablated",
        "run_spec_sha": inputs["run_spec"].spec_sha,
        "factory_sha": inputs[
            f"{'actual' if name.startswith('actual') else 'ablated'}_factory_sha"
        ],
        "transition_sha": inputs[transition_key].transition_sha,
        "dynamics_certificate_sha": inputs[certificate_key].certificate_sha,
        "shell_outcome_sha": inputs["shell_outcome"].outcome_sha,
    }


def _presence(outcome: PairedResponseOutcome) -> dict[str, bool]:
    attempt = outcome.attempt_audit
    actual = attempt.actual_branch_attempt
    ablated = attempt.ablated_branch_attempt
    paired = outcome.paired_response
    return {
        "actual_branch_attempt": actual is not None,
        "actual_response_values": actual is not None
        and actual.response_values is not None,
        "actual_bridge_audit": actual is not None and actual.bridge_audit is not None,
        "ablated_branch_attempt": ablated is not None,
        "ablated_response_values": ablated is not None
        and ablated.response_values is not None,
        "ablated_bridge_audit": ablated is not None
        and ablated.bridge_audit is not None,
        "paired_response": paired is not None,
        "actual_completed_response": paired is not None,
        "ablated_completed_response": paired is not None,
    }


def _fp64_bits(value: object) -> tuple[list[dict[str, str]], list[str]]:
    observed: list[dict[str, str]] = []
    negative_zero: list[str] = []

    def visit(item: object, path: str) -> None:
        if type(item) is float:
            bits = struct.pack(">d", item).hex()
            observed.append({"path": path, "bits": bits})
            if bits == "8000000000000000":
                negative_zero.append(path)
            return
        if type(item) is list:
            for index, child in enumerate(item):
                visit(child, f"{path}/{index}")
            return
        if type(item) is dict:
            for key, child in item.items():
                escaped = key.replace("~", "~0").replace("/", "~1")
                visit(child, f"{path}/{escaped}")

    visit(value, "")
    return observed, negative_zero


def replay_case(case_id: str, complete_wire: dict[str, object]) -> dict[str, object]:
    inputs = hydrate_complete_input(complete_wire)
    if (
        complete_input_wire(**inputs) != complete_wire  # type: ignore[arg-type]
    ):
        raise AssertionError("hydrated legacy input does not round-trip exactly")
    expected_injection = None if case_id == "success" else case_id
    if inputs["injected_failure"] != expected_injection:
        raise AssertionError("legacy failure injection differs from its case")

    callback_trace: list[str] = []
    leaf_digests: list[dict[str, object]] = []
    if case_id in ("qualification_invalid", "input_binding_invalid"):
        failure = PairedResponseFailure(case_id)
        outcome = response_module._paired_prebranch_failure(
            failure=failure,
            window_protocol=inputs["window_protocol"],
            qualification_sha=inputs["qualification_sha"],
            actual_factory_sha=inputs["actual_factory_sha"],
            ablated_factory_sha=inputs["ablated_factory_sha"],
            actual_transition=inputs["actual_transition"],
            ablated_transition=inputs["ablated_transition"],
            actual_dynamics_certificate=inputs["actual_dynamics_certificate"],
            ablated_dynamics_certificate=inputs["ablated_dynamics_certificate"],
            run_spec=inputs["run_spec"],
            shell_outcome=inputs["shell_outcome"],
        )
    else:
        fail_at = _FAIL_STAGE_BY_CASE[case_id]

        def stage(name: str, result: object):
            def invoke():
                callback_trace.append(name)
                input_body = _leaf_input_body(name, inputs)
                if fail_at == name:
                    output_body: object = {
                        "error": "injected-v3m0-b7-legacy-golden-failure",
                        "leaf_id": name,
                    }
                elif type(result) is FrozenComplexTensor:
                    output_body = _tensor_wire(result)
                else:
                    output_body = _bridge_wire(result)
                leaf_digests.append(
                    {
                        "leaf_id": name,
                        "call_ordinal": len(callback_trace) - 1,
                        "input_body_sha": hashlib.sha256(
                            _canonical_bytes(input_body)
                        ).hexdigest(),
                        "output_body_sha": hashlib.sha256(
                            _canonical_bytes(output_body)
                        ).hexdigest(),
                    }
                )
                if fail_at == name:
                    raise ValueError(output_body["error"])
                return result

            return invoke

        actual_attempt, ablated_attempt, failure = (
            response_module._run_atomic_paired_branch_attempts(
                actual_values_call=stage(
                    "actual_values", inputs["actual_response_values"]
                ),
                actual_bridge_call=stage(
                    "actual_bridge", inputs["actual_bridge_audit"]
                ),
                ablated_values_call=stage(
                    "ablated_values", inputs["ablated_response_values"]
                ),
                ablated_bridge_call=stage(
                    "ablated_bridge", inputs["ablated_bridge_audit"]
                ),
            )
        )
        paired = None
        if failure is None:
            if ablated_attempt is None:
                raise AssertionError("successful legacy replay lacks ablated attempt")
            shell_outcome = inputs["shell_outcome"]
            if shell_outcome.shell is None:
                raise AssertionError("successful legacy replay lacks shell manifest")
            actual_response = _build_source_readout_response_from_values(
                branch="actual",
                factory_sha=inputs["actual_factory_sha"],
                transition_sha=inputs["actual_transition"].transition_sha,
                dynamics_certificate_sha=inputs[
                    "actual_dynamics_certificate"
                ].certificate_sha,
                run_spec=inputs["run_spec"],
                shell_manifest_sha=shell_outcome.shell.shell_manifest_sha,
                bridge_audit=actual_attempt.bridge_audit,
                values=actual_attempt.response_values,
            )
            ablated_response = _build_source_readout_response_from_values(
                branch="matched_ablated",
                factory_sha=inputs["ablated_factory_sha"],
                transition_sha=inputs["ablated_transition"].transition_sha,
                dynamics_certificate_sha=inputs[
                    "ablated_dynamics_certificate"
                ].certificate_sha,
                run_spec=inputs["run_spec"],
                shell_manifest_sha=shell_outcome.shell.shell_manifest_sha,
                bridge_audit=ablated_attempt.bridge_audit,
                values=ablated_attempt.response_values,
            )
            provisional_pair = PairedFilteredResponse(
                pair_schema_version=PAIRED_RESPONSE_SCHEMA_VERSION,
                ablation_manifest_sha=inputs["ablation_manifest_sha"],
                qualification_sha=inputs["qualification_sha"],
                actual_dynamics_certificate=inputs["actual_dynamics_certificate"],
                ablated_dynamics_certificate=inputs["ablated_dynamics_certificate"],
                actual=actual_response,
                ablated=ablated_response,
                run_spec=inputs["run_spec"],
                shell_manifest=shell_outcome.shell,
                pair_sha="0" * 64,
            )
            paired = dataclasses.replace(
                provisional_pair,
                pair_sha=canonical_sha(
                    paired_filtered_response_payload(provisional_pair)
                ),
            )
        attempt = response_module._paired_attempt_audit(
            window_protocol=inputs["window_protocol"],
            qualification_sha=inputs["qualification_sha"],
            actual_factory_sha=inputs["actual_factory_sha"],
            ablated_factory_sha=inputs["ablated_factory_sha"],
            actual_transition=inputs["actual_transition"],
            ablated_transition=inputs["ablated_transition"],
            actual_dynamics_certificate=inputs["actual_dynamics_certificate"],
            ablated_dynamics_certificate=inputs["ablated_dynamics_certificate"],
            run_spec=inputs["run_spec"],
            shell_outcome=inputs["shell_outcome"],
            actual_branch_attempt=actual_attempt,
            ablated_branch_attempt=ablated_attempt,
            first_failure=failure,
        )
        outcome = response_module._paired_outcome(attempt, failure, paired)

    outcome_wire = _outcome_wire(outcome)
    canonical = _canonical_bytes(outcome_wire)
    fp64_bits, negative_zero_paths = _fp64_bits(
        {"complete_input_wire": complete_wire, "complete_outcome_wire": outcome_wire}
    )
    return {
        "case_id": case_id,
        "expected_failure": None if outcome.failure is None else outcome.failure.value,
        "complete_input_wire": complete_wire,
        "complete_outcome_wire": outcome_wire,
        "canonical_utf8_hex": canonical.hex(),
        "literal_sha256": hashlib.sha256(canonical).hexdigest(),
        "callback_trace": callback_trace,
        "presence": _presence(outcome),
        "fp64_bits": fp64_bits,
        "negative_zero_paths": negative_zero_paths,
        "ordered_leaf_digests": leaf_digests,
    }


def test_legacy_response_golden_replays_exactly() -> None:
    source_bytes = _trusted_git_object(RESPONSE_SOURCE_PATH)
    assert hashlib.sha256(source_bytes).hexdigest() == RESPONSE_SOURCE_RAW_SHA256

    fixture_bytes = FIXTURE_PATH.read_bytes()
    assert hashlib.sha256(fixture_bytes).hexdigest() == FIXTURE_RAW_SHA256
    fixture = json.loads(fixture_bytes)
    assert tuple(fixture) == (
        "fixture_schema_version",
        "source_commit_sha",
        "response_source_path",
        "response_source_raw_sha256",
        "cases",
    )
    assert fixture["fixture_schema_version"] == "v3m0.b7.legacy-response-golden.v1"
    assert fixture["source_commit_sha"] == SOURCE_COMMIT_SHA
    assert fixture["response_source_path"] == RESPONSE_SOURCE_PATH
    assert fixture["response_source_raw_sha256"] == RESPONSE_SOURCE_RAW_SHA256
    cases = fixture["cases"]
    assert tuple(case["case_id"] for case in cases) == CASE_ORDER
    assert all(tuple(case) == CASE_FIELD_ORDER for case in cases)
    assert [
        replay_case(case["case_id"], case["complete_input_wire"]) for case in cases
    ] == cases
