"""Closed C20 deterministic-series control authority for V3-M0.

C20 is an analysis control, not a response-block path.  Its two outcomes are
materialized only from the live ParentFreeze scenario wires, replay the pure
D-M2-6 fitter, and are returned through an opaque live capability.
"""

from __future__ import annotations

import math
import struct
import threading
import weakref
from dataclasses import dataclass, replace
from typing import Callable, Literal, Optional

import numpy as np

from .evidence import canonical_sha
from .parent_freeze import (
    ApplicationScenarioExecutionSpec,
    SyntheticApplicationOperation,
    V3M0SyntheticControlApplicationSpec,
    VerifiedParentFreeze,
    application_scenario_execution_spec_payload,
    synthetic_control_application_spec_payload,
)
from .sigma import (
    ConstantFit,
    DM26ControlAudit,
    DM26Decision,
    HighOrderFit,
    LeaveOneOutPowerFit,
    PowerFit,
    SigmaResult,
    fit_sigma,
)


DETERMINISTIC_SERIES_CONTROL_OUTCOME_SCHEMA_VERSION = (
    "v3m0.deterministic-series-control-outcome.v1"
)
_C20_CONTROL_ID = "C20_DM26_CLEAN_ZERO_TRUE_FLOOR"
_C20_SERIES_CLASSES = ("clean-zero", "true-floor")
_C20_RECIPE_ID = "deterministic-series-dm26-v1"
_C20_DECISION_RULE = "D-M2-6"
_ISSUANCE_TOKEN = object()


