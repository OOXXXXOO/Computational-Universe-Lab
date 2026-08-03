"""B9-lower tests for the exact Parent-v3 scenario replay authority."""

from __future__ import annotations

import ast
import copy
import gc
import inspect
import weakref
from dataclasses import dataclass, fields, replace
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
OWNER_PATH = REPO_ROOT / "rulespace_v3" / "parent_v3_scenario_replay_authority_v1.py"
SCHEMA_VERSION = "v3m0.parent-v3-scenario-replay-authority.v1"
PREPARATION_COMMIT_SHA = "1" * 40
PARENT_V3_SHA = "2" * 64
ALLOWED_IMPORTS = {
    "rulespace_v3.evidence",
    "rulespace_v3.parent_authority_v3",
    "rulespace_v3.parent_freeze",
}


@dataclass(frozen=True)
class _FakeReviewedCandidateV3:
    historical_parent_v1: object


@dataclass(frozen=True)
class _FakeParentFreezeV3Manifest:
    parent_freeze_v3_sha: str
    preparation_commit_sha: str
    reviewed_candidate_v3: _FakeReviewedCandidateV3


class _FakeVerifiedParentFreezeV3:
    __slots__ = ("manifest", "__weakref__")

    def __init__(self, manifest: _FakeParentFreezeV3Manifest) -> None:
        self.manifest = manifest


@pytest.fixture(scope="module")
def historical_parent_v1():
    from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze

    return issue_v3m0_parent_freeze().manifest


def _module():
    import rulespace_v3.parent_v3_scenario_replay_authority_v1 as facade

    return facade


def _fake_parent_payload(manifest: _FakeParentFreezeV3Manifest) -> dict[str, object]:
    if type(manifest) is not _FakeParentFreezeV3Manifest:
        raise TypeError("exact fake Parent-v3 manifest required")
    return {
        "parent_freeze_schema_version": "v3m0.fake-parent-v3.v1",
        "preparation_commit_sha": manifest.preparation_commit_sha,
        "reviewed_candidate_v3": {
            "historical_parent_v1_sha": (
                manifest.reviewed_candidate_v3.historical_parent_v1.parent_freeze_sha
            )
        },
    }


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    historical_parent_v1,
):
    facade = _module()
    manifest = _FakeParentFreezeV3Manifest(
        parent_freeze_v3_sha=PARENT_V3_SHA,
        preparation_commit_sha=PREPARATION_COMMIT_SHA,
        reviewed_candidate_v3=_FakeReviewedCandidateV3(historical_parent_v1),
    )
    parent = _FakeVerifiedParentFreezeV3(manifest)
    calls: list[object] = []

    def require_parent(observed):
        calls.append(observed)
        if type(observed) is not _FakeVerifiedParentFreezeV3:
            raise TypeError("exact fake live Parent-v3 required")
        if observed is not parent:
            raise ValueError("fake Parent-v3 identity is not live")
        if observed.manifest != manifest:
            raise ValueError("fake Parent-v3 body drifted")
        return copy.deepcopy(manifest)

    monkeypatch.setattr(
        facade,
        "VerifiedParentFreezeV3",
        _FakeVerifiedParentFreezeV3,
    )
    monkeypatch.setattr(
        facade,
        "ParentFreezeV3Manifest",
        _FakeParentFreezeV3Manifest,
    )
    monkeypatch.setattr(facade, "require_current_parent_v3", require_parent)
    monkeypatch.setattr(
        facade,
        "_parent_freeze_v3_manifest_payload",
        _fake_parent_payload,
    )
    graph = facade._make_parent_v3_scenario_replay_authority_v1_graph(
        facade._ISSUANCE_TOKEN
    )
    owner_payload = facade._make_parent_v3_scenario_replay_authority_v1_payload_api(
        facade._parent_v3_scenario_replay_authority_v1_payload_impl,
        body_type=facade.ParentV3ScenarioReplayAuthorityV1,
        record_validator=facade._exact_record,
        body_validator=facade.ParentV3ScenarioReplayAuthorityV1.__post_init__,
        parent_type=_FakeParentFreezeV3Manifest,
        parent_payload_builder=_fake_parent_payload,
        application_type=facade.V3M0SyntheticControlApplicationSpec,
        application_payload_builder=(facade.synthetic_control_application_spec_payload),
        scenario_type=facade.ApplicationScenarioExecutionSpec,
        scenario_payload_builder=(facade.application_scenario_execution_spec_payload),
    )
    return SimpleNamespace(
        facade=facade,
        graph=graph,
        parent=parent,
        manifest=manifest,
        historical=historical_parent_v1,
        calls=calls,
        owner_payload=owner_payload,
    )


