"""Current-Parent Task 11/12 authority boundary.

This module is intentionally fail-closed until a Task-11 registry/window
replay exists under the issued Parent-v2 root.  Neither public issuer accepts
thresholds, response templates, scenario authorities, or raw evidence from a
caller.
"""

from __future__ import annotations

import copy
import re
import threading
import weakref
from dataclasses import dataclass, fields as dataclass_fields

from .calibration_authority import (
    SelectedControlEvidenceRef,
    WindowThresholdSelection,
    window_threshold_selection_payload,
)
from .evidence import canonical_sha
from .parent_freeze import (
    ApplicationScenarioExecutionSpec,
    application_scenario_execution_spec_payload,
)
from .parent_v2_contracts import (
    CurrentApplicationAuthorityV2,
    CurrentScenarioAuthorityV2,
    CurrentScenarioResponseContractV2,
    current_application_authority_v2_payload,
    current_scenario_authority_v2_payload,
    current_scenario_response_contract_v2_payload,
)


WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION = (
    "v3m0.window-threshold-calibration.v2"
)
CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION = (
    "v3m0.calibration-application-permit.v2"
)
_APPLICATION_PERMIT_SCOPE_V2 = (
    "v3m0-current-synthetic-control-application-v2"
)
_CALIBRATION_REPLAY_CONTRACT_ID = (
    "replay-window-threshold-calibration-under-current-parent-v2"
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
    observed = frozenset(vars(value))
    if observed != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


@dataclass(frozen=True)
class WindowThresholdCalibrationV2:
    """Raw serialization wire; never a capability by itself."""

    calibration_schema_version: str
    authority_state: str
    parent_freeze_v2_sha: str
    current_control_registry_sha: str
    current_window_protocol_sha: str
    current_calibration_outcome_sha: str
    selection: WindowThresholdSelection
    replay_contract_id: str
    calibration_v2_sha: str

    def __post_init__(self) -> None:
        if (
            self.calibration_schema_version
            != WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION
        ):
            raise ValueError("Task-11-v2 calibration schema drifted")
        if self.authority_state != "CURRENT_PARENT_V2_BOUND_CALIBRATION":
            raise ValueError("Task-11-v2 calibration state drifted")
        for field in (
            "parent_freeze_v2_sha",
            "current_control_registry_sha",
            "current_window_protocol_sha",
            "current_calibration_outcome_sha",
            "calibration_v2_sha",
        ):
            _sha(getattr(self, field), field)
        if type(self.selection) is not WindowThresholdSelection:
            raise TypeError("selection must be an exact WindowThresholdSelection")
        if self.replay_contract_id != _CALIBRATION_REPLAY_CONTRACT_ID:
            raise ValueError("Task-11-v2 replay contract drifted")


def window_threshold_calibration_v2_payload(
    calibration: WindowThresholdCalibrationV2,
) -> dict[str, object]:
    _exact_record(
        calibration,
        WindowThresholdCalibrationV2,
        "Task-11-v2 calibration wire",
    )
    return {
        "calibration_schema_version": calibration.calibration_schema_version,
        "authority_state": calibration.authority_state,
        "parent_freeze_v2_sha": calibration.parent_freeze_v2_sha,
        "current_control_registry_sha": calibration.current_control_registry_sha,
        "current_window_protocol_sha": calibration.current_window_protocol_sha,
        "current_calibration_outcome_sha": (
            calibration.current_calibration_outcome_sha
        ),
        "selection": {
            **window_threshold_selection_payload(calibration.selection),
            "selection_sha": calibration.selection.selection_sha,
        },
        "replay_contract_id": calibration.replay_contract_id,
    }


def verify_window_threshold_calibration_v2_wire(
    calibration: WindowThresholdCalibrationV2,
) -> WindowThresholdCalibrationV2:
    """Validate a raw wire without hydrating it into a capability."""

    _exact_record(
        calibration,
        WindowThresholdCalibrationV2,
        "Task-11-v2 calibration wire",
    )
    calibration.__post_init__()
    selection = calibration.selection
    _exact_record(selection, WindowThresholdSelection, "threshold selection")
    selection.__post_init__()
    for index, reference in enumerate(selection.selected_evidence_refs):
        _exact_record(
            reference,
            SelectedControlEvidenceRef,
            f"selected evidence ref[{index}]",
        )
        reference.__post_init__()
    if selection.selection_sha != canonical_sha(
        window_threshold_selection_payload(selection)
    ):
        raise ValueError("selection SHA does not match its exact body")
    if calibration.calibration_v2_sha != canonical_sha(
        window_threshold_calibration_v2_payload(calibration)
    ):
        raise ValueError("Task-11-v2 calibration SHA does not match its body")
    return copy.deepcopy(calibration)


@dataclass(frozen=True)
class CalibrationApplicationPermitV2:
    """Raw current-Parent Task-12 permit; never a capability by itself."""

    permit_schema_version: str
    scope: str
    parent_freeze_v2_sha: str
    calibration: WindowThresholdCalibrationV2
    control_case_id: str
    application_authority: CurrentApplicationAuthorityV2
    scenario_authority_shas: tuple[str, ...]
    selected_fejer_order: int
    permit_sha: str

    def __post_init__(self) -> None:
        if (
            self.permit_schema_version
            != CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION
        ):
            raise ValueError("Task-12-v2 permit schema drifted")
        if self.scope != _APPLICATION_PERMIT_SCOPE_V2:
            raise ValueError("Task-12-v2 permit scope drifted")
        _sha(self.parent_freeze_v2_sha, "parent_freeze_v2_sha")
        if type(self.calibration) is not WindowThresholdCalibrationV2:
            raise TypeError("permit calibration has the wrong strict type")
        _text(self.control_case_id, "control_case_id")
        if type(self.application_authority) is not CurrentApplicationAuthorityV2:
            raise TypeError("permit application authority has the wrong strict type")
        if type(self.scenario_authority_shas) is not tuple:
            raise TypeError("scenario_authority_shas must be an exact tuple")
        for index, value in enumerate(self.scenario_authority_shas):
            _sha(value, f"scenario_authority_shas[{index}]")
        if len(self.scenario_authority_shas) != len(
            set(self.scenario_authority_shas)
        ):
            raise ValueError("scenario authority SHAs must be unique")
        if type(self.selected_fejer_order) is not int:
            raise TypeError("selected_fejer_order must be an exact integer")
        _sha(self.permit_sha, "permit_sha")


def calibration_application_permit_v2_payload(
    permit: CalibrationApplicationPermitV2,
) -> dict[str, object]:
    _exact_record(
        permit,
        CalibrationApplicationPermitV2,
        "Task-12-v2 permit wire",
    )
    return {
        "permit_schema_version": permit.permit_schema_version,
        "scope": permit.scope,
        "parent_freeze_v2_sha": permit.parent_freeze_v2_sha,
        "calibration": {
            **window_threshold_calibration_v2_payload(permit.calibration),
            "calibration_v2_sha": permit.calibration.calibration_v2_sha,
        },
        "control_case_id": permit.control_case_id,
        "application_authority": {
            **current_application_authority_v2_payload(
                permit.application_authority
            ),
            "application_authority_sha": (
                permit.application_authority.application_authority_sha
            ),
        },
        "scenario_authority_shas": list(permit.scenario_authority_shas),
        "selected_fejer_order": permit.selected_fejer_order,
    }


def _verify_current_application_authority(
    application: CurrentApplicationAuthorityV2,
) -> None:
    _exact_record(
        application,
        CurrentApplicationAuthorityV2,
        "current application authority",
    )
    application.__post_init__()
    for index, scenario in enumerate(application.scenario_authorities):
        _exact_record(
            scenario,
            CurrentScenarioAuthorityV2,
            f"current scenario authority[{index}]",
        )
        scenario.__post_init__()
        execution = scenario.scenario_execution_spec
        _exact_record(
            execution,
            ApplicationScenarioExecutionSpec,
            f"scenario execution spec[{index}]",
        )
        execution.__post_init__()
        if execution.scenario_sha != canonical_sha(
            application_scenario_execution_spec_payload(execution)
        ):
            raise ValueError("scenario execution SHA does not match its body")
        response = scenario.response_contract
        _exact_record(
            response,
            CurrentScenarioResponseContractV2,
            f"current response contract[{index}]",
        )
        response.__post_init__()
        if response.response_contract_sha != canonical_sha(
            current_scenario_response_contract_v2_payload(response)
        ):
            raise ValueError("current response-contract SHA drifted")
        if scenario.scenario_authority_sha != canonical_sha(
            current_scenario_authority_v2_payload(scenario)
        ):
            raise ValueError("current scenario-authority SHA drifted")
    if application.application_authority_sha != canonical_sha(
        current_application_authority_v2_payload(application)
    ):
        raise ValueError("current application-authority SHA drifted")


def verify_calibration_application_permit_v2_wire(
    permit: CalibrationApplicationPermitV2,
) -> CalibrationApplicationPermitV2:
    """Validate a raw permit without hydrating it into a capability."""

    _exact_record(
        permit,
        CalibrationApplicationPermitV2,
        "Task-12-v2 permit wire",
    )
    permit.__post_init__()
    verify_window_threshold_calibration_v2_wire(permit.calibration)
    _verify_current_application_authority(permit.application_authority)
    expected_scenario_shas = tuple(
        item.scenario_authority_sha
        for item in permit.application_authority.scenario_authorities
    )
    if (
        permit.parent_freeze_v2_sha
        != permit.calibration.parent_freeze_v2_sha
        or permit.control_case_id
        != permit.application_authority.control_case_id
        or permit.scenario_authority_shas != expected_scenario_shas
        or permit.selected_fejer_order
        != permit.calibration.selection.selected_fejer_order
    ):
        raise ValueError("Task-12-v2 permit contains a cross-authority splice")
    if permit.permit_sha != canonical_sha(
        calibration_application_permit_v2_payload(permit)
    ):
        raise ValueError("Task-12-v2 permit SHA does not match its body")
    return copy.deepcopy(permit)


class VerifiedCalibrationApplicationPermitV2:
    """Opaque live current-Parent Task-12 permit capability."""

    __slots__ = ("__permit", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        permit: CalibrationApplicationPermitV2,
        seal: str,
        *,
        _issuance_token=_ISSUANCE_TOKEN,
        _setattr=object.__setattr__,
    ) -> None:
        if token is not _issuance_token:
            raise TypeError(
                "VerifiedCalibrationApplicationPermitV2 is module-issued only"
            )
        _setattr(
            self,
            "_VerifiedCalibrationApplicationPermitV2__permit",
            copy.deepcopy(permit),
        )
        _setattr(
            self,
            "_VerifiedCalibrationApplicationPermitV2__token",
            token,
        )
        _setattr(self, "_VerifiedCalibrationApplicationPermitV2__seal", seal)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedCalibrationApplicationPermitV2 is immutable")

    @property
    def permit(self) -> CalibrationApplicationPermitV2:
        return require_calibration_application_permit_v2(self)

    @property
    def application_authority(self) -> CurrentApplicationAuthorityV2:
        return copy.deepcopy(self.permit.application_authority)

    @property
    def scenario_authorities(self) -> tuple[CurrentScenarioAuthorityV2, ...]:
        return copy.deepcopy(self.permit.application_authority.scenario_authorities)


class VerifiedWindowThresholdCalibrationV2:
    """Opaque live Task-11-v2 capability."""

    __slots__ = ("__calibration", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        calibration: WindowThresholdCalibrationV2,
        seal: str,
        *,
        _issuance_token=_ISSUANCE_TOKEN,
        _setattr=object.__setattr__,
    ) -> None:
        if token is not _issuance_token:
            raise TypeError(
                "VerifiedWindowThresholdCalibrationV2 is module-issued only"
            )
        _setattr(
            self,
            "_VerifiedWindowThresholdCalibrationV2__calibration",
            copy.deepcopy(calibration),
        )
        _setattr(
            self,
            "_VerifiedWindowThresholdCalibrationV2__token",
            token,
        )
        _setattr(self, "_VerifiedWindowThresholdCalibrationV2__seal", seal)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedWindowThresholdCalibrationV2 is immutable")

    @property
    def calibration(self) -> WindowThresholdCalibrationV2:
        return require_window_threshold_calibration_v2(self)

    @property
    def selection(self) -> WindowThresholdSelection:
        return copy.deepcopy(self.calibration.selection)


class ApplicationAuthorityV2UpstreamUnavailable(RuntimeError):
    """The current Parent/Task-11 replay chain is not yet issuable."""


def _require_exact_current_parent(parent):
    # Kept lazy so a DRAFT Parent-v2 construction failure cannot weaken or
    # replace this module's raw exact-type contracts during import.
    parent_type = type(parent)
    if (
        parent_type.__module__ != "rulespace_v3.parent_authority"
        or parent_type.__name__ != "VerifiedParentFreezeV2"
    ):
        raise TypeError(
            "current authority requires an exact live VerifiedParentFreezeV2"
        )
    from .parent_authority import VerifiedParentFreezeV2, require_current_parent

    if parent_type is not VerifiedParentFreezeV2:
        raise TypeError(
            "current authority requires an exact live VerifiedParentFreezeV2"
        )
    return require_current_parent(parent)


@dataclass(frozen=True)
class _WindowCalibrationAuthorityV2:
    calibration: WindowThresholdCalibrationV2
    parent: object
    fingerprint: str


_WINDOW_CALIBRATION_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedWindowThresholdCalibrationV2],
        _WindowCalibrationAuthorityV2,
    ],
] = {}
_WINDOW_CALIBRATION_LOCK = threading.RLock()


