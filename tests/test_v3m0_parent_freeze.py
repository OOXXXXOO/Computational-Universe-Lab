from __future__ import annotations

import dataclasses
import gc
import hashlib
import inspect
import unittest
import weakref
from pathlib import Path

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.parent_freeze import (
    APPLICATION_CONTROL_CASE_IDS,
    IMPLEMENTATION_PLAN_SOURCE_PATH,
    PARENT_FREEZE_SCHEMA_VERSION,
    PROGRAM_ID,
    TASK9_COMMIT_SHA,
    TASKBOOK_SOURCE_PATH,
    ApplicationOperationKind,
    ParentFreezeManifest,
    SyntheticApplicationOperation,
    SyntheticApplicationProtocolConstants,
    TaggedScalarWire,
    V3M0SyntheticControlApplicationSpec,
    VerifiedParentFreeze,
    _reverify_verified_parent_freeze,
    issue_v3m0_parent_freeze,
    parent_freeze_manifest_payload,
    synthetic_application_basis_protocol_payload,
    synthetic_application_grid_protocol_payload,
    synthetic_application_operation_payload,
    synthetic_application_protocol_constants_payload,
    synthetic_application_readout_protocol_payload,
    synthetic_control_application_spec_payload,
    verify_parent_freeze,
    verify_synthetic_control_application_spec,
)


ROOT = Path(__file__).resolve().parents[1]


def _resign_operation(
    operation: SyntheticApplicationOperation,
) -> SyntheticApplicationOperation:
    return dataclasses.replace(
        operation,
        operation_sha=canonical_sha(
            synthetic_application_operation_payload(operation)
        ),
    )


def _resign_spec(
    spec: V3M0SyntheticControlApplicationSpec,
) -> V3M0SyntheticControlApplicationSpec:
    return dataclasses.replace(
        spec,
        application_spec_sha=canonical_sha(
            synthetic_control_application_spec_payload(spec)
        ),
    )


def _resign_constants(
    constants: SyntheticApplicationProtocolConstants,
) -> SyntheticApplicationProtocolConstants:
    return dataclasses.replace(
        constants,
        constants_sha=canonical_sha(
            synthetic_application_protocol_constants_payload(constants)
        ),
    )


def _resign_manifest(manifest: ParentFreezeManifest) -> ParentFreezeManifest:
    return dataclasses.replace(
        manifest,
        parent_freeze_sha=canonical_sha(parent_freeze_manifest_payload(manifest)),
    )


class TaggedScalarWireTests(unittest.TestCase):
    def test_each_tag_accepts_exactly_its_one_wire_value(self) -> None:
        wires = (
            TaggedScalarWire("integer", 7, None, None, None),
            TaggedScalarWire("fp64-bits", None, 0x3FF0000000000000, None, None),
            TaggedScalarWire("text", None, None, "frozen", None),
            TaggedScalarWire(
                "complex128-bits",
                None,
                None,
                None,
                (0x3FF0000000000000, 0),
            ),
        )
        self.assertEqual(
            tuple(wire.value_kind for wire in wires),
            ("integer", "fp64-bits", "text", "complex128-bits"),
        )

    def test_xor_wrong_tag_bool_as_int_and_bit_overflow_fail(self) -> None:
        bad_arguments = (
            ("integer", None, None, None, None),
            ("integer", 1, None, "extra", None),
            ("integer", True, None, None, None),
            ("fp64-bits", None, -1, None, None),
            ("fp64-bits", None, 1 << 64, None, None),
            ("text", None, None, "", None),
            ("complex128-bits", None, None, None, (0, 1 << 64)),
        )
        for arguments in bad_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaises((TypeError, ValueError)):
                    TaggedScalarWire(*arguments)


class ClosedApplicationManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verified = issue_v3m0_parent_freeze()
        cls.manifest = cls.verified.manifest
        cls.constants = cls.manifest.protocol_constant_payload

    def test_no_arg_issuer_freezes_exact_c01_c20_order_and_unique_ids(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(issue_v3m0_parent_freeze).parameters),
            (),
        )
        self.assertEqual(
            tuple(
                spec.control_case_id
                for spec in self.manifest.synthetic_control_application_specs
            ),
            APPLICATION_CONTROL_CASE_IDS,
        )
        self.assertEqual(len(APPLICATION_CONTROL_CASE_IDS), 20)
        instance_ids = tuple(
            spec.application_instance_id
            for spec in self.manifest.synthetic_control_application_specs
        )
        self.assertEqual(len(instance_ids), len(set(instance_ids)))
        operation_ids = tuple(
            operation.operation_instance_id
            for spec in self.manifest.synthetic_control_application_specs
            for operation in spec.operations
        )
        self.assertEqual(len(operation_ids), len(set(operation_ids)))

    def test_full_protocol_bodies_constants_and_document_hashes_are_frozen(
        self,
    ) -> None:
        self.assertEqual(
            self.manifest.parent_freeze_schema_version,
            PARENT_FREEZE_SCHEMA_VERSION,
        )
        self.assertEqual(self.manifest.program_id, PROGRAM_ID)
        self.assertEqual(self.manifest.task9_commit_sha, TASK9_COMMIT_SHA)
        self.assertEqual(
            self.manifest.taskbook_source_sha,
            hashlib.sha256((ROOT / TASKBOOK_SOURCE_PATH).read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest.implementation_plan_source_sha,
            hashlib.sha256(
                (ROOT / IMPLEMENTATION_PLAN_SOURCE_PATH).read_bytes()
            ).hexdigest(),
        )
        self.assertGreater(len(self.constants.tagged_constants), 0)
        for spec in self.manifest.synthetic_control_application_specs:
            self.assertGreater(len(spec.basis_protocol.source_basis.vectors_wire), 0)
            self.assertGreater(len(spec.basis_protocol.readout_basis.vectors_wire), 0)
            self.assertGreater(len(spec.grid_protocol.response_reciprocal_indices), 0)
            self.assertGreater(len(spec.grid_protocol.bridge_reciprocal_indices), 0)
            self.assertGreater(len(spec.readout_protocol.source_metric_whitener.values_wire), 0)
            self.assertGreater(len(spec.operations), 0)
            self.assertGreater(len(spec.output_operation_instance_ids), 0)

        payload = parent_freeze_manifest_payload(self.manifest)
        first_spec = payload["synthetic_control_application_specs"][0]
        self.assertIsInstance(first_spec["basis_protocol"], dict)
        self.assertIsInstance(first_spec["grid_protocol"], dict)
        self.assertIsInstance(first_spec["readout_protocol"], dict)
        self.assertIsInstance(payload["protocol_constant_payload"], dict)

    def test_every_recursive_body_has_the_expected_self_hash(self) -> None:
        constants = self.constants
        self.assertEqual(
            constants.constants_sha,
            canonical_sha(
                synthetic_application_protocol_constants_payload(constants)
            ),
        )
        for spec in self.manifest.synthetic_control_application_specs:
            self.assertEqual(
                spec.basis_protocol.protocol_sha,
                canonical_sha(
                    synthetic_application_basis_protocol_payload(
                        spec.basis_protocol
                    )
                ),
            )
            self.assertEqual(
                spec.grid_protocol.protocol_sha,
                canonical_sha(
                    synthetic_application_grid_protocol_payload(
                        spec.grid_protocol
                    )
                ),
            )
            self.assertEqual(
                spec.readout_protocol.protocol_sha,
                canonical_sha(
                    synthetic_application_readout_protocol_payload(
                        spec.readout_protocol
                    )
                ),
            )
            for operation in spec.operations:
                self.assertEqual(
                    operation.operation_sha,
                    canonical_sha(
                        synthetic_application_operation_payload(operation)
                    ),
                )
            self.assertEqual(
                spec.application_spec_sha,
                canonical_sha(synthetic_control_application_spec_payload(spec)),
            )
        self.assertEqual(
            self.manifest.parent_freeze_sha,
            canonical_sha(parent_freeze_manifest_payload(self.manifest)),
        )

    def test_closed_specs_verify_and_raw_manifest_hydrates(self) -> None:
        for spec in self.manifest.synthetic_control_application_specs:
            self.assertEqual(
                verify_synthetic_control_application_spec(spec, self.constants),
                spec,
            )
        hydrated = verify_parent_freeze(self.manifest)
        self.assertIsInstance(hydrated, VerifiedParentFreeze)
        self.assertEqual(
            _reverify_verified_parent_freeze(hydrated),
            self.manifest,
        )

    def test_operation_kind_dependencies_outputs_and_reachability_are_closed(
        self,
    ) -> None:
        spec = self.manifest.synthetic_control_application_specs[0]
        first = spec.operations[0]
        with self.assertRaisesRegex(ValueError, "operation_kind"):
            dataclasses.replace(
                first,
                operation_kind="open-ended-op",  # type: ignore[arg-type]
            )

        dangling = _resign_operation(
            dataclasses.replace(
                first,
                input_operation_instance_ids=("missing-operation",),
            )
        )
        dangling_spec = _resign_spec(
            dataclasses.replace(spec, operations=(dangling,))
        )
        with self.assertRaisesRegex(ValueError, "dependency|missing"):
            verify_synthetic_control_application_spec(
                dangling_spec,
                self.constants,
            )

        left = _resign_operation(
            dataclasses.replace(
                first,
                operation_instance_id=f"{spec.application_instance_id}.cycle-a",
                input_operation_instance_ids=(
                    f"{spec.application_instance_id}.cycle-b",
                ),
            )
        )
        right = _resign_operation(
            dataclasses.replace(
                first,
                operation_instance_id=f"{spec.application_instance_id}.cycle-b",
                input_operation_instance_ids=(
                    f"{spec.application_instance_id}.cycle-a",
                ),
            )
        )
        cyclic = _resign_spec(
            dataclasses.replace(
                spec,
                operations=(left, right),
                output_operation_instance_ids=(right.operation_instance_id,),
            )
        )
        with self.assertRaisesRegex(ValueError, "cycle|acyclic"):
            verify_synthetic_control_application_spec(cyclic, self.constants)

        independent = _resign_operation(
            dataclasses.replace(
                first,
                operation_instance_id=f"{spec.application_instance_id}.dead",
            )
        )
        dead = _resign_spec(
            dataclasses.replace(
                spec,
                operations=tuple(
                    sorted(
                        (first, independent),
                        key=lambda operation: operation.operation_instance_id,
                    )
                ),
                output_operation_instance_ids=(first.operation_instance_id,),
            )
        )
        with self.assertRaisesRegex(ValueError, "reachable|dead"):
            verify_synthetic_control_application_spec(dead, self.constants)

        missing_output = _resign_spec(
            dataclasses.replace(spec, output_operation_instance_ids=())
        )
        with self.assertRaisesRegex(ValueError, "output"):
            verify_synthetic_control_application_spec(
                missing_output,
                self.constants,
            )

    def test_canonical_order_duplicate_ids_parameters_and_caps_fail(self) -> None:
        spec = self.manifest.synthetic_control_application_specs[0]
        first = spec.operations[0]
        parameter = ("zeta", TaggedScalarWire("integer", 1, None, None, None))
        noncanonical = _resign_operation(
            dataclasses.replace(
                first,
                parameters=(parameter, ("alpha", parameter[1])),
            )
        )
        noncanonical_spec = _resign_spec(
            dataclasses.replace(spec, operations=(noncanonical,))
        )
        with self.assertRaisesRegex(ValueError, "canonical"):
            verify_synthetic_control_application_spec(
                noncanonical_spec,
                self.constants,
            )

        duplicate = _resign_spec(
            dataclasses.replace(spec, operations=(first, first))
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify_synthetic_control_application_spec(
                duplicate,
                self.constants,
            )

        tiny_operation_cap = _resign_constants(
            dataclasses.replace(self.constants, max_operation_count=0)
        )
        with self.assertRaisesRegex(ValueError, "operation.*cap"):
            verify_synthetic_control_application_spec(spec, tiny_operation_cap)

        tiny_edge_cap = _resign_constants(
            dataclasses.replace(self.constants, max_dependency_edge_count=0)
        )
        operation_with_edge = _resign_operation(
            dataclasses.replace(
                first,
                operation_instance_id=f"{spec.application_instance_id}.edge",
                input_operation_instance_ids=(first.operation_instance_id,),
            )
        )
        edge_spec = _resign_spec(
            dataclasses.replace(
                spec,
                operations=(first, operation_with_edge),
                output_operation_instance_ids=(
                    operation_with_edge.operation_instance_id,
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "dependency edge.*cap"):
            verify_synthetic_control_application_spec(
                edge_spec,
                tiny_edge_cap,
            )

        tiny_parameter_cap = _resign_constants(
            dataclasses.replace(self.constants, max_parameter_count=0)
        )
        with self.assertRaisesRegex(ValueError, "parameter.*cap"):
            verify_synthetic_control_application_spec(
                spec,
                tiny_parameter_cap,
            )

        tiny_byte_cap = _resign_constants(
            dataclasses.replace(self.constants, max_serialized_bytes=1)
        )
        with self.assertRaisesRegex(ValueError, "serialized.*cap"):
            verify_synthetic_control_application_spec(spec, tiny_byte_cap)

    def test_closed_manifest_rejects_resigned_substitution_and_wrong_order(
        self,
    ) -> None:
        first = self.manifest.synthetic_control_application_specs[0]
        changed_spec = _resign_spec(
            dataclasses.replace(
                first,
                expected_prediction_profile_id="post-hoc-substitution",
            )
        )
        changed_specs = (
            changed_spec,
            *self.manifest.synthetic_control_application_specs[1:],
        )
        changed_manifest = _resign_manifest(
            dataclasses.replace(
                self.manifest,
                synthetic_control_application_specs=changed_specs,
            )
        )
        with self.assertRaisesRegex(ValueError, "closed|freeze"):
            verify_parent_freeze(changed_manifest)

        reversed_manifest = _resign_manifest(
            dataclasses.replace(
                self.manifest,
                synthetic_control_application_specs=tuple(
                    reversed(self.manifest.synthetic_control_application_specs)
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "order|closed|freeze"):
            verify_parent_freeze(reversed_manifest)

    def test_bad_manifest_self_hash_and_non_raw_input_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "parent_freeze_sha"):
            verify_parent_freeze(
                dataclasses.replace(self.manifest, parent_freeze_sha="0" * 64)
            )
        with self.assertRaises(TypeError):
            verify_parent_freeze(  # type: ignore[arg-type]
                parent_freeze_manifest_payload(self.manifest)
            )


class ParentFreezeCapabilityTests(unittest.TestCase):
    def test_slot_copy_subclass_and_live_slot_mutation_fail_closed(self) -> None:
        issued = issue_v3m0_parent_freeze()
        forged = object.__new__(VerifiedParentFreeze)
        for slot in ("manifest", "token", "seal"):
            object.__setattr__(
                forged,
                f"_VerifiedParentFreeze__{slot}",
                object.__getattribute__(
                    issued,
                    f"_VerifiedParentFreeze__{slot}",
                ),
            )
        with self.assertRaisesRegex(ValueError, "registry|identity"):
            _reverify_verified_parent_freeze(forged)

        class HostileVerifiedParentFreeze(VerifiedParentFreeze):
            __slots__ = ()

        hostile = object.__new__(HostileVerifiedParentFreeze)
        with self.assertRaisesRegex(TypeError, "module-issued"):
            _reverify_verified_parent_freeze(hostile)

        object.__setattr__(
            issued,
            "_VerifiedParentFreeze__manifest",
            dataclasses.replace(issued.manifest, parent_freeze_sha="0" * 64),
        )
        with self.assertRaisesRegex(ValueError, "seal|authority|manifest"):
            _reverify_verified_parent_freeze(issued)

    def test_expired_weakref_and_forged_revival_fail_closed(self) -> None:
        issued = issue_v3m0_parent_freeze()
        saved_slots = tuple(
            object.__getattribute__(
                issued,
                f"_VerifiedParentFreeze__{slot}",
            )
            for slot in ("manifest", "token", "seal")
        )
        reference = weakref.ref(issued)
        del issued
        gc.collect()
        self.assertIsNone(reference())

        revived = object.__new__(VerifiedParentFreeze)
        for slot, value in zip(("manifest", "token", "seal"), saved_slots):
            object.__setattr__(
                revived,
                f"_VerifiedParentFreeze__{slot}",
                value,
            )
        with self.assertRaisesRegex(ValueError, "registry|identity"):
            _reverify_verified_parent_freeze(revived)


if __name__ == "__main__":
    unittest.main()