def _assert_rejected(callable_) -> None:
    with pytest.raises((AttributeError, RuntimeError, TypeError, ValueError)):
        callable_()


def _direct_rulespace_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            imported.add(f"rulespace_v3.{node.module}")
        elif isinstance(node, ast.Import):
            imported.update(
                alias.name
                for alias in node.names
                if alias.name.startswith("rulespace_v3.")
            )
    return imported


def _full_application_payload(facade, application) -> dict[str, object]:
    return {
        **facade.synthetic_control_application_spec_payload(application),
        "application_spec_sha": application.application_spec_sha,
    }


def _full_scenario_payload(facade, scenario) -> dict[str, object]:
    return {
        **facade.application_scenario_execution_spec_payload(scenario),
        "scenario_sha": scenario.scenario_sha,
    }


def _reviewed_path_closure_payload(closure) -> dict[str, object]:
    return {
        "reviewed_path_closure_schema_version": (
            "v3m0.parent-reviewed-path-closure.v1"
        ),
        "entries": [
            {"relative_path": path, "raw_sha256": raw_sha} for path, raw_sha in closure
        ],
    }


def test_owner_surface_exact_record_api_and_import_dag() -> None:
    facade = _module()

    assert [item.name for item in fields(facade.ParentV3ScenarioReplayAuthorityV1)] == [
        "replay_schema_version",
        "parent_freeze_v3",
        "preparation_commit_sha",
        "source_parent_v1_ordinal",
        "control_case_id",
        "application_spec",
        "scenario_specs",
        "p_blob_source_closure",
        "p_blob_source_closure_sha",
        "replay_sha",
    ]
    assert [
        item.name
        for item in fields(facade._VerifiedParentV3ScenarioReplayAuthorityV1View)
    ] == ["replay_authority", "parent"]
    assert tuple(
        inspect.signature(facade.replay_parent_v3_scenario_authority_v1).parameters
    ) == ("parent", "control_case_id")
    assert tuple(
        inspect.signature(
            facade._reverify_verified_parent_v3_scenario_replay_authority_v1
        ).parameters
    ) == ("replay",)
    assert tuple(
        inspect.signature(
            facade._require_parent_v3_scenario_replay_authority_v1_for_parent
        ).parameters
    ) == ("parent", "replay")
    assert tuple(
        inspect.signature(
            facade.parent_v3_scenario_replay_authority_v1_payload
        ).parameters
    ) == ("replay",)
    assert isinstance(
        facade.VerifiedParentV3ScenarioReplayAuthorityV1.replay_authority,
        property,
    )
    assert tuple(facade.__all__) == (
        "ParentV3ScenarioReplayAuthorityV1",
        "VerifiedParentV3ScenarioReplayAuthorityV1",
        "parent_v3_scenario_replay_authority_v1_payload",
        "replay_parent_v3_scenario_authority_v1",
    )
    with pytest.raises(TypeError):
        facade.VerifiedParentV3ScenarioReplayAuthorityV1()

    imports = _direct_rulespace_imports(OWNER_PATH)
    assert imports == ALLOWED_IMPORTS
    source = OWNER_PATH.read_text(encoding="utf-8").lower()
    for forbidden in (
        "runtime_v3",
        ".blocks",
        "hydrate",
        "promote",
        "resign",
        "opaque_adapter",
    ):
        assert forbidden not in source


