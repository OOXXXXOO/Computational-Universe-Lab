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
import rulespace_v3.structure as structure_owner
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.dynamics import measure_transition
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    FrozenComplexTensor,
    freeze_complex_tensor,
    frozen_tensor_array,
)
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


_LEGACY_STRUCTURE_SHA = (
    "332c021718c6da18a85f741e99c912e77b2a7c844b4d1027019c0e497f63c722"
)
_LEGACY_REALITY_SHA = "1e7a98eed96f9f38fab8b203ef2569738ca8362d5e455c4ece6814babf65e031"
_LEGACY_STRUCTURE_ALL = [
    "FOURIER_REALITY_ID",
    "POSITIVE_ZERO_PATTERN_ID",
    "REALITY_SCHEMA_VERSION",
    "STRUCTURE_SCHEMA_VERSION",
    "RealityCertificate",
    "StructureManifest",
    "build_structure_manifest",
    "certify_reality",
    "reality_certificate_payload",
    "structure_manifest_payload",
    "verify_reality_certificate",
    "verify_structure_manifest",
]


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

    def test_owner_neutral_core_signatures_dag_and_exports_are_frozen(self):
        structure_core = getattr(
            structure_owner,
            "_build_bound_synthetic_structure_manifest",
        )
        structure_signature = inspect.signature(structure_core)
        self.assertEqual(
            tuple(structure_signature.parameters),
            (
                "structure_form",
                "target_spec_sha",
                "state_schema_id",
                "channel_order",
                "canonical_channel_pairs",
                "prestructure_authority_sha",
            ),
        )
        self.assertIs(
            structure_signature.parameters["structure_form"].kind,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
        self.assertTrue(
            all(
                parameter.kind is inspect.Parameter.KEYWORD_ONLY
                for name, parameter in structure_signature.parameters.items()
                if name != "structure_form"
            )
        )
        self.assertEqual(
            str(structure_signature.return_annotation),
            "StructureManifest",
        )

        reality_core = getattr(
            structure_owner,
            "_build_reality_certificate_from_raw",
        )
        reality_signature = inspect.signature(reality_core)
        self.assertEqual(
            tuple(reality_signature.parameters),
            ("factory", "transition", "structure"),
        )
        self.assertTrue(
            all(
                parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
                for parameter in reality_signature.parameters.values()
            )
        )
        self.assertEqual(
            str(reality_signature.return_annotation),
            "RealityCertificate",
        )
        self.assertEqual(structure_owner.__all__, _LEGACY_STRUCTURE_ALL)
        self.assertNotIn(structure_core.__name__, structure_owner.__all__)
        self.assertNotIn(reality_core.__name__, structure_owner.__all__)
        for core in (structure_core, reality_core):
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
            structure_owner.StructureManifest,
            structure_owner.RealityCertificate,
        ):
            post_init = record_type.__post_init__
            self.assertIsNot(post_init.__globals__, vars(structure_owner))
            self.assertEqual(tuple(inspect.signature(post_init).parameters), ("self",))

        tree = ast.parse(Path(structure_owner.__file__).read_text(encoding="utf-8"))
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

    def test_legacy_joins_precede_exactly_one_neutral_core_call(self):
        structure_core = getattr(
            structure_owner,
            "_build_bound_synthetic_structure_manifest",
        )
        make_structure = getattr(structure_owner, "_make_expected_structure")
        rejected_binder = mock.Mock(side_effect=ValueError("legacy join rejected"))
        rejected_core = mock.Mock(wraps=structure_core)
        rejected_builder = make_structure(
            rejected_binder,
            rejected_core,
            tensor_freezer=structure_owner.freeze_complex_tensor,
            np_module=np,
        )
        with self.assertRaisesRegex(ValueError, "legacy join rejected"):
            rejected_builder(self.factory, self.authority)
        rejected_binder.assert_called_once_with(self.factory, self.authority)
        rejected_core.assert_not_called()

        order: list[str] = []
        production_binder = getattr(structure_owner, "_bind_structure_inputs")

        def traced_binder(*args, **kwargs):
            order.append("join")
            return production_binder(*args, **kwargs)

        def traced_core(*args, **kwargs):
            order.append("core")
            return structure_core(*args, **kwargs)

        binder = mock.Mock(side_effect=traced_binder)
        core = mock.Mock(side_effect=traced_core)
        builder = make_structure(
            binder,
            core,
            tensor_freezer=structure_owner.freeze_complex_tensor,
            np_module=np,
        )
        structure = builder(self.factory, self.authority)
        binder.assert_called_once_with(self.factory, self.authority)
        core.assert_called_once()
        self.assertEqual(order, ["join", "core"])
        self.assertEqual(structure.structure_manifest_sha, _LEGACY_STRUCTURE_SHA)

        reality_core = getattr(
            structure_owner,
            "_build_reality_certificate_from_raw",
        )
        make_reality = getattr(structure_owner, "_make_expected_reality")
        rejected_binder = mock.Mock(side_effect=ValueError("legacy join rejected"))
        rejected_core = mock.Mock(wraps=reality_core)
        rejected_builder = make_reality(rejected_binder, rejected_core)
        with self.assertRaisesRegex(ValueError, "legacy join rejected"):
            rejected_builder(self.factory, self.transition, structure)
        rejected_binder.assert_called_once_with(
            self.factory,
            self.transition,
            structure,
        )
        rejected_core.assert_not_called()

        order.clear()
        production_binder = getattr(structure_owner, "_bind_reality_inputs")

        def traced_reality_binder(*args, **kwargs):
            order.append("join")
            return production_binder(*args, **kwargs)

        def traced_reality_core(*args, **kwargs):
            order.append("core")
            return reality_core(*args, **kwargs)

        binder = mock.Mock(side_effect=traced_reality_binder)
        core = mock.Mock(side_effect=traced_reality_core)
        builder = make_reality(binder, core)
        reality = builder(self.factory, self.transition, structure)
        binder.assert_called_once_with(self.factory, self.transition, structure)
        core.assert_called_once_with(
            self.factory, self.transition.transition, structure
        )
        self.assertEqual(order, ["join", "core"])
        self.assertEqual(reality.reality_certificate_sha, _LEGACY_REALITY_SHA)

    def test_neutral_core_candidates_exactly_equal_legacy_goldens(self):
        legacy_structure = build_structure_manifest(self.factory, self.authority)
        structure_core = getattr(
            structure_owner,
            "_build_bound_synthetic_structure_manifest",
        )
        candidate_structure = structure_core(
            legacy_structure.structure_form,
            target_spec_sha=legacy_structure.target_spec_sha,
            state_schema_id=legacy_structure.state_schema_id,
            channel_order=legacy_structure.channel_order,
            canonical_channel_pairs=legacy_structure.canonical_channel_pairs,
            prestructure_authority_sha=(legacy_structure.prestructure_authority_sha),
        )
        self.assertEqual(candidate_structure, legacy_structure)
        self.assertEqual(
            canonical_sha(structure_manifest_payload(candidate_structure)),
            _LEGACY_STRUCTURE_SHA,
        )

        legacy_reality = certify_reality(
            self.factory,
            self.transition,
            legacy_structure,
        )
        reality_core = getattr(
            structure_owner,
            "_build_reality_certificate_from_raw",
        )
        candidate_reality = reality_core(
            self.factory,
            self.transition.transition,
            candidate_structure,
        )
        self.assertEqual(candidate_reality, legacy_reality)
        self.assertEqual(
            canonical_sha(reality_certificate_payload(candidate_reality)),
            _LEGACY_REALITY_SHA,
        )

    def test_reality_core_ignores_factory_view_global_redirect(self):
        structure = build_structure_manifest(self.factory, self.authority)
        core = getattr(
            structure_owner,
            "_build_reality_certificate_from_raw",
        )
        baseline = core(
            self.factory,
            self.transition.transition,
            structure,
        )
        original_view_type = factory_owner._VerifiedFactoryView

        def redirected_view(*, factory, trace, target, role):
            altered_factory = dataclasses.replace(factory)
            object.__setattr__(
                altered_factory,
                "primitives",
                (*factory.primitives, factory.primitives[0]),
            )
            return original_view_type(
                factory=altered_factory,
                trace=trace,
                target=target,
                role=role,
            )

        with mock.patch.object(
            factory_owner,
            "_VerifiedFactoryView",
            side_effect=redirected_view,
        ) as redirected:
            replayed = core(
                self.factory,
                self.transition.transition,
                structure,
            )

        redirected.assert_not_called()
        self.assertEqual(replayed, baseline)
        self.assertEqual(replayed.factory_coefficient_count, 3)
        self.assertEqual(replayed.reality_certificate_sha, _LEGACY_REALITY_SHA)

    def test_structure_core_rejects_negative_zero_in_exact_block_j(self):
        legacy = build_structure_manifest(self.factory, self.authority)
        values = frozen_tensor_array(legacy.structure_form)
        values[0, 0] = complex(-0.0, 0.0)
        signed_zero_form = freeze_complex_tensor(values)
        core = getattr(
            structure_owner,
            "_build_bound_synthetic_structure_manifest",
        )
        with self.assertRaisesRegex(ValueError, "canonical block-J"):
            core(
                signed_zero_form,
                target_spec_sha=legacy.target_spec_sha,
                state_schema_id=legacy.state_schema_id,
                channel_order=legacy.channel_order,
                canonical_channel_pairs=legacy.canonical_channel_pairs,
                prestructure_authority_sha=legacy.prestructure_authority_sha,
            )

    def test_frozen_legacy_paths_resist_owner_global_redirects(self):
        baseline_structure = build_structure_manifest(self.factory, self.authority)
        baseline_reality = certify_reality(
            self.factory,
            self.transition,
            baseline_structure,
        )

        def redirected(*_args, **_kwargs):
            raise AssertionError("post-freeze structure global was consulted")

        names = (
            "_reverify_verified_factory",
            "_reverify_verified_prestructure_authority",
            "_reverify_verified_transition",
            "_build_bound_synthetic_structure_manifest",
            "_build_reality_certificate_from_raw",
            "_bind_structure_inputs",
            "_bind_reality_inputs",
            "_expected_structure",
            "_expected_reality",
            "freeze_complex_tensor",
            "frozen_tensor_array",
            "canonical_sha",
        )
        with contextlib.ExitStack() as stack:
            for name in names:
                stack.enter_context(
                    mock.patch.object(
                        structure_owner,
                        name,
                        side_effect=redirected,
                        create=True,
                    )
                )
            self.assertEqual(
                build_structure_manifest(self.factory, self.authority),
                baseline_structure,
            )
            self.assertEqual(
                verify_structure_manifest(
                    baseline_structure,
                    self.factory,
                    self.authority,
                ),
                baseline_structure,
            )
            self.assertEqual(
                certify_reality(
                    self.factory,
                    self.transition,
                    baseline_structure,
                ),
                baseline_reality,
            )
            self.assertEqual(
                verify_reality_certificate(
                    baseline_reality,
                    self.factory,
                    self.transition,
                    baseline_structure,
                ),
                baseline_reality,
            )

    def test_neutral_cores_helpers_and_records_resist_builtin_shadow(self):
        baseline_structure = build_structure_manifest(self.factory, self.authority)
        baseline_reality = certify_reality(
            self.factory,
            self.transition,
            baseline_structure,
        )
        structure_core = getattr(
            structure_owner,
            "_build_bound_synthetic_structure_manifest",
        )
        reality_core = getattr(
            structure_owner,
            "_build_reality_certificate_from_raw",
        )

        def redirected(*_args, **_kwargs):
            raise AssertionError("owner builtin/helper shadow was consulted")

        callable_names = (
            "type",
            "str",
            "int",
            "float",
            "TypeError",
            "ValueError",
            "len",
            "tuple",
            "set",
            "all",
            "range",
            "enumerate",
            "isinstance",
            "list",
            "getattr",
            "_text",
            "_sha",
            "_nonnegative_int",
            "_tensor_record",
            "structure_manifest_payload",
            "reality_certificate_payload",
            "_validate_synthetic_structure",
            "_is_positive_zero",
            "canonical_sha",
            "freeze_complex_tensor",
            "frozen_tensor_array",
        )
        with contextlib.ExitStack() as stack:
            for name in callable_names:
                stack.enter_context(
                    mock.patch.object(
                        structure_owner,
                        name,
                        redirected,
                        create=True,
                    )
                )
            for name in ("np", "math", "struct"):
                stack.enter_context(mock.patch.object(structure_owner, name, object()))
            stack.enter_context(
                mock.patch.object(
                    structure_owner,
                    "POSITIVE_ZERO_PATTERN_ID",
                    "redirected-positive-zero-pattern",
                )
            )
            stack.enter_context(
                mock.patch.object(
                    structure_owner,
                    "FOURIER_REALITY_ID",
                    "redirected-fourier-reality",
                )
            )

            baseline_structure.__post_init__()
            baseline_reality.__post_init__()
            rebuilt_structure = structure_core(
                baseline_structure.structure_form,
                target_spec_sha=baseline_structure.target_spec_sha,
                state_schema_id=baseline_structure.state_schema_id,
                channel_order=baseline_structure.channel_order,
                canonical_channel_pairs=(baseline_structure.canonical_channel_pairs),
                prestructure_authority_sha=(
                    baseline_structure.prestructure_authority_sha
                ),
            )
            rebuilt_reality = reality_core(
                self.factory,
                self.transition.transition,
                rebuilt_structure,
            )

        self.assertEqual(rebuilt_structure, baseline_structure)
        self.assertEqual(rebuilt_reality, baseline_reality)

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
