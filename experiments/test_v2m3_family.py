"""Tests for the M3′ Round 0 family-admission instrument."""

from importlib.util import find_spec
from importlib import import_module
import unittest

m3_family = import_module("rulespace_v2.m3_family")

class M3FamilyModuleTests(unittest.TestCase):
    def test_m3_family_module_exists(self) -> None:
        self.assertIsNotNone(find_spec("rulespace_v2.m3_family"))

    def test_public_family_admission_interface_exists(self) -> None:
        module = import_module("rulespace_v2.m3_family")
        for name in (
            "PilotCell",
            "build_pilot_manifest",
            "legacy_rc3ii_descriptor",
            "audit_family_descriptor",
        ):
            with self.subTest(name=name):
                self.assertTrue(hasattr(module, name), name)


class PilotManifestTests(unittest.TestCase):
    def test_manifest_is_the_frozen_five_by_six_core_grid(self) -> None:
        self.assertTrue(hasattr(m3_family, "Q_LEVELS"))
        self.assertTrue(hasattr(m3_family, "KAPPA_C_LEVELS"))
        try:
            cells = m3_family.build_pilot_manifest()
        except NotImplementedError:
            self.fail("build_pilot_manifest is not implemented")

        self.assertEqual(len(cells), 30)
        self.assertEqual({cell.q for cell in cells}, set(m3_family.Q_LEVELS))
        self.assertEqual({cell.kappa_c for cell in cells}, set(m3_family.KAPPA_C_LEVELS))
        self.assertEqual(len({cell.cell_id for cell in cells}), 30)
        self.assertTrue(
            all(
                cell.eta == 0.0
                and cell.matter_epsilon_fixed == 1.0
                and cell.retune_mode == "actual-floquet-shell"
                for cell in cells
            )
        )

    def test_manifest_never_injects_measured_coordinates(self) -> None:
        try:
            cells = m3_family.build_pilot_manifest()
        except NotImplementedError:
            self.fail("build_pilot_manifest is not implemented")
        for cell in cells:
            with self.subTest(cell_id=cell.cell_id):
                payload = cell.as_dict()
                self.assertNotIn("epsilon_geo", payload)
                self.assertNotIn("sigma", payload)


class FamilyAdmissionTests(unittest.TestCase):
    @staticmethod
    def valid_descriptor() -> dict[str, object]:
        return {
            "construction_kind": "strict_local_realspace",
            "realspace_step_factory": "rulespace_v2.m3_runtime:make_step",
            "support_radius": 2,
            "declared_composition_radius": 2,
            "support_radius_independent_of_L": True,
            "unitarity_error_fp64": 5e-14,
            "same_state_space_all_q": True,
            "k_dependent_projection": False,
            "explicit_local_shears": ["base", "s1", "s2", "s3"],
            "q_layer_counts": [0, 1, 2, 3, 4],
            "coordinates_are_measured": True,
            "floquet_retune_mode": "actual-floquet-shell",
        }

    def test_current_rc3ii_descriptor_is_rejected(self) -> None:
        try:
            result = m3_family.audit_family_descriptor(
                m3_family.legacy_rc3ii_descriptor()
            )
        except NotImplementedError:
            self.fail("family admission is not implemented")

        self.assertFalse(result["pass"])
        self.assertIn("spectral_bookkeeping_only", result["failures"])
        self.assertIn("missing_realspace_step_factory", result["failures"])
        self.assertIn("k_dependent_projection", result["failures"])

    def test_strict_local_realspace_descriptor_is_admitted(self) -> None:
        try:
            result = m3_family.audit_family_descriptor(self.valid_descriptor())
        except NotImplementedError:
            self.fail("audit_family_descriptor is not implemented")

        self.assertTrue(result["pass"])
        self.assertEqual(result["failures"], [])
        self.assertTrue(all(result["checks"].values()))

    def test_descriptor_cannot_inject_measured_coordinates(self) -> None:
        for measured_field, value in (
            ("epsilon_geo", 0.5),
            ("sigma", {"alpha": 1.0, "A": 0.0}),
        ):
            descriptor = self.valid_descriptor() | {measured_field: value}
            with self.subTest(measured_field=measured_field):
                try:
                    result = m3_family.audit_family_descriptor(descriptor)
                except NotImplementedError:
                    self.fail("audit_family_descriptor is not implemented")
                self.assertFalse(result["pass"])
                self.assertIn("measured_coordinate_injection", result["failures"])


if __name__ == "__main__":
    unittest.main()
