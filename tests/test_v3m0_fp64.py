from __future__ import annotations

import inspect
import math
import unittest
from dataclasses import replace
from fractions import Fraction
from unittest import mock

import numpy as np

from rulespace_v3 import fp64 as fp64_module
from rulespace_v3.fp64 import (
    FP64_PRIMITIVES_SCOPE_ID,
    MINIMUM_NORMAL,
    MINIMUM_SUBNORMAL,
    PowerDriftBounds,
    build_complex_dot_roundoff_bound,
    complex_dot_q,
    compute_power_drift_bounds,
    directed_add_lower,
    directed_add_upper,
    directed_div_upper,
    directed_div_lower,
    directed_mul_lower,
    directed_mul_upper,
    directed_sub_upper,
    directed_sub_lower,
    frobenius_sqrt_upper,
    is_positive_zero,
    require_hard_scalar,
    require_semantic_zero,
    verify_complex_dot_roundoff_bound,
    verify_frobenius_sqrt_upper,
    verify_gamma_q_upper,
    gamma_q_upper,
)


class PublicSurfaceTests(unittest.TestCase):
    def test_fp64_primitives_expose_no_caller_self_signing_authority(self):
        forbidden_names = (
            "NormalizedMetricResidualAuthority",
            "PowerDriftAudit",
            "issue_normalized_metric_residual_authority",
            "build_power_drift_audit",
            "verify_power_drift_audit",
        )
        for name in forbidden_names:
            with self.subTest(name=name):
                self.assertFalse(hasattr(fp64_module, name))
                self.assertNotIn(name, fp64_module.__all__)
        self.assertEqual(
            tuple(inspect.signature(compute_power_drift_bounds).parameters),
            ("delta_upper",),
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
    def test_zero_delta_is_exact_identity_without_squaring(self):
        with (
            mock.patch(
                "rulespace_v3.fp64.directed_mul_lower",
                side_effect=AssertionError("lower square"),
            ),
            mock.patch(
                "rulespace_v3.fp64.directed_mul_upper",
                side_effect=AssertionError("upper square"),
            ),
        ):
            bounds = compute_power_drift_bounds(-0.0)
        self.assertIsInstance(bounds, PowerDriftBounds)
        self.assertTrue(bounds.identity_branch)
        self.assertEqual(bounds.executed_squaring_count, 0)
        self.assertEqual(bounds.one_minus_delta_lower, 1.0)
        self.assertEqual(bounds.one_plus_delta_upper, 1.0)
        for value in (
            bounds.delta_upper,
            bounds.growth_upper,
            bounds.contraction_upper,
            bounds.drift_upper,
        ):
            self.assertTrue(is_positive_zero(value))

    def test_nonzero_delta_executes_exactly_fourteen_directed_squarings(self):
        delta = 2.0 ** -50
        with (
            mock.patch("builtins.pow", side_effect=AssertionError("pow")),
            mock.patch("math.exp", side_effect=AssertionError("exp")),
        ):
            bounds = compute_power_drift_bounds(delta)
        self.assertFalse(bounds.identity_branch)
        self.assertEqual(bounds.nonzero_delta_squaring_count, 14)
        self.assertEqual(bounds.executed_squaring_count, 14)
        self.assertGreater(bounds.growth_upper, 0.0)
        self.assertGreater(bounds.contraction_upper, 0.0)
        self.assertEqual(
            bounds.drift_upper,
            max(bounds.growth_upper, bounds.contraction_upper),
        )

        exact_delta = Fraction(*delta.as_integer_ratio())
        exact_growth = (1 + exact_delta) ** bounds.macro_step - 1
        exact_contraction = 1 - (1 - exact_delta) ** bounds.macro_step
        self.assertGreaterEqual(
            Fraction(*bounds.growth_upper.as_integer_ratio()),
            exact_growth,
        )
        self.assertGreaterEqual(
            Fraction(*bounds.contraction_upper.as_integer_ratio()),
            exact_contraction,
        )

    def test_delta_one_e_minus_twelve_fails_the_drift_hard_gate(self):
        with self.assertRaisesRegex(ValueError, "1e-8 hard gate"):
            compute_power_drift_bounds(1.0e-12)

    def test_delta_accepts_only_hard_fp64_in_zero_to_one(self):
        for invalid in (None, True, 0, Fraction(0, 1), object()):
            with self.subTest(invalid=invalid):
                with self.assertRaises(TypeError):
                    compute_power_drift_bounds(invalid)
        for invalid in (-0.5, 1.0):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    compute_power_drift_bounds(invalid)

    def test_independent_instrumentation_observes_fourteen_squarings_per_branch(self):
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
            bounds = compute_power_drift_bounds(2.0 ** -50)
        self.assertEqual(lower_calls, 14)
        self.assertEqual(upper_calls, 14)
        self.assertEqual(1 << lower_calls, bounds.macro_step)


class StrictWireTests(unittest.TestCase):
    def test_wire_integer_fields_reject_bool_and_float_as_int(self):
        bounds = compute_power_drift_bounds(2.0 ** -50)
        with self.assertRaises(TypeError):
            replace(bounds, macro_step=True)
        with self.assertRaises(TypeError):
            replace(bounds, executed_squaring_count=14.0)

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
