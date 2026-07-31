from __future__ import annotations

import dataclasses
import unittest
from dataclasses import dataclass

import numpy as np

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import frozen_tensor_array
from rulespace_v3.metric import (
    MetricOriginManifest,
    build_stability_metric_witness,
    metric_origin_payload,
    stability_metric_witness_payload,
    verify_stability_metric_witness,
)
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.registry import build_closed_control_registry
from rulespace_v3.structure import build_structure_manifest
from tests.test_v3m0_dynamics import _quarter_turn_controls


class StabilityMetricWitnessTests(unittest.TestCase):
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
        cls.structure = build_structure_manifest(
            cls.factory,
            cls.authority,
        )

    def test_synthetic_metric_is_closed_normalized_identity(self):
        witness = build_stability_metric_witness(
            self.factory,
            self.authority,
            self.structure,
        )
        self.assertEqual(witness.metric_kind, "constant-state-v1")
        self.assertEqual(witness.metric_support_offsets, ((0,),))
        kernel = frozen_tensor_array(witness.metric_kernel)
        self.assertEqual(kernel.shape, (1, 2, 2))
        np.testing.assert_array_equal(kernel[0], np.eye(2))
        self.assertEqual(np.trace(kernel[0]), 2.0)
        self.assertEqual(witness.positive_eigenvalue_floor, 1.0)
        self.assertEqual(witness.condition_number_max, 1.0)
        self.assertEqual(witness.metric_origin.origin_kind, "synthetic-identity-v1")
        self.assertEqual(
            verify_stability_metric_witness(
                witness,
                self.factory,
                self.authority,
                self.structure,
            ),
            witness,
        )

    def test_resigned_origin_or_witness_cannot_change_metric(self):
        witness = build_stability_metric_witness(
            self.factory,
            self.authority,
            self.structure,
        )
        changed_origin = dataclasses.replace(
            witness.metric_origin,
            derivation_or_preregistration_sha="0" * 64,
            origin_sha="0" * 64,
        )
        changed_origin = dataclasses.replace(
            changed_origin,
            origin_sha=canonical_sha(metric_origin_payload(changed_origin)),
        )
        changed = dataclasses.replace(
            witness,
            metric_origin=changed_origin,
            witness_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            witness_sha=canonical_sha(
                stability_metric_witness_payload(changed)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_stability_metric_witness(
                changed,
                self.factory,
                self.authority,
                self.structure,
            )

    def test_nested_origin_subclass_with_unknown_field_is_rejected(self):
        @dataclass(frozen=True)
        class ExtraOrigin(MetricOriginManifest):
            extra_unknown_field: str

        witness = build_stability_metric_witness(
            self.factory,
            self.authority,
            self.structure,
        )
        origin = witness.metric_origin
        injected = ExtraOrigin(
            **{
                field.name: getattr(origin, field.name)
                for field in dataclasses.fields(origin)
            },
            extra_unknown_field="must-not-be-ignored",
        )
        with self.assertRaises((TypeError, ValueError)):
            dataclasses.replace(
                witness,
                metric_origin=injected,
                witness_sha="0" * 64,
            )


if __name__ == "__main__":
    unittest.main()
