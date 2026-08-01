"""Parent-v3 Task-11 calibration and application-permit authority tests."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, fields, replace
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

CONTROL_CASE_IDS = (
    "C01_BLIND_HOLDOUT_FULL",
    "C02_CONDITIONED_ZERO",
    "C03_EQUAL_RANK_DIRECT_SUM",
    "C04_CANONICAL_ANGLE_025_075",
    "C05_PHASE_AND_SCALAR_GAIN",
    "C06_INTERNAL_NONSCALE_MIXING",
    "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE",
    "C08_RANK_R_MISSING_MODES",
    "C09_PURE_GAUGE_DRESSING",
    "C10_FULL_SOURCE_EXTRA_MODE",
    "C11_NULL_GREY_SIGNAL_AMPLITUDE",
    "C12_NU_INC_IR_NORMALIZATION",
    "C13_BOTH_ZERO_UNDEFINED",
    "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL",
    "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
    "C16_COVERAGE_025_075",
    "C17_QUOTIENT_GAUGE_COVERAGE",
    "C18_ABLATED_INDEPENDENT_UNARY",
    "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
    "C20_DM26_CLEAN_ZERO_TRUE_FLOOR",
)


@dataclass(frozen=True)
class _FakeStatus:
    defined: bool


@dataclass(frozen=True)
class _FakeSelection:
    selected_fejer_order: int


@dataclass(frozen=True)
class _FakeOutcome:
    status: _FakeStatus
    manifest: str
    selection: _FakeSelection | None
    outcome_sha: str

    def __post_init__(self) -> None:
        if self.status.defined != (self.selection is not None):
            raise ValueError("fake outcome status/selection mismatch")


@dataclass(frozen=True)
class _FakeResponseV2:
    scenario_id: str
    response_contract_sha: str


@dataclass(frozen=True)
class _FakeScenarioV2:
    control_case_id: str
    application_instance_id: str
    scenario_id: str
    response_contract: _FakeResponseV2
    scenario_authority_sha: str


@dataclass(frozen=True)
class _FakeApplicationV2:
    control_case_id: str
    application_instance_id: str
    scenario_authorities: tuple[_FakeScenarioV2, ...]
    application_authority_sha: str


@dataclass(frozen=True)
class _FakeResponseV3:
    control_case_id: str
    application_instance_id: str
    scenario_id: str
    response_contract_sha: str


@dataclass(frozen=True)
class _FakeScenarioV3:
    control_case_id: str
    application_instance_id: str
    scenario_id: str
    response_contract: _FakeResponseV3
    scenario_authority_sha: str


@dataclass(frozen=True)
class _FakeApplicationV3:
    control_case_id: str
    application_instance_id: str
    scenario_authorities: tuple[_FakeScenarioV3, ...]
    application_authority_sha: str


@dataclass(frozen=True)
class _FakeHistoricalManifest:
    marker: str


@dataclass(frozen=True)
class _FakeHistoricalParent:
    manifest: _FakeHistoricalManifest


@dataclass(frozen=True)
class _FakeParent:
    manifest: object


class _RogueEqualBody:
    """Hostile repeated body whose equality lies about every comparison."""

    def __init__(self, source: object) -> None:
        self.__dict__.update(vars(source))
        if "scenario_id" in self.__dict__:
            self.scenario_id = "v3m0.rogue.scenario"
        for field in ("scenario_authority_sha", "response_contract_sha"):
            if field in self.__dict__:
                setattr(self, field, "6" * 64)

    def __eq__(self, other: object) -> bool:
        del other
        return True


def _fake_outcome_payload(outcome: _FakeOutcome) -> dict[str, object]:
    return {
        "status": {"defined": outcome.status.defined},
        "manifest": outcome.manifest,
        "selection": (
            None
            if outcome.selection is None
            else {
                "selected_fejer_order": outcome.selection.selected_fejer_order,
            }
        ),
    }


def _fake_v2_application_payload(
    application: _FakeApplicationV2,
) -> dict[str, object]:
    if type(application) is not _FakeApplicationV2:
        raise TypeError("expected exact fake V2 application")
    return {
        "control_case_id": application.control_case_id,
        "application_instance_id": application.application_instance_id,
        "scenario_authorities": [
            {
                "control_case_id": scenario.control_case_id,
                "application_instance_id": scenario.application_instance_id,
                "scenario_id": scenario.scenario_id,
                "response_contract": {
                    "scenario_id": scenario.response_contract.scenario_id,
                    "response_contract_sha": (
                        scenario.response_contract.response_contract_sha
                    ),
                },
                "scenario_authority_sha": scenario.scenario_authority_sha,
            }
            for scenario in application.scenario_authorities
        ],
    }


def _fake_v3_response_payload(response: _FakeResponseV3) -> dict[str, object]:
    return {
        "control_case_id": response.control_case_id,
        "application_instance_id": response.application_instance_id,
        "scenario_id": response.scenario_id,
    }


def _fake_v3_scenario_payload(scenario: _FakeScenarioV3) -> dict[str, object]:
    return {
        "control_case_id": scenario.control_case_id,
        "application_instance_id": scenario.application_instance_id,
        "scenario_id": scenario.scenario_id,
        "response_contract": {
            **_fake_v3_response_payload(scenario.response_contract),
            "response_contract_sha": (scenario.response_contract.response_contract_sha),
        },
    }


def _fake_v3_application_payload(
    application: _FakeApplicationV3,
) -> dict[str, object]:
    return {
        "control_case_id": application.control_case_id,
        "application_instance_id": application.application_instance_id,
        "scenario_authorities": [
            {
                **_fake_v3_scenario_payload(scenario),
                "scenario_authority_sha": scenario.scenario_authority_sha,
            }
            for scenario in application.scenario_authorities
        ],
    }


def _v2_application(case_id: str, ordinal: int) -> _FakeApplicationV2:
    application_id = f"v3m0.fake.application.{ordinal:02d}.v2"
    scenario_id = f"{application_id}.success"
    response = _FakeResponseV2(scenario_id, f"{ordinal + 31:064x}")
    scenario = _FakeScenarioV2(
        case_id,
        application_id,
        scenario_id,
        response,
        f"{ordinal + 61:064x}",
    )
    return _FakeApplicationV2(
        case_id,
        application_id,
        (scenario,),
        f"{ordinal + 91:064x}",
    )


def _v3_application() -> _FakeApplicationV3:
    case_id = CONTROL_CASE_IDS[18]
    application_id = "v3m0.synthetic-control.c19.v2"
    scenario_id = f"{application_id}.success"
    response = _FakeResponseV3(
        case_id,
        application_id,
        scenario_id,
        "d" * 64,
    )
    scenario = _FakeScenarioV3(
        case_id,
        application_id,
        scenario_id,
        response,
        "e" * 64,
    )
    return _FakeApplicationV3(case_id, application_id, (scenario,), "f" * 64)


def _make_fake_authority_graph(
    monkeypatch: pytest.MonkeyPatch,
    *,
    resolved: bool = True,
    missing_case: str | None = None,
):
    import rulespace_v3.application_authority_v3 as facade
    from rulespace_v3.evidence import canonical_sha

    historical_manifest = _FakeHistoricalManifest("historical-parent-v1")
    historical_parent = _FakeHistoricalParent(historical_manifest)
    inherited = tuple(
        _v2_application(case_id, ordinal)
        for ordinal, case_id in enumerate(CONTROL_CASE_IDS)
        if case_id != CONTROL_CASE_IDS[18] and case_id != missing_case
    )
    refrozen = (_v3_application(),)
    candidate = SimpleNamespace(
        historical_parent_v1=historical_manifest,
        reviewed_candidate_v1=SimpleNamespace(
            application_candidates=tuple(
                SimpleNamespace(control_case_id=case_id) for case_id in CONTROL_CASE_IDS
            )
        ),
        inherited_current_application_authorities_v2=inherited,
        refrozen_current_application_authorities_v3=refrozen,
    )

    def current_registry_payload(observed_candidate) -> dict[str, object]:
        if observed_candidate != candidate:
            raise ValueError("candidate body drifted")
        inherited_by_case = {item.control_case_id: item for item in inherited}
        refrozen_by_case = {item.control_case_id: item for item in refrozen}
        entries = []
        for ordinal, case_id in enumerate(CONTROL_CASE_IDS):
            if case_id in inherited_by_case:
                application = inherited_by_case[case_id]
                entries.append(
                    {
                        "parent_v1_ordinal": ordinal,
                        "authority_tag": "INHERITED_CURRENT_V2",
                        "application_authority": {
                            **_fake_v2_application_payload(application),
                            "application_authority_sha": (
                                application.application_authority_sha
                            ),
                        },
                    }
                )
            elif case_id in refrozen_by_case:
                application_v3 = refrozen_by_case[case_id]
                entries.append(
                    {
                        "parent_v1_ordinal": ordinal,
                        "authority_tag": "REFROZEN_CURRENT_V3",
                        "application_authority": {
                            **_fake_v3_application_payload(application_v3),
                            "application_authority_sha": (
                                application_v3.application_authority_sha
                            ),
                        },
                    }
                )
            else:
                raise ValueError("current registry is missing an application")
        return {
            "current_application_registry_schema_version": (
                "v3m0.current-application-registry.v3"
            ),
            "entries": entries,
        }

    registry_payload = (
        None if missing_case is not None else current_registry_payload(candidate)
    )
    parent_manifest = SimpleNamespace(
        reviewed_candidate_v3=candidate,
        current_application_registry_sha=(
            "0" * 64 if registry_payload is None else canonical_sha(registry_payload)
        ),
        parent_freeze_v3_sha="a" * 64,
    )
    parent = _FakeParent(parent_manifest)

    provisional_outcome = _FakeOutcome(
        _FakeStatus(resolved),
        "six-order-task11-manifest",
        _FakeSelection(32) if resolved else None,
        "0" * 64,
    )
    outcome = replace(
        provisional_outcome,
        outcome_sha=canonical_sha(_fake_outcome_payload(provisional_outcome)),
    )
    counters = {"parent": 0, "task8": 0, "task11": 0}

    def require_parent(observed_parent):
        counters["parent"] += 1
        if type(observed_parent) is not _FakeParent:
            raise TypeError("exact fake Parent-v3 required")
        return copy.deepcopy(observed_parent.manifest)

    def issue_historical_parent():
        return historical_parent

    def reverify_historical_parent(observed_parent):
        if type(observed_parent) is not _FakeHistoricalParent:
            raise TypeError("exact historical parent required")
        return observed_parent.manifest

    def replay_task8(observed_parent, scenarios):
        counters["task8"] += 1
        if observed_parent is not historical_parent:
            raise ValueError("historical parent identity drifted")
        if tuple(item.control_case_id for item in scenarios) != CONTROL_CASE_IDS[:3]:
            raise ValueError("Task8 scenarios are not exact C01-C03")
        return SimpleNamespace(scenarios=scenarios, marker="task8-replay")

    def run_task11(observed_parent, task8_replay):
        counters["task11"] += 1
        if observed_parent is not historical_parent:
            raise ValueError("Task11 historical parent drifted")
        if task8_replay.marker != "task8-replay":
            raise ValueError("Task11 replay drifted")
        return outcome

    monkeypatch.setattr(facade, "canonical_sha", canonical_sha)
    monkeypatch.setattr(facade, "WindowCalibrationOutcome", _FakeOutcome)
    monkeypatch.setattr(
        facade,
        "window_calibration_outcome_payload",
        _fake_outcome_payload,
    )
    monkeypatch.setattr(facade, "VerifiedParentFreezeV3", _FakeParent)
    monkeypatch.setattr(facade, "require_current_parent_v3", require_parent)
    monkeypatch.setattr(
        facade,
        "current_application_registry_v3_payload",
        current_registry_payload,
    )
    monkeypatch.setattr(
        facade,
        "current_application_authority_v2_payload",
        _fake_v2_application_payload,
    )
    monkeypatch.setattr(
        facade,
        "CurrentScenarioResponseContractV3",
        _FakeResponseV3,
    )
    monkeypatch.setattr(facade, "CurrentScenarioAuthorityV3", _FakeScenarioV3)
    monkeypatch.setattr(facade, "CurrentApplicationAuthorityV3", _FakeApplicationV3)
    monkeypatch.setattr(
        facade,
        "current_scenario_response_contract_v3_payload",
        _fake_v3_response_payload,
    )
    monkeypatch.setattr(
        facade,
        "current_scenario_authority_v3_payload",
        _fake_v3_scenario_payload,
    )
    monkeypatch.setattr(
        facade,
        "current_application_authority_v3_payload",
        _fake_v3_application_payload,
    )
    monkeypatch.setattr(
        facade,
        "verify_current_application_authority_v3",
        lambda value: (
            value
            if type(value) is _FakeApplicationV3
            else (_ for _ in ()).throw(TypeError("exact fake V3 application required"))
        ),
    )
    monkeypatch.setattr(facade, "VerifiedParentFreeze", _FakeHistoricalParent)
    monkeypatch.setattr(facade, "issue_v3m0_parent_freeze", issue_historical_parent)
    monkeypatch.setattr(
        facade,
        "_reverify_verified_parent_freeze",
        reverify_historical_parent,
    )
    monkeypatch.setattr(
        facade,
        "_replay_current_task8_control_roots",
        replay_task8,
    )
    monkeypatch.setattr(
        facade,
        "_run_task11_window_calibration_from_task8_replay",
        run_task11,
    )
    monkeypatch.setattr(facade, "APPLICATION_CONTROL_CASE_IDS", CONTROL_CASE_IDS)

    graph = facade._make_application_authority_v3_graph(facade._ISSUANCE_TOKEN)
    return SimpleNamespace(
        facade=facade,
        graph=graph,
        parent=parent,
        parent_manifest=parent_manifest,
        historical_parent=historical_parent,
        candidate=candidate,
        outcome=outcome,
        v3_application=refrozen[0],
        counters=counters,
    )


def test_exact_raw_records_public_signatures_and_no_v2_surface() -> None:
    import rulespace_v3.application_authority_v3 as facade

    assert [
        item.name for item in fields(facade.ParentV3CalibrationControlReplayRefV1)
    ] == [
        "replay_ref_schema_version",
        "parent_freeze_v3_sha",
        "current_application_registry_sha",
        "parent_v1_ordinal",
        "authority_tag",
        "control_case_id",
        "control_id",
        "application_authority_v2",
        "application_authority_v2_sha",
        "scenario_authority_v2",
        "scenario_authority_v2_sha",
        "response_contract_v2",
        "response_contract_v2_sha",
        "replay_ref_sha",
    ]
    assert [item.name for item in fields(facade.WindowThresholdCalibrationV3)] == [
        "calibration_v3_schema_version",
        "parent_freeze_v3_sha",
        "current_application_registry_sha",
        "current_application_registry_v3",
        "calibration_control_replay_refs",
        "calibration_outcome",
        "calibration_v3_sha",
    ]
    assert [item.name for item in fields(facade.CalibrationApplicationPermitV3)] == [
        "permit_schema_version",
        "parent_freeze_v3_sha",
        "calibration",
        "current_application_authority",
        "current_scenario_authority",
        "current_scenario_response_contract",
        "selected_fejer_order",
        "permit_scope_id",
        "permit_sha",
    ]
    assert tuple(
        inspect.signature(facade.calibrate_v3m0_window_thresholds_v3).parameters
    ) == ("parent",)
    assert tuple(
        inspect.signature(facade.verify_window_threshold_calibration_v3).parameters
    ) == ("parent", "calibration")
    assert tuple(
        inspect.signature(facade.issue_calibration_application_permit_v3).parameters
    ) == (
        "parent",
        "calibration",
        "control_case_id",
        "application_instance_id",
        "scenario_id",
    )
    assert tuple(
        inspect.signature(facade.verify_calibration_application_permit_v3).parameters
    ) == ("parent", "permit")
    assert not any("V2" in name for name in facade.__all__)


def test_calibration_binds_full_mixed_registry_and_exact_c01_c03_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fake_authority_graph(monkeypatch)
    wrapper = fixture.graph.calibrate(fixture.parent)
    body = wrapper.calibration

    assert type(wrapper) is fixture.facade.VerifiedWindowThresholdCalibrationV3
    assert body.parent_freeze_v3_sha == fixture.parent_manifest.parent_freeze_v3_sha
    assert body.current_application_registry_sha == (
        fixture.parent_manifest.current_application_registry_sha
    )
    entries = body.current_application_registry_v3["entries"]
    assert len(entries) == 20
    assert [item["parent_v1_ordinal"] for item in entries] == list(range(20))
    assert [item["authority_tag"] for item in entries].count(
        "INHERITED_CURRENT_V2"
    ) == 19
    assert [item["authority_tag"] for item in entries].count("REFROZEN_CURRENT_V3") == 1
    assert tuple(
        (item.parent_v1_ordinal, item.control_case_id, item.control_id)
        for item in body.calibration_control_replay_refs
    ) == (
        (0, CONTROL_CASE_IDS[0], "full"),
        (1, CONTROL_CASE_IDS[1], "zero"),
        (2, CONTROL_CASE_IDS[2], "direct_sum"),
    )
    assert all(
        item.authority_tag == "INHERITED_CURRENT_V2"
        for item in body.calibration_control_replay_refs
    )
    assert all(
        "parent_freeze_v2_sha" not in vars(item)
        for item in body.calibration_control_replay_refs
    )
    full_wire = fixture.facade.window_threshold_calibration_v3_payload(body)
    assert "parent_freeze_v2_sha" not in json.dumps(full_wire, sort_keys=True)
    assert body.calibration_outcome == fixture.outcome
    assert fixture.counters["task8"] >= 1
    assert fixture.counters["task11"] >= 1

    detached = wrapper.calibration
    object.__setattr__(detached, "parent_freeze_v3_sha", "9" * 64)
    assert wrapper.calibration == body
    assert fixture.graph.verify_calibration(fixture.parent, wrapper) is wrapper


def test_resolved_calibration_issues_only_exact_current_v3_scenario_permit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fake_authority_graph(monkeypatch)
    calibration = fixture.graph.calibrate(fixture.parent)
    application = fixture.v3_application
    scenario = application.scenario_authorities[0]
    permit = fixture.graph.issue_permit(
        fixture.parent,
        calibration,
        application.control_case_id,
        application.application_instance_id,
        scenario.scenario_id,
    )
    body = permit.permit

    assert type(permit) is fixture.facade.VerifiedCalibrationApplicationPermitV3
    assert body.calibration == calibration.calibration
    assert body.current_application_authority == application
    assert body.current_scenario_authority == scenario
    assert body.current_scenario_response_contract == scenario.response_contract
    assert body.selected_fejer_order == 32
    assert body.permit_scope_id == "v3m0-parent-v3-current-application-scenario-v1"
    assert fixture.graph.verify_permit(fixture.parent, permit) is permit

    with pytest.raises(TypeError):
        fixture.graph.verify_permit(fixture.parent, body)
    forged = object.__new__(fixture.facade.VerifiedCalibrationApplicationPermitV3)
    with pytest.raises((TypeError, ValueError, AttributeError)):
        fixture.graph.verify_permit(fixture.parent, forged)
    equal_parent = _FakeParent(copy.deepcopy(fixture.parent_manifest))
    with pytest.raises(ValueError, match="Parent|identity|root"):
        fixture.graph.verify_permit(equal_parent, permit)

    detached = permit.permit
    object.__setattr__(detached, "selected_fejer_order", 64)
    assert permit.permit == body

    internal = object.__getattribute__(
        permit,
        "_VerifiedCalibrationApplicationPermitV3__permit",
    )
    object.__setattr__(internal, "selected_fejer_order", 64)
    with pytest.raises(ValueError, match="seal|splice|root|immutable"):
        fixture.graph.verify_permit(fixture.parent, permit)


def test_calibration_and_permit_resolver_redirection_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calibration_fixture = _make_fake_authority_graph(monkeypatch)
    calibration = calibration_fixture.graph.calibrate(calibration_fixture.parent)
    object.__setattr__(
        calibration,
        "_VerifiedWindowThresholdCalibrationV3__resolver",
        lambda _wrapper: object(),
    )
    with pytest.raises(ValueError, match="resolver|immutable"):
        calibration_fixture.graph.verify_calibration(
            calibration_fixture.parent,
            calibration,
        )

    permit_fixture = _make_fake_authority_graph(monkeypatch)
    permit_calibration = permit_fixture.graph.calibrate(permit_fixture.parent)
    application = permit_fixture.v3_application
    scenario = application.scenario_authorities[0]
    permit = permit_fixture.graph.issue_permit(
        permit_fixture.parent,
        permit_calibration,
        application.control_case_id,
        application.application_instance_id,
        scenario.scenario_id,
    )
    object.__setattr__(
        permit,
        "_VerifiedCalibrationApplicationPermitV3__resolver",
        lambda _wrapper: object(),
    )
    with pytest.raises(ValueError, match="resolver|immutable"):
        permit_fixture.graph.verify_permit(permit_fixture.parent, permit)


def test_unresolved_window_never_issues_permit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fake_authority_graph(monkeypatch, resolved=False)
    calibration = fixture.graph.calibrate(fixture.parent)
    application = fixture.v3_application
    scenario = application.scenario_authorities[0]

    assert calibration.calibration.calibration_outcome.selection is None
    with pytest.raises(fixture.facade.ApplicationAuthorityV3Failure) as caught:
        fixture.graph.issue_permit(
            fixture.parent,
            calibration,
            application.control_case_id,
            application.application_instance_id,
            scenario.scenario_id,
        )
    assert caught.value.reason_id == "WINDOW_UNRESOLVED"


def test_missing_task8_case_raw_hydration_cross_parent_and_splices_die(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fake_authority_graph(monkeypatch)
    calibration = fixture.graph.calibrate(fixture.parent)
    raw = calibration.calibration
    application = fixture.v3_application
    scenario = application.scenario_authorities[0]

    with pytest.raises(TypeError):
        fixture.graph.verify_calibration(fixture.parent, raw)
    forged = object.__new__(fixture.facade.VerifiedWindowThresholdCalibrationV3)
    with pytest.raises((TypeError, ValueError, AttributeError)):
        fixture.graph.verify_calibration(fixture.parent, forged)
    equal_parent = _FakeParent(copy.deepcopy(fixture.parent_manifest))
    with pytest.raises(ValueError, match="Parent|identity|root"):
        fixture.graph.verify_calibration(equal_parent, calibration)
    for identifiers in (
        (
            CONTROL_CASE_IDS[0],
            application.application_instance_id,
            scenario.scenario_id,
        ),
        (application.control_case_id, "wrong-application", scenario.scenario_id),
        (
            application.control_case_id,
            application.application_instance_id,
            "wrong-scenario",
        ),
    ):
        with pytest.raises((fixture.facade.ApplicationAuthorityV3Failure, ValueError)):
            fixture.graph.issue_permit(
                fixture.parent,
                calibration,
                *identifiers,
            )

    internal = object.__getattribute__(
        calibration,
        "_VerifiedWindowThresholdCalibrationV3__calibration",
    )
    object.__setattr__(internal, "parent_freeze_v3_sha", "f" * 64)
    with pytest.raises(ValueError, match="seal|splice|root|immutable"):
        fixture.graph.verify_calibration(fixture.parent, calibration)

    missing_fixture = _make_fake_authority_graph(
        monkeypatch,
        missing_case=CONTROL_CASE_IDS[1],
    )
    with pytest.raises((ValueError, fixture.facade.ApplicationAuthorityV3Failure)):
        missing_fixture.graph.calibrate(missing_fixture.parent)


@pytest.mark.parametrize("splice", ("delete", "reorder", "tag", "body"))
def test_full_registry_delete_reorder_tag_and_body_splices_die(
    monkeypatch: pytest.MonkeyPatch,
    splice: str,
) -> None:
    fixture = _make_fake_authority_graph(monkeypatch)
    calibration = fixture.graph.calibrate(fixture.parent)
    internal = object.__getattribute__(
        calibration,
        "_VerifiedWindowThresholdCalibrationV3__calibration",
    )
    entries = internal.current_application_registry_v3["entries"]
    if splice == "delete":
        entries.pop()
    elif splice == "reorder":
        entries[0], entries[1] = entries[1], entries[0]
    elif splice == "tag":
        entries[0]["authority_tag"] = "REFROZEN_CURRENT_V3"
    else:
        entries[0]["application_authority"]["application_authority_sha"] = "7" * 64
    with pytest.raises(ValueError, match="seal|splice|root|immutable"):
        fixture.graph.verify_calibration(fixture.parent, calibration)


@pytest.mark.parametrize(
    "repeated_field",
    ("scenario_authority_v2", "response_contract_v2"),
)
def test_rogue_equal_repeated_scenario_and_response_bodies_die(
    monkeypatch: pytest.MonkeyPatch,
    repeated_field: str,
) -> None:
    fixture = _make_fake_authority_graph(monkeypatch)
    calibration = fixture.graph.calibrate(fixture.parent)
    internal = object.__getattribute__(
        calibration,
        "_VerifiedWindowThresholdCalibrationV3__calibration",
    )
    replay_ref = internal.calibration_control_replay_refs[0]
    source = getattr(replay_ref, repeated_field)
    object.__setattr__(replay_ref, repeated_field, _RogueEqualBody(source))

    with pytest.raises(ValueError, match="seal|splice|root|immutable"):
        fixture.graph.verify_calibration(fixture.parent, calibration)


@pytest.mark.parametrize(
    "repeated_field",
    ("current_scenario_authority", "current_scenario_response_contract"),
)
def test_rogue_equal_permit_scenario_and_response_bodies_die(
    monkeypatch: pytest.MonkeyPatch,
    repeated_field: str,
) -> None:
    fixture = _make_fake_authority_graph(monkeypatch)
    calibration = fixture.graph.calibrate(fixture.parent)
    application = fixture.v3_application
    scenario = application.scenario_authorities[0]
    permit = fixture.graph.issue_permit(
        fixture.parent,
        calibration,
        application.control_case_id,
        application.application_instance_id,
        scenario.scenario_id,
    )
    internal = object.__getattribute__(
        permit,
        "_VerifiedCalibrationApplicationPermitV3__permit",
    )
    source = getattr(internal, repeated_field)
    object.__setattr__(internal, repeated_field, _RogueEqualBody(source))

    with pytest.raises(ValueError, match="seal|splice|root|immutable"):
        fixture.graph.verify_permit(fixture.parent, permit)


def test_production_module_has_only_frozen_direct_import_edges() -> None:
    module_path = REPO_ROOT / "rulespace_v3/application_authority_v3.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            imported.add(f"rulespace_v3.{node.module}")
    assert imported == {
        "rulespace_v3.calibration_authority",
        "rulespace_v3.parent_authority_v3",
        "rulespace_v3.parent_candidate_v3",
        "rulespace_v3.parent_freeze",
        "rulespace_v3.parent_v3_contracts",
        "rulespace_v3.task11_runner",
        "rulespace_v3.task8_control_replay",
    }
    assert not imported & {
        "rulespace_v3.application_authority_v2",
        "rulespace_v3.current_window_replay",
        "rulespace_v3.parent_authority",
        "rulespace_v3.parent_freeze_v2",
        "rulespace_v3.parent_v2_contracts",
        "rulespace_v3.task11_evidence",
    }

    import rulespace_v3.application_authority_v3 as facade

    for public_api in (
        facade.calibrate_v3m0_window_thresholds_v3,
        facade.verify_window_threshold_calibration_v3,
        facade.issue_calibration_application_permit_v3,
        facade.verify_calibration_application_permit_v3,
    ):
        assert "_PRODUCTION_GRAPH" not in public_api.__code__.co_names
