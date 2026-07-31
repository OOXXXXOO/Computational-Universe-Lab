"""Directed fp64 enclosure primitives for the V3-M0 hard-arithmetic lane.

This module intentionally excludes the root-of-unity table.  It provides the
small, reusable arithmetic slice needed by the later Task 10 certificate
builders: scalar policy, directed elementary operations, exact-ratio gamma and
Frobenius containment, complex-dot roundoff bounds, and the fixed T=16384
power-drift audit.
"""

from __future__ import annotations

import math
import re
import struct
import sys
from dataclasses import dataclass, fields
from fractions import Fraction
from typing import Optional, Union

import numpy as np

from rulespace_v3.evidence import canonical_sha


UNIT_ROUNDOFF_DENOMINATOR = 1 << 53
MINIMUM_SUBNORMAL_POWER_OF_TWO = -1074
MINIMUM_SUBNORMAL = math.ldexp(1.0, MINIMUM_SUBNORMAL_POWER_OF_TWO)
MINIMUM_NORMAL = sys.float_info.min
MAXIMUM_FINITE = sys.float_info.max

GAMMA_BOUND_METHOD_ID = "integer-ratio-q-u-over-one-minus-q-u-v1"
DOT_OPERATION_COUNT_ID = "complex-dot-real-component-q-equals-4n-minus-1-v1"
DOT_ROUNDOFF_BOUND_ID = "gamma-q-times-absolute-product-sum-plus-minsub-v1"
FROBENIUS_CONTAINMENT_ID = "exact-integer-ratio-square-containment-v1"
POWER_DRIFT_METHOD_ID = "t16384-directed-repeated-squaring-v1"
POWER_DRIFT_SCHEMA_VERSION = "v3m0-power-drift-audit-v1"
POWER_DRIFT_MACRO_STEP = 16384
POWER_DRIFT_SQUARING_COUNT = 14

_MINIMUM_NORMAL_BITS = 0x0010000000000000
_MAXIMUM_FINITE_BITS = 0x7FEFFFFFFFFFFFFF
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


Number = Union[int, float, Fraction]


def _float_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _float_from_bits(bits: int) -> float:
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


def is_positive_zero(value: object) -> bool:
    """Return true only for the binary64 +0.0 bit pattern."""

    return (
        isinstance(value, (float, np.float64))
        and float(value) == 0.0
        and math.copysign(1.0, float(value)) > 0.0
    )


