from __future__ import annotations

import math
import unittest
from dataclasses import replace
from fractions import Fraction
from unittest import mock

import numpy as np

from rulespace_v3.fp64 import (
    MINIMUM_NORMAL,
    MINIMUM_SUBNORMAL,
    PowerDriftAudit,
    build_complex_dot_roundoff_bound,
    build_power_drift_audit,
    complex_dot_q,
    directed_add_upper,
    directed_div_lower,
    directed_mul_upper,
    directed_sub_lower,
    frobenius_sqrt_upper,
    is_positive_zero,
    require_hard_scalar,
    require_semantic_zero,
    verify_complex_dot_roundoff_bound,
    verify_frobenius_sqrt_upper,
    verify_gamma_q_upper,
    verify_power_drift_audit,
    gamma_q_upper,
)


class HardScalarPolicyTests(unittest.TestCase):
    def test_signed_zero_is_hard_but_only_positive_zero_is_semantic(self):
        self.assertEqual(require_hard_scalar(+0.0), +0.0)
        self.assertEqual(
            math.copysign(1.0, require_hard_scalar(-0.0)),
            -1.0,
        )
        self.assertTrue(is_positive_zero(+0.0))
        self.assertFalse(is_positive_zero(-0.0))
        self.assertEqual(require_semantic_zero(+0.0), +0.0)
        with self.assertRaisesRegex(ValueError, "positive zero"):
            require_semantic_zero(-0.0)

    def test_nonzero_subnormal_nonfinite_and_bool_are_rejected(self):
        for value in (
            MINIMUM_SUBNORMAL,
            -MINIMUM_SUBNORMAL,
            math.nextafter(MINIMUM_NORMAL, 0.0),
            math.inf,
            -math.inf,
            math.nan,
        ):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    require_hard_scalar(value)
        with self.assertRaises(TypeError):
            require_hard_scalar(True)


class DirectedScalarOperationTests(unittest.TestCase):
    def test_each_nonzero_operation_moves_one_ulp_outward(self):
        self.assertEqual(
            directed_add_upper(1.0, 2.0),
            math.nextafter(3.0, math.inf),
        )
        self.assertEqual(
            directed_sub_lower(3.0, 1.0),
            math.nextafter(2.0, -math.inf),
        )
        self.assertEqual(
            directed_mul_upper(1.5, 2.0),
            math.nextafter(3.0, math.inf),
        )
        self.assertEqual(
            directed_div_lower(3.0, 2.0),
            math.nextafter(1.5, -math.inf),
        )

    def test_exact_zero_stays_signed_zero_and_overflow_is_rejected(self):
        self.assertTrue(is_positive_zero(directed_add_upper(+0.0, +0.0)))
        self.assertEqual(
            math.copysign(1.0, directed_sub_lower(-0.0, +0.0)),
            -1.0,
        )
        with self.assertRaisesRegex(ValueError, "overflow"):
            directed_mul_upper(float.fromhex("0x1.fffffffffffffp+1023"), 2.0)


class GammaAndDotBoundTests(unittest.TestCase):
    def test_complex_dot_q_and_gamma_are_exact_integer_ratio_upper(self):
        self.assertEqual(complex_dot_q(1), 3)
        self.assertEqual(complex_dot_q(7), 27)
        q = complex_dot_q(7)
        upper = gamma_q_upper(q)
        verify_gamma_q_upper(q, upper)
        previous = math.nextafter(upper, -math.inf)
        with self.assertRaisesRegex(ValueError, "inward"):
            verify_gamma_q_upper(q, previous)

        numerator, denominator = upper.as_integer_ratio()
        self.assertGreaterEqual(
            numerator * ((1 << 53) - q),
            q * denominator,
        )

    def test_dot_bound_binds_absolute_products_and_minsub_body(self):
        bound = build_complex_dot_roundoff_bound(
            length=3,
            absolute_product_sum=12.5,
        )
        self.assertEqual(bound.q, 11)
        self.assertEqual(bound.real_operation_count, 11)
        self.assertEqual(bound.minimum_subnormal_numerator, 11)
        self.assertEqual(bound.minimum_subnormal_power_of_two, -1074)
        self.assertEqual(bound.absolute_product_sum, 12.5)
        self.assertIs(verify_complex_dot_roundoff_bound(bound), bound)

        with self.assertRaisesRegex(ValueError, "roundoff"):
            verify_complex_dot_roundoff_bound(
                replace(
                    bound,
                    roundoff_upper=math.nextafter(
                        bound.roundoff_upper,
                        -math.inf,
                    ),
                )
            )


