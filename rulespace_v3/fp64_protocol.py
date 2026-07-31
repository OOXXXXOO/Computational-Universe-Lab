"""Complete hard-arithmetic protocol binding fp64 primitives to Root64."""

from __future__ import annotations

import math
import re
import struct
import sys
from dataclasses import dataclass, replace
from typing import Literal

from .evidence import canonical_sha
from .fp64 import (
    DOT_OPERATION_COUNT_ID,
    DOT_ROUNDOFF_BOUND_ID,
    FROBENIUS_CONTAINMENT_ID,
    GAMMA_BOUND_METHOD_ID,
    MINIMUM_SUBNORMAL_POWER_OF_TWO,
    UNIT_ROUNDOFF_DENOMINATOR,
)
from .root64 import (
    Fp64RootOfUnityIntervalTable,
    build_root64_interval_table,
    root64_table_payload,
    verify_root64_interval_table,
)


FP64_PROTOCOL_SCHEMA_VERSION = "v3m0.fp64-enclosure-protocol.v1"
SCALAR_EXPRESSION_DAG_ID = (
    "ordered-four-real-products-and-additions-no-fma-v1"
)
GRADUAL_UNDERFLOW_ID = "real-operation-count-times-minsub-v1"
ROOT_CENTER_PROPAGATION_ID = (
    "coefficient-frobenius-sum-times-root-center-distance-v1"
)
FINITE_VALUE_POLICY = (
    "finite-normal-or-signed-zero-reject-nonzero-subnormal-ftz-nan-inf-"
    "overflow-v1"
)
OUTWARD_ROUNDING_ID = "nextafter-after-every-scalar-op-v1"
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")

_POSITIVE_ZERO_BITS = 0x0000000000000000
_MINIMUM_SUBNORMAL_BITS = 0x0000000000000001
_TWO_MINIMUM_SUBNORMAL_BITS = 0x0000000000000002
_HALF_MINIMUM_NORMAL_BITS = 0x0008000000000000
_MINIMUM_NORMAL_BITS = 0x0010000000000000
_HALF_ULP_AT_ONE_BITS = 0x3CA0000000000000
_HALF_BITS = 0x3FE0000000000000
_ONE_DOWN_BITS = 0x3FEFFFFFFFFFFFFF
_ONE_BITS = 0x3FF0000000000000
_ONE_UP_BITS = 0x3FF0000000000001
_ONE_TWO_ULPS_UP_BITS = 0x3FF0000000000002
_POSITIVE_INFINITY_BITS = 0x7FF0000000000000
_NEGATIVE_ZERO_BITS = 0x8000000000000000
_NEGATIVE_MINIMUM_SUBNORMAL_BITS = 0x8000000000000001
_NEGATIVE_ONE_BITS = 0xBFF0000000000000
_NEGATIVE_INFINITY_BITS = 0xFFF0000000000000


@dataclass(frozen=True)
class _Fp64RuntimeObservation:
    double_byte_width: int
    radix: int
    mantissa_digits: int
    minimum_exponent: int
    maximum_exponent: int
    tie_even_lower_result_bits: int
    tie_odd_lower_result_bits: int
    half_minimum_normal_result_bits: int
    minimum_subnormal_scaled_result_bits: int
    minimum_subnormal_sum_result_bits: int
    nextafter_positive_zero_up_bits: int
    nextafter_negative_zero_down_bits: int
    nextafter_positive_minsub_to_zero_bits: int
    nextafter_negative_minsub_to_zero_bits: int
    nextafter_one_up_bits: int
    nextafter_one_down_bits: int
    positive_zero_bits: int
    negative_zero_bits: int
    copied_negative_zero_bits: int
    negative_zero_sum_bits: int
    negative_zero_product_bits: int


def _runtime_float_from_bits(bits: int) -> float:
    if type(bits) is not int or not 0 <= bits < (1 << 64):
        raise TypeError("binary64 bits must be an unsigned 64-bit int")
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


