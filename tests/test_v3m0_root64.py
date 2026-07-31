from __future__ import annotations

import cmath
import math
import struct
import unittest
from dataclasses import replace
from fractions import Fraction
from unittest import mock

from rulespace_v3.evidence import canonical_sha


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


def _assert_inside_rn_cell(
    test: unittest.TestCase,
    lower: Fraction,
    upper: Fraction,
    bits: int,
) -> None:
    cell_lower, cell_upper, center_is_even = _rounding_cell(bits)
    test.assertTrue(
        lower > cell_lower or (lower == cell_lower and center_is_even)
    )
    test.assertTrue(
        upper < cell_upper or (upper == cell_upper and center_is_even)
    )


class Root64IntervalTableTests(unittest.TestCase):
    def test_builds_complete_canonical_p192_table(self) -> None:
        from rulespace_v3.root64 import (
            build_root64_interval_table,
            verify_root64_interval_table,
        )

        table = build_root64_interval_table()
        self.assertIs(verify_root64_interval_table(table), table)
        self.assertEqual(
            table.table_id,
            "root64-dyadic-machin-taylor-containment-v1",
        )
        self.assertEqual(table.denominator, 64)
        self.assertEqual(table.dyadic_exponent, 192)
        self.assertEqual(table.taylor_precision_bits, 192)
        self.assertEqual(
            table.machin_identity_id,
            "pi-equals-16atan1over5-minus4atan1over239-v1",
        )
        self.assertEqual(
            table.remainder_method_id,
            "bigint-alternating-rational-remainder-v1",
        )
        self.assertEqual(len(table.entries), 64)
        self.assertEqual(
            tuple(entry.root_index for entry in table.entries),
            tuple(range(64)),
        )

        scale = 1 << 192
        pi_probe_digits = (
            "314159265358979323846264338327950288419716939937510582097494459230781640"
        )
        pi_probe = Fraction(int(pi_probe_digits), 10 ** (len(pi_probe_digits) - 1))
        self.assertLessEqual(Fraction(table.pi_lower_numerator, scale), pi_probe)
        self.assertGreaterEqual(Fraction(table.pi_upper_numerator, scale), pi_probe)
        self.assertLessEqual(
            table.pi_upper_numerator - table.pi_lower_numerator,
            2,
        )

    def test_every_interval_proves_binary64_center_rounding_cell(self) -> None:
        from rulespace_v3.root64 import build_root64_interval_table

        table = build_root64_interval_table()
        scale = 1 << table.dyadic_exponent
        for entry in table.entries:
            with self.subTest(root_index=entry.root_index):
                self.assertEqual(entry.dyadic_exponent, 192)
                real_lower = Fraction(entry.real_lower_numerator, scale)
                real_upper = Fraction(entry.real_upper_numerator, scale)
                imag_lower = Fraction(entry.imag_lower_numerator, scale)
                imag_upper = Fraction(entry.imag_upper_numerator, scale)
                self.assertLessEqual(real_lower, real_upper)
                self.assertLessEqual(imag_lower, imag_upper)
                _assert_inside_rn_cell(
                    self,
                    real_lower,
                    real_upper,
                    entry.real_center_f64_bits,
                )
                _assert_inside_rn_cell(
                    self,
                    imag_lower,
                    imag_upper,
                    entry.imag_center_f64_bits,
                )
                if real_lower == real_upper == 0:
                    self.assertEqual(entry.real_center_f64_bits, 0)
                if imag_lower == imag_upper == 0:
                    self.assertEqual(entry.imag_center_f64_bits, 0)

        canonical_axes = {
            0: (0x3FF0000000000000, 0),
            16: (0, 0x3FF0000000000000),
            32: (0xBFF0000000000000, 0),
            48: (0, 0xBFF0000000000000),
        }
        for index, expected_bits in canonical_axes.items():
            entry = table.entries[index]
            self.assertEqual(
                (entry.real_center_f64_bits, entry.imag_center_f64_bits),
                expected_bits,
            )

    def test_center_distance_square_and_minimal_integer_ratio_sqrt_upper(
        self,
    ) -> None:
        from rulespace_v3.root64 import build_root64_interval_table

        table = build_root64_interval_table()
        scale = 1 << table.dyadic_exponent
        square_denominator = 1 << (2 * table.dyadic_exponent)
        for entry in table.entries:
            with self.subTest(root_index=entry.root_index):
                real_center = _fraction_from_bits(entry.real_center_f64_bits)
                imag_center = _fraction_from_bits(entry.imag_center_f64_bits)
                real_center_scaled = real_center * scale
                imag_center_scaled = imag_center * scale
                self.assertEqual(real_center_scaled.denominator, 1)
                self.assertEqual(imag_center_scaled.denominator, 1)
                real_error = max(
                    abs(entry.real_lower_numerator - real_center_scaled.numerator),
                    abs(entry.real_upper_numerator - real_center_scaled.numerator),
                )
                imag_error = max(
                    abs(entry.imag_lower_numerator - imag_center_scaled.numerator),
                    abs(entry.imag_upper_numerator - imag_center_scaled.numerator),
                )
                expected_square_numerator = real_error**2 + imag_error**2
                self.assertEqual(
                    entry.center_distance_squared_upper_numerator,
                    expected_square_numerator,
                )
                self.assertEqual(
                    entry.center_distance_squared_upper_power_of_two,
                    -384,
                )

                target_square = Fraction(
                    expected_square_numerator,
                    square_denominator,
                )
                upper_bits = entry.center_distance_upper_f64_bits
                self.assertGreaterEqual(upper_bits, 0)
                self.assertLessEqual(upper_bits, 0x7FEFFFFFFFFFFFFF)
                upper = _fraction_from_bits(upper_bits)
                self.assertGreaterEqual(upper * upper, target_square)
                if expected_square_numerator == 0:
                    self.assertEqual(upper_bits, 0)
                else:
                    self.assertGreater(upper_bits, 0)
                    previous = _fraction_from_bits(upper_bits - 1)
                    self.assertLess(previous * previous, target_square)

    def test_verifier_rebuilds_math_after_recursive_resigning(self) -> None:
        from rulespace_v3.root64 import (
            build_root64_interval_table,
            root64_table_payload,
            verify_root64_interval_table,
        )

        table = build_root64_interval_table()
        first = replace(
            table.entries[1],
            real_lower_numerator=table.entries[1].real_lower_numerator + 1,
        )
        provisional = replace(
            table,
            entries=(table.entries[0], first, *table.entries[2:]),
            table_sha="0" * 64,
        )
        tampered = replace(
            provisional,
            table_sha=canonical_sha(root64_table_payload(provisional)),
        )
        with self.assertRaisesRegex(ValueError, "canonical|containment|entry"):
            verify_root64_interval_table(tampered)

        wrong_center = replace(
            table.entries[7],
            real_center_f64_bits=table.entries[7].real_center_f64_bits - 1,
        )
        provisional = replace(
            table,
            entries=(*table.entries[:7], wrong_center, *table.entries[8:]),
            table_sha="0" * 64,
        )
        tampered = replace(
            provisional,
            table_sha=canonical_sha(root64_table_payload(provisional)),
        )
        with self.assertRaisesRegex(ValueError, "canonical|rounding|entry"):
            verify_root64_interval_table(tampered)

    def test_strict_wire_types_and_order_are_enforced(self) -> None:
        from rulespace_v3.root64 import (
            build_root64_interval_table,
            root64_table_payload,
            verify_root64_interval_table,
        )

        table = build_root64_interval_table()
        malformed_entry = replace(table.entries[0], root_index=True)
        provisional = replace(
            table,
            entries=(malformed_entry, *table.entries[1:]),
            table_sha="0" * 64,
        )
        malformed = replace(
            provisional,
            table_sha=canonical_sha(root64_table_payload(provisional)),
        )
        with self.assertRaises(TypeError):
            verify_root64_interval_table(malformed)

        reordered_entries = (table.entries[1], table.entries[0], *table.entries[2:])
        provisional = replace(
            table,
            entries=reordered_entries,
            table_sha="0" * 64,
        )
        reordered = replace(
            provisional,
            table_sha=canonical_sha(root64_table_payload(provisional)),
        )
        with self.assertRaisesRegex(ValueError, "canonical|root_index|order"):
            verify_root64_interval_table(reordered)

    def test_hard_path_does_not_call_library_trigonometry(self) -> None:
        forbidden = mock.Mock(side_effect=AssertionError("libm trig called"))
        with (
            mock.patch.object(math, "sin", forbidden),
            mock.patch.object(math, "cos", forbidden),
            mock.patch.object(cmath, "exp", forbidden),
        ):
            from rulespace_v3.root64 import (
                build_root64_interval_table,
                verify_root64_interval_table,
            )

            table = build_root64_interval_table()
            self.assertIs(verify_root64_interval_table(table), table)
        self.assertEqual(forbidden.call_count, 0)


if __name__ == "__main__":
    unittest.main()
