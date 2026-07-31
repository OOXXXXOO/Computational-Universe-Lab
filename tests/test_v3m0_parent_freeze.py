from __future__ import annotations

import dataclasses
import gc
import hashlib
import inspect
import struct
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
    ParentFreezeManifest,
    SyntheticApplicationOperation,
    SyntheticApplicationPredictionProfile,
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
    synthetic_application_prediction_profile_payload,
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


def _resign_prediction_profile(
    profile: SyntheticApplicationPredictionProfile,
) -> SyntheticApplicationPredictionProfile:
    return dataclasses.replace(
        profile,
        prediction_profile_sha=canonical_sha(
            synthetic_application_prediction_profile_payload(profile)
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


def _float_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _exact_values(
    profile: SyntheticApplicationPredictionProfile,
) -> dict[str, tuple[TaggedScalarWire, ...]]:
    return dict(profile.expected_exact_values)


def _labels(
    profile: SyntheticApplicationPredictionProfile,
) -> dict[str, tuple[str, ...]]:
    return dict(profile.expected_qualitative_labels)


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

    def test_nonfinite_fp64_and_complex_ieee754_bit_patterns_fail(self) -> None:
        nonfinite_bits = (
            0x7FF0000000000000,
            0xFFF0000000000000,
            0x7FF0000000000001,
            0x7FF8000000000000,
            0xFFF8000000000001,
        )
        for bits in nonfinite_bits:
            with self.subTest(kind="fp64", bits=hex(bits)):
                with self.assertRaisesRegex(ValueError, "finite"):
                    TaggedScalarWire("fp64-bits", None, bits, None, None)
            for component in (0, 1):
                value = [0, 0]
                value[component] = bits
                with self.subTest(
                    kind="complex128",
                    component=component,
                    bits=hex(bits),
                ):
                    with self.assertRaisesRegex(ValueError, "finite"):
                        TaggedScalarWire(
                            "complex128-bits",
                            None,
                            None,
                            None,
                            tuple(value),
                        )

    def test_finite_edge_bit_patterns_remain_legal(self) -> None:
        finite_bits = (
            0x0000000000000000,
            0x8000000000000000,
            0x0000000000000001,
            0x7FEFFFFFFFFFFFFF,
            0xFFEFFFFFFFFFFFFF,
        )
        for bits in finite_bits:
            with self.subTest(bits=hex(bits)):
                self.assertEqual(
                    TaggedScalarWire(
                        "fp64-bits",
                        None,
                        bits,
                        None,
                        None,
                    ).fp64_bits_value,
                    bits,
                )
                self.assertEqual(
                    TaggedScalarWire(
                        "complex128-bits",
                        None,
                        None,
                        None,
                        (bits, 0),
                    ).complex128_bits_value,
                    (bits, 0),
                )


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
            self.assertEqual(spec.protocol_constant_payload, self.constants)
            self.assertEqual(
                spec.expected_prediction_profile.control_case_id,
                spec.control_case_id,
            )

        payload = parent_freeze_manifest_payload(self.manifest)
        first_spec = payload["synthetic_control_application_specs"][0]
        self.assertIsInstance(first_spec["basis_protocol"], dict)
        self.assertIsInstance(first_spec["grid_protocol"], dict)
        self.assertIsInstance(first_spec["readout_protocol"], dict)
        self.assertIsInstance(first_spec["protocol_constant_payload"], dict)
        self.assertIsInstance(first_spec["expected_prediction_profile"], dict)
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
                spec.protocol_constant_payload.constants_sha,
                canonical_sha(
                    synthetic_application_protocol_constants_payload(
                        spec.protocol_constant_payload
                    )
                ),
            )
            self.assertEqual(
                spec.expected_prediction_profile.prediction_profile_sha,
                canonical_sha(
                    synthetic_application_prediction_profile_payload(
                        spec.expected_prediction_profile
                    )
                ),
            )
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
        self.assertEqual(
            tuple(
                inspect.signature(
                    verify_synthetic_control_application_spec
                ).parameters
            ),
            ("spec",),
        )
        for spec in self.manifest.synthetic_control_application_specs:
            self.assertEqual(
                verify_synthetic_control_application_spec(spec),
                spec,
            )
        hydrated = verify_parent_freeze(self.manifest)
        self.assertIsInstance(hydrated, VerifiedParentFreeze)
        self.assertEqual(
            _reverify_verified_parent_freeze(hydrated),
            self.manifest,
        )

    def test_all_twenty_cases_freeze_non_placeholder_dags_and_predictions(
        self,
    ) -> None:
        expected_kinds = {
            "C01_BLIND_HOLDOUT_FULL": {"identity-v1", "geometry-subspace-v1"},
            "C02_CONDITIONED_ZERO": {"identity-v1", "amplitude-rescale-v1"},
            "C03_EQUAL_RANK_DIRECT_SUM": {"amplitude-rescale-v1", "direct-sum-v1"},
            "C04_CANONICAL_ANGLE_025_075": {
                "canonical-shear-v1",
                "geometry-subspace-v1",
            },
            "C05_PHASE_AND_SCALAR_GAIN": {
                "phase-rotation-v1",
                "amplitude-rescale-v1",
            },
            "C06_INTERNAL_NONSCALE_MIXING": {
                "identity-v1",
                "source-linear-mix-v1",
            },
            "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE": {
                "phase-rotation-v1",
                "direct-sum-v1",
            },
            "C08_RANK_R_MISSING_MODES": {
                "identity-v1",
                "geometry-subspace-v1",
            },
            "C09_PURE_GAUGE_DRESSING": {
                "canonical-shear-v1",
                "geometry-subspace-v1",
            },
            "C10_FULL_SOURCE_EXTRA_MODE": {
                "source-linear-mix-v1",
                "geometry-subspace-v1",
            },
            "C11_NULL_GREY_SIGNAL_AMPLITUDE": {
                "amplitude-rescale-v1",
                "direct-sum-v1",
            },
            "C12_NU_INC_IR_NORMALIZATION": {
                "identity-v1",
                "geometry-subspace-v1",
            },
            "C13_BOTH_ZERO_UNDEFINED": {
                "amplitude-rescale-v1",
                "direct-sum-v1",
            },
            "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL": {
                "deterministic-series-v1",
                "direct-sum-v1",
            },
            "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY": {
                "geometry-subspace-v1",
                "direct-sum-v1",
            },
            "C16_COVERAGE_025_075": {
                "coverage-subspace-v1",
                "direct-sum-v1",
            },
            "C17_QUOTIENT_GAUGE_COVERAGE": {
                "canonical-shear-v1",
                "coverage-subspace-v1",
            },
            "C18_ABLATED_INDEPENDENT_UNARY": {
                "source-linear-mix-v1",
                "geometry-subspace-v1",
            },
            "C19_FULL_POSITIVE_OBSERVER_COLLAPSE": {
                "identity-v1",
                "geometry-subspace-v1",
            },
            "C20_DM26_CLEAN_ZERO_TRUE_FLOOR": {
                "deterministic-series-v1",
                "direct-sum-v1",
            },
        }
        for spec in self.manifest.synthetic_control_application_specs:
            with self.subTest(control_case_id=spec.control_case_id):
                self.assertGreaterEqual(len(spec.operations), 2)
                self.assertTrue(
                    expected_kinds[spec.control_case_id].issubset(
                        {operation.operation_kind for operation in spec.operations}
                    )
                )
                self.assertNotIn(
                    "case-ordinal",
                    {
                        name
                        for operation in spec.operations
                        for name, _ in operation.parameters
                    },
                )
                self.assertGreater(
                    len(spec.expected_prediction_profile.expected_exact_values)
                    + len(
                        spec.expected_prediction_profile
                        .expected_qualitative_labels
                    ),
                    0,
                )

    def test_each_control_dag_freezes_its_case_specific_replay_parameters(
        self,
    ) -> None:
        required_parameter_names = {
            "C01_BLIND_HOLDOUT_FULL": {
                "branch-role",
                "construction",
                "target-visibility",
            },
            "C02_CONDITIONED_ZERO": {
                "amplitude-scale",
                "target-visibility",
            },
            "C03_EQUAL_RANK_DIRECT_SUM": {"left-rank", "right-rank"},
            "C04_CANONICAL_ANGLE_025_075": {
                "survival-squared-correlation-0",
                "survival-squared-correlation-1",
            },
            "C05_PHASE_AND_SCALAR_GAIN": {
                "amplitude-scale",
                "phase-radians",
            },
            "C06_INTERNAL_NONSCALE_MIXING": {
                "matrix-00",
                "matrix-01",
                "matrix-10",
                "matrix-11",
            },
            "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE": {
                "combiner-00",
                "combiner-01",
                "combiner-10",
                "combiner-11",
            },
            "C08_RANK_R_MISSING_MODES": {"missing-rank"},
            "C09_PURE_GAUGE_DRESSING": {"gauge-amplitude", "gauge-sector"},
            "C10_FULL_SOURCE_EXTRA_MODE": {
                "new-source-axis",
                "source-domain",
            },
            "C11_NULL_GREY_SIGNAL_AMPLITUDE": {"amplitude-scale"},
            "C12_NU_INC_IR_NORMALIZATION": {
                "curvature-mode-count",
                "normalizer",
                "raw-noise-gates",
            },
            "C13_BOTH_ZERO_UNDEFINED": {"amplitude-scale"},
            "C14_UNSTABLE_UNCLASSIFIED_ENDPOINT_SHELL": {
                "fault-mode",
                "series-code",
            },
            "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY": {
                "frozen-spectrum-length",
                "geometry-variant",
                "physical-rank",
            },
            "C16_COVERAGE_025_075": {
                "coverage-squared-correlation",
            },
            "C17_QUOTIENT_GAUGE_COVERAGE": {
                "gauge-amplitude",
                "quotient",
            },
            "C18_ABLATED_INDEPENDENT_UNARY": {
                "independent-source-axis",
                "observer",
            },
            "C19_FULL_POSITIVE_OBSERVER_COLLAPSE": {
                "certificate",
                "frequency-sector",
            },
            "C20_DM26_CLEAN_ZERO_TRUE_FLOOR": {
                "decision-rule",
                "series-class",
            },
        }
        specs = {
            spec.control_case_id: spec
            for spec in self.manifest.synthetic_control_application_specs
        }
        for control_case_id, required_names in required_parameter_names.items():
            with self.subTest(control_case_id=control_case_id):
                actual_names = {
                    name
                    for operation in specs[control_case_id].operations
                    for name, _ in operation.parameters
                }
                self.assertTrue(required_names.issubset(actual_names))

        c01_roles = tuple(
            wire.text_value
            for operation in specs["C01_BLIND_HOLDOUT_FULL"].operations
            for name, wire in operation.parameters
            if name == "branch-role"
        )
        self.assertEqual(c01_roles, ("actual", "ablated"))

        c07_parameters = {
            name: wire.integer_value
            for operation in specs[
                "C07_CONSTRUCTIVE_DESTRUCTIVE_INTERFERENCE"
            ].operations
            for name, wire in operation.parameters
            if name.startswith("combiner-")
        }
        self.assertEqual(
            c07_parameters,
            {
                "combiner-00": 1,
                "combiner-01": 1,
                "combiner-10": 1,
                "combiner-11": -1,
            },
        )

    def test_c04_c11_and_c15_freeze_mechanical_boundary_predictions(
        self,
    ) -> None:
        specs = {
            spec.control_case_id: spec
            for spec in self.manifest.synthetic_control_application_specs
        }

        c04 = specs["C04_CANONICAL_ANGLE_025_075"]
        self.assertEqual(
            tuple(
                wire.fp64_bits_value
                for wire in _exact_values(
                    c04.expected_prediction_profile
                )["survival-spectrum"]
            ),
            (_float_bits(0.25), _float_bits(0.75)),
        )
        self.assertEqual(
            _labels(c04.expected_prediction_profile)["survival-side"],
            ("below", "above"),
        )
        c04_parameters = {
            name: wire
            for operation in c04.operations
            for name, wire in operation.parameters
        }
        self.assertEqual(
            c04_parameters["survival-squared-correlation-0"].fp64_bits_value,
            _float_bits(0.25),
        )
        self.assertEqual(
            c04_parameters["survival-squared-correlation-1"].fp64_bits_value,
            _float_bits(0.75),
        )

        c11 = specs["C11_NULL_GREY_SIGNAL_AMPLITUDE"]
        self.assertEqual(
            tuple(
                wire.fp64_bits_value
                for wire in _exact_values(
                    c11.expected_prediction_profile
                )["input-amplitude"]
            ),
            (_float_bits(0.0), _float_bits(0.5), _float_bits(1.0)),
        )
        outcomes = _exact_values(c11.expected_prediction_profile)[
            "causal-coordinate"
        ]
        self.assertEqual(
            (
                outcomes[0].fp64_bits_value,
                outcomes[1].text_value,
                outcomes[2].fp64_bits_value,
            ),
            (_float_bits(0.0), "undefined", _float_bits(1.0)),
        )
        self.assertEqual(
            _labels(c11.expected_prediction_profile)["amplitude-regime"],
            ("null", "grey", "signal"),
        )

        c15 = specs["C15_TT_ROW_FULLH_LOWRANK_GEOMETRY"]
        c15_values = _exact_values(c15.expected_prediction_profile)
        self.assertEqual(
            tuple(sorted(c15_values)),
            (
                "g-spectrum.full-h",
                "g-spectrum.low-rank-tt",
                "g-spectrum.tt",
                "g-spectrum.tt-plus-row",
            ),
        )
        self.assertEqual(
            {
                key: tuple(wire.fp64_bits_value for wire in values)
                for key, values in c15_values.items()
            },
            {
                "g-spectrum.full-h": (_float_bits(1.0), _float_bits(1.0)),
                "g-spectrum.low-rank-tt": (
                    _float_bits(0.0),
                    _float_bits(1.0),
                ),
                "g-spectrum.tt": (_float_bits(1.0), _float_bits(1.0)),
                "g-spectrum.tt-plus-row": (
                    _float_bits(1.0),
                    _float_bits(1.0),
                ),
            },
        )
        self.assertEqual(
            _labels(c15.expected_prediction_profile)["geometry-variant"],
            ("full-h", "low-rank-tt", "tt", "tt-plus-row"),
        )

    def test_embedded_constants_and_prediction_cannot_be_resigned_post_hoc(
        self,
    ) -> None:
        c04 = self.manifest.synthetic_control_application_specs[3]
        changed_values = tuple(
            (
                name,
                (
                    TaggedScalarWire(
                        "fp64-bits",
                        None,
                        _float_bits(0.30),
                        None,
                        None,
                    ),
                    *values[1:],
                )
                if name == "survival-spectrum"
                else values,
            )
            for name, values in c04.expected_prediction_profile.expected_exact_values
        )
        changed_profile = _resign_prediction_profile(
            dataclasses.replace(
                c04.expected_prediction_profile,
                expected_exact_values=changed_values,
            )
        )
        changed_spec = _resign_spec(
            dataclasses.replace(
                c04,
                expected_prediction_profile=changed_profile,
            )
        )
        with self.assertRaisesRegex(ValueError, "prediction|control body"):
            verify_synthetic_control_application_spec(changed_spec)

        tiny_constants = _resign_constants(
            dataclasses.replace(
                c04.protocol_constant_payload,
                max_operation_count=0,
            )
        )
        tiny_spec = _resign_spec(
            dataclasses.replace(
                c04,
                protocol_constant_payload=tiny_constants,
            )
        )
        with self.assertRaisesRegex(ValueError, "constant|operation.*cap"):
            verify_synthetic_control_application_spec(tiny_spec)

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
            verify_synthetic_control_application_spec(dangling_spec)

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
            verify_synthetic_control_application_spec(cyclic)

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
            verify_synthetic_control_application_spec(dead)

        missing_output = _resign_spec(
            dataclasses.replace(spec, output_operation_instance_ids=())
        )
        with self.assertRaisesRegex(ValueError, "output"):
            verify_synthetic_control_application_spec(missing_output)

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
            verify_synthetic_control_application_spec(noncanonical_spec)

        duplicate = _resign_spec(
            dataclasses.replace(spec, operations=(first, first))
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify_synthetic_control_application_spec(duplicate)

        tiny_operation_cap = _resign_constants(
            dataclasses.replace(self.constants, max_operation_count=0)
        )
        tiny_operation_spec = _resign_spec(
            dataclasses.replace(
                spec,
                protocol_constant_payload=tiny_operation_cap,
            )
        )
        with self.assertRaisesRegex(ValueError, "operation.*cap"):
            verify_synthetic_control_application_spec(tiny_operation_spec)

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
                protocol_constant_payload=tiny_edge_cap,
                output_operation_instance_ids=(
                    operation_with_edge.operation_instance_id,
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "dependency edge.*cap"):
            verify_synthetic_control_application_spec(edge_spec)

        tiny_parameter_cap = _resign_constants(
            dataclasses.replace(self.constants, max_parameter_count=0)
        )
        tiny_parameter_spec = _resign_spec(
            dataclasses.replace(
                spec,
                protocol_constant_payload=tiny_parameter_cap,
            )
        )
        with self.assertRaisesRegex(ValueError, "parameter.*cap"):
            verify_synthetic_control_application_spec(tiny_parameter_spec)

        tiny_byte_cap = _resign_constants(
            dataclasses.replace(self.constants, max_serialized_bytes=1)
        )
        tiny_byte_spec = _resign_spec(
            dataclasses.replace(
                spec,
                protocol_constant_payload=tiny_byte_cap,
            )
        )
        with self.assertRaisesRegex(ValueError, "serialized.*cap"):
            verify_synthetic_control_application_spec(tiny_byte_spec)

    def test_closed_manifest_rejects_resigned_substitution_and_wrong_order(
        self,
    ) -> None:
        first = self.manifest.synthetic_control_application_specs[0]
        changed_spec = _resign_spec(
            dataclasses.replace(
                first,
                builder_id="post-hoc-substitution",
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