def _runtime_float_bits(value: float) -> int:
    if type(value) is not float:
        raise TypeError("runtime binary64 value must be an exact float")
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _observe_fp64_runtime() -> _Fp64RuntimeObservation:
    """Execute the frozen scalar probes on runtime-constructed operands."""

    positive_zero = _runtime_float_from_bits(_POSITIVE_ZERO_BITS)
    negative_zero = _runtime_float_from_bits(_NEGATIVE_ZERO_BITS)
    minimum_subnormal = _runtime_float_from_bits(
        _MINIMUM_SUBNORMAL_BITS
    )
    negative_minimum_subnormal = _runtime_float_from_bits(
        _NEGATIVE_MINIMUM_SUBNORMAL_BITS
    )
    minimum_normal = _runtime_float_from_bits(_MINIMUM_NORMAL_BITS)
    half = _runtime_float_from_bits(_HALF_BITS)
    one = _runtime_float_from_bits(_ONE_BITS)
    one_up = _runtime_float_from_bits(_ONE_UP_BITS)
    half_ulp_at_one = _runtime_float_from_bits(_HALF_ULP_AT_ONE_BITS)
    positive_infinity = _runtime_float_from_bits(
        _POSITIVE_INFINITY_BITS
    )
    negative_one = _runtime_float_from_bits(_NEGATIVE_ONE_BITS)
    negative_infinity = _runtime_float_from_bits(
        _NEGATIVE_INFINITY_BITS
    )
    subnormal_scale = float(
        1 << (sys.float_info.mant_dig - 1)
    )
    return _Fp64RuntimeObservation(
        double_byte_width=struct.calcsize("d"),
        radix=sys.float_info.radix,
        mantissa_digits=sys.float_info.mant_dig,
        minimum_exponent=sys.float_info.min_exp,
        maximum_exponent=sys.float_info.max_exp,
        tie_even_lower_result_bits=_runtime_float_bits(
            one + half_ulp_at_one
        ),
        tie_odd_lower_result_bits=_runtime_float_bits(
            one_up + half_ulp_at_one
        ),
        half_minimum_normal_result_bits=_runtime_float_bits(
            minimum_normal * half
        ),
        minimum_subnormal_scaled_result_bits=_runtime_float_bits(
            minimum_subnormal * subnormal_scale
        ),
        minimum_subnormal_sum_result_bits=_runtime_float_bits(
            minimum_subnormal + minimum_subnormal
        ),
        nextafter_positive_zero_up_bits=_runtime_float_bits(
            math.nextafter(positive_zero, one)
        ),
        nextafter_negative_zero_down_bits=_runtime_float_bits(
            math.nextafter(negative_zero, negative_one)
        ),
        nextafter_positive_minsub_to_zero_bits=_runtime_float_bits(
            math.nextafter(minimum_subnormal, positive_zero)
        ),
        nextafter_negative_minsub_to_zero_bits=_runtime_float_bits(
            math.nextafter(negative_minimum_subnormal, positive_zero)
        ),
        nextafter_one_up_bits=_runtime_float_bits(
            math.nextafter(one, positive_infinity)
        ),
        nextafter_one_down_bits=_runtime_float_bits(
            math.nextafter(one, negative_infinity)
        ),
        positive_zero_bits=_runtime_float_bits(positive_zero),
        negative_zero_bits=_runtime_float_bits(negative_zero),
        copied_negative_zero_bits=_runtime_float_bits(
            math.copysign(positive_zero, negative_one)
        ),
        negative_zero_sum_bits=_runtime_float_bits(
            negative_zero + negative_zero
        ),
        negative_zero_product_bits=_runtime_float_bits(
            negative_zero * one
        ),
    )


