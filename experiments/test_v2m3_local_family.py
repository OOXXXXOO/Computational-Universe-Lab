"""Tests for the M3′ strict-local real-space construction family."""

from importlib import import_module
from importlib.util import find_spec
import unittest
from unittest.mock import patch

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

    def test_all_thirty_steps_run_with_numpy_fft_disabled(self) -> None:
        state = local_family.LocalFamilyState.zeros(L=7)

        def forbidden_fft(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("FFT entered the production time-step path")

        fft_names = ("fft", "ifft", "fftn", "ifftn", "rfft", "irfft")
        patchers = [
            patch.object(np.fft, name, forbidden_fft)
            for name in fft_names
        ]
        for patcher in patchers:
            patcher.start()
        try:
            for q in local_family.Q_LEVELS:
                for kappa_c in local_family.KAPPA_C_LEVELS:
                    with self.subTest(q=q, kappa_c=kappa_c):
                        local_family.realspace_step_factory(q, kappa_c)(state)
        finally:
            for patcher in reversed(patchers):
                patcher.stop()


class LocalOperatorCertificateTests(unittest.TestCase):
    def test_constraint_operator_and_adjoint_match(self) -> None:
        rng = np.random.default_rng(19)
        h = rng.normal(size=(10, 7, 7, 7)) + 1j * rng.normal(
            size=(10, 7, 7, 7)
        )
        zeta = rng.normal(size=(4, 7, 7, 7)) + 1j * rng.normal(
            size=(4, 7, 7, 7)
        )
        lhs = np.vdot(local_family.constraint_spatial(h), zeta)
        try:
            adjoint = local_family.constraint_spatial_adjoint(zeta)
        except NotImplementedError:
            self.fail("constraint_spatial_adjoint is not implemented")
        rhs = np.vdot(h, adjoint)
        residual = abs(lhs - rhs) / max(abs(lhs), 1e-300)
        self.assertLess(residual, 1e-13)

    def test_floquet_retune_uses_the_actual_reference_shell(self) -> None:
        try:
            table = local_family.floquet_retune_table()
        except NotImplementedError:
            self.fail("floquet_retune_table is not implemented")

        self.assertEqual(set(table), {0, 1, 2, 3, 4})
        for q, row in table.items():
            with self.subTest(q=q):
                self.assertEqual(row["L_ref"], 32)
                self.assertEqual(row["k_units_ref"], [1, 0, 0])
                self.assertLess(row["frequency_residual"], 1e-12)
                self.assertGreater(row["dt"], 0.99)
                self.assertLessEqual(row["dt"], 1.000000000001)

    def test_macro_step_support_is_finite_and_volume_independent(self) -> None:
        self.assertTrue(hasattr(local_family, "measure_support_radii"))
        support = local_family.measure_support_radii(L_values=(17, 21))
        self.assertEqual(set(support["per_L"]), {"17", "21"})
        self.assertEqual(len(set(support["per_L"].values())), 1)
        self.assertTrue(support["independent_of_L"])
        self.assertLessEqual(support["max_radius"], 6)

    def test_adjoint_certificate_records_the_fp64_residual(self) -> None:
        self.assertTrue(hasattr(local_family, "adjoint_certificate"))
        certificate = local_family.adjoint_certificate(L=7, seed=19)
        self.assertLess(certificate["constraint_adjoint_residual"], 1e-13)
        self.assertLess(certificate["walk_stiffness_adjoint_residual"], 1e-13)
        self.assertLess(certificate["r30_stiffness_adjoint_residual"], 1e-13)
        self.assertTrue(certificate["pass"])


class LocalFamilySymplecticTests(unittest.TestCase):
    def test_constraint_coupling_is_a_positive_square_completed_penalty(self) -> None:
        for q in local_family.Q_LEVELS:
            dt = local_family.floquet_retune_table()[q]["dt"]
            for kappa_c in local_family.KAPPA_C_LEVELS:
                for k in local_family.K_CERT:
                    with self.subTest(q=q, kappa_c=kappa_c, k=k):
                        potential = local_family.symbol_of_potential(
                            q, kappa_c, k
                        )
                        eigenvalues = np.linalg.eigvalsh(potential)
                        self.assertGreaterEqual(float(eigenvalues.min()), -2e-12)
                        self.assertLess(
                            dt * dt * float(eigenvalues.max()),
                            4.0,
                        )

    def test_all_thirty_cells_pass_the_fp64_symplectic_gate(self) -> None:
        self.assertTrue(hasattr(local_family, "certify_local_family"))
        certificate = local_family.certify_local_family()
        self.assertEqual(certificate["cells_checked"], 30)
        self.assertEqual(
            certificate["zero_mode_policy"],
            "analytic Jordan drift; spectral modulus excluded at k=0",
        )
        self.assertLess(certificate["max_verlet_cfl_number"], 4.0)
        self.assertLessEqual(
            certificate["max_symplectic_defect_fp64"],
            1e-12,
        )
        self.assertLessEqual(
            certificate["max_potential_hermitian_defect"],
            1e-12,
        )
        self.assertLessEqual(
            certificate["max_abs_eig_modulus_minus_1"],
            1e-12,
        )
        self.assertTrue(certificate["stable_all"])
        self.assertTrue(certificate["pass"])


if __name__ == "__main__":
    unittest.main()