def _sha(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _finite(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an exact float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _optional_finite(value: object, field: str) -> Optional[float]:
    if value is None:
        return None
    return _finite(value, field)


def _constant_fit_payload(fit: ConstantFit) -> dict[str, object]:
    if type(fit) is not ConstantFit:
        raise TypeError("constant fit has the wrong exact type")
    return {
        "A": _finite(fit.A, "constant.A"),
        "sigma_A": _finite(fit.sigma_A, "constant.sigma_A"),
        "rss": _finite(fit.rss, "constant.rss"),
        "aic": _finite(fit.aic, "constant.aic"),
        "sample_count": fit.sample_count,
        "parameter_count": fit.parameter_count,
    }


def _power_fit_payload(fit: PowerFit) -> dict[str, object]:
    if type(fit) is not PowerFit:
        raise TypeError("power fit has the wrong exact type")
    return {
        "A": _finite(fit.A, "power.A"),
        "sigma_A": _optional_finite(fit.sigma_A, "power.sigma_A"),
        "B": _finite(fit.B, "power.B"),
        "sigma_B": _optional_finite(fit.sigma_B, "power.sigma_B"),
        "alpha": _finite(fit.alpha, "power.alpha"),
        "sigma_alpha": _optional_finite(
            fit.sigma_alpha,
            "power.sigma_alpha",
        ),
        "rss": _finite(fit.rss, "power.rss"),
        "aic": _finite(fit.aic, "power.aic"),
        "sample_count": fit.sample_count,
        "parameter_count": fit.parameter_count,
    }


def _high_order_fit_payload(fit: HighOrderFit) -> dict[str, object]:
    if type(fit) is not HighOrderFit:
        raise TypeError("high-order fit has the wrong exact type")
    return {
        "A": _finite(fit.A, "high.A"),
        "B": _finite(fit.B, "high.B"),
        "C": _finite(fit.C, "high.C"),
        "alpha": _finite(fit.alpha, "high.alpha"),
        "rss": _finite(fit.rss, "high.rss"),
        "aic": _finite(fit.aic, "high.aic"),
        "sample_count": fit.sample_count,
        "parameter_count": fit.parameter_count,
    }


def _dm26_decision_payload(decision: DM26Decision) -> dict[str, object]:
    if type(decision) is not DM26Decision:
        raise TypeError("D-M2-6 decision has the wrong exact type")
    return {
        "power_full": _power_fit_payload(decision.power_full),
        "high_order": _high_order_fit_payload(decision.high_order),
        "delta_aic_power_minus_high": _finite(
            decision.delta_aic_power_minus_high,
            "dm26.delta_aic_power_minus_high",
        ),
        "high_order_aic_supported": decision.high_order_aic_supported,
        "high_order_intercept_collapsed": (
            decision.high_order_intercept_collapsed
        ),
        "high_order_pollution": decision.high_order_pollution,
        "A_half": _finite(decision.A_half, "dm26.A_half"),
        "alpha_half": _finite(decision.alpha_half, "dm26.alpha_half"),
        "half_window_pollution": decision.half_window_pollution,
        "both_pollution": decision.both_pollution,
    }


def _dm26_control_payload(control: DM26ControlAudit) -> dict[str, object]:
    if type(control) is not DM26ControlAudit:
        raise TypeError("D-M2-6 control has the wrong exact type")
    return {
        "control_id": control.control_id,
        "family": control.family,
        "expected_pollution": control.expected_pollution,
        "decision": _dm26_decision_payload(control.decision),
        "matches_expected": control.matches_expected,
    }


def sigma_result_evidence_payload(result: SigmaResult) -> dict[str, object]:
    """Serialize every frozen sigma fit/decision field without NaN sentinels."""

    if type(result) is not SigmaResult:
        raise TypeError("sigma result has the wrong exact type")
    if any(type(row) is not LeaveOneOutPowerFit for row in result.loo):
        raise TypeError("LOO rows have the wrong exact type")
    decision = result.dm26_decision
    return {
        "geometry_manifest_id": result.geometry_manifest_id,
        "deterministic": result.deterministic,
        "model_winner": result.model_winner,
        "constant_fit": _constant_fit_payload(result.constant_fit),
        "power_fit": _power_fit_payload(result.power_fit),
        "high_order_fit": _high_order_fit_payload(result.high_order_fit),
        "A": _finite(result.A, "sigma.A"),
        "alpha": _optional_finite(result.alpha, "sigma.alpha"),
        "sigma_A": _optional_finite(result.sigma_A, "sigma.sigma_A"),
        "sigma_alpha": _optional_finite(
            result.sigma_alpha,
            "sigma.sigma_alpha",
        ),
        "delta_aic": _finite(result.delta_aic, "sigma.delta_aic"),
        "loo": [
            {
                "dropped_k": _finite(row.dropped_k, "loo.dropped_k"),
                "fit": _power_fit_payload(row.fit),
            }
            for row in result.loo
        ],
        "fit_window": [
            _finite(value, "sigma.fit_window") for value in result.fit_window
        ],
        "expanded_window": (
            None
            if result.expanded_window is None
            else [
                _finite(value, "sigma.expanded_window")
                for value in result.expanded_window
            ]
        ),
        "direction": result.direction,
        "alpha_identifiable": result.alpha_identifiable,
        "zero_consistent": result.zero_consistent,
        "zero_test": result.zero_test,
        "dm26_decision": (
            None if decision is None else _dm26_decision_payload(decision)
        ),
        "dm26_controls": [
            _dm26_control_payload(control) for control in result.dm26_controls
        ],
    }


@dataclass(frozen=True)
class DeterministicSeriesControlOutcome:
    outcome_schema_version: str
    parent_freeze_sha: str
    application_spec: V3M0SyntheticControlApplicationSpec
    scenario_spec: ApplicationScenarioExecutionSpec
    k_values: tuple[float, ...]
    raw_samples: tuple[float, ...]
    series_class: Literal["clean-zero", "true-floor"]
    decision_rule: Literal["D-M2-6"]
    sigma_result: SigmaResult
    fit_decision_evidence_sha: str
    outcome_sha: str

    def __post_init__(self) -> None:
        if (
            self.outcome_schema_version
            != DETERMINISTIC_SERIES_CONTROL_OUTCOME_SCHEMA_VERSION
        ):
            raise ValueError("deterministic-series outcome schema is not frozen")
        _sha(self.parent_freeze_sha, "parent_freeze_sha")
        if type(self.application_spec) is not V3M0SyntheticControlApplicationSpec:
            raise TypeError("application_spec has the wrong exact type")
        if type(self.scenario_spec) is not ApplicationScenarioExecutionSpec:
            raise TypeError("scenario_spec has the wrong exact type")
        if type(self.k_values) is not tuple or type(self.raw_samples) is not tuple:
            raise TypeError("series values must be exact tuples")
        if len(self.k_values) != 4 or len(self.raw_samples) != 4:
            raise ValueError("C20 series must contain exactly four samples")
        for value in (*self.k_values, *self.raw_samples):
            _finite(value, "series value")
        if self.series_class not in _C20_SERIES_CLASSES:
            raise ValueError("series_class is outside the C20 registry")
        if self.decision_rule != _C20_DECISION_RULE:
            raise ValueError("decision_rule is not D-M2-6")
        if type(self.sigma_result) is not SigmaResult:
            raise TypeError("sigma_result has the wrong exact type")
        for field in ("fit_decision_evidence_sha", "outcome_sha"):
            _sha(getattr(self, field), field)


def _application_record(
    spec: V3M0SyntheticControlApplicationSpec,
) -> dict[str, object]:
    return {
        **synthetic_control_application_spec_payload(spec),
        "application_spec_sha": spec.application_spec_sha,
    }


def _scenario_record(
    scenario: ApplicationScenarioExecutionSpec,
) -> dict[str, object]:
    return {
        **application_scenario_execution_spec_payload(scenario),
        "scenario_sha": scenario.scenario_sha,
    }


def deterministic_series_control_outcome_payload(
    outcome: DeterministicSeriesControlOutcome,
) -> dict[str, object]:
    if type(outcome) is not DeterministicSeriesControlOutcome:
        raise TypeError("outcome must be a DeterministicSeriesControlOutcome")
    outcome.__post_init__()
    return {
        "outcome_schema_version": outcome.outcome_schema_version,
        "parent_freeze_sha": outcome.parent_freeze_sha,
        "application_spec": _application_record(outcome.application_spec),
        "scenario_spec": _scenario_record(outcome.scenario_spec),
        "k_values": list(outcome.k_values),
        "raw_samples": list(outcome.raw_samples),
        "series_class": outcome.series_class,
        "decision_rule": outcome.decision_rule,
        "fit_decision_evidence": sigma_result_evidence_payload(
            outcome.sigma_result
        ),
        "fit_decision_evidence_sha": outcome.fit_decision_evidence_sha,
    }


def _wire_float(operation: SyntheticApplicationOperation, name: str) -> float:
    parameters = dict(operation.parameters)
    if name not in parameters:
        raise ValueError(f"C20 operation is missing {name}")
    wire = parameters[name]
    if wire.value_kind != "fp64-bits" or wire.fp64_bits_value is None:
        raise ValueError(f"C20 {name} is not a frozen fp64 wire")
    value = struct.unpack(">d", struct.pack(">Q", wire.fp64_bits_value))[0]
    return _finite(float(value), name)


def _wire_text(operation: SyntheticApplicationOperation, name: str) -> str:
    parameters = dict(operation.parameters)
    if name not in parameters:
        raise ValueError(f"C20 operation is missing {name}")
    wire = parameters[name]
    if wire.value_kind != "text" or wire.text_value is None:
        raise ValueError(f"C20 {name} is not a frozen text wire")
    return wire.text_value


def _materialize_outcome(
    parent: VerifiedParentFreeze,
    scenario_id: str,
    *,
    wire_float: Callable[[SyntheticApplicationOperation, str], float] = (
        _wire_float
    ),
    wire_text: Callable[[SyntheticApplicationOperation, str], str] = _wire_text,
    sigma_fitter: Callable[..., SigmaResult] = fit_sigma,
    fit_payload_builder: Callable[[SigmaResult], dict[str, object]] = (
        sigma_result_evidence_payload
    ),
    outcome_payload_builder: Callable[
        [DeterministicSeriesControlOutcome],
        dict[str, object],
    ] = deterministic_series_control_outcome_payload,
    canonical_hash: Callable[[object], str] = canonical_sha,
) -> DeterministicSeriesControlOutcome:
    if type(parent) is not VerifiedParentFreeze:
        raise TypeError("parent must be a live VerifiedParentFreeze")
    if type(scenario_id) is not str:
        raise TypeError("scenario_id must be an exact string")
    manifest = parent.manifest
    application = next(
        (
            spec
            for spec in manifest.synthetic_control_application_specs
            if spec.control_case_id == _C20_CONTROL_ID
        ),
        None,
    )
    if application is None:
        raise ValueError("ParentFreeze has no C20 application")
    scenario = next(
        (
            candidate
            for candidate in application.scenario_execution_specs
            if candidate.scenario_id == scenario_id
        ),
        None,
    )
    if scenario is None:
        raise ValueError("scenario_id is not a frozen C20 scenario")
    if (
        scenario.execution_lane != "ANALYSIS_CONTROL"
        or scenario.execution_recipe_id != _C20_RECIPE_ID
        or scenario.expected_artifact_type
        != "VerifiedDeterministicSeriesControlOutcome"
        or len(scenario.operation_output_ids) != 1
    ):
        raise ValueError("C20 scenario contract is inconsistent")
    operation_by_id = {
        operation.operation_instance_id: operation
        for operation in application.operations
    }
    operation = operation_by_id.get(scenario.operation_output_ids[0])
    if operation is None or operation.operation_kind != "deterministic-series-v1":
        raise ValueError("C20 scenario does not select a deterministic series")
    series_class = wire_text(operation, "series-class")
    if series_class not in _C20_SERIES_CLASSES:
        raise ValueError("C20 series class is not frozen")
    k_values = tuple(wire_float(operation, f"k-{index}") for index in range(4))
    raw_samples = tuple(
        wire_float(operation, f"sample-{index}") for index in range(4)
    )
    pair = next(
        (
            candidate
            for candidate in application.operations
            if candidate.operation_kind == "direct-sum-v1"
            and set(candidate.input_operation_instance_ids)
            == {
                item.operation_output_ids[0]
                for item in application.scenario_execution_specs
            }
        ),
        None,
    )
    if pair is None or wire_text(pair, "decision-rule") != _C20_DECISION_RULE:
        raise ValueError("C20 D-M2-6 pair operation is absent")
    result = sigma_fitter(
        np.asarray(k_values, dtype=np.float64),
        np.asarray(raw_samples, dtype=np.float64),
        f"v3m0-c20-{scenario.scenario_sha}",
        deterministic=True,
    )
    if (
        result.dm26_decision is None
        or len(result.dm26_controls) != 8
        or not all(control.matches_expected for control in result.dm26_controls)
    ):
        raise ValueError("C20 D-M2-6 teeth controls did not verify")
    expected_zero = series_class == "clean-zero"
    if result.zero_consistent is not expected_zero:
        raise ValueError("C20 clean-zero/true-floor decision is incorrect")
    if result.dm26_decision.both_pollution is not expected_zero:
        raise ValueError("C20 D-M2-6 double test did not separate the controls")
    fit_payload = fit_payload_builder(result)
    provisional = DeterministicSeriesControlOutcome(
        outcome_schema_version=(
            DETERMINISTIC_SERIES_CONTROL_OUTCOME_SCHEMA_VERSION
        ),
        parent_freeze_sha=manifest.parent_freeze_sha,
        application_spec=application,
        scenario_spec=scenario,
        k_values=k_values,
        raw_samples=raw_samples,
        series_class=series_class,
        decision_rule=_C20_DECISION_RULE,
        sigma_result=result,
        fit_decision_evidence_sha=canonical_hash(fit_payload),
        outcome_sha="0" * 64,
    )
    return replace(
        provisional,
        outcome_sha=canonical_hash(outcome_payload_builder(provisional)),
    )


class VerifiedDeterministicSeriesControlOutcome:
    """Opaque live capability for one canonical C20 scenario replay."""

    __slots__ = (
        "__parent",
        "__scenario_id",
        "__seal",
        "__token",
        "__weakref__",
    )

    def __init__(
        self,
        token: object,
        parent: VerifiedParentFreeze,
        scenario_id: str,
        seal: str,
        *,
        _issuance_token: object = _ISSUANCE_TOKEN,
    ) -> None:
        if token is not _issuance_token:
            raise TypeError(
                "VerifiedDeterministicSeriesControlOutcome is issuer-only"
            )
        object.__setattr__(self, "_VerifiedDeterministicSeriesControlOutcome__parent", parent)
        object.__setattr__(
            self,
            "_VerifiedDeterministicSeriesControlOutcome__scenario_id",
            scenario_id,
        )
        object.__setattr__(self, "_VerifiedDeterministicSeriesControlOutcome__seal", seal)
        object.__setattr__(self, "_VerifiedDeterministicSeriesControlOutcome__token", token)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError(
            "VerifiedDeterministicSeriesControlOutcome is immutable"
        )

    @property
    def outcome(self) -> DeterministicSeriesControlOutcome:
        return _reverify_verified_deterministic_series_control_outcome(self)


@dataclass(frozen=True)
class _SeriesAuthority:
    parent: VerifiedParentFreeze
    scenario_id: str
    seal: str


def _series_seal(
    parent: VerifiedParentFreeze,
    outcome: DeterministicSeriesControlOutcome,
    *,
    canonical_hash: Callable[[object], str] = canonical_sha,
) -> str:
    return canonical_hash(
        {
            "authority_kind": "v3m0-deterministic-series-control-live-v1",
            "parent_identity": id(parent),
            "parent_freeze_sha": outcome.parent_freeze_sha,
            "scenario_sha": outcome.scenario_spec.scenario_sha,
            "outcome_sha": outcome.outcome_sha,
        }
    )


def _make_series_registry(
    *,
    materializer: Callable[
        [VerifiedParentFreeze, str],
        DeterministicSeriesControlOutcome,
    ] = _materialize_outcome,
    seal_builder: Callable[
        [VerifiedParentFreeze, DeterministicSeriesControlOutcome],
        str,
    ] = _series_seal,
    wrapper_type: type[
        VerifiedDeterministicSeriesControlOutcome
    ] = VerifiedDeterministicSeriesControlOutcome,
    canonical_hash: Callable[[object], str] = canonical_sha,
    fit_payload_builder: Callable[[SigmaResult], dict[str, object]] = (
        sigma_result_evidence_payload
    ),
    outcome_payload_builder: Callable[
        [DeterministicSeriesControlOutcome],
        dict[str, object],
    ] = deterministic_series_control_outcome_payload,
) -> tuple[
    Callable[
        [VerifiedParentFreeze, str],
        VerifiedDeterministicSeriesControlOutcome,
    ],
    Callable[
        [VerifiedDeterministicSeriesControlOutcome],
        DeterministicSeriesControlOutcome,
    ],
]:
    registry: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedDeterministicSeriesControlOutcome],
            _SeriesAuthority,
        ],
    ] = {}
    lock = threading.RLock()

    def issue(
        parent: VerifiedParentFreeze,
        scenario_id: str,
    ) -> VerifiedDeterministicSeriesControlOutcome:
        outcome = materializer(parent, scenario_id)
        seal = seal_builder(parent, outcome)
        wrapper = wrapper_type(
            _ISSUANCE_TOKEN,
            parent,
            scenario_id,
            seal,
        )
        authority = _SeriesAuthority(parent, scenario_id, seal)
        key = id(wrapper)

        def expire(reference, *, registry_key=key):
            with lock:
                current = registry.get(registry_key)
                if current is not None and current[0] is reference:
                    registry.pop(registry_key, None)

        reference = weakref.ref(wrapper, expire)
        with lock:
            registry[key] = (reference, authority)
        return wrapper

    def reverify(
        value: VerifiedDeterministicSeriesControlOutcome,
    ) -> DeterministicSeriesControlOutcome:
        if type(value) is not VerifiedDeterministicSeriesControlOutcome:
            raise TypeError(
                "value must be a VerifiedDeterministicSeriesControlOutcome"
            )
        with lock:
            entry = registry.get(id(value))
        if entry is None or entry[0]() is not value:
            raise ValueError("deterministic-series authority is not live")
        authority = entry[1]
        parent = object.__getattribute__(
            value,
            "_VerifiedDeterministicSeriesControlOutcome__parent",
        )
        scenario_id = object.__getattribute__(
            value,
            "_VerifiedDeterministicSeriesControlOutcome__scenario_id",
        )
        seal = object.__getattribute__(
            value,
            "_VerifiedDeterministicSeriesControlOutcome__seal",
        )
        token = object.__getattribute__(
            value,
            "_VerifiedDeterministicSeriesControlOutcome__token",
        )
        if (
            token is not _ISSUANCE_TOKEN
            or parent is not authority.parent
            or scenario_id != authority.scenario_id
            or seal != authority.seal
        ):
            raise ValueError("deterministic-series wrapper identity changed")
        outcome = materializer(parent, scenario_id)
        if seal_builder(parent, outcome) != authority.seal:
            raise ValueError("deterministic-series live replay changed")
        if outcome.fit_decision_evidence_sha != canonical_hash(
            fit_payload_builder(outcome.sigma_result)
        ):
            raise ValueError("fit-decision evidence hash mismatch")
        if outcome.outcome_sha != canonical_hash(
            outcome_payload_builder(outcome)
        ):
            raise ValueError("deterministic-series outcome hash mismatch")
        return outcome

    return issue, reverify


