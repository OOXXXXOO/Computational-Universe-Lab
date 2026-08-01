"""Parent-v3 Task-11 calibration and application-permit authority.

The dataclasses in this module are serialization wires, never capabilities.
Only live wrappers issued by the closed graph below authorize downstream use.
Every verification replays the Parent-v3 registry and Task-11 numerical chain;
raw bodies, old wrappers, cross-Parent values, and copied thresholds fail closed.
"""

from __future__ import annotations

import copy
import re
import threading
import weakref
from collections.abc import Callable
from dataclasses import dataclass, fields as dataclass_fields, replace

from .calibration_authority import (
    WindowCalibrationOutcome,
    canonical_sha,
    window_calibration_outcome_payload,
)
from .parent_authority_v3 import (
    VerifiedParentFreezeV3,
    require_current_parent_v3,
)
from .parent_candidate_v3 import (
    current_application_authority_v2_payload,
    current_application_registry_v3_payload,
)
from .parent_freeze import (
    APPLICATION_CONTROL_CASE_IDS,
    VerifiedParentFreeze,
    _reverify_verified_parent_freeze,
    issue_v3m0_parent_freeze,
)
from .parent_v3_contracts import (
    CurrentApplicationAuthorityV3,
    CurrentScenarioAuthorityV3,
    CurrentScenarioResponseContractV3,
    current_application_authority_v3_payload,
    current_scenario_authority_v3_payload,
    current_scenario_response_contract_v3_payload,
    verify_current_application_authority_v3,
)
from .task11_runner import _run_task11_window_calibration_from_task8_replay
from .task8_control_replay import _replay_current_task8_control_roots


