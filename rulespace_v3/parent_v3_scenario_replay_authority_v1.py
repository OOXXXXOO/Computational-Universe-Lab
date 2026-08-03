"""Exact lower-owner replay of inherited scenarios from one live Parent-v3."""

from __future__ import annotations

import copy
import re
import threading
import weakref
from dataclasses import dataclass, fields as dataclass_fields, replace
from pathlib import PurePosixPath
from typing import Literal, NamedTuple

from .evidence import canonical_sha
from .parent_authority_v3 import (
    ParentFreezeV3Manifest,
    VerifiedParentFreezeV3,
    _parent_freeze_v3_manifest_payload,
    require_current_parent_v3,
)
from .parent_freeze import (
    APPLICATION_CONTROL_CASE_IDS,
    ApplicationScenarioExecutionSpec,
    V3M0SyntheticControlApplicationSpec,
    application_scenario_execution_spec_payload,
    synthetic_control_application_spec_payload,
    verify_application_scenario_execution_spec,
    verify_synthetic_control_application_spec,
)


PARENT_V3_SCENARIO_REPLAY_AUTHORITY_V1_SCHEMA_VERSION = (
    "v3m0.parent-v3-scenario-replay-authority.v1"
)
_REVIEWED_PATH_CLOSURE_SCHEMA_VERSION = "v3m0.parent-reviewed-path-closure.v1"
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWER_GIT_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_ISSUANCE_TOKEN = object()
_PROPERTY_BINDING_TOKEN = object()
_REPLAY_CONTROL_CASE_IDS = APPLICATION_CONTROL_CASE_IDS[:18] + (
    APPLICATION_CONTROL_CASE_IDS[19],
)

ReplayControlCaseId = Literal[
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
    "C20_DM26_CLEAN_ZERO_TRUE_FLOOR",
]


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise TypeError(f"{field} must be an exact non-empty string")
    return value


def _sha256(value: object, field: str, *, _text_validator=_text) -> str:
    result = _text_validator(value, field)
    if _LOWER_SHA256.fullmatch(result) is None:
        raise ValueError(f"{field} must be one lowercase SHA-256")
    return result


def _git_sha1(value: object, field: str, *, _text_validator=_text) -> str:
    result = _text_validator(value, field)
    if _LOWER_GIT_SHA1.fullmatch(result) is None:
        raise ValueError(f"{field} must be one lowercase Git SHA-1")
    return result


def _exact_record(
    value: object,
    record_type: type,
    field: str,
    *,
    _fields_builder=dataclass_fields,
) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    expected = frozenset(item.name for item in _fields_builder(record_type))
    if frozenset(vars(value)) != expected:
        raise ValueError(f"{field} contains unknown or missing fields")


def _source_closure(
    value: object,
    *,
    _sha_validator=_sha256,
    _text_validator=_text,
    _path_type=PurePosixPath,
) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple or not value:
        raise TypeError("p_blob_source_closure must be a non-empty exact tuple")
    entries: list[tuple[str, str]] = []
    for index, entry in enumerate(value):
        if type(entry) is not tuple or len(entry) != 2:
            raise TypeError(
                f"p_blob_source_closure[{index}] must be an exact path/SHA pair"
            )
        path = _text_validator(
            entry[0],
            f"p_blob_source_closure[{index}].relative_path",
        )
        raw_sha = _sha_validator(
            entry[1],
            f"p_blob_source_closure[{index}].raw_sha256",
        )
        pure_path = _path_type(path)
        if (
            pure_path.is_absolute()
            or str(pure_path) != path
            or any(part in ("", ".", "..") for part in pure_path.parts)
        ):
            raise ValueError("p_blob_source_closure contains a non-canonical path")
        entries.append((path, raw_sha))
    paths = tuple(path for path, _ in entries)
    if len(set(paths)) != len(paths):
        raise ValueError("p_blob_source_closure contains duplicate paths")
    if paths != tuple(sorted(paths, key=lambda path: path.encode("utf-8"))):
        raise ValueError("p_blob_source_closure is not in UTF-8 path order")
    return tuple(entries)


def _reviewed_path_closure_payload(
    closure: tuple[tuple[str, str], ...],
    *,
    _closure_validator=_source_closure,
    _schema_version=_REVIEWED_PATH_CLOSURE_SCHEMA_VERSION,
) -> dict[str, object]:
    entries = _closure_validator(closure)
    return {
        "reviewed_path_closure_schema_version": _schema_version,
        "entries": [
            {"relative_path": path, "raw_sha256": raw_sha} for path, raw_sha in entries
        ],
    }