def _verify_fp64_runtime_observation(
    observation: _Fp64RuntimeObservation,
) -> _Fp64RuntimeObservation:
    if type(observation) is not _Fp64RuntimeObservation:
        raise TypeError("runtime observation has the wrong exact type")
    expected = {
        "double_byte_width": 8,
        "radix": 2,
        "mantissa_digits": 53,
        "minimum_exponent": -1021,
        "maximum_exponent": 1024,
        "tie_even_lower_result_bits": _ONE_BITS,
        "tie_odd_lower_result_bits": _ONE_TWO_ULPS_UP_BITS,
        "half_minimum_normal_result_bits": _HALF_MINIMUM_NORMAL_BITS,
        "minimum_subnormal_scaled_result_bits": _MINIMUM_NORMAL_BITS,
        "minimum_subnormal_sum_result_bits": _TWO_MINIMUM_SUBNORMAL_BITS,
        "nextafter_positive_zero_up_bits": _MINIMUM_SUBNORMAL_BITS,
        "nextafter_negative_zero_down_bits": (
            _NEGATIVE_MINIMUM_SUBNORMAL_BITS
        ),
        "nextafter_positive_minsub_to_zero_bits": _POSITIVE_ZERO_BITS,
        "nextafter_negative_minsub_to_zero_bits": _NEGATIVE_ZERO_BITS,
        "nextafter_one_up_bits": _ONE_UP_BITS,
        "nextafter_one_down_bits": _ONE_DOWN_BITS,
        "positive_zero_bits": _POSITIVE_ZERO_BITS,
        "negative_zero_bits": _NEGATIVE_ZERO_BITS,
        "copied_negative_zero_bits": _NEGATIVE_ZERO_BITS,
        "negative_zero_sum_bits": _NEGATIVE_ZERO_BITS,
        "negative_zero_product_bits": _NEGATIVE_ZERO_BITS,
    }
    for field, frozen in expected.items():
        observed = getattr(observation, field)
        if type(observed) is not int:
            raise TypeError(f"{field} must be an exact int")
        if observed != frozen:
            raise ValueError(f"{field} does not match required fp64 semantics")
    return observation


def _require_fp64_runtime_environment() -> _Fp64RuntimeObservation:
    try:
        return _verify_fp64_runtime_observation(
            _observe_fp64_runtime()
        )
    except Exception as exc:
        raise RuntimeError(
            "fp64 runtime semantics are not certified"
        ) from exc