def require_hard_scalar(value: object, name: str = "value") -> float:
    """Validate the hard-lane finite-normal-or-signed-zero policy."""

    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be an fp64 scalar, not bool")
    if not isinstance(value, (float, np.float64)):
        raise TypeError(f"{name} must be an fp64 scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if result != 0.0 and abs(result) < MINIMUM_NORMAL:
        raise ValueError(f"{name} must not be a nonzero subnormal")
    return result


def require_semantic_zero(value: object, name: str = "value") -> float:
    """Require the canonical semantic-zero representation (+0.0)."""

    result = require_hard_scalar(value, name)
    if not is_positive_zero(result):
        raise ValueError(f"{name} must be positive zero")
    return result


def _exact_fraction(value: float) -> Fraction:
    return Fraction(*value.as_integer_ratio())


def _directed_result(
    raw: float,
    exact: Fraction,
    toward: float,
    name: str,
) -> float:
    if not math.isfinite(raw):
        raise ValueError(f"{name} overflowed")
    if exact == 0:
        # An exactly representable cancellation needs no expansion.  Preserve
        # the IEEE sign selected by the scalar operation.
        return require_hard_scalar(raw, name)
    outward = math.nextafter(raw, toward)
    if not math.isfinite(outward):
        raise ValueError(f"{name} overflowed during outward rounding")
    return require_hard_scalar(outward, name)


def _directed_binary(
    left: object,
    right: object,
    operation: str,
    toward: float,
) -> float:
    a = require_hard_scalar(left, "left")
    b = require_hard_scalar(right, "right")
    af = _exact_fraction(a)
    bf = _exact_fraction(b)
    if operation == "add":
        return _directed_result(a + b, af + bf, toward, "addition")
    if operation == "sub":
        return _directed_result(a - b, af - bf, toward, "subtraction")
    if operation == "mul":
        return _directed_result(a * b, af * bf, toward, "multiplication")
    if operation == "div":
        if b == 0.0:
            raise ValueError("division denominator must be nonzero")
        return _directed_result(a / b, af / bf, toward, "division")
    raise AssertionError("unknown directed operation")


def directed_add_upper(left: object, right: object) -> float:
    return _directed_binary(left, right, "add", math.inf)


def directed_add_lower(left: object, right: object) -> float:
    return _directed_binary(left, right, "add", -math.inf)


def directed_sub_upper(left: object, right: object) -> float:
    return _directed_binary(left, right, "sub", math.inf)


def directed_sub_lower(left: object, right: object) -> float:
    return _directed_binary(left, right, "sub", -math.inf)


def directed_mul_upper(left: object, right: object) -> float:
    return _directed_binary(left, right, "mul", math.inf)


def directed_mul_lower(left: object, right: object) -> float:
    return _directed_binary(left, right, "mul", -math.inf)


def directed_div_upper(left: object, right: object) -> float:
    return _directed_binary(left, right, "div", math.inf)


def directed_div_lower(left: object, right: object) -> float:
    return _directed_binary(left, right, "div", -math.inf)


def _positive_float_fraction(bits: int) -> Fraction:
    return _exact_fraction(_float_from_bits(bits))


def _minimal_normal_float_upper(exact: Fraction, name: str) -> float:
    if exact <= 0:
        raise ValueError(f"{name} must be positive")
    if exact > _exact_fraction(MAXIMUM_FINITE):
        raise ValueError(f"{name} exceeds finite fp64 range")
    if exact <= _exact_fraction(MINIMUM_NORMAL):
        return MINIMUM_NORMAL

    lower = _MINIMUM_NORMAL_BITS
    upper = _MAXIMUM_FINITE_BITS
    while lower < upper:
        middle = (lower + upper) // 2
        if _positive_float_fraction(middle) >= exact:
            upper = middle
        else:
            lower = middle + 1
    return _float_from_bits(lower)


def complex_dot_q(length: object) -> int:
    """Return the frozen real-component operation count q=4n-1."""

    if isinstance(length, (bool, np.bool_)) or type(length) is not int:
        raise TypeError("length must be an int")
    if length <= 0:
        raise ValueError("length must be positive")
    q = 4 * length - 1
    if q >= UNIT_ROUNDOFF_DENOMINATOR:
        raise ValueError("complex dot operation count makes gamma undefined")
    return q


def _require_q(q: object) -> int:
    if isinstance(q, (bool, np.bool_)) or type(q) is not int:
        raise TypeError("q must be an int")
    if q <= 0 or q >= UNIT_ROUNDOFF_DENOMINATOR:
        raise ValueError("q must satisfy 0 < q < 2**53")
    return q


def _gamma_fraction(q: int) -> Fraction:
    return Fraction(q, UNIT_ROUNDOFF_DENOMINATOR - q)


def gamma_q_upper(q: object) -> float:
    """Return the tight normal fp64 upper for q*u/(1-q*u)."""

    checked = _require_q(q)
    return _minimal_normal_float_upper(_gamma_fraction(checked), "gamma_q")


def verify_gamma_q_upper(q: object, upper: object) -> float:
    """Verify gamma containment by exact as_integer_ratio cross products."""

    checked = _require_q(q)
    value = require_hard_scalar(upper, "gamma_q_upper")
    if value <= 0.0:
        raise ValueError("gamma_q_upper must be positive")
    numerator, denominator = value.as_integer_ratio()
    if numerator * (UNIT_ROUNDOFF_DENOMINATOR - checked) < checked * denominator:
        raise ValueError("gamma_q_upper is inward")
    return value


@dataclass(frozen=True)
class ComplexDotRoundoffBound:
    length: int
    q: int
    gamma_upper: float
    absolute_product_sum: float
    real_operation_count: int
    minimum_subnormal_numerator: int
    minimum_subnormal_power_of_two: int
    operation_count_id: str
    bound_method_id: str
    roundoff_upper: float


def _dot_roundoff_exact(
    gamma_upper: float,
    absolute_product_sum: float,
    real_operation_count: int,
) -> Fraction:
    return (
        _exact_fraction(gamma_upper) * _exact_fraction(absolute_product_sum)
        + Fraction(real_operation_count, 1 << 1074)
    )


def build_complex_dot_roundoff_bound(
    *,
    length: object,
    absolute_product_sum: object,
) -> ComplexDotRoundoffBound:
    q = complex_dot_q(length)
    product_sum = require_hard_scalar(
        absolute_product_sum,
        "absolute_product_sum",
    )
    if product_sum < 0.0:
        raise ValueError("absolute_product_sum must be nonnegative")
    gamma = gamma_q_upper(q)
    exact_bound = _dot_roundoff_exact(gamma, product_sum, q)
    upper = _minimal_normal_float_upper(exact_bound, "roundoff bound")
    return ComplexDotRoundoffBound(
        length=int(length),
        q=q,
        gamma_upper=gamma,
        absolute_product_sum=product_sum,
        real_operation_count=q,
        minimum_subnormal_numerator=q,
        minimum_subnormal_power_of_two=MINIMUM_SUBNORMAL_POWER_OF_TWO,
        operation_count_id=DOT_OPERATION_COUNT_ID,
        bound_method_id=DOT_ROUNDOFF_BOUND_ID,
        roundoff_upper=upper,
    )


def verify_complex_dot_roundoff_bound(
    bound: object,
) -> ComplexDotRoundoffBound:
    if not isinstance(bound, ComplexDotRoundoffBound):
        raise TypeError("bound must be a ComplexDotRoundoffBound")
    expected = build_complex_dot_roundoff_bound(
        length=bound.length,
        absolute_product_sum=bound.absolute_product_sum,
    )
    if bound != expected:
        raise ValueError("complex-dot roundoff bound does not match exact body")
    verify_gamma_q_upper(bound.q, bound.gamma_upper)
    if _float_bits(bound.roundoff_upper) != _float_bits(expected.roundoff_upper):
        raise ValueError("complex-dot roundoff upper is inward")
    return bound


def _as_nonnegative_fraction(value: Number, name: str) -> Fraction:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an int, Fraction, or fp64")
    if type(value) is int:
        result = Fraction(value, 1)
    elif isinstance(value, Fraction):
        result = value
    elif isinstance(value, (float, np.float64)):
        scalar = require_hard_scalar(value, name)
        result = _exact_fraction(scalar)
    else:
        raise TypeError(f"{name} must be an int, Fraction, or fp64")
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _square_contains(bits: int, radicand: Fraction) -> bool:
    candidate = _positive_float_fraction(bits)
    return candidate * candidate >= radicand


def frobenius_sqrt_upper(sum_squares_upper: Number) -> float:
    """Return the tight fp64 upper proved by exact integer-ratio squaring."""

    radicand = _as_nonnegative_fraction(
        sum_squares_upper,
        "sum_squares_upper",
    )
    if radicand == 0:
        return +0.0
    if _exact_fraction(MAXIMUM_FINITE) ** 2 < radicand:
        raise ValueError("Frobenius square root exceeds finite fp64 range")
    if _exact_fraction(MINIMUM_NORMAL) ** 2 >= radicand:
        return MINIMUM_NORMAL

    lower = _MINIMUM_NORMAL_BITS
    upper = _MAXIMUM_FINITE_BITS
    while lower < upper:
        middle = (lower + upper) // 2
        if _square_contains(middle, radicand):
            upper = middle
        else:
            lower = middle + 1
    return _float_from_bits(lower)


def verify_frobenius_sqrt_upper(
    sum_squares_upper: Number,
    stored_upper: object,
) -> float:
    radicand = _as_nonnegative_fraction(
        sum_squares_upper,
        "sum_squares_upper",
    )
    upper = require_hard_scalar(stored_upper, "frobenius_sqrt_upper")
    if radicand == 0:
        return require_semantic_zero(upper, "frobenius_sqrt_upper")
    if upper <= 0.0:
        raise ValueError("frobenius_sqrt_upper must be positive")
    squared = _exact_fraction(upper) ** 2
    if squared < radicand:
        raise ValueError("frobenius_sqrt_upper is inward")
    return upper


@dataclass(frozen=True)
class PowerDriftAudit:
    audit_schema_version: str
    normalized_metric_residual_audit_sha: str
    macro_step: int
    nonzero_delta_squaring_count: int
    executed_squaring_count: int
    identity_branch: bool
    method_id: str
    delta_upper: float
    one_minus_delta_lower: float
    one_plus_delta_upper: float
    growth_upper: float
    contraction_upper: float
    drift_upper: float
    audit_sha: str


def _power_drift_payload(audit: PowerDriftAudit) -> dict[str, object]:
    return {
        field.name: getattr(audit, field.name)
        for field in fields(PowerDriftAudit)
        if field.name != "audit_sha"
    }


def _require_sha(value: object, name: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256")
    return value


def _build_power_values(delta: float) -> tuple[float, float, float, float, float]:
    one_minus = directed_sub_lower(1.0, delta)
    one_plus = directed_add_upper(1.0, delta)
    lower_power = one_minus
    upper_power = one_plus
    for _ in range(POWER_DRIFT_SQUARING_COUNT):
        lower_power = directed_mul_lower(lower_power, lower_power)
        upper_power = directed_mul_upper(upper_power, upper_power)
    growth = directed_sub_upper(upper_power, 1.0)
    contraction = directed_sub_upper(1.0, lower_power)
    return one_minus, one_plus, growth, contraction, max(growth, contraction)


def build_power_drift_audit(
    delta_upper: object,
    *,
    normalized_metric_residual_audit_sha: str,
) -> PowerDriftAudit:
    """Build the fixed T=16384 directed repeated-squaring audit."""

    source_sha = _require_sha(
        normalized_metric_residual_audit_sha,
        "normalized_metric_residual_audit_sha",
    )
    delta = require_hard_scalar(delta_upper, "delta_upper")
    if delta < 0.0 or delta >= 1.0:
        raise ValueError("delta_upper must satisfy 0 <= delta < 1")
    if delta == 0.0:
        delta = +0.0
        values = {
            "executed_squaring_count": 0,
            "identity_branch": True,
            "one_minus_delta_lower": 1.0,
            "one_plus_delta_upper": 1.0,
            "growth_upper": +0.0,
            "contraction_upper": +0.0,
            "drift_upper": +0.0,
        }
    else:
        one_minus, one_plus, growth, contraction, drift = _build_power_values(
            delta
        )
        values = {
            "executed_squaring_count": POWER_DRIFT_SQUARING_COUNT,
            "identity_branch": False,
            "one_minus_delta_lower": one_minus,
            "one_plus_delta_upper": one_plus,
            "growth_upper": growth,
            "contraction_upper": contraction,
            "drift_upper": drift,
        }
    provisional = PowerDriftAudit(
        audit_schema_version=POWER_DRIFT_SCHEMA_VERSION,
        normalized_metric_residual_audit_sha=source_sha,
        macro_step=POWER_DRIFT_MACRO_STEP,
        nonzero_delta_squaring_count=POWER_DRIFT_SQUARING_COUNT,
        executed_squaring_count=values["executed_squaring_count"],
        identity_branch=values["identity_branch"],
        method_id=POWER_DRIFT_METHOD_ID,
        delta_upper=delta,
        one_minus_delta_lower=values["one_minus_delta_lower"],
        one_plus_delta_upper=values["one_plus_delta_upper"],
        growth_upper=values["growth_upper"],
        contraction_upper=values["contraction_upper"],
        drift_upper=values["drift_upper"],
        audit_sha="",
    )
    return PowerDriftAudit(
        **_power_drift_payload(provisional),
        audit_sha=canonical_sha(_power_drift_payload(provisional)),
    )


def _source_delta_and_sha(
    source: object,
    audit: PowerDriftAudit,
) -> tuple[float, str]:
    if source is None:
        return audit.delta_upper, audit.normalized_metric_residual_audit_sha
    if isinstance(source, (float, np.float64)):
        return require_hard_scalar(source, "expected delta"), (
            audit.normalized_metric_residual_audit_sha
        )
    if hasattr(source, "normalized_metric_residual_upper"):
        delta = require_hard_scalar(
            getattr(source, "normalized_metric_residual_upper"),
            "normalized_metric_residual_upper",
        )
    elif hasattr(source, "delta_upper"):
        delta = require_hard_scalar(getattr(source, "delta_upper"), "delta_upper")
    else:
        raise TypeError("normalized metric residual has no delta upper")
    source_sha = getattr(source, "audit_sha", None)
    return delta, _require_sha(source_sha, "normalized metric residual audit_sha")


def _same_fp64(left: float, right: float) -> bool:
    return _float_bits(left) == _float_bits(right)


def verify_power_drift_audit(
    audit: object,
    normalized_metric_residual: Optional[object] = None,
) -> PowerDriftAudit:
    """Recompute and strictly verify the fixed power-drift audit."""

    if not isinstance(audit, PowerDriftAudit):
        raise TypeError("audit must be a PowerDriftAudit")
    if audit.nonzero_delta_squaring_count != POWER_DRIFT_SQUARING_COUNT:
        raise ValueError("nonzero power drift squaring count must be 14")
    expected_executed = 0 if audit.identity_branch else POWER_DRIFT_SQUARING_COUNT
    if audit.executed_squaring_count != expected_executed:
        raise ValueError("executed power drift squaring count is invalid")
    delta, source_sha = _source_delta_and_sha(normalized_metric_residual, audit)
    expected = build_power_drift_audit(
        delta,
        normalized_metric_residual_audit_sha=source_sha,
    )
    for field_name in (
        "delta_upper",
        "one_minus_delta_lower",
        "one_plus_delta_upper",
        "growth_upper",
        "contraction_upper",
        "drift_upper",
    ):
        if not _same_fp64(
            getattr(audit, field_name),
            getattr(expected, field_name),
        ):
            raise ValueError("power drift audit has an inward or altered bound")
    if audit != expected:
        raise ValueError("power drift audit does not match the frozen method")
    return audit


__all__ = [
    "ComplexDotRoundoffBound",
    "FROBENIUS_CONTAINMENT_ID",
    "GAMMA_BOUND_METHOD_ID",
    "MAXIMUM_FINITE",
    "MINIMUM_NORMAL",
    "MINIMUM_SUBNORMAL",
    "MINIMUM_SUBNORMAL_POWER_OF_TWO",
    "POWER_DRIFT_MACRO_STEP",
    "POWER_DRIFT_METHOD_ID",
    "POWER_DRIFT_SQUARING_COUNT",
    "PowerDriftAudit",
    "UNIT_ROUNDOFF_DENOMINATOR",
    "build_complex_dot_roundoff_bound",
    "build_power_drift_audit",
    "complex_dot_q",
    "directed_add_lower",
    "directed_add_upper",
    "directed_div_lower",
    "directed_div_upper",
    "directed_mul_lower",
    "directed_mul_upper",
    "directed_sub_lower",
    "directed_sub_upper",
    "frobenius_sqrt_upper",
    "gamma_q_upper",
    "is_positive_zero",
    "require_hard_scalar",
    "require_semantic_zero",
    "verify_complex_dot_roundoff_bound",
    "verify_frobenius_sqrt_upper",
    "verify_gamma_q_upper",
    "verify_power_drift_audit",
]
