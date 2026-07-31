"""Causal-subspace survival kernels and the V3-M0 Task 13 authority.

The numerical kernel remains independently testable, but the evaluator-facing
API accepts only live Task 12 response blocks and a live survival-threshold
authority.  Calibration evidence recursively embeds the complete Parent,
permit, application-spec, and branch-block wires and is always rebuilt from
the live inputs before use.
"""

from __future__ import annotations

import math
import threading
import weakref
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

from .blocks import (
    ResponseBlock,
    VerifiedResponseBlock,
    _reverify_verified_response_block,
    response_block_payload,
)
from .calibration_authority import (
    CalibrationApplicationPermit,
    VerifiedCalibrationApplicationPermit,
    _preflight_tree,
    _reverify_verified_calibration_application_permit,
    build_v3m0_application_response_run_spec,
    calibration_application_permit_payload,
)
from .evidence import canonical_sha
from .factory import frozen_tensor_array
from .linalg import (
    LINALG_ARITHMETIC_WORK_CAP,
    LINALG_ENTRY_CAP,
    _canonical_columns_work,
    canonical_orthonormal_columns,
)
from .parent_freeze import (
    ParentFreezeManifest,
    V3M0SyntheticControlApplicationSpec,
    parent_freeze_manifest_payload,
    synthetic_control_application_spec_payload,
)
from .thresholds import SIGNAL_NOISE_RATIO_MIN


CAUSAL_HERMITIAN_TOLERANCE = 1e-12
SURVIVAL_THRESHOLD_INSTANCE_AUDIT_SCHEMA_VERSION = (
    "v3m0.survival-threshold-instance-audit.v1"
)
SURVIVAL_THRESHOLD_CONTROL_EVIDENCE_SCHEMA_VERSION = (
    "v3m0.survival-threshold-control-evidence.v1"
)
SURVIVAL_THRESHOLD_CALIBRATION_SCHEMA_VERSION = (
    "v3m0.survival-threshold-calibration.v1"
)
SURVIVAL_THRESHOLD = 0.5
SURVIVAL_AMBIGUITY_HALF_WIDTH = 0.1

_SIDE_LABELS = ("below", "grey", "above")
_REQUIRED_SURVIVAL_THRESHOLD_CONTROLS = (
    "C04_CANONICAL_ANGLE_025_075",
)
_UNENCODABLE_SURVIVAL_THRESHOLD_CONTROL = (
    "C11_NULL_GREY_SIGNAL_AMPLITUDE"
)
_ZERO_SHA = "0" * 64
_ISSUANCE_TOKEN = object()


@dataclass(frozen=True)
class CausalNumericalThresholds:
    """Numeric view mechanically copied from verified Task 11/13 calibration."""

    absolute_signal_threshold: float
    raw_noise_floor: float
    relative_gap_min: float
    survival_threshold: float
    survival_ambiguity_half_width: float

    def __post_init__(self) -> None:
        for field in (
            "absolute_signal_threshold",
            "raw_noise_floor",
            "relative_gap_min",
            "survival_threshold",
            "survival_ambiguity_half_width",
        ):
            value = getattr(self, field)
            if type(value) is not float or not math.isfinite(value):
                raise TypeError(f"{field} must be an exact finite float")
        if self.absolute_signal_threshold <= 0.0:
            raise ValueError("absolute_signal_threshold must be positive")
        if self.raw_noise_floor < 0.0:
            raise ValueError("raw_noise_floor must be nonnegative")
        if self.relative_gap_min < 1.0:
            raise ValueError("relative_gap_min must be at least one")
        if not 0.0 < self.survival_threshold < 1.0:
            raise ValueError("survival_threshold must lie strictly inside (0,1)")
        if self.survival_ambiguity_half_width <= 0.0:
            raise ValueError("survival_ambiguity_half_width must be positive")
        if (
            self.survival_threshold - self.survival_ambiguity_half_width < 0.0
            or self.survival_threshold + self.survival_ambiguity_half_width > 1.0
        ):
            raise ValueError("survival ambiguity band must lie inside [0,1]")


@dataclass(frozen=True)
class CausalSpectrum:
    survival_spectrum: tuple[float, ...]
    epsilon_dof: Optional[float]
    epsilon_cont: float
    chi_extra: float
    kappa_map: Optional[float]
    d_proc_sq: Optional[float]
    gain_ratio: Optional[float]
    phase_shift: Optional[float]
    ambiguous: bool
    actual_rank: int
    ablated_rank: int
    ablated_all_rank: int
    k_surv_hermitian_residual: float


def _response_matrix_header(value: object, field: str) -> np.ndarray:
    if type(value) is not np.ndarray:
        raise TypeError(f"{field} must be an exact numpy.ndarray")
    if value.ndim != 2 or value.shape[0] <= 0 or value.shape[1] <= 0:
        raise ValueError(f"{field} must be a non-empty matrix")
    if value.shape[0] * value.shape[1] > LINALG_ENTRY_CAP:
        raise ValueError(f"{field} exceeds the matrix resource cap")
    if value.dtype != np.dtype(np.complex128):
        raise TypeError(f"{field} must have complex128 dtype")
    return value


def _materialize_response_matrix(value: np.ndarray, field: str) -> np.ndarray:
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{field} must be finite")
    return np.array(value, dtype=np.complex128, copy=True, order="C")


def _max_abs(value: np.ndarray) -> float:
    if value.size == 0:
        return 0.0
    return float(np.max(np.abs(value)))


def _basis_decomposition_work(values: np.ndarray) -> int:
    maximum_rank = min(values.shape)
    return values.shape[0] * values.shape[1] * maximum_rank + _canonical_columns_work(
        *values.shape
    )


def _canonical_unit_interval(value: float, field: str) -> float:
    result = float(value)
    if (
        not math.isfinite(result)
        or result < -CAUSAL_HERMITIAN_TOLERANCE
        or result > 1.0 + CAUSAL_HERMITIAN_TOLERANCE
    ):
        raise ValueError(f"{field} is outside the audited unit interval")
    return float(min(1.0, max(0.0, result)))


