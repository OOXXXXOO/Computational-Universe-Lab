"""Tests for the M3′ strict-local real-space construction family."""

from importlib import import_module
from importlib.util import find_spec
import unittest

import numpy as np


local_family = import_module("rulespace_v2.m3_local_family")


class LocalFamilyInterfaceTests(unittest.TestCase):
    def test_module_exists(self) -> None:
        self.assertIsNotNone(find_spec("rulespace_v2.m3_local_family"))

    def test_public_construction_interface_exists(self) -> None:
        for name in (
            "LocalFamilyState",
            "LocalFamilyStep",
            "realspace_step_factory",
            "apply_walk_stiffness",
            "apply_r30_stiffness",
            "apply_counter_stiffness",
            "constraint_spatial",
            "constraint_spatial_adjoint",
            "floquet_retune_table",
        ):
            with self.subTest(name=name):
                self.assertTrue(hasattr(local_family, name), name)


class LocalFamilyStateTests(unittest.TestCase):
    def test_all_cells_use_the_same_state_schema(self) -> None:
        self.assertTrue(hasattr(local_family.LocalFamilyState, "zeros"))
        state = local_family.LocalFamilyState.zeros(L=7)
        expected = (
            (10, 7, 7, 7),
            (10, 7, 7, 7),
            (4, 7, 7, 7),
            (4, 7, 7, 7),
        )
        self.assertEqual(state.schema, expected)

        for q in range(5):
            with self.subTest(q=q):
                try:
                    stepped = local_family.realspace_step_factory(q, 0.02)(state)
                except NotImplementedError:
                    self.fail("realspace_step_factory is not implemented")
                self.assertEqual(stepped.schema, expected)
                for field in (
                    stepped.h,
                    stepped.p_h,
                    stepped.zeta,
                    stepped.p_zeta,
                ):
                    self.assertEqual(field.dtype, np.complex128)

    def test_q_is_an_explicit_four_layer_stiffness_prefix(self) -> None:
        rng = np.random.default_rng(11)
        h = rng.normal(size=(10, 7, 7, 7)) + 1j * rng.normal(
            size=(10, 7, 7, 7)
        )
        try:
            walk = local_family.apply_walk_stiffness(h)
            r30 = local_family.apply_r30_stiffness(h)
        except NotImplementedError:
            self.fail("stiffness operators are not implemented")

        for q in range(5):
            with self.subTest(q=q):
                accumulated = walk.copy()
                for layer in range(q):
                    accumulated += local_family.apply_counter_stiffness(h, layer)
                expected = walk + (q / 4.0) * (r30 - walk)
                np.testing.assert_allclose(
                    accumulated,
                    expected,
                    atol=2e-14,
                    rtol=2e-14,
                )


if __name__ == "__main__":
    unittest.main()
