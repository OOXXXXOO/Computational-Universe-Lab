from __future__ import annotations

import dataclasses
import unittest
from dataclasses import dataclass

import numpy as np

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.dynamics import measure_transition
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import FrozenComplexTensor, frozen_tensor_array
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.registry import build_closed_control_registry
from rulespace_v3.structure import (
    build_structure_manifest,
    certify_reality,
    reality_certificate_payload,
    structure_manifest_payload,
    verify_reality_certificate,
    verify_structure_manifest,
)
from tests.test_v3m0_dynamics import _quarter_turn_controls


class StructureAndRealityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        cls.construction = matched_ablation(cls.controls[0].factory)
        assert cls.construction.pair is not None
        cls.authority = issue_synthetic_prestructure_authority(
            cls.parent,
            cls.registry,
            "full",
            cls.construction,
            "actual",
        )
        cls.factory = cls.construction.pair.actual
        cls.transition = measure_transition(cls.factory, cls.authority)

    def test_synthetic_structure_is_mechanically_symplectic(self):
        structure = build_structure_manifest(
            self.factory,
            self.authority,
        )
        self.assertEqual(structure.evidence_lane, "synthetic-classical")
        self.assertEqual(structure.structure_kind, "symplectic")
        self.assertEqual(
            structure.canonical_channel_pairs,
            (("x.000", "y.000"),),
        )
        omega = frozen_tensor_array(structure.structure_form)
        np.testing.assert_array_equal(omega.T, -omega)
        self.assertNotEqual(np.linalg.det(omega), 0.0)
        self.assertEqual(
            verify_structure_manifest(
                structure,
                self.factory,
                self.authority,
            ),
            structure,
        )

    def test_reality_certificate_counts_positive_zero_imaginary_bits(self):
        structure = build_structure_manifest(
            self.factory,
            self.authority,
        )
        reality = certify_reality(
            self.factory,
            self.transition,
            structure,
        )
        self.assertEqual(reality.factory_coefficient_count, 3)
        self.assertEqual(reality.transition_entry_count, 2 * 2 * 5)
        self.assertEqual(
            reality.imaginary_bit_pattern_id,
            "all-positive-zero-f64-v1",
        )
        self.assertEqual(
            verify_reality_certificate(
                reality,
                self.factory,
                self.transition,
                structure,
            ),
            reality,
        )

    def test_resigned_structure_and_reality_tamper_are_rejected(self):
        structure = build_structure_manifest(
            self.factory,
            self.authority,
        )
        changed_structure = dataclasses.replace(
            structure,
            structure_kind="unitary",
            structure_manifest_sha="0" * 64,
        )
        changed_structure = dataclasses.replace(
            changed_structure,
            structure_manifest_sha=canonical_sha(
                structure_manifest_payload(changed_structure)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_structure_manifest(
                changed_structure,
                self.factory,
                self.authority,
            )

        reality = certify_reality(
            self.factory,
            self.transition,
            structure,
        )
        changed_reality = dataclasses.replace(
            reality,
            factory_coefficient_count=4,
            reality_certificate_sha="0" * 64,
        )
        changed_reality = dataclasses.replace(
            changed_reality,
            reality_certificate_sha=canonical_sha(
                reality_certificate_payload(changed_reality)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_reality_certificate(
                changed_reality,
                self.factory,
                self.transition,
                structure,
            )

    def test_nested_tensor_subclass_with_unknown_field_is_rejected(self):
        @dataclass(frozen=True)
        class ExtraTensor(FrozenComplexTensor):
            extra_unknown_field: str

        structure = build_structure_manifest(
            self.factory,
            self.authority,
        )
        tensor = structure.structure_form
        injected = ExtraTensor(
            tensor_schema_version=tensor.tensor_schema_version,
            shape=tensor.shape,
            values_wire=tensor.values_wire,
            tensor_sha=tensor.tensor_sha,
            extra_unknown_field="must-not-be-ignored",
        )
        with self.assertRaises((TypeError, ValueError)):
            dataclasses.replace(
                structure,
                structure_form=injected,
                structure_manifest_sha="0" * 64,
            )


if __name__ == "__main__":
    unittest.main()