class FrobeniusContainmentTests(unittest.TestCase):
    def test_exact_ratio_square_containment_rejects_inward_ulp(self):
        radicand = Fraction(2, 1)
        upper = frobenius_sqrt_upper(radicand)
        self.assertGreaterEqual(
            Fraction(*upper.as_integer_ratio()) ** 2,
            radicand,
        )
        self.assertEqual(
            verify_frobenius_sqrt_upper(radicand, upper),
            upper,
        )
        with self.assertRaisesRegex(ValueError, "inward"):
            verify_frobenius_sqrt_upper(
                radicand,
                math.nextafter(upper, -math.inf),
            )

    def test_frobenius_upper_does_not_depend_on_libm_sqrt(self):
        with mock.patch("math.sqrt", side_effect=AssertionError("libm sqrt")):
            upper = frobenius_sqrt_upper(Fraction(10, 3))
        self.assertGreaterEqual(
            Fraction(*upper.as_integer_ratio()) ** 2,
            Fraction(10, 3),
        )


class PowerDriftTests(unittest.TestCase):
    def test_zero_delta_is_exact_identity_without_squaring(self):
        audit = build_power_drift_audit(
            +0.0,
            normalized_metric_residual_audit_sha="a" * 64,
        )
        self.assertIsInstance(audit, PowerDriftAudit)
        self.assertTrue(audit.identity_branch)
        self.assertEqual(audit.executed_squaring_count, 0)
        self.assertEqual(audit.one_minus_delta_lower, 1.0)
        self.assertEqual(audit.one_plus_delta_upper, 1.0)
        for value in (
            audit.delta_upper,
            audit.growth_upper,
            audit.contraction_upper,
            audit.drift_upper,
        ):
            self.assertTrue(is_positive_zero(value))
        self.assertIs(verify_power_drift_audit(audit), audit)

    def test_nonzero_delta_executes_exactly_fourteen_directed_squarings(self):
        with (
            mock.patch("builtins.pow", side_effect=AssertionError("pow")),
            mock.patch("math.exp", side_effect=AssertionError("exp")),
        ):
            audit = build_power_drift_audit(
                2.0 ** -50,
                normalized_metric_residual_audit_sha="b" * 64,
            )
        self.assertFalse(audit.identity_branch)
        self.assertEqual(audit.nonzero_delta_squaring_count, 14)
        self.assertEqual(audit.executed_squaring_count, 14)
        self.assertGreater(audit.growth_upper, 0.0)
        self.assertGreater(audit.contraction_upper, 0.0)
        self.assertEqual(
            audit.drift_upper,
            max(audit.growth_upper, audit.contraction_upper),
        )
        self.assertIs(verify_power_drift_audit(audit), audit)

        for bad_count in (13, 15):
            with self.subTest(bad_count=bad_count):
                with self.assertRaisesRegex(ValueError, "squaring"):
                    verify_power_drift_audit(
                        replace(audit, executed_squaring_count=bad_count)
                    )

    def test_power_audit_rejects_an_inward_one_ulp_bound(self):
        audit = build_power_drift_audit(
            2.0 ** -50,
            normalized_metric_residual_audit_sha="c" * 64,
        )
        with self.assertRaisesRegex(ValueError, "power drift"):
            verify_power_drift_audit(
                replace(
                    audit,
                    growth_upper=math.nextafter(
                        audit.growth_upper,
                        -math.inf,
                    ),
                )
            )


if __name__ == "__main__":
    unittest.main()