(
    _issue_verified_deterministic_series_control_outcome,
    _reverify_verified_deterministic_series_control_outcome,
) = _make_series_registry()


def _make_public_series_issuer(
    issuer: Callable[
        [VerifiedParentFreeze, str],
        VerifiedDeterministicSeriesControlOutcome,
    ],
) -> Callable[
    [VerifiedParentFreeze],
    tuple[
        VerifiedDeterministicSeriesControlOutcome,
        VerifiedDeterministicSeriesControlOutcome,
    ],
]:
    def issue(
        parent: VerifiedParentFreeze,
    ) -> tuple[
        VerifiedDeterministicSeriesControlOutcome,
        VerifiedDeterministicSeriesControlOutcome,
    ]:
        """Issue both canonical C20 analysis scenarios in ParentFreeze order."""

        if type(parent) is not VerifiedParentFreeze:
            raise TypeError("parent must be a live VerifiedParentFreeze")
        manifest = parent.manifest
        application = next(
            spec
            for spec in manifest.synthetic_control_application_specs
            if spec.control_case_id == _C20_CONTROL_ID
        )
        scenarios = application.scenario_execution_specs
        if (
            len(scenarios) != 2
            or tuple(scenario.execution_lane for scenario in scenarios)
            != ("ANALYSIS_CONTROL", "ANALYSIS_CONTROL")
        ):
            raise ValueError("ParentFreeze C20 scenario order is not frozen")
        return (
            issuer(parent, scenarios[0].scenario_id),
            issuer(parent, scenarios[1].scenario_id),
        )

    return issue


