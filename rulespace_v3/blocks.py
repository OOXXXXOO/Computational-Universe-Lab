"""Branch-specific, calibration-bound response blocks for V3-M0.

The public builders accept no caller-supplied metric, incidence operator, or
threshold.  Every numerical object is derived from the readout calibration
spec bound to the selected response (or, later, an application permit), and
all five matrices are independently frozen into the raw evidence body.
"""

from __future__ import annotations

import copy
import math
import threading
import weakref
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from .calibration_authority import (
    APPLICATION_READOUT_DERIVATION_ID,
    VerifiedCalibrationApplicationPermit,
    VerifiedWindowThresholdCalibration,
    _preflight_tree,
    _reverify_verified_calibration_application_permit,
    _reverify_verified_window_threshold_calibration,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
)
from .linalg import (
    LINALG_ARITHMETIC_WORK_CAP,
    LINALG_ENTRY_CAP,
    canonical_orthonormal_columns,
    hermitian_positive_whitener,
)
from .registry import (
    ControlReadoutCalibrationSpec,
    readout_calibration_spec_payload,
)
from .response import (
    SourceReadoutResponse,
    VerifiedPairedResponseOutcome,
    _reverify_verified_paired_response_outcome,
    source_readout_response_payload,
)


RESPONSE_BLOCK_OPERATOR_SPEC_SCHEMA_VERSION = "v3m0.response-block-operator-spec.v1"
RESPONSE_BLOCK_AUDIT_SCHEMA_VERSION = "v3m0.response-block-audit.v1"
RESPONSE_BLOCK_SCHEMA_VERSION = "v3m0.response-block.v1"
_ZERO_SHA = "0" * 64
_ISSUANCE_TOKEN = object()
_AUDIT_TOLERANCE = 1.0e-12