def _exact_int(value: object, expected: int, field: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value != expected:
        raise ValueError(f"{field} is not frozen")


def _exact_text(value: object, expected: str, field: str) -> None:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if value != expected:
        raise ValueError(f"{field} is not frozen")


@dataclass(frozen=True)
class Fp64EnclosureProtocol:
    protocol_schema_version: str
    unit_roundoff_numerator: Literal[1]
    unit_roundoff_denominator: Literal[9007199254740992]
    minimum_subnormal_numerator: Literal[1]
    minimum_subnormal_power_of_two: Literal[-1074]
    gamma_bound_method_id: Literal[
        "integer-ratio-q-u-over-one-minus-q-u-v1"
    ]
    complex_add_real_add_count: Literal[2]
    complex_multiply_real_multiply_count: Literal[4]
    complex_multiply_real_add_count: Literal[2]
    matrix_dot_operation_count_id: Literal[
        "complex-dot-real-component-q-equals-4n-minus-1-v1"
    ]
    scalar_expression_dag_id: Literal[
        "ordered-four-real-products-and-additions-no-fma-v1"
    ]
    roundoff_bound_id: Literal[
        "gamma-q-times-absolute-product-sum-plus-minsub-v1"
    ]
    gradual_underflow_additive_id: Literal[
        "real-operation-count-times-minsub-v1"
    ]
    root_center_error_propagation_id: Literal[
        "coefficient-frobenius-sum-times-root-center-distance-v1"
    ]
    frobenius_sqrt_containment_id: Literal[
        "exact-integer-ratio-square-containment-v1"
    ]
    fma_policy: Literal["forbidden"]
    reassociation_policy: Literal["forbidden"]
    finite_value_policy: Literal[
        "finite-normal-or-signed-zero-reject-nonzero-subnormal-ftz-nan-inf-overflow-v1"
    ]
    outward_rounding_id: Literal["nextafter-after-every-scalar-op-v1"]
    root_interval_table: Fp64RootOfUnityIntervalTable
    protocol_sha: str

    def __post_init__(self) -> None:
        if type(self.protocol_schema_version) is not str:
            raise TypeError("protocol_schema_version must be a string")
        _exact_int(self.unit_roundoff_numerator, 1, "unit_roundoff_numerator")
        _exact_int(
            self.unit_roundoff_denominator,
            UNIT_ROUNDOFF_DENOMINATOR,
            "unit_roundoff_denominator",
        )
        _exact_int(
            self.minimum_subnormal_numerator,
            1,
            "minimum_subnormal_numerator",
        )
        _exact_int(
            self.minimum_subnormal_power_of_two,
            MINIMUM_SUBNORMAL_POWER_OF_TWO,
            "minimum_subnormal_power_of_two",
        )
        for field, expected in (
            ("gamma_bound_method_id", GAMMA_BOUND_METHOD_ID),
            ("matrix_dot_operation_count_id", DOT_OPERATION_COUNT_ID),
            ("scalar_expression_dag_id", SCALAR_EXPRESSION_DAG_ID),
            ("roundoff_bound_id", DOT_ROUNDOFF_BOUND_ID),
            ("gradual_underflow_additive_id", GRADUAL_UNDERFLOW_ID),
            (
                "root_center_error_propagation_id",
                ROOT_CENTER_PROPAGATION_ID,
            ),
            (
                "frobenius_sqrt_containment_id",
                FROBENIUS_CONTAINMENT_ID,
            ),
            ("fma_policy", "forbidden"),
            ("reassociation_policy", "forbidden"),
            ("finite_value_policy", FINITE_VALUE_POLICY),
            ("outward_rounding_id", OUTWARD_ROUNDING_ID),
        ):
            _exact_text(getattr(self, field), expected, field)
        _exact_int(
            self.complex_add_real_add_count,
            2,
            "complex_add_real_add_count",
        )
        _exact_int(
            self.complex_multiply_real_multiply_count,
            4,
            "complex_multiply_real_multiply_count",
        )
        _exact_int(
            self.complex_multiply_real_add_count,
            2,
            "complex_multiply_real_add_count",
        )
        if not isinstance(
            self.root_interval_table,
            Fp64RootOfUnityIntervalTable,
        ):
            raise TypeError(
                "root_interval_table has the wrong record type"
            )
        if type(self.protocol_sha) is not str:
            raise TypeError("protocol_sha must be a string")
        if _LOWER_SHA.fullmatch(self.protocol_sha) is None:
            raise ValueError("protocol_sha must be a lowercase SHA-256")


def fp64_enclosure_protocol_payload(
    protocol: Fp64EnclosureProtocol,
) -> dict[str, object]:
    if not isinstance(protocol, Fp64EnclosureProtocol):
        raise TypeError("protocol must be an Fp64EnclosureProtocol")
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "unit_roundoff_numerator": protocol.unit_roundoff_numerator,
        "unit_roundoff_denominator": protocol.unit_roundoff_denominator,
        "minimum_subnormal_numerator": (
            protocol.minimum_subnormal_numerator
        ),
        "minimum_subnormal_power_of_two": (
            protocol.minimum_subnormal_power_of_two
        ),
        "gamma_bound_method_id": protocol.gamma_bound_method_id,
        "complex_add_real_add_count": (
            protocol.complex_add_real_add_count
        ),
        "complex_multiply_real_multiply_count": (
            protocol.complex_multiply_real_multiply_count
        ),
        "complex_multiply_real_add_count": (
            protocol.complex_multiply_real_add_count
        ),
        "matrix_dot_operation_count_id": (
            protocol.matrix_dot_operation_count_id
        ),
        "scalar_expression_dag_id": protocol.scalar_expression_dag_id,
        "roundoff_bound_id": protocol.roundoff_bound_id,
        "gradual_underflow_additive_id": (
            protocol.gradual_underflow_additive_id
        ),
        "root_center_error_propagation_id": (
            protocol.root_center_error_propagation_id
        ),
        "frobenius_sqrt_containment_id": (
            protocol.frobenius_sqrt_containment_id
        ),
        "fma_policy": protocol.fma_policy,
        "reassociation_policy": protocol.reassociation_policy,
        "finite_value_policy": protocol.finite_value_policy,
        "outward_rounding_id": protocol.outward_rounding_id,
        "root_interval_table": {
            **root64_table_payload(protocol.root_interval_table),
            "table_sha": protocol.root_interval_table.table_sha,
        },
    }