def _window_calibration_seal(
    calibration: WindowThresholdCalibrationV2,
) -> str:
    return canonical_sha(
        {
            "authority_kind": "v3m0-window-threshold-calibration-live-v2",
            "calibration": {
                **window_threshold_calibration_v2_payload(calibration),
                "calibration_v2_sha": calibration.calibration_v2_sha,
            },
        }
    )


def _issue_replayed_window_threshold_calibration_v2(
    calibration: WindowThresholdCalibrationV2,
    parent,
    parent_manifest,
) -> VerifiedWindowThresholdCalibrationV2:
    """Trusted Task-11 replay connection; never a public hydration path."""

    snapshot = verify_window_threshold_calibration_v2_wire(calibration)
    if snapshot.parent_freeze_v2_sha != parent_manifest.parent_freeze_v2_sha:
        raise ValueError("Task-11-v2 calibration is spliced to another Parent-v2")
    fingerprint = _window_calibration_seal(snapshot)
    wrapper = VerifiedWindowThresholdCalibrationV2(
        _ISSUANCE_TOKEN,
        snapshot,
        fingerprint,
    )
    identity = id(wrapper)
    authority = _WindowCalibrationAuthorityV2(
        calibration=copy.deepcopy(snapshot),
        parent=parent,
        fingerprint=fingerprint,
    )

    def remove_stale(
        reference: weakref.ReferenceType[VerifiedWindowThresholdCalibrationV2],
        wrapper_id: int = identity,
    ) -> None:
        with _WINDOW_CALIBRATION_LOCK:
            current = _WINDOW_CALIBRATION_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _WINDOW_CALIBRATION_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove_stale)
    with _WINDOW_CALIBRATION_LOCK:
        _WINDOW_CALIBRATION_LIVE[identity] = (reference, authority)
    return wrapper