def _sha(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _finite_nonnegative(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{field} must be finite and non-negative")
    return value


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be a positive exact int")
    return value


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative exact int")
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


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


def _response_record(response: SourceReadoutResponse) -> dict[str, object]:
    return {
        **source_readout_response_payload(response),
        "response_sha": response.response_sha,
    }


@dataclass(frozen=True)
class ResponseBlockOperatorSpec:
    spec_schema_version: str
    source_metric_whitener: FrozenComplexTensor
    h_metric_whitener: FrozenComplexTensor
    curvature_incidence_operator: FrozenComplexTensor
    curvature_metric_whitener: FrozenComplexTensor
    curvature_normalizer_id: str
    derivation_id: Literal["control-readout-calibration-spec-recursive-v1"]
    source_spec_sha: str
    spec_sha: str

    def __post_init__(self) -> None:
        if self.spec_schema_version != (RESPONSE_BLOCK_OPERATOR_SPEC_SCHEMA_VERSION):
            raise ValueError("response block operator schema is not frozen")
        for name in (
            "source_metric_whitener",
            "h_metric_whitener",
            "curvature_incidence_operator",
            "curvature_metric_whitener",
        ):
            if type(getattr(self, name)) is not FrozenComplexTensor:
                raise TypeError(f"{name} has the wrong strict tensor type")
        if (
            type(self.curvature_normalizer_id) is not str
            or not self.curvature_normalizer_id
        ):
            raise ValueError("curvature_normalizer_id must be non-empty")
        if self.derivation_id != APPLICATION_READOUT_DERIVATION_ID:
            raise ValueError("response block operator derivation is not frozen")
        _sha(self.source_spec_sha, "source_spec_sha")
        _sha(self.spec_sha, "spec_sha")


def response_block_operator_spec_payload(
    spec: ResponseBlockOperatorSpec,
) -> dict[str, object]:
    _preflight_tree(spec, "response block operator spec")
    _exact_record(
        spec,
        ResponseBlockOperatorSpec,
        "response block operator spec",
    )
    return {
        "spec_schema_version": spec.spec_schema_version,
        "source_metric_whitener": _tensor_record(spec.source_metric_whitener),
        "h_metric_whitener": _tensor_record(spec.h_metric_whitener),
        "curvature_incidence_operator": _tensor_record(
            spec.curvature_incidence_operator
        ),
        "curvature_metric_whitener": _tensor_record(spec.curvature_metric_whitener),
        "curvature_normalizer_id": spec.curvature_normalizer_id,
        "derivation_id": spec.derivation_id,
        "source_spec_sha": spec.source_spec_sha,
    }


@dataclass(frozen=True)
class ResponseBlockAudit:
    audit_schema_version: str
    q_all_orth_residual: float
    q_active_orth_residual: float
    curvature_hermitian_residual: float
    q_curv_orth_residual: float
    s_curv_hermitian_residual: float
    source_metric_min_lower: float
    h_metric_min_lower: float
    curvature_metric_min_lower: float
    active_rank: int
    curvature_rank: int
    audit_sha: str

    def __post_init__(self) -> None:
        if self.audit_schema_version != RESPONSE_BLOCK_AUDIT_SCHEMA_VERSION:
            raise ValueError("response block audit schema is not frozen")
        for name in (
            "q_all_orth_residual",
            "q_active_orth_residual",
            "curvature_hermitian_residual",
            "q_curv_orth_residual",
            "s_curv_hermitian_residual",
            "source_metric_min_lower",
            "h_metric_min_lower",
            "curvature_metric_min_lower",
        ):
            _finite_nonnegative(getattr(self, name), name)
        _nonnegative_int(self.active_rank, "active_rank")
        _nonnegative_int(self.curvature_rank, "curvature_rank")
        if self.curvature_rank > self.active_rank:
            raise ValueError("curvature rank exceeds source-active rank")
        _sha(self.audit_sha, "audit_sha")


def response_block_audit_payload(
    audit: ResponseBlockAudit,
) -> dict[str, object]:
    _preflight_tree(audit, "response block audit")
    _exact_record(audit, ResponseBlockAudit, "response block audit")
    return {
        name: getattr(audit, name)
        for name in tuple(ResponseBlockAudit.__dataclass_fields__)[:-1]
    }


@dataclass(frozen=True)
class ResponseBlock:
    block_schema_version: str
    branch: Literal["actual", "matched_ablated"]
    source_readout_response: SourceReadoutResponse
    response_sha: str
    pair_sha: str
    operator_spec: ResponseBlockOperatorSpec
    q_all: FrozenComplexTensor
    q_active: FrozenComplexTensor
    v_curv: FrozenComplexTensor
    q_curv: FrozenComplexTensor
    s_curv: FrozenComplexTensor
    audit: ResponseBlockAudit
    paired_response_sha: str
    calibration_manifest_sha: str
    selected_fejer_order: int
    application_authority_sha: str
    block_sha: str

    def __post_init__(self) -> None:
        if self.block_schema_version != RESPONSE_BLOCK_SCHEMA_VERSION:
            raise ValueError("response block schema is not frozen")
        if self.branch not in ("actual", "matched_ablated"):
            raise ValueError("response block branch is not frozen")
        if type(self.source_readout_response) is not SourceReadoutResponse:
            raise TypeError("source_readout_response has the wrong strict type")
        if self.source_readout_response.branch != self.branch:
            raise ValueError("branch response is not branch-specific")
        for name in (
            "response_sha",
            "pair_sha",
            "paired_response_sha",
            "calibration_manifest_sha",
            "application_authority_sha",
            "block_sha",
        ):
            _sha(getattr(self, name), name)
        if type(self.operator_spec) is not ResponseBlockOperatorSpec:
            raise TypeError("operator_spec has the wrong strict type")
        for name in ("q_all", "q_active", "v_curv", "q_curv", "s_curv"):
            if type(getattr(self, name)) is not FrozenComplexTensor:
                raise TypeError(f"{name} has the wrong strict tensor type")
        if type(self.audit) is not ResponseBlockAudit:
            raise TypeError("audit has the wrong strict type")
        _positive_int(self.selected_fejer_order, "selected_fejer_order")


def response_block_payload(block: ResponseBlock) -> dict[str, object]:
    _preflight_tree(block, "response block")
    _exact_record(block, ResponseBlock, "response block")
    _validate_response_block_body(block)
    return {
        "block_schema_version": block.block_schema_version,
        "branch": block.branch,
        "source_readout_response": _response_record(block.source_readout_response),
        "response_sha": block.response_sha,
        "pair_sha": block.pair_sha,
        "operator_spec": {
            **response_block_operator_spec_payload(block.operator_spec),
            "spec_sha": block.operator_spec.spec_sha,
        },
        "q_all": _tensor_record(block.q_all),
        "q_active": _tensor_record(block.q_active),
        "v_curv": _tensor_record(block.v_curv),
        "q_curv": _tensor_record(block.q_curv),
        "s_curv": _tensor_record(block.s_curv),
        "audit": {
            **response_block_audit_payload(block.audit),
            "audit_sha": block.audit.audit_sha,
        },
        "paired_response_sha": block.paired_response_sha,
        "calibration_manifest_sha": block.calibration_manifest_sha,
        "selected_fejer_order": block.selected_fejer_order,
        "application_authority_sha": block.application_authority_sha,
    }


def _validate_response_block_body(block: ResponseBlock) -> None:
    """Replay nested hashes, rank shapes, and the zero-rank storage rule."""

    block.__post_init__()
    response = block.source_readout_response
    if response.response_sha != canonical_sha(
        source_readout_response_payload(response)
    ):
        raise ValueError("branch response SHA does not match full body")
    if block.response_sha != response.response_sha:
        raise ValueError("response_sha does not bind the branch response")
    operator = block.operator_spec
    if operator.spec_sha != canonical_sha(
        response_block_operator_spec_payload(operator)
    ):
        raise ValueError("operator spec SHA does not match full body")
    source_spec = ControlReadoutCalibrationSpec(
        spec_schema_version="v3m0.control-readout-calibration-spec.v1",
        source_metric_whitener=operator.source_metric_whitener,
        h_metric_whitener=operator.h_metric_whitener,
        curvature_incidence_operator=operator.curvature_incidence_operator,
        curvature_metric_whitener=operator.curvature_metric_whitener,
        curvature_normalizer_id=operator.curvature_normalizer_id,
        spec_sha=operator.source_spec_sha,
    )
    if source_spec.spec_sha != canonical_sha(
        readout_calibration_spec_payload(source_spec)
    ):
        raise ValueError("operator source_spec_sha does not match full body")
    audit = block.audit
    if audit.audit_sha != canonical_sha(response_block_audit_payload(audit)):
        raise ValueError("response block audit SHA does not match full body")
    if any(
        getattr(audit, field) > _AUDIT_TOLERANCE
        for field in (
            "q_all_orth_residual",
            "q_active_orth_residual",
            "curvature_hermitian_residual",
            "q_curv_orth_residual",
            "s_curv_hermitian_residual",
        )
    ):
        raise ValueError("response block audit residual exceeds 1e-12")
    if any(
        getattr(audit, field) <= 0.0
        for field in (
            "source_metric_min_lower",
            "h_metric_min_lower",
            "curvature_metric_min_lower",
        )
    ):
        raise ValueError("response block metric lower bound is not positive")
    response_shape = response.values.shape
    if len(response_shape) != 3:
        raise ValueError("branch response values are not rank-three")
    n_k, n_readout, n_source = response_shape
    active_storage = max(1, audit.active_rank)
    curvature_storage = max(1, audit.curvature_rank)
    expected_shapes = {
        "q_all": (n_source, n_source),
        "q_active": (n_source, active_storage),
        "v_curv": (active_storage, curvature_storage),
        "q_curv": (n_source, curvature_storage),
        "s_curv": (n_k * n_readout, curvature_storage),
    }
    for name, expected_shape in expected_shapes.items():
        tensor = getattr(block, name)
        if tensor.shape != expected_shape:
            raise ValueError(f"{name} storage shape/rank mismatch")
    if audit.active_rank == 0:
        for name in ("q_active", "v_curv", "q_curv", "s_curv"):
            if bool(np.any(frozen_tensor_array(getattr(block, name)) != 0.0)):
                raise ValueError(f"{name} zero-rank padding is not exact zero")
    elif audit.curvature_rank == 0:
        for name in ("v_curv", "q_curv", "s_curv"):
            if bool(np.any(frozen_tensor_array(getattr(block, name)) != 0.0)):
                raise ValueError(f"{name} zero-rank padding is not exact zero")


def _spectral_norm(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    result = float(np.linalg.norm(values, ord=2))
    if not math.isfinite(result):
        raise ValueError("response block residual left the finite range")
    return result


def _strict_response_values(values: object) -> np.ndarray:
    if type(values) is not np.ndarray:
        raise TypeError("response values must be an exact numpy.ndarray")
    if values.dtype != np.dtype(np.complex128):
        raise TypeError("response values must be complex128")
    if values.ndim != 3 or any(size <= 0 for size in values.shape):
        raise ValueError("response values must have shape (n_k,n_readout,n_source)")
    if math.prod(values.shape) > LINALG_ENTRY_CAP:
        raise ValueError("response values exceed the matrix resource cap")
    if not bool(np.all(np.isfinite(values))):
        raise ValueError("response values must be finite")
    return np.array(values, dtype=np.complex128, copy=True, order="C")


def _operator_matrix(
    tensor: FrozenComplexTensor,
    field: str,
) -> np.ndarray:
    values = frozen_tensor_array(tensor)
    if values.ndim != 2 or any(size <= 0 for size in values.shape):
        raise ValueError(f"{field} must be a non-empty matrix")
    if math.prod(values.shape) > LINALG_ENTRY_CAP:
        raise ValueError(f"{field} exceeds the matrix resource cap")
    return values


def _validate_operator_spec(
    spec: ControlReadoutCalibrationSpec,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    _preflight_tree(spec, "control readout calibration spec")
    _exact_record(
        spec,
        ControlReadoutCalibrationSpec,
        "control readout calibration spec",
    )
    if spec.spec_sha != canonical_sha(readout_calibration_spec_payload(spec)):
        raise ValueError("readout calibration spec self-hash mismatch")
    if spec.curvature_normalizer_id != "synthetic-identity-v1":
        raise ValueError("Task 12 only implements the frozen synthetic normalizer")
    source = _operator_matrix(
        spec.source_metric_whitener,
        "source_metric_whitener",
    )
    readout = _operator_matrix(
        spec.h_metric_whitener,
        "h_metric_whitener",
    )
    incidence = _operator_matrix(
        spec.curvature_incidence_operator,
        "curvature_incidence_operator",
    )
    curvature = _operator_matrix(
        spec.curvature_metric_whitener,
        "curvature_metric_whitener",
    )
    if source.shape[0] != source.shape[1]:
        raise ValueError("source metric whitener must be square")
    if readout.shape[0] != readout.shape[1]:
        raise ValueError("h metric whitener must be square")
    if curvature.shape[0] != curvature.shape[1]:
        raise ValueError("curvature metric whitener must be square")
    if incidence.shape[1] != readout.shape[0]:
        raise ValueError("curvature incidence readout dimension mismatch")
    if incidence.shape[0] != curvature.shape[0]:
        raise ValueError("curvature metric dimension mismatch")
    # A metric-null direction is not silently clipped.  Task 12's current
    # readout specs contain no quotient map, so all three declared whiteners
    # must themselves be Hermitian positive and invertible.
    for matrix, field in (
        (source, "source metric whitener"),
        (readout, "h metric whitener"),
        (curvature, "curvature metric whitener"),
    ):
        try:
            hermitian_positive_whitener(
                matrix,
                hermitian_tolerance=_AUDIT_TOLERANCE,
                minimum_positive_eigenvalue=0.0,
            )
        except ValueError as exc:
            raise ValueError(
                f"{field} is not positive/invertible; an explicit quotient "
                "is required for metric-null directions"
            ) from exc
    return source, readout, incidence, curvature


def _operator_shape_headers(
    spec: ControlReadoutCalibrationSpec,
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Read only exact tensor headers for aggregate work preflight."""

    _exact_record(
        spec,
        ControlReadoutCalibrationSpec,
        "control readout calibration spec",
    )
    result: list[tuple[int, int]] = []
    for name in (
        "source_metric_whitener",
        "h_metric_whitener",
        "curvature_incidence_operator",
        "curvature_metric_whitener",
    ):
        tensor = getattr(spec, name)
        _exact_record(tensor, FrozenComplexTensor, name)
        if (
            type(tensor.shape) is not tuple
            or len(tensor.shape) != 2
            or any(type(size) is not int or size <= 0 for size in tensor.shape)
        ):
            raise ValueError(f"{name} must have a positive matrix shape")
        if math.prod(tensor.shape) > LINALG_ENTRY_CAP:
            raise ValueError(f"{name} exceeds the matrix resource cap")
        result.append(tensor.shape)
    source_shape, h_shape, incidence_shape, curvature_shape = result
    if source_shape[0] != source_shape[1]:
        raise ValueError("source metric whitener must be square")
    if h_shape[0] != h_shape[1]:
        raise ValueError("h metric whitener must be square")
    if curvature_shape[0] != curvature_shape[1]:
        raise ValueError("curvature metric whitener must be square")
    if incidence_shape[1] != h_shape[0]:
        raise ValueError("curvature incidence readout dimension mismatch")
    if incidence_shape[0] != curvature_shape[0]:
        raise ValueError("curvature metric dimension mismatch")
    return source_shape, h_shape, incidence_shape, curvature_shape


@dataclass(frozen=True)
class _ResponseBlockMatrices:
    q_all: np.ndarray
    q_active: np.ndarray
    v_curv: np.ndarray
    q_curv: np.ndarray
    s_curv: np.ndarray
    q_all_orth_residual: float
    q_active_orth_residual: float
    curvature_hermitian_residual: float
    q_curv_orth_residual: float
    s_curv_hermitian_residual: float
    source_metric_min_lower: float
    h_metric_min_lower: float
    curvature_metric_min_lower: float
    active_rank: int
    curvature_rank: int


def _metric_minimum(whitener: np.ndarray) -> float:
    metric = whitener.conj().T @ whitener
    hermitian = _spectral_norm(metric - metric.conj().T)
    if hermitian > _AUDIT_TOLERANCE:
        raise ValueError("derived metric is not Hermitian")
    eigenvalues = np.linalg.eigvalsh(metric)
    if not bool(np.all(np.isfinite(eigenvalues))):
        raise ValueError("derived metric spectrum left the finite range")
    minimum = float(eigenvalues[0])
    if minimum <= 0.0:
        raise ValueError("derived metric is not strictly positive")
    return minimum


def _orth_residual(
    whitened_basis: np.ndarray,
) -> float:
    rank = whitened_basis.shape[1]
    identity = np.eye(rank, dtype=np.complex128)
    return _spectral_norm(whitened_basis.conj().T @ whitened_basis - identity)


def _derive_response_block_matrices(
    response_values: np.ndarray,
    readout_spec: ControlReadoutCalibrationSpec,
    *,
    h_signal_threshold: float,
    curvature_signal_threshold: float,
) -> _ResponseBlockMatrices:
    """Mechanical ``Q_all→Q_active→Vcurv→Qcurv→Scurv`` derivation."""

    if (
        type(h_signal_threshold) is not float
        or not math.isfinite(h_signal_threshold)
        or h_signal_threshold <= 0.0
    ):
        raise ValueError("h_signal_threshold must be finite and positive")
    if (
        type(curvature_signal_threshold) is not float
        or not math.isfinite(curvature_signal_threshold)
        or curvature_signal_threshold <= 0.0
    ):
        raise ValueError("curvature_signal_threshold must be finite and positive")
    values = _strict_response_values(response_values)
    source_shape, h_shape, incidence_shape, _ = _operator_shape_headers(readout_spec)
    n_k, n_readout, n_source = values.shape
    if source_shape != (n_source, n_source):
        raise ValueError("source metric dimension does not match response")
    if h_shape != (n_readout, n_readout):
        raise ValueError("h metric dimension does not match response")
    n_curvature = incidence_shape[0]
    # Conservative aggregate preflight: three spectral validations, inverse,
    # response multiplications, two source-space SVDs, and one output-space
    # orthogonalization.
    work = (
        30 * (n_source**3 + n_readout**3 + n_curvature**3)
        + 12 * n_k * n_readout * n_source**2
        + 12 * n_k * n_curvature * n_source**2
        + 12 * (n_k * n_readout) * n_source**2
        + 12 * (n_k * n_curvature) * n_source**2
    )
    if work > LINALG_ARITHMETIC_WORK_CAP:
        raise ValueError("response block exceeds the arithmetic work cap")
    source, h_metric, incidence, curvature_metric = _validate_operator_spec(
        readout_spec
    )

    try:
        q_all = np.linalg.inv(source)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "source metric whitener is not invertible; explicit quotient required"
        ) from exc
    if not bool(np.all(np.isfinite(q_all))):
        raise ValueError("source canonical basis left the finite range")
    source_identity = source @ q_all
    q_all_residual = _orth_residual(source_identity)

    h_rows = np.concatenate(
        tuple(h_metric @ values[index] @ q_all for index in range(n_k)),
        axis=0,
    )
    active_coordinates = canonical_orthonormal_columns(
        h_rows.conj().T,
        absolute_threshold=h_signal_threshold,
    )
    q_active = q_all @ active_coordinates
    active_whitened = source @ q_active
    q_active_residual = _orth_residual(active_whitened)
    active_rank = q_active.shape[1]

    curvature_rows = np.concatenate(
        tuple(
            curvature_metric @ incidence @ values[index] @ q_active
            for index in range(n_k)
        ),
        axis=0,
    )
    curvature_gram = curvature_rows.conj().T @ curvature_rows
    curvature_hermitian = _spectral_norm(curvature_gram - curvature_gram.conj().T)
    if active_rank == 0:
        v_curv = np.zeros((0, 0), dtype=np.complex128)
    else:
        v_curv = canonical_orthonormal_columns(
            curvature_rows.conj().T,
            absolute_threshold=curvature_signal_threshold,
        )
    q_curv = q_active @ v_curv
    q_curv_residual = _orth_residual(source @ q_curv)
    curvature_rank = q_curv.shape[1]

    if curvature_rank == 0:
        s_curv = np.zeros(
            (n_k * n_readout, 0),
            dtype=np.complex128,
        )
    else:
        selected_h_rows = np.concatenate(
            tuple(h_metric @ values[index] @ q_curv for index in range(n_k)),
            axis=0,
        )
        s_curv = canonical_orthonormal_columns(
            selected_h_rows,
            absolute_threshold=h_signal_threshold,
            expected_rank=curvature_rank,
        )
    s_curv_residual = _orth_residual(s_curv)

    residuals = (
        q_all_residual,
        q_active_residual,
        curvature_hermitian,
        q_curv_residual,
        s_curv_residual,
    )
    if any(item > _AUDIT_TOLERANCE for item in residuals):
        raise ValueError("response block audit residual exceeds 1e-12")
    return _ResponseBlockMatrices(
        q_all=np.array(q_all, copy=True, order="C"),
        q_active=np.array(q_active, copy=True, order="C"),
        v_curv=np.array(v_curv, copy=True, order="C"),
        q_curv=np.array(q_curv, copy=True, order="C"),
        s_curv=np.array(s_curv, copy=True, order="C"),
        q_all_orth_residual=q_all_residual,
        q_active_orth_residual=q_active_residual,
        curvature_hermitian_residual=curvature_hermitian,
        q_curv_orth_residual=q_curv_residual,
        s_curv_hermitian_residual=s_curv_residual,
        source_metric_min_lower=_metric_minimum(source),
        h_metric_min_lower=_metric_minimum(h_metric),
        curvature_metric_min_lower=_metric_minimum(curvature_metric),
        active_rank=active_rank,
        curvature_rank=curvature_rank,
    )


def _derive_operator_spec(
    source: ControlReadoutCalibrationSpec,
) -> ResponseBlockOperatorSpec:
    _validate_operator_spec(source)
    provisional = ResponseBlockOperatorSpec(
        spec_schema_version=RESPONSE_BLOCK_OPERATOR_SPEC_SCHEMA_VERSION,
        source_metric_whitener=source.source_metric_whitener,
        h_metric_whitener=source.h_metric_whitener,
        curvature_incidence_operator=source.curvature_incidence_operator,
        curvature_metric_whitener=source.curvature_metric_whitener,
        curvature_normalizer_id=source.curvature_normalizer_id,
        derivation_id=APPLICATION_READOUT_DERIVATION_ID,
        source_spec_sha=source.spec_sha,
        spec_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        spec_sha=canonical_sha(response_block_operator_spec_payload(provisional)),
    )


def _freeze_block_matrix(values: np.ndarray) -> FrozenComplexTensor:
    """Freeze a matrix, padding only structurally empty rank axes.

    ``FrozenComplexTensor`` predates empty subspaces and requires every shape
    extent to be positive.  The effective column counts remain authoritative
    in ``ResponseBlockAudit.active_rank/curvature_rank``; a zero-rank matrix
    is therefore represented by an all-zero one-column storage tensor and
    consumers must slice to the audited rank.
    """

    if type(values) is not np.ndarray or values.ndim != 2:
        raise TypeError("response block matrices must be exact matrices")
    rows, columns = values.shape
    if rows > 0 and columns > 0:
        return freeze_complex_tensor(values)
    padded = np.zeros(
        (max(1, rows), max(1, columns)),
        dtype=np.complex128,
    )
    return freeze_complex_tensor(padded)


def _build_raw_block(
    response: SourceReadoutResponse,
    *,
    pair_sha: str,
    paired_response_sha: str,
    readout_spec: ControlReadoutCalibrationSpec,
    h_signal_threshold: float,
    curvature_signal_threshold: float,
    calibration_manifest_sha: str,
    selected_fejer_order: int,
    application_authority_sha: str,
) -> ResponseBlock:
    _preflight_tree(response, "source readout response")
    _exact_record(
        response,
        SourceReadoutResponse,
        "source readout response",
    )
    values = frozen_tensor_array(response.values)
    matrices = _derive_response_block_matrices(
        values,
        readout_spec,
        h_signal_threshold=h_signal_threshold,
        curvature_signal_threshold=curvature_signal_threshold,
    )
    operator_spec = _derive_operator_spec(readout_spec)
    provisional_audit = ResponseBlockAudit(
        audit_schema_version=RESPONSE_BLOCK_AUDIT_SCHEMA_VERSION,
        q_all_orth_residual=matrices.q_all_orth_residual,
        q_active_orth_residual=matrices.q_active_orth_residual,
        curvature_hermitian_residual=(matrices.curvature_hermitian_residual),
        q_curv_orth_residual=matrices.q_curv_orth_residual,
        s_curv_hermitian_residual=(matrices.s_curv_hermitian_residual),
        source_metric_min_lower=matrices.source_metric_min_lower,
        h_metric_min_lower=matrices.h_metric_min_lower,
        curvature_metric_min_lower=(matrices.curvature_metric_min_lower),
        active_rank=matrices.active_rank,
        curvature_rank=matrices.curvature_rank,
        audit_sha=_ZERO_SHA,
    )
    audit = replace(
        provisional_audit,
        audit_sha=canonical_sha(response_block_audit_payload(provisional_audit)),
    )
    provisional = ResponseBlock(
        block_schema_version=RESPONSE_BLOCK_SCHEMA_VERSION,
        branch=response.branch,
        source_readout_response=response,
        response_sha=response.response_sha,
        pair_sha=_sha(pair_sha, "pair_sha"),
        operator_spec=operator_spec,
        q_all=freeze_complex_tensor(matrices.q_all),
        q_active=_freeze_block_matrix(matrices.q_active),
        v_curv=_freeze_block_matrix(matrices.v_curv),
        q_curv=_freeze_block_matrix(matrices.q_curv),
        s_curv=_freeze_block_matrix(matrices.s_curv),
        audit=audit,
        paired_response_sha=_sha(
            paired_response_sha,
            "paired_response_sha",
        ),
        calibration_manifest_sha=_sha(
            calibration_manifest_sha,
            "calibration_manifest_sha",
        ),
        selected_fejer_order=_positive_int(
            selected_fejer_order,
            "selected_fejer_order",
        ),
        application_authority_sha=_sha(
            application_authority_sha,
            "application_authority_sha",
        ),
        block_sha=_ZERO_SHA,
    )
    return replace(
        provisional,
        block_sha=canonical_sha(response_block_payload(provisional)),
    )


class VerifiedResponseBlock:
    """Opaque downstream-only response-block capability."""

    __slots__ = ("__block", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        block: ResponseBlock,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("VerifiedResponseBlock is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedResponseBlock__block",
            block,
        )
        object.__setattr__(
            self,
            "_VerifiedResponseBlock__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedResponseBlock__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedResponseBlock is immutable")

    @property
    def block(self) -> ResponseBlock:
        return _reverify_verified_response_block(self).block


@dataclass(frozen=True)
class _BlockAuthority:
    block: ResponseBlock
    authority_kind: Literal["selected", "permitted"]
    authority_inputs: tuple[object, ...]
    branch: Literal["actual", "matched_ablated"]
    digest: str
    seal: str


@dataclass(frozen=True)
class _BlockView:
    block: ResponseBlock


_BLOCK_LIVE: dict[
    int,
    tuple[weakref.ReferenceType[VerifiedResponseBlock], _BlockAuthority],
] = {}
_BLOCK_LOCK = threading.RLock()


def _selected_expected(
    response: VerifiedPairedResponseOutcome,
    calibration: VerifiedWindowThresholdCalibration,
    branch: Literal["actual", "matched_ablated"],
) -> ResponseBlock:
    if branch not in ("actual", "matched_ablated"):
        raise ValueError("branch is not frozen")
    paired_view = _reverify_verified_paired_response_outcome(response)
    calibration_view = _reverify_verified_window_threshold_calibration(calibration)
    outcome = paired_view.outcome
    paired = outcome.paired_response
    if not outcome.status.defined or paired is None:
        raise ValueError("selected response block requires a successful pair")
    selection = calibration_view.outcome.selection
    if selection is None:
        raise ValueError("selected response block requires calibration selection")
    references = tuple(
        item
        for item in selection.selected_evidence_refs
        if item.paired_response_sha == paired.pair_sha
    )
    if len(references) != 1:
        raise ValueError("paired response SHA is not a unique selected evidence ref")
    reference = references[0]
    if (
        paired.run_spec.fejer_order != selection.selected_fejer_order
        or paired.run_spec.spec_sha != reference.run_spec_sha
    ):
        raise ValueError("selected response uses the wrong T/run spec")
    registry = calibration_view.outcome.manifest.control_registry
    entries = tuple(
        entry
        for entry in registry.entries
        if entry.entry_sha == reference.control_registry_entry_sha
    )
    if len(entries) != 1:
        raise ValueError("selected response registry entry is not unique")
    entry = entries[0]
    if (
        paired.run_spec.control_registry_entry_sha != entry.entry_sha
        or paired.actual.source_basis != entry.source_basis
        or paired.actual.readout_basis != entry.readout_basis
        or paired.ablated.source_basis != entry.source_basis
        or paired.ablated.readout_basis != entry.readout_basis
    ):
        raise ValueError("selected response basis/registry binding mismatch")
    selected = paired.actual if branch == "actual" else paired.ablated
    calibration_sha = calibration_view.outcome.manifest.calibration_manifest_sha
    return _build_raw_block(
        selected,
        pair_sha=paired.pair_sha,
        paired_response_sha=outcome.outcome_sha,
        readout_spec=entry.readout_calibration_spec,
        h_signal_threshold=selection.h_tau_sig,
        curvature_signal_threshold=selection.curv_tau_sig,
        calibration_manifest_sha=calibration_sha,
        selected_fejer_order=selection.selected_fejer_order,
        application_authority_sha=calibration_sha,
    )


def _issue_block(
    block: ResponseBlock,
    *,
    authority_kind: Literal["selected", "permitted"],
    authority_inputs: tuple[object, ...],
    branch: Literal["actual", "matched_ablated"],
) -> VerifiedResponseBlock:
    _preflight_tree(block, "response block")
    digest = canonical_sha(response_block_payload(block))
    if digest != block.block_sha:
        raise ValueError("response block self-hash mismatch")
    seal = canonical_sha(
        {
            "verified_schema_version": "v3m0.verified-response-block.v1",
            "authority_kind": authority_kind,
            "branch": branch,
            "block_sha": block.block_sha,
            "body_digest": digest,
        }
    )
    wrapper = VerifiedResponseBlock(
        _ISSUANCE_TOKEN,
        copy.deepcopy(block),
        seal,
    )
    identity = id(wrapper)
    authority = _BlockAuthority(
        block=copy.deepcopy(block),
        authority_kind=authority_kind,
        authority_inputs=authority_inputs,
        branch=branch,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[VerifiedResponseBlock],
        wrapper_id: int = identity,
    ) -> None:
        with _BLOCK_LOCK:
            current = _BLOCK_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _BLOCK_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _BLOCK_LOCK:
        _BLOCK_LIVE[identity] = (reference, authority)
    return wrapper


def build_selected_control_response_block(
    response: VerifiedPairedResponseOutcome,
    calibration: VerifiedWindowThresholdCalibration,
    branch: Literal["actual", "matched_ablated"],
) -> VerifiedResponseBlock:
    expected = _selected_expected(response, calibration, branch)
    return _issue_block(
        expected,
        authority_kind="selected",
        authority_inputs=(response, calibration),
        branch=branch,
    )


def verify_selected_control_response_block(
    block: ResponseBlock,
    response: VerifiedPairedResponseOutcome,
    calibration: VerifiedWindowThresholdCalibration,
    branch: Literal["actual", "matched_ablated"],
) -> VerifiedResponseBlock:
    _preflight_tree(block, "raw selected response block")
    _exact_record(block, ResponseBlock, "raw selected response block")
    expected = _selected_expected(response, calibration, branch)
    if block != expected:
        raise ValueError("raw selected response block differs from replay")
    return _issue_block(
        expected,
        authority_kind="selected",
        authority_inputs=(response, calibration),
        branch=branch,
    )


def build_permitted_response_block(
    permit: VerifiedCalibrationApplicationPermit,
    evidence: object,
    branch: Literal["actual", "matched_ablated"],
) -> VerifiedResponseBlock:
    """Fail closed until the full application-evidence issuer is present.

    A permit alone is intentionally insufficient: accepting it here would
    create the exact pre-response/response authority cycle Task 12 forbids.
    """

    _reverify_verified_calibration_application_permit(permit)
    del evidence, branch
    raise TypeError(
        "permitted response block requires a live "
        "VerifiedV3M0ControlApplicationEvidence"
    )


def verify_permitted_response_block(
    block: ResponseBlock,
    permit: VerifiedCalibrationApplicationPermit,
    evidence: object,
    branch: Literal["actual", "matched_ablated"],
) -> VerifiedResponseBlock:
    _preflight_tree(block, "raw permitted response block")
    _reverify_verified_calibration_application_permit(permit)
    del evidence, branch
    raise TypeError(
        "permitted response block hydration requires a live "
        "VerifiedV3M0ControlApplicationEvidence"
    )


def _reverify_verified_response_block(
    wrapper: VerifiedResponseBlock,
) -> _BlockView:
    if type(wrapper) is not VerifiedResponseBlock:
        raise TypeError("consumer requires a live VerifiedResponseBlock")
    with _BLOCK_LOCK:
        current = _BLOCK_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("response block identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedResponseBlock__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedResponseBlock__block",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedResponseBlock__seal",
        )
    except AttributeError as exc:
        raise ValueError("response block authority record is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("response block token mismatch")
    if authority.authority_kind == "selected":
        response, calibration = authority.authority_inputs
        expected = _selected_expected(
            response,
            calibration,
            authority.branch,
        )
    else:
        raise ValueError("permitted response block authority is not implemented")
    raw_digest = canonical_sha(response_block_payload(raw))
    expected_digest = canonical_sha(response_block_payload(expected))
    expected_seal = canonical_sha(
        {
            "verified_schema_version": "v3m0.verified-response-block.v1",
            "authority_kind": authority.authority_kind,
            "branch": authority.branch,
            "block_sha": expected.block_sha,
            "body_digest": expected_digest,
        }
    )
    if (
        raw_digest != authority.digest
        or expected_digest != authority.digest
        or expected != authority.block
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("response block immutable seal mismatch")
    return _BlockView(block=copy.deepcopy(expected))


__all__ = [
    "RESPONSE_BLOCK_AUDIT_SCHEMA_VERSION",
    "RESPONSE_BLOCK_OPERATOR_SPEC_SCHEMA_VERSION",
    "RESPONSE_BLOCK_SCHEMA_VERSION",
    "ResponseBlock",
    "ResponseBlockAudit",
    "ResponseBlockOperatorSpec",
    "VerifiedResponseBlock",
    "build_permitted_response_block",
    "build_selected_control_response_block",
    "response_block_audit_payload",
    "response_block_operator_spec_payload",
    "response_block_payload",
    "verify_permitted_response_block",
    "verify_selected_control_response_block",
]
