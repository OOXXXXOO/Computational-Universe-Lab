"""Coefficient-level Laurent residual certificates for V3-M0."""

from __future__ import annotations

import math
import re
import json
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Literal

import numpy as np

from .dynamics import VerifiedTransition, _reverify_verified_transition
from .evidence import canonical_sha
from .factory import (
    TENSOR_SCHEMA_VERSION,
    FrozenComplexTensor,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
)
from .fp64 import (
    MAXIMUM_FINITE,
    MINIMUM_NORMAL,
    build_complex_dot_roundoff_bound,
    directed_add_upper,
    directed_mul_upper,
    frobenius_sqrt_upper,
    require_hard_scalar,
)
from .fp64_protocol import (
    Fp64EnclosureProtocol,
    verify_fp64_enclosure_protocol,
)
from .metric import (
    StabilityMetricWitness,
    verify_stability_metric_witness,
)
from .structure import StructureManifest, verify_structure_manifest


LAURENT_RESIDUAL_SCHEMA_VERSION = "v3m0.laurent-residual-certificate.v1"
FOURIER_CONVENTION_ID: Literal[
    "signed-displacement-exp-minus-i-k-dot-d-v1"
] = "signed-displacement-exp-minus-i-k-dot-d-v1"
MATRIX_NORM_ID: Literal["spectral-2-v1"] = "spectral-2-v1"
MOMENTUM_SUPREMUM_METHOD_ID: Literal[
    "sum-of-directed-outward-frobenius-upper-v1"
] = "sum-of-directed-outward-frobenius-upper-v1"
LAURENT_MAX_PAIR_PRODUCT = 1_000_000
LAURENT_MAX_SUPPORT = 100_000
LAURENT_MAX_COEFFICIENT_ENTRIES = 16_777_216
LAURENT_MAX_ARITHMETIC_WORK = 2_000_000_000
LAURENT_MAX_EVIDENCE_BODY_BYTES = 268_435_456
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")

Offset = tuple[int, ...]
CenterMap = dict[Offset, np.ndarray]
ErrorMap = dict[Offset, list[list[Fraction]]]
ExactComplex = tuple[Fraction, Fraction]
ExactMatrix = list[list[ExactComplex]]
ExactMap = dict[Offset, ExactMatrix]


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _finite_nonnegative(value: object, field: str) -> float:
    if type(value) is not float:
        raise TypeError(f"{field} must be an fp64 wire float")
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{field} must be finite and non-negative")
    return value


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


@dataclass(frozen=True)
class LaurentResidualCertificate:
    residual_schema_version: str
    residual_kind: Literal[
        "canonical-structure",
        "stability-metric",
    ]
    operand_shas: tuple[str, ...]
    spatial_ndim: int
    n_state: int
    fp64_enclosure_protocol_sha: str
    fourier_convention_id: Literal[
        "signed-displacement-exp-minus-i-k-dot-d-v1"
    ]
    matrix_norm_id: Literal["spectral-2-v1"]
    momentum_supremum_method_id: Literal[
        "sum-of-directed-outward-frobenius-upper-v1"
    ]
    support_offsets: tuple[tuple[int, ...], ...]
    coefficients: FrozenComplexTensor
    convolution_pair_counts: tuple[int, ...]
    coefficient_roundoff_frobenius_uppers: tuple[float, ...]
    coefficient_frobenius_upper_sum: float
    raw_global_momentum_supremum_bound: float
    residual_sha: str

    def __post_init__(self) -> None:
        _text(self.residual_schema_version, "residual_schema_version")
        if self.residual_kind not in (
            "canonical-structure",
            "stability-metric",
        ):
            raise ValueError("residual_kind is not closed")
        if type(self.operand_shas) is not tuple or len(self.operand_shas) != 3:
            raise ValueError("operand_shas must contain exactly three SHAs")
        for index, value in enumerate(self.operand_shas):
            _sha(value, f"operand_shas[{index}]")
        ndim = _positive_int(self.spatial_ndim, "spatial_ndim")
        state_count = _positive_int(self.n_state, "n_state")
        _sha(
            self.fp64_enclosure_protocol_sha,
            "fp64_enclosure_protocol_sha",
        )
        if self.fourier_convention_id != FOURIER_CONVENTION_ID:
            raise ValueError("Fourier convention is not frozen")
        if self.matrix_norm_id != MATRIX_NORM_ID:
            raise ValueError("matrix norm is not frozen")
        if (
            self.momentum_supremum_method_id
            != MOMENTUM_SUPREMUM_METHOD_ID
        ):
            raise ValueError("momentum supremum method is not frozen")
        if type(self.support_offsets) is not tuple or not self.support_offsets:
            raise ValueError("support_offsets must be non-empty")
        if len(self.support_offsets) > LAURENT_MAX_SUPPORT:
            raise ValueError("Laurent result support cap exceeded")
        if (
            len(self.support_offsets) * state_count * state_count
            > LAURENT_MAX_COEFFICIENT_ENTRIES
        ):
            raise ValueError("Laurent coefficient-entry cap exceeded")
        for row in self.support_offsets:
            if type(row) is not tuple or len(row) != ndim:
                raise ValueError("support offset dimension mismatch")
            if not all(type(item) is int for item in row):
                raise TypeError("support offsets must contain ints")
        if self.support_offsets != tuple(sorted(set(self.support_offsets))):
            raise ValueError("support offsets must be unique and canonical")
        if type(self.coefficients) is not FrozenComplexTensor:
            raise TypeError(
                "coefficients must be an exact FrozenComplexTensor"
            )
        if self.coefficients.shape != (
            len(self.support_offsets),
            state_count,
            state_count,
        ):
            raise ValueError("coefficient tensor shape mismatch")
        if (
            type(self.convolution_pair_counts) is not tuple
            or len(self.convolution_pair_counts) != 2
        ):
            raise ValueError(
                "convolution_pair_counts must contain exactly two stages"
            )
        for index, value in enumerate(self.convolution_pair_counts):
            _positive_int(value, f"convolution_pair_counts[{index}]")
        if (
            type(self.coefficient_roundoff_frobenius_uppers) is not tuple
            or len(self.coefficient_roundoff_frobenius_uppers)
            != len(self.support_offsets)
        ):
            raise ValueError("coefficient roundoff upper count mismatch")
        for index, value in enumerate(
            self.coefficient_roundoff_frobenius_uppers
        ):
            _finite_nonnegative(
                value,
                f"coefficient_roundoff_frobenius_uppers[{index}]",
            )
        _finite_nonnegative(
            self.coefficient_frobenius_upper_sum,
            "coefficient_frobenius_upper_sum",
        )
        _finite_nonnegative(
            self.raw_global_momentum_supremum_bound,
            "raw_global_momentum_supremum_bound",
        )
        _sha(self.residual_sha, "residual_sha")