@pytest.mark.parametrize(
    ("control_case_id", "ordinal"),
    (
        ("C01_BLIND_HOLDOUT_FULL", 1),
        ("C18_ABLATED_INDEPENDENT_UNARY", 18),
        ("C20_DM26_CLEAN_ZERO_TRUE_FLOOR", 20),
    ),
)
def test_replay_issues_exact_parent_p_blob_body(
    monkeypatch: pytest.MonkeyPatch,
    historical_parent_v1,
    control_case_id: str,
    ordinal: int,
) -> None:
    from rulespace_v3.evidence import canonical_sha

    fixture = _fixture(monkeypatch, historical_parent_v1)
    capability = fixture.graph.replay(fixture.parent, control_case_id)
    raw = capability.replay_authority
    application = historical_parent_v1.synthetic_control_application_specs[ordinal - 1]

    assert type(capability) is (
        fixture.facade.VerifiedParentV3ScenarioReplayAuthorityV1
    )
    assert type(raw) is fixture.facade.ParentV3ScenarioReplayAuthorityV1
    assert raw.replay_schema_version == SCHEMA_VERSION
    assert raw.parent_freeze_v3 == fixture.manifest
    assert raw.parent_freeze_v3 is not fixture.manifest
    assert raw.preparation_commit_sha == PREPARATION_COMMIT_SHA
    assert raw.source_parent_v1_ordinal == ordinal
    assert raw.control_case_id == control_case_id
    assert raw.application_spec == application
    assert raw.application_spec is not application
    assert raw.scenario_specs == application.scenario_execution_specs
    assert raw.scenario_specs is not application.scenario_execution_specs
    assert raw.p_blob_source_closure == historical_parent_v1.source_closure
    assert raw.p_blob_source_closure is not historical_parent_v1.source_closure
    assert raw.p_blob_source_closure_sha == canonical_sha(
        _reviewed_path_closure_payload(historical_parent_v1.source_closure)
    )
    assert raw.replay_sha == canonical_sha(fixture.owner_payload(raw))

    payload = fixture.owner_payload(raw)
    assert list(payload) == [item.name for item in fields(type(raw))][:-1]
    assert payload["parent_freeze_v3"] == {
        **_fake_parent_payload(fixture.manifest),
        "parent_freeze_v3_sha": PARENT_V3_SHA,
    }
    assert payload["application_spec"] == _full_application_payload(
        fixture.facade,
        application,
    )
    assert payload["scenario_specs"] == [
        _full_scenario_payload(fixture.facade, scenario)
        for scenario in application.scenario_execution_specs
    ]
    assert payload["p_blob_source_closure"] == [
        list(item) for item in historical_parent_v1.source_closure
    ]

    view = fixture.graph.require_for_parent(fixture.parent, capability)
    assert view.parent is fixture.parent
    assert view.replay_authority == raw
    assert view.replay_authority is not raw
    assert all(call is fixture.parent for call in fixture.calls)


@pytest.mark.parametrize(
    "control_case_id",
    (
        "C01",
        "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
        "C20",
        "c01_blind_holdout_full",
        "C21_NOT_REGISTERED",
        "",
        None,
        1,
    ),
)
def test_replay_rejects_nonexact_or_excluded_control_ids(
    monkeypatch: pytest.MonkeyPatch,
    historical_parent_v1,
    control_case_id: object,
) -> None:
    fixture = _fixture(monkeypatch, historical_parent_v1)
    _assert_rejected(lambda: fixture.graph.replay(fixture.parent, control_case_id))