def require_window_threshold_calibration_v2(
    calibration: VerifiedWindowThresholdCalibrationV2,
) -> WindowThresholdCalibrationV2:
    """Consume only an exact live module-issued Task-11-v2 capability."""

    if type(calibration) is not VerifiedWindowThresholdCalibrationV2:
        raise TypeError(
            "Task-12-v2 rejects v1, raw, and subclass calibration values"
        )
    with _WINDOW_CALIBRATION_LOCK:
        current = _WINDOW_CALIBRATION_LIVE.get(id(calibration))
        if current is None or current[0]() is not calibration:
            raise ValueError(
                "VerifiedWindowThresholdCalibrationV2 identity is not live"
            )
        authority = current[1]
    try:
        token = object.__getattribute__(
            calibration,
            "_VerifiedWindowThresholdCalibrationV2__token",
        )
        raw = object.__getattribute__(
            calibration,
            "_VerifiedWindowThresholdCalibrationV2__calibration",
        )
        seal = object.__getattribute__(
            calibration,
            "_VerifiedWindowThresholdCalibrationV2__seal",
        )
    except AttributeError as exc:
        raise ValueError("Task-11-v2 calibration record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("Task-11-v2 calibration token mismatch")
    snapshot = verify_window_threshold_calibration_v2_wire(raw)
    parent_manifest = _require_exact_current_parent(authority.parent)
    expected_seal = _window_calibration_seal(snapshot)
    if (
        snapshot != authority.calibration
        or snapshot.parent_freeze_v2_sha
        != parent_manifest.parent_freeze_v2_sha
        or seal != authority.fingerprint
        or seal != expected_seal
    ):
        raise ValueError("Task-11-v2 calibration immutable seal mismatch")
    return copy.deepcopy(authority.calibration)


@dataclass(frozen=True)
class _PermitAuthorityV2:
    permit: CalibrationApplicationPermitV2
    parent: object
    calibration: VerifiedWindowThresholdCalibrationV2
    fingerprint: str


_PERMIT_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedCalibrationApplicationPermitV2],
        _PermitAuthorityV2,
    ],
] = {}
_PERMIT_LOCK = threading.RLock()