def laurent_residual_payload(
    certificate: LaurentResidualCertificate,
) -> dict[str, object]:
    if type(certificate) is not LaurentResidualCertificate:
        raise TypeError(
            "certificate must be an exact LaurentResidualCertificate"
        )
    return {
        "residual_schema_version": certificate.residual_schema_version,
        "residual_kind": certificate.residual_kind,
        "operand_shas": list(certificate.operand_shas),
        "spatial_ndim": certificate.spatial_ndim,
        "n_state": certificate.n_state,
        "fp64_enclosure_protocol_sha": (
            certificate.fp64_enclosure_protocol_sha
        ),
        "fourier_convention_id": certificate.fourier_convention_id,
        "matrix_norm_id": certificate.matrix_norm_id,
        "momentum_supremum_method_id": (
            certificate.momentum_supremum_method_id
        ),
        "support_offsets": [
            list(item) for item in certificate.support_offsets
        ],
        "coefficients": _tensor_record(certificate.coefficients),
        "convolution_pair_counts": list(
            certificate.convolution_pair_counts
        ),
        "coefficient_roundoff_frobenius_uppers": list(
            certificate.coefficient_roundoff_frobenius_uppers
        ),
        "coefficient_frobenius_upper_sum": (
            certificate.coefficient_frobenius_upper_sum
        ),
        "raw_global_momentum_supremum_bound": (
            certificate.raw_global_momentum_supremum_bound
        ),
    }