@dataclass(frozen=True)
class ParentV3ScenarioReplayAuthorityV1:
    replay_schema_version: str
    parent_freeze_v3: ParentFreezeV3Manifest
    preparation_commit_sha: str
    source_parent_v1_ordinal: int
    control_case_id: ReplayControlCaseId
    application_spec: V3M0SyntheticControlApplicationSpec
    scenario_specs: tuple[ApplicationScenarioExecutionSpec, ...]
    p_blob_source_closure: tuple[tuple[str, str], ...]
    p_blob_source_closure_sha: str
    replay_sha: str

    def __post_init__(
        self,
        *,
        _schema=PARENT_V3_SCENARIO_REPLAY_AUTHORITY_V1_SCHEMA_VERSION,
        _control_ids=APPLICATION_CONTROL_CASE_IDS,
        _replay_ids=_REPLAY_CONTROL_CASE_IDS,
        _application_type=V3M0SyntheticControlApplicationSpec,
        _scenario_type=ApplicationScenarioExecutionSpec,
        _record_validator=_exact_record,
        _git_validator=_git_sha1,
        _closure_validator=_source_closure,
        _sha_validator=_sha256,
    ) -> None:
        if self.replay_schema_version != _schema:
            raise ValueError("Parent-v3 scenario replay schema drifted")
        _git_validator(self.preparation_commit_sha, "preparation_commit_sha")
        if type(self.source_parent_v1_ordinal) is not int:
            raise TypeError("source_parent_v1_ordinal must be an exact int")
        if self.control_case_id not in _replay_ids:
            raise ValueError("control_case_id is outside C01-C18,C20")
        expected_ordinal = _control_ids.index(self.control_case_id) + 1
        if self.source_parent_v1_ordinal != expected_ordinal:
            raise ValueError("source_parent_v1_ordinal disagrees with Parent-v1 order")
        _record_validator(
            self.application_spec,
            _application_type,
            "application_spec",
        )
        if self.application_spec.control_case_id != self.control_case_id:
            raise ValueError("application_spec control_case_id drifted")
        if type(self.scenario_specs) is not tuple or not self.scenario_specs:
            raise TypeError("scenario_specs must be a non-empty exact tuple")
        for index, scenario in enumerate(self.scenario_specs):
            _record_validator(
                scenario,
                _scenario_type,
                f"scenario_specs[{index}]",
            )
        if self.scenario_specs != self.application_spec.scenario_execution_specs:
            raise ValueError("scenario_specs drifted from the complete application")
        _closure_validator(self.p_blob_source_closure)
        _sha_validator(
            self.p_blob_source_closure_sha,
            "p_blob_source_closure_sha",
        )
        _sha_validator(self.replay_sha, "replay_sha")


def _parent_v3_scenario_replay_authority_v1_payload_impl(
    replay: object,
    *,
    body_type: type,
    record_validator,
    body_validator,
    parent_type: type,
    parent_payload_builder,
    application_type: type,
    application_payload_builder,
    scenario_type: type,
    scenario_payload_builder,
) -> dict[str, object]:
    record_validator(replay, body_type, "Parent-v3 scenario replay authority")
    body_validator(replay)
    record_validator(replay.parent_freeze_v3, parent_type, "parent_freeze_v3")
    record_validator(replay.application_spec, application_type, "application_spec")
    for index, scenario in enumerate(replay.scenario_specs):
        record_validator(scenario, scenario_type, f"scenario_specs[{index}]")
    return {
        "replay_schema_version": replay.replay_schema_version,
        "parent_freeze_v3": {
            **parent_payload_builder(replay.parent_freeze_v3),
            "parent_freeze_v3_sha": replay.parent_freeze_v3.parent_freeze_v3_sha,
        },
        "preparation_commit_sha": replay.preparation_commit_sha,
        "source_parent_v1_ordinal": replay.source_parent_v1_ordinal,
        "control_case_id": replay.control_case_id,
        "application_spec": {
            **application_payload_builder(replay.application_spec),
            "application_spec_sha": replay.application_spec.application_spec_sha,
        },
        "scenario_specs": [
            {
                **scenario_payload_builder(scenario),
                "scenario_sha": scenario.scenario_sha,
            }
            for scenario in replay.scenario_specs
        ],
        "p_blob_source_closure": [list(item) for item in replay.p_blob_source_closure],
        "p_blob_source_closure_sha": replay.p_blob_source_closure_sha,
    }


