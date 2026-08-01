"""Mechanically matched ablation construction and qualification."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Optional

from .contracts import BlockStatus, UndefinedReason
from .evidence import canonical_sha
from .factory import (
    NEUTRAL_IDENTITY_ID,
    PRIMITIVE_SCHEMA_VERSION,
    LinearRealspaceFactory,
    Primitive,
    VerifiedFactory,
    _VerifiedFactoryView,
    _reverify_verified_factory,
    _verify_factory_payload,
    _verify_matched_ablated_factory,
    factory_sha,
    primitive_sha,
    runtime_operator_sha,
    verify_factory,
)
from .trace import MechanismKind


ABLATION_MANIFEST_SCHEMA_VERSION = "v3m0.ablation-manifest.v1"
DYNAMICS_REPORT_SCHEMA_VERSION = "v3m0.ablation-dynamics-report.v1"
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_QUALIFIED_OUTCOME_TOKEN = object()


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    text = _text(value, field)
    if _LOWER_SHA.fullmatch(text) is None:
        raise ValueError(
            f"{field} must be a 64-digit lowercase hexadecimal SHA"
        )
    return text


@dataclass(frozen=True)
class AblationReplacement:
    layer_slot_id: str
    mechanism_id: str
    actual_primitive_sha: str
    neutral_identity_id: str
    ablated_primitive_sha: str

    def __post_init__(self) -> None:
        _text(self.layer_slot_id, "layer_slot_id")
        _text(self.mechanism_id, "mechanism_id")
        _sha(self.actual_primitive_sha, "actual_primitive_sha")
        if self.neutral_identity_id != NEUTRAL_IDENTITY_ID:
            raise ValueError("neutral_identity_id is not the frozen registry ID")
        _sha(self.ablated_primitive_sha, "ablated_primitive_sha")


@dataclass(frozen=True)
class AblationManifest:
    manifest_schema_version: str
    construction_trace_sha: str
    actual_factory_sha: str
    ablated_factory_sha: str
    replacements: tuple[AblationReplacement, ...]
    manifest_sha: str

    def __post_init__(self) -> None:
        _text(self.manifest_schema_version, "manifest_schema_version")
        _sha(self.construction_trace_sha, "construction_trace_sha")
        _sha(self.actual_factory_sha, "actual_factory_sha")
        _sha(self.ablated_factory_sha, "ablated_factory_sha")
        if type(self.replacements) is not tuple:
            raise TypeError("replacements must be a tuple")
        if not all(
            isinstance(item, AblationReplacement)
            for item in self.replacements
        ):
            raise TypeError("replacements has the wrong record type")
        slots = tuple(item.layer_slot_id for item in self.replacements)
        if len(set(slots)) != len(slots):
            raise ValueError("replacements contains duplicate layer slots")
        _sha(self.manifest_sha, "manifest_sha")


@dataclass(frozen=True)
class AblationPair:
    actual: VerifiedFactory
    ablated: VerifiedFactory
    manifest: AblationManifest

    def __post_init__(self) -> None:
        if not isinstance(self.actual, VerifiedFactory):
            raise TypeError("actual must be a VerifiedFactory")
        if not isinstance(self.ablated, VerifiedFactory):
            raise TypeError("ablated must be a VerifiedFactory")
        if not isinstance(self.manifest, AblationManifest):
            raise TypeError("manifest must be an AblationManifest")


@dataclass(frozen=True)
class AblationDynamicsReport:
    report_schema_version: str
    factory_sha: str
    state_schema_matches: bool
    reversible: bool
    stable: bool
    certificate_sha: str
    report_sha: str

    def __post_init__(self) -> None:
        _text(self.report_schema_version, "report_schema_version")
        _sha(self.factory_sha, "factory_sha")
        for field in ("state_schema_matches", "reversible", "stable"):
            if type(getattr(self, field)) is not bool:
                raise TypeError(f"{field} must be a bool")
        _sha(self.certificate_sha, "certificate_sha")
        _sha(self.report_sha, "report_sha")


@dataclass(frozen=True)
class AblationConstructionOutcome:
    status: BlockStatus
    pair: Optional[AblationPair]

    def __post_init__(self) -> None:
        if not isinstance(self.status, BlockStatus):
            raise TypeError("status must be a BlockStatus")
        if self.pair is not None and not isinstance(self.pair, AblationPair):
            raise TypeError("pair must be an AblationPair or None")
        if self.status.defined != (self.pair is not None):
            raise ValueError("construction defined iff pair is present")


class VerifiedDynamicsReport:
    """Reserved opaque type; no Task 9 success issuer exists."""

    __slots__ = ()

    def __new__(cls, *args: object, **kwargs: object):
        del cls, args, kwargs
        raise TypeError(
            "VerifiedDynamicsReport is unavailable until Task 10 "
            "verifies a DynamicsCertificate"
        )

    @property
    def report(self) -> AblationDynamicsReport:
        raise ValueError("Task 10 DynamicsCertificate authority is unavailable")

    @property
    def certificate_sha(self) -> str:
        raise ValueError("Task 10 DynamicsCertificate authority is unavailable")


class QualifiedAblationOutcome:
    """Opaque qualification; it is never constructible from caller booleans."""

    __slots__ = (
        "__status",
        "__pair",
        "__dynamics_report",
        "__verified_dynamics_report",
        "__construction_outcome",
        "__token",
        "__seal",
    )
    __status: BlockStatus
    __pair: Optional[AblationPair]
    __dynamics_report: Optional[AblationDynamicsReport]
    __verified_dynamics_report: Optional[VerifiedDynamicsReport]
    __construction_outcome: AblationConstructionOutcome
    __token: object
    __seal: str

    def __init__(
        self,
        token: object,
        construction_outcome: AblationConstructionOutcome,
        status: BlockStatus,
        pair: Optional[AblationPair],
        verified_dynamics_report: Optional[VerifiedDynamicsReport],
    ) -> None:
        if token is not _QUALIFIED_OUTCOME_TOKEN:
            raise TypeError(
                "QualifiedAblationOutcome can only be issued by qualification"
            )
        raw_report = (
            None
            if verified_dynamics_report is None
            else verified_dynamics_report.report
        )
        object.__setattr__(
            self,
            "_QualifiedAblationOutcome__status",
            status,
        )
        object.__setattr__(
            self,
            "_QualifiedAblationOutcome__pair",
            pair,
        )
        object.__setattr__(
            self,
            "_QualifiedAblationOutcome__dynamics_report",
            raw_report,
        )
        object.__setattr__(
            self,
            "_QualifiedAblationOutcome__verified_dynamics_report",
            verified_dynamics_report,
        )
        object.__setattr__(
            self,
            "_QualifiedAblationOutcome__construction_outcome",
            construction_outcome,
        )
        object.__setattr__(
            self,
            "_QualifiedAblationOutcome__token",
            token,
        )
        object.__setattr__(
            self,
            "_QualifiedAblationOutcome__seal",
            _qualified_outcome_seal(
                construction_outcome,
                status,
                pair,
                verified_dynamics_report,
                raw_report,
            ),
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("QualifiedAblationOutcome is immutable")

    @property
    def status(self) -> BlockStatus:
        return self.__status

    @property
    def pair(self) -> Optional[AblationPair]:
        return self.__pair

    @property
    def dynamics_report(self) -> Optional[VerifiedDynamicsReport]:
        return self.__verified_dynamics_report

    @property
    def qualification_sha(self) -> str:
        """Stable evidence identity over the qualification body."""

        return self.__seal

    @property
    def certificate_sha(self) -> Optional[str]:
        if self.__verified_dynamics_report is None:
            return None
        return self.__verified_dynamics_report.certificate_sha


def _replacement_payload(
    replacement: AblationReplacement,
) -> dict[str, object]:
    if not isinstance(replacement, AblationReplacement):
        raise TypeError("replacement must be an AblationReplacement")
    return {
        "layer_slot_id": replacement.layer_slot_id,
        "mechanism_id": replacement.mechanism_id,
        "actual_primitive_sha": replacement.actual_primitive_sha,
        "neutral_identity_id": replacement.neutral_identity_id,
        "ablated_primitive_sha": replacement.ablated_primitive_sha,
    }


def ablation_manifest_payload(
    manifest: AblationManifest,
) -> dict[str, object]:
    if not isinstance(manifest, AblationManifest):
        raise TypeError("manifest must be an AblationManifest")
    return {
        "manifest_schema_version": manifest.manifest_schema_version,
        "construction_trace_sha": manifest.construction_trace_sha,
        "actual_factory_sha": manifest.actual_factory_sha,
        "ablated_factory_sha": manifest.ablated_factory_sha,
        "replacements": [
            _replacement_payload(item) for item in manifest.replacements
        ],
    }


def dynamics_report_payload(
    report: AblationDynamicsReport,
) -> dict[str, object]:
    if not isinstance(report, AblationDynamicsReport):
        raise TypeError("report must be an AblationDynamicsReport")
    return {
        "report_schema_version": report.report_schema_version,
        "factory_sha": report.factory_sha,
        "state_schema_matches": report.state_schema_matches,
        "reversible": report.reversible,
        "stable": report.stable,
        "certificate_sha": report.certificate_sha,
    }


def build_dynamics_report(
    *,
    factory_sha_value: str,
    state_schema_matches: bool,
    reversible: bool,
    stable: bool,
    certificate_sha: str,
) -> AblationDynamicsReport:
    provisional = AblationDynamicsReport(
        report_schema_version=DYNAMICS_REPORT_SCHEMA_VERSION,
        factory_sha=factory_sha_value,
        state_schema_matches=state_schema_matches,
        reversible=reversible,
        stable=stable,
        certificate_sha=certificate_sha,
        report_sha="0" * 64,
    )
    return replace(
        provisional,
        report_sha=canonical_sha(dynamics_report_payload(provisional)),
    )


def _status_payload(status: BlockStatus) -> dict[str, object]:
    if not isinstance(status, BlockStatus):
        raise TypeError("status must be a BlockStatus")
    return {
        "defined": status.defined,
        "reason": None if status.reason is None else status.reason.value,
    }


def verify_verified_dynamics_report(
    verified: VerifiedDynamicsReport,
) -> VerifiedDynamicsReport:
    """Fail closed until Task 10 installs a mechanical certificate issuer."""

    if not isinstance(verified, VerifiedDynamicsReport):
        raise TypeError("verified report must be a VerifiedDynamicsReport")
    raise ValueError(
        "VerifiedDynamicsReport is unavailable until Task 10 verifies "
        "a DynamicsCertificate"
    )


def _pair_seal_record(pair: Optional[AblationPair]) -> Optional[dict[str, object]]:
    if pair is None:
        return None
    actual = _reverify_verified_factory(pair.actual)
    ablated = _reverify_verified_factory(pair.ablated)
    return {
        "actual_factory_sha": actual.factory.factory_sha,
        "ablated_factory_sha": ablated.factory.factory_sha,
        "manifest": {
            **ablation_manifest_payload(pair.manifest),
            "manifest_sha": pair.manifest.manifest_sha,
        },
    }


def _verified_dynamics_seal_record(
    verified_dynamics_report: Optional[VerifiedDynamicsReport],
    raw_report: Optional[AblationDynamicsReport],
) -> Optional[dict[str, object]]:
    if verified_dynamics_report is None and raw_report is None:
        return None
    if verified_dynamics_report is None or raw_report is None:
        raise ValueError("verified dynamics authority and report must be paired")
    verified = verify_verified_dynamics_report(verified_dynamics_report)
    authoritative_report = verified.report
    if raw_report != authoritative_report:
        raise ValueError("verified dynamics authority report mismatch")
    if raw_report.report_sha != canonical_sha(
        dynamics_report_payload(raw_report)
    ):
        raise ValueError("verified dynamics report SHA mismatch")
    if verified.certificate_sha != raw_report.certificate_sha:
        raise ValueError("verified dynamics certificate SHA mismatch")
    return {
        "report": {
            **dynamics_report_payload(raw_report),
            "report_sha": raw_report.report_sha,
        },
        "certificate_sha": verified.certificate_sha,
    }


def _qualified_outcome_seal(
    construction_outcome: AblationConstructionOutcome,
    status: BlockStatus,
    pair: Optional[AblationPair],
    verified_dynamics_report: Optional[VerifiedDynamicsReport],
    raw_report: Optional[AblationDynamicsReport],
) -> str:
    verified_dynamics = _verified_dynamics_seal_record(
        verified_dynamics_report,
        raw_report,
    )
    return canonical_sha(
        {
            "qualified_schema_version": "v3m0.qualified-ablation.v2",
            "construction": {
                "status": _status_payload(construction_outcome.status),
                "pair": _pair_seal_record(construction_outcome.pair),
            },
            "status": _status_payload(status),
            "pair": _pair_seal_record(pair),
            "verified_dynamics": verified_dynamics,
        }
    )


def _issue_qualified_outcome(
    construction_outcome: AblationConstructionOutcome,
    status: BlockStatus,
    pair: Optional[AblationPair],
    verified_dynamics_report: Optional[VerifiedDynamicsReport],
) -> QualifiedAblationOutcome:
    return QualifiedAblationOutcome(
        _QUALIFIED_OUTCOME_TOKEN,
        construction_outcome,
        status,
        pair,
        verified_dynamics_report,
    )


def _neutral_for(
    primitive: Primitive,
    spatial_ndim: int,
) -> Primitive:
    """Closed neutral registry: there is deliberately no registration API."""

    zero = (0,) * spatial_ndim
    return Primitive(
        primitive_schema_version=PRIMITIVE_SCHEMA_VERSION,
        mechanism_id=primitive.mechanism_id,
        production_id=primitive.production_id,
        layer_slot_id=primitive.layer_slot_id,
        operation_id="neutral_identity",
        interface_id=primitive.interface_id,
        source_channel=primitive.source_channel,
        destination_channel=primitive.destination_channel,
        offset=zero,
        support_offsets=(zero,),
        coefficient_wire=(0.0, 0.0),
        coefficient_digest=primitive.coefficient_digest,
        neutral_identity_id=NEUTRAL_IDENTITY_ID,
    )


def _same_metadata(
    actual: LinearRealspaceFactory,
    ablated: LinearRealspaceFactory,
) -> Optional[str]:
    for field in (
        "construction_trace_sha",
        "grammar_id",
        "target_spec_id",
        "target_spec_sha",
        "interface",
        "state_schema_id",
        "spatial_ndim",
        "channel_order",
        "state_shape",
        "dtype",
        "backend",
        "dt",
        "target_blind_parameters",
        "layer_slot_ids",
        "source_manifest_id",
        "readout_basis",
        "boundary_manifest_id",
        "run_length",
    ):
        if getattr(actual, field) != getattr(ablated, field):
            return field
    return None


def _reconstruct_pair_body(
    snapshot: _VerifiedFactoryView,
) -> tuple[LinearRealspaceFactory, AblationManifest]:
    """Replay the closed ablation body without issuing runtime capabilities."""

    if type(snapshot) is not _VerifiedFactoryView:
        raise TypeError("pair reconstruction requires a verified actual snapshot")
    if snapshot.role != "actual":
        raise ValueError("pair reconstruction requires an actual factory")
    trace = snapshot.trace
    target = snapshot.target
    primitives = []
    replacements = []
    for primitive, traced in zip(
        snapshot.factory.primitives,
        trace.primitives,
    ):
        if traced.kind is MechanismKind.TARGET_CONDITIONED:
            neutral = _neutral_for(
                primitive,
                snapshot.factory.spatial_ndim,
            )
            primitives.append(neutral)
            replacements.append(
                AblationReplacement(
                    layer_slot_id=primitive.layer_slot_id,
                    mechanism_id=primitive.mechanism_id,
                    actual_primitive_sha=primitive_sha(primitive),
                    neutral_identity_id=NEUTRAL_IDENTITY_ID,
                    ablated_primitive_sha=primitive_sha(neutral),
                )
            )
        else:
            primitives.append(primitive)
    primitive_tuple = tuple(primitives)
    provisional = replace(
        snapshot.factory,
        factory_role="matched_ablated",
        factory_id=snapshot.factory.factory_id + "::matched-ablated",
        runtime_operator_sha=runtime_operator_sha(primitive_tuple),
        primitives=primitive_tuple,
        factory_sha="0" * 64,
    )
    ablated_payload = replace(
        provisional,
        factory_sha=factory_sha(provisional),
    )
    _verify_factory_payload(
        ablated_payload,
        trace,
        target,
        expected_role="matched_ablated",
    )
    provisional_manifest = AblationManifest(
        manifest_schema_version=ABLATION_MANIFEST_SCHEMA_VERSION,
        construction_trace_sha=trace.trace_sha,
        actual_factory_sha=snapshot.factory.factory_sha,
        ablated_factory_sha=ablated_payload.factory_sha,
        replacements=tuple(replacements),
        manifest_sha="0" * 64,
    )
    manifest = replace(
        provisional_manifest,
        manifest_sha=canonical_sha(
            ablation_manifest_payload(provisional_manifest)
        ),
    )
    return ablated_payload, manifest


def _construct_pair(
    actual: VerifiedFactory,
    verified_actual: Optional[_VerifiedFactoryView] = None,
) -> AblationPair:
    snapshot = (
        _reverify_verified_factory(actual)
        if verified_actual is None
        else verified_actual
    )
    ablated_payload, manifest = _reconstruct_pair_body(snapshot)
    pair_actual = verify_factory(
        snapshot.factory,
        snapshot.trace,
        snapshot.target,
    )
    verified_ablated = _verify_matched_ablated_factory(
        ablated_payload,
        snapshot.trace,
        snapshot.target,
    )
    return AblationPair(
        actual=pair_actual,
        ablated=verified_ablated,
        manifest=manifest,
    )


def matched_ablation(
    factory: VerifiedFactory,
) -> AblationConstructionOutcome:
    """Construct the unique matched neutral replacement from an actual factory."""

    try:
        verified = _reverify_verified_factory(factory)
    except (TypeError, ValueError):
        return AblationConstructionOutcome(
            BlockStatus(False, UndefinedReason.MANIFEST_MISMATCH),
            None,
        )
    if verified.role != "actual":
        return AblationConstructionOutcome(
            BlockStatus(False, UndefinedReason.MANIFEST_MISMATCH),
            None,
        )
    trace = verified.trace
    if any(
        item.kind is MechanismKind.UNCLASSIFIED for item in trace.primitives
    ):
        return AblationConstructionOutcome(
            BlockStatus(False, UndefinedReason.TRACE_UNCLASSIFIED),
            None,
        )
    conditioned = tuple(
        item
        for item in trace.primitives
        if item.kind is MechanismKind.TARGET_CONDITIONED
    )
    if any(
        item.neutral_ablation != NEUTRAL_IDENTITY_ID
        for item in conditioned
    ):
        return AblationConstructionOutcome(
            BlockStatus(False, UndefinedReason.ABLATION_NOT_REVERSIBLE),
            None,
        )
    try:
        pair = _construct_pair(factory, verified)
        verify_ablation_pair(pair)
    except (TypeError, ValueError):
        return AblationConstructionOutcome(
            BlockStatus(False, UndefinedReason.STATE_SCHEMA_MISMATCH),
            None,
        )
    return AblationConstructionOutcome(BlockStatus(True, None), pair)


def verify_ablation_pair(pair: AblationPair) -> AblationPair:
    """Replay the closed replacement algorithm and the recursive manifest SHA."""

    if not isinstance(pair, AblationPair):
        raise TypeError("pair must be an AblationPair")
    actual = _reverify_verified_factory(pair.actual)
    ablated = _reverify_verified_factory(pair.ablated)
    if actual.role != "actual":
        raise ValueError("actual role mismatch")
    if ablated.role != "matched_ablated":
        raise ValueError("ablated role mismatch")
    actual_trace = actual.trace
    actual_target = actual.target
    ablated_trace = ablated.trace
    ablated_target = ablated.target
    if actual_trace != ablated_trace:
        raise ValueError("construction trace binding mismatch")
    if actual_target != ablated_target:
        raise ValueError("target binding mismatch")
    mismatch = _same_metadata(actual.factory, ablated.factory)
    if mismatch is not None:
        raise ValueError(f"{mismatch} mismatch")
    expected_ablated, expected_manifest = _reconstruct_pair_body(actual)
    if ablated.factory != expected_ablated:
        raise ValueError("ablated factory is not the unique matched construction")
    manifest = pair.manifest
    if manifest.manifest_schema_version != ABLATION_MANIFEST_SCHEMA_VERSION:
        raise ValueError("manifest_schema_version mismatch")
    if manifest.construction_trace_sha != actual_trace.trace_sha:
        raise ValueError("manifest construction_trace_sha mismatch")
    if manifest.actual_factory_sha != actual.factory.factory_sha:
        raise ValueError("manifest actual_factory_sha mismatch")
    if manifest.ablated_factory_sha != ablated.factory.factory_sha:
        raise ValueError("manifest ablated_factory_sha mismatch")
    if manifest.replacements != expected_manifest.replacements:
        raise ValueError("manifest replacements mismatch")
    if manifest.manifest_sha != canonical_sha(
        ablation_manifest_payload(manifest)
    ):
        raise ValueError("manifest_sha does not match complete manifest body")
    return pair


def _verify_construction_outcome(
    outcome: AblationConstructionOutcome,
) -> AblationConstructionOutcome:
    if not isinstance(outcome, AblationConstructionOutcome):
        raise TypeError("outcome must be an AblationConstructionOutcome")
    if not outcome.status.defined:
        if outcome.pair is not None:
            raise ValueError("undefined construction cannot contain a pair")
        if outcome.status.reason not in (
            UndefinedReason.MANIFEST_MISMATCH,
            UndefinedReason.TRACE_UNCLASSIFIED,
            UndefinedReason.ABLATION_NOT_REVERSIBLE,
            UndefinedReason.STATE_SCHEMA_MISMATCH,
        ):
            raise ValueError("construction has an invalid undefined reason")
        return outcome
    if outcome.pair is None:
        raise ValueError("defined construction outcome lost its pair")
    verify_ablation_pair(outcome.pair)
    return outcome


def qualify_ablation(
    outcome: AblationConstructionOutcome,
    dynamics_report: Optional[VerifiedDynamicsReport],
) -> QualifiedAblationOutcome:
    """Qualify only a Task-10-authorized dynamics report, never caller booleans."""

    verified_construction = _verify_construction_outcome(outcome)
    if not verified_construction.status.defined:
        if dynamics_report is not None:
            raise ValueError(
                "failed construction cannot carry a dynamics authority"
            )
        return _issue_qualified_outcome(
            verified_construction,
            verified_construction.status,
            None,
            None,
        )
    if verified_construction.pair is None:
        raise AssertionError("construction verification lost its pair")
    del dynamics_report
    raise TypeError(
        "successful qualification is unavailable until Task 10 verifies "
        "a full-state DynamicsCertificate"
    )


def verify_qualified_ablation(
    outcome: QualifiedAblationOutcome,
) -> QualifiedAblationOutcome:
    """Replay all authority, pair, report, binding, and status invariants."""

    if not isinstance(outcome, QualifiedAblationOutcome):
        raise TypeError("outcome must be a QualifiedAblationOutcome")
    try:
        token = object.__getattribute__(
            outcome,
            "_QualifiedAblationOutcome__token",
        )
        seal = object.__getattribute__(
            outcome,
            "_QualifiedAblationOutcome__seal",
        )
        status = object.__getattribute__(
            outcome,
            "_QualifiedAblationOutcome__status",
        )
        pair = object.__getattribute__(
            outcome,
            "_QualifiedAblationOutcome__pair",
        )
        raw_report = object.__getattribute__(
            outcome,
            "_QualifiedAblationOutcome__dynamics_report",
        )
        verified_report = object.__getattribute__(
            outcome,
            "_QualifiedAblationOutcome__verified_dynamics_report",
        )
        construction = object.__getattribute__(
            outcome,
            "_QualifiedAblationOutcome__construction_outcome",
        )
    except AttributeError as exc:
        raise ValueError(
            "QualifiedAblationOutcome authority record is incomplete"
        ) from exc
    if token is not _QUALIFIED_OUTCOME_TOKEN:
        raise ValueError("QualifiedAblationOutcome authority token mismatch")
    try:
        expected_seal = _qualified_outcome_seal(
            construction,
            status,
            pair,
            verified_report,
            raw_report,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(
            "QualifiedAblationOutcome sealed body is malformed"
        ) from exc
    if seal != expected_seal:
        raise ValueError("QualifiedAblationOutcome immutable seal mismatch")
    if not isinstance(status, BlockStatus):
        raise ValueError("qualified status type mismatch")
    verified_construction = _verify_construction_outcome(construction)
    if not verified_construction.status.defined:
        if status != verified_construction.status:
            raise ValueError("qualified status does not propagate construction")
        if pair is not None or raw_report is not None or verified_report is not None:
            raise ValueError(
                "failed construction must have no pair or dynamics report"
            )
        return outcome

    raise ValueError(
        "defined qualification is unavailable until Task 10 verifies "
        "a full-state DynamicsCertificate"
    )


__all__ = [
    "ABLATION_MANIFEST_SCHEMA_VERSION",
    "DYNAMICS_REPORT_SCHEMA_VERSION",
    "AblationConstructionOutcome",
    "AblationDynamicsReport",
    "AblationManifest",
    "AblationPair",
    "AblationReplacement",
    "QualifiedAblationOutcome",
    "VerifiedDynamicsReport",
    "ablation_manifest_payload",
    "build_dynamics_report",
    "dynamics_report_payload",
    "matched_ablation",
    "qualify_ablation",
    "verify_ablation_pair",
    "verify_qualified_ablation",
    "verify_verified_dynamics_report",
]
