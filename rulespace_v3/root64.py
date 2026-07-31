"""Exact dyadic containment table for the 64 binary64 roots of unity.

The hard path uses only integer and rational arithmetic.  A P=192 Machin
bracket for pi feeds alternating Taylor brackets on the first octant; exact
symmetries generate the other seven octants.  Every stored interval is then
proved to lie in its binary64 center's round-to-nearest-even cell.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Callable, Literal

from .evidence import canonical_sha


DYADIC_EXPONENT = 192
ROOT_DENOMINATOR = 64
DYADIC_SCALE = 1 << DYADIC_EXPONENT
DISTANCE_SQUARE_DENOMINATOR = 1 << (2 * DYADIC_EXPONENT)
TABLE_SCHEMA_VERSION = "v3m0.fp64-root-of-unity-interval-table.v1"
TABLE_ID = "root64-dyadic-machin-taylor-containment-v1"
MACHIN_IDENTITY_ID = "pi-equals-16atan1over5-minus4atan1over239-v1"
REMAINDER_METHOD_ID = "bigint-alternating-rational-remainder-v1"
AUDITED_ROOT64_TABLE_SHA = (
    "d54b51d9163589f405a859b494290248af69d680359f69b64d735d9a080570d8"
)
_SERIES_TOLERANCE = Fraction(1, 1 << (DYADIC_EXPONENT + 32))
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_POSITIVE_MAX_FINITE_BITS = 0x7FEFFFFFFFFFFFFF


@dataclass(frozen=True)
class Fp64RootIntervalEntry:
    root_index: int
    dyadic_exponent: Literal[192]
    real_lower_numerator: int
    real_upper_numerator: int
    imag_lower_numerator: int
    imag_upper_numerator: int
    real_center_f64_bits: int
    imag_center_f64_bits: int
    center_distance_squared_upper_numerator: int
    center_distance_squared_upper_power_of_two: Literal[-384]
    center_distance_upper_f64_bits: int


@dataclass(frozen=True)
class Fp64RootOfUnityIntervalTable:
    table_schema_version: str
    table_id: Literal["root64-dyadic-machin-taylor-containment-v1"]
    denominator: Literal[64]
    dyadic_exponent: Literal[192]
    pi_lower_numerator: int
    pi_upper_numerator: int
    machin_identity_id: Literal[
        "pi-equals-16atan1over5-minus4atan1over239-v1"
    ]
    taylor_precision_bits: Literal[192]
    remainder_method_id: Literal[
        "bigint-alternating-rational-remainder-v1"
    ]
    entries: tuple[Fp64RootIntervalEntry, ...]
    table_sha: str


def _entry_payload(entry: Fp64RootIntervalEntry) -> dict[str, object]:
    if not isinstance(entry, Fp64RootIntervalEntry):
        raise TypeError("entries must contain Fp64RootIntervalEntry values")
    return {
        "root_index": entry.root_index,
        "dyadic_exponent": entry.dyadic_exponent,
        "real_lower_numerator": entry.real_lower_numerator,
        "real_upper_numerator": entry.real_upper_numerator,
        "imag_lower_numerator": entry.imag_lower_numerator,
        "imag_upper_numerator": entry.imag_upper_numerator,
        "real_center_f64_bits": entry.real_center_f64_bits,
        "imag_center_f64_bits": entry.imag_center_f64_bits,
        "center_distance_squared_upper_numerator": (
            entry.center_distance_squared_upper_numerator
        ),
        "center_distance_squared_upper_power_of_two": (
            entry.center_distance_squared_upper_power_of_two
        ),
        "center_distance_upper_f64_bits": (
            entry.center_distance_upper_f64_bits
        ),
    }


def root64_table_payload(
    table: Fp64RootOfUnityIntervalTable,
) -> dict[str, object]:
    """Return the complete serializable table body, excluding ``table_sha``."""

    if not isinstance(table, Fp64RootOfUnityIntervalTable):
        raise TypeError("table must be an Fp64RootOfUnityIntervalTable")
    if type(table.entries) is not tuple:
        raise TypeError("entries must be a tuple")
    return {
        "table_schema_version": table.table_schema_version,
        "table_id": table.table_id,
        "denominator": table.denominator,
        "dyadic_exponent": table.dyadic_exponent,
        "pi_lower_numerator": table.pi_lower_numerator,
        "pi_upper_numerator": table.pi_upper_numerator,
        "machin_identity_id": table.machin_identity_id,
        "taylor_precision_bits": table.taylor_precision_bits,
        "remainder_method_id": table.remainder_method_id,
        "entries": [_entry_payload(entry) for entry in table.entries],
    }


def _alternating_bracket(
    term_at: Callable[[int], Fraction],
) -> tuple[Fraction, Fraction]:
    partial = Fraction(0)
    previous: Fraction | None = None
    for index in range(10_000):
        term = term_at(index)
        if term < 0:
            raise AssertionError("alternating-series magnitudes must be positive")
        if previous is not None and term > previous:
            raise AssertionError("alternating-series magnitudes must decrease")
        partial = partial + term if index % 2 == 0 else partial - term
        next_term = term_at(index + 1)
        if next_term < 0 or next_term > term:
            raise AssertionError("alternating-series remainder is not decreasing")
        if next_term <= _SERIES_TOLERANCE:
            adjacent = (
                partial - next_term
                if (index + 1) % 2 == 1
                else partial + next_term
            )
            return min(partial, adjacent), max(partial, adjacent)
        previous = term
    raise AssertionError("alternating-series bracket did not converge")


def _atan_reciprocal_bracket(denominator: int) -> tuple[Fraction, Fraction]:
    if type(denominator) is not int:
        raise TypeError("atan reciprocal denominator must be an int")
    if denominator <= 1:
        raise ValueError("atan reciprocal denominator must exceed one")

    def term_at(index: int) -> Fraction:
        return Fraction(
            1,
            (2 * index + 1) * denominator ** (2 * index + 1),
        )

    return _alternating_bracket(term_at)


def _floor_scaled(value: Fraction) -> int:
    return (value.numerator * DYADIC_SCALE) // value.denominator


def _ceil_scaled(value: Fraction) -> int:
    numerator = value.numerator * DYADIC_SCALE
    return -((-numerator) // value.denominator)


def _machin_pi_dyadic_bracket() -> tuple[int, int]:
    atan5_lower, atan5_upper = _atan_reciprocal_bracket(5)
    atan239_lower, atan239_upper = _atan_reciprocal_bracket(239)
    lower = 16 * atan5_lower - 4 * atan239_upper
    upper = 16 * atan5_upper - 4 * atan239_lower
    if not lower < upper:
        raise AssertionError("Machin construction did not bracket pi")
    return _floor_scaled(lower), _ceil_scaled(upper)


def _sin_bracket(value: Fraction) -> tuple[Fraction, Fraction]:
    if value < 0 or value > 1:
        raise ValueError("sine Taylor input must lie in [0,1]")

    def term_at(index: int) -> Fraction:
        numerator = value ** (2 * index + 1)
        factorial = 1
        for factor in range(2, 2 * index + 2):
            factorial *= factor
        return numerator / factorial

    return _alternating_bracket(term_at)


def _cos_bracket(value: Fraction) -> tuple[Fraction, Fraction]:
    if value < 0 or value > 1:
        raise ValueError("cosine Taylor input must lie in [0,1]")

    def term_at(index: int) -> Fraction:
        numerator = value ** (2 * index)
        factorial = 1
        for factor in range(2, 2 * index + 1):
            factorial *= factor
        return numerator / factorial

    return _alternating_bracket(term_at)


def _first_octant_intervals(
    pi_lower_numerator: int,
    pi_upper_numerator: int,
) -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
    rows: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for reduced_index in range(9):
        x_lower = Fraction(
            reduced_index * pi_lower_numerator,
            32 * DYADIC_SCALE,
        )
        x_upper = Fraction(
            reduced_index * pi_upper_numerator,
            32 * DYADIC_SCALE,
        )
        sin_lower, _ = _sin_bracket(x_lower)
        _, sin_upper = _sin_bracket(x_upper)
        cos_lower, _ = _cos_bracket(x_upper)
        _, cos_upper = _cos_bracket(x_lower)
        sine = (_floor_scaled(sin_lower), _ceil_scaled(sin_upper))
        cosine = (_floor_scaled(cos_lower), _ceil_scaled(cos_upper))
        if sine[0] > sine[1] or cosine[0] > cosine[1]:
            raise AssertionError("Taylor construction produced an empty interval")
        rows.append((cosine, sine))
    return tuple(rows)


def _negate_interval(interval: tuple[int, int]) -> tuple[int, int]:
    return -interval[1], -interval[0]


def _root_interval(
    root_index: int,
    first_octant: tuple[tuple[tuple[int, int], tuple[int, int]], ...],
) -> tuple[tuple[int, int], tuple[int, int]]:
    octant, offset = divmod(root_index, 8)
    reduced_index = offset if octant % 2 == 0 else 8 - offset
    cosine, sine = first_octant[reduced_index]
    if octant == 0:
        return cosine, sine
    if octant == 1:
        return sine, cosine
    if octant == 2:
        return _negate_interval(sine), cosine
    if octant == 3:
        return _negate_interval(cosine), sine
    if octant == 4:
        return _negate_interval(cosine), _negate_interval(sine)
    if octant == 5:
        return _negate_interval(sine), _negate_interval(cosine)
    if octant == 6:
        return sine, _negate_interval(cosine)
    if octant == 7:
        return cosine, _negate_interval(sine)
    raise AssertionError("root index escaped the eight octants")


def _float_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _float_from_bits(bits: int) -> float:
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


def _fraction_from_bits(bits: int) -> Fraction:
    value = _float_from_bits(bits)
    return Fraction(*value.as_integer_ratio())


def _rounding_cell(bits: int) -> tuple[Fraction, Fraction, bool]:
    value = _float_from_bits(bits)
    if value == 0.0:
        center = Fraction(0)
        predecessor = Fraction(-1, 1 << 1074)
        successor = Fraction(1, 1 << 1074)
    elif value > 0.0:
        center = _fraction_from_bits(bits)
        predecessor = _fraction_from_bits(bits - 1)
        successor = _fraction_from_bits(bits + 1)
    else:
        center = _fraction_from_bits(bits)
        predecessor = _fraction_from_bits(bits + 1)
        successor = _fraction_from_bits(bits - 1)
    return (
        (predecessor + center) / 2,
        (center + successor) / 2,
        bits & 1 == 0,
    )


def _center_bits_for_interval(lower: int, upper: int) -> int:
    midpoint = Fraction(lower + upper, 2 * DYADIC_SCALE)
    bits = _float_bits(float(midpoint))
    if bits & 0x7FF0000000000000 == 0x7FF0000000000000:
        raise AssertionError("root center is not finite")
    if lower == upper == 0:
        bits = 0
    cell_lower, cell_upper, center_is_even = _rounding_cell(bits)
    rational_lower = Fraction(lower, DYADIC_SCALE)
    rational_upper = Fraction(upper, DYADIC_SCALE)
    lower_inside = rational_lower > cell_lower or (
        rational_lower == cell_lower and center_is_even
    )
    upper_inside = rational_upper < cell_upper or (
        rational_upper == cell_upper and center_is_even
    )
    if not lower_inside or not upper_inside:
        raise AssertionError("dyadic root interval escaped its binary64 RN cell")
    return bits


def _scaled_center(bits: int) -> int:
    value = _fraction_from_bits(bits)
    scaled = value * DYADIC_SCALE
    if scaled.denominator != 1:
        raise AssertionError("binary64 root center is not representable at P=192")
    return scaled.numerator


def _square_covers(bits: int, target_numerator: int) -> bool:
    numerator, denominator = _float_from_bits(bits).as_integer_ratio()
    return (
        numerator * numerator * DISTANCE_SQUARE_DENOMINATOR
        >= target_numerator * denominator * denominator
    )


def _minimal_sqrt_upper_bits(target_numerator: int) -> int:
    if type(target_numerator) is not int:
        raise TypeError("target numerator must be an int")
    if target_numerator < 0:
        raise ValueError("target numerator must not be negative")
    if target_numerator == 0:
        return 0
    if not _square_covers(_POSITIVE_MAX_FINITE_BITS, target_numerator):
        raise OverflowError("distance upper does not fit binary64")
    lower = 0
    upper = _POSITIVE_MAX_FINITE_BITS
    while lower < upper:
        middle = (lower + upper) // 2
        if _square_covers(middle, target_numerator):
            upper = middle
        else:
            lower = middle + 1
    if lower == 0 or _square_covers(lower - 1, target_numerator):
        raise AssertionError("integer-ratio square upper is not minimal")
    return lower


def _build_entry(
    root_index: int,
    real_interval: tuple[int, int],
    imag_interval: tuple[int, int],
) -> Fp64RootIntervalEntry:
    real_lower, real_upper = real_interval
    imag_lower, imag_upper = imag_interval
    real_bits = _center_bits_for_interval(real_lower, real_upper)
    imag_bits = _center_bits_for_interval(imag_lower, imag_upper)
    real_center = _scaled_center(real_bits)
    imag_center = _scaled_center(imag_bits)
    real_error = max(
        abs(real_lower - real_center),
        abs(real_upper - real_center),
    )
    imag_error = max(
        abs(imag_lower - imag_center),
        abs(imag_upper - imag_center),
    )
    distance_square_numerator = real_error**2 + imag_error**2
    return Fp64RootIntervalEntry(
        root_index=root_index,
        dyadic_exponent=DYADIC_EXPONENT,
        real_lower_numerator=real_lower,
        real_upper_numerator=real_upper,
        imag_lower_numerator=imag_lower,
        imag_upper_numerator=imag_upper,
        real_center_f64_bits=real_bits,
        imag_center_f64_bits=imag_bits,
        center_distance_squared_upper_numerator=distance_square_numerator,
        center_distance_squared_upper_power_of_two=-2 * DYADIC_EXPONENT,
        center_distance_upper_f64_bits=_minimal_sqrt_upper_bits(
            distance_square_numerator
        ),
    )


def build_root64_interval_table() -> Fp64RootOfUnityIntervalTable:
    """Construct the canonical P=192 root-of-unity containment table."""

    pi_lower, pi_upper = _machin_pi_dyadic_bracket()
    first_octant = _first_octant_intervals(pi_lower, pi_upper)
    entries = tuple(
        _build_entry(root_index, *_root_interval(root_index, first_octant))
        for root_index in range(ROOT_DENOMINATOR)
    )
    provisional = Fp64RootOfUnityIntervalTable(
        table_schema_version=TABLE_SCHEMA_VERSION,
        table_id=TABLE_ID,
        denominator=ROOT_DENOMINATOR,
        dyadic_exponent=DYADIC_EXPONENT,
        pi_lower_numerator=pi_lower,
        pi_upper_numerator=pi_upper,
        machin_identity_id=MACHIN_IDENTITY_ID,
        taylor_precision_bits=DYADIC_EXPONENT,
        remainder_method_id=REMAINDER_METHOD_ID,
        entries=entries,
        table_sha="0" * 64,
    )
    return replace(
        provisional,
        table_sha=canonical_sha(root64_table_payload(provisional)),
    )


def _require_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    return value


def _validate_entry_shape(
    entry: Fp64RootIntervalEntry,
    expected_index: int,
) -> None:
    if not isinstance(entry, Fp64RootIntervalEntry):
        raise TypeError("entries must contain Fp64RootIntervalEntry values")
    values = {
        "root_index": entry.root_index,
        "dyadic_exponent": entry.dyadic_exponent,
        "real_lower_numerator": entry.real_lower_numerator,
        "real_upper_numerator": entry.real_upper_numerator,
        "imag_lower_numerator": entry.imag_lower_numerator,
        "imag_upper_numerator": entry.imag_upper_numerator,
        "real_center_f64_bits": entry.real_center_f64_bits,
        "imag_center_f64_bits": entry.imag_center_f64_bits,
        "center_distance_squared_upper_numerator": (
            entry.center_distance_squared_upper_numerator
        ),
        "center_distance_squared_upper_power_of_two": (
            entry.center_distance_squared_upper_power_of_two
        ),
        "center_distance_upper_f64_bits": (
            entry.center_distance_upper_f64_bits
        ),
    }
    for field, value in values.items():
        _require_int(value, f"entry[{expected_index}].{field}")
    if entry.root_index != expected_index:
        raise ValueError("entries must have canonical root_index order")
    if entry.dyadic_exponent != DYADIC_EXPONENT:
        raise ValueError("entry dyadic_exponent mismatch")
    if entry.real_lower_numerator > entry.real_upper_numerator:
        raise ValueError("real root interval is empty")
    if entry.imag_lower_numerator > entry.imag_upper_numerator:
        raise ValueError("imaginary root interval is empty")
    if entry.center_distance_squared_upper_numerator < 0:
        raise ValueError("center distance square must not be negative")
    if entry.center_distance_squared_upper_power_of_two != -384:
        raise ValueError("center distance square power mismatch")
    for field, bits in (
        ("real_center_f64_bits", entry.real_center_f64_bits),
        ("imag_center_f64_bits", entry.imag_center_f64_bits),
    ):
        if not 0 <= bits <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError(f"{field} must be an unsigned binary64 wire")
        if bits & 0x7FF0000000000000 == 0x7FF0000000000000:
            raise ValueError(f"{field} must encode a finite binary64 value")
    distance_bits = entry.center_distance_upper_f64_bits
    if not 0 <= distance_bits <= _POSITIVE_MAX_FINITE_BITS:
        raise ValueError(
            "center_distance_upper_f64_bits must encode a nonnegative finite value"
        )


def verify_root64_interval_table(
    table: Fp64RootOfUnityIntervalTable,
) -> Fp64RootOfUnityIntervalTable:
    """Rebuild and compare every exact containment and binary64 proof field."""

    if not isinstance(table, Fp64RootOfUnityIntervalTable):
        raise TypeError("table must be an Fp64RootOfUnityIntervalTable")
    if type(table.table_schema_version) is not str:
        raise TypeError("table_schema_version must be a str")
    if table.table_schema_version != TABLE_SCHEMA_VERSION:
        raise ValueError("unexpected table_schema_version")
    if table.table_id != TABLE_ID:
        raise ValueError("unexpected table_id")
    for field, value in (
        ("denominator", table.denominator),
        ("dyadic_exponent", table.dyadic_exponent),
        ("pi_lower_numerator", table.pi_lower_numerator),
        ("pi_upper_numerator", table.pi_upper_numerator),
        ("taylor_precision_bits", table.taylor_precision_bits),
    ):
        _require_int(value, field)
    if table.denominator != ROOT_DENOMINATOR:
        raise ValueError("root denominator mismatch")
    if table.dyadic_exponent != DYADIC_EXPONENT:
        raise ValueError("table dyadic_exponent mismatch")
    if table.taylor_precision_bits != DYADIC_EXPONENT:
        raise ValueError("Taylor precision mismatch")
    if table.pi_lower_numerator >= table.pi_upper_numerator:
        raise ValueError("pi interval must be nonempty")
    if table.machin_identity_id != MACHIN_IDENTITY_ID:
        raise ValueError("Machin identity mismatch")
    if table.remainder_method_id != REMAINDER_METHOD_ID:
        raise ValueError("remainder method mismatch")
    if type(table.entries) is not tuple:
        raise TypeError("entries must be a tuple")
    if len(table.entries) != ROOT_DENOMINATOR:
        raise ValueError("root64 table must contain exactly 64 entries")
    for expected_index, entry in enumerate(table.entries):
        _validate_entry_shape(entry, expected_index)
    if type(table.table_sha) is not str:
        raise TypeError("table_sha must be a str")
    if _LOWER_SHA256.fullmatch(table.table_sha) is None:
        raise ValueError("table_sha must be a lowercase SHA-256")
    if table.table_sha != canonical_sha(root64_table_payload(table)):
        raise ValueError("table_sha does not match the complete table body")
    if table.table_sha != AUDITED_ROOT64_TABLE_SHA:
        raise ValueError("table_sha does not match the audited root64 table")
    canonical = build_root64_interval_table()
    if table != canonical:
        raise ValueError(
            "table is not the canonical Machin/Taylor containment construction"
        )
    return table


build_fp64_root_of_unity_interval_table = build_root64_interval_table
verify_fp64_root_of_unity_interval_table = verify_root64_interval_table


__all__ = [
    "AUDITED_ROOT64_TABLE_SHA",
    "DYADIC_EXPONENT",
    "Fp64RootIntervalEntry",
    "Fp64RootOfUnityIntervalTable",
    "build_fp64_root_of_unity_interval_table",
    "build_root64_interval_table",
    "root64_table_payload",
    "verify_fp64_root_of_unity_interval_table",
    "verify_root64_interval_table",
]