def _canonical_json_byte_count(payload: dict[str, object]) -> int:
    return len(
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def _preflight_laurent_evidence_body(
    *,
    kind: Literal["canonical-structure", "stability-metric"],
    operands: tuple[str, ...],
    ndim: int,
    n_state: int,
    protocol_sha: str,
    support: tuple[Offset, ...],
    centers: CenterMap,
    pair_counts: tuple[int, ...],
    roundoff_uppers: tuple[float, ...],
    upper_sum: float,
) -> int:
    """Count canonical bytes without materializing the coefficient wire list."""

    coefficient_stub = {
        "tensor_schema_version": TENSOR_SCHEMA_VERSION,
        "shape": [len(support), n_state, n_state],
        "values_wire": [],
        "tensor_sha": "0" * 64,
    }
    body: dict[str, object] = {
        "residual_schema_version": LAURENT_RESIDUAL_SCHEMA_VERSION,
        "residual_kind": kind,
        "operand_shas": list(operands),
        "spatial_ndim": ndim,
        "n_state": n_state,
        "fp64_enclosure_protocol_sha": protocol_sha,
        "fourier_convention_id": FOURIER_CONVENTION_ID,
        "matrix_norm_id": MATRIX_NORM_ID,
        "momentum_supremum_method_id": MOMENTUM_SUPREMUM_METHOD_ID,
        "support_offsets": [list(item) for item in support],
        "coefficients": coefficient_stub,
        "convolution_pair_counts": list(pair_counts),
        "coefficient_roundoff_frobenius_uppers": list(
            roundoff_uppers
        ),
        "coefficient_frobenius_upper_sum": upper_sum,
        "raw_global_momentum_supremum_bound": upper_sum,
    }
    base_count = _canonical_json_byte_count(body)
    value_list_count = 2
    first = True
    for offset in support:
        matrix = centers[offset]
        for value in matrix.flat:
            real = require_hard_scalar(value.real, "coefficient real")
            imag = require_hard_scalar(value.imag, "coefficient imag")
            wire_count = len(
                json.dumps(
                    [real, imag],
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            value_list_count += wire_count + (0 if first else 1)
            first = False
            if (
                base_count - 2 + value_list_count
                > LAURENT_MAX_EVIDENCE_BODY_BYTES
            ):
                raise ValueError(
                    "Laurent canonical evidence body cap exceeded"
                )
    total = base_count - 2 + value_list_count
    if total > LAURENT_MAX_EVIDENCE_BODY_BYTES:
        raise ValueError("Laurent canonical evidence body cap exceeded")
    return total


def _preflight_raw_laurent_cardinality(
    certificate: LaurentResidualCertificate,
) -> None:
    """Apply constant-space schema caps before building any raw lists."""

    if type(certificate.operand_shas) is not tuple or len(
        certificate.operand_shas
    ) != 3:
        raise ValueError("operand_shas must contain exactly three SHAs")
    if type(certificate.support_offsets) is not tuple:
        raise TypeError("support_offsets must be a tuple")
    support_count = len(certificate.support_offsets)
    if support_count <= 0 or support_count > LAURENT_MAX_SUPPORT:
        raise ValueError("Laurent result support cap exceeded")
    state_count = _positive_int(certificate.n_state, "n_state")
    if (
        support_count * state_count * state_count
        > LAURENT_MAX_COEFFICIENT_ENTRIES
    ):
        raise ValueError("Laurent coefficient-entry cap exceeded")
    if type(certificate.convolution_pair_counts) is not tuple or len(
        certificate.convolution_pair_counts
    ) != 2:
        raise ValueError(
            "convolution_pair_counts must contain exactly two stages"
        )
    if (
        type(certificate.coefficient_roundoff_frobenius_uppers)
        is not tuple
        or len(certificate.coefficient_roundoff_frobenius_uppers)
        != support_count
    ):
        raise ValueError("coefficient roundoff upper count mismatch")
    if type(certificate.coefficients) is not FrozenComplexTensor:
        raise TypeError("coefficients must be an exact FrozenComplexTensor")
    if certificate.coefficients.shape != (
        support_count,
        state_count,
        state_count,
    ):
        raise ValueError("coefficient tensor shape mismatch")


def _preflight_raw_laurent_evidence_body(
    certificate: LaurentResidualCertificate,
) -> int:
    """Count an untrusted raw wire before materializing its payload."""

    _preflight_raw_laurent_cardinality(certificate)
    coefficient_stub = {
        "tensor_schema_version": (
            certificate.coefficients.tensor_schema_version
        ),
        "shape": list(certificate.coefficients.shape),
        "values_wire": [],
        "tensor_sha": certificate.coefficients.tensor_sha,
    }
    body: dict[str, object] = {
        "residual_schema_version": certificate.residual_schema_version,
        "residual_kind": certificate.residual_kind,
        "operand_shas": list(certificate.operand_shas),
        "spatial_ndim": certificate.spatial_ndim,
        "n_state": certificate.n_state,
        "fp64_enclosure_protocol_sha": (
            certificate.fp64_enclosure_protocol_sha
        ),
        "fourier_convention_id": certificate.fourier_convention_id,
        "matrix_norm_id": certificate.matrix_norm_id,
        "momentum_supremum_method_id": (
            certificate.momentum_supremum_method_id
        ),
        "support_offsets": [
            list(item) for item in certificate.support_offsets
        ],
        "coefficients": coefficient_stub,
        "convolution_pair_counts": list(
            certificate.convolution_pair_counts
        ),
        "coefficient_roundoff_frobenius_uppers": list(
            certificate.coefficient_roundoff_frobenius_uppers
        ),
        "coefficient_frobenius_upper_sum": (
            certificate.coefficient_frobenius_upper_sum
        ),
        "raw_global_momentum_supremum_bound": (
            certificate.raw_global_momentum_supremum_bound
        ),
    }
    base_count = _canonical_json_byte_count(body)
    value_list_count = 2
    for index, wire in enumerate(certificate.coefficients.values_wire):
        if type(wire) is not tuple or len(wire) != 2:
            raise TypeError("coefficient wire must be a real/imag tuple")
        real = require_hard_scalar(
            wire[0],
            f"coefficients.values_wire[{index}].real",
        )
        imag = require_hard_scalar(
            wire[1],
            f"coefficients.values_wire[{index}].imag",
        )
        wire_count = len(
            json.dumps(
                [real, imag],
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        value_list_count += wire_count + (0 if index == 0 else 1)
        if (
            base_count - 2 + value_list_count
            > LAURENT_MAX_EVIDENCE_BODY_BYTES
        ):
            raise ValueError(
                "Laurent canonical evidence body cap exceeded"
            )
    total = base_count - 2 + value_list_count
    if total > LAURENT_MAX_EVIDENCE_BODY_BYTES:
        raise ValueError("Laurent canonical evidence body cap exceeded")
    return total


def _preflight_convolution(
    *,
    left_count: int,
    right_count: int,
    n_state: int,
) -> int:
    left = _positive_int(left_count, "left_count")
    right = _positive_int(right_count, "right_count")
    state = _positive_int(n_state, "n_state")
    pair_count = left * right
    if pair_count > LAURENT_MAX_PAIR_PRODUCT:
        raise ValueError("Laurent convolution pair-product cap exceeded")
    if pair_count * state**3 > LAURENT_MAX_ARITHMETIC_WORK:
        raise ValueError("Laurent convolution arithmetic work cap exceeded")
    return pair_count


def _offset_sum(left: Offset, right: Offset) -> Offset:
    return tuple(first + second for first, second in zip(left, right))


def _preflight_support_offsets(
    left: tuple[Offset, ...],
    right: tuple[Offset, ...],
    n_state: int,
    *,
    stage: str,
) -> tuple[Offset, ...]:
    if type(left) is not tuple or not left:
        raise ValueError(f"{stage} left support must be non-empty")
    if type(right) is not tuple or not right:
        raise ValueError(f"{stage} right support must be non-empty")
    ndim = len(left[0])
    for label, support in (("left", left), ("right", right)):
        for offset in support:
            if (
                type(offset) is not tuple
                or len(offset) != ndim
                or not all(type(item) is int for item in offset)
            ):
                raise ValueError(
                    f"{stage} {label} support dimension mismatch"
                )
    pair_count = len(left) * len(right)
    if pair_count > LAURENT_MAX_PAIR_PRODUCT:
        raise ValueError(
            f"{stage} Laurent convolution pair-product cap exceeded"
        )
    state = _positive_int(n_state, "n_state")
    if pair_count * state**3 > LAURENT_MAX_ARITHMETIC_WORK:
        raise ValueError(
            f"{stage} Laurent convolution arithmetic work cap exceeded"
        )
    support: set[Offset] = set()
    for first in left:
        for second in right:
            support.add(_offset_sum(first, second))
            if len(support) > LAURENT_MAX_SUPPORT:
                raise ValueError(
                    f"{stage} Laurent result support cap exceeded"
                )
    result = tuple(sorted(support))
    if len(result) * state * state > LAURENT_MAX_COEFFICIENT_ENTRIES:
        raise ValueError(
            f"{stage} Laurent coefficient-entry cap exceeded"
        )
    return result


def _preflight_convolution_chain(
    left: tuple[Offset, ...],
    middle: tuple[Offset, ...],
    right: tuple[Offset, ...],
    n_state: int,
) -> tuple[tuple[Offset, ...], tuple[Offset, ...]]:
    """Plan both Laurent products before allocating either coefficient map."""

    first = _preflight_support_offsets(
        left,
        middle,
        n_state,
        stage="first",
    )
    second = _preflight_support_offsets(
        first,
        right,
        n_state,
        stage="second",
    )
    return first, second


def _preflight_result_support(
    left: CenterMap,
    right: CenterMap,
    n_state: int,
) -> tuple[Offset, ...]:
    return _preflight_support_offsets(
        tuple(left),
        tuple(right),
        n_state,
        stage="current",
    )


def _fraction(value: float) -> Fraction:
    return Fraction.from_float(require_hard_scalar(value, "fraction input"))


def _complex_exact(value: complex) -> ExactComplex:
    return (
        _fraction(require_hard_scalar(value.real, "complex real")),
        _fraction(require_hard_scalar(value.imag, "complex imag")),
    )


def _hard_mul(left: float, right: float, field: str) -> float:
    first = require_hard_scalar(left, f"{field}.left")
    second = require_hard_scalar(right, f"{field}.right")
    return require_hard_scalar(first * second, field)


def _hard_add(left: float, right: float, field: str) -> float:
    first = require_hard_scalar(left, f"{field}.left")
    second = require_hard_scalar(right, f"{field}.right")
    return require_hard_scalar(first + second, field)


def _hard_sub(left: float, right: float, field: str) -> float:
    first = require_hard_scalar(left, f"{field}.left")
    second = require_hard_scalar(right, f"{field}.right")
    return require_hard_scalar(first - second, field)


def _ordered_complex_multiply(
    left: complex,
    right: complex,
) -> complex:
    left_real = require_hard_scalar(left.real, "multiply.left.real")
    left_imag = require_hard_scalar(left.imag, "multiply.left.imag")
    right_real = require_hard_scalar(right.real, "multiply.right.real")
    right_imag = require_hard_scalar(right.imag, "multiply.right.imag")
    real_first = _hard_mul(
        left_real,
        right_real,
        "multiply.real.first",
    )
    real_second = _hard_mul(
        left_imag,
        right_imag,
        "multiply.real.second",
    )
    imag_first = _hard_mul(
        left_real,
        right_imag,
        "multiply.imag.first",
    )
    imag_second = _hard_mul(
        left_imag,
        right_real,
        "multiply.imag.second",
    )
    return complex(
        _hard_sub(real_first, real_second, "multiply.real.subtract"),
        _hard_add(imag_first, imag_second, "multiply.imag.add"),
    )


def _ordered_complex_add(
    left: complex,
    right: complex,
) -> complex:
    return complex(
        _hard_add(left.real, right.real, "complex_add.real"),
        _hard_add(left.imag, right.imag, "complex_add.imag"),
    )


def _ordered_complex_subtract(
    left: complex,
    right: complex,
) -> complex:
    return complex(
        _hard_sub(left.real, right.real, "complex_subtract.real"),
        _hard_sub(left.imag, right.imag, "complex_subtract.imag"),
    )


def _absolute_product_sum_add(
    current: float,
    left: complex,
    right: complex,
) -> float:
    result = require_hard_scalar(current, "absolute_product_sum")
    factors = (
        (abs(float(left.real)), abs(float(right.real))),
        (abs(float(left.imag)), abs(float(right.imag))),
        (abs(float(left.real)), abs(float(right.imag))),
        (abs(float(left.imag)), abs(float(right.real))),
    )
    for first, second in factors:
        product = directed_mul_upper(first, second)
        result = directed_add_upper(result, product)
    return result


def _ordered_complex_dot_values(
    left: tuple[complex, ...],
    right: tuple[complex, ...],
) -> tuple[complex, float]:
    """Execute the frozen q=4n-1 center DAG and its outward abs sum."""

    if type(left) is not tuple or type(right) is not tuple:
        raise TypeError("dot operands must be tuples")
    if not left or len(left) != len(right):
        raise ValueError("dot operands must have equal positive length")
    center: complex | None = None
    absolute_product_sum = +0.0
    for left_value, right_value in zip(left, right):
        term = _ordered_complex_multiply(left_value, right_value)
        center = (
            term
            if center is None
            else _ordered_complex_add(center, term)
        )
        absolute_product_sum = _absolute_product_sum_add(
            absolute_product_sum,
            left_value,
            right_value,
        )
    if center is None:
        raise AssertionError("non-empty dot did not produce a center")
    return center, absolute_product_sum


def _validate_center_map(
    values: CenterMap,
    n_state: int,
    field: str,
) -> None:
    if type(values) is not dict or not values:
        raise ValueError(f"{field} must be a non-empty dict")
    for offset, matrix in values.items():
        if type(offset) is not tuple or not all(
            type(item) is int for item in offset
        ):
            raise TypeError(f"{field} offsets must be integer tuples")
        if type(matrix) is not np.ndarray:
            raise TypeError(f"{field} matrices must be NumPy arrays")
        if matrix.dtype != np.dtype(np.complex128):
            raise TypeError(f"{field} matrices must be complex128")
        if matrix.shape != (n_state, n_state):
            raise ValueError(f"{field} matrix shape mismatch")
        for index, value in enumerate(matrix.flat):
            require_hard_scalar(
                value.real,
                f"{field}[{offset}][{index}].real",
            )
            require_hard_scalar(
                value.imag,
                f"{field}[{offset}][{index}].imag",
            )


def _exact_add(left: ExactComplex, right: ExactComplex) -> ExactComplex:
    return left[0] + right[0], left[1] + right[1]


def _exact_sub(left: ExactComplex, right: ExactComplex) -> ExactComplex:
    return left[0] - right[0], left[1] - right[1]


def _exact_mul(left: ExactComplex, right: ExactComplex) -> ExactComplex:
    return (
        left[0] * right[0] - left[1] * right[1],
        left[0] * right[1] + left[1] * right[0],
    )


def _exact_zero_matrix(n_state: int) -> ExactMatrix:
    return [
        [(Fraction(0), Fraction(0)) for _ in range(n_state)]
        for _ in range(n_state)
    ]


def _exact_center_map(values: CenterMap) -> ExactMap:
    result: ExactMap = {}
    for offset, matrix in values.items():
        result[offset] = [
            [_complex_exact(complex(item)) for item in row]
            for row in matrix
        ]
    return result


def _exact_convolve(
    left: ExactMap,
    right: ExactMap,
    n_state: int,
) -> ExactMap:
    result: ExactMap = {}
    for left_offset, left_matrix in left.items():
        for right_offset, right_matrix in right.items():
            offset = _offset_sum(left_offset, right_offset)
            target = result.setdefault(
                offset,
                _exact_zero_matrix(n_state),
            )
            for row in range(n_state):
                for column in range(n_state):
                    value: ExactComplex = (Fraction(0), Fraction(0))
                    for inner in range(n_state):
                        value = _exact_add(
                            value,
                            _exact_mul(
                                left_matrix[row][inner],
                                right_matrix[inner][column],
                            ),
                        )
                    target[row][column] = _exact_add(
                        target[row][column],
                        value,
                    )
    return result


def _zero_errors(
    values: CenterMap,
    n_state: int,
) -> ErrorMap:
    return {
        offset: [
            [Fraction(0) for _ in range(n_state)]
            for _ in range(n_state)
        ]
        for offset in values
    }


def _one_norm(value: complex) -> Fraction:
    return abs(_fraction(float(value.real))) + abs(
        _fraction(float(value.imag))
    )


def _addition_roundoff(
    result: complex,
    left: complex,
    right: complex,
) -> Fraction:
    exact_real = _fraction(float(left.real)) + _fraction(float(right.real))
    exact_imag = _fraction(float(left.imag)) + _fraction(float(right.imag))
    return (
        abs(_fraction(float(result.real)) - exact_real)
        + abs(_fraction(float(result.imag)) - exact_imag)
    )


def _scalar_convolve(
    left: CenterMap,
    left_errors: ErrorMap,
    right: CenterMap,
    right_errors: ErrorMap,
    n_state: int,
) -> tuple[CenterMap, ErrorMap, int]:
    _validate_center_map(left, n_state, "left")
    _validate_center_map(right, n_state, "right")
    support = _preflight_result_support(left, right, n_state)
    pair_count = len(left) * len(right)
    centers: CenterMap = {
        offset: np.zeros((n_state, n_state), dtype=np.complex128)
        for offset in support
    }
    errors: ErrorMap = {
        offset: [
            [Fraction(0) for _ in range(n_state)]
            for _ in range(n_state)
        ]
        for offset in support
    }
    for left_offset, left_matrix in left.items():
        for right_offset, right_matrix in right.items():
            offset = _offset_sum(left_offset, right_offset)
            product = np.zeros(
                (n_state, n_state),
                dtype=np.complex128,
            )
            product_error = [
                [Fraction(0) for _ in range(n_state)]
                for _ in range(n_state)
            ]
            for row in range(n_state):
                for column in range(n_state):
                    left_values = tuple(
                        complex(left_matrix[row, inner])
                        for inner in range(n_state)
                    )
                    right_values = tuple(
                        complex(right_matrix[inner, column])
                        for inner in range(n_state)
                    )
                    center, product_sum = _ordered_complex_dot_values(
                        left_values,
                        right_values,
                    )
                    propagated = Fraction(0)
                    for inner in range(n_state):
                        left_value = left_values[inner]
                        right_value = right_values[inner]
                        left_error = left_errors[left_offset][row][inner]
                        right_error = right_errors[right_offset][inner][column]
                        propagated += (
                            left_error * (_one_norm(right_value) + right_error)
                            + _one_norm(left_value) * right_error
                        )
                    dot = build_complex_dot_roundoff_bound(
                        length=n_state,
                        absolute_product_sum=float(product_sum),
                    )
                    product[row, column] = center
                    product_error[row][column] = (
                        propagated
                        + 2 * _fraction(dot.roundoff_upper)
                    )
            target = centers[offset]
            for row in range(n_state):
                for column in range(n_state):
                    before = complex(target[row, column])
                    addition = _ordered_complex_add(
                        before,
                        complex(product[row, column]),
                    )
                    errors[offset][row][column] += (
                        product_error[row][column]
                        + _addition_roundoff(
                            addition,
                            before,
                            complex(product[row, column]),
                        )
                    )
                    target[row, column] = addition
    return centers, errors, pair_count


def _subtract_map(
    centers: CenterMap,
    errors: ErrorMap,
    subtract: CenterMap,
    n_state: int,
) -> tuple[CenterMap, ErrorMap]:
    support = tuple(sorted(set(centers) | set(subtract)))
    if len(support) > LAURENT_MAX_SUPPORT:
        raise ValueError("Laurent subtraction support cap exceeded")
    if len(support) * n_state * n_state > LAURENT_MAX_COEFFICIENT_ENTRIES:
        raise ValueError("Laurent subtraction entry cap exceeded")
    result: CenterMap = {}
    result_errors: ErrorMap = {}
    for offset in support:
        left = centers.get(
            offset,
            np.zeros((n_state, n_state), dtype=np.complex128),
        )
        right = subtract.get(
            offset,
            np.zeros((n_state, n_state), dtype=np.complex128),
        )
        target = np.zeros((n_state, n_state), dtype=np.complex128)
        target_errors = [
            [Fraction(0) for _ in range(n_state)]
            for _ in range(n_state)
        ]
        base_errors = errors.get(
            offset,
            target_errors,
        )
        for row in range(n_state):
            for column in range(n_state):
                left_value = complex(left[row, column])
                right_value = complex(right[row, column])
                value = _ordered_complex_subtract(
                    left_value,
                    right_value,
                )
                target[row, column] = value
                exact_real = (
                    _fraction(float(left_value.real))
                    - _fraction(float(right_value.real))
                )
                exact_imag = (
                    _fraction(float(left_value.imag))
                    - _fraction(float(right_value.imag))
                )
                rounding = (
                    abs(_fraction(float(value.real)) - exact_real)
                    + abs(_fraction(float(value.imag)) - exact_imag)
                )
                target_errors[row][column] = (
                    base_errors[row][column] + rounding
                )
        result[offset] = target
        result_errors[offset] = target_errors
    return result, result_errors


def _exact_subtract_map(
    centers: ExactMap,
    subtract: ExactMap,
    n_state: int,
) -> ExactMap:
    support = tuple(sorted(set(centers) | set(subtract)))
    result: ExactMap = {}
    for offset in support:
        left = centers.get(offset, _exact_zero_matrix(n_state))
        right = subtract.get(offset, _exact_zero_matrix(n_state))
        result[offset] = [
            [
                _exact_sub(left[row][column], right[row][column])
                for column in range(n_state)
            ]
            for row in range(n_state)
        ]
    return result


def _minimal_float_upper(value: Fraction) -> float:
    if value < 0:
        raise ValueError("upper value must be non-negative")
    if value == 0:
        return 0.0
    if value > _fraction(MAXIMUM_FINITE):
        raise ValueError("upper value exceeds finite fp64")
    if value <= _fraction(MINIMUM_NORMAL):
        return MINIMUM_NORMAL
    candidate = float(value)
    if _fraction(candidate) < value:
        candidate = math.nextafter(candidate, math.inf)
    if not math.isfinite(candidate):
        raise ValueError("upper value overflowed")
    return candidate


def _coefficient_uppers(
    support: tuple[Offset, ...],
    centers: CenterMap,
    propagated: ErrorMap,
    exact: ExactMap,
    n_state: int,
) -> tuple[float, ...]:
    result: list[float] = []
    for offset in support:
        sum_squares = Fraction(0)
        center_matrix = centers[offset]
        exact_matrix = exact[offset]
        for row in range(n_state):
            for column in range(n_state):
                center = _complex_exact(complex(center_matrix[row, column]))
                exact_value = exact_matrix[row][column]
                actual_error = (
                    abs(center[0] - exact_value[0])
                    + abs(center[1] - exact_value[1])
                )
                entry_upper = max(
                    actual_error,
                    propagated[offset][row][column],
                )
                sum_squares += entry_upper * entry_upper
        result.append(frobenius_sqrt_upper(sum_squares))
    return tuple(result)


def _coefficient_frobenius_upper_sum(
    support: tuple[Offset, ...],
    centers: CenterMap,
    roundoff_uppers: tuple[float, ...],
) -> float:
    """Outward sum of ``||stored coefficient||_F + roundoff``."""

    if len(support) != len(roundoff_uppers):
        raise ValueError("coefficient center and roundoff counts differ")
    total = Fraction(0)
    for index, offset in enumerate(support):
        if offset not in centers:
            raise ValueError("coefficient center support is incomplete")
        sum_squares = Fraction(0)
        for value in np.asarray(centers[offset], dtype=np.complex128).flat:
            exact = _complex_exact(complex(value))
            sum_squares += exact[0] * exact[0] + exact[1] * exact[1]
        center_upper = frobenius_sqrt_upper(sum_squares)
        total += _fraction(center_upper) + _fraction(
            _finite_nonnegative(
                roundoff_uppers[index],
                f"roundoff_uppers[{index}]",
            )
        )
    return _minimal_float_upper(total)


def _transition_map(
    transition: VerifiedTransition,
) -> tuple[CenterMap, int]:
    view = _reverify_verified_transition(transition)
    raw = view.transition
    values = frozen_tensor_array(raw.kernel)
    result = {
        offset: values[
            (slice(None), slice(None))
            + tuple(
                coordinate % length
                for coordinate, length in zip(
                    offset,
                    raw.spatial_shape,
                )
            )
        ].copy()
        for offset in raw.support_offsets
    }
    return result, len(raw.channel_order)


def _constant_map(
    matrix: np.ndarray,
    ndim: int,
) -> CenterMap:
    return {(0,) * ndim: np.asarray(matrix, dtype=np.complex128).copy()}


def _left_adjoint_map(
    values: CenterMap,
    *,
    conjugate: bool,
) -> CenterMap:
    return {
        tuple(-item for item in offset): (
            matrix.conj().T.copy() if conjugate else matrix.T.copy()
        )
        for offset, matrix in values.items()
    }


def _metric_map(witness: StabilityMetricWitness) -> CenterMap:
    values = frozen_tensor_array(witness.metric_kernel)
    return {
        offset: values[index].copy()
        for index, offset in enumerate(witness.metric_support_offsets)
    }


def _build_residual(
    *,
    kind: Literal["canonical-structure", "stability-metric"],
    transition: VerifiedTransition,
    structure: StructureManifest,
    metric: StabilityMetricWitness,
    protocol: Fp64EnclosureProtocol,
) -> LaurentResidualCertificate:
    transition_view = _reverify_verified_transition(transition)
    factory = transition_view.factory
    authority = transition_view.prestructure
    verified_structure = verify_structure_manifest(
        structure,
        factory,
        authority,
    )
    verified_metric = verify_stability_metric_witness(
        metric,
        factory,
        authority,
        structure,
    )
    verified_protocol = verify_fp64_enclosure_protocol(protocol)
    transition_map, n_state = _transition_map(transition)
    ndim = len(transition_view.transition.spatial_shape)
    if kind == "canonical-structure":
        middle = _constant_map(
            frozen_tensor_array(verified_structure.structure_form),
            ndim,
        )
        left = _left_adjoint_map(
            transition_map,
            conjugate=False,
        )
        operands = (
            transition_view.transition.transition_sha,
            verified_structure.structure_manifest_sha,
            verified_structure.structure_form.tensor_sha,
        )
    else:
        middle = _metric_map(verified_metric)
        left = _left_adjoint_map(
            transition_map,
            conjugate=True,
        )
        operands = (
            transition_view.transition.transition_sha,
            verified_metric.witness_sha,
            verified_metric.metric_kernel.tensor_sha,
        )
    planned_first_support, planned_second_support = (
        _preflight_convolution_chain(
            tuple(left),
            tuple(middle),
            tuple(transition_map),
            n_state,
        )
    )
    first, first_errors, first_pairs = _scalar_convolve(
        left,
        _zero_errors(left, n_state),
        middle,
        _zero_errors(middle, n_state),
        n_state,
    )
    if tuple(first) != planned_first_support:
        raise ValueError("first Laurent support differs from preflight")
    second, second_errors, second_pairs = _scalar_convolve(
        first,
        first_errors,
        transition_map,
        _zero_errors(transition_map, n_state),
        n_state,
    )
    if tuple(second) != planned_second_support:
        raise ValueError("second Laurent support differs from preflight")
    residual, residual_errors = _subtract_map(
        second,
        second_errors,
        middle,
        n_state,
    )
    exact_first = _exact_convolve(
        _exact_center_map(left),
        _exact_center_map(middle),
        n_state,
    )
    exact_second = _exact_convolve(
        exact_first,
        _exact_center_map(transition_map),
        n_state,
    )
    exact_residual = _exact_subtract_map(
        exact_second,
        _exact_center_map(middle),
        n_state,
    )
    support = tuple(sorted(residual))
    uppers = _coefficient_uppers(
        support,
        residual,
        residual_errors,
        exact_residual,
        n_state,
    )
    upper_sum = _coefficient_frobenius_upper_sum(
        support,
        residual,
        uppers,
    )
    evidence_body_bytes = _preflight_laurent_evidence_body(
        kind=kind,
        operands=operands,
        ndim=ndim,
        n_state=n_state,
        protocol_sha=verified_protocol.protocol_sha,
        support=support,
        centers=residual,
        pair_counts=(first_pairs, second_pairs),
        roundoff_uppers=uppers,
        upper_sum=upper_sum,
    )
    coefficient_tensor = freeze_complex_tensor(
        np.stack([residual[offset] for offset in support], axis=0)
    )
    provisional = LaurentResidualCertificate(
        residual_schema_version=LAURENT_RESIDUAL_SCHEMA_VERSION,
        residual_kind=kind,
        operand_shas=operands,
        spatial_ndim=ndim,
        n_state=n_state,
        fp64_enclosure_protocol_sha=verified_protocol.protocol_sha,
        fourier_convention_id=FOURIER_CONVENTION_ID,
        matrix_norm_id=MATRIX_NORM_ID,
        momentum_supremum_method_id=MOMENTUM_SUPREMUM_METHOD_ID,
        support_offsets=support,
        coefficients=coefficient_tensor,
        convolution_pair_counts=(first_pairs, second_pairs),
        coefficient_roundoff_frobenius_uppers=uppers,
        coefficient_frobenius_upper_sum=upper_sum,
        raw_global_momentum_supremum_bound=upper_sum,
        residual_sha="0" * 64,
    )
    if (
        _canonical_json_byte_count(laurent_residual_payload(provisional))
        != evidence_body_bytes
    ):
        raise ValueError("Laurent evidence byte preflight drifted")
    return replace(
        provisional,
        residual_sha=canonical_sha(laurent_residual_payload(provisional)),
    )


def certify_laurent_residuals(
    transition: VerifiedTransition,
    structure: StructureManifest,
    metric: StabilityMetricWitness,
    protocol: Fp64EnclosureProtocol,
) -> tuple[LaurentResidualCertificate, LaurentResidualCertificate]:
    """Build canonical-structure and metric residuals independently."""

    return (
        _build_residual(
            kind="canonical-structure",
            transition=transition,
            structure=structure,
            metric=metric,
            protocol=protocol,
        ),
        _build_residual(
            kind="stability-metric",
            transition=transition,
            structure=structure,
            metric=metric,
            protocol=protocol,
        ),
    )


def verify_laurent_residual_certificate(
    certificate: LaurentResidualCertificate,
    transition: VerifiedTransition,
    structure: StructureManifest,
    metric: StabilityMetricWitness,
    protocol: Fp64EnclosureProtocol,
) -> LaurentResidualCertificate:
    if type(certificate) is not LaurentResidualCertificate:
        raise TypeError("certificate must be a LaurentResidualCertificate")
    if certificate.residual_schema_version != LAURENT_RESIDUAL_SCHEMA_VERSION:
        raise ValueError("unexpected Laurent residual schema")
    _preflight_raw_laurent_evidence_body(certificate)
    if certificate.residual_sha != canonical_sha(
        laurent_residual_payload(certificate)
    ):
        raise ValueError("residual_sha does not match complete body")
    expected = _build_residual(
        kind=certificate.residual_kind,
        transition=transition,
        structure=structure,
        metric=metric,
        protocol=protocol,
    )
    if certificate.residual_sha != expected.residual_sha:
        raise ValueError("Laurent residual does not match reconstruction")
    return certificate


__all__ = [
    "FOURIER_CONVENTION_ID",
    "LAURENT_MAX_ARITHMETIC_WORK",
    "LAURENT_MAX_COEFFICIENT_ENTRIES",
    "LAURENT_MAX_PAIR_PRODUCT",
    "LAURENT_MAX_SUPPORT",
    "LAURENT_RESIDUAL_SCHEMA_VERSION",
    "MATRIX_NORM_ID",
    "MOMENTUM_SUPREMUM_METHOD_ID",
    "LaurentResidualCertificate",
    "certify_laurent_residuals",
    "laurent_residual_payload",
    "verify_laurent_residual_certificate",
]