def _make_parent_v3_scenario_replay_authority_v1_payload_api(
    payload_impl,
    *,
    body_type,
    record_validator,
    body_validator,
    parent_type,
    parent_payload_builder,
    application_type,
    application_payload_builder,
    scenario_type,
    scenario_payload_builder,
):
    def parent_v3_scenario_replay_authority_v1_payload(
        replay,
    ) -> dict[str, object]:
        return payload_impl(
            replay,
            body_type=body_type,
            record_validator=record_validator,
            body_validator=body_validator,
            parent_type=parent_type,
            parent_payload_builder=parent_payload_builder,
            application_type=application_type,
            application_payload_builder=application_payload_builder,
            scenario_type=scenario_type,
            scenario_payload_builder=scenario_payload_builder,
        )

    return parent_v3_scenario_replay_authority_v1_payload


parent_v3_scenario_replay_authority_v1_payload = (
    _make_parent_v3_scenario_replay_authority_v1_payload_api(
        _parent_v3_scenario_replay_authority_v1_payload_impl,
        body_type=ParentV3ScenarioReplayAuthorityV1,
        record_validator=_exact_record,
        body_validator=ParentV3ScenarioReplayAuthorityV1.__post_init__,
        parent_type=ParentFreezeV3Manifest,
        parent_payload_builder=_parent_freeze_v3_manifest_payload,
        application_type=V3M0SyntheticControlApplicationSpec,
        application_payload_builder=synthetic_control_application_spec_payload,
        scenario_type=ApplicationScenarioExecutionSpec,
        scenario_payload_builder=application_scenario_execution_spec_payload,
    )
)


@dataclass(frozen=True)
class _VerifiedParentV3ScenarioReplayAuthorityV1View:
    replay_authority: ParentV3ScenarioReplayAuthorityV1
    parent: VerifiedParentFreezeV3


class VerifiedParentV3ScenarioReplayAuthorityV1:
    """Opaque live identity for one exact Parent-v3 inherited replay."""

    __slots__ = (
        "__replay_authority",
        "__authority_seal",
        "__token",
        "__weakref__",
    )

    def __init__(self) -> None:
        raise TypeError("Parent-v3 scenario replay authority is module-issued only")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("Parent-v3 scenario replay authority is immutable")


def _make_property_dispatcher(
    binding_token: object,
    *,
    _weak_reference=weakref.ref,
    _id=id,
):
    bindings: dict[int, tuple[weakref.ReferenceType[object], object]] = {}
    lock = threading.RLock()

    def require_binding(value, expected_resolver=None):
        with lock:
            current = bindings.get(_id(value))
            if current is None or current[0]() is not value:
                raise ValueError("scenario replay property identity is not live")
            resolver = current[1]
        if expected_resolver is not None and resolver is not expected_resolver:
            raise ValueError("scenario replay property resolver drifted")
        return resolver

    def resolve(value):
        return require_binding(value)(value)

    def bind(value, resolver, *, token):
        if token is not binding_token:
            raise TypeError("scenario replay property binding token mismatch")
        identity = _id(value)

        def remove_stale(reference, wrapper_id=identity):
            with lock:
                current = bindings.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del bindings[wrapper_id]

        reference = _weak_reference(value, remove_stale)
        with lock:
            current = bindings.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("scenario replay property identity collision")
            bindings[identity] = (reference, resolver)

    return resolve, bind, require_binding


(
    _resolve_replay_authority_property,
    _bind_replay_authority_property,
    _require_replay_authority_property_binding,
) = _make_property_dispatcher(_PROPERTY_BINDING_TOKEN)


def _make_replay_authority_property(resolver):
    def replay_authority(value):
        return resolver(value).replay_authority

    return property(replay_authority)


VerifiedParentV3ScenarioReplayAuthorityV1.replay_authority = (
    _make_replay_authority_property(_resolve_replay_authority_property)
)


class _ParentV3ScenarioReplayAuthorityV1Graph(NamedTuple):
    replay: object
    reverify: object
    require_for_parent: object


