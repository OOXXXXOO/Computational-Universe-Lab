from __future__ import annotations

import dataclasses
import inspect
import unittest
from unittest import mock

import rulespace_v3.fp64_protocol as fp64_protocol_module
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.fp64_protocol import (
    _Fp64RuntimeObservation,
    _observe_fp64_runtime,
    _require_fp64_runtime_environment,
    _runtime_float_bits,
    _runtime_float_from_bits,
    _verify_fp64_runtime_observation,
    build_fp64_enclosure_protocol,
    fp64_enclosure_protocol_payload,
    verify_fp64_enclosure_protocol,
)
from rulespace_v3.root64 import AUDITED_ROOT64_TABLE_SHA


class Fp64EnclosureProtocolTests(unittest.TestCase):
    def test_protocol_recursively_binds_audited_root64_table(self):
        protocol = build_fp64_enclosure_protocol()
        self.assertEqual(protocol.unit_roundoff_numerator, 1)
        self.assertEqual(
            protocol.unit_roundoff_denominator,
            2**53,
        )
        self.assertEqual(protocol.minimum_subnormal_power_of_two, -1074)
        self.assertEqual(protocol.fma_policy, "forbidden")
        self.assertEqual(protocol.reassociation_policy, "forbidden")
        self.assertEqual(
            protocol.root_interval_table.table_sha,
            AUDITED_ROOT64_TABLE_SHA,
        )
        self.assertEqual(
            verify_fp64_enclosure_protocol(protocol),
            protocol,
        )

    def test_caller_resigned_protocol_cannot_change_policy(self):
        protocol = build_fp64_enclosure_protocol()
        changed = dataclasses.replace(
            protocol,
            protocol_schema_version="caller-policy-v1",
            protocol_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            protocol_sha=canonical_sha(
                fp64_enclosure_protocol_payload(changed)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_fp64_enclosure_protocol(changed)


class Fp64RuntimeSemanticsTests(unittest.TestCase):
    _EXPECTED_BITS = {
        "double_byte_width": 8,
        "radix": 2,
        "mantissa_digits": 53,
        "minimum_exponent": -1021,
        "maximum_exponent": 1024,
        "tie_even_lower_result_bits": 0x3FF0000000000000,
        "tie_odd_lower_result_bits": 0x3FF0000000000002,
        "half_minimum_normal_result_bits": 0x0008000000000000,
        "minimum_subnormal_scaled_result_bits": 0x0010000000000000,
        "minimum_subnormal_sum_result_bits": 0x0000000000000002,
        "nextafter_positive_zero_up_bits": 0x0000000000000001,
        "nextafter_negative_zero_down_bits": 0x8000000000000001,
        "nextafter_positive_minsub_to_zero_bits": 0x0000000000000000,
        "nextafter_negative_minsub_to_zero_bits": 0x8000000000000000,
        "nextafter_one_up_bits": 0x3FF0000000000001,
        "nextafter_one_down_bits": 0x3FEFFFFFFFFFFFFF,
        "positive_zero_bits": 0x0000000000000000,
        "negative_zero_bits": 0x8000000000000000,
        "copied_negative_zero_bits": 0x8000000000000000,
        "negative_zero_sum_bits": 0x8000000000000000,
        "negative_zero_product_bits": 0x8000000000000000,
    }

    def test_current_runtime_observation_matches_every_exact_bit(self) -> None:
        observation = _observe_fp64_runtime()
        self.assertIsInstance(observation, _Fp64RuntimeObservation)
        for field, expected in self._EXPECTED_BITS.items():
            with self.subTest(field=field):
                self.assertEqual(getattr(observation, field), expected)
                self.assertIs(type(getattr(observation, field)), int)
        self.assertIs(
            _verify_fp64_runtime_observation(observation),
            observation,
        )
        self.assertEqual(_require_fp64_runtime_environment(), observation)

    def test_every_observation_field_is_a_fail_closed_exact_gate(self) -> None:
        observation = _observe_fp64_runtime()
        self.assertEqual(
            {field.name for field in dataclasses.fields(observation)},
            set(self._EXPECTED_BITS),
        )
        for field in dataclasses.fields(observation):
            with self.subTest(field=field.name):
                changed = dataclasses.replace(
                    observation,
                    **{field.name: getattr(observation, field.name) + 1},
                )
                with self.assertRaises((TypeError, ValueError)):
                    _verify_fp64_runtime_observation(changed)
        with self.assertRaises(TypeError):
            _verify_fp64_runtime_observation(
                dataclasses.replace(observation, double_byte_width=True)
            )

    def test_non_nearest_rounding_mode_observations_are_rejected(self) -> None:
        observation = _observe_fp64_runtime()
        simulated_non_nearest = {
            "upward": dataclasses.replace(
                observation,
                tie_even_lower_result_bits=0x3FF0000000000001,
            ),
            "downward-or-toward-zero": dataclasses.replace(
                observation,
                tie_odd_lower_result_bits=0x3FF0000000000001,
            ),
        }
        for mode, changed in simulated_non_nearest.items():
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    _verify_fp64_runtime_observation(changed)

    def test_ftz_daz_nextafter_and_signed_zero_failures_are_rejected(
        self,
    ) -> None:
        observation = _observe_fp64_runtime()
        changed_by_failure = {
            "ftz": dataclasses.replace(
                observation,
                half_minimum_normal_result_bits=0,
            ),
            "daz": dataclasses.replace(
                observation,
                minimum_subnormal_scaled_result_bits=0,
            ),
            "nextafter": dataclasses.replace(
                observation,
                nextafter_positive_zero_up_bits=0,
            ),
            "signed-zero": dataclasses.replace(
                observation,
                negative_zero_sum_bits=0,
            ),
        }
        for failure, changed in changed_by_failure.items():
            with self.subTest(failure=failure):
                with self.assertRaises(ValueError):
                    _verify_fp64_runtime_observation(changed)

    def test_public_build_and_verify_reject_each_mutated_observation(
        self,
    ) -> None:
        protocol = build_fp64_enclosure_protocol()
        observation = _observe_fp64_runtime()
        for field in dataclasses.fields(observation):
            changed = dataclasses.replace(
                observation,
                **{field.name: getattr(observation, field.name) + 1},
            )
            with (
                self.subTest(field=field.name),
                mock.patch.object(
                    fp64_protocol_module,
                    "_observe_fp64_runtime",
                    return_value=changed,
                ),
            ):
                for operation in (
                    build_fp64_enclosure_protocol,
                    lambda: verify_fp64_enclosure_protocol(protocol),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "fp64 runtime semantics are not certified",
                    ) as caught:
                        operation()
                    self.assertIsNotNone(caught.exception.__cause__)

    def test_runtime_probe_exceptions_are_uniformly_fail_closed(self) -> None:
        protocol = build_fp64_enclosure_protocol()
        patches = {
            "observer": mock.patch.object(
                fp64_protocol_module,
                "_observe_fp64_runtime",
                side_effect=FloatingPointError("observer"),
            ),
            "pack": mock.patch.object(
                fp64_protocol_module.struct,
                "pack",
                side_effect=RuntimeError("pack"),
            ),
            "nextafter": mock.patch.object(
                fp64_protocol_module.math,
                "nextafter",
                side_effect=RuntimeError("nextafter"),
            ),
            "validator": mock.patch.object(
                fp64_protocol_module,
                "_verify_fp64_runtime_observation",
                side_effect=ValueError("validator"),
            ),
        }
        for failure, patcher in patches.items():
            with self.subTest(failure=failure), patcher:
                for operation in (
                    build_fp64_enclosure_protocol,
                    lambda: verify_fp64_enclosure_protocol(protocol),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "fp64 runtime semantics are not certified",
                    ) as caught:
                        operation()
                    self.assertIsNotNone(caught.exception.__cause__)

    def test_probe_inputs_are_runtime_bits_and_public_wire_is_unchanged(
        self,
    ) -> None:
        source = "\n".join(
            (
                inspect.getsource(_runtime_float_from_bits),
                inspect.getsource(_runtime_float_bits),
                inspect.getsource(_observe_fp64_runtime),
            )
        )
        self.assertIn("struct.pack", source)
        self.assertIn("struct.unpack", source)
        self.assertIn("sys.float_info.mant_dig", source)
        self.assertNotIn("float.fromhex", source)
        self.assertNotIn("math.ldexp", source)
        self.assertEqual(
            tuple(inspect.signature(build_fp64_enclosure_protocol).parameters),
            (),
        )
        self.assertEqual(
            tuple(inspect.signature(verify_fp64_enclosure_protocol).parameters),
            ("protocol",),
        )
        protocol = build_fp64_enclosure_protocol()
        self.assertEqual(
            set(fp64_enclosure_protocol_payload(protocol)),
            {
                "protocol_schema_version",
                "unit_roundoff_numerator",
                "unit_roundoff_denominator",
                "minimum_subnormal_numerator",
                "minimum_subnormal_power_of_two",
                "gamma_bound_method_id",
                "complex_add_real_add_count",
                "complex_multiply_real_multiply_count",
                "complex_multiply_real_add_count",
                "matrix_dot_operation_count_id",
                "scalar_expression_dag_id",
                "roundoff_bound_id",
                "gradual_underflow_additive_id",
                "root_center_error_propagation_id",
                "frobenius_sqrt_containment_id",
                "fma_policy",
                "reassociation_policy",
                "finite_value_policy",
                "outward_rounding_id",
                "root_interval_table",
            },
        )


if __name__ == "__main__":
    unittest.main()