def test_replay_rejects_parent_copy_wrapper_forgery_cross_graph_and_death(
    monkeypatch: pytest.MonkeyPatch,
    historical_parent_v1,
) -> None:
    fixture = _fixture(monkeypatch, historical_parent_v1)
    capability = fixture.graph.replay(fixture.parent, "C01_BLIND_HOLDOUT_FULL")
    raw = capability.replay_authority

    equal_parent = _FakeVerifiedParentFreezeV3(copy.deepcopy(fixture.manifest))
    _assert_rejected(
        lambda: fixture.graph.replay(equal_parent, "C01_BLIND_HOLDOUT_FULL")
    )
    _assert_rejected(
        lambda capability=capability: fixture.graph.require_for_parent(
            equal_parent,
            capability,
        )
    )
    _assert_rejected(lambda: fixture.graph.require_for_parent(fixture.parent, raw))

    forged = object.__new__(fixture.facade.VerifiedParentV3ScenarioReplayAuthorityV1)
    _assert_rejected(lambda: fixture.graph.reverify(forged))
    try:
        equal_copy = copy.copy(capability)
    except (AttributeError, TypeError, ValueError):
        pass
    else:
        _assert_rejected(lambda: fixture.graph.reverify(equal_copy))
    other_graph = fixture.facade._make_parent_v3_scenario_replay_authority_v1_graph(
        fixture.facade._ISSUANCE_TOKEN
    )
    _assert_rejected(lambda capability=capability: other_graph.reverify(capability))

    reference = weakref.ref(capability)
    del capability
    gc.collect()
    assert reference() is None


@pytest.mark.parametrize(
    ("field_name", "replacement_factory"),
    (
        ("source_parent_v1_ordinal", lambda raw: raw.source_parent_v1_ordinal + 1),
        ("control_case_id", lambda raw: "C02_CONDITIONED_ZERO"),
        (
            "application_spec",
            lambda raw: replace(raw.application_spec, application_spec_sha="f" * 64),
        ),
        (
            "scenario_specs",
            lambda raw: tuple(reversed(raw.scenario_specs)),
        ),
        (
            "p_blob_source_closure",
            lambda raw: tuple(reversed(raw.p_blob_source_closure)),
        ),
        ("p_blob_source_closure_sha", lambda raw: "e" * 64),
        ("replay_sha", lambda raw: "d" * 64),
    ),
)
def test_recursive_reverification_rejects_ordinal_body_root_and_p_blob_drift(
    monkeypatch: pytest.MonkeyPatch,
    historical_parent_v1,
    field_name: str,
    replacement_factory,
) -> None:
    fixture = _fixture(monkeypatch, historical_parent_v1)
    capability = fixture.graph.replay(fixture.parent, "C05_PHASE_AND_SCALAR_GAIN")
    raw = capability.replay_authority
    try:
        hostile = replace(raw, **{field_name: replacement_factory(raw)})
    except (TypeError, ValueError):
        return
    object.__setattr__(
        capability,
        "_VerifiedParentV3ScenarioReplayAuthorityV1__replay_authority",
        hostile,
    )
    _assert_rejected(lambda: fixture.graph.reverify(capability))


def test_recursive_reverification_rejects_seal_tamper_and_parent_p_blob_drift(
    monkeypatch: pytest.MonkeyPatch,
    historical_parent_v1,
) -> None:
    fixture = _fixture(monkeypatch, historical_parent_v1)
    seal_tampered = fixture.graph.replay(
        fixture.parent,
        "C01_BLIND_HOLDOUT_FULL",
    )
    object.__setattr__(
        seal_tampered,
        "_VerifiedParentV3ScenarioReplayAuthorityV1__authority_seal",
        "0" * 64,
    )
    _assert_rejected(lambda: fixture.graph.reverify(seal_tampered))

    body_tampered = fixture.graph.replay(
        fixture.parent,
        "C20_DM26_CLEAN_ZERO_TRUE_FLOOR",
    )
    hostile_historical = replace(
        historical_parent_v1,
        source_closure=tuple(reversed(historical_parent_v1.source_closure)),
    )
    object.__setattr__(
        fixture.parent,
        "manifest",
        replace(
            fixture.manifest,
            reviewed_candidate_v3=_FakeReviewedCandidateV3(hostile_historical),
        ),
    )
    _assert_rejected(lambda: fixture.graph.reverify(body_tampered))