def _permit_seal(permit: CalibrationApplicationPermitV2) -> str:
    return canonical_sha(
        {
            "authority_kind": "v3m0-calibration-application-permit-live-v2",
            "permit": {
                **calibration_application_permit_v2_payload(permit),
                "permit_sha": permit.permit_sha,
            },
        }
    )


def _current_application_for_instance(
    parent_manifest,
    application_instance_id: str,
) -> CurrentApplicationAuthorityV2:
    identifier = _text(application_instance_id, "application_instance_id")
    matches = tuple(
        item
        for item in parent_manifest.current_application_authorities
        if item.application_instance_id == identifier
    )
    if len(matches) != 1:
        raise ValueError(
            "application instance ID does not resolve to one current "
            "application authority"
        )
    application = matches[0]
    _verify_current_application_authority(application)

    candidate_matches = tuple(
        item
        for item in parent_manifest.reviewed_candidate_v1.application_candidates
        if item.application_instance_id == identifier
    )
    if len(candidate_matches) != 1:
        raise ValueError(
            "application instance ID does not resolve to one reviewed "
            "candidate-v1 application"
        )
    candidate = candidate_matches[0]
    candidate_specs = tuple(
        item.scenario_execution_spec for item in candidate.scenario_candidates
    )
    if (
        candidate.control_case_id != application.control_case_id
        or candidate.based_on_application_spec_sha
        != application.based_on_application_spec_sha
        or candidate.candidate_application_sha
        != application.source_candidate_v1_application_sha
        or candidate_specs != application.complete_scenario_execution_specs
    ):
        raise ValueError(
            "current application authority is spliced from reviewed candidate-v1"
        )

    source_matches = tuple(
        item
        for item in (
            parent_manifest.historical_parent_v1.synthetic_control_application_specs
        )
        if item.application_instance_id == identifier
    )
    if len(source_matches) != 1:
        raise ValueError(
            "application instance ID does not resolve to one Parent application spec"
        )
    source = source_matches[0]
    if (
        source.control_case_id != application.control_case_id
        or source.application_spec_sha != application.based_on_application_spec_sha
    ):
        raise ValueError("current application authority is spliced from its Parent spec")
    if (
        "control-application-evidence" not in source.required_pipeline_stages
        or "window-calibration" in source.required_pipeline_stages
    ):
        raise ValueError(
            "selected calibration applications C01-C03 cannot receive "
            "application permits"
        )
    return copy.deepcopy(application)


