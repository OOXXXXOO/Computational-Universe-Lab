"""Fail-closed V3-M0 control assembly.

This module is deliberately an assembler, not an authority issuer.  It may
consume live opaque capabilities issued by Tasks 11--14, but it cannot mint,
hydrate, or repair a threshold, application permit, or response block.

The current upstream surface does not yet expose the typed expected-
termination capabilities for C11/C13/C14.  Those slots therefore remain
explicit lane failures.  C20 is consumed only through its independent live
deterministic-series authority.  In particular, this module never converts an
expected internal termination or analysis control into a successful downstream
``VerifiedResponseBlock``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Optional

from rulespace_v3.blocks import VerifiedResponseBlock
from rulespace_v3.calibration_authority import (
    VerifiedResponseBlockAttemptOutcome,
    VerifiedCalibrationApplicationPermit,
    VerifiedWindowThresholdCalibration,
    reverify_verified_response_block_attempt_outcome,
)
from rulespace_v3.causal import VerifiedSurvivalThresholdCalibration
from rulespace_v3.contracts import (
    BlockStatus,
    RequiredBlockReport,
    UndefinedReason,
    evaluate_required_blocks,
)
from rulespace_v3.evidence import (
    EvidenceEnvelope,
    FINAL_RESULT_EVIDENCE_FIELDS,
)
from rulespace_v3.geometry import (
    VerifiedGeometryCoverageThresholdCalibration,
)
from rulespace_v3.parent_freeze import VerifiedParentFreeze
from rulespace_v3.series_control import (
    VerifiedDeterministicSeriesControlOutcome,
    verify_verified_deterministic_series_control_outcome,
)
from rulespace_v3.state import V3M0StateDecision, resolve_v3m0_state


V3M0_CONTROL_ASSEMBLY_SCHEMA_VERSION = "v3m0.control-assembly.v1"

CONTROL_IDS = (
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

REPRESENTATION_INVARIANT_IDS = (
    "I01_LAYER_SPLIT_MERGE",
    "I02_INSERT_S_SINV",
    "I03_COMMUTING_LAYER_REORDER",
    "I04_Q_LABEL_PERMUTATION",
    "I05_SOURCE_ISOMETRY",
    "I06_READOUT_ISOMETRY",
    "I07_PHASE_NONZERO_SCALAR",
    "I08_COVARIANT_CANONICAL_CHANGE",
    "I09_NO_WRAP_VOLUME_CHANGE",
)

SELECTED_CONTROL_IDS = CONTROL_IDS[:3]
APPLICATION_CONTROL_IDS = CONTROL_IDS[3:]
APPLICATION_PERMIT_CONTROL_IDS = CONTROL_IDS[3:19]
EXPECTED_TYPED_TERMINATION_CONTROL_IDS = (
    "C11_NULL_GREY_SIGNAL_AMPLITUDE",
    "C13_BOTH_ZERO_UNDEFINED",
    "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL",
)
ANALYSIS_CONTROL_IDS = ("C20_DM26_CLEAN_ZERO_TRUE_FLOOR",)
EXPECTED_TERMINATION_STAGES = (
    "activation",
    "trace",
    "stability",
    "endpoint_shell",
    "success",
)
EXPECTED_TYPED_TERMINATION_MANIFEST = (
    (
        "C11_NULL_GREY_SIGNAL_AMPLITUDE",
        (
            ("null", "activation", UndefinedReason.RESPONSE_NULL),
            ("grey", "activation", UndefinedReason.RESPONSE_GREY),
        ),
    ),
    (
        "C13_BOTH_ZERO_UNDEFINED",
        (
            ("both-zero", "activation", UndefinedReason.RESPONSE_NULL),
        ),
    ),
    (
        "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL",
        (
            (
                "endpoint-ambiguous",
                "endpoint_shell",
                UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS,
            ),
            ("response-null", "activation", UndefinedReason.RESPONSE_NULL),
            (
                "trace-unclassified",
                "trace",
                UndefinedReason.TRACE_UNCLASSIFIED,
            ),
            ("unstable", "stability", UndefinedReason.UNSTABLE),
        ),
    ),
)
_EXPECTED_TERMINATIONS_BY_ID = dict(EXPECTED_TYPED_TERMINATION_MANIFEST)


def _nonempty_text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


@dataclass(frozen=True)
class V3M0ScenarioLaneContract:
    """Task-17 view of one ParentFreeze scenario and its terminal lane."""

    control_id: str
    scenario_id: str
    scenario_slug: str
    execution_lane: str
    expected_terminal_stage: Optional[str]
    expected_undefined_reason: Optional[UndefinedReason]
    expected_artifact_type: str

    def __post_init__(self) -> None:
        if self.control_id not in CONTROL_IDS:
            raise ValueError("scenario contract has an unknown control ID")
        _nonempty_text(self.scenario_id, "scenario_id")
        _nonempty_text(self.scenario_slug, "scenario_slug")
        if self.execution_lane not in (
            "BLOCK_SUCCESS",
            "EXPECTED_TYPED_TERMINATION",
            "ANALYSIS_CONTROL",
        ):
            raise ValueError("scenario contract has an unknown execution lane")
        if (
            self.expected_terminal_stage is not None
            and self.expected_terminal_stage not in EXPECTED_TERMINATION_STAGES
        ):
            raise ValueError("scenario contract has an unknown terminal stage")
        if (
            self.expected_undefined_reason is not None
            and type(self.expected_undefined_reason) is not UndefinedReason
        ):
            raise TypeError("scenario reason must be an exact UndefinedReason")
        expected_artifact = {
            "BLOCK_SUCCESS": "VerifiedResponseBlock",
            "EXPECTED_TYPED_TERMINATION": (
                "VerifiedResponseBlockAttemptOutcome"
            ),
            "ANALYSIS_CONTROL": (
                "VerifiedDeterministicSeriesControlOutcome"
            ),
        }[self.execution_lane]
        if self.expected_artifact_type != expected_artifact:
            raise ValueError("scenario artifact type differs from its lane")
        if self.execution_lane == "BLOCK_SUCCESS":
            if (
                self.expected_terminal_stage != "success"
                or self.expected_undefined_reason is not None
            ):
                raise ValueError("BLOCK_SUCCESS must terminate at success")
        elif self.execution_lane == "EXPECTED_TYPED_TERMINATION":
            if (
                self.expected_terminal_stage in (None, "success")
                or self.expected_undefined_reason is None
            ):
                raise ValueError("typed termination needs an exact failure")
        elif (
            self.expected_terminal_stage is not None
            or self.expected_undefined_reason is not None
        ):
            raise ValueError("analysis controls do not claim a terminal stage")


def _scenario_contract(
    control_id: str,
    slug: str,
    lane: str,
    stage: Optional[str] = None,
    reason: Optional[UndefinedReason] = None,
) -> V3M0ScenarioLaneContract:
    ordinal = CONTROL_IDS.index(control_id) + 1
    return V3M0ScenarioLaneContract(
        control_id=control_id,
        scenario_id=(
            f"v3m0.synthetic-control.c{ordinal:02d}.v1."
            f"scenario.{slug}.v1"
        ),
        scenario_slug=slug,
        execution_lane=lane,
        expected_terminal_stage=stage,
        expected_undefined_reason=reason,
        expected_artifact_type={
            "BLOCK_SUCCESS": "VerifiedResponseBlock",
            "EXPECTED_TYPED_TERMINATION": (
                "VerifiedResponseBlockAttemptOutcome"
            ),
            "ANALYSIS_CONTROL": (
                "VerifiedDeterministicSeriesControlOutcome"
            ),
        }[lane],
    )


def _success(control_id: str, slug: str) -> V3M0ScenarioLaneContract:
    return _scenario_contract(control_id, slug, "BLOCK_SUCCESS", "success")


def _termination(
    control_id: str,
    slug: str,
    stage: str,
    reason: UndefinedReason,
) -> V3M0ScenarioLaneContract:
    return _scenario_contract(
        control_id,
        slug,
        "EXPECTED_TYPED_TERMINATION",
        stage,
        reason,
    )


def _analysis(control_id: str, slug: str) -> V3M0ScenarioLaneContract:
    return _scenario_contract(control_id, slug, "ANALYSIS_CONTROL")


# This is an independent Task-17 freeze of the exact ParentFreeze order.  A
# live parent must match it recursively before any scenario capability counts.
SCENARIO_LANE_MANIFEST = (
    _success(CONTROL_IDS[0], "holdout-span"),
    _success(CONTROL_IDS[1], "conditioned-zero"),
    _success(CONTROL_IDS[2], "equal-rank-direct-sum"),
    _success(CONTROL_IDS[3], "canonical-angle"),
    _success(CONTROL_IDS[4], "phase"),
    _success(CONTROL_IDS[4], "gain"),
    _success(CONTROL_IDS[5], "nonscale-mixing"),
    _success(CONTROL_IDS[6], "interference"),
    _success(CONTROL_IDS[7], "rank-missing"),
    _success(CONTROL_IDS[8], "gauge-dressing"),
    _success(CONTROL_IDS[9], "extra-mode"),
    _termination(
        CONTROL_IDS[10],
        "null",
        "activation",
        UndefinedReason.RESPONSE_NULL,
    ),
    _termination(
        CONTROL_IDS[10],
        "grey",
        "activation",
        UndefinedReason.RESPONSE_GREY,
    ),
    _success(CONTROL_IDS[10], "signal"),
    _success(CONTROL_IDS[11], "ir-normalization"),
    _termination(
        CONTROL_IDS[12],
        "both-zero",
        "activation",
        UndefinedReason.RESPONSE_NULL,
    ),
    _termination(
        CONTROL_IDS[13],
        "endpoint-ambiguous",
        "endpoint_shell",
        UndefinedReason.ENDPOINT_SHELL_AMBIGUOUS,
    ),
    _termination(
        CONTROL_IDS[13],
        "response-null",
        "activation",
        UndefinedReason.RESPONSE_NULL,
    ),
    _termination(
        CONTROL_IDS[13],
        "trace-unclassified",
        "trace",
        UndefinedReason.TRACE_UNCLASSIFIED,
    ),
    _termination(
        CONTROL_IDS[13],
        "unstable",
        "stability",
        UndefinedReason.UNSTABLE,
    ),
    _success(CONTROL_IDS[14], "full-h"),
    _success(CONTROL_IDS[14], "low-rank-tt"),
    _success(CONTROL_IDS[14], "tt"),
    _success(CONTROL_IDS[14], "tt-plus-row"),
    _success(CONTROL_IDS[15], "coverage-low"),
    _success(CONTROL_IDS[15], "coverage-high"),
    _success(CONTROL_IDS[16], "quotient-gauge"),
    _success(CONTROL_IDS[17], "independent-unary"),
    _success(CONTROL_IDS[18], "observer-collapse"),
    _analysis(CONTROL_IDS[19], "clean-zero"),
    _analysis(CONTROL_IDS[19], "true-floor"),
)
SCENARIO_IDS = tuple(contract.scenario_id for contract in SCENARIO_LANE_MANIFEST)
BLOCK_SUCCESS_SCENARIO_IDS = tuple(
    contract.scenario_id
    for contract in SCENARIO_LANE_MANIFEST
    if contract.execution_lane == "BLOCK_SUCCESS"
)
EXPECTED_TYPED_TERMINATION_SCENARIO_IDS = tuple(
    contract.scenario_id
    for contract in SCENARIO_LANE_MANIFEST
    if contract.execution_lane == "EXPECTED_TYPED_TERMINATION"
)
ANALYSIS_CONTROL_SCENARIO_IDS = tuple(
    contract.scenario_id
    for contract in SCENARIO_LANE_MANIFEST
    if contract.execution_lane == "ANALYSIS_CONTROL"
)
SELECTED_BLOCK_SUCCESS_SCENARIO_IDS = BLOCK_SUCCESS_SCENARIO_IDS[:3]
APPLICATION_SCENARIO_IDS = tuple(
    contract.scenario_id
    for contract in SCENARIO_LANE_MANIFEST
    if contract.control_id in APPLICATION_CONTROL_IDS
)
APPLICATION_BLOCK_SUCCESS_SCENARIO_IDS = tuple(
    contract.scenario_id
    for contract in SCENARIO_LANE_MANIFEST
    if (
        contract.control_id in APPLICATION_CONTROL_IDS
        and contract.execution_lane == "BLOCK_SUCCESS"
    )
)
BLOCK_SUCCESS_CONTROL_IDS = tuple(
    control_id
    for control_id in CONTROL_IDS
    if any(
        contract.control_id == control_id
        and contract.execution_lane == "BLOCK_SUCCESS"
        for contract in SCENARIO_LANE_MANIFEST
    )
)
APPLICATION_BLOCK_SUCCESS_CONTROL_IDS = tuple(
    control_id
    for control_id in APPLICATION_CONTROL_IDS
    if control_id in BLOCK_SUCCESS_CONTROL_IDS
)
_SCENARIO_BY_ID = {
    contract.scenario_id: contract for contract in SCENARIO_LANE_MANIFEST
}

_GLOBAL_CAPABILITY_IDS = (
    "window_threshold_calibration",
    "parent_freeze",
    "survival_threshold_calibration",
    "geometry_coverage_threshold_calibration",
    "final_evidence_envelope",
)


def _exact_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{field} must be an exact bool")
    return value


def _status(
    reason: Optional[UndefinedReason] = None,
) -> BlockStatus:
    return BlockStatus(reason is None, reason)


def _validate_named_capability_rows(
    rows: object,
    *,
    field: str,
    allowed_ids: tuple[str, ...],
    width: int,
) -> tuple[tuple[object, ...], ...]:
    if type(rows) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    seen: set[str] = set()
    observed: list[str] = []
    for index, row in enumerate(rows):
        if type(row) is not tuple or len(row) != width:
            raise TypeError(f"{field}[{index}] must be an exact {width}-tuple")
        control_id = row[0]
        if type(control_id) is not str or control_id not in allowed_ids:
            raise ValueError(f"{field}[{index}] has an unknown control ID")
        if control_id in seen:
            raise ValueError(f"{field} contains duplicate control ID {control_id}")
        seen.add(control_id)
        observed.append(control_id)
    expected_subsequence = tuple(
        control_id for control_id in allowed_ids if control_id in seen
    )
    if tuple(observed) != expected_subsequence:
        raise ValueError(f"{field} must preserve frozen control order")
    return rows


@dataclass(frozen=True)
class V3M0CapabilityBundle:
    """Untrusted transport for capability slots.

    Values intentionally have type ``object`` here.  Assembly performs exact
    runtime type and live-seal checks and records a required-block failure for
    every raw substitute or dead/incorrect body.
    """

    window_calibration: object = None
    parent_freeze: object = None
    survival_calibration: object = None
    geometry_calibration: object = None
    selected_blocks: tuple[tuple[str, object, object], ...] = ()
    application_permits: tuple[tuple[str, object], ...] = ()
    application_blocks: tuple[tuple[str, object, object], ...] = ()
    expected_terminations: tuple[tuple[str, object], ...] = ()
    analysis_controls: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        _validate_named_capability_rows(
            self.selected_blocks,
            field="selected_blocks",
            allowed_ids=SELECTED_BLOCK_SUCCESS_SCENARIO_IDS,
            width=3,
        )
        _validate_named_capability_rows(
            self.application_permits,
            field="application_permits",
            allowed_ids=APPLICATION_PERMIT_CONTROL_IDS,
            width=2,
        )
        _validate_named_capability_rows(
            self.application_blocks,
            field="application_blocks",
            allowed_ids=APPLICATION_SCENARIO_IDS,
            width=3,
        )
        _validate_named_capability_rows(
            self.expected_terminations,
            field="expected_terminations",
            allowed_ids=EXPECTED_TYPED_TERMINATION_SCENARIO_IDS,
            width=2,
        )
        _validate_named_capability_rows(
            self.analysis_controls,
            field="analysis_controls",
            allowed_ids=ANALYSIS_CONTROL_SCENARIO_IDS,
            width=2,
        )


@dataclass(frozen=True)
class V3M0AuditResult:
    """One evaluator result retained verbatim by the assembler."""

    audit_id: str
    status: BlockStatus
    passed: bool
    raw_spectra: tuple[tuple[str, tuple[float, ...]], ...]
    margins: tuple[tuple[str, float], ...]
    termination_events: tuple[
        tuple[str, str, Optional[UndefinedReason]],
        ...,
    ] = ()

    def __post_init__(self) -> None:
        _nonempty_text(self.audit_id, "audit_id")
        if type(self.status) is not BlockStatus:
            raise TypeError("status must be an exact BlockStatus")
        _exact_bool(self.passed, "passed")
        if self.passed and not self.status.defined:
            raise ValueError("an undefined audit cannot pass")
        if type(self.raw_spectra) is not tuple:
            raise TypeError("raw_spectra must be a tuple")
        spectrum_ids: set[str] = set()
        for index, row in enumerate(self.raw_spectra):
            if type(row) is not tuple or len(row) != 2:
                raise TypeError(f"raw_spectra[{index}] must be an exact pair")
            spectrum_id, values = row
            _nonempty_text(spectrum_id, f"raw_spectra[{index}].spectrum_id")
            if spectrum_id in spectrum_ids:
                raise ValueError(f"duplicate spectrum ID {spectrum_id}")
            spectrum_ids.add(spectrum_id)
            if type(values) is not tuple:
                raise TypeError(f"raw_spectra[{index}].values must be a tuple")
            for value_index, value in enumerate(values):
                if type(value) is not float:
                    raise TypeError(
                        f"raw_spectra[{index}].values[{value_index}] "
                        "must be a float"
                    )
                if not math.isfinite(value):
                    raise ValueError("raw spectra must contain only finite values")
        if type(self.margins) is not tuple:
            raise TypeError("margins must be a tuple")
        margin_ids: set[str] = set()
        for index, row in enumerate(self.margins):
            if type(row) is not tuple or len(row) != 2:
                raise TypeError(f"margins[{index}] must be an exact pair")
            margin_id, value = row
            _nonempty_text(margin_id, f"margins[{index}].margin_id")
            if margin_id in margin_ids:
                raise ValueError(f"duplicate margin ID {margin_id}")
            margin_ids.add(margin_id)
            if type(value) is not float:
                raise TypeError(f"margins[{index}].value must be a float")
            if not math.isfinite(value):
                raise ValueError("margins must contain only finite values")
        if self.passed and (
            not self.margins
            or any(value <= 0.0 for _, value in self.margins)
        ):
            raise ValueError("a passing audit requires strictly positive margins")
        if type(self.termination_events) is not tuple:
            raise TypeError("termination_events must be a tuple")
        cases: set[str] = set()
        for index, row in enumerate(self.termination_events):
            if type(row) is not tuple or len(row) != 3:
                raise TypeError(
                    f"termination_events[{index}] must be an exact triple"
                )
            case_id, stage, reason = row
            _nonempty_text(case_id, f"termination_events[{index}].case_id")
            _nonempty_text(stage, f"termination_events[{index}].stage")
            if case_id in cases:
                raise ValueError(f"duplicate termination case {case_id}")
            if stage not in EXPECTED_TERMINATION_STAGES:
                raise ValueError(f"unknown termination stage {stage}")
            if reason is not None and type(reason) is not UndefinedReason:
                raise TypeError(
                    "termination reasons must be exact enum values or None"
                )
            if (stage == "success") != (reason is None):
                raise ValueError(
                    "success is the only termination stage without a reason"
                )
            cases.add(case_id)


@dataclass(frozen=True)
class V3M0ControlAssembly:
    schema_version: str
    scenario_manifest: tuple[V3M0ScenarioLaneContract, ...]
    block_success: tuple[V3M0AuditResult, ...]
    expected_typed_termination: tuple[V3M0AuditResult, ...]
    analysis_control: tuple[V3M0AuditResult, ...]
    invariants: tuple[V3M0AuditResult, ...]
    required_blocks: RequiredBlockReport
    lane_failures: tuple[tuple[str, UndefinedReason], ...]
    formal_all_pass: bool
    exact_all_pass: bool
    identifiability_all_pass: bool
    all_block_success_artifacts_verified: bool
    all_required_controls_pass: bool
    all_expected_terminations_verified: bool
    all_analysis_controls_verified: bool
    representation_invariants_pass: bool
    no_unexpected_downstream_capability: bool
    no_physical_anchor_run: bool
    evidence: Optional[EvidenceEnvelope]
    decision: V3M0StateDecision

    def __post_init__(self) -> None:
        if self.schema_version != V3M0_CONTROL_ASSEMBLY_SCHEMA_VERSION:
            raise ValueError("unexpected control assembly schema")
        if self.scenario_manifest != SCENARIO_LANE_MANIFEST:
            raise ValueError("assembly scenario manifest differs from freeze")
        if any(
            type(row) is not V3M0ScenarioLaneContract
            for row in self.scenario_manifest
        ):
            raise TypeError("scenario manifest rows must have exact type")
        expected_orders = (
            (self.block_success, BLOCK_SUCCESS_SCENARIO_IDS),
            (
                self.expected_typed_termination,
                EXPECTED_TYPED_TERMINATION_SCENARIO_IDS,
            ),
            (self.analysis_control, ANALYSIS_CONTROL_SCENARIO_IDS),
            (self.invariants, REPRESENTATION_INVARIANT_IDS),
        )
        for rows, expected_ids in expected_orders:
            if type(rows) is not tuple:
                raise TypeError("assembly audit columns must be tuples")
            if any(type(row) is not V3M0AuditResult for row in rows):
                raise TypeError("assembly audit rows must be exact V3M0AuditResult")
            if tuple(row.audit_id for row in rows) != expected_ids:
                raise ValueError("assembly audit column order differs from freeze")
        if type(self.required_blocks) is not RequiredBlockReport:
            raise TypeError("required_blocks must be an exact RequiredBlockReport")
        if type(self.lane_failures) is not tuple:
            raise TypeError("lane_failures must be a tuple")
        lane_ids: set[str] = set()
        for row in self.lane_failures:
            if type(row) is not tuple or len(row) != 2:
                raise TypeError("lane_failures entries must be exact pairs")
            lane_id, reason = row
            _nonempty_text(lane_id, "lane failure ID")
            if lane_id in lane_ids:
                raise ValueError(f"duplicate lane failure ID {lane_id}")
            if type(reason) is not UndefinedReason:
                raise TypeError("lane failure reason must be exact")
            lane_ids.add(lane_id)
        for field in (
            "formal_all_pass",
            "exact_all_pass",
            "identifiability_all_pass",
            "all_block_success_artifacts_verified",
            "all_required_controls_pass",
            "all_expected_terminations_verified",
            "all_analysis_controls_verified",
            "representation_invariants_pass",
            "no_unexpected_downstream_capability",
            "no_physical_anchor_run",
        ):
            _exact_bool(getattr(self, field), field)
        if self.evidence is not None and type(self.evidence) is not EvidenceEnvelope:
            raise TypeError("evidence must be an exact EvidenceEnvelope or None")
        if type(self.decision) is not V3M0StateDecision:
            raise TypeError("decision must be an exact V3M0StateDecision")

    @property
    def controls(self) -> tuple[V3M0AuditResult, ...]:
        by_id: dict[str, list[V3M0AuditResult]] = {
            control_id: [] for control_id in CONTROL_IDS
        }
        for column in (
            self.block_success,
            self.expected_typed_termination,
            self.analysis_control,
        ):
            for row in column:
                by_id[_SCENARIO_BY_ID[row.audit_id].control_id].append(row)
        aggregate: list[V3M0AuditResult] = []
        for control_id in CONTROL_IDS:
            rows = by_id[control_id]
            if not rows:
                raise AssertionError("control lost every execution lane")
            if len(rows) == 1:
                aggregate.append(replace(rows[0], audit_id=control_id))
                continue
            first_reason = next(
                (
                    row.status.reason
                    for row in rows
                    if not row.status.defined
                ),
                None,
            )
            source = next(
                (row for row in rows if row.raw_spectra or row.margins),
                rows[0],
            )
            events = tuple(
                event
                for row in rows
                for event in row.termination_events
            )
            aggregate.append(
                V3M0AuditResult(
                    audit_id=control_id,
                    status=_status(first_reason),
                    passed=all(row.passed for row in rows),
                    raw_spectra=source.raw_spectra,
                    margins=source.margins,
                    termination_events=events,
                )
            )
        return tuple(aggregate)


def _live_parent(value: object) -> tuple[BlockStatus, object]:
    if value is None:
        return _status(UndefinedReason.PRESTRUCTURE_INVALID), None
    if type(value) is not VerifiedParentFreeze:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        manifest = value.manifest
        observed_ids = tuple(
            spec.control_case_id
            for spec in manifest.synthetic_control_application_specs
        )
        observed_scenarios = tuple(
            (
                application.control_case_id,
                scenario.scenario_id,
                scenario.execution_lane,
                scenario.expected_terminal_stage,
                scenario.expected_undefined_reason,
                scenario.expected_artifact_type,
            )
            for application in manifest.synthetic_control_application_specs
            for scenario in application.scenario_execution_specs
        )
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    expected_scenarios = tuple(
        (
            contract.control_id,
            contract.scenario_id,
            contract.execution_lane,
            contract.expected_terminal_stage,
            contract.expected_undefined_reason,
            contract.expected_artifact_type,
        )
        for contract in SCENARIO_LANE_MANIFEST
    )
    if observed_ids != CONTROL_IDS or observed_scenarios != expected_scenarios:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), manifest


def _live_window(value: object) -> tuple[BlockStatus, object]:
    if value is None:
        return _status(UndefinedReason.WINDOW_UNRESOLVED), None
    if type(value) is not VerifiedWindowThresholdCalibration:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        outcome = value.outcome
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), outcome


def _live_survival(value: object) -> tuple[BlockStatus, object]:
    if value is None:
        return _status(UndefinedReason.PRESTRUCTURE_INVALID), None
    if type(value) is not VerifiedSurvivalThresholdCalibration:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        calibration = value.calibration
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), calibration


def _live_geometry(value: object) -> tuple[BlockStatus, object]:
    if value is None:
        return _status(UndefinedReason.PRESTRUCTURE_INVALID), None
    if type(value) is not VerifiedGeometryCoverageThresholdCalibration:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        calibration = value.calibration
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), calibration


def _live_permit(
    value: object,
    control_id: str,
) -> tuple[BlockStatus, object]:
    if value is None:
        return _status(UndefinedReason.PRESTRUCTURE_INVALID), None
    if type(value) is not VerifiedCalibrationApplicationPermit:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        permit = value.permit
        observed_id = permit.application_spec.control_case_id
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    if observed_id != control_id:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), permit


def _live_block(
    value: object,
    *,
    branch: str,
    window_outcome: object,
    permit: object = None,
) -> tuple[BlockStatus, object]:
    if value is None:
        return _status(UndefinedReason.RESPONSE_BRIDGE_FAILED), None
    if type(value) is not VerifiedResponseBlock:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        block = value.block
        if block.branch != branch:
            raise ValueError("branch mismatch")
        if window_outcome is not None:
            calibration_sha = (
                window_outcome.manifest.calibration_manifest_sha
            )
            if block.calibration_manifest_sha != calibration_sha:
                raise ValueError("window calibration mismatch")
        if permit is not None and (
            block.application_authority_sha != permit.permit_sha
        ):
            raise ValueError("application permit mismatch")
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), block


def _pair_binding_status(
    actual: object,
    ablated: object,
) -> BlockStatus:
    if actual is None or ablated is None:
        return _status(UndefinedReason.RESPONSE_BRIDGE_FAILED)
    try:
        if (
            actual.pair_sha != ablated.pair_sha
            or actual.paired_response_sha != ablated.paired_response_sha
            or actual.calibration_manifest_sha
            != ablated.calibration_manifest_sha
        ):
            raise ValueError("pair mismatch")
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH)
    return _status()


def _evidence_status(value: object) -> tuple[BlockStatus, Optional[EvidenceEnvelope]]:
    if value is None:
        return _status(UndefinedReason.PRESTRUCTURE_INVALID), None
    if type(value) is not EvidenceEnvelope:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        for field in FINAL_RESULT_EVIDENCE_FIELDS:
            getattr(value, field)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), value


def _live_typed_termination(
    value: object,
    *,
    contract: V3M0ScenarioLaneContract,
    parent_manifest: object,
    permit: object,
) -> tuple[BlockStatus, object]:
    """Strictly replay one exact Task-12 expected-termination capability."""

    if value is None:
        return _status(UndefinedReason.PRESTRUCTURE_INVALID), None
    if type(value) is not VerifiedResponseBlockAttemptOutcome:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        outcome = reverify_verified_response_block_attempt_outcome(value)
        scenario = outcome.scenario_spec
        application = outcome.application_spec
        if parent_manifest is None or permit is None:
            raise ValueError("typed termination lacks live parent or permit")
        if outcome.permit != permit:
            raise ValueError("typed termination is bound to another permit")
        if (
            outcome.permit.parent_freeze.parent_freeze_sha
            != parent_manifest.parent_freeze_sha
        ):
            raise ValueError("typed termination is bound to another parent")
        if application != permit.application_spec:
            raise ValueError("typed termination application/permit mismatch")
        if application.control_case_id != contract.control_id:
            raise ValueError("typed termination control ID mismatch")
        if scenario.scenario_id != contract.scenario_id:
            raise ValueError("typed termination scenario ID mismatch")
        if scenario.execution_lane != contract.execution_lane:
            raise ValueError("typed termination lane mismatch")
        if (
            scenario.expected_terminal_stage
            != contract.expected_terminal_stage
            or scenario.expected_undefined_reason
            is not contract.expected_undefined_reason
            or scenario.expected_artifact_type
            != contract.expected_artifact_type
        ):
            raise ValueError("typed termination prophecy mismatch")
        if (
            outcome.terminal_stage != contract.expected_terminal_stage
            or outcome.status.defined
            or outcome.status.reason is not contract.expected_undefined_reason
            or outcome.downstream_capability_issued is not False
        ):
            raise ValueError("typed termination outcome mismatch")
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), outcome


def _live_series_control(
    value: object,
    *,
    contract: V3M0ScenarioLaneContract,
    parent_manifest: object,
) -> tuple[BlockStatus, object]:
    """Strictly replay one opaque C20 capability against the live parent."""

    if value is None:
        return _status(UndefinedReason.PRESTRUCTURE_INVALID), None
    if type(value) is not VerifiedDeterministicSeriesControlOutcome:
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    try:
        outcome = verify_verified_deterministic_series_control_outcome(value)
        scenario = outcome.scenario_spec
        application = outcome.application_spec
        if parent_manifest is None:
            raise ValueError("live ParentFreeze is absent")
        if outcome.parent_freeze_sha != parent_manifest.parent_freeze_sha:
            raise ValueError("C20 authority is bound to another parent")
        if application.control_case_id != contract.control_id:
            raise ValueError("C20 control ID mismatch")
        if scenario.scenario_id != contract.scenario_id:
            raise ValueError("C20 scenario ID mismatch")
        if scenario.execution_lane != contract.execution_lane:
            raise ValueError("C20 execution lane mismatch")
        if scenario.expected_artifact_type != contract.expected_artifact_type:
            raise ValueError("C20 artifact type mismatch")
        if outcome.series_class != contract.scenario_slug:
            raise ValueError("C20 series class/order mismatch")
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return _status(UndefinedReason.MANIFEST_MISMATCH), None
    return _status(), outcome


def _series_audit(
    contract: V3M0ScenarioLaneContract,
    status: BlockStatus,
    outcome: object,
) -> V3M0AuditResult:
    if not status.defined or outcome is None:
        return V3M0AuditResult(
            audit_id=contract.scenario_id,
            status=status,
            passed=False,
            raw_spectra=(),
            margins=(),
        )
    return V3M0AuditResult(
        audit_id=contract.scenario_id,
        status=_status(),
        passed=True,
        raw_spectra=(
            ("k_values", tuple(outcome.k_values)),
            ("raw_samples", tuple(outcome.raw_samples)),
        ),
        margins=(("strict_live_replay", 1.0),),
    )


def _typed_termination_audit(
    contract: V3M0ScenarioLaneContract,
    status: BlockStatus,
    outcome: object,
) -> V3M0AuditResult:
    """Translate one replayed attempt into its exact expected-failure audit."""

    if not status.defined or outcome is None:
        return V3M0AuditResult(
            audit_id=contract.scenario_id,
            status=status,
            passed=False,
            raw_spectra=(),
            margins=(),
        )
    return V3M0AuditResult(
        audit_id=contract.scenario_id,
        status=_status(),
        passed=True,
        raw_spectra=(
            (
                "raw_singular_values",
                tuple(outcome.raw_singular_values),
            ),
        ),
        margins=(("strict_live_replay", 1.0),),
        termination_events=(
            (
                contract.scenario_slug,
                contract.expected_terminal_stage,
                contract.expected_undefined_reason,
            ),
        ),
    )


def _row_map(
    rows: tuple[tuple[object, ...], ...],
) -> dict[str, tuple[object, ...]]:
    return {row[0]: row[1:] for row in rows}  # type: ignore[index]


def _audit_map(
    rows: object,
    *,
    field: str,
    allowed_ids: tuple[str, ...],
) -> dict[str, V3M0AuditResult]:
    if type(rows) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    result: dict[str, V3M0AuditResult] = {}
    observed: list[str] = []
    for index, row in enumerate(rows):
        if type(row) is not V3M0AuditResult:
            raise TypeError(f"{field}[{index}] must be a V3M0AuditResult")
        if row.audit_id not in allowed_ids:
            raise ValueError(f"{field}[{index}] has an unknown audit ID")
        if row.audit_id in result:
            raise ValueError(f"{field} contains duplicate audit ID {row.audit_id}")
        observed.append(row.audit_id)
        result[row.audit_id] = row
    expected_subsequence = tuple(item for item in allowed_ids if item in result)
    if tuple(observed) != expected_subsequence:
        raise ValueError(f"{field} must preserve frozen audit order")
    return result


def _first_failure(statuses: tuple[BlockStatus, ...]) -> Optional[UndefinedReason]:
    for status in statuses:
        if not status.defined:
            if status.reason is None:
                raise AssertionError("undefined status lost its reason")
            return status.reason
    return None


def _effective_audit(
    audit_id: str,
    supplied: Optional[V3M0AuditResult],
    dependency_statuses: tuple[BlockStatus, ...],
    *,
    expected_termination_events: Optional[
        tuple[tuple[str, str, Optional[UndefinedReason]], ...]
    ],
) -> V3M0AuditResult:
    reason = _first_failure(dependency_statuses)
    if supplied is None:
        return V3M0AuditResult(
            audit_id=audit_id,
            status=_status(reason or UndefinedReason.PRESTRUCTURE_INVALID),
            passed=False,
            raw_spectra=(),
            margins=(),
        )
    if reason is not None:
        return replace(
            supplied,
            status=_status(reason),
            passed=False,
        )
    if (
        expected_termination_events is None
        and supplied.termination_events
    ):
        return replace(
            supplied,
            status=_status(UndefinedReason.MANIFEST_MISMATCH),
            passed=False,
        )
    if (
        expected_termination_events is not None
        and supplied.termination_events != expected_termination_events
    ):
        return replace(
            supplied,
            status=_status(UndefinedReason.MANIFEST_MISMATCH),
            passed=False,
        )
    return supplied


def _audit_to_wire(
    row: V3M0AuditResult,
    *,
    id_key: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        id_key: row.audit_id,
        "defined": row.status.defined,
        "passed": row.passed,
        "undefined_reason": (
            None if row.status.reason is None else row.status.reason.value
        ),
        "raw_spectra": [
            {
                "spectrum_id": spectrum_id,
                "values": list(values),
            }
            for spectrum_id, values in row.raw_spectra
        ],
        "margins": [
            {
                "margin_id": margin_id,
                "value": value,
            }
            for margin_id, value in row.margins
        ],
        "termination_events": [
            {
                "case_id": case_id,
                "stage": stage,
                "reason": None if reason is None else reason.value,
            }
            for case_id, stage, reason in row.termination_events
        ],
    }
    if id_key == "scenario_id":
        payload["control_id"] = _SCENARIO_BY_ID[row.audit_id].control_id
    return payload


def assemble_v3m0_controls(
    *,
    formal_all_pass: bool,
    exact_all_pass: bool,
    identifiability_all_pass: bool,
    capabilities: V3M0CapabilityBundle,
    control_results: tuple[V3M0AuditResult, ...],
    invariant_results: tuple[V3M0AuditResult, ...],
    evidence: object,
    no_physical_anchor_run: bool,
) -> V3M0ControlAssembly:
    """Assemble the frozen control matrix without issuing new authority."""

    formal = _exact_bool(formal_all_pass, "formal_all_pass")
    exact = _exact_bool(exact_all_pass, "exact_all_pass")
    identifiable = _exact_bool(
        identifiability_all_pass,
        "identifiability_all_pass",
    )
    scope_clean = _exact_bool(
        no_physical_anchor_run,
        "no_physical_anchor_run",
    )
    if type(capabilities) is not V3M0CapabilityBundle:
        raise TypeError("capabilities must be an exact V3M0CapabilityBundle")
    block_results_by_id = _audit_map(
        control_results,
        field="control_results",
        allowed_ids=BLOCK_SUCCESS_SCENARIO_IDS,
    )
    invariants_by_id = _audit_map(
        invariant_results,
        field="invariant_results",
        allowed_ids=REPRESENTATION_INVARIANT_IDS,
    )

    statuses: dict[str, BlockStatus] = {}
    required_ids: list[str] = []
    lane_failures: list[tuple[str, UndefinedReason]] = []

    def record_required(block_id: str, status: BlockStatus) -> None:
        if block_id in statuses:
            raise AssertionError(f"duplicate internal required block {block_id}")
        statuses[block_id] = status
        required_ids.append(block_id)

    def record_lane_failure(lane_id: str, status: BlockStatus) -> None:
        if status.defined:
            return
        if status.reason is None:
            raise AssertionError("lane failure lost its reason")
        if any(existing_id == lane_id for existing_id, _ in lane_failures):
            raise AssertionError(f"duplicate internal lane failure {lane_id}")
        lane_failures.append((lane_id, status.reason))

    window_status, window_outcome = _live_window(
        capabilities.window_calibration
    )
    parent_status, parent_manifest = _live_parent(
        capabilities.parent_freeze
    )
    survival_status, _ = _live_survival(capabilities.survival_calibration)
    geometry_status, _ = _live_geometry(capabilities.geometry_calibration)
    evidence_status, checked_evidence = _evidence_status(evidence)
    if (
        parent_status.defined
        and evidence_status.defined
        and checked_evidence is not None
        and checked_evidence.parent_v2_sha != parent_manifest.parent_v2_sha
    ):
        evidence_status = _status(UndefinedReason.MANIFEST_MISMATCH)
        checked_evidence = None
    record_required(_GLOBAL_CAPABILITY_IDS[0], window_status)
    record_required(_GLOBAL_CAPABILITY_IDS[1], parent_status)
    record_required(_GLOBAL_CAPABILITY_IDS[2], survival_status)
    record_required(_GLOBAL_CAPABILITY_IDS[3], geometry_status)
    record_required(_GLOBAL_CAPABILITY_IDS[4], evidence_status)
    global_statuses = (
        window_status,
        parent_status,
        survival_status,
        geometry_status,
        evidence_status,
    )

    selected = _row_map(capabilities.selected_blocks)
    permits = _row_map(capabilities.application_permits)
    application_blocks = _row_map(capabilities.application_blocks)
    typed_terminations = _row_map(capabilities.expected_terminations)
    analysis_controls = _row_map(capabilities.analysis_controls)
    block_statuses: dict[str, tuple[BlockStatus, ...]] = {}
    termination_statuses: dict[str, tuple[BlockStatus, ...]] = {}
    termination_outcomes: dict[str, object] = {}
    analysis_statuses: dict[str, tuple[BlockStatus, ...]] = {}
    analysis_outcomes: dict[str, object] = {}
    no_unexpected_downstream = True

    permit_statuses: dict[str, BlockStatus] = {}
    permit_bodies: dict[str, object] = {}
    for control_id in APPLICATION_PERMIT_CONTROL_IDS:
        permit_value = permits.get(control_id, (None,))[0]
        permit_status, permit_body = _live_permit(
            permit_value,
            control_id,
        )
        permit_statuses[control_id] = permit_status
        permit_bodies[control_id] = permit_body

    for contract in SCENARIO_LANE_MANIFEST:
        if (
            contract.control_id not in SELECTED_CONTROL_IDS
            or contract.execution_lane != "BLOCK_SUCCESS"
        ):
            continue
        scenario_id = contract.scenario_id
        actual, ablated = selected.get(scenario_id, (None, None))
        actual_status, actual_body = _live_block(
            actual,
            branch="actual",
            window_outcome=window_outcome,
        )
        ablated_status, ablated_body = _live_block(
            ablated,
            branch="matched_ablated",
            window_outcome=window_outcome,
        )
        pair_status = _pair_binding_status(actual_body, ablated_body)
        record_required(f"{scenario_id}.actual_response_block", actual_status)
        record_required(f"{scenario_id}.ablated_response_block", ablated_status)
        record_required(f"{scenario_id}.response_pair_binding", pair_status)
        block_statuses[scenario_id] = (
            *global_statuses,
            actual_status,
            ablated_status,
            pair_status,
        )

    recorded_required_permits: set[str] = set()
    for contract in SCENARIO_LANE_MANIFEST:
        control_id = contract.control_id
        scenario_id = contract.scenario_id
        if control_id not in APPLICATION_CONTROL_IDS:
            continue

        if contract.execution_lane == "ANALYSIS_CONTROL":
            local_statuses = [parent_status]
            if scenario_id in application_blocks:
                unexpected_status = _status(
                    UndefinedReason.MANIFEST_MISMATCH
                )
                record_lane_failure(
                    f"{scenario_id}.unexpected_downstream_response_block",
                    unexpected_status,
                )
                local_statuses.append(unexpected_status)
                no_unexpected_downstream = False
            analysis_value = analysis_controls.get(
                scenario_id,
                (None,),
            )[0]
            analysis_status, analysis_outcome = _live_series_control(
                analysis_value,
                contract=contract,
                parent_manifest=parent_manifest,
            )
            record_lane_failure(
                f"{scenario_id}.verified_series_evidence",
                analysis_status,
            )
            local_statuses.append(analysis_status)
            analysis_statuses[scenario_id] = tuple(local_statuses)
            analysis_outcomes[scenario_id] = analysis_outcome
            continue

        permit_status = permit_statuses[control_id]
        permit_body = permit_bodies[control_id]
        if contract.execution_lane == "BLOCK_SUCCESS":
            if control_id not in recorded_required_permits:
                record_required(
                    f"{control_id}.application_permit",
                    permit_status,
                )
                recorded_required_permits.add(control_id)
            local_statuses: list[BlockStatus] = [
                *global_statuses,
                permit_status,
            ]
            actual, ablated = application_blocks.get(
                scenario_id,
                (None, None),
            )
            actual_status, actual_body = _live_block(
                actual,
                branch="actual",
                window_outcome=window_outcome,
                permit=permit_body,
            )
            ablated_status, ablated_body = _live_block(
                ablated,
                branch="matched_ablated",
                window_outcome=window_outcome,
                permit=permit_body,
            )
            pair_status = _pair_binding_status(actual_body, ablated_body)
            record_required(
                f"{scenario_id}.actual_response_block",
                actual_status,
            )
            record_required(
                f"{scenario_id}.ablated_response_block",
                ablated_status,
            )
            record_required(
                f"{scenario_id}.response_pair_binding",
                pair_status,
            )
            local_statuses.extend(
                (actual_status, ablated_status, pair_status)
            )
            block_statuses[scenario_id] = tuple(local_statuses)
            continue

        if contract.execution_lane == "EXPECTED_TYPED_TERMINATION":
            typed_statuses: list[BlockStatus] = [
                parent_status,
                window_status,
                evidence_status,
                permit_status,
            ]
            record_lane_failure(
                f"{scenario_id}.application_permit",
                permit_status,
            )
            if scenario_id in application_blocks:
                unexpected_status = _status(
                    UndefinedReason.MANIFEST_MISMATCH
                )
                record_lane_failure(
                    f"{scenario_id}.unexpected_downstream_response_block",
                    unexpected_status,
                )
                typed_statuses.append(unexpected_status)
                no_unexpected_downstream = False
            termination_value = typed_terminations.get(
                scenario_id,
                (None,),
            )[0]
            termination_status, termination_outcome = _live_typed_termination(
                termination_value,
                contract=contract,
                parent_manifest=parent_manifest,
                permit=permit_body,
            )
            record_lane_failure(
                f"{scenario_id}.expected_typed_termination",
                termination_status,
            )
            typed_statuses.append(termination_status)
            termination_statuses[scenario_id] = tuple(typed_statuses)
            termination_outcomes[scenario_id] = termination_outcome
            continue
        raise AssertionError("unclassified application scenario lane")

    block_success = tuple(
        _effective_audit(
            scenario_id,
            block_results_by_id.get(scenario_id),
            block_statuses[scenario_id],
            expected_termination_events=None,
        )
        for scenario_id in BLOCK_SUCCESS_SCENARIO_IDS
    )
    expected_terminations = tuple(
        _typed_termination_audit(
            contract,
            _status(
                _first_failure(
                    termination_statuses[contract.scenario_id]
                )
            ),
            termination_outcomes[contract.scenario_id],
        )
        for contract in SCENARIO_LANE_MANIFEST
        if contract.execution_lane == "EXPECTED_TYPED_TERMINATION"
    )
    analysis = tuple(
        _series_audit(
            contract,
            _status(
                _first_failure(
                    analysis_statuses[contract.scenario_id]
                )
            ),
            analysis_outcomes[contract.scenario_id],
        )
        for contract in SCENARIO_LANE_MANIFEST
        if contract.execution_lane == "ANALYSIS_CONTROL"
    )
    all_capability_statuses = tuple(statuses[block_id] for block_id in required_ids)
    effective_invariants = tuple(
        _effective_audit(
            invariant_id,
            invariants_by_id.get(invariant_id),
            all_capability_statuses,
            expected_termination_events=None,
        )
        for invariant_id in REPRESENTATION_INVARIANT_IDS
    )
    required_report = evaluate_required_blocks(statuses, required_ids)
    all_blocks_pass = all(row.passed for row in block_success)
    all_terminations_pass = all(row.passed for row in expected_terminations)
    all_analysis_pass = all(row.passed for row in analysis)
    all_controls_pass = (
        all_blocks_pass
        and all_terminations_pass
        and all_analysis_pass
    )
    all_invariants_pass = all(row.passed for row in effective_invariants)
    decision = resolve_v3m0_state(
        formal_all_pass=formal,
        exact_all_pass=exact,
        identifiability_all_pass=identifiable,
        required_blocks=required_report,
        all_block_success_artifacts_verified=all_blocks_pass,
        all_required_controls_pass=all_controls_pass,
        representation_invariants_pass=all_invariants_pass,
        all_expected_terminations_verified=all_terminations_pass,
        all_analysis_controls_verified=all_analysis_pass,
        no_unexpected_downstream_capability=no_unexpected_downstream,
        no_physical_anchor_run=scope_clean,
    )
    return V3M0ControlAssembly(
        schema_version=V3M0_CONTROL_ASSEMBLY_SCHEMA_VERSION,
        scenario_manifest=SCENARIO_LANE_MANIFEST,
        block_success=block_success,
        expected_typed_termination=expected_terminations,
        analysis_control=analysis,
        invariants=effective_invariants,
        required_blocks=required_report,
        lane_failures=tuple(lane_failures),
        formal_all_pass=formal,
        exact_all_pass=exact,
        identifiability_all_pass=identifiable,
        all_block_success_artifacts_verified=all_blocks_pass,
        all_required_controls_pass=all_controls_pass,
        all_expected_terminations_verified=all_terminations_pass,
        all_analysis_controls_verified=all_analysis_pass,
        representation_invariants_pass=all_invariants_pass,
        no_unexpected_downstream_capability=no_unexpected_downstream,
        no_physical_anchor_run=scope_clean,
        evidence=checked_evidence,
        decision=decision,
    )


def control_assembly_to_wire(
    assembly: V3M0ControlAssembly,
) -> dict[str, object]:
    if type(assembly) is not V3M0ControlAssembly:
        raise TypeError("assembly must be an exact V3M0ControlAssembly")
    payload: dict[str, object] = {
        "schema_version": assembly.schema_version,
        "state": assembly.decision.state.value,
        "ready": assembly.decision.ready,
        "formal_all_pass": assembly.formal_all_pass,
        "exact_all_pass": assembly.exact_all_pass,
        "identifiability_all_pass": assembly.identifiability_all_pass,
        "all_block_success_artifacts_verified": (
            assembly.all_block_success_artifacts_verified
        ),
        "all_required_controls_pass": assembly.all_required_controls_pass,
        "all_expected_terminations_verified": (
            assembly.all_expected_terminations_verified
        ),
        "all_analysis_controls_verified": (
            assembly.all_analysis_controls_verified
        ),
        "representation_invariants_pass": (
            assembly.representation_invariants_pass
        ),
        "no_unexpected_downstream_capability": (
            assembly.no_unexpected_downstream_capability
        ),
        "no_physical_anchor_run": assembly.no_physical_anchor_run,
        "scenario_manifest": [
            {
                "control_id": contract.control_id,
                "scenario_id": contract.scenario_id,
                "scenario_slug": contract.scenario_slug,
                "execution_lane": contract.execution_lane,
                "expected_terminal_stage": (
                    contract.expected_terminal_stage
                ),
                "expected_undefined_reason": (
                    None
                    if contract.expected_undefined_reason is None
                    else contract.expected_undefined_reason.value
                ),
                "expected_artifact_type": contract.expected_artifact_type,
            }
            for contract in assembly.scenario_manifest
        ],
        "BLOCK_SUCCESS": [
            _audit_to_wire(row, id_key="scenario_id")
            for row in assembly.block_success
        ],
        "EXPECTED_TYPED_TERMINATION": [
            _audit_to_wire(row, id_key="scenario_id")
            for row in assembly.expected_typed_termination
        ],
        "ANALYSIS_CONTROL": [
            _audit_to_wire(row, id_key="scenario_id")
            for row in assembly.analysis_control
        ],
        "REPRESENTATION_INVARIANTS": [
            _audit_to_wire(row, id_key="invariant_id")
            for row in assembly.invariants
        ],
        "required_blocks": {
            "defined": assembly.required_blocks.status.defined,
            "undefined_reason": (
                None
                if assembly.required_blocks.status.reason is None
                else assembly.required_blocks.status.reason.value
            ),
            "undefined": [
                {
                    "block_id": block_id,
                    "reason": reason.value,
                }
                for block_id, reason in assembly.required_blocks.undefined
            ],
        },
        "lane_failures": [
            {
                "lane_id": lane_id,
                "reason": reason.value,
            }
            for lane_id, reason in assembly.lane_failures
        ],
    }
    for field in FINAL_RESULT_EVIDENCE_FIELDS:
        value = (
            None
            if assembly.evidence is None
            else getattr(assembly.evidence, field)
        )
        if field == "toolchain_manifest" and value is not None:
            value = _thaw_json(value)
        payload[field] = value
    return payload


def _thaw_json(value: object) -> object:
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    if hasattr(value, "items"):
        return {
            str(key): _thaw_json(item)
            for key, item in value.items()  # type: ignore[union-attr]
        }
    return value


__all__ = [
    "ANALYSIS_CONTROL_IDS",
    "ANALYSIS_CONTROL_SCENARIO_IDS",
    "APPLICATION_BLOCK_SUCCESS_CONTROL_IDS",
    "APPLICATION_BLOCK_SUCCESS_SCENARIO_IDS",
    "APPLICATION_CONTROL_IDS",
    "APPLICATION_PERMIT_CONTROL_IDS",
    "APPLICATION_SCENARIO_IDS",
    "BLOCK_SUCCESS_CONTROL_IDS",
    "BLOCK_SUCCESS_SCENARIO_IDS",
    "CONTROL_IDS",
    "EXPECTED_TERMINATION_STAGES",
    "EXPECTED_TYPED_TERMINATION_CONTROL_IDS",
    "EXPECTED_TYPED_TERMINATION_MANIFEST",
    "EXPECTED_TYPED_TERMINATION_SCENARIO_IDS",
    "REPRESENTATION_INVARIANT_IDS",
    "SCENARIO_IDS",
    "SCENARIO_LANE_MANIFEST",
    "SELECTED_BLOCK_SUCCESS_SCENARIO_IDS",
    "SELECTED_CONTROL_IDS",
    "V3M0AuditResult",
    "V3M0CapabilityBundle",
    "V3M0ControlAssembly",
    "V3M0ScenarioLaneContract",
    "V3M0_CONTROL_ASSEMBLY_SCHEMA_VERSION",
    "assemble_v3m0_controls",
    "control_assembly_to_wire",
]
