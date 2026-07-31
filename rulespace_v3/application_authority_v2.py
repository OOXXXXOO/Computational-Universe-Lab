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
from .parent_authority import (
    VerifiedParentFreezeV2,
    require_current_parent as _require_current_parent_v2,
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


def _verify_window_threshold_calibration_v2_wire_impl(
    calibration: WindowThresholdCalibrationV2,
    *,
    exact_record=_exact_record,
    selection_payload=window_threshold_selection_payload,
    calibration_payload=window_threshold_calibration_v2_payload,
    sha_builder=canonical_sha,
    clone=copy.deepcopy,
) -> WindowThresholdCalibrationV2:
    """Validate a raw wire without hydrating it into a capability."""

    exact_record(
        calibration,
        WindowThresholdCalibrationV2,
        "Task-11-v2 calibration wire",
    )
    calibration.__post_init__()
    selection = calibration.selection
    exact_record(selection, WindowThresholdSelection, "threshold selection")
    selection.__post_init__()
    for index, reference in enumerate(selection.selected_evidence_refs):
        exact_record(
            reference,
            SelectedControlEvidenceRef,
            f"selected evidence ref[{index}]",
        )
        reference.__post_init__()
    if selection.selection_sha != sha_builder(
        selection_payload(selection)
    ):
        raise ValueError("selection SHA does not match its exact body")
    if calibration.calibration_v2_sha != sha_builder(
        calibration_payload(calibration)
    ):
        raise ValueError("Task-11-v2 calibration SHA does not match its body")
    return clone(calibration)


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


def _verify_current_application_authority_impl(
    application: CurrentApplicationAuthorityV2,
    *,
    exact_record=_exact_record,
    execution_payload=application_scenario_execution_spec_payload,
    response_payload=current_scenario_response_contract_v2_payload,
    scenario_payload=current_scenario_authority_v2_payload,
    application_payload=current_application_authority_v2_payload,
    sha_builder=canonical_sha,
) -> None:
    exact_record(
        application,
        CurrentApplicationAuthorityV2,
        "current application authority",
    )
    application.__post_init__()
    for index, scenario in enumerate(application.scenario_authorities):
        exact_record(
            scenario,
            CurrentScenarioAuthorityV2,
            f"current scenario authority[{index}]",
        )
        scenario.__post_init__()
        execution = scenario.scenario_execution_spec
        exact_record(
            execution,
            ApplicationScenarioExecutionSpec,
            f"scenario execution spec[{index}]",
        )
        execution.__post_init__()
        if execution.scenario_sha != sha_builder(
            execution_payload(execution)
        ):
            raise ValueError("scenario execution SHA does not match its body")
        response = scenario.response_contract
        exact_record(
            response,
            CurrentScenarioResponseContractV2,
            f"current response contract[{index}]",
        )
        response.__post_init__()
        if response.response_contract_sha != sha_builder(
            response_payload(response)
        ):
            raise ValueError("current response-contract SHA drifted")
        if scenario.scenario_authority_sha != sha_builder(
            scenario_payload(scenario)
        ):
            raise ValueError("current scenario-authority SHA drifted")
    if application.application_authority_sha != sha_builder(
        application_payload(application)
    ):
        raise ValueError("current application-authority SHA drifted")


def _verify_calibration_application_permit_v2_wire_impl(
    permit: CalibrationApplicationPermitV2,
    *,
    exact_record=_exact_record,
    calibration_verifier=_verify_window_threshold_calibration_v2_wire_impl,
    application_verifier=_verify_current_application_authority_impl,
    permit_payload=calibration_application_permit_v2_payload,
    sha_builder=canonical_sha,
    clone=copy.deepcopy,
) -> CalibrationApplicationPermitV2:
    """Validate a raw permit without hydrating it into a capability."""

    exact_record(
        permit,
        CalibrationApplicationPermitV2,
        "Task-12-v2 permit wire",
    )
    permit.__post_init__()
    calibration_verifier(permit.calibration)
    application_verifier(permit.application_authority)
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
    if permit.permit_sha != sha_builder(
        permit_payload(permit)
    ):
        raise ValueError("Task-12-v2 permit SHA does not match its body")
    return clone(permit)


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


def _replay_current_window_threshold_calibration_v2(parent, parent_manifest):
    del parent, parent_manifest
    raise ApplicationAuthorityV2UpstreamUnavailable(
        "Task-11-v2 needs a current Parent-v2 control registry, window "
        "protocol, and six-candidate calibration replay; v1 calibration "
        "cannot be rebound by copying its thresholds"
    )


def _require_exact_current_parent(
    parent,
    *,
    parent_type=VerifiedParentFreezeV2,
    parent_reverifier=_require_current_parent_v2,
    type_fn=type,
):
    if type_fn(parent) is not parent_type:
        raise TypeError(
            "current authority requires an exact live VerifiedParentFreezeV2"
        )
    return parent_reverifier(parent)


@dataclass(frozen=True)
class _WindowCalibrationAuthorityV2:
    calibration: WindowThresholdCalibrationV2
    parent: object
    fingerprint: str


@dataclass(frozen=True)
class _PermitAuthorityV2:
    permit: CalibrationApplicationPermitV2
    parent: object
    calibration: VerifiedWindowThresholdCalibrationV2
    fingerprint: str


def _close_wire_verifiers(window_impl, application_impl, permit_impl):
    exact_record = _exact_record
    selection_payload = window_threshold_selection_payload
    calibration_payload = window_threshold_calibration_v2_payload
    execution_payload = application_scenario_execution_spec_payload
    response_payload = current_scenario_response_contract_v2_payload
    scenario_payload = current_scenario_authority_v2_payload
    application_payload = current_application_authority_v2_payload
    permit_payload = calibration_application_permit_v2_payload
    sha_builder = canonical_sha
    clone = copy.deepcopy

    def verify_window(calibration):
        return window_impl(
            calibration,
            exact_record=exact_record,
            selection_payload=selection_payload,
            calibration_payload=calibration_payload,
            sha_builder=sha_builder,
            clone=clone,
        )

    def verify_application(application):
        return application_impl(
            application,
            exact_record=exact_record,
            execution_payload=execution_payload,
            response_payload=response_payload,
            scenario_payload=scenario_payload,
            application_payload=application_payload,
            sha_builder=sha_builder,
        )

    def verify_permit(permit):
        return permit_impl(
            permit,
            exact_record=exact_record,
            calibration_verifier=verify_window,
            application_verifier=verify_application,
            permit_payload=permit_payload,
            sha_builder=sha_builder,
            clone=clone,
        )

    verify_window.__name__ = "verify_window_threshold_calibration_v2_wire"
    verify_application.__name__ = "_verify_current_application_authority"
    verify_permit.__name__ = "verify_calibration_application_permit_v2_wire"
    return verify_window, verify_application, verify_permit


(
    verify_window_threshold_calibration_v2_wire,
    _verify_current_application_authority,
    verify_calibration_application_permit_v2_wire,
) = _close_wire_verifiers(
    _verify_window_threshold_calibration_v2_wire_impl,
    _verify_current_application_authority_impl,
    _verify_calibration_application_permit_v2_wire_impl,
)


def _close_parent_reverifier():
    parent_impl = _require_exact_current_parent
    parent_type = VerifiedParentFreezeV2
    parent_reverifier = _require_current_parent_v2
    type_fn = type

    def require_parent(parent):
        return parent_impl(
            parent,
            parent_type=parent_type,
            parent_reverifier=parent_reverifier,
            type_fn=type_fn,
        )

    require_parent.__name__ = "_require_exact_current_parent"
    return require_parent


_require_exact_current_parent = _close_parent_reverifier()


def _make_application_authority_graph(issuance_token):
    parent_reverifier = _require_exact_current_parent
    calibration_replayer = _replay_current_window_threshold_calibration_v2
    calibration_verifier = verify_window_threshold_calibration_v2_wire
    application_verifier = _verify_current_application_authority
    permit_verifier = verify_calibration_application_permit_v2_wire
    calibration_payload = window_threshold_calibration_v2_payload
    permit_payload = calibration_application_permit_v2_payload
    sha_builder = canonical_sha
    text_validator = _text
    clone = copy.deepcopy
    weak_reference = weakref.ref
    lock_builder = threading.RLock
    id_fn = id
    type_fn = type
    object_getattribute = object.__getattribute__
    window_wrapper_type = VerifiedWindowThresholdCalibrationV2
    permit_wrapper_type = VerifiedCalibrationApplicationPermitV2
    permit_wire_type = CalibrationApplicationPermitV2
    window_authority_type = _WindowCalibrationAuthorityV2
    permit_authority_type = _PermitAuthorityV2
    permit_schema_version = CALIBRATION_APPLICATION_PERMIT_V2_SCHEMA_VERSION
    permit_scope = _APPLICATION_PERMIT_SCOPE_V2
    window_live: dict[int, object] = {}
    permit_live: dict[int, object] = {}
    window_lock = lock_builder()
    permit_lock = lock_builder()

    def window_seal(calibration):
        return sha_builder(
            {
                "authority_kind": "v3m0-window-threshold-calibration-live-v2",
                "calibration": {
                    **calibration_payload(calibration),
                    "calibration_v2_sha": calibration.calibration_v2_sha,
                },
            }
        )

    def permit_seal(permit):
        return sha_builder(
            {
                "authority_kind": "v3m0-calibration-application-permit-live-v2",
                "permit": {
                    **permit_payload(permit),
                    "permit_sha": permit.permit_sha,
                },
            }
        )

    def current_application_for_instance(
        parent_manifest,
        application_instance_id,
    ):
        identifier = text_validator(
            application_instance_id,
            "application_instance_id",
        )
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
        application_verifier(application)

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
                "application instance ID does not resolve to one Parent "
                "application spec"
            )
        source = source_matches[0]
        if (
            source.control_case_id != application.control_case_id
            or source.application_spec_sha
            != application.based_on_application_spec_sha
        ):
            raise ValueError(
                "current application authority is spliced from its Parent spec"
            )
        if (
            "control-application-evidence" not in source.required_pipeline_stages
            or "window-calibration" in source.required_pipeline_stages
        ):
            raise ValueError(
                "selected calibration applications C01-C03 cannot receive "
                "application permits"
            )
        return clone(application)

    def expected_permit(
        parent_manifest,
        calibration,
        application_instance_id,
    ):
        verified_calibration = calibration_verifier(calibration)
        if (
            verified_calibration.parent_freeze_v2_sha
            != parent_manifest.parent_freeze_v2_sha
        ):
            raise ValueError(
                "Task-11-v2 calibration is bound to another Parent-v2"
            )
        application = current_application_for_instance(
            parent_manifest,
            application_instance_id,
        )
        scenario_shas = tuple(
            item.scenario_authority_sha
            for item in application.scenario_authorities
        )
        provisional = permit_wire_type(
            permit_schema_version=permit_schema_version,
            scope=permit_scope,
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
        return permit_wire_type(
            **{
                **vars(provisional),
                "permit_sha": sha_builder(permit_payload(provisional)),
            }
        )

    def issue_calibration(parent):
        parent_manifest = parent_reverifier(parent)
        replayed = calibration_replayer(parent, parent_manifest)
        snapshot = calibration_verifier(replayed)
        if snapshot.parent_freeze_v2_sha != parent_manifest.parent_freeze_v2_sha:
            raise ValueError(
                "Task-11-v2 calibration is spliced to another Parent-v2"
            )
        fingerprint = window_seal(snapshot)
        wrapper = window_wrapper_type(
            issuance_token,
            snapshot,
            fingerprint,
        )
        identity = id_fn(wrapper)
        authority = window_authority_type(
            calibration=clone(snapshot),
            parent=parent,
            fingerprint=fingerprint,
        )

        def remove_stale(reference, wrapper_id=identity):
            with window_lock:
                current = window_live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del window_live[wrapper_id]

        reference = weak_reference(wrapper, remove_stale)
        with window_lock:
            current = window_live.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("Task-11-v2 calibration identity collision")
            window_live[identity] = (reference, authority)
        return wrapper

    def require_calibration(calibration):
        if type_fn(calibration) is not window_wrapper_type:
            raise TypeError(
                "Task-12-v2 rejects v1, raw, and subclass calibration values"
            )
        with window_lock:
            current = window_live.get(id_fn(calibration))
            if current is None or current[0]() is not calibration:
                raise ValueError(
                    "VerifiedWindowThresholdCalibrationV2 identity is not live"
                )
            authority = current[1]
        try:
            token = object_getattribute(
                calibration,
                "_VerifiedWindowThresholdCalibrationV2__token",
            )
            raw = object_getattribute(
                calibration,
                "_VerifiedWindowThresholdCalibrationV2__calibration",
            )
            seal = object_getattribute(
                calibration,
                "_VerifiedWindowThresholdCalibrationV2__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "Task-11-v2 calibration record is incomplete"
            ) from exc
        if token is not issuance_token:
            raise ValueError("Task-11-v2 calibration token mismatch")
        snapshot = calibration_verifier(raw)
        parent_manifest = parent_reverifier(authority.parent)
        replayed = calibration_verifier(
            calibration_replayer(authority.parent, parent_manifest)
        )
        expected_seal = window_seal(replayed)
        if (
            snapshot != authority.calibration
            or snapshot != replayed
            or replayed.parent_freeze_v2_sha
            != parent_manifest.parent_freeze_v2_sha
            or seal != authority.fingerprint
            or seal != expected_seal
        ):
            raise ValueError("Task-11-v2 calibration immutable seal mismatch")
        return clone(replayed)

    def require_calibration_parent_identity(calibration, parent):
        with window_lock:
            current = window_live.get(id_fn(calibration))
            if current is None or current[0]() is not calibration:
                raise ValueError("Task-11-v2 calibration identity is not live")
            if current[1].parent is not parent:
                raise ValueError(
                    "Task-11-v2 calibration and permit use different "
                    "Parent identities"
                )

    def issue_permit(parent, calibration, application_instance_id):
        if type_fn(calibration) is not window_wrapper_type:
            raise TypeError(
                "Task-12-v2 requires an exact live "
                "VerifiedWindowThresholdCalibrationV2"
            )
        parent_manifest = parent_reverifier(parent)
        calibration_body = require_calibration(calibration)
        require_calibration_parent_identity(calibration, parent)
        expected = expected_permit(
            parent_manifest,
            calibration_body,
            application_instance_id,
        )
        snapshot = permit_verifier(expected)
        fingerprint = permit_seal(snapshot)
        wrapper = permit_wrapper_type(
            issuance_token,
            snapshot,
            fingerprint,
        )
        identity = id_fn(wrapper)
        authority = permit_authority_type(
            permit=clone(snapshot),
            parent=parent,
            calibration=calibration,
            fingerprint=fingerprint,
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
                raise RuntimeError("Task-12-v2 permit identity collision")
            permit_live[identity] = (reference, authority)
        return wrapper

    def require_permit(permit):
        if type_fn(permit) is not permit_wrapper_type:
            raise TypeError("Task-12-v2 rejects v1, raw, and subclass permit values")
        with permit_lock:
            current = permit_live.get(id_fn(permit))
            if current is None or current[0]() is not permit:
                raise ValueError(
                    "VerifiedCalibrationApplicationPermitV2 identity is not live"
                )
            authority = current[1]
        try:
            token = object_getattribute(
                permit,
                "_VerifiedCalibrationApplicationPermitV2__token",
            )
            raw = object_getattribute(
                permit,
                "_VerifiedCalibrationApplicationPermitV2__permit",
            )
            seal = object_getattribute(
                permit,
                "_VerifiedCalibrationApplicationPermitV2__seal",
            )
        except AttributeError as exc:
            raise ValueError("Task-12-v2 permit record is incomplete") from exc
        if token is not issuance_token:
            raise ValueError("Task-12-v2 permit token mismatch")
        snapshot = permit_verifier(raw)
        parent_manifest = parent_reverifier(authority.parent)
        calibration_body = require_calibration(authority.calibration)
        require_calibration_parent_identity(
            authority.calibration,
            authority.parent,
        )
        expected = expected_permit(
            parent_manifest,
            calibration_body,
            authority.permit.application_authority.application_instance_id,
        )
        expected_seal = permit_seal(expected)
        if (
            snapshot != authority.permit
            or snapshot != expected
            or seal != authority.fingerprint
            or seal != expected_seal
        ):
            raise ValueError("Task-12-v2 permit immutable seal mismatch")
        return clone(authority.permit)

    def require_permit_for_parent(permit_v2, formal_parent_v2):
        """Replay a permit and prove that its owner is this Parent identity."""

        permit_body = require_permit(permit_v2)
        parent_manifest = parent_reverifier(formal_parent_v2)
        with permit_lock:
            current = permit_live.get(id_fn(permit_v2))
            if current is None or current[0]() is not permit_v2:
                raise ValueError(
                    "Task-12-v2 permit identity is not live for Parent binding"
                )
            authority = current[1]
        if authority.parent is not formal_parent_v2:
            raise ValueError(
                "Task-12-v2 permit belongs to a different Parent identity"
            )
        if (
            permit_body.parent_freeze_v2_sha
            != parent_manifest.parent_freeze_v2_sha
        ):
            raise ValueError(
                "Task-12-v2 permit body is spliced to another Parent-v2"
            )
        return permit_body

    def calibration_property(wrapper):
        return require_calibration(wrapper)

    def permit_property(wrapper):
        return require_permit(wrapper)

    current_application_for_instance.__name__ = (
        "_current_application_for_instance"
    )
    expected_permit.__name__ = "_expected_calibration_application_permit_v2"
    issue_calibration.__name__ = "_issue_replayed_window_threshold_calibration_v2"
    require_calibration.__name__ = "require_window_threshold_calibration_v2"
    issue_permit.__name__ = "_issue_calibration_application_permit_v2"
    require_permit.__name__ = "require_calibration_application_permit_v2"
    require_permit_for_parent.__name__ = (
        "_require_calibration_application_permit_v2_for_parent"
    )
    return (
        current_application_for_instance,
        expected_permit,
        issue_calibration,
        require_calibration,
        issue_permit,
        require_permit,
        require_permit_for_parent,
        calibration_property,
        permit_property,
    )


(
    _current_application_for_instance,
    _expected_calibration_application_permit_v2,
    _closed_calibration_issuer,
    require_window_threshold_calibration_v2,
    _closed_permit_issuer,
    require_calibration_application_permit_v2,
    _require_calibration_application_permit_v2_for_parent,
    _calibration_property,
    _permit_property,
) = _make_application_authority_graph(_ISSUANCE_TOKEN)

VerifiedWindowThresholdCalibrationV2.calibration = property(
    _calibration_property
)
VerifiedCalibrationApplicationPermitV2.permit = property(_permit_property)


def _make_public_issuers(calibration_issuer, permit_issuer):
    """Expose only issuers that replay their complete live authority graph."""

    def issue_v3m0_window_threshold_calibration_v2(parent):
        return calibration_issuer(parent)

    def issue_v3m0_calibration_application_permit_v2(
        parent,
        calibration,
        application_instance_id,
    ):
        return permit_issuer(
            parent,
            calibration,
            application_instance_id,
        )

    return (
        issue_v3m0_window_threshold_calibration_v2,
        issue_v3m0_calibration_application_permit_v2,
    )


(
    issue_v3m0_window_threshold_calibration_v2,
    issue_v3m0_calibration_application_permit_v2,
) = _make_public_issuers(
    _closed_calibration_issuer,
    _closed_permit_issuer,
)

# Every closure-reachable issuer independently replays its live inputs, so
# extracting a private callable cannot create a raw hydration path.
del _closed_calibration_issuer
del _closed_permit_issuer
del _calibration_property
del _permit_property
del _verify_window_threshold_calibration_v2_wire_impl
del _verify_current_application_authority_impl
del _verify_calibration_application_permit_v2_wire_impl
del _close_wire_verifiers
del _close_parent_reverifier
del _make_application_authority_graph
del _make_public_issuers
del _ISSUANCE_TOKEN


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