issue_v3m0_deterministic_series_control_outcomes = _make_public_series_issuer(
    _issue_verified_deterministic_series_control_outcome
)


def _make_public_series_verifier(
    verifier: Callable[
        [VerifiedDeterministicSeriesControlOutcome],
        DeterministicSeriesControlOutcome,
    ],
) -> Callable[
    [VerifiedDeterministicSeriesControlOutcome],
    DeterministicSeriesControlOutcome,
]:
    def verify(
        value: VerifiedDeterministicSeriesControlOutcome,
    ) -> DeterministicSeriesControlOutcome:
        """Recompute one live C20 outcome from its bound ParentFreeze scenario."""

        return verifier(value)

    return verify


verify_verified_deterministic_series_control_outcome = (
    _make_public_series_verifier(
        _reverify_verified_deterministic_series_control_outcome
    )
)

__all__ = [
    "DETERMINISTIC_SERIES_CONTROL_OUTCOME_SCHEMA_VERSION",
    "DeterministicSeriesControlOutcome",
    "VerifiedDeterministicSeriesControlOutcome",
    "deterministic_series_control_outcome_payload",
    "issue_v3m0_deterministic_series_control_outcomes",
    "sigma_result_evidence_payload",
    "verify_verified_deterministic_series_control_outcome",
]