def _make_parent_v3_scenario_replay_authority_v1_graph(
    issuance_token: object,
) -> _ParentV3ScenarioReplayAuthorityV1Graph:
    if issuance_token is not _ISSUANCE_TOKEN:
        raise TypeError("Parent-v3 scenario replay graph token mismatch")

    verified_parent_type = VerifiedParentFreezeV3
    parent_manifest_type = ParentFreezeV3Manifest
    parent_requirer = require_current_parent_v3
    parent_payload_builder = _parent_freeze_v3_manifest_payload
    application_type = V3M0SyntheticControlApplicationSpec
    scenario_type = ApplicationScenarioExecutionSpec
    application_payload_builder = synthetic_control_application_spec_payload
    scenario_payload_builder = application_scenario_execution_spec_payload
    application_verifier = verify_synthetic_control_application_spec
    scenario_verifier = verify_application_scenario_execution_spec
    sha_builder = canonical_sha
    body_type = ParentV3ScenarioReplayAuthorityV1
    body_validator = body_type.__post_init__
    wrapper_type = VerifiedParentV3ScenarioReplayAuthorityV1
    view_type = _VerifiedParentV3ScenarioReplayAuthorityV1View
    exact_record_validator = _exact_record
    closure_validator = _source_closure
    closure_payload_builder = _reviewed_path_closure_payload
    sha_validator = _sha256
    git_validator = _git_sha1
    body_payload_impl = _parent_v3_scenario_replay_authority_v1_payload_impl
    schema_version = PARENT_V3_SCENARIO_REPLAY_AUTHORITY_V1_SCHEMA_VERSION
    all_control_ids = APPLICATION_CONTROL_CASE_IDS
    replay_control_ids = _REPLAY_CONTROL_CASE_IDS
    clone = copy.deepcopy
    replace_fn = replace
    type_fn = type
    id_fn = id
    weak_reference = weakref.ref
    object_new = object.__new__
    object_setattr = object.__setattr__
    property_binder = _bind_replay_authority_property
    property_binding_guard = _require_replay_authority_property_binding
    property_binding_token = _PROPERTY_BINDING_TOKEN
    registry: dict[int, tuple[object, object, object, str]] = {}
    lock = threading.RLock()

    def body_payload(body):
        return body_payload_impl(
            body,
            body_type=body_type,
            record_validator=exact_record_validator,
            body_validator=body_validator,
            parent_type=parent_manifest_type,
            parent_payload_builder=parent_payload_builder,
            application_type=application_type,
            application_payload_builder=application_payload_builder,
            scenario_type=scenario_type,
            scenario_payload_builder=scenario_payload_builder,
        )

    def require_parent(parent):
        if type_fn(parent) is not verified_parent_type:
            raise TypeError("scenario replay requires exact live Parent-v3")
        manifest = parent_requirer(parent)
        exact_record_validator(manifest, parent_manifest_type, "parent_freeze_v3")
        parent_payload_builder(manifest)
        sha_validator(manifest.parent_freeze_v3_sha, "parent_freeze_v3_sha")
        git_validator(manifest.preparation_commit_sha, "preparation_commit_sha")
        return clone(manifest)

    def derive(parent, control_case_id):
        if (
            type_fn(control_case_id) is not str
            or control_case_id not in replay_control_ids
        ):
            raise ValueError("scenario replay control_case_id is outside C01-C18,C20")
        manifest = require_parent(parent)
        historical = manifest.reviewed_candidate_v3.historical_parent_v1
        applications = historical.synthetic_control_application_specs
        if type_fn(applications) is not tuple or len(applications) != len(
            all_control_ids
        ):
            raise ValueError("Parent-v3 P blob application registry is not exact")
        if not all(type_fn(item) is application_type for item in applications):
            raise TypeError("Parent-v3 P blob contains a non-exact application")
        if tuple(item.control_case_id for item in applications) != all_control_ids:
            raise ValueError("Parent-v3 P blob application order drifted")
        ordinal = all_control_ids.index(control_case_id) + 1
        application = application_verifier(applications[ordinal - 1])
        if type_fn(application) is not application_type:
            raise TypeError("application verifier returned the wrong exact type")
        scenarios = tuple(
            scenario_verifier(scenario, application.operations)
            for scenario in application.scenario_execution_specs
        )
        if not scenarios or scenarios != application.scenario_execution_specs:
            raise ValueError("verified scenarios drifted from the full application")
        closure = closure_validator(historical.source_closure)
        detached_closure = tuple((path, raw_sha) for path, raw_sha in closure)
        closure_root = sha_builder(closure_payload_builder(detached_closure))
        replay = body_type(
            replay_schema_version=schema_version,
            parent_freeze_v3=clone(manifest),
            preparation_commit_sha=manifest.preparation_commit_sha,
            source_parent_v1_ordinal=ordinal,
            control_case_id=control_case_id,
            application_spec=clone(application),
            scenario_specs=clone(scenarios),
            p_blob_source_closure=detached_closure,
            p_blob_source_closure_sha=closure_root,
            replay_sha="0" * 64,
        )
        replay = replace_fn(replay, replay_sha=sha_builder(body_payload(replay)))
        body_payload(replay)
        return replay

    def authority_seal(body):
        return sha_builder(
            {
                "authority_kind": ("v3m0-parent-v3-scenario-replay-live-identity-v1"),
                "replay_authority": {
                    **body_payload(body),
                    "replay_sha": body.replay_sha,
                },
            }
        )

    def reverify(replay):
        if type_fn(replay) is not wrapper_type:
            raise TypeError("scenario replay consumer requires the exact live wrapper")
        property_binding_guard(replay, reverify)
        with lock:
            current = registry.get(id_fn(replay))
            if current is None or current[0]() is not replay:
                raise ValueError("scenario replay identity is absent from the registry")
            parent = current[1]()
            expected = clone(current[2])
            expected_seal = current[3]
        if parent is None:
            raise ValueError("scenario replay Parent-v3 identity is no longer live")
        try:
            observed = object.__getattribute__(
                replay,
                "_VerifiedParentV3ScenarioReplayAuthorityV1__replay_authority",
            )
            observed_seal = object.__getattribute__(
                replay,
                "_VerifiedParentV3ScenarioReplayAuthorityV1__authority_seal",
            )
            observed_token = object.__getattribute__(
                replay,
                "_VerifiedParentV3ScenarioReplayAuthorityV1__token",
            )
        except AttributeError as exc:
            raise ValueError("scenario replay wrapper is incomplete") from exc
        if observed_token is not issuance_token:
            raise ValueError("scenario replay issuance token drifted")
        exact_record_validator(observed, body_type, "scenario replay live body")
        body_validator(observed)
        if observed_seal != expected_seal or observed_seal != authority_seal(observed):
            raise ValueError("scenario replay authority seal drifted")
        if observed != expected:
            raise ValueError("scenario replay live body drifted")
        rebuilt = derive(parent, observed.control_case_id)
        if rebuilt != expected:
            raise ValueError("scenario replay Parent-v3 P blob drifted")
        if observed.replay_sha != sha_builder(body_payload(observed)):
            raise ValueError("scenario replay self hash drifted")
        return view_type(clone(expected), parent)

    def issue(parent, control_case_id):
        body = derive(parent, control_case_id)
        seal = authority_seal(body)
        wrapper = object_new(wrapper_type)
        object_setattr(
            wrapper,
            "_VerifiedParentV3ScenarioReplayAuthorityV1__replay_authority",
            clone(body),
        )
        object_setattr(
            wrapper,
            "_VerifiedParentV3ScenarioReplayAuthorityV1__authority_seal",
            seal,
        )
        object_setattr(
            wrapper,
            "_VerifiedParentV3ScenarioReplayAuthorityV1__token",
            issuance_token,
        )
        identity = id_fn(wrapper)

        def remove_stale(reference, wrapper_id=identity):
            with lock:
                current = registry.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del registry[wrapper_id]

        wrapper_reference = weak_reference(wrapper, remove_stale)
        parent_reference = weak_reference(parent)
        with lock:
            current = registry.get(identity)
            if current is not None and current[0]() is not None:
                raise RuntimeError("scenario replay identity collision")
            registry[identity] = (
                wrapper_reference,
                parent_reference,
                clone(body),
                seal,
            )
        property_binder(
            wrapper,
            reverify,
            token=property_binding_token,
        )
        reverify(wrapper)
        return wrapper

    def require_for_parent(parent, replay):
        if type_fn(parent) is not verified_parent_type:
            raise TypeError("scenario replay requires exact live Parent-v3")
        view = reverify(replay)
        if view.parent is not parent:
            raise ValueError("scenario replay belongs to another Parent-v3 identity")
        return view

    return _ParentV3ScenarioReplayAuthorityV1Graph(
        issue,
        reverify,
        require_for_parent,
    )


_PRODUCTION_GRAPH = _make_parent_v3_scenario_replay_authority_v1_graph(_ISSUANCE_TOKEN)
replay_parent_v3_scenario_authority_v1 = _PRODUCTION_GRAPH.replay
_reverify_verified_parent_v3_scenario_replay_authority_v1 = _PRODUCTION_GRAPH.reverify
_require_parent_v3_scenario_replay_authority_v1_for_parent = (
    _PRODUCTION_GRAPH.require_for_parent
)


__all__ = (
    "ParentV3ScenarioReplayAuthorityV1",
    "VerifiedParentV3ScenarioReplayAuthorityV1",
    "parent_v3_scenario_replay_authority_v1_payload",
    "replay_parent_v3_scenario_authority_v1",
)
