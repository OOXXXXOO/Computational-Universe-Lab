from __future__ import annotations

import ast
import contextlib
import dataclasses
import dis
import inspect
import unittest
from pathlib import Path
from dataclasses import dataclass
from unittest import mock

import numpy as np

import rulespace_v3.factory as factory_owner
import rulespace_v3.metric as metric_owner
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array
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


_LEGACY_METRIC_SHA = "d3cb39ca74e1971d8f155e1d31bb623723970b1f437dfdf0d93ec7d395b9c054"
_LEGACY_METRIC_ALL = [
    "METRIC_NORMALIZATION_ID",
    "METRIC_ORIGIN_SCHEMA_VERSION",
    "METRIC_SUPPORT_SCHEMA_VERSION",
    "STABILITY_METRIC_SCHEMA_VERSION",
    "MetricOriginManifest",
    "StabilityMetricWitness",
    "build_stability_metric_witness",
    "metric_origin_payload",
    "metric_support_payload",
    "stability_metric_witness_payload",
    "verify_stability_metric_witness",
]


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

    def test_owner_neutral_core_signature_dag_and_exports_are_frozen(self):
        core = getattr(
            metric_owner,
            "_build_bound_synthetic_identity_metric",
        )
        signature = inspect.signature(core)
        self.assertEqual(
            tuple(signature.parameters),
            (
                "factory",
                "structure",
                "state_metric",
                "parent_freeze_sha",
                "prestructure_authority_sha",
                "derivation_or_preregistration_sha",
                "metric_support_offsets",
            ),
        )
        self.assertTrue(
            all(
                signature.parameters[name].kind
                is inspect.Parameter.POSITIONAL_OR_KEYWORD
                for name in ("factory", "structure", "state_metric")
            )
        )
        self.assertTrue(
            all(
                signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
                for name in (
                    "parent_freeze_sha",
                    "prestructure_authority_sha",
                    "derivation_or_preregistration_sha",
                    "metric_support_offsets",
                )
            )
        )
        self.assertEqual(
            str(signature.return_annotation),
            "StabilityMetricWitness",
        )
        self.assertEqual(metric_owner.__all__, _LEGACY_METRIC_ALL)
        self.assertNotIn(core.__name__, metric_owner.__all__)
        self.assertFalse(
            [
                instruction.argval
                for instruction in dis.get_instructions(core)
                if instruction.opname == "LOAD_GLOBAL"
            ]
        )
        self.assertFalse(
            any(
                type(cell.cell_contents) in (dict, list)
                for cell in (core.__closure__ or ())
            )
        )
        for record_type in (
            metric_owner.MetricOriginManifest,
            metric_owner.StabilityMetricWitness,
        ):
            post_init = record_type.__post_init__
            self.assertIsNot(post_init.__globals__, vars(metric_owner))
            self.assertEqual(tuple(inspect.signature(post_init).parameters), ("self",))

        tree = ast.parse(Path(metric_owner.__file__).read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 1 and node.module:
                    imports.add(f"rulespace_v3.{node.module}")
                elif node.module:
                    imports.add(node.module)
        self.assertFalse(
            {
                "rulespace_v3.parent_v3_application_prestructure",
                "rulespace_v3.transition_authority_v3",
                "rulespace_v3.certificate_v3",
            }.intersection(imports)
        )

    def test_legacy_metric_join_precedes_exactly_one_neutral_core_call(self):
        core = getattr(
            metric_owner,
            "_build_bound_synthetic_identity_metric",
        )
        make_expected = getattr(metric_owner, "_make_expected_metric")
        rejected_binder = mock.Mock(side_effect=ValueError("legacy join rejected"))
        rejected_core = mock.Mock(wraps=core)
        rejected_builder = make_expected(
            rejected_binder,
            rejected_core,
            tensor_freezer=metric_owner.freeze_complex_tensor,
            np_module=np,
        )
        with self.assertRaisesRegex(ValueError, "legacy join rejected"):
            rejected_builder(self.factory, self.authority, self.structure)
        rejected_binder.assert_called_once_with(
            self.factory,
            self.authority,
            self.structure,
        )
        rejected_core.assert_not_called()

        order: list[str] = []
        production_binder = getattr(metric_owner, "_bind_metric_inputs")

        def traced_binder(*args, **kwargs):
            order.append("join")
            return production_binder(*args, **kwargs)

        def traced_core(*args, **kwargs):
            order.append("core")
            return core(*args, **kwargs)

        binder = mock.Mock(side_effect=traced_binder)
        traced = mock.Mock(side_effect=traced_core)
        builder = make_expected(
            binder,
            traced,
            tensor_freezer=metric_owner.freeze_complex_tensor,
            np_module=np,
        )
        witness = builder(self.factory, self.authority, self.structure)
        binder.assert_called_once_with(
            self.factory,
            self.authority,
            self.structure,
        )
        traced.assert_called_once()
        self.assertEqual(order, ["join", "core"])
        self.assertEqual(witness.witness_sha, _LEGACY_METRIC_SHA)

    def test_neutral_metric_candidate_exactly_equals_legacy_golden(self):
        legacy = build_stability_metric_witness(
            self.factory,
            self.authority,
            self.structure,
        )
        state_metric = freeze_complex_tensor(
            frozen_tensor_array(legacy.metric_kernel)[0]
        )
        core = getattr(
            metric_owner,
            "_build_bound_synthetic_identity_metric",
        )
        candidate = core(
            self.factory,
            self.structure,
            state_metric,
            parent_freeze_sha=legacy.metric_origin.parent_freeze_sha,
            prestructure_authority_sha=(
                legacy.metric_origin.prestructure_authority_sha
            ),
            derivation_or_preregistration_sha=(
                legacy.metric_origin.derivation_or_preregistration_sha
            ),
            metric_support_offsets=legacy.metric_support_offsets,
        )
        self.assertEqual(candidate, legacy)
        self.assertEqual(
            canonical_sha(stability_metric_witness_payload(candidate)),
            _LEGACY_METRIC_SHA,
        )

    def test_metric_core_ignores_factory_tensor_verifier_global_redirect(self):
        baseline = build_stability_metric_witness(
            self.factory,
            self.authority,
            self.structure,
        )
        state_metric = freeze_complex_tensor(
            frozen_tensor_array(baseline.metric_kernel)[0]
        )
        core = getattr(
            metric_owner,
            "_build_bound_synthetic_identity_metric",
        )

        def redirected_verifier(tensor):
            values_wire = list(tensor.values_wire)
            values_wire[1] = (-0.0, values_wire[1][1])
            return dataclasses.replace(
                tensor,
                values_wire=tuple(values_wire),
            )

        with mock.patch.object(
            factory_owner,
            "verify_frozen_tensor",
            side_effect=redirected_verifier,
        ) as redirected:
            replayed = core(
                self.factory,
                self.structure,
                state_metric,
                parent_freeze_sha=baseline.metric_origin.parent_freeze_sha,
                prestructure_authority_sha=(
                    baseline.metric_origin.prestructure_authority_sha
                ),
                derivation_or_preregistration_sha=(
                    baseline.metric_origin.derivation_or_preregistration_sha
                ),
                metric_support_offsets=baseline.metric_support_offsets,
            )

        redirected.assert_not_called()
        self.assertEqual(replayed, baseline)
        self.assertEqual(replayed.witness_sha, _LEGACY_METRIC_SHA)

    def test_metric_core_rejects_negative_zero_in_bit_exact_identity(self):
        legacy = build_stability_metric_witness(
            self.factory,
            self.authority,
            self.structure,
        )
        values = frozen_tensor_array(legacy.metric_kernel)[0]
        values[0, 1] = complex(-0.0, 0.0)
        signed_zero_metric = freeze_complex_tensor(values)
        core = getattr(
            metric_owner,
            "_build_bound_synthetic_identity_metric",
        )
        with self.assertRaisesRegex(ValueError, "bit-exact identity"):
            core(
                self.factory,
                self.structure,
                signed_zero_metric,
                parent_freeze_sha=legacy.metric_origin.parent_freeze_sha,
                prestructure_authority_sha=(
                    legacy.metric_origin.prestructure_authority_sha
                ),
                derivation_or_preregistration_sha=(
                    legacy.metric_origin.derivation_or_preregistration_sha
                ),
                metric_support_offsets=legacy.metric_support_offsets,
            )

    def test_frozen_metric_paths_resist_owner_global_redirects(self):
        baseline = build_stability_metric_witness(
            self.factory,
            self.authority,
            self.structure,
        )

        def redirected(*_args, **_kwargs):
            raise AssertionError("post-freeze metric global was consulted")

        names = (
            "_reverify_verified_factory",
            "_reverify_verified_prestructure_authority",
            "verify_structure_manifest",
            "_build_bound_synthetic_identity_metric",
            "_bind_metric_inputs",
            "_expected_metric",
            "freeze_complex_tensor",
            "frozen_tensor_array",
            "canonical_sha",
        )
        with contextlib.ExitStack() as stack:
            for name in names:
                stack.enter_context(
                    mock.patch.object(
                        metric_owner,
                        name,
                        side_effect=redirected,
                        create=True,
                    )
                )
            self.assertEqual(
                build_stability_metric_witness(
                    self.factory,
                    self.authority,
                    self.structure,
                ),
                baseline,
            )
            self.assertEqual(
                verify_stability_metric_witness(
                    baseline,
                    self.factory,
                    self.authority,
                    self.structure,
                ),
                baseline,
            )

    def test_neutral_core_helpers_and_records_resist_builtin_shadow(self):
        baseline = build_stability_metric_witness(
            self.factory,
            self.authority,
            self.structure,
        )
        state_metric = freeze_complex_tensor(
            frozen_tensor_array(baseline.metric_kernel)[0]
        )
        core = getattr(
            metric_owner,
            "_build_bound_synthetic_identity_metric",
        )

        def redirected(*_args, **_kwargs):
            raise AssertionError("owner builtin/helper shadow was consulted")

        callable_names = (
            "type",
            "str",
            "int",
            "float",
            "complex",
            "TypeError",
            "ValueError",
            "len",
            "tuple",
            "set",
            "sorted",
            "all",
            "isinstance",
            "list",
            "getattr",
            "_text",
            "_sha",
            "_finite_float",
            "_tensor_record",
            "metric_support_payload",
            "metric_origin_payload",
            "_origin_record",
            "stability_metric_witness_payload",
            "structure_manifest_payload",
            "canonical_sha",
            "freeze_complex_tensor",
            "frozen_tensor_array",
        )
        with contextlib.ExitStack() as stack:
            for name in callable_names:
                stack.enter_context(
                    mock.patch.object(
                        metric_owner,
                        name,
                        redirected,
                        create=True,
                    )
                )
            for name in ("np", "math"):
                stack.enter_context(mock.patch.object(metric_owner, name, object()))
            stack.enter_context(
                mock.patch.object(
                    metric_owner,
                    "METRIC_NORMALIZATION_ID",
                    "redirected-normalization",
                )
            )

            baseline.metric_origin.__post_init__()
            baseline.__post_init__()
            rebuilt = core(
                self.factory,
                self.structure,
                state_metric,
                parent_freeze_sha=baseline.metric_origin.parent_freeze_sha,
                prestructure_authority_sha=(
                    baseline.metric_origin.prestructure_authority_sha
                ),
                derivation_or_preregistration_sha=(
                    baseline.metric_origin.derivation_or_preregistration_sha
                ),
                metric_support_offsets=baseline.metric_support_offsets,
            )

        self.assertEqual(rebuilt, baseline)

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
            witness_sha=canonical_sha(stability_metric_witness_payload(changed)),
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