def _expected_calibration_application_permit_v2(
    parent_manifest,
    calibration: WindowThresholdCalibrationV2,
    application_instance_id: str,
) -> CalibrationApplicationPermitV2:
    verified_calibration = verify_window_threshold_calibration_v2_wire(
        calibration
    )
    if (
        verified_calibration.parent_freeze_v2_sha
        != parent_manifest.parent_freeze_v2_sha
    ):
        raise ValueError("Task-11-v2 calibration is bound to another Parent-v2")
    application = _current_application_for_instance(
        parent_manifest,
        application_instance_id,
    )
    scenario_shas = tuple(
        item.scenario_authority_sha
        for item in application.scenario_authorities
    )
    provisional = CalibrationApplicationPermitV2(
        permit_schema_version=(
            CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION
        ),
        scope=_APPLICATION_PERMIT_SCOPE_V2,
        parent_freeze_v2_sha=parent_manifest.parent_freeze_v2_sha,
        calibration=verified_calibration,
        control_case_id=application.control_case_id,
        application_authority=application,
        scenario_authority_shas=scenario_shas,
        selected_fejer_order=(
            verified_calibration.selection.selected_fejer_order
        ),
        permit_sha="0" * 64,
    )
    return CalibrationApplicationPermitV2(
        **{
            **vars(provisional),
            "permit_sha": canonical_sha(
                calibration_application_permit_v2_payload(provisional)
            ),
        }
    )