PARENT_V3_CALIBRATION_CONTROL_REPLAY_REF_V1_SCHEMA_VERSION = (
    "v3m0.parent-v3-calibration-control-replay-ref.v1"
)
WINDOW_THRESHOLD_CALIBRATION_V3_SCHEMA_VERSION = "v3m0.window-threshold-calibration.v3"
CALIBRATION_APPLICATION_PERMIT_V3_SCHEMA_VERSION = (
    "v3m0.calibration-application-permit.v3"
)
CALIBRATION_APPLICATION_PERMIT_V3_SCOPE_ID = (
    "v3m0-parent-v3-current-application-scenario-v1"
)
_CURRENT_APPLICATION_REGISTRY_V3_SCHEMA_VERSION = "v3m0.current-application-registry.v3"
_CALIBRATION_CONTROLS = (
    (0, "C01_BLIND_HOLDOUT_FULL", "full"),
    (1, "C02_CONDITIONED_ZERO", "zero"),
    (2, "C03_EQUAL_RANK_DIRECT_SUM", "direct_sum"),
)
_FAILURE_REASON_IDS = frozenset(
    (
        "PARENT_V3_UNAVAILABLE",
        "CALIBRATION_REPLAY_FAILED",
        "WINDOW_UNRESOLVED",
        "CURRENT_APPLICATION_MISSING",
        "SCENARIO_MISSING",
        "CROSS_PARENT_ROOT",
    )
)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in dataclass_fields(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _exact_keys(value: object, expected: frozenset[str], field: str) -> dict:
    if type(value) is not dict:
        raise TypeError(f"{field} must be an exact dict")
    if frozenset(value) != expected:
        raise ValueError(f"{field} contains unknown or missing keys")
    return value


class ApplicationAuthorityV3Failure(ValueError):
    """Typed fail-closed result for the Parent-v3 application boundary."""

    def __init__(self, reason_id: str, detail: str) -> None:
        if reason_id not in _FAILURE_REASON_IDS:
            raise ValueError("application-authority-v3 failure reason is not frozen")
        self.reason_id = reason_id
        self.detail = _text(detail, "application-authority-v3 failure detail")
        super().__init__(f"{reason_id}: {detail}")


@dataclass(frozen=True)
class ParentV3CalibrationControlReplayRefV1:
    replay_ref_schema_version: str
    parent_freeze_v3_sha: str
    current_application_registry_sha: str
    parent_v1_ordinal: int
    authority_tag: str
    control_case_id: str
    control_id: str
    application_authority_v2: object
    application_authority_v2_sha: str
    scenario_authority_v2: object
    scenario_authority_v2_sha: str
    response_contract_v2: object
    response_contract_v2_sha: str
    replay_ref_sha: str

    def __post_init__(self) -> None:
        if self.replay_ref_schema_version != (
            PARENT_V3_CALIBRATION_CONTROL_REPLAY_REF_V1_SCHEMA_VERSION
        ):
            raise ValueError("Parent-v3 calibration replay-ref schema drifted")
        _sha(self.parent_freeze_v3_sha, "parent_freeze_v3_sha")
        _sha(
            self.current_application_registry_sha,
            "current_application_registry_sha",
        )
        if type(self.parent_v1_ordinal) is not int or self.parent_v1_ordinal < 0:
            raise ValueError("parent_v1_ordinal must be a non-negative exact int")
        if self.authority_tag != "INHERITED_CURRENT_V2":
            raise ValueError("calibration replay ref is not inherited current V2")
        expected = tuple(
            item for item in _CALIBRATION_CONTROLS if item[0] == self.parent_v1_ordinal
        )
        if len(expected) != 1 or expected[0][1:] != (
            self.control_case_id,
            self.control_id,
        ):
            raise ValueError("calibration replay-ref ordinal/case/control drifted")
        for field in (
            "application_authority_v2_sha",
            "scenario_authority_v2_sha",
            "response_contract_v2_sha",
            "replay_ref_sha",
        ):
            _sha(getattr(self, field), field)


@dataclass(frozen=True)
class WindowThresholdCalibrationV3:
    calibration_v3_schema_version: str
    parent_freeze_v3_sha: str
    current_application_registry_sha: str
    current_application_registry_v3: dict[str, object]
    calibration_control_replay_refs: tuple[ParentV3CalibrationControlReplayRefV1, ...]
    calibration_outcome: WindowCalibrationOutcome
    calibration_v3_sha: str

    def __post_init__(self) -> None:
        if (
            self.calibration_v3_schema_version
            != WINDOW_THRESHOLD_CALIBRATION_V3_SCHEMA_VERSION
        ):
            raise ValueError("window-threshold calibration-v3 schema drifted")
        _sha(self.parent_freeze_v3_sha, "parent_freeze_v3_sha")
        _sha(
            self.current_application_registry_sha,
            "current_application_registry_sha",
        )
        if type(self.current_application_registry_v3) is not dict:
            raise TypeError("current_application_registry_v3 must be an exact dict")
        if (
            type(self.calibration_control_replay_refs) is not tuple
            or len(self.calibration_control_replay_refs) != 3
            or not all(
                type(item) is ParentV3CalibrationControlReplayRefV1
                for item in self.calibration_control_replay_refs
            )
        ):
            raise TypeError("calibration replay refs must be the exact three-ref tuple")
        if type(self.calibration_outcome) is not WindowCalibrationOutcome:
            raise TypeError("calibration_outcome has the wrong exact type")
        _sha(self.calibration_v3_sha, "calibration_v3_sha")


@dataclass(frozen=True)
class CalibrationApplicationPermitV3:
    permit_schema_version: str
    parent_freeze_v3_sha: str
    calibration: WindowThresholdCalibrationV3
    current_application_authority: CurrentApplicationAuthorityV3
    current_scenario_authority: CurrentScenarioAuthorityV3
    current_scenario_response_contract: CurrentScenarioResponseContractV3
    selected_fejer_order: int
    permit_scope_id: str
    permit_sha: str

    def __post_init__(self) -> None:
        if (
            self.permit_schema_version
            != CALIBRATION_APPLICATION_PERMIT_V3_SCHEMA_VERSION
        ):
            raise ValueError("calibration application-permit-v3 schema drifted")
        _sha(self.parent_freeze_v3_sha, "parent_freeze_v3_sha")
        if type(self.calibration) is not WindowThresholdCalibrationV3:
            raise TypeError("permit calibration has the wrong exact type")
        if (
            type(self.current_application_authority)
            is not CurrentApplicationAuthorityV3
        ):
            raise TypeError("permit application has the wrong exact type")
        if type(self.current_scenario_authority) is not CurrentScenarioAuthorityV3:
            raise TypeError("permit scenario has the wrong exact type")
        if (
            type(self.current_scenario_response_contract)
            is not CurrentScenarioResponseContractV3
        ):
            raise TypeError("permit response contract has the wrong exact type")
        if type(self.selected_fejer_order) is not int or self.selected_fejer_order <= 0:
            raise ValueError("selected_fejer_order must be a positive exact int")
        if self.permit_scope_id != CALIBRATION_APPLICATION_PERMIT_V3_SCOPE_ID:
            raise ValueError("calibration application-permit-v3 scope drifted")
        _sha(self.permit_sha, "permit_sha")


def _v2_nested_wires(
    application: object,
    application_payload_builder: Callable[[object], dict[str, object]],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    payload = application_payload_builder(application)
    if type(payload) is not dict:
        raise TypeError("current application-authority-v2 payload must be a dict")
    application_wire = payload
    scenarios = application_wire.get("scenario_authorities")
    if type(scenarios) is not list or len(scenarios) != 1:
        raise ValueError("calibration application must expose exactly one scenario")
    scenario_wire = scenarios[0]
    if type(scenario_wire) is not dict:
        raise TypeError("scenario-authority-v2 payload must be an exact dict")
    response_wire = scenario_wire.get("response_contract")
    if type(response_wire) is not dict:
        raise TypeError("response-contract-v2 payload must be an exact dict")
    application_full = {
        **copy.deepcopy(application_wire),
        "application_authority_sha": application.application_authority_sha,
    }
    return (
        application_full,
        copy.deepcopy(scenario_wire),
        copy.deepcopy(response_wire),
    )


def _v2_repeated_wires(
    replay_ref: ParentV3CalibrationControlReplayRefV1,
    application_payload_builder: Callable[[object], dict[str, object]],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Serialize all three repeated bodies through the V2 canonical owner."""

    application = replay_ref.application_authority_v2
    application_wire, nested_scenario_wire, nested_response_wire = _v2_nested_wires(
        application, application_payload_builder
    )
    nested_scenario = application.scenario_authorities[0]
    nested_response = nested_scenario.response_contract
    repeated_scenario = replay_ref.scenario_authority_v2
    repeated_response = replay_ref.response_contract_v2
    if type(repeated_scenario) is not type(nested_scenario):
        raise TypeError("repeated scenario-authority-v2 has the wrong exact type")
    if type(repeated_response) is not type(nested_response):
        raise TypeError("repeated response-contract-v2 has the wrong exact type")

    scenario_application = replace(
        application,
        scenario_authorities=(repeated_scenario,),
    )
    _, repeated_scenario_wire, _ = _v2_nested_wires(
        scenario_application,
        application_payload_builder,
    )
    scenario_with_repeated_response = replace(
        repeated_scenario,
        response_contract=repeated_response,
    )
    response_application = replace(
        application,
        scenario_authorities=(scenario_with_repeated_response,),
    )
    _, scenario_with_response_wire, repeated_response_wire = _v2_nested_wires(
        response_application,
        application_payload_builder,
    )
    if (
        repeated_scenario_wire != nested_scenario_wire
        or scenario_with_response_wire != nested_scenario_wire
        or repeated_response_wire != nested_response_wire
    ):
        raise ValueError(
            "repeated V2 scenario/response wire differs from application nesting"
        )
    return application_wire, repeated_scenario_wire, repeated_response_wire


def _parent_v3_calibration_control_replay_ref_v1_payload_impl(
    replay_ref: ParentV3CalibrationControlReplayRefV1,
    *,
    application_payload_builder: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    _exact_record(
        replay_ref,
        ParentV3CalibrationControlReplayRefV1,
        "Parent-v3 calibration replay ref",
    )
    replay_ref.__post_init__()
    application_wire, scenario_wire, response_wire = _v2_repeated_wires(
        replay_ref,
        application_payload_builder,
    )
    return {
        "replay_ref_schema_version": replay_ref.replay_ref_schema_version,
        "parent_freeze_v3_sha": replay_ref.parent_freeze_v3_sha,
        "current_application_registry_sha": (
            replay_ref.current_application_registry_sha
        ),
        "parent_v1_ordinal": replay_ref.parent_v1_ordinal,
        "authority_tag": replay_ref.authority_tag,
        "control_case_id": replay_ref.control_case_id,
        "control_id": replay_ref.control_id,
        "application_authority_v2": application_wire,
        "application_authority_v2_sha": replay_ref.application_authority_v2_sha,
        "scenario_authority_v2": scenario_wire,
        "scenario_authority_v2_sha": replay_ref.scenario_authority_v2_sha,
        "response_contract_v2": response_wire,
        "response_contract_v2_sha": replay_ref.response_contract_v2_sha,
    }


def parent_v3_calibration_control_replay_ref_v1_payload(
    replay_ref: ParentV3CalibrationControlReplayRefV1,
) -> dict[str, object]:
    return _parent_v3_calibration_control_replay_ref_v1_payload_impl(
        replay_ref,
        application_payload_builder=current_application_authority_v2_payload,
    )


def _window_threshold_calibration_v3_payload_impl(
    calibration: WindowThresholdCalibrationV3,
    *,
    replay_ref_payload_builder: Callable[[object], dict[str, object]],
    outcome_payload_builder: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    _exact_record(
        calibration,
        WindowThresholdCalibrationV3,
        "window-threshold calibration v3",
    )
    calibration.__post_init__()
    return {
        "calibration_v3_schema_version": calibration.calibration_v3_schema_version,
        "parent_freeze_v3_sha": calibration.parent_freeze_v3_sha,
        "current_application_registry_sha": (
            calibration.current_application_registry_sha
        ),
        "current_application_registry_v3": copy.deepcopy(
            calibration.current_application_registry_v3
        ),
        "calibration_control_replay_refs": [
            {
                **replay_ref_payload_builder(item),
                "replay_ref_sha": item.replay_ref_sha,
            }
            for item in calibration.calibration_control_replay_refs
        ],
        "calibration_outcome": {
            **outcome_payload_builder(calibration.calibration_outcome),
            "outcome_sha": calibration.calibration_outcome.outcome_sha,
        },
    }


def window_threshold_calibration_v3_payload(
    calibration: WindowThresholdCalibrationV3,
) -> dict[str, object]:
    return _window_threshold_calibration_v3_payload_impl(
        calibration,
        replay_ref_payload_builder=parent_v3_calibration_control_replay_ref_v1_payload,
        outcome_payload_builder=window_calibration_outcome_payload,
    )


def _calibration_application_permit_v3_payload_impl(
    permit: CalibrationApplicationPermitV3,
    *,
    calibration_payload_builder: Callable[[object], dict[str, object]],
    application_payload_builder: Callable[[object], dict[str, object]],
    scenario_payload_builder: Callable[[object], dict[str, object]],
    response_payload_builder: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    _exact_record(
        permit,
        CalibrationApplicationPermitV3,
        "calibration application permit v3",
    )
    permit.__post_init__()
    return {
        "permit_schema_version": permit.permit_schema_version,
        "parent_freeze_v3_sha": permit.parent_freeze_v3_sha,
        "calibration": {
            **calibration_payload_builder(permit.calibration),
            "calibration_v3_sha": permit.calibration.calibration_v3_sha,
        },
        "current_application_authority": {
            **application_payload_builder(permit.current_application_authority),
            "application_authority_sha": (
                permit.current_application_authority.application_authority_sha
            ),
        },
        "current_scenario_authority": {
            **scenario_payload_builder(permit.current_scenario_authority),
            "scenario_authority_sha": (
                permit.current_scenario_authority.scenario_authority_sha
            ),
        },
        "current_scenario_response_contract": {
            **response_payload_builder(permit.current_scenario_response_contract),
            "response_contract_sha": (
                permit.current_scenario_response_contract.response_contract_sha
            ),
        },
        "selected_fejer_order": permit.selected_fejer_order,
        "permit_scope_id": permit.permit_scope_id,
    }


def calibration_application_permit_v3_payload(
    permit: CalibrationApplicationPermitV3,
) -> dict[str, object]:
    return _calibration_application_permit_v3_payload_impl(
        permit,
        calibration_payload_builder=window_threshold_calibration_v3_payload,
        application_payload_builder=current_application_authority_v3_payload,
        scenario_payload_builder=current_scenario_authority_v3_payload,
        response_payload_builder=current_scenario_response_contract_v3_payload,
    )


class VerifiedWindowThresholdCalibrationV3:
    """Opaque live Parent-v3 Task-11 calibration capability."""

    __slots__ = (
        "__calibration",
        "__token",
        "__seal",
        "__resolver",
        "__weakref__",
    )

    def __init__(
        self,
        token: object,
        calibration: WindowThresholdCalibrationV3,
        seal: str,
        resolver: Callable[[object], WindowThresholdCalibrationV3],
        *,
        _issuance_token: object = _ISSUANCE_TOKEN,
    ) -> None:
        if token is not _issuance_token:
            raise TypeError(
                "VerifiedWindowThresholdCalibrationV3 is module-issued only"
            )
        object.__setattr__(
            self,
            "_VerifiedWindowThresholdCalibrationV3__calibration",
            copy.deepcopy(calibration),
        )
        object.__setattr__(
            self,
            "_VerifiedWindowThresholdCalibrationV3__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedWindowThresholdCalibrationV3__seal",
            seal,
        )
        object.__setattr__(
            self,
            "_VerifiedWindowThresholdCalibrationV3__resolver",
            resolver,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedWindowThresholdCalibrationV3 is immutable")

    @property
    def calibration(self) -> WindowThresholdCalibrationV3:
        resolver = object.__getattribute__(
            self,
            "_VerifiedWindowThresholdCalibrationV3__resolver",
        )
        return resolver(self)


class VerifiedCalibrationApplicationPermitV3:
    """Opaque live Parent-v3 application/scenario permit capability."""

    __slots__ = (
        "__permit",
        "__token",
        "__seal",
        "__resolver",
        "__weakref__",
    )

    def __init__(
        self,
        token: object,
        permit: CalibrationApplicationPermitV3,
        seal: str,
        resolver: Callable[[object], CalibrationApplicationPermitV3],
        *,
        _issuance_token: object = _ISSUANCE_TOKEN,
    ) -> None:
        if token is not _issuance_token:
            raise TypeError(
                "VerifiedCalibrationApplicationPermitV3 is module-issued only"
            )
        object.__setattr__(
            self,
            "_VerifiedCalibrationApplicationPermitV3__permit",
            copy.deepcopy(permit),
        )
        object.__setattr__(
            self,
            "_VerifiedCalibrationApplicationPermitV3__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedCalibrationApplicationPermitV3__seal",
            seal,
        )
        object.__setattr__(
            self,
            "_VerifiedCalibrationApplicationPermitV3__resolver",
            resolver,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedCalibrationApplicationPermitV3 is immutable")

    @property
    def permit(self) -> CalibrationApplicationPermitV3:
        resolver = object.__getattribute__(
            self,
            "_VerifiedCalibrationApplicationPermitV3__resolver",
        )
        return resolver(self)


@dataclass(frozen=True)
class _WindowAuthorityV3:
    calibration: WindowThresholdCalibrationV3
    parent: object
    fingerprint: str


@dataclass(frozen=True)
class _PermitAuthorityV3:
    permit: CalibrationApplicationPermitV3
    parent: object
    calibration: VerifiedWindowThresholdCalibrationV3
    fingerprint: str


@dataclass(frozen=True)
class _ApplicationAuthorityV3Graph:
    calibrate: Callable[[object], VerifiedWindowThresholdCalibrationV3]
    verify_calibration: Callable[[object, object], VerifiedWindowThresholdCalibrationV3]
    issue_permit: Callable[..., VerifiedCalibrationApplicationPermitV3]
    verify_permit: Callable[[object, object], VerifiedCalibrationApplicationPermitV3]


def _make_application_authority_v3_graph(
    issuance_token: object,
) -> _ApplicationAuthorityV3Graph:
    """Close one authority graph over its exact dependency implementations."""

    if issuance_token is not _ISSUANCE_TOKEN:
        raise TypeError("application-authority-v3 graph token mismatch")

    parent_type = VerifiedParentFreezeV3
    parent_reverifier = require_current_parent_v3
    registry_payload_builder = current_application_registry_v3_payload
    v2_application_payload_builder = current_application_authority_v2_payload
    historical_parent_type = VerifiedParentFreeze
    historical_parent_issuer = issue_v3m0_parent_freeze
    historical_parent_reverifier = _reverify_verified_parent_freeze
    task8_replayer = _replay_current_task8_control_roots
    task11_runner = _run_task11_window_calibration_from_task8_replay
    outcome_type = WindowCalibrationOutcome
    outcome_payload_builder = window_calibration_outcome_payload
    v3_application_type = CurrentApplicationAuthorityV3
    v3_scenario_type = CurrentScenarioAuthorityV3
    v3_response_type = CurrentScenarioResponseContractV3
    v3_application_verifier = verify_current_application_authority_v3
    v3_application_payload_builder = current_application_authority_v3_payload
    v3_scenario_payload_builder = current_scenario_authority_v3_payload
    v3_response_payload_builder = current_scenario_response_contract_v3_payload
    replay_ref_type = ParentV3CalibrationControlReplayRefV1
    calibration_wire_type = WindowThresholdCalibrationV3
    permit_wire_type = CalibrationApplicationPermitV3
    window_wrapper_type = VerifiedWindowThresholdCalibrationV3
    permit_wrapper_type = VerifiedCalibrationApplicationPermitV3
    window_authority_type = _WindowAuthorityV3
    permit_authority_type = _PermitAuthorityV3
    sha_builder = canonical_sha
    expected_cases = tuple(APPLICATION_CONTROL_CASE_IDS)
    text_validator = _text
    sha_validator = _sha
    exact_record = _exact_record
    exact_keys = _exact_keys
    clone = copy.deepcopy
    type_fn = type
    id_fn = id
    weak_reference = weakref.ref
    object_getattribute = object.__getattribute__
    lock_builder = threading.RLock
    window_live: dict[int, object] = {}
    permit_live: dict[int, object] = {}
    window_lock = lock_builder()
    permit_lock = lock_builder()

    if len(expected_cases) != 20 or len(set(expected_cases)) != 20:
        raise RuntimeError("Parent-v3 control-case order is not the frozen 20-tuple")

    def replay_ref_payload(replay_ref):
        return _parent_v3_calibration_control_replay_ref_v1_payload_impl(
            replay_ref,
            application_payload_builder=v2_application_payload_builder,
        )

    def calibration_payload(calibration):
        return _window_threshold_calibration_v3_payload_impl(
            calibration,
            replay_ref_payload_builder=replay_ref_payload,
            outcome_payload_builder=outcome_payload_builder,
        )

    def permit_payload(permit):
        return _calibration_application_permit_v3_payload_impl(
            permit,
            calibration_payload_builder=calibration_payload,
            application_payload_builder=v3_application_payload_builder,
            scenario_payload_builder=v3_scenario_payload_builder,
            response_payload_builder=v3_response_payload_builder,
        )

    def calibration_seal(calibration):
        return sha_builder(
            {
                "authority_kind": "v3m0-window-threshold-calibration-live-v3",
                "calibration": {
                    **calibration_payload(calibration),
                    "calibration_v3_sha": calibration.calibration_v3_sha,
                },
            }
        )

    def permit_seal(permit):
        return sha_builder(
            {
                "authority_kind": "v3m0-calibration-application-permit-live-v3",
                "permit": {
                    **permit_payload(permit),
                    "permit_sha": permit.permit_sha,
                },
            }
        )

    def require_parent(parent):
        try:
            if type_fn(parent) is not parent_type:
                raise TypeError("application authority requires exact Parent-v3")
            manifest = parent_reverifier(parent)
            sha_validator(manifest.parent_freeze_v3_sha, "parent_freeze_v3_sha")
            sha_validator(
                manifest.current_application_registry_sha,
                "current_application_registry_sha",
            )
            return manifest
        except ApplicationAuthorityV3Failure:
            raise
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ApplicationAuthorityV3Failure(
                "PARENT_V3_UNAVAILABLE",
                str(exc),
            ) from exc

    def verify_registry(registry, expected_root):
        root = sha_validator(expected_root, "current_application_registry_sha")
        body = exact_keys(
            registry,
            frozenset(("current_application_registry_schema_version", "entries")),
            "current application registry v3",
        )
        if body["current_application_registry_schema_version"] != (
            _CURRENT_APPLICATION_REGISTRY_V3_SCHEMA_VERSION
        ):
            raise ValueError("current application registry-v3 schema drifted")
        entries = body["entries"]
        if type(entries) is not list or len(entries) != len(expected_cases):
            raise ValueError("current application registry must contain 20 entries")
        seen_applications: set[str] = set()
        for ordinal, (entry, case_id) in enumerate(zip(entries, expected_cases)):
            entry_body = exact_keys(
                entry,
                frozenset(
                    ("parent_v1_ordinal", "authority_tag", "application_authority")
                ),
                f"current application registry entry[{ordinal}]",
            )
            expected_tag = (
                "REFROZEN_CURRENT_V3"
                if case_id == "C19_FULL_POSITIVE_OBSERVER_COLLAPSE"
                else "INHERITED_CURRENT_V2"
            )
            application = entry_body["application_authority"]
            if type(application) is not dict:
                raise TypeError("registry application body must be an exact dict")
            application_id = application.get("application_instance_id")
            if (
                type(entry_body["parent_v1_ordinal"]) is not int
                or entry_body["parent_v1_ordinal"] != ordinal
                or entry_body["authority_tag"] != expected_tag
                or application.get("control_case_id") != case_id
                or type(application_id) is not str
                or not application_id
                or application_id in seen_applications
            ):
                raise ValueError("current application registry order/tag/body drifted")
            seen_applications.add(application_id)
        if sha_builder(body) != root:
            raise ValueError("current application registry SHA differs from Parent-v3")
        return clone(body)

    def verify_outcome(outcome):
        exact_record(outcome, outcome_type, "window calibration outcome")
        outcome.__post_init__()
        if outcome.outcome_sha != sha_builder(outcome_payload_builder(outcome)):
            raise ValueError("window calibration outcome SHA drifted")
        return clone(outcome)

    def verify_replay_ref(replay_ref):
        exact_record(
            replay_ref,
            replay_ref_type,
            "Parent-v3 calibration replay ref",
        )
        replay_ref.__post_init__()
        application = replay_ref.application_authority_v2
        scenarios = getattr(application, "scenario_authorities", None)
        if type(scenarios) is not tuple or len(scenarios) != 1:
            raise ValueError("calibration V2 application must expose one scenario")
        scenario = scenarios[0]
        response = getattr(scenario, "response_contract", None)
        if type(replay_ref.scenario_authority_v2) is not type(scenario):
            raise TypeError("repeated scenario-authority-v2 has the wrong exact type")
        if type(replay_ref.response_contract_v2) is not type(response):
            raise TypeError("repeated response-contract-v2 has the wrong exact type")
        if (
            scenario != replay_ref.scenario_authority_v2
            or response != replay_ref.response_contract_v2
            or getattr(application, "control_case_id", None)
            != replay_ref.control_case_id
            or getattr(scenario, "control_case_id", None) != replay_ref.control_case_id
            or getattr(scenario, "application_instance_id", None)
            != getattr(application, "application_instance_id", None)
            or getattr(response, "scenario_id", None)
            != getattr(scenario, "scenario_id", None)
            or getattr(application, "application_authority_sha", None)
            != replay_ref.application_authority_v2_sha
            or getattr(scenario, "scenario_authority_sha", None)
            != replay_ref.scenario_authority_v2_sha
            or getattr(response, "response_contract_sha", None)
            != replay_ref.response_contract_v2_sha
        ):
            raise ValueError("calibration replay ref contains a nested V2 splice")
        if replay_ref.replay_ref_sha != sha_builder(replay_ref_payload(replay_ref)):
            raise ValueError("calibration replay-ref SHA drifted")
        return clone(replay_ref)

    def verify_calibration_wire(calibration):
        exact_record(
            calibration,
            calibration_wire_type,
            "window-threshold calibration v3",
        )
        calibration.__post_init__()
        verify_registry(
            calibration.current_application_registry_v3,
            calibration.current_application_registry_sha,
        )
        observed_refs = tuple(
            (
                item.parent_v1_ordinal,
                item.control_case_id,
                item.control_id,
            )
            for item in calibration.calibration_control_replay_refs
        )
        if observed_refs != _CALIBRATION_CONTROLS:
            raise ValueError("calibration replay refs are not exact ordered C01-C03")
        for replay_ref in calibration.calibration_control_replay_refs:
            verify_replay_ref(replay_ref)
            if (
                replay_ref.parent_freeze_v3_sha != calibration.parent_freeze_v3_sha
                or replay_ref.current_application_registry_sha
                != calibration.current_application_registry_sha
            ):
                raise ValueError("calibration replay ref contains a cross-root splice")
        verify_outcome(calibration.calibration_outcome)
        if calibration.calibration_v3_sha != sha_builder(
            calibration_payload(calibration)
        ):
            raise ValueError("window-threshold calibration-v3 SHA drifted")
        return clone(calibration)

    def build_replay_refs(candidate, parent_manifest, registry):
        inherited = getattr(
            candidate,
            "inherited_current_application_authorities_v2",
            None,
        )
        if type(inherited) is not tuple:
            raise TypeError("Parent-v3 inherited V2 applications are not a tuple")
        by_case = {item.control_case_id: item for item in inherited}
        if len(by_case) != len(inherited):
            raise ValueError("Parent-v3 inherited V2 applications repeat a case")
        entries = registry["entries"]
        refs: list[ParentV3CalibrationControlReplayRefV1] = []
        for ordinal, case_id, control_id in _CALIBRATION_CONTROLS:
            application = by_case.get(case_id)
            if application is None:
                raise ValueError(
                    f"Parent-v3 is missing inherited calibration {case_id}"
                )
            scenarios = getattr(application, "scenario_authorities", None)
            if type(scenarios) is not tuple or len(scenarios) != 1:
                raise ValueError(f"{case_id} must expose exactly one scenario")
            scenario = scenarios[0]
            response = getattr(scenario, "response_contract", None)
            application_wire, scenario_wire, response_wire = _v2_nested_wires(
                application,
                v2_application_payload_builder,
            )
            registry_entry = entries[ordinal]
            if (
                registry_entry["authority_tag"] != "INHERITED_CURRENT_V2"
                or registry_entry["application_authority"] != application_wire
                or scenario_wire.get("scenario_authority_sha")
                != scenario.scenario_authority_sha
                or response_wire.get("response_contract_sha")
                != response.response_contract_sha
            ):
                raise ValueError(f"{case_id} replay body differs from current registry")
            provisional = replay_ref_type(
                replay_ref_schema_version=(
                    PARENT_V3_CALIBRATION_CONTROL_REPLAY_REF_V1_SCHEMA_VERSION
                ),
                parent_freeze_v3_sha=parent_manifest.parent_freeze_v3_sha,
                current_application_registry_sha=(
                    parent_manifest.current_application_registry_sha
                ),
                parent_v1_ordinal=ordinal,
                authority_tag="INHERITED_CURRENT_V2",
                control_case_id=case_id,
                control_id=control_id,
                application_authority_v2=clone(application),
                application_authority_v2_sha=application.application_authority_sha,
                scenario_authority_v2=clone(scenario),
                scenario_authority_v2_sha=scenario.scenario_authority_sha,
                response_contract_v2=clone(response),
                response_contract_v2_sha=response.response_contract_sha,
                replay_ref_sha="0" * 64,
            )
            replay_ref = replace(
                provisional,
                replay_ref_sha=sha_builder(replay_ref_payload(provisional)),
            )
            refs.append(verify_replay_ref(replay_ref))
        return tuple(refs)

    def expected_calibration(parent_manifest):
        try:
            candidate = parent_manifest.reviewed_candidate_v3
            registry = verify_registry(
                registry_payload_builder(candidate),
                parent_manifest.current_application_registry_sha,
            )
            refs = build_replay_refs(candidate, parent_manifest, registry)
            historical_parent = historical_parent_issuer()
            if type_fn(historical_parent) is not historical_parent_type:
                raise TypeError("historical Parent issuer returned the wrong type")
            historical_manifest = historical_parent_reverifier(historical_parent)
            if historical_manifest != candidate.historical_parent_v1:
                raise ValueError("historical Parent-v1 differs from Parent-v3 witness")
            scenarios = tuple(item.scenario_authority_v2 for item in refs)
            task8_replay = task8_replayer(historical_parent, scenarios)
            outcome = verify_outcome(task11_runner(historical_parent, task8_replay))
            provisional = calibration_wire_type(
                calibration_v3_schema_version=(
                    WINDOW_THRESHOLD_CALIBRATION_V3_SCHEMA_VERSION
                ),
                parent_freeze_v3_sha=parent_manifest.parent_freeze_v3_sha,
                current_application_registry_sha=(
                    parent_manifest.current_application_registry_sha
                ),
                current_application_registry_v3=registry,
                calibration_control_replay_refs=refs,
                calibration_outcome=outcome,
                calibration_v3_sha="0" * 64,
            )
            calibration = replace(
                provisional,
                calibration_v3_sha=sha_builder(calibration_payload(provisional)),
            )
            return verify_calibration_wire(calibration)
        except ApplicationAuthorityV3Failure:
            raise
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ApplicationAuthorityV3Failure(
                "CALIBRATION_REPLAY_FAILED",
                str(exc),
            ) from exc

    def issue_calibration(parent):
        parent_manifest = require_parent(parent)
        snapshot = expected_calibration(parent_manifest)
        fingerprint = calibration_seal(snapshot)

        def resolver(wrapper):
            return require_calibration(wrapper)

        wrapper = window_wrapper_type(
            issuance_token,
            snapshot,
            fingerprint,
            resolver,
        )
        identity = id_fn(wrapper)
        authority = window_authority_type(clone(snapshot), parent, fingerprint)

        def remove_stale(reference, wrapper_id=identity):
            with window_lock:
                current = window_live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del window_live[wrapper_id]

        reference = weak_reference(wrapper, remove_stale)
        with window_lock:
            current = window_live.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("live calibration-v3 identity collision")
            window_live[identity] = (reference, authority)
        return wrapper

    def calibration_authority(calibration):
        if type_fn(calibration) is not window_wrapper_type:
            raise TypeError(
                "calibration-v3 consumer rejects raw, old, and subclass values"
            )
        with window_lock:
            current = window_live.get(id_fn(calibration))
            if current is None or current[0]() is not calibration:
                raise ValueError(
                    "calibration-v3 identity is absent from its live registry"
                )
            return current[1]

    def require_calibration(calibration):
        authority = calibration_authority(calibration)
        try:
            token = object_getattribute(
                calibration,
                "_VerifiedWindowThresholdCalibrationV3__token",
            )
            raw = object_getattribute(
                calibration,
                "_VerifiedWindowThresholdCalibrationV3__calibration",
            )
            seal = object_getattribute(
                calibration,
                "_VerifiedWindowThresholdCalibrationV3__seal",
            )
        except AttributeError as exc:
            raise ValueError("calibration-v3 immutable record is incomplete") from exc
        if token is not issuance_token:
            raise ValueError("calibration-v3 immutable token drifted")
        try:
            snapshot = verify_calibration_wire(raw)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("calibration-v3 immutable body/seal drifted") from exc
        parent_manifest = require_parent(authority.parent)
        expected = expected_calibration(parent_manifest)
        expected_seal = calibration_seal(expected)
        if (
            snapshot != authority.calibration
            or snapshot != expected
            or seal != authority.fingerprint
            or seal != expected_seal
        ):
            raise ValueError("calibration-v3 immutable seal or replay root drifted")
        return clone(expected)

    def verify_calibration(parent, calibration):
        authority = calibration_authority(calibration)
        if authority.parent is not parent:
            raise ApplicationAuthorityV3Failure(
                "CROSS_PARENT_ROOT",
                "calibration and Parent identities differ",
            )
        require_calibration(calibration)
        return calibration

    def current_v3_application(parent_manifest, control_case_id, application_id):
        case_id = text_validator(control_case_id, "control_case_id")
        instance_id = text_validator(application_id, "application_instance_id")
        candidate = parent_manifest.reviewed_candidate_v3
        applications = getattr(
            candidate,
            "refrozen_current_application_authorities_v3",
            None,
        )
        if type(applications) is not tuple:
            raise ApplicationAuthorityV3Failure(
                "CURRENT_APPLICATION_MISSING",
                "Parent-v3 refrozen application tuple is unavailable",
            )
        matches = tuple(
            item
            for item in applications
            if item.control_case_id == case_id
            and item.application_instance_id == instance_id
        )
        if len(matches) != 1:
            raise ApplicationAuthorityV3Failure(
                "CURRENT_APPLICATION_MISSING",
                "application IDs do not resolve to one current V3 authority",
            )
        application = matches[0]
        if type_fn(application) is not v3_application_type:
            raise TypeError("current Parent-v3 application has the wrong exact type")
        v3_application_verifier(application)
        registry = verify_registry(
            registry_payload_builder(candidate),
            parent_manifest.current_application_registry_sha,
        )
        entries = tuple(
            item
            for item in registry["entries"]
            if item["authority_tag"] == "REFROZEN_CURRENT_V3"
            and item["application_authority"].get("control_case_id") == case_id
            and item["application_authority"].get("application_instance_id")
            == instance_id
        )
        full_wire = {
            **v3_application_payload_builder(application),
            "application_authority_sha": application.application_authority_sha,
        }
        if len(entries) != 1 or entries[0]["application_authority"] != full_wire:
            raise ApplicationAuthorityV3Failure(
                "CURRENT_APPLICATION_MISSING",
                "current V3 application differs from the Parent registry",
            )
        return clone(application)

    def expected_permit(
        parent_manifest,
        calibration_body,
        control_case_id,
        application_instance_id,
        scenario_id,
    ):
        verified_calibration = verify_calibration_wire(calibration_body)
        if (
            verified_calibration.parent_freeze_v3_sha
            != parent_manifest.parent_freeze_v3_sha
            or verified_calibration.current_application_registry_sha
            != parent_manifest.current_application_registry_sha
        ):
            raise ApplicationAuthorityV3Failure(
                "CROSS_PARENT_ROOT",
                "calibration body differs from the current Parent-v3 root",
            )
        outcome = verified_calibration.calibration_outcome
        if not outcome.status.defined or outcome.selection is None:
            raise ApplicationAuthorityV3Failure(
                "WINDOW_UNRESOLVED",
                "Task-11 has no selected Fejer order under this Parent-v3",
            )
        application = current_v3_application(
            parent_manifest,
            control_case_id,
            application_instance_id,
        )
        scenario_identifier = text_validator(scenario_id, "scenario_id")
        scenarios = application.scenario_authorities
        matches = tuple(
            item
            for item in scenarios
            if item.scenario_id == scenario_identifier
            and item.control_case_id == application.control_case_id
            and item.application_instance_id == application.application_instance_id
        )
        if len(matches) != 1:
            raise ApplicationAuthorityV3Failure(
                "SCENARIO_MISSING",
                "scenario ID does not resolve inside the current V3 application",
            )
        scenario = matches[0]
        response = scenario.response_contract
        if (
            type_fn(scenario) is not v3_scenario_type
            or type_fn(response) is not v3_response_type
            or response.control_case_id != application.control_case_id
            or response.application_instance_id != application.application_instance_id
            or response.scenario_id != scenario.scenario_id
        ):
            raise ApplicationAuthorityV3Failure(
                "SCENARIO_MISSING",
                "current scenario/response body contains an ID splice",
            )
        selected_order = outcome.selection.selected_fejer_order
        provisional = permit_wire_type(
            permit_schema_version=CALIBRATION_APPLICATION_PERMIT_V3_SCHEMA_VERSION,
            parent_freeze_v3_sha=parent_manifest.parent_freeze_v3_sha,
            calibration=clone(verified_calibration),
            current_application_authority=clone(application),
            current_scenario_authority=clone(scenario),
            current_scenario_response_contract=clone(response),
            selected_fejer_order=selected_order,
            permit_scope_id=CALIBRATION_APPLICATION_PERMIT_V3_SCOPE_ID,
            permit_sha="0" * 64,
        )
        return replace(
            provisional,
            permit_sha=sha_builder(permit_payload(provisional)),
        )

    def verify_permit_wire(permit):
        exact_record(
            permit,
            permit_wire_type,
            "calibration application permit v3",
        )
        permit.__post_init__()
        calibration = verify_calibration_wire(permit.calibration)
        application = permit.current_application_authority
        v3_application_verifier(application)
        scenario = permit.current_scenario_authority
        response = permit.current_scenario_response_contract
        if (
            type_fn(scenario) is not v3_scenario_type
            or type_fn(response) is not v3_response_type
            or permit.parent_freeze_v3_sha != calibration.parent_freeze_v3_sha
            or scenario not in application.scenario_authorities
            or response != scenario.response_contract
            or permit.selected_fejer_order
            != calibration.calibration_outcome.selection.selected_fejer_order
        ):
            raise ValueError("calibration application permit contains a splice")
        if permit.permit_sha != sha_builder(permit_payload(permit)):
            raise ValueError("calibration application-permit-v3 SHA drifted")
        return clone(permit)

    def issue_permit(
        parent,
        calibration,
        control_case_id,
        application_instance_id,
        scenario_id,
    ):
        calibration_binding = calibration_authority(calibration)
        if calibration_binding.parent is not parent:
            raise ApplicationAuthorityV3Failure(
                "CROSS_PARENT_ROOT",
                "calibration and Parent identities differ",
            )
        parent_manifest = require_parent(parent)
        calibration_body = require_calibration(calibration)
        expected = expected_permit(
            parent_manifest,
            calibration_body,
            control_case_id,
            application_instance_id,
            scenario_id,
        )
        snapshot = verify_permit_wire(expected)
        fingerprint = permit_seal(snapshot)

        def resolver(wrapper):
            return require_permit(wrapper)

        wrapper = permit_wrapper_type(
            issuance_token,
            snapshot,
            fingerprint,
            resolver,
        )
        identity = id_fn(wrapper)
        authority = permit_authority_type(
            clone(snapshot),
            parent,
            calibration,
            fingerprint,
        )

        def remove_stale(reference, wrapper_id=identity):
            with permit_lock:
                current = permit_live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del permit_live[wrapper_id]

        reference = weak_reference(wrapper, remove_stale)
        with permit_lock:
            current = permit_live.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("live application-permit-v3 identity collision")
            permit_live[identity] = (reference, authority)
        return wrapper

    def permit_authority(permit):
        if type_fn(permit) is not permit_wrapper_type:
            raise TypeError("permit-v3 consumer rejects raw, old, and subclass values")
        with permit_lock:
            current = permit_live.get(id_fn(permit))
            if current is None or current[0]() is not permit:
                raise ValueError("permit-v3 identity is absent from its live registry")
            return current[1]

    def require_permit(permit):
        authority = permit_authority(permit)
        try:
            token = object_getattribute(
                permit,
                "_VerifiedCalibrationApplicationPermitV3__token",
            )
            raw = object_getattribute(
                permit,
                "_VerifiedCalibrationApplicationPermitV3__permit",
            )
            seal = object_getattribute(
                permit,
                "_VerifiedCalibrationApplicationPermitV3__seal",
            )
        except AttributeError as exc:
            raise ValueError("permit-v3 immutable record is incomplete") from exc
        if token is not issuance_token:
            raise ValueError("permit-v3 immutable token drifted")
        try:
            snapshot = verify_permit_wire(raw)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("permit-v3 immutable body/seal drifted") from exc
        parent_manifest = require_parent(authority.parent)
        calibration_body = require_calibration(authority.calibration)
        expected = expected_permit(
            parent_manifest,
            calibration_body,
            authority.permit.current_application_authority.control_case_id,
            authority.permit.current_application_authority.application_instance_id,
            authority.permit.current_scenario_authority.scenario_id,
        )
        expected_seal = permit_seal(expected)
        if (
            snapshot != authority.permit
            or snapshot != expected
            or seal != authority.fingerprint
            or seal != expected_seal
        ):
            raise ValueError("permit-v3 immutable seal or replay root drifted")
        return clone(expected)

    def verify_permit(parent, permit):
        authority = permit_authority(permit)
        if authority.parent is not parent:
            raise ApplicationAuthorityV3Failure(
                "CROSS_PARENT_ROOT",
                "permit and Parent identities differ",
            )
        require_permit(permit)
        return permit

    return _ApplicationAuthorityV3Graph(
        calibrate=issue_calibration,
        verify_calibration=verify_calibration,
        issue_permit=issue_permit,
        verify_permit=verify_permit,
    )


def _make_public_application_authority_v3_api(graph):
    """Close public entry points over the production graph exactly once."""

    def calibrate_v3m0_window_thresholds_v3(parent):
        """Replay Task 11 under the exact live Parent-v3 mixed registry."""

        return graph.calibrate(parent)

    def verify_window_threshold_calibration_v3(parent, calibration):
        """Reverify an opaque Parent-v3 calibration by recursive replay."""

        return graph.verify_calibration(parent, calibration)

    def issue_calibration_application_permit_v3(
        parent,
        calibration,
        control_case_id,
        application_instance_id,
        scenario_id,
    ):
        """Issue a resolved-window permit for one exact current V3 scenario."""

        return graph.issue_permit(
            parent,
            calibration,
            control_case_id,
            application_instance_id,
            scenario_id,
        )

    def verify_calibration_application_permit_v3(parent, permit):
        """Reverify all Parent/calibration/application/scenario permit joins."""

        return graph.verify_permit(parent, permit)

    return (
        calibrate_v3m0_window_thresholds_v3,
        verify_window_threshold_calibration_v3,
        issue_calibration_application_permit_v3,
        verify_calibration_application_permit_v3,
    )


_PRODUCTION_GRAPH = _make_application_authority_v3_graph(_ISSUANCE_TOKEN)
(
    calibrate_v3m0_window_thresholds_v3,
    verify_window_threshold_calibration_v3,
    issue_calibration_application_permit_v3,
    verify_calibration_application_permit_v3,
) = _make_public_application_authority_v3_api(_PRODUCTION_GRAPH)


__all__ = (
    "ApplicationAuthorityV3Failure",
    "CALIBRATION_APPLICATION_PERMIT_V3_SCHEMA_VERSION",
    "CALIBRATION_APPLICATION_PERMIT_V3_SCOPE_ID",
    "CalibrationApplicationPermitV3",
    "PARENT_V3_CALIBRATION_CONTROL_REPLAY_REF_V1_SCHEMA_VERSION",
    "ParentV3CalibrationControlReplayRefV1",
    "VerifiedCalibrationApplicationPermitV3",
    "VerifiedWindowThresholdCalibrationV3",
    "WINDOW_THRESHOLD_CALIBRATION_V3_SCHEMA_VERSION",
    "WindowThresholdCalibrationV3",
    "calibrate_v3m0_window_thresholds_v3",
    "calibration_application_permit_v3_payload",
    "issue_calibration_application_permit_v3",
    "parent_v3_calibration_control_replay_ref_v1_payload",
    "verify_calibration_application_permit_v3",
    "verify_window_threshold_calibration_v3",
    "window_threshold_calibration_v3_payload",
)