def _canonical_unit_interval_array(values: np.ndarray, field: str) -> np.ndarray:
    if not bool(np.all(np.isfinite(values))) or bool(
        np.any(values < -CAUSAL_HERMITIAN_TOLERANCE)
        or np.any(values > 1.0 + CAUSAL_HERMITIAN_TOLERANCE)
    ):
        raise ValueError(f"{field} lies outside the audited unit interval")
    return np.clip(values, 0.0, 1.0).astype(np.float64, copy=False)


def _active_basis(
    values: np.ndarray,
    thresholds: CausalNumericalThresholds,
    field: str,
) -> np.ndarray:
    work = _basis_decomposition_work(values)
    if work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError(f"{field} exceeds the arithmetic work cap")
    singular_values = np.linalg.svd(
        values,
        compute_uv=False,
        full_matrices=False,
    )
    if not bool(np.all(np.isfinite(singular_values))):
        raise ValueError(f"{field} singular values are non-finite")
    numerical_floor = (
        np.finfo(np.float64).eps * max(values.shape) * float(singular_values[0]) * 64.0
    )
    signal_line = max(
        thresholds.absolute_signal_threshold,
        thresholds.raw_noise_floor * thresholds.relative_gap_min,
    )
    if bool(
        np.any(
            (singular_values > thresholds.raw_noise_floor)
            & (singular_values < signal_line)
        )
    ):
        raise ValueError(f"{field} lies in the calibrated signal grey band")
    if numerical_floor > signal_line and bool(
        np.any((singular_values >= signal_line) & (singular_values < numerical_floor))
    ):
        raise ValueError(f"{field} numerical rank is unresolved above signal line")
    effective_threshold = float(max(signal_line, numerical_floor))
    rank = int(np.count_nonzero(singular_values >= effective_threshold))
    if 0 < rank < len(singular_values):
        inactive = max(
            float(singular_values[rank]),
            thresholds.raw_noise_floor,
        )
        relative_gap = (
            math.inf if inactive == 0.0 else float(singular_values[rank - 1]) / inactive
        )
        if relative_gap < thresholds.relative_gap_min:
            raise ValueError(f"{field} does not pass the relative rank gap")
    return canonical_orthonormal_columns(
        values,
        absolute_threshold=effective_threshold,
        expected_rank=rank,
    )


def _scaled_frobenius(value: np.ndarray) -> tuple[float, float]:
    scale = _max_abs(value)
    if scale == 0.0:
        return 0.0, 0.0
    scaled = value / scale
    norm_sq = float(np.sum(np.abs(scaled) ** 2))
    if not math.isfinite(norm_sq) or norm_sq <= 0.0:
        raise ValueError("scaled Frobenius norm left the finite range")
    return scale, norm_sq


def compute_causal_spectrum(
    actual_on_actual_sector: np.ndarray,
    ablated_on_actual_sector: np.ndarray,
    ablated_on_full_source: np.ndarray,
    *,
    thresholds: CausalNumericalThresholds,
) -> CausalSpectrum:
    """Measure matched-ablation survival in the actual curvature sector."""

    actual_view = _response_matrix_header(
        actual_on_actual_sector,
        "actual_on_actual_sector",
    )
    ablated_view = _response_matrix_header(
        ablated_on_actual_sector,
        "ablated_on_actual_sector",
    )
    ablated_all_view = _response_matrix_header(
        ablated_on_full_source,
        "ablated_on_full_source",
    )
    if ablated_view.shape != actual_view.shape:
        raise ValueError("matched response shape mismatch")
    if ablated_all_view.shape[0] != actual_view.shape[0]:
        raise ValueError("full-source response observer dimension mismatch")
    if type(thresholds) is not CausalNumericalThresholds:
        raise TypeError("thresholds must be exact calibrated numerical values")

    observer_dimension = actual_view.shape[0]
    actual_rank_cap = min(actual_view.shape)
    ablated_rank_cap = min(ablated_view.shape)
    ablated_all_rank_cap = min(ablated_all_view.shape)
    aggregate_work = (
        _basis_decomposition_work(actual_view)
        + _basis_decomposition_work(ablated_view)
        + _basis_decomposition_work(ablated_all_view)
        + observer_dimension * ablated_rank_cap * actual_rank_cap
        + ablated_rank_cap * actual_rank_cap**2
        + 2 * actual_rank_cap**3
        + observer_dimension * actual_rank_cap * ablated_all_rank_cap
        + observer_dimension * (2 * actual_view.shape[1] + ablated_all_view.shape[1])
    )
    if aggregate_work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError("causal aggregate calculation exceeds the arithmetic work cap")

    actual = _materialize_response_matrix(
        actual_view,
        "actual_on_actual_sector",
    )
    ablated = _materialize_response_matrix(
        ablated_view,
        "ablated_on_actual_sector",
    )
    ablated_all = _materialize_response_matrix(
        ablated_all_view,
        "ablated_on_full_source",
    )

    actual_basis = _active_basis(
        actual,
        thresholds,
        "actual response",
    )
    if actual_basis.shape[1] != actual.shape[1]:
        raise ValueError("actual response lost a preregistered curvature mode")
    ablated_basis = _active_basis(
        ablated,
        thresholds,
        "ablated response",
    )
    ablated_all_basis = _active_basis(
        ablated_all,
        thresholds,
        "full-source ablated response",
    )

    if ablated_basis.shape[1] == 0:
        k_surv = np.zeros(
            (actual_basis.shape[1], actual_basis.shape[1]),
            dtype=np.complex128,
        )
    else:
        overlap = ablated_basis.conj().T @ actual_basis
        k_surv = overlap.conj().T @ overlap
    hermitian_residual = float(np.linalg.norm(k_surv - k_surv.conj().T, ord=2))
    if (
        not math.isfinite(hermitian_residual)
        or hermitian_residual > CAUSAL_HERMITIAN_TOLERANCE
    ):
        raise ValueError("K_surv exceeds the Hermitian residual tolerance")

    survival = _canonical_unit_interval_array(
        np.linalg.eigvalsh(k_surv),
        "K_surv eigenvalue",
    )
    ambiguous = bool(
        np.any(
            np.abs(survival - thresholds.survival_threshold)
            < thresholds.survival_ambiguity_half_width
        )
    )
    epsilon_dof = (
        None
        if ambiguous
        else float(
            np.count_nonzero(survival >= thresholds.survival_threshold) / len(survival)
        )
    )
    epsilon_cont = _canonical_unit_interval(
        float(np.mean(survival)),
        "continuous survival",
    )

    if ablated_all_basis.shape[1] == 0:
        chi_extra = 0.0
    else:
        shared_weight = float(
            np.linalg.norm(
                actual_basis.conj().T @ ablated_all_basis,
                ord="fro",
            )
            ** 2
        )
        chi_extra = float(1.0 - shared_weight / ablated_all_basis.shape[1])
        chi_extra = _canonical_unit_interval(
            chi_extra,
            "full-source extra-mode fraction",
        )

    ablated_scale, ablated_norm_scaled = _scaled_frobenius(ablated)
    actual_scale, actual_norm_scaled = _scaled_frobenius(actual)
    if ablated_scale == 0.0:
        kappa_map = None
        d_proc_sq = None
        gain_ratio = None
        phase_shift = None
    else:
        ablated_scaled = ablated / ablated_scale
        actual_scaled = actual / actual_scale
        inner = complex(np.vdot(ablated_scaled, actual_scaled))
        kappa_map = _canonical_unit_interval(
            float(abs(inner) ** 2 / (ablated_norm_scaled * actual_norm_scaled)),
            "Procrustes overlap",
        )
        d_proc_sq = _canonical_unit_interval(
            float(1.0 - kappa_map),
            "Procrustes squared distance",
        )
        log_gain = (
            math.log(ablated_scale)
            - math.log(actual_scale)
            + 0.5 * (math.log(ablated_norm_scaled) - math.log(actual_norm_scaled))
        )
        if abs(log_gain) > math.log(np.finfo(np.float64).max):
            raise ValueError("Procrustes gain ratio left the finite range")
        gain_ratio = float(math.exp(log_gain))
        phase_shift = (
            None if abs(inner) == 0.0 else float(math.atan2(inner.imag, inner.real))
        )

    return CausalSpectrum(
        survival_spectrum=tuple(float(value) for value in survival),
        epsilon_dof=epsilon_dof,
        epsilon_cont=epsilon_cont,
        chi_extra=chi_extra,
        kappa_map=kappa_map,
        d_proc_sq=d_proc_sq,
        gain_ratio=gain_ratio,
        phase_shift=phase_shift,
        ambiguous=ambiguous,
        actual_rank=actual_basis.shape[1],
        ablated_rank=ablated_basis.shape[1],
        ablated_all_rank=ablated_all_basis.shape[1],
        k_surv_hermitian_residual=hermitian_residual,
    )