def _issue_calibration_application_permit_v2(
    permit: CalibrationApplicationPermitV2,
    parent,
    calibration: VerifiedWindowThresholdCalibrationV2,
) -> VerifiedCalibrationApplicationPermitV2:
    snapshot = verify_calibration_application_permit_v2_wire(permit)
    fingerprint = _permit_seal(snapshot)
    wrapper = VerifiedCalibrationApplicationPermitV2(
        _ISSUANCE_TOKEN,
        snapshot,
        fingerprint,
    )
    identity = id(wrapper)
    authority = _PermitAuthorityV2(
        permit=copy.deepcopy(snapshot),
        parent=parent,
        calibration=calibration,
        fingerprint=fingerprint,
    )

    def remove_stale(
        reference: weakref.ReferenceType[VerifiedCalibrationApplicationPermitV2],
        wrapper_id: int = identity,
    ) -> None:
        with _PERMIT_LOCK:
            current = _PERMIT_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _PERMIT_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove_stale)
    with _PERMIT_LOCK:
        _PERMIT_LIVE[identity] = (reference, authority)
    return wrapper


def require_calibration_application_permit_v2(
    permit: VerifiedCalibrationApplicationPermitV2,
) -> CalibrationApplicationPermitV2:
    """Consume only an exact live module-issued Task-12-v2 permit."""

    if type(permit) is not VerifiedCalibrationApplicationPermitV2:
        raise TypeError("Task-12-v2 rejects v1, raw, and subclass permit values")
    with _PERMIT_LOCK:
        current = _PERMIT_LIVE.get(id(permit))
        if current is None or current[0]() is not permit:
            raise ValueError(
                "VerifiedCalibrationApplicationPermitV2 identity is not live"
            )
        authority = current[1]
    try:
        token = object.__getattribute__(
            permit,
            "_VerifiedCalibrationApplicationPermitV2__token",
        )
        raw = object.__getattribute__(
            permit,
            "_VerifiedCalibrationApplicationPermitV2__permit",
        )
        seal = object.__getattribute__(
            permit,
            "_VerifiedCalibrationApplicationPermitV2__seal",
        )
    except AttributeError as exc:
        raise ValueError("Task-12-v2 permit record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("Task-12-v2 permit token mismatch")
    snapshot = verify_calibration_application_permit_v2_wire(raw)
    parent_manifest = _require_exact_current_parent(authority.parent)
    calibration_body = require_window_threshold_calibration_v2(
        authority.calibration
    )
    expected = _expected_calibration_application_permit_v2(
        parent_manifest,
        calibration_body,
        authority.permit.application_authority.application_instance_id,
    )
    expected_seal = _permit_seal(expected)
    if (
        snapshot != authority.permit
        or snapshot != expected
        or seal != authority.fingerprint
        or seal != expected_seal
    ):
        raise ValueError("Task-12-v2 permit immutable seal mismatch")
    return copy.deepcopy(authority.permit)


def _replay_current_window_threshold_calibration_v2(parent, parent_manifest):
    del parent, parent_manifest
    raise ApplicationAuthorityV2UpstreamUnavailable(
        "Task-11-v2 needs a current Parent-v2 control registry, window "
        "protocol, and six-candidate calibration replay; v1 calibration "
        "cannot be rebound by copying its thresholds"
    )


def _require_calibration_parent_identity(
    calibration: VerifiedWindowThresholdCalibrationV2,
    parent,
) -> None:
    with _WINDOW_CALIBRATION_LOCK:
        current = _WINDOW_CALIBRATION_LIVE.get(id(calibration))
        if current is None or current[0]() is not calibration:
            raise ValueError("Task-11-v2 calibration identity is not live")
        if current[1].parent is not parent:
            raise ValueError(
                "Task-11-v2 calibration and permit use different Parent identities"
            )


def _make_public_issuers(
    *,
    parent_reverifier=_require_exact_current_parent,
    calibration_replayer=_replay_current_window_threshold_calibration_v2,
    calibration_issuer=_issue_replayed_window_threshold_calibration_v2,
    calibration_type=VerifiedWindowThresholdCalibrationV2,
    calibration_reverifier=require_window_threshold_calibration_v2,
    calibration_parent_checker=_require_calibration_parent_identity,
    permit_builder=_expected_calibration_application_permit_v2,
    permit_issuer=_issue_calibration_application_permit_v2,
):
    """Freeze public issuers away from later module-global rebinding."""

    def issue_v3m0_window_threshold_calibration_v2(parent):
        parent_manifest = parent_reverifier(parent)
        calibration = calibration_replayer(parent, parent_manifest)
        return calibration_issuer(calibration, parent, parent_manifest)

    def issue_v3m0_calibration_application_permit_v2(
        parent,
        calibration,
        application_instance_id,
    ):
        if type(calibration) is not calibration_type:
            raise TypeError(
                "Task-12-v2 requires an exact live "
                "VerifiedWindowThresholdCalibrationV2"
            )
        parent_manifest = parent_reverifier(parent)
        calibration_body = calibration_reverifier(calibration)
        calibration_parent_checker(calibration, parent)
        expected = permit_builder(
            parent_manifest,
            calibration_body,
            application_instance_id,
        )
        return permit_issuer(expected, parent, calibration)

    return (
        issue_v3m0_window_threshold_calibration_v2,
        issue_v3m0_calibration_application_permit_v2,
    )


(
    issue_v3m0_window_threshold_calibration_v2,
    issue_v3m0_calibration_application_permit_v2,
) = _make_public_issuers()

# The public closures retain these implementation objects in their sealed
# defaults.  Removing the module attributes prevents callers from bypassing
# the live-authority checks by reaching a raw issuer or rebuilding the public
# closures with injected dependencies.
del _issue_replayed_window_threshold_calibration_v2
del _issue_calibration_application_permit_v2
del _make_public_issuers


__all__ = [
    "ApplicationAuthorityV2UpstreamUnavailable",
    "CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION",
    "CalibrationApplicationPermitV2",
    "VerifiedCalibrationApplicationPermitV2",
    "WINDOW_THRESHOLD_CALIBRATION_V2_SCHEMA_VERSION",
    "VerifiedWindowThresholdCalibrationV2",
    "WindowThresholdCalibrationV2",
    "calibration_application_permit_v2_payload",
    "issue_v3m0_calibration_application_permit_v2",
    "issue_v3m0_window_threshold_calibration_v2",
    "require_calibration_application_permit_v2",
    "require_window_threshold_calibration_v2",
    "verify_window_threshold_calibration_v2_wire",
    "verify_calibration_application_permit_v2_wire",
    "window_threshold_calibration_v2_payload",
]
