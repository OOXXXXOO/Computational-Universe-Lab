from __future__ import annotations

import math
import unittest
from dataclasses import replace
from fractions import Fraction
from unittest import mock

import numpy as np

from rulespace_v3.fp64 import (
    FP64_PRIMITIVES_SCOPE_ID,
    MINIMUM_NORMAL,
    MINIMUM_SUBNORMAL,
    NormalizedMetricResidualAuthority,
    PowerDriftAudit,
    build_complex_dot_roundoff_bound,
    build_power_drift_audit,
    complex_dot_q,
    directed_add_lower,
    directed_add_upper,
    directed_div_upper,
    directed_div_lower,
    directed_mul_lower,
    directed_mul_upper,
    directed_sub_upper,
    directed_sub_lower,
    frobenius_sqrt_upper,
    issue_normalized_metric_residual_authority,
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

    def test_all_eight_apis_enclose_inexact_and_negative_exact_results(self):
        cases = (
            (directed_add_lower, 0.1, 0.2, "lower"),
            (directed_add_upper, -0.1, -0.2, "upper"),
            (directed_sub_lower, -0.1, 0.2, "lower"),
            (directed_sub_upper, 0.1, -0.2, "upper"),
            (directed_mul_lower, -0.1, 0.2, "lower"),
            (directed_mul_upper, 0.1, 0.2, "upper"),
            (directed_div_lower, -0.1, 0.2, "lower"),
            (directed_div_upper, 0.1, 0.2, "upper"),
        )
        for operation, left, right, direction in cases:
            with self.subTest(operation=operation.__name__):
                value = operation(left, right)
                binary_exact = {
                    directed_add_lower: Fraction(*left.as_integer_ratio())
                    + Fraction(*right.as_integer_ratio()),
                    directed_add_upper: Fraction(*left.as_integer_ratio())
                    + Fraction(*right.as_integer_ratio()),
                    directed_sub_lower: Fraction(*left.as_integer_ratio())
                    - Fraction(*right.as_integer_ratio()),
                    directed_sub_upper: Fraction(*left.as_integer_ratio())
                    - Fraction(*right.as_integer_ratio()),
                    directed_mul_lower: Fraction(*left.as_integer_ratio())
                    * Fraction(*right.as_integer_ratio()),
                    directed_mul_upper: Fraction(*left.as_integer_ratio())
                    * Fraction(*right.as_integer_ratio()),
                    directed_div_lower: Fraction(*left.as_integer_ratio())
                    / Fraction(*right.as_integer_ratio()),
                    directed_div_upper: Fraction(*left.as_integer_ratio())
                    / Fraction(*right.as_integer_ratio()),
                }[operation]
                stored = Fraction(*value.as_integer_ratio())
                if direction == "lower":
                    self.assertLessEqual(stored, binary_exact)
                else:
                    self.assertGreaterEqual(stored, binary_exact)


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

    def test_q_rejects_bool_zero_and_gamma_singular_boundary(self):
        with self.assertRaises(TypeError):
            complex_dot_q(True)
        with self.assertRaises(ValueError):
            complex_dot_q(0)
        with self.assertRaises(TypeError):
            gamma_q_upper(True)
        with self.assertRaises(ValueError):
            gamma_q_upper(1 << 53)

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

    def test_zero_negative_and_minimum_normal_boundaries(self):
        self.assertTrue(is_positive_zero(frobenius_sqrt_upper(Fraction(0, 1))))
        with self.assertRaises(ValueError):
            frobenius_sqrt_upper(Fraction(-1, 3))

        minimum_normal = Fraction(*MINIMUM_NORMAL.as_integer_ratio())
        radicand = minimum_normal * minimum_normal
        self.assertEqual(frobenius_sqrt_upper(radicand), MINIMUM_NORMAL)
        self.assertEqual(
            verify_frobenius_sqrt_upper(radicand, MINIMUM_NORMAL),
            MINIMUM_NORMAL,
        )
        with self.assertRaises((ValueError, TypeError)):
            verify_frobenius_sqrt_upper(
                radicand,
                math.nextafter(MINIMUM_NORMAL, 0.0),
            )


class PowerDriftTests(unittest.TestCase):
    @staticmethod
    def authority(
        delta: float,
        character: str,
    ) -> NormalizedMetricResidualAuthority:
        return issue_normalized_metric_residual_authority(
            audit_sha=character * 64,
            delta_upper=delta,
        )

    def test_zero_delta_is_exact_identity_without_squaring(self):
        authority = self.authority(+0.0, "a")
        audit = build_power_drift_audit(authority)
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
        self.assertIs(verify_power_drift_audit(audit, authority), audit)

    def test_nonzero_delta_executes_exactly_fourteen_directed_squarings(self):
        authority = self.authority(2.0 ** -50, "b")
        with (
            mock.patch("builtins.pow", side_effect=AssertionError("pow")),
            mock.patch("math.exp", side_effect=AssertionError("exp")),
        ):
            audit = build_power_drift_audit(authority)
        self.assertFalse(audit.identity_branch)
        self.assertEqual(audit.nonzero_delta_squaring_count, 14)
        self.assertEqual(audit.executed_squaring_count, 14)
        self.assertGreater(audit.growth_upper, 0.0)
        self.assertGreater(audit.contraction_upper, 0.0)
        self.assertEqual(
            audit.drift_upper,
            max(audit.growth_upper, audit.contraction_upper),
        )
        self.assertIs(verify_power_drift_audit(audit, authority), audit)

        for bad_count in (13, 15):
            with self.subTest(bad_count=bad_count):
                with self.assertRaisesRegex(ValueError, "squaring"):
                    verify_power_drift_audit(
                        replace(audit, executed_squaring_count=bad_count),
                        authority,
                    )

    def test_power_audit_rejects_an_inward_one_ulp_bound(self):
        authority = self.authority(2.0 ** -50, "c")
        audit = build_power_drift_audit(authority)
        with self.assertRaisesRegex(ValueError, "power drift"):
            verify_power_drift_audit(
                replace(
                    audit,
                    growth_upper=math.nextafter(
                        audit.growth_upper,
                        -math.inf,
                    ),
                ),
                authority,
            )

    def test_delta_one_e_minus_twelve_fails_the_drift_hard_gate(self):
        authority = self.authority(1.0e-12, "d")
        with self.assertRaisesRegex(ValueError, "1e-8 hard gate"):
            build_power_drift_audit(authority)

    def test_verifier_requires_the_exact_module_issued_authority(self):
        authority = self.authority(2.0 ** -50, "e")
        audit = build_power_drift_audit(authority)
        for invalid in (None, 2.0 ** -50, object()):
            with self.subTest(invalid=invalid):
                with self.assertRaises(TypeError):
                    verify_power_drift_audit(audit, invalid)  # type: ignore[arg-type]

        class Duck:
            audit_sha = "e" * 64
            delta_upper = 2.0 ** -50

        with self.assertRaises(TypeError):
            verify_power_drift_audit(audit, Duck())  # type: ignore[arg-type]

        unissued = object.__new__(NormalizedMetricResidualAuthority)
        object.__setattr__(unissued, "_audit_sha", "e" * 64)
        object.__setattr__(unissued, "_delta_upper", 2.0 ** -50)
        with self.assertRaisesRegex(ValueError, "unissued"):
            verify_power_drift_audit(audit, unissued)

        wrong_sha = self.authority(2.0 ** -50, "f")
        with self.assertRaisesRegex(ValueError, "authority"):
            verify_power_drift_audit(audit, wrong_sha)

    def test_independent_instrumentation_observes_fourteen_squarings_per_branch(self):
        authority = self.authority(2.0 ** -50, "1")
        lower_calls = 0
        upper_calls = 0
        real_lower = directed_mul_lower
        real_upper = directed_mul_upper

        def instrument_lower(left: object, right: object) -> float:
            nonlocal lower_calls
            lower_calls += 1
            return real_lower(left, right)

        def instrument_upper(left: object, right: object) -> float:
            nonlocal upper_calls
            upper_calls += 1
            return real_upper(left, right)

        with (
            mock.patch("rulespace_v3.fp64.directed_mul_lower", instrument_lower),
            mock.patch("rulespace_v3.fp64.directed_mul_upper", instrument_upper),
        ):
            audit = build_power_drift_audit(authority)
        self.assertEqual(lower_calls, 14)
        self.assertEqual(upper_calls, 14)
        self.assertEqual(1 << lower_calls, audit.macro_step)


class StrictWireTests(unittest.TestCase):
    def test_wire_integer_fields_reject_bool_and_float_as_int(self):
        authority = PowerDriftTests.authority(2.0 ** -50, "2")
        audit = build_power_drift_audit(authority)
        with self.assertRaises(TypeError):
            replace(audit, macro_step=True)
        with self.assertRaises(TypeError):
            replace(audit, executed_squaring_count=14.0)

        bound = build_complex_dot_roundoff_bound(
            length=2,
            absolute_product_sum=1.0,
        )
        with self.assertRaises(TypeError):
            replace(bound, q=True)
        with self.assertRaises(TypeError):
            replace(bound, real_operation_count=7.0)

    def test_scope_is_explicitly_primitives_without_root_table(self):
        self.assertEqual(
            FP64_PRIMITIVES_SCOPE_ID,
            "directed-fp64-primitives-without-root64-v1",
        )


if __name__ == "__main__":
    unittest.main()