def _sha(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    try:
        observed = frozenset(vars(value))
    except TypeError as exc:
        raise TypeError(f"{field} has no exact record body") from exc
    expected = frozenset(record_type.__dataclass_fields__)
    if observed != expected:
        raise ValueError(f"{field} contains missing or unknown fields")


def _finite_float(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an exact fp64 wire float")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _finite_unit_tuple(value: object, field: str) -> tuple[float, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty tuple")
    result: list[float] = []
    for index, item in enumerate(value):
        number = _finite_float(item, f"{field}[{index}]")
        if number < 0.0 or number > 1.0:
            raise ValueError(f"{field}[{index}] must lie inside [0,1]")
        result.append(number)
    return tuple(result)


def _finite_tuple(value: object, field: str) -> tuple[float, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty tuple")
    return tuple(
        _finite_float(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    )


def _side_tuple(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty tuple")
    for index, item in enumerate(value):
        if type(item) is not str or item not in _SIDE_LABELS:
            raise ValueError(f"{field}[{index}] is not a frozen side label")
    return value


def _application_record(
    application: V3M0SyntheticControlApplicationSpec,
) -> dict[str, object]:
    return {
        **synthetic_control_application_spec_payload(application),
        "application_spec_sha": application.application_spec_sha,
    }


def _permit_record(
    permit: CalibrationApplicationPermit,
) -> dict[str, object]:
    return {
        **calibration_application_permit_payload(permit),
        "permit_sha": permit.permit_sha,
    }


def _block_record(block: ResponseBlock) -> dict[str, object]:
    return {
        **response_block_payload(block),
        "block_sha": block.block_sha,
    }


def _parent_record(parent: ParentFreezeManifest) -> dict[str, object]:
    return {
        **parent_freeze_manifest_payload(parent),
        "parent_freeze_sha": parent.parent_freeze_sha,
    }


@dataclass(frozen=True)
class SurvivalThresholdInstanceAudit:
    audit_schema_version: str
    application_spec: V3M0SyntheticControlApplicationSpec
    permit: CalibrationApplicationPermit
    actual_block: ResponseBlock
    ablated_block: ResponseBlock
    survival_spectrum: tuple[float, ...]
    measured_side_labels: tuple[Literal["below", "grey", "above"], ...]
    expected_side_labels: tuple[Literal["below", "grey", "above"], ...]
    signed_threshold_margins: tuple[float, ...]
    minimum_absolute_margin: float
    audit_sha: str

    def __post_init__(self) -> None:
        if self.audit_schema_version != (
            SURVIVAL_THRESHOLD_INSTANCE_AUDIT_SCHEMA_VERSION
        ):
            raise ValueError("survival threshold audit schema is not frozen")
        if type(self.application_spec) is not V3M0SyntheticControlApplicationSpec:
            raise TypeError("application_spec has the wrong strict type")
        if type(self.permit) is not CalibrationApplicationPermit:
            raise TypeError("permit has the wrong strict type")
        if self.permit.application_spec != self.application_spec:
            raise ValueError("permit does not bind the embedded application spec")
        if type(self.actual_block) is not ResponseBlock:
            raise TypeError("actual_block has the wrong strict type")
        if type(self.ablated_block) is not ResponseBlock:
            raise TypeError("ablated_block has the wrong strict type")
        if self.actual_block.branch != "actual":
            raise ValueError("actual_block has the wrong branch")
        if self.ablated_block.branch != "matched_ablated":
            raise ValueError("ablated_block has the wrong branch")
        spectrum = _finite_unit_tuple(
            self.survival_spectrum,
            "survival_spectrum",
        )
        measured = _side_tuple(
            self.measured_side_labels,
            "measured_side_labels",
        )
        expected = _side_tuple(
            self.expected_side_labels,
            "expected_side_labels",
        )
        margins = _finite_tuple(
            self.signed_threshold_margins,
            "signed_threshold_margins",
        )
        if not (
            len(spectrum) == len(measured) == len(expected) == len(margins)
        ):
            raise ValueError("survival audit vectors have different lengths")
        canonical_margins = tuple(
            float(item - SURVIVAL_THRESHOLD) for item in spectrum
        )
        if margins != canonical_margins:
            raise ValueError("signed threshold margins are not mechanical")
        minimum = _finite_float(
            self.minimum_absolute_margin,
            "minimum_absolute_margin",
        )
        if minimum < 0.0 or minimum != min(abs(item) for item in margins):
            raise ValueError("minimum_absolute_margin is not mechanical")
        _sha(self.audit_sha, "audit_sha")


def survival_threshold_instance_audit_payload(
    audit: SurvivalThresholdInstanceAudit,
) -> dict[str, object]:
    _preflight_tree(audit, "survival threshold instance audit")
    _exact_record(
        audit,
        SurvivalThresholdInstanceAudit,
        "survival threshold instance audit",
    )
    audit.__post_init__()
    return {
        "audit_schema_version": audit.audit_schema_version,
        "application_spec": _application_record(audit.application_spec),
        "permit": _permit_record(audit.permit),
        "actual_block": _block_record(audit.actual_block),
        "ablated_block": _block_record(audit.ablated_block),
        "survival_spectrum": list(audit.survival_spectrum),
        "measured_side_labels": list(audit.measured_side_labels),
        "expected_side_labels": list(audit.expected_side_labels),
        "signed_threshold_margins": list(audit.signed_threshold_margins),
        "minimum_absolute_margin": audit.minimum_absolute_margin,
    }


@dataclass(frozen=True)
class SurvivalThresholdControlEvidence:
    evidence_schema_version: str
    parent_freeze: ParentFreezeManifest
    instance_audits: tuple[SurvivalThresholdInstanceAudit, ...]
    evidence_sha: str

    def __post_init__(self) -> None:
        if self.evidence_schema_version != (
            SURVIVAL_THRESHOLD_CONTROL_EVIDENCE_SCHEMA_VERSION
        ):
            raise ValueError("survival threshold evidence schema is not frozen")
        if type(self.parent_freeze) is not ParentFreezeManifest:
            raise TypeError("parent_freeze has the wrong strict type")
        if type(self.instance_audits) is not tuple or not self.instance_audits:
            raise ValueError("instance_audits must be a non-empty tuple")
        if not all(
            type(item) is SurvivalThresholdInstanceAudit
            for item in self.instance_audits
        ):
            raise TypeError("instance_audits has a wrong strict record type")
        instance_ids = tuple(
            item.application_spec.application_instance_id
            for item in self.instance_audits
        )
        if len(frozenset(instance_ids)) != len(instance_ids):
            raise ValueError("survival threshold application instances repeat")
        parent_order = {
            item.application_instance_id: index
            for index, item in enumerate(
                self.parent_freeze.synthetic_control_application_specs
            )
        }
        try:
            ordinals = tuple(parent_order[item] for item in instance_ids)
        except KeyError as exc:
            raise ValueError(
                "survival threshold application is absent from ParentFreeze"
            ) from exc
        if ordinals != tuple(sorted(ordinals)):
            raise ValueError("instance_audits are not in ParentFreeze order")
        if any(
            item.permit.parent_freeze != self.parent_freeze
            for item in self.instance_audits
        ):
            raise ValueError("instance audit does not embed the common ParentFreeze")
        _sha(self.evidence_sha, "evidence_sha")


def survival_threshold_control_evidence_payload(
    evidence: SurvivalThresholdControlEvidence,
) -> dict[str, object]:
    _preflight_tree(evidence, "survival threshold control evidence")
    _exact_record(
        evidence,
        SurvivalThresholdControlEvidence,
        "survival threshold control evidence",
    )
    evidence.__post_init__()
    return {
        "evidence_schema_version": evidence.evidence_schema_version,
        "parent_freeze": _parent_record(evidence.parent_freeze),
        "instance_audits": [
            {
                **survival_threshold_instance_audit_payload(item),
                "audit_sha": item.audit_sha,
            }
            for item in evidence.instance_audits
        ],
    }


@dataclass(frozen=True)
class SurvivalThresholdCalibration:
    calibration_schema_version: str
    tau_surv: Literal[0.5]
    ambiguity_half_width: Literal[0.1]
    control_evidence: SurvivalThresholdControlEvidence
    calibration_sha: str

    def __post_init__(self) -> None:
        if self.calibration_schema_version != (
            SURVIVAL_THRESHOLD_CALIBRATION_SCHEMA_VERSION
        ):
            raise ValueError("survival threshold calibration schema is not frozen")
        if type(self.tau_surv) is not float or self.tau_surv != SURVIVAL_THRESHOLD:
            raise ValueError("tau_surv is not frozen at 0.5")
        if (
            type(self.ambiguity_half_width) is not float
            or self.ambiguity_half_width != SURVIVAL_AMBIGUITY_HALF_WIDTH
        ):
            raise ValueError("ambiguity_half_width is not frozen at 0.1")
        if type(self.control_evidence) is not SurvivalThresholdControlEvidence:
            raise TypeError("control_evidence has the wrong strict type")
        _sha(self.calibration_sha, "calibration_sha")


def survival_threshold_calibration_payload(
    calibration: SurvivalThresholdCalibration,
) -> dict[str, object]:
    _preflight_tree(calibration, "survival threshold calibration")
    _exact_record(
        calibration,
        SurvivalThresholdCalibration,
        "survival threshold calibration",
    )
    calibration.__post_init__()
    return {
        "calibration_schema_version": calibration.calibration_schema_version,
        "tau_surv": calibration.tau_surv,
        "ambiguity_half_width": calibration.ambiguity_half_width,
        "control_evidence": {
            **survival_threshold_control_evidence_payload(
                calibration.control_evidence
            ),
            "evidence_sha": calibration.control_evidence.evidence_sha,
        },
    }


@dataclass(frozen=True)
class CausalResult:
    survival_spectrum: tuple[float, ...]
    epsilon_dof: Optional[float]
    epsilon_cont: Optional[float]
    chi_extra: Optional[float]
    kappa_map: Optional[float]
    d_proc_sq: Optional[float]
    gain_ratio: Optional[float]
    phase_shift: Optional[float]
    ambiguous: bool

    def __post_init__(self) -> None:
        _finite_unit_tuple(self.survival_spectrum, "survival_spectrum")
        for name in (
            "epsilon_dof",
            "epsilon_cont",
            "chi_extra",
            "kappa_map",
            "d_proc_sq",
        ):
            value = getattr(self, name)
            if value is not None:
                number = _finite_float(value, name)
                if number < 0.0 or number > 1.0:
                    raise ValueError(f"{name} must lie inside [0,1]")
        for name in ("gain_ratio", "phase_shift"):
            value = getattr(self, name)
            if value is not None:
                _finite_float(value, name)
        if type(self.ambiguous) is not bool:
            raise TypeError("ambiguous must be an exact bool")
        if self.ambiguous != (self.epsilon_dof is None):
            raise ValueError("ambiguous and epsilon_dof do not agree")


def _side_label(value: float) -> Literal["below", "grey", "above"]:
    margin = value - SURVIVAL_THRESHOLD
    if abs(margin) < SURVIVAL_AMBIGUITY_HALF_WIDTH:
        return "grey"
    if margin < 0.0:
        return "below"
    return "above"


def _profile_labels(
    application: V3M0SyntheticControlApplicationSpec,
) -> tuple[Literal["below", "grey", "above"], ...]:
    labels = dict(
        application.expected_prediction_profile.expected_qualitative_labels
    )
    if application.control_case_id == "C04_CANONICAL_ANGLE_025_075":
        raw = labels.get("survival-side")
        if raw != ("below", "above"):
            raise ValueError("C04 ParentFreeze side labels are not frozen")
        return ("below", "above")
    if application.control_case_id == "C11_NULL_GREY_SIGNAL_AMPLITUDE":
        raw = labels.get("amplitude-regime")
        mapping = {
            "null": "below",
            "grey": "grey",
            "signal": "above",
        }
        if raw != ("null", "grey", "signal"):
            raise ValueError("C11 ParentFreeze amplitude labels are not frozen")
        return tuple(mapping[item] for item in raw)  # type: ignore[return-value]
    raise ValueError("permit is not a survival-threshold calibration control")


def _validate_response_pair(
    actual: ResponseBlock,
    ablated: ResponseBlock,
) -> None:
    if actual.branch != "actual" or ablated.branch != "matched_ablated":
        raise ValueError("causal inputs must be ordered actual then matched_ablated")
    for name in (
        "pair_sha",
        "paired_response_sha",
        "calibration_manifest_sha",
        "selected_fejer_order",
        "application_authority_sha",
        "operator_spec",
        "q_all",
    ):
        if getattr(actual, name) != getattr(ablated, name):
            raise ValueError(f"causal response pair has mismatched {name}")
    if (
        actual.source_readout_response.source_basis
        != ablated.source_readout_response.source_basis
        or actual.source_readout_response.readout_basis
        != ablated.source_readout_response.readout_basis
        or actual.source_readout_response.run_spec_sha
        != ablated.source_readout_response.run_spec_sha
    ):
        raise ValueError("causal branch response authority is not paired")


def _bind_pair_to_permit(
    actual: ResponseBlock,
    ablated: ResponseBlock,
    permit: CalibrationApplicationPermit,
    verified_permit: VerifiedCalibrationApplicationPermit,
) -> None:
    _validate_response_pair(actual, ablated)
    run_spec = build_v3m0_application_response_run_spec(
        verified_permit
    ).run_spec
    if (
        actual.source_readout_response.run_spec_sha != run_spec.run_spec_sha
        or ablated.source_readout_response.run_spec_sha != run_spec.run_spec_sha
    ):
        raise ValueError("response blocks are not bound to the permit run spec")
    if (
        actual.calibration_manifest_sha
        != permit.calibration_manifest.calibration_manifest_sha
        or actual.selected_fejer_order != permit.selected_fejer_order
        or actual.operator_spec.source_spec_sha
        != permit.readout_calibration_spec.spec_sha
    ):
        raise ValueError("response blocks are not bound to permit calibration")
    for block in (actual, ablated):
        response = block.source_readout_response
        if (
            response.source_basis != permit.source_basis
            or response.readout_basis != permit.readout_basis
        ):
            raise ValueError("response block basis differs from permit")


def _tensor_shape_header(
    tensor: object,
    field: str,
    *,
    ndim: int,
) -> tuple[int, ...]:
    try:
        shape = tensor.shape
    except AttributeError as exc:
        raise TypeError(f"{field} has no frozen tensor shape") from exc
    if (
        type(shape) is not tuple
        or len(shape) != ndim
        or any(type(size) is not int or size <= 0 for size in shape)
    ):
        raise ValueError(f"{field} has an invalid tensor shape")
    if math.prod(shape) > LINALG_ENTRY_CAP:
        raise ValueError(f"{field} exceeds the resource cap")
    return shape


def _causal_block_resource_preflight(
    actual: ResponseBlock,
    ablated: ResponseBlock,
) -> None:
    actual_shape = _tensor_shape_header(
        actual.source_readout_response.values,
        "actual response values",
        ndim=3,
    )
    ablated_shape = _tensor_shape_header(
        ablated.source_readout_response.values,
        "ablated response values",
        ndim=3,
    )
    if actual_shape != ablated_shape:
        raise ValueError("causal branch response shapes differ")
    n_k, n_readout, n_source = actual_shape
    incidence_shape = _tensor_shape_header(
        actual.operator_spec.curvature_incidence_operator,
        "curvature incidence operator",
        ndim=2,
    )
    curvature_shape = _tensor_shape_header(
        actual.operator_spec.curvature_metric_whitener,
        "curvature metric whitener",
        ndim=2,
    )
    if (
        incidence_shape[1] != n_readout
        or curvature_shape[0] != curvature_shape[1]
        or curvature_shape[1] != incidence_shape[0]
    ):
        raise ValueError("causal curvature operator shapes do not compose")
    curvature_rank = actual.audit.curvature_rank
    if type(curvature_rank) is not int or curvature_rank <= 0:
        raise ValueError("actual response block has no curvature mode")
    q_curv_shape = _tensor_shape_header(
        actual.q_curv,
        "actual q_curv",
        ndim=2,
    )
    q_all_shape = _tensor_shape_header(
        actual.q_all,
        "actual q_all",
        ndim=2,
    )
    if (
        q_curv_shape[0] != n_source
        or q_curv_shape[1] < curvature_rank
        or q_all_shape != (n_source, n_source)
    ):
        raise ValueError("causal source basis shapes do not compose")
    n_curvature = incidence_shape[0]
    observer_dimension = n_k * n_curvature
    if (
        observer_dimension * curvature_rank > LINALG_ENTRY_CAP
        or observer_dimension * n_source > LINALG_ENTRY_CAP
    ):
        raise ValueError("causal response matrix exceeds the resource cap")
    arithmetic_work = (
        3 * n_curvature**2 * n_readout
        + 3 * n_k * n_curvature * n_readout * n_source
        + n_k
        * n_curvature
        * n_source
        * (2 * curvature_rank + n_source)
    )
    if arithmetic_work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError("causal block transform exceeds the resource work cap")


def _curvature_response_rows(
    block: ResponseBlock,
    source_columns: np.ndarray,
) -> np.ndarray:
    values = frozen_tensor_array(block.source_readout_response.values)
    incidence = frozen_tensor_array(
        block.operator_spec.curvature_incidence_operator
    )
    curvature = frozen_tensor_array(
        block.operator_spec.curvature_metric_whitener
    )
    if (
        values.ndim != 3
        or source_columns.ndim != 2
        or values.shape[2] != source_columns.shape[0]
        or incidence.shape[1] != values.shape[1]
        or curvature.shape[0] != curvature.shape[1]
        or curvature.shape[1] != incidence.shape[0]
    ):
        raise ValueError("response block curvature dimensions do not compose")
    return np.concatenate(
        tuple(
            curvature @ incidence @ values[index] @ source_columns
            for index in range(values.shape[0])
        ),
        axis=0,
    ).astype(np.complex128, copy=False)


def _causal_spectrum_from_blocks(
    actual: ResponseBlock,
    ablated: ResponseBlock,
    *,
    absolute_signal_threshold: float,
    raw_noise_floor: float,
) -> CausalSpectrum:
    _validate_response_pair(actual, ablated)
    _causal_block_resource_preflight(actual, ablated)
    curvature_rank = actual.audit.curvature_rank
    q_curv = frozen_tensor_array(actual.q_curv)[:, :curvature_rank]
    q_all = frozen_tensor_array(actual.q_all)
    thresholds = CausalNumericalThresholds(
        absolute_signal_threshold=absolute_signal_threshold,
        raw_noise_floor=raw_noise_floor,
        relative_gap_min=float(SIGNAL_NOISE_RATIO_MIN),
        survival_threshold=SURVIVAL_THRESHOLD,
        survival_ambiguity_half_width=SURVIVAL_AMBIGUITY_HALF_WIDTH,
    )
    return compute_causal_spectrum(
        _curvature_response_rows(actual, q_curv),
        _curvature_response_rows(ablated, q_curv),
        _curvature_response_rows(ablated, q_all),
        thresholds=thresholds,
    )


def _instance_audit(
    actual: ResponseBlock,
    ablated: ResponseBlock,
    permit: CalibrationApplicationPermit,
) -> SurvivalThresholdInstanceAudit:
    spectrum = _causal_spectrum_from_blocks(
        actual,
        ablated,
        absolute_signal_threshold=permit.selection.curv_tau_sig,
        raw_noise_floor=permit.selection.curv_noise_ref,
    )
    values = spectrum.survival_spectrum
    measured = tuple(_side_label(value) for value in values)
    expected = _profile_labels(permit.application_spec)
    if len(measured) != len(expected):
        raise ValueError("measured survival spectrum has the wrong Parent rank")
    if measured != expected:
        raise ValueError("measured survival sides differ from ParentFreeze")
    margins = tuple(float(value - SURVIVAL_THRESHOLD) for value in values)
    provisional = SurvivalThresholdInstanceAudit(
        audit_schema_version=SURVIVAL_THRESHOLD_INSTANCE_AUDIT_SCHEMA_VERSION,
        application_spec=permit.application_spec,
        permit=permit,
        actual_block=actual,
        ablated_block=ablated,
        survival_spectrum=values,
        measured_side_labels=measured,
        expected_side_labels=expected,
        signed_threshold_margins=margins,
        minimum_absolute_margin=float(min(abs(item) for item in margins)),
        audit_sha=_ZERO_SHA,
    )
    return SurvivalThresholdInstanceAudit(
        **{
            **vars(provisional),
            "audit_sha": canonical_sha(
                survival_threshold_instance_audit_payload(provisional)
            ),
        }
    )


def _input_headers(
    blocks: object,
    permits: object,
) -> tuple[
    tuple[tuple[VerifiedResponseBlock, VerifiedResponseBlock], ...],
    tuple[VerifiedCalibrationApplicationPermit, ...],
]:
    if type(blocks) is not tuple or not blocks:
        raise ValueError("blocks must be a non-empty tuple")
    if type(permits) is not tuple:
        raise TypeError("permits must be a tuple")
    if len(blocks) != len(permits):
        raise ValueError("blocks and permits must have the same length")
    for index, pair in enumerate(blocks):
        if type(pair) is not tuple or len(pair) != 2:
            raise TypeError(f"blocks[{index}] must be an exact two-block tuple")
        for branch_index, block in enumerate(pair):
            if type(block) is not VerifiedResponseBlock:
                raise TypeError(
                    f"blocks[{index}][{branch_index}] must be a "
                    "VerifiedResponseBlock"
                )
    for index, permit in enumerate(permits):
        if type(permit) is not VerifiedCalibrationApplicationPermit:
            raise TypeError(
                f"permits[{index}] must be a "
                "VerifiedCalibrationApplicationPermit"
            )
    return blocks, permits


def _expected_survival_threshold_calibration(
    blocks: tuple[tuple[VerifiedResponseBlock, VerifiedResponseBlock], ...],
    permits: tuple[VerifiedCalibrationApplicationPermit, ...],
) -> SurvivalThresholdCalibration:
    checked_blocks, checked_permits = _input_headers(blocks, permits)
    rows: list[
        tuple[
            int,
            ResponseBlock,
            ResponseBlock,
            CalibrationApplicationPermit,
        ]
    ] = []
    parent: Optional[ParentFreezeManifest] = None
    parent_order: dict[str, int] = {}
    calibration_sha: Optional[str] = None
    seen_cases: set[str] = set()
    for index, (pair, verified_permit) in enumerate(
        zip(checked_blocks, checked_permits)
    ):
        actual = _reverify_verified_response_block(pair[0]).block
        ablated = _reverify_verified_response_block(pair[1]).block
        permit = _reverify_verified_calibration_application_permit(
            verified_permit
        ).permit
        _bind_pair_to_permit(actual, ablated, permit, verified_permit)
        case = permit.application_spec.control_case_id
        if case == _UNENCODABLE_SURVIVAL_THRESHOLD_CONTROL:
            raise ValueError(
                "C11 grey activation is undefined before K_surv and cannot "
                "be encoded by the all-float Task 13 audit schema"
            )
        if case not in _REQUIRED_SURVIVAL_THRESHOLD_CONTROLS:
            raise ValueError(
                "survival threshold calibration accepts only C04"
            )
        if case in seen_cases:
            raise ValueError("survival threshold control case repeats")
        seen_cases.add(case)
        if parent is None:
            parent = permit.parent_freeze
            parent_order = {
                item.application_instance_id: ordinal
                for ordinal, item in enumerate(
                    parent.synthetic_control_application_specs
                )
            }
            calibration_sha = (
                permit.calibration_manifest.calibration_manifest_sha
            )
        elif permit.parent_freeze != parent:
            raise ValueError("survival threshold permits have different parents")
        if (
            permit.calibration_manifest.calibration_manifest_sha
            != calibration_sha
        ):
            raise ValueError(
                "survival threshold permits have different calibrations"
            )
        instance_id = permit.application_spec.application_instance_id
        if instance_id not in parent_order:
            raise ValueError("permit application is absent from ParentFreeze")
        rows.append(
            (
                parent_order[instance_id],
                actual,
                ablated,
                permit,
            )
        )
        del index
    if seen_cases != set(_REQUIRED_SURVIVAL_THRESHOLD_CONTROLS):
        raise ValueError("survival threshold calibration requires C04")
    if parent is None:
        raise ValueError("survival threshold controls are empty")
    audits = tuple(
        _instance_audit(actual, ablated, permit)
        for _, actual, ablated, permit in sorted(rows, key=lambda item: item[0])
    )
    provisional_evidence = SurvivalThresholdControlEvidence(
        evidence_schema_version=(
            SURVIVAL_THRESHOLD_CONTROL_EVIDENCE_SCHEMA_VERSION
        ),
        parent_freeze=parent,
        instance_audits=audits,
        evidence_sha=_ZERO_SHA,
    )
    evidence = SurvivalThresholdControlEvidence(
        **{
            **vars(provisional_evidence),
            "evidence_sha": canonical_sha(
                survival_threshold_control_evidence_payload(
                    provisional_evidence
                )
            ),
        }
    )
    provisional = SurvivalThresholdCalibration(
        calibration_schema_version=SURVIVAL_THRESHOLD_CALIBRATION_SCHEMA_VERSION,
        tau_surv=SURVIVAL_THRESHOLD,
        ambiguity_half_width=SURVIVAL_AMBIGUITY_HALF_WIDTH,
        control_evidence=evidence,
        calibration_sha=_ZERO_SHA,
    )
    return SurvivalThresholdCalibration(
        **{
            **vars(provisional),
            "calibration_sha": canonical_sha(
                survival_threshold_calibration_payload(provisional)
            ),
        }
    )


@dataclass(frozen=True)
class _SurvivalThresholdAuthority:
    blocks: tuple[tuple[VerifiedResponseBlock, VerifiedResponseBlock], ...]
    permits: tuple[VerifiedCalibrationApplicationPermit, ...]
    calibration: SurvivalThresholdCalibration
    digest: str
    seal: str


class VerifiedSurvivalThresholdCalibration:
    """Opaque live authority for the frozen survival threshold."""

    __slots__ = ("__calibration", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        calibration: SurvivalThresholdCalibration,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError(
                "VerifiedSurvivalThresholdCalibration is module-issued only"
            )
        object.__setattr__(
            self,
            "_VerifiedSurvivalThresholdCalibration__calibration",
            calibration,
        )
        object.__setattr__(
            self,
            "_VerifiedSurvivalThresholdCalibration__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedSurvivalThresholdCalibration__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("survival threshold authority is immutable")

    @property
    def calibration(self) -> SurvivalThresholdCalibration:
        return _reverify_verified_survival_threshold_calibration(self)


_SURVIVAL_THRESHOLD_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedSurvivalThresholdCalibration],
        _SurvivalThresholdAuthority,
    ],
] = {}
_SURVIVAL_THRESHOLD_LOCK = threading.RLock()


def _issue_survival_threshold_calibration(
    calibration: SurvivalThresholdCalibration,
    blocks: tuple[tuple[VerifiedResponseBlock, VerifiedResponseBlock], ...],
    permits: tuple[VerifiedCalibrationApplicationPermit, ...],
) -> VerifiedSurvivalThresholdCalibration:
    digest = canonical_sha(survival_threshold_calibration_payload(calibration))
    if digest != calibration.calibration_sha:
        raise ValueError("survival threshold calibration self-hash mismatch")
    seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-survival-threshold-calibration.v1"
            ),
            "calibration_sha": calibration.calibration_sha,
            "body_digest": digest,
        }
    )
    wrapper = VerifiedSurvivalThresholdCalibration(
        _ISSUANCE_TOKEN,
        calibration,
        seal,
    )
    identity = id(wrapper)
    authority = _SurvivalThresholdAuthority(
        blocks=blocks,
        permits=permits,
        calibration=calibration,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[VerifiedSurvivalThresholdCalibration],
        wrapper_id: int = identity,
    ) -> None:
        with _SURVIVAL_THRESHOLD_LOCK:
            current = _SURVIVAL_THRESHOLD_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _SURVIVAL_THRESHOLD_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _SURVIVAL_THRESHOLD_LOCK:
        _SURVIVAL_THRESHOLD_LIVE[identity] = (reference, authority)
    return wrapper