def _build_fp64_enclosure_protocol_body() -> Fp64EnclosureProtocol:
    table = build_root64_interval_table()
    provisional = Fp64EnclosureProtocol(
        protocol_schema_version=FP64_PROTOCOL_SCHEMA_VERSION,
        unit_roundoff_numerator=1,
        unit_roundoff_denominator=UNIT_ROUNDOFF_DENOMINATOR,
        minimum_subnormal_numerator=1,
        minimum_subnormal_power_of_two=MINIMUM_SUBNORMAL_POWER_OF_TWO,
        gamma_bound_method_id=GAMMA_BOUND_METHOD_ID,
        complex_add_real_add_count=2,
        complex_multiply_real_multiply_count=4,
        complex_multiply_real_add_count=2,
        matrix_dot_operation_count_id=DOT_OPERATION_COUNT_ID,
        scalar_expression_dag_id=SCALAR_EXPRESSION_DAG_ID,
        roundoff_bound_id=DOT_ROUNDOFF_BOUND_ID,
        gradual_underflow_additive_id=GRADUAL_UNDERFLOW_ID,
        root_center_error_propagation_id=ROOT_CENTER_PROPAGATION_ID,
        frobenius_sqrt_containment_id=FROBENIUS_CONTAINMENT_ID,
        fma_policy="forbidden",
        reassociation_policy="forbidden",
        finite_value_policy=FINITE_VALUE_POLICY,
        outward_rounding_id=OUTWARD_ROUNDING_ID,
        root_interval_table=table,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            fp64_enclosure_protocol_payload(provisional)
        ),
    )


def build_fp64_enclosure_protocol() -> Fp64EnclosureProtocol:
    _require_fp64_runtime_environment()
    return _build_fp64_enclosure_protocol_body()


def verify_fp64_enclosure_protocol(
    protocol: Fp64EnclosureProtocol,
) -> Fp64EnclosureProtocol:
    _require_fp64_runtime_environment()
    if type(protocol) is not Fp64EnclosureProtocol:
        raise TypeError("protocol must be an Fp64EnclosureProtocol")
    if protocol.protocol_schema_version != FP64_PROTOCOL_SCHEMA_VERSION:
        raise ValueError("unexpected fp64 protocol schema")
    verify_root64_interval_table(protocol.root_interval_table)
    if protocol.protocol_sha != canonical_sha(
        fp64_enclosure_protocol_payload(protocol)
    ):
        raise ValueError("protocol_sha does not match complete body")
    expected = _build_fp64_enclosure_protocol_body()
    if protocol.protocol_sha != expected.protocol_sha:
        raise ValueError("protocol does not match the closed construction")
    return protocol


__all__ = [
    "FINITE_VALUE_POLICY",
    "FP64_PROTOCOL_SCHEMA_VERSION",
    "GRADUAL_UNDERFLOW_ID",
    "OUTWARD_ROUNDING_ID",
    "ROOT_CENTER_PROPAGATION_ID",
    "SCALAR_EXPRESSION_DAG_ID",
    "Fp64EnclosureProtocol",
    "build_fp64_enclosure_protocol",
    "fp64_enclosure_protocol_payload",
    "verify_fp64_enclosure_protocol",
]