def test_graph_captures_dependencies_before_hostile_global_rebinding(
    monkeypatch: pytest.MonkeyPatch,
    historical_parent_v1,
) -> None:
    fixture = _fixture(monkeypatch, historical_parent_v1)
    first = fixture.graph.replay(
        fixture.parent,
        "C01_BLIND_HOLDOUT_FULL",
    )
    first_raw = first.replay_authority
    baseline_payload = fixture.owner_payload(first_raw)
    expected_record_type = fixture.facade.ParentV3ScenarioReplayAuthorityV1
    expected_wrapper_type = fixture.facade.VerifiedParentV3ScenarioReplayAuthorityV1
    expected_view_type = fixture.facade._VerifiedParentV3ScenarioReplayAuthorityV1View

    def bomb(*args, **kwargs):
        del args, kwargs
        raise AssertionError("late-bound hostile dependency was called")

    for name in (
        "VerifiedParentFreezeV3",
        "ParentFreezeV3Manifest",
        "V3M0SyntheticControlApplicationSpec",
        "ApplicationScenarioExecutionSpec",
        "require_current_parent_v3",
        "_parent_freeze_v3_manifest_payload",
        "canonical_sha",
        "synthetic_control_application_spec_payload",
        "application_scenario_execution_spec_payload",
        "verify_synthetic_control_application_spec",
        "verify_application_scenario_execution_spec",
        "ParentV3ScenarioReplayAuthorityV1",
        "VerifiedParentV3ScenarioReplayAuthorityV1",
        "_VerifiedParentV3ScenarioReplayAuthorityV1View",
        "_exact_record",
        "_text",
        "_sha256",
        "_git_sha1",
        "_source_closure",
        "_reviewed_path_closure_payload",
        "_parent_v3_scenario_replay_authority_v1_payload_impl",
        "PurePosixPath",
        "dataclass_fields",
        "replace",
        "copy",
    ):
        monkeypatch.setattr(fixture.facade, name, bomb)
    monkeypatch.setattr(
        fixture.facade,
        "PARENT_V3_SCENARIO_REPLAY_AUTHORITY_V1_SCHEMA_VERSION",
        "redirected-schema",
    )
    monkeypatch.setattr(
        fixture.facade,
        "APPLICATION_CONTROL_CASE_IDS",
        ("redirected-control",),
    )
    monkeypatch.setattr(
        fixture.facade,
        "_REPLAY_CONTROL_CASE_IDS",
        ("redirected-replay",),
    )
    monkeypatch.setattr(
        fixture.facade,
        "weakref",
        SimpleNamespace(ref=bomb),
    )

    assert fixture.owner_payload(first_raw) == baseline_payload
    first_view = fixture.graph.reverify(first)
    assert type(first) is expected_wrapper_type
    assert type(first_view) is expected_view_type
    assert type(first_view.replay_authority) is expected_record_type
    capability = fixture.graph.replay(
        fixture.parent,
        "C20_DM26_CLEAN_ZERO_TRUE_FLOOR",
    )
    view = fixture.graph.require_for_parent(fixture.parent, capability)
    assert view.parent is fixture.parent
    assert view.replay_authority.control_case_id == ("C20_DM26_CLEAN_ZERO_TRUE_FLOOR")


def test_no_public_raw_verifier_or_capability_minting_surface() -> None:
    facade = _module()
    public_names = set(facade.__all__)

    assert public_names == {
        "ParentV3ScenarioReplayAuthorityV1",
        "VerifiedParentV3ScenarioReplayAuthorityV1",
        "parent_v3_scenario_replay_authority_v1_payload",
        "replay_parent_v3_scenario_authority_v1",
    }
    assert not any(
        token in name.lower()
        for name in public_names
        for token in ("verify", "hydrate", "promote", "resign", "mint")
    )
    raw = facade.ParentV3ScenarioReplayAuthorityV1
    assert not hasattr(raw, "verify")
    assert not hasattr(raw, "hydrate")