def _reverify_verified_survival_threshold_calibration(
    wrapper: VerifiedSurvivalThresholdCalibration,
) -> SurvivalThresholdCalibration:
    if type(wrapper) is not VerifiedSurvivalThresholdCalibration:
        raise TypeError(
            "consumer requires a live VerifiedSurvivalThresholdCalibration"
        )
    with _SURVIVAL_THRESHOLD_LOCK:
        current = _SURVIVAL_THRESHOLD_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("survival threshold authority identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedSurvivalThresholdCalibration__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedSurvivalThresholdCalibration__calibration",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedSurvivalThresholdCalibration__seal",
        )
    except AttributeError as exc:
        raise ValueError("survival threshold authority record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("survival threshold authority token mismatch")
    expected = _expected_survival_threshold_calibration(
        authority.blocks,
        authority.permits,
    )
    raw_digest = canonical_sha(survival_threshold_calibration_payload(raw))
    expected_digest = canonical_sha(
        survival_threshold_calibration_payload(expected)
    )
    expected_seal = canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-survival-threshold-calibration.v1"
            ),
            "calibration_sha": expected.calibration_sha,
            "body_digest": expected_digest,
        }
    )
    if (
        raw_digest != authority.digest
        or expected_digest != authority.digest
        or expected != authority.calibration
        or raw != authority.calibration
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("survival threshold immutable seal mismatch")
    return expected


def calibrate_survival_threshold(
    blocks: tuple[tuple[VerifiedResponseBlock, VerifiedResponseBlock], ...],
    permits: tuple[VerifiedCalibrationApplicationPermit, ...],
) -> VerifiedSurvivalThresholdCalibration:
    checked_blocks, checked_permits = _input_headers(blocks, permits)
    expected = _expected_survival_threshold_calibration(
        checked_blocks,
        checked_permits,
    )
    return _issue_survival_threshold_calibration(
        expected,
        checked_blocks,
        checked_permits,
    )


def verify_survival_threshold_calibration(
    raw: SurvivalThresholdCalibration,
    blocks: tuple[tuple[VerifiedResponseBlock, VerifiedResponseBlock], ...],
    permits: tuple[VerifiedCalibrationApplicationPermit, ...],
) -> VerifiedSurvivalThresholdCalibration:
    _preflight_tree(raw, "raw survival threshold calibration")
    _exact_record(
        raw,
        SurvivalThresholdCalibration,
        "raw survival threshold calibration",
    )
    checked_blocks, checked_permits = _input_headers(blocks, permits)
    expected = _expected_survival_threshold_calibration(
        checked_blocks,
        checked_permits,
    )
    if raw != expected:
        raise ValueError("raw survival threshold calibration differs from replay")
    if raw.calibration_sha != canonical_sha(
        survival_threshold_calibration_payload(raw)
    ):
        raise ValueError("raw survival threshold calibration hash mismatch")
    return _issue_survival_threshold_calibration(
        expected,
        checked_blocks,
        checked_permits,
    )


def compute_causal_survival(
    actual: VerifiedResponseBlock,
    ablated: VerifiedResponseBlock,
    threshold: VerifiedSurvivalThresholdCalibration,
) -> CausalResult:
    if type(actual) is not VerifiedResponseBlock:
        raise TypeError("actual must be a VerifiedResponseBlock")
    if type(ablated) is not VerifiedResponseBlock:
        raise TypeError("ablated must be a VerifiedResponseBlock")
    if type(threshold) is not VerifiedSurvivalThresholdCalibration:
        raise TypeError(
            "threshold must be a VerifiedSurvivalThresholdCalibration"
        )
    actual_raw = _reverify_verified_response_block(actual).block
    ablated_raw = _reverify_verified_response_block(ablated).block
    calibration = _reverify_verified_survival_threshold_calibration(threshold)
    audits = calibration.control_evidence.instance_audits
    if not audits:
        raise ValueError("survival threshold calibration has no control evidence")
    selection = audits[0].permit.selection
    calibration_sha = audits[0].permit.calibration_manifest.calibration_manifest_sha
    if any(
        item.permit.selection != selection
        or item.permit.calibration_manifest.calibration_manifest_sha
        != calibration_sha
        for item in audits
    ):
        raise ValueError("survival threshold control calibration is inconsistent")
    if (
        actual_raw.calibration_manifest_sha != calibration_sha
        or ablated_raw.calibration_manifest_sha != calibration_sha
    ):
        raise ValueError("response blocks use a different window calibration")
    spectrum = _causal_spectrum_from_blocks(
        actual_raw,
        ablated_raw,
        absolute_signal_threshold=selection.curv_tau_sig,
        raw_noise_floor=selection.curv_noise_ref,
    )
    return CausalResult(
        survival_spectrum=spectrum.survival_spectrum,
        epsilon_dof=spectrum.epsilon_dof,
        epsilon_cont=spectrum.epsilon_cont,
        chi_extra=spectrum.chi_extra,
        kappa_map=spectrum.kappa_map,
        d_proc_sq=spectrum.d_proc_sq,
        gain_ratio=spectrum.gain_ratio,
        phase_shift=spectrum.phase_shift,
        ambiguous=spectrum.ambiguous,
    )


__all__ = [
    "CAUSAL_HERMITIAN_TOLERANCE",
    "CausalNumericalThresholds",
    "CausalResult",
    "CausalSpectrum",
    "SURVIVAL_AMBIGUITY_HALF_WIDTH",
    "SURVIVAL_THRESHOLD",
    "SURVIVAL_THRESHOLD_CALIBRATION_SCHEMA_VERSION",
    "SURVIVAL_THRESHOLD_CONTROL_EVIDENCE_SCHEMA_VERSION",
    "SURVIVAL_THRESHOLD_INSTANCE_AUDIT_SCHEMA_VERSION",
    "SurvivalThresholdCalibration",
    "SurvivalThresholdControlEvidence",
    "SurvivalThresholdInstanceAudit",
    "VerifiedSurvivalThresholdCalibration",
    "calibrate_survival_threshold",
    "compute_causal_spectrum",
    "compute_causal_survival",
    "survival_threshold_calibration_payload",
    "survival_threshold_control_evidence_payload",
    "survival_threshold_instance_audit_payload",
    "verify_survival_threshold_calibration",
]
